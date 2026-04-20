"""
AutoJustice AI NEXUS - Case Management Router
Officer actions: assign cases, update status, add notes, search, export.
All actions are audited and role-protected.
"""
import uuid
import csv
import io
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from database import get_db
from models.db_models import Report, OfficerUser, AuditLog, CaseNote
from models.schemas import (
    CaseAssignRequest, CaseStatusUpdateRequest, CaseNoteCreate,
    CaseNoteResponse, CaseSearchRequest, ReportListItem, ReportResponse,
)
from routers.auth import require_officer, get_current_officer
from services.followup_email_service import followup_service

logger = logging.getLogger(__name__)
router = APIRouter()

VALID_STATUSES = {
    "PENDING", "PROCESSING", "TRIAGED",
    "COMPLAINT_REGISTERED", "UNDER_INVESTIGATION", "CLOSED", "ARCHIVED"
}


# ─── Case Assignment ──────────────────────────────────────────────────────────

@router.post("/{report_id}/assign")
def assign_case(
    report_id: str,
    payload: CaseAssignRequest,
    db: Session = Depends(get_db),
    officer: OfficerUser = Depends(require_officer),
):
    """Assign a case to an officer."""
    report = _get_report_or_404(report_id, db)

    target_officer = db.query(OfficerUser).filter(
        OfficerUser.id == payload.officer_id,
        OfficerUser.is_active == True,
    ).first()
    if not target_officer:
        raise HTTPException(404, "Target officer not found or inactive.")

    prev_officer = report.assigned_officer
    report.assigned_officer = target_officer.full_name
    report.assigned_officer_id = target_officer.id

    if payload.notes:
        note = CaseNote(
            id=str(uuid.uuid4()),
            report_id=report.id,
            officer_id=officer.id,
            note_text=f"Case assigned to {target_officer.full_name}. {payload.notes}",
            is_internal=True,
        )
        db.add(note)

    db.add(AuditLog(
        id=str(uuid.uuid4()),
        report_id=report.id,
        action="CASE_ASSIGNED",
        actor=officer.username,
        actor_id=officer.id,
        details={
            "assigned_to": target_officer.full_name,
            "assigned_to_id": target_officer.id,
            "previous_officer": prev_officer,
        },
    ))
    db.commit()
    return {"success": True, "assigned_to": target_officer.full_name}


# ─── Status Updates ───────────────────────────────────────────────────────────

@router.patch("/{report_id}/status")
def update_status(
    report_id: str,
    payload: CaseStatusUpdateRequest,
    db: Session = Depends(get_db),
    officer: OfficerUser = Depends(require_officer),
):
    """Update case status with optional reason."""
    from fastapi import BackgroundTasks
    from config import settings

    report = _get_report_or_404(report_id, db)

    if payload.status not in VALID_STATUSES:
        raise HTTPException(400, f"Invalid status. Valid: {', '.join(sorted(VALID_STATUSES))}")

    prev_status = report.status
    report.status = payload.status

    if payload.status == "CLOSED":
        report.closed_at = datetime.utcnow()
        report.closure_reason = payload.reason

    if payload.reason:
        note = CaseNote(
            id=str(uuid.uuid4()),
            report_id=report.id,
            officer_id=officer.id,
            note_text=f"Status changed to {payload.status}. Reason: {payload.reason}",
            is_internal=True,
        )
        db.add(note)

    db.add(AuditLog(
        id=str(uuid.uuid4()),
        report_id=report.id,
        action="STATUS_UPDATED",
        actor=officer.username,
        actor_id=officer.id,
        details={"from": prev_status, "to": payload.status, "reason": payload.reason},
    ))
    db.commit()

    # ── Phase 2: Send closure/status email to complainant ─────────────
    if report.complainant_email:
        if payload.status == "CLOSED":
            followup_service.send_closure_update(
                to_email=report.complainant_email,
                name=report.complainant_name,
                case_number=report.case_number,
                closure_reason=payload.reason or "Case has been closed by the investigating officer.",
                crime_category=report.crime_category or "Cybercrime",
                station_name=settings.station_name,
            )
        elif payload.status == "UNDER_INVESTIGATION":
            followup_service.send_status_update(
                to_email=report.complainant_email,
                name=report.complainant_name,
                case_number=report.case_number,
                status=payload.status,
                risk_level=report.risk_level or "MEDIUM",
                crime_category=report.crime_category or "Cybercrime",
                assigned_officer=report.assigned_officer,
                station_name=settings.station_name,
                hours_elapsed=0,
            )

    return {"success": True, "status": payload.status}


# ─── Case Notes ───────────────────────────────────────────────────────────────

