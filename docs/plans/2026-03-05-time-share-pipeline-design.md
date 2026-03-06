# Time_Share_Pct Pipeline — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Assign Time_Share_Pct to 5,382 tasks across 310 SOC entries using Opus, then compute Economy_Weight_K.

**Architecture:** Single script `scoring/task_pipeline/time_share.py` reads the `3 Tasks` tab, enriches with frequency from `onet_raw.json`, calls Opus (4 workers) per SOC, validates/normalizes, checkpoints to JSON, writes back to workbook.

**Tech Stack:** Python 3, openpyxl, anthropic SDK, concurrent.futures

---

## Key Context

- **Workbook:** `jobs-data-v3.xlsx`, tab `3 Tasks`, 12 columns, 5382 data rows
- **310 SOC entries:** 293 with O*NET tasks (ON- prefix), 17 LLM-generated (CL- prefix)
- **Task counts:** 7-20 per SOC, median 18, mean 17.4
- **Frequency enrichment:** `onet_raw.json` has frequency for 92% of O*NET tasks. Match by exact task_text (confirmed: workbook texts are exact subset of onet_raw texts). CL- tasks get no frequency (LLM assigns "N/A").
- **Existing pattern:** `curate_and_score.py` shows the established API calling, retry, and progress patterns in this project.

---

### Task 1: Build input extraction (read workbook + enrich frequency)

**Files:**
- Create: `scoring/task_pipeline/time_share.py`

**Step 1: Write the extraction function**

```python
"""Time_Share_Pct Pipeline: Assign time allocation using Opus.

Reads 3 Tasks tab, enriches with O*NET frequency data, calls Opus
to assign time_share_pct per task (summing to 100 per SOC), validates,
and writes back Time_Share_Pct + Economy_Weight_K to the workbook.
"""

import json
import os
import sys
import time
import openpyxl
import anthropic
from concurrent.futures import ThreadPoolExecutor, as_completed

WORKBOOK = "jobs-data-v3.xlsx"
ONET_RAW = "scoring/task_pipeline/onet_raw.json"
RESULTS_FILE = "scoring/task_pipeline/time_share_results.json"
MODEL = "claude-opus-4-6"
MAX_WORKERS = 4
MAX_RETRIES = 3


def load_frequency_lookup():
    """Build task_text -> frequency lookup from onet_raw.json."""
    with open(ONET_RAW) as f:
        raw = json.load(f)
    lookup = {}
    for entry in raw:
        for task in entry.get("tasks", []):
            if task.get("frequency") and task.get("task_text"):
                lookup[task["task_text"]] = task["frequency"]
    return lookup


def load_tasks_from_workbook():
    """Read 3 Tasks tab, group by SOC_Code."""
    wb = openpyxl.load_workbook(WORKBOOK, data_only=True)
    ws = wb["3 Tasks"]

    soc_entries = {}  # soc_code -> {title, employment_K, tasks: [...]}
    for row in range(2, ws.max_row + 1):
        soc_code = ws.cell(row=row, column=1).value
        if not soc_code:
            continue

        if soc_code not in soc_entries:
            soc_entries[soc_code] = {
                "soc_code": soc_code,
                "title": ws.cell(row=row, column=2).value,
                "employment_K": ws.cell(row=row, column=9).value or 0,
                "tasks": [],
            }

        soc_entries[soc_code]["tasks"].append({
            "row": row,
            "task_id": ws.cell(row=row, column=3).value,
            "task_description": ws.cell(row=row, column=4).value,
            "task_type": ws.cell(row=row, column=5).value,
            "importance": ws.cell(row=row, column=7).value,
            "gwa": ws.cell(row=row, column=8).value,
        })

    wb.close()
    return soc_entries


def enrich_with_frequency(soc_entries, freq_lookup):
    """Add frequency field to each task from O*NET data."""
    enriched = 0
    total = 0
    for entry in soc_entries.values():
        for task in entry["tasks"]:
            total += 1
            freq = freq_lookup.get(task["task_description"])
            task["frequency"] = freq if freq else None
            if freq:
                enriched += 1
    return enriched, total
```

**Step 2: Verify extraction works**

Run:
```bash
python3 -c "
import sys; sys.path.insert(0, '.')
from scoring.task_pipeline.time_share import load_tasks_from_workbook, load_frequency_lookup, enrich_with_frequency
entries = load_tasks_from_workbook()
freq = load_frequency_lookup()
enriched, total = enrich_with_frequency(entries, freq)
print(f'SOCs: {len(entries)}, Tasks: {total}, Frequency enriched: {enriched}')
sample = list(entries.values())[0]
print(f'Sample: {sample[\"soc_code\"]} - {sample[\"title\"]} ({len(sample[\"tasks\"])} tasks)')
t = sample['tasks'][0]
print(f'  Task: {t[\"task_id\"]} freq={t[\"frequency\"]} imp={t[\"importance\"]}')
"
```

