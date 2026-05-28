/**
 * AutoJustice AI NEXUS — Citizen Portal JS
 * Dual OTP Verification: Phone (SMS) + Email both required before form opens.
 * DigiLocker: optional Aadhaar verification (boosts trust score).
 */

// ── i18n (Phase 2) ────────────────────────────────────────────────────────────
let _t = (key) => key;
let _setLang = null;
(async () => {
  try {
    const i18n = await import('/static/js/i18n.js');
    _t = i18n.t;
    _setLang = i18n.setLang;
    i18n.initI18n();
  } catch (e) { console.warn('[i18n] Failed to load:', e); }
})();

// ── Global State ──────────────────────────────────────────────────────────────
let currentStep = 1;
let selectedFiles = [];
let submittedReportId = null;

// Dual verification tokens
let phoneOtpToken = null;       // Set after phone OTP verified
let emailOtpToken = null;       // Set after email OTP verified
let digilockerSessionToken = null; // Optional DigiLocker

let verifiedPhone = null;
let verifiedEmail = null;

let phoneResendTimer = null;
let emailResendTimer = null;

// ═══════════════════════════════════════════════════════════════════════════════
// PHONE OTP (Step 1)
// ═══════════════════════════════════════════════════════════════════════════════

async function sendPhoneOTP() {
  const input = document.getElementById('phoneNumber');
  const phone = input ? input.value.trim() : '';

  if (!phone || !/^[6-9]\d{9}$/.test(phone.replace(/\D/g, '').slice(-10))) {
    if (input) input.style.borderColor = 'var(--red)';
    showToast('Please enter a valid 10-digit Indian mobile number.', 'err');
    if (input) input.focus();
    return;
  }
  if (input) input.style.borderColor = '';

  const btn = document.getElementById('sendPhoneOtpBtn');
  btn.disabled = true;
  btn.textContent = 'Sending...';

  try {
    const res = await fetch('/api/auth/send-otp', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phone }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed to send SMS OTP');

    document.getElementById('phoneOtpEntryRow').style.display = 'block';
    if (input) input.readOnly = true;
    btn.style.display = 'none';

    const d = document.getElementById('p0');
    if (d) d.focus();
    showToast('OTP sent via SMS! Check your messages.', 'ok');
    _startCountdown('phoneResendTimer', 'phoneResendBtn', 60, 'phoneResendTimer_ref');

  } catch (err) {
    btn.disabled = false;
    btn.textContent = 'Send OTP';
    showToast(err.message, 'err');
  }
}

async function verifyPhoneOTP() {
  const digits = ['p0','p1','p2','p3','p4','p5'].map(id => {
    const el = document.getElementById(id);
    return el ? el.value.trim() : '';
  });
  const otp = digits.join('');

  if (otp.length !== 6 || !/^\d{6}$/.test(otp)) {
    showToast('Please enter the complete 6-digit OTP.', 'err');
    const d = document.getElementById('p0');
    if (d) d.focus();
    return;
  }

  const phone = document.getElementById('phoneNumber').value.trim();
  const btn = document.getElementById('verifyPhoneOtpBtn');
  btn.disabled = true;
  btn.textContent = 'Verifying...';

  try {
    const res = await fetch('/api/auth/verify-otp', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phone, otp }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Verification failed');

    phoneOtpToken = data.session_token;
    verifiedPhone = phone;

    // Collapse panel with done style
    const panel = document.getElementById('dvp-phone');
    if (panel) panel.classList.add('dv-done');
    const doneMsg = document.getElementById('dvp-phone-done');
    if (doneMsg) {
      doneMsg.style.display = 'flex';
      const sp = doneMsg.querySelector('.dv-done-num');
      if (sp) sp.textContent = '+91 ' + phone.replace(/\D/g,'').slice(-10);
    }

    // Update checklist
    const chk = document.getElementById('dv-check-phone');
    if (chk) { chk.textContent = '✅'; chk.style.color = '#16a34a'; }
    const lbl = document.getElementById('dv-check-phone-label');
    if (lbl) lbl.style.color = '#16a34a';

    showToast('✅ Mobile number verified!', 'ok');
    _checkBothVerified();

  } catch (err) {
    btn.disabled = false;
    btn.textContent = 'Verify OTP';
    showToast(err.message, 'err');
    document.querySelectorAll('.phone-otp-digit').forEach(el => {
      el.style.borderColor = 'var(--red)';
      setTimeout(() => { el.style.borderColor = ''; }, 1500);
    });
  }
}

