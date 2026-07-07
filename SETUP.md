# Setup Guide

Step-by-step instructions for getting the AI Job Search framework running.

## 1. Prerequisites

### Claude Code

Install Claude Code (Anthropic's CLI for Claude):

```bash
npm install -g @anthropic-ai/claude-code
```

You'll need an Anthropic API key or a Claude Pro/Team subscription. See the [Claude Code docs](https://docs.anthropic.com/en/docs/claude-code) for details.

### Python 3.10+ and uv

Required for the job scraper, which is run via [uv](https://docs.astral.sh/uv/). Check with:

```bash
python --version
uv --version   # install from https://docs.astral.sh/uv/ if missing
```

### LaTeX (for compiling CVs and cover letters)

Install a LaTeX distribution to compile the generated `.tex` files to PDF:

- **Windows:** [MiKTeX](https://miktex.org/download)
- **macOS:** [MacTeX](https://tug.org/mactex/)
- **Linux:** `sudo apt install texlive-full` or `sudo dnf install texlive-scheme-full`

The CV compiles with `pdflatex`. The cover letter compiles with `xelatex` (for custom fonts).

## 2. Fork and clone

```bash
gh repo fork <your-fork> --clone
cd ai-job-search
```

## 3. Enable skills and permissions

The repo ships with a `.claude/settings.local.json` that pre-approves the skills and Bash commands Claude needs. Claude Code loads this automatically when you run `claude` inside the repo — no extra steps required.

If you want to review or adjust what is permitted, open the file:

```
.claude/settings.local.json
```

Key permissions pre-approved:
- `Skill(job-scraper)` — lets Claude run `/search` without prompting
- `Bash(python:*)` / `Bash(python3:*)` — runs the job scraper
- `Bash(git:*)` — lets Claude commit and push
- `Bash(gh repo:*)` — GitHub CLI operations

To add or remove permissions, run `/update-config` inside Claude Code and describe the change in plain English.

## 4. Install scraper dependencies

From the repo root, create a uv virtual environment and install into it:

```bash
uv venv
uv pip install -r job_scraper/requirements.txt
```

The scraper is then run with `uv run python -m job_scraper`.

## 5. Configure the scraper

```bash
cp job_scraper/.env.example job_scraper/.env
```

Open `job_scraper/.env` and fill in:

- **`SEARCH_QUERIES`** — comma-separated job titles to search (e.g. `product manager,product owner`). Sent to LinkedIn NL, hiring.cafe, and Adzuna NL.
- **`NVB_DCO_TITLE`** — NVB taxonomy title matching your role (default: `Productmanager`).
- **`NVB_CITY`** / **`NVB_DISTANCE_KM`** — your target city and commute radius.
- **`ADZUNA_APP_ID`** / **`ADZUNA_APP_KEY`** — optional; a free key from [developer.adzuna.com](https://developer.adzuna.com) enables the Adzuna NL source. Without it, Adzuna is silently skipped and the other six sources still run.

Six of the seven sources need no API key.

## 6. Run the setup interview

Start Claude Code in the repository:

```bash
claude
```

Then run the onboarding:

```
/job-scraper-setup
```

Claude will offer two paths:

- **Path A (recommended):** Share your existing CV (mention the file with `@` or paste the text). Claude extracts your information and asks follow-up questions for anything missing.
- **Path B:** Answer structured interview questions section by section.

Both paths produce the same result: fully populated profile files.

### What gets populated

Files holding your real data (`01-candidate-profile.md`, `job_search_tracker.csv`, `cv/templates.md`, rendered `cv/*.tex`) are **gitignored** — the repo tracks only their `*.example` seeds (like `.env` / `.env.example`). Setup writes the real files locally; they are never committed.

| File | Content |
|------|---------|
| `01-candidate-profile.md` | Single source of truth (gitignored; seed: `01-candidate-profile.example.md`): identity, education, experience, Claims Inventory, Framing Notes, behavioral summary, career goals |
| `04-job-evaluation.md` | Scoring framework (reads your data from `01-candidate-profile.md`) |
| `05-cv-templates.md` | CV templates with your profile statements |
| `09-interview-prep.md` | STAR examples from your experience |
| `cv/main_<lastname>.tex` | Your LaTeX CV (copied from `main_example.tex`) |
| `search-queries.md` | Job search queries for `/search` fallback |

### Re-running setup

Update specific sections later without re-doing the full profile:

```
/job-scraper-setup --section skills
/job-scraper-setup --section experience
/job-scraper-setup --section search
```

The `--section search` option is especially useful as your priorities evolve.

## 7. Test the workflow

### Search for jobs

```
/search
```

Claude runs the Python scraper, fetches from all configured sources, deduplicates, evaluates fit, and presents a ranked shortlist. Typical first run takes 10–30 seconds.

### Apply to a job

```
/job-scraper-apply https://www.linkedin.com/jobs/view/123456789
```

Or paste the job description directly:

```
/job-scraper-apply [paste job posting text here]
```

Claude will:
1. Evaluate the fit against your profile
2. Ask if you want to proceed
3. Draft a tailored CV and cover letter
4. Have a reviewer agent critique the drafts
5. Revise and present the final output

## 8. Compile your documents

After `/job-scraper-apply` creates the LaTeX files:

```bash
# Compile CV (pdflatex)
cd cv && pdflatex main_<company>.tex && cd ..

# Compile cover letter (xelatex — required for custom fonts)
cd cover_letters && xelatex cover_<company>_<role>.tex && cd ..
```

## Troubleshooting

### Scraper not returning results

1. Check that `job_scraper/.env` exists (copy from `.env.example` if not)
2. Six of the seven sources need no key; only Adzuna NL requires `ADZUNA_APP_ID`/`ADZUNA_APP_KEY`
3. Verify `NVB_DCO_TITLE` matches a valid NVB taxonomy title for your role

### LaTeX compilation errors

- CV: uses `pdflatex` (standard LaTeX)
- Cover letter: uses `xelatex` (for custom fonts in `cover_letters/OpenFonts/fonts/`)
- Ensure your LaTeX distribution includes the `moderncv` package

### Fonts not found in cover letter

The cover letter template expects fonts in `cover_letters/OpenFonts/fonts/`. Make sure this directory exists and contains the Lato and Raleway font files.
