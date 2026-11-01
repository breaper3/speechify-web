/**
 * Speechify Local - Neural Reader Engine & Visual PDF Synchronizer
 */

// Application State
const state = {
  document: null,          // { doc_id, is_pdf, title, total_sentences, total_words, sentences, pages, paragraphs }
  currentIndex: 0,         // Current active sentence index
  isPlaying: false,        // Audio playing state
  viewMode: 'pdf',         // 'pdf' or 'text'
  voice: 'af_heart',       // Default Kokoro voice
  speed: 1.0,              // Playback rate
  pdfZoom: 1.0,            // PDF scaling factor
  audioBlobCache: new Map(), // sentenceIndex -> blobUrl
  fontSize: 20,            // Base reader font size in px
  isDockMinimized: false,  // Minimized floating dock
  search: {
    query: '',
    matches: [],
    currentIndex: -1,
    activeSentenceId: null,
    isOpen: false
  }
};

// DOM Elements
const audio = document.getElementById('audioPlayer');
const pdfViewer = document.getElementById('pdfViewer');
const readerContent = document.getElementById('readerContent');
const emptyState = document.getElementById('emptyState');
const docHeaderTitle = document.getElementById('docHeaderTitle');
const docHeaderStats = document.getElementById('docHeaderStats');
const hardwareBadge = document.getElementById('hardwareBadge');
const hardwareText = document.getElementById('hardwareText');
const btnFullscreen = document.getElementById('btnFullscreen');

// Search Elements
const searchBar = document.getElementById('searchBar');
const searchInput = document.getElementById('searchInput');
const searchCount = document.getElementById('searchCount');
const btnOpenSearch = document.getElementById('btnOpenSearch');
const btnCloseSearch = document.getElementById('btnCloseSearch');
const btnSearchPrev = document.getElementById('btnSearchPrev');
const btnSearchNext = document.getElementById('btnSearchNext');
const btnSearchPlay = document.getElementById('btnSearchPlay');

// View Toggle
const viewModeToggle = document.getElementById('viewModeToggle');
const btnViewPdf = document.getElementById('btnViewPdf');
const btnViewText = document.getElementById('btnViewText');
const btnMobileViewToggle = document.getElementById('btnMobileViewToggle');
const btnMobileMenu = document.getElementById('btnMobileMenu');

// Transport Controls & Desktop Dock
const playerDock = document.getElementById('playerDock');
const btnMinimizeDock = document.getElementById('btnMinimizeDock');
const btnExpandDock = document.getElementById('btnExpandDock');
const dockMinimizedBar = document.getElementById('dockMinimizedBar');
const btnMiniPlayPause = document.getElementById('btnMiniPlayPause');
const miniPlayIcon = document.getElementById('miniPlayIcon');
const miniPauseIcon = document.getElementById('miniPauseIcon');
const miniSentenceCounter = document.getElementById('miniSentenceCounter');

const btnPlayPause = document.getElementById('btnPlayPause');
const playIcon = document.getElementById('playIcon');
const pauseIcon = document.getElementById('pauseIcon');
const btnPrev = document.getElementById('btnPrev');
const btnNext = document.getElementById('btnNext');
const sentenceCounter = document.getElementById('sentenceCounter');
const remainingTime = document.getElementById('remainingTime');
const dockProgressBar = document.getElementById('dockProgressBar');
const dockProgressTrack = document.getElementById('dockProgressTrack');

// Settings & Speed Gauge
const voiceSelect = document.getElementById('voiceSelect');
const speedThumbTooltip = document.getElementById('speedThumbTooltip');
const speedGaugeSlider = document.getElementById('speedGaugeSlider');
const speedGaugeFill = document.getElementById('speedGaugeFill');
const speedGaugeVal = document.getElementById('speedGaugeVal');
const btnSpeedDown = document.getElementById('btnSpeedDown');
const btnSpeedUp = document.getElementById('btnSpeedUp');
const btnSpeedGaugePill = document.getElementById('btnSpeedGaugePill');
const speedPopover = document.getElementById('speedPopover');
const btnCloseSpeedPopover = document.getElementById('btnCloseSpeedPopover');
const popoverLargeVal = document.getElementById('popoverLargeVal');
const popoverWpmVal = document.getElementById('popoverWpmVal');
const popoverSpeedSlider = document.getElementById('popoverSpeedSlider');
const speedPresetChips = document.querySelectorAll('.speed-preset-chip');
const btnThemeToggle = document.getElementById('btnThemeToggle');
const themeIcon = document.getElementById('themeIcon');
const btnZoomIn = document.getElementById('btnZoomIn');
const btnZoomOut = document.getElementById('btnZoomOut');

// Mobile Mini-Player Bar Elements
const dockMobileBar = document.getElementById('dockMobileBar');
const btnMobileMiniPlay = document.getElementById('btnMobileMiniPlay');
const miniMobilePlayIcon = document.getElementById('miniMobilePlayIcon');
const miniMobilePauseIcon = document.getElementById('miniMobilePauseIcon');
const mobileMiniInfo = document.getElementById('mobileMiniInfo');
const mobileMiniDocTitle = document.getElementById('mobileMiniDocTitle');
const mobileMiniSnippet = document.getElementById('mobileMiniSnippet');
const mobileMiniSpeedPill = document.getElementById('mobileMiniSpeedPill');
const btnMobileMiniExpand = document.getElementById('btnMobileMiniExpand');

// Mobile Expanded Player Sheet Elements
const mobileSheetOverlay = document.getElementById('mobileSheetOverlay');
const mobilePlayerSheet = document.getElementById('mobilePlayerSheet');
const sheetDragHandle = document.getElementById('sheetDragHandle');
const btnCollapseMobileSheet = document.getElementById('btnCollapseMobileSheet');
const mobileSheetDocTitle = document.getElementById('mobileSheetDocTitle');
const mobileSheetDocStats = document.getElementById('mobileSheetDocStats');
const mobileSentenceCard = document.getElementById('mobileSentenceCard');
const mobileCurrentSentenceText = document.getElementById('mobileCurrentSentenceText');
const mobileScrubberTrack = document.getElementById('mobileScrubberTrack');
const mobileScrubberFill = document.getElementById('mobileScrubberFill');
const mobileScrubberSentence = document.getElementById('mobileScrubberSentence');
const mobileScrubberTime = document.getElementById('mobileScrubberTime');
const btnMobilePrev = document.getElementById('btnMobilePrev');
const btnMobilePlayPause = document.getElementById('btnMobilePlayPause');
const mobileSheetPlayIcon = document.getElementById('mobileSheetPlayIcon');
const mobileSheetPauseIcon = document.getElementById('mobileSheetPauseIcon');
const btnMobileNext = document.getElementById('btnMobileNext');
const mobileSheetSpeedBadge = document.getElementById('mobileSheetSpeedBadge');
const mobileSheetSpeedSlider = document.getElementById('mobileSheetSpeedSlider');
const speedChipsM = document.querySelectorAll('.speed-chip-m');
const mobileSheetVoiceSelect = document.getElementById('mobileSheetVoiceSelect');

// Mobile Actions Drawer Elements
const mobileDrawerOverlay = document.getElementById('mobileDrawerOverlay');
const btnCloseMobileDrawer = document.getElementById('btnCloseMobileDrawer');
const mobileDrawerHardware = document.getElementById('mobileDrawerHardware');
const btnDrawerSamplePdf = document.getElementById('btnDrawerSamplePdf');
const btnDrawerImport = document.getElementById('btnDrawerImport');
const btnDrawerSearch = document.getElementById('btnDrawerSearch');
const btnDrawerTheme = document.getElementById('btnDrawerTheme');
const drawerThemeIcon = document.getElementById('drawerThemeIcon');
const btnDrawerViewToggle = document.getElementById('btnDrawerViewToggle');
const drawerViewModeDesc = document.getElementById('drawerViewModeDesc');
const btnDrawerFullscreen = document.getElementById('btnDrawerFullscreen');
const btnDrawerZoomOut = document.getElementById('btnDrawerZoomOut');
const btnDrawerZoomIn = document.getElementById('btnDrawerZoomIn');

// Modal Elements
const importModal = document.getElementById('importModal');
const btnOpenImport = document.getElementById('btnOpenImport');
const btnEmptyImport = document.getElementById('btnEmptyImport');
const btnCloseModal = document.getElementById('btnCloseModal');
const tabButtons = document.querySelectorAll('.tab-btn');
const tabPanels = document.querySelectorAll('.tab-panel');
const pasteTitle = document.getElementById('pasteTitle');
const pasteContent = document.getElementById('pasteContent');
const btnSubmitPaste = document.getElementById('btnSubmitPaste');
const btnSamplePdf = document.getElementById('btnSamplePdf');
const btnEmptyPdf = document.getElementById('btnEmptyPdf');
const btnSamplePdfInModal = document.getElementById('btnSamplePdfInModal');
const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('fileInput');
const fileStatus = document.getElementById('fileStatus');
const fileName = document.getElementById('fileName');

// Library & Sharing DOM Elements
const btnLibrary = document.getElementById('btnLibrary');
const libraryBadgeCount = document.getElementById('libraryBadgeCount');
const btnShareDoc = document.getElementById('btnShareDoc');
const libraryModal = document.getElementById('libraryModal');
const btnCloseLibraryModal = document.getElementById('btnCloseLibraryModal');
const librarySearchInput = document.getElementById('librarySearchInput');
const btnLibraryNewUpload = document.getElementById('btnLibraryNewUpload');
const libraryListContainer = document.getElementById('libraryListContainer');
const shareModal = document.getElementById('shareModal');
const btnCloseShareModal = document.getElementById('btnCloseShareModal');
const shareLinkInput = document.getElementById('shareLinkInput');
const btnCopyShareLink = document.getElementById('btnCopyShareLink');
const shareToast = document.getElementById('shareToast');

