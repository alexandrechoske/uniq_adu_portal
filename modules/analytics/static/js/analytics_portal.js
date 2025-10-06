// Analytics Portal - Novo JavaScript Otimizado com View
let analyticsData = {};
let charts = {};
let currentFilters = {
    dateRange: '30d',
    userRole: 'all',
    moduleName: 'all'
};

let isLoading = false;

document.addEventListener('DOMContentLoaded', function() {
    console.log('[ANALYTICS PORTAL] Module loaded');
    initializeAnalytics();
});

function initializeAnalytics() {
    // Configurar Chart.js defaults
    Chart.defaults.font.family = 'Segoe UI, Tahoma, Geneva, Verdana, sans-serif';
    Chart.defaults.color = '#6b7280';
    Chart.defaults.borderColor = '#f1f5f9';
    
    setupEventListeners();
    loadAllData();
}

function setupEventListeners() {
    // Botões principais
    document.getElementById('open-filters')?.addEventListener('click', openFiltersModal);
    document.getElementById('refresh-data')?.addEventListener('click', refreshData);
    document.getElementById('reset-filters')?.addEventListener('click', resetFilters);
    
    // Modal
    document.getElementById('apply-filters')?.addEventListener('click', applyFilters);
    document.getElementById('clear-filters')?.addEventListener('click', clearFilters);
    document.querySelector('.close')?.addEventListener('click', closeFiltersModal);
    
    // Click outside modal
    window.addEventListener('click', function(event) {
        const modal = document.getElementById('filters-modal');
        if (event.target === modal) {
            closeFiltersModal();
        }
    });
}

async function loadAllData() {
    if (isLoading) return;
    
    isLoading = true;
    showLoading();
    
    try {
        // Construir query string com filtros
        const params = new URLSearchParams({
            dateRange: currentFilters.dateRange,
            userRole: currentFilters.userRole,
            moduleName: currentFilters.moduleName
        });
        
        // Carregar todas as APIs em paralelo
        const [kpis, timeline, topModules, deviceBreakdown, topPages, recentLogs, userProfile, activeUsers] = await Promise.all([
            fetch(`/analytics/api/portal/kpis?${params}`).then(r => r.json()),
            fetch(`/analytics/api/portal/timeline?${params}`).then(r => r.json()),
            fetch(`/analytics/api/portal/top-modules?${params}`).then(r => r.json()),
            fetch(`/analytics/api/portal/device-breakdown?${params}`).then(r => r.json()),
            fetch(`/analytics/api/portal/top-pages?${params}`).then(r => r.json()),
            fetch(`/analytics/api/portal/recent-logs?${params}`).then(r => r.json()),
            fetch(`/analytics/api/portal/user-profile-breakdown?${params}`).then(r => r.json()),
            fetch(`/analytics/api/portal/most-active-users?${params}`).then(r => r.json())
        ]);
        
        // Atualizar interface
        if (kpis.success) updateKPIs(kpis.data);
        if (timeline.success) createTimelineChart(timeline.data);
        if (topModules.success) createTopModulesChart(topModules.data);
        if (deviceBreakdown.success) createDeviceChart(deviceBreakdown.data);
        if (topPages.success) createTopPagesChart(topPages.data);
        if (recentLogs.success) updateRecentLogsTable(recentLogs.data);
        if (userProfile.success) createUserProfileChart(userProfile.data);
        if (activeUsers.success) updateActiveUsersTable(activeUsers.data);
        
        console.log('[ANALYTICS PORTAL] Todos os dados carregados com sucesso');
        
    } catch (error) {
        console.error('[ANALYTICS PORTAL] Erro ao carregar dados:', error);
        showError('Erro ao carregar dados do analytics');
    } finally {
        isLoading = false;
        hideLoading();
    }
}

function updateKPIs(data) {
    // Total de Acessos
    updateKPIValue('total-access', data.total_access || 0);
    
    // Usuários Únicos
    updateKPIValue('unique-users', data.unique_users || 0);
    
    // Tempo Médio de Resposta
    const avgTime = data.avg_response_time_ms || 0;
    updateKPIValue('avg-response-time', avgTime, 'ms');
    
    // Taxa de Sucesso
    updateKPIValue('success-rate', data.success_rate || 100, '%');
    
    console.log('[ANALYTICS PORTAL] KPIs atualizados');
}

