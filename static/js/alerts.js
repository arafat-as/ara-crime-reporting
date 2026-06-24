/**
 * Real-time Alerts and Socket.IO Integration
 */

const Alerts = {
    socket: null,
    
    init() {
        this.fetchActiveAlerts();
        this.initSocket();
    },
    
    initSocket() {
        // Only init if socket.io is loaded
        if (typeof io === 'undefined') return;
        
        this.socket = io({
            auth: {
                token: App.state.token
            }
        });
        
        this.socket.on('connect', () => {
            console.log('Socket.IO connected');
        });
        
        this.socket.on('new_alert', (alert) => {
            console.log('New alert received:', alert);
            
            // Show toast
            const isCritical = alert.severity === 'critical' || alert.severity === 'high';
            App.showToast(`🚨 Area Alert: ${alert.title}`, alert.message, isCritical ? 'critical' : 'warning');
            
            // Refresh ticker
            this.fetchActiveAlerts();
        });
        
        this.socket.on('new_report', (report) => {
            // Only officers and admins should be notified of new raw reports generally
            if (App.state.user && ['officer', 'admin'].includes(App.state.user.role)) {
                App.showToast('New Report Submitted', report.title, 'info');
                // If on officer dashboard, refresh queue
                if (window.location.pathname === '/officer' && typeof window.refreshOfficerQueue === 'function') {
                    window.refreshOfficerQueue();
                }
            }
        });
        
        this.socket.on('report_update', (report) => {
            // If the user is the reporter, notify them of status change
            if (App.state.user && report.reporter && report.reporter.id === App.state.user.id) {
                App.showToast(
                    'Report Status Updated', 
                    `Your report "${report.title}" is now ${report.status}`, 
                    'info'
                );
                // If on dashboard, refresh my reports
                if (window.location.pathname === '/dashboard' && typeof window.refreshMyReports === 'function') {
                    window.refreshMyReports();
                }
            }
        });
    },
    
    async fetchActiveAlerts() {
        try {
            const data = await App.api('/alerts');
            this.renderTicker(data.alerts);
        } catch (error) {
            console.error('Failed to fetch alerts:', error);
        }
    },
    
    renderTicker(alerts) {
        const tickerContainer = document.getElementById('global-alert-ticker');
        const tickerContent = document.getElementById('ticker-content');
        
        if (!tickerContainer || !tickerContent) return;
        
        if (!alerts || alerts.length === 0) {
            tickerContainer.style.display = 'none';
            return;
        }
        
        let html = '';
        // Duplicate alerts to make the infinite scroll smooth
        const displayAlerts = [...alerts, ...alerts, ...alerts];
        
        displayAlerts.forEach(alert => {
            const isCritical = alert.severity === 'critical';
            const icon = isCritical ? '<i class="fa-solid fa-triangle-exclamation" style="color: yellow;"></i>' : '🚨';
            
            html += `
                <div class="ticker-item">
                    ${icon} <strong>${alert.title}:</strong> ${alert.message}
                </div>
                <div class="ticker-item" style="color: rgba(255,255,255,0.3);"> | </div>
            `;
        });
        
        tickerContent.innerHTML = html;
        tickerContainer.style.display = 'block';
    }
};
