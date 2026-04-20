"""
AutoJustice AI NEXUS — DigiLocker OAuth 2.0 Routes
Endpoints for citizen identity verification via DigiLocker.

Routes:
  GET  /api/digilocker/auth-url        → get the DigiLocker login URL
  GET  /api/digilocker/callback        → OAuth callback (real credentials)
  GET  /api/digilocker/demo-callback   → demo mode callback (no real credentials)
  POST /api/digilocker/verify-session  → validate an existing session token
  GET  /api/digilocker/status          → check if DigiLocker is configured
"""
import logging
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel

from config import settings
from services.digilocker_service import DigiLockerService

logger = logging.getLogger(__name__)
router = APIRouter()

# ─── Service singleton ────────────────────────────────────────────────────────
_digilocker = DigiLockerService(
    client_id=getattr(settings, "digilocker_client_id", ""),
    client_secret=getattr(settings, "digilocker_client_secret", ""),
    redirect_uri=getattr(settings, "digilocker_redirect_uri",
                         "http://localhost:8000/api/digilocker/callback"),
    use_sandbox=getattr(settings, "digilocker_use_sandbox", True),
)


# ─── Schemas ─────────────────────────────────────────────────────────────────

class SessionVerifyRequest(BaseModel):
    session_token: str

class DemoCallbackRequest(BaseModel):
    state: str
    name: str = ""


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.get("/status")
def digilocker_status():
    """Returns DigiLocker configuration status."""
    return {
        "configured": not _digilocker.demo_mode,
        "demo_mode":  _digilocker.demo_mode,
        "message": (
            "DigiLocker configured — real Aadhaar verification active."
            if not _digilocker.demo_mode
            else "DigiLocker running in demo mode. Add DIGILOCKER_CLIENT_ID to .env for production."
        ),
    }


@router.get("/auth-url")
def get_auth_url():
    """
    Generate and return the DigiLocker OAuth 2.0 authorization URL.
    Frontend redirects citizen to this URL to start verification.
    """
    try:
        result = _digilocker.get_auth_url()
        return result
    except Exception as e:
        logger.error(f"DigiLocker auth URL generation failed: {e}")
        raise HTTPException(500, f"Failed to generate DigiLocker auth URL: {str(e)}")


@router.get("/callback")
async def digilocker_callback(
    request: Request,
    code: str = "",
    state: str = "",
    error: str = "",
    error_description: str = "",
):
    """
    DigiLocker OAuth 2.0 callback endpoint.
    Exchanges authorization code for access token, fetches user profile.
    Returns an HTML page that passes the verified session back to the citizen portal.
    """
    if error:
        logger.warning(f"DigiLocker callback error: {error} — {error_description}")
        return _callback_error_page(
            f"DigiLocker verification failed: {error_description or error}"
        )

    if not code or not state:
        return _callback_error_page("Missing code or state parameter from DigiLocker.")

    try:
        profile = await _digilocker.handle_callback(code, state)
        return _callback_success_page(profile)
    except ValueError as e:
        logger.warning(f"DigiLocker callback validation error: {e}")
        return _callback_error_page(str(e))
    except Exception as e:
        logger.error(f"DigiLocker callback unexpected error: {e}", exc_info=True)
        return _callback_error_page("An unexpected error occurred. Please try again.")


@router.get("/demo-callback")
def demo_callback(state: str = "", name: str = ""):
    """
    Demo mode callback — simulates DigiLocker verification without real credentials.
    Used for hackathon demo when DIGILOCKER_CLIENT_ID is not configured.
    """
    if not state:
        raise HTTPException(400, "Missing state parameter.")

    try:
        profile = _digilocker.handle_demo_callback(state, name=name)
        return _callback_success_page(profile)
    except ValueError as e:
        return _callback_error_page(str(e))


@router.get("/demo-verify")
def demo_verify(state: str = "", name: str = ""):
    """
    JSON version of demo-callback for direct fetch() calls from the citizen portal.
    Returns the verified profile as JSON — no popup or redirect required.
    """
    if not state:
        raise HTTPException(400, "Missing state parameter.")
    try:
        profile = _digilocker.handle_demo_callback(state, name=name)
        return {"ok": True, "profile": profile}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/verify-session")
