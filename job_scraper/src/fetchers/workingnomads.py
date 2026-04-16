"""
Fetcher for Working Nomads — Elasticsearch API.

API: POST https://www.workingnomads.com/jobsapi/_search

KEY FINDINGS (2026-04-16):
  - The site uses a public Elasticsearch endpoint (/jobsapi/_search). The
    /api/exposed_jobs/ endpoint is a red herring: it returns the last 32 jobs
    globally, ignoring all filter params — do not use it.
  - The frontend URL ?tag=product-manager maps to a query_string phrase search
    for "product manager" across fields title^2, description, company, with
    min_score=2. This is what we replicate here (plus OR variants for product
    owner / head of product / product lead / product director).
  - Location filter: {"terms": {"locations": [<allowlist>]}} where `locations`
    is a discrete array per job. Allowlist keeps Europe-compatible locations;
    USA / North America / Latin America / APAC are excluded.
  - Date filter: {"range": {"pub_date": {"gte": "now-Nd/d"}}} — server-side.
  - Pagination: `from` + `size` (50/page). Sorted by pub_date desc.
  - apply_url: direct external URL (no WN redirect needed).
  - Auth: none required. Public Elasticsearch endpoint.
"""
import logging
from typing import Optional

from ..helpers import (
    build_client, iso_date, iso_ts, utc_now, parse_iso,
    load_title_keywords, title_matches, html_to_md,
)
from ..types import Job, make_canonical_key

logger = logging.getLogger(__name__)

BASE_URL    = "https://www.workingnomads.com"
SEARCH_PATH = "/jobsapi/_search"

PAGE_SIZE     = 50
MAX_PAGES     = 6
LOOKBACK_DAYS = 14

# Discrete location values on Working Nomads that are accessible to an
# NL-based remote worker. The `locations` field is an array of these strings.
_EUROPE_LOCATIONS = {
    "Anywhere",
    "EMEA",
    "Europe",
    "UK",
    "Ireland",
    "Germany",
    "Spain",
    "Poland",
    "Portugal",
    "Netherlands",
    "France",
    "Czechia",
    "Lithuania",
    "Romania",
    "Switzerland",
    "Sweden",
    "Italy",
    "Denmark",
    "Finland",
    "Norway",
    "Serbia",
    "Ukraine",
    "Austria",
    "Estonia",
    "Hungary",
    "Belgium",
    "Cyprus",
    "Slovakia",
    "Croatia",
    "Greece",
    "Latvia",
    "Slovenia",
}


# Phrase terms mirroring the frontend ?tag=product-manager query.
# The frontend converts tag slugs to phrases (hyphen→space) then searches
# via query_string across title^2, description, company with min_score=2.
_PM_QUERY = (
    '"product manager" OR "product owner" OR "head of product" '
    'OR "product director" OR "product lead"'
)


def _build_query(lookback_days: int, page: int) -> dict:
    return {
        "track_total_hits": True,
        "min_score": 2,
        "from": (page - 1) * PAGE_SIZE,
        "size": PAGE_SIZE,
        "sort": [{"pub_date": {"order": "desc"}}],
        "_source": [
            "id", "title", "company", "locations", "pub_date",
            "apply_url", "description",
        ],
        "query": {
            "bool": {
                "must": {
                    "query_string": {
                        "query": _PM_QUERY,
                        "fields": ["title^2", "description", "company"],
                    }
                },
                "filter": [
                    {"terms": {"locations": sorted(_EUROPE_LOCATIONS)}},
                    {"range": {"pub_date": {"gte": f"now-{lookback_days}d/d"}}},
                ],
            }
        },
    }


async def fetch_workingnomads(
    lookback_days: int = LOOKBACK_DAYS,
    title_keywords: list[str] | None = None,
) -> list[Job]:
    """
    Fetch Working Nomads Management jobs filtered to Europe-compatible locations.

    No credentials required. All filtering is server-side except title keyword
    matching (client-side safety net).
    """
    title_keywords = title_keywords or load_title_keywords()
    fetched_at     = iso_ts(utc_now())
    jobs: list[Job] = []
    seen_keys: set[str] = set()

    async with build_client() as client:
        page       = 1
        total_hits = None

        while page <= MAX_PAGES:
            try:
                resp = await client.post(
                    BASE_URL + SEARCH_PATH,
                    json=_build_query(lookback_days, page),
                    headers={"Content-Type": "application/json"},
                )
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                logger.error("workingnomads: error page %d: %s", page, e)
                break

            hits_obj = data.get("hits") or {}
            if total_hits is None:
                total_hits = (hits_obj.get("total") or {}).get("value", 0)

            raw_hits = hits_obj.get("hits") or []
            if not raw_hits:
                break

            kept = skipped = 0
            for hit in raw_hits:
                raw = hit.get("_source") or {}

                if not title_matches(raw.get("title", ""), "", title_keywords):
                    skipped += 1
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
                "workingnomads page %d  kept=%d  skipped(title)=%d  total_hits=%s",
                page, kept, skipped, total_hits,
            )

            if len(jobs) + (page - 1) * PAGE_SIZE >= (total_hits or 0):
                break

            page += 1

    logger.info("workingnomads: collected %d jobs", len(jobs))
    return jobs


def _normalise(raw: dict, fetched_at: str) -> Optional[Job]:
    job_id = str(raw.get("id") or "")
    title  = (raw.get("title") or "").strip()
    if not job_id or not title:
        return None

    company   = (raw.get("company") or "").strip()
    locations = raw.get("locations") or []
    location  = ", ".join(locations) if locations else "Remote"
    apply_url = raw.get("apply_url") or f"{BASE_URL}/job/go/{job_id}/"

    dt          = parse_iso(raw.get("pub_date") or "")
    date_posted = iso_date(dt) if dt else ""

    return Job(
        id            = job_id,
        source        = "workingnomads",
        title         = title,
        company       = company,
        location      = location,
        date_posted   = date_posted,
        fetched_at    = fetched_at,
        description   = html_to_md(raw.get("description")) or None,
        apply_url     = apply_url,
        canonical_key = make_canonical_key(title, company, location),
    )
