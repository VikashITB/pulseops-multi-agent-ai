// frontend/script.js
// PulseOps Elite — Real backend auth + all original functionality preserved

"use strict";

/* ─────────────────────────────────────────
   API BASE
───────────────────────────────────────── */

const API_BASE = "https://pulseops-multi-agent-ai.onrender.com/api/v1";

/* ─────────────────────────────────────────
   INIT ON DOM READY
───────────────────────────────────────── */

document.addEventListener("DOMContentLoaded", () => {
  injectModalStyles();
  injectModalHTML();
  initSidebar();
  initCardTracking();
  initAuthUI();
  initCharCounter();
  setStatus("IDLE");
  setDot("#2e3f5e");
  drawSparkline();
});

/* ─────────────────────────────────────────
   DOM REFERENCES
───────────────────────────────────────── */

const taskInput        = document.getElementById("taskInput");
const submitBtn        = document.getElementById("submitBtn");
const charCount        = document.getElementById("charCount");
const progressLog      = document.getElementById("progressLog");
const outputBlock      = document.getElementById("outputBlock");
const connectionStatus = document.getElementById("connectionStatus");
const statusLabel      = document.getElementById("statusLabel");
const taskIdDisplay    = document.getElementById("taskIdDisplay");
const footerTaskCount  = document.getElementById("footerTaskCount");
const progressBarFill  = document.getElementById("progressBarFill");
const progressBarGlow  = document.getElementById("progressBarGlow");
const progressPct      = document.getElementById("progressPct");
const copyBtn          = document.getElementById("copyBtn");
const clearBtn         = document.getElementById("clearBtn");
const exportTxtBtn     = document.getElementById("exportTxtBtn");
const exportPdfBtn     = document.getElementById("exportPdfBtn");
const typingIndicator  = document.getElementById("typingIndicator");
const toastContainer   = document.getElementById("toastContainer");
const sidebar          = document.getElementById("sidebar");
const sidebarToggle    = document.getElementById("sidebarToggle");
const sidebarOverlay   = document.getElementById("sidebarOverlay");
const sidebarList      = document.getElementById("sidebarList");
const sidebarEmpty     = document.getElementById("sidebarEmpty");
const statSessions     = document.getElementById("statSessions");
const statQueries      = document.getElementById("statQueries");
const historySearch    = document.getElementById("historySearch");
const navModeBadge     = document.getElementById("navModeBadge");

/* ─────────────────────────────────────────
   STATE
───────────────────────────────────────── */

let activeEventSource = null;
let totalTasks    = 0;
let totalQueries  = 0;
let tasksDone     = 0;
let tasksFailed   = 0;
let taskStartTime = null;
let totalMs       = 0;

/* ─────────────────────────────────────────
   SIDEBAR
───────────────────────────────────────── */

function initSidebar() {
  sidebarToggle.addEventListener("click", toggleSidebar);
  sidebarOverlay.addEventListener("click", closeSidebar);
  historySearch.addEventListener("input", filterHistory);

  const clearHistoryBtn = document.getElementById("clearHistoryBtn");
  if (clearHistoryBtn) {
    clearHistoryBtn.addEventListener("click", clearHistory);
  }
}

function toggleSidebar() {
  const isOpen = sidebar.classList.toggle("show");
  sidebarOverlay.classList.toggle("show", isOpen);
  sidebarToggle.classList.toggle("active", isOpen);
  sidebarToggle.setAttribute("aria-expanded", isOpen);
}

function closeSidebar() {
  sidebar.classList.remove("show");
  sidebarOverlay.classList.remove("show");
  sidebarToggle.classList.remove("active");
  sidebarToggle.setAttribute("aria-expanded", false);
}

function clearHistory() {
  sidebarList.innerHTML = "";
  sidebarEmpty.style.display = "flex";
  showToast("History cleared", "info");
}

/* ─────────────────────────────────────────
   CARD MOUSE TRACKING (glassmorphism glow)
───────────────────────────────────────── */

function initCardTracking() {
  document.querySelectorAll(".card").forEach(card => {
    card.addEventListener("mousemove", e => {
      const rect = card.getBoundingClientRect();
      card.style.setProperty("--mouse-x", `${e.clientX - rect.left}px`);
      card.style.setProperty("--mouse-y", `${e.clientY - rect.top}px`);
    });
  });
}

/* ═══════════════════════════════════════════
   AUTH — MODAL INJECTION
   (keeps index.html untouched)
═══════════════════════════════════════════ */

