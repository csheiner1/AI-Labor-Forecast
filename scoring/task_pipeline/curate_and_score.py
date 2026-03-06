"""Phase 1: LLM-powered task enrichment and autonomy scoring.

For O*NET-covered SOCs (340): takes pre-filtered tasks (all Core + top Supplemental,
capped at 20), has LLM assign time_share_pct, confirm metadata, and score autonomy.
For missing SOCs (17): generates 12 tasks from scratch with full metadata and scores.

Uses parallel batching with retry logic and resume support.

Output: scoring/task_pipeline/scored_tasks.json
"""

import json
import os
import sys
import time
import anthropic
from concurrent.futures import ThreadPoolExecutor, as_completed

INPUT = "scoring/task_pipeline/onet_raw.json"
OUTPUT = "scoring/task_pipeline/scored_tasks.json"
PROGRESS_DIR = "scoring/task_pipeline/progress"
MODEL = "claude-sonnet-4-20250514"
MAX_WORKERS = 6
MAX_RETRIES = 3
MAX_TASKS = 20      # Pre-filter cap for O*NET entries
MIN_TASKS_GEN = 12  # Target for LLM-generated entries

# ── GWA list (shared across prompts) ─────────────────────────────────────────

GWA_LIST = """Getting Information | Processing Information | Analyzing Data/Information |
Evaluating Information to Determine Compliance | Making Decisions and Solving Problems |
Thinking Creatively | Updating and Using Relevant Knowledge |
Developing Objectives and Strategies | Scheduling Work and Activities |
Organizing, Planning, and Prioritizing Work | Interacting With Computers |
Documenting/Recording Information | Interpreting Information for Others |
Communicating with Supervisors, Peers, or Subordinates |
Communicating with People Outside the Organization |
Establishing and Maintaining Interpersonal Relationships |
Selling or Influencing Others | Resolving Conflicts and Negotiating |
Coordinating the Work and Activities of Others | Training and Teaching Others |
Guiding, Directing, and Motivating Subordinates | Coaching and Developing Others |
Providing Consultation and Advice | Performing Administrative Activities |
Monitoring and Controlling Resources | Assisting and Caring for Others |
Performing for or Working with the Public |
Monitoring Processes, Materials, or Surroundings |
Identifying Objects, Actions, and Events |
Inspecting Equipment, Structures, or Materials |
Drafting/Specifying Technical Devices"""

# ── Prompt templates ──────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an occupational analyst specializing in AI labor displacement research.
You produce structured JSON output. Never include markdown formatting or commentary outside the JSON."""

ENRICH_PROMPT = """You are enriching and scoring a task inventory for the occupation below.
These tasks come from O*NET. Your job is to assign time allocations, fill any missing
metadata, and score each task for AI autonomy potential.

## Occupation
- SOC Code: {soc_code}
- Title: {soc_title}
- Employment: {employment_K}K workers
- Sectors: {sector_count} industries

## Tasks to Enrich ({task_count} tasks)
{task_list}

## Instructions

For EACH task above, return a JSON object with these fields:

1. **task_text**: Use the O*NET text as-is. For merged SOC groups, lightly edit only
   if two tasks are near-duplicates — combine them into one and drop the other.
   You may return fewer tasks than provided if you merge duplicates, but never add new tasks.

2. **task_type**: "Core" or "Supplemental". Use the O*NET classification if provided.
   For unclassified (n/a) tasks, assign based on whether the task is central to the role.

3. **time_share_pct**: Integer percentage of typical work time. All values must sum to
   exactly 100. High-frequency core tasks get larger shares. Rare supplemental tasks
   can be as low as 2%.

4. **importance**: Integer 1-5. Use O*NET importance if provided (round to nearest int).
   If N/A, assign based on how critical this task is to the role (5=essential, 1=minor).

5. **frequency**: "daily", "weekly", "monthly", or "yearly". Use O*NET frequency if
   provided. If N/A, assign based on typical cadence.

6. **gwa**: General Work Activity category. Use the O*NET GWA if provided and valid.
   If N/A or invalid, assign from this list:
   {gwa_list}

