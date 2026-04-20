/**
 * AutoJustice AI NEXUS — Citizen Portal JS
 * Handles email OTP verification, multi-step form, file upload, submission.
 * Phase 2: i18n multi-language support integrated.
 */

// ── Phase 2: i18n Integration ─────────────────────────────────────────────────
// Dynamically import i18n module (ES module pattern)
let _t = (key) => key;   // Fallback: return key if i18n not loaded
let _setLang = null;
(async () => {
  try {
    const i18n = await import('/static/js/i18n.js');
    _t = i18n.t;
    _setLang = i18n.setLang;
    i18n.initI18n();
  } catch (e) {
    console.warn('[i18n] Failed to load:', e);
  }
})();

let currentStep = 1;
let selectedFiles = [];
let submittedReportId = null;
let otpSessionToken = null;   // Set after successful OTP verification
let verifiedEmail = null;
let resendCountdownTimer = null;

// ── Email OTP Verification ──────────────────────────────────────────────────

async function sendOTP() {
  const emailInput = document.getElementById('otpEmail');
  const email = emailInput ? emailInput.value.trim() : '';

  if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    emailInput.style.borderColor = 'var(--red)';
    showToast('Please enter a valid email address.', 'err');
    emailInput.focus();
    return;
  }
  emailInput.style.borderColor = '';

  const btn = document.getElementById('sendOtpBtn');
  btn.disabled = true;
  btn.textContent = 'Sending...';

  try {
    const res = await fetch('/api/auth/send-otp', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    });
    const data = await res.json();

    if (!res.ok) throw new Error(data.detail || 'Failed to send OTP');

    // Show OTP entry row, disable email input
    document.getElementById('otpEntryRow').style.display = 'block';
    emailInput.readOnly = true;
    btn.style.display = 'none';

    // Focus first digit
    document.getElementById('d0').focus();

    showToast('OTP sent! Check your inbox.', 'ok');
    _startResendCountdown(60);

  } catch (err) {
    btn.disabled = false;
    btn.textContent = 'Send OTP';
    showToast(err.message, 'err');
  }
}

async function verifyOTP() {
  const digits = ['d0','d1','d2','d3','d4','d5'].map(id => {
    const el = document.getElementById(id);
    return el ? el.value.trim() : '';
  });
  const otp = digits.join('');

  if (otp.length !== 6 || !/^\d{6}$/.test(otp)) {
    showToast('Please enter the complete 6-digit OTP.', 'err');
    document.getElementById('d0').focus();
    return;
  }

  const email = document.getElementById('otpEmail').value.trim();
  const btn = document.getElementById('verifyOtpBtn');
  btn.disabled = true;
  btn.textContent = 'Verifying...';

  try {
    const res = await fetch('/api/auth/verify-otp', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, otp }),
    });
    const data = await res.json();

    if (!res.ok) throw new Error(data.detail || 'Verification failed');

    otpSessionToken = data.session_token;
    verifiedEmail   = email;

    // Hide OTP section
    document.getElementById('otp-section').style.display = 'none';

    // Stop countdown
    if (resendCountdownTimer) clearInterval(resendCountdownTimer);

    // Show verified banner
    const banner = document.getElementById('verifiedBanner');
    banner.classList.add('show');
    const ve = document.getElementById('verifiedEmail');
    if (ve) ve.textContent = email + ' — Verified';

    // Reveal form
    document.getElementById('formSection').style.display = 'block';

    // Pre-fill email in form (read-only)
    const emailField = document.getElementById('complainant_email');
    if (emailField) {
      emailField.value = email;
      emailField.readOnly = true;
    }

    showToast('Email verified. Please fill in your complaint details.', 'ok');
    window.scrollTo({ top: 0, behavior: 'smooth' });

  } catch (err) {
    btn.disabled = false;
    btn.textContent = 'Verify OTP';
    showToast(err.message, 'err');
    // Shake digits
    document.querySelectorAll('.otp-digit').forEach(el => {
      el.style.borderColor = 'var(--red)';
      setTimeout(() => { el.style.borderColor = ''; }, 1500);
    });
  }
}

async function resendOTP() {
  const btn = document.getElementById('resendBtn');
  if (btn.disabled) return;

  const email = document.getElementById('otpEmail').value.trim();
  btn.disabled = true;

  try {
    const res = await fetch('/api/auth/send-otp', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed to resend OTP');

    // Clear digits
    ['d0','d1','d2','d3','d4','d5'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.value = '';
    });
    document.getElementById('d0').focus();

    showToast('New OTP sent!', 'ok');
    _startResendCountdown(60);

  } catch (err) {
    showToast(err.message, 'err');
    btn.disabled = false;
  }
}

