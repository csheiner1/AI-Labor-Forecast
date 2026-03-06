"""Download and cache BLS data files."""
import os
import zipfile
import requests

from social_impact.config import DATA_CACHE, SOURCES


def download_file(key, force=False):
    """Download a source file if not already cached.

    Args:
        key: Key from SOURCES dict (e.g. 'cpsaat11')
        force: If True, re-download even if cached

    Returns:
        Path to the downloaded/cached file.
    """
    url = SOURCES[key]
    filename = url.split("/")[-1]
    local_path = os.path.join(DATA_CACHE, filename)

    if os.path.exists(local_path) and not force:
        print(f"  [{key}] Using cached: {filename}")
        return local_path

    os.makedirs(DATA_CACHE, exist_ok=True)
    print(f"  [{key}] Downloading {url}...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0.0.0 Safari/537.36",
    }
    resp = requests.get(url, timeout=120, headers=headers, stream=True)
    resp.raise_for_status()
    size = 0
    with open(local_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=65536):
            f.write(chunk)
            size += len(chunk)
    print(f"  [{key}] Saved: {filename} ({size / 1024:.0f} KB)")

    # Auto-extract ZIP files with path traversal protection
    if filename.endswith(".zip"):
        extract_dir = os.path.join(DATA_CACHE, key)
        os.makedirs(extract_dir, exist_ok=True)
        with zipfile.ZipFile(local_path) as zf:
            for member in zf.namelist():
                member_path = os.path.realpath(os.path.join(extract_dir, member))
                if not member_path.startswith(os.path.realpath(extract_dir) + os.sep) \
                   and member_path != os.path.realpath(extract_dir):
                    raise ValueError(f"ZIP member {member!r} would extract outside target dir")
            zf.extractall(extract_dir)
        print(f"  [{key}] Extracted to {extract_dir}/")

    return local_path


def download_all(force=False):
    """Download all source files."""
    print("Downloading BLS source data...")
    paths = {}
    for key in SOURCES:
        try:
            paths[key] = download_file(key, force=force)
        except Exception as e:
            print(f"  [{key}] FAILED: {e}")
            paths[key] = None
    return paths


if __name__ == "__main__":
    import sys
    force = "--force" in sys.argv
    download_all(force=force)
