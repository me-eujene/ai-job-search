# Setup Guide

Step-by-step instructions for getting the AI Job Search framework running.

## 1. Prerequisites

### Claude Code

Install Claude Code (Anthropic's CLI for Claude):

```bash
npm install -g @anthropic-ai/claude-code
```

You'll need an Anthropic API key or a Claude Pro/Team subscription. See the [Claude Code docs](https://docs.anthropic.com/en/docs/claude-code) for details.

### Python 3.10+

Required for the job scraper. Check with:

```bash
python --version
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

## 3. Install scraper dependencies

```bash
pip install -r job_scraper/requirements.txt
```

## 4. Configure the scraper

```bash
cp job_scraper/.env.example job_scraper/.env
```

Open `job_scraper/.env` and fill in:

- **`RAPIDAPI_KEY`** — required for Indeed NL and LinkedIn NL. Get a free key at [rapidapi.com](https://rapidapi.com/letscrape-6bRBa3QguO5/api/jobs-api14) (200 requests/month free tier).
- **`SEARCH_QUERIES`** — comma-separated job titles to search (e.g. `product manager,product owner`).
- **`NVB_DCO_TITLE`** — NVB taxonomy title matching your role (default: `Productmanager`).
- **`NVB_CITY`** / **`NVB_DISTANCE_KM`** — your target city and commute radius.

NVB (Nationale Vacaturebank) requires no API key.

## 5. Run the setup interview

Start Claude Code in the repository:

```bash
claude
```

Then run the onboarding:

```
/setup-job-agent
```

Claude will offer two paths:

- **Path A (recommended):** Share your existing CV (mention the file with `@` or paste the text). Claude extracts your information and asks follow-up questions for anything missing.
- **Path B:** Answer structured interview questions section by section.

Both paths produce the same result: fully populated profile files.

### What gets populated

| File | Content |
|------|---------|
| `CLAUDE.md` | Your full candidate profile |
| `01-candidate-profile.md` | Structured education, experience, skills |
| `02-behavioral-profile.md` | Behavioral assessment |
| `04-job-evaluation.md` | Personalized skill match areas and career goals |
| `05-cv-templates.md` | CV templates with your profile statements |
| `07-interview-prep.md` | STAR examples from your experience |
| `cv/main_<lastname>.tex` | Your LaTeX CV (copied from `main_example.tex`) |
| `search-queries.md` | Job search queries for `/scrape` fallback |

### Re-running setup

Update specific sections later without re-doing the full profile:

```
/setup-job-agent --section skills
/setup-job-agent --section experience
/setup-job-agent --section search
```

The `--section search` option is especially useful as your priorities evolve.

## 6. Test the workflow

### Search for jobs

```
/scrape
```

Claude runs the Python scraper, fetches from all configured sources, and presents matches. Typical first run takes 10–30 seconds.

### Apply to a job

```
/apply https://www.linkedin.com/jobs/view/123456789
```

Or paste the job description directly:

```
/apply [paste job posting text here]
```

Claude will:
1. Evaluate the fit against your profile
2. Ask if you want to proceed
3. Draft a tailored CV and cover letter
4. Have a reviewer agent critique the drafts
5. Revise and present the final output

## 7. Compile your documents

After `/apply` creates the LaTeX files:

```bash
# Compile CV (pdflatex)
cd cv && pdflatex main_<company>.tex && cd ..

# Compile cover letter (xelatex — required for custom fonts)
cd cover_letters && xelatex cover_<company>_<role>.tex && cd ..
```

## Troubleshooting

### Scraper not returning results

1. Check that `job_scraper/.env` exists (copy from `.env.example` if not)
2. For Indeed/LinkedIn results: ensure `RAPIDAPI_KEY` is set in `.env`; NVB works without a key
3. Verify `NVB_DCO_TITLE` matches a valid NVB taxonomy title for your role

### LaTeX compilation errors

- CV: uses `pdflatex` (standard LaTeX)
- Cover letter: uses `xelatex` (for custom fonts in `cover_letters/OpenFonts/fonts/`)
- Ensure your LaTeX distribution includes the `moderncv` package

### Fonts not found in cover letter

The cover letter template expects fonts in `cover_letters/OpenFonts/fonts/`. Make sure this directory exists and contains the Lato and Raleway font files.
