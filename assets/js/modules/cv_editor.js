/* cv_editor.js — CV section modal row management + HTMX config hook */

function addCvItem(containerId, templateId) {
  const container = document.getElementById(containerId);
  const template = document.getElementById(templateId);
  if (!container || !template) return;
  const clone = template.content.cloneNode(true);
  container.appendChild(clone);
}

function removeCvItem(btn) {
  const row = btn.closest("[data-item-row]");
  if (row) row.remove();
}

/* ── HTMX config hook: serialize CV + deal sections before POST ── */

document.addEventListener("htmx:configRequest", function (evt) {
  const elt = evt.detail.elt;

  // CV sections — serialize items from data-items-container
  const cvForm = elt.matches(".cv-section-form") ? elt : elt.closest(".cv-section-form");
  if (cvForm) {
    const container =
      cvForm.querySelector("[data-items-container]") ||
      cvForm.querySelector("[data-cv-items]");
    const dataField = cvForm.querySelector('[name="data"]');
    if (container && dataField) {
      const items = [];
      container.querySelectorAll("[data-item-row]").forEach(function (row) {
        const item = {};
        row.querySelectorAll("[data-field]").forEach(function (input) {
          item[input.dataset.field] = input.value;
        });
        items.push(item);
      });
      dataField.value = JSON.stringify(items);
    }
  }
});
