#!/usr/bin/env python3
"""
Deep-dive analysis: Staffing & Recruitment Agencies sector
Scenario: Significant capability / High friction
"""

import openpyxl
from collections import defaultdict

WB_PATH = "jobs-data-v3.xlsx"

# ── Load workbook (read-only, data_only) ─────────────────────────────────────
wb = openpyxl.load_workbook(WB_PATH, data_only=True, read_only=True)
ws = wb["5 Results"]

# Column indices (1-based) from header inspection
COL = {
    "soc":         1,
    "title":       2,
    "sector":      3,
    "occ_group":   4,
    "emp_k":       5,
    "wage":        6,
    "tc_adj_mod":  7,
    "tc_adj_sig":  8,
    "w":           9,
    "a_mod":      10,
    "a_sig":      11,
    "S_mod":      12,
    "S_sig":      13,
    "d_max":      14,
    "E":          15,
    "T_18mo_high":17,
    "R_high":     19,
    "d_sig_high": 23,
    "disp_K":     27,
}

SECTOR = "Staffing & Recruitment Agencies"

# ── Read all rows, filter to Staffing sector ─────────────────────────────────
rows = []
all_d_max = []
all_sector_rows = defaultdict(list)

first = True
for row in ws.iter_rows(min_row=1, values_only=True):
    if first:
        first = False
        continue  # skip header
    soc      = row[COL["soc"]-1]
    if soc is None:
        continue
    title    = row[COL["title"]-1]
    sector   = row[COL["sector"]-1]
    occ_grp  = row[COL["occ_group"]-1]
    emp_k    = row[COL["emp_k"]-1] or 0
    wage     = row[COL["wage"]-1] or 0
    tc_mod   = row[COL["tc_adj_mod"]-1] or 0
    tc_sig   = row[COL["tc_adj_sig"]-1] or 0
    w        = row[COL["w"]-1] or 0
    a_mod    = row[COL["a_mod"]-1] or 0
    a_sig    = row[COL["a_sig"]-1] or 0
    S_mod    = row[COL["S_mod"]-1] or 0
    S_sig    = row[COL["S_sig"]-1] or 0
    d_max    = row[COL["d_max"]-1] or 0
    E        = row[COL["E"]-1] or 0
    T_high   = row[COL["T_18mo_high"]-1] or 0
    R_high   = row[COL["R_high"]-1] or 0
    d_sig_h  = row[COL["d_sig_high"]-1] or 0
    disp_k   = row[COL["disp_K"]-1] or 0

    rec = {
        "soc": soc, "title": title, "sector": sector, "occ_group": occ_grp,
        "emp_k": emp_k, "wage": wage,
        "tc_adj_mod": tc_mod, "tc_adj_sig": tc_sig, "w": w,
        "a_mod": a_mod, "a_sig": a_sig, "S_mod": S_mod, "S_sig": S_sig,
        "d_max": d_max, "E": E, "T_high": T_high, "R_high": R_high,
        "d_sig_high": d_sig_h, "disp_k": disp_k,
    }

    all_d_max.append(d_max)
    all_sector_rows[sector].append(rec)

    if sector == SECTOR:
        rows.append(rec)

wb.close()

# Sort by displaced K descending
rows.sort(key=lambda r: r["disp_k"], reverse=True)

n_jobs = len(rows)
total_emp = sum(r["emp_k"] for r in rows)
total_disp = sum(r["disp_k"] for r in rows)
avg_rate = (total_disp / total_emp * 100) if total_emp else 0

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1: Sector Overview
# ══════════════════════════════════════════════════════════════════════════════
print("=" * 120)
print(f"  DEEP DIVE: {SECTOR}")
print(f"  Scenario: Significant Capability / High Friction")
print("=" * 120)
print()
print(f"  Jobs (SOCs) in sector:    {n_jobs}")
print(f"  Total employment:         {total_emp:,.1f} K")
print(f"  Total displaced:          {total_disp:,.1f} K")
print(f"  Sector displacement rate: {avg_rate:.1f}%")
print(f"  d_max:                    {rows[0]['d_max']:.4f}  (highest of all 21 sectors)")
print()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2: All Jobs — sorted by displaced K
# ══════════════════════════════════════════════════════════════════════════════
print("─" * 120)
print("  ALL JOBS — sorted by Displaced K (sig/high) descending")
print("─" * 120)
hdr = (f"{'SOC':<10} {'Job Title':<44} {'Occ Group':<22} "
       f"{'Emp K':>7} {'Disp K':>7} {'Rate%':>6} "
       f"{'w':>5} {'a_sig':>6} {'S_sig':>6}")
