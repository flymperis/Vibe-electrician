(function () {
    const body = document.getElementById("quote-lines-body");
    const addBtn = document.getElementById("add-line-btn");
    const totalFormsInput = document.querySelector('input[name$="-TOTAL_FORMS"]');
    const templateEl = document.getElementById("quote-line-empty-template");
    const grandTotalEl = document.getElementById("quote-grand-total");
    const linesSubtotalEl = document.getElementById("quote-lines-subtotal");
    const manualTotalInput = document.querySelector(".quote-manual-total");

    if (!body || !addBtn || !totalFormsInput || !templateEl) {
        return;
    }

    function formatMoney(value) {
        return value.toLocaleString("el-GR", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        }) + " €";
    }

    function parseNumber(input) {
        if (!input) {
            return 0;
        }
        const value = parseFloat(String(input.value || "").replace(",", "."));
        return Number.isFinite(value) ? value : 0;
    }

    function rowIsDeleted(row) {
        const deleteInput = row.querySelector('input[name$="-DELETE"]');
        return deleteInput && deleteInput.checked;
    }

    function hasLinePrice(row) {
        const priceInput = row.querySelector(".line-price");
        return priceInput && String(priceInput.value || "").trim() !== "";
    }

    function updateRowTotal(row) {
        const totalCell = row.querySelector(".line-total");
        if (!totalCell) {
            return;
        }
        if (rowIsDeleted(row)) {
            totalCell.textContent = "—";
            row.classList.add("line-deleted");
            return;
        }
        row.classList.remove("line-deleted");
        const desc = row.querySelector(".line-description");
        if (!desc || !desc.value.trim()) {
            totalCell.textContent = "—";
            return;
        }
        if (!hasLinePrice(row)) {
            totalCell.textContent = "—";
            return;
        }
        const qty = parseNumber(row.querySelector(".line-qty"));
        const price = parseNumber(row.querySelector(".line-price"));
        totalCell.textContent = formatMoney(qty * price);
    }

    function computeLinesSubtotal() {
        let sum = 0;
        body.querySelectorAll(".quote-line-row").forEach((row) => {
            if (rowIsDeleted(row)) {
                return;
            }
            const desc = row.querySelector(".line-description");
            if (!desc || !desc.value.trim() || !hasLinePrice(row)) {
                return;
            }
            const qty = parseNumber(row.querySelector(".line-qty"));
            const price = parseNumber(row.querySelector(".line-price"));
            sum += qty * price;
        });
        return sum;
    }

    function updateTotals() {
        const subtotal = computeLinesSubtotal();
        if (linesSubtotalEl) {
            linesSubtotalEl.textContent = formatMoney(subtotal);
        }
        if (!grandTotalEl) {
            return;
        }
        const manual = manualTotalInput ? parseNumber(manualTotalInput) : 0;
        const manualFilled = manualTotalInput && String(manualTotalInput.value || "").trim() !== "";
        const displayTotal = manualFilled ? manual : subtotal;
        grandTotalEl.textContent = formatMoney(displayTotal);
    }

    function bindRow(row) {
        row.querySelectorAll(".line-qty, .line-price, .line-description").forEach((input) => {
            input.addEventListener("input", () => {
                updateRowTotal(row);
                updateTotals();
            });
        });
        const deleteInput = row.querySelector('input[name$="-DELETE"]');
        if (deleteInput) {
            deleteInput.addEventListener("change", () => {
                updateRowTotal(row);
                updateTotals();
            });
        }
        updateRowTotal(row);
    }

    function addLine() {
        const index = parseInt(totalFormsInput.value, 10);
        const row = templateEl.content.firstElementChild.cloneNode(true);
        row.innerHTML = row.innerHTML.replace(/__prefix__/g, String(index));
        body.appendChild(row);
        totalFormsInput.value = String(index + 1);
        bindRow(row);
        updateTotals();
    }

    if (manualTotalInput) {
        manualTotalInput.addEventListener("input", updateTotals);
    }

    addBtn.addEventListener("click", addLine);
    body.querySelectorAll(".quote-line-row").forEach(bindRow);
    updateTotals();
})();