@router.post("/{report_id}/notes", response_model=CaseNoteResponse)
def add_note(
    report_id: str,
    payload: CaseNoteCreate,
    db: Session = Depends(get_db),
    officer: OfficerUser = Depends(require_officer),
):
    """Add an internal or public note to a case."""
    report = _get_report_or_404(report_id, db)

    note = CaseNote(
        id=str(uuid.uuid4()),
        report_id=report.id,
        officer_id=officer.id,
        note_text=payload.note_text.strip(),
        is_internal=payload.is_internal,
    )
    db.add(note)
    db.add(AuditLog(
        id=str(uuid.uuid4()),
        report_id=report.id,
        action="NOTE_ADDED",
        actor=officer.username,
        actor_id=officer.id,
        details={"internal": payload.is_internal, "length": len(payload.note_text)},
    ))
    db.commit()
    db.refresh(note)

    return CaseNoteResponse(
        id=note.id,
        report_id=note.report_id,
        officer_id=note.officer_id,
        created_at=note.created_at,
        note_text=note.note_text,
        is_internal=note.is_internal,
        officer_name=officer.full_name,
    )


@router.get("/{report_id}/notes", response_model=List[CaseNoteResponse])
def get_notes(
    report_id: str,
    include_internal: bool = True,
    db: Session = Depends(get_db),
    officer: Optional[OfficerUser] = Depends(get_current_officer),
):
    """Get all notes for a case. Non-officers only see public notes."""
    report = _get_report_or_404(report_id, db)

    query = db.query(CaseNote).filter(CaseNote.report_id == report_id)
    if not officer or not include_internal:
        query = query.filter(CaseNote.is_internal == False)

    notes = query.order_by(CaseNote.created_at.asc()).all()

    result = []
    for n in notes:
        officer_name = None
        if n.officer:
            officer_name = n.officer.full_name
        result.append(CaseNoteResponse(
            id=n.id,
            report_id=n.report_id,
            officer_id=n.officer_id,
            created_at=n.created_at,
            note_text=n.note_text,
            is_internal=n.is_internal,
            officer_name=officer_name,
        ))
    return result


# ─── Case Search ──────────────────────────────────────────────────────────────

@router.post("/search", response_model=List[ReportListItem])
def search_cases(
    payload: CaseSearchRequest,
    db: Session = Depends(get_db),
    officer: OfficerUser = Depends(require_officer),
):
    """Advanced case search with multiple filters."""
    query = db.query(Report)

    if payload.query:
        term = f"%{payload.query}%"
        query = query.filter(or_(
            Report.case_number.ilike(term),
            Report.complainant_name.ilike(term),
            Report.complainant_phone.ilike(term),
            Report.incident_description.ilike(term),
            Report.crime_category.ilike(term),
        ))

    if payload.risk_level:
        query = query.filter(Report.risk_level == payload.risk_level.upper())

    if payload.status:
        query = query.filter(Report.status == payload.status.upper())

    if payload.crime_category:
        query = query.filter(Report.crime_category.ilike(f"%{payload.crime_category}%"))

    if payload.date_from:
        query = query.filter(Report.created_at >= payload.date_from)

    if payload.date_to:
        query = query.filter(Report.created_at <= payload.date_to)

    if payload.assigned_officer_id:
        query = query.filter(Report.assigned_officer_id == payload.assigned_officer_id)

    if payload.is_flagged_fake is not None:
        query = query.filter(Report.is_flagged_fake == payload.is_flagged_fake)

    reports = (
        query.order_by(Report.created_at.desc())
        .offset(payload.offset)
        .limit(payload.limit)
        .all()
    )

    return [
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
        for r in reports
    ]


# ─── CSV Export ───────────────────────────────────────────────────────────────

