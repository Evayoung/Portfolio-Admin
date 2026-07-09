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
    if (btn) {
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
      return;
    }

    const addToSectionsBtn = e.target.closest("[data-add-to-sections]");
    if (addToSectionsBtn) {
      const sourceId = addToSectionsBtn.dataset.draftSource;
      const source = document.getElementById(sourceId);
      const draftKind = addToSectionsBtn.dataset.draftKind || 'AI Section';
      if (source && source.value) {
        const sectionsInput = document.getElementById('sections_json');
        if (sectionsInput) {
          let sections = [];
          try {
            sections = JSON.parse(sectionsInput.value || '[]');
          } catch (_) { sections = []; }
          
          const titleMap = {
            "proposal": "Proposal Plan",
            "quote": "Quotation Details",
            "invoice": "Invoice Wording",
            "scope": "Project Scope",
            "payment_terms": "Payment Terms"
          };
          const title = titleMap[draftKind] || "AI Draft Section";
          
          sections.push({ title: title, content: source.value });
          sectionsInput.value = JSON.stringify(sections);
          
          // Dispatch custom event to notify initDealSections to reload and render
          sectionsInput.dispatchEvent(new CustomEvent('sections:update'));
          
          // Visual feedback
          const orig = addToSectionsBtn.textContent;
          addToSectionsBtn.textContent = "Added to Sections!";
          setTimeout(() => { addToSectionsBtn.textContent = orig; }, 1500);
        }
      }
    }
  });
}

/* ── Line Items Editor — dynamic table with totals, paste, validation ── */

