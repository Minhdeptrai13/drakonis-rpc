const DEFAULT_PRESETS = [
  {
    id: 'preset-vscode',
    name: 'VS Code Coding',
    isDefault: true,
    config: {
      activityType: 'playing',
      activityName: 'Visual Studio Code',
      details: 'Developing Discord RPC Master',
      state: 'Workspace: DiscordRPG (Python)',
      largeImage: 'bot_avatar',
      largeText: 'Visual Studio Code',
      smallImage: 'python',
      smallText: 'Python 3.12',
      hasTimestamp: true,
      btn1Label: 'GitHub Project',
      btn1Url: 'https://github.com',
      btn2Label: 'Join Server',
      btn2Url: 'https://discord.gg'
    }
  },
  {
    id: 'preset-valorant',
    name: 'Valorant Radiant',
    isDefault: true,
    config: {
      activityType: 'competing',
      activityName: 'VALORANT',
      details: 'Competitive - Haven',
      state: 'Rank: Radiant (Top 50)',
      largeImage: 'bot_avatar',
      largeText: 'Match Score: 12 - 11',
      smallImage: 'git',
      smallText: 'Radiant #24',
      hasTimestamp: true,
      btn1Label: 'Tracker.gg Stats',
      btn1Url: 'https://tracker.gg',
      btn2Label: 'Watch VOD',
      btn2Url: 'https://youtube.com'
    }
  },
  {
    id: 'preset-stream',
    name: 'Twitch Streaming',
    isDefault: true,
    config: {
      activityType: 'streaming',
      streamUrl: 'https://twitch.tv/discord',
      activityName: 'Late Night Chill & Code',
      details: 'Building Discord RPC Bot in Python',
      state: 'Chatting with viewers (1,240 live)',
      largeImage: 'bot_avatar',
      largeText: '1080p 60fps',
      smallImage: 'python',
      smallText: 'Verified Partner',
      hasTimestamp: true,
      btn1Label: 'Kênh Twitch',
      btn1Url: 'https://twitch.tv',
      btn2Label: 'Donate / Ung Ho',
      btn2Url: 'https://twitch.tv'
    }
  },
  {
    id: 'preset-chill',
    name: 'Lofi Chill Beats',
    isDefault: true,
    config: {
      activityType: 'listening',
      activityName: 'Lofi Girl - Synthwave Radio',
      details: 'Chill Beats to Relax/Study to',
      state: 'Track: Sunset Boulevard',
      largeImage: 'bot_avatar',
      largeText: 'Lofi Girl Live',
      smallImage: 'python',
      smallText: 'Relaxing',
      hasTimestamp: true,
      btn1Label: 'Listen on YouTube',
      btn1Url: 'https://youtube.com',
      btn2Label: 'Spotify Playlist',
      btn2Url: 'https://spotify.com'
    }
  }
];

const KNOWN_ASSET_ICONS = {
  vscode: 'https://cdn.discordapp.com/app-assets/383226320970055681/1359299466493956258.png',
  python: 'https://cdn.discordapp.com/app-assets/383226320970055681/1359299282380918886.png',
  git: 'https://cdn.discordapp.com/app-assets/383226320970055681/1359298453284323538.png',
  docker: 'https://cdn.discordapp.com/app-assets/383226320970055681/1359298813092823040.png',
  js: 'https://cdn.discordapp.com/app-assets/383226320970055681/1359299016025964687.png',
  ts: 'https://cdn.discordapp.com/app-assets/383226320970055681/1359299427059236984.png',
  jsx: 'https://cdn.discordapp.com/app-assets/383226320970055681/1359299015983894651.png',
  tsx: 'https://cdn.discordapp.com/app-assets/383226320970055681/1359299426262319284.png',
  cpp: 'https://cdn.discordapp.com/app-assets/383226320970055681/1359298399379390484.png',
  csharp: 'https://cdn.discordapp.com/app-assets/383226320970055681/1359298403259121674.png',
  java: 'https://cdn.discordapp.com/app-assets/383226320970055681/1359298971738050570.png',
  html: 'https://cdn.discordapp.com/app-assets/383226320970055681/1359298971646038066.png',
  css: 'https://cdn.discordapp.com/app-assets/383226320970055681/1359298399085527152.png',
  rust: 'https://cdn.discordapp.com/app-assets/383226320970055681/1359299338907549887.png',
  go: 'https://cdn.discordapp.com/app-assets/383226320970055681/1359298884043800586.png',
  react: 'https://cdn.discordapp.com/app-assets/383226320970055681/1359299015983894651.png',
  vue: 'https://cdn.discordapp.com/app-assets/383226320970055681/1359299519573131545.png',
  tailwind: 'https://cdn.discordapp.com/app-assets/383226320970055681/1359299371597824070.png'
};

let detectedAppAvatarUrl = null;
let userPresets = [];
let isRpcRunning = false;
let rpcStatusCurrent = 'stopped';
let statusPollingInterval = null;
let logPollingInterval = null;
let liveTimerInterval = null;
let elapsedSeconds = 0;
let rotatorTimer = null;
let currentRotatorIndex = 0;
const CONFIG_STORAGE_KEY = 'drakonis_rpc_saved_config';
let faviconCanvas = null;
let faviconCtx = null;
let faviconAnimAngle = 0;
let tabAnimInterval = null;
let titleTickerStep = 0;
let questPollingInterval = null;

document.addEventListener('DOMContentLoaded', () => {
  setupLivePreviewListeners();
  checkAccountLinkStatus();
  loadSavedToken();
  loadPresets();
  loadFormDraft();
  renderVisualGallery();
  renderPortalBotsGrid();
  loadAvailableQuests();
  initLyricModule();
  updateLivePreview();
  startLivePreviewTimer();
  initTabAnimation();
  pollStatus();
  fetchLogs(false);

  statusPollingInterval = setInterval(pollStatus, 3000);
  questPollingInterval = setInterval(pollQuestStatus, 2500);
});

const SPLIT_TABS = ['tab-home', 'tab-content', 'tab-images', 'tab-buttons', 'tab-quest', 'tab-lyric', 'tab-account', 'tab-logs'];
const FULL_TABS = ['tab-guide', 'tab-about'];

function switchMainTab(tabId) {
  document.querySelectorAll('.nav-tab-link').forEach(btn => {
    if (btn.getAttribute('data-tab') === tabId) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });

  const splitGrid = document.getElementById('main-split-grid');

  if (SPLIT_TABS.includes(tabId)) {
    if (splitGrid) splitGrid.classList.remove('d-none');

    FULL_TABS.forEach(id => {
      const el = document.getElementById(id);
      if (el) el.classList.remove('active');
    });

    SPLIT_TABS.forEach(id => {
      const el = document.getElementById(id);
      if (el) {
        if (id === tabId) el.classList.add('active');
        else el.classList.remove('active');
      }
    });
  } else {
    if (splitGrid) splitGrid.classList.add('d-none');

    SPLIT_TABS.forEach(id => {
      const el = document.getElementById(id);
      if (el) el.classList.remove('active');
    });

    FULL_TABS.forEach(id => {
      const el = document.getElementById(id);
      if (el) {
        if (id === tabId) el.classList.add('active');
        else el.classList.remove('active');
      }
    });

    if (tabId === 'tab-logs') {
      fetchLogs(true);
    }
  }
}

async function fetchLogs(scrollBottom = false) {
  try {
    const res = await fetch('/api/logs');
    if (!res.ok) return;
    const data = await res.json();
    if (!data.success || !Array.isArray(data.logs)) return;

    const termScreen = document.getElementById('terminal-screen');
    const fullViewport = document.getElementById('full-terminal-viewport');

    let html = '';
    if (data.logs.length === 0) {
      html = `
        <div class="log-line info">
          <span class="log-time">[00:00:00]</span>
          <span class="log-tag">[SYSTEM]</span>
          <span class="log-msg">Hệ thống sẵn sàng. Bấm "Khởi Chạy" để bắt đầu kết nối...</span>
        </div>
      `;
    } else {
      data.logs.forEach(item => {
        const lvl = escapeHtml(item.level || 'info');
        const time = escapeHtml(item.timestamp || '00:00:00');
        const msg = escapeHtml(item.message || '');
        html += `
          <div class="log-line ${lvl}">
            <span class="log-time">[${time}]</span>
            <span class="log-tag">[${lvl.toUpperCase()}]</span>
            <span class="log-msg">${msg}</span>
          </div>
        `;
      });
    }

    if (termScreen) {
      termScreen.innerHTML = html;
      if (scrollBottom) termScreen.scrollTop = termScreen.scrollHeight;
    }
    if (fullViewport) {
      fullViewport.innerHTML = html;
      if (scrollBottom) fullViewport.scrollTop = fullViewport.scrollHeight;
    }
  } catch (err) {
    console.warn('Lỗi khi tải log:', err);
  }
}

