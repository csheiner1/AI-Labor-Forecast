"""Generate charts for the Social Impact dashboard.

Generates static PNG files in dashboard/static/img/.
Called on app startup or manually via `python3 dashboard/charts.py`.
"""
import os
import sys
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dashboard.data_loader import store

CHART_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "img")

# Colors
C_BLUE = "#2563eb"
C_RED = "#dc2626"
C_AMBER = "#f59e0b"
C_GREEN = "#16a34a"
C_GRAY = "#6b7280"
C_LIGHT_BLUE = "#93c5fd"
C_BG = "#f8fafc"

plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor": C_BG,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "font.family": "sans-serif",
    "font.size": 11,
    "figure.dpi": 150,
})


def _ensure_dir():
    os.makedirs(CHART_DIR, exist_ok=True)


def chart_displacement_by_demographic(data, field, label, filename):
    """Bar chart: displacement rate by a demographic percentage bracket.

    Bins SOCs by the demographic field into brackets (e.g. <20%, 20-40%, etc.)
    and shows employment-weighted mean displacement for each bracket.
    """
    _ensure_dir()

    # Filter to SOCs with this field
    valid = [r for r in data if r.get(field) is not None and r.get("d_mod_low") is not None]
    if not valid:
        print(f"  Skipping {filename}: no valid data for {field}")
        return

    # Bin by demographic percentage
    bins = [(0, 20), (20, 40), (40, 60), (60, 80), (80, 100)]
    bin_labels = ["<20%", "20-40%", "40-60%", "60-80%", "80-100%"]
    bin_data = {l: {"emp": 0, "disp_sum": 0} for l in bin_labels}

    for r in valid:
        pct = r[field]
        emp = r.get("Employment_2024_K", 0) or 0
        d = r.get("d_mod_low", 0) or 0
        for (lo, hi), bl in zip(bins, bin_labels):
            if lo <= pct < hi or (hi == 100 and pct == 100):
                bin_data[bl]["emp"] += emp
                bin_data[bl]["disp_sum"] += emp * d
                break

    means = []
    for bl in bin_labels:
        bd = bin_data[bl]
        means.append(bd["disp_sum"] / bd["emp"] if bd["emp"] > 0 else 0)

    fig, ax = plt.subplots(figsize=(8, 5))
    x = np.arange(len(bin_labels))
    bars = ax.bar(x, means, color=C_BLUE, alpha=0.8, edgecolor="white")
    ax.set_xticks(x)
    ax.set_xticklabels(bin_labels)
    ax.set_xlabel(f"{label} Share of Workforce")
    ax.set_ylabel("Emp-Weighted Mean Displacement Rate")
    ax.set_title(f"Displacement Rate by {label}")
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1, decimals=1))

    fig.tight_layout()
    fig.savefig(os.path.join(CHART_DIR, filename), bbox_inches="tight")
    plt.close()
    print(f"  {filename}")


def chart_wage_quintile_displacement(data, filename="equity_wage_quintile.png"):
    """Bar chart: displacement by wage quintile."""
    _ensure_dir()

    valid = [r for r in data if r.get("Median_Wage") and r.get("d_mod_low") is not None]
    valid.sort(key=lambda r: r["Median_Wage"])

    n = len(valid)
    if n < 5:
        print(f"  Skipping {filename}: too few records ({n})")
        return

    q_size = n // 5
    labels = ["Q1\n(lowest)", "Q2", "Q3", "Q4", "Q5\n(highest)"]
    means_mod = []
    means_sig = []

    for i in range(5):
        start = i * q_size
        end = start + q_size if i < 4 else n
        q = valid[start:end]
        total_emp = sum(r.get("Employment_2024_K", 0) or 0 for r in q)
        if total_emp > 0:
            wm_mod = sum((r.get("d_mod_low", 0) or 0) * (r.get("Employment_2024_K", 0) or 0) for r in q) / total_emp
            wm_sig = sum((r.get("d_sig_low", 0) or 0) * (r.get("Employment_2024_K", 0) or 0) for r in q) / total_emp
        else:
            wm_mod = wm_sig = 0
        means_mod.append(wm_mod)
        means_sig.append(wm_sig)

    fig, ax = plt.subplots(figsize=(9, 5.5))
    x = np.arange(5)
    w = 0.35
    ax.bar(x - w/2, means_mod, w, label="Moderate", color=C_BLUE, alpha=0.8)
    ax.bar(x + w/2, means_sig, w, label="Significant", color=C_RED, alpha=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_xlabel("Wage Quintile")
    ax.set_ylabel("Emp-Weighted Mean Displacement Rate")
    ax.set_title("Displacement Rate by Wage Quintile\n(Moderate vs. Significant Scenario, Low Friction)")
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1, decimals=1))
    ax.legend()

    fig.tight_layout()
    fig.savefig(os.path.join(CHART_DIR, filename), bbox_inches="tight")
    plt.close()
    print(f"  {filename}")


