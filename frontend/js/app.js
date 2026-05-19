

const API = 'https://cc-software.onrender.com'; 

let TOKEN        = localStorage.getItem('cc_token')  || null;
let CURRENT_USER = JSON.parse(localStorage.getItem('cc_user') || 'null');
let CURRENT_PAGE = 'dashboard';
let WBS_PROJECT_ID     = null;
let EVM_PROJECT_ID     = null;
let PROJECT_INFO_ID    = null;
let EDIT_PROJECT_ID  = null;
let EDIT_TASK_ID     = null;
let METRICS_PROJECT_ID = null;
let CHATBOT_HISTORY    = [];

async function api(method, path, body = null) {
  const opts = {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(TOKEN ? { Authorization: `Bearer ${TOKEN}` } : {}),
    },
  };
  if (body) opts.body = JSON.stringify(body);

  const res = await fetch(API + path, opts);

  if (res.status === 401) { doLogout(); throw new Error('Session expired. Please log in again.'); }

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }

  return res.json().catch(() => ({}));
}

function toast(msg, type = 'info') {
  const icons = { success: 'check_circle', error: 'cancel', info: 'info' };
  const el = document.createElement('div');
  el.className = `toast-item ${type}`;
  el.innerHTML = `<span class="material-symbols-outlined" style="font-size:16px;vertical-align:middle">${icons[type]}</span><span>${msg}</span>`;
  document.getElementById('toast').appendChild(el);
  setTimeout(() => el.style.opacity = '0', 3000);
  setTimeout(() => el.remove(), 3500);
}

function openModal(id)  { document.getElementById(id).classList.add('open'); }
function closeModal(id) { document.getElementById(id).classList.remove('open'); }

document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
  backdrop.addEventListener('click', e => {
    if (e.target === backdrop) backdrop.classList.remove('open');
  });
});

async function doLogin() {
  const username = document.getElementById('login-username').value.trim();
  const password = document.getElementById('login-password').value;
  const errEl    = document.getElementById('login-error');
  const spinner  = document.getElementById('login-spinner');
  const label    = document.getElementById('login-label');

  if (!username || !password) { showLoginErr('Please enter username and password.'); return; }

  label.style.display   = 'none';
  spinner.style.display = 'block';
  errEl.style.display   = 'none';

  try {
    const data = await api('POST', '/api/auth/login', { username, password });
    TOKEN        = data.access_token;
    CURRENT_USER = data.user;
    localStorage.setItem('cc_token', TOKEN);
    localStorage.setItem('cc_user', JSON.stringify(CURRENT_USER));
    initApp();
  } catch (e) {
    showLoginErr(e.message || 'Login failed. Check your credentials.');
  } finally {
    label.style.display   = 'inline';
    spinner.style.display = 'none';
  }
}

function showLoginErr(msg) {
  const errEl = document.getElementById('login-error');
  errEl.textContent   = msg;
  errEl.style.display = 'block';
}

function doLogout() {
  TOKEN = null; CURRENT_USER = null;
  localStorage.removeItem('cc_token');
  localStorage.removeItem('cc_user');
  document.getElementById('login-page').style.display = 'flex';
  document.getElementById('app').style.display        = 'none';
}

function showUserMenu() {
  if (confirm(`Sign out as ${CURRENT_USER?.username}?`)) doLogout();
}

document.addEventListener('keydown', e => {
  if (e.key === 'Enter') {
    const lp = document.getElementById('login-page');
    if (lp && lp.style.display !== 'none') {
      const signupVisible = document.getElementById('signup-section') &&
                            document.getElementById('signup-section').style.display !== 'none';
      if (signupVisible) doSignUp(); else doLogin();
    }
  }
});

function initApp() {
  document.getElementById('login-page').style.display = 'none';
  document.getElementById('app').style.display        = 'block';

  const initials = CURRENT_USER.username.slice(0, 2).toUpperCase();
  document.getElementById('user-avatar').textContent       = initials;
  document.getElementById('user-name-display').textContent = CURRENT_USER.username;
  document.getElementById('user-role-display').textContent = CURRENT_USER.role;

  document.getElementById('nav-users').style.display =
    CURRENT_USER.role === 'Admin' ? 'flex' : 'none';

  navigate('dashboard');
  loadNotifCount();
}

if (TOKEN && CURRENT_USER) initApp();

setInterval(() => { if (TOKEN) loadNotifCount(); }, 30000);

function navigate(page, params = {}) {
  CURRENT_PAGE = page;
  if (params.WBS_PROJECT_ID     !== undefined) WBS_PROJECT_ID     = params.WBS_PROJECT_ID;
  if (params.EVM_PROJECT_ID     !== undefined) EVM_PROJECT_ID     = params.EVM_PROJECT_ID;
  if (params.PROJECT_INFO_ID    !== undefined) PROJECT_INFO_ID    = params.PROJECT_INFO_ID;
  if (params.MEMBER_PROJECT_ID  !== undefined) MEMBER_PROJECT_ID  = params.MEMBER_PROJECT_ID;

  document.querySelectorAll('.nav-item[data-page]').forEach(el => {
    el.classList.toggle('active', el.dataset.page === page);
  });

  const pages = { dashboard, analytics, projects, selection, wbs, evm, notifications, reports, users, gantt, members, profile, projectInfo, chatbot };
  if (pages[page]) pages[page]();
}

async function loadNotifCount() {
  try {
    const data   = await api('GET', '/api/notifications');
    const unread = data.filter(n => !n.is_read).length;
    const badge    = document.getElementById('notif-count');
    const navBadge = document.getElementById('nav-notif-count');
    if (unread > 0) {
      badge.style.display = 'flex';
      badge.textContent   = unread;
      navBadge.textContent = unread;
    } else {
      badge.style.display  = 'none';
      navBadge.textContent = '0';
    }
  } catch {}
}

async function deleteAllNotifications() {
  if (!confirm('Delete all notifications? This cannot be undone.')) return;
  try {
    await api('DELETE', '/api/notifications');
    toast('All notifications deleted', 'success');
    loadNotifCount();
    notifications();
  } catch (e) { toast(e.message, 'error'); }
}

async function downloadFile(path, filename) {
  try {
    const res = await fetch(`${API}${path}`, {
      headers: { 'Authorization': `Bearer ${TOKEN}` }
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      toast(err.detail || 'Download failed', 'error');
      return;
    }
    const blob = await res.blob();
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  } catch (e) {
    toast('Download failed: ' + e.message, 'error');
  }
}

function fmt(n, decimals = 2) {
  if (n == null) return '—';
  return Number(n).toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

function fmtK(n) {
  if (n == null) return '—';
  if (Math.abs(n) >= 1e6) return (n / 1e6).toFixed(1) + 'M';
  if (Math.abs(n) >= 1e3) return (n / 1e3).toFixed(0) + 'K';
  return Number(n).toFixed(0);
}

function statusBadge(s) {
  const m = {
    'Pending':'gray','Candidate':'gray','Draft':'gray',
    'Selected':'violet','In Progress':'blue',
    'Completed':'green','Cancelled':'rose',
  };
  return `<span class="badge badge-${m[s] || 'gray'}">${s}</span>`;
}

function riskBadge(level) {
  const m = { Low:'green', Medium:'amber', High:'rose', Critical:'rose' };
  return `<span class="badge badge-${m[level] || 'gray'}">${level}</span>`;
}

function taskBadge(s) {
  const m = { 'Not Started':'gray', 'In Progress':'blue', 'Completed':'green' };
  return `<span class="badge badge-${m[s] || 'gray'}">${s}</span>`;
}

Chart.defaults.color              = '#94a3b8';
Chart.defaults.borderColor        = 'rgba(255,255,255,0.06)';
Chart.defaults.plugins.legend.labels.font    = { size: 11, family: 'DM Mono' };
Chart.defaults.plugins.legend.labels.boxWidth = 10;
Chart.defaults.plugins.legend.labels.padding  = 12;
Chart.defaults.scale.ticks.font               = { size: 10 };

async function dashboard() {
  document.getElementById('main-content').innerHTML = `
    <div class="page-content">
      <div class="page-header">
        <div>
          <div class="page-title">Dashboard</div>
          <div class="page-subtitle">Portfolio overview · Live EVM data</div>
        </div>
      </div>
      <div class="kpi-grid" id="kpi-grid">
        <div style="grid-column:1/-1;display:flex;align-items:center;gap:12px;padding:20px;color:var(--text-3)">
          <div class="spinner"></div> Loading metrics...
        </div>
      </div>
      <div class="grid-2" style="margin-top:20px">
        <div class="card">
          <div class="card-title">Project Status Distribution</div>
          <div class="chart-container" style="height:220px"><canvas id="status-chart"></canvas></div>
        </div>
        <div class="card">
          <div class="card-title">EVM — Portfolio Overview <span style="font-size:11px;font-weight:400;color:var(--text-3)">(PV vs EV vs AC)</span></div>
          <div class="chart-container" style="height:220px"><canvas id="evm-chart"></canvas></div>
        </div>
      </div>
      <div class="card" style="margin-top:20px">
        <div class="card-title">All Projects <span style="font-size:11px;font-weight:400;color:var(--text-3)">Quick overview</span></div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>#</th><th>Project</th><th>Status</th><th>Budget</th>
                <th>Progress</th><th>CPI</th><th>SPI</th><th>EAC</th>
              </tr>
            </thead>
            <tbody id="dash-table-body">
              <tr><td colspan="8" style="text-align:center;padding:24px;color:var(--text-3)">Loading...</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>`;

  try {
    const [summary, dashData] = await Promise.all([
      api('GET', '/api/analytics/portfolio/summary'),
      api('GET', '/api/dashboard'),
    ]);

    
    const evm = summary.evm;
    document.getElementById('kpi-grid').innerHTML = `
      <div class="kpi-card blue">
        <div class="kpi-icon material-symbols-outlined">folder</div>
        <div class="kpi-label">Total Projects</div>
        <div class="kpi-value">${summary.total_projects}</div>
        <div class="kpi-sub">${summary.selected_projects} selected</div>
      </div>
      <div class="kpi-card green">
        <div class="kpi-icon material-symbols-outlined">payments</div>
        <div class="kpi-label">Portfolio Budget</div>
        <div class="kpi-value">${fmtK(summary.total_budget)}</div>
        <div class="kpi-sub">SAR across all projects</div>
      </div>
      <div class="kpi-card amber">
        <div class="kpi-icon material-symbols-outlined">group</div>
        <div class="kpi-label">Team Members</div>
        <div class="kpi-value">${summary.users.active}</div>
        <div class="kpi-sub">${summary.users.project_managers} PMs · ${summary.users.team_members} members</div>
      </div>
      <div class="kpi-card ${evm.at_risk_projects > 0 ? 'rose' : 'green'}">
        <div class="kpi-icon material-symbols-outlined">warning</div>
        <div class="kpi-label">Projects At Risk</div>
        <div class="kpi-value">${evm.at_risk_projects}</div>
        <div class="kpi-sub">${evm.healthy_projects} healthy · avg CPI ${evm.avg_cpi ?? '—'}</div>
      </div>
      <div class="kpi-card blue">
        <div class="kpi-icon material-symbols-outlined">task_alt</div>
        <div class="kpi-label">Task Completion</div>
        <div class="kpi-value">${summary.tasks.completion_rate_pct}%</div>
        <div class="kpi-sub">${summary.tasks.completed} / ${summary.tasks.total} tasks done</div>
      </div>`;

    
    const statusDist = summary.status_distribution;
    const sColors = {
      'In Progress':'#3b82f6','Completed':'#10b981','Pending':'#475569',
      'Selected':'#8b5cf6','Candidate':'#64748b','Draft':'#334155','Cancelled':'#f43f5e'
    };
    new Chart(document.getElementById('status-chart'), {
      type: 'doughnut',
      data: {
        labels: Object.keys(statusDist),
        datasets: [{
          data: Object.values(statusDist),
          backgroundColor: Object.keys(statusDist).map(k => sColors[k] || '#475569'),
          borderWidth: 0,
          hoverOffset: 6,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: 'right' } },
        cutout: '70%',
      },
    });

    
    new Chart(document.getElementById('evm-chart'), {
      type: 'bar',
      data: {
        labels: dashData.map(p => p.project_name.slice(0, 14)),
        datasets: [
          { label: 'PV', data: dashData.map(p => p.evm?.pv  || 0), backgroundColor: 'rgba(59,130,246,0.5)',  borderColor: '#3b82f6', borderWidth: 1 },
          { label: 'EV', data: dashData.map(p => p.evm?.ev  || 0), backgroundColor: 'rgba(16,185,129,0.5)',  borderColor: '#10b981', borderWidth: 1 },
          { label: 'AC', data: dashData.map(p => p.evm?.ac  || 0), backgroundColor: 'rgba(245,158,11,0.5)',  borderColor: '#f59e0b', borderWidth: 1 },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: { grid: { color: 'rgba(255,255,255,0.04)' } },
          y: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { callback: v => fmtK(v) } },
        },
      },
    });

    
    document.getElementById('nav-projects-count').textContent = dashData.length;
    const tbody = document.getElementById('dash-table-body');
    if (!dashData.length) {
      tbody.innerHTML = `<tr><td colspan="8"><div class="empty-state"><div class="empty-icon"><span class="material-symbols-outlined">folder</span></div><div class="empty-title">No projects yet</div></div></td></tr>`;
      return;
    }

    tbody.innerHTML = dashData.map((p, i) => {
      const cpi = p.evm?.cpi;
      const spi = p.evm?.spi;
      const cpiColor = cpi == null ? '' : cpi < 0.9 ? 'color:var(--rose)' : 'color:var(--emerald)';
      const spiColor = spi == null ? '' : spi < 0.9 ? 'color:var(--rose)' : 'color:var(--emerald)';
      const pct       = p.progress_pct;
      const fillColor = pct >= 70 ? 'green' : pct >= 30 ? 'amber' : '';
      return `<tr>
        <td style="color:var(--text-3);font-family:var(--font-mono)">${i + 1}</td>
        <td>
          <span style="font-weight:600;cursor:pointer;color:var(--blue-glow)"
                onclick="navigate('projectInfo',{PROJECT_INFO_ID:${p.project_id}})">${p.project_name}</span>
        </td>
        <td>${statusBadge(p.status)}</td>
        <td style="font-family:var(--font-mono)">${fmtK(p.budget)} SAR</td>
        <td style="min-width:130px">
          <div style="display:flex;align-items:center;gap:8px">
            <div class="progress-bar" style="flex:1">
              <div class="progress-fill ${fillColor}" style="width:${pct}%"></div>
            </div>
            <span style="font-family:var(--font-mono);font-size:11px;color:var(--text-3);width:32px">${pct}%</span>
          </div>
        </td>
        <td style="font-family:var(--font-mono);font-size:12px;${cpiColor}">${cpi != null ? fmt(cpi, 3) : '—'}</td>
        <td style="font-family:var(--font-mono);font-size:12px;${spiColor}">${spi != null ? fmt(spi, 3) : '—'}</td>
        <td style="font-family:var(--font-mono);font-size:12px">${p.evm?.eac != null ? fmtK(p.evm.eac) : '—'}</td>
      </tr>`;
    }).join('');

  } catch (e) { toast(e.message, 'error'); }
}

async function analytics() {
  document.getElementById('main-content').innerHTML = `
    <div class="page-content">
      <div class="page-header">
        <div>
          <div class="page-title">Analytics</div>
          <div class="page-subtitle">Risk intelligence · Budget utilisation · Portfolio health</div>
        </div>
      </div>
      <div class="card" style="margin-bottom:20px">
        <div class="card-title">
          Risk Assessment
          <span style="font-weight:400;font-size:11px;color:var(--text-3)">Scored by EVM indicators + deadline proximity</span>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr><th>Rank</th><th>Project</th><th>Risk Level</th><th>Risk Score</th><th>CPI</th><th>SPI</th><th>Days Left</th><th>Flags</th></tr>
            </thead>
            <tbody id="risk-table">
              <tr><td colspan="8" style="text-align:center;padding:20px;color:var(--text-3)">Loading...</td></tr>
            </tbody>
          </table>
        </div>
      </div>
      <div class="card" style="margin-bottom:20px">
        <div class="card-title">Budget Utilisation</div>
        <div class="chart-container" style="height:220px"><canvas id="budget-chart"></canvas></div>
      </div>
      <div class="card">
        <div class="card-title">Portfolio Composition</div>
        <div id="composition-body" style="padding:8px;color:var(--text-3)">Loading...</div>
      </div>
    </div>`;

  try {
    const [risk, budget, summary] = await Promise.all([
      api('GET', '/api/analytics/portfolio/risk'),
      api('GET', '/api/analytics/portfolio/budget'),
      api('GET', '/api/analytics/portfolio/summary'),
    ]);

    
    const riskTbody = document.getElementById('risk-table');
    if (!risk.length) {
      riskTbody.innerHTML = `<tr><td colspan="8"><div class="empty-state"><div class="empty-icon"><span class="material-symbols-outlined">shield</span></div><div class="empty-title">No risk data yet</div></div></td></tr>`;
    } else {
      riskTbody.innerHTML = risk.map((r, i) => {
        const barColor = r.risk_score > 60 ? 'var(--rose)' : r.risk_score > 30 ? 'var(--amber)' : 'var(--emerald)';
        return `<tr>
          <td style="font-family:var(--font-mono);color:var(--text-3)">${i + 1}</td>
          <td style="font-weight:600">${r.project_name}</td>
          <td>
            <div class="risk-bar">
              <div class="risk-level ${r.risk_level}"></div>
              ${riskBadge(r.risk_level)}
            </div>
          </td>
          <td>
            <div class="score-bar-wrap">
              <div class="score-bar" style="width:80px">
                <div class="score-fill" style="width:${r.risk_score}%;background:${barColor}"></div>
              </div>
              <span class="score-val">${r.risk_score}</span>
            </div>
          </td>
          <td style="font-family:var(--font-mono);color:${r.cpi < 0.9 ? 'var(--rose)' : 'var(--emerald)'}">${r.cpi != null ? fmt(r.cpi, 3) : '—'}</td>
          <td style="font-family:var(--font-mono);color:${r.spi < 0.9 ? 'var(--rose)' : 'var(--emerald)'}">${r.spi != null ? fmt(r.spi, 3) : '—'}</td>
          <td style="font-family:var(--font-mono);color:${r.days_remaining < 30 ? 'var(--rose)' : 'var(--text-2)'}">${r.days_remaining != null ? r.days_remaining + 'd' : '—'}</td>
          <td style="font-size:11px;color:var(--text-2)">${r.risk_flags.slice(0, 2).join(' · ') || '—'}</td>
        </tr>`;
      }).join('');
    }

    
    new Chart(document.getElementById('budget-chart'), {
      type: 'bar',
      data: {
        labels: budget.map(b => b.project_name.slice(0, 14)),
        datasets: [
          { label: 'Budget',      data: budget.map(b => b.budget),      backgroundColor: 'rgba(59,130,246,0.25)', borderColor: '#3b82f6', borderWidth: 1 },
          { label: 'Actual Cost', data: budget.map(b => b.actual_cost), backgroundColor: budget.map(b => b.is_over_budget ? 'rgba(244,63,94,0.5)' : 'rgba(16,185,129,0.5)'), borderColor: budget.map(b => b.is_over_budget ? '#f43f5e' : '#10b981'), borderWidth: 1 },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: { grid: { color: 'rgba(255,255,255,0.04)' } },
          y: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { callback: v => fmtK(v) } },
        },
      },
    });

    
    const comp = summary.status_distribution;
    document.getElementById('composition-body').innerHTML = `
      <div style="display:flex;flex-wrap:wrap;gap:12px;padding:4px 0">
        ${Object.entries(comp).map(([k, v]) => `
          <div style="display:flex;align-items:center;gap:12px;background:var(--bg-raised);border:1px solid var(--border);border-radius:var(--radius-md);padding:14px 18px;min-width:150px">
            <div style="font-family:var(--font-display);font-size:30px;font-weight:800">${v}</div>
            <div>
              <div style="font-weight:600;font-size:13px">${k}</div>
              <div style="font-size:11px;color:var(--text-3);font-family:var(--font-mono)">projects</div>
            </div>
          </div>`).join('')}
      </div>`;

  } catch (e) { toast(e.message, 'error'); }
}

