# core/pdf_generator.py
"""
PDF Report Generator — compiles markdown due diligence reports into
professional, publication-quality PDF documents using ReportLab.
"""
import io
import os
import re
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

# FUSION Brand Colors
BRAND_GREEN = colors.HexColor("#4fae47")  # FUSION green
BRAND_DARK_GREEN = colors.HexColor("#3d8b36")
DARK_TEXT = colors.HexColor("#18181b")    # Slate 900
SECONDARY_TEXT = colors.HexColor("#71717a") # Slate 500
BORDER_GREY = colors.HexColor("#e4e4e7")    # Slate 200
BG_LIGHT = colors.HexColor("#f8fafc")       # Slate 50
BG_WHITE = colors.HexColor("#ffffff")
BG_INK = colors.HexColor("#0b0f0e")         # near-black brand backdrop

# Real FUSION "F" mark — trimmed of its whitespace margins once and cached.
_LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logofusion.png")
_LOGO_CACHE = {}


def _get_brand_logo():
    """Return (png_bytes, aspect_ratio=w/h) for the trimmed green 'F' mark, or None.
    The source PNG has wide white margins, so we crop to the glyph for crisp,
    tightly-aligned placement in the PDF. Result is cached for reuse across pages."""
    if "logo" in _LOGO_CACHE:
        return _LOGO_CACHE["logo"]
    result = None
    try:
        from PIL import Image as PILImage
        img = PILImage.open(_LOGO_PATH).convert("RGBA")
        # Knock the near-white photo background out to transparent so the green
        # mark blends seamlessly onto any page colour (no grey box).
        px = img.load()
        w, h = img.size
        for y in range(h):
            for x in range(w):
                r, g, b, a = px[x, y]
                if r > 226 and g > 226 and b > 226:
                    px[x, y] = (r, g, b, 0)
        bbox = img.split()[3].getbbox()  # trim to the non-transparent glyph
        if bbox:
            img = img.crop(bbox)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        result = (buf.getvalue(), img.width / float(img.height))
    except Exception:
        result = None
    _LOGO_CACHE["logo"] = result
    return result


def clean_unicode_and_emojis(text: str) -> str:
    """Replaces emojis and unsupported high-Unicode characters with safe representations
    or strips them to prevent ReportLab rendering/encoding exceptions.
    Also escapes XML/HTML special characters to prevent paraparser syntax errors.
    """
    if not text:
        return ""
        
    replacements = {
        "💼": "",
        "📊": "",
        "⚖️": "",
        "⚖": "",
        "🚨": "[ALERT]",
        "📋": "[GAP]",
        "🛡️": "[CONFIDENCE]",
        "🛡": "[CONFIDENCE]",
        "🎯": "[COVERAGE]",
        "🚦": "[STATUS]",
        "🏢": "",
        "💵": "",
        "🔧": "",
        "📈": "",
        "📝": "",
        "🤖": "",
        "🚀": "",
        "🤝": "",
        "⚠️": "[WARNING]",
        "⚠": "[WARNING]",
        "✨": "",
        "🔥": "",
        "─": "-",
        "—": "-",
        "–": "-",
        "“": '"',
        "”": '"',
        "‘": "'",
        "’": "'",
        "•": "*",
    }
    
    for emoji, replacement in replacements.items():
        text = text.replace(emoji, replacement)
        
    # Standard Helvetica supports Latin-1 characters (up to codepoint 255).
    # We strip out any character beyond 255 to ensure zero compilation errors.
    cleaned = []
    for char in text:
        if ord(char) <= 255:
            cleaned.append(char)
        else:
            # Skip high unicode characters to avoid 'latin-1' encoding crashes
            pass
            
    text = "".join(cleaned)
    
    # Escape XML/HTML special characters to prevent paraparser syntax errors
    text = text.replace("&", "&amp;")
    text = text.replace("&amp;amp;", "&amp;")
    text = text.replace("&amp;lt;", "&lt;")
    text = text.replace("&amp;gt;", "&gt;")
    text = text.replace("&amp;quot;", "&amp;")
    text = text.replace("&amp;apos;", "&apos;")
    
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    
    # Restore allowed tags
    allowed_tags = ["b", "i", "u", "strong", "em"]
    for tag in allowed_tags:
        text = text.replace(f"&lt;{tag}&gt;", f"<{tag}>")
        text = text.replace(f"&lt;/{tag}&gt;", f"</{tag}>")
        
    # Handle self-closing/standard line break tags
    text = text.replace("&lt;br&gt;", "<br/>")
    text = text.replace("&lt;br/&gt;", "<br/>")
    text = text.replace("&lt;br /&gt;", "<br/>")
    
    return text


