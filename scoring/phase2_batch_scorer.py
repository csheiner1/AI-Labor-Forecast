"""Phase 2: API-based batch scoring of workflow_simplicity, x_scale, x_sub.

Reads calibration anchors from Phase 1, scores all 462 occupations in
batches of 25 using Claude Opus 4.6 at temperature=0.2.
"""
import json
import os
import time
import anthropic

CLIENT = anthropic.Anthropic()
MODEL = "claude-opus-4-6"
TEMPERATURE = 0.2
BATCH_SIZE = 25

# --- Load data ---
with open('scoring/job_profiles.json') as f:
    ALL_PROFILES = json.load(f)

with open('scoring/calibration_results.json') as f:
    CALIBRATION = json.load(f)

# --- Build calibration anchor text ---
def format_anchors(cal):
    """Format calibration results as reference anchors for batch prompts."""
    lines = []
    for c in cal:
        lines.append(
            f"- {c['custom_title']} ({c['sector']}): "
            f"workflow_simplicity={c['workflow_simplicity']}, "
            f"x_scale={c['x_scale']}, x_sub={c['x_sub']}"
        )
        if c.get('reasoning_summary'):
            lines.append(f"  Rationale: {c['reasoning_summary']}")
    return "\n".join(lines)

ANCHOR_TEXT = format_anchors(CALIBRATION)

# --- Prompt template ---
SYSTEM_PROMPT = """You are scoring occupations for an AI labor displacement forecast model.

You will score each occupation on THREE variables, each on a 5-point scale.
Score each variable INDEPENDENTLY using its own reasoning block. Do not let
one variable's assessment influence another.

## Variable 1: workflow_simplicity
How complex is the orchestration of this job's task flow?
- 1.00 = Independent/trivial: tasks are independent or fixed linear pipeline
- 0.75 = Mostly independent: most tasks execute independently, few require coordination
- 0.50 = Moderate interdependence: meaningful dependencies, some branching, iteration loops
- 0.25 = Tightly coupled: highly interdependent, frequent branching, backtracking, real-time adaptation
- 0.00 = Fully dynamic: sequence determined in real-time by evolving conditions

## Variable 2: x_scale (Throughput)
Does AI increase capacity/speed at scale for this occupation?
- 0.00 = No throughput gain: physical or situational constraints cap speed
- 0.25 = Modest scaling: AI helps but significant bottlenecks remain
- 0.50 = Moderate scaling: AI doubles/triples throughput in some areas, constrained in others
- 0.75 = Strong scaling: AI handles large volumes with minimal human oversight
- 1.00 = Near-unlimited: AI processes at machine speed, no human bottleneck

## Variable 3: x_sub (Substitutability)
Is the human the product, or is the output the product?
- 0.00 = Human IS the product: value is intrinsically human (therapist, clergy, trial lawyer)
- 0.25 = Strong human preference: human presence strongly valued, some substitution emerging
- 0.50 = Mixed/contested: human matters for some market segments, substitution happening in others
- 0.75 = Weak human preference: most would accept AI if cheaper/faster
- 1.00 = Fully substitutable: output is the product, not the human

IMPORTANT: x_sub captures whether the human IS the product (intrinsic). This is different
from T3 (Customer Acceptance), which captures whether customers are WILLING to accept AI
(a preference that can erode). x_sub = 0.00 means even if customers wanted AI, the service
fundamentally requires a human. x_sub = 1.00 means the output matters, not who produces it.

## Calibration Anchors (reference points from Phase 1)
{anchors}

## Output Format
Return a JSON array. For each occupation, provide:
```json
{{
  "custom_title": "...",
  "soc_code": "...",
  "workflow_simplicity_reasoning": "2-3 sentences about task orchestration ONLY",
  "workflow_simplicity": <score>,
  "x_scale_reasoning": "2-3 sentences about throughput/scaling ONLY",
  "x_scale": <score>,
  "x_sub_reasoning": "2-3 sentences about human-is-the-product ONLY",
  "x_sub": <score>,
  "coherence_note": "any tensions between the three scores"
}}
```

Score ONLY from {{0.00, 0.25, 0.50, 0.75, 1.00}}. No other values."""

