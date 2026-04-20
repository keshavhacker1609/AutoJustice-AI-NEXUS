"""
AutoJustice AI NEXUS - Centralized Configuration
All settings are loaded from environment variables with secure defaults.
Never hardcode secrets — use .env for local dev and vault/secrets-manager in production.
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    # ─── Core App ─────────────────────────────────────────────────────
    app_name: str = Field(default="AutoJustice AI NEXUS")
    app_version: str = Field(default="2.0.0")
    debug: bool = Field(default=False)
    secret_key: str = Field(default="change-me-in-production-use-openssl-rand-hex-32")

    # ─── JWT Authentication ────────────────────────────────────────────
    jwt_algorithm: str = Field(default="HS256")
    jwt_access_token_expire_minutes: int = Field(default=480)   # 8 hours for officers
    default_admin_username: str = Field(default="admin")
    default_admin_password: str = Field(default="AutoJustice@2024!")  # overridden in prod

    # ─── AI Services ──────────────────────────────────────────────────
    gemini_api_key: str = Field(default="")
    gemini_model: str = Field(default="gemini-1.5-pro")
    tesseract_path: str = Field(default="tesseract")

    # ─── Database ─────────────────────────────────────────────────────
    database_url: str = Field(default="sqlite:///./autojustice.db")

    # ─── File Storage ─────────────────────────────────────────────────
    upload_dir: str = Field(default="uploads")
    fir_output_dir: str = Field(default="firs")
    max_upload_size_mb: int = Field(default=25)

    # ─── Risk Engine Thresholds ───────────────────────────────────────
    high_risk_threshold: float = Field(default=0.70)
    medium_risk_threshold: float = Field(default=0.40)
    fake_report_threshold: float = Field(default=0.45)

    # ─── Image Forensics ──────────────────────────────────────────────
    ela_quality: int = Field(default=90)                 # ELA JPEG re-save quality
    ela_tamper_threshold: float = Field(default=0.55)   # Score above = likely tampered
    max_gps_distance_km: float = Field(default=500.0)    # Max plausible GPS drift

    # ─── Rate Limiting (anti-abuse) ───────────────────────────────────
    rate_limit_submissions_per_hour: int = Field(default=5)    # Per IP
    rate_limit_window_seconds: int = Field(default=3600)
    rate_limit_enabled: bool = Field(default=True)

    # ─── Reporter Trust Scoring ───────────────────────────────────────
    trust_score_new_reporter: float = Field(default=0.70)      # Default for new reporters
    trust_score_min_reports_for_history: int = Field(default=3)  # Min reports before scoring

    # ─── Notifications (SMTP) ─────────────────────────────────────────
    smtp_enabled: bool = Field(default=False)
    smtp_host: str = Field(default="smtp.gmail.com")
    smtp_port: int = Field(default=587)
    smtp_username: str = Field(default="")
    smtp_password: str = Field(default="")
    smtp_from_email: str = Field(default="noreply@autojustice.gov.in")

    # ─── SMS OTP (Phase 2 — Twilio primary / Fast2SMS India fallback) ───
    sms_enabled: bool = Field(default=False)
    sms_provider: str = Field(default="twilio")          # "twilio" | "fast2sms"
    twilio_account_sid: str = Field(default="")
    twilio_auth_token: str = Field(default="")
    twilio_from_number: str = Field(default="")           # +1XXXXXXXXXX
    fast2sms_api_key: str = Field(default="")             # Fast2SMS API key (India)

    # ─── DigiLocker OAuth 2.0 (Citizen Identity Verification) ────────
    digilocker_client_id: str = Field(default="")
    digilocker_client_secret: str = Field(default="")
    digilocker_redirect_uri: str = Field(default="http://localhost:8000/api/digilocker/callback")
    digilocker_use_sandbox: bool = Field(default=True)   # True = sandbox; False = production

    # ─── Follow-up Email (Phase 2 — automated updates to complainants) ─
    followup_emails_enabled: bool = Field(default=True)
    followup_email_delay_hours: int = Field(default=24)   # First follow-up 24h after submission

    # ─── Police Station Identity ──────────────────────────────────────
    station_name: str = Field(default="Cyber Crime Police Station")
    station_address: str = Field(default="Commissioner Office, Cyber Cell")
    station_code: str = Field(default="CC-001")
    station_state: str = Field(default="Maharashtra")
    station_district: str = Field(default="Mumbai City")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()

# ─── Resolve Absolute Paths ────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
UPLOAD_PATH = BASE_DIR / settings.upload_dir
FIR_PATH = BASE_DIR / settings.fir_output_dir

UPLOAD_PATH.mkdir(exist_ok=True)
FIR_PATH.mkdir(exist_ok=True)

# ─── Allowed Evidence File Types ───────────────────────────────────────
ALLOWED_EXTENSIONS = {
    # Images
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp",
    # Documents
    ".pdf", ".txt",
    # Videos (Phase 2 — deepfake forensics)
    ".mp4", ".mov", ".avi", ".webm", ".mkv", ".m4v",
}

VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".webm", ".mkv", ".m4v"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"}
