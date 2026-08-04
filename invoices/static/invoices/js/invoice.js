function calculateRow(row) {
    const qtyInput = row.querySelector(".qty, .line-qty");
    const priceInput = row.querySelector(".unit-price, .line-price");
    const totalInput = row.querySelector(".line-total");

    const qty = parseFloat(qtyInput ? qtyInput.value : 0) || 0;
    const price = parseFloat(priceInput ? priceInput.value : 0) || 0;
    const lineTotal = qty * price;

    if (totalInput) {
        totalInput.value = "₦" + lineTotal.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }
    return lineTotal;
}

function calculateInvoiceTotal() {
    let subtotal = 0;
    document.querySelectorAll(".invoice-row").forEach(function (row) {
        subtotal += calculateRow(row);
    });

    const subtotalEl = document.getElementById("subtotal");
    if (subtotalEl) {
        subtotalEl.innerText = "₦" + subtotal.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    const vatInput = document.getElementById("id_vat");
    const vatRate = parseFloat(vatInput ? vatInput.value : 0) || 0;
    const vatAmount = (subtotal * vatRate) / 100;

    const vatLabel = document.getElementById("vat-label");
    if (vatLabel) {
        vatLabel.innerText = `VAT (${vatRate}%)`;
    }
    const vatDisplay = document.getElementById("vat-display");
    if (vatDisplay) {
        vatDisplay.innerText = "₦" + vatAmount.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    const grandTotal = subtotal + vatAmount;
    const grandTotalEl = document.getElementById("grand-total");
    if (grandTotalEl) {
        grandTotalEl.innerText = "₦" + grandTotal.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }
    const previewTotalEl = document.getElementById("preview-total");
    if (previewTotalEl) {
        previewTotalEl.innerText = "₦" + grandTotal.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }
}

document.addEventListener("change", async function (e) {
    if (e.target.classList.contains("product-select")) {
        const select = e.target;
        if (!select.value) return;

        const row = select.closest("tr");
        try {
            const response = await fetch(`/products/${select.value}/info/`);
            if (response.ok) {
                const product = await response.json();
                const descInput = row.querySelector(".description");
                if (descInput) {
                    descInput.value = product.description || product.name;
                }
                const priceInput = row.querySelector(".unit-price, .line-price");
                if (priceInput) {
                    priceInput.value = product.price;
                }
                calculateRow(row);
                calculateInvoiceTotal();
            }
        } catch (err) {
            console.error("Error fetching product info:", err);
        }
    }
});

document.addEventListener("input", function (e) {
    if (e.target.classList.contains("qty") || e.target.classList.contains("line-qty") ||
        e.target.classList.contains("unit-price") || e.target.classList.contains("line-price") ||
        e.target.id === "id_vat") {
        const row = e.target.closest("tr");
        if (row) calculateRow(row);
        calculateInvoiceTotal();
    }
});

document.addEventListener("DOMContentLoaded", function () {
    calculateInvoiceTotal();

    const addRowBtn = document.getElementById("add-row");
    if (addRowBtn) {
        addRowBtn.addEventListener("click", function () {
            const tbody = document.getElementById("invoice-items-body");
            const template = document.getElementById("empty-form-template");
            const totalFormsInput = document.getElementById("id_items-TOTAL_FORMS");

            if (tbody && template && totalFormsInput) {
                const count = parseInt(totalFormsInput.value, 10);
                const newRowHtml = template.innerHTML.replace(/__prefix__/g, count);
                tbody.insertAdjacentHTML("beforeend", newRowHtml);
                totalFormsInput.value = count + 1;
                calculateInvoiceTotal();
            }
        });
    }

    document.addEventListener("click", function (e) {
        if (e.target.classList.contains("remove-row")) {
            const row = e.target.closest("tr");
            const tbody = document.getElementById("invoice-items-body");
            if (tbody && tbody.querySelectorAll("tr").length > 1) {
                row.remove();
                calculateInvoiceTotal();
            }
        }
    });

    const customerSelect = document.getElementById("id_customer");
    const previewCustomer = document.getElementById("preview-customer");
    if (customerSelect && previewCustomer) {
        customerSelect.addEventListener("change", function () {
            const selectedText = customerSelect.options[customerSelect.selectedIndex]?.text || "-";
            previewCustomer.textContent = selectedText;
        });
    }

    const projectInput = document.getElementById("id_project_name");
    const previewProject = document.getElementById("preview-project");
    if (projectInput && previewProject) {
        projectInput.addEventListener("input", function () {
            previewProject.textContent = projectInput.value || "-";
        });
    }
});
