// State Management
const state = {
  query: '',
  provider: 'all',
  orientation: '',
  sort: 'most_relevant',
  page: 1,
  results: [],
  total: 0,
  isLoading: false,
  activeVideo: null,
  isLicensed: false,
  adminPassword: ''
};

// DOM Elements
const searchForm = document.getElementById('search-form');
const searchInput = document.getElementById('search-input');
const clearSearchBtn = document.getElementById('clear-search-btn');
const providerTabs = document.getElementById('provider-tabs');
const orientationSelect = document.getElementById('orientation-select');
const sortSelect = document.getElementById('sort-select');
const topicChips = document.getElementById('topic-chips');
const videoGrid = document.getElementById('video-grid');
const loadingState = document.getElementById('loading-state');
const welcomeState = document.getElementById('welcome-state');
const noResultsState = document.getElementById('no-results-state');
const loadMoreWrapper = document.getElementById('load-more-wrapper');
const loadMoreBtn = document.getElementById('load-more-btn');
const statsBadge = document.getElementById('results-count-text');
const licenseBadge = document.getElementById('license-badge');
const licenseStatusText = document.getElementById('license-status-text');

// Modal Elements
const videoModal = document.getElementById('video-modal');
const modalVideoPlayer = document.getElementById('modal-video-player');
const modalTitle = document.getElementById('modal-title');
const modalBadges = document.getElementById('modal-badges');
const modalDownloadOptions = document.getElementById('modal-download-options');
const closeModalBtn = document.getElementById('close-modal-btn');
const toast = document.getElementById('toast');
const toastMessage = document.getElementById('toast-message');

// License & Admin Modal Elements
const licenseModal = document.getElementById('license-modal');
const licenseForm = document.getElementById('license-form');
const licenseKeyInput = document.getElementById('license-key-input');
const licenseErrorMsg = document.getElementById('license-error-msg');

const openAdminBtn = document.getElementById('open-admin-btn');
const adminModal = document.getElementById('admin-modal');
const closeAdminBtn = document.getElementById('close-admin-btn');
const adminLoginView = document.getElementById('admin-login-view');
const adminDashboardView = document.getElementById('admin-dashboard-view');
const adminLoginForm = document.getElementById('admin-login-form');
const adminPassInput = document.getElementById('admin-pass-input');
const adminLoginError = document.getElementById('admin-login-error');
const adminLogoutBtn = document.getElementById('admin-logout-btn');

const createKeyForm = document.getElementById('create-key-form');
const clientNameInput = document.getElementById('client-name-input');
const keyDaysSelect = document.getElementById('key-days-select');
const newKeyBox = document.getElementById('new-key-box');
const newKeyCode = document.getElementById('new-key-code');
const copyKeyBtn = document.getElementById('copy-key-btn');
const licensesTableBody = document.getElementById('licenses-table-body');

// Storyblocks Developer API Key DOM Elements
const createApiKeyForm = document.getElementById('create-api-key-form');
const apiClientName = document.getElementById('api-client-name');
const apiDaysSelect = document.getElementById('api-days-select');
const apiLimitSelect = document.getElementById('api-limit-select');
const newApiKeyBox = document.getElementById('new-api-key-box');
const newApiKeyCode = document.getElementById('new-api-key-code');
const copyApiKeyBtn = document.getElementById('copy-api-key-btn');
const apiKeysTableBody = document.getElementById('api-keys-table-body');

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
  setupEventListeners();
  setupAdminListeners();

  // Check License on start
  await checkLicenseStatus();
});

// --- LICENSE VERIFICATION ---
// Purge old cached tokens from all computers
localStorage.removeItem('stockstream_license');
localStorage.removeItem('stockstream_client_session_v2');

const SESSION_STORAGE_KEY = 'stockstream_v3_session';

async function checkLicenseStatus() {
  const savedKey = localStorage.getItem(SESSION_STORAGE_KEY);
  if (!savedKey) {
    lockApp('Please enter your license key to unlock StockStream.');
    return;
  }

  const isValid = await verifyLicenseKey(savedKey, false);
  if (isValid) {
    unlockApp();
    triggerSearch('earth');
  } else {
    lockApp('Your session has expired. Please enter a valid license key.');
  }
}

