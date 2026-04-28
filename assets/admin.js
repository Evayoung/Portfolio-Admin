/* admin.js — Neo Admin interactive behaviours */

/* ── PWA install prompt ─────────────────────────────────── */

let installPrompt = null;

const installTriggers = [
  () => document.getElementById("install-app-trigger"),
  () => document.getElementById("install-app-trigger-mobile"),
  () => document.getElementById("install-app-trigger-drawer"),
];

function setInstallVisibility(visible) {
  installTriggers.forEach((getter) => {
    const node = getter();
    if (!node) return;
    node.dataset.installPromptAvailable = visible ? "true" : "false";
  });
}

function openInstallDrawer() {
  const drawer = document.getElementById("adminInstallDrawer");
  if (!drawer || !window.bootstrap?.Offcanvas) return;
  window.bootstrap.Offcanvas.getOrCreateInstance(drawer).show();
}

async function handleInstallClick(event) {
  event.preventDefault();
  if (!installPrompt) {
    openInstallDrawer();
    return;
  }
  installPrompt.prompt();
  await installPrompt.userChoice.catch(() => null);
  installPrompt = null;
  setInstallVisibility(false);
}

window.addEventListener("beforeinstallprompt", (event) => {
  event.preventDefault();
  installPrompt = event;
  setInstallVisibility(true);
});

window.addEventListener("appinstalled", () => {
  installPrompt = null;
  setInstallVisibility(false);
});

/* ── Clipboard copy — [data-copy-target] handler ─────────── */

function initClipboardCopy() {
  document.addEventListener("click", function (e) {
    const btn = e.target.closest("[data-copy-target]");
    if (!btn) return;
    const text = btn.dataset.copyTarget;
    const label = btn.dataset.copyLabel || btn.textContent.trim();
    navigator.clipboard
      .writeText(text)
      .then(() => {
        btn.textContent = "Copied!";
        setTimeout(() => {
          btn.textContent = label;
        }, 1800);
      })
      .catch(() => {
        btn.textContent = "Copy failed";
        setTimeout(() => {
          btn.textContent = label;
        }, 2000);
      });
  });
}

/* ── Mobile panel toggle (list ↔ editor) ─────────────────── */

function initPanelToggle() {
  document.querySelectorAll("[data-panel-toggle]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const targetId = btn.dataset.panelToggle;
      const target = document.getElementById(targetId);
      if (!target) return;
      const isHidden = target.classList.toggle("admin-panel-hidden");
      btn.textContent = isHidden ? "Show Editor ↓" : "Hide Editor ↑";
      if (!isHidden) {
        setTimeout(() => target.scrollIntoView({ behavior: "smooth", block: "start" }), 80);
      }
    });
  });
}

/* ── Keyboard shortcut hint modal ────────────────────────── */

function initKeyboardShortcuts() {
  document.addEventListener("keydown", (e) => {
    // Don't fire inside inputs / textareas
    if (e.target.closest("input, textarea, select, [contenteditable]")) return;
    if (e.key === "?") {
      const modal = document.getElementById("admin-shortcuts-modal");
      if (modal && window.bootstrap?.Modal) {
        window.bootstrap.Modal.getOrCreateInstance(modal).show();
      }
    }
    // Quick navigation: g then d/s/p/b/m
    if (e.key === "g") {
      window._adminNavKey = true;
      setTimeout(() => { window._adminNavKey = false; }, 1200);
    }
    if (window._adminNavKey) {
      const routes = { d: "/deals", s: "/submissions", p: "/projects", b: "/blog", m: "/media" };
      if (routes[e.key]) {
        window.location.href = routes[e.key];
        window._adminNavKey = false;
      }
    }
  });
}

/* ── DOMContentLoaded init ───────────────────────────────── */

window.addEventListener("DOMContentLoaded", () => {
  // PWA install triggers
  installTriggers.forEach((getter) => {
    const node = getter();
    if (!node) return;
    node.addEventListener("click", handleInstallClick);
  });
  setInstallVisibility(false);

  // Clipboard
  initClipboardCopy();

  // Panel toggle
  initPanelToggle();

  // Keyboard shortcuts
  initKeyboardShortcuts();
});
