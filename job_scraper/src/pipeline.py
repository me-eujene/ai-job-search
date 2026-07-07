"""
Main pipeline: orchestrates all fetchers, deduplicates, and writes output.

Called by:
  - APScheduler (daily 07:00 weekdays)          → run_pipeline()
  - POST /api/run/now  (run all sources)         → run_pipeline()
  - POST /api/run/{source}  (single source)      → run_pipeline(sources=["nvb"])
"""
import asyncio
import logging
import os
from typing import Literal

from .helpers import run_id_now, iso_ts, utc_now, parse_iso
from .state import (
    init_db, mark_seen_if_new, prune_old, start_run, finish_run, log_error,
    update_description, get_recent_runs,
)
from .enrich import enrich_new_jobs
from .types import Job

logger = logging.getLogger(__name__)

Source = Literal["linkedin", "nvb", "hiringcafe", "adzuna", "wwr", "wttj", "workingnomads"]
ALL_SOURCES: list[Source] = ["linkedin", "nvb", "hiringcafe", "adzuna", "wwr", "wttj", "workingnomads"]


def _get_queries() -> list[str]:
    """Read SEARCH_QUERIES env var. Used by Indeed and LinkedIn only."""
    raw = os.environ.get("SEARCH_QUERIES", "")
    if raw:
        return [q.strip() for q in raw.split(",") if q.strip()]
    return []


def zero_yield_warnings(source_counts: dict[str, int],
                        history: list[dict]) -> list[str]:
    """Flag sources that yielded 0 this run but averaged >=3 over recent runs.

    A silent zero usually means the site changed and the fetcher is broken
    (this has happened to sources before anyone noticed).
    """
    past: dict[str, list[int]] = {}
    for run in history:
        for src, n in (run.get("sources") or {}).items():
            past.setdefault(src, []).append(n)

    warnings = []
    for src, count in source_counts.items():
        counts = past.get(src)
        if count == 0 and counts and sum(counts) / len(counts) >= 3:
            warnings.append(
                f"{src}: returned 0 jobs (trailing avg {sum(counts) / len(counts):.0f} "
                f"over {len(counts)} runs) — source may be broken"
            )
    return warnings


def dynamic_lookback(history: list[dict], floor: int = 14, cap: int = 30) -> int:
    """Lookback = days since last completed run + 3, clamped to [floor, cap].

    Guarantees no posting gap between runs regardless of cadence. With no
    history, use the widest window.
    """
    for run in history:
        if run.get("status") == "done" and run.get("started_at"):
            started = parse_iso(run["started_at"])
            if started:
                gap = (utc_now() - started).days + 3
                return max(floor, min(cap, gap))
    return cap


async def _fetch_source(source: Source, queries: list[str], lookback_days: int) -> tuple[list[Job], str | None]:
    """
    Run one fetcher. Returns (jobs, error_message_or_None).
    Never raises — errors are returned as a string.
    """
    try:
        if source == "linkedin":
            from .fetchers.linkedin import fetch_linkedin
            return await fetch_linkedin(queries or None, lookback_days=lookback_days), None

        if source == "nvb":
            from .fetchers.nvb import fetch_nvb
            return await fetch_nvb(lookback_days=lookback_days), None

        if source == "hiringcafe":
            from .fetchers.hiringcafe import fetch_hiringcafe
            return await fetch_hiringcafe(queries or None, lookback_days=lookback_days), None

        if source == "adzuna":
            from .fetchers.adzuna import fetch_adzuna
            return await fetch_adzuna(queries or None, lookback_days=lookback_days), None

        if source == "wwr":
            from .fetchers.wwr import fetch_wwr
            return await fetch_wwr(lookback_days=lookback_days), None

        if source == "wttj":
            from .fetchers.wttj import fetch_wttj
            return await fetch_wttj(lookback_days=lookback_days), None

        if source == "workingnomads":
            from .fetchers.workingnomads import fetch_workingnomads
            return await fetch_workingnomads(lookback_days=lookback_days), None

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
    history = get_recent_runs(6)
    lookback = dynamic_lookback(history)
    logger.info("Pipeline lookback window: %d days", lookback)

    label = "+".join(sources)
    logger.info("Pipeline run %s started (sources: %s)", run_id, label)

    queries   = _get_queries()
    all_jobs: list[Job] = []
    errors:   list[str] = []
    source_counts: dict[str, int] = {}

    results = await asyncio.gather(
        *(_fetch_source(source, queries, lookback) for source in sources)
    )
    for source, (jobs, err) in zip(sources, results):
        source_counts[source] = len(jobs)
        all_jobs.extend(jobs)
        if err:
            logger.error(err)
            errors.append(err)
            log_error(run_id, source, err)

    for warning in zero_yield_warnings(source_counts, history):
        logger.warning(warning)
        errors.append(warning)
        log_error(run_id, warning.split(":")[0], warning)

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
            description=job.description,
            description_ok=job.description_ok,
            fetched_at=job.fetched_at,
        )
        if inserted:
            new_jobs_list.append(job)
        else:
            skipped += 1

    # ---- Post-dedup enrichment ------------------------------------------
    if new_jobs_list:
        pre_ok = sum(1 for j in new_jobs_list if j.description_ok)
        new_jobs_list = await enrich_new_jobs(new_jobs_list)
        for job in new_jobs_list:
            if job.description_ok:
                update_description(job.canonical_key, job.description, True)
        post_ok = sum(1 for j in new_jobs_list if j.description_ok)
        if post_ok > pre_ok:
            logger.info("Enrichment: description_ok %d → %d of %d new jobs",
                        pre_ok, post_ok, len(new_jobs_list))

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