function getOrCreateDeviceId() {
  let devId = localStorage.getItem('stockstream_device_fingerprint');
  if (!devId) {
    devId = 'DEV-' + Math.random().toString(36).substring(2, 10).toUpperCase() + '-' + Date.now().toString(36).toUpperCase();
    localStorage.setItem('stockstream_device_fingerprint', devId);
  }
  return devId;
}

function lockApp(msg = '') {
  state.isLicensed = false;
  licenseModal.classList.remove('hidden');
  licenseBadge.classList.add('expired');
  licenseStatusText.textContent = 'Locked';
  licenseBadge.title = 'Subscription Locked';
  if (msg && licenseErrorMsg) {
    licenseErrorMsg.textContent = msg;
    licenseErrorMsg.classList.remove('hidden');
  }
}

function unlockApp() {
  state.isLicensed = true;
  licenseModal.classList.add('hidden');
  if (licenseErrorMsg) licenseErrorMsg.classList.add('hidden');
}

async function verifyLicenseKey(key, showErrors = true) {
  if (!key) return false;
  try {
    const deviceId = getOrCreateDeviceId();
    const res = await fetch('/api/license/verify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ license_key: key, device_id: deviceId })
    });
    const data = await res.json();

    if (data.valid) {
      state.isLicensed = true;
      localStorage.setItem(SESSION_STORAGE_KEY, data.license_key);
      licenseBadge.classList.remove('expired');

      let daysText = '';
      if (data.days_remaining > 365) {
        daysText = 'Lifetime Active';
      } else if (data.days_remaining > 1) {
        daysText = `${data.days_remaining} Days Remaining`;
      } else if (data.days_remaining === 1) {
        daysText = '1 Day Left (Expires Soon)';
      } else {
        daysText = 'Expires Today';
      }

      licenseStatusText.textContent = daysText;
      licenseBadge.title = `Licensed to: ${data.client_name || 'Subscriber'} | Valid until: ${data.expires_at || ''}`;
      return true;
    } else {
      localStorage.removeItem(SESSION_STORAGE_KEY);
      if (showErrors && licenseErrorMsg) {
        licenseErrorMsg.textContent = data.message || 'Invalid License Key';
        licenseErrorMsg.classList.remove('hidden');
      }
      licenseBadge.classList.add('expired');
      licenseStatusText.textContent = 'Locked';
      licenseBadge.title = 'Access Locked';
      return false;
    }
  } catch (err) {
    console.error('License check error:', err);
    return false;
  }
}

function setupEventListeners() {
  // Lock Tool / Logout Device Button
  const lockAppBtn = document.getElementById('lock-app-btn');
  if (lockAppBtn) {
    lockAppBtn.addEventListener('click', () => {
      localStorage.removeItem(SESSION_STORAGE_KEY);
      lockApp('Device logged out. Please enter your license key.');
    });
  }

  // License Activation Form
  licenseForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const key = licenseKeyInput.value.trim();
    if (!key) return;

    licenseErrorMsg.classList.add('hidden');
    const isValid = await verifyLicenseKey(key, true);
    if (isValid) {
      licenseModal.classList.add('hidden');
      showToast('License successfully activated!');
      triggerSearch('earth');
    }
  });

  // Search Form Submit
  searchForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const q = searchInput.value.trim();
    if (q) {
      triggerSearch(q);
    }
  });

  // Search Input Clear Button
  searchInput.addEventListener('input', () => {
    clearSearchBtn.style.display = searchInput.value ? 'block' : 'none';
  });

  clearSearchBtn.addEventListener('click', () => {
    searchInput.value = '';
    clearSearchBtn.style.display = 'none';
    searchInput.focus();
  });

  // Provider Tabs
  providerTabs.addEventListener('click', (e) => {
    const tab = e.target.closest('.pill-tab');
    if (!tab) return;
    document.querySelectorAll('.pill-tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    state.provider = tab.dataset.provider;
    if (state.query) {
      triggerSearch(state.query);
    }
  });

  // Filters
  orientationSelect.addEventListener('change', () => {
    state.orientation = orientationSelect.value;
    if (state.query) triggerSearch(state.query);
  });

  sortSelect.addEventListener('change', () => {
    state.sort = sortSelect.value;
    if (state.query) triggerSearch(state.query);
  });

  // Topic Chips
  topicChips.addEventListener('click', (e) => {
    const chip = e.target.closest('.topic-chip');
    if (!chip) return;
    const query = chip.dataset.query;
    searchInput.value = query;
    clearSearchBtn.style.display = 'block';
    triggerSearch(query);
  });

  // Load More Button
  loadMoreBtn.addEventListener('click', () => {
    if (!state.isLoading) {
      fetchVideos(false);
    }
  });

  // Modal Close
  closeModalBtn.addEventListener('click', closeModal);
  videoModal.addEventListener('click', (e) => {
    if (e.target === videoModal) closeModal();
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      if (!videoModal.classList.contains('hidden')) closeModal();
      if (!adminModal.classList.contains('hidden')) closeAdminModal();
    }
  });
}

