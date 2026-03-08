#!/usr/bin/env python3
"""
Comprehensive job-level displacement analysis.
Reads the '5 Results' tab from jobs-data-v3.xlsx (read-only) and produces
formatted tables of displacement statistics.
"""

import openpyxl
import statistics
from collections import defaultdict

WORKBOOK = "/Users/charliesheiner/Projects/ai-labor-analysis/jobs-data-v3.xlsx"
SHEET = "5 Results"

# ── Load workbook (read-only) ──────────────────────────────────────────────
wb = openpyxl.load_workbook(WORKBOOK, read_only=True, data_only=True)
ws = wb[SHEET]

# ── Read headers and identify columns ──────────────────────────────────────
rows = list(ws.iter_rows(min_row=1, values_only=True))
headers = [str(h).strip() if h else f"col_{i}" for i, h in enumerate(rows[0])]
data_rows = rows[1:]

# Print column index map for verification
print("=" * 90)
print("COLUMN MAP (index: header)")
print("=" * 90)
for i, h in enumerate(headers):
    print(f"  {i:>2}: {h}")
print()

# ── Build list of job dicts ────────────────────────────────────────────────
# Map by header name — we'll figure out exact names from the printout
def col(name):
    """Find column index by partial header match (case-insensitive)."""
    name_l = name.lower()
    for i, h in enumerate(headers):
        if name_l == h.lower():
            return i
    # partial match
    for i, h in enumerate(headers):
        if name_l in h.lower():
            return i
    return None

# We need these columns — try to find them
col_map = {
    "soc_code":   0,   # col A
    "job_title":  1,   # col B
    "sector":     2,   # col C
    "occ_group":  3,   # col D
    "employment": 4,   # col E
    "wage":       5,   # col F
    "tc_adj_mod": 6,   # col G
    "tc_adj_sig": 7,   # col H
    "w":          8,   # col I
    "a_mod":      9,   # col J
    "a_sig":      10,  # col K
    "S_mod":      11,  # col L
    "S_sig":      12,  # col M
    "d_max":      13,  # col N
}
# Displacement results are further right — col index 20, 22, 24, 26 (0-based)
# Columns 14-26 span the friction/scenario results
# d_mod_high ~ col 20, d_sig_high ~ col 22, displaced_K_mod_high ~ col 24, displaced_K_sig_high ~ col 26

# Let's be flexible: scan headers for known patterns
def find_col(patterns, fallback_idx=None):
    """Find column by trying multiple header patterns."""
    for pat in patterns:
        idx = col(pat)
        if idx is not None:
            return idx
    return fallback_idx

jobs = []
for row in data_rows:
    if not row or not row[0]:
        continue
    # Skip if SOC code doesn't look like a SOC (XX-XXXX)
    soc = str(row[0]).strip()
    if len(soc) < 5:
        continue

    def safe_float(idx):
        try:
            v = row[idx]
            if v is None:
                return None
            return float(v)
        except (ValueError, TypeError, IndexError):
            return None

    job = {
        "soc_code":    soc,
        "job_title":   str(row[1]).strip() if row[1] else "",
        "sector":      str(row[2]).strip() if row[2] else "",
        "occ_group":   str(row[3]).strip() if row[3] else "",
        "employment":  safe_float(4),
        "wage":        safe_float(5),
        "tc_adj_mod":  safe_float(6),
        "tc_adj_sig":  safe_float(7),
        "w":           safe_float(8),
        "a_mod":       safe_float(9),
        "a_sig":       safe_float(10),
        "S_mod":       safe_float(11),
        "S_sig":       safe_float(12),
        "d_max":       safe_float(13),
    }

    # For the displacement result columns, scan by header name
    # They should be around columns 20-27
    for i in range(14, len(headers)):
        h = headers[i].lower() if i < len(headers) else ""
        if "d_mod" in h and "high" in h and "displaced" not in h and "displace" not in h:
            job["d_mod_high"] = safe_float(i)
        elif "d_sig" in h and "high" in h and "displaced" not in h and "displace" not in h:
            job["d_sig_high"] = safe_float(i)
        elif "displaced" in h and "mod" in h and "high" in h:
            job["displaced_K_mod_high"] = safe_float(i)
        elif "displaced" in h and "sig" in h and "high" in h:
            job["displaced_K_sig_high"] = safe_float(i)

    # Fallback: use positional if header scan didn't find them
    if "d_mod_high" not in job:
        job["d_mod_high"] = safe_float(20)
    if "d_sig_high" not in job:
        job["d_sig_high"] = safe_float(22)
    if "displaced_K_mod_high" not in job:
        job["displaced_K_mod_high"] = safe_float(24)
    if "displaced_K_sig_high" not in job:
        job["displaced_K_sig_high"] = safe_float(26)

    jobs.append(job)