function injectModalStyles() {
  const style = document.createElement("style");
  style.id = "pulseops-auth-styles";
  style.textContent = `
    /* Auth Modal Overlay */
    .auth-modal-overlay {
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.75);
      backdrop-filter: blur(8px);
      -webkit-backdrop-filter: blur(8px);
      z-index: 200;
      display: flex;
      align-items: center;
      justify-content: center;
      opacity: 0;
      pointer-events: none;
      transition: opacity 0.25s cubic-bezier(0.4,0,0.2,1);
    }
    .auth-modal-overlay.open {
      opacity: 1;
      pointer-events: all;
    }

    /* Auth Modal Box */
    .auth-modal {
      width: 100%;
      max-width: 420px;
      background: #05080f;
      border: 1px solid rgba(79,132,255,0.18);
      border-radius: 24px;
      padding: 38px 34px 34px;
      box-shadow: 0 40px 100px rgba(0,0,0,0.7), 0 0 0 1px rgba(255,255,255,0.04) inset;
      transform: translateY(20px) scale(0.97);
      transition: transform 0.3s cubic-bezier(0.4,0,0.2,1);
      position: relative;
      margin: 16px;
    }
    .auth-modal-overlay.open .auth-modal {
      transform: translateY(0) scale(1);
    }

    /* Top shimmer */
    .auth-modal::before {
      content: "";
      position: absolute;
      top: 0; left: 0; right: 0;
      height: 1px;
      border-radius: 24px 24px 0 0;
      background: linear-gradient(90deg,
        transparent,
        rgba(79,132,255,0.5),
        rgba(139,92,246,0.5),
        transparent
      );
    }

    /* Close button */
    .auth-modal-close {
      position: absolute;
      top: 16px; right: 16px;
      width: 30px; height: 30px;
      border-radius: 8px;
      border: 1px solid rgba(255,255,255,0.07);
      background: rgba(255,255,255,0.04);
      color: #5a7099;
      font-size: 15px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: 0.2s;
      line-height: 1;
      padding: 0;
    }
    .auth-modal-close:hover {
      background: rgba(239,68,68,0.1);
      color: #fca5a5;
      border-color: rgba(239,68,68,0.2);
      transform: none;
      box-shadow: none;
    }

    /* Modal header */
    .auth-modal-icon {
      width: 48px; height: 48px;
      border-radius: 14px;
      background: linear-gradient(135deg, #4f84ff, #8b5cf6);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 22px;
      margin-bottom: 20px;
      box-shadow: 0 4px 24px rgba(79,132,255,0.35);
    }
    .auth-modal h2 {
      font-family: 'Syne', sans-serif;
      font-size: 22px;
      font-weight: 800;
      color: #edf2ff;
      margin-bottom: 4px;
      letter-spacing: -0.5px;
    }
    .auth-modal-sub {
      font-size: 13px;
      color: #5a7099;
      margin-bottom: 28px;
    }
    .auth-modal-sub a {
      color: #7aaeff;
      cursor: pointer;
      text-decoration: none;
      font-weight: 600;
    }
    .auth-modal-sub a:hover { text-decoration: underline; }

    /* Form fields */
    .auth-field {
      display: flex;
      flex-direction: column;
      gap: 6px;
      margin-bottom: 14px;
    }
    .auth-field label {
      font-size: 11.5px;
      font-weight: 700;
      color: #5a7099;
      text-transform: uppercase;
      letter-spacing: 0.07em;
    }
    .auth-field input {
      padding: 12px 14px;
      border-radius: 11px;
      border: 1px solid rgba(255,255,255,0.07);
      background: rgba(255,255,255,0.04);
      color: #edf2ff;
      font-family: 'DM Sans', sans-serif;
      font-size: 14px;
      outline: none;
      transition: border-color 0.2s, background 0.2s, box-shadow 0.2s;
      width: 100%;
      box-sizing: border-box;
    }
    .auth-field input::placeholder { color: #2e3f5e; }
    .auth-field input:focus {
      border-color: rgba(79,132,255,0.45);
      background: rgba(79,132,255,0.05);
      box-shadow: 0 0 0 3px rgba(79,132,255,0.08);
    }
    .auth-field input.error { border-color: rgba(239,68,68,0.5); }

    /* Error message */
    .auth-error {
      display: none;
      align-items: center;
      gap: 7px;
      padding: 10px 14px;
      border-radius: 10px;
      background: rgba(239,68,68,0.08);
      border: 1px solid rgba(239,68,68,0.18);
      color: #fca5a5;
      font-size: 13px;
      margin-bottom: 14px;
      animation: authFadeIn 0.2s ease;
    }
    .auth-error.visible { display: flex; }

    /* Submit button */
    .auth-submit {
      width: 100%;
      padding: 13px;
      border-radius: 12px;
      border: none;
      background: linear-gradient(135deg, #4f84ff 0%, #8b5cf6 100%);
      color: white;
      font-family: 'Syne', sans-serif;
      font-size: 14px;
      font-weight: 800;
      cursor: pointer;
      transition: 0.25s;
      margin-top: 4px;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      box-shadow: 0 4px 20px rgba(79,132,255,0.3), inset 0 1px 0 rgba(255,255,255,0.15);
      position: relative; overflow: hidden;
    }
    .auth-submit::after {
      content: "";
      position: absolute; inset: 0;
      background: linear-gradient(180deg, rgba(255,255,255,0.08) 0%, transparent 50%);
      pointer-events: none;
    }
    .auth-submit:hover:not(:disabled) {
      transform: translateY(-2px);
      box-shadow: 0 10px 32px rgba(79,132,255,0.48), inset 0 1px 0 rgba(255,255,255,0.15);
    }
    .auth-submit:disabled {
      opacity: 0.6;
      cursor: not-allowed;
      transform: none;
    }

    /* Spinner inside button */
    .auth-spinner {
      width: 15px; height: 15px;
      border: 2px solid rgba(255,255,255,0.3);
      border-top-color: white;
      border-radius: 50%;
      animation: authSpin 0.7s linear infinite;
      display: none;
    }
    .auth-spinner.show { display: block; }

    @keyframes authSpin { to { transform: rotate(360deg); } }
    @keyframes authFadeIn {
      from { opacity: 0; transform: translateY(-4px); }
      to   { opacity: 1; transform: translateY(0); }
    }
  `;
  document.head.appendChild(style);
}

