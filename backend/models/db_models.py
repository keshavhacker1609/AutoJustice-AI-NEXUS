"""
AutoJustice AI NEXUS - SQLAlchemy ORM Models
Chain-of-custody compliant schema with SHA-256 integrity fields.
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Float, Boolean, DateTime,
    ForeignKey, Integer, JSON, Index
)
from sqlalchemy.orm import relationship
from database import Base


def generate_uuid():
    return str(uuid.uuid4())


# ─── Core Report Models ───────────────────────────────────────────────────────

class Report(Base):
    """
    Core forensic case record. Every mutation is logged in AuditLog.
    Immutable fields (sha256_*) are set on creation and never updated.
    """
    __tablename__ = "reports"

    # ─── Identity ─────────────────────────────────────────────────────
    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_number = Column(String(20), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ─── Complainant PII (DPDP Act compliant - stored encrypted in prod) ──
    complainant_name = Column(String(255), nullable=False)
    complainant_phone = Column(String(20), nullable=True, index=True)
    complainant_email = Column(String(255), nullable=True, index=True)
    complainant_address = Column(Text, nullable=True)

    # ─── Incident Details ─────────────────────────────────────────────
    incident_description = Column(Text, nullable=False)
    incident_date = Column(String(50), nullable=True)
    incident_location = Column(String(500), nullable=True)

    # ─── AI Analysis Results ──────────────────────────────────────────
    extracted_text = Column(Text, nullable=True)
    risk_level = Column(String(10), nullable=True, index=True)
    risk_score = Column(Float, nullable=True)
    crime_category = Column(String(100), nullable=True, index=True)
    crime_subcategory = Column(String(100), nullable=True)

    # ─── Extracted Entities (for FIR) ─────────────────────────────────
    entities = Column(JSON, nullable=True)
    bns_sections = Column(JSON, nullable=True)
    ai_summary = Column(Text, nullable=True)

    # ─── Fake Report Detection ────────────────────────────────────────
    authenticity_score = Column(Float, nullable=True)
    is_flagged_fake = Column(Boolean, default=False, index=True)
    fake_flags = Column(JSON, nullable=True)
    fake_recommendation = Column(String(50), nullable=True)

    # ─── Image Forensics ──────────────────────────────────────────────
    forensics_tamper_score = Column(Float, nullable=True)     # 0=clean, 1=tampered
    forensics_flags = Column(JSON, nullable=True)             # List of forensic anomalies
    forensics_summary = Column(Text, nullable=True)

    # ─── DigiLocker Identity Verification ────────────────────────────
    digilocker_verified = Column(Boolean, default=False, nullable=False)
    digilocker_name     = Column(String(255), nullable=True)  # Aadhaar-verified name

    # ─── Reporter Trust ───────────────────────────────────────────────
    reporter_trust_score = Column(Float, nullable=True)       # 0=untrusted, 1=trusted
    reporter_profile_id = Column(String(36), ForeignKey("reporter_profiles.id"), nullable=True)

    # ─── FIR Status ───────────────────────────────────────────────────
    status = Column(String(30), default="PENDING", index=True)
    fir_path = Column(String(500), nullable=True)
    fir_generated_at = Column(DateTime, nullable=True)
    assigned_officer = Column(String(255), nullable=True, index=True)
    assigned_officer_id = Column(String(36), ForeignKey("officer_users.id"), nullable=True)
    closed_at = Column(DateTime, nullable=True)
    closure_reason = Column(Text, nullable=True)

    # ─── Jurisdiction (Phase 2 — inter-state forwarding) ──────────────
    detected_state = Column(String(100), nullable=True, index=True)
    detected_district = Column(String(100), nullable=True)
    detected_jurisdiction = Column(String(100), nullable=True)   # E.g. "Delhi Cyber Cell"
    jurisdiction_confidence = Column(Float, nullable=True)       # 0.0 - 1.0
    is_forwarded = Column(Boolean, default=False, index=True)
    forwarded_to_station = Column(String(255), nullable=True)
    forwarded_to_state = Column(String(100), nullable=True)
    forwarded_at = Column(DateTime, nullable=True)
    forwarded_by = Column(String(255), nullable=True)
    forwarding_reason = Column(Text, nullable=True)

    # ─── Chain of Custody (SHA-256 Hashes) ───────────────────────────
    content_hash = Column(String(64), nullable=True, index=True)
    fir_hash = Column(String(64), nullable=True)

    # ─── Submission Metadata ──────────────────────────────────────────
    submission_ip = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)

    # ─── Relationships ────────────────────────────────────────────────
    evidence_files = relationship("EvidenceFile", back_populates="report", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="report", cascade="all, delete-orphan")
    case_notes = relationship("CaseNote", back_populates="report", cascade="all, delete-orphan")
    reporter_profile = relationship("ReporterProfile", back_populates="reports")
    assigned_officer_user = relationship("OfficerUser", back_populates="assigned_reports")

    __table_args__ = (
        Index("ix_reports_created_risk", "created_at", "risk_level"),
    )


class EvidenceFile(Base):
    """
    Individual evidence file record. SHA-256 hashed on upload for tamper detection.
    Complies with Section 65B Indian Evidence Act.
    """
    __tablename__ = "evidence_files"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    report_id = Column(String(36), ForeignKey("reports.id"), nullable=False, index=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    original_filename = Column(String(500), nullable=False)
    stored_filename = Column(String(500), nullable=False)
    file_type = Column(String(20), nullable=False)
    file_size_bytes = Column(Integer, nullable=True)
    mime_type = Column(String(100), nullable=True)

    # ─── Section 65B Compliance Fields ───────────────────────────────
    sha256_hash = Column(String(64), nullable=False)
    ocr_text = Column(Text, nullable=True)
    ocr_confidence = Column(Float, nullable=True)

    # ─── Forensic Metadata ────────────────────────────────────────────
    exif_data = Column(JSON, nullable=True)
    is_tampered = Column(Boolean, default=False)
    tamper_score = Column(Float, nullable=True)         # 0=clean, 1=definitely tampered
    tamper_flags = Column(JSON, nullable=True)          # Specific anomalies found
    ela_analysis = Column(JSON, nullable=True)          # ELA heatmap statistics
    gps_lat = Column(Float, nullable=True)              # Extracted GPS latitude
    gps_lon = Column(Float, nullable=True)              # Extracted GPS longitude

    report = relationship("Report", back_populates="evidence_files")


class AuditLog(Base):
    """
    Immutable audit trail for every system action. Required for legal defensibility.
    Records must never be deleted or modified.
    """
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    report_id = Column(String(36), ForeignKey("reports.id"), nullable=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    action = Column(String(100), nullable=False, index=True)
    actor = Column(String(255), nullable=True)
    actor_id = Column(String(36), nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)

    report = relationship("Report", back_populates="audit_logs")


class CaseNote(Base):
    """
    Officer notes attached to a case. Immutable once written (only officer who wrote can delete).
    """
    __tablename__ = "case_notes"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    report_id = Column(String(36), ForeignKey("reports.id"), nullable=False, index=True)
    officer_id = Column(String(36), ForeignKey("officer_users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    note_text = Column(Text, nullable=False)
    is_internal = Column(Boolean, default=True)   # Internal = not visible to citizen

    report = relationship("Report", back_populates="case_notes")
    officer = relationship("OfficerUser", back_populates="case_notes")


# ─── User / Auth Models ───────────────────────────────────────────────────────

class OfficerUser(Base):
    """
    Police officer account for dashboard access.
    Passwords are stored as bcrypt hashes — never plaintext.
    """
    __tablename__ = "officer_users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    username = Column(String(50), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    badge_number = Column(String(50), nullable=True, unique=True)
    email = Column(String(255), nullable=True, unique=True)
    rank = Column(String(100), nullable=True)                # Inspector, SI, etc.
    department = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default="officer")             # admin / officer / read_only
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    assigned_reports = relationship("Report", back_populates="assigned_officer_user")
    case_notes = relationship("CaseNote", back_populates="officer")


# ─── Reporter Reputation Models ───────────────────────────────────────────────

class ReporterProfile(Base):
    """
    Aggregated profile for a repeat reporter (identified by phone or email).
    Enables trust scoring based on historical submission quality.
    """
    __tablename__ = "reporter_profiles"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    phone = Column(String(20), nullable=True, unique=True, index=True)
    email = Column(String(255), nullable=True, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)

    # ─── Submission History ───────────────────────────────────────────
    total_submissions = Column(Integer, default=0)
    genuine_count = Column(Integer, default=0)       # Verified genuine reports
    fake_flagged_count = Column(Integer, default=0)  # Reports flagged/rejected as fake
    high_risk_count = Column(Integer, default=0)     # HIGH risk reports submitted
    fir_generated_count = Column(Integer, default=0) # Reports that led to FIR

    # ─── Computed Trust Score ─────────────────────────────────────────
    trust_score = Column(Float, default=0.70)        # 0.0 (blocked) → 1.0 (fully trusted)
    is_blocked = Column(Boolean, default=False)      # Permanently blocked spammer
    block_reason = Column(Text, nullable=True)

    reports = relationship("Report", back_populates="reporter_profile")
