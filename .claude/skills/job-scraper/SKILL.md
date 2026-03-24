# Job Scraper

**name:** job-scraper
**description:** Searches Dutch job sites (Indeed NL, LinkedIn NL, Nationale Vacaturebank) for new positions matching your profile. Deduplicates across runs via a SQLite-backed Python pipeline. Triggers on: job scrape, find jobs, search jobs, new jobs, job search, scrape jobs, /scrape
**allowed-tools:** Read, Write, Edit, Glob, Grep, WebFetch, WebSearch, Agent, AskUserQuestion, Bash

---

## How It Works

The `job_scraper/` Python pipeline fetches jobs from three Dutch sources:
- **NVB** (Nationale Vacaturebank) — public API, no auth required, city-radius filters
- **Indeed NL** — via RapidAPI (jobs-api14); requires `RAPIDAPI_KEY` in `job_scraper/.env`
- **LinkedIn NL** — via RapidAPI (jobs-api14); same key as Indeed

State is stored in a SQLite database (`job_scraper/state.db`). A FastAPI server with APScheduler runs the pipeline on a daily schedule (Mon-Fri 07:00 Amsterdam time) and exposes a REST API for manual triggers and job queries.

## Invocation

The user triggers this skill by saying things like:
- "Find new jobs"
- "Scrape for jobs"
- "Any new positions?"
- "/scrape"

---

## Execution Steps

### Step 0: Check if the server is running

```bash
curl -s http://localhost:8000/api/status
```

If it returns a connection error, start the server first:

```bash
cd job_scraper && python -m ui.server &
```

Wait a moment, then proceed.

### Step 1: Trigger a pipeline run

```bash
# Run all sources
curl -s -X POST http://localhost:8000/api/run/now

# Or run a single source
curl -s -X POST http://localhost:8000/api/run/nvb
curl -s -X POST http://localhost:8000/api/run/indeed
curl -s -X POST http://localhost:8000/api/run/linkedin
```

The response is immediate (returns `{"status": "started"}`); the run executes in the background.

### Step 2: Wait and query results

Poll for completion (the run typically takes 15–60 seconds):

```bash
curl -s http://localhost:8000/api/status
```

Once `run_in_progress` is `false`, query new jobs:

```bash
# All jobs from the last 14 days
curl -s "http://localhost:8000/api/jobs?since=$(date -d '14 days ago' +%Y-%m-%d)"

# Or filter by source
curl -s "http://localhost:8000/api/jobs?source=nvb"
```

Check for errors:

```bash
curl -s http://localhost:8000/api/errors
```

### Step 3: Quick Fit Assessment

For each returned job, do a rapid fit check against the candidate's profile:

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

After presenting, ask:
> "Want me to evaluate any of these in detail? Just give me the number(s)."

If the user picks a number, invoke the **job-application-assistant** skill (fit evaluation first, then CV + cover letter if approved).

### Step 6: Update Tracker (Optional)

If the user decides to apply to any job, add a row to `job_search_tracker.csv`.

---

## Configuration

The pipeline reads from `job_scraper/.env`. Key variables:

| Variable | Purpose | Default |
|---|---|---|
| `RAPIDAPI_KEY` | API key for Indeed + LinkedIn (jobs-api14) | — required |
| `SEARCH_QUERIES` | Comma-separated queries for Indeed/LinkedIn | `product manager` |
| `NVB_DCO_TITLE` | NVB taxonomy title filter | `Productmanager` |
| `NVB_CITY` | City for NVB location radius | `Amsterdam` |
| `NVB_DISTANCE_KM` | Search radius in km | `40` |
| `TITLE_KEYWORDS` | Client-side title filter (all sources) | product manager variants |
| `DB_PATH` | SQLite database path | `job_scraper/state.db` |
| `PORT` | API server port | `8000` |

Copy `job_scraper/.env.example` to `job_scraper/.env` and fill in values before first use.

---

## Important Rules

1. **Never fabricate job postings.** Only present jobs returned by the actual pipeline.
2. **Respect deduplication.** The pipeline deduplicates via `state.db`; always cross-reference `job_search_tracker.csv` for applied roles.
3. **Focus on configured geographic area.** The pipeline already filters by location; flag any jobs outside the expected area.
4. **Only open positions.** Skip postings with expired deadlines or those marked as closed.