function injectModalHTML() {
  const overlay = document.createElement("div");
  overlay.id = "authModalOverlay";
  overlay.className = "auth-modal-overlay";
  overlay.setAttribute("role", "dialog");
  overlay.setAttribute("aria-modal", "true");

  overlay.innerHTML = `
    <div class="auth-modal" id="authModal">
      <button class="auth-modal-close" id="authModalClose" aria-label="Close">✕</button>

      <div class="auth-modal-icon">⚡</div>
      <h2 id="authModalTitle">Welcome back</h2>
      <p class="auth-modal-sub" id="authModalSub">
        No account? <a id="authModalSwitch">Sign up free</a>
      </p>

      <!-- Name field (signup only) -->
      <div class="auth-field" id="authNameField" style="display:none">
        <label for="authNameInput">Full Name</label>
        <input type="text" id="authNameInput" placeholder="Vikash Gupta" autocomplete="name" />
      </div>

      <div class="auth-field">
        <label for="authEmailInput">Email</label>
        <input type="email" id="authEmailInput" placeholder="you@example.com" autocomplete="email" />
      </div>

      <div class="auth-field">
        <label for="authPasswordInput">Password</label>
        <input type="password" id="authPasswordInput" placeholder="••••••••" autocomplete="current-password" />
      </div>

      <div class="auth-error" id="authError">
        <span>⚠</span>
        <span id="authErrorMsg">Invalid credentials</span>
      </div>

      <button class="auth-submit" id="authSubmitBtn">
        <div class="auth-spinner" id="authSpinner"></div>
        <span id="authSubmitLabel">Sign In</span>
      </button>
    </div>
  `;

  document.body.appendChild(overlay);

  overlay.addEventListener("click", e => {
    if (e.target === overlay) closeAuthModal();
  });

  document.getElementById("authModalClose").addEventListener("click", closeAuthModal);
  document.getElementById("authModalSwitch").addEventListener("click", toggleAuthMode);

  overlay.addEventListener("keydown", e => {
    if (e.key === "Enter") document.getElementById("authSubmitBtn").click();
    if (e.key === "Escape") closeAuthModal();
  });
}

/* ═══════════════════════════════════════════
   AUTH — REAL BACKEND INTEGRATION
═══════════════════════════════════════════ */

async function initAuthUI() {
  const loginBtn  = document.getElementById("loginBtn");
  const signupBtn = document.getElementById("signupBtn");
  const logoutBtn = document.getElementById("logoutBtn");

  if (loginBtn)  loginBtn.addEventListener("click",  handleLogin);
  if (signupBtn) signupBtn.addEventListener("click",  handleSignup);
  if (logoutBtn) logoutBtn.addEventListener("click",  handleLogout);

  const submitBtn = document.getElementById("authSubmitBtn");
  if (submitBtn) submitBtn.addEventListener("click", handleAuthSubmit);

  const token = getToken();
  if (token) await restoreSession(token);
}

