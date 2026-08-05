// ABS Toast Notification Helper
function showAbsToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `abs-toast abs-toast-${type}`;
    toast.innerText = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}
