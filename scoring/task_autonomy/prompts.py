"""Prompt templates for task-level autonomy scoring.

Two scenarios scored per task:
  - Moderate (aut_score_mod): steady continuation, no breakthroughs
  - Significant (aut_score_sig): step-change improvement, architectural breakthroughs

Each score uses the 5-point scale {0.00, 0.25, 0.50, 0.75, 1.00} plus a
confidence flag (high/low) for audit prioritization.
"""

SYSTEM_PROMPT = """\
You are an occupational analyst scoring tasks for an AI labor displacement forecast.
You produce structured JSON output only. No markdown, no commentary outside the JSON."""

SCORING_PROMPT = """\
Score each task below for AI autonomy potential under TWO scenarios.
The occupation context is provided so you understand what the worker actually does,
but score each TASK independently based on what that specific task requires.

## Occupation Context
- SOC Code: {soc_code}
- Title: {job_title}
- Employment: {employment_K}K workers

## Tasks to Score ({task_count} tasks)
{task_list}

## Scoring Scale (use ONLY these values)
- 0.00 = AI cannot meaningfully assist — hard gate exists
    Physical presence required, regulatory signature, real-time human judgment
    in novel/high-stakes situations, or embodied dexterity.
    Examples: performing surgery, physically inspecting a building, testifying
    in court, restraining a suspect, comforting a grieving patient in person.

- 0.25 = AI assists but human does most work — copilot mode
    AI drafts, suggests, retrieves, but human drives decisions and execution.
    The task requires significant professional judgment, contextual nuance,
    or multi-stakeholder negotiation that AI cannot yet handle reliably.
    Examples: developing a novel strategic plan, mediating a labor dispute,
    diagnosing a rare medical condition, leading a difficult parent conference.

- 0.50 = AI and human share work roughly equally — partnership
    AI handles routine instances autonomously; human handles complex, ambiguous,
    or edge cases. The split reflects that the task has both routine and
    non-routine components.
    Examples: reviewing standard contracts (AI) vs. novel contract terms (human),
    handling routine customer escalations vs. complex complaints,
    coding standard features vs. debugging novel architecture issues.

- 0.75 = AI does most work, human spot-checks — AI-primary
    AI reliably performs this task for the large majority of instances. Human
    reviews a sample, handles rare exceptions, or provides final sign-off.
    The key distinction from 1.00: a human must still be in the loop because
    errors on some instances could cause meaningful harm, or because edge cases
    arise often enough (~10-20% of instances) to need human judgment.
    Examples: drafting legal briefs for attorney review, generating financial
    reports with accountant sign-off, triaging patient messages for nurse review.

- 1.00 = AI performs this task fully — autonomous
    AI produces output functionally equivalent to a competent human for typical
    instances. A human MAY audit a random sample, but is not required in the
    workflow. Errors are either rare enough or low-stakes enough that batch
    audit is sufficient. This is NOT perfection — it is the standard a
    competent human employee would meet.
    Examples: scheduling appointments, generating standard reports from
    structured data, filing/categorizing documents, data entry from forms,
    maintaining databases, compiling statistical summaries, routing
    correspondence, processing standard invoices, basic bookkeeping entries,
    transcribing recordings, translating standard documents.

## Scenario 1: MODERATE (aut_score_mod)
18-month horizon through Oct 2027. Steady continuation of current approaches,
no architectural breakthroughs. This represents what CURRENT systems (early 2026)
can already do or will clearly achieve with incremental scaling.

Capabilities:
- Context: ~1.5M token window, reliable retrieval to ~400K tokens
- Tool use: Improved multi-tool chaining for familiar APIs/protocols
- Agents: 4-6 hour autonomous work blocks. Reliable on ~5-8 step workflows,
  fragile beyond 10 steps
- Efficiency: 3x token cost reduction from March 2026 baseline
- Alignment: RLVR in verifiable domains (code, math, science, structured data).
  Professional judgment still relies on RLHF without outcome verification
- Reasoning: Reliable on ~3 levels of derived-premise dependency
- Speed: <400ms voice, ~1s text, 8-60s complex reasoning
- Browser/computer use: Improved but still unreliable on complex web workflows
- Reliability: Well-defined task sequences only. Limited error detection

Note: Current AI systems (early 2026) already perform many structured
information-processing tasks autonomously in production — scheduling,
data entry, report generation, document classification, and bookkeeping
are deployed at scale today. Score these based on actual capability, not
theoretical risk.

## Scenario 2: SIGNIFICANT (aut_score_sig)
18-month horizon through Oct 2027. Step-change improvement requiring
architectural or training breakthroughs.

Capabilities:
- Context: ~2-3M token window, reliable retrieval to ~1M tokens
- Tool use: Reliable multi-tool chaining across unfamiliar APIs
- Agents: 6-10 hour autonomous work blocks. Reliable on ~12-15 step workflows,
  20-step viable with light oversight
- Efficiency: 10x token cost reduction from March 2026 baseline
- Alignment: RLVR expands to semi-verifiable professional domains (financial
  models with backtestable outputs, legal research with citation verification,
  medical diagnosis against confirmed outcomes). Subjective judgment remains
  RLHF-dependent
- Reasoning: Reliable on ~4 levels of derived-premise dependency
- Speed: <250ms voice, ~0.5s text, 5-30s complex reasoning
- Browser/computer use: Reliable navigation across arbitrary web interfaces
- Multimodal: Strong vision, document, and diagram understanding
- Orchestration: Parallel agent coordination
- Reliability: Longer task sequences, can pivot between related tasks within a
  domain, improved error detection, more consistent outputs

## Confidence Flag
For each score, also provide a confidence flag:
- "high" = you are confident this is the right anchor point (clear-cut case)
- "low" = this task is ambiguous, could reasonably be scored one step
  higher or lower (borderline case)

## Critical Scoring Rules
1. Score each task INDEPENDENTLY — do not let one task's score influence others
2. A job with mostly automatable tasks can still have tasks that score 0.00
3. Score each scenario INDEPENDENTLY — do not anchor sig on mod. Evaluate each
   scenario's capabilities from scratch. The gap between mod and sig should
   vary by task: some tasks may score the same in both (already at ceiling
   or hard-gated), others may jump 2+ steps.
4. Consider what the task actually requires:
   - Physical presence / dexterity -> resists automation
   - Real-time human judgment in novel situations -> resists automation
   - Deep emotional rapport / trust relationship -> resists automation
   - Regulatory sign-off / legal liability -> resists automation
   - Data analysis / pattern matching -> scores higher
   - Document generation / summarization -> scores higher
   - Scheduling / coordination / retrieval -> scores higher
   - Record-keeping / filing / database maintenance -> scores higher
   - Standard calculations / form processing -> scores higher
5. The score captures BOTH technical capability AND economic viability
6. 0.00 means a hard gate (physical, legal, relational) — not just "difficult"
7. sig >= mod always (significant scenario is strictly more capable)
8. Do NOT use 0.75 as a default ceiling. Many information-processing tasks
   with well-defined inputs/outputs and low error stakes are genuinely 1.00
   under moderate assumptions. Ask: "Would a batch audit catch the rare error?"
   If yes, that is 1.00, not 0.75.

## Calibration Anchors
Use these reference points to calibrate your scores:

| Task Example | mod | sig | Rationale |
|---|---|---|---|
| Schedule patient appointments | 1.00 | 1.00 | Structured, rule-based, current systems already do this |
| Maintain personnel records and files | 1.00 | 1.00 | Database CRUD, no judgment needed |
| Compile statistical reports from data | 1.00 | 1.00 | Structured data → formatted output |
| Process standard insurance claims | 0.75 | 1.00 | Routine claims autonomous; complex ones need review in mod |
| Draft legal brief for attorney review | 0.50 | 0.75 | Requires legal reasoning; sig gets reliable citation verification |
| Develop strategic plan for organization | 0.25 | 0.25 | Novel strategy requires human judgment in both scenarios |
| Perform physical therapy on patients | 0.00 | 0.00 | Physical presence required — hard gate |
| Counsel patients about mental health | 0.00 | 0.00 | Deep therapeutic rapport — hard gate |

## Output Format
Return ONLY a JSON array with one object per task:
```json
[
  {{
    "task_id": "ON-111011-001",
    "aut_score_mod": 0.50,
    "confidence_mod": "high",
    "aut_score_sig": 0.75,
    "confidence_sig": "high"
  }}
]
```"""


def format_task_list(tasks):
    """Format tasks as a numbered list for the prompt."""
    lines = []
    for i, t in enumerate(tasks, 1):
        tid = t["task_id"]
        ttype = t["task_type"] or "n/a"
        imp = t["importance"] if t["importance"] is not None else "N/A"
        gwa = t["gwa"] or "N/A"
        time_pct = t["time_share_pct"] if t["time_share_pct"] is not None else "N/A"
        desc = t["task_description"]
        lines.append(
            f"{i}. task_id={tid}  type={ttype}  importance={imp}  "
            f"time_share={time_pct}%  gwa={gwa}\n   {desc}"
        )
    return "\n".join(lines)


def build_scoring_prompt(soc_code, job_title, employment_k, tasks):
    """Build the full scoring prompt for one SOC's tasks."""
    task_list = format_task_list(tasks)
    return SCORING_PROMPT.format(
        soc_code=soc_code,
        job_title=job_title,
        employment_K=employment_k or "N/A",
        task_count=len(tasks),
        task_list=task_list,
    )
