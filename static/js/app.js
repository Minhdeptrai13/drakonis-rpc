
const KNOWN_ASSET_ICONS = {
  vscode:   {url:'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/vscode/vscode-original.svg', name:'VSCode'},
  python:   {url:'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/python/python-original.svg', name:'Python'},
  git:      {url:'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/git/git-original.svg', name:'Git'},
  docker:   {url:'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/docker/docker-original.svg', name:'Docker'},
  js:       {url:'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/javascript/javascript-original.svg', name:'JavaScript'},
  ts:       {url:'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/typescript/typescript-original.svg', name:'TypeScript'},
  jsx:      {url:'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/react/react-original.svg', name:'React JSX'},
  tsx:      {url:'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/react/react-original.svg', name:'React TSX'},
  html:     {url:'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/html5/html5-original.svg', name:'HTML'},
  css:      {url:'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/css3/css3-original.svg', name:'CSS'},
  c:        {url:'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/c/c-original.svg', name:'C'},
  cpp:      {url:'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/cplusplus/cplusplus-original.svg', name:'C++'},
  csharp:   {url:'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/csharp/csharp-original.svg', name:'C#'},
  java:     {url:'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/java/java-original.svg', name:'Java'},
  rust:     {url:'https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/rust/rust-original.svg', name:'Rust'},
  go:       {url:'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/go/go-original.svg', name:'Go'}
};

const LYRIC_TRACKS = {
  sunset: {
    url: 'https://w.soundcloud.com/player/?url=https%3A//api.soundcloud.com/tracks/236166415&color=%236366f1&auto_play=false&hide_related=true&show_comments=false',
    lyrics: [
      {t:0,  l:''},
      {t:5,  l:'Chieu tan, anh den neon le loi'},
      {t:12, l:'Bong toi phu mo con duong nhung nguoi di'},
      {t:20, l:'Ta nhin troi, mua roi thay tung giot le roi'},
      {t:28, l:'Nho ai do, noi xa xoi, mot minh toi'},
      {t:36, l:'Sunset lover, em trong giac mo anh'},
      {t:44, l:'Mau vang hong phu len nhung duong chan troi'},
      {t:52, l:'Song con song... am am tren mat bien'},
      {t:60, l:'Gio thoi, mem mai, nghe nhu tieng goi'},
      {t:68, l:'Ta bay di cung em, noi minh tu do'},
      {t:76, l:'Khong con lo, khong con so, chi yeu thoi...'},
    ]
  },
  cyber: {
    url: 'https://w.soundcloud.com/player/?url=https%3A//api.soundcloud.com/tracks/1087027808&color=%2306b6d4&auto_play=false&hide_related=true&show_comments=false',
    lyrics: [
      {t:0,  l:''},
      {t:4,  l:'Neon lights flicker in the rain'},
      {t:10, l:'Circuits pulse beneath the city veins'},
      {t:17, l:'We run through data streams and code'},
      {t:24, l:'A ghost in the machine, alone on this road'},
      {t:32, l:'System override — engage'},
      {t:40, l:'The future burns, turn the page'},
      {t:48, l:'Chrome and steel, synthetic heart'},
      {t:56, l:'We were built for breaking apart'},
    ]
  },
  midnight: {
    url: 'https://w.soundcloud.com/player/?url=https%3A//api.soundcloud.com/tracks/1391843740&color=%23a855f7&auto_play=false&hide_related=true&show_comments=false',
    lyrics: [
      {t:0,  l:''},
      {t:6,  l:'Mua roi tren Tokyo, uot mem ban tay'},
      {t:14, l:'Den sap tat, con gac tro vang bong den'},
      {t:22, l:'Tieng piano khe khang, nho ai tu xa'},
      {t:30, l:'Dem Nhat Ban, ben minh chi co mot minh'},
      {t:38, l:'Sakura roi tren toc, lanh nhung dep'},
      {t:46, l:'Tieng hat vong, tieng hat vong trong gio'},
    ]
  }
};

let rpcRunning = false;
let rpcStartTime = null;
let timerInterval = null;
let logPollingInterval = null;
let rotatorInterval = null;
let currentPresets = [];
let currentLargeImageUrl = '';
let currentSmallImageUrl = '';
let detectedAppAvatarUrl = '';
let SCWidget = null;
let lyricSyncing = false;
let lyricInterval = null;
let currentLyrics = [];
let scDuration = 0;
let questRunnerInterval = null;
let questLogInterval = null;
let questLogLastCount = 0;
let currentQuestId = null;

// ============================================================
// TAB NAVIGATION
// ============================================================

function switchTab(tabId) {
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.sidebar-nav-item').forEach(b => b.classList.remove('active'));
  const panel = document.getElementById(tabId);
  if (panel) panel.classList.add('active');
  const btn = document.querySelector(`[data-tab="${tabId}"]`);
  if (btn) btn.classList.add('active');
  if (tabId === 'tab-rpc') startLogPolling();
  else if (tabId === 'tab-quest') { loadAvailableQuests(); startLogPolling('quest'); }
}

// ============================================================
// TOAST NOTIFICATIONS
// ============================================================

function showToast(msg, type = 'info', duration = 4000) {
  const container = document.getElementById('toast-container');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.textContent = msg;
  container.appendChild(toast);
  setTimeout(() => toast.classList.add('show'), 10);
  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 350);
  }, duration);
}

// ============================================================
// ACCOUNT MODAL
// ============================================================

function toggleAccountModal(show) {
  const bd = document.getElementById('account-modal-backdrop');
  if (!bd) return;
  if (show === true || show === undefined) {
    bd.classList.remove('d-none');
    bd.classList.add('modal-visible');
    document.body.style.overflow = 'hidden';
  } else {
    bd.classList.add('d-none');
    bd.classList.remove('modal-visible');
    document.body.style.overflow = '';
  }
}

function handleBackdropClick(e) {
  if (e.target === document.getElementById('account-modal-backdrop')) toggleAccountModal(false);
}

function toggleTokenVisibility() {
  const inp = document.getElementById('input-token');
  if (!inp) return;
  inp.type = inp.type === 'password' ? 'text' : 'password';
}

function copyTokenScript() {
  const script = `(webpackChunkdiscord_app.push([[''],{},e=>{m=[];for(let c in e.c)m.push(e.c[c])}]),m).find(m=>m?.exports?.default?.getToken!==void 0).exports.default.getToken()`;
  navigator.clipboard.writeText(script).then(() => showToast('Da copy script — Mo Discord Web > F12 > Dan vao Console', 'success'))
    .catch(() => showToast('Khong the copy — hay tu copy script', 'error'));
}

