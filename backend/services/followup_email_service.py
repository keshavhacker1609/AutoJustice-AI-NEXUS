"""
AutoJustice AI NEXUS — Phase 2: Automated Follow-up Email Service
Sends structured status update emails to complainants after complaint registration.

Email schedule:
  T+0       : Acknowledgement email (sent immediately at submission)
  T+24h     : First follow-up — case status update
  T+72h     : Second follow-up — escalation reminder if still unassigned
  T+7d      : Final follow-up — case closure or progress update

All emails are triggered via BackgroundTasks (non-blocking).
"""
import logging
import smtplib
import time
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

logger = logging.getLogger(__name__)


# ─── Email Builder Helpers ────────────────────────────────────────────────────

def _base_template(subject_line: str, body_html: str) -> str:
    """Wrap body HTML in the AutoJustice branded email shell."""
    return f"""<!DOCTYPE html>
<html><body style="margin:0;padding:0;background:#f0f4f8;font-family:'Segoe UI',Arial,sans-serif">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f4f8;padding:32px 0">
<tr><td align="center">
<table width="560" cellpadding="0" cellspacing="0"
  style="background:#fff;border:1px solid #d1d9e0;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.06)">

  <!-- Header -->
  <tr><td style="background:#1a3f6f;padding:0">
    <table width="100%"><tr>
      <td width="6" style="background:#FF6B00;padding:0"></td>
      <td style="padding:18px 24px">
        <p style="margin:0;color:#fff;font-size:17px;font-weight:700">AutoJustice AI NEXUS</p>
        <p style="margin:4px 0 0;color:rgba(255,255,255,0.65);font-size:11px;
           letter-spacing:.5px;text-transform:uppercase">
          National Cyber Crime Reporting Portal
        </p>
      </td>
      <td style="padding:18px 24px;text-align:right">
        <p style="margin:0;color:rgba(255,255,255,0.50);font-size:11px">
          Ministry of Home Affairs<br>Government of India
        </p>
      </td>
    </tr></table>
  </td></tr>

  <!-- Body -->
  <tr><td style="padding:28px 28px 24px">{body_html}</td></tr>

  <!-- Footer -->
  <tr><td style="background:#f7f9fc;border-top:1px solid #e2e8f0;padding:14px 28px">
    <p style="margin:0;color:#a0aec0;font-size:11px;line-height:1.6">
      This is an automated message from AutoJustice AI NEXUS. Do not reply to this email.<br>
      For queries, visit your nearest Cyber Crime Police Station or call 1930 (National Cyber Crime Helpline).
    </p>
  </td></tr>

</table>
</td></tr>
</table>
</body></html>"""


def _risk_badge(risk_level: str) -> str:
    colors = {"HIGH": "#b91c1c", "MEDIUM": "#d97706", "LOW": "#16a34a"}
    bg = colors.get(risk_level, "#64748b")
    return (
        f'<span style="display:inline-block;background:{bg};color:#fff;'
        f'font-size:11px;font-weight:700;padding:3px 10px;border-radius:4px;'
        f'letter-spacing:.5px;text-transform:uppercase">{risk_level} RISK</span>'
    )


def _status_badge(status: str) -> str:
    colors = {
        "COMPLAINT_REGISTERED": "#16a34a",
        "UNDER_INVESTIGATION":  "#1d4ed8",
        "TRIAGED":              "#d97706",
        "CLOSED":               "#64748b",
    }
    labels = {
        "COMPLAINT_REGISTERED": "Complaint Registered",
        "UNDER_INVESTIGATION":  "Under Investigation",
        "TRIAGED":              "Awaiting Review",
        "CLOSED":               "Case Closed",
    }
    bg = colors.get(status, "#64748b")
    label = labels.get(status, status.replace("_", " ").title())
    return (
        f'<span style="display:inline-block;background:{bg};color:#fff;'
        f'font-size:11px;font-weight:700;padding:3px 10px;border-radius:4px;'
        f'letter-spacing:.5px">{label}</span>'
    )


