#!/usr/bin/env python3
"""
Sector-level displacement analysis — read-only.
Reads the '5 Results' tab from jobs-data-v3.xlsx and aggregates by Sector.
"""

import openpyxl
from collections import defaultdict

WORKBOOK = "jobs-data-v3.xlsx"
SHEET = "5 Results"

# Column indices (1-based) confirmed from header inspection
COL_SECTOR = 3
COL_EMPLOYMENT = 5
COL_D_MOD_HIGH = 21
COL_D_SIG_HIGH = 23
COL_DISPLACED_K_MOD_HIGH = 25
COL_DISPLACED_K_SIG_HIGH = 27


def main():
    wb = openpyxl.load_workbook(WORKBOOK, read_only=True, data_only=True)
    ws = wb[SHEET]

    # Accumulate per-sector
    sectors = defaultdict(lambda: {
        "employment_K": 0.0,
        "displaced_mod_K": 0.0,
        "displaced_sig_K": 0.0,
        "d_rates_mod": [],   # individual SOC displacement rates
        "d_rates_sig": [],
        "soc_count": 0,
    })

    skipped = 0
    total_rows = 0

    for row in ws.iter_rows(min_row=2, values_only=True):
        sector = row[COL_SECTOR - 1]
        if sector is None:
            continue
        total_rows += 1

        emp = row[COL_EMPLOYMENT - 1]
        d_mod = row[COL_D_MOD_HIGH - 1]
        d_sig = row[COL_D_SIG_HIGH - 1]
        dk_mod = row[COL_DISPLACED_K_MOD_HIGH - 1]
        dk_sig = row[COL_DISPLACED_K_SIG_HIGH - 1]

        # Skip rows with missing critical data
        if emp is None:
            skipped += 1
            continue

        s = sectors[sector]
        s["employment_K"] += float(emp)
        s["displaced_mod_K"] += float(dk_mod) if dk_mod is not None else 0.0
        s["displaced_sig_K"] += float(dk_sig) if dk_sig is not None else 0.0
        if d_mod is not None:
            s["d_rates_mod"].append(float(d_mod))
        if d_sig is not None:
            s["d_rates_sig"].append(float(d_sig))
        s["soc_count"] += 1

    wb.close()

    # Build summary rows
    grand_emp = sum(s["employment_K"] for s in sectors.values())
    grand_mod = sum(s["displaced_mod_K"] for s in sectors.values())
    grand_sig = sum(s["displaced_sig_K"] for s in sectors.values())
    grand_socs = sum(s["soc_count"] for s in sectors.values())

    rows = []
    for name, s in sectors.items():
        emp = s["employment_K"]
        emp_share = (emp / grand_emp * 100) if grand_emp else 0
        mod_k = s["displaced_mod_K"]
        sig_k = s["displaced_sig_K"]
        mod_pct = (mod_k / emp * 100) if emp else 0
        sig_pct = (sig_k / emp * 100) if emp else 0
        avg_d_mod = (sum(s["d_rates_mod"]) / len(s["d_rates_mod"]) * 100) if s["d_rates_mod"] else 0
        avg_d_sig = (sum(s["d_rates_sig"]) / len(s["d_rates_sig"]) * 100) if s["d_rates_sig"] else 0
        rows.append({
            "sector": name,
            "employment_K": emp,
            "emp_share": emp_share,
            "mod_K": mod_k,
            "mod_pct": mod_pct,
            "sig_K": sig_k,
            "sig_pct": sig_pct,
            "avg_d_mod": avg_d_mod,
            "avg_d_sig": avg_d_sig,
            "soc_count": s["soc_count"],
        })

    # Sort by displaced_K_sig_high descending
    rows.sort(key=lambda r: r["sig_K"], reverse=True)

    # ── Print main table ──────────────────────────────────────────────
    print("=" * 160)
    print("SECTOR-LEVEL DISPLACEMENT ANALYSIS  (High Friction Scenario)")
    print(f"Source: {WORKBOOK} → '{SHEET}'  |  {total_rows} SOC rows read, {skipped} skipped")
    print("=" * 160)

    hdr = (
        f"{'Sector':<40s} {'Emp(K)':>8s} {'Emp%':>6s} │ "
        f"{'Mod(K)':>8s} {'Mod%':>6s} {'AvgD%':>6s} │ "
        f"{'Sig(K)':>8s} {'Sig%':>6s} {'AvgD%':>6s} │ "
        f"{'SOCs':>5s}"
    )
    print(hdr)
    print("─" * 160)

    for r in rows:
        line = (
            f"{r['sector']:<40s} {r['employment_K']:>8.1f} {r['emp_share']:>5.1f}% │ "
            f"{r['mod_K']:>8.1f} {r['mod_pct']:>5.2f}% {r['avg_d_mod']:>5.2f}% │ "
            f"{r['sig_K']:>8.1f} {r['sig_pct']:>5.2f}% {r['avg_d_sig']:>5.2f}% │ "
            f"{r['soc_count']:>5d}"
        )
        print(line)

    # Grand totals
    print("─" * 160)
    grand_mod_pct = (grand_mod / grand_emp * 100) if grand_emp else 0
    grand_sig_pct = (grand_sig / grand_emp * 100) if grand_emp else 0
    all_d_mod = [d for s in sectors.values() for d in s["d_rates_mod"]]
    all_d_sig = [d for s in sectors.values() for d in s["d_rates_sig"]]
    avg_all_mod = (sum(all_d_mod) / len(all_d_mod) * 100) if all_d_mod else 0
    avg_all_sig = (sum(all_d_sig) / len(all_d_sig) * 100) if all_d_sig else 0

    total_line = (
        f"{'GRAND TOTAL':<40s} {grand_emp:>8.1f} {'100.0%':>6s} │ "
        f"{grand_mod:>8.1f} {grand_mod_pct:>5.2f}% {avg_all_mod:>5.2f}% │ "
        f"{grand_sig:>8.1f} {grand_sig_pct:>5.2f}% {avg_all_sig:>5.2f}% │ "
        f"{grand_socs:>5d}"
    )
    print(total_line)
    print("=" * 160)

    # ── Highest / Lowest displacement RATES ───────────────────────────
    print()
    print("=" * 100)
    print("DISPLACEMENT RATE RANKINGS  (sector-level displaced_K / employment_K)")
    print("=" * 100)

    # By moderate rate
    by_mod_rate = sorted(rows, key=lambda r: r["mod_pct"], reverse=True)
    print()
    print("── MODERATE CAPABILITY — Highest displacement rates ──")
    for i, r in enumerate(by_mod_rate[:5], 1):
        print(f"  {i}. {r['sector']:<40s}  {r['mod_pct']:>5.2f}%  ({r['mod_K']:.1f}K of {r['employment_K']:.1f}K)")
    print()
    print("── MODERATE CAPABILITY — Lowest displacement rates ──")
    for i, r in enumerate(by_mod_rate[-5:], 1):
        print(f"  {i}. {r['sector']:<40s}  {r['mod_pct']:>5.2f}%  ({r['mod_K']:.1f}K of {r['employment_K']:.1f}K)")

    # By significant rate
    by_sig_rate = sorted(rows, key=lambda r: r["sig_pct"], reverse=True)
    print()
    print("── SIGNIFICANT CAPABILITY — Highest displacement rates ──")
    for i, r in enumerate(by_sig_rate[:5], 1):
        print(f"  {i}. {r['sector']:<40s}  {r['sig_pct']:>5.2f}%  ({r['sig_K']:.1f}K of {r['employment_K']:.1f}K)")
    print()
    print("── SIGNIFICANT CAPABILITY — Lowest displacement rates ──")
    for i, r in enumerate(by_sig_rate[-5:], 1):
        print(f"  {i}. {r['sector']:<40s}  {r['sig_pct']:>5.2f}%  ({r['sig_K']:.1f}K of {r['employment_K']:.1f}K)")

    # ── Concentration analysis ────────────────────────────────────────
    print()
    print("=" * 100)
    print("CONCENTRATION ANALYSIS")
    print("=" * 100)
    cumul_sig = 0.0
    print()
    print("Cumulative share of SIGNIFICANT displaced workers (sorted by sig displaced K desc):")
    for r in rows:
        cumul_sig += r["sig_K"]
        pct = cumul_sig / grand_sig * 100 if grand_sig else 0
        bar = "█" * int(pct / 2)
        print(f"  {r['sector']:<40s}  {r['sig_K']:>7.1f}K  cumul {pct:>5.1f}%  {bar}")

    print()
    # How many sectors account for 50% / 80% of displacement?
    cumul = 0.0
    for i, r in enumerate(rows, 1):
        cumul += r["sig_K"]
        if cumul >= grand_sig * 0.5:
            print(f"Top {i} sector(s) account for 50% of significant displacement ({cumul:.1f}K / {grand_sig:.1f}K)")
            break
    cumul = 0.0
    for i, r in enumerate(rows, 1):
        cumul += r["sig_K"]
        if cumul >= grand_sig * 0.8:
            print(f"Top {i} sector(s) account for 80% of significant displacement ({cumul:.1f}K / {grand_sig:.1f}K)")
            break

    # ── Size vs Rate quadrant ─────────────────────────────────────────
    print()
    print("=" * 100)
    print("SIZE vs RATE QUADRANT  (sig scenario)")
    print(f"  Median employment share: {sorted([r['emp_share'] for r in rows])[len(rows)//2]:.1f}%")
    med_rate = sorted([r['sig_pct'] for r in rows])[len(rows)//2]
    med_emp = sorted([r['emp_share'] for r in rows])[len(rows)//2]
    print(f"  Median displacement rate: {med_rate:.2f}%")
    print("=" * 100)
    print()
    print("  HIGH employment, HIGH displacement rate (most impactful):")
    for r in rows:
        if r["emp_share"] >= med_emp and r["sig_pct"] >= med_rate:
            print(f"    • {r['sector']:<40s}  emp={r['emp_share']:.1f}%  rate={r['sig_pct']:.2f}%")
    print()
    print("  HIGH employment, LOW displacement rate (large but resilient):")
    for r in rows:
        if r["emp_share"] >= med_emp and r["sig_pct"] < med_rate:
            print(f"    • {r['sector']:<40s}  emp={r['emp_share']:.1f}%  rate={r['sig_pct']:.2f}%")
    print()
    print("  LOW employment, HIGH displacement rate (niche but vulnerable):")
    for r in rows:
        if r["emp_share"] < med_emp and r["sig_pct"] >= med_rate:
            print(f"    • {r['sector']:<40s}  emp={r['emp_share']:.1f}%  rate={r['sig_pct']:.2f}%")
    print()
    print("  LOW employment, LOW displacement rate (least concern):")
    for r in rows:
        if r["emp_share"] < med_emp and r["sig_pct"] < med_rate:
            print(f"    • {r['sector']:<40s}  emp={r['emp_share']:.1f}%  rate={r['sig_pct']:.2f}%")


if __name__ == "__main__":
    main()
