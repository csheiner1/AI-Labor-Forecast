"""Tests for social_impact.merge module."""
import pytest
import os
import json


@pytest.fixture
def merged_data():
    """Load merged data from JSON output."""
    from social_impact.config import MERGED_OUTPUT
    if not os.path.exists(MERGED_OUTPUT):
        pytest.skip("merged_social_data.json not found; run pipeline first")
    with open(MERGED_OUTPUT) as f:
        return json.load(f)


def test_merged_data_is_list(merged_data):
    assert isinstance(merged_data, list)
    assert len(merged_data) > 200


def test_merged_records_have_soc(merged_data):
    """All records should have SOC_Code."""
    for rec in merged_data:
        assert "SOC_Code" in rec
        assert rec["SOC_Code"] is not None


def test_merged_records_have_demographics(merged_data):
    """Some records should have demographic fields."""
    demo_count = sum(1 for r in merged_data if r.get("Pct_Female") is not None)
    assert demo_count > 100, f"Only {demo_count} records have demographics"


def test_merged_records_have_geography(merged_data):
    """Some records should have geographic fields."""
    geo_count = sum(1 for r in merged_data if r.get("Top_State_1") is not None)
    assert geo_count > 100, f"Only {geo_count} records have geography"


def test_merged_records_have_union(merged_data):
    """Most records should have union rate."""
    union_count = sum(1 for r in merged_data if r.get("Union_Rate_Pct") is not None)
    assert union_count > 200, f"Only {union_count} records have union rate"


def test_edu_partisan_lean_computed(merged_data):
    """Records with bachelors_pct should have Edu_Partisan_Lean."""
    lean_count = sum(1 for r in merged_data if r.get("Edu_Partisan_Lean") is not None)
    assert lean_count > 50, f"Only {lean_count} records have partisan lean"


def test_compute_edu_partisan_lean():
    """Test the partisan lean formula directly."""
    from social_impact.merge import compute_edu_partisan_lean
    # 50% bachelor's = midpoint between D+13 and R-6
    lean = compute_edu_partisan_lean(50.0)
    assert isinstance(lean, float)
    # 100% bachelor's should lean heavily D
    lean_100 = compute_edu_partisan_lean(100.0)
    assert lean_100 > 0
    # 0% bachelor's should lean R
    lean_0 = compute_edu_partisan_lean(0.0)
    assert lean_0 < 0
