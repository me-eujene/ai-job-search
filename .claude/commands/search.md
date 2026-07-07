# /search — Job Search & Application Orchestrator

Entry point for the full pipeline. Follow the Pipeline Overview in `CLAUDE.md` from Phase 0 through Phase 8.

Optional `$ARGUMENTS`: a query or filter to pass to the scraper (e.g. "product manager Amsterdam"). If omitted, uses configured search queries.

Before starting: read `01-candidate-profile.md`. If it is missing (a fresh clone tracks only the `01-candidate-profile.example.md` seed) or still contains unfilled placeholders (`[YOUR_NAME]`, etc.), stop and tell the user to run `/job-scraper-setup` first — it writes the real, gitignored profile from the seed.