function createTimelineChart(data) {
    const ctx = document.getElementById('timeline-chart');
    if (!ctx) return;
    
    // Destruir gráfico existente
    if (charts.timeline) {
        charts.timeline.destroy();
    }
    
    charts.timeline = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels || [],
            datasets: [{
                label: 'Acessos',
                data: data.values || [],
                borderColor: '#3498DB',
                backgroundColor: 'rgba(52, 152, 219, 0.1)',
                fill: true,
                tension: 0.4,
                pointRadius: 4,
                pointBackgroundColor: '#3498DB',
                pointBorderColor: '#ffffff',
                pointBorderWidth: 2,
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: 'white',
                    bodyColor: 'white',
                    borderColor: '#3498DB',
                    borderWidth: 1,
                    cornerRadius: 8
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    }
                },
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    },
                    ticks: {
                        precision: 0
                    }
                }
            }
        }
    });
}

function createTopModulesChart(data) {
    const ctx = document.getElementById('top-modules-chart');
    if (!ctx) return;
    
    if (charts.topModules) {
        charts.topModules.destroy();
    }
    
    charts.topModules = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.labels || [],
            datasets: [{
                label: 'Acessos',
                data: data.values || [],
                backgroundColor: '#10b981',
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    }
                },
                y: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0
                    }
                }
            }
        }
    });
}

function createDeviceChart(data) {
    const ctx = document.getElementById('device-chart');
    if (!ctx) return;
    
    if (charts.device) {
        charts.device.destroy();
    }
    
    charts.device = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: data.labels || [],
            datasets: [{
                data: data.values || [],
                backgroundColor: ['#3498DB', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        boxWidth: 12,
                        padding: 10
                    }
                }
            }
        }
    });
}

function createTopPagesChart(data) {
    const ctx = document.getElementById('top-pages-chart');
    if (!ctx) return;
    
    if (charts.topPages) {
        charts.topPages.destroy();
    }
    
    charts.topPages = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.labels || [],
            datasets: [{
                label: 'Acessos',
                data: data.values || [],
                backgroundColor: '#3498DB',
                borderRadius: 4
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0
                    }
                },
                y: {
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

function createUserProfileChart(data) {
    const ctx = document.getElementById('user-profile-chart');
    if (!ctx) return;
    
    if (charts.userProfile) {
        charts.userProfile.destroy();
    }
    
    charts.userProfile = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: data.labels || [],
            datasets: [{
                data: data.values || [],
                backgroundColor: ['#3498DB', '#10b981', '#f59e0b', '#ef4444']
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        boxWidth: 12,
                        padding: 10
                    }
                }
            }
        }
    });
}

function updateRecentLogsTable(logs) {
    const tbody = document.querySelector('#recent-logs-table tbody');
    const countElement = document.getElementById('logs-count');
    
    if (!tbody || !countElement) return;
    
    countElement.textContent = `${logs.length} registros`;
    
    tbody.innerHTML = logs.map(log => {
        // Formatar data/hora para padrão brasileiro
        let timestampFormatted = 'N/A';
        if (log.access_timestamp) {
            try {
                const date = new Date(log.access_timestamp);
                timestampFormatted = date.toLocaleString('pt-BR', {
                    day: '2-digit',
                    month: '2-digit',
                    year: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit'
                });
            } catch (e) {
                timestampFormatted = log.access_timestamp;
            }
        }
        
        return `
            <tr>
                <td>${timestampFormatted}</td>
                <td>
                    <strong>${log.user_name || 'N/A'}</strong><br>
                    <small>${log.user_email || ''}</small>
                </td>
                <td><span class="role-badge role-${log.user_role || 'unknown'}">${log.user_role || 'N/A'}</span></td>
                <td>${log.module_name || 'N/A'}</td>
                <td>${log.page_name || 'N/A'}</td>
                <td>
                    <span class="status-badge status-${log.http_status < 400 ? 'success' : 'error'}">
                        ${log.http_status || 200}
                    </span>
                </td>
            </tr>
        `;
    }).join('');
}

