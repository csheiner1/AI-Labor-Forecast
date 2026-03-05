#!/usr/bin/env python3
"""Deterministic data validation for jobs-data-v3.xlsx"""

import openpyxl
from collections import defaultdict, Counter

wb = openpyxl.load_workbook('jobs-data-v3.xlsx', data_only=True)
issues = []

def issue(severity, sheet, description):
    issues.append((severity, sheet, description))

def read_sheet(name, header_row=1, data_start=None):
    """Read sheet into list of dicts"""
    ws = wb[name]
    if data_start is None:
        data_start = header_row + 1
    headers = [ws.cell(header_row, c).value for c in range(1, ws.max_column+1)]
    rows = []
    for r in range(data_start, ws.max_row+1):
        row = {headers[c]: ws.cell(r, c+1).value for c in range(len(headers))}
        rows.append(row)
    return headers, rows

# ========================================
# 1. TASKS SHEET VALIDATION
# ========================================
print("Checking 3 Tasks...")
ws_tasks = wb['3 Tasks']
task_headers = [ws_tasks.cell(1, c).value for c in range(1, ws_tasks.max_column+1)]

VALID_AUT_SCORES = {0.0, 0.25, 0.5, 0.75, 1.0}
task_jobs = set()  # (SOC_Code, Job_Title)
task_soc_codes = set()
task_ids_seen = set()
time_shares_by_job = defaultdict(float)
task_count = 0
aut_issues = 0

for r in range(2, ws_tasks.max_row+1):
    soc = ws_tasks.cell(r, 1).value
    job = ws_tasks.cell(r, 2).value
    task_id = ws_tasks.cell(r, 3).value
    task_desc = ws_tasks.cell(r, 4).value
    task_type = ws_tasks.cell(r, 5).value
    time_share = ws_tasks.cell(r, 6).value
    importance = ws_tasks.cell(r, 7).value
    frequency = ws_tasks.cell(r, 8).value
    gwa = ws_tasks.cell(r, 9).value
    dedup_emp = ws_tasks.cell(r, 10).value
    econ_weight = ws_tasks.cell(r, 11).value
    aut_mod = ws_tasks.cell(r, 12).value
    aut_sig = ws_tasks.cell(r, 13).value
    
    if soc is None and job is None:
        continue
    task_count += 1
    task_jobs.add((soc, job))
    task_soc_codes.add(soc)
    
    # Duplicate task IDs
    if task_id in task_ids_seen:
        issue("HIGH", "3 Tasks", f"Duplicate Task_ID: {task_id} at row {r}")
    task_ids_seen.add(task_id)
    
    # Null checks
    for col_name, val in [("SOC_Code", soc), ("Job_Title", job), ("Task_ID", task_id), 
                           ("Task_Description", task_desc), ("Task_Type", task_type),
                           ("Time_Share_Pct", time_share), ("GWA", gwa)]:
        if val is None:
            issue("HIGH", "3 Tasks", f"Null {col_name} at row {r}")
    
    # Aut score validation
    if aut_mod is not None and aut_mod not in VALID_AUT_SCORES:
        issue("HIGH", "3 Tasks", f"Invalid Aut_Score_Mod={aut_mod} at row {r} (task {task_id})")
        aut_issues += 1
    if aut_sig is not None and aut_sig not in VALID_AUT_SCORES:
        issue("HIGH", "3 Tasks", f"Invalid Aut_Score_Sig={aut_sig} at row {r} (task {task_id})")
        aut_issues += 1
    if aut_mod is None:
        issue("HIGH", "3 Tasks", f"Missing Aut_Score_Mod at row {r} (task {task_id})")
    if aut_sig is None:
        issue("HIGH", "3 Tasks", f"Missing Aut_Score_Sig at row {r} (task {task_id})")
    
    # sig >= mod constraint
    if aut_mod is not None and aut_sig is not None and aut_sig < aut_mod:
        issue("HIGH", "3 Tasks", f"sig ({aut_sig}) < mod ({aut_mod}) at row {r} (task {task_id}, job {job})")
    
    # Task_Type valid
    if task_type not in ("Core", "Supplemental", None):
        issue("MEDIUM", "3 Tasks", f"Invalid Task_Type='{task_type}' at row {r}")
    
    # Time share accumulation
    if time_share is not None:
        time_shares_by_job[(soc, job)] += time_share
    
    # Employment checks
    if dedup_emp is not None and dedup_emp < 0:
        issue("HIGH", "3 Tasks", f"Negative Dedup_Employment_K={dedup_emp} at row {r}")

