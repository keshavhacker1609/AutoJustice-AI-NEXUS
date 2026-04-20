"""
AutoJustice AI NEXUS - Multi-Layer Fake Report Detection Engine
Prevents gaming of the AI system through keyword stuffing, fabricated narratives,
copy-paste templates, and other deceptive submission patterns.

Detection Layers:
  L1: Trigger word density analysis (keyword stuffing detection)
  L2: Gemini narrative coherence + authenticity verification
  L3: Evidence ↔ description correlation scoring
  L4: Entity consistency validation
  L5: Duplicate fingerprint detection (in-session)
  L6: Behavioral anomaly scoring (submission patterns)
"""
import json
import re
import logging
from typing import Optional
from models.schemas import FakeDetectionResult

logger = logging.getLogger(__name__)

try:
    from google import genai
    from google.genai import types as genai_types
    from config import settings
    GEMINI_AVAILABLE = bool(settings.gemini_api_key)
except Exception:
    GEMINI_AVAILABLE = False

# ─── Known fake report template patterns ─────────────────────────────────────
# IMPORTANT: only include patterns that NEVER appear in real victim reports.
# "please help me" was removed — genuine distressed victims write this constantly.
# "kindly take action against" was removed — standard in Indian formal letters.
FAKE_TEMPLATE_PATTERNS = [
    r"i am writing to report",                        # Bureaucratic opener, not natural speech
    r"this is to inform you that",                    # Formal template preamble
    r"i want to file a complaint against unknown person",  # Suspiciously vague stock phrase
    r"xyz person",                                    # Placeholder not replaced
    r"abc mobile",                                    # Placeholder not replaced
    r"\[victim name\]",                               # Unfilled template field
    r"\[suspect name\]",                              # Unfilled template field
    r"insert name here",                              # Unfilled template field
    r"describe the incident here",                    # Unfilled template field
]

# ─── Amount regex — matches Indian currency in any common written form ────────
# Covers: "Rs. 45,000" / "Rs 45000" / "INR 45,000" / "₹45000" / "45,000 rs"
# / "45000 rupees" / "45,000/-"
_RE_AMOUNT = re.compile(
    r'\bRs\.?\s*[\d,]+|\bINR\s*[\d,]+|₹\s*[\d,]+'
    r'|[\d,]+\s*(?:rs|rupees|/-)\b'
    r'|[\d,]+\s*rs\b',
    re.IGNORECASE,
)

# High-risk trigger words that can be artificially inserted to inflate risk
TRIGGER_WORDS = [
    "bomb", "terrorist", "kill", "murder", "rape", "hack", "blackmail",
    "extort", "ransom", "nude", "child abuse", "drugs", "weapon", "illegal",
    "threat", "sextortion", "suicide", "kidnap",
]