7. **aut_score_mod**: AI autonomy score under MODERATE scenario (18-month horizon
   through Oct 2027, steady continuation of current approaches, no breakthroughs).
   Use ONLY these values:
   - 0.00 = AI cannot meaningfully assist with this task
   - 0.25 = AI assists but human does most work
   - 0.50 = AI and human share work roughly equally
   - 0.75 = AI does most work, human reviews/approves
   - 1.00 = AI can fully perform this task autonomously

   MODERATE AI CAPABILITIES (Oct 2027):
   - Context: ~1.5M token window, reliable retrieval to ~400K tokens, degrades beyond
   - Tool use: Improved multi-tool chaining for familiar APIs/protocols
   - Agents: 4-6 hour autonomous work blocks. Reliable on ~5-8 step workflows, fragile beyond 10 steps
   - Efficiency: 3x token cost reduction from March 2026 baseline
   - Alignment: Improved RLHF. RLVR advances in verifiable domains (code, math, science,
     structured data) via self-distillation. Professional judgment tasks still rely on RLHF
     without outcome verification
   - Reasoning: Reliable on ~3 levels of derived-premise dependency. Deep analysis still
     needs human verification
   - Speed: <400ms voice, ~1s text, 8-60s complex reasoning
   - Browser/computer use: Improved but still unreliable on complex web workflows
   - Reliability: Executes well-defined task sequences. Pivoting between disparate tasks
     requires explicit re-prompting. Limited error detection

8. **aut_score_sig**: AI autonomy score under SIGNIFICANT scenario (18-month horizon
   through Oct 2027, step-change improvement requiring architectural or training
   breakthroughs). Same 5-point scale.

   SIGNIFICANT AI CAPABILITIES (Oct 2027):
   - Context: ~2-3M token window, reliable retrieval to ~1M tokens, some degradation beyond
   - Tool use: Reliable multi-tool chaining across unfamiliar APIs
   - Agents: 6-10 hour autonomous work blocks. Reliable on ~12-15 step workflows,
     20-step viable with light oversight
   - Efficiency: 10x token cost reduction from March 2026 baseline
   - Alignment: RLVR expands to semi-verifiable professional domains (financial models
     with backtestable outputs, legal research with citation verification, medical diagnosis
     against confirmed outcomes). Substantially more reliable in structured professional
     reasoning. Truly subjective judgment remains RLHF-dependent
   - Reasoning: Reliable on ~4 levels of derived-premise dependency. Novel/unprecedented
     reasoning still limited
   - Speed: <250ms voice, ~0.5s text, 5-30s complex reasoning
   - Browser/computer use: Reliable navigation across arbitrary web interfaces
   - Multimodal: Strong vision, document, and diagram understanding
   - Orchestration: Parallel agent coordination
   - Reliability: Executes longer task sequences with less rigid structure. Can pivot
     between related tasks within a domain without full context reset. Improved error
     detection. More consistent outputs across runs

CRITICAL SCORING RULES:
- Score each task INDEPENDENTLY. Do not let one task's score influence others.
- A job with mostly automatable tasks can still have one task that scores 0.00.
- Consider what the task actually requires: physical presence? real-time human judgment?
  emotional rapport? regulatory sign-off? These resist automation.
- Consider what AI excels at: data analysis, document generation, pattern matching,
  scheduling, information retrieval. These score higher.
- The score captures both technical capability AND economic viability. A task where AI
  could technically perform it but the cost exceeds human labor should score lower.

Return ONLY a JSON array of objects (one per task, or fewer if you merged duplicates):
```json
[
  {{
    "task_text": "...",
    "task_type": "Core",
    "time_share_pct": 15,
    "importance": 4,
    "frequency": "daily",
    "gwa": "Analyzing Data/Information",
    "aut_score_mod": 0.50,
    "aut_score_sig": 0.75
  }}
]
```"""

GENERATE_PROMPT = """You are generating a task inventory for an occupation that lacks O*NET task data.
Create {target_count} representative tasks from your knowledge of this occupation.

## Occupation
- SOC Code: {soc_code}
- Title: {soc_title}
- Employment: {employment_K}K workers
- Sectors: {sector_count} industries

## Instructions

Generate exactly {target_count} tasks that accurately represent what workers in this
occupation actually do day-to-day. Aim for 8-9 Core and 3-4 Supplemental tasks.
Be specific and concrete — avoid generic corporate language.

For each task provide ALL of these fields:
- task_text: Specific description of the task
- task_type: "Core" or "Supplemental"
- time_share_pct: Integer, all must sum to exactly 100
- importance: Integer 1-5 (5=essential to role)
- frequency: "daily", "weekly", "monthly", or "yearly"
- gwa: One category from: {gwa_list}
- aut_score_mod: AI autonomy under MODERATE scenario (0 / 0.25 / 0.5 / 0.75 / 1.0)
  Moderate = steady continuation through Oct 2027, no breakthroughs:
  ~1.5M context (reliable to ~400K), improved tool chaining for familiar APIs,
  reliable ~5-8 step workflows, 3x cost reduction, RLVR in verifiable domains only,
  ~3 levels reliable reasoning depth, <400ms voice / 8-60s complex reasoning,
  unreliable browser on complex workflows, limited error detection.

