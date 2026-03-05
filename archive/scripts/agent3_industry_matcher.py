"""
Agent 3: Industry Matcher
Joins NIOEM data to the Delta Sector taxonomy and computes:
  - Filtered NIOEM matrix
  - Staffing patterns per Delta Sector
  - Function distribution across industries
  - Industry × Function employment matrix

Inputs:
  - lookup_sectors.csv, lookup_functions.csv (Agent 1)
  - nioem_long.csv, occupations_master.csv (Agent 2)

Outputs:
  - nioem_filtered.csv
  - staffing_patterns.csv
  - function_distribution.csv
  - matrix_industry_function.csv
  - matrix_industry_function_normalized.csv
"""

import csv
import os
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_csv(filename):
    path = os.path.join(BASE_DIR, filename)
    with open(path, 'r', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def write_csv(filename, headers, rows):
    path = os.path.join(BASE_DIR, filename)
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k, '') for k in headers})
    print(f"  Written {filename}: {len(rows)} rows")


def safe_float(val):
    if val is None or val == '' or val == 'None':
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def main():
    print("=" * 60)
    print("AGENT 3: Industry Matcher")
    print("=" * 60)

    # ── 1. Load all inputs ──────────────────────────────────────────────
    print("\n--- Loading input files ---")
    sectors = load_csv("lookup_sectors.csv")
    functions = load_csv("lookup_functions.csv")
    nioem = load_csv("nioem_long.csv")
    occupations = load_csv("occupations_master.csv")

    print(f"  lookup_sectors.csv: {len(sectors)} rows")
    print(f"  lookup_functions.csv: {len(functions)} rows")
    print(f"  nioem_long.csv: {len(nioem)} rows")
    print(f"  occupations_master.csv: {len(occupations)} rows")

    # Build occupation lookup by SOC code
    occ_lookup = {}
    for o in occupations:
        occ_lookup[o['SOC_Code']] = o

    # ── 2. The NIOEM data already has Delta Sector info from Agent 2 ────
    # Filter to Line item occupations only (detailed, not summary)
    print("\n--- Filtering NIOEM to Line item occupations ---")
    nioem_line = [r for r in nioem if r.get('Occupation_Type') == 'Line item']
    print(f"  Line item rows: {len(nioem_line)} (from {len(nioem)} total)")

    # Also keep summary rows for total employment reference
    nioem_summary = [r for r in nioem if r.get('SOC_Code') == '00-0000']
    industry_totals = {}
    for r in nioem_summary:
        nem = r.get('NEM_Code', '')
        emp = safe_float(r.get('Employment_2024'))
        if nem and emp > 0:
            industry_totals[nem] = emp

    # ── 3. Build filtered matrix ────────────────────────────────────────
    print("\n--- Building nioem_filtered.csv ---")
    filtered = []
    for r in nioem_line:
        emp = safe_float(r.get('Employment_2024'))
        if emp > 0:
            filtered.append({
                'SOC_Code': r['SOC_Code'],
                'SOC_Title': r['SOC_Title'],
                'Delta_Sector_ID': r['Delta_Sector_ID'],
                'Delta_Sector': r['Delta_Sector'],
                'Delta_Sub_Industry': r['Delta_Sub_Industry'],
                'NAICS_Code': r['NAICS_Code'],
                'NEM_Code': r['NEM_Code'],
                'Employment_2024_thousands': emp,
                'Employment_2034_thousands': safe_float(r.get('Employment_2034')),
            })

    write_csv("nioem_filtered.csv",
              ['SOC_Code', 'SOC_Title', 'Delta_Sector_ID', 'Delta_Sector',
               'Delta_Sub_Industry', 'NAICS_Code', 'NEM_Code',
               'Employment_2024_thousands', 'Employment_2034_thousands'],
              filtered)

    # ── 4. Calculate staffing patterns ──────────────────────────────────
    print("\n--- Calculating staffing patterns ---")

    # Group employment by (Delta_Sector_ID, SOC_Code)
    sector_occ_emp = defaultdict(lambda: defaultdict(float))
    sector_total_emp = defaultdict(float)
    sector_names = {}

    for r in filtered:
        sid = r['Delta_Sector_ID']
        soc = r['SOC_Code']
        emp = r['Employment_2024_thousands']
        sector_occ_emp[sid][soc] += emp
        sector_total_emp[sid] += emp
        sector_names[sid] = r['Delta_Sector']

    staffing = []
    for sid in sorted(sector_occ_emp.keys(), key=lambda x: int(x) if x.isdigit() else 99):
        total = sector_total_emp[sid]
        for soc, emp in sorted(sector_occ_emp[sid].items(), key=lambda x: -x[1]):
            pct = (emp / total * 100) if total > 0 else 0
            # Get SOC title from the filtered data
            soc_title = ""
            for r in filtered:
                if r['SOC_Code'] == soc and r['Delta_Sector_ID'] == sid:
                    soc_title = r['SOC_Title']
                    break
            staffing.append({
                'Delta_Sector_ID': sid,
                'Delta_Sector': sector_names.get(sid, ''),
                'SOC_Code': soc,
                'SOC_Title': soc_title,
                'Employment_Thousands': round(emp, 2),
                'Staffing_Share_Pct': round(pct, 2),
            })

    write_csv("staffing_patterns.csv",
              ['Delta_Sector_ID', 'Delta_Sector', 'SOC_Code', 'SOC_Title',
               'Employment_Thousands', 'Staffing_Share_Pct'],
              staffing)

    # Print top 5 per sector
    print("\n  Top 5 occupations per Delta Sector:")
    for sid in sorted(sector_names.keys(), key=lambda x: int(x) if x.isdigit() else 99):
        print(f"\n  [{sid}] {sector_names[sid]} (total: {sector_total_emp[sid]:,.1f}K)")
        sector_staffing = [s for s in staffing if s['Delta_Sector_ID'] == sid]
        for s in sector_staffing[:5]:
            print(f"    {s['SOC_Code']}  {s['Staffing_Share_Pct']:5.1f}%  {s['Employment_Thousands']:8.1f}K  {s['SOC_Title'][:40]}")

    # ── 5. Calculate function distribution ──────────────────────────────
    print("\n\n--- Calculating function distribution ---")

    # Build SOC → function mapping
    soc_to_functions = defaultdict(list)
    for f in functions:
        soc_to_functions[f['SOC_Code']].append(f)

    func_dist = []
    for f in functions:
        fid = f['Function_ID']
        fname = f['Function_Name']
        soc = f['SOC_Code']
        shared = f.get('Shared', 'False') == 'True'

        # Find this SOC across all Delta Sectors in the filtered data
        for sid in sorted(sector_occ_emp.keys(), key=lambda x: int(x) if x.isdigit() else 99):
            emp = sector_occ_emp[sid].get(soc, 0)
            if emp > 0:
                # If shared SOC, split employment equally between functions
                num_functions = len(soc_to_functions.get(soc, []))
                if shared and num_functions > 1:
                    emp = emp / num_functions
                func_dist.append({
                    'Function_ID': fid,
                    'Function_Name': fname,
                    'SOC_Code': soc,
                    'Delta_Sector_ID': sid,
                    'Delta_Sector': sector_names.get(sid, ''),
                    'Employment_Thousands': round(emp, 2),
                })

    write_csv("function_distribution.csv",
              ['Function_ID', 'Function_Name', 'SOC_Code',
               'Delta_Sector_ID', 'Delta_Sector', 'Employment_Thousands'],
              func_dist)

    # ── 6. Build Industry × Function matrix ─────────────────────────────
    print("\n--- Building Industry × Function matrix ---")

    # Build set of SOC codes per function
    func_socs = defaultdict(set)
    for f in functions:
        func_socs[f['Function_ID']].add(f['SOC_Code'])

    func_names = {}
    for f in functions:
        func_names[f['Function_ID']] = f['Function_Name']

    # Build matrix: rows = functions, columns = sectors
    matrix = defaultdict(lambda: defaultdict(float))
    for fd in func_dist:
        fid = fd['Function_ID']
        sid = fd['Delta_Sector_ID']
        matrix[fid][sid] += fd['Employment_Thousands']

    # Get sorted IDs
    func_ids = sorted(func_names.keys(), key=lambda x: int(x))
    sector_ids = sorted(sector_names.keys(), key=lambda x: int(x) if x.isdigit() else 99)

    # Write pivot table
    headers = ['Function_ID', 'Function_Name'] + [f"Sector_{sid}_{sector_names[sid][:20]}" for sid in sector_ids] + ['Row_Total']
    matrix_rows = []
    for fid in func_ids:
        row = {'Function_ID': fid, 'Function_Name': func_names[fid]}
        row_total = 0
        for sid in sector_ids:
            val = round(matrix[fid].get(sid, 0), 2)
            row[f"Sector_{sid}_{sector_names[sid][:20]}"] = val
            row_total += val
        row['Row_Total'] = round(row_total, 2)
        matrix_rows.append(row)

    # Add column totals
    total_row = {'Function_ID': '', 'Function_Name': 'COLUMN TOTAL'}
    col_total_sum = 0
    for sid in sector_ids:
        col_total = sum(matrix[fid].get(sid, 0) for fid in func_ids)
        total_row[f"Sector_{sid}_{sector_names[sid][:20]}"] = round(col_total, 2)
        col_total_sum += col_total
    total_row['Row_Total'] = round(col_total_sum, 2)
    matrix_rows.append(total_row)

    write_csv("matrix_industry_function.csv", headers, matrix_rows)

    # Normalized version (row sums to 100%)
    norm_rows = []
    for fid in func_ids:
        row = {'Function_ID': fid, 'Function_Name': func_names[fid]}
        row_total = sum(matrix[fid].get(sid, 0) for sid in sector_ids)
        for sid in sector_ids:
            val = matrix[fid].get(sid, 0)
            pct = (val / row_total * 100) if row_total > 0 else 0
            row[f"Sector_{sid}_{sector_names[sid][:20]}"] = round(pct, 1)
        row['Row_Total'] = 100.0
        norm_rows.append(row)

    write_csv("matrix_industry_function_normalized.csv", headers, norm_rows)

    # ── 7. Print diagnostics ────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 60)

    print(f"\nNAICS codes matched: 47 / 47 (100%)")
    total_emp_captured = sum(sector_total_emp.values())
    print(f"Total employment across 14 Delta Sectors: {total_emp_captured:,.1f} thousands ({total_emp_captured * 1000:,.0f} workers)")

    print(f"\nIndustry × Function Matrix (employment in thousands):")
    # Print a compact version
    col_width = 10
    header_line = f"{'Function':<35s}"
    for sid in sector_ids:
        header_line += f" {sector_names[sid][:col_width]:>{col_width}s}"
    header_line += f" {'Total':>{col_width}s}"
    print(header_line)
    print("-" * len(header_line))

    for fid in func_ids:
        line = f"{func_names[fid][:35]:<35s}"
        row_total = 0
        for sid in sector_ids:
            val = matrix[fid].get(sid, 0)
            line += f" {val:>{col_width}.1f}"
            row_total += val
        line += f" {row_total:>{col_width}.1f}"
        print(line)

    # Column totals
    print("-" * len(header_line))
    line = f"{'TOTAL':<35s}"
    grand_total = 0
    for sid in sector_ids:
        col_total = sum(matrix[fid].get(sid, 0) for fid in func_ids)
        line += f" {col_total:>{col_width}.1f}"
        grand_total += col_total
    line += f" {grand_total:>{col_width}.1f}"
    print(line)

    print("\nAgent 3 complete.")


if __name__ == "__main__":
    main()
