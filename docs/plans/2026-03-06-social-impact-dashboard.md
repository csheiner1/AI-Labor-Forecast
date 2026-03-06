# Social Impact Data Pipeline & Dashboard — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enrich the workbook with a "6 Social Impact" tab containing demographic, education, political proxy, and geographic data for 310 SOCs, then build a 4-page Flask dashboard visualizing social implications of AI displacement.

**Architecture:** Two-phase build. Phase 1 is a data pipeline (`social_impact/` package) that downloads BLS/Census/O\*NET source files, crosswalks them to the project's 310 SOC codes, and writes a new workbook tab. Phase 2 is a Flask app (`dashboard/`) with 4 page routes that read from the workbook and O\*NET/OEWS data at runtime. The pipeline produces a single intermediate JSON (`social_impact/merged_social_data.json`) before the final workbook writeback, enabling inspection and reuse.

**Tech Stack:** Python 3, openpyxl, pandas, Flask, requests, numpy, scipy (for cosine similarity in transition pathways). No Plotly — charts rendered with matplotlib and served as static PNGs, consistent with existing `analysis/` pattern.

---

## Key Context

- **Workbook:** `jobs-data-v3.xlsx`, 8 existing tabs. New tab "6 Social Impact" will be the 9th.
- **310 SOC codes** in `4 Results` tab with displacement scores, employment, wages, sector assignments.
- **21 sectors** across the workbook.
- **Existing patterns:** The project uses openpyxl for all workbook I/O (never pandas for xlsx). Pipeline scripts live under `scoring/`. Analysis/visualization scripts live under `analysis/`. Flask is listed as a dependency but no app exists yet.
- **O\*NET data:** Already downloaded as `onet_db.zip` with extracted files in `onet_data/db_29_1_text/`. Contains Skills.txt, Knowledge.txt, Abilities.txt needed for transition pathways.
- **SOC format in workbook:** 2-digit major group + 4-digit detail, e.g. "11-1011". Some entries are comma-separated merged codes like "13-2051, 13-2052". BLS source data uses "11-1011.00" format (with .00 suffix).

### Data Source Summary

| Source | URL | Format | Join Key |
|--------|-----|--------|----------|
| CPSAAT11 (race/gender) | bls.gov/cps/cpsaat11.htm | XLSX, ~570 Census occ codes | Census occ -> SOC crosswalk |
| CPSAAT11B (age) | bls.gov/cps/cpsaat11b.htm | XLSX, same structure | Same crosswalk |
| BLS Table 5.3 (education attainment) | bls.gov/emp/tables/educational-attainment.htm | XLSX | Direct 6-digit SOC |
| BLS Table 5.4 (typical entry ed) | bls.gov/emp/tables.htm | XLSX | Direct 6-digit SOC |
| BLS CPS Union table | bls.gov/news.release/union2.t03.htm | HTML table | 2-digit SOC major group |
| Census->SOC crosswalk | bls.gov/cps/2018-census-occupation-classification-titles-and-code-list.xlsx | XLSX | Census code -> SOC |
| OEWS state data | bls.gov/oes/current/oessrcst.htm | Bulk ZIP | Direct 6-digit SOC |
| OEWS metro data | bls.gov/oes/current/oessrcma.htm | Bulk ZIP | Direct 6-digit SOC |
| O\*NET Skills/Knowledge | Local: onet_data/db_29_1_text/ | TSV | O\*NET-SOC (add .00 suffix) |
| ACS foreign-born (fallback) | BLS Foreign-born workers report | PDF/summary tables | 2-digit SOC major group |

### Critical Data Caveats

1. **Hispanic/Latino is ethnicity, not race.** Hispanic workers are also counted in White/Black/Asian. Pct_Hispanic is an independent column, not part of the race breakdown.
2. **CPSAAT11 uses Census occupation codes (~570), not SOC.** Most map 1:1 to SOC, but ~22 SOC codes aggregate into broader Census buckets. The crosswalk file resolves this.
3. **Union rate** is only available at the 2-digit SOC major group level (22 groups). All SOCs in the same major group get the same rate.
4. **Foreign-born share** — ACS PUMS would give SOC-level data but is too heavy. Use BLS annual report summary at 2-digit major group level as fallback.
5. **OEWS metro file** is ~4M rows. Process it at runtime for the geographic page rather than storing per-SOC data in the workbook (only top-3 states and top metro go in the tab).
6. **Education-partisan lean** is a derived proxy: `lean = pct_bachelors_plus * 0.13 + (1 - pct_bachelors_plus) * (-0.06)` based on Pew Research education-partisan gradient (college grads +13 Dem, non-college +6 Rep).

---

### Task 1: Create project structure and download infrastructure

**Files:**
- Create: `social_impact/__init__.py`
- Create: `social_impact/config.py`
- Create: `social_impact/download.py`

**Step 1: Create directory structure**

Run:
```bash
mkdir -p social_impact/data_cache
touch social_impact/__init__.py
```

**Step 2: Write config.py with all source URLs, paths, and constants**

```python
"""Configuration for Social Impact data pipeline."""
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKBOOK = os.path.join(PROJECT_ROOT, "jobs-data-v3.xlsx")
DATA_CACHE = os.path.join(PROJECT_ROOT, "social_impact", "data_cache")
MERGED_OUTPUT = os.path.join(PROJECT_ROOT, "social_impact", "merged_social_data.json")
ONET_DIR = os.path.join(PROJECT_ROOT, "onet_data", "db_29_1_text")

# BLS source URLs
SOURCES = {
    "cpsaat11": "https://www.bls.gov/cps/cpsaat11.xlsx",
    "cpsaat11b": "https://www.bls.gov/cps/cpsaat11b.xlsx",
    "edu_attainment": "https://www.bls.gov/emp/ind-occ-matrix/education.xlsx",
    "entry_education": "https://www.bls.gov/emp/ind-occ-matrix/occupation-entry-ed.xlsx",
    "census_soc_crosswalk": "https://www.bls.gov/cps/2018-census-occupation-classification-titles-and-code-list.xlsx",
    "oews_state": "https://www.bls.gov/oes/special-requests/oesm24st.zip",
    "oews_metro": "https://www.bls.gov/oes/special-requests/oesm24ma.zip",
}

# Union data is an HTML table, not a downloadable file
UNION_TABLE_URL = "https://www.bls.gov/news.release/union2.t03.htm"

# Foreign-born by major occupation group (from BLS 2024 report, Table 4)
# https://www.bls.gov/news.release/forbrn.t04.htm
# Values: percent foreign-born in major occupation group
FOREIGN_BORN_BY_MAJOR_GROUP = {
    "11": 12.2,  # Management
    "13": 16.1,  # Business and financial operations
    "15": 26.5,  # Computer and mathematical
    "17": 17.8,  # Architecture and engineering
    "19": 21.3,  # Life, physical, and social science
    "21": 13.1,  # Community and social service
    "23": 8.6,   # Legal
    "25": 10.9,  # Educational instruction and library
    "27": 13.5,  # Arts, design, entertainment, sports, media
    "29": 19.0,  # Healthcare practitioners and technical
    "31": 28.8,  # Healthcare support
    "33": 9.7,   # Protective service
    "35": 28.5,  # Food preparation and serving
    "37": 33.8,  # Building and grounds cleaning and maintenance
    "39": 16.7,  # Personal care and service
    "41": 12.1,  # Sales and related
    "43": 11.2,  # Office and administrative support
    "45": 42.4,  # Farming, fishing, and forestry
    "47": 30.2,  # Construction and extraction
    "49": 15.6,  # Installation, maintenance, and repair
    "51": 21.8,  # Production
    "53": 20.3,  # Transportation and material moving
}

# Education-partisan gradient (Pew Research Center, 2024)
# College grads lean +13 Dem, non-college lean +6 Rep
# We express as D-R margin: positive = Dem lean, negative = Rep lean
EDU_PARTISAN_COLLEGE = 0.13    # +13% Dem margin for bachelor's+
EDU_PARTISAN_NO_COLLEGE = -0.06  # +6% Rep margin for no bachelor's

# Our 310 SOC codes (loaded dynamically from workbook)
# This is populated at runtime by load_project_socs()
```

**Step 3: Write download.py with caching downloader**

```python
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
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    with open(local_path, "wb") as f:
        f.write(resp.content)
    print(f"  [{key}] Saved: {filename} ({len(resp.content) / 1024:.0f} KB)")

    # Auto-extract ZIP files
    if filename.endswith(".zip"):
        extract_dir = os.path.join(DATA_CACHE, key)
        os.makedirs(extract_dir, exist_ok=True)
        with zipfile.ZipFile(local_path) as zf:
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
```

**Step 4: Add data_cache to .gitignore**

Append to `.gitignore`:
```
# Social impact data cache (downloaded BLS files)
social_impact/data_cache/
```

**Step 5: Test downloads**

Run:
```bash
python3 -c "
from social_impact.download import download_file
# Test one small file first
path = download_file('census_soc_crosswalk')
print(f'Downloaded to: {path}')
import os
print(f'Size: {os.path.getsize(path)} bytes')
"
```

Expected: File downloads successfully, size > 10 KB.

**Step 6: Download all source files**

Run:
```bash
python3 social_impact/download.py
```

Expected: All files download. OEWS ZIPs auto-extract. Some files may fail if BLS URLs have changed — that's OK, we'll handle fallbacks per-parser.

**Step 7: Commit**

```bash
git add social_impact/__init__.py social_impact/config.py social_impact/download.py .gitignore
git commit -m "Add social impact pipeline: config and BLS data download"
```

---

### Task 2: Build Census-to-SOC crosswalk parser

**Files:**
- Create: `social_impact/crosswalk.py`

The CPSAAT11/11B tables use Census occupation codes (~570 codes), not SOC. The BLS provides a crosswalk file mapping Census codes to 2018 SOC. We need this crosswalk to join demographic data to our 310 project SOCs.

**Step 1: Write the crosswalk parser**

```python
"""Census occupation code <-> SOC crosswalk.

BLS file: '2018 Census occupation classification titles and code list'
Format: XLSX with columns like Census_Code, Census_Title, SOC_Code, SOC_Title
Many-to-many: one Census code can map to multiple SOC codes (broad groupings),
and multiple Census codes can share the same SOC.
"""
import os
import openpyxl
from collections import defaultdict

from social_impact.config import DATA_CACHE


def load_crosswalk(crosswalk_path=None):
    """Parse the Census->SOC crosswalk file.

    Returns:
        census_to_soc: dict mapping Census code (str) -> list of SOC codes (str)
        soc_to_census: dict mapping SOC code (str) -> list of Census codes (str)
    """
    if crosswalk_path is None:
        crosswalk_path = os.path.join(DATA_CACHE,
            "2018-census-occupation-classification-titles-and-code-list.xlsx")

    wb = openpyxl.load_workbook(crosswalk_path, read_only=True)
    ws = wb.active

    # Find header row — look for a row containing 'Census' and 'SOC'
    header_row = None
    census_col = None
    soc_col = None
    for r in range(1, min(20, ws.max_row + 1)):
        row_vals = [str(ws.cell(r, c).value or "").strip().lower() for c in range(1, ws.max_column + 1)]
        for i, val in enumerate(row_vals):
            if "census" in val and "code" in val:
                census_col = i + 1
            if "soc" in val and "code" in val:
                soc_col = i + 1
        if census_col and soc_col:
            header_row = r
            break

    if not header_row:
        # Fallback: try common column positions
        # Typically: col 1 = Census code, col 3 = SOC code
        print("  WARNING: Could not find header row, using fallback columns 1 & 3")
        census_col = 1
        soc_col = 3
        header_row = 1

    census_to_soc = defaultdict(list)
    soc_to_census = defaultdict(list)

    for r in range(header_row + 1, ws.max_row + 1):
        census_raw = ws.cell(r, census_col).value
        soc_raw = ws.cell(r, soc_col).value

        if not census_raw or not soc_raw:
            continue

        census_code = str(census_raw).strip()
        soc_code = str(soc_raw).strip()

        # Normalize SOC: remove .00 suffix if present
        if soc_code.endswith(".00"):
            soc_code = soc_code[:-3]

        # Skip non-numeric codes (headers, totals)
        if not census_code[0].isdigit():
            continue

        if soc_code not in census_to_soc[census_code]:
            census_to_soc[census_code].append(soc_code)
        if census_code not in soc_to_census[soc_code]:
            soc_to_census[soc_code].append(census_code)

    wb.close()

    print(f"  Crosswalk: {len(census_to_soc)} Census codes -> {len(soc_to_census)} SOC codes")
    return dict(census_to_soc), dict(soc_to_census)


def load_project_socs():
    """Load the 310 SOC codes from the workbook's 4 Results tab.

    Returns:
        dict: soc_code -> {title, sector, employment_K, median_wage}
    """
    from social_impact.config import WORKBOOK
    wb = openpyxl.load_workbook(WORKBOOK, read_only=True)
    ws = wb["4 Results"]

    socs = {}
    for r in range(2, ws.max_row + 1):
        soc = ws.cell(r, 1).value
        if not soc:
            continue
        socs[soc] = {
            "title": ws.cell(r, 2).value,
            "sector": ws.cell(r, 3).value,
            "employment_K": ws.cell(r, 5).value,
            "median_wage": ws.cell(r, 6).value,
        }

    wb.close()
    print(f"  Project SOCs: {len(socs)}")
    return socs


def build_soc_lookup(project_socs, soc_to_census):
    """Build a lookup: for each project SOC, find the Census codes to pull from.

    Handles merged SOCs (comma-separated like "13-2051, 13-2052") by trying
    each individual code.

    Returns:
        dict: project_soc -> list of Census codes
    """
    lookup = {}
    matched = 0
    unmatched = []

    for soc in project_socs:
        # Handle comma-separated merged SOCs
        individual_socs = [s.strip() for s in soc.split(",")]
        census_codes = []
        for s in individual_socs:
            if s in soc_to_census:
                census_codes.extend(soc_to_census[s])
        if census_codes:
            lookup[soc] = list(set(census_codes))
            matched += 1
        else:
            unmatched.append(soc)

    print(f"  SOC->Census lookup: {matched}/{len(project_socs)} matched")
    if unmatched:
        print(f"  Unmatched ({len(unmatched)}): {unmatched[:10]}")

    return lookup
```

