#!/usr/bin/env python3
"""
Occupation Group-Level Displacement Analysis
=============================================
Reads the '5 Results' tab from jobs-data-v3.xlsx (read-only) and produces:
  1. Aggregated displacement statistics by Occupation Group
  2. Cross-tab: top contributing sectors per Occupation Group
  3. Grand totals
"""

import openpyxl
from collections import defaultdict
import statistics

WORKBOOK = "jobs-data-v3.xlsx"
SHEET = "5 Results"

# Human-readable labels for occ groups
OCC_GROUP_LABELS = {
    "Core": "Core (Industry-Specific)",
    "G1_Exec_Management": "G1 Executive & Management",
    "G2_HR_People": "G2 HR & People",
    "G3_Finance_Accounting": "G3 Finance & Accounting",
    "G4_IT_Digital": "G4 IT & Digital",
    "G5_Marketing_Creative": "G5 Marketing & Creative",
    "G6_Sales_BizDev": "G6 Sales & Business Dev",
    "G7_Legal_Compliance": "G7 Legal & Compliance",
    "G8_Procurement_Supply": "G8 Procurement & Supply Chain",
    "G9_Admin_Office": "G9 Admin & Office Support",
}


def safe_float(v, default=0.0):
    """Convert cell value to float, defaulting if None or non-numeric."""
    if v is None:
        return default
    try:
        return float(v)
    except (ValueError, TypeError):
        return default


def load_data():
    """Load the 5 Results tab and return list of row dicts."""
    wb = openpyxl.load_workbook(WORKBOOK, read_only=True, data_only=True)
    ws = wb[SHEET]
    rows = []
    for row in ws.iter_rows(min_row=2, max_row=358, values_only=True):
        soc = row[0]
        if not soc or not str(soc).strip():
            continue
        rows.append({
            "soc": str(row[0]).strip(),
            "title": str(row[1]).strip() if row[1] else "",
            "sector": str(row[2]).strip() if row[2] else "",
            "occ_group": str(row[3]).strip() if row[3] else "",
            "employment_K": safe_float(row[4]),
            "median_wage": safe_float(row[5]),
            "d_mod_high": safe_float(row[20]),
            "d_sig_high": safe_float(row[22]),
            "displaced_K_mod_high": safe_float(row[24]),
            "displaced_K_sig_high": safe_float(row[26]),
        })
    wb.close()
    return rows


def aggregate_by_occ_group(rows):
    """Aggregate displacement stats by occupation group."""
    groups = defaultdict(lambda: {
        "employment_K": 0.0,
        "displaced_mod_K": 0.0,
        "displaced_sig_K": 0.0,
        "wages": [],
        "wage_employment_pairs": [],
        "soc_count": 0,
        "d_rates_mod": [],
        "d_rates_sig": [],
    })

    for r in rows:
        g = groups[r["occ_group"]]
        g["employment_K"] += r["employment_K"]
        g["displaced_mod_K"] += r["displaced_K_mod_high"]
        g["displaced_sig_K"] += r["displaced_K_sig_high"]
        g["wages"].append(r["median_wage"])
        g["wage_employment_pairs"].append((r["median_wage"], r["employment_K"]))
        g["soc_count"] += 1
        g["d_rates_mod"].append(r["d_mod_high"])
        g["d_rates_sig"].append(r["d_sig_high"])

    return groups


def aggregate_sector_by_occ_group(rows):
    """Cross-tab: for each occ group, aggregate displacement by sector."""
    cross = defaultdict(lambda: defaultdict(lambda: {
        "employment_K": 0.0,
        "displaced_mod_K": 0.0,
        "displaced_sig_K": 0.0,
    }))
    for r in rows:
        c = cross[r["occ_group"]][r["sector"]]
        c["employment_K"] += r["employment_K"]
        c["displaced_mod_K"] += r["displaced_K_mod_high"]
        c["displaced_sig_K"] += r["displaced_K_sig_high"]
    return cross


def weighted_avg_wage(pairs):
    """Employment-weighted average wage."""
    total_emp = sum(emp for _, emp in pairs)
    if total_emp == 0:
        return 0
    return sum(w * emp for w, emp in pairs) / total_emp


def print_separator(char="=", width=160):
    print(char * width)


