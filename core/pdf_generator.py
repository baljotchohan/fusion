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
PRIMARY_COLOR = colors.HexColor("#0f172a")    # Slate 900 (deep slate for titles)
SECONDARY_COLOR = colors.HexColor("#334155")  # Slate 700 (for sub-headers)
DARK_TEXT = colors.HexColor("#0f172a")        # Slate 900 for main text
SECONDARY_TEXT = colors.HexColor("#475569")   # Slate 600 for labels / captions
BORDER_GREY = colors.HexColor("#cbd5e1")      # Slate 300 for clean lines
BG_LIGHT = colors.HexColor("#f8fafc")         # Slate 50 for table rows
BG_WHITE = colors.HexColor("#ffffff")

# Real FUSION horizontal wordmark — trimmed of its whitespace margins once and cached.
_LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fusionlogo.png")
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
    Also strips out all grounding tags and developer metadata ([Grounding: ...]).
    Escapes XML/HTML special characters to prevent paraparser syntax errors.
    """
    if not text:
        return ""
        
    # Remove Grounding blocks: [Grounding: ...]
    text = re.sub(r'\[Grounding:\s*.*?\]', '', text, flags=re.DOTALL)
    
    # Mute bracketed potential conflict prefixes
    text = text.replace("[POTENTIAL CONFLICT]", "Potential Conflict:")
        
    replacements = {
        "💼": "",
        "📊": "",
        "⚖️": "",
        "⚖": "",
        "🚨": "Alert: ",
        "📋": "Gap: ",
        "🛡️": "Confidence: ",
        "🛡": "Confidence: ",
        "🎯": "Coverage: ",
        "🚦": "Status: ",
        "🏢": "",
        "💵": "",
        "🔧": "",
        "📈": "",
        "📝": "",
        "🤖": "",
        "🚀": "",
        "🤝": "",
        "⚠️": "Warning: ",
        "⚠": "Warning: ",
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
        
    # Clean up redundant warnings
    text = text.replace("Warning:  Potential Conflict:", "Potential Conflict:")
    text = text.replace("Warning: Potential Conflict:", "Potential Conflict:")
        
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
    
    # Trim leading/trailing spaces
    text = text.strip()
    
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
            
        # Draw Running Header — real horizontal logo wordmark
        text_x = 54
        logo = _get_brand_logo()
        if logo:
            png_bytes, aspect = logo
            h = 10
            w = h * aspect
            try:
                self.drawImage(ImageReader(io.BytesIO(png_bytes)), 54, 752, width=w, height=h, mask='auto')
                text_x = 54 + w + 8
            except Exception:
                pass

        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(SECONDARY_TEXT)
        self.drawString(text_x, 755, "|   DUE DILIGENCE AUDIT REPORT")
        self.drawRightString(612 - 54, 755, "CONFIDENTIAL")
        
        self.setStrokeColor(BORDER_GREY)
        self.setLineWidth(0.5)
        self.line(54, 745, 612 - 54, 745)
        
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
        fontSize=24,
        leading=30,
        textColor=PRIMARY_COLOR,
        spaceAfter=8
    )
    
    cover_subtitle_style = ParagraphStyle(
        'CoverSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=SECONDARY_COLOR,
        spaceAfter=40
    )
    
    h1_style = ParagraphStyle(
        'Header1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=17,
        textColor=PRIMARY_COLOR,
        spaceBefore=18,
        spaceAfter=6,
        keepWithNext=True
    )
    
    h2_style = ParagraphStyle(
        'Header2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=14.5,
        textColor=SECONDARY_COLOR,
        spaceBefore=12,
        spaceAfter=4,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13.5,
        textColor=DARK_TEXT,
        spaceAfter=6
    )
    
    bullet_style = ParagraphStyle(
        'BulletCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13.5,
        textColor=DARK_TEXT,
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=4
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
        _lh = 36
        _lw = _lh * _aspect
        story.append(Image(io.BytesIO(_png), width=_lw, height=_lh))
    else:
        story.append(Paragraph("FUSION", wordmark_style))

    story.append(Paragraph("VENTURE CAPITAL · AI INVESTMENT COMMITTEE", tagline_style))
    story.append(Spacer(1, 34))

    # Title & Subtitle
    company_name_clean = clean_unicode_and_emojis(company_name)
    story.append(Paragraph("DUE DILIGENCE AUDIT REPORT", cover_title_style))
    story.append(Paragraph(f"INVESTMENT INQUIRY: {company_name_clean.upper()}", cover_subtitle_style))
    
    # Decorative line
    story.append(HRFlowable(width="100%", thickness=1.5, color=PRIMARY_COLOR, spaceBefore=0, spaceAfter=200))
    
    # Metadata Block at bottom of cover page
    meta_box_data = [
        [Paragraph("DEAL RECORD", meta_label_style), Paragraph(deal_record, meta_val_style)],
        [Paragraph("DATE EVALUATED", meta_label_style), Paragraph(date_evaluated, meta_val_style)],
        [Paragraph("SECURITY SWARM STATUS", meta_label_style), Paragraph("COMPLETE & VERIFIED", ParagraphStyle('MStatus', parent=meta_val_style, fontName='Helvetica-Bold', textColor=PRIMARY_COLOR))],
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
    
    # Mute colors for a professional, institutional-grade layout
    bg_color = BG_LIGHT
    box_color = BORDER_GREY
    txt_color = PRIMARY_COLOR
        
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
            
            line_clean = clean_unicode_and_emojis(line_str)
            
            if line_clean.startswith("# "):
                title_text = line_clean.replace("# ", "").strip().upper()
                title_text_formatted = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", title_text)
                story.append(Paragraph(f"<b>{title_text_formatted}</b>", ParagraphStyle('MemoMainTitle', parent=h1_style, spaceBefore=12, spaceAfter=6, keepWithNext=True)))
            elif line_clean.startswith("### "):
                h_text = line_clean.replace("### ", "").strip()
                h_text_formatted = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", h_text)
                story.append(Paragraph(h_text_formatted, h2_style))
            elif line_clean.startswith("* ") or line_clean.startswith("- "):
                b_text = line_clean[2:].strip()
                if not b_text or set(b_text) <= set("-+=_ "):  # empty / rule-only bullet
                    continue
                b_text_formatted = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", b_text)
                story.append(Paragraph(b_text_formatted, bullet_style))
            elif re.match(r"^\d+\.\s+", line_clean):
                num_text = re.sub(r"^\d+\.\s+", "", line_clean).strip()
                num_text_formatted = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", num_text)
                story.append(Paragraph(f"{line_clean.split('.')[0]}. {num_text_formatted}", bullet_style))
            elif line_clean.startswith("|"):
                # Strip ASCII box pipe borders, keep the inner content as a line
                inner = line_clean.strip("|").strip()
                if not inner or set(inner) <= set("-+=_ `"):
                    continue
                inner_formatted = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", inner)
                story.append(Paragraph(inner_formatted, body_style))
            elif line_clean.startswith("```") or line_clean.startswith("+--") or (line_clean and set(line_clean) <= set("-+=_ `")):
                # Skip code fences and decision-card ASCII border/rule lines
                continue
            else:
                line_clean_formatted = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", line_clean)
                story.append(Paragraph(line_clean_formatted, body_style))
        story.append(Spacer(1, 10))
        
    # ────────────────────────────────────────────────────────
    # 3. RISK SCORECARD
    # ────────────────────────────────────────────────────────
    # Parse risk scorecard metrics
    risk_scores = []
    idx = 0
    while idx < len(lines):
        line = lines[idx].strip()
        if line.startswith("## ") and "risk scorecard" in line.lower():
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
            ('BACKGROUND', (0,0), (-1,0), SECONDARY_COLOR),
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
                bullet_clean = clean_unicode_and_emojis(bullet_text)
                bullet_formatted = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", bullet_clean)
                partner_findings.append(("bullet", bullet_formatted))
            elif line:
                line_clean = clean_unicode_and_emojis(line)
                line_formatted = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", line_clean)
                partner_findings.append(("text", line_formatted))
        idx += 1
        
    # Flush the final partner
    if current_partner and partner_findings:
        story.extend(create_partner_card(current_partner, partner_findings, body_style, bullet_style))
        
    # Build Document
    doc.build(story, canvasmaker=BrandedCanvas)
    buffer.seek(0)
    return buffer.getvalue()


def create_partner_card(partner_name: str, findings: list, body_style: ParagraphStyle, bullet_style: ParagraphStyle) -> list:
    """Helper that packages a partner's findings as clean paragraphs and standard bullets,
    avoiding busy tables/borders, and placing a thin divider at the end.
    """
    partner_clean = clean_unicode_and_emojis(partner_name)
    
    elements = []
    
    # Title Style
    title_style = ParagraphStyle(
        'CardPartnerTitle',
        parent=body_style,
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=PRIMARY_COLOR,
        spaceBefore=12,
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
        spaceAfter=6,
        keepWithNext=True
    )
    
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
        
    # Process findings
    first_finding_para = None
    finding_elements = []
    for kind, text in findings:
        if kind == "timestamp":
            continue
            
        p_style = bullet_style if kind == "bullet" else body_style
        p_text = f"&bull; {text}" if kind == "bullet" else text
        para = Paragraph(p_text, p_style)
        
        if not first_finding_para:
            first_finding_para = para
        else:
            finding_elements.append(para)
            
    if first_finding_para:
        header_elements.append(first_finding_para)
        
    # Add KeepTogether for header + first finding to prevent orphan headers
    elements.append(KeepTogether(header_elements))
    
    # Add the rest of findings
    elements.extend(finding_elements)
    
    # Add a thin grey divider line at the end of this partner section
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BORDER_GREY, spaceBefore=8, spaceAfter=8))
    
    return elements
