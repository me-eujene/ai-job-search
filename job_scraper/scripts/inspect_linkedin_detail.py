"""
Fetch one LinkedIn job detail page and print raw HTML + parsed description.
Usage: uv run python job_scraper/scripts/inspect_linkedin_detail.py <job_id>
Default job_id: 4419146693 (Scrive PM)
"""
import asyncio, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from job_scraper.src.helpers import build_client
from job_scraper.src.fetchers.linkedin import _parse_detail_description

JOB_ID = sys.argv[1] if len(sys.argv) > 1 else "4419146693"
HEADERS = {"Accept": "text/html, application/xhtml+xml, */*;q=0.9"}

async def main():
    async with build_client() as client:
        resp = await client.get(
            f"https://www.linkedin.com/jobs/view/{JOB_ID}/",
            headers=HEADERS,
        )
        print(f"Status: {resp.status_code}")
        desc = _parse_detail_description(resp.text)
        print(f"Parsed description ({len(desc or '')} chars):")
        snippet = (desc or "NOTHING EXTRACTED")[:1000]
        print(snippet)

asyncio.run(main())
