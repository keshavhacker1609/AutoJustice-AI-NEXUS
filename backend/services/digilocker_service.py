"""
AutoJustice AI NEXUS — DigiLocker OAuth 2.0 Identity Verification Service
Integrates with India's official DigiLocker API (MeitY) for citizen authentication.

Real OAuth 2.0 flow with PKCE (Proof Key for Code Exchange).
Sessions persisted to PostgreSQL/SQLite — survive server restarts.
Fetches Aadhaar-verified name, DOB, gender from DigiLocker user profile.

To use real DigiLocker:
  Register at: https://partners.digitallocker.gov.in/
  Add DIGILOCKER_CLIENT_ID and DIGILOCKER_CLIENT_SECRET to .env

Demo mode (no credentials): returns mock verified profile.
"""
import hashlib
import logging
import secrets
import base64
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlencode

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# ─── DigiLocker API Endpoints ─────────────────────────────────────────────────
DIGILOCKER_AUTH_URL   = "https://api.digitallocker.gov.in/public/oauth2/1/authorize"
DIGILOCKER_TOKEN_URL  = "https://api.digitallocker.gov.in/public/oauth2/1/token"
DIGILOCKER_USER_URL   = "https://api.digitallocker.gov.in/public/oauth2/1/user"

DIGILOCKER_SANDBOX_AUTH  = "https://digilocker.meripehchaan.gov.in/public/oauth2/1/authorize"
DIGILOCKER_SANDBOX_TOKEN = "https://digilocker.meripehchaan.gov.in/public/oauth2/1/token"
DIGILOCKER_SANDBOX_USER  = "https://digilocker.meripehchaan.gov.in/public/oauth2/1/user"

STATE_TTL_SECONDS   = 600    # 10 min to complete OAuth flow
SESSION_TTL_HOURS   = 2      # 2 hour session after verification

# In-memory state store ONLY for OAuth PKCE state (short-lived, doesn't need DB)
_STATE_STORE: dict = {}


