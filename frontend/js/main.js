// ============================================
// SAS University - Shared JavaScript
// ============================================

// Dark/Light Mode
function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateThemeIcon(savedTheme);
}

function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('theme', next);
    updateThemeIcon(next);
}

function updateThemeIcon(theme) {
    const btn = document.querySelector('.theme-toggle');
    if (btn) btn.textContent = theme === 'dark' ? '☀️' : '🌙';
}

// Toast Notifications
function showToast(message, type = 'info') {
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const icons = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' };
    toast.innerHTML = `<span>${icons[type] || icons.info}</span><span>${message}</span>`;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.classList.add('removing');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Mobile Sidebar
function toggleSidebar() {
    document.querySelector('.sidebar').classList.toggle('open');
}

// Modal
function openModal(id) {
    document.getElementById(id).classList.add('active');
}

function closeModal(id) {
    document.getElementById(id).classList.remove('active');
}

// Password Toggle
function togglePassword(inputId, btn) {
    const input = document.getElementById(inputId);
    if (input.type === 'password') {
        input.type = 'text';
        btn.textContent = '🙈';
    } else {
        input.type = 'password';
        btn.textContent = '👁️';
    }
}

// Get current date formatted
function getCurrentDate() {
    const now = new Date();
    const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
    return {
        dayName: days[now.getDay()],
        day: now.getDate(),
        month: months[now.getMonth()],
        year: now.getFullYear(),
        full: now.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })
    };
}

// Update date display
function updateDateDisplay() {
    const dateEl = document.getElementById('current-date');
    if (dateEl) {
        const d = getCurrentDate();
        dateEl.innerHTML = `
            <div class="date-day">${d.dayName}</div>
            <div class="date-number">${d.day}</div>
            <div class="date-month">${d.month} ${d.year}</div>
        `;
    }
    const dateTextEl = document.getElementById('date-text');
    if (dateTextEl) {
        dateTextEl.textContent = getCurrentDate().full;
    }
}

// Search filter for tables
function filterTable(inputId, tableId) {
    const input = document.getElementById(inputId);
    const table = document.getElementById(tableId);
    if (!input || !table) return;
    
    input.addEventListener('input', function() {
        const term = this.value.toLowerCase();
        const rows = table.querySelectorAll('tbody tr');
        rows.forEach(row => {
            const text = row.textContent.toLowerCase();
            row.style.display = text.includes(term) ? '' : 'none';
        });
    });
}

// Logout
function logout() {
    localStorage.removeItem('userRole');
    localStorage.removeItem('userName');
    window.location.href = '../index.html';
}

// Get user info
function getUserInfo() {
    return {
        name: localStorage.getItem('userName') || 'User',
        role: localStorage.getItem('userRole') || 'student'
    };
}

// Initialize on load
document.addEventListener('DOMContentLoaded', function() {
    initTheme();
    updateDateDisplay();
    
    // Update user name in welcome
    const user = getUserInfo();
    const welcomeName = document.getElementById('welcome-name');
    if (welcomeName) welcomeName.textContent = user.name;
    
    const sidebarName = document.getElementById('sidebar-name');
    if (sidebarName) sidebarName.textContent = user.name;
    
    const sidebarRole = document.getElementById('sidebar-role');
    if (sidebarRole) sidebarRole.textContent = user.role.charAt(0).toUpperCase() + user.role.slice(1);
    
    const sidebarAvatar = document.getElementById('sidebar-avatar');
    if (sidebarAvatar) sidebarAvatar.textContent = user.name.charAt(0).toUpperCase();
    
    // Close modals on overlay click
    document.querySelectorAll('.modal-overlay').forEach(overlay => {
        overlay.addEventListener('click', function(e) {
            if (e.target === this) this.classList.remove('active');
        });
    });
});