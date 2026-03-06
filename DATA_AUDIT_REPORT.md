# Data Integrity Audit Report

**Date:** 2026-03-05
**Workbook:** `jobs-data-v3.xlsx`
**Source data:** BLS Employment Projections 2024–2034, NIOEM crosswalk, O*NET

---

## Executive Summary

The workbook's SOC and NAICS codes are valid and correctly mapped. The core data integrity is sound. However, six issues require attention before restructuring:

| # | Issue | Severity | Scope |
|---|-------|----------|-------|
| 1 | 25 SOC codes have duplicate task sets in `3 Tasks` | **High** | 25 occupations |
| 2 | 45 white-collar SOC codes missing from model entirely | **High** | ~14M workers |
| 3 | 7,087K workers in excluded industries (3 dropped sectors) | **High** | 7.1M workers |
| 4 | 817 staffing pattern employment mismatches vs BLS source | **Medium** | crosswalk |
| 5 | 1A Summary employment totals don't match 1A Industries sums | **Low** | 17 sectors |
| 6 | 1 orphan SOC in Tasks (15-1244) with no matching job row | **Low** | 1 occupation |

---

## Issue 1: Duplicate Task Sets (HIGH)

**25 SOC codes have tasks repeated multiple times** in `3 Tasks`, causing time shares to sum to 200%–600% instead of ~100%. This happens because a single BLS SOC code is used for multiple custom job titles (e.g., SOC 13-1111 maps to Management Consultant, Strategy Consultant, Business Analyst, Operations Consultant, Policy Analyst, Operations Analyst — 6 titles), and the task battery was duplicated for each.

**Affected SOC codes (25):**

| SOC | Custom Titles | Tasks | Time Share Sum |
|-----|--------------|-------|----------------|
| 13-1111 | Management/Strategy/Business/Ops Consultant, Policy/Ops Analyst | 46 | 600% |
| 15-2051 | Data Scientist, Clinical Data Mgr, Data Analyst, BI Analyst | 46 | 600% |
| 13-2051 | Financial Analyst, Portfolio Mgr, Risk Analyst, Treasury Analyst, Energy Analyst | 40 | 500% |
| 15-1252 | Software Engineer, DevOps, ML Engineer, SRE, Backend Dev | 40 | 500% |
| 11-2021 | Product/Marketing/Brand/BD Manager | 36 | 400% |
| 11-1011 | CEO, COO, CFO, CTO | 36 | 400% |
| 13-2011 | Fund Accountant, Auditor, CPA, Forensic Accountant | 36 | 400% |
| 15-1211 | Systems Analyst, Health Informatics Analyst, IT Consultant | 27 | 300% |
| 15-1241 | Cloud Architect, Solutions Architect, Network Engineer | 24 | 300% |
| 11-3071 | Supply Chain/Logistics/Warehouse Manager | 24 | 300% |
| 19-1042 | Clinical Research Assoc, Medical Science Liaison, Pharmacovigilance | 21 | 300% |
| 13-2099 | Investment Banker, Quant Analyst, Financial specialists | 24 | 300% |
| 11-1021 | Plant Manager, Retail Store Manager | 24 | 300% |
| + 12 more with 2 titles each | | | 200% |

**Impact:** Task coverage and autonomy fraction calculations will be distorted if duplicate tasks aren't handled properly. The dedup_employment_K and economy_weight_K columns may also double-count.

**Resolution:** Deduplicate tasks so each SOC code's task battery appears once. The task-to-job mapping needs to be one-to-many (one task set → multiple custom titles), not duplicated.

---

## Issue 2: Missing White-Collar Occupations (HIGH)

**45 white-collar BLS line-item SOC codes are entirely absent** from both `2 Jobs` and `Jobs_All_Industry`. Several are very large:

| SOC | Title | BLS Employment (K) | Category |
|-----|-------|-------------------|----------|
| 41-2031 | Retail salespersons | 3,936.7 | Sales |
| 41-2011 | Cashiers | 3,157.2 | Sales |
| 43-9061 | Office clerks, general | 2,646.0 | Admin |
| 41-1011 | First-line supervisors of retail sales | 1,432.6 | Sales |
| 41-4012 | Sales reps, wholesale/manufacturing | 1,310.5 | Sales |
| 13-1071 | Human resources specialists | 944.3 | Business |
| 43-5071 | Shipping/receiving/inventory clerks | 862.2 | Admin |
| 11-9013 | Farmers/ranchers/agricultural managers | 836.1 | Management |
| 25-3031 | Substitute teachers | 510.1 | Education |
| 29-2052 | Pharmacy technicians | 490.4 | Healthcare |
| 41-2021 | Counter and rental clerks | 408.2 | Sales |
| 11-9051 | Food service managers | 352.8 | Management |
| 29-1051 | Pharmacists | 335.1 | Healthcare |
| 43-5052 | Postal service mail carriers | 319.4 | Admin |
| + 31 more smaller occupations | | | |

