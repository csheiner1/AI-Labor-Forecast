#!/usr/bin/env python3
"""
Deep-dive analysis of the CONSTRUCTION sector
Scenario: Significant capability / High friction
"""

import openpyxl

# ── Load data ────────────────────────────────────────────────────────────────
wb = openpyxl.load_workbook("jobs-data-v3.xlsx", read_only=True, data_only=True)
ws = wb["5 Results"]

rows = []
for row in ws.iter_rows(min_row=2, values_only=True):
    soc       = row[0]
    if soc is None:
        continue
    title     = row[1]
    sector    = row[2]
    occ_group = row[3]
    emp_k     = row[4]  # Employment_2024_K
    wage      = row[5]  # Median_Wage
    tc_mod    = row[6]
    tc_sig    = row[7]
    w         = row[8]
    a_mod     = row[9]
    a_sig     = row[10]
    s_mod     = row[11]
    s_sig     = row[12]
    d_max     = row[13]
    E         = row[14]
    T_high    = row[16]
    R_high    = row[18]
    d_sig_h   = row[22]
    disp_k    = row[26]  # displaced_K_sig_high

    if sector == "Construction":
        rows.append({
            "soc": soc, "title": title, "occ_group": occ_group,
            "emp_k": emp_k or 0, "wage": wage or 0,
            "tc_sig": tc_sig or 0, "w": w or 0,
            "a_sig": a_sig or 0, "s_sig": s_sig or 0,
            "d_max": d_max or 0, "E": E or 0,
            "T_high": T_high or 0, "R_high": R_high or 0,
            "d_sig_h": d_sig_h or 0, "disp_k": disp_k or 0,
        })

wb.close()

# ── Sort by displaced_K descending ───────────────────────────────────────────
rows.sort(key=lambda r: r["disp_k"], reverse=True)

# ── Classification: physical/trades vs office/admin ──────────────────────────
# Core occupations in Construction are field trades (electricians, carpenters,
# equipment operators, etc.).  The G-prefixed occ groups are support functions.
OFFICE_GROUPS = {
    "G1_Exec_Management", "G3_Finance_Accounting", "G4_IT_Digital",
    "G7_Legal_Compliance", "G9_Admin_Office",
}

def job_type(occ_group):
    return "Office/Admin" if occ_group in OFFICE_GROUPS else "Physical/Trades"

# ── Print all jobs ───────────────────────────────────────────────────────────
print("=" * 130)
print("CONSTRUCTION SECTOR — Significant Capability / High Friction Scenario")
print("=" * 130)

header = (
    f"{'SOC':<12} {'Job Title':<40} {'Occ Group':<22} {'Type':<15} "
    f"{'Emp K':>7} {'Disp K':>7} {'Rate%':>6} {'w':>5} "
    f"{'a_sig':>6} {'S_sig':>6}"
)
print(header)
print("-" * 130)

total_emp = 0
total_disp = 0
for r in rows:
    rate_pct = (r["d_sig_h"] * 100) if r["d_sig_h"] else 0
    jtype = job_type(r["occ_group"])
    print(
        f"{r['soc']:<12} {r['title'][:40]:<40} {r['occ_group'][:22]:<22} {jtype:<15} "
        f"{r['emp_k']:>7.1f} {r['disp_k']:>7.2f} {rate_pct:>6.1f} {r['w']:>5.2f} "
        f"{r['a_sig']:>6.3f} {r['s_sig']:>6.3f}"
    )
    total_emp += r["emp_k"]
    total_disp += r["disp_k"]

print("-" * 130)
print(
    f"{'TOTAL':<12} {'':<40} {'':<22} {'':<15} "
    f"{total_emp:>7.1f} {total_disp:>7.2f} {(total_disp/total_emp*100) if total_emp else 0:>6.1f}"
)

# ── Subtotals by Occ Group ──────────────────────────────────────────────────
print("\n")
print("=" * 100)
print("SUBTOTALS BY OCCUPATION GROUP")
print("=" * 100)

from collections import defaultdict
by_grp = defaultdict(lambda: {"emp": 0, "disp": 0, "count": 0, "type": ""})
for r in rows:
    g = r["occ_group"]
    by_grp[g]["emp"] += r["emp_k"]
    by_grp[g]["disp"] += r["disp_k"]
    by_grp[g]["count"] += 1
    by_grp[g]["type"] = job_type(g)

grp_header = (
    f"{'Occ Group':<26} {'Type':<15} {'Jobs':>5} {'Emp K':>8} "
    f"{'Disp K':>8} {'Rate%':>7} {'% of Sector Disp':>18}"
)
print(grp_header)
print("-" * 100)

for g in sorted(by_grp, key=lambda g: by_grp[g]["disp"], reverse=True):
    d = by_grp[g]
    rate = (d["disp"] / d["emp"] * 100) if d["emp"] else 0
    share = (d["disp"] / total_disp * 100) if total_disp else 0
    print(
        f"{g:<26} {d['type']:<15} {d['count']:>5} {d['emp']:>8.1f} "
        f"{d['disp']:>8.2f} {rate:>7.1f} {share:>17.1f}%"
    )