// Auth DOM Elements
const btnTriggerGoogleSignIn = document.getElementById('btnTriggerGoogleSignIn');
const userPill = document.getElementById('userPill');
const userAvatar = document.getElementById('userAvatar');
const userName = document.getElementById('userName');
const btnSignOut = document.getElementById('btnSignOut');
const gSignInContainer = document.getElementById('gSignInContainer');
const libraryAccountStatus = document.getElementById('libraryAccountStatus');

// Progress sync timer
let progressSyncTimer = null;

// ==================== IndexedDB Local-First Persistence ====================
const DB_NAME = 'speechify_local_db';
const DB_VERSION = 1;
let idb = null;

function initIndexedDB() {
  return new Promise((resolve) => {
    try {
      const req = indexedDB.open(DB_NAME, DB_VERSION);
      req.onupgradeneeded = (e) => {
        const db = e.target.result;
        if (!db.objectStoreNames.contains('documents')) {
          const store = db.createObjectStore('documents', { keyPath: 'doc_id' });
          store.createIndex('last_read_at', 'last_read_at', { unique: false });
        }
      };
      req.onsuccess = (e) => {
        idb = e.target.result;
        resolve(idb);
      };
      req.onerror = () => {
        console.warn('[IndexedDB] Database open error, using localStorage fallback');
        resolve(null);
      };
    } catch (err) {
      console.warn('[IndexedDB] Initialization error:', err);
      resolve(null);
    }
  });
}

function idbSaveDocument(doc) {
  if (!doc || !doc.doc_id) return Promise.resolve();
  const record = {
    doc_id: doc.doc_id,
    title: doc.title || 'Untitled Document',
    filename: doc.filename || (doc.title + (doc.is_pdf ? '.pdf' : '.txt')),
    is_pdf: !!doc.is_pdf,
    total_sentences: doc.total_sentences || (doc.sentences ? doc.sentences.length : 0),
    total_words: doc.total_words || 0,
    est_minutes: doc.est_minutes || 0,
    current_sentence_index: doc.current_sentence_index || 0,
    current_page: doc.current_page || 0,
    speed: doc.speed || state.speed || 1.0,
    voice: doc.voice || state.voice || 'af_heart',
    last_read_at: Date.now(),
    doc_data: doc
  };

  try {
    localStorage.setItem('speechify_last_active_doc_id', doc.doc_id);
  } catch (e) {}

  if (!idb) return Promise.resolve();
  return new Promise((resolve) => {
    try {
      const tx = idb.transaction(['documents'], 'readwrite');
      tx.objectStore('documents').put(record);
      tx.oncomplete = () => resolve(true);
      tx.onerror = () => resolve(false);
    } catch (e) {
      resolve(false);
    }
  });
}

function idbGetDocument(docId) {
  if (!idb || !docId) return Promise.resolve(null);
  return new Promise((resolve) => {
    try {
      const tx = idb.transaction(['documents'], 'readonly');
      const req = tx.objectStore('documents').get(docId);
      req.onsuccess = () => resolve(req.result || null);
      req.onerror = () => resolve(null);
    } catch (e) {
      resolve(null);
    }
  });
}

function idbListDocuments() {
  if (!idb) return Promise.resolve([]);
  return new Promise((resolve) => {
    try {
      const tx = idb.transaction(['documents'], 'readonly');
      const req = tx.objectStore('documents').getAll();
      req.onsuccess = () => {
        const list = req.result || [];
        list.sort((a, b) => (b.last_read_at || 0) - (a.last_read_at || 0));
        resolve(list);
      };
      req.onerror = () => resolve([]);
    } catch (e) {
      resolve([]);
    }
  });
}

function idbUpdateProgress(docId, sentenceIndex, pageNum, speed, voice) {
  if (!docId) return;
  idbGetDocument(docId).then((rec) => {
    if (rec) {
      rec.current_sentence_index = sentenceIndex;
      rec.current_page = pageNum;
      rec.last_read_at = Date.now();
      if (speed) rec.speed = speed;
      if (voice) rec.voice = voice;
      if (rec.doc_data) {
        rec.doc_data.current_sentence_index = sentenceIndex;
        rec.doc_data.current_page = pageNum;
      }
      idbSaveDocument(rec.doc_data);
    }
  });
}

function idbDeleteDocument(docId) {
  if (!idb || !docId) return Promise.resolve();
  return new Promise((resolve) => {
    try {
      const tx = idb.transaction(['documents'], 'readwrite');
      tx.objectStore('documents').delete(docId);
      tx.oncomplete = () => resolve(true);
      tx.onerror = () => resolve(false);
    } catch (e) {
      resolve(false);
    }
  });
}

// ==================== User & Google Authentication ====================
let currentUser = null;
let googleClientId = '';

async function checkAuthSession() {
  try {
    const res = await fetch('/api/auth/me');
    if (res.ok) {
      const data = await res.json();
      if (data.authenticated && data.user) {
        setLoggedInUser(data.user);
        return;
      }
    }
  } catch (e) {}
  setLoggedOutUser();
}

function setLoggedInUser(user) {
  currentUser = user;
  if (gSignInContainer) gSignInContainer.classList.add('hidden');
  if (userPill) userPill.classList.remove('hidden');
  if (userAvatar) userAvatar.src = user.picture || 'https://www.gstatic.com/images/branding/product/1x/avatar_square_grey_512dp.png';
  if (userName) userName.textContent = user.name || user.email.split('@')[0];
  if (libraryAccountStatus) libraryAccountStatus.textContent = `Signed in as ${user.email} (Cloud Sync Active)`;

  refreshLibraryBadge();
}

function setLoggedOutUser() {
  currentUser = null;
  if (gSignInContainer) gSignInContainer.classList.remove('hidden');
  if (userPill) userPill.classList.add('hidden');
  if (libraryAccountStatus) libraryAccountStatus.textContent = 'Local Guest Library (Sign in to sync across devices)';

  refreshLibraryBadge();
}

async function initGoogleSignIn() {
  try {
    const cfgRes = await fetch('/api/auth/config');
    if (cfgRes.ok) {
      const cfg = await cfgRes.json();
      googleClientId = cfg.client_id;
    }
  } catch (e) {}

  let attempts = 0;
  const checkGsi = setInterval(() => {
    attempts++;
    if (window.google && google.accounts && google.accounts.id) {
      clearInterval(checkGsi);
      setupGsi();
    } else if (attempts > 30) {
      clearInterval(checkGsi);
    }
  }, 250);
}

function setupGsi() {
  if (!window.google || !google.accounts || !google.accounts.id) return;
  const clientIdToUse = googleClientId || 'YOUR_GOOGLE_CLIENT_ID.apps.googleusercontent.com';

  google.accounts.id.initialize({
    client_id: clientIdToUse,
    callback: handleGoogleCredentialResponse,
    ux_mode: 'popup',
    auto_select: false,
    itp_support: true,
    use_fedcm_for_prompt: true,
    use_fedcm_for_button: true,
    context: 'signin'
  });

  const hiddenWrapper = document.getElementById('hiddenGsiWrapper');
  if (hiddenWrapper) {
    google.accounts.id.renderButton(hiddenWrapper, {
      type: 'standard',
      theme: 'outline',
      size: 'medium'
    });
  }
}

function triggerGoogleSignIn() {
  if (!googleClientId) {
    const entered = prompt(
      "Sign in with Google requires a Google OAuth Client ID.\n\n" +
      "If you have created a Client ID in Google Cloud Console, enter it here:\n" +
      "(or set GOOGLE_CLIENT_ID on Render):"
    );
    if (entered && entered.trim()) {
      googleClientId = entered.trim();
      setupGsi();
      setTimeout(() => {
        if (window.google && google.accounts && google.accounts.id) {
          google.accounts.id.prompt();
        }
      }, 300);
    }
    return;
  }

  if (window.google && google.accounts && google.accounts.id) {
    google.accounts.id.prompt((notification) => {
      if (notification.isNotDisplayed() || notification.isSkippedMoment()) {
        const hiddenWrapper = document.getElementById('hiddenGsiWrapper');
        const renderedBtn = hiddenWrapper ? hiddenWrapper.querySelector('[role="button"]') : null;
        if (renderedBtn) renderedBtn.click();
      }
    });
  }
}

async function handleGoogleCredentialResponse(response) {
  if (!response || !response.credential) return;
  try {
    const res = await fetch('/api/auth/google', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ credential: response.credential })
    });
    if (res.ok) {
      const data = await res.json();
      setLoggedInUser(data.user);
    } else {
      const err = await res.json();
      alert('Sign-in error: ' + (err.detail || 'Verification failed'));
    }
  } catch (err) {
    alert('Could not complete Google Sign-in: ' + err.message);
  }
}

async function handleLogout() {
  try {
    await fetch('/api/auth/logout', { method: 'POST' });
  } catch (e) {}
  setLoggedOutUser();
}

// ==================== Document Library & Sharing ====================

async function refreshLibraryBadge() {
  const localDocs = await idbListDocuments();
  let count = localDocs.length;
  try {
    const res = await fetch('/api/documents');
    if (res.ok) {
      const data = await res.json();
      const serverDocs = data.documents || [];
      const ids = new Set(localDocs.map(d => d.doc_id));
      serverDocs.forEach(d => ids.add(d.doc_id));
      count = ids.size;
    }
  } catch (e) {}

  if (libraryBadgeCount) {
    libraryBadgeCount.textContent = count;
  }
}