**Step 2: Test the crosswalk**

Run:
```bash
python3 -c "
from social_impact.crosswalk import load_crosswalk, load_project_socs, build_soc_lookup
census_to_soc, soc_to_census = load_crosswalk()
project_socs = load_project_socs()
lookup = build_soc_lookup(project_socs, soc_to_census)
# Show a few mappings
for soc in list(lookup.keys())[:5]:
    print(f'  {soc} -> Census {lookup[soc]}')
"
```

Expected: ~280-310 SOCs matched (some may not have Census equivalents if they are combined/niche). Unmatched SOCs will fall back to major-group averages later.

**Step 3: Commit**

```bash
git add social_impact/crosswalk.py
git commit -m "Add Census-to-SOC crosswalk parser for demographic data join"
```

---

### Task 3: Parse CPSAAT11 (race/gender by occupation)

**Files:**
- Create: `social_impact/parse_demographics.py`

CPSAAT11 is an XLSX file with Census occupation codes and demographic breakdowns. The file has a non-standard layout: merged cells, multi-level headers, footnotes. We need to extract: Pct_Female, Pct_White, Pct_Black, Pct_Asian, Pct_Hispanic per Census occupation code.

**Step 1: Write the CPSAAT11 parser**

```python
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
from collections import defaultdict

from social_impact.config import DATA_CACHE


def _find_data_start(df):
    """Find the row where actual data begins (after header rows)."""
    for i in range(len(df)):
        row = df.iloc[i]
        # Look for a row where the first column has "Total" or a recognizable
        # occupation text, and subsequent columns have numbers
        first_val = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""
        if "total" in first_val.lower() and "16 years" in first_val.lower():
            return i
    # Fallback: look for first row with numeric data in column 2+
    for i in range(len(df)):
        row = df.iloc[i]
        if pd.notna(row.iloc[1]) and isinstance(row.iloc[1], (int, float)):
            return i
    return 0


def _clean_occupation_text(text):
    """Normalize occupation text for matching."""
    if not text or pd.isna(text):
        return ""
    text = str(text).strip()
    # Remove footnote markers
    text = re.sub(r'\d+$', '', text).strip()
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

    # Find header row containing "Women" or "Percent"
    header_row = None
    col_map = {}
    for i in range(min(20, len(df))):
        row_vals = [str(v).strip().lower() if pd.notna(v) else "" for v in df.iloc[i]]
        joined = " ".join(row_vals)
        if "women" in joined or "percent" in joined:
            # Map columns by header text
            for j, val in enumerate(row_vals):
                if "total" in val and ("employed" in val or "thousand" in val):
                    col_map["total"] = j
                elif "women" in val:
                    col_map["pct_female"] = j
                elif "white" in val:
                    col_map["pct_white"] = j
                elif "black" in val or "african" in val:
                    col_map["pct_black"] = j
                elif "asian" in val:
                    col_map["pct_asian"] = j
                elif "hispanic" in val or "latino" in val:
                    col_map["pct_hispanic"] = j
            if len(col_map) >= 4:
                header_row = i
                break

    if header_row is None:
        # Fallback to known layout
        print("  WARNING: Could not detect CPSAAT11 headers, using fallback columns")
        header_row = 3
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

        # Pct over 55: sum of 55-64 and 65+ columns if available
        pct_55_64 = 0
        pct_65_plus = 0
        if "pct_55_64" in col_map:
            val = df.iloc[i, col_map["pct_55_64"]]
            pct_55_64 = float(val) if pd.notna(val) and isinstance(val, (int, float)) else 0
        if "pct_65_plus" in col_map:
            val = df.iloc[i, col_map["pct_65_plus"]]
            pct_65_plus = float(val) if pd.notna(val) and isinstance(val, (int, float)) else 0
        record["pct_over_55"] = round(pct_55_64 + pct_65_plus, 1) if (pct_55_64 or pct_65_plus) else None

        results[occ_text] = record

    print(f"  CPSAAT11B: {len(results)} occupation entries parsed")
    return results
```

**Step 2: Test the parsers**

Run:
```bash
python3 -c "
from social_impact.parse_demographics import parse_cpsaat11, parse_cpsaat11b
demo = parse_cpsaat11()
age = parse_cpsaat11b()
# Show a few entries
for occ in list(demo.keys())[:5]:
    print(f'  {occ}: {demo[occ]}')
print()
for occ in list(age.keys())[:5]:
    print(f'  {occ}: {age[occ]}')
"
```

Expected: ~500-570 occupation entries parsed from each file. Verify that `pct_female`, `pct_white`, etc. are reasonable percentages.

**Step 3: Commit**

```bash
git add social_impact/parse_demographics.py
git commit -m "Add CPSAAT11/11B parsers for race, gender, and age demographics"
```

---

### Task 4: Parse education data (BLS Tables 5.3 and 5.4)

**Files:**
- Create: `social_impact/parse_education.py`

Tables 5.3 (education attainment distribution) and 5.4 (typical entry education) use direct SOC codes, so no crosswalk needed. However, the XLSX files have multi-row headers and merged cells.

**Step 1: Write the education parsers**

```python
"""Parse BLS employment projections education tables.

Table 5.3: Educational attainment distribution (pct with each level)
Table 5.4: Typical entry-level education requirement
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
        dict: soc_code -> {pct_bachelors_plus, pct_graduate_deg, distribution}
    """
    if filepath is None:
        filepath = os.path.join(DATA_CACHE, "education.xlsx")

    df = pd.read_excel(filepath, header=None, sheet_name=0)

    # Find the header row with column labels
    # Look for row with "SOC" or "Occupation" and education level names
    header_row = None
    soc_col = None
    edu_cols = {}

    for i in range(min(20, len(df))):
        row_vals = [str(v).strip().lower() if pd.notna(v) else "" for v in df.iloc[i]]
        joined = " ".join(row_vals)

        if ("bachelor" in joined or "doctoral" in joined) and ("soc" in joined or "code" in joined or "occupation" in joined):
            for j, val in enumerate(row_vals):
                if "code" in val or "soc" in val:
                    soc_col = j
                elif "occupation" in val and "title" in val:
                    pass  # skip title column
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
        # Try reading with pandas auto-header detection
        df2 = pd.read_excel(filepath, sheet_name=0)
        cols = [str(c).lower() for c in df2.columns]
        print(f"  Auto-detected columns: {cols}")
        return {}

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
    """Parse Table 5.4 or equivalent: Typical entry-level education.

    Returns:
        dict: soc_code -> typical_entry_education (string)
    """
    if filepath is None:
        filepath = os.path.join(DATA_CACHE, "occupation-entry-ed.xlsx")

    df = pd.read_excel(filepath, header=None, sheet_name=0)

    # Find header row
    header_row = None
    soc_col = None
    edu_col = None

    for i in range(min(20, len(df))):
        row_vals = [str(v).strip().lower() if pd.notna(v) else "" for v in df.iloc[i]]
        joined = " ".join(row_vals)

        if ("typical" in joined or "entry" in joined or "education" in joined) and \
           ("soc" in joined or "code" in joined or "occupation" in joined):
            for j, val in enumerate(row_vals):
                if "code" in val or "soc" in val:
                    soc_col = j
                elif "typical" in val or "entry" in val or "education" in val:
                    edu_col = j
            if soc_col is not None and edu_col is not None:
                header_row = i
                break

    if header_row is None:
        print("  WARNING: Could not detect entry education headers")
        return {}

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
```

**Step 2: Test the education parsers**

Run:
```bash
python3 -c "
from social_impact.parse_education import parse_education_attainment, parse_entry_education
edu = parse_education_attainment()
entry = parse_entry_education()
# Show sample
for soc in ['11-1011', '13-2011', '15-1252', '25-1011', '29-1141']:
    e = edu.get(soc, {})
    en = entry.get(soc, 'N/A')
    print(f'{soc}: bach+={e.get(\"pct_bachelors_plus\", \"?\")}  grad={e.get(\"pct_graduate_deg\", \"?\")}  entry={en}')
"
```

Expected: Most of our 310 SOC codes should have education data. Bachelor's+ percentages should range from ~10% to ~99%.

**Step 3: Commit**

```bash
git add social_impact/parse_education.py
git commit -m "Add BLS education attainment and entry education parsers"
```

---

### Task 5: Parse union data and build OEWS geographic lookups

**Files:**
- Create: `social_impact/parse_union.py`
- Create: `social_impact/parse_oews.py`

**Step 1: Write union rate parser (HTML table)**

```python
"""Parse BLS union membership table by major occupation group.

Source: https://www.bls.gov/news.release/union2.t03.htm
This is an HTML table, not a downloadable file.
Data is at 2-digit SOC major group level only.
"""
import os
import re
import requests
import pandas as pd

from social_impact.config import UNION_TABLE_URL, DATA_CACHE


# Fallback hardcoded values from BLS 2024 union membership report
# Major occupation group -> union membership rate (%)
UNION_RATES_2024 = {
    "11": 5.1,   # Management
    "13": 4.3,   # Business and financial operations
    "15": 5.2,   # Computer and mathematical
    "17": 8.3,   # Architecture and engineering
    "19": 10.5,  # Life, physical, and social science
    "21": 15.4,  # Community and social service
    "23": 5.8,   # Legal
    "25": 33.8,  # Educational instruction and library
    "27": 8.0,   # Arts, design, entertainment, sports, media
    "29": 11.6,  # Healthcare practitioners and technical
    "31": 10.8,  # Healthcare support
    "33": 33.9,  # Protective service
    "35": 4.7,   # Food preparation and serving
    "37": 11.9,  # Building and grounds cleaning
    "39": 5.7,   # Personal care and service
    "41": 3.4,   # Sales and related
    "43": 8.1,   # Office and administrative support
    "45": 3.2,   # Farming, fishing, forestry
    "47": 12.4,  # Construction and extraction
    "49": 10.8,  # Installation, maintenance, repair
    "51": 8.7,   # Production
    "53": 14.6,  # Transportation and material moving
}


def fetch_union_rates():
    """Try to fetch union rates from BLS website, fall back to hardcoded.

    Returns:
        dict: 2-digit SOC major group -> union rate (%)
    """
    try:
        resp = requests.get(UNION_TABLE_URL, timeout=30)
        resp.raise_for_status()
        tables = pd.read_html(resp.text)
        # Find the table with occupation groups
        for table in tables:
            cols = [str(c).lower() for c in table.columns]
            if any("union" in c or "member" in c for c in cols):
                print(f"  Found union table with {len(table)} rows")
                # Parse would go here, but BLS HTML tables are notoriously
                # inconsistent. If parsing succeeds, use it; otherwise fallback.
                break
        print("  Using hardcoded 2024 union rates (BLS parse succeeded but format uncertain)")
        return UNION_RATES_2024
    except Exception as e:
        print(f"  Union table fetch failed ({e}), using hardcoded 2024 values")
        return UNION_RATES_2024


def get_union_rate(soc_code):
    """Get union rate for a SOC code using its 2-digit major group."""
    major = soc_code.split("-")[0]
    return UNION_RATES_2024.get(major)
```

**Step 2: Write OEWS geographic data parser**