async function clearLogs() {
  try {
    const res = await fetch('/api/logs', { method: 'DELETE' });
    if (res.ok) {
      const emptyHtml = `
        <div class="log-line info">
          <span class="log-time">[SYSTEM]</span>
          <span class="log-tag">[INFO]</span>
          <span class="log-msg">Đã xóa sạch nhật ký sự kiện.</span>
        </div>
      `;
      const termScreen = document.getElementById('terminal-screen');
      const fullViewport = document.getElementById('full-terminal-viewport');
      if (termScreen) termScreen.innerHTML = emptyHtml;
      if (fullViewport) fullViewport.innerHTML = emptyHtml;
      showToast('Đã xóa sạch nhật ký hệ thống!', 'info');
    }
  } catch (err) {
    showToast('Lỗi khi xóa log: ' + err.message, 'error');
  }
}

function startStartupLogPolling(durationMs = 12000) {
  if (logPollingInterval) clearInterval(logPollingInterval);
  fetchLogs(true);
  logPollingInterval = setInterval(() => {
    fetchLogs(true);
  }, 750);
  setTimeout(() => {
    if (logPollingInterval) {
      clearInterval(logPollingInterval);
      logPollingInterval = null;
    }
  }, durationMs);
}

function resolvePreviewUrl(val) {
  if (!val) return '';
  const trimmed = val.trim();
  const lower = trimmed.toLowerCase();

  if (lower === 'bot_avatar' || lower === 'portal' || lower === 'bot' || lower === 'app' || lower === 'default') {
    if (detectedAppAvatarUrl) {
      return detectedAppAvatarUrl;
    }
    const lastUpload = localStorage.getItem('last_uploaded_preview_url');
    if (lastUpload) {
      return lastUpload;
    }
    return '/static/uploads/b6892ebe383640c596013c353ec3dabd.jpeg';
  }

  if (KNOWN_ASSET_ICONS[lower]) {
    return KNOWN_ASSET_ICONS[lower];
  }
  return trimmed;
}

function setAsset(target, key) {
  const inputId = target === 'large' ? 'input-large-image' : 'input-small-image';
  const el = document.getElementById(inputId);
  if (el) {
    el.value = key;
    updateLivePreview();
    if (isRpcRunning) {
      handleUpdateRPC();
    }
  }
}

function saveFormDraft(notify = false) {
  try {
    const cfg = getCurrentFormConfig();
    localStorage.setItem(CONFIG_STORAGE_KEY, JSON.stringify(cfg));
    if (notify) {
      showToast('Đã lưu cấu hình thành công! Toàn bộ nội dung sẽ được giữ nguyên.', 'success');
    }
  } catch (e) {
    if (notify) {
      showToast('Lỗi khi lưu cấu hình trình duyệt: ' + e.message, 'error');
    }
  }
}

function handleSaveConfig() {
  saveFormDraft(true);
}

function loadFormDraft() {
  try {
    const raw = localStorage.getItem(CONFIG_STORAGE_KEY);
    if (!raw) return;
    const cfg = JSON.parse(raw);
    if (cfg && typeof cfg === 'object') {
      applyConfigToForm(cfg);
    }
  } catch (e) {
  }
}

function initTabAnimation() {
  faviconCanvas = document.createElement('canvas');
  faviconCanvas.width = 32;
  faviconCanvas.height = 32;
  faviconCtx = faviconCanvas.getContext('2d');
  if (tabAnimInterval) clearInterval(tabAnimInterval);
  tabAnimInterval = setInterval(renderTabTick, 90);
}

function renderTabTick() {
  faviconAnimAngle = (faviconAnimAngle + 0.14) % (Math.PI * 2);
  titleTickerStep++;

  if (faviconCtx) {
    faviconCtx.clearRect(0, 0, 32, 32);

    faviconCtx.beginPath();
    faviconCtx.arc(16, 16, 15, 0, Math.PI * 2);
    faviconCtx.fillStyle = '#0a0d14';
    faviconCtx.fill();
    faviconCtx.lineWidth = 1.5;
    faviconCtx.strokeStyle = 'rgba(255,255,255,0.12)';
    faviconCtx.stroke();

    if (rpcStatusCurrent === 'running') {
      faviconCtx.beginPath();
      faviconCtx.arc(16, 16, 11, faviconAnimAngle, faviconAnimAngle + 1.6);
      faviconCtx.strokeStyle = '#10b981';
      faviconCtx.lineWidth = 2.5;
      faviconCtx.lineCap = 'round';
      faviconCtx.stroke();

      const pulse = 4 + Math.sin(faviconAnimAngle * 2) * 1.5;
      faviconCtx.beginPath();
      faviconCtx.arc(16, 16, pulse, 0, Math.PI * 2);
      faviconCtx.fillStyle = '#34d399';
      faviconCtx.fill();
    } else if (rpcStatusCurrent === 'connecting' || rpcStatusCurrent === 'stopping') {
      faviconCtx.beginPath();
      faviconCtx.arc(16, 16, 11, faviconAnimAngle, faviconAnimAngle + 2.4);
      faviconCtx.strokeStyle = '#f59e0b';
      faviconCtx.lineWidth = 2.5;
      faviconCtx.lineCap = 'round';
      faviconCtx.stroke();

      faviconCtx.beginPath();
      faviconCtx.arc(16, 16, 4, 0, Math.PI * 2);
      faviconCtx.fillStyle = '#fbbf24';
      faviconCtx.fill();
    } else {
      faviconCtx.beginPath();
      faviconCtx.arc(16, 16, 11, faviconAnimAngle, faviconAnimAngle + 1.2);
      faviconCtx.strokeStyle = '#6366f1';
      faviconCtx.lineWidth = 2;
      faviconCtx.lineCap = 'round';
      faviconCtx.stroke();

      const pulse = 3.5 + Math.sin(faviconAnimAngle) * 1.2;
      faviconCtx.beginPath();
      faviconCtx.arc(16, 16, pulse, 0, Math.PI * 2);
      faviconCtx.fillStyle = '#a855f7';
      faviconCtx.fill();
    }

    const favEl = document.getElementById('app-favicon');
    if (favEl) {
      favEl.href = faviconCanvas.toDataURL('image/png');
    }
  }

  if (titleTickerStep % 15 === 0) {
    const actName = (document.getElementById('input-activity-name') ? document.getElementById('input-activity-name').value.trim() : '') || 'Drakonis';
    if (rpcStatusCurrent === 'running') {
      const liveIndicators = ['● LIVE', '✦ RUNNING', '▶ ACTIVE'];
      const ind = liveIndicators[Math.floor(titleTickerStep / 15) % liveIndicators.length];
      document.title = `${ind} | ${actName} - Drakonis RPC`;
    } else if (rpcStatusCurrent === 'connecting') {
      const waitDots = ['·', '··', '···'];
      const dot = waitDots[Math.floor(titleTickerStep / 15) % waitDots.length];
      document.title = `Connecting${dot} | Drakonis RPC`;
    } else {
      const idleHeaders = ['Drakonis RPC v2.5', 'Drakonis Rich Presence', 'Drakonis Master'];
      const header = idleHeaders[Math.floor(titleTickerStep / 25) % idleHeaders.length];
      document.title = `${header}`;
    }
  }
}

function setupLivePreviewListeners() {
  const inputsToWatch = [
    'select-activity-type',
    'select-user-status',
    'input-stream-url',
    'input-activity-name',
    'input-details',
    'input-state',
    'input-large-image',
    'input-large-text',
    'input-small-image',
    'input-small-text',
    'input-btn1-label',
    'input-btn1-url',
    'input-btn2-label',
    'input-btn2-url',
    'input-app-id',
    'check-auto-app',
    'check-timestamp'
  ];

  inputsToWatch.forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener('input', () => {
        updateLivePreview();
        saveFormDraft(false);
      });
      el.addEventListener('change', () => {
        updateLivePreview();
        saveFormDraft(false);
      });
    }
  });

  const tokenInput = document.getElementById('input-token');
  if (tokenInput) {
    tokenInput.addEventListener('input', () => {
      localStorage.setItem('discord_rpc_user_token', tokenInput.value.trim());
      saveFormDraft(false);
    });
  }

  document.querySelectorAll('.action-save').forEach(btn => {
    btn.addEventListener('click', handleSaveConfig);
  });
}

function loadSavedToken() {
  const savedToken = localStorage.getItem('discord_rpc_user_token');
  const tokenInput = document.getElementById('input-token');
  if (savedToken && tokenInput && !tokenInput.value) {
    tokenInput.value = savedToken;
    setTimeout(() => {
      scanPortalApps(false);
    }, 400);
  }
}

function toggleTokenVisibility() {
  const tokenInput = document.getElementById('input-token');
  const toggleLabel = document.getElementById('token-toggle-label');
  if (tokenInput.type === 'password') {
    tokenInput.type = 'text';
    toggleLabel.innerText = 'Ẩn Token';
  } else {
    tokenInput.type = 'password';
    toggleLabel.innerText = 'Hiện Token';
  }
}

function onActivityTypeChange() {
  const type = document.getElementById('select-activity-type').value;
  const streamGroup = document.getElementById('stream-url-group');
  if (streamGroup) {
    if (type === 'streaming') {
      streamGroup.classList.remove('d-none');
    } else {
      streamGroup.classList.add('d-none');
    }
  }
  updateLivePreview();
}

