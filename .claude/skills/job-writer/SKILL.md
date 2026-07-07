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
- `requirements_map`: the approved requirement → claim → placement table from Step 4
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

## Step 4: Requirements map + framing checkpoint

Before drafting anything, build the **requirements map** — the importance model for this application.

1. Extract every requirement from the posting and classify its priority:
   - `must` — the hiring manager filters on this
   - `nice` — mentioned, but not decisive
   - `noise` — boilerplate ("excellent communication", "team player", generic role craft)
2. For each `must` and `nice`, map it to a claim from the Claims Inventory in `01-candidate-profile.md`, note the claim type (`capability` / `exposure` / evidence bullet), and decide where it lands: profile statement / competency / experience bullet / cover letter / **acknowledged gap**. `noise` requirements get no ink.
3. Name the **top 3 must-sees** — the three things this hiring manager must find in the top third of page 1.

Present the map as a compact table together with the framing proposal:

> "Requirements map: [table]. Top 3 must-sees: [X, Y, Z]. I'm planning to open with [X] and frame the motivation as [Y, based on authenticity inputs]. Does this match your intent, or do you want to adjust?"

Do not draft until the user confirms or adjusts. Store the approved framing as `framing_approval` and the map as `requirements_map` — return both to the orchestrator so the reviewer receives them too.

**Hard rule for drafting:** every line in `cv.md` and `cover.md` must trace to a requirements-map row or to the identity line. Anything that doesn't trace gets cut, not squeezed in.

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
[Sentence 1: identity line verbatim from the Core Definition in 01-candidate-profile.md — do not rewrite. Sentence 2 (optional): role-specific emphasis, only if warranted by the voice inputs. Never replace the identity line with a deliverables summary; never attach "N+ years" to a domain.]

## Core Competencies
- **Category:** specifics
(max 3 items — each must answer a `must` requirement from the requirements map and be backed by a named `capability` claim from the Claims Inventory. `exposure` and `hygiene` items are banned here.)

## Experience

### Job Title — Company (YYYY–YYYY) | City
- Bullet with metric or outcome
- Bullet
(4–6 bullets for most recent; 2–4 for older)

## Personal Projects
- **Project** (Year). One–two lines. `exposure`-type tools live here and only here, described as part of the project.

## Education

### Degree in Field — Institution (YYYY–YYYY) | City

## Languages
Language (native), Language (fluent).

## References
Available upon request.
```

Rules:
- Always English
- Voice inputs are the primary source for capability framing — profile data is supporting evidence
- **Claim-type discipline:** competencies come only from `capability` claims; side-project tech (`exposure`) never appears outside Personal Projects; `hygiene` items are never printed
- Every line traces to a requirements-map row; the top 3 must-sees are visible in the top third of page 1
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
- 200 word body maximum (up to 300 still fits on page, but tight is better)
- No em-dashes; no clichés ("passionate about", "leverage", "drive results")
- Reference **Claude Code** by name if mentioning agentic coding or AI tooling

---

## Revise mode

When called with `mode: revise`:

1. Read `critique` (reviewer feedback) and `user_comments` (if any)
2. Re-read current `cv.md` and `cover.md`
3. Apply improvements — **in this order**:
   1. Fix factual and category violations: fabricated or overstated claims, `exposure` presented as `capability`, `hygiene` items printed, identity line rewritten
   2. Strengthen the mapping of the top-3 must-sees from the requirements map — they must be visible in the top third of page 1
   3. **Cut** the weakest, lowest-signal content — the default action for a line flagged as filler is deletion, not rewording
   4. Incorporate verified company-specific angles from reviewer research
   5. Fix tone/style issues flagged by reviewer; apply user edits or comments
   6. Keywords: only where the posting's term replaces a weaker synonym of something already claimed — never as new content
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
- Returns to orchestrator: `voice_inputs`, `authenticity_inputs`, `framing_approval`, `requirements_map`

**IMPORTANT:** After writing the files, do NOT present the drafts to the user and do NOT ask what they'd like to do next. Return control to the orchestrator immediately.

---

## Hand-over

**After draft (Steps 1–6):** Return `voice_inputs`, `authenticity_inputs`, `framing_approval`, `requirements_map` to the orchestrator. **Next step: orchestrator spawns `job-reviewer` (Phase 5)** via the Agent tool using the `job-reviewer` skill prompt template. Do not interact with the user until the reviewer returns.

**After revise (revise mode):** Present the 3–5 key tailoring decisions and gaps summary to the user. Then ask: "Ready to render to PDF, or do you want to make further edits?" — If further edits: collect user comments, re-invoke `job-writer` with `mode: revise` and `user_comments`. If ready: **next step → load `latex-renderer` skill**, passing folder path.
