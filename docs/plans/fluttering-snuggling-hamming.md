# Plan: Fix divergences identified from conversation review

## Context

Reviewing the conversation where `/setup-job-agent` (command) and `job-scraper` (skill) were executed for the first time against their definitions, to identify where behavior diverged from spec or real-usage gaps were exposed.

**File taxonomy:**
- **Commands** (user-invoked with `/`): `.claude/commands/setup-job-agent.md`, `.claude/commands/apply.md`
- **Skill** (auto-loaded by trigger): `.claude/skills/job-scraper/SKILL.md` + reference files in `job-application-assistant/`
- **Python pipeline**: `job_scraper/src/fetchers/`

---

## Divergences Found

### 1. `SKILL.md` — Blocklist not enforced before presenting results

**Spec intent:** Blocklisted companies (TomTom B.V., Bunq) should never be surfaced.

**What happened:** TomTom (#26) and Bunq (#27) both appeared in the results table. I flagged TomTom as a deal-breaker in a note but still showed it. Bunq was listed as "High" fit — the user had to explicitly add it to the blocklist after seeing it.

**Fix:** Add an explicit pre-display filter step to `SKILL.md` — before building the results table, silently drop any job whose company matches the CLAUDE.md deal-breaker list. Do not count them in totals or mention them.

---

### 2. `linkedin.py` — Blank company names (already fixed)

**What happened:** All LinkedIn jobs had blank company names and no `apply_url` because the API returns `companyName`/`linkedinUrl` but the normaliser looked for `organization`/`detailsPageUrl`. This made blocklist enforcement impossible for LinkedIn results.

**Fix already applied** in `job_scraper/src/fetchers/linkedin.py`.

**Remaining side-effect:** The 8 blank-company LinkedIn entries are now in `state.db` with canonical keys built on empty company names. On the next full run, the same jobs (with correct company names) will generate different canonical keys and re-appear as "new". Need to purge the ghost entries from `state.db`.

---

### 3. `indeed.py` — Blank location and apply_url (not yet fixed)

**What happened:** All 18 Indeed jobs had blank `location` and `apply_url` in the output. Same root cause as LinkedIn — field name mismatch between what the API returns and what `_normalise` reads.

**Fix:** Inspect raw Indeed API response (same debug pattern used for LinkedIn), then update `indeed.py` field mappings.

---

### 4. `search-queries.md` — Placeholder remnants in prose block

**What happened:** The NVB settings code fence was correctly updated, but the prose `Location scope` section below it still has `[YOUR_CITY]` / `[YOUR_RADIUS_KM]` tokens.

**Fix:** Replace those two tokens with `Amsterdam` and `40` in `search-queries.md`.

---

### 5. `setup-job-agent.md` (command) — Skipped proactive role suggestions

**Spec says (Section 9):** Proactively suggest role types the user may not have considered (Technical Consultant, Solutions Engineer, adjacent sectors).

**What happened:** Skipped — the user confirmed memory was correct and I jumped to file generation.

**Fix:** This is a behavior gap in the command spec. The command should make suggestions mandatory even when importing from an existing profile, not just in interview mode. Add a note to the Section 9 block.

---

### 6. `setup-job-agent.md` (command) — Didn't surface the existing RapidAPI key

**Spec says:** Ask about RapidAPI key; if provided, write to `.env`. If not, note only NVB will be active.

**What happened:** Key was already in `.env` — I silently used it without reporting it to the user.

**Fix:** Add a check step: if `.env` already has `RAPIDAPI_KEY` set, report it to the user ("Your RapidAPI key is already configured — Indeed NL and LinkedIn NL are active") rather than re-asking or silently proceeding.

---

## Files to Change

| File | Change type |
|------|-------------|
| `.claude/skills/job-scraper/SKILL.md` | Add blocklist filter step before presenting results |
| `.claude/skills/job-scraper/search-queries.md` | Replace 2 placeholder tokens |
| `.claude/commands/setup-job-agent.md` | (a) Mandate proactive role suggestions even in import path; (b) check for existing RAPIDAPI_KEY before asking |
| `job_scraper/src/fetchers/indeed.py` | Fix field name mismatches for location and apply_url |
| `job_scraper/state.db` | Purge 8 blank-company LinkedIn ghost entries |

---

## Implementation Steps

### Step 1: Fix search-queries.md placeholders
Two-line edit: `[YOUR_CITY]` → `Amsterdam`, `[YOUR_RADIUS_KM]` → `40` in the Location scope prose block.

### Step 2: Purge state.db ghost entries
```sql
DELETE FROM jobs WHERE source = 'linkedin' AND company = '';
```
Run via `python -c "import sqlite3; ..."` or direct sqlite3 invocation.

### Step 3: Diagnose and fix indeed.py
```python
# Debug: print raw Indeed API response shape (first job)
```
Then update `_normalise` in `job_scraper/src/fetchers/indeed.py` with correct field names, following the same pattern as the LinkedIn fix.

### Step 4: Update SKILL.md — add blocklist filter
In the "Present Results" step (Step 5), add before the table:
> Before building the results table, read the deal-breakers list from CLAUDE.md. Silently drop any job whose company name matches a blocklisted company (TomTom B.V., Bunq, or any others listed). Do not include them in counts or mention them.

### Step 5: Update setup-job-agent.md (command)
Two targeted edits to the Section 9 block:
- Add: if `.env` already contains `RAPIDAPI_KEY`, report its presence rather than re-asking
- Add: role suggestion step is mandatory even in Path A (CV import), not only in Path B (interview mode)

---

## Verification

1. `python -m job_scraper --sources linkedin` — confirm company names and URLs present
2. `python -m job_scraper --sources indeed` — confirm location and apply_url populated
3. Full `python -m job_scraper` — confirm TomTom and Bunq do not appear in Claude's output table
4. Read `search-queries.md` — confirm no `[PLACEHOLDER]` tokens remain
