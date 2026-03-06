"""Merge all social impact data sources onto project SOCs.

Join strategy per source:
1. CPSAAT11/11B (demographics): Crosswalk-first matching:
   SOC -> Census codes (via build_soc_lookup) -> Census titles -> fuzzy match CPSAAT text
   Fallback 1: direct fuzzy match SOC title to CPSAAT text
   Fallback 2: major-group averaging
2. Education attainment/entry: Direct SOC match
3. Union rates: 2-digit SOC major group
4. Foreign-born: 2-digit SOC major group (hardcoded from BLS report)
5. OEWS state/metro: Direct SOC match
6. Edu_Partisan_Lean: Derived from pct_bachelors_plus
"""
import json
import os
import re
from collections import defaultdict

from social_impact.config import (
    WORKBOOK, MERGED_OUTPUT, STATE_SHARES_OUTPUT, DATA_CACHE,
    FOREIGN_BORN_BY_MAJOR_GROUP, EDU_PARTISAN_COLLEGE, EDU_PARTISAN_NO_COLLEGE,
)
from social_impact.crosswalk import (
    load_crosswalk, load_project_socs, build_soc_lookup,
)
from social_impact.parse_demographics import parse_cpsaat11, parse_cpsaat11b
from social_impact.parse_education import parse_education_attainment, parse_entry_education
from social_impact.parse_union import get_union_rate
from social_impact.parse_oews import parse_oews_state, parse_oews_metro_lq


def _fuzzy_match_occupation(target_text, demo_data, threshold=0.65):
    """Try to match an occupation title text to CPSAAT11 entries.

    Uses progressively looser matching:
    1. Exact match (case-insensitive)
    2. Target contained in key or key contained in target
    3. Word overlap ratio >= threshold
    """
    target_lower = target_text.lower().strip()
    target_words = set(re.findall(r'\w+', target_lower))

    # Exact match
    for key in demo_data:
        if key.lower().strip() == target_lower:
            return key

    # Containment match -- require both strings >= 15 chars to avoid
    # false positives on short generic strings (e.g. "Managers")
    best_contain = None
    best_contain_len = float("inf")
    for key in demo_data:
        key_lower = key.lower().strip()
        if len(target_lower) >= 15 and len(key_lower) >= 15:
            if target_lower in key_lower or key_lower in target_lower:
                # Prefer shortest containing match to reduce false positives
                if len(key_lower) < best_contain_len:
                    best_contain = key
                    best_contain_len = len(key_lower)
    if best_contain is not None:
        return best_contain

    # Word overlap
    best_match = None
    best_score = 0
    for key in demo_data:
        key_words = set(re.findall(r'\w+', key.lower()))
        if not key_words or not target_words:
            continue
        overlap = len(target_words & key_words) / max(len(target_words), len(key_words))
        if overlap > best_score and overlap >= threshold:
            best_score = overlap
            best_match = key

    return best_match