function resetOtpFlow() {
  // Allow user to change email
  const emailInput = document.getElementById('otpEmail');
  emailInput.readOnly = false;
  emailInput.value = '';
  emailInput.focus();

  document.getElementById('otpEntryRow').style.display = 'none';

  const sendBtn = document.getElementById('sendOtpBtn');
  sendBtn.style.display = '';
  sendBtn.disabled = false;
  sendBtn.textContent = 'Send OTP';

  const verifyBtn = document.getElementById('verifyOtpBtn');
  verifyBtn.disabled = false;
  verifyBtn.textContent = 'Verify OTP';

  ['d0','d1','d2','d3','d4','d5'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = '';
  });

  if (resendCountdownTimer) clearInterval(resendCountdownTimer);
  const resendBtn = document.getElementById('resendBtn');
  resendBtn.disabled = true;
  document.getElementById('resendTimer').textContent = '60';
}

function _startResendCountdown(seconds) {
  if (resendCountdownTimer) clearInterval(resendCountdownTimer);

  let remaining = seconds;
  const timerEl = document.getElementById('resendTimer');
  const resendBtn = document.getElementById('resendBtn');

  resendBtn.disabled = true;
  if (timerEl) timerEl.textContent = remaining;

  resendCountdownTimer = setInterval(() => {
    remaining -= 1;
    if (timerEl) timerEl.textContent = remaining;
    if (remaining <= 0) {
      clearInterval(resendCountdownTimer);
      resendCountdownTimer = null;
      resendBtn.disabled = false;
    }
  }, 1000);
}

// ── OTP Digit Auto-Tab Behavior ─────────────────────────────────────────────

function _setupOtpDigits() {
  const digits = document.querySelectorAll('.otp-digit');
  digits.forEach((input, idx) => {
    input.addEventListener('input', (e) => {
      const val = e.target.value.replace(/\D/g, '');
      e.target.value = val.slice(-1); // keep only last digit
      if (val && idx < digits.length - 1) digits[idx + 1].focus();
      // Auto-submit when last digit filled
      if (idx === digits.length - 1 && val) verifyOTP();
    });

    input.addEventListener('keydown', (e) => {
      if (e.key === 'Backspace' && !e.target.value && idx > 0) {
        digits[idx - 1].focus();
      }
      if (e.key === 'ArrowLeft'  && idx > 0) digits[idx - 1].focus();
      if (e.key === 'ArrowRight' && idx < digits.length - 1) digits[idx + 1].focus();
    });

    // Handle paste on any digit
    input.addEventListener('paste', (e) => {
      e.preventDefault();
      const pasted = (e.clipboardData || window.clipboardData).getData('text').replace(/\D/g, '');
      pasted.split('').slice(0, 6).forEach((ch, i) => {
        if (digits[i]) digits[i].value = ch;
      });
      const next = Math.min(pasted.length, digits.length - 1);
      digits[next].focus();
      if (pasted.length >= 6) verifyOTP();
    });
  });
}

// ── Step Navigation ─────────────────────────────────────────────────────────

