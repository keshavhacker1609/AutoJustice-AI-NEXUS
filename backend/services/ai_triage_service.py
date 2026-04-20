"""
AutoJustice AI NEXUS - AI Triage Service (Google Gemini)
Performs semantic analysis, risk scoring, entity extraction, and BNS/IPC section mapping.
Designed with structured prompts to resist hallucination and keyword-gaming.
"""
import json
import logging
import re
from typing import Optional
from models.schemas import TriageResult

logger = logging.getLogger(__name__)

# ─── Gemini Setup (google-genai new SDK) ─────────────────────────────────────
try:
    from google import genai
    from google.genai import types as genai_types
    from config import settings
    GEMINI_AVAILABLE = bool(settings.gemini_api_key)
except Exception as e:
    GEMINI_AVAILABLE = False
    logger.warning(f"Gemini API unavailable: {e}")

# ─── BNS/IPC Section Reference Mapping ───────────────────────────────────────
BNS_SECTIONS = {
    "Cyber Fraud": ["BNS Section 318 (Cheating)", "IT Act Section 66D (Cheating by impersonation)", "IT Act Section 43 (Damage to computer)"],
    "Online Harassment": ["BNS Section 351 (Criminal Intimidation)", "IT Act Section 66A (Offensive messages)", "BNS Section 79 (Abetment)"],
    "Identity Theft": ["IT Act Section 66C (Identity theft)", "IT Act Section 66D (Impersonation)", "BNS Section 336 (Forgery)"],
    "Financial Crime": ["BNS Section 316 (Criminal breach of trust)", "PMLA Section 3 (Money laundering)", "IT Act Section 66D"],
    "Data Breach": ["IT Act Section 43A (Failure to protect data)", "IT Act Section 66 (Hacking)", "DPDP Act 2023"],
    "Extortion": ["BNS Section 308 (Extortion)", "IT Act Section 66E (Privacy violation)", "BNS Section 351"],
    "Child Safety": ["POCSO Act Section 13 (Child pornography)", "IT Act Section 67B", "BNS Section 94"],
    "Impersonation": ["IT Act Section 66D", "BNS Section 336 (Forgery)", "BNS Section 340 (False personation)"],
    "Other Cybercrime": ["IT Act Section 66 (Hacking/unauthorized access)", "BNS Section 115 (Voluntarily causing hurt)"],
}

TRIAGE_PROMPT = """
You are a senior forensic AI analyst for the Indian Cyber Crime Police. Your task is to analyze
a citizen-submitted report and extract structured intelligence for law enforcement.

CRITICAL INSTRUCTIONS:
- Base your analysis ONLY on what is actually described, not on trigger words alone
- If the description is vague, incoherent, or lacks specific details, reflect that in a lower risk score
- A threat must have: a specific victim, a specific harmful act, and plausible context to be HIGH risk

AI CHATBOT EVIDENCE RULE (apply before all other scoring):
- If the OCR evidence text contains ChatGPT, Claude, Gemini, Bing AI, or any AI chatbot interface output,
  the risk_score must be capped at 0.40 (MEDIUM at most) and risk_level must be "MEDIUM" or "LOW".
- Reason: anyone can prompt an AI chatbot to generate threatening text. A screenshot of ChatGPT saying
  "I will harm you" proves only that the submitter typed that prompt — it is NOT evidence of a real crime.
- Set crime_subcategory to "Suspected Fabricated Evidence" in this case.
- This is different from a criminal USING AI tools (e.g., AI-generated deepfake for sextortion) — that IS
  a real crime. The distinction: is ChatGPT the evidence of the crime, or is a human criminal the evidence?

REPORT CONTENT:
---
Incident Description: {description}

OCR-Extracted Evidence Text: {evidence_text}
---

Respond in STRICT JSON format (no markdown, no extra text):
{{
  "risk_level": "HIGH" | "MEDIUM" | "LOW",
  "risk_score": <float 0.0-1.0>,
  "crime_category": "<primary category from: Cyber Fraud, Online Harassment, Identity Theft, Financial Crime, Data Breach, Extortion, Child Safety, Impersonation, Other Cybercrime>",
  "crime_subcategory": "<specific type, e.g., 'UPI Fraud', 'Sextortion', 'Phishing'>",
  "ai_summary": "<2-3 sentence factual summary of the alleged incident for police briefing>",
  "entities": {{
    "victim": "<name if mentioned, else null>",
    "suspect": "<name/handle/entity if mentioned, else null>",
    "financial_amount": "<amount if mentioned, else null>",
    "financial_vector": "<UPI/bank/crypto/etc if mentioned, else null>",
    "platform": "<WhatsApp/Telegram/Instagram/etc if mentioned, else null>",
    "location": "<location if mentioned, else null>",
    "contact_numbers": ["<any phone numbers mentioned>"],
    "urls_links": ["<any URLs or handles mentioned>"]
  }},
  "bns_sections": ["<list 2-4 most applicable BNS/IPC/IT Act sections>"],
  "reasoning": "<1 sentence explaining why this risk level was assigned>"
}}
"""