wb.close()

print(f"Loaded {len(jobs)} jobs from '{SHEET}'\n")

# Verify we have displacement data
sample = jobs[0]
print("Sample job (first row):")
for k, v in sample.items():
    print(f"  {k}: {v}")
print()

# ── Helper: format table ──────────────────────────────────────────────────
def fmt_pct(v):
    if v is None:
        return "  N/A"
    return f"{v*100:6.2f}%"

def fmt_k(v):
    if v is None:
        return "    N/A"
    return f"{v:8.1f}"

def fmt_wage(v):
    if v is None:
        return "    N/A"
    return f"${v:>8,.0f}"

def fmt_f(v, w=6, d=3):
    if v is None:
        return " " * w
    return f"{v:{w}.{d}f}"

TITLE_W = 42
SEP = "-" * 130

def print_table(title, rows, columns):
    """
    columns: list of (header, key, formatter, width)
    """
    print("\n" + "=" * 130)
    print(f"  {title}")
    print("=" * 130)
    # Header
    hdr = " " + " ".join(f"{c[0]:>{c[3]}}" for c in columns)
    print(hdr)
    print(SEP)
    for i, r in enumerate(rows, 1):
        line = " "
        for c in columns:
            val = r.get(c[1])
            formatted = c[2](val) if callable(c[2]) else str(val)
            line += f"{formatted:>{c[3]}} "
        print(f"{i:>3}.{line}")
    print()

# ══════════════════════════════════════════════════════════════════════════
# ANALYSIS 1: Top 25 by absolute workers displaced (sig, high friction)
# ══════════════════════════════════════════════════════════════════════════
valid_displaced = [j for j in jobs if j.get("displaced_K_sig_high") is not None]
by_displaced_abs = sorted(valid_displaced, key=lambda j: j["displaced_K_sig_high"] or 0, reverse=True)

cols_abs = [
    ("Job Title",          "job_title",             lambda v: v[:TITLE_W].ljust(TITLE_W), TITLE_W),
    ("Sector",             "sector",                lambda v: (v or "")[:16].ljust(16), 16),
    ("Emp(K)",             "employment",            lambda v: fmt_k(v), 8),
    ("d_sig_H",            "d_sig_high",            fmt_pct, 8),
    ("Displaced(K)",       "displaced_K_sig_high",  lambda v: fmt_k(v), 10),
    ("Wage",               "wage",                  fmt_wage, 10),
]

print_table("TOP 25 JOBS BY ABSOLUTE WORKERS DISPLACED (Significant Capability, High Friction)",
            by_displaced_abs[:25], cols_abs)

# Total displaced in top 25
top25_displaced = sum(j["displaced_K_sig_high"] for j in by_displaced_abs[:25] if j["displaced_K_sig_high"])
total_displaced = sum(j["displaced_K_sig_high"] for j in valid_displaced if j["displaced_K_sig_high"])
total_emp = sum(j["employment"] for j in jobs if j.get("employment"))
print(f"  Top 25 account for {top25_displaced:,.1f}K of {total_displaced:,.1f}K total displaced ({top25_displaced/total_displaced*100:.1f}%)")
print(f"  Total employment across all {len(jobs)} jobs: {total_emp:,.0f}K")
print()

# ══════════════════════════════════════════════════════════════════════════
# ANALYSIS 2: Top 25 by displacement RATE (sig, high friction)
# ══════════════════════════════════════════════════════════════════════════
valid_rate = [j for j in jobs if j.get("d_sig_high") is not None and j["d_sig_high"] > 0]
by_rate = sorted(valid_rate, key=lambda j: j["d_sig_high"], reverse=True)

cols_rate = [
    ("Job Title",          "job_title",             lambda v: v[:TITLE_W].ljust(TITLE_W), TITLE_W),
    ("Sector",             "sector",                lambda v: (v or "")[:16].ljust(16), 16),
    ("Emp(K)",             "employment",            lambda v: fmt_k(v), 8),
    ("a_sig",              "a_sig",                 lambda v: fmt_f(v), 7),
    ("S_sig",              "S_sig",                 lambda v: fmt_f(v), 7),
    ("d_max",              "d_max",                 lambda v: fmt_f(v), 7),
    ("d_sig_H",            "d_sig_high",            fmt_pct, 8),
    ("Displaced(K)",       "displaced_K_sig_high",  lambda v: fmt_k(v), 10),
]

print_table("TOP 25 JOBS BY DISPLACEMENT RATE (Significant Capability, High Friction)",
            by_rate[:25], cols_rate)