function updateLivePreview() {
  const typeEl = document.getElementById('select-activity-type');
  const type = typeEl ? typeEl.value : 'playing';
  const userStatus = document.getElementById('select-user-status') ? document.getElementById('select-user-status').value : 'online';
  const actName = (document.getElementById('input-activity-name') ? document.getElementById('input-activity-name').value.trim() : '') || 'Visual Studio Code';
  const details = document.getElementById('input-details') ? document.getElementById('input-details').value.trim() : '';
  const state = document.getElementById('input-state') ? document.getElementById('input-state').value.trim() : '';
  const largeImg = document.getElementById('input-large-image') ? document.getElementById('input-large-image').value.trim() : '';
  const smallImg = document.getElementById('input-small-image') ? document.getElementById('input-small-image').value.trim() : '';
  const hasTimestamp = document.getElementById('check-timestamp') ? document.getElementById('check-timestamp').checked : true;

  const btn1Label = document.getElementById('input-btn1-label') ? document.getElementById('input-btn1-label').value.trim() : '';
  const btn1Url = document.getElementById('input-btn1-url') ? document.getElementById('input-btn1-url').value.trim() : '';
  const btn2Label = document.getElementById('input-btn2-label') ? document.getElementById('input-btn2-label').value.trim() : '';
  const btn2Url = document.getElementById('input-btn2-url') ? document.getElementById('input-btn2-url').value.trim() : '';

  const headerEl = document.getElementById('pv-activity-type-header');
  const statusDot = document.getElementById('pv-status-dot');

  if (headerEl) {
    switch (type) {
      case 'playing':
        headerEl.innerText = 'PLAYING A GAME';
        break;
      case 'streaming':
        headerEl.innerText = 'STREAMING ON TWITCH';
        break;
      case 'listening':
        headerEl.innerText = 'LISTENING TO';
        break;
      case 'watching':
        headerEl.innerText = 'WATCHING';
        break;
      case 'competing':
        headerEl.innerText = 'COMPETING IN';
        break;
      default:
        headerEl.innerText = 'PLAYING A GAME';
    }
  }

  if (statusDot) {
    if (type === 'streaming') {
      statusDot.className = 'status-badge-dot streaming';
    } else if (userStatus === 'idle') {
      statusDot.className = 'status-badge-dot idle';
    } else if (userStatus === 'dnd') {
      statusDot.className = 'status-badge-dot dnd';
    } else {
      statusDot.className = 'status-badge-dot';
    }
  }

  const actNameEl = document.getElementById('pv-activity-name');
  if (actNameEl) actNameEl.innerText = actName;
  
  const detailsEl = document.getElementById('pv-details');
  if (detailsEl) {
    if (details) {
      detailsEl.innerText = details;
      detailsEl.style.display = 'block';
    } else {
      detailsEl.style.display = 'none';
    }
  }

  const stateEl = document.getElementById('pv-state');
  if (stateEl) {
    if (state) {
      stateEl.innerText = state;
      stateEl.style.display = 'block';
    } else {
      stateEl.style.display = 'none';
    }
  }

  const resolvedLarge = resolvePreviewUrl(largeImg);
  const largeImgEl = document.getElementById('pv-large-img');
  if (largeImgEl) {
    if (resolvedLarge) {
      largeImgEl.src = resolvedLarge;
      largeImgEl.style.display = 'block';
      largeImgEl.onerror = () => {
        largeImgEl.src = 'https://cdn.discordapp.com/embed/avatars/1.png';
      };
    } else {
      largeImgEl.src = 'https://cdn.discordapp.com/embed/avatars/1.png';
    }
  }

  const resolvedSmall = resolvePreviewUrl(smallImg);
  const smallImgEl = document.getElementById('pv-small-img');
  if (smallImgEl) {
    if (resolvedSmall) {
      smallImgEl.src = resolvedSmall;
      smallImgEl.style.display = 'block';
      smallImgEl.onerror = () => {
        smallImgEl.style.display = 'none';
      };
    } else {
      smallImgEl.style.display = 'none';
    }
  }

  const timeEl = document.getElementById('pv-time');
  if (timeEl) {
    timeEl.style.display = hasTimestamp ? 'flex' : 'none';
  }

  const btn1El = document.getElementById('pv-btn1');
  const btn2El = document.getElementById('pv-btn2');

  if (btn1El) {
    if (btn1Label) {
      btn1El.innerText = btn1Label;
      btn1El.href = btn1Url || '#';
      btn1El.style.display = 'block';
    } else {
      btn1El.style.display = 'none';
    }
  }

  if (btn2El) {
    if (btn2Label) {
      btn2El.innerText = btn2Label;
      btn2El.href = btn2Url || '#';
      btn2El.style.display = 'block';
    } else {
      btn2El.style.display = 'none';
    }
  }

  updateVisualImageBoxes();
}

function updateVisualImageBoxes() {
  const largeEl = document.getElementById('input-large-image');
  const largeImgVal = (largeEl && largeEl.value) ? largeEl.value.trim() : '';
  const smallEl = document.getElementById('input-small-image');
  const smallImgVal = (smallEl && smallEl.value) ? smallEl.value.trim() : '';

  const boxLarge = document.getElementById('box-large-preview');
  const lblLarge = document.getElementById('lbl-large-source');
  const resolvedLarge = resolvePreviewUrl(largeImgVal);

  if (boxLarge) {
    boxLarge.src = resolvedLarge || 'https://cdn.discordapp.com/embed/avatars/0.png';
  }

  if (lblLarge) {
    const lower = largeImgVal.toLowerCase();
    if (lower === 'bot_avatar' || lower === 'portal' || lower === 'bot') {
      lblLarge.innerText = 'Avatar Anime Girl (Bot Portal)';
    } else if (KNOWN_ASSET_ICONS[lower]) {
      lblLarge.innerText = `Logo ${largeImgVal.toUpperCase()}`;
    } else if (largeImgVal.includes('/uploads/')) {
      lblLarge.innerText = 'Ảnh tải lên từ máy';
    } else if (largeImgVal) {
      lblLarge.innerText = 'Ảnh tùy chỉnh Discord';
    } else {
      lblLarge.innerText = 'Chưa chọn ảnh lớn';
    }
  }

  const boxSmall = document.getElementById('box-small-preview');
  const lblSmall = document.getElementById('lbl-small-source');
  const resolvedSmall = resolvePreviewUrl(smallImgVal);

  if (boxSmall) {
    if (resolvedSmall) {
      boxSmall.src = resolvedSmall;
      boxSmall.style.display = 'block';
    } else {
      boxSmall.style.display = 'none';
    }
  }

  if (lblSmall) {
    const lower = smallImgVal.toLowerCase();
    if (!smallImgVal) {
      lblSmall.innerText = 'Không dùng (Đã gỡ)';
    } else if (KNOWN_ASSET_ICONS[lower]) {
      lblSmall.innerText = `Biểu tượng ${smallImgVal.toUpperCase()}`;
    } else if (smallImgVal.includes('/uploads/')) {
      lblSmall.innerText = 'Ảnh tải lên từ máy';
    } else {
      lblSmall.innerText = 'Biểu tượng tùy chỉnh';
    }
  }
}

function startLivePreviewTimer() {
  if (liveTimerInterval) clearInterval(liveTimerInterval);
  liveTimerInterval = setInterval(() => {
    elapsedSeconds++;
    const hrs = String(Math.floor(elapsedSeconds / 3600)).padStart(2, '0');
    const mins = String(Math.floor((elapsedSeconds % 3600) / 60)).padStart(2, '0');
    const secs = String(elapsedSeconds % 60).padStart(2, '0');
    
    const timerText = document.getElementById('pv-timer-text');
    if (timerText) {
      if (hrs > 0) {
        timerText.innerText = `${hrs}:${mins}:${secs} elapsed`;
      } else {
        timerText.innerText = `${mins}:${secs} elapsed`;
      }
    }
  }, 1000);
}

function triggerUpload(target) {
  const fileInput = document.getElementById(`file-upload-${target}`);
  if (fileInput) fileInput.click();
}

async function uploadImageFile(input, target) {
  if (!input.files || input.files.length === 0) return;
  const file = input.files[0];

  const reader = new FileReader();
  reader.onload = (e) => {
    const previewEl = document.getElementById(`pv-${target}-img`);
    if (previewEl) {
      previewEl.src = e.target.result;
      previewEl.style.display = 'block';
    }
  };
  reader.readAsDataURL(file);

  showToast(`Đang tải ảnh "${file.name}"...`, 'info');

  const formData = new FormData();
  formData.append('image', file);

  try {
    const response = await fetch('/api/upload', {
      method: 'POST',
      body: formData
    });
    const data = await response.json();

    if (response.ok && data.success) {
      const urlInput = document.getElementById(`input-${target}-image`);
      if (urlInput) {
        urlInput.value = data.url;
        localStorage.setItem('last_uploaded_preview_url', data.url);
        if (target === 'large') {
          detectedAppAvatarUrl = data.url;
        }
        updateLivePreview();
        showToast('Đã lưu ảnh thành công!', 'success');

        if (isRpcRunning) {
          handleUpdateRPC();
        }
      }
    } else {
      showToast(`Lỗi tải ảnh: ${data.message || 'Không xác định'}`, 'error');
    }
  } catch (err) {
    showToast(`Lỗi kết nối khi tải ảnh: ${err.message}`, 'error');
  } finally {
    input.value = '';
  }
}