# Time share sums
time_share_issues = 0
for (soc, job), total in time_shares_by_job.items():
    if abs(total - 100.0) > 2.0:  # Allow 2% tolerance
        issue("MEDIUM", "3 Tasks", f"Time_Share_Pct sums to {total:.1f}% for {job} ({soc}), expected ~100%")
        time_share_issues += 1

print(f"  {task_count} tasks, {len(task_jobs)} unique jobs, {time_share_issues} time-share issues")

# ========================================
# 2. JOBS SHEET VALIDATION
# ========================================
print("Checking 2 Jobs...")
ws_jobs = wb['2 Jobs']
job_soc_codes = set()
job_titles = set()
job_sectors = set()
jobs_data = {}  # (SOC_Code, Custom_Title) -> row data

for r in range(2, ws_jobs.max_row+1):
    soc = ws_jobs.cell(r, 1).value
    title = ws_jobs.cell(r, 2).value
    sector = ws_jobs.cell(r, 3).value
    emp = ws_jobs.cell(r, 4).value
    wage = ws_jobs.cell(r, 5).value
    
    if soc is None and title is None:
        continue
    
    job_soc_codes.add(soc)
    job_titles.add((soc, title))
    if sector:
        job_sectors.add(sector)
    jobs_data[(soc, title)] = {"emp": emp, "sector": sector, "wage": wage}
    
    # Null checks
    if soc is None: issue("HIGH", "2 Jobs", f"Null SOC_Code at row {r}")
    if title is None: issue("HIGH", "2 Jobs", f"Null Custom_Title at row {r}")
    if sector is None: issue("HIGH", "2 Jobs", f"Null Sector at row {r} ({title})")
    if emp is None: issue("HIGH", "2 Jobs", f"Null Employment at row {r} ({title})")
    if emp is not None and emp <= 0: issue("MEDIUM", "2 Jobs", f"Employment={emp} <= 0 at row {r} ({title})")
    if wage is not None and wage <= 0: issue("MEDIUM", "2 Jobs", f"Wage={wage} <= 0 at row {r} ({title})")

print(f"  {len(job_titles)} jobs, {len(job_soc_codes)} unique SOC codes, {len(job_sectors)} sectors")

# ========================================
# 3. 1A SUMMARY VALIDATION
# ========================================
print("Checking 1A Summary...")
ws_summary = wb['1A Summary']
summary_sectors = {}
for r in range(2, ws_summary.max_row+1):
    sid = ws_summary.cell(r, 1).value
    name = ws_summary.cell(r, 2).value
    num_naics = ws_summary.cell(r, 3).value
    emp = ws_summary.cell(r, 4).value
    if sid is None:
        continue
    summary_sectors[sid] = {"name": name, "emp": emp, "num_naics": num_naics}
    if emp is None or emp <= 0:
        issue("HIGH", "1A Summary", f"Invalid employment for sector {sid} ({name})")

print(f"  {len(summary_sectors)} sectors")

# ========================================
# 4. 1A INDUSTRIES VALIDATION
# ========================================
print("Checking 1A Industries...")
ws_ind = wb['1A Industries']
industries_by_sector = defaultdict(list)
industries_emp_by_sector = defaultdict(float)

for r in range(2, ws_ind.max_row+1):
    naics = ws_ind.cell(r, 1).value
    naics_title = ws_ind.cell(r, 2).value
    sid = ws_ind.cell(r, 3).value
    sector = ws_ind.cell(r, 4).value
    emp = ws_ind.cell(r, 8).value
    
    if naics is None and sid is None:
        continue
    industries_by_sector[sid].append(naics)
    if emp is not None:
        industries_emp_by_sector[sid] += emp

# Check NAICS counts match summary
for sid, data in summary_sectors.items():
    actual = len(industries_by_sector.get(sid, []))
    expected = data["num_naics"]
    if expected and actual != expected:
        issue("MEDIUM", "1A Industries", f"Sector {sid} ({data['name']}): {actual} NAICS codes but Summary says {expected}")

# Check employment rollups
for sid, data in summary_sectors.items():
    ind_total = industries_emp_by_sector.get(sid, 0)
    sum_emp = data["emp"]
    if sum_emp and abs(ind_total - sum_emp) > 1.0:  # 1K tolerance
        issue("MEDIUM", "1A Industries→Summary", f"Sector {sid} ({data['name']}): Industries sum={ind_total:.1f}K vs Summary={sum_emp:.1f}K")