function openLibrary() {
  if (libraryModal) libraryModal.classList.remove('hidden');
  renderLibraryList();
}

function closeLibrary() {
  if (libraryModal) libraryModal.classList.add('hidden');
}

function formatTimeAgo(ms) {
  if (!ms) return 'Recently';
  const diff = Date.now() - ms;
  const mins = Math.floor(diff / 60000);
  if (mins < 2) return 'Just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

async function renderLibraryList(query = '') {
  if (!libraryListContainer) return;
  libraryListContainer.innerHTML = '<div style="text-align:center;padding:30px;color:var(--text-muted);">Loading library...</div>';

  let serverDocs = [];
  try {
    const res = await fetch('/api/documents');
    if (res.ok) {
      const data = await res.json();
      serverDocs = data.documents || [];
    }
  } catch (e) {}

  const localDocs = await idbListDocuments();

  const mergedMap = new Map();
  serverDocs.forEach(d => mergedMap.set(d.doc_id, d));
  localDocs.forEach(d => {
    if (!mergedMap.has(d.doc_id)) {
      mergedMap.set(d.doc_id, d);
    } else {
      const existing = mergedMap.get(d.doc_id);
      if ((d.last_read_at || 0) > (existing.last_read_at || 0)) {
        existing.current_sentence_index = d.current_sentence_index;
        existing.current_page = d.current_page;
        existing.last_read_at = d.last_read_at;
      }
    }
  });

  let allDocs = Array.from(mergedMap.values());
  allDocs.sort((a, b) => (b.last_read_at || 0) - (a.last_read_at || 0));

  if (query && query.trim()) {
    const q = query.toLowerCase();
    allDocs = allDocs.filter(d => (d.title || '').toLowerCase().includes(q) || (d.filename || '').toLowerCase().includes(q));
  }

  if (libraryBadgeCount) libraryBadgeCount.textContent = allDocs.length;

  if (allDocs.length === 0) {
    libraryListContainer.innerHTML = `
      <div class="library-empty-state">
        <div class="library-empty-icon">📚</div>
        <h4>No Documents in Library</h4>
        <p>Import a PDF or text file to start reading. Your progress is saved automatically.</p>
      </div>
    `;
    return;
  }

  libraryListContainer.innerHTML = '';
  allDocs.forEach(doc => {
    const isPdf = !!doc.is_pdf;
    const isActive = state.document && state.document.doc_id === doc.doc_id;
    const curIdx = doc.current_sentence_index || 0;
    const totalS = doc.total_sentences || 1;
    const pct = Math.min(100, Math.round((curIdx / Math.max(1, totalS)) * 100));
    const timeAgo = formatTimeAgo(doc.last_read_at);

    const card = document.createElement('div');
    card.className = `library-doc-card ${isActive ? 'active-doc' : ''}`;
    card.innerHTML = `
      <div class="library-card-icon ${isPdf ? 'pdf-icon' : ''}">
        ${isPdf ? 'PDF' : 'TXT'}
      </div>
      <div class="library-card-body">
        <div class="library-card-title-row">
          <span class="library-card-title">${escapeHtml(doc.title)}</span>
          ${isActive ? '<span class="library-active-badge">Reading</span>' : ''}
        </div>
        <div class="library-card-meta">
          <span>${pct}% read · Sentence ${curIdx + 1}/${totalS}</span>
          ${isPdf ? `<span>Page ${(doc.current_page || 0) + 1}</span>` : ''}
          <span>${doc.total_words || 0} words</span>
          <span>${timeAgo}</span>
        </div>
        <div class="library-progress-track">
          <div class="library-progress-bar" style="width: ${pct}%"></div>
        </div>
      </div>
      <div class="library-card-actions">
        <button class="btn-library-action btn-action-resume" title="Resume reading">
          ▶ Resume
        </button>
        <button class="btn-library-action btn-action-share" title="Share link">
          🔗 Share
        </button>
        <button class="btn-library-action btn-action-delete" title="Delete from library">
          🗑
        </button>
      </div>
    `;

    card.querySelector('.btn-action-resume').addEventListener('click', (e) => {
      e.stopPropagation();
      loadSavedDocument(doc.doc_id);
    });

    card.addEventListener('click', () => {
      loadSavedDocument(doc.doc_id);
    });

    card.querySelector('.btn-action-share').addEventListener('click', (e) => {
      e.stopPropagation();
      openShareModal(doc.doc_id);
    });

    card.querySelector('.btn-action-delete').addEventListener('click', async (e) => {
      e.stopPropagation();
      if (confirm(`Remove "${doc.title}" from your library?`)) {
        await deleteSavedDocument(doc.doc_id);
        renderLibraryList(librarySearchInput ? librarySearchInput.value : '');
      }
    });

    libraryListContainer.appendChild(card);
  });
}

async function loadSavedDocument(docId) {
  closeLibrary();

  // 1. Check local IndexedDB first for instant startup
  const localRec = await idbGetDocument(docId);
  if (localRec && localRec.doc_data) {
    renderDocument(localRec.doc_data);
    if (localRec.current_sentence_index > 0) {
      setTimeout(() => jumpToSentence(localRec.current_sentence_index, false), 150);
    }
  }

  // 2. Fetch from server to sync latest server progress
  try {
    const res = await fetch(`/api/documents/${docId}`);
    if (res.ok) {
      const serverDoc = await res.json();
      renderDocument(serverDoc);
      const resumeIndex = serverDoc.current_sentence_index || 0;
      if (resumeIndex > 0) {
        setTimeout(() => jumpToSentence(resumeIndex, false), 150);
      }
    }
  } catch (err) {
    console.warn('[Doc Load] Server fetch fallback:', err);
  }
}

async function deleteSavedDocument(docId) {
  await idbDeleteDocument(docId);
  try {
    await fetch(`/api/documents/${docId}`, { method: 'DELETE' });
  } catch (e) {}

  if (state.document && state.document.doc_id === docId) {
    localStorage.removeItem('speechify_last_active_doc_id');
  }
  refreshLibraryBadge();
}

async function openShareModal(docId) {
  const targetId = docId || (state.document ? state.document.doc_id : null);
  if (!targetId) return;

  try {
    const res = await fetch(`/api/documents/${targetId}/share`, { method: 'POST' });
    if (res.ok) {
      const data = await res.json();
      if (shareLinkInput) shareLinkInput.value = data.share_url;
      if (shareToast) shareToast.classList.add('hidden');
      if (shareModal) shareModal.classList.remove('hidden');
    }
  } catch (err) {
    alert('Failed to generate share link: ' + err.message);
  }
}

function closeShareModal() {
  if (shareModal) shareModal.classList.add('hidden');
}

function copyShareLink() {
  if (!shareLinkInput || !shareLinkInput.value) return;
  navigator.clipboard.writeText(shareLinkInput.value).then(() => {
    if (shareToast) {
      shareToast.classList.remove('hidden');
      setTimeout(() => shareToast.classList.add('hidden'), 3000);
    }
  }).catch(() => {
    shareLinkInput.select();
    document.execCommand('copy');
  });
}

async function loadSharedDocument(shareId) {
  try {
    const res = await fetch(`/api/shared/${shareId}`);
    if (!res.ok) throw new Error('Shared document not found');
    const docData = await res.json();
    renderDocument(docData);
    if (docHeaderTitle) docHeaderTitle.textContent = `${docData.title} (Shared)`;
  } catch (err) {
    alert('Error loading shared document: ' + err.message);
    loadSamplePdf();
  }
}

function persistReadingProgress(index, pageNum) {
  if (!state.document || !state.document.doc_id) return;
  const docId = state.document.doc_id;
  state.document.current_sentence_index = index;
  state.document.current_page = pageNum;

  // Instant local IndexedDB save
  idbUpdateProgress(docId, index, pageNum, state.speed, state.voice);
  try {
    localStorage.setItem('speechify_last_active_doc_id', docId);
  } catch (e) {}

  // Debounced cloud sync
  clearTimeout(progressSyncTimer);
  progressSyncTimer = setTimeout(() => {
    fetch(`/api/documents/${docId}/progress`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        sentence_index: index,
        page_num: pageNum,
        speed: state.speed,
        voice: state.voice
      })
    }).catch(() => {});
  }, 2000);
}

// Mobile WakeLock & Haptics Helpers
let wakeLock = null;
async function requestWakeLock() {
  if ('wakeLock' in navigator && !wakeLock) {
    try {
      wakeLock = await navigator.wakeLock.request('screen');
      wakeLock.addEventListener('release', () => { wakeLock = null; });
    } catch (e) {
      // Background / non-visible tab wake lock exception safely ignored
    }
  }
}

function releaseWakeLock() {
  if (wakeLock) {
    wakeLock.release().catch(() => {}).finally(() => { wakeLock = null; });
  }
}

function triggerHaptic(duration = 12) {
  if (typeof navigator !== 'undefined' && navigator.vibrate) {
    try { navigator.vibrate(duration); } catch (_) {}
  }
}

// ==========================================================================
// Initialization & Voice Loading
// ==========================================================================
async function initApp() {
  setupEventListeners();
  setupKeyboardShortcuts();
  setupMediaSession();
  setupMobileGestures();
  setPlaybackSpeed(1.0, true);

  // Initialize Local Persistence & Google OAuth
  await initIndexedDB();
  await checkAuthSession();
  initGoogleSignIn();
  await loadVoices();

  // Check URL query parameters (?share=... or ?doc=...)
  const urlParams = new URLSearchParams(window.location.search);
  const shareParam = urlParams.get('share');
  const docParam = urlParams.get('doc');

  if (shareParam) {
    await loadSharedDocument(shareParam);
    return;
  }
  if (docParam) {
    await loadSavedDocument(docParam);
    return;
  }

  // Restore last active document from IndexedDB or server
  const lastDocId = localStorage.getItem('speechify_last_active_doc_id');
  if (lastDocId) {
    const rec = await idbGetDocument(lastDocId);
    if (rec && rec.doc_data) {
      renderDocument(rec.doc_data);
      if (rec.current_sentence_index > 0) {
        setTimeout(() => jumpToSentence(rec.current_sentence_index, false), 150);
      }
      return;
    }
  }

  // If no last active, check if any saved documents exist in IndexedDB
  const allDocs = await idbListDocuments();
  if (allDocs && allDocs.length > 0) {
    await loadSavedDocument(allDocs[0].doc_id);
    return;
  }

  // Fresh user: load sample research paper
  await loadSamplePdf();
}