function goToStep(step) {
  if (step === 2 && !validateStep1()) return;
  if (step === 3 && !validateStep2()) return;
  if (step === 4) buildReview();

  document.querySelectorAll('.form-step').forEach(el => el.classList.remove('active'));
  const target = document.getElementById(`formStep${step}`);
  if (target) target.classList.add('active');
  currentStep = step;

  // Update step indicators
  for (let i = 1; i <= 4; i++) {
    const stepEl = document.getElementById(`step-${i}`);
    if (!stepEl) continue;
    stepEl.classList.remove('active', 'done');
    if (i < step)  stepEl.classList.add('done');
    if (i === step) stepEl.classList.add('active');
  }

  // Update connecting lines
  for (let i = 1; i <= 3; i++) {
    const line = document.getElementById(`line-${i}`);
    if (line) line.classList.toggle('done', i < step);
  }

  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function validateStep1() {
  const name = document.getElementById('complainant_name').value.trim();
  if (!name || name.length < 2) {
    showToast('Please enter your full name.', 'err');
    document.getElementById('complainant_name').focus();
    return false;
  }
  return true;
}

function validateStep2() {
  const desc = document.getElementById('incident_description').value.trim();
  if (!desc || desc.length < 20) {
    showToast('Please describe the incident in at least 20 characters.', 'err');
    document.getElementById('incident_description').focus();
    return false;
  }
  return true;
}

// ── Live Stats ───────────────────────────────────────────────────────────────

async function loadLiveStats() {
  try {
    const res  = await fetch('/api/dashboard/live-stats');
    if (!res.ok) return;
    const data = await res.json();

    const total = data.total_reports_processed;
    const firs  = data.firs_auto_generated;
    const today = data.reports_today;
    const fake  = data.fake_blocked;

    _setText('statTotal',   total?.toLocaleString('en-IN'));
    _setText('statFirs',    firs?.toLocaleString('en-IN'));
    _setText('statToday',   today?.toLocaleString('en-IN'));
    _setText('statFake',    fake?.toLocaleString('en-IN'));
    _setText('tickerTotal', total?.toLocaleString('en-IN'));
  } catch (_) { /* server may not be ready yet */ }
}

function _setText(id, val) {
  const el = document.getElementById(id);
  if (el && val != null) el.textContent = val;
}

// ── Character Counter ────────────────────────────────────────────────────────

function _setupCharCounter() {
  const desc    = document.getElementById('incident_description');
  const counter = document.getElementById('desc-counter');
  if (!desc || !counter) return;

  desc.addEventListener('input', () => {
    const len = desc.value.length;
    if (len < 20) {
      counter.textContent = `${20 - len} more characters needed`;
      counter.style.color = 'var(--red)';
    } else {
      counter.textContent = `&#10003; ${len} characters`;
      counter.style.color = 'var(--success)';
    }
  });
}

// ── File Upload Dropzone ─────────────────────────────────────────────────────

function setupDropzone() {
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('evidence_files');
  if (!dropzone || !fileInput) return;

  dropzone.addEventListener('dragover', e => {
    e.preventDefault();
    dropzone.classList.add('dragover');
  });
  dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
  dropzone.addEventListener('drop', e => {
    e.preventDefault();
    dropzone.classList.remove('dragover');
    _addFiles(e.dataTransfer.files);
  });

  fileInput.addEventListener('change', () => _addFiles(fileInput.files));
}

async function _addFiles(files) {
  const MAX_MB  = 25;
  const ALLOWED = ['.jpg','.jpeg','.png','.gif','.bmp','.tiff','.pdf','.txt'];

  for (const file of Array.from(files)) {
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!ALLOWED.includes(ext)) {
      showToast(`"${file.name}" is not a supported file type.`, 'err');
      continue;
    }
    if (file.size > MAX_MB * 1024 * 1024) {
      showToast(`"${file.name}" exceeds the 25 MB limit.`, 'err');
      continue;
    }
    if (selectedFiles.find(f => f.name === file.name && f.size === file.size)) continue;

    // Add with pending status, then validate
    const entry = { file, status: 'validating', warning: null };
    selectedFiles.push(entry);
    _renderFileList();

    try {
      const fd = new FormData();
      fd.append('file', file);
      const res = await fetch('/api/reports/validate-evidence', { method: 'POST', body: fd });
      const data = await res.json();

      if (data.blocked) {
        // Remove from list and show blocking error
        selectedFiles = selectedFiles.filter(e => e !== entry);
        _renderFileList();
        _showFileError(file.name, data.warnings[0]);
        continue;
      } else if (data.warnings && data.warnings.length > 0) {
        entry.status = 'warning';
        entry.warning = data.warnings[0];
      } else {
        entry.status = 'ok';
      }
    } catch (_) {
      entry.status = 'ok'; // OCR service unavailable — allow and let server decide
    }

    _renderFileList();
  }
}

function _showFileError(filename, message) {
  // Inline error block above the dropzone
  const container = document.getElementById('fileList');
  const errEl = document.createElement('div');
  errEl.style.cssText = 'background:#fef2f2;border:1px solid #fca5a5;border-left:4px solid var(--red);padding:10px 14px;border-radius:3px;margin-bottom:8px;font-size:12px;color:#7f1d1d';
  errEl.innerHTML = `<strong>File rejected: ${escapeHtml(filename)}</strong><br>${escapeHtml(message)}`;
  container.insertBefore(errEl, container.firstChild);
  setTimeout(() => errEl.remove(), 8000);
}

