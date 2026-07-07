# /job-scraper-setup - Profile Onboarding Interview

You are running the onboarding setup for the AI Job Search framework. Your goal is to collect the user's professional information and populate all profile files so the `/job-scraper-apply` workflow works out of the box.

---

## Step 0: Welcome & Choose Path

Welcome the user and explain what this setup does. Then offer two paths:

> **Welcome to the AI Job Search setup!**
>
> I'll help you set up your professional profile so Claude can evaluate job postings, tailor CVs, write cover letters, and prepare you for interviews.
>
> **Two ways to get started:**
>
> **Path A: Import from CV (recommended)** - Share your existing CV or resume (mention the file with @ or paste the text). I'll extract your information automatically and ask follow-up questions for anything missing.
>
> **Path B: Interview mode** - I'll walk you through structured questions section by section. Great if you're starting from scratch.
>
> Which do you prefer?

If the user specifies `$ARGUMENTS` containing `--section <name>`, skip to that section only for updating.

---

## Path A: Document Import

If the user provides a CV/resume:

1. Read the document thoroughly
2. Extract all structured information: name, contact, education, experience, skills, publications, awards
3. Present a summary of what was extracted
4. Ask follow-up questions for gaps (behavioral profile, career goals, deal-breakers, salary expectations, references)
5. Complete Section 9 (Job Search Configuration) — this step is mandatory even in Path A. Ask about target job titles, key skills as search terms, geographic scope, and scraper configuration. Then proactively suggest role types the user may not have considered (see Section 9 below).
6. Proceed to file generation (Step 3)

---

## Path B: Interview Mode

Walk through each section conversationally. Ask questions naturally, not as a form. Let the user answer in their own words and you'll structure the data.

### Section 1: Identity & Contact
Ask about:
- Full name
- Location (city, country)
- Phone, email, LinkedIn, GitHub
- Languages spoken (with proficiency levels)
- Current employment status
- Family/commute constraints (if any)

### Section 2: Education
For each degree:
- Level (PhD, MSc, BSc, etc.), field, institution, years
- Thesis topic (if applicable)
- Key coursework or topics

Also ask about certifications (online courses, professional certs).

### Section 3: Professional Experience
For each role (most recent first):
- Job title, company, dates, location
- Key responsibilities (3-5 bullets)
- Key achievements or projects
- Technologies/tools used

Also ask about independent projects, freelance work, or side projects.

### Section 4: Technical Skills
- Programming languages + proficiency level
- ML/AI frameworks and tools
- Domain expertise
- Software tools and platforms
- Any other technical skills

