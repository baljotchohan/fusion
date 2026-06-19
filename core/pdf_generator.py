# core/pdf_generator.py
"""
PDF Report Generator — compiles FUSION diligence markdown into a
publication-quality PDF. Each partner agent gets a dedicated page with
a full-width role banner, the scorecard is a structured 2-column grid,
and every page carries consistent header / footer chrome.
"""
import io
import os
import re
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether, HRFlowable, Image, Flowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Drawing, Rect, String as GStr, Line as GLine
from reportlab.graphics import renderPDF

# ── Brand palette ──────────────────────────────────────────────────────────────
C_SLATE_900  = colors.HexColor("#0f172a")
C_SLATE_800  = colors.HexColor("#1e293b")
C_SLATE_700  = colors.HexColor("#334155")
C_SLATE_600  = colors.HexColor("#475569")
C_SLATE_400  = colors.HexColor("#94a3b8")
C_SLATE_300  = colors.HexColor("#cbd5e1")
C_SLATE_200  = colors.HexColor("#e2e8f0")
C_SLATE_100  = colors.HexColor("#f1f5f9")
C_SLATE_50   = colors.HexColor("#f8fafc")
C_WHITE      = colors.HexColor("#ffffff")
C_GREEN_700  = colors.HexColor("#15803d")
C_GREEN_600  = colors.HexColor("#16a34a")
C_GREEN_50   = colors.HexColor("#f0fdf4")
C_GREEN_BAR  = colors.HexColor("#22c55e")
C_AMBER_600  = colors.HexColor("#d97706")
C_AMBER_50   = colors.HexColor("#fffbeb")
C_AMBER_BAR  = colors.HexColor("#f59e0b")
C_RED_700    = colors.HexColor("#b91c1c")
C_RED_600    = colors.HexColor("#dc2626")
C_RED_50     = colors.HexColor("#fef2f2")
C_RED_BAR    = colors.HexColor("#ef4444")
C_BLUE_700   = colors.HexColor("#1d4ed8")
C_BLUE_600   = colors.HexColor("#2563eb")
C_BLUE_50    = colors.HexColor("#eff6ff")
C_VIOLET_600 = colors.HexColor("#7c3aed")
C_VIOLET_50  = colors.HexColor("#f5f3ff")
C_CYAN_600   = colors.HexColor("#0891b2")
C_CYAN_50    = colors.HexColor("#ecfeff")

_LOGO_PATH  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fusionlogo.png")
_LOGO_CACHE: dict = {}

# Partner role metadata — maps lowercase partial name to display info
_PARTNER_META = {
    "managing": {
        "title": "MANAGING PARTNER",
        "role":  "Investment Committee Orchestrator  ·  Final Verdict Authority",
        "accent": C_SLATE_800,
        "bg":    C_SLATE_900,
        "fg":    C_WHITE,
    },
    "financial": {
        "title": "FINANCIAL PARTNER",
        "role":  "Financial Due Diligence  ·  Committee Weight: 30%",
        "accent": C_BLUE_700,
        "bg":    C_BLUE_600,
        "fg":    C_WHITE,
    },
    "legal": {
        "title": "LEGAL PARTNER",
        "role":  "Legal & Compliance Review  ·  Committee Weight: 25%",
        "accent": C_VIOLET_600,
        "bg":    C_VIOLET_600,
        "fg":    C_WHITE,
    },
    "technical": {
        "title": "TECHNICAL PARTNER",
        "role":  "Technical Architecture Review  ·  Committee Weight: 25%",
        "accent": C_CYAN_600,
        "bg":    C_CYAN_600,
        "fg":    C_WHITE,
    },
    "market": {
        "title": "MARKET PARTNER",
        "role":  "Market & Competitive Intelligence  ·  Committee Weight: 20%",
        "accent": C_GREEN_600,
        "bg":    C_GREEN_600,
        "fg":    C_WHITE,
    },
}

def _partner_meta(name: str) -> dict:
    key = name.lower()
    for k, v in _PARTNER_META.items():
        if k in key:
            return v
    return {"title": name.upper(), "role": "Partner Report", "accent": C_SLATE_700, "bg": C_SLATE_700, "fg": C_WHITE}