async function handleBindToken() {
  const tokenEl = document.getElementById('input-token');
  const appIdEl = document.getElementById('input-app-id');
  if (!tokenEl?.value.trim()) { showToast('Vui long dan Discord Token vao o nhap', 'error'); return; }
  showToast('Dang xac minh token...', 'info', 2000);
  try {
    const r = await fetch('/api/account/bind_token', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({token: tokenEl.value.trim(), app_id: appIdEl?.value.trim() || ''})
    });
    const d = await r.json();
    if (d.success) {
      showToast(`Da lien ket: ${d.username}!`, 'success');
      updateAccountUI(d);
      toggleAccountModal(false);
      document.getElementById('token-alert-bar')?.remove();
      loadAvailableQuests();
    } else showToast(d.message || d.error || 'Token khong hop le', 'error');
  } catch(e) { showToast('Loi ket noi may chu', 'error'); }
}

async function handleSaveConfig() {
  const cfg = buildRPCConfig();
  showToast('Dang luu cau hinh...', 'info', 1500);
  try {
    const r = await fetch('/api/save_config', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(cfg)
    });
    const d = await r.json();
    if (d.success) {
      showToast('Da luu cau hinh thanh cong!', 'success');
    } else {
      showToast(d.message || 'Loi khi luu cau hinh', 'error');
    }
  } catch(e) {
    showToast('Loi ket noi toi may chu', 'error');
  }
}

async function handleUnbindToken() {
  if (!confirm('Huy lien ket Discord Token?')) return;
  try {
    await fetch('/api/account/unbind_token', {method:'POST'});
    showToast('Da huy lien ket token', 'info');
    location.reload();
  } catch(e) { showToast('Loi huy lien ket', 'error'); }
}

function updateAccountUI(data) {
  const sacName = document.getElementById('sac-name');
  const sacBadge = document.getElementById('sac-badge');
  const sacImg = document.getElementById('sac-avatar-img');
  const sacPh = document.getElementById('sac-avatar-placeholder');
  const accName = document.getElementById('account-view-name');
  const accStatus = document.getElementById('account-view-status');
  const lscUser = document.getElementById('lsc-username');
  const lscAv = document.getElementById('lsc-avatar');
  const pvDisp = document.getElementById('pv-display-name');
  const pvAv = document.getElementById('pv-avatar');
  if (sacName) sacName.textContent = data.username || 'Discord';
  if (sacBadge) { sacBadge.textContent = 'Da Lien Ket'; sacBadge.className = 'sac-badge linked'; }
  if (data.avatar) {
    if (sacImg) { sacImg.src = data.avatar; sacImg.style.display = ''; }
    if (sacPh) sacPh.style.display = 'none';
    if (lscAv) lscAv.src = data.avatar;
    if (pvAv) pvAv.src = data.avatar;
  }
  if (accName) accName.textContent = data.username || '';
  if (accStatus) accStatus.textContent = 'Token da xac minh — dung chung ca 3 tinh nang';
  if (lscUser) lscUser.textContent = data.username || '';
  if (pvDisp) pvDisp.textContent = data.username || '';
}

// ============================================================
// RPC CONTROLS
// ============================================================

function buildRPCConfig() {
  const actType = document.getElementById('select-activity-type')?.value || 'playing';
  const name = document.getElementById('input-activity-name')?.value.trim() || 'Discord RPC';
  const details = document.getElementById('input-details')?.value.trim() || '';
  const state = document.getElementById('input-state')?.value.trim() || '';
  const largeImage = document.getElementById('input-large-image')?.value.trim() || currentLargeImageUrl || 'bot_avatar';
  const smallImage = document.getElementById('input-small-image')?.value.trim() || currentSmallImageUrl || '';
  const largeText = document.getElementById('input-large-text')?.value.trim() || '';
  const smallText = document.getElementById('input-small-text')?.value.trim() || '';
  const btn1Label = document.getElementById('input-btn1-label')?.value.trim() || '';
  const btn1Url = document.getElementById('input-btn1-url')?.value.trim() || '';
  const btn2Label = document.getElementById('input-btn2-label')?.value.trim() || '';
  const btn2Url = document.getElementById('input-btn2-url')?.value.trim() || '';
  const useTimestamp = document.getElementById('check-timestamp')?.checked || false;
  const status = document.getElementById('select-user-status')?.value || 'online';
  const appId = document.getElementById('input-app-id')?.value.trim() || '1546849576986607657';
  const streamUrl = document.getElementById('input-stream-url')?.value.trim() || '';
  const buttons = [];
  if (btn1Label && btn1Url) buttons.push({label: btn1Label, url: btn1Url});
  if (btn2Label && btn2Url) buttons.push({label: btn2Label, url: btn2Url});
  return { activity_type: actType, name, details, state, large_image: largeImage, small_image: smallImage,
    large_text: largeText, small_text: smallText, buttons, use_timestamp: useTimestamp,
    status, app_id: appId, stream_url: streamUrl };
}

async function handleStartRPC() {
  const cfg = buildRPCConfig();
  try {
    const r = await fetch('/api/start', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(cfg)});
    const d = await r.json();
    if (d.success) {
      rpcRunning = true; rpcStartTime = Date.now();
      document.getElementById('btn-start').disabled = true;
      document.getElementById('btn-update').disabled = false;
      document.getElementById('btn-stop').disabled = false;
      setLed('running'); startTimer(); startLogPolling();
      showToast('RPC da khoi dong!', 'success');
    } else showToast(d.error || 'Khoi dong that bai', 'error');
  } catch(e) { showToast('Loi ket noi may chu', 'error'); }
}

async function handleUpdateRPC() {
  const cfg = buildRPCConfig();
  try {
    const r = await fetch('/api/update', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(cfg)});
    const d = await r.json();
    if (d.success) showToast('Da cap nhat RPC!', 'success');
    else showToast(d.error || 'Cap nhat that bai', 'error');
  } catch(e) { showToast('Loi ket noi', 'error'); }
}

async function handleStopRPC() {
  try {
    const r = await fetch('/api/stop', {method:'POST'});
    const d = await r.json();
    if (d.success) {
      rpcRunning = false; rpcStartTime = null;
      document.getElementById('btn-start').disabled = false;
      document.getElementById('btn-update').disabled = true;
      document.getElementById('btn-stop').disabled = true;
      setLed('idle'); stopTimer();
      showToast('Da dung RPC', 'info');
    }
  } catch(e) { showToast('Loi dung RPC', 'error'); }
}




// ============================================================
// LIVE PREVIEW
// ============================================================

