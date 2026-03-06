"""Phase 3: Hybrid Auditor — programmatic checks + API re-scoring of flagged occupations.

Two components:
1. Programmatic (Python): distribution checks, correlation caps, SOC-group coherence, consistency rules
2. Semantic (API): LLM re-scores flagged occupations individually at temp=0.1
"""
import json
import os
import statistics
from collections import Counter, defaultdict
import anthropic

CLIENT = anthropic.Anthropic()
MODEL = "claude-opus-4-6"

VALID_SCORES = {0.0, 0.25, 0.5, 0.75, 1.0}
VARIABLES = ['workflow_simplicity', 'x_scale', 'x_sub']


def load_scores():
    with open('scoring/batch_results/all_scores.json') as f:
        return json.load(f)


def load_profiles():
    with open('scoring/job_profiles.json') as f:
        profiles = json.load(f)
    return {p['custom_title']: p for p in profiles}


# ===== PROGRAMMATIC CHECKS =====

def check_distribution(scores):
    """No variable should have >35% concentrated at a single anchor."""
    flags = []
    for var in VARIABLES:
        values = [s[var] for s in scores]
        counts = Counter(values)
        total = len(values)
        for val, count in counts.items():
            pct = count / total
            if pct > 0.35:
                flags.append({
                    'type': 'distribution_skew',
                    'variable': var,
                    'value': val,
                    'pct': round(pct, 3),
                    'count': count,
                    'message': f"{var}={val} has {pct:.1%} of all scores (>{35}% threshold)"
                })
    return flags


def check_correlation(scores):
    """x_scale vs x_sub correlation should not exceed 0.80."""
    flags = []
    x_scale = [s['x_scale'] for s in scores]
    x_sub = [s['x_sub'] for s in scores]
    n = len(x_scale)
    if n < 3:
        return flags

    mean_a = sum(x_scale) / n
    mean_b = sum(x_sub) / n
    cov = sum((a - mean_a) * (b - mean_b) for a, b in zip(x_scale, x_sub)) / n
    std_a = (sum((a - mean_a) ** 2 for a in x_scale) / n) ** 0.5
    std_b = (sum((b - mean_b) ** 2 for b in x_sub) / n) ** 0.5
    if std_a > 0 and std_b > 0:
        corr = cov / (std_a * std_b)
        if abs(corr) > 0.80:
            flags.append({
                'type': 'high_correlation',
                'variables': 'x_scale vs x_sub',
                'correlation': round(corr, 3),
                'message': f"x_scale/x_sub correlation = {corr:.3f} (>0.80 threshold)"
            })
    return flags


def check_soc_group_coherence(scores, profiles):
    """Within-group standard deviation check for 2-digit SOC groups."""
    flags = []
    soc_groups = defaultdict(list)
    for s in scores:
        soc_2 = s['soc_code'][:2] if 'soc_code' in s else None
        if soc_2:
            soc_groups[soc_2].append(s)

    for soc_2, group in soc_groups.items():
        if len(group) < 3:
            continue
        for var in VARIABLES:
            vals = [s[var] for s in group]
            std = statistics.stdev(vals) if len(vals) > 1 else 0
            if std > 0.40:
                titles = [s['custom_title'] for s in group]
                flags.append({
                    'type': 'soc_group_incoherence',
                    'soc_group': soc_2,
                    'variable': var,
                    'std': round(std, 3),
                    'titles': titles,
                    'values': vals,
                    'message': f"SOC {soc_2} has high within-group std={std:.3f} on {var}"
                })
    return flags


def check_consistency_rules(scores, profiles):
    """Flag rare/suspicious combinations."""
    flags = []
    for s in scores:
        title = s['custom_title']
        p = profiles.get(title, {})

        # Low x_sub + high workflow_simplicity is rare
        if s['x_sub'] <= 0.25 and s['workflow_simplicity'] >= 0.75:
            flags.append({
                'type': 'rare_combination',
                'title': title,
                'rule': 'low_xsub_high_workflow',
                'x_sub': s['x_sub'],
                'workflow_simplicity': s['workflow_simplicity'],
                'message': f"{title}: x_sub={s['x_sub']} + workflow_simplicity={s['workflow_simplicity']} is rare (human IS product + simple workflow)"
            })

        # Physical jobs (dental hygienist, etc.) should have low x_scale
        if p.get('interpersonal_task_share', 0) > 0.5 and s['x_scale'] >= 0.75:
            flags.append({
                'type': 'rare_combination',
                'title': title,
                'rule': 'high_interpersonal_high_scale',
                'interpersonal_share': p['interpersonal_task_share'],
                'x_scale': s['x_scale'],
                'message': f"{title}: interpersonal_share={p['interpersonal_task_share']} + x_scale={s['x_scale']} is suspicious"
            })

        # Very high digital share + low x_scale
        if p.get('digital_task_share', 0) > 0.5 and s['x_scale'] <= 0.25:
            flags.append({
                'type': 'rare_combination',
                'title': title,
                'rule': 'high_digital_low_scale',
                'digital_share': p['digital_task_share'],
                'x_scale': s['x_scale'],
                'message': f"{title}: digital_share={p['digital_task_share']} + x_scale={s['x_scale']} — digital tasks usually scale"
            })

    return flags