For each skill or tool mentioned across Sections 3–4, classify it (silently, don't turn this into a form) into one of three claim types — you'll need this for Section 4.5:
- `capability`: backed by shipped, evidence-bearing work in Experience — safe to lead a CV bullet or competency with
- `exposure`: used only in a side project, once, or at prototype depth — never a standalone competency
- `hygiene`: baseline tooling/role craft (Jira, Git, Scrum, stakeholder management, etc.) — never printed, kept only for ATS keyword coverage

### Section 4.5: Core Definition & Claims Inventory

This section produces the two artifacts every other skill (writing style, CV templates, reviewer) depends on: the **Core Definition** (single-line identity) and the **Claims Inventory** (capability/exposure/hygiene classification with tiers).

1. **Core Definition:** Synthesize one sentence describing *what kind of professional* the candidate is — never an achievement, never a list of domains, no "N+ years". Draft it, show it to the user, and iterate until they confirm it's exact. This line will be used verbatim everywhere; get it right here.
2. **Claims Inventory — differentiators:** From the skills classified above, pick 3–6 `capability` claims that most set the candidate apart from other applicants in their target roles. Each needs: a short name, what it means in one clause, and the specific Experience entries that serve as evidence.
3. **Claims Inventory — supporting:** Remaining `capability` claims that strengthen the story but don't lead it.
4. **Exposure:** List side-project-only tech/tools with a one-line note on where they may appear (Personal Projects entry only).
5. **Hygiene:** List baseline tooling/role craft — confirm with the user this list is never meant to appear on the CV itself.
6. **Framing Notes:** Ask "Are there a few different types of roles you're targeting that call for different emphasis?" (e.g., technical vs. domain vs. leadership-leaning). For each named role-type, write one line on which Experience/Capability to lead with. Add a "Core positioning across all roles" line — the one sentence that should stay consistent no matter which template is used.

### Section 5: Publications & Awards (optional)
- Peer-reviewed papers, conference presentations
- Hackathons, competitions, awards
- Skip if not applicable

### Section 6: Behavioral Profile (optional)
If they have a formal assessment (PI, DISC, Myers-Briggs, StrengthsFinder):
- Ask them to describe or share the results

If not, ask behavioral questions:
- "What work environments do you thrive in?"
- "What drains your energy at work?"
- "How do you prefer to work in teams?"
- "How do you make decisions - quickly or deliberately?"
- "What's your communication style?"
- Synthesize answers into a behavioral profile

### Section 7: Career Goals & Preferences
- Target roles and industries
- What excites you in work
- Deal-breakers and must-haves
- Salary expectations/baseline (optional)
- What environments to avoid
- Commute/location constraints

### Section 8: References (optional)
For each reference:
- Name, title, company, email, phone
- Relationship to the user

### Section 9: Job Search Configuration
This section generates the search queries that power `/search`. Use the information from Sections 1, 4, and 7 to build targeted queries.

Ask about:
- **Role titles to search for:** "What job titles should I search for? For example: Data Scientist, ML Engineer, Geophysicist." Collect 3-8 specific titles.
- **Key skills as search terms:** "Which of your skills are most likely to appear in job postings?" Pick 3-5 that are distinctive and searchable.
- **Target companies (optional):** "Are there specific companies you'd like to monitor for openings?"
- **Geographic scope:** "Which cities or regions should I search in? How far are you willing to commute?" Use this to define the location filter tiers (ideal, acceptable, borderline, too far).
- **Scraper configuration:** "The job scraper pulls from seven sources by default — Dutch-market boards (Nationale Vacaturebank, LinkedIn NL, Adzuna NL) plus global remote sources (hiring.cafe, We Work Remotely, Welcome to the Jungle, Working Nomads). I'll configure the NVB taxonomy title, city, and search radius for you. What full-text search terms should I use for the query-based sources — specific job titles like 'Product Manager' or 'Data Engineer'?"
- **Adzuna API key (optional):** First check whether `job_scraper/.env` already contains a non-empty `ADZUNA_APP_ID`. If yes, report: "Your Adzuna key is already configured — Adzuna NL is active." Do not re-ask. If not set, ask: "Adzuna NL needs a free App ID and App Key from developer.adzuna.com. Do you have one? If so, paste both now — if not, the other six sources still work and you can add Adzuna later." Write `ADZUNA_APP_ID` and `ADZUNA_APP_KEY` to `.env` if provided; if not, leave them blank and note that Adzuna will be skipped.

**Important:** Also suggest role types the user may not have considered, based on their skill profile. For example:
- If they have strong Python + domain expertise: "Have you considered roles like 'Technical Consultant' or 'Solutions Engineer' in your domain?"
- If they have ML + a specific industry: "Companies in adjacent industries also hire for these skills. Should I include searches for [adjacent sector]?"
- If they have project management experience alongside technical skills: "Would you also want to search for 'Technical Project Manager' or 'Team Lead' roles?"

This proactive suggestion step helps users discover career paths they might not have considered.

---

## Step 3: Generate Profile Files

Once all information is collected (via either path), generate the following files.

> **Personal data vs. template seeds.** The files holding real personal data — `01-candidate-profile.md`, `job_search_tracker.csv`, `cv/templates.md`, and rendered `cv/*.tex` — are **gitignored**. Only their `*.example` seeds (and `cv/main_example.tex`) are tracked in git. Write the real files at their normal paths; git will not track them. Do not modify the `*.example` seeds.

### 1. Write `01-candidate-profile.md`
Populate `.claude/skills/job-application-assistant/01-candidate-profile.md` with all collected data. Sections to fill:
- Core Definition (single-line identity from Section 4.5 — verbatim, confirmed with the user)
- Identity & Contact (name, location, phone, email, LinkedIn, GitHub, languages, status, constraints)
- Education table
- Professional Experience (one subsection per role)
- Independent Projects
- Technical Skills (programming, domain, tools)
- Claims Inventory (from Section 4.5): Capabilities — differentiators, Capabilities — supporting, Exposure, Hygiene — each capability claim must cite the specific Experience entry that backs it
- Framing Notes (from Section 4.5): one line per named role-type plus the cross-role core positioning line
- Certifications, Publications, Awards, References
- Behavioral Summary (profile type, strengths, growth areas, ideal environment, passions)
- Career Goals & Target Sectors (target roles, target sectors, deal-breakers)

Do NOT modify `CLAUDE.md` — it now references this file instead of storing profile data directly.

### 2. Leave `04-job-evaluation.md` as-is
`04` no longer stores candidate-specific data — it reads skills, Claims Inventory, career goals, and constraints directly from `01-candidate-profile.md` at evaluation time. Do not hardcode the user's skills or goals into `04`.

### 3. Update `05-cv-templates.md`
Add role-specific profile statement templates based on their background.

### 4. Update `09-interview-prep.md`
Create STAR examples from their actual experience (at least 3-4 examples).

### 5. Create `cv/main_<lastname>.tex`
Copy `cv/main_example.tex` and replace placeholder personal data with their actual name, contact info, and add their education and most recent experience entries. Do not modify `cv/main_example.tex` — it is the reusable template seed.

### 6. Update `.claude/skills/job-scraper/search-queries.md`
Replace all placeholder tokens with the user's actual information from Section 9:
- Replace `[YOUR_PRIMARY_ROLE_TYPE]` and `[YOUR_CITY]` with actual values in the NVB settings block
- Replace `[YOUR_PRIMARY_JOB_TITLE]`, `[YOUR_SECONDARY_JOB_TITLE]` in `SEARCH_QUERIES` and `TITLE_KEYWORDS`
- Fill in the location filter tiers (ideal, acceptable, borderline, too far) based on commute constraints
- Set `NVB_DISTANCE_KM` to the appropriate radius

Also write the user's values into `job_scraper/.env` directly (create from `.env.example` if it doesn't exist):
- Set `SEARCH_QUERIES` to their comma-separated job titles
- Set `NVB_DCO_TITLE` to the matching NVB taxonomy title
- Set `NVB_CITY` and `NVB_DISTANCE_KM`
- Set `TITLE_KEYWORDS` to their title relevance filter phrases
- Set `ADZUNA_APP_ID` and `ADZUNA_APP_KEY` if provided in Section 9 (leave blank otherwise)

