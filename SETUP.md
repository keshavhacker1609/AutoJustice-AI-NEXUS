# AutoJustice AI NEXUS — Complete Setup Guide

## What This Is
A FastAPI + Jinja2 web platform for AI-driven digital forensics and cyber crime complaint triage.  
**Stack:** Python 3.11/3.12, FastAPI, SQLAlchemy, Google Gemini AI, Tesseract OCR, ReportLab PDF.

---

## PART 1 — Run Locally on Windows (VS Code)

### Step 1: Install Prerequisites

| Tool | Download |
|------|----------|
| Python 3.11 or 3.12 | https://www.python.org/downloads/ (check "Add to PATH") |
| Tesseract OCR | https://github.com/UB-Mannheim/tesseract/wiki → download installer |
| VS Code | https://code.visualstudio.com |
| Git | https://git-scm.com |

After installing Tesseract, note its path — usually:
`C:\Program Files\Tesseract-OCR\tesseract.exe`

### Step 2: Open in VS Code

```
File → Open Folder → select the "AutoJustice-AI (Nexus)" folder
```

Install the **Python extension** (ms-python.python) when VS Code prompts.

### Step 3: Create & Activate a Virtual Environment

Open VS Code Terminal (Ctrl + `) and run:

```bash
# Create venv
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Install all dependencies
pip install -r requirements.txt
```

### Step 4: Configure Environment

Edit `backend/.env` and set your values:

```env
# REQUIRED: Your Gemini API key
# Get it free at: https://makersuite.google.com/app/apikey
GEMINI_API_KEY=your-actual-api-key-here

# REQUIRED: Full path to Tesseract on Windows
TESSERACT_PATH=C:/Program Files/Tesseract-OCR/tesseract.exe

# Change this before going live!
DEFAULT_ADMIN_PASSWORD=YourStrongPassword@2024!

# Generate a new secret key (run in Python):
# python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=your-generated-secret-here
```

### Step 5: Run the App

```bash
# From the project root (where run.py is)
python run.py
```

Open your browser:
- **Citizen Portal:** http://localhost:8000/
- **Officer Login:** http://localhost:8000/login
- **Police Dashboard:** http://localhost:8000/dashboard (login first)
- **Case Tracking:** http://localhost:8000/track
- **API Docs:** http://localhost:8000/api/docs

**Default login:** `admin` / (whatever you set in `DEFAULT_ADMIN_PASSWORD`)

### VS Code Recommended Extensions

Install these for best experience:
- `ms-python.python` — Python language support
- `ms-python.pylance` — Type checking
- `ms-python.black-formatter` — Auto formatting
- `humao.rest-client` — Test API endpoints

### VS Code Launch Configuration

Create `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "AutoJustice Dev Server",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": ["main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"],
      "cwd": "${workspaceFolder}/backend",
      "env": {"PYTHONPATH": "${workspaceFolder}/backend"},
      "jinja": true
    }
  ]
}
```

---

## PART 2 — Push to GitHub

### Step 1: Initialize Git Repository

```bash
# In project root
git init
git add .
git commit -m "feat: AutoJustice AI NEXUS v2.0 - initial commit"
```

### Step 2: Create GitHub Repository

1. Go to https://github.com/new
2. Repository name: `autojustice-ai-nexus`
3. Set to **Private** (this handles law enforcement data!)
4. Do NOT initialize with README (we already have one)
5. Click **Create repository**

### Step 3: Push to GitHub

```bash
git remote add origin https://github.com/YOUR_USERNAME/autojustice-ai-nexus.git
git branch -M main
git push -u origin main
```

> **IMPORTANT:** The `.gitignore` excludes `backend/.env`, `*.db`, `uploads/`, and `firs/` to prevent committing credentials or evidence files. **Never remove these from .gitignore.**

---

## PART 3 — Deploy to Render

Render is the recommended hosting platform. It supports Docker, PostgreSQL, and has a free tier for testing.

### Step 1: Create Render Account

Go to https://render.com and sign up with your GitHub account.

### Step 2: Create a New Web Service

1. Click **New** → **Web Service**
2. Connect your GitHub repo (`autojustice-ai-nexus`)
3. **Runtime:** Docker
4. **Region:** Singapore (or nearest to you)
5. **Plan:** Starter ($7/mo) — free tier sleeps after 15 min

Render auto-detects our `Dockerfile` and `render.yaml`.

### Step 3: Set Environment Variables in Render Dashboard

In the Render service → **Environment** tab, add these manually:

| Variable | Value |
|----------|-------|
| `GEMINI_API_KEY` | Your Gemini API key |
| `DEFAULT_ADMIN_PASSWORD` | A strong password (NOT the default) |

All other variables are defined in `render.yaml` and set automatically.

### Step 4: Create PostgreSQL Database

1. Click **New** → **PostgreSQL**
2. Name: `autojustice-db`
3. Plan: **Free** (1 GB, good for testing)
4. Region: Same as web service

Copy the **Internal Database URL** and set it as `DATABASE_URL` in the web service environment variables.

OR let `render.yaml` handle it — the `fromDatabase` property links them automatically.

### Step 5: Deploy

```bash
git push origin main
```

Render auto-deploys on every push to `main`. Watch the build log in the Render dashboard.

Your live URL will be: `https://autojustice-ai-nexus.onrender.com`

### Step 6: Post-Deployment Checklist

- [ ] Visit `https://your-app.onrender.com/api/health` — should return `{"status": "operational"}`
- [ ] Log in at `/login` with your admin credentials
- [ ] Change `ALLOWED_ORIGINS` in Render env to your actual domain
- [ ] Set a strong `DEFAULT_ADMIN_PASSWORD`
- [ ] Add a custom domain in Render dashboard (Settings → Custom Domains)

---

## IMPORTANT NOTES

### Tesseract OCR on Render
Tesseract is installed via the `Dockerfile` (`apt-get install tesseract-ocr`). This is why we use Docker runtime on Render — Python-only runtime does not support system packages.

### File Storage on Render
Render's filesystem is **ephemeral** — uploaded files and generated FIRs are stored in `/tmp` and will be wiped on each deploy. For production:
- Use **Render Disks** (persistent storage) — add to `render.yaml`
- OR integrate **AWS S3 / Cloudflare R2** for file storage

### AI Fallback Mode
If `GEMINI_API_KEY` is not set or invalid, the system automatically falls back to rule-based detection. Core functionality (case tracking, FIR generation, dashboard) works without Gemini. AI-powered analysis (triage, fake detection, entity extraction) requires a valid key.

### Database Migration (SQLite → PostgreSQL)
When `DATABASE_URL` points to PostgreSQL, the app automatically creates tables on first start (via `Base.metadata.create_all`). No migration tool needed for initial setup.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError: pydantic_settings` | `pip install pydantic-settings` |
| `tesseract is not installed` | Set `TESSERACT_PATH=C:/Program Files/Tesseract-OCR/tesseract.exe` in `.env` |
| `bcrypt` version error | `pip install bcrypt==3.2.2` |
| Dashboard 401 Unauthorized | Log in at `/login` first — all dashboard API calls require JWT token |
| Port 8000 already in use | `python run.py` → uses port 8000. Kill other process or change `--port` in `run.py` |
| Render deploy fails | Check build logs — usually a system package or Python version issue |

