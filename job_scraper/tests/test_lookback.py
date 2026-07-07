from datetime import timedelta

from job_scraper.src.helpers import iso_ts, utc_now
from job_scraper.src.pipeline import dynamic_lookback


def _run(days_ago: int, status: str = "done") -> dict:
    return {"status": status, "started_at": iso_ts(utc_now() - timedelta(days=days_ago))}


def test_recent_run_uses_floor():
    assert dynamic_lookback([_run(5)]) == 14


def test_long_gap_extends_window():
    assert dynamic_lookback([_run(17)]) == 20   # 17 + 3


def test_capped_at_30():
    assert dynamic_lookback([_run(45)]) == 30


def test_no_history_uses_cap():
    assert dynamic_lookback([]) == 30


def test_running_rows_ignored():
    # First row is the current run (status=running) — must be skipped
    assert dynamic_lookback([_run(0, status="running"), _run(17)]) == 20
