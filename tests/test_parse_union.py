"""Tests for social_impact.parse_union module."""
import pytest


def test_get_union_rate_valid_soc():
    """get_union_rate should return a float for valid SOC codes."""
    from social_impact.parse_union import get_union_rate
    rate = get_union_rate("25-1011")  # Education
    assert isinstance(rate, (int, float))
    assert 0 <= rate <= 100


def test_get_union_rate_none_for_unknown():
    """get_union_rate should return None for unknown SOC prefix."""
    from social_impact.parse_union import get_union_rate
    rate = get_union_rate("99-9999")
    assert rate is None


def test_union_rates_coverage():
    """Union rates should cover major SOC groups."""
    from social_impact.parse_union import UNION_RATES_2024
    assert len(UNION_RATES_2024) >= 20
    # Check some expected major groups
    assert "11" in UNION_RATES_2024  # Management
    assert "15" in UNION_RATES_2024  # Computer
    assert "29" in UNION_RATES_2024  # Healthcare practitioners


def test_union_rates_in_range():
    """All union rates should be between 0 and 100."""
    from social_impact.parse_union import UNION_RATES_2024
    for major, rate in UNION_RATES_2024.items():
        assert 0 <= rate <= 100, f"Union rate for {major} out of range: {rate}"
