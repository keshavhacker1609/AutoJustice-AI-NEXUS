# AutoJustice AI NEXUS
### AI-Driven Digital Forensics & Automated Threat Triage Platform

> **Prototype v1.0** — Built for law enforcement hackathon demonstration

---

## Quick Start (5 Minutes)

### 1. Prerequisites
- Python 3.10+
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) (Windows installer)
- Google Gemini API Key (free at [aistudio.google.com](https://aistudio.google.com))

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment
Edit `backend/.env`:
```
GEMINI_API_KEY=your_actual_key_here
TESSERACT_PATH=C:/Program Files/Tesseract-OCR/tesseract.exe
```

### 4. Run
```bash
python run.py
```

### 5. Open in Browser
| URL | Description |
|-----|-------------|
| http://localhost:8000 | **Citizen Portal** — Submit reports |
| http://localhost:8000/dashboard | **Police Dashboard** — Command center |
| http://localhost:8000/api/docs | **API Docs** — Swagger UI |

---

## Architecture

```
AutoJustice-AI (Nexus)/
├── backend/
│   ├── main.py                  # FastAPI app entry point
│   ├── config.py                # Centralized configuration
│   ├── database.py              # SQLite/SQLAlchemy ORM
│   ├── models/
│   │   ├── db_models.py         # Report, EvidenceFile, AuditLog
│   │   └── schemas.py           # Pydantic request/response models
│   ├── routers/
│   │   ├── reports.py           # Submit, list, get, FIR endpoints
│   │   └── dashboard.py         # Stats + audit log endpoints
│   ├── services/
│   │   ├── ocr_service.py       # Tesseract OCR extraction
│   │   ├── ai_triage_service.py # Gemini semantic risk classification
│   │   ├── fake_detection_service.py # 6-layer fake report detection
│   │   ├── fir_generator.py     # ReportLab PDF FIR generation
│   │   └── hash_service.py      # SHA-256 chain of custody
│   ├── templates/
│   │   ├── citizen_portal.html  # Citizen submission UI
│   │   └── police_dashboard.html # Officer command dashboard
│   └── static/js/
│       ├── citizen.js           # Citizen portal JS
│       └── dashboard.js         # Dashboard charts + tables
├── requirements.txt
├── run.py                       # Server launcher
└── .env.example
```

---

## AI Pipeline Flow

```
Citizen Upload
     ↓
OCR Extraction (Tesseract)
     ↓
SHA-256 Hash (Section 65B)
     ↓
Fake Detection (6-Layer AI)
  L1: Keyword density analysis
  L2: Gemini narrative coherence
  L3: Evidence-description correlation
  L4: Entity consistency validation
  L5: Duplicate fingerprint detection
  L6: Behavioral anomaly scoring
     ↓
AI Semantic Triage (Gemini)
  - Risk Level: HIGH / MEDIUM / LOW
  - Crime Category + BNS/IPC sections
  - Entity extraction (victim, suspect, financial)
     ↓
FIR Auto-Generation (ReportLab PDF)
  - Legally structured document
  - Section 65B certificate
  - SHA-256 integrity hash
     ↓
Police Dashboard Alert
```

---

## Compliance Framework

| Regulation | Implementation |
|-----------|----------------|
| Section 65B (Indian Evidence Act) | SHA-256 hash on every file + FIR |
| DPDP Act 2023 | PII fields isolated, no third-party sharing |
| BNS 2023 | Auto-mapped crime sections in FIR |
| IT Act 2000 | Cyber offence classification |

---

## Fake Report Detection (Anti-Gaming)

The system uses 6 independent detection layers to prevent false reports even when trigger words are deliberately inserted:

1. **Keyword Stuffing** — detects unnatural density of high-risk keywords
2. **Gemini Coherence Check** — semantic analysis of narrative logic
3. **Evidence Correlation** — checks if uploaded evidence matches the description
4. **Entity Consistency** — validates named entities are internally consistent
5. **Duplicate Detection** — SHA-256 content fingerprinting prevents resubmission
6. **Template Detection** — identifies copy-pasted report patterns

Each layer produces a score. Weighted composite determines final recommendation:
- **GENUINE** (>65%) → proceed to FIR
- **REVIEW** (45–65%) → officer manually reviews
- **REJECT** (<45%) → flagged, case closed

---

## Production Roadmap

- [ ] PostgreSQL + async SQLAlchemy
- [ ] Redis + Celery for async AI pipeline
- [ ] JWT officer authentication
- [ ] NGINX reverse proxy + WAF
- [ ] PDF digital signature (PKI)
- [ ] Multi-language (Hindi/regional)
- [ ] SMS/Email notifications
- [ ] Mobile app for citizens
- [ ] ML-based image tamper detection
