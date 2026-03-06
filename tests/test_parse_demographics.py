"""Tests for social_impact.parse_demographics module."""
import pytest
import os


@pytest.fixture
def demo_data():
    """Try to parse demographics if cached file exists."""
    from social_impact.config import DATA_CACHE
    race_file = os.path.join(DATA_CACHE, "cpsaat11.xlsx")
    if not os.path.exists(race_file):
        pytest.skip("cpsaat11.xlsx not downloaded; run pipeline first")
    from social_impact.parse_demographics import parse_cpsaat11
    return parse_cpsaat11(race_file)


def test_parse_cpsaat11_returns_dict(demo_data):
    """parse_cpsaat11 should return a dict of occupation title -> record."""
    assert isinstance(demo_data, dict)
    assert len(demo_data) > 50


def test_parse_cpsaat11_fields(demo_data):
    """Each record should have expected demographic fields."""
    required = {"total_employed_K", "pct_female"}
    for title, rec in list(demo_data.items())[:5]:
        for field in required:
            assert field in rec, f"{field} missing for {title}"


def test_parse_cpsaat11_pct_in_range(demo_data):
    """Percentage fields should be in 0-100 range."""
    for title, rec in demo_data.items():
        pct = rec.get("pct_female")
        if pct is not None:
            assert 0 <= pct <= 100, f"pct_female={pct} out of range for {title}"


@pytest.fixture
def age_data():
    """Try to parse age data if cached file exists."""
    from social_impact.config import DATA_CACHE
    age_file = os.path.join(DATA_CACHE, "cpsaat11b.xlsx")
    if not os.path.exists(age_file):
        pytest.skip("cpsaat11b.xlsx not downloaded; run pipeline first")
    from social_impact.parse_demographics import parse_cpsaat11b
    return parse_cpsaat11b(age_file)


def test_parse_cpsaat11b_returns_dict(age_data):
    """parse_cpsaat11b should return a dict."""
    assert isinstance(age_data, dict)
    assert len(age_data) > 50


def test_parse_cpsaat11b_has_over55(age_data):
    """Each record should have pct_over_55 field."""
    for title, rec in list(age_data.items())[:5]:
        assert "pct_over_55" in rec
