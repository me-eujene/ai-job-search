"""
Fetcher for LinkedIn NL via the public guest API (no authentication required).

Endpoint: https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search

Returns HTML fragments — parsed with BeautifulSoup4 (lxml backend).

Notes:
- No API key or login needed. LinkedIn intentionally exposes job listings publicly
  so search engines can index them.
- f_TPR timespan codes: r86400=24h, r604800=7d, r1209600=14d, r2592000=30d
- Pagination via start= param (25 jobs per page); empty page signals end of results
- Sleep 1s between pages to be polite and avoid rate limiting
- build_client() sets Accept: application/json globally; we override it per-request
  because the guest API returns HTML, not JSON
"""
import asyncio
import logging
from typing import Optional

from bs4 import BeautifulSoup

from ..helpers import (
    build_client, iso_date, iso_ts, utc_now, parse_iso, is_within_days,
    load_title_keywords, title_matches,
)
from ..types import Job, make_canonical_key

logger = logging.getLogger(__name__)

BASE_URL    = "https://www.linkedin.com"
SEARCH_PATH = "/jobs-guest/jobs/api/seeMoreJobPostings/search"

DEFAULT_QUERIES  = ["product manager"]
LOCATION         = "Amsterdam, Netherlands"
LOOKBACK_DAYS    = 14
PAGE_SIZE        = 25
MAX_PAGES        = 5           # ceiling: 5 × 25 = 125 jobs per query
INTER_PAGE_SLEEP = 2.0         # seconds between page fetches (1s hit 429 at page 5)

# f_TPR values by day bucket. We pick the smallest bucket >= lookback_days.
_TPR_BUCKETS = [(7, "r604800"), (14, "r1209600"), (30, "r2592000")]

# Per-request Accept override (guest API returns HTML, not JSON)
_HTML_HEADERS = {"Accept": "text/html, application/xhtml+xml, */*;q=0.9"}


async def fetch_linkedin(
    queries: list[str] | None = None,
    lookback_days: int = LOOKBACK_DAYS,
    title_keywords: list[str] | None = None,
) -> list[Job]:
    """Fetch LinkedIn NL jobs via the public guest API. No API key needed."""
    queries        = queries or DEFAULT_QUERIES
    title_keywords = title_keywords or load_title_keywords()
    fetched_at     = iso_ts(utc_now())
    jobs: list[Job] = []
    seen_keys: set[str] = set()

    # Pick the nearest f_TPR bucket covering lookback_days
    tpr = "r2592000"  # default: 30d
    for days, code in _TPR_BUCKETS:
        if lookback_days <= days:
            tpr = code
            break

    async with build_client() as client:
        for query in queries:
            logger.info("LinkedIn: searching '%s'", query)
            start     = 0
            date_stop = False

            for page_num in range(MAX_PAGES):
                if date_stop:
                    break

                params = {
                    "keywords": query,
                    "location": LOCATION,
                    "f_TPR":    tpr,
                    "start":    start,
                }

                try:
                    resp = await client.get(
                        BASE_URL + SEARCH_PATH,
                        params=params,
                        headers=_HTML_HEADERS,
                    )
                    resp.raise_for_status()
                except Exception as e:
                    logger.error(
                        "LinkedIn page %d error for '%s': %s", page_num, query, e
                    )
                    break

                cards = _parse_cards(resp.text)
                if not cards:
                    logger.info(
                        "LinkedIn '%s': empty page at start=%d — done", query, start
                    )
                    break

                skipped_title = 0
                for raw in cards:
                    # Date gate — listings are newest-first, so we can early-exit
                    date_str = raw.get("date", "")
                    if date_str and not is_within_days(date_str, lookback_days):
                        date_stop = True
                        break

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
                        "LinkedIn '%s' start=%d: skipped %d off-topic titles",
                        query, start, skipped_title,
                    )

                start += PAGE_SIZE
                if page_num < MAX_PAGES - 1 and not date_stop:
                    await asyncio.sleep(INTER_PAGE_SLEEP)

    logger.info("LinkedIn: collected %d jobs", len(jobs))
    return jobs


def _parse_cards(html: str) -> list[dict]:
    """Parse job cards from a LinkedIn guest API HTML fragment."""
    soup  = BeautifulSoup(html, "lxml")
    cards = []

    for card in soup.find_all("div", class_="base-card"):
        # Job ID from data-entity-urn="urn:li:jobPosting:1234567890"
        urn    = card.get("data-entity-urn", "")
        job_id = urn.split(":")[-1] if urn else ""

        title_tag = card.find("h3", class_="base-search-card__title")
        title     = title_tag.get_text(strip=True) if title_tag else ""

        subtitle  = card.find("h4", class_="base-search-card__subtitle")
        company_a = subtitle.find("a") if subtitle else None
        company   = company_a.get_text(strip=True) if company_a else ""

        loc_tag  = card.find("span", class_="job-search-card__location")
        location = loc_tag.get_text(strip=True) if loc_tag else ""

        time_tag = card.find("time")
        date_str = time_tag.get("datetime", "") if time_tag else ""

        cards.append({
            "id":       job_id,
            "title":    title,
            "company":  company,
            "location": location,
            "date":     date_str,
        })

    return cards


def _normalise(raw: dict, fetched_at: str) -> Optional[Job]:
    title   = raw.get("title", "")
    company = raw.get("company", "")
    if not title:
        return None

    # LinkedIn location strings: "Amsterdam, North Holland, Netherlands" → city only
    loc_full = raw.get("location", "")
    city     = loc_full.split(",")[0].strip() if loc_full else ""

    job_id      = raw.get("id", "")
    date_str    = raw.get("date", "")
    dt          = parse_iso(date_str)
    date_posted = iso_date(dt) if dt else date_str

    apply_url = f"{BASE_URL}/jobs/view/{job_id}/" if job_id else ""

    return Job(
        id            = job_id or make_canonical_key(title, company, city)[:16],
        source        = "linkedin",
        title         = title,
        company       = company,
        location      = city,
        date_posted   = date_posted,
        fetched_at    = fetched_at,
        description   = None,  # search results don't include full descriptions
        apply_url     = apply_url,
        canonical_key = make_canonical_key(title, company, city),
    )
