// ABS Dropdown Helper
document.addEventListener('click', function (e) {
    if (e.target.matches('.abs-dropdown-toggle')) {
        const menu = e.target.nextElementSibling;
        if (menu) menu.classList.toggle('show');
    }
});
