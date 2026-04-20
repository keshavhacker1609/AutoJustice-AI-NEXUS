"""
AutoJustice AI NEXUS - Reports Router
Full AI pipeline: OCR → Image Forensics → Fake Detection → AI Triage → FIR Generation.
Integrates reporter trust scoring, tamper detection, and chain-of-custody hashing.
"""
import os
import re
import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

from database import get_db
from models.db_models import Report, EvidenceFile, AuditLog, OfficerUser
from models.schemas import ReportResponse, ReportListItem
from services.hash_service import HashService
from services.ocr_service import OCRService
from services.ai_triage_service import AITriageService
from services.fake_detection_service import FakeDetectionService
from services.fir_generator import ComplaintReportGenerator
from services.image_forensics_service import ImageForensicsService
from services.video_forensics_service import video_forensics_service
from services.reporter_trust_service import ReporterTrustService
from services.followup_email_service import followup_service
from services.jurisdiction_service import jurisdiction_service
from config import (
    settings, UPLOAD_PATH, FIR_PATH,
    ALLOWED_EXTENSIONS, VIDEO_EXTENSIONS, IMAGE_EXTENSIONS,
)
from routers.auth import require_officer, get_current_officer

logger = logging.getLogger(__name__)
router = APIRouter()

# ─── Shared Service Instances ─────────────────────────────────────────────────
_hash_service = HashService()
_ocr_service = OCRService()
_ai_triage = AITriageService()
_fake_detector = FakeDetectionService()
_fir_gen = ComplaintReportGenerator()
_forensics = ImageForensicsService()
_trust_service = ReporterTrustService()


def _generate_case_number() -> str:
    """Generate a unique case number in CY-YYYY-XXXXXXXX format."""
    import random
    year = datetime.utcnow().year
    serial = random.randint(10000000, 99999999)
    return f"CY-{year}-{serial}"


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ─── Submit Report ─────────────────────────────────────────────────────────────

