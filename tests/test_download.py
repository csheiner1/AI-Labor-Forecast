"""Tests for BLS file downloader.

The first two tests make real HTTP requests (or rely on cached files).
They are skipped in CI or when SKIP_NETWORK_TESTS=1 is set.
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_skip_network = pytest.mark.skipif(
    os.environ.get("CI") == "true" or os.environ.get("SKIP_NETWORK_TESTS") == "1",
    reason="Skipped in CI / offline environments (set SKIP_NETWORK_TESTS=1)",
)


@_skip_network
def test_download_file_returns_path():
    from social_impact.download import download_file
    # Test with a small file (crosswalk)
    path = download_file("census_soc_crosswalk")
    assert path is not None
    assert os.path.exists(path)
    assert os.path.getsize(path) > 1000, "Downloaded file too small"


@_skip_network
def test_download_file_caching():
    from social_impact.download import download_file
    # Second call should use cache
    path1 = download_file("census_soc_crosswalk")
    path2 = download_file("census_soc_crosswalk")
    assert path1 == path2


def test_download_file_invalid_key():
    from social_impact.download import download_file
    with pytest.raises(KeyError):
        download_file("nonexistent_source")
