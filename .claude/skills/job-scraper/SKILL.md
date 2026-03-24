---
name: job-scraper
description: "Searches Dutch job sites (Indeed NL, LinkedIn NL, Nationale Vacaturebank) for new positions, evaluates fit, and assists with applications: tailoring CVs, writing cover letters, and preparing for interviews. Triggers on: job scrape, find jobs, search jobs, new jobs, job search, scrape jobs, /scrape, job posting, job application, CV, cover letter, resume, interview prep, job fit, career, application, apply"
allowed-tools: "Read, Write, Edit, Glob, Grep, WebFetch, WebSearch, Agent, AskUserQuestion, Bash"
---

# Job Search & Application Assistant

## How It Works

The `job_scraper/` Python pipeline fetches jobs from three Dutch sources:
- **NVB** (Nationale Vacaturebank) — public API, no auth required, city-radius filters
- **Indeed NL** — via RapidAPI (jobs-api14); requires `RAPIDAPI_KEY` in `job_scraper/.env`
- **LinkedIn NL** — via RapidAPI (jobs-api14); same key as Indeed

State is stored in a SQLite database (`job_scraper/state.db`). A FastAPI server with APScheduler runs the pipeline on a daily schedule (Mon-Fri 07:00 Amsterdam time) and exposes a REST API for manual triggers and job queries.

---

## Scraping Workflow

The user triggers the scraping workflow by saying things like:
- "Find new jobs"
- "Scrape for jobs"
- "Any new positions?"
- "/scrape"

The scraper server and pipeline run are managed externally (scheduled daily or triggered manually by the user). This skill assumes data has already been collected and queries it directly.

### Step 1: Check data availability

Query the API for jobs from the last 14 days:

```bash
curl -s "http://localhost:8000/api/jobs?since=YYYY-MM-DD"
```

Substitute a date 14 days before today for `YYYY-MM-DD`.

**If the server is unreachable** (connection refused / no response):
> "The scraper server doesn't appear to be running. Please start it with `cd job_scraper && python -m ui.server` and trigger a run with `curl -X POST http://localhost:8000/api/run/now`, then try again."
Stop here.

**If the server responds but returns zero jobs:**
Check the last run timestamp via `curl -s http://localhost:8000/api/status` and errors via `curl -s http://localhost:8000/api/errors`.
- If the last run was more than 3 days ago, or if there are pipeline errors: prompt the user to trigger a fresh scrape (`curl -X POST http://localhost:8000/api/run/now`) and stop.
- If the last run was recent and there are no errors: report that no new jobs were found and stop.

**If jobs are returned**, proceed to Step 2.

### Step 2: Quick Fit Assessment

Read `01-candidate-profile.md` and `02-behavioral-profile.md`. For each returned job, do a rapid fit check:

- **High match**: Role directly involves core skills
- **Medium match**: Role is adjacent to the candidate's experience
- **Low match**: Role requires significant skills the candidate lacks

### Step 3: Cross-reference with tracker

Read `job_search_tracker.csv` and skip any jobs whose company+title already appears there (already applied or evaluated).

### Step 4: Present Results

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

---

## Application Workflow

When the user provides a job posting (URL or text), or selects a job from scrape results, follow this workflow.

### Step 1: Research & Evaluate Fit
- Fetch the job posting content (use WebFetch for URLs)
- Analyze the posting for required competencies, keywords, and priorities
- Research the company (website, LinkedIn, mission, recent news)
- Score the posting against the candidate's profile using the framework in `04-job-evaluation.md`
- Present the evaluation table and verdict
- Suggest whether the candidate should call the employer before applying (see `04-job-evaluation.md` for guidance)
- Ask the user if they want to proceed with an application

**If the user declines**, stop here.

### Step 2: Tailor CV

_Only proceed if the user confirmed they want to apply._

- Read the candidate's existing CVs from `cv/docs/` (`.docx` or `.pdf` files) as baseline content — these are the source of truth for experience, dates, and phrasing
- List existing LaTeX variants in `cv/` and pick the most recently modified tailored file as the structural starting point, or `cv/main_example.tex` if none exist
- Follow the guidelines in `05-cv-templates.md`
- Create `cv/main_<company>.tex` with tailored content
- Adjust: profile statement, skills section, experience bullet emphasis, section order

### Step 3: Write Cover Letter
- Follow the writing style rules in `03-writing-style.md` (critical: no em-dashes, no cliches)
- Follow the template structure in `06-cover-letter-templates.md`
- Create `cover_letters/cover_<company>_<role>.tex`
- Ensure the letter connects specific experience to the role requirements

### Step 4: Update Tracker

Add a row to `job_search_tracker.csv` for this application (company, role, date, status = "drafted").

### Step 5: Offer Interview Preparation

After delivering the CV and cover letter, ask:
> "Want me to prepare interview talking points for this role?"

If yes:
- Follow the framework in `07-interview-prep.md`
- Prepare STAR-format answers for likely questions
- Identify role-specific talking points
- Draft questions the candidate should ask the interviewer

---

## Reference Files

| File | Purpose |
|------|---------|
| `01-candidate-profile.md` | Education, experience, skills, publications, awards |
| `02-behavioral-profile.md` | Behavioral assessment, strengths, ideal environments |
| `03-writing-style.md` | Tone, structure, do's and don'ts |
| `04-job-evaluation.md` | Scoring framework for job fit |
| `05-cv-templates.md` | LaTeX CV structure and tailoring rules |
| `06-cover-letter-templates.md` | LaTeX cover letter structure and tailoring rules |
| `07-interview-prep.md` | STAR examples, tough questions, roleplay guidelines |

---

## Quick Commands

The user may ask for individual steps without running the full workflow:
- "Evaluate this job posting" — Application Step 1 only
- "Write a CV for [company]" — Run Application Step 1 first to fetch the posting and extract role requirements, then proceed directly to Step 2 without asking whether to continue.
- "Write a cover letter for [role] at [company]" — Application Step 3 only. Same prerequisite: a job posting must be in context.
- "Help me prepare for an interview at [company]" — Application Step 5 only
- "What jobs should I look for?" — Career strategy discussion. Read `01-candidate-profile.md`, `02-behavioral-profile.md`, and `04-job-evaluation.md`. Discuss target roles, sectors, deal-breakers, and positioning.

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
