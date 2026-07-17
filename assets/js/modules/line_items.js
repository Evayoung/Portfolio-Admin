/* line_items.js — Dynamic table editor with totals, paste from spreadsheet, validation */

function initLineItemsEditor() {
  document.querySelectorAll(".line-items-editor").forEach((container) => {
    const table = container.querySelector(".line-items-table");
    const hiddenInput = container.querySelector("[data-li-hidden]");
    if (!table || !hiddenInput) return;

    function serialize() {
      const rows = [];
      table.querySelectorAll("tbody tr").forEach((row) => {
        const item = (row.querySelector(".li-item")?.value || "").trim();
        const desc = (row.querySelector(".li-desc")?.value || "").trim();
        const qty = (row.querySelector(".li-qty")?.value || "1").trim();
        const amount = (row.querySelector(".li-amount")?.value || "0").trim();
        if (item) rows.push(item + " | " + desc + " | " + qty + " | " + amount);
      });
      hiddenInput.value = rows.join("\n");
      updateTotal();
    }

    function updateTotal() {
      let total = 0;
      table.querySelectorAll("tbody tr").forEach((row) => {
        const qty = parseInt(row.querySelector(".li-qty")?.value) || 0;
        const amount = parseInt(row.querySelector(".li-amount")?.value) || 0;
        total += qty * amount;
      });
      const totalCell = container.querySelector(".li-total-value");
      if (totalCell) totalCell.textContent = "\u20A6" + total.toLocaleString();
    }

    function createRowHtml() {
      return (
        '<td><input type="text" class="form-control form-control-sm li-item" placeholder="Item name"></td>' +
        '<td><input type="text" class="form-control form-control-sm li-desc" placeholder="Description"></td>' +
        '<td style="width:80px"><input type="text" class="form-control form-control-sm li-qty" placeholder="Qty" value="1"></td>' +
        '<td style="width:120px"><input type="text" class="form-control form-control-sm li-amount" placeholder="Amount" value="0"></td>' +
        '<td style="width:40px"><button type="button" class="btn btn-outline-danger btn-sm li-delete">\u00D7</button></td>'
      );
    }

    function bindRow(row) {
      const delBtn = row.querySelector(".li-delete");
      if (delBtn) {
        delBtn.addEventListener("click", () => {
          if (table.querySelectorAll("tbody tr").length > 1) {
            row.remove();
            serialize();
          }
        });
      }
      row.querySelectorAll("input").forEach((inp) => {
        inp.addEventListener("input", serialize);
        inp.addEventListener("change", serialize);
        inp.addEventListener("paste", handlePaste);
      });
      // Validation on blur for numeric fields
      [".li-amount", ".li-qty"].forEach((sel) => {
        const numInput = row.querySelector(sel);
        if (numInput) {
          numInput.addEventListener("blur", function () {
            const val = this.value.trim();
            if (val && isNaN(parseInt(val))) {
              this.classList.add("is-invalid");
            } else {
              this.classList.remove("is-invalid");
            }
          });
        }
      });
    }

    function handlePaste(e) {
      const data = (e.clipboardData || window.clipboardData).getData("text");
      if (!data || !data.includes("\t")) return;
      e.preventDefault();
      const pastedRows = data.split("\n").filter((r) => r.trim());
      const startInput = e.target;
      const startRow = startInput.closest("tr");
      const startCol = Array.from(startRow.querySelectorAll("td")).indexOf(startInput.closest("td"));

      let currentRow = startRow;
      pastedRows.forEach((rowData, ri) => {
        const cells = rowData.split("\t");
        if (ri > 0) {
          const tr = document.createElement("tr");
          tr.innerHTML = createRowHtml();
          currentRow.after(tr);
          currentRow = tr;
          bindRow(tr);
        }
        const inputs = currentRow.querySelectorAll("input");
        cells.forEach((cell, ci) => {
          const idx = startCol + ci;
          if (idx < inputs.length) inputs[idx].value = cell.trim();
        });
      });
      serialize();
    }

    // Add Row button
    const addBtn = container.querySelector(".li-add-row");
    if (addBtn) {
      addBtn.addEventListener("click", () => {
        const tbody = table.querySelector("tbody");
        const tr = document.createElement("tr");
        tr.innerHTML = createRowHtml();
        tbody.appendChild(tr);
        bindRow(tr);
        serialize();
      });
    }

    // Initialize existing rows
    table.querySelectorAll("tbody tr").forEach(bindRow);
    serialize();
  });
}