async function loadVoices() {
  try {
    const res = await fetch('/api/voices');
    if (!res.ok) throw new Error('Failed to load voices');
    const data = await res.json();
    
    let hwString = data.device === 'cuda' ? 'Kokoro-82M · CUDA GPU' : (data.device === 'cloud' ? 'Speechify Cloud' : 'Kokoro-82M · CPU Mode');
    try {
      const nodeRes = await fetch('/api/node-status');
      if (nodeRes.ok) {
        const nodeData = await nodeRes.json();
        if (nodeData.configured) {
          hwString = nodeData.online ? 'GPU Worker Connected · CUDA' : 'Cloud Mode · Home GPU Offline';
        }
      }
    } catch (e) {}
    if (hardwareText) hardwareText.textContent = hwString;
    if (mobileDrawerHardware) mobileDrawerHardware.textContent = hwString;

    voiceSelect.innerHTML = '';
    if (mobileSheetVoiceSelect) mobileSheetVoiceSelect.innerHTML = '';

    data.voices.forEach(v => {
      const opt = document.createElement('option');
      opt.value = v.id;
      opt.textContent = `${v.name} (${v.accent} ${v.gender})`;
      if (v.id === 'af_heart') opt.selected = true;
      voiceSelect.appendChild(opt);

      if (mobileSheetVoiceSelect) {
        const mOpt = document.createElement('option');
        mOpt.value = v.id;
        mOpt.textContent = `${v.name} (${v.accent} ${v.gender})`;
        if (v.id === 'af_heart') mOpt.selected = true;
        mobileSheetVoiceSelect.appendChild(mOpt);
      }
    });
  } catch (err) {
    console.warn('[Voices] Could not load voices from server:', err);
  }
}

// ==========================================================================
// Document Loading
// ==========================================================================
async function loadSamplePdf() {
  try {
    const res = await fetch('/api/sample-pdf');
    if (!res.ok) throw new Error('Failed to load sample PDF');
    const docData = await res.json();
    renderDocument(docData);
  } catch (err) {
    console.error('[Sample PDF Error]', err);
  }
}

async function loadDocumentFromFile(file) {
  fileStatus.classList.remove('hidden');
  fileName.textContent = file.name;
  
  const formData = new FormData();
  formData.append('file', file);

  try {
    const res = await fetch('/api/parse-file', {
      method: 'POST',
      body: formData
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'File parsing failed');
    }
    const docData = await res.json();
    renderDocument(docData);
    closeModal();
  } catch (err) {
    alert('Error loading file: ' + err.message);
  } finally {
    fileStatus.classList.add('hidden');
  }
}

async function loadDocumentFromText(title, rawText) {
  try {
    const res = await fetch('/api/parse-text', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: rawText, title: title })
    });
    if (!res.ok) throw new Error('Parsing failed');
    const docData = await res.json();
    renderDocument(docData);
    closeModal();
  } catch (err) {
    alert('Failed to parse text: ' + err.message);
  }
}

// ==========================================================================
// Document Rendering (Visual PDF vs Text Reader)
// ==========================================================================
function renderDocument(docData) {
  state.document = docData;
  const resumeIndex = (typeof docData.current_sentence_index === 'number' && docData.current_sentence_index < docData.total_sentences) ? docData.current_sentence_index : 0;
  state.currentIndex = resumeIndex;
  state.audioBlobCache.clear();
  clearSearchHighlights();
  closeSearch();
  pauseAudio();

  // Save to IndexedDB and update active state
  idbSaveDocument(docData);
  refreshLibraryBadge();

  if (btnShareDoc) btnShareDoc.classList.remove('hidden');

  // Update Headers & Mobile Titles
  docHeaderTitle.textContent = docData.title;
  if (mobileMiniDocTitle) mobileMiniDocTitle.textContent = docData.title;
  if (mobileSheetDocTitle) mobileSheetDocTitle.textContent = docData.title;

  const pagesText = docData.is_pdf ? `${docData.total_pages} pages · ` : '';
  docHeaderStats.textContent = `${pagesText}${docData.total_words} words · ~${docData.est_minutes} min`;

  // Handle PDF vs Text View Toggle
  if (docData.is_pdf) {
    viewModeToggle.classList.remove('hidden');
    if (btnMobileViewToggle) btnMobileViewToggle.classList.remove('hidden');
    setViewMode('pdf');
    renderPdfView(docData);
  } else {
    viewModeToggle.classList.add('hidden');
    if (btnMobileViewToggle) btnMobileViewToggle.classList.add('hidden');
    setViewMode('text');
  }

  // Always build Reader Text View as alternative
  renderTextView(docData);

  updateProgressUI();
  preloadNextSentence(resumeIndex);

  if (resumeIndex > 0) {
    setTimeout(() => jumpToSentence(resumeIndex, false), 150);
  }
}

function renderPdfView(docData) {
  pdfViewer.innerHTML = '';
  
  // Set up an IntersectionObserver for reliable, smooth page rendering
  const pageObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const sheet = entry.target;
        const img = sheet.querySelector('.pdf-page-img');
        if (img && !img.src) {
          img.src = img.dataset.src;
        }
        pageObserver.unobserve(sheet);
      }
    });
  }, {
    rootMargin: '1200px 0px 1200px 0px' // Preload 1200px above and below viewport
  });

  docData.pages.forEach(p => {
    const sheet = document.createElement('div');
    sheet.className = 'pdf-page-sheet is-loading';
    sheet.dataset.page = p.page_num;
    sheet.style.aspectRatio = `${p.width} / ${p.height}`;

    // Actual high-res rendered PDF page
    const img = document.createElement('img');
    img.className = 'pdf-page-img';
    img.alt = `Page ${p.page_num + 1}`;
    img.dataset.src = `/api/pdf-page/${docData.doc_id}/${p.page_num}`;

    // Remove loading placeholder once image renders
    img.onload = () => {
      sheet.classList.remove('is-loading');
    };

    // Auto-retry with backoff if image fails
    img.onerror = () => {
      console.warn(`[PDF Page] Page ${p.page_num + 1} render retry...`);
      setTimeout(() => {
        img.src = `/api/pdf-page/${docData.doc_id}/${p.page_num}?retry=${Date.now()}`;
      }, 1500);
    };

    // First 4 pages load immediately; subsequent pages load via IntersectionObserver
    if (p.page_num < 4) {
      img.src = img.dataset.src;
    } else {
      pageObserver.observe(sheet);
    }

    sheet.appendChild(img);

    // Coordinate-aligned overlay layer
    const overlay = document.createElement('div');
    overlay.className = 'pdf-overlay';
    overlay.dataset.page = p.page_num;

    // Sentence highlight boxes
    p.sentence_ids.forEach(sId => {
      const sObj = docData.sentences[sId];
      if (sObj && sObj.rects) {
        sObj.rects.forEach(r => {
          const box = document.createElement('div');
          box.className = 'pdf-sentence-box';
          box.dataset.id = sId;
          box.style.left = `${r.x}%`;
          box.style.top = `${r.y}%`;
          box.style.width = `${r.w}%`;
          box.style.height = `${r.h}%`;
          box.title = sObj.text;

          // Click to play sentence
          box.addEventListener('click', (e) => {
            e.stopPropagation();
            jumpToSentence(sId, true);
          });

          overlay.appendChild(box);
        });
      }
    });

    sheet.appendChild(overlay);

    // Page number tag
    const pageTag = document.createElement('div');
    pageTag.className = 'page-number-tag';
    pageTag.textContent = `Page ${p.page_num + 1} of ${docData.total_pages}`;
    sheet.appendChild(pageTag);

    pdfViewer.appendChild(sheet);
  });
}

function renderTextView(docData) {
  readerContent.innerHTML = '';
  
  docData.paragraphs.forEach(p => {
    const pEl = document.createElement('p');
    pEl.className = 'reader-paragraph';
    pEl.dataset.pIdx = p.idx;

    p.sentence_ids.forEach(sId => {
      const sObj = docData.sentences[sId];
      const sSpan = document.createElement('span');
      sSpan.className = 'sentence';
      sSpan.dataset.id = sId;
      sSpan.textContent = sObj.text + ' ';
      
      sSpan.addEventListener('click', () => {
        jumpToSentence(sId, true);
      });

      pEl.appendChild(sSpan);
    });

    readerContent.appendChild(pEl);
  });
}

