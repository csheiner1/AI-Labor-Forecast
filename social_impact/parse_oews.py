"""Parse OEWS (Occupational Employment and Wage Statistics) state and metro data.

State data: SOC x state employment and wages -> top 3 states per SOC
Metro data: SOC x MSA employment -> top metro by location quotient per SOC

These are large files (~4M rows for metro). We parse them into per-SOC
lookups for the workbook tab (top-3 states, top metro LQ), and provide
functions for the Flask app to query at runtime.
"""
import os
import re
import pandas as pd

from social_impact.config import DATA_CACHE


def _find_oews_csv(subdir, pattern="state"):
    """Find the OEWS CSV/Excel file in the extracted ZIP directory.

    ZIP extraction may produce a nested subdirectory, so we search recursively.
    """
    extract_dir = os.path.join(DATA_CACHE, subdir)
    if not os.path.isdir(extract_dir):
        return None
    # Walk the directory tree to find matching files
    for root, dirs, files in os.walk(extract_dir):
        for f in files:
            if pattern in f.lower() and (f.endswith(".xlsx") or f.endswith(".csv")):
                return os.path.join(root, f)
    # Fallback: any xlsx/csv
    for root, dirs, files in os.walk(extract_dir):
        for f in files:
            if f.endswith(".xlsx") or f.endswith(".csv"):
                return os.path.join(root, f)
    return None


def _normalize_soc(soc_str):
    """Normalize OEWS SOC code to project format.

    Validates format (XX-XXXX) and excludes:
    - Aggregate codes ending in 0000 (e.g. "11-0000", "00-0000")
    - Non-standard formats
    """
    if not soc_str:
        return None
    soc = str(soc_str).strip()
    if soc.endswith(".00"):
        soc = soc[:-3]
    # Must match XX-XXXX format
    if not re.match(r'^\d{2}-\d{4}$', soc):
        return None
    # Exclude aggregate codes (e.g. "11-0000", "00-0000")
    if soc.endswith("0000"):
        return None
    return soc


def parse_oews_state(project_socs=None):
    """Parse OEWS state data to find top-3 states per SOC by employment.

    Also returns full state-level employment shares per SOC for proportional
    geographic displacement allocation (not just the top-3 names).

    Args:
        project_socs: set of SOC codes to filter for (optional)

    Returns:
        tuple: (top3_dict, shares_dict)
            top3_dict: soc_code -> [state1, state2, state3] ordered by employment
            shares_dict: soc_code -> {state_name: employment_share_fraction, ...}
                         (all states, shares sum to 1.0 per SOC)
    """
    filepath = _find_oews_csv("oews_state")
    if filepath is None:
        print("  WARNING: OEWS state file not found")
        return {}, {}

    print(f"  Reading OEWS state data from {os.path.basename(filepath)}...")

    if filepath.endswith(".xlsx"):
        df = pd.read_excel(filepath, dtype=str)
    else:
        df = pd.read_csv(filepath, dtype=str)

    # Normalize column names
    df.columns = [c.strip().upper() for c in df.columns]

    # Find relevant columns -- prefer AREA_TITLE over PRIM_STATE for full names
    soc_col = None
    state_col = None
    emp_col = None
    for c in df.columns:
        if "OCC_CODE" in c or "SOC" in c:
            soc_col = c
        elif "AREA_TITLE" in c:
            state_col = c
        elif "TOT_EMP" in c or "EMPLOYMENT" in c:
            emp_col = c
    # Fallback to PRIM_STATE if AREA_TITLE not found
    if state_col is None:
        for c in df.columns:
            if "STATE" in c:
                state_col = c
                break

    if not all([soc_col, state_col, emp_col]):
        print(f"  WARNING: Could not find required columns. Available: {list(df.columns)}")
        return {}, {}

    print(f"  Columns: SOC={soc_col}, State={state_col}, Emp={emp_col}")

    # Filter to detailed SOCs (not groups) and convert employment to numeric
    df[emp_col] = pd.to_numeric(df[emp_col], errors="coerce")
    df = df[df[emp_col].notna() & (df[emp_col] > 0)].copy()

    # Normalize SOC codes and filter
    df["_soc"] = df[soc_col].apply(_normalize_soc)
    df = df[df["_soc"].notna()]
    if project_socs:
        df = df[df["_soc"].isin(project_socs)]
    df = df[df[state_col].notna()]

    # Vectorized groupby approach for top-3 states and employment shares
    top3_results = {}
    shares_results = {}
    for soc, group in df.groupby("_soc"):
        sorted_group = group.sort_values(emp_col, ascending=False)
        states = sorted_group[state_col].tolist()
        emps = sorted_group[emp_col].tolist()
        top3_results[soc] = states[:3]
        total_emp = sum(emps)
        if total_emp > 0:
            shares_results[soc] = {s: e / total_emp for s, e in zip(states, emps)}
        else:
            shares_results[soc] = {}

    print(f"  OEWS state: top-3 states for {len(top3_results)} SOCs, "
          f"shares for {len(shares_results)} SOCs")
    return top3_results, shares_results


def parse_oews_metro_lq(project_socs=None):
    """Parse OEWS metro data to find top metro by location quotient per SOC.

    Location quotient (LQ) measures concentration: an LQ > 1 means the
    occupation is more concentrated in that metro than nationally.

    Args:
        project_socs: set of SOC codes to filter for (optional)

    Returns:
        dict: soc_code -> "Metro Name (LQ=X.XX)"
    """
    filepath = _find_oews_csv("oews_metro", pattern="msa")
    if filepath is None:
        filepath = _find_oews_csv("oews_metro", pattern="metro")
    if filepath is None:
        print("  WARNING: OEWS metro file not found")
        return {}

    print(f"  Reading OEWS metro data from {os.path.basename(filepath)}...")
    print("  (This file is large, may take 30-60 seconds...)")

    if filepath.endswith(".xlsx"):
        df = pd.read_excel(filepath, dtype=str)
    else:
        df = pd.read_csv(filepath, dtype=str, low_memory=False)

    df.columns = [c.strip().upper() for c in df.columns]

    soc_col = None
    area_col = None
    lq_col = None
    for c in df.columns:
        if "OCC_CODE" in c:
            soc_col = c
        elif "AREA_TITLE" in c:
            area_col = c
        elif "LOC_QUOTIENT" in c or "LQ" in c.replace("_", ""):
            lq_col = c

    if not all([soc_col, area_col, lq_col]):
        print(f"  WARNING: Could not find required columns. Available: {list(df.columns)}")
        return {}

    df[lq_col] = pd.to_numeric(df[lq_col], errors="coerce")
    df = df[df[lq_col].notna() & (df[lq_col] > 0)]

    # Find top metro by LQ per SOC
    results = {}
    soc_groups = df.groupby(soc_col)
    for soc_raw, group in soc_groups:
        soc = _normalize_soc(soc_raw)
        if not soc:
            continue
        if project_socs and soc not in project_socs:
            continue
        top = group.nlargest(1, lq_col).iloc[0]
        metro = top[area_col]
        lq = top[lq_col]
        results[soc] = f"{metro} (LQ={lq:.2f})"

    print(f"  OEWS metro: top metro LQ for {len(results)} SOCs")
    return results
