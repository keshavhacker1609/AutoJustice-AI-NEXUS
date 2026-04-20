/**
 * AutoJustice AI NEXUS — Police Command Dashboard JS
 * Handles stats loading, charts, case tables, modal, and audit log.
 */

let dailyChart, riskChart, categoryChart;
let allCases = [];
let currentFilter = null;
let refreshInterval = null;

// ── Init ────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  updateClock();
  setInterval(updateClock, 1000);
  loadDashboard();
  loadAllCases();
  refreshInterval = setInterval(loadDashboard, 30000); // Auto-refresh every 30s
});

function updateClock() {
  const el = document.getElementById('topbarTime');
  if (el) {
    const now = new Date();
    el.textContent = now.toLocaleTimeString('en-IN', { hour12: false }) + ' IST';
  }
}

// ── View Navigation ─────────────────────────────────────────────────────────

const VIEW_CONFIG = {
  'overview':     { title: 'Command Overview',       sub: 'Real-time cybercrime intelligence dashboard' },
  'cases':        { title: 'All Cases',              sub: 'Full case registry with filters' },
  'high-risk':    { title: 'High Risk Cases',        sub: 'Immediate action required' },
  'fake-reports': { title: 'Flagged Reports',        sub: 'AI authenticity concerns — review before action' },
  'firs':         { title: 'Complaint Reports',      sub: 'Auto-generated Preliminary Complaint Reports' },
  'audit':        { title: 'Audit Log',              sub: 'Immutable system action trail — Section 65B' },
  'forensics':    { title: 'Image Forensics',        sub: 'Tamper detection & evidence integrity analysis' },
  'trust':        { title: 'Reporter Trust',         sub: 'Submission history & reputation scoring' },
};

function authHeaders() {
  const token = localStorage.getItem('aj_token');
  return token ? { 'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json' } : {};
}

function showView(name) {
  document.querySelectorAll('.view').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.sidebar-nav-item').forEach(el => el.classList.remove('active'));

  const viewEl = document.getElementById(`view-${name}`);
  const navEl  = document.getElementById(`nav-${name}`);

  if (viewEl) viewEl.classList.add('active');
  if (navEl)  navEl.classList.add('active');

  const cfg = VIEW_CONFIG[name] || {};
  document.getElementById('topbarTitle').textContent = cfg.title || name;
  document.getElementById('topbarSub').textContent   = cfg.sub   || '';

  // Lazy-load content for specific views
  if (name === 'high-risk')    loadFilteredCases('HIGH', 'highRiskBody', 8);
  if (name === 'fake-reports') loadFakeReports();
  if (name === 'firs')         loadFIRRegistry();
  if (name === 'audit')        loadAuditLog();
  if (name === 'forensics')    loadForensicsSummary();
  if (name === 'trust')        loadTrustSummary();
}

// ── Dashboard Stats & Charts ─────────────────────────────────────────────────

async function loadDashboard() {
  try {
    const res  = await fetch('/api/dashboard/stats', { headers: authHeaders() });
    const data = await res.json();

    // Station name
    document.getElementById('sidebarStation').textContent =
      'Cyber Crime Police Station';

    // Stat cards
    setEl('statTotal',   data.total_reports);
    setEl('statHigh',    data.risk_distribution?.high || 0);
    setEl('statPending', data.pending_triage);
    setEl('statCRs',    data.firs_generated);
    setEl('statFake',    data.fake_flagged);
    setEl('statAuthScore', `Avg auth: ${(data.avg_authenticity_score * 100).toFixed(0)}%`);

    // Sidebar badges
    setEl('sidebarTotalBadge', data.total_reports);
    setEl('sidebarHighBadge',  data.risk_distribution?.high || 0);
    setEl('sidebarFakeBadge',  data.fake_flagged);
    setEl('sidebarCRBadge',   data.firs_generated);

    // High risk today alert
    const highToday = data.high_risk_today || 0;
    const alertEl = document.getElementById('highRiskAlert');
    if (highToday > 0) {
      alertEl.style.display = 'flex';
      setEl('highRiskTodayCount', highToday);
    } else {
      alertEl.style.display = 'none';
    }

    // Big auth score
    setEl('bigAuthScore', `${(data.avg_authenticity_score * 100).toFixed(0)}%`);

    // Auth breakdown
    const breakdownEl = document.getElementById('authBreakdown');
    if (breakdownEl) {
      const dist = data.risk_distribution || {};
      const total = data.total_reports || 1;
      breakdownEl.innerHTML = [
        { label: 'High Risk Cases',    count: dist.high || 0,    color: 'var(--red)' },
        { label: 'Medium Risk Cases',  count: dist.medium || 0,  color: 'var(--orange)' },
        { label: 'Low Risk Cases',     count: dist.low || 0,     color: 'var(--success)' },
        { label: 'Fake Flagged',       count: data.fake_flagged, color: '#7c3aed' },
      ].map(item => `
        <div>
          <div style="display:flex; justify-content:space-between; font-size:12px; margin-bottom:4px">
            <span>${item.label}</span>
            <strong>${item.count}</strong>
          </div>
          <div class="score-bar">
            <div class="score-fill" style="width:${(item.count/total*100).toFixed(1)}%; background:${item.color}"></div>
          </div>
        </div>
      `).join('');
    }

    // Charts
    renderDailyChart(data.daily_submissions || []);
    renderRiskChart(data.risk_distribution || {});
    renderCategoryChart(data.top_crime_categories || []);

    // Recent cases table
    renderCasesTable(data.recent_reports || [], 'recentCasesBody');

  } catch (err) {
    console.error('Dashboard load error:', err);
    showToast('Failed to load dashboard data.', 'error');
  }
}

// ── Charts ───────────────────────────────────────────────────────────────────

function renderDailyChart(data) {
  const ctx = document.getElementById('dailyChart');
  if (!ctx) return;

  const labels = data.map(d => {
    const date = new Date(d.date);
    return date.toLocaleDateString('en-IN', { month: 'short', day: 'numeric' });
  });

  if (dailyChart) dailyChart.destroy();
  dailyChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        {
          label: 'High',
          data: data.map(d => d.high),
          backgroundColor: 'rgba(192,57,43,0.8)',
          borderRadius: 4,
        },
        {
          label: 'Medium',
          data: data.map(d => d.medium),
          backgroundColor: 'rgba(217,119,6,0.8)',
          borderRadius: 4,
        },
        {
          label: 'Low',
          data: data.map(d => d.low),
          backgroundColor: 'rgba(22,163,74,0.8)',
          borderRadius: 4,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { position: 'top', labels: { font: { size: 11 } } } },
      scales: {
        x: { stacked: true, grid: { display: false }, ticks: { font: { size: 10 } } },
        y: { stacked: true, beginAtZero: true, ticks: { precision: 0, font: { size: 10 } } },
      },
    },
  });
}