def _match_demographics_to_socs(demo_data, project_socs, soc_census_lookup,
                                 census_titles):
    """Match CPSAAT demographic data to project SOCs.

    Works for ANY field set -- auto-detects numeric fields from the data.
    This means the same function works for CPSAAT11 (race/gender fields like
    pct_female, pct_white, etc.) AND CPSAAT11B (age fields like median_age,
    pct_over_55).

    Matching strategy (crosswalk-first):
    1. PRIMARY: Use crosswalk. For each project SOC, get its Census codes
       via soc_census_lookup (from build_soc_lookup). For each Census code,
       get the Census title from census_titles. Fuzzy-match that title
       against the CPSAAT occupation text keys. If multiple Census codes
       map to one SOC, average the demographics weighted by total_employed_K.
    2. FALLBACK 1: Direct fuzzy match of the SOC's workbook title against
       CPSAAT occupation text (catches cases where crosswalk has no mapping
       but the title is recognizable).
    3. FALLBACK 2: Major-group averaging -- average all CPSAAT entries whose
       Census codes map to SOCs in the same 2-digit major group.
    """
    matched = {}
    needs_group_fallback = []

    demo_by_text = demo_data  # already keyed by occ text

    # Auto-detect numeric fields from the first entry (excluding total_employed_K)
    numeric_fields = []
    if demo_by_text:
        sample = next(iter(demo_by_text.values()))
        numeric_fields = [k for k in sample.keys() if k != "total_employed_K"]

    # Track match sources for reporting
    match_sources = {"crosswalk": 0, "title_fuzzy": 0, "major_group": 0}

    # --- Pass 1: Match via crosswalk and title fuzzy ---
    for soc, meta in project_socs.items():
        title = meta["title"]
        census_codes = soc_census_lookup.get(soc, [])

        # === Strategy 1 (PRIMARY): Crosswalk-based matching ===
        crosswalk_matches = []
        for census_code in census_codes:
            census_title = census_titles.get(census_code, "")
            if not census_title:
                continue
            match = _fuzzy_match_occupation(census_title, demo_by_text, threshold=0.65)
            if match:
                crosswalk_matches.append(demo_by_text[match])

        if crosswalk_matches:
            if len(crosswalk_matches) == 1:
                matched[soc] = crosswalk_matches[0]
            else:
                # Average multiple Census-code matches, weighted by total_employed_K
                avg = {}
                for field in numeric_fields:
                    weighted_sum = sum(
                        (m.get(field) or 0) * (m.get("total_employed_K", 1) or 1)
                        for m in crosswalk_matches if m.get(field) is not None
                    )
                    contributing = [m for m in crosswalk_matches if m.get(field) is not None]
                    if contributing:
                        contrib_emp = sum(m.get("total_employed_K", 1) or 1 for m in contributing)
                        avg[field] = round(weighted_sum / contrib_emp, 1)
                    else:
                        avg[field] = None
                matched[soc] = avg
            match_sources["crosswalk"] += 1
            continue

        # === Strategy 2 (FALLBACK 1): Direct title fuzzy match ===
        match = _fuzzy_match_occupation(title, demo_by_text, threshold=0.65)
        if match:
            matched[soc] = demo_by_text[match]
            match_sources["title_fuzzy"] += 1
            continue

        # Defer to pass 2 for major-group averaging
        needs_group_fallback.append(soc)

    # --- Pass 2: Major-group averaging using all pass-1 matches ---
    unmatched = []
    for soc in needs_group_fallback:
        major = soc.split("-")[0]
        group_vals = [
            matched[other_soc]
            for other_soc in matched
            if other_soc.startswith(major + "-")
        ]

        if group_vals:
            avg = {}
            for field in numeric_fields:
                vals = [v[field] for v in group_vals if v.get(field) is not None]
                avg[field] = round(sum(vals) / len(vals), 1) if vals else None
            matched[soc] = avg
            match_sources["major_group"] += 1
        else:
            unmatched.append(soc)

    print(f"  Demographics matched: {len(matched)}/{len(project_socs)}")
    print(f"    Crosswalk: {match_sources['crosswalk']}, "
          f"Title fuzzy: {match_sources['title_fuzzy']}, "
          f"Major-group avg: {match_sources['major_group']}")
    if unmatched:
        print(f"  Unmatched ({len(unmatched)}): {unmatched[:10]}...")

    return matched


def compute_edu_partisan_lean(pct_bachelors_plus):
    """Compute education-partisan lean proxy.

    Based on Pew Research: college grads lean D+13, non-college lean R+6.
    Returns a value from -0.06 (fully non-college, R lean) to +0.13 (fully college, D lean).
    Positive = Democratic lean, negative = Republican lean.
    """
    if pct_bachelors_plus is None:
        return None
    pct = pct_bachelors_plus / 100.0  # convert from percentage to fraction
    lean = pct * EDU_PARTISAN_COLLEGE + (1 - pct) * EDU_PARTISAN_NO_COLLEGE
    return round(lean, 4)


