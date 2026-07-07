"""
Fetcher for We Work Remotely (WWR) — Product Jobs RSS feed.

Feed: https://weworkremotely.com/remote-jobs.rss  (all categories, ~79 items)

KEY FINDINGS (2026-03-28):
  - Plain HTTP GET with a browser User-Agent returns RSS 2.0 XML (200 OK).
    Without a User-Agent header, Cloudflare returns 403.
  - No auth, no API key required.
  - Single feed — no pagination. All live listings returned in one response.
  - Typically 2–10 items at any time; items expire ~30 days after posting.
  - Title format: "Company: Job Title" — split on first ": " to separate fields.
  - Location: <region> element — e.g. "Anywhere in the World", "USA Only".
    Geo filter: allowlist keeps only regions compatible with NL-based applicants
    ("anywhere in the world", "europe", "emea", "worldwide"). Region-restricted
    listings like "USA Only" or "North America Only" are dropped.
  - pubDate is RFC 2822 (e.g. "Mon, 16 Mar 2026 20:31:52 +0000"), NOT ISO 8601.
    Parsed via email.utils.parsedate_to_datetime (stdlib, no extra dep).
  - Apply URL: <guid> element (same as <link>).
  - Description: HTML-encoded in CDATA — strip_html() applied for storage.
"""
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Optional

from ..helpers import (
    build_client, iso_date, iso_ts, utc_now, cutoff_date,
    load_title_keywords, title_matches, html_to_md,
)
from ..types import Job, make_canonical_key, is_description_ok

logger = logging.getLogger(__name__)

FEED_URL      = "https://weworkremotely.com/remote-jobs.rss"
LOOKBACK_DAYS = 30   # WWR posts expire ~30 days after posting; match that window

# Allowlist: region substrings compatible with an NL-based remote worker.
# Empty region is also accepted (treat as unrestricted).
_ALLOWED_REGION_SUBSTRINGS = (
    "anywhere",
    "europe",
    "emea",
    "worldwide",
    "global",
)


def _region_ok(region: str) -> bool:
    """Return True if the region is open to NL-based applicants."""
    if not region:
        return True
    r = region.lower()
    return any(a in r for a in _ALLOWED_REGION_SUBSTRINGS)


def _parse_rfc2822(s: Optional[str]) -> Optional[datetime]:
    """Parse an RFC 2822 date string to UTC datetime."""
    if not s:
        return None
    try:
        return parsedate_to_datetime(s.strip()).astimezone(timezone.utc)
    except Exception:
        return None


async def fetch_wwr(
    lookback_days: int = LOOKBACK_DAYS,
    title_keywords: list[str] | None = None,
) -> list[Job]:
    """
    Fetch WeWorkRemotely Product Jobs from the public RSS feed.

    No credentials required. Returns [] on any HTTP or parse error.
    """
    title_keywords = title_keywords or load_title_keywords()
    fetched_at     = iso_ts(utc_now())
    cutoff         = cutoff_date(lookback_days)
    jobs: list[Job] = []
    seen_keys: set[str] = set()

    async with build_client() as client:
        try:
            resp = await client.get(
                FEED_URL,
                headers={"Accept": "application/rss+xml, application/xml, text/xml, */*"},
            )
            resp.raise_for_status()
            xml_bytes = resp.content
        except Exception as e:
            logger.error("WWR: failed to fetch feed: %s", e)
            return []

    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        logger.error("WWR: XML parse error: %s", e)
        return []

    items = root.findall(".//item")
    logger.info("WWR: %d items in feed", len(items))

    for item in items:
        raw_title  = item.findtext("title") or ""
        guid       = item.findtext("guid") or item.findtext("link") or ""
        pub_date   = item.findtext("pubDate") or ""
        region     = item.findtext("region") or ""
        raw_desc   = item.findtext("description") or ""

        # Geo filter — drop region-restricted listings not open to NL
        if not _region_ok(region):
            continue

        # Date filter
        dt = _parse_rfc2822(pub_date)
        if dt and dt < cutoff:
            continue

        # Split "Company: Job Title" → company + title
        if ": " in raw_title:
            company, title = raw_title.split(": ", 1)
        else:
            company = ""
            title   = raw_title

        if not title:
            continue

        # Title keyword filter
        if not title_matches(title, "", title_keywords):
            continue

        date_posted = iso_date(dt) if dt else ""
        description = html_to_md(raw_desc) or None

        job = Job(
            id             = guid,
            source         = "wwr",
            title          = title.strip(),
            company        = company.strip(),
            location       = region.strip() or "Remote",
            date_posted    = date_posted,
            fetched_at     = fetched_at,
            description    = description,
            apply_url      = guid,
            canonical_key  = make_canonical_key(title, company, region),
            description_ok = is_description_ok(description),
        )

        if job.canonical_key in seen_keys:
            continue
        seen_keys.add(job.canonical_key)
        jobs.append(job)

    logger.info("WWR: collected %d jobs (after title filter + date cutoff)", len(jobs))
    return jobs
