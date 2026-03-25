<p align="center">
  <img src="claude_animation.gif" alt="Claude Job Search Assistant" width="200">
</p>

# AI Job Search

An AI-powered job application framework built on [Claude Code](https://claude.com/claude-code). Fork it, fill in your profile, and let Claude evaluate job postings, tailor your CV, write cover letters, and prepare you for interviews.

## What this is

A structured workflow that turns Claude Code into a full-stack job application assistant. The core workflow (self-profiling, fit evaluation, and the drafter-reviewer application pipeline) is **language- and country-agnostic**. The job portal search tools are built for the **Dutch market** (Indeed NL, LinkedIn NL, Nationale Vacaturebank), but the pattern is designed to be swapped for your local job boards.

```
/setup-job-agent          /scrape              /apply <url>
  |                |                     |
  v                v                     v
Fill in        Run Python           Evaluate fit
your profile   job scraper          Score & recommend
  |                |                     |
  v                v                     v
Profile        Present matches      Draft CV + Cover Letter
files ready    with fit ratings     (LaTeX, tailored)
                   |                     |
                   v                     v
               Pick a match         Reviewer agent critiques
               -> /apply            -> Revise -> Final output
```

The framework encodes career guidance best practices, including structured evaluation criteria and forward-looking cover letter framing.

## Prerequisites

- [Claude Code](https://claude.com/claude-code) (CLI)
- Python 3.10+
- LaTeX distribution (for compiling CVs and cover letters): [TeX Live](https://tug.org/texlive/) or [MiKTeX](https://miktex.org/)

## Quick start

### 1. Fork and clone

```bash
gh repo fork <your-fork> --clone
cd ai-job-search
```

### 2. Install job scraper dependencies

```bash
pip install -r job_scraper/requirements.txt
```

### 3. Configure the scraper

```bash
cp job_scraper/.env.example job_scraper/.env
# Edit .env: add your RAPIDAPI_KEY and adjust search queries / location
```

The RapidAPI key powers Indeed NL and LinkedIn NL fetchers (free tier: 200 requests/month). NVB (Nationale Vacaturebank) requires no key.

### 4. Set up your profile

```bash
claude
# Then inside Claude Code:
/setup-job-agent
```

Claude will ask about your background, skills, and career goals, then populate all profile files automatically. You can import from an existing CV or answer questions interactively.

### 5. Search for jobs

```bash
/scrape
```

This starts the Python scraper, fetches from all configured sources, deduplicates against previously seen jobs, and presents matches sorted by fit. Pick a match to run `/apply` on it directly.

### 6. Apply to a job

```bash
/apply https://www.linkedin.com/jobs/view/123456789
```

If the URL can't be fetched (some portals block automated access), paste the job description directly:

```bash
/apply <paste the full job description here>
```

This runs the full workflow: evaluate fit, draft CV + cover letter, review with a second agent, revise, and present the final output.

## File structure

```
ai-job-search/
├── CLAUDE.md                          # Main candidate profile + workflow rules
├── .claude/
│   ├── commands/
│   │   ├── apply.md                   # /apply workflow (drafter-reviewer)
│   │   └── setup-job-agent.md          # /setup-job-agent onboarding interview
│   ├── skills/
│   │   ├── job-application-assistant/  # Core application skill
│   │   │   ├── SKILL.md               # Skill definition
│   │   │   ├── 01-candidate-profile.md
│   │   │   ├── 02-behavioral-profile.md
│   │   │   ├── 03-writing-style.md
│   │   │   ├── 04-job-evaluation.md
│   │   │   ├── 05-cv-templates.md
│   │   │   ├── 06-cover-letter-templates.md
│   │   │   └── 07-interview-prep.md
│   │   └── job-scraper/               # Job search orchestration skill
│   │       ├── SKILL.md
│   │       └── search-queries.md      # Populated by /setup-job-agent
│   └── settings.local.json            # Claude Code permissions
├── job_scraper/                       # Python job scraper (NL market)
│   ├── src/
│   │   ├── pipeline.py                # Orchestrates all fetchers
│   │   ├── state.py                   # SQLite deduplication store
│   │   ├── types.py                   # Job dataclass + canonical key
│   │   ├── helpers.py                 # HTTP client, date utils, title filter
│   │   └── fetchers/
│   │       ├── indeed.py              # Indeed NL via RapidAPI (jobs-api14)
│   │       ├── linkedin.py            # LinkedIn NL via RapidAPI (jobs-api14)
│   │       └── nvb.py                 # Nationale Vacaturebank (public API)
│   ├── .env.example                   # Configuration template
│   └── requirements.txt
├── cv/
│   └── main_example.tex               # moderncv LaTeX template
├── cover_letters/
│   ├── cover.cls                      # Custom cover letter LaTeX class
│   └── OpenFonts/                     # Lato + Raleway fonts
├── job_search_tracker.csv             # Application tracking spreadsheet
└── SETUP.md                           # Detailed setup guide
```

## How `/apply` works

The `/apply` command runs a **drafter-reviewer workflow**:

1. **Parse** the job posting (URL or text)
2. **Evaluate fit** against your profile (skills, experience, culture, location, career alignment)
3. **Draft** a tailored CV and cover letter in LaTeX
4. **Spawn a reviewer agent** that researches the company and critiques the drafts
5. **Revise** based on the reviewer's feedback
6. **Present** the final output with a verification checklist

All claims in the CV and cover letter are verified against your actual profile. The system never fabricates skills or experience.

## How the job scraper works

The `job_scraper/` pipeline is a Python service with three fetchers:

| Source | Approach | Auth |
|--------|----------|------|
| **NVB** (Nationale Vacaturebank) | Public REST API with `dcoTitle` + location filters | None |
| **Indeed NL** | RapidAPI (jobs-api14) | `RAPIDAPI_KEY` |
| **LinkedIn NL** | RapidAPI (jobs-api14) | `RAPIDAPI_KEY` |

All sources feed into a shared deduplication store (SQLite). Claude runs `python -m job_scraper` directly — no server process needed. Results are written to `job_scraper/last_run.json` and read back by Claude via the Read tool.

## Customization

### Which files to edit manually

If you prefer editing files directly instead of using `/setup-job-agent`:

| File | What to change |
|------|---------------|
| `CLAUDE.md` | Your full profile (name, education, experience, skills, goals) |
| `01-candidate-profile.md` | Structured version of your CV data |
| `02-behavioral-profile.md` | Your behavioral assessment or self-assessment |
| `04-job-evaluation.md` | Skill match areas, career goals, motivation filters |
| `05-cv-templates.md` | Profile statement templates for different role types |
| `07-interview-prep.md` | Your STAR examples from actual experience |
| `search-queries.md` | Job search queries (used by some WebSearch fallback paths) |

### Configuring the scraper

Edit `job_scraper/.env` to adjust:
- `SEARCH_QUERIES` — comma-separated queries sent to Indeed and LinkedIn
- `NVB_DCO_TITLE` — NVB's taxonomy title (e.g. `Productmanager`, `Data Scientist`)
- `NVB_CITY` / `NVB_DISTANCE_KM` — location filter
- `TITLE_KEYWORDS` — client-side relevance filter applied to all sources

### LaTeX templates

The CV uses [moderncv](https://ctan.org/pkg/moderncv) (banking style). The cover letter uses a custom `cover.cls` with Lato/Raleway fonts. You can replace these with your own templates; just update the guidance in `05-cv-templates.md` and `06-cover-letter-templates.md`.

## Tips for better results

**Profile depth matters.** The single biggest factor in output quality is how much detail you put into your profile. Role descriptions with specific projects, tools, and measurable achievements give the system far more to work with than a list of job titles.

**Skills in context.** Instead of listing "Python", describe how you applied it: "Built ML pipelines for customer churn prediction using scikit-learn" gives sharper tailoring than "Python, machine learning."

**Career path discovery.** The framework supports two modes: explicit targeting (you know which roles you want) and latent opportunity discovery (the system surfaces paths you haven't considered, based on your full history). During `/setup-job-agent`, invest time describing what energized you and what you'd want more of — this directly shapes fit evaluation.

## Acknowledgements

- [Mikkel Krogholm](https://github.com/mikkelkrogsholm) for the original job search CLI skill pattern this project builds on
- Built with [Claude Code](https://claude.com/claude-code) by [Anthropic](https://anthropic.com)

## License

MIT
