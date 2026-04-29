"""
Main pipeline: orchestrates all fetchers, deduplicates, and writes output.

Called by:
  - APScheduler (daily 07:00 weekdays)          → run_pipeline()
  - POST /api/run/now  (run all sources)         → run_pipeline()
  - POST /api/run/{source}  (single source)      → run_pipeline(sources=["nvb"])
"""
import logging
import os
from typing import Literal

from .helpers import run_id_now, iso_ts, utc_now
from .state import init_db, mark_seen_if_new, prune_old, start_run, finish_run, log_error
from .types import Job

logger = logging.getLogger(__name__)

Source = Literal["linkedin", "nvb", "hiringcafe", "adzuna", "workingnomads"]
ALL_SOURCES: list[Source] = ["linkedin", "nvb", "hiringcafe", "adzuna", "workingnomads"]


def _get_queries() -> list[str]:
    """Read SEARCH_QUERIES env var. Used by Indeed and LinkedIn only."""
    raw = os.environ.get("SEARCH_QUERIES", "")
    if raw:
        return [q.strip() for q in raw.split(",") if q.strip()]
    return []


async def _fetch_source(source: Source, queries: list[str]) -> tuple[list[Job], str | None]:
    """
    Run one fetcher. Returns (jobs, error_message_or_None).
    Never raises — errors are returned as a string.
    """
    try:
        if source == "linkedin":
            from .fetchers.linkedin import fetch_linkedin
            return await fetch_linkedin(queries or None), None

        if source == "nvb":
            from .fetchers.nvb import fetch_nvb
            return await fetch_nvb(), None

        if source == "hiringcafe":
            from .fetchers.hiringcafe import fetch_hiringcafe
            return await fetch_hiringcafe(queries or None), None

        if source == "adzuna":
            from .fetchers.adzuna import fetch_adzuna
            return await fetch_adzuna(queries or None), None

        if source == "workingnomads":
            from .fetchers.workingnomads import fetch_workingnomads
            return await fetch_workingnomads(), None

    except Exception as e:
        return [], f"{source} fetch failed: {e}"

    return [], f"Unknown source: {source}"


async def run_pipeline(sources: list[Source] | None = None) -> dict:
    """
    Execute a fetch cycle for the given sources (default: all three).

    Returns a summary dict suitable for API responses.
    """
    sources = sources or ALL_SOURCES
    init_db()
    prune_old()
    run_id  = run_id_now()
    started = iso_ts(utc_now())
    start_run(run_id, started)

    label = "+".join(sources)
    logger.info("Pipeline run %s started (sources: %s)", run_id, label)

    queries   = _get_queries()
    all_jobs: list[Job] = []
    errors:   list[str] = []
    source_counts: dict[str, int] = {}

    for source in sources:
        jobs, err = await _fetch_source(source, queries)
        source_counts[source] = len(jobs)
        all_jobs.extend(jobs)
        if err:
            logger.error(err)
            errors.append(err)
            log_error(run_id, source, err)

    # ---- Deduplication --------------------------------------------------
    total_fetched = len(all_jobs)
    new_jobs_list: list[Job] = []
    skipped = 0

    for job in all_jobs:
        inserted = mark_seen_if_new(
            canonical_key=job.canonical_key,
            title=job.title,
            company=job.company,
            location=job.location,
            source=job.source,
            apply_url=job.apply_url,
            date_posted=job.date_posted,
            fetched_at=job.fetched_at,
        )
        if inserted:
            new_jobs_list.append(job)
        else:
            skipped += 1

    new_count = len(new_jobs_list)
    if not new_jobs_list:
        logger.info("No new jobs this run")

    finished = iso_ts(utc_now())
    finish_run(
        run_id=run_id,
        finished_at=finished,
        total_fetched=total_fetched,
        new_jobs=new_count,
        skipped=skipped,
        sources=source_counts,
        errors=errors,
    )

    summary = {
        "run_id":        run_id,
        "started_at":    started,
        "finished_at":   finished,
        "total_fetched": total_fetched,
        "new_jobs":      new_count,
        "skipped":       skipped,
        "sources":       source_counts,
        "errors":        errors,
        "jobs":          new_jobs_list,   # in-memory Job objects; carry description
    }
    logger.info("Pipeline run %s done — %s", run_id, summary)
    return summary