def chart_gender_displacement(data, filename="equity_gender.png"):
    """Scatter: Pct_Female vs displacement rate, sized by employment."""
    _ensure_dir()
    valid = [r for r in data if r.get("Pct_Female") is not None and r.get("d_mod_low") is not None]
    if not valid:
        return

    x = [r["Pct_Female"] for r in valid]
    y = [r["d_mod_low"] for r in valid]
    sizes = [max(3, (r.get("Employment_2024_K", 0) or 0) / 10) for r in valid]

    fig, ax = plt.subplots(figsize=(9, 6))
    ax.scatter(x, y, s=sizes, alpha=0.5, c=C_BLUE, edgecolors="white", linewidth=0.5)
    ax.set_xlabel("Percent Female")
    ax.set_ylabel("Displacement Rate (Moderate, Low Friction)")
    ax.set_title("Gender Composition vs. AI Displacement Risk")
    ax.xaxis.set_major_formatter(mticker.PercentFormatter(xmax=100))
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1, decimals=1))

    fig.tight_layout()
    fig.savefig(os.path.join(CHART_DIR, filename), bbox_inches="tight")
    plt.close()
    print(f"  {filename}")


def chart_state_displacement_risk(data, state_shares=None, filename="geo_state_risk.png"):
    """Horizontal bar chart: top 20 states by total displaced workers.

    Distributes each SOC's displaced workers proportionally across states
    using OEWS state employment shares.
    """
    _ensure_dir()

    state_totals = defaultdict(lambda: {"displaced": 0, "emp": 0, "socs": 0})

    for r in data:
        dk = r.get("displaced_K_mod_low", 0) or 0
        emp = r.get("Employment_2024_K", 0) or 0
        soc = r.get("SOC_Code", "")
        if dk <= 0:
            continue

        # Use OEWS employment shares if available
        shares = (state_shares or {}).get(soc, {})
        if shares:
            for state_name, frac in shares.items():
                state_totals[state_name]["displaced"] += dk * frac
                state_totals[state_name]["emp"] += emp * frac
                state_totals[state_name]["socs"] += frac
        else:
            # Fallback: split equally across available top states
            top_states = [r.get(f"Top_State_{i}") for i in [1, 2, 3]
                          if r.get(f"Top_State_{i}")]
            if top_states:
                share = 1.0 / len(top_states)
                for state_name in top_states:
                    state_totals[state_name]["displaced"] += dk * share
                    state_totals[state_name]["emp"] += emp * share
                    state_totals[state_name]["socs"] += share

    if not state_totals:
        return

    # Sort by displaced workers, take top 20
    top = sorted(state_totals.items(), key=lambda x: x[1]["displaced"], reverse=True)[:20]
    top.reverse()  # for horizontal bar (bottom = largest)

    states = [t[0] for t in top]
    displaced = [t[1]["displaced"] for t in top]

    fig, ax = plt.subplots(figsize=(10, 8))
    y = np.arange(len(states))
    ax.barh(y, displaced, color=C_RED, alpha=0.8)
    ax.set_yticks(y)
    ax.set_yticklabels(states, fontsize=9)
    ax.set_xlabel("Displaced Workers (thousands, Moderate Low Friction)")
    ax.set_title("Top 20 States by Estimated Displaced Workers\n(Proportional allocation via OEWS state employment shares)")

    fig.tight_layout()
    fig.savefig(os.path.join(CHART_DIR, filename), bbox_inches="tight")
    plt.close()
    print(f"  {filename}")


