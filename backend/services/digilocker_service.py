"""
AutoJustice AI NEXUS — DigiLocker OAuth 2.0 Identity Verification Service
Integrates with India's official DigiLocker API (MeitY) for citizen authentication.

Real OAuth 2.0 flow with PKCE (Proof Key for Code Exchange).
Fetches Aadhaar-verified name, DOB, gender from DigiLocker user profile.

To use real DigiLocker:
  Register at: https://partners.digitallocker.gov.in/
  Add DIGILOCKER_CLIENT_ID and DIGILOCKER_CLIENT_SECRET to .env

Demo mode (no credentials): returns mock verified profile for hackathon demo.
"""
import hashlib
import hmac
import logging
import secrets
import base64
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

# ─── DigiLocker API Endpoints (Production) ────────────────────────────────────
DIGILOCKER_AUTH_URL   = "https://api.digitallocker.gov.in/public/oauth2/1/authorize"
DIGILOCKER_TOKEN_URL  = "https://api.digitallocker.gov.in/public/oauth2/1/token"
DIGILOCKER_USER_URL   = "https://api.digitallocker.gov.in/public/oauth2/1/user"

# Sandbox endpoints (use for testing before production approval)
DIGILOCKER_SANDBOX_AUTH  = "https://digilocker.meripehchaan.gov.in/public/oauth2/1/authorize"
DIGILOCKER_SANDBOX_TOKEN = "https://digilocker.meripehchaan.gov.in/public/oauth2/1/token"
DIGILOCKER_SANDBOX_USER  = "https://digilocker.meripehchaan.gov.in/public/oauth2/1/user"


# ─── In-memory state store (Redis in production) ──────────────────────────────
# Maps state_token → {code_verifier, created_at}
_STATE_STORE: dict = {}
# Maps session_token → verified profile
_SESSION_STORE: dict = {}

STATE_TTL_SECONDS    = 600   # 10 min to complete OAuth flow
SESSION_TTL_SECONDS  = 3600  # 1 hour session after verification


