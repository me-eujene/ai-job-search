# Job Scraper Configuration

<!-- SETUP: Populated by /setup-job-agent -- section search -->
<!-- Describes the .env variables that control the Python scraper in job_scraper/ -->

## How the scraper is configured

The Python scraper in `job_scraper/` reads its search parameters from `job_scraper/.env`.
This file documents the current configuration for reference. Edit `.env` directly to change search behaviour.

---

## Active configuration

### Sources

| Source | Status | Auth |
|--------|--------|------|
| NVB (Nationale Vacaturebank) | Enabled | None |
| Indeed NL | Enabled — requires `RAPIDAPI_KEY` | RapidAPI key |
| LinkedIn NL | Enabled — requires `RAPIDAPI_KEY` | RapidAPI key |

---

### NVB settings

```
NVB_DCO_TITLE=[YOUR_PRIMARY_ROLE_TYPE]
NVB_CITY=[YOUR_CITY]
NVB_DISTANCE_KM=40
```

`NVB_DCO_TITLE` uses NVB's own job taxonomy (`dcoTitle` filter). Examples:
- `Productmanager` — covers Product Manager, Senior PM, Product Owner, Product Lead
- `Data Scientist`
- `Software Engineer`
- `Business Analyst`

To find valid taxonomy titles, search NVB and observe the `dcoTitle` value in the URL or network requests.

---

### Indeed NL / LinkedIn NL queries

```
SEARCH_QUERIES=[YOUR_PRIMARY_JOB_TITLE],[YOUR_SECONDARY_JOB_TITLE]
```

Comma-separated search terms sent to both Indeed NL and LinkedIn NL. These are full-text searches, so broader terms (e.g. `product manager`) work better than narrow ones.

---

### Title relevance filter (all sources)

```
TITLE_KEYWORDS=[YOUR_PRIMARY_JOB_TITLE],[YOUR_SECONDARY_JOB_TITLE],[YOUR_KEY_SKILL]
```

Client-side filter applied after fetching. A job is kept only if its title contains at least one of these phrases. This is the safety net for API noise — especially NVB, which can return off-topic results even with `dcoTitle`. Use lowercase, comma-separated phrases.

---

### Location scope

Target city and commute radius for NVB (NVB resolves coordinates automatically):

```
NVB_CITY=[YOUR_CITY]
NVB_DISTANCE_KM=[YOUR_RADIUS_KM]
```

For Indeed/LinkedIn, embed the city in `SEARCH_QUERIES` if needed (e.g. `product manager amsterdam`), since city-level filtering via API params is unreliable for NL.

Acceptable commute areas (for Claude to use when assessing fit):
- Ideal: [YOUR_CITY] and direct surroundings
- Acceptable: [ACCEPTABLE_AREA_1]
- Borderline: [BORDERLINE_AREA] (~X min by transit)
- Too far: [TOO_FAR_AREA]

---

## Updating this configuration

Re-run setup to reconfigure search without touching your profile:

```
/setup-job-agent-job-agent --section search
```

Or edit `job_scraper/.env` directly and restart the server:

```bash
cd job_scraper && python -m ui.server
```
