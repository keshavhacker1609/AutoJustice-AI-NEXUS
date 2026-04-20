"""
AutoJustice AI NEXUS - FIR PDF Generator
Generates legally structured Police Complaint Reports using ReportLab.
Compliant with: BNS 2023 | Indian Evidence Act Section 65B | DPDP Act 2023
"""
import logging
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional
from config import settings as _settings

logger = logging.getLogger(__name__)

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm, mm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, KeepTogether
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logger.warning("ReportLab not installed. FIR PDF generation unavailable.")


# ─── Color Palette (Government Document Standards) ────────────────────────────
COLOR_NAVY = colors.HexColor("#1a2a4a")
COLOR_SAFFRON = colors.HexColor("#FF9933")
COLOR_GREEN = colors.HexColor("#138808")
COLOR_LIGHT_BLUE = colors.HexColor("#e8f0fe")
COLOR_RED_ALERT = colors.HexColor("#c0392b")
COLOR_ORANGE_ALERT = colors.HexColor("#e67e22")
COLOR_GRAY = colors.HexColor("#7f8c8d")
COLOR_LIGHT_GRAY = colors.HexColor("#f5f6fa")
COLOR_WHITE = colors.white
COLOR_BLACK = colors.black


class ComplaintReportGenerator:
    """Generates legally structured Complaint Report PDFs with SHA-256 chain-of-custody certificates."""

    def generate(
        self,
        report_data: Dict[str, Any],
        output_path: str | Path,
    ) -> Path:
        """
        Generate a complete FIR PDF document.
        Returns the path to the generated file.
        Raises RuntimeError if ReportLab is not installed.
        """
        if not REPORTLAB_AVAILABLE:
            raise RuntimeError(
                "ReportLab is not installed. Run: pip install reportlab"
            )

        output_path = Path(output_path)
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=1.5*cm,
            bottomMargin=1.5*cm,
        )

        styles = self._build_styles()
        story = []

        # ── Sections ──────────────────────────────────────────────────
        story.extend(self._build_header(styles, report_data))
        story.append(Spacer(1, 8*mm))
        story.extend(self._build_case_info_table(styles, report_data))
        story.append(Spacer(1, 6*mm))
        story.extend(self._build_complainant_section(styles, report_data))
        story.append(Spacer(1, 6*mm))
        story.extend(self._build_incident_section(styles, report_data))
        story.append(Spacer(1, 6*mm))
        story.extend(self._build_entities_section(styles, report_data))
        story.append(Spacer(1, 6*mm))
        story.extend(self._build_legal_sections(styles, report_data))
        story.append(Spacer(1, 6*mm))
        story.extend(self._build_evidence_chain(styles, report_data))
        story.append(Spacer(1, 8*mm))
        story.extend(self._build_ai_analysis_section(styles, report_data))
        story.append(Spacer(1, 10*mm))
        story.extend(self._build_signature_section(styles, report_data))
        story.append(Spacer(1, 8*mm))
        story.extend(self._build_section_65b_certificate(styles, report_data))

        doc.build(story)
        logger.info(f"Complaint Report generated: {output_path}")
        return output_path

    def _build_styles(self):
        styles = getSampleStyleSheet()
        custom = {
            "CRTitle": ParagraphStyle(
                "CRTitle", parent=styles["Normal"],
                fontSize=16, fontName="Helvetica-Bold",
                textColor=COLOR_NAVY, alignment=TA_CENTER,
                spaceAfter=2*mm,
            ),
            "CRSubTitle": ParagraphStyle(
                "CRSubTitle", parent=styles["Normal"],
                fontSize=11, fontName="Helvetica",
                textColor=COLOR_NAVY, alignment=TA_CENTER,
                spaceAfter=1*mm,
            ),
            "SectionHeader": ParagraphStyle(
                "SectionHeader", parent=styles["Normal"],
                fontSize=10, fontName="Helvetica-Bold",
                textColor=COLOR_WHITE, alignment=TA_LEFT,
                backColor=COLOR_NAVY, spaceBefore=2*mm,
                leftIndent=3*mm, spaceAfter=2*mm,
            ),
            "FieldLabel": ParagraphStyle(
                "FieldLabel", parent=styles["Normal"],
                fontSize=8, fontName="Helvetica-Bold",
                textColor=COLOR_GRAY,
            ),
            "FieldValue": ParagraphStyle(
                "FieldValue", parent=styles["Normal"],
                fontSize=9, fontName="Helvetica",
                textColor=COLOR_BLACK,
            ),
            "CRBodyText": ParagraphStyle(
                "CRBodyText", parent=styles["Normal"],
                fontSize=9, fontName="Helvetica",
                textColor=COLOR_BLACK, alignment=TA_JUSTIFY,
                leading=14,
            ),
            "AlertHigh": ParagraphStyle(
                "AlertHigh", parent=styles["Normal"],
                fontSize=10, fontName="Helvetica-Bold",
                textColor=COLOR_WHITE, backColor=COLOR_RED_ALERT,
                alignment=TA_CENTER, spaceBefore=2*mm, spaceAfter=2*mm,
            ),
            "AlertMedium": ParagraphStyle(
                "AlertMedium", parent=styles["Normal"],
                fontSize=10, fontName="Helvetica-Bold",
                textColor=COLOR_WHITE, backColor=COLOR_ORANGE_ALERT,
                alignment=TA_CENTER, spaceBefore=2*mm, spaceAfter=2*mm,
            ),
            "HashText": ParagraphStyle(
                "HashText", parent=styles["Normal"],
                fontSize=7, fontName="Courier",
                textColor=COLOR_GRAY, wordWrap="CJK",
            ),
            "CertText": ParagraphStyle(
                "CertText", parent=styles["Normal"],
                fontSize=8, fontName="Helvetica",
                textColor=COLOR_NAVY, alignment=TA_JUSTIFY,
                leading=12,
            ),
            "SmallGray": ParagraphStyle(
                "SmallGray", parent=styles["Normal"],
                fontSize=7, fontName="Helvetica",
                textColor=COLOR_GRAY,
            ),
        }
        # Wrap in try/except: getSampleStyleSheet() is a global singleton,
        # so styles already added on a previous call must be skipped gracefully.
        for name, style in custom.items():
            try:
                styles.add(style)
            except KeyError:
                pass  # Already registered from a previous call — safe to skip
        return styles

    def _build_header(self, styles, data: dict):
        elements = []

        # Tricolor banner
        banner_data = [[" ", " ", " "]]
        banner = Table(banner_data, colWidths=["33%", "34%", "33%"])
        banner.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), COLOR_SAFFRON),
            ("BACKGROUND", (1, 0), (1, 0), COLOR_WHITE),
            ("BACKGROUND", (2, 0), (2, 0), COLOR_GREEN),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [None]),
            ("ROWHEIGHT", (0, 0), (0, 0), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        elements.append(banner)
        elements.append(Spacer(1, 4*mm))

        from config import settings
        elements.append(Paragraph("POLICE COMPLAINT REPORT (PCR)", styles["CRTitle"]))
        elements.append(Paragraph("Cyber Crime Police Station — Automated Intelligence Division", styles["CRSubTitle"]))
        elements.append(Paragraph(settings.station_name.upper(), styles["CRSubTitle"]))
        elements.append(Paragraph(settings.station_address, styles["SmallGray"]))

        elements.append(Spacer(1, 3*mm))
        elements.append(HRFlowable(width="100%", thickness=2, color=COLOR_NAVY))

        # Risk level alert banner
        risk_level = data.get("risk_level", "LOW")
        if risk_level == "HIGH":
            elements.append(Spacer(1, 2*mm))
            elements.append(Paragraph(
                f"⚠ HIGH RISK CASE — IMMEDIATE POLICE ACTION REQUIRED",
                styles["AlertHigh"]
            ))
        elif risk_level == "MEDIUM":
            elements.append(Spacer(1, 2*mm))
            elements.append(Paragraph(
                f"⚡ MEDIUM RISK CASE — PRIORITY REVIEW REQUIRED",
                styles["AlertMedium"]
            ))

        return elements

    def _build_case_info_table(self, styles, data: dict):
        elements = [Paragraph(" CASE INFORMATION", styles["SectionHeader"])]

        now = datetime.utcnow()
        row_data = [
            [
                Paragraph("Complaint No.:", styles["FieldLabel"]),
                Paragraph(data.get("case_number", "N/A"), styles["FieldValue"]),
                Paragraph("Date of Complaint:", styles["FieldLabel"]),
                Paragraph(now.strftime("%d %B %Y"), styles["FieldValue"]),
            ],
            [
                Paragraph("Time of Complaint:", styles["FieldLabel"]),
                Paragraph(now.strftime("%H:%M:%S UTC"), styles["FieldValue"]),
                Paragraph("Risk Level:", styles["FieldLabel"]),
                Paragraph(f"{data.get('risk_level', 'N/A')} (Score: {data.get('risk_score', 0):.0%})", styles["FieldValue"]),
            ],
            [
                Paragraph("Crime Category:", styles["FieldLabel"]),
                Paragraph(data.get("crime_category", "N/A"), styles["FieldValue"]),
                Paragraph("Subcategory:", styles["FieldLabel"]),
                Paragraph(data.get("crime_subcategory", "N/A"), styles["FieldValue"]),
            ],
            [
                Paragraph("Status:", styles["FieldLabel"]),
                Paragraph("FIR REGISTERED — AUTO-GENERATED", styles["FieldValue"]),
                Paragraph("Authenticity:", styles["FieldLabel"]),
                Paragraph(
                    f"{data.get('fake_recommendation', 'REVIEW')} "
                    f"({data.get('authenticity_score', 0):.0%})",
                    styles["FieldValue"]
                ),
            ],
        ]

        table = Table(row_data, colWidths=["20%", "30%", "20%", "30%"])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), COLOR_LIGHT_GRAY),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [COLOR_WHITE, COLOR_LIGHT_GRAY]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dde1e7")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        elements.append(table)
        return elements

    def _build_complainant_section(self, styles, data: dict):
        elements = [Paragraph(" COMPLAINANT DETAILS", styles["SectionHeader"])]

        rows = [
            [Paragraph("Full Name:", styles["FieldLabel"]),
             Paragraph(data.get("complainant_name", "N/A"), styles["FieldValue"]),
             Paragraph("Phone:", styles["FieldLabel"]),
             Paragraph(data.get("complainant_phone", "Not provided"), styles["FieldValue"])],
            [Paragraph("Email:", styles["FieldLabel"]),
             Paragraph(data.get("complainant_email", "Not provided"), styles["FieldValue"]),
             Paragraph("Address:", styles["FieldLabel"]),
             Paragraph(data.get("complainant_address", "Not provided"), styles["FieldValue"])],
        ]

        table = Table(rows, colWidths=["20%", "30%", "20%", "30%"])
        table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dde1e7")),
            ("BACKGROUND", (0, 0), (-1, -1), COLOR_LIGHT_BLUE),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        elements.append(table)
        return elements

    def _build_incident_section(self, styles, data: dict):
        elements = [Paragraph(" INCIDENT DESCRIPTION", styles["SectionHeader"])]

        meta_rows = [[
            Paragraph("Date of Incident:", styles["FieldLabel"]),
            Paragraph(data.get("incident_date", "Not specified"), styles["FieldValue"]),
            Paragraph("Location:", styles["FieldLabel"]),
            Paragraph(data.get("incident_location", "Not specified"), styles["FieldValue"]),
        ]]
        meta_table = Table(meta_rows, colWidths=["20%", "30%", "20%", "30%"])
        meta_table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dde1e7")),
            ("BACKGROUND", (0, 0), (-1, -1), COLOR_LIGHT_GRAY),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(meta_table)
        elements.append(Spacer(1, 3*mm))

        elements.append(Paragraph("<b>Complainant Statement:</b>", styles["CRBodyText"]))
        elements.append(Spacer(1, 2*mm))
        elements.append(Paragraph(
            data.get("incident_description", "N/A").replace("\n", "<br/>"),
            styles["CRBodyText"]
        ))

        if data.get("ai_summary"):
            elements.append(Spacer(1, 3*mm))
            elements.append(Paragraph("<b>AI Case Summary (Auto-Generated):</b>", styles["FieldLabel"]))
            elements.append(Paragraph(data["ai_summary"], styles["CRBodyText"]))

        return elements

    def _build_entities_section(self, styles, data: dict):
        elements = [Paragraph(" EXTRACTED ENTITIES (AI-IDENTIFIED)", styles["SectionHeader"])]

        entities = data.get("entities", {}) or {}
        entity_rows = [
            [Paragraph("Victim:", styles["FieldLabel"]),
             Paragraph(str(entities.get("victim") or "Not identified"), styles["FieldValue"]),
             Paragraph("Suspect:", styles["FieldLabel"]),
             Paragraph(str(entities.get("suspect") or "Unknown"), styles["FieldValue"])],
            [Paragraph("Financial Loss:", styles["FieldLabel"]),
             Paragraph(str(entities.get("financial_amount") or "Not mentioned"), styles["FieldValue"]),
             Paragraph("Financial Vector:", styles["FieldLabel"]),
             Paragraph(str(entities.get("financial_vector") or "Not identified"), styles["FieldValue"])],
            [Paragraph("Platform:", styles["FieldLabel"]),
             Paragraph(str(entities.get("platform") or "Not specified"), styles["FieldValue"]),
             Paragraph("Location:", styles["FieldLabel"]),
             Paragraph(str(entities.get("location") or "Not specified"), styles["FieldValue"])],
        ]

        # Contact numbers and URLs
        contacts = entities.get("contact_numbers", []) or []
        urls = entities.get("urls_links", []) or []
        if contacts or urls:
            entity_rows.append([
                Paragraph("Phone Numbers:", styles["FieldLabel"]),
                Paragraph(", ".join(str(c) for c in contacts) or "None", styles["FieldValue"]),
                Paragraph("URLs / Handles:", styles["FieldLabel"]),
                Paragraph(", ".join(str(u) for u in urls) or "None", styles["FieldValue"]),
            ])

        table = Table(entity_rows, colWidths=["20%", "30%", "20%", "30%"])
        table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dde1e7")),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [COLOR_WHITE, COLOR_LIGHT_GRAY]),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        elements.append(table)
        return elements

    def _build_legal_sections(self, styles, data: dict):
        elements = [Paragraph(" APPLICABLE LEGAL SECTIONS (BNS / IT ACT)", styles["SectionHeader"])]

        sections = data.get("bns_sections", []) or []
        if not sections:
            elements.append(Paragraph("No specific sections identified by AI.", styles["CRBodyText"]))
            return elements

        section_rows = [[Paragraph(f"• {s}", styles["FieldValue"])] for s in sections]
        table = Table(section_rows, colWidths=["100%"])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), COLOR_LIGHT_BLUE),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#c5d3f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(table)
        return elements

    def _build_evidence_chain(self, styles, data: dict):
        elements = [Paragraph(" DIGITAL EVIDENCE CHAIN OF CUSTODY (Section 65B)", styles["SectionHeader"])]

        evidence_files = data.get("evidence_files", [])
        if not evidence_files:
            elements.append(Paragraph("No evidence files attached to this report.", styles["CRBodyText"]))
            return elements

        header_row = [
            Paragraph("File Name", styles["FieldLabel"]),
            Paragraph("Type", styles["FieldLabel"]),
            Paragraph("SHA-256 Hash (Immutable)", styles["FieldLabel"]),
            Paragraph("OCR Conf.", styles["FieldLabel"]),
            Paragraph("Upload Time", styles["FieldLabel"]),
        ]
        rows = [header_row]

        for ef in evidence_files:
            rows.append([
                Paragraph(str(ef.get("original_filename", ""))[:40], styles["HashText"]),
                Paragraph(str(ef.get("file_type", "")), styles["HashText"]),
                Paragraph(str(ef.get("sha256_hash", ""))[:64], styles["HashText"]),
                Paragraph(f"{ef.get('ocr_confidence', 0):.0%}", styles["HashText"]),
                Paragraph(str(ef.get("uploaded_at", ""))[:19], styles["HashText"]),
            ])

        table = Table(rows, colWidths=["25%", "8%", "38%", "10%", "19%"])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), COLOR_WHITE),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [COLOR_WHITE, COLOR_LIGHT_GRAY]),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#dde1e7")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        elements.append(table)

        # Report content hash
        if data.get("content_hash"):
            elements.append(Spacer(1, 2*mm))
            elements.append(Paragraph(
                f"<b>Report Content Hash (SHA-256):</b> {data['content_hash']}",
                styles["HashText"]
            ))

        return elements

    def _build_ai_analysis_section(self, styles, data: dict):
        elements = [Paragraph(" AI FORENSIC ANALYSIS REPORT", styles["SectionHeader"])]

        fake_rec = data.get("fake_recommendation", "REVIEW")
        auth_score = data.get("authenticity_score", 0.5)
        fake_flags = data.get("fake_flags", []) or []

        analysis_rows = [
            [Paragraph("Authenticity Score:", styles["FieldLabel"]),
             Paragraph(f"{auth_score:.0%}", styles["FieldValue"]),
             Paragraph("AI Recommendation:", styles["FieldLabel"]),
             Paragraph(fake_rec, styles["FieldValue"])],
            [Paragraph("Risk Score:", styles["FieldLabel"]),
             Paragraph(f"{data.get('risk_score', 0):.0%}", styles["FieldValue"]),
             Paragraph("Risk Category:", styles["FieldLabel"]),
             Paragraph(data.get("risk_level", "N/A"), styles["FieldValue"])],
        ]

        table = Table(analysis_rows, colWidths=["20%", "30%", "20%", "30%"])
        table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dde1e7")),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [COLOR_LIGHT_BLUE, COLOR_WHITE]),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(table)

        if fake_flags:
            elements.append(Spacer(1, 2*mm))
            elements.append(Paragraph("<b>Anomaly Flags:</b>", styles["FieldLabel"]))
            for flag in fake_flags:
                elements.append(Paragraph(f"• {flag}", styles["SmallGray"]))

        elements.append(Spacer(1, 2*mm))
        elements.append(Paragraph(
            "<i>Note: AI analysis is advisory only. A trained officer must review this Complaint Report before any legal action is taken. AI outputs do not constitute "
            "prima facie evidence.</i>",
            styles["SmallGray"]
        ))

        return elements

    def _build_signature_section(self, styles, data: dict):
        elements = [HRFlowable(width="100%", thickness=1, color=COLOR_NAVY)]
        elements.append(Spacer(1, 4*mm))

        sig_rows = [[
            Paragraph("Complainant Signature / Thumb Impression", styles["FieldLabel"]),
            Paragraph("Investigating Officer", styles["FieldLabel"]),
            Paragraph("Station House Officer (SHO)", styles["FieldLabel"]),
        ]]
        sig_rows.append([
            Paragraph("\n\n\n______________________", styles["FieldValue"]),
            Paragraph("\n\n\n______________________", styles["FieldValue"]),
            Paragraph("\n\n\n______________________", styles["FieldValue"]),
        ])
        sig_rows.append([
            Paragraph(data.get("complainant_name", ""), styles["SmallGray"]),
            Paragraph(data.get("assigned_officer", "Officer Assigned"), styles["SmallGray"]),
            Paragraph("Date: _______________", styles["SmallGray"]),
        ])

        table = Table(sig_rows, colWidths=["33%", "34%", "33%"])
        table.setStyle(TableStyle([
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        elements.append(table)
        return elements

    def _build_section_65b_certificate(self, styles, data: dict):
        elements = []
        elements.append(HRFlowable(width="100%", thickness=1, color=COLOR_GRAY, lineCap="round"))
        elements.append(Spacer(1, 3*mm))
        elements.append(Paragraph("SECTION 65B CERTIFICATE — INDIAN EVIDENCE ACT, 1872", styles["FieldLabel"]))
        elements.append(Spacer(1, 2*mm))

        cert_text = (
            f"I, the authorized system custodian of AutoJustice AI NEXUS ({data.get('case_number', 'N/A')}), "
            f"hereby certify that the electronic records contained in this Police Complaint Report "
            f"were produced by AutoJustice AI NEXUS (Version {_settings.app_version}), an automated digital forensics "
            f"system operating under the supervision of the Cyber Crime Investigation Unit. "
            f"The records were produced from legitimate digital activities and the computer system "
            f"was functioning properly at the time of generation. "
            f"Content Integrity Hash (SHA-256): {data.get('content_hash', 'N/A')}. "
            f"Generated on: {datetime.utcnow().strftime('%d %B %Y at %H:%M:%S UTC')}."
        )
        elements.append(Paragraph(cert_text, styles["CertText"]))
        elements.append(Spacer(1, 3*mm))
        elements.append(Paragraph(
            "Generated by AutoJustice AI NEXUS | Powered by Google Gemini + Tesseract OCR | "
            "DPDP Act 2023 Compliant | For law enforcement use only.",
            styles["SmallGray"]
        ))
        return elements
