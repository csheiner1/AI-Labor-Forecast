#!/usr/bin/env python3
"""
Breakdown of SIGNIFICANT capability, HIGH friction scenario
from the 5 Results tab of jobs-data-v3.xlsx.

Read-only -- does not modify the workbook.
"""

import openpyxl
from collections import defaultdict

WB_PATH = "jobs-data-v3.xlsx"
SHEET = "5 Results"


def load_data():
    wb = openpyxl.load_workbook(WB_PATH, read_only=True, data_only=True)
    ws = wb[SHEET]
    rows = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        soc = row[0]  # col 1: SOC_Code
        if not soc:
            continue
        title   = str(row[1] or "")
        sector  = str(row[2] or "")
        occ_grp = str(row[3] or "")
        emp_k   = float(row[4] or 0)   # col 5: Employment_2024_K
        d_rate  = float(row[22] or 0)   # col 23: d_sig_high
        disp_k  = float(row[26] or 0)   # col 27: displaced_K_sig_high
        rows.append({
            "soc": soc, "title": title, "sector": sector, "occ_group": occ_grp,
            "emp_k": emp_k, "d_rate": d_rate, "disp_k": disp_k,
        })
    wb.close()
    return rows


def print_sector_table(rows):
    buckets = defaultdict(lambda: {"emp_k": 0.0, "disp_k": 0.0})
    for r in rows:
        buckets[r["sector"]]["emp_k"]  += r["emp_k"]
        buckets[r["sector"]]["disp_k"] += r["disp_k"]

    total_emp  = sum(b["emp_k"]  for b in buckets.values())
    total_disp = sum(b["disp_k"] for b in buckets.values())
    items = sorted(buckets.items(), key=lambda x: x[1]["disp_k"], reverse=True)

    W = 95
    print("=" * W)
    print("TABLE 1: DISPLACEMENT BY SECTOR  (Significant capability, High friction)")
    print("=" * W)
    print(f"{'Sector':<32s} {'Employment (K)':>14s} {'Displaced (K)':>14s} {'Rate (%)':>10s} {'Share (%)':>10s}")
    print("-" * W)

    for sector, b in items:
        rate  = (b["disp_k"] / b["emp_k"] * 100) if b["emp_k"] else 0.0
        share = (b["disp_k"] / total_disp * 100) if total_disp else 0.0
        print(f"{sector:<32s} {b['emp_k']:>14.1f} {b['disp_k']:>14.1f} {rate:>10.2f} {share:>10.2f}")

    rate_total = (total_disp / total_emp * 100) if total_emp else 0.0
    print("-" * W)
    print(f"{'TOTAL':<32s} {total_emp:>14.1f} {total_disp:>14.1f} {rate_total:>10.2f} {'100.00':>10s}")
    print("=" * W)
    print()


def print_occ_group_table(rows):
    buckets = defaultdict(lambda: {"emp_k": 0.0, "disp_k": 0.0})
    for r in rows:
        buckets[r["occ_group"]]["emp_k"]  += r["emp_k"]
        buckets[r["occ_group"]]["disp_k"] += r["disp_k"]

    total_emp  = sum(b["emp_k"]  for b in buckets.values())
    total_disp = sum(b["disp_k"] for b in buckets.values())
    items = sorted(buckets.items(), key=lambda x: x[1]["disp_k"], reverse=True)

    W = 95
    print("=" * W)
    print("TABLE 2: DISPLACEMENT BY OCCUPATION GROUP  (Significant capability, High friction)")
    print("=" * W)
    print(f"{'Occupation Group':<32s} {'Employment (K)':>14s} {'Displaced (K)':>14s} {'Rate (%)':>10s} {'Share (%)':>10s}")
    print("-" * W)

    for occ, b in items:
        rate  = (b["disp_k"] / b["emp_k"] * 100) if b["emp_k"] else 0.0
        share = (b["disp_k"] / total_disp * 100) if total_disp else 0.0
        print(f"{occ:<32s} {b['emp_k']:>14.1f} {b['disp_k']:>14.1f} {rate:>10.2f} {share:>10.2f}")

    rate_total = (total_disp / total_emp * 100) if total_emp else 0.0
    print("-" * W)
    print(f"{'TOTAL':<32s} {total_emp:>14.1f} {total_disp:>14.1f} {rate_total:>10.2f} {'100.00':>10s}")
    print("=" * W)
    print()


def print_top30_table(rows):
    total_disp = sum(r["disp_k"] for r in rows)
    top30 = sorted(rows, key=lambda r: r["disp_k"], reverse=True)[:30]

    W = 130
    print("=" * W)
    print("TABLE 3: TOP 30 JOBS BY DISPLACED WORKERS  (Significant capability, High friction)")
    print("=" * W)
    print(f"{'SOC':<10s} {'Job Title':<42s} {'Sector':<22s} {'Occ Group':<22s} "
          f"{'Emp (K)':>9s} {'Disp (K)':>9s} {'Rate (%)':>9s}")
    print("-" * W)

    for r in top30:
        title  = r["title"][:40]
        sector = r["sector"][:20]
        occ    = r["occ_group"][:20]
        rate   = r["d_rate"] * 100
        print(f"{r['soc']:<10s} {title:<42s} {sector:<22s} {occ:<22s} "
              f"{r['emp_k']:>9.1f} {r['disp_k']:>9.1f} {rate:>9.2f}")

    cum_emp  = sum(r["emp_k"]  for r in top30)
    cum_disp = sum(r["disp_k"] for r in top30)
    print("-" * W)
    print(f"{'':10s} {'TOP 30 SUBTOTAL':<42s} {'':22s} {'':22s} "
          f"{cum_emp:>9.1f} {cum_disp:>9.1f} {'':>9s}")
    share = (cum_disp / total_disp * 100) if total_disp else 0.0
    print(f"{'':10s} {f'(= {share:.1f}% of total displaced)':<42s}")
    print("=" * W)


def main():
    rows = load_data()
    print(f"Loaded {len(rows)} job rows from '{SHEET}'\n")
    print_sector_table(rows)
    print_occ_group_table(rows)
    print_top30_table(rows)


if __name__ == "__main__":
    main()