function getCurrentFormConfig() {
  const autoAppCheckbox = document.getElementById('check-auto-app');
  const autoApp = autoAppCheckbox ? autoAppCheckbox.checked : true;
  return {
    token: document.getElementById('input-token').value.trim(),
    autoApp: autoApp,
    appId: document.getElementById('input-app-id').value.trim() || '1546849576986607657',
    activityType: document.getElementById('select-activity-type').value,
    userStatus: document.getElementById('select-user-status') ? document.getElementById('select-user-status').value : 'online',
    streamUrl: document.getElementById('input-stream-url') ? document.getElementById('input-stream-url').value.trim() : '',
    activityName: document.getElementById('input-activity-name').value.trim() || 'Visual Studio Code',
    details: document.getElementById('input-details').value.trim(),
    state: document.getElementById('input-state').value.trim(),
    largeImage: document.getElementById('input-large-image').value.trim(),
    largeText: document.getElementById('input-large-text').value.trim(),
    smallImage: document.getElementById('input-small-image').value.trim(),
    smallText: document.getElementById('input-small-text').value.trim(),
    hasTimestamp: document.getElementById('check-timestamp').checked,
    btn1Label: document.getElementById('input-btn1-label').value.trim(),
    btn1Url: document.getElementById('input-btn1-url').value.trim(),
    btn2Label: document.getElementById('input-btn2-label').value.trim(),
    btn2Url: document.getElementById('input-btn2-url').value.trim()
  };
}

function applyConfigToForm(cfg) {
  if (!cfg) return;
  if (cfg.autoApp !== undefined && document.getElementById('check-auto-app')) {
    document.getElementById('check-auto-app').checked = cfg.autoApp;
  }
  if (cfg.appId !== undefined && document.getElementById('input-app-id')) {
    document.getElementById('input-app-id').value = cfg.appId;
  }
  if (cfg.activityType) document.getElementById('select-activity-type').value = cfg.activityType;
  if (cfg.userStatus && document.getElementById('select-user-status')) document.getElementById('select-user-status').value = cfg.userStatus;
  if (cfg.streamUrl !== undefined && document.getElementById('input-stream-url')) document.getElementById('input-stream-url').value = cfg.streamUrl;
  if (cfg.activityName !== undefined) document.getElementById('input-activity-name').value = cfg.activityName;
  if (cfg.details !== undefined) document.getElementById('input-details').value = cfg.details;
  if (cfg.state !== undefined) document.getElementById('input-state').value = cfg.state;
  if (cfg.largeImage !== undefined) document.getElementById('input-large-image').value = cfg.largeImage;
  if (cfg.largeText !== undefined) document.getElementById('input-large-text').value = cfg.largeText;
  if (cfg.smallImage !== undefined) document.getElementById('input-small-image').value = cfg.smallImage;
  if (cfg.smallText !== undefined) document.getElementById('input-small-text').value = cfg.smallText;
  if (cfg.hasTimestamp !== undefined) document.getElementById('check-timestamp').checked = cfg.hasTimestamp;
  if (cfg.btn1Label !== undefined) document.getElementById('input-btn1-label').value = cfg.btn1Label;
  if (cfg.btn1Url !== undefined) document.getElementById('input-btn1-url').value = cfg.btn1Url;
  if (cfg.btn2Label !== undefined) document.getElementById('input-btn2-label').value = cfg.btn2Label;
  if (cfg.btn2Url !== undefined) document.getElementById('input-btn2-url').value = cfg.btn2Url;
  onActivityTypeChange();
  updateLivePreview();
  saveFormDraft(false);
}

async function handleStartRPC() {
  const config = getCurrentFormConfig();
  if (!config.token) {
    showToast('Vui lòng nhập Discord User Token!', 'error');
    switchMainTab('tab-account');
    const tokenInput = document.getElementById('input-token');
    if (tokenInput) tokenInput.focus();
    return;
  }
  if (!config.activityName) {
    showToast('Vui lòng nhập tên hoạt động / ứng dụng!', 'error');
    switchMainTab('tab-content');
    const actInput = document.getElementById('input-activity-name');
    if (actInput) actInput.focus();
    return;
  }

  setConnectingState();
  showToast('Đang kết nối tới Discord Gateway...', 'info');
  startStartupLogPolling(15000);

  try {
    const res = await fetch('/api/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config)
    });
    const data = await res.json();

    if (res.ok && data.success) {
      showToast(data.message || 'Đã gửi lệnh khởi chạy RPC!', 'success');
      pollStatus();
      fetchLogs(true);
    } else {
      showToast(`Không thể khởi chạy: ${data.message || 'Lỗi không xác định'}`, 'error');
      setStoppedState();
      fetchLogs(true);
    }
  } catch (err) {
    showToast(`Lỗi kết nối máy chủ Flask: ${err.message}`, 'error');
    setStoppedState();
  }
}

async function handleUpdateRPC() {
  const config = getCurrentFormConfig();
  if (!config.activityName) {
    showToast('Vui lòng nhập tên hoạt động / ứng dụng!', 'error');
    switchMainTab('tab-content');
    const actInput = document.getElementById('input-activity-name');
    if (actInput) actInput.focus();
    return;
  }

  showToast('Đang cập nhật trạng thái Discord...', 'info');
  startStartupLogPolling(8000);

  try {
    const res = await fetch('/api/update', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config)
    });
    const data = await res.json();

    if (res.ok && data.success) {
      showToast('Đã cập nhật trạng thái Discord thành công!', 'success');
      pollStatus();
      fetchLogs(true);
    } else {
      showToast(`Lỗi cập nhật: ${data.message || 'Không xác định'}`, 'error');
      fetchLogs(true);
    }
  } catch (err) {
    showToast(`Lỗi kết nối khi cập nhật: ${err.message}`, 'error');
  }
}

async function handleStopRPC() {
  showToast('Đang ngắt kết nối và giải phóng trạng thái...', 'info');
  setStoppingState();

  try {
    const res = await fetch('/api/stop', { method: 'POST' });
    const data = await res.json();

    if (res.ok && data.success) {
      showToast('Đã dừng Discord RPC thành công!', 'success');
      setStoppedState();
      pollStatus();
      fetchLogs(true);
    } else {
      showToast(`Lỗi khi dừng RPC: ${data.message || 'Không xác định'}`, 'error');
      setStoppedState();
    }
  } catch (err) {
    showToast(`Lỗi: ${err.message}`, 'error');
    setStoppedState();
  }
}

async function pollStatus() {
  try {
    const res = await fetch('/api/status');
    if (!res.ok) return;
    const data = await res.json();

    if (data.status === 'running') {
      setRunningState(data.user_tag);
    } else if (data.status === 'connecting') {
      setConnectingState();
    } else if (data.status === 'stopping') {
      setStoppingState();
    } else {
      setStoppedState(data.error_message);
    }
  } catch (e) {
  }
}

function setRunningState(userTag) {
  isRpcRunning = true;
  rpcStatusCurrent = 'running';
  const led = document.getElementById('led-indicator');
  const text = document.getElementById('status-text');

  if (led) led.className = 'status-led running';
  if (text) text.innerText = userTag ? `Đang phát (${userTag})` : 'Đang phát trạng thái';

  document.querySelectorAll('.action-start').forEach(btn => {
    btn.disabled = true;
    btn.innerText = 'Đang Chạy';
  });
  document.querySelectorAll('.action-update').forEach(btn => {
    btn.disabled = false;
  });
  document.querySelectorAll('.action-stop').forEach(btn => {
    btn.disabled = false;
    btn.innerText = 'Dừng Lại';
  });
}

function setConnectingState() {
  rpcStatusCurrent = 'connecting';
  const led = document.getElementById('led-indicator');
  const text = document.getElementById('status-text');

  if (led) led.className = 'status-led connecting';
  if (text) text.innerText = 'Đang kết nối...';

  document.querySelectorAll('.action-start').forEach(btn => {
    btn.disabled = true;
    btn.innerText = 'Đang Kết Nối...';
  });
  document.querySelectorAll('.action-update').forEach(btn => {
    btn.disabled = true;
  });
  document.querySelectorAll('.action-stop').forEach(btn => {
    btn.disabled = false;
    btn.innerText = 'Dừng Lại';
  });
}

function setStoppingState() {
  isRpcRunning = false;
  rpcStatusCurrent = 'stopping';
  const led = document.getElementById('led-indicator');
  const text = document.getElementById('status-text');

  if (led) led.className = 'status-led connecting';
  if (text) text.innerText = 'Đang dừng...';

  document.querySelectorAll('.action-start').forEach(btn => {
    btn.disabled = true;
    btn.innerText = 'Khởi Chạy';
  });
  document.querySelectorAll('.action-update').forEach(btn => {
    btn.disabled = true;
  });
  document.querySelectorAll('.action-stop').forEach(btn => {
    btn.disabled = true;
    btn.innerText = 'Đang Dừng...';
  });
}

