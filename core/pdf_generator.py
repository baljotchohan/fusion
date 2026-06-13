# core/pdf_generator.py
"""
PDF Report Generator — compiles markdown due diligence reports into
professional, publication-quality PDF documents using ReportLab.
"""
import io
import re
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

# FUSION Brand Colors
BRAND_GREEN = colors.HexColor("#4fae47")  # FUSION green
DARK_TEXT = colors.HexColor("#1c1c1e")
SECONDARY_TEXT = colors.HexColor("#52525b")
BORDER_GREY = colors.HexColor("#e4e4e7")
BG_LIGHT = colors.HexColor("#fafafa")

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
        
        # Suppress headers/footers on page 1 (cover page) if total pages > 1
        if self._pageNumber == 1 and total_pages > 1:
            self.restoreState()
            return
            
        # Draw Running Header
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(BRAND_GREEN)
        self.drawString(54, 750, "FUSION due diligence audit report")
        
        self.setFont("Helvetica", 8)
        self.setFillColor(SECONDARY_TEXT)
        self.drawRightString(612 - 54, 750, "CONFIDENTIAL")
        
        self.setStrokeColor(BORDER_GREY)
        self.setLineWidth(0.5)
        self.line(54, 742, 612 - 54, 742)
        
        # Draw Running Footer
        self.line(54, 55, 612 - 54, 55)
        self.drawString(54, 42, "FUSION Investment Committee Swarm")
        self.drawRightString(612 - 54, 42, f"Page {self._pageNumber} of {total_pages}")
        
        self.restoreState()


