"""
AutoJustice AI NEXUS — Mobile Exposure Helper

One command to:
  1. Boot the FastAPI server on 0.0.0.0:8000
  2. Open an ngrok HTTPS tunnel
  3. Print the public URL + render a QR code you can scan from your phone
  4. Keep logs streaming until Ctrl+C

Usage:
    python expose_mobile.py

Prereqs:
    pip install qrcode[pil] requests     (already in requirements.txt territory)
    ngrok (installed via winget)
    One-time: ngrok config add-authtoken <TOKEN>   (grab free token at dashboard.ngrok.com)
"""
from __future__ import annotations

import os
import sys
import time
import subprocess
import shutil
import threading
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    # Line-buffer so every print() flushes immediately (important for mixed subprocess stdout)
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
except Exception:
    pass

# Force every print to flush — we share stdout with uvicorn's child process
_orig_print = print
def print(*a, **kw):
    kw.setdefault("flush", True)
    _orig_print(*a, **kw)

import requests

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
PORT = 8000
NGROK_API = "http://127.0.0.1:4040/api/tunnels"

# Known ngrok install paths (winget puts it here on Windows)
NGROK_CANDIDATES = [
    shutil.which("ngrok"),
    r"C:\Users\Kesha\AppData\Local\Microsoft\WinGet\Packages\Ngrok.Ngrok_Microsoft.Winget.Source_8wekyb3d8bbwe\ngrok.exe",
]
NGROK = next((p for p in NGROK_CANDIDATES if p and Path(p).exists()), None)


def banner(msg: str, color="96"):
    bar = "═" * 72
    print(f"\033[{color};1m{bar}\n  {msg}\n{bar}\033[0m")


def start_server() -> subprocess.Popen:
    banner(f"Starting uvicorn on 0.0.0.0:{PORT}", "95")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(BACKEND)
    # Sensible mobile-friendly defaults — rate limit ON (real users), SMTP/SMS off
    env.setdefault("RATE_LIMIT_ENABLED", "true")
    env.setdefault("DEBUG", "false")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app",
         "--host", "0.0.0.0", "--port", str(PORT),
         "--log-level", "info"],
        cwd=str(BACKEND), env=env,
    )
    # Wait for /api/health
    for _ in range(60):
        try:
            r = requests.get(f"http://127.0.0.1:{PORT}/api/health", timeout=1)
            if r.status_code == 200:
                print(f"\033[92m  ✓ Server healthy: {r.json()}\033[0m")
                return proc
        except Exception:
            pass
        time.sleep(0.5)
    raise RuntimeError("Server didn't come up within 30s")


def start_ngrok():
    """Returns (process, public_https_url)."""
    if not NGROK:
        raise RuntimeError(
            "ngrok not found. Install with: winget install --id Ngrok.Ngrok"
        )
    banner("Opening ngrok tunnel", "95")
    print(f"  binary: {NGROK}")

    # Windows: DETACHED_PROCESS (0x08) so ngrok runs in its own process group
    # and doesn't share our stdio/TTY (ngrok v3 refuses to tunnel when it thinks
    # it has no TTY unless --log=stdout is passed — and even then it's finicky).
    creation = 0
    if os.name == "nt":
        creation = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | 0x00000008  # DETACHED_PROCESS
    proc = subprocess.Popen(
        [NGROK, "http", str(PORT), "--log=stdout", "--log-format=logfmt", "--log-level=info"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        creationflags=creation,
        close_fds=True,
    )
    print(f"  ngrok pid: {proc.pid}")

    # Poll local ngrok API for the public URL (ngrok opens 4040 within ~2s)
    last_err = ""
    for i in range(60):
        try:
            r = requests.get(NGROK_API, timeout=1)
            if r.status_code == 200:
                for t in r.json().get("tunnels", []):
                    url = t.get("public_url", "")
                    if url.startswith("https://"):
                        return proc, url
        except Exception as e:
            last_err = str(e)
        if proc.poll() is not None:
            raise RuntimeError(
                f"ngrok exited with code {proc.returncode} before opening a tunnel.\n"
                f"Common causes:\n"
                f"  - Missing authtoken → run: ngrok config add-authtoken <TOKEN>\n"
                f"    (free at https://dashboard.ngrok.com/get-started/your-authtoken)\n"
                f"  - Another ngrok session already running (free tier = 1 at a time)"
            )
        time.sleep(0.5)
    raise RuntimeError(
        f"ngrok didn't expose a public URL in 30s. Last API error: {last_err}\n"
        f"Check http://127.0.0.1:4040 in your browser for details."
    )


def print_qr(url: str):
    """Render the URL as a QR code in the terminal."""
    try:
        import qrcode
    except ImportError:
        print("\n[hint] pip install 'qrcode[pil]' to see a scannable QR here.")
        return
    qr = qrcode.QRCode(border=1)
    qr.add_data(url)
    qr.make(fit=True)
    qr.print_ascii(invert=True)


def main():
    if not NGROK:
        print("\033[91m!! ngrok.exe not found on PATH.\033[0m")
        print("   Install:  winget install --id Ngrok.Ngrok")
        print("   Auth:     ngrok config add-authtoken <TOKEN>   (free at dashboard.ngrok.com)")
        sys.exit(1)

    srv = start_server()
    try:
        ngrok_proc, url = start_ngrok()
    except Exception as e:
        srv.terminate()
        print(f"\033[91m{e}\033[0m")
        sys.exit(1)

    banner("🌐  LIVE ON MOBILE  🌐", "92")
    print()
    print(f"  Public URL  : \033[96;1m{url}\033[0m")
    print(f"  Citizen     : {url}/")
    print(f"  Officer     : {url}/login")
    print(f"  Track case  : {url}/track")
    print(f"  API docs    : {url}/api/docs")
    print(f"  Health      : {url}/api/health")
    print()
    print("  📱  Scan the QR below on your phone:")
    print()
    print_qr(url)
    print()
    print("  ngrok inspector: http://127.0.0.1:4040  (see every request from your phone)")
    print()
    print("\033[93m  Ctrl+C to stop the server + tunnel\033[0m")
    print()

    try:
        srv.wait()
    except KeyboardInterrupt:
        print("\n\033[96m[STOP] tearing down server + ngrok...\033[0m")
    finally:
        for p in (ngrok_proc, srv):
            try:
                p.terminate()
                p.wait(timeout=4)
            except Exception:
                try: p.kill()
                except Exception: pass
        print("\033[92m  ✓ Stopped\033[0m")


if __name__ == "__main__":
    main()
