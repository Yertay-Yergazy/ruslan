// АвтоСервис Про — Main JS

document.addEventListener('DOMContentLoaded', () => {
    // Auto-close alerts after 5s
    document.querySelectorAll('.alert.alert-dismissible').forEach(alert => {
        setTimeout(() => {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            bsAlert && bsAlert.close();
        }, 5000);
    });

    // Smooth scroll for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(a => {
        a.addEventListener('click', e => {
            const target = document.querySelector(a.getAttribute('href'));
            if (target) {
                e.preventDefault();
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });

    // Active nav link highlight on scroll
    const sections = document.querySelectorAll('section[id]');
    if (sections.length) {
        const observer = new IntersectionObserver(entries => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    document.querySelectorAll('.nav-link[href="#' + entry.target.id + '"]').forEach(l => {
                        l.classList.add('active');
                    });
                }
            });
        }, { threshold: 0.5 });
        sections.forEach(s => observer.observe(s));
    }

    // Phone number formatter
    document.querySelectorAll('input[type="tel"]').forEach(input => {
        input.addEventListener('input', () => {
            let v = input.value.replace(/\D/g, '');
            if (v.startsWith('7') || v.startsWith('8')) v = v.slice(1);
            if (v.length > 10) v = v.slice(0, 10);
            if (v.length > 6) v = v.replace(/(\d{3})(\d{3})(\d{2})(\d{0,2})/, '+7 ($1) $2-$3-$4');
            else if (v.length > 3) v = v.replace(/(\d{3})(\d{0,3})/, '+7 ($1) $2');
            else if (v.length > 0) v = '+7 (' + v;
            input.value = v;
        });
    });

    // Tooltips
    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
        new bootstrap.Tooltip(el);
    });

    // Confirm delete
    document.querySelectorAll('[data-confirm]').forEach(el => {
        el.addEventListener('click', e => {
            if (!confirm(el.dataset.confirm)) e.preventDefault();
        });
    });
});

// Toggle password visibility
function togglePassword(id) {
    const f = document.getElementById(id);
    const eye = document.getElementById(id + '-eye');
    if (!f) return;
    if (f.type === 'password') {
        f.type = 'text';
        if (eye) eye.className = 'fas fa-eye-slash';
    } else {
        f.type = 'password';
        if (eye) eye.className = 'fas fa-eye';
    }
}
