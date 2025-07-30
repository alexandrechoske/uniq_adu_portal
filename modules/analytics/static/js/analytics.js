// Analytics Module JavaScript - Funcionalidade completa com gráficos e filtros
let analyticsData = {};
let charts = {};
let currentFilters = {
    dateRange: '30d',
    userRole: 'all',
    actionType: 'all',
    startDate: null,
    endDate: null
};

document.addEventListener('DOMContentLoaded', function() {
    console.log('[ANALYTICS] Module loaded');
    initializeAnalytics();
    setupEventListeners();
    loadAnalyticsStats();
});

function initializeAnalytics() {
    // Configurar Chart.js defaults
    Chart.defaults.font.family = 'Segoe UI, Tahoma, Geneva, Verdana, sans-serif';
    Chart.defaults.color = '#6b7280';
    Chart.defaults.borderColor = '#f1f5f9';
    Chart.defaults.backgroundColor = 'rgba(52, 152, 219, 0.1)';
}

function setupEventListeners() {
    // Botões de filtro e refresh
    document.getElementById('open-filters')?.addEventListener('click', openFiltersModal);
    document.getElementById('refresh-data')?.addEventListener('click', refreshData);
    document.getElementById('reset-filters')?.addEventListener('click', resetFilters);
    
    // Modal de filtros
    document.getElementById('apply-filters')?.addEventListener('click', applyFilters);
    document.getElementById('clear-filters')?.addEventListener('click', clearFilters);
    document.querySelector('.close')?.addEventListener('click', closeFiltersModal);
    
    // Period controls
    document.querySelectorAll('.period-btn').forEach(btn => {
        btn.addEventListener('click', handlePeriodChange);
    });
    
    // Date range selector
    document.getElementById('date-range')?.addEventListener('change', handleDateRangeChange);
    
    // Click outside modal to close
    window.addEventListener('click', function(event) {
        const modal = document.getElementById('filters-modal');
        if (event.target === modal) {
            closeFiltersModal();
        }
    });
}

async function loadAnalyticsStats() {
    try {
        console.log('[ANALYTICS] Carregando estatísticas...');
        showLoading();
        
        // Fazer requisições em paralelo
        const [statsResponse, chartsResponse, usersResponse, activityResponse] = await Promise.all([
            fetch('/usuarios/analytics/api/stats?' + new URLSearchParams(currentFilters)),
            fetch('/usuarios/analytics/api/charts?' + new URLSearchParams(currentFilters)),
            fetch('/usuarios/analytics/api/top-users?' + new URLSearchParams(currentFilters)),
            fetch('/usuarios/analytics/api/recent-activity?' + new URLSearchParams(currentFilters))
        ]);
        
        if (!statsResponse.ok || !chartsResponse.ok || !usersResponse.ok || !activityResponse.ok) {
            throw new Error('Erro ao carregar dados');
        }
        
        const [stats, charts, users, activity] = await Promise.all([
            statsResponse.json(),
            chartsResponse.json(),
            usersResponse.json(),
            activityResponse.json()
        ]);
        
        analyticsData = { stats, charts, users, activity };
        
        // Atualizar interface
        updateStatsCards(stats);
        updateCharts(charts);
        updateTopUsersTable(users);
        updateRecentActivityTable(activity);
        updateFilterSummary();
        
        console.log('[ANALYTICS] Dados carregados com sucesso');
        
    } catch (error) {
        console.error('[ANALYTICS] Erro ao carregar dados:', error);
        showError('Erro ao carregar dados: ' + error.message);
    } finally {
        hideLoading();
    }
}

function updateStatsCards(data) {
    // Atualizar KPI cards
    updateKPIValue('total-access', data.total_access || 0);
    updateKPIValue('unique-users', data.unique_users || 0);
    updateKPIValue('logins-today', data.logins_today || 0);
    updateKPIValue('total-logins', data.total_logins || 0);
    updateKPIValue('avg-session', data.avg_session_minutes || 0, 'min');
    
    console.log('[ANALYTICS] Cards atualizados');
}

function updateCharts(chartsData) {
    // Destruir gráficos existentes
    Object.values(charts).forEach(chart => {
        if (chart) chart.destroy();
    });
    charts = {};
    
    // Criar gráficos
    createDailyAccessChart(chartsData.daily_access || []);
    createTopPagesChart(chartsData.top_pages || []);
    createUsersActivityChart(chartsData.users_activity || []);
    createHourlyHeatmapChart(chartsData.hourly_heatmap || []);
    
    console.log('[ANALYTICS] Gráficos atualizados');
}

