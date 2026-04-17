---
name: job-writer
description: "Conduct a structured candidate interview then draft targeted cv.md and cover.md application documents for a specific role. Also handles revision mode after reviewer feedback or user edits. Invoke this skill whenever drafting or revising CV/cover letter content — it owns the interview → draft → revise loop. Do NOT write application documents without invoking this skill first. Triggers on: draft CV, write cover letter, draft application, tailor CV, start drafting, write my application, revise based on feedback."
allowed-tools: "Read, Write, Edit, Glob"
---

# job-writer

Draft and revise `cv.md` and `cover.md` for a specific role. Called twice per role: once to draft (after the interview), once to revise (after reviewer feedback and/or user edits).

---

## Input contract

**Draft call** (from orchestrator after user picks a role):
- `eval`: eval object from `eval.md`
- `job_posting`: raw text of the posting

**Revise call** (same skill, `mode: revise`):
- All of the above, plus:
- `framing_approval`: the 2–3 sentence framing the user confirmed in Step 4 (passed to reviewer; needed here so revisions stay consistent with it)
- `critique`: structured feedback from the reviewer
- `user_comments`: free-text or inline edits from the user edit loop (may be empty)

---

## Step 1: Opening brief

Present a 2–3 sentence summary of what the role is actually asking for, then one sentence on the company. Factual — not marketing copy.

> "[Company] is [one-sentence description — what they do, market position, or stage]. The [Role] is responsible for [core responsibility from JD]. They're looking for someone who can [the key capability or challenge the role centres on]."

Then proceed to the interviews.

---

## Step 2: Voice interview

Ask both questions together in a single message:

> 1. **What's relevant from your experience for this role, and why do you think it is?**
> 2. **What do you want them to understand about how you work that the CV won't show?**

Wait for answers. Store as `voice_inputs`. These are the raw material for capability claims and framing — shape them, don't replace them with profile data.

---

## Step 3: Authenticity interview

Ask both questions together in a single message:

> 1. **What about this role and company interests you?**
> 2. **Is there any personal angle that makes this role stand out for you?** (There may be none — that's fine.)

Wait for answers. Store as `authenticity_inputs`. If there is no personal angle, omit or minimise that section in the cover letter — do not invent motivation.

---

## Step 4: Framing checkpoint

Before drafting the cover letter, propose the framing in 2–3 sentences:

> "I'm planning to open with [X] and frame the motivation as [Y, based on authenticity inputs]. Does this match your intent, or do you want to adjust the angle?"

Do not write the letter until the user confirms or adjusts. Store the approved framing as `framing_approval` — return this to the orchestrator so the reviewer receives it too.

---

## Step 5: Draft cv.md

Read:
- `.claude/skills/job-application-assistant/01-candidate-profile.md`
- `.claude/skills/job-application-assistant/03-writing-style.md`
- `.claude/skills/job-application-assistant/05-cv-templates.md`

Write `applications/<folder>/cv.md` using the structure below. Draft from scratch — do not copy from any existing `.tex` file.

### cv.md structure

```markdown
## Profile
[3–4 line profile statement tailored to this role]

## Core Competencies
- **Category:** skills, tools, specifics
- **Category:** ...
(5–7 items)

## Experience

### Job Title — Company (YYYY–YYYY) | City
- Bullet with metric or outcome
- Bullet
(4–6 bullets for most recent; 2–4 for older)

## Education

### Degree in Field — Institution (YYYY–YYYY) | City
Thesis: "Title." Brief description.

## Languages
Language (native), Language (fluent), Language (intermediate).

## Publications
- Author(s) (Year). Title. Journal/Conference. [DOI link](url)

## Honors and Awards
- **Award Name** — Event/Organization (Year).

## References
Available upon request.
```

Rules:
- Always English
- Voice inputs are the primary source for capability framing — profile data is supporting evidence
- 2-page limit when rendered; cut rather than squeeze

---

## Step 6: Draft cover.md

Read:
- `.claude/skills/job-application-assistant/06-cover-letter-templates.md`

Write `applications/<folder>/cover.md` using the structure below. Match the language of the job posting (Dutch posting → Dutch cover letter).

### cover.md structure

```markdown
Dear [Name / Hiring Manager],

[Opening paragraph — role name, connection to background, 2–3 sentences]

[Body paragraph intro sentence:]

- **Label:** concrete achievement or relevant skill
- **Label:** ...
- **Label:** ...

[Connection to this company specifically — mission, product, recent initiative]

[Personal fit or forward-looking close — 2–3 sentences]

Kind regards,
[Candidate name]
```

Rules:
- Authenticity inputs anchor the motivation section — do not invent motivation
- 250–300 word body maximum
- No em-dashes; no clichés ("passionate about", "leverage", "drive results")
- Reference **Claude Code** by name if mentioning agentic coding or AI tooling

---

## Revise mode

When called with `mode: revise`:

1. Read `critique` (reviewer feedback) and `user_comments` (if any)
2. Re-read current `cv.md` and `cover.md`
3. Apply improvements — in order of impact:
   - Add missed keywords where they fit naturally
   - Incorporate company-specific angles from reviewer research
   - Reframe passive statements to be action-oriented
   - Fix tone/style issues flagged by reviewer
   - Apply any user edits or comments
4. Edit both files in place
5. Do NOT apply suggestions that fabricate skills or experience — if a requirement is a genuine gap, say so

After revising, present to the user:
- 3–5 key tailoring decisions made
- What the reviewer suggested that had the most impact
- Any gaps acknowledged or reframed honestly

Then ask: "Ready to render to PDF, or do you want to make further edits?"

---

## Output contract

- Files written: `applications/<folder>/cv.md`, `applications/<folder>/cover.md`
- Returns to orchestrator: `framing_approval` (needed by reviewer)
