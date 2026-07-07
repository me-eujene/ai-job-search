from job_scraper.src.types import Job, make_canonical_key


def test_make_canonical_key_is_stable():
    a = make_canonical_key("Product Manager", "Acme", "Amsterdam")
    b = make_canonical_key("Product Manager", "Acme", "Amsterdam")
    assert a == b and len(a) == 40