function createDailyAccessChart(data) {
    const ctx = document.getElementById('daily-access-chart');
    if (!ctx) return;
    
    const labels = data.map(item => new Date(item.date).toLocaleDateString('pt-BR'));
    const values = data.map(item => item.count);
    
    charts.dailyAccess = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Acessos',
                data: values,
                borderColor: '#3498DB',
                backgroundColor: 'rgba(52, 152, 219, 0.1)',
                fill: true,
                tension: 0.4
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

function createTopPagesChart(data) {
    const ctx = document.getElementById('top-pages-chart');
    if (!ctx) return;
    
    const labels = data.slice(0, 10).map(item => item.page_name || 'Sem nome');
    const values = data.slice(0, 10).map(item => item.count);
    
    charts.topPages = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: [
                    '#3498DB', '#10b981', '#f59e0b', '#ef4444', '#06b6d4',
                    '#8b5cf6', '#f97316', '#059669', '#ec4899', '#6366f1'
                ]
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

function createUsersActivityChart(data) {
    const ctx = document.getElementById('users-activity-chart');
    if (!ctx) return;
    
    const labels = data.map(item => item.user_name || 'Usuário');
    const values = data.map(item => item.access_count);
    
    charts.usersActivity = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels.slice(0, 10),
            datasets: [{
                label: 'Acessos',
                data: values.slice(0, 10),
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

function createHourlyHeatmapChart(data) {
    const ctx = document.getElementById('hourly-heatmap-chart');
    if (!ctx) return;
    
    // Preparar dados para heatmap por hora
    const hours = Array.from({length: 24}, (_, i) => i);
    const hourlyData = hours.map(hour => {
        const hourData = data.find(item => item.hour === hour);
        return hourData ? hourData.count : 0;
    });
    
    charts.hourlyHeatmap = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: hours.map(h => h.toString().padStart(2, '0') + ':00'),
            datasets: [{
                label: 'Acessos por Hora',
                data: hourlyData,
                backgroundColor: hourlyData.map(value => {
                    const max = Math.max(...hourlyData);
                    const intensity = max > 0 ? value / max : 0;
                    return `rgba(52, 152, 219, ${0.2 + intensity * 0.8})`;
                }),
                borderColor: '#3498DB',
                borderWidth: 1,
                borderRadius: 2
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

function updateTopUsersTable(data) {
    const tbody = document.querySelector('#top-users-table tbody');
    const countElement = document.getElementById('users-count');
    
    if (!tbody || !countElement) return;
    
    countElement.textContent = `${data.length} usuários`;
    
    tbody.innerHTML = data.map(user => `
        <tr>
            <td>
                <div class="user-info">
                    <strong>${user.user_name || 'N/A'}</strong>
                    <br><small>${user.user_email || ''}</small>
                </div>
            </td>
            <td>
                <span class="role-badge role-${user.user_role || 'unknown'}">${user.user_role || 'N/A'}</span>
            </td>
            <td><strong>${user.total_access || 0}</strong></td>
            <td>${user.last_login ? new Date(user.last_login).toLocaleString('pt-BR') : 'Nunca'}</td>
            <td>${user.avg_session_minutes || 0} min</td>
            <td>${user.favorite_pages || 'N/A'}</td>
        </tr>
    `).join('');
}

function updateRecentActivityTable(data) {
    const tbody = document.querySelector('#recent-activity-table tbody');
    const countElement = document.getElementById('activity-count');
    
    if (!tbody || !countElement) return;
    
    countElement.textContent = `${data.length} atividades`;
    
    tbody.innerHTML = data.map(activity => `
        <tr>
            <td>${new Date(activity.timestamp).toLocaleString('pt-BR')}</td>
            <td>
                <div class="user-info">
                    <strong>${activity.user_name || 'N/A'}</strong>
                    <br><small>${activity.user_email || ''}</small>
                </div>
            </td>
            <td>
                <span class="action-badge action-${activity.action_type || 'unknown'}">${activity.action_type || 'N/A'}</span>
            </td>
            <td>${activity.page_name || activity.endpoint || 'N/A'}</td>
            <td><code>${activity.ip_address || 'N/A'}</code></td>
            <td>${activity.user_agent ? activity.user_agent.substring(0, 50) + '...' : 'N/A'}</td>
        </tr>
    `).join('');
}

function updateKPIValue(elementId, value, suffix = '') {
    const element = document.getElementById(elementId);
    if (element) {
        const displayValue = typeof value === 'number' ? value.toLocaleString('pt-BR') : value;
        animateNumber(element, displayValue + (suffix ? ' ' + suffix : ''));
    }
}

function animateNumber(element, finalValue) {
    // Animação simples
    element.style.opacity = '0.5';
    setTimeout(() => {
        element.textContent = finalValue;
        element.style.opacity = '1';
    }, 200);
}

// Event Handlers
function handlePeriodChange(event) {
    const period = event.target.dataset.period;
    const chart = event.target.dataset.chart;
    
    // Atualizar botões ativos
    event.target.parentElement.querySelectorAll('.period-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');
    
    // Atualizar filtros e recarregar dados
    if (chart === 'daily') {
        currentFilters.dateRange = period;
        loadAnalyticsStats();
    }
}

function handleDateRangeChange(event) {
    const customDates = document.getElementById('custom-dates');
    if (event.target.value === 'custom') {
        customDates.style.display = 'block';
    } else {
        customDates.style.display = 'none';
        currentFilters.dateRange = event.target.value;
    }
}

// Modal Functions
function openFiltersModal() {
    document.getElementById('filters-modal').style.display = 'flex';
    
    // Preencher valores atuais
    document.getElementById('date-range').value = currentFilters.dateRange;
    document.getElementById('user-role').value = currentFilters.userRole;
    document.getElementById('action-type').value = currentFilters.actionType;
}

function closeFiltersModal() {
    document.getElementById('filters-modal').style.display = 'none';
}

function applyFilters() {
    const dateRange = document.getElementById('date-range').value;
    const userRole = document.getElementById('user-role').value;
    const actionType = document.getElementById('action-type').value;
    
    currentFilters = {
        dateRange,
        userRole,
        actionType,
        startDate: dateRange === 'custom' ? document.getElementById('start-date').value : null,
        endDate: dateRange === 'custom' ? document.getElementById('end-date').value : null
    };
    
    // Mostrar/esconder botão de reset
    const hasFilters = userRole !== 'all' || actionType !== 'all' || dateRange !== '30d';
    document.getElementById('reset-filters').style.display = hasFilters ? 'block' : 'none';
    
    loadAnalyticsStats();
    closeFiltersModal();
}

function clearFilters() {
    currentFilters = {
        dateRange: '30d',
        userRole: 'all',
        actionType: 'all',
        startDate: null,
        endDate: null
    };
    
    document.getElementById('reset-filters').style.display = 'none';
    loadAnalyticsStats();
    closeFiltersModal();
}

function resetFilters() {
    clearFilters();
}

function refreshData() {
    loadAnalyticsStats();
}

function updateFilterSummary() {
    const summaryElement = document.getElementById('filter-summary-text');
    if (!summaryElement) return;
    
    let summary = 'Vendo dados ';
    
    // Período
    switch (currentFilters.dateRange) {
        case '1d': summary += 'de hoje'; break;
        case '7d': summary += 'dos últimos 7 dias'; break;
        case '30d': summary += 'dos últimos 30 dias'; break;
        case 'custom': summary += 'personalizados'; break;
        default: summary += 'dos últimos 30 dias';
    }
    
    // Filtros adicionais
    const filters = [];
    if (currentFilters.userRole !== 'all') {
        filters.push(`usuários ${currentFilters.userRole}`);
    }
    if (currentFilters.actionType !== 'all') {
        filters.push(`ações de ${currentFilters.actionType}`);
    }
    
    if (filters.length > 0) {
        summary += ` - ${filters.join(', ')}`;
    }
    
    summaryElement.textContent = summary;
}

// Loading States
function showLoading() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.style.display = 'flex';
    }
}

function hideLoading() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.style.display = 'none';
    }
}

function showError(message) {
    console.error('[ANALYTICS]', message);
    // Pode ser expandido para mostrar toast ou modal de erro
}

// Auto-refresh a cada 5 minutos
setInterval(() => {
    console.log('[ANALYTICS] Auto-refresh das estatísticas');
    loadAnalyticsStats();
}, 300000);

// Expor funções globalmente para debug
window.analyticsModule = {
    refresh: refreshData,
    loadStats: loadAnalyticsStats,
    showError: showError,
    currentFilters: currentFilters,
    analyticsData: analyticsData,
    charts: charts
};
