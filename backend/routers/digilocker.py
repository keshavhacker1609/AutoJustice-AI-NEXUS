"""
AutoJustice AI NEXUS — DigiLocker OAuth 2.0 Routes
All verification sessions are persisted to the database.

Routes:
  GET  /api/digilocker/status              → config status
  GET  /api/digilocker/auth-url            → get DigiLocker login URL
  GET  /api/digilocker/callback            → OAuth callback (real credentials)
  GET  /api/digilocker/demo-callback       → demo mode callback
  GET  /api/digilocker/demo-verify         → JSON demo verify
  POST /api/digilocker/verify-session      → validate session token from DB
  GET  /api/digilocker/profile/{token}     → get full verified profile by token
"""
import logging
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from services.digilocker_service import DigiLockerService

logger = logging.getLogger(__name__)
router = APIRouter()

# ─── Service singleton ────────────────────────────────────────────────────────
_digilocker = DigiLockerService(
    client_id     = getattr(settings, "digilocker_client_id", ""),
    client_secret = getattr(settings, "digilocker_client_secret", ""),
    redirect_uri  = getattr(settings, "digilocker_redirect_uri",
                            "http://localhost:8000/api/digilocker/callback"),
    use_sandbox   = getattr(settings, "digilocker_use_sandbox", True),
)


# ─── Schemas ──────────────────────────────────────────────────────────────────

class SessionVerifyRequest(BaseModel):
    session_token: str


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/status")
def digilocker_status():
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
    """Generate DigiLocker OAuth 2.0 authorization URL."""
    try:
        return _digilocker.get_auth_url()
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
    db: Session = Depends(get_db),
):
    """
    DigiLocker OAuth 2.0 callback.
    Exchanges code → access token → fetches profile → persists to DB.
    Returns HTML page that passes session back to citizen portal via postMessage.
    """
    if error:
        logger.warning(f"DigiLocker callback error: {error} — {error_description}")
        return _callback_error_page(f"DigiLocker verification failed: {error_description or error}")

    if not code or not state:
        return _callback_error_page("Missing code or state parameter from DigiLocker.")

    ip_address = request.client.host if request.client else ""
    user_agent = request.headers.get("user-agent", "")

    try:
        profile = await _digilocker.handle_callback(
            code=code, state=state, db=db,
            ip_address=ip_address, user_agent=user_agent
        )
        return _callback_success_page(profile)
    except ValueError as e:
        logger.warning(f"DigiLocker callback validation error: {e}")
        return _callback_error_page(str(e))
    except Exception as e:
        logger.error(f"DigiLocker callback unexpected error: {e}", exc_info=True)
        return _callback_error_page("An unexpected error occurred. Please try again.")


@router.get("/demo-callback")
def demo_callback(
    request: Request,
    state: str = "",
    name: str = "",
    db: Session = Depends(get_db),
):
    """
    Demo mode callback — simulates DigiLocker verification.
    Persists to DB just like real verification.
    """
    if not state:
        raise HTTPException(400, "Missing state parameter.")

    ip_address = request.client.host if request.client else ""
    user_agent = request.headers.get("user-agent", "")

    try:
        profile = _digilocker.handle_demo_callback(
            state=state, db=db, name=name,
            ip_address=ip_address, user_agent=user_agent
        )
        return _callback_success_page(profile)
    except ValueError as e:
        return _callback_error_page(str(e))


@router.get("/demo-verify")
def demo_verify(
    request: Request,
    state: str = "",
    name: str = "",
    db: Session = Depends(get_db),
):
    """JSON version of demo-callback for direct fetch() calls."""
    if not state:
        raise HTTPException(400, "Missing state parameter.")

    ip_address = request.client.host if request.client else ""
    user_agent = request.headers.get("user-agent", "")

    try:
        profile = _digilocker.handle_demo_callback(
            state=state, db=db, name=name,
            ip_address=ip_address, user_agent=user_agent
        )
        return {"ok": True, "profile": profile}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/verify-session")
def verify_session(body: SessionVerifyRequest, db: Session = Depends(get_db)):
    """
    Validate a DigiLocker session token from the database.
    Returns the full verified profile if valid.
    """
    profile = _digilocker.verify_session(body.session_token, db=db)
    if not profile:
        raise HTTPException(
            401,
            "Invalid or expired DigiLocker session. Please verify your identity again."
        )
    return {
        "valid":   True,
        "profile": {
            "name":                profile.get("name"),
            "dob":                 profile.get("dob"),
            "gender":              profile.get("gender"),
            "aadhaar_suffix":      profile.get("aadhaar_suffix"),
            "aadhaar_masked":      profile.get("aadhaar_masked"),
            "digilocker_id":       profile.get("digilocker_id"),
            "verified":            True,
            "is_demo":             profile.get("is_demo", False),
            "verification_method": profile.get("verification_method"),
            "verification_time":   profile.get("verification_time"),
        },
    }


@router.get("/profile/{session_token}")
def get_verification_profile(session_token: str, db: Session = Depends(get_db)):
    """
    Get full verified profile by session token.
    Used by the citizen portal to pre-fill the complaint form.
    """
    profile = _digilocker.verify_session(session_token, db=db)
    if not profile:
        raise HTTPException(
            401,
            "Invalid or expired DigiLocker session. Please verify your identity again."
        )
    return {"ok": True, "profile": profile}


