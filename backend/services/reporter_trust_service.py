"""
AutoJustice AI NEXUS - Reporter Trust & Reputation Scoring Service
Tracks reporter submission history to detect serial false-reporters and
reward genuine reporters with a higher trust multiplier.

Trust Score = weighted combination of:
  - Historical accuracy (genuine vs fake ratio)
  - Submission frequency (spam patterns)
  - Report quality (detail level, FIR generated)
  - Account age / first-time reporter penalty
"""
import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from models.db_models import ReporterProfile, Report

logger = logging.getLogger(__name__)


class ReporterTrustService:
    """
    Computes and updates reporter trust scores based on submission history.
    Integrates with fake detection to adjust the authenticity threshold.
    """

    def get_or_create_profile(
        self,
        db: Session,
        phone: Optional[str],
        email: Optional[str],
    ) -> Optional[ReporterProfile]:
        """
        Retrieve existing reporter profile or create a new one.
        Identifies reporter by phone (primary) or email (secondary).
        Returns None if neither phone nor email is provided.
        """
        if not phone and not email:
            return None

        profile = None

        # ── Try phone first ────────────────────────────────────────────
        if phone:
            clean_phone = self._clean_phone(phone)
            profile = db.query(ReporterProfile).filter(
                ReporterProfile.phone == clean_phone
            ).first()

        # ── Try email if phone didn't match ────────────────────────────
        if not profile and email:
            clean_email = email.strip().lower()
            profile = db.query(ReporterProfile).filter(
                ReporterProfile.email == clean_email
            ).first()

        # ── Create new profile if not found ───────────────────────────
        if not profile:
            profile = ReporterProfile(
                phone=self._clean_phone(phone) if phone else None,
                email=email.strip().lower() if email else None,
                trust_score=0.70,  # Default for new reporters
                total_submissions=0,
            )
            db.add(profile)
            db.flush()
            logger.info(f"New reporter profile created: phone={phone}, email={email}")

        return profile

    def get_trust_score(self, profile: Optional[ReporterProfile]) -> float:
        """
        Return current trust score for a reporter.
        New reporters get a neutral 0.70 score.
        Blocked reporters return 0.0.
        """
        if not profile:
            return 0.70  # Unknown reporter — neutral trust
        if profile.is_blocked:
            return 0.0
        return profile.trust_score

    def record_submission(
        self,
        db: Session,
        profile: Optional[ReporterProfile],
        report_id: str,
    ) -> None:
        """
        Record a new submission for this reporter.
        Increments submission counter and updates last_seen.
        """
        if not profile:
            return

        profile.total_submissions = (profile.total_submissions or 0) + 1
        profile.last_seen = datetime.utcnow()
        # Link report to profile (done in reports router via FK)
        db.flush()

    def update_after_analysis(
        self,
        db: Session,
        profile: Optional[ReporterProfile],
        is_genuine: bool,
        risk_level: str,
        fir_generated: bool,
    ) -> float:
        """
        Update trust score based on the AI analysis result for the latest submission.
        Called after triage and fake detection are complete.
        Returns the updated trust score.
        """
        if not profile:
            return 0.70

        if is_genuine:
            profile.genuine_count = (profile.genuine_count or 0) + 1
        else:
            profile.fake_flagged_count = (profile.fake_flagged_count or 0) + 1

        if risk_level == "HIGH":
            profile.high_risk_count = (profile.high_risk_count or 0) + 1

        if fir_generated:
            profile.fir_generated_count = (profile.fir_generated_count or 0) + 1

        # Recalculate trust score
        new_score = self._compute_trust_score(profile)
        profile.trust_score = new_score

        # Auto-block persistent fake reporters (>3 fake reports, < 20% genuine rate)
        from config import settings
        total = profile.total_submissions or 1
        fake_rate = (profile.fake_flagged_count or 0) / total
        if (profile.fake_flagged_count or 0) >= 5 and fake_rate > 0.60:
            profile.is_blocked = True
            profile.block_reason = (
                f"Auto-blocked: {profile.fake_flagged_count} fake reports out of "
                f"{total} total submissions ({fake_rate:.0%} fake rate)"
            )
            logger.warning(
                f"Reporter {profile.id} auto-blocked: "
                f"{profile.fake_flagged_count}/{total} fake submissions"
            )

        db.flush()
        return new_score

    def apply_trust_modifier(
        self,
        authenticity_score: float,
        trust_score: float,
    ) -> float:
        """
        Combine fake-detection authenticity score with reporter trust score.
        Trusted reporters get a slight boost; untrusted reporters get penalized.

        Formula:
          - Trust > 0.85: +8% boost
          - Trust 0.65–0.85: neutral
          - Trust 0.40–0.65: -10% penalty
          - Trust < 0.40: -20% penalty
          - Trust = 0 (blocked): cap at 0.10
        """
        if trust_score == 0.0:
            return min(authenticity_score, 0.10)  # Blocked reporter

        if trust_score >= 0.85:
            modifier = 1.08
        elif trust_score >= 0.65:
            modifier = 1.00
        elif trust_score >= 0.40:
            modifier = 0.90
        else:
            modifier = 0.80

        adjusted = authenticity_score * modifier
        return round(min(max(adjusted, 0.0), 1.0), 3)

    def check_submission_frequency(
        self,
        db: Session,
        profile: Optional[ReporterProfile],
    ) -> tuple[bool, str]:
        """
        Check if the reporter is submitting too frequently (rate abuse).
        Returns (is_suspicious, reason).
        """
        if not profile:
            return False, ""

        # Count submissions in last 24 hours
        cutoff = datetime.utcnow() - timedelta(hours=24)
        recent_count = db.query(Report).filter(
            Report.reporter_profile_id == profile.id,
            Report.created_at >= cutoff,
        ).count()

        if recent_count >= 10:
            return True, f"Excessive submissions: {recent_count} in last 24 hours"

        # Count in last hour
        cutoff_1h = datetime.utcnow() - timedelta(hours=1)
        hour_count = db.query(Report).filter(
            Report.reporter_profile_id == profile.id,
            Report.created_at >= cutoff_1h,
        ).count()

        if hour_count >= 4:
            return True, f"Rapid submissions: {hour_count} in last hour"

        return False, ""

    # ─── Private Helpers ─────────────────────────────────────────────────────

    def _compute_trust_score(self, profile: ReporterProfile) -> float:
        """
        Compute a new trust score from scratch based on profile history.

        Components:
          1. Accuracy ratio (genuine / total submissions)  — 50% weight
          2. FIR generation ratio (firs / genuine)         — 25% weight
          3. HIGH risk ratio (serious cases)               — 15% weight
          4. Longevity bonus (>5 genuine reports)          — 10% weight
        """
        from config import settings

        total = max(profile.total_submissions or 0, 1)
        genuine = profile.genuine_count or 0
        fake = profile.fake_flagged_count or 0
        firs = profile.fir_generated_count or 0
        high_risk = profile.high_risk_count or 0

        # Component 1: Accuracy (how many submissions were genuine)
        accuracy = genuine / total
        accuracy_score = accuracy  # 0-1

        # Component 2: FIR quality (of genuine reports, how many were serious enough for FIR)
        fir_quality = firs / max(genuine, 1)
        fir_score = min(fir_quality * 1.5, 1.0)  # Cap at 1.0, slight boost

        # Component 3: Serious cases ratio
        serious_ratio = high_risk / total
        serious_score = min(serious_ratio * 2, 1.0)  # Cap at 1.0

        # Component 4: Longevity bonus (reward reporters with history)
        if genuine >= 10:
            longevity_score = 1.0
        elif genuine >= 5:
            longevity_score = 0.75
        elif genuine >= 3:
            longevity_score = 0.50
        else:
            longevity_score = 0.25  # New/unproven reporter

        # Weighted combination
        trust = (
            accuracy_score * 0.50 +
            fir_score * 0.25 +
            serious_score * 0.15 +
            longevity_score * 0.10
        )

        # Hard penalty for high fake count
        if fake >= 3:
            penalty = min((fake - 2) * 0.10, 0.40)
            trust = max(trust - penalty, 0.05)

        return round(min(max(trust, 0.0), 1.0), 3)

    @staticmethod
    def _clean_phone(phone: Optional[str]) -> Optional[str]:
        """Normalize phone number to digits-only for consistent lookup."""
        if not phone:
            return None
        digits = "".join(c for c in phone if c.isdigit())
        if len(digits) == 12 and digits.startswith("91"):
            digits = digits[2:]  # Strip country code
        return digits if len(digits) >= 10 else phone.strip()