# ── Office vs Trades summary ────────────────────────────────────────────────
print("\n")
print("=" * 100)
print("PHYSICAL/TRADES vs OFFICE/ADMIN BREAKDOWN")
print("=" * 100)

type_agg = defaultdict(lambda: {"emp": 0, "disp": 0, "count": 0})
for r in rows:
    t = job_type(r["occ_group"])
    type_agg[t]["emp"] += r["emp_k"]
    type_agg[t]["disp"] += r["disp_k"]
    type_agg[t]["count"] += 1

type_header = (
    f"{'Category':<20} {'Jobs':>5} {'Emp K':>8} {'Disp K':>8} "
    f"{'Rate%':>7} {'% of Sector Emp':>16} {'% of Sector Disp':>18}"
)
print(type_header)
print("-" * 100)

for t in ["Office/Admin", "Physical/Trades"]:
    d = type_agg[t]
    rate = (d["disp"] / d["emp"] * 100) if d["emp"] else 0
    emp_share = (d["emp"] / total_emp * 100) if total_emp else 0
    disp_share = (d["disp"] / total_disp * 100) if total_disp else 0
    print(
        f"{t:<20} {d['count']:>5} {d['emp']:>8.1f} {d['disp']:>8.2f} "
        f"{rate:>7.1f} {emp_share:>15.1f}% {disp_share:>17.1f}%"
    )

# ── Friction detail ─────────────────────────────────────────────────────────
print("\n")
print("=" * 100)
print("FRICTION & TIMING COMPONENTS (High Scenario)")
print("=" * 100)

fr_header = (
    f"{'SOC':<12} {'Title':<36} {'d_max':>6} {'E':>6} "
    f"{'T_18mo':>7} {'R':>6} {'d_sig%':>7}"
)
print(fr_header)
print("-" * 100)

for r in rows:
    rate_pct = r["d_sig_h"] * 100
    print(
        f"{r['soc']:<12} {r['title'][:36]:<36} {r['d_max']:>6.3f} {r['E']:>6.3f} "
        f"{r['T_high']:>7.3f} {r['R_high']:>6.3f} {rate_pct:>7.1f}"
    )

# ── Key takeaways ───────────────────────────────────────────────────────────
print("\n")
print("=" * 100)
print("KEY FINDINGS")
print("=" * 100)

office = type_agg["Office/Admin"]
trades = type_agg["Physical/Trades"]
office_rate = (office["disp"] / office["emp"] * 100) if office["emp"] else 0
trades_rate = (trades["disp"] / trades["emp"] * 100) if trades["emp"] else 0
office_disp_share = (office["disp"] / total_disp * 100) if total_disp else 0

# Top 3 displaced jobs
top3 = rows[:3]

print(f"""
1. SECTOR OVERVIEW
   - {len(rows)} SOCs in Construction, {total_emp:.1f}K total employment
   - Total displaced (Sig/High): {total_disp:.2f}K
   - Sector-wide displacement rate: {(total_disp/total_emp*100):.1f}%

2. OFFICE/ADMIN vs PHYSICAL/TRADES
   - Office/Admin: {office['count']} jobs, {office['emp']:.1f}K emp, {office['disp']:.2f}K displaced ({office_rate:.1f}% rate)
   - Physical/Trades: {trades['count']} jobs, {trades['emp']:.1f}K emp, {trades['disp']:.2f}K displaced ({trades_rate:.1f}% rate)
   - Office/Admin accounts for {office_disp_share:.1f}% of sector displacement
   - Displacement IS {'CONCENTRATED' if office_disp_share > 60 else 'NOT concentrated'} in back-office functions
     (office rate {office_rate:.1f}% vs trades rate {trades_rate:.1f}%)

3. TOP 3 DISPLACED OCCUPATIONS
   - {top3[0]['title']}: {top3[0]['disp_k']:.2f}K ({top3[0]['d_sig_h']*100:.1f}%) — {job_type(top3[0]['occ_group'])}
   - {top3[1]['title']}: {top3[1]['disp_k']:.2f}K ({top3[1]['d_sig_h']*100:.1f}%) — {job_type(top3[1]['occ_group'])}
   - {top3[2]['title']}: {top3[2]['disp_k']:.2f}K ({top3[2]['d_sig_h']*100:.1f}%) — {job_type(top3[2]['occ_group'])}

4. WHY TRADES DISPLACEMENT IS {'LOW' if trades_rate < 5 else 'MODERATE' if trades_rate < 10 else 'HIGH'}
   - Physical tasks have low autonomy scores (a_sig) → low S-curve output
   - d_max for Construction: {rows[0]['d_max']:.3f} (turnover ceiling)
   - Even significant AI capability barely moves the needle on hands-on trades
""")