function setStoppedState(errorMsg = null) {
  isRpcRunning = false;
  rpcStatusCurrent = 'stopped';
  const led = document.getElementById('led-indicator');
  const text = document.getElementById('status-text');

  if (led) led.className = 'status-led';
  if (text) text.innerText = errorMsg ? `Lỗi: ${errorMsg}` : 'Đã dừng';

  document.querySelectorAll('.action-start').forEach(btn => {
    btn.disabled = false;
    btn.innerText = 'Khởi Chạy';
  });
  document.querySelectorAll('.action-update').forEach(btn => {
    btn.disabled = true;
  });
  document.querySelectorAll('.action-stop').forEach(btn => {
    btn.disabled = true;
    btn.innerText = 'Dừng Lại';
  });
}

async function loadPresets() {
  try {
    const res = await fetch('/api/presets');
    if (res.ok) {
      const data = await res.json();
      userPresets = data.presets || [];
    }
  } catch (e) {
    userPresets = [];
  }
  renderPresetChips();
}

function renderPresetChips() {
  const container = document.getElementById('preset-list');
  if (!container) return;
  container.innerHTML = '';

  DEFAULT_PRESETS.forEach(p => {
    const chip = document.createElement('div');
    chip.className = 'preset-chip';
    chip.innerText = p.name;
    chip.onclick = () => {
      document.querySelectorAll('.preset-chip').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      applyConfigToForm(p.config);
      showToast(`Đã áp dụng mẫu "${p.name}"!`, 'info');
      if (isRpcRunning) {
        handleUpdateRPC();
      }
    };
    container.appendChild(chip);
  });

  userPresets.forEach(p => {
    const chip = document.createElement('div');
    chip.className = 'preset-chip';
    chip.innerHTML = `
      <span>${escapeHtml(p.name)}</span>
      <span class="preset-delete-btn" title="Xóa mẫu này" onclick="deletePreset(event, ${p.id})">&times;</span>
    `;
    chip.onclick = (e) => {
      if (e.target.classList.contains('preset-delete-btn')) return;
      document.querySelectorAll('.preset-chip').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      applyConfigToForm(p.config);
      showToast(`Đã áp dụng mẫu "${p.name}"!`, 'info');
      if (isRpcRunning) {
        handleUpdateRPC();
      }
    };
    container.appendChild(chip);
  });
}

async function saveCurrentAsPreset() {
  const name = prompt('Nhập tên cho Mẫu Cấu Hình mới:', 'Mẫu Tùy Chỉnh');
  if (!name || !name.trim()) return;

  const config = getCurrentFormConfig();
  delete config.token;

  try {
    const res = await fetch('/api/presets', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: name.trim(), config })
    });
    const data = await res.json();

    if (res.ok && data.success) {
      showToast(`Đã lưu mẫu "${name}" thành công!`, 'success');
      loadPresets();
    } else {
      showToast(`Không thể lưu preset: ${data.message}`, 'error');
    }
  } catch (err) {
    showToast(`Lỗi: ${err.message}`, 'error');
  }
}

async function deletePreset(event, presetId) {
  event.stopPropagation();
  if (!confirm('Bạn có chắc chắn muốn xóa mẫu cấu hình này không?')) return;

  try {
    const res = await fetch(`/api/presets/${presetId}`, { method: 'DELETE' });
    const data = await res.json();
    if (res.ok && data.success) {
      showToast('Đã xóa mẫu cấu hình!', 'info');
      loadPresets();
    } else {
      showToast(`Lỗi: ${data.message}`, 'error');
    }
  } catch (err) {
    showToast(`Lỗi: ${err.message}`, 'error');
  }
}

function toggleRotator() {
  const isEnabled = document.getElementById('check-rotator').checked;
  const intervalSeconds = parseInt(document.getElementById('input-rotator-interval').value) || 30;

  if (rotatorTimer) {
    clearInterval(rotatorTimer);
    rotatorTimer = null;
  }

  if (isEnabled) {
    showToast(`Đã bật Tự Động Đổi Trạng Thái (chu kỳ ${intervalSeconds}s)`, 'info');
    const allPresets = [...DEFAULT_PRESETS, ...userPresets];
    if (allPresets.length === 0) return;

    rotatorTimer = setInterval(() => {
      if (!isRpcRunning) return;
      currentRotatorIndex = (currentRotatorIndex + 1) % allPresets.length;
      const target = allPresets[currentRotatorIndex];
      applyConfigToForm(target.config);
      handleUpdateRPC();
      showToast(`Rotator: Đang chuyển sang "${target.name}"`, 'info');
    }, intervalSeconds * 1000);
  } else {
    showToast('Đã tắt Tự Động Đổi Trạng Thái', 'info');
  }
}

const VISUAL_GALLERY_ITEMS = [
  { id: 'bot_avatar', name: 'Bot Anime Avatar', url: '/static/uploads/b6892ebe383640c596013c353ec3dabd.jpeg' },
  { id: 'vscode', name: 'VS Code', url: 'https://cdn.discordapp.com/app-assets/383226320970055681/1359299466493956258.png' },
  { id: 'python', name: 'Python 3', url: 'https://cdn.discordapp.com/app-assets/383226320970055681/1359299282380918886.png' },
  { id: 'git', name: 'Git', url: 'https://cdn.discordapp.com/app-assets/383226320970055681/1359298453284323538.png' },
  { id: 'docker', name: 'Docker', url: 'https://cdn.discordapp.com/app-assets/383226320970055681/1359298813092823040.png' },
  { id: 'js', name: 'JavaScript', url: 'https://cdn.discordapp.com/app-assets/383226320970055681/1359299016025964687.png' },
  { id: 'ts', name: 'TypeScript', url: 'https://cdn.discordapp.com/app-assets/383226320970055681/1359299427059236984.png' },
  { id: 'react', name: 'React', url: 'https://cdn.discordapp.com/app-assets/383226320970055681/1359299015983894651.png' },
  { id: 'tailwind', name: 'Tailwind CSS', url: 'https://cdn.discordapp.com/app-assets/383226320970055681/1359299371597824070.png' },
  { id: 'cpp', name: 'C++', url: 'https://cdn.discordapp.com/app-assets/383226320970055681/1359298399379390484.png' },
  { id: 'java', name: 'Java', url: 'https://cdn.discordapp.com/app-assets/383226320970055681/1359298971738050570.png' },
  { id: 'rust', name: 'Rust', url: 'https://cdn.discordapp.com/app-assets/383226320970055681/1359299338907549887.png' }
];

const DEFAULT_SAMPLE_BOTS = [
  {
    id: '1546849576986607657',
    name: 'Discord RPG Bot (Anime Avatar)',
    bot_avatar: '/static/uploads/b6892ebe383640c596013c353ec3dabd.jpeg',
    display_avatar: '/static/uploads/b6892ebe383640c596013c353ec3dabd.jpeg',
    badge: 'Avatar Anime RPG'
  },
  {
    id: '383226320970055681',
    name: 'Visual Studio Code',
    bot_avatar: null,
    app_icon: 'https://cdn.discordapp.com/app-assets/383226320970055681/1359299466493956258.png',
    display_avatar: 'https://cdn.discordapp.com/app-assets/383226320970055681/1359299466493956258.png',
    badge: 'App Code Editor'
  },
  {
    id: '383226320970055682',
    name: 'Python 3 Developer Presence',
    bot_avatar: null,
    app_icon: 'https://cdn.discordapp.com/app-assets/383226320970055681/1359299282380918886.png',
    display_avatar: 'https://cdn.discordapp.com/app-assets/383226320970055681/1359299282380918886.png',
    badge: 'Python Environment'
  }
];

function renderVisualGallery() {
  const container = document.getElementById('visual-gallery-grid');
  if (!container) return;
  container.innerHTML = '';

  VISUAL_GALLERY_ITEMS.forEach(item => {
    const tile = document.createElement('div');
    tile.className = 'visual-asset-tile';

    const realUrl = item.id === 'bot_avatar' && detectedAppAvatarUrl ? detectedAppAvatarUrl : item.url;

    tile.innerHTML = `
      <img src="${realUrl}" alt="${escapeHtml(item.name)}" class="visual-asset-img" onerror="this.src='https://cdn.discordapp.com/embed/avatars/0.png'">
      <span class="visual-asset-label">${escapeHtml(item.name)}</span>
      <div class="tile-action-row">
        <button type="button" class="btn-tile-act large" title="Đặt làm Ảnh Lớn">Ảnh Lớn</button>
        <button type="button" class="btn-tile-act small" title="Đặt làm Ảnh Nhỏ">Ảnh Nhỏ</button>
      </div>
    `;

    const btnLarge = tile.querySelector('.btn-tile-act.large');
    const btnSmall = tile.querySelector('.btn-tile-act.small');

    if (btnLarge) {
      btnLarge.onclick = (e) => {
        e.stopPropagation();
        setAsset('large', item.id);
        showToast(`Đã chọn "${item.name}" làm Ảnh Lớn!`, 'info');
      };
    }

    if (btnSmall) {
      btnSmall.onclick = (e) => {
        e.stopPropagation();
        setAsset('small', item.id);
        showToast(`Đã chọn "${item.name}" làm Ảnh Nhỏ!`, 'info');
      };
    }

    tile.onclick = () => {
      setAsset('large', item.id);
      showToast(`Đã chọn "${item.name}" làm Ảnh Lớn!`, 'info');
    };

    container.appendChild(tile);
  });
}

