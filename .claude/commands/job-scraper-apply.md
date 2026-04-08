# /job-scraper-apply - Drafter-Reviewer Job Application Workflow

You are orchestrating a two-agent job application workflow. The job posting is provided below as `$ARGUMENTS` (either a URL or pasted text).
Follow these steps **exactly in order**. Do not skip steps.

---

## Step 0: Parse Input

- If `$ARGUMENTS` looks like a URL, use `WebFetch` to retrieve the job posting content.
- If it is pasted text, use it directly.
- If a `.md` file with role evaluations is provided, use it.
- Extract: **company name**, **role title**, **department** (if mentioned), **location**, and **language** of the posting (Dutch or English).
- Store these for use throughout the workflow.

---

## Step 1: DRAFTER - Evaluate Fit

Read the evaluation framework:
- `.claude/skills/job-application-assistant/04-job-evaluation.md`
- `.claude/skills/job-application-assistant/01-candidate-profile.md`

Using the framework from `04-job-evaluation.md`, evaluate the job posting against the candidate's profile.

Present the evaluation to the user with:

1. **Skills match** - which required/preferred skills match vs. gaps
2. **Experience match** - how work history maps to the role
3. **Behavioral/culture match** - how behavioral profile fits the role/company culture
4. **Overall fit score** and recommendation (strong fit / moderate fit / weak fit)

After presenting the evaluation, ask the user:
> "Should I proceed with drafting the CV and cover letter for this role?"

**If the user says no, stop here.** If yes, continue to Step 2.

---

## Step 2: DRAFTER - Candidate Interview

This is the first thing the candidate experiences before any drafting begins. Open with a brief to orient them, then ask both interview sets in sequence.

### Opening brief

Present a 2-3 sentence summary of what the role is actually asking for, followed by one sentence on the company. Keep it factual, not marketing copy.

Example format:
> "[Company] is [one-sentence description — what they do, market position, or stage]. The [Role] is responsible for [core responsibility from JD]. They're looking for someone who can [the key capability or challenge the role centres on]."

Then proceed to the two interview sets below, one at a time.

---

### Step 2.1: Voice Interview

Ask these two questions together in a single message:

> 1. **What's relevant from your experience for this role, and why do you think it is?**
> 2. **What do you want them to understand about how you work that the CV won't show?**

Wait for the answers. Store them as **voice inputs** — these are the raw material for capability claims and framing. The agent edits and shapes these; it does not generate them from profile data.

---

### Step 2.2: Authenticity Interview

Ask these two questions together in a single message:

