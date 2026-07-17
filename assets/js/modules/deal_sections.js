/* deal_sections.js — Section editor with modal CRUD, reorder, and auto-save */

let _autoSaveDealTimer = null;

function _autoSaveDeal() {
  // Debounce: batch rapid changes (reorder, edit) into a single save
  if (_autoSaveDealTimer) clearTimeout(_autoSaveDealTimer);
  _autoSaveDealTimer = setTimeout(function () {
    const dealForm =
      document.querySelector('[data-deal-form]') ||
      document.querySelector('.admin-settings-form[hx-post="/deals/save"]') ||
      document.querySelector('.admin-settings-form[hx\\:post="/deals/save"]') ||
      document.querySelector(".admin-settings-form");
    if (dealForm && window.htmx) {
      htmx.trigger(dealForm, "submit");
    }
  }, 500);
}

function initDealSections() {
  const container =
    document.querySelector("[data-deal-sections]") ||
    document.getElementById("deal-sections-container");
  const hiddenInput =
    document.querySelector("[data-sections-input]") ||
    document.getElementById("sections_json");
  const addBtn =
    document.querySelector("[data-deal-section-add]") ||
    document.getElementById("deal-section-add-btn");
  const modal =
    document.querySelector("[data-deal-section-modal]") ||
    document.getElementById("deal-section-modal");
  const saveBtn =
    document.querySelector("[data-deal-section-save]") ||
    document.getElementById("deal-section-save-btn");
  const titleInput =
    document.querySelector("[data-deal-section-title]") ||
    document.getElementById("deal-section-title-input");
  const contentInput =
    document.querySelector("[data-deal-section-content]") ||
    document.getElementById("deal-section-content-input");
  const modalTitle =
    document.querySelector("[data-deal-section-modal-title]") ||
    document.getElementById("deal-section-modal-title");

  if (!container || !hiddenInput) return;

  let sections = [];
  let editingIndex = -1;

  try {
    const parsed = JSON.parse(hiddenInput.value || "[]");
    sections = Array.isArray(parsed) ? parsed : [];
  } catch (_) { sections = []; }

  function serialize() {
    hiddenInput.value = JSON.stringify(sections);
    render();
  }

  function escapeHtml(str) {
    const d = document.createElement("div");
    d.textContent = str;
    return d.innerHTML;
  }

  function stripMd(str) {
    return str.replace(/[#*`\[\]>_~|]/g, "").replace(/\s+/g, " ").trim();
  }

  function render() {
    if (sections.length === 0) {
      container.innerHTML = '<p class="admin-save-note" style="margin-bottom:0;">No sections yet. Click "Add Section" to build the document content.</p>';
      return;
    }
    let html = "";
    for (let i = 0; i < sections.length; i++) {
      const s = sections[i];
      let preview = stripMd(s.content || "").substring(0, 120);
      if (s.content && s.content.length > 120) preview += "...";
      html +=
        '<div class="deal-section-item" data-index="' + i + '">' +
          '<div class="deal-section-header">' +
            '<span class="deal-section-title">' + escapeHtml(s.title || "Untitled") + "</span>" +
            '<div class="deal-section-actions">' +
              '<button type="button" class="btn btn-sm btn-outline-secondary section-move-up" title="Move up"' + (i === 0 ? " disabled" : "") + ">&uarr;</button>" +
              '<button type="button" class="btn btn-sm btn-outline-secondary section-move-down" title="Move down"' + (i === sections.length - 1 ? " disabled" : "") + ">&darr;</button>" +
              '<button type="button" class="btn btn-sm btn-outline-primary section-edit" title="Edit">&#9998;</button>' +
              '<button type="button" class="btn btn-sm btn-outline-danger section-delete" title="Delete">&times;</button>' +
            "</div>" +
          "</div>" +
          '<div class="deal-section-preview">' + escapeHtml(preview) + "</div>" +
        "</div>";
    }
    container.innerHTML = html;
    bindSectionEvents();
  }

  function bindSectionEvents() {
    container.querySelectorAll(".section-move-up").forEach(function (btn) {
      btn.addEventListener("click", function () {
        const idx = parseInt(this.closest(".deal-section-item").dataset.index);
        if (idx > 0) {
          const tmp = sections[idx - 1];
          sections[idx - 1] = sections[idx];
          sections[idx] = tmp;
          serialize();
          _autoSaveDeal();
        }
      });
    });
    container.querySelectorAll(".section-move-down").forEach(function (btn) {
      btn.addEventListener("click", function () {
        const idx = parseInt(this.closest(".deal-section-item").dataset.index);
        if (idx < sections.length - 1) {
          const tmp = sections[idx + 1];
          sections[idx + 1] = sections[idx];
          sections[idx] = tmp;
          serialize();
          _autoSaveDeal();
        }
      });
    });
    container.querySelectorAll(".section-edit").forEach(function (btn) {
      btn.addEventListener("click", function () {
        const idx = parseInt(this.closest(".deal-section-item").dataset.index);
        openModal(idx);
      });
    });
    container.querySelectorAll(".section-delete").forEach(function (btn) {
      btn.addEventListener("click", function () {
        const idx = parseInt(this.closest(".deal-section-item").dataset.index);
        showConfirm(
          'Delete section "' + (sections[idx].title || "Untitled") + '"?',
          function () {
            sections.splice(idx, 1);
            serialize();
            _autoSaveDeal();
          },
          null,
          { title: "Delete Section", confirmText: "Delete", variant: "danger" }
        );
      });
    });
  }

  function openModal(idx) {
    editingIndex = idx;
    if (idx >= 0 && idx < sections.length) {
      modalTitle.textContent = "Edit Section";
      titleInput.value = sections[idx].title || "";
      contentInput.value = sections[idx].content || "";
    } else {
      modalTitle.textContent = "Add Section";
      titleInput.value = "";
      contentInput.value = "";
    }
    if (window.bootstrap) {
      const bsModal = window.bootstrap.Modal.getOrCreateInstance(modal);
      bsModal.show();
    }
  }

  if (addBtn) {
    addBtn.addEventListener("click", function () { openModal(-1); });
  }
  if (saveBtn) {
    saveBtn.addEventListener("click", function () {
      const title = titleInput.value.trim();
      const content = contentInput.value.trim();
      if (!title) { titleInput.focus(); return; }
      if (editingIndex >= 0 && editingIndex < sections.length) {
        sections[editingIndex].title = title;
        sections[editingIndex].content = content;
      } else {
        sections.push({ title: title, content: content });
      }
      serialize();

      // Disable save button and show spinner
      saveBtn.disabled = true;
      const originalHtml = saveBtn.innerHTML;
      saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Saving...';

      const dealForm =
        hiddenInput.closest(".admin-settings-form") ||
        document.querySelector('[data-deal-form]');
      if (dealForm && window.htmx) {
        const onHtmxRequest = function (evt) {
          if (evt.detail.pathInfo.requestPath.indexOf("/deals/save") !== -1) {
            dealForm.removeEventListener("htmx:afterRequest", onHtmxRequest);
            if (evt.detail.successful) {
              saveBtn.innerHTML = "\u2713 Saved!";
              saveBtn.classList.remove("btn-primary", "admin-install-btn");
              saveBtn.classList.add("btn-success");

              setTimeout(function () {
                if (window.bootstrap) {
                  const bsModal = bootstrap.Modal.getInstance(modal);
                  if (bsModal) bsModal.hide();
                }
                saveBtn.disabled = false;
                saveBtn.innerHTML = originalHtml;
                saveBtn.classList.remove("btn-success");
                saveBtn.classList.add("btn-primary", "admin-install-btn");
              }, 600);
            } else {
              saveBtn.disabled = false;
              saveBtn.innerHTML = originalHtml;
              // Show error toast instead of native alert
              var toastContainer = document.getElementById("toast-container");
              if (toastContainer) {
                var toastEl = document.createElement("div");
                toastEl.className = "toast align-items-center text-bg-danger border-0";
                toastEl.setAttribute("role", "alert");
                toastEl.innerHTML =
                  '<div class="d-flex"><div class="toast-body">Failed to save section changes. Please try again.</div>' +
                  '<button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button></div>';
                toastContainer.appendChild(toastEl);
                var bsToast = new bootstrap.Toast(toastEl, { delay: 5000 });
                bsToast.show();
                toastEl.addEventListener("hidden.bs.toast", function () { toastEl.remove(); });
              } else {
                console.error("Failed to save section changes to the database.");
              }
            }
          }
        };
        dealForm.addEventListener("htmx:afterRequest", onHtmxRequest);
        htmx.trigger(dealForm, "submit");
      } else {
        if (window.bootstrap) {
          window.bootstrap.Modal.getInstance(modal).hide();
        }
        saveBtn.disabled = false;
      }
    });
  }

  hiddenInput.addEventListener("sections:update", function () {
    try {
      const parsed = JSON.parse(hiddenInput.value || "[]");
      sections = Array.isArray(parsed) ? parsed : [];
    } catch (_) { sections = []; }
    render();
  });

  render();
}
