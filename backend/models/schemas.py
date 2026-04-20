"""
AutoJustice AI NEXUS - Pydantic Request/Response Schemas
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


# ─── Authentication Schemas ───────────────────────────────────────────────────

class OfficerLoginRequest(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    officer_id: str
    full_name: str
    role: str
    badge_number: Optional[str] = None


class OfficerCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    full_name: str = Field(..., min_length=2, max_length=255)
    password: str = Field(..., min_length=8)
    badge_number: Optional[str] = None
    email: Optional[str] = None
    rank: Optional[str] = None
    department: Optional[str] = None
    phone: Optional[str] = None
    role: str = Field(default="officer")


class OfficerResponse(BaseModel):
    id: str
    username: str
    full_name: str
    badge_number: Optional[str]
    email: Optional[str]
    rank: Optional[str]
    department: Optional[str]
    role: str
    is_active: bool
    last_login: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Report Submission ────────────────────────────────────────────────────────

class ReportCreate(BaseModel):
    complainant_name: str = Field(..., min_length=2, max_length=255)
    complainant_phone: Optional[str] = Field(None, max_length=20)
    complainant_email: Optional[str] = Field(None)
    complainant_address: Optional[str] = None
    incident_description: str = Field(..., min_length=20)
    incident_date: Optional[str] = None
    incident_location: Optional[str] = None


class EvidenceFileResponse(BaseModel):
    id: str
    original_filename: str
    file_type: str
    file_size_bytes: Optional[int]
    sha256_hash: str
    ocr_text: Optional[str]
    ocr_confidence: Optional[float]
    uploaded_at: datetime
    is_tampered: bool
    tamper_score: Optional[float]
    tamper_flags: Optional[List[str]]
    gps_lat: Optional[float]
    gps_lon: Optional[float]
    ela_analysis: Optional[Dict[str, Any]] = None
    exif_data: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class ForensicsResult(BaseModel):
    tamper_score: float
    is_tampered: bool
    flags: List[str]
    summary: str
    ela_stats: Optional[Dict[str, Any]] = None


# ─── Report Response (Full Detail) ───────────────────────────────────────────

class ReportResponse(BaseModel):
    id: str
    case_number: str
    created_at: datetime
    status: str

    complainant_name: str
    incident_description: str
    incident_date: Optional[str]
    incident_location: Optional[str]

    extracted_text: Optional[str]
    risk_level: Optional[str]
    risk_score: Optional[float]
    crime_category: Optional[str]
    crime_subcategory: Optional[str]
    ai_summary: Optional[str]
    entities: Optional[Dict[str, Any]]
    bns_sections: Optional[List[str]]

    authenticity_score: Optional[float]
    is_flagged_fake: bool
    fake_flags: Optional[List[str]]
    fake_recommendation: Optional[str]

    forensics_tamper_score: Optional[float]
    forensics_flags: Optional[List[str]]
    forensics_summary: Optional[str]

    reporter_trust_score: Optional[float]

    digilocker_verified: bool = False
    digilocker_name: Optional[str] = None

    content_hash: Optional[str]
    fir_path: Optional[str]
    fir_hash: Optional[str]
    fir_generated_at: Optional[datetime]
    assigned_officer: Optional[str]
    submission_ip: Optional[str]

    evidence_files: List[EvidenceFileResponse] = []

    class Config:
        from_attributes = True


# ─── Report List (Compact) ────────────────────────────────────────────────────

class ReportListItem(BaseModel):
    id: str
    case_number: str
    created_at: datetime
    status: str
    complainant_name: str
    risk_level: Optional[str]
    risk_score: Optional[float]
    crime_category: Optional[str]
    is_flagged_fake: bool
    fake_recommendation: Optional[str]
    authenticity_score: Optional[float]
    forensics_tamper_score: Optional[float]
    reporter_trust_score: Optional[float]
    assigned_officer: Optional[str]
    evidence_count: int = 0
    digilocker_verified: bool = False

    class Config:
        from_attributes = True


# ─── Case Management Schemas ──────────────────────────────────────────────────

class CaseAssignRequest(BaseModel):
    officer_id: str
    notes: Optional[str] = None


class CaseStatusUpdateRequest(BaseModel):
    status: str = Field(..., pattern="^(PENDING|PROCESSING|TRIAGED|FIR_GENERATED|UNDER_INVESTIGATION|CLOSED|ARCHIVED)$")
    reason: Optional[str] = None


class CaseNoteCreate(BaseModel):
    note_text: str = Field(..., min_length=5, max_length=5000)
    is_internal: bool = True


class CaseNoteResponse(BaseModel):
    id: str
    report_id: str
    officer_id: str
    created_at: datetime
    note_text: str
    is_internal: bool
    officer_name: Optional[str] = None

    class Config:
        from_attributes = True


class CaseSearchRequest(BaseModel):
    query: Optional[str] = None
    risk_level: Optional[str] = None
    status: Optional[str] = None
    crime_category: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    assigned_officer_id: Optional[str] = None
    is_flagged_fake: Optional[bool] = None
    limit: int = Field(default=50, le=200)
    offset: int = Field(default=0, ge=0)


# ─── Dashboard Statistics ─────────────────────────────────────────────────────

class RiskDistribution(BaseModel):
    high: int = 0
    medium: int = 0
    low: int = 0
    pending: int = 0


class DashboardStats(BaseModel):
    total_reports: int
    pending_triage: int
    firs_generated: int
    fake_flagged: int
    risk_distribution: RiskDistribution
    top_crime_categories: List[Dict[str, Any]]
    recent_reports: List[ReportListItem]
    daily_submissions: List[Dict[str, Any]]
    avg_authenticity_score: float
    high_risk_today: int
    under_investigation: int
    avg_tamper_score: float


# ─── AI Analysis Result (Internal) ───────────────────────────────────────────

class TriageResult(BaseModel):
    risk_level: str
    risk_score: float
    crime_category: str
    crime_subcategory: str
    ai_summary: str
    entities: Dict[str, Any]
    bns_sections: List[str]


class FakeDetectionResult(BaseModel):
    authenticity_score: float
    is_suspicious: bool
    flags: List[str]
    recommendation: str  # GENUINE / REVIEW / REJECT
    details: Dict[str, Any]


# ─── Reporter Trust ───────────────────────────────────────────────────────────

class ReporterProfileResponse(BaseModel):
    id: str
    phone: Optional[str]
    email: Optional[str]
    total_submissions: int
    genuine_count: int
    fake_flagged_count: int
    high_risk_count: int
    trust_score: float
    is_blocked: bool
    last_seen: datetime

    class Config:
        from_attributes = True