async function projects() {
  const canEdit = ['Admin', 'Project Manager'].includes(CURRENT_USER?.role);

  document.getElementById('main-content').innerHTML = `
    <div class="page-content">
      <div class="page-header">
        <div>
          <div class="page-title">Projects</div>
          <div class="page-subtitle">Full project registry</div>
        </div>
        <div class="page-actions">
          <div class="search-box"><span class="material-symbols-outlined">search</span> <input id="proj-search" placeholder="Search projects..." oninput="filterProjects()" /></div>
          ${canEdit ? `<button class="btn btn-primary" onclick="openProjectModal()" style="width:auto">+ New Project</button>` : ''}
        </div>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr><th>#</th><th>Project Name</th><th>Project Manager</th><th>Status</th><th>Budget (SAR)</th><th>Start</th><th>End</th><th>Score</th><th>Actions</th></tr>
          </thead>
          <tbody id="projects-tbody">
            <tr><td colspan="9" style="text-align:center;padding:24px;color:var(--text-3)">Loading...</td></tr>
          </tbody>
        </table>
      </div>
    </div>`;

  try {
    const [projs, leaderboard, users] = await Promise.all([
      api('GET', '/api/projects'),
      api('GET', '/api/analytics/selection/leaderboard').catch(() => []),
      api('GET', '/api/users').catch(() => []),
    ]);
    window._allProjects = projs;
    window._allUsers = users;

    const scoreMap = {};
    leaderboard.forEach(r => { scoreMap[r.project_id] = r.scoring?.total_score; });

    const render = (list) => {
      const tbody = document.getElementById('projects-tbody');
      if (!list.length) {
        tbody.innerHTML = `<tr><td colspan="9"><div class="empty-state"><div class="empty-icon"><span class="material-symbols-outlined">folder</span></div><div class="empty-title">No projects found</div></div></td></tr>`;
        return;
      }
      tbody.innerHTML = list.map((p, i) => {
        const score  = scoreMap[p.project_id];
        const canDel = CURRENT_USER?.role === 'Admin' ||
                       (CURRENT_USER?.role === 'Project Manager' && p.manager_id === CURRENT_USER?.user_id);
        const mgr    = p.manager_name || '—';
        return `<tr>
          <td style="color:var(--text-3);font-family:var(--font-mono)">${i + 1}</td>
          <td>
            <div style="font-weight:600;cursor:pointer;color:var(--blue-glow)"
                 onclick="navigate('projectInfo',{PROJECT_INFO_ID:${p.project_id}})">${p.name}</div>
            ${p.description ? `<div style="font-size:11px;color:var(--text-3);margin-top:2px">${p.description.slice(0, 60)}${p.description.length > 60 ? '…' : ''}</div>` : ''}
          </td>
          <td>
            ${p.manager_name
              ? `<div style="display:flex;align-items:center;gap:6px">
                   <div style="width:26px;height:26px;border-radius:50%;background:var(--blue-glow);display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;color:#fff">${p.manager_name[0].toUpperCase()}</div>
                   <span style="font-size:13px">${p.manager_name}</span>
                 </div>`
              : `<span style="color:var(--text-3);font-size:12px">—</span>`}
          </td>
          <td>
            ${statusBadge(p.status)}
            ${p.is_selected ? '<span class="badge badge-violet" style="margin-left:4px">★ Selected</span>' : ''}
          </td>
          <td style="font-family:var(--font-mono)">${fmtK(p.budget)}</td>
          <td style="font-family:var(--font-mono);font-size:12px;color:var(--text-2)">${p.start_date || '—'}</td>
          <td style="font-family:var(--font-mono);font-size:12px;color:var(--text-2)">${p.end_date   || '—'}</td>
          <td>
            ${score != null
              ? `<div class="score-bar-wrap">
                   <div class="score-bar" style="width:70px"><div class="score-fill" style="width:${score}%"></div></div>
                   <span class="score-val">${fmt(score, 1)}</span>
                 </div>`
              : `<span style="color:var(--text-3);font-size:12px">—</span>`}
          </td>
          <td>
            <div style="display:flex;gap:6px">
              <button class="btn btn-ghost btn-sm" onclick="navigate('projectInfo',{PROJECT_INFO_ID:${p.project_id}})" title="Project Details"><span class="material-symbols-outlined">info</span></button>
              <button class="btn btn-ghost btn-sm" onclick="navigate('wbs',{WBS_PROJECT_ID:${p.project_id}})" title="WBS Tasks"><span class="material-symbols-outlined">assignment</span></button>
              <button class="btn btn-ghost btn-sm" onclick="openMetricsModal(${p.project_id})" title="Financial Metrics"><span class="material-symbols-outlined">payments</span></button>
              ${canEdit ? `<button class="btn btn-ghost btn-sm" onclick="openProjectModal(${p.project_id})" title="Edit"><span class="material-symbols-outlined">edit</span></button>` : ''}
              ${canDel  ? `<button class="btn btn-ghost btn-sm" style="color:var(--rose)" onclick="deleteProject(${p.project_id},'${p.name.replace(/'/g,"\\'")}')"><span class="material-symbols-outlined">delete</span></button>` : ''}
            </div>
          </td>
        </tr>`;
      }).join('');
    };

    render(projs);
    document.getElementById('nav-projects-count').textContent = projs.length;

    window.filterProjects = () => {
      const q = document.getElementById('proj-search')?.value.toLowerCase() || '';
      render(window._allProjects.filter(p =>
        p.name.toLowerCase().includes(q) ||
        (p.description || '').toLowerCase().includes(q) ||
        (p.manager_name || '').toLowerCase().includes(q)
      ));
    };

  } catch (e) { toast(e.message, 'error'); }
}

function openProjectModal(projectId = null) {
  EDIT_PROJECT_ID = projectId;
  document.getElementById('project-modal-title').textContent = projectId ? 'Edit Project' : 'New Project';

  // Populate manager dropdown
  const mgrSel = document.getElementById('pm-manager');
  mgrSel.innerHTML = '<option value="">— Unassigned —</option>';
  (window._allUsers || []).forEach(u => {
    const opt = document.createElement('option');
    opt.value = u.user_id;
    opt.textContent = `${u.username} (${u.role})`;
    mgrSel.appendChild(opt);
  });

  if (projectId) {
    const p = window._allProjects?.find(x => x.project_id === projectId);
    if (p) {
      document.getElementById('pm-name').value    = p.name || '';
      document.getElementById('pm-desc').value    = p.description || '';
      document.getElementById('pm-budget').value  = p.budget || '';
      document.getElementById('pm-status').value  = p.status || 'Pending';
      document.getElementById('pm-start').value   = p.start_date || '';
      document.getElementById('pm-end').value     = p.end_date   || '';
      mgrSel.value = p.manager_id || '';
    }
  } else {
    ['pm-name','pm-desc','pm-budget','pm-start','pm-end'].forEach(id => { document.getElementById(id).value = ''; });
    document.getElementById('pm-status').value = 'Pending';
    mgrSel.value = '';
  }
  openModal('project-modal');
}

async function saveProject() {
  const mgrVal = document.getElementById('pm-manager').value;
  const body = {
    name:        document.getElementById('pm-name').value.trim(),
    description: document.getElementById('pm-desc').value.trim() || null,
    budget:      parseFloat(document.getElementById('pm-budget').value),
    status:      document.getElementById('pm-status').value,
    start_date:  document.getElementById('pm-start').value || null,
    end_date:    document.getElementById('pm-end').value   || null,
    manager_id:  mgrVal ? parseInt(mgrVal) : null,
  };
  if (!body.name || !body.budget) { toast('Name and budget are required', 'error'); return; }
  try {
    if (EDIT_PROJECT_ID) {
      await api('PUT', `/api/projects/${EDIT_PROJECT_ID}`, body);
      toast('Project updated', 'success');
    } else {
      await api('POST', '/api/projects/', body);
      toast('Project created', 'success');
    }
    loadNotifCount();
    closeModal('project-modal');
    projects();
  } catch (e) { toast(e.message, 'error'); }
}

async function deleteProject(id, name) {
  if (!confirm(`Delete "${name}"? This cannot be undone.`)) return;
  try {
    await api('DELETE', `/api/projects/${id}`);
    toast('Project deleted', 'success');
    loadNotifCount();
    projects();
  } catch (e) { toast(e.message, 'error'); }
}

function openMetricsModal(projectId) {
  METRICS_PROJECT_ID = projectId;
  ['mm-invest','mm-rev','mm-cost','mm-life'].forEach(id => { document.getElementById(id).value = ''; });
  openModal('metrics-modal');
}

async function saveMetrics() {
  const body = {
    initial_investment: parseFloat(document.getElementById('mm-invest').value),
    annual_revenue:     parseFloat(document.getElementById('mm-rev').value),
    annual_cost:        parseFloat(document.getElementById('mm-cost').value),
    project_lifetime:   parseInt(document.getElementById('mm-life').value),
  };
  if (Object.values(body).some(v => isNaN(v))) { toast('Please fill all fields', 'error'); return; }
  try {
    await api('POST', `/api/projects/${METRICS_PROJECT_ID}/metrics`, body);
    toast('Metrics calculated & saved', 'success');
    closeModal('metrics-modal');
  } catch (e) { toast(e.message, 'error'); }
}

// ══════════════════════════════════════════════
//  PAGE: SELECTION & RANKING
// ══════════════════════════════════════════════
async function selection() {
  document.getElementById('main-content').innerHTML = `
    <div class="page-content">
      <div class="page-header">
        <div>
          <div class="page-title">Selection & Ranking</div>
          <div class="page-subtitle">Financial scoring · ROI · BCR · NPV · Payback Period</div>
        </div>
        <div class="page-actions">
          <button class="btn btn-ghost" onclick="downloadFile('/api/reports/selection/csv','cc_selection_report.csv')"><span class="material-symbols-outlined">download</span> Export CSV</button>
        </div>
      </div>
      <div class="card" style="margin-bottom:20px">
        <div class="card-title">Scoring Leaderboard <span style="font-size:11px;font-weight:400;color:var(--text-3)">Composite score out of 100</span></div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr><th>Rank</th><th>Project</th><th>Total Score</th><th>ROI %</th><th>BCR</th><th>Payback (yrs)</th><th>NPV</th><th>Status</th><th>Action</th></tr>
            </thead>
            <tbody id="ranking-tbody">
              <tr><td colspan="9" style="text-align:center;padding:24px;color:var(--text-3)">Loading...</td></tr>
            </tbody>
          </table>
        </div>
      </div>
      <div class="card">
        <div class="card-title">Score Breakdown by Component</div>
        <div class="chart-container" style="height:240px"><canvas id="score-chart"></canvas></div>
      </div>
    </div>`;

  try {
    const data = await api('GET', '/api/analytics/selection/leaderboard');
    const canSelect = ['Admin','Project Manager'].includes(CURRENT_USER?.role);

    document.getElementById('ranking-tbody').innerHTML = data.length
      ? data.map(r => {
          const score = r.scoring?.total_score;
          const pct   = score != null ? Math.min(score, 100) : 0;
          return `<tr>
            <td style="font-family:var(--font-mono);font-weight:700;color:var(--amber)">${r.rank}</td>
            <td>
              <div style="font-weight:600">${r.name}</div>
              ${r.is_selected ? '<span class="badge badge-violet">★ Selected</span>' : ''}
            </td>
            <td>
              <div class="score-bar-wrap">
                <div class="score-bar" style="width:90px"><div class="score-fill" style="width:${pct}%"></div></div>
                <span class="score-val">${score != null ? fmt(score, 1) : '—'}</span>
              </div>
            </td>
            <td style="font-family:var(--font-mono);color:${(r.financials?.roi || 0) > 0 ? 'var(--emerald)' : 'var(--rose)'}">${r.financials?.roi != null ? fmt(r.financials.roi, 1) + '%' : '—'}</td>
            <td style="font-family:var(--font-mono)">${r.financials?.bcr != null ? fmt(r.financials.bcr, 2) : '—'}</td>
            <td style="font-family:var(--font-mono)">${r.financials?.payback_period != null ? fmt(r.financials.payback_period, 1) : '—'}</td>
            <td style="font-family:var(--font-mono);color:${(r.financials?.npv || 0) > 0 ? 'var(--emerald)' : 'var(--rose)'}">${r.financials?.npv != null ? fmtK(r.financials.npv) : '—'}</td>
            <td>${statusBadge(r.status)}</td>
            <td>
              <div style="display:flex;gap:6px">
                ${canSelect && !r.is_selected ? `<button class="btn btn-ghost btn-sm" onclick="selectProject(${r.project_id},'${r.name.replace(/'/g,"\\'")}')"><span class="material-symbols-outlined">check</span> Select</button>` : ''}
                <button class="btn btn-ghost btn-sm" onclick="openMetricsModal(${r.project_id})"><span class="material-symbols-outlined">analytics</span> Metrics</button>
              </div>
            </td>
          </tr>`;
        }).join('')
      : `<tr><td colspan="9"><div class="empty-state"><div class="empty-icon"><span class="material-symbols-outlined">emoji_events</span></div><div class="empty-title">No scored projects yet</div><div class="empty-sub">Add financial metrics to projects first</div></div></td></tr>`;

    // Score breakdown stacked bar chart
    const top8 = data.slice(0, 8);
    new Chart(document.getElementById('score-chart'), {
      type: 'bar',
      data: {
        labels: top8.map(r => r.name.slice(0, 14)),
        datasets: [
          { label: 'ROI Score',     data: top8.map(r => r.scoring?.roi_score     || 0), backgroundColor: 'rgba(59,130,246,0.7)' },
          { label: 'BCR Score',     data: top8.map(r => r.scoring?.bcr_score     || 0), backgroundColor: 'rgba(16,185,129,0.7)' },
          { label: 'Payback Score', data: top8.map(r => r.scoring?.payback_score || 0), backgroundColor: 'rgba(245,158,11,0.7)' },
          { label: 'NPV Score',     data: top8.map(r => r.scoring?.eva_score     || 0), backgroundColor: 'rgba(139,92,246,0.7)' },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: { stacked: true, grid: { color: 'rgba(255,255,255,0.04)' } },
          y: { stacked: true, grid: { color: 'rgba(255,255,255,0.04)' }, max: 100 },
        },
      },
    });

  } catch (e) { toast(e.message, 'error'); }
}

async function selectProject(id, name) {
  if (!confirm(`Mark "${name}" as the selected project?`)) return;
  try {
    await api('POST', `/api/projects/selection/select/${id}`);
    toast(`${name} selected`, 'success');
    selection();
  } catch (e) { toast(e.message, 'error'); }
}

// ══════════════════════════════════════════════
//  PAGE: WBS TASKS
// ══════════════════════════════════════════════
async function wbs() {
  const canEdit = ['Admin','Project Manager'].includes(CURRENT_USER?.role);
  const canPM   = ['Admin','Project Manager'].includes(CURRENT_USER?.role);

  document.getElementById('main-content').innerHTML = `
    <div class="page-content">
      <div class="page-header">
        <div>
          <div class="page-title">WBS Tasks</div>
          <div class="page-subtitle">Work Breakdown Structure · Earned Value tracking</div>
        </div>
        <div class="page-actions">
          <select id="wbs-project-select" class="form-input" style="width:220px" onchange="loadWBSTasks(this.value)">
            <option value="">— Select Project —</option>
          </select>
          ${canPM ? `<button class="btn btn-primary" onclick="openTaskModal()" style="width:auto">+ Add Task</button>` : ''}
          <button class="btn btn-ghost" id="wbs-export-btn" style="display:none" onclick="exportWBS()"><span class="material-symbols-outlined">download</span> Export CSV</button>
        </div>
      </div>
      <div id="wbs-body">
        <div class="empty-state">
          <div class="empty-icon"><span class="material-symbols-outlined">assignment</span></div>
          <div class="empty-title">Select a project to view its tasks</div>
        </div>
      </div>
    </div>`;

  try {
    const projs = await api('GET', '/api/projects');
    window._allProjects = projs;
    const sel = document.getElementById('wbs-project-select');
    projs.forEach(p => {
      const opt = document.createElement('option');
      opt.value       = p.project_id;
      opt.textContent = p.name;
      sel.appendChild(opt);
    });

    if (WBS_PROJECT_ID) {
      sel.value = WBS_PROJECT_ID;
      loadWBSTasks(WBS_PROJECT_ID);
    }
  } catch (e) { toast(e.message, 'error'); }
}

async function loadWBSTasks(projectId) {
  WBS_PROJECT_ID = projectId ? parseInt(projectId) : null;
  const body      = document.getElementById('wbs-body');
  const exportBtn = document.getElementById('wbs-export-btn');

  if (!projectId) {
    exportBtn.style.display = 'none';
    body.innerHTML = `<div class="empty-state"><div class="empty-icon"><span class="material-symbols-outlined">assignment</span></div><div class="empty-title">Select a project to view tasks</div></div>`;
    return;
  }

  exportBtn.style.display = 'inline-flex';
  body.innerHTML = `<div style="display:flex;align-items:center;gap:12px;padding:20px;color:var(--text-3)"><div class="spinner"></div> Loading tasks...</div>`;

  try {
    const [tasks, evm] = await Promise.all([
      api('GET', `/api/projects/${projectId}/tasks`),
      api('GET', `/api/projects/${projectId}/evm`).catch(() => null),
    ]);

    const canPM = ['Admin','Project Manager'].includes(CURRENT_USER?.role);
    const canAny = true;

    // EVM Summary Strip
    let evmStrip = '';
    if (evm) {
      const cpiColor = parseFloat(evm.cpi) < 0.9 ? 'var(--rose)' : 'var(--emerald)';
      const spiColor = parseFloat(evm.spi) < 0.9 ? 'var(--rose)' : 'var(--emerald)';
      evmStrip = `
        <div style="display:flex;flex-wrap:wrap;gap:12px;margin-bottom:20px">
          ${[['BAC',evm.bac],['PV',evm.pv],['EV',evm.ev],['AC',evm.ac]].map(([l,v]) => `
            <div style="background:var(--bg-surface);border:1px solid var(--border);border-radius:var(--radius-md);padding:12px 18px;min-width:120px">
              <div style="font-family:var(--font-mono);font-size:10px;color:var(--text-3);text-transform:uppercase;margin-bottom:4px">${l}</div>
              <div style="font-family:var(--font-display);font-size:22px;font-weight:700">${fmtK(v)}</div>
            </div>`).join('')}
          <div style="background:var(--bg-surface);border:1px solid var(--border);border-radius:var(--radius-md);padding:12px 18px;min-width:100px">
            <div style="font-family:var(--font-mono);font-size:10px;color:var(--text-3);margin-bottom:4px">CPI</div>
            <div style="font-family:var(--font-display);font-size:22px;font-weight:700;color:${cpiColor}">${fmt(evm.cpi, 3)}</div>
          </div>
          <div style="background:var(--bg-surface);border:1px solid var(--border);border-radius:var(--radius-md);padding:12px 18px;min-width:100px">
            <div style="font-family:var(--font-mono);font-size:10px;color:var(--text-3);margin-bottom:4px">SPI</div>
            <div style="font-family:var(--font-display);font-size:22px;font-weight:700;color:${spiColor}">${fmt(evm.spi, 3)}</div>
          </div>
          <div style="background:var(--bg-surface);border:1px solid var(--border);border-radius:var(--radius-md);padding:12px 18px;min-width:120px">
            <div style="font-family:var(--font-mono);font-size:10px;color:var(--text-3);margin-bottom:4px">EAC</div>
            <div style="font-family:var(--font-display);font-size:22px;font-weight:700">${fmtK(evm.eac)}</div>
          </div>
          <div style="background:var(--bg-surface);border:1px solid var(--border);border-radius:var(--radius-md);padding:12px 18px;min-width:120px">
            <div style="font-family:var(--font-mono);font-size:10px;color:var(--text-3);margin-bottom:4px">ETC</div>
            <div style="font-family:var(--font-display);font-size:22px;font-weight:700">${fmtK(evm.etc)}</div>
          </div>
        </div>`;
    }

    const tasksHTML = !tasks.length
      ? `<tr><td colspan="9"><div class="empty-state"><div class="empty-icon"><span class="material-symbols-outlined">assignment</span></div><div class="empty-title">No tasks yet</div><div class="empty-sub">Add WBS tasks to start EVM tracking</div></div></td></tr>`
      : tasks.map((t, i) => {
          const pct       = Number(t.percent_complete || 0);
          const fillColor = pct >= 100 ? 'green' : pct >= 50 ? '' : pct >= 1 ? 'amber' : 'rose';
          return `<tr>
            <td style="color:var(--text-3);font-family:var(--font-mono)">${t.order_index || i + 1}</td>
            <td>
              <div style="font-weight:600">${t.task_name}</div>
              ${t.description ? `<div style="font-size:11px;color:var(--text-3);margin-top:1px">${t.description}</div>` : ''}
            </td>
            <td>${taskBadge(t.status)}</td>
            <td style="font-family:var(--font-mono);font-size:12px">${fmtK(t.planned_value)}</td>
            <td style="font-family:var(--font-mono);font-size:12px">${fmtK(t.actual_cost)}</td>
            <td style="font-family:var(--font-mono);font-size:12px">${fmtK(t.earned_value)}</td>
            <td style="font-family:var(--font-mono);font-size:12px">${pct}%</td>
            <td>
              <div class="progress-bar" style="min-width:90px">
                <div class="progress-fill ${fillColor}" style="width:${pct}%"></div>
              </div>
            </td>
            <td>
              <div style="display:flex;gap:5px">
                ${canAny ? `<button class="btn btn-ghost btn-sm" onclick="openTaskModal(${t.task_id})"><span class="material-symbols-outlined">edit</span></button>` : ''}
                ${canPM  ? `<button class="btn btn-ghost btn-sm" style="color:var(--rose)" onclick="deleteTask(${t.task_id},'${t.task_name.replace(/'/g,"\\'")}')"><span class="material-symbols-outlined">delete</span></button>` : ''}
              </div>
            </td>
          </tr>`;
        }).join('');

    body.innerHTML = evmStrip + `
      <div class="table-wrap">
        <table>
          <thead>
            <tr><th>#</th><th>Task Name</th><th>Status</th><th>PV</th><th>AC</th><th>EV</th><th>% Done</th><th>Progress</th><th>Actions</th></tr>
          </thead>
          <tbody>${tasksHTML}</tbody>
        </table>
      </div>`;

    window._currentTasks = tasks;

  } catch (e) {
    toast(e.message, 'error');
    body.innerHTML = `<div class="empty-state"><div class="empty-icon"><span class="material-symbols-outlined">warning</span></div><div class="empty-title">${e.message}</div></div>`;
  }
}

function openTaskModal(taskId = null) {
  if (!WBS_PROJECT_ID) { toast('Please select a project first', 'error'); return; }
  EDIT_TASK_ID = taskId;
  document.getElementById('task-modal-title').textContent = taskId ? 'Edit Task' : 'Add WBS Task';
  if (taskId) {
    const t = window._currentTasks?.find(x => x.task_id === taskId);
    if (t) {
      document.getElementById('tm-name').value   = t.task_name || '';
      document.getElementById('tm-desc').value   = t.description || '';
      document.getElementById('tm-pv').value     = t.planned_value || '';
      document.getElementById('tm-order').value  = t.order_index ?? 0;
      document.getElementById('tm-ac').value     = t.actual_cost || '';
      document.getElementById('tm-pct').value    = t.percent_complete || '';
      document.getElementById('tm-status').value = t.status || 'Not Started';
    }
  } else {
    ['tm-name','tm-desc','tm-pv','tm-ac','tm-pct'].forEach(id => { document.getElementById(id).value = ''; });
    document.getElementById('tm-order').value  = 0;
    document.getElementById('tm-status').value = 'Not Started';
  }
  openModal('task-modal');
}

async function saveTask() {
  const body = {
    task_name:        document.getElementById('tm-name').value.trim(),
    description:      document.getElementById('tm-desc').value.trim() || null,
    planned_value:    parseFloat(document.getElementById('tm-pv').value)    || 0,
    order_index:      parseInt(document.getElementById('tm-order').value)   || 0,
    actual_cost:      parseFloat(document.getElementById('tm-ac').value)    || 0,
    percent_complete: parseFloat(document.getElementById('tm-pct').value)   || 0,
    status:           document.getElementById('tm-status').value,
  };
  if (!body.task_name) { toast('Task name is required', 'error'); return; }
  try {
    if (EDIT_TASK_ID) {
      await api('PUT', `/api/projects/${WBS_PROJECT_ID}/tasks/${EDIT_TASK_ID}`, body);
      toast('Task updated', 'success');
    } else {
      await api('POST', `/api/projects/${WBS_PROJECT_ID}/tasks`, body);
      toast('Task added', 'success');
    }
    loadNotifCount();
    closeModal('task-modal');
    loadWBSTasks(WBS_PROJECT_ID);
  } catch (e) { toast(e.message, 'error'); }
}

async function deleteTask(id, name) {
  if (!confirm(`Delete task "${name}"?`)) return;
  try {
    await api('DELETE', `/api/projects/${WBS_PROJECT_ID}/tasks/${id}`);
    toast('Task deleted', 'success');
    loadNotifCount();
    loadWBSTasks(WBS_PROJECT_ID);
  } catch (e) { toast(e.message, 'error'); }
}

function exportWBS() {
  if (!WBS_PROJECT_ID) return;
  downloadFile(`/api/reports/project/${WBS_PROJECT_ID}/wbs/csv`, `project_${WBS_PROJECT_ID}_wbs.csv`);
}

async function evm() {
  document.getElementById('main-content').innerHTML = `
    <div class="page-content">
      <div class="page-header">
        <div>
          <div class="page-title">EVM Metrics</div>
          <div class="page-subtitle">Earned Value Management · Deep analytics per project</div>
        </div>
        <div class="page-actions">
          <select id="evm-project-select" class="form-input" style="width:220px" onchange="loadEVM(this.value)">
            <option value="">— Select Project —</option>
          </select>
        </div>
      </div>
      <div id="evm-body">
        <div class="empty-state">
          <div class="empty-icon"><span class="material-symbols-outlined">show_chart</span></div>
          <div class="empty-title">Select a project to view EVM metrics</div>
        </div>
      </div>
    </div>`;

  try {
    const projs = await api('GET', '/api/projects');
    window._allProjects = projs;
    const sel = document.getElementById('evm-project-select');
    projs.forEach(p => {
      const opt = document.createElement('option');
      opt.value       = p.project_id;
      opt.textContent = p.name;
      sel.appendChild(opt);
    });
    if (EVM_PROJECT_ID) { sel.value = EVM_PROJECT_ID; loadEVM(EVM_PROJECT_ID); }
  } catch (e) { toast(e.message, 'error'); }
}

async function loadEVM(projectId) {
  EVM_PROJECT_ID = projectId ? parseInt(projectId) : null;
  const body = document.getElementById('evm-body');
  if (!projectId) {
    body.innerHTML = `<div class="empty-state"><div class="empty-icon"><span class="material-symbols-outlined">show_chart</span></div><div class="empty-title">Select a project</div></div>`;
    return;
  }

  body.innerHTML = `<div style="display:flex;align-items:center;gap:12px;padding:20px;color:var(--text-3)"><div class="spinner"></div> Loading EVM data...</div>`;

  try {
    const trend = await api('GET', `/api/analytics/projects/${projectId}/evm/trend`);
    const e     = trend.current_evm;
    const cpiGood = parseFloat(e.cpi) >= 0.9;
    const spiGood = parseFloat(e.spi) >= 0.9;

    body.innerHTML = `
      <div class="kpi-grid" style="margin-bottom:20px">
        <div class="kpi-card blue">
          <div class="kpi-icon material-symbols-outlined">architecture</div>
          <div class="kpi-label">Planned Value (PV)</div>
          <div class="kpi-value">${fmtK(e.pv)}</div>
          <div class="kpi-sub">Budgeted work scheduled</div>
        </div>
        <div class="kpi-card green">
          <div class="kpi-icon material-symbols-outlined">task_alt</div>
          <div class="kpi-label">Earned Value (EV)</div>
          <div class="kpi-value">${fmtK(e.ev)}</div>
          <div class="kpi-sub">Value of work performed</div>
        </div>
        <div class="kpi-card amber">
          <div class="kpi-icon material-symbols-outlined">savings</div>
          <div class="kpi-label">Actual Cost (AC)</div>
          <div class="kpi-value">${fmtK(e.ac)}</div>
          <div class="kpi-sub">Real cost incurred</div>
        </div>
        <div class="kpi-card ${cpiGood ? 'green' : 'rose'}">
          <div class="kpi-icon material-symbols-outlined">settings</div>
          <div class="kpi-label">CPI</div>
          <div class="kpi-value" style="color:${cpiGood ? 'var(--emerald)' : 'var(--rose)'}">${fmt(e.cpi, 3)}</div>
          <div class="kpi-sub">${cpiGood ? 'On budget' : 'Over budget'}</div>
        </div>
        <div class="kpi-card ${spiGood ? 'green' : 'rose'}">
          <div class="kpi-icon">⏱</div>
          <div class="kpi-label">SPI</div>
          <div class="kpi-value" style="color:${spiGood ? 'var(--emerald)' : 'var(--rose)'}">${fmt(e.spi, 3)}</div>
          <div class="kpi-sub">${spiGood ? 'On schedule' : 'Behind schedule'}</div>
        </div>
        <div class="kpi-card blue">
          <div class="kpi-icon material-symbols-outlined">flag</div>
          <div class="kpi-label">EAC — Estimate at Completion</div>
          <div class="kpi-value">${fmtK(e.eac)}</div>
          <div class="kpi-sub">Projected final cost</div>
        </div>
        <div class="kpi-card blue">
          <div class="kpi-icon material-symbols-outlined">explore</div>
          <div class="kpi-label">ETC — Estimate to Complete</div>
          <div class="kpi-value">${fmtK(e.etc)}</div>
          <div class="kpi-sub">Remaining work cost</div>
        </div>
      </div>
      <div class="card">
        <div class="card-title">Cumulative EVM Trend — PV / EV / AC per Task</div>
        <div class="chart-container" style="height:280px"><canvas id="trend-chart"></canvas></div>
      </div>`;

    if (trend.trend && trend.trend.length > 0) {
      new Chart(document.getElementById('trend-chart'), {
        type: 'line',
        data: {
          labels: trend.trend.map(t => t.period),
          datasets: [
            { label: 'PV', data: trend.trend.map(t => t.pv), borderColor: '#3b82f6', backgroundColor: 'rgba(59,130,246,0.08)', tension: 0.4, fill: true,  pointRadius: 5 },
            { label: 'EV', data: trend.trend.map(t => t.ev), borderColor: '#10b981', backgroundColor: 'rgba(16,185,129,0.08)', tension: 0.4, fill: true,  pointRadius: 5 },
            { label: 'AC', data: trend.trend.map(t => t.ac), borderColor: '#f59e0b', backgroundColor: 'transparent',           tension: 0.4, fill: false, pointRadius: 5, borderDash: [5,4] },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            x: { grid: { color: 'rgba(255,255,255,0.04)' } },
            y: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { callback: v => fmtK(v) } },
          },
        },
      });
    } else {
      document.getElementById('trend-chart').parentElement.innerHTML = `
        <div class="empty-state" style="padding:40px">
          <div class="empty-icon"><span class="material-symbols-outlined">show_chart</span></div>
          <div class="empty-title">Add WBS tasks to generate trend data</div>
        </div>`;
    }

  } catch (e) {
    toast(e.message, 'error');
    body.innerHTML = `<div class="empty-state"><div class="empty-icon"><span class="material-symbols-outlined">warning</span></div><div class="empty-title">${e.message}</div></div>`;
  }
}

async function notifications() {
  document.getElementById('main-content').innerHTML = `
    <div class="page-content">
      <div class="page-header">
        <div>
          <div class="page-title">Notifications</div>
          <div class="page-subtitle">Project activity · Add · Edit · Delete events</div>
        </div>
        <div class="page-actions">
          <button class="btn btn-ghost" onclick="markAllRead()"><span class="material-symbols-outlined">done_all</span> Mark all read</button>
          <button class="btn btn-danger" onclick="deleteAllNotifications()"><span class="material-symbols-outlined">delete_sweep</span> Delete All</button>
        </div>
      </div>
      <div id="notif-list">
        <div style="display:flex;align-items:center;gap:12px;padding:20px;color:var(--text-3)">
          <div class="spinner"></div> Loading...
        </div>
      </div>
    </div>`;

  try {
    const data = await api('GET', '/api/notifications');
    window._notifications = data;
    renderNotifications(data);
  } catch (e) { toast(e.message, 'error'); }
}

function renderNotifications(data) {
  const container = document.getElementById('notif-list');
  if (!data.length) {
    container.innerHTML = `<div class="empty-state"><div class="empty-icon"><span class="material-symbols-outlined">notifications</span></div><div class="empty-title">No notifications</div><div class="empty-sub">All clear!</div></div>`;
    return;
  }
  const typeIcons = { danger:'warning', warning:'schedule', info:'info' };
  container.innerHTML = data.map(n => `
    <div class="notif-item ${!n.is_read ? 'unread' : ''}" onclick="markRead(${n.notification_id})">
      <div class="notif-icon ${n.type || 'info'}">${typeIcons[n.type] || 'ℹ️'}</div>
      <div class="notif-body" style="flex:1">
        <div class="notif-title">${n.title || 'Notification'}</div>
        <div class="notif-msg">${n.message}</div>
        <div class="notif-time">${new Date(n.created_at).toLocaleString()}</div>
      </div>
      ${!n.is_read ? `<div style="width:8px;height:8px;border-radius:50%;background:var(--blue-vivid);flex-shrink:0;margin-top:4px"></div>` : ''}
    </div>`).join('');
}

async function markRead(id) {
  try {
    await api('PUT', `/api/notifications/${id}/read`);
    loadNotifCount();
    const n = window._notifications?.find(x => x.notification_id === id);
    if (n) { n.is_read = true; renderNotifications(window._notifications); }
  } catch {}
}

async function markAllRead() {
  const unread = (window._notifications || []).filter(n => !n.is_read);
  await Promise.all(unread.map(n => api('PUT', `/api/notifications/${n.notification_id}/read`).catch(() => {})));
  loadNotifCount();
  notifications();
  toast('All marked as read', 'success');
}

async function users() {
  if (CURRENT_USER?.role !== 'Admin') { navigate('dashboard'); return; }

  document.getElementById('main-content').innerHTML = `
    <div class="page-content">
      <div class="page-header">
        <div>
          <div class="page-title">User Management</div>
          <div class="page-subtitle">Admin panel · Role-Based Access Control</div>
        </div>
        <div class="page-actions">
          <button class="btn btn-primary" onclick="openUserModal()" style="width:auto">+ Add User</button>
        </div>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr><th>ID</th><th>Username</th><th>Email</th><th>Role</th><th>Status</th><th>Joined</th><th>Actions</th></tr>
          </thead>
          <tbody id="users-tbody">
            <tr><td colspan="7" style="text-align:center;padding:24px;color:var(--text-3)">Loading...</td></tr>
          </tbody>
        </table>
      </div>
    </div>`;

  try {
    const data = await api('GET', '/api/users');
    window._allUsers = data;
    const roleColor = { 'Admin':'rose', 'Project Manager':'amber', 'Team Member':'blue' };

    document.getElementById('users-tbody').innerHTML = data.map(u => `<tr>
      <td style="font-family:var(--font-mono);color:var(--text-3)">${u.user_id}</td>
      <td>
        <div style="display:flex;align-items:center;gap:10px">
          <div style="width:28px;height:28px;border-radius:50%;background:linear-gradient(135deg,var(--blue-vivid),var(--violet));
                      display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:700;color:white;flex-shrink:0">
            ${u.username.slice(0, 2).toUpperCase()}
          </div>
          <span style="font-weight:600">${u.username}</span>
        </div>
      </td>
      <td style="color:var(--text-2)">${u.email}</td>
      <td>
        ${u.user_id === CURRENT_USER?.user_id
          ? `<span class="badge badge-${roleColor[u.role] || 'gray'}">${u.role}</span>`
          : `<select class="role-select role-select-${roleColor[u.role] || 'gray'}"
                     onchange="changeUserRole(${u.user_id}, this.value, this)">
               <option value="Admin"           ${u.role === 'Admin'           ? 'selected' : ''}>Admin</option>
               <option value="Project Manager" ${u.role === 'Project Manager' ? 'selected' : ''}>Project Manager</option>
               <option value="Team Member"     ${u.role === 'Team Member'     ? 'selected' : ''}>Team Member</option>
             </select>`
        }
      </td>
      <td>${u.is_active ? `<span class="badge badge-green">Active</span>` : `<span class="badge badge-rose">Inactive</span>`}</td>
      <td style="font-family:var(--font-mono);font-size:11px;color:var(--text-3)">${new Date(u.created_at).toLocaleDateString()}</td>
      <td>
        ${u.is_active && u.user_id !== CURRENT_USER?.user_id
          ? `<button class="btn btn-ghost btn-sm" style="color:var(--rose)"
                     onclick="deactivateUser(${u.user_id},'${u.username.replace(/'/g,"\\'")}')">Deactivate</button>`
          : ''}
      </td>
    </tr>`).join('');

  } catch (e) { toast(e.message, 'error'); }
}

function openUserModal() {
  ['um-username','um-email','um-pass'].forEach(id => { document.getElementById(id).value = ''; });
  document.getElementById('um-role').value = 'Team Member';
  openModal('user-modal');
}

async function saveUser() {
  const body = {
    username: document.getElementById('um-username').value.trim(),
    email:    document.getElementById('um-email').value.trim(),
    password: document.getElementById('um-pass').value,
    role:     document.getElementById('um-role').value,
  };
  if (!body.username || !body.email || !body.password) { toast('All fields are required', 'error'); return; }
  try {
    await api('POST', '/api/users/', body);
    toast('User created', 'success');
    closeModal('user-modal');
    users();
  } catch (e) { toast(e.message, 'error'); }
}

async function deactivateUser(id, name) {
  if (!confirm(`Deactivate account "${name}"? They will lose all access.`)) return;
  try {
    await api('DELETE', `/api/users/${id}`);
    toast(`${name} deactivated`, 'success');
    users();
  } catch (e) { toast(e.message, 'error'); }
}

async function changeUserRole(userId, newRole, selectEl) {
  const oldRole = selectEl.dataset.prev || selectEl.querySelector('option[selected]')?.value;
  try {
    await api('PUT', `/api/users/${userId}`, { role: newRole });
    const roleColor = { 'Admin':'rose', 'Project Manager':'amber', 'Team Member':'blue' };
    selectEl.className = `role-select role-select-${roleColor[newRole] || 'gray'}`;
    selectEl.dataset.prev = newRole;
    toast(`Role updated to "${newRole}"`, 'success');
  } catch (e) {
    toast(e.message, 'error');
    users(); // re-render to restore original value
  }
}

// ══════════════════════════════════════════════
//  PAGE: GANTT CHART
// ══════════════════════════════════════════════
async function gantt() {
  document.getElementById('main-content').innerHTML = `
    <div class="page-content">
      <div class="page-header">
        <div>
          <div class="page-title">Gantt Chart</div>
          <div class="page-subtitle">Timeline view · Projects & WBS tasks</div>
        </div>
        <div class="page-actions">
          <select id="gantt-project-select" class="form-input" style="width:220px" onchange="loadGantt(this.value)">
            <option value="">— Select Project —</option>
          </select>
        </div>
      </div>
      <div id="gantt-body">
        <div class="empty-state">
          <div class="empty-icon"><span class="material-symbols-outlined">calendar_month</span></div>
          <div class="empty-title">Select a project to view its Gantt chart</div>
          <div class="empty-sub">Tasks must have start and end dates for timeline rendering</div>
        </div>
      </div>
    </div>`;

  try {
    const projs = await api('GET', '/api/projects');
    window._allProjects = projs;
    const sel = document.getElementById('gantt-project-select');
    projs.forEach(p => {
      const opt = document.createElement('option');
      opt.value = p.project_id;
      opt.textContent = p.name;
      sel.appendChild(opt);
    });
  } catch (e) { toast(e.message, 'error'); }
}

async function loadGantt(projectId) {
  const body = document.getElementById('gantt-body');
  if (!projectId) {
    body.innerHTML = `<div class="empty-state"><div class="empty-icon"><span class="material-symbols-outlined">calendar_month</span></div><div class="empty-title">Select a project</div></div>`;
    return;
  }

  body.innerHTML = `<div style="display:flex;align-items:center;gap:12px;padding:20px;color:var(--text-3)"><div class="spinner"></div> Building Gantt chart...</div>`;

  try {
    const [project, tasks] = await Promise.all([
      api('GET', `/api/projects/${projectId}`),
      api('GET', `/api/projects/${projectId}/tasks`),
    ]);

    const proj = window._allProjects?.find(p => p.project_id == projectId);

    // ── Build timeline from project dates + tasks ──
    const projStart = proj?.start_date ? new Date(proj.start_date) : new Date();
    const projEnd   = proj?.end_date   ? new Date(proj.end_date)   : new Date(Date.now() + 90*864e5);
    const today     = new Date();

    const totalDays = Math.max(1, Math.ceil((projEnd - projStart) / 864e5));

    // Generate week labels
    const weeks = [];
    let d = new Date(projStart);
    while (d <= projEnd) {
      weeks.push(new Date(d));
      d.setDate(d.getDate() + 7);
    }

    const BAR_H  = 36;
    const ROW_H  = 48;
    const LABEL_W = 200;
    const CHART_W = Math.max(600, weeks.length * 80);
    const SVG_H   = (tasks.length + 1) * ROW_H + 60;

    // Color helpers
    const statusColors = {
      'Completed':   '#10b981',
      'In Progress': '#3b82f6',
      'Not Started': '#475569',
    };

    const pctToWidth = (pct, totalW) => Math.max(4, (pct / 100) * totalW);

    const dayOffset = (dateStr, fallback) => {
      if (!dateStr) return fallback;
      const dt = new Date(dateStr);
      const diff = Math.ceil((dt - projStart) / 864e5);
      return Math.max(0, Math.min(diff, totalDays));
    };

    const todayX = LABEL_W + (Math.ceil((today - projStart) / 864e5) / totalDays) * CHART_W;

    let svgRows = '';

    // ── Project bar (row 0) ──
    svgRows += `
      <rect x="0" y="8" width="${LABEL_W - 12}" height="${BAR_H}" rx="6" fill="#1a2235"/>
      <text x="10" y="31" fill="#f1f5f9" font-family="Syne,sans-serif" font-weight="700" font-size="13">${(proj?.name || 'Project').slice(0,26)}</text>
      <rect x="${LABEL_W}" y="8" width="${CHART_W}" height="${BAR_H}" rx="6" fill="#1a2235" opacity="0.5"/>
      <rect x="${LABEL_W}" y="14" width="${CHART_W}" height="${BAR_H - 12}" rx="4" fill="#1f2b40"/>
      <rect x="${LABEL_W}" y="14" width="${CHART_W}" height="${BAR_H - 12}" rx="4" fill="url(#projGrad)" opacity="0.7"/>
      <text x="${LABEL_W + 8}" y="31" fill="#f1f5f9" font-family="DM Mono,monospace" font-size="11">
        ${proj?.start_date || '—'} → ${proj?.end_date || '—'}  ·  ${totalDays}d
      </text>`;

    // ── Week grid lines ──
    weeks.forEach((w, i) => {
      const x = LABEL_W + (i / (weeks.length || 1)) * CHART_W;
      const label = w.toLocaleDateString('en', { month:'short', day:'numeric' });
      svgRows += `
        <line x1="${x}" y1="0" x2="${x}" y2="${SVG_H}" stroke="#1a2235" stroke-width="1"/>
        <text x="${x + 4}" y="${SVG_H - 8}" fill="#475569" font-family="DM Mono,monospace" font-size="9">${label}</text>`;
    });

    // ── Task bars ──
    tasks.forEach((t, idx) => {
      const y   = (idx + 1) * ROW_H + 8;
      const pct = Number(t.percent_complete || 0);
      const color = statusColors[t.status] || '#475569';

      // Use order_index as proxy for relative position if no dates
      const startFrac = tasks.length > 1 ? idx / tasks.length : 0;
      const durFrac   = tasks.length > 1 ? 1 / tasks.length  : 1;
      const barX      = LABEL_W + startFrac * CHART_W;
      const barW      = Math.max(30, durFrac * CHART_W - 4);
      const fillW     = pctToWidth(pct, barW);

      svgRows += `
        <rect x="0" y="${y}" width="${LABEL_W - 12}" height="${BAR_H}" rx="5" fill="#111827"/>
        <text x="10" y="${y + 14}" fill="#94a3b8" font-family="DM Sans,sans-serif" font-size="11" font-weight="600">
          ${(t.task_name).slice(0,26)}
        </text>
        <text x="10" y="${y + 28}" fill="#475569" font-family="DM Mono,monospace" font-size="9">${t.status}</text>

        <!-- bar background -->
        <rect x="${barX}" y="${y + 6}" width="${barW}" height="${BAR_H - 14}" rx="4" fill="#1a2235"/>
        <!-- progress fill -->
        <rect x="${barX}" y="${y + 6}" width="${fillW}" height="${BAR_H - 14}" rx="4" fill="${color}" opacity="0.85"/>
        <!-- pct label -->
        <text x="${barX + fillW + 4}" y="${y + 18}" fill="${color}" font-family="DM Mono,monospace" font-size="10" font-weight="600">${pct}%</text>
        <!-- EV / PV mini info -->
        <text x="${barX + 6}" y="${y + 26}" fill="rgba(255,255,255,0.5)" font-family="DM Mono,monospace" font-size="9">
          PV:${fmtK(t.planned_value)} AC:${fmtK(t.actual_cost)}
        </text>`;
    });

    // ── Today line ──
    if (todayX >= LABEL_W && todayX <= LABEL_W + CHART_W) {
      svgRows += `
        <line x1="${todayX}" y1="0" x2="${todayX}" y2="${SVG_H - 20}" stroke="#f43f5e" stroke-width="1.5" stroke-dasharray="4,3"/>
        <text x="${todayX + 4}" y="16" fill="#f43f5e" font-family="DM Mono,monospace" font-size="9">TODAY</text>`;
    }

    body.innerHTML = `
      <div class="card" style="overflow-x:auto;padding:20px">
        <div class="card-title" style="margin-bottom:16px">
          ${proj?.name || 'Project'} — Timeline
          <span style="font-weight:400;font-size:11px;color:var(--text-3)">${tasks.length} tasks · ${totalDays} days</span>
        </div>
        <svg width="${LABEL_W + CHART_W}" height="${SVG_H}"
             xmlns="http:
          <defs>
            <linearGradient id="projGrad" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%"   stop-color="#3b82f6" stop-opacity="0.7"/>
              <stop offset="100%" stop-color="#8b5cf6" stop-opacity="0.5"/>
            </linearGradient>
          </defs>
          <rect width="${LABEL_W + CHART_W}" height="${SVG_H}" fill="#080c14" rx="12"/>
          ${svgRows}
        </svg>
      </div>

      <div style="display:flex;gap:16px;margin-top:16px;flex-wrap:wrap">
        <div style="display:flex;align-items:center;gap:6px;font-size:12px;font-family:var(--font-mono);color:var(--text-2)">
          <div style="width:12px;height:4px;border-radius:2px;background:#10b981"></div> Completed
        </div>
        <div style="display:flex;align-items:center;gap:6px;font-size:12px;font-family:var(--font-mono);color:var(--text-2)">
          <div style="width:12px;height:4px;border-radius:2px;background:#3b82f6"></div> In Progress
        </div>
        <div style="display:flex;align-items:center;gap:6px;font-size:12px;font-family:var(--font-mono);color:var(--text-2)">
          <div style="width:12px;height:4px;border-radius:2px;background:#475569"></div> Not Started
        </div>
        <div style="display:flex;align-items:center;gap:6px;font-size:12px;font-family:var(--font-mono);color:var(--text-2)">
          <div style="width:2px;height:14px;background:#f43f5e"></div> Today
        </div>
      </div>`;

  } catch (e) {
    toast(e.message, 'error');
    body.innerHTML = `<div class="empty-state"><div class="empty-icon"><span class="material-symbols-outlined">warning</span></div><div class="empty-title">${e.message}</div></div>`;
  }
}

// ══════════════════════════════════════════════
//  PAGE: MEMBER MANAGEMENT
// ══════════════════════════════════════════════
let MEMBER_PROJECT_ID = null;

async function members() {
  const canPM = ['Admin','Project Manager'].includes(CURRENT_USER?.role);

  document.getElementById('main-content').innerHTML = `
    <div class="page-content">
      <div class="page-header">
        <div>
          <div class="page-title">Member Management</div>
          <div class="page-subtitle">Assign team members to projects · Track roles</div>
        </div>
        <div class="page-actions">
          <select id="mbr-proj-select" class="form-input" style="width:220px" onchange="loadProjectMembers(this.value)">
            <option value="">— Select Project —</option>
          </select>
          ${canPM ? `<button class="btn btn-primary" style="width:auto" onclick="openMemberModal()">+ Add Member</button>` : ''}
        </div>
      </div>
      <div id="members-body">
        <div class="empty-state">
          <div class="empty-icon"><span class="material-symbols-outlined">group</span></div>
          <div class="empty-title">Select a project to manage its members</div>
        </div>
      </div>
    </div>`;

  try {
    const [projs, allUsers] = await Promise.all([
      api('GET', '/api/projects'),
      api('GET', '/api/users/directory'),
    ]);
    window._allProjects = projs;
    window._allUsers    = allUsers;

    const sel = document.getElementById('mbr-proj-select');
    projs.forEach(p => {
      const opt = document.createElement('option');
      opt.value       = p.project_id;
      opt.textContent = p.name;
      sel.appendChild(opt);
    });
  } catch (e) { toast(e.message, 'error'); }
}

async function loadProjectMembers(projectId) {
  MEMBER_PROJECT_ID = projectId ? parseInt(projectId) : null;
  const body  = document.getElementById('members-body');
  const canPM = ['Admin','Project Manager'].includes(CURRENT_USER?.role);

  if (!projectId) {
    body.innerHTML = `<div class="empty-state"><div class="empty-icon"><span class="material-symbols-outlined">group</span></div><div class="empty-title">Select a project</div></div>`;
    return;
  }

  body.innerHTML = `<div style="display:flex;align-items:center;gap:12px;padding:20px;color:var(--text-3)"><div class="spinner"></div> Loading members...</div>`;

  try {
    const membersList = await api('GET', `/api/projects/${projectId}/members`);
    window._currentMembers = membersList;

    if (!membersList.length) {
      body.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon"><span class="material-symbols-outlined">group</span></div>
          <div class="empty-title">No members assigned yet</div>
          <div class="empty-sub">Add team members to this project</div>
        </div>`;
      return;
    }

    const roleColor = { 'Admin':'rose', 'Project Manager':'amber', 'Team Member':'blue' };

    body.innerHTML = `
      <div class="table-wrap">
        <table>
          <thead>
            <tr><th>#</th><th>Member</th><th>System Role</th><th>Role in Project</th><th>Assigned</th>${canPM ? '<th>Actions</th>' : ''}</tr>
          </thead>
          <tbody>
            ${membersList.map((m, i) => `<tr>
              <td style="font-family:var(--font-mono);color:var(--text-3)">${i + 1}</td>
              <td>
                <div style="display:flex;align-items:center;gap:10px">
                  <div style="width:32px;height:32px;border-radius:50%;background:linear-gradient(135deg,var(--blue-vivid),var(--violet));
                              display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;color:white;flex-shrink:0">
                    ${(m.username || '?').slice(0,2).toUpperCase()}
                  </div>
                  <span style="font-weight:600">${m.username || '—'}</span>
                </div>
              </td>
              <td>—</td>
              <td><span style="font-size:12px;color:var(--text-2)">${m.role_in_project || '—'}</span></td>
              <td style="font-family:var(--font-mono);font-size:11px;color:var(--text-3)">${new Date(m.assigned_at).toLocaleDateString()}</td>
              ${canPM ? `<td>
                ${m.is_manager ? '' : `<button class="btn btn-ghost btn-sm" style="color:var(--rose)"
                        onclick="removeMember(${m.user_id},'${(m.username||'').replace(/'/g,"\\'")}')">Remove</button>`}
              </td>` : ''}
            </tr>`).join('')}
          </tbody>
        </table>
      </div>`;
  } catch (e) { toast(e.message, 'error'); }
}

async function openMemberModal() {
  const modal = document.getElementById('member-modal');

  // Populate project select
  const projSel = document.getElementById('mbr-project');
  projSel.innerHTML = (window._allProjects || []).map(p =>
    `<option value="${p.project_id}">${p.name}</option>`).join('');
  if (MEMBER_PROJECT_ID) projSel.value = MEMBER_PROJECT_ID;

  // Populate user select — fetch all users if not cached
  if (!window._allUsers?.length) {
    try { window._allUsers = await api('GET', '/api/users/directory'); } catch {}
  }
  const userSel = document.getElementById('mbr-user');
  userSel.innerHTML = (window._allUsers || []).map(u =>
    `<option value="${u.user_id}">${u.username} (${u.role})</option>`).join('');

  document.getElementById('mbr-role').value = '';
  openModal('member-modal');
}

async function saveMember() {
  const projectId = parseInt(document.getElementById('mbr-project').value);
  const userId    = parseInt(document.getElementById('mbr-user').value);
  const role      = document.getElementById('mbr-role').value.trim() || null;

  if (!projectId || !userId) { toast('Select a project and user', 'error'); return; }

  try {
    await api('POST', `/api/projects/${projectId}/members`, { user_id: userId, role_in_project: role });
    toast('Member added', 'success');
    loadNotifCount();
    closeModal('member-modal');
    if (MEMBER_PROJECT_ID === projectId) loadProjectMembers(projectId);
  } catch (e) { toast(e.message, 'error'); }
}

async function removeMember(userId, username) {
  if (!MEMBER_PROJECT_ID) return;
  if (!confirm(`Remove "${username}" from this project?`)) return;
  try {
    await api('DELETE', `/api/projects/${MEMBER_PROJECT_ID}/members/${userId}`);
    toast(`${username} removed`, 'success');
    loadNotifCount();
    loadProjectMembers(MEMBER_PROJECT_ID);
  } catch (e) { toast(e.message, 'error'); }
}

// ══════════════════════════════════════════════
//  COMMENTS — injected into WBS / Project pages
// ══════════════════════════════════════════════
let COMMENT_PROJECT_ID = null;
let EDIT_COMMENT_ID    = null;

async function loadComments(projectId, containerId) {
  COMMENT_PROJECT_ID = projectId;
  const container = document.getElementById(containerId);
  if (!container) return;

  try {
    const comments = await api('GET', `/api/projects/${projectId}/comments`);
    window._comments = comments;

    const canEdit = true; // anyone can comment
    container.innerHTML = `
      <div class="card" style="margin-top:20px">
        <div class="card-title">
          <span class="material-symbols-outlined">chat</span> Discussion
          <button class="btn btn-ghost btn-sm" onclick="openCommentModal()">+ Add Comment</button>
        </div>
        ${!comments.length
          ? `<div class="empty-state" style="padding:32px">
               <div class="empty-icon" style="font-size:28px"><span class="material-symbols-outlined">chat</span></div>
               <div class="empty-title">No comments yet</div>
               <div class="empty-sub">Be the first to comment on this project</div>
             </div>`
          : comments.map(c => `
            <div style="display:flex;gap:14px;padding:16px 0;border-bottom:1px solid var(--border)">
              <div style="width:36px;height:36px;border-radius:50%;background:linear-gradient(135deg,var(--blue-vivid),var(--violet));
                          display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;color:white;flex-shrink:0">
                ${(c.author_username || '?').slice(0,2).toUpperCase()}
              </div>
              <div style="flex:1;min-width:0">
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px">
                  <span style="font-weight:600;font-size:13px">${c.author_username || '—'}</span>
                  <span style="font-size:11px;color:var(--text-3);font-family:var(--font-mono)">${new Date(c.created_at).toLocaleString()}</span>
                  ${c.created_at !== c.updated_at ? `<span style="font-size:10px;color:var(--text-3)">(edited)</span>` : ''}
                </div>
                <div style="font-size:13px;color:var(--text-2);line-height:1.6;white-space:pre-wrap">${c.content}</div>
                ${c.user_id === CURRENT_USER?.user_id || CURRENT_USER?.role === 'Admin'
                  ? `<div style="display:flex;gap:8px;margin-top:8px">
                       <button class="btn btn-ghost btn-sm" onclick="openCommentModal(${c.comment_id})"><span class="material-symbols-outlined">edit</span> Edit</button>
                       <button class="btn btn-ghost btn-sm" style="color:var(--rose)" onclick="deleteComment(${c.comment_id})"><span class="material-symbols-outlined">delete</span> Delete</button>
                     </div>`
                  : ''}
              </div>
            </div>`).join('')}
      </div>`;
  } catch (e) {
    if (container) container.innerHTML = '';
  }
}

function openCommentModal(commentId = null) {
  EDIT_COMMENT_ID = commentId;
  document.getElementById('comment-modal-title').textContent = commentId ? 'Edit Comment' : 'Add Comment';
  if (commentId) {
    const c = window._comments?.find(x => x.comment_id === commentId);
    document.getElementById('cm-content').value = c?.content || '';
  } else {
    document.getElementById('cm-content').value = '';
  }
  openModal('comment-modal');
}

async function saveComment() {
  const content = document.getElementById('cm-content').value.trim();
  if (!content) { toast('Comment cannot be empty', 'error'); return; }
  if (!COMMENT_PROJECT_ID) { toast('No project selected', 'error'); return; }

  try {
    if (EDIT_COMMENT_ID) {
      await api('PUT', `/api/projects/${COMMENT_PROJECT_ID}/comments/${EDIT_COMMENT_ID}`, { content });
      toast('Comment updated', 'success');
    } else {
      await api('POST', `/api/projects/${COMMENT_PROJECT_ID}/comments`, { content });
      toast('Comment posted', 'success');
    }
    loadNotifCount();
    closeModal('comment-modal');
    loadComments(COMMENT_PROJECT_ID, 'comments-section');
  } catch (e) { toast(e.message, 'error'); }
}

async function deleteComment(commentId) {
  if (!confirm('Delete this comment?')) return;
  try {
    await api('DELETE', `/api/projects/${COMMENT_PROJECT_ID}/comments/${commentId}`);
    toast('Comment deleted', 'success');
    loadComments(COMMENT_PROJECT_ID, 'comments-section');
  } catch (e) { toast(e.message, 'error'); }
}

// ══════════════════════════════════════════════
//  PAGE: REPORTS — updated with PDF + Comments
// ══════════════════════════════════════════════
async function reports() {
  document.getElementById('main-content').innerHTML = `
    <div class="page-content">
      <div class="page-header">
        <div>
          <div class="page-title">Reports</div>
          <div class="page-subtitle">PDF reports · CSV exports · API documentation</div>
        </div>
      </div>

      <!-- PDF Reports section -->
      <div style="margin-bottom:20px">
        <div class="card-title" style="font-size:13px;color:var(--text-2);letter-spacing:.08em;text-transform:uppercase;margin-bottom:12px;font-family:var(--font-mono)">
          <span class="material-symbols-outlined">picture_as_pdf</span> PDF Reports
        </div>
        <div class="grid-2" style="margin-bottom:12px">
          <div class="card">
            <div style="font-size:36px;margin-bottom:12px"><span class="material-symbols-outlined">folder_open</span></div>
            <div class="card-title" style="margin-bottom:8px">Portfolio Summary PDF</div>
            <p style="color:var(--text-2);font-size:13px;line-height:1.6;margin-bottom:20px">
              Executive overview of all projects — status, EVM indicators (CPI/SPI), budget,
              risk flags, and composite scores. Professional dark-theme layout ready for client delivery.
            </p>
            <button class="btn btn-primary" style="width:auto"
                    onclick="downloadFile('/api/pdf/portfolio','portfolio_report.pdf')">
              <span class="material-symbols-outlined">picture_as_pdf</span> Download Portfolio PDF
            </button>
          </div>
          <div class="card">
            <div style="font-size:36px;margin-bottom:12px"><span class="material-symbols-outlined">assignment</span></div>
            <div class="card-title" style="margin-bottom:8px">Single Project Full Report</div>
            <p style="color:var(--text-2);font-size:13px;line-height:1.6;margin-bottom:20px">
              Detailed per-project PDF: EVM KPIs, WBS task breakdown, financial scoring (ROI/BCR/NPV),
              and variance analysis. Generated per project for client-ready delivery.
            </p>
            <div style="display:flex;gap:8px;flex-wrap:wrap" id="pdf-project-btns">
              <div style="color:var(--text-3)">Loading projects...</div>
            </div>
          </div>
        </div>
      </div>

      <!-- CSV Exports section -->
      <div style="margin-bottom:20px">
        <div class="card-title" style="font-size:13px;color:var(--text-2);letter-spacing:.08em;text-transform:uppercase;margin-bottom:12px;font-family:var(--font-mono)">
          <span class="material-symbols-outlined">table_chart</span> CSV Exports
        </div>
        <div class="grid-2">
          <div class="card">
            <div style="font-size:36px;margin-bottom:12px"><span class="material-symbols-outlined">table_chart</span></div>
            <div class="card-title" style="margin-bottom:8px">Dashboard Report</div>
            <p style="color:var(--text-2);font-size:13px;line-height:1.6;margin-bottom:20px">
              Full EVM metrics for all projects — CPI, SPI, EAC, BAC, over-budget and behind-schedule flags.
            </p>
            <button class="btn btn-ghost"
                    onclick="downloadFile('/api/reports/dashboard/csv','cc_dashboard_report.csv')"><span class="material-symbols-outlined">download</span> Dashboard CSV</button>
          </div>
          <div class="card">
            <div style="font-size:36px;margin-bottom:12px"><span class="material-symbols-outlined">emoji_events</span></div>
            <div class="card-title" style="margin-bottom:8px">Selection & Ranking Report</div>
            <p style="color:var(--text-2);font-size:13px;line-height:1.6;margin-bottom:20px">
              Ranked projects with ROI, BCR, Payback Period, NPV, and composite selection scores.
            </p>
            <button class="btn btn-ghost"
                    onclick="downloadFile('/api/reports/selection/csv','cc_selection_report.csv')"><span class="material-symbols-outlined">download</span> Selection CSV</button>
          </div>
        </div>
      </div>

      <!-- WBS per project -->
      <div class="card" style="margin-bottom:20px">
        <div class="card-title">WBS Task Report — Per Project</div>
        <p style="color:var(--text-2);font-size:13px;margin-bottom:16px">
          Work breakdown structure with PV, AC, EV, and completion percentages.
        </p>
        <div style="display:flex;gap:10px;flex-wrap:wrap" id="wbs-export-btns">
          <div style="color:var(--text-3)">Loading...</div>
        </div>
      </div>

      <!-- API Docs -->
      <div class="card">
        <div class="card-title">API Documentation</div>
        <p style="color:var(--text-2);font-size:13px;margin-bottom:16px">
          Interactive API explorer — test all endpoints directly from the browser.
        </p>
        <div style="display:flex;gap:10px;flex-wrap:wrap">
          <button class="btn btn-ghost" onclick="window.open('${API}/docs','_blank')">🔗 Swagger UI</button>
          <button class="btn btn-ghost" onclick="window.open('${API}/redoc','_blank')">📘 ReDoc</button>
          <button class="btn btn-ghost" onclick="window.open('${API}/health','_blank')">💚 Health Check</button>
        </div>
      </div>
    </div>`;

  try {
    const projs = await api('GET', '/api/projects');

    // PDF project buttons
    document.getElementById('pdf-project-btns').innerHTML = projs.length
      ? projs.map(p => `
          <button class="btn btn-primary btn-sm" style="width:auto"
                  onclick="downloadFile('/api/pdf/project/${p.project_id}','${p.name.replace(/'/g,'').slice(0,30)}_report.pdf')">
            <span class="material-symbols-outlined">description</span> ${p.name.slice(0, 20)}
          </button>`).join('')
      : `<span style="color:var(--text-3)">No projects available</span>`;

    // WBS CSV buttons
    document.getElementById('wbs-export-btns').innerHTML = projs.length
      ? projs.map(p => `
          <button class="btn btn-ghost btn-sm"
                  onclick="downloadFile('/api/reports/project/${p.project_id}/wbs/csv','${p.name.replace(/'/g,'').slice(0,30)}_wbs.csv')">
            <span class="material-symbols-outlined">download</span> ${p.name.slice(0, 22)}
          </button>`).join('')
      : `<span style="color:var(--text-3)">No projects available</span>`;
  } catch {}
}

// ══════════════════════════════════════════════
//  PATCH: Add comments section to WBS page
// ══════════════════════════════════════════════
// Override loadWBSTasks to append comments at bottom
const _originalLoadWBSTasks = loadWBSTasks;
loadWBSTasks = async function(projectId) {
  await _originalLoadWBSTasks(projectId);
  if (projectId) {
    // Append comment section container
    const mc = document.getElementById('main-content');
    const existing = document.getElementById('comments-section');
    if (!existing) {
      const div = document.createElement('div');
      div.id = 'comments-section';
      mc.querySelector('.page-content')?.appendChild(div);
    }
    loadComments(parseInt(projectId), 'comments-section');
  }
};

// ══════════════════════════════════════════════
//  CSS: Additional styles injected at runtime
// ══════════════════════════════════════════════
(function injectStyles() {
  const style = document.createElement('style');
  style.textContent = `
    /* Gantt SVG hover */
    svg rect[data-task]:hover { opacity:1 !important; cursor:pointer; }

    /* Comment section smooth load */
    #comments-section { animation: slideUp 0.25s ease; }

    /* Member grid cards */
    .member-card {
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: var(--radius-lg);
      padding: 20px;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 10px;
      text-align: center;
      transition: all var(--transition);
    }
    .member-card:hover {
      border-color: var(--border-lit);
      transform: translateY(-2px);
      box-shadow: 0 8px 24px rgba(0,0,0,0.3);
    }
  `;
  document.head.appendChild(style);
})();

// ══════════════════════════════════════════════
//  PROFILE PAGE
// ══════════════════════════════════════════════
async function profile() {
  const mc = document.getElementById('main-content');
  mc.innerHTML = `
    <div class="page-content">
      <div class="page-header">
        <div>
          <div class="page-title">My Profile</div>
          <div class="page-subtitle">Personal details · Enrolled projects · Account settings</div>
        </div>
      </div>
      <div id="profile-body"><div class="spinner" style="margin:60px auto"></div></div>
    </div>`;

  let user, myProjects;
  try {
    [user, myProjects] = await Promise.all([
      api('GET', '/api/auth/me'),
      api('GET', '/api/auth/my-projects'),
    ]);
  } catch (e) {
    document.getElementById('profile-body').innerHTML =
      `<div class="empty-state"><div class="empty-icon material-symbols-outlined">warning</div><div class="empty-title">${e.message}</div></div>`;
    return;
  }

  const initials = user.username.slice(0, 2).toUpperCase();
  const roleColor = { Admin: 'rose', 'Project Manager': 'blue', 'Team Member': 'emerald' }[user.role] || 'blue';
  const joined = new Date(user.created_at).toLocaleDateString('en-US', { year:'numeric', month:'long', day:'numeric' });

  const projectCard = (p) => {
    const pct = p.task_total ? Math.round(p.task_done / p.task_total * 100) : 0;
    const statusColor = { 'In Progress':'blue','Completed':'green','Pending':'amber','Cancelled':'rose','Candidate':'violet' }[p.status] || 'blue';
    const rel = p.relation === 'manager'
      ? `<span class="badge badge-blue" style="font-size:10px">Manager</span>`
      : `<span class="badge badge-emerald" style="font-size:10px">Member</span>`;
    return `
      <div class="profile-proj-card" onclick="navigate('wbs',{WBS_PROJECT_ID:${p.project_id}})">
        <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:8px;margin-bottom:10px">
          <div style="font-weight:600;font-size:13px;color:var(--text-1);line-height:1.3">${p.name}</div>
          ${rel}
        </div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px">
          <span class="badge badge-${statusColor}" style="font-size:10px">${p.status}</span>
          ${p.end_date ? `<span style="font-size:11px;color:var(--text-3)"><span class="material-symbols-outlined" style="font-size:12px;vertical-align:middle">calendar_month</span> ${p.end_date}</span>` : ''}
        </div>
        <div style="font-size:11px;color:var(--text-3);margin-bottom:6px">Tasks: ${p.task_done}/${p.task_total} completed</div>
        <div style="background:var(--bg-raised);border-radius:4px;height:5px;overflow:hidden">
          <div style="height:100%;width:${pct}%;background:var(--blue-vivid);border-radius:4px;transition:width .3s"></div>
        </div>
      </div>`;
  };

  const allProjects = [...myProjects.managed, ...myProjects.member];

  document.getElementById('profile-body').innerHTML = `
    <div class="profile-layout">

      <!-- ── Left Column: Avatar + Bio ── -->
      <div class="profile-left">
        <div class="profile-avatar-card">
          <div class="profile-avatar-big">${initials}</div>
          <div class="profile-username">${user.username}</div>
          <div class="profile-fullname" id="pf-fullname-display">${user.full_name || '<span style="color:var(--text-3);font-style:italic">No full name set</span>'}</div>
          <span class="badge badge-${roleColor}" style="margin-top:6px;font-size:12px">${user.role}</span>
          <div style="margin-top:16px;font-size:12px;color:var(--text-3);display:flex;align-items:center;gap:4px">
            <span class="material-symbols-outlined" style="font-size:14px">calendar_today</span> Member since ${joined}
          </div>
          <div style="margin-top:8px;font-size:12px;color:var(--text-3);display:flex;align-items:center;gap:4px">
            <span class="material-symbols-outlined" style="font-size:14px">mail</span> ${user.email}
          </div>
          <div style="margin-top:8px;font-size:12px;color:${user.is_active ? 'var(--emerald)' : 'var(--rose)'};display:flex;align-items:center;gap:4px">
            <span class="material-symbols-outlined" style="font-size:14px">${user.is_active ? 'check_circle' : 'cancel'}</span>
            ${user.is_active ? 'Active account' : 'Inactive'}
          </div>
        </div>

        <!-- Stats Card -->
        <div class="profile-stats-card">
          <div class="profile-stat">
            <div class="profile-stat-val">${myProjects.stats.total_projects}</div>
            <div class="profile-stat-lbl">Projects</div>
          </div>
          <div class="profile-stat">
            <div class="profile-stat-val">${myProjects.stats.managing}</div>
            <div class="profile-stat-lbl">Managing</div>
          </div>
          <div class="profile-stat">
            <div class="profile-stat-val">${myProjects.stats.member_of}</div>
            <div class="profile-stat-lbl">Member of</div>
          </div>
        </div>
      </div>

      <!-- ── Right Column ── -->
      <div class="profile-right">

        <!-- Edit Profile Card -->
        <div class="card" style="margin-bottom:20px">
          <div class="card-header" style="display:flex;justify-content:space-between;align-items:center">
            <span style="font-weight:600;font-size:14px">Edit Profile</span>
            <button class="btn btn-ghost btn-sm" id="pf-edit-btn" onclick="toggleProfileEdit(true)">
              <span class="material-symbols-outlined" style="font-size:15px">edit</span> Edit
            </button>
          </div>
          <div id="pf-view-mode" style="padding:16px 0 4px">
            <div style="margin-bottom:14px">
              <div style="font-size:11px;color:var(--text-3);text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px">Full Name</div>
              <div style="font-size:14px" id="pf-view-fullname">${user.full_name || '—'}</div>
            </div>
            <div style="margin-bottom:14px">
              <div style="font-size:11px;color:var(--text-3);text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px">Email</div>
              <div style="font-size:14px" id="pf-view-email">${user.email}</div>
            </div>
            <div>
              <div style="font-size:11px;color:var(--text-3);text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px">Bio</div>
              <div style="font-size:14px;line-height:1.6;color:var(--text-2)" id="pf-view-bio">${user.bio || '<span style="color:var(--text-3);font-style:italic">No bio yet</span>'}</div>
            </div>
          </div>
          <div id="pf-edit-mode" style="display:none;padding:16px 0 4px">
            <div class="form-group">
              <label class="form-label">Full Name</label>
              <input class="form-input" id="pf-input-fullname" placeholder="Your full name" value="${user.full_name || ''}">
            </div>
            <div class="form-group">
              <label class="form-label">Email</label>
              <input class="form-input" id="pf-input-email" type="email" placeholder="your@email.com" value="${user.email}">
            </div>
            <div class="form-group">
              <label class="form-label">Bio</label>
              <textarea class="form-input" id="pf-input-bio" rows="4" placeholder="Tell us about yourself…" style="resize:vertical">${user.bio || ''}</textarea>
            </div>
            <div style="display:flex;gap:8px;margin-top:4px">
              <button class="btn btn-primary btn-sm" onclick="saveProfile()">Save Changes</button>
              <button class="btn btn-ghost btn-sm" onclick="toggleProfileEdit(false)">Cancel</button>
            </div>
          </div>
        </div>

        <!-- Change Password Card -->
        <div class="card" style="margin-bottom:20px">
          <div class="card-header" style="display:flex;justify-content:space-between;align-items:center">
            <span style="font-weight:600;font-size:14px">Change Password</span>
            <button class="btn btn-ghost btn-sm" onclick="togglePwdForm()">
              <span class="material-symbols-outlined" style="font-size:15px">lock</span> Change
            </button>
          </div>
          <div id="pf-pwd-form" style="display:none;padding:16px 0 4px">
            <div class="form-group">
              <label class="form-label">Current Password</label>
              <input class="form-input" id="pf-pwd-current" type="password" placeholder="Current password">
            </div>
            <div class="form-group">
              <label class="form-label">New Password</label>
              <input class="form-input" id="pf-pwd-new" type="password" placeholder="New password (min 6 chars)">
            </div>
            <div class="form-group">
              <label class="form-label">Confirm New Password</label>
              <input class="form-input" id="pf-pwd-confirm" type="password" placeholder="Confirm new password">
            </div>
            <div style="display:flex;gap:8px;margin-top:4px">
              <button class="btn btn-primary btn-sm" onclick="savePassword()">Update Password</button>
              <button class="btn btn-ghost btn-sm" onclick="togglePwdForm()">Cancel</button>
            </div>
          </div>
        </div>

        <!-- Enrolled Projects -->
        <div class="card">
          <div class="card-header" style="font-weight:600;font-size:14px">
            <span class="material-symbols-outlined" style="font-size:18px;vertical-align:middle;margin-right:6px">folder</span>
            Enrolled Projects
            <span class="badge badge-blue" style="margin-left:8px;font-size:11px">${allProjects.length}</span>
          </div>
          ${allProjects.length
            ? `<div class="profile-proj-grid">${allProjects.map(projectCard).join('')}</div>`
            : `<div class="empty-state" style="padding:30px 0">
                <div class="empty-icon material-symbols-outlined">folder_open</div>
                <div class="empty-title">No projects yet</div>
                <div class="empty-sub">You are not enrolled in any project</div>
               </div>`
          }
        </div>

      </div>
    </div>`;
}

function toggleProfileEdit(show) {
  document.getElementById('pf-view-mode').style.display = show ? 'none' : 'block';
  document.getElementById('pf-edit-mode').style.display = show ? 'block' : 'none';
  document.getElementById('pf-edit-btn').style.display  = show ? 'none' : '';
}

function togglePwdForm() {
  const f = document.getElementById('pf-pwd-form');
  f.style.display = f.style.display === 'none' ? 'block' : 'none';
  if (f.style.display === 'none') {
    ['pf-pwd-current','pf-pwd-new','pf-pwd-confirm'].forEach(id => { document.getElementById(id).value = ''; });
  }
}

async function saveProfile() {
  const full_name = document.getElementById('pf-input-fullname').value.trim();
  const email     = document.getElementById('pf-input-email').value.trim();
  const bio       = document.getElementById('pf-input-bio').value.trim();
  try {
    const updated = await api('PUT', '/api/auth/profile', { full_name, email, bio });
    // Refresh local display
    document.getElementById('pf-view-fullname').textContent = updated.full_name || '—';
    document.getElementById('pf-view-email').textContent    = updated.email;
    document.getElementById('pf-view-bio').innerHTML        = updated.bio || '<span style="color:var(--text-3);font-style:italic">No bio yet</span>';
    document.getElementById('pf-fullname-display').innerHTML = updated.full_name || '<span style="color:var(--text-3);font-style:italic">No full name set</span>';
    // Update cached user
    CURRENT_USER = { ...CURRENT_USER, full_name: updated.full_name, email: updated.email, bio: updated.bio };
    localStorage.setItem('cc_user', JSON.stringify(CURRENT_USER));
    toggleProfileEdit(false);
    toast('Profile updated', 'success');
  } catch(e) { toast(e.message, 'error'); }
}

// ══════════════════════════════════════════════
//  PROJECT INFO PAGE
// ══════════════════════════════════════════════
async function projectInfo() {
  const mc = document.getElementById('main-content');

  if (!PROJECT_INFO_ID) {
    mc.innerHTML = `<div class="page-content"><div class="empty-state" style="margin-top:60px">
      <div class="empty-icon material-symbols-outlined">info</div>
      <div class="empty-title">No project selected</div>
      <div class="empty-sub">Go to Projects and click a project name</div>
    </div></div>`;
    return;
  }

  mc.innerHTML = `<div class="page-content"><div style="display:flex;align-items:center;justify-content:center;height:200px"><div class="spinner"></div></div></div>`;

  try {
    const [proj, members, tasks, evm, scoring, metrics, comments] = await Promise.all([
      api('GET', `/api/projects/${PROJECT_INFO_ID}`),
      api('GET', `/api/projects/${PROJECT_INFO_ID}/members`).catch(() => []),
      api('GET', `/api/projects/${PROJECT_INFO_ID}/tasks`).catch(() => []),
      api('GET', `/api/projects/${PROJECT_INFO_ID}/evm`).catch(() => null),
      api('GET', `/api/projects/${PROJECT_INFO_ID}/scoring`).catch(() => null),
      api('GET', `/api/projects/${PROJECT_INFO_ID}/metrics`).catch(() => null),
      api('GET', `/api/projects/${PROJECT_INFO_ID}/comments`).catch(() => []),
    ]);

    const canEdit = ['Admin','Project Manager'].includes(CURRENT_USER?.role);
    const canDel  = CURRENT_USER?.role === 'Admin' ||
                    (CURRENT_USER?.role === 'Project Manager' && proj.manager_id === CURRENT_USER?.user_id);

    // ── Derived stats ──
    const taskDone    = tasks.filter(t => t.status === 'Completed').length;
    const taskPct     = tasks.length ? Math.round(taskDone / tasks.length * 100) : 0;
    const daysLeft    = proj.end_date ? Math.ceil((new Date(proj.end_date) - new Date()) / 86400000) : null;
    const daysColor   = daysLeft == null ? 'var(--text-3)' : daysLeft < 0 ? 'var(--rose)' : daysLeft < 30 ? 'var(--amber)' : 'var(--emerald)';
    const memberInitials = (name) => name?.slice(0,2).toUpperCase() || '?';
    const roleColors  = { Admin:'rose', 'Project Manager':'blue', 'Team Member':'emerald' };

    // ── Status timeline ──
    const statusOrder = ['Pending','Candidate','In Progress','Completed','Cancelled'];
    const statusIdx   = statusOrder.indexOf(proj.status);

    mc.innerHTML = `
    <div class="page-content">

      <!-- ── Header ── -->
      <div class="page-header" style="align-items:flex-start;flex-wrap:wrap;gap:12px">
        <div style="display:flex;align-items:center;gap:12px">
          <button class="btn btn-ghost btn-sm" onclick="navigate('projects')" style="gap:4px">
            <span class="material-symbols-outlined" style="font-size:16px">arrow_back</span> Projects
          </button>
          <div>
            <div class="page-title" style="margin-bottom:4px">${proj.name}</div>
            <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
              ${statusBadge(proj.status)}
              ${proj.is_selected ? '<span class="badge badge-violet">★ Selected</span>' : ''}
            </div>
          </div>
        </div>
        <div class="page-actions">
          ${canEdit ? `<button class="btn btn-ghost btn-sm" onclick="openProjectModal(${proj.project_id})"><span class="material-symbols-outlined" style="font-size:15px">edit</span> Edit</button>` : ''}
          <button class="btn btn-ghost btn-sm" onclick="navigate('wbs',{WBS_PROJECT_ID:${proj.project_id}})"><span class="material-symbols-outlined" style="font-size:15px">assignment</span> WBS Tasks</button>
          <button class="btn btn-ghost btn-sm" onclick="navigate('evm',{EVM_PROJECT_ID:${proj.project_id}})"><span class="material-symbols-outlined" style="font-size:15px">show_chart</span> EVM</button>
          <button class="btn btn-ghost btn-sm" onclick="downloadFile('/api/pdf/project/${proj.project_id}','project_${proj.project_id}_report.pdf')"><span class="material-symbols-outlined" style="font-size:15px">picture_as_pdf</span> PDF</button>
          ${canDel ? `<button class="btn btn-ghost btn-sm" style="color:var(--rose)" onclick="deleteProject(${proj.project_id},'${proj.name.replace(/'/g,"\\'")}')"><span class="material-symbols-outlined" style="font-size:15px">delete</span> Delete</button>` : ''}
        </div>
      </div>

      <div class="pi-layout">

        <!-- ══ LEFT COLUMN ══ -->
        <div class="pi-left">

          <!-- Description -->
          ${proj.description ? `
          <div class="card pi-card" style="margin-bottom:16px">
            <div class="pi-section-title"><span class="material-symbols-outlined">description</span> Description</div>
            <p style="font-size:13px;line-height:1.7;color:var(--text-2);margin:0">${proj.description}</p>
          </div>` : ''}

          <!-- Key Details -->
          <div class="card pi-card" style="margin-bottom:16px">
            <div class="pi-section-title"><span class="material-symbols-outlined">info</span> Project Details</div>
            <div class="pi-detail-grid">
              <div class="pi-detail-item">
                <div class="pi-detail-label">Manager</div>
                <div class="pi-detail-val">
                  ${proj.manager_name
                    ? `<div style="display:flex;align-items:center;gap:8px">
                         <div class="pi-avatar" style="background:var(--blue-vivid)">${memberInitials(proj.manager_name)}</div>
                         <span>${proj.manager_name}</span>
                       </div>`
                    : '<span style="color:var(--text-3)">Unassigned</span>'}
                </div>
              </div>
              <div class="pi-detail-item">
                <div class="pi-detail-label">Budget</div>
                <div class="pi-detail-val" style="font-family:var(--font-mono);color:var(--emerald);font-weight:600">${fmtK(proj.budget)} SAR</div>
              </div>
              <div class="pi-detail-item">
                <div class="pi-detail-label">Start Date</div>
                <div class="pi-detail-val">${proj.start_date || '—'}</div>
              </div>
              <div class="pi-detail-item">
                <div class="pi-detail-label">End Date</div>
                <div class="pi-detail-val">${proj.end_date || '—'}</div>
              </div>
              <div class="pi-detail-item">
                <div class="pi-detail-label">Days Remaining</div>
                <div class="pi-detail-val" style="color:${daysColor};font-weight:600">
                  ${daysLeft == null ? '—' : daysLeft < 0 ? `${Math.abs(daysLeft)}d overdue` : `${daysLeft}d`}
                </div>
              </div>
              <div class="pi-detail-item">
                <div class="pi-detail-label">Project ID</div>
                <div class="pi-detail-val" style="font-family:var(--font-mono);color:var(--text-3)">#${proj.project_id}</div>
              </div>
            </div>
          </div>

          <!-- Status Timeline -->
          <div class="card pi-card" style="margin-bottom:16px">
            <div class="pi-section-title"><span class="material-symbols-outlined">timeline</span> Status</div>
            <div class="pi-timeline">
              ${statusOrder.map((s, i) => `
                <div class="pi-timeline-step ${i <= statusIdx ? 'done' : ''} ${s === proj.status ? 'current' : ''}">
                  <div class="pi-timeline-dot"></div>
                  <div class="pi-timeline-label">${s}</div>
                </div>`).join('')}
            </div>
          </div>

          <!-- Task Progress -->
          <div class="card pi-card" style="margin-bottom:16px">
            <div class="pi-section-title"><span class="material-symbols-outlined">task_alt</span> Task Progress</div>
            <div style="display:flex;align-items:center;gap:12px;margin-bottom:10px">
              <div style="flex:1">
                <div style="background:var(--bg-raised);border-radius:6px;height:10px;overflow:hidden">
                  <div style="height:100%;width:${taskPct}%;background:linear-gradient(90deg,var(--blue-vivid),var(--violet));border-radius:6px;transition:width .4s"></div>
                </div>
              </div>
              <div style="font-size:20px;font-weight:700;color:var(--blue-vivid);min-width:46px;text-align:right">${taskPct}%</div>
            </div>
            <div style="display:flex;gap:16px;flex-wrap:wrap">
              <span style="font-size:12px;color:var(--text-3)"><b style="color:var(--text-1)">${tasks.length}</b> total</span>
              <span style="font-size:12px;color:var(--text-3)"><b style="color:var(--emerald)">${taskDone}</b> completed</span>
              <span style="font-size:12px;color:var(--text-3)"><b style="color:var(--amber)">${tasks.filter(t=>t.status==='In Progress').length}</b> in progress</span>
              <span style="font-size:12px;color:var(--text-3)"><b style="color:var(--text-2)">${tasks.filter(t=>t.status==='Not Started').length}</b> not started</span>
            </div>
          </div>

          <!-- EVM Summary -->
          ${evm ? `
          <div class="card pi-card" style="margin-bottom:16px">
            <div class="pi-section-title"><span class="material-symbols-outlined">show_chart</span> EVM Summary</div>
            <div class="pi-evm-grid">
              ${[
                ['CPI', fmt(evm.cpi), Number(evm.cpi) >= 1 ? 'var(--emerald)' : Number(evm.cpi) >= 0.9 ? 'var(--amber)' : 'var(--rose)', 'Cost Performance'],
                ['SPI', fmt(evm.spi), Number(evm.spi) >= 1 ? 'var(--emerald)' : Number(evm.spi) >= 0.9 ? 'var(--amber)' : 'var(--rose)', 'Schedule Performance'],
                ['EV',  fmtK(evm.ev),  'var(--blue-vivid)', 'Earned Value'],
                ['AC',  fmtK(evm.ac),  'var(--text-1)',      'Actual Cost'],
                ['PV',  fmtK(evm.pv),  'var(--text-1)',      'Planned Value'],
                ['EAC', fmtK(evm.eac), 'var(--amber)',       'Est. At Completion'],
              ].map(([k,v,c,lbl]) => `
                <div class="pi-evm-item">
                  <div style="font-size:11px;color:var(--text-3);margin-bottom:3px">${lbl}</div>
                  <div style="font-size:18px;font-weight:700;color:${c}">${v}</div>
                  <div style="font-size:10px;color:var(--text-3)">${k}</div>
                </div>`).join('')}
            </div>
          </div>` : ''}

          <!-- Financial Metrics -->
          ${metrics ? `
          <div class="card pi-card" style="margin-bottom:16px">
            <div class="pi-section-title"><span class="material-symbols-outlined">payments</span> Financial Metrics</div>
            <div class="pi-detail-grid">
              ${[
                ['ROI',          `${fmt(metrics.roi, 1)}%`,  'var(--emerald)'],
                ['BCR',          fmt(metrics.bcr),            Number(metrics.bcr)>=1?'var(--emerald)':'var(--rose)'],
                ['NPV',          fmtK(metrics.npv)+' SAR',   Number(metrics.npv)>=0?'var(--emerald)':'var(--rose)'],
                ['Payback Period',`${fmt(metrics.payback_period,1)} yrs`, 'var(--blue-vivid)'],
              ].map(([lbl,val,color]) => `
                <div class="pi-detail-item">
                  <div class="pi-detail-label">${lbl}</div>
                  <div class="pi-detail-val" style="font-weight:600;color:${color}">${val}</div>
                </div>`).join('')}
            </div>
            ${scoring ? `<div style="margin-top:14px;padding-top:14px;border-top:1px solid var(--border);display:flex;align-items:center;gap:12px">
              <div>
                <div style="font-size:11px;color:var(--text-3);margin-bottom:3px">Composite Score</div>
                <div style="font-size:28px;font-weight:800;color:var(--blue-vivid)">${fmt(scoring.total_score,1)}</div>
              </div>
              <div style="flex:1">
                <div style="background:var(--bg-raised);border-radius:4px;height:8px;overflow:hidden">
                  <div style="height:100%;width:${scoring.total_score}%;background:linear-gradient(90deg,var(--blue-vivid),var(--violet));border-radius:4px"></div>
                </div>
                ${scoring.priority_rank ? `<div style="font-size:11px;color:var(--text-3);margin-top:4px">Rank #${scoring.priority_rank}</div>` : ''}
              </div>
            </div>` : ''}
          </div>` : ''}

        </div>

        <!-- ══ RIGHT COLUMN ══ -->
        <div class="pi-right">

          <!-- Team Members -->
          <div class="card pi-card" style="margin-bottom:16px">
            <div class="pi-section-title" style="display:flex;justify-content:space-between;align-items:center">
              <span><span class="material-symbols-outlined">group</span> Team
                <span class="badge badge-blue" style="margin-left:6px;font-size:10px">${members.length}</span>
              </span>
              ${canEdit ? `<button class="btn btn-ghost btn-sm" onclick="navigate('members',{MEMBER_PROJECT_ID:${proj.project_id}})"><span class="material-symbols-outlined" style="font-size:14px">manage_accounts</span> Manage</button>` : ''}
            </div>

            ${proj.manager_name ? `
            <div style="margin-bottom:10px">
              <div style="font-size:10px;color:var(--text-3);text-transform:uppercase;letter-spacing:.06em;margin-bottom:8px">Project Manager</div>
              <div class="pi-member-row">
                <div class="pi-avatar" style="background:linear-gradient(135deg,var(--blue-vivid),var(--violet))">${memberInitials(proj.manager_name)}</div>
                <div>
                  <div style="font-weight:600;font-size:13px">${proj.manager_name}</div>
                  <div style="font-size:11px;color:var(--blue-vivid)">Project Manager</div>
                </div>
                <span class="badge badge-blue" style="margin-left:auto;font-size:10px">Manager</span>
              </div>
            </div>
            <div style="height:1px;background:var(--border);margin-bottom:10px"></div>` : ''}

            ${members.length ? `
            <div>
              <div style="font-size:10px;color:var(--text-3);text-transform:uppercase;letter-spacing:.06em;margin-bottom:8px">Team Members</div>
              <div style="display:flex;flex-direction:column;gap:8px">
                ${members.map(m => `
                  <div class="pi-member-row">
                    <div class="pi-avatar" style="background:var(--bg-raised);color:var(--text-1);border:1px solid var(--border)">${memberInitials(m.username)}</div>
                    <div>
                      <div style="font-weight:600;font-size:13px">${m.username}</div>
                      ${m.role_in_project ? `<div style="font-size:11px;color:var(--text-3)">${m.role_in_project}</div>` : ''}
                    </div>
                    <span class="badge badge-${roleColors[m.role]||'emerald'}" style="margin-left:auto;font-size:10px">${m.role || 'Team Member'}</span>
                  </div>`).join('')}
              </div>
            </div>` : `
            <div style="text-align:center;padding:20px 0;color:var(--text-3);font-size:13px">
              <span class="material-symbols-outlined" style="font-size:32px;opacity:.3;display:block;margin-bottom:8px">group_off</span>
              No team members assigned
            </div>`}
          </div>

          <!-- WBS Tasks List -->
          <div class="card pi-card" style="margin-bottom:16px">
            <div class="pi-section-title" style="display:flex;justify-content:space-between;align-items:center">
              <span><span class="material-symbols-outlined">assignment</span> WBS Tasks
                <span class="badge badge-blue" style="margin-left:6px;font-size:10px">${tasks.length}</span>
              </span>
              <button class="btn btn-ghost btn-sm" onclick="navigate('wbs',{WBS_PROJECT_ID:${proj.project_id}})">
                <span class="material-symbols-outlined" style="font-size:14px">open_in_new</span> View All
              </button>
            </div>
            ${tasks.length ? `
            <div style="display:flex;flex-direction:column;gap:6px;max-height:320px;overflow-y:auto">
              ${tasks.map(t => {
                const pct = t.percent_complete || 0;
                const tColor = t.status === 'Completed' ? 'var(--emerald)' : t.status === 'In Progress' ? 'var(--blue-vivid)' : 'var(--text-3)';
                const tIcon  = t.status === 'Completed' ? 'task_alt' : t.status === 'In Progress' ? 'pending' : 'radio_button_unchecked';
                return `<div style="display:flex;gap:10px;align-items:flex-start;padding:8px;background:var(--bg-raised);border-radius:6px">
                  <span class="material-symbols-outlined" style="font-size:16px;color:${tColor};flex-shrink:0;margin-top:1px">${tIcon}</span>
                  <div style="flex:1;min-width:0">
                    <div style="font-size:13px;font-weight:500;color:var(--text-1);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${t.task_name}</div>
                    <div style="display:flex;align-items:center;gap:6px;margin-top:4px">
                      <div style="flex:1;background:var(--border);border-radius:3px;height:4px;overflow:hidden">
                        <div style="height:100%;width:${pct}%;background:${tColor};border-radius:3px"></div>
                      </div>
                      <span style="font-size:10px;color:var(--text-3);min-width:28px;text-align:right">${pct}%</span>
                    </div>
                  </div>
                </div>`;
              }).join('')}
            </div>` : `<div style="text-align:center;padding:20px 0;color:var(--text-3);font-size:13px">No tasks yet</div>`}
          </div>

          <!-- Comments -->
          <div class="card pi-card">
            <div class="pi-section-title" style="display:flex;justify-content:space-between;align-items:center">
              <span><span class="material-symbols-outlined">chat</span> Discussion
                <span class="badge badge-blue" style="margin-left:6px;font-size:10px">${comments.length}</span>
              </span>
              <button class="btn btn-ghost btn-sm" onclick="navigate('wbs',{WBS_PROJECT_ID:${proj.project_id}})">
                <span class="material-symbols-outlined" style="font-size:14px">open_in_new</span> View
              </button>
            </div>
            ${comments.length ? `
            <div style="display:flex;flex-direction:column;gap:10px;max-height:280px;overflow-y:auto">
              ${comments.slice(-5).reverse().map(c => `
                <div style="display:flex;gap:10px;align-items:flex-start">
                  <div class="pi-avatar" style="background:var(--bg-raised);border:1px solid var(--border);font-size:12px;flex-shrink:0">${memberInitials(c.author_username)}</div>
                  <div style="flex:1;background:var(--bg-raised);border-radius:8px;padding:10px">
                    <div style="display:flex;justify-content:space-between;margin-bottom:4px">
                      <span style="font-size:12px;font-weight:600">${c.author_username}</span>
                      <span style="font-size:10px;color:var(--text-3)">${new Date(c.created_at).toLocaleDateString()}</span>
                    </div>
                    <div style="font-size:13px;color:var(--text-2);line-height:1.5">${c.content}</div>
                  </div>
                </div>`).join('')}
            </div>` : `<div style="text-align:center;padding:20px 0;color:var(--text-3);font-size:13px">No comments yet</div>`}
          </div>

        </div>
      </div>
    </div>`;

  } catch(e) {
    mc.innerHTML = `<div class="page-content"><div class="empty-state" style="margin-top:60px">
      <div class="empty-icon material-symbols-outlined">warning</div>
      <div class="empty-title">Failed to load project</div>
      <div class="empty-sub">${e.message}</div>
    </div></div>`;
  }
}

async function savePassword() {
  const current_password = document.getElementById('pf-pwd-current').value;
  const new_password     = document.getElementById('pf-pwd-new').value;
  const confirm          = document.getElementById('pf-pwd-confirm').value;
  if (new_password !== confirm) { toast('Passwords do not match', 'error'); return; }
  if (new_password.length < 6)  { toast('Password must be at least 6 characters', 'error'); return; }
  try {
    await api('PUT', '/api/auth/reset-password', { current_password, new_password });
    togglePwdForm();
    toast('Password updated', 'success');
  } catch(e) { toast(e.message, 'error'); }
}

// ─── CHATBOT — ARIA ─────────────────────────────────────────────────────────

// ARIA avatar — robot face on brand gradient background
const ARIA_SVG = `<svg viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg" width="22" height="22">
  <!-- Antenna stem -->
  <rect x="15" y="0" width="2" height="4" rx="1" fill="white" opacity="0.9"/>
  <!-- Antenna ball -->
  <circle cx="16" cy="0.5" r="2" fill="white"/>
  <!-- Head body — transparent so container gradient shows through -->
  <rect x="2" y="4" width="28" height="24" rx="6" fill="white" opacity="0.15"/>
  <!-- Left eye -->
  <rect x="6" y="10" width="8" height="7" rx="2.5" fill="white" opacity="0.25"/>
  <rect x="7.5" y="11.5" width="5" height="4" rx="1.5" fill="white"/>
  <!-- Right eye -->
  <rect x="18" y="10" width="8" height="7" rx="2.5" fill="white" opacity="0.25"/>
  <rect x="19.5" y="11.5" width="5" height="4" rx="1.5" fill="white"/>
  <!-- Mouth bar -->
  <rect x="7" y="21" width="18" height="4" rx="2" fill="white" opacity="0.25"/>
  <!-- Mouth segments -->
  <rect x="8"  y="22" width="3" height="2" rx="0.8" fill="white"/>
  <rect x="12" y="22" width="3" height="2" rx="0.8" fill="white" opacity="0.5"/>
  <rect x="16" y="22" width="3" height="2" rx="0.8" fill="white"/>
  <rect x="20" y="22" width="3" height="2" rx="0.8" fill="white" opacity="0.5"/>
  <!-- Side ear bolts -->
  <circle cx="2"  cy="16" r="2" fill="white" opacity="0.4"/>
  <circle cx="30" cy="16" r="2" fill="white" opacity="0.4"/>
</svg>`;

function chatbot() {
  const mc = document.getElementById('main-content');
  mc.innerHTML = `
  <div class="page-content chatbot-page">
    <div class="page-header">
      <div>
        <div class="page-title">ARIA</div>
        <div class="page-sub">AI Resource &amp; Intelligence Assistant — asks about your live projects, EVM, and risks</div>
      </div>
      <div class="page-actions">
        <button class="btn btn-ghost btn-sm" onclick="chatbotClear()">
          <span class="material-symbols-outlined" style="font-size:15px">delete_sweep</span> Clear chat
        </button>
      </div>
    </div>

    <div class="chatbot-wrap">
      <div class="chatbot-messages" id="chatbot-messages">
        <div class="chatbot-msg-bot">
          <div class="chatbot-bot-avatar">${ARIA_SVG}</div>
          <div class="chatbot-bubble chatbot-bubble-bot">
            <p>Hi <strong>${escHtml(CURRENT_USER?.username || 'there')}</strong>! I'm <strong>ARIA</strong> — your AI Resource &amp; Intelligence Assistant.</p>
            <p style="margin-top:6px">I have access to your live project data and can answer questions about budgets, risks, EVM metrics, or any project management concept. Try a quick question below!</p>
          </div>
        </div>
      </div>

      <div class="chatbot-chips">
        <button class="chatbot-chip" onclick="chatbotSendChip('Show my projects')">My projects</button>
        <button class="chatbot-chip" onclick="chatbotSendChip('In progress projects')">In progress</button>
        <button class="chatbot-chip" onclick="chatbotSendChip('High risk projects')">High risk</button>
        <button class="chatbot-chip" onclick="chatbotSendChip('Over budget projects')">Over budget</button>
        <button class="chatbot-chip" onclick="chatbotSendChip('Portfolio summary')">Portfolio summary</button>
        <button class="chatbot-chip" onclick="chatbotSendChip('What is EVM?')">What is EVM?</button>
        <button class="chatbot-chip" onclick="chatbotSendChip('What is CPI?')">What is CPI?</button>
        <button class="chatbot-chip" onclick="chatbotSendChip('What is WBS?')">What is WBS?</button>
      </div>

      <div class="chatbot-input-row">
        <input class="chatbot-input" id="chatbot-input" type="text"
               placeholder="Ask about your projects..."
               onkeydown="if(event.key==='Enter')chatbotSend()" />
        <button class="chatbot-send-btn" onclick="chatbotSend()">
          <span class="material-symbols-outlined">send</span>
        </button>
      </div>
    </div>
  </div>`;
}

function chatbotSendChip(text) {
  const input = document.getElementById('chatbot-input');
  if (input) { input.value = text; chatbotSend(); }
}

function chatbotClear() {
  CHATBOT_HISTORY = [];
  chatbot();
}

async function chatbotSend() {
  const input = document.getElementById('chatbot-input');
  const msg = input?.value.trim();
  if (!msg) return;
  input.value = '';

  const msgsEl = document.getElementById('chatbot-messages');

  msgsEl.insertAdjacentHTML('beforeend', `
    <div class="chatbot-msg-user">
      <div class="chatbot-bubble chatbot-bubble-user">${escHtml(msg)}</div>
      <div class="chatbot-user-avatar">${(CURRENT_USER?.username || 'U').slice(0, 2).toUpperCase()}</div>
    </div>`);

  const loadId = 'cb-load-' + Date.now();
  msgsEl.insertAdjacentHTML('beforeend', `
    <div class="chatbot-msg-bot" id="${loadId}">
      <div class="chatbot-bot-avatar">${ARIA_SVG}</div>
      <div class="chatbot-bubble chatbot-bubble-bot chatbot-typing"><span></span><span></span><span></span></div>
    </div>`);
  msgsEl.scrollTop = msgsEl.scrollHeight;

  const html = await chatbotProcess(msg);

  const loadEl = document.getElementById(loadId);
  if (loadEl) {
    loadEl.innerHTML = `
      <div class="chatbot-bot-avatar">${ARIA_SVG}</div>
      <div class="chatbot-bubble chatbot-bubble-bot">${html}</div>`;
  }
  msgsEl.scrollTop = msgsEl.scrollHeight;

  CHATBOT_HISTORY.push({ role: 'user', content: msg });
  const tmp = document.createElement('div');
  tmp.innerHTML = html;
  CHATBOT_HISTORY.push({ role: 'assistant', content: tmp.textContent || '' });
}

function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function mdToHtml(md) {
  const lines = md.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>').split('\n');
  const out = [];
  let inList = false;
  for (const line of lines) {
    if (line.startsWith('- ') || line.startsWith('* ')) {
      if (!inList) { out.push('<ul style="margin:8px 0 0 16px;line-height:1.9">'); inList = true; }
      out.push(`<li>${line.slice(2)}</li>`);
    } else {
      if (inList) { out.push('</ul>'); inList = false; }
      if (line.trim()) out.push(`<p>${line}</p>`);
    }
  }
  if (inList) out.push('</ul>');
  return out.join('');
}

async function chatbotProcess(msg) {
  const q = msg.toLowerCase();

  if (/^help$|what can you|capabilities/.test(q)) {
    return `<p>Here's what you can ask me:</p>
    <ul style="margin:8px 0 0 16px;line-height:2">
      <li><strong>Projects:</strong> "show my projects", "in progress", "completed", "pending"</li>
      <li><strong>Risk &amp; budget:</strong> "high risk projects", "over budget"</li>
      <li><strong>Analytics:</strong> "portfolio summary"</li>
      <li><strong>EVM:</strong> "what is EVM?", "what is CPI?", "what is SPI?", "what is WBS?"</li>
      <li><strong>Finance:</strong> "what is ROI?", "what is NPV?", "what is BCR?"</li>
    </ul>`;
  }

  if (/^(hi|hello|hey|good morning|good afternoon)/.test(q)) {
    return `<p>Hello <strong>${escHtml(CURRENT_USER?.username || 'there')}</strong>! Ask me about your projects or type "help" to see what I can do.</p>`;
  }

  // ── PM / EVM concepts ──
  if (/what is evm|earned value management/.test(q)) {
    return `<p><strong>Earned Value Management (EVM)</strong> integrates scope, schedule, and cost to measure project performance.</p>
    <ul style="margin:8px 0 0 16px;line-height:1.9">
      <li><strong>PV</strong> — Planned Value (budgeted work scheduled)</li>
      <li><strong>EV</strong> — Earned Value (budgeted cost of completed work)</li>
      <li><strong>AC</strong> — Actual Cost (real spend so far)</li>
      <li><strong>CPI</strong> = EV ÷ AC &nbsp;(cost efficiency)</li>
      <li><strong>SPI</strong> = EV ÷ PV &nbsp;(schedule efficiency)</li>
    </ul>`;
  }
  if (/what is cpi|cost performance index/.test(q)) {
    return `<p><strong>Cost Performance Index (CPI)</strong> = EV ÷ AC</p>
    <ul style="margin:8px 0 0 16px;line-height:1.9">
      <li><strong>CPI &gt; 1.0</strong> — Under budget</li>
      <li><strong>CPI = 1.0</strong> — Exactly on budget</li>
      <li><strong>CPI &lt; 1.0</strong> — Over budget (needs attention)</li>
    </ul>`;
  }
  if (/what is spi|schedule performance index/.test(q)) {
    return `<p><strong>Schedule Performance Index (SPI)</strong> = EV ÷ PV</p>
    <ul style="margin:8px 0 0 16px;line-height:1.9">
      <li><strong>SPI &gt; 1.0</strong> — Ahead of schedule</li>
      <li><strong>SPI = 1.0</strong> — On schedule</li>
      <li><strong>SPI &lt; 1.0</strong> — Behind schedule</li>
    </ul>`;
  }
  if (/what is eac|estimate at completion/.test(q)) {
    return `<p><strong>Estimate at Completion (EAC)</strong> = BAC ÷ CPI</p>
    <p style="margin-top:6px">EAC is the forecast total cost based on current spending efficiency. If CPI &lt; 1.0, EAC will exceed the original Budget at Completion (BAC).</p>`;
  }
  if (/what is vac|variance at completion/.test(q)) {
    return `<p><strong>Variance at Completion (VAC)</strong> = BAC − EAC</p>
    <ul style="margin:8px 0 0 16px;line-height:1.9">
      <li><strong>VAC &gt; 0</strong> — Expected to finish under budget</li>
      <li><strong>VAC &lt; 0</strong> — Expected to finish over budget</li>
    </ul>`;
  }
  if (/what is wbs|work breakdown/.test(q)) {
    return `<p><strong>Work Breakdown Structure (WBS)</strong> decomposes a project into manageable tasks.</p>
    <ul style="margin:8px 0 0 16px;line-height:1.9">
      <li>Each task tracks PV, AC, and % complete</li>
      <li>EV is auto-calculated: PV × (% complete ÷ 100)</li>
      <li>All tasks feed into the project's EVM metrics</li>
    </ul>`;
  }
  if (/what is roi|return on investment/.test(q)) {
    return `<p><strong>ROI</strong> = (Net Benefit ÷ Investment) × 100%. Auto-calculated in <strong>Selection &amp; Ranking</strong> when you enter financial metrics.</p>`;
  }
  if (/what is npv|net present value/.test(q)) {
    return `<p><strong>NPV &gt; 0</strong> → project adds value (accept). <strong>NPV &lt; 0</strong> → costs exceed discounted benefits (reject).</p>`;
  }
  if (/what is bcr|benefit.cost ratio/.test(q)) {
    return `<p><strong>BCR</strong> = Total Benefits ÷ Total Costs &nbsp;|&nbsp; &gt;1 feasible · =1 break-even · &lt;1 not feasible.</p>`;
  }

  // ── Live data ──
  if (/portfolio|summary|overview/.test(q) && !/project/.test(q)) {
    try {
      const s = await api('GET', '/api/analytics/portfolio/summary');
      return `<p><strong>Portfolio Summary</strong></p>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:10px">
        <div class="cb-stat"><div class="cb-stat-label">Total Projects</div><div class="cb-stat-val" style="color:var(--blue-vivid)">${s.total_projects}</div></div>
        <div class="cb-stat"><div class="cb-stat-label">Portfolio Budget</div><div class="cb-stat-val" style="color:var(--emerald)">${fmtK(s.total_budget)} SAR</div></div>
        <div class="cb-stat"><div class="cb-stat-label">At-Risk</div><div class="cb-stat-val" style="color:var(--rose)">${s.evm?.at_risk_projects ?? '—'}</div></div>
        <div class="cb-stat"><div class="cb-stat-label">Task Completion</div><div class="cb-stat-val" style="color:var(--amber)">${s.tasks?.completion_rate_pct ?? '—'}%</div></div>
      </div>`;
    } catch(e) { return `<p style="color:var(--rose)">Could not load data: ${escHtml(e.message)}</p>`; }
  }

  if (/show.*(my )?projects|list.*projects|(my )?projects|how many projects/.test(q)) {
    try {
      const projs = await api('GET', '/api/projects');
      if (!projs.length) return `<p>No projects found. Go to <strong>All Projects</strong> to create one.</p>`;
      const rows = projs.map(p => `
        <div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid var(--border)">
          <span style="font-weight:500;font-size:13px">${escHtml(p.name)}</span>${statusBadge(p.status)}
        </div>`).join('');
      return `<p>You have <strong>${projs.length}</strong> project(s):</p><div style="margin-top:8px">${rows}</div>`;
    } catch(e) { return `<p style="color:var(--rose)">Could not load projects: ${escHtml(e.message)}</p>`; }
  }

  const statusMap = { 'in progress':'In Progress','completed':'Completed','pending':'Pending',
    'cancelled':'Cancelled','candidate':'Candidate','draft':'Draft','selected':'Selected' };
  for (const [key, label] of Object.entries(statusMap)) {
    if (q.includes(key)) {
      try {
        const projs = await api('GET', '/api/projects');
        const f = projs.filter(p => p.status === label);
        if (!f.length) return `<p>No <strong>${label}</strong> projects found.</p>`;
        const rows = f.map(p => `
          <div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--border)">
            <span style="font-weight:500;font-size:13px">${escHtml(p.name)}</span>
            <span style="font-size:11px;color:var(--text-2)">${fmtK(p.budget)} SAR</span>
          </div>`).join('');
        return `<p><strong>${f.length}</strong> ${label} project(s):</p><div style="margin-top:8px">${rows}</div>`;
      } catch(e) { return `<p style="color:var(--rose)">${escHtml(e.message)}</p>`; }
    }
  }

  if (/high risk|risk assessment|at risk/.test(q) && !/what is/.test(q)) {
    try {
      const risk = await api('GET', '/api/analytics/portfolio/risk');
      const hi = risk.filter(r => r.risk_level === 'High' || r.risk_level === 'Critical');
      if (!hi.length) return `<p>No high-risk or critical projects found. Your portfolio looks healthy!</p>`;
      const rows = hi.map(r => `
        <div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--border)">
          <span style="font-weight:500;font-size:13px">${escHtml(r.project_name)}</span>${riskBadge(r.risk_level)}
        </div>`).join('');
      return `<p><strong>${hi.length}</strong> high-risk project(s):</p><div style="margin-top:8px">${rows}</div>
      <p style="margin-top:10px;font-size:12px;color:var(--text-2)">See full details in <strong>Analytics</strong>.</p>`;
    } catch(e) { return `<p style="color:var(--rose)">${escHtml(e.message)}</p>`; }
  }

  if (/over budget|budget overrun/.test(q)) {
    try {
      const budget = await api('GET', '/api/analytics/portfolio/budget');
      const over = budget.filter(b => b.is_over_budget);
      if (!over.length) return `<p>No projects are currently over budget. Keep it up!</p>`;
      const rows = over.map(b => `
        <div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--border)">
          <span style="font-weight:500;font-size:13px">${escHtml(b.project_name)}</span>
          <span style="color:var(--rose);font-size:11px;font-weight:600">Over Budget</span>
        </div>`).join('');
      return `<p><strong>${over.length}</strong> over-budget project(s):</p><div style="margin-top:8px">${rows}</div>`;
    } catch(e) { return `<p style="color:var(--rose)">${escHtml(e.message)}</p>`; }
  }

  if (/budget/.test(q)) {
    try {
      const s = await api('GET', '/api/analytics/portfolio/summary');
      return `<p>Total portfolio budget: <strong style="color:var(--emerald)">${fmtK(s.total_budget)} SAR</strong> across <strong>${s.total_projects}</strong> projects.</p>
      <p style="margin-top:8px;font-size:12px;color:var(--text-2)">Go to <strong>Analytics</strong> for a full breakdown per project.</p>`;
    } catch(e) { return `<p style="color:var(--rose)">${escHtml(e.message)}</p>`; }
  }

  try {
    const res = await api('POST', '/api/chatbot/ask', {
      message: msg,
      history: CHATBOT_HISTORY.slice(-8)
    });
    return mdToHtml(res.reply);
  } catch(e) {
    if (e.message && e.message.includes('GROQ_API_KEY')) {
      return `<p>The AI backend is not configured yet. Ask your admin to add a <strong>GROQ_API_KEY</strong> to the server's .env file.</p>`;
    }
    return `<p style="color:var(--rose)">Could not reach AI: ${escHtml(e.message)}</p>`;
  }
}