def main():
    rows = load_data()
    total_employment = sum(r["employment_K"] for r in rows)

    print()
    print_separator()
    print("OCCUPATION GROUP-LEVEL DISPLACEMENT ANALYSIS")
    print(f"Source: {WORKBOOK} / '{SHEET}' — {len(rows)} SOCs, High-Friction Scenario")
    print_separator()

    # ── Part 1: Aggregate table ──────────────────────────────────────────
    groups = aggregate_by_occ_group(rows)

    # Build summary records sorted by displaced_sig_K descending
    summaries = []
    for gname, g in groups.items():
        label = OCC_GROUP_LABELS.get(gname, gname)
        emp = g["employment_K"]
        d_mod = g["displaced_mod_K"]
        d_sig = g["displaced_sig_K"]
        avg_wage = weighted_avg_wage(g["wage_employment_pairs"])
        med_wage = statistics.median(g["wages"]) if g["wages"] else 0
        avg_d_mod = statistics.mean(g["d_rates_mod"]) if g["d_rates_mod"] else 0
        avg_d_sig = statistics.mean(g["d_rates_sig"]) if g["d_rates_sig"] else 0

        summaries.append({
            "label": label,
            "code": gname,
            "soc_count": g["soc_count"],
            "employment_K": emp,
            "emp_share_pct": (emp / total_employment * 100) if total_employment else 0,
            "displaced_mod_K": d_mod,
            "d_mod_pct": (d_mod / emp * 100) if emp else 0,
            "displaced_sig_K": d_sig,
            "d_sig_pct": (d_sig / emp * 100) if emp else 0,
            "avg_wage": avg_wage,
            "median_wage": med_wage,
            "avg_d_rate_mod": avg_d_mod,
            "avg_d_rate_sig": avg_d_sig,
        })

    summaries.sort(key=lambda s: s["displaced_sig_K"], reverse=True)

    # Print header
    print()
    print(f"{'Occupation Group':<35} {'SOCs':>4}  {'Employ(K)':>10}  {'Emp%':>5}  "
          f"{'Mod Disp(K)':>11}  {'Mod%':>5}  {'Sig Disp(K)':>11}  {'Sig%':>5}  "
          f"{'Avg d_mod':>9}  {'Avg d_sig':>9}  {'Wtd Avg Wage':>12}  {'Med Wage':>10}")
    print("-" * 160)

    grand_emp = 0.0
    grand_mod = 0.0
    grand_sig = 0.0

    for s in summaries:
        grand_emp += s["employment_K"]
        grand_mod += s["displaced_mod_K"]
        grand_sig += s["displaced_sig_K"]
        print(f"{s['label']:<35} {s['soc_count']:>4}  {s['employment_K']:>10,.1f}  "
              f"{s['emp_share_pct']:>4.1f}%  "
              f"{s['displaced_mod_K']:>11,.2f}  {s['d_mod_pct']:>4.1f}%  "
              f"{s['displaced_sig_K']:>11,.2f}  {s['d_sig_pct']:>4.1f}%  "
              f"{s['avg_d_rate_mod']:>8.4f}  {s['avg_d_rate_sig']:>8.4f}  "
              f"${s['avg_wage']:>11,.0f}  ${s['median_wage']:>9,.0f}")

    print("-" * 160)
    print(f"{'GRAND TOTAL':<35} {len(rows):>4}  {grand_emp:>10,.1f}  100.0%  "
          f"{grand_mod:>11,.2f}  {grand_mod/grand_emp*100:>4.1f}%  "
          f"{grand_sig:>11,.2f}  {grand_sig/grand_emp*100:>4.1f}%")
    print()

    # ── Part 2: Top-5 most-displaced occ groups — detail breakdown ───────
    print_separator()
    print("DETAILED BREAKDOWN: TOP SOCs BY DISPLACEMENT IN EACH OCCUPATION GROUP")
    print_separator()

    for s in summaries:
        gname = s["code"]
        label = s["label"]
        group_rows = [r for r in rows if r["occ_group"] == gname]
        group_rows.sort(key=lambda r: r["displaced_K_sig_high"], reverse=True)

        print(f"\n  {label}  ({s['soc_count']} SOCs, {s['employment_K']:,.1f}K employed, "
              f"{s['displaced_sig_K']:,.2f}K displaced sig)")
        print(f"  {'SOC':<10} {'Title':<50} {'Employ(K)':>10}  {'Mod Disp(K)':>11}  {'Sig Disp(K)':>11}  "
              f"{'d_mod':>7}  {'d_sig':>7}  {'Wage':>10}")
        print(f"  {'-'*130}")

        top_n = min(10, len(group_rows))
        for r in group_rows[:top_n]:
            title = r["title"][:48]
            print(f"  {r['soc']:<10} {title:<50} {r['employment_K']:>10,.1f}  "
                  f"{r['displaced_K_mod_high']:>11,.2f}  {r['displaced_K_sig_high']:>11,.2f}  "
                  f"{r['d_mod_high']:>6.4f}  {r['d_sig_high']:>6.4f}  ${r['median_wage']:>9,.0f}")
        if len(group_rows) > top_n:
            remaining_sig = sum(r["displaced_K_sig_high"] for r in group_rows[top_n:])
            print(f"  {'...':<10} {'(remaining ' + str(len(group_rows)-top_n) + ' SOCs)':<50} "
                  f"{'':>10}  {'':>11}  {remaining_sig:>11,.2f}")

    # ── Part 3: Cross-tab — Sector contributions per Occ Group ───────────
    print()
    print_separator()
    print("CROSS-TAB: SECTOR CONTRIBUTIONS TO DISPLACEMENT BY OCCUPATION GROUP")
    print("(Top 5 sectors per occ group, ranked by significant displacement)")
    print_separator()

    cross = aggregate_sector_by_occ_group(rows)

    for s in summaries:
        gname = s["code"]
        label = s["label"]
        sector_data = cross[gname]

        # Sort sectors by displaced_sig_K descending
        sector_list = []
        for sector, data in sector_data.items():
            sector_list.append({
                "sector": sector,
                "employment_K": data["employment_K"],
                "displaced_mod_K": data["displaced_mod_K"],
                "displaced_sig_K": data["displaced_sig_K"],
            })
        sector_list.sort(key=lambda x: x["displaced_sig_K"], reverse=True)

        group_sig_total = s["displaced_sig_K"]

        print(f"\n  {label}  (Total sig displacement: {group_sig_total:,.2f}K)")
        print(f"  {'Sector':<45} {'Employ(K)':>10}  {'Mod Disp(K)':>11}  {'Sig Disp(K)':>11}  "
              f"{'% of Group Sig':>14}")
        print(f"  {'-'*100}")

        shown = 0
        shown_sig = 0.0
        for sd in sector_list[:7]:
            pct = (sd["displaced_sig_K"] / group_sig_total * 100) if group_sig_total else 0
            print(f"  {sd['sector']:<45} {sd['employment_K']:>10,.1f}  "
                  f"{sd['displaced_mod_K']:>11,.2f}  {sd['displaced_sig_K']:>11,.2f}  "
                  f"{pct:>13.1f}%")
            shown += 1
            shown_sig += sd["displaced_sig_K"]

        if len(sector_list) > 7:
            remaining = group_sig_total - shown_sig
            print(f"  {'(remaining ' + str(len(sector_list)-7) + ' sectors)':<45} "
                  f"{'':>10}  {'':>11}  {remaining:>11,.2f}  "
                  f"{(remaining/group_sig_total*100) if group_sig_total else 0:>13.1f}%")

    # ── Part 4: Grand summary statistics ─────────────────────────────────
    print()
    print_separator()
    print("GRAND SUMMARY")
    print_separator()

    all_wages = [r["median_wage"] for r in rows]
    all_d_sig = [r["d_sig_high"] for r in rows]
    all_d_mod = [r["d_mod_high"] for r in rows]

    print(f"  Total SOCs analyzed:            {len(rows)}")
    print(f"  Total employment:               {grand_emp:>12,.1f}K  ({grand_emp/1000:,.1f}M)")
    print(f"  Total displaced (moderate):     {grand_mod:>12,.2f}K  ({grand_mod/grand_emp*100:.2f}% of employment)")
    print(f"  Total displaced (significant):  {grand_sig:>12,.2f}K  ({grand_sig/grand_emp*100:.2f}% of employment)")
    print(f"  Incremental sig vs mod:         {grand_sig-grand_mod:>12,.2f}K  (+{(grand_sig-grand_mod)/grand_mod*100:.1f}%)")
    print()
    print(f"  Avg d_rate (mod, unweighted):   {statistics.mean(all_d_mod):.4f}")
    print(f"  Avg d_rate (sig, unweighted):   {statistics.mean(all_d_sig):.4f}")
    print(f"  Median d_rate (mod):            {statistics.median(all_d_mod):.4f}")
    print(f"  Median d_rate (sig):            {statistics.median(all_d_sig):.4f}")
    print(f"  Max d_rate (sig):               {max(all_d_sig):.4f}")
    print(f"  Min d_rate (sig, >0):           {min(d for d in all_d_sig if d > 0):.4f}")
    print(f"  SOCs with zero mod displacement: {sum(1 for d in all_d_mod if d == 0)}")
    print(f"  SOCs with zero sig displacement: {sum(1 for d in all_d_sig if d == 0)}")
    print()

    # Displacement concentration
    rows_by_sig = sorted(rows, key=lambda r: r["displaced_K_sig_high"], reverse=True)
    cumul = 0.0
    for i, r in enumerate(rows_by_sig, 1):
        cumul += r["displaced_K_sig_high"]
        if cumul >= grand_sig * 0.5:
            print(f"  50% of significant displacement concentrated in top {i} SOCs "
                  f"({i/len(rows)*100:.1f}% of all SOCs)")
            break
    cumul = 0.0
    for i, r in enumerate(rows_by_sig, 1):
        cumul += r["displaced_K_sig_high"]
        if cumul >= grand_sig * 0.8:
            print(f"  80% of significant displacement concentrated in top {i} SOCs "
                  f"({i/len(rows)*100:.1f}% of all SOCs)")
            break

    print()
    print("  Top 10 SOCs by significant displacement (K):")
    print(f"  {'Rank':>4}  {'SOC':<10} {'Title':<45} {'Occ Group':<30} {'Sig Disp(K)':>11}  {'d_sig':>7}")
    print(f"  {'-'*115}")
    for i, r in enumerate(rows_by_sig[:10], 1):
        label = OCC_GROUP_LABELS.get(r["occ_group"], r["occ_group"])
        title = r["title"][:43]
        print(f"  {i:>4}  {r['soc']:<10} {title:<45} {label:<30} "
              f"{r['displaced_K_sig_high']:>11,.2f}  {r['d_sig_high']:>6.4f}")

    print()
    print_separator()
    print("END OF ANALYSIS")
    print_separator()


if __name__ == "__main__":
    main()