Expected: 310 SOCs, 5382 tasks, ~4700+ frequency enriched.

---

### Task 2: Build prompt and LLM calling

**Files:**
- Modify: `scoring/task_pipeline/time_share.py`

**Step 1: Add the prompt template and API calling logic**

Append to `time_share.py`:

```python
SYSTEM_PROMPT = """You are an occupational analyst. You produce structured JSON output only. No markdown, no commentary."""

USER_PROMPT = """Assign the percentage of a typical worker's time spent on each task for this occupation.

## Occupation
- SOC Code: {soc_code}
- Title: {title}
- Employment: {employment_K}K workers

## Tasks ({task_count} tasks)
{task_list}

## Instructions

For EACH task, assign an integer `time_share_pct` representing what percentage of a
typical worker's work time is spent on this task. All values must sum to exactly 100.

Guidelines:
- Core tasks generally get more time than Supplemental tasks
- Daily tasks generally get more time than yearly tasks
- Importance does NOT equal time — a rare emergency task can be importance=5 but time=2%
- Every task must get at least 1%
- Be realistic about how workers actually spend their days

Return ONLY a JSON array in the same order as the input, with task_id and time_share_pct:
```json
[
  {{"task_id": "ON-111011-001", "time_share_pct": 15}},
  {{"task_id": "ON-111011-002", "time_share_pct": 8}}
]
```"""


def format_task_list(tasks):
    """Format tasks as numbered list for the prompt."""
    lines = []
    for i, t in enumerate(tasks, 1):
        freq_str = f"freq={t['frequency']}" if t["frequency"] else "freq=N/A"
        lines.append(
            f"{i}. [{t['task_id']}] [{t['task_type']}] imp={t['importance']} "
            f"{freq_str} gwa={t['gwa']}\n   {t['task_description']}"
        )
    return "\n".join(lines)


def call_opus(client, soc_entry):
    """Call Opus to assign time shares for one SOC."""
    task_list = format_task_list(soc_entry["tasks"])
    prompt = USER_PROMPT.format(
        soc_code=soc_entry["soc_code"],
        title=soc_entry["title"],
        employment_K=soc_entry["employment_K"],
        task_count=len(soc_entry["tasks"]),
        task_list=task_list,
    )

    for attempt in range(MAX_RETRIES):
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            text = response.content[0].text.strip()

            # Strip markdown wrapping if present
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            text = text.strip()

            return json.loads(text)

        except json.JSONDecodeError as e:
            print(f"  [{soc_entry['soc_code']}] JSON parse error (attempt {attempt+1}): {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(2)

        except anthropic.RateLimitError:
            wait = 30 * (attempt + 1)
            print(f"  [{soc_entry['soc_code']}] Rate limited, waiting {wait}s...")
            time.sleep(wait)

        except anthropic.APIError as e:
            print(f"  [{soc_entry['soc_code']}] API error (attempt {attempt+1}): {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(5)

    return None
```

---

### Task 3: Build validation and normalization

**Files:**
- Modify: `scoring/task_pipeline/time_share.py`

**Step 1: Add validation logic**

```python
def validate_and_normalize(result, soc_entry):
    """Validate LLM response and normalize time shares.

    Returns (task_id_to_share, warnings, needs_retry).
    """
    soc_code = soc_entry["soc_code"]
    expected_ids = [t["task_id"] for t in soc_entry["tasks"]]
    warnings = []

    if not isinstance(result, list):
        return None, ["Response is not a list"], True

    # Check task count
    if len(result) != len(expected_ids):
        return None, [f"Got {len(result)} tasks, expected {len(expected_ids)}"], True

    # Build mapping
    id_to_share = {}
    for item in result:
        tid = item.get("task_id")
        share = item.get("time_share_pct")
        if tid not in expected_ids:
            return None, [f"Unknown task_id: {tid}"], True
        if not isinstance(share, (int, float)) or share < 0:
            return None, [f"Invalid time_share for {tid}: {share}"], True
        id_to_share[tid] = share

    if len(id_to_share) != len(expected_ids):
        missing = set(expected_ids) - set(id_to_share.keys())
        return None, [f"Missing task_ids: {missing}"], True

    # Check sum and normalize
    total = sum(id_to_share.values())

    if abs(total - 100) <= 2:
        # Within ±2%: silent normalize
        pass
    elif abs(total - 100) <= 5:
        # Within ±5%: normalize with warning
        warnings.append(f"Sum was {total}, normalized to 100")
    else:
        # >5% deviation: retry
        return None, [f"Sum is {total}, too far from 100"], True

    # Normalize to exactly 100
    if total != 100 and total > 0:
        factor = 100.0 / total
        for tid in id_to_share:
            id_to_share[tid] = max(1, round(id_to_share[tid] * factor))
        # Fix rounding remainder
        diff = 100 - sum(id_to_share.values())
        if diff != 0:
            # Apply remainder to the largest share
            largest = max(id_to_share, key=id_to_share.get)
            id_to_share[largest] += diff

    # Sanity warnings (non-blocking)
    for tid, share in id_to_share.items():
        if share < 1:
            warnings.append(f"{tid}: share={share}% (< 1%)")
        if share > 40:
            warnings.append(f"{tid}: share={share}% (> 40%)")

    return id_to_share, warnings, False
```

