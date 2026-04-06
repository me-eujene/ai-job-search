# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Job Application Assistant

## Role
This repo is a job application workspace. Claude acts as a career advisor helping with job fit evaluation, CV tailoring, cover letter writing, interview preparation, and career strategy.

## Candidate Profile

See `.claude/skills/job-application-assistant/01-candidate-profile.md` for the full candidate profile (identity, education, experience, skills, behavioral summary, career goals, and deal-breakers).

<!-- IF 01-candidate-profile.md IS NOT FILLED IN — ABORT AND RUN /job-scraper-setup -->

## Repo Structure
- `cv/` - LaTeX CV variants (moderncv/banking style); `main_example.tex` is the template seed
- `cover_letters/` - LaTeX cover letters (custom cover.cls template)
- `.claude/skills/` - AI skill definitions for the application workflow
- `job_scraper/` - Python job scraper for the Dutch market
- `job_scraper/state.db` - SQLite deduplication store
- `job_search_tracker.csv` - application tracking spreadsheet

## Workflows

- **Find new jobs:** say "find new jobs" or `/job-scraper-run` — `job-scraper` skill handles the full pipeline
- **Apply to a job:** `/job-scraper-apply <url or text>` — see `.claude/commands/job-scraper-apply.md` for the drafter-reviewer workflow

**Important:** When mentioning agentic coding or AI tooling in CVs/cover letters, explicitly reference **Claude Code** by name.

## Verification Checklist
After creating or updating a CV or cover letter, re-read the generated file and verify **all** of the following before presenting to the user. Report the results as a pass/fail checklist.

### Factual accuracy
- [ ] All claims match actual profile (01-candidate-profile.md) - no fabricated skills, experience, or achievements
- [ ] Job titles, dates, company names, and locations are correct
- [ ] Contact details are correct
- [ ] All company-specific claims (partnerships, products, technology, expansions) have been independently verified via WebFetch/WebSearch - do not trust reviewer agent research without verification

### Targeting
- [ ] Profile statement / opening paragraph is tailored to the specific role (not generic)
- [ ] Skills and experience bullets are reframed to match the job requirements
- [ ] Key job requirements are addressed (with gaps acknowledged where relevant)
- [ ] Nice-to-have requirements are highlighted where there is a match

### Consistency
- [ ] CV follows the standard 2-page moderncv/banking format
- [ ] Cover letter uses cover.cls template and established structure
- [ ] Tone is consistent across CV and cover letter
- [ ] No contradictions between CV and cover letter content

### Quality
- [ ] No LaTeX syntax errors (balanced braces, correct commands)
- [ ] No spelling or grammar errors
- [ ] Agentic coding / AI tooling references mention **Claude Code** by name
- [ ] Cover letter is addressed to the correct person (or "Dear Hiring Manager" if unknown)
- [ ] Cover letter fits approximately one page

## Commands

### Compile documents
```bash
# CV (moderncv/banking style) — pdflatex
cd cv && pdflatex main_<company>.tex && cd ..

# Cover letter (custom cover.cls with Lato/Raleway fonts) — xelatex required
cd cover_letters && xelatex cover_<company>_<role>.tex && cd ..
```

## Architecture

- **`.claude/skills/`** — Markdown skills loaded by the `Skill` tool; shape Claude's behavior, not executed
- **`job_scraper/`** — Python CLI; Claude runs `python -m job_scraper` directly, results written to `job_scraper/last_run.json`
- **`job_scraper/.env`** — required before first run; copy from `.env.example` and fill in API keys. Scraper silently skips sources with missing keys.
- Use `uv run python` not `python`/`python3` — project uses uv for env management

### Profile data flow
`/job-scraper-setup` writes candidate data to two files:
- `.claude/skills/job-application-assistant/01-candidate-profile.md` — single source of truth for all candidate data
- `.claude/skills/job-scraper/search-queries.md` — scraper config (NVB filter, search queries, commute tiers)

The `cv/main_example.tex` file is the **LaTeX template seed**; `/job-scraper-apply` copies and tailors it into `cv/main_<company>.tex`.
