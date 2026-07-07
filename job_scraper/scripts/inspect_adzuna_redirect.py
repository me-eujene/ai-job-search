"""
Follow one Adzuna redirect_url and extract content with trafilatura.
Usage: uv run python job_scraper/scripts/inspect_adzuna_redirect.py

Edit TEST_URL to use any redirect_url from last_run.json.
"""
import asyncio, sys
sys.path.insert(0, ".")
from job_scraper.src.helpers import build_client
from job_scraper.src.fetchers.adzuna import _extract_description_from_html

TEST_URL = "https://www.adzuna.nl/land/ad/5731966669?se=GChqmDxb8RGLhOKqikEyOg&utm_medium=api&utm_source=98ed7463"

async def main():
    async with build_client() as client:
        try:
            resp = await client.get(TEST_URL)
            print(f"Status: {resp.status_code}, Final URL: {resp.url}")
            text = _extract_description_from_html(resp.text)
            print(f"\nExtracted ({len(text or '')} chars):\n{(text or 'NOTHING')[:1500]}")
        except Exception as e:
            print(f"Error: {e}")

asyncio.run(main())