class DigiLockerService:
    """
    Full DigiLocker OAuth 2.0 + PKCE identity verification service.

    Flow:
      1. get_auth_url()     → redirect user to DigiLocker login
      2. handle_callback()  → exchange code → get access token → fetch profile
      3. verify_session()   → validate session token from subsequent requests
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        use_sandbox: bool = False,
    ):
        self.client_id     = client_id
        self.client_secret = client_secret
        self.redirect_uri  = redirect_uri
        self.demo_mode     = not client_id or client_id == "DEMO"

        if use_sandbox and not self.demo_mode:
            self._auth_url  = DIGILOCKER_SANDBOX_AUTH
            self._token_url = DIGILOCKER_SANDBOX_TOKEN
            self._user_url  = DIGILOCKER_SANDBOX_USER
        else:
            self._auth_url  = DIGILOCKER_AUTH_URL
            self._token_url = DIGILOCKER_TOKEN_URL
            self._user_url  = DIGILOCKER_USER_URL

        if self.demo_mode:
            logger.info(
                "DigiLocker running in DEMO mode. "
                "Set DIGILOCKER_CLIENT_ID in .env for real verification."
            )

    # ── Step 1: Generate Authorization URL ────────────────────────────────────

    def get_auth_url(self) -> dict:
        """
        Generate DigiLocker OAuth 2.0 authorization URL with PKCE.
        Returns: { auth_url, state, demo_mode }
        """
        state = secrets.token_urlsafe(32)

        if self.demo_mode:
            # Return a demo URL — no real redirect needed
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

        # PKCE: generate code_verifier and code_challenge
        code_verifier  = secrets.token_urlsafe(64)
        code_challenge = (
            base64.urlsafe_b64encode(
                hashlib.sha256(code_verifier.encode("ascii")).digest()
            )
            .rstrip(b"=")
            .decode("ascii")
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

    # ── Step 2: Handle Callback ───────────────────────────────────────────────

    async def handle_callback(self, code: str, state: str) -> dict:
        """
        Exchange authorization code for access token, fetch user profile.
        Returns verified user profile dict.
        Raises ValueError on any failure.
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

        profile = self._normalize_profile(user_data, access_token)
        session_token = self._create_session(profile)
        profile["session_token"] = session_token
        return profile

    # ── Demo Callback (for hackathon demo without real credentials) ───────────

    def handle_demo_callback(self, state: str, name: str = "", aadhaar_suffix: str = "") -> dict:
        """
        Demo-mode callback: returns a mock verified profile.
        Simulates what DigiLocker would return for real credentials.
        """
        state_data = _STATE_STORE.pop(state, None)
        if not state_data or not state_data.get("demo"):
            raise ValueError("Invalid demo state.")

        created = datetime.fromisoformat(state_data["created_at"])
        if (datetime.utcnow() - created).total_seconds() > STATE_TTL_SECONDS:
            raise ValueError("Demo session expired.")

        # Generate a realistic mock profile
        mock_aadhaar = f"XXXX-XXXX-{secrets.randbelow(9000) + 1000}"
        profile = {
            "name":           name or "Demo Citizen",
            "dob":            "01/01/1995",
            "gender":         "M",
            "aadhaar_suffix": aadhaar_suffix or mock_aadhaar[-4:],
            "digilocker_id":  f"DL{secrets.token_hex(6).upper()}",
            "verified":       True,
            "verification_time": datetime.utcnow().isoformat(),
            "verification_method": "DigiLocker-Demo",
            "aadhaar_masked": mock_aadhaar,
        }

        session_token = self._create_session(profile)
        profile["session_token"] = session_token
        return profile

    # ── Session Management ────────────────────────────────────────────────────

    def _create_session(self, profile: dict) -> str:
        """Create a secure session token for the verified profile."""
        session_token = secrets.token_urlsafe(48)
        _SESSION_STORE[session_token] = {
            "profile":    profile,
            "created_at": datetime.utcnow().isoformat(),
        }
        # Clean up expired sessions
        self._cleanup_sessions()
        return session_token

    def verify_session(self, session_token: str) -> Optional[dict]:
        """
        Validate a session token.
        Returns the verified profile dict, or None if invalid/expired.
        """
        session = _SESSION_STORE.get(session_token)
        if not session:
            return None

        created = datetime.fromisoformat(session["created_at"])
        if (datetime.utcnow() - created).total_seconds() > SESSION_TTL_SECONDS:
            _SESSION_STORE.pop(session_token, None)
            return None

        return session["profile"]

    def _cleanup_sessions(self):
        """Remove expired sessions to prevent memory leak."""
        cutoff = datetime.utcnow() - timedelta(seconds=SESSION_TTL_SECONDS)
        expired = [
            k for k, v in _SESSION_STORE.items()
            if datetime.fromisoformat(v["created_at"]) < cutoff
        ]
        for k in expired:
            _SESSION_STORE.pop(k, None)

        # Also cleanup state store
        cutoff_state = datetime.utcnow() - timedelta(seconds=STATE_TTL_SECONDS)
        expired_states = [
            k for k, v in _STATE_STORE.items()
            if datetime.fromisoformat(v["created_at"]) < cutoff_state
        ]
        for k in expired_states:
            _STATE_STORE.pop(k, None)

    # ── Profile Normalization ─────────────────────────────────────────────────

    @staticmethod
    def _normalize_profile(raw: dict, access_token: str) -> dict:
        """
        Normalize DigiLocker API response into our standard profile format.
        DigiLocker returns different field names depending on API version.
        """
        # Handle both v1 and v2 response formats
        name = (
            raw.get("name") or
            raw.get("fullName") or
            raw.get("full_name") or
            f"{raw.get('firstName', '')} {raw.get('lastName', '')}".strip() or
            "Verified Citizen"
        )

        dob = (
            raw.get("dob") or
            raw.get("dateOfBirth") or
            raw.get("date_of_birth") or
            ""
        )

        gender = (
            raw.get("gender") or
            raw.get("sex") or
            ""
        )

        digilocker_id = (
            raw.get("digilockerid") or
            raw.get("digiLocker_id") or
            raw.get("sub") or
            raw.get("user_id") or
            ""
        )

        # Aadhaar is never fully exposed — only last 4 digits
        aadhaar_suffix = str(raw.get("aadhaarSuffix", raw.get("aadhaar_suffix", ""))).strip()

        return {
            "name":                name,
            "dob":                 dob,
            "gender":              gender,
            "aadhaar_suffix":      aadhaar_suffix,
            "digilocker_id":       digilocker_id,
            "verified":            True,
            "verification_time":   datetime.utcnow().isoformat(),
            "verification_method": "DigiLocker-OAuth2-PKCE",
        }