function renderPortalBotsGrid(apps) {
  const container = document.getElementById('portal-bots-container');
  if (!container) return;

  const botList = (apps && apps.length > 0) ? apps : DEFAULT_SAMPLE_BOTS;
  const appIdEl = document.getElementById('input-app-id');
  const currentAppId = (appIdEl && appIdEl.value) ? appIdEl.value.trim() : '';
  container.innerHTML = '';

  botList.forEach(app => {
    const card = document.createElement('div');
    const isSelected = currentAppId && currentAppId === app.id;
    card.className = `portal-bot-card ${isSelected ? 'active' : ''}`;
    
    const avatarUrl = app.display_avatar || app.bot_avatar || app.app_icon || 'https://cdn.discordapp.com/embed/avatars/0.png';
    const badgeText = app.badge || (app.bot_avatar ? 'Avatar Anime Bot' : 'Application');

    card.innerHTML = `
      <img src="${avatarUrl}" alt="${escapeHtml(app.name)}" class="portal-bot-avatar" onerror="this.src='https://cdn.discordapp.com/embed/avatars/0.png'">
      <div class="portal-bot-info">
        <div class="portal-bot-name">${escapeHtml(app.name)}</div>
        <div class="portal-bot-id">ID: ${escapeHtml(app.id)}</div>
        <span class="portal-bot-badge">${badgeText}</span>
      </div>
    `;

    card.onclick = () => {
      document.querySelectorAll('.portal-bot-card').forEach(c => c.classList.remove('active'));
      card.classList.add('active');

      const appIdInput = document.getElementById('input-app-id');
      if (appIdInput) appIdInput.value = app.id;

      const actInput = document.getElementById('input-activity-name');
      if (actInput) actInput.value = app.name;

      detectedAppAvatarUrl = avatarUrl;
      const largeInput = document.getElementById('input-large-image');
      if (largeInput) largeInput.value = 'bot_avatar';

      updateLivePreview();
      renderVisualGallery();
      showToast(`Đã chọn Bot: ${app.name}! Live Preview đã tự động nạp Avatar Anime.`, 'success');

      if (isRpcRunning) {
        handleUpdateRPC();
      }
    };

    container.appendChild(card);
  });
}

function toggleManualInput(target) {
  const wrap = document.getElementById(`manual-${target}-wrap`);
  if (wrap) {
    wrap.classList.toggle('d-none');
  }
}

function clearSmallImage() {
  const smallInput = document.getElementById('input-small-image');
  if (smallInput) {
    smallInput.value = '';
    updateLivePreview();
    showToast('Đã gỡ Ảnh Nhỏ khỏi trạng thái!', 'info');
    if (isRpcRunning) {
      handleUpdateRPC();
    }
  }
}

function onManualImageChange(target) {
  updateLivePreview();
  if (isRpcRunning) {
    handleUpdateRPC();
  }
}

async function useDevPortalAvatar() {
  const largeInput = document.getElementById('input-large-image');
  if (largeInput) {
    largeInput.value = 'bot_avatar';
  }

  showToast('Đang nạp Avatar Anime từ Developer Portal...', 'info');
  await scanPortalApps(true);
  updateLivePreview();

  if (isRpcRunning) {
    handleUpdateRPC();
  } else {
    showToast('Đã nạp Avatar Bot Anime! Bấm Khởi Chạy để hiển thị.', 'success');
  }
}

async function scanPortalApps(autoApply = false) {
  const tokenInput = document.getElementById('input-token');
  const token = tokenInput ? tokenInput.value.trim() : '';
  const appIdInput = document.getElementById('input-app-id');
  const appId = appIdInput ? appIdInput.value.trim() : '';

  if (!token) {
    if (!autoApply) {
      showToast('Vui lòng dán Discord User Token ở tab Tài Khoản trước!', 'error');
    }
    return;
  }

  try {
    const res = await fetch('/api/portal_app_info', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token, appId })
    });
    const data = await res.json();

    if (res.ok && data.success && data.apps && data.apps.length > 0) {
      renderPortalBotsGrid(data.apps);

      let targetApp = data.apps.find(a => appId && a.id === appId) || data.apps[0];
      
      const avatarUrl = targetApp.bot_avatar || targetApp.app_icon || '';
      if (avatarUrl) {
        detectedAppAvatarUrl = avatarUrl;
      }

      const banner = document.getElementById('detected-app-banner');
      const iconEl = document.getElementById('detected-app-icon');
      const titleEl = document.getElementById('detected-app-title');
      const descEl = document.getElementById('detected-app-desc');

      if (banner && iconEl && titleEl && descEl) {
        iconEl.src = avatarUrl || 'https://cdn.discordapp.com/embed/avatars/0.png';
        titleEl.innerText = `${targetApp.name} (ID: ${targetApp.id})`;
        descEl.innerText = targetApp.bot_avatar ? 'Đã tìm thấy Avatar Bot Anime trên Developer Portal!' : 'Đã tìm thấy Ứng dụng trên Developer Portal!';
        banner.classList.remove('d-none');
      }

      if (appIdInput && (!appIdInput.value || autoApply)) {
        appIdInput.value = targetApp.id;
      }

      if (autoApply && avatarUrl) {
        const largeInput = document.getElementById('input-large-image');
        if (largeInput) largeInput.value = 'bot_avatar';
        updateLivePreview();
        renderVisualGallery();
      }

      if (!autoApply) {
        showToast(`Đã tìm thấy ${data.apps.length} bot/ứng dụng từ Developer Portal!`, 'success');
      }
    } else {
      renderPortalBotsGrid([]);
      if (!autoApply) {
        showToast(data.message || 'Không tìm thấy ứng dụng trên Developer Portal với Token này', 'error');
      }
    }
  } catch (err) {
    console.warn('Lỗi khi quét portal apps:', err);
  }
}

function applyDetectedAvatar() {
  const largeInput = document.getElementById('input-large-image');
  if (largeInput) {
    largeInput.value = 'bot_avatar';
    updateLivePreview();
    if (isRpcRunning) {
      handleUpdateRPC();
    }
    showToast('Đã áp dụng Avatar Anime cho Ảnh Lớn!', 'success');
  }
}

function copyTokenScript() {
  const script = `(webpackChunkdiscord_app.push([[''],{},e=>{m=[];for(let c in e.c)m.push(e.c[c])}]),m).find(m=>m?.exports?.default?.getToken!==void 0).exports.default.getToken()`;
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(script).then(() => {
      showToast('Đã copy lệnh lấy Token! Mở Console (F12) trên Discord rồi dán vào.', 'success');
    }).catch(() => {
      prompt('Copy câu lệnh sau và dán vào Console (F12) trên Discord:', script);
    });
  } else {
    prompt('Copy câu lệnh sau và dán vào Console (F12) trên Discord:', script);
  }
}

function showToast(message, type = 'info', duration = 3500) {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast-item ${type}`;
  toast.innerHTML = `<span>${escapeHtml(message)}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(12px) scale(0.95)';
    toast.style.transition = 'all 0.22s ease';
    setTimeout(() => toast.remove(), 220);
  }, duration);
}

function escapeHtml(text) {
  if (!text) return '';
  const div = document.createElement('div');
  div.innerText = text;
  return div.innerHTML;
}

let isAccountLinked = false;
let currentQuestIdRunning = null;
let lyricAudioContext = null;
let lyricOscillator = null;
let lyricGainNode = null;
let lyricAudioTimer = null;
let lyricCurrentSeconds = 0;
let lyricIsPlaying = false;
let lyricActiveIndex = -1;

const BUILTIN_LYRICS = {
  sunset: [
    { time: 0, text: "Lofi Beats - Sunset Boulevard 🌅" },
    { time: 5, text: "Giai điệu hoàng hôn dịu êm buông xuống" },
    { time: 12, text: "Ánh đèn phố thị lung linh rực sáng" },
    { time: 18, text: "Thả trôi ưu phiền cùng khúc nhạc đêm" },
    { time: 25, text: "Drakonis RPC phát nhạc trực tiếp" },
    { time: 32, text: "Giai điệu lofi ngân vang trong tĩnh lặng" },
    { time: 40, text: "Chill cùng bạn bè trên Discord đêm nay" },
    { time: 48, text: "Hoàng hôn dần tắt, màn đêm buông lơi" }
  ],
  cyber: [
    { time: 0, text: "Cyber City 2077 - Synthwave Night ⚡" },
    { time: 4, text: "Tia sáng neon quét qua con phố dài" },
    { time: 10, text: "Tốc độ ánh sáng trong màn đêm tương lai" },
    { time: 17, text: "Bass dồn dập đánh thức thế giới số hóa" },
    { time: 24, text: "Công nghệ và âm nhạc hòa làm một" },
    { time: 31, text: "Đỉnh cao phong cách Drakonis Master" },
    { time: 38, text: "Chinh phục thế giới ảo không giới hạn" }
  ],
  midnight: [
    { time: 0, text: "Tokyo Midnight Rain - Piano Solo 🌧️" },
    { time: 6, text: "Tiếng mưa rơi nhẹ bên khung cửa sổ" },
    { time: 13, text: "Từng nốt dương cầm lắng đọng tâm hồn" },
    { time: 20, text: "Không gian bình yên giữa phố phường" },
    { time: 28, text: "Trạng thái cảm xúc hòa cùng thanh âm" },
    { time: 36, text: "Cảm nhận sự tĩnh tại trong từng khoảnh khắc" }
  ]
};