class DigiLockerService:
    """
    Full DigiLocker OAuth 2.0 + PKCE identity verification service.
    All verified sessions are persisted to the database.

    Flow:
      1. get_auth_url()          → redirect user to DigiLocker login
      2. handle_callback(db)     → exchange code → get access token → fetch profile → save to DB
      3. verify_session(db)      → validate session token from DB
    """

    def __init__(self, client_id: str, client_secret: str,
                 redirect_uri: str, use_sandbox: bool = False):
        self.client_id     = client_id
        self.client_secret = client_secret
        self.redirect_uri  = redirect_uri
        self.demo_mode     = not client_id or client_id in ("", "DEMO", "your_digilocker_client_id_here")

        if use_sandbox and not self.demo_mode:
            self._auth_url  = DIGILOCKER_SANDBOX_AUTH
            self._token_url = DIGILOCKER_SANDBOX_TOKEN
            self._user_url  = DIGILOCKER_SANDBOX_USER
        else:
            self._auth_url  = DIGILOCKER_AUTH_URL
            self._token_url = DIGILOCKER_TOKEN_URL
            self._user_url  = DIGILOCKER_USER_URL

        if self.demo_mode:
            logger.info("DigiLocker running in DEMO mode. Set DIGILOCKER_CLIENT_ID in .env for real verification.")

    # ── Step 1: Generate Authorization URL ────────────────────────────────────

    def get_auth_url(self) -> dict:
        """
        Generate DigiLocker OAuth 2.0 authorization URL with PKCE.
        Returns: { auth_url, state, demo_mode }
        """
        state = secrets.token_urlsafe(32)

        if self.demo_mode:
            _STATE_STORE[state] = {
                "code_verifier": "demo",
                "created_at": datetime.utcnow().isoformat(),
                "demo": True,
            }
            return {
                "auth_url": f"/api/digilocker/demo-callback?state={state}",
                "state": state,
                "demo_mode": True,
            }

        # PKCE: code_verifier + code_challenge
        code_verifier  = secrets.token_urlsafe(64)
        code_challenge = (
            base64.urlsafe_b64encode(
                hashlib.sha256(code_verifier.encode("ascii")).digest()
            ).rstrip(b"=").decode("ascii")
        )

        _STATE_STORE[state] = {
            "code_verifier": code_verifier,
            "created_at": datetime.utcnow().isoformat(),
            "demo": False,
        }

        params = {
            "response_type":         "code",
            "client_id":             self.client_id,
            "redirect_uri":          self.redirect_uri,
            "state":                 state,
            "code_challenge":        code_challenge,
            "code_challenge_method": "S256",
        }
        return {
            "auth_url":  self._auth_url + "?" + urlencode(params),
            "state":     state,
            "demo_mode": False,
        }

    # ── Step 2: Handle Callback (Real OAuth) ──────────────────────────────────

    async def handle_callback(self, code: str, state: str,
                               db: Session, ip_address: str = "",
                               user_agent: str = "") -> dict:
        """
        Exchange authorization code for access token, fetch user profile, persist to DB.
        Returns verified user profile dict with session_token.
        """
        # Validate state
        state_data = _STATE_STORE.pop(state, None)
        if not state_data:
            raise ValueError("Invalid or expired state token. Please restart verification.")

        created = datetime.fromisoformat(state_data["created_at"])
        if (datetime.utcnow() - created).total_seconds() > STATE_TTL_SECONDS:
            raise ValueError("Verification session expired. Please try again.")

        if state_data.get("demo"):
            raise ValueError("Demo mode: use /demo-callback endpoint.")

        import httpx

        # Exchange code for access token
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                token_resp = await client.post(
                    self._token_url,
                    data={
                        "grant_type":    "authorization_code",
                        "code":          code,
                        "client_id":     self.client_id,
                        "client_secret": self.client_secret,
                        "redirect_uri":  self.redirect_uri,
                        "code_verifier": state_data["code_verifier"],
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                token_resp.raise_for_status()
                token_data = token_resp.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"DigiLocker token exchange failed: {e.response.text}")
            raise ValueError(f"DigiLocker authentication failed: {e.response.status_code}")
        except Exception as e:
            logger.error(f"DigiLocker token exchange error: {e}")
            raise ValueError("Could not connect to DigiLocker. Please try again.")

        access_token = token_data.get("access_token")
        if not access_token:
            raise ValueError("No access token returned by DigiLocker.")

        # Fetch user profile
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                user_resp = await client.get(
                    self._user_url,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                user_resp.raise_for_status()
                user_data = user_resp.json()
        except Exception as e:
            logger.error(f"DigiLocker user profile fetch error: {e}")
            raise ValueError("Could not retrieve your DigiLocker profile.")

        profile = self._normalize_profile(user_data)
        session_token = self._persist_verification(
            db=db, profile=profile, is_demo=False,
            ip_address=ip_address, user_agent=user_agent
        )
        profile["session_token"] = session_token
        return profile

    # ── Demo Callback ─────────────────────────────────────────────────────────

    def handle_demo_callback(self, state: str, db: Session,
                              name: str = "", ip_address: str = "",
                              user_agent: str = "") -> dict:
        """
        Demo-mode callback: returns a mock verified profile, persisted to DB.
        Simulates what DigiLocker returns for real credentials.
        """
        state_data = _STATE_STORE.pop(state, None)
        if not state_data or not state_data.get("demo"):
            raise ValueError("Invalid demo state.")

        created = datetime.fromisoformat(state_data["created_at"])
        if (datetime.utcnow() - created).total_seconds() > STATE_TTL_SECONDS:
            raise ValueError("Demo session expired.")

        mock_suffix = str(secrets.randbelow(9000) + 1000)
        mock_aadhaar = f"XXXX-XXXX-XXXX-{mock_suffix}"
        profile = {
            "name":                name or "Demo Citizen",
            "dob":                 "01/01/1995",
            "gender":              "M",
            "aadhaar_suffix":      mock_suffix,
            "aadhaar_masked":      mock_aadhaar,
            "digilocker_id":       f"DL{secrets.token_hex(6).upper()}",
            "verified":            True,
            "verification_time":   datetime.utcnow().isoformat(),
            "verification_method": "DigiLocker-Demo",
        }
        session_token = self._persist_verification(
            db=db, profile=profile, is_demo=True,
            ip_address=ip_address, user_agent=user_agent
        )
        profile["session_token"] = session_token
        return profile

    # ── DB Persistence ────────────────────────────────────────────────────────

    def _persist_verification(self, db: Session, profile: dict,
                               is_demo: bool, ip_address: str = "",
                               user_agent: str = "") -> str:
        """
        Save verification record to the database.
        Returns the session_token for use in subsequent requests.
        """
        from models.db_models import CitizenVerification, ReporterProfile

        session_token = secrets.token_urlsafe(48)
        expires_at    = datetime.utcnow() + timedelta(hours=SESSION_TTL_HOURS)

        # Try to link to existing ReporterProfile by Aadhaar suffix
        # (best-effort — no personal data stored beyond last 4 digits)
        reporter_profile_id = None
        aadhaar_suffix = profile.get("aadhaar_suffix", "")
        if aadhaar_suffix:
            existing = db.query(ReporterProfile).filter(
                ReporterProfile.phone == f"AADHAAR_{aadhaar_suffix}"
            ).first()
            if existing:
                reporter_profile_id = existing.id

        verification = CitizenVerification(
            session_token       = session_token,
            verified_name       = profile.get("name", "Verified Citizen"),
            dob                 = profile.get("dob", ""),
            gender              = profile.get("gender", ""),
            aadhaar_suffix      = aadhaar_suffix,
            aadhaar_masked      = profile.get("aadhaar_masked", f"XXXX-XXXX-XXXX-{aadhaar_suffix}"),
            digilocker_id       = profile.get("digilocker_id", ""),
            verification_method = profile.get("verification_method", "DigiLocker"),
            is_demo             = is_demo,
            is_used             = False,
            is_expired          = False,
            ip_address          = ip_address,
            user_agent          = user_agent[:500] if user_agent else "",
            expires_at          = expires_at,
            reporter_profile_id = reporter_profile_id,
        )
        db.add(verification)
        db.commit()
        db.refresh(verification)

        logger.info(
            f"DigiLocker verification saved | id={verification.id} "
            f"| demo={is_demo} | name={profile.get('name')} | ip={ip_address}"
        )
        return session_token

    # ── Session Verification ──────────────────────────────────────────────────

    def verify_session(self, session_token: str, db: Session) -> Optional[dict]:
        """
        Validate a session token against the database.
        Returns the verified profile dict, or None if invalid/expired.
        """
        from models.db_models import CitizenVerification

        verification = db.query(CitizenVerification).filter(
            CitizenVerification.session_token == session_token
        ).first()

        if not verification:
            return None

        # Check expiry
        if datetime.utcnow() > verification.expires_at:
            verification.is_expired = True
            db.commit()
            logger.info(f"DigiLocker session expired: {session_token[:16]}...")
            return None

        if verification.is_expired:
            return None

        return {
            "id":                  verification.id,
            "name":                verification.verified_name,
            "dob":                 verification.dob,
            "gender":              verification.gender,
            "aadhaar_suffix":      verification.aadhaar_suffix,
            "aadhaar_masked":      verification.aadhaar_masked,
            "digilocker_id":       verification.digilocker_id,
            "verification_method": verification.verification_method,
            "verification_time":   verification.created_at.isoformat(),
            "is_demo":             verification.is_demo,
            "verified":            True,
            "session_token":       session_token,
        }

    def mark_session_used(self, session_token: str, db: Session) -> bool:
        """Mark a verification session as used (after report is submitted)."""
        from models.db_models import CitizenVerification

        verification = db.query(CitizenVerification).filter(
            CitizenVerification.session_token == session_token
        ).first()

        if not verification:
            return False

        verification.is_used = True
        db.commit()
        return True

    # ── Profile Normalization ─────────────────────────────────────────────────

    @staticmethod
    def _normalize_profile(raw: dict) -> dict:
        """Normalize DigiLocker API response into our standard profile format."""
        name = (
            raw.get("name") or raw.get("fullName") or raw.get("full_name") or
            f"{raw.get('firstName', '')} {raw.get('lastName', '')}".strip() or
            "Verified Citizen"
        )
        dob = raw.get("dob") or raw.get("dateOfBirth") or raw.get("date_of_birth") or ""
        gender = raw.get("gender") or raw.get("sex") or ""
        digilocker_id = (
            raw.get("digilockerid") or raw.get("digiLocker_id") or
            raw.get("sub") or raw.get("user_id") or ""
        )
        aadhaar_suffix = str(raw.get("aadhaarSuffix", raw.get("aadhaar_suffix", ""))).strip()

        return {
            "name":                name,
            "dob":                 dob,
            "gender":              gender,
            "aadhaar_suffix":      aadhaar_suffix,
            "aadhaar_masked":      f"XXXX-XXXX-XXXX-{aadhaar_suffix}" if aadhaar_suffix else "",
            "digilocker_id":       digilocker_id,
            "verified":            True,
            "verification_time":   datetime.utcnow().isoformat(),
            "verification_method": "DigiLocker-OAuth2-PKCE",
        }