async function resendPhoneOTP() {
  const btn = document.getElementById('phoneResendBtn');
  if (btn && btn.disabled) return;
  const phone = document.getElementById('phoneNumber').value.trim();
  if (btn) btn.disabled = true;

  try {
    const res = await fetch('/api/auth/send-otp', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phone }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed to resend OTP');

    ['p0','p1','p2','p3','p4','p5'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.value = '';
    });
    const d = document.getElementById('p0');
    if (d) d.focus();
    showToast('New SMS OTP sent!', 'ok');
    _startCountdown('phoneResendTimer', 'phoneResendBtn', 60, 'phoneResendTimer_ref');
  } catch (err) {
    showToast(err.message, 'err');
    if (btn) btn.disabled = false;
  }
}

function resetPhoneOtpFlow() {
  const input = document.getElementById('phoneNumber');
  if (input) { input.readOnly = false; input.value = ''; input.focus(); }
  const entryRow = document.getElementById('phoneOtpEntryRow');
  if (entryRow) entryRow.style.display = 'none';
  const sendBtn = document.getElementById('sendPhoneOtpBtn');
  if (sendBtn) { sendBtn.style.display = ''; sendBtn.disabled = false; sendBtn.textContent = 'Send OTP'; }
  ['p0','p1','p2','p3','p4','p5'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = '';
  });
}

// ═══════════════════════════════════════════════════════════════════════════════
// EMAIL OTP (Step 2)
// ═══════════════════════════════════════════════════════════════════════════════

async function sendOTP() {
  const emailInput = document.getElementById('otpEmail');
  const email = emailInput ? emailInput.value.trim() : '';

  if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    if (emailInput) emailInput.style.borderColor = 'var(--red)';
    showToast('Please enter a valid email address.', 'err');
    if (emailInput) emailInput.focus();
    return;
  }
  if (emailInput) emailInput.style.borderColor = '';

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

    document.getElementById('otpEntryRow').style.display = 'block';
    if (emailInput) emailInput.readOnly = true;
    btn.style.display = 'none';

    const d = document.getElementById('d0');
    if (d) d.focus();
    showToast('OTP sent! Check your inbox (and spam folder).', 'ok');
    _startCountdown('resendTimer', 'resendBtn', 60, 'emailResendTimer_ref');

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
    const d = document.getElementById('d0');
    if (d) d.focus();
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

    emailOtpToken = data.session_token;
    verifiedEmail = email;

    // Collapse panel with done style
    const panel = document.getElementById('dvp-email');
    if (panel) panel.classList.add('dv-done');
    const doneMsg = document.getElementById('dvp-email-done');
    if (doneMsg) {
      doneMsg.style.display = 'flex';
      const sp = doneMsg.querySelector('.dv-done-email');
      if (sp) sp.textContent = email;
    }

    // Update checklist
    const chk = document.getElementById('dv-check-email');
    if (chk) { chk.textContent = '✅'; chk.style.color = '#16a34a'; }
    const lbl = document.getElementById('dv-check-email-label');
    if (lbl) lbl.style.color = '#16a34a';

    showToast('✅ Email verified!', 'ok');
    _checkBothVerified();

  } catch (err) {
    btn.disabled = false;
    btn.textContent = 'Verify OTP';
    showToast(err.message, 'err');
    document.querySelectorAll('.otp-digit').forEach(el => {
      el.style.borderColor = 'var(--red)';
      setTimeout(() => { el.style.borderColor = ''; }, 1500);
    });
  }
}

async function resendOTP() {
  const btn = document.getElementById('resendBtn');
  if (btn && btn.disabled) return;
  const email = document.getElementById('otpEmail').value.trim();
  if (btn) btn.disabled = true;

  try {
    const res = await fetch('/api/auth/send-otp', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed to resend OTP');

    ['d0','d1','d2','d3','d4','d5'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.value = '';
    });
    const d = document.getElementById('d0');
    if (d) d.focus();
    showToast('New OTP sent!', 'ok');
    _startCountdown('resendTimer', 'resendBtn', 60, 'emailResendTimer_ref');
  } catch (err) {
    showToast(err.message, 'err');
    if (btn) btn.disabled = false;
  }
}

