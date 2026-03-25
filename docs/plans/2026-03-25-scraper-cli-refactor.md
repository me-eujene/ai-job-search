# Scraper CLI Refactor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the FastAPI/APScheduler server layer with a direct CLI entry point so Claude can trigger the scraper in-session with a single Bash command.

**Architecture:** `python -m job_scraper` runs the pipeline directly, writes new jobs to `job_scraper/last_run.json`, and exits. Claude reads that file with the Read tool. SQLite (`state.db`) remains the deduplication store, unchanged.

**Tech Stack:** Python stdlib only additions (`argparse`, `asyncio`, `json`); remove `fastapi`, `uvicorn`, `apscheduler`.

---

### Task 1: Create `job_scraper/__main__.py`

**Files:**
- Create: `job_scraper/__main__.py`

**Step 1: Write the file**

```python
"""
CLI entry point for the NL job scraper.

Usage (from repo root):
  python -m job_scraper                        # all sources
  python -m job_scraper --sources nvb          # one source
  python -m job_scraper --sources indeed nvb   # two sources
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from .src.pipeline import run_pipeline, ALL_SOURCES
from .src.state import get_jobs
from .src.helpers import iso_date, utc_now

OUTPUT_FILE = Path(__file__).parent / "last_run.json"


async def main() -> None:
    parser = argparse.ArgumentParser(description="NL Job Scraper")
    parser.add_argument(
        "--sources",
        nargs="+",
        choices=ALL_SOURCES,
        default=None,
        metavar="SOURCE",
        help=f"Sources to fetch. Choices: {', '.join(ALL_SOURCES)}. Default: all.",
    )
    args = parser.parse_args()

    summary = await run_pipeline(sources=args.sources)

    # Fetch jobs inserted during this run (filter by today's date — safe for a
    # single daily run; if two runs happen on the same day both are included,
    # which is acceptable for a personal tool).
    today = iso_date(utc_now())
    jobs = get_jobs(since=today)

    result = {**summary, "jobs": jobs}
    OUTPUT_FILE.write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(
        f"Run {summary['run_id']}: {summary['new_jobs']} new jobs "
        f"({summary['total_fetched']} fetched, {summary['skipped']} dupes). "
        f"Results → {OUTPUT_FILE}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    asyncio.run(main())
```

**Step 2: Verify it's importable (dry run — no API calls)**

```bash
cd D:\_coding\ai-job-search && python -c "import job_scraper"
```

Expected: no output, no import errors.

**Step 3: Commit**

```bash
git add job_scraper/__main__.py
git commit -m "feat: add CLI entry point, replace server layer with direct pipeline call"
```

---

### Task 2: Slim `requirements.txt`

**Files:**
- Modify: `job_scraper/requirements.txt`

**Step 1: Replace the file contents**

```
# NL Job Scraper — Python dependencies
# Install with: pip install -r job_scraper/requirements.txt

# HTTP
httpx>=0.27.0

# Environment variables
python-dotenv>=1.0.1
```

(Remove: `fastapi>=0.111.0`, `uvicorn[standard]>=0.29.0`, `apscheduler>=3.10.4`)