function updateLivePreview() {
  const actType = document.getElementById('select-activity-type')?.value || 'playing';
  const name = document.getElementById('input-activity-name')?.value || 'Visual Studio Code';
  const details = document.getElementById('input-details')?.value || '';
  const state = document.getElementById('input-state')?.value || '';
  const btn1L = document.getElementById('input-btn1-label')?.value || '';
  const btn1U = document.getElementById('input-btn1-url')?.value || '#';
  const btn2L = document.getElementById('input-btn2-label')?.value || '';
  const btn2U = document.getElementById('input-btn2-url')?.value || '#';
  const useTimer = document.getElementById('check-timestamp')?.checked;
  const userStatus = document.getElementById('select-user-status')?.value || 'online';

  const typeMap = {playing:'PLAYING A GAME', streaming:'LIVE ON TWITCH', listening:'LISTENING TO', watching:'WATCHING', competing:'COMPETING IN'};
  const el = (id) => document.getElementById(id);
  if (el('pv-activity-type-header')) el('pv-activity-type-header').textContent = typeMap[actType] || 'PLAYING A GAME';
  if (el('pv-activity-name')) el('pv-activity-name').textContent = name || '\u200b';
  if (el('pv-details')) el('pv-details').textContent = details || '';
  if (el('pv-state')) el('pv-state').textContent = state || '';
  el('pv-details').style.display = details ? '' : 'none';
  el('pv-state').style.display = state ? '' : 'none';
  if (el('pv-time')) el('pv-time').style.display = useTimer ? '' : 'none';

  const btnsEl = document.querySelector('.dpm-act-buttons');
  if (btnsEl) {
    const b1 = document.getElementById('pv-btn1');
    const b2 = document.getElementById('pv-btn2');
    if (b1) { b1.textContent = btn1L || ''; b1.href = btn1U; b1.style.display = btn1L ? '' : 'none'; }
    if (b2) { b2.textContent = btn2L || ''; b2.href = btn2U; b2.style.display = btn2L ? '' : 'none'; }
    btnsEl.style.display = (btn1L || btn2L) ? '' : 'none';
  }

  const dotEl = document.getElementById('pv-status-dot');
  if (dotEl) {
    const cols = {online:'#3ba55c', idle:'#faa61a', dnd:'#ed4245', invisible:'#747f8d'};
    dotEl.style.background = cols[userStatus] || '#3ba55c';
  }

  // Dong bo hien thi anh lon
  const largeImgVal = document.getElementById('input-large-image')?.value.trim() || currentLargeImageUrl;
  const pvLarge = document.getElementById('pv-large-img');
  if (pvLarge) {
    if (largeImgVal) {
      if (!largeImgVal.startsWith('http')) {
        const known = KNOWN_ASSET_ICONS[largeImgVal];
        pvLarge.src = known ? known.url : 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/vscode/vscode-original.svg';
      } else {
        pvLarge.src = largeImgVal;
      }
    } else {
      pvLarge.src = 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/vscode/vscode-original.svg';
    }
  }

  // Dong bo hien thi anh nho: Neu co anh nho thi hien de len goc anh to, neu go anh nho thi chi hien 1 anh to
  const smallImgVal = document.getElementById('input-small-image')?.value.trim() || currentSmallImageUrl;
  const pvSmall = document.getElementById('pv-small-img');
  if (pvSmall) {
    if (smallImgVal) {
      if (!smallImgVal.startsWith('http')) {
        const known = KNOWN_ASSET_ICONS[smallImgVal];
        pvSmall.src = known ? known.url : smallImgVal;
      } else {
        pvSmall.src = smallImgVal;
      }
      pvSmall.style.display = 'block';
    } else {
      pvSmall.src = '';
      pvSmall.style.display = 'none';
    }
  }
}

// ============================================================
// TIMER
// ============================================================

function startTimer() {
  stopTimer();
  timerInterval = setInterval(() => {
    if (!rpcStartTime) return;
    const elapsed = Math.floor((Date.now() - rpcStartTime) / 1000);
    const h = Math.floor(elapsed / 3600);
    const m = Math.floor((elapsed % 3600) / 60);
    const s = elapsed % 60;
    const txt = h > 0 ? `${h}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')} elapsed`
                      : `${m}:${String(s).padStart(2,'0')} elapsed`;
    const el = document.getElementById('pv-timer-text');
    if (el) el.textContent = txt;
  }, 1000);
}

function stopTimer() {
  if (timerInterval) { clearInterval(timerInterval); timerInterval = null; }
}

// ============================================================
// LED / STATUS
// ============================================================

function setLed(state) {
  const led = document.getElementById('led-indicator');
  const txt = document.getElementById('status-text');
  if (!led) return;
  led.className = 'status-led';
  if (state === 'running') {
    led.classList.add('led-green');
    if (txt) txt.textContent = 'RPC Dang Chay';
  } else if (state === 'quest') {
    led.classList.add('led-amber');
    if (txt) txt.textContent = 'Quest Dang Chay';
  } else if (state === 'lyric') {
    led.classList.add('led-cyan');
    if (txt) txt.textContent = 'Lyric Dang Dong Bo';
  } else {
    if (txt) txt.textContent = 'Chua Chay';
  }
}

// ============================================================
// LOG POLLING
// ============================================================

function startLogPolling(type = 'rpc') {
  if (logPollingInterval) { clearInterval(logPollingInterval); logPollingInterval = null; }
  logPollingInterval = setInterval(() => fetchLogs(type), 2000);
}

async function fetchLogs(type = 'rpc') {
  try {
    const r = await fetch('/api/logs');
    const d = await r.json();
    const screenId = type === 'quest' ? 'quest-log-screen' : 'terminal-screen';
    const screen = document.getElementById(screenId);
    if (!screen || !d.logs) return;
    const wasBottom = screen.scrollTop + screen.clientHeight >= screen.scrollHeight - 5;
    const existing = screen.querySelectorAll('.log-line').length;
    if (d.logs.length > existing) {
      const newLogs = d.logs.slice(existing);
      newLogs.forEach(log => {
        const div = document.createElement('div');
        const lvl = log.level || 'info';
        div.className = `log-line ${lvl}`;
        div.innerHTML = `<span class="log-time">[${log.time}]</span><span class="log-tag">[${lvl.toUpperCase()}]</span><span class="log-msg">${escapeHtml(log.message)}</span>`;
        screen.appendChild(div);
      });
      if (wasBottom) screen.scrollTop = screen.scrollHeight;
    }
  } catch(e) {}
}

function clearLogs() {
  const screen = document.getElementById('terminal-screen');
  if (screen) screen.innerHTML = '';
}

function escapeHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ============================================================
// PRESETS
// ============================================================

async function loadPresets() {
  try {
    const r = await fetch('/api/presets');
    const d = await r.json();
    currentPresets = d.presets || [];
    renderPresets();
  } catch(e) {}
}

function renderPresets() {
  const bar = document.getElementById('preset-list');
  if (!bar) return;
  bar.innerHTML = '';
  if (!currentPresets.length) {
    bar.innerHTML = '<span style="font-size:0.78rem;color:var(--text-muted)">Chua co preset nao. Luu preset de bat dau.</span>';
    return;
  }
  currentPresets.forEach(p => {
    const btn = document.createElement('button');
    btn.className = 'preset-chip';
    btn.textContent = p.name;
    btn.title = `Load preset: ${p.name}`;
    btn.onclick = () => loadPreset(p.id);
    const del = document.createElement('button');
    del.className = 'preset-chip-del';
    del.textContent = 'x';
    del.onclick = (e) => { e.stopPropagation(); deletePreset(p.id); };
    const wrap = document.createElement('div');
    wrap.className = 'preset-chip-wrap';
    wrap.appendChild(btn);
    wrap.appendChild(del);
    bar.appendChild(wrap);
  });
}

