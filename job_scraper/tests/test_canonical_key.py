from job_scraper.src.types import make_canonical_key


def test_location_first_segment_only():
    # Observed: hiringcafe "Amsterdam, Netherlands" vs adzuna "Amsterdam"
    assert make_canonical_key("Product Manager", "Dyson", "Amsterdam, Netherlands") == \
           make_canonical_key("Product Manager", "Dyson", "Amsterdam")


def test_gender_tag_stripped_from_title():
    assert make_canonical_key("Product Manager (m/f/d)", "Acme", "Berlin") == \
           make_canonical_key("Product Manager", "Acme", "Berlin")
    assert make_canonical_key("Product Owner (m/v/x)", "Acme", "Utrecht") == \
           make_canonical_key("Product Owner", "Acme", "Utrecht")


def test_legal_suffix_stripped_from_company():
    assert make_canonical_key("PM", "Lely B.V.", "Maassluis") == \
           make_canonical_key("PM", "Lely", "Maassluis")
    assert make_canonical_key("PM", "Bynder BV", "Amsterdam") == \
           make_canonical_key("PM", "Bynder", "Amsterdam")


def test_whitespace_and_case_insensitive():
    assert make_canonical_key("  Product  Manager ", "ACME", "amsterdam") == \
           make_canonical_key("product manager", "Acme", "Amsterdam")


def test_different_cities_stay_distinct():
    # Pessimistic: same title+company in two cities = two roles
    assert make_canonical_key("Product Manager", "Acme", "Amsterdam") != \
           make_canonical_key("Product Manager", "Acme", "Rotterdam")


def test_meaningful_parentheticals_kept():
    # Only gender tags are stripped, not real qualifiers
    assert make_canonical_key("Product Manager (Payments)", "Acme", "Amsterdam") != \
           make_canonical_key("Product Manager", "Acme", "Amsterdam")