@router.get("/export/csv")
def export_cases_csv(
    risk_level: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    limit: int = Query(default=1000, le=5000),
    db: Session = Depends(get_db),
    officer: OfficerUser = Depends(require_officer),
):
    """
    Export cases to CSV for reporting/analysis.
    PII fields (phone, email) are included — handle with care (DPDP Act).
    """
    query = db.query(Report)

    if risk_level:
        query = query.filter(Report.risk_level == risk_level.upper())
    if status:
        query = query.filter(Report.status == status.upper())
    if date_from:
        try:
            query = query.filter(Report.created_at >= datetime.fromisoformat(date_from))
        except ValueError:
            pass
    if date_to:
        try:
            query = query.filter(Report.created_at <= datetime.fromisoformat(date_to))
        except ValueError:
            pass

    reports = query.order_by(Report.created_at.desc()).limit(limit).all()

    # Build CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Case Number", "Date", "Status", "Risk Level", "Risk Score",
        "Crime Category", "Crime Subcategory", "Authenticity Score",
        "Fake Recommendation", "Tamper Score", "Reporter Trust",
        "Assigned Officer", "FIR Generated", "Evidence Files",
        "Complainant Name", "Phone", "Email",
    ])

    for r in reports:
        writer.writerow([
            r.case_number,
            r.created_at.strftime("%Y-%m-%d %H:%M"),
            r.status,
            r.risk_level or "",
            f"{r.risk_score:.2f}" if r.risk_score else "",
            r.crime_category or "",
            r.crime_subcategory or "",
            f"{r.authenticity_score:.2f}" if r.authenticity_score else "",
            r.fake_recommendation or "",
            f"{r.forensics_tamper_score:.2f}" if r.forensics_tamper_score else "",
            f"{r.reporter_trust_score:.2f}" if r.reporter_trust_score else "",
            r.assigned_officer or "",
            "Yes" if r.fir_path else "No",
            len(r.evidence_files),
            r.complainant_name,
            r.complainant_phone or "",
            r.complainant_email or "",
        ])

    output.seek(0)
    filename = f"autojustice_cases_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.csv"
    db.add(AuditLog(
        id=str(uuid.uuid4()),
        action="CASES_EXPORTED_CSV",
        actor=officer.username,
        actor_id=officer.id,
        details={"rows": len(reports), "filters": {"risk_level": risk_level, "status": status}},
    ))
    db.commit()

    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ─── Flag / Unflag as Fake ────────────────────────────────────────────────────

@router.post("/{report_id}/flag-fake")
def flag_as_fake(
    report_id: str,
    reason: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    officer: OfficerUser = Depends(require_officer),
):
    """Officer action: manually mark a report as fake."""
    report = _get_report_or_404(report_id, db)

    report.is_flagged_fake = True
    report.fake_recommendation = "REJECT"
    report.status = "CLOSED"
    report.closed_at = datetime.utcnow()
    report.closure_reason = reason or "Manually flagged as fake by officer"

    db.add(CaseNote(
        id=str(uuid.uuid4()),
        report_id=report.id,
        officer_id=officer.id,
        note_text=f"Report manually flagged as FAKE. Reason: {reason or 'Not specified'}",
        is_internal=True,
    ))
    db.add(AuditLog(
        id=str(uuid.uuid4()),
        report_id=report.id,
        action="MANUALLY_FLAGGED_FAKE",
        actor=officer.username,
        actor_id=officer.id,
        details={"reason": reason},
    ))
    db.commit()
    return {"success": True, "message": "Report flagged as fake and closed."}


@router.post("/{report_id}/unflag-fake")
def unflag_fake(
    report_id: str,
    reason: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    officer: OfficerUser = Depends(require_officer),
):
    """Officer action: reverse a fake flag (genuine report incorrectly flagged)."""
    report = _get_report_or_404(report_id, db)

    report.is_flagged_fake = False
    report.fake_recommendation = "GENUINE"
    report.status = "TRIAGED"
    report.closed_at = None
    report.closure_reason = None

    db.add(AuditLog(
        id=str(uuid.uuid4()),
        report_id=report.id,
        action="FAKE_FLAG_REVERSED",
        actor=officer.username,
        actor_id=officer.id,
        details={"reason": reason},
    ))
    db.commit()
    return {"success": True, "message": "Fake flag removed. Case reopened."}


# ─── Jurisdiction / Inter-State Forwarding (Phase 2) ─────────────────────────

@router.get("/{report_id}/jurisdiction")
def check_jurisdiction(
    report_id: str,
    db: Session = Depends(get_db),
    officer: OfficerUser = Depends(require_officer),
):
    """Return the detected jurisdiction and forwarding recommendation for a case."""
    from services.jurisdiction_service import jurisdiction_service
    from config import settings
    report = _get_report_or_404(report_id, db)

    # Re-detect fresh (in case report predates jurisdiction feature)
    jur = jurisdiction_service.detect(
        incident_location=report.incident_location,
        incident_description=report.incident_description,
        complainant_address=report.complainant_address,
    )
    return {
        "case_number": report.case_number,
        "host_station": settings.station_name,
        "host_state": settings.station_state,
        "detected_state": jur.detected_state,
        "detected_district": jur.detected_district,
        "jurisdiction_name": jur.jurisdiction_name,
        "confidence": jur.confidence,
        "requires_forwarding": jur.requires_forwarding,
        "reason": jur.reason,
        "matched_keywords": jur.matched_keywords,
        "already_forwarded": bool(report.is_forwarded),
        "forwarded_to_station": report.forwarded_to_station,
        "forwarded_to_state": report.forwarded_to_state,
    }


