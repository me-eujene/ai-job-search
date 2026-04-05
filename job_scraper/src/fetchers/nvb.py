"""
Fetcher for Nationale Vacaturebank (NVB).

API: https://api.nationalevacaturebank.nl/api/jobs/v3/sites/nationalevacaturebank.nl/jobs

KEY FINDINGS (2026-03-23):
  - The `query` param is full-text description search — returns pizzamakers, hospital
    staff, anything mentioning "product manager" in the body. Do NOT use alone.
  - Server-side filters use a space-separated compound string in a single `filters` param:
      filters=dcoTitle:Productmanager city:Amsterdam latitude:52.371016 longitude:4.904189 distance:40
  - dcoTitle filter reduces results from 3,254 → 273 NL-wide, then location + distance
    further reduces to ~92 within 40km of Amsterdam. 4 pages of 25.
  - Geolocation API: GET /api/v1/geolocations/nl/{cityName}
    Returns { cityCenter: { latitude, longitude }, cityName, ... }
  - A small number of false positives (dcoTitle mapping noise) remain — removed by the
    client-side title keyword filter.
"""
import json as _json
import logging
import os
from typing import Optional

import httpx

from ..helpers import (
    build_client, iso_date, iso_ts, utc_now, parse_iso, is_within_days,
    load_title_keywords, title_matches, html_to_md,
)
from ..types import Job, make_canonical_key

logger = logging.getLogger(__name__)

BASE_URL     = "https://api.nationalevacaturebank.nl"
SEARCH_PATH  = "/api/jobs/v3/sites/nationalevacaturebank.nl/jobs"
GEO_PATH     = "/api/v1/geolocations/nl/{city}"

# -------------------------------------------------------------------
# Defaults — all overridable via env vars
# -------------------------------------------------------------------

# NVB taxonomy title (dcoTitle). "Productmanager" covers PM, Senior PM,
# Product Owner, Product Lead etc. per live testing.
DEFAULT_DCO_TITLE   = "Productmanager"

# Location for the distance filter
DEFAULT_CITY        = "Amsterdam"
DEFAULT_LATITUDE    = "52.371016"
DEFAULT_LONGITUDE   = "4.904189"
DEFAULT_DISTANCE_KM = "40"

PAGE_SIZE     = 25
MAX_PAGES     = 6          # 6 × 25 = 150 ceiling; typical run is 4 pages (~92 results)
LOOKBACK_DAYS = 14


# -------------------------------------------------------------------
# Config loaders
# -------------------------------------------------------------------

def _build_filters(city: str, lat: str, lon: str, distance: str,
                   dco_title: str) -> str:
    """Build the space-separated NVB filters string."""
    return (
        f"dcoTitle:{dco_title}"
        f" city:{city}"
        f" latitude:{lat}"
        f" longitude:{lon}"
        f" distance:{distance}"
    )


# -------------------------------------------------------------------
# Geolocation lookup
# -------------------------------------------------------------------

async def resolve_city(client: httpx.AsyncClient, city: str) -> tuple[str, str]:
    """
    Look up lat/lon for a Dutch city via the NVB geolocation API.
    Returns (latitude, longitude) as strings.
    Falls back to Amsterdam defaults on error.
    """
    try:
        url = BASE_URL + GEO_PATH.format(city=city.lower())
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()
        center = data.get("cityCenter") or {}
        lat = str(center.get("latitude") or DEFAULT_LATITUDE)
        lon = str(center.get("longitude") or DEFAULT_LONGITUDE)
        logger.info("NVB geo: %s → lat=%s lon=%s", city, lat, lon)
        return lat, lon
    except Exception as e:
        logger.warning("NVB geo lookup failed for '%s': %s — using defaults", city, e)
        return DEFAULT_LATITUDE, DEFAULT_LONGITUDE


# -------------------------------------------------------------------
# Main fetcher
# -------------------------------------------------------------------