function initLineItemsEditor() {
  document.querySelectorAll('.line-items-editor').forEach((container) => {
    const table = container.querySelector('.line-items-table');
    const hiddenInput = container.querySelector('[data-li-hidden]');
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

/* ── Deal auto-save helper (used by sections editor) ──────── */

function _autoSaveDeal() {
  var dealForm = document.querySelector('.admin-settings-form[hx-post="/deals/save"], .admin-settings-form[hx\\:post="/deals/save"]');
  if (!dealForm) {
    // Try finding by action attribute
    dealForm = document.querySelector('.admin-settings-form');
  }
  if (dealForm && window.htmx) {
    htmx.trigger(dealForm, 'submit');
  }
}

/* ── Deal Sections Editor ──────────────────────── */

function initDealSections() {
  const container = document.getElementById('deal-sections-container');
  const hiddenInput = document.getElementById('sections_json');
  const addBtn = document.getElementById('deal-section-add-btn');
  const modal = document.getElementById('deal-section-modal');
  const saveBtn = document.getElementById('deal-section-save-btn');
  const titleInput = document.getElementById('deal-section-title-input');
  const contentInput = document.getElementById('deal-section-content-input');
  const modalTitle = document.getElementById('deal-section-modal-title');
  if (!container || !hiddenInput) return;

  let sections = [];
  let editingIndex = -1;

  try {
    const parsed = JSON.parse(hiddenInput.value || '[]');
    sections = Array.isArray(parsed) ? parsed : [];
  } catch (_) { sections = []; }

  function serialize() {
    hiddenInput.value = JSON.stringify(sections);
    render();
  }

  function escapeHtml(str) {
    const d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
  }

  function stripMd(str) {
    return str.replace(/[#*`\[\]>_~|]/g, '').replace(/\s+/g, ' ').trim();
  }

  function render() {
    if (sections.length === 0) {
      container.innerHTML = '<p class="admin-save-note" style="margin-bottom:0;">No sections yet. Click "Add Section" to build the document content.</p>';
      return;
    }
    var html = '';
    for (var i = 0; i < sections.length; i++) {
      var s = sections[i];
      var preview = stripMd(s.content || '').substring(0, 120);
      if (s.content && s.content.length > 120) preview += '...';
      html +=
        '<div class="deal-section-item" data-index="' + i + '">' +
          '<div class="deal-section-header">' +
            '<span class="deal-section-title">' + escapeHtml(s.title || 'Untitled') + '</span>' +
            '<div class="deal-section-actions">' +
              '<button type="button" class="btn btn-sm btn-outline-secondary section-move-up" title="Move up"' + (i === 0 ? ' disabled' : '') + '>&uarr;</button>' +
              '<button type="button" class="btn btn-sm btn-outline-secondary section-move-down" title="Move down"' + (i === sections.length - 1 ? ' disabled' : '') + '>&darr;</button>' +
              '<button type="button" class="btn btn-sm btn-outline-primary section-edit" title="Edit">&#9998;</button>' +
              '<button type="button" class="btn btn-sm btn-outline-danger section-delete" title="Delete">&times;</button>' +
            '</div>' +
          '</div>' +
          '<div class="deal-section-preview">' + escapeHtml(preview) + '</div>' +
        '</div>';
    }
    container.innerHTML = html;

    // Bind events
    container.querySelectorAll('.section-move-up').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var idx = parseInt(this.closest('.deal-section-item').dataset.index);
        if (idx > 0) {
          var tmp = sections[idx - 1];
          sections[idx - 1] = sections[idx];
          sections[idx] = tmp;
          serialize();
          _autoSaveDeal();
        }
      });
    });
    container.querySelectorAll('.section-move-down').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var idx = parseInt(this.closest('.deal-section-item').dataset.index);
        if (idx < sections.length - 1) {
          var tmp = sections[idx + 1];
          sections[idx + 1] = sections[idx];
          sections[idx] = tmp;
          serialize();
          _autoSaveDeal();
        }
      });
    });
    container.querySelectorAll('.section-edit').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var idx = parseInt(this.closest('.deal-section-item').dataset.index);
        openModal(idx);
      });
    });
    container.querySelectorAll('.section-delete').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var idx = parseInt(this.closest('.deal-section-item').dataset.index);
        if (confirm('Delete section "' + (sections[idx].title || 'Untitled') + '"?')) {
          sections.splice(idx, 1);
          serialize();
          _autoSaveDeal();
        }
      });
    });
  }

  function openModal(idx) {
    editingIndex = idx;
    if (idx >= 0 && idx < sections.length) {
      modalTitle.textContent = 'Edit Section';
      titleInput.value = sections[idx].title || '';
      contentInput.value = sections[idx].content || '';
    } else {
      modalTitle.textContent = 'Add Section';
      titleInput.value = '';
      contentInput.value = '';
    }
    if (window.bootstrap) {
      var bsModal = window.bootstrap.Modal.getOrCreateInstance(modal);
      bsModal.show();
    }
  }

  if (addBtn) {
    addBtn.addEventListener('click', function () { openModal(-1); });
  }
  if (saveBtn) {
    saveBtn.addEventListener('click', function () {
      var title = titleInput.value.trim();
      var content = contentInput.value.trim();
      if (!title) { titleInput.focus(); return; }
      if (editingIndex >= 0 && editingIndex < sections.length) {
        sections[editingIndex].title = title;
        sections[editingIndex].content = content;
      } else {
        sections.push({ title: title, content: content });
      }
      serialize();
      if (window.bootstrap) {
        window.bootstrap.Modal.getInstance(modal).hide();
      }
      // Auto-save the deal form so section edits are persisted immediately
      var dealForm = hiddenInput.closest('.admin-settings-form');
      if (dealForm && window.htmx) {
        // Small delay to let the modal finish closing
        setTimeout(function () {
          htmx.trigger(dealForm, 'submit');
        }, 200);
      }
    });
  }

  hiddenInput.addEventListener('sections:update', function () {
    try {
      const parsed = JSON.parse(hiddenInput.value || '[]');
      sections = Array.isArray(parsed) ? parsed : [];
    } catch (_) { sections = []; }
    render();
  });

  render();
}

/* ── HTMX config hook: serialise deal sections before POST ── */

document.addEventListener('htmx:configRequest', function (evt) {
  const elt = evt.detail.elt;
  // CV sections
  const cvForm = elt.matches('.cv-section-form') ? elt : elt.closest('.cv-section-form');
  if (cvForm) {
    const container = cvForm.querySelector('[data-items-container]');
    const dataField = cvForm.querySelector('[name="data"]');
    if (container && dataField) {
      const items = [];
      container.querySelectorAll('[data-item-row]').forEach(function (row) {
        const item = {};
        row.querySelectorAll('[data-field]').forEach(function (input) {
          item[input.dataset.field] = input.value;
        });
        items.push(item);
      });
      dataField.value = JSON.stringify(items);
    }
  }
  // Deal sections
  const dealForm = elt.matches('.admin-settings-form') ? elt : elt.closest('.admin-settings-form');
  if (dealForm) {
    const hiddenInput = document.getElementById('sections_json');
    if (hiddenInput) {
      // sections_json is already maintained by initDealSections()
    }
  }
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

  // Deal Sections Editor
  initDealSections();

  // Image upload preview
  initImagePreview();

  // HTMX OOB toast auto-init
  initToasts();
});