function handleLogin()  { openAuthModal("login");  }
function handleSignup() { openAuthModal("signup"); }

function handleLogout() {
  clearToken();
  clearUser();
  showLoggedOut();
  showToast("Signed out", "info");
}

let _authMode = "login";

function openAuthModal(mode = "login") {
  _authMode = mode;
  _applyAuthMode();
  _clearAuthForm();
  const overlay = document.getElementById("authModalOverlay");
  if (overlay) {
    overlay.classList.add("open");
    overlay.onclick = e => { if (e.target === overlay) closeAuthModal(); };
    overlay.onkeydown = e => { if (e.key === "Escape") closeAuthModal(); };
  }
  const closeBtn = document.getElementById("authModalClose");
  if (closeBtn) closeBtn.onclick = closeAuthModal;

  const switchLink = document.getElementById("authModalSwitch");
  if (switchLink) switchLink.onclick = toggleAuthMode;

  setTimeout(() => {
    const first = _authMode === "signup"
      ? document.getElementById("authNameInput")
      : document.getElementById("authEmailInput");
    first?.focus();
  }, 80);
}

function closeAuthModal() {
  document.getElementById("authModalOverlay")?.classList.remove("open");
  _clearAuthForm();
}

function toggleAuthMode() {
  _authMode = _authMode === "login" ? "signup" : "login";
  _applyAuthMode();
  _clearAuthForm();
  document.getElementById("authModalSwitch").onclick = toggleAuthMode;
}

function _applyAuthMode() {
  const isSignup = _authMode === "signup";
  const title    = document.getElementById("authModalTitle");
  const sub      = document.getElementById("authModalSub");
  const label    = document.getElementById("authSubmitLabel");
  const nameWrap = document.getElementById("authNameField");
  const pwInput  = document.getElementById("authPasswordInput");

  if (title)    title.textContent  = isSignup ? "Create account"  : "Welcome back";
  if (label)    label.textContent  = isSignup ? "Create Account"  : "Sign In";
  if (nameWrap) nameWrap.style.display = isSignup ? "flex" : "none";
  if (pwInput)  pwInput.setAttribute("autocomplete", isSignup ? "new-password" : "current-password");
  if (sub) {
    sub.innerHTML = isSignup
      ? `Already have an account? <a id="authModalSwitch">Sign in</a>` 
      : `No account? <a id="authModalSwitch">Sign up free</a>`;
  }
}

function _clearAuthForm() {
  ["authNameInput", "authEmailInput", "authPasswordInput"].forEach(id => {
    const el = document.getElementById(id);
    if (el) { el.value = ""; el.classList.remove("error"); }
  });
  _setAuthError(null);
  _setAuthLoading(false);
}

function _setAuthError(msg) {
  const box = document.getElementById("authError");
  const txt = document.getElementById("authErrorMsg");
  if (!box) return;
  if (msg) {
    if (txt) txt.textContent = msg;
    box.classList.add("visible");
  } else {
    box.classList.remove("visible");
  }
}

function _setAuthLoading(on) {
  const btn     = document.getElementById("authSubmitBtn");
  const spinner = document.getElementById("authSpinner");
  const label   = document.getElementById("authSubmitLabel");
  if (btn)     btn.disabled = on;
  if (spinner) spinner.classList.toggle("show", on);
  if (label && on) label.textContent = _authMode === "signup" ? "Creating…" : "Signing in…";
  if (label && !on) label.textContent = _authMode === "signup" ? "Create Account" : "Sign In";
}

async function handleAuthSubmit() {
  _setAuthError(null);

  const email    = document.getElementById("authEmailInput")?.value.trim()  || "";
  const password = document.getElementById("authPasswordInput")?.value       || "";
  const name     = document.getElementById("authNameInput")?.value.trim()   || "";

  if (!email || !password) {
    _setAuthError("Email and password are required.");
    return;
  }
  if (!/\S+@\S+\.\S+/.test(email)) {
    document.getElementById("authEmailInput")?.classList.add("error");
    _setAuthError("Please enter a valid email address.");
    return;
  }
  if (_authMode === "signup" && !name) {
    document.getElementById("authNameInput")?.classList.add("error");
    _setAuthError("Please enter your full name.");
    return;
  }

  _setAuthLoading(true);
  _authMode === "signup"
    ? await apiRegister(name, email, password)
    : await apiLogin(email, password);
  _setAuthLoading(false);
}