function renderRiskChart(dist) {
  const ctx = document.getElementById('riskChart');
  if (!ctx) return;

  if (riskChart) riskChart.destroy();
  riskChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['High Risk', 'Medium Risk', 'Low Risk', 'Pending'],
      datasets: [{
        data: [dist.high || 0, dist.medium || 0, dist.low || 0, dist.pending || 0],
        backgroundColor: ['#c0392b', '#d97706', '#16a34a', '#1565c0'],
        borderWidth: 2,
        borderColor: 'white',
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '65%',
      plugins: {
        legend: {
          position: 'bottom',
          labels: { font: { size: 11 }, padding: 12, usePointStyle: true },
        },
      },
    },
  });
}

function renderCategoryChart(categories) {
  const ctx = document.getElementById('categoryChart');
  if (!ctx) return;

  if (categoryChart) categoryChart.destroy();
  categoryChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: categories.map(c => c.category),
      datasets: [{
        label: 'Reports',
        data: categories.map(c => c.count),
        backgroundColor: [
          '#1565c0','#c0392b','#d97706','#16a34a',
          '#7c3aed','#0891b2','#db2777','#ea580c',
        ],
        borderRadius: 6,
      }],
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { beginAtZero: true, ticks: { precision: 0, font: { size: 10 } }, grid: { color: '#f1f5f9' } },
        y: { ticks: { font: { size: 10 } }, grid: { display: false } },
      },
    },
  });
}

// ── Case Tables ───────────────────────────────────────────────────────────────

async function loadAllCases() {
  try {
    const res = await fetch('/api/reports/?limit=200', { headers: authHeaders() });
    allCases = await res.json();
    renderCasesTable(allCases, 'allCasesBody');
  } catch (err) {
    console.error('Cases load error:', err);
  }
}

async function loadFilteredCases(riskLevel, targetId, limit = 100) {
  try {
    const url = riskLevel ? `/api/reports/?risk_level=${riskLevel}&limit=${limit}` : `/api/reports/?limit=${limit}`;
    const res = await fetch(url, { headers: authHeaders() });
    const data = await res.json();
    renderCasesTable(data, targetId);
  } catch (err) {
    document.getElementById(targetId).innerHTML = `<tr><td colspan="8" class="loading-text">Failed to load cases.</td></tr>`;
  }
}

async function loadFakeReports() {
  try {
    const res  = await fetch('/api/reports/?limit=200', { headers: authHeaders() });
    const data = await res.json();
    const fakes = data.filter(r => r.is_flagged_fake || r.fake_recommendation === 'REJECT' || r.fake_recommendation === 'REVIEW');
    renderFakeTable(fakes, 'fakeReportsBody');
  } catch (err) {
    document.getElementById('fakeReportsBody').innerHTML = `<tr><td colspan="7" class="loading-text">Failed to load.</td></tr>`;
  }
}

async function loadFIRRegistry() {
  try {
    const res  = await fetch('/api/reports/?status=COMPLAINT_REGISTERED&limit=200', { headers: authHeaders() });
    const data = await res.json();
    renderComplaintTable(data, 'firsBody');
  } catch (err) {
    document.getElementById('firsBody').innerHTML = `<tr><td colspan="6" class="loading-text">Failed to load.</td></tr>`;
  }
}