# ─── Individual Email Templates ───────────────────────────────────────────────

def build_acknowledgement_email(
    name: str,
    case_number: str,
    risk_level: str,
    crime_category: str,
    ai_summary: str,
    fir_generated: bool,
    station_name: str,
) -> str:
    """T+0: Immediate acknowledgement after submission."""
    fir_note = (
        '<p style="margin:0 0 12px;padding:10px 14px;background:#d1fae5;border-left:4px solid #16a34a;'
        'color:#065f46;font-size:13px;border-radius:0 4px 4px 0">'
        '✓ <strong>Complaint Report (FIR) has been auto-generated</strong> for this case and '
        'forwarded to the duty officer for immediate review.</p>'
    ) if fir_generated else (
        '<p style="margin:0 0 12px;padding:10px 14px;background:#fef3c7;border-left:4px solid #d97706;'
        'color:#92400e;font-size:13px;border-radius:0 4px 4px 0">'
        '⚠ Your case has been triaged and queued for officer review. '
        'A complaint report will be generated after review.</p>'
    )

    body = f"""
<p style="margin:0 0 16px;color:#1a3f6f;font-size:16px;font-weight:700">
  Your Complaint Has Been Received
</p>
<p style="margin:0 0 20px;color:#4a5568;font-size:14px;line-height:1.7">
  Dear <strong>{name}</strong>,<br><br>
  Your cybercrime complaint has been successfully submitted to <strong>{station_name}</strong>.
  Our AI system has analysed your case and assigned it a priority level.
  Please save your case number for future reference.
</p>

<!-- Case Details Box -->
<table width="100%" cellpadding="0" cellspacing="0"
  style="background:#f0f4ff;border:1px solid #c7d7ff;border-radius:6px;margin-bottom:20px">
  <tr><td style="padding:18px 20px">
    <p style="margin:0 0 6px;color:#718096;font-size:11px;font-weight:600;
       text-transform:uppercase;letter-spacing:.5px">Case Number</p>
    <p style="margin:0 0 16px;color:#1a3f6f;font-size:24px;font-weight:700;
       font-family:monospace;letter-spacing:2px">{case_number}</p>
    <table cellpadding="0" cellspacing="0"><tr>
      <td style="padding-right:12px">{_risk_badge(risk_level)}</td>
      <td><span style="color:#4a5568;font-size:13px">{crime_category}</span></td>
    </tr></table>
  </td></tr>
</table>

{fir_note}

<!-- AI Summary -->
<p style="margin:0 0 8px;color:#2d3748;font-size:13px;font-weight:600">AI Case Summary</p>
<p style="margin:0 0 20px;color:#4a5568;font-size:13px;line-height:1.7;
   padding:12px 16px;background:#f7f9fc;border-radius:6px;border:1px solid #e2e8f0">
  {ai_summary}
</p>

<p style="margin:0 0 8px;color:#2d3748;font-size:13px;font-weight:600">What Happens Next?</p>
<ol style="margin:0 0 20px;padding-left:20px;color:#4a5568;font-size:13px;line-height:2">
  <li>A trained cyber crime officer will review your complaint and evidence within 24–48 hours.</li>
  <li>You will receive email updates as the case progresses.</li>
  <li>If additional information is needed, an officer may contact you.</li>
  <li>Track your case live at <strong>cybercrime.gov.in</strong> using case number <strong>{case_number}</strong>.</li>
</ol>

<p style="margin:0;color:#718096;font-size:12px;line-height:1.7">
  <strong>Helpline:</strong> 1930 (available 24×7) &nbsp;|&nbsp;
  <strong>Portal:</strong> cybercrime.gov.in
</p>
"""
    return _base_template(f"Case {case_number} — Complaint Received", body)