async function loadPreset(id) {
  try {
    const r = await fetch(`/api/presets/${id}`);
    const d = await r.json();
    if (!d.config) return;
    const c = d.config;
    const set = (elId, val) => { const e = document.getElementById(elId); if (e && val !== undefined) e.value = val; };
    set('input-activity-name', c.name);
    set('input-details', c.details);
    set('input-state', c.state);
    set('input-large-image', c.large_image);
    set('input-small-image', c.small_image);
    set('input-large-text', c.large_text);
    set('input-small-text', c.small_text);
    set('input-btn1-label', c.buttons?.[0]?.label || '');
    set('input-btn1-url', c.buttons?.[0]?.url || '');
    set('input-btn2-label', c.buttons?.[1]?.label || '');
    set('input-btn2-url', c.buttons?.[1]?.url || '');
    set('select-activity-type', c.activity_type || 'playing');
    set('input-app-id', c.app_id || '');
    const ts = document.getElementById('check-timestamp');
    if (ts) ts.checked = !!c.use_timestamp;
    onManualImageChange('large');
    onManualImageChange('small');
    updateLivePreview();
    showToast(`Da load preset "${d.name}"`, 'success');
  } catch(e) { showToast('Loi load preset', 'error'); }
}

async function saveCurrentAsPreset() {
  const name = prompt('Ten Preset:');
  if (!name?.trim()) return;
  const cfg = buildRPCConfig();
  try {
    const r = await fetch('/api/presets', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({name: name.trim(), config: cfg})});
    const d = await r.json();
    if (d.success) { showToast(`Da luu preset "${name}"`, 'success'); loadPresets(); }
    else showToast(d.error || 'Luu that bai', 'error');
  } catch(e) { showToast('Loi luu preset', 'error'); }
}

async function deletePreset(id) {
  if (!confirm('Xoa preset nay?')) return;
  try {
    await fetch(`/api/presets/${id}`, {method:'DELETE'});
    showToast('Da xoa preset', 'info');
    loadPresets();
  } catch(e) {}
}

// ============================================================
// ACTIVITY TYPE CHANGE
// ============================================================

function onActivityTypeChange() {
  const val = document.getElementById('select-activity-type')?.value;
  const streamGroup = document.getElementById('stream-url-group');
  if (streamGroup) streamGroup.classList.toggle('d-none', val !== 'streaming');
  updateLivePreview();
}

// ============================================================
// IMAGE HANDLING
// ============================================================

function triggerUpload(type) {
  document.getElementById(`file-upload-${type}`)?.click();
}

async function uploadImageFile(input, type) {
  if (!input.files?.length) return;
  const file = input.files[0];
  const formData = new FormData();
  formData.append('image', file);
  formData.append('type', type);
  showToast('Dang tai len anh...', 'info', 2000);
  try {
    const r = await fetch('/api/upload', {method:'POST', body: formData});
    const d = await r.json();
    if (d.success) {
      const url = d.url;
      if (type === 'large') {
        currentLargeImageUrl = url;
        const img = document.getElementById('box-large-preview');
        if (img) img.src = url;
        const pvImg = document.getElementById('pv-large-img');
        if (pvImg) pvImg.src = url;
        const src = document.getElementById('lbl-large-source');
        if (src) src.textContent = 'Hinh tai len';
      } else {
        currentSmallImageUrl = url;
        const wrap = document.getElementById('wrap-small-preview');
        if (wrap) wrap.style.display = '';
        const img = document.getElementById('box-small-preview');
        if (img) { img.src = url; img.style.display = ''; }
        const pvImg = document.getElementById('pv-small-img');
        if (pvImg) { pvImg.src = url; pvImg.style.display = 'block'; }
        const src = document.getElementById('lbl-small-source');
        if (src) src.textContent = 'Hinh tai len';
        const btnAdd = document.getElementById('btn-add-small');
        if (btnAdd) btnAdd.textContent = 'Doi Anh';
        const btnRemove = document.getElementById('btn-remove-small');
        if (btnRemove) btnRemove.style.display = '';
      }
      showToast('Da tai len anh!', 'success');
    } else showToast(d.error || 'Tai len that bai', 'error');
  } catch(e) { showToast('Loi tai len anh', 'error'); }
}

function onManualImageChange(type) {
  const val = document.getElementById(`input-${type}-image`)?.value.trim() || '';
  if (!val) {
    if (type === 'small') clearSmallImage();
    return;
  }
  let url = val;
  let iconName = val;
  if (['bot_avatar', 'app', 'bot', 'developer_portal', 'portal'].includes(val.toLowerCase())) {
    url = detectedAppAvatarUrl || 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/vscode/vscode-original.svg';
    iconName = 'Bot Avatar';
  } else if (!val.startsWith('http')) {
    const known = KNOWN_ASSET_ICONS[val];
    if (known) {
      url = known.url;
      iconName = known.name;
    } else {
      url = 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/vscode/vscode-original.svg';
      iconName = val;
    }
  }
  if (type === 'large') {
    const img = document.getElementById('box-large-preview');
    const pvImg = document.getElementById('pv-large-img');
    if (img) img.src = url;
    if (pvImg) pvImg.src = url;
    currentLargeImageUrl = url;
    const src = document.getElementById('lbl-large-source');
    if (src) src.textContent = iconName;
  } else {
    currentSmallImageUrl = url;
    const wrap = document.getElementById('wrap-small-preview');
    if (wrap) wrap.style.display = '';
    const img = document.getElementById('box-small-preview');
    if (img) { img.src = url; img.style.display = ''; }
    const pvImg = document.getElementById('pv-small-img');
    if (pvImg) { pvImg.src = url; pvImg.style.display = 'block'; }
    const src = document.getElementById('lbl-small-source');
    if (src) src.textContent = iconName;
    const btnAdd = document.getElementById('btn-add-small');
    if (btnAdd) btnAdd.textContent = 'Doi Anh';
    const btnRemove = document.getElementById('btn-remove-small');
    if (btnRemove) btnRemove.style.display = '';
  }
}

function toggleManualInput(type) {
  const wrap = document.getElementById(`manual-${type}-wrap`);
  if (wrap) wrap.classList.toggle('d-none');
}

