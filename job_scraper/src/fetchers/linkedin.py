"""
Fetcher for LinkedIn NL via jobs-api14 on RapidAPI.

Endpoint: https://jobs-api14.p.rapidapi.com/v2/linkedin/search

Notes from live tests (2026-03-23):
- Returns up to ~20 jobs per call
- employmentTypes=fulltime works; experienceLevels=senior returns 0 results (don't use)
- Remote filter: workplaceTypes=remote
- No reliable datePosted filter — filter client-side by datePublishedTimestamp

Budget: 3 queries × 1 call each = 3 calls/run (same key as Indeed; combined budget is
        6 calls/run × 22 weekdays = 132 calls/month — within the 200/month free tier).
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
SEARCH_PATH   = "/v2/linkedin/search"
RAPIDAPI_HOST = "jobs-api14.p.rapidapi.com"

DEFAULT_QUERIES = [
    "product manager",
]

LOCATION      = "Amsterdam, Netherlands"
LOOKBACK_DAYS = 14


async def fetch_linkedin(
    queries: list[str] | None = None,
    api_key: str | None = None,
    lookback_days: int = LOOKBACK_DAYS,
    title_keywords: list[str] | None = None,
) -> list[Job]:
    """
    Fetch LinkedIn NL jobs via RapidAPI.
    api_key defaults to RAPIDAPI_KEY environment variable.
    """
    api_key        = api_key or os.environ.get("RAPIDAPI_KEY", "")
    title_keywords = title_keywords or load_title_keywords()
    if not api_key:
        logger.error("RAPIDAPI_KEY not set; skipping LinkedIn fetch")
        return []

    queries = queries or DEFAULT_QUERIES
    fetched_at = iso_ts(utc_now())
    jobs: list[Job] = []
    seen_keys: set[str] = set()

    headers = {
        "x-rapidapi-host": RAPIDAPI_HOST,
        "x-rapidapi-key": api_key,
    }

    async with build_client() as client:
        for query in queries:
            logger.info("LinkedIn: searching '%s'", query)
            try:
                raw_jobs = await _search(client, headers, query)
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    logger.warning("LinkedIn: rate limited (429) on query '%s'", query)
                else:
                    logger.error("LinkedIn HTTP error for '%s': %s", query, e)
                continue
            except Exception as e:
                logger.error("LinkedIn error for '%s': %s", query, e)
                continue

            skipped_title = 0
            for raw in raw_jobs:
                # Date filter
                ts_ms = raw.get("datePublishedTimestamp")
                if ts_ms:
                    dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
                    if not is_within_days(iso_ts(dt), lookback_days):
                        continue
                elif raw.get("datePosted"):
                    if not is_within_days(raw["datePosted"], lookback_days):
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
                logger.info("LinkedIn '%s': skipped %d off-topic titles", query, skipped_title)

    logger.info("LinkedIn: collected %d jobs", len(jobs))
    return jobs


async def _search(
    client: httpx.AsyncClient, headers: dict, query: str
) -> list[dict]:
    params = {
        "query":           query,
        "location":        LOCATION,
        "employmentTypes": "fulltime",
    }
    resp = await client.get(
        BASE_URL + SEARCH_PATH,
        params=params,
        headers=headers,
    )
    resp.raise_for_status()
    data = resp.json()

    # Documented schema: { "jobs": [...] }
    for key in ("jobs", "data"):
        if key in data:
            return data[key]
    logger.warning("LinkedIn: unexpected response shape — top-level keys: %s", list(data.keys()))
    return []


def _normalise(raw: dict, fetched_at: str) -> Optional[Job]:
    """Convert a raw jobs-api14 LinkedIn result to a Job."""
    job_id = raw.get("id") or raw.get("jobId") or ""
    title  = raw.get("title") or raw.get("jobTitle") or ""
    if not title:
        return None

    company = raw.get("companyName") or raw.get("company") or raw.get("organization") or ""
    if isinstance(company, dict):
        company = company.get("name") or ""

    loc_obj = raw.get("location") or {}
    if isinstance(loc_obj, dict):
        city = loc_obj.get("city") or loc_obj.get("display") or ""
    else:
        city = str(loc_obj)

    # Date
    ts_ms = raw.get("datePublishedTimestamp")
    if ts_ms:
        dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
        date_posted = iso_date(dt)
    else:
        date_raw = raw.get("datePosted") or ""
        dt2 = parse_iso(date_raw)
        date_posted = iso_date(dt2) if dt2 else ""

    apply_url = raw.get("linkedinUrl") or raw.get("detailsPageUrl") or raw.get("url") or ""

    description = raw.get("description") or raw.get("snippet") or None

    canonical_key = make_canonical_key(title, company, city)

    return Job(
        id=str(job_id) if job_id else canonical_key[:16],
        source="linkedin",
        title=title,
        company=company,
        location=city,
        date_posted=date_posted,
        fetched_at=fetched_at,
        description=description,
        apply_url=apply_url,
        canonical_key=canonical_key,
    )