print(hdr)
print("-" * 120)

for r in rows:
    rate = (r["disp_k"] / r["emp_k"] * 100) if r["emp_k"] else 0
    line = (f"{r['soc']:<10} {r['title'][:43]:<44} {r['occ_group'][:21]:<22} "
            f"{r['emp_k']:>7.1f} {r['disp_k']:>7.2f} {rate:>5.1f}% "
            f"{r['w']:>5.2f} {r['a_sig']:>6.4f} {r['S_sig']:>6.4f}")
    print(line)

print("-" * 120)
print(f"{'TOTAL':<10} {'':<44} {'':<22} "
      f"{total_emp:>7.1f} {total_disp:>7.2f} {avg_rate:>5.1f}%")
print()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3: Subtotals by Occupation Group
# ══════════════════════════════════════════════════════════════════════════════
print("─" * 120)
print("  SUBTOTALS BY OCCUPATION GROUP")
print("─" * 120)

grp_data = defaultdict(lambda: {"emp": 0, "disp": 0, "count": 0, "wages": []})
for r in rows:
    g = r["occ_group"]
    grp_data[g]["emp"] += r["emp_k"]
    grp_data[g]["disp"] += r["disp_k"]
    grp_data[g]["count"] += 1
    grp_data[g]["wages"].append(r["wage"])

grp_sorted = sorted(grp_data.items(), key=lambda x: x[1]["disp"], reverse=True)

print(f"{'Occ Group':<30} {'SOCs':>5} {'Emp K':>8} {'Disp K':>8} {'Rate%':>7} {'Avg Wage':>10}")
print("-" * 75)
for g, d in grp_sorted:
    rate = (d["disp"] / d["emp"] * 100) if d["emp"] else 0
    avg_w = sum(d["wages"]) / len(d["wages"]) if d["wages"] else 0
    print(f"{g:<30} {d['count']:>5} {d['emp']:>8.1f} {d['disp']:>8.2f} {rate:>6.1f}% {avg_w:>10,.0f}")
print("-" * 75)
print(f"{'TOTAL':<30} {n_jobs:>5} {total_emp:>8.1f} {total_disp:>8.2f} {avg_rate:>6.1f}%")
print()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4: d_max Amplification Analysis
# ══════════════════════════════════════════════════════════════════════════════
print("─" * 120)
print("  d_max AMPLIFICATION ANALYSIS")
print("─" * 120)

d_max_staffing = rows[0]["d_max"]
all_d_max_unique = sorted(set(all_d_max))
median_idx = len(all_d_max_unique) // 2
median_d_max = sorted(all_d_max_unique)[median_idx]

# Collect all unique sector d_max values
sector_dmax = {}
for sector, srecs in all_sector_rows.items():
    if srecs:
        sector_dmax[sector] = srecs[0]["d_max"]
sector_dmax_sorted = sorted(sector_dmax.items(), key=lambda x: x[1], reverse=True)

print(f"\n  d_max by sector (all 21):")
print(f"  {'Sector':<42} {'d_max':>8}")
print(f"  {'-'*52}")
for s, dm in sector_dmax_sorted:
    marker = "  ◀ THIS SECTOR" if s == SECTOR else ""
    print(f"  {s:<42} {dm:>8.4f}{marker}")