async def fetch_nvb(
    lookback_days: int = LOOKBACK_DAYS,
    title_keywords: list[str] | None = None,
    dco_title: str | None = None,
    city: str | None = None,
    distance_km: str | None = None,
) -> list[Job]:
    """
    Fetch NVB jobs using server-side dcoTitle + location filters.

    All arguments fall back to environment variables, then built-in defaults:
      NVB_DCO_TITLE   — taxonomy title (default: Productmanager)
      NVB_CITY        — city name for location filter (default: Amsterdam)
      NVB_DISTANCE_KM — search radius in km (default: 40)
      TITLE_KEYWORDS  — comma-separated client-side title filter
    """
    dco_title      = dco_title      or os.environ.get("NVB_DCO_TITLE",   DEFAULT_DCO_TITLE)
    city           = city           or os.environ.get("NVB_CITY",        DEFAULT_CITY)
    distance_km    = distance_km    or os.environ.get("NVB_DISTANCE_KM", DEFAULT_DISTANCE_KM)
    title_keywords = title_keywords or load_title_keywords()
    fetched_at     = iso_ts(utc_now())
    jobs: list[Job] = []
    seen_keys: set[str] = set()

    async with build_client() as client:
        # Resolve city coordinates
        lat, lon = await resolve_city(client, city)

        filters_str = _build_filters(city, lat, lon, distance_km, dco_title)
        logger.info("NVB: filters=%r  title_keywords=%s", filters_str, title_keywords)

        page      = 1
        date_stop = False

        while not date_stop and page <= MAX_PAGES:
            try:
                data = await _search_page(client, filters_str, page)
            except httpx.HTTPStatusError as e:
                logger.error(
                    "NVB HTTP %s page %d — body: %s",
                    e.response.status_code, page,
                    e.response.text[:200],
                )
                break
            except Exception as e:
                logger.error("NVB error page %d: %s", page, e)
                break

            raw_jobs = (data.get("_embedded") or {}).get("jobs") or []
            if not raw_jobs:
                break

            kept = skipped_title = 0
            for raw in raw_jobs:
                # Date cutoff — sort=date is newest-first
                if not is_within_days(raw.get("startDate"), lookback_days):
                    date_stop = True
                    break

                # Client-side title filter: safety net for dcoTitle taxonomy noise
                raw_title = raw.get("title") or ""
                raw_fn    = raw.get("functionTitle") or ""
                if not title_matches(raw_title, raw_fn, title_keywords):
                    skipped_title += 1
                    continue

                job = _normalise(raw, fetched_at)
                if job is None:
                    continue

                if job.canonical_key in seen_keys:
                    continue
                seen_keys.add(job.canonical_key)
                jobs.append(job)
                kept += 1

            logger.info(
                "NVB page %d/%s  kept=%d  skipped(title)=%d  date_stop=%s",
                page, data.get("pages", "?"), kept, skipped_title, date_stop,
            )

            if page >= (data.get("pages") or 1):
                break
            page += 1

    logger.info("NVB total: %d jobs", len(jobs))
    return jobs


# -------------------------------------------------------------------
# HTTP + normalisation
# -------------------------------------------------------------------

async def _search_page(
    client: httpx.AsyncClient, filters_str: str, page: int
) -> dict:
    # Build the URL manually so the filters string is encoded with %20 for spaces
    # and literal colons — httpx's params= encoding can produce + for spaces which
    # some proxy/CDN layers reject.
    from urllib.parse import urlencode, quote
    qs = urlencode({
        "limit": PAGE_SIZE,
        "page":  page,
        "sort":  "date",
    })
    # Encode filters separately: %20 for spaces, keep colons literal
    filters_enc = quote(filters_str, safe=":")
    url = f"{BASE_URL}{SEARCH_PATH}?{qs}&filters={filters_enc}"
    resp = await client.get(url)
    resp.raise_for_status()
    # Force UTF-8: httpx/chardet can misdetect cp1251 from Cyrillic-heavy
    # description text, garbling € and – characters.
    return _json.loads(resp.content.decode("utf-8"))


def _normalise(raw: dict, fetched_at: str) -> Optional[Job]:
    job_id = raw.get("id")
    title  = raw.get("title") or raw.get("functionTitle") or ""
    if not job_id or not title:
        return None

    company_obj = raw.get("company") or {}
    company     = company_obj.get("name") or ""

    loc_obj  = raw.get("workLocation") or {}
    city     = loc_obj.get("city") or loc_obj.get("municipality") or ""
    province = loc_obj.get("province") or ""
    country  = (loc_obj.get("country") or {}).get("iso") or "NL"

    if country != "NL":
        return None

    location = city if not province else f"{city}, {province}"

    dt          = parse_iso(raw.get("startDate") or "")
    date_posted = iso_date(dt) if dt else ""

    apply_obj = raw.get("apply") or {}
    apply_url = apply_obj.get("url") or ""
    if not apply_url:
        links     = raw.get("_links") or {}
        detail    = links.get("detail") or {}
        apply_url = (
            detail.get("href")
            or f"https://www.nationalevacaturebank.nl/vacature/{job_id}"
        )

    return Job(
        id            = str(job_id),
        source        = "nvb",
        title         = title,
        company       = company,
        location      = location,
        date_posted   = date_posted,
        fetched_at    = fetched_at,
        description   = html_to_md(raw.get("description")) or None,
        apply_url     = apply_url,
        canonical_key = make_canonical_key(title, company, city),
    )
