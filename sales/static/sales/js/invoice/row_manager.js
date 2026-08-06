// row_manager.js - Dynamic row addition & deletion management
document.addEventListener('DOMContentLoaded', function () {
    if (window.InvoiceRowManagerInitialized) {
        return;
    }
    window.InvoiceRowManagerInitialized = true;

    document.addEventListener('click', function (e) {
        const addBtn = e.target.closest('#add-row');
        if (addBtn) {
            e.preventDefault();
            const tbody = document.getElementById('invoice-items-body');
            const template = document.getElementById('empty-form-template');
            const totalFormsInput = document.getElementById('id_items-TOTAL_FORMS');

            if (tbody && template && totalFormsInput) {
                const count = parseInt(totalFormsInput.value, 10);
                const newRowHtml = template.innerHTML.replace(/__prefix__/g, count);
                tbody.insertAdjacentHTML('beforeend', newRowHtml);
                totalFormsInput.value = count + 1;
            }
            return;
        }

        const removeBtn = e.target.closest('.remove-row');
        if (removeBtn) {
            e.preventDefault();
            const row = removeBtn.closest('tr');
            if (!row) return;

            const deleteCheckbox = row.querySelector('input[type="checkbox"][name$="-DELETE"]');
            const idInput = row.querySelector('input[type="hidden"][name$="-id"]');

            if (idInput && idInput.value) {
                if (deleteCheckbox) {
                    deleteCheckbox.checked = true;
                } else {
                    const nameAttr = idInput.name.replace(/-id$/, '-DELETE');
                    const hiddenDelete = document.createElement('input');
                    hiddenDelete.type = 'hidden';
                    hiddenDelete.name = nameAttr;
                    hiddenDelete.value = 'on';
                    row.appendChild(hiddenDelete);
                }
                row.style.display = 'none';
                row.classList.add('d-none');
            } else {
                row.remove();
            }
        }
    });
});