function resetOtpFlow() {
  const emailInput = document.getElementById('otpEmail');
  if (emailInput) { emailInput.readOnly = false; emailInput.value = ''; emailInput.focus(); }
  const entryRow = document.getElementById('otpEntryRow');
  if (entryRow) entryRow.style.display = 'none';
  const sendBtn = document.getElementById('sendOtpBtn');
  if (sendBtn) { sendBtn.style.display = ''; sendBtn.disabled = false; sendBtn.textContent = 'Send OTP'; }
  ['d0','d1','d2','d3','d4','d5'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = '';
  });
}

// ═══════════════════════════════════════════════════════════════════════════════
// DUAL VERIFICATION CHECK
// ═══════════════════════════════════════════════════════════════════════════════

function _checkBothVerified() {
  const phoneOk = !!phoneOtpToken;
  const emailOk = !!emailOtpToken;

  // Update checklist badges
  const phoneBadge = document.getElementById('dv-badge-phone');
  const emailBadge = document.getElementById('dv-badge-email');
  if (phoneBadge) {
    phoneBadge.textContent = phoneOk ? '✅ Verified' : 'REQUIRED';
    phoneBadge.style.background = phoneOk ? '#dcfce7' : '#fee2e2';
    phoneBadge.style.color = phoneOk ? '#166534' : '#991b1b';
  }
  if (emailBadge) {
    emailBadge.textContent = emailOk ? '✅ Verified' : 'REQUIRED';
    emailBadge.style.background = emailOk ? '#dcfce7' : '#fee2e2';
    emailBadge.style.color = emailOk ? '#166534' : '#991b1b';
  }

  const btn = document.getElementById('dv-proceed-btn');
  if (btn) {
    btn.disabled = !(phoneOk && emailOk);
    if (phoneOk && emailOk) {
      btn.textContent = '✅ Both Verified — Continue to Complaint Form →';
      btn.style.background = '#16a34a';
    }
  }
}

function proceedWithBothVerified() {
  if (!phoneOtpToken || !emailOtpToken) {
    showToast('Please complete both phone and email verification first.', 'err');
    return;
  }

  // Hide verification section, show form
  const dvSection = document.getElementById('dv-section');
  if (dvSection) dvSection.style.display = 'none';
  const formSection = document.getElementById('formSection');
  if (formSection) formSection.style.display = 'block';

  // Pre-fill phone and email in form
  const phoneField = document.getElementById('complainant_phone');
  if (phoneField && verifiedPhone) {
    phoneField.value = verifiedPhone;
    phoneField.readOnly = true;
  }
  const emailField = document.getElementById('complainant_email');
  if (emailField && verifiedEmail) {
    emailField.value = verifiedEmail;
    emailField.readOnly = true;
  }

  showToast('Identity verified! Please fill in your complaint details.', 'ok');
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ═══════════════════════════════════════════════════════════════════════════════
// DIGILOCKER (Optional)
// ═══════════════════════════════════════════════════════════════════════════════

function toggleDigiLockerPanel() {
  const body = document.getElementById('dv-opt-body');
  const arrow = document.getElementById('dv-opt-arrow');
  if (!body) return;
  const isOpen = body.style.display !== 'none';
  body.style.display = isOpen ? 'none' : 'block';
  if (arrow) arrow.textContent = isOpen ? '›' : '⌄';
}

function openDigiLockerPopup() {
  fetch('/api/digilocker/auth-url')
    .then(r => r.json())
    .then(d => {
      if (d.auth_url) {
        const popup = window.open(d.auth_url, 'DigiLocker', 'width=500,height=650,scrollbars=yes');
        window._digiLockerPopup = popup;
        // Poll for callback
        const poll = setInterval(() => {
          try {
            if (popup.closed) {
              clearInterval(poll);
              return;
            }
            const url = popup.location.href;
            if (url && url.includes('/api/digilocker/callback')) {
              clearInterval(poll);
              popup.close();
              showToast('DigiLocker verification in progress...', 'ok');
            }
          } catch (_) { /* cross-origin — ignore */ }
        }, 500);
      } else {
        showToast(d.message || 'DigiLocker not configured yet.', 'err');
      }
    })
    .catch(() => showToast('DigiLocker service unavailable.', 'err'));
}

// Called from DigiLocker callback (postMessage)
window.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'digilocker_verified') {
    digilockerSessionToken = event.data.session_token;
    const btn = document.getElementById('dlVerifyBtn');
    if (btn) { btn.textContent = '✅ Aadhaar Verified'; btn.disabled = true; btn.style.background = '#16a34a'; }
    showToast('✅ Aadhaar verified via DigiLocker!', 'ok');
  }
});