**Step 2: Verify no remaining imports of removed packages in src/**

```bash
grep -r "fastapi\|uvicorn\|apscheduler" D:\_coding\ai-job-search\job_scraper\src\
```

Expected: no matches.

**Step 3: Commit**

```bash
git add job_scraper/requirements.txt
git commit -m "chore: remove fastapi/uvicorn/apscheduler from dependencies"
```

---

### Task 3: Delete the `ui/` directory

**Files:**
- Delete: `job_scraper/ui/server.py`
- Delete: `job_scraper/ui/index.html`
- Delete: `job_scraper/ui/__init__.py`
- Delete: `job_scraper/ui/` (directory itself)

**Step 1: Delete the directory**

```bash
rm -rf "D:\_coding\ai-job-search\job_scraper\ui"
```

**Step 2: Verify it's gone**

```bash
ls "D:\_coding\ai-job-search\job_scraper\"
```

Expected: `ui/` is absent. `src/`, `__main__.py`, `requirements.txt`, `.env`, `state.db` remain.

**Step 3: Commit**

```bash
git add -A
git commit -m "chore: delete ui/ server layer (FastAPI dashboard + APScheduler)"
```

---

### Task 4: Add `last_run.json` to `.gitignore`

**Files:**
- Modify: `job_scraper/.gitignore`

**Step 1: Read current `.gitignore`**

Read `job_scraper/.gitignore` to see current contents.

**Step 2: Append the generated output file**

Add to `.gitignore`:
```
last_run.json
```

**Step 3: Commit**

```bash
git add job_scraper/.gitignore
git commit -m "chore: gitignore generated last_run.json"
```

---

### Task 5: Update `SKILL.md` — replace curl workflow with CLI workflow

**Files:**
- Modify: `.claude/skills/job-scraper/SKILL.md`

**Step 1: Replace the "How It Works" paragraph**

Old:
```
State is stored in a SQLite database (`job_scraper/state.db`). A FastAPI server with APScheduler runs the pipeline on a daily schedule (Mon-Fri 07:00 Amsterdam time) and exposes a REST API for manual triggers and job queries.
```

New:
```
State is stored in a SQLite database (`job_scraper/state.db`). The pipeline runs on demand — Claude triggers it directly with a Bash command. No server process is needed.
```

**Step 2: Replace the entire "Scraping Workflow" section**

Replace from `## Scraping Workflow` down to (and including) `If no jobs remain after tracker deduplication, say so and stop.` with:

```markdown
## Scraping Workflow

The user triggers the scraping workflow by saying things like:
- "Find new jobs"
- "Scrape for jobs"
- "Any new positions?"
- "/scrape"

### Step 1: Run the pipeline

```bash
cd D:\_coding\ai-job-search && python -m job_scraper
```

To run a single source: `python -m job_scraper --sources nvb`

Wait for the command to complete (typically 10–30 seconds). It writes results to `job_scraper/last_run.json`.

**If the command fails** (import error, missing `.env`, API key not set):
- Check `job_scraper/.env` exists and contains `RAPIDAPI_KEY`
- Check dependencies: `pip install -r job_scraper/requirements.txt`

### Step 2: Read results

Read `job_scraper/last_run.json`. The file contains:
- `run_id`, `started_at`, `finished_at` — run metadata
- `total_fetched`, `new_jobs`, `skipped` — counts
- `sources` — per-source counts
- `errors` — any fetch errors (empty list = clean run)
- `jobs` — array of new job objects (title, company, location, source, apply_url, date_posted, description)

**If `new_jobs` is 0**: Report that no new jobs were found this run and stop.
**If `errors` is non-empty**: Report the errors to the user alongside any results.

### Step 3: Quick Fit Assessment

Read `01-candidate-profile.md` and `02-behavioral-profile.md`. For each job in `jobs`, do a rapid fit check:

- **High match**: Role directly involves core skills
- **Medium match**: Role is adjacent to the candidate's experience
- **Low match**: Role requires significant skills the candidate lacks

### Step 4: Cross-reference with tracker

Read `job_search_tracker.csv` and skip any jobs whose company+title already appears there (already applied or evaluated).

### Step 5: Present Results

Present new jobs in a table sorted by fit (high first):

```
## New Job Matches — YYYY-MM-DD

Found X new positions (Y high, Z medium, W low match).

| # | Fit | Title | Company | Location | Date | URL |
|---|-----|-------|---------|----------|------|-----|
| 1 | High | ... | ... | ... | ... | [Link](...) |

### High-Match Highlights
For each high-match job, add 2-3 bullet points:
- Why it matches the candidate's profile
- Key requirements to check
- Any red flags
```

If no jobs remain after tracker deduplication, say so and stop.

After presenting, ask:
> "Want me to evaluate any of these in detail? Just give me the number(s)."

If the user picks a number, proceed with the **Application Workflow** below.
```

**Step 3: Remove the `PORT` variable from the Configuration table**

In the Configuration section, delete the row:
```
| `PORT` | API server port | `8000` |
```

**Step 4: Commit**

```bash
git add .claude/skills/job-scraper/SKILL.md
git commit -m "docs: update job-scraper skill for CLI workflow, remove server references"
```

---

### Task 6: Update `CLAUDE.md` — scraper workflow section

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Replace the "Workflow for Finding New Jobs" section**

Old:
```markdown
## Workflow for Finding New Jobs (Scraper)
1. Ensure the scraper server is running (`cd job_scraper && python -m ui.server`) and has completed at least one pipeline run
2. Say **"find new jobs"** or **"/scrape"** — the `job-scraper` skill queries the API, assesses fit against your profile, and deduplicates against `job_search_tracker.csv`
3. Review the results table; ask for a detailed evaluation on any interesting listing by number
4. If you want to apply, the skill flows directly into the application workflow below
```

New:
```markdown
## Workflow for Finding New Jobs (Scraper)
1. Say **"find new jobs"** or **"/scrape"** — the `job-scraper` skill runs the pipeline directly, reads the results, assesses fit against your profile, and deduplicates against `job_search_tracker.csv`
2. Review the results table; ask for a detailed evaluation on any interesting listing by number
3. If you want to apply, the skill flows directly into the application workflow below
```

**Step 2: Replace the scraper commands block**

Old:
```bash
# Start the scraper server
cd job_scraper && python -m ui.server

# Trigger a run manually
curl -s -X POST http://localhost:8000/api/run/now

# Query new jobs (last 14 days)
curl -s "http://localhost:8000/api/jobs?since=$(date -d '14 days ago' +%Y-%m-%d)"

# Check status / errors
curl -s http://localhost:8000/api/status
curl -s http://localhost:8000/api/errors
```

New:
```bash
# Run the scraper (all sources)
python -m job_scraper

# Run a single source
python -m job_scraper --sources nvb

# Results are written to job_scraper/last_run.json
```

**Step 3: Update the Architecture section**

In the `### Two-tier tool system` section, replace:

Old:
```
- **`job_scraper/`** — Python service with a REST API. Claude triggers it via `curl` and queries results via `/api/jobs`. Uses FastAPI + APScheduler; state in SQLite (`state.db`).
```

New:
```
- **`job_scraper/`** — Python CLI package. Claude runs `python -m job_scraper` directly via Bash. The pipeline fetches from external APIs, deduplicates against SQLite (`state.db`), and writes new jobs to `job_scraper/last_run.json` which Claude reads with the Read tool.
```

**Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md for CLI scraper workflow"
```

---

### Task 7: Smoke test end-to-end

**Step 1: Install slimmed dependencies**

```bash
pip install -r job_scraper/requirements.txt
```

**Step 2: Run with NVB only (no API key needed)**

```bash
cd D:\_coding\ai-job-search && python -m job_scraper --sources nvb
```

Expected stderr output: `Run YYYYMMDD_HHMMSS: N new jobs (M fetched, K dupes). Results → ...last_run.json`

**Step 3: Verify output file**

Read `job_scraper/last_run.json`. Confirm it contains `run_id`, `jobs` array, `errors: []`.

**Step 4: Commit if any fixes were needed, otherwise done.**
