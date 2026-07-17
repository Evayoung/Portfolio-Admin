/* ai_draft.js — AI Draft: apply-to-field + add-to-sections handlers */

function initApplyDraft() {
  document.addEventListener("click", function (e) {
    // Apply draft content to a specific form field
    const btn = e.target.closest("[data-apply-field]");
    if (btn) {
      const fieldId = btn.dataset.applyField;
      const sourceId = btn.dataset.draftSource;
      const source = document.getElementById(sourceId);
      const target = document.getElementById(fieldId);
      if (source && target) {
        target.value = source.value;
        target.dispatchEvent(new Event("input", { bubbles: true }));
        const orig = btn.textContent;
        btn.textContent = "Applied!";
        setTimeout(() => { btn.textContent = orig; }, 1200);
      }
      return;
    }

    // Append draft content to deal sections
    const addToSectionsBtn = e.target.closest("[data-add-to-sections]");
    if (addToSectionsBtn) {
      const sourceId = addToSectionsBtn.dataset.draftSource;
      const source = document.getElementById(sourceId);
      const draftKind = addToSectionsBtn.dataset.draftKind || "AI Section";
      if (source && source.value) {
        const sectionsInput =
          document.querySelector("[data-sections-input]") ||
          document.getElementById("sections_json");
        if (sectionsInput) {
          let sections = [];
          try {
            sections = JSON.parse(sectionsInput.value || "[]");
          } catch (_) { sections = []; }

          const titleMap = {
            proposal: "Proposal Plan",
            quote: "Quotation Details",
            invoice: "Invoice Wording",
            scope: "Project Scope",
            payment_terms: "Payment Terms",
          };
          const title = titleMap[draftKind] || "AI Draft Section";

          sections.push({ title: title, content: source.value });
          sectionsInput.value = JSON.stringify(sections);

          // Notify sections editor to re-render
          sectionsInput.dispatchEvent(new CustomEvent("sections:update"));

          const orig = addToSectionsBtn.textContent;
          addToSectionsBtn.textContent = "Added to Sections!";
          setTimeout(() => { addToSectionsBtn.textContent = orig; }, 1500);
        }
      }
    }
  });
}
