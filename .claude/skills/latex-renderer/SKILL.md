---
name: latex-renderer
description: "Convert cv.md and cover.md to LaTeX files and compile to PDF. Invoke this skill whenever the user asks to render, compile, or export the application to PDF. Do NOT write LaTeX by hand — always use this skill. Triggers on: render to PDF, compile, export PDF, generate LaTeX, make PDF, create PDF, render application."
allowed-tools: "Read, Write, Edit, Glob, Bash"
---

# latex-renderer

Mechanical conversion of `cv.md` and `cover.md` to compilable LaTeX, then compile to PDF. No editorial judgment — this phase is purely structural translation.

All mapping rules are in `07-latex-renderer-rules.md`. Load it before starting.

---

## Input contract

- `folder`: `applications/<company>-<role>/`
- Files that must exist: `<folder>/cv.md`, `<folder>/cover.md`
- Candidate contact data: read from `.claude/skills/job-application-assistant/01-candidate-profile.md`

---

## Step 1: Load rendering rules

Read `.claude/skills/job-application-assistant/07-latex-renderer-rules.md` in full before proceeding. All LaTeX structure, escape rules, and compile commands are defined there.

---

## Step 2: Render cv.md → main_<company>.tex

1. Read `<folder>/cv.md`
2. Read `cv/main_example.tex` as structural reference
3. Apply the md→LaTeX section mapping from `07-latex-renderer-rules.md`
4. Fill personal data (name, email, phone, LinkedIn, GitHub) from `01-candidate-profile.md`
5. Escape all special characters per the escaping table
6. Write the output to:
   - `<folder>/main_<company>.tex`
   - Also copy to `cv/main_<company>.tex`

---

## Step 3: Render cover.md → cover_<company>_<role>.tex

1. Read `<folder>/cover.md`
2. Apply the md→LaTeX section mapping from `07-latex-renderer-rules.md`
3. Fill personal data from `01-candidate-profile.md`
4. Copy `cover_letters/cover.cls` to `<folder>/cover.cls`
5. Write the output to:
   - `<folder>/cover_<company>_<role>.tex`
   - Also copy to `cover_letters/cover_<company>_<role>.tex`

---

## Step 4: Compile

```bash
# CV
cd cv && pdflatex main_<company>.tex && cd ..

# Cover letter (must compile from cover_letters/ so fonts resolve)
cd cover_letters && xelatex cover_<company>_<role>.tex && cd ..
```

Run each compile command. If either fails, show the error output and stop — do not silently produce a broken PDF.

---

## Step 5: Verify compilation

Check against the compilation checklist in `07-latex-renderer-rules.md`:

- [ ] pdflatex exits without errors
- [ ] xelatex exits without errors
- [ ] CV PDF is exactly 2 pages
- [ ] Cover letter PDF is exactly 1 page
- [ ] No placeholder text remaining
- [ ] URLs in CV are live links

If CV overflows 2 pages: go back to `cv.md`, identify the longest section, and trim bullets until it fits. Do not reduce font size or geometry.

If cover letter overflows 1 page: trim the body to stay under 300 words. Do not change font size or line spacing unless the word count is already ≤300.

---

## Output contract

- Files written: `<folder>/main_<company>.tex`, `<folder>/cover_<company>_<role>.tex`, `<folder>/cover.cls`
- Copies in: `cv/main_<company>.tex`, `cover_letters/cover_<company>_<role>.tex`
- PDFs compiled in: `cv/` and `cover_letters/`

Report to user: verification checklist results (pass/fail per item) and file paths.

---

## Hand-over

After reporting, return to the orchestrator. **Next step: Phase 8 complete.** Orchestrator prompts: "Application for [Role] at [Company] complete. Want to apply to another role?" If yes → return to Phase 2 shortlist. If no → end session.
