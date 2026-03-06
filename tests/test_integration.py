"""Integration tests for the full social impact pipeline."""
import pytest
import os
import json


def test_merged_json_exists():
    """Pipeline output JSON should exist."""
    from social_impact.config import MERGED_OUTPUT
    assert os.path.exists(MERGED_OUTPUT), "Run social_impact/run.py first"


def test_state_shares_exists():
    """State shares JSON should exist alongside merged data."""
    from social_impact.config import MERGED_OUTPUT
    state_shares_path = MERGED_OUTPUT.replace("merged_social_data.json", "state_shares.json")
    assert os.path.exists(state_shares_path)


def test_merged_json_matches_workbook():
    """Merged JSON record count should match workbook tab."""
    from social_impact.config import MERGED_OUTPUT, WORKBOOK
    import openpyxl

    with open(MERGED_OUTPUT) as f:
        data = json.load(f)

    wb = openpyxl.load_workbook(WORKBOOK, read_only=True)
    ws = wb["6 Social Impact"]
    wb_count = 0
    for row in ws.iter_rows(min_row=2, max_col=1, values_only=True):
        if row[0]:
            wb_count += 1
    wb.close()

    assert len(data) == wb_count, f"JSON has {len(data)}, workbook has {wb_count}"


def test_all_charts_generated():
    """All 9 expected chart PNG files should exist."""
    from dashboard.charts import CHART_DIR
    expected = [
        "equity_wage_quintile.png", "equity_gender.png",
        "equity_female_bins.png", "equity_black_bins.png",
        "equity_hispanic_bins.png", "equity_age55_bins.png",
        "geo_state_risk.png",
        "pol_lean_scatter.png", "pol_education.png",
    ]
    for fn in expected:
        assert os.path.exists(os.path.join(CHART_DIR, fn)), f"Missing: {fn}"


def test_dashboard_loads_data():
    """Dashboard DataStore should load without error."""
    from dashboard.data_loader import DataStore
    store = DataStore()
    store.load()
    assert len(store.soc_lookup) > 300
    # Verify some fields are populated
    sample = list(store.soc_lookup.values())[0]
    assert "SOC_Code" in sample


def test_pipeline_coverage():
    """At least 60% of SOCs should have demographic data."""
    from social_impact.config import MERGED_OUTPUT
    with open(MERGED_OUTPUT) as f:
        data = json.load(f)
    total = len(data)
    with_demo = sum(1 for r in data if r.get("Pct_Female") is not None)
    coverage = with_demo / total
    assert coverage >= 0.60, f"Demographic coverage only {coverage:.1%}"
