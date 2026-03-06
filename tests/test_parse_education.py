"""Tests for social_impact.parse_education module."""
import pytest
import os


@pytest.fixture
def edu_attainment():
    """Parse education attainment data."""
    from social_impact.config import DATA_CACHE
    f = os.path.join(DATA_CACHE, "education.xlsx")
    if not os.path.exists(f):
        pytest.skip("education.xlsx not downloaded; run pipeline first")
    from social_impact.parse_education import parse_education_attainment
    return parse_education_attainment(f)


@pytest.fixture
def entry_ed():
    """Parse entry education data."""
    from social_impact.config import DATA_CACHE
    f = os.path.join(DATA_CACHE, "education.xlsx")
    if not os.path.exists(f):
        pytest.skip("education.xlsx not downloaded; run pipeline first")
    from social_impact.parse_education import parse_entry_education
    return parse_entry_education(f)


def test_attainment_returns_dict(edu_attainment):
    assert isinstance(edu_attainment, dict)
    assert len(edu_attainment) > 50


def test_attainment_has_bachelors_pct(edu_attainment):
    """Records should have pct_bachelors_plus field."""
    for title, rec in list(edu_attainment.items())[:5]:
        assert "pct_bachelors_plus" in rec
        val = rec["pct_bachelors_plus"]
        assert 0 <= val <= 100


def test_entry_education_returns_dict(entry_ed):
    assert isinstance(entry_ed, dict)
    assert len(entry_ed) > 50


def test_entry_education_has_string_values(entry_ed):
    """Values should be education level strings."""
    for soc, edu_str in list(entry_ed.items())[:5]:
        assert isinstance(edu_str, str)
        assert len(edu_str) > 0