async function checkAccountLinkStatus() {
  try {
    const res = await fetch('/api/account/info');
    if (!res.ok) return;
    const data = await res.json();
    if (data.success && data.has_token) {
      isAccountLinked = true;
      applyUnlockedAccountState(data);
    } else {
      isAccountLinked = false;
      applyLockedAccountState();
    }
  } catch (err) {
  }
}

function applyUnlockedAccountState(info) {
  const topWarn = document.getElementById('top-unlinked-banner');
  if (topWarn) topWarn.classList.add('d-none');
  const botBar = document.getElementById('bottom-token-bar');
  if (botBar) botBar.classList.add('d-none');

  document.querySelectorAll('.locked-feature-overlay').forEach(el => {
    el.classList.add('d-none');
  });

  const headerName = document.getElementById('header-user-name');
  if (headerName && info.discord_username) {
    headerName.innerText = info.discord_username;
  }
  const headerAvatar = document.getElementById('header-user-avatar');
  const headerPlaceholder = document.getElementById('header-user-avatar-placeholder');
  if (info.discord_avatar) {
    if (headerAvatar) {
      headerAvatar.src = info.discord_avatar;
      headerAvatar.classList.remove('d-none');
    }
    if (headerPlaceholder) headerPlaceholder.classList.add('d-none');
  }

  const badge = document.getElementById('header-user-badge');
  if (badge) {
    badge.className = 'user-chip-badge linked';
    badge.innerText = 'Đã Xác Minh';
  }

  const accName = document.getElementById('account-view-name');
  if (accName && info.discord_username) {
    accName.innerText = info.discord_username;
  }
  const accAvatar = document.getElementById('account-view-avatar');
  if (accAvatar && info.discord_avatar) {
    accAvatar.src = info.discord_avatar;
  }
  const accStatus = document.getElementById('account-view-status');
  if (accStatus) {
    accStatus.innerText = `ID: ${info.discord_id} • Đã liên kết token (${info.masked_token})`;
  }
}

function applyLockedAccountState() {
  const topWarn = document.getElementById('top-unlinked-banner');
  if (topWarn) topWarn.classList.remove('d-none');
  const botBar = document.getElementById('bottom-token-bar');
  if (botBar) botBar.classList.remove('d-none');

  document.querySelectorAll('.locked-feature-overlay').forEach(el => {
    el.classList.remove('d-none');
  });

  const badge = document.getElementById('header-user-badge');
  if (badge) {
    badge.className = 'user-chip-badge unlinked';
    badge.innerText = 'Chưa Liên Kết';
  }
}

async function handleBindToken() {
  const tokenInput = document.getElementById('input-token');
  const token = tokenInput ? tokenInput.value.trim() : '';
  if (!token) {
    showToast('Vui lòng dán Discord User Token vào ô nhập trước!', 'error');
    return;
  }

  showToast('Đang kết nối xác thực với Discord API...', 'info');

  try {
    const res = await fetch('/api/account/bind_token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token })
    });
    const data = await res.json();
    if (res.ok && data.success) {
      showToast(data.message || 'Liên kết Discord Token thành công!', 'success');
      localStorage.setItem('discord_rpc_user_token', token);
      saveFormDraft(false);
      checkAccountLinkStatus();
      loadAvailableQuests();
    } else {
      showToast(data.message || 'Không thể liên kết token!', 'error');
    }
  } catch (err) {
    showToast('Lỗi kết nối máy chủ: ' + err.message, 'error');
  }
}

async function handleUnbindToken() {
  if (!confirm('Bạn có chắc muốn hủy liên kết Discord Token khỏi tài khoản này?')) return;
  try {
    const res = await fetch('/api/account/unbind_token', { method: 'POST' });
    const data = await res.json();
    if (res.ok && data.success) {
      showToast('Đã hủy liên kết token thành công!', 'info');
      localStorage.removeItem('discord_rpc_user_token');
      const tokenInput = document.getElementById('input-token');
      if (tokenInput) tokenInput.value = '';
      checkAccountLinkStatus();
    } else {
      showToast(data.message || 'Lỗi khi hủy liên kết', 'error');
    }
  } catch (err) {
    showToast('Lỗi: ' + err.message, 'error');
  }
}

async function loadAvailableQuests() {
  const container = document.getElementById('quests-list-container');
  if (!container) return;

  try {
    const res = await fetch('/api/quests');
    if (!res.ok) return;
    const data = await res.json();
    if (data.success && Array.isArray(data.quests)) {
      renderQuestsList(data.quests);
      if (data.worker_status) {
        updateQuestUIStatus(data.worker_status);
      }
    }
  } catch (err) {
  }
}

function renderQuestsList(quests) {
  const container = document.getElementById('quests-list-container');
  if (!container) return;

  if (quests.length === 0) {
    container.innerHTML = '<div class="empty-hint-box">Không có nhiệm vụ Discord nào khả dụng lúc này.</div>';
    return;
  }

  let html = '';
  quests.forEach(q => {
    const qid = escapeHtml(q.id);
    const title = escapeHtml(q.title);
    const game = escapeHtml(q.game_name);
    const reward = escapeHtml(q.reward);
    const badge = escapeHtml(q.badge || 'Nhiệm Vụ');
    const sec = q.target_seconds || 45;

    html += `
      <div class="quest-card">
        <div class="quest-card-top">
          <span class="quest-card-badge">${badge}</span>
          <div class="quest-card-title">${title}</div>
          <div class="quest-card-reward">${reward}</div>
        </div>
        <button type="button" class="action-btn action-start w-100 py-2 mt-2" onclick="handleStartQuest('${qid}', '${escapeHtml(title)}', 'PLAY_ON_DESKTOP', ${sec})">
          Bắt Đầu Auto Cày
        </button>
      </div>
    `;
  });
  container.innerHTML = html;
}

async function handleStartQuest(questId, questName, taskType = 'PLAY_ON_DESKTOP', targetSeconds = 45) {
  if (!isAccountLinked) {
    showToast('Vui lòng liên kết Discord Token trước khi cày Quest!', 'error');
    switchMainTab('tab-account');
    return;
  }

  currentQuestIdRunning = questId;
  showToast(`Bắt đầu cày nhiệm vụ: ${questName}...`, 'info');

  try {
    const res = await fetch('/api/quests/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ quest_id: questId, quest_name: questName, task_type: taskType, target_seconds: targetSeconds })
    });
    const data = await res.json();
    if (res.ok && data.success) {
      showToast(data.message, 'success');
      pollQuestStatus();
    } else {
      showToast(data.message || 'Lỗi khi khởi chạy Quest', 'error');
    }
  } catch (err) {
    showToast('Lỗi kết nối: ' + err.message, 'error');
  }
}

async function handleStopQuest() {
  try {
    const res = await fetch('/api/quests/stop', { method: 'POST' });
    const data = await res.json();
    if (res.ok) {
      showToast('Đã gửi lệnh dừng nhiệm vụ', 'info');
      pollQuestStatus();
    }
  } catch (err) {
    showToast('Lỗi: ' + err.message, 'error');
  }
}

async function pollQuestStatus() {
  try {
    const res = await fetch('/api/quests/status');
    if (!res.ok) return;
    const data = await res.json();
    if (data.success && data.status) {
      updateQuestUIStatus(data.status);
    }
  } catch (err) {
  }
}

