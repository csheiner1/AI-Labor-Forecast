"""Tests for .gitignore entries."""
import pytest
import os


def test_gitignore_has_data_cache():
    """Data cache directory should be in .gitignore."""
    gi_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".gitignore")
    with open(gi_path) as f:
        content = f.read()
    assert "data_cache" in content


def test_gitignore_has_chart_pngs():
    """Generated chart PNGs should be in .gitignore."""
    gi_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".gitignore")
    with open(gi_path) as f:
        content = f.read()
    assert "*.png" in content


def test_gitignore_has_merged_json():
    """Merged output JSON should be in .gitignore."""
    gi_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".gitignore")
    with open(gi_path) as f:
        content = f.read()
    assert "merged_social_data.json" in content