// ═══════════════════════════════════════════════════════════════════════════════
// COUNTDOWN TIMER (shared)
// ═══════════════════════════════════════════════════════════════════════════════

const _timerRefs = {};

function _startCountdown(timerElId, btnId, seconds, refKey) {
  if (_timerRefs[refKey]) clearInterval(_timerRefs[refKey]);

  let remaining = seconds;
  const timerEl = document.getElementById(timerElId);
  const btn = document.getElementById(btnId);
  if (btn) btn.disabled = true;
  if (timerEl) timerEl.textContent = remaining;

  _timerRefs[refKey] = setInterval(() => {
    remaining -= 1;
    if (timerEl) timerEl.textContent = remaining;
    if (remaining <= 0) {
      clearInterval(_timerRefs[refKey]);
      _timerRefs[refKey] = null;
      if (btn) btn.disabled = false;
    }
  }, 1000);
}

// ═══════════════════════════════════════════════════════════════════════════════
// OTP DIGIT AUTO-TAB
// ═══════════════════════════════════════════════════════════════════════════════

function _setupOtpDigits(selector, verifyFn) {
  const digits = document.querySelectorAll(selector);
  digits.forEach((input, idx) => {
    input.addEventListener('input', (e) => {
      const val = e.target.value.replace(/\D/g, '');
      e.target.value = val.slice(-1);
      if (val && idx < digits.length - 1) digits[idx + 1].focus();
      if (idx === digits.length - 1 && val) verifyFn();
    });
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Backspace' && !e.target.value && idx > 0) digits[idx - 1].focus();
      if (e.key === 'ArrowLeft'  && idx > 0) digits[idx - 1].focus();
      if (e.key === 'ArrowRight' && idx < digits.length - 1) digits[idx + 1].focus();
    });
    input.addEventListener('paste', (e) => {
      e.preventDefault();
      const pasted = (e.clipboardData || window.clipboardData).getData('text').replace(/\D/g, '');
      pasted.split('').slice(0, 6).forEach((ch, i) => { if (digits[i]) digits[i].value = ch; });
      const next = Math.min(pasted.length, digits.length - 1);
      digits[next].focus();
      if (pasted.length >= 6) verifyFn();
    });
  });
}

// ═══════════════════════════════════════════════════════════════════════════════
// STEP NAVIGATION
// ═══════════════════════════════════════════════════════════════════════════════

function goToStep(step) {
  if (step === 2 && !validateStep1()) return;
  if (step === 3 && !validateStep2()) return;
  if (step === 4) buildReview();

  document.querySelectorAll('.form-step').forEach(el => el.classList.remove('active'));
  const target = document.getElementById(`formStep${step}`);
  if (target) target.classList.add('active');
  currentStep = step;

  for (let i = 1; i <= 4; i++) {
    const stepEl = document.getElementById(`step-${i}`);
    if (!stepEl) continue;
    stepEl.classList.remove('active', 'done');
    if (i < step)  stepEl.classList.add('done');
    if (i === step) stepEl.classList.add('active');
  }
  for (let i = 1; i <= 3; i++) {
    const line = document.getElementById(`line-${i}`);
    if (line) line.classList.toggle('done', i < step);
  }
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function validateStep1() {
  const name = document.getElementById('complainant_name')?.value.trim();
  if (!name || name.length < 2) {
    showToast('Please enter your full name.', 'err');
    document.getElementById('complainant_name')?.focus();
    return false;
  }
  return true;
}

function validateStep2() {
  const desc = document.getElementById('incident_description')?.value.trim();
  if (!desc || desc.length < 20) {
    showToast('Please describe the incident in at least 20 characters.', 'err');
    document.getElementById('incident_description')?.focus();
    return false;
  }
  return true;
}

// ═══════════════════════════════════════════════════════════════════════════════
// LIVE STATS
// ═══════════════════════════════════════════════════════════════════════════════

async function loadLiveStats() {
  try {
    const res  = await fetch('/api/dashboard/live-stats');
    if (!res.ok) return;
    const data = await res.json();
    _setText('statTotal',   data.total_reports_processed?.toLocaleString('en-IN'));
    _setText('statFirs',    data.firs_auto_generated?.toLocaleString('en-IN'));
    _setText('statToday',   data.reports_today?.toLocaleString('en-IN'));
    _setText('statFake',    data.fake_blocked?.toLocaleString('en-IN'));
    _setText('tickerTotal', data.total_reports_processed?.toLocaleString('en-IN'));
  } catch (_) {}
}

function _setText(id, val) {
  const el = document.getElementById(id);
  if (el && val != null) el.textContent = val;
}

// ═══════════════════════════════════════════════════════════════════════════════
// CHARACTER COUNTER
// ═══════════════════════════════════════════════════════════════════════════════

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
      counter.innerHTML = `&#10003; ${len} characters`;
      counter.style.color = 'var(--success)';
    }
  });
}

