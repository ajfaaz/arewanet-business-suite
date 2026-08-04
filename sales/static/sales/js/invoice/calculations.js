// calculations.js - Handles row & document calculation logic
function calculateRowTotal(row) {
    const qtyInput = row.querySelector('.qty, [name$="-qty"]');
    const priceInput = row.querySelector('.unit-price, [name$="-unit_price"]');
    const totalInput = row.querySelector('.line-total');

    const qty = parseFloat(qtyInput ? qtyInput.value : 0) || 0;
    const price = parseFloat(priceInput ? priceInput.value : 0) || 0;
    const lineTotal = qty * price;

    if (totalInput) {
        totalInput.value = '₦' + lineTotal.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }
    return lineTotal;
}