// --- ADMIN PORTAL LOGIC ---
const ADMIN_SESSION_KEY = 'stockstream_admin_pass_v1';

window.switchAdminTab = function(targetId, clickedBtn) {
  document.querySelectorAll('.admin-subtab').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.admin-tab-content').forEach(c => {
    c.classList.add('hidden');
    c.style.display = 'none';
  });

  if (clickedBtn) {
    clickedBtn.classList.add('active');
  } else {
    const activeBtn = document.querySelector(`.admin-subtab[data-tab="${targetId}"]`);
    if (activeBtn) activeBtn.classList.add('active');
  }

  const targetContent = document.getElementById(targetId);
  if (targetContent) {
    targetContent.classList.remove('hidden');
    targetContent.style.display = 'block';
  }

  if (targetId === 'tab-licenses') {
    if (window.loadAdminLicenses) window.loadAdminLicenses();
  } else if (targetId === 'tab-apikeys') {
    if (window.loadAdminApiKeys) window.loadAdminApiKeys();
  }
};

function setupAdminListeners() {
  state.adminPassword = sessionStorage.getItem(ADMIN_SESSION_KEY) || '';

  const handleOpenAdmin = () => {
    adminModal.classList.remove('hidden');
    state.adminPassword = sessionStorage.getItem(ADMIN_SESSION_KEY) || state.adminPassword || '';
    if (!state.adminPassword) {
      adminLoginView.classList.remove('hidden');
      adminDashboardView.classList.add('hidden');
    } else {
      adminLoginView.classList.add('hidden');
      adminDashboardView.classList.remove('hidden');
      loadAdminLicenses();
    }
  };

  // Secret 1: Check if URL has #admin
  if (window.location.hash === '#admin') {
    handleOpenAdmin();
  }
  window.addEventListener('hashchange', () => {
    if (window.location.hash === '#admin') handleOpenAdmin();
  });

  // Secret 2: Keyboard Shortcut Ctrl + Shift + A
  document.addEventListener('keydown', (e) => {
    if (e.ctrlKey && e.shiftKey && (e.key === 'A' || e.key === 'a')) {
      e.preventDefault();
      handleOpenAdmin();
    }
  });

  // Secret 3: Double click on Brand Logo
  const brandLogo = document.querySelector('.brand-logo');
  if (brandLogo) {
    brandLogo.addEventListener('dblclick', (e) => {
      e.preventDefault();
      handleOpenAdmin();
    });
  }

  if (openAdminBtn) {
    openAdminBtn.addEventListener('click', handleOpenAdmin);
  }

  closeAdminBtn.addEventListener('click', closeAdminModal);

  // Admin Login
  adminLoginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const pass = adminPassInput.value.trim();
    if (!pass) return;

    try {
      const res = await fetch('/api/admin/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password: pass })
      });
      if (res.ok) {
        state.adminPassword = pass;
        sessionStorage.setItem(ADMIN_SESSION_KEY, pass);
        adminLoginError.classList.add('hidden');
        adminLoginView.classList.add('hidden');
        adminDashboardView.classList.remove('hidden');
        loadAdminLicenses();
      } else {
        adminLoginError.textContent = 'Incorrect password. Access denied.';
        adminLoginError.classList.remove('hidden');
      }
    } catch (err) {
      adminLoginError.textContent = 'Server error logging in';
      adminLoginError.classList.remove('hidden');
    }
  });

  // Admin Logout
  adminLogoutBtn.addEventListener('click', () => {
    state.adminPassword = '';
    sessionStorage.removeItem(ADMIN_SESSION_KEY);
    adminDashboardView.classList.add('hidden');
    adminLoginView.classList.remove('hidden');
    adminPassInput.value = '';
  });

  const subtabBtns = document.querySelectorAll('.admin-subtab');
  subtabBtns.forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const targetId = btn.getAttribute('data-tab');
      window.switchAdminTab(targetId, btn);
    });
  });

  // Create Web License Form
  createKeyForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const name = clientNameInput.value.trim() || 'Client';
    const days = parseInt(keyDaysSelect.value, 10) || 30;

    const currentPass = state.adminPassword || sessionStorage.getItem(ADMIN_SESSION_KEY) || '';
    if (!currentPass) {
      showToast('Please re-login to Admin');
      adminLoginView.classList.remove('hidden');
      adminDashboardView.classList.add('hidden');
      return;
    }

    try {
      const res = await fetch('/api/admin/create-license', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password: currentPass, client_name: name, days: days })
      });
      const data = await res.json();
      if (data.success) {
        newKeyCode.textContent = data.license_key;
        newKeyBox.classList.remove('hidden');
        clientNameInput.value = '';
        showToast(`Key generated for ${name} (${days} Days)`);
        loadAdminLicenses();
      } else {
        showToast(data.detail || 'Error generating key');
      }
    } catch (err) {
      showToast('Error generating license key');
    }
  });

  // Create Storyblocks Developer API Key Form
  if (createApiKeyForm) {
    createApiKeyForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const name = apiClientName.value.trim() || 'Developer';
      const days = parseInt(apiDaysSelect.value, 10) || 30;
      const limit = parseInt(apiLimitSelect.value, 10);

      const currentPass = state.adminPassword || sessionStorage.getItem(ADMIN_SESSION_KEY) || '';
      if (!currentPass) {
        showToast('Please re-login to Admin');
        adminLoginView.classList.remove('hidden');
        adminDashboardView.classList.add('hidden');
        return;
      }

      try {
        const res = await fetch('/api/admin/create-api-key', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ password: currentPass, client_name: name, days: days, daily_limit: limit })
        });
        const data = await res.json();
        if (data.success) {
          newApiKeyCode.textContent = data.api_key;
          newApiKeyBox.classList.remove('hidden');
          apiClientName.value = '';
          showToast(`Storyblocks API Key created for ${name} (${limit > 0 ? limit + ' req/day' : 'Unlimited'})`);
          loadAdminApiKeys();
        } else {
          showToast(data.detail || 'Error generating API key');
        }
      } catch (err) {
        showToast('Error generating API key');
      }
    });
  }

  // Copy Web License Key Button
  copyKeyBtn.addEventListener('click', () => {
    navigator.clipboard.writeText(newKeyCode.textContent);
    showToast('Web License Key copied to clipboard!');
  });

  // Copy API Key Button
  if (copyApiKeyBtn) {
    copyApiKeyBtn.addEventListener('click', () => {
      navigator.clipboard.writeText(newApiKeyCode.textContent);
      showToast('Storyblocks API Key copied to clipboard!');
    });
  }
}