**Note:** Some exclusions are defensible (cashiers, retail salespersons, mail carriers may be considered non-white-collar). But **HR specialists (944K)**, **pharmacists (335K)**, **pharmacy technicians (490K)**, and **substitute teachers (510K)** appear to be genuine gaps.

**Cross-reference with old data:** The old workbook (`jobs-data-frictions-scoring-2.xlsx`) included some of these — e.g., pharmacists, pharmacy technicians, food service managers, substitute teachers — under the sectors that were later dropped.

---

## Issue 3: Excluded Industry Employment (HIGH)

**3 sectors were dropped** from the 20-sector model, leaving 7,087K workers unmodeled:

| Dropped Sector | NAICS Codes |
|---|---|
| Construction | 236, 237, 238 |
| Accommodation & Food Services | 721, 722 |
| Staffing & Recruitment Agencies | 5613 |

The white-collar workers in these sectors are currently excluded. Top affected occupations:

| SOC | Title | Excluded Emp (K) | % of Total |
|-----|-------|-----------------|------------|
| 11-1021 | General and operations managers | 550.5 | 23% |
| 11-9021 | Construction managers | 283.4 | 86% |
| 13-1082 | Project management specialists | 252.5 | 28% |
| 43-6014 | Secretaries/admin assistants | 198.9 | 19% |
| 43-3031 | Bookkeeping clerks | 192.6 | 20% |

---

## Issue 4: Staffing Pattern Crosswalk Discrepancies (MEDIUM)

- **817 (sector, SOC) pairs** have employment differences > 1K between the workbook's `Staffing Patterns` tab and the BLS source CSV.
- Some are extreme (e.g., Sector 4 / SOC 29-1141 shows WB=2,682K vs BLS=0.5K — a 536,000% diff), suggesting a column mapping or aggregation error during the crosswalk build.
- **482 (sector, SOC) pairs** exist in the workbook but not in the BLS source file, concentrated in Sector 17 (Logistics & Distribution), likely because this sector was consolidated from multiple old sectors.

**Resolution:** Rebuild `Staffing Patterns` from the raw NIOEM data with the current 17-sector (or expanded 20-sector) mapping.

---

## Issue 5: 1A Summary Rounding Discrepancies (LOW)

All 17 sectors show small employment mismatches between `1A Summary` totals and the computed sum from `1A Industries` rows (0.1%–2% range). Likely a data vintage or rounding issue.

Additionally, **Sector 10 (Education & Academia)** shows 3 NAICS codes in the summary but actually has 4 in `1A Industries` (the synthetic `Pub_K12` code was added but the count wasn't updated).

**Resolution:** Recompute `1A Summary` from `1A Industries`.

---

## Issue 6: Orphan SOC in Tasks (LOW)

SOC **15-1244** (Network and computer systems administrators) has tasks in `3 Tasks` but no corresponding row in `2 Jobs`.

**Resolution:** Either add 15-1244 to `2 Jobs` or remove its tasks from `3 Tasks`.

---

## What Validated Clean

- **All 408 unique SOC codes** in the workbook are valid BLS line-item codes (not summary-level).
- **All 71 NAICS codes** are valid (1 synthetic `Pub_K12` is documented as "Estimated").
- **Title-to-SOC mappings** are correct — custom titles are legitimate narrowings of BLS categories.
- **No SOC codes in Tasks are missing from BLS.**
- **Jobs_All_Industry internal arithmetic** is clean (`Modeled_17 + Excluded_3 = All_20` holds).
- **All 3,552 autonomy scores** are in valid [0, 1] range with 100% coverage.
- **All 19 GWA values** are valid O*NET Generalized Work Activity labels.
- **All tasks have complete data** — no missing descriptions, types, importance, or GWA values.

---

## Recommended Fix Order

1. **Deduplicate tasks** (Issue 1) — prerequisite for correct scoring
2. **Decide on missing occupations** (Issue 2) — which of the 45 to add back
3. **Decide on excluded sectors** (Issue 3) — restore the 3 dropped sectors?
4. **Rebuild staffing patterns** (Issue 4) — from raw NIOEM with final sector mapping
5. **Recompute 1A Summary** (Issue 5) — simple formula refresh
6. **Fix orphan SOC** (Issue 6) — add or remove 15-1244
