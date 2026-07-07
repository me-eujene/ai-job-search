from job_scraper.src.ats import parse_hc_id, _join_smartrecruiters_sections


def test_parse_triple_underscore_ids():
    assert parse_hc_id("grnhse___fundraiseup___4711181005") == \
        ("grnhse", "fundraiseup", "4711181005")
    assert parse_hc_id("ashby___uberall___99f643f7-902e-4ff6-8422-e5054207cea2") == \
        ("ashby", "uberall", "99f643f7-902e-4ff6-8422-e5054207cea2")
    assert parse_hc_id(
        "workday___brenntag-wd3-brenntag_jobs___product-manager_jr110887"
    ) == ("workday", "brenntag-wd3-brenntag_jobs", "product-manager_jr110887")


def test_parse_multi_segment_board_token():
    # successfactors ids have 4 segments: board token spans the middle two
    assert parse_hc_id("successfactors___eu___AFKL___1354459957") == \
        ("successfactors", "eu___AFKL", "1354459957")


def test_parse_double_underscore_recruitee():
    assert parse_hc_id("recruitee__greenflux__2664342") == \
        ("recruitee", "greenflux", "2664342")


def test_parse_url_encoded_ats_id():
    src, board, aid = parse_hc_id("sparkhire___rounds%2F59.005___99.D6D")
    assert board == "rounds/59.005"
    assert aid == "99.D6D"


def test_parse_unrecognisable_returns_none():
    assert parse_hc_id("no-separators-here") is None


def test_smartrecruiters_section_join():
    sections = {
        "companyDescription": {"title": "About", "text": "<p>We build stuff.</p>"},
        "jobDescription": {"title": "Role", "text": "<p>You will PM.</p>"},
        "irrelevant": "not-a-dict",
    }
    text = _join_smartrecruiters_sections(sections)
    assert "We build stuff." in text
    assert "You will PM." in text