function closeAdminModal() {
  adminModal.classList.add('hidden');
}

async function loadAdminLicenses() {
  if (!state.adminPassword) return;
  try {
    const res = await fetch(`/api/admin/licenses?password=${encodeURIComponent(state.adminPassword)}`);
    const data = await res.json();
    if (data.success) {
      renderLicensesTable(data.licenses);
    }
  } catch (err) {
    console.error('Error loading licenses:', err);
  }
}
window.loadAdminLicenses = loadAdminLicenses;

function renderLicensesTable(licenses) {
  licensesTableBody.innerHTML = '';
  if (!licenses || licenses.length === 0) {
    licensesTableBody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 14px;">No licenses generated yet.</td></tr>';
    return;
  }

  licenses.forEach(lic => {
    const tr = document.createElement('tr');
    const statusClass = lic.status === 'active' ? 'active' : (lic.status === 'expired' ? 'expired' : 'revoked');
    
    tr.innerHTML = `
      <td><strong>${escapeHtml(lic.client_name)}</strong></td>
      <td><code>${escapeHtml(lic.license_key)}</code></td>
      <td>${lic.duration_days} Days</td>
      <td>${escapeHtml(lic.expires_at.split(' ')[0])}</td>
      <td><span class="status-pill ${statusClass}">${lic.status}</span></td>
      <td>
        ${lic.status === 'active' ? 
          `<button class="btn-table-action" onclick="revokeLicense('${lic.license_key}')" title="Deactivate"><i class="fa-solid fa-ban"></i> Revoke</button>` : 
          `<button class="btn-table-action" onclick="deleteLicense(${lic.id})" title="Delete"><i class="fa-solid fa-trash"></i> Delete</button>`
        }
      </td>
    `;
    licensesTableBody.appendChild(tr);
  });
}