function setViewMode(mode) {
  state.viewMode = mode;
  if (mode === 'pdf') {
    pdfViewer.classList.remove('hidden');
    readerContent.classList.add('hidden');
    btnViewPdf.classList.add('active');
    btnViewText.classList.remove('active');
    document.body.classList.add('view-pdf');
    if (btnMobileViewToggle) {
      const pdfIcon = btnMobileViewToggle.querySelector('.icon-mobile-pdf');
      const textIcon = btnMobileViewToggle.querySelector('.icon-mobile-text');
      if (pdfIcon && textIcon) {
        pdfIcon.classList.remove('hidden');
        textIcon.classList.add('hidden');
      }
    }
    if (drawerViewModeDesc) drawerViewModeDesc.textContent = 'Currently: PDF View';
  } else {
    pdfViewer.classList.add('hidden');
    readerContent.classList.remove('hidden');
    btnViewPdf.classList.remove('active');
    btnViewText.classList.add('active');
    document.body.classList.remove('view-pdf');
    if (btnMobileViewToggle) {
      const pdfIcon = btnMobileViewToggle.querySelector('.icon-mobile-pdf');
      const textIcon = btnMobileViewToggle.querySelector('.icon-mobile-text');
      if (pdfIcon && textIcon) {
        pdfIcon.classList.add('hidden');
        textIcon.classList.remove('hidden');
      }
    }
    if (drawerViewModeDesc) drawerViewModeDesc.textContent = 'Currently: Text View';
  }
  updateActiveSentenceHighlight(state.currentIndex);
}

// ==========================================================================
// Playback Engine & Audio Queue
// ==========================================================================
async function playSentence(index) {
  if (!state.document || index < 0 || index >= state.document.total_sentences) {
    pauseAudio();
    return;
  }

  state.currentIndex = index;
  updateActiveSentenceHighlight(index);
  updateProgressUI();
  updateMediaSession(index);

  const sentenceObj = state.document.sentences[index];
  const curPage = sentenceObj ? (sentenceObj.page_num || 0) : 0;
  persistReadingProgress(index, curPage);
  
  try {
    let blobUrl = state.audioBlobCache.get(index);
    if (!blobUrl) {
      const audioUrl = `/api/tts?text=${encodeURIComponent(sentenceObj.text)}&voice=${state.voice}&speed=1.0`;
      const res = await fetch(audioUrl);
      if (!res.ok) throw new Error('Audio generation failed');
      const blob = await res.blob();
      blobUrl = URL.createObjectURL(blob);
      state.audioBlobCache.set(index, blobUrl);
    }

    audio.src = blobUrl;
    audio.playbackRate = state.speed;
    await audio.play();
    setPlayingState(true);

    // Lookahead buffering: Preload next 2 sentences immediately
    preloadNextSentence(index + 1);
    preloadNextSentence(index + 2);

  } catch (err) {
    console.error('[Playback Error]', err);
    if (err.name !== 'AbortError') {
      setPlayingState(false);
    }
  }
}

async function preloadNextSentence(index) {
  if (!state.document || index >= state.document.total_sentences) return;
  if (state.audioBlobCache.has(index)) return;

  const sObj = state.document.sentences[index];
  try {
    const url = `/api/tts?text=${encodeURIComponent(sObj.text)}&voice=${state.voice}&speed=1.0`;
    const res = await fetch(url);
    if (res.ok) {
      const blob = await res.blob();
      state.audioBlobCache.set(index, URL.createObjectURL(blob));
    }
  } catch (e) {
    // Background prewarm failure ignored
  }
}

function pauseAudio() {
  audio.pause();
  setPlayingState(false);
}

function togglePlayPause() {
  if (!state.document || state.document.total_sentences === 0) return;
  if (state.isPlaying) {
    pauseAudio();
  } else {
    playSentence(state.currentIndex);
  }
}

function jumpToSentence(index, autoPlay = true) {
  if (!state.document) return;
  const target = Math.max(0, Math.min(index, state.document.total_sentences - 1));
  state.currentIndex = target;
  const sObj = state.document.sentences[target];
  const curPage = sObj ? (sObj.page_num || 0) : 0;
  persistReadingProgress(target, curPage);

  if (autoPlay) {
    playSentence(target);
  } else {
    updateActiveSentenceHighlight(target);
    updateProgressUI();
  }
}

function setPlayingState(playing) {
  state.isPlaying = playing;
  if (playing) {
    requestWakeLock();
    triggerHaptic(12);
    playIcon.classList.add('hidden');
    pauseIcon.classList.remove('hidden');
    btnPlayPause.classList.add('is-playing');
    if (miniPlayIcon && miniPauseIcon) {
      miniPlayIcon.classList.add('hidden');
      miniPauseIcon.classList.remove('hidden');
    }
    if (miniMobilePlayIcon && miniMobilePauseIcon) {
      miniMobilePlayIcon.classList.add('hidden');
      miniMobilePauseIcon.classList.remove('hidden');
    }
    if (mobileSheetPlayIcon && mobileSheetPauseIcon) {
      mobileSheetPlayIcon.classList.add('hidden');
      mobileSheetPauseIcon.classList.remove('hidden');
    }
  } else {
    releaseWakeLock();
    playIcon.classList.remove('hidden');
    pauseIcon.classList.add('hidden');
    btnPlayPause.classList.remove('is-playing');
    if (miniPlayIcon && miniPauseIcon) {
      miniPlayIcon.classList.remove('hidden');
      miniPauseIcon.classList.add('hidden');
    }
    if (miniMobilePlayIcon && miniMobilePauseIcon) {
      miniMobilePlayIcon.classList.remove('hidden');
      miniMobilePauseIcon.classList.add('hidden');
    }
    if (mobileSheetPlayIcon && mobileSheetPauseIcon) {
      mobileSheetPlayIcon.classList.remove('hidden');
      mobileSheetPauseIcon.classList.add('hidden');
    }
  }
}

// Advance audio seamlessly when sentence finishes
audio.addEventListener('ended', () => {
  if (!state.document) return;
  const nextIdx = state.currentIndex + 1;
  if (nextIdx < state.document.total_sentences) {
    playSentence(nextIdx);
  } else {
    setPlayingState(false);
    updateActiveSentenceHighlight(-1);
  }
});

// ==========================================================================
// UI Updates & Dual Highlighting (PDF & Text)
// ==========================================================================
function smoothScrollToActiveElement(el) {
  if (!el) return;
  const rect = el.getBoundingClientRect();
  const headerHeight = 70;
  const dockHeight = window.innerWidth <= 1024 ? 90 : 110;
  const visibleTop = headerHeight + 20;
  const visibleBottom = window.innerHeight - dockHeight - 20;
  const visibleHeight = Math.max(100, visibleBottom - visibleTop);

  // Scroll into the unobstructed reading corridor between top header and bottom dock
  if (rect.top < visibleTop || rect.bottom > visibleBottom) {
    const elDocY = window.pageYOffset + rect.top + (rect.height / 2);
    const targetScrollY = elDocY - (visibleTop + visibleHeight / 2);
    window.scrollTo({
      top: Math.max(0, targetScrollY),
      behavior: 'smooth'
    });
  }
}

function updateActiveSentenceHighlight(index) {
  // 1. PDF View Highlighting
  const prevPdfBoxes = document.querySelectorAll('.pdf-sentence-box.active-pdf-highlight');
  prevPdfBoxes.forEach(b => b.classList.remove('active-pdf-highlight'));

  if (index >= 0 && state.viewMode === 'pdf') {
    const activeBoxes = document.querySelectorAll(`.pdf-sentence-box[data-id="${index}"]`);
    if (activeBoxes.length > 0) {
      activeBoxes.forEach(b => b.classList.add('active-pdf-highlight'));
      smoothScrollToActiveElement(activeBoxes[0]);
    }
  }

  // 2. Text View Highlighting
  const prevTextActive = document.querySelector('.sentence.active-sentence');
  if (prevTextActive) prevTextActive.classList.remove('active-sentence');

  if (index >= 0 && state.viewMode === 'text') {
    const activeEl = document.querySelector(`.sentence[data-id="${index}"]`);
    if (activeEl) {
      activeEl.classList.add('active-sentence');
      smoothScrollToActiveElement(activeEl);
    }
  }
}

function updateProgressUI() {
  if (!state.document || state.document.total_sentences === 0) {
    sentenceCounter.textContent = 'Sentence 0 / 0';
    if (miniSentenceCounter) miniSentenceCounter.textContent = 'Sentence 0 / 0';
    if (mobileMiniSnippet) mobileMiniSnippet.textContent = 'Sentence 0 / 0 · 0m left';
    if (mobileSheetDocStats) mobileSheetDocStats.textContent = 'Sentence 0 / 0 · 0m left';
    if (mobileScrubberSentence) mobileScrubberSentence.textContent = 'Sentence 0 / 0';
    if (mobileScrubberTime) mobileScrubberTime.textContent = '0m left';
    if (mobileScrubberFill) mobileScrubberFill.style.width = '0%';
    remainingTime.textContent = '0m left';
    dockProgressBar.style.width = '0%';
    return;
  }

  const current = state.currentIndex + 1;
  const total = state.document.total_sentences;
  sentenceCounter.textContent = `Sentence ${current} / ${total}`;
  if (miniSentenceCounter) miniSentenceCounter.textContent = `Sentence ${current} / ${total}`;

  let remainingWords = 0;
  for (let i = state.currentIndex; i < total; i++) {
    remainingWords += state.document.sentences[i].word_count || 10;
  }
  const adjustedWpm = 150 * state.speed;
  const minsLeft = Math.max(0.1, Math.round((remainingWords / adjustedWpm) * 10) / 10);
  remainingTime.textContent = `${minsLeft}m left`;

  const pct = (state.currentIndex / total) * 100;
  dockProgressBar.style.width = `${pct}%`;

  // Mobile Sync Updates
  if (mobileMiniSnippet) {
    mobileMiniSnippet.textContent = `Sentence ${current} / ${total} · ${minsLeft}m left`;
  }
  if (mobileSheetDocStats) {
    mobileSheetDocStats.textContent = `Sentence ${current} / ${total} · ${minsLeft}m left`;
  }
  if (mobileScrubberSentence) {
    mobileScrubberSentence.textContent = `Sentence ${current} of ${total}`;
  }
  if (mobileScrubberTime) {
    mobileScrubberTime.textContent = `${minsLeft}m left`;
  }
  if (mobileScrubberFill) {
    mobileScrubberFill.style.width = `${pct}%`;
  }
  if (mobileCurrentSentenceText && state.document.sentences[state.currentIndex]) {
    mobileCurrentSentenceText.textContent = state.document.sentences[state.currentIndex].text;
  }
}

