<p align="center">
  <img src="claude_animation.gif" alt="Claude Job Search Assistant" width="200">
</p>

# AI Job Search

An AI-powered job application framework built on [Claude Code](https://claude.com/claude-code). Fork it, fill in your profile, and let Claude evaluate job postings, tailor your CV, write cover letters, and prepare you for interviews.

## What this is

A structured workflow that turns Claude Code into a full-stack job application assistant. The core workflow (self-profiling, fit evaluation, and the drafter-reviewer application pipeline) is **language- and country-agnostic**. The job portal search tools mix Dutch-market sources (LinkedIn NL, Nationale Vacaturebank, Adzuna NL) with global remote-friendly sources (hiring.cafe, We Work Remotely, Welcome to the Jungle, Working Nomads), but the pattern is designed to be swapped for your local job boards.

```
/job-scraper-setup            /search                          /job-scraper-apply <url>
  |                              |                                        |
  v                              v                                        v
Fill in                   Run Python job scraper                  Evaluate fit
your profile              Batch-evaluate fit                      Score & recommend
  |                              |                                        |
  v                              v                                        v
Profile                  Ranked shortlist                    Candidate interview
files ready               presented                          Voice + authenticity inputs
                                |                                        |
                                v                                        v
                          Pick a role                        Draft CV + Cover Letter
                          (continues below)  ---------->     Framing approved before writing
                                                                          |
                                                                          v
                                                              Reviewer agent critiques
                                                              -> Revise -> Render to PDF
```

Two entry points: `/search` runs the full pipeline (fetch → batch assess → shortlist → per-role apply); `/job-scraper-apply <url or text>` skips straight to evaluating and applying to one role you already have in hand.

The framework encodes career guidance best practices, including structured evaluation criteria and forward-looking cover letter framing.

## Prerequisites

- [Claude Code](https://claude.com/claude-code) (CLI)
- Python 3.10+ and [uv](https://docs.astral.sh/uv/) (the scraper is run via `uv run`)
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
# Edit .env: adjust search queries, NVB location, and title keywords
```

No API keys required for six of the seven sources. **Adzuna NL** needs a free App ID/App Key from [developer.adzuna.com](https://developer.adzuna.com) — without it, Adzuna is silently skipped and the rest still run.

### 4. Set up your profile

```bash
claude
# Then inside Claude Code:
/job-scraper-setup
```

Claude will ask about your background, skills, and career goals, then populate all profile files automatically. You can import from an existing CV or answer questions interactively.

### 5. Search and apply, end to end

```bash
/search
```

This runs the Python scraper, fetches from all configured sources, deduplicates against previously seen jobs, evaluates fit against your profile, and presents a ranked shortlist. Pick a role and the same session continues straight into the apply workflow (interview → draft → review → revise → render).

### 6. Apply to a specific job directly

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
├── CLAUDE.md                          # Workflow rules + pipeline phases (Phase 0-8)
├── .claude/
│   ├── commands/
│   │   ├── search.md                  # /search — full pipeline orchestrator
│   │   ├── job-scraper-apply.md       # /job-scraper-apply — single-role shortcut
│   │   └── job-scraper-setup.md       # /job-scraper-setup onboarding interview
│   ├── skills/
│   │   ├── job-application-assistant/  # Core application skill
│   │   │   ├── SKILL.md               # Skill definition
│   │   │   ├── 01-candidate-profile.md  # Identity, experience, Claims Inventory
│   │   │   ├── 02-behavioral-profile.md
│   │   │   ├── 03-writing-style.md
│   │   │   ├── 04-job-evaluation.md
│   │   │   ├── 05-cv-templates.md
│   │   │   ├── 06-cover-letter-templates.md
│   │   │   ├── 07-latex-renderer-rules.md
│   │   │   ├── 08-writing-style-review.md
│   │   │   └── 09-interview-prep.md
│   │   ├── job-evaluate/               # Fit-scoring skill
│   │   ├── job-writer/                 # Interview + draft + revise skill
│   │   ├── job-reviewer/               # Independent reviewer prompt template
│   │   ├── latex-renderer/             # Markdown -> LaTeX -> PDF skill
│   │   └── job-scraper/               # Job search orchestration skill
│   │       ├── SKILL.md
│   │       └── search-queries.md      # Populated by /job-scraper-setup
│   └── settings.local.json            # Claude Code permissions
├── job_scraper/                       # Python job scraper
│   ├── src/
│   │   ├── pipeline.py                # Orchestrates all fetchers
│   │   ├── state.py                   # SQLite deduplication store
│   │   ├── types.py                   # Job dataclass + canonical key
│   │   ├── ats.py / enrich.py          # Description enrichment (post-dedup)
│   │   ├── helpers.py                 # HTTP client, date utils, title filter
│   │   └── fetchers/
│   │       ├── adzuna.py              # Adzuna NL public search API (needs API key)
│   │       ├── hiringcafe.py          # hiring.cafe public Next.js SSR endpoint
│   │       ├── linkedin.py            # LinkedIn NL guest API (no auth)
│   │       ├── nvb.py                 # Nationale Vacaturebank (public API)
│   │       ├── workingnomads.py       # Working Nomads (public Elasticsearch endpoint)
│   │       ├── wttj.py                # Welcome to the Jungle (public Algolia index)
│   │       └── wwr.py                 # We Work Remotely (public RSS feed)
│   ├── tests/                          # pytest suite
│   ├── .env.example                   # Configuration template
│   └── requirements.txt
├── applications/                      # Per-application output folders
│   └── <company>-<role>/
│       ├── eval.md, cv.md, cover.md   # Editorial drafts (markdown)
│       ├── main_<company>.tex         # Rendered CV
│       └── cover_<company>_<role>.tex # Rendered cover letter
├── cv/
│   └── main_example.tex               # moderncv LaTeX CV template seed
├── cover_letters/
│   ├── cover.cls                      # Custom cover letter LaTeX class
│   └── OpenFonts/                     # Lato + Raleway fonts
├── job_search_tracker.csv             # Application tracking spreadsheet
└── SETUP.md                           # Detailed setup guide
```

## Commands

| Command | What it does |
|---------|-------------|
| `/job-scraper-setup` | Profile onboarding interview — populates all profile files from your CV or via Q&A. Re-run with `--section search` to update search config only. |
| `/search` | Full pipeline — runs the Python job scraper, deduplicates results, evaluates fit against your profile, presents a ranked shortlist, then continues straight into the apply workflow for whichever role you pick. |
| `/job-scraper-apply <url or text>` | Single-role shortcut — skips fetch/batch, evaluates fit for one posting, drafts a tailored CV + cover letter, runs a reviewer agent, and presents the final output. |

---

## How the application workflow works

Once you're evaluating a specific role — whether via `/search`'s shortlist or `/job-scraper-apply` directly — the same **drafter-reviewer workflow** runs in six steps:

1. **Parse** the job posting (URL or pasted text)
2. **Evaluate fit** — scores the role against your profile across skills, experience, culture, and career alignment; asks for go/no-go before proceeding
3. **Candidate interview** — two short question sets before any drafting begins: one on what's relevant from your experience and how you work; one on why this role interests you. Your answers become the raw material for capability claims and motivation. The agent edits your words — it doesn't generate them from the profile.
4. **Draft** — tailors CV and cover letter to the role. Proposes the cover letter framing (opening angle + motivation) and waits for your approval before writing. Two paths: PATH A for minor changes to an existing PDF/doc CV; PATH B for a full LaTeX rewrite into `applications/<company>-<role>/`.
5. **Reviewer agent** — a second agent researches the company, extracts role keywords, and critiques the drafts for missed requirements, passive language, inauthenticity against your stated inputs, and style issues
6. **Revise and present** — integrates reviewer feedback, then summarises the key tailoring decisions before finalising the files

The system enforces a strict no-fabrication rule: every claim is grounded in your actual profile. Stretch bullets are flagged with an explicit keep/soften/drop prompt.

## How the job scraper works

The `job_scraper/` pipeline is a Python CLI with seven fetchers:

| Source | Approach | Auth |
|--------|----------|------|
| **hiring.cafe** | Public Next.js SSR data endpoint (`/_next/data/<build_id>/index.json`) — returns the first results page without auth | None |
| **LinkedIn NL** | Public guest API (`/jobs-guest/` endpoint) — HTML fragments parsed with BeautifulSoup | None |
| **NVB** (Nationale Vacaturebank) | Public REST API with `dcoTitle` + location filters | None |
| **Adzuna NL** | Public search API (`/api/v1/jobs/nl/search`) — results fetched by keyword query | Free API key |
| **We Work Remotely** | Public RSS feed (Product Jobs) — global remote listings | None |
| **Welcome to the Jungle** | Public Algolia index — global remote-friendly PM/technical-PM roles | None |
| **Working Nomads** | Public Elasticsearch endpoint (`/jobsapi/_search`), Management category | None |

Sources run concurrently and feed into a shared deduplication store (SQLite), with per-source description enrichment applied post-dedup. Claude runs `uv run python -m job_scraper` directly — no server process needed. Results are written to `job_scraper/last_run.json` and read back by Claude via the Read tool.

## Customization

### Which files to edit manually

If you prefer editing files directly instead of using `/job-scraper-setup`:

| File | What to change |
|------|---------------|
| `01-candidate-profile.md` | Your full profile: identity, education, experience, Core Definition (single-line identity), Claims Inventory (capability/exposure/hygiene claims), Framing Notes, career goals |
| `02-behavioral-profile.md` | Your behavioral assessment or self-assessment |
| `04-job-evaluation.md` | Skill match areas, career goals, motivation filters |
| `05-cv-templates.md` | CV section rules — tied to the Claims Inventory in `01-candidate-profile.md` |
| `09-interview-prep.md` | Your STAR examples from actual experience |
| `search-queries.md` | Job search queries used by the scraper |

`CLAUDE.md` holds workflow rules, not profile data — it references `01-candidate-profile.md` instead of duplicating it.

### Configuring the scraper

Edit `job_scraper/.env` to adjust:
- `SEARCH_QUERIES` — comma-separated queries sent to LinkedIn, hiring.cafe, and Adzuna
- `NVB_DCO_TITLE` — NVB's taxonomy title (e.g. `Productmanager`, `Data Scientist`)
- `NVB_CITY` / `NVB_DISTANCE_KM` — location filter
- `TITLE_KEYWORDS` — client-side relevance filter applied to all sources
- `ADZUNA_APP_ID` / `ADZUNA_APP_KEY` — required for the Adzuna source only

### LaTeX templates

The CV uses [moderncv](https://ctan.org/pkg/moderncv) (banking style). The cover letter uses a custom `cover.cls` with Lato/Raleway fonts. You can replace these with your own templates; just update the guidance in `05-cv-templates.md` and `06-cover-letter-templates.md`.

## Tips for better results

**Profile depth matters.** The single biggest factor in output quality is how much detail you put into your profile. Role descriptions with specific projects, tools, and measurable achievements give the system far more to work with than a list of job titles.

**Skills in context.** Instead of listing "Python", describe how you applied it: "Built ML pipelines for customer churn prediction using scikit-learn" gives sharper tailoring than "Python, machine learning."

**Career path discovery.** The framework supports two modes: explicit targeting (you know which roles you want) and latent opportunity discovery (the system surfaces paths you haven't considered, based on your full history). During `/job-scraper-setup`, invest time describing what energized you and what you'd want more of — this directly shapes fit evaluation.

## Acknowledgements

- [Mads Lorentzen](https://github.com/MadsLorentzen) — the Claude Code skill files (`01–09`), LaTeX CV/cover letter templates, and application workflow in this repo are adapted from his [ai-job-search](https://github.com/MadsLorentzen/ai-job-search) original. The Python job scraper was rebuilt independently.
- Built with [Claude Code](https://claude.com/claude-code) by [Anthropic](https://anthropic.com)

## License

MIT
