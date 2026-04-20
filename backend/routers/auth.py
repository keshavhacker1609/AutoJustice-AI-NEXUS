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

def _send_otp_sms(to_phone: str, otp: str) -> bool:
    """
    Send OTP via SMS. Supports Twilio (international) and Fast2SMS (India).
    Returns True if sent successfully, False if SMS not configured or failed.

    To enable: set SMS_ENABLED=true in .env, choose SMS_PROVIDER=twilio|fast2sms,
    and provide the corresponding API credentials.
    """
    if not settings.sms_enabled:
        logger.info(f"[DEV — SMS disabled] OTP for {to_phone}: {otp}")
        return False

    message_body = (
        f"AutoJustice AI NEXUS: Your OTP is {otp}. "
        f"Valid for 5 minutes. Do not share with anyone."
    )

    # ── Twilio ────────────────────────────────────────────────────────
    if settings.sms_provider == "twilio":
        if not (settings.twilio_account_sid and settings.twilio_auth_token and settings.twilio_from_number):
            logger.warning("Twilio SMS: credentials not configured (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER)")
            return False
        try:
            from twilio.rest import Client as TwilioClient
            client = TwilioClient(settings.twilio_account_sid, settings.twilio_auth_token)
            client.messages.create(
                body=message_body,
                from_=settings.twilio_from_number,
                to=to_phone,
            )
            logger.info(f"Twilio SMS sent to {to_phone[:6]}****")
            return True
        except ImportError:
            logger.warning("twilio package not installed. Run: pip install twilio")
            return False
        except Exception as e:
            logger.error(f"Twilio SMS failed for {to_phone[:6]}****: {e}")
            return False

    # ── Fast2SMS (India) ──────────────────────────────────────────────
    elif settings.sms_provider == "fast2sms":
        if not settings.fast2sms_api_key:
            logger.warning("Fast2SMS: API key not configured (FAST2SMS_API_KEY)")
            return False
        try:
            import urllib.request, urllib.parse, json as _json
            # Strip country code for Fast2SMS (expects 10-digit Indian mobile)
            digits = re.sub(r'\D', '', to_phone)
            if len(digits) == 12 and digits.startswith("91"):
                digits = digits[2:]
            if len(digits) != 10:
                logger.warning(f"Fast2SMS: invalid phone format {to_phone}")
                return False

            payload = _json.dumps({
                "route": "otp",
                "variables_values": otp,
                "flash": "0",
                "numbers": digits,
            }).encode("utf-8")

            req = urllib.request.Request(
                "https://www.fast2sms.com/dev/bulkV2",
                data=payload,
                headers={
                    "authorization": settings.fast2sms_api_key,
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = _json.loads(resp.read())
            if result.get("return"):
                logger.info(f"Fast2SMS OTP sent to {digits[:4]}****")
                return True
            else:
                logger.error(f"Fast2SMS error: {result.get('message', 'unknown')}")
                return False
        except Exception as e:
            logger.error(f"Fast2SMS send failed for {to_phone}: {e}")
            return False

    logger.warning(f"Unknown SMS provider: {settings.sms_provider}")
    return False


def _send_otp_email(to_email: str, otp: str) -> bool:
    """Send OTP email via SMTP. Returns True if sent, False if SMTP not configured."""
    if not settings.smtp_enabled or not settings.smtp_username:
        logger.info(f"[DEV — SMTP disabled] OTP for {to_email}: {otp}")
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"AutoJustice AI — Your Verification OTP: {otp}"
        msg["From"]    = settings.smtp_from_email
        msg["To"]      = to_email
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
        msg.attach(MIMEText(html, "html"))
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as s:
            s.starttls()
            s.login(settings.smtp_username, settings.smtp_password)
            s.sendmail(settings.smtp_from_email, to_email, msg.as_string())
        logger.info(f"OTP email sent to {to_email}")
        return True
    except Exception as exc:
        logger.error(f"SMTP send failed for {to_email}: {exc}")
        logger.info(f"[FALLBACK] OTP for {to_email}: {otp}")
        return False


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
        sent = _send_otp_sms(identifier, otp)
        masked = identifier[:3] + "****" + identifier[-2:] if len(identifier) >= 6 else "****"
        return {
            "sent": True,
            "channel": "sms",
            "sms_used": sent,
            "message": f"OTP sent to {masked} via SMS.",
            "dev_note": "SMS disabled — OTP logged to server console." if not sent else None,
        }
    else:
        sent = _send_otp_email(identifier, otp)
        masked = identifier[:2] + "***@" + identifier.split("@")[1]
        return {
            "sent": True,
            "channel": "email",
            "smtp_used": sent,
            "message": f"OTP sent to {masked}. Check your inbox (and spam folder).",
            "dev_note": "SMTP disabled — OTP logged to server console." if not sent else None,
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