// ==========================================================================
// MediaSession API
// ==========================================================================
function setupMediaSession() {
  if ('mediaSession' in navigator) {
    navigator.mediaSession.setActionHandler('play', () => togglePlayPause());
    navigator.mediaSession.setActionHandler('pause', () => pauseAudio());
    navigator.mediaSession.setActionHandler('previoustrack', () => jumpToSentence(state.currentIndex - 1, true));
    navigator.mediaSession.setActionHandler('nexttrack', () => jumpToSentence(state.currentIndex + 1, true));
  }
}

function updateMediaSession(index) {
  if ('mediaSession' in navigator && state.document) {
    const sObj = state.document.sentences[index];
    navigator.mediaSession.metadata = new MediaMetadata({
      title: sObj ? sObj.text : 'Speechify Local',
      artist: `Voice: ${state.voice}`,
      album: state.document.title
    });
  }
}

// ==========================================================================
// Document Search Engine (High Performance, O(1) DOM Operations)
// ==========================================================================
function openSearch() {
  if (!state.document) return;
  state.search.isOpen = true;
  searchBar.classList.remove('hidden');
  searchInput.focus();
  searchInput.select();
  const val = searchInput.value.trim();
  if (val.length >= 2) {
    performSearch(val);
  }
}

function closeSearch() {
  state.search.isOpen = false;
  searchBar.classList.add('hidden');
  clearSearchHighlights();
}

function clearSearchHighlights() {
  // Clear only previously active highlights without thrashing the entire DOM
  if (state.search.activeSentenceId !== null) {
    const prevPdf = document.querySelectorAll(`.pdf-sentence-box[data-id="${state.search.activeSentenceId}"]`);
    prevPdf.forEach(b => b.classList.remove('search-active'));
    const prevText = document.querySelector(`.sentence[data-id="${state.search.activeSentenceId}"]`);
    if (prevText) prevText.classList.remove('search-active');
    state.search.activeSentenceId = null;
  }
  
  // Clean up any remaining active search highlights
  document.querySelectorAll('.search-active').forEach(el => el.classList.remove('search-active'));

  state.search.matches = [];
  state.search.currentIndex = -1;
  searchCount.textContent = '0 / 0';
}

let searchDebounceTimer = null;
function handleSearchInput(val) {
  clearTimeout(searchDebounceTimer);
  const trimmed = val.trim();
  if (trimmed.length < 2) {
    clearSearchHighlights();
    searchCount.textContent = trimmed.length === 1 ? '2+ chars' : '0 / 0';
    return;
  }
  searchDebounceTimer = setTimeout(() => {
    performSearch(trimmed);
  }, 180);
}

function performSearch(query) {
  clearSearchHighlights();
  state.search.query = query;
  if (!query || query.length < 2 || !state.document || !state.document.sentences) {
    searchCount.textContent = '0 / 0';
    return;
  }

  const lowerQ = query.toLowerCase();
  const matches = [];
  const sentences = state.document.sentences;

  // Blazingly fast in-memory array search (runs in <1ms even for 30,000 sentences)
  for (let i = 0; i < sentences.length; i++) {
    const s = sentences[i];
    if (s.text && s.text.toLowerCase().includes(lowerQ)) {
      matches.push({
        sentenceId: s.id,
        pageNum: s.page_num,
        text: s.text
      });
      // Safety cap at 500 matches to prevent memory bloat
      if (matches.length >= 500) break;
    }
  }

  state.search.matches = matches;

  if (matches.length === 0) {
    searchCount.textContent = '0 results';
    return;
  }

  // Focus the first match directly without blocking the main browser thread
  focusMatch(0);
}