function updateActiveUsersTable(users) {
    const tbody = document.querySelector('#active-users-table tbody');
    const countElement = document.getElementById('users-count');
    
    if (!tbody || !countElement) return;
    
    countElement.textContent = `${users.length} usuários`;
    
    tbody.innerHTML = users.map(user => {
        // Formatar último acesso
        let lastAccessFormatted = 'N/A';
        if (user.last_access) {
            try {
                const date = new Date(user.last_access);
                lastAccessFormatted = date.toLocaleString('pt-BR', {
                    day: '2-digit',
                    month: '2-digit',
                    year: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                });
            } catch (e) {
                lastAccessFormatted = user.last_access;
            }
        }
        
        return `
            <tr>
                <td>
                    <strong>${user.user_name || 'N/A'}</strong><br>
                    <small>${user.user_email || ''}</small>
                </td>
                <td><span class="role-badge role-${user.user_role || 'unknown'}">${user.user_role || 'N/A'}</span></td>
                <td><strong>${user.access_count || 0}</strong></td>
                <td><strong>${lastAccessFormatted}</strong></td>
            </tr>
        `;
    }).join('');
}

function updateKPIValue(elementId, value, suffix = '') {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = value.toLocaleString('pt-BR') + (suffix ? ' ' + suffix : '');
    }
}

// Modal Functions
function openFiltersModal() {
    document.getElementById('filters-modal').style.display = 'flex';
    
    // Preencher valores atuais
    document.getElementById('date-range').value = currentFilters.dateRange;
    document.getElementById('user-role').value = currentFilters.userRole;
    document.getElementById('module-name').value = currentFilters.moduleName;
}

function closeFiltersModal() {
    document.getElementById('filters-modal').style.display = 'none';
}

function applyFilters() {
    const dateRange = document.getElementById('date-range').value;
    const userRole = document.getElementById('user-role').value;
    const moduleName = document.getElementById('module-name').value;
    
    currentFilters = {
        dateRange: dateRange,
        userRole: userRole,
        moduleName: moduleName
    };
    
    updateFilterSummary();
    closeFiltersModal();
    loadAllData();
}

function clearFilters() {
    currentFilters = {
        dateRange: '30d',
        userRole: 'all',
        moduleName: 'all'
    };
    
    document.getElementById('date-range').value = '30d';
    document.getElementById('user-role').value = 'all';
    document.getElementById('module-name').value = 'all';
}

function resetFilters() {
    clearFilters();
    updateFilterSummary();
    closeFiltersModal();
    loadAllData();
}

function refreshData() {
    loadAllData();
}

function updateFilterSummary() {
    const summaryText = document.getElementById('filter-summary-text');
    const resetBtn = document.getElementById('reset-filters');
    
    if (!summaryText || !resetBtn) return;
    
    let text = 'Vendo dados ';
    
    // Período
    if (currentFilters.dateRange === '1d') {
        text += 'de hoje';
    } else if (currentFilters.dateRange === '7d') {
        text += 'dos últimos 7 dias';
    } else if (currentFilters.dateRange === '30d') {
        text += 'dos últimos 30 dias';
    }
    
    // Role
    if (currentFilters.userRole !== 'all') {
        text += ` • Perfil: ${currentFilters.userRole}`;
    }
    
    // Módulo
    if (currentFilters.moduleName !== 'all') {
        text += ` • Módulo: ${currentFilters.moduleName}`;
    }
    
    summaryText.textContent = text;
    
    // Mostrar/ocultar botão de reset
    const hasFilters = currentFilters.userRole !== 'all' || currentFilters.moduleName !== 'all';
    resetBtn.style.display = hasFilters ? 'inline-block' : 'none';
}

// Loading States
function showLoading() {
    document.querySelectorAll('.component-loading').forEach(el => {
        el.style.display = 'flex';
    });
}

function hideLoading() {
    document.querySelectorAll('.component-loading').forEach(el => {
        el.style.display = 'none';
    });
}

function showError(message) {
    console.error('[ANALYTICS PORTAL]', message);
    // Pode adicionar toast/notification aqui
}

// Auto-refresh a cada 5 minutos
setInterval(() => {
    if (!document.hidden) {
        console.log('[ANALYTICS PORTAL] Auto-refresh');
        loadAllData();
    }
}, 300000);

// Expor para debug
window.analyticsPortal = {
    refresh: refreshData,
    loadData: loadAllData,
    currentFilters: currentFilters,
    charts: charts
};