def build_status_update_email(
    name: str,
    case_number: str,
    status: str,
    risk_level: str,
    assigned_officer: Optional[str],
    crime_category: str,
    station_name: str,
    hours_elapsed: int,
) -> str:
    """T+24h or T+72h: Status update follow-up."""
    officer_note = (
        f'<p style="margin:0 0 16px;color:#4a5568;font-size:13px;line-height:1.7">'
        f'Your case has been assigned to <strong>{assigned_officer}</strong> '
        f'at {station_name}.</p>'
    ) if assigned_officer and assigned_officer != "Pending Assignment" else (
        '<p style="margin:0 0 16px;padding:10px 14px;background:#fef3c7;border-left:4px solid #d97706;'
        'color:#92400e;font-size:13px;border-radius:0 4px 4px 0">'
        '⏳ Your case is queued for officer assignment. High-priority cases are assigned within 24 hours. '
        'Thank you for your patience.</p>'
    )

    body = f"""
<p style="margin:0 0 16px;color:#1a3f6f;font-size:16px;font-weight:700">
  Case Status Update — {hours_elapsed}h Since Submission
</p>
<p style="margin:0 0 20px;color:#4a5568;font-size:14px;line-height:1.7">
  Dear <strong>{name}</strong>,<br><br>
  Here is the current status of your cybercrime complaint filed with <strong>{station_name}</strong>.
</p>

<table width="100%" cellpadding="0" cellspacing="0"
  style="background:#f0f4ff;border:1px solid #c7d7ff;border-radius:6px;margin-bottom:20px">
  <tr><td style="padding:18px 20px">
    <table cellpadding="4" cellspacing="0">
      <tr>
        <td style="color:#718096;font-size:12px;font-weight:600;width:140px">Case Number</td>
        <td style="color:#1a3f6f;font-size:14px;font-weight:700;font-family:monospace">{case_number}</td>
      </tr>
      <tr>
        <td style="color:#718096;font-size:12px;font-weight:600">Current Status</td>
        <td>{_status_badge(status)}</td>
      </tr>
      <tr>
        <td style="color:#718096;font-size:12px;font-weight:600">Risk Priority</td>
        <td>{_risk_badge(risk_level)}</td>
      </tr>
      <tr>
        <td style="color:#718096;font-size:12px;font-weight:600">Crime Type</td>
        <td style="color:#4a5568;font-size:13px">{crime_category}</td>
      </tr>
    </table>
  </td></tr>
</table>

{officer_note}

<p style="margin:0 0 8px;color:#2d3748;font-size:13px;font-weight:600">Track Your Case</p>
<p style="margin:0 0 20px;color:#4a5568;font-size:13px;line-height:1.7">
  Use case number <strong style="font-family:monospace;color:#1a3f6f">{case_number}</strong>
  on the cybercrime portal to track real-time updates.<br>
  For urgent matters, call <strong>1930</strong> (National Cyber Crime Helpline, available 24×7).
</p>
<p style="margin:0;color:#718096;font-size:12px">
  If you have additional evidence or information, reply to your original submission on the portal.
</p>
"""
    return _base_template(f"Case {case_number} — Status Update", body)