function updateQuestUIStatus(st) {
  const titleEl = document.getElementById('quest-active-title');
  const subEl = document.getElementById('quest-active-sub');
  const chipEl = document.getElementById('quest-status-chip');
  const fillEl = document.getElementById('quest-progress-fill');
  const pctEl = document.getElementById('quest-progress-pct');
  const timeEl = document.getElementById('quest-progress-time');
  const stopBtn = document.getElementById('btn-quest-stop');

  if (!titleEl) return;

  if (st.status === 'running') {
    titleEl.innerText = st.quest_name || 'Đang cày nhiệm vụ...';
    subEl.innerText = `Đang gửi gói stream heartbeat giả lập qua Discord Gateway (${st.task_type})`;
    chipEl.className = 'quest-status-chip running';
    chipEl.innerText = 'Đang Cày';
    if (stopBtn) stopBtn.disabled = false;
  } else if (st.status === 'completed') {
    titleEl.innerText = st.quest_name || 'Nhiệm vụ hoàn thành!';
    subEl.innerText = 'Đã mở khóa phần thưởng thành công! Kiểm tra hộp quà trên Discord.';
    chipEl.className = 'quest-status-chip completed';
    chipEl.innerText = 'Hoàn Thành';
    if (stopBtn) stopBtn.disabled = true;
  } else {
    titleEl.innerText = 'Chưa chạy nhiệm vụ nào';
    subEl.innerText = 'Chọn một nhiệm vụ bên dưới và bấm "Bắt Đầu Auto Cày"';
    chipEl.className = 'quest-status-chip';
    chipEl.innerText = 'Chờ Lệnh';
    if (stopBtn) stopBtn.disabled = true;
  }

  const pct = st.progress_pct || 0;
  if (fillEl) fillEl.style.width = `${pct}%`;
  if (pctEl) pctEl.innerText = `${pct}%`;
  if (timeEl) timeEl.innerText = `${st.elapsed_seconds || 0}s / ${st.target_seconds || 0}s`;
}

async function handleClaimHypeSquad(houseId) {
  if (!isAccountLinked) {
    showToast('Vui lòng liên kết Discord Token trước khi nhận huy hiệu!', 'error');
    switchMainTab('tab-account');
    return;
  }

  showToast('Đang gửi yêu cầu nhận huy hiệu HypeSquad tới Discord...', 'info');

  try {
    const res = await fetch('/api/hypesquad/claim', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ house_id: houseId })
    });
    const data = await res.json();
    if (res.ok && data.success) {
      showToast(data.message, 'success');
      fetchLogs(true);
    } else {
      showToast(data.message || 'Không thể nhận huy hiệu', 'error');
    }
  } catch (err) {
    showToast('Lỗi kết nối: ' + err.message, 'error');
  }
}

function initLyricModule() {
  handleSelectLyricTrack();
}

function handleSelectLyricTrack() {
  const sel = document.getElementById('select-lyric-track');
  if (!sel) return;
  const val = sel.value;
  const customBox = document.getElementById('custom-lrc-group');

  if (val === 'custom') {
    if (customBox) customBox.classList.remove('d-none');
    renderLyricsView([]);
  } else {
    if (customBox) customBox.classList.add('d-none');
    const trackLines = BUILTIN_LYRICS[val] || [];
    renderLyricsView(trackLines);
  }
}

function renderLyricsView(lines) {
  const wrap = document.getElementById('lyric-lines-wrapper');
  if (!wrap) return;

  if (!lines || lines.length === 0) {
    wrap.innerHTML = '<div class="lyric-line">Chưa có câu hát nào hoặc đang dùng chế độ dán lời thủ công.</div>';
    return;
  }

  let html = '';
  lines.forEach((l, idx) => {
    html += `<div class="lyric-line" id="lyric-line-${idx}">${escapeHtml(l.text)}</div>`;
  });
  wrap.innerHTML = html;
}

function handleToggleLyricAudio() {
  if (lyricIsPlaying) {
    handleStopLyricAudio();
  } else {
    startLyricPlayback();
  }
}

function startLyricPlayback() {
  if (!isAccountLinked) {
    showToast('Cần liên kết Discord Token để đồng bộ câu hát lên Custom Status!', 'error');
    switchMainTab('tab-account');
    return;
  }

  lyricIsPlaying = true;
  lyricCurrentSeconds = 0;
  lyricActiveIndex = -1;

  const playBtn = document.getElementById('btn-lyric-play');
  const stopBtn = document.getElementById('btn-lyric-stop');
  const syncInd = document.getElementById('lyric-sync-indicator');

  if (playBtn) playBtn.innerText = 'Đang Phát & Đồng Bộ';
  if (stopBtn) stopBtn.disabled = false;
  if (syncInd) syncInd.innerText = 'Đang đồng bộ Discord Status...';

  try {
    if (!lyricAudioContext) {
      lyricAudioContext = new (window.AudioContext || window.webkitAudioContext)();
    }
    if (lyricAudioContext.state === 'suspended') {
      lyricAudioContext.resume();
    }

    playLofiSynthChord();
  } catch (e) {
  }

  if (lyricAudioTimer) clearInterval(lyricAudioTimer);
  lyricAudioTimer = setInterval(tickLyricPlayback, 1000);
  tickLyricPlayback();
  showToast('Đã bắt đầu phát nhạc và đồng bộ trạng thái Discord!', 'success');
}

function playLofiSynthChord() {
  try {
    if (!lyricAudioContext) return;
    const osc = lyricAudioContext.createOscillator();
    const gain = lyricAudioContext.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(261.63, lyricAudioContext.currentTime);
    gain.gain.setValueAtTime(0.08, lyricAudioContext.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, lyricAudioContext.currentTime + 3.5);
    osc.connect(gain);
    gain.connect(lyricAudioContext.destination);
    osc.start();
    osc.stop(lyricAudioContext.currentTime + 3.5);
  } catch (e) {
  }
}

function tickLyricPlayback() {
  lyricCurrentSeconds++;

  const curTimeEl = document.getElementById('audio-time-current');
  if (curTimeEl) {
    const m = String(Math.floor(lyricCurrentSeconds / 60)).padStart(2, '0');
    const s = String(lyricCurrentSeconds % 60).padStart(2, '0');
    curTimeEl.innerText = `${m}:${s}`;
  }

  const sel = document.getElementById('select-lyric-track');
  const trackKey = sel ? sel.value : 'sunset';
  let lines = BUILTIN_LYRICS[trackKey] || [];

  if (trackKey === 'custom') {
    const area = document.getElementById('input-custom-lrc');
    const raw = area ? area.value.trim() : '';
    lines = parseCustomLrc(raw);
  }

  let matchedIdx = -1;
  for (let i = lines.length - 1; i >= 0; i--) {
    if (lyricCurrentSeconds >= lines[i].time) {
      matchedIdx = i;
      break;
    }
  }

  if (matchedIdx !== -1 && matchedIdx !== lyricActiveIndex) {
    lyricActiveIndex = matchedIdx;
    highlightLyricLine(matchedIdx);
    const activeLineText = lines[matchedIdx].text;
    syncLyricToDiscord(activeLineText);
    playLofiSynthChord();
  }

  const maxTime = lines.length > 0 ? lines[lines.length - 1].time + 15 : 60;
  const totEl = document.getElementById('audio-time-total');
  if (totEl) {
    const tm = String(Math.floor(maxTime / 60)).padStart(2, '0');
    const ts = String(maxTime % 60).padStart(2, '0');
    totEl.innerText = `${tm}:${ts}`;
  }

  if (lyricCurrentSeconds >= maxTime) {
    handleStopLyricAudio();
    showToast('Bài hát đã kết thúc!', 'info');
  }
}

function highlightLyricLine(idx) {
  document.querySelectorAll('.lyric-line').forEach((el, i) => {
    if (i === idx) {
      el.classList.add('active');
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    } else {
      el.classList.remove('active');
    }
  });
}

function parseCustomLrc(text) {
  if (!text) return [];
  const lines = text.split('\n');
  const result = [];
  let secCounter = 0;
  lines.forEach(l => {
    const clean = l.trim();
    if (!clean) return;
    const match = clean.match(/\[(\d{1,2}):(\d{2})\](.*)/);
    if (match) {
      const min = parseInt(match[1]);
      const sec = parseInt(match[2]);
      result.push({ time: min * 60 + sec, text: match[3].trim() });
    } else {
      result.push({ time: secCounter, text: clean });
      secCounter += 6;
    }
  });
  return result;
}

async function syncLyricToDiscord(lineText) {
  const emojiSel = document.getElementById('select-lyric-emoji');
  const emoji = emojiSel ? emojiSel.value : '🎵';

  try {
    await fetch('/api/lyrics/sync', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: lineText, emoji })
    });
  } catch (e) {
  }
}

async function handleStopLyricAudio() {
  lyricIsPlaying = false;
  if (lyricAudioTimer) {
    clearInterval(lyricAudioTimer);
    lyricAudioTimer = null;
  }

  const playBtn = document.getElementById('btn-lyric-play');
  const stopBtn = document.getElementById('btn-lyric-stop');
  const syncInd = document.getElementById('lyric-sync-indicator');

  if (playBtn) playBtn.innerText = 'Bắt Đầu Phát & Đồng Bộ';
  if (stopBtn) stopBtn.disabled = true;
  if (syncInd) syncInd.innerText = 'Đã dừng';
}

async function handleClearDiscordStatus() {
  showToast('Đang xóa câu hát trên Discord Status...', 'info');
  try {
    const res = await fetch('/api/lyrics/clear', { method: 'POST' });
    const data = await res.json();
    if (res.ok && data.success) {
      showToast('Đã xóa Custom Status trên Discord thành công!', 'success');
    } else {
      showToast(data.message || 'Lỗi khi xóa status', 'error');
    }
  } catch (e) {
    showToast('Lỗi: ' + e.message, 'error');
  }
}
