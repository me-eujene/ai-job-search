# CV Templates and Tailoring Guide

<!-- SETUP: Profile statements and section ordering are personalized by running /job-scraper-setup -->

Editorial guidance for writing and tailoring `cv.md`. All LaTeX rendering rules live in `07-latex-renderer-rules.md`. This file is the **single authoritative spec** for each CV section — if another file appears to define a section differently, this one wins.

The claims that feed every section come from the **Claims Inventory** in `01-candidate-profile.md`. Claim types (`capability` / `exposure` / `hygiene`) and tiers (`differentiator` / `supporting` / `hygiene`) are binding, not advisory.

---

## Profile Statement

The most important section to tailor — and the most constrained.

- **Sentence 1: the identity line, verbatim** from the Core Definition in `01-candidate-profile.md`. It states what *kind* of PM the candidate is. Do not rewrite it.
- **Sentence 2 (optional): role-specific emphasis** — only if the voice inputs warrant it. 2 sentences absolute maximum.
- **Never achievements.** Deliverables, metrics, and outcomes live in the Experience bullets. A profile statement that summarises accomplishments is a rewrite violation.
- **Never generic PM-craft traits** ("data-driven", "customer-obsessed", "results-oriented") — only differentiators.
- **Never attach "N+ years" to a domain** ("10+ years building API products"). Tenure claims read as padding and date the candidate.
- **No tense mixing** within the statement.
- Never repeats claims that appear in the sections below.

---

## Core Competencies

**Max 3 bullets.** Format: `**Category:** specifics`.

Rules:
- Each bullet answers a `must` requirement from the requirements map — competencies exist to mirror the "what you'll bring" section of the JD, nothing else.
- Each bullet is backed by a named `capability` claim from the Claims Inventory, which in turn links to evidence in Experience. No capability without evidence.
- `exposure` items (side-project tech) are banned here — they live in Personal Projects.
- `hygiene` items (Jira, Git, Figma, Scrum, stakeholder management, generic role craft) are banned here and everywhere else on the CV.
- `differentiator`-tier capabilities take the slots before `supporting`-tier ones.

A long dot-separated skills line is the canonical failure mode of this section. Three sharp bullets beat eleven keywords.

---

## Professional Experience

- Reverse chronological. Rewrite bullets to emphasise the aspects mapped in the requirements map.
- 4–6 bullets for most recent role, 2–3 for previous, 1–2 for older.
- **Emphasise measurable results**: "Reduced processing time by X%", "alpha in ~6 months".
- Relative weight of experiences must be preserved — a minor aspect of a role cannot lead its bullet list just because it matches the JD (see the interview backtrack test in `03-writing-style.md`).
- Experience bullets are the **only** place achievement claims live.

---

## Personal Projects

- Describe the project as what it is — never inflate scope or reframe it as something it wasn't (an evaluation tool, a research project, professional work).
- `exposure`-type tools (side-project or incidental tech) appear here and only here, as part of the project description.
- One entry, 1–3 lines. Moves up in prominence when the Framing Notes in `01-candidate-profile.md` call for it.

---

## Education

- Degrees and completed courses, dates and titles only — the candidate's qualifiers are experience-based, keep this brief.

---

## Section Ordering

Default order: Profile → Core Competencies → Experience → Personal Projects → Education → Languages → References.

For builder-PM / agentic-AI roles, Personal Projects may move directly under Core Competencies.

---

## Handling Employment Gaps

- Explain matter-of-factly if needed.
- Describe how professional development continued during the gap.
- Frame as deliberate skill-building and career repositioning.

---

## Traceability Rule

Every line on the CV must trace to either the identity line or a row in the requirements map built in job-writer Step 4. A line that answers no requirement and expresses no differentiator is filler — cut it. When trimming for the page budget, cut in reverse tier order: hygiene never got in, `supporting` goes before `differentiator`.

---

## Page Budget — Hard 2-Page Limit

The CV **must** fit on exactly 2 pages. Use these content limits:

| Section | Max budget |
|---------|-----------|
| Profile statement | 2 sentences |
| Core Competencies | 3 bullets, each 1–2 lines |
| Most recent role | 4–5 bullets |
| Previous role | 2–3 bullets |
| Older roles | 1–2 bullets (1 line each) |
| Personal Projects | 1 entry, 1–3 lines |
| Education | 2–3 entries, 1 line each |
| References | "Available upon request." (single line) |

**If in doubt, cut rather than squeeze.** Cramped content is worse than missing content.