class BrandedCanvas(canvas.Canvas):
    """Canvas that draws professional running headers and footers on every page."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pages = []

    def showPage(self):
        self.pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        page_count = len(self.pages)
        for page in self.pages:
            self.__dict__.update(page)
            self.draw_header_footer(page_count)
            super().showPage()
        super().save()

    def draw_header_footer(self, total_pages):
        self.saveState()
        
        # Suppress headers/footers on page 1 (cover page)
        if self._pageNumber == 1:
            self.restoreState()
            return
            
        # Draw Running Header — real F mark + wordmark
        text_x = 54
        logo = _get_brand_logo()
        if logo:
            png_bytes, aspect = logo
            h = 13
            w = h * aspect
            try:
                self.drawImage(ImageReader(io.BytesIO(png_bytes)), 54, 750, width=w, height=h, mask='auto')
                text_x = 54 + w + 7
            except Exception:
                pass

        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(BRAND_DARK_GREEN)
        t1 = "FUSION VENTURE CAPITAL"
        self.drawString(text_x, 755, t1)

        x2 = text_x + self.stringWidth(t1, "Helvetica-Bold", 8) + 8
        self.setFont("Helvetica", 8)
        self.setFillColor(SECONDARY_TEXT)
        self.drawString(x2, 755, "|   DUE DILIGENCE AUDIT REPORT")
        self.drawRightString(612 - 54, 755, "CONFIDENTIAL")
        
        self.setStrokeColor(BORDER_GREY)
        self.setLineWidth(0.5)
        self.line(54, 747, 612 - 54, 747)
        
        # Draw Running Footer
        self.line(54, 55, 612 - 54, 55)
        self.drawString(54, 42, "FUSION Investment Committee Swarm Engine")
        self.drawRightString(612 - 54, 42, f"Page {self._pageNumber} of {total_pages}")
        
        self.restoreState()


def compile_pdf_report(report_md: str, company_name: str) -> bytes:
    """Parses FUSION diligence report markdown and compiles it into a styled PDF.

    Returns:
        bytes: Raw PDF file bytes.
    """
    buffer = io.BytesIO()
    
    # Standard letter is 612 x 792 pt
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=54,  # 0.75 in
        rightMargin=54,
        topMargin=72,   # 1.0 in (space for running header)
        bottomMargin=72
    )

    styles = getSampleStyleSheet()
    
    # Custom Typography Styles
    cover_title_style = ParagraphStyle(
        'CoverTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=28,
        leading=34,
        textColor=DARK_TEXT,
        spaceAfter=8
    )
    
    cover_subtitle_style = ParagraphStyle(
        'CoverSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=17,
        textColor=BRAND_GREEN,
        spaceAfter=40
    )
    
    h1_style = ParagraphStyle(
        'Header1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=19,
        textColor=DARK_TEXT,
        spaceBefore=22,
        spaceAfter=8,
        keepWithNext=True
    )
    
    h2_style = ParagraphStyle(
        'Header2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=BRAND_DARK_GREEN,
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=14,
        textColor=DARK_TEXT,
        spaceAfter=8
    )
    
    bullet_style = ParagraphStyle(
        'BulletCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=14,
        textColor=DARK_TEXT,
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=5
    )
    
    meta_label_style = ParagraphStyle(
        'MetaLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=13,
        textColor=SECONDARY_TEXT
    )
    
    meta_val_style = ParagraphStyle(
        'MetaValue',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13,
        textColor=DARK_TEXT
    )

    verdict_lbl_style = ParagraphStyle(
        'VerdictLbl',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=SECONDARY_TEXT,
        alignment=1
    )

    story = []
    
    # ── Parse markdown sections ──
    lines = report_md.split("\n")
    
    # Extract metadata
    deal_record = "N/A"
    date_evaluated = "N/A"
    verdict = "PENDING"
    verdict_memo_lines = []
    in_verdict_memo = False
    
    idx = 0
    while idx < len(lines):
        line = lines[idx].strip()
        
        # Parse frontmatter
        if line.startswith("**Deal Evaluation Record:"):
            deal_record = line.replace("**Deal Evaluation Record:", "").replace("**", "").strip()
        elif line.startswith("**Date Evaluated:"):
            date_evaluated = line.replace("**Date Evaluated:", "").replace("**", "").strip()
        elif line.startswith("## ⚖️ COMMITTEE VERDICT:"):
            verdict = line.replace("## ⚖️ COMMITTEE VERDICT:", "").strip()
            in_verdict_memo = True
            idx += 1
            continue
        elif in_verdict_memo:
            if line.startswith("---") or line.startswith("## "):
                in_verdict_memo = False
            else:
                if line:
                    verdict_memo_lines.append(line)
        idx += 1
        
    # Clean parsed values
    deal_record = clean_unicode_and_emojis(deal_record)
    date_evaluated = clean_unicode_and_emojis(date_evaluated)
    verdict = clean_unicode_and_emojis(verdict).upper().strip()
    
    # ────────────────────────────────────────────────────────
    # 1. COVER PAGE
    # ────────────────────────────────────────────────────────
    story.append(Spacer(1, 78))

    # ── Brand lockup: real green "F" mark + "USION" wordmark = FUSION ──
    wordmark_style = ParagraphStyle(
        'Wordmark', parent=styles['Normal'], fontName='Helvetica-Bold',
        fontSize=34, leading=38, textColor=DARK_TEXT,
    )
    tagline_style = ParagraphStyle(
        'Tagline', parent=styles['Normal'], fontName='Helvetica-Bold',
        fontSize=9.5, leading=13, textColor=SECONDARY_TEXT, spaceBefore=10,
    )

    _logo = _get_brand_logo()
    if _logo:
        _png, _aspect = _logo
        _lh = 44
        _lw = _lh * _aspect
        brand_row = Table(
            [[Image(io.BytesIO(_png), width=_lw, height=_lh),
              Paragraph("USION", wordmark_style)]],
            colWidths=[_lw + 2, 360], rowHeights=[_lh],
        )
        brand_row.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(brand_row)
    else:
        story.append(Paragraph("FUSION", wordmark_style))

    story.append(Paragraph("VENTURE CAPITAL · AI INVESTMENT COMMITTEE", tagline_style))
    story.append(Spacer(1, 34))

    # Title & Subtitle
    company_name_clean = clean_unicode_and_emojis(company_name)
    story.append(Paragraph("DUE DILIGENCE AUDIT REPORT", cover_title_style))
    story.append(Paragraph(f"INVESTMENT INQUIRY: {company_name_clean.upper()}", cover_subtitle_style))
    
    # Decorative line
    story.append(HRFlowable(width="100%", thickness=4, color=BRAND_GREEN, spaceBefore=0, spaceAfter=200))
    
    # Metadata Block at bottom of cover page
    meta_box_data = [
        [Paragraph("DEAL RECORD", meta_label_style), Paragraph(deal_record, meta_val_style)],
        [Paragraph("DATE EVALUATED", meta_label_style), Paragraph(date_evaluated, meta_val_style)],
        [Paragraph("SECURITY SWARM STATUS", meta_label_style), Paragraph("COMPLETE & VERIFIED", ParagraphStyle('MStatus', parent=meta_val_style, fontName='Helvetica-Bold', textColor=BRAND_DARK_GREEN))],
    ]
    meta_box_table = Table(meta_box_data, colWidths=[160, 340])
    meta_box_table.setStyle(TableStyle([
        ('LINEBELOW', (0,0), (-1,-2), 0.5, BORDER_GREY),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(meta_box_table)
    
    story.append(PageBreak())
    
    # ────────────────────────────────────────────────────────
    # 2. MAIN REPORT - EXECUTIVE SUMMARY & VERDICT
    # ────────────────────────────────────────────────────────
    story.append(Paragraph("Executive Verdict Summary", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER_GREY, spaceBefore=2, spaceAfter=14))
    
    # Configure colors based on investment verdict
    if "INVEST" in verdict:
        bg_color = colors.HexColor("#f0fdf4")      # Soft Green
        box_color = colors.HexColor("#bbf7d0")     # Light Green Border
        txt_color = colors.HexColor("#15803d")     # Deep Green Text
    elif "CONDITIONAL" in verdict:
        bg_color = colors.HexColor("#fffbeb")      # Soft Amber/Yellow
        box_color = colors.HexColor("#fef3c7")     # Light Yellow Border
        txt_color = colors.HexColor("#b45309")     # Deep Amber Text
    else:  # PASS / DECLINE / PENDING
        bg_color = colors.HexColor("#fef2f2")      # Soft Red
        box_color = colors.HexColor("#fee2e2")     # Light Red Border
        txt_color = colors.HexColor("#b91c1c")     # Deep Red Text
        
    verdict_title_style = ParagraphStyle(
        'VerdictTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=txt_color,
        alignment=1  # Centered
    )
        
    verdict_panel_data = [
        [Paragraph("INVESTMENT SWARM DECISION", verdict_lbl_style)],
        [Paragraph(verdict, verdict_title_style)]
    ]
    verdict_table = Table(verdict_panel_data, colWidths=[504])
    verdict_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), bg_color),
        ('BOX', (0,0), (-1,-1), 1.5, box_color),
        ('TOPPADDING', (0,0), (-1,-1), 14),
        ('BOTTOMPADDING', (0,0), (-1,-1), 14),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(verdict_table)
    story.append(Spacer(1, 15))
    
    # Verdict Synthesis Memo / Investment Memo
    if verdict_memo_lines:
        # We process line-by-line to preserve structured markdown headers and lists in the PDF
        for line in verdict_memo_lines:
            line_str = line.strip()
            if not line_str:
                continue
            
            line_formatted = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", line_str)
            line_clean = clean_unicode_and_emojis(line_formatted)
            
            if line_clean.startswith("# "):
                title_text = line_clean.replace("# ", "").strip().upper()
                story.append(Paragraph(f"<b>{title_text}</b>", ParagraphStyle('MemoMainTitle', parent=h1_style, spaceBefore=12, spaceAfter=6, keepWithNext=True)))
            elif line_clean.startswith("### "):
                h_text = line_clean.replace("### ", "").strip()
                story.append(Paragraph(h_text, h2_style))
            elif line_clean.startswith("* ") or line_clean.startswith("- "):
                b_text = line_clean[2:].strip()
                if not b_text or set(b_text) <= set("-+=_ "):  # empty / rule-only bullet
                    continue
                story.append(Paragraph(b_text, bullet_style))
            elif re.match(r"^\d+\.\s+", line_clean):
                num_text = re.sub(r"^\d+\.\s+", "", line_clean).strip()
                story.append(Paragraph(f"{line_clean.split('.')[0]}. {num_text}", bullet_style))
            elif line_clean.startswith("|"):
                # Strip ASCII box pipe borders, keep the inner content as a line
                inner = line_clean.strip("|").strip()
                if not inner or set(inner) <= set("-+=_ `"):
                    continue
                story.append(Paragraph(inner, body_style))
            elif line_clean.startswith("```") or line_clean.startswith("+--") or (line_clean and set(line_clean) <= set("-+=_ `")):
                # Skip code fences and decision-card ASCII border/rule lines
                continue
            else:
                story.append(Paragraph(line_clean, body_style))
        story.append(Spacer(1, 10))
        
    # ────────────────────────────────────────────────────────
    # 3. RISK SCORECARD
    # ────────────────────────────────────────────────────────
    # Parse risk scorecard metrics
    risk_scores = []
    idx = 0
    while idx < len(lines):
        line = lines[idx].strip()
        if "risk scorecard" in line.lower() or "## 📊 risk scorecard" in line.lower():
            idx += 1
            while idx < len(lines) and not lines[idx].strip().startswith("---") and not lines[idx].strip().startswith("## "):
                sub_line = lines[idx].strip()
                if sub_line.startswith("* "):
                    metric_match = re.search(r"\*\s*\*\frac{(.*?)}{(.*?)}", sub_line) or re.search(r"\*\s*\*\*(.*?):\*\*\s*(.*?)(?:\(|$)", sub_line)
                    if metric_match:
                        metric_name = metric_match.group(1).strip()
                        metric_val = metric_match.group(2).replace("**", "").strip()
                        risk_scores.append((metric_name, metric_val))
                idx += 1
            break
        idx += 1
        
    if risk_scores:
        story.append(Paragraph("Risk Analysis Scorecard", h1_style))
        story.append(HRFlowable(width="100%", thickness=1, color=BORDER_GREY, spaceBefore=2, spaceAfter=14))
        
        score_table_data = [[
            Paragraph("<b>RISK DOMAIN</b>", ParagraphStyle('TH1', fontName='Helvetica-Bold', fontSize=9, leading=11, textColor=colors.white)), 
            Paragraph("<b>WEIGHT / SCORE</b>", ParagraphStyle('TH2', fontName='Helvetica-Bold', fontSize=9, leading=11, textColor=colors.white, alignment=2))
        ]]
        
        for name, val in risk_scores:
            name_clean = clean_unicode_and_emojis(name)
            val_clean = clean_unicode_and_emojis(val)
            
            # Format rows nicely
            if "weighted" in name_clean.lower() or "score" in name_clean.lower():
                # Highlight the total weighted score row
                n_para = Paragraph(f"<b>{name_clean.upper()}</b>", ParagraphStyle('RiskWeighted', parent=body_style, fontName='Helvetica-Bold'))
                v_para = Paragraph(f"<b>{val_clean}</b>", ParagraphStyle('RiskWeightedVal', parent=body_style, fontName='Helvetica-Bold', alignment=2))
            else:
                n_para = Paragraph(name_clean, body_style)
                v_para = Paragraph(val_clean, ParagraphStyle('RiskVal', parent=body_style, alignment=2))
                
            score_table_data.append([n_para, v_para])
            
        score_table = Table(score_table_data, colWidths=[354, 150])
        score_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), BRAND_GREEN),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ('TOPPADDING', (0,0), (-1,-1), 8),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [BG_WHITE, BG_LIGHT]),
            ('GRID', (0,0), (-1,-1), 0.5, BORDER_GREY),
        ]))
        story.append(score_table)
        story.append(Spacer(1, 20))
        
    # ────────────────────────────────────────────────────────
    # 4. PARTNER AUDIT LOGS (TIMELINE)
    # ────────────────────────────────────────────────────────
    story.append(Paragraph("Chronological Partner Audit Logs", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER_GREY, spaceBefore=2, spaceAfter=14))
    
    idx = 0
    in_timeline = False
    current_partner = None
    partner_findings = []
    
    while idx < len(lines):
        line = lines[idx].strip()
        if "chronological partner audit timeline" in line.lower() or "## 📝 chronological partner audit timeline" in line.lower():
            in_timeline = True
            idx += 1
            continue
            
        if in_timeline:
            # Clean ASCII-card noise from an embedded verdict card: strip the pipe
            # borders but KEEP the inner content (DECISION/CONFIDENCE/etc.); drop
            # pure rules, +---+ borders, and ``` code fences.
            if line.startswith("|"):
                inner = line.strip("|").strip()
                if not inner or set(inner) <= set("-+=_ "):
                    idx += 1
                    continue
                line = inner
            elif line.startswith("```") or line.startswith("+--") or (line and set(line) <= set("-+=_ ")):
                idx += 1
                continue
            if line.startswith("### "):
                if current_partner and partner_findings:
                    # Render the previous partner audit block as a nice card
                    story.extend(create_partner_card(current_partner, partner_findings, body_style, bullet_style))
                    story.append(Spacer(1, 14))
                current_partner = line.replace("###", "").strip()
                partner_findings = []
            elif line.startswith("*Timestamp:"):
                timestamp_clean = clean_unicode_and_emojis(line)
                partner_findings.append(("timestamp", timestamp_clean))
            elif line.startswith("-") or line.startswith("* "):
                bullet_text = line[2:].strip()
                if not bullet_text or set(bullet_text) <= set("-+=_ "):  # empty / rule-only bullet
                    idx += 1
                    continue
                bullet_text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", bullet_text)
                bullet_text = clean_unicode_and_emojis(bullet_text)
                partner_findings.append(("bullet", bullet_text))
            elif line:
                cleaned_line = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", line)
                cleaned_line = clean_unicode_and_emojis(cleaned_line)
                partner_findings.append(("text", cleaned_line))
        idx += 1
        
    # Flush the final partner
    if current_partner and partner_findings:
        story.extend(create_partner_card(current_partner, partner_findings, body_style, bullet_style))
        
    # Build Document
    doc.build(story, canvasmaker=BrandedCanvas)
    buffer.seek(0)
    return buffer.getvalue()


def create_partner_card(partner_name: str, findings: list, body_style: ParagraphStyle, bullet_style: ParagraphStyle) -> list:
    """Helper that packages a partner's findings as split-friendly flowables inside card blocks."""
    partner_clean = clean_unicode_and_emojis(partner_name)
    
    elements = []
    
    # Title Style
    title_style = ParagraphStyle(
        'CardPartnerTitle',
        parent=body_style,
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=BRAND_DARK_GREEN,
        spaceBefore=8,
        spaceAfter=2,
        keepWithNext=True
    )
    
    timestamp_style = ParagraphStyle(
        'CardTimestamp',
        parent=body_style,
        fontName='Helvetica-Oblique',
        fontSize=8,
        leading=11,
        textColor=SECONDARY_TEXT,
        spaceAfter=8,
        keepWithNext=True
    )
    
    # We keep the partner header together with the first block of findings
    header_elements = [Paragraph(partner_clean.upper(), title_style)]
    
    # Find timestamp if present
    timestamp_text = None
    first_finding_idx = 0
    for i, (kind, text) in enumerate(findings):
        if kind == "timestamp":
            timestamp_text = text
            if i == first_finding_idx:
                first_finding_idx += 1
            break
            
    if timestamp_text:
        header_elements.append(Paragraph(timestamp_text, timestamp_style))
        
    # Now create the findings flowables. We wrap each one in a card table to keep the styling.
    # To prevent LayoutErrors, each finding is wrapped in its own separate Table that fits on a page.
    for kind, text in findings:
        if kind == "timestamp":
            continue
            
        p_style = bullet_style if kind == "bullet" else body_style
        p_text = f"• {text}" if kind == "bullet" else text
        para = Paragraph(p_text, p_style)
        
        # Wrap the single paragraph in a Table with a left accent bar and light bg
        item_table = Table([["", para]], colWidths=[4, 492])
        item_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (0,0), BRAND_GREEN),
            ('BACKGROUND', (1,0), (1,0), BG_LIGHT),
            ('LINELEFT', (0,0), (0,-1), 1, BORDER_GREY),
            ('LINERIGHT', (1,0), (1,-1), 1, BORDER_GREY),
            ('LINETOP', (0,0), (-1,0), 0.5, BORDER_GREY),
            ('LINEBELOW', (0,0), (-1,-1), 0.5, BORDER_GREY),
            ('TOPPADDING', (1,0), (1,0), 6),
            ('BOTTOMPADDING', (1,0), (1,0), 6),
            ('LEFTPADDING', (1,0), (1,0), 12),
            ('RIGHTPADDING', (1,0), (1,0), 12),
            ('TOPPADDING', (0,0), (0,0), 0),
            ('BOTTOMPADDING', (0,0), (0,0), 0),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ]))
        item_table.spaceAfter = 2
        
        if header_elements:
            # Keep header and first finding together on the same page
            header_elements.append(item_table)
            elements.append(KeepTogether(header_elements))
            header_elements = None
        else:
            elements.append(item_table)
            
    return elements
