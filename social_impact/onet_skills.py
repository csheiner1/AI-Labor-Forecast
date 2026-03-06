"""Extract O*NET skills and knowledge vectors for transition pathway computation.

Reads Skills.txt and Knowledge.txt from the local O*NET database.
Produces a normalized skill/knowledge profile per SOC that can be used
for cosine similarity-based occupation matching.
"""
import os
import csv
import threading
import numpy as np
from collections import defaultdict

from social_impact.config import ONET_DIR


def _normalize_soc(onet_soc):
    """Convert O*NET SOC (e.g. '11-1011.00') to project format ('11-1011')."""
    soc = str(onet_soc).strip()
    if soc.endswith(".00"):
        soc = soc[:-3]
    # Handle specializations like '15-1252.01' -> '15-1252'
    if "." in soc:
        soc = soc.split(".")[0]
    return soc


def load_onet_dimension(filename, scale_id="LV"):
    """Load one O*NET dimension (Skills, Knowledge, or Abilities).

    Args:
        filename: e.g. 'Skills.txt'
        scale_id: 'LV' for level (default), 'IM' for importance

    Returns:
        dict: soc_code -> {element_name: score, ...}
    """
    filepath = os.path.join(ONET_DIR, filename)
    if not os.path.exists(filepath):
        print(f"  WARNING: {filepath} not found")
        return {}

    # Accumulate (sum, count) per (soc, element) so we can compute a correct
    # mean when multiple O*NET specializations map to the same 6-digit SOC.
    accum = defaultdict(lambda: defaultdict(lambda: [0.0, 0]))
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            if row.get("Scale ID") != scale_id:
                continue
            if row.get("Recommend Suppress") == "Y":
                continue

            onet_soc = row.get("O*NET-SOC Code", "")
            soc = _normalize_soc(onet_soc)
            element = row.get("Element Name", "").strip()
            try:
                score = float(row.get("Data Value", 0))
            except (ValueError, TypeError):
                continue

            if element and score > 0:
                accum[soc][element][0] += score
                accum[soc][element][1] += 1

    # Convert accumulated (sum, count) to mean scores
    soc_profiles = {}
    for soc, elements_dict in accum.items():
        soc_profiles[soc] = {
            elem: total / count
            for elem, (total, count) in elements_dict.items()
        }

    print(f"  {filename}: {len(soc_profiles)} SOCs, "
          f"{len(set(e for p in soc_profiles.values() for e in p))} elements")
    return soc_profiles


def build_skill_vectors(project_socs=None):
    """Build combined skill+knowledge vectors for all SOCs.

    Combines Skills (35 elements) and Knowledge (33 elements) into
    a single 68-dimension vector per SOC. Values are O*NET level scores (0-7).

    Args:
        project_socs: optional set of SOC codes to filter for

    Returns:
        tuple: (soc_list, element_names, matrix)
            soc_list: list of SOC codes
            element_names: list of element names (ordered)
            matrix: numpy array shape (n_socs, n_elements)
    """
    print("\nBuilding O*NET skill vectors...")

    skills = load_onet_dimension("Skills.txt", "LV")
    knowledge = load_onet_dimension("Knowledge.txt", "LV")

    # Combine into one profile per SOC
    all_socs = set(skills.keys()) | set(knowledge.keys())
    if project_socs:
        all_socs = all_socs & set(project_socs)

    # Collect all element names
    skill_elements = sorted(set(e for p in skills.values() for e in p))
    knowledge_elements = sorted(set(e for p in knowledge.values() for e in p))
    all_elements = skill_elements + knowledge_elements

    # Build matrix
    soc_list = sorted(all_socs)
    matrix = np.zeros((len(soc_list), len(all_elements)), dtype=np.float64)

    for i, soc in enumerate(soc_list):
        skill_profile = skills.get(soc, {})
        knowledge_profile = knowledge.get(soc, {})
        for j, element in enumerate(all_elements):
            if element in skill_profile:
                matrix[i, j] = skill_profile[element]
            elif element in knowledge_profile:
                matrix[i, j] = knowledge_profile[element]

    # Precompute lookup and row norms for efficient similarity queries
    soc_to_idx = {soc: i for i, soc in enumerate(soc_list)}
    norms = np.linalg.norm(matrix, axis=1)

    print(f"  Skill vectors: {matrix.shape[0]} SOCs x {matrix.shape[1]} dimensions")
    return soc_list, all_elements, matrix, soc_to_idx, norms


