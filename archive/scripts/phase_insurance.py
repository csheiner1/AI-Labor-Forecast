"""
Phase 4 — Split Insurance from Finance into new Sector 21.

Exports: apply_insurance_split(wb) which modifies an openpyxl Workbook in-place.
"""

import csv
import os
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NIOEM_PATH = os.path.join(BASE_DIR, "nioem_filtered.csv")

INSURANCE_NAICS = {"5241", "5242", "5251"}
INSURANCE_SOC_CODES = {"15-2011", "13-2053", "13-1031", "13-1032", "41-3021", "43-9041"}


def _safe_float(val):
    """Convert cell value to float, treating None/empty as 0."""
    if val is None or val == "" or val == "None":
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def _load_nioem():
    """Load nioem_filtered.csv and return list of dicts."""
    with open(NIOEM_PATH, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _find_col_by_header(ws, row, text):
    """Find column number in a row whose value contains `text`."""
    for c in range(1, ws.max_column + 1):
        val = ws.cell(row, c).value
        if val and text in str(val):
            return c
    return None


# ─────────────────────────────────────────────────────────────────────
# Step 4a — Move insurance NAICS codes in 1A Industries & Lookup_Sectors
# ─────────────────────────────────────────────────────────────────────

def _step_4a(wb):
    print("  Step 4a: Moving insurance NAICS in 1A Industries and Lookup_Sectors...")

    # 1A Industries — Sector_ID is integer
    ws = wb["1A Industries"]
    count = 0
    for r in range(2, ws.max_row + 1):
        naics = str(ws.cell(r, 1).value or "").strip()
        if naics in INSURANCE_NAICS:
            ws.cell(r, 3).value = 21  # Sector_ID
            ws.cell(r, 4).value = "Insurance"  # Sector
            count += 1
    print(f"    1A Industries: moved {count} rows to Sector 21")

    # Lookup_Sectors — Sector_ID is string
    ws = wb["Lookup_Sectors"]
    count = 0
    for r in range(2, ws.max_row + 1):
        naics = str(ws.cell(r, 4).value or "").strip()  # col D = NAICS_Code
        if naics in INSURANCE_NAICS:
            ws.cell(r, 1).value = "21"  # Sector_ID
            ws.cell(r, 2).value = "Insurance"  # Sector
            count += 1
    print(f"    Lookup_Sectors: moved {count} rows to Sector 21")


# ─────────────────────────────────────────────────────────────────────
# Step 4b — Move 6 insurance-specific jobs in 2 Jobs & Lookup_Jobs
# ─────────────────────────────────────────────────────────────────────

def _step_4b(wb):
    print("  Step 4b: Moving 6 insurance jobs in 2 Jobs and Lookup_Jobs...")

    # 2 Jobs sheet — Sector_ID stored as string, col D
    ws = wb["2 Jobs"]
    count = 0
    for r in range(2, ws.max_row + 1):
        soc = str(ws.cell(r, 1).value or "").strip()
        sid = str(ws.cell(r, 4).value or "").strip()
        if soc in INSURANCE_SOC_CODES and sid == "1":
            ws.cell(r, 4).value = "21"   # Sector_ID
            ws.cell(r, 5).value = "Insurance"  # Sector
            count += 1
    print(f"    2 Jobs: moved {count} rows to Sector 21")

    # Lookup_Jobs — col B = Sector_ID (string)
    ws = wb["Lookup_Jobs"]
    count = 0
    for r in range(2, ws.max_row + 1):
        soc = str(ws.cell(r, 3).value or "").strip()  # col C = SOC_Code
        sid = str(ws.cell(r, 2).value or "").strip()   # col B = Sector_ID
        if soc in INSURANCE_SOC_CODES and sid == "1":
            ws.cell(r, 2).value = "21"
            count += 1
    print(f"    Lookup_Jobs: moved {count} rows to Sector 21")


# ─────────────────────────────────────────────────────────────────────
# Step 4c — Update 1A Summary
# ─────────────────────────────────────────────────────────────────────

def _step_4c(wb):
    print("  Step 4c: Updating 1A Summary...")

    ws = wb["1A Summary"]

    # Find Finance row (Sector_ID == 1)
    finance_row = None
    for r in range(2, ws.max_row + 1):
        if ws.cell(r, 1).value == 1 or str(ws.cell(r, 1).value) == "1":
            finance_row = r
            break

    if not finance_row:
        print("    WARNING: Could not find Finance row in 1A Summary")
        return

    # Calculate insurance avg wage from 2 Jobs sheet
    jobs_ws = wb["2 Jobs"]
    ins_wage_sum = 0.0
    ins_emp_sum = 0.0
    fin_wage_sum = 0.0
    fin_emp_sum = 0.0
    for r in range(2, jobs_ws.max_row + 1):
        soc = str(jobs_ws.cell(r, 1).value or "").strip()
        sid = str(jobs_ws.cell(r, 4).value or "").strip()
        emp = _safe_float(jobs_ws.cell(r, 8).value)
        wage = _safe_float(jobs_ws.cell(r, 9).value)
        # After step 4b, insurance jobs already have sid='21'
        if sid == "21":
            ins_wage_sum += wage * emp
            ins_emp_sum += emp
        elif sid == "1":
            fin_wage_sum += wage * emp
            fin_emp_sum += emp

    ins_avg_wage = ins_wage_sum / ins_emp_sum if ins_emp_sum > 0 else 0
    fin_avg_wage = fin_wage_sum / fin_emp_sum if fin_emp_sum > 0 else 0

    # Update Finance row
    ws.cell(finance_row, 3).value = 8       # Num_NAICS (11 - 3 = 8)
    ws.cell(finance_row, 4).value = 3632.3  # Employment
    ws.cell(finance_row, 5).value = round(fin_avg_wage, 2) if fin_avg_wage else None
    print(f"    Finance row updated: Emp=3632.3, Num_NAICS=8, Avg_Wage={fin_avg_wage:.0f}")

    # Add Insurance row at end
    new_row = ws.max_row + 1
    ws.cell(new_row, 1).value = 21
    ws.cell(new_row, 2).value = "Insurance"
    ws.cell(new_row, 3).value = 3        # Num_NAICS
    ws.cell(new_row, 4).value = 2994.4   # Employment
    ws.cell(new_row, 5).value = round(ins_avg_wage, 2) if ins_avg_wage else None
    print(f"    Insurance row added: Emp=2994.4, Num_NAICS=3, Avg_Wage={ins_avg_wage:.0f}")


# ─────────────────────────────────────────────────────────────────────
# Step 4d — Split Matrix Finance column into Finance + Insurance
# ─────────────────────────────────────────────────────────────────────

def _step_4d(wb):
    print("  Step 4d: Splitting Matrix Finance column...")

    nioem = _load_nioem()
    ws = wb["Matrix"]
    jobs_ws = wb["2 Jobs"]

    # Finance column is col 3 in Matrix (header row 2)
    fin_col = 3
    row_total_col = ws.max_column  # last col = Row Total

    # Build SOC → Function_ID mapping from 2 Jobs (for ALL finance+insurance SOCs)
    soc_to_func = {}
    for r in range(2, jobs_ws.max_row + 1):
        soc = str(jobs_ws.cell(r, 1).value or "").strip()
        sid = str(jobs_ws.cell(r, 4).value or "").strip()
        func_id = jobs_ws.cell(r, 6).value
        if sid in ("1", "21") and func_id is not None:
            soc_to_func[soc] = str(func_id).strip()

    # Build per-function insurance share from NIOEM
    # func → {insurance_emp, total_emp}
    func_ins_emp = defaultdict(float)
    func_total_emp = defaultdict(float)
    global_ins_emp = 0.0
    global_total_emp = 0.0

    for row in nioem:
        if row["Delta_Sector_ID"] != "1":
            continue
        soc = row["SOC_Code"]
        emp = _safe_float(row["Employment_2024_thousands"])
        naics = row["NAICS_Code"]
        is_insurance = naics in INSURANCE_NAICS

        func_id = soc_to_func.get(soc)

        if func_id:
            func_total_emp[func_id] += emp
            if is_insurance:
                func_ins_emp[func_id] += emp

        global_total_emp += emp
        if is_insurance:
            global_ins_emp += emp

    global_ratio = global_ins_emp / global_total_emp if global_total_emp > 0 else 0.452
    print(f"    Global insurance ratio: {global_ratio:.4f}")

    # Insert new column after Finance (col 3) for Insurance
    ws.insert_cols(fin_col + 1)
    # After insertion, old col 4+ shifted right; row_total_col shifted right too
    ins_col = fin_col + 1  # col 4 = Insurance
    row_total_col += 1     # shifted

    # Set headers
    ws.cell(2, ins_col).value = "21 Insurance"

    # Data rows: 3 to 19 (17 function rows)
    for r in range(3, 20):
        func_id = str(ws.cell(r, 1).value or "").strip()
        fin_val = _safe_float(ws.cell(r, fin_col).value)

        # Determine insurance share for this function
        if func_id in func_total_emp and func_total_emp[func_id] > 0:
            share = func_ins_emp.get(func_id, 0) / func_total_emp[func_id]
        else:
            share = global_ratio

        ins_val = round(fin_val * share, 1)
        new_fin_val = round(fin_val - ins_val, 1)

        ws.cell(r, fin_col).value = new_fin_val
        ws.cell(r, ins_col).value = ins_val

        # Recalculate row total (sum cols 3 to row_total_col-1)
        row_sum = 0.0
        for c in range(3, row_total_col):
            row_sum += _safe_float(ws.cell(r, c).value)
        ws.cell(r, row_total_col).value = round(row_sum, 1)

    # Row 20 = COLUMN TOTAL
    for c in [fin_col, ins_col, row_total_col]:
        col_sum = 0.0
        for r in range(3, 20):
            col_sum += _safe_float(ws.cell(r, c).value)
        ws.cell(20, c).value = round(col_sum, 1)

    # ── Normalized section (rows 22+) ──
    # Row 22: title, Row 23: headers, Rows 24-40: data
    ws.cell(23, ins_col).value = "21 Insurance"

    for r in range(24, 41):
        # Recalculate row total of absolute values first
        abs_row_total = 0.0
        for c in range(3, row_total_col):
            abs_r = r - 21  # corresponding absolute row (24→3, etc.)
            abs_row_total += _safe_float(ws.cell(abs_r, c).value)

        if abs_row_total > 0:
            for c in range(3, row_total_col):
                abs_r = r - 21
                abs_val = _safe_float(ws.cell(abs_r, c).value)
                ws.cell(r, c).value = round(abs_val / abs_row_total * 100, 1)

    print(f"    Matrix split complete. Insurance column inserted at col {ins_col}")


# ─────────────────────────────────────────────────────────────────────
# Step 4e — Split 2B Job_Industry Finance column
# ─────────────────────────────────────────────────────────────────────

def _step_4e(wb):
    print("  Step 4e: Splitting 2B Job_Industry Finance column...")

    nioem = _load_nioem()
    ws = wb["2B Job_Industry"]

    fin_col = 3  # col C = "Finance & Financial Services"

    # Build per-SOC insurance ratio from NIOEM
    soc_ins_emp = defaultdict(float)
    soc_total_emp = defaultdict(float)

    for row in nioem:
        if row["Delta_Sector_ID"] != "1":
            continue
        soc = row["SOC_Code"]
        emp = _safe_float(row["Employment_2024_thousands"])
        naics = row["NAICS_Code"]

        soc_total_emp[soc] += emp
        if naics in INSURANCE_NAICS:
            soc_ins_emp[soc] += emp

    global_ins = sum(soc_ins_emp.values())
    global_tot = sum(soc_total_emp.values())
    global_ratio = global_ins / global_tot if global_tot > 0 else 0.452

    # Insert Insurance column after Finance (col 3)
    ws.insert_cols(fin_col + 1)
    ins_col = fin_col + 1  # col 4

    # Set headers
    ws.cell(1, ins_col).value = None  # title row
    ws.cell(2, ins_col).value = "Insurance"

    # Data rows start at row 3
    for r in range(3, ws.max_row + 1):
        soc = str(ws.cell(r, 1).value or "").strip()
        if not soc:
            continue

        fin_val = _safe_float(ws.cell(r, fin_col).value)

        if soc in soc_total_emp and soc_total_emp[soc] > 0:
            ratio = soc_ins_emp.get(soc, 0) / soc_total_emp[soc]
        else:
            ratio = global_ratio

        ins_val = round(fin_val * ratio, 1)
        new_fin_val = round(fin_val - ins_val, 1)

        ws.cell(r, fin_col).value = new_fin_val
        ws.cell(r, ins_col).value = ins_val

    print(f"    2B split complete. Insurance column inserted at col {ins_col}")


# ─────────────────────────────────────────────────────────────────────
# Step 4f — Create Insurance rows in Staffing Patterns
# ─────────────────────────────────────────────────────────────────────

def _step_4f(wb):
    print("  Step 4f: Creating Insurance rows in Staffing Patterns...")

    nioem = _load_nioem()
    ws = wb["Staffing Patterns"]

    # Aggregate NIOEM insurance employment by SOC
    ins_soc_emp = defaultdict(float)
    ins_soc_title = {}
    fin_soc_emp = defaultdict(float)  # non-insurance finance

    for row in nioem:
        if row["Delta_Sector_ID"] != "1":
            continue
        soc = row["SOC_Code"]
        emp = _safe_float(row["Employment_2024_thousands"])
        naics = row["NAICS_Code"]

        if naics in INSURANCE_NAICS:
            ins_soc_emp[soc] += emp
            ins_soc_title[soc] = row["SOC_Title"]
        else:
            fin_soc_emp[soc] += emp

    total_ins_emp = sum(ins_soc_emp.values())
    total_fin_emp = sum(fin_soc_emp.values())

    # Update existing Finance rows: subtract insurance employment, recalc shares
    fin_rows = []  # track (row_num, soc) for finance
    for r in range(2, ws.max_row + 1):
        sid = str(ws.cell(r, 1).value or "").strip()
        if sid != "1":
            continue
        soc = str(ws.cell(r, 3).value or "").strip()
        old_emp = _safe_float(ws.cell(r, 5).value)

        # Subtract insurance portion
        ins_portion = ins_soc_emp.get(soc, 0)
        new_emp = round(old_emp - ins_portion, 1)
        if new_emp < 0:
            new_emp = 0.0
        ws.cell(r, 5).value = new_emp
        fin_rows.append((r, soc, new_emp))

    # Recalculate finance staffing shares
    new_fin_total = sum(emp for _, _, emp in fin_rows)
    for r, soc, emp in fin_rows:
        share = round(emp / new_fin_total * 100, 2) if new_fin_total > 0 else 0
        ws.cell(r, 6).value = share

    print(f"    Updated {len(fin_rows)} Finance staffing rows (new total: {new_fin_total:.1f}K)")

    # Append Insurance rows at end of sheet
    insert_row = ws.max_row + 1
    count = 0
    for soc in sorted(ins_soc_emp.keys()):
        emp = round(ins_soc_emp[soc], 1)
        share = round(emp / total_ins_emp * 100, 2) if total_ins_emp > 0 else 0
        title = ins_soc_title.get(soc, soc)

        ws.cell(insert_row, 1).value = "21"
        ws.cell(insert_row, 2).value = "Insurance"
        ws.cell(insert_row, 3).value = soc
        ws.cell(insert_row, 4).value = title
        ws.cell(insert_row, 5).value = emp
        ws.cell(insert_row, 6).value = share
        insert_row += 1
        count += 1

    print(f"    Added {count} Insurance staffing rows (total emp: {total_ins_emp:.1f}K)")


# ─────────────────────────────────────────────────────────────────────
# Step 4g — Update Industry Frictions
# ─────────────────────────────────────────────────────────────────────

def _step_4g(wb):
    print("  Step 4g: Updating Industry Frictions...")

    ws = wb["Industry Frictions"]

    # Calculate insurance avg wage from 2 Jobs
    jobs_ws = wb["2 Jobs"]
    ins_wage_sum = 0.0
    ins_emp_sum = 0.0
    for r in range(2, jobs_ws.max_row + 1):
        sid = str(jobs_ws.cell(r, 4).value or "").strip()
        if sid == "21":
            emp = _safe_float(jobs_ws.cell(r, 8).value)
            wage = _safe_float(jobs_ws.cell(r, 9).value)
            ins_wage_sum += wage * emp
            ins_emp_sum += emp
    ins_avg_wage = round(ins_wage_sum / ins_emp_sum) if ins_emp_sum > 0 else None

    # Find Finance row and Insurance row
    for r in range(4, ws.max_row + 1):
        row_id = ws.cell(r, 1).value
        name = str(ws.cell(r, 2).value or "").strip()

        if row_id == 1 or (isinstance(row_id, (int, float)) and int(row_id) == 1 and "Finance" in name):
            # Update Finance employment
            ws.cell(r, 3).value = 3632.3
            # Recalculate finance avg wage
            fin_wage_sum = 0.0
            fin_emp_sum = 0.0
            for jr in range(2, jobs_ws.max_row + 1):
                sid = str(jobs_ws.cell(jr, 4).value or "").strip()
                if sid == "1":
                    emp = _safe_float(jobs_ws.cell(jr, 8).value)
                    wage = _safe_float(jobs_ws.cell(jr, 9).value)
                    fin_wage_sum += wage * emp
                    fin_emp_sum += emp
            fin_avg_wage = round(fin_wage_sum / fin_emp_sum) if fin_emp_sum > 0 else None
            ws.cell(r, 4).value = fin_avg_wage
            print(f"    Finance row updated: Emp=3632.3, Avg_Wage={fin_avg_wage}")

        if name == "Insurance" or (row_id == 2 and "Insurance" in name):
            # Update Insurance employment and wage
            ws.cell(r, 3).value = 2994.4
            ws.cell(r, 4).value = ins_avg_wage
            print(f"    Insurance row updated: Emp=2994.4, Avg_Wage={ins_avg_wage}")


# ─────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────

def apply_insurance_split(wb):
    """Split Insurance from Finance (Sector 1) into new Sector 21."""
    print("\n" + "=" * 60)
    print("PHASE 4: INSURANCE SPLIT")
    print("=" * 60)

    _step_4a(wb)
    _step_4b(wb)
    _step_4c(wb)
    _step_4d(wb)
    _step_4e(wb)
    _step_4f(wb)
    _step_4g(wb)

    print("\n  Phase 4 complete: Insurance split from Finance.")
    return wb