---

### Task 4: Build checkpoint/resume and parallel processing

**Files:**
- Modify: `scoring/task_pipeline/time_share.py`

**Step 1: Add resume logic and process_soc function**

```python
def load_checkpoint():
    """Load completed results from checkpoint file."""
    if os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE) as f:
            results = json.load(f)
        return {r["soc_code"]: r for r in results}
    return {}


def save_checkpoint(completed):
    """Save all completed results to checkpoint file."""
    results = sorted(completed.values(), key=lambda r: r["soc_code"])
    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=2)


def process_soc(client, soc_entry):
    """Process one SOC: call Opus, validate, return result or None."""
    soc_code = soc_entry["soc_code"]

    for retry in range(MAX_RETRIES):
        raw = call_opus(client, soc_entry)
        if raw is None:
            continue

        id_to_share, warnings, needs_retry = validate_and_normalize(raw, soc_entry)

        if warnings:
            for w in warnings[:3]:
                print(f"  [{soc_code}] {w}")

        if needs_retry and retry < MAX_RETRIES - 1:
            print(f"  [{soc_code}] Retrying ({retry + 1}/{MAX_RETRIES})...")
            time.sleep(2)
            continue

        if id_to_share is None:
            return None

        return {
            "soc_code": soc_code,
            "title": soc_entry["title"],
            "employment_K": soc_entry["employment_K"],
            "task_count": len(soc_entry["tasks"]),
            "time_shares": id_to_share,
            "warnings": warnings,
        }

    return None
```

---

### Task 5: Build main function with parallel execution

**Files:**
- Modify: `scoring/task_pipeline/time_share.py`

**Step 1: Add main function**

```python
def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set.")
        sys.exit(1)

    client = anthropic.Anthropic()

    # Load inputs
    print("Loading tasks from workbook...")
    soc_entries = load_tasks_from_workbook()
    print(f"  {len(soc_entries)} SOC entries, {sum(len(e['tasks']) for e in soc_entries.values())} tasks")

    print("Loading frequency data...")
    freq_lookup = load_frequency_lookup()
    enriched, total = enrich_with_frequency(soc_entries, freq_lookup)
    print(f"  Frequency enriched: {enriched}/{total} tasks ({100*enriched/total:.0f}%)")

    # Resume support
    completed = load_checkpoint()
    if completed:
        print(f"  Resuming: {len(completed)} already done")

    remaining = {k: v for k, v in soc_entries.items() if k not in completed}
    print(f"  Remaining: {len(remaining)} SOCs")

    if not remaining:
        print("All SOCs already complete. Running writeback...")
        writeback(completed, soc_entries)
        return

    # Process with parallel workers
    failed = []
    processed = 0

    print(f"\nProcessing with {MAX_WORKERS} workers (Opus)...")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(process_soc, client, entry): soc_code
            for soc_code, entry in remaining.items()
        }

        for future in as_completed(futures):
            soc_code = futures[future]
            processed += 1

            try:
                result = future.result()
                if result:
                    completed[soc_code] = result
                    print(f"  [{processed}/{len(remaining)}] {soc_code}: "
                          f"{result['title']} ({result['task_count']} tasks)")
                else:
                    failed.append(soc_code)
                    print(f"  [{processed}/{len(remaining)}] {soc_code}: FAILED")
            except Exception as e:
                failed.append(soc_code)
                print(f"  [{processed}/{len(remaining)}] {soc_code}: ERROR {e}")

            # Checkpoint every 10 completions
            if processed % 10 == 0:
                save_checkpoint(completed)
                print(f"  --- Checkpoint: {len(completed)} complete, {len(failed)} failed ---")

    # Final save
    save_checkpoint(completed)

    print(f"\nScoring complete: {len(completed)} SOCs, {len(failed)} failed")
    if failed:
        print(f"Failed SOCs: {failed}")

    # Writeback if all complete
    if len(completed) == len(soc_entries):
        writeback(completed, soc_entries)
    else:
        print(f"\n{len(soc_entries) - len(completed)} SOCs incomplete. Re-run to retry.")


if __name__ == "__main__":
    main()
```