function clearSmallImage() {
  currentSmallImageUrl = '';
  const wrap = document.getElementById('wrap-small-preview');
  if (wrap) wrap.style.display = 'none';
  const img = document.getElementById('box-small-preview');
  if (img) { img.src = ''; img.style.display = 'none'; }
  const pvImg = document.getElementById('pv-small-img');
  if (pvImg) { pvImg.src = ''; pvImg.style.display = 'none'; }
  const inp = document.getElementById('input-small-image');
  if (inp) inp.value = '';
  const src = document.getElementById('lbl-small-source');
  if (src) src.textContent = 'Chua them anh nho';
  const btnAdd = document.getElementById('btn-add-small');
  if (btnAdd) btnAdd.textContent = '+ Them / Tai Len';
  const btnRemove = document.getElementById('btn-remove-small');
  if (btnRemove) btnRemove.style.display = 'none';
  showToast('Da go anh nho — xem truoc chi con 1 anh lon', 'info');
}

// ============================================================
// GALLERY GRID
// ============================================================

function buildVisualGallery() {
  const grid = document.getElementById('visual-gallery-grid');
  if (!grid) return;
  grid.innerHTML = '';
  Object.entries(KNOWN_ASSET_ICONS).forEach(([key, val]) => {
    const btn = document.createElement('button');
    btn.className = 'gallery-icon-btn';
    btn.title = val.name;
    btn.innerHTML = `<img src="${val.url}" alt="${val.name}" loading="lazy"><span>${val.name}</span>`;
    btn.onclick = () => {
      const inp = document.getElementById('input-small-image');
      if (inp) { inp.value = key; inp.closest('#manual-small-wrap')?.classList.remove('d-none'); }
      onManualImageChange('small');
      showToast(`Da chon icon: ${val.name}`, 'info', 2000);
    };
    grid.appendChild(btn);
  });
}

// ============================================================
// PORTAL / BOT SCANNING
// ============================================================

async function scanPortalApps(silent = false) {
  if (!silent) showToast('Dang quet Developer Portal...', 'info', 2500);
  try {
    const r = await fetch('/api/portal_app_info');
    const d = await r.json();
    if (d.success && d.apps?.length) {
      const app = d.apps[0];
      detectedAppAvatarUrl = app.avatar_url || '';
      const banner = document.getElementById('detected-app-banner');
      const icon = document.getElementById('detected-app-icon');
      const title = document.getElementById('detected-app-title');
      const desc = document.getElementById('detected-app-desc');
      if (banner) banner.classList.remove('d-none');
      const fallback = document.getElementById('detected-app-fallback');
      if (icon) {
        if (app.avatar_url) {
          icon.src = app.avatar_url;
          icon.style.display = 'block';
          if (fallback) fallback.style.display = 'none';
        } else {
          icon.style.display = 'none';
          if (fallback) fallback.style.display = 'flex';
        }
      }
      if (title) title.textContent = app.name || 'App';
      if (desc) desc.textContent = `ID: ${app.id} — Tìm thấy trên Developer Portal!`;
      const container = document.getElementById('portal-bots-container');
      if (container) {
        container.innerHTML = '';
        d.apps.slice(0, 6).forEach(a => {
          const chip = document.createElement('div');
          chip.className = 'bot-chip';
          const avatarHtml = a.avatar_url
            ? `<img src="${a.avatar_url}" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';" alt=""><span class="bot-chip-fallback" style="display:none;">🤖</span>`
            : `<span class="bot-chip-fallback">🤖</span>`;
          chip.innerHTML = `${avatarHtml}<span>${escapeHtml(a.name)}</span>`;
          chip.onclick = () => {
            const appId = document.getElementById('input-app-id');
            if (appId) appId.value = a.id;
            detectedAppAvatarUrl = a.avatar_url || '';
            showToast(`Đã chọn app: ${a.name}`, 'success');
          };
          container.appendChild(chip);
        });
      }
      if (!silent) showToast(`Tim thay ${d.apps.length} app(s) tren Portal`, 'success');
    } else {
      if (!silent) showToast('Khong tim thay app nao tren Portal', 'warning');
    }
  } catch(e) { if (!silent) showToast('Loi quet Portal', 'error'); }
}

function applyDetectedAvatar() {
  if (!detectedAppAvatarUrl) { showToast('Chua co avatar de ap dung', 'warning'); return; }
  const img = document.getElementById('box-large-preview');
  const pvImg = document.getElementById('pv-large-img');
  if (img) img.src = detectedAppAvatarUrl;
  if (pvImg) pvImg.src = detectedAppAvatarUrl;
  currentLargeImageUrl = detectedAppAvatarUrl;
  const src = document.getElementById('lbl-large-source');
  if (src) src.textContent = 'Bot Portal Avatar';
  showToast('Da ap dung Bot Avatar!', 'success');
}

async function useDevPortalAvatar() {
  await scanPortalApps(true);
  applyDetectedAvatar();
}

// ============================================================
// ROTATOR
// ============================================================

function toggleRotator() {
  const on = document.getElementById('check-rotator')?.checked;
  if (on) {
    const interval = parseInt(document.getElementById('input-rotator-interval')?.value || '30') * 1000;
    rotatorInterval = setInterval(async () => {
      if (!currentPresets.length) return;
      const idx = Math.floor(Math.random() * currentPresets.length);
      await loadPreset(currentPresets[idx].id);
      if (rpcRunning) await handleUpdateRPC();
    }, interval);
    showToast('Bat che do xoay vong preset', 'info');
  } else {
    clearInterval(rotatorInterval); rotatorInterval = null;
    showToast('Da tat xoay vong preset', 'info');
  }
}

// ============================================================
// SOUNDCLOUD WIDGET
// ============================================================

function initSCWidget() {
  const iframe = document.getElementById('sc-widget');
  if (!iframe || typeof SC === 'undefined') { setTimeout(initSCWidget, 600); return; }
  SCWidget = SC.Widget(iframe);
  SCWidget.bind(SC.Widget.Events.READY, () => {
    SCWidget.getDuration(d => { scDuration = d / 1000; });
  });
  SCWidget.bind(SC.Widget.Events.FINISH, () => {
    if (lyricSyncing) handleStopLyricAudio();
  });
}

function loadCustomSoundCloudUrl() {
  const url = document.getElementById('input-soundcloud-url')?.value.trim();
  if (!url) { showToast('Vui long dan link SoundCloud', 'warning'); return; }
  const encoded = encodeURIComponent(url);
  const iframeUrl = `https://w.soundcloud.com/player/?url=${encoded}&color=%236366f1&auto_play=false&hide_related=true&show_comments=false&show_user=true&show_reposts=false&show_teaser=false`;
  const iframe = document.getElementById('sc-widget');
  if (iframe) {
    iframe.src = iframeUrl;
    setTimeout(initSCWidget, 1000);
  }
  showToast('Dang nap bai hat...', 'info', 2000);
}