// ═══════════════════════════════════════════════════════════════════════════════
// FILE UPLOAD DROPZONE
// ═══════════════════════════════════════════════════════════════════════════════

function setupDropzone() {
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('evidence_files');
  if (!dropzone || !fileInput) return;

  dropzone.addEventListener('dragover', e => { e.preventDefault(); dropzone.classList.add('dragover'); });
  dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
  dropzone.addEventListener('drop', e => { e.preventDefault(); dropzone.classList.remove('dragover'); _addFiles(e.dataTransfer.files); });
  fileInput.addEventListener('change', () => _addFiles(fileInput.files));
}

async function _addFiles(files) {
  const MAX_MB  = 25;
  const ALLOWED = ['.jpg','.jpeg','.png','.gif','.bmp','.tiff','.pdf','.txt'];

  for (const file of Array.from(files)) {
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!ALLOWED.includes(ext)) { showToast(`"${file.name}" is not a supported file type.`, 'err'); continue; }
    if (file.size > MAX_MB * 1024 * 1024) { showToast(`"${file.name}" exceeds the 25 MB limit.`, 'err'); continue; }
    if (selectedFiles.find(f => (f.file||f).name === file.name && (f.file||f).size === file.size)) continue;

    const entry = { file, status: 'validating', warning: null };
    selectedFiles.push(entry);
    _renderFileList();

    try {
      const fd = new FormData();
      fd.append('file', file);
      const res = await fetch('/api/reports/validate-evidence', { method: 'POST', body: fd });
      const data = await res.json();
      if (data.blocked) {
        selectedFiles = selectedFiles.filter(e => e !== entry);
        _renderFileList();
        _showFileError(file.name, data.warnings[0]);
        continue;
      } else if (data.warnings && data.warnings.length > 0) {
        entry.status = 'warning'; entry.warning = data.warnings[0];
      } else {
        entry.status = 'ok';
      }
    } catch (_) { entry.status = 'ok'; }
    _renderFileList();
  }
}

