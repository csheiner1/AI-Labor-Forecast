"""Compute d_max per sector from BLS JOLTS total separation rate data.

Fetches monthly TSR from the BLS public API, averages the most recent
full year, maps to the project's 21 model sectors, and computes:

    d_max = 1 - (1 - monthly_rate/100) ^ 18

This compounds the monthly separation rate to an 18-month window, giving
the maximum workforce reduction possible via natural attrition + turnover.

Output: scoring/dmax_results.json
"""
import json
import os
import urllib.request
import urllib.error
import warnings

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "dmax_results.json")
TARGET_YEAR = "2025"

# BLS JOLTS series IDs for total separation rate by supersector.
JOLTS_SERIES = {
    "finance_insurance":    "JTS520000000000000TSR",
    "information":          "JTS510000000000000TSR",
    "healthcare":           "JTS620000000000000TSR",
    "prof_business":        "JTS540099000000000TSR",
    "real_estate":          "JTS530000000000000TSR",
    "education":            "JTS610000000000000TSR",
    "government":           "JTS900000000000000TSR",
    "manufacturing":        "JTS300000000000000TSR",
    "retail":               "JTS440000000000000TSR",
    "construction":         "JTS230000000000000TSR",
    "transport_warehouse":  "JTS480099000000000TSR",
    "wholesale":            "JTS420000000000000TSR",
    "accommodation_food":   "JTS700000000000000TSR",
    "total_nonfarm":        "JTS000000000000000TSR",
}

# Map each of 21 model sectors to its JOLTS supersector key.
SECTOR_JOLTS_MAP = {
    "Finance & Banking":                "finance_insurance",
    "Insurance":                        "finance_insurance",
    "Technology & Software":            "information",
    "Healthcare & Life Sciences":       "healthcare",
    "Law Firms & Legal Services":       "prof_business",
    "Management Consulting Firms":      "prof_business",
    "Accounting & Tax Firms":           "prof_business",
    "Advertising & PR Agencies":        "prof_business",
    "Staffing & Recruitment Agencies":  "prof_business",
    "Real Estate & Property":           "real_estate",
    "Education & Academia":             "education",
    "Government & Public Administration": "government",
    "Media Publishing & Entertainment": "information",
    "Energy & Utilities":               "total_nonfarm",   # no direct JOLTS match
    "Architecture & Engineering Firms": "prof_business",
    "Manufacturing":                    "manufacturing",
    "Retail Trade":                     "retail",
    "Construction":                     "construction",
    "Transportation & Logistics":       "transport_warehouse",
    "Wholesale Trade":                  "wholesale",
    "Accommodation & Food Services":    "accommodation_food",
}

SECTOR_IDS = {
    "Finance & Banking": 1, "Insurance": 2, "Technology & Software": 3,
    "Healthcare & Life Sciences": 4, "Law Firms & Legal Services": 5,
    "Management Consulting Firms": 6, "Accounting & Tax Firms": 7,
    "Advertising & PR Agencies": 8, "Staffing & Recruitment Agencies": 9,
    "Real Estate & Property": 10, "Education & Academia": 11,
    "Government & Public Administration": 12,
    "Media Publishing & Entertainment": 13, "Energy & Utilities": 14,
    "Architecture & Engineering Firms": 15, "Manufacturing": 16,
    "Retail Trade": 17, "Construction": 18, "Transportation & Logistics": 19,
    "Wholesale Trade": 20, "Accommodation & Food Services": 21,
}

# Hardcoded fallback: 2025 average monthly TSR (%) from BLS JOLTS.
# Source: BLS JOLTS, accessed 2026-03-07.
FALLBACK_RATES = {
    "finance_insurance":    2.07,
    "information":          2.96,
    "healthcare":           2.80,
    "prof_business":        4.55,
    "real_estate":          2.50,
    "education":            2.22,
    "government":           1.38,
    "manufacturing":        2.47,
    "retail":               3.81,
    "construction":         4.03,
    "transport_warehouse":  3.88,
    "wholesale":            2.22,
    "accommodation_food":   5.45,
    "total_nonfarm":        3.30,
}

