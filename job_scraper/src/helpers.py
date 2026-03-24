"""
Shared utilities: HTTP client factory, HTML stripping, date helpers, title filter.
"""
import os
import re
import httpx
from datetime import datetime, timezone, timedelta
from typing import Optional


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

def build_client(timeout: float = 15.0) -> httpx.AsyncClient:
    """Return a pre-configured async HTTP client."""
    return httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=True,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json",
            "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.8",
        },
    )


async def get_json(client: httpx.AsyncClient, url: str,
                   params: Optional[dict] = None,
                   extra_headers: Optional[dict] = None) -> dict:
    """GET a URL and return parsed JSON. Raises on non-2xx."""
    headers = extra_headers or {}
    resp = await client.get(url, params=params, headers=headers)
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------

_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s{2,}")


def strip_html(html: Optional[str]) -> Optional[str]:
    """Remove HTML tags and collapse whitespace."""
    if not html:
        return html
    text = _TAG_RE.sub(" ", html)
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace(
        "&gt;", ">").replace("&nbsp;", " ").replace("&quot;", '"')
    return _WHITESPACE_RE.sub(" ", text).strip()


# ---------------------------------------------------------------------------
# Dates
# ---------------------------------------------------------------------------

def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def run_id_now() -> str:
    """Generate a run ID from the current UTC time: YYYYMMDD_HHMMSS"""
    return utc_now().strftime("%Y%m%d_%H%M%S")


def iso_date(dt: datetime) -> str:
    """Return ISO 8601 date string: YYYY-MM-DD"""
    return dt.strftime("%Y-%m-%d")


def iso_ts(dt: datetime) -> str:
    """Return ISO 8601 timestamp with Z suffix."""
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def cutoff_date(days: int = 14) -> datetime:
    """Return a UTC datetime N days ago."""
    return utc_now() - timedelta(days=days)


def parse_iso(s: Optional[str]) -> Optional[datetime]:
    """Parse an ISO 8601 string (with or without timezone) to a datetime."""
    if not s:
        return None
    # Strip trailing Z, then parse
    s = s.rstrip("Z").split("+")[0]
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def is_within_days(date_str: Optional[str], days: int = 14) -> bool:
    """Return True if date_str is within the last N days."""
    dt = parse_iso(date_str)
    if dt is None:
        return True   # include if unknown
    return dt >= cutoff_date(days)


# ---------------------------------------------------------------------------
# Title keyword filter (shared by all fetchers)
# ---------------------------------------------------------------------------

_DEFAULT_TITLE_KEYWORDS = [
    "product manager",
    "product lead",
    "head of product",
    "director of product",
    "vp product",
    "chief product",
    "product owner",
    "product director",
    "productmanager",      # Dutch spelling
    "producteigenaar",     # Dutch for product owner
]


def load_title_keywords() -> list[str]:
    """Load title keywords from TITLE_KEYWORDS env var, or use built-in defaults."""
    raw = os.environ.get("TITLE_KEYWORDS", "")
    if raw:
        return [k.strip().lower() for k in raw.split(",") if k.strip()]
    return _DEFAULT_TITLE_KEYWORDS


def title_matches(title: str, function_title: str, keywords: list[str]) -> bool:
    """Return True if either title field contains at least one keyword."""
    haystack = f"{title} {function_title}".lower()
    return any(kw in haystack for kw in keywords)