# ── Logo ───────────────────────────────────────────────────────────────────────
def _get_brand_logo():
    if "logo" in _LOGO_CACHE:
        return _LOGO_CACHE["logo"]
    result = None
    try:
        from PIL import Image as PILImage
        img = PILImage.open(_LOGO_PATH).convert("RGBA")
        px = img.load()
        w, h = img.size
        for y in range(h):
            for x in range(w):
                r, g, b, a = px[x, y]
                if r > 226 and g > 226 and b > 226:
                    px[x, y] = (r, g, b, 0)
        bbox = img.split()[3].getbbox()
        if bbox:
            img = img.crop(bbox)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        result = (buf.getvalue(), img.width / float(img.height))
    except Exception:
        result = None
    _LOGO_CACHE["logo"] = result
    return result


# ── Text cleaning ──────────────────────────────────────────────────────────────
def _strip_agent_internals(text: str) -> str:
    if not text:
        return text
    text = re.sub(r'thenvoi_send_message\s*\(.*?\)', '', text, flags=re.DOTALL)
    text = re.sub(r'Then I will report[^\n]*\n?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'If you need further assistance[^\n]*\n?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\$\[amount\]', '$15,000,000', text)
    text = re.sub(r'\$\[valuation\]', '$60,000,000 post', text)
    text = re.sub(r'\[today\]', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def clean_unicode_and_emojis(text: str) -> str:
    if not text:
        return ""
    text = _strip_agent_internals(text)
    text = re.sub(r'\[Grounding:\s*.*?\]', '', text, flags=re.DOTALL)
    text = text.replace("[POTENTIAL CONFLICT]", "Potential Conflict:")
    replacements = {
        "💼": "", "📊": "", "⚖️": "", "⚖": "", "🚨": "Alert: ",
        "📋": "", "🛡️": "", "🛡": "", "🎯": "", "🚦": "",
        "🏢": "", "💵": "", "🔧": "", "📈": "", "📝": "",
        "🤖": "", "🚀": "", "🤝": "", "⚠️": "Warning: ", "⚠": "Warning: ",
        "✨": "", "🔥": "", "─": "-", "—": "-", "–": "-",
        "“": '"', "”": '"', "‘": "'", "’": "'", "•": "*",
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    text = text.replace("Warning:  Potential Conflict:", "Potential Conflict:")
    cleaned = [c for c in text if ord(c) <= 255]
    text = "".join(cleaned)
    text = text.replace("&", "&amp;").replace("&amp;amp;", "&amp;")
    text = text.replace("<", "&lt;").replace(">", "&gt;")
    for tag in ["b", "i", "u", "strong", "em"]:
        text = text.replace(f"&lt;{tag}&gt;", f"<{tag}>")
        text = text.replace(f"&lt;/{tag}&gt;", f"</{tag}>")
    text = text.replace("&lt;br&gt;", "<br/>").replace("&lt;br/&gt;", "<br/>")
    return text.strip()


def _fmt(text: str) -> str:
    text = clean_unicode_and_emojis(text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    return text


# ── Verdict / risk helpers ─────────────────────────────────────────────────────
def _verdict_colors(verdict: str):
    v = verdict.upper().strip()
    if v == "INVEST":
        return C_GREEN_700, C_GREEN_50, C_GREEN_600
    if v == "CONDITIONAL":
        return C_AMBER_600, C_AMBER_50, C_AMBER_BAR
    return C_RED_700, C_RED_50, C_RED_600


def _risk_bar_color(score: float) -> colors.Color:
    if score <= 4:
        return C_GREEN_BAR
    if score <= 6:
        return C_AMBER_BAR
    return C_RED_BAR


def _risk_label(score: float) -> str:
    if score <= 4:
        return "LOW"
    if score <= 6:
        return "MEDIUM"
    return "HIGH"


def _severity_color(severity: int) -> colors.Color:
    if severity >= 8:
        return C_RED_600
    if severity >= 5:
        return C_AMBER_600
    return C_GREEN_600


# ── Risk bar chart Drawing ─────────────────────────────────────────────────────
def _risk_bar_chart(fin: float, leg: float, tech: float, mkt: float, weighted: float) -> Drawing:
    domains = [
        ("Financial Risk", fin, "30%"),
        ("Legal Risk",     leg, "25%"),
        ("Technical Risk", tech, "25%"),
        ("Market Risk",    mkt, "20%"),
    ]
    LABEL_W   = 110
    BAR_MAX_W = 300
    SCORE_W   = 90
    ROW_H     = 28
    PAD       = 8
    TOTAL_W   = LABEL_W + BAR_MAX_W + SCORE_W + 24
    TOTAL_H   = len(domains) * ROW_H + PAD * 2 + ROW_H + 10

    d = Drawing(TOTAL_W, TOTAL_H)

    # Column headers
    d.add(GStr(LABEL_W - 6, TOTAL_H - PAD - 8, "DOMAIN",
               fontName="Helvetica-Bold", fontSize=7,
               fillColor=C_SLATE_600, textAnchor="end"))
    d.add(GStr(LABEL_W + BAR_MAX_W / 2, TOTAL_H - PAD - 8, "RISK LEVEL (0–10)",
               fontName="Helvetica-Bold", fontSize=7,
               fillColor=C_SLATE_600, textAnchor="middle"))
    d.add(GStr(LABEL_W + BAR_MAX_W + 10, TOTAL_H - PAD - 8, "SCORE  (WEIGHT)",
               fontName="Helvetica-Bold", fontSize=7,
               fillColor=C_SLATE_600, textAnchor="start"))

    # Tick lines at 2, 4, 6, 8
    for tick in [2, 4, 6, 8, 10]:
        tx = LABEL_W + (tick / 10.0) * BAR_MAX_W
        d.add(GLine(tx, PAD, tx, TOTAL_H - PAD - 14,
                    strokeColor=C_SLATE_200, strokeWidth=0.5))

    for i, (name, score, weight) in enumerate(domains):
        y = TOTAL_H - PAD - 16 - (i + 1) * ROW_H
        bar_w = (score / 10.0) * BAR_MAX_W
        bar_h = 16

        d.add(GStr(LABEL_W - 8, y + 5, name,
                   fontName="Helvetica-Bold", fontSize=8,
                   fillColor=C_SLATE_700, textAnchor="end"))

        # Track
        d.add(Rect(LABEL_W, y, BAR_MAX_W, bar_h,
                   fillColor=C_SLATE_100, strokeColor=C_SLATE_300, strokeWidth=0.5,
                   rx=2, ry=2))
        # Fill
        if bar_w > 0:
            d.add(Rect(LABEL_W, y, bar_w, bar_h,
                       fillColor=_risk_bar_color(score), strokeWidth=0, rx=2, ry=2))

        d.add(GStr(LABEL_W + BAR_MAX_W + 10, y + 5,
                   f"{score:.1f}/10  ({weight})",
                   fontName="Helvetica-Bold", fontSize=8.5,
                   fillColor=C_SLATE_900))

    # Weighted total row
    if weighted is not None:
        y = PAD
        d.add(GLine(0, y + ROW_H - 2, TOTAL_W, y + ROW_H - 2,
                    strokeColor=C_SLATE_300, strokeWidth=0.75))
        d.add(GStr(LABEL_W - 8, y + 5, "WEIGHTED TOTAL",
                   fontName="Helvetica-Bold", fontSize=8,
                   fillColor=C_SLATE_900, textAnchor="end"))
        bar_w = (weighted / 10.0) * BAR_MAX_W
        d.add(Rect(LABEL_W, y, BAR_MAX_W, 16,
                   fillColor=C_SLATE_100, strokeColor=C_SLATE_300, strokeWidth=0.5,
                   rx=2, ry=2))
        if bar_w > 0:
            d.add(Rect(LABEL_W, y, bar_w, 16,
                       fillColor=_risk_bar_color(weighted), strokeWidth=0, rx=2, ry=2))
        d.add(GStr(LABEL_W + BAR_MAX_W + 10, y + 5,
                   f"{weighted:.2f}/10",
                   fontName="Helvetica-Bold", fontSize=9.5,
                   fillColor=C_SLATE_900))

    return d


class _DrawingFlowable(Flowable):
    def __init__(self, drawing: Drawing):
        super().__init__()
        self.drawing = drawing
        self.width  = drawing.width
        self.height = drawing.height

    def draw(self):
        renderPDF.draw(self.drawing, self.canv, 0, 0)


# ── Running header / footer ────────────────────────────────────────────────────
class BrandedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pages = []

    def showPage(self):
        self.pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self.pages)
        for page in self.pages:
            self.__dict__.update(page)
            self._draw_chrome(total)
            super().showPage()
        super().save()

    def _draw_chrome(self, total_pages: int):
        self.saveState()
        if self._pageNumber == 1:
            self.restoreState()
            return

        W = 612
        MARGIN = 54

        # ── Header ────────────────────────────────────────────────────────────
        self.setStrokeColor(C_SLATE_300)
        self.setLineWidth(0.5)
        self.line(MARGIN, 748, W - MARGIN, 748)

        text_x = MARGIN
        logo = _get_brand_logo()
        if logo:
            png_bytes, aspect = logo
            lh = 11
            lw = lh * aspect
            try:
                self.drawImage(ImageReader(io.BytesIO(png_bytes)),
                               MARGIN, 753, width=lw, height=lh, mask="auto")
                text_x = MARGIN + lw + 8
            except Exception:
                pass

        self.setFont("Helvetica-Bold", 7)
        self.setFillColor(C_SLATE_600)
        self.drawString(text_x, 756, "FUSION  ·  DUE DILIGENCE AUDIT REPORT")
        self.drawRightString(W - MARGIN, 756, "CONFIDENTIAL")

        # ── Footer ────────────────────────────────────────────────────────────
        self.line(MARGIN, 56, W - MARGIN, 56)
        self.setFont("Helvetica", 7)
        self.setFillColor(C_SLATE_600)
        self.drawString(MARGIN, 44, "FUSION Investment Committee  ·  AI-Powered Venture Capital Due Diligence")
        self.drawRightString(W - MARGIN, 44, f"Page {self._pageNumber} of {total_pages}")
        self.restoreState()


# ── Partner page banner ────────────────────────────────────────────────────────
def _partner_page_header(meta: dict, company: str, sev: int,
                         body_style: ParagraphStyle) -> list:
    """Full-width colored banner that opens every partner's dedicated page."""
    accent = meta["bg"]
    fg     = meta["fg"]

    sev_label = "HIGH SEVERITY" if sev >= 8 else ("MEDIUM SEVERITY" if sev >= 5 else "LOW SEVERITY")
    sev_color = _severity_color(sev)

    title_st = ParagraphStyle("PBT", fontName="Helvetica-Bold", fontSize=18, leading=22,
                               textColor=colors.HexColor("#ffffff"), spaceBefore=0, spaceAfter=0)
    role_st  = ParagraphStyle("PBR", fontName="Helvetica",       fontSize=9,  leading=13,
                               textColor=colors.HexColor("#e2e8f0"), spaceBefore=2, spaceAfter=0)
    co_st    = ParagraphStyle("PBC", fontName="Helvetica-Oblique", fontSize=8, leading=11,
                               textColor=colors.HexColor("#cbd5e1"), spaceBefore=4, spaceAfter=0)

    banner = Table(
        [[Paragraph(meta["title"], title_st)],
         [Paragraph(meta["role"],  role_st)],
         [Paragraph(f"Company Under Review: {company}", co_st)]],
        colWidths=[504]
    )
    banner.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), accent),
        ("TOPPADDING",    (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (0, 0), 4),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 10),
        ("LEFTPADDING",   (0, 0), (-1, -1), 18),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 18),
    ]))

    sev_st = ParagraphStyle("SB", fontName="Helvetica-Bold", fontSize=8, leading=10,
                             textColor=sev_color)
    meta_st = ParagraphStyle("SM", fontName="Helvetica", fontSize=8, leading=12,
                              textColor=C_SLATE_700)
    sev_table = Table(
        [[Paragraph(f"SEVERITY ASSESSMENT: {sev_label}  ·  {sev}/10", sev_st),
          Paragraph("This page contains the partner's independent due diligence findings.", meta_st)]],
        colWidths=[252, 252]
    )
    sev_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), C_SLATE_50),
        ("LINEBELOW",     (0, 0), (-1, -1), 0.5, C_SLATE_200),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 14),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 14),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))

    return [banner, sev_table, Spacer(1, 14)]


