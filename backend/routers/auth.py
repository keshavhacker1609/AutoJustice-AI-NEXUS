"""
AutoJustice AI NEXUS - Authentication Router
JWT-based authentication for police officers.
Passwords hashed with bcrypt. Tokens expire after configured duration.
"""
import uuid
import logging
import random
import re
import secrets
import smtplib
import time
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from database import get_db
from models.db_models import OfficerUser, AuditLog
from models.schemas import OfficerLoginRequest, Token, OfficerCreate, OfficerResponse
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer(auto_error=False)

# ─── JWT Setup ───────────────────────────────────────────────────────────────
try:
    from jose import JWTError, jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    logger.error("python-jose not installed. Run: pip install python-jose[cryptography]")

# ─── Bcrypt Setup (direct — bypasses passlib/bcrypt version incompatibility) ─
try:
    import bcrypt as _bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False
    logger.error("bcrypt not installed. Run: pip install bcrypt")


# ─── Helper Functions ─────────────────────────────────────────────────────────

def _hash_password(password: str) -> str:
    """Hash password using bcrypt directly. Truncates to 72 bytes (bcrypt limit)."""
    if not BCRYPT_AVAILABLE:
        raise RuntimeError("bcrypt is required. Run: pip install bcrypt")
    pwd_bytes = password.encode("utf-8")[:72]
    return _bcrypt.hashpw(pwd_bytes, _bcrypt.gensalt(12)).decode("utf-8")


def _verify_password(plain: str, hashed: str) -> bool:
    """Verify password against bcrypt hash."""
    if not BCRYPT_AVAILABLE:
        return False
    try:
        return _bcrypt.checkpw(plain.encode("utf-8")[:72], hashed.encode("utf-8"))
    except Exception:
        return False


def _create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    if not JWT_AVAILABLE:
        raise RuntimeError("python-jose is required for authentication")
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.jwt_access_token_expire_minutes)
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)


def _decode_token(token: str) -> Optional[dict]:
    if not JWT_AVAILABLE:
        return None
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError:
        return None


