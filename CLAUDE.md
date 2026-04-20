# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Job Application Assistant

## Role
This repo is a job application workspace. Claude acts as a career advisor helping with job fit evaluation, CV tailoring, cover letter writing, interview preparation, and career strategy.

## Candidate Profile

See `.claude/skills/job-application-assistant/01-candidate-profile.md` for the full candidate profile (identity, education, experience, skills, behavioral summary, career goals, and deal-breakers).

<!-- IF 01-candidate-profile.md IS NOT FILLED IN — ABORT AND RUN /job-scraper-setup -->

## Repo Structure

- `cv/` — LaTeX CV variants (moderncv/banking style); `main_example.tex` is the template seed
- `cover_letters/` — LaTeX cover letters (custom cover.cls template)
- `applications/<company>-<role>/` — per-role application folder; contains `eval.md`, `cv.md`, `cover.md`, rendered `.tex` files, and compiled PDFs
- `.claude/skills/` — AI skill definitions for the application workflow
- `.claude/commands/` — slash command orchestrators
- `job_scraper/` — Python job scraper for the Dutch market
- `job_scraper/state.db` — SQLite deduplication store
- `job_search_tracker.csv` — application tracking spreadsheet

## Workflows

- **Find and apply to jobs:** `/search` — full pipeline: fetch → batch assess → shortlist → per-role apply (interview → draft → review → revise → render)
- **Apply to a specific role directly:** `/job-scraper-apply <url or text>` — skips fetch/batch, evaluates one role and runs the apply flow
- **Set up your profile:** `/job-scraper-setup` — required before first use

**Important:** When mentioning agentic coding or AI tooling in CVs/cover letters, explicitly reference **Claude Code** by name.

## Pipeline Overview

Two entry points:
- `/search` — full pipeline: runs scraper, then Phases 0–8
- `/job-scraper-apply <url or text>` — single-role shortcut: skips Phases 0–2, starts at Phase 3 with the provided posting

---

### Phase 0: Fetch

```bash
uv run python -m job_scraper
```

Read `job_scraper/last_run.json`.

| Condition | Action |
|-----------|--------|
| `new_jobs == 0`, no errors | Tell user. Ask: proceed with previously fetched jobs, or exit. |
| `new_jobs == 0`, errors present | Report errors. Ask: fix scraper, or proceed with old jobs. |
| `new_jobs > 0`, errors present | Report which sources errored. Continue with fetched jobs. |
| `new_jobs > 0`, no errors | Proceed to Phase 1. |

Each job object contains: `title`, `company`, `location`, `source`, `apply_url`, `date_posted`, `description` (plain text), `description_ok` (bool), `canonical_key`.

---

### Phase 1: Assess

For each job, check description before invoking `job-evaluate`:

| Condition | Action |
|-----------|--------|
| `description_ok: true` | Invoke `job-evaluate` with the description. |
| `description_ok: false`, direct job page URL | Attempt `WebFetch(apply_url)`. If substantive, use it. Otherwise treat as thin. |
| `description_ok: false`, ATS redirect (Greenhouse, Workday, SmartRecruiters, SuccessFactors, Lever) | Skip WebFetch. Mark job `[thin]`. |
| WebFetch fails (403/503) | Mark job `[thin]`. |

`[thin]` jobs carry forward to the shortlist without a fit score — do not evaluate them.

**`job-evaluate` skill** — input: job object + description text. Reads `01-candidate-profile.md` and `04-job-evaluation.md`. Returns an eval object and writes `applications/<folder>/eval.md`. Does not ask "should I proceed?" in batch — that belongs in Phase 2.

Collect all eval objects. Proceed when all jobs are assessed.

---

### Phase 2: Shortlist

Rank evaluated roles by `fit_score` descending. `[thin]` jobs appear at the bottom unscored.

| Job state | Display |
|-----------|---------|
| Normal | Ranked row with score and recommendation |
| `deal_breakers` non-empty | Flagged `[deal-breaker]` — shown, not hidden |
| `fit_score < 4` | Flagged `[weak fit]` — shown at bottom |
| `[thin]` | "Limited description — open link before deciding." No score. |

Ask: "Which role would you like to apply to? Enter a number, or 'done' to exit."

**State carried forward into Phase 3:** eval object, full job posting text, folder path (`applications/<folder>/`).

The shortlist stays active for the full session — user can return to it after each application.

---

### Phase 3–4: Interview + Draft

**`job-writer` skill** — input: eval object, job posting text, folder path.

Conducts: opening brief → voice interview (2 questions) → authenticity interview (2 questions) → framing checkpoint (user approves angle) → drafts `cv.md` and `cover.md`.

Reads: `01-candidate-profile.md`, `03-writing-style.md`, `05-cv-templates.md`, `06-cover-letter-templates.md`.

**State returned to pipeline after Phase 4:** `voice_inputs`, `authenticity_inputs`, `framing_approval`.

---

### Phase 5: Review

