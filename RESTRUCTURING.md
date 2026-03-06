# Data Architecture Restructuring Brief

This document is the primary reference for restructuring the AI labor displacement forecast model's data architecture. It defines the problems, the solution, every workbook change required, source files, and execution order.

---

## Context

The project forecasts AI-driven white-collar labor displacement. The master equation is:

```
d(t; i, s) = d_max(i) * phi(a(i,s)) * E(i) * T(t; i, s) * R(i)
```

The model maps tasks to jobs to industries. Task bundles determine job automatability; industry-level frictions (d_max, E, T, R) gate the speed and magnitude of displacement.

The current workbook is `jobs-data-v3.xlsx` with these key tabs:

| Tab | Contents |
|-----|----------|
| `1A Industries` | 71 NAICS codes mapped to 17 sectors |
| `1A Summary` | 17 sectors aggregated |
| `2 Jobs` | 462 occupations, each assigned to ONE primary sector |
| `Staffing Patterns` | 3,051 rows of sector x SOC employment shares |
| `2B Job_Industry` | Job x industry employment crosswalk |
| `Jobs_All_Industry` | Full 462 x 20 industry employment matrix (includes 3 "excluded" industries) |
| `3 Tasks` | 3,552 tasks x 2 scenarios with autonomy scores |
| `4 Results` | 462 rows with job-level scores and industry frictions applied |
| `Low/High Industry Frictions` | 17 rows each, one per sector |

---

## The Four Problems

### Problem A: Missing 30M White-Collar Workers

By categorizing work into 17 white-collar sectors, we omit ~30 million white-collar workers in blue-collar industries. V3 explicitly removed 5 sectors from the old data: Construction, Accommodation & Food Services, Staffing & Recruitment Agencies, Transportation & Warehousing, and Wholesale Trade. This cut 38 occupations and 303 tasks.

### Problem B: Blue-Collar Industry Friction Gaps

Simply adding blue-collar industries back and applying industry-level frictions doesn't fully work because we don't know those industries well enough to characterize all their frictions accurately.

### Problem C: Industry-Level Frictions Are Too Coarse

Within finance, an investment analyst and a customer service rep face very different demand elasticity. Demand elasticity is more occupation-specific than industry-specific -- customer service elasticity is similar whether the rep works in finance or healthcare. Yet the current model applies one set of frictions (d_max, E, T, R) to all 35 jobs in finance identically.

### Problem D: Industry Distinctions Still Matter

Institutional inertia, regulatory environment, capital availability -- these ARE genuinely industry-level. Dropping industry entirely would lose important signal.

---

## The Solution: Industry x Occupation Group Frictions

### Core Concept

Decompose the friction unit from "industry" to "industry x occupation group." Each of the 17-20 industries gets ~8-12 occupation groups, and frictions are scored at that intersection.

### Occupation Group Taxonomy

Two types of groups:

1. **Core groups** (3-5 per industry): Industry-specific occupations. Example for Finance: Front Office, Middle Office, Back Office, Retail Banking.
2. **Common groups** (~7-8, cross-cutting): Occupations that appear across many industries. Examples: Sales & BD, Customer Service, Marketing & Comms, Administrative Support, HR, IT Support, Finance & Accounting (internal), Legal & Compliance.

**Critical starting point:** The old workbook has a `1B Functions` sheet (in `archive/old_data/jobs-data-frictions-scoring-2.xlsx`) with 393 rows mapping SOC codes to functional categories. This is essentially the occupation-group concept and should be used as the starting point for the taxonomy. Function categories include: Executive & General Management, Finance Accounting & FP&A, Legal & Compliance, and more.

### Revised Equation

```
d(t; j, i, s) = d_max(i,g) * phi(a(j,s)) * E(i,g) * T(t; i,g,s) * R(i,g)
```

Where j = occupation, i = industry, g = occupation group, s = scenario.

### Scoring Economics

- 17-20 industries x 10-12 groups each = ~170-240 friction cells
- Each cell scored on d_max, E, T, R = ~680-960 individual friction values
- This is manually tractable (vs. 462 x 20 = 9,240 cells for full occupation x industry)

---

## What Needs to Change in the Workbook

### Tabs to Rebuild/Expand

#### `1A Industries` -- EXPAND

- Add back the 5 removed sectors: Construction, Accommodation & Food Services, Staffing & Recruitment Agencies, Transportation & Warehousing, Wholesale Trade
- Source: old workbook `archive/old_data/jobs-data-frictions-scoring-2.xlsx` has the NAICS mappings for all 20 sectors
- Alternatively, consolidate some (e.g., Transportation & Warehousing could merge into Logistics & Distribution which already exists in v3)
- Final target: ~20 sectors covering all white-collar employment

#### `2 Jobs` -- RESTRUCTURE

- Add back the 38 removed occupations from old workbook
- Remove the single-sector assignment as the primary organizing principle
- Add new column: `occupation_group_id` mapping each job to its group
- Keep occupation-level properties: SOC code, title, task coverage, workflow_simplicity, x_scale, x_sub
- The question "which industries does this job work in?" gets answered by the employment crosswalk, NOT by a primary sector column