function _showFileError(filename, message) {
  const container = document.getElementById('fileList');
  if (!container) return;
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
    const file   = entry.file || entry;
    const status = entry.status || 'ok';
    const warning = entry.warning || null;
    const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
    const statusIcon = status === 'validating' ? '<span style="color:var(--gray-400);font-size:11px">Checking...</span>'
                     : status === 'warning'    ? '<span style="color:var(--saffron);font-size:11px;font-weight:600">&#9888; Warning</span>'
                     : '<span style="color:var(--success);font-size:11px">&#10003; Valid</span>';
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

function removeFile(idx) { selectedFiles.splice(idx, 1); _renderFileList(); }
function _getActualFiles() { return selectedFiles.map(e => e.file || e); }

// ═══════════════════════════════════════════════════════════════════════════════
// REVIEW BUILDER
// ═══════════════════════════════════════════════════════════════════════════════

function buildReview() {
  const fields = {
    'Full Name':     document.getElementById('complainant_name')?.value,
    'Mobile':        document.getElementById('complainant_phone')?.value || '—',
    'Email':         document.getElementById('complainant_email')?.value || '—',
    'Address':       document.getElementById('complainant_address')?.value || '—',
    'Incident Date': document.getElementById('incident_date')?.value || '—',
    'Location':      document.getElementById('incident_location')?.value || '—',
  };
  const desc      = document.getElementById('incident_description')?.value || '';
  const fileCount = selectedFiles.length;
  const actualFiles = _getActualFiles();
  const rows = Object.entries(fields).map(([k, v]) =>
    `<tr><td>${escapeHtml(k)}</td><td>${escapeHtml(v || '—')}</td></tr>`
  ).join('');
  document.getElementById('reviewContent').innerHTML = `
    <table class="review-table" style="margin-bottom:14px">${rows}</table>
    <div style="margin-bottom:12px">
      <div style="font-size:11px;color:var(--gray-400);font-weight:600;text-transform:uppercase;margin-bottom:6px">Incident Description</div>
      <div style="background:var(--gray-50);border:1px solid var(--gray-200);padding:12px 14px;border-radius:3px;font-size:13px;line-height:1.7">${escapeHtml(desc)}</div>
    </div>
    <div style="background:var(--gov-blue-lt);border:1px solid #c3d4e8;padding:10px 14px;border-radius:3px;font-size:12px;color:var(--gov-blue)">
      <strong>${fileCount} evidence file${fileCount !== 1 ? 's' : ''} attached</strong>
      ${fileCount > 0 ? ' — ' + actualFiles.map(f => escapeHtml(f.name)).join(', ') : ''}
    </div>`;
}

// ═══════════════════════════════════════════════════════════════════════════════
// FORM SUBMISSION
// ═══════════════════════════════════════════════════════════════════════════════

function setupFormSubmit() {
  const form = document.getElementById('reportForm');
  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    // Double-check both OTPs are present
    if (!phoneOtpToken) {
      showToast('Mobile number verification is required.', 'err');
      return;
    }
    if (!emailOtpToken) {
      showToast('Email verification is required.', 'err');
      return;
    }

    const submitBtn = document.getElementById('submitBtn');
    submitBtn.disabled = true;
    showLoading(true, 'Connecting to server...');

    // Pre-warm: ping health endpoint to wake Render from sleep before heavy request
    try {
      showLoading(true, 'Connecting to server...');
      const warmStart = Date.now();
      await fetch('/api/health', { signal: AbortSignal.timeout(45000) });
      const warmMs = Date.now() - warmStart;
      if (warmMs > 4000) {
        // Server was sleeping — wait longer for workers to fully initialise
        showLoading(true, 'Server waking up, please wait...');
        await new Promise(r => setTimeout(r, 8000));
      }
    } catch (_) { /* ignore — proceed anyway */ }

    showLoading(true, 'Uploading your complaint...');

    const formData = new FormData();

    // Attach BOTH OTP session tokens
    formData.append('phone_otp_token',   phoneOtpToken);
    formData.append('otp_session_token', emailOtpToken);
    if (digilockerSessionToken) formData.append('digilocker_session_token', digilockerSessionToken);

    formData.append('complainant_name',     document.getElementById('complainant_name').value);
    formData.append('incident_description', document.getElementById('incident_description').value);
    formData.append('complainant_phone',    document.getElementById('complainant_phone').value || '');
    formData.append('complainant_email',    document.getElementById('complainant_email').value || '');
    formData.append('complainant_address',  document.getElementById('complainant_address').value || '');
    formData.append('incident_date',        document.getElementById('incident_date').value || '');
    formData.append('incident_location',    document.getElementById('incident_location').value || '');
    _getActualFiles().forEach(file => formData.append('evidence_files', file));

    const loadingSteps = [
      [800,  'Running OCR on evidence files...'],
      [1600, 'AI semantic analysis in progress...'],
      [2400, 'Running fake report detection...'],
      [3200, 'Extracting entities for Complaint Report...'],
      [4000, 'Generating Complaint Report PDF...'],
    ];
    loadingSteps.forEach(([delay, msg]) => setTimeout(() => setLoadingText(msg), delay));

    // Submit with auto-retry — if server is starting up (503/502) retry up to 3×
    const MAX_RETRIES = 3;
    let lastErr = null;

    for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
      try {
        if (attempt > 1) {
          showLoading(true, `Server starting up… retrying (${attempt}/${MAX_RETRIES})`);
          await new Promise(r => setTimeout(r, 18000)); // wait 18 s before retry
        }

        const response = await fetch('/api/reports/submit', { method: 'POST', body: formData });

        if (response.status === 503 || response.status === 502) {
          // Server not ready — retry
          lastErr = new Error(`Server not ready (${response.status}). Retrying…`);
          continue;
        }

        if (!response.ok) {
          // Real error — parse and show immediately, no retry
          let detail = `Server error (${response.status}). Please try again.`;
          try {
            const text = await response.text();
            if (text && text.trim().startsWith('{')) {
              const errJson = JSON.parse(text);
              detail = errJson.detail || detail;
            }
          } catch (_) {}
          throw new Error(detail);
        }

        const data = await response.json();
        showLoading(false);
        displayResult(data);
        submittedReportId = data.id;
        lastErr = null;
        break; // success

      } catch (err) {
        if (err.message && err.message.includes('Retrying')) {
          lastErr = err;
          continue;
        }
        // Non-retriable error
        showLoading(false);
        submitBtn.disabled = false;
        showToast('Submission failed: ' + err.message, 'err');
        lastErr = null;
        break;
      }
    }

    if (lastErr) {
      // All retries exhausted
      showLoading(false);
      submitBtn.disabled = false;
      showToast('Server is temporarily unavailable. Please wait 1 minute and try again.', 'err');
    }
  });
}