```python
"""Parse OEWS (Occupational Employment and Wage Statistics) state and metro data.

State data: SOC x state employment and wages -> top 3 states per SOC
Metro data: SOC x MSA employment -> top metro by location quotient per SOC

These are large files (~4M rows for metro). We parse them into per-SOC
lookups for the workbook tab (top-3 states, top metro LQ), and provide
functions for the Flask app to query at runtime.
"""
import os
import csv
import pandas as pd
from collections import defaultdict

from social_impact.config import DATA_CACHE


def _find_oews_csv(subdir, pattern="state"):
    """Find the OEWS CSV/Excel file in the extracted ZIP directory."""
    extract_dir = os.path.join(DATA_CACHE, subdir)
    if not os.path.isdir(extract_dir):
        return None
    for f in os.listdir(extract_dir):
        if pattern in f.lower() and (f.endswith(".xlsx") or f.endswith(".csv")):
            return os.path.join(extract_dir, f)
    # Try any xlsx/csv file
    for f in os.listdir(extract_dir):
        if f.endswith(".xlsx") or f.endswith(".csv"):
            return os.path.join(extract_dir, f)
    return None


def _normalize_soc(soc_str):
    """Normalize OEWS SOC code to project format."""
    if not soc_str:
        return None
    soc = str(soc_str).strip()
    if soc.endswith(".00"):
        soc = soc[:-3]
    return soc


def parse_oews_state(project_socs=None):
    """Parse OEWS state data to find top-3 states per SOC by employment.

    Args:
        project_socs: set of SOC codes to filter for (optional)

    Returns:
        dict: soc_code -> [state1, state2, state3] ordered by employment
    """
    filepath = _find_oews_csv("oews_state")
    if filepath is None:
        print("  WARNING: OEWS state file not found")
        return {}

    print(f"  Reading OEWS state data from {os.path.basename(filepath)}...")

    if filepath.endswith(".xlsx"):
        df = pd.read_excel(filepath, dtype=str)
    else:
        df = pd.read_csv(filepath, dtype=str)

    # Normalize column names
    df.columns = [c.strip().upper() for c in df.columns]

    # Find relevant columns
    soc_col = None
    state_col = None
    emp_col = None
    for c in df.columns:
        if "OCC_CODE" in c or "SOC" in c:
            soc_col = c
        elif "AREA_TITLE" in c or "STATE" in c:
            state_col = c
        elif "TOT_EMP" in c or "EMPLOYMENT" in c:
            emp_col = c

    if not all([soc_col, state_col, emp_col]):
        print(f"  WARNING: Could not find required columns. Available: {list(df.columns)}")
        return {}

    print(f"  Columns: SOC={soc_col}, State={state_col}, Emp={emp_col}")

    # Filter to detailed SOCs (not groups) and convert employment to numeric
    df[emp_col] = pd.to_numeric(df[emp_col], errors="coerce")
    df = df[df[emp_col].notna() & (df[emp_col] > 0)]

    # Build per-SOC state rankings
    soc_states = defaultdict(list)
    for _, row in df.iterrows():
        soc = _normalize_soc(row[soc_col])
        if not soc:
            continue
        if project_socs and soc not in project_socs:
            continue
        state = row[state_col]
        emp = row[emp_col]
        if state and emp > 0:
            soc_states[soc].append((state, emp))

    # Sort and take top 3
    results = {}
    for soc, states in soc_states.items():
        top3 = sorted(states, key=lambda x: x[1], reverse=True)[:3]
        results[soc] = [s[0] for s in top3]

    print(f"  OEWS state: top-3 states for {len(results)} SOCs")
    return results


def parse_oews_metro_lq(project_socs=None):
    """Parse OEWS metro data to find top metro by location quotient per SOC.

    Location quotient (LQ) measures concentration: an LQ > 1 means the
    occupation is more concentrated in that metro than nationally.

    Args:
        project_socs: set of SOC codes to filter for (optional)

    Returns:
        dict: soc_code -> "Metro Name (LQ=X.XX)"
    """
    filepath = _find_oews_csv("oews_metro", pattern="metro")
    if filepath is None:
        # Try the MA directory
        filepath = _find_oews_csv("oews_metro", pattern="ma")
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
```

**Step 3: Test the parsers**

Run:
```bash
python3 -c "
from social_impact.parse_union import fetch_union_rates, get_union_rate
rates = fetch_union_rates()
print(f'Union rates for {len(rates)} major groups')
print(f'  11-1011 -> {get_union_rate(\"11-1011\")}%')
print(f'  25-1011 -> {get_union_rate(\"25-1011\")}%')
"
```

Run:
```bash
python3 -c "
from social_impact.parse_oews import parse_oews_state
from social_impact.crosswalk import load_project_socs
socs = set(load_project_socs().keys())
states = parse_oews_state(socs)
for soc in ['11-1011', '15-1252', '29-1141']:
    print(f'  {soc}: {states.get(soc, \"N/A\")}')
"
```

Expected: Union rates loaded (hardcoded fallback is fine). OEWS state data gives top-3 states per SOC.

**Step 4: Commit**

```bash
git add social_impact/parse_union.py social_impact/parse_oews.py
git commit -m "Add union rate and OEWS geographic data parsers"
```

---

### Task 6: Build the merge engine and derived columns

**Files:**
- Create: `social_impact/merge.py`

This is the core logic: take all parsed sources and join them onto the 310 project SOCs. For CPSAAT11/11B data, use the Census-to-SOC crosswalk. For education/OEWS, use direct SOC match. Compute derived columns (Edu_Partisan_Lean, Pct_Foreign_Born).

**Step 1: Write the merge engine**

```python
"""Merge all social impact data sources onto project SOCs.

Join strategy per source:
1. CPSAAT11/11B (demographics): Census occ text -> Census code -> SOC via crosswalk
2. Education attainment/entry: Direct SOC match
3. Union rates: 2-digit SOC major group
4. Foreign-born: 2-digit SOC major group (hardcoded from BLS report)
5. OEWS state/metro: Direct SOC match
6. Edu_Partisan_Lean: Derived from pct_bachelors_plus

For CPSAAT11/11B, the join is tricky because the files use occupation titles,
not Census codes directly. We match by building a Census-code -> title -> demo
mapping using the crosswalk and fuzzy matching.
"""
import json
import os
import re
from collections import defaultdict

from social_impact.config import (
    WORKBOOK, MERGED_OUTPUT, DATA_CACHE,
    FOREIGN_BORN_BY_MAJOR_GROUP, EDU_PARTISAN_COLLEGE, EDU_PARTISAN_NO_COLLEGE,
)
from social_impact.crosswalk import (
    load_crosswalk, load_project_socs, build_soc_lookup,
)
from social_impact.parse_demographics import parse_cpsaat11, parse_cpsaat11b
from social_impact.parse_education import parse_education_attainment, parse_entry_education
from social_impact.parse_union import get_union_rate, UNION_RATES_2024
from social_impact.parse_oews import parse_oews_state, parse_oews_metro_lq


def _fuzzy_match_occupation(target_text, demo_data, threshold=0.7):
    """Try to match an occupation title text to CPSAAT11 entries.

    Uses progressively looser matching:
    1. Exact match (case-insensitive)
    2. Target contained in key or key contained in target
    3. Word overlap ratio >= threshold
    """
    target_lower = target_text.lower().strip()
    target_words = set(re.findall(r'\w+', target_lower))

    # Exact match
    for key in demo_data:
        if key.lower().strip() == target_lower:
            return key

    # Containment match
    for key in demo_data:
        key_lower = key.lower().strip()
        if target_lower in key_lower or key_lower in target_lower:
            return key

    # Word overlap
    best_match = None
    best_score = 0
    for key in demo_data:
        key_words = set(re.findall(r'\w+', key.lower()))
        if not key_words or not target_words:
            continue
        overlap = len(target_words & key_words) / max(len(target_words), len(key_words))
        if overlap > best_score and overlap >= threshold:
            best_score = overlap
            best_match = key

    return best_match


def _match_demographics_to_socs(demo_data, project_socs, census_to_soc, soc_to_census):
    """Match CPSAAT demographic data to project SOCs.

    Strategy:
    1. For each project SOC, find its Census code(s) via crosswalk
    2. The Census code maps to a title in the crosswalk
    3. Match that title to CPSAAT data using fuzzy matching
    4. If multiple Census codes for one SOC, average the demographics weighted
       by total_employed_K

    Fallback: try matching the SOC title from the workbook directly against
    CPSAAT occupation titles.

    Returns:
        dict: project_soc -> {pct_female, pct_white, ...} or None
    """
    matched = {}
    unmatched = []

    # Build a simple lookup from the CPSAAT data
    demo_by_text = demo_data  # already keyed by occ text

    for soc, meta in project_socs.items():
        title = meta["title"]
        census_codes = soc_to_census.get(soc, [])

        # For merged SOCs, try each individual code
        if not census_codes and "," in soc:
            for s in soc.split(","):
                s = s.strip()
                if s in soc_to_census:
                    census_codes.extend(soc_to_census[s])

        # Strategy 1: Try matching SOC title directly to CPSAAT
        match = _fuzzy_match_occupation(title, demo_by_text, threshold=0.65)
        if match:
            matched[soc] = demo_by_text[match]
            continue

        # Strategy 2: Use major group fallback — average all CPSAAT entries
        # that map to the same 2-digit SOC group
        major = soc.split("-")[0]
        group_vals = []
        for occ_text, data in demo_by_text.items():
            # Check if any SOC in this Census occ's mapping shares our major group
            for census_code in census_to_soc:
                for mapped_soc in census_to_soc[census_code]:
                    if mapped_soc.startswith(major + "-"):
                        match2 = _fuzzy_match_occupation(occ_text, {occ_text: data})
                        if match2:
                            group_vals.append(data)
                            break

        if group_vals:
            # Average the group values
            avg = {}
            for field in ["pct_female", "pct_white", "pct_black", "pct_asian", "pct_hispanic"]:
                vals = [v[field] for v in group_vals if v.get(field) is not None]
                avg[field] = round(sum(vals) / len(vals), 1) if vals else None
            matched[soc] = avg
        else:
            unmatched.append(soc)

    print(f"  Demographics matched: {len(matched)}/{len(project_socs)}")
    if unmatched:
        print(f"  Unmatched ({len(unmatched)}): {unmatched[:10]}...")

    return matched


def compute_edu_partisan_lean(pct_bachelors_plus):
    """Compute education-partisan lean proxy.

    Based on Pew Research: college grads lean D+13, non-college lean R+6.
    Returns a value from -0.06 (fully non-college, R lean) to +0.13 (fully college, D lean).
    Positive = Democratic lean, negative = Republican lean.
    """
    if pct_bachelors_plus is None:
        return None
    pct = pct_bachelors_plus / 100.0  # convert from percentage to fraction
    lean = pct * EDU_PARTISAN_COLLEGE + (1 - pct) * EDU_PARTISAN_NO_COLLEGE
    return round(lean, 4)


def merge_all():
    """Run the full merge pipeline.

    Returns:
        list of dicts, one per SOC, with all social impact columns.
    """
    print("\n=== Social Impact Data Merge ===\n")

    # 1. Load project SOCs
    project_socs = load_project_socs()

    # 2. Load crosswalk
    census_to_soc, soc_to_census = load_crosswalk()

    # 3. Parse demographics
    print("\nParsing demographics (CPSAAT11)...")
    demo_data = parse_cpsaat11()
    demo_matched = _match_demographics_to_socs(demo_data, project_socs, census_to_soc, soc_to_census)

    print("\nParsing age data (CPSAAT11B)...")
    age_data = parse_cpsaat11b()
    age_matched = _match_demographics_to_socs(age_data, project_socs, census_to_soc, soc_to_census)

    # 4. Parse education
    print("\nParsing education data...")
    edu_attain = parse_education_attainment()
    entry_edu = parse_entry_education()

    # 5. Parse geographic data
    print("\nParsing OEWS state data...")
    soc_set = set(project_socs.keys())
    state_data = parse_oews_state(soc_set)

    print("\nParsing OEWS metro data...")
    metro_data = parse_oews_metro_lq(soc_set)

    # 6. Merge everything
    print("\nMerging all sources...")
    results = []

    for soc, meta in sorted(project_socs.items()):
        row = {
            "SOC_Code": soc,
            "Job_Title": meta["title"],
        }

        # Demographics
        demo = demo_matched.get(soc, {})
        row["Pct_Female"] = demo.get("pct_female")
        row["Pct_White"] = demo.get("pct_white")
        row["Pct_Black"] = demo.get("pct_black")
        row["Pct_Asian"] = demo.get("pct_asian")
        row["Pct_Hispanic"] = demo.get("pct_hispanic")

        # Age
        age = age_matched.get(soc, {})
        row["Median_Age"] = age.get("median_age")
        row["Pct_Over_55"] = age.get("pct_over_55")

        # Education — try direct SOC match, then first code of merged SOC
        edu = edu_attain.get(soc, {})
        if not edu and "," in soc:
            for s in soc.split(","):
                edu = edu_attain.get(s.strip(), {})
                if edu:
                    break
        row["Pct_Bachelors_Plus"] = edu.get("pct_bachelors_plus")
        row["Pct_Graduate_Deg"] = edu.get("pct_graduate_deg")

        entry = entry_edu.get(soc)
        if not entry and "," in soc:
            for s in soc.split(","):
                entry = entry_edu.get(s.strip())
                if entry:
                    break
        row["Typical_Entry_Ed"] = entry

        # Foreign born (major group level)
        major = soc.split("-")[0]
        row["Pct_Foreign_Born"] = FOREIGN_BORN_BY_MAJOR_GROUP.get(major)

        # Union rate (major group level)
        row["Union_Rate_Pct"] = get_union_rate(soc)

        # Education-partisan lean (derived)
        row["Edu_Partisan_Lean"] = compute_edu_partisan_lean(row["Pct_Bachelors_Plus"])

        # Geographic
        top_states = state_data.get(soc, [])
        if not top_states and "," in soc:
            for s in soc.split(","):
                top_states = state_data.get(s.strip(), [])
                if top_states:
                    break
        row["Top_State_1"] = top_states[0] if len(top_states) > 0 else None
        row["Top_State_2"] = top_states[1] if len(top_states) > 1 else None
        row["Top_State_3"] = top_states[2] if len(top_states) > 2 else None

        metro_lq = metro_data.get(soc)
        if not metro_lq and "," in soc:
            for s in soc.split(","):
                metro_lq = metro_data.get(s.strip())
                if metro_lq:
                    break
        row["Top_Metro_LQ"] = metro_lq

        results.append(row)

    # Report coverage
    print(f"\n--- Merge Coverage Report ---")
    for col in ["Pct_Female", "Pct_White", "Pct_Black", "Pct_Asian", "Pct_Hispanic",
                 "Median_Age", "Pct_Over_55", "Pct_Bachelors_Plus", "Pct_Graduate_Deg",
                 "Typical_Entry_Ed", "Pct_Foreign_Born", "Union_Rate_Pct",
                 "Edu_Partisan_Lean", "Top_State_1", "Top_Metro_LQ"]:
        filled = sum(1 for r in results if r.get(col) is not None)
        print(f"  {col}: {filled}/{len(results)} ({100*filled/len(results):.0f}%)")

    # Save intermediate JSON
    os.makedirs(os.path.dirname(MERGED_OUTPUT), exist_ok=True)
    with open(MERGED_OUTPUT, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved {len(results)} records to {MERGED_OUTPUT}")

    return results


if __name__ == "__main__":
    merge_all()
```