function handleSelectLyricTrack() {
  const val = document.getElementById('select-lyric-track')?.value;
  const customGroup = document.getElementById('custom-lrc-group');
  if (val === 'custom') {
    if (customGroup) customGroup.classList.remove('d-none');
    return;
  }
  if (customGroup) customGroup.classList.add('d-none');
  const track = LYRIC_TRACKS[val];
  if (!track) return;
  currentLyrics = track.lyrics;
  const iframe = document.getElementById('sc-widget');
  if (iframe) {
    iframe.src = track.url;
    setTimeout(initSCWidget, 1000);
  }
}

function handleToggleLyricAudio() {
  if (!SCWidget) { showToast('Widget chua san sang, doi mot chut', 'warning'); return; }
  if (lyricSyncing) { handleStopLyricAudio(); return; }
  const sel = document.getElementById('select-lyric-track')?.value;
  if (sel === 'custom') {
    const raw = document.getElementById('input-custom-lrc')?.value.trim();
    currentLyrics = parseLRC(raw);
  } else if (LYRIC_TRACKS[sel]) {
    currentLyrics = LYRIC_TRACKS[sel].lyrics;
  }
  SCWidget.play();
  lyricSyncing = true;
  setLed('lyric');
  const playBtn = document.getElementById('btn-lyric-play');
  const stopBtn = document.getElementById('btn-lyric-stop');
  if (playBtn) playBtn.textContent = 'Dung Dong Bo';
  if (stopBtn) stopBtn.disabled = false;
  const syncInd = document.getElementById('lyric-sync-indicator');
  if (syncInd) syncInd.style.display = '';
  const liveDot = document.getElementById('lyric-live-dot');
  if (liveDot) liveDot.style.display = '';
  lyricInterval = setInterval(syncLyric, 500);
}

function handleStopLyricAudio() {
  if (SCWidget) SCWidget.pause();
  lyricSyncing = false;
  clearInterval(lyricInterval); lyricInterval = null;
  setLed('idle');
  const playBtn = document.getElementById('btn-lyric-play');
  const stopBtn = document.getElementById('btn-lyric-stop');
  if (playBtn) playBtn.textContent = 'Bat Dau Dong Bo';
  if (stopBtn) stopBtn.disabled = true;
  const syncInd = document.getElementById('lyric-sync-indicator');
  if (syncInd) syncInd.style.display = 'none';
  const liveDot = document.getElementById('lyric-live-dot');
  if (liveDot) liveDot.style.display = 'none';
  showToast('Da dung Lyric Sync', 'info');
}

async function handleClearDiscordStatus() {
  try {
    const r = await fetch('/api/lyrics/clear', {method:'POST'});
    const d = await r.json();
    if (d.success) {
      showToast('Da xoa Custom Status!', 'success');
      const lyr = document.getElementById('lsc-lyric-current');
      if (lyr) lyr.textContent = 'Status da duoc xoa';
    } else showToast(d.error || 'Loi xoa status', 'error');
  } catch(e) { showToast('Loi ket noi', 'error'); }
}

function syncLyric() {
  if (!SCWidget || !lyricSyncing) return;
  SCWidget.getPosition(pos => {
    const sec = pos / 1000;
    SCWidget.getDuration(dur => {
      scDuration = dur / 1000;
      updateLyricProgress(sec, scDuration);
    });
    const line = getCurrentLyric(sec);
    if (line !== undefined) {
      updateLyricDisplay(line, sec);
    }
  });
}

function getCurrentLyric(sec) {
  if (!currentLyrics.length) return undefined;
  let current = '';
  for (let i = 0; i < currentLyrics.length; i++) {
    if (sec >= currentLyrics[i].t) current = currentLyrics[i].l;
    else break;
  }
  return current;
}

function updateLyricDisplay(line, sec) {
  const emoji = document.getElementById('select-lyric-emoji')?.value || '🎵';
  const lscEl = document.getElementById('lsc-lyric-current');
  const emojiEl = document.getElementById('lsc-emoji');
  if (lscEl) lscEl.textContent = line || '♪ ♫ ♪';
  if (emojiEl) emojiEl.textContent = emoji;

  const wrapper = document.getElementById('lyric-lines-wrapper');
  if (wrapper) {
    wrapper.innerHTML = '';
    const nearLines = currentLyrics.filter(l => Math.abs(l.t - sec) < 20 && l.l);
    if (!nearLines.length) {
      const d = document.createElement('div');
      d.className = 'lyric-line';
      d.textContent = '♪ ♫ ♪';
      wrapper.appendChild(d);
      return;
    }
    nearLines.forEach(l => {
      const d = document.createElement('div');
      d.className = 'lyric-line' + (l.l === line ? ' active' : '');
      d.textContent = l.l;
      wrapper.appendChild(d);
    });
  }

  if (lyricSyncing && line) {
    fetch('/api/lyrics/sync', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({status: line, emoji: emoji})
    }).catch(() => {});
  }
}

function updateLyricProgress(sec, total) {
  const fill = document.getElementById('lsc-progress-fill');
  const cur = document.getElementById('audio-time-current');
  const tot = document.getElementById('audio-time-total');
  if (fill && total > 0) fill.style.width = `${(sec / total) * 100}%`;
  if (cur) cur.textContent = formatTime(sec);
  if (tot) tot.textContent = formatTime(total);
}

function formatTime(sec) {
  const s = Math.floor(sec);
  const m = Math.floor(s / 60);
  const ss = s % 60;
  return `${String(m).padStart(2,'0')}:${String(ss).padStart(2,'0')}`;
}

function parseLRC(raw) {
  if (!raw) return [];
  const lines = [];
  raw.split('\n').forEach(line => {
    const m = line.match(/\[(\d+):(\d+)\]\s*(.*)/);
    if (m) {
      lines.push({ t: parseInt(m[1]) * 60 + parseInt(m[2]), l: m[3].trim() });
    }
  });
  return lines.sort((a, b) => a.t - b.t);
}

// ============================================================
// ============================================================
// QUEST
// ============================================================

async function loadAvailableQuests() {
  const container = document.getElementById('quests-list-container');
  if (!container) return;
  container.innerHTML = '<div class="quest-loading">Dang tai danh sach nhiem vu Discord...</div>';
  try {
    const r = await fetch('/api/quests');
    const d = await r.json();
    container.innerHTML = '';
    if (!d.quests?.length) {
      container.innerHTML = '<div class="quest-loading">Khong tim thay nhiem vu nao hoac chua lien ket Discord Token.</div>';
      return;
    }
    d.quests.forEach(q => {
      const card = buildQuestCard(q);
      container.appendChild(card);
    });
  } catch(e) {
    container.innerHTML = '<div class="quest-loading">Loi khi tai danh sach nhiem vu tu may chu.</div>';
  }
}

// ============================================================
// QUEST LOG TERMINAL
// ============================================================

const QUEST_LOG_LEVEL_COLOR = {
  'success': '#4ade80',
  'error': '#f87171',
  'warning': '#fbbf24',
  'warn': '#fbbf24',
  'info': '#a5b4fc'
};

