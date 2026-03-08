#!/usr/bin/env python3
"""
Review of TOP 40 jobs by displaced_K_sig_high from 5 Results tab.
Read-only analysis — does NOT modify the workbook.
"""

import openpyxl

WORKBOOK = "jobs-data-v3.xlsx"
SHEET = "5 Results"

# Industries for friction sanity checks (using actual workbook sector names)
OLD_LUMBERING = {"Government & Public Administration", "Education & Academia",
                 "Healthcare & Life Sciences", "Manufacturing"}
FAST_MOVING = {"Technology & Software", "Management Consulting Firms",
               "Advertising & PR Agencies"}
CONSERVATIVE = {"Government & Public Administration", "Education & Academia",
                "Healthcare & Life Sciences", "Manufacturing",
                "Energy & Utilities"}

def main():
    wb = openpyxl.load_workbook(WORKBOOK, read_only=True, data_only=True)
    ws = wb[SHEET]

    rows = []
    for r in ws.iter_rows(min_row=2, max_col=27, values_only=True):
        soc = r[0]
        if not soc or not str(soc).strip():
            continue
        rows.append({
            "soc":        str(r[0]).strip(),
            "title":      str(r[1]).strip() if r[1] else "",
            "sector":     str(r[2]).strip() if r[2] else "",
            "occ_group":  str(r[3]).strip() if r[3] else "",
            "emp_k":      float(r[4]) if r[4] is not None else 0.0,
            "median_wage": float(r[5]) if r[5] is not None else 0.0,
            "tc_adj_mod": float(r[6]) if r[6] is not None else 0.0,
            "tc_adj_sig": float(r[7]) if r[7] is not None else 0.0,
            "w":          float(r[8]) if r[8] is not None else 0.0,
            "a_mod":      float(r[9]) if r[9] is not None else 0.0,
            "a_sig":      float(r[10]) if r[10] is not None else 0.0,
            "S_mod":      float(r[11]) if r[11] is not None else 0.0,
            "S_sig":      float(r[12]) if r[12] is not None else 0.0,
            "d_max":      float(r[13]) if r[13] is not None else 0.0,
            "E":          float(r[14]) if r[14] is not None else 0.0,
            "T_18mo_high": float(r[16]) if r[16] is not None else 0.0,
            "R_high":     float(r[18]) if r[18] is not None else 0.0,
            "d_sig_high": float(r[22]) if r[22] is not None else 0.0,
            "disp_k":     float(r[26]) if r[26] is not None else 0.0,
        })
    wb.close()

    total_rows = len(rows)
    total_disp_k = sum(r["disp_k"] for r in rows)
    total_emp_k = sum(r["emp_k"] for r in rows)

    print(f"{'='*140}")
    print(f"TOP 40 JOBS BY DISPLACED_K_SIG_HIGH — DETAILED PIPELINE REVIEW")
    print(f"{'='*140}")
    print(f"Total SOCs: {total_rows}  |  Total Employment: {total_emp_k:,.0f}K"
          f"  |  Total Displaced (sig, high friction): {total_disp_k:,.1f}K")
    print(f"{'='*140}\n")

    # Sort by displaced_K_sig_high descending
    rows.sort(key=lambda x: x["disp_k"], reverse=True)
    top40 = rows[:40]

    # ── Table Header ──
    hdr = (f"{'#':>3} {'SOC':<10} {'Title':<40} {'Sector':<25} {'OccGrp':<25} "
           f"{'Emp_K':>7} {'tc_sig':>6} {'w':>5} {'a_sig':>5} {'S_sig':>5} "
           f"{'d_max':>5} {'E':>5} {'T_18':>5} {'R':>5} {'Fric':>5} "
           f"{'d_sig%':>6} {'Disp_K':>7} {'CumK':>8} {'Cum%':>5}")
    print(hdr)
    print("-" * len(hdr))

    cum_k = 0.0
    flagged = []

    for i, r in enumerate(top40, 1):
        title_short = r["title"][:40]
        sector_short = r["sector"][:25]
        occ_short = r["occ_group"][:25]
        friction_discount = r["E"] * r["T_18mo_high"] * r["R_high"]
        cum_k += r["disp_k"]
        cum_pct = (cum_k / total_disp_k * 100) if total_disp_k > 0 else 0

        print(f"{i:>3} {r['soc']:<10} {title_short:<40} {sector_short:<25} {occ_short:<25} "
              f"{r['emp_k']:>7.1f} {r['tc_adj_sig']:>6.3f} {r['w']:>5.2f} "
              f"{r['a_sig']:>5.3f} {r['S_sig']:>5.3f} {r['d_max']:>5.3f} "
              f"{r['E']:>5.2f} {r['T_18mo_high']:>5.3f} {r['R_high']:>5.3f} "
              f"{friction_discount:>5.3f} "
              f"{r['d_sig_high']*100:>6.2f} {r['disp_k']:>7.1f} "
              f"{cum_k:>8.1f} {cum_pct:>5.1f}")

        # ── Flag suspicious friction values ──
        flags = []
        sector = r["sector"]

        # Old/lumbering with high friction discount (too permissive?)
        if sector in OLD_LUMBERING and friction_discount > 0.3:
            flags.append(f"HIGH friction discount ({friction_discount:.3f}) in conservative sector '{sector}' — possibly too permissive")

        # Fast-moving with low friction discount (too restrictive?)
        if sector in FAST_MOVING and friction_discount < 0.15:
            flags.append(f"LOW friction discount ({friction_discount:.3f}) in fast-moving sector '{sector}' — possibly too restrictive")

        # E=1.0 in conservative sector
        if r["E"] == 1.0 and sector in CONSERVATIVE:
            flags.append(f"E=1.00 (full enterprise readiness) in conservative sector '{sector}' — is this realistic?")

        if flags:
            flagged.append((i, r, friction_discount, flags))

    # ── Cumulative concentration analysis ──
    print(f"\n{'='*140}")
    print("CUMULATIVE CONCENTRATION ANALYSIS")
    print(f"{'='*140}")
    cum_k = 0.0
    milestones = [5, 10, 15, 20, 25, 30, 35, 40]
    for i, r in enumerate(top40, 1):
        cum_k += r["disp_k"]
        if i in milestones:
            cum_pct = cum_k / total_disp_k * 100
            print(f"  Top {i:>2} jobs: {cum_k:>8.1f}K displaced  ({cum_pct:>5.1f}% of total {total_disp_k:,.1f}K)")

    # ── Friction discount distribution for top 40 ──
    print(f"\n{'='*140}")
    print("FRICTION DISCOUNT (E × T_18mo × R) DISTRIBUTION — TOP 40")
    print(f"{'='*140}")
    frictions = [(r["E"] * r["T_18mo_high"] * r["R_high"], r) for r in top40]
    frictions.sort(key=lambda x: x[0], reverse=True)

    print(f"\n  {'Range':<25} {'Count':>5}  Jobs")
    print(f"  {'-'*80}")
    brackets = [
        (0.4, 1.01, ">= 0.40 (very permissive)"),
        (0.3, 0.4,  "0.30 – 0.39"),
        (0.2, 0.3,  "0.20 – 0.29"),
        (0.15, 0.2, "0.15 – 0.19"),
        (0.10, 0.15,"0.10 – 0.14"),
        (0.0, 0.10, "< 0.10 (very restrictive)"),
    ]
    for lo, hi, label in brackets:
        in_bracket = [(f, r) for f, r in frictions if lo <= f < hi]
        names = ", ".join(r["title"][:30] for _, r in in_bracket[:5])
        if len(in_bracket) > 5:
            names += f", ... (+{len(in_bracket)-5} more)"
        print(f"  {label:<25} {len(in_bracket):>5}  {names}")

    # ── Flagged jobs ──
    print(f"\n{'='*140}")
    print("FLAGGED JOBS — FRICTION VALUES WORTH REVIEWING")
    print(f"{'='*140}")
    if not flagged:
        print("  No jobs flagged.")
    else:
        for rank, r, fd, flags in flagged:
            print(f"\n  #{rank:>2} {r['soc']} {r['title'][:50]}")
            print(f"      Sector: {r['sector']}  |  E={r['E']:.2f}  T={r['T_18mo_high']:.3f}  R={r['R_high']:.3f}  |  Friction discount={fd:.3f}")
            print(f"      d_sig_high={r['d_sig_high']*100:.2f}%  |  Displaced={r['disp_k']:.1f}K  |  Emp={r['emp_k']:.1f}K")
            for f in flags:
                print(f"      >>> FLAG: {f}")

    # ── Summary statistics ──
    print(f"\n{'='*140}")
    print("SUMMARY STATISTICS — TOP 40")
    print(f"{'='*140}")
    top40_disp = sum(r["disp_k"] for r in top40)
    top40_emp = sum(r["emp_k"] for r in top40)
    avg_d_sig = sum(r["d_sig_high"] for r in top40) / 40
    avg_friction = sum(r["E"] * r["T_18mo_high"] * r["R_high"] for r in top40) / 40
    avg_S = sum(r["S_sig"] for r in top40) / 40
    avg_a = sum(r["a_sig"] for r in top40) / 40
    avg_dmax = sum(r["d_max"] for r in top40) / 40

    print(f"  Total displaced (top 40):       {top40_disp:>8.1f}K  ({top40_disp/total_disp_k*100:.1f}% of all)")
    print(f"  Total employment (top 40):      {top40_emp:>8.1f}K  ({top40_emp/total_emp_k*100:.1f}% of all)")
    print(f"  Avg displacement rate (d_sig%):    {avg_d_sig*100:>6.2f}%")
    print(f"  Avg autonomy (a_sig):              {avg_a:>6.3f}")
    print(f"  Avg sigmoid (S_sig):               {avg_S:>6.3f}")
    print(f"  Avg d_max:                         {avg_dmax:>6.3f}")
    print(f"  Avg friction discount (E×T×R):     {avg_friction:>6.3f}")

    # ── Sector breakdown of top 40 ──
    print(f"\n  Sector breakdown (top 40 jobs):")
    sector_counts = {}
    sector_disp = {}
    for r in top40:
        s = r["sector"]
        sector_counts[s] = sector_counts.get(s, 0) + 1
        sector_disp[s] = sector_disp.get(s, 0) + r["disp_k"]
    for s in sorted(sector_disp, key=sector_disp.get, reverse=True):
        print(f"    {s:<30} {sector_counts[s]:>2} jobs  {sector_disp[s]:>8.1f}K displaced")

    # ── Highest-displacement-rate jobs (even if not highest absolute) ──
    print(f"\n{'='*140}")
    print("HIGHEST DISPLACEMENT RATE (d_sig_high%) IN TOP 40 — regardless of employment size")
    print(f"{'='*140}")
    by_rate = sorted(top40, key=lambda x: x["d_sig_high"], reverse=True)
    for i, r in enumerate(by_rate[:15], 1):
        fd = r["E"] * r["T_18mo_high"] * r["R_high"]
        print(f"  {i:>2}. {r['d_sig_high']*100:>6.2f}%  {r['title'][:45]:<45}  "
              f"Emp={r['emp_k']:>6.1f}K  a={r['a_sig']:.3f}  S={r['S_sig']:.3f}  "
              f"d_max={r['d_max']:.3f}  fric={fd:.3f}")

    print(f"\n{'='*140}")
    print("END OF REVIEW")
    print(f"{'='*140}")


if __name__ == "__main__":
    main()