function _renderFileList() {
  const container = document.getElementById('fileList');
  if (!container) return;
  container.innerHTML = '';

  selectedFiles.forEach((entry, idx) => {
    const file   = entry.file || entry; // support legacy plain File objects
    const status = entry.status || 'ok';
    const warning = entry.warning || null;

    const ext    = file.name.split('.').pop().toLowerCase();
    const sizeMB = (file.size / (1024 * 1024)).toFixed(2);

    const statusIcon = status === 'validating' ? '<span style="color:var(--gray-400);font-size:11px">Checking...</span>'
                     : status === 'warning'    ? '<span style="color:var(--saffron);font-size:11px;font-weight:600">&#9888; Warning</span>'
                     : status === 'ok'         ? '<span style="color:var(--success);font-size:11px">&#10003; Valid</span>'
                     : '';

    const borderColor = status === 'warning' ? 'border-color:#fcd34d;background:#fffbeb'
                      : status === 'ok'      ? '' : '';

    const item = document.createElement('div');
    item.className = 'file-item';
    item.style.cssText = status === 'warning' ? 'border-color:#fcd34d;background:#fffbeb;flex-wrap:wrap' : 'flex-wrap:wrap';
    item.innerHTML = `
      <span class="fname" style="flex:1">&#128196; ${escapeHtml(file.name)}</span>
      <span class="fsize">${sizeMB} MB</span>
      ${statusIcon}
      <span class="frem" onclick="removeFile(${idx})" title="Remove">&times;</span>
      ${warning ? `<div style="width:100%;font-size:11px;color:#78350f;margin-top:6px;padding-top:6px;border-top:1px solid #fcd34d">&#9888; ${escapeHtml(warning)}</div>` : ''}
    `;
    container.appendChild(item);
  });
}

function removeFile(idx) {
  selectedFiles.splice(idx, 1);
  _renderFileList();
}

function _getActualFiles() {
  return selectedFiles.map(e => e.file || e);
}

// ── Review Builder ───────────────────────────────────────────────────────────

function buildReview() {
  const fields = {
    'Full Name':      document.getElementById('complainant_name')?.value,
    'Mobile':         document.getElementById('complainant_phone')?.value || '—',
    'Email':          document.getElementById('complainant_email')?.value || '—',
    'Address':        document.getElementById('complainant_address')?.value || '—',
    'Incident Date':  document.getElementById('incident_date')?.value || '—',
    'Location':       document.getElementById('incident_location')?.value || '—',
  };

  const desc      = document.getElementById('incident_description')?.value || '';
  const fileCount = selectedFiles.length;
  const actualFiles = _getActualFiles();

  const rows = Object.entries(fields).map(([k, v]) => `
    <tr>
      <td>${escapeHtml(k)}</td>
      <td>${escapeHtml(v || '—')}</td>
    </tr>
  `).join('');

  document.getElementById('reviewContent').innerHTML = `
    <table class="review-table" style="margin-bottom:14px">${rows}</table>
    <div style="margin-bottom:12px">
      <div style="font-size:11px;color:var(--gray-400);font-weight:600;text-transform:uppercase;margin-bottom:6px">Incident Description</div>
      <div style="background:var(--gray-50);border:1px solid var(--gray-200);padding:12px 14px;border-radius:3px;font-size:13px;line-height:1.7">${escapeHtml(desc)}</div>
    </div>
    <div style="background:var(--gov-blue-lt);border:1px solid #c3d4e8;padding:10px 14px;border-radius:3px;font-size:12px;color:var(--gov-blue)">
      <strong>${fileCount} evidence file${fileCount !== 1 ? 's' : ''} attached</strong>
      ${fileCount > 0 ? ' — ' + actualFiles.map(f => escapeHtml(f.name)).join(', ') : ''}
    </div>
  `;
}

// ── Form Submission ──────────────────────────────────────────────────────────

function setupFormSubmit() {
  const form = document.getElementById('reportForm');
  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const submitBtn = document.getElementById('submitBtn');
    submitBtn.disabled = true;

    showLoading(true, 'Uploading evidence files...');

    const formData = new FormData();

    // Attach OTP session token if verified
    if (otpSessionToken) {
      formData.append('otp_session_token', otpSessionToken);
    }

    formData.append('complainant_name',      document.getElementById('complainant_name').value);
    formData.append('incident_description',  document.getElementById('incident_description').value);
    formData.append('complainant_phone',     document.getElementById('complainant_phone').value || '');
    formData.append('complainant_email',     document.getElementById('complainant_email').value || '');
    formData.append('complainant_address',   document.getElementById('complainant_address').value || '');
    formData.append('incident_date',         document.getElementById('incident_date').value || '');
    formData.append('incident_location',     document.getElementById('incident_location').value || '');

    _getActualFiles().forEach(file => formData.append('evidence_files', file));

    const loadingSteps = [
      [800,  'Running OCR on evidence files...'],
      [1600, 'AI semantic analysis in progress...'],
      [2400, 'Running fake report detection...'],
      [3200, 'Extracting entities for Complaint Report...'],
      [4000, 'Generating Complaint Report PDF...'],
    ];
    loadingSteps.forEach(([delay, msg]) => {
      setTimeout(() => setLoadingText(msg), delay);
    });

    try {
      const response = await fetch('/api/reports/submit', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Submission failed.');
      }

      const data = await response.json();
      showLoading(false);
      displayResult(data);
      submittedReportId = data.id;

    } catch (err) {
      showLoading(false);
      submitBtn.disabled = false;
      showToast('Submission failed: ' + err.message, 'err');
    }
  });
}

// ── Result Display ───────────────────────────────────────────────────────────

function displayResult(data) {
  document.getElementById('reportForm').style.display = 'none';
  const stepProgress = document.querySelector('.step-progress');
  if (stepProgress) stepProgress.style.display = 'none';
  document.getElementById('result-section').style.display = 'block';

  const risk   = (data.risk_level || 'PENDING').toLowerCase();
  const head   = document.getElementById('resultHead');
  if (head) head.className = `result-head ${risk}`;

  document.getElementById('resultBadge').textContent       = 'Complaint Registered';
  document.getElementById('resultCaseNumber').textContent  = data.case_number || '—';
  document.getElementById('resultStatusMsg').textContent   =
    risk === 'high'   ? 'High-risk threat detected. Complaint Report auto-registered. Police notified.' :
    risk === 'medium' ? 'Medium-risk case. Under priority review.' :
                        'Complaint submitted successfully. Under standard review.';

  document.getElementById('resultRiskLevel').textContent = (data.risk_level || '—');
  document.getElementById('resultRiskLevel').style.color =
    risk === 'high' ? 'var(--red)' : risk === 'medium' ? 'var(--saffron)' : 'var(--success)';

  document.getElementById('resultCrimeCategory').textContent = data.crime_category || '—';

  document.getElementById('resultFirStatus').textContent =
    data.fir_path ? 'Complaint Report Auto-Generated' : 'Pending Officer Review';

  const auth    = data.authenticity_score || 0;
  const authPct = (auth * 100).toFixed(0);
  document.getElementById('resultAuthenticity').textContent =
    data.fake_recommendation === 'GENUINE' ? `Genuine (${authPct}%)` :
    data.fake_recommendation === 'REVIEW'  ? `Under Review (${authPct}%)` :
    data.is_flagged_fake                   ? `Flagged (${authPct}%)` :
    `${authPct}%`;

  const authColor = auth > 0.65 ? 'var(--success)' : auth > 0.45 ? 'var(--saffron)' : 'var(--red)';
  const authBar   = document.getElementById('authBar');
  if (authBar) {
    authBar.style.width      = authPct + '%';
    authBar.style.background = authColor;
  }

  document.getElementById('resultAiSummary').textContent = data.ai_summary || 'Analysis complete.';
  document.getElementById('resultHash').textContent      = data.content_hash || 'N/A';

  const dlBtn = document.getElementById('downloadFirBtn');
  if (data.fir_path && dlBtn) {
    dlBtn.style.display = 'inline-flex';
    dlBtn.onclick = downloadComplaintReport;
  }

  document.querySelector('.result-wrap')?.scrollIntoView({ behavior: 'smooth' });
}

function downloadComplaintReport() {
  if (!submittedReportId) {
    showToast('No report ID found. Please resubmit.', 'err');
    return;
  }
  const link = document.createElement('a');
  link.href     = `/api/reports/${submittedReportId}/fir/download`;
  link.download = `ComplaintReport_${submittedReportId}.pdf`;
  link.target   = '_blank';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  showToast('Downloading Complaint Report PDF...', 'ok');
}

function submitAnother() {
  location.reload();
}

// ── Utilities ────────────────────────────────────────────────────────────────

function showLoading(show, text = 'Processing...') {
  const overlay = document.getElementById('loadingOverlay');
  const textEl  = document.getElementById('loadingText');
  if (overlay) overlay.classList.toggle('show', show);
  if (textEl)  textEl.textContent = text;
}

function setLoadingText(text) {
  const el = document.getElementById('loadingText');
  if (el) el.textContent = text;
}

function showToast(message, type = 'info') {
  const toast = document.getElementById('toast');
  if (!toast) return;
  toast.textContent = message;
  toast.className = `toast show${type ? ' ' + type : ''}`;
  setTimeout(() => toast.classList.remove('show'), 3500);
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ── Init ─────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  _setupOtpDigits();
  _setupCharCounter();
  setupDropzone();
  setupFormSubmit();
  loadLiveStats();
  setInterval(loadLiveStats, 30000);

  // Focus email input on load
  const emailInput = document.getElementById('otpEmail');
  if (emailInput) emailInput.focus();
});