After writing `.env`, run a quick verification to confirm the scraper works:
```bash
uv venv
uv pip install -r job_scraper/requirements.txt -q
uv run python -m job_scraper --sources nvb
```
Report the result: how many jobs were fetched, how many are new. If it fails, show the error and suggest fixes (missing `.env`, wrong Python version, uv not installed, etc.). This uses NVB only, which needs no API key.

---

## Step 4: Confirm & Next Steps

Present a summary:

> **Setup complete!** Here's what was generated:
>
> - `.claude/skills/job-application-assistant/01-candidate-profile.md` - Your complete candidate profile (single source of truth: identity, experience, Claims Inventory, Framing Notes, behavioral summary, career goals)
> - `.claude/skills/job-application-assistant/04-job-evaluation.md` - Evaluation framework (reads your data from `01`)
> - `.claude/skills/job-application-assistant/05-cv-templates.md` - CV templates with your profile statements
> - `.claude/skills/job-application-assistant/09-interview-prep.md` - STAR examples from your experience
> - `cv/main_<lastname>.tex` - Your LaTeX CV base (copied from `main_example.tex`)
> - `.claude/skills/job-scraper/search-queries.md` - Job search queries for `/search`
>
> **Try it out:**
> - The scraper just ran a test — if it found jobs, run `/search` to see the full evaluation
> - Run `/job-scraper-apply` with a job posting URL to see the full application workflow
> - Run `/job-scraper-setup --section search` later to update your search queries as your priorities evolve

---

## Design Principles

- Each section is a natural conversation, not a form
- The user can skip optional sections
- Synthesize answers into structured formats (the user doesn't need to know markdown or LaTeX)
- Can be re-run with `--section <name>` to update specific sections (e.g., `/job-scraper-setup --section search` to reconfigure job search queries without re-doing the full profile)
- Section 9 (search) proactively suggests role types the user may not have considered
- At the end, suggest running `/search` and `/job-scraper-apply` with a test job posting
