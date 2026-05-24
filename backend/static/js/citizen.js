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
let phoneOtpToken  = null;   // session token after phone SMS OTP verified
let emailOtpToken  = null;   // session token after email OTP verified
let digilockerSessionToken = null;
let digilockerProfile = null;
let verifiedEmail = null;
let verifiedPhone = null;
let resendCountdownTimer = null;
let phoneResendCountdownTimer = null;
let _dlPopupTimer = null;

// ── DigiLocker optional panel toggle ─────────────────────────────────────────
function toggleDigiLockerPanel() {
  const body   = document.getElementById('dv-opt-body');
  const toggle = document.getElementById('dv-opt-toggle');
  if (!body) return;
  const isOpen = body.style.display !== 'none';
  body.style.display = isOpen ? 'none' : 'block';
  if (toggle) toggle.style.transform = isOpen ? '' : 'rotate(90deg)';
}

// ── Dual verification checker ─────────────────────────────────────────────────
function _checkBothVerified() {
  const phoneOk = !!phoneOtpToken;
  const emailOk = !!emailOtpToken;

  // Update checklist items
  const cp = document.getElementById('dv-check-phone');
  const cc = document.getElementById('dv-cc-phone');
  if (cp) cp.classList.toggle('done', phoneOk);
  if (cc) cc.textContent = phoneOk ? '✓' : '';

  const ce = document.getElementById('dv-check-email');
  const cce = document.getElementById('dv-cc-email');
  if (ce) ce.classList.toggle('done', emailOk);
  if (cce) cce.textContent = emailOk ? '✓' : '';

  const btn = document.getElementById('dv-proceed-btn');
  if (btn) {
    btn.disabled = !(phoneOk && emailOk);
    if (phoneOk && emailOk) {
      btn.textContent = '✅  Both verified — Continue to File Complaint →';
    }
  }
}