def merge_all():
    """Run the full merge pipeline.

    Returns:
        list of dicts, one per SOC, with all social impact columns.
    """
    print("\n=== Social Impact Data Merge ===\n")

    # 1. Load project SOCs
    project_socs = load_project_socs()

    # 2. Load crosswalk and build SOC->Census lookup
    census_to_soc, soc_to_census, census_titles = load_crosswalk()
    soc_census_lookup = build_soc_lookup(project_socs, soc_to_census)

    # 3. Parse demographics -- use crosswalk as primary matching strategy
    print("\nParsing demographics (CPSAAT11)...")
    demo_data = parse_cpsaat11()
    demo_matched = _match_demographics_to_socs(demo_data, project_socs,
                                                soc_census_lookup, census_titles)

    print("\nParsing age data (CPSAAT11B)...")
    age_data = parse_cpsaat11b()
    age_matched = _match_demographics_to_socs(age_data, project_socs,
                                               soc_census_lookup, census_titles)

    # 4. Parse education
    print("\nParsing education data...")
    edu_attain = parse_education_attainment()
    entry_edu = parse_entry_education()

    # 5. Parse geographic data
    print("\nParsing OEWS state data...")
    soc_set = set(project_socs.keys())
    state_data, state_shares = parse_oews_state(soc_set)

    print("\nParsing OEWS metro data...")
    metro_data = parse_oews_metro_lq(soc_set)

    # 6. Merge everything
    print("\nMerging all sources...")
    results = []

    for soc, meta in sorted(project_socs.items()):
        row = {
            "SOC_Code": soc,
            "Job_Title": meta["title"],
        }

        # Demographics
        demo = demo_matched.get(soc, {})
        row["Pct_Female"] = demo.get("pct_female")
        row["Pct_White"] = demo.get("pct_white")
        row["Pct_Black"] = demo.get("pct_black")
        row["Pct_Asian"] = demo.get("pct_asian")
        row["Pct_Hispanic"] = demo.get("pct_hispanic")

        # Age
        age = age_matched.get(soc, {})
        row["Median_Age"] = age.get("median_age")
        row["Pct_Over_55"] = age.get("pct_over_55")

        # Education -- try direct SOC match, then first code of merged SOC
        edu = edu_attain.get(soc, {})
        if not edu and "," in soc:
            for s in soc.split(","):
                edu = edu_attain.get(s.strip(), {})
                if edu:
                    break
        row["Pct_Bachelors_Plus"] = edu.get("pct_bachelors_plus")
        row["Pct_Graduate_Deg"] = edu.get("pct_graduate_deg")

        entry = entry_edu.get(soc)
        if not entry and "," in soc:
            for s in soc.split(","):
                entry = entry_edu.get(s.strip())
                if entry:
                    break
        row["Typical_Entry_Ed"] = entry

        # Foreign born (major group level)
        major = soc.split("-")[0]
        row["Pct_Foreign_Born"] = FOREIGN_BORN_BY_MAJOR_GROUP.get(major)

        # Union rate (major group level)
        row["Union_Rate_Pct"] = get_union_rate(soc)

        # Education-partisan lean (derived)
        row["Edu_Partisan_Lean"] = compute_edu_partisan_lean(row["Pct_Bachelors_Plus"])

        # Geographic
        top_states = state_data.get(soc, [])
        if not top_states and "," in soc:
            for s in soc.split(","):
                top_states = state_data.get(s.strip(), [])
                if top_states:
                    break
        row["Top_State_1"] = top_states[0] if len(top_states) > 0 else None
        row["Top_State_2"] = top_states[1] if len(top_states) > 1 else None
        row["Top_State_3"] = top_states[2] if len(top_states) > 2 else None

        metro_lq = metro_data.get(soc)
        if not metro_lq and "," in soc:
            for s in soc.split(","):
                metro_lq = metro_data.get(s.strip())
                if metro_lq:
                    break
        row["Top_Metro_LQ"] = metro_lq

        results.append(row)

    # Report coverage
    print(f"\n--- Merge Coverage Report ---")
    for col in ["Pct_Female", "Pct_White", "Pct_Black", "Pct_Asian", "Pct_Hispanic",
                 "Median_Age", "Pct_Over_55", "Pct_Bachelors_Plus", "Pct_Graduate_Deg",
                 "Typical_Entry_Ed", "Pct_Foreign_Born", "Union_Rate_Pct",
                 "Edu_Partisan_Lean", "Top_State_1", "Top_Metro_LQ"]:
        filled = sum(1 for r in results if r.get(col) is not None)
        print(f"  {col}: {filled}/{len(results)} ({100*filled/len(results):.0f}%)")

    # Save intermediate JSON
    os.makedirs(os.path.dirname(MERGED_OUTPUT), exist_ok=True)
    with open(MERGED_OUTPUT, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved {len(results)} records to {MERGED_OUTPUT}")

    # Save state employment shares for geographic chart generation
    with open(STATE_SHARES_OUTPUT, "w") as f:
        json.dump(state_shares, f, indent=2)
    print(f"Saved state shares for {len(state_shares)} SOCs to {STATE_SHARES_OUTPUT}")

    return results


if __name__ == "__main__":
    merge_all()
