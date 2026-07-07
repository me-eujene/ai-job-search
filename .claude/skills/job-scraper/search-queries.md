# Job Scraper Configuration

<!-- SETUP: Populated by /job-scraper-setup -- section search -->
<!-- Describes the .env variables that control the Python scraper in job_scraper/ -->

## How the scraper is configured

The Python scraper in `job_scraper/` reads its search parameters from `job_scraper/.env`.
This file documents the current configuration for reference. Edit `.env` directly to change search behaviour.

---

## Active configuration

### Sources

| Source | Status | Auth |
|--------|--------|------|
| LinkedIn NL | Enabled | None |
| NVB (Nationale Vacaturebank) | Enabled | None |
| hiring.cafe | Enabled | None |
| Adzuna NL | Enabled | ADZUNA_APP_ID, ADZUNA_APP_KEY |
| We Work Remotely (WWR) | Enabled | None |
| Welcome to the Jungle (WTTJ) | Enabled | None |
| Working Nomads | Enabled | None |

---

### Search queries

```
SEARCH_QUERIES=product manager,product owner,product lead,head of product
```

Full-text search queries sent to LinkedIn NL, hiring.cafe, and Adzuna NL. Comma-separated for multiple queries. Each additional query gives hiring.cafe an extra public results page (~60 results per query).

LinkedIn runs two passes per query:
- Amsterdam-area jobs (location radius: 40 km)
- Country-wide remote jobs (f_WT=2)

---

### NVB (Nationale Vacaturebank) settings

```
NVB_DCO_TITLE=Productmanager
NVB_CITY=Amsterdam
NVB_DISTANCE_KM=40
```

NVB uses server-side job taxonomy (`dcoTitle` filter). The value `Productmanager` covers Product Manager, Senior PM, Product Owner, Product Lead, etc. per NVB's own classification.

NVB resolves city coordinates automatically and applies a radius filter.

---

### Title relevance filter (all sources)

```
TITLE_KEYWORDS=product manager,product owner,product lead,head of product,director of product,product director,vp product,chief product,productmanager,producteigenaar
```

Client-side filter applied after fetching — a job is kept only if its title contains at least one of these phrases. This is the safety net for API noise; especially NVB can return off-topic results even with `dcoTitle`. Use lowercase, comma-separated phrases.

---

### Description enrichment (post-dedup)

Max detail-page fetches per run, per source:

```
LINKEDIN_MAX_DETAIL_FETCHES=30
ADZUNA_MAX_DETAIL_FETCHES=50
HIRINGCAFE_MAX_DETAIL_FETCHES=80
```

After deduplication, the scraper fetches full job descriptions from detail pages up to these limits per source per run.

---

### Lookback (automatic)

Lookback windows are computed automatically from the gap since the last successful run, typically 14–30 days. There is no per-source lookback env var.

---

## Updating this configuration

Re-run setup to reconfigure search without touching your profile:

```
/job-scraper-setup --section search
```

Or edit `job_scraper/.env` directly:

```bash
# Edit job_scraper/.env and save. The scraper will pick up changes on the next run.
```
