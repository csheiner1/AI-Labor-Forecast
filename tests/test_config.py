"""Tests for social_impact config."""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_config_paths_exist():
    from social_impact.config import PROJECT_ROOT, WORKBOOK
    assert os.path.isdir(PROJECT_ROOT)
    assert os.path.exists(WORKBOOK), f"Workbook not found at {WORKBOOK}"


def test_sources_all_have_urls():
    from social_impact.config import SOURCES
    assert len(SOURCES) >= 7
    for key, url in SOURCES.items():
        assert url.startswith("https://"), f"{key} URL does not start with https://"


def test_foreign_born_data_complete():
    from social_impact.config import FOREIGN_BORN_BY_MAJOR_GROUP
    # Should cover at least the white-collar major groups
    for major in ["11", "13", "15", "17", "23", "25", "29"]:
        assert major in FOREIGN_BORN_BY_MAJOR_GROUP, f"Missing major group {major}"


def test_onet_dir_resolves_to_main_repo():
    """ONET_DIR should point to main repo root even in a worktree."""
    from social_impact.config import ONET_DIR, ONET_ZIP
    # ONET_DIR should be an absolute path containing onet_data
    assert os.path.isabs(ONET_DIR), f"ONET_DIR should be absolute: {ONET_DIR}"
    assert "onet_data" in ONET_DIR
    # ONET_ZIP should point to the main repo's onet_db.zip
    assert ONET_ZIP.endswith("onet_db.zip")
