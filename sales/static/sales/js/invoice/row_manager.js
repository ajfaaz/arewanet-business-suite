// row_manager.js - Dynamic row addition & deletion management
document.addEventListener('DOMContentLoaded', function () {
    const addRowBtn = document.getElementById('add-row');
    if (addRowBtn) {
        addRowBtn.addEventListener('click', function () {
            const tbody = document.getElementById('invoice-items-body');
            const template = document.getElementById('empty-form-template');
            const totalFormsInput = document.getElementById('id_items-TOTAL_FORMS');

            if (tbody && template && totalFormsInput) {
                const count = parseInt(totalFormsInput.value, 10);
                const newRowHtml = template.innerHTML.replace(/__prefix__/g, count);
                tbody.insertAdjacentHTML('beforeend', newRowHtml);
                totalFormsInput.value = count + 1;
            }
        });
    }

    document.addEventListener('click', function (e) {
        if (e.target && e.target.classList.contains('remove-row')) {
            const row = e.target.closest('tr');
            if (row) {
                row.remove();
            }
        }
    });
});
