import os

import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    # state.py reads DB_PATH at import time — reload with the env var set
    import importlib
    from job_scraper.src import state
    importlib.reload(state)
    state.init_db()
    yield state
    importlib.reload(state)  # restore module-level DB_PATH for other tests


def test_description_persisted(db):
    inserted = db.mark_seen_if_new(
        canonical_key="k1", title="PM", company="Acme", location="Amsterdam",
        source="test", apply_url="https://x", date_posted="2026-07-01",
        description="d" * 300, description_ok=True, fetched_at="2026-07-05T00:00:00Z",
    )
    assert inserted is True
    row = db.get_jobs()[0]
    assert row["description"] == "d" * 300
    assert row["description_ok"] == 1


def test_update_description_backfills(db):
    db.mark_seen_if_new(
        canonical_key="k2", title="PM", company="Acme", location="Amsterdam",
        source="test", apply_url="https://x", date_posted="2026-07-01",
        description=None, description_ok=False, fetched_at="2026-07-05T00:00:00Z",
    )
    db.update_description("k2", "full text " * 40, True)
    row = [r for r in db.get_jobs() if r["canonical_key"] == "k2"][0]
    assert row["description_ok"] == 1
    assert row["description"].startswith("full text")


def test_duplicate_insert_returns_false(db):
    kwargs = dict(
        canonical_key="k3", title="PM", company="Acme", location="Amsterdam",
        source="test", apply_url="https://x", date_posted="2026-07-01",
        description=None, description_ok=False, fetched_at="2026-07-05T00:00:00Z",
    )
    assert db.mark_seen_if_new(**kwargs) is True
    assert db.mark_seen_if_new(**kwargs) is False