function focusMatch(index) {
  const matches = state.search.matches;
  if (!matches || matches.length === 0) return;

  const targetIndex = (index + matches.length) % matches.length;
  state.search.currentIndex = targetIndex;
  searchCount.textContent = `${targetIndex + 1} / ${matches.length}`;

  const match = matches[targetIndex];

  // 1. Remove previous active match (O(1) operation)
  if (state.search.activeSentenceId !== null && state.search.activeSentenceId !== match.sentenceId) {
    const prevPdf = document.querySelectorAll(`.pdf-sentence-box[data-id="${state.search.activeSentenceId}"]`);
    prevPdf.forEach(b => b.classList.remove('search-active'));
    const prevText = document.querySelector(`.sentence[data-id="${state.search.activeSentenceId}"]`);
    if (prevText) prevText.classList.remove('search-active');
  }

  state.search.activeSentenceId = match.sentenceId;

  // 2. Add active highlight to new focused match and scroll into view (O(1) operation)
  if (state.viewMode === 'pdf') {
    const activeBoxes = document.querySelectorAll(`.pdf-sentence-box[data-id="${match.sentenceId}"]`);
    if (activeBoxes.length > 0) {
      activeBoxes.forEach(b => b.classList.add('search-active'));
      activeBoxes[0].scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  } else {
    const activeSpan = document.querySelector(`.sentence[data-id="${match.sentenceId}"]`);
    if (activeSpan) {
      activeSpan.classList.add('search-active');
      activeSpan.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }
}

function nextMatch() {
  if (state.search.matches && state.search.matches.length > 0) {
    focusMatch(state.search.currentIndex + 1);
  }
}

function prevMatch() {
  if (state.search.matches && state.search.matches.length > 0) {
    focusMatch(state.search.currentIndex - 1);
  }
}

function playSearchMatch() {
  if (state.search.matches && state.search.matches.length > 0 && state.search.currentIndex >= 0) {
    const match = state.search.matches[state.search.currentIndex];
    jumpToSentence(match.sentenceId, true);
    closeSearch();
  }
}

// ==========================================================================
// Dock Minimization & Fullscreen Controllers
// ==========================================================================
function toggleMinimizeDock(minimize) {
  if (typeof minimize === 'boolean') {
    state.isDockMinimized = minimize;
  } else {
    state.isDockMinimized = !state.isDockMinimized;
  }

  if (state.isDockMinimized) {
    playerDock.classList.add('is-minimized');
    dockMinimizedBar.classList.remove('hidden');
  } else {
    playerDock.classList.remove('is-minimized');
    dockMinimizedBar.classList.add('hidden');
  }
}

function toggleFullscreen() {
  if (!document.fullscreenElement) {
    const elem = document.documentElement;
    if (elem.requestFullscreen) {
      elem.requestFullscreen().catch(err => {
        console.warn('Fullscreen request failed:', err);
      });
    } else if (elem.webkitRequestFullscreen) {
      elem.webkitRequestFullscreen();
    }
  } else {
    if (document.exitFullscreen) {
      document.exitFullscreen();
    } else if (document.webkitExitFullscreen) {
      document.webkitExitFullscreen();
    }
  }
}

// ==========================================================================
// Keyboard Shortcuts
// ==========================================================================
function setupKeyboardShortcuts() {
  window.addEventListener('keydown', (e) => {
    // Intercept Ctrl+F / Cmd+F anywhere to trigger search
    if ((e.ctrlKey || e.metaKey) && (e.code === 'KeyF' || e.key === 'f')) {
      e.preventDefault();
      openSearch();
      return;
    }

    if (e.code === 'Escape') {
      if (state.search.isOpen) {
        closeSearch();
        return;
      }
      pauseAudio();
      closeModal();
      return;
    }

    if (['INPUT', 'TEXTAREA'].includes(e.target.tagName)) return;

    // Press 'F' to toggle fullscreen
    if (e.code === 'KeyF' && !e.ctrlKey && !e.metaKey && !e.altKey) {
      e.preventDefault();
      toggleFullscreen();
      return;
    }

    // Press 'M' to toggle dock minimize
    if (e.code === 'KeyM' && !e.ctrlKey && !e.metaKey && !e.altKey) {
      e.preventDefault();
      toggleMinimizeDock();
      return;
    }

    if (e.code === 'Space') {
      e.preventDefault();
      togglePlayPause();
    } else if (e.code === 'ArrowLeft') {
      e.preventDefault();
      jumpToSentence(state.currentIndex - 1, true);
    } else if (e.code === 'ArrowRight') {
      e.preventDefault();
      jumpToSentence(state.currentIndex + 1, true);
    } else if (e.code === 'ArrowUp') {
      e.preventDefault();
      adjustSpeed(0.02);
    } else if (e.code === 'ArrowDown') {
      e.preventDefault();
      adjustSpeed(-0.02);
    }
  });
}

// Significant speed stops for tactile magnetic snapping
const SPEED_MILESTONES = [0.5, 0.75, 1.0, 1.1, 1.2, 1.25, 1.3, 1.4, 1.5, 1.75, 2.0, 2.25, 2.5, 3.0, 3.5];
const SNAP_THRESHOLD = 0.038;

function formatSpeed(val) {
  const rounded = Math.round(val * 100) / 100;
  if (rounded % 1 === 0) return `${rounded.toFixed(1)}x`;
  if (Math.round(rounded * 10) === rounded * 10) return `${rounded.toFixed(1)}x`;
  return `${rounded.toFixed(2)}x`;
}

function adjustSpeed(delta) {
  setPlaybackSpeed(state.speed + delta, true);
}

function setPlaybackSpeed(targetSpeed, applySnap = true) {
  let finalSpeed = targetSpeed;
  let isSnapped = false;
  let snappedMilestone = null;

  if (applySnap) {
    for (const m of SPEED_MILESTONES) {
      if (Math.abs(targetSpeed - m) <= SNAP_THRESHOLD) {
        finalSpeed = m;
        isSnapped = true;
        snappedMilestone = m;
        break;
      }
    }
  }

  if (!isSnapped) {
    // Round strictly to 0.02 increments
    finalSpeed = Math.round(targetSpeed * 50) / 50;
  }

  // Clamp within 0.5x to 3.5x
  finalSpeed = Math.max(0.5, Math.min(3.5, finalSpeed));
  state.speed = finalSpeed;
  audio.playbackRate = finalSpeed;

  // Haptic resistance pulse on mobile when snapping into a milestone
  if (isSnapped && state.lastSnappedMilestone !== snappedMilestone) {
    if (navigator.vibrate) {
      try { navigator.vibrate(10); } catch (e) {}
    }
    state.lastSnappedMilestone = snappedMilestone;
  } else if (!isSnapped) {
    state.lastSnappedMilestone = null;
  }

  const speedStr = formatSpeed(finalSpeed);
  const pct = Math.max(0, Math.min(100, ((finalSpeed - 0.5) / 3.0) * 100));

  // Update inline dock gauge
  if (speedGaugeSlider) speedGaugeSlider.value = finalSpeed;
  if (speedGaugeFill) speedGaugeFill.style.width = `${pct}%`;
  if (speedGaugeVal) speedGaugeVal.textContent = speedStr;

  // Update floating rate bubble directly above the slider thumb
  if (speedThumbTooltip) {
    speedThumbTooltip.style.left = `${pct}%`;
    speedThumbTooltip.textContent = speedStr;
    speedThumbTooltip.classList.toggle('is-snapped', isSnapped);
  }

  // Update popover dial
  if (popoverSpeedSlider) popoverSpeedSlider.value = finalSpeed;
  if (popoverLargeVal) popoverLargeVal.textContent = speedStr;
  if (popoverWpmVal) popoverWpmVal.textContent = `~${Math.round(150 * finalSpeed)} words per minute`;

  // Update active preset chip
  if (speedPresetChips) {
    speedPresetChips.forEach(chip => {
      const chipSpeed = parseFloat(chip.dataset.speed);
      if (Math.abs(chipSpeed - finalSpeed) < 0.03) {
        chip.classList.add('active');
      } else {
        chip.classList.remove('active');
      }
    });
  }

  // Update mobile mini speed pill
  if (mobileMiniSpeedPill) {
    mobileMiniSpeedPill.textContent = speedStr;
  }

  // Update mobile full player sheet speed controls
  if (mobileSheetSpeedSlider) {
    mobileSheetSpeedSlider.value = finalSpeed;
  }
  if (mobileSheetSpeedBadge) {
    mobileSheetSpeedBadge.textContent = `${speedStr} (~${Math.round(150 * finalSpeed)} WPM)`;
  }
  if (speedChipsM) {
    speedChipsM.forEach(chip => {
      const chipSpeed = parseFloat(chip.dataset.speed);
      if (Math.abs(chipSpeed - finalSpeed) < 0.03) {
        chip.classList.add('active');
      } else {
        chip.classList.remove('active');
      }
    });
  }

  updateProgressUI();
}

// ==========================================================================
// Event Listeners & Wire-up
// ==========================================================================
function setupEventListeners() {
  btnPlayPause.addEventListener('click', togglePlayPause);
  btnPrev.addEventListener('click', () => jumpToSentence(state.currentIndex - 1, true));
  btnNext.addEventListener('click', () => jumpToSentence(state.currentIndex + 1, true));

  // Speed Gauge Slider & Nudge Listeners (0.02 step with magnetic stops)
  if (speedGaugeSlider) {
    speedGaugeSlider.addEventListener('input', (e) => {
      setPlaybackSpeed(parseFloat(e.target.value), true);
    });
  }
  if (popoverSpeedSlider) {
    popoverSpeedSlider.addEventListener('input', (e) => {
      setPlaybackSpeed(parseFloat(e.target.value), true);
    });
  }
  if (btnSpeedDown) {
    btnSpeedDown.addEventListener('click', () => {
      // Step down by 0.02
      setPlaybackSpeed(state.speed - 0.02, false);
    });
  }
  if (btnSpeedUp) {
    btnSpeedUp.addEventListener('click', () => {
      // Step up by 0.02
      setPlaybackSpeed(state.speed + 0.02, false);
    });
  }
  if (btnSpeedGaugePill) {
    btnSpeedGaugePill.addEventListener('click', (e) => {
      e.stopPropagation();
      if (speedPopover) speedPopover.classList.toggle('hidden');
    });
  }
  if (btnCloseSpeedPopover) {
    btnCloseSpeedPopover.addEventListener('click', () => {
      if (speedPopover) speedPopover.classList.add('hidden');
    });
  }
  document.addEventListener('click', (e) => {
    if (speedPopover && !speedPopover.classList.contains('hidden')) {
      if (!speedPopover.contains(e.target) && e.target !== btnSpeedGaugePill && !btnSpeedGaugePill.contains(e.target)) {
        speedPopover.classList.add('hidden');
      }
    }
  });
  if (speedPresetChips) {
    speedPresetChips.forEach(chip => {
      chip.addEventListener('click', () => {
        setPlaybackSpeed(parseFloat(chip.dataset.speed));
      });
    });
  }

  voiceSelect.addEventListener('change', (e) => {
    state.voice = e.target.value;
    state.audioBlobCache.clear();
    if (state.isPlaying) playSentence(state.currentIndex);
  });

  // View Mode Switches
  btnViewPdf.addEventListener('click', () => setViewMode('pdf'));
  btnViewText.addEventListener('click', () => setViewMode('text'));

  // Theme Toggle
  btnThemeToggle.addEventListener('click', () => {
    const isLight = document.body.classList.toggle('theme-light');
    themeIcon.textContent = isLight ? '☀️' : '🌙';
  });

  // Zoom / Font Controls
  btnZoomOut.addEventListener('click', () => {
    if (state.viewMode === 'pdf') {
      state.pdfZoom = Math.max(0.65, state.pdfZoom - 0.1);
      document.documentElement.style.setProperty('--pdf-zoom', state.pdfZoom);
    } else {
      state.fontSize = Math.max(15, state.fontSize - 2);
      document.documentElement.style.setProperty('--reader-font-size', `${state.fontSize}px`);
    }
  });

  btnZoomIn.addEventListener('click', () => {
    if (state.viewMode === 'pdf') {
      state.pdfZoom = Math.min(1.5, state.pdfZoom + 0.1);
      document.documentElement.style.setProperty('--pdf-zoom', state.pdfZoom);
    } else {
      state.fontSize = Math.min(32, state.fontSize + 2);
      document.documentElement.style.setProperty('--reader-font-size', `${state.fontSize}px`);
    }
  });

  // Modal Open/Close
  btnOpenImport.addEventListener('click', openModal);
  btnEmptyImport.addEventListener('click', openModal);
  btnCloseModal.addEventListener('click', closeModal);
  importModal.addEventListener('click', (e) => {
    if (e.target === importModal) closeModal();
  });

  // Modal Tabs
  tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      tabButtons.forEach(b => b.classList.remove('active'));
      tabPanels.forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById(btn.dataset.tab).classList.add('active');
    });
  });

  // Paste Text Submit
  btnSubmitPaste.addEventListener('click', () => {
    const text = pasteContent.value.trim();
    if (!text) {
      alert('Please enter or paste text to read.');
      return;
    }
    const title = pasteTitle.value.trim() || 'Pasted Document';
    loadDocumentFromText(title, text);
    pasteContent.value = '';
    pasteTitle.value = '';
  });

  // Sample PDF Buttons
  const handleLoadSamplePdf = () => {
    loadSamplePdf();
    closeModal();
  };
  btnSamplePdf.addEventListener('click', handleLoadSamplePdf);
  btnEmptyPdf.addEventListener('click', handleLoadSamplePdf);
  btnSamplePdfInModal.addEventListener('click', handleLoadSamplePdf);

  // File Upload & Dropzone
  dropzone.addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files[0]) {
      loadDocumentFromFile(e.target.files[0]);
    }
  });

  dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('drag-over');
  });

  dropzone.addEventListener('dragleave', () => {
    dropzone.classList.remove('drag-over');
  });

  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('drag-over');
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      loadDocumentFromFile(e.dataTransfer.files[0]);
    }
  });

  // Scrubber Track
  dockProgressTrack.addEventListener('click', (e) => {
    if (!state.document) return;
    const rect = dockProgressTrack.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const ratio = Math.max(0, Math.min(1, clickX / rect.width));
    const targetIdx = Math.floor(ratio * state.document.total_sentences);
    jumpToSentence(targetIdx, true);
  });

  // Search Event Listeners
  btnOpenSearch.addEventListener('click', openSearch);
  btnCloseSearch.addEventListener('click', closeSearch);
  btnSearchPrev.addEventListener('click', prevMatch);
  btnSearchNext.addEventListener('click', nextMatch);
  btnSearchPlay.addEventListener('click', playSearchMatch);
  searchInput.addEventListener('input', (e) => handleSearchInput(e.target.value));
  searchInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      if (e.shiftKey) prevMatch();
      else nextMatch();
    } else if (e.key === 'Escape') {
      e.preventDefault();
      closeSearch();
    }
  });

  // Dock Minimization Listeners
  if (btnMinimizeDock) {
    btnMinimizeDock.addEventListener('click', () => toggleMinimizeDock(true));
  }
  if (btnExpandDock) {
    btnExpandDock.addEventListener('click', () => toggleMinimizeDock(false));
  }
  if (btnMiniPlayPause) {
    btnMiniPlayPause.addEventListener('click', togglePlayPause);
  }

  // Fullscreen Listeners
  if (btnFullscreen) {
    btnFullscreen.addEventListener('click', toggleFullscreen);
  }

  document.addEventListener('fullscreenchange', () => {
    const isFs = !!document.fullscreenElement;
    document.body.classList.toggle('is-fullscreen', isFs);
    if (btnFullscreen) {
      const enterIcon = btnFullscreen.querySelector('.icon-fs-enter');
      const exitIcon = btnFullscreen.querySelector('.icon-fs-exit');
      if (enterIcon && exitIcon) {
        if (isFs) {
          enterIcon.classList.add('hidden');
          exitIcon.classList.remove('hidden');
        } else {
          enterIcon.classList.remove('hidden');
          exitIcon.classList.add('hidden');
        }
      }
    }
  });

  // Mobile Header & Drawer Listeners
  if (btnMobileMenu) {
    btnMobileMenu.addEventListener('click', openMobileDrawer);
  }
  if (btnCloseMobileDrawer) {
    btnCloseMobileDrawer.addEventListener('click', closeMobileDrawer);
  }
  if (mobileDrawerOverlay) {
    mobileDrawerOverlay.addEventListener('click', (e) => {
      if (e.target === mobileDrawerOverlay) closeMobileDrawer();
    });
  }
  if (btnMobileViewToggle) {
    btnMobileViewToggle.addEventListener('click', () => {
      setViewMode(state.viewMode === 'pdf' ? 'text' : 'pdf');
    });
  }

  // Drawer Action Buttons
  if (btnDrawerSamplePdf) {
    btnDrawerSamplePdf.addEventListener('click', () => {
      loadSamplePdf();
      closeMobileDrawer();
    });
  }
  if (btnDrawerImport) {
    btnDrawerImport.addEventListener('click', () => {
      openModal();
      closeMobileDrawer();
    });
  }
  if (btnDrawerSearch) {
    btnDrawerSearch.addEventListener('click', () => {
      openSearch();
      closeMobileDrawer();
    });
  }
  if (btnDrawerTheme) {
    btnDrawerTheme.addEventListener('click', () => {
      const isLight = document.body.classList.toggle('theme-light');
      themeIcon.textContent = isLight ? '☀️' : '🌙';
      if (drawerThemeIcon) drawerThemeIcon.textContent = isLight ? '☀️' : '🌙';
    });
  }
  if (btnDrawerViewToggle) {
    btnDrawerViewToggle.addEventListener('click', () => {
      setViewMode(state.viewMode === 'pdf' ? 'text' : 'pdf');
    });
  }
  if (btnDrawerFullscreen) {
    btnDrawerFullscreen.addEventListener('click', () => {
      toggleFullscreen();
      closeMobileDrawer();
    });
  }
  if (btnDrawerZoomOut) {
    btnDrawerZoomOut.addEventListener('click', () => btnZoomOut.click());
  }
  if (btnDrawerZoomIn) {
    btnDrawerZoomIn.addEventListener('click', () => btnZoomIn.click());
  }

  // Mobile Mini-Player Bar
  if (btnMobileMiniPlay) {
    btnMobileMiniPlay.addEventListener('click', (e) => {
      e.stopPropagation();
      togglePlayPause();
    });
  }
  if (mobileMiniInfo) {
    mobileMiniInfo.addEventListener('click', openMobilePlayerSheet);
  }
  if (btnMobileMiniExpand) {
    btnMobileMiniExpand.addEventListener('click', openMobilePlayerSheet);
  }
  if (mobileMiniSpeedPill) {
    mobileMiniSpeedPill.addEventListener('click', openMobilePlayerSheet);
  }

  // Mobile Full Player Sheet
  if (btnCollapseMobileSheet) {
    btnCollapseMobileSheet.addEventListener('click', closeMobilePlayerSheet);
  }
  if (mobileSheetOverlay) {
    mobileSheetOverlay.addEventListener('click', closeMobilePlayerSheet);
  }
  if (btnMobilePrev) {
    btnMobilePrev.addEventListener('click', () => {
      triggerHaptic(10);
      jumpToSentence(state.currentIndex - 1, true);
    });
  }
  if (btnMobilePlayPause) {
    btnMobilePlayPause.addEventListener('click', togglePlayPause);
  }
  if (btnMobileNext) {
    btnMobileNext.addEventListener('click', () => {
      triggerHaptic(10);
      jumpToSentence(state.currentIndex + 1, true);
    });
  }
  if (mobileSheetSpeedSlider) {
    mobileSheetSpeedSlider.addEventListener('input', (e) => {
      setPlaybackSpeed(parseFloat(e.target.value), true);
    });
  }
  if (mobileSheetVoiceSelect) {
    mobileSheetVoiceSelect.addEventListener('change', (e) => {
      state.voice = e.target.value;
      voiceSelect.value = state.voice;
      state.audioBlobCache.clear();
      if (state.isPlaying) playSentence(state.currentIndex);
    });
  }
  if (mobileScrubberTrack) {
    mobileScrubberTrack.addEventListener('click', (e) => {
      if (!state.document) return;
      const rect = mobileScrubberTrack.getBoundingClientRect();
      const clickX = e.clientX - rect.left;
      const ratio = Math.max(0, Math.min(1, clickX / rect.width));
      const targetIdx = Math.floor(ratio * state.document.total_sentences);
      jumpToSentence(targetIdx, true);
    });
  }

  // Library Listeners
  if (btnLibrary) btnLibrary.addEventListener('click', openLibrary);
  if (btnCloseLibraryModal) btnCloseLibraryModal.addEventListener('click', closeLibrary);
  if (libraryModal) {
    libraryModal.addEventListener('click', (e) => {
      if (e.target === libraryModal) closeLibrary();
    });
  }
  if (btnLibraryNewUpload) {
    btnLibraryNewUpload.addEventListener('click', () => {
      closeLibrary();
      openModal();
    });
  }
  if (librarySearchInput) {
    librarySearchInput.addEventListener('input', (e) => {
      renderLibraryList(e.target.value);
    });
  }

  // Share Listeners
  if (btnShareDoc) {
    btnShareDoc.addEventListener('click', () => openShareModal());
  }
  if (btnCloseShareModal) btnCloseShareModal.addEventListener('click', closeShareModal);
  if (shareModal) {
    shareModal.addEventListener('click', (e) => {
      if (e.target === shareModal) closeShareModal();
    });
  }
  if (btnCopyShareLink) btnCopyShareLink.addEventListener('click', copyShareLink);

  // Auth Listeners
  if (btnTriggerGoogleSignIn) {
    btnTriggerGoogleSignIn.addEventListener('click', triggerGoogleSignIn);
  }
  if (btnSignOut) {
    btnSignOut.addEventListener('click', handleLogout);
  }
}

