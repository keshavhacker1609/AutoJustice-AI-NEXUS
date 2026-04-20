"""
Explainable-AI Case Report generator.
Produces a forensically-styled PDF per case describing:
  • Case metadata + complainant
  • Evidence chain-of-custody (SHA-256 + forensic scores)
  • AI triage reasoning
  • Authenticity / fake-detection reasoning
  • Entity extraction breakdown & investigability score
  • BNS 2023 legal mapping
  • Jurisdiction detection
  • Officer-facing recommendation
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
    HRFlowable,
)


_navy = colors.HexColor("#1a3f6f")
_accent = colors.HexColor("#b8860b")
_light = colors.HexColor("#f4f4f8")


def _styles():
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle(
        name="Cover", fontName="Helvetica-Bold", fontSize=22,
        alignment=1, textColor=_navy, spaceAfter=12))
    ss.add(ParagraphStyle(
        name="H1", fontName="Helvetica-Bold", fontSize=14,
        textColor=_navy, spaceBefore=10, spaceAfter=6))
    ss.add(ParagraphStyle(
        name="H2", fontName="Helvetica-Bold", fontSize=11,
        textColor=_accent, spaceBefore=6, spaceAfter=4))
    ss.add(ParagraphStyle(
        name="Body", fontName="Helvetica", fontSize=10, leading=14))
    ss.add(ParagraphStyle(
        name="Mono", fontName="Courier", fontSize=9, leading=12))
    ss.add(ParagraphStyle(
        name="Tag", fontName="Helvetica", fontSize=9, leading=11,
        textColor=colors.grey))
    return ss


def _kv_table(rows, col_widths=(5 * cm, 11.5 * cm)):
    t = Table(rows, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), _light),
        ("TEXTCOLOR",  (0, 0), (0, -1), _navy),
        ("FONTNAME",   (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME",   (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE",   (0, 0), (-1, -1), 9),
        ("VALIGN",     (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",(0, 0), (-1, -1), 6),
        ("RIGHTPADDING",(0,0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0,0),(-1, -1), 5),
        ("GRID",       (0, 0), (-1, -1), 0.25, colors.lightgrey),
    ]))
    return t


def _risk_badge(level: str):
    color = {"HIGH": colors.HexColor("#d92d20"),
             "MEDIUM": colors.HexColor("#e58a00"),
             "LOW": colors.HexColor("#067647")}.get(level, colors.grey)
    t = Table([[f"  RISK: {level}  "]], colWidths=[6 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color),
        ("TEXTCOLOR",  (0, 0), (-1, -1), colors.white),
        ("FONTNAME",   (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, -1), 13),
        ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING",(0,0),(-1,-1), 7),
    ]))
    return t


def generate(case: Dict[str, Any], explain: Dict[str, Any], jurisdiction: Dict[str, Any],
             out_path: Path) -> Path:
    """Render an Explainable-AI PDF report for a single case."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(out_path), pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm,
        title=f"XAI Report — {case.get('case_number', '?')}",
    )
    ss = _styles()
    story = []

    # ── Cover header ──
    story.append(Paragraph("AutoJustice AI NEXUS", ss["Cover"]))
    story.append(Paragraph("Explainable-AI Case Report", ss["H1"]))
    story.append(HRFlowable(width="100%", thickness=1.2, color=_navy))
    story.append(Spacer(1, 8))

    story.append(_risk_badge(case.get("risk_level", "UNKNOWN")))
    story.append(Spacer(1, 10))

    # ── Case metadata ──
    story.append(Paragraph("1. Case Metadata", ss["H1"]))
    story.append(_kv_table([
        ["Case Number",   case.get("case_number", "—")],
        ["Case ID",       case.get("id", "—")],
        ["Filed (UTC)",   str(case.get("created_at", "—"))[:19]],
        ["Status",        case.get("status", "—")],
        ["Crime Category",f"{case.get('crime_category','—')} / {case.get('crime_subcategory','—')}"],
        ["Risk Level",    f"{case.get('risk_level','?')}  (score {case.get('risk_score',0):.2%})"],
        ["Authenticity",  f"{case.get('fake_recommendation','?')}  ({case.get('authenticity_score',0):.0%})"],
    ]))
    story.append(Spacer(1, 8))

    # ── Complainant ──
    story.append(Paragraph("2. Complainant", ss["H1"]))
    story.append(_kv_table([
        ["Name",    case.get("complainant_name", "—")],
        ["Email",   case.get("complainant_email", "—") or "—"],
        ["Phone",   case.get("complainant_phone", "—") or "—"],
        ["Address", case.get("complainant_address", "—") or "—"],
        ["Reporter Trust", f"{case.get('reporter_trust_score', 0):.0%}"],
    ]))
    story.append(Spacer(1, 8))

    # ── Incident ──
    story.append(Paragraph("3. Incident", ss["H1"]))
    story.append(_kv_table([
        ["Date",     str(case.get("incident_date", "—"))[:10]],
        ["Location", case.get("incident_location", "—") or "—"],
    ]))
    story.append(Spacer(1, 4))
    story.append(Paragraph("<b>Description</b>", ss["H2"]))
    desc = (case.get("incident_description") or "—").replace("\n", "<br/>")
    story.append(Paragraph(desc, ss["Body"]))
    story.append(Spacer(1, 8))

    # ── Evidence + chain of custody ──
    story.append(Paragraph("4. Evidence &amp; Chain of Custody", ss["H1"]))
    ev_files = case.get("evidence_files") or []
    if ev_files:
        rows = [["#", "File", "Type", "SHA-256 (first 16)", "Tamper"]]
        for i, ev in enumerate(ev_files, 1):
            rows.append([
                str(i),
                (ev.get("original_filename") or "")[:32],
                ev.get("file_type", "—"),
                (ev.get("content_hash") or "")[:16] + "…",
                f"{ev.get('tamper_score',0):.2f}" if ev.get("tamper_score") is not None else "—",
            ])
        t = Table(rows, colWidths=[0.8*cm, 5.5*cm, 2.2*cm, 5*cm, 2.5*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0), _navy),
            ("TEXTCOLOR", (0,0),(-1,0), colors.white),
            ("FONTNAME",  (0,0),(-1,0), "Helvetica-Bold"),
            ("FONTSIZE",  (0,0),(-1,-1), 8),
            ("GRID",      (0,0),(-1,-1), 0.25, colors.lightgrey),
            ("VALIGN",    (0,0),(-1,-1), "MIDDLE"),
        ]))
        story.append(t)
        story.append(Spacer(1, 4))
        story.append(Paragraph(
            "Each evidence artefact is hashed at upload. Tamper score combines ELA, metadata "
            "anomalies and content-hash verification (Section 65B, Indian Evidence Act).",
            ss["Tag"]))
    else:
        story.append(Paragraph("No evidence files attached.", ss["Body"]))
    story.append(Spacer(1, 8))

    # ── AI Risk reasoning ──
    rr = explain.get("risk_reasoning", {})
    story.append(Paragraph("5. AI Risk-Level Reasoning", ss["H1"]))
    story.append(Paragraph(f"<b>{rr.get('headline','—')}</b>", ss["Body"]))
    story.append(Spacer(1, 4))
    for f in rr.get("factors", []):
        story.append(Paragraph("• " + f, ss["Body"]))
    story.append(Spacer(1, 8))

    # ── Authenticity reasoning ──
    ar = explain.get("authenticity_reasoning", {})
    story.append(Paragraph("6. Authenticity / Fake-Report Reasoning", ss["H1"]))
    story.append(Paragraph(f"<b>{ar.get('headline','—')}</b>", ss["Body"]))
    story.append(Spacer(1, 4))
    for f in ar.get("factors", []):
        story.append(Paragraph("• " + f, ss["Body"]))
    if ar.get("all_flags"):
        story.append(Spacer(1, 4))
        story.append(Paragraph(f"<b>Flags detected ({ar.get('flags_detected',0)}):</b>", ss["H2"]))
        for fl in ar["all_flags"][:10]:
            story.append(Paragraph("• " + str(fl), ss["Body"]))
    story.append(Spacer(1, 8))

    # ── Investigability ──
    inv = explain.get("investigability", {})
    story.append(Paragraph("7. Investigability Score", ss["H1"]))
    story.append(Paragraph(
        f"<b>{inv.get('label','—')}</b> — score {inv.get('score',0):.2f}/1.00",
        ss["Body"]))
    checks = inv.get("entity_checks", {})
    rows = [[k.replace("_", " ").title(), "YES" if v else "no"] for k, v in checks.items()]
    if rows:
        story.append(Spacer(1, 4))
        story.append(_kv_table(rows))
    story.append(Spacer(1, 8))

    # ── Legal mapping ──
    lm = explain.get("legal_mapping", {})
    story.append(Paragraph("8. Legal Mapping — BNS 2023", ss["H1"]))
    sections = lm.get("sections_applied") or []
    if sections:
        for s in sections:
            story.append(Paragraph("• " + str(s), ss["Body"]))
    else:
        story.append(Paragraph("No BNS sections auto-mapped.", ss["Body"]))
    story.append(Spacer(1, 4))
    story.append(Paragraph(lm.get("note", ""), ss["Tag"]))
    story.append(Spacer(1, 8))

    # ── Jurisdiction ──
    if jurisdiction:
        story.append(Paragraph("9. Jurisdiction Detection", ss["H1"]))
        story.append(_kv_table([
            ["Detected State",    jurisdiction.get("detected_state",   "—") or "—"],
            ["Detected District", jurisdiction.get("detected_district","—") or "—"],
            ["Jurisdiction Name", jurisdiction.get("jurisdiction_name","—") or "—"],
            ["Confidence",        f"{jurisdiction.get('confidence',0):.0%}"],
            ["Requires Forwarding", "YES" if jurisdiction.get("requires_forwarding") else "no"],
            ["Reason",            jurisdiction.get("reason", "—") or "—"],
        ]))
        mk = jurisdiction.get("matched_keywords") or []
        if mk:
            story.append(Spacer(1, 3))
            story.append(Paragraph("Matched keywords: " + ", ".join(str(k) for k in mk[:10]), ss["Tag"]))
        story.append(Spacer(1, 8))

    # ── Officer recommendation ──
    story.append(Paragraph("10. Officer Recommendation", ss["H1"]))
    risk = case.get("risk_level", "LOW")
    rec = {
        "HIGH":   "Immediate action: register FIR, preserve evidence, coordinate with cyber-cell "
                  "and banking partners for transaction freeze within 24 hours.",
        "MEDIUM": "Review: verify complainant details, request supporting documents, schedule "
                  "statement within 7 days. Generate FIR upon verification.",
        "LOW":    "Triage: cross-check database for similar patterns. Issue acknowledgement; "
                  "request additional evidence before FIR registration.",
    }.get(risk, "Officer review required.")
    story.append(Paragraph(rec, ss["Body"]))
    story.append(Spacer(1, 8))

    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        explain.get("ai_confidence_note",
            "AI decisions are advisory. Officer must verify before legal action."),
        ss["Tag"]))
    story.append(Paragraph(
        f"Generated {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC  •  "
        f"AutoJustice AI NEXUS — XAI Engine v2.0",
        ss["Tag"]))

    doc.build(story)
    return out_path


