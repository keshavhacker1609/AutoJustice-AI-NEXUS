"""
AutoJustice AI NEXUS — One-Click Demo Launcher
Seeds demo data + starts the server in a single command.

Run: python run_demo.py
"""
import sys
import os
import subprocess
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).parent / "backend"


def print_banner():
    print("\n" + "=" * 62)
    print("  AI NEXUS — Cyber Crime Intelligence Platform")
    print("  Prototype v1.0 | Hackathon Demo Build")
    print("=" * 62)


def check_env():
    env_path = BACKEND_DIR / ".env"
    if not env_path.exists():
        print("\n  ⚠  WARNING: backend/.env not found.")
        print("     Gemini AI features will use rule-based fallback.")
        print("     Add GEMINI_API_KEY to backend/.env for full AI features.\n")
    else:
        # Check if API key is set
        content = env_path.read_text()
        if "your_gemini_api_key_here" in content or "GEMINI_API_KEY=" not in content:
            print("\n  ⚠  Gemini API key not configured in backend/.env")
            print("     System will run with rule-based AI fallback.\n")


def seed_demo_data():
    print("\n  📊 Seeding demo data...")
    try:
        result = subprocess.run(
            [sys.executable, "demo_seed.py"],
            cwd=str(Path(__file__).parent),
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    print(" ", line.strip())
        else:
            print("  ⚠  Seed warning:", result.stderr[:200] if result.stderr else "Unknown error")
    except Exception as e:
        print(f"  ⚠  Seed failed: {e} (continuing anyway)")


def print_urls():
    print("\n" + "─" * 62)
    print("  🌐  LIVE URLS — Open in browser:")
    print("")
    print("  📋  Citizen Portal    →  http://localhost:8000")
    print("  🚨  Police Dashboard  →  http://localhost:8000/dashboard")
    print("  🔑  Officer Login     →  http://localhost:8000/login")
    print("  📖  API Docs          →  http://localhost:8000/api/docs")
    print("")
    print("  🔐  Default Login: admin / Admin@12345")
    print("")
    print("─" * 62)
    print("  Press Ctrl+C to stop the server")
    print("─" * 62 + "\n")


def main():
    print_banner()
    check_env()
    seed_demo_data()
    print_urls()

    os.chdir(BACKEND_DIR)

    subprocess.run([
        sys.executable, "-m", "uvicorn",
        "main:app",
        "--reload",
        "--host", "0.0.0.0",
        "--port", "8000",
        "--log-level", "warning",  # Cleaner output for demo
    ])


if __name__ == "__main__":
    main()
