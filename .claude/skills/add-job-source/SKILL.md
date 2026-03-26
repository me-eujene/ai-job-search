---
name: add-job-source
description: "Add a new Dutch job site as a data source to the Python job scraper pipeline. Triggers on: add source, add job site, add [site name] to scraper, new data source, integrate [site], scrape [site]"
allowed-tools: "Read, Write, Edit, Glob, Grep, Bash, WebFetch, WebSearch"
---

# Add a New Job Source to the Pipeline

## Overview

This skill guides you through discovering a job site's data API and implementing a new Python async fetcher that plugs into the existing pipeline.

**Philosophy: intelligence first, implementation second.**
Start with the cheapest possible request (a plain HTTP GET), escalate only when needed, and validate every assumption before writing a fetcher. Both existing fetchers (`linkedin.py`, `nvb.py`) were built this way — the NVB docstring even records the key reconnaissance findings.

---

## Phase 0 — Quick HTTP Assessment

Run a plain `curl` or `httpx` request against the site's job listing URL **before opening a browser**.

```bash
# Check response type and headers
curl -sI "https://example.com/vacatures"

# Fetch the page and inspect the first ~300 lines
curl -s "https://example.com/vacatures?q=product+manager" | head -300
```

**What to look for:**

| Signal | Implication |
|--------|-------------|
| `Content-Type: application/json` | Direct public API — use it |
| `<script>` tag with `__NEXT_DATA__` or hydration JSON | Data embedded in HTML — extractable without browser |
| Fully server-rendered HTML with job cards | BeautifulSoup scraping (like `linkedin.py`) |
| Empty `<div id="app">` / `<div id="root">` | JavaScript SPA — go to Phase 1 |

**Advance to Phase 1 only if** the response body contains no usable job data. Most Dutch job boards expose a public REST API; check Phase 2 first.

---

## Phase 1 — Browser Network Interception (JS-rendered sites only)

Ask the user to open the site in Chrome and:
1. Open DevTools → **Network** tab → filter by **Fetch/XHR**
2. Perform a job search (e.g. "product manager Amsterdam")
3. Look for API calls returning JSON arrays or objects containing job data

Alternatively, use the Claude-in-Chrome tools if available:
- Navigate to the site, open the network panel, trigger a search
- Filter requests for patterns: `/api/`, `/jobs`, `/vacatures`, `/search`, `graphql`

**Document every endpoint found**, including:
- Full URL with query parameters
- Request headers (especially `Authorization`, `X-Api-Key`, `Content-Type`)
- Response schema (field names for title, company, location, date, apply URL)

---

## Phase 2 — API Deep Scan

Once you have a candidate endpoint, probe it systematically:

```bash
# Test the raw endpoint
curl -s "https://example.com/api/jobs?q=product+manager&location=Amsterdam&page=1" | python -m json.tool | head -100

# Check for sitemap or robots.txt clues
curl -s "https://example.com/sitemap.xml" | head -50
curl -s "https://example.com/robots.txt"
```

**Confirm these before implementing:**

- [ ] Pagination mechanism: `page=N`, `offset=N`, cursor-based, or link header?
- [ ] Maximum page size (try `limit=100`)
- [ ] Date filter: is there a `since`, `dateFrom`, or `f_TPR`-style parameter?
- [ ] Location/radius filter available server-side?
- [ ] Auth required? (Try without any auth headers first — NVB and LinkedIn guest API both work unauthenticated)
- [ ] Rate limiting: does adding `1–2s` sleep between pages avoid 429s?
- [ ] Empty-page sentinel: does an empty results array signal end-of-pages, or is there a `totalPages` field?

**Field mapping — identify the JSON key for each:**

| Our `Job` field | Typical API field names |
|-----------------|------------------------|
| `id` | `id`, `jobId`, `vacancy_id` |
| `title` | `title`, `jobTitle`, `name` |
| `company` | `company.name`, `employer`, `companyName` |
| `location` | `location.city`, `workLocation.city`, `city` |
| `date_posted` | `startDate`, `publishedAt`, `date`, `postedAt` |
| `apply_url` | `apply.url`, `url`, `_links.detail.href` |
| `description` | `description`, `body`, `summary` |

---

## Phase 3 — Validate Before Implementing

Before writing the fetcher, run a minimal Python test:

```python
import asyncio, httpx, json

async def test():
    async with httpx.AsyncClient(
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
        follow_redirects=True,
    ) as client:
        r = await client.get(
            "https://example.com/api/jobs",
            params={"q": "product manager", "location": "Amsterdam", "page": 1},
        )
        print(r.status_code)
        data = r.json()
        print(json.dumps(data, indent=2)[:2000])

asyncio.run(test())
```

Run with: `uv run python -c "..."` (project uses uv).

**Pass criteria before continuing:**
- Returns HTTP 200 with job data
- Job objects contain all required fields (title, company, location, date, apply URL)
- Pagination produces a second non-empty page

---

## Phase 4 — Implement the Fetcher

Create `job_scraper/src/fetchers/<source>.py`.

### Fetcher contract

