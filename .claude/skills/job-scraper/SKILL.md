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

State is stored in a SQLite database (`job_scraper/state.db`). The pipeline runs on demand — Claude triggers it directly with a Bash command from the repo root. No server process is needed.

---

## Scraping Workflow

The user triggers the scraping workflow by saying things like:
- "Find new jobs"
- "Scrape for jobs"
- "Any new positions?"
- "/scrape"

### Step 1: Run the pipeline

From the repo root:
```bash
python -m job_scraper
```

To run a single source: `python -m job_scraper --sources nvb`

Wait for the command to complete (typically 10–30 seconds). It writes results to `job_scraper/last_run.json`.

**If the command fails** (import error, missing `.env`, API key not set):
- Check `job_scraper/.env` exists; if running Indeed/LinkedIn, ensure `RAPIDAPI_KEY` is set (NVB works without it)
- Check dependencies are installed: `pip install -r job_scraper/requirements.txt`

### Step 2: Read results

Read `job_scraper/last_run.json`. The file contains:
- `run_id`, `started_at`, `finished_at` — run metadata
- `total_fetched`, `new_jobs`, `skipped` — counts
- `sources` — per-source counts (e.g. `{"indeed": 3, "nvb": 2}`)
- `errors` — any fetch errors (empty list = clean run)
- `jobs` — array of new job objects: `title`, `company`, `location`, `source`, `apply_url`, `date_posted`, `description`

**If `new_jobs` is 0**: Report that no new jobs were found and stop.
**If `errors` is non-empty**: Report errors alongside any results found.

### Step 3: Quick Fit Assessment

Read the candidate profile files. For each job in `jobs`, do a rapid fit check:

- **High match**: Role directly involves core skills
- **Medium match**: Role is adjacent to the candidate's experience
- **Low match**: Role requires significant skills the candidate lacks

### Step 4: Cross-reference with tracker

Read `job_search_tracker.csv` and skip any jobs whose company+title already appears there (already applied or evaluated).

### Step 4b: Apply blocklist

Read the deal-breakers list from `CLAUDE.md`. Silently drop any job whose company name matches a blocklisted company. Do not include dropped jobs in counts or mention them.

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
| `RAPIDAPI_KEY` | API key for Indeed + LinkedIn (jobs-api14) | — required for Indeed/LinkedIn; NVB works without it |
| `SEARCH_QUERIES` | Comma-separated queries for Indeed/LinkedIn | `product manager` |
| `NVB_DCO_TITLE` | NVB taxonomy title filter | `Productmanager` |
| `NVB_CITY` | City for NVB location radius | `Amsterdam` |
| `NVB_DISTANCE_KM` | Search radius in km | `40` |
| `TITLE_KEYWORDS` | Client-side title filter (all sources) | product manager variants |
| `DB_PATH` | SQLite database path | `job_scraper/state.db` |

Copy `job_scraper/.env.example` to `job_scraper/.env` and fill in values before first use.

---

## Important Rules

1. **Never fabricate job postings.** Only present jobs returned by the actual pipeline.
2. **Respect deduplication.** The pipeline deduplicates via `state.db`; always cross-reference `job_search_tracker.csv` for applied roles.
3. **Focus on configured geographic area.** The pipeline already filters by location; flag any jobs outside the expected area.
4. **Only open positions.** Skip postings with expired deadlines or those marked as closed.
