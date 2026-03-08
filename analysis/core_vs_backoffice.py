#!/usr/bin/env python3
"""Core vs Back-Office displacement analysis across all 21 sectors.

Reads the '5 Results' tab from jobs-data-v3.xlsx and produces:
  1. Full sector table: Core vs Support employment & displacement
  2. Core-only ranking by displaced_K
  3. Back-office dependency ranking
  4. Per-sector detail of Core SOCs
"""

import openpyxl
from collections import defaultdict

WB_PATH = "jobs-data-v3.xlsx"

# ── Load data ──────────────────────────────────────────────────────────────
wb = openpyxl.load_workbook(WB_PATH, read_only=True, data_only=True)
ws = wb["5 Results"]

rows = []
for r in ws.iter_rows(min_row=2, values_only=True):
    soc = r[0]
    if soc is None:
        continue
    rows.append({
        "soc":        r[0],
        "title":      r[1],
        "sector":     r[2],
        "occ_group":  r[3],
        "emp_k":      float(r[4] or 0),
        "d_sig_high": float(r[22] or 0),
        "disp_k":     float(r[26] or 0),
    })
wb.close()

print(f"Loaded {len(rows)} SOC-sector rows\n")

# ── Aggregate by sector ───────────────────────────────────────────────────
sectors = defaultdict(lambda: {
    "core_emp": 0, "core_disp": 0, "core_socs": [],
    "supp_emp": 0, "supp_disp": 0, "supp_socs": [],
})

for r in rows:
    s = sectors[r["sector"]]
    if r["occ_group"] == "Core":
        s["core_emp"]  += r["emp_k"]
        s["core_disp"] += r["disp_k"]
        s["core_socs"].append(r)
    else:
        s["supp_emp"]  += r["emp_k"]
        s["supp_disp"] += r["disp_k"]
        s["supp_socs"].append(r)

# Build summary list
summary = []
for name, s in sectors.items():
    total_emp  = s["core_emp"] + s["supp_emp"]
    total_disp = s["core_disp"] + s["supp_disp"]
    core_rate  = (s["core_disp"] / s["core_emp"] * 100) if s["core_emp"] > 0 else 0
    supp_rate  = (s["supp_disp"] / s["supp_emp"] * 100) if s["supp_emp"] > 0 else 0
    core_share = (s["core_disp"] / total_disp * 100) if total_disp > 0 else 0
    supp_share = (s["supp_disp"] / total_disp * 100) if total_disp > 0 else 0
    summary.append({
        "sector":     name,
        "total_emp":  total_emp,
        "core_emp":   s["core_emp"],
        "supp_emp":   s["supp_emp"],
        "core_disp":  s["core_disp"],
        "supp_disp":  s["supp_disp"],
        "total_disp": total_disp,
        "core_rate":  core_rate,
        "supp_rate":  supp_rate,
        "core_share": core_share,
        "supp_share": supp_share,
        "core_socs":  s["core_socs"],
    })

# ── TABLE 1: Full sector table sorted by total displaced_K desc ──────────
summary.sort(key=lambda x: x["total_disp"], reverse=True)

print("=" * 155)
print("TABLE 1: CORE vs SUPPORT DISPLACEMENT BY SECTOR  (Significant capability, High friction)")
print("=" * 155)
hdr = (f"{'Sector':<35} {'Tot Emp K':>9} {'Core Emp':>9} {'Supp Emp':>9} "
       f"{'Core Dsp':>9} {'Supp Dsp':>9} {'Tot Dsp':>9} "
       f"{'Core %':>7} {'Supp %':>7} {'CoreShr%':>9}")
print(hdr)
print("-" * 155)

tot_emp = tot_core_emp = tot_supp_emp = 0
tot_core_disp = tot_supp_disp = tot_disp = 0

