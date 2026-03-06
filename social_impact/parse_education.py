"""Parse BLS employment projections education tables.

Both tables are sheets within the same downloaded file (education.xlsx):
  - Table 5.3: Educational attainment distribution (pct with each level)
  - Table 5.4: Typical entry-level education requirement

The BLS entry-education URL (occupation-entry-ed.xlsx) returns 404; Table 5.4
in education.xlsx contains the same data and is the authoritative source.
"""
import os
import re
import pandas as pd

from social_impact.config import DATA_CACHE


def _normalize_soc(soc_str):
    """Normalize SOC code: remove .00 suffix, strip whitespace."""
    if not soc_str:
        return None
    soc = str(soc_str).strip()
    if soc.endswith(".00"):
        soc = soc[:-3]
    # Must match pattern XX-XXXX
    if re.match(r'^\d{2}-\d{4}$', soc):
        return soc
    return None


def parse_education_attainment(filepath=None):
    """Parse Table 5.3: Educational attainment for workers 25+.

    We need: Pct_Bachelors_Plus, Pct_Graduate_Deg per SOC.
    Bachelors+ = bachelors + masters + doctoral/professional.

    Returns:
        dict: soc_code -> {pct_bachelors_plus, pct_graduate_deg}
    """
    if filepath is None:
        filepath = os.path.join(DATA_CACHE, "education.xlsx")

    df = pd.read_excel(filepath, header=None, sheet_name="Table 5.3")

    # Find the header row with column labels
    header_row = None
    soc_col = None
    edu_cols = {}

    for i in range(min(20, len(df))):
        row_vals = [str(v).strip().lower() if pd.notna(v) else "" for v in df.iloc[i]]
        joined = " ".join(row_vals)

        if ("bachelor" in joined or "doctoral" in joined) and \
           ("code" in joined or "matrix" in joined or "soc" in joined):
            for j, val in enumerate(row_vals):
                if "code" in val or "matrix code" in val:
                    soc_col = j
                elif "bachelor" in val:
                    edu_cols["bachelors"] = j
                elif "master" in val:
                    edu_cols["masters"] = j
                elif "doctoral" in val or "professional" in val:
                    edu_cols["doctoral"] = j
                elif "less than" in val or "high school" in val:
                    edu_cols["hs_or_less"] = j
                elif "some college" in val or "associate" in val:
                    edu_cols["some_college"] = j
            if soc_col is not None and len(edu_cols) >= 2:
                header_row = i
                break

    if header_row is None:
        print("  WARNING: Could not detect education attainment headers")
        print("  Attempting fallback parsing...")
        # Known layout for Table 5.3: col 1 = SOC code
        header_row = 1
        soc_col = 1
        edu_cols = {"bachelors": 6, "masters": 7, "doctoral": 8}

    print(f"  Education attainment: header row={header_row}, SOC col={soc_col}, "
          f"edu cols={edu_cols}")

    results = {}
    for i in range(header_row + 1, len(df)):
        soc = _normalize_soc(df.iloc[i, soc_col])
        if not soc:
            continue

        bachelors = 0
        masters = 0
        doctoral = 0

        for level, col in edu_cols.items():
            val = df.iloc[i, col]
            if pd.notna(val) and isinstance(val, (int, float)):
                if level == "bachelors":
                    bachelors = float(val)
                elif level == "masters":
                    masters = float(val)
                elif level == "doctoral":
                    doctoral = float(val)

        pct_bachelors_plus = round(bachelors + masters + doctoral, 1)
        pct_graduate = round(masters + doctoral, 1)

        results[soc] = {
            "pct_bachelors_plus": pct_bachelors_plus,
            "pct_graduate_deg": pct_graduate,
        }

    print(f"  Education attainment: {len(results)} SOCs parsed")
    return results


def parse_entry_education(filepath=None):
    """Parse Table 5.4: Typical entry-level education.

    Returns:
        dict: soc_code -> typical_entry_education (string)
    """
    if filepath is None:
        filepath = os.path.join(DATA_CACHE, "education.xlsx")

    df = pd.read_excel(filepath, header=None, sheet_name="Table 5.4")

    # Find header row
    header_row = None
    soc_col = None
    edu_col = None

    for i in range(min(20, len(df))):
        row_vals = [str(v).strip().lower() if pd.notna(v) else "" for v in df.iloc[i]]
        joined = " ".join(row_vals)

        if ("typical" in joined or "entry" in joined) and \
           ("code" in joined or "matrix" in joined):
            for j, val in enumerate(row_vals):
                if "code" in val or "matrix code" in val:
                    soc_col = j
                # Match "Typical education needed for entry" but NOT
                # "Typical on-the-job training..." -- check for "education" in same cell
                elif ("typical" in val and "education" in val) or \
                     ("entry" in val and "education" in val):
                    edu_col = j
            if soc_col is not None and edu_col is not None:
                header_row = i
                break

    if header_row is None:
        # Known fallback: col 1 = SOC code, col 2 = entry education
        print("  WARNING: Could not detect entry education headers, using fallback")
        header_row = 1
        soc_col = 1
        edu_col = 2

    print(f"  Entry education: header row={header_row}, SOC col={soc_col}, edu col={edu_col}")

    results = {}
    for i in range(header_row + 1, len(df)):
        soc = _normalize_soc(df.iloc[i, soc_col])
        if not soc:
            continue

        edu = df.iloc[i, edu_col]
        if pd.notna(edu):
            results[soc] = str(edu).strip()

    print(f"  Entry education: {len(results)} SOCs parsed")
    return results