---

### Task 6: Build workbook writeback

**Files:**
- Modify: `scoring/task_pipeline/time_share.py`

**Step 1: Add writeback function** (insert before `main()`)

```python
def writeback(completed, soc_entries):
    """Write Time_Share_Pct and Economy_Weight_K to workbook."""
    print("\nWriting to workbook...")
    wb = openpyxl.load_workbook(WORKBOOK)
    ws = wb["3 Tasks"]

    updated = 0
    for row in range(2, ws.max_row + 1):
        soc_code = ws.cell(row=row, column=1).value
        task_id = ws.cell(row=row, column=3).value
        emp_k = ws.cell(row=row, column=9).value or 0

        if soc_code in completed and task_id:
            shares = completed[soc_code]["time_shares"]
            share = shares.get(task_id)
            if share is not None:
                ws.cell(row=row, column=6, value=share)  # Time_Share_Pct
                economy_weight = round(emp_k * share / 100, 2)
                ws.cell(row=row, column=10, value=economy_weight)  # Economy_Weight_K
                updated += 1

    wb.save(WORKBOOK)
    wb.close()
    print(f"  Updated {updated} rows in {WORKBOOK}")

    # Summary stats
    shares_all = []
    for r in completed.values():
        shares_all.extend(r["time_shares"].values())
    print(f"  Time shares: min={min(shares_all)}, max={max(shares_all)}, "
          f"mean={sum(shares_all)/len(shares_all):.1f}")
```

---

### Task 7: End-to-end dry run test

**Step 1: Test with 2 SOCs (no API call)**

Run:
```bash
python3 -c "
import sys; sys.path.insert(0, '.')
from scoring.task_pipeline.time_share import (
    load_tasks_from_workbook, load_frequency_lookup, enrich_with_frequency,
    validate_and_normalize, format_task_list
)

entries = load_tasks_from_workbook()
freq = load_frequency_lookup()
enrich_with_frequency(entries, freq)

# Test format_task_list
sample = list(entries.values())[0]
print(format_task_list(sample['tasks'][:3]))
print()

# Test validate_and_normalize with mock data
mock_result = [{'task_id': t['task_id'], 'time_share_pct': 100 // len(sample['tasks'])}
               for t in sample['tasks']]
# Fix sum
diff = 100 - sum(m['time_share_pct'] for m in mock_result)
mock_result[0]['time_share_pct'] += diff

shares, warnings, retry = validate_and_normalize(mock_result, sample)
print(f'Validation: shares={len(shares)}, warnings={warnings}, retry={retry}')
print(f'Sum: {sum(shares.values())}')
"
```

Expected: Formatted task list prints correctly, validation passes with sum=100.

**Step 2: Run full pipeline**

```bash
python3 scoring/task_pipeline/time_share.py
```

Expected: ~20-25 min runtime, 310/310 SOCs complete, workbook updated.

---

### Task 8: Post-run audit

**Step 1: Verify workbook state**

```bash
python3 -c "
import openpyxl

wb = openpyxl.load_workbook('jobs-data-v3.xlsx', data_only=True)
ws = wb['3 Tasks']

soc_sums = {}
null_shares = 0
null_econ = 0
total = 0

for r in range(2, ws.max_row + 1):
    soc = ws.cell(row=r, column=1).value
    ts = ws.cell(row=r, column=6).value
    ew = ws.cell(row=r, column=10).value
    if not soc:
        continue
    total += 1
    if ts is None:
        null_shares += 1
    else:
        soc_sums.setdefault(soc, 0)
        soc_sums[soc] += ts
    if ew is None:
        null_econ += 1

bad_sums = {s: v for s, v in soc_sums.items() if v != 100}
print(f'Total rows: {total}')
print(f'Null Time_Share_Pct: {null_shares}')
print(f'Null Economy_Weight_K: {null_econ}')
print(f'SOCs where sum != 100: {len(bad_sums)}')
if bad_sums:
    for s, v in list(bad_sums.items())[:5]:
        print(f'  {s}: sum={v}')
wb.close()
"
```

Expected: 0 nulls, 0 bad sums, all 5382 rows populated.

---

### Task 9: Commit

```bash
git add scoring/task_pipeline/time_share.py scoring/task_pipeline/time_share_results.json docs/plans/2026-03-05-time-share-pipeline-design.md
git commit -m "Add Time_Share_Pct pipeline: Opus-based time allocation for 310 SOCs"
```
