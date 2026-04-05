"""
Fetcher for hiring.cafe — a global job board with strong NL/EU coverage.

API: https://hiring.cafe/api/search-jobs

KEY FINDINGS (2026-03-26):
  - Site is protected by Cloudflare Bot Management (JS challenge).
    Plain httpx / curl-cffi both fail with 403.
  - Solution: cf_clearance Python package (Playwright + stealth JS injection)
    launches a real Chromium browser, solves the challenge automatically, and
    returns a cf_clearance cookie that authorises subsequent httpx requests.
  - Cookie must be used with the SAME User-Agent that Playwright reported;
    mismatched UA causes immediate 403.
  - Cookie lifetime: ~30 min to a few hours. Refreshed automatically each run.
  - Search state param `s` = base64(url_encode(JSON)) — a 94-key JSON object.
    Only a handful of keys matter; the rest can be omitted (API ignores missing keys).
  - Pagination: ?page=1,2,3... — empty results array signals end.
  - Date field: v5_processed_job_data.estimated_publish_date (ISO-8601 string).
  - Location field: v5_processed_job_data.formatted_workplace_location (human string).
  - `is_expired: True` listings are occasionally returned — filtered out.

Field map:
  title       → job_information.title
  company     → enriched_company_data.name  (or v5.company_name fallback)
  location    → v5.formatted_workplace_location
  date_posted → v5.estimated_publish_date
  apply_url   → apply_url
  description → job_information.description  (full HTML)
  id          → id  (e.g. "ashby___mollie___3955c991-...")
"""
import asyncio
import base64
import logging
from typing import Optional
from urllib.parse import quote

import httpx

from ..helpers import (
    build_client, iso_date, iso_ts, utc_now, parse_iso, is_within_days,
    load_title_keywords, title_matches, html_to_md,
)
from ..types import Job, make_canonical_key

logger = logging.getLogger(__name__)

PAGE_SIZE     = 40
MAX_PAGES     = 10
LOOKBACK_DAYS = 14

# Netherlands country-level location object used in the search state.
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


def _build_s(query: str, lookback_days: int) -> str:
    """Encode a hiring.cafe search state as base64(url_encode(JSON))."""
    payload = {
        "searchQuery": query,
        "locations": [_NL_LOCATION],
        "workplaceTypes": ["Remote", "Hybrid", "Onsite"],
        "commitmentTypes": ["Full Time", "Part Time", "Contract"],
        "dateFetchedPastNDays": lookback_days,
        "sortBy": "default",
    }
    import json
    return base64.b64encode(quote(json.dumps(payload)).encode()).decode()


async def _get_cf_clearance() -> tuple[str, str]:
    """
    Launch a stealth Chromium browser, solve the Cloudflare challenge on
    hiring.cafe, and return (cf_clearance_value, user_agent).

    Raises RuntimeError if the cookie cannot be obtained.
    """
    try:
        from playwright.async_api import async_playwright
        from cf_clearance import async_stealth, async_cf_retry
    except ImportError as e:
        raise RuntimeError(
            "cf-clearance and playwright are required for hiring.cafe. "
            "Run: pip install cf-clearance playwright && playwright install chromium"
        ) from e

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        try:
            page = await browser.new_page()
            await async_stealth(page)
            await page.goto("https://hiring.cafe/")
            await async_cf_retry(page, tries=15)
            ua = await page.evaluate("navigator.userAgent")
            cookies = await page.context.cookies()
        finally:
            await browser.close()

    cf = next((c["value"] for c in cookies if c["name"] == "cf_clearance"), None)
    if not cf:
        raise RuntimeError("hiring.cafe: cf_clearance cookie not found after challenge")
    return cf, ua


async def fetch_hiringcafe(
    queries: list[str] | None = None,
    lookback_days: int = LOOKBACK_DAYS,
    title_keywords: list[str] | None = None,
) -> list[Job]:
    """Fetch hiring.cafe NL jobs via the search API (Cloudflare-protected)."""
    queries        = queries or ["product manager"]
    title_keywords = title_keywords or load_title_keywords()
    fetched_at     = iso_ts(utc_now())
    jobs: list[Job] = []
    seen_keys: set[str] = set()

    # Solve Cloudflare challenge once; reuse cookie for all pages.
    try:
        cf_cookie, ua = await _get_cf_clearance()
    except Exception as e:
        logger.error("hiring.cafe: could not obtain cf_clearance — %s", e)
        return []

    headers = {
        "User-Agent": ua,
        "Accept": "*/*",
        "Referer": "https://hiring.cafe/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    }

    async with httpx.AsyncClient(
        headers=headers,
        cookies={"cf_clearance": cf_cookie},
        follow_redirects=True,
        timeout=30.0,
    ) as client:
        for query in queries:
            logger.info("hiring.cafe: searching '%s'", query)
            s = _build_s(query, lookback_days)

            for page_num in range(1, MAX_PAGES + 1):
                try:
                    resp = await client.get(
                        "https://hiring.cafe/api/search-jobs",
                        params={"s": s, "size": str(PAGE_SIZE), "page": str(page_num), "sv": "control"},
                    )
                    resp.raise_for_status()
                    raw_jobs = resp.json().get("results", [])
                except Exception as e:
                    logger.error("hiring.cafe '%s' page %d: %s", query, page_num, e)
                    break

                if not raw_jobs:
                    logger.info("hiring.cafe '%s': empty page at %d — done", query, page_num)
                    break

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
                    logger.info(
                        "hiring.cafe '%s' page %d: skipped %d off-topic titles",
                        query, page_num, skipped_title,
                    )

                if page_num < MAX_PAGES:
                    await asyncio.sleep(1.0)

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
    # Trim redundant country suffix: "Amsterdam, North Holland, Netherlands" → keep as-is
    # but "Netherlands, Netherlands" → "Netherlands"
    parts = [p.strip() for p in location.split(",")]
    if len(parts) >= 2 and parts[-1] == parts[-2]:
        location = ", ".join(parts[:-1])

    date_str    = v5.get("estimated_publish_date") or ""
    dt          = parse_iso(date_str)
    date_posted = iso_date(dt) if dt else date_str[:10] if date_str else ""

    apply_url = raw.get("apply_url") or f"https://hiring.cafe/viewjob/{job_id}"

    return Job(
        id            = job_id,
        source        = "hiringcafe",
        title         = title,
        company       = company,
        location      = location,
        date_posted   = date_posted,
        fetched_at    = fetched_at,
        description   = html_to_md(info.get("description")) or None,
        apply_url     = apply_url,
        canonical_key = make_canonical_key(title, company, location),
    )
