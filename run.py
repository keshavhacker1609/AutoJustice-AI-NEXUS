"""
AutoJustice AI NEXUS v2.0 — Development Server Launcher
Run this file to start the application: python3.12 run.py
"""
import sys
import os
import subprocess
from pathlib import Path


def find_python():
    """
    Find a working Python 3.11/3.12/3.13 interpreter.
    Python 3.14+ may have package compatibility issues — prefer 3.12.
    """
    current_major = sys.version_info.major
    current_minor = sys.version_info.minor

    # If already running a compatible version, use it
    if current_major == 3 and current_minor in (11, 12, 13):
        return sys.executable

    # If on 3.14+, try to find 3.12 or 3.13 explicitly
    if current_major == 3 and current_minor >= 14:
        for candidate in ["python3.12", "python3.13", "python3.11"]:
            try:
                result = subprocess.run(
                    [candidate, "--version"], capture_output=True, text=True
                )
                if result.returncode == 0:
                    print(f"  Note: Using {candidate} (your default python3 is {sys.version.split()[0]})")
                    return candidate
            except FileNotFoundError:
                continue

    return sys.executable


def check_env():
    env_path = Path(__file__).parent / "backend" / ".env"
    if not env_path.exists():
        print("\n  WARNING: backend/.env not found.")
        print("  Copy .env.example to backend/.env and fill in your GEMINI_API_KEY.")
        print("  The system will run in FALLBACK mode (rule-based AI, no Gemini).\n")
        return False
    return True


def check_deps():
    missing = []
    try:
        import fastapi
    except ImportError:
        missing.append("fastapi")
    try:
        import sqlalchemy
    except ImportError:
        missing.append("sqlalchemy")
    try:
        import passlib
    except ImportError:
        missing.append("passlib[bcrypt]")
    try:
        import jose
    except ImportError:
        missing.append("python-jose[cryptography]")
    try:
        import reportlab
    except ImportError:
        missing.append("reportlab")
    try:
        import pydantic_settings
    except ImportError:
        missing.append("pydantic-settings")
    if missing:
        print(f"\n  ERROR: Missing packages: {', '.join(missing)}")
        print(f"  Fix: {find_python()} -m pip install -r requirements.txt\n")
        return False
    return True


def main():
    print("=" * 60)
    print("  AutoJustice AI NEXUS v2.0")
    print("  AI-Driven Digital Forensics & Threat Triage Platform")
    print("=" * 60)

    check_env()
    if not check_deps():
        sys.exit(1)

    python_exec = find_python()
    backend_dir = Path(__file__).parent / "backend"

    print("\n  Starting development server on http://localhost:8000")
    print()
    print("  Citizen Portal    ->  http://localhost:8000/")
    print("  Track Case        ->  http://localhost:8000/track")
    print("  Officer Login     ->  http://localhost:8000/login")
    print("  Police Dashboard  ->  http://localhost:8000/dashboard")
    print("  API Docs          ->  http://localhost:8000/api/docs")
    print()
    print("  Default login: admin / <see backend/.env DEFAULT_ADMIN_PASSWORD>")
    print("  IMPORTANT: Change the default password before deploying!")
    print()
    print("  Press Ctrl+C to stop.\n")

    os.chdir(backend_dir)

    subprocess.run([
        python_exec, "-m", "uvicorn",
        "main:app",
        "--reload",
        "--host", "0.0.0.0",
        "--port", "8000",
        "--log-level", "info",
    ])


if __name__ == "__main__":
    main()
