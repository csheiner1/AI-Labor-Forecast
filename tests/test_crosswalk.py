"""Tests for social_impact.crosswalk module."""
import pytest
import os
from unittest.mock import patch, MagicMock


def test_load_crosswalk_returns_three_dicts():
    """load_crosswalk returns (census_to_soc, soc_to_census, census_titles)."""
    from social_impact.crosswalk import load_crosswalk
    c2s, s2c, titles = load_crosswalk()
    assert isinstance(c2s, dict)
    assert isinstance(s2c, dict)
    assert isinstance(titles, dict)


def test_load_crosswalk_maps_census_to_soc():
    """Census codes should map to lists of SOC codes."""
    from social_impact.crosswalk import load_crosswalk
    c2s, s2c, titles = load_crosswalk()
    if c2s:
        for census_code, soc_list in list(c2s.items())[:5]:
            assert isinstance(soc_list, list)
            assert all(isinstance(s, str) for s in soc_list)


def test_load_project_socs():
    """load_project_socs reads from workbook 4 Results tab, returns dict."""
    from social_impact.crosswalk import load_project_socs
    socs = load_project_socs()
    assert isinstance(socs, dict)
    assert len(socs) > 100  # at least 100 SOCs
    # Each value should have title and sector
    sample = list(socs.values())[0]
    assert "title" in sample
    assert "sector" in sample


def test_build_soc_lookup():
    """build_soc_lookup creates mapping from project SOCs to census codes."""
    from social_impact.crosswalk import load_crosswalk, load_project_socs, build_soc_lookup
    _, soc_to_census, _ = load_crosswalk()
    project_socs = load_project_socs()
    lookup = build_soc_lookup(project_socs, soc_to_census)
    assert isinstance(lookup, dict)
    assert len(lookup) > 0