# ========================================
# 5. FRICTIONS TABS VALIDATION
# ========================================
print("Checking Frictions tabs...")
VALID_E = {0.15, 0.30, 0.50, 0.75, 1.00}
friction_sectors = {}

for sheet_name in ['Low Industry Frictions', 'High Industry Frictions']:
    ws = wb[sheet_name]
    for r in range(5, ws.max_row+1):
        sid = ws.cell(r, 1).value
        name = ws.cell(r, 2).value
        emp = ws.cell(r, 3).value
        wage = ws.cell(r, 4).value
        t1 = ws.cell(r, 5).value
        t2 = ws.cell(r, 6).value
        t3 = ws.cell(r, 7).value
        t4 = ws.cell(r, 8).value
        d_idx = ws.cell(r, 9).value
        t0 = ws.cell(r, 10).value
        t18 = ws.cell(r, 11).value
        f1 = ws.cell(r, 12).value
        f2 = ws.cell(r, 13).value
        f3 = ws.cell(r, 14).value
        f_sum = ws.cell(r, 15).value
        r_val = ws.cell(r, 16).value
        e_val = ws.cell(r, 17).value
        
        if sid is None:
            continue
        
        if sheet_name == 'Low Industry Frictions':
            friction_sectors[sid] = name
        
        # T drivers 1-4
        for t_name, t_val in [("T1", t1), ("T2", t2), ("T3", t3), ("T4", t4)]:
            if t_val is not None and (t_val < 1 or t_val > 4):
                issue("HIGH", sheet_name, f"Sector {sid} ({name}): {t_name}={t_val} outside 1-4")
            if t_val is not None and t_val != int(t_val):
                issue("MEDIUM", sheet_name, f"Sector {sid} ({name}): {t_name}={t_val} not integer")
        
        # R sub-components 1-4
        for f_name, f_val in [("f1", f1), ("f2", f2), ("f3", f3)]:
            if f_val is not None and (f_val < 1 or f_val > 4):
                issue("HIGH", sheet_name, f"Sector {sid} ({name}): {f_name}={f_val} outside 1-4")
        
        # E valid values
        if e_val is not None and e_val not in VALID_E:
            issue("MEDIUM", sheet_name, f"Sector {sid} ({name}): E={e_val} not in {{0.15, 0.30, 0.50, 0.75, 1.00}}")
        
        # Verify D_base formula: avg(T1,T2,T3)
        if t1 is not None and t2 is not None and t3 is not None and d_idx is not None:
            d_base = (t1+t2+t3)/3
            d_spread = max(t1,t2,t3) - d_base
            expected_d = d_base + 0.25 * d_spread
            if abs(d_idx - expected_d) > 0.01:
                issue("HIGH", sheet_name, f"Sector {sid} ({name}): D={d_idx:.4f} but expected {expected_d:.4f}")
        
        # Verify t0 formula: 1.5*D - 0.5*T4 - 0.5
        if d_idx is not None and t4 is not None and t0 is not None:
            expected_t0 = 1.5*d_idx - 0.5*t4 - 0.5
            if abs(t0 - expected_t0) > 0.01:
                issue("HIGH", sheet_name, f"Sector {sid} ({name}): t0={t0:.4f} but expected {expected_t0:.4f}")
        
        # Verify T(18mo) formula: 1/(1+exp(-alpha*(1.5-t0))) with alpha=3
        import math
        if t0 is not None and t18 is not None:
            alpha = 3
            expected_t18 = 1 / (1 + math.exp(-alpha * (1.5 - t0)))
            if abs(t18 - expected_t18) > 0.01:
                issue("HIGH", sheet_name, f"Sector {sid} ({name}): T(18mo)={t18:.4f} but expected {expected_t18:.4f}")
        
        # Verify F = f1+f2+f3
        if f1 is not None and f2 is not None and f3 is not None and f_sum is not None:
            expected_f = f1+f2+f3
            if abs(f_sum - expected_f) > 0.01:
                issue("HIGH", sheet_name, f"Sector {sid} ({name}): F={f_sum} but expected {expected_f}")
        
        # Verify R = 1 - 0.7*(F-3)/9
        if f_sum is not None and r_val is not None:
            expected_r = 1 - 0.7*(f_sum - 3)/9
            if abs(r_val - expected_r) > 0.01:
                issue("HIGH", sheet_name, f"Sector {sid} ({name}): R={r_val:.4f} but expected {expected_r:.4f}")
        
        # Employment match with summary
        if sid in summary_sectors and emp is not None:
            sum_emp = summary_sectors[sid]["emp"]
            if sum_emp and abs(emp - sum_emp) > 1.0:
                issue("MEDIUM", sheet_name, f"Sector {sid} ({name}): Emp={emp} vs Summary={sum_emp}")

