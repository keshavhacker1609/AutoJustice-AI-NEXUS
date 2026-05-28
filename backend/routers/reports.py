"""
AutoJustice AI NEXUS - Reports Router
Full AI pipeline: OCR → Image Forensics → Fake Detection → AI Triage → FIR Generation.
Integrates reporter trust scoring, tamper detection, and chain-of-custody hashing.
"""
import csv
import io
import os
import re
import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
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


# ─── Background: FULL Pipeline (AI triage + fake detect + OCR + forensics + FIR) ─
#
# The HTTP response returns in < 3 s (just file I/O + DB insert).
# EVERYTHING else runs here, after the response is already sent to the client.
# No Render 60-second proxy timeout risk.
#

def _process_everything_bg(
    report_id: str,
    is_freq_suspicious: bool,
    freq_reason: str,
    trust_score: float,
):
    """
    Full AI + forensics pipeline executed in a background task.

    Stages (all happen after HTTP response is sent):
      1.  OCR + EXIF on every evidence file
      2.  Image ELA forensics
      3.  Video forensics
      4.  Fake report detection (Gemini L2 + rule-based layers)
      5.  AI semantic triage (Gemini)
      6.  Risk capping / fake escalation logic
      7.  Jurisdiction detection
      8.  Reporter trust update
      9.  Complaint Report PDF generation
     10.  Follow-up acknowledgement email
    """
    import gc
    from database import SessionLocal
    from models.db_models import Report, EvidenceFile as _EvidenceFile
    from config import (
        FIR_PATH, UPLOAD_PATH, IMAGE_EXTENSIONS, VIDEO_EXTENSIONS,
        settings as _cfg,
    )
    import datetime as _dt

    db = SessionLocal()
    report = None
    try:
        report = db.query(Report).filter(Report.id == report_id).first()
        if not report:
            logger.error(f"[BG] Report {report_id} not found")
            return

        description = report.incident_description

        evidence_files = (
            db.query(_EvidenceFile)
            .filter(_EvidenceFile.report_id == report_id)
            .all()
        )

        # ── Stage 1–3: OCR + forensics ────────────────────────────────────
        all_ocr_text: list = []
        max_tamper_score = 0.0
        all_forensic_flags: list = []
        forensic_summaries: list = []

        for ev in evidence_files:
            stored_path = UPLOAD_PATH / ev.stored_filename
            if not stored_path.exists():
                continue

            suffix = Path(ev.stored_filename).suffix.lower()

            # OCR
            try:
                ocr_text, ocr_conf = _ocr_service.extract_text(stored_path)
                ev.ocr_text       = ocr_text
                ev.ocr_confidence = ocr_conf
                if ocr_text and not ocr_text.startswith("["):
                    all_ocr_text.append(ocr_text)
                if suffix in IMAGE_EXTENSIONS:
                    exif = _ocr_service.extract_exif_metadata(stored_path)
                    if exif:
                        ev.exif_data = exif
            except Exception as err:
                logger.error(f"[BG OCR] {ev.original_filename}: {err}")

            # Image forensics (ELA)
            if ev.file_type == "image":
                try:
                    fr = _forensics.analyze(stored_path)
                    ev.tamper_score = fr["tamper_score"]
                    ev.is_tampered  = fr["is_tampered"]
                    ev.tamper_flags = fr["flags"]
                    ev.ela_analysis = fr.get("ela_stats")
                    ev.gps_lat      = fr.get("gps_lat")
                    ev.gps_lon      = fr.get("gps_lon")
                    if fr["tamper_score"] > max_tamper_score:
                        max_tamper_score = fr["tamper_score"]
                    all_forensic_flags.extend(fr["flags"])
                    if fr["summary"]:
                        forensic_summaries.append(fr["summary"])
                except Exception as err:
                    logger.error(f"[BG FORENSICS] {ev.original_filename}: {err}")

            # Video forensics
            if ev.file_type == "video":
                try:
                    vr = video_forensics_service.analyze(stored_path)
                    ev.tamper_score = vr.get("tamper_score", 0.0)
                    ev.is_tampered  = vr.get("is_tampered", False)
                    ev.tamper_flags = vr.get("flags", [])
                    ev.ela_analysis = {
                        "layer_scores": vr.get("layer_scores"),
                        "metadata":     vr.get("metadata"),
                        "format":       vr.get("format"),
                    }
                    if ev.tamper_score and ev.tamper_score > max_tamper_score:
                        max_tamper_score = ev.tamper_score
                    all_forensic_flags.extend(vr.get("flags", []))
                    if vr.get("summary"):
                        forensic_summaries.append(f"[VIDEO {ev.original_filename}] {vr['summary']}")
                except Exception as err:
                    logger.error(f"[BG VIDEO] {ev.original_filename}: {err}")

        db.commit()   # persist per-file OCR + forensics data
        gc.collect()  # release PIL/numpy objects from OCR + forensics

        combined_ocr = " ".join(all_ocr_text)
        if combined_ocr:
            report.extracted_text = combined_ocr[:5000]
            # Refresh content hash now that we have OCR text
            report.content_hash = _hash_service.hash_report_content(
                description, combined_ocr, report.complainant_name
            )
        if evidence_files:
            report.forensics_tamper_score = round(max_tamper_score, 3)
            report.forensics_flags        = list(set(all_forensic_flags))
            report.forensics_summary      = " | ".join(forensic_summaries) or None

        # ── Stage 4: Fake report detection ───────────────────────────────
        try:
            fake_result = _fake_detector.analyze(
                description=description,
                evidence_text=combined_ocr,
                content_hash=report.content_hash or "",
                db=db,
            )
        except Exception as err:
            logger.error(f"[BG FAKE] {report_id}: {err}")
            from services.fake_detection_service import FakeDetectionResult
            fake_result = FakeDetectionResult(
                authenticity_score=0.6, recommendation="REVIEW", flags=[]
            )

        adjusted_auth = _trust_service.apply_trust_modifier(
            fake_result.authenticity_score, trust_score
        )
        if max_tamper_score >= _cfg.ela_tamper_threshold:
            adjusted_auth = min(adjusted_auth, 0.50)
            fake_result.flags.append(
                f"IMAGE FORENSICS: Potential tampering detected (score={max_tamper_score:.0%})"
            )
        if is_freq_suspicious and freq_reason:
            adjusted_auth = min(adjusted_auth, 0.40)
            fake_result.flags.append(f"FREQUENCY ABUSE: {freq_reason}")

        report.authenticity_score  = adjusted_auth
        report.is_flagged_fake     = adjusted_auth < _cfg.fake_report_threshold
        report.fake_flags          = list(set(fake_result.flags))
        report.fake_recommendation = fake_result.recommendation
        if adjusted_auth < 0.25:
            report.fake_recommendation = "REJECT"
        elif adjusted_auth < _cfg.fake_report_threshold and report.fake_recommendation == "GENUINE":
            report.fake_recommendation = "REVIEW"

        # ── Stage 5: AI semantic triage ───────────────────────────────────
        try:
            triage = _ai_triage.analyze(description, combined_ocr)
        except Exception as err:
            logger.error(f"[BG TRIAGE] {report_id}: {err}")
            triage = _ai_triage._fallback_analyze(description, combined_ocr)

        report.risk_level       = triage.risk_level
        report.risk_score       = triage.risk_score
        report.crime_category   = triage.crime_category
        report.crime_subcategory = triage.crime_subcategory
        report.ai_summary       = triage.ai_summary
        report.entities         = triage.entities
        report.bns_sections     = triage.bns_sections

        # ── Stage 6: Risk capping / fake escalation ───────────────────────
        if report.fake_recommendation in ("REVIEW", "REJECT") or report.is_flagged_fake:
            if triage.risk_level == "HIGH" and adjusted_auth < 0.65:
                report.risk_level = "MEDIUM"
                report.risk_score = min(report.risk_score, 0.58)
                report.fake_flags = list(set(
                    (report.fake_flags or []) +
                    ["RISK CAPPED: Authenticity too low — downgraded to MEDIUM"]
                ))
        if report.is_flagged_fake and report.fake_recommendation == "REJECT":
            report.risk_level    = "HIGH"
            report.risk_score    = max(report.risk_score, 0.80)
            report.crime_subcategory = "False Complaint Filing"
            report.bns_sections  = [
                "BNS Section 211 (Intentionally giving false information to public servant)",
                "BNS Section 218 (Public servant framing incorrect record/writing)",
                "IT Act Section 66D (Cheating by personation using computer resource)",
            ]
            report.ai_summary = (
                f"[AUTOMATED FLAG] Likely fabricated report (auth: {adjusted_auth:.0%}). "
                f"Recommend investigating complainant under BNS §211. "
                f"Original triage: {triage.ai_summary}"
            )

        # ── Stage 7: Jurisdiction detection ──────────────────────────────
        try:
            jur = jurisdiction_service.detect(
                incident_location=report.incident_location,
                incident_description=description,
                complainant_address=report.complainant_address,
            )
            report.detected_state        = jur.detected_state
            report.detected_district     = jur.detected_district
            report.detected_jurisdiction = jur.jurisdiction_name
            report.jurisdiction_confidence = jur.confidence
            if jur.requires_forwarding:
                report.fake_flags = list(set(
                    (report.fake_flags or []) + [f"JURISDICTION: {jur.reason}"]
                ))
        except Exception as err:
            logger.warning(f"[BG JURISDICTION] {report_id}: {err}")

        # ── Stage 8: Reporter trust update ────────────────────────────────
        try:
            reporter_profile = (
                db.query(__import__("models.db_models", fromlist=["ReporterProfile"]).ReporterProfile)
                .filter_by(id=report.reporter_profile_id)
                .first()
            ) if report.reporter_profile_id else None
            is_genuine = report.fake_recommendation == "GENUINE"
            fir_will_be_generated = (
                report.risk_level in ("HIGH", "MEDIUM")
                and report.fake_recommendation != "REJECT"
            )
            new_trust = _trust_service.update_after_analysis(
                db, reporter_profile,
                is_genuine=is_genuine,
                risk_level=report.risk_level,
                fir_generated=fir_will_be_generated,
            )
            report.reporter_trust_score = new_trust
        except Exception as err:
            logger.warning(f"[BG TRUST] {report_id}: {err}")

        report.status = "TRIAGED"
        db.commit()
        logger.info(
            f"[BG] Analysis complete for {report.case_number} — "
            f"risk={report.risk_level} auth={adjusted_auth:.2f}"
        )

        # ── Stage 9: Complaint Report PDF ─────────────────────────────────
        fir_will_generate = (
            report.risk_level in ("HIGH", "MEDIUM")
            and report.fake_recommendation != "REJECT"
        )
        if fir_will_generate:
            try:
                fir_filename = f"CR_{report.case_number}.pdf"
                fir_output   = FIR_PATH / fir_filename
                evidence_list_for_fir = [
                    {
                        "original_filename": ev.original_filename,
                        "file_type":         ev.file_type,
                        "sha256_hash":       ev.sha256_hash,
                        "ocr_confidence":    ev.ocr_confidence or 0,
                        "uploaded_at":       ev.uploaded_at.isoformat() if ev.uploaded_at else "",
                        "tamper_score":      ev.tamper_score or 0,
                        "is_tampered":       ev.is_tampered or False,
                    }
                    for ev in evidence_files
                ]
                _fir_gen.generate(
                    report_data={
                        "case_number":            report.case_number,
                        "complainant_name":        report.complainant_name,
                        "complainant_phone":       report.complainant_phone,
                        "complainant_email":       report.complainant_email,
                        "complainant_address":     report.complainant_address,
                        "incident_description":    report.incident_description,
                        "incident_date":           report.incident_date,
                        "incident_location":       report.incident_location,
                        "risk_level":              report.risk_level,
                        "risk_score":              report.risk_score,
                        "crime_category":          report.crime_category,
                        "crime_subcategory":       report.crime_subcategory,
                        "ai_summary":              report.ai_summary,
                        "entities":                report.entities,
                        "bns_sections":            report.bns_sections,
                        "authenticity_score":      report.authenticity_score,
                        "fake_recommendation":     report.fake_recommendation,
                        "fake_flags":              report.fake_flags,
                        "content_hash":            report.content_hash,
                        "forensics_tamper_score":  report.forensics_tamper_score,
                        "forensics_flags":         report.forensics_flags,
                        "reporter_trust_score":    report.reporter_trust_score,
                        "evidence_files":          evidence_list_for_fir,
                        "assigned_officer":        "Pending Assignment",
                    },
                    output_path=fir_output,
                )
                report.fir_path         = fir_filename
                report.fir_generated_at = _dt.datetime.utcnow()
                report.fir_hash         = _hash_service.hash_file(fir_output)
                report.status           = "COMPLAINT_REGISTERED"
                db.commit()
                logger.info(f"[BG FIR] Generated: {fir_filename}")
            except Exception as err:
                logger.error(f"[BG FIR] {report_id}: {err}")

        # ── Stage 10: Follow-up acknowledgement email ─────────────────────
        if report.complainant_email:
            try:
                followup_service.send_acknowledgement(
                    to_email=report.complainant_email,
                    name=report.complainant_name,
                    case_number=report.case_number,
                    risk_level=report.risk_level or "LOW",
                    crime_category=report.crime_category or "Cybercrime",
                    ai_summary=report.ai_summary or "Your complaint has been recorded.",
                    fir_generated=bool(report.fir_path),
                    station_name=_cfg.station_name,
                )
            except Exception as err:
                logger.warning(f"[BG EMAIL] {report_id}: {err}")

    except Exception as e:
        logger.error(f"[BG PIPELINE] Failed for {report_id}: {e}", exc_info=True)
        try:
            if report:
                report.status = "TRIAGED"
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


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
    phone_otp_token: Optional[str] = Form(None),
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

    # ── 0. Identity verification — require BOTH phone OTP + email OTP ────────
    phone_otp_verified = False
    email_otp_verified = False
    digilocker_verified = False
    digilocker_name_verified = None
    digilocker_profile = None

    try:
        from routers.auth import _otp_store
        import time as _time

        # Verify phone OTP token
        if phone_otp_token:
            entry = _otp_store.get(f"sess_{phone_otp_token}")
            if entry and entry.get("expires_at", 0) > _time.time():
                phone_otp_verified = True
                logger.info(f"Phone OTP verified: {str(entry.get('identifier',''))[:6]}** IP={client_ip}")

        # Verify email OTP token (sent as otp_session_token)
        if otp_session_token:
            entry = _otp_store.get(f"sess_{otp_session_token}")
            if entry and entry.get("expires_at", 0) > _time.time():
                email_otp_verified = True
                logger.info(f"Email OTP verified: {str(entry.get('identifier',''))[:4]}** IP={client_ip}")

    except Exception as e:
        logger.warning(f"OTP session verify error: {e}")

    # Optional: DigiLocker Aadhaar (bonus — boosts trust score)
    if digilocker_session_token:
        try:
            from services.digilocker_service import DigiLockerService
            from config import settings as _s
            _dl = DigiLockerService(
                client_id=getattr(_s, "digilocker_client_id", ""),
                client_secret=getattr(_s, "digilocker_client_secret", ""),
                redirect_uri=getattr(_s, "digilocker_redirect_uri", ""),
            )
            digilocker_profile = _dl.verify_session(digilocker_session_token, db)
            if digilocker_profile:
                digilocker_verified = True
                digilocker_name_verified = digilocker_profile.get("name")
                logger.info(f"DigiLocker verified: {digilocker_name_verified} IP={client_ip}")
        except Exception as e:
            logger.warning(f"DigiLocker session verify error: {e}")

    # ── Enforce: Email is required; phone OTP is optional ────────────────────
    if not email_otp_verified:
        raise HTTPException(
            status_code=401,
            detail="Email verification is required. Please complete Email OTP verification."
        )

    # Identity confirmed — email required, phone optional
    digilocker_verified_flag = email_otp_verified

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
    # Dual OTP + DigiLocker verification boosts base trust score
    if digilocker_verified or digilocker_verified_flag:
        trust_score = min(1.0, trust_score + 0.15)
        logger.info(f"Identity verification trust boost applied: score={trust_score:.2f}")

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
        digilocker_verified=(digilocker_verified or digilocker_verified_flag),
        digilocker_name=digilocker_name_verified,
        # Extended DigiLocker fields (populated only when DigiLocker was used)
        digilocker_dob=(digilocker_profile.get("dob") if digilocker_profile else None),
        digilocker_gender=(digilocker_profile.get("gender") if digilocker_profile else None),
        digilocker_aadhaar_suffix=(digilocker_profile.get("aadhaar_suffix") if digilocker_profile else None),
        digilocker_method=(digilocker_profile.get("verification_method") if digilocker_profile else None),
        citizen_verification_id=(str(digilocker_profile["id"]) if digilocker_profile and digilocker_profile.get("id") else None),
    )
    db.add(report)
    db.flush()

    # ── 4. Save uploaded evidence files (hash only — OCR/forensics in background) ─
    # We intentionally skip OCR and image forensics here to keep the main request
    # well under Render's 60 s proxy timeout.  The background task will pick up
    # OCR + ELA forensics + FIR generation once the response is sent.
    stored_evidence = []

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

        # SHA-256 hash for Section 65B compliance (fast — just hashing)
        file_hash = _hash_service.hash_bytes(file_bytes)

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
            # ocr_text / forensics fields populated by background task
        )
        db.add(ev)
        stored_evidence.append(ev)

    # ── 5. Content hash (description only — OCR text added by background task) ──
    report.content_hash = _hash_service.hash_report_content(
        description, "", complainant_name
    )

    # ── 6. Record submission in trust service (fast DB write) ─────────
    _trust_service.record_submission(db, reporter_profile, report.id)

    # ── 7. Audit log ──────────────────────────────────────────────────
    db.add(AuditLog(
        id=str(uuid.uuid4()),
        report_id=report.id,
        action="REPORT_SUBMITTED",
        actor="SYSTEM",
        ip_address=client_ip,
        details={
            "status":          "PROCESSING",
            "evidence_count":  len(stored_evidence),
            "pipeline":        "async-background",
        }
    ))

    db.commit()
    db.refresh(report)

    # ── 8. Mark DigiLocker session as used (non-fatal) ────────────────
    if digilocker_session_token and digilocker_profile:
        try:
            from services.digilocker_service import DigiLockerService
            from config import settings as _s
            DigiLockerService(
                client_id=getattr(_s, "digilocker_client_id", ""),
                client_secret=getattr(_s, "digilocker_client_secret", ""),
                redirect_uri=getattr(_s, "digilocker_redirect_uri", ""),
            ).mark_session_used(digilocker_session_token, db)
        except Exception as e:
            logger.warning(f"DigiLocker mark_used failed: {e}")

    # ── 9. Fire full AI+forensics pipeline in background ─────────────
    # The response is returned immediately with status=PROCESSING.
    # The background task advances it: PROCESSING → TRIAGED → COMPLAINT_REGISTERED
    background_tasks.add_task(
        _process_everything_bg,
        report_id=report.id,
        is_freq_suspicious=is_freq_suspicious,
        freq_reason=freq_reason or "",
        trust_score=trust_score,
    )

    logger.info(
        f"Submission accepted: case={report.case_number} "
        f"evidence={len(stored_evidence)} IP={client_ip}"
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


# ─── Officer Dashboard Management Endpoints ───────────────────────────────────

@router.get("/officers/list")
def list_officers(
    db: Session = Depends(get_db),
    officer: OfficerUser = Depends(require_officer),
):
    officers = db.query(OfficerUser).filter(OfficerUser.is_active == True).all()
    return [
        {"id": o.id, "name": o.full_name or o.username, "rank": o.rank or "", "username": o.username}
        for o in officers
    ]


@router.get("/export/csv")
def export_cases_csv(
    db: Session = Depends(get_db),
    officer: OfficerUser = Depends(require_officer),
):
    reports = db.query(Report).order_by(Report.created_at.desc()).limit(500).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Case Number", "Date", "Complainant", "Phone", "Email",
        "Crime Category", "Risk Level", "Status", "Assigned Officer",
        "Authenticity Score", "AI Summary", "Incident Location",
    ])
    for r in reports:
        writer.writerow([
            r.case_number,
            r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
            r.complainant_name,
            r.complainant_phone or "",
            r.complainant_email or "",
            r.crime_category or "",
            r.risk_level or "",
            r.status,
            r.assigned_officer or "Unassigned",
            f"{(r.authenticity_score or 0)*100:.0f}%" if r.authenticity_score else "",
            (r.ai_summary or "")[:200],
            r.incident_location or "",
        ])
    output.seek(0)
    filename = f"autojustice_cases_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.patch("/{report_id}/status")