def get_current_officer(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Optional[OfficerUser]:
    """
    FastAPI dependency: extract and validate JWT from Authorization header.
    Returns the OfficerUser or None if token is missing/invalid.
    Use require_officer() to enforce authentication.
    """
    if not credentials:
        return None
    payload = _decode_token(credentials.credentials)
    if not payload:
        return None
    officer_id = payload.get("sub")
    if not officer_id:
        return None
    officer = db.query(OfficerUser).filter(
        OfficerUser.id == officer_id,
        OfficerUser.is_active == True,
    ).first()
    return officer


def require_officer(
    officer: Optional[OfficerUser] = Depends(get_current_officer),
) -> OfficerUser:
    """Strict auth dependency — raises 401 if no valid token."""
    if not officer:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return officer


def require_admin(
    officer: OfficerUser = Depends(require_officer),
) -> OfficerUser:
    """Admin-only dependency — raises 403 for non-admin officers."""
    if officer.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return officer


def ensure_default_admin(db: Session) -> None:
    """
    Create default admin account if no officers exist.
    Called on application startup.
    """
    if not JWT_AVAILABLE or not BCRYPT_AVAILABLE:
        logger.warning("Auth dependencies not installed — skipping default admin creation")
        return

    count = db.query(OfficerUser).count()
    if count == 0:
        admin = OfficerUser(
            id=str(uuid.uuid4()),
            username=settings.default_admin_username,
            full_name="System Administrator",
            hashed_password=_hash_password(settings.default_admin_password),
            role="admin",
            department="Cyber Crime Police Station",
            is_active=True,
        )
        db.add(admin)
        db.commit()
        logger.info(
            f"Default admin created: username='{settings.default_admin_username}' "
            f"— CHANGE THE PASSWORD IMMEDIATELY IN PRODUCTION"
        )


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/login", response_model=Token)
def login(payload: OfficerLoginRequest, db: Session = Depends(get_db)):
    """Officer login — returns a JWT Bearer token."""
    if not JWT_AVAILABLE or not BCRYPT_AVAILABLE:
        raise HTTPException(503, "Authentication service unavailable — missing dependencies.")

    officer = db.query(OfficerUser).filter(
        OfficerUser.username == payload.username.strip(),
        OfficerUser.is_active == True,
    ).first()

    if not officer or not _verify_password(payload.password, officer.hashed_password):
        logger.warning(f"Failed login attempt for username: {payload.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    officer.last_login = datetime.utcnow()
    db.add(AuditLog(
        id=str(uuid.uuid4()),
        action="OFFICER_LOGIN",
        actor=officer.username,
        actor_id=officer.id,
        details={"role": officer.role},
    ))
    db.commit()

    token = _create_access_token({
        "sub": officer.id,
        "username": officer.username,
        "role": officer.role,
    })

    return Token(
        access_token=token,
        token_type="bearer",
        officer_id=officer.id,
        full_name=officer.full_name,
        role=officer.role,
        badge_number=officer.badge_number,
    )


@router.get("/me", response_model=OfficerResponse)
def get_me(officer: OfficerUser = Depends(require_officer)):
    """Get current officer's profile."""
    return officer


@router.post("/officers", response_model=OfficerResponse)
def create_officer(
    payload: OfficerCreate,
    db: Session = Depends(get_db),
    admin: OfficerUser = Depends(require_admin),
):
    """Admin only: create a new officer account."""
    if not JWT_AVAILABLE or not BCRYPT_AVAILABLE:
        raise HTTPException(503, "Auth dependencies not installed.")

    existing = db.query(OfficerUser).filter(
        OfficerUser.username == payload.username.strip()
    ).first()
    if existing:
        raise HTTPException(400, f"Username '{payload.username}' already exists.")

    officer = OfficerUser(
        id=str(uuid.uuid4()),
        username=payload.username.strip(),
        full_name=payload.full_name.strip(),
        hashed_password=_hash_password(payload.password),
        badge_number=payload.badge_number,
        email=payload.email,
        rank=payload.rank,
        department=payload.department,
        phone=payload.phone,
        role=payload.role,
    )
    db.add(officer)
    db.add(AuditLog(
        id=str(uuid.uuid4()),
        action="OFFICER_CREATED",
        actor=admin.username,
        actor_id=admin.id,
        details={"new_officer": payload.username, "role": payload.role},
    ))
    db.commit()
    db.refresh(officer)
    return officer


@router.get("/officers", response_model=list[OfficerResponse])
def list_officers(
    db: Session = Depends(get_db),
    officer: OfficerUser = Depends(require_officer),
):
    """List all active officers (accessible to all officers)."""
    return db.query(OfficerUser).filter(OfficerUser.is_active == True).all()


@router.put("/officers/{officer_id}/deactivate")
def deactivate_officer(
    officer_id: str,
    db: Session = Depends(get_db),
    admin: OfficerUser = Depends(require_admin),
):
    """Admin only: deactivate an officer account."""
    target = db.query(OfficerUser).filter(OfficerUser.id == officer_id).first()
    if not target:
        raise HTTPException(404, "Officer not found.")
    if target.id == admin.id:
        raise HTTPException(400, "Cannot deactivate your own account.")
    target.is_active = False
    db.add(AuditLog(
        id=str(uuid.uuid4()),
        action="OFFICER_DEACTIVATED",
        actor=admin.username,
        actor_id=admin.id,
        details={"target_officer": target.username},
    ))
    db.commit()
    return {"success": True, "message": f"Officer {target.username} deactivated."}


# ─── Email OTP Verification ───────────────────────────────────────────────────
# In-memory store: email -> {otp, expires_at, attempts}
# Session store:   "sess_<token>" -> {email, expires_at}
_otp_store: dict = {}

OTP_TTL = 300       # 5 minutes
OTP_RESEND_WAIT = 60
OTP_MAX_ATTEMPTS = 5
SESSION_TTL = 1800  # 30 minutes — enough to fill the complaint form


class _SendOTPBody:
    def __init__(self, email: str): self.email = email
class _VerifyOTPBody:
    def __init__(self, email: str, otp: str): self.email = email; self.otp = otp


from pydantic import BaseModel as _BM

class SendOTPRequest(_BM):
    email: Optional[str] = None
    phone: Optional[str] = None    # Phase 2: SMS OTP if email unavailable

class VerifyOTPRequest(_BM):
    email: Optional[str] = None
    phone: Optional[str] = None
    otp: str

class ValidateSessionRequest(_BM):
    session_token: str


# ─── SMS OTP — Phase 2 ────────────────────────────────────────────────────────

def _send_otp_sms(to_phone: str, otp: str) -> tuple[bool, str]:
    """
    Send OTP via SMS. Returns (success, error_detail).
    Supports Fast2SMS → 2Factor.in fallback (both India, no DLT).
    """
    if not settings.sms_enabled:
        logger.info(f"[DEV — SMS disabled] OTP for {to_phone}: {otp}")
        return False, "SMS_DISABLED"

    import httpx as _httpx

    digits = re.sub(r'\D', '', to_phone)
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    if not re.match(r'^[6-9]\d{9}$', digits):
        return False, f"Invalid phone number format: {to_phone}"

    # ── Fast2SMS (primary — India OTP route, no DLT) ──────────────────
    if settings.fast2sms_api_key:
        try:
            logger.info(f"Fast2SMS: sending to {digits[:4]}****{digits[-2:]} (key: {settings.fast2sms_api_key[:8]}...)")
            with _httpx.Client(timeout=12.0) as _client:
                resp = _client.post(
                    "https://www.fast2sms.com/dev/bulkV2",
                    data={"route": "otp", "variables_values": otp, "flash": "0", "numbers": digits},
                    headers={"authorization": settings.fast2sms_api_key, "Cache-Control": "no-cache"},
                )
            logger.info(f"Fast2SMS {resp.status_code}: {resp.text[:400]}")
            result = resp.json()
            if result.get("return") is True:
                logger.info(f"Fast2SMS OTP sent to {digits[:4]}****{digits[-2:]}")
                return True, ""
            err = str(result.get("message", result))
            logger.error(f"Fast2SMS rejected: {err}")
            # Fall through to 2Factor fallback
        except Exception as e:
            logger.error(f"Fast2SMS exception: {e}")

    # ── 2Factor.in fallback (India — TRANSACTIONAL OTP, no DLT) ──────
    twofactor_key = getattr(settings, "twofactor_api_key", "")
    if twofactor_key:
        try:
            logger.info(f"2Factor fallback: sending to {digits[:4]}****{digits[-2:]}")
            # TRANSACTIONAL route: sends text OTP without DLT registration
            url = f"https://2factor.in/API/V1/{twofactor_key}/SMS/{digits}/{otp}/AUTOGEN"
            with _httpx.Client(timeout=12.0) as _client:
                resp = _client.get(url)
            logger.info(f"2Factor {resp.status_code}: {resp.text[:300]}")
            result = resp.json()
            if result.get("Status") == "Success":
                logger.info(f"2Factor OTP sent to {digits[:4]}****{digits[-2:]}")
                return True, ""
            err = str(result.get("Details", result))
            logger.error(f"2Factor rejected: {err}")
            return False, f"SMS failed (Fast2SMS + 2Factor both rejected). Details: {err}"
        except Exception as e:
            logger.error(f"2Factor exception: {e}")
            return False, f"SMS service error: {e}"

    # ── Twilio (international fallback) ──────────────────────────────
    if settings.sms_provider == "twilio":
        if not (settings.twilio_account_sid and settings.twilio_auth_token and settings.twilio_from_number):
            return False, "Twilio credentials not configured"
        try:
            from twilio.rest import Client as TwilioClient
            msg_body = f"AutoJustice AI NEXUS: Your OTP is {otp}. Valid 5 min. Do not share."
            client = TwilioClient(settings.twilio_account_sid, settings.twilio_auth_token)
            client.messages.create(body=msg_body, from_=settings.twilio_from_number, to=f"+91{digits}")
            logger.info(f"Twilio SMS sent to {digits[:4]}****")
            return True, ""
        except Exception as e:
            logger.error(f"Twilio failed: {e}")
            return False, f"Twilio error: {e}"

    return False, "No SMS provider configured. Set FAST2SMS_API_KEY in Render environment."


def _send_otp_email(to_email: str, otp: str) -> tuple[bool, str]:
    """
    Send OTP email. Returns (success, error_detail).
    - If SMTP_HOST contains 'resend': uses Resend HTTP API
    - Otherwise: uses SMTP (Brevo smtp-relay.brevo.com:587 recommended)
    NOTE: Resend free plan restricts 'onboarding@resend.dev' to sending only
    to the account owner's email. For unrestricted sending, use Brevo SMTP.
    """
    if not settings.smtp_enabled:
        logger.info(f"[DEV — SMTP disabled] OTP for {to_email}: {otp}")
        return False, "SMTP_DISABLED"
    if not settings.smtp_username:
        logger.warning("Email: SMTP_USERNAME not configured")
        return False, "SMTP_USERNAME not set"

    html = f"""
<!DOCTYPE html><html><body style="margin:0;padding:0;background:#f0f4f8;font-family:'Segoe UI',Arial,sans-serif">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f4f8;padding:32px 0">
<tr><td align="center">
<table width="520" cellpadding="0" cellspacing="0" style="background:#fff;border:1px solid #d1d9e0;border-radius:6px;overflow:hidden">
  <tr><td style="background:#1a3f6f;padding:0">
    <table width="100%"><tr>
      <td width="6" style="background:#FF6B00"></td>
      <td style="padding:18px 24px">
        <p style="margin:0;color:#fff;font-size:17px;font-weight:700">AutoJustice AI NEXUS</p>
        <p style="margin:4px 0 0;color:rgba(255,255,255,0.65);font-size:11px;letter-spacing:.5px;text-transform:uppercase">National Cyber Crime Reporting Portal</p>
      </td>
    </tr></table>
  </td></tr>
  <tr><td style="padding:32px 28px">
    <p style="margin:0 0 16px;color:#1a3f6f;font-size:15px;font-weight:600">Email Verification OTP</p>
    <p style="margin:0 0 20px;color:#4a5568;font-size:14px;line-height:1.6">
      You have requested to file a cybercrime complaint on AutoJustice AI NEXUS.<br>
      Use the OTP below to verify your email address. <strong>Valid for 5 minutes.</strong>
    </p>
    <div style="background:#f7f9fc;border:2px dashed #c3cfe2;border-radius:6px;padding:24px;text-align:center;margin-bottom:24px">
      <p style="margin:0 0 6px;color:#718096;font-size:11px;text-transform:uppercase;letter-spacing:1px;font-weight:600">One-Time Password</p>
      <p style="margin:0;font-size:42px;font-weight:700;letter-spacing:14px;color:#1a3f6f;font-family:'Courier New',monospace">{otp}</p>
    </div>
    <p style="margin:0;color:#718096;font-size:12px;line-height:1.7">
      Do not share this OTP with anyone. AutoJustice will never ask you for this code by phone or email.<br>
      If you did not request this, please ignore this message.
    </p>
  </td></tr>
  <tr><td style="background:#f7f9fc;border-top:1px solid #e2e8f0;padding:14px 28px">
    <p style="margin:0;color:#a0aec0;font-size:11px">Ministry of Home Affairs, Government of India &nbsp;|&nbsp; cybercrime.gov.in</p>
  </td></tr>
</table>
</td></tr></table>
</body></html>"""

    # ── Resend HTTP API ────────────────────────────────────────────────
    # NOTE: onboarding@resend.dev can ONLY send to the account owner's verified
    # email on Resend's free plan (no custom domain). For any-recipient sending,
    # use Brevo SMTP instead (smtp-relay.brevo.com:587).
    if "resend" in (settings.smtp_host or "").lower():
        api_key = settings.smtp_password
        if not api_key:
            logger.error("Resend API key empty (SMTP_PASSWORD not set)")
            return False, "Resend API key not configured"
        try:
            import httpx as _httpx
            logger.info(f"Resend API: {to_email} (key: {api_key[:8]}...)")
            resp = _httpx.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "from": "AutoJustice AI NEXUS <onboarding@resend.dev>",
                    "to": [to_email],
                    "subject": f"AutoJustice AI — Your Verification OTP: {otp}",
                    "html": html,
                },
                timeout=15.0,
            )
            logger.info(f"Resend {resp.status_code}: {resp.text[:300]}")
            if resp.status_code in (200, 201):
                logger.info(f"Resend: OTP sent to {to_email}")
                return True, ""
            err = resp.text[:200]
            logger.error(f"Resend FAILED {resp.status_code}: {err}")
            return False, f"Resend API error {resp.status_code}: {err}"
        except Exception as exc:
            logger.error(f"Resend exception: {exc}")
            return False, f"Resend connection error: {exc}"

    # ── SMTP (Brevo / Gmail / any provider) ───────────────────────────
    # Brevo free: smtp-relay.brevo.com:587 — works for ANY recipient, 300/day
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"AutoJustice AI — Your Verification OTP: {otp}"
        msg["From"]    = settings.smtp_from_email
        msg["To"]      = to_email
        msg.attach(MIMEText(html, "html"))
        logger.info(f"SMTP: connecting to {settings.smtp_host}:{settings.smtp_port} for {to_email}")
        if int(settings.smtp_port) == 465:
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=15) as s:
                s.login(settings.smtp_username, settings.smtp_password)
                s.sendmail(settings.smtp_from_email, to_email, msg.as_string())
        else:
            with smtplib.SMTP(settings.smtp_host, int(settings.smtp_port), timeout=15) as s:
                s.ehlo()
                s.starttls()
                s.ehlo()
                s.login(settings.smtp_username, settings.smtp_password)
                s.sendmail(settings.smtp_from_email, to_email, msg.as_string())
        logger.info(f"SMTP: OTP sent to {to_email}")
        return True, ""
    except Exception as exc:
        logger.error(f"SMTP failed for {to_email}: {exc}")
        return False, f"SMTP error: {exc}"


