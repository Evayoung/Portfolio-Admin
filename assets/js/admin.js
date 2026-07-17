/* admin.js — Neo Admin orchestrator
   Loads modular feature scripts from /assets/js/modules/.
   Each module is a self-contained IIFE-style file with global init functions.
   ─────────────────────────────────────────────────────────────────────────── */

/* ── PWA install prompt ─────────────────────────────────── */

let installPrompt = null;

const installTriggers = [
  () => document.querySelector("[data-install-trigger='sidebar']"),
  () => document.querySelector("[data-install-trigger='mobile']"),
  () => document.querySelector("[data-install-trigger='drawer']"),
];

function setInstallVisibility(visible) {
  installTriggers.forEach((getter) => {
    const node = getter();
    if (!node) return;
    node.dataset.installPromptAvailable = visible ? "true" : "false";
  });
}

function openInstallDrawer() {
  const drawer =
    document.querySelector("[data-install-drawer]") ||
    document.getElementById("adminInstallDrawer");
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

/* ── DOMContentLoaded — init all modules ───────────────── */

window.addEventListener("DOMContentLoaded", () => {
  // PWA install triggers
  installTriggers.forEach((getter) => {
    const node = getter();
    if (!node) return;
    node.addEventListener("click", handleInstallClick);
  });
  setInstallVisibility(false);

  // Utilities (clipboard, panel toggle, keyboard, image preview, guards, form loading)
  initClipboardCopy();
  initPanelToggle();
  initKeyboardShortcuts();
  initImagePreview();
  initFormLoading();

  // Feature modules
  initApplyDraft();
  initLineItemsEditor();
  initDealSections();

  // Toasts + modal feedback
  initToasts();
  initModalSaveFeedback();

  // Safety
  initUnsavedGuard();
  initSessionWarning();
});