function appendQuestLog(entry) {
  const screen = document.getElementById('quest-log-screen');
  if (!screen) return;
  const line = document.createElement('div');
  line.className = `log-line ${entry.level || 'info'}`;
  const color = QUEST_LOG_LEVEL_COLOR[entry.level] || '#a5b4fc';
  line.innerHTML = `<span class="log-time" style="color:#64748b;">[${entry.time}]</span> <span class="log-msg" style="color:${color};">${escapeHtml(entry.message)}</span>`;
  screen.appendChild(line);
  // Auto-scroll to bottom
  screen.scrollTop = screen.scrollHeight;
  // Trim old entries (keep max 100 lines visible)
  while (screen.children.length > 120) {
    screen.removeChild(screen.firstChild);
  }
}

function clearQuestLog() {
  const screen = document.getElementById('quest-log-screen');
  if (screen) screen.innerHTML = '';
  questLogLastCount = 0;
}

async function fetchQuestLogs() {
  try {
    const r = await fetch('/api/quests/logs');
    const d = await r.json();
    if (!d.success || !d.logs) return;
    const logs = d.logs;
    if (logs.length > questLogLastCount) {
      // Append only new entries
      for (let i = questLogLastCount; i < logs.length; i++) {
        appendQuestLog(logs[i]);
      }
      questLogLastCount = logs.length;
    }
  } catch(e) {}
}

function startQuestLogPolling() {
  if (questLogInterval) clearInterval(questLogInterval);
  questLogInterval = setInterval(fetchQuestLogs, 800);
}

function stopQuestLogPolling() {
  if (questLogInterval) { clearInterval(questLogInterval); questLogInterval = null; }
}


async function handleAutoEnrollAll() {
  showToast('Dang tu dong nhan tat ca Quest tren Discord...', 'info', 2500);
  try {
    const r = await fetch('/api/quests/enroll_all', {method: 'POST'});
    const d = await r.json();
    if (d.success) {
      showToast(d.message || `Da nhan tat ca nhiem vu thanh cong!`, 'success');
      loadAvailableQuests();
    } else {
      showToast(d.message || 'Khong the nhan nhiem vu', 'error');
    }
  } catch(e) {
    showToast('Loi ket noi khi nhan nhiem vu', 'error');
  }
}

function buildQuestCard(q) {
  const card = document.createElement('div');
  card.className = 'quest-card-v2';
  const pct = q.progress_pct || 0;
  const imgUrl = q.banner_url || q.banner || '';
  const taskBadge = q.task_type || q.type || 'Quest';
  const isEnrolled = q.enrolled;
  const isCompleted = q.completed;

  let actionBtn = `<button type="button" class="quest-card-start-btn" onclick="handleStartQuest('${escapeHtml(q.id || '')}', '${escapeHtml(q.title || q.name || 'Quest')}', '${escapeHtml(q.game_name || '')}', '${escapeHtml(imgUrl)}', '${escapeHtml(taskBadge)}', ${q.target_seconds || 60})">Bat Dau Auto Cay</button>`;
  if (isCompleted) {
    actionBtn = `<button type="button" class="quest-card-start-btn completed" disabled>Da Hoan Thanh</button>`;
  }

  card.innerHTML = `
    ${imgUrl ? `<img src="${escapeHtml(imgUrl)}" class="quest-card-banner" alt="${escapeHtml(q.title || '')}" onerror="this.style.display='none'">` : ''}
    <div class="quest-card-body">
      <div class="quest-card-badge-row">
        <span class="quest-card-badge">${escapeHtml(taskBadge)}</span>
        ${isEnrolled ? '<span class="quest-tag enrolled">Da Nhan</span>' : '<span class="quest-tag not-enrolled">Chua Nhan</span>'}
      </div>
      <div class="quest-card-title">${escapeHtml(q.title || q.name || 'Nhiem vu')}</div>
      <div class="quest-card-game">${escapeHtml(q.game_name || q.app_name || '')}</div>
      ${q.rewards_text ? `<div class="quest-card-reward">Phan thuong: ${escapeHtml(q.rewards_text)}</div>` : ''}
      <div class="quest-card-progress">
        <div class="quest-card-progress-bar"><div class="quest-card-progress-fill" style="width:${pct}%"></div></div>
        <div class="quest-card-progress-pct">${pct}% hoan thanh (${Math.round(q.seconds_done || 0)}s / ${q.target_seconds || 60}s)</div>
      </div>
      ${actionBtn}
    </div>`;
  return card;
}

async function handleStartAutoQuest() {
  const titleEl = document.getElementById('quest-active-title');
  const subEl = document.getElementById('quest-active-sub');
  const chip = document.getElementById('quest-status-chip');
  if (titleEl) titleEl.textContent = 'Auto Completer Đang Chạy...';
  if (subEl) subEl.textContent = 'Đang tự động quét & hoàn thành tất cả Quest...';
  if (chip) { chip.textContent = 'Đang Chạy Auto'; chip.className = 'quest-status-badge running'; }
  setLed('quest');
  const stopBtn = document.getElementById('btn-quest-stop');
  if (stopBtn) stopBtn.disabled = false;

  // Clear console and start log polling
  clearQuestLog();
  await fetch('/api/quests/logs', {method: 'DELETE'});
  questLogLastCount = 0;
  startQuestLogPolling();

  try {
    const r = await fetch('/api/quests/start', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({auto: true})
    });
    const d = await r.json();
    if (d.success) {
      showToast('Đã khởi động Quest Auto-Completer!', 'success');
      startQuestProgressPolling('auto', 100);
    } else {
      showToast(d.message || 'Không thể chạy Auto Quest', 'error');
      if (chip) { chip.textContent = 'Lỗi'; chip.className = 'quest-status-badge'; }
      setLed('idle');
      if (stopBtn) stopBtn.disabled = true;
      stopQuestLogPolling();
    }
  } catch(e) {
    showToast('Lỗi kết nối máy chủ', 'error');
    stopQuestLogPolling();
  }
}