def build_closure_email(
    name: str,
    case_number: str,
    closure_reason: str,
    crime_category: str,
    station_name: str,
) -> str:
    """T+7d or on case closure: Final update."""
    body = f"""
<p style="margin:0 0 16px;color:#1a3f6f;font-size:16px;font-weight:700">
  Case Update — {case_number}
</p>
<p style="margin:0 0 20px;color:#4a5568;font-size:14px;line-height:1.7">
  Dear <strong>{name}</strong>,<br><br>
  We are writing to provide a final update on your cybercrime complaint filed with
  <strong>{station_name}</strong>.
</p>
<table width="100%" cellpadding="0" cellspacing="0"
  style="background:#f0f4ff;border:1px solid #c7d7ff;border-radius:6px;margin-bottom:20px">
  <tr><td style="padding:18px 20px">
    <p style="margin:0 0 4px;color:#718096;font-size:12px;font-weight:600">Case Number</p>
    <p style="margin:0 0 12px;color:#1a3f6f;font-size:18px;font-weight:700;font-family:monospace">{case_number}</p>
    <p style="margin:0 0 4px;color:#718096;font-size:12px;font-weight:600">Closure Note</p>
    <p style="margin:0;color:#4a5568;font-size:13px;line-height:1.7">{closure_reason or "Case processing completed."}</p>
  </td></tr>
</table>
<p style="margin:0 0 16px;color:#4a5568;font-size:13px;line-height:1.7">
  If you believe this matter requires further investigation, you may re-open your case
  by visiting the portal with your case number or by visiting your nearest cyber crime police station.
</p>
<p style="margin:0;color:#718096;font-size:12px">
  Thank you for using AutoJustice AI NEXUS. Your report helps make India's cyberspace safer.
</p>
"""
    return _base_template(f"Case {case_number} — Final Update", body)


# ─── Email Sending Engine ─────────────────────────────────────────────────────

class FollowUpEmailService:
    """
    Sends automated follow-up emails to complainants at key case milestones.
    All sends are non-blocking (call from BackgroundTasks).
    """

    def _send(self, to_email: str, subject: str, html_body: str) -> bool:
        """Low-level SMTP send. Returns True on success."""
        from config import settings
        if not settings.smtp_enabled or not settings.smtp_username:
            logger.info(f"[FOLLOWUP — SMTP disabled] Would send '{subject}' to {to_email}")
            return False
        if not to_email or "@" not in to_email:
            return False
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"]    = settings.smtp_from_email
            msg["To"]      = to_email
            msg.attach(MIMEText(html_body, "html"))
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=12) as s:
                s.starttls()
                s.login(settings.smtp_username, settings.smtp_password)
                s.sendmail(settings.smtp_from_email, to_email, msg.as_string())
            logger.info(f"Follow-up email sent: '{subject}' → {to_email[:4]}****")
            return True
        except Exception as e:
            logger.error(f"Follow-up email failed for {to_email[:4]}****: {e}")
            return False

    def send_acknowledgement(
        self,
        to_email: str,
        name: str,
        case_number: str,
        risk_level: str,
        crime_category: str,
        ai_summary: str,
        fir_generated: bool,
        station_name: str,
    ) -> bool:
        """Send immediate acknowledgement email at submission."""
        from config import settings
        if not settings.followup_emails_enabled:
            return False
        html = build_acknowledgement_email(
            name, case_number, risk_level, crime_category,
            ai_summary, fir_generated, station_name,
        )
        return self._send(
            to_email,
            f"✓ Complaint Received — Case {case_number} | AutoJustice AI NEXUS",
            html,
        )

    def send_status_update(
        self,
        to_email: str,
        name: str,
        case_number: str,
        status: str,
        risk_level: str,
        crime_category: str,
        assigned_officer: Optional[str],
        station_name: str,
        hours_elapsed: int = 24,
    ) -> bool:
        """Send 24h/72h follow-up status update."""
        from config import settings
        if not settings.followup_emails_enabled:
            return False
        html = build_status_update_email(
            name, case_number, status, risk_level,
            assigned_officer, crime_category, station_name, hours_elapsed,
        )
        return self._send(
            to_email,
            f"Case {case_number} — Status Update ({hours_elapsed}h) | AutoJustice",
            html,
        )

    def send_closure_update(
        self,
        to_email: str,
        name: str,
        case_number: str,
        closure_reason: str,
        crime_category: str,
        station_name: str,
    ) -> bool:
        """Send final case closure email."""
        from config import settings
        if not settings.followup_emails_enabled:
            return False
        html = build_closure_email(name, case_number, closure_reason, crime_category, station_name)
        return self._send(
            to_email,
            f"Case {case_number} — Final Update | AutoJustice AI NEXUS",
            html,
        )


# Module-level singleton
followup_service = FollowUpEmailService()
