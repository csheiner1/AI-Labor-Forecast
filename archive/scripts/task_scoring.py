"""
TASK AUTOMATABILITY SCORING SYSTEM
===================================
Multi-agent pipeline for scoring task-level AI autonomy fractions
under two capability scenarios (Moderate / Significant gains, Oct 2027).

Architecture (all phases use Claude Opus 4.6):
  Agent 1 — CALIBRATOR: Scores ~15 anchor tasks with full reasoning. Output becomes
                        the shared reference frame for all subsequent scoring.
                        Uses adaptive thinking for deeper constraint analysis.
  Agent 2 — BATCH SCORER: Processes tasks in batches of 25-30, returning structured
                          JSON scores. Calibration anchors embedded in every batch.
  Agent 3 — DRIFT AUDITOR: Samples scored tasks across batches, flags inconsistencies
                           relative to anchors. Re-scores flagged tasks.
                           Uses adaptive thinking for judgment on disagreements.

Run: `python task_scoring.py` (defaults to jobs-data.xlsx in ai-labor-analysis project)

Methodology is loaded from scoring-methodology.md — edit that file to adjust
scenarios, rubric, anchors, or universal limits without touching this code.
"""

import anthropic
import json
import math
import pandas as pd
import sys
import time
from pathlib import Path

client = anthropic.Anthropic()
MODEL = "claude-opus-4-6"

# ──────────────────────────────────────────────────
# LOAD METHODOLOGY FROM REFERENCE DOC
# ──────────────────────────────────────────────────

METHODOLOGY_PATH = Path(__file__).parent / "scoring-methodology.md"


def load_methodology() -> str:
    """Load the scoring methodology doc. Fail loudly if missing."""
    if not METHODOLOGY_PATH.exists():
        print(f"ERROR: scoring-methodology.md not found at {METHODOLOGY_PATH}")
        print("This file defines scenarios, rubric, anchors, and universal limits.")
        sys.exit(1)
    with open(METHODOLOGY_PATH) as f:
        return f.read()


METHODOLOGY = load_methodology()

# ──────────────────────────────────────────────────
# PIPELINE HELPERS
# ──────────────────────────────────────────────────

CHECKPOINT_DIR = Path("scoring_checkpoints")


def call_claude(
    content: list[dict],
    max_tokens: int = 4096,
    use_thinking: bool = False,
) -> str:
    """
    Streaming Claude API call with retry logic.

    - use_thinking=True:  adaptive thinking, no temperature (Calibrator + Auditor)
    - use_thinking=False: temperature=0.2 for consistency (Batch Scorer)

    Content blocks with cache_control are cached server-side; pass METHODOLOGY
    as the first block with cache_control to avoid re-encoding it on every call.
    """
    kwargs: dict = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": content}],
    }
    if use_thinking:
        kwargs["thinking"] = {"type": "adaptive"}
    else:
        kwargs["temperature"] = 0.2

    for attempt in range(3):
        try:
            with client.messages.stream(**kwargs) as stream:
                final = stream.get_final_message()
                # Skip thinking blocks; return the text block
                return next(b.text for b in final.content if b.type == "text")
        except Exception as e:
            if attempt == 2:
                raise
            print(f"  Retry {attempt + 1}: {e}")
            time.sleep(2 ** attempt)


def parse_json(text: str) -> dict:
    """Extract and parse the first JSON object from text.

    Uses json_repair to handle malformed JSON (e.g. unescaped quotes in
    free-text fields like 'reason'), which is common when adaptive thinking
    generates verbose explanations.
    """
    from json_repair import repair_json
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON object found in response:\n{text[:500]}")
    return json.loads(repair_json(text[start : end + 1]))


# ──────────────────────────────────────────────────
# AGENT 1: CALIBRATOR
# ──────────────────────────────────────────────────

