"""
AutoJustice AI NEXUS — Feature Extraction for ML Models
Extracts 18 numerical features from report text for the fake detection model.
"""
import re
import math
from typing import List

# ─── Feature name registry (order must match extract_features output) ─────────
FEATURE_NAMES = [
    "word_count",
    "unique_word_ratio",
    "trigger_word_count",
    "has_financial_amount",
    "has_phone_number",
    "has_date",
    "has_proper_name",
    "template_match_count",
    "avg_word_length",
    "sentence_count",
    "specificity_score",
    "capital_letter_ratio",
    "numeric_ratio",
    "has_url",
    "has_email",
    "exclamation_count",
    "question_mark_count",
    "financial_claim_without_amount",
]

# ─── Constants (shared with fake_detection_service.py) ────────────────────────
TRIGGER_WORDS = [
    "bomb", "terrorist", "kill", "murder", "rape", "hack", "blackmail",
    "extort", "ransom", "nude", "child abuse", "drugs", "weapon", "illegal",
    "threat", "sextortion", "suicide", "kidnap",
]

FAKE_TEMPLATE_PATTERNS = [
    r"i am writing to report",
    r"this is to inform you that",
    r"kindly take action against",
    r"i want to file a complaint against unknown person",
    r"please help me",
    r"xyz person",
    r"abc mobile",
    r"\[victim name\]",
    r"\[suspect name\]",
    r"insert name here",
]

FINANCIAL_KEYWORDS = [
    "transfer", "debit", "otp", "account", "bank", "payment", "upi",
    "money", "amount", "credited", "debited", "fraud", "wallet",
    "neft", "rtgs", "imps",
]

# ─── Compiled regex patterns ──────────────────────────────────────────────────
_RE_FINANCIAL_AMOUNT = re.compile(r'\bRs\.?\s*\d+|\bINR\s*\d+|₹\s*\d+', re.IGNORECASE)
_RE_PHONE           = re.compile(r'\b\d{10}\b')
_RE_DATE            = re.compile(
    r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b'
    r'|\b(?:january|february|march|april|may|june|july|august'
    r'|september|october|november|december)\b',
    re.IGNORECASE,
)
_RE_PROPER_NAME     = re.compile(r'\b[A-Z][a-z]+ [A-Z][a-z]+\b')
_RE_URL             = re.compile(
    r'https?://\S+|www\.\S+|\S+\.com\b|\S+\.in\b|\S+\.org\b',
    re.IGNORECASE,
)
_RE_EMAIL           = re.compile(r'\b[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}\b')


def extract_features(description: str, evidence_text: str = "") -> List[float]:
    """
    Extract 18 numerical features from a complaint description and optional
    evidence text.  All features are normalised to [0.0, 1.0].

    Parameters
    ----------
    description  : The raw complaint text entered by the citizen.
    evidence_text: OCR text extracted from uploaded evidence files (optional).

    Returns
    -------
    List of 18 floats in the same order as FEATURE_NAMES.
    """
    combined = (description + " " + evidence_text).lower()
    words_combined = combined.split()
    words_desc     = description.split()

    n_words = len(words_combined)
    n_words_desc = len(words_desc)

    # Guard against empty input
    if n_words == 0:
        return [0.0] * len(FEATURE_NAMES)

    # ── 1. word_count ─────────────────────────────────────────────────────────
    word_count = min(math.log(n_words + 1) / math.log(500), 1.0)

    # ── 2. unique_word_ratio ──────────────────────────────────────────────────
    unique_word_ratio = len(set(words_combined)) / n_words

    # ── 3. trigger_word_count ─────────────────────────────────────────────────
    found_triggers = sum(1 for tw in TRIGGER_WORDS if tw in combined)
    trigger_word_count = min(found_triggers / 5.0, 1.0)

    # ── 4. has_financial_amount ───────────────────────────────────────────────
    has_financial_amount = 1.0 if _RE_FINANCIAL_AMOUNT.search(combined) else 0.0

    # ── 5. has_phone_number ───────────────────────────────────────────────────
    has_phone_number = 1.0 if _RE_PHONE.search(combined) else 0.0

    # ── 6. has_date ───────────────────────────────────────────────────────────
    has_date = 1.0 if _RE_DATE.search(combined) else 0.0

    # ── 7. has_proper_name ────────────────────────────────────────────────────
    # Intentionally check original description (case-sensitive) for proper names
    has_proper_name = 1.0 if _RE_PROPER_NAME.search(description) else 0.0

    # ── 8. template_match_count ───────────────────────────────────────────────
    matched_templates = sum(
        1 for p in FAKE_TEMPLATE_PATTERNS if re.search(p, combined)
    )
    template_match_count = min(matched_templates / 3.0, 1.0)

    # ── 9. avg_word_length ────────────────────────────────────────────────────
    avg_len = sum(len(w) for w in words_combined) / n_words if n_words else 0
    avg_word_length = min(avg_len / 10.0, 1.0)

    # ── 10. sentence_count ────────────────────────────────────────────────────
    sentences = re.split(r'[.!?]+', combined)
    n_sentences = sum(1 for s in sentences if s.strip())
    sentence_count = min(n_sentences / 20.0, 1.0)

    # ── 11. specificity_score ─────────────────────────────────────────────────
    specificity_score = (
        has_financial_amount + has_phone_number + has_date + has_proper_name
    ) / 4.0

    # ── 12. capital_letter_ratio ──────────────────────────────────────────────
    # Ratio of words in original description starting with a capital letter
    if n_words_desc > 0:
        cap_words = sum(1 for w in words_desc if w and w[0].isupper())
        capital_letter_ratio = cap_words / n_words_desc
    else:
        capital_letter_ratio = 0.0

    # ── 13. numeric_ratio ─────────────────────────────────────────────────────
    numeric_words = sum(1 for w in words_combined if re.search(r'\d', w))
    numeric_ratio = numeric_words / n_words

    # ── 14. has_url ───────────────────────────────────────────────────────────
    has_url = 1.0 if _RE_URL.search(combined) else 0.0

    # ── 15. has_email ─────────────────────────────────────────────────────────
    has_email = 1.0 if _RE_EMAIL.search(combined) else 0.0

    # ── 16. exclamation_count ─────────────────────────────────────────────────
    exclamation_count = min(combined.count('!') / 5.0, 1.0)

    # ── 17. question_mark_count ───────────────────────────────────────────────
    question_mark_count = min(combined.count('?') / 3.0, 1.0)

    # ── 18. financial_claim_without_amount ────────────────────────────────────
    has_financial_keyword = any(kw in combined for kw in FINANCIAL_KEYWORDS)
    financial_claim_without_amount = (
        1.0 if (has_financial_keyword and has_financial_amount == 0.0) else 0.0
    )

    return [
        word_count,
        unique_word_ratio,
        trigger_word_count,
        has_financial_amount,
        has_phone_number,
        has_date,
        has_proper_name,
        template_match_count,
        avg_word_length,
        sentence_count,
        specificity_score,
        capital_letter_ratio,
        numeric_ratio,
        has_url,
        has_email,
        exclamation_count,
        question_mark_count,
        financial_claim_without_amount,
    ]
