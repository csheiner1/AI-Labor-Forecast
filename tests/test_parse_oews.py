"""Tests for social_impact.parse_oews module."""
import pytest
import os


@pytest.fixture
def state_data():
    """Parse OEWS state data if available."""
    from social_impact.config import DATA_CACHE
    state_dir = os.path.join(DATA_CACHE, "oews_state")
    if not os.path.exists(state_dir):
        pytest.skip("OEWS state data not downloaded; run pipeline first")
    from social_impact.parse_oews import parse_oews_state
    top3, shares = parse_oews_state()
    return top3, shares


@pytest.fixture
def metro_data():
    """Parse OEWS metro data if available."""
    from social_impact.config import DATA_CACHE
    metro_dir = os.path.join(DATA_CACHE, "oews_metro")
    if not os.path.exists(metro_dir):
        pytest.skip("OEWS metro data not downloaded; run pipeline first")
    from social_impact.parse_oews import parse_oews_metro_lq
    return parse_oews_metro_lq()


def test_state_data_returns_tuple(state_data):
    """parse_oews_state returns (top3_dict, shares_dict)."""
    top3, shares = state_data
    assert isinstance(top3, dict)
    assert isinstance(shares, dict)
    assert len(top3) > 50


def test_state_data_has_top_states(state_data):
    """Each SOC should have a list of top states."""
    top3, _ = state_data
    for soc, states in list(top3.items())[:5]:
        assert isinstance(states, list)
        assert len(states) >= 1


def test_state_data_states_are_full_names(state_data):
    """State names should be full names, not abbreviations."""
    top3, _ = state_data
    for soc, states in list(top3.items())[:5]:
        for state_name in states:
            assert len(state_name) > 2, f"State appears to be abbreviation: {state_name}"


def test_metro_data_returns_dict(metro_data):
    assert isinstance(metro_data, dict)
    assert len(metro_data) > 50


def test_metro_data_has_lq_strings(metro_data):
    """Each SOC should map to a metro LQ string."""
    for soc, lq_str in list(metro_data.items())[:5]:
        assert isinstance(lq_str, str)
        assert "LQ" in lq_str