class AITriageService:
    """
    Semantic triage engine powered by Google Gemini.
    Classifies threat level and extracts structured entities for FIR generation.
    """

    def __init__(self):
        self.client = None
        if GEMINI_AVAILABLE:
            from config import settings
            try:
                self.client = genai.Client(api_key=settings.gemini_api_key)
                self._model_name = settings.gemini_model
            except Exception as e:
                logger.error(f"Gemini client init failed: {e}")
                self.client = None

    def analyze(self, description: str, evidence_text: str = "") -> TriageResult:
        """
        Full semantic analysis of a report submission.
        Falls back to rule-based analysis if Gemini is unavailable.
        """
        if self.client and GEMINI_AVAILABLE:
            try:
                return self._gemini_analyze(description, evidence_text)
            except Exception as e:
                logger.error(f"Gemini analysis failed: {e}. Using fallback.")

        return self._fallback_analyze(description, evidence_text)

    def _gemini_analyze(self, description: str, evidence_text: str) -> TriageResult:
        """Execute Gemini semantic analysis with structured output parsing."""
        prompt = TRIAGE_PROMPT.format(
            description=description[:3000],
            evidence_text=evidence_text[:2000] if evidence_text else "No evidence text extracted"
        )

        response = self.client.models.generate_content(
            model=self._model_name,
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                temperature=0.1,
                top_p=0.8,
                max_output_tokens=1500,
            ),
        )
        raw = response.text.strip()

        # Strip markdown code blocks if present
        raw = re.sub(r"```(?:json)?", "", raw).strip()

        data = json.loads(raw)

        # Map to BNS sections from our reference if AI provided generic text
        category = data.get("crime_category", "Other Cybercrime")
        bns = data.get("bns_sections", BNS_SECTIONS.get(category, BNS_SECTIONS["Other Cybercrime"]))

        return TriageResult(
            risk_level=data.get("risk_level", "LOW"),
            risk_score=float(data.get("risk_score", 0.2)),
            crime_category=category,
            crime_subcategory=data.get("crime_subcategory", "General"),
            ai_summary=data.get("ai_summary", "Unable to generate summary."),
            entities=data.get("entities", {}),
            bns_sections=bns,
        )

    def _fallback_analyze(self, description: str, evidence_text: str) -> TriageResult:
        """
        Rule-based fallback when Gemini is unavailable.
        Uses keyword matching + context scoring (inferior to Gemini but functional).
        """
        text = (description + " " + evidence_text).lower()

        # Weighted keyword scoring with context requirements
        high_indicators = {
            "transferred money": 3, "sent money": 3, "upi fraud": 4,
            "account hacked": 4, "blackmail": 4, "sextortion": 5, "threat": 2,
            "nude": 4, "ransom": 5, "extort": 4, "child": 3, "minor": 3,
            "suicide": 3, "bomb": 5, "kill": 4, "murder": 4, "fake profile": 3,
            "demanded": 3, "demand money": 4, "pay or": 3, "will kill": 5,
            "kill me": 5, "kill my family": 5, "harm you": 3, "harm my": 3,
            "threatening": 3, "life threat": 5, "kidnap": 4, "abduct": 4,
        }
        medium_indicators = {
            "harassment": 2, "abuse": 2, "fraud": 2, "scam": 2, "phishing": 2,
            "impersonation": 2, "stalking": 2, "cheat": 2,
            "otp": 2, "debit": 2, "debited": 2, "hacked": 3,
            "blackmailed": 4, "cheated": 2, "duped": 2, "threatened": 2,
            "demand": 2, "pay else": 2, "wont pay": 2, "won't pay": 2,
        }

        # ── AI chatbot evidence check (before all other scoring) ──────────────
        _AI_CHATBOT_RE = re.compile(
            r'\bchatgpt\b|\bgpt[-\s]?[34o]\b|\bopenai\b|\bclaude\b'
            r'|\bgemini\b|\bbing\s*ai\b|\bai\s*chatbot\b|\bcopilot\b|\bperplexity\b',
            re.IGNORECASE,
        )
        has_chatbot_evidence = bool(_AI_CHATBOT_RE.search(text))

        high_score = sum(w for kw, w in high_indicators.items() if kw in text)
        medium_score = sum(w for kw, w in medium_indicators.items() if kw in text)

        # ── Financial loss boost ───────────────────────────────────────────────
        _amount_re = re.compile(
            r'\bRs\.?\s*[\d,]+|\bINR\s*[\d,]+|₹\s*[\d,]+'
            r'|[\d,]+\s*(?:rs|rupees|/-)\b',
            re.IGNORECASE,
        )
        if _amount_re.search(text):
            medium_score += 3

        if high_score >= 4:
            risk_level, risk_score = "HIGH", min(0.5 + high_score * 0.05, 0.95)
        elif medium_score >= 3 or high_score >= 2:
            risk_level, risk_score = "MEDIUM", min(0.40 + medium_score * 0.03, 0.75)
        else:
            risk_level, risk_score = "LOW", 0.15

        # ── AI chatbot cap — must apply AFTER scoring ──────────────────────────
        if has_chatbot_evidence:
            if risk_level == "HIGH":
                risk_level = "MEDIUM"
            risk_score = min(risk_score, 0.40)
            logger.info("Triage risk capped: AI chatbot detected in evidence text")

        # Detect most likely category
        categories = {
            "Extortion": ["blackmail", "extort", "ransom", "nude", "sextortion",
                          "demanded", "demand money", "will kill", "kill me",
                          "pay or", "wont pay", "won't pay", "kidnap", "abduct",
                          "life threat", "threatening"],
            "Financial Crime": ["upi", "bank", "money", "transfer", "payment",
                                "fraud", "rupees", "rs.", "inr", "debit", "credited"],
            "Online Harassment": ["harass", "abuse", "bully", "threaten", "stalk",
                                  "intimidat"],
            "Identity Theft": ["fake profile", "impersonat", "identity"],
            "Child Safety": ["child", "minor", "pocso"],
        }

        detected_category = "Other Cybercrime"
        for cat, keywords in categories.items():
            if any(kw in text for kw in keywords):
                detected_category = cat
                break

        # Try ML crime classifier
        try:
            from ml.predictor import ml_predictor
            ml_crime = ml_predictor.predict_crime(description)
            if ml_crime.get("available") and ml_crime.get("confidence", 0) > 0.4:
                detected_category = ml_crime["crime_category"]
                logger.info(
                    f"ML crime classifier: {detected_category} "
                    f"({ml_crime['confidence']:.0%})"
                )
        except Exception:
            pass

        subcategory = "Suspected Fabricated Evidence" if has_chatbot_evidence else "General"
        summary_prefix = (
            "[AI CHATBOT EVIDENCE DETECTED] Risk capped at MEDIUM — ChatGPT/AI output "
            "is not genuine cybercrime evidence. Officer should verify authenticity. "
        ) if has_chatbot_evidence else ""

        return TriageResult(
            risk_level=risk_level,
            risk_score=risk_score,
            crime_category=detected_category,
            crime_subcategory=subcategory,
            ai_summary=f"{summary_prefix}Automated rule-based triage: {risk_level} risk {detected_category} incident. Manual review recommended.",
            entities={"victim": None, "suspect": None, "financial_amount": None},
            bns_sections=BNS_SECTIONS.get(detected_category, BNS_SECTIONS["Other Cybercrime"]),
        )