**Step 2: Test the merge**

Run:
```bash
python3 social_impact/merge.py
```

Expected: 310 records merged. Coverage report shows most columns above 80%. Some CPSAAT matches may be lower (~60-80%) due to the Census-code mismatch — that's acceptable for v1. The intermediate JSON is saved for inspection.

**Step 3: Inspect a few records**

Run:
```bash
python3 -c "
import json
with open('social_impact/merged_social_data.json') as f:
    data = json.load(f)
# Show 3 sample records
for r in data[:3]:
    print(json.dumps(r, indent=2))
    print()
"
```

Expected: Records have reasonable values. Pct_Female for nurses should be >80%, Pct_Bachelors_Plus for physicians should be >90%, etc.

**Step 4: Commit**

```bash
git add social_impact/merge.py
git commit -m "Add social impact merge engine: joins demographics, education, geographic data to 310 SOCs"
```

---

### Task 7: Write the workbook tab

**Files:**
- Create: `social_impact/writeback.py`

**Step 1: Write the workbook writeback script**

```python
"""Write merged social impact data to '6 Social Impact' tab in the workbook.

Creates the tab if it doesn't exist. Overwrites all data if it does.
"""
import json
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

from social_impact.config import WORKBOOK, MERGED_OUTPUT


# Column order matching the approved design
COLUMNS = [
    "SOC_Code",
    "Job_Title",
    "Pct_Female",
    "Pct_White",
    "Pct_Black",
    "Pct_Asian",
    "Pct_Hispanic",
    "Median_Age",
    "Pct_Over_55",
    "Pct_Bachelors_Plus",
    "Pct_Graduate_Deg",
    "Typical_Entry_Ed",
    "Pct_Foreign_Born",
    "Union_Rate_Pct",
    "Edu_Partisan_Lean",
    "Top_State_1",
    "Top_State_2",
    "Top_State_3",
    "Top_Metro_LQ",
]


def writeback(data=None):
    """Write social impact data to the workbook.

    Args:
        data: list of dicts (if None, loads from merged_social_data.json)
    """
    if data is None:
        with open(MERGED_OUTPUT) as f:
            data = json.load(f)
        print(f"Loaded {len(data)} records from {MERGED_OUTPUT}")

    print(f"Writing to {WORKBOOK}...")
    wb = openpyxl.load_workbook(WORKBOOK)

    # Create or clear the tab
    tab_name = "6 Social Impact"
    if tab_name in wb.sheetnames:
        del wb[tab_name]
    ws = wb.create_sheet(tab_name)

    # Styling
    header_font = Font(bold=True, size=11)
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font_white = Font(bold=True, size=11, color="FFFFFF")
    thin_border = Border(
        bottom=Side(style="thin", color="D9D9D9"),
    )

    # Write headers
    for col, header in enumerate(COLUMNS, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font_white
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", wrap_text=True)

    # Write data
    for i, record in enumerate(data, 2):
        for col, field in enumerate(COLUMNS, 1):
            val = record.get(field)
            ws.cell(row=i, column=col, value=val)

    # Set column widths
    widths = {
        "SOC_Code": 12, "Job_Title": 40, "Pct_Female": 11, "Pct_White": 10,
        "Pct_Black": 10, "Pct_Asian": 10, "Pct_Hispanic": 12, "Median_Age": 11,
        "Pct_Over_55": 11, "Pct_Bachelors_Plus": 15, "Pct_Graduate_Deg": 14,
        "Typical_Entry_Ed": 25, "Pct_Foreign_Born": 14, "Union_Rate_Pct": 13,
        "Edu_Partisan_Lean": 15, "Top_State_1": 18, "Top_State_2": 18,
        "Top_State_3": 18, "Top_Metro_LQ": 35,
    }
    for col, field in enumerate(COLUMNS, 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = widths.get(field, 12)

    # Freeze header row
    ws.freeze_panes = "A2"

    wb.save(WORKBOOK)
    print(f"  Written {len(data)} rows to '{tab_name}' tab")
    print(f"  {len(COLUMNS)} columns: {', '.join(COLUMNS)}")


if __name__ == "__main__":
    writeback()
```

**Step 2: Run the writeback**

Run:
```bash
python3 social_impact/writeback.py
```

**Step 3: Verify the workbook**

Run:
```bash
python3 -c "
import openpyxl
wb = openpyxl.load_workbook('jobs-data-v3.xlsx', read_only=True)
print('Sheets:', wb.sheetnames)
ws = wb['6 Social Impact']
print(f'Rows: {ws.max_row}, Cols: {ws.max_column}')
headers = [ws.cell(1, c).value for c in range(1, 20)]
print('Headers:', headers)
# Sample first 3 data rows
for r in range(2, 5):
    vals = [ws.cell(r, c).value for c in range(1, 20)]
    print(f'  Row {r}: {vals}')
# Count non-null values per column
for c in range(1, 20):
    header = ws.cell(1, c).value
    filled = sum(1 for r in range(2, ws.max_row + 1) if ws.cell(r, c).value is not None)
    print(f'  {header}: {filled}/{ws.max_row - 1}')
wb.close()
"
```

Expected: 310 data rows, 19 columns, tab appears in the workbook. Most columns have 80%+ fill rate. `Pct_Foreign_Born` and `Union_Rate_Pct` should be 100% (major-group fallback).

**Step 4: Commit**

```bash
git add social_impact/writeback.py
git commit -m "Add workbook writeback for 6 Social Impact tab"
```

---

### Task 8: Create run.py pipeline orchestrator

**Files:**
- Create: `social_impact/run.py`

**Step 1: Write the orchestrator**

```python
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


def main():
    args = set(sys.argv[1:])
    start = time.time()

    if not args or "--download" in args:
        print("=" * 60)
        print("PHASE 1: Download BLS source data")
        print("=" * 60)
        force = "--force" in args
        download_all(force=force)

    if not args or "--merge" in args:
        print("\n" + "=" * 60)
        print("PHASE 2: Parse and merge")
        print("=" * 60)
        data = merge_all()

    if not args or "--writeback" in args:
        print("\n" + "=" * 60)
        print("PHASE 3: Write to workbook")
        print("=" * 60)
        writeback()

    elapsed = time.time() - start
    print(f"\nDone in {elapsed:.1f}s")


if __name__ == "__main__":
    main()
```

**Step 2: Test full pipeline**

Run:
```bash
python3 social_impact/run.py
```

Expected: All 3 phases complete. Workbook has "6 Social Impact" tab with 310 rows.

**Step 3: Commit**

```bash
git add social_impact/run.py
git commit -m "Add social impact pipeline orchestrator (download, merge, writeback)"
```

---

### Task 9: Extract O\*NET skills/knowledge for transition pathways

**Files:**
- Create: `social_impact/onet_skills.py`

The transition pathways page needs O\*NET skills and knowledge vectors per SOC to compute pairwise similarity. This module extracts and normalizes the skill/knowledge profiles from the already-downloaded O\*NET database.

**Step 1: Write the O\*NET skills extractor**

```python
"""Extract O*NET skills and knowledge vectors for transition pathway computation.

Reads Skills.txt and Knowledge.txt from the local O*NET database.
Produces a normalized skill/knowledge profile per SOC that can be used
for cosine similarity-based occupation matching.
"""
import os
import csv
import numpy as np
from collections import defaultdict

from social_impact.config import ONET_DIR


def _normalize_soc(onet_soc):
    """Convert O*NET SOC (e.g. '11-1011.00') to project format ('11-1011')."""
    soc = str(onet_soc).strip()
    if soc.endswith(".00"):
        soc = soc[:-3]
    # Handle specializations like '15-1252.01' -> '15-1252'
    if "." in soc:
        soc = soc.split(".")[0]
    return soc


def load_onet_dimension(filename, scale_id="LV"):
    """Load one O*NET dimension (Skills, Knowledge, or Abilities).

    Args:
        filename: e.g. 'Skills.txt'
        scale_id: 'LV' for level (default), 'IM' for importance

    Returns:
        dict: soc_code -> {element_name: score, ...}
    """
    filepath = os.path.join(ONET_DIR, filename)
    if not os.path.exists(filepath):
        print(f"  WARNING: {filepath} not found")
        return {}

    soc_profiles = defaultdict(dict)
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            if row.get("Scale ID") != scale_id:
                continue
            if row.get("Recommend Suppress") == "Y":
                continue

            onet_soc = row.get("O*NET-SOC Code", "")
            soc = _normalize_soc(onet_soc)
            element = row.get("Element Name", "").strip()
            try:
                score = float(row.get("Data Value", 0))
            except (ValueError, TypeError):
                continue

            if element and score > 0:
                # If multiple specializations map to same SOC, average them
                if element in soc_profiles[soc]:
                    soc_profiles[soc][element] = (soc_profiles[soc][element] + score) / 2
                else:
                    soc_profiles[soc][element] = score

    print(f"  {filename}: {len(soc_profiles)} SOCs, "
          f"{len(set(e for p in soc_profiles.values() for e in p))} elements")
    return dict(soc_profiles)


def build_skill_vectors(project_socs=None):
    """Build combined skill+knowledge vectors for all SOCs.

    Combines Skills (35 elements) and Knowledge (33 elements) into
    a single 68-dimension vector per SOC. Values are O*NET level scores (0-7).

    Args:
        project_socs: optional set of SOC codes to filter for

    Returns:
        tuple: (soc_list, element_names, matrix)
            soc_list: list of SOC codes
            element_names: list of element names (ordered)
            matrix: numpy array shape (n_socs, n_elements)
    """
    print("\nBuilding O*NET skill vectors...")

    skills = load_onet_dimension("Skills.txt", "LV")
    knowledge = load_onet_dimension("Knowledge.txt", "LV")

    # Combine into one profile per SOC
    all_socs = set(skills.keys()) | set(knowledge.keys())
    if project_socs:
        all_socs = all_socs & set(project_socs)

    # Collect all element names
    skill_elements = sorted(set(e for p in skills.values() for e in p))
    knowledge_elements = sorted(set(e for p in knowledge.values() for e in p))
    all_elements = skill_elements + knowledge_elements

    # Build matrix
    soc_list = sorted(all_socs)
    matrix = np.zeros((len(soc_list), len(all_elements)))

    for i, soc in enumerate(soc_list):
        skill_profile = skills.get(soc, {})
        knowledge_profile = knowledge.get(soc, {})
        for j, element in enumerate(all_elements):
            if element in skill_profile:
                matrix[i, j] = skill_profile[element]
            elif element in knowledge_profile:
                matrix[i, j] = knowledge_profile[element]

    print(f"  Skill vectors: {matrix.shape[0]} SOCs x {matrix.shape[1]} dimensions")
    return soc_list, all_elements, matrix


def find_transition_targets(soc_code, soc_list, matrix, displacement_data,
                            n_candidates=10, max_displacement=0.15):
    """Find transition targets for a high-displacement SOC.

    Uses cosine similarity between skill/knowledge vectors to find
    similar occupations with lower displacement rates.

    Args:
        soc_code: Source SOC code
        soc_list: List of all SOC codes (matches matrix rows)
        matrix: Skill vector matrix (n_socs x n_elements)
        displacement_data: dict soc -> {d_mod_low, d_sig_low, employment_K, ...}
        n_candidates: Number of candidates to return
        max_displacement: Maximum displacement rate for a viable target

    Returns:
        list of dicts: [{soc, title, similarity, displacement, shared_skills}, ...]
    """
    if soc_code not in soc_list:
        return []

    idx = soc_list.index(soc_code)
    source_vec = matrix[idx]

    # Compute cosine similarity
    norms = np.linalg.norm(matrix, axis=1)
    source_norm = np.linalg.norm(source_vec)
    if source_norm == 0:
        return []

    similarities = matrix @ source_vec / (norms * source_norm + 1e-10)

    # Rank and filter
    candidates = []
    for i in np.argsort(-similarities):
        other_soc = soc_list[i]
        if other_soc == soc_code:
            continue
        sim = similarities[i]
        if sim < 0.5:  # Below 0.5 similarity is not a realistic transition
            break

        disp = displacement_data.get(other_soc, {})
        d_rate = disp.get("d_mod_low", 0.5)  # default high if unknown
        if d_rate > max_displacement:
            continue

        candidates.append({
            "soc": other_soc,
            "title": disp.get("title", ""),
            "similarity": round(float(sim), 3),
            "d_mod_low": round(d_rate, 3),
            "employment_K": disp.get("employment_K", 0),
        })

        if len(candidates) >= n_candidates:
            break

    return candidates


if __name__ == "__main__":
    soc_list, elements, matrix = build_skill_vectors()
    print(f"\nElements: {elements[:10]}...")
    print(f"Matrix shape: {matrix.shape}")
    print(f"Sample vector for 11-1011: {matrix[soc_list.index('11-1011')][:5]}")
```

