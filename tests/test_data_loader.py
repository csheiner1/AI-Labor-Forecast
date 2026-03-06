"""Tests for dashboard.data_loader module."""
import pytest


def test_datastore_load():
    """DataStore should load data from workbook."""
    from dashboard.data_loader import DataStore
    store = DataStore()
    store.load()
    assert len(store.results) > 300
    assert len(store.soc_lookup) > 200


def test_datastore_get_all():
    """get_all should return list of merged dicts."""
    from dashboard.data_loader import DataStore
    store = DataStore()
    store.load()
    data = store.get_all()
    assert isinstance(data, list)
    assert len(data) == len(store.soc_lookup)
    # Each record should have SOC_Code
    for r in data[:5]:
        assert "SOC_Code" in r


def test_datastore_get_soc():
    """get_soc should return dict for valid SOC."""
    from dashboard.data_loader import DataStore
    store = DataStore()
    store.load()
    soc = list(store.soc_lookup.keys())[0]
    rec = store.get_soc(soc)
    assert rec is not None
    assert rec["SOC_Code"] == soc


def test_datastore_get_soc_missing():
    """get_soc should return None for invalid SOC."""
    from dashboard.data_loader import DataStore
    store = DataStore()
    store.load()
    assert store.get_soc("99-9999") is None


def test_datastore_get_sectors():
    """get_sectors should return sorted list of sector names."""
    from dashboard.data_loader import DataStore
    store = DataStore()
    store.load()
    sectors = store.get_sectors()
    assert isinstance(sectors, list)
    assert len(sectors) > 5
    assert sectors == sorted(sectors)


def test_datastore_get_wage_quintiles():
    """get_wage_quintiles should return 5 quintile buckets."""
    from dashboard.data_loader import DataStore
    store = DataStore()
    store.load()
    quintiles = store.get_wage_quintiles()
    assert len(quintiles) == 5
    for label, socs in quintiles.items():
        assert len(socs) > 0


def test_datastore_deduplicates():
    """Duplicate SOCs should be merged into single entries."""
    from dashboard.data_loader import DataStore
    store = DataStore()
    store.load()
    soc_codes = [r["SOC_Code"] for r in store.get_all()]
    assert len(soc_codes) == len(set(soc_codes))


def test_datastore_social_data_merged():
    """Social Impact data should be merged into results."""
    from dashboard.data_loader import DataStore
    store = DataStore()
    store.load()
    # At least some records should have social impact fields
    social_fields = ["Pct_Female", "Top_State_1", "Union_Rate_Pct"]
    for field in social_fields:
        count = sum(1 for r in store.get_all() if r.get(field) is not None)
        assert count > 100, f"Only {count} records have {field}"
