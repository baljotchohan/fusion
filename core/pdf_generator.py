# core/pdf_generator.py
"""
PDF Report Generator — compiles FUSION diligence markdown into a
publication-quality PDF with colored verdict, visual risk bars,
and clean partner audit cards.
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

# ── Brand palette ─────────────────────────────────────────────────────────────
C_SLATE_900  = colors.HexColor("#0f172a")
C_SLATE_700  = colors.HexColor("#334155")
C_SLATE_600  = colors.HexColor("#475569")
C_SLATE_300  = colors.HexColor("#cbd5e1")
C_SLATE_200  = colors.HexColor("#e2e8f0")
C_SLATE_50   = colors.HexColor("#f8fafc")
C_WHITE      = colors.HexColor("#ffffff")
C_GREEN_600  = colors.HexColor("#16a34a")
C_GREEN_50   = colors.HexColor("#f0fdf4")
C_GREEN_BAR  = colors.HexColor("#22c55e")
C_AMBER_600  = colors.HexColor("#d97706")
C_AMBER_50   = colors.HexColor("#fffbeb")
C_AMBER_BAR  = colors.HexColor("#f59e0b")
C_RED_600    = colors.HexColor("#dc2626")
C_RED_50     = colors.HexColor("#fef2f2")
C_RED_BAR    = colors.HexColor("#ef4444")
C_BLUE_600   = colors.HexColor("#2563eb")

_LOGO_PATH  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fusionlogo.png")
_LOGO_CACHE: dict = {}


# ── Logo ──────────────────────────────────────────────────────────────────────
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


# ── Text cleaning ─────────────────────────────────────────────────────────────
def _strip_agent_internals(text: str) -> str:
    """Remove LLM tool-call artifacts that must never appear in client reports."""
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
    """Bold-markdown to ReportLab tags + clean."""
    text = clean_unicode_and_emojis(text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    return text


# ── Verdict helpers ───────────────────────────────────────────────────────────
def _verdict_colors(verdict: str):
    v = verdict.upper().strip()
    if v in ("INVEST",):
        return C_GREEN_600, C_GREEN_50, C_GREEN_600
    if v in ("CONDITIONAL",):
        return C_AMBER_600, C_AMBER_50, C_AMBER_600
    return C_RED_600, C_RED_50, C_RED_600   # REJECT / PASS / anything else


def _risk_bar_color(score: float) -> colors.Color:
    if score <= 4:
        return C_GREEN_BAR
    if score <= 6:
        return C_AMBER_BAR
    return C_RED_BAR


def _severity_color(severity: int) -> colors.Color:
    if severity >= 8:
        return C_RED_600
    if severity >= 5:
        return C_AMBER_600
    return C_GREEN_600


# ── Risk bar chart (Drawing) ──────────────────────────────────────────────────
def _risk_bar_chart(fin: float, leg: float, tech: float, mkt: float, weighted: float) -> Drawing:
    domains = [
        ("Financial Risk", fin, "30%"),
        ("Legal Risk",     leg, "25%"),
        ("Technical Risk", tech, "25%"),
        ("Market Risk",    mkt, "20%"),
    ]
    LABEL_W   = 100
    BAR_MAX_W = 280
    SCORE_W   = 80
    ROW_H     = 26
    PAD       = 6
    TOTAL_W   = LABEL_W + BAR_MAX_W + SCORE_W + 24
    TOTAL_H   = len(domains) * ROW_H + PAD * 2 + ROW_H + 8  # extra row for weighted

    d = Drawing(TOTAL_W, TOTAL_H)

    # Column headers
    d.add(GStr(LABEL_W - 4, TOTAL_H - PAD - 8, "DOMAIN",
               fontName="Helvetica-Bold", fontSize=7.5,
               fillColor=C_SLATE_600, textAnchor="end"))
    d.add(GStr(LABEL_W + BAR_MAX_W / 2, TOTAL_H - PAD - 8, "RISK LEVEL",
               fontName="Helvetica-Bold", fontSize=7.5,
               fillColor=C_SLATE_600, textAnchor="middle"))
    d.add(GStr(LABEL_W + BAR_MAX_W + 8, TOTAL_H - PAD - 8, "SCORE",
               fontName="Helvetica-Bold", fontSize=7.5,
               fillColor=C_SLATE_600, textAnchor="start"))

    for i, (name, score, weight) in enumerate(domains):
        y = TOTAL_H - PAD - 16 - (i + 1) * ROW_H
        bar_w = (score / 10.0) * BAR_MAX_W
        bar_h = 14

        # Label
        d.add(GStr(LABEL_W - 6, y + 4, name,
                   fontName="Helvetica", fontSize=8.5,
                   fillColor=C_SLATE_700, textAnchor="end"))

        # Background track
        d.add(Rect(LABEL_W, y, BAR_MAX_W, bar_h,
                   fillColor=C_SLATE_200, strokeColor=C_SLATE_300, strokeWidth=0.5))

        # Filled bar
        if bar_w > 0:
            d.add(Rect(LABEL_W, y, bar_w, bar_h,
                       fillColor=_risk_bar_color(score), strokeWidth=0))

        # Score + weight label
        d.add(GStr(LABEL_W + BAR_MAX_W + 8, y + 4,
                   f"{score:.1f}/10  (wt {weight})",
                   fontName="Helvetica-Bold", fontSize=8.5,
                   fillColor=C_SLATE_900))

    # Weighted total row
    if weighted is not None:
        y = PAD
        d.add(GLine(LABEL_W, y + ROW_H - 2, TOTAL_W, y + ROW_H - 2,
                    strokeColor=C_SLATE_300, strokeWidth=0.5))
        d.add(GStr(LABEL_W - 6, y + 4, "WEIGHTED SCORE",
                   fontName="Helvetica-Bold", fontSize=8.5,
                   fillColor=C_SLATE_900, textAnchor="end"))
        bar_w = (weighted / 10.0) * BAR_MAX_W
        d.add(Rect(LABEL_W, y, BAR_MAX_W, 14,
                   fillColor=C_SLATE_200, strokeColor=C_SLATE_300, strokeWidth=0.5))
        if bar_w > 0:
            d.add(Rect(LABEL_W, y, bar_w, 14,
                       fillColor=_risk_bar_color(weighted), strokeWidth=0))
        d.add(GStr(LABEL_W + BAR_MAX_W + 8, y + 4,
                   f"{weighted:.2f}/10",
                   fontName="Helvetica-Bold", fontSize=9,
                   fillColor=C_SLATE_900))

    return d


class _DrawingFlowable(Flowable):
    """Wraps a reportlab Drawing so it can sit in a platypus story."""
    def __init__(self, drawing: Drawing):
        super().__init__()
        self.drawing = drawing
        self.width  = drawing.width
        self.height = drawing.height

    def draw(self):
        renderPDF.draw(self.drawing, self.canv, 0, 0)


# ── Running header / footer ───────────────────────────────────────────────────
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

        # Header
        text_x = 54
        logo = _get_brand_logo()
        if logo:
            png_bytes, aspect = logo
            lh = 10
            lw = lh * aspect
            try:
                self.drawImage(ImageReader(io.BytesIO(png_bytes)),
                               54, 752, width=lw, height=lh, mask="auto")
                text_x = 54 + lw + 8
            except Exception:
                pass
        self.setFont("Helvetica-Bold", 7.5)
        self.setFillColor(C_SLATE_600)
        self.drawString(text_x, 755, "|   DUE DILIGENCE AUDIT REPORT")
        self.drawRightString(612 - 54, 755, "CONFIDENTIAL")
        self.setStrokeColor(C_SLATE_300)
        self.setLineWidth(0.5)
        self.line(54, 745, 612 - 54, 745)

        # Footer
        self.line(54, 55, 612 - 54, 55)
        self.setFont("Helvetica", 7.5)
        self.drawString(54, 42, "FUSION Investment Committee  ·  AI-Powered Venture Capital Due Diligence")
        self.drawRightString(612 - 54, 42, f"Page {self._pageNumber} of {total_pages}")
        self.restoreState()


# ── Partner audit card ────────────────────────────────────────────────────────
def _partner_card(partner_name: str, findings: list,
                  body_style: ParagraphStyle, bullet_style: ParagraphStyle,
                  severity: int = 5) -> list:
    elements = []
    accent = _severity_color(severity)
    partner_clean = clean_unicode_and_emojis(partner_name)

    title_style = ParagraphStyle(
        "CardTitle", parent=body_style,
        fontName="Helvetica-Bold", fontSize=11, leading=14,
        textColor=C_SLATE_900, spaceBefore=14, spaceAfter=2, keepWithNext=True,
    )
    badge_style = ParagraphStyle(
        "SevBadge", parent=body_style,
        fontName="Helvetica-Bold", fontSize=8, leading=10,
        textColor=accent,
    )
    ts_style = ParagraphStyle(
        "CardTS", parent=body_style,
        fontName="Helvetica-Oblique", fontSize=7.5, leading=10,
        textColor=C_SLATE_600, spaceAfter=6, keepWithNext=True,
    )

    # Severity label
    sev_label = "HIGH SEVERITY" if severity >= 8 else ("MEDIUM" if severity >= 5 else "LOW")

    header_items = [
        Paragraph(partner_clean.upper(), title_style),
        Paragraph(f"{sev_label}  ·  {severity}/10", badge_style),
    ]

    timestamp_text = None
    body_items = []
    for kind, text in findings:
        if kind == "timestamp":
            timestamp_text = text
        elif kind == "bullet":
            body_items.append(Paragraph(f"&bull; {text}", bullet_style))
        elif kind == "subhead":
            body_items.append(Paragraph(f"<b>{text}</b>", ParagraphStyle(
                "CardSH", parent=body_style, fontName="Helvetica-Bold",
                fontSize=9, leading=12, spaceBefore=6, spaceAfter=2)))
        else:
            if text.strip():
                body_items.append(Paragraph(text, body_style))

    if timestamp_text:
        header_items.append(Paragraph(timestamp_text, ts_style))

    # Accent left-border using a 1-col table
    content_rows = []
    for el in header_items + (body_items[:1] if body_items else []):
        content_rows.append([el])

    if content_rows:
        kt = Table(content_rows, colWidths=[484])
        kt.setStyle(TableStyle([
            ("LEFTPADDING",  (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING",   (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 2),
            ("LINEBEFORE",   (0, 0), (-1, -1), 3, accent),
        ]))
        elements.append(kt)

    elements.extend(body_items[1:])
    elements.append(HRFlowable(width="100%", thickness=0.5,
                                color=C_SLATE_200, spaceBefore=10, spaceAfter=4))
    return elements


# ── Main compiler ─────────────────────────────────────────────────────────────
def compile_pdf_report(report_md: str, company_name: str) -> bytes:
    """Parse FUSION diligence markdown and compile a professional PDF."""
    report_md = _strip_agent_internals(report_md)
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        leftMargin=54, rightMargin=54, topMargin=72, bottomMargin=72,
    )

    SS = getSampleStyleSheet()

    def _style(name, **kw):
        return ParagraphStyle(name, parent=SS["Normal"], **kw)

    cover_title  = _style("CvT",  fontName="Helvetica-Bold", fontSize=26, leading=32, textColor=C_SLATE_900, spaceAfter=8)
    cover_sub    = _style("CvS",  fontName="Helvetica-Bold", fontSize=11, leading=15, textColor=C_SLATE_700, spaceAfter=36)
    h1           = _style("H1",   fontName="Helvetica-Bold", fontSize=13, leading=17, textColor=C_SLATE_900, spaceBefore=20, spaceAfter=6,  keepWithNext=True)
    h2           = _style("H2",   fontName="Helvetica-Bold", fontSize=10, leading=14, textColor=C_SLATE_700, spaceBefore=10, spaceAfter=4,  keepWithNext=True)
    body         = _style("Body", fontName="Helvetica",      fontSize=9,  leading=13.5, textColor=C_SLATE_900, spaceAfter=5)
    bullet       = _style("Bull", fontName="Helvetica",      fontSize=9,  leading=13.5, textColor=C_SLATE_900, spaceAfter=4, leftIndent=14, firstLineIndent=-10)
    meta_lbl     = _style("ML",   fontName="Helvetica-Bold", fontSize=9,  leading=13,  textColor=C_SLATE_600)
    meta_val     = _style("MV",   fontName="Helvetica",      fontSize=9,  leading=13,  textColor=C_SLATE_900)

    lines = report_md.split("\n")

    # ── Parse metadata ────────────────────────────────────────────────────────
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

    # ── Parse risk scores ─────────────────────────────────────────────────────
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

    # ── Parse verdict memo block ──────────────────────────────────────────────
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

    # ── Parse partner timeline ────────────────────────────────────────────────
    partners: list[tuple] = []   # (name, severity, findings_list)
    cur_name, cur_sev, cur_findings = None, 5, []
    in_timeline = False

    for line in lines:
        s = line.strip()
        if re.search(r"chronological partner audit timeline", s, re.IGNORECASE):
            in_timeline = True
            continue
        if not in_timeline:
            continue

        # Skip code fences, pure rules, pipe-only lines
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

    # ── 1. COVER PAGE ─────────────────────────────────────────────────────────
    story.append(Spacer(1, 72))

    logo = _get_brand_logo()
    if logo:
        png_bytes, aspect = logo
        lh = 38
        story.append(Image(io.BytesIO(png_bytes), width=lh * aspect, height=lh))
    else:
        story.append(Paragraph("FUSION", cover_title))

    story.append(Paragraph("VENTURE CAPITAL  ·  AI INVESTMENT COMMITTEE",
                            _style("CVTag", fontName="Helvetica-Bold", fontSize=9.5,
                                   leading=13, textColor=C_SLATE_600, spaceBefore=8)))
    story.append(Spacer(1, 32))
    story.append(Paragraph("DUE DILIGENCE AUDIT REPORT", cover_title))
    story.append(Paragraph(f"INVESTMENT INQUIRY: {company_clean.upper()}", cover_sub))
    story.append(HRFlowable(width="100%", thickness=2, color=C_SLATE_900,
                             spaceBefore=0, spaceAfter=130))

    # Verdict badge on cover
    vbadge_style = _style("VBadge", fontName="Helvetica-Bold", fontSize=13,
                           leading=17, textColor=verdict_color, alignment=1)
    cover_badge = Table([[Paragraph(f"COMMITTEE VERDICT: {verdict}", vbadge_style)]],
                        colWidths=[504])
    cover_badge.setStyle(TableStyle([
        ("BACKGROUND",     (0, 0), (-1, -1), verdict_bg),
        ("BOX",            (0, 0), (-1, -1), 1.5, verdict_border),
        ("TOPPADDING",     (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 10),
        ("ALIGN",          (0, 0), (-1, -1), "CENTER"),
    ]))
    story.append(cover_badge)
    story.append(Spacer(1, 18))

    # Metadata table
    meta_data = [
        [Paragraph("DEAL RECORD",          meta_lbl), Paragraph(deal_record,    meta_val)],
        [Paragraph("DATE EVALUATED",        meta_lbl), Paragraph(date_evaluated, meta_val)],
        [Paragraph("COMMITTEE STATUS",      meta_lbl), Paragraph("COMPLETE &amp; VERIFIED",
            _style("MBold", fontName="Helvetica-Bold", fontSize=9, leading=13, textColor=C_SLATE_900))],
    ]
    meta_table = Table(meta_data, colWidths=[160, 344])
    meta_table.setStyle(TableStyle([
        ("LINEBELOW",      (0, 0), (-1, -2), 0.5, C_SLATE_300),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 8),
        ("TOPPADDING",     (0, 0), (-1, -1), 8),
        ("VALIGN",         (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(meta_table)
    story.append(PageBreak())

    # ── 2. EXECUTIVE VERDICT SUMMARY ──────────────────────────────────────────
    story.append(Paragraph("Executive Verdict Summary", h1))
    story.append(HRFlowable(width="100%", thickness=1, color=C_SLATE_300,
                             spaceBefore=2, spaceAfter=14))

    verdict_title_style = _style(
        "VT", fontName="Helvetica-Bold", fontSize=26, leading=30,
        textColor=verdict_color, alignment=1,
    )
    vt_label_style = _style("VTL", fontName="Helvetica-Bold", fontSize=8,
                             leading=11, textColor=C_SLATE_600, alignment=1)

    verdict_panel = Table([
        [Paragraph("INVESTMENT COMMITTEE DECISION", vt_label_style)],
        [Paragraph(verdict, verdict_title_style)],
    ], colWidths=[504])
    verdict_panel.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), verdict_bg),
        ("BOX",           (0, 0), (-1, -1), 2, verdict_border),
        ("TOPPADDING",    (0, 0), (-1, -1), 16),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
    ]))
    story.append(verdict_panel)
    story.append(Spacer(1, 16))

    # Render verdict memo (investment memo body)
    skip_next_fence = False
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
                story.append(Paragraph(f"&bull; {txt}", bullet))
        elif re.match(r"^\d+\.\s+", s):
            story.append(Paragraph(s_fmt, bullet))
        else:
            story.append(Paragraph(s_fmt, body))

    story.append(Spacer(1, 8))

    # ── 3. RISK SCORECARD (visual) ────────────────────────────────────────────
    story.append(Paragraph("Risk Analysis Scorecard", h1))
    story.append(HRFlowable(width="100%", thickness=1, color=C_SLATE_300,
                             spaceBefore=2, spaceAfter=14))

    if all(v is not None for v in [fin_score, leg_score, tech_score, mkt_score]):
        drawing = _risk_bar_chart(fin_score, leg_score, tech_score, mkt_score, weighted)
        story.append(_DrawingFlowable(drawing))
        story.append(Spacer(1, 6))

        # Summary table below bars
        w_label = f"{weighted:.2f}/10" if weighted is not None else "N/A"
        score_rows = [
            [Paragraph("<b>RISK DOMAIN</b>",   _style("TH1", fontName="Helvetica-Bold", fontSize=8.5, leading=11, textColor=C_WHITE)),
             Paragraph("<b>SCORE</b>",         _style("TH2", fontName="Helvetica-Bold", fontSize=8.5, leading=11, textColor=C_WHITE, alignment=1)),
             Paragraph("<b>WEIGHT</b>",        _style("TH3", fontName="Helvetica-Bold", fontSize=8.5, leading=11, textColor=C_WHITE, alignment=1))],
            [Paragraph("Financial Risk",  body), Paragraph(f"{fin_score:.1f}/10",  _style("SV",  fontName="Helvetica", fontSize=9, leading=13, textColor=C_SLATE_900, alignment=1)), Paragraph("30%", _style("SW",  fontName="Helvetica", fontSize=9, leading=13, textColor=C_SLATE_900, alignment=1))],
            [Paragraph("Legal Risk",      body), Paragraph(f"{leg_score:.1f}/10",  _style("SV2", fontName="Helvetica", fontSize=9, leading=13, textColor=C_SLATE_900, alignment=1)), Paragraph("25%", _style("SW2", fontName="Helvetica", fontSize=9, leading=13, textColor=C_SLATE_900, alignment=1))],
            [Paragraph("Technical Risk",  body), Paragraph(f"{tech_score:.1f}/10", _style("SV3", fontName="Helvetica", fontSize=9, leading=13, textColor=C_SLATE_900, alignment=1)), Paragraph("25%", _style("SW3", fontName="Helvetica", fontSize=9, leading=13, textColor=C_SLATE_900, alignment=1))],
            [Paragraph("Market Risk",     body), Paragraph(f"{mkt_score:.1f}/10",  _style("SV4", fontName="Helvetica", fontSize=9, leading=13, textColor=C_SLATE_900, alignment=1)), Paragraph("20%", _style("SW4", fontName="Helvetica", fontSize=9, leading=13, textColor=C_SLATE_900, alignment=1))],
            [Paragraph("<b>WEIGHTED RISK SCORE</b>", _style("TWS", fontName="Helvetica-Bold", fontSize=9, leading=12, textColor=C_SLATE_900)),
             Paragraph(f"<b>{w_label}</b>", _style("TWV", fontName="Helvetica-Bold", fontSize=9, leading=12, textColor=verdict_color, alignment=1)),
             Paragraph("", body)],
        ]
        score_table = Table(score_rows, colWidths=[300, 112, 92])
        score_table.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0),  C_SLATE_700),
            ("BACKGROUND",    (0, -1),(- 1, -1), verdict_bg),
            ("ROWBACKGROUNDS",(0, 1), (-1, -2), [C_WHITE, C_SLATE_50]),
            ("GRID",          (0, 0), (-1, -1), 0.5, C_SLATE_300),
            ("TOPPADDING",    (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(score_table)
    story.append(Spacer(1, 20))

    # ── 4. PARTNER AUDIT LOGS ─────────────────────────────────────────────────
    story.append(Paragraph("Partner Audit Logs", h1))
    story.append(HRFlowable(width="100%", thickness=1, color=C_SLATE_300,
                             spaceBefore=2, spaceAfter=14))

    for pname, psev, pfindings in partners:
        story.extend(_partner_card(pname, pfindings, body, bullet, psev))

    # Build
    doc.build(story, canvasmaker=BrandedCanvas)
    buffer.seek(0)
    return buffer.getvalue()
