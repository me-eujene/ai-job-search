# Netherlands job board CLI: refactor spec

## Overview

This document maps each existing Danish CLI tool to a Dutch equivalent and specifies the
API approach, command interface, and open questions for each. The goal is to produce four
new skills under `.agents/skills/` that mirror the structure of the Danish tools:
`search` + `detail` commands, consistent flag names, three output formats
(`json` / `table` / `plain`), and errors to stderr as `{ "error": "...", "code": "..." }`.

---

## Data quality assessment

Before committing to any board, it is worth understanding what each actually covers in the
Dutch market. The boards vary significantly in volume, audience fit, and data freshness.

| Board | Active listings | Monthly visits | Quality score | Audience fit | Key weakness |
|---|---|---|---|---|---|
| Nationale Vacaturebank | ~64K–80K | 1.5M | 6.8/10 | All sectors, all levels | Score reflects older review data |
| Werk.nl (UWV) | ~267K | High (gov) | Moderate | Blue/grey collar, public sector | Poorly covers knowledge/professional roles |
| Intermediair.nl | ~2K | 858K | 7.6/10 | HBO/WO graduates, professionals | Very low volume |
| Adzuna NL | Unknown for NL | Moderate | Low global share (0.05%) | Broad aggregator | Duplicate/stale listings; small NL market share |
| Indeed NL (MCP) | Massive (45–50% of global listings) | Dominant | High | All sectors, all levels | See Indeed MCP section below |

### Key findings

**NVB** is the strongest general-purpose board: high volume, broad coverage, and a public API
that is already partially documented. The 6.8/10 score reflects an older review; the platform
remains the most popular career site in the Netherlands for ten consecutive years.

**Werk.nl** has the highest raw listing count (267K as of August 2025, up 57% year-on-year)
but is structurally skewed towards blue-collar, logistics, care, and public sector roles. UWV
explicitly notes that highly skilled and specialised positions are often not on the platform.
For a professional-level job search it adds limited value unless the target role is in a
sector where UWV listings dominate.

**Intermediair** has the best audience fit for a professional or academic job search but very
low volume (~2K listings). Quality per listing is high (all HBO/WO level), but the small pool
means it should be treated as a supplementary source rather than a primary one. Worth building
only if the target audience is specifically higher-educated professionals.