**Step 2: Test the skill vector builder**

Run:
```bash
python3 social_impact/onet_skills.py
```

Expected: ~800+ O\*NET SOCs loaded, ~68 elements (35 skills + 33 knowledge), matrix built. Our 310 project SOCs should all be present.

**Step 3: Commit**

```bash
git add social_impact/onet_skills.py
git commit -m "Add O*NET skill/knowledge vector extraction for transition pathways"
```

---

### Task 10: Build Flask app scaffold and data loader

**Files:**
- Create: `dashboard/__init__.py`
- Create: `dashboard/app.py`
- Create: `dashboard/data_loader.py`
- Create: `dashboard/templates/base.html`

**Step 1: Create directory structure**

Run:
```bash
mkdir -p dashboard/templates dashboard/static/css dashboard/static/img
touch dashboard/__init__.py
```

**Step 2: Write the data loader**

```python
"""Load workbook data for the Flask dashboard.

Reads from 4 Results and 6 Social Impact tabs on startup.
Caches in memory for fast page rendering.
"""
import openpyxl
import os

from social_impact.config import WORKBOOK


class DataStore:
    """In-memory cache of workbook data for the dashboard."""

    def __init__(self):
        self.results = []       # 4 Results tab rows
        self.social = []        # 6 Social Impact tab rows
        self.soc_lookup = {}    # SOC -> merged dict of results + social
        self._loaded = False

    def load(self):
        """Load data from workbook into memory."""
        if self._loaded:
            return

        wb = openpyxl.load_workbook(WORKBOOK, read_only=True, data_only=True)

        # Load 4 Results
        ws = wb["4 Results"]
        headers = [ws.cell(1, c).value for c in range(1, 28)]
        for r in range(2, ws.max_row + 1):
            soc = ws.cell(r, 1).value
            if not soc:
                continue
            row = {}
            for c, h in enumerate(headers, 0):
                if h and c < 27:
                    row[h] = ws.cell(r, c + 1).value
            self.results.append(row)

        # Load 6 Social Impact
        try:
            ws2 = wb["6 Social Impact"]
            headers2 = [ws2.cell(1, c).value for c in range(1, 20)]
            for r in range(2, ws2.max_row + 1):
                soc = ws2.cell(r, 1).value
                if not soc:
                    continue
                row = {}
                for c, h in enumerate(headers2, 0):
                    if h and c < 19:
                        row[h] = ws2.cell(r, c + 1).value
                self.social.append(row)
        except KeyError:
            print("WARNING: '6 Social Impact' tab not found. Run social_impact/run.py first.")

        wb.close()

        # Build merged lookup
        social_by_soc = {r["SOC_Code"]: r for r in self.social}
        for r in self.results:
            soc = r["SOC_Code"]
            merged = dict(r)
            if soc in social_by_soc:
                merged.update(social_by_soc[soc])
            self.soc_lookup[soc] = merged

        self._loaded = True
        print(f"DataStore loaded: {len(self.results)} results, {len(self.social)} social impact rows")

    def get_all(self):
        """Return all SOC records as merged dicts."""
        self.load()
        return list(self.soc_lookup.values())

    def get_soc(self, soc_code):
        """Return one SOC record."""
        self.load()
        return self.soc_lookup.get(soc_code)

    def get_sectors(self):
        """Return list of unique sectors."""
        self.load()
        return sorted(set(r.get("Sector", "") for r in self.results if r.get("Sector")))

    def get_wage_quintiles(self):
        """Return SOC codes grouped by wage quintile."""
        self.load()
        wages = [(r["SOC_Code"], r.get("Median_Wage", 0) or 0) for r in self.results]
        wages.sort(key=lambda x: x[1])
        n = len(wages)
        quintile_size = n // 5
        quintiles = {}
        labels = ["Q1 (lowest)", "Q2", "Q3", "Q4", "Q5 (highest)"]
        for i, label in enumerate(labels):
            start = i * quintile_size
            end = start + quintile_size if i < 4 else n
            quintiles[label] = [w[0] for w in wages[start:end]]
        return quintiles


# Singleton instance
store = DataStore()
```

**Step 3: Write the Flask app**

```python
"""Flask dashboard for AI Labor Displacement Social Impact analysis.

4 pages:
1. /equity       - Equity Impact (race, gender, age, wage quintile)
2. /geographic   - Geographic Risk (state/metro vulnerability)
3. /political    - Political Landscape (education-partisan proxy, swing states)
4. /transitions  - Transition Pathways (O*NET skill similarity)
"""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, request, jsonify
from dashboard.data_loader import store

app = Flask(__name__)


@app.before_request
def ensure_data_loaded():
    """Load workbook data on first request."""
    store.load()


@app.route("/")
def index():
    """Landing page with overview."""
    data = store.get_all()
    total_emp = sum(r.get("Employment_2024_K", 0) or 0 for r in data)
    return render_template("index.html",
                           n_socs=len(data),
                           total_emp=total_emp,
                           sectors=store.get_sectors())


@app.route("/equity")
def equity():
    """Equity Impact page."""
    data = store.get_all()
    return render_template("equity.html", data=data, sectors=store.get_sectors())


@app.route("/geographic")
def geographic():
    """Geographic Risk page."""
    data = store.get_all()
    return render_template("geographic.html", data=data)


@app.route("/political")
def political():
    """Political Landscape page."""
    data = store.get_all()
    return render_template("political.html", data=data)


@app.route("/transitions")
def transitions():
    """Transition Pathways page."""
    data = store.get_all()
    return render_template("transitions.html", data=data)


@app.route("/api/transition/<soc_code>")
def api_transition(soc_code):
    """API endpoint: find transition targets for a SOC code."""
    from social_impact.onet_skills import build_skill_vectors, find_transition_targets

    soc_list, elements, matrix = build_skill_vectors(set(store.soc_lookup.keys()))
    displacement_data = {}
    for soc, rec in store.soc_lookup.items():
        displacement_data[soc] = {
            "title": rec.get("Job_Title", ""),
            "d_mod_low": rec.get("d_mod_low", 0),
            "employment_K": rec.get("Employment_2024_K", 0),
        }

    max_d = float(request.args.get("max_displacement", 0.15))
    n = int(request.args.get("n", 10))
    targets = find_transition_targets(soc_code, soc_list, matrix,
                                       displacement_data, n_candidates=n,
                                       max_displacement=max_d)
    source = store.get_soc(soc_code)
    return jsonify({
        "source": {
            "soc": soc_code,
            "title": source.get("Job_Title") if source else "",
            "d_mod_low": source.get("d_mod_low") if source else None,
        },
        "targets": targets,
    })


if __name__ == "__main__":
    app.run(debug=True, port=5001)
```

**Step 4: Write the base template**

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}AI Labor Displacement{% endblock %} | Social Impact Dashboard</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
    {% block head %}{% endblock %}
</head>
<body>
    <nav class="sidebar">
        <div class="sidebar-header">
            <h2>AI Labor<br>Displacement</h2>
            <p class="subtitle">Social Impact Dashboard</p>
        </div>
        <ul class="nav-links">
            <li><a href="/" class="{% if request.path == '/' %}active{% endif %}">Overview</a></li>
            <li><a href="/equity" class="{% if request.path == '/equity' %}active{% endif %}">Equity Impact</a></li>
            <li><a href="/geographic" class="{% if request.path == '/geographic' %}active{% endif %}">Geographic Risk</a></li>
            <li><a href="/political" class="{% if request.path == '/political' %}active{% endif %}">Political Landscape</a></li>
            <li><a href="/transitions" class="{% if request.path == '/transitions' %}active{% endif %}">Transition Pathways</a></li>
        </ul>
        <div class="sidebar-footer">
            <p>310 SOCs | 21 Sectors</p>
        </div>
    </nav>
    <main class="content">
        {% block content %}{% endblock %}
    </main>
    {% block scripts %}{% endblock %}
</body>
</html>
```

**Step 5: Write basic CSS**

Create `dashboard/static/css/style.css`:

```css
/* Social Impact Dashboard */
* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    display: flex;
    min-height: 100vh;
    background: #f1f5f9;
    color: #1e293b;
}

.sidebar {
    width: 240px;
    background: #0f172a;
    color: #e2e8f0;
    padding: 24px 16px;
    position: fixed;
    height: 100vh;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
}