# ── Scorecard grid (2 × 2 domain cards + weighted total) ──────────────────────
def _scorecard_grid(fin: float, leg: float, tech: float, mkt: float,
                    weighted: float | None, verdict_color: colors.Color,
                    verdict_bg: colors.Color, body_style: ParagraphStyle) -> list:
    """Structured 2-column domain cards + weighted total banner."""
    domains = [
        ("Financial Risk", fin,  "30%", C_BLUE_600,   C_BLUE_50),
        ("Legal Risk",     leg,  "25%", C_VIOLET_600, C_VIOLET_50),
        ("Technical Risk", tech, "25%", C_CYAN_600,   C_CYAN_50),
        ("Market Risk",    mkt,  "20%", C_GREEN_600,  C_GREEN_50),
    ]

    def _cell(name, score, weight, accent, bg):
        bar_color = _risk_bar_color(score)
        risk_txt  = _risk_label(score)

        name_st  = ParagraphStyle("DN", fontName="Helvetica-Bold", fontSize=7.5, leading=10,
                                   textColor=accent, spaceBefore=0, spaceAfter=2)
        score_st = ParagraphStyle("DS", fontName="Helvetica-Bold", fontSize=20, leading=24,
                                   textColor=C_SLATE_900, spaceBefore=0, spaceAfter=0)
        risk_st  = ParagraphStyle("DR", fontName="Helvetica-Bold", fontSize=7, leading=9,
                                   textColor=bar_color, spaceBefore=2, spaceAfter=2)
        wt_st    = ParagraphStyle("DW", fontName="Helvetica", fontSize=7.5, leading=10,
                                   textColor=C_SLATE_600)

        cell_content = Table(
            [[Paragraph(name.upper(), name_st)],
             [Paragraph(f"{score:.1f}/10", score_st)],
             [Paragraph(f"RISK: {risk_txt}", risk_st)],
             [Paragraph(f"Committee weight: {weight}", wt_st)]],
            colWidths=[228]
        )
        cell_content.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), bg),
            ("TOPPADDING",    (0, 0), (-1, -1), 12),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING",   (0, 0), (-1, -1), 14),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 14),
            ("LINEBEFORE",    (0, 0), (-1, -1), 3, accent),
        ]))
        return cell_content

    cells = [_cell(n, s, w, a, b) for n, s, w, a, b in domains]

    grid = Table(
        [[cells[0], cells[1]],
         [cells[2], cells[3]]],
        colWidths=[252, 252],
        rowHeights=[None, None]
    )
    grid.setStyle(TableStyle([
        ("GRID",           (0, 0), (-1, -1), 0.5, C_SLATE_200),
        ("TOPPADDING",     (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 0),
        ("LEFTPADDING",    (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",   (0, 0), (-1, -1), 0),
    ]))

    elements = [grid, Spacer(1, 8)]

    # Weighted total banner
    if weighted is not None:
        wt_label_st = ParagraphStyle("WL", fontName="Helvetica-Bold", fontSize=9,
                                      leading=12, textColor=C_SLATE_50)
        wt_score_st = ParagraphStyle("WS", fontName="Helvetica-Bold", fontSize=22,
                                      leading=26, textColor=verdict_color, alignment=2)
        wt_note_st  = ParagraphStyle("WN", fontName="Helvetica", fontSize=8,
                                      leading=11, textColor=C_SLATE_400)

        wt_table = Table(
            [[Paragraph("WEIGHTED RISK SCORE", wt_label_st),
              Paragraph(f"{weighted:.2f} / 10", wt_score_st)],
             [Paragraph("Financial 30%  ·  Legal 25%  ·  Technical 25%  ·  Market 20%", wt_note_st),
              Paragraph("", wt_note_st)]],
            colWidths=[340, 164]
        )
        wt_table.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), C_SLATE_800),
            ("TOPPADDING",    (0, 0), (-1, -1), 12),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ("LEFTPADDING",   (0, 0), (-1, -1), 18),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 18),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("SPAN",          (1, 0), (1, 1)),
        ]))
        elements.append(wt_table)

    return elements