# --- Sector-level adjustments ---
# JOLTS groups several of our sectors under one supersector. Where we have
# good reason to believe turnover differs within a supersector, we override
# with an adjusted monthly TSR.  The JOLTS supersector rate is the
# employment-weighted average across its NAICS components, so our
# adjustments should roughly bracket it.
#
# Format: sector_name -> adjusted monthly TSR (%)
SECTOR_OVERRIDES = {
    # -- Professional & Business Services (JOLTS: 4.55%/mo) --
    # NAICS 54 (Professional/Technical) ≈ 3.0%/mo weighted avg
    # NAICS 56 (Administrative/Support) ≈ 6.5%/mo weighted avg
    # Blended ≈ 4.55% (matches JOLTS).
    #
    # Law (5411): credentialed, partnership track, low voluntary quit.
    # Annual turnover ~18-22% (NALP surveys). → ~1.8%/mo
    "Law Firms & Legal Services":       1.80,
    # Accounting (5412): seasonal tax staff inflates separations, but
    # core staff stable. Annual ~25%. → ~2.3%/mo
    "Accounting & Tax Firms":           2.30,
    # Architecture/Engineering (5413): licensed professionals, project-
    # based but low churn. Annual ~22-25%. → ~2.2%/mo
    "Architecture & Engineering Firms": 2.20,
    # Consulting (5416): up-or-out culture at major firms, high associate
    # turnover. Annual ~30-35%. → ~3.2%/mo
    "Management Consulting Firms":      3.20,
    # Advertising/PR (5418): creative churn, project-based, agency
    # culture. Annual ~30%. → ~3.0%/mo
    "Advertising & PR Agencies":        3.00,
    # Staffing (5613): inherits Prof & Business Services base rate.
    # Temp worker cycling inflates raw JOLTS separations but does not
    # represent displacement-susceptible turnover. No override needed.
    # "Staffing & Recruitment Agencies":  removed,

    # -- Information (JOLTS: 2.96%/mo) --
    # Tech/Software (5112, 5182, 5191): higher voluntary quits than
    # legacy media, especially 2021-2023. Annual ~35%. → ~3.3%/mo
    "Technology & Software":            3.30,
    # Media/Publishing (511x, 515, 516): legacy media shrinking but
    # remaining workforce is stable. Annual ~25%. → ~2.5%/mo
    "Media Publishing & Entertainment": 2.50,

    # -- Finance & Insurance (JOLTS: 2.07%/mo) --
    # Finance/Banking (521-523): branch consolidation, some churn.
    # Close to supersector avg. → ~2.15%/mo
    "Finance & Banking":                2.15,
    # Insurance (524): very stable, credentialed, low quit rate.
    # Annual ~18%. → ~1.70%/mo
    "Insurance":                        1.70,
}


def compute_dmax(monthly_tsr_pct):
    """Compute d_max from monthly total separation rate (%).

    d_max = 1 - (1 - monthly_rate/100) ^ 18
    """
    rate = monthly_tsr_pct / 100
    if rate <= 0:
        return 0.0
    if rate >= 1:
        return 1.0
    return round(1 - (1 - rate) ** 18, 4)


def average_monthly_rate(data_points, year=TARGET_YEAR):
    """Average monthly TSR values for a given year, excluding M13 (annual avg)."""
    monthly_values = []
    for d in data_points:
        if d["year"] == year and d["period"].startswith("M") and d["period"] != "M13":
            monthly_values.append(float(d["value"]))
    if not monthly_values:
        raise ValueError(f"No monthly data found for year {year}")
    if len(monthly_values) < 12:
        warnings.warn(
            f"Only {len(monthly_values)}/12 months available for {year}. "
            f"Average may be biased by seasonal effects."
        )
    return sum(monthly_values) / len(monthly_values)


def fetch_jolts_data(series_ids):
    """Fetch JOLTS data from BLS public API v1."""
    url = "https://api.bls.gov/publicAPI/v1/timeseries/data/"
    payload = json.dumps({"seriesid": series_ids}).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read().decode("utf-8"))

    if result.get("status") != "REQUEST_SUCCEEDED":
        raise RuntimeError(f"BLS API error: {result.get('message', result)}")

    out = {}
    for series in result.get("Results", {}).get("series", []):
        sid = series["seriesID"]
        out[sid] = series.get("data", [])
    return out


def fetch_all_jolts():
    """Fetch all required JOLTS series, batched for API limits."""
    unique_series = list(set(JOLTS_SERIES.values()))

    results = {}
    for i in range(0, len(unique_series), 10):
        batch = unique_series[i:i + 10]
        print(f"  Fetching batch {i // 10 + 1}: {len(batch)} series...")
        data = fetch_jolts_data(batch)
        results.update(data)

    rates = {}
    for key, series_id in JOLTS_SERIES.items():
        if series_id not in results:
            raise RuntimeError(f"Missing data for {key} ({series_id})")
        avg = average_monthly_rate(results[series_id])
        rates[key] = round(avg, 2)
        print(f"  {key}: {rates[key]}% monthly TSR")

    return rates


def main():
    # Try API first, fall back to hardcoded rates
    try:
        print("Fetching JOLTS data from BLS API...")
        rates = fetch_all_jolts()
        source = "api"
    except (urllib.error.URLError, RuntimeError, ValueError) as e:
        print(f"API fetch failed ({e}), using hardcoded 2025 fallback rates.")
        rates = FALLBACK_RATES.copy()
        source = "fallback"

    # Compute d_max for each sector
    results = []
    print(f"\n{'Sector':<45} {'Mo TSR':>7} {'d_max':>7}")
    print("-" * 62)

    for sector in sorted(SECTOR_JOLTS_MAP.keys(), key=lambda s: SECTOR_IDS[s]):
        jolts_key = SECTOR_JOLTS_MAP[sector]
        jolts_rate = rates[jolts_key]

        # Apply sector-level override if available
        if sector in SECTOR_OVERRIDES:
            monthly_tsr = SECTOR_OVERRIDES[sector]
            adj = "adj"
        else:
            monthly_tsr = jolts_rate
            adj = "   "

        d_max = compute_dmax(monthly_tsr)

        results.append({
            "sector_id": SECTOR_IDS[sector],
            "sector": sector,
            "jolts_key": jolts_key,
            "jolts_series": JOLTS_SERIES[jolts_key],
            "jolts_base_rate": jolts_rate,
            "monthly_tsr_pct": monthly_tsr,
            "adjusted": sector in SECTOR_OVERRIDES,
            "d_max": d_max,
            "source": source,
        })

        print(f"  {sector:<43} {monthly_tsr:>6.2f}% {d_max:>7.4f} {adj}")

    results.sort(key=lambda r: r["sector_id"])

    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nWrote {len(results)} sector d_max values to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
