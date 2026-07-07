"""
Core data types for the NL job scraper.
"""
from dataclasses import dataclass, field
from typing import Optional
import hashlib
import re


@dataclass
class Job:
    """Normalised job posting from any source."""
    id: str                      # source-specific ID (string)
    source: str                  # "indeed" | "linkedin" | "nvb"
    title: str
    company: str
    location: str                # city, or city + province
    date_posted: str             # ISO 8601 date  e.g. "2026-03-22"
    fetched_at: str              # ISO 8601 timestamp e.g. "2026-03-23T07:00:00Z"
    description: Optional[str]   # HTML or plain text
    apply_url: str
    canonical_key: str           # SHA1(title.lower + company.lower + city.lower)
    description_ok: bool = False  # True if description is substantive (>=200 chars)


@dataclass
class RunResult:
    """Summary of a single scheduled or manual run."""
    run_id: str
    started_at: str              # ISO 8601 timestamp
    finished_at: str             # ISO 8601 timestamp
    total_fetched: int
    new_jobs: int
    skipped_duplicates: int
    errors: list[str] = field(default_factory=list)
    sources: dict[str, int] = field(default_factory=dict)   # source -> new count


# Gender tags like (m/f/d), (m/v/x), (w/m/d) — any 2-3 single letters separated
# by / or |. Deliberately narrow: real qualifiers like (Payments) must survive.
_GENDER_TAG_RE = re.compile(r"\s*\((?:[a-z]\s*[/|]\s*){1,2}[a-z]\)\s*", re.IGNORECASE)

# Trailing corporate legal suffixes. Word-boundary anchored, end-of-string only.
_LEGAL_SUFFIX_RE = re.compile(
    r"[\s,]+(b\.?\s?v\.?|n\.?v\.?|inc\.?|ltd\.?|llc|gmbh|ag|sa|s\.a\.)\s*$",
    re.IGNORECASE,
)

_WS_RE = re.compile(r"\s+")


def _norm_title(title: str) -> str:
    t = _GENDER_TAG_RE.sub(" ", title.lower())
    return _WS_RE.sub(" ", t).strip()


def _norm_company(company: str) -> str:
    c = _LEGAL_SUFFIX_RE.sub("", company.lower().strip())
    return _WS_RE.sub(" ", c).strip()


def _norm_city(city: str) -> str:
    # Sources format locations differently ("Amsterdam" vs "Amsterdam, Netherlands"
    # vs "Amsterdam, Noord-Holland"). First comma-segment is the city everywhere.
    return _WS_RE.sub(" ", city.lower().split(",")[0].strip())


def make_canonical_key(title: str, company: str, city: str) -> str:
    """SHA1 fingerprint for cross-source deduplication.

    Normalization is deliberately conservative: formatting noise only.
    A missed merge costs one duplicate evaluation; an over-merge loses a role.
    """
    raw = f"{_norm_title(title)}|{_norm_company(company)}|{_norm_city(city)}"
    return hashlib.sha1(raw.encode()).hexdigest()


def is_description_ok(description, min_chars: int = 200) -> bool:
    return bool(description) and len(description) >= min_chars
