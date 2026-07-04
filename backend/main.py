"""
AutoJustice AI NEXUS - FastAPI Application Entry Point
AI-Driven Digital Forensics & Automated Threat Triage Platform
"""
import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse

sys.path.insert(0, str(Path(__file__).parent))

from database import engine, Base, SessionLocal
from routers import reports, dashboard
from routers.auth import router as auth_router, ensure_default_admin
from routers.cases import router as cases_router
from routers.digilocker import router as digilocker_router
from middleware.rate_limiter import RateLimiterMiddleware
from config import settings

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ─── Application Lifespan ─────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info(f"  {settings.app_name} v{settings.app_version}")
    logger.info("  Initializing database schema...")
    Base.metadata.create_all(bind=engine)

    # ── Lightweight migrations: add new columns to existing DBs ──────────────────
    from sqlalchemy import inspect, text
    _insp = inspect(engine)
    if _insp.has_table("reports"):
        _existing = {c["name"] for c in _insp.get_columns("reports")}
        _new_cols = {
            # Phase 2 — jurisdiction
            "detected_state":            "VARCHAR(64)",
            "detected_district":         "VARCHAR(64)",
            "detected_jurisdiction":     "VARCHAR(128)",
            "jurisdiction_confidence":   "FLOAT",
            "is_forwarded":              "BOOLEAN DEFAULT 0",
            "forwarded_to_station":      "VARCHAR(128)",
            "forwarded_to_state":        "VARCHAR(64)",
            "forwarded_at":              "DATETIME",
            "forwarded_by":              "VARCHAR(64)",
            "forwarding_reason":         "TEXT",
            # Phase 3 — DigiLocker identity verification
            "digilocker_dob":            "VARCHAR(20)",
            "digilocker_gender":         "VARCHAR(10)",
            "digilocker_aadhaar_suffix": "VARCHAR(10)",
            "digilocker_method":         "VARCHAR(50)",
            "citizen_verification_id":   "VARCHAR(36)",
            # Phase 4 — Officer dashboard management
            "is_priority":               "BOOLEAN DEFAULT FALSE",
        }
        with engine.begin() as conn:
            for col, ddl in _new_cols.items():
                if col not in _existing:
                    try:
                        conn.execute(text(f"ALTER TABLE reports ADD COLUMN {col} {ddl}"))
                        logger.info(f"  migrated: added reports.{col}")
                    except Exception as e:
                        logger.warning(f"  migration skip {col}: {e}")

    # Create default admin account if no officers exist
    db = SessionLocal()
    try:
        ensure_default_admin(db)
    finally:
        db.close()

    logger.info("  Database ready.")
    logger.info(f"  Station: {settings.station_name}")
    logger.info(f"  Rate limiting: {'enabled' if settings.rate_limit_enabled else 'disabled'}")
    logger.info("=" * 60)
    yield
    logger.info("AutoJustice AI NEXUS shutting down.")


# ─── FastAPI App ──────────────────────────────────────────────────────────────
# In production the interactive docs and OpenAPI schema are disabled so the full
# API surface is not disclosed publicly. Enable with EXPOSE_DOCS=true (or DEBUG=true).
_docs_enabled = settings.expose_docs or settings.debug

app = FastAPI(
    title="AutoJustice AI NEXUS",
    description=(
        "AI-Driven Digital Forensics & Automated Threat Triage Platform for Law Enforcement. "
        "Powered by Google Gemini + Tesseract OCR. "
        "Section 65B | BNS 2023 | DPDP Act 2023 Compliant."
    ),
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/api/docs" if _docs_enabled else None,
    redoc_url="/api/redoc" if _docs_enabled else None,
    openapi_url="/openapi.json" if _docs_enabled else None,
)

# ─── Middleware ───────────────────────────────────────────────────────────────
app.add_middleware(RateLimiterMiddleware)