function filterCases(riskLevel, btn) {
  document.querySelectorAll('.table-filters .filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  currentFilter = riskLevel;
  const filtered = riskLevel ? allCases.filter(r => r.risk_level === riskLevel) : allCases;
  renderCasesTable(filtered, 'allCasesBody');
}

function renderCasesTable(cases, targetId) {
  const tbody = document.getElementById(targetId);
  if (!tbody) return;

  if (!cases || cases.length === 0) {
    tbody.innerHTML = `
      <tr><td colspan="8">
        <div class="no-data">
          <div class="no-icon">📭</div>
          <h4>No cases found</h4>
          <p>No reports match the current filter.</p>
        </div>
      </td></tr>`;
    return;
  }

  tbody.innerHTML = cases.map(r => {
    const risk   = r.risk_level || 'PENDING';
    const auth   = r.authenticity_score != null ? `${(r.authenticity_score * 100).toFixed(0)}%` : '—';
    const authColor = r.authenticity_score > 0.65 ? 'var(--success)'
                    : r.authenticity_score > 0.45 ? 'var(--orange)' : 'var(--red)';
    const timeAgo = formatTimeAgo(r.created_at);
    const fakeFlag = r.is_flagged_fake
      ? `<span class="fake-flag">⚠ ${r.fake_recommendation || 'REVIEW'}</span>` : '';

    return `
      <tr>
        <td><span class="case-number">${escapeHtml(r.case_number)}</span></td>
        <td>${escapeHtml(r.complainant_name)}</td>
        <td>
          <span class="risk-badge risk-${risk}">${riskIcon(risk)} ${risk}</span>
          ${r.risk_score ? `<div style="font-size:10px;color:var(--gray-400);margin-top:2px">${(r.risk_score*100).toFixed(0)}%</div>` : ''}
        </td>
        <td>${escapeHtml(r.crime_category || '—')}</td>
        <td><span class="status-badge status-${r.status}">${formatStatus(r.status)}</span></td>
        <td>
          <span style="color:${authColor}; font-weight:600; font-size:13px">${auth}</span>
          ${fakeFlag}
        </td>
        <td style="color:var(--gray-400); font-size:12px">${timeAgo}</td>
        <td>
          <div style="display:flex; gap:4px; flex-wrap:wrap">
            <button class="table-action-btn" onclick="openCase('${r.id}')">View</button>
            <button class="table-action-btn" style="color:var(--blue);border-color:var(--blue)" onclick="showAIExplain('${r.id}','${r.case_number}')" title="Why did AI decide this?">🔍 Explain</button>
            ${r.fir_path
              ? `<button class="table-action-btn download" onclick="downloadComplaintReport('${r.id}')">Download CR</button>`
              : `<button class="table-action-btn" onclick="generateComplaintReport('${r.id}', this)">Gen CR</button>`
            }
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

function renderFakeTable(cases, targetId) {
  const tbody = document.getElementById(targetId);
  if (!tbody) return;

  if (!cases.length) {
    tbody.innerHTML = `<tr><td colspan="7"><div class="no-data"><div class="no-icon">✅</div><h4>No suspicious reports</h4><p>AI has not flagged any reports.</p></div></td></tr>`;
    return;
  }

  tbody.innerHTML = cases.map(r => {
    const auth = r.authenticity_score != null ? `${(r.authenticity_score * 100).toFixed(0)}%` : '—';
    const recColor = r.fake_recommendation === 'REJECT' ? 'var(--red)'
                   : r.fake_recommendation === 'REVIEW' ? 'var(--orange)' : 'var(--success)';
    const flags = (r.fake_flags || []).slice(0, 2).join('; ') || '—';

    return `
      <tr>
        <td><span class="case-number">${escapeHtml(r.case_number)}</span></td>
        <td>${escapeHtml(r.complainant_name)}</td>
        <td style="color:${auth === '—' ? 'var(--gray-400)' : (r.authenticity_score > 0.5 ? 'var(--success)' : 'var(--red)')}; font-weight:600">${auth}</td>
        <td><strong style="color:${recColor}">${r.fake_recommendation || '—'}</strong></td>
        <td style="font-size:11px; color:var(--gray-600); max-width:200px">${escapeHtml(flags)}</td>
        <td style="color:var(--gray-400); font-size:12px">${formatTimeAgo(r.created_at)}</td>
        <td>
          <div style="display:flex; gap:4px">
            <button class="table-action-btn" onclick="openCase('${r.id}')">Review</button>
            <button class="table-action-btn" style="color:var(--red)" onclick="flagFake('${r.id}', this)">Flag</button>
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

function renderComplaintTable(cases, targetId) {
  const tbody = document.getElementById(targetId);
  if (!tbody) return;

  if (!cases.length) {
    tbody.innerHTML = `<tr><td colspan="6"><div class="no-data"><div class="no-icon">📄</div><h4>No Complaints Registered yet</h4></div></td></tr>`;
    return;
  }

  tbody.innerHTML = cases.map(r => `
    <tr>
      <td><span class="case-number">${escapeHtml(r.case_number)}</span></td>
      <td>
        ${escapeHtml(r.complainant_name)}
        ${r.digilocker_verified ? '<span title="DigiLocker Verified" style="margin-left:5px;background:#dcfce7;color:#15803d;font-size:10px;font-weight:700;padding:1px 6px;border-radius:99px;vertical-align:middle;">DL</span>' : ''}
      </td>
      <td><span class="risk-badge risk-${r.risk_level || 'PENDING'}">${riskIcon(r.risk_level)} ${r.risk_level || '—'}</span></td>
      <td>${escapeHtml(r.crime_category || '—')}</td>
      <td style="color:var(--gray-400); font-size:12px">${formatTimeAgo(r.created_at)}</td>
      <td>
        <button class="table-action-btn download" onclick="downloadComplaintReport('${r.id}')">Download Complaint Report</button>
      </td>
    </tr>
  `).join('');
}

// ── Case Detail Modal ─────────────────────────────────────────────────────────

async function openCase(reportId) {
  const modal = document.getElementById('caseModal');
  const body  = document.getElementById('modalBody');

  modal.classList.add('show');
  body.innerHTML = '<div class="loading-text"><div class="spinner"></div></div>';

  try {
    const res  = await fetch(`/api/reports/${reportId}`, { headers: authHeaders() });
    const data = await res.json();

    document.getElementById('modalTitle').textContent = `Case: ${data.case_number}`;
    document.getElementById('modalCaseNumber').textContent =
      `${data.crime_category || 'Unknown'} · ${data.status} · Submitted ${formatTimeAgo(data.created_at)}`;

    const risk = data.risk_level || 'PENDING';
    const auth = data.authenticity_score != null ? `${(data.authenticity_score * 100).toFixed(0)}%` : '—';
    const entities = data.entities || {};
    const bns = data.bns_sections || [];
    const fakeFlags = data.fake_flags || [];
    const evidenceFiles = data.evidence_files || [];

    body.innerHTML = `
      <!-- Status Row -->
      <div style="display:flex; gap:8px; flex-wrap:wrap; margin-bottom:20px">
        <span class="risk-badge risk-${risk}" style="font-size:13px; padding:5px 14px">${riskIcon(risk)} ${risk} RISK</span>
        <span class="status-badge status-${data.status}" style="padding:5px 10px; font-size:12px">${formatStatus(data.status)}</span>
        <span style="background:${data.is_flagged_fake ? '#fff7ed' : '#f0fdf4'}; color:${data.is_flagged_fake ? 'var(--orange)' : 'var(--success)'}; padding:4px 12px; border-radius:999px; font-size:11px; font-weight:700">
          ${data.is_flagged_fake ? '⚠ FLAGGED' : '✓ Not Flagged'} · Auth: ${auth}
        </span>
      </div>

      <!-- Complainant -->
      <div class="detail-section">
        <h4>Complainant</h4>
        <div class="detail-grid">
          <div class="detail-field"><label>Name</label><div class="val">${escapeHtml(data.complainant_name)}</div></div>
          <div class="detail-field"><label>Phone</label><div class="val">${escapeHtml(data.complainant_phone || '—')}</div></div>
          <div class="detail-field"><label>Email</label><div class="val">${escapeHtml(data.complainant_email || '—')}</div></div>
          <div class="detail-field"><label>Address</label><div class="val">${escapeHtml(data.complainant_address || '—')}</div></div>
        </div>
      </div>

      <!-- Incident -->
      <div class="detail-section">
        <h4>Incident Details</h4>
        <div class="detail-grid" style="margin-bottom:10px">
          <div class="detail-field"><label>Date</label><div class="val">${escapeHtml(data.incident_date || '—')}</div></div>
          <div class="detail-field"><label>Location</label><div class="val">${escapeHtml(data.incident_location || '—')}</div></div>
        </div>
        <div class="description-box">${escapeHtml(data.incident_description)}</div>
      </div>

      <!-- AI Analysis -->
      <div class="detail-section">
        <h4>AI Analysis</h4>
        <div class="detail-grid" style="margin-bottom:10px">
          <div class="detail-field"><label>Risk Score</label><div class="val">${data.risk_score ? (data.risk_score * 100).toFixed(0) + '%' : '—'}</div></div>
          <div class="detail-field"><label>Category</label><div class="val">${escapeHtml(data.crime_category || '—')} → ${escapeHtml(data.crime_subcategory || '—')}</div></div>
        </div>
        ${data.ai_summary ? `<div class="description-box" style="font-style:italic">"${escapeHtml(data.ai_summary)}"</div>` : ''}
      </div>

      <!-- Entities -->
      ${Object.keys(entities).length > 0 ? `
      <div class="detail-section">
        <h4>Extracted Entities</h4>
        <div class="entity-grid">
          ${Object.entries(entities).map(([k, v]) =>
            v && (Array.isArray(v) ? v.length > 0 : true)
            ? `<div class="entity-chip"><label>${k.replace('_', ' ')}</label>${escapeHtml(Array.isArray(v) ? v.join(', ') : v)}</div>`
            : ''
          ).join('')}
        </div>
      </div>` : ''}

      <!-- BNS Sections -->
      ${bns.length > 0 ? `
      <div class="detail-section">
        <h4>Applicable Legal Sections</h4>
        <div class="bns-list">${bns.map(s => `<span class="bns-chip">${escapeHtml(s)}</span>`).join('')}</div>
      </div>` : ''}

      <!-- Fake Detection -->
      <div class="detail-section">
        <h4>Fake Report Detection</h4>
        <div class="detail-grid" style="margin-bottom:${fakeFlags.length > 0 ? '10px' : '0'}">
          <div class="detail-field"><label>Authenticity Score</label>
            <div class="val" style="color:${data.authenticity_score > 0.65 ? 'var(--success)' : data.authenticity_score > 0.45 ? 'var(--orange)' : 'var(--red)'}">${auth}</div>
            <div class="score-bar" style="margin-top:6px"><div class="score-fill" style="width:${(data.authenticity_score || 0) * 100}%; background:${data.authenticity_score > 0.65 ? 'var(--success)' : data.authenticity_score > 0.45 ? 'var(--orange)' : 'var(--red)'}"></div></div>
          </div>
          <div class="detail-field"><label>Recommendation</label><div class="val" style="color:${data.fake_recommendation === 'GENUINE' ? 'var(--success)' : data.fake_recommendation === 'REJECT' ? 'var(--red)' : 'var(--orange)'}">${data.fake_recommendation || '—'}</div></div>
        </div>
        ${fakeFlags.length > 0 ? `
          <div class="fake-flags-list">
            ${fakeFlags.map(f => `<div class="fake-flag-item">⚠ ${escapeHtml(f)}</div>`).join('')}
          </div>` : ''}
      </div>

      <!-- Evidence Files -->
      ${evidenceFiles.length > 0 ? `
      <div class="detail-section">
        <h4>Evidence Chain of Custody (${evidenceFiles.length} files)</h4>
        ${evidenceFiles.map(ef => `
          <div style="background:var(--gray-50); padding:10px 12px; border-radius:8px; margin-bottom:6px; font-size:12px">
            <div style="display:flex; justify-content:space-between; margin-bottom:4px">
              <strong>${escapeHtml(ef.original_filename)}</strong>
              <span style="color:var(--gray-400)">${ef.file_type} · OCR: ${ef.ocr_confidence ? (ef.ocr_confidence * 100).toFixed(0) + '%' : '—'}</span>
            </div>
            <div class="hash-box">SHA-256: ${escapeHtml(ef.sha256_hash)}</div>
          </div>
        `).join('')}
      </div>` : ''}

      <!-- Content Hash -->
      <div class="detail-section">
        <h4>Report Integrity Hash (Section 65B)</h4>
        <div class="hash-box">${escapeHtml(data.content_hash || 'Not computed')}</div>
      </div>

      <!-- Image Forensics — Explainable AI breakdown -->
      ${data.forensics_tamper_score != null ? `
      <div class="detail-section">
        <h4>Image Forensics Analysis</h4>
        <div class="detail-grid" style="margin-bottom:12px">
          <div class="detail-field"><label>Overall Tamper Score</label>
            <div class="val" style="font-size:16px; font-weight:700; color:${data.forensics_tamper_score >= 0.55 ? 'var(--red)' : data.forensics_tamper_score >= 0.30 ? 'var(--orange)' : 'var(--success)'}">
              ${(data.forensics_tamper_score * 100).toFixed(0)}%
              <span style="font-size:11px; font-weight:600">${data.forensics_tamper_score >= 0.55 ? ' — Likely Tampered' : data.forensics_tamper_score >= 0.30 ? ' — Suspicious' : ' — Clean'}</span>
            </div>
            <div class="score-bar" style="margin-top:6px"><div class="score-fill" style="width:${data.forensics_tamper_score * 100}%;background:${data.forensics_tamper_score >= 0.55 ? 'var(--red)' : data.forensics_tamper_score >= 0.30 ? 'var(--orange)' : 'var(--success)'}"></div></div>
          </div>
          <div class="detail-field"><label>Reporter Trust Score</label>
            <div class="val" style="font-size:16px; font-weight:700; color:${(data.reporter_trust_score||0) >= 0.65 ? 'var(--success)' : (data.reporter_trust_score||0) >= 0.40 ? 'var(--orange)' : 'var(--red)'}">
              ${data.reporter_trust_score != null ? (data.reporter_trust_score * 100).toFixed(0) + '%' : '—'}
            </div>
            ${data.reporter_trust_score != null ? `<div class="score-bar" style="margin-top:6px"><div class="score-fill" style="width:${(data.reporter_trust_score||0)*100}%;background:${(data.reporter_trust_score||0)>=0.65?'var(--success)':(data.reporter_trust_score||0)>=0.40?'var(--orange)':'var(--red)'}"></div></div>` : ''}
          </div>
        </div>

        <!-- Per-file forensic breakdown -->
        ${(data.evidence_files || []).filter(ef => ef.tamper_score != null).map(ef => {
          const ts = ef.tamper_score || 0;
          const tsColor = ts >= 0.55 ? 'var(--red)' : ts >= 0.30 ? 'var(--orange)' : 'var(--success)';
          const tsLabel = ts >= 0.55 ? 'HIGH SUSPICION' : ts >= 0.30 ? 'MODERATE' : ts >= 0.10 ? 'Low' : 'Clean';
          const tFlags = ef.tamper_flags || [];
          const ela = ef.ela_analysis || {};
          const exif = ef.exif_data || {};
          return `
          <div style="background:var(--gray-50); border:1px solid var(--gray-200); border-radius:8px; padding:12px; margin-bottom:8px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
              <span style="font-size:12px; font-weight:600; color:var(--navy)">${escapeHtml(ef.original_filename)}</span>
              <span style="font-size:11px; font-weight:700; color:${tsColor}; background:${ts>=0.55?'#fdecea':ts>=0.30?'#fff7ed':'#f0fdf4'}; padding:2px 8px; border-radius:4px">${tsLabel} (${(ts*100).toFixed(0)}%)</span>
            </div>
            <!-- Analysis Layers -->
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:6px; margin-bottom:8px;">
              ${ela.mean_diff != null ? `
              <div style="font-size:11px; padding:5px 8px; background:white; border-radius:5px; border:1px solid var(--gray-200)">
                <div style="font-weight:600; color:var(--gray-400); margin-bottom:2px; text-transform:uppercase; font-size:10px">ELA (Error Level Analysis)</div>
                <div style="color:${ela.mean_diff > 15 ? 'var(--red)' : ela.mean_diff > 8 ? 'var(--orange)' : 'var(--success)'}; font-weight:600">
                  ${ela.mean_diff > 15 ? 'Editing artifacts found' : ela.mean_diff > 8 ? 'Minor anomalies' : 'No editing detected'}
                </div>
                <div style="color:var(--gray-400); font-size:10px">diff=${ela.mean_diff?.toFixed(1) || '—'} max=${ela.max_diff || '—'}</div>
              </div>` : ''}
              <div style="font-size:11px; padding:5px 8px; background:white; border-radius:5px; border:1px solid var(--gray-200)">
                <div style="font-weight:600; color:var(--gray-400); margin-bottom:2px; text-transform:uppercase; font-size:10px">EXIF Metadata</div>
                <div style="color:${!exif || Object.keys(exif).length === 0 ? 'var(--orange)' : 'var(--success)'}; font-weight:600">
                  ${!exif || Object.keys(exif).length === 0 ? 'No metadata (suspicious for JPEG)' : (exif.Make ? exif.Make + ' ' + (exif.Model||'') : 'Metadata present')}
                </div>
                ${exif.Software ? `<div style="color:var(--red); font-size:10px">Software: ${escapeHtml(String(exif.Software))}</div>` : ''}
              </div>
            </div>
            ${tFlags.length > 0 ? `
            <div style="display:flex; flex-direction:column; gap:3px;">
              ${tFlags.map(f => `<div style="background:#fff7ed; border-left:2px solid var(--orange); padding:4px 8px; border-radius:0 4px 4px 0; font-size:11px; color:#92400e">${escapeHtml(f)}</div>`).join('')}
            </div>` : `<div style="font-size:11px; color:var(--success); padding:4px 0">No tampering anomalies detected in this file.</div>`}
          </div>`;
        }).join('')}

        ${data.forensics_flags?.length && !data.evidence_files?.some(ef => ef.tamper_score != null) ? `
          <div class="fake-flags-list">${data.forensics_flags.slice(0,4).map(f => `<div class="fake-flag-item">${escapeHtml(f)}</div>`).join('')}</div>` : ''}
      </div>` : ''}

      <!-- DigiLocker Verification Status -->
      ${data.digilocker_verified ? `
      <div style="display:flex;align-items:center;gap:10px;background:#f0fdf4;border:1.5px solid #86efac;border-radius:10px;padding:10px 16px;margin-bottom:8px;">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#16a34a" stroke-width="2.5"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><polyline points="9 12 11 14 15 10"/></svg>
        <span style="font-size:13px;font-weight:600;color:#15803d;">DigiLocker Verified</span>
        <span style="font-size:12px;color:#166534;">— Identity confirmed via Aadhaar: <strong>${escapeHtml(data.digilocker_name || data.complainant_name)}</strong></span>
        <span style="margin-left:auto;font-size:10px;background:#dcfce7;color:#15803d;padding:2px 8px;border-radius:99px;font-weight:600;">MeitY · Govt. of India</span>
      </div>` : `
      <div style="display:flex;align-items:center;gap:10px;background:#fafafa;border:1px solid #e5e7eb;border-radius:10px;padding:10px 16px;margin-bottom:8px;">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#9ca3af" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
        <span style="font-size:12px;color:#6b7280;">Identity not verified via DigiLocker — complainant submitted without Aadhaar verification</span>
      </div>`}

      <!-- Case Notes -->
      <div class="detail-section">
        <h4>Case Notes</h4>
        <div id="notes-${data.id}"><p style="color:var(--gray-400);font-size:12px">Loading notes...</p></div>
      </div>

      <!-- Actions -->
      <div class="modal-actions">
        ${data.fir_path
          ? `<button class="btn btn-primary" onclick="downloadComplaintReport('${data.id}')">Download Complaint Report PDF</button>`
          : `<button class="btn btn-primary" onclick="generateComplaintReport('${data.id}', this)">Generate Complaint Report</button>`
        }
        <button class="btn" style="background:var(--blue-light);color:var(--blue)" onclick="showAIExplain('${data.id}','${data.case_number}')">AI Explain</button>
        <button class="btn btn-outline" onclick="assignCase('${data.id}')">Assign Officer</button>
        <button class="btn btn-outline" onclick="addNote('${data.id}')">Add Note</button>
        <button class="btn btn-danger" onclick="flagFake('${data.id}', this)">Flag as Fake</button>
        <button class="btn btn-outline" onclick="closeModal()">Close</button>
      </div>
    `;
    // Load notes asynchronously after modal renders
    setTimeout(() => loadCaseNotes(data.id), 100);

  } catch (err) {
    body.innerHTML = `<div class="loading-text" style="color:var(--red)">Failed to load case details.</div>`;
  }
}

function closeModal() {
  document.getElementById('caseModal').classList.remove('show');
}

// ── Case Actions ─────────────────────────────────────────────────────────────

function downloadComplaintReport(reportId) {
  window.open(`/api/reports/${reportId}/fir/download`, '_blank');
}

async function generateComplaintReport(reportId, btn) {
  if (btn) { btn.disabled = true; btn.textContent = 'Generating...'; }
  try {
    const res = await fetch(`/api/reports/${reportId}/generate-fir`, {
      method: 'POST',
      headers: authHeaders(),
    });
    if (res.status === 401) {
      showToast('Authentication required — please log in again.', 'error');
      if (btn) { btn.disabled = false; btn.textContent = 'Gen CR'; }
      setTimeout(() => { window.location.href = '/login'; }, 1500);
      return;
    }
    const data = await res.json();
    if (data.success) {
      showToast(`Complaint Report generated: ${data.case_number}`, 'success');
      if (btn) {
        btn.className = 'btn btn-primary';
        btn.textContent = 'Download CR';
        btn.onclick = () => downloadComplaintReport(reportId);
        btn.disabled = false;
      }
      loadDashboard();
    } else {
      showToast(data.detail || 'Generation failed.', 'error');
      if (btn) { btn.disabled = false; btn.textContent = 'Gen CR'; }
    }
  } catch (err) {
    showToast('Generation failed — network error.', 'error');
    if (btn) { btn.disabled = false; btn.textContent = 'Gen CR'; }
  }
}

async function flagFake(reportId, btn) {
  const reason = prompt('Enter reason for flagging as fake (optional):') ?? '';
  if (reason === null) return; // cancelled
  if (btn) btn.disabled = true;
  try {
    const res = await fetch(
      `/api/cases/${reportId}/flag-fake?reason=${encodeURIComponent(reason)}`,
      { method: 'POST', headers: authHeaders() }
    );
    if (!res.ok) throw new Error('Failed');
    showToast('Report flagged as fake and closed.', 'success');
    closeModal();
    loadDashboard();
    loadAllCases();
  } catch (err) {
    showToast('Action failed.', 'error');
    if (btn) btn.disabled = false;
  }
}

async function assignCase(reportId) {
  try {
    const res = await fetch('/api/auth/officers', { headers: authHeaders() });
    if (!res.ok) throw new Error('Not authorised');
    const officers = await res.json();
    if (!officers.length) { showToast('No officers available.', 'error'); return; }

    const names = officers.map((o, i) => `${i + 1}. ${o.full_name}${o.rank ? ' (' + o.rank + ')' : ''}`).join('\n');
    const choice = prompt(`Assign to officer (enter number):\n${names}`);
    if (!choice) return;
    const idx = parseInt(choice) - 1;
    if (isNaN(idx) || idx < 0 || idx >= officers.length) { showToast('Invalid selection.', 'error'); return; }

    const officer = officers[idx];
    const r = await fetch(`/api/cases/${reportId}/assign`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ officer_id: officer.id }),
    });
    if (!r.ok) throw new Error('Failed');
    showToast(`Case assigned to ${officer.full_name}`, 'success');
    openCase(reportId); // Refresh modal
    loadDashboard();
  } catch (err) {
    showToast('Assignment failed — ensure you are logged in.', 'error');
  }
}

async function addNote(reportId) {
  const text = prompt('Enter case note:');
  if (!text || !text.trim()) return;
  try {
    const r = await fetch(`/api/cases/${reportId}/notes`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ note_text: text.trim(), is_internal: true }),
    });
    if (!r.ok) throw new Error('Failed');
    showToast('Note added successfully.', 'success');
    loadCaseNotes(reportId);
  } catch (err) {
    showToast('Failed to add note — ensure you are logged in.', 'error');
  }
}