def build_calibrator_content(sample_tasks: list[dict]) -> list[dict]:
    """
    Returns content blocks for the calibrator call.

    Block 1 (cached): METHODOLOGY — stable across all calls.
    Block 2 (uncached): instructions + task list — specific to this calibration run.

    Uses adaptive thinking: the calibrator is doing nuanced multi-dimensional
    reasoning to establish the reference frame for all downstream scoring.
    """
    task_block = "\n".join(
        f"TASK {i+1}: [{t.get('Job_Title', 'N/A')} | {t.get('Function_Name', 'N/A')}] "
        f"\"{t['Task_Description']}\" "
        f"(Task_Type: {t.get('Task_Type', 'N/A')}, "
        f"Time_Share: {t.get('Time_Share_Pct', 'N/A')}%)"
        for i, t in enumerate(sample_tasks)
    )

    instructions = f"""You are an expert labor economist and AI capabilities researcher.
Your job is to score task automatability under two AI capability scenarios,
using the methodology above as your single source of truth.

INSTRUCTIONS:
Below are {len(sample_tasks)} tasks sampled from across industries. For EACH task:
1. State what the task requires (2-3 sentences max).
2. Identify the binding constraint on automation under each scenario.
3. Assign autonomy scores for Moderate and Significant.
4. Flag if this task could serve as a useful additional calibration anchor.

TASKS TO SCORE:
{task_block}

Respond in this exact JSON format (no markdown fences, no preamble):
{{
  "scored_tasks": [
    {{
      "task_index": 1,
      "task_description": "...",
      "binding_constraint_moderate": "...",
      "binding_constraint_significant": "...",
      "score_moderate": 0.50,
      "score_significant": 0.75,
      "is_good_anchor": true,
      "anchor_reasoning": "..."
    }}
  ]
}}"""

    return [
        {
            "type": "text",
            "text": METHODOLOGY,
            "cache_control": {"type": "ephemeral"},
        },
        {
            "type": "text",
            "text": instructions,
        },
    ]


# ──────────────────────────────────────────────────
# AGENT 2: BATCH SCORER
# ──────────────────────────────────────────────────

def build_batch_scorer_content(
    tasks: list[dict],
    batch_index: int,
    total_batches: int,
    extra_anchors: str = "",
) -> list[dict]:
    """
    Returns content blocks for a batch scoring call.

    Block 1 (cached): METHODOLOGY — identical across all batch calls.
    Block 2 (cached, if present): extra anchors from calibration phase —
        generated once and constant for all batches.
    Block 3 (uncached): batch header + task list + rules — changes every call.

    No adaptive thinking: batch scorer needs cross-batch consistency.
    temperature=0.2 is set in call_claude when use_thinking=False.
    """
    task_block = "\n".join(
        f"[{i+1}] ({t.get('Job_Title', 'N/A')} | {t.get('Function_Name', 'N/A')}) "
        f"\"{t['Task_Description']}\" "
        f"(Task_Type: {t.get('Task_Type', 'N/A')}, "
        f"Time_Share: {t.get('Time_Share_Pct', 'N/A')}%)"
        for i, t in enumerate(tasks)
    )

    batch_prompt = f"""You are a task automatability scorer. Batch {batch_index}/{total_batches}.

You are evaluating whether a FRONTIER AI MODEL available in October 2027 — not today's
models — can autonomously perform each task below. Score against the scenarios and
calibration anchors defined in the methodology above.

TASKS TO SCORE:
{task_block}

Score each task. Respond ONLY with JSON (no markdown, no preamble):
{{
  "scores": [
    {{
      "index": 1,
      "mod": 0.50,
      "sig": 0.75
    }}
  ]
}}

RULES:
- Scores must be from {{0.00, 0.25, 0.50, 0.75, 1.00}}.
- sig >= mod always (more capability cannot reduce automation potential).
- If a task's binding constraint is a UNIVERSAL LIMITATION, mod and sig should be identical or very close.
- If uncertain between two levels, identify the binding constraint and check how calibration anchors with similar constraints were scored. Match that pattern.
- Check your scores against the calibration anchors for consistency before responding."""

    blocks: list[dict] = [
        {
            "type": "text",
            "text": METHODOLOGY,
            "cache_control": {"type": "ephemeral"},
        },
    ]

    if extra_anchors:
        blocks.append(
            {
                "type": "text",
                "text": extra_anchors,
                "cache_control": {"type": "ephemeral"},
            }
        )

    blocks.append({"type": "text", "text": batch_prompt})
    return blocks