def compile_pdf_report(report_md: str, company_name: str) -> bytes:
    """Parses FUSION diligence report markdown and compiles it into a styled PDF.

    Returns:
        bytes: Raw PDF file bytes.
    """
    buffer = io.BytesIO()
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
    title_style = ParagraphStyle(
        'CoverTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=26,
        leading=32,
        textColor=DARK_TEXT,
        spaceAfter=12
    )
    
    subtitle_style = ParagraphStyle(
        'CoverSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=BRAND_GREEN,
        spaceAfter=30
    )
    
    h1_style = ParagraphStyle(
        'Header1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=DARK_TEXT,
        spaceBefore=18,
        spaceAfter=8,
        keepWithNext=True
    )
    
    h2_style = ParagraphStyle(
        'Header2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=BRAND_GREEN,
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14.5,
        textColor=DARK_TEXT,
        spaceAfter=10
    )
    
    bullet_style = ParagraphStyle(
        'BulletCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14.5,
        textColor=DARK_TEXT,
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=6
    )
    
    meta_style = ParagraphStyle(
        'MetadataText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=SECONDARY_TEXT
    )

    verdict_invest_style = ParagraphStyle(
        'VerdictInvest',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#2e9e3a"),
        alignment=1  # Centered
    )
    
    verdict_conditional_style = ParagraphStyle(
        'VerdictConditional',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#d97706"),
        alignment=1
    )
    
    verdict_pass_style = ParagraphStyle(
        'VerdictPass',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#dc2626"),
        alignment=1
    )

    story = []
    
    # ── Parse markdown sections ──
    # Clean header signs
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
        
    # Cover / Header block
    story.append(Paragraph("FUSION DUE DILIGENCE REPORT", title_style))
    story.append(Paragraph(f"Target Company: {company_name}", subtitle_style))
    
    # Metadata block
    meta_table_data = [
        [Paragraph(f"<b>Deal Record:</b> {deal_record}", meta_style), 
         Paragraph(f"<b>Date Evaluated:</b> {date_evaluated}", meta_style)]
    ]
    meta_table = Table(meta_table_data, colWidths=[250, 250])
    meta_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 25))
    
    # Verdict Panel
    verdict_para_style = verdict_pass_style
    if verdict == "INVEST":
        verdict_para_style = verdict_invest_style
    elif verdict == "CONDITIONAL":
        verdict_para_style = verdict_conditional_style
        
    verdict_panel_data = [
        [Paragraph("COMMITTEE VERDICT", ParagraphStyle('VP', fontName='Helvetica-Bold', fontSize=10, textColor=SECONDARY_TEXT, alignment=1))],
        [Paragraph(verdict, verdict_para_style)]
    ]
    verdict_table = Table(verdict_panel_data, colWidths=[500])
    verdict_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), BG_LIGHT),
        ('BOX', (0,0), (-1,-1), 1, BORDER_GREY),
        ('TOPPADDING', (0,0), (-1,-1), 16),
        ('BOTTOMPADDING', (0,0), (-1,-1), 16),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ]))
    story.append(verdict_table)
    story.append(Spacer(1, 15))
    
    # Verdict Synthesis Memo
    if verdict_memo_lines:
        story.append(Paragraph("Verdict Synthesis Memo", h2_style))
        memo_text = " ".join(verdict_memo_lines)
        # Clean markdown bold/italics
        memo_text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", memo_text)
        story.append(Paragraph(memo_text, body_style))
        story.append(Spacer(1, 15))
        
    # Parse risk scorecard
    risk_scores = []
    idx = 0
    while idx < len(lines):
        line = lines[idx].strip()
        if "risk scorecard" in line.lower() or "## 📊 risk scorecard" in line.lower():
            idx += 1
            while idx < len(lines) and not lines[idx].strip().startswith("---") and not lines[idx].strip().startswith("## "):
                sub_line = lines[idx].strip()
                if sub_line.startswith("* "):
                    metric_match = re.search(r"\*\s*\*\*(.*?):\*\*\s*(.*?)(?:\(|$)", sub_line)
                    if metric_match:
                        metric_name = metric_match.group(1).strip()
                        metric_val = metric_match.group(2).replace("**", "").strip()
                        risk_scores.append((metric_name, metric_val))
                idx += 1
            break
        idx += 1
        
    if risk_scores:
        story.append(Paragraph("Risk Scorecard", h1_style))
        score_table_data = [[Paragraph("<b>Risk Domain</b>", meta_style), Paragraph("<b>Score</b>", meta_style)]]
        for name, val in risk_scores:
            bold_val = f"<b>{val}</b>" if "weighted" in name.lower() or "score" in name.lower() else val
            score_table_data.append([Paragraph(name, body_style), Paragraph(bold_val, body_style)])
            
        score_table = Table(score_table_data, colWidths=[350, 150])
        score_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), BG_LIGHT),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('LINEBELOW', (0,0), (-1,-1), 0.5, BORDER_GREY),
        ]))
        story.append(score_table)
        story.append(Spacer(1, 20))
        
    # Chronological Audit Timeline
    story.append(Paragraph("Chronological Partner Audit Timeline", h1_style))
    
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
                    # Flush previous partner
                    story.append(KeepTogether([
                        Paragraph(current_partner, h2_style),
                        Paragraph(" ".join(partner_findings), body_style)
                    ]))
                    story.append(Spacer(1, 10))
                current_partner = line.replace("###", "").strip()
                partner_findings = []
            elif line.startswith("*Timestamp:"):
                # Append timestamp as a small line
                partner_findings.append(f"<i>({line})</i><br/><br/>")
            elif line.startswith("-") or line.startswith("* "):
                # bullet points
                bullet_text = line[2:].strip()
                bullet_text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", bullet_text)
                partner_findings.append(f"• {bullet_text}<br/>")
            elif line:
                cleaned_line = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", line)
                partner_findings.append(cleaned_line)
        idx += 1
        
    # Flush last partner
    if current_partner and partner_findings:
        story.append(KeepTogether([
            Paragraph(current_partner, h2_style),
            Paragraph(" ".join(partner_findings), body_style)
        ]))
        
    # Build Document
    doc.build(story, canvasmaker=BrandedCanvas)
    buffer.seek(0)
    return buffer.getvalue()