function proceedWithBothVerified() {
  const vs = document.getElementById('verify-section');
  if (vs) vs.style.display = 'none';

  // Show verified banner
  const banner = document.getElementById('verifiedBanner');
  if (banner) banner.classList.add('show');
  const bannerTitle = document.getElementById('verifiedBannerTitle');
  if (bannerTitle) bannerTitle.textContent = 'Mobile & Email Verified';
  const ve = document.getElementById('verifiedEmail');
  if (ve) {
    const parts = [];
    if (verifiedPhone) parts.push('+91 ' + verifiedPhone);
    if (verifiedEmail) parts.push(verifiedEmail);
    if (digilockerProfile) parts.push('+ Aadhaar (DigiLocker)');
    ve.textContent = parts.join(' · ') + ' — Identity confirmed';
  }

  // Pre-fill form fields
  const phoneField = document.getElementById('complainant_phone');
  if (phoneField && verifiedPhone) {
    phoneField.value    = verifiedPhone;
    phoneField.readOnly = true;
    phoneField.style.background = 'var(--gray-50)';
    phoneField.title = 'Verified via SMS OTP';
  }
  const emailField = document.getElementById('complainant_email');
  if (emailField && verifiedEmail) {
    emailField.value    = verifiedEmail;
    emailField.readOnly = true;
  }
  // Pre-fill name from DigiLocker if available
  if (digilockerProfile && digilockerProfile.name) {
    const nameField = document.getElementById('complainant_name');
    if (nameField) {
      nameField.value    = digilockerProfile.name;
      nameField.readOnly = true;
      nameField.style.background = 'var(--gray-50)';
      nameField.title    = 'Name verified via Aadhaar DigiLocker';
    }
  }

  document.getElementById('formSection').style.display = 'block';
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ── Mobile Phone OTP Verification ────────────────────────────────────────────

async function sendPhoneOTP() {
  const phoneInput = document.getElementById('phoneNumber');
  const phone = phoneInput ? phoneInput.value.trim().replace(/\D/g, '') : '';

  if (!phone || !/^[6-9]\d{9}$/.test(phone)) {
    if (phoneInput) phoneInput.style.borderColor = 'var(--red)';
    showToast('Enter a valid 10-digit Indian mobile number (starts with 6-9).', 'err');
    if (phoneInput) phoneInput.focus();
    return;
  }
  if (phoneInput) phoneInput.style.borderColor = '';

  const btn = document.getElementById('sendPhoneOtpBtn');
  btn.disabled = true;
  btn.textContent = 'Sending…';

  try {
    const res = await fetch('/api/auth/send-otp', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phone }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed to send OTP');

    document.getElementById('phoneOtpEntryRow').style.display = 'block';
    if (phoneInput) phoneInput.readOnly = true;
    btn.style.display = 'none';

    document.getElementById('p0').focus();
    showToast('OTP sent to your mobile!', 'ok');
    _startPhoneResendCountdown(60);

    // DEV mode: if SMS disabled, OTP is in server logs — show hint
    if (data.dev_note) {
      showToast('⚠ SMS not configured — check server terminal for OTP', 'err');
    }

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
    document.getElementById('p0').focus();
    return;
  }

  const phone = document.getElementById('phoneNumber').value.trim().replace(/\D/g, '');
  const btn = document.getElementById('verifyPhoneOtpBtn');
  btn.disabled = true;
  btn.textContent = 'Verifying…';

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

    if (phoneResendCountdownTimer) clearInterval(phoneResendCountdownTimer);

    // Collapse phone panel to verified state
    const panel = document.getElementById('dvp-phone');
    if (panel) panel.classList.add('dv-done');
    const badge = document.getElementById('dv-badge-phone');
    if (badge) { badge.textContent = '✓ VERIFIED'; badge.className = 'dv-badge dv-badge-ok'; }
    const doneMsg = document.getElementById('dvp-phone-done');
    const doneTxt = document.getElementById('dv-phone-done-text');
    if (doneTxt) doneTxt.textContent = '+91 ' + phone + ' — Verified via SMS OTP';
    if (doneMsg) doneMsg.style.display = 'block';

    showToast('✓ Mobile number verified!', 'ok');
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
  if (btn.disabled) return;
  const phone = document.getElementById('phoneNumber').value.trim().replace(/\D/g, '');
  btn.disabled = true;
  try {
    const res = await fetch('/api/auth/send-otp', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phone }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed to resend');
    ['p0','p1','p2','p3','p4','p5'].forEach(id => {
      const el = document.getElementById(id); if (el) el.value = '';
    });
    document.getElementById('p0').focus();
    showToast('New OTP sent to your mobile!', 'ok');
    _startPhoneResendCountdown(60);
  } catch (err) {
    showToast(err.message, 'err');
    btn.disabled = false;
  }
}

function resetPhoneOtpFlow() {
  const phoneInput = document.getElementById('phoneNumber');
  if (phoneInput) { phoneInput.readOnly = false; phoneInput.value = ''; phoneInput.focus(); }
  document.getElementById('phoneOtpEntryRow').style.display = 'none';
  const sendBtn = document.getElementById('sendPhoneOtpBtn');
  if (sendBtn) { sendBtn.style.display = ''; sendBtn.disabled = false; sendBtn.textContent = 'Send OTP'; }
  const verifyBtn = document.getElementById('verifyPhoneOtpBtn');
  if (verifyBtn) { verifyBtn.disabled = false; verifyBtn.textContent = 'Verify OTP'; }
  ['p0','p1','p2','p3','p4','p5'].forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
  if (phoneResendCountdownTimer) clearInterval(phoneResendCountdownTimer);
  const rb = document.getElementById('phoneResendBtn');
  if (rb) rb.disabled = true;
  const rt = document.getElementById('phoneResendTimer');
  if (rt) rt.textContent = '60';
}

function _startPhoneResendCountdown(seconds) {
  if (phoneResendCountdownTimer) clearInterval(phoneResendCountdownTimer);
  let remaining = seconds;
  const timerEl = document.getElementById('phoneResendTimer');
  const resendBtn = document.getElementById('phoneResendBtn');
  if (resendBtn) resendBtn.disabled = true;
  if (timerEl) timerEl.textContent = remaining;
  phoneResendCountdownTimer = setInterval(() => {
    remaining -= 1;
    if (timerEl) timerEl.textContent = remaining;
    if (remaining <= 0) {
      clearInterval(phoneResendCountdownTimer);
      phoneResendCountdownTimer = null;
      if (resendBtn) resendBtn.disabled = false;
    }
  }, 1000);
}

// ── DigiLocker Aadhaar Verification ──────────────────────────────────────────

async function openDigiLockerPopup() {
  const btn = document.getElementById('dlVerifyBtn');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `
      <div class="dl-logo-box">🔐</div>
      <div class="dl-btn-text">
        <strong>Opening DigiLocker…</strong>
        <span>Please allow the popup and complete Aadhaar login</span>
      </div>`;
  }

  try {
    // Fetch the auth URL from backend
    const res = await fetch('/api/digilocker/auth-url');
    if (!res.ok) throw new Error('Could not generate DigiLocker authorization URL');
    const data = await res.json();

    // Open popup window (DigiLocker login page or demo callback)
    const popupWidth  = 520;
    const popupHeight = 680;
    const left = Math.round((window.screen.width  - popupWidth)  / 2);
    const top  = Math.round((window.screen.height - popupHeight) / 2);
    const features = `width=${popupWidth},height=${popupHeight},left=${left},top=${top},scrollbars=yes,resizable=yes`;

    const popup = window.open(data.auth_url, 'digilocker_auth', features);

    if (!popup || popup.closed) {
      throw new Error('Popup was blocked by your browser. Please allow popups for this site and try again.');
    }

    // Listen for postMessage from the callback page
    _listenForDigiLockerCallback(popup);

  } catch (err) {
    _resetDlBtn();
    showToast(err.message || 'Could not open DigiLocker. Please use Email OTP instead.', 'err');
  }
}