def find_transition_targets(soc_code, soc_list, matrix, displacement_data,
                            n_candidates=10, max_displacement=0.15,
                            soc_to_idx=None, norms=None):
    """Find transition targets for a high-displacement SOC.

    Uses cosine similarity between skill/knowledge vectors to find
    similar occupations with lower displacement rates.

    Args:
        soc_code: Source SOC code
        soc_list: List of all SOC codes (matches matrix rows)
        matrix: Skill vector matrix (n_socs x n_elements)
        displacement_data: dict soc -> {d_mod_low, d_sig_low, employment_K, ...}
        n_candidates: Number of candidates to return
        max_displacement: Maximum displacement rate for a viable target
        soc_to_idx: Optional precomputed {soc: row_index} dict (O(1) lookup)
        norms: Optional precomputed row norms array

    Returns:
        list of dicts: [{soc, title, similarity, displacement, shared_skills}, ...]
    """
    # Use precomputed index if available, else fall back to list search
    if soc_to_idx is not None:
        idx = soc_to_idx.get(soc_code)
        if idx is None:
            return []
    else:
        if soc_code not in soc_list:
            return []
        idx = soc_list.index(soc_code)

    source_vec = matrix[idx]

    # Use precomputed norms if available
    if norms is None:
        norms = np.linalg.norm(matrix, axis=1)
    source_norm = norms[idx]
    if source_norm == 0:
        return []

    denom = norms * source_norm
    denom[denom == 0] = 1e-10  # avoid division by zero
    with np.errstate(over="ignore", invalid="ignore"):
        similarities = (matrix @ source_vec) / denom
    similarities = np.nan_to_num(similarities, nan=0.0)

    # Rank and filter
    candidates = []
    for i in np.argsort(-similarities):
        other_soc = soc_list[i]
        if other_soc == soc_code:
            continue
        sim = similarities[i]
        if sim < 0.5:  # Below 0.5 similarity is not a realistic transition
            break

        disp = displacement_data.get(other_soc, {})
        d_rate = disp.get("d_mod_low") or 0.5  # default high if unknown/None
        if d_rate > max_displacement:
            continue

        candidates.append({
            "soc": other_soc,
            "title": disp.get("title", ""),
            "similarity": round(float(sim), 3),
            "d_mod_low": round(d_rate, 3),
            "employment_K": disp.get("employment_K", 0),
        })

        if len(candidates) >= n_candidates:
            break

    return candidates


# Module-level cache (thread-safe)
_cached_vectors = None
_cached_socs = None
_cache_lock = threading.Lock()

def get_cached_vectors(project_socs=None):
    """Return cached skill vectors, building on first call.

    If called with a different project_socs set than the cached one,
    invalidates and rebuilds the cache.  Thread-safe via double-check
    locking.
    """
    global _cached_vectors, _cached_socs
    soc_key = frozenset(project_socs) if project_socs else None
    if _cached_vectors is None or soc_key != _cached_socs:
        with _cache_lock:
            if _cached_vectors is None or soc_key != _cached_socs:
                _cached_vectors = build_skill_vectors(project_socs)
                _cached_socs = soc_key
    return _cached_vectors


if __name__ == "__main__":
    soc_list, elements, matrix, soc_to_idx, norms = build_skill_vectors()
    print(f"\nElements: {elements[:10]}...")
    print(f"Matrix shape: {matrix.shape}")
    if "11-1011" in soc_to_idx:
        print(f"Sample vector for 11-1011: {matrix[soc_to_idx['11-1011']][:5]}")