_allowed_origins = os.environ.get(
    "ALLOWED_ORIGINS",
    "http://localhost:8000,http://127.0.0.1:8000,"
    "https://keshavsingla16-autojustice-ai-nexus.hf.space"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

# ─── Static Files & Templates ─────────────────────────────────────────────────
BACKEND_DIR = Path(__file__).parent
STATIC_DIR = BACKEND_DIR / "static"
STATIC_DIR.mkdir(exist_ok=True)
(STATIC_DIR / "css").mkdir(exist_ok=True)
(STATIC_DIR / "js").mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.middleware("http")
async def no_cache_js_css(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/static/js/") or request.url.path.startswith("/static/css/"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response
templates = Jinja2Templates(directory=str(BACKEND_DIR / "templates"))

# ─── API Routers ──────────────────────────────────────────────────────────────
app.include_router(auth_router,       prefix="/api/auth",       tags=["Authentication"])
app.include_router(reports.router,    prefix="/api/reports",    tags=["Reports"])
app.include_router(dashboard.router,  prefix="/api/dashboard",  tags=["Dashboard"])
app.include_router(cases_router,      prefix="/api/cases",      tags=["Case Management"])
app.include_router(digilocker_router, prefix="/api/digilocker", tags=["DigiLocker Identity"])


# ─── Frontend Routes ──────────────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
async def citizen_portal(request: Request):
    """Citizen evidence submission portal."""
    return templates.TemplateResponse(
        request=request,
        name="citizen_portal.html",
        context={"station_name": settings.station_name},
    )


@app.get("/dashboard", include_in_schema=False)
async def police_dashboard(request: Request):
    """Police command dashboard."""
    return templates.TemplateResponse(
        request=request,
        name="police_dashboard.html",
        context={"station_name": settings.station_name},
    )


@app.get("/track", include_in_schema=False)
@app.get("/track/{case_number}", include_in_schema=False)
async def track_case(request: Request, case_number: str = ""):
    """Citizen case tracking page."""
    return templates.TemplateResponse(
        request=request,
        name="case_tracking.html",
        context={"case_number": case_number, "station_name": settings.station_name},
    )


@app.get("/login", include_in_schema=False)
async def login_page(request: Request):
    """Officer login page."""
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"station_name": settings.station_name},
    )


# ─── PWA Routes ──────────────────────────────────────────────────────────────
@app.get("/sw.js", include_in_schema=False)
async def service_worker():
    """Serve service worker at root scope (required for full PWA offline support)."""
    from fastapi.responses import FileResponse as _FR
    sw_path = STATIC_DIR / "sw.js"
    return _FR(str(sw_path), media_type="application/javascript",
               headers={"Service-Worker-Allowed": "/"})


@app.get("/offline", include_in_schema=False)
@app.get("/offline.html", include_in_schema=False)
async def offline_page():
    """PWA offline fallback page."""
    from fastapi.responses import FileResponse as _FR
    return _FR(str(STATIC_DIR / "offline.html"), media_type="text/html")


# ─── Health Check ─────────────────────────────────────────────────────────────
@app.get("/api/health", tags=["System"])
async def health_check():
    return {
        "status": "operational",
        "system": settings.app_name,
        "version": settings.app_version,
        "station": settings.station_name,
    }


# ─── AI Diagnostic (temporary) ────────────────────────────────────────────────
# Reports the true state of the Gemini integration and performs a live probe so
# silent fallbacks can be diagnosed without digging through container logs.
# Does NOT expose the API key. Remove once the Gemini path is confirmed healthy.
@app.get("/api/health/ai", tags=["System"])
async def ai_health_check():
    key = settings.gemini_api_key or ""
    result = {
        "gemini_key_present": bool(key),
        "gemini_key_len": len(key),
        "gemini_key_prefix": (key[:6] + "…") if key else None,
        "configured_model": settings.gemini_model,
        "sdk_import": None,
        "probe_ok": False,
        "probe_error": None,
        "probe_text": None,
    }
    try:
        from google import genai as _genai
        from google.genai import types as _gtypes
        result["sdk_import"] = "ok"
    except Exception as e:
        result["sdk_import"] = f"FAILED: {type(e).__name__}: {e}"
        return result
    if not key:
        result["probe_error"] = "No GEMINI_API_KEY set"
        return result
    try:
        _client = _genai.Client(api_key=key)
        _resp = _client.models.generate_content(
            model=settings.gemini_model,
            contents="Reply with the single word: OK",
            config=_gtypes.GenerateContentConfig(max_output_tokens=5, temperature=0.0),
        )
        result["probe_ok"] = True
        result["probe_text"] = (getattr(_resp, "text", "") or "").strip()[:50]
    except Exception as e:
        result["probe_error"] = f"{type(e).__name__}: {str(e)[:400]}"
    return result


# ─── Global Error Handler ─────────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error. Please contact system administrator."},
    )
