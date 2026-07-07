import asyncio
from dataclasses import replace

from job_scraper.src.types import Job
from job_scraper.src import enrich


def _job(source, key, ok=False, **kw):
    defaults = dict(
        id="1", source=source, title="PM", company="Acme", location="Amsterdam",
        date_posted="2026-07-01", fetched_at="2026-07-05T00:00:00Z",
        description=None, apply_url="https://example.com/j/1",
        canonical_key=key, description_ok=ok,
    )
    defaults.update(kw)
    return Job(**defaults)


def test_enrich_skips_jobs_with_ok_descriptions(monkeypatch):
    called = []

    async def fake_enricher(jobs):
        called.extend(j.canonical_key for j in jobs)
        return [replace(j, description="x" * 300, description_ok=True) for j in jobs]

    monkeypatch.setitem(enrich.ENRICHERS, "linkedin", fake_enricher)
    jobs = [
        _job("linkedin", "a", ok=False),
        _job("linkedin", "b", ok=True, description="y" * 300),
        _job("nvb", "c", ok=False),  # no enricher registered for nvb
    ]
    out = asyncio.run(enrich.enrich_new_jobs(jobs))
    assert called == ["a"]                     # only the thin linkedin job
    assert out[0].description_ok is True       # enriched
    assert out[1].description == "y" * 300     # untouched
    assert out[2].description_ok is False      # untouched, no enricher
    assert [j.canonical_key for j in out] == ["a", "b", "c"]  # order preserved
