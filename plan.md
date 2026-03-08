# Solution C: Attrition & Hiring Freeze Implementation Plan

## What We're Adding

Two new industry-level variables that model *how* displacement happens — not whether AI can do the work (that's `phi(a)`), but whether the workforce reduction comes via natural attrition vs. disruptive layoffs, and how much hiring slowdown is already baked in.

### New Variables

**A(i) — Attrition Capacity** (data-driven, NOT scored)
- Definition: The fraction of an industry's workforce that naturally turns over each year (quits, retirements, transfers)
- Source: BLS JOLTS quit rates by supersector, normalized to [0, 1]
- Range: 0.22 (Government, ~10% annual) to 1.00 (Accommodation & Food, ~45% annual)
- NOT scenario-dependent — structural industry property

**H(i,s) — Hiring Freeze Intensity** (scored, scenario-dependent)
- Definition: How aggressively firms in industry i are freezing/slowing hiring in scenario s
- Scale: 5-point {0.00 No freeze, 0.25 Mild slowdown, 0.50 Selective freeze, 0.75 Broad freeze, 1.00 Hard freeze}
- Scenario-dependent: Low scenario = less aggressive freezes; High scenario = more aggressive
- Scored per sector in 5L/5H Frictions tabs (alongside T1-T4, f1-f3, E)

### Modified Equation

Current: `d(t; i, s) = d_max * phi(a(i,s)) * E(i) * T(t; i, s) * R(i)`

New: `d(t; i, s) = d_max * phi(a(i,s)) * E(i) * T(t; i, s) * R(i) * G(i, s)`

Where: `G(i, s) = A(i) + H(i, s) * (1 - A(i))`

**Interpretation of G:**
- G represents the "displacement channel capacity" — what fraction of potential displacement can actually be realized
- A(i) alone provides the baseline: if 30% of workers quit annually, you can absorb 30% displacement just by not backfilling
- H(i,s) extends beyond natural attrition via active hiring freezes: if A(i) = 0.30 and H(i,s) = 0.50, then G = 0.30 + 0.50 * 0.70 = 0.65
- When G = 1.0: full displacement capacity (high attrition + hard freeze)
- When G is low (e.g., 0.25): only a quarter of theoretical displacement can actually happen in the time window
- G is always in [A(i), 1.0] — attrition alone sets the floor

**Why this works:** The current model computes *what percentage of jobs could be displaced*. G modulates *how much of that theoretical displacement can actually manifest* given labor market mechanics. Industries with high turnover (retail, food service) can absorb AI displacement silently through non-replacement. Low-turnover industries (government, energy) face a bottleneck.

---

## Implementation Steps

### Step 1: Create attrition data file
**File:** `scoring/attrition_rates.json`

Hardcoded from JOLTS data (not scored — these are empirical):
```json
{
  "source": "BLS JOLTS December 2025, annualized quit rates by supersector",
  "sectors": {
    "1":  {"name": "Finance & Banking", "jolts_supersector": "Financial activities", "annual_quit_rate": 0.17, "A": 0.38},
    "2":  {"name": "Insurance", "jolts_supersector": "Financial activities", "annual_quit_rate": 0.17, "A": 0.38},
    ...
    "21": {"name": "Accommodation & Food Services", "jolts_supersector": "Accommodation and food services", "annual_quit_rate": 0.45, "A": 1.00}
  }
}
```

### Step 2: Add H(i,s) column to 5L/5H Frictions tabs
**File:** `rebuild_frictions_tabs.py`

Add column V (col 22): `H — Hiring Freeze Intensity` with header styling matching existing columns. Pre-fill blank for manual scoring.

Column layout change:
- Current cols A-U (1-21): unchanged
- New col V (22): `H\nHiring Freeze\nIntensity`

### Step 3: Add A(i) and G columns to 5L/5H Frictions tabs
**File:** `rebuild_frictions_tabs.py`

Add columns W-X (23-24):
- Col W (23): `A(i)\nAttrition\nCapacity` — auto-filled from attrition_rates.json (read-only, data-driven)
- Col X (24): `G\nDisplacement\nChannel` — Excel formula: `=W{row} + V{row} * (1 - W{row})`

### Step 4: Add columns to 4 Results tab
**File:** phase5_writeback.py or a new script

Add 4 new columns after existing col 30:
- Col 31: `A_attrition` — from attrition_rates.json, looked up by sector
- Col 32: `H_freeze_low` — from 5L Frictions
- Col 33: `H_freeze_high` — from 5H Frictions
- Col 34: `G_low` — computed: A + H_low * (1 - A)
- Col 35: `G_high` — computed: A + H_high * (1 - A)

The existing d_mod_low/high and d_sig_low/high columns (23-26) and displaced_K columns (27-30) will need their formulas updated to multiply by G.

### Step 5: Update validate_workbook.py
Add validation for:
- H values in {0.00, 0.25, 0.50, 0.75, 1.00}
- A values present for all 21 sectors
- G = A + H*(1-A) formula check
- G in [0, 1]
- H_high >= H_low (more aggressive scenario = more freezing)

### Step 6: Update methodology PDF
**File:** `docs/generate_methodology.py`

- Add Section 5.x: "Attrition Capacity & Hiring Freeze Channel"
- Update master equation display
- Add G(i,s) explanation with the JOLTS data table
- Add H scoring rubric
- Reference historical precedents (ATMs/tellers, "low-hire low-fire" 2025 dynamics)

### Step 7: Update CLAUDE.md
Add A(i) and H(i,s) to the master equation and key design rules.

---

## What This Does NOT Change
- Task-level scoring (Layer 1) — untouched
- Job-level scoring pipeline (workflow_simplicity, x_scale, x_sub) — untouched
- phi(a) sigmoid — untouched
- d_max constant (0.18) — untouched
- T, R, E scoring — untouched
- The existing 5L/5H structure — extended, not replaced

## Key Design Decision: Why G Multiplies the Whole Expression

G acts as a "realization rate" on theoretical displacement. The product `d_max * phi(a) * E * T * R` tells us what *could* happen technically and institutionally. G tells us what fraction of that potential *actually manifests as headcount reduction* within the forecast window, given labor market dynamics.

This is multiplicative because:
1. If attrition is high (A=1.0), nearly all theoretical displacement can be silently absorbed → G≈1.0, no dampening
2. If attrition is low AND no freeze (A=0.22, H=0), only 22% of displacement manifests → strong dampening
3. Hiring freezes extend the channel beyond natural attrition, approaching full realization

## Files Modified (7 files)
1. `scoring/attrition_rates.json` — NEW (data file)
2. `rebuild_frictions_tabs.py` — add H, A, G columns
3. `validate_workbook.py` — add H/A/G validation
4. `docs/generate_methodology.py` — add methodology section
5. `CLAUDE.md` — update equation and variable list
6. `scoring/phase5_writeback.py` — add A/G to results (after H is scored)
7. `jobs-data-v3.xlsx` — rebuilt with new columns (via rebuild script)