- aut_score_sig: AI autonomy under SIGNIFICANT scenario (0 / 0.25 / 0.5 / 0.75 / 1.0)
  Significant = step-change breakthroughs through Oct 2027:
  ~2-3M context (reliable to ~1M), reliable tool chaining across unfamiliar APIs,
  reliable ~12-15 step workflows, 10x cost reduction, RLVR in semi-verifiable
  professional domains, ~4 levels reliable reasoning depth, <250ms voice / 5-30s
  complex reasoning, reliable browser navigation, strong multimodal understanding,
  parallel agent orchestration, improved error detection and coordination.

SCORING RULES:
- Score each task independently — no halo effects
- 0.00 = AI cannot assist, 0.25 = AI assists/human leads, 0.50 = shared,
  0.75 = AI leads/human reviews, 1.00 = fully autonomous
- Physical, high-stakes judgment, and relationship tasks resist automation
- Data processing, document generation, and pattern matching are more automatable
- The score captures both technical capability AND economic viability

Return ONLY a JSON array of exactly {target_count} objects."""


# ── Valid values for validation ───────────────────────────────────────────────

VALID_GWAS = {
    "Getting Information", "Processing Information", "Analyzing Data/Information",
    "Evaluating Information to Determine Compliance",
    "Making Decisions and Solving Problems", "Thinking Creatively",
    "Updating and Using Relevant Knowledge", "Developing Objectives and Strategies",
    "Scheduling Work and Activities", "Organizing, Planning, and Prioritizing Work",
    "Interacting With Computers", "Documenting/Recording Information",
    "Interpreting Information for Others",
    "Communicating with Supervisors, Peers, or Subordinates",
    "Communicating with People Outside the Organization",
    "Establishing and Maintaining Interpersonal Relationships",
    "Selling or Influencing Others", "Resolving Conflicts and Negotiating",
    "Coordinating the Work and Activities of Others",
    "Training and Teaching Others",
    "Guiding, Directing, and Motivating Subordinates",
    "Coaching and Developing Others", "Providing Consultation and Advice",
    "Performing Administrative Activities", "Monitoring and Controlling Resources",
    "Assisting and Caring for Others", "Performing for or Working with the Public",
    "Monitoring Processes, Materials, or Surroundings",
    "Identifying Objects, Actions, and Events",
    "Inspecting Equipment, Structures, or Materials",
    "Drafting/Specifying Technical Devices",
}
VALID_SCORES = {0, 0.25, 0.5, 0.75, 1.0}
VALID_FREQS = {"daily", "weekly", "monthly", "yearly"}


# ── Pre-filtering ─────────────────────────────────────────────────────────────

def prefilter_tasks(tasks, max_tasks=MAX_TASKS):
    """Pre-filter O*NET tasks: all Core + top Supplemental by importance, capped."""
    core = [t for t in tasks if t["task_type"] == "Core"]
    supp = sorted(
        [t for t in tasks if t["task_type"] == "Supplemental"],
        key=lambda t: -(t["importance"] or 0),
    )
    untyped = sorted(
        [t for t in tasks if t["task_type"] not in ("Core", "Supplemental")],
        key=lambda t: -(t["importance"] or 0),
    )

    # Priority: core + untyped (potential core), then supplemental to fill
    candidates = core + untyped
    candidates = sorted(candidates, key=lambda t: -(t["importance"] or 0))[:max_tasks - 3]
    remaining_slots = max_tasks - len(candidates)
    candidates += supp[:max(0, remaining_slots)]
    return candidates[:max_tasks]


def format_task_list(tasks):
    """Format O*NET tasks as a numbered list for the prompt."""
    lines = []
    for i, t in enumerate(tasks, 1):
        imp_str = f"imp={t['importance']}" if t["importance"] else "imp=N/A"
        freq_str = f"freq={t['frequency']}" if t["frequency"] else "freq=N/A"
        gwa_str = f"gwa={t['gwa']}" if t["gwa"] else "gwa=N/A"
        type_str = t["task_type"] or "n/a"
        src = f"[{t['source_soc']}] " if t.get("source_soc") else ""
        lines.append(
            f"{i}. {src}[{type_str}] {imp_str} {freq_str} {gwa_str}\n   {t['task_text']}"
        )
    return "\n".join(lines)


# ── Validation ────────────────────────────────────────────────────────────────

def validate_response(tasks_json, soc_code, expected_min=8, expected_max=22):
    """Validate LLM response structure and fix common issues."""
    errors = []

    if not isinstance(tasks_json, list):
        return None, ["Response is not a list"]

    if len(tasks_json) < expected_min or len(tasks_json) > expected_max:
        errors.append(f"Got {len(tasks_json)} tasks (expected {expected_min}-{expected_max})")
        if len(tasks_json) < 5 or len(tasks_json) > 30:
            return None, errors

    # Fix time_share_pct to sum to 100
    total_time = sum(t.get("time_share_pct", 0) for t in tasks_json)
    if total_time != 100:
        errors.append(f"Time shares sum to {total_time}, not 100")
        if total_time > 0:
            factor = 100.0 / total_time
            for t in tasks_json:
                t["time_share_pct"] = max(1, round(t.get("time_share_pct", 5) * factor))
            diff = 100 - sum(t["time_share_pct"] for t in tasks_json)
            tasks_json[0]["time_share_pct"] += diff

    for i, t in enumerate(tasks_json):
        # GWA validation
        if t.get("gwa") not in VALID_GWAS:
            errors.append(f"Task {i}: invalid GWA '{t.get('gwa')}'")
            t["gwa"] = "Making Decisions and Solving Problems"

        # Score validation
        for score_key in ["aut_score_mod", "aut_score_sig"]:
            val = t.get(score_key)
            if val not in VALID_SCORES:
                if isinstance(val, (int, float)):
                    nearest = min(VALID_SCORES, key=lambda x: abs(x - val))
                    t[score_key] = nearest
                    errors.append(f"Task {i}: {score_key}={val} -> {nearest}")
                else:
                    t[score_key] = 0.5

        # Frequency validation
        if t.get("frequency") not in VALID_FREQS:
            t["frequency"] = "weekly"

        # Importance validation
        if not isinstance(t.get("importance"), (int, float)) or not (1 <= t["importance"] <= 5):
            t["importance"] = 3
        else:
            t["importance"] = round(t["importance"])

        # Task type validation
        if t.get("task_type") not in ("Core", "Supplemental"):
            t["task_type"] = "Core"

    return tasks_json, errors


# ── LLM calling ──────────────────────────────────────────────────────────────

def call_llm(client, prompt, soc_code):
    """Call Claude API with retry logic."""
    for attempt in range(MAX_RETRIES):
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=8192,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            text = response.content[0].text.strip()

            # Extract JSON from response (handle markdown wrapping)
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            text = text.strip()

            tasks_json = json.loads(text)
            return tasks_json

        except json.JSONDecodeError as e:
            print(f"  [{soc_code}] JSON parse error: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(2)
                continue
            return None

        except anthropic.RateLimitError:
            wait = 30 * (attempt + 1)
            print(f"  [{soc_code}] Rate limited, waiting {wait}s...")
            time.sleep(wait)
            continue

        except anthropic.APIError as e:
            print(f"  [{soc_code}] API error: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(5)
                continue
            return None

    return None


def process_entry(client, entry):
    """Process a single SOC entry: enrich O*NET tasks or generate from scratch."""
    soc_code = entry["soc_code"]
    soc_title = entry["soc_title"]

    if entry["source"] == "onet" and entry["tasks"]:
        # Pre-filter O*NET tasks
        filtered = prefilter_tasks(entry["tasks"])
        task_list = format_task_list(filtered)

        prompt = ENRICH_PROMPT.format(
            soc_code=soc_code,
            soc_title=soc_title,
            employment_K=entry["total_employment_K"],
            sector_count=entry["sector_count"],
            task_count=len(filtered),
            task_list=task_list,
            gwa_list=GWA_LIST,
        )
        source = "onet_curated"
        expect_min = max(7, len(filtered) - 5)  # allow merging of duplicates
        expect_max = len(filtered) + 2
    else:
        prompt = GENERATE_PROMPT.format(
            soc_code=soc_code,
            soc_title=soc_title,
            employment_K=entry["total_employment_K"],
            sector_count=entry["sector_count"],
            target_count=MIN_TASKS_GEN,
            gwa_list=GWA_LIST,
        )
        source = "llm_generated"
        expect_min = 8
        expect_max = MIN_TASKS_GEN + 3

    raw = call_llm(client, prompt, soc_code)
    if raw is None:
        return None

    validated, errors = validate_response(raw, soc_code, expect_min, expect_max)
    if errors:
        print(f"  [{soc_code}] Warnings: {'; '.join(errors[:3])}")
    if validated is None:
        print(f"  FAILED validation: {soc_code}")
        return None

    return {
        "soc_code": soc_code,
        "soc_title": soc_title,
        "is_merged": entry["is_merged"],
        "total_employment_K": entry["total_employment_K"],
        "source": source,
        "task_count": len(validated),
        "tasks": validated,
        "validation_warnings": errors or [],
    }


# ── Progress management ──────────────────────────────────────────────────────

def save_progress(results, failed):
    os.makedirs(PROGRESS_DIR, exist_ok=True)
    with open(os.path.join(PROGRESS_DIR, "partial_results.json"), "w") as f:
        json.dump(results, f, indent=2)
    if failed:
        with open(os.path.join(PROGRESS_DIR, "failed.json"), "w") as f:
            json.dump(failed, f, indent=2)


def load_progress():
    path = os.path.join(PROGRESS_DIR, "partial_results.json")
    if os.path.exists(path):
        with open(path) as f:
            results = json.load(f)
        completed = {r["soc_code"] for r in results}
        return results, completed
    return [], set()


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY environment variable not set.")
        sys.exit(1)

    client = anthropic.Anthropic()

    print("Loading O*NET raw data...")
    with open(INPUT) as f:
        entries = json.load(f)
    print(f"  {len(entries)} SOC entries to process")

    # Resume support
    results, completed = load_progress()
    if completed:
        print(f"  Resuming: {len(completed)} already done, {len(entries) - len(completed)} remaining")

    remaining = [e for e in entries if e["soc_code"] not in completed]
    onet_count = sum(1 for e in remaining if e["source"] == "onet")
    llm_count = sum(1 for e in remaining if e["source"] == "llm_generate")
    print(f"  O*NET enrichment: {onet_count}, LLM generation: {llm_count}")

    failed = []
    processed = 0

    print(f"\nProcessing with {MAX_WORKERS} parallel workers...")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(process_entry, client, entry): entry
            for entry in remaining
        }

        for future in as_completed(futures):
            entry = futures[future]
            processed += 1

            try:
                result = future.result()
                if result:
                    results.append(result)
                    print(f"  [{processed}/{len(remaining)}] {entry['soc_code']}: "
                          f"{entry['soc_title']} ({result['task_count']} tasks)")
                else:
                    failed.append(entry["soc_code"])
                    print(f"  [{processed}/{len(remaining)}] {entry['soc_code']}: FAILED")
            except Exception as e:
                failed.append(entry["soc_code"])
                print(f"  [{processed}/{len(remaining)}] {entry['soc_code']}: ERROR {e}")

            if processed % 25 == 0:
                save_progress(results, failed)
                print(f"  --- Progress saved ({len(results)} complete, {len(failed)} failed) ---")

    results.sort(key=lambda r: r["soc_code"])

    with open(OUTPUT, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved {len(results)} scored entries to {OUTPUT}")

    if failed:
        print(f"\n{len(failed)} FAILED entries:")
        for soc in failed:
            print(f"  {soc}")
        save_progress(results, failed)
    else:
        partial = os.path.join(PROGRESS_DIR, "partial_results.json")
        if os.path.exists(partial):
            os.remove(partial)

    # Summary stats
    all_tasks = [t for r in results for t in r["tasks"]]
    task_counts = [r["task_count"] for r in results]
    mod_scores = [t["aut_score_mod"] for t in all_tasks]
    sig_scores = [t["aut_score_sig"] for t in all_tasks]

    print(f"\nSummary:")
    print(f"  Entries: {len(results)}")
    print(f"  Total tasks: {len(all_tasks)}")
    print(f"  Tasks per SOC: min={min(task_counts)}, max={max(task_counts)}, "
          f"avg={sum(task_counts)/len(task_counts):.1f}")
    print(f"  Aut_Score_Mod: mean={sum(mod_scores)/len(mod_scores):.3f}")
    print(f"  Aut_Score_Sig: mean={sum(sig_scores)/len(sig_scores):.3f}")

    sources = {}
    for r in results:
        sources[r["source"]] = sources.get(r["source"], 0) + 1
    print(f"  Sources: {sources}")


if __name__ == "__main__":
    main()
