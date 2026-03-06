"""Phase 4: Reliability Verification — resample 10%, re-score, compute kappa.

Thresholds: kappa >= 0.75, within-one-step >= 90%, exact agreement >= 65%.
"""
import json
import random
import anthropic

CLIENT = anthropic.Anthropic()
MODEL = "claude-opus-4-6"
VARIABLES = ['workflow_simplicity', 'x_scale', 'x_sub']
VALID_SCORES = [0.0, 0.25, 0.5, 0.75, 1.0]
SAMPLE_RATE = 0.10


def weighted_quadratic_kappa(scores1, scores2, categories):
    """Compute weighted quadratic kappa between two sets of scores."""
    n = len(categories)
    N = len(scores1)

    # Build confusion matrix
    matrix = [[0] * n for _ in range(n)]
    for s1, s2 in zip(scores1, scores2):
        i = categories.index(s1)
        j = categories.index(s2)
        matrix[i][j] += 1

    # Weight matrix (quadratic)
    weights = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            weights[i][j] = (i - j) ** 2 / (n - 1) ** 2

    # Expected matrix under independence
    row_sums = [sum(matrix[i]) for i in range(n)]
    col_sums = [sum(matrix[i][j] for i in range(n)) for j in range(n)]

    observed = sum(weights[i][j] * matrix[i][j] for i in range(n) for j in range(n)) / N
    expected = sum(weights[i][j] * row_sums[i] * col_sums[j] for i in range(n) for j in range(n)) / (N * N)

    if expected == 0:
        return 1.0
    return 1.0 - observed / expected


def within_one_step(scores1, scores2):
    """Fraction of pairs within one step on the 5-point scale."""
    agree = sum(1 for a, b in zip(scores1, scores2) if abs(a - b) <= 0.25)
    return agree / len(scores1) if scores1 else 0


def exact_agreement(scores1, scores2):
    """Fraction of exact matches."""
    agree = sum(1 for a, b in zip(scores1, scores2) if a == b)
    return agree / len(scores1) if scores1 else 0


def main():
    with open('scoring/final_scores.json') as f:
        scores = json.load(f)

    with open('scoring/job_profiles.json') as f:
        profiles = json.load(f)
    profiles_map = {p['custom_title']: p for p in profiles}

    with open('scoring/calibration_results.json') as f:
        calibration = json.load(f)

    # Stratified sample: 10% from each sector
    from collections import defaultdict
    by_sector = defaultdict(list)
    for s in scores:
        p = profiles_map.get(s['custom_title'], {})
        sector = p.get('sector', 'Unknown')
        by_sector[sector].append(s)

    sample = []
    random.seed(42)
    for sector, sector_scores in by_sector.items():
        n = max(1, round(len(sector_scores) * SAMPLE_RATE))
        sample.extend(random.sample(sector_scores, min(n, len(sector_scores))))

    print(f"Reliability sample: {len(sample)} occupations ({len(sample)/len(scores):.1%})")

    # Build anchor text
    anchor_lines = [
        f"- {c['custom_title']}: workflow_simplicity={c['workflow_simplicity']}, "
        f"x_scale={c['x_scale']}, x_sub={c['x_sub']}"
        for c in calibration
    ]
    anchor_text = "\n".join(anchor_lines)

    # Re-score each sampled occupation independently
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from phase2_batch_scorer import format_profile_for_prompt, SYSTEM_PROMPT
    rescore_results = []

    BATCH_SIZE = 10
    for i in range(0, len(sample), BATCH_SIZE):
        batch = sample[i:i + BATCH_SIZE]
        batch_profiles = [profiles_map[s['custom_title']] for s in batch if s['custom_title'] in profiles_map]

        profiles_text = "\n\n".join(format_profile_for_prompt(p) for p in batch_profiles)
        user_prompt = f"Score the following {len(batch_profiles)} occupations.\nReturn a JSON array.\n\n{profiles_text}"
        system = SYSTEM_PROMPT.format(anchors=anchor_text)

        response = CLIENT.messages.create(
            model=MODEL,
            temperature=0.2,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": user_prompt}],
        )

        text = response.content[0].text
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        batch_results = json.loads(text)
        rescore_results.extend(batch_results)
        print(f"  Re-scored batch {i // BATCH_SIZE + 1}: {len(batch_results)} jobs")

    # Match original and re-scored
    rescore_map = {r['custom_title']: r for r in rescore_results}

    results = {}
    for var in VARIABLES:
        original = []
        rescored = []
        for s in sample:
            title = s['custom_title']
            if title in rescore_map:
                original.append(s[var])
                rescored.append(rescore_map[title][var])

        kappa = weighted_quadratic_kappa(original, rescored, VALID_SCORES)
        w1s = within_one_step(original, rescored)
        exact = exact_agreement(original, rescored)

        results[var] = {
            'kappa': round(kappa, 3),
            'within_one_step': round(w1s, 3),
            'exact_agreement': round(exact, 3),
            'pass_kappa': kappa >= 0.75,
            'pass_within_one': w1s >= 0.90,
            'pass_exact': exact >= 0.65,
            'n': len(original),
        }

    # Report
    print(f"\n{'='*60}")
    print(f"{'Variable':<25} {'Kappa':>8} {'Within-1':>10} {'Exact':>8} {'Pass':>6}")
    print(f"{'='*60}")
    all_pass = True
    for var, r in results.items():
        passed = r['pass_kappa'] and r['pass_within_one'] and r['pass_exact']
        all_pass = all_pass and passed
        mark = 'YES' if passed else 'NO'
        print(f"{var:<25} {r['kappa']:>8.3f} {r['within_one_step']:>10.3f} {r['exact_agreement']:>8.3f} {mark:>6}")
    print(f"{'='*60}")
    print(f"Overall: {'PASS' if all_pass else 'FAIL'}")

    with open('scoring/reliability_results.json', 'w') as f:
        json.dump(results, f, indent=2)

    if not all_pass:
        print("\nWARNING: Reliability thresholds not met. Review discrepant occupations.")
        # Show discrepancies
        for s in sample:
            title = s['custom_title']
            if title in rescore_map:
                r = rescore_map[title]
                diffs = {var: abs(s[var] - r[var]) for var in VARIABLES}
                if any(d > 0.25 for d in diffs.values()):
                    print(f"  {title}: orig={[s[v] for v in VARIABLES]} rescore={[r[v] for v in VARIABLES]}")

    return all_pass


if __name__ == '__main__':
    main()