@router.post("/submit", response_model=ReportResponse)
async def submit_report(
    request: Request,
    background_tasks: BackgroundTasks,
    complainant_name: str = Form(...),
    incident_description: str = Form(...),
    complainant_phone: Optional[str] = Form(None),
    complainant_email: Optional[str] = Form(None),
    complainant_address: Optional[str] = Form(None),
    incident_date: Optional[str] = Form(None),
    incident_location: Optional[str] = Form(None),
    digilocker_session_token: Optional[str] = Form(None),
    otp_session_token: Optional[str] = Form(None),
    evidence_files: List[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
):
    """
    Primary endpoint: accepts citizen report + evidence files.
    Full pipeline: validation → file forensics → OCR → reporter trust →
                   fake detection → AI triage → FIR generation → audit log.
    """
    client_ip = _get_client_ip(request)
    user_agent = request.headers.get("User-Agent", "")[:500]

    # ── 0. Identity verification check (OTP email or DigiLocker) ─────────
    digilocker_verified = False
    digilocker_name_verified = None

    # Check OTP session token first
    if otp_session_token:
        try:
            from routers.auth import _otp_store
            import time as _time
            entry = _otp_store.get(f"sess_{otp_session_token}")
            if entry and entry.get("expires_at", 0) > _time.time():
                digilocker_verified = True
                digilocker_name_verified = entry.get("email")
                logger.info(f"OTP session verified: {digilocker_name_verified} IP={client_ip}")
        except Exception as e:
            logger.warning(f"OTP session verify error: {e}")

    # Fallback: DigiLocker session token
    elif digilocker_session_token:
        try:
            from services.digilocker_service import DigiLockerService
            from config import settings as _s
            _dl = DigiLockerService(
                client_id=getattr(_s, "digilocker_client_id", ""),
                client_secret=getattr(_s, "digilocker_client_secret", ""),
                redirect_uri=getattr(_s, "digilocker_redirect_uri", ""),
            )
            profile = _dl.verify_session(digilocker_session_token)
            if profile:
                digilocker_verified = True
                digilocker_name_verified = profile.get("name")
                logger.info(f"DigiLocker verified: {digilocker_name_verified} IP={client_ip}")
        except Exception as e:
            logger.warning(f"DigiLocker session verify error: {e}")

    # ── 1. Input validation ───────────────────────────────────────────
    description = incident_description.strip()
    if len(description) < 20:
        raise HTTPException(400, "Description too short (minimum 20 characters).")
    if len(description) > 5000:
        raise HTTPException(400, "Description too long (max 5000 characters).")

    # ── 2. Reporter profile & trust check ─────────────────────────────
    reporter_profile = _trust_service.get_or_create_profile(
        db, complainant_phone, complainant_email
    )
    trust_score = _trust_service.get_trust_score(reporter_profile)

    if reporter_profile and reporter_profile.is_blocked:
        logger.warning(f"Blocked reporter attempted submission: IP={client_ip}")
        raise HTTPException(403, "This contact has been flagged. Please visit your nearest police station.")

    # Check submission frequency for this reporter
    is_freq_suspicious, freq_reason = _trust_service.check_submission_frequency(db, reporter_profile)

    # ── 3. Create initial report record ───────────────────────────────
    # DigiLocker verification boosts base trust score
    if digilocker_verified:
        trust_score = min(1.0, trust_score + 0.15)
        logger.info(f"DigiLocker trust boost applied: score={trust_score:.2f}")

    report = Report(
        id=str(uuid.uuid4()),
        case_number=_generate_case_number(),
        complainant_name=complainant_name.strip(),
        complainant_phone=complainant_phone,
        complainant_email=complainant_email,
        complainant_address=complainant_address,
        incident_description=description,
        incident_date=incident_date,
        incident_location=incident_location,
        status="PROCESSING",
        submission_ip=client_ip,
        user_agent=user_agent,
        reporter_profile_id=reporter_profile.id if reporter_profile else None,
        reporter_trust_score=trust_score,
        digilocker_verified=digilocker_verified,
        digilocker_name=digilocker_name_verified,
    )
    db.add(report)
    db.flush()

    # ── 4. Process uploaded evidence files ────────────────────────────
    all_ocr_text = []
    stored_evidence = []
    image_paths_for_forensics = []
    ocr_info_notes: list = []          # soft warnings — never block submission

    for upload in evidence_files:
        if not upload.filename:
            continue

        suffix = Path(upload.filename).suffix.lower()
        if suffix not in ALLOWED_EXTENSIONS:
            logger.warning(f"Rejected file type: {suffix} from {client_ip}")
            continue

        file_bytes = await upload.read()
        if len(file_bytes) > settings.max_upload_size_mb * 1024 * 1024:
            raise HTTPException(413, f"File '{upload.filename}' exceeds {settings.max_upload_size_mb}MB limit.")

        # Store with UUID filename to prevent path traversal
        safe_name = f"{str(uuid.uuid4())}{suffix}"
        stored_path = UPLOAD_PATH / safe_name
        stored_path.write_bytes(file_bytes)

        # SHA-256 hash for Section 65B compliance
        file_hash = _hash_service.hash_bytes(file_bytes)

        # OCR extraction
        ocr_text, ocr_confidence = _ocr_service.extract_text(stored_path)

        # Soft warning: image uploaded but no text found (e.g. accident photo, injury image).
        # This is EXPECTED for visual evidence — does not block submission or affect scoring.
        if (
            ocr_confidence == 0.0
            and suffix in IMAGE_EXTENSIONS
            and not ocr_text.startswith("[OCR")      # skip Tesseract-unavailable messages
        ):
            ocr_info_notes.append(
                f"OCR-INFO '{upload.filename}': No text detected in this image. "
                "Visual evidence (accident photos, injury documentation, location images) "
                "is fully accepted — image forensics and chain-of-custody hash still applied."
            )
            logger.info(
                f"OCR found no text in '{upload.filename}' — treating as visual evidence, "
                "submission continues normally."
            )

        # EXIF metadata for images
        exif_data = {}
        if suffix in IMAGE_EXTENSIONS:
            exif_data = _ocr_service.extract_exif_metadata(stored_path)
            image_paths_for_forensics.append(stored_path)

        ev = EvidenceFile(
            id=str(uuid.uuid4()),
            report_id=report.id,
            original_filename=upload.filename[:255],
            stored_filename=safe_name,
            file_type=(
                "image" if suffix in IMAGE_EXTENSIONS else
                "video" if suffix in VIDEO_EXTENSIONS else
                "pdf" if suffix == ".pdf" else "text"
            ),
            file_size_bytes=len(file_bytes),
            mime_type=upload.content_type,
            sha256_hash=file_hash,
            ocr_text=ocr_text,
            ocr_confidence=ocr_confidence,
            exif_data=exif_data if exif_data else None,
        )
        db.add(ev)
        stored_evidence.append(ev)
        if ocr_text and not ocr_text.startswith("["):
            all_ocr_text.append(ocr_text)

    combined_ocr = " ".join(all_ocr_text)
    report.extracted_text = combined_ocr[:5000] if combined_ocr else None

    # ── 5. Image forensics on each image file ─────────────────────────
    max_tamper_score = 0.0
    all_forensic_flags = []
    forensic_summaries = []

    for i, (ev, img_path) in enumerate(
        [(e, UPLOAD_PATH / e.stored_filename) for e in stored_evidence
         if e.file_type == "image"]
    ):
        forensics_result = _forensics.analyze(img_path)

        ev.tamper_score = forensics_result["tamper_score"]
        ev.is_tampered = forensics_result["is_tampered"]
        ev.tamper_flags = forensics_result["flags"]
        ev.ela_analysis = forensics_result.get("ela_stats")
        ev.gps_lat = forensics_result.get("gps_lat")
        ev.gps_lon = forensics_result.get("gps_lon")

        if forensics_result["tamper_score"] > max_tamper_score:
            max_tamper_score = forensics_result["tamper_score"]
        all_forensic_flags.extend(forensics_result["flags"])
        if forensics_result["summary"]:
            forensic_summaries.append(forensics_result["summary"])

    # ── 5b. Video forensics (Phase 2 — deepfake detection) ────────────
    for ev in [e for e in stored_evidence if e.file_type == "video"]:
        vid_path = UPLOAD_PATH / ev.stored_filename
        try:
            v_result = video_forensics_service.analyze(vid_path)
        except Exception as e:
            logger.error(f"Video forensics failed for {ev.original_filename}: {e}")
            continue

        ev.tamper_score = v_result.get("tamper_score", 0.0)
        ev.is_tampered = v_result.get("is_tampered", False)
        ev.tamper_flags = v_result.get("flags", [])
        # Store layer scores/metadata in ela_analysis column (reused for video layer data)
        ev.ela_analysis = {
            "layer_scores": v_result.get("layer_scores"),
            "metadata": v_result.get("metadata"),
            "format": v_result.get("format"),
        }

        if ev.tamper_score and ev.tamper_score > max_tamper_score:
            max_tamper_score = ev.tamper_score
        all_forensic_flags.extend(v_result.get("flags", []))
        if v_result.get("summary"):
            forensic_summaries.append(f"[VIDEO {ev.original_filename}] {v_result['summary']}")

    if stored_evidence:
        report.forensics_tamper_score = round(max_tamper_score, 3)
        report.forensics_flags = list(set(all_forensic_flags)) + ocr_info_notes
        report.forensics_summary = " | ".join(forensic_summaries) if forensic_summaries else None

    # ── 6. Content hash (chain of custody + duplicate detection) ─────
    report.content_hash = _hash_service.hash_report_content(
        description, combined_ocr, complainant_name
    )

    # ── 7. Fake report detection ──────────────────────────────────────
    fake_result = _fake_detector.analyze(
        description=description,
        evidence_text=combined_ocr,
        content_hash=report.content_hash,
        db=db,
    )

    # Apply reporter trust modifier
    adjusted_auth_score = _trust_service.apply_trust_modifier(
        fake_result.authenticity_score, trust_score
    )

    # Factor in image tampering into authenticity
    if max_tamper_score >= settings.ela_tamper_threshold:
        adjusted_auth_score = min(adjusted_auth_score, 0.50)
        fake_result.flags.append(
            f"IMAGE FORENSICS: Potential tampering detected (score={max_tamper_score:.0%})"
        )

    # Factor in frequency abuse
    if is_freq_suspicious:
        adjusted_auth_score = min(adjusted_auth_score, 0.40)
        fake_result.flags.append(f"FREQUENCY ABUSE: {freq_reason}")

    report.authenticity_score = adjusted_auth_score
    report.is_flagged_fake = adjusted_auth_score < settings.fake_report_threshold
    report.fake_flags = list(set(fake_result.flags))
    report.fake_recommendation = fake_result.recommendation

    # Override recommendation if score is very low
    if adjusted_auth_score < 0.25:
        report.fake_recommendation = "REJECT"
    elif adjusted_auth_score < settings.fake_report_threshold:
        if report.fake_recommendation == "GENUINE":
            report.fake_recommendation = "REVIEW"

    # ── 8. AI semantic triage ─────────────────────────────────────────
    triage = _ai_triage.analyze(description, combined_ocr)
    report.risk_level = triage.risk_level
    report.risk_score = triage.risk_score
    report.crime_category = triage.crime_category
    report.crime_subcategory = triage.crime_subcategory
    report.ai_summary = triage.ai_summary
    report.entities = triage.entities
    report.bns_sections = triage.bns_sections

    # ── 8a. Cross-inform: fake score caps triage risk ─────────────────
    # A report flagged as suspicious/fake should NEVER propagate as HIGH risk
    # for the described crime — that would generate a FIR for a fictional incident.
    # Only confirmed GENUINE reports (auth >= 0.65) can reach HIGH risk unimpeded.
    if report.fake_recommendation in ("REVIEW", "REJECT") or report.is_flagged_fake:
        if triage.risk_level == "HIGH" and adjusted_auth_score < 0.65:
            report.risk_level = "MEDIUM"
            report.risk_score = min(report.risk_score, 0.58)
            report.fake_flags = list(set(
                (report.fake_flags or []) +
                ["RISK CAPPED: Authenticity score too low to confirm HIGH risk — downgraded to MEDIUM pending officer verification"]
            ))
            logger.info(
                f"Risk capped MEDIUM for case={report.case_number} "
                f"auth={adjusted_auth_score:.2f} fake_rec={report.fake_recommendation}"
            )

    # ── 8b. Escalate risk for confirmed fake reports ──────────────────
    # Filing a false police complaint is itself an offence under BNS §211.
    # Flagged-fake (REJECT) reports are elevated to HIGH risk so officers
    # know to investigate the complainant — NOT the described crime.
    if report.is_flagged_fake and report.fake_recommendation == "REJECT":
        report.risk_level = "HIGH"
        report.risk_score = max(report.risk_score, 0.80)
        report.crime_subcategory = "False Complaint Filing"
        report.bns_sections = [
            "BNS Section 211 (Intentionally giving false information to public servant)",
            "BNS Section 218 (Public servant framing incorrect record/writing)",
            "IT Act Section 66D (Cheating by personation using computer resource)",
        ]
        report.ai_summary = (
            f"[AUTOMATED FLAG] This submission has been assessed as a likely fabricated "
            f"report (authenticity score: {adjusted_auth_score:.0%}). The described incident "
            f"may not have occurred. Recommend investigating the complainant for potential "
            f"false complaint filing under BNS §211. Original triage: {triage.ai_summary}"
        )
        logger.warning(
            f"Fake report escalated to HIGH risk: case={report.case_number} "
            f"auth={adjusted_auth_score:.2f}"
        )

    # ── 8c. Jurisdiction detection (Phase 2) ──────────────────────────
    try:
        jur = jurisdiction_service.detect(
            incident_location=incident_location,
            incident_description=description,
            complainant_address=complainant_address,
        )
        report.detected_state = jur.detected_state
        report.detected_district = jur.detected_district
        report.detected_jurisdiction = jur.jurisdiction_name
        report.jurisdiction_confidence = jur.confidence
        if jur.requires_forwarding:
            report.fake_flags = list(set(
                (report.fake_flags or []) +
                [f"JURISDICTION: {jur.reason}"]
            ))
            logger.info(
                f"Case {report.case_number}: jurisdiction forwarding recommended "
                f"→ {jur.detected_state} (conf={jur.confidence:.2f})"
            )
    except Exception as e:
        logger.warning(f"Jurisdiction detection failed for {report.case_number}: {e}")

    # ── 9. Update reporter trust score ────────────────────────────────
    is_genuine = report.fake_recommendation == "GENUINE"
    fir_will_be_generated = (
        triage.risk_level in ("HIGH", "MEDIUM") and
        report.fake_recommendation != "REJECT"
    )
    _trust_service.record_submission(db, reporter_profile, report.id)
    new_trust_score = _trust_service.update_after_analysis(
        db, reporter_profile,
        is_genuine=is_genuine,
        risk_level=triage.risk_level,
        fir_generated=fir_will_be_generated,
    )
    report.reporter_trust_score = new_trust_score

    # ── 10. Auto-generate FIR ─────────────────────────────────────────
    if fir_will_be_generated:
        try:
            fir_filename = f"CR_{report.case_number}.pdf"
            fir_output = FIR_PATH / fir_filename

            evidence_list = [
                {
                    "original_filename": ev.original_filename,
                    "file_type": ev.file_type,
                    "sha256_hash": ev.sha256_hash,
                    "ocr_confidence": ev.ocr_confidence or 0,
                    "uploaded_at": ev.uploaded_at.isoformat() if ev.uploaded_at else "",
                    "tamper_score": ev.tamper_score or 0,
                    "is_tampered": ev.is_tampered or False,
                }
                for ev in stored_evidence
            ]

            _fir_gen.generate(
                report_data={
                    "case_number": report.case_number,
                    "complainant_name": report.complainant_name,
                    "complainant_phone": report.complainant_phone,
                    "complainant_email": report.complainant_email,
                    "complainant_address": report.complainant_address,
                    "incident_description": report.incident_description,
                    "incident_date": report.incident_date,
                    "incident_location": report.incident_location,
                    "risk_level": report.risk_level,
                    "risk_score": report.risk_score,
                    "crime_category": report.crime_category,
                    "crime_subcategory": report.crime_subcategory,
                    "ai_summary": report.ai_summary,
                    "entities": report.entities,
                    "bns_sections": report.bns_sections,
                    "authenticity_score": report.authenticity_score,
                    "fake_recommendation": report.fake_recommendation,
                    "fake_flags": report.fake_flags,
                    "content_hash": report.content_hash,
                    "forensics_tamper_score": report.forensics_tamper_score,
                    "forensics_flags": report.forensics_flags,
                    "reporter_trust_score": report.reporter_trust_score,
                    "evidence_files": evidence_list,
                    "assigned_officer": "Pending Assignment",
                },
                output_path=fir_output,
            )

            report.fir_path = fir_filename
            report.fir_generated_at = datetime.utcnow()
            report.fir_hash = _hash_service.hash_file(fir_output)
            report.status = "COMPLAINT_REGISTERED"

        except Exception as e:
            logger.error(f"FIR generation failed for {report.case_number}: {e}")
            report.status = "TRIAGED"
    else:
        report.status = "TRIAGED"

    # ── 11. Audit log ─────────────────────────────────────────────────
    db.add(AuditLog(
        id=str(uuid.uuid4()),
        report_id=report.id,
        action="REPORT_SUBMITTED",
        actor="SYSTEM",
        ip_address=client_ip,
        details={
            "risk_level": report.risk_level,
            "authenticity_score": report.authenticity_score,
            "fake_recommendation": report.fake_recommendation,
            "complaint_report_generated": bool(report.fir_path),
            "evidence_count": len(stored_evidence),
            "tamper_score": report.forensics_tamper_score,
            "reporter_trust_score": report.reporter_trust_score,
        }
    ))

    db.commit()
    db.refresh(report)

    # ── 12. Follow-up acknowledgement email (Phase 2) ─────────────────
    if complainant_email:
        background_tasks.add_task(
            followup_service.send_acknowledgement,
            to_email=complainant_email,
            name=complainant_name.strip(),
            case_number=report.case_number,
            risk_level=report.risk_level or "LOW",
            crime_category=report.crime_category or "Cybercrime",
            ai_summary=report.ai_summary or "Your complaint has been recorded and will be reviewed by an officer.",
            fir_generated=bool(report.fir_path),
            station_name=settings.station_name,
        )

    return ReportResponse.model_validate(report)


# ─── Evidence Pre-Validation ──────────────────────────────────────────────────

# Stock photo filename patterns — these are never genuine cybercrime evidence
_STOCK_RE = re.compile(
    r'^\d+_[A-Z]_\d+_'           # Shutterstock: 360_F_135167384_...
    r'|gettyimages[-_]\d+'        # Getty Images
    r'|adobe.?stock'              # Adobe Stock
    r'|istockphoto'               # iStock
    r'|depositphotos'             # Depositphotos
    r'|shutterstock',
    re.IGNORECASE,
)

_IRRELEVANT_NAME_RE = re.compile(
    r'\b(?:emoji|smiley|laugh|funny|meme|clipart|icon|sticker|cartoon|avatar'
    r'|wallpaper|background|banner|logo|template|placeholder|sample|test'
    r'|image\d{3,}|img\d{3,}|photo\d{3,}|pic\d{3,})\b',
    re.IGNORECASE,
)


@router.post("/validate-evidence")
async def validate_evidence(file: UploadFile = File(...)):
    """
    Quick pre-validation of a single evidence file before form submission.
    Returns a warning if the file is unlikely to be genuine cybercrime evidence.
    """
    import re as _re
    filename = file.filename or ""
    content = await file.read(512 * 1024)  # Read first 512 KB only
    file_size = len(content)

    warnings = []
    is_blocked = False

    # 1. Stock photo filename pattern
    if _STOCK_RE.search(filename):
        warnings.append("This appears to be a stock photo or commercial image, not a genuine screenshot or document.")
        is_blocked = True

    # 2. Irrelevant name keywords
    if _IRRELEVANT_NAME_RE.search(filename):
        warnings.append("Filename suggests this is not cybercrime evidence (emoji, meme, icon, template, etc.).")
        is_blocked = True

    # 3. Very small image — likely emoji, icon, or thumbnail
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext in ("jpg", "jpeg", "png", "gif", "bmp", "webp") and file_size < 30_000:
        warnings.append(f"Image is very small ({file_size // 1024} KB). Genuine screenshots and documents are typically larger than 30 KB.")
        if file_size < 10_000:
            is_blocked = True

    # 4. Quick OCR check on image files — no text = likely irrelevant
    if ext in ("jpg", "jpeg", "png", "bmp", "tiff") and not is_blocked:
        try:
            import tempfile, os as _os
            with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as tmp:
                tmp.write(content)
                tmp_path = tmp.name
            ocr_text, _ocr_conf = _ocr_service.extract_text(tmp_path)
            _os.unlink(tmp_path)
            ocr_text = (ocr_text or "").strip()
            if len(ocr_text) < 10:
                warnings.append(
                    "No readable text found in this image. Valid evidence (screenshots, documents, transaction records) "
                    "should contain visible text. A blank or decorative image is not accepted as cybercrime evidence."
                )
                is_blocked = True
        except Exception:
            pass  # OCR unavailable — skip this check

    if warnings:
        return JSONResponse(status_code=422, content={
            "valid": False,
            "blocked": is_blocked,
            "warnings": warnings,
            "filename": filename,
        })

    return {"valid": True, "blocked": False, "warnings": [], "filename": filename}


# ─── List Reports ─────────────────────────────────────────────────────────────

@router.get("/", response_model=List[ReportListItem])
def list_reports(
    limit: int = 50,
    offset: int = 0,
    risk_level: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    officer: OfficerUser = Depends(require_officer),
):
    """List reports with optional filtering. Used by police dashboard."""
    query = db.query(Report)
    if risk_level:
        query = query.filter(Report.risk_level == risk_level.upper())
    if status:
        query = query.filter(Report.status == status.upper())

    reports = query.order_by(Report.created_at.desc()).offset(offset).limit(limit).all()

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


# ─── Get Report ───────────────────────────────────────────────────────────────

@router.get("/track/{case_number}", response_model=ReportResponse)
def track_case_by_number(case_number: str, db: Session = Depends(get_db)):
    """Public: look up a case by case number (for citizen case tracking)."""
    report = db.query(Report).filter(Report.case_number == case_number.upper()).first()
    if not report:
        raise HTTPException(404, f"Case {case_number} not found.")
    return ReportResponse.model_validate(report)


@router.get("/{report_id}", response_model=ReportResponse)
def get_report(report_id: str, db: Session = Depends(get_db), officer: OfficerUser = Depends(require_officer)):
    """Get full report detail by ID."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(404, f"Report {report_id} not found.")
    return ReportResponse.model_validate(report)


# ─── FIR Download ─────────────────────────────────────────────────────────────

@router.get("/{report_id}/fir/download")
def download_fir(report_id: str, db: Session = Depends(get_db), officer: OfficerUser = Depends(require_officer)):
    """Download the generated FIR PDF for a report."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(404, "Report not found.")
    if not report.fir_path:
        raise HTTPException(404, "No FIR has been generated for this report yet.")
    fir_file = FIR_PATH / report.fir_path
    if not fir_file.exists():
        raise HTTPException(404, "FIR file not found on disk.")
    safe_filename = report.fir_path.replace("FIR_", "ComplaintReport_").replace("CR_", "ComplaintReport_")
    return FileResponse(str(fir_file), media_type="application/pdf", filename=safe_filename)


# ─── Force Generate FIR ───────────────────────────────────────────────────────

@router.post("/{report_id}/generate-fir")
def force_generate_fir(report_id: str, db: Session = Depends(get_db), officer: OfficerUser = Depends(require_officer)):
    """Manually trigger FIR generation for any report (officer action)."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(404, "Report not found.")

    try:
        evidence_list = [
            {
                "original_filename": ev.original_filename,
                "file_type": ev.file_type,
                "sha256_hash": ev.sha256_hash,
                "ocr_confidence": ev.ocr_confidence or 0,
                "uploaded_at": ev.uploaded_at.isoformat() if ev.uploaded_at else "",
                "tamper_score": ev.tamper_score or 0,
                "is_tampered": ev.is_tampered or False,
            }
            for ev in report.evidence_files
        ]

        fir_filename = f"CR_{report.case_number}.pdf"
        fir_output = FIR_PATH / fir_filename

        _fir_gen.generate(
            report_data={
                "case_number": report.case_number,
                "complainant_name": report.complainant_name,
                "complainant_phone": report.complainant_phone,
                "complainant_email": report.complainant_email,
                "complainant_address": report.complainant_address,
                "incident_description": report.incident_description,
                "incident_date": report.incident_date,
                "incident_location": report.incident_location,
                "risk_level": report.risk_level,
                "risk_score": report.risk_score,
                "crime_category": report.crime_category,
                "crime_subcategory": report.crime_subcategory,
                "ai_summary": report.ai_summary,
                "entities": report.entities,
                "bns_sections": report.bns_sections,
                "authenticity_score": report.authenticity_score,
                "fake_recommendation": report.fake_recommendation,
                "fake_flags": report.fake_flags,
                "content_hash": report.content_hash,
                "forensics_tamper_score": report.forensics_tamper_score,
                "forensics_flags": report.forensics_flags,
                "reporter_trust_score": report.reporter_trust_score,
                "evidence_files": evidence_list,
                "assigned_officer": report.assigned_officer or "Pending",
            },
            output_path=fir_output,
        )

        report.fir_path = fir_filename
        report.fir_generated_at = datetime.utcnow()
        report.fir_hash = _hash_service.hash_file(fir_output)
        report.status = "COMPLAINT_REGISTERED"

        db.add(AuditLog(
            id=str(uuid.uuid4()),
            report_id=report.id,
            action="FIR_MANUALLY_GENERATED",
            actor="OFFICER",
            details={"fir_path": fir_filename},
        ))
        db.commit()
        return {"success": True, "fir_path": fir_filename, "case_number": report.case_number}

    except Exception as e:
        logger.error(f"Manual FIR generation failed: {e}")
        raise HTTPException(500, f"FIR generation failed: {str(e)}")


# ─── Verify Evidence Integrity ────────────────────────────────────────────────

@router.get("/{report_id}/verify-integrity")
def verify_evidence_integrity(report_id: str, db: Session = Depends(get_db), officer: OfficerUser = Depends(require_officer)):
    """
    Verify SHA-256 hashes of all evidence files match stored values.
    Detects post-upload tampering with stored files.
    """
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(404, "Report not found.")

    results = []
    for ev in report.evidence_files:
        stored_path = UPLOAD_PATH / ev.stored_filename
        if not stored_path.exists():
            results.append({
                "file": ev.original_filename,
                "status": "FILE_MISSING",
                "stored_hash": ev.sha256_hash,
            })
            continue

        current_hash = _hash_service.hash_file(stored_path)
        intact = current_hash == ev.sha256_hash
        results.append({
            "file": ev.original_filename,
            "status": "INTACT" if intact else "TAMPERED",
            "stored_hash": ev.sha256_hash,
            "current_hash": current_hash,
        })

    all_intact = all(r["status"] == "INTACT" for r in results)
    return {
        "case_number": report.case_number,
        "all_intact": all_intact,
        "evidence_count": len(results),
        "results": results,
    }