async function handleStartQuest(id, name, game, imgUrl, taskType, targetSec) {
  currentQuestId = id;
  const titleEl = document.getElementById('quest-active-title');
  const subEl = document.getElementById('quest-active-sub');
  const bannerEl = document.getElementById('quest-game-banner');
  const chip = document.getElementById('quest-status-chip');
  if (titleEl) titleEl.textContent = name;
  if (subEl) subEl.textContent = `Game: ${game || 'Discord'} [${taskType}] — Đang khởi động...`;
  if (chip) { chip.textContent = 'Đang Chạy'; chip.className = 'quest-status-badge running'; }
  if (bannerEl) {
    if (imgUrl) bannerEl.innerHTML = `<img src="${escapeHtml(imgUrl)}" alt="" style="width:100%;height:100%;object-fit:cover;" onerror="this.style.display='none'">`;
    else bannerEl.innerHTML = `<div class="qrc-game-placeholder">${escapeHtml(game || 'Quest')}</div>`;
  }
  setLed('quest');
  const stopBtn = document.getElementById('btn-quest-stop');
  if (stopBtn) stopBtn.disabled = false;

  // Clear console and start log polling
  clearQuestLog();
  await fetch('/api/quests/logs', {method: 'DELETE'});
  questLogLastCount = 0;
  startQuestLogPolling();

  try {
    const r = await fetch('/api/quests/start', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({quest_id: id, quest_name: name, task_type: taskType, target_seconds: targetSec})
    });
    const d = await r.json();
    if (d.success) {
      showToast(`Bắt đầu cày: ${name}`, 'success');
      startQuestProgressPolling(id, targetSec);
    } else {
      showToast(d.message || 'Không thể bắt đầu quest', 'error');
      if (chip) { chip.textContent = 'Lỗi'; chip.className = 'quest-status-badge'; }
      setLed('idle');
      if (stopBtn) stopBtn.disabled = true;
      stopQuestLogPolling();
    }
  } catch(e) { showToast('Lỗi kết nối máy chủ', 'error'); stopQuestLogPolling(); }
}

function startQuestProgressPolling(id, targetSec) {
  if (questRunnerInterval) clearInterval(questRunnerInterval);
  questRunnerInterval = setInterval(async () => {
    try {
      const r = await fetch('/api/quests/status');
      const d = await r.json();
      const st = d.status || {};
      const pct = st.progress_pct || 0;
      const elapsed = st.elapsed_seconds || 0;
      const target = st.target_seconds || targetSec;

      const titleEl = document.getElementById('quest-active-title');
      const subEl = document.getElementById('quest-active-sub');
      if (st.is_auto_mode && st.quest_name && titleEl) {
        titleEl.textContent = `Auto: ${st.quest_name}`;
        if (subEl) subEl.textContent = `Loại: ${st.task_type || 'N/A'} — Đang tự động xử lý`;
      }

      const pctEl = document.getElementById('quest-progress-pct');
      const fillEl = document.getElementById('quest-progress-fill');
      const timeEl = document.getElementById('quest-progress-time');
      if (pctEl) pctEl.textContent = `${pct}%`;
      if (fillEl) fillEl.style.width = `${pct}%`;
      if (timeEl) timeEl.textContent = `${elapsed}s / ${target}s`;

      if (st.status === 'completed') {
        clearInterval(questRunnerInterval);
        questRunnerInterval = null;
        stopQuestLogPolling();
        await fetchQuestLogs();
        const chip = document.getElementById('quest-status-chip');
        if (chip) { chip.textContent = 'Hoàn Thành'; chip.className = 'quest-status-badge completed'; }
        setLed('idle');
        const stopBtn = document.getElementById('btn-quest-stop');
        if (stopBtn) stopBtn.disabled = true;
        showToast('Nhiệm vụ đã hoàn thành!', 'success', 6000);
        loadAvailableQuests();
      } else if (st.status === 'stopped') {
        clearInterval(questRunnerInterval);
        questRunnerInterval = null;
        stopQuestLogPolling();
        const chip = document.getElementById('quest-status-chip');
        if (chip) { chip.textContent = 'Đã Dừng'; chip.className = 'quest-status-badge'; }
        setLed('idle');
        const stopBtn = document.getElementById('btn-quest-stop');
        if (stopBtn) stopBtn.disabled = true;
      }
    } catch(e) {}
  }, 1200);
}

async function handleStopQuest() {
  try {
    await fetch('/api/quests/stop', {method:'POST'});
    if (questRunnerInterval) {
      clearInterval(questRunnerInterval);
      questRunnerInterval = null;
    }
    stopQuestLogPolling();
    setLed('idle');
    const chip = document.getElementById('quest-status-chip');
    if (chip) { chip.textContent = 'Da Dung'; chip.className = 'quest-status-badge'; }
    document.getElementById('btn-quest-stop').disabled = true;
    showToast('Da dung auto quest', 'info');
  } catch(e) { showToast('Loi dung quest', 'error'); }
}

// ============================================================
// HYPESQUAD
// ============================================================

async function handleClaimHypeSquad(house) {
  const names = {1:'Bravery', 2:'Brilliance', 3:'Balance'};
  showToast(`Dang nhan HypeSquad ${names[house]}...`, 'info', 2000);
  try {
    const r = await fetch('/api/hypesquad/claim', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({house_id: house})
    });
    const d = await r.json();
    if (d.success) showToast(`Da nhan Huy Hieu ${names[house]}!`, 'success');
    else showToast(d.error || 'Nhan huy hieu that bai', 'error');
  } catch(e) { showToast('Loi ket noi', 'error'); }
}

// Fix typo in HTML for balance button
function handleClaimHypeQuad(house) { handleClaimHypeSquad(house); }

// ============================================================
// INIT
async function loadSavedConfig() {
  try {
    const r = await fetch('/api/get_config');
    const d = await r.json();
    if (d.success && d.config) {
      const c = d.config;
      const set = (elId, val) => { const e = document.getElementById(elId); if (e && val !== undefined && val !== null) e.value = val; };
      if (c.name) set('input-activity-name', c.name);
      if (c.details !== undefined) set('input-details', c.details);
      if (c.state !== undefined) set('input-state', c.state);
      if (c.large_image) set('input-large-image', c.large_image);
      if (c.small_image) set('input-small-image', c.small_image);
      if (c.large_text !== undefined) set('input-large-text', c.large_text);
      if (c.small_text !== undefined) set('input-small-text', c.small_text);
      if (c.buttons?.[0]) {
        set('input-btn1-label', c.buttons[0].label || '');
        set('input-btn1-url', c.buttons[0].url || '');
      }
      if (c.buttons?.[1]) {
        set('input-btn2-label', c.buttons[1].label || '');
        set('input-btn2-url', c.buttons[1].url || '');
      }
      if (c.activity_type) set('select-activity-type', c.activity_type);
      if (c.app_id) set('input-app-id', c.app_id);
      if (c.user_status) set('select-user-status', c.user_status);
      const ts = document.getElementById('check-timestamp');
      if (ts && c.use_timestamp !== undefined) ts.checked = !!c.use_timestamp;

      if (c.large_image) onManualImageChange('large');
      if (c.small_image) {
        onManualImageChange('small');
      } else {
        clearSmallImage();
      }
      updateLivePreview();
    }
  } catch(e) {}
}

function init() {
  buildVisualGallery();
  loadPresets();
  onActivityTypeChange();
  updateLivePreview();
  initSCWidget();
  handleSelectLyricTrack();
  loadAvailableQuests();
  startLogPolling();
  loadSavedConfig();
}

document.addEventListener('DOMContentLoaded', init);
