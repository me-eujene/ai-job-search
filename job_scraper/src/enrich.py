"""
Post-dedup description enrichment.

Runs in the pipeline AFTER deduplication so detail-fetch budgets are spent
only on genuinely new jobs. Each source registers an async enricher that
takes the source's thin jobs and returns them (same order) with descriptions
filled in where possible.

Budgets (env-overridable):
  LINKEDIN_MAX_DETAIL_FETCHES    default 30   (2.0s between fetches — 429s below that)
  ADZUNA_MAX_DETAIL_FETCHES      default 50   (1.5s between fetches)
  HIRINGCAFE_MAX_DETAIL_FETCHES  default 80   (concurrent, semaphore 5)
"""
import asyncio
import logging
import os
from dataclasses import replace
from typing import Awaitable, Callable

from .helpers import build_client, extract_text_from_html
from .types import Job, is_description_ok

logger = logging.getLogger(__name__)


def _budget(source: str, default: int) -> int:
    return int(os.environ.get(f"{source.upper()}_MAX_DETAIL_FETCHES", str(default)))


async def enrich_new_jobs(jobs: list[Job]) -> list[Job]:
    """Enrich thin jobs per source. Preserves list order. Never raises."""
    out = list(jobs)
    by_source: dict[str, list[int]] = {}
    for i, job in enumerate(out):
        if not job.description_ok:
            by_source.setdefault(job.source, []).append(i)

    for source, idxs in by_source.items():
        enricher = ENRICHERS.get(source)
        if enricher is None:
            continue
        try:
            enriched = await enricher([out[i] for i in idxs])
        except Exception as e:
            logger.error("enrich: %s enricher failed: %s", source, e)
            continue
        for i, job in zip(idxs, enriched):
            out[i] = job
        ok = sum(1 for i in idxs if out[i].description_ok)
        logger.info("enrich: %s — %d/%d thin jobs enriched", source, ok, len(idxs))
    return out


# ---------------------------------------------------------------------------
# LinkedIn: fetch job detail pages (moved from fetchers/linkedin.py)
# ---------------------------------------------------------------------------

async def _enrich_linkedin(jobs: list[Job]) -> list[Job]:
    from .fetchers.linkedin import BASE_URL, _HTML_HEADERS, _parse_detail_description

    budget = _budget("linkedin", 30)
    result: list[Job] = []
    fetched = 0
    async with build_client() as client:
        for job in jobs:
            if fetched >= budget or not job.id:
                result.append(job)
                continue
            try:
                resp = await client.get(
                    f"{BASE_URL}/jobs/view/{job.id}/", headers=_HTML_HEADERS
                )
                resp.raise_for_status()
                desc = _parse_detail_description(resp.text)
            except Exception as e:
                logger.warning("enrich linkedin: %s failed: %s", job.id, e)
                desc = None
            fetched += 1
            if desc:
                result.append(replace(job, description=desc,
                                      description_ok=is_description_ok(desc)))
            else:
                result.append(job)
            await asyncio.sleep(2.0)
    logger.info("enrich linkedin: fetched %d/%d detail pages", fetched, len(jobs))
    return result


# ---------------------------------------------------------------------------
# Adzuna: follow redirect_url, extract with trafilatura (moved from fetchers/adzuna.py)
# ---------------------------------------------------------------------------

async def _enrich_adzuna(jobs: list[Job]) -> list[Job]:
    budget = _budget("adzuna", 50)
    result: list[Job] = []
    fetched = 0
    async with build_client() as client:
        for job in jobs:
            if fetched >= budget or not job.apply_url:
                result.append(job)
                continue
            try:
                resp = await client.get(job.apply_url)
                resp.raise_for_status()
                desc = extract_text_from_html(resp.text)
            except Exception as e:
                logger.warning("enrich adzuna: %s failed: %s", job.apply_url, e)
                desc = None
            fetched += 1
            if desc:
                result.append(replace(job, description=desc, description_ok=True))
            else:
                result.append(job)
            await asyncio.sleep(1.5)
    logger.info("enrich adzuna: fetched %d/%d detail pages", fetched, len(jobs))
    return result


# ---------------------------------------------------------------------------
# hiring.cafe: public ATS APIs (see ats.py) — concurrent, budgeted
# ---------------------------------------------------------------------------

async def _enrich_hiringcafe(jobs: list[Job]) -> list[Job]:
    from .ats import fetch_ats_description

    budget = _budget("hiringcafe", 80)
    todo = jobs[:budget]
    rest = jobs[budget:]
    cache: dict = {}
    sem = asyncio.Semaphore(5)

    async with build_client(timeout=20.0) as client:
        async def one(job: Job) -> Job:
            async with sem:
                desc = await fetch_ats_description(client, job.id, job.apply_url, cache)
            if desc:
                return replace(job, description=desc,
                               description_ok=is_description_ok(desc))
            return job

        enriched = list(await asyncio.gather(*(one(j) for j in todo)))
    return enriched + rest


ENRICHERS: dict[str, Callable[[list[Job]], Awaitable[list[Job]]]] = {
    "linkedin":   _enrich_linkedin,
    "adzuna":     _enrich_adzuna,
    "hiringcafe": _enrich_hiringcafe,
}