def generate_index(cases: list[dict], out_path: Path) -> Path:
    """Cover page listing all generated XAI reports."""
    doc = SimpleDocTemplate(str(out_path), pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    ss = _styles()
    story = [
        Paragraph("AutoJustice AI NEXUS", ss["Cover"]),
        Paragraph("Complete Workflow Demo — Case Gallery", ss["H1"]),
        HRFlowable(width="100%", thickness=1.2, color=_navy),
        Spacer(1, 8),
        Paragraph(
            f"This demo submitted <b>{len(cases)}</b> representative cases through the entire AutoJustice "
            "pipeline. Each case below has a dedicated Explainable-AI PDF in the "
            "<font face='Courier'>xai/</font> folder.",
            ss["Body"]),
        Spacer(1, 8),
    ]
    rows = [["#", "Case No.", "Risk", "Category", "Auth", "Jurisdiction", "XAI Report"]]
    for i, c in enumerate(cases, 1):
        rows.append([
            str(i),
            c.get("case_number", "—"),
            c.get("risk_level", "—"),
            (c.get("crime_category") or "—")[:22],
            f"{(c.get('authenticity_score') or 0):.0%}",
            (c.get("detected_state") or "—")[:16],
            f"xai/{c.get('case_number','?')}.pdf",
        ])
    t = Table(rows, colWidths=[0.7*cm, 3.5*cm, 1.5*cm, 4*cm, 1.4*cm, 3*cm, 4*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0), _navy),
        ("TEXTCOLOR", (0,0),(-1,0), colors.white),
        ("FONTNAME",  (0,0),(-1,0), "Helvetica-Bold"),
        ("FONTSIZE",  (0,0),(-1,-1), 8),
        ("GRID",      (0,0),(-1,-1), 0.25, colors.lightgrey),
        ("VALIGN",    (0,0),(-1,-1), "MIDDLE"),
    ]))
    story.append(t)
    story.append(Spacer(1, 14))
    story.append(Paragraph(
        "Each XAI report explains the AI's reasoning for risk level, authenticity, "
        "entity extraction, BNS legal mapping and jurisdictional routing — designed "
        "to be auditable and reviewable by a trained officer.",
        ss["Tag"]))
    doc.build(story)
    return out_path
