# /job-scraper-apply — Apply to a Specific Role

Entry point for the single-role flow. Follow the Pipeline Overview in `CLAUDE.md` starting at Phase 3, using the provided posting as input.

`$ARGUMENTS`: a job posting URL or pasted text.

Before starting: read `01-candidate-profile.md`. If it contains unfilled placeholders (`[YOUR_NAME]`, etc.), stop and tell the user to run `/job-scraper-setup` first.

Skip Phases 0–2. Run `job-evaluate` on the provided posting first (this is the Phase 2 decision gate for the single-role flow — present the eval summary and ask whether to proceed before continuing to Phase 3).
