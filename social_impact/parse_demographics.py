"""Parse BLS CPSAAT11 (race/gender) and CPSAAT11B (age) tables.

These files have irregular Excel layouts:
- Multi-row headers with merged cells
- Occupation names in column A, data in columns B+
- Indentation indicates hierarchy (major group > detailed occ)
- Census occupation codes embedded in occupation names (sometimes)

Strategy: Use pandas to read the raw sheets, then manual row-by-row
parsing to extract the demographic data keyed by occupation text.
Match to Census codes using the occupation title text.
"""
import os
import re
import pandas as pd
from social_impact.config import DATA_CACHE


def _clean_occupation_text(text):
    """Normalize occupation text for matching."""
    if not text or pd.isna(text):
        return ""
    text = str(text).strip()
    # Remove footnote markers (1-2 trailing digits preceded by whitespace)
    text = re.sub(r'\s+\d{1,2}$', '', text).strip()
    return text


def parse_cpsaat11(filepath=None):
    """Parse CPSAAT11 (Employed persons by detailed occupation, sex, race, ethnicity).

    The table structure (after headers):
    Col 0: Occupation title
    Col 1: Total employed (thousands)
    Col 2: Percent Women
    Col 3: Percent White
    Col 4: Percent Black or African American
    Col 5: Percent Asian
    Col 6: Percent Hispanic or Latino

    Note: Column positions may vary by year. We detect them from the header row.

    Returns:
        dict: occupation_text -> {
            total_employed_K, pct_female, pct_white, pct_black, pct_asian, pct_hispanic
        }
    """
    if filepath is None:
        filepath = os.path.join(DATA_CACHE, "cpsaat11.xlsx")

    # Read all data, no header inference
    df = pd.read_excel(filepath, header=None, sheet_name=0)

    # CPSAAT11 has multi-row headers spanning rows 3-5:
    # Row 4: "Total employed", "Percent of total employed"
    # Row 5: "", "", "Women", "White", "Black or African American", "Asian", "Hispanic or Latino"
    # Data starts at row 7 (0-indexed 6).
    # We search for the row containing "Women" to detect column positions.
    header_row = None
    col_map = {}
    for i in range(min(20, len(df))):
        row_vals = [str(v).strip().lower() if pd.notna(v) else "" for v in df.iloc[i]]
        if "women" in row_vals:
            for j, val in enumerate(row_vals):
                if "women" in val:
                    col_map["pct_female"] = j
                elif "white" in val:
                    col_map["pct_white"] = j
                elif "black" in val or "african" in val:
                    col_map["pct_black"] = j
                elif "asian" in val:
                    col_map["pct_asian"] = j
                elif "hispanic" in val or "latino" in val:
                    col_map["pct_hispanic"] = j
            # Total employed is in column 1 (the row above usually has "Total employed")
            col_map["total"] = 1
            header_row = i
            break

    if header_row is None:
        # Fallback to known layout
        print("  WARNING: Could not detect CPSAAT11 headers, using fallback columns")
        header_row = 5
        col_map = {"total": 1, "pct_female": 2, "pct_white": 3,
                    "pct_black": 4, "pct_asian": 5, "pct_hispanic": 6}

    print(f"  CPSAAT11: header at row {header_row}, columns: {col_map}")

    results = {}
    for i in range(header_row + 1, len(df)):
        occ_text = _clean_occupation_text(df.iloc[i, 0])
        if not occ_text or occ_text.lower().startswith("note"):
            continue

        # Skip rows that are just major group headers (no data)
        total_val = df.iloc[i, col_map.get("total", 1)]
        if pd.isna(total_val) or not isinstance(total_val, (int, float)):
            continue

        record = {"total_employed_K": total_val}
        for field in ["pct_female", "pct_white", "pct_black", "pct_asian", "pct_hispanic"]:
            col = col_map.get(field)
            if col is not None:
                val = df.iloc[i, col]
                record[field] = float(val) if pd.notna(val) and isinstance(val, (int, float)) else None
            else:
                record[field] = None

        results[occ_text] = record

    print(f"  CPSAAT11: {len(results)} occupation entries parsed")
    return results


def parse_cpsaat11b(filepath=None):
    """Parse CPSAAT11B (Employed persons by detailed occupation and age).

    Extracts: Median_Age, Pct_Over_55 per occupation.

    Returns:
        dict: occupation_text -> {total_employed_K, median_age, pct_over_55}
    """
    if filepath is None:
        filepath = os.path.join(DATA_CACHE, "cpsaat11b.xlsx")

    df = pd.read_excel(filepath, header=None, sheet_name=0)

    # Find header row containing age ranges
    header_row = None
    col_map = {}
    for i in range(min(20, len(df))):
        row_vals = [str(v).strip().lower() if pd.notna(v) else "" for v in df.iloc[i]]
        joined = " ".join(row_vals)
        if "median age" in joined or "55" in joined:
            for j, val in enumerate(row_vals):
                if "total" in val:
                    col_map["total"] = j
                elif "median" in val and "age" in val:
                    col_map["median_age"] = j
                elif "55" in val and ("64" in val or "over" in val or "years" in val):
                    col_map["pct_55_64"] = j
                elif "65" in val and ("over" in val or "older" in val or "years" in val):
                    col_map["pct_65_plus"] = j
            if "median_age" in col_map:
                header_row = i
                break

    if header_row is None:
        print("  WARNING: Could not detect CPSAAT11B headers, using fallback")
        header_row = 3
        col_map = {"total": 1, "median_age": 8}

    print(f"  CPSAAT11B: header at row {header_row}, columns: {col_map}")

    results = {}
    for i in range(header_row + 1, len(df)):
        occ_text = _clean_occupation_text(df.iloc[i, 0])
        if not occ_text or occ_text.lower().startswith("note"):
            continue

        total_val = df.iloc[i, col_map.get("total", 1)]
        if pd.isna(total_val) or not isinstance(total_val, (int, float)):
            continue

        record = {"total_employed_K": total_val}

        # Median age
        median_col = col_map.get("median_age")
        if median_col is not None:
            val = df.iloc[i, median_col]
            record["median_age"] = float(val) if pd.notna(val) and isinstance(val, (int, float)) else None
        else:
            record["median_age"] = None

        # Over 55: CPSAAT11B columns are employment counts (thousands), not percentages.
        # Sum 55-64 and 65+ counts, then divide by total to get percentage.
        has_age_cols = "pct_55_64" in col_map or "pct_65_plus" in col_map
        count_55_64 = 0.0
        count_65_plus = 0.0
        if "pct_55_64" in col_map:
            val = df.iloc[i, col_map["pct_55_64"]]
            count_55_64 = float(val) if pd.notna(val) and isinstance(val, (int, float)) else 0.0
        if "pct_65_plus" in col_map:
            val = df.iloc[i, col_map["pct_65_plus"]]
            count_65_plus = float(val) if pd.notna(val) and isinstance(val, (int, float)) else 0.0
        if has_age_cols and total_val and total_val > 0:
            record["pct_over_55"] = round((count_55_64 + count_65_plus) / total_val * 100, 1)
        else:
            record["pct_over_55"] = None

        results[occ_text] = record

    print(f"  CPSAAT11B: {len(results)} occupation entries parsed")
    return results
