"""
Fetcher for Adzuna NL via the official public REST API.

API: https://api.adzuna.com/v1/api/jobs/nl/search/{page}

KEY FINDINGS:
  - Requires ADZUNA_APP_ID and ADZUNA_APP_KEY (register at developer.adzuna.com).
    If either key is missing, the fetcher logs a warning and returns [].
  - Page number is in the URL path (/search/1, /search/2, ...), not a query param.
  - max_days_old=14 filters server-side — no need to break on stale dates.
  - sort_by=date returns newest-first.
  - distance param is in km (same convention as NVB_DISTANCE_KM).
  - results_per_page max is 50.
  - Response: {"results": [...], "count": N}
  - Each job: id, title, company.display_name, location.display_name,
    created (ISO 8601), redirect_url, description (truncated snippet).
"""
import logging
import os
from typing import Optional

from ..helpers import (
    build_client, iso_date, iso_ts, utc_now, parse_iso, is_within_days,
    load_title_keywords, title_matches,
)
from ..types import Job, make_canonical_key

logger = logging.getLogger(__name__)

BASE_URL    = "https://api.adzuna.com/v1/api/jobs/nl/search"

DEFAULT_QUERY       = "product manager"
DEFAULT_LOCATION    = "Amsterdam"
DEFAULT_DISTANCE_KM = 40
LOOKBACK_DAYS       = 14
RESULTS_PER_PAGE    = 50
MAX_PAGES           = 4   # 4 × 50 = 200 ceiling; max_days_old=14 already limits volume


async def fetch_adzuna(
    queries: list[str] | None = None,
    lookback_days: int = LOOKBACK_DAYS,
    title_keywords: list[str] | None = None,
) -> list[Job]:
    """
    Fetch Adzuna NL jobs via the official API.

    Requires ADZUNA_APP_ID and ADZUNA_APP_KEY in the environment.
    Returns [] immediately (with a warning) if either key is absent.
    """
    app_id  = os.environ.get("ADZUNA_APP_ID", "").strip()
    app_key = os.environ.get("ADZUNA_APP_KEY", "").strip()
    if not app_id or not app_key:
        logger.warning(
            "Adzuna: ADZUNA_APP_ID and/or ADZUNA_APP_KEY not set — skipping source. "
            "Register at https://developer.adzuna.com to get credentials."
        )
        return []

    queries        = queries or [DEFAULT_QUERY]
    title_keywords = title_keywords or load_title_keywords()
    distance_km    = int(os.environ.get("ADZUNA_DISTANCE_KM", DEFAULT_DISTANCE_KM))
    fetched_at     = iso_ts(utc_now())
    jobs: list[Job] = []
    seen_keys: set[str] = set()

    async with build_client() as client:
        for query in queries:
            logger.info("Adzuna: searching '%s'", query)

            for page in range(1, MAX_PAGES + 1):
                try:
                    resp = await client.get(
                        f"{BASE_URL}/{page}",
                        params={
                            "app_id":          app_id,
                            "app_key":         app_key,
                            "what":            query,
                            "where":           DEFAULT_LOCATION,
                            "distance":        distance_km,
                            "max_days_old":    lookback_days,
                            "sort_by":         "date",
                            "results_per_page": RESULTS_PER_PAGE,
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()
                except Exception as e:
                    logger.error("Adzuna error page %d for '%s': %s", page, query, e)
                    break

                raw_jobs = data.get("results") or []
                if not raw_jobs:
                    logger.info("Adzuna '%s': empty page %d — done", query, page)
                    break

                skipped_title = 0
                for raw in raw_jobs:
                    if not title_matches(raw.get("title", ""), "", title_keywords):
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
                    logger.info(
                        "Adzuna '%s' page %d: skipped %d off-topic titles",
                        query, page, skipped_title,
                    )

                # If fewer results than a full page, we've exhausted this query
                if len(raw_jobs) < RESULTS_PER_PAGE:
                    break

    logger.info("Adzuna: collected %d jobs", len(jobs))
    return jobs


def _normalise(raw: dict, fetched_at: str) -> Optional[Job]:
    job_id = str(raw.get("id") or "")
    title  = raw.get("title") or ""
    if not job_id or not title:
        return None

    company = (raw.get("company") or {}).get("display_name") or ""

    # location.display_name is e.g. "Amsterdam, Noord-Holland" — keep city only
    loc_display = (raw.get("location") or {}).get("display_name") or ""
    city = loc_display.split(",")[0].strip() if loc_display else ""

    date_str    = raw.get("created") or ""
    dt          = parse_iso(date_str)
    date_posted = iso_date(dt) if dt else date_str

    apply_url   = raw.get("redirect_url") or ""
    description = raw.get("description") or None

    return Job(
        id            = job_id,
        source        = "adzuna",
        title         = title,
        company       = company,
        location      = city,
        date_posted   = date_posted,
        fetched_at    = fetched_at,
        description   = description,
        apply_url     = apply_url,
        canonical_key = make_canonical_key(title, company, city),
    )