for s in summary:
    print(f"{s['sector']:<35} {s['total_emp']:>9.1f} {s['core_emp']:>9.1f} {s['supp_emp']:>9.1f} "
          f"{s['core_disp']:>9.1f} {s['supp_disp']:>9.1f} {s['total_disp']:>9.1f} "
          f"{s['core_rate']:>6.1f}% {s['supp_rate']:>6.1f}% {s['core_share']:>8.1f}%")
    tot_emp       += s["total_emp"]
    tot_core_emp  += s["core_emp"]
    tot_supp_emp  += s["supp_emp"]
    tot_core_disp += s["core_disp"]
    tot_supp_disp += s["supp_disp"]
    tot_disp      += s["total_disp"]

print("-" * 155)
agg_core_rate  = (tot_core_disp / tot_core_emp * 100) if tot_core_emp > 0 else 0
agg_supp_rate  = (tot_supp_disp / tot_supp_emp * 100) if tot_supp_emp > 0 else 0
agg_core_share = (tot_core_disp / tot_disp * 100) if tot_disp > 0 else 0
print(f"{'TOTAL':<35} {tot_emp:>9.1f} {tot_core_emp:>9.1f} {tot_supp_emp:>9.1f} "
      f"{tot_core_disp:>9.1f} {tot_supp_disp:>9.1f} {tot_disp:>9.1f} "
      f"{agg_core_rate:>6.1f}% {agg_supp_rate:>6.1f}% {agg_core_share:>8.1f}%")

# ── TABLE 2: Core-only ranking ───────────────────────────────────────────
print("\n\n" + "=" * 100)
print("TABLE 2: CORE-ONLY RANKING  (Sectors by Core displaced_K descending)")
print("=" * 100)
core_ranked = sorted(summary, key=lambda x: x["core_disp"], reverse=True)
print(f"{'Rank':<5} {'Sector':<35} {'Core Emp K':>10} {'Core Dsp K':>11} {'Core Rate%':>11} {'# Core SOCs':>12}")
print("-" * 100)
for i, s in enumerate(core_ranked, 1):
    n_socs = len(s["core_socs"])
    print(f"{i:<5} {s['sector']:<35} {s['core_emp']:>10.1f} {s['core_disp']:>11.1f} "
          f"{s['core_rate']:>10.1f}% {n_socs:>12}")

# ── TABLE 3: Back-office dependency ranking ──────────────────────────────
print("\n\n" + "=" * 100)
print("TABLE 3: BACK-OFFICE DEPENDENCY  (Sectors by Support share of displacement, descending)")
print("=" * 100)
bo_ranked = sorted(summary, key=lambda x: x["supp_share"], reverse=True)
print(f"{'Rank':<5} {'Sector':<35} {'Supp Dsp K':>11} {'Tot Dsp K':>10} {'SuppShr%':>9} {'CoreShr%':>9}")
print("-" * 100)
for i, s in enumerate(bo_ranked, 1):
    print(f"{i:<5} {s['sector']:<35} {s['supp_disp']:>11.1f} {s['total_disp']:>10.1f} "
          f"{s['supp_share']:>8.1f}% {s['core_share']:>8.1f}%")

# ── TABLE 4: Per-sector Core SOC detail ──────────────────────────────────
print("\n\n" + "=" * 140)
print("TABLE 4: CORE SOC DETAIL BY SECTOR")
print("=" * 140)

for s in summary:  # already sorted by total_disp desc
    core = s["core_socs"]
    if not core:
        print(f"\n--- {s['sector']} --- (no Core SOCs assigned)")
        continue
    core_sorted = sorted(core, key=lambda x: x["disp_k"], reverse=True)
    print(f"\n--- {s['sector']} ---  Core Employment: {s['core_emp']:.1f}K | Core Displaced: {s['core_disp']:.1f}K | Core Rate: {s['core_rate']:.1f}%")
    print(f"  {'SOC':<10} {'Title':<55} {'Emp K':>8} {'d_sig_hi':>9} {'Dsp K':>8}")
    print(f"  {'-'*10} {'-'*55} {'-'*8} {'-'*9} {'-'*8}")
    for c in core_sorted:
        print(f"  {c['soc']:<10} {c['title'][:55]:<55} {c['emp_k']:>8.1f} {c['d_sig_high']:>8.2%} {c['disp_k']:>8.1f}")

print("\n\nDone.")
