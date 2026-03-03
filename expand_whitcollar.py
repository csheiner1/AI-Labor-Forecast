"""
Expand the dataset to cover ALL white-collar SOC codes found in the NIOEM.
Adds 7 new functions and ~365 new job entries to the lookup CSVs.

Run this BEFORE agent3, agent4, and task_generator_v2.
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


# ── White-collar SOC filter ──────────────────────────────────────────────
WHITE_COLLAR_MAJORS = ['11','13','15','17','19','21','23','25','27','29','41','43']

def is_white_collar(soc):
    if soc[:2] in WHITE_COLLAR_MAJORS:
        # Exclude retail floor sales (41-2xxx)
        if soc.startswith('41-2'):
            return False
        return True
    # Include Intelligence Analyst
    if soc == '33-3021':
        return True
    return False


# ── Function assignment ──────────────────────────────────────────────────
# Existing functions 1-10, new functions 11-17
NEW_FUNCTIONS = {
    11: "Healthcare & Clinical",
    12: "Education & Instruction",
    13: "Science & Research",
    14: "Community & Social Services",
    15: "Arts, Design & Creative",
    16: "Office & Administrative Support",
    17: "Engineering & Architecture",
}

def assign_function(soc, title=''):
    """Assign a SOC code to a function ID based on occupation group."""
    major = soc[:2]
    detail = soc[:5]  # e.g., "11-30"

    # ── Management (11-xxxx) ──
    if major == '11':
        # Marketing/PR/Advertising managers
        if soc in ('11-2011', '11-2021', '11-2031', '11-2032', '11-2033'):
            return 5  # Marketing & Communications
        # Financial managers
        if soc in ('11-3031',):
            return 2  # Finance
        # HR managers
        if soc in ('11-3111', '11-3121', '11-3131'):
            return 4  # HR
        # IT/Computer managers
        if soc in ('11-3021',):
            return 7  # IT
        # Operations/transportation/facilities managers
        if soc in ('11-3012', '11-3013', '11-3071'):
            return 9  # Operations
        # Sales managers
        if soc in ('11-2022',):
            return 6  # Sales
        # Engineering/architecture managers
        if soc in ('11-9041',):
            return 17  # Engineering
        # Education administrators
        if soc in ('11-9032', '11-9033', '11-9039'):
            return 12  # Education
        # Healthcare managers
        if soc in ('11-9111',):
            return 11  # Healthcare
        # All other managers → Executive
        return 1  # Executive & General Management

    # ── Business & Financial (13-xxxx) ──
    if major == '13':
        # Financial specialists
        if detail in ('13-20',) or soc[:5] in ('13-20', '13-21'):
            return 2  # Finance
        if soc.startswith('13-2'):
            return 2
        # HR-related
        if soc in ('13-1071', '13-1075', '13-1141', '13-1151'):
            return 4  # HR
        # Marketing
        if soc in ('13-1161',):
            return 5  # Marketing
        # Compliance
        if soc in ('13-1041',):
            return 3  # Legal
        # Operations/supply chain
        if soc in ('13-1081', '13-1082', '13-1023', '13-1020'):
            return 9  # Operations
        # Cost estimators, purchasing
        if soc in ('13-1051', '13-1032'):
            return 9  # Operations
        # Management analysts, consultants
        if soc in ('13-1111',):
            return 10  # Strategy
        # All other business operations
        return 10  # Strategy & Corporate Development

    # ── Computer & Math (15-xxxx) ──
    if major == '15':
        if soc.startswith('15-2'):  # Math/stats
            return 8  # Data Analytics
        return 7  # IT

    # ── Engineering & Architecture (17-xxxx) ──
    if major == '17':
        return 17  # Engineering & Architecture

    # ── Science (19-xxxx) ──
    if major == '19':
        return 13  # Science & Research

    # ── Community & Social (21-xxxx) ──
    if major == '21':
        return 14  # Community & Social Services

    # ── Legal (23-xxxx) ──
    if major == '23':
        return 3  # Legal & Compliance

    # ── Education (25-xxxx) ──
    if major == '25':
        return 12  # Education & Instruction

    # ── Arts/Design/Media (27-xxxx) ──
    if major == '27':
        return 15  # Arts, Design & Creative

    # ── Healthcare (29-xxxx) ──
    if major == '29':
        return 11  # Healthcare & Clinical

    # ── Sales (41-xxxx) ──
    if major == '41':
        return 6  # Sales & Business Development

    # ── Office/Admin (43-xxxx) ──
    if major == '43':
        return 16  # Office & Administrative Support

    # ── Protective service (Intelligence Analyst) ──
    if soc == '33-3021':
        return 8  # Data Analytics

    return 10  # Default: Strategy


def main():
    print("=" * 60)
    print("EXPANDING DATASET TO ALL WHITE-COLLAR SOC CODES")
    print("=" * 60)

    # ── Load current data ─────────────────────────────────────────────
    print("\n--- Loading current data ---")
    functions = load_csv("lookup_functions.csv")
    jobs = load_csv("lookup_jobs.csv")
    nioem = load_csv("nioem_filtered.csv")
    occupations = load_csv("occupations_master.csv")

    occ_lookup = {o['SOC_Code']: o for o in occupations}
    current_socs = set(j['SOC_Code'] for j in jobs)
    current_func_socs = set(f['SOC_Code'] for f in functions)

    print(f"  Current jobs: {len(jobs)} (covering {len(current_socs)} unique SOCs)")
    print(f"  Current functions: {len(functions)} rows")

    # ── Find all white-collar SOCs in NIOEM ───────────────────────────
    print("\n--- Identifying white-collar SOCs in NIOEM ---")
    nioem_soc_emp = defaultdict(lambda: defaultdict(float))
    nioem_soc_total = defaultdict(float)
    sector_names = {}

    for r in nioem:
        soc = r['SOC_Code']
        sid = r['Delta_Sector_ID']
        emp = safe_float(r.get('Employment_2024_thousands'))
        nioem_soc_emp[soc][sid] += emp
        nioem_soc_total[soc] += emp
        if sid not in sector_names:
            sector_names[sid] = r['Delta_Sector']

    all_wc_socs = set()
    for soc in nioem_soc_total:
        if is_white_collar(soc):
            all_wc_socs.add(soc)

    missing_socs = all_wc_socs - current_socs
    print(f"  White-collar SOCs in NIOEM: {len(all_wc_socs)}")
    print(f"  Already covered: {len(all_wc_socs - missing_socs)}")
    print(f"  Missing (to add): {len(missing_socs)}")

    # ── Assign primary sector for each missing SOC ────────────────────
    print("\n--- Assigning sectors and functions ---")
    new_jobs = []
    new_func_entries = []

    for soc in sorted(missing_socs):
        occ = occ_lookup.get(soc, {})
        title = occ.get('SOC_Title', soc)

        # Primary sector = sector with most employment
        sector_emp = nioem_soc_emp[soc]
        if sector_emp:
            primary_sid = max(sector_emp, key=sector_emp.get)
        else:
            primary_sid = '1'  # fallback

        primary_sector = sector_names.get(primary_sid, '')
        func_id = assign_function(soc, title)

        new_jobs.append({
            'Custom_Title': title,
            'Delta_Sector_ID': primary_sid,
            'SOC_Code': soc,
            'SOC_Title': title,
            'Mapping_Notes': 'Auto-expanded',
        })

        # Add to functions if not already there
        if soc not in current_func_socs:
            # Get function name
            func_name = None
            for f in functions:
                if f['Function_ID'] == str(func_id):
                    func_name = f['Function_Name']
                    break
            if not func_name:
                func_name = NEW_FUNCTIONS.get(func_id, f"Function {func_id}")

            new_func_entries.append({
                'Function_ID': str(func_id),
                'Function_Name': func_name,
                'SOC_Code': soc,
                'SOC_Title': title,
                'Shared': 'False',
            })

    # ── Merge and write ───────────────────────────────────────────────
    print("\n--- Writing expanded lookup files ---")

    # Expanded functions
    all_functions = list(functions) + new_func_entries
    write_csv("lookup_functions.csv",
              ['Function_ID', 'Function_Name', 'SOC_Code', 'SOC_Title', 'Shared'],
              all_functions)

    # Expanded jobs
    all_jobs = list(jobs) + new_jobs
    write_csv("lookup_jobs.csv",
              ['Custom_Title', 'Delta_Sector_ID', 'SOC_Code', 'SOC_Title', 'Mapping_Notes'],
              all_jobs)

    # ── Summary ───────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("EXPANSION SUMMARY")
    print("=" * 60)
    print(f"Jobs: {len(jobs)} → {len(all_jobs)} (+{len(new_jobs)})")
    print(f"Functions entries: {len(functions)} → {len(all_functions)} (+{len(new_func_entries)})")
    print(f"Unique SOC codes: {len(current_socs)} → {len(current_socs | missing_socs)}")

    # Breakdown by new function
    from collections import Counter
    func_counts = Counter()
    func_emp = defaultdict(float)
    for j in new_jobs:
        fid = assign_function(j['SOC_Code'])
        func_counts[fid] += 1
        func_emp[fid] += nioem_soc_total.get(j['SOC_Code'], 0)

    print(f"\nNew jobs by function:")
    all_func_names = {}
    for f in all_functions:
        all_func_names[f['Function_ID']] = f['Function_Name']
    for fid, name in NEW_FUNCTIONS.items():
        all_func_names[str(fid)] = name

    for fid in sorted(func_counts.keys()):
        fname = all_func_names.get(str(fid), f"Function {fid}")
        print(f"  {fid:>2d} {fname:<40s} {func_counts[fid]:>4d} jobs  {func_emp[fid]:>10,.1f}K emp")

    # Total employment
    new_emp = sum(nioem_soc_total.get(j['SOC_Code'], 0) for j in new_jobs)
    old_emp = sum(nioem_soc_total.get(soc, 0) for soc in current_socs)
    print(f"\nEmployment in NIOEM sectors:")
    print(f"  Original 124 jobs: {old_emp:,.1f}K")
    print(f"  New {len(new_jobs)} jobs:     {new_emp:,.1f}K")
    print(f"  Total:             {old_emp + new_emp:,.1f}K")


if __name__ == "__main__":
    main()
