# Task Automatability Scoring Methodology

## Purpose

This document defines the framework for scoring whether a **frontier AI model available in October 2027** can autonomously perform a given task. It is the single source of truth referenced by all scoring agents (Calibrator, Batch Scorer, Drift Auditor).

---

## 1. Scoring Rubric

You are scoring the **AUTONOMY FRACTION** of a task: what fraction of this task's value-add can a **FRONTIER AI MODEL IN OCTOBER 2027** deliver WITHOUT a human in the loop, at quality sufficient to meet the standard the employer requires?

Each scenario describes a specific frontier model with defined capabilities and defined limitations. You are asking: *"If an enterprise deployed this October 2027 model with best-practice engineering — proper prompting, RAG pipelines, tool integrations, agent scaffolding — could it perform this task end-to-end?"*

This is NOT "can today's AI assist with this?" — it is "can the described Oct 2027 frontier model PERFORM this task to the required quality threshold autonomously, reliably, at scale?"

### Scale

| Score | Meaning | Examples |
|-------|---------|----------|
| 0.00 | AI cannot meaningfully perform this task. Human does 100%. | Physical plumbing repair, live courtroom cross-examination, psychotherapy requiring genuine human relationship. |
| 0.25 | AI handles routine/structured subtasks, but a human must do the core judgment work. AI is an assistant, not a replacement. | AI drafts initial research summaries but analyst must interpret; AI pre-screens resumes but recruiter makes calls. |
| 0.50 | AI autonomously handles ~half of cases (routine instances), but complex/edge cases require human execution. | AI handles standard customer complaints end-to-end but escalates complex ones; AI writes routine code but human handles architecture. |
| 0.75 | AI performs this task in most cases. Human needed only for rare edge cases, novel situations, or final sign-off on high-stakes outputs. | AI generates and validates standard financial reports; AI handles full contract review for standard agreements. |
| 1.00 | AI fully performs this task autonomously with no human involvement, at or above human quality, across essentially all cases. | Automated data entry from structured forms; automated log monitoring and standard alert triage; automated translation of standard business documents. |

### Scoring Principles

1. **Score the TASK, not the job.** A single task within a complex job can be fully automatable.
2. **Score against the SCENARIO's specific frontier model.** Each scenario defines a concrete Oct 2027 model with explicit capabilities and explicit limitations. A task might be 0.25 under the Moderate model but 0.75 under the Significant model — that's expected. The gap between scenarios should be driven by specific capability differences (e.g., 1-day vs 7-day state management, structured vs dynamic tool use), not vibes.
3. **Reliability matters.** If AI can do it 90% of the time but fails catastrophically 10%, the score should reflect the need for human oversight (likely 0.50–0.75, not 1.0).
4. **Consider the FULL task lifecycle:** input gathering, execution, quality verification, exception handling, and delivery/communication of output.
5. **"Autonomous" means the AI handles the complete task** including knowing when it's done and whether the output is correct. Self-correction counts if it's reliable.
6. **Cost matters implicitly:** if AI can do it but at 10x the compute cost of a human hour, score lower — employers won't deploy it.

---

## 2. Scenario: Moderate Capability Gains (October 2027)

You are evaluating whether a FRONTIER AI MODEL available in October 2027 can autonomously perform a given task. This is not today's model. This is the best commercially available AI system 18 months from now, assuming on-pace improvements within the current research paradigm — no fundamental breakthroughs, just steady compounding of existing approaches.

### The frontier model in this scenario CAN:

- Leverage continued pre-training scaling + more efficient training
- Apply RLVR expanded into verifiable domains (math, chemistry, biology, etc.)
- Produce nearly human-indistinguishable multimodal output (text, image, audio, video) but WITHOUT native multimodal reasoning — it generates excellent multimodal content but cannot analytically reason over images, video, or audio inputs in the way it reasons over text
- Operate with 5x effective usable context vs. today (context window + in-context learning)
- Use improved RAG pipelines (better embeddings, hybrid retrieval, smarter chunking, re-ranking)
- Execute expanded structured tool use (API calls, database queries, defined integrations)
- Maintain coherent task state for up to 1 full workday (~8–10 hours)
- Operate at 20–35x token efficiency vs. today (dramatically cheaper inference)
- Checkpoint and resume agentic workflows
- Self-correct via re-prompting when it detects errors
- Use attention engineering (sparse attention, efficient KV caching) for better long-range coherence

### The frontier model in this scenario CANNOT:

- **Guarantee zero hallucination** — hallucination is largely mitigated for tasks grounded in structured data, explicit documents, and RLVR-covered domains (math, code, hard sciences) where the model self-verifies. But hallucination remains meaningful for novel synthesis across many sources, ungrounded numerical claims from memory, citations generated without retrieval, white-collar domains outside RLVR coverage (law, finance, consulting, strategy), long-chain reasoning (10+ steps) where errors compound, and niche edge cases where training data is thin
- Run agentic loops reliably beyond ~10 sequential steps without human checkpoints
- Maintain coherent state past 1 day — multi-day workflows still need human handoff
- Dynamically discover or adapt to new tools/APIs at runtime (tool use is pre-configured)
- Reliably navigate arbitrary browser/GUI interfaces
- Catch subtle, domain-specific errors through self-correction (it catches obvious mistakes, not nuanced ones)
- Orchestrate truly parallel agentic workflows at scale
- Handle very large information scopes (full codebases, massive legal discovery) without human orchestration of the retrieval strategy

### Scoring question (Moderate):

*"Could this specific frontier model, deployed with reasonable engineering (proper prompting, tool integration, RAG pipelines), perform this task end-to-end without a human?"*

---

## 3. Scenario: Significant Capability Gains (October 2027)

You are evaluating whether a FRONTIER AI MODEL available in October 2027 can autonomously perform a given task. This is a step-change improvement — still within reach of the current research paradigm, but representing the upper bound of what's plausible in 18 months. Think: multiple research bets pay off simultaneously.

### The frontier model in this scenario CAN:

- Leverage continued pre-training scaling + more efficient training
- Apply rich-context RLVR enabling post-training across a broad set of white-collar domains (law, finance, medicine, engineering, management)
- Produce nearly human-indistinguishable multimodal output (text, image, audio, video) WITH native multimodal reasoning and some iterative refinement — it can analytically reason over visual, audio, and video inputs, and improve its multimodal outputs through iteration, though not perfectly
- Operate with 10x effective usable context vs. today (context window + in-context learning)
- Use improved RAG pipelines (better embeddings, hybrid retrieval, smarter chunking, re-ranking)
- Dynamically discover, adapt to, and use new tools/APIs at runtime without pre-configuration
- Maintain coherent task state for up to 7 consecutive days
- Operate at 35–60x token efficiency vs. today (inference cost approaches negligible for most tasks)
- Orchestrate parallel agentic workflows and manage multi-agent coordination
- Enforce runtime constraints and validation across multi-step task chains
- Deploy robust, task-specific agent architectures (specialized agents for coding, research, analysis, etc.)
- Use attention engineering (more effective sparse attention, efficient KV caching)
- Reliably navigate standard browser interfaces and GUI applications

### The frontier model in this scenario CANNOT:

- **Guarantee zero hallucination** — hallucination surface is substantially smaller than Moderate. Rich-context RLVR in white-collar domains (law, finance, medicine, engineering) plus dynamic tool use for real-time citation verification plus agentic checkpointing for intermediate verification means standard professional tasks are largely mitigated. Hallucination remains meaningful for genuinely novel synthesis where no documented evidence exists to verify against, very long reasoning chains (20+ steps) with tightly coupled dependencies, niche edge cases at the frontier of any domain, and catastrophic-consequence contexts where even low hallucination rates are unacceptable (regulatory filings, clinical decisions for rare conditions)
- Maintain coherent state beyond ~7 days — month-long projects still require human oversight architecture
- Reliably handle truly novel problem structures where no training signal exists (it excels at learned patterns, not genuine first-principles invention)
- Reverse-engineer proprietary or undocumented systems (dynamic tool use works on documented interfaces)
- Perform physical-world tasks requiring real-time perception, dexterity, or embodied presence (surgery, plumbing, physical assembly)
- Match expert-level human judgment in adversarial, high-ambiguity contexts (complex litigation strategy, high-stakes negotiation with adaptive counterparties, novel geopolitical analysis)
- Navigate highly custom or legacy enterprise software with non-standard interfaces
- Generate genuinely novel creative or scientific breakthroughs (it is an exceptional synthesizer and pattern-matcher, not an originator of paradigm-shifting ideas)
- Operate in environments with no digital interface (field work, in-person relationship management, physical security)

### Scoring question (Significant):

*"Could this specific frontier model, deployed with best-practice engineering and purpose-built agent scaffolding, perform this task end-to-end without a human?"*

---

## 4. Universal Limitations (Bind in Both Scenarios)

No matter which scenario you are scoring under, the frontier model in Oct 2027 STILL has these fundamental limitations. These are not engineering gaps that better scaffolding can fix — they are architectural and research-frontier constraints that have not been solved.

1. **Self-correction is good but has a ceiling.** The model catches surface-level errors, logical inconsistencies, and formatting mistakes. In RLVR-trained domains, self-correction is strong. However, it fails on: errors of omission (doesn't know what it doesn't know), subtle framing errors (wrong analytical framework, wrong assumptions), errors requiring external validation, and compounding errors in long chains. *Binding question: "Can correctness be mechanically verified, or does it require human judgment?"*