async function apiRegister(name, email, password) {
  try {
    const res  = await fetch(`${API_BASE}/auth/register`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ full_name: name, email, password })
    });
    const data = await res.json();

    if (!res.ok) {
      _setAuthError(
        typeof data.detail === "string"
          ? data.detail
          : Array.isArray(data.detail)
            ? data.detail.map(e => e.msg).join(", ")
            : "Request failed"
      || data.message || "Registration failed.");
      return;
    }

    showToast("Account created!", "success");
    await apiLogin(email, password);

  } catch (_) {
    _setAuthError("Network error. Please try again.");
  }
}

async function apiLogin(email, password) {
  try {
    const res  = await fetch(`${API_BASE}/auth/login`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ email, password })
    });
    const data = await res.json();

    if (!res.ok) {
      _setAuthError(
        typeof data.detail === "string"
          ? data.detail
          : Array.isArray(data.detail)
            ? data.detail.map(e => e.msg).join(", ")
            : "Request failed"
      || data.message || "Invalid email or password.");
      return;
    }

    const token = data.access_token || data.token || data.jwt;
    if (!token) {
      _setAuthError("Auth error: no token in response.");
      return;
    }

    saveToken(token);

    const user = await fetchMe(token);
    const displayName  = user?.name || user?.full_name || email.split("@")[0];
    const displayEmail = user?.email || email;

    saveUser(displayName, displayEmail);
    showLoggedIn(displayName, displayEmail);
    showToast(`Welcome, ${displayName}!`, "success");
    closeAuthModal();
    closeSidebar();

  } catch (_) {
    _setAuthError("Network error. Please try again.");
  }
}

async function restoreSession(token) {
  const user = await fetchMe(token);
  if (!user) {
    clearToken();
    clearUser();
    return;
  }
  const name  = user.name || user.full_name || user.email?.split("@")[0] || "User";
  const email = user.email || "";
  saveUser(name, email);
  showLoggedIn(name, email);
}

async function fetchMe(token) {
  try {
    const res = await fetch(`${API_BASE}/auth/me`, {
      headers: { "Authorization": `Bearer ${token}` }
    });
    return res.ok ? await res.json() : null;
  } catch (_) {
    return null;
  }
}

function showLoggedIn(name, email) {
  document.getElementById("authLoggedOut")?.classList.add("hidden");
  document.getElementById("authLoggedIn")?.classList.remove("hidden");

  const initial = document.getElementById("avatarInitial");
  const dispName  = document.getElementById("displayName");
  const dispEmail = document.getElementById("displayEmail");

  if (initial)   initial.textContent  = name.charAt(0).toUpperCase();
  if (dispName)  dispName.textContent  = name;
  if (dispEmail) dispEmail.textContent = email;
}

function showLoggedOut() {
  document.getElementById("authLoggedOut")?.classList.remove("hidden");
  document.getElementById("authLoggedIn")?.classList.add("hidden");
}

function saveToken(t)  { try { localStorage.setItem("pulseops_token", t);                      } catch (_) {} }
function getToken()    { try { return localStorage.getItem("pulseops_token");                   } catch (_) { return null; } }
function clearToken()  { try { localStorage.removeItem("pulseops_token");                       } catch (_) {} }
function saveUser(n,e) { try { localStorage.setItem("pulseops_user", JSON.stringify({name:n, email:e})); } catch (_) {} }
function getSavedUser(){ try { return JSON.parse(localStorage.getItem("pulseops_user"));        } catch (_) { return null; } }
function clearUser()   { try { localStorage.removeItem("pulseops_user");                        } catch (_) {} }

/* ─────────────────────────────────────────
   CHAR COUNTER
───────────────────────────────────────── */

function initCharCounter() {
  taskInput.addEventListener("input", () => {
    charCount.textContent = taskInput.value.length;
  });
}

/* ─────────────────────────────────────────
   HELPERS
───────────────────────────────────────── */

function setStatus(text) {
  if (statusLabel) statusLabel.textContent = text;
}

function setDot(color, pulse = false) {
  if (!connectionStatus) return;
  connectionStatus.style.background = color;
  connectionStatus.classList.toggle("pulse", pulse);
}

function setProgress(percent) {
  if (progressBarFill) progressBarFill.style.width = `${percent}%`;
  if (progressBarGlow) progressBarGlow.style.opacity = percent > 0 && percent < 100 ? "1" : "0";
  if (progressPct) progressPct.textContent = `${percent}%`;
}

function showTyping(show = true) {
  if (typingIndicator) typingIndicator.style.display = show ? "flex" : "none";
}

function setModeBadge(mode) {
  if (!navModeBadge) return;
  navModeBadge.className = "nav-mode-badge";
  if (mode === "fast") {
    navModeBadge.classList.add("fast");
    navModeBadge.textContent = "⚡ FAST";
  } else if (mode === "full") {
    navModeBadge.classList.add("full");
    navModeBadge.textContent = "🔬 FULL";
  }
}

