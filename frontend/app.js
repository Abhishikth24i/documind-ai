/* DOCUMIND AI - JAVASCRIPT APPLICATION ENGINE */
const API_BASE = '';

const Auth = {
  getUser() {
    const s = localStorage.getItem('documind_user_auth');
    if (s) { try { return JSON.parse(s); } catch(e){} }
    return null;
  },
  login(user) {
    localStorage.setItem('documind_user_auth', JSON.stringify(user));
    updateUserBadge(user);
  },
  logout() {
    localStorage.removeItem('documind_user_auth');
    showToast('Signed out', 'info');
    setTimeout(() => { location.reload(); }, 600);
  }
};

const SessionManager = {
  getAll() {
    const s = localStorage.getItem('documind_sessions_list');
    if (s) { try { return JSON.parse(s); } catch(e){} }
    return [];
  },
  saveAll(list) {
    localStorage.setItem('documind_sessions_list', JSON.stringify(list));
    renderSessionsSidebar();
  },
  createSession(title = 'New Document Session', docId = null) {
    const id = 'sess_' + Date.now();
    const list = this.getAll();
    const newSess = { id, title, docId, goal: 'qa', createdAt: Date.now() };
    list.unshift(newSess);
    this.saveAll(list);
    this.activateSession(id);
    return newSess;
  },
  activateSession(id) {
    const list = this.getAll();
    const sess = list.find(s => s.id === id);
    if (!sess) return;
    AppState.activeSessionId = sess.id;
    AppState.activeDocId = sess.docId;
    AppState.activeGoal = sess.goal || 'qa';
    localStorage.setItem('documind_current_session_id', id);

    updateSessionHeader(sess);
    renderGoalTabs();
    renderSuggestions();
    restoreSessionMessages(sess.id);
    renderSessionsSidebar();
  },
  renameSession(id) {
    const list = this.getAll();
    const s = list.find(item => item.id === id);
    if (!s) return;
    const newTitle = prompt('Enter new session title:', s.title);
    if (newTitle && newTitle.trim()) {
      s.title = newTitle.trim();
      this.saveAll(list);
      if (AppState.activeSessionId === id) updateSessionHeader(s);
    }
  },
  deleteSession(id) {
    let list = this.getAll();
    list = list.filter(s => s.id !== id);
    localStorage.removeItem('documind_messages_' + id);
    this.saveAll(list);
    if (AppState.activeSessionId === id) {
      if (list.length > 0) this.activateSession(list[0].id);
      else this.createSession('New Document Session', null);
    }
  }
};

const AppState = {
  activeSessionId: null,
  activeDocId: null,
  activeGoal: 'qa',
  docs: [],
  savedMessages: [],
  chatHistory: [],
  isProcessing: false
};

function getClientSessionHeaders() {
  let id = localStorage.getItem('documind_session_id');
  if (!id) {
    id = 'client_' + Date.now();
    localStorage.setItem('documind_session_id', id);
  }
  return { 'X-Session-Id': id };
}
const SESSION_HEADERS = getClientSessionHeaders();

function openStudioWorkspace(label = 'Launching Workspace...') {
  const transitionScreen = document.getElementById('launch-transition-screen');
  const launchLabel = document.getElementById('launch-transition-label');
  const websiteView = document.getElementById('website-view');
  const studioView = document.getElementById('studio-view');
  const authModal = document.getElementById('auth-modal');

  authModal.style.display = 'none';
  launchLabel.textContent = label;
  transitionScreen.style.display = 'flex';

  setTimeout(() => {
    transitionScreen.style.display = 'none';
    websiteView.classList.add('hidden');
    studioView.classList.add('active');
    window.scrollTo(0, 0);

    const sessions = SessionManager.getAll();
    if (sessions.length === 0) {
      SessionManager.createSession('First Document Session', null);
    } else {
      const cur = localStorage.getItem('documind_current_session_id') || sessions[0].id;
      SessionManager.activateSession(cur);
    }
    showToast('Entered DocuMind Neural Studio', 'info');
  }, 700);
}

function exitStudioToWebsite() {
  const websiteView = document.getElementById('website-view');
  const studioView = document.getElementById('studio-view');
  studioView.classList.remove('active');
  websiteView.classList.remove('hidden');
  window.scrollTo(0, 0);
}

let toastTimeout = null;
function showToast(msg, type = 'info') {
  const t = document.getElementById('app-toast');
  if (!t) return;
  clearTimeout(toastTimeout);
  t.textContent = (type === 'error' ? '⚠️ ' : (type === 'success' ? '✅ ' : 'ℹ️ ')) + msg;
  t.style.display = 'block';
  toastTimeout = setTimeout(() => { t.style.display = 'none'; }, 3800);
}

function updateUserBadge(user) {
  const avatar = document.getElementById('user-avatar-badge');
  const name = document.getElementById('user-name-badge');
  if (avatar && user) avatar.textContent = (user.name || 'U')[0].toUpperCase();
  if (name && user) name.textContent = user.name || 'Pro Member';
}