# ──────────────────────────────────────────────────
# AGENT 3: DRIFT AUDITOR
# ──────────────────────────────────────────────────

def build_auditor_content(scored_sample: list[dict]) -> list[dict]:
    """
    Returns content blocks for an audit call.

    Block 1 (cached): METHODOLOGY — same as all other calls.
    Block 2 (uncached): audit instructions + sampled tasks.

    Uses adaptive thinking: the auditor is making judgment calls about
    whether original scores were wrong and producing reasoned explanations.
    """
    task_block = "\n".join(
        f"[Batch {t['batch']}, #{t['index']}] ({t.get('Job_Title','N/A')} | "
        f"{t.get('Function_Name','N/A')}) "
        f"\"{t['Task_Description']}\" "
        f"(Task_Type: {t.get('Task_Type', 'N/A')}) — "
        f"Original scores: mod={t['score_moderate']}, sig={t['score_significant']}"
        for t in scored_sample
    )

    instructions = f"""You are an independent auditor checking scoring consistency.
Use the methodology above as your single source of truth.

Below are tasks scored by a prior agent across multiple batches. For each:
1. Independently determine the correct score (ignore the original).
2. Compare to the original. Flag if your score differs by >= 0.25.

TASKS TO AUDIT:
{task_block}

Respond ONLY with JSON:
{{
  "audits": [
    {{
      "batch": 1,
      "index": 3,
      "original_mod": 0.50,
      "original_sig": 0.75,
      "audited_mod": 0.50,
      "audited_sig": 0.50,
      "flagged": true,
      "reason": "Original overestimates significant scenario because..."
    }}
  ]
}}"""

    return [
        {
            "type": "text",
            "text": METHODOLOGY,
            "cache_control": {"type": "ephemeral"},
        },
        {
            "type": "text",
            "text": instructions,
        },
    ]


# ──────────────────────────────────────────────────
# CHECKPOINT HELPERS
# ──────────────────────────────────────────────────