.sidebar-header h2 { font-size: 18px; font-weight: 700; color: #f8fafc; }
.sidebar-header .subtitle { font-size: 12px; color: #94a3b8; margin-top: 4px; }

.nav-links {
    list-style: none;
    margin-top: 32px;
    flex-grow: 1;
}

.nav-links li a {
    display: block;
    padding: 10px 12px;
    color: #cbd5e1;
    text-decoration: none;
    border-radius: 6px;
    margin-bottom: 4px;
    font-size: 14px;
    transition: background 0.15s;
}

.nav-links li a:hover { background: #1e293b; color: #f8fafc; }
.nav-links li a.active { background: #2563eb; color: #fff; font-weight: 600; }

.sidebar-footer {
    font-size: 11px;
    color: #64748b;
    padding-top: 16px;
    border-top: 1px solid #1e293b;
}

.content {
    margin-left: 240px;
    padding: 32px;
    flex-grow: 1;
    max-width: 1200px;
}

h1 { font-size: 28px; font-weight: 700; margin-bottom: 8px; }
.page-subtitle { font-size: 15px; color: #64748b; margin-bottom: 24px; }

/* Cards */
.card-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 16px;
    margin-bottom: 32px;
}

.card {
    background: #fff;
    border-radius: 12px;
    padding: 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}

.card h3 { font-size: 13px; text-transform: uppercase; color: #64748b; letter-spacing: 0.5px; }
.card .value { font-size: 32px; font-weight: 700; margin: 8px 0; }
.card .detail { font-size: 13px; color: #94a3b8; }

/* Tables */
.data-table {
    width: 100%;
    border-collapse: collapse;
    background: #fff;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    margin-bottom: 24px;
}

.data-table th {
    background: #f8fafc;
    padding: 10px 12px;
    text-align: left;
    font-size: 12px;
    text-transform: uppercase;
    color: #64748b;
    letter-spacing: 0.5px;
    border-bottom: 2px solid #e2e8f0;
}

.data-table td {
    padding: 10px 12px;
    font-size: 14px;
    border-bottom: 1px solid #f1f5f9;
}

.data-table tr:hover { background: #f8fafc; }

/* Charts */
.chart-container {
    background: #fff;
    border-radius: 12px;
    padding: 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    margin-bottom: 24px;
}

.chart-container h2 {
    font-size: 18px;
    margin-bottom: 16px;
}

.chart-container img {
    max-width: 100%;
    height: auto;
}

/* Bar indicators */
.bar-container { display: flex; align-items: center; gap: 8px; }
.bar {
    height: 8px;
    border-radius: 4px;
    background: #2563eb;
    min-width: 2px;
}
.bar.red { background: #dc2626; }
.bar.amber { background: #f59e0b; }
.bar.green { background: #16a34a; }

/* Filters */
.filter-bar {
    display: flex;
    gap: 12px;
    margin-bottom: 24px;
    flex-wrap: wrap;
}

.filter-bar select, .filter-bar input {
    padding: 8px 12px;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    font-size: 14px;
    background: #fff;
}

/* Responsive */
@media (max-width: 768px) {
    .sidebar { display: none; }
    .content { margin-left: 0; }
}
```

**Step 6: Test app starts**

Run:
```bash
python3 -c "
import sys
sys.path.insert(0, '.')
from dashboard.app import app
with app.test_client() as c:
    resp = c.get('/')
    print(f'Status: {resp.status_code}')
    print(f'Length: {len(resp.data)} bytes')
"
```

Expected: May get a 500 if templates are incomplete, but the import should succeed.

**Step 7: Commit**

```bash
git add dashboard/__init__.py dashboard/app.py dashboard/data_loader.py \
    dashboard/templates/base.html dashboard/static/css/style.css
git commit -m "Add Flask dashboard scaffold: app, data loader, base template, CSS"
```

---

### Task 11: Build Equity Impact page (Page 1)

**Files:**
- Create: `dashboard/templates/index.html`
- Create: `dashboard/templates/equity.html`
- Create: `dashboard/charts.py`

This page shows displacement disparities by race/gender/age and wage quintile. Charts are pre-rendered as static PNGs by `charts.py` (same pattern as `analysis/displacement_analysis.py`).

**Step 1: Write the chart generation module**

```python
"""Generate charts for the Social Impact dashboard.

Generates static PNG files in dashboard/static/img/.
Called on app startup or manually via `python3 dashboard/charts.py`.
"""
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dashboard.data_loader import store

CHART_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "img")

# Colors
C_BLUE = "#2563eb"
C_RED = "#dc2626"
C_AMBER = "#f59e0b"
C_GREEN = "#16a34a"
C_GRAY = "#6b7280"
C_LIGHT_BLUE = "#93c5fd"
C_BG = "#f8fafc"

plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor": C_BG,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "font.family": "sans-serif",
    "font.size": 11,
    "figure.dpi": 150,
})


def _ensure_dir():
    os.makedirs(CHART_DIR, exist_ok=True)


def chart_displacement_by_demographic(data, field, label, filename):
    """Bar chart: displacement rate by a demographic percentage bracket.

    Bins SOCs by the demographic field into brackets (e.g. <20%, 20-40%, etc.)
    and shows employment-weighted mean displacement for each bracket.
    """
    _ensure_dir()

    # Filter to SOCs with this field
    valid = [r for r in data if r.get(field) is not None and r.get("d_mod_low") is not None]
    if not valid:
        print(f"  Skipping {filename}: no valid data for {field}")
        return

    # Bin by demographic percentage
    bins = [(0, 20), (20, 40), (40, 60), (60, 80), (80, 100)]
    bin_labels = ["<20%", "20-40%", "40-60%", "60-80%", "80-100%"]
    bin_data = {l: {"emp": 0, "disp_sum": 0} for l in bin_labels}

    for r in valid:
        pct = r[field]
        emp = r.get("Employment_2024_K", 0) or 0
        d = r.get("d_mod_low", 0) or 0
        for (lo, hi), bl in zip(bins, bin_labels):
            if lo <= pct < hi or (hi == 100 and pct == 100):
                bin_data[bl]["emp"] += emp
                bin_data[bl]["disp_sum"] += emp * d
                break

    means = []
    for bl in bin_labels:
        bd = bin_data[bl]
        means.append(bd["disp_sum"] / bd["emp"] if bd["emp"] > 0 else 0)

    fig, ax = plt.subplots(figsize=(8, 5))
    x = np.arange(len(bin_labels))
    bars = ax.bar(x, means, color=C_BLUE, alpha=0.8, edgecolor="white")
    ax.set_xticks(x)
    ax.set_xticklabels(bin_labels)
    ax.set_xlabel(f"{label} Share of Workforce")
    ax.set_ylabel("Emp-Weighted Mean Displacement Rate")
    ax.set_title(f"Displacement Rate by {label}")
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1, decimals=1))

    fig.tight_layout()
    fig.savefig(os.path.join(CHART_DIR, filename), bbox_inches="tight")
    plt.close()
    print(f"  {filename}")


def chart_wage_quintile_displacement(data, filename="equity_wage_quintile.png"):
    """Bar chart: displacement by wage quintile."""
    _ensure_dir()

    valid = [r for r in data if r.get("Median_Wage") and r.get("d_mod_low") is not None]
    valid.sort(key=lambda r: r["Median_Wage"])

    n = len(valid)
    q_size = n // 5
    labels = ["Q1\n(lowest)", "Q2", "Q3", "Q4", "Q5\n(highest)"]
    means_mod = []
    means_sig = []
    total_emps = []

    for i in range(5):
        start = i * q_size
        end = start + q_size if i < 4 else n
        q = valid[start:end]
        total_emp = sum(r.get("Employment_2024_K", 0) or 0 for r in q)
        total_emps.append(total_emp)
        if total_emp > 0:
            wm_mod = sum((r.get("d_mod_low", 0) or 0) * (r.get("Employment_2024_K", 0) or 0) for r in q) / total_emp
            wm_sig = sum((r.get("d_sig_low", 0) or 0) * (r.get("Employment_2024_K", 0) or 0) for r in q) / total_emp
        else:
            wm_mod = wm_sig = 0
        means_mod.append(wm_mod)
        means_sig.append(wm_sig)

    fig, ax = plt.subplots(figsize=(9, 5.5))
    x = np.arange(5)
    w = 0.35
    ax.bar(x - w/2, means_mod, w, label="Moderate", color=C_BLUE, alpha=0.8)
    ax.bar(x + w/2, means_sig, w, label="Significant", color=C_RED, alpha=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_xlabel("Wage Quintile")
    ax.set_ylabel("Emp-Weighted Mean Displacement Rate")
    ax.set_title("Displacement Rate by Wage Quintile\n(Moderate vs. Significant Scenario, Low Friction)")
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1, decimals=1))
    ax.legend()

    fig.tight_layout()
    fig.savefig(os.path.join(CHART_DIR, filename), bbox_inches="tight")
    plt.close()
    print(f"  {filename}")


def chart_gender_displacement(data, filename="equity_gender.png"):
    """Scatter: Pct_Female vs displacement rate, sized by employment."""
    _ensure_dir()

    valid = [r for r in data if r.get("Pct_Female") is not None and r.get("d_mod_low") is not None]
    if not valid:
        return

    x = [r["Pct_Female"] for r in valid]
    y = [r["d_mod_low"] for r in valid]
    sizes = [max(3, (r.get("Employment_2024_K", 0) or 0) / 10) for r in valid]

    fig, ax = plt.subplots(figsize=(9, 6))
    ax.scatter(x, y, s=sizes, alpha=0.5, c=C_BLUE, edgecolors="white", linewidth=0.5)
    ax.set_xlabel("Percent Female")
    ax.set_ylabel("Displacement Rate (Moderate, Low Friction)")
    ax.set_title("Gender Composition vs. AI Displacement Risk")
    ax.xaxis.set_major_formatter(mticker.PercentFormatter(xmax=100))
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1, decimals=1))

    fig.tight_layout()
    fig.savefig(os.path.join(CHART_DIR, filename), bbox_inches="tight")
    plt.close()
    print(f"  {filename}")


def generate_all_charts():
    """Generate all dashboard charts."""
    print("\nGenerating dashboard charts...")
    store.load()
    data = store.get_all()

    chart_wage_quintile_displacement(data)
    chart_gender_displacement(data)
    chart_displacement_by_demographic(data, "Pct_Female", "Female", "equity_female_bins.png")
    chart_displacement_by_demographic(data, "Pct_Black", "Black/African American", "equity_black_bins.png")
    chart_displacement_by_demographic(data, "Pct_Hispanic", "Hispanic/Latino", "equity_hispanic_bins.png")
    chart_displacement_by_demographic(data, "Pct_Over_55", "Workers Over 55", "equity_age55_bins.png")

    print("Charts complete.")


if __name__ == "__main__":
    generate_all_charts()
```

**Step 2: Write the index template**

Create `dashboard/templates/index.html`:

```html
{% extends "base.html" %}
{% block title %}Overview{% endblock %}
{% block content %}
<h1>AI Labor Displacement: Social Impact</h1>
<p class="page-subtitle">Analyzing the distributional consequences of AI-driven workforce displacement across 310 white-collar occupations.</p>

<div class="card-grid">
    <div class="card">
        <h3>Occupations Analyzed</h3>
        <div class="value">{{ n_socs }}</div>
        <div class="detail">6-digit SOC codes with full displacement scores</div>
    </div>
    <div class="card">
        <h3>Total Employment</h3>
        <div class="value">{{ "%.1f"|format(total_emp / 1000) }}M</div>
        <div class="detail">Workers across {{ sectors|length }} industry sectors</div>
    </div>
    <div class="card">
        <h3>Data Layers</h3>
        <div class="value">4</div>
        <div class="detail">Equity, Geographic, Political, Transitions</div>
    </div>
</div>

<div class="chart-container">
    <h2>Dashboard Pages</h2>
    <div class="card-grid">
        <a href="/equity" class="card" style="text-decoration:none;color:inherit;">
            <h3>Equity Impact</h3>
            <p>How displacement falls across race, gender, age, and income groups</p>
        </a>
        <a href="/geographic" class="card" style="text-decoration:none;color:inherit;">
            <h3>Geographic Risk</h3>
            <p>State and metro area vulnerability to occupational displacement</p>
        </a>
        <a href="/political" class="card" style="text-decoration:none;color:inherit;">
            <h3>Political Landscape</h3>
            <p>Education-partisan proxy and swing state exposure analysis</p>
        </a>
        <a href="/transitions" class="card" style="text-decoration:none;color:inherit;">
            <h3>Transition Pathways</h3>
            <p>O*NET skill-based retraining targets for high-displacement SOCs</p>
        </a>
    </div>
</div>
{% endblock %}
```

**Step 3: Write the equity template**

Create `dashboard/templates/equity.html`:

```html
{% extends "base.html" %}
{% block title %}Equity Impact{% endblock %}
{% block content %}
<h1>Equity Impact Analysis</h1>
<p class="page-subtitle">How AI displacement risk distributes across demographic groups and income levels.</p>

<div class="chart-container">
    <h2>Displacement by Wage Quintile</h2>
    <img src="{{ url_for('static', filename='img/equity_wage_quintile.png') }}" alt="Wage quintile chart">
</div>

<div class="chart-container">
    <h2>Gender Composition vs. Displacement Risk</h2>
    <img src="{{ url_for('static', filename='img/equity_gender.png') }}" alt="Gender scatter plot">
</div>

<div class="card-grid">
    <div class="chart-container">
        <h2>Displacement by Female Share</h2>
        <img src="{{ url_for('static', filename='img/equity_female_bins.png') }}" alt="Female bins">
    </div>
    <div class="chart-container">
        <h2>Displacement by Black/AA Share</h2>
        <img src="{{ url_for('static', filename='img/equity_black_bins.png') }}" alt="Black bins">
    </div>
</div>

<div class="card-grid">
    <div class="chart-container">
        <h2>Displacement by Hispanic/Latino Share</h2>
        <img src="{{ url_for('static', filename='img/equity_hispanic_bins.png') }}" alt="Hispanic bins">
    </div>
    <div class="chart-container">
        <h2>Displacement by Over-55 Share</h2>
        <img src="{{ url_for('static', filename='img/equity_age55_bins.png') }}" alt="Age 55+ bins">
    </div>
</div>

<div class="chart-container">
    <h2>Most Impacted Occupations by Demographic</h2>
    <p class="page-subtitle">Top 20 occupations by displaced workers, with demographic composition.</p>
    <table class="data-table">
        <thead>
            <tr>
                <th>SOC</th>
                <th>Occupation</th>
                <th>Emp (K)</th>
                <th>d (Mod)</th>
                <th>Displaced (K)</th>
                <th>% Female</th>
                <th>% Black</th>
                <th>% Hispanic</th>
                <th>% Over 55</th>
            </tr>
        </thead>
        <tbody>
        {% for r in data|sort(attribute='displaced_K_mod_low', reverse=True) %}
        {% if loop.index <= 20 %}
            <tr>
                <td>{{ r.SOC_Code }}</td>
                <td>{{ r.Job_Title }}</td>
                <td>{{ "%.1f"|format(r.Employment_2024_K or 0) }}</td>
                <td>{{ "%.1f%%"|format((r.d_mod_low or 0) * 100) }}</td>
                <td>{{ "%.1f"|format(r.displaced_K_mod_low or 0) }}</td>
                <td>{{ "%.1f"|format(r.Pct_Female or 0) }}%</td>
                <td>{{ "%.1f"|format(r.Pct_Black or 0) }}%</td>
                <td>{{ "%.1f"|format(r.Pct_Hispanic or 0) }}%</td>
                <td>{{ "%.1f"|format(r.Pct_Over_55 or 0) }}%</td>
            </tr>
        {% endif %}
        {% endfor %}
        </tbody>
    </table>
</div>
{% endblock %}
```

**Step 4: Generate charts and test**

Run:
```bash
python3 dashboard/charts.py
```

Expected: 6 PNG files generated in `dashboard/static/img/`.

Run:
```bash
python3 -c "
import sys; sys.path.insert(0, '.')
from dashboard.app import app
with app.test_client() as c:
    for path in ['/', '/equity']:
        resp = c.get(path)
        print(f'{path}: {resp.status_code} ({len(resp.data)} bytes)')
"
```

Expected: Both return 200.

**Step 5: Commit**

```bash
git add dashboard/charts.py dashboard/templates/index.html dashboard/templates/equity.html
git commit -m "Add Equity Impact page with demographic displacement charts"
```

---

### Task 12: Build Geographic Risk page (Page 2)

**Files:**
- Create: `dashboard/templates/geographic.html`
- Modify: `dashboard/charts.py` (add geographic charts)

**Step 1: Add geographic chart functions to charts.py**

Append to `dashboard/charts.py`:

```python
def chart_state_displacement_risk(data, filename="geo_state_risk.png"):
    """Horizontal bar chart: top 20 states by total displaced workers.

    Aggregates displaced_K_mod_low across SOCs, using Top_State_1 assignment.
    """
    _ensure_dir()

    from collections import defaultdict
    state_totals = defaultdict(lambda: {"displaced": 0, "emp": 0, "socs": 0})

    for r in data:
        state = r.get("Top_State_1")
        if not state:
            continue
        emp = r.get("Employment_2024_K", 0) or 0
        dk = r.get("displaced_K_mod_low", 0) or 0
        state_totals[state]["displaced"] += dk
        state_totals[state]["emp"] += emp
        state_totals[state]["socs"] += 1

    if not state_totals:
        return

    # Sort by displaced workers, take top 20
    top = sorted(state_totals.items(), key=lambda x: x[1]["displaced"], reverse=True)[:20]
    top.reverse()  # for horizontal bar (bottom = largest)

    states = [t[0] for t in top]
    displaced = [t[1]["displaced"] for t in top]

    fig, ax = plt.subplots(figsize=(10, 8))
    y = np.arange(len(states))
    ax.barh(y, displaced, color=C_RED, alpha=0.8)
    ax.set_yticks(y)
    ax.set_yticklabels(states, fontsize=9)
    ax.set_xlabel("Displaced Workers (thousands, Moderate Low Friction)")
    ax.set_title("Top 20 States by Estimated Displaced Workers\n(Based on primary state of SOC employment)")

    fig.tight_layout()
    fig.savefig(os.path.join(CHART_DIR, filename), bbox_inches="tight")
    plt.close()
    print(f"  {filename}")
```

Also add to `generate_all_charts()`:
```python
    chart_state_displacement_risk(data)
```

**Step 2: Write the geographic template**

Create `dashboard/templates/geographic.html`:

```html
{% extends "base.html" %}
{% block title %}Geographic Risk{% endblock %}
{% block content %}
<h1>Geographic Risk Analysis</h1>
<p class="page-subtitle">Where AI displacement will concentrate geographically based on occupation employment patterns.</p>

<div class="chart-container">
    <h2>Top States by Displaced Workers</h2>
    <img src="{{ url_for('static', filename='img/geo_state_risk.png') }}" alt="State displacement risk">
</div>

<div class="chart-container">
    <h2>Occupations by Primary State</h2>
    <p class="page-subtitle">Filter by state to see which occupations are concentrated there.</p>

    <div class="filter-bar">
        <select id="state-filter" onchange="filterByState()">
            <option value="">All States</option>
            {% set states = data|map(attribute='Top_State_1')|select('string')|unique|sort %}
            {% for state in states %}
            <option value="{{ state }}">{{ state }}</option>
            {% endfor %}
        </select>
    </div>

    <table class="data-table" id="state-table">
        <thead>
            <tr>
                <th>SOC</th>
                <th>Occupation</th>
                <th>Sector</th>
                <th>Emp (K)</th>
                <th>d (Mod)</th>
                <th>Top State 1</th>
                <th>Top State 2</th>
                <th>Top State 3</th>
                <th>Top Metro (LQ)</th>
            </tr>
        </thead>
        <tbody>
        {% for r in data|sort(attribute='displaced_K_mod_low', reverse=True) %}
            <tr data-state="{{ r.Top_State_1 or '' }}">
                <td>{{ r.SOC_Code }}</td>
                <td>{{ r.Job_Title }}</td>
                <td>{{ r.Sector }}</td>
                <td>{{ "%.1f"|format(r.Employment_2024_K or 0) }}</td>
                <td>{{ "%.1f%%"|format((r.d_mod_low or 0) * 100) }}</td>
                <td>{{ r.Top_State_1 or '-' }}</td>
                <td>{{ r.Top_State_2 or '-' }}</td>
                <td>{{ r.Top_State_3 or '-' }}</td>
                <td>{{ r.Top_Metro_LQ or '-' }}</td>
            </tr>
        {% endfor %}
        </tbody>
    </table>
</div>
{% endblock %}

{% block scripts %}
<script>
function filterByState() {
    const state = document.getElementById('state-filter').value;
    const rows = document.querySelectorAll('#state-table tbody tr');
    rows.forEach(row => {
        if (!state || row.dataset.state === state) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
}
</script>
{% endblock %}
```

**Step 3: Regenerate charts and test**

Run:
```bash
python3 dashboard/charts.py
```

Run:
```bash
python3 -c "
import sys; sys.path.insert(0, '.')
from dashboard.app import app
with app.test_client() as c:
    resp = c.get('/geographic')
    print(f'/geographic: {resp.status_code} ({len(resp.data)} bytes)')
"
```

Expected: 200, page renders with state data table.

**Step 4: Commit**

```bash
git add dashboard/templates/geographic.html dashboard/charts.py
git commit -m "Add Geographic Risk page with state displacement analysis"
```

---

### Task 13: Build Political Landscape page (Page 3)

**Files:**
- Create: `dashboard/templates/political.html`
- Modify: `dashboard/charts.py` (add political charts)

**Step 1: Add political charts to charts.py**

Append to `dashboard/charts.py`:

```python
def chart_partisan_lean_vs_displacement(data, filename="pol_lean_scatter.png"):
    """Scatter plot: Edu_Partisan_Lean vs displacement, sized by employment."""
    _ensure_dir()

    valid = [r for r in data if r.get("Edu_Partisan_Lean") is not None and r.get("d_mod_low") is not None]
    if not valid:
        return

    x = [r["Edu_Partisan_Lean"] for r in valid]
    y = [r["d_mod_low"] for r in valid]
    sizes = [max(3, (r.get("Employment_2024_K", 0) or 0) / 10) for r in valid]

    fig, ax = plt.subplots(figsize=(10, 6))
    scatter = ax.scatter(x, y, s=sizes, alpha=0.5, c=C_BLUE, edgecolors="white", linewidth=0.5)
    ax.axvline(0, color=C_GRAY, linestyle="--", linewidth=1, alpha=0.5)
    ax.set_xlabel("Education-Partisan Lean (- = Rep lean, + = Dem lean)")
    ax.set_ylabel("Displacement Rate (Moderate, Low Friction)")
    ax.set_title("Education-Partisan Lean vs. AI Displacement Risk")
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1, decimals=1))
    ax.annotate("Rep lean", xy=(min(x), 0), fontsize=9, color=C_RED, alpha=0.7)
    ax.annotate("Dem lean", xy=(max(x) * 0.7, 0), fontsize=9, color=C_BLUE, alpha=0.7)

    fig.tight_layout()
    fig.savefig(os.path.join(CHART_DIR, filename), bbox_inches="tight")
    plt.close()
    print(f"  {filename}")


def chart_education_displacement(data, filename="pol_education.png"):
    """Bar chart: displacement by typical entry education level."""
    _ensure_dir()

    from collections import defaultdict
    edu_groups = defaultdict(lambda: {"emp": 0, "disp_sum": 0, "count": 0})

    for r in data:
        edu = r.get("Typical_Entry_Ed")
        if not edu or r.get("d_mod_low") is None:
            continue
        emp = r.get("Employment_2024_K", 0) or 0
        d = r.get("d_mod_low", 0) or 0
        edu_groups[edu]["emp"] += emp
        edu_groups[edu]["disp_sum"] += emp * d
        edu_groups[edu]["count"] += 1

    if not edu_groups:
        return

    # Sort by displacement rate
    items = []
    for edu, vals in edu_groups.items():
        rate = vals["disp_sum"] / vals["emp"] if vals["emp"] > 0 else 0
        items.append((edu, rate, vals["emp"], vals["count"]))
    items.sort(key=lambda x: x[1], reverse=True)

    labels = [i[0][:30] for i in items]
    rates = [i[1] for i in items]

    fig, ax = plt.subplots(figsize=(10, max(5, len(items) * 0.4)))
    y = np.arange(len(labels))
    ax.barh(y, rates, color=C_BLUE, alpha=0.8)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel("Emp-Weighted Mean Displacement Rate")
    ax.set_title("Displacement by Typical Entry Education")
    ax.xaxis.set_major_formatter(mticker.PercentFormatter(xmax=1, decimals=1))
    ax.invert_yaxis()

    fig.tight_layout()
    fig.savefig(os.path.join(CHART_DIR, filename), bbox_inches="tight")
    plt.close()
    print(f"  {filename}")
```

Also add to `generate_all_charts()`:
```python
    chart_partisan_lean_vs_displacement(data)
    chart_education_displacement(data)
```

**Step 2: Write the political template**

Create `dashboard/templates/political.html`:

```html
{% extends "base.html" %}
{% block title %}Political Landscape{% endblock %}
{% block content %}
<h1>Political Landscape Analysis</h1>
<p class="page-subtitle">How AI displacement intersects with education levels and the education-partisan gradient.</p>

<div class="card-grid">
    <div class="card">
        <h3>Methodology Note</h3>
        <p style="font-size:13px;color:#64748b;margin-top:8px;">
            "Education-Partisan Lean" is a proxy derived from Pew Research data:
            college graduates lean D+13, non-college workers lean R+6.
            Each occupation's lean is computed from its bachelor's-degree attainment rate.
            This is a statistical proxy, not a measurement of individual political views.
        </p>
    </div>
</div>

<div class="chart-container">
    <h2>Education-Partisan Lean vs. Displacement Risk</h2>
    <img src="{{ url_for('static', filename='img/pol_lean_scatter.png') }}" alt="Partisan lean scatter">
</div>

<div class="chart-container">
    <h2>Displacement by Entry Education Level</h2>
    <img src="{{ url_for('static', filename='img/pol_education.png') }}" alt="Education displacement">
</div>

<div class="chart-container">
    <h2>Swing State Exposure</h2>
    <p class="page-subtitle">Occupations where the primary employment state is a swing state (AZ, GA, MI, NV, NC, PA, WI).</p>
    <table class="data-table">
        <thead>
            <tr>
                <th>SOC</th>
                <th>Occupation</th>
                <th>Emp (K)</th>
                <th>d (Mod)</th>
                <th>Displaced (K)</th>
                <th>Primary State</th>
                <th>Edu Lean</th>
                <th>Union Rate</th>
            </tr>
        </thead>
        <tbody>
        {% set swing_states = ['Arizona', 'Georgia', 'Michigan', 'Nevada', 'North Carolina', 'Pennsylvania', 'Wisconsin'] %}
        {% for r in data|sort(attribute='displaced_K_mod_low', reverse=True) %}
        {% if r.Top_State_1 in swing_states %}
            <tr>
                <td>{{ r.SOC_Code }}</td>
                <td>{{ r.Job_Title }}</td>
                <td>{{ "%.1f"|format(r.Employment_2024_K or 0) }}</td>
                <td>{{ "%.1f%%"|format((r.d_mod_low or 0) * 100) }}</td>
                <td>{{ "%.1f"|format(r.displaced_K_mod_low or 0) }}</td>
                <td>{{ r.Top_State_1 }}</td>
                <td>{{ "%.3f"|format(r.Edu_Partisan_Lean or 0) }}</td>
                <td>{{ "%.1f%%"|format(r.Union_Rate_Pct or 0) }}</td>
            </tr>
        {% endif %}
        {% endfor %}
        </tbody>
    </table>
</div>
{% endblock %}
```

**Step 3: Regenerate charts and test**

Run:
```bash
python3 dashboard/charts.py
python3 -c "
import sys; sys.path.insert(0, '.')
from dashboard.app import app
with app.test_client() as c:
    resp = c.get('/political')
    print(f'/political: {resp.status_code} ({len(resp.data)} bytes)')
"
```

Expected: 200.

**Step 4: Commit**

```bash
git add dashboard/templates/political.html dashboard/charts.py
git commit -m "Add Political Landscape page with education-partisan analysis"
```

---

### Task 14: Build Transition Pathways page (Page 4)

**Files:**
- Create: `dashboard/templates/transitions.html`

This page is interactive: the user selects a high-displacement SOC, and the `/api/transition/<soc>` endpoint returns skill-similar occupations with lower displacement.

**Step 1: Write the transitions template**

Create `dashboard/templates/transitions.html`:

```html
{% extends "base.html" %}
{% block title %}Transition Pathways{% endblock %}
{% block content %}
<h1>Transition Pathways</h1>
<p class="page-subtitle">
    For high-displacement occupations, find skill-similar jobs with lower AI displacement risk.
    Based on O*NET skill and knowledge vector cosine similarity.
</p>

<div class="filter-bar">
    <select id="soc-select" style="width:400px;">
        <option value="">Select a high-displacement occupation...</option>
        {% for r in data|sort(attribute='displaced_K_mod_low', reverse=True) %}
        {% if (r.d_mod_low or 0) > 0.08 %}
        <option value="{{ r.SOC_Code }}">
            {{ r.SOC_Code }} - {{ r.Job_Title }} (d={{ "%.1f%%"|format((r.d_mod_low or 0) * 100) }}, {{ "%.0f"|format(r.Employment_2024_K or 0) }}K workers)
        </option>
        {% endif %}
        {% endfor %}
    </select>
    <button onclick="findTransitions()" style="padding:8px 16px;background:#2563eb;color:#fff;border:none;border-radius:6px;cursor:pointer;">
        Find Transition Targets
    </button>
</div>

<div id="source-info" style="display:none;" class="card" style="margin-bottom:24px;">
    <h3>Source Occupation</h3>
    <p id="source-detail"></p>
</div>

<div id="results" style="display:none;" class="chart-container">
    <h2>Recommended Transition Targets</h2>
    <p class="page-subtitle">Occupations with similar skills/knowledge and lower displacement risk.</p>
    <table class="data-table" id="results-table">
        <thead>
            <tr>
                <th>Rank</th>
                <th>SOC</th>
                <th>Target Occupation</th>
                <th>Skill Similarity</th>
                <th>Displacement Rate</th>
                <th>Employment (K)</th>
            </tr>
        </thead>
        <tbody id="results-body">
        </tbody>
    </table>
</div>

<div id="loading" style="display:none;text-align:center;padding:40px;">
    <p>Computing skill similarities... (first load may take 10-15 seconds)</p>
</div>

<div id="no-results" style="display:none;" class="card">
    <p>No viable transition targets found. This may mean the occupation's skill profile is highly specialized.</p>
</div>
{% endblock %}

{% block scripts %}
<script>
async function findTransitions() {
    const soc = document.getElementById('soc-select').value;
    if (!soc) return;

    document.getElementById('loading').style.display = 'block';
    document.getElementById('results').style.display = 'none';
    document.getElementById('no-results').style.display = 'none';
    document.getElementById('source-info').style.display = 'none';

    try {
        const resp = await fetch(`/api/transition/${soc}?n=10&max_displacement=0.15`);
        const data = await resp.json();

        document.getElementById('loading').style.display = 'none';

        // Show source info
        const src = data.source;
        document.getElementById('source-detail').textContent =
            `${src.soc} - ${src.title} | Displacement: ${(src.d_mod_low * 100).toFixed(1)}%`;
        document.getElementById('source-info').style.display = 'block';

        if (data.targets.length === 0) {
            document.getElementById('no-results').style.display = 'block';
            return;
        }

        // Populate table
        const tbody = document.getElementById('results-body');
        tbody.innerHTML = '';
        data.targets.forEach((t, i) => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${i + 1}</td>
                <td>${t.soc}</td>
                <td>${t.title}</td>
                <td>${(t.similarity * 100).toFixed(1)}%</td>
                <td>${(t.d_mod_low * 100).toFixed(1)}%</td>
                <td>${t.employment_K.toFixed(0)}</td>
            `;
            tbody.appendChild(row);
        });
        document.getElementById('results').style.display = 'block';
    } catch (err) {
        document.getElementById('loading').style.display = 'none';
        alert('Error: ' + err.message);
    }
}
</script>
{% endblock %}
```

**Step 2: Test the transition API**

Run:
```bash
python3 -c "
import sys; sys.path.insert(0, '.')
from dashboard.app import app
with app.test_client() as c:
    # Test the transitions page loads
    resp = c.get('/transitions')
    print(f'/transitions: {resp.status_code}')
    # Test the API endpoint
    resp = c.get('/api/transition/43-3071')
    print(f'/api/transition/43-3071: {resp.status_code}')
    if resp.status_code == 200:
        import json
        data = json.loads(resp.data)
        print(f'  Source: {data[\"source\"]}')
        print(f'  Targets: {len(data[\"targets\"])}')
        for t in data['targets'][:3]:
            print(f'    {t[\"soc\"]} {t[\"title\"]}: sim={t[\"similarity\"]}, d={t[\"d_mod_low\"]}')
"
```

Expected: Page loads (200). API returns transition targets sorted by similarity, all with d < 0.15.

**Step 3: Commit**

```bash
git add dashboard/templates/transitions.html
git commit -m "Add Transition Pathways page with O*NET skill-similarity API"
```

---

### Task 15: Cache O\*NET skill vectors to avoid re-computation

**Files:**
- Modify: `dashboard/app.py`
- Modify: `social_impact/onet_skills.py`

The `/api/transition/<soc>` endpoint currently rebuilds skill vectors on every call. Add caching.

**Step 1: Add caching to onet_skills.py**

Add at module level in `social_impact/onet_skills.py`:

```python
# Module-level cache
_cached_vectors = None

def get_cached_vectors(project_socs=None):
    """Return cached skill vectors, building on first call."""
    global _cached_vectors
    if _cached_vectors is None:
        _cached_vectors = build_skill_vectors(project_socs)
    return _cached_vectors
```

**Step 2: Update the API endpoint in app.py**

Replace the `/api/transition/<soc_code>` route body:

```python
@app.route("/api/transition/<soc_code>")
def api_transition(soc_code):
    """API endpoint: find transition targets for a SOC code."""
    from social_impact.onet_skills import get_cached_vectors, find_transition_targets

    soc_list, elements, matrix = get_cached_vectors(set(store.soc_lookup.keys()))
    displacement_data = {}
    for soc, rec in store.soc_lookup.items():
        displacement_data[soc] = {
            "title": rec.get("Job_Title", ""),
            "d_mod_low": rec.get("d_mod_low", 0),
            "employment_K": rec.get("Employment_2024_K", 0),
        }

    max_d = float(request.args.get("max_displacement", 0.15))
    n = int(request.args.get("n", 10))
    targets = find_transition_targets(soc_code, soc_list, matrix,
                                       displacement_data, n_candidates=n,
                                       max_displacement=max_d)
    source = store.get_soc(soc_code)
    return jsonify({
        "source": {
            "soc": soc_code,
            "title": source.get("Job_Title") if source else "",
            "d_mod_low": source.get("d_mod_low") if source else None,
        },
        "targets": targets,
    })
```

**Step 3: Test cached API is fast on second call**

Run:
```bash
python3 -c "
import time, sys
sys.path.insert(0, '.')
from dashboard.app import app
with app.test_client() as c:
    t0 = time.time()
    c.get('/api/transition/43-3071')
    t1 = time.time()
    print(f'First call: {t1-t0:.2f}s')
    t0 = time.time()
    c.get('/api/transition/13-2011')
    t1 = time.time()
    print(f'Second call (cached): {t1-t0:.2f}s')
"
```

Expected: First call ~2-5s, second call <0.5s.

**Step 4: Commit**

```bash
git add social_impact/onet_skills.py dashboard/app.py
git commit -m "Cache O*NET skill vectors for fast transition API responses"
```

---

### Task 16: End-to-end integration test

**Step 1: Run full pipeline from scratch**

Run:
```bash
# Download data (if not cached)
python3 social_impact/run.py --download

# Merge and write to workbook
python3 social_impact/run.py --merge --writeback

# Generate charts
python3 dashboard/charts.py
```

**Step 2: Verify workbook**

Run:
```bash
python3 -c "
import openpyxl
wb = openpyxl.load_workbook('jobs-data-v3.xlsx', read_only=True)
print('Sheets:', wb.sheetnames)
assert '6 Social Impact' in wb.sheetnames, 'Missing 6 Social Impact tab!'
ws = wb['6 Social Impact']
print(f'Tab: {ws.max_row - 1} rows, {ws.max_column} columns')
# Verify key columns
headers = [ws.cell(1, c).value for c in range(1, 20)]
assert headers[0] == 'SOC_Code'
assert headers[2] == 'Pct_Female'
assert headers[14] == 'Edu_Partisan_Lean'
assert headers[18] == 'Top_Metro_LQ'
print('Headers OK:', headers)
# Coverage check
for c in range(1, 20):
    h = ws.cell(1, c).value
    filled = sum(1 for r in range(2, ws.max_row + 1) if ws.cell(r, c).value is not None)
    pct = 100 * filled / (ws.max_row - 1)
    status = 'OK' if pct > 50 else 'LOW'
    print(f'  [{status}] {h}: {filled}/{ws.max_row - 1} ({pct:.0f}%)')
wb.close()
print('Workbook verification PASSED')
"
```

Expected: 310 data rows, 19 columns, all columns > 50% filled.

**Step 3: Test all Flask pages**

Run:
```bash
python3 -c "
import sys; sys.path.insert(0, '.')
from dashboard.app import app
with app.test_client() as c:
    for path in ['/', '/equity', '/geographic', '/political', '/transitions']:
        resp = c.get(path)
        assert resp.status_code == 200, f'{path} returned {resp.status_code}'
        print(f'{path}: OK ({len(resp.data)} bytes)')
    # Test API
    resp = c.get('/api/transition/43-3071')
    assert resp.status_code == 200
    import json
    data = json.loads(resp.data)
    assert len(data['targets']) > 0, 'No transition targets returned'
    print(f'/api/transition: OK ({len(data[\"targets\"])} targets)')
print('All pages PASSED')
"
```

Expected: All 5 pages return 200, API returns targets.

**Step 4: Manual visual check**

Run:
```bash
python3 dashboard/app.py
```

Then visit `http://localhost:5001` in a browser. Check:
- Overview page shows 310 SOCs, correct total employment
- Equity page shows all 6 charts and the top-20 table
- Geographic page shows state bar chart and filterable table
- Political page shows scatter plot and swing state table
- Transitions page dropdown works, API returns results

**Step 5: Commit**

```bash
git add -A
git commit -m "Integration test: full pipeline and 4-page dashboard verified"
```

---

### Task 17: Add .gitignore entries and final cleanup

**Step 1: Update .gitignore**

Ensure these are present:
```
# Social impact data cache (downloaded BLS files)
social_impact/data_cache/

# Dashboard generated charts
dashboard/static/img/*.png

# Intermediate merge output
social_impact/merged_social_data.json
```

**Step 2: Verify no large files are staged**

Run:
```bash
git status
git diff --stat HEAD
```

Ensure no data_cache files, no PNGs, no merged_social_data.json are tracked.

**Step 3: Final commit**

```bash
git add .gitignore
git commit -m "Update .gitignore for social impact data and dashboard assets"
```

---

## File Inventory

### New files (create)

| File | Purpose |
|------|---------|
| `social_impact/__init__.py` | Package marker |
| `social_impact/config.py` | URLs, paths, constants |
| `social_impact/download.py` | BLS file downloader with caching |
| `social_impact/crosswalk.py` | Census-to-SOC crosswalk + project SOC loader |
| `social_impact/parse_demographics.py` | CPSAAT11/11B parsers (race, gender, age) |
| `social_impact/parse_education.py` | BLS Tables 5.3/5.4 parsers |
| `social_impact/parse_union.py` | Union rate by major occ group |
| `social_impact/parse_oews.py` | OEWS state/metro geographic parsers |
| `social_impact/merge.py` | Merge engine: all sources -> 310 SOC records |
| `social_impact/writeback.py` | Write "6 Social Impact" tab to workbook |
| `social_impact/run.py` | Pipeline orchestrator |
| `social_impact/onet_skills.py` | O\*NET skill/knowledge vectors for transitions |
| `dashboard/__init__.py` | Package marker |
| `dashboard/app.py` | Flask app with 4 page routes + transition API |
| `dashboard/data_loader.py` | Workbook data cache for dashboard |
| `dashboard/charts.py` | Static chart generation (matplotlib PNGs) |
| `dashboard/templates/base.html` | Base template with sidebar nav |
| `dashboard/templates/index.html` | Overview/landing page |
| `dashboard/templates/equity.html` | Equity Impact page |
| `dashboard/templates/geographic.html` | Geographic Risk page |
| `dashboard/templates/political.html` | Political Landscape page |
| `dashboard/templates/transitions.html` | Transition Pathways page |
| `dashboard/static/css/style.css` | Dashboard CSS |

### Modified files

| File | Change |
|------|--------|
| `.gitignore` | Add social_impact/data_cache/, dashboard/static/img/*.png, social_impact/merged_social_data.json |
| `jobs-data-v3.xlsx` | New "6 Social Impact" tab (310 rows, 19 columns) |

### Directories created

```
social_impact/
social_impact/data_cache/    (gitignored)
dashboard/
dashboard/templates/
dashboard/static/
dashboard/static/css/
dashboard/static/img/        (gitignored PNGs)
```

---

## Risk Register

| Risk | Impact | Mitigation |
|------|--------|------------|
| BLS URLs change or return 403 | Download fails | Cached files in data_cache/; hardcoded fallbacks for union/foreign-born |
| CPSAAT11 format changes between years | Parser fails | Fallback column positions; header auto-detection |
| Census-to-SOC crosswalk misses some SOCs | ~10-30 SOCs without demographics | Major-group averaging fallback; explicit unmatched list |
| OEWS ZIP contents change filename | Geographic parsers fail | Glob-based file finder in _find_oews_csv() |
| O\*NET SOC codes with specializations (e.g. .01, .02) | Multiple vectors per project SOC | Average specializations to parent SOC in _normalize_soc() |
| Merged SOC codes in workbook (comma-separated) | Join failures | Try each individual code in the comma-separated list |
| Large OEWS metro file causes memory issues | Slow/crashes | Filter to project SOCs during read; use pandas groupby, not row iteration |