async function loadAdminApiKeys() {
  if (!state.adminPassword || !apiKeysTableBody) return;
  try {
    const res = await fetch(`/api/admin/api-keys?password=${encodeURIComponent(state.adminPassword)}`);
    const data = await res.json();
    if (data.success) {
      renderApiKeysTable(data.api_keys);
    }
  } catch (err) {
    console.error('Error loading API keys:', err);
  }
}
window.loadAdminApiKeys = loadAdminApiKeys;

function renderApiKeysTable(apiKeys) {
  if (!apiKeysTableBody) return;
  apiKeysTableBody.innerHTML = '';
  if (!apiKeys || apiKeys.length === 0) {
    apiKeysTableBody.innerHTML = '<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 14px;">No Storyblocks API keys generated yet.</td></tr>';
    return;
  }

  apiKeys.forEach(k => {
    const tr = document.createElement('tr');
    const statusClass = k.status === 'active' ? 'active' : (k.status === 'expired' ? 'expired' : 'revoked');
    const limitLabel = k.daily_limit > 0 ? `${k.daily_limit} / day` : 'Unlimited';

    tr.innerHTML = `
      <td><strong>${escapeHtml(k.client_name)}</strong></td>
      <td><code title="Click to copy" style="cursor: pointer;" onclick="navigator.clipboard.writeText('${k.api_key}'); showToast('API Key copied!');">${escapeHtml(k.api_key)}</code></td>
      <td>
        <span style="color: #38bdf8; font-weight: 700;">${limitLabel}</span>
        <button class="btn-table-action" style="margin-left: 4px; padding: 1px 4px; font-size: 9px;" onclick="updateApiKeyLimitPrompt('${k.api_key}', ${k.daily_limit})" title="Change Daily Limit"><i class="fa-solid fa-pen"></i></button>
      </td>
      <td>${k.requests_today}</td>
      <td>${k.total_requests}</td>
      <td>${escapeHtml(k.expires_at.split(' ')[0])}</td>
      <td><span class="status-pill ${statusClass}">${k.status}</span></td>
      <td>
        ${k.status === 'active' ? 
          `<button class="btn-table-action" onclick="revokeApiKeyAction('${k.api_key}')" title="Revoke API Key"><i class="fa-solid fa-ban"></i> Revoke</button>` : 
          `<button class="btn-table-action" onclick="deleteApiKeyAction(${k.id})" title="Delete API Key"><i class="fa-solid fa-trash"></i> Delete</button>`
        }
      </td>
    `;
    apiKeysTableBody.appendChild(tr);
  });
}

window.updateApiKeyLimitPrompt = async function(key, currentLimit) {
  const newLimitStr = prompt(`Enter new Daily Request Limit for key ${key} (0 for Unlimited):`, currentLimit);
  if (newLimitStr === null) return;
  const newLimit = parseInt(newLimitStr, 10);
  if (isNaN(newLimit) || newLimit < 0) {
    alert('Please enter a valid positive number or 0 for unlimited.');
    return;
  }
  try {
    const res = await fetch('/api/admin/update-api-key-limit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password: state.adminPassword, api_key: key, daily_limit: newLimit })
    });
    const data = await res.json();
    if (data.success) {
      showToast(`Daily limit updated to ${newLimit > 0 ? newLimit + ' req/day' : 'Unlimited'}`);
      loadAdminApiKeys();
    }
  } catch (e) {
    showToast('Error updating limit');
  }
};

window.revokeApiKeyAction = async function(key) {
  if (!confirm(`Are you sure you want to revoke Storyblocks API key ${key}?`)) return;
  try {
    const res = await fetch('/api/admin/revoke-api-key', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password: state.adminPassword, api_key: key })
    });
    const data = await res.json();
    if (data.success) {
      showToast('API Key revoked');
      loadAdminApiKeys();
    }
  } catch (e) {
    showToast('Error revoking API key');
  }
};