// ═══════════════════════════════════════════════════════════════════════════════
// RESULT DISPLAY
// ═══════════════════════════════════════════════════════════════════════════════

function displayResult(data) {
  document.getElementById('reportForm').style.display = 'none';
  const stepProgress = document.querySelector('.step-progress');
  if (stepProgress) stepProgress.style.display = 'none';
  document.getElementById('result-section').style.display = 'block';

  submittedReportId = data.id;
  _applyResultData(data);

  document.querySelector('.result-wrap')?.scrollIntoView({ behavior: 'smooth' });

  // If still PROCESSING, poll until AI analysis is complete
  if (!data.risk_level || data.status === 'PROCESSING') {
    _pollForAnalysis(data.case_number, data.id);
  } else if (data.case_number) {
    _pollForFir(data.case_number, data.id);
  }
}

function _applyResultData(data) {
  const isProcessing = !data.risk_level || data.status === 'PROCESSING';
  const risk = (data.risk_level || 'pending').toLowerCase();
  const head = document.getElementById('resultHead');
  if (head) head.className = `result-head ${isProcessing ? 'processing' : risk}`;

  document.getElementById('resultBadge').textContent      = isProcessing ? 'Complaint Received — Analysing…' : 'Complaint Registered';
  document.getElementById('resultCaseNumber').textContent = data.case_number || '—';
  document.getElementById('resultStatusMsg').textContent  = isProcessing
    ? 'Your complaint has been received. AI analysis is in progress — this page will update automatically.'
    : (risk === 'high'   ? 'High-risk threat detected. Complaint Report auto-registered. Police notified.' :
       risk === 'medium' ? 'Medium-risk case. Under priority review.' :
                           'Complaint submitted successfully. Under standard review.');

  document.getElementById('resultRiskLevel').textContent = isProcessing ? 'Analysing…' : (data.risk_level || '—');
  document.getElementById('resultRiskLevel').style.color =
    isProcessing ? 'var(--gray-400)' :
    risk === 'high' ? 'var(--red)' : risk === 'medium' ? 'var(--saffron)' : 'var(--success)';

  document.getElementById('resultCrimeCategory').textContent = isProcessing ? 'Analysing…' : (data.crime_category || '—');

  const firStatusEl = document.getElementById('resultFirStatus');
  if (firStatusEl) {
    const shouldHaveFir = ['high', 'medium'].includes(risk) && data.fake_recommendation !== 'REJECT';
    firStatusEl.textContent = isProcessing
      ? 'Generating after AI analysis…'
      : (data.fir_path ? 'Complaint Report Ready ✅'
          : shouldHaveFir ? 'Complaint Report generating… (~1 min)' : 'Pending Officer Review');
  }

  const auth    = data.authenticity_score || 0;
  const authPct = (auth * 100).toFixed(0);
  document.getElementById('resultAuthenticity').textContent = isProcessing ? 'Analysing…'
    : (data.fake_recommendation === 'GENUINE' ? `Genuine (${authPct}%)`
    : data.fake_recommendation === 'REVIEW'  ? `Under Review (${authPct}%)`
    : data.is_flagged_fake                   ? `Flagged (${authPct}%)` : `${authPct}%`);

  const authBar = document.getElementById('authBar');
  if (authBar && !isProcessing) {
    const authColor = auth > 0.65 ? 'var(--success)' : auth > 0.45 ? 'var(--saffron)' : 'var(--red)';
    authBar.style.width      = authPct + '%';
    authBar.style.background = authColor;
  }

  document.getElementById('resultAiSummary').textContent = isProcessing
    ? 'AI is analysing your complaint. Results will appear here in 30–60 seconds…'
    : (data.ai_summary || 'Analysis complete.');
  document.getElementById('resultHash').textContent = data.content_hash || 'N/A';

  // Show download button if FIR already ready
  const dlBtn = document.getElementById('downloadFirBtn');
  if (dlBtn) {
    if (data.fir_path) {
      dlBtn.style.display = 'inline-flex';
      dlBtn.onclick = downloadComplaintReport;
    } else {
      dlBtn.style.display = 'none';
    }
  }
}

