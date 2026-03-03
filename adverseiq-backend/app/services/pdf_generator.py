import logging
from datetime import datetime, timezone
from typing import Optional

from fpdf import FPDF

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
# Colour palette (R, G, B)
# ------------------------------------------------------------------ #
C_NAVY    = (30,  58,  95)
C_BLUE    = (37, 99, 235)
C_SLATE   = (71, 85, 105)
C_MUTED   = (148, 163, 184)
C_BORDER  = (226, 232, 240)
C_WHITE   = (255, 255, 255)
C_BLACK   = (15,  23,  42)

C_EMERGENT_BG  = (220,  38,  38)
C_EMERGENT_FG  = (255, 255, 255)
C_URGENT_BG    = (245, 158,  11)
C_URGENT_FG    = (28,  25,  23)
C_ROUTINE_BG   = (209, 250, 229)
C_ROUTINE_FG   = (6,   95,  70)

C_HIGH_BG  = (209, 250, 229)
C_HIGH_FG  = (6,   95,  70)
C_MED_BG   = (254, 243, 199)
C_MED_FG   = (146,  64,  14)
C_LOW_BG   = (254, 226, 226)
C_LOW_FG   = (153,  27,  27)

C_STEP_BG  = (237, 242, 254)
C_REC_BG   = (239, 246, 255)
C_REC_BD   = (191, 219, 254)
C_DISC_BG  = (250, 250, 250)

# ------------------------------------------------------------------ #
# Helper functions
# ------------------------------------------------------------------ #
def _strategy_label(s: str) -> str:
    return {"rapid": "Rapid Check", "mechanism": "Mechanism Trace",
            "hypothesis": "Mystery Solver"}.get(s, s.title())


def _urgency_label(u: str) -> str:
    return {"emergent": "EMERGENT - Immediate clinical evaluation required",
            "urgent":   "URGENT - Clinical attention required",
            "routine":  "ROUTINE - No immediate action required"}.get(u, u.title())


def _conf_colors(confidence: int):
    if confidence >= 70:
        return C_HIGH_BG, C_HIGH_FG
    if confidence >= 40:
        return C_MED_BG, C_MED_FG
    return C_LOW_BG, C_LOW_FG


def _urgency_colors(urgency: str):
    return {"emergent": (C_EMERGENT_BG, C_EMERGENT_FG),
            "urgent":   (C_URGENT_BG,   C_URGENT_FG),
            "routine":  (C_ROUTINE_BG,  C_ROUTINE_FG)}.get(urgency, (C_ROUTINE_BG, C_ROUTINE_FG))


def _patient_context_str(ctx: Optional[dict]) -> str:
    if not ctx:
        return ""
    parts = []
    if ctx.get("age"):
        parts.append(f"Age {ctx['age']}")
    if ctx.get("sex"):
        parts.append({"M": "Male", "F": "Female"}.get(ctx["sex"], ctx["sex"]))
    flags = []
    if ctx.get("renalImpairment"):
        flags.append("Renal impairment")
    if ctx.get("hepaticImpairment"):
        flags.append("Hepatic impairment")
    if ctx.get("pregnant"):
        flags.append("Pregnant")
    if flags:
        parts.append(", ".join(flags))
    return " / ".join(parts)