# ─── HTML Response Helpers ────────────────────────────────────────────────────

def _callback_success_page(profile: dict) -> HTMLResponse:
    """
    Returns HTML page that sends verified session to parent window via postMessage.
    """
    session_token = profile.get("session_token", "")
    name          = profile.get("name", "Verified Citizen")
    dob           = profile.get("dob", "")
    gender_raw    = profile.get("gender", "")
    gender_label  = {"M": "Male", "F": "Female", "T": "Transgender"}.get(gender_raw, gender_raw)
    aadhaar       = profile.get("aadhaar_masked") or (
        f"XXXX-XXXX-XXXX-{profile.get('aadhaar_suffix')}"
        if profile.get("aadhaar_suffix") else ""
    )
    method   = profile.get("verification_method", "DigiLocker")
    is_demo  = "Demo" in method

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>DigiLocker Verified</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Inter', sans-serif;
      background: linear-gradient(135deg, #e8f5e9 0%, #e3f2fd 100%);
      display: flex; align-items: center; justify-content: center;
      min-height: 100vh; padding: 20px;
    }}
    .card {{
      background: white; border-radius: 20px; padding: 40px 36px;
      max-width: 460px; width: 100%;
      box-shadow: 0 20px 60px rgba(0,0,0,0.12);
    }}
    .icon-wrap {{
      width: 80px; height: 80px; border-radius: 50%;
      background: linear-gradient(135deg, #16a34a, #15803d);
      display: flex; align-items: center; justify-content: center;
      margin: 0 auto 20px;
      box-shadow: 0 8px 24px rgba(22,163,74,0.3);
    }}
    .icon-wrap svg {{ width: 40px; height: 40px; }}
    .badge {{
      display: inline-flex; align-items: center; gap: 6px;
      background: #dcfce7; color: #15803d;
      padding: 6px 14px; border-radius: 999px;
      font-size: 12px; font-weight: 600;
      margin-bottom: 16px; letter-spacing: 0.3px;
    }}
    h2 {{
      font-size: 24px; font-weight: 700; color: #0f172a;
      margin-bottom: 8px; text-align: center;
    }}
    .subtitle {{
      font-size: 14px; color: #64748b; text-align: center;
      margin-bottom: 28px; line-height: 1.6;
    }}
    .info-grid {{ display: grid; gap: 10px; margin-bottom: 28px; }}
    .info-row {{
      background: #f8fafc; padding: 12px 16px; border-radius: 10px;
      display: flex; justify-content: space-between; align-items: center;
      border: 1px solid #e2e8f0;
    }}
    .info-label {{
      font-size: 11px; color: #94a3b8; font-weight: 600;
      text-transform: uppercase; letter-spacing: 0.8px;
    }}
    .info-value {{ font-size: 14px; font-weight: 600; color: #1e293b; }}
    .info-value.mono {{ font-family: 'Courier New', monospace; letter-spacing: 1px; }}
    .demo-banner {{
      background: #fffbeb; border: 1px solid #fcd34d;
      padding: 10px 14px; border-radius: 10px;
      font-size: 12px; color: #92400e;
      margin-bottom: 20px; line-height: 1.5;
    }}
    .stored-badge {{
      display: flex; align-items: center; gap: 8px;
      background: #eff6ff; border: 1px solid #bfdbfe;
      padding: 10px 14px; border-radius: 10px;
      font-size: 12px; color: #1d4ed8;
      margin-bottom: 20px;
    }}
    .btn {{
      background: linear-gradient(135deg, #1565c0, #0d47a1);
      color: white; border: none;
      padding: 14px 24px; border-radius: 10px;
      font-size: 15px; font-weight: 600;
      cursor: pointer; width: 100%; font-family: inherit;
      transition: opacity 0.2s; letter-spacing: 0.3px;
    }}
    .btn:hover {{ opacity: 0.92; }}
    .btn:disabled {{ opacity: 0.6; cursor: not-allowed; }}
    .spinner {{
      display: inline-block; width: 16px; height: 16px;
      border: 2px solid rgba(255,255,255,0.4);
      border-top-color: white; border-radius: 50%;
      animation: spin 0.7s linear infinite;
      vertical-align: middle; margin-right: 8px;
    }}
    @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
    .text-center {{ text-align: center; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="text-center">
      <div class="icon-wrap">
        <svg fill="none" stroke="white" stroke-width="2.5" viewBox="0 0 24 24">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
          <polyline points="9 12 11 14 15 10"/>
        </svg>
      </div>
      <div class="badge">
        <svg width="12" height="12" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
        </svg>
        Identity Verified via DigiLocker
      </div>
      <h2>Verification Successful</h2>
      <p class="subtitle">Your Aadhaar-linked identity has been confirmed.<br>You may now proceed to file your complaint.</p>
    </div>

    {"<div class='demo-banner'><strong>Demo Mode:</strong> This is a simulated verification for testing. In production, your real Aadhaar-linked identity is verified directly through DigiLocker.</div>" if is_demo else ""}

    <div class="stored-badge">
      <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/>
        <circle cx="12" cy="7" r="4"/>
      </svg>
      Identity record saved securely to the AutoJustice database
    </div>

    <div class="info-grid">
      <div class="info-row">
        <span class="info-label">Verified Name</span>
        <span class="info-value">{name}</span>
      </div>
      {f'<div class="info-row"><span class="info-label">Date of Birth</span><span class="info-value">{dob}</span></div>' if dob else ''}
      {f'<div class="info-row"><span class="info-label">Gender</span><span class="info-value">{gender_label}</span></div>' if gender_label else ''}
      {f'<div class="info-row"><span class="info-label">Aadhaar (masked)</span><span class="info-value mono">{aadhaar}</span></div>' if aadhaar else ''}
      <div class="info-row">
        <span class="info-label">Verification Method</span>
        <span class="info-value">{method}</span>
      </div>
    </div>

    <button class="btn" id="continueBtn" onclick="sendToParent()">
      Continue to File Complaint
    </button>
  </div>

  <script>
    const SESSION_TOKEN = "{session_token}";
    const PROFILE = {{
      name:                "{name}",
      dob:                 "{dob}",
      gender:              "{gender_raw}",
      gender_label:        "{gender_label}",
      aadhaar_suffix:      "{profile.get('aadhaar_suffix', '')}",
      aadhaar_masked:      "{aadhaar}",
      session_token:       SESSION_TOKEN,
      verified:            true,
      is_demo:             {"true" if is_demo else "false"},
      verification_method: "{method}",
    }};

    function sendToParent() {{
      const btn = document.getElementById('continueBtn');
      btn.innerHTML = '<span class="spinner"></span>Continuing...';
      btn.disabled = true;

      const msg = {{ type: 'DIGILOCKER_VERIFIED', profile: PROFILE }};

      if (window.opener && !window.opener.closed) {{
        window.opener.postMessage(msg, '*');
        setTimeout(() => window.close(), 800);
      }} else if (window.parent && window.parent !== window) {{
        window.parent.postMessage(msg, '*');
      }} else {{
        sessionStorage.setItem('digilocker_profile', JSON.stringify(PROFILE));
        sessionStorage.setItem('digilocker_session', SESSION_TOKEN);
        window.location.href = '/';
      }}
    }}

    // Auto-send after 1.5s if opened as popup
    if (window.opener && !window.opener.closed) {{
      setTimeout(sendToParent, 1500);
    }}
  </script>
</body>
</html>"""
    return HTMLResponse(content=html)


def _callback_error_page(message: str) -> HTMLResponse:
    """Returns HTML error page that notifies the parent window."""
    safe_message = message.replace("'", "\\'").replace('"', '\\"')
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Verification Failed</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Inter', sans-serif;
      background: linear-gradient(135deg, #fef2f2 0%, #fefce8 100%);
      display: flex; align-items: center; justify-content: center;
      min-height: 100vh; padding: 20px;
    }}
    .card {{
      background: white; border-radius: 20px; padding: 40px 36px;
      max-width: 460px; width: 100%;
      box-shadow: 0 20px 60px rgba(0,0,0,0.12); text-align: center;
    }}
    .icon-wrap {{
      width: 80px; height: 80px; border-radius: 50%;
      background: linear-gradient(135deg, #dc2626, #b91c1c);
      display: flex; align-items: center; justify-content: center;
      margin: 0 auto 20px;
      box-shadow: 0 8px 24px rgba(220,38,38,0.3);
      font-size: 36px;
    }}
    h2 {{ font-size: 24px; font-weight: 700; color: #0f172a; margin-bottom: 12px; }}
    .error-box {{
      background: #fef2f2; border: 1px solid #fecaca;
      padding: 14px 16px; border-radius: 10px;
      font-size: 13px; color: #991b1b; margin: 16px 0 24px; line-height: 1.5;
    }}
    p {{ font-size: 14px; color: #64748b; margin-bottom: 24px; line-height: 1.6; }}
    .btn {{
      background: #1a2a4a; color: white; border: none;
      padding: 14px 24px; border-radius: 10px;
      font-size: 15px; font-weight: 600;
      cursor: pointer; width: 100%; font-family: inherit;
    }}
  </style>
</head>
<body>
  <div class="card">
    <div class="icon-wrap">✕</div>
    <h2>Verification Failed</h2>
    <div class="error-box">{message}</div>
    <p>Please close this window and try verifying your identity again.</p>
    <button class="btn" onclick="notifyAndClose()">Close & Retry</button>
  </div>
  <script>
    function notifyAndClose() {{
      const msg = {{ type: 'DIGILOCKER_ERROR', message: '{safe_message}' }};
      if (window.opener && !window.opener.closed) {{
        window.opener.postMessage(msg, '*');
        window.close();
      }} else if (window.parent && window.parent !== window) {{
        window.parent.postMessage(msg, '*');
      }} else {{
        window.location.href = '/';
      }}
    }}
  </script>
</body>
</html>"""
    return HTMLResponse(content=html)