FAKE_DETECTION_PROMPT = """
You are a senior forensic analyst for the Indian Cyber Crime Police with 15 years of
experience identifying fabricated complaints. Your job is NOT to be helpful to the
complainant — it is to protect the justice system from abuse.

ASSUME THE REPORT MAY BE FAKE. Your task is to find evidence that it is genuine.
A report that simply SOUNDS real is not the same as one that IS real.

CRITICAL PRE-CHECK — AI CHATBOT EVIDENCE:
If the OCR evidence text shows output from ChatGPT, Claude, Gemini, Bard, Bing AI, or any
other AI chatbot interface, apply these rules IMMEDIATELY before all other checks:
- Set evidence_match = 0.05 (AI-generated text is trivially fabricable — anyone can prompt
  an AI to write any threatening or incriminating text)
- Set plausibility = 0.10 (real criminals do not send ChatGPT screenshots as threats)
- Set adversarial_probe = 0.05 (this is a textbook method for gaming risk detection systems)
- Add a flag: "AI chatbot output is not genuine cybercrime evidence"
A screenshot of ChatGPT saying "I will harm you" proves nothing — the submitter typed that prompt.

REPORT TO ANALYZE:
---
Description: {description}

Evidence Text (from uploaded image/document OCR): {evidence_text}
---

Apply ALL of the following adversarial checks:

1. NARRATIVE_COHERENCE (0.0-1.0)
   - Does the timeline hold up? Could all described actions fit in the stated time window?
   - Are the victim's reactions what a real person would do? (Panic, confusion, delayed realisation
     are genuine; perfectly logical step-by-step recall is suspicious.)
   - Does the emotional register match someone who experienced this, or someone who wrote about it?

2. SPECIFICITY (0.0-1.0)
   - Specific details (exact amounts, real phone numbers, named banks, UPI IDs, timestamps) score HIGH.
   - CRITICAL: Anyone can fabricate specific-looking details. Score HIGH only when details feel
     embedded naturally in the narrative, NOT like a keyword list inserted to appear credible.
   - A report with "Rs 45000 via UPI to 9876543210 on 14/04/2026 from HDFC" but no context
     about the actual human interaction is still suspicious despite its specifics.

3. TRIGGER_STUFFING (0.0-1.0)
   - Are dangerous keywords (threat, hack, ransom, nude, bomb) appearing naturally in context?
   - Score LOW if these words feel inserted to inflate AI risk scoring.

4. EVIDENCE_MATCH (0.0-1.0)
   - Does the uploaded OCR evidence DIRECTLY support the described incident?
   - If description says "UPI transfer" but OCR shows no financial data: score = 0.1
   - If no evidence uploaded but description says "I have attached proof": score = 0.2

5. ENTITY_CONSISTENCY (0.0-1.0)
   - Are names, amounts, phone numbers consistent throughout the report?
   - Do mentioned phone numbers look like real 10-digit Indian mobiles?
   - If a UPI ID is mentioned, does it follow real UPI format (name@bank)?
   - Does the suspect's claimed method of contact match the described platform?

6. TEMPLATE_PATTERN (0.0-1.0)
   - Does this read like a unique personal experience or a filled-in template?
   - Watch for: over-formal language from a supposedly distressed victim, perfect recall of every
     procedural detail, descriptions that match "how UPI fraud works" explanations rather than
     a messy personal experience. Real victims often have emotional irregularities and confused ordering.

7. PLAUSIBILITY (0.0-1.0)
   - Could this scenario actually happen in India as described?
   - Example implausibility: "bank called me and simultaneously asked for Aadhaar + OTP + password"
     (real banks never do this).

8. ADVERSARIAL_PROBE (0.0-1.0)
   - Imagine someone who READ about cybercrime complaints and is constructing one.
   - Does this report include all the "right" elements (amount, platform, phone, date, emotional appeal)
     but feel ASSEMBLED rather than RECALLED from memory?
   - Is there any detail only a real victim would know, versus something anyone could research?
   - Does the language shift register between emotional passages and technical detail in a way
     that suggests two different authoring modes (feeling → looking up facts → feeling again)?
   - Score 1.0 = unmistakably a lived experience. Score 0.0 = reads like a researched construction.

Respond ONLY in this exact JSON format (no markdown):
{{
  "scores": {{
    "narrative_coherence": <0.0-1.0>,
    "specificity": <0.0-1.0>,
    "trigger_stuffing": <0.0-1.0>,
    "evidence_match": <0.0-1.0>,
    "entity_consistency": <0.0-1.0>,
    "template_pattern": <0.0-1.0>,
    "plausibility": <0.0-1.0>,
    "adversarial_probe": <0.0-1.0>
  }},
  "flags": ["<specific red flags — be precise, e.g. 'Victim reports sharing OTP immediately without hesitation — atypical panic response'>"],
  "reasoning": "<2-3 sentences: what is the single most suspicious element, and what would a police officer need to verify?>",
  "recommendation": "GENUINE" | "REVIEW" | "REJECT"
}}
"""

# Weights for each detection dimension (must sum to 1.0)
# adversarial_probe added — gets highest weight as it is the direct counter to keyword-gaming
DIMENSION_WEIGHTS = {
    "narrative_coherence": 0.15,
    "specificity":         0.12,
    "trigger_stuffing":    0.12,
    "evidence_match":      0.13,
    "entity_consistency":  0.10,
    "template_pattern":    0.10,
    "plausibility":        0.08,
    "adversarial_probe":   0.20,   # Highest weight — directly counters keyword-gaming
}


