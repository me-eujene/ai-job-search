"""
Fetcher for Welcome to the Jungle (WTTJ).

API: Algolia search — https://csekhvms53-dsn.algolia.net/1/indexes/wttj_jobs_production_en/query

KEY FINDINGS (2026-04-14):
  - WTTJ is a React SPA; job data comes entirely from Algolia.
  - Algolia App ID and API key are public/client-side, embedded in window.env in every
    page response: ALGOLIA_APPLICATION_ID=CSEKHVMS53, ALGOLIA_API_KEY_CLIENT=...
  - The API requires a Referer: https://www.welcometothejungle.com/ header; without it
    Algolia returns 403 "Method not allowed with this referer".
  - Index name: wttj_jobs_production_en  (EN language shard)
  - Pagination: 0-indexed `page` param; response has `nbPages`.
  - Date filter: server-side via numericFilters on `published_at_timestamp` (Unix seconds).
  - Apply URL pattern: https://www.welcometothejungle.com/en/companies/{org_slug}/jobs/{wk_reference}
  - Facet filter syntax: list of lists = OR within, AND across.
  - Auth: none beyond the public Referer-gated key.
  - Rate limiting: not observed at 50-hit pages; 0.5s sleep between pages is sufficient.
"""
import logging
import time
from typing import Optional

from ..helpers import (
    build_client, iso_date, iso_ts, utc_now, parse_iso, is_within_days,
    load_title_keywords, title_matches,
)
from ..types import Job, make_canonical_key, is_description_ok

logger = logging.getLogger(__name__)

ALGOLIA_HOST    = "https://csekhvms53-dsn.algolia.net"
ALGOLIA_APP_ID  = "CSEKHVMS53"
ALGOLIA_API_KEY = "4bd8f6215d0cc52b26430765769e65a0"
ALGOLIA_INDEX   = "wttj_jobs_production_en"
WTTJ_BASE_URL   = "https://www.welcometothejungle.com"

PAGE_SIZE     = 50
MAX_PAGES     = 6
LOOKBACK_DAYS = 14

# Facet filters to keep results relevant.
# OR within each sub-list; AND between sub-lists.
_PROFESSION_FILTER = [
    "new_profession.sub_category_reference:product-management-wNjYw",
    "new_profession.sub_category_reference:technical-product-management-jNjUx",
]
_REMOTE_FILTER = [
    "remote:fulltime",
]
_CONTRACT_FILTER = [
    "contract_type:full_time",
    "contract_type:freelance",
    "contract_type:temporary",
]
# OR across both parent sectors (travel, mobility) and tech sub-sectors.
# Keeping these in one list avoids the Algolia AND-between-groups behaviour
# that would otherwise require a company to be tagged in both groups.
_SECTOR_FILTER = [
    "sectors.parent_reference:hotel-tourism-leisure",
    "sectors.parent_reference:mobility-transport",
    "sectors.reference:artificial-intelligence-machine-learning",
    "sectors.reference:big-data-1",
    "sectors.reference:connected-objects",
    "sectors.reference:mobile-apps",
    "sectors.reference:saas-cloud-services",
    "sectors.reference:software-1",
]


async def fetch_wttj(
    lookback_days: int = LOOKBACK_DAYS,
    title_keywords: list[str] | None = None,
) -> list[Job]:
    """
    Fetch Welcome to the Jungle jobs via Algolia.

    Searches the EN language index for PM roles (product-management +
    technical-product-management) that are remote-friendly (fulltime,
    partial, or punctual remote), posted within `lookback_days`.

    No API key needed beyond the public client key baked into the site HTML.
    """
    title_keywords = title_keywords or load_title_keywords()
    fetched_at     = iso_ts(utc_now())
    cutoff_ts      = int(time.time()) - (lookback_days * 86400)

    jobs: list[Job] = []
    seen_keys: set[str] = set()

    _algolia_headers = {
        "X-Algolia-Application-Id": ALGOLIA_APP_ID,
        "X-Algolia-API-Key":        ALGOLIA_API_KEY,
        "Referer":                  "https://www.welcometothejungle.com/",
    }

    async with build_client() as client:
        page = 0
        while page < MAX_PAGES:
            body = {
                "query":          "",
                "hitsPerPage":    PAGE_SIZE,
                "page":           page,
                "facetFilters":   [
                    _PROFESSION_FILTER,
                    _REMOTE_FILTER,
                    _CONTRACT_FILTER,
                    _SECTOR_FILTER,
                ],
                "numericFilters": [f"published_at_timestamp>={cutoff_ts}"],
            }
            try:
                resp = await client.post(
                    f"{ALGOLIA_HOST}/1/indexes/{ALGOLIA_INDEX}/query",
                    json=body,
                    headers=_algolia_headers,
                )
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                logger.error("wttj error page %d: %s", page, e)
                break

            hits = data.get("hits") or []
            nb_pages = data.get("nbPages") or 1

            if not hits:
                break

            for raw in hits:
                if not title_matches(raw.get("name", ""), "", title_keywords):
                    continue

                job = _normalise(raw, fetched_at)
                if job is None:
                    continue
                if job.canonical_key in seen_keys:
                    continue
                seen_keys.add(job.canonical_key)
                jobs.append(job)

            logger.info(
                "wttj page %d/%d  hits=%d  kept_so_far=%d",
                page + 1, nb_pages, len(hits), len(jobs),
            )

            if page + 1 >= nb_pages:
                break
            page += 1

    logger.info("wttj: collected %d jobs", len(jobs))
    return jobs


def _normalise(raw: dict, fetched_at: str) -> Optional[Job]:
    wk_ref = raw.get("wk_reference") or ""
    title  = raw.get("name") or ""
    if not wk_ref or not title:
        return None

    org      = raw.get("organization") or {}
    company  = org.get("name") or ""
    org_slug = org.get("slug") or ""

    offices  = raw.get("offices") or [{}]
    city     = (offices[0].get("city") or "") if offices else ""
    country  = (offices[0].get("country_code") or "") if offices else ""
    location = f"{city}, {country}".strip(", ") if city or country else ""

    dt          = parse_iso(raw.get("published_at") or "")
    date_posted = iso_date(dt) if dt else (raw.get("published_at_date") or "")

    apply_url = (
        f"{WTTJ_BASE_URL}/en/companies/{org_slug}/jobs/{wk_ref}"
        if org_slug
        else f"{WTTJ_BASE_URL}/en/jobs/{wk_ref}"
    )

    description = raw.get("summary") or None
    return Job(
        id             = wk_ref,
        source         = "wttj",
        title          = title,
        company        = company,
        location       = location,
        date_posted    = date_posted,
        fetched_at     = fetched_at,
        description    = description,
        apply_url      = apply_url,
        canonical_key  = make_canonical_key(title, company, city),
        description_ok = is_description_ok(description),
    )
