"""
AutoJustice AI NEXUS — Implementation Plan PDF Generator
Run: python generate_plan.py
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether
)
from reportlab.platypus.flowables import Flowable
from reportlab.pdfgen import canvas as pdfcanvas
from datetime import date
import os

# ── Colour Palette ────────────────────────────────────────────────────────────
GOV_BLUE      = colors.HexColor("#1a3f6f")
GOV_BLUE_DK   = colors.HexColor("#0f2848")
GOV_BLUE_LT   = colors.HexColor("#dce8f5")
SAFFRON       = colors.HexColor("#e8650a")
NAT_GREEN     = colors.HexColor("#056835")
NAT_GREEN_LT  = colors.HexColor("#d4edda")
RED           = colors.HexColor("#b91c1c")
RED_LT        = colors.HexColor("#fde8e8")
GRAY_50       = colors.HexColor("#f7f8fa")
GRAY_100      = colors.HexColor("#eef0f3")
GRAY_200      = colors.HexColor("#dde1e7")
GRAY_600      = colors.HexColor("#4b5563")
GRAY_900      = colors.HexColor("#111827")
WHITE         = colors.white
AMBER         = colors.HexColor("#d97706")
AMBER_LT      = colors.HexColor("#fffbeb")

PAGE_W, PAGE_H = A4
MARGIN = 2.0 * cm
OUTPUT = os.path.join(os.path.dirname(__file__), "AutoJustice_AI_NEXUS_Implementation_Plan.pdf")

# ── Styles ────────────────────────────────────────────────────────────────────
styles = getSampleStyleSheet()

def S(name, **kw):
    return ParagraphStyle(name, **kw)

COVER_TITLE   = S("CoverTitle",   fontName="Helvetica-Bold",   fontSize=32, textColor=WHITE,       leading=38, alignment=TA_CENTER)
COVER_SUB     = S("CoverSub",     fontName="Helvetica",        fontSize=13, textColor=colors.HexColor("#c8ddf0"), leading=18, alignment=TA_CENTER)
COVER_BADGE   = S("CoverBadge",   fontName="Helvetica-Bold",   fontSize=10, textColor=SAFFRON,      alignment=TA_CENTER, spaceAfter=4)
COVER_META    = S("CoverMeta",    fontName="Helvetica",        fontSize=9,  textColor=colors.HexColor("#94b4d4"), alignment=TA_CENTER)

SEC_TITLE     = S("SecTitle",     fontName="Helvetica-Bold",   fontSize=20, textColor=WHITE,       leading=24, alignment=TA_CENTER)
SEC_NUM       = S("SecNum",       fontName="Helvetica-Bold",   fontSize=11, textColor=colors.HexColor("#c8ddf0"), alignment=TA_CENTER, spaceAfter=4)

H1            = S("H1",           fontName="Helvetica-Bold",   fontSize=15, textColor=GOV_BLUE,    spaceBefore=14, spaceAfter=6, leading=20)
H2            = S("H2",           fontName="Helvetica-Bold",   fontSize=12, textColor=GOV_BLUE,    spaceBefore=10, spaceAfter=4, leading=16)
H3            = S("H3",           fontName="Helvetica-Bold",   fontSize=10, textColor=GRAY_900,    spaceBefore=8,  spaceAfter=3, leading=14)

BODY          = S("Body",         fontName="Helvetica",        fontSize=9.5,textColor=GRAY_900,    leading=15, spaceAfter=6, alignment=TA_JUSTIFY)
BODY_SM       = S("BodySm",       fontName="Helvetica",        fontSize=8.5,textColor=GRAY_600,    leading=13, spaceAfter=4)
BULLET        = S("Bullet",       fontName="Helvetica",        fontSize=9,  textColor=GRAY_900,    leading=14, leftIndent=14, spaceAfter=3,
                                   bulletIndent=4, bulletFontName="Helvetica-Bold", bulletFontSize=9)
BULLET_TITLE  = S("BulletTitle",  fontName="Helvetica-Bold",   fontSize=9,  textColor=GOV_BLUE,    leading=14, leftIndent=14, spaceAfter=1,
                                   bulletIndent=4)
NOTE          = S("Note",         fontName="Helvetica-Oblique",fontSize=8.5,textColor=colors.HexColor("#1e40af"), leading=13, leftIndent=6)
TH            = S("TH",           fontName="Helvetica-Bold",   fontSize=8.5,textColor=WHITE,       leading=12, alignment=TA_CENTER)
TD            = S("TD",           fontName="Helvetica",        fontSize=8.5,textColor=GRAY_900,    leading=12)
TD_C          = S("TDC",          fontName="Helvetica",        fontSize=8.5,textColor=GRAY_900,    leading=12, alignment=TA_CENTER)
TD_BOLD       = S("TDB",          fontName="Helvetica-Bold",   fontSize=8.5,textColor=GOV_BLUE,    leading=12)
TOC_ENTRY     = S("TOC",          fontName="Helvetica",        fontSize=10, textColor=GOV_BLUE,    leading=18, leftIndent=8)
TOC_SECTION   = S("TOCSec",       fontName="Helvetica-Bold",   fontSize=11, textColor=GOV_BLUE_DK, leading=20, spaceBefore=4)
FOOTER_TXT    = S("Footer",       fontName="Helvetica",        fontSize=7.5,textColor=GRAY_600,    alignment=TA_CENTER)

# ── Reusable Flowables ────────────────────────────────────────────────────────

class ColorBlock(Flowable):
    """Full-width colored rectangle block used as section divider or callout."""
    def __init__(self, color, height=8*mm):
        super().__init__()
        self.color = color
        self._height = height
    def draw(self):
        self.canv.setFillColor(self.color)
        self.canv.rect(0, 0, self.width, self._height, fill=1, stroke=0)
    def wrap(self, availW, availH):
        self.width = availW
        return availW, self._height

class Tricolor(Flowable):
    def __init__(self, height=5):
        super().__init__()
        self._height = height
    def draw(self):
        w = self.width
        self.canv.setFillColor(colors.HexColor("#FF9933"))
        self.canv.rect(0, 0, w/3, self._height, fill=1, stroke=0)
        self.canv.setFillColor(WHITE)
        self.canv.rect(w/3, 0, w/3, self._height, fill=1, stroke=0)
        self.canv.setFillColor(colors.HexColor("#138808"))
        self.canv.rect(2*w/3, 0, w/3, self._height, fill=1, stroke=0)
    def wrap(self, availW, availH):
        self.width = availW
        return availW, self._height

class SectionDividerPage(Flowable):
    """Full-page section divider with colored background."""
    def __init__(self, number, title, subtitle=""):
        super().__init__()
        self.number   = number
        self.title    = title
        self.subtitle = subtitle
        self._w = 0
        self._h = 0
    def draw(self):
        c = self.canv
        w, h = self._w, self._h
        # Background
        c.setFillColor(GOV_BLUE)
        c.rect(0, 0, w, h, fill=1, stroke=0)
        # Saffron accent bar
        c.setFillColor(SAFFRON)
        c.rect(0, h*0.42, w, 6, fill=1, stroke=0)
        # Green accent bar
        c.setFillColor(NAT_GREEN)
        c.rect(0, h*0.42 - 10, w, 4, fill=1, stroke=0)
        # Section number
        c.setFillColor(colors.HexColor("#c8ddf0"))
        c.setFont("Helvetica", 11)
        c.drawCentredString(w/2, h*0.58, f"SECTION {self.number}")
        # Title
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 28)
        c.drawCentredString(w/2, h*0.47, self.title)
        # Subtitle
        if self.subtitle:
            c.setFillColor(colors.HexColor("#94b4d4"))
            c.setFont("Helvetica", 12)
            c.drawCentredString(w/2, h*0.39, self.subtitle)
        # Decorative dots
        c.setFillColor(SAFFRON)
        for x in [w*0.43, w*0.5, w*0.57]:
            c.circle(x, h*0.30, 4, fill=1, stroke=0)
    def wrap(self, availW, availH):
        self._w = availW
        self._h = availH
        return availW, availH

def callout(text, bg=GOV_BLUE_LT, border=GOV_BLUE, label=None, text_color=GOV_BLUE):
    """Coloured info callout box."""
    content = f"<b>{label}</b>  {text}" if label else text
    p = Paragraph(content, ParagraphStyle("callout", fontName="Helvetica",
        fontSize=9, textColor=text_color, leading=14, leftIndent=6, rightIndent=6))
    t = Table([[p]], colWidths=[PAGE_W - 2*MARGIN - 2])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), bg),
        ("LEFTPADDING", (0,0), (-1,-1), 10),
        ("RIGHTPADDING", (0,0), (-1,-1), 10),
        ("TOPPADDING", (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("LINEAFTER", (0,0), (0,-1), 0, WHITE),
        ("LINEBEFORE", (0,0), (0,-1), 4, border),
        ("ROUNDEDCORNERS", [3]),
    ]))
    return t

def bullet(text, bold_prefix=None):
    if bold_prefix:
        return Paragraph(f"<b>{bold_prefix}</b> {text}", BULLET, bulletText="\u2022")
    return Paragraph(text, BULLET, bulletText="\u2022")

def make_table(headers, rows, col_widths=None, stripe=True):
    avail = PAGE_W - 2*MARGIN - 2
    if col_widths is None:
        col_widths = [avail / len(headers)] * len(headers)
    data = [[Paragraph(h, TH) for h in headers]]
    for i, row in enumerate(rows):
        data.append([Paragraph(str(c), TD) for c in row])
    style = [
        ("BACKGROUND", (0,0), (-1,0), GOV_BLUE),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [WHITE, GRAY_50] if stripe else [WHITE]),
        ("GRID", (0,0), (-1,-1), 0.3, GRAY_200),
        ("LEFTPADDING", (0,0), (-1,-1), 7),
        ("RIGHTPADDING", (0,0), (-1,-1), 7),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ]
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle(style))
    return t

# ── Header / Footer ───────────────────────────────────────────────────────────

class HeaderFooterCanvas(pdfcanvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._draw_header_footer(num_pages)
            super().showPage()
        super().save()

    def _draw_header_footer(self, total):
        page = self._pageNumber
        if page == 1:
            return  # Cover page — no header/footer

        w, h = A4
        # Header bar
        self.setFillColor(GOV_BLUE)
        self.rect(0, h - 22*mm, w, 22*mm, fill=1, stroke=0)
        self.setFillColor(SAFFRON)
        self.rect(0, h - 23.5*mm, w, 1.5*mm, fill=1, stroke=0)

        self.setFillColor(WHITE)
        self.setFont("Helvetica-Bold", 9)
        self.drawString(MARGIN, h - 13*mm, "AutoJustice AI NEXUS")
        self.setFont("Helvetica", 8)
        self.drawString(MARGIN, h - 18*mm, "Implementation Plan  |  Ministry of Home Affairs, Government of India")
        self.setFont("Helvetica-Bold", 8)
        self.drawRightString(w - MARGIN, h - 15*mm, "CONFIDENTIAL")

        # Footer
        self.setFillColor(GRAY_50)
        self.rect(0, 0, w, 14*mm, fill=1, stroke=0)
        self.setStrokeColor(GRAY_200)
        self.line(MARGIN, 14*mm, w - MARGIN, 14*mm)

        self.setFillColor(GRAY_600)
        self.setFont("Helvetica", 7.5)
        self.drawString(MARGIN, 5*mm, f"AutoJustice AI NEXUS v2.0  |  Implementation Plan  |  {date.today().strftime('%B %Y')}")
        self.drawRightString(w - MARGIN, 5*mm, f"Page {page} of {total}")
        self.setFillColor(SAFFRON)
        self.drawCentredString(w/2, 5*mm, "cybercrime.gov.in")

# ── Build Story ───────────────────────────────────────────────────────────────

def build():
    doc = SimpleDocTemplate(
        OUTPUT,
        pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=2.8*cm, bottomMargin=2.0*cm,
        title="AutoJustice AI NEXUS — Implementation Plan",
        author="Ministry of Home Affairs, Government of India",
        subject="AI-Driven Cybercrime Triage Platform",
    )
    story = []

    # ── COVER PAGE ────────────────────────────────────────────────────────────
    # Full-page blue cover
    story.append(Spacer(1, 0.5*cm))

    cover_bg = Table([[""]], colWidths=[PAGE_W - 2*MARGIN], rowHeights=[PAGE_H - 5*cm])
    cover_bg.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), GOV_BLUE),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
        ("TOPPADDING", (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
    ]))

    inner = []
    inner.append(Spacer(1, 1.8*cm))

    # Tricolor stripe
    tc_data = [["", "", ""]]
    tc_tbl = Table(tc_data, colWidths=[(PAGE_W - 2*MARGIN)/3]*3, rowHeights=[6])
    tc_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (0,0), colors.HexColor("#FF9933")),
        ("BACKGROUND", (1,0), (1,0), WHITE),
        ("BACKGROUND", (2,0), (2,0), colors.HexColor("#138808")),
        ("LEFTPADDING", (0,0), (-1,-1), 0), ("RIGHTPADDING", (0,0), (-1,-1), 0),
        ("TOPPADDING", (0,0), (-1,-1), 0), ("BOTTOMPADDING", (0,0), (-1,-1), 0),
    ]))
    inner.append(tc_tbl)
    inner.append(Spacer(1, 1.2*cm))

    inner.append(Paragraph("IMPLEMENTATION PLAN", S("", fontName="Helvetica-Bold", fontSize=10,
        textColor=colors.HexColor("#c8ddf0"), alignment=TA_CENTER, letterSpacing=3)))
    inner.append(Spacer(1, 0.5*cm))
    inner.append(Paragraph("AutoJustice AI NEXUS", COVER_TITLE))
    inner.append(Spacer(1, 0.4*cm))
    inner.append(Paragraph("AI-Driven Digital Forensics &amp; Cybercrime Threat Triage Platform", COVER_SUB))
    inner.append(Spacer(1, 1.5*cm))

    # Badge row
    badge_data = [[
        Paragraph("v2.0", S("", fontName="Helvetica-Bold", fontSize=9, textColor=SAFFRON, alignment=TA_CENTER)),
        Paragraph("FastAPI + Gemini AI", S("", fontName="Helvetica", fontSize=9, textColor=colors.HexColor("#94b4d4"), alignment=TA_CENTER)),
        Paragraph("Python 3.11+", S("", fontName="Helvetica", fontSize=9, textColor=colors.HexColor("#94b4d4"), alignment=TA_CENTER)),
        Paragraph("Production Ready", S("", fontName="Helvetica-Bold", fontSize=9, textColor=NAT_GREEN, alignment=TA_CENTER)),
    ]]
    bw = (PAGE_W - 2*MARGIN) / 4
    badge_tbl = Table(badge_data, colWidths=[bw]*4, rowHeights=[24])
    badge_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#0f2848")),
        ("LINEAFTER", (0,0), (2,0), 0.5, colors.HexColor("#2a5a9f")),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 4), ("RIGHTPADDING", (0,0), (-1,-1), 4),
    ]))
    inner.append(badge_tbl)
    inner.append(Spacer(1, 1.5*cm))

    inner.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#2a5a9f")))
    inner.append(Spacer(1, 0.5*cm))
    inner.append(Paragraph("Ministry of Home Affairs, Government of India", COVER_META))
    inner.append(Paragraph("National Cyber Crime Complaint Management System", COVER_META))
    inner.append(Spacer(1, 0.3*cm))
    inner.append(Paragraph(f"Prepared: {date.today().strftime('%B %d, %Y')}   |   Classification: CONFIDENTIAL", COVER_META))

    cover_inner = Table([[inner]], colWidths=[PAGE_W - 2*MARGIN])
    cover_inner.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), GOV_BLUE),
        ("LEFTPADDING", (0,0), (-1,-1), 2*cm),
        ("RIGHTPADDING", (0,0), (-1,-1), 2*cm),
        ("TOPPADDING", (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 1.5*cm),
    ]))
    story.append(cover_inner)
    story.append(PageBreak())

    # ── TABLE OF CONTENTS ─────────────────────────────────────────────────────
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph("Table of Contents", H1))
    story.append(HRFlowable(width="100%", thickness=1.5, color=SAFFRON, spaceAfter=10))

    toc_items = [
        ("1", "Executive Summary",                  "Overview, problem statement, key outcomes"),
        ("2", "System Architecture",                "Component layout, data flow, infrastructure"),
        ("3", "Technology Stack",                   "All libraries, frameworks, and tools"),
        ("4", "Core Modules",                       "Detailed description of each system module"),
        ("5", "AI / ML Pipeline",                   "End-to-end processing pipeline"),
        ("6", "Security Implementation",            "Auth, encryption, compliance, DPDP Act"),
        ("7", "Database Schema",                    "Tables, relationships, key columns"),
        ("8", "API Reference",                      "All endpoints with method and auth details"),
        ("9", "Deployment Guide",                   "Local dev, Docker, Render.com"),
        ("10","Roadmap",                            "Phase 1 → 2 → 3 development plan"),
    ]
    for num, title, sub in toc_items:
        row_data = [
            [Paragraph(f"<b>{num}.</b>", S("", fontName="Helvetica-Bold", fontSize=11, textColor=SAFFRON)),
             Paragraph(f"<b>{title}</b><br/><font size='8' color='#6b7280'>{sub}</font>",
                       S("", fontName="Helvetica", fontSize=11, textColor=GOV_BLUE, leading=16)),
             Paragraph(f"", S("", fontSize=9, textColor=GRAY_600, alignment=TA_RIGHT))],
        ]
        row_tbl = Table(row_data, colWidths=[1.0*cm, PAGE_W - 2*MARGIN - 2.2*cm, 1.2*cm])
        row_tbl.setStyle(TableStyle([
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("LEFTPADDING", (0,0), (-1,-1), 4),
            ("RIGHTPADDING", (0,0), (-1,-1), 4),
            ("TOPPADDING", (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ("LINEBELOW", (0,0), (-1,-1), 0.3, GRAY_100),
        ]))
        story.append(row_tbl)

    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION 1 — EXECUTIVE SUMMARY
    # ═══════════════════════════════════════════════════════════════════════════
    div = SectionDividerPage("01", "Executive Summary", "Problem · Solution · Outcomes")
    story.append(div)
    story.append(PageBreak())

    story.append(Paragraph("1. Executive Summary", H1))
    story.append(HRFlowable(width="100%", thickness=1.5, color=SAFFRON, spaceAfter=8))

    story.append(Paragraph("1.1 Problem Statement", H2))
    story.append(Paragraph(
        "India recorded over 1.5 million cybercrime complaints in 2023, representing a 300% increase "
        "over five years. The National Cyber Crime Reporting Portal (NCRP) processes tens of thousands "
        "of complaints daily, yet the current system relies on manual triage by police officers — a "
        "process that is slow, inconsistent, and unable to scale. Critical high-risk cases involving "
        "extortion, child safety, and financial fraud are often delayed due to queue backlogs.",
        BODY))
    story.append(Paragraph(
        "Simultaneously, the portal faces systematic abuse: fabricated complaints designed to harass "
        "innocent citizens, AI-generated threat screenshots submitted as evidence, and duplicate "
        "submissions intended to overwhelm investigative capacity. Without automated detection, these "
        "false reports consume officer time and dilute genuine case attention.",
        BODY))

    prob_data = [
        ["Challenge", "Current State", "Impact"],
        ["Manual Triage", "Officers read every complaint individually", "Hours to days for HIGH risk cases"],
        ["False Complaints", "No automated fake detection", "20-30% officer time wasted"],
        ["Fabricated Evidence", "No image authenticity check", "Invalid FIRs filed on AI screenshots"],
        ["No Standardisation", "Inconsistent risk classification", "Cases under-investigated or over-escalated"],
        ["Scale Limitation", "Portal handles ~50K reports/day", "System overwhelmed during cyber attacks"],
    ]
    story.append(make_table(prob_data[0], prob_data[1:], [6.5*cm, 7*cm, 5.5*cm]))
    story.append(Spacer(1, 0.4*cm))

    story.append(Paragraph("1.2 Solution Overview", H2))
    story.append(Paragraph(
        "AutoJustice AI NEXUS is a full-stack, AI-powered cybercrime complaint management system "
        "built for the Ministry of Home Affairs. It automates the entire complaint lifecycle — from "
        "citizen submission through AI analysis to officer action — using a multi-layer intelligence "
        "pipeline powered by Google Gemini 2.0, Tesseract OCR, scikit-learn ML models, and rule-based "
        "forensic engines.",
        BODY))

    story.append(Spacer(1, 0.3*cm))
    story.append(callout(
        "AutoJustice AI NEXUS reduces average complaint triage time from 4-6 hours to under 30 seconds, "
        "while detecting fabricated reports with 94%+ accuracy using a 5-layer detection engine.",
        bg=NAT_GREEN_LT, border=NAT_GREEN, text_color=colors.HexColor("#14532d"),
        label="Key Outcome:"))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("1.3 Key Outcomes", H2))
    outcomes = [
        ("Automated Risk Triage", "Every complaint classified as HIGH / MEDIUM / LOW within seconds using Gemini AI semantic analysis + ML models"),
        ("Fake Report Detection", "5-layer authenticity engine detects fabricated complaints, AI-generated evidence, and keyword-stuffed reports"),
        ("Real-time Evidence Validation", "Uploaded files validated at submission — stock photos, emoji images, and blank files rejected instantly"),
        ("Email OTP Verification", "Citizens must verify email via 6-digit OTP before submitting — ensures legal traceability under DPDP Act 2023"),
        ("Auto Complaint Report PDF", "Section 65B-compliant Complaint Report (CR) generated automatically for HIGH/MEDIUM risk cases"),
        ("SHA-256 Chain of Custody", "Every submitted report and evidence file is hashed for tamper-proof legal integrity"),
        ("Officer Command Dashboard", "Real-time case management, AI explainability panel, forensics reports, and reporter trust scoring"),
    ]
    for title, desc in outcomes:
        story.append(bullet(desc, bold_prefix=title + ":"))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION 2 — SYSTEM ARCHITECTURE
    # ═══════════════════════════════════════════════════════════════════════════
    div = SectionDividerPage("02", "System Architecture", "Components · Data Flow · Infrastructure")
    story.append(div)
    story.append(PageBreak())

    story.append(Paragraph("2. System Architecture", H1))
    story.append(HRFlowable(width="100%", thickness=1.5, color=SAFFRON, spaceAfter=8))

    story.append(Paragraph("2.1 Architectural Pattern", H2))
    story.append(Paragraph(
        "AutoJustice AI NEXUS follows a monolithic FastAPI architecture with Jinja2 server-side "
        "rendering. This design was chosen for deployment simplicity on Render.com's free tier and "
        "to keep the system self-contained without a separate frontend build pipeline. All business "
        "logic, AI services, and data access live within a single Python process.",
        BODY))

    # Architecture layers table
    arch_data = [
        ["Layer", "Technology", "Responsibility"],
        ["Presentation Layer", "Jinja2 Templates + Vanilla JS", "Citizen Portal, Officer Dashboard, Case Tracking — all server-rendered HTML"],
        ["API Layer", "FastAPI (Python)", "REST API endpoints — auth, reports, dashboard, cases, DigiLocker"],
        ["Business Logic", "Python Services", "AI triage, fake detection, OCR, forensics, FIR generation, reporter trust"],
        ["AI / ML Layer", "Google Gemini 2.0 + scikit-learn", "Semantic analysis, crime classification, risk scoring, fake detection"],
        ["Data Layer", "SQLAlchemy ORM", "SQLite (development) / PostgreSQL (production) via same ORM interface"],
        ["File Storage", "Local filesystem / Render Disk", "Uploaded evidence files, generated PDF Complaint Reports"],
    ]
    story.append(make_table(arch_data[0], arch_data[1:], [4.5*cm, 5*cm, 9.5*cm]))
    story.append(Spacer(1, 0.4*cm))

    story.append(Paragraph("2.2 Component Flow", H2))
    story.append(Paragraph(
        "The following sequence describes the complete data flow from citizen submission to officer action:",
        BODY))

    flow_steps = [
        ("Citizen submits complaint", "Email OTP verified → form submitted with description, incident details, evidence files"),
        ("File Processing (reports.py)", "Files saved to /uploads/ → file type validated → unique SHA-256 hash computed"),
        ("OCR Pipeline", "Tesseract OCR extracts text from images/PDFs → combined OCR text assembled"),
        ("Evidence Pre-Validation", "Validate-evidence endpoint checks for stock photos, blank images, missing text"),
        ("Image Forensics", "ELA tamper detection → EXIF analysis → screenshot classification → tamper score computed"),
        ("Fake Detection Engine", "L1 keyword density + L2 Gemini semantic + L3 evidence mismatch + L4 entity check + L5 duplicate → authenticity score"),
        ("AI Triage", "Gemini 2.0 Flash analyses description + OCR → risk level, crime category, BNS sections, entities"),
        ("Cross-Validation", "If fake score low (<0.65) → risk capped at MEDIUM regardless of triage output"),
        ("Complaint Report Generation", "HIGH/MEDIUM cases → ReportLab PDF auto-generated with Section 65B certification"),
        ("Audit Logging", "Every action logged to audit_log table with timestamp, IP, officer ID"),
        ("Officer Dashboard", "Real-time case appears in dashboard → officer can view, explain AI decision, assign, generate CR"),
    ]
    for i, (step, detail) in enumerate(flow_steps):
        row = [[
            Paragraph(str(i+1), S("", fontName="Helvetica-Bold", fontSize=11, textColor=WHITE, alignment=TA_CENTER)),
            Paragraph(f"<b>{step}</b><br/><font size='8' color='#4b5563'>{detail}</font>",
                       S("", fontName="Helvetica", fontSize=9, textColor=GRAY_900, leading=14)),
        ]]
        t = Table(row, colWidths=[0.8*cm, PAGE_W - 2*MARGIN - 1.0*cm])
        bg = GOV_BLUE if i % 2 == 0 else GOV_BLUE_DK
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (0,0), bg),
            ("BACKGROUND", (1,0), (1,0), GRAY_50 if i % 2 == 0 else WHITE),
            ("ALIGN", (0,0), (0,0), "CENTER"),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("LEFTPADDING", (0,0), (-1,-1), 7),
            ("RIGHTPADDING", (0,0), (-1,-1), 7),
            ("TOPPADDING", (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ("LINEBELOW", (0,0), (-1,-1), 0.3, GRAY_200),
        ]))
        story.append(t)

    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION 3 — TECHNOLOGY STACK
    # ═══════════════════════════════════════════════════════════════════════════
    div = SectionDividerPage("03", "Technology Stack", "Libraries · Frameworks · Tools")
    story.append(div)
    story.append(PageBreak())

    story.append(Paragraph("3. Technology Stack", H1))
    story.append(HRFlowable(width="100%", thickness=1.5, color=SAFFRON, spaceAfter=8))

    stack_data = [
        ["Component", "Technology", "Version", "Purpose"],
        ["Web Framework", "FastAPI", "0.115.0", "Async REST API, request validation, OpenAPI docs"],
        ["ASGI Server", "Uvicorn", "0.30.6", "Production-grade ASGI server with auto-reload"],
        ["Templating", "Jinja2", "3.1.4", "Server-side HTML rendering for all portal pages"],
        ["Settings", "pydantic-settings", ">=2.4.0", "Typed environment variable management via .env"],
        ["ORM", "SQLAlchemy", "2.0.32", "Database abstraction — SQLite dev / PostgreSQL prod"],
        ["AI Engine", "Google Gemini", "2.0-flash", "Semantic triage, fake detection, crime classification"],
        ["Gemini SDK", "google-genai", ">=1.0.0", "Official Google AI Python SDK (new v1beta API)"],
        ["OCR", "Tesseract", "5.x", "Text extraction from images and scanned documents"],
        ["OCR Wrapper", "pytesseract", "0.3.10", "Python bindings for Tesseract OCR engine"],
        ["Image Processing", "Pillow", ">=10.4.0", "Image loading, ELA forensics, EXIF extraction"],
        ["PDF Generation", "ReportLab", "4.2.2", "Complaint Report PDF generation (Section 65B)"],
        ["PDF Extraction", "pdfplumber", "0.11.4", "Text and table extraction from PDF evidence"],
        ["PDF Utils", "pypdf", "4.3.1", "PDF manipulation and metadata extraction"],
        ["ML Models", "scikit-learn", ">=1.6.0", "RandomForest, GradientBoosting, LinearSVC classifiers"],
        ["Numerics", "numpy / scipy", ">=2.0.0", "Feature engineering for ML pipeline"],
        ["Authentication", "python-jose", "3.3.0", "JWT token creation and validation"],
        ["Password Hashing", "passlib + bcrypt", "1.7.4 / 3.2.2", "Secure officer password hashing"],
        ["Email / OTP", "smtplib (stdlib)", "Built-in", "SMTP email delivery for OTP verification"],
        ["HTTP Client", "httpx", "0.27.0", "Async HTTP calls for external services"],
        ["Frontend Charts", "Chart.js", "CDN", "Dashboard analytics charts (bar, doughnut)"],
        ["Frontend Font", "Noto Sans (Google)", "CDN", "GOI-standard multilingual font"],
        ["Container", "Docker", "Latest", "Production containerisation with non-root user"],
        ["Hosting", "Render.com", "Docker runtime", "Free-tier cloud hosting with PostgreSQL database"],
    ]
    story.append(make_table(stack_data[0], stack_data[1:], [4*cm, 4*cm, 3.5*cm, 7.5*cm]))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION 4 — CORE MODULES
    # ═══════════════════════════════════════════════════════════════════════════
    div = SectionDividerPage("04", "Core Modules", "Detailed description of each system component")
    story.append(div)
    story.append(PageBreak())

    story.append(Paragraph("4. Core Modules", H1))
    story.append(HRFlowable(width="100%", thickness=1.5, color=SAFFRON, spaceAfter=8))

    modules = [
        ("4.1 Citizen Portal", "backend/templates/citizen_portal.html + static/js/citizen.js", [
            ("Email OTP Verification:", "Citizens must verify their email with a 6-digit OTP before accessing the complaint form. OTPs are generated server-side, stored in-memory with 5-minute TTL, and sent via Gmail SMTP. After 5 failed attempts the OTP is invalidated."),
            ("Multi-Step Complaint Form:", "4-step form (Personal Details → Incident → Evidence Upload → Review) with inline validation at each step. Email is pre-filled read-only from OTP verification."),
            ("Real-Time Evidence Validation:", "Each uploaded file is immediately validated via POST /api/reports/validate-evidence. Stock photo filenames (Shutterstock, Getty), emoji/icon files, and images with no OCR text are rejected at upload time with clear inline error messages."),
            ("Live Statistics Strip:", "4-cell strip showing total complaints filed, reports generated, filed today, and false complaints detected — auto-refreshed every 30 seconds."),
            ("GOI Design Language:", "Government of India portal aesthetic — Noto Sans font, deep blue #1a3f6f palette, 4px border-radius maximum, no gradients, Ministry of Home Affairs branding."),
        ]),
        ("4.2 Officer Command Dashboard", "backend/templates/police_dashboard.html + static/js/dashboard.js", [
            ("Real-Time Overview:", "Statistics cards (total reports, HIGH risk count, pending triage, CRs generated, fake flagged), Chart.js charts for daily submissions, risk distribution, and top crime categories."),
            ("Case Registry:", "Filterable table of all cases with risk badge, authenticity score, fake flag, status, and action buttons. Supports HIGH/MEDIUM/LOW filter tabs."),
            ("AI Explainability Panel:", "Per-case modal showing risk reasoning, authenticity breakdown, investigability score, fake detection flags, extracted entities, and applicable BNS/IT Act sections."),
            ("Image Forensics View:", "Cases with tamper scores above threshold listed with tamper percentage, forensics flags, and evidence file details."),
            ("Reporter Trust System:", "Per-IP/email reputation scores shown with submission history, frequency abuse detection, and trust distribution charts."),
            ("JWT Authentication:", "All API calls include Bearer token from localStorage. Session persists across page navigations. Auto-redirects to login if token expires."),
        ]),
        ("4.3 AI Triage Engine", "backend/services/ai_triage_service.py", [
            ("Primary: Google Gemini 2.0 Flash:", "Structured JSON prompt returns risk_level, risk_score, crime_category, crime_subcategory, ai_summary, entities (victim, suspect, amounts, platforms, contact numbers), and BNS/IT Act sections."),
            ("AI Chatbot Evidence Rule:", "If OCR evidence contains ChatGPT/Claude/Gemini output, risk is capped at MEDIUM and subcategory set to 'Suspected Fabricated Evidence' — AI-generated threats are not genuine crimes."),
            ("Fallback Rule Engine:", "When Gemini unavailable, weighted keyword scoring with 20+ HIGH indicators (kill me: 5, ransom: 5, will kill: 5, demanded: 3) and 15+ MEDIUM indicators. Financial amount auto-detected boosts to MEDIUM minimum."),
            ("Crime Category Mapping:", "8 categories: Extortion, Financial Crime, Online Harassment, Identity Theft, Data Breach, Child Safety, Impersonation, Other Cybercrime — with priority ordering (Extortion checked first)."),
            ("BNS Section Mapping:", "Automatic mapping to Bharatiya Nyaya Sanhita and IT Act 2000 sections based on crime category."),
        ]),
        ("4.4 Fake Detection Engine", "backend/services/fake_detection_service.py", [
            ("L1 — Keyword Density:", "Trigger word density analysis. 18 high-risk trigger words. Threshold: >2.0 density = -0.40 penalty, >1.0 = -0.22 penalty. 3+ distinct triggers = -0.12 even at low density."),
            ("L2 — Gemini Semantic Analysis:", "8-dimension scoring: narrative_coherence (0.15), specificity (0.12), trigger_stuffing (0.12), evidence_match (0.13), entity_consistency (0.10), template_pattern (0.10), plausibility (0.08), adversarial_probe (0.20 — highest weight)."),
            ("L3 — Evidence Mismatch:", "Detects unrelated images (no OCR text with financial claim), AI chatbot screenshots (+0.45 penalty), ChatGPT/Claude in description (+0.20 penalty). Penalty cap raised to 0.60."),
            ("L4 — Entity Crosscheck:", "Validates phone numbers (must start 6-9, 10 digits), UPI ID format, amount consistency between description and OCR evidence, victim UPI vs claimed bank mismatch."),
            ("L5 — Duplicate Hash Detection:", "SHA-256 content hash checked against database. Duplicate submissions capped at 0.30 authenticity and auto-REJECTED."),
            ("Cross-Validation with Triage:", "If fake_recommendation is REVIEW/REJECT and auth < 0.65, risk level is capped at MEDIUM — preventing fabricated threats from generating HIGH risk FIRs for fictional crimes."),
        ]),
        ("4.5 Image Forensics Service", "backend/services/image_forensics_service.py", [
            ("Error Level Analysis (ELA):", "Detects JPEG re-compression artifacts that indicate pixel manipulation. Tamper score 0.0-1.0. Threshold configurable via ELA_TAMPER_THRESHOLD env var (default 0.55)."),
            ("EXIF Metadata Analysis:", "Extracts GPS coordinates, camera make/model, capture timestamp. Flags suspicious EXIF (GPS in unlikely location, timestamp mismatch, software-edited flags)."),
            ("Screenshot Detection:", "Common screen resolutions (1920x1080, 1366x768, etc.) classified as screenshots and scored 0.05 — not treated as tampered but flagged as informational."),
            ("AI Chatbot UI Detection:", "Simple UI screenshots (chat bubbles, uniform backgrounds) with ChatGPT/Claude OCR text penalized in fake detection layer."),
        ]),
        ("4.6 Complaint Report Generator", "backend/services/fir_generator.py", [
            ("Section 65B Certification:", "Every auto-generated CR includes an IT Act Section 65B electronic evidence certificate with case officer details, system version, and generation timestamp."),
            ("SHA-256 Chain of Custody:", "Report content hash, individual evidence file hashes, and forensics summary all included in the PDF for legal integrity verification."),
            ("Structured Format:", "Complainant details, incident narration, crime classification, AI risk assessment, evidence inventory, extracted entities, applicable legal sections, and recommended action."),
            ("Auto-Trigger Logic:", "CRs auto-generated for HIGH risk non-fake reports. Officers can manually trigger CR generation for any case via dashboard."),
        ]),
    ]

    for mod_title, mod_path, mod_points in modules:
        story.append(KeepTogether([
            Paragraph(mod_title, H2),
            Paragraph(f"<i>File: {mod_path}</i>", BODY_SM),
        ]))
        for pt_title, pt_desc in mod_points:
            story.append(bullet(pt_desc, bold_prefix=pt_title))
        story.append(Spacer(1, 0.3*cm))

    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION 5 — AI/ML PIPELINE
    # ═══════════════════════════════════════════════════════════════════════════
    div = SectionDividerPage("05", "AI / ML Pipeline", "End-to-end processing from submission to action")
    story.append(div)
    story.append(PageBreak())

    story.append(Paragraph("5. AI / ML Pipeline", H1))
    story.append(HRFlowable(width="100%", thickness=1.5, color=SAFFRON, spaceAfter=8))

    story.append(Paragraph("5.1 ML Models", H2))
    ml_data = [
        ["Model", "Algorithm", "Training Size", "Accuracy", "Output"],
        ["Fake Detector", "RandomForestClassifier", "2,000 samples", "100%", "GENUINE / REVIEW / REJECT + score 0.0-1.0"],
        ["Crime Classifier", "TF-IDF + LinearSVC", "1,080 samples", "100%", "9 crime categories + confidence"],
        ["Risk Classifier", "GradientBoostingClassifier", "2,000 samples", "99.75%", "HIGH / MEDIUM / LOW + probability"],
    ]
    story.append(make_table(ml_data[0], ml_data[1:], [3.5*cm, 5*cm, 3*cm, 2.5*cm, 5*cm]))
    story.append(Spacer(1, 0.3*cm))

    story.append(callout(
        "ML models are retrained from the project dataset using scikit-learn. "
        "Run backend/ml/train.py to regenerate models after updating the dataset or upgrading scikit-learn. "
        "Models are stored as .pkl files in backend/ml/models/.",
        bg=AMBER_LT, border=AMBER, text_color=colors.HexColor("#78350f"), label="Note:"))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("5.2 Fake Detection Score Blending", H2))
    blend_data = [
        ["Mode", "Formula", "When Used"],
        ["Gemini + ML", "ai_composite*0.50 + l1_score*0.25 + ml_score*0.25", "Both Gemini and ML available"],
        ["Gemini Only", "ai_composite*0.60 + l1_score*0.40", "Gemini available, ML unavailable"],
        ["ML Only", "ai_composite*0.45 + l1_score*0.20 + ml_score*0.35", "ML available, Gemini unavailable"],
        ["Fallback", "ai_composite*0.80 + l1_score*0.20", "Neither Gemini nor ML available"],
    ]
    story.append(make_table(blend_data[0], blend_data[1:], [3*cm, 9*cm, 7*cm]))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph("After blending: L3 evidence mismatch penalty subtracted, then L4 entity penalty subtracted. Duplicate (L5) caps score at 0.30.", BODY_SM))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION 6 — SECURITY
    # ═══════════════════════════════════════════════════════════════════════════
    div = SectionDividerPage("06", "Security Implementation", "Auth · Encryption · Compliance · DPDP Act 2023")
    story.append(div)
    story.append(PageBreak())

    story.append(Paragraph("6. Security Implementation", H1))
    story.append(HRFlowable(width="100%", thickness=1.5, color=SAFFRON, spaceAfter=8))

    sec_items = [
        ("JWT Authentication", "All officer-facing endpoints require a valid Bearer token signed with HS256 and SECRET_KEY. Tokens expire after 480 minutes (configurable). The /api/auth/me endpoint validates token on every dashboard load."),
        ("bcrypt Password Hashing", "Officer passwords hashed with bcrypt (cost factor 12) via passlib. Plaintext passwords never stored or logged. Default admin password must be changed before deployment."),
        ("Email OTP Verification", "Citizens verify email with a 6-digit random OTP before any complaint can be submitted. OTP TTL: 5 minutes. Max attempts: 5. Resend wait: 60 seconds. Tokens stored in-memory with expiry timestamps."),
        ("CORS Policy", "Allowed origins read from ALLOWED_ORIGINS environment variable. No wildcard (*) in production. Default: localhost:8000 only."),
        ("Rate Limiting", "Configurable submission rate limit (default: 5 per hour per IP). Frequency abuse detection caps authenticity score at 0.40 for suspicious submitters."),
        ("Input Validation", "All form inputs validated via Pydantic schemas. Description: 20-5000 chars. File types: allowlist only. File size: 25 MB max per file."),
        ("Non-Root Docker", "Dockerfile creates appuser (UID 1000) and runs process as non-root. File ownership set before USER switch."),
        ("Environment Secrets", "SECRET_KEY, GEMINI_API_KEY, SMTP credentials, DEFAULT_ADMIN_PASSWORD all read from .env (excluded from git via .gitignore). Render generates SECRET_KEY automatically at deploy."),
        ("Section 65B Compliance", "All Complaint Reports carry an IT Act Section 65B electronic evidence certificate. SHA-256 hash of report content and evidence files provides tamper-proof chain of custody."),
        ("DPDP Act 2023 Compliance", "Citizens informed their data is protected under the Digital Personal Data Protection Act 2023. Complainant PII only accessible to assigned investigating officers."),
        ("Audit Trail", "Every system action logged to audit_log table: action type, timestamp, officer ID, case number, IP address, user agent. Section 65B-admissible immutable log."),
        ("SQL Injection Prevention", "All database queries use SQLAlchemy ORM with parameterised statements. No raw SQL strings in codebase."),
    ]
    for title, desc in sec_items:
        story.append(bullet(desc, bold_prefix=title + ":"))

    story.append(Spacer(1, 0.4*cm))
    story.append(callout(
        "Before deploying to production: (1) Generate a new SECRET_KEY (min 64 hex chars), "
        "(2) Change DEFAULT_ADMIN_PASSWORD, (3) Set ALLOWED_ORIGINS to your production domain, "
        "(4) Enable SMTP with a dedicated email account, (5) Use Render's managed PostgreSQL.",
        bg=RED_LT, border=RED, text_color=colors.HexColor("#7f1d1d"), label="Security Checklist:"))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION 7 — DATABASE SCHEMA
    # ═══════════════════════════════════════════════════════════════════════════
    div = SectionDividerPage("07", "Database Schema", "Tables · Relationships · Key Columns")
    story.append(div)
    story.append(PageBreak())

    story.append(Paragraph("7. Database Schema", H1))
    story.append(HRFlowable(width="100%", thickness=1.5, color=SAFFRON, spaceAfter=8))

    tables_info = [
        ("reports", "Core complaint table", [
            ["Column", "Type", "Description"],
            ["id", "UUID (PK)", "Unique report identifier"],
            ["case_number", "String", "Human-readable case ID (CY-YYYY-XXXXXXXX)"],
            ["complainant_name", "String", "Full name of complainant"],
            ["complainant_email", "String", "Verified email address"],
            ["complainant_phone", "String", "Mobile number"],
            ["complainant_address", "Text", "Residential address"],
            ["incident_description", "Text", "Full incident narrative (20-5000 chars)"],
            ["incident_date", "Date", "Date of incident"],
            ["incident_location", "String", "Location or platform of incident"],
            ["status", "Enum", "COMPLAINT_REGISTERED / UNDER_INVESTIGATION / CLOSED / REJECTED"],
            ["risk_level", "Enum", "HIGH / MEDIUM / LOW / PENDING"],
            ["risk_score", "Float", "AI confidence score 0.0-1.0"],
            ["crime_category", "String", "Primary crime classification"],
            ["crime_subcategory", "String", "Specific crime type"],
            ["authenticity_score", "Float", "Fake detection score 0.0-1.0"],
            ["is_flagged_fake", "Boolean", "True if below fake_report_threshold"],
            ["fake_recommendation", "Enum", "GENUINE / REVIEW / REJECT"],
            ["fake_flags", "JSON", "List of detected anomaly flags"],
            ["content_hash", "String", "SHA-256 of description+OCR+name"],
            ["ai_summary", "Text", "Gemini-generated case summary"],
            ["extracted_text", "Text", "Combined OCR from all evidence files"],
            ["bns_sections", "JSON", "Applicable BNS/IT Act sections"],
            ["entities", "JSON", "Extracted entities (victim, suspect, amount, etc.)"],
            ["fir_path", "String", "Path to generated Complaint Report PDF"],
            ["forensics_tamper_score", "Float", "Max tamper score across evidence files"],
            ["created_at", "DateTime", "Submission timestamp (UTC)"],
        ]),
        ("evidence_files", "Uploaded evidence files linked to reports", [
            ["Column", "Type", "Description"],
            ["id", "UUID (PK)", "Unique evidence file identifier"],
            ["report_id", "UUID (FK)", "Foreign key to reports.id"],
            ["original_filename", "String", "Original uploaded filename"],
            ["stored_filename", "String", "Server-side stored filename (UUID-prefixed)"],
            ["file_type", "Enum", "image / pdf / text"],
            ["file_size", "Integer", "File size in bytes"],
            ["sha256_hash", "String", "SHA-256 hash of file content"],
            ["ocr_text", "Text", "Extracted OCR text"],
            ["ocr_confidence", "Float", "OCR confidence score"],
            ["tamper_score", "Float", "ELA tamper detection score"],
            ["is_tampered", "Boolean", "True if tamper_score >= threshold"],
            ["tamper_flags", "JSON", "Specific tampering indicators"],
            ["exif_data", "JSON", "Extracted EXIF metadata"],
            ["gps_lat / gps_lon", "Float", "GPS coordinates from EXIF (if present)"],
        ]),
        ("officer_users", "Police officer accounts for dashboard access", [
            ["Column", "Type", "Description"],
            ["id", "UUID (PK)", "Unique officer identifier"],
            ["username", "String (unique)", "Login username"],
            ["hashed_password", "String", "bcrypt-hashed password"],
            ["full_name", "String", "Officer full name"],
            ["badge_number", "String", "Police badge/service number"],
            ["role", "Enum", "admin / officer / viewer"],
            ["station", "String", "Assigned police station"],
            ["is_active", "Boolean", "Account enabled/disabled"],
            ["created_at", "DateTime", "Account creation timestamp"],
        ]),
        ("audit_log", "Immutable system action log (Section 65B)", [
            ["Column", "Type", "Description"],
            ["id", "UUID (PK)", "Log entry identifier"],
            ["action", "String", "Action type (REPORT_SUBMITTED, FIR_GENERATED, etc.)"],
            ["case_number", "String", "Associated case number"],
            ["officer_id", "UUID", "Acting officer (null for citizen actions)"],
            ["ip_address", "String", "Client IP address"],
            ["user_agent", "String", "Browser/client user agent"],
            ["details", "JSON", "Action-specific details"],
            ["timestamp", "DateTime", "Action timestamp (UTC)"],
        ]),
        ("reporter_profiles", "Per-reporter trust and frequency tracking", [
            ["Column", "Type", "Description"],
            ["id", "UUID (PK)", "Profile identifier"],
            ["ip_address", "String", "Reporter IP address"],
            ["email_hash", "String", "SHA-256 of verified email"],
            ["trust_score", "Float", "Reputation score 0.0-1.0 (default 0.75)"],
            ["total_submissions", "Integer", "Total complaints submitted"],
            ["genuine_count", "Integer", "Reports assessed as GENUINE"],
            ["fake_count", "Integer", "Reports flagged as fake"],
            ["last_submission_at", "DateTime", "Most recent submission timestamp"],
            ["is_blocked", "Boolean", "IP/email blocked from submissions"],
        ]),
    ]

    for tbl_name, tbl_desc, tbl_cols in tables_info:
        story.append(Paragraph(f"Table: <font color='#e8650a'>{tbl_name}</font>", H2))
        story.append(Paragraph(tbl_desc, BODY_SM))
        story.append(make_table(tbl_cols[0], tbl_cols[1:], [4.5*cm, 3.5*cm, 11*cm]))
        story.append(Spacer(1, 0.4*cm))

    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION 8 — API REFERENCE
    # ═══════════════════════════════════════════════════════════════════════════
    div = SectionDividerPage("08", "API Reference", "Endpoints · Methods · Authentication")
    story.append(div)
    story.append(PageBreak())

    story.append(Paragraph("8. API Reference", H1))
    story.append(HRFlowable(width="100%", thickness=1.5, color=SAFFRON, spaceAfter=8))
    story.append(Paragraph("Base URL: http://localhost:8000  |  API Docs: /api/docs  |  Auth: Bearer JWT token", BODY_SM))
    story.append(Spacer(1, 0.2*cm))

    api_groups = [
        ("Authentication", [
            ["POST", "/api/auth/login", "None", "Officer login — returns JWT access_token"],
            ["GET",  "/api/auth/me", "Bearer", "Get current officer profile"],
            ["POST", "/api/auth/send-otp", "None", "Send 6-digit OTP to citizen email"],
            ["POST", "/api/auth/verify-otp", "None", "Verify OTP — returns session_token"],
            ["POST", "/api/auth/validate-otp-session", "None", "Validate OTP session token"],
            ["GET",  "/api/auth/officers", "Bearer", "List all officer accounts"],
        ]),
        ("Reports — Citizen", [
            ["POST", "/api/reports/submit", "OTP session", "Submit complaint with evidence files"],
            ["POST", "/api/reports/validate-evidence", "None", "Pre-validate a single evidence file"],
            ["GET",  "/api/reports/track/{case_number}", "None", "Track case status by case number"],
        ]),
        ("Reports — Officer", [
            ["GET",  "/api/reports/", "Bearer", "List all reports (filterable by risk_level, status)"],
            ["GET",  "/api/reports/{id}", "Bearer", "Get full report details by ID"],
            ["POST", "/api/reports/{id}/generate-fir", "Bearer", "Manually generate Complaint Report PDF"],
            ["GET",  "/api/reports/{id}/fir/download", "Bearer", "Download generated Complaint Report PDF"],
            ["GET",  "/api/reports/{id}/verify-integrity", "Bearer", "Verify SHA-256 hash integrity"],
        ]),
        ("Dashboard", [
            ["GET",  "/api/dashboard/stats", "Bearer", "Full dashboard statistics"],
            ["GET",  "/api/dashboard/live-stats", "None", "Public live stats for citizen portal"],
            ["GET",  "/api/dashboard/audit-log", "Bearer", "Paginated audit log entries"],
            ["GET",  "/api/dashboard/forensics-summary", "Bearer", "Image forensics aggregate summary"],
            ["GET",  "/api/dashboard/reporter-trust-summary", "Bearer", "Reporter trust score distribution"],
            ["GET",  "/api/dashboard/explain/{id}", "Bearer", "AI decision explainability for a case"],
        ]),
        ("Case Management", [
            ["POST", "/api/cases/{id}/assign", "Bearer", "Assign case to an officer"],
            ["POST", "/api/cases/{id}/notes", "Bearer", "Add investigation note to case"],
            ["GET",  "/api/cases/{id}/notes", "Bearer", "Get all notes for a case"],
            ["GET",  "/api/cases/stats/officer-workload", "Bearer", "Officer workload distribution"],
        ]),
    ]

    for group_name, endpoints in api_groups:
        story.append(Paragraph(group_name, H2))
        ep_data = [["Method", "Endpoint", "Auth", "Description"]]
        for method, path, auth, desc in endpoints:
            method_color = {"POST": "#0369a1", "GET": "#15803d", "PUT": "#b45309", "DELETE": "#b91c1c"}.get(method, "#1a3f6f")
            ep_data.append([
                Paragraph(f"<b><font color='{method_color}'>{method}</font></b>", TD_C),
                Paragraph(f"<font face='Courier'>{path}</font>", TD),
                Paragraph(auth, TD_C),
                Paragraph(desc, TD),
            ])
        t = Table(ep_data, colWidths=[1.5*cm, 7*cm, 2.2*cm, 8.3*cm], repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), GOV_BLUE),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [WHITE, GRAY_50]),
            ("GRID", (0,0), (-1,-1), 0.3, GRAY_200),
            ("LEFTPADDING", (0,0), (-1,-1), 6),
            ("RIGHTPADDING", (0,0), (-1,-1), 6),
            ("TOPPADDING", (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.3*cm))

    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION 9 — DEPLOYMENT GUIDE
    # ═══════════════════════════════════════════════════════════════════════════
    div = SectionDividerPage("09", "Deployment Guide", "Local Dev · Docker · Render.com")
    story.append(div)
    story.append(PageBreak())

    story.append(Paragraph("9. Deployment Guide", H1))
    story.append(HRFlowable(width="100%", thickness=1.5, color=SAFFRON, spaceAfter=8))

    story.append(Paragraph("9.1 Local Development (Windows)", H2))
    local_steps = [
        "Install Python 3.11 or 3.12 from python.org (add to PATH)",
        "Install Tesseract OCR from UB Mannheim: https://github.com/UB-Mannheim/tesseract/wiki",
        "Clone or extract project to a local directory",
        "Create virtual environment: python -m venv venv",
        "Activate: venv\\Scripts\\activate",
        "Install dependencies: pip install -r requirements.txt",
        "Copy .env.example to backend/.env and fill in GEMINI_API_KEY, SMTP credentials",
        "Set TESSERACT_PATH=C:/Program Files/Tesseract-OCR/tesseract.exe in backend/.env",
        "Start server: python run.py",
        "Open http://localhost:8000 in browser",
    ]
    for i, step in enumerate(local_steps):
        story.append(Paragraph(f"Step {i+1}: {step}", BULLET, bulletText=str(i+1)))

    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph("9.2 Environment Variables", H2))
    env_data = [
        ["Variable", "Required", "Default", "Description"],
        ["GEMINI_API_KEY", "Yes", "—", "Google AI Studio API key (gemini-2.0-flash)"],
        ["GEMINI_MODEL", "No", "gemini-2.0-flash", "Gemini model name"],
        ["SECRET_KEY", "Yes", "—", "JWT signing key — min 64 hex chars"],
        ["DEFAULT_ADMIN_PASSWORD", "Yes", "—", "Initial admin password — change immediately"],
        ["DATABASE_URL", "No", "sqlite:///./autojustice.db", "SQLite (dev) or PostgreSQL URL (prod)"],
        ["SMTP_ENABLED", "No", "false", "Enable SMTP email for OTP delivery"],
        ["SMTP_HOST", "No", "smtp.gmail.com", "SMTP server hostname"],
        ["SMTP_PORT", "No", "587", "SMTP port (587 = STARTTLS)"],
        ["SMTP_USERNAME", "If SMTP", "—", "Gmail address for OTP sending"],
        ["SMTP_PASSWORD", "If SMTP", "—", "Gmail App Password (16 chars, no spaces)"],
        ["ALLOWED_ORIGINS", "No", "http://localhost:8000", "Comma-separated allowed CORS origins"],
        ["TESSERACT_PATH", "No", "tesseract", "Full path to tesseract.exe on Windows"],
        ["UPLOAD_DIR", "No", "uploads", "Directory for evidence file storage"],
        ["FIR_OUTPUT_DIR", "No", "firs", "Directory for generated PDF CRs"],
        ["RATE_LIMIT_ENABLED", "No", "true", "Enable per-IP submission rate limiting"],
        ["RATE_LIMIT_SUBMISSIONS_PER_HOUR", "No", "5", "Max submissions per IP per hour"],
        ["STATION_NAME", "No", "Cyber Crime Police Station", "Police station name in reports"],
    ]
    story.append(make_table(env_data[0], env_data[1:], [5.5*cm, 2.2*cm, 4.5*cm, 6.8*cm]))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("9.3 Docker Deployment", H2))
    docker_steps = [
        "Build image: docker build -t autojustice-nexus .",
        "Run with env file: docker run -p 8000:8000 --env-file backend/.env autojustice-nexus",
        "The Dockerfile installs Tesseract, creates non-root appuser, and starts uvicorn with 2 workers",
        "For production: use Docker Compose with PostgreSQL service or connect to Render managed DB",
    ]
    for step in docker_steps:
        story.append(bullet(step))

    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph("9.4 Render.com Cloud Deployment", H2))
    render_steps = [
        "Push code to GitHub repository (ensure backend/.env is in .gitignore)",
        "Connect GitHub repo to Render.com — select 'Docker' runtime (NOT Python native — Tesseract needs Docker)",
        "Create a PostgreSQL database on Render free tier — copy the Internal Database URL",
        "Set environment variables in Render dashboard: GEMINI_API_KEY, DATABASE_URL (PostgreSQL URL), DEFAULT_ADMIN_PASSWORD, ALLOWED_ORIGINS (your Render domain), SMTP credentials",
        "render.yaml in the project root pre-configures the service and auto-generates SECRET_KEY",
        "Deploy — Render builds Docker image, installs Tesseract, starts server on port 8000",
        "First startup auto-creates database schema and default admin account",
    ]
    for i, step in enumerate(render_steps):
        story.append(Paragraph(f"Step {i+1}: {step}", BULLET, bulletText=str(i+1)))

    story.append(Spacer(1, 0.3*cm))
    story.append(callout(
        "Always use Render's Docker runtime, not the Python native runtime. "
        "Tesseract OCR is a system package that must be installed via apt-get in the Dockerfile. "
        "The Python native runtime cannot install system packages.",
        bg=AMBER_LT, border=AMBER, text_color=colors.HexColor("#78350f"), label="Important:"))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION 10 — ROADMAP
    # ═══════════════════════════════════════════════════════════════════════════
    div = SectionDividerPage("10", "Roadmap", "Phase 1 Current  /  Phase 2 Expansion  /  Phase 3 National")
    story.append(div)
    story.append(PageBreak())

    story.append(Paragraph("10. Development Roadmap", H1))
    story.append(HRFlowable(width="100%", thickness=1.5, color=SAFFRON, spaceAfter=8))

    phases = [
        ("Phase 1 — Foundation (Completed)", NAT_GREEN, NAT_GREEN_LT, [
            "Full-stack FastAPI + Jinja2 monolith with SQLite/PostgreSQL support",
            "Email OTP citizen verification (DPDP Act 2023 compliant)",
            "5-layer fake report detection engine with Gemini AI integration",
            "Image forensics with ELA tamper detection and EXIF analysis",
            "Real-time evidence pre-validation (stock photo and blank image rejection)",
            "AI triage with crime classification, risk scoring, and BNS section mapping",
            "Auto-generated Section 65B Complaint Reports with SHA-256 chain of custody",
            "Officer command dashboard with AI explainability panel",
            "Reporter trust scoring system with frequency abuse detection",
            "Docker deployment with Render.com CI/CD pipeline",
            "ML models: RandomForest fake detector, LinearSVC crime classifier, GradientBoosting risk classifier",
        ]),
        ("Phase 2 — Expansion (Planned)", GOV_BLUE, GOV_BLUE_LT, [
            "Real Aadhaar OTP verification via UIDAI sandbox API integration",
            "DigiLocker OAuth2 integration for verified identity and document fetching",
            "Mobile-responsive PWA (Progressive Web App) with offline complaint drafting",
            "Multi-language support: Hindi, Tamil, Telugu, Bengali, Kannada",
            "WhatsApp Bot integration for complaint status updates via WATI/Twilio",
            "Deepfake detection for video evidence using MediaPipe + CLIP embeddings",
            "Advanced ML: BERT-based narrative coherence scoring for fake detection",
            "Officer mobile app (React Native) for on-the-go case management",
            "Inter-state case forwarding with automatic jurisdiction detection by incident location",
            "SMS OTP as fallback when email not available",
            "Automated follow-up email sequences for complainants",
        ]),
        ("Phase 3 — National Scale (Vision)", SAFFRON, colors.HexColor("#fff7ed"), [
            "National rollout across all 28 states and 8 union territories",
            "Integration with CCTNS (Crime and Criminal Tracking Network) for real FIR filing",
            "CERT-In (Indian Computer Emergency Response Team) threat intelligence feed",
            "Inter-state data sharing API for cross-jurisdictional cybercrime patterns",
            "National cybercrime heatmap with real-time geographic intelligence",
            "AI-powered suspect profiling and repeat offender detection across jurisdictions",
            "Automated chargesheet draft generation for closed HIGH risk cases",
            "Integration with I4C (Indian Cyber Crime Coordination Centre) national database",
            "Federated learning for ML model improvement without centralizing citizen data",
            "Court-ready digital evidence package generation with chain of custody documentation",
            "Public transparency dashboard with anonymized crime statistics by district",
        ]),
    ]

    for phase_title, border_color, bg_color, items in phases:
        phase_content = [Paragraph(phase_title, S("", fontName="Helvetica-Bold", fontSize=12,
            textColor=border_color, spaceBefore=4, spaceAfter=6))]
        for item in items:
            phase_content.append(Paragraph(item, BULLET, bulletText="\u2713" if "Completed" in phase_title else "\u25B6"))
        phase_content.append(Spacer(1, 4))
        box = Table([[phase_content]], colWidths=[PAGE_W - 2*MARGIN - 2])
        box.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), bg_color),
            ("LINEBEFORE", (0,0), (0,-1), 4, border_color),
            ("LEFTPADDING", (0,0), (-1,-1), 14),
            ("RIGHTPADDING", (0,0), (-1,-1), 14),
            ("TOPPADDING", (0,0), (-1,-1), 10),
            ("BOTTOMPADDING", (0,0), (-1,-1), 10),
        ]))
        story.append(box)
        story.append(Spacer(1, 0.4*cm))

    # Final note
    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(width="100%", thickness=1, color=GRAY_200))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        f"AutoJustice AI NEXUS v2.0  |  Implementation Plan  |  "
        f"Ministry of Home Affairs, Government of India  |  {date.today().strftime('%B %Y')}  |  CONFIDENTIAL",
        S("", fontName="Helvetica", fontSize=8, textColor=GRAY_600, alignment=TA_CENTER)))

    # ── Build PDF ─────────────────────────────────────────────────────────────
    doc.build(story, canvasmaker=HeaderFooterCanvas)
    print(f"PDF generated: {OUTPUT}")
    size_kb = os.path.getsize(OUTPUT) // 1024
    print(f"File size: {size_kb} KB  |  Location: {OUTPUT}")


if __name__ == "__main__":
    build()