median_d_max_val = sorted(sector_dmax.values())[len(sector_dmax) // 2]
print(f"\n  Staffing d_max:  {d_max_staffing:.4f}")
print(f"  Median d_max:    {median_d_max_val:.4f}")
print(f"  Ratio:           {d_max_staffing / median_d_max_val:.2f}x")
print()

# Counterfactual: what if Staffing had median d_max?
print(f"  COUNTERFACTUAL: What if Staffing had the median d_max ({median_d_max_val:.4f})?")
print(f"  {'Job Title':<44} {'Actual K':>9} {'Counter K':>10} {'Diff K':>8} {'Diff%':>7}")
print(f"  {'-'*82}")

total_counter = 0
for r in rows:
    # d_sig_high = d_max * S_sig * E * T_high * R_high
    # Counterfactual = (median_d_max / actual_d_max) * actual_displaced
    if d_max_staffing > 0:
        counter_disp = r["disp_k"] * (median_d_max_val / d_max_staffing)
    else:
        counter_disp = 0
    diff = r["disp_k"] - counter_disp
    diff_pct = (diff / r["disp_k"] * 100) if r["disp_k"] else 0
    total_counter += counter_disp
    print(f"  {r['title'][:43]:<44} {r['disp_k']:>9.2f} {counter_disp:>10.2f} {diff:>8.2f} {diff_pct:>6.1f}%")

diff_total = total_disp - total_counter
diff_pct_total = (diff_total / total_disp * 100) if total_disp else 0
print(f"  {'-'*82}")
print(f"  {'TOTAL':<44} {total_disp:>9.2f} {total_counter:>10.2f} {diff_total:>8.2f} {diff_pct_total:>6.1f}%")
print()
print(f"  --> With the median d_max, Staffing displacement would drop from "
      f"{total_disp:,.1f}K to {total_counter:,.1f}K")
print(f"      a reduction of {diff_total:,.1f}K ({diff_pct_total:.1f}%)")
print(f"      The high d_max accounts for {diff_total:,.1f}K of excess displacement")
print()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5: Full Pipeline — Top 5 Jobs
# ══════════════════════════════════════════════════════════════════════════════
print("─" * 120)
print("  FULL DISPLACEMENT PIPELINE — Top 5 Jobs by Displaced K")
print("─" * 120)

top5 = rows[:5]
for i, r in enumerate(top5, 1):
    # Recompute to show the pipeline
    tc = r["tc_adj_sig"]
    w = r["w"]
    a = tc * w
    # S(a) = a^0.8 / (a^0.8 + (1-a)^0.8)
    if a > 0 and a < 1:
        S = a**0.8 / (a**0.8 + (1 - a)**0.8)
    elif a >= 1:
        S = 1.0
    else:
        S = 0.0
    d = r["d_max"] * S * r["E"] * r["T_high"] * r["R_high"]
    disp_k = d * r["emp_k"]

    rate = (r["disp_k"] / r["emp_k"] * 100) if r["emp_k"] else 0

    print(f"\n  #{i}  {r['soc']}  {r['title']}")
    print(f"  {'─'*90}")
    print(f"  Employment:     {r['emp_k']:,.1f} K          Median wage: ${r['wage']:,.0f}")
    print(f"  Occ group:      {r['occ_group']}")
    print()
    print(f"  STEP 1: Task Coverage → tc_adj_sig")
    print(f"    tc_adj_sig = {tc:.4f}")
    print()
    print(f"  STEP 2: Workflow Separability → w")
    print(f"    w = {w:.2f}")
    print()
    print(f"  STEP 3: Job Autonomy  a = tc_adj × w")
    print(f"    a_sig = {tc:.4f} × {w:.2f} = {a:.4f}")
    print(f"    (workbook a_sig = {r['a_sig']:.4f})")
    print()
    print(f"  STEP 4: Sigmoid Transform  S(a) = a^0.8 / (a^0.8 + (1-a)^0.8)")
    print(f"    S({a:.4f}) = {a:.4f}^0.8 / ({a:.4f}^0.8 + {1-a:.4f}^0.8)")
    print(f"    S_sig = {S:.4f}")
    print(f"    (workbook S_sig = {r['S_sig']:.4f})")
    print()
    print(f"  STEP 5: Displacement Rate  d = d_max × S × E × T × R")
    print(f"    d_max    = {r['d_max']:.4f}   (JOLTS-based, highest sector)")
    print(f"    E        = {r['E']:.4f}   (employer readiness)")
    print(f"    T_18mo   = {r['T_high']:.4f}   (technology timeline, high friction)")
    print(f"    R_high   = {r['R_high']:.4f}   (regulatory friction)")
    print(f"    d_sig_high = {r['d_max']:.4f} × {S:.4f} × {r['E']:.4f} × {r['T_high']:.4f} × {r['R_high']:.4f}")
    print(f"             = {d:.4f}  ({d*100:.2f}%)")
    print(f"    (workbook d_sig_high = {r['d_sig_high']:.4f})")
    print()
    print(f"  STEP 6: Displaced Workers  disp_K = d × Employment")
    print(f"    disp_K = {d:.4f} × {r['emp_k']:.1f} = {disp_k:.2f} K")
    print(f"    (workbook displaced_K = {r['disp_k']:.2f} K)")
    print()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6: Summary Statistics
# ══════════════════════════════════════════════════════════════════════════════
print("─" * 120)
print("  SUMMARY STATISTICS")
print("─" * 120)

# Sector comparison
print(f"\n  Staffing vs. All Sectors:")
all_sector_totals = []
for sector, srecs in all_sector_rows.items():
    s_emp = sum(r["emp_k"] for r in srecs)
    s_disp = sum(r["disp_k"] for r in srecs)
    s_rate = (s_disp / s_emp * 100) if s_emp else 0
    all_sector_totals.append((sector, s_emp, s_disp, s_rate))

all_sector_totals.sort(key=lambda x: x[3], reverse=True)
print(f"\n  {'Sector':<42} {'Emp K':>8} {'Disp K':>8} {'Rate%':>7}")
print(f"  {'-'*67}")
for s, emp, disp, rate in all_sector_totals:
    marker = "  ◀" if s == SECTOR else ""
    print(f"  {s:<42} {emp:>8.1f} {disp:>8.1f} {rate:>6.1f}%{marker}")

grand_emp = sum(x[1] for x in all_sector_totals)
grand_disp = sum(x[2] for x in all_sector_totals)
grand_rate = (grand_disp / grand_emp * 100) if grand_emp else 0
print(f"  {'-'*67}")
print(f"  {'TOTAL':<42} {grand_emp:>8.1f} {grand_disp:>8.1f} {grand_rate:>6.1f}%")

staffing_share_emp = total_emp / grand_emp * 100 if grand_emp else 0
staffing_share_disp = total_disp / grand_disp * 100 if grand_disp else 0

print(f"\n  Staffing share of total employment:    {staffing_share_emp:.1f}%")
print(f"  Staffing share of total displacement:  {staffing_share_disp:.1f}%")
print(f"  Displacement concentration ratio:      {staffing_share_disp/staffing_share_emp:.2f}x")

# Distribution of displacement rates within Staffing
rates = [(r["disp_k"] / r["emp_k"] * 100) if r["emp_k"] else 0 for r in rows]
rates.sort()
print(f"\n  Distribution of job-level displacement rates in Staffing:")
print(f"    Min:    {min(rates):.1f}%")
print(f"    25th:   {rates[len(rates)//4]:.1f}%")
print(f"    Median: {rates[len(rates)//2]:.1f}%")
print(f"    75th:   {rates[3*len(rates)//4]:.1f}%")
print(f"    Max:    {max(rates):.1f}%")

# Which jobs have the highest displacement RATES (not absolute)?
print(f"\n  Top 10 by Displacement Rate (%) in Staffing:")
rate_sorted = sorted(rows, key=lambda r: (r["disp_k"]/r["emp_k"]) if r["emp_k"] else 0, reverse=True)
print(f"  {'SOC':<10} {'Job Title':<44} {'Rate%':>6} {'Disp K':>7} {'Emp K':>7}")
print(f"  {'-'*78}")
for r in rate_sorted[:10]:
    rate = (r["disp_k"] / r["emp_k"] * 100) if r["emp_k"] else 0
    print(f"  {r['soc']:<10} {r['title'][:43]:<44} {rate:>5.1f}% {r['disp_k']:>7.2f} {r['emp_k']:>7.1f}")

print()
print("=" * 120)
print("  END OF STAFFING & RECRUITMENT AGENCIES DEEP DIVE")
print("=" * 120)