function clearModeBadge() {
  if (navModeBadge) navModeBadge.className = "nav-mode-badge";
}

function addLog(text, type = "normal") {
  if (!progressLog) return;
  const row = document.createElement("div");
  row.className = `log-row ${type}`;
  row.textContent = text;
  progressLog.prepend(row);
}

function showToast(message, type = "info") {
  if (!toastContainer) return;
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  const iconMap = { success: "✓", error: "✕", info: "i" };
  toast.innerHTML = `<div class="toast-icon">${iconMap[type] || "i"}</div><span>${message}</span>`;
  toastContainer.appendChild(toast);
  setTimeout(() => {
    toast.style.animation = "toastSlideOut 0.28s cubic-bezier(0.4,0,0.2,1) forwards";
    setTimeout(() => toast.remove(), 280);
  }, 3200);
}

function addSession(prompt) {
  if (!sidebarList || !sidebarEmpty) return;
  sidebarEmpty.style.display = "none";

  const item = document.createElement("div");
  item.className = "session-item";
  const now  = new Date();
  const time = now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  item.innerHTML = `
    <div>${prompt.slice(0, 52)}${prompt.length > 52 ? "…" : ""}</div>
    <span class="session-timestamp">${time}</span>
  `;
  item.addEventListener("click", () => {
    taskInput.value = prompt;
    charCount.textContent = prompt.length;
    closeSidebar();
  });
  sidebarList.prepend(item);

  totalTasks++;
  if (statSessions) statSessions.textContent = totalTasks;
  if (footerTaskCount) footerTaskCount.textContent = `${totalTasks} task${totalTasks !== 1 ? "s" : ""} dispatched`;
}

function updateQueries() {
  totalQueries++;
  if (statQueries) statQueries.textContent = totalQueries;
}

function filterHistory() {
  const q = historySearch.value.toLowerCase();
  sidebarList.querySelectorAll(".session-item").forEach(item => {
    item.style.display = item.textContent.toLowerCase().includes(q) ? "block" : "none";
  });
}

/* ─────────────────────────────────────────
   SPARKLINE
───────────────────────────────────────── */

const sparklineData = [];

function drawSparkline() {
  const canvas = document.getElementById("sparklineCanvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const W = canvas.width, H = canvas.height;
  ctx.clearRect(0, 0, W, H);

  if (sparklineData.length < 2) {
    // Draw flat baseline
    ctx.beginPath();
    ctx.moveTo(0, H - 2); ctx.lineTo(W, H - 2);
    ctx.strokeStyle = "rgba(79,132,255,0.25)";
    ctx.lineWidth = 1.5;
    ctx.stroke();
    return;
  }

  const max = Math.max(...sparklineData) || 1;
  const min = Math.min(...sparklineData);
  const range = max - min || 1;
  const pts = sparklineData.map((v, i) => ({
    x: (i / (sparklineData.length - 1)) * W,
    y: H - 3 - ((v - min) / range) * (H - 6)
  }));

  // Fill gradient
  const grad = ctx.createLinearGradient(0, 0, 0, H);
  grad.addColorStop(0, "rgba(79,132,255,0.22)");
  grad.addColorStop(1, "rgba(79,132,255,0)");
  ctx.beginPath();
  ctx.moveTo(pts[0].x, H);
  pts.forEach(p => ctx.lineTo(p.x, p.y));
  ctx.lineTo(pts[pts.length - 1].x, H);
  ctx.closePath();
  ctx.fillStyle = grad;
  ctx.fill();

  // Line
  ctx.beginPath();
  pts.forEach((p, i) => i === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y));
  ctx.strokeStyle = "#7aaeff";
  ctx.lineWidth = 1.8;
  ctx.lineJoin = "round";
  ctx.stroke();

  // End dot
  const last = pts[pts.length - 1];
  ctx.beginPath();
  ctx.arc(last.x, last.y, 2.5, 0, Math.PI * 2);
  ctx.fillStyle = "#7aaeff";
  ctx.fill();
}

/* ─────────────────────────────────────────
   COUNT-UP ANIMATION
───────────────────────────────────────── */

function animateCount(el, target, suffix = "", duration = 600) {
  if (!el) return;
  const start = parseFloat(el.dataset.current || "0") || 0;
  if (start === target) return;
  const startTime = performance.now();
  function step(now) {
    const p = Math.min((now - startTime) / duration, 1);
    const ease = 1 - Math.pow(1 - p, 3); // ease-out-cubic
    const val = start + (target - start) * ease;
    el.textContent = Number.isInteger(target)
      ? Math.round(val) + suffix
      : val.toFixed(1) + suffix;
    if (p < 1) requestAnimationFrame(step);
    else { el.textContent = target + suffix; el.dataset.current = target; }
  }
  requestAnimationFrame(step);
}