window.deleteApiKeyAction = async function(id) {
  try {
    const res = await fetch('/api/admin/delete-api-key', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password: state.adminPassword, api_key_id: id })
    });
    const data = await res.json();
    if (data.success) {
      showToast('API key deleted');
      loadAdminApiKeys();
    }
  } catch (e) {
    showToast('Error deleting API key');
  }
};

window.revokeLicense = async function(key) {
  if (!confirm(`Are you sure you want to revoke key ${key}?`)) return;
  try {
    const res = await fetch('/api/admin/revoke-license', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password: state.adminPassword, license_key: key })
    });
    const data = await res.json();
    if (data.success) {
      showToast('License revoked');
      loadAdminLicenses();
    }
  } catch (e) {
    showToast('Error revoking license');
  }
};

window.deleteLicense = async function(id) {
  try {
    const res = await fetch('/api/admin/delete-license', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password: state.adminPassword, license_id: id })
    });
    const data = await res.json();
    if (data.success) {
      showToast('License deleted');
      loadAdminLicenses();
    }
  } catch (e) {
    showToast('Error deleting license');
  }
};

// --- SEARCH & MEDIA RENDERING ---

function triggerSearch(query) {
  state.query = query;
  state.page = 1;
  state.results = [];
  searchInput.value = query;
  clearSearchBtn.style.display = 'block';
  fetchVideos(true);
}

async function fetchVideos(isNewSearch = true) {
  if (state.isLoading) return;
  state.isLoading = true;

  if (isNewSearch) {
    state.page = 1;
    videoGrid.innerHTML = '';
    welcomeState.classList.add('hidden');
    noResultsState.classList.add('hidden');
    loadMoreWrapper.classList.add('hidden');
    loadingState.classList.remove('hidden');
    statsBadge.textContent = 'Searching...';
  } else {
    loadMoreBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Loading...';
  }

  const params = new URLSearchParams({
    keywords: state.query,
    provider: state.provider,
    page: state.page,
    num_results: 24,
    orientation: state.orientation,
    sort: state.sort
  });

  try {
    const response = await fetch(`/api/search?${params.toString()}`);
    const data = await response.json();

    loadingState.classList.add('hidden');
    loadMoreBtn.innerHTML = '<i class="fa-solid fa-angles-down"></i> Load More Videos';

    if (data.success && data.results && data.results.length > 0) {
      if (isNewSearch) {
        state.results = data.results;
      } else {
        state.results = state.results.concat(data.results);
      }
      state.total = data.total || state.results.length;
      state.page++;

      renderVideoCards(data.results, isNewSearch);
      statsBadge.textContent = `${state.results.length}+ Videos Found`;
      loadMoreWrapper.classList.remove('hidden');
    } else {
      if (isNewSearch) {
        noResultsState.classList.remove('hidden');
        statsBadge.textContent = '0 Videos Found';
      } else {
        loadMoreWrapper.classList.add('hidden');
        showToast('No more videos available');
      }
    }
  } catch (err) {
    console.error('Fetch error:', err);
    loadingState.classList.add('hidden');
    if (isNewSearch) {
      noResultsState.classList.remove('hidden');
    }
    showToast('Failed to load videos. Please retry.');
  } finally {
    state.isLoading = false;
  }
}

function renderVideoCards(videos, isNewSearch) {
  if (isNewSearch) {
    videoGrid.innerHTML = '';
  }

  videos.forEach(video => {
    const card = createVideoCard(video);
    videoGrid.appendChild(card);
  });
}

