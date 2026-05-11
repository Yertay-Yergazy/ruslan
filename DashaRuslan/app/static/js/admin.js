// АвтоСервис Про — Admin Panel JS

document.addEventListener('DOMContentLoaded', () => {
    const sidebar = document.getElementById('sidebar');
    const mainWrapper = document.getElementById('mainWrapper');
    const toggle = document.getElementById('sidebarToggle');

    // Sidebar toggle
    if (toggle) {
        toggle.addEventListener('click', () => {
            if (window.innerWidth <= 991) {
                sidebar.classList.toggle('mobile-open');
            } else {
                sidebar.classList.toggle('collapsed');
                mainWrapper.classList.toggle('collapsed');
            }
        });
    }

    // Auto-close alerts
    document.querySelectorAll('.alert.alert-dismissible').forEach(alert => {
        setTimeout(() => {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            bsAlert && bsAlert.close();
        }, 4000);
    });

    // Confirm delete buttons
    document.querySelectorAll('[data-confirm]').forEach(el => {
        el.addEventListener('click', e => {
            if (!confirm(el.dataset.confirm)) e.preventDefault();
        });
    });

    // Schedule toggles - grey out time inputs when not working
    document.querySelectorAll('.schedule-toggle').forEach(toggle => {
        const day = toggle.dataset.day;
        const timeRow = document.getElementById(day + '_times');

        function updateTimeRow() {
            if (timeRow) {
                timeRow.style.opacity = toggle.checked ? '1' : '0.4';
                timeRow.querySelectorAll('input').forEach(i => i.disabled = !toggle.checked);
            }
        }

        updateTimeRow();
        toggle.addEventListener('change', updateTimeRow);
    });

    // Tooltips
    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
        new bootstrap.Tooltip(el);
    });

    // DataTable-like: click row → navigate
    document.querySelectorAll('tr[data-href]').forEach(row => {
        row.style.cursor = 'pointer';
        row.addEventListener('click', () => { window.location = row.dataset.href; });
    });
});