function openMobileDrawer() {
  if (mobileDrawerOverlay) mobileDrawerOverlay.classList.remove('hidden');
}

function closeMobileDrawer() {
  if (mobileDrawerOverlay) mobileDrawerOverlay.classList.add('hidden');
}

function openMobilePlayerSheet() {
  if (mobilePlayerSheet) mobilePlayerSheet.classList.add('is-open');
  if (mobileSheetOverlay) mobileSheetOverlay.classList.remove('hidden');
  updateProgressUI();
}

function closeMobilePlayerSheet() {
  if (mobilePlayerSheet) mobilePlayerSheet.classList.remove('is-open');
  if (mobileSheetOverlay) mobileSheetOverlay.classList.add('hidden');
}

function setupMobileGestures() {
  let startY = 0;
  let currentY = 0;

  // Swipe down to dismiss mobile full player sheet
  if (mobilePlayerSheet) {
    mobilePlayerSheet.addEventListener('touchstart', (e) => {
      startY = e.touches[0].clientY;
    }, { passive: true });

    mobilePlayerSheet.addEventListener('touchmove', (e) => {
      currentY = e.touches[0].clientY;
    }, { passive: true });

    mobilePlayerSheet.addEventListener('touchend', () => {
      if (currentY - startY > 75) {
        closeMobilePlayerSheet();
      }
      startY = 0;
      currentY = 0;
    });
  }

  // Horizontal swipe gestures on reader canvas to navigate sentences
  let touchStartX = 0;
  let touchStartY = 0;
  const readerMain = document.querySelector('.reader-container');
  if (readerMain) {
    readerMain.addEventListener('touchstart', (e) => {
      touchStartX = e.touches[0].clientX;
      touchStartY = e.touches[0].clientY;
    }, { passive: true });

    readerMain.addEventListener('touchend', (e) => {
      const touchEndX = e.changedTouches[0].clientX;
      const touchEndY = e.changedTouches[0].clientY;
      const diffX = touchEndX - touchStartX;
      const diffY = touchEndY - touchStartY;

      // Check for clean horizontal swipe gesture (>80px)
      if (Math.abs(diffX) > 80 && Math.abs(diffX) > Math.abs(diffY) * 1.8) {
        if (diffX < 0) {
          // Swipe Left -> Next Sentence
          triggerHaptic(10);
          jumpToSentence(state.currentIndex + 1, true);
        } else {
          // Swipe Right -> Previous Sentence
          triggerHaptic(10);
          jumpToSentence(state.currentIndex - 1, true);
        }
      }
    }, { passive: true });
  }
}

function openModal() {
  importModal.classList.remove('hidden');
}

function closeModal() {
  importModal.classList.add('hidden');
}

// Start application
document.addEventListener('DOMContentLoaded', initApp);
