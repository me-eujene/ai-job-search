"""Live check: fetch hiring.cafe jobs and report enrichment coverage by ATS.

Usage: uv run python job_scraper/scripts/verify_hiringcafe_enrichment.py
"""
import asyncio
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from job_scraper.src.fetchers.hiringcafe import fetch_hiringcafe
from job_scraper.src.enrich import _enrich_hiringcafe
from job_scraper.src.ats import parse_hc_id


async def main() -> None:
    jobs = await fetch_hiringcafe()
    print(f"fetched {len(jobs)} jobs")
    enriched = await _enrich_hiringcafe(jobs)
    by_ats: Counter = Counter()
    ok_by_ats: Counter = Counter()
    for job in enriched:
        parsed = parse_hc_id(job.id)
        ats = parsed[0] if parsed else "unparseable"
        by_ats[ats] += 1
        if job.description_ok:
            ok_by_ats[ats] += 1
    total_ok = sum(ok_by_ats.values())
    print(f"description_ok: {total_ok}/{len(enriched)}")
    for ats, n in by_ats.most_common():
        print(f"  {ats:>16}: {ok_by_ats[ats]}/{n}")


if __name__ == "__main__":
    asyncio.run(main())
