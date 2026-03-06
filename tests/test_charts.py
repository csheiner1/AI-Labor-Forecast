"""Tests for dashboard.charts module."""
import pytest
import os


def test_chart_dir_exists():
    """Static image directory should exist."""
    from dashboard.charts import CHART_DIR
    assert os.path.isdir(CHART_DIR)


def test_equity_charts_exist():
    """Equity charts should have been generated."""
    from dashboard.charts import CHART_DIR
    expected = [
        "equity_wage_quintile.png",
        "equity_gender.png",
        "equity_female_bins.png",
        "equity_black_bins.png",
        "equity_hispanic_bins.png",
        "equity_age55_bins.png",
    ]
    for fn in expected:
        path = os.path.join(CHART_DIR, fn)
        assert os.path.exists(path), f"Missing chart: {fn}"
        assert os.path.getsize(path) > 1000, f"Chart {fn} too small"


def test_geo_chart_exists():
    """Geographic state risk chart should exist."""
    from dashboard.charts import CHART_DIR
    path = os.path.join(CHART_DIR, "geo_state_risk.png")
    assert os.path.exists(path)
    assert os.path.getsize(path) > 1000


def test_political_charts_exist():
    """Political charts should exist."""
    from dashboard.charts import CHART_DIR
    for fn in ["pol_lean_scatter.png", "pol_education.png"]:
        path = os.path.join(CHART_DIR, fn)
        assert os.path.exists(path), f"Missing chart: {fn}"
        assert os.path.getsize(path) > 1000


def test_chart_functions_callable():
    """All chart functions should be importable."""
    from dashboard.charts import (
        chart_displacement_by_demographic,
        chart_wage_quintile_displacement,
        chart_gender_displacement,
        chart_state_displacement_risk,
        chart_partisan_lean_vs_displacement,
        chart_education_displacement,
        generate_all_charts,
    )
    # Just verify they're callable
    assert callable(generate_all_charts)