def run_programmatic_checks(scores, profiles):
    """Run all programmatic checks, return aggregated flags."""
    all_flags = []
    all_flags.extend(check_distribution(scores))
    all_flags.extend(check_correlation(scores))
    all_flags.extend(check_soc_group_coherence(scores, profiles))
    all_flags.extend(check_consistency_rules(scores, profiles))

    # Deduplicate flagged titles
    flagged_titles = set()
    for f in all_flags:
        if 'title' in f:
            flagged_titles.add(f['title'])
        elif 'titles' in f:
            flagged_titles.update(f['titles'])

    return all_flags, flagged_titles


# ===== SEMANTIC AUDITOR (API) =====

def rescore_flagged(flagged_titles, scores, profiles, calibration):
    """Re-score flagged occupations individually at temp=0.1."""
    flagged_scores = [s for s in scores if s['custom_title'] in flagged_titles]
    print(f"\nSemantic audit: re-scoring {len(flagged_scores)} flagged occupations...")

    # Build calibration anchor text
    anchor_lines = []
    for c in calibration:
        anchor_lines.append(
            f"- {c['custom_title']}: workflow_simplicity={c['workflow_simplicity']}, "
            f"x_scale={c['x_scale']}, x_sub={c['x_sub']}"
        )
    anchor_text = "\n".join(anchor_lines)

    revised = []
    for s in flagged_scores:
        p = profiles.get(s['custom_title'], {})
        reasons = [f['message'] for f in all_flags if f.get('title') == s['custom_title'] or s['custom_title'] in f.get('titles', [])]

        prompt = f"""You are auditing a score for the AI labor displacement model.

This occupation was flagged for review. Original scores and flag reasons below.

## Occupation: {s['custom_title']} (SOC: {s.get('soc_code', 'N/A')})
Sector: {p.get('sector', 'N/A')}
Employment: {p.get('employment_K', 'N/A')}K
Task coverage: mod={p.get('task_coverage_mod')}, sig={p.get('task_coverage_sig')}
Interpersonal task share: {p.get('interpersonal_task_share', 'N/A')}
Digital task share: {p.get('digital_task_share', 'N/A')}
Judgment task share: {p.get('judgment_task_share', 'N/A')}

## Original Scores
workflow_simplicity: {s['workflow_simplicity']} — {s.get('workflow_simplicity_reasoning', '')}
x_scale: {s['x_scale']} — {s.get('x_scale_reasoning', '')}
x_sub: {s['x_sub']} — {s.get('x_sub_reasoning', '')}

## Flag Reasons
{chr(10).join('- ' + r for r in reasons)}

## Calibration Anchors
{anchor_text}

Review the original scores. For each variable, either CONFIRM or REVISE.
Return JSON: {{"custom_title": "...", "workflow_simplicity": <score>, "x_scale": <score>, "x_sub": <score>, "audit_action": "confirmed" or "revised", "audit_notes": "..."}}
Scores must be from {{0.00, 0.25, 0.50, 0.75, 1.00}}."""

        response = CLIENT.messages.create(
            model=MODEL,
            temperature=0.1,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )

        text = response.content[0].text
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        result = json.loads(text)
        revised.append(result)
        action = result.get('audit_action', 'unknown')
        print(f"  {s['custom_title']}: {action}")

    return revised


def main():
    scores = load_scores()
    profiles = load_profiles()

    with open('scoring/calibration_results.json') as f:
        calibration = json.load(f)

    print(f"Auditing {len(scores)} scores...")

    global all_flags
    all_flags, flagged_titles = run_programmatic_checks(scores, profiles)

    print(f"\n=== Programmatic Check Results ===")
    print(f"Total flags: {len(all_flags)}")
    print(f"Unique flagged occupations: {len(flagged_titles)}")

    by_type = Counter(f['type'] for f in all_flags)
    for t, c in by_type.items():
        print(f"  {t}: {c}")

    # Save flags
    with open('scoring/audit_flags.json', 'w') as f:
        json.dump(all_flags, f, indent=2)

    if flagged_titles:
        revised = rescore_flagged(flagged_titles, scores, profiles, calibration)

        # Merge revised scores back
        revised_map = {r['custom_title']: r for r in revised}
        final_scores = []
        for s in scores:
            if s['custom_title'] in revised_map:
                rev = revised_map[s['custom_title']]
                s['workflow_simplicity'] = rev['workflow_simplicity']
                s['x_scale'] = rev['x_scale']
                s['x_sub'] = rev['x_sub']
                s['audit_action'] = rev.get('audit_action', 'revised')
                s['audit_notes'] = rev.get('audit_notes', '')
            else:
                s['audit_action'] = 'passed'
            final_scores.append(s)

        with open('scoring/final_scores.json', 'w') as f:
            json.dump(final_scores, f, indent=2)
        print(f"\nSaved {len(final_scores)} final scores (with {len(revised)} audited)")
    else:
        print("\nNo flags — all scores passed programmatic checks.")
        with open('scoring/final_scores.json', 'w') as f:
            json.dump(scores, f, indent=2)


if __name__ == '__main__':
    main()