@router.post("/send-otp")
def send_otp(body: SendOTPRequest):
    """
    Send a 6-digit OTP to the citizen's email OR phone number.
    Phase 2: if phone is provided and SMS is enabled, sends via SMS as fallback.
    """
    # ── Determine delivery channel ────────────────────────────────────
    use_sms = False
    identifier = None

    if body.email and body.email.strip():
        email = body.email.lower().strip()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            raise HTTPException(400, "Please enter a valid email address.")
        identifier = email
        channel = "email"
    elif body.phone and body.phone.strip():
        # SMS fallback — only if email not provided
        phone = re.sub(r'\D', '', body.phone.strip())
        if not re.match(r'^[6-9]\d{9}$', phone) and not re.match(r'^\+\d{8,15}$', body.phone.strip()):
            raise HTTPException(400, "Please enter a valid 10-digit Indian mobile number.")
        identifier = phone
        channel = "sms"
        use_sms = True
    else:
        raise HTTPException(400, "Please provide either an email address or phone number.")

    now = time.time()
    existing = _otp_store.get(identifier)
    if existing and existing["expires_at"] - now > (OTP_TTL - OTP_RESEND_WAIT):
        wait = int(existing["expires_at"] - now - (OTP_TTL - OTP_RESEND_WAIT))
        raise HTTPException(429, f"OTP already sent. Please wait {wait} seconds before requesting again.")

    otp = str(random.randint(100000, 999999))
    _otp_store[identifier] = {
        "otp": otp,
        "expires_at": now + OTP_TTL,
        "attempts": 0,
        "channel": channel,
        "identifier": identifier,
    }

    if use_sms:
        sent, err_detail = _send_otp_sms(identifier, otp)
        masked = identifier[:3] + "****" + identifier[-2:] if len(identifier) >= 6 else "****"
        if not sent:
            _otp_store.pop(identifier, None)
            if err_detail == "SMS_DISABLED":
                raise HTTPException(503, "SMS service is disabled. Please use Email OTP instead.")
            raise HTTPException(503, f"SMS delivery failed: {err_detail}. Please use Email OTP instead.")
        return {
            "sent": True,
            "channel": "sms",
            "message": f"OTP sent to {masked} via SMS.",
        }
    else:
        sent, err_detail = _send_otp_email(identifier, otp)
        masked = identifier[:2] + "***@" + identifier.split("@")[1]
        if not sent:
            _otp_store.pop(identifier, None)
            if not settings.smtp_enabled:
                raise HTTPException(503, "Email service is disabled on this server.")
            raise HTTPException(503, f"Email delivery failed: {err_detail}")
        return {
            "sent": True,
            "channel": "email",
            "message": f"OTP sent to {masked}. Check your inbox and spam folder.",
        }