class FakeDetectionService:
    """
    Multi-layer authenticity verification engine.
    Combines AI semantic analysis with rule-based statistical checks.
    """

    def __init__(self):
        self.client = None
        if GEMINI_AVAILABLE:
            from config import settings
            try:
                self.client = genai.Client(api_key=settings.gemini_api_key)
                self._model_name = settings.gemini_model
            except Exception as e:
                logger.error(f"Gemini fake detection client init failed: {e}")
                self.client = None

        self._submitted_hashes: set = set()  # Fallback in-memory store (DB preferred via analyze_with_db)

        # ── L7: ML model (optional) ────────────────────────────────────────
        try:
            from ml.predictor import ml_predictor
            self._ml = ml_predictor
            self._ml_available = True
        except Exception:
            try:
                from predictor import ml_predictor  # when running from ml/ dir
                self._ml = ml_predictor
                self._ml_available = True
            except Exception:
                self._ml = None
                self._ml_available = False

    def analyze(
        self,
        description: str,
        evidence_text: str = "",
        content_hash: str = "",
        db=None,
    ) -> FakeDetectionResult:
        """
        Run all detection layers and compute a final authenticity score.
        Returns FakeDetectionResult with recommendation: GENUINE / REVIEW / REJECT
        """
        flags = []
        layer_scores = {}

        # ── L1: Rule-based keyword stuffing detection ─────────────────
        l1_score, l1_flags = self._l1_keyword_density(description, evidence_text)
        layer_scores["rule_based"] = l1_score
        flags.extend(l1_flags)

        # ── L3: Evidence ↔ description mismatch detection ─────────────
        l3_penalty, l3_flags = self._l3_evidence_mismatch(description, evidence_text)
        flags.extend(l3_flags)

        # ── L4: Entity cross-check (phone, UPI, amounts vs evidence) ──
        l4_penalty, l4_flags = self._l4_entity_crosscheck(description, evidence_text)
        flags.extend(l4_flags)

        # ── L5: Duplicate fingerprint check ───────────────────────────
        l5_score, l5_flags = self._l5_duplicate_check(content_hash, db=db)
        flags.extend(l5_flags)

        # ── L7: ML model prediction ────────────────────────────────────
        ml_result = {}
        if self._ml_available:
            try:
                ml_result = self._l7_ml_check(description, evidence_text)
            except Exception as e:
                logger.warning(f"ML prediction failed: {e}")

        # ── L2: Gemini authenticity analysis ──────────────────────────
        ai_scores = {}
        ai_flags = []
        ai_reasoning = ""
        ai_recommendation = "REVIEW"

        if self.client and GEMINI_AVAILABLE:
            try:
                ai_result = self._l2_gemini_check(description, evidence_text)
                ai_scores = ai_result.get("scores", {})
                ai_flags = ai_result.get("flags", [])
                ai_reasoning = ai_result.get("reasoning", "")
                ai_recommendation = ai_result.get("recommendation", "REVIEW")
                flags.extend(ai_flags)
            except Exception as e:
                logger.error(f"Gemini fake detection failed: {e}")
                ai_scores = {k: 0.6 for k in DIMENSION_WEIGHTS}  # Neutral fallback

        else:
            # Fallback rule-based scoring for all dimensions
            ai_scores = self._fallback_scores(description, evidence_text)
            if not flags:
                ai_recommendation = "REVIEW"

        # ── Weighted composite score ───────────────────────────────────
        ai_composite = sum(
            ai_scores.get(dim, 0.5) * weight
            for dim, weight in DIMENSION_WEIGHTS.items()
        )

        # Blend rule-based + AI + ML scores.
        # When Gemini is unavailable, the fallback ai_composite is already
        # conservative. Reduce the weight of l1_score (rule-based) to prevent
        # a clean-written fake from inflating the final score via the L1 path.
        ml_score_val = ml_result.get("ml_score", 0.5) if ml_result.get("available") else None

        if GEMINI_AVAILABLE and self.client:
            if ml_score_val is not None:
                # Gemini + ML both available
                final_score = (
                    (ai_composite * 0.50)
                    + (l1_score * 0.25)
                    + (ml_score_val * 0.25)
                )
            else:
                # Gemini only
                final_score = (ai_composite * 0.60) + (l1_score * 0.40)
        else:
            if ml_score_val is not None:
                # ML available but Gemini not
                final_score = (
                    (ai_composite * 0.45)
                    + (l1_score * 0.20)
                    + (ml_score_val * 0.35)
                )
            else:
                # Neither Gemini nor ML — rule-based only
                # 80% conservative AI composite, 20% rule-based — reduces l1 inflation
                final_score = (ai_composite * 0.80) + (l1_score * 0.20)

        # L3: Evidence-description mismatch hard penalty
        final_score = max(0.0, final_score - l3_penalty)

        # L4: Entity cross-check penalty
        final_score = max(0.0, final_score - l4_penalty)

        # Duplicate submission is a hard penalty
        if l5_score < 0.5:
            final_score = min(final_score, 0.30)
            ai_recommendation = "REJECT"

        # Determine recommendation from score if AI not available.
        # Rule-based mode can never confirm GENUINE — best it can say is REVIEW.
        if not GEMINI_AVAILABLE:
            if final_score >= 0.45:
                ai_recommendation = "REVIEW"   # Human officer must verify manually
            else:
                ai_recommendation = "REJECT"

        from config import settings
        is_suspicious = final_score < settings.fake_report_threshold

        return FakeDetectionResult(
            authenticity_score=round(final_score, 3),
            is_suspicious=is_suspicious,
            flags=list(set(flags)),  # Deduplicate flags
            recommendation=ai_recommendation,
            details={
                "rule_based_score": round(l1_score, 3),
                "ai_composite_score": round(ai_composite, 3),
                "ai_dimension_scores": ai_scores,
                "ai_reasoning": ai_reasoning,
                "duplicate_detected": l5_score < 0.5,
                "ml_result": ml_result,
            }
        )

    def _l1_keyword_density(self, description: str, evidence_text: str) -> tuple[float, list]:
        """
        Layer 1: Statistical keyword analysis.
        Detects: trigger word stuffing, template patterns, implausible word ratios.
        """
        flags = []
        score = 1.0  # Start with full trust, deduct for anomalies
        combined = (description + " " + evidence_text).lower()
        word_count = len(combined.split())

        if word_count < 5:
            return 0.2, ["Report is too short to be credible (less than 5 words)"]

        # ── Check 1: Trigger word density ────────────────────────────
        found_triggers = [w for w in TRIGGER_WORDS if w in combined]
        trigger_density = len(found_triggers) / max(word_count / 50, 1)

        if trigger_density > 2.0:
            score -= 0.40
            flags.append(f"High-risk keyword stuffing detected: {found_triggers[:5]}")
        elif trigger_density > 1.0:
            score -= 0.22
            flags.append(f"Elevated trigger word density: {found_triggers[:3]}")
        elif len(found_triggers) >= 3:
            # Even low density with 3+ distinct trigger words is suspicious
            score -= 0.12
            flags.append(f"Multiple high-risk trigger words present: {found_triggers[:3]}")

        # ── Check 2: Template pattern matching ────────────────────────
        template_matches = [p for p in FAKE_TEMPLATE_PATTERNS if re.search(p, combined)]
        if len(template_matches) >= 2:
            score -= 0.25
            flags.append("Report matches multiple generic template patterns — possible copy-paste")
        elif len(template_matches) == 1:
            # A single soft pattern is only flagged when the report is also very short/vague
            if word_count < 40:
                score -= 0.10
                flags.append("Possible template language detected (short report)")

        # ── Check 3: Specificity ratio (proper nouns, numbers, dates) ─
        specifics = re.findall(r'\b[A-Z][a-z]+\b|\b\d{10}\b|\b\d{1,3}[,\d]*\b|\bINR\b|\bRs\.?\b', description)
        specificity_ratio = len(specifics) / max(word_count / 20, 1)
        if specificity_ratio < 0.3 and word_count > 50:
            score -= 0.15
            flags.append("Report lacks specific details (names, amounts, dates, phone numbers)")

        # ── Check 4: Excessive repetition ─────────────────────────────
        words = combined.split()
        unique_ratio = len(set(words)) / len(words) if words else 1
        if unique_ratio < 0.4:
            score -= 0.20
            flags.append("Abnormally high word repetition detected (copy-paste pattern)")

        # ── Check 5: Lack of any verifiable specific detail ──────────────
        # Any report > 20 words should have at least ONE concrete verifiable
        # element. Vague complaints without names, amounts, phones, or dates
        # are the hallmark of fabricated reports — regardless of length.
        if word_count > 20:
            # Amount: accepts "Rs. 45,000", "45,000 rs", "45000 rupees", "₹45000"
            has_amount   = bool(_RE_AMOUNT.search(combined))
            has_phone    = bool(re.search(r'\b\d{10}\b', combined))
            has_date     = bool(re.search(
                r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b'
                r'|\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{4}\b'
                r'|\b\d{4}\b',   # year alone counts (e.g. "10 april 2026")
                combined, re.IGNORECASE,
            ))
            has_propname = bool(re.search(r'\b[A-Z][a-z]+ [A-Z][a-z]+\b', description))
            # Named bank / payment platform is a strong specificity signal
            has_platform = bool(re.search(
                r'\b(?:hdfc|sbi|icici|axis|pnb|kotak|yes bank|canara|bob|union bank'
                r'|paytm|phonepe|phone\s?pe|gpay|google\s?pay|bhim|upi|neft|rtgs|imps'
                r'|whatsapp|telegram|instagram|facebook|twitter)\b',
                combined, re.IGNORECASE,
            ))

            specificity_count = sum([has_amount, has_phone, has_date, has_propname, has_platform])
            has_any_specific = specificity_count >= 1

            if not has_any_specific:
                score -= 0.25
                flags.append("Report lacks any verifiable specific detail (name, amount, phone, date, platform)")
            elif word_count > 50 and specificity_count < 2:
                score -= 0.10
                flags.append("Report has limited verifiable details for its length")

        return max(0.0, min(score, 1.0)), flags

    def _l2_gemini_check(self, description: str, evidence_text: str) -> dict:
        """Layer 2: Gemini semantic authenticity analysis."""
        prompt = FAKE_DETECTION_PROMPT.format(
            description=description[:2000],
            evidence_text=evidence_text[:1500] if evidence_text else "No evidence text provided"
        )
        response = self.client.models.generate_content(
            model=self._model_name,
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                temperature=0.05,
                top_p=0.9,
                max_output_tokens=1000,
            ),
        )
        raw = response.text.strip()
        raw = re.sub(r"```(?:json)?", "", raw).strip()
        return json.loads(raw)

    def _l3_evidence_mismatch(self, description: str, evidence_text: str) -> tuple[float, list]:
        """
        Layer 3: Evidence ↔ description correlation.

        Detects when the uploaded image / evidence file contains no readable
        content despite the complaint claiming a financial or cyber incident.
        Classic example: a photo of a chair submitted as "proof" of UPI fraud.

        Returns (penalty: float, flags: list[str]).
        Penalty is capped at 0.40 so a single layer can't fully override AI.
        """
        flags: list = []
        penalty = 0.0
        desc_lower = description.lower()

        FINANCIAL_KEYWORDS = [
            "transfer", "upi", "bank", "account", "otp", "payment",
            "money", "amount", "debit", "fraud", "scam", "transaction",
            "credited", "debited", "wallet", "neft", "rtgs", "imps",
            "paytm", "phonepe", "gpay", "google pay", "loan", "invest",
        ]
        SCREENSHOT_KEYWORDS = [
            "screenshot", "photo", "image", "attached", "evidence",
            "proof", "document", "statement", "record",
        ]

        has_financial_claim = any(kw in desc_lower for kw in FINANCIAL_KEYWORDS)
        has_screenshot_claim = any(kw in desc_lower for kw in SCREENSHOT_KEYWORDS)

        # Normalize evidence_text — None and whitespace-only both count as empty
        ocr_text = (evidence_text or "").strip()
        ocr_length = len(ocr_text)

        # ── Signal 1+2: Explicit attachment claim + no readable text in evidence ──
        # The complainant says they are attaching a screenshot / document / proof
        # AND the uploaded image contains no OCR text → the image is unrelated.
        # Classic example: "I have attached the transaction screenshot" but the
        # uploaded file is a photo of a chair.
        #
        # IMPORTANT: We do NOT penalise reports where no attachment was mentioned.
        # A genuine victim who just typed their experience without uploading anything
        # should not be flagged — absence of an attachment is normal and expected.
        if has_financial_claim and has_screenshot_claim and ocr_length < 20:
            penalty += 0.30
            flags.append(
                "Complainant references attached financial evidence but uploaded "
                "image contains no readable text — image appears unrelated to claim"
            )
        elif has_screenshot_claim and ocr_length < 10:
            # Screenshot specifically referenced but image is completely blank
            penalty += 0.15
            flags.append(
                "Complainant references attached screenshot/document but uploaded "
                "image contains no extractable text"
            )

        # ── Signal 3: Evidence text exists but shares zero keywords with claim ──
        # E.g. description says "UPI transfer" but OCR reads "Dairy Products Invoice".
        # Only check when there IS some OCR text to avoid double-penalising empty images.
        if ocr_length >= 20 and has_financial_claim:
            ocr_lower = ocr_text.lower()
            evidence_relevant = any(kw in ocr_lower for kw in FINANCIAL_KEYWORDS) or bool(
                re.search(r'rs\.?\s*\d+|inr\s*\d+|₹\s*\d+|\d{10,}', ocr_lower)
            )
            if not evidence_relevant:
                penalty += 0.15
                flags.append(
                    "Evidence text does not contain any financial references — "
                    "may be unrelated to the reported cyber-financial crime"
                )

        # ── Signal 4: AI chatbot evidence detection ───────────────────────────
        # A screenshot of ChatGPT / Claude / Gemini / Bing AI is NOT genuine
        # cybercrime evidence. Anyone can prompt an AI to generate any threatening
        # or incriminating text. This is a common method to game risk-scoring systems.
        _AI_CHATBOT_RE = re.compile(
            r'\bchatgpt\b|\bgpt[-\s]?[34o]\b|\bopenai\b|\bclaude\b'
            r'|\bgemini\b|\bbing\s*ai\b|\bai\s*chatbot\b|\bai\s*assistant\b'
            r'|\bcopilot\b|\bperplexity\b|\bmistral\b',
            re.IGNORECASE,
        )
        if _AI_CHATBOT_RE.search(ocr_text):
            penalty += 0.45
            flags.append(
                "AI CHATBOT EVIDENCE: Evidence contains AI chatbot output (ChatGPT/Claude/Gemini). "
                "AI-generated text is trivially fabricable — anyone can prompt an AI to write "
                "threatening content. This is not valid cybercrime evidence."
            )
        elif _AI_CHATBOT_RE.search(description):
            penalty += 0.20
            flags.append(
                "AI CHATBOT REFERENCE: Description mentions an AI chatbot as the source of threat. "
                "AI output is not genuine criminal activity — real criminals use real channels."
            )

        return min(penalty, 0.60), flags

    def _l4_entity_crosscheck(self, description: str, evidence_text: str) -> tuple[float, list]:
        """
        Layer 4: Entity cross-verification.

        Even a well-crafted fake with all the right keywords fails when its
        internal entities are inconsistent or implausible:

          • Phone numbers in description vs. phone numbers in OCR evidence don't match
          • UPI ID format is malformed (fakers often invent fake-looking IDs)
          • Amount in description vs. amount visible in OCR differ significantly
          • Claimed bank name doesn't match UPI suffix (e.g. "SBI account" but UPI is @axisbank)
          • Multiple phone numbers in description that don't all look like real Indian mobiles

        Returns (penalty: float, flags: list[str]).
        """
        flags: list = []
        penalty = 0.0
        desc_lower = description.lower()
        ocr_lower  = (evidence_text or "").lower()

        # ── Check 1: Phone numbers in description vs OCR ─────────────────────
        desc_phones = set(re.findall(r'\b[6-9]\d{9}\b', description))
        ocr_phones  = set(re.findall(r'\b[6-9]\d{9}\b', evidence_text or ""))

        # Invalid Indian mobile numbers (must start with 6-9)
        all_desc_numbers = re.findall(r'\b\d{10}\b', description)
        bad_numbers = [n for n in all_desc_numbers if not re.match(r'^[6-9]', n)]
        if bad_numbers:
            penalty += 0.15
            flags.append(
                f"ENTITY: Phone number(s) {bad_numbers} do not match Indian mobile format "
                f"(must start with 6-9) — possibly fabricated"
            )

        # Numbers in description should appear in OCR if evidence was uploaded
        if desc_phones and ocr_phones and not desc_phones.intersection(ocr_phones):
            penalty += 0.20
            flags.append(
                f"ENTITY: Phone number(s) {desc_phones} mentioned in complaint do not "
                f"appear in uploaded evidence ({ocr_phones}) — numbers may be fabricated"
            )

        # ── Check 2: UPI ID format validation ────────────────────────────────
        upi_ids = re.findall(r'[\w.\-]+@[\w]+', description + " " + (evidence_text or ""))
        VALID_UPI_HANDLES = {
            "okaxis", "okhdfcbank", "okicici", "oksbi", "ybl", "ibl", "axl",
            "paytm", "fbl", "apl", "upi", "icici", "sbi", "hdfc", "axis",
            "kotak", "pnb", "aubank", "indus", "rbl", "idbi", "boi", "cnrb",
            "federal", "unionbank", "allbank", "mahb", "jsb", "dcb",
        }
        for uid in upi_ids:
            if "@" in uid:
                handle = uid.split("@")[1].lower().strip()
                # UPI handles must be letters only, 2-20 chars
                if not re.match(r'^[a-z]{2,20}$', handle):
                    penalty += 0.10
                    flags.append(
                        f"ENTITY: UPI ID '{uid}' has an invalid handle format — "
                        f"real UPI handles are letters only (e.g. fraud@paytm)"
                    )
                    break

        # ── Check 3: Amount consistency between description and OCR ──────────
        desc_amounts = _RE_AMOUNT.findall(desc_lower)
        ocr_amounts  = _RE_AMOUNT.findall(ocr_lower)

        if desc_amounts and ocr_amounts:
            # Extract numeric values for comparison
            def _to_int(s: str) -> int:
                return int(re.sub(r'[^\d]', '', s)) if re.search(r'\d', s) else 0
            desc_vals = [_to_int(a) for a in desc_amounts if _to_int(a) > 0]
            ocr_vals  = [_to_int(a) for a in ocr_amounts  if _to_int(a) > 0]
            if desc_vals and ocr_vals:
                # Check if any description amount matches any OCR amount within 10%
                matched = any(
                    abs(dv - ov) / max(ov, 1) < 0.10
                    for dv in desc_vals for ov in ocr_vals
                )
                if not matched:
                    penalty += 0.20
                    flags.append(
                        f"ENTITY: Amount in complaint ({desc_amounts}) does not match "
                        f"amount in uploaded evidence ({ocr_amounts}) — figures inconsistent"
                    )

        # ── Check 4: Victim's own UPI vs claimed bank inconsistency ─────────────
        # NOTE: We do NOT flag when the FRAUDSTER's receiving UPI is from a different
        # bank — that is completely normal and expected in real fraud cases.
        # (Victim loses from HDFC; fraudster receives on @paytm — this is genuine.)
        #
        # We ONLY flag when the complaint explicitly states the VICTIM's OWN UPI ID
        # but that ID's bank suffix contradicts the claimed account bank.
        # Pattern: "my UPI is victim@okaxis but I bank with SBI"
        victim_upi_patterns = re.findall(
            r'(?:my upi|my upi id|my id|sent from)\s*(?:is\s*)?'
            r'([\w.\-]+@[\w]+)',
            desc_lower
        )
        BANK_UPI_MAP = {
            "sbi":   ["oksbi", "sbi"],
            "hdfc":  ["okhdfcbank", "hdfc"],
            "icici": ["okicici", "icici"],
            "axis":  ["okaxis", "axl", "axis"],
            "kotak": ["kotak"],
        }
        for uid in victim_upi_patterns:
            if "@" in uid:
                upi_handle = uid.split("@")[1].lower()
                for bank, valid_handles in BANK_UPI_MAP.items():
                    if bank in desc_lower and upi_handle not in valid_handles:
                        # Victim claims to bank with X but their own UPI shows bank Y
                        if any(upi_handle in hs for b, hs in BANK_UPI_MAP.items() if b != bank):
                            penalty += 0.15
                            flags.append(
                                f"ENTITY: Victim claims '{bank.upper()}' account but "
                                f"their own UPI ID '{uid}' indicates a different bank"
                            )
                            break

        return min(penalty, 0.40), flags

    def _l5_duplicate_check(self, content_hash: str, db=None) -> tuple[float, list]:
        """Layer 5: Detect duplicate submissions by content hash.
        Uses DB query when db session is provided (multi-worker safe), otherwise in-memory fallback.
        """
        if not content_hash:
            return 1.0, []
        if db is not None:
            try:
                from models.db_models import Report
                existing = db.query(Report).filter(Report.content_hash == content_hash).first()
                if existing:
                    return 0.0, [f"DUPLICATE: This exact report content was already submitted (case {existing.case_number})"]
                return 1.0, []
            except Exception:
                pass
        # In-memory fallback (single-process dev only)
        if content_hash in self._submitted_hashes:
            return 0.0, ["DUPLICATE: This exact report content was already submitted"]
        self._submitted_hashes.add(content_hash)
        return 1.0, []

    def _l7_ml_check(self, description: str, evidence_text: str) -> dict:
        """
        Layer 7: ML model-based authenticity prediction.
        Returns the full dict from MLPredictor.predict_fake().
        """
        return self._ml.predict_fake(description, evidence_text)

    def _fallback_scores(self, description: str, evidence_text: str) -> dict:
        """
        Fallback dimension scores when Gemini is unavailable.
        Intentionally conservative — rule-based analysis cannot reliably distinguish
        a plausible fake from a genuine report. All dimensions start at a low baseline
        to force REVIEW rather than GENUINE when AI is offline.
        """
        combined = (description + " " + evidence_text).lower()
        word_count = len(combined.split())

        has_names    = bool(re.search(r'\b[A-Z][a-z]+ [A-Z][a-z]+\b', description))
        has_phone    = bool(re.search(r'\b\d{10}\b', combined))
        # Amount: covers all Indian currency notations including "45,000 rs" / "45000 rupees"
        has_amount   = bool(_RE_AMOUNT.search(combined))
        has_dates    = bool(re.search(
            r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b'
            r'|\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{4}\b'
            r'|\b\d{4}\b',
            combined, re.IGNORECASE,
        ))
        # Named bank / payment platform counts as a verifiable specific detail
        has_platform = bool(re.search(
            r'\b(?:hdfc|sbi|icici|axis|pnb|kotak|yes bank|canara|bob|union bank'
            r'|paytm|phonepe|phone\s?pe|gpay|google\s?pay|bhim|upi|neft|rtgs|imps'
            r'|whatsapp|telegram|instagram|facebook|twitter)\b',
            combined, re.IGNORECASE,
        ))
        templates = [p for p in FAKE_TEMPLATE_PATTERNS if re.search(p, combined)]
        triggers  = [w for w in TRIGGER_WORDS if w in combined]

        # Financial claim without a specific amount is a strong fake signal
        financial_keywords = ["transfer", "debit", "otp", "account", "bank", "payment",
                               "upi", "money", "amount", "credited", "debited", "fraud"]
        has_financial_claim = any(kw in combined for kw in financial_keywords)
        financial_without_amount = has_financial_claim and not has_amount

        # Specificity: count concrete verifiable markers (5 possible, need ≥1 to avoid flag)
        specificity_markers = sum([has_names, has_phone, has_amount, has_dates, has_platform])
        if financial_without_amount:
            specificity = 0.20   # Claims money lost but gives no amount → suspicious
        elif specificity_markers >= 3:
            specificity = 0.65
        elif specificity_markers >= 2:
            specificity = 0.52
        elif specificity_markers >= 1:
            specificity = 0.42
        else:
            specificity = 0.20

        # AI chatbot in evidence — extremely suspicious
        _AI_CHATBOT_RE = re.compile(
            r'\bchatgpt\b|\bgpt[-\s]?[34o]\b|\bopenai\b|\bclaude\b'
            r'|\bgemini\b|\bbing\s*ai\b|\bai\s*chatbot\b|\bcopilot\b',
            re.IGNORECASE,
        )
        has_chatbot_evidence = bool(_AI_CHATBOT_RE.search(combined))

        # Adversarial probe fallback: triggers + chatbot = almost certainly gamed
        if has_chatbot_evidence:
            adversarial_probe = 0.05
        elif len(triggers) >= 3:
            adversarial_probe = 0.20
        elif len(triggers) >= 2:
            adversarial_probe = 0.35
        elif len(triggers) >= 1:
            adversarial_probe = 0.45
        else:
            adversarial_probe = 0.50

        return {
            # Conservative — narrative logic requires AI to validate
            "narrative_coherence": 0.55 if word_count > 30 else 0.25,
            "specificity": specificity,
            # Lower ceiling: without context, trigger words can't be assessed properly
            "trigger_stuffing": max(0.05, 0.80 - len(triggers) * 0.25),
            # Hard penalty for no-evidence reports — if no file was uploaded, can't verify
            "evidence_match": 0.05 if has_chatbot_evidence else (0.45 if evidence_text.strip() else 0.25),
            # Cannot verify entity consistency without AI
            "entity_consistency": 0.40 if has_chatbot_evidence else 0.50,
            "template_pattern": 0.15 if len(templates) >= 2 else 0.70,
            # Cannot assess plausibility without AI
            "plausibility": 0.10 if has_chatbot_evidence else 0.50,
            # Adversarial probe — now included in fallback
            "adversarial_probe": adversarial_probe,
        }