def verify_session(body: SessionVerifyRequest):
    """
    Validate a DigiLocker session token issued after successful verification.
    Returns the verified profile if the session is valid.
    Used by the report submission endpoint to verify citizen identity.
    """
    profile = _digilocker.verify_session(body.session_token)
    if not profile:
        raise HTTPException(401, "Invalid or expired DigiLocker session. Please verify your identity again.")

    return {
        "valid":   True,
        "profile": {
            "name":                profile.get("name"),
            "dob":                 profile.get("dob"),
            "gender":              profile.get("gender"),
            "aadhaar_suffix":      profile.get("aadhaar_suffix"),
            "verified":            True,
            "verification_method": profile.get("verification_method"),
            "verification_time":   profile.get("verification_time"),
        },
    }


# ─── HTML Response Helpers ────────────────────────────────────────────────────

def _callback_success_page(profile: dict) -> HTMLResponse:
    """
    Returns an HTML page that posts the verified session data to the parent window
    via postMessage, then closes itself.
    The citizen portal JS listens for this message to proceed with the form.
    """
    session_token = profile.get("session_token", "")
    name          = profile.get("name", "Verified Citizen")
    dob           = profile.get("dob", "")
    gender        = profile.get("gender", "")
    aadhaar       = profile.get("aadhaar_masked", "") or (
        f"XXXX-XXXX-XXXX-{profile.get('aadhaar_suffix', '???')}"
        if profile.get("aadhaar_suffix") else ""
    )
    method        = profile.get("verification_method", "DigiLocker")
    is_demo       = "Demo" in method

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <title>DigiLocker Verification</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
  <style>
    * {{ box-sizing:border-box; margin:0; padding:0; }}
    body {{ font-family:'Inter',sans-serif; background:#f0fdf4; display:flex; align-items:center; justify-content:center; min-height:100vh; }}
    .card {{ background:white; border-radius:16px; padding:36px 32px; max-width:440px; width:100%; box-shadow:0 8px 32px rgba(0,0,0,0.12); text-align:center; }}
    .check {{ width:72px; height:72px; background:#16a34a; border-radius:50%; display:flex; align-items:center; justify-content:center; margin:0 auto 20px; }}
    .check svg {{ width:36px; height:36px; }}
    h2 {{ font-size:22px; font-weight:700; color:#0f172a; margin-bottom:8px; }}
    p {{ font-size:14px; color:#64748b; margin-bottom:20px; line-height:1.6; }}
    .info-grid {{ display:grid; gap:10px; margin-bottom:24px; text-align:left; }}
    .info-row {{ background:#f8fafc; padding:10px 14px; border-radius:8px; display:flex; justify-content:space-between; align-items:center; }}
    .info-label {{ font-size:11px; color:#94a3b8; font-weight:600; text-transform:uppercase; letter-spacing:0.5px; }}
    .info-value {{ font-size:14px; font-weight:600; color:#0f172a; }}
    .badge {{ display:inline-flex; align-items:center; gap:6px; background:#dcfce7; color:#15803d; padding:5px 12px; border-radius:999px; font-size:12px; font-weight:600; margin-bottom:20px; }}
    {"" if not is_demo else ".demo-note { background:#fff7ed; border:1px solid #fed7aa; padding:10px 14px; border-radius:8px; font-size:12px; color:#9a3412; margin-bottom:16px; text-align:left; }"}
    .btn {{ background:#1565c0; color:white; border:none; padding:12px 24px; border-radius:8px; font-size:14px; font-weight:600; cursor:pointer; width:100%; font-family:inherit; }}
    .btn:hover {{ background:#0d47a1; }}
    .spinner {{ display:inline-block; width:16px; height:16px; border:2px solid rgba(255,255,255,0.3); border-top-color:white; border-radius:50%; animation:spin 0.7s linear infinite; vertical-align:middle; margin-right:6px; }}
    @keyframes spin {{ to {{ transform:rotate(360deg); }} }}
  </style>
</head>
<body>
  <div class="card">
    <div class="check">
      <svg fill="none" stroke="white" stroke-width="3" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"/></svg>
    </div>
    <div class="badge">
      <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
      Identity Verified via DigiLocker
    </div>
    <h2>Verification Successful!</h2>
    <p>Your Aadhaar-linked identity has been verified. You may now submit your complaint securely.</p>
    {"<div class='demo-note'>⚠ <strong>Demo Mode:</strong> This is a simulated verification. In production, real Aadhaar-linked credentials are verified via DigiLocker.</div>" if is_demo else ""}
    <div class="info-grid">
      <div class="info-row">
        <span class="info-label">Verified Name</span>
        <span class="info-value">{name}</span>
      </div>
      {f'<div class="info-row"><span class="info-label">Date of Birth</span><span class="info-value">{dob}</span></div>' if dob else ''}
      {f'<div class="info-row"><span class="info-label">Aadhaar (masked)</span><span class="info-value" style="font-family:monospace">{aadhaar}</span></div>' if aadhaar else ''}
    </div>
    <button class="btn" id="continueBtn" onclick="sendToParent()">
      Continue to Report Submission
    </button>
  </div>

  <script>
    const SESSION_TOKEN = "{session_token}";
    const PROFILE = {{
      name:                "{name}",
      dob:                 "{dob}",
      gender:              "{gender}",
      aadhaar_suffix:      "{profile.get('aadhaar_suffix', '')}",
      session_token:       SESSION_TOKEN,
      verified:            true,
      verification_method: "{method}",
    }};

    function sendToParent() {{
      const btn = document.getElementById('continueBtn');
      btn.innerHTML = '<span class="spinner"></span>Continuing...';
      btn.disabled = true;

      if (window.opener && !window.opener.closed) {{
        // Popup window: send to opener
        window.opener.postMessage({{
          type: 'DIGILOCKER_VERIFIED',
          profile: PROFILE,
        }}, window.location.origin);
        setTimeout(() => window.close(), 500);
      }} else if (window.parent && window.parent !== window) {{
        // iframe: send to parent
        window.parent.postMessage({{
          type: 'DIGILOCKER_VERIFIED',
          profile: PROFILE,
        }}, window.location.origin);
      }} else {{
        // Same-tab redirect: store in sessionStorage and go back
        sessionStorage.setItem('digilocker_profile', JSON.stringify(PROFILE));
        sessionStorage.setItem('digilocker_session', SESSION_TOKEN);
        window.location.href = '/';
      }}
    }}

    // Auto-trigger if this was opened as a popup
    if (window.opener && !window.opener.closed) {{
      setTimeout(sendToParent, 1000);
    }}
  </script>
</body>
</html>"""
    return HTMLResponse(content=html)


def _callback_error_page(message: str) -> HTMLResponse:
    """Returns an HTML error page that notifies the parent window."""
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <title>Verification Failed</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
  <style>
    * {{ box-sizing:border-box; margin:0; padding:0; }}
    body {{ font-family:'Inter',sans-serif; background:#fef2f2; display:flex; align-items:center; justify-content:center; min-height:100vh; }}
    .card {{ background:white; border-radius:16px; padding:36px 32px; max-width:440px; width:100%; box-shadow:0 8px 32px rgba(0,0,0,0.12); text-align:center; }}
    .icon {{ width:72px; height:72px; background:#dc2626; border-radius:50%; display:flex; align-items:center; justify-content:center; margin:0 auto 20px; font-size:32px; }}
    h2 {{ font-size:22px; font-weight:700; color:#0f172a; margin-bottom:12px; }}
    p {{ font-size:14px; color:#64748b; margin-bottom:24px; line-height:1.6; }}
    .error-box {{ background:#fef2f2; border:1px solid #fecaca; padding:12px 16px; border-radius:8px; font-size:13px; color:#991b1b; margin-bottom:20px; }}
    .btn {{ background:#1a2a4a; color:white; border:none; padding:12px 24px; border-radius:8px; font-size:14px; font-weight:600; cursor:pointer; width:100%; font-family:inherit; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">✕</div>
    <h2>Verification Failed</h2>
    <div class="error-box">{message}</div>
    <p>Please close this window and try verifying your identity again.</p>
    <button class="btn" onclick="notifyAndClose()">Close & Retry</button>
  </div>
  <script>
    function notifyAndClose() {{
      if (window.opener && !window.opener.closed) {{
        window.opener.postMessage({{ type: 'DIGILOCKER_ERROR', message: '{message}' }}, window.location.origin);
        window.close();
      }} else {{
        window.location.href = '/';
      }}
    }}
  </script>
</body>
</html>"""
    return HTMLResponse(content=html)