#### `2B Job_Industry` / `Jobs_All_Industry` -- PROMOTE & VERIFY

- This tab already has the 462 x 20 employment distribution. Promote from reference to primary employment source.
- Add back the 38 removed occupations' cross-industry employment
- Verify employment figures for previously-excluded industries are complete (source: BLS OES)
- This becomes the primary employment crosswalk

#### `3 Tasks` -- ADD BACK REMOVED TASKS

- Add back the 303 tasks for the 38 removed occupations
- Source: old workbook `3 Tasks` sheet (3,855 tasks vs current 3,552)
- Task autonomy scores may need to be re-scored for the added tasks (they had single `Automatability_Score` in old format; v3 uses `Aut_Score_Mod` and `Aut_Score_Sig` for two scenarios)

### New Tabs to Create

#### `Occupation Groups` (NEW)

- Define ~76-100 groups: ~8 common + ~3-5 core per industry
- Columns: `group_id`, `group_name`, `group_type` (core/common), `primary_industry` (for core groups)
- Starting point: `1B Functions` sheet from old workbook

#### `Occupation -> Group Mapping` (NEW, or add column to `2 Jobs`)

- Map each of ~500 SOC codes to an occupation group
- Starting point: `1B Functions` already has `Function_ID` mapped to SOC codes

#### `Industry x Group Frictions` (NEW, replaces current friction tabs)

- ~170-240 rows: one per industry x occupation group with non-trivial employment
- Columns: `industry_id`, `group_id`, `d_max`, `E`, `T_low`, `T_high`, `R_low`, `R_high`
- Must be scored manually (this is the core analytical work)

#### `4 Results` -- RESTRUCTURE

- Expand from 462 rows to ~3,000+ rows (one per occupation x industry pair with non-zero employment)
- Each row gets automatability from the occupation + frictions from the industry x group lookup
- OR: keep 462 rows with weighted-average frictions (simpler but loses industry-level reporting)
- **Recommended:** expand to occupation x industry rows

### Tabs That Stay Unchanged

- `3 Tasks` structure (just add back removed tasks)
- Lookup tables (update to reflect expanded scope)

---

## Old Data Reference Files

### Primary Source: Pre-Consolidation Workbook

```
archive/old_data/jobs-data-frictions-scoring-2.xlsx
```

Key sheets to pull from:

| Sheet | Contents | Delta vs v3 |
|-------|----------|-------------|
| `1A Industries` | 76 NAICS codes across 20 sectors | v3 has 71 NAICS / 17 sectors |
| `1B Functions` | 393 rows mapping SOC codes to functional groups | **USE AS STARTING POINT for occupation group taxonomy** |
| `2 Jobs` | 446+ occupations | v3 has 462 (but 38 different ones removed) |
| `3 Tasks` | 3,855 tasks | v3 has 3,552 (303 removed). Old format has single `Automatability_Score`, not two-scenario `Aut_Score_Mod`/`Aut_Score_Sig` |
| `Staffing Patterns` | 6,035 rows across 20 sectors | v3 has 3,051 / 17 sectors |
| `Matrix` | Employment cross-tabulation summary | -- |

### BLS Source Data

```
archive/csv_intermediates/occupation.xlsx
```

Contains 1,116+ base occupation records.

---

## Execution Order

| Step | Action | Dependencies |
|------|--------|--------------|
| 1 | **Define occupation group taxonomy** -- Start from `1B Functions`, refine into core + common groups | None |
| 2 | **Expand `1A Industries`** -- Add back removed sectors from old workbook | None |
| 3 | **Expand `2 Jobs`** -- Add back 38 removed occupations, add `group_id` column, remove single-sector constraint | Steps 1, 2 |
| 4 | **Expand `3 Tasks`** -- Add back 303 tasks, re-score for two scenarios (Mod/Sig) | Step 3 |
| 5 | **Rebuild employment crosswalk** -- Promote `Jobs_All_Industry`, add removed occupations | Steps 2, 3 |
| 6 | **Create `Industry x Group Frictions` tab** -- Define ~170 cells, score manually | Steps 1, 2 |
| 7 | **Restructure `4 Results`** -- Expand to occupation x industry rows, update formulas | Steps 3, 4, 5, 6 |

Steps 1 and 2 can run in parallel. Steps 3, 4, and 5 depend on both. Step 6 depends on 1 and 2. Step 7 depends on everything.

---

## Scoring Pipeline Impact

The existing scoring pipeline (Phases 0-5 defined in `CLAUDE.md`) scores `workflow_simplicity`, `x_scale`, `x_sub` at the occupation level. These scores are occupation properties and do NOT change with the restructuring. The pipeline stays the same but needs to:

- Process ~500 occupations instead of 462 (add the 38 back)
- The Phase 2 sector groupings for parallel agents may shift slightly

The NEW manual scoring work is the ~680 Industry x Group friction values. This is separate from the automated scoring pipeline.
