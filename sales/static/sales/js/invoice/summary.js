// summary.js - Real-time invoice summary widget updater
function updateInvoiceSummary() {
    let subtotal = 0;
    document.querySelectorAll('.invoice-row').forEach(row => {
        if (row.style.display !== 'none' && !row.classList.contains('d-none')) {
            if (typeof calculateRowTotal === 'function') {
                subtotal += calculateRowTotal(row);
            }
        }
    });

    const subtotalEl = document.getElementById('subtotal');
    if (subtotalEl) {
        subtotalEl.innerText = '₦' + subtotal.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    const grandTotalEl = document.getElementById('grand-total');
    if (grandTotalEl) {
        grandTotalEl.innerText = '₦' + subtotal.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }
}

document.addEventListener('input', updateInvoiceSummary);
document.addEventListener('DOMContentLoaded', updateInvoiceSummary);