def save_checkpoint(all_scores: list, batch_index: int):
    """Save progress after each batch so we can resume on failure."""
    CHECKPOINT_DIR.mkdir(exist_ok=True)
    checkpoint = {
        "scores": all_scores,
        "last_batch": batch_index,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    with open(CHECKPOINT_DIR / "progress.json", "w") as f:
        json.dump(checkpoint, f)


def load_checkpoint():
    """Load previous progress if it exists."""
    cp_path = CHECKPOINT_DIR / "progress.json"
    if cp_path.exists():
        with open(cp_path) as f:
            checkpoint = json.load(f)
        print(
            f"  Found checkpoint from {checkpoint['timestamp']}: "
            f"{len(checkpoint['scores'])} tasks scored, last batch {checkpoint['last_batch']}"
        )
        return checkpoint["scores"], checkpoint["last_batch"]
    return None


def clear_checkpoint():
    """Remove checkpoint after successful completion."""
    cp_path = CHECKPOINT_DIR / "progress.json"
    if cp_path.exists():
        cp_path.unlink()


# ──────────────────────────────────────────────────
# DATA LOADING
# ──────────────────────────────────────────────────

def load_tasks(filepath: str) -> pd.DataFrame:
    """Load the '3 Tasks' tab from the Excel file."""
    df = pd.read_excel(filepath, sheet_name="3 Tasks")
    print(f"Loaded {len(df)} rows from '3 Tasks' tab")
    print(f"Columns: {list(df.columns)}")
    return df


def sample_diverse_tasks(df: pd.DataFrame, n: int = 15) -> list[dict]:
    """
    Stratified sample across industries/job types for calibration.
    Falls back to random if no industry column exists.
    """
    if "industry" in df.columns:
        sampled = df.groupby("industry", group_keys=False).apply(
            lambda x: x.sample(min(2, len(x)))
        ).head(n)
    else:
        sampled = df.sample(min(n, len(df)))
    return sampled.to_dict("records")


# ──────────────────────────────────────────────────
# PIPELINE ORCHESTRATOR
# ──────────────────────────────────────────────────

def run_pipeline(input_path: str, output_path: str, batch_size: int = 25):
    """
    Full pipeline: Calibrate → Batch Score (with checkpointing) → Audit → Output.
    """
    # 1. Load
    df = load_tasks(input_path)

    required = ["Task_Description", "Job_Title", "Function_Name"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        print(f"ERROR: Missing columns: {missing}")
        print(f"Available columns: {list(df.columns)}")
        sys.exit(1)

    tasks = df.to_dict("records")
    print(f"\n{'='*60}")
    print(f"PIPELINE START — {len(tasks)} tasks to score")
    print(f"{'='*60}\n")

    # 2. Check for existing checkpoint
    all_scores = []
    start_batch = 0
    checkpoint = load_checkpoint()
    if checkpoint:
        all_scores, last_batch = checkpoint
        start_batch = last_batch + 1
        print(f"  Resuming from batch {start_batch + 1}\n")

    # 3. Calibrate (skip if resuming past batch 0)
    extra_anchor_text = ""
    if start_batch == 0:
        print("PHASE 1: Calibration  [adaptive thinking enabled]")
        sample = sample_diverse_tasks(df, n=15)
        cal_content = build_calibrator_content(sample)
        print(f"  Scoring {len(sample)} anchor tasks...")
        cal_raw = call_claude(cal_content, max_tokens=32000, use_thinking=True)
        cal_result = parse_json(cal_raw)

        new_anchors = [t for t in cal_result["scored_tasks"] if t.get("is_good_anchor")]
        if new_anchors:
            extra_anchor_text = "\nADDITIONAL CALIBRATION ANCHORS (from calibration phase):\n"
            for a in new_anchors[:5]:
                extra_anchor_text += (
                    f"- \"{a['task_description']}\" → "
                    f"Moderate: {a['score_moderate']}, Significant: {a['score_significant']}. "
                    f"Reason: {a.get('anchor_reasoning', 'N/A')}\n"
                )
        print(f"  Generated {len(new_anchors)} additional anchors.\n")

        CHECKPOINT_DIR.mkdir(exist_ok=True)
        with open(CHECKPOINT_DIR / "extra_anchors.txt", "w") as f:
            f.write(extra_anchor_text)
    else:
        anchor_path = CHECKPOINT_DIR / "extra_anchors.txt"
        if anchor_path.exists():
            with open(anchor_path) as f:
                extra_anchor_text = f.read()
            print("  Loaded calibration anchors from checkpoint.\n")

    # 4. Batch Score
    total_batches = math.ceil(len(tasks) / batch_size)
    print(
        f"PHASE 2: Batch Scoring ({total_batches} batches, "
        f"starting at {start_batch + 1})  [temperature=0.2, no thinking]"
    )

    for b in range(start_batch, total_batches):
        start = b * batch_size
        end = min(start + batch_size, len(tasks))
        batch = tasks[start:end]
        print(f"  Batch {b+1}/{total_batches} — tasks {start+1}-{end}")

        content = build_batch_scorer_content(
            batch, b + 1, total_batches, extra_anchor_text
        )
        raw = call_claude(content, max_tokens=4096, use_thinking=False)
        result = parse_json(raw)

        for s in result["scores"]:
            s["batch"] = b + 1
            s["global_index"] = start + s["index"] - 1
        all_scores.extend(result["scores"])

        save_checkpoint(all_scores, b)

        if b < total_batches - 1:
            time.sleep(1)

    print(f"  Scored {len(all_scores)} tasks total.\n")

    # 5. Audit (batched, max 30 tasks per audit call)
    print("PHASE 3: Drift Audit  [adaptive thinking enabled]")
    audit_sample_size = max(10, len(all_scores) // 10)
    audit_sample_size = min(audit_sample_size, 385)

    import random
    audit_indices = random.sample(
        range(len(all_scores)), min(audit_sample_size, len(all_scores))
    )

    audit_sample = []
    for idx in audit_indices:
        s = all_scores[idx]
        gi = s["global_index"]
        audit_sample.append(
            {
                "batch": s["batch"],
                "index": s["index"],
                "Job_Title": tasks[gi].get("Job_Title", "N/A"),
                "Function_Name": tasks[gi].get("Function_Name", "N/A"),
                "Task_Description": tasks[gi]["Task_Description"],
                "Task_Type": tasks[gi].get("Task_Type", "N/A"),
                "score_moderate": s["mod"],
                "score_significant": s["sig"],
            }
        )

    AUDIT_BATCH_SIZE = 15
    all_flagged = []
    audit_batches = math.ceil(len(audit_sample) / AUDIT_BATCH_SIZE)
    print(f"  Auditing {len(audit_sample)} tasks in {audit_batches} batches...")

    for ab in range(audit_batches):
        a_start = ab * AUDIT_BATCH_SIZE
        a_end = min(a_start + AUDIT_BATCH_SIZE, len(audit_sample))
        audit_batch = audit_sample[a_start:a_end]
        print(f"  Audit batch {ab+1}/{audit_batches} — {len(audit_batch)} tasks")

        content = build_auditor_content(audit_batch)
        audit_raw = call_claude(content, max_tokens=32000, use_thinking=True)
        audit_result = parse_json(audit_raw)

        flagged = [a for a in audit_result["audits"] if a.get("flagged")]
        all_flagged.extend(flagged)

        if ab < audit_batches - 1:
            time.sleep(1)

    print(f"  Flagged {len(all_flagged)}/{len(audit_sample)} tasks for re-scoring.")

    # 6. Apply audit corrections
    if all_flagged:
        print(f"\nPHASE 4: Applying {len(all_flagged)} corrections")
        for f in all_flagged:
            for s in all_scores:
                if s["batch"] == f["batch"] and s["index"] == f["index"]:
                    print(
                        f"  Correcting batch {f['batch']} #{f['index']}: "
                        f"mod {s['mod']}→{f['audited_mod']}, "
                        f"sig {s['sig']}→{f['audited_sig']}"
                    )
                    s["mod"] = f["audited_mod"]
                    s["sig"] = f["audited_sig"]
                    s["audit_corrected"] = True
                    break

    # 7. Write output
    print(f"\nPHASE 5: Writing output to {output_path}")
    for s in all_scores:
        gi = s["global_index"]
        df.loc[gi, "score_moderate"] = s["mod"]
        df.loc[gi, "score_significant"] = s["sig"]
        df.loc[gi, "audit_corrected"] = s.get("audit_corrected", False)

    df.to_excel(output_path, index=False)
    clear_checkpoint()
    print(f"\nDONE. {len(df)} tasks scored and written to {output_path}")

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"  Mean moderate score:    {df['score_moderate'].mean():.3f}")
    print(f"  Mean significant score: {df['score_significant'].mean():.3f}")
    print(f"  Tasks at 0.00 (mod):    {(df['score_moderate'] == 0).sum()}")
    print(f"  Tasks at 1.00 (mod):    {(df['score_moderate'] == 1).sum()}")
    print(f"  Tasks at 0.00 (sig):    {(df['score_significant'] == 0).sum()}")
    print(f"  Tasks at 1.00 (sig):    {(df['score_significant'] == 1).sum()}")
    print(f"  Audit corrections:      {len(all_flagged)}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default="/Users/charliesheiner/Projects/ai-labor-analysis/jobs-data.xlsx",
    )
    parser.add_argument(
        "--output",
        default="/Users/charliesheiner/Projects/ai-labor-analysis/scored_tasks.xlsx",
    )
    parser.add_argument("--batch-size", type=int, default=25)
    args = parser.parse_args()
    run_pipeline(args.input, args.output, args.batch_size)