function updateMetrics() {
  const done  = document.getElementById("metricTasksDone");
  const avg   = document.getElementById("metricAvgTime");
  const rate  = document.getElementById("metricSuccessRate");
  const trend = document.getElementById("metricSuccessTrend");

  if (done) animateCount(done, tasksDone);

  const attempted = tasksDone + tasksFailed;
  if (attempted > 0 && avg) {
    const ms = Math.round(totalMs / attempted);
    const display = ms >= 1000 ? parseFloat((ms / 1000).toFixed(1)) : ms;
    const suffix  = ms >= 1000 ? "s" : "ms";
    avg.dataset.current = avg.dataset.current || "0";
    animateCount(avg, display, suffix);
  }

  if (attempted > 0 && rate) {
    const pct = Math.round((tasksDone / attempted) * 100);
    animateCount(rate, pct, "%");
    if (trend) {
      trend.textContent = pct >= 90 ? "↑ great" : pct >= 70 ? "↑ good" : "↓ low";
      trend.className = `metric-trend ${pct >= 70 ? "up" : "down"}`;
    }
  }

  // Sparkline — record a data point per completed task
  sparklineData.push(tasksDone);
  if (sparklineData.length > 12) sparklineData.shift();
  drawSparkline();
}

/* ─────────────────────────────────────────
   OUTPUT SHIMMER
───────────────────────────────────────── */

function showOutputShimmer(show) {
  const shimmer = document.getElementById("outputShimmer");
  const output  = document.getElementById("outputBlock");
  if (!shimmer) return;
  shimmer.classList.toggle("visible", show);
  if (output) output.style.opacity = show ? "0.15" : "1";
}

function failState() {
  tasksFailed++;
  if (taskStartTime) { totalMs += Date.now() - taskStartTime; taskStartTime = null; }
  updateMetrics();
  showOutputShimmer(false);
  submitBtn.disabled = false;
  submitBtn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg> Dispatch Task`;
  setStatus("FAILED");
  setDot("#ef4444", false);
  showTyping(false);
  clearModeBadge();
  if (progressPct) progressPct.textContent = "0%";
}

function completeTask(result) {
  tasksDone++;
  if (taskStartTime) { totalMs += Date.now() - taskStartTime; taskStartTime = null; }
  updateMetrics();
  showOutputShimmer(false);
  outputBlock.textContent = result;
  submitBtn.disabled = false;
  submitBtn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg> Dispatch Task`;
  setStatus("COMPLETED");
  setDot("#10b981", false);
  setProgress(100);
  showTyping(false);
  addLog("Task completed", "success");
  showToast("Task completed", "success");
  setTimeout(clearModeBadge, 4000);
}

/* ─────────────────────────────────────────
   SUBMIT TASK
───────────────────────────────────────── */

async function submitTask() {
  const prompt = taskInput.value.trim();
  if (!prompt) return;

  if (activeEventSource) activeEventSource.close();

  progressLog.innerHTML = "";
  outputBlock.textContent = "";
  taskIdDisplay.textContent = "";

  setProgress(8);
  submitBtn.disabled = true;
  submitBtn.innerHTML = `<span style="display:inline-flex;align-items:center;gap:6px">
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="animation:spin 1s linear infinite">
      <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
    </svg> Running…</span>`;

  setStatus("SUBMITTING");
  setDot("#f59e0b", false);
  showTyping(true);
  showOutputShimmer(true);
  addLog("Task accepted", "success");
  showToast("Task submitted", "info");
  addSession(prompt);
  updateQueries();
  taskStartTime = Date.now();

  try {
    const headers = { "Content-Type": "application/json" };
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const res = await fetch(`${API_BASE}/task`, {
      method: "POST",
      headers,
      body: JSON.stringify({ request: prompt })
    });

    const data = await res.json();
    const taskId = data.task_id || data.id;

    if (!taskId) throw new Error("Task id missing");

    taskIdDisplay.textContent = taskId;

    if (data.mode === "fast" || data.routing === "fast") setModeBadge("fast");
    else if (data.mode === "full" || data.routing === "full") setModeBadge("full");

    openStream(taskId);
  } catch (error) {
    addLog("Submission failed", "error");
    showToast("Submission failed", "error");
    failState();
  }
}

/* ─────────────────────────────────────────
   STREAM
───────────────────────────────────────── */