def format_profile_for_prompt(p):
    """Format a single job profile for the scoring prompt."""
    top_tasks = "\n".join(
        f"    - [{t['gwa']}] {t['desc']} (score_mod={t['score_mod']}, score_sig={t['score_sig']}, time_share={t['time_share']}%)"
        for t in p['top3_tasks']
    )
    bottom_tasks = "\n".join(
        f"    - [{t['gwa']}] {t['desc']} (score_mod={t['score_mod']}, score_sig={t['score_sig']}, time_share={t['time_share']}%)"
        for t in p['bottom3_tasks']
    )
    gwa_dist = ", ".join(f"{k}: {v}" for k, v in list(p['gwa_distribution'].items())[:6])

    return f"""### {p['custom_title']} (SOC: {p['soc_code']})
  Sector: {p['sector']}
  Employment: {p['employment_K']}K | Median Wage: {'$'+format(p['median_wage'],',') if p['median_wage'] is not None else '≥$239,200'}
  Industry concentration: {p.get('primary_industry', 'N/A')}
  Task coverage: mod={p['task_coverage_mod']}, sig={p['task_coverage_sig']}
  Task count: {p['num_tasks']} | Heterogeneity (sig): {p['heterogeneity_sig']}
  GWA shares: interpersonal={p['interpersonal_task_share']}, digital={p['digital_task_share']}, judgment={p['judgment_task_share']}
  GWA distribution: {gwa_dist}
  Highest-autonomy tasks:
{top_tasks}
  Lowest-autonomy tasks:
{bottom_tasks}"""


def score_batch(batch_profiles, batch_num):
    """Score a batch of profiles via API call."""
    profiles_text = "\n\n".join(format_profile_for_prompt(p) for p in batch_profiles)

    user_prompt = f"""Score the following {len(batch_profiles)} occupations.
Return a JSON array with exactly {len(batch_profiles)} entries.

{profiles_text}"""

    system = SYSTEM_PROMPT.format(anchors=ANCHOR_TEXT)

    response = CLIENT.messages.create(
        model=MODEL,
        temperature=TEMPERATURE,
        max_tokens=8192,
        system=system,
        messages=[{"role": "user", "content": user_prompt}],
    )

    # Extract text content
    text = response.content[0].text

    # Parse JSON from response (handle markdown code blocks)
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]

    scores = json.loads(text)

    # Validate
    valid_values = {0.0, 0.25, 0.5, 0.75, 1.0}
    for s in scores:
        for var in ['workflow_simplicity', 'x_scale', 'x_sub']:
            assert var in s, f"Missing {var} in {s.get('custom_title', '?')}"
            assert s[var] in valid_values, f"Invalid {var}={s[var]} for {s.get('custom_title', '?')}"

    # Log token usage
    usage = {
        'input_tokens': response.usage.input_tokens,
        'output_tokens': response.usage.output_tokens,
        'batch_num': batch_num,
        'num_jobs': len(batch_profiles),
    }

    return scores, usage


def main():
    # Filter out already-scored jobs (for resumability)
    scored_file = 'scoring/batch_results/all_scores.json'
    already_scored = set()
    if os.path.exists(scored_file):
        with open(scored_file) as f:
            existing = json.load(f)
        already_scored = {s['custom_title'] for s in existing}
        print(f"Resuming: {len(already_scored)} already scored")

    remaining = [p for p in ALL_PROFILES if p['custom_title'] not in already_scored]
    print(f"Scoring {len(remaining)} remaining occupations in batches of {BATCH_SIZE}")

    all_scores = list(json.load(open(scored_file))) if os.path.exists(scored_file) else []
    all_usage = []

    # Batch and score
    for i in range(0, len(remaining), BATCH_SIZE):
        batch = remaining[i:i + BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1
        total_batches = (len(remaining) + BATCH_SIZE - 1) // BATCH_SIZE

        print(f"\nBatch {batch_num}/{total_batches}: {[p['custom_title'] for p in batch[:3]]}... ({len(batch)} jobs)")

        try:
            scores, usage = score_batch(batch, batch_num)
            all_scores.extend(scores)
            all_usage.append(usage)
            print(f"  OK: {usage['input_tokens']} in / {usage['output_tokens']} out tokens")

            # Save checkpoint after each batch
            with open(scored_file, 'w') as f:
                json.dump(all_scores, f, indent=2)

            # Save per-batch file too
            with open(f'scoring/batch_results/batch_{batch_num:03d}.json', 'w') as f:
                json.dump({'scores': scores, 'usage': usage}, f, indent=2)

            # Rate limit courtesy
            time.sleep(1)

        except Exception as e:
            print(f"  ERROR on batch {batch_num}: {e}")
            # Save progress so far
            with open(scored_file, 'w') as f:
                json.dump(all_scores, f, indent=2)
            print(f"  Saved {len(all_scores)} scores so far. Re-run to resume.")
            raise

    # Final summary
    total_in = sum(u['input_tokens'] for u in all_usage)
    total_out = sum(u['output_tokens'] for u in all_usage)
    print(f"\n=== COMPLETE ===")
    print(f"Scored: {len(all_scores)} occupations")
    print(f"Tokens: {total_in:,} input + {total_out:,} output")
    print(f"Est. cost: ${total_in * 15 / 1_000_000 + total_out * 75 / 1_000_000:.2f}")

    with open('scoring/batch_results/usage_log.json', 'w') as f:
        json.dump(all_usage, f, indent=2)


if __name__ == '__main__':
    main()
