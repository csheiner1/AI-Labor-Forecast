"""Social Impact Pipeline: download, parse, merge, writeback.

Usage:
    python3 social_impact/run.py              # Full pipeline
    python3 social_impact/run.py --download   # Download only
    python3 social_impact/run.py --merge      # Merge only (skip download)
    python3 social_impact/run.py --writeback  # Writeback only (from cached JSON)
"""
import sys
import time

from social_impact.download import download_all
from social_impact.merge import merge_all
from social_impact.writeback import writeback


KNOWN_FLAGS = {"--download", "--merge", "--writeback", "--force"}


def main():
    args = set(sys.argv[1:])
    start = time.time()

    unknown = args - KNOWN_FLAGS
    if unknown:
        print(f"WARNING: Unknown flag(s) ignored: {', '.join(sorted(unknown))}")
        print(f"  Known flags: {', '.join(sorted(KNOWN_FLAGS))}")

    force = "--force" in args
    # --force is a modifier, not a phase selector; strip it for phase logic
    phase_args = args - {"--force"} - unknown

    if not phase_args or "--download" in phase_args:
        print("=" * 60)
        print("PHASE 1: Download BLS source data")
        print("=" * 60)
        download_all(force=force)

    if not phase_args or "--merge" in phase_args:
        print("\n" + "=" * 60)
        print("PHASE 2: Parse and merge")
        print("=" * 60)
        data = merge_all()

    if not phase_args or "--writeback" in phase_args:
        print("\n" + "=" * 60)
        print("PHASE 3: Write to workbook")
        print("=" * 60)
        writeback()

    elapsed = time.time() - start
    print(f"\nDone in {elapsed:.1f}s")


if __name__ == "__main__":
    main()
