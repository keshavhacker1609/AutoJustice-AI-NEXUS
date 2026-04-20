"""
AutoJustice AI NEXUS - Dashboard Router
Aggregated analytics, audit log, and system health for the police command dashboard.
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any
from collections import defaultdict

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models.db_models import Report, AuditLog, OfficerUser
from models.schemas import DashboardStats, RiskDistribution, ReportListItem
from routers.auth import require_officer

router = APIRouter()


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db), officer: OfficerUser = Depends(require_officer)):
    """
    Aggregated statistics for the police command dashboard.
    Called every 30 seconds for live refresh.
    """
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # ── Core counts ───────────────────────────────────────────────────
    total = db.query(func.count(Report.id)).scalar() or 0
    pending = db.query(func.count(Report.id)).filter(Report.status == "PENDING").scalar() or 0
    processing = db.query(func.count(Report.id)).filter(Report.status == "PROCESSING").scalar() or 0
    firs_gen = db.query(func.count(Report.id)).filter(Report.status == "COMPLAINT_REGISTERED").scalar() or 0
    fake_flagged = db.query(func.count(Report.id)).filter(Report.is_flagged_fake == True).scalar() or 0
    under_inv = db.query(func.count(Report.id)).filter(Report.status == "UNDER_INVESTIGATION").scalar() or 0

    # ── Risk distribution ─────────────────────────────────────────────
    high_count = db.query(func.count(Report.id)).filter(Report.risk_level == "HIGH").scalar() or 0
    medium_count = db.query(func.count(Report.id)).filter(Report.risk_level == "MEDIUM").scalar() or 0
    low_count = db.query(func.count(Report.id)).filter(Report.risk_level == "LOW").scalar() or 0

    # ── Today's HIGH risk ─────────────────────────────────────────────
    high_today = db.query(func.count(Report.id)).filter(
        Report.risk_level == "HIGH",
        Report.created_at >= today_start
    ).scalar() or 0

    # ── Top crime categories ──────────────────────────────────────────
    cat_query = db.query(
        Report.crime_category,
        func.count(Report.id).label("count")
    ).filter(
        Report.crime_category.isnot(None)
    ).group_by(Report.crime_category).order_by(func.count(Report.id).desc()).limit(8).all()

    top_categories = [
        {"category": row.crime_category, "count": row.count}
        for row in cat_query
    ]

    # ── Daily submissions (last 14 days) ──────────────────────────────
    daily_data: Dict[str, Dict[str, int]] = {}
    for i in range(13, -1, -1):
        day = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        daily_data[day] = {"date": day, "total": 0, "high": 0, "medium": 0, "low": 0}

    recent_all = db.query(Report).filter(
        Report.created_at >= now - timedelta(days=14)
    ).all()

    for r in recent_all:
        day_key = r.created_at.strftime("%Y-%m-%d")
        if day_key in daily_data:
            daily_data[day_key]["total"] += 1
            if r.risk_level == "HIGH":
                daily_data[day_key]["high"] += 1
            elif r.risk_level == "MEDIUM":
                daily_data[day_key]["medium"] += 1
            elif r.risk_level == "LOW":
                daily_data[day_key]["low"] += 1

    # ── Average authenticity score ─────────────────────────────────────
    avg_auth_row = db.query(func.avg(Report.authenticity_score)).filter(
        Report.authenticity_score.isnot(None)
    ).scalar()
    avg_auth = round(float(avg_auth_row or 0), 3)

    # ── Average tamper score ───────────────────────────────────────────
    avg_tamper_row = db.query(func.avg(Report.forensics_tamper_score)).filter(
        Report.forensics_tamper_score.isnot(None)
    ).scalar()
    avg_tamper = round(float(avg_tamper_row or 0), 3)

    # ── Recent reports ────────────────────────────────────────────────
    recent_reports_raw = db.query(Report).order_by(Report.created_at.desc()).limit(10).all()

    recent_reports = [
        ReportListItem(
            id=r.id,
            case_number=r.case_number,
            created_at=r.created_at,
            status=r.status,
            complainant_name=r.complainant_name,
            risk_level=r.risk_level,
            risk_score=r.risk_score,
            crime_category=r.crime_category,
            is_flagged_fake=r.is_flagged_fake,
            fake_recommendation=r.fake_recommendation,
            authenticity_score=r.authenticity_score,
            forensics_tamper_score=r.forensics_tamper_score,
            reporter_trust_score=r.reporter_trust_score,
            assigned_officer=r.assigned_officer,
            evidence_count=len(r.evidence_files),
        )
        for r in recent_reports_raw
    ]

    return DashboardStats(
        total_reports=total,
        pending_triage=pending + processing,
        firs_generated=firs_gen,
        fake_flagged=fake_flagged,
        under_investigation=under_inv,
        risk_distribution=RiskDistribution(
            high=high_count,
            medium=medium_count,
            low=low_count,
            pending=pending + processing,
        ),
        top_crime_categories=top_categories,
        recent_reports=recent_reports,
        daily_submissions=list(daily_data.values()),
        avg_authenticity_score=avg_auth,
        avg_tamper_score=avg_tamper,
        high_risk_today=high_today,
    )


@router.get("/audit-log")
def get_audit_log(
    limit: int = Query(default=50, le=200),
    action: str = Query(default=None),
    db: Session = Depends(get_db),
    officer: OfficerUser = Depends(require_officer),
):
    """Recent audit log entries for compliance monitoring."""
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action == action.upper())
    logs = query.order_by(AuditLog.timestamp.desc()).limit(limit).all()
    return [
        {
            "id": l.id,
            "report_id": l.report_id,
            "timestamp": l.timestamp.isoformat(),
            "action": l.action,
            "actor": l.actor,
            "actor_id": l.actor_id,
            "ip_address": l.ip_address,
            "details": l.details,
        }
        for l in logs
    ]


@router.get("/system-health")
def system_health(db: Session = Depends(get_db), officer: OfficerUser = Depends(require_officer)):
    """System health overview for the dashboard status bar."""
    now = datetime.utcnow()
    last_hour = now - timedelta(hours=1)
    last_day = now - timedelta(days=1)

    recent_submissions = db.query(func.count(Report.id)).filter(
        Report.created_at >= last_hour
    ).scalar() or 0

    recent_high_risk = db.query(func.count(Report.id)).filter(
        Report.risk_level == "HIGH",
        Report.created_at >= last_day,
    ).scalar() or 0

    pending_firs = db.query(func.count(Report.id)).filter(
        Report.risk_level.in_(["HIGH", "MEDIUM"]),
        Report.fir_path.is_(None),
        Report.is_flagged_fake == False,
        Report.status == "TRIAGED",
    ).scalar() or 0

    blocked_reporters = db.query(func.count(Report.id)).filter(
        Report.is_flagged_fake == True,
        Report.created_at >= last_day,
    ).scalar() or 0

    return {
        "status": "operational",
        "submissions_last_hour": recent_submissions,
        "high_risk_last_24h": recent_high_risk,
        "pending_fir_generation": pending_firs,
        "fake_flagged_last_24h": blocked_reporters,
        "timestamp": now.isoformat(),
    }


@router.get("/forensics-summary")
def forensics_summary(db: Session = Depends(get_db), officer: OfficerUser = Depends(require_officer)):
    """Summary of image forensics findings."""
    total_with_images = db.query(func.count(Report.id)).filter(
        Report.forensics_tamper_score.isnot(None)
    ).scalar() or 0

    tampered = db.query(func.count(Report.id)).filter(
        Report.forensics_tamper_score >= 0.55
    ).scalar() or 0

    suspicious = db.query(func.count(Report.id)).filter(
        Report.forensics_tamper_score >= 0.30,
        Report.forensics_tamper_score < 0.55,
    ).scalar() or 0

    avg_score_row = db.query(func.avg(Report.forensics_tamper_score)).filter(
        Report.forensics_tamper_score.isnot(None)
    ).scalar()

    return {
        "total_analyzed": total_with_images,
        "tampered_detected": tampered,
        "suspicious_detected": suspicious,
        "clean": max(0, total_with_images - tampered - suspicious),
        "avg_tamper_score": round(float(avg_score_row or 0), 3),
    }


@router.get("/explain/{report_id}")
def explain_ai_decision(report_id: str, db: Session = Depends(get_db), officer: OfficerUser = Depends(require_officer)):
    """
    AI Explainability endpoint — returns a human-readable breakdown of why
    the AI assigned a particular risk level and authenticity score.
    Used by the dashboard 'Why did AI decide this?' panel.
    """
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        from fastapi import HTTPException
        raise HTTPException(404, "Report not found")

    risk = report.risk_level or "UNKNOWN"
    auth = report.authenticity_score or 0.5
    entities = report.entities or {}
    fake_flags = report.fake_flags or []
    bns = report.bns_sections or []

    # ── Risk level reasoning ───────────────────────────────────────────────
    risk_reasons = []
    if risk == "HIGH":
        risk_reasons = [
            "✓ Specific financial loss amount identified" if entities.get("financial_amount") else "✗ No financial amount — lower confidence",
            "✓ Named suspect or suspect profile identified" if entities.get("suspect") else "✗ Suspect not identified",
            "✓ Specific platform identified (traceable)" if entities.get("platform") else "✗ No platform identified",
            "✓ Contact numbers or URLs extracted for investigation" if (entities.get("contact_numbers") or entities.get("urls_links")) else "✗ No contact trace available",
            f"✓ High risk score: {report.risk_score:.0%}" if report.risk_score and report.risk_score >= 0.70 else "—",
        ]
    elif risk == "MEDIUM":
        risk_reasons = [
            "⚠ Some specific details present but incomplete narrative",
            "⚠ Financial loss possible but unconfirmed",
            "⚠ Incident is credible but lacks full evidentiary chain",
            f"⚠ Risk score: {report.risk_score:.0%} — above threshold but not definitive" if report.risk_score else "—",
        ]
    else:
        risk_reasons = [
            "✗ No confirmed financial loss",
            "✗ Vague or generic description",
            "✗ No specific suspect or platform identified",
            f"✗ Low risk score: {report.risk_score:.0%}" if report.risk_score else "—",
        ]

    # ── Authenticity reasoning ─────────────────────────────────────────────
    auth_reasons = []
    rec = report.fake_recommendation or "REVIEW"
    if rec == "GENUINE":
        auth_reasons = [
            "✓ Narrative is coherent and internally consistent",
            "✓ Specific verifiable details (amounts, numbers, dates) present",
            "✓ No keyword stuffing or template patterns detected",
            "✓ Evidence aligns with description",
            f"✓ High authenticity score: {auth:.0%}",
        ]
    elif rec == "REVIEW":
        auth_reasons = [
            "⚠ Some details could be more specific",
            "⚠ AI cannot fully verify all claims without evidence",
            f"⚠ Authenticity score: {auth:.0%} — requires officer review",
        ]
    else:
        auth_reasons = fake_flags[:5] if fake_flags else [
            "✗ Report did not pass AI authenticity checks",
            "✗ Possible keyword manipulation or template usage",
        ]

    # ── Entity extraction confidence ───────────────────────────────────────
    entity_confidence = {
        "victim_identified":   bool(entities.get("victim")),
        "suspect_identified":  bool(entities.get("suspect")),
        "financial_traced":    bool(entities.get("financial_amount") and entities.get("financial_vector")),
        "platform_identified": bool(entities.get("platform")),
        "contact_available":   bool(entities.get("contact_numbers") or entities.get("urls_links")),
        "location_known":      bool(entities.get("location")),
    }
    investigability_score = sum(entity_confidence.values()) / len(entity_confidence)

    return {
        "report_id": report_id,
        "case_number": report.case_number,
        "risk_level": risk,
        "risk_score": report.risk_score,
        "authenticity_score": auth,
        "fake_recommendation": rec,
        "crime_category": report.crime_category,
        "crime_subcategory": report.crime_subcategory,

        "risk_reasoning": {
            "headline": f"Classified as {risk} risk because: {report.crime_subcategory or report.crime_category}",
            "factors": [r for r in risk_reasons if r != "—"],
        },

        "authenticity_reasoning": {
            "headline": f"Report authenticity: {rec} ({auth:.0%} confidence)",
            "factors": auth_reasons,
            "flags_detected": len(fake_flags),
            "all_flags": fake_flags,
        },

        "investigability": {
            "score": round(investigability_score, 2),
            "label": "High" if investigability_score >= 0.7 else "Medium" if investigability_score >= 0.4 else "Low",
            "entity_checks": entity_confidence,
            "note": "Higher investigability = more leads available for officers",
        },

        "legal_mapping": {
            "sections_applied": bns,
            "section_count": len(bns),
            "note": "AI-mapped based on crime category. Officer must verify applicability.",
        },

        "ai_confidence_note": (
            "This analysis was performed by Google Gemini (semantic AI) + rule-based validation. "
            "AI decisions are advisory and must be reviewed by a trained officer before legal action."
        ),
    }


@router.get("/live-stats")
def live_stats(db: Session = Depends(get_db)):
    """
    Lightweight endpoint for the citizen portal live counter.
    Shows aggregate public stats without PII.
    """
    total = db.query(func.count(Report.id)).scalar() or 0
    firs  = db.query(func.count(Report.id)).filter(Report.status == "COMPLAINT_REGISTERED").scalar() or 0
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today = db.query(func.count(Report.id)).filter(Report.created_at >= today_start).scalar() or 0
    return {
        "total_reports_processed": total,
        "firs_auto_generated": firs,
        "reports_today": today,
        "fake_blocked": db.query(func.count(Report.id)).filter(Report.is_flagged_fake == True).scalar() or 0,
    }


@router.get("/reporter-trust-summary")
def reporter_trust_summary(db: Session = Depends(get_db), officer: OfficerUser = Depends(require_officer)):
    """Summary of reporter trust distribution."""
    from models.db_models import ReporterProfile
    from sqlalchemy import case

    total = db.query(func.count(ReporterProfile.id)).scalar() or 0
    blocked = db.query(func.count(ReporterProfile.id)).filter(
        ReporterProfile.is_blocked == True
    ).scalar() or 0
    low_trust = db.query(func.count(ReporterProfile.id)).filter(
        ReporterProfile.trust_score < 0.40,
        ReporterProfile.is_blocked == False,
    ).scalar() or 0
    high_trust = db.query(func.count(ReporterProfile.id)).filter(
        ReporterProfile.trust_score >= 0.80
    ).scalar() or 0

    return {
        "total_reporter_profiles": total,
        "blocked": blocked,
        "low_trust": low_trust,
        "high_trust": high_trust,
        "neutral": max(0, total - blocked - low_trust - high_trust),
    }