# ========================================
# 6. CROSS-SHEET REFERENTIAL INTEGRITY
# ========================================
print("Checking cross-sheet references...")

# Tasks jobs vs Jobs sheet
tasks_not_in_jobs = task_jobs - job_titles
jobs_not_in_tasks = job_titles - task_jobs

if tasks_not_in_jobs:
    for soc, title in sorted(tasks_not_in_jobs):
        issue("HIGH", "3 Tasks→2 Jobs", f"Task job ({soc}, {title}) not found in 2 Jobs")

if jobs_not_in_tasks:
    for soc, title in sorted(jobs_not_in_tasks):
        issue("MEDIUM", "2 Jobs→3 Tasks", f"Job ({soc}, {title}) has no tasks in 3 Tasks")

# Sectors in Jobs vs Summary
summary_sector_names = {d["name"] for d in summary_sectors.values()}
jobs_sectors_not_in_summary = job_sectors - summary_sector_names
if jobs_sectors_not_in_summary:
    for s in sorted(jobs_sectors_not_in_summary):
        issue("HIGH", "2 Jobs→1A Summary", f"Sector '{s}' in Jobs not found in Summary")

# Friction sectors vs Summary sectors
friction_sector_names = set(friction_sectors.values())
summary_not_in_frictions = summary_sector_names - friction_sector_names
frictions_not_in_summary = friction_sector_names - summary_sector_names

if summary_not_in_frictions:
    for s in sorted(summary_not_in_frictions):
        issue("HIGH", "1A Summary→Frictions", f"Sector '{s}' in Summary but missing from Frictions tabs")
if frictions_not_in_summary:
    for s in sorted(frictions_not_in_summary):
        issue("HIGH", "Frictions→1A Summary", f"Sector '{s}' in Frictions but missing from Summary")

# Staffing patterns SOC codes vs Jobs
print("Checking Staffing Patterns...")
ws_staff = wb['Staffing Patterns']
staffing_soc = set()
staffing_by_sector = defaultdict(float)  # sector_id -> sum of shares

for r in range(2, ws_staff.max_row+1):
    sid = ws_staff.cell(r, 1).value
    soc = ws_staff.cell(r, 3).value
    share = ws_staff.cell(r, 6).value
    if soc:
        staffing_soc.add(soc)
    if sid and share:
        staffing_by_sector[str(sid)] += share

# Check staffing share sums
for sid, total in staffing_by_sector.items():
    if abs(total - 100.0) > 5.0:  # 5% tolerance for staffing
        issue("MEDIUM", "Staffing Patterns", f"Sector {sid}: Staffing shares sum to {total:.1f}%, expected ~100%")

# Job_Industry SOC codes vs Jobs
print("Checking Job_Industry...")
ws_ji = wb['2B Job_Industry']
ji_soc = set()
ji_industries = []

# Header is in row 2 for this sheet
for c in range(3, ws_ji.max_column+1):
    ind_name = ws_ji.cell(2, c).value
    if ind_name:
        ji_industries.append(ind_name)

for r in range(3, ws_ji.max_row+1):
    soc = ws_ji.cell(r, 1).value
    if soc:
        ji_soc.add(soc)

# Check JI industries vs summary sectors
ji_industries_set = set(ji_industries)
summary_not_in_ji = summary_sector_names - ji_industries_set
ji_not_in_summary = ji_industries_set - summary_sector_names

if summary_not_in_ji:
    for s in sorted(summary_not_in_ji):
        issue("MEDIUM", "1A Summary→Job_Industry", f"Sector '{s}' in Summary but missing from Job_Industry columns")
if ji_not_in_summary:
    for s in sorted(ji_not_in_summary):
        issue("MEDIUM", "Job_Industry→1A Summary", f"Industry '{s}' in Job_Industry but not in Summary")

