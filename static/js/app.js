/**
 * Core Application Logic for CrimeAlert NG
 */

const App = {
    // API Configuration
    API_URL: '/api',
    
    // Global State
    state: {
        token: localStorage.getItem('token'),
        user: JSON.parse(localStorage.getItem('user') || 'null')
    },
    
    init() {
        console.log('App initialized.');
        this.setupInterceptors();
        this.renderNavigation();
    },
    
    // Setup fetch wrapper to auto-inject JWT token
    api: async (endpoint, options = {}) => {
        const url = `${App.API_URL}${endpoint}`;
        
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };
        
        if (App.state.token) {
            headers['Authorization'] = `Bearer ${App.state.token}`;
        }
        
        // Remove Content-Type if sending FormData (browser sets it with boundary)
        if (options.body instanceof FormData) {
            delete headers['Content-Type'];
        }
        
        const config = {
            ...options,
            headers
        };
        
        try {
            const response = await fetch(url, config);
            const data = await response.json();
            
            if (!response.ok) {
                if (response.status === 401) {
                    // Token expired or invalid
                    Auth.logout(false);
                }
                throw new Error(data.error || data.msg || 'An error occurred');
            }
            
            return data;
        } catch (error) {
            console.error(`API Error (${endpoint}):`, error);
            throw error;
        }
    },
    
    setupInterceptors() {
        // Any global fetch intercepts if needed
    },
    
    // Dynamic Navigation Rendering
    renderNavigation() {
        const navMenu = document.getElementById('nav-menu');
        const navAuth = document.getElementById('nav-auth');
        
        if (!navMenu || !navAuth) return;
        
        let menuHtml = `<a href="/" class="nav-link">Home</a>
                        <a href="/map" class="nav-link">Live Map</a>`;
        let authHtml = '';
        
        if (this.state.user) {
            const role = this.state.user.role;
            
            if (role === 'citizen') {
                menuHtml += `<a href="/dashboard" class="nav-link">My Dashboard</a>`;
                menuHtml += `<a href="/report/new" class="nav-link">Report Crime</a>`;
            } else if (role === 'officer') {
                menuHtml += `<a href="/officer" class="nav-link">Officer Panel</a>`;
            } else if (role === 'admin') {
                menuHtml += `<a href="/admin" class="nav-link">Admin Panel</a>`;
            }
            
            authHtml = `
                <span style="color: var(--text-muted); font-size: 0.9rem;">
                    Hello, <strong>${this.state.user.username}</strong>
                </span>
                <button onclick="Auth.logout()" class="btn btn-outline" style="padding: 6px 12px; font-size: 0.8rem;">
                    <i class="fa-solid fa-sign-out-alt"></i> Logout
                </button>
            `;
        } else {
            authHtml = `
                <a href="/login" class="btn btn-outline" style="padding: 6px 16px;">Login</a>
                <a href="/register" class="btn btn-primary" style="padding: 6px 16px;">Register</a>
            `;
        }
        
        navMenu.innerHTML = menuHtml;
        navAuth.innerHTML = authHtml;
    },
    
    // Toast Notification System
    showToast(title, message, type = 'info') {
        const container = document.getElementById('toast-container');
        if (!container) return;
        
        const icons = {
            'info': 'fa-circle-info',
            'success': 'fa-circle-check',
            'warning': 'fa-triangle-exclamation',
            'error': 'fa-circle-xmark',
            'critical': 'fa-skull-crossbones'
        };
        
        const colors = {
            'info': 'var(--primary-color)',
            'success': 'var(--color-low)',
            'warning': 'var(--color-medium)',
            'error': 'var(--color-high)',
            'critical': 'var(--color-critical)'
        };
        
        const toast = document.createElement('div');
        toast.className = 'toast';
        if (type === 'critical') toast.classList.add('pulse');
        
        toast.style.borderLeftColor = colors[type];
        
        toast.innerHTML = `
            <div class="toast-icon" style="color: ${colors[type]}">
                <i class="fa-solid ${icons[type]}"></i>
            </div>
            <div class="toast-content">
                <h4>${title}</h4>
                <p>${message}</p>
            </div>
        `;
        
        container.appendChild(toast);
        
        // Trigger animation
        setTimeout(() => toast.classList.add('show'), 10);
        
        // Remove after 5 seconds (longer for critical)
        const duration = type === 'critical' ? 8000 : 5000;
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, duration);
    },
    
    // Utility formatters
    formatDate(dateString) {
        if (!dateString) return 'N/A';
        const date = new Date(dateString);
        return date.toLocaleString();
    },
    
    getStatusBadge(status) {
        return `<span class="badge status-${status}">${status}</span>`;
    },
    
    getSeverityBadge(severity) {
        return `<span class="badge badge-${severity}">${severity}</span>`;
    }
};
