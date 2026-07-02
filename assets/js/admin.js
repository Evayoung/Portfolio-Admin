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

/* ── AI Draft — Apply to field handler ─────────────────────── */

function initApplyDraft() {
  document.addEventListener("click", function (e) {
    const btn = e.target.closest("[data-apply-field]");
    if (!btn) return;
    const fieldId = btn.dataset.applyField;
    const sourceId = btn.dataset.draftSource;
    const source = document.getElementById(sourceId);
    const target = document.getElementById(fieldId);
    if (source && target) {
      target.value = source.value;
      target.dispatchEvent(new Event("input", { bubbles: true }));
      // Visual feedback
      const orig = btn.textContent;
      btn.textContent = "Applied!";
      setTimeout(() => { btn.textContent = orig; }, 1200);
    }
  });
}

/* ── Line Items Editor — dynamic table with totals, paste, validation ── */

function initLineItemsEditor() {
  document.querySelectorAll('.line-items-editor').forEach((container) => {
    const table = container.querySelector('.line-items-table');
    const hiddenInput = document.getElementById('line_items');
    if (!table || !hiddenInput) return;

    function serialize() {
      const rows = [];
      table.querySelectorAll('tbody tr').forEach((row) => {
        const item = (row.querySelector('.li-item')?.value || '').trim();
        const desc = (row.querySelector('.li-desc')?.value || '').trim();
        const qty = (row.querySelector('.li-qty')?.value || '1').trim();
        const amount = (row.querySelector('.li-amount')?.value || '0').trim();
        if (item) rows.push(item + ' | ' + desc + ' | ' + qty + ' | ' + amount);
      });
      hiddenInput.value = rows.join('\n');
      updateTotal();
    }

    function updateTotal() {
      let total = 0;
      table.querySelectorAll('tbody tr').forEach((row) => {
        const qty = parseInt(row.querySelector('.li-qty')?.value) || 0;
        const amount = parseInt(row.querySelector('.li-amount')?.value) || 0;
        total += qty * amount;
      });
      const totalCell = container.querySelector('.li-total-value');
      if (totalCell) totalCell.textContent = '\u20A6' + total.toLocaleString();
    }

    function bindRow(row) {
      // Delete button
      const delBtn = row.querySelector('.li-delete');
      if (delBtn) {
        delBtn.addEventListener('click', () => {
          if (table.querySelectorAll('tbody tr').length > 1) {
            row.remove();
            serialize();
          }
        });
      }
      // Input change events
      row.querySelectorAll('input').forEach((inp) => {
        inp.addEventListener('input', serialize);
        inp.addEventListener('change', serialize);
      });
      // Paste support (tab-separated spreadsheet data)
      row.querySelectorAll('input').forEach((inp) => {
        inp.addEventListener('paste', handlePaste);
      });
      // Validation on blur
      const amtInput = row.querySelector('.li-amount');
      if (amtInput) {
        amtInput.addEventListener('blur', function () {
          const val = this.value.trim();
          if (val && isNaN(parseInt(val))) {
            this.classList.add('is-invalid');
          } else {
            this.classList.remove('is-invalid');
          }
        });
      }
      const qtyInput = row.querySelector('.li-qty');
      if (qtyInput) {
        qtyInput.addEventListener('blur', function () {
          const val = this.value.trim();
          if (val && isNaN(parseInt(val))) {
            this.classList.add('is-invalid');
          } else {
            this.classList.remove('is-invalid');
          }
        });
      }
    }

    function handlePaste(e) {
      const data = (e.clipboardData || window.clipboardData).getData('text');
      if (!data || !data.includes('\t')) return; // Only handle tab-separated
      e.preventDefault();
      const pastedRows = data.split('\n').filter((r) => r.trim());
      const startInput = e.target;
      const startRow = startInput.closest('tr');
      const startCol = Array.from(startRow.querySelectorAll('td')).indexOf(startInput.closest('td'));

      let currentRow = startRow;
      pastedRows.forEach((rowData, ri) => {
        const cells = rowData.split('\t');
        if (ri > 0) {
          const tr = document.createElement('tr');
          tr.innerHTML =
            '<td><input type="text" class="form-control form-control-sm li-item" placeholder="Item name"></td>' +
            '<td><input type="text" class="form-control form-control-sm li-desc" placeholder="Description"></td>' +
            '<td style="width:80px"><input type="text" class="form-control form-control-sm li-qty" placeholder="Qty" value="1"></td>' +
            '<td style="width:120px"><input type="text" class="form-control form-control-sm li-amount" placeholder="Amount" value="0"></td>' +
            '<td style="width:40px"><button type="button" class="btn btn-outline-danger btn-sm li-delete">\u00D7</button></td>';
          currentRow.after(tr);
          currentRow = tr;
          bindRow(tr);
        }
        const inputs = currentRow.querySelectorAll('input');
        cells.forEach((cell, ci) => {
          const idx = startCol + ci;
          if (idx < inputs.length) inputs[idx].value = cell.trim();
        });
      });
      serialize();
    }

    // Add Row button
    const addBtn = container.querySelector('.li-add-row');
    if (addBtn) {
      addBtn.addEventListener('click', () => {
        const tbody = table.querySelector('tbody');
        const tr = document.createElement('tr');
        tr.innerHTML =
          '<td><input type="text" class="form-control form-control-sm li-item" placeholder="Item name"></td>' +
          '<td><input type="text" class="form-control form-control-sm li-desc" placeholder="Description"></td>' +
          '<td style="width:80px"><input type="text" class="form-control form-control-sm li-qty" placeholder="Qty" value="1"></td>' +
          '<td style="width:120px"><input type="text" class="form-control form-control-sm li-amount" placeholder="Amount" value="0"></td>' +
          '<td style="width:40px"><button type="button" class="btn btn-outline-danger btn-sm li-delete">\u00D7</button></td>';
        tbody.appendChild(tr);
        bindRow(tr);
        serialize();
      });
    }

    // Initialize existing rows
    table.querySelectorAll('tbody tr').forEach(bindRow);
    serialize();
  });
}

