/* utilities.js — Clipboard, Panel Toggle, Keyboard Shortcuts, Image Preview, Session Guard */

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
        setTimeout(() => { btn.textContent = label; }, 1800);
      })
      .catch(() => {
        btn.textContent = "Copy failed";
        setTimeout(() => { btn.textContent = label; }, 2000);
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
    if (e.target.closest("input, textarea, select, [contenteditable]")) return;
    if (e.key === "?") {
      const modal =
        document.querySelector("[data-shortcut-modal]") ||
        document.getElementById("admin-shortcuts-modal");
      if (modal && window.bootstrap?.Modal) {
        window.bootstrap.Modal.getOrCreateInstance(modal).show();
      }
    }
    if (e.key === "g") {
      window._adminNavKey = true;
      setTimeout(() => { window._adminNavKey = false; }, 600);
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

/* ── Image upload preview ─────────────────────────────────── */

function initImagePreview() {
  document.addEventListener("change", function (e) {
    const input = e.target.closest("[data-preview-target]");
    if (!input || !input.files || !input.files[0]) return;
    const previewId = input.dataset.previewTarget;
    const img =
      document.querySelector("[data-preview-image='" + previewId + "']") ||
      document.getElementById(previewId);
    if (!img) return;
    const file = input.files[0];
    if (!file.type.startsWith("image/")) return;
    const reader = new FileReader();
    reader.onload = function (ev) {
      img.src = ev.target.result;
      img.classList.remove("d-none");
    };
    reader.readAsDataURL(file);
  });
}

/* ── Unsaved Changes Guard ──────────────────────────────── */

function initUnsavedGuard() {
  let isDirty = false;

  document.addEventListener("input", (e) => {
    if (e.target.closest("form")) isDirty = true;
  });
  document.addEventListener("change", (e) => {
    if (e.target.closest("form")) isDirty = true;
  });
  document.addEventListener("htmx:afterRequest", (e) => {
    if (e.detail.successful) isDirty = false;
  });

  window.addEventListener("beforeunload", (e) => {
    if (isDirty) {
      e.preventDefault();
      e.returnValue = "";
    }
  });
}

/* ── Session Expiry Warning ─────────────────────────────── */

function initSessionWarning() {
  const meta = document.querySelector('meta[name="session-expires-at"]');
  if (!meta) return;
  const expiresAt = parseInt(meta.content, 10);
  if (!expiresAt) return;

  function checkExpiry() {
    const now = Math.floor(Date.now() / 1000);
    const remaining = expiresAt - now;
    if (remaining > 0 && remaining <= 600 && !window._sessionWarningShown) {
      window._sessionWarningShown = true;
      const minutes = Math.ceil(remaining / 60);
      showConfirm(
        "Your session expires in " + minutes + " minute(s). Stay signed in?",
        function () { window.location.reload(); },
        function () { window.location.href = "/login"; },
        { title: "Session Expiring", confirmText: "Stay Signed In", cancelText: "Sign Out", variant: "warning" }
      );
    }
    if (remaining <= 0) {
      window.location.href = "/login";
    }
  }

  setInterval(checkExpiry, 30000);
}

/* ── Form submit loading states (port from datascience_admin) ── */

function initFormLoading() {
  document.addEventListener("submit", function (e) {
    var form = e.target;
    if (form.tagName !== "FORM") return;
    var btn = form.querySelector('button[type="submit"]');
    if (btn && !btn.classList.contains("btn-outline-danger") && !btn.classList.contains("btn-close")) {
      btn.classList.add("is-loading");
      btn.disabled = true;
    }
  });
  document.addEventListener("htmx:afterRequest", function (e) {
    if (e.detail.successful) {
      document.querySelectorAll("button.is-loading").forEach(function (btn) {
        btn.classList.remove("is-loading");
        btn.disabled = false;
      });
    }
  });
}

/* ── Branded Confirm Dialog (replaces native confirm()) ── */

function showConfirm(message, onConfirm, onCancel, opts) {
  opts = opts || {};
  var title = opts.title || "Confirm";
  var confirmText = opts.confirmText || "Confirm";
  var cancelText = opts.cancelText || "Cancel";
  var variant = opts.variant || "danger";

  var modalId = "confirm-dialog-" + Date.now();
  var btnVariant = variant === "danger" ? "btn-danger" : variant === "warning" ? "btn-warning" : "btn-primary";

  var modal = document.createElement("div");
  modal.className = "modal fade";
  modal.id = modalId;
  modal.tabIndex = -1;
  modal.innerHTML =
    '<div class="modal-dialog modal-dialog-centered">' +
      '<div class="modal-content">' +
        '<div class="modal-header">' +
          '<h5 class="modal-title">' + title + '</h5>' +
          '<button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>' +
        '</div>' +
        '<div class="modal-body"><p class="mb-0">' + message + '</p></div>' +
        '<div class="modal-footer">' +
          '<button type="button" class="btn btn-secondary" data-bs-dismiss="modal">' + cancelText + '</button>' +
          '<button type="button" class="btn ' + btnVariant + '" id="' + modalId + '-confirm">' + confirmText + '</button>' +
        '</div>' +
      '</div>' +
    '</div>';

  document.body.appendChild(modal);

  var bsModal = new bootstrap.Modal(modal);
  bsModal.show();

  modal.querySelector("#" + modalId + "-confirm").addEventListener("click", function () {
    bsModal.hide();
    if (onConfirm) onConfirm();
  });

  modal.addEventListener("hidden.bs.modal", function () {
    if (onCancel) onCancel();
    modal.remove();
  });
}
