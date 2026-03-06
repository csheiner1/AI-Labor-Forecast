"""Tests for social_impact.onet_skills module."""
import pytest
import numpy as np


def test_build_skill_vectors():
    """build_skill_vectors should return soc_list, elements, matrix."""
    from social_impact.onet_skills import build_skill_vectors
    soc_list, elements, matrix = build_skill_vectors()
    assert isinstance(soc_list, list)
    assert isinstance(elements, list)
    assert isinstance(matrix, np.ndarray)
    assert len(soc_list) > 100
    assert len(elements) > 50
    assert matrix.shape == (len(soc_list), len(elements))


def test_skill_vectors_with_project_filter():
    """Filtering by project SOCs should reduce the count."""
    from social_impact.onet_skills import build_skill_vectors
    small_set = {"11-1011", "15-1252", "29-1141"}
    soc_list, elements, matrix = build_skill_vectors(project_socs=small_set)
    assert len(soc_list) <= len(small_set)
    assert matrix.shape[0] == len(soc_list)


def test_find_transition_targets():
    """find_transition_targets should return similar occupations."""
    from social_impact.onet_skills import build_skill_vectors, find_transition_targets
    soc_list, elements, matrix = build_skill_vectors()
    displacement_data = {soc: {"d_mod_low": 0.05, "title": soc, "employment_K": 100}
                         for soc in soc_list}
    # Make source have high displacement
    if "11-1011" in soc_list:
        displacement_data["11-1011"]["d_mod_low"] = 0.20
        targets = find_transition_targets("11-1011", soc_list, matrix,
                                          displacement_data, n_candidates=5)
        assert isinstance(targets, list)
        assert len(targets) > 0
        # Targets should have lower displacement
        for t in targets:
            assert t["d_mod_low"] <= 0.15


def test_find_transition_targets_missing_soc():
    """Missing SOC should return empty list."""
    from social_impact.onet_skills import build_skill_vectors, find_transition_targets
    soc_list, elements, matrix = build_skill_vectors()
    targets = find_transition_targets("99-9999", soc_list, matrix, {})
    assert targets == []


def test_get_cached_vectors():
    """get_cached_vectors should cache and return same object."""
    from social_impact.onet_skills import get_cached_vectors, _cached_vectors
    import social_impact.onet_skills as mod
    mod._cached_vectors = None  # reset cache
    v1 = get_cached_vectors()
    v2 = get_cached_vectors()
    assert v1[0] is v2[0]  # same list object