/* ── CV Section modal row management ──────────────────────── */

function addCvItem(containerId, templateId) {
  const container = document.getElementById(containerId);
  const template = document.getElementById(templateId);
  if (!container || !template) return;
  const clone = template.content.cloneNode(true);
  container.appendChild(clone);
}

function removeCvItem(btn) {
  const row = btn.closest('[data-item-row]');
  if (row) row.remove();
}

/* ── HTMX config hook: serialise CV section items before POST ── */

document.addEventListener('htmx:configRequest', function (evt) {
  const elt = evt.detail.elt;
  const form = elt.matches('.cv-section-form') ? elt : elt.closest('.cv-section-form');
  if (!form) return;
  const container = form.querySelector('[data-items-container]');
  const dataField = form.querySelector('[name="data"]');
  if (!container || !dataField) return;
  const items = [];
  container.querySelectorAll('[data-item-row]').forEach(function (row) {
    const item = {};
    row.querySelectorAll('[data-field]').forEach(function (input) {
      item[input.dataset.field] = input.value;
    });
    items.push(item);
  });
  dataField.value = JSON.stringify(items);
});

/* ── Image upload preview ─────────────────────────────────── */

function initImagePreview() {
  document.addEventListener('change', function (e) {
    const input = e.target.closest('[data-preview-target]');
    if (!input || !input.files || !input.files[0]) return;
    const previewId = input.dataset.previewTarget;
    const img = document.getElementById(previewId);
    if (!img) return;
    const file = input.files[0];
    if (!file.type.startsWith('image/')) return;
    const reader = new FileReader();
    reader.onload = function (ev) {
      img.src = ev.target.result;
      img.classList.remove('d-none');
    };
    reader.readAsDataURL(file);
  });
}

/* ── HTMX OOB Toast auto-init ────────────────────────────── */

function initToasts() {
  document.addEventListener('htmx:afterSwap', function () {
    if (!window.bootstrap) return;
    document.querySelectorAll('.toast:not([data-fs-toast-ready])').forEach(function (el) {
      el.setAttribute('data-fs-toast-ready', 'true');
      try {
        var toast = new bootstrap.Toast(el);
        toast.show();
      } catch (_) { /* silently skip */ }
    });
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

  // AI Draft apply-to-field
  initApplyDraft();

  // Line Items Editor
  initLineItemsEditor();

  // Image upload preview
  initImagePreview();

  // HTMX OOB toast auto-init
  initToasts();
});