function createVideoCard(video) {
  const card = document.createElement('div');
  card.className = 'video-card';
  card.dataset.id = video.id;

  const durationText = formatDuration(video.duration);
  const badge4k = video.has_4k ? '<span class="badge badge-4k">4K UHD</span>' : '';
  const badgeHd = (!video.has_4k && video.has_hd) ? '<span class="badge badge-hd">HD</span>' : '';

  card.innerHTML = `
    <div class="card-media-wrapper" title="Click for details & formats">
      <img class="card-thumbnail" src="${video.thumbnail || ''}" alt="${escapeHtml(video.title)}" loading="lazy" />
      <video class="card-video" src="${video.preview_video || ''}" muted loop playsinline controlsList="nodownload" oncontextmenu="return false;" disablePictureInPicture></video>
      <div class="card-badges-top">
        ${badge4k || badgeHd ? `<div>${badge4k}${badgeHd}</div>` : ''}
      </div>
      <div class="card-duration">
        <i class="fa-solid fa-clock"></i> ${durationText}
      </div>
      <div class="card-play-overlay">
        <i class="fa-solid fa-play"></i>
      </div>
    </div>
    <div class="card-body">
      <h3 class="card-title" title="${escapeHtml(video.title)}">${escapeHtml(video.title)}</h3>
      <div class="card-actions">
        <button class="btn-card-download" title="1-Click Direct Download Original 1080p Full HD">
          <i class="fa-solid fa-download"></i> Download 1080p
        </button>
        <button class="btn-card-options" title="More Original Qualities (4K, 720p)">
          <i class="fa-solid fa-sliders"></i>
        </button>
      </div>
    </div>
  `;

  // Hover video preview playback
  const mediaWrapper = card.querySelector('.card-media-wrapper');
  const videoEl = card.querySelector('.card-video');

  mediaWrapper.addEventListener('mouseenter', () => {
    if (videoEl && video.preview_video) {
      videoEl.currentTime = 0;
      const playPromise = videoEl.play();
      if (playPromise !== undefined) {
        playPromise.catch(() => {});
      }
    }
  });

  mediaWrapper.addEventListener('mouseleave', () => {
    if (videoEl) {
      videoEl.pause();
    }
  });

  // Click card or options button to open modal
  mediaWrapper.addEventListener('click', () => openModal(video));
  card.querySelector('.btn-card-options').addEventListener('click', () => openModal(video));

  // Quick download button (1-click direct download 1080p)
  card.querySelector('.btn-card-download').addEventListener('click', async (e) => {
    e.stopPropagation();
    e.preventDefault();
    handleQuickDownload(video);
  });

  return card;
}

async function handleQuickDownload(video) {
  showToast(`Downloading 1080p for "${video.title}"...`);
  try {
    const details = await fetchVideoDetails(video.id, video.provider_type);
    if (details.success && details.downloads && details.downloads.length > 0) {
      const mp4Options = details.downloads.filter(d => (d.format || 'MP4').toUpperCase() === 'MP4');
      
      const opt1080p = mp4Options.find(d => d.resolution.toString().includes('1080')) || 
                       mp4Options.find(d => d.resolution.toString().includes('2160') || d.resolution.toString().includes('4k')) ||
                       mp4Options[0] || 
                       details.downloads[0];

      const cleanName = `${sanitizeFilename(video.title)}-${opt1080p.resolution || '1080p'}.mp4`;
      triggerDirectDownload(opt1080p.download_url, cleanName);
    } else if (video.preview_video) {
      triggerDirectDownload(video.preview_video, `${sanitizeFilename(video.title)}-1080p.mp4`);
    } else {
      showToast('Download link unavailable.');
    }
  } catch (err) {
    console.error('Download error:', err);
    if (video.preview_video) {
      triggerDirectDownload(video.preview_video, `${sanitizeFilename(video.title)}-1080p.mp4`);
    }
  }
}

async function openModal(video) {
  state.activeVideo = video;
  modalTitle.textContent = video.title;
  modalVideoPlayer.src = video.preview_video || '';
  modalVideoPlayer.play().catch(() => {});

  const badge4k = video.has_4k ? '<span class="badge badge-4k">4K UHD</span>' : '';
  const badgeHd = video.has_hd ? '<span class="badge badge-hd">HD</span>' : '';
  const providerClass = video.provider_type || 'flexclip';
  const providerLabel = video.provider_type === 'flexclip' ? 'Storyblocks' : (video.provider || 'StockStream');
  modalBadges.innerHTML = `
    <span class="badge badge-provider ${providerClass}">${providerLabel}</span>
    ${badge4k}${badgeHd}
    <span class="badge badge-provider"><i class="fa-solid fa-clock"></i> ${formatDuration(video.duration)}</span>
  `;

  modalDownloadOptions.innerHTML = '<div style="color: var(--text-secondary); padding: 12px;"><i class="fa-solid fa-spinner fa-spin"></i> Fetching high-quality download links...</div>';
  videoModal.classList.remove('hidden');

  try {
    const details = await fetchVideoDetails(video.id, video.provider_type);
    if (details.success && details.downloads && details.downloads.length > 0) {
      renderDownloadOptions(details.downloads, video.title);
    } else {
      modalDownloadOptions.innerHTML = `
        <button class="download-option-btn primary" onclick="triggerDirectDownload('${video.preview_video}', '${sanitizeFilename(video.title)}-1080p.mp4')">
          <div class="option-res-name"><span>Download 1080p Full HD (MP4)</span> <i class="fa-solid fa-download"></i></div>
          <div class="option-details">Instant High Quality MP4 Download</div>
        </button>
      `;
    }
  } catch (e) {
    modalDownloadOptions.innerHTML = '<div style="color: #ef4444;">Failed to load download formats.</div>';
  }
}