# ══════════════════════════════════════════════════════════════════════════
# ANALYSIS 3: Bottom 25 by displacement rate (non-zero)
# ══════════════════════════════════════════════════════════════════════════
by_rate_asc = sorted(valid_rate, key=lambda j: j["d_sig_high"])

print_table("BOTTOM 25 JOBS BY DISPLACEMENT RATE (Non-Zero, Significant Capability, High Friction)",
            by_rate_asc[:25], cols_rate)

# ══════════════════════════════════════════════════════════════════════════
# ANALYSIS 4: Distribution statistics
# ══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 130)
print("  DISPLACEMENT RATE DISTRIBUTION STATISTICS")
print("=" * 130)

for scenario, key in [("Moderate (High Friction)", "d_mod_high"),
                       ("Significant (High Friction)", "d_sig_high")]:
    vals = [j[key] for j in jobs if j.get(key) is not None]
    if not vals:
        print(f"\n  {scenario}: No data available")
        continue

    vals_sorted = sorted(vals)
    n = len(vals)
    q1 = vals_sorted[n // 4]
    q2 = vals_sorted[n // 2]
    q3 = vals_sorted[3 * n // 4]
    p10 = vals_sorted[n // 10]
    p90 = vals_sorted[9 * n // 10]

    print(f"\n  {scenario}  (n={n})")
    print(f"    Mean:     {statistics.mean(vals)*100:6.2f}%")
    print(f"    Median:   {q2*100:6.2f}%")
    print(f"    Std Dev:  {statistics.stdev(vals)*100:6.2f}%")
    print(f"    Min:      {min(vals)*100:6.2f}%")
    print(f"    P10:      {p10*100:6.2f}%")
    print(f"    Q1 (25%): {q1*100:6.2f}%")
    print(f"    Q2 (50%): {q2*100:6.2f}%")
    print(f"    Q3 (75%): {q3*100:6.2f}%")
    print(f"    P90:      {p90*100:6.2f}%")
    print(f"    Max:      {max(vals)*100:6.2f}%")

print()

# Histogram-like distribution
print("  DISPLACEMENT RATE DISTRIBUTION (Significant Capability, High Friction)")
print(SEP)
d_vals = [j["d_sig_high"] for j in jobs if j.get("d_sig_high") is not None]
buckets = [(0.0, 0.01), (0.01, 0.02), (0.02, 0.03), (0.03, 0.05),
           (0.05, 0.10), (0.10, 0.15), (0.15, 0.20), (0.20, 0.30),
           (0.30, 0.50), (0.50, 1.01)]
for lo, hi in buckets:
    count = sum(1 for v in d_vals if lo <= v < hi)
    bar = "#" * count
    label = f"  {lo*100:5.1f}% - {hi*100:5.1f}%"
    if hi > 1.0:
        label = f"  {lo*100:5.1f}% -   50%+"
    print(f"  {label}: {count:>4} jobs  {bar}")

# ══════════════════════════════════════════════════════════════════════════
# ANALYSIS 5: Wage analysis
# ══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 130)
print("  WAGE ANALYSIS BY DISPLACEMENT LEVEL")
print("=" * 130)

# Sort by displaced_K_sig_high for absolute impact
with_wage = [j for j in valid_displaced if j.get("wage") is not None and j.get("displaced_K_sig_high") is not None]
by_disp = sorted(with_wage, key=lambda j: j["displaced_K_sig_high"] or 0, reverse=True)

top50 = by_disp[:50]
bot50 = by_disp[-50:]
all_wages = [j["wage"] for j in with_wage if j["wage"]]

top50_wages = [j["wage"] for j in top50 if j["wage"]]
bot50_wages = [j["wage"] for j in bot50 if j["wage"]]

print(f"\n  Top 50 most-displaced jobs (by absolute workers):")
print(f"    Mean wage:   ${statistics.mean(top50_wages):>10,.0f}")
print(f"    Median wage: ${statistics.median(top50_wages):>10,.0f}")

print(f"\n  Bottom 50 least-displaced jobs:")
print(f"    Mean wage:   ${statistics.mean(bot50_wages):>10,.0f}")
print(f"    Median wage: ${statistics.median(bot50_wages):>10,.0f}")

print(f"\n  Overall ({len(all_wages)} jobs with wage data):")
print(f"    Mean wage:   ${statistics.mean(all_wages):>10,.0f}")
print(f"    Median wage: ${statistics.median(all_wages):>10,.0f}")

# Also by rate
by_rate_w = sorted([j for j in with_wage if j.get("d_sig_high") and j["d_sig_high"] > 0],
                   key=lambda j: j["d_sig_high"], reverse=True)
top50r = by_rate_w[:50]
bot50r = by_rate_w[-50:]
top50r_wages = [j["wage"] for j in top50r if j["wage"]]
bot50r_wages = [j["wage"] for j in bot50r if j["wage"]]

print(f"\n  Top 50 highest displacement RATE jobs:")
print(f"    Mean wage:   ${statistics.mean(top50r_wages):>10,.0f}")
print(f"    Median wage: ${statistics.median(top50r_wages):>10,.0f}")

print(f"\n  Bottom 50 lowest displacement RATE jobs (non-zero):")
print(f"    Mean wage:   ${statistics.mean(bot50r_wages):>10,.0f}")
print(f"    Median wage: ${statistics.median(bot50r_wages):>10,.0f}")

# ══════════════════════════════════════════════════════════════════════════
# ANALYSIS 6: Threshold counts
# ══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 130)
print("  DISPLACEMENT THRESHOLD ANALYSIS (Significant Capability, High Friction)")
print("=" * 130)

thresholds = [0.01, 0.02, 0.03, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30]
d_all = [(j.get("d_sig_high"), j.get("employment")) for j in jobs
         if j.get("d_sig_high") is not None]

print(f"\n  {'Threshold':>12}  {'# Jobs':>8}  {'% of Jobs':>10}  {'Workers(K)':>12}  {'% of Workforce':>15}")
print("  " + "-" * 65)

total_workers = sum(emp for _, emp in d_all if emp)
for t in thresholds:
    above = [(d, emp) for d, emp in d_all if d >= t]
    n_jobs = len(above)
    workers = sum(emp for _, emp in above if emp)
    print(f"  {'>':>1}{t*100:>5.0f}%       {n_jobs:>5}     {n_jobs/len(d_all)*100:>6.1f}%     {workers:>9,.0f}K       {workers/total_workers*100:>6.1f}%")

# Zero displacement jobs
zero_jobs = [j for j in jobs if j.get("d_sig_high") is not None and j["d_sig_high"] == 0]
print(f"\n  Jobs with ZERO displacement: {len(zero_jobs)}")
if zero_jobs:
    zero_emp = sum(j["employment"] for j in zero_jobs if j.get("employment"))
    print(f"  Workers in zero-displacement jobs: {zero_emp:,.0f}K")

# ══════════════════════════════════════════════════════════════════════════
# ANALYSIS 7: Moderate vs Significant comparison
# ══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 130)
print("  MODERATE vs SIGNIFICANT CAPABILITY COMPARISON")
print("=" * 130)

both = [j for j in jobs if j.get("d_mod_high") is not None and j.get("d_sig_high") is not None]
if both:
    mod_rates = [j["d_mod_high"] for j in both]
    sig_rates = [j["d_sig_high"] for j in both]
    ratios = [s / m if m > 0 else None for m, s in zip(mod_rates, sig_rates)]
    valid_ratios = [r for r in ratios if r is not None]

    mod_displaced = sum(j.get("displaced_K_mod_high", 0) or 0 for j in both)
    sig_displaced = sum(j.get("displaced_K_sig_high", 0) or 0 for j in both)

    print(f"\n  Total displaced (Moderate, High Friction):     {mod_displaced:>10,.1f}K")
    print(f"  Total displaced (Significant, High Friction):  {sig_displaced:>10,.1f}K")
    print(f"  Ratio (Sig/Mod):                               {sig_displaced/mod_displaced:>10.2f}x")
    print(f"\n  Mean displacement rate (Moderate):   {statistics.mean(mod_rates)*100:6.2f}%")
    print(f"  Mean displacement rate (Significant):{statistics.mean(sig_rates)*100:6.2f}%")
    print(f"  Median ratio (Sig/Mod per job):      {statistics.median(valid_ratios):6.2f}x")

    # Jobs where sig is much higher than mod
    big_jumps = sorted(both, key=lambda j: (j["d_sig_high"] - j["d_mod_high"]), reverse=True)
    print(f"\n  Top 10 jobs with LARGEST gap (Significant - Moderate displacement rate):")
    print(f"  {'Job Title':<45} {'d_mod_H':>8} {'d_sig_H':>8} {'Gap':>8}")
    print("  " + "-" * 75)
    for j in big_jumps[:10]:
        gap = j["d_sig_high"] - j["d_mod_high"]
        print(f"  {j['job_title'][:44]:<45} {j['d_mod_high']*100:>6.2f}%  {j['d_sig_high']*100:>6.2f}%  {gap*100:>+6.2f}pp")

print("\n" + "=" * 130)
print("  ANALYSIS COMPLETE")
print("=" * 130)