async function loadCaseNotes(reportId) {
  const container = document.getElementById(`notes-${reportId}`);
  if (!container) return;
  try {
    const res = await fetch(`/api/cases/${reportId}/notes`, { headers: authHeaders() });
    const notes = await res.json();
    if (!notes.length) {
      container.innerHTML = '<p style="color:var(--gray-400);font-size:12px">No notes yet.</p>';
      return;
    }
    container.innerHTML = notes.map(n => `
      <div style="background:#f8fafc;border-radius:8px;padding:10px 12px;margin-bottom:8px;font-size:12px">
        <div style="display:flex;justify-content:space-between;margin-bottom:4px">
          <strong style="color:var(--navy)">${escapeHtml(n.officer_name || 'Officer')}</strong>
          <span style="color:var(--gray-400)">${new Date(n.created_at).toLocaleString('en-IN')}</span>
        </div>
        <p style="color:#374151">${escapeHtml(n.note_text)}</p>
      </div>
    `).join('');
  } catch {
    container.innerHTML = '<p style="color:var(--red);font-size:12px">Failed to load notes.</p>';
  }
}

async function loadForensicsSummary() {
  const container = document.getElementById('view-forensics');
  if (!container) return;
  try {
    const [fRes, rRes] = await Promise.all([
      fetch('/api/dashboard/forensics-summary', { headers: authHeaders() }),
      fetch('/api/reports/?limit=200', { headers: authHeaders() }),
    ]);
    const fData = await fRes.json();
    const cases = await rRes.json();
    const tampered = cases.filter(r => (r.forensics_tamper_score || 0) >= 0.55);
    const suspicious = cases.filter(r => {
      const s = r.forensics_tamper_score || 0;
      return s >= 0.30 && s < 0.55;
    });
    container.innerHTML = `
      <div class="stat-grid" style="margin-bottom:24px">
        <div class="stat-card"><div class="stat-icon" style="background:#fde8e8">🔬</div><div class="stat-body"><div class="stat-value">${fData.total_analyzed}</div><div class="stat-label">Images Analyzed</div></div></div>
        <div class="stat-card"><div class="stat-icon" style="background:#fde8e8">🚨</div><div class="stat-body"><div class="stat-value" style="color:var(--red)">${fData.tampered_detected}</div><div class="stat-label">Tampered Detected</div></div></div>
        <div class="stat-card"><div class="stat-icon" style="background:#fff7ed">⚠️</div><div class="stat-body"><div class="stat-value" style="color:var(--orange)">${fData.suspicious_detected}</div><div class="stat-label">Suspicious</div></div></div>
        <div class="stat-card"><div class="stat-icon" style="background:#f0fdf4">✅</div><div class="stat-body"><div class="stat-value" style="color:var(--success)">${fData.clean}</div><div class="stat-label">Clean</div></div></div>
      </div>
      <div class="table-card">
        <div class="table-header"><h3>High Tamper Score Cases</h3></div>
        <div class="table-wrap"><table class="data-table"><thead><tr>
          <th>Case</th><th>Complainant</th><th>Risk</th><th>Category</th><th>Tamper Score</th><th>Actions</th>
        </tr></thead><tbody>
        ${tampered.length ? tampered.map(r => `
          <tr>
            <td><span class="case-number">${escapeHtml(r.case_number)}</span></td>
            <td>${escapeHtml(r.complainant_name)}</td>
            <td><span class="risk-badge risk-${r.risk_level || 'PENDING'}">${r.risk_level || '—'}</span></td>
            <td>${escapeHtml(r.crime_category || '—')}</td>
            <td style="color:var(--red);font-weight:700">${((r.forensics_tamper_score||0)*100).toFixed(0)}%</td>
            <td><button class="table-action-btn" onclick="openCase('${r.id}')">Review</button></td>
          </tr>`) .join('') : '<tr><td colspan="6" class="loading-text">No highly tampered images detected.</td></tr>'}
        </tbody></table></div>
      </div>`;
  } catch {
    container.innerHTML = '<p style="color:var(--red)">Failed to load forensics data.</p>';
  }
}

