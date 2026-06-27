/**
 * Admin Dashboard Logic
 */

const Admin = {
    charts: {},
    
    init() {
        if (!Auth.requireRole(['admin'])) return;
        
        this.fetchStats();
        this.fetchUsers();
        this.fetchLogs();
        this.setupEventListeners();
        
        // Setup Chart.js global defaults for dark theme
        Chart.defaults.color = '#9ca3af';
        Chart.defaults.borderColor = 'rgba(255, 255, 255, 0.05)';
    },
    
    async fetchStats() {
        try {
            const data = await App.api('/admin/stats');
            
            document.getElementById('admin-total-users').innerText = data.total_users;
            document.getElementById('admin-total-reports').innerText = data.total_reports;
            document.getElementById('admin-resolution-rate').innerText = `${data.resolution_rate}%`;
            
            this.renderCategoryChart(data.by_category);
            this.renderSeverityChart(data.by_severity);
            
        } catch (error) {
            console.error('Failed to fetch admin stats:', error);
            App.showToast('Error', 'Failed to load dashboard statistics', 'error');
        }
    },
    
    renderCategoryChart(categoryData) {
        const ctx = document.getElementById('categoryChart').getContext('2d');
        
        // Destroy existing chart if it exists
        if (this.charts.category) {
            this.charts.category.destroy();
        }
        
        if (!categoryData || categoryData.length === 0) return;
        
        const labels = categoryData.map(item => item.name);
        const data = categoryData.map(item => item.count);
        
        this.charts.category = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Reports',
                    data: data,
                    backgroundColor: 'rgba(0, 212, 255, 0.6)',
                    borderColor: 'rgba(0, 212, 255, 1)',
                    borderWidth: 1,
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: { beginAtZero: true, ticks: { precision: 0 } }
                }
            }
        });
    },
    
    renderSeverityChart(severityData) {
        const ctx = document.getElementById('severityChart').getContext('2d');
        
        if (this.charts.severity) {
            this.charts.severity.destroy();
        }
        
        const data = [
            severityData.critical || 0,
            severityData.high || 0,
            severityData.medium || 0,
            severityData.low || 0
        ];
        
        this.charts.severity = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Critical', 'High', 'Medium', 'Low'],
                datasets: [{
                    data: data,
                    backgroundColor: [
                        '#ef4444', // Critical
                        '#f97316', // High
                        '#f59e0b', // Medium
                        '#10b981'  // Low
                    ],
                    borderWidth: 0,
                    hoverOffset: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'right' }
                },
                cutout: '70%'
            }
        });
    },
    
    async fetchUsers(search = '') {
        try {
            const url = search ? `/admin/users?search=${encodeURIComponent(search)}` : '/admin/users';
            const data = await App.api(url);
            
            const tbody = document.getElementById('users-body');
            
            if (data.users.length === 0) {
                tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; padding: 30px; color: var(--text-muted);">No users found.</td></tr>`;
                return;
            }
            
            let html = '';
            data.users.forEach(u => {
                const isCurrent = App.state.user && App.state.user.id === u.id;
                
                let roleBadge = '';
                if (u.role === 'admin') roleBadge = '<span class="badge" style="background: rgba(139, 92, 246, 0.2); color: #8b5cf6;">Admin</span>';
                else if (u.role === 'officer') roleBadge = '<span class="badge" style="background: rgba(59, 130, 246, 0.2); color: #3b82f6;">Officer</span>';
                else roleBadge = '<span class="badge" style="background: rgba(156, 163, 175, 0.2); color: #9ca3af;">Citizen</span>';
                
                const statusBadge = u.is_active 
                    ? '<span class="badge badge-low">Active</span>'
                    : '<span class="badge badge-critical">Deactivated</span>';
                
                html += `
                    <tr>
                        <td>
                            <div style="display: flex; align-items: center; gap: 10px;">
                                <div style="width: 32px; height: 32px; border-radius: 50%; background: ${u.avatar_color}; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 0.8rem;">
                                    ${u.username.charAt(0).toUpperCase()}
                                </div>
                                <div>
                                    <div style="font-weight: 500;">${u.full_name} ${isCurrent ? '<span style="color:var(--text-muted);font-size:0.8rem;">(You)</span>' : ''}</div>
                                    <div style="font-size: 0.8rem; color: var(--text-muted);">${u.email}</div>
                                </div>
                            </div>
                        </td>
                        <td>${roleBadge}</td>
                        <td>${statusBadge}</td>
                        <td><small style="color: var(--text-muted);">${App.formatDate(u.created_at).split(',')[0]}</small></td>
                        <td>
                            <div style="display: flex; gap: 5px;">
                                <button class="btn btn-outline" style="padding: 4px 8px; font-size: 0.8rem;" onclick="Admin.openRoleModal(${u.id}, '${u.username}', '${u.role}')" ${isCurrent ? 'disabled' : ''}>
                                    Role
                                </button>
                                <button class="btn ${u.is_active ? 'btn-danger' : 'btn-outline'}" style="padding: 4px 8px; font-size: 0.8rem;" onclick="Admin.toggleUserStatus(${u.id})" ${isCurrent ? 'disabled' : ''}>
                                    ${u.is_active ? 'Deactivate' : 'Activate'}
                                </button>
                            </div>
                        </td>
                    </tr>
                `;
            });
            
            tbody.innerHTML = html;
            
        } catch (error) {
            console.error('Failed to fetch users:', error);
        }
    },
    
    async fetchLogs() {
        try {
            const data = await App.api('/admin/logs?per_page=50');
            const tbody = document.getElementById('logs-body');

            if (!data.logs || data.logs.length === 0) {
                tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; padding: 30px; color: var(--text-muted);">No activity recorded yet.</td></tr>`;
                return;
            }

            let html = '';
            data.logs.forEach(log => {
                const userLabel = log.user
                    ? `${log.user.full_name} <span style="color: var(--text-muted); font-size: 0.8rem;">(@${log.user.username})</span>`
                    : '<span style="color: var(--text-muted);">System</span>';

                html += `
                    <tr>
                        <td><small style="color: var(--text-muted);">${App.formatDate(log.created_at)}</small></td>
                        <td>${userLabel}</td>
                        <td><span class="badge" style="background: rgba(0, 212, 255, 0.15); color: var(--primary-color);">${log.action}</span></td>
                        <td><small>${log.details || '-'}</small></td>
                        <td><small style="color: var(--text-muted);">${log.ip_address || '-'}</small></td>
                    </tr>
                `;
            });

            tbody.innerHTML = html;
        } catch (error) {
            console.error('Failed to fetch activity logs:', error);
            const tbody = document.getElementById('logs-body');
            if (tbody) {
                tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; padding: 20px; color: var(--color-critical);">Failed to load activity log.</td></tr>`;
            }
        }
    },
    
    setupEventListeners() {
        document.getElementById('user-search').addEventListener('input', (e) => {
            // Debounce could be added here, keeping it simple for now
            this.fetchUsers(e.target.value);
        });

        document.getElementById('btn-refresh-logs').addEventListener('click', () => {
            this.fetchLogs();
        });
        
        document.getElementById('role-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const id = document.getElementById('role-user-id').value;
            const newRole = document.getElementById('new-role').value;
            
            try {
                await App.api(`/admin/users/${id}/role`, {
                    method: 'PUT',
                    body: JSON.stringify({ role: newRole })
                });
                
                App.showToast('Role Updated', 'User permissions changed successfully', 'success');
                this.closeModal('role-modal');
                this.fetchUsers();
                
            } catch (error) {
                App.showToast('Error', error.message, 'error');
            }
        });
    },
    
    openRoleModal(id, username, currentRole) {
        document.getElementById('role-user-id').value = id;
        document.getElementById('role-user-name').innerText = `Editing: @${username}`;
        document.getElementById('new-role').value = currentRole;
        document.getElementById('role-modal').classList.add('active');
    },
    
    closeModal(id) {
        document.getElementById(id).classList.remove('active');
    },
    
    async toggleUserStatus(id) {
        try {
            await App.api(`/admin/users/${id}`, { method: 'DELETE' });
            this.fetchUsers(); // Refresh table
        } catch (error) {
            App.showToast('Error', error.message, 'error');
        }
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    Admin.init();
});