**Adzuna NL** has a very small global market share (0.05% vs LinkedIn's 24%) but lists the
Netherlands as one of its key markets. Its aggregator model risks duplicate and stale listings.
As a fallback aggregator with a public API it is convenient to build, but it should not be
treated as a high-confidence primary source.

**Indeed NL** dominates on volume and quality. See the dedicated section below on whether the
official Indeed MCP can be used instead of building a custom CLI.

---

## Indeed MCP: can we use it?

Indeed has published an official MCP server at `https://mcp.indeed.com/claude/mcp`
([docs](https://docs.indeed.com/mcp)). The relevant findings:

**Tools exposed:**

- `search_jobs` — searches job listings by title, keywords, location, and employment type
- `get_job` — retrieves full detail for a specific job posting by ID
- `list_applications` — lists applications (this tool is employer/scope-dependent and is
  not relevant for job searching)

**Location support:** The `search_jobs` tool supports country-code filtering using ISO-3166-1
alpha-2 codes, so filtering to `NL` for the Netherlands is supported.

**Authentication:** Requires signing in with a personal Indeed account via OAuth. This is a
one-time browser-based flow, after which the MCP session is authenticated.

**Architecture fit:** This is a remote MCP server using Streamable HTTP — it is not a CLI
tool that runs locally. It fits the agent invocation pattern (called directly by Claude) rather
than the `bun run skills/…/cli.ts` pattern of the other skills. The distinction matters:

| Approach | How invoked | Auth model | Fits CLI skill pattern? |
|---|---|---|---|
| CLI skill (NVB, Adzuna, etc.) | `bun run skills/…/cli.ts search` | No auth or env-var keys | Yes |
| Indeed MCP | Remote MCP connector in `settings.local.json` | OAuth (Indeed account) | No — agent-native only |

**Recommendation:** Use Indeed MCP as a native agent tool rather than wrapping it in a CLI
skill. It can be added to `.claude/settings.local.json` as a remote MCP connection. When the
agent needs broad coverage, it calls the Indeed MCP directly alongside the CLI-based tools.
This avoids duplicating effort building a scraper for a site that explicitly prohibits
scraping, while gaining access to the highest-coverage source in the Dutch market.

The revised board plan with this in mind:

---

## ts-jobspy evaluation (live test results, 2026-03-23)

`ts-jobspy` (`npm install ts-jobspy`) is a TypeScript port of python-jobspy that scrapes
Indeed (and other boards) without requiring authentication. A live test against `nl.indeed.com`
confirmed it works for the Netherlands.

| Feature | Result | Notes |
|---|---|---|
| NL data | ✅ Works | Returns `nl.indeed.com` URLs; correctly routes to Dutch Indeed |
| Speed | ✅ ~0.8s for 10 results | Suitable for CLI use |
| Full descriptions | ✅ 3–8K chars per listing | No need for a separate `detail` command |
| Date posted | ✅ Accurate | Today's listings confirmed |
| `hoursOld` filter | ✅ Works | `hoursOld: 24` returned 3 results — correct given actual posting volume |
| `isRemote` filter | ✅ Works | All returned results confirmed remote; Dutch-language listings included |
| Location precision | ❌ Broken at city level | Rotterdam vs Amsterdam search returned **identical results**. Location is not city-filtered. |
| Salary data | ❌ Always n/a for NL | Indeed NL listings rarely include structured salary data |
| Filter combinations | ⚠️ Restricted | `hoursOld`, `jobType`, and `isRemote` are mutually exclusive — only one can be used per search |

### Design consequence: location in query, not as a flag

The broken city-level location filter is the most significant finding. It mirrors the known
limitation in `jobindex-search` (which also cannot filter by area via API params). The same
solution applies: city should be embedded in `--query` rather than offered as a separate
`--location` flag. For example:

```
indeed-cli search --query "product manager amsterdam"
indeed-cli search --query "data engineer amsterdam --remote"
```

This is a known pattern in the repo and should be documented clearly in the SKILL.md.

### Viability verdict

`ts-jobspy` is viable as the engine for an `indeed-search` CLI skill. It is the only
no-auth path to Indeed NL data that fits the existing `bun run` CLI pattern. The tradeoff
vs the official MCP:

| | ts-jobspy CLI | Indeed MCP |
|---|---|---|
| Auth required | None | Indeed account (OAuth) |
| City-level filtering | No (embed in query) | Yes (proper location param) |
| Salary data | No | Potentially yes |
| Maintenance risk | Medium (unofficial scraper) | Low (official) |
| Fits CLI skill pattern | Yes | No |

Use `ts-jobspy` for the CLI skill. The official MCP remains an option if OAuth auth is
acceptable and city-level filtering matters.

---

## Revised board mapping

| Danish tool | Dutch equivalent | Approach | Priority |
|---|---|---|---|
| jobdanmark-search | nvb-search (Nationale Vacaturebank) | Public API | 1 — build first |
| jobindex-search | indeed-search (Indeed NL via ts-jobspy) | ts-jobspy CLI skill | 2 — no auth, broad coverage |
| jobbank-search | intermediair-search (Intermediair.nl) | HTML scraping | 3 — supplementary |
| jobnet-search | werk-search (Werk.nl / UWV) | HTML scraping | 4 — only if blue-collar roles are in scope |

> **Adzuna** is removed from the primary plan. Its low NL market share and aggregator-quality
> data make it a poor trade-off against the effort of building and maintaining the CLI. If NVB
> and Indeed are in place, Adzuna adds diminishing value.

> **Werk.nl** is deprioritised. Given that the target audience is likely professional or
> knowledge-worker roles (consistent with the existing Intermediair mapping), Werk.nl's
> structural bias towards blue-collar and public sector listings means it covers a different
> audience segment. Reconsider if the search scope expands to include those roles.

---

---

## 1. nvb-search — Nationale Vacaturebank

**Status**: API confirmed via live browser inspection (2026-03-23). Public API at
`https://api.nationalevacaturebank.nl`. No authentication required. CORS is permissive
(requests work from the NVB domain; Python httpx works server-to-server without CORS
restrictions).

### Confirmed API surface (live-tested)

**Base URL:** `https://api.nationalevacaturebank.nl`

| Endpoint | Purpose | Status |
|---|---|---|
| `GET /api/jobs/v3/sites/nationalevacaturebank.nl/jobs` | Paginated job search | ✅ Confirmed, 200 OK |
| `GET /api/jobs/v3/sites/nationalevacaturebank.nl/jobs/new/{id}` | Single job detail | ✅ Confirmed (from `_links.self`) |
| `GET /api/jobs/v3/sites/nationalevacaturebank.nl/aggregations` | Filter bucket counts | ✅ Confirmed |

**Search query parameters (confirmed working):**

| Parameter | Values | Notes |
|---|---|---|
| `filters` | space-separated `key:value` string | see below — this is the correct filter mechanism |
| `limit` | integer | results per page; 25 recommended |
| `page` | integer (1-indexed) | pagination |
| `sort` | `date`, `relevance`, `distance`, `random` | `date` = newest first |

> **Do not use the `query` param alone.** It is a full-text description search that matches
> any job mentioning the keyword anywhere in the body — returns pizzamakers, hospital
> purchasing staff, etc. alongside actual product roles.

**`filters` param — space-separated compound string (confirmed working):**

```
filters=dcoTitle:Productmanager city:Amsterdam latitude:52.359273 longitude:4.887492 distance:40
```

| Filter key | Example value | Effect |
|---|---|---|
| `dcoTitle` | `Productmanager` | NVB's normalised job-title taxonomy. Reduces 3,254 → 273 NL-wide. |
| `city` | `Amsterdam` | City name |
| `latitude` | `52.359273` | City centre latitude (resolve via geolocation API) |
| `longitude` | `4.887492` | City centre longitude |
| `distance` | `40` | Radius in km. With Amsterdam + 40km: 3,254 → **92 results**, 4 pages. |

**Geolocation API (confirmed):**
```
GET /api/v1/geolocations/nl/{cityName}
→ { "cityCenter": { "latitude": "52.359273", "longitude": "4.887492" }, "cityName": "Amsterdam", ... }
```

**Location filtering (corrected):** Server-side location filter DOES work via the `filters`
compound param. Earlier negative tests used the wrong format (`locationText=`, `municipality=`,
etc. as top-level query params — these do nothing). Correct format is `city:X latitude:Y longitude:Z distance:N` inside the single `filters` value.

**Date filtering:** No server-side date filter. Use `sort=date` (newest-first) and stop
paginating once `startDate < cutoff`. With `dcoTitle + location`, the full result set is
only ~92 jobs so all 4 pages complete quickly.

**Response format (HAL):**
```json
{
  "page": 1,
  "limit": 25,
  "pages": 1627,
  "total": 3254,
  "_links": { "self": {}, "first": {}, "last": {}, "next": {}, "sort:date": {}, "sort:distance": {}, "sort:random": {} },
  "_embedded": {
    "jobs": [...],
    "aggregations": {}
  }
}
```

**Job object — key fields:**

| Field | Type | Example |
|---|---|---|
| `id` | UUID string | `"4dbdefe2-52bf-4b27-9f9b-07bbc79dbb66"` |
| `title` | string | `"Product Manager"` |
| `functionTitle` | string | normalised title |
| `company.name` | string | `"Eneco"` |
| `company.slug` | string | `"eneco"` |
| `description` | HTML string | full job description |
| `workLocation.city` | string | `"Rotterdam"` |
| `workLocation.province` | string | `"Zuid-Holland"` |
| `workLocation.geolocation` | `{latitude, longitude}` | decimal strings |
| `startDate` | ISO 8601 | `"2026-03-22T23:00:00Z"` (posting date) |
| `endDate` | ISO 8601 | application deadline |
| `apply.url` | string | direct apply URL |
| `contractType` | string | `"Vast"` (permanent) |
| `workingHours.min/max` | integer | hours per week |
| `careerLevel` | string | `"Ervaren"` (experienced) |
| `_links.self.href` | string | API canonical URL |
| `_links.detail.href` | string | public NVB page URL |

### Fetcher strategy for the automated pipeline

```python
# Per search term, paginate with sort=date and limit=25
# Stop when startDate of last job on page < (today - 14 days)
# Filter client-side: keep only NL jobs (country.iso == "NL")
# Canonical key: SHA1(title.lower() + company.name.lower() + city.lower())

GET /api/jobs/v3/sites/nationalevacaturebank.nl/jobs
  ?query=<term>&limit=25&sort=date&page=<n>
```

Estimated API calls per run: 2 queries × ~2 pages each = 4 calls/run × 22 weekdays = 88
calls/month. No auth, no rate limit observed.

### Open questions

- Whether an undocumented `startDate[from]` param exists (all tested variants returned
  the same `total` — likely no server-side date filter).
- Whether the `detail` endpoint returns richer data than the search result (e.g. full
  HTML description — the search result already includes `description` so this may not
  be needed).

---

## 2. werk-search — Werk.nl (UWV)

**Status**: Requires reverse engineering. UWV has confirmed there is no public API and
none is planned. Scraping is explicitly permitted by UWV. The Apify scraper
([lexis-solutions/werk-nl-scraper](https://apify.com/lexis-solutions/werk-nl-scraper))
demonstrates that the site is scrapeable.

### Likely approach

Werk.nl is a Next.js / React SPA. The search interface at `https://www.werk.nl/vacatures/`
almost certainly makes XHR/fetch calls to an internal BFF endpoint. The approach mirrors
how `jobnet-search` handles the Jobnet BFF (`jobnet.dk/bff`) and how `jobbank-search`
handles the RSS feed and JSON-LD:

1. Open `werk.nl/vacatures` in Chrome DevTools > Network > Fetch/XHR.
2. Perform a search and observe the outbound request URL, headers, and body.
3. Identify the search endpoint, its parameters, and any required headers (e.g. a CSRF
   token similar to the `x-csrf: 1` pattern in jobnet-search).
4. Confirm pagination structure and whether a detail endpoint exists or whether detail
   requires fetching the HTML page and parsing JSON-LD.

### Expected filter surface (based on the website's UI)

- Keyword / job title
- Region or city
- Employment type: fulltime, parttime, oproepkracht (flex), stage (internship)
- Distance radius from postcode

### Proposed CLI (provisional — pending API discovery)

```
werk-cli search [flags]
  --query <text>           keyword / job title
  --postcode <code>        Dutch postcode e.g. 1012
  --radius <km>            radius from postcode
  --region <name>          region name e.g. Noord-Holland
  --type <type>            fulltime|parttime|flex|stage (repeatable)
  --page <n>
  --limit <n>
  --format json|table|plain

werk-cli detail <id>
  --format json|plain
```

### Open questions

- Exact BFF endpoint URL and required headers (needs live browser inspection).
- Whether pagination is cursor-based or page-number-based.
- Whether JSON-LD is embedded in job detail pages (common for Dutch boards).
- Whether the site uses a token / fingerprinting mechanism that would complicate scraping.

---

## 3. intermediair-search — Intermediair.nl

**Status**: Requires reverse engineering. Intermediair is owned by DPG Media and
targets highly educated professionals. No public API is documented. Its audience maps
directly to Akademikernes Jobbank: academic, graduate, and professional roles. Filters
visible on the site suggest a rich query model.

### Likely approach

Same as Werk.nl: inspect live network traffic in Chrome DevTools during a job search to
find the underlying API or BFF endpoint.

### Expected filter surface (from site UI)

- Keyword / job title
- Location (city / region)
- Sector / branch (branche)
- Education level (opleidingsniveau)
- Experience level (ervaringsniveau)
- Contract type: vast, tijdelijk, freelance, stage, traineeship
- Hours (part/full time)
- Publication date (within X days)
- Recruiter type: employer direct vs. agency

### Proposed CLI (provisional — pending API discovery)

```
intermediair-cli search [flags]
  --query <text>           keyword / job title
  --location <city>        city or region
  --sector <id>            sector/branch code (repeatable)
  --education <level>      MBO|HBO|WO (repeatable)
  --contract <type>        vast|tijdelijk|freelance|stage|traineeship (repeatable)
  --hours <type>           fulltime|parttime
  --days <n>               posted within last N days
  --page <n>
  --limit <n>
  --format json|table|plain

intermediair-cli detail <id>
  --format json|plain

intermediair-cli sectors    list available sector codes
```

### Open questions

- Exact API endpoint and whether it is a REST JSON API or requires HTML parsing.
- Whether the site uses authentication or session tokens for API calls.
- Whether filter values (sector codes, education levels) are queryable or need to be
  hardcoded from a reference page, as in jobbank-search.

---

## 4. adzuna-search — Adzuna NL

**Status**: Ready to build. Adzuna has a public documented REST API
(`https://api.adzuna.com/v1/api/jobs/nl`) requiring a free API key. This is the
closest like-for-like replacement for Jobindex.dk: a broad aggregator covering all
sectors, with keyword search and date-based filtering.

### API surface

Base URL: `https://api.adzuna.com/v1/api/jobs/nl`

| Endpoint | Purpose |
|---|---|
| `GET /search/<page>` | Paginated job search |
| `GET /categories` | List job categories |
| `GET /geodata` | Location data |

Authentication: `app_id` and `app_key` query parameters (free registration at
`developer.adzuna.com`). Unlike the Danish tools, this requires credentials —
the CLI should read them from environment variables `ADZUNA_APP_ID` and
`ADZUNA_APP_KEY`.

Key search parameters:

- `what` — keyword(s)
- `where` — location string (city or region)
- `distance` — radius in km
- `results_per_page` — 10–50 (default 10)
- `max_days_old` — filter by recency
- `sort_by` — `relevance`, `date`, `salary`
- `full_time` / `part_time` / `permanent` / `contract` / `internship` — boolean flags
- `category` — category tag from `/categories`

### Proposed CLI

```
adzuna-cli search [flags]
  --query <text>           keyword search (what)
  --location <text>        city or region (where)
  --distance <km>          radius
  --days <n>               max posting age in days
  --sort <order>           relevance|date|salary (default: relevance)
  --full-time              filter: full-time only
  --part-time              filter: part-time only
  --permanent              filter: permanent contracts
  --contract               filter: contract/temp roles
  --internship             filter: internships
  --category <tag>         category tag from categories command
  --page <n>               page number
  --limit <n>              cap results
  --format json|table|plain

adzuna-cli detail <id>     full job posting (fetches job URL, parses JSON-LD or HTML)
  --format json|plain

adzuna-cli categories      list available NL job categories with tags
```

### Open questions

- Whether Adzuna job detail pages embed JSON-LD (the `detail` command may need to scrape
  the redirected employer or Adzuna-hosted page).
- Whether the redirect URL in search results points to Adzuna-hosted or external pages,
  affecting how `detail` works.
- Whether the free tier has sufficient rate limits for interactive use (typically 250
  requests/day on the free plan — should be noted in the SKILL.md).

---

## Implementation order

The recommended build sequence, from lowest to highest complexity:

1. **nvb-search** — public API, no auth, MCP precedent to reference.
2. **adzuna-search** — documented API, only complication is API key handling.
3. **werk-search** — scraping required, but UWV permits it; likely a straightforward BFF.
4. **intermediair-search** — scraping required; DPG Media sites tend to be more complex.

---

## Required investigation before building werk-search and intermediair-search

Both tools need a brief live browser session before writing any code:

1. Open Chrome DevTools > Network > Fetch/XHR.
2. Navigate to the job search page (`werk.nl/vacatures` or `intermediair.nl/vacatures`).
3. Perform a search with representative filters.
4. Record: the full request URL, method (GET/POST), headers, request body (if POST),
   and response structure.
5. Click into a job detail page and record the same for the detail call.
6. Check for CSRF tokens, session cookies, or fingerprinting headers.

This should take 15–20 minutes per site and is all that blocks starting those two tools.

---

## Shared implementation patterns to carry over

From the existing Danish CLIs:

- Use `@bunli/core` for CLI scaffolding (consistent with the rest of the repo).
- `helpers.ts`: `apiFetch` with exponential backoff + jitter on 429/5xx, `writeError` to
  stderr, `stripHtml` for plain-text detail output.
- Two-step workflow: `search` returns IDs/slugs → `detail <id>` fetches full content.
- JSON-LD (`application/ld+json`, schema.org `JobPosting`) is the preferred parsing
  target for detail pages when available — avoids brittle HTML selectors.
- `meta.total` in search responses to surface the true result count when truncated.
- `--format json` as the default (programmatic); `--format table` for human scanning;
  `--format plain` for readable single-job detail.