async function loadTrustSummary() {
  const container = document.getElementById('view-trust');
  if (!container) return;
  try {
    const res = await fetch('/api/dashboard/reporter-trust-summary', { headers: authHeaders() });
    const data = await res.json();
    container.innerHTML = `
      <div class="stat-grid" style="margin-bottom:24px">
        <div class="stat-card"><div class="stat-icon" style="background:#e8f0fe">👥</div><div class="stat-body"><div class="stat-value">${data.total_reporter_profiles}</div><div class="stat-label">Reporter Profiles</div></div></div>
        <div class="stat-card"><div class="stat-icon" style="background:#f0fdf4">⭐</div><div class="stat-body"><div class="stat-value" style="color:var(--success)">${data.high_trust}</div><div class="stat-label">High Trust</div></div></div>
        <div class="stat-card"><div class="stat-icon" style="background:#fff7ed">⚠️</div><div class="stat-body"><div class="stat-value" style="color:var(--orange)">${data.low_trust}</div><div class="stat-label">Low Trust</div></div></div>
        <div class="stat-card"><div class="stat-icon" style="background:#fde8e8">🚫</div><div class="stat-body"><div class="stat-value" style="color:var(--red)">${data.blocked}</div><div class="stat-label">Blocked</div></div></div>
      </div>
      <div class="table-card">
        <div class="table-header"><h3>Trust Score Distribution</h3></div>
        <div style="padding:20px">
          ${[
            { label: 'High Trust (≥0.80)', count: data.high_trust, color: 'var(--success)', pct: data.total_reporter_profiles ? data.high_trust/data.total_reporter_profiles : 0 },
            { label: 'Neutral (0.40–0.79)', count: data.neutral,  color: 'var(--blue)',    pct: data.total_reporter_profiles ? data.neutral/data.total_reporter_profiles : 0 },
            { label: 'Low Trust (<0.40)',   count: data.low_trust, color: 'var(--orange)',  pct: data.total_reporter_profiles ? data.low_trust/data.total_reporter_profiles : 0 },
            { label: 'Blocked',             count: data.blocked,   color: 'var(--red)',     pct: data.total_reporter_profiles ? data.blocked/data.total_reporter_profiles : 0 },
          ].map(item => `
            <div style="margin-bottom:14px">
              <div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:4px">
                <span>${item.label}</span><strong>${item.count}</strong>
              </div>
              <div class="score-bar"><div class="score-fill" style="width:${(item.pct*100).toFixed(1)}%;background:${item.color}"></div></div>
            </div>`).join('')}
        </div>
      </div>`;
  } catch {
    container.innerHTML = '<p style="color:var(--red)">Failed to load trust data.</p>';
  }
}