function _listenForDigiLockerCallback(popup) {
  // Handler for postMessage from callback page
  function messageHandler(event) {
    // Only accept messages from our own origin
    if (event.origin !== window.location.origin) return;
    const msg = event.data;

    // Handle both success and error message types from DigiLocker callback
    if (!msg || (msg.type !== 'DIGILOCKER_VERIFIED' && msg.type !== 'DIGILOCKER_ERROR')) return;

    // Clean up
    window.removeEventListener('message', messageHandler);
    if (_dlPopupTimer) { clearInterval(_dlPopupTimer); _dlPopupTimer = null; }
    if (popup && !popup.closed) popup.close();

    if (msg.type === 'DIGILOCKER_ERROR') {
      _resetDlBtn();
      showToast('DigiLocker verification failed: ' + (msg.message || 'Unknown error'), 'err');
      return;
    }

    // ── Success — session_token is inside profile object ──
    const profile = msg.profile || {};
    digilockerSessionToken = profile.session_token || '';
    digilockerProfile      = profile;
    _onDigiLockerVerified(digilockerProfile);
  }

  window.addEventListener('message', messageHandler);

  // Fallback: poll for popup close (user closed without completing)
  _dlPopupTimer = setInterval(() => {
    if (popup && popup.closed) {
      clearInterval(_dlPopupTimer);
      _dlPopupTimer = null;
      window.removeEventListener('message', messageHandler);
      if (!digilockerSessionToken) {
        _resetDlBtn();
        // Don't show error — user may have just closed intentionally
      }
    }
  }, 600);
}

function _onDigiLockerVerified(profile) {
  // Hide unverified panel, show verified card
  const unverifiedPanel = document.getElementById('dlUnverifiedPanel');
  const verifiedCard    = document.getElementById('dlVerifiedCard');
  if (unverifiedPanel) unverifiedPanel.style.display = 'none';
  if (verifiedCard)    verifiedCard.classList.add('show');

  // Fill identity details
  _setText('dlVerifiedName',    profile.name    || 'Verified Citizen');
  _setText('dlVerifiedAadhaar', profile.aadhaar_masked || '—');
  _setText('dlVerifiedDob',     profile.dob     || '—');
  const genderMap = { M: 'Male', F: 'Female', T: 'Transgender' };
  _setText('dlVerifiedGender',  genderMap[profile.gender] || profile.gender || '—');

  showToast('✓ Aadhaar identity verified via DigiLocker! Now complete phone & email OTP.', 'ok');
}

