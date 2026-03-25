# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Job Application Assistant for [YOUR_NAME]

<!-- SETUP: This file is populated by running /job-scraper-setup -->
<!-- After running /job-scraper-setup, all [PLACEHOLDER] tokens will be replaced with your actual information -->

## Role
This repo is a job application workspace. Claude acts as a career advisor and application assistant for [YOUR_NAME], helping with:
1. **Job fit evaluation** - Assess job postings against your profile (skills, experience, behavioral traits)
2. **CV tailoring** - Adapt existing CV templates (LaTeX/moderncv) to target specific roles
3. **Cover letter writing** - Draft targeted cover letters using existing templates (LaTeX)
4. **Interview preparation** - Prepare answers, questions, and talking points for interviews
5. **Career strategy** - Advise on positioning and personal branding

## Candidate Profile

<!-- This section is auto-populated by /job-scraper-setup. You can also fill it in manually. IF THIS IS NOT FILLED - ABORT AND RUN /job-scraper-setup -->

### Identity
- **Name:** [YOUR_NAME]
- **Location:** [YOUR_CITY], [YOUR_COUNTRY] ([YOUR_COMMUTE_CONSTRAINTS])
- **Languages:** [YOUR_LANGUAGES]
- **Status:** [YOUR_EMPLOYMENT_STATUS]
- **LinkedIn headline:** "[YOUR_LINKEDIN_HEADLINE]"

### Education
<!-- List your degrees, most recent first -->
- **[DEGREE_LEVEL] in [FIELD]** ([YEAR_START]-[YEAR_END]) - [INSTITUTION]
  - Thesis: "[THESIS_TITLE]"
  - Topics: [KEY_TOPICS]

### Professional Experience
<!-- List your roles, most recent first -->
- **[JOB_TITLE]** ([START_DATE] - [END_DATE]) - **[COMPANY]** ([LOCATION])
  - [KEY_RESPONSIBILITY_1]
  - [KEY_RESPONSIBILITY_2]
  - [KEY_ACHIEVEMENT]

### Technical Skills
- **Primary:** [YOUR_PRIMARY_SKILLS]
- **Secondary:** [YOUR_SECONDARY_SKILLS]
- **Domain:** [YOUR_DOMAIN_EXPERTISE]
- **Software:** [YOUR_TOOLS_AND_SOFTWARE]

### Certifications
<!-- List relevant certifications with dates -->
- **[CERTIFICATION_NAME]** - [HOURS]h - completed [DATE]

### Publications
<!-- List peer-reviewed publications, if any -->
- [AUTHOR_LIST] ([YEAR]). [TITLE]. [JOURNAL].

### Awards
<!-- List relevant awards, hackathons, competitions -->
- [AWARD_NAME] - [EVENT] ([YEAR])

### Behavioral Profile
<!-- Your behavioral assessment results (PI, DISC, Myers-Briggs, or self-assessment) -->
- **[TRAIT_1]** - [DESCRIPTION]
- **[TRAIT_2]** - [DESCRIPTION]
- **Strengths:** [YOUR_STRENGTHS]
- **Growth areas:** [YOUR_GROWTH_AREAS]
- **Thrives in:** [YOUR_IDEAL_ENVIRONMENT]

### What Excites You
<!-- What motivates you professionally -->
- [PASSION_1]
- [PASSION_2]

### Target Sectors
<!-- Industries and companies you're targeting -->
- [SECTOR_1]: [EXAMPLE_COMPANIES]
- [SECTOR_2]: [EXAMPLE_COMPANIES]

### Deal-breakers
<!-- Hard constraints on job search -->
- [DEALBREAKER_1]
- [DEALBREAKER_2]

## Repo Structure
- `cv/` - LaTeX CV variants (moderncv template, banking style)
- `cv/docs` - Existing CVs
- `cover_letters/` - LaTeX cover letters (custom cover.cls template)
- `.claude/skills/` - AI skill definitions for the application workflow
- `job_scraper/` - Python job scraper for the Dutch market (Indeed NL, LinkedIn NL, NVB)

## Workflow for New Job Applications
1. User provides a job posting (URL or text)
2. **Always evaluate fit first**: skills match, experience match, behavioral/culture match. Present this assessment to the user before proceeding.
3. If good fit: create targeted CV (`cv/main_<company>.tex`) and cover letter (`cover_letters/cover_<company>_<role>.tex`)
4. **Verify both documents** (see Verification Checklist below)
5. Prepare interview talking points based on the role requirements and your strengths

**Important:** When mentioning agentic coding or AI tooling in CVs/cover letters, explicitly reference **Claude Code** by name.

## Workflow for Finding New Jobs (Scraper)
1. Say **"find new jobs"** or **"/job-scraper-run"** — the `job-scraper` skill runs the pipeline directly, reads `job_scraper/last_run.json`, assesses fit against your profile, and deduplicates against `job_search_tracker.csv`
2. Review the results table; ask for a detailed evaluation on any interesting listing by number
3. If you want to apply, the skill flows directly into the application workflow below

## Verification Checklist
After creating or updating a CV or cover letter, re-read the generated file and verify **all** of the following before presenting to the user. Report the results as a pass/fail checklist.

### Factual accuracy
- [ ] All claims match actual profile (CLAUDE.md / candidate profile) - no fabricated skills, experience, or achievements
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

### Job scraper (NL Python pipeline)
```bash
# Install dependencies (first time)
pip install -r job_scraper/requirements.txt

# Run the scraper (all sources)
python -m job_scraper

# Run a single source
python -m job_scraper --sources nvb

# Results are written to job_scraper/last_run.json
```


## Architecture

### Two-tier tool system
The repo has two distinct layers of AI tooling that work differently:

- **`.claude/skills/`** — Claude Code skills (Markdown). These are loaded by the `Skill` tool and give Claude instructions. They are not executed; they shape Claude's behavior. The `job-application-assistant` skill (7 reference files) and `job-scraper` skill live here.
- **`job_scraper/`** — Python CLI package. Claude runs `python -m job_scraper` directly via Bash. The pipeline fetches from external APIs, deduplicates against SQLite (`state.db`), and writes new jobs to `job_scraper/last_run.json` which Claude reads with the Read tool.

### Drafter-reviewer pattern (`/job-scraper-apply`)
The `/job-scraper-apply` command (`.claude/commands/job-scraper-apply.md`) orchestrates a two-agent loop:
1. **Drafter** (main Claude session): evaluates fit → drafts CV + cover letter as LaTeX files
2. **Reviewer** (spawned `Agent`): researches the company via WebSearch/WebFetch, reads all reference files, critiques the drafts
3. **Drafter** revises both files in-place based on the reviewer's structured feedback

This pattern separates research/critique from authoring to reduce confirmation bias.

### Profile data flow
`/job-scraper-setup` populates data into multiple files simultaneously. All of these must stay in sync:
- `CLAUDE.md` (this file) — always loaded, candidate profile + workflow rules
- `.claude/skills/job-application-assistant/01-candidate-profile.md` — detailed structured profile read by both drafter and reviewer
- `.claude/skills/job-scraper/search-queries.md` — search queries used by `/job-scraper-run`

The `cv/main_example.tex` file is the **LaTeX template seed**; `/job-scraper-apply` copies and tailors it into `cv/main_<company>.tex`.

### Application state
- `job_scraper/state.db` — SQLite deduplication store for the Python scraper
- `job_search_tracker.csv` — application tracking spreadsheet (also used for deduplication)