// ── Audit Log ────────────────────────────────────────────────────────────────

async function loadAuditLog() {
  const container = document.getElementById('auditLogContent');
  if (!container) return;

  try {
    const res  = await fetch('/api/dashboard/audit-log?limit=50', { headers: authHeaders() });
    const logs = await res.json();

    if (!logs.length) {
      container.innerHTML = '<p style="color:var(--gray-400)">No audit entries yet.</p>';
      return;
    }

    container.innerHTML = logs.map(log => `
      <div class="audit-entry">
        <div class="audit-dot" style="background:${log.action.includes('FAKE') ? 'var(--orange)' : log.action.includes('FIR') ? 'var(--success)' : 'var(--blue)'}"></div>
        <div style="flex:1">
          <div style="display:flex; justify-content:space-between">
            <span class="audit-action">${escapeHtml(log.action)}</span>
            <span class="audit-time">${new Date(log.timestamp).toLocaleString('en-IN')}</span>
          </div>
          ${log.details ? `<div class="audit-details">${JSON.stringify(log.details).slice(0, 150)}</div>` : ''}
          ${log.ip_address ? `<div style="font-size:10px; color:var(--gray-400); margin-top:2px">IP: ${log.ip_address}</div>` : ''}
        </div>
      </div>
    `).join('');
  } catch (err) {
    container.innerHTML = '<p style="color:var(--red)">Failed to load audit log.</p>';
  }
}

