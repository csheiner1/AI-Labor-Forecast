#!/usr/bin/env python3
"""
Generate comprehensive AI Labor Forecast Methodology PDF.
"""

from fpdf import FPDF
import os

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "AI_Labor_Forecast_Methodology.pdf")

# -- Color palette --
NAVY = (15, 30, 62)
SLATE = (55, 65, 81)
BODY = (38, 38, 42)
LIGHT_GRAY = (148, 155, 168)
ACCENT = (37, 99, 235)
ACCENT_LIGHT = (235, 240, 252)
TABLE_HEAD_BG = (30, 41, 69)
TABLE_ALT = (245, 247, 251)
TABLE_BORDER = (210, 215, 225)
WHITE = (255, 255, 255)
RULE_COLOR = (200, 207, 220)


class MethodologyPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=22)
        self.set_left_margin(22)
        self.set_right_margin(22)
        self._row_idx = 0

    def header(self):
        if self.page_no() <= 2:
            return
        self.set_font("Helvetica", "", 7.5)
        self.set_text_color(*LIGHT_GRAY)
        self.set_y(10)
        self.cell(0, 8, "AI Labor Forecast Methodology", align="L")
        self.cell(0, 8, f"{self.page_no()}", align="R")
        self.ln(4)
        self.set_draw_color(*RULE_COLOR)
        self.set_line_width(0.2)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(6)

    def footer(self):
        if self.page_no() <= 2:
            return
        self.set_y(-14)
        self.set_draw_color(*RULE_COLOR)
        self.set_line_width(0.2)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.set_y(-12)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*LIGHT_GRAY)
        self.cell(0, 8, "Confidential", align="C")

    # -- Title page --
    def title_page(self):
        self.add_page()
        # Top accent bar
        self.set_fill_color(*NAVY)
        self.rect(0, 0, self.w, 6, style="F")
        self.set_fill_color(*ACCENT)
        self.rect(0, 6, self.w, 1.5, style="F")
        self.ln(72)
        # Title
        self.set_font("Helvetica", "B", 32)
        self.set_text_color(*NAVY)
        self.cell(0, 14, "AI Labor Forecast", align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 32)
        self.cell(0, 14, "Methodology", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(12)
        # Accent line
        self.set_draw_color(*ACCENT)
        self.set_line_width(1.2)
        cx = self.w / 2
        self.line(cx - 35, self.get_y(), cx + 35, self.get_y())
        self.ln(14)
        # Subtitle
        self.set_font("Helvetica", "", 12)
        self.set_text_color(*SLATE)
        self.cell(0, 7, "18-Month AI Labor Displacement Forecast", align="C", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 7, "2x2 Scenario Framework", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(40)
        # Date
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*LIGHT_GRAY)
        self.cell(0, 7, "March 2026", align="C", new_x="LMARGIN", new_y="NEXT")
        # Bottom accent bar
        self.set_fill_color(*ACCENT)
        self.rect(0, self.h - 7.5, self.w, 1.5, style="F")
        self.set_fill_color(*NAVY)
        self.rect(0, self.h - 6, self.w, 6, style="F")

    # -- Section headers --
    def section_header(self, number, title):
        self.ln(8)
        self.set_font("Helvetica", "B", 15)
        self.set_text_color(*NAVY)
        self.cell(0, 10, f"{number}    {title}", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*ACCENT)
        self.set_line_width(0.7)
        self.line(self.l_margin, self.get_y(), self.l_margin + 45, self.get_y())
        self.ln(5)

    def subsection_header(self, title):
        self.ln(5)
        self.set_font("Helvetica", "B", 11.5)
        self.set_text_color(*SLATE)
        self.cell(0, 7, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def sub_subsection_header(self, title):
        self.ln(3)
        self.set_font("Helvetica", "BI", 10.5)
        self.set_text_color(80, 90, 115)
        self.cell(0, 6, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    # -- Body text --
    def body_text(self, text):
        self.set_font("Helvetica", "", 9.5)
        self.set_text_color(*BODY)
        self.multi_cell(0, 5.2, text)
        self.ln(2.5)

    # -- Equation block with left accent --
    def equation_block(self, equation):
        self.ln(2)
        y = self.get_y()
        w = self.w - self.l_margin - self.r_margin
        # Background
        self.set_fill_color(*ACCENT_LIGHT)
        self.rect(self.l_margin, y, w, 11, style="F")
        # Left accent bar
        self.set_fill_color(*ACCENT)
        self.rect(self.l_margin, y, 2.5, 11, style="F")
        # Text
        self.set_font("Courier", "B", 10.5)
        self.set_text_color(*NAVY)
        self.set_xy(self.l_margin + 8, y)
        self.cell(w - 8, 11, equation, new_x="LMARGIN", new_y="NEXT")
        self.ln(4)

    # -- Bullet --
    def bullet(self, text, bold_prefix=None, indent=8):
        x = self.l_margin + indent
        self.set_x(x)
        self.set_font("Helvetica", "", 9.5)
        self.set_text_color(*BODY)
        w = self.w - x - self.r_margin
        # Accent dot
        self.set_fill_color(*ACCENT)
        dot_y = self.get_y() + 2
        self.rect(x, dot_y, 1.5, 1.5, style="F")
        self.set_x(x + 5)
        if bold_prefix:
            self.set_font("Helvetica", "B", 9.5)
            prefix_w = self.get_string_width(bold_prefix + " ") + 1
            self.cell(prefix_w, 5.2, bold_prefix + " ")
            self.set_font("Helvetica", "", 9.5)
            remaining_w = w - 5 - prefix_w
            self.multi_cell(remaining_w, 5.2, text)
        else:
            self.multi_cell(w - 5, 5.2, text)
        self.ln(1.5)

    # -- Tables --
    def table_header(self, col_widths, headers):
        self._row_idx = 0
        self.set_font("Helvetica", "B", 8.5)
        self.set_fill_color(*TABLE_HEAD_BG)
        self.set_text_color(*WHITE)
        self.set_draw_color(*TABLE_HEAD_BG)
        for w, h in zip(col_widths, headers):
            self.cell(w, 8, f" {h}", border=1, fill=True, align="L")
        self.ln()

    def table_row(self, col_widths, values, aligns=None):
        self.set_font("Helvetica", "", 8.5)
        self.set_text_color(*BODY)
        if aligns is None:
            aligns = ["L"] * len(values)
        # Alternating row color
        if self._row_idx % 2 == 0:
            self.set_fill_color(*WHITE)
        else:
            self.set_fill_color(*TABLE_ALT)
        self._row_idx += 1
        # Calculate needed heights
        line_heights = []
        for w, v in zip(col_widths, values):
            n_lines = max(1, len(v) / max(1, (w / 2.0)))
            line_heights.append(max(7, int(n_lines * 4.8)))
        row_h = max(line_heights)
        if self.get_y() + row_h > self.h - 28:
            self.add_page()
        self.set_draw_color(*TABLE_BORDER)
        for w, v, a in zip(col_widths, values, aligns):
            x = self.get_x()
            y = self.get_y()
            fill = self._row_idx % 2 == 0
            self.rect(x, y, w, row_h, style="FD" if fill else "FD")
            self.set_xy(x + 2, y + 1.5)
            self.multi_cell(w - 4, 4.5, v, align=a)
            self.set_xy(x + w, y)
        self.ln(row_h)


def build_pdf():
    pdf = MethodologyPDF()

    # =========================================================================
    # TITLE PAGE
    # =========================================================================
    pdf.title_page()

    # =========================================================================
    # TABLE OF CONTENTS
    # =========================================================================
    pdf.add_page()
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 17)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 10, "Contents", new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(*ACCENT)
    pdf.set_line_width(0.7)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.l_margin + 30, pdf.get_y())
    pdf.ln(8)

    toc_items = [
        (1, "1", "Overview and Purpose"),
        (1, "2", "The Master Equation"),
        (1, "3", "Task-Level Automatability Scoring"),
        (2, "3.1", "Autonomy Fraction Scale"),
        (2, "3.2", "Tech Capability Scenarios"),
        (2, "3.3", "Scoring Pipeline Architecture"),
        (2, "3.4", "Universal Limitations"),
        (1, "4", "Job-Level Automatability Approximation"),
        (2, "4.1", "Sigmoid Transform"),
        (2, "4.2", "Job-Level Decomposition"),
        (2, "4.3", "x_depth Operationalization"),
        (2, "4.4", "Job-Level Scoring Pipeline"),
        (1, "5", "Industry-Level Variables"),
        (2, "5.1", "Displacement Ceiling (d_max = 0.18)"),
        (2, "5.2", "Elasticity Dampener (E)"),
        (2, "5.3", "Adoption Velocity (T)"),
        (2, "5.4", "Structural Resistance (R)"),
        (1, "6", "Scenario Mapping"),
        (1, "7", "Data Architecture"),
        (1, "8", "Frictions Scoring Structure"),
    ]

    for level, num, title in toc_items:
        if level == 1:
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(*NAVY)
            indent = 0
        else:
            pdf.set_font("Helvetica", "", 9.5)
            pdf.set_text_color(*SLATE)
            indent = 10
        pdf.set_x(pdf.l_margin + indent)
        pdf.cell(0, 7.5, f"{num}    {title}", new_x="LMARGIN", new_y="NEXT")

    # =========================================================================
    # SECTION 1: OVERVIEW
    # =========================================================================
    pdf.add_page()
    pdf.section_header("1", "Overview and Purpose")
    pdf.body_text(
        "This methodology forecasts AI labor displacement across industries and "
        "occupations over an 18-month horizon (through October 2027), using a 2x2 scenario "
        "framework."
    )
    pdf.body_text("The two axes of the scenario framework are:")
    pdf.bullet(
        "Moderate vs. Significant gains in AI capability",
        bold_prefix="Axis 1 -- Tech Capabilities:"
    )
    pdf.bullet(
        "Low vs. High institutional friction to adoption",
        bold_prefix="Axis 2 -- Non-Tech Frictions:"
    )
    pdf.body_text(
        "The methodology translates scenario assumptions about AI capability advancement and "
        "organizational friction into occupation-level and industry-level displacement numbers. "
        "The 2x2 produces four distinct scenarios, each yielding different displacement outputs "
        "per occupation."
    )

    pdf.subsection_header("Analytical Flow")
    pdf.body_text(
        "The methodology operates in three layers, each building on the one below:"
    )
    pdf.bullet(
        "Score each of 3,552 tasks for automatability under two tech capability scenarios "
        "(Moderate and Significant), producing 7,104 task-level scores.",
        bold_prefix="Layer 1 -- Task-Level Scoring:"
    )
    pdf.bullet(
        "Aggregate task-level scores upward to approximate a job-level automatability score "
        "for each of 462 occupations, using time-share weighting, workflow complexity, "
        "throughput scaling, and substitutability.",
        bold_prefix="Layer 2 -- Job-Level Approximation:"
    )
    pdf.bullet(
        "Apply industry-level variables -- displacement ceiling (d_max), elasticity dampener "
        "(E), adoption velocity (T), and structural resistance (R) -- to convert job-level "
        "automatability into realized displacement estimates across the 2x2 scenario grid.",
        bold_prefix="Layer 3 -- Industry-Level Application:"
    )

    pdf.body_text(
        "The model is best used as an ordinal ranking tool, not a cardinal predictor. It "
        "correctly ranks industries (call centers > software > paralegals > teachers > nurses) "
        "but absolute magnitudes should carry approximately +/-50% confidence intervals for "
        "mid-range industries."
    )

    # =========================================================================
    # SECTION 2: MASTER EQUATION
    # =========================================================================
    pdf.section_header("2", "The Master Equation")

    pdf.equation_block("d(t; i, s) = d_max * phi(a(i,s)) * E(i) * T(t; i, s) * R(i)")

    pdf.body_text(
        "Read the equation left to right as a chain of multiplicative filters. Each variable "
        "starts with 'how much displacement is possible' and progressively narrows it to 'how "
        "much actually happens.'"
    )

    pdf.bullet("d(t; i, s) = displacement rate for industry i in scenario s at time t")
    pdf.bullet("d_max = 0.18, absolute ceiling on displacement rate (historical precedent, constant across industries and scenarios)")
    pdf.bullet("phi(a(i,s)) = sigmoid-transformed automatability (derived from task-level scores)")
    pdf.bullet("E(i) = elasticity dampener (Jevons paradox / demand absorption)")
    pdf.bullet("T(t; i, s) = adoption velocity (logistic S-curve, industry-level)")
    pdf.bullet("R(i) = structural resistance dampener (regulatory/liability floors)")

    pdf.body_text(
        "Automatability (a) is scored at the task level under two tech capability scenarios. "
        "It has no relationship to frictions. The friction-related variables (T, R) and the "
        "demand-side variable (E) are applied at the industry level to convert automatability "
        "into realized displacement."
    )

    # =========================================================================
    # SECTION 3: TASK-LEVEL AUTOMATABILITY SCORING
    # =========================================================================
    pdf.add_page()
    pdf.section_header("3", "Task-Level Automatability Scoring")

    pdf.body_text(
        "The foundation of the model is task-level scoring. Each of 3,552 tasks is scored for "
        "its autonomy fraction under two tech capability scenarios, producing 7,104 scores "
        "(3,552 x 2). This scoring is purely about what AI can do technically and economically "
        "-- it is independent of adoption frictions, regulation, or institutional readiness."
    )

    # 3.1
    pdf.subsection_header("3.1  Autonomy Fraction Scale")
    pdf.body_text(
        "Each task is scored for what fraction of the task's value-add a frontier AI model "
        "in October 2027 can deliver without a human in the loop, at sufficient quality."
    )

    cw = [25, 141]
    pdf.table_header(cw, ["Score", "Meaning"])
    pdf.table_row(cw, ["0.00", "AI cannot meaningfully perform this task"], ["C", "L"])
    pdf.table_row(cw, ["0.25", "AI handles routine subtasks, human does core judgment"], ["C", "L"])
    pdf.table_row(cw, ["0.50", "AI handles approximately half of cases autonomously"], ["C", "L"])
    pdf.table_row(cw, ["0.75", "AI performs in most cases, human for rare edge cases"], ["C", "L"])
    pdf.table_row(cw, ["1.00", "AI fully performs autonomously at or above human quality"], ["C", "L"])

    pdf.ln(2)
    pdf.body_text(
        "The score captures both technical capability AND economic viability. A task where AI "
        "is technically capable but costs 3x the human does not score high. A task where AI is "
        "cheaper and better scores near 1.0."
    )

    # 3.2
    pdf.subsection_header("3.2  Tech Capability Scenarios")
    pdf.body_text("Each task is scored under two tech capability scenarios:")

    pdf.sub_subsection_header("Moderate Capability Gains")
    pdf.body_text(
        "Steady compounding of current approaches (baseline: March 2026). No architectural "
        "breakthroughs, but incremental improvement across all dimensions:"
    )
    pdf.bullet(
        "~1.5M token window, reliable retrieval to ~400K tokens, degrades beyond.",
        bold_prefix="Context:"
    )
    pdf.bullet(
        "Improved multi-tool chaining for familiar APIs/protocols.",
        bold_prefix="Tool use:"
    )
    pdf.bullet(
        "4-6 hour autonomous work blocks. 2-3 day project span with daily human "
        "check-ins. Reliable on ~5-8 step workflows, fragile beyond 10 steps.",
        bold_prefix="Agents:"
    )
    pdf.bullet(
        "3x token cost reduction.",
        bold_prefix="Efficiency:"
    )
    pdf.bullet(
        "Improved RLHF. RLVR advances in verifiable domains (code, math, science, "
        "structured data) via self-distillation -- more sample-efficient, more concise, "
        "better credit assignment. Professional judgment tasks still rely on RLHF "
        "without outcome verification.",
        bold_prefix="Alignment:"
    )
    pdf.bullet(
        "Reliable on ~3 levels of derived-premise dependency. Deep analysis still "
        "needs human verification.",
        bold_prefix="Reasoning:"
    )
    pdf.bullet(
        "<400ms voice, ~1s text, 8-60s complex reasoning.",
        bold_prefix="Speed:"
    )
    pdf.bullet(
        "Improved but still unreliable on complex web workflows.",
        bold_prefix="Browser/computer use:"
    )
    pdf.bullet(
        "Executes well-defined task sequences. Pivoting between disparate tasks requires "
        "explicit re-prompting and context setup. Limited error detection -- often doesn't "
        "know when it's wrong.",
        bold_prefix="Reliability & coordination:"
    )

    pdf.sub_subsection_header("Significant Capability Gains")
    pdf.body_text(
        "Step-change improvement requiring one or more architectural or training breakthroughs "
        "beyond current trajectory:"
    )
    pdf.bullet(
        "~2-3M token window, reliable retrieval to ~1M tokens, some degradation beyond.",
        bold_prefix="Context:"
    )
    pdf.bullet(
        "Reliable multi-tool chaining across unfamiliar APIs.",
        bold_prefix="Tool use:"
    )
    pdf.bullet(
        "6-10 hour autonomous work blocks. 7-10 day project span with daily check-ins. "
        "Reliable on ~12-15 step workflows, 20-step viable with light oversight.",
        bold_prefix="Agents:"
    )
    pdf.bullet(
        "10x token cost reduction.",
        bold_prefix="Efficiency:"
    )
    pdf.bullet(
        "RLVR expands to semi-verifiable professional domains -- tasks with partial "
        "correctness signals (financial models with backtestable outputs, legal research "
        "with citation verification, medical diagnosis against confirmed outcomes). "
        "Substantially more reliable in structured professional reasoning. Truly subjective "
        "judgment remains RLHF-dependent.",
        bold_prefix="Alignment:"
    )
    pdf.bullet(
        "Reliable on ~4 levels of derived-premise dependency. Novel/unprecedented "
        "reasoning still limited.",
        bold_prefix="Reasoning:"
    )
    pdf.bullet(
        "<250ms voice, ~0.5s text, 5-30s complex reasoning.",
        bold_prefix="Speed:"
    )
    pdf.bullet(
        "Reliable navigation across arbitrary web interfaces.",
        bold_prefix="Browser/computer use:"
    )
    pdf.bullet(
        "Strong vision, document, and diagram understanding.",
        bold_prefix="Multimodal:"
    )
    pdf.bullet(
        "Parallel agent coordination.",
        bold_prefix="Orchestration:"
    )
    pdf.bullet(
        "Executes longer task sequences with less rigid structure. Can pivot between "
        "related tasks within a domain without full context reset. Improved error "
        "detection -- flags low-confidence outputs more reliably, though still misses "
        "subtle errors. More consistent outputs across runs.",
        bold_prefix="Reliability & coordination:"
    )

    pdf.body_text(
        "Constraint: significant >= moderate always. More capability cannot reduce automation "
        "potential. This produces 7,104 scores total (3,552 tasks x 2 scenarios)."
    )

    # 3.3
    pdf.subsection_header("3.3  Scoring Pipeline Architecture")
    pdf.body_text("All agents use Claude Opus 4.6:")

    pdf.bullet(
        "Scores ~15 anchor tasks with full reasoning, using adaptive thinking. "
        "These anchors become the shared reference frame for all subsequent scoring.",
        bold_prefix="Agent 1 (Calibrator):"
    )
    pdf.bullet(
        "Processes tasks in batches of 25-30, returning structured JSON with anchors "
        "embedded in context. Uses temperature=0.2 for consistency, no adaptive thinking.",
        bold_prefix="Agent 2 (Batch Scorer):"
    )
    pdf.bullet(
        "Samples scored tasks across batches, flags inconsistencies vs. anchors, "
        "re-scores flagged tasks. Uses adaptive thinking.",
        bold_prefix="Agent 3 (Drift Auditor):"
    )

    # 3.4
    pdf.subsection_header("3.4  Universal Limitations (bind in both scenarios)")
    pdf.body_text(
        "If a task's binding constraint is a universal limitation, moderate and significant "
        "scores should be identical or very close."
    )
    pdf.bullet("Self-correction has a ceiling (catches surface errors, not subtle framing errors)")
    pdf.bullet("No self-recursive model improvement")
    pdf.bullet("No continual learning from deployment")
    pdf.bullet("No mechanistic interpretability")
    pdf.bullet("No accurate uncertainty calibration")
    pdf.bullet("No robust causal reasoning over novel mechanisms")
    pdf.bullet("No genuine theory of mind in adversarial settings")
    pdf.bullet("No robust performance under distribution shift")
    pdf.bullet("No physical-world embodiment (any physical task = 0.00)")

    # =========================================================================
    # SECTION 4: JOB-LEVEL AUTOMATABILITY APPROXIMATION
    # =========================================================================
    pdf.add_page()
    pdf.section_header("4", "Job-Level Automatability Approximation")

    pdf.body_text(
        "Task-level scores are aggregated upward to produce a job-level automatability score "
        "for each of 462 occupations. This approximation accounts for the fact that a job is "
        "more than the sum of its tasks -- workflow complexity, throughput dynamics, and human "
        "substitutability all mediate how task automation translates to job-level impact."
    )

    # 4.1
    pdf.subsection_header("4.1  Sigmoid Transform")
    pdf.equation_block("phi(a) = a^2 / (a^2 + (1-a)^2)")
    pdf.body_text(
        "The raw job-level automatability score is passed through a sigmoid transform. This "
        "crushes scores below ~0.5 toward zero (half-automatable jobs barely register as "
        "displacement candidates) while amplifying scores above ~0.7 toward 1.0 (once a job "
        "is clearly automatable, partial scores do not linger). This reflects the empirical "
        "reality that displacement is a threshold phenomenon, not a linear one."
    )

    # 4.2
    pdf.subsection_header("4.2  Job-Level Decomposition")
    pdf.equation_block("a(i,s) = x_depth * avg(x_scale, x_sub)")
    pdf.body_text(
        "x_depth is the hard gate: if AI cannot do the core tasks, a = 0 regardless of "
        "scaling potential or substitutability. x_scale and x_sub modulate the magnitude "
        "but neither can independently zero out an otherwise automatable job."
    )
    pdf.body_text(
        "x_depth is a continuous [0, 1] value derived from task-level scores (see 4.3). "
        "x_scale and x_sub are scored directly at the job level on a 5-point anchored "
        "scale {0.00, 0.25, 0.50, 0.75, 1.00}, matching the task-level autonomy fraction "
        "scale. This ensures all inputs to the composition are on a consistent [0, 1] scale "
        "with the midpoint at 0.50, and the sigmoid phi(a) is the sole source of "
        "non-linearity in the pipeline."
    )

    cw = [25, 38, 73, 30]
    pdf.table_header(cw, ["Component", "Name", "What It Captures", "Scale"])
    pdf.table_row(cw, [
        "x_depth", "Task Depth",
        "Can AI do the core tasks? Derived from task-level autonomy fraction scores. "
        "Operationalized as task_coverage * workflow_simplicity. This is the GATE -- "
        "if x_depth = 0, the job is not automatable.",
        "[0, 1]"
    ], ["C", "L", "L", "C"])
    pdf.table_row(cw, [
        "x_scale", "Throughput",
        "Does AI increase capacity/speed at scale? Some tasks automate well individually "
        "but bottleneck at volume. Modulates magnitude, does not gate.",
        "5-point"
    ], ["C", "L", "L", "C"])
    pdf.table_row(cw, [
        "x_sub", "Substitutability",
        "Is the human the product? In some roles the value is intrinsically human -- a "
        "therapist, a trial lawyer, a live performer. AI doing the task does "
        "not deliver the same product. Modulates magnitude, does not gate.",
        "5-point"
    ], ["C", "L", "L", "C"])

    pdf.body_text(
        "The gated structure reflects a key insight: task automation depth is a prerequisite "
        "for displacement, while scaling and substitutability determine how much displacement "
        "results. A job with high x_depth but low x_sub (human is the product) will see "
        "reduced displacement, but not zero -- the pressure still exists."
    )

    pdf.sub_subsection_header("x_sub Anchor Definitions")
    cw = [20, 50, 96]
    pdf.table_header(cw, ["Score", "Level", "Definition and Exemplars"])
    pdf.table_row(cw, [
        "0.00", "Human IS the product",
        "The value delivered is intrinsically human. AI performing the task does not produce "
        "an equivalent output. Exemplars: psychotherapist, elected official, trial lawyer "
        "(courtroom performance), clergy."
    ], ["C", "L", "L"])
    pdf.table_row(cw, [
        "0.25", "Strong human pref.",
        "Human presence is strongly valued but some substitution is emerging. Exemplars: "
        "surgeon (robotic surgery emerging), K-12 teacher (AI tutoring exists), personal "
        "fitness trainer, live performing artist."
    ], ["C", "L", "L"])
    pdf.table_row(cw, [
        "0.50", "Mixed / contested",
        "Human element matters for a meaningful fraction of the market, but substitution is "
        "already happening for another meaningful fraction. Exemplars: financial advisor "
        "(robo-advisors exist), real estate agent, management consultant, journalist."
    ], ["C", "L", "L"])
    pdf.table_row(cw, [
        "0.75", "Weak human pref.",
        "Most clients would accept AI if cheaper/faster. Human preference is residual and "
        "eroding. Exemplars: customer service rep, tax preparer, paralegal, insurance "
        "underwriter, technical writer."
    ], ["C", "L", "L"])
    pdf.table_row(cw, [
        "1.00", "Fully substitutable",
        "No human-is-the-product effect. Output is the product, not the human. Exemplars: "
        "warehouse worker, data entry keyer, assembly line worker, file clerk, meter reader."
    ], ["C", "L", "L"])

    pdf.sub_subsection_header("x_scale Anchor Definitions")
    cw = [20, 50, 96]
    pdf.table_header(cw, ["Score", "Level", "Definition and Exemplars"])
    pdf.table_row(cw, [
        "0.00", "No throughput gain",
        "AI provides no meaningful throughput advantage at production volume. Physical or "
        "situational constraints cap speed. Exemplars: artisanal crafts, emergency first "
        "responders, hands-on physical therapy."
    ], ["C", "L", "L"])
    pdf.table_row(cw, [
        "0.25", "Modest scaling",
        "AI helps but significant bottlenecks remain. Throughput gains are incremental, not "
        "transformative. Exemplars: construction supervision, surgical procedures, field "
        "inspection roles."
    ], ["C", "L", "L"])
    pdf.table_row(cw, [
        "0.50", "Moderate scaling",
        "AI doubles or triples throughput in some task areas but is constrained in others. "
        "Meaningful gains but not unlimited. Exemplars: financial analysis, software QA "
        "testing, marketing content creation."
    ], ["C", "L", "L"])
    pdf.table_row(cw, [
        "0.75", "Strong scaling",
        "AI handles large volumes with minimal human oversight in most task areas. "
        "Exemplars: legal document review, medical image screening, customer inquiry "
        "routing, insurance claims processing."
    ], ["C", "L", "L"])
    pdf.table_row(cw, [
        "1.00", "Near-unlimited",
        "AI processes at machine speed with no human bottleneck. Volume is limited only by "
        "compute. Exemplars: automated trading, data processing, email filtering, "
        "code linting, log analysis."
    ], ["C", "L", "L"])

    # 4.3
    pdf.subsection_header("4.3  x_depth Operationalization")
    pdf.equation_block("x_depth = task_coverage * workflow_simplicity")
    pdf.bullet(
        "Time-share-weighted mean of individual task autonomy fraction scores from the "
        "Tasks sheet. This is the direct aggregation of Layer 1 scores into the job level.",
        bold_prefix="task_coverage ="
    )
    pdf.bullet(
        "Discount factor for coordination complexity: task independence, branching logic, "
        "error propagation, and dynamic sequencing. A job with 10 individually automatable "
        "tasks that must be tightly sequenced scores lower than one with 10 independent "
        "automatable tasks. Scored on the same 5-point anchored scale:",
        bold_prefix="workflow_simplicity ="
    )

    pdf.ln(2)
    cw = [20, 50, 96]
    pdf.table_header(cw, ["Score", "Level", "Definition and Exemplars"])
    pdf.table_row(cw, [
        "1.00", "Independent / trivial",
        "Tasks are independent or follow a fixed linear pipeline with no branching. No human "
        "judgment at transitions. Exemplars: data entry pipeline, assembly line steps, "
        "document scan-OCR-file."
    ], ["C", "L", "L"])
    pdf.table_row(cw, [
        "0.75", "Mostly independent",
        "Most tasks execute independently, a few require coordination. Transition decisions "
        "are routine. Exemplars: standard accounting close, routine legal review, "
        "customer service ticket handling."
    ], ["C", "L", "L"])
    pdf.table_row(cw, [
        "0.50", "Moderate interdep.",
        "Meaningful dependencies and some branching. Intermediate outputs need evaluation "
        "before proceeding. Some iteration loops. Exemplars: software dev cycle, financial "
        "modeling, marketing campaign execution."
    ], ["C", "L", "L"])
    pdf.table_row(cw, [
        "0.25", "Tightly coupled",
        "Highly interdependent with frequent branching, backtracking, real-time adaptation. "
        "Failure at any stage requires replanning. Exemplars: surgical procedures, complex "
        "negotiations, crisis management."
    ], ["C", "L", "L"])
    pdf.table_row(cw, [
        "0.00", "Fully dynamic",
        "Sequence and nature of tasks determined in real-time by evolving conditions. No "
        "predetermined workflow exists. Exemplars: battlefield command, emergency room "
        "triage-to-treatment, live field investigation."
    ], ["C", "L", "L"])

    # 4.4
    pdf.add_page()
    pdf.subsection_header("4.4  Job-Level Scoring Pipeline")
    pdf.body_text(
        "x_scale, x_sub, and workflow_simplicity are scored for all 462 occupations using "
        "a dedicated AI pipeline. These variables are scenario-independent (they describe "
        "structural properties of the job, not AI capability), producing 462 x 3 = 1,386 "
        "scores total."
    )

    pdf.sub_subsection_header("Phase 0: Pre-Processing (Programmatic)")
    pdf.body_text(
        "For each occupation, assemble a structured profile: O*NET title and description, "
        "BLS employment count, education requirements, industry concentration, and task-level "
        "data summaries (mean/std/IQR of autonomy scores, task heterogeneity index, the 3 "
        "highest- and 3 lowest-autonomy tasks). Task-level features are curated per variable "
        "to avoid construct contamination -- e.g., the x_sub prompt receives interpersonal "
        "and judgment task proportions, while the x_scale prompt receives digital/physical "
        "task splits and output type."
    )

    pdf.sub_subsection_header("Phase 1: Calibration Agent (Claude Opus 4.6)")
    pdf.body_text(
        "Scores a curated set of 30 boundary-case occupations -- jobs where reasonable raters "
        "might disagree (e.g., Management Analyst, Radiologic Technologist, Real Estate Agent, "
        "Airline Pilot, Chef/Head Cook). Each occupation is scored individually with full "
        "chain-of-thought reasoning. Output is human-reviewed before proceeding. Temperature=0.1."
    )

    pdf.sub_subsection_header("Phase 2: Batch Scorer (Claude Opus 4.6)")
    pdf.body_text(
        "Processes all 462 occupations in batches of 25. All three variables are scored jointly "
        "per occupation for coherence, but the prompt enforces structured independent reasoning "
        "blocks to mitigate halo effects:"
    )
    pdf.bullet(
        "Model reasons ONLY about throughput and scaling properties, ignoring "
        "human-relationship and workflow dimensions.",
        bold_prefix="x_scale block:"
    )
    pdf.bullet(
        "Model reasons ONLY about whether the human is essential to the service, "
        "ignoring workflow complexity and scaling.",
        bold_prefix="x_sub block:"
    )
    pdf.bullet(
        "Model reasons ONLY about orchestration complexity of the task flow, "
        "ignoring scaling and substitutability.",
        bold_prefix="workflow block:"
    )
    pdf.bullet(
        "Model notes tensions between variable assessments without adjusting "
        "scores. Frequent tensions signal genuinely complex occupations.",
        bold_prefix="coherence note:"
    )
    pdf.body_text(
        "8-10 calibration exemplars from Phase 1 are embedded in each batch prompt as "
        "reference anchors. Temperature=0.2."
    )

    pdf.sub_subsection_header("Phase 3: Hybrid Auditor")
    pdf.body_text(
        "Two-component quality assurance. First, programmatic checks (Python): distributional "
        "analysis (no variable >35% concentrated at a single anchor), SOC-group coherence "
        "(within-group standard deviation checks), cross-variable correlation caps (x_scale "
        "vs. x_sub correlation should not exceed 0.80), and predefined consistency rules "
        "(e.g., low x_sub + high workflow_simplicity is flagged as rare). Second, a semantic "
        "auditor agent (Claude Opus 4.6) reviews flagged occupations (~10-15% of total) "
        "individually at temperature=0.1, either confirming or revising scores with reasoning."
    )

    pdf.sub_subsection_header("Phase 4: Reliability Verification")
    pdf.body_text(
        "A stratified random sample of 46 occupations (10%) is re-scored through Phase 2 "
        "with an independent run. Weighted quadratic kappa is computed for each variable. "
        "Acceptable thresholds: kappa >= 0.75, within-one-step agreement >= 90%, exact "
        "agreement >= 65%. If any variable fails, the pipeline enters a diagnostic loop: "
        "examine discrepant occupations, identify patterns, revise prompt guidance, and "
        "re-run full scoring."
    )

    # =========================================================================
    # SECTION 5: INDUSTRY-LEVEL VARIABLES
    # =========================================================================
    pdf.add_page()
    pdf.section_header("5", "Industry-Level Variables")

    pdf.body_text(
        "Once job-level automatability is established from task scores, the following variables "
        "are applied at the industry level to determine how much of that theoretical "
        "automatability translates into actual displacement within the 18-month window. "
        "These variables capture demand dynamics, adoption speed, and structural barriers -- "
        "none of which affect what AI can do (that is captured in a), but all of which affect "
        "whether and how fast displacement actually happens."
    )

    # 5.1 d_max
    pdf.subsection_header("5.1  d_max -- Displacement Ceiling")
    pdf.body_text(
        "The absolute maximum rate at which jobs can disappear, based on "
        "historical precedent. No industry has ever shed more than approximately 12% of "
        "employment per year, even during massive disruptions (typesetters, switchboard "
        "operators, etc.). Over the 18-month forecast window, that translates to 18%."
    )
    pdf.body_text(
        "d_max = 0.18 is a universal constant, applied identically across all industries "
        "and scenarios. Industry-specific adoption differences are already captured by T "
        "(adoption velocity) and R (structural resistance), so varying the ceiling would "
        "double-count those effects. Everything else in the equation multiplies against "
        "this ceiling to pull the number down."
    )

    # 5.2 E
    pdf.subsection_header("5.2  E(i) -- Elasticity Dampener")
    pdf.body_text(
        "Even if a task is fully automatable and economically justified, does displacement "
        "translate to fewer people? This is the Jevons paradox / demand absorption question."
    )
    pdf.bullet(
        "AI does it cheaper -> way more people file complex returns -> demand absorbs "
        "workers -> E ~ 0.25",
        bold_prefix="Tax preparation:"
    )
    pdf.bullet(
        "AI does it cheaper -> same number of invoices exist -> heads drop -> E ~ 1.0",
        bold_prefix="Back-office data entry:"
    )
    pdf.body_text(
        "This is an industry-level property about demand elasticity, not a technology question. "
        "It is scenario-stable -- the underlying demand structure of an industry does not "
        "change based on whether AI capabilities are moderate or significant over 18 months."
    )
    pdf.body_text("3-level scale: {0.25, 0.50, 1.00}")

    cw = [25, 30, 111]
    pdf.table_header(cw, ["Score", "Level", "Definition and Exemplars"])
    pdf.table_row(cw, [
        "0.25", "Demand-absorbing",
        "Strong Jevons effect. AI makes the service dramatically cheaper, demand explodes, "
        "and most displaced workers are reabsorbed into expanded volume. "
        "Exemplars: technology & software (cheaper dev -> more software built), "
        "healthcare diagnostics (cheaper screening -> more people screened), "
        "management consulting (cheaper analysis -> more companies buy it)."
    ], ["C", "L", "L"])
    pdf.table_row(cw, [
        "0.50", "Partially absorbing",
        "Mixed demand response. Some new demand emerges but not enough to fully offset "
        "displacement. Net effect is roughly half of theoretical displacement materializes. "
        "Exemplars: finance (some new products, not 1:1 absorption), legal services "
        "(cheaper review -> some new demand but market doesn't double), manufacturing, retail."
    ], ["C", "L", "L"])
    pdf.table_row(cw, [
        "1.00", "Demand-fixed",
        "No meaningful demand absorption. The volume of work is structurally determined and "
        "does not increase when costs drop. Displacement translates directly to headcount reduction. "
        "Exemplars: government administration (fixed number of citizens to serve), "
        "education (fixed number of students), advertising (budget-driven, not cost-driven)."
    ], ["C", "L", "L"])

    # 5.3 T
    pdf.subsection_header("5.3  T(t; i, s) -- Adoption Velocity")
    pdf.body_text(
        "A logistic S-curve capturing how fast AI deployment is rolling out within an industry. "
        "Even if something is automatable and economical, deployment takes time."
    )
    pdf.equation_block("T(t) = 1 / (1 + exp(-alpha * (t - t_0)))")
    pdf.bullet("t = time (1.5 years for the 18-month mark)")
    pdf.bullet("t_0 = inflection point (when adoption is at 50%)")
    pdf.bullet("alpha = steepness (convexity) of the transition curve")

    pdf.sub_subsection_header("alpha -- Convexity Exponent (fixed at ~3)")
    pdf.body_text(
        "alpha controls how sharply industries transition from low to high adoption once they "
        "pass the inflection point. Fixed at alpha ~ 3 for all industries. Squaring the "
        "transition slope punishes industries near the inflection and rewards those well past "
        "it, analogous to k ~ 2 in the sigmoid transform phi(a)."
    )

    cw = [40, 40, 86]
    pdf.table_header(cw, ["t_0 (inflection)", "T(18mo)", "Interpretation"])
    pdf.table_row(cw, [
        "0.5 years", "0.953", "Already past inflection; near-full adoption by 18mo"
    ], ["C", "C", "L"])
    pdf.table_row(cw, [
        "1.0 years", "0.818", "Adoption well underway, majority adopted"
    ], ["C", "C", "L"])
    pdf.table_row(cw, [
        "1.5 years", "0.500", "At inflection point at 18mo; half adopted"
    ], ["C", "C", "L"])
    pdf.table_row(cw, [
        "2.0 years", "0.182", "Still early; most adoption ahead"
    ], ["C", "C", "L"])
    pdf.table_row(cw, [
        "2.5 years", "0.047", "Pre-inflection; minimal adoption within window"
    ], ["C", "C", "L"])

    pdf.ln(2)

    pdf.sub_subsection_header("T Driver Sub-components (scored 1-4 each)")
    cw = [20, 50, 96]
    pdf.table_header(cw, ["Driver", "Name", "What It Captures"])
    pdf.table_row(cw, [
        "T1", "Institutional Inertia",
        "Organizational resistance to change: bureaucratic layers, change management overhead, retraining requirements, union negotiations"
    ], ["C", "L", "L"])
    pdf.table_row(cw, [
        "T2", "Systems Integration",
        "Technical complexity of deploying AI: legacy system compatibility, data pipeline readiness, vendor ecosystem maturity"
    ], ["C", "L", "L"])
    pdf.table_row(cw, [
        "T3", "Customer Acceptance",
        "End-user/customer willingness to interact with AI: trust requirements, preference for human contact, brand risk"
    ], ["C", "L", "L"])
    pdf.table_row(cw, [
        "T4", "Competitive Pressure",
        "Market dynamics pushing adoption: competitor moves, margin pressure, talent scarcity forcing automation (higher = faster adoption)"
    ], ["C", "L", "L"])

    pdf.sub_subsection_header("Derived Formulas")
    pdf.equation_block("D_base   = avg(T1, T2, T3)")
    pdf.equation_block("D_spread = max(T1, T2, T3) - D_base")
    pdf.equation_block("D        = D_base + 0.25 * D_spread")
    pdf.equation_block("t_0      = 1.5*D - 0.5*T4 - 0.5")
    pdf.equation_block("T(18mo)  = 1 / (1 + exp(-alpha * (1.5 - t_0)))")

    pdf.body_text(
        "T1-T3 act as drag factors (higher score = slower adoption), while T4 (Competitive "
        "Pressure) acts as an accelerant (higher score = faster adoption, pulling the inflection "
        "point earlier)."
    )

    pdf.body_text(
        "The bottleneck adjustment (D_spread) captures the reality that a single extreme drag "
        "-- e.g., an unresolved regulatory barrier -- can slow adoption beyond what the average "
        "would suggest. When all three drags are equal, D_spread = 0 and D collapses to the "
        "simple average. When one drag is much worse, D is pulled partially toward the "
        "bottleneck. The coefficient is set to 0.25 (rather than higher) because T is scored "
        "at the industry level and industries are heterogeneous -- a systems integration "
        "bottleneck at large hospital systems does not equally bind a solo-practice "
        "dermatologist. The partial adjustment acknowledges bottleneck effects without "
        "overstating them across diverse actors within a sector."
    )

    pdf.body_text(
        "T is scored separately for each scenario. In the high-tech scenarios, tools are more "
        "mature and integration is easier, so T2 may decrease; competitive pressure (T4) may "
        "increase as early movers demonstrate value. In high-friction scenarios, T1 increases "
        "as institutional resistance stiffens."
    )

    pdf.body_text(
        "Full separate T1-T4 per scenario with separate alpha, yielding independent "
        "T(18mo) values for each of the four 2x2 scenarios."
    )

    pdf.sub_subsection_header("Adoption-Gated Flag ('Powder Kegs')")
    pdf.body_text(
        "Industries are flagged as 'adoption-gated' when T < 0.2 AND the displacement "
        "ceiling (d_max * phi(a) * E) > 0.10. These are industries where the technical and "
        "economic conditions for significant displacement are already met, but adoption "
        "timing is the sole constraint. A single catalyst -- a competitor automating, a "
        "turnkey vendor launching, a regulatory green light -- could trigger rapid "
        "displacement. The flag ensures readers do not mistake low realized displacement "
        "for low risk."
    )

    # 5.4 R
    pdf.subsection_header("5.4  R(i) -- Structural Resistance")
    pdf.body_text(
        "Regulatory floors, liability regimes, and safety-critical trust requirements that "
        "cannot be overcome regardless of tech capability or organizational willingness. "
        "These are hard constraints that cap displacement independent of everything else "
        "in the equation."
    )

    pdf.sub_subsection_header("R Sub-components (scored 1-4 each)")
    cw = [30, 45, 91]
    pdf.table_header(cw, ["Component", "Name", "What It Captures"])
    pdf.table_row(cw, [
        "f1", "Liability",
        "Liability and insurability: who is liable when AI makes an error? Unresolved liability allocation blocks deployment."
    ], ["C", "L", "L"])
    pdf.table_row(cw, [
        "f2", "Statutory Mandate",
        "Statutory human mandate / regulatory floor: hard licensure requirements, legal mandates for human involvement."
    ], ["C", "L", "L"])
    pdf.table_row(cw, [
        "f3", "Labor & Gatekeeping",
        "Organized labor and professional gatekeeping: unions, professional associations, collective bargaining agreements, credentialing bodies that restrict who can perform the work."
    ], ["C", "L", "L"])

    pdf.sub_subsection_header("Formula")
    pdf.equation_block("F = f1 + f2 + f3")
    pdf.equation_block("R = 1 - 0.7 * (F - 3) / 9")
    pdf.body_text(
        "Range: F=3 -> R=1.00 (no barrier), F=12 -> R=0.30 (strong barrier). "
        "Most occupations cluster near R=1.0; R bites hard on approximately 50-80 of 462 jobs "
        "(healthcare providers, licensed professionals, safety-critical operators)."
    )

    pdf.body_text(
        "R is scenario-stable. Regulatory change over 18 months is minimal -- new legislation "
        "and liability frameworks take years to materialize."
    )

    # =========================================================================
    # SECTION 6: SCENARIO MAPPING
    # =========================================================================
    pdf.add_page()
    pdf.section_header("6", "Scenario Mapping")

    pdf.body_text("The 2x2 framework maps each variable to its controlling axis:")

    cw = [35, 52, 40, 39]
    pdf.table_header(cw, ["Variable", "Description", "Tech Axis", "Friction Axis"])
    pdf.table_row(cw, [
        "a(i,s)", "Task-level automatability",
        "Varies (mod/sig)", "Not applicable"
    ], ["L", "L", "C", "C"])
    pdf.table_row(cw, [
        "d_max", "Displacement ceiling (0.18)",
        "Constant", "Constant"
    ], ["L", "L", "C", "C"])
    pdf.table_row(cw, [
        "E(i)", "Elasticity dampener",
        "Fixed", "Fixed"
    ], ["L", "L", "C", "C"])
    pdf.table_row(cw, [
        "T(t;i,s)", "Adoption velocity",
        "Varies", "Varies"
    ], ["L", "L", "C", "C"])
    pdf.table_row(cw, [
        "R(i)", "Structural resistance",
        "Fixed", "Fixed"
    ], ["L", "L", "C", "C"])

    pdf.ln(4)
    pdf.body_text("The four scenarios are:")
    pdf.bullet(
        "a uses moderate scores; T scored with slower adoption (less mature tools, less "
        "competitive urgency) and lower institutional friction",
        bold_prefix="Scenario 1 -- Moderate Tech / Low Friction:"
    )
    pdf.bullet(
        "a uses moderate scores; T scored with slower adoption and higher institutional friction",
        bold_prefix="Scenario 2 -- Moderate Tech / High Friction:"
    )
    pdf.bullet(
        "a uses significant scores; T scored with faster adoption (mature tools, high "
        "competitive pressure) and lower institutional friction",
        bold_prefix="Scenario 3 -- Significant Tech / Low Friction:"
    )
    pdf.bullet(
        "a uses significant scores; T scored with faster adoption but higher institutional friction",
        bold_prefix="Scenario 4 -- Significant Tech / High Friction:"
    )

    pdf.ln(2)
    pdf.body_text(
        "Task-level automatability (a) is driven purely by the tech capability axis. "
        "Adoption velocity (T) is driven by both axes -- tech maturity affects integration "
        "ease and competitive pressure, while friction affects institutional inertia and "
        "customer acceptance. d_max, E, and R are scenario-stable."
    )

    # =========================================================================
    # SECTION 7: DATA ARCHITECTURE
    # =========================================================================
    pdf.section_header("7", "Data Architecture")

    pdf.body_text("Built on BLS National Industry-Occupation Employment Matrix (NIOEM):")

    cw = [30, 82, 54]
    pdf.table_header(cw, ["Level", "Data", "Rows"])
    pdf.table_row(cw, [
        "Industries", "70 NAICS codes rolled to 17 sectors", "17 summary rows"
    ], ["L", "L", "L"])
    pdf.table_row(cw, [
        "Jobs", "462 job titles with BLS employment, wages, projections", "462 rows"
    ], ["L", "L", "L"])
    pdf.table_row(cw, [
        "Tasks", "Tasks with Time_Share_Pct, Importance, Frequency, GWA", "3,552 rows"
    ], ["L", "L", "L"])
    pdf.table_row(cw, [
        "Staffing", "Top occupations by share within each sector", "Variable"
    ], ["L", "L", "L"])

    pdf.ln(3)
    pdf.body_text(
        "Automatability score columns exist at every level (Tasks, Jobs, Industries) "
        "with mod/sig variants (Auto_Score_Mod, Auto_Score_Sig). Task-level scores are the "
        "foundation; higher levels are derived by aggregation."
    )
    pdf.body_text(
        "19 GWA (Generalized Work Activity) categories classify all 3,552 tasks, providing a "
        "structured taxonomy for understanding the distribution of task types across occupations."
    )

    # =========================================================================
    # SECTION 8: FRICTIONS SCORING STRUCTURE
    # =========================================================================
    pdf.section_header("8", "Frictions Scoring Structure")

    pdf.body_text(
        "Industry-level variables (T, R, E) are scored in dedicated spreadsheet tabs, "
        "separate from task-level automatability scoring:"
    )

    pdf.subsection_header("Industry Frictions Tab (17 industries)")
    pdf.bullet("Reference columns: Sector ID, Industry Name, Employment (K), Avg Median Wage")
    pdf.bullet(
        "T sub-component columns: T1 (Institutional Inertia), T2 (Systems Integration), "
        "T3 (Customer Acceptance), T4 (Competitive Pressure) -- scored per scenario, "
        "with derived D_base, D_spread, D, t0, alpha, and T(18mo)"
    )
    pdf.bullet("R sub-component columns: f1 Liability, f2 Statutory Human Mandate, f3 Labor & Gatekeeping, F sum, R Value")
    pdf.bullet("E column: Elasticity dampener (dropdown from {0.25, 0.50, 1.00})")
    pdf.bullet("Notes column")

    # =========================================================================
    # OUTPUT
    # =========================================================================
    pdf.output(OUTPUT_PATH)
    print(f"PDF generated: {OUTPUT_PATH}")
    print(f"Pages: {pdf.page_no()}")


if __name__ == "__main__":
    build_pdf()