def chart_partisan_lean_vs_displacement(data, filename="pol_lean_scatter.png"):
    """Scatter plot: Edu_Partisan_Lean vs displacement, sized by employment."""
    _ensure_dir()

    valid = [r for r in data if r.get("Edu_Partisan_Lean") is not None and r.get("d_mod_low") is not None]
    if not valid:
        return

    x = [r["Edu_Partisan_Lean"] for r in valid]
    y = [r["d_mod_low"] for r in valid]
    sizes = [max(3, (r.get("Employment_2024_K", 0) or 0) / 10) for r in valid]

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.scatter(x, y, s=sizes, alpha=0.5, c=C_BLUE, edgecolors="white", linewidth=0.5)
    ax.axvline(0, color=C_GRAY, linestyle="--", linewidth=1, alpha=0.5)
    ax.set_xlabel("Education-Partisan Lean (- = Rep lean, + = Dem lean)")
    ax.set_ylabel("Displacement Rate (Moderate, Low Friction)")
    ax.set_title("Education-Partisan Lean vs. AI Displacement Risk")
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1, decimals=1))
    ax.annotate("Rep lean", xy=(min(x), 0), fontsize=9, color=C_RED, alpha=0.7)
    ax.annotate("Dem lean", xy=(max(x) * 0.7, 0), fontsize=9, color=C_BLUE, alpha=0.7)

    fig.tight_layout()
    fig.savefig(os.path.join(CHART_DIR, filename), bbox_inches="tight")
    plt.close()
    print(f"  {filename}")


def chart_education_displacement(data, filename="pol_education.png"):
    """Bar chart: displacement by typical entry education level."""
    _ensure_dir()

    edu_groups = defaultdict(lambda: {"emp": 0, "disp_sum": 0, "count": 0})

    for r in data:
        edu = r.get("Typical_Entry_Ed")
        if not edu or r.get("d_mod_low") is None:
            continue
        emp = r.get("Employment_2024_K", 0) or 0
        d = r.get("d_mod_low", 0) or 0
        edu_groups[edu]["emp"] += emp
        edu_groups[edu]["disp_sum"] += emp * d
        edu_groups[edu]["count"] += 1

    if not edu_groups:
        return

    # Sort by displacement rate
    items = []
    for edu, vals in edu_groups.items():
        rate = vals["disp_sum"] / vals["emp"] if vals["emp"] > 0 else 0
        items.append((edu, rate, vals["emp"], vals["count"]))
    items.sort(key=lambda x: x[1], reverse=True)

    labels = [i[0][:30] for i in items]
    rates = [i[1] for i in items]

    fig, ax = plt.subplots(figsize=(10, max(5, len(items) * 0.4)))
    y = np.arange(len(labels))
    ax.barh(y, rates, color=C_BLUE, alpha=0.8)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel("Emp-Weighted Mean Displacement Rate")
    ax.set_title("Displacement by Typical Entry Education")
    ax.xaxis.set_major_formatter(mticker.PercentFormatter(xmax=1, decimals=1))
    ax.invert_yaxis()

    fig.tight_layout()
    fig.savefig(os.path.join(CHART_DIR, filename), bbox_inches="tight")
    plt.close()
    print(f"  {filename}")


def generate_all_charts():
    """Generate all dashboard charts."""
    print("\nGenerating dashboard charts...")
    store.load()
    data = store.get_all()

    # Equity charts
    chart_wage_quintile_displacement(data)
    chart_gender_displacement(data)
    chart_displacement_by_demographic(data, "Pct_Female", "Female", "equity_female_bins.png")
    chart_displacement_by_demographic(data, "Pct_Black", "Black/African American", "equity_black_bins.png")
    chart_displacement_by_demographic(data, "Pct_Hispanic", "Hispanic/Latino", "equity_hispanic_bins.png")
    chart_displacement_by_demographic(data, "Pct_Over_55", "Workers Over 55", "equity_age55_bins.png")

    # Geographic chart -- load cached state shares
    from social_impact.config import STATE_SHARES_OUTPUT
    state_shares_path = STATE_SHARES_OUTPUT
    state_shares = {}
    if os.path.exists(state_shares_path):
        with open(state_shares_path) as f:
            state_shares = json.load(f)
        print(f"  Loaded state shares for {len(state_shares)} SOCs from {state_shares_path}")
    else:
        print(f"  WARNING: {state_shares_path} not found -- run social_impact/run.py first")

    chart_state_displacement_risk(data, state_shares=state_shares)

    # Political charts
    chart_partisan_lean_vs_displacement(data)
    chart_education_displacement(data)

    print("Charts complete.")


if __name__ == "__main__":
    generate_all_charts()