Every fetcher must:
1. Be `async` and return `list[Job]`
2. Use `build_client()` from `..helpers` for the HTTP client
3. Apply `title_matches(title, function_title, keywords)` to filter off-topic listings
4. Apply `is_within_days(date_str, lookback_days)` to drop stale listings
5. Deduplicate within the run using a local `seen_keys: set[str]`
6. Never raise — catch exceptions and log them; return whatever was collected

### Template — JSON REST API (like nvb.py)

```python
"""
Fetcher for <SiteName>.

API: <endpoint URL>

KEY FINDINGS:
  - <document your reconnaissance findings here>
  - Auth: none / API key in header X-... / ...
  - Pagination: page= param, empty array = end of results
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

BASE_URL     = "https://example.com"
SEARCH_PATH  = "/api/jobs"

DEFAULT_CITY        = "Amsterdam"
DEFAULT_DISTANCE_KM = "40"
PAGE_SIZE     = 25
MAX_PAGES     = 6
LOOKBACK_DAYS = 14


async def fetch_<source>(
    queries: list[str] | None = None,
    lookback_days: int = LOOKBACK_DAYS,
    title_keywords: list[str] | None = None,
) -> list[Job]:
    """Fetch <SiteName> jobs. <Auth notes>."""
    title_keywords = title_keywords or load_title_keywords()
    fetched_at     = iso_ts(utc_now())
    jobs: list[Job] = []
    seen_keys: set[str] = set()

    async with build_client() as client:
        page = 1
        while page <= MAX_PAGES:
            try:
                resp = await client.get(
                    BASE_URL + SEARCH_PATH,
                    params={"q": "product manager", "location": DEFAULT_CITY, "page": page, "limit": PAGE_SIZE},
                )
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                logger.error("<source> error page %d: %s", page, e)
                break

            raw_jobs = data.get("jobs") or []   # adjust key to match actual API
            if not raw_jobs:
                break

            for raw in raw_jobs:
                if not is_within_days(raw.get("publishedAt"), lookback_days):
                    break   # newest-first: early exit

                if not title_matches(raw.get("title", ""), "", title_keywords):
                    continue

                job = _normalise(raw, fetched_at)
                if job is None:
                    continue
                if job.canonical_key in seen_keys:
                    continue
                seen_keys.add(job.canonical_key)
                jobs.append(job)

            page += 1

    logger.info("<source>: collected %d jobs", len(jobs))
    return jobs


def _normalise(raw: dict, fetched_at: str) -> Optional[Job]:
    job_id = str(raw.get("id") or "")
    title  = raw.get("title") or ""
    if not job_id or not title:
        return None

    company  = (raw.get("company") or {}).get("name") or raw.get("companyName") or ""
    city     = raw.get("city") or ""
    date_str = raw.get("publishedAt") or ""
    dt       = parse_iso(date_str)

    return Job(
        id            = job_id,
        source        = "<source>",
        title         = title,
        company       = company,
        location      = city,
        date_posted   = iso_date(dt) if dt else date_str,
        fetched_at    = fetched_at,
        description   = raw.get("description") or None,
        apply_url     = raw.get("url") or "",
        canonical_key = make_canonical_key(title, company, city),
    )
```

### Template — HTML scraping (like linkedin.py)

If the site returns HTML fragments (no JSON API found), use BeautifulSoup:

```python
from bs4 import BeautifulSoup
# Use client.get(..., headers={"Accept": "text/html, */*"})
# Parse with BeautifulSoup(resp.text, "lxml")
# Extract fields from CSS selectors found during reconnaissance
```

---

## Phase 5 — Register the Source

### 1. Update `pipeline.py`

```python
# Line ~19: add to the Literal type
Source = Literal["linkedin", "nvb", "<source>"]

# Line ~20: add to the list
ALL_SOURCES: list[Source] = ["linkedin", "nvb", "<source>"]

# In _fetch_source(), add a branch:
if source == "<source>":
    from .fetchers.<source> import fetch_<source>
    return await fetch_<source>(queries or None), None
```

### 2. Update `job_scraper/.env.example`

Add any new env vars (API keys, city, radius) with placeholder values and comments.

### 3. Update the Configuration table in `job-scraper/SKILL.md`

Add a row to the `## Configuration` table for each new env var.

---

## Phase 6 — Smoke Test

```bash
uv run python -m job_scraper --sources <source>
```

Check `job_scraper/last_run.json`:
- `errors` should be empty
- `sources.<source>` count > 0 (or 0 with a clear log message if no new jobs)
- Jobs have valid `title`, `company`, `location`, `date_posted`, `apply_url`

If errors appear, read the log output — the fetcher logs the HTTP status and error message per page.

---

## Checklist

- [ ] Phase 0: confirmed response type (JSON API / HTML / SPA)
- [ ] Phase 1: identified endpoint URL and required headers (if SPA)
- [ ] Phase 2: confirmed pagination, date filter, field names
- [ ] Phase 3: validated endpoint with a raw Python test
- [ ] Phase 4: created `job_scraper/src/fetchers/<source>.py`
  - [ ] Uses `build_client()`, `title_matches()`, `is_within_days()`
  - [ ] Catches all exceptions, never raises
  - [ ] Documents key findings in module docstring
- [ ] Phase 5: registered in `pipeline.py`, `.env.example`, `SKILL.md` config table
- [ ] Phase 6: smoke test passes (`uv run python -m job_scraper --sources <source>`)