@router.post("/{report_id}/forward")
def forward_case(
    report_id: str,
    target_station: Optional[str] = Query(default=None),
    target_state: Optional[str] = Query(default=None),
    reason: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    officer: OfficerUser = Depends(require_officer),
):
    """
    Forward a case to another state's cyber cell. If target_station/state are
    not provided, uses the auto-detected jurisdiction.
    """
    from services.jurisdiction_service import jurisdiction_service, STATE_CYBER_CELL
    from config import settings
    report = _get_report_or_404(report_id, db)

    if report.is_forwarded:
        raise HTTPException(409, f"Case already forwarded to {report.forwarded_to_station}.")

    # Determine target
    if not target_state:
        jur = jurisdiction_service.detect(
            incident_location=report.incident_location,
            incident_description=report.incident_description,
            complainant_address=report.complainant_address,
        )
        if not jur.requires_forwarding:
            raise HTTPException(
                400,
                f"Auto-detection found no jurisdiction outside {settings.station_state}. "
                "Specify target_state explicitly to override."
            )
        target_state = jur.detected_state
        target_station = target_station or jur.jurisdiction_name

    target_station = target_station or STATE_CYBER_CELL.get(target_state, f"{target_state} Cyber Cell")

    # Update report
    report.is_forwarded = True
    report.forwarded_to_station = target_station
    report.forwarded_to_state = target_state
    report.forwarded_at = datetime.utcnow()
    report.forwarded_by = officer.full_name or officer.username
    report.forwarding_reason = reason or "Inter-state jurisdiction transfer."
    report.status = "ARCHIVED"  # Local copy archived after forwarding

    db.add(CaseNote(
        id=str(uuid.uuid4()),
        report_id=report.id,
        officer_id=officer.id,
        note_text=(
            f"Case forwarded to {target_station} ({target_state}). "
            f"Reason: {report.forwarding_reason}"
        ),
        is_internal=True,
    ))
    db.add(AuditLog(
        id=str(uuid.uuid4()),
        report_id=report.id,
        action="CASE_FORWARDED",
        actor=officer.username,
        actor_id=officer.id,
        details={
            "target_station": target_station,
            "target_state": target_state,
            "reason": report.forwarding_reason,
            "host_state": settings.station_state,
        },
    ))
    db.commit()

    # Notify complainant if email available
    if report.complainant_email:
        try:
            followup_service.send_status_update(
                to_email=report.complainant_email,
                name=report.complainant_name,
                case_number=report.case_number,
                status=f"FORWARDED to {target_station}",
                risk_level=report.risk_level or "MEDIUM",
                crime_category=report.crime_category or "Cybercrime",
                assigned_officer=None,
                station_name=settings.station_name,
                hours_elapsed=0,
            )
        except Exception as e:
            logger.warning(f"Forwarding notification email failed: {e}")

    return {
        "success": True,
        "case_number": report.case_number,
        "forwarded_to_station": target_station,
        "forwarded_to_state": target_state,
        "forwarded_at": report.forwarded_at.isoformat(),
    }


# ─── Analytics ───────────────────────────────────────────────────────────────

@router.get("/analytics/officer-workload")
def officer_workload(
    db: Session = Depends(get_db),
    officer: OfficerUser = Depends(require_officer),
):
    """Cases assigned per officer for workload balancing."""
    from sqlalchemy import func as f
    workload = db.query(
        Report.assigned_officer,
        f.count(Report.id).label("count"),
    ).filter(
        Report.assigned_officer.isnot(None),
        Report.status.notin_(["CLOSED", "ARCHIVED"]),
    ).group_by(Report.assigned_officer).all()

    return [{"officer": r.assigned_officer, "open_cases": r.count} for r in workload]


@router.get("/analytics/crime-trends")
def crime_trends(
    days: int = Query(default=30, le=365),
    db: Session = Depends(get_db),
    officer: OfficerUser = Depends(require_officer),
):
    """Crime category trends over the past N days."""
    from sqlalchemy import func
    from datetime import timedelta
    cutoff = datetime.utcnow() - timedelta(days=days)

    rows = db.query(
        Report.crime_category,
        Report.risk_level,
        func.count(Report.id).label("count"),
    ).filter(
        Report.created_at >= cutoff,
        Report.crime_category.isnot(None),
    ).group_by(Report.crime_category, Report.risk_level).all()

    trends: dict = {}
    for row in rows:
        cat = row.crime_category
        if cat not in trends:
            trends[cat] = {"category": cat, "total": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        trends[cat]["total"] += row.count
        if row.risk_level in ("HIGH", "MEDIUM", "LOW"):
            trends[cat][row.risk_level] += row.count

    return sorted(trends.values(), key=lambda x: x["total"], reverse=True)


# ─── Helper ───────────────────────────────────────────────────────────────────

def _get_report_or_404(report_id: str, db: Session) -> Report:
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(404, f"Report {report_id} not found.")
    return report
