from job_scraper.src.pipeline import zero_yield_warnings


HISTORY = [
    {"sources": {"adzuna": 55, "wttj": 0, "wwr": 1, "nvb": 3}},
    {"sources": {"adzuna": 54, "wttj": 0, "wwr": 0, "nvb": 4}},
    {"sources": {"adzuna": 48, "wttj": 12, "wwr": 2, "nvb": 4}},
    {"sources": None},          # current run row — sources_json still null
]


def test_flags_source_that_dropped_to_zero():
    warnings = zero_yield_warnings({"adzuna": 0, "nvb": 3}, HISTORY)
    assert len(warnings) == 1
    assert "adzuna" in warnings[0]


def test_low_volume_sources_not_flagged():
    # wwr trailing avg is 1 — noise, not breakage
    assert zero_yield_warnings({"wwr": 0}, HISTORY) == []


def test_no_history_no_warnings():
    assert zero_yield_warnings({"newsource": 0}, []) == []


def test_nonzero_yield_not_flagged():
    assert zero_yield_warnings({"adzuna": 12}, HISTORY) == []
