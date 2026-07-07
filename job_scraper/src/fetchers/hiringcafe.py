"""
Fetcher for hiring.cafe — a global job board with strong NL/EU coverage.

KEY FINDINGS (2026-06-01):
  - Old /api/search-jobs endpoint is now auth-gated (returns 401).
  - Cloudflare challenge is no longer presented; cf_clearance approach is obsolete.
  - Current approach: fetch /_next/data/{buildId}/index.json?searchState=<JSON>
    — a public Next.js SSR endpoint that returns the first page of results without auth.
  - buildId is extracted from __NEXT_DATA__ in the hiring.cafe homepage HTML.
  - Location filtering: pass Netherlands location object in searchState.locations;
    geo_country=NL cookie also helps server-side filtering.
  - Date filtering: dateFetchedPastNDays in searchState is honoured server-side.
  - Pagination: only the SSR first page is publicly accessible (~58-74 results/query).
    Subsequent pages require auth — single-page retrieval is accepted as the limit.
  - ssrIsLastPage: true signals no further pages even if we could fetch them.

Field map (unchanged from original — same job object structure):
  title       → job_information.title
  company     → enriched_company_data.name  (or v5.company_name fallback)
  location    → v5.formatted_workplace_location
  date_posted → v5.estimated_publish_date
  apply_url   → apply_url
  description → job_information.description  (full HTML)
  id          → id  (e.g. "ashby___mollie___3955c991-...")
"""
import json
import logging
import re
from typing import Optional

import httpx

from ..helpers import (
    build_client, iso_date, iso_ts, utc_now, parse_iso, is_within_days,
    load_title_keywords, title_matches, html_to_md,
)
from ..types import Job, make_canonical_key, is_description_ok

logger = logging.getLogger(__name__)

LOOKBACK_DAYS = 14
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/145.0.0.0 Safari/537.36"
)
_NL_LOCATION = {
    "formatted_address": "Netherlands",
    "types": ["country"],
    "geometry": {"location": {"lat": "52.3759", "lon": "4.8975"}},
    "id": "user_country",
    "address_components": [
        {"long_name": "Netherlands", "short_name": "NL", "types": ["country"]}
    ],
    "options": {"flexible_regions": ["anywhere_in_continent", "anywhere_in_world"]},
}
_GEO_COOKIES = {
    "geo_country": "NL",
    "geo_lat": "52.3716",
    "geo_lng": "4.8883",
    "geo_city": "Amsterdam",
}


def _get_build_id(client: httpx.Client) -> str:
    """Extract Next.js buildId from the hiring.cafe homepage __NEXT_DATA__ block."""
    resp = client.get("https://hiring.cafe/", timeout=15)
    resp.raise_for_status()
    m = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        resp.text,
    )
    if not m:
        raise RuntimeError("__NEXT_DATA__ not found in hiring.cafe HTML")
    return json.loads(m.group(1))["buildId"]


async def fetch_hiringcafe(
    queries: list[str] | None = None,
    lookback_days: int = LOOKBACK_DAYS,
    title_keywords: list[str] | None = None,
) -> list[Job]:
    """Fetch hiring.cafe NL jobs via the Next.js SSR data endpoint."""
    queries        = queries or ["product manager"]
    title_keywords = title_keywords or load_title_keywords()
    fetched_at     = iso_ts(utc_now())
    jobs: list[Job] = []
    seen_keys: set[str] = set()

    headers = {
        "User-Agent": _UA,
        "Accept": "*/*",
        "Referer": "https://hiring.cafe/",
        "x-nextjs-data": "1",
    }

    with httpx.Client(headers=headers, cookies=_GEO_COOKIES, follow_redirects=True, timeout=20.0) as client:
        try:
            build_id = _get_build_id(client)
            logger.info("hiring.cafe: buildId=%s", build_id)
        except Exception as e:
            logger.error("hiring.cafe: could not fetch buildId — %s", e)
            return []

        data_url = f"https://hiring.cafe/_next/data/{build_id}/index.json"

        for query in queries:
            logger.info("hiring.cafe: searching '%s'", query)
            search_state = json.dumps({
                "searchQuery": query,
                "locations": [_NL_LOCATION],
                "dateFetchedPastNDays": lookback_days,
            })
            try:
                resp = client.get(data_url, params={"searchState": search_state})
                resp.raise_for_status()
                page_props = resp.json().get("pageProps", {})
            except Exception as e:
                logger.error("hiring.cafe '%s': %s", query, e)
                continue

            raw_jobs = page_props.get("ssrHits") or []
            ssr_error = page_props.get("ssrError")
            if ssr_error:
                logger.error("hiring.cafe '%s': ssrError=%s", query, ssr_error)
                continue

            logger.info(
                "hiring.cafe '%s': %d hits (total=%s, isLastPage=%s)",
                query, len(raw_jobs),
                page_props.get("ssrTotalCount"),
                page_props.get("ssrIsLastPage"),
            )

            skipped_title = 0
            for raw in raw_jobs:
                if raw.get("is_expired"):
                    continue

                v5   = raw.get("v5_processed_job_data") or {}
                info = raw.get("job_information") or {}
                title = info.get("title") or ""

                if not title_matches(title, "", title_keywords):
                    skipped_title += 1
                    continue

                date_str = v5.get("estimated_publish_date") or ""
                if date_str and not is_within_days(date_str, lookback_days):
                    continue

                job = _normalise(raw, v5, info, fetched_at)
                if job is None:
                    continue
                if job.canonical_key in seen_keys:
                    continue
                seen_keys.add(job.canonical_key)
                jobs.append(job)

            if skipped_title:
                logger.info("hiring.cafe '%s': skipped %d off-topic titles", query, skipped_title)

    logger.info("hiring.cafe: collected %d jobs", len(jobs))
    return jobs


def _normalise(raw: dict, v5: dict, info: dict, fetched_at: str) -> Optional[Job]:
    job_id = raw.get("id") or ""
    title  = info.get("title") or ""
    if not job_id or not title:
        return None

    company_data = raw.get("enriched_company_data") or {}
    company = company_data.get("name") or v5.get("company_name") or ""

    location = v5.get("formatted_workplace_location") or ""
    parts = [p.strip() for p in location.split(",")]
    if len(parts) >= 2 and parts[-1] == parts[-2]:
        location = ", ".join(parts[:-1])

    date_str    = v5.get("estimated_publish_date") or ""
    dt          = parse_iso(date_str)
    date_posted = iso_date(dt) if dt else date_str[:10] if date_str else ""

    apply_url = raw.get("apply_url") or f"https://hiring.cafe/viewjob/{job_id}"

    description = html_to_md(info.get("description")) or None
    return Job(
        id             = job_id,
        source         = "hiringcafe",
        title          = title,
        company        = company,
        location       = location,
        date_posted    = date_posted,
        fetched_at     = fetched_at,
        description    = description,
        apply_url      = apply_url,
        canonical_key  = make_canonical_key(title, company, location),
        description_ok = is_description_ok(description),
    )
