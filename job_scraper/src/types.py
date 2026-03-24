"""
Core data types for the NL job scraper.
"""
from dataclasses import dataclass, field
from typing import Optional
import hashlib


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


def make_canonical_key(title: str, company: str, city: str) -> str:
    """SHA1 fingerprint for cross-source deduplication."""
    raw = f"{title.lower().strip()}|{company.lower().strip()}|{city.lower().strip()}"
    return hashlib.sha1(raw.encode()).hexdigest()
