<p align="center">
  <img src="claude_animation.gif" alt="Claude Job Search Assistant" width="200">
</p>

# AI Job Search

An AI-powered job application framework built on [Claude Code](https://claude.com/claude-code). Fork it, fill in your profile, and let Claude evaluate job postings, tailor your CV, write cover letters, and prepare you for interviews.

## What this is

A structured workflow that turns Claude Code into a full-stack job application assistant. The core workflow (self-profiling, fit evaluation, and the drafter-reviewer application pipeline) is **language- and country-agnostic**. The job portal search tools are built for the **Dutch market** (hiring.cafe, LinkedIn NL, Nationale Vacaturebank, Adzuna NL), but the pattern is designed to be swapped for your local job boards.

```
/job-scraper-setup      /job-scraper-run          /job-scraper-apply <url>
  |                           |                              |
  v                           v                              v
Fill in                 Run Python                   Evaluate fit
your profile            job scraper                  Score & recommend
  |                           |                              |
  v                           v                              v
Profile               Present matches              Candidate interview
files ready           with fit ratings             Voice + authenticity inputs
                            |                              |
                            v                              v
                      Pick a match              Draft CV + Cover Letter
                      -> /job-scraper-apply      Framing approved before writing
                                                 (PATH A: PDF edits /
                                                  PATH B: LaTeX)
                                                           |
                                                           v
                                                  Reviewer agent critiques
                                                  -> Revise -> Final output
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
playwright install chromium   # one-time: needed for hiring.cafe Cloudflare bypass
```

### 3. Configure the scraper

```bash
cp job_scraper/.env.example job_scraper/.env
# Edit .env: adjust search queries, NVB location, and title keywords
```

No API keys required — all four sources use public endpoints.

### 4. Set up your profile

```bash
claude
# Then inside Claude Code:
/job-scraper-setup
```

Claude will ask about your background, skills, and career goals, then populate all profile files automatically. You can import from an existing CV or answer questions interactively.

### 5. Search for jobs

```bash
/job-scraper-run
```

This starts the Python scraper, fetches from all configured sources, deduplicates against previously seen jobs, and presents matches sorted by fit. Pick a match to run `/job-scraper-apply` on it directly.

### 6. Apply to a job

```bash
/job-scraper-apply https://www.linkedin.com/jobs/view/123456789
```

If the URL can't be fetched (some portals block automated access), paste the job description directly:

```bash
/job-scraper-apply <paste the full job description here>
```

This runs the full workflow: evaluate fit, draft CV + cover letter, review with a second agent, revise, and present the final output.

## File structure

```
ai-job-search/
├── CLAUDE.md                          # Main candidate profile + workflow rules
├── .claude/
│   ├── commands/
│   │   ├── job-scraper-apply.md       # /job-scraper-apply workflow (drafter-reviewer)
│   │   └── job-scraper-setup.md       # /job-scraper-setup onboarding interview
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
│   │       └── search-queries.md      # Populated by /job-scraper-setup
│   └── settings.local.json            # Claude Code permissions
├── job_scraper/                       # Python job scraper (NL market)
│   ├── src/
│   │   ├── pipeline.py                # Orchestrates all fetchers
│   │   ├── state.py                   # SQLite deduplication store
│   │   ├── types.py                   # Job dataclass + canonical key
│   │   ├── helpers.py                 # HTTP client, date utils, title filter
│   │   └── fetchers/
│   │       ├── adzuna.py              # Adzuna NL public search API
│   │       ├── hiringcafe.py          # hiring.cafe (Cloudflare bypass via Playwright)
│   │       ├── linkedin.py            # LinkedIn NL guest API (no auth)
│   │       └── nvb.py                 # Nationale Vacaturebank (public API)
│   ├── .env.example                   # Configuration template
│   └── requirements.txt
├── applications/                      # Per-application output folders
│   └── <company>-<role>/
│       ├── main_<company>.tex         # Tailored CV (PATH B)
│       └── cover_<company>_<role>.tex # Cover letter (PATH B)
├── templates/
│   ├── main_example.tex               # moderncv LaTeX CV template
│   ├── cover.cls                      # Custom cover letter LaTeX class
│   └── OpenFonts/                     # Lato + Raleway fonts
├── job_search_tracker.csv             # Application tracking spreadsheet
└── SETUP.md                           # Detailed setup guide
```

## Commands

| Command | What it does |
|---------|-------------|
| `/job-scraper-setup` | Profile onboarding interview — populates all profile files from your CV or via Q&A. Re-run with `--section search` to update search config only. |
| `/job-scraper-run` | Runs the Python job scraper, deduplicates results, evaluates fit against your profile, and presents a ranked table of new positions. |
| `/job-scraper-apply <url or text>` | Full application workflow — evaluates fit, drafts a tailored CV + cover letter in LaTeX, runs a reviewer agent, and presents the final output. |

---

## How `/job-scraper-apply` works

The `/job-scraper-apply` command runs a **drafter-reviewer workflow** in six steps:

1. **Parse** the job posting (URL or pasted text)
2. **Evaluate fit** — scores the role against your profile across skills, experience, culture, and career alignment; asks for go/no-go before proceeding
3. **Candidate interview** — two short question sets before any drafting begins: one on what's relevant from your experience and how you work; one on why this role interests you. Your answers become the raw material for capability claims and motivation. The agent edits your words — it doesn't generate them from the profile.
4. **Draft** — tailors CV and cover letter to the role. Proposes the cover letter framing (opening angle + motivation) and waits for your approval before writing. Two paths: PATH A for minor changes to an existing PDF/doc CV; PATH B for a full LaTeX rewrite into `applications/<company>-<role>/`.
5. **Reviewer agent** — a second agent researches the company, extracts role keywords, and critiques the drafts for missed requirements, passive language, inauthenticity against your stated inputs, and style issues
6. **Revise and present** — integrates reviewer feedback, then summarises the key tailoring decisions before finalising the files

The system enforces a strict no-fabrication rule: every claim is grounded in your actual profile. Stretch bullets are flagged with an explicit keep/soften/drop prompt.

## How the job scraper works

The `job_scraper/` pipeline is a Python CLI with four fetchers:

| Source | Approach | Auth |
|--------|----------|------|
| **hiring.cafe** | Search API (`/api/search-jobs`) — Cloudflare bypass via `cf-clearance` (Playwright stealth browser, runs once per scrape) | None |
| **LinkedIn NL** | Public guest API (`/jobs-guest/` endpoint) — HTML fragments parsed with BeautifulSoup | None |
| **NVB** (Nationale Vacaturebank) | Public REST API with `dcoTitle` + location filters | None |
| **Adzuna NL** | Public search API (`/api/v1/jobs/nl/search`) — results fetched by keyword query | None |

All sources feed into a shared deduplication store (SQLite). Claude runs `python -m job_scraper` directly — no server process needed. Results are written to `job_scraper/last_run.json` and read back by Claude via the Read tool.

## Customization

### Which files to edit manually

If you prefer editing files directly instead of using `/job-scraper-setup`:

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
- `SEARCH_QUERIES` — comma-separated queries sent to LinkedIn and hiring.cafe
- `NVB_DCO_TITLE` — NVB's taxonomy title (e.g. `Productmanager`, `Data Scientist`)
- `NVB_CITY` / `NVB_DISTANCE_KM` — location filter
- `TITLE_KEYWORDS` — client-side relevance filter applied to all sources

### LaTeX templates

The CV uses [moderncv](https://ctan.org/pkg/moderncv) (banking style). The cover letter uses a custom `cover.cls` with Lato/Raleway fonts. You can replace these with your own templates; just update the guidance in `05-cv-templates.md` and `06-cover-letter-templates.md`.

## Tips for better results

**Profile depth matters.** The single biggest factor in output quality is how much detail you put into your profile. Role descriptions with specific projects, tools, and measurable achievements give the system far more to work with than a list of job titles.

**Skills in context.** Instead of listing "Python", describe how you applied it: "Built ML pipelines for customer churn prediction using scikit-learn" gives sharper tailoring than "Python, machine learning."

**Career path discovery.** The framework supports two modes: explicit targeting (you know which roles you want) and latent opportunity discovery (the system surfaces paths you haven't considered, based on your full history). During `/job-scraper-setup`, invest time describing what energized you and what you'd want more of — this directly shapes fit evaluation.

## Acknowledgements

- [Mads Lorentzen](https://github.com/MadsLorentzen) — the Claude Code skill files (`01–07`), LaTeX CV/cover letter templates, and application workflow in this repo are adapted from his [ai-job-search](https://github.com/MadsLorentzen/ai-job-search) original. The Python job scraper was rebuilt independently.
- Built with [Claude Code](https://claude.com/claude-code) by [Anthropic](https://anthropic.com)

## License

MIT