# ------------------------------------------------------------------ #
# Report class
# ------------------------------------------------------------------ #
class _Report(FPDF):
    """FPDF subclass with convenience drawing helpers."""

    PAGE_W   = 210
    MARGIN   = 18
    CONTENT_W = 210 - 2 * 18  # 174 mm

    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_margins(self.MARGIN, self.MARGIN, self.MARGIN)
        self.set_auto_page_break(auto=True, margin=self.MARGIN)
        self.add_page()

    # ── low-level helpers ────────────────────────────────────────── #

    def _set_rgb(self, rgb, target="draw"):
        r, g, b = rgb
        if target == "fill":
            self.set_fill_color(r, g, b)
        elif target == "text":
            self.set_text_color(r, g, b)
        else:
            self.set_draw_color(r, g, b)

    def _filled_rect(self, x, y, w, h, fill_rgb, border_rgb=None):
        self._set_rgb(fill_rgb, "fill")
        if border_rgb:
            self._set_rgb(border_rgb)
            style = "FD"
        else:
            style = "F"
        self.rect(x, y, w, h, style=style)

    def _section_title(self, text: str):
        self.ln(4)
        self.set_font("Helvetica", style="B", size=7)
        self._set_rgb(C_BLUE, "text")
        self.cell(self.CONTENT_W, 5, text.upper(), new_x="LMARGIN", new_y="NEXT")
        y = self.get_y()
        self._set_rgb(C_BLUE)
        self.line(self.MARGIN, y, self.MARGIN + self.CONTENT_W, y)
        self._set_rgb(C_BLACK, "text")
        self.ln(3)

    def _kv_row(self, key: str, value: str):
        self.set_font("Helvetica", style="B", size=9)
        self._set_rgb(C_SLATE, "text")
        self.cell(42, 6, key, new_x="RIGHT", new_y="TOP")
        self.set_font("Helvetica", size=9)
        self._set_rgb(C_BLACK, "text")
        self.multi_cell(self.CONTENT_W - 42, 6, value or "-")

    # ── section renderers ────────────────────────────────────────── #

    def render_header(self, timestamp: str, strategy_label: str, analysis_id: str):
        W = self.CONTENT_W
        M = self.MARGIN

        self._filled_rect(0, 0, self.PAGE_W, 1.5, C_BLUE)
        y = self.get_y()

        self.set_font("Helvetica", style="B", size=16)
        self._set_rgb(C_NAVY, "text")
        self.set_xy(M, y + 4)
        self.cell(W * 0.65, 8, "AdverseIQ Clinical Report", new_x="RIGHT", new_y="TOP")

        self.set_font("Helvetica", size=7.5)
        self._set_rgb(C_SLATE, "text")
        self.set_xy(M + W * 0.65, y + 4)
        self.multi_cell(W * 0.35, 4,
                        f"Generated: {timestamp}\nStrategy: {strategy_label}\nID: {analysis_id}",
                        align="R")

        self.set_xy(M, y + 13)
        self.set_font("Helvetica", size=8)
        self._set_rgb(C_MUTED, "text")
        self.cell(W, 5, "Multi-Hypothesis Drug Interaction Analysis", new_x="LMARGIN", new_y="NEXT")

        self.ln(1)
        y2 = self.get_y()
        self._set_rgb(C_BLUE)
        self.set_line_width(0.5)
        self.line(M, y2, M + W, y2)
        self.set_line_width(0.2)
        self.ln(4)
        self._set_rgb(C_BLACK, "text")

    def render_urgency_banner(self, urgency: str, urgency_reason: str):
        bg, fg = _urgency_colors(urgency)
        label = _urgency_label(urgency)
        W = self.CONTENT_W
        M = self.MARGIN

        h_main = 8
        h_reason = (max(6, len(urgency_reason) // 80 * 5 + 6)) if urgency_reason else 0
        total_h = h_main + h_reason + 6
        y = self.get_y()
        self._filled_rect(M, y, W, total_h, bg)

        self.set_xy(M + 4, y + 3)
        self.set_font("Helvetica", style="B", size=10)
        self._set_rgb(fg, "text")
        self.cell(W - 8, h_main, label, new_x="LMARGIN", new_y="NEXT")

        if urgency_reason:
            self.set_x(M + 4)
            self.set_font("Helvetica", size=8.5)
            self.multi_cell(W - 8, 5, urgency_reason)

        self.set_xy(M, y + total_h + 2)
        self._set_rgb(C_BLACK, "text")
        self.ln(2)

    def render_patient_summary(self, meds_str: str, symptoms_str: str, context_str: str):
        self._section_title("Patient Summary")
        self._kv_row("Medications", meds_str)
        self._kv_row("Symptoms", symptoms_str)
        if context_str:
            self._kv_row("Patient Context", context_str)

    def render_confidence(self, confidence: int, factors: list):
        self._section_title("Overall Confidence")
        bg, fg = _conf_colors(confidence)
        M = self.MARGIN
        W = self.CONTENT_W
        y = self.get_y()

        badge_w, badge_h = 22, 9
        self._filled_rect(M, y, badge_w, badge_h, bg)
        self.set_xy(M, y + 1)
        self.set_font("Helvetica", style="B", size=11)
        self._set_rgb(fg, "text")
        self.cell(badge_w, badge_h - 2, f"{confidence}%", align="C", new_x="RIGHT", new_y="TOP")

        factor_strs = []
        for f in factors:
            arrow = "+" if f.get("direction") == "increases" else "-"
            factor_strs.append(f"{arrow} {f.get('factor', '')}")

        self.set_font("Helvetica", size=8)
        self._set_rgb(C_SLATE, "text")
        self.set_xy(M + badge_w + 5, y + 2)
        self.multi_cell(W - badge_w - 5, 4.5, "  |  ".join(factor_strs))

        self.set_xy(M, max(self.get_y(), y + badge_h + 1))
        self._set_rgb(C_BLACK, "text")
        self.ln(2)

    def render_causal_steps(self, steps: list):
        if not steps:
            return
        self._section_title("Causal Chain")
        M = self.MARGIN
        W = self.CONTENT_W

        for step in steps:
            if self.get_y() > 260:
                self.add_page()

            y = self.get_y()
            self._filled_rect(M, y, 2, 18, C_BLUE)
            self._filled_rect(M + 2, y, W - 2, 18, C_STEP_BG)

            self.set_xy(M + 4, y + 1.5)
            self.set_font("Helvetica", style="B", size=8)
            self._set_rgb(C_BLUE, "text")
            source = str(step.get("source", "")).upper()
            self.cell(10, 5, f"Step {step.get('step', '?')}", new_x="RIGHT", new_y="TOP")
            self.set_font("Helvetica", style="B", size=7)
            self._set_rgb(C_SLATE, "text")
            self.cell(0, 5, f"[{source}]", new_x="LMARGIN", new_y="NEXT")

            self.set_x(M + 4)
            self.set_font("Helvetica", style="B", size=8.5)
            self._set_rgb(C_BLACK, "text")
            self.multi_cell(W - 8, 4.5, step.get("mechanism", ""))

            self.set_x(M + 4)
            self.set_font("Helvetica", size=8)
            self._set_rgb(C_SLATE, "text")
            finding = step.get("expected_finding", "")
            evidence = step.get("evidence", "")
            if finding:
                self.multi_cell(W - 8, 4, f"Finding: {finding}")
            if evidence:
                self.set_x(M + 4)
                self.set_font("Helvetica", style="I", size=7.5)
                self.multi_cell(W - 8, 4, evidence)

            self.ln(2)
            self._set_rgb(C_BLACK, "text")

    def render_hypotheses(self, hypotheses: list):
        if not hypotheses:
            return
        self._section_title("Hypotheses")
        M = self.MARGIN
        W = self.CONTENT_W

        status_colors = {
            "supported": C_ROUTINE_FG,
            "possible":  (180, 100, 10),
            "rejected":  C_MUTED,
        }

        for h in hypotheses[:5]:
            if self.get_y() > 250:
                self.add_page()

            y = self.get_y()
            status = h.get("status", "possible")
            accent = status_colors.get(status, C_BLUE)

            self._filled_rect(M, y, 3, 28, accent)
            self._set_rgb(C_BORDER)
            self.rect(M + 3, y, W - 3, 28, style="D")

            self.set_xy(M + 6, y + 2)
            self.set_font("Helvetica", style="B", size=9)
            self._set_rgb(C_NAVY, "text")
            conf = h.get("confidence", "")
            desc = str(h.get("description", ""))[:80]
            self.cell(W - 12, 5, f"{h.get('id','')}: {desc}  ({conf}%)",
                      new_x="LMARGIN", new_y="NEXT")

            self.set_x(M + 6)
            self.set_font("Helvetica", style="I", size=8)
            self._set_rgb(C_SLATE, "text")
            self.multi_cell(W - 12, 4, str(h.get("mechanism", ""))[:120])

            for e in h.get("supporting_evidence", [])[:3]:
                self.set_x(M + 10)
                self.set_font("Helvetica", size=7.5)
                self._set_rgb(C_SLATE, "text")
                self.multi_cell(W - 16, 4, f"+ {e}")

            self.set_xy(M, y + 29)
            self.ln(2)
            self._set_rgb(C_BLACK, "text")

    def render_recommendation(self, text: str):
        if not text:
            return
        self._section_title("Clinical Recommendation")
        M = self.MARGIN
        W = self.CONTENT_W
        y = self.get_y()
        lines = max(1, len(text) // 75 + 1)
        h = lines * 5.5 + 10
        self._filled_rect(M, y, W, h, C_REC_BG, C_REC_BD)
        self.set_xy(M + 5, y + 4)
        self.set_font("Helvetica", size=9.5)
        self._set_rgb(C_NAVY, "text")
        self.multi_cell(W - 10, 5.5, text)
        self.set_xy(M, y + h + 2)
        self._set_rgb(C_BLACK, "text")

    def render_disclaimer(self, text: str):
        if not text:
            return
        M = self.MARGIN
        W = self.CONTENT_W
        y = self.get_y()
        lines = max(1, len(text) // 85 + 1)
        h = lines * 4.5 + 8
        self._filled_rect(M, y, W, h, C_DISC_BG, C_BORDER)
        self.set_xy(M + 4, y + 3)
        self.set_font("Helvetica", style="I", size=7.5)
        self._set_rgb(C_MUTED, "text")
        self.multi_cell(W - 8, 4.5, text)
        self.set_xy(M, y + h + 2)
        self._set_rgb(C_BLACK, "text")

    def render_footer(self):
        self.set_y(-14)
        M = self.MARGIN
        W = self.CONTENT_W
        y = self.get_y()
        self._set_rgb(C_BORDER)
        self.line(M, y, M + W, y)
        self.set_xy(M, y + 2)
        self.set_font("Helvetica", size=7)
        self._set_rgb(C_MUTED, "text")
        self.cell(W / 2, 4, "AdverseIQ - Clinical Decision Support", new_x="RIGHT", new_y="TOP")
        self.cell(W / 2, 4, "Generated from K2 Think V2 structured reasoning", align="R",
                  new_x="LMARGIN", new_y="NEXT")


# ------------------------------------------------------------------ #
# Public interface
# ------------------------------------------------------------------ #
class PDFGenerator:
    def generate(self, result: dict, request: dict, analysis_id: str = "N/A") -> bytes:
        medications = request.get("medications", [])
        symptoms = request.get("symptoms", [])
        patient_context = request.get("patientContext")

        meds_str = ", ".join(
            m.get("displayName") or m.get("genericName") or "unknown"
            for m in medications
        )
        symptoms_str = ", ".join(
            f"{s['description']} ({s.get('severity', 'unspecified')})"
            for s in symptoms
        ) or "None reported"

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        strategy_label = _strategy_label(result.get("strategy", ""))
        short_id = str(analysis_id)[:8].upper()

        pdf = _Report()
        pdf.render_header(timestamp, strategy_label, short_id)
        pdf.render_urgency_banner(
            result.get("urgency", "routine"),
            result.get("urgency_reason", ""),
        )
        pdf.render_patient_summary(meds_str, symptoms_str, _patient_context_str(patient_context))
        pdf.render_confidence(
            result.get("overall_confidence", 0),
            result.get("confidence_factors", []),
        )
        pdf.render_hypotheses(result.get("hypotheses", []))
        pdf.render_causal_steps(result.get("causal_steps", []))
        pdf.render_recommendation(result.get("recommendation", ""))
        pdf.render_disclaimer(result.get("disclaimer", ""))
        pdf.render_footer()

        return bytes(pdf.output())


pdf_generator = PDFGenerator()
