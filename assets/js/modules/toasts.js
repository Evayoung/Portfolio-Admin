/* toasts.js — ModernToast auto-dismiss + Bootstrap toast auto-init after HTMX swaps */

function initToasts() {
  function initModernToasts() {
    document.querySelectorAll('[data-fs-modern-toast]:not([data-fs-toast-ready])').forEach(function (el) {
      el.setAttribute("data-fs-toast-ready", "true");
      const duration = parseInt(el.dataset.duration || "4000", 10);
      if (duration > 0) {
        setTimeout(function () {
          el.style.transition = "opacity 0.3s ease, transform 0.3s ease";
          el.style.opacity = "0";
          el.style.transform = "translateX(100%)";
          setTimeout(function () { el.remove(); }, 300);
        }, duration);
      }
    });
  }

  function initBootstrapToasts() {
    if (!window.bootstrap) return;
    document.querySelectorAll(".toast:not([data-fs-toast-ready])").forEach(function (el) {
      el.setAttribute("data-fs-toast-ready", "true");
      try {
        var toast = new bootstrap.Toast(el);
        toast.show();
      } catch (_) { /* silently skip */ }
    });
  }

  // Run on initial load and after HTMX swaps
  initModernToasts();
  initBootstrapToasts();
  document.addEventListener("htmx:afterSwap", function () {
    initModernToasts();
    initBootstrapToasts();
  });
}

/* ── Modal Auto-Save Graceful Reload Interceptor ────────── */

function initModalSaveFeedback() {
  let _pendingModalReload = null;

  document.addEventListener("htmx:beforeProcessResponse", function (evt) {
    const xhr = evt.detail.xhr;
    if (!xhr) return;

    const openModal = document.querySelector(".modal.show");
    if (openModal && xhr.getResponseHeader("HX-Refresh") === "true") {
      const orig = xhr.getResponseHeader.bind(xhr);
      xhr.getResponseHeader = function (name) {
        if (name && name.toLowerCase() === "hx-refresh") return null;
        return orig(name);
      };
      _pendingModalReload = openModal;
    }
  });

  document.addEventListener("htmx:afterRequest", function (evt) {
    if (!_pendingModalReload || !evt.detail.successful) {
      _pendingModalReload = null;
      return;
    }
    const modal = _pendingModalReload;
    _pendingModalReload = null;

    if (window.bootstrap) {
      const bsModal = bootstrap.Modal.getInstance(modal);
      if (bsModal) bsModal.hide();
    }
    setTimeout(() => window.location.reload(), 350);
  });
}