function proceedAfterDigiLocker() {
  // DigiLocker verified — just show toast; proceed button still requires phone+email
  showToast('✓ DigiLocker Aadhaar verified! Now complete phone & email OTP.', 'ok');
}

function _resetDlBtn() {
  const btn = document.getElementById('dlVerifyBtn');
  if (btn) {
    btn.disabled = false;
    btn.innerHTML = `
      <div class="dl-logo-box">🔐</div>
      <div class="dl-btn-text">
        <strong>Verify with DigiLocker</strong>
        <span>Opens the official DigiLocker login in a secure popup window</span>
      </div>
      <div class="dl-arrow">&#8250;</div>`;
  }
}

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

    emailOtpToken = data.session_token;
    verifiedEmail = email;

    if (resendCountdownTimer) clearInterval(resendCountdownTimer);

    // Collapse email panel to verified state
    const panel = document.getElementById('dvp-email');
    if (panel) panel.classList.add('dv-done');
    const badge = document.getElementById('dv-badge-email');
    if (badge) { badge.textContent = '✓ VERIFIED'; badge.className = 'dv-badge dv-badge-ok'; }
    const doneMsg = document.getElementById('dvp-email-done');
    const doneTxt = document.getElementById('dv-email-done-text');
    if (doneTxt) doneTxt.textContent = email + ' — Verified via OTP';
    if (doneMsg) doneMsg.style.display = 'block';

    // Pre-fill email field immediately
    const emailField = document.getElementById('complainant_email');
    if (emailField) { emailField.value = email; }

    showToast('✓ Email verified!', 'ok');
    _checkBothVerified();

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

  // Build identity verification badge — always show both phone + email
  let idVerifyBadge = '';
  const phoneLine = verifiedPhone ? `✅ Mobile +91 ${escapeHtml(verifiedPhone)} — SMS OTP` : '';
  const emailLine = verifiedEmail ? `✅ Email ${escapeHtml(verifiedEmail)} — OTP` : '';
  const dlLine    = (digilockerSessionToken && digilockerProfile)
    ? `🔒 Aadhaar ${escapeHtml(digilockerProfile.aadhaar_masked || '')} — DigiLocker Verified` : '';

  idVerifyBadge = `
    <div style="background:#f0fdf4;border:1.5px solid #86efac;border-radius:5px;padding:10px 14px;margin-bottom:12px;font-size:12px;">
      <div style="font-weight:700;color:#14532d;margin-bottom:6px;">Identity Verification</div>
      <div style="display:flex;flex-direction:column;gap:4px;font-size:12px;color:#166534">
        ${phoneLine ? `<span>${phoneLine}</span>` : ''}
        ${emailLine ? `<span>${emailLine}</span>` : ''}
        ${dlLine    ? `<span>${dlLine}</span>`    : ''}
      </div>
    </div>`;

  document.getElementById('reviewContent').innerHTML = `
    ${idVerifyBadge}
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

    // Send both phone + email OTP tokens (both required by backend)
    if (phoneOtpToken)  formData.append('phone_otp_token', phoneOtpToken);
    if (emailOtpToken)  formData.append('otp_session_token', emailOtpToken);
    if (digilockerSessionToken) formData.append('digilocker_session_token', digilockerSessionToken);

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
  _setupPhoneOtpDigits();
  _setupCharCounter();
  setupDropzone();
  setupFormSubmit();
  loadLiveStats();
  setInterval(loadLiveStats, 30000);

  // Default: DigiLocker tab active
  const dlTab = document.getElementById('vt-digilocker');
  if (dlTab) dlTab.style.display = '';
});

function _setupPhoneOtpDigits() {
  const digits = document.querySelectorAll('.phone-otp-digit');
  digits.forEach((input, idx) => {
    input.addEventListener('input', (e) => {
      const val = e.target.value.replace(/\D/g, '');
      e.target.value = val.slice(-1);
      if (val && idx < digits.length - 1) digits[idx + 1].focus();
      if (idx === digits.length - 1 && val) verifyPhoneOTP();
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
      if (pasted.length >= 6) verifyPhoneOTP();
    });
  });
}