/** Poll every 10 s until AI analysis fields are populated */
function _pollForAnalysis(caseNumber, reportId) {
  let attempts = 0;
  const MAX = 24;   // 24 × 10 s = 4 min max
  const iv = setInterval(async () => {
    try {
      attempts++;
      const res = await fetch(`/api/reports/track/${caseNumber}`);
      if (!res.ok) return;
      const data = await res.json();

      if (data.risk_level && data.status !== 'PROCESSING') {
        clearInterval(iv);
        submittedReportId = reportId || submittedReportId;
        _applyResultData(data);
        showToast('✅ AI analysis complete!', 'ok');
        // Continue polling for FIR if needed
        _pollForFir(caseNumber, reportId);
      } else if (attempts >= MAX) {
        clearInterval(iv);
        showToast('Analysis is taking longer than expected. Refresh the page later.', 'err');
      }
    } catch (_) {}
  }, 10000);
}

/** Poll every 15 s until FIR PDF is generated */
function _pollForFir(caseNumber, reportId) {
  let attempts = 0;
  const MAX = 12;   // 12 × 15 s = 3 min
  const iv = setInterval(async () => {
    try {
      attempts++;
      const res = await fetch(`/api/reports/track/${caseNumber}`);
      if (!res.ok) return;
      const data = await res.json();

      if (data.fir_path) {
        clearInterval(iv);
        submittedReportId = reportId || submittedReportId;
        const firStatusEl = document.getElementById('resultFirStatus');
        if (firStatusEl) firStatusEl.textContent = 'Complaint Report Ready ✅';
        const dlBtn = document.getElementById('downloadFirBtn');
        if (dlBtn) { dlBtn.style.display = 'inline-flex'; dlBtn.onclick = downloadComplaintReport; }
        showToast('✅ Complaint Report PDF is ready — click Download!', 'ok');
      } else if (attempts >= MAX) {
        clearInterval(iv);
      }
    } catch (_) {}
  }, 15000);
}

function downloadComplaintReport() {
  if (!submittedReportId) { showToast('No report ID found.', 'err'); return; }
  const link = document.createElement('a');
  link.href     = `/api/reports/${submittedReportId}/fir/download`;
  link.download = `ComplaintReport_${submittedReportId}.pdf`;
  link.target   = '_blank';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  showToast('Downloading Complaint Report PDF...', 'ok');
}

function submitAnother() { location.reload(); }

// ═══════════════════════════════════════════════════════════════════════════════
// UTILITIES
// ═══════════════════════════════════════════════════════════════════════════════

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
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// ═══════════════════════════════════════════════════════════════════════════════
// INIT
// ═══════════════════════════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {
  // Setup phone OTP digit auto-tab
  _setupOtpDigits('.phone-otp-digit', verifyPhoneOTP);
  // Setup email OTP digit auto-tab
  _setupOtpDigits('.otp-digit', verifyOTP);

  _setupCharCounter();
  setupDropzone();
  setupFormSubmit();
  loadLiveStats();
  setInterval(loadLiveStats, 30000);

  // Keep-alive: ping server every 8 min so Render free tier doesn't sleep
  // while the user is filling out the complaint form (takes 5-15 minutes)
  setInterval(() => {
    fetch('/api/health').catch(() => {});
  }, 8 * 60 * 1000);

  // Initial check (both not verified)
  _checkBothVerified();
});