@router.post("/verify-otp")
def verify_otp(body: VerifyOTPRequest):
    """
    Verify the OTP and return a session token for form submission.
    Accepts email or phone as identifier (whichever was used to request OTP).
    """
    # Resolve identifier — match whichever channel was used
    identifier = None
    if body.email and body.email.strip():
        identifier = body.email.lower().strip()
    elif body.phone and body.phone.strip():
        identifier = re.sub(r'\D', '', body.phone.strip())
        if len(identifier) == 12 and identifier.startswith("91"):
            identifier = identifier[2:]
    if not identifier:
        raise HTTPException(400, "Please provide the email or phone used to request the OTP.")

    otp = body.otp.strip()

    record = _otp_store.get(identifier)
    if not record:
        raise HTTPException(400, "No OTP found for this contact. Please request a new OTP.")
    if time.time() > record["expires_at"]:
        _otp_store.pop(identifier, None)
        raise HTTPException(400, "OTP has expired. Please request a new one.")

    record["attempts"] += 1
    if record["attempts"] > OTP_MAX_ATTEMPTS:
        _otp_store.pop(identifier, None)
        raise HTTPException(400, "Too many incorrect attempts. Please request a new OTP.")
    if record["otp"] != otp:
        left = OTP_MAX_ATTEMPTS - record["attempts"]
        raise HTTPException(400, f"Incorrect OTP. {left} attempt{'s' if left != 1 else ''} remaining.")

    _otp_store.pop(identifier, None)
    token = secrets.token_hex(32)
    channel = record.get("channel", "email")
    _otp_store[f"sess_{token}"] = {
        "email": identifier if channel == "email" else (body.email or ""),
        "phone": identifier if channel == "sms" else "",
        "channel": channel,
        "expires_at": time.time() + SESSION_TTL,
    }
    logger.info(f"OTP verified via {channel}: {identifier[:4]}****")
    return {
        "verified": True,
        "email": identifier if channel == "email" else (body.email or ""),
        "phone": identifier if channel == "sms" else "",
        "channel": channel,
        "session_token": token,
    }


@router.post("/validate-otp-session")
def validate_otp_session(body: ValidateSessionRequest):
    """Validate an OTP session token (called by report submission to confirm identity was verified)."""
    key = f"sess_{body.session_token}"
    rec = _otp_store.get(key)
    if not rec or time.time() > rec["expires_at"]:
        _otp_store.pop(key, None)
        raise HTTPException(401, "Session expired or invalid. Please verify again.")
    return {"valid": True, "email": rec.get("email", ""), "phone": rec.get("phone", "")}
