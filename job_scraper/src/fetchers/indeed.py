"""
Fetcher for Indeed NL via jobs-api14 on RapidAPI.

Endpoint: https://jobs-api14.p.rapidapi.com/v2/indeed/search
Free tier: 200 requests/month.

Budget:  3 queries × ~1 page each = 3 calls/run × 22 weekdays = 66 calls/month
         Well within 200/month even if queries are expanded.

Key findings from live tests (2026-03-23):
- location precision works at city level (Amsterdam vs Rotterdam returns different results)
- datePosted=week is available but returns < 24h old results when combined with sort=date
- salary is always null in NL listings — not included in output
- experienceLevels=senior returns 0 results — don't use
"""
import logging
import os
from datetime import datetime, timezone
from typing import Optional

import httpx

from ..helpers import (
    build_client, iso_date, iso_ts, utc_now, parse_iso, is_within_days,
    load_title_keywords, title_matches,
)
from ..types import Job, make_canonical_key

logger = logging.getLogger(__name__)

BASE_URL      = "https://jobs-api14.p.rapidapi.com"
SEARCH_PATH   = "/v2/indeed/search"
RAPIDAPI_HOST = "jobs-api14.p.rapidapi.com"

DEFAULT_QUERIES = [
    "product manager",
]

LOCATION      = "Amsterdam, Netherlands"
COUNTRY       = "NL"
PAGE_SIZE     = 20
LOOKBACK_DAYS = 14


async def fetch_indeed(
    queries: list[str] | None = None,
    api_key: str | None = None,
    lookback_days: int = LOOKBACK_DAYS,
    title_keywords: list[str] | None = None,
) -> list[Job]:
    """
    Fetch Indeed NL jobs via RapidAPI.
    api_key defaults to RAPIDAPI_KEY environment variable.
    """
    api_key        = api_key or os.environ.get("RAPIDAPI_KEY", "")
    title_keywords = title_keywords or load_title_keywords()
    if not api_key:
        logger.error("RAPIDAPI_KEY not set; skipping Indeed fetch")
        return []

    queries    = queries or DEFAULT_QUERIES
    fetched_at = iso_ts(utc_now())
    jobs: list[Job] = []
    seen_keys: set[str] = set()

    headers = {
        "x-rapidapi-host": RAPIDAPI_HOST,
        "x-rapidapi-key": api_key,
    }

    async with build_client() as client:
        for query in queries:
            logger.info("Indeed: searching '%s'", query)
            try:
                raw_jobs = await _search(client, headers, query)
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    logger.warning("Indeed: rate limited (429) on query '%s'", query)
                else:
                    logger.error("Indeed HTTP error for '%s': %s", query, e)
                continue
            except Exception as e:
                logger.error("Indeed error for '%s': %s", query, e)
                continue

            skipped_title = 0
            for raw in raw_jobs:
                # Date filter
                date_str = raw.get("datePosted") or raw.get("datePublished") or ""
                if date_str and not is_within_days(date_str, lookback_days):
                    continue

                # Title relevance gate
                raw_title = raw.get("title") or raw.get("jobTitle") or ""
                if not title_matches(raw_title, "", title_keywords):
                    skipped_title += 1
                    continue

                job = _normalise(raw, fetched_at)
                if job is None:
                    continue

                if job.canonical_key in seen_keys:
                    continue
                seen_keys.add(job.canonical_key)
                jobs.append(job)

            if skipped_title:
                logger.info("Indeed '%s': skipped %d off-topic titles", query, skipped_title)

    logger.info("Indeed: collected %d jobs", len(jobs))
    return jobs


async def _search(
    client: httpx.AsyncClient, headers: dict, query: str
) -> list[dict]:
    params = {
        "query":       query,
        "location":    LOCATION,
        "countryCode": COUNTRY,
        "datePosted":  "week",          # limit to last 7 days server-side
        "sortType":    "date",
    }
    resp = await client.get(
        BASE_URL + SEARCH_PATH,
        params=params,
        headers=headers,
    )
    resp.raise_for_status()
    data = resp.json()

    # Documented schema: { "data": [...], "meta": { "totalResults": N } }
    for key in ("data", "jobs"):
        if key in data:
            return data[key]
    logger.warning("Indeed: unexpected response shape — top-level keys: %s", list(data.keys()))
    return []


def _normalise(raw: dict, fetched_at: str) -> Optional[Job]:
    """Convert a raw jobs-api14 Indeed result to a Job."""
    job_id = raw.get("id") or raw.get("jobId") or ""
    title  = raw.get("title") or raw.get("jobTitle") or ""
    if not title:
        return None

    # Company
    company = raw.get("companyName") or raw.get("company") or raw.get("organization") or ""
    if isinstance(company, dict):
        company = company.get("name") or company.get("display_name") or ""

    # Location — API returns { "location": str, "country": str, "countryCode": str }
    loc_obj = raw.get("location") or {}
    if isinstance(loc_obj, dict):
        city        = loc_obj.get("location") or loc_obj.get("city") or loc_obj.get("display") or ""
        country_val = loc_obj.get("countryCode") or loc_obj.get("country") or "NL"
    else:
        city        = str(loc_obj)
        country_val = "NL"

    if country_val not in ("NL", "Netherlands", "nederland"):
        return None

    # Date — prefer timestamp, fall back to datePosted string
    ts_ms = raw.get("datePublishedTimestamp")
    if ts_ms:
        dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
        date_posted = iso_date(dt)
    else:
        date_raw = raw.get("datePosted") or raw.get("datePublished") or ""
        dt2 = parse_iso(date_raw)
        date_posted = iso_date(dt2) if dt2 else ""

    apply_url = raw.get("applyUrl") or raw.get("detailsPageUrl") or raw.get("url") or ""

    description = raw.get("description") or raw.get("snippet") or None

    canonical_key = make_canonical_key(title, company, city)

    return Job(
        id=str(job_id) if job_id else canonical_key[:16],
        source="indeed",
        title=title,
        company=company,
        location=city,
        date_posted=date_posted,
        fetched_at=fetched_at,
        description=description,
        apply_url=apply_url,
        canonical_key=canonical_key,
    )