> 1. **What about this role and company interests you?**
> 2. **Is there any personal angle that makes this role stand out for you?** (There may be none — that's fine.)

Wait for the answers. Store them as **authenticity inputs** — these anchor the motivation section. If there is no personal angle, that section is omitted or kept minimal; do not invent one.

---

## Step 3: DRAFTER - Draft CV + Cover Letter

## PATH A FOR MINOR CHANGES

Read the following reference files:
- `.claude/skills/job-application-assistant/01-candidate-profile.md`
- `.claude/skills/job-application-assistant/03-writing-style.md`
- Read any existing cv/*.pdf files

Use one of the existing .pdf or .doc files provided by user (ask if none available) to use as a source format.
User may decide to make changes themselves, if so - generate a list of high- and medium- priority changes per resume section. Explain your motivation behind each change and why do you think this reframe is about form, not substance.
See more in

### PATH B FOR MAJOR CHANGES OR WHEN NO CV
If no CV provided: use LaTeX sources and formats.

Read the following reference files:
- `.claude/skills/job-application-assistant/01-candidate-profile.md`
- `.claude/skills/job-application-assistant/03-writing-style.md`
- `.claude/skills/job-application-assistant/05-cv-templates.md`
- `.claude/skills/job-application-assistant/06-cover-letter-templates.md`

### PATH A — Minor changes (existing .pdf or .doc CV available)

Use an existing `.pdf` or `.doc` file provided by the user as the source format. If none is available, ask the user before proceeding.

If the user wants to make changes themselves: generate a prioritized list of **high-** and **medium-priority changes per CV section**. For each change, explain the motivation and why the reframe is about form, not substance.

### PATH B — Major changes or no CV provided

Use LaTeX sources and formats.

Also read the most recent existing CV and cover letter files for structural reference:
- Read any existing `applications/*/main_*.tex` file as a LaTeX template reference
- Read any existing `applications/*/cover_*.tex` file as a cover letter template reference

#### CV (`applications/<company>-<role>/main_<company>.tex`)
- Always in **English**
- Follow the moderncv/banking format from `05-cv-templates.md`
- Tailor the profile statement and experience bullets to the specific role
- Reframe skills and achievements to match job requirements
- Keep to 2 pages
- Copy `cover.cls` from `templates/` into the new application folder

#### Cover Letter (`applications/<company>-<role>/cover_<company>_<role>.tex`)

**Before drafting the cover letter**, propose the framing in 2-3 sentences and wait for approval:

> "I'm planning to open with [X] and frame the motivation as [Y based on authenticity inputs]. Does this match your intent, or do you want to adjust the angle?"

Do not write the letter until the user confirms or revises the framing.

- **Match the language of the job posting** (Dutch posting -> Dutch cover letter, English posting -> English cover letter)
- Follow the structure from `06-cover-letter-templates.md`
- Use the `cover.cls` template
- Tailor the opening paragraph to the specific role and company
- Address to a named person if available in the posting, otherwise "Dear Hiring Manager" (or equivalent in posting language)
- Keep to approximately one page
- Any mention of agentic coding or AI tooling must reference **Claude Code** by name

Write both files to disk.

---

## Step 4: REVIEWER - Research & Critique

Use the **Agent tool** to spawn a `general-purpose` reviewer agent with the following prompt:

```
You are a hiring manager proxy reviewing a job application. Your job is to make the application as targeted and compelling as possible.

## Candidate's Interview Inputs
The candidate provided these inputs before drafting. The cover letter must be grounded in them — not in generic fit language derived from the job posting.

<VOICE_INPUTS>
<INSERT_VOICE_INPUTS_HERE>
</VOICE_INPUTS>

<AUTHENTICITY_INPUTS>
<INSERT_AUTHENTICITY_INPUTS_HERE>
</AUTHENTICITY_INPUTS>

## Your Tasks

### 1. Research the Company
Use WebSearch and WebFetch to research:
- The company's website, mission, and recent news
- The specific department or team (if mentioned in the posting)
- Any recent projects, press releases, or strategic initiatives relevant to the role
- Company culture and values
- Extract 10 keywords that describe the role and the company.

### 2. Read All Reference Materials
Read these files to understand the candidate and quality standards:
- `.claude/skills/job-application-assistant/01-candidate-profile.md`
- `.claude/skills/job-application-assistant/02-behavioral-profile.md`
- `.claude/skills/job-application-assistant/03-writing-style.md`
- `.claude/skills/job-application-assistant/04-job-evaluation.md`
- `.claude/skills/job-application-assistant/05-cv-templates.md`
- `.claude/skills/job-application-assistant/06-cover-letter-templates.md`

### 3. Read the Drafts
Read the drafted CV and cover letter:
- If PATH A was used: read the new `.pdf` or `.doc` file provided by the user, or the change list generated by the drafter
- If PATH B was used: read `applications/<COMPANY>-<ROLE>/main_<COMPANY>.tex` and `applications/<COMPANY>-<ROLE>/cover_<COMPANY>_<ROLE>.tex`

### 4. Read the Job Posting
<JOB_POSTING>
<INSERT_JOB_POSTING_TEXT_HERE>
</JOB_POSTING>

### 5. Produce Feedback
Return a structured critique with **specific, actionable suggestions** in these categories:

**a) Missed keywords/requirements**
- List any requirements or keywords from the posting that are not addressed in the CV or cover letter
- For each, suggest where and how to add them (with specific text suggestions)

**b) Company/department-specific angles**
- Based on your research, suggest specific angles to add
- Suggest how to connect experience to the company's strategic priorities

**c) Action-oriented reframing**
- Identify passive or generic statements and suggest action-oriented rewrites

**d) Tone and style issues**
- Check against the writing style guide (03-writing-style.md)
- Flag any issues with tone, formality, or voice
- Check for authenticity against the candidate's stated inputs: does the motivation section use what the candidate actually said, or did it revert to generic fitting language? Flag any passage that reads as constructed rather than rooted in the candidate's own words.
- Flag em-dashes (`--` or `---` used as prose separators)
- Flag clichés and filler phrases: "passionate about", "great fit", "leverage", "drive results", "hit the ground running", and false dichotomies
- Flag gerund-as-subject constructions: sentences opening with "Verb+ing ... is something I ..." or "Verb+ing ... is what I ..." — rewrite as direct first-person claims
- Flag generic buzzwords without concrete backing

**e) Verification checklist**
Run this checklist and report pass/fail for each:
- [ ] All claims match actual profile - no fabricated skills, experience, or achievements. Relative weight of the experiences is preserved.
- [ ] Job titles, dates, company names, and locations are correct
- [ ] Contact details are correct
- [ ] Profile statement is tailored to the specific role
- [ ] Key job requirements are addressed
- [ ] No LaTeX syntax errors (balanced braces, correct commands)
- [ ] No spelling or grammar errors
- [ ] Agentic coding / AI tooling references mention Claude Code by name
- [ ] Cover letter addressed correctly
- [ ] Cover letter fits approximately one page
- [ ] CV follows 2-page moderncv/banking format

**CRITICAL RULE:** All suggestions must be grounded in actual profile data. Do NOT suggest fabricating skills, experience, or achievements. If a requirement is a gap, say so honestly and suggest how to frame adjacent experience instead.

Return your full feedback as a single structured message.
```

**Important:** Before spawning the agent, replace `<COMPANY>`, `<ROLE>`, `<INSERT_JOB_POSTING_TEXT_HERE>`, `<INSERT_VOICE_INPUTS_HERE>`, and `<INSERT_AUTHENTICITY_INPUTS_HERE>` with the actual values from Steps 0-3.

---

## Step 5: DRAFTER - Revise Based on Feedback

Once the reviewer agent returns its feedback:

1. Read the reviewer's suggestions carefully
2. Read both draft files again
3. Incorporate the suggestions that improve the application:
   - Add missed keywords where they fit naturally
   - Add company-specific angles from the reviewer's research
   - Reframe passive statements to be more action-oriented
   - Fix any tone/style issues
   - Fix any verification checklist failures
4. Update both files **in place** (edit, don't recreate) — OR generate edit recommendations if the user is working in PATH A and prefers to apply changes themselves
5. Do NOT incorporate suggestions that would fabricate skills or experience

---

## Step 6: Present Final Output

After revision, present to the user:

### Key Tailoring Decisions
Summarize 3-5 key decisions made to tailor the application:
- What was emphasized and why
- What company-specific angles were incorporated
- What the reviewer suggested that was most impactful
- Any gaps that were acknowledged or reframed
- Confirm before writing the final files

### Files Created
List the files written — if applicable:
- `applications/<company>-<role>/main_<company>.tex`
- `applications/<company>-<role>/cover_<company>_<role>.tex`

If PATH A was used, summarize the change recommendations delivered instead.

Tell the user: "The application materials are ready for your review."