2. **No self-recursive model improvement.** The model cannot improve its own weights, architecture, or training process at runtime. It does not get smarter by working on a problem.

3. **No continual learning from deployment.** The model does not learn from its interactions or build persistent expertise in a client's specific domain, codebase, organizational culture, or decision-making patterns over time without explicit fine-tuning.

4. **No mechanistic interpretability.** The model cannot explain *why* it reached a conclusion in terms of the actual computational process. It generates post-hoc rationalizations that are not reliable. For tasks requiring auditable decision trails (regulated industries, legal proceedings, medical diagnostics), this is binding.

5. **No accurate uncertainty calibration.** The model cannot reliably distinguish between things it knows with high confidence and things it's guessing at. For tasks where knowing what you don't know is essential (risk assessment, triage, escalation decisions), this limits autonomy.

6. **No robust causal reasoning over novel mechanisms.** The model excels at pattern-matching but cannot reliably construct new causal models for mechanisms it hasn't seen. Tasks requiring genuine first-principles reasoning about unprecedented situations still need human expertise.

7. **No genuine theory of mind in adversarial settings.** The model cannot reliably model what a sophisticated, adaptive counterparty is thinking in real time. Tasks involving strategic interaction with humans actively trying to outmaneuver the system remain limited.

8. **No robust performance under distribution shift.** When encountering truly novel situations — new regulatory regimes, unprecedented market conditions, first-of-their-kind failures — reliability degrades unpredictably. It cannot flag "this is outside my training distribution" with accuracy.

9. **No physical-world embodiment.** The model has no hands, no eyes, no physical presence. Any task requiring physical manipulation, real-time sensory perception, or embodied presence is scored 0.00 regardless of scenario.

**If a task's binding constraint is one of these universal limitations, the moderate and significant scores should be IDENTICAL or very close.**

---

## 5. Calibration Anchors

Use these as fixed reference points when scoring. Your scores for other tasks should be consistent with these benchmarks.

| Anchor Task | Moderate | Significant | Reasoning |
|-------------|----------|-------------|-----------|
| Schedule meetings and manage calendar | 0.75 | 1.00 | Structured tool use + 1-day state handles most scheduling. Fails on political dynamics, cross-org coordination without shared calendars. Significant: dynamic tool use + 7-day state + browser nav closes gaps. |
| Conduct quantitative financial modeling | 0.25 | 0.50 | Can generate templates and do formula work, but assumption selection and model architecture require human. Significant: domain RLVR improves financial reasoning, builds standard models autonomously, bespoke still human. |
| Write and edit marketing copy | 0.75 | 1.00 | Current models already strong. Needs human for brand voice calibration on new campaigns. Significant: domain post-training + dynamic tool use makes fully autonomous for standard copy. |
| Diagnose and troubleshoot IT infrastructure issues | 0.50 | 0.75 | Structured tool use handles known-pattern diagnosis. Breaks on novel failure modes, cross-system cascading, hardware. Significant: dynamic tool use + browser/GUI + 7-day state expands coverage dramatically. |
| Provide in-person patient care and physical examination | 0.00 | 0.00 | Requires physical presence, tactile assessment, real-time patient interaction. No change across scenarios. |
| Review and summarize legal documents for due diligence | 0.50 | 0.75 | 5x context + RAG handles standard review. Misses subtle cross-references, jurisdiction nuances. Significant: 10x context + domain RLVR + 7-day state enables multi-day workflows. Human for materiality judgment. |
| Process and reconcile accounts payable invoices | 0.75 | 1.00 | Structured tool use + RAG handles matching/coding for standard invoices. Edge cases need human. Significant: dynamic tool use + browser nav handles vendor portals, dispute workflows. |
| Develop original research hypotheses and experimental designs | 0.25 | 0.25 | Can survey literature and suggest incremental variations, but novelty requires human creativity. Capability gains have diminishing returns here — bottleneck is novelty, not information processing. |

---

## 6. Batch Scoring Rules

- Scores must be from {0.00, 0.25, 0.50, 0.75, 1.00}.
- `sig >= mod` always (more capability cannot reduce automation potential).
- If a task's binding constraint is a UNIVERSAL LIMITATION, mod and sig should be identical or very close.
- If uncertain between two levels, identify the binding constraint causing uncertainty and check how calibration anchors with similar constraints were scored. Match that pattern. Do not default to scoring higher or lower — score your best estimate. Accuracy matters more than conservatism.
- Check your scores against the calibration anchors for consistency before responding.