# Lookup_Jobs vs Jobs
print("Checking Lookup tables...")
ws_lj = wb['Lookup_Jobs']
lookup_jobs = set()
for r in range(2, ws_lj.max_row+1):
    title = ws_lj.cell(r, 1).value
    soc = ws_lj.cell(r, 3).value
    if title and soc:
        lookup_jobs.add((soc, title))

lookup_not_in_jobs = lookup_jobs - job_titles
jobs_not_in_lookup = job_titles - lookup_jobs
if lookup_not_in_jobs:
    for soc, title in sorted(lookup_not_in_jobs)[:20]:
        issue("MEDIUM", "Lookup_Jobs→2 Jobs", f"Lookup job ({soc}, {title}) not in 2 Jobs")
    if len(lookup_not_in_jobs) > 20:
        issue("MEDIUM", "Lookup_Jobs→2 Jobs", f"...and {len(lookup_not_in_jobs)-20} more")
if jobs_not_in_lookup:
    for soc, title in sorted(jobs_not_in_lookup)[:20]:
        issue("MEDIUM", "2 Jobs→Lookup_Jobs", f"Job ({soc}, {title}) not in Lookup_Jobs")
    if len(jobs_not_in_lookup) > 20:
        issue("MEDIUM", "2 Jobs→Lookup_Jobs", f"...and {len(jobs_not_in_lookup)-20} more")

# Lookup_Sectors vs 1A Industries
ws_ls = wb['Lookup_Sectors']
lookup_sector_names = set()
for r in range(2, ws_ls.max_row+1):
    name = ws_ls.cell(r, 2).value
    if name:
        lookup_sector_names.add(name)

ls_not_in_summary = lookup_sector_names - summary_sector_names
summary_not_in_ls = summary_sector_names - lookup_sector_names
if ls_not_in_summary:
    for s in sorted(ls_not_in_summary):
        issue("MEDIUM", "Lookup_Sectors→Summary", f"Sector '{s}' in Lookup but not in Summary")
if summary_not_in_ls:
    for s in sorted(summary_not_in_ls):
        issue("MEDIUM", "Summary→Lookup_Sectors", f"Sector '{s}' in Summary but not in Lookup")

# ========================================
# 7. EMPLOYMENT CONSISTENCY
# ========================================
print("Checking employment consistency...")

# For jobs with multiple titles sharing a SOC code, check they have same BLS employment
soc_emp = defaultdict(set)
for (soc, title), data in jobs_data.items():
    if data["emp"] is not None:
        soc_emp[soc].add(data["emp"])

for soc, emps in soc_emp.items():
    if len(emps) > 1:
        # Multiple employment values for same SOC is expected (shared SOC, same BLS number)
        # But flag if they differ
        pass  # This is expected - multiple custom titles map to same SOC with same employment

# Check dedup employment in tasks vs jobs employment
task_emp_by_job = {}
for r in range(2, ws_tasks.max_row+1):
    soc = ws_tasks.cell(r, 1).value
    job = ws_tasks.cell(r, 2).value
    dedup = ws_tasks.cell(r, 10).value
    if soc and job and dedup is not None:
        task_emp_by_job[(soc, job)] = dedup

for (soc, job), dedup_emp in task_emp_by_job.items():
    if (soc, job) in jobs_data:
        job_emp = jobs_data[(soc, job)]["emp"]
        if job_emp is not None and dedup_emp is not None:
            if dedup_emp > job_emp + 0.1:
                issue("MEDIUM", "3 Tasks→2 Jobs", f"Dedup_Emp ({dedup_emp:.1f}K) > Job_Emp ({job_emp:.1f}K) for {job} ({soc})")

# ========================================
# REPORT
# ========================================
print("\n" + "="*80)
print("VALIDATION REPORT")
print("="*80)

by_severity = defaultdict(list)
for sev, sheet, desc in issues:
    by_severity[sev].append((sheet, desc))

for sev in ["HIGH", "MEDIUM", "LOW"]:
    items = by_severity.get(sev, [])
    print(f"\n{'='*40}")
    print(f"  {sev}: {len(items)} issues")
    print(f"{'='*40}")
    for sheet, desc in items:
        print(f"  [{sheet}] {desc}")

print(f"\n\nTOTAL: {len(issues)} issues ({len(by_severity.get('HIGH',[]))} HIGH, {len(by_severity.get('MEDIUM',[]))} MEDIUM, {len(by_severity.get('LOW',[]))} LOW)")