def update_case_status(
    report_id: str,
    status: str = Form(...),
    note: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    officer: OfficerUser = Depends(require_officer),
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(404, "Report not found")
    old = report.status
    report.status = status.upper()
    if status.upper() == "CLOSED":
        report.closed_at = datetime.utcnow()
        if note:
            report.closure_reason = note
    if note:
        from models.db_models import CaseNote
        cn = CaseNote(
            report_id=report_id,
            officer_id=officer.id,
            note_text=f"[Status changed: {old} → {status.upper()}] {note}",
            is_internal=True,
        )
        db.add(cn)
    db.add(AuditLog(
        id=str(uuid.uuid4()),
        action="STATUS_UPDATE",
        actor=officer.username,
        actor_id=officer.id,
        report_id=report_id,
        details={"old": old, "new": status.upper(), "note": note},
    ))
    db.commit()
    return {"ok": True, "status": report.status}


@router.patch("/{report_id}/assign")
def assign_officer(
    report_id: str,
    officer_id: str = Form(...),
    db: Session = Depends(get_db),
    current_officer: OfficerUser = Depends(require_officer),
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(404, "Report not found")
    assignee = db.query(OfficerUser).filter(OfficerUser.id == officer_id).first()
    if not assignee:
        raise HTTPException(404, "Officer not found")
    report.assigned_officer = assignee.full_name or assignee.username
    report.assigned_officer_id = assignee.id
    if report.status == "PENDING":
        report.status = "INVESTIGATING"
    db.add(AuditLog(
        id=str(uuid.uuid4()),
        action="CASE_ASSIGNED",
        actor=current_officer.username,
        actor_id=current_officer.id,
        report_id=report_id,
        details={"assigned_to": assignee.username, "assigned_to_id": officer_id},
    ))
    db.commit()
    return {"ok": True, "assigned_to": assignee.full_name or assignee.username}


@router.patch("/{report_id}/priority")
def toggle_priority(
    report_id: str,
    db: Session = Depends(get_db),
    officer: OfficerUser = Depends(require_officer),
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(404, "Report not found")
    current = getattr(report, "is_priority", False) or False
    report.is_priority = not current
    db.commit()
    return {"ok": True, "is_priority": report.is_priority}


@router.post("/{report_id}/notes")
def add_case_note(
    report_id: str,
    note_text: str = Form(...),
    db: Session = Depends(get_db),
    officer: OfficerUser = Depends(require_officer),
):
    from models.db_models import CaseNote
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(404, "Report not found")
    note = CaseNote(
        report_id=report_id,
        officer_id=officer.id,
        note_text=note_text.strip(),
        is_internal=True,
    )
    db.add(note)
    db.add(AuditLog(
        id=str(uuid.uuid4()),
        action="NOTE_ADDED",
        actor=officer.username,
        actor_id=officer.id,
        report_id=report_id,
    ))
    db.commit()
    db.refresh(note)
    return {
        "id": note.id,
        "note_text": note.note_text,
        "officer": officer.full_name or officer.username,
        "created_at": note.created_at.isoformat(),
    }


@router.get("/{report_id}/notes")
def get_case_notes(
    report_id: str,
    db: Session = Depends(get_db),
    officer: OfficerUser = Depends(require_officer),
):
    from models.db_models import CaseNote
    notes = (
        db.query(CaseNote)
        .filter(CaseNote.report_id == report_id)
        .order_by(CaseNote.created_at.desc())
        .all()
    )
    return [
        {
            "id": n.id,
            "note_text": n.note_text,
            "officer": (n.officer.full_name or n.officer.username) if n.officer else "Unknown",
            "created_at": n.created_at.isoformat(),
        }
        for n in notes
    ]


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