function openStream(taskId) {
  let completed = false;
  const es = new EventSource(`${API_BASE}/stream/${taskId}`);
  activeEventSource = es;

  es.onopen = () => {
    setStatus("STREAMING");
    setDot("#10b981", true);
    setProgress(20);
    addLog("Live connection established", "success");
    showToast("Connected to stream", "success");
  };

  es.addEventListener("task_started", event => {
    const payload = JSON.parse(event.data);
    if (payload.mode) setModeBadge(payload.mode);
    addLog("Task started");
    setProgress(35);
  });

  es.addEventListener("plan_ready", () => {
    addLog("Plan ready");
    setProgress(45);
  });

  es.addEventListener("step_started", event => {
    const payload = JSON.parse(event.data);
    addLog(payload.message || "Step started");
    setProgress(60);
  });

  es.addEventListener("step_progress", event => {
    const payload = JSON.parse(event.data);
    if (payload.data && payload.data.token) {
      outputBlock.textContent += payload.data.token;
      outputBlock.scrollTop = outputBlock.scrollHeight;
    }
  });

  es.addEventListener("step_completed", event => {
    const payload = JSON.parse(event.data);
    addLog(payload.message || "Step completed");
    setProgress(80);
  });

  es.addEventListener("task_completed", event => {
    completed = true;
    const payload = JSON.parse(event.data);
    const result =
      payload.data?.result ||
      payload.data?.final_output ||
      outputBlock.textContent ||
      "Completed";
    completeTask(result);
    es.close();
  });

  es.addEventListener("task_failed", () => {
    completed = true;
    addLog("Task failed", "error");
    showToast("Task failed", "error");
    failState();
    es.close();
  });

  es.onerror = () => {
    if (!completed) {
      addLog("Connection closed", "error");
      failState();
    }
    es.close();
  };
}

/* ─────────────────────────────────────────
   ACTIONS
───────────────────────────────────────── */

function copyOutput() {
  const text = outputBlock.textContent.trim();
  if (!text || text === "Final result will appear here.") {
    showToast("Nothing to copy", "info");
    return;
  }
  navigator.clipboard.writeText(text).then(() => {
    copyBtn.textContent = "✓ Copied";
    copyBtn.classList.add("success");
    showToast("Copied to clipboard", "success");
    setTimeout(() => {
      copyBtn.innerHTML = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg> Copy`;
      copyBtn.classList.remove("success");
    }, 2200);
  });
}

function clearAll() {
  taskInput.value = "";
  charCount.textContent = "0";
  progressLog.innerHTML = "";
  outputBlock.textContent = "Final result will appear here.";
  setProgress(0);
  setStatus("IDLE");
  setDot("#2e3f5e", false);
  showTyping(false);
  showOutputShimmer(false);
  clearModeBadge();
  if (taskIdDisplay) taskIdDisplay.textContent = "";
  if (progressPct) progressPct.textContent = "0%";
}

function exportTxt() {
  const text = outputBlock.textContent.trim();
  if (!text || text === "Final result will appear here.") {
    showToast("Nothing to export", "info");
    return;
  }
  const blob = new Blob([text], { type: "text/plain" });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement("a");
  a.href = url;
  a.download = `pulseops-${Date.now()}.txt`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
  showToast("Exported as TXT", "success");
}

function exportPdf() {
  const text = outputBlock.textContent.trim();
  if (!text || text === "Final result will appear here.") {
    showToast("Nothing to export", "info");
    return;
  }
  const printWindow = window.open("", "_blank");
  printWindow.document.write(`
    <!DOCTYPE html>
    <html>
    <head>
      <title>PulseOps Export</title>
      <style>
        body { font-family: 'DM Sans', sans-serif; padding: 48px; line-height: 1.8; color: #1a1a2e; max-width: 800px; margin: 0 auto; }
        h2   { font-size: 20px; margin-bottom: 24px; color: #4f84ff; font-family: 'Syne', sans-serif; }
        pre  { white-space: pre-wrap; background: #f4f6fb; padding: 24px; border-radius: 12px; font-size: 14px; border: 1px solid #e2e8f0; }
      </style>
    </head>
    <body>
      <h2>⚡ PulseOps AI — Export</h2>
      <pre>${text}</pre>
    </body>
    </html>
  `);
  printWindow.document.close();
  printWindow.print();
  showToast("PDF export dialog opened", "success");
}

/* ─────────────────────────────────────────
   CSS KEYFRAME for spin (injected once)
───────────────────────────────────────── */

const spinStyle = document.createElement("style");
spinStyle.textContent = "@keyframes spin { to { transform: rotate(360deg); } }";
document.head.appendChild(spinStyle);