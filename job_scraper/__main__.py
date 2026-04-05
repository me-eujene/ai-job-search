"""
CLI entry point for the NL job scraper.

Usage (from repo root):
  python -m job_scraper                        # all sources
  python -m job_scraper --sources nvb          # one source
  python -m job_scraper --sources indeed nvb   # two sources
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from .src.pipeline import run_pipeline, ALL_SOURCES
from .src.state import get_jobs
from .src.helpers import iso_date, utc_now

OUTPUT_FILE = Path(__file__).parent / "last_run.json"


async def main() -> None:
    parser = argparse.ArgumentParser(description="NL Job Scraper")
    parser.add_argument(
        "--sources",
        nargs="+",
        choices=ALL_SOURCES,
        default=None,
        metavar="SOURCE",
        help=f"Sources to fetch. Choices: {', '.join(ALL_SOURCES)}. Default: all.",
    )
    args = parser.parse_args()

    summary = await run_pipeline(sources=args.sources)

    # Fetch jobs inserted during this run only (skip if nothing new this run).
    # Strip internal fields the agent doesn't need: canonical_key, first_seen,
    # fetched_at, and description (too large; retrieved on demand per job).
    _INTERNAL = {"first_seen", "fetched_at", "description"}
    if summary["new_jobs"] > 0:
        today = iso_date(utc_now())
        raw_jobs = get_jobs(since=today)
        jobs = [{k: v for k, v in j.items() if k not in _INTERNAL} for j in raw_jobs]
    else:
        jobs = []

    result = {**summary, "jobs": jobs}
    OUTPUT_FILE.write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(
        f"Run {summary['run_id']}: {summary['new_jobs']} new jobs "
        f"({summary['total_fetched']} fetched, {summary['skipped']} dupes). "
        f"Results → {OUTPUT_FILE}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    asyncio.run(main())
