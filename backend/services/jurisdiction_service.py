"""
AutoJustice AI NEXUS — Phase 2: Jurisdiction Detection & Inter-State Case Forwarding
Detects the correct police jurisdiction from the incident location + description,
and supports forwarding cases outside the host station's jurisdiction to the
appropriate state cyber cell.

Strategy:
  1. Parse `incident_location` and `incident_description` for state / UT / major city names.
  2. Compare detected state with the host station's configured `station_state`.
  3. If different, flag for forwarding. Officer confirms before record is marked forwarded.

Gracefully falls back to the host station when no location is detected.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Optional

from config import settings

logger = logging.getLogger(__name__)


# ─── Indian States + UTs with major cities / districts ───────────────────────
# Ordering matters — longer/more specific names first so we match them before
# the short state name.
STATE_DATA = {
    "Andhra Pradesh":    ["andhra pradesh", "visakhapatnam", "vijayawada", "guntur", "tirupati", "nellore", "kurnool"],
    "Arunachal Pradesh": ["arunachal pradesh", "itanagar", "naharlagun", "pasighat"],
    "Assam":             ["assam", "guwahati", "dibrugarh", "silchar", "jorhat", "tezpur"],
    "Bihar":             ["bihar", "patna", "gaya", "bhagalpur", "muzaffarpur", "darbhanga"],
    "Chhattisgarh":      ["chhattisgarh", "raipur", "bhilai", "bilaspur", "korba", "durg"],
    "Goa":               ["goa", "panaji", "panjim", "margao", "vasco"],
    "Gujarat":           ["gujarat", "ahmedabad", "surat", "vadodara", "rajkot", "gandhinagar", "bhavnagar", "jamnagar"],
    "Haryana":           ["haryana", "gurugram", "gurgaon", "faridabad", "panipat", "ambala", "hisar", "rohtak", "karnal"],
    "Himachal Pradesh":  ["himachal pradesh", "shimla", "dharamshala", "manali", "solan", "mandi"],
    "Jharkhand":         ["jharkhand", "ranchi", "jamshedpur", "dhanbad", "bokaro"],
    "Karnataka":         ["karnataka", "bengaluru", "bangalore", "mysuru", "mysore", "hubballi", "mangaluru", "mangalore", "belagavi", "kalaburagi"],
    "Kerala":            ["kerala", "thiruvananthapuram", "kochi", "cochin", "kozhikode", "calicut", "thrissur", "kollam", "malappuram"],
    "Madhya Pradesh":    ["madhya pradesh", "bhopal", "indore", "jabalpur", "gwalior", "ujjain", "sagar"],
    "Maharashtra":       ["maharashtra", "mumbai", "pune", "nagpur", "thane", "nashik", "aurangabad", "solapur", "navi mumbai", "kolhapur"],
    "Manipur":           ["manipur", "imphal"],
    "Meghalaya":         ["meghalaya", "shillong", "tura"],
    "Mizoram":           ["mizoram", "aizawl"],
    "Nagaland":          ["nagaland", "kohima", "dimapur"],
    "Odisha":            ["odisha", "orissa", "bhubaneswar", "cuttack", "rourkela", "puri", "sambalpur"],
    "Punjab":            ["punjab", "ludhiana", "amritsar", "jalandhar", "patiala", "bathinda", "mohali"],
    "Rajasthan":         ["rajasthan", "jaipur", "jodhpur", "udaipur", "kota", "ajmer", "bikaner"],
    "Sikkim":            ["sikkim", "gangtok"],
    "Tamil Nadu":        ["tamil nadu", "tamilnadu", "chennai", "coimbatore", "madurai", "tiruchirappalli", "trichy", "salem", "tirunelveli", "erode"],
    "Telangana":         ["telangana", "hyderabad", "secunderabad", "warangal", "nizamabad", "karimnagar"],
    "Tripura":           ["tripura", "agartala"],
    "Uttar Pradesh":     ["uttar pradesh", "lucknow", "kanpur", "varanasi", "agra", "prayagraj", "allahabad", "ghaziabad", "noida", "meerut", "gorakhpur"],
    "Uttarakhand":       ["uttarakhand", "dehradun", "haridwar", "rishikesh", "nainital", "haldwani"],
    "West Bengal":       ["west bengal", "kolkata", "calcutta", "howrah", "durgapur", "asansol", "siliguri"],
    # Union Territories
    "Delhi":             ["delhi", "new delhi", "ncr"],
    "Jammu and Kashmir": ["jammu and kashmir", "jammu", "srinagar", "j&k"],
    "Ladakh":            ["ladakh", "leh", "kargil"],
    "Chandigarh":        ["chandigarh"],
    "Puducherry":        ["puducherry", "pondicherry", "karaikal"],
    "Andaman and Nicobar Islands": ["andaman", "nicobar", "port blair"],
    "Dadra and Nagar Haveli and Daman and Diu": ["dadra", "nagar haveli", "daman", "diu", "silvassa"],
    "Lakshadweep":       ["lakshadweep", "kavaratti"],
}

# Each state's designated cyber crime cell contact (used for forwarding letter)
STATE_CYBER_CELL = {
    state: f"{state} State Cyber Crime Cell"
    for state in STATE_DATA
}


@dataclass
class JurisdictionResult:
    detected_state: Optional[str]
    detected_district: Optional[str]
    jurisdiction_name: Optional[str]
    confidence: float
    requires_forwarding: bool
    reason: str
    matched_keywords: list


class JurisdictionService:
    """Detects state-level jurisdiction from free-text location + description."""

    def __init__(self) -> None:
        # Pre-compile regex — word boundary per keyword, case-insensitive
        self._patterns = {}
        for state, keywords in STATE_DATA.items():
            # Longest keyword first so "new delhi" matches before "delhi"
            sorted_kw = sorted(keywords, key=len, reverse=True)
            escaped = [re.escape(k) for k in sorted_kw]
            self._patterns[state] = re.compile(
                r"\b(" + "|".join(escaped) + r")\b", re.IGNORECASE
            )

    def detect(
        self,
        incident_location: Optional[str],
        incident_description: Optional[str] = None,
        complainant_address: Optional[str] = None,
    ) -> JurisdictionResult:
        """
        Run detection. Location is weighted highest; description/address are
        fallback signals.
        """
        # Assemble search corpus — location first (3x weight), then address,
        # then description (1x weight).
        corpus_parts = []
        if incident_location:
            corpus_parts.append((incident_location * 3, 3.0))    # weight marker
        if complainant_address:
            corpus_parts.append((complainant_address, 2.0))
        if incident_description:
            corpus_parts.append((incident_description, 1.0))

        if not corpus_parts:
            return JurisdictionResult(
                detected_state=None, detected_district=None,
                jurisdiction_name=None, confidence=0.0,
                requires_forwarding=False,
                reason="No location or description provided.",
                matched_keywords=[],
            )

        # Count weighted hits per state
        scores: dict[str, float] = {}
        matched: dict[str, list] = {}
        for text, weight in corpus_parts:
            for state, pat in self._patterns.items():
                hits = pat.findall(text)
                if hits:
                    scores[state] = scores.get(state, 0.0) + weight * len(hits)
                    matched.setdefault(state, []).extend([h.lower() for h in hits])

        if not scores:
            # No match — assume host jurisdiction
            return JurisdictionResult(
                detected_state=settings.station_state,
                detected_district=settings.station_district,
                jurisdiction_name=settings.station_name,
                confidence=0.20,
                requires_forwarding=False,
                reason="No state keyword matched — defaulting to host station jurisdiction.",
                matched_keywords=[],
            )

        # Winner is highest score; confidence based on score spread
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top_state, top_score = ranked[0]
        second_score = ranked[1][1] if len(ranked) > 1 else 0.0

        # Confidence: dominant signal = high; competing signals = lower
        denom = top_score + second_score + 0.001
        confidence = min(1.0, 0.55 + (top_score - second_score) / denom * 0.45)
        confidence = round(confidence, 3)

        # Find most specific matched keyword as the "district" hint
        kws = sorted(set(matched.get(top_state, [])), key=len, reverse=True)
        district_hint = kws[0].title() if kws else None

        host_state = (settings.station_state or "").strip().lower()
        requires_forwarding = bool(
            top_state.lower() != host_state
            and confidence >= 0.55
        )

        jurisdiction_name = (
            STATE_CYBER_CELL.get(top_state) if requires_forwarding
            else settings.station_name
        )

        reason = (
            f"Detected state '{top_state}' (score={top_score:.1f}, "
            f"keywords={kws[:3]}). "
            + (
                f"Outside host jurisdiction '{settings.station_state}' — forwarding recommended."
                if requires_forwarding
                else "Within host jurisdiction."
            )
        )

        return JurisdictionResult(
            detected_state=top_state,
            detected_district=district_hint,
            jurisdiction_name=jurisdiction_name,
            confidence=confidence,
            requires_forwarding=requires_forwarding,
            reason=reason,
            matched_keywords=kws[:10],
        )


# Module-level singleton
jurisdiction_service = JurisdictionService()
