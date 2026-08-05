// ABS Sidebar Toggle Logic (Desktop & Mobile)
document.addEventListener('DOMContentLoaded', function () {
    const toggleBtns = document.querySelectorAll('.abs-sidebar-toggle, .sidebar-toggle');
    const sidebar = document.querySelector('.abs-sidebar, .sidebar');

    toggleBtns.forEach(btn => {
        btn.addEventListener('click', function (e) {
            e.stopPropagation();
            if (sidebar) {
                sidebar.classList.toggle('show');
                sidebar.classList.toggle('active');
            }
        });
    });

    document.addEventListener('click', function (e) {
        if (sidebar && sidebar.classList.contains('show') && !sidebar.contains(e.target)) {
            sidebar.classList.remove('show');
            sidebar.classList.remove('active');
        }
    });
});