// ── Utilities ────────────────────────────────────────────────────────────────

function setEl(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function riskIcon(level) {
  return level === 'HIGH' ? '●' : level === 'MEDIUM' ? '●' : level === 'LOW' ? '●' : '●';
}

/**
 * Human-readable status labels.
 * Avoids showing raw DB enum values like "FIR_GENERATED" or "COMPLAINT_REGISTERED".
 */
function formatStatus(status) {
  const STATUS_LABELS = {
    'PENDING':               'Pending',
    'PROCESSING':            'Processing',
    'TRIAGED':               'CR Generated',
    'COMPLAINT_REGISTERED':  'CR Generated',
    'FIR_GENERATED':         'CR Generated',
    'CLOSED':                'Closed',
    'REJECTED':              'Rejected',
  };
  if (!status) return '—';
  return STATUS_LABELS[status] || status.replace(/_/g, ' ');
}

function formatTimeAgo(isoString) {
  if (!isoString) return '—';
  const now  = Date.now();
  const then = new Date(isoString).getTime();
  const diff = Math.floor((now - then) / 1000);

  if (diff < 60)   return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return new Date(isoString).toLocaleDateString('en-IN');
}

function showToast(msg, type = 'info') {
  const toast = document.getElementById('toast');
  if (!toast) return;
  toast.textContent = msg;
  toast.className = `toast show ${type}`;
  setTimeout(() => toast.classList.remove('show'), 3000);
}

// Close modal on overlay click
document.getElementById('caseModal')?.addEventListener('click', function(e) {
  if (e.target === this) closeModal();
});

// ── AI Explainability Panel ───────────────────────────────────────────────────

async function showAIExplain(reportId, caseNumber) {
  // Open modal first with loading
  const modal = document.getElementById('caseModal');
  const body  = document.getElementById('modalBody');
  document.getElementById('modalTitle').textContent = 'AI Decision Explainability';
  document.getElementById('modalCaseNumber').textContent = `Why did AI classify ${caseNumber} this way?`;
  modal.classList.add('show');
  body.innerHTML = '<div class="loading-text"><div class="spinner"></div> Fetching AI reasoning...</div>';

  try {
    const res  = await fetch(`/api/dashboard/explain/${reportId}`, { headers: authHeaders() });
    const data = await res.json();

    const riskColor = data.risk_level === 'HIGH' ? 'var(--red)'
                    : data.risk_level === 'MEDIUM' ? 'var(--orange)' : 'var(--success)';
    const authColor = data.authenticity_score >= 0.65 ? 'var(--success)'
                    : data.authenticity_score >= 0.45 ? 'var(--orange)' : 'var(--red)';
    const invColor  = data.investigability?.score >= 0.7 ? 'var(--success)'
                    : data.investigability?.score >= 0.4 ? 'var(--orange)' : 'var(--red)';

    body.innerHTML = `
      <!-- Header Scores -->
      <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:12px; margin-bottom:20px;">
        <div style="background:var(--gray-50); padding:14px; border-radius:10px; text-align:center; border-top:3px solid ${riskColor}">
          <div style="font-size:10px; font-weight:700; color:var(--gray-400); text-transform:uppercase; margin-bottom:4px">Risk Level</div>
          <div style="font-size:22px; font-weight:800; color:${riskColor}">${data.risk_level}</div>
          <div style="font-size:12px; color:var(--gray-400)">${(data.risk_score*100).toFixed(0)}% confidence</div>
        </div>
        <div style="background:var(--gray-50); padding:14px; border-radius:10px; text-align:center; border-top:3px solid ${authColor}">
          <div style="font-size:10px; font-weight:700; color:var(--gray-400); text-transform:uppercase; margin-bottom:4px">Authenticity</div>
          <div style="font-size:22px; font-weight:800; color:${authColor}">${(data.authenticity_score*100).toFixed(0)}%</div>
          <div style="font-size:12px; color:var(--gray-400)">${data.fake_recommendation}</div>
        </div>
        <div style="background:var(--gray-50); padding:14px; border-radius:10px; text-align:center; border-top:3px solid ${invColor}">
          <div style="font-size:10px; font-weight:700; color:var(--gray-400); text-transform:uppercase; margin-bottom:4px">Investigability</div>
          <div style="font-size:22px; font-weight:800; color:${invColor}">${(data.investigability?.score*100||0).toFixed(0)}%</div>
          <div style="font-size:12px; color:var(--gray-400)">${data.investigability?.label || '—'}</div>
        </div>
      </div>

      <!-- Risk Reasoning -->
      <div style="margin-bottom:16px;">
        <div style="font-size:11px; font-weight:700; color:var(--gray-400); text-transform:uppercase; margin-bottom:8px;">Why This Risk Level?</div>
        <div style="background:var(--gray-50); padding:12px; border-radius:8px; font-size:13px; margin-bottom:8px; font-weight:500; color:var(--navy)">${escapeHtml(data.risk_reasoning?.headline)}</div>
        ${(data.risk_reasoning?.factors||[]).map(f => `
          <div style="font-size:12px; padding:5px 0; color:${f.startsWith('✓') ? 'var(--success)' : f.startsWith('⚠') ? 'var(--orange)' : 'var(--gray-600)'};">${escapeHtml(f)}</div>
        `).join('')}
      </div>

      <!-- Authenticity Reasoning -->
      <div style="margin-bottom:16px;">
        <div style="font-size:11px; font-weight:700; color:var(--gray-400); text-transform:uppercase; margin-bottom:8px;">Why This Authenticity Score?</div>
        <div style="background:var(--gray-50); padding:12px; border-radius:8px; font-size:13px; margin-bottom:8px; font-weight:500; color:var(--navy)">${escapeHtml(data.authenticity_reasoning?.headline)}</div>
        ${(data.authenticity_reasoning?.factors||[]).map(f => `
          <div style="font-size:12px; padding:5px 0; color:${f.startsWith('✓') ? 'var(--success)' : f.startsWith('⚠') ? 'var(--orange)' : 'var(--red)'};">${escapeHtml(f)}</div>
        `).join('')}
      </div>

      <!-- Investigability Checklist -->
      <div style="margin-bottom:16px;">
        <div style="font-size:11px; font-weight:700; color:var(--gray-400); text-transform:uppercase; margin-bottom:8px;">Investigation Leads Available</div>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:6px;">
          ${Object.entries(data.investigability?.entity_checks||{}).map(([key, val]) => `
            <div style="display:flex; align-items:center; gap:6px; font-size:12px; padding:6px 8px; background:${val ? '#f0fdf4' : '#fef2f2'}; border-radius:6px;">
              <span>${val ? '✅' : '❌'}</span>
              <span style="color:${val ? 'var(--success)' : 'var(--red)'}; font-weight:500">${key.replace(/_/g,' ')}</span>
            </div>
          `).join('')}
        </div>
      </div>

      <!-- Legal Sections -->
      ${(data.legal_mapping?.sections_applied||[]).length > 0 ? `
      <div style="margin-bottom:16px;">
        <div style="font-size:11px; font-weight:700; color:var(--gray-400); text-transform:uppercase; margin-bottom:8px;">AI-Mapped Legal Sections (${data.legal_mapping.section_count})</div>
        <div style="display:flex; flex-wrap:wrap; gap:6px;">
          ${data.legal_mapping.sections_applied.map(s => `<span style="background:#eff6ff; color:#1e40af; padding:4px 10px; border-radius:6px; font-size:11px; font-weight:500">${escapeHtml(s)}</span>`).join('')}
        </div>
      </div>` : ''}

      <!-- AI Disclaimer -->
      <div style="background:#fff7ed; border-left:3px solid var(--orange); padding:10px 12px; border-radius:0 6px 6px 0; font-size:11px; color:#92400e; margin-top:8px;">
        ⚠ ${escapeHtml(data.ai_confidence_note)}
      </div>

      <div class="modal-actions" style="margin-top:16px; padding-top:16px; border-top:1px solid var(--gray-200);">
        <button class="btn btn-outline" onclick="closeModal()">Close</button>
      </div>
    `;

  } catch (err) {
    body.innerHTML = `<div class="loading-text" style="color:var(--red)">Failed to load AI explanation: ${err.message}</div>`;
  }
}
