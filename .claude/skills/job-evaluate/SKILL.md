---
name: job-evaluate
description: "Evaluate a job posting for candidate fit and write a structured eval.md. Use this skill whenever a job posting needs to be assessed — from a URL, pasted text, or as part of the /search batch flow. Triggers on: evaluate this job, how good is this role, should I apply, assess fit, rate this posting, job fit score, job evaluation. Also invoke when the /search orchestrator or /job-scraper-apply command needs fit scoring before drafting begins."
allowed-tools: "Read, Write, Glob, WebFetch"
---

# job-evaluate

Evaluate a job posting against the candidate profile and write the result to `eval.md`.

Called from the `/search` orchestrator (batch, one role at a time) and from `/job-scraper-apply` (single role, on-demand). Same logic in both contexts.

---

## Input contract

- **job_posting**: raw text or URL of the job posting
- **folder**: `applications/<DDMMYYY-company>-<role>/` (created before calling this skill if it doesn't exist)

---

## Step 0: Parse the posting

- If input is a URL, use `WebFetch` to retrieve the content.
- If it is pasted text, use it directly.
- Extract and store:
  - `company_name`
  - `role_title`
  - `department` (if mentioned)
  - `location`
  - `posting_language` (Dutch or English)
  - `folder_name` — derive as `<company_slug>-<role_slug>` (lowercase, hyphens, no special chars)

If the folder `applications/<folder_name>/` does not exist, create it.

---

## Step 1: Check candidate profile

Read `.claude/skills/job-application-assistant/01-candidate-profile.md`.

If the file contains template placeholders like `[YOUR_NAME]`, `[YOUR_EXPERIENCE]`, or similar unfilled tokens — the profile has not been set up. Stop here and tell the user:

> "The candidate profile hasn't been populated yet. Run `/job-scraper-setup` first to set up your profile, then re-run this evaluation."

Do not proceed with scoring against an empty profile.

---

## Step 2: Evaluate fit

Read:
- `.claude/skills/job-application-assistant/04-job-evaluation.md`
- `.claude/skills/job-application-assistant/01-candidate-profile.md` (already read above)

Apply the framework from `04-job-evaluation.md`. Produce an eval object with:

```
company: <name>
role: <title>
location: <location>
posting_language: <en|nl>
folder: applications/<folder_name>/

fit_score: <overall 1-10>
recommendation: <strong fit | moderate fit | weak fit | skip>

dimensions:
  skills_match:
    score: <1-10>
    matched: [list of matched required/preferred skills]
    gaps: [list of missing required skills]
  experience_match:
    score: <1-10>
    summary: <how work history maps to the role>
  behavioral_match:
    score: <1-10>
    summary: <how behavioral profile fits role/company culture>

keywords: [10 keywords describing the role and company]
deal_breakers: [any deal-breakers from candidate profile that apply]
notes: <any additional context relevant to the application>
```

---

## Step 3: Write eval.md

Write the eval object to `applications/<folder_name>/MMDDYY-<company>-<role>-eval.md` in the format above.

---

## Output contract

- File written: `applications/<folder_name>/MMDDYY-<company>-<role>-eval.md`
- Returns to caller: the eval object (for use in subsequent pipeline phases)

After writing, display a brief summary to the user:
- Company, role, location, fit score, recommendation
- Top 2–3 matched strengths and top 2–3 gaps
- Any deal-breakers

Then ask: "Should I proceed with drafting the application for this role?" If no, stop.