function renderDownloadOptions(downloads, title) {
  modalDownloadOptions.innerHTML = '';

  const opt1080p = downloads.find(d => d.resolution.toString().includes('1080') && (d.format || 'MP4').toUpperCase() === 'MP4');
  const otherOptions = downloads.filter(d => d !== opt1080p);

  if (opt1080p) {
    const primaryBtn = document.createElement('button');
    primaryBtn.className = 'download-option-btn primary featured-1080p';
    const filename = `${sanitizeFilename(title)}-1080p.mp4`;
    primaryBtn.innerHTML = `
      <div class="option-res-name">
        <span><i class="fa-solid fa-star"></i> Download 1080p Full HD (Recommended)</span>
        <i class="fa-solid fa-download"></i>
      </div>
      <div class="option-details">Best for YouTube, Editing & Social Media • Instant MP4</div>
    `;
    primaryBtn.addEventListener('click', () => {
      triggerDirectDownload(opt1080p.download_url, filename);
    });
    modalDownloadOptions.appendChild(primaryBtn);
  }

  if (otherOptions.length > 0) {
    const subHeading = document.createElement('div');
    subHeading.className = 'modal-other-title';
    subHeading.innerHTML = `<span>Other Available Resolutions (${otherOptions.length}):</span>`;
    modalDownloadOptions.appendChild(subHeading);

    const otherGrid = document.createElement('div');
    otherGrid.className = 'download-other-grid';

    otherOptions.forEach(dl => {
      const btn = document.createElement('button');
      btn.className = 'download-option-btn secondary';
      const filename = `${sanitizeFilename(title)}-${dl.resolution}.${(dl.format || 'MP4').toLowerCase()}`;
      
      btn.innerHTML = `
        <div class="option-res-name">
          <span>${escapeHtml(dl.label)}</span>
          <i class="fa-solid fa-download"></i>
        </div>
        <div class="option-details">${dl.format || 'MP4'} Format</div>
      `;

      btn.addEventListener('click', () => {
        triggerDirectDownload(dl.download_url, filename);
      });

      otherGrid.appendChild(btn);
    });

    modalDownloadOptions.appendChild(otherGrid);
  }
}

async function fetchVideoDetails(id, provider) {
  const res = await fetch(`/api/video-details?id=${encodeURIComponent(id)}&provider=${encodeURIComponent(provider)}`);
  return await res.json();
}

function triggerDirectDownload(streamUrl, filename) {
  showToast(`Downloading: ${filename}`);
  const proxyUrl = `/api/download?url=${encodeURIComponent(streamUrl)}&filename=${encodeURIComponent(filename)}`;
  
  const link = document.createElement('a');
  link.href = proxyUrl;
  link.setAttribute('download', filename);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

function closeModal() {
  modalVideoPlayer.pause();
  modalVideoPlayer.src = '';
  videoModal.classList.add('hidden');
  state.activeVideo = null;
}

// Helpers
function formatDuration(sec) {
  if (!sec || isNaN(sec)) return '00:10';
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function sanitizeFilename(str) {
  if (!str) return 'stock-video';
  return str.replace(/[^a-zA-Z0-9_-]/g, '_').substring(0, 40);
}

let toastTimer = null;
function showToast(msg) {
  toastMessage.textContent = msg;
  toast.classList.remove('hidden');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    toast.classList.add('hidden');
  }, 3500);
}