# ── Partner findings block ─────────────────────────────────────────────────────
def _partner_findings(findings: list, body_style: ParagraphStyle,
                      bullet_style: ParagraphStyle) -> list:
    elements = []
    for kind, text in findings:
        if kind == "timestamp":
            ts_st = ParagraphStyle("TS", fontName="Helvetica-Oblique", fontSize=7.5,
                                    leading=10, textColor=C_SLATE_400, spaceAfter=8)
            elements.append(Paragraph(text, ts_st))
        elif kind == "bullet":
            elements.append(Paragraph(f"&bull;  {text}", bullet_style))
        elif kind == "subhead":
            sh_st = ParagraphStyle("SH", fontName="Helvetica-Bold", fontSize=10,
                                    leading=13, textColor=C_SLATE_900,
                                    spaceBefore=10, spaceAfter=4, keepWithNext=True)
            elements.append(Paragraph(f"<b>{text}</b>", sh_st))
        else:
            if text.strip():
                elements.append(Paragraph(text, body_style))
    return elements


# ── Main compiler ──────────────────────────────────────────────────────────────
def compile_pdf_report(report_md: str, company_name: str) -> bytes:
    """Parse FUSION diligence markdown and compile a structured PDF.

    Structure:
      Page 1  — Cover (company, verdict badge, metadata)
      Page 2  — Executive Verdict Summary + Investment Memo
      Page 3  — Risk Analysis Scorecard (2×2 grid + bar chart)
      Page 4+ — One dedicated page per partner agent
    """
    report_md = _strip_agent_internals(report_md)
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        leftMargin=54, rightMargin=54, topMargin=72, bottomMargin=72,
    )

    SS = getSampleStyleSheet()

    def _style(name, **kw):
        return ParagraphStyle(name, parent=SS["Normal"], **kw)

    cover_title = _style("CvT",  fontName="Helvetica-Bold", fontSize=28, leading=34,
                          textColor=C_SLATE_900, spaceAfter=8)
    cover_sub   = _style("CvS",  fontName="Helvetica-Bold", fontSize=12, leading=16,
                          textColor=C_SLATE_700, spaceAfter=32)
    h1          = _style("H1",   fontName="Helvetica-Bold", fontSize=13, leading=17,
                          textColor=C_SLATE_900, spaceBefore=20, spaceAfter=6, keepWithNext=True)
    h2          = _style("H2",   fontName="Helvetica-Bold", fontSize=10, leading=14,
                          textColor=C_SLATE_700, spaceBefore=10, spaceAfter=4, keepWithNext=True)
    body        = _style("Body", fontName="Helvetica",      fontSize=9,  leading=14,
                          textColor=C_SLATE_900, spaceAfter=5)
    bullet      = _style("Bull", fontName="Helvetica",      fontSize=9,  leading=14,
                          textColor=C_SLATE_900, spaceAfter=4,
                          leftIndent=16, firstLineIndent=-12)
    meta_lbl    = _style("ML",   fontName="Helvetica-Bold", fontSize=8.5, leading=12,
                          textColor=C_SLATE_600)
    meta_val    = _style("MV",   fontName="Helvetica",      fontSize=8.5, leading=12,
                          textColor=C_SLATE_900)

    lines = report_md.split("\n")

    # ── Parse metadata ─────────────────────────────────────────────────────────
    deal_record    = "N/A"
    date_evaluated = "N/A"
    company_clean  = clean_unicode_and_emojis(company_name)
    verdict        = "PENDING"

    for line in lines:
        s = line.strip()
        if s.startswith("**Deal Evaluation Record:"):
            deal_record = s.replace("**Deal Evaluation Record:", "").replace("**", "").strip()
        elif s.startswith("**Date Evaluated:"):
            date_evaluated = s.replace("**Date Evaluated:", "").replace("**", "").strip()
        elif s.startswith("## ") and "COMMITTEE VERDICT:" in s.upper():
            verdict = s.split("COMMITTEE VERDICT:")[-1].strip().upper()

    verdict_color, verdict_bg, verdict_border = _verdict_colors(verdict)
    deal_record    = clean_unicode_and_emojis(deal_record)
    date_evaluated = clean_unicode_and_emojis(date_evaluated)

    # ── Parse risk scores ──────────────────────────────────────────────────────
    fin_score = leg_score = tech_score = mkt_score = weighted = None
    for line in lines:
        s = line.strip()
        m = re.search(r"Financial Risk.*?(\d+(?:\.\d+)?)/10", s, re.IGNORECASE)
        if m: fin_score = float(m.group(1))
        m = re.search(r"Legal Risk.*?(\d+(?:\.\d+)?)/10", s, re.IGNORECASE)
        if m: leg_score = float(m.group(1))
        m = re.search(r"Technical Risk.*?(\d+(?:\.\d+)?)/10", s, re.IGNORECASE)
        if m: tech_score = float(m.group(1))
        m = re.search(r"Market Risk.*?(\d+(?:\.\d+)?)/10", s, re.IGNORECASE)
        if m: mkt_score = float(m.group(1))
        m = re.search(r"WEIGHTED RISK SCORE.*?(\d+(?:\.\d+)?)/10", s, re.IGNORECASE)
        if m: weighted = float(m.group(1))

    # ── Parse verdict memo ─────────────────────────────────────────────────────
    verdict_memo: list[str] = []
    in_memo = False
    for line in lines:
        s = line.strip()
        if "COMMITTEE VERDICT:" in s.upper() and s.startswith("## "):
            in_memo = True
            continue
        if in_memo:
            if s.startswith("---") or (s.startswith("## ") and "COMMITTEE VERDICT:" not in s.upper()):
                in_memo = False
            else:
                verdict_memo.append(line)

    # ── Parse partners ─────────────────────────────────────────────────────────
    partners: list[tuple] = []  # (name, severity, findings_list)
    cur_name, cur_sev, cur_findings = None, 5, []
    in_timeline = False

    for line in lines:
        s = line.strip()
        if re.search(r"chronological partner audit timeline", s, re.IGNORECASE):
            in_timeline = True
            continue
        if not in_timeline:
            continue
        if s.startswith("```") or s.startswith("+--") or (s and set(s) <= set("-+=_ ")):
            continue
        if s.startswith("|"):
            inner = s.strip("|").strip()
            if not inner or set(inner) <= set("-+=_ "):
                continue
            s = inner
        if s.startswith("### "):
            if cur_name:
                partners.append((cur_name, cur_sev, cur_findings))
            cur_name = s.replace("###", "").strip()
            m = re.search(r"Severity:\s*(\d+)", cur_name, re.IGNORECASE)
            cur_sev = int(m.group(1)) if m else 5
            cur_name = re.sub(r"\s*\(Severity:.*?\)", "", cur_name).strip()
            cur_findings = []
        elif s.startswith("*Timestamp:"):
            cur_findings.append(("timestamp", clean_unicode_and_emojis(s)))
        elif s.startswith("- ") or s.startswith("* "):
            txt = _fmt(s[2:].strip())
            if txt and not set(txt.replace("&amp;", "")) <= set("-+=_ "):
                cur_findings.append(("bullet", txt))
        elif re.match(r"^#+\s+", s):
            cur_findings.append(("subhead", _fmt(re.sub(r"^#+\s+", "", s))))
        elif s:
            cur_findings.append(("text", _fmt(s)))

    if cur_name:
        partners.append((cur_name, cur_sev, cur_findings))

    # ══════════════════════════════════════════════════════════════════════════
    # BUILD STORY
    # ══════════════════════════════════════════════════════════════════════════
    story = []

    # ────────────────────────────────────────────────────────────────────────
    # PAGE 1 — COVER
    # ────────────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 60))

    logo = _get_brand_logo()
    if logo:
        png_bytes, aspect = logo
        lh = 42
        story.append(Image(io.BytesIO(png_bytes), width=lh * aspect, height=lh))
        story.append(Spacer(1, 8))
    else:
        story.append(Paragraph("FUSION", cover_title))

    story.append(Paragraph(
        "VENTURE CAPITAL  ·  AI INVESTMENT COMMITTEE",
        _style("CVTag", fontName="Helvetica-Bold", fontSize=9, leading=13,
               textColor=C_SLATE_600, spaceBefore=6, spaceAfter=36)
    ))
    story.append(HRFlowable(width="100%", thickness=1.5, color=C_SLATE_300,
                             spaceBefore=0, spaceAfter=24))
    story.append(Paragraph("DUE DILIGENCE AUDIT REPORT", cover_title))
    story.append(Paragraph(f"Investment Inquiry: {company_clean}",
                            _style("CvCo", fontName="Helvetica-Bold", fontSize=13,
                                   leading=17, textColor=C_SLATE_700, spaceAfter=28)))

    # Verdict badge
    vbadge_st = _style("VBadge", fontName="Helvetica-Bold", fontSize=16,
                        leading=20, textColor=verdict_color, alignment=1)
    cover_badge = Table(
        [[Paragraph("INVESTMENT COMMITTEE VERDICT", _style("VBL", fontName="Helvetica-Bold",
                                                            fontSize=7.5, leading=10,
                                                            textColor=C_SLATE_600, alignment=1))],
         [Paragraph(verdict, vbadge_st)]],
        colWidths=[504]
    )
    cover_badge.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), verdict_bg),
        ("BOX",           (0, 0), (-1, -1), 2, verdict_border),
        ("TOPPADDING",    (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
    ]))
    story.append(cover_badge)
    story.append(Spacer(1, 24))

    # Cover metadata table
    meta_data = [
        [Paragraph("DEAL RECORD",     meta_lbl), Paragraph(deal_record,    meta_val)],
        [Paragraph("DATE EVALUATED",  meta_lbl), Paragraph(date_evaluated, meta_val)],
        [Paragraph("COMMITTEE",       meta_lbl), Paragraph("5 AI Partners  ·  Fully Automated",
            _style("CMB", fontName="Helvetica", fontSize=8.5, leading=12, textColor=C_SLATE_900))],
        [Paragraph("STATUS",          meta_lbl), Paragraph("COMPLETE & VERIFIED",
            _style("CST", fontName="Helvetica-Bold", fontSize=8.5, leading=12, textColor=C_GREEN_700))],
    ]
    meta_table = Table(meta_data, colWidths=[150, 354])
    meta_table.setStyle(TableStyle([
        ("LINEBELOW",     (0, 0), (-1, -2), 0.5, C_SLATE_200),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING",    (0, 0), (-1, -1), 9),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(meta_table)

    story.append(Spacer(1, 24))
    story.append(HRFlowable(width="100%", thickness=0.5, color=C_SLATE_200,
                             spaceBefore=0, spaceAfter=0))
    story.append(PageBreak())

    # ────────────────────────────────────────────────────────────────────────
    # PAGE 2 — EXECUTIVE VERDICT SUMMARY
    # ────────────────────────────────────────────────────────────────────────
    story.append(Paragraph("Executive Verdict Summary", h1))
    story.append(HRFlowable(width="100%", thickness=1, color=C_SLATE_300,
                             spaceBefore=2, spaceAfter=14))

    # Large verdict display
    verdict_panel = Table(
        [[Paragraph("INVESTMENT COMMITTEE DECISION",
                    _style("VL", fontName="Helvetica-Bold", fontSize=7.5, leading=10,
                           textColor=C_SLATE_600, alignment=1))],
         [Paragraph(verdict,
                    _style("VT", fontName="Helvetica-Bold", fontSize=30, leading=36,
                           textColor=verdict_color, alignment=1))]],
        colWidths=[504]
    )
    verdict_panel.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), verdict_bg),
        ("BOX",           (0, 0), (-1, -1), 2, verdict_border),
        ("TOPPADDING",    (0, 0), (-1, -1), 18),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 18),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
    ]))
    story.append(verdict_panel)
    story.append(Spacer(1, 16))

    # Verdict memo body
    for line in verdict_memo:
        s = line.strip()
        if not s:
            continue
        if s.startswith("```") or s.startswith("+--") or (s and set(s) <= set("-+=_ `")):
            continue
        if s.startswith("|"):
            inner = s.strip("|").strip()
            if not inner or set(inner) <= set("-+=_ "):
                continue
            s = inner
        s_fmt = _fmt(s)
        if s.startswith("# "):
            story.append(Paragraph(s_fmt.replace("# ", "").upper(), h1))
        elif s.startswith("### "):
            story.append(Paragraph(s_fmt.replace("### ", ""), h2))
        elif s.startswith("- ") or s.startswith("* "):
            txt = _fmt(s[2:].strip())
            if txt:
                story.append(Paragraph(f"&bull;  {txt}", bullet))
        elif re.match(r"^\d+\.\s+", s):
            story.append(Paragraph(s_fmt, bullet))
        else:
            story.append(Paragraph(s_fmt, body))

    story.append(PageBreak())

    # ────────────────────────────────────────────────────────────────────────
    # PAGE 3 — RISK ANALYSIS SCORECARD
    # ────────────────────────────────────────────────────────────────────────
    story.append(Paragraph("Risk Analysis Scorecard", h1))
    story.append(HRFlowable(width="100%", thickness=1, color=C_SLATE_300,
                             spaceBefore=2, spaceAfter=14))

    if all(v is not None for v in [fin_score, leg_score, tech_score, mkt_score]):
        story.extend(_scorecard_grid(
            fin_score, leg_score, tech_score, mkt_score,
            weighted, verdict_color, verdict_bg, body
        ))
        story.append(Spacer(1, 20))
        story.append(Paragraph("Risk Level Breakdown", h2))
        story.append(HRFlowable(width="100%", thickness=0.5, color=C_SLATE_200,
                                 spaceBefore=2, spaceAfter=10))
        drawing = _risk_bar_chart(fin_score, leg_score, tech_score, mkt_score, weighted)
        story.append(_DrawingFlowable(drawing))

    story.append(PageBreak())

    # ────────────────────────────────────────────────────────────────────────
    # PAGES 4+ — ONE PAGE PER PARTNER AGENT
    # ────────────────────────────────────────────────────────────────────────
    # Canonical partner order so Managing Partner always goes last
    _ORDER = ["financial", "legal", "technical", "market", "managing"]

    def _sort_key(p):
        name_low = p[0].lower()
        for i, k in enumerate(_ORDER):
            if k in name_low:
                return i
        return len(_ORDER)

    for pname, psev, pfindings in sorted(partners, key=_sort_key):
        meta = _partner_meta(pname)
        story.extend(_partner_page_header(meta, company_clean, psev, body))
        story.extend(_partner_findings(pfindings, body, bullet))
        story.append(Spacer(1, 16))
        story.append(HRFlowable(width="100%", thickness=0.5, color=C_SLATE_200,
                                 spaceBefore=4, spaceAfter=0))
        story.append(PageBreak())

    # Remove trailing page break
    if story and isinstance(story[-1], PageBreak):
        story.pop()

    doc.build(story, canvasmaker=BrandedCanvas)
    buffer.seek(0)
    return buffer.getvalue()
