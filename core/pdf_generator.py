# core/pdf_generator.py
"""
PDF Report Generator — compiles markdown due diligence reports into
professional, publication-quality PDF documents using ReportLab.
"""
import io
import re
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

# FUSION Brand Colors
BRAND_GREEN = colors.HexColor("#4fae47")  # FUSION green
BRAND_DARK_GREEN = colors.HexColor("#3d8b36")
DARK_TEXT = colors.HexColor("#18181b")    # Slate 900
SECONDARY_TEXT = colors.HexColor("#71717a") # Slate 500
BORDER_GREY = colors.HexColor("#e4e4e7")    # Slate 200
BG_LIGHT = colors.HexColor("#f8fafc")       # Slate 50
BG_WHITE = colors.HexColor("#ffffff")

def clean_unicode_and_emojis(text: str) -> str:
    """Replaces emojis and unsupported high-Unicode characters with safe representations
    or strips them to prevent ReportLab rendering/encoding exceptions.
    """
    if not text:
        return ""
        
    replacements = {
        "💼": "",
        "📊": "",
        "⚖️": "",
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
    }
    
    for emoji, replacement in replacements.items():
        text = text.replace(emoji, replacement)
        
    # Standard Helvetica supports Latin-1 characters (up to codepoint 255).
    # We strip out any character beyond 255 to ensure zero compilation errors,
    # but we preserve standard HTML tags used in Paragraphs (like <b>, <i>, <br/>).
    cleaned = []
    for char in text:
        if ord(char) <= 255:
            cleaned.append(char)
        else:
            # Skip high unicode characters to avoid 'latin-1' encoding crashes
            pass
            
    return "".join(cleaned)


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
            
        # Draw Running Header
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(BRAND_DARK_GREEN)
        self.drawString(54, 755, "FUSION VENTURE CAPITAL")
        
        self.setFont("Helvetica", 8)
        self.setFillColor(SECONDARY_TEXT)
        self.drawString(175, 755, "|   DUE DILIGENCE AUDIT REPORT")
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
    story.append(Spacer(1, 100))
    
    # Top Logo Accent
    logo_data = [[
        Paragraph("<b>F U S I O N</b>", ParagraphStyle('LogoText', fontName='Helvetica-Bold', fontSize=12, leading=14, textColor=colors.white))
    ]]
    logo_table = Table(logo_data, colWidths=[80], rowHeights=[24])
    logo_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), BRAND_GREEN),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(logo_table)
    story.append(Spacer(1, 20))
    
    # Title & Subtitle
    story.append(Paragraph("DUE DILIGENCE AUDIT REPORT", cover_title_style))
    story.append(Paragraph(f"INVESTMENT INQUIRY: {company_name.upper()}", cover_subtitle_style))
    
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
    
    # Verdict Synthesis Memo
    if verdict_memo_lines:
        story.append(Paragraph("Verdict Synthesis Memo", h2_style))
        memo_text = " ".join(verdict_memo_lines)
        memo_text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", memo_text)
        memo_text = clean_unicode_and_emojis(memo_text)
        story.append(Paragraph(memo_text, body_style))
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
            if line.startswith("### "):
                if current_partner and partner_findings:
                    # Render the previous partner audit block as a nice card
                    story.append(create_partner_card(current_partner, partner_findings, body_style, bullet_style))
                    story.append(Spacer(1, 14))
                current_partner = line.replace("###", "").strip()
                partner_findings = []
            elif line.startswith("*Timestamp:"):
                timestamp_clean = clean_unicode_and_emojis(line)
                partner_findings.append(("timestamp", timestamp_clean))
            elif line.startswith("-") or line.startswith("* "):
                bullet_text = line[2:].strip()
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
        story.append(create_partner_card(current_partner, partner_findings, body_style, bullet_style))
        
    # Build Document
    doc.build(story, canvasmaker=BrandedCanvas)
    buffer.seek(0)
    return buffer.getvalue()


def create_partner_card(partner_name: str, findings: list, body_style: ParagraphStyle, bullet_style: ParagraphStyle) -> KeepTogether:
    """Helper that packages a partner's findings inside a beautiful bordered table card."""
    partner_clean = clean_unicode_and_emojis(partner_name)
    
    card_elements = []
    
    # Title Style
    title_style = ParagraphStyle(
        'CardPartnerTitle',
        parent=body_style,
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=BRAND_DARK_GREEN,
        spaceAfter=2
    )
    
    timestamp_style = ParagraphStyle(
        'CardTimestamp',
        parent=body_style,
        fontName='Helvetica-Oblique',
        fontSize=8,
        leading=11,
        textColor=SECONDARY_TEXT,
        spaceAfter=8
    )
    
    card_elements.append(Paragraph(partner_clean.upper(), title_style))
    
    # Separate findings
    for kind, text in findings:
        if kind == "timestamp":
            card_elements.append(Paragraph(text, timestamp_style))
        elif kind == "bullet":
            card_elements.append(Paragraph(f"• {text}", bullet_style))
        else:
            card_elements.append(Paragraph(text, body_style))
            
    # Put them inside a Table card with a left green accent line
    # Left column is the green accent line (width 4pt)
    # Right column is the content (width 490pt)
    card_table_data = [
        ["", card_elements]
    ]
    card_table = Table(card_table_data, colWidths=[4, 492])
    card_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,0), BRAND_GREEN),
        ('BACKGROUND', (1,0), (1,0), BG_LIGHT),
        ('BOX', (0,0), (-1,-1), 1, BORDER_GREY),
        ('TOPPADDING', (1,0), (1,0), 12),
        ('BOTTOMPADDING', (1,0), (1,0), 12),
        ('LEFTPADDING', (1,0), (1,0), 14),
        ('RIGHTPADDING', (1,0), (1,0), 14),
        ('TOPPADDING', (0,0), (0,0), 0),
        ('BOTTOMPADDING', (0,0), (0,0), 0),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    
    # We want to keep the header and first few lines of the card together
    return KeepTogether([card_table])