Load **`job-reviewer` skill** to get the reviewer prompt template. Fill all placeholders:

| Placeholder | Source |
|-------------|--------|
| `INSERT_VOICE_INPUTS` | Phase 4 `voice_inputs` |
| `INSERT_AUTHENTICITY_INPUTS` | Phase 4 `authenticity_inputs` |
| `INSERT_FRAMING_APPROVAL` | Phase 4 `framing_approval` |
| `INSERT_FOLDER` | folder path |
| `INSERT_JOB_POSTING_TEXT` | full posting text |

Spawn a `general-purpose` agent via the Agent tool with the filled prompt.

**State returned after Phase 5:** `critique` — structured feedback from the reviewer agent.

---

### Phase 6: Revise

**`job-writer` skill** with `mode: revise` — input: eval object, posting text, `voice_inputs`, `authenticity_inputs`, `framing_approval`, `critique`. Edits `cv.md` and `cover.md` in place.

---

### Phase 7: User edit loop

> "Drafts are at `applications/<folder>/cv.md` and `applications/<folder>/cover.md`. Edit them directly and paste comments here, or say 'done' to render."

If user pastes comments: invoke `job-writer` with `mode: revise`, `user_comments` set to their input. Repeat until "done".

---

### Phase 8: Render

**`latex-renderer` skill** — input: folder path. Reads `cv.md`, `cover.md`, `01-candidate-profile.md`, `07-latex-renderer-rules.md`, `cv/main_example.tex`. Writes `.tex` files and compiles PDFs.

After rendering: show file paths and verification checklist results.

---

### Return to shortlist

> "Application for [Role] at [Company] complete. Want to apply to another role?"

If yes: return to Phase 2. If no: end session.

## Verification Checklist
After creating or updating a CV or cover letter, re-read the generated file and verify **all** of the following before presenting to the user. Report the results as a pass/fail checklist.

### Factual accuracy
- [ ] All claims match actual profile (01-candidate-profile.md) — no fabricated skills, experience, or achievements
- [ ] Job titles, dates, company names, and locations are correct
- [ ] Contact details are correct
- [ ] All company-specific claims (partnerships, products, technology, expansions) have been independently verified via WebFetch/WebSearch — do not trust reviewer agent research without verification

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

### Skills (loaded by the Skill tool)

| Skill | Role |
|-------|------|
| `job-application-assistant/01-candidate-profile.md` | Candidate data — single source of truth |
| `job-application-assistant/02-behavioral-profile.md` | Behavioral assessment detail |
| `job-application-assistant/03-writing-style.md` | Tone, anti-patterns, writing rules |
| `job-application-assistant/04-job-evaluation.md` | Fit scoring framework |
| `job-application-assistant/05-cv-templates.md` | Editorial CV guidance (section order, content rules) |
| `job-application-assistant/06-cover-letter-templates.md` | Editorial cover letter guidance |
| `job-application-assistant/07-latex-renderer-rules.md` | LaTeX rendering spec — md→tex mapping, escape rules, compile instructions |
| `job-application-assistant/08-writing-style-review.md` | Reviewer checklist — writing style, tone, authenticity, and fabrication guard |
| `job-application-assistant/09-interview-prep.md` | STAR examples, interview coaching |
| `job-evaluate/SKILL.md` | Parse posting, score fit, write eval.md |
| `job-writer/SKILL.md` | Interview candidate, draft cv.md + cover.md, handle revisions |
| `job-reviewer/SKILL.md` | Independent reviewer prompt template (spawned as agent) |
| `latex-renderer/SKILL.md` | Convert cv.md/cover.md → .tex → compile PDF |

### Commands

| Command | Role |
|---------|------|
| `search.md` | Entry point for `/search` — triggers the full pipeline defined above |
| `job-scraper-apply.md` | Entry point for `/job-scraper-apply` — triggers single-role flow from Phase 3 |
| `job-scraper-setup.md` | Profile onboarding interview |

### Infrastructure

- **`job_scraper/`** — Python CLI; run via `uv run python -m job_scraper`, results written to `job_scraper/last_run.json`
- **`job_scraper/.env`** — required before first run; copy from `.env.example` and fill in API keys. Scraper silently skips sources with missing keys.
- Use `uv run python` not `python`/`python3` — project uses uv for env management

### Profile data flow

`/job-scraper-setup` writes candidate data to two files:
- `.claude/skills/job-application-assistant/01-candidate-profile.md` — single source of truth for all candidate data
- `.claude/skills/job-scraper/search-queries.md` — scraper config (NVB filter, search queries, commute tiers)

### Editorial vs rendering separation

- **Editorial work** happens in `cv.md` and `cover.md` (plain markdown, human-readable)
- **LaTeX rendering** is a mechanical final step: `latex-renderer` skill converts markdown → `.tex` → PDF
- Do not edit `.tex` files directly for content changes — edit the `.md` source and re-render

The `cv/main_example.tex` file is the **LaTeX template seed** used by the renderer as structural reference.
