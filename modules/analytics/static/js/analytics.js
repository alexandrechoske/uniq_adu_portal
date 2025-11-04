// Analytics Module JavaScript - Funcionalidade completa com gráficos e filtros
const ANALYTICS_DEBUG = false; // Ativar para logs detalhados
let analyticsData = {};
let charts = {};
let currentFilters = {
    dateRange: '30d',
    userRole: 'all',
    actionType: 'all',
    startDate: null,
    endDate: null
};

let isLoading = false;
let loadAttempts = 0;
const maxLoadAttempts = 3;

// Helper para logs condicionais
function logDebug(message, ...args) {
    if (ANALYTICS_DEBUG) {
        console.log(message, ...args);
    }
}

document.addEventListener('DOMContentLoaded', function() {
    console.log('[ANALYTICS] Module loaded - Starting initialization');
    
    // Inicializar imediatamente - não depender de unifiedLoadingManager
    initializeAnalytics();
    setupEventListeners();
    
    // Aguardar um pouco antes de carregar para permitir que outros scripts inicializem
    setTimeout(() => {
        console.log('[ANALYTICS] Calling loadAnalyticsStats()');
        loadAnalyticsStats();
    }, 500);
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
    console.log('[ANALYTICS] loadAnalyticsStats called - isLoading:', isLoading);
    
    if (isLoading) {
        logDebug('[ANALYTICS] Já está carregando, aguardando...');
        return;
    }
    
    isLoading = true;
    loadAttempts++;
    
    try {
        console.log('[ANALYTICS] Fetching data - attempt', loadAttempts);
        
        // Fazer requisições em paralelo
        const [statsResponse, chartsResponse, usersResponse, activityResponse, inactiveUsersResponse] = await Promise.all([
            fetch('/analytics/api/stats?' + new URLSearchParams(currentFilters)),
            fetch('/analytics/api/charts?' + new URLSearchParams(currentFilters)),
            fetch('/analytics/api/top-users?' + new URLSearchParams(currentFilters)),
            fetch('/analytics/api/recent-activity?' + new URLSearchParams(currentFilters)),
            fetch('/analytics/api/inactive-users')
        ]);
        
        console.log('[ANALYTICS] Responses received:', {
            stats: statsResponse.status,
            charts: chartsResponse.status,
            users: usersResponse.status,
            activity: activityResponse.status,
            inactiveUsers: inactiveUsersResponse.status
        });
        
        if (!statsResponse.ok || !chartsResponse.ok || !usersResponse.ok || !activityResponse.ok || !inactiveUsersResponse.ok) {
            throw new Error('Erro ao carregar dados - Status codes: ' + 
                [statsResponse.status, chartsResponse.status, usersResponse.status, activityResponse.status, inactiveUsersResponse.status].join(','));
        }
        
        const [stats, charts, users, activity, inactiveUsersData] = await Promise.all([
            statsResponse.json(),
            chartsResponse.json(),
            usersResponse.json(),
            activityResponse.json(),
            inactiveUsersResponse.json()
        ]);
        
        console.log('[ANALYTICS] Data parsed successfully');
        console.log('[ANALYTICS] Charts data received:', {
            daily_access_count: charts.daily_access?.length,
            first_date: charts.daily_access?.[0]?.date,
            last_date: charts.daily_access?.[charts.daily_access?.length - 1]?.date,
            last_count: charts.daily_access?.[charts.daily_access?.length - 1]?.count
        });
        
        analyticsData = { stats, charts, users, activity, inactiveUsers: inactiveUsersData.inactive_users || [] };
        
        // Atualizar interface
        updateStatsCards(stats);
        updateCharts(charts);
        updateTopUsersTable(users);
        updateInactiveUsersTable(analyticsData.inactiveUsers);
        updateRecentActivityTable(activity);
        updateFilterSummary();
        
        console.log('[ANALYTICS] ✅ All data loaded and rendered successfully');
        loadAttempts = 0; // Reset attempts on success
        
        // Notificar sistema unificado que o carregamento foi concluído
        if (window.unifiedLoadingManager && window.unifiedLoadingManager.isTransitioning) {
            logDebug('[ANALYTICS] Notificando sistema unificado - dados carregados');
            // O sistema unificado detectará automaticamente que os dados carregaram
        }
        
    } catch (error) {
        console.error('[ANALYTICS] ❌ ERROR loading data:', error);
        console.error('[ANALYTICS] Error stack:', error.stack);
        
        // Tentar novamente se não atingiu o máximo
        if (loadAttempts < maxLoadAttempts) {
            console.warn('[ANALYTICS] Retrying in 2 seconds... (attempt', loadAttempts + 1, 'of', maxLoadAttempts, ')');
            setTimeout(() => {
                isLoading = false;
                loadAnalyticsStats();
            }, 2000);
            return;
        } else {
            showError('Erro ao carregar dados: ' + error.message);
            loadAttempts = 0;
        }
    } finally {
        isLoading = false;
    }
}

function updateStatsCards(data) {
    // Atualizar KPI cards
    updateKPIValue('total-access', data.total_access || 0);
    updateKPIValue('unique-users', data.unique_users || 0);
    updateKPIValue('logins-today', data.logins_today || 0);
    updateKPIValue('total-logins', data.total_logins || 0);
    updateKPIValue('avg-session', data.avg_session_minutes || 0, 'min');
    
    logDebug('[ANALYTICS] Cards atualizados');
}

function updateCharts(chartsData) {
    // Destruir gráficos existentes explicitamente
    Object.values(charts).forEach(chart => {
        if (chart && typeof chart.destroy === 'function') {
            chart.destroy();
        }
    });
    charts = {};
    
    // Aguardar um pouco para garantir limpeza completa
    setTimeout(() => {
        // Criar gráficos
        createDailyAccessChart(chartsData);
        createTopPagesChart(chartsData.top_pages || []);
        createUsersActivityChart(chartsData.users_activity || []);
        createHourlyHeatmapChart(chartsData.hourly_heatmap || []);
        
        logDebug('[ANALYTICS] Gráficos atualizados');
    }, 100);
}

function createDailyAccessChart(data) {
    const ctx = document.getElementById('daily-access-chart');
    if (!ctx) return;
    
    // Tratamento seguro das datas
    // Espera-se que chartsData tenha daily_access e daily_users
    const accessData = data.daily_access || [];
    const usersData = data.daily_users || [];

    console.log('[ANALYTICS] createDailyAccessChart - Dados recebidos:', {
        totalDias: accessData.length,
        primeiroDia: accessData[0]?.date,
        ultimoDia: accessData[accessData.length - 1]?.date,
        ultimoCount: accessData[accessData.length - 1]?.count
    });

    // Garantir que as datas estejam alinhadas
    const labels = accessData.map(item => {
        try {
            const date = new Date(item.date);
            return date.toLocaleDateString('pt-BR', { 
                day: '2-digit', 
                month: '2-digit' 
            });
        } catch {
            return item.date;
        }
    });
    
    const accessValues = accessData.map(item => item.count || 0);
    const usersValues = usersData.map(item => item.count || 0);

    console.log('[ANALYTICS] Daily Chart - Total de labels:', labels.length);
    console.log('[ANALYTICS] Daily Chart - Últimos 5 labels:', labels.slice(-5));
    console.log('[ANALYTICS] Daily Chart - Últimos 5 valores:', accessValues.slice(-5));
    logDebug('[ANALYTICS] Daily Chart - Access Values:', accessValues);
    logDebug('[ANALYTICS] Daily Chart - Users Values:', usersValues);
    logDebug('[ANALYTICS] Daily Chart - Labels:', labels);

    charts.dailyAccess = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Total de Acessos',
                    data: accessValues,
                    borderColor: '#3498DB',
                    backgroundColor: 'rgba(52, 152, 219, 0.1)',
                    fill: true,
                    tension: 0.4,
                    pointRadius: function(context) {
                        // Mostrar pontos maiores apenas quando há dados
                        return context.raw > 0 ? 5 : 3;
                    },
                    pointBackgroundColor: '#3498DB',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2,
                    borderWidth: 2
                },
                {
                    label: 'Total de Usuários',
                    data: usersValues,
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.08)',
                    fill: false,
                    tension: 0.4,
                    pointRadius: function(context) {
                        // Mostrar pontos maiores apenas quando há dados
                        return context.raw > 0 ? 5 : 3;
                    },
                    pointBackgroundColor: '#10b981',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2,
                    borderWidth: 2
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'index'
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        boxWidth: 16,
                        font: { weight: 'bold' },
                        usePointStyle: true,
                        padding: 20
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: 'white',
                    bodyColor: 'white',
                    borderColor: '#3498DB',
                    borderWidth: 1,
                    cornerRadius: 8,
                    displayColors: true,
                    callbacks: {
                        title: function(context) {
                            return `Data: ${context[0].label}`;
                        },
                        label: function(context) {
                            return `${context.dataset.label}: ${context.raw}`;
                        }
                    }
                },
                datalabels: {
                    display: function(context) {
                        // Mostrar apenas se o valor for maior que 0
                        return context.dataset.data[context.dataIndex] > 0;
                    },
                    align: 'top',
                    anchor: 'end',
                    color: function(context) {
                        return context.datasetIndex === 0 ? '#3498DB' : '#10b981';
                    },
                    font: {
                        size: 10,
                        weight: 'bold'
                    },
                    formatter: function(value) {
                        return value > 0 ? value : '';
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        maxRotation: 45,
                        font: {
                            size: 11
                        }
                    }
                },
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    },
                    ticks: {
                        precision: 0,
                        font: {
                            size: 11
                        }
                    }
                }
            }
        },
        plugins: [ChartDataLabels]
    });
}

function createTopPagesChart(data) {
    const ctx = document.getElementById('top-pages-chart');
    if (!ctx) return;
    
    const labels = data.slice(0, 10).map(item => item.page_name || 'Sem nome');
    const values = data.slice(0, 10).map(item => item.count);
    
    // Mudar para heatmap (bar horizontal)
    charts.topPages = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Acessos',
                data: values,
                backgroundColor: values.map(value => {
                    const max = Math.max(...values);
                    const intensity = max > 0 ? value / max : 0;
                    return `rgba(52, 152, 219, ${0.3 + intensity * 0.7})`;
                }),
                borderColor: '#3498DB',
                borderWidth: 1
            }]
        },
        options: {
            indexAxis: 'y', // Barras horizontais
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                datalabels: {
                    display: true,
                    align: 'end',
                    anchor: 'end',
                    color: '#3498DB',
                    font: {
                        size: 11,
                        weight: 'bold'
                    },
                    formatter: function(value) {
                        return value;
                    }
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    },
                    ticks: {
                        precision: 0
                    }
                },
                y: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        font: {
                            size: 10
                        }
                    }
                }
            }
        },
        plugins: [ChartDataLabels]
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
                borderRadius: 4,
                borderSkipped: false
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
                    borderColor: '#10b981',
                    borderWidth: 1,
                    cornerRadius: 8,
                    callbacks: {
                        title: function(context) {
                            return `Usuário: ${context[0].label}`;
                        },
                        label: function(context) {
                            return `Acessos: ${context.raw}`;
                        }
                    }
                },
                datalabels: {
                    display: true,
                    align: 'end',
                    anchor: 'end',
                    color: '#10b981',
                    font: {
                        size: 11,
                        weight: 'bold'
                    },
                    formatter: function(value) {
                        return value;
                    }
                }
            },
            scales: { 
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        maxRotation: 45,
                        font: {
                            size: 10
                        }
                    }
                },
                y: { 
                    beginAtZero: true, 
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    },
                    ticks: { 
                        precision: 0,
                        font: {
                            size: 11
                        }
                    } 
                } 
            }
        },
        plugins: [ChartDataLabels]
    });
}

function createHourlyHeatmapChart(data) {
    const ctx = document.getElementById('hourly-heatmap-chart');
    if (!ctx) return;
    
    // Preparar dados para heatmap por hora com usuários únicos
    const hours = Array.from({length: 24}, (_, i) => i);
    const hourlyData = hours.map(hour => {
        const hourData = data.find(item => item.hour === hour);
        return hourData ? hourData.count : 0;
    });
    
    const hourlyUsers = hours.map(hour => {
        const hourData = data.find(item => item.hour === hour);
        return hourData ? hourData.unique_users : 0;
    });
    
    charts.hourlyHeatmap = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: hours.map(h => h.toString().padStart(2, '0') + ':00'),
            datasets: [
                {
                    label: 'Total de Acessos',
                    data: hourlyData,
                    backgroundColor: hourlyData.map(value => {
                        const max = Math.max(...hourlyData);
                        const intensity = max > 0 ? value / max : 0;
                        return `rgba(52, 152, 219, ${0.2 + intensity * 0.8})`;
                    }),
                    borderColor: '#3498DB',
                    borderWidth: 1,
                    borderRadius: 2
                },
                {
                    label: 'Usuários Únicos',
                    data: hourlyUsers,
                    backgroundColor: 'rgba(16, 185, 129, 0.6)',
                    borderColor: '#10b981',
                    borderWidth: 1,
                    borderRadius: 2
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        boxWidth: 12,
                        font: { weight: 'bold' },
                        padding: 15
                    }
                },
                datalabels: {
                    display: function(context) {
                        return context.dataset.data[context.dataIndex] > 0;
                    },
                    align: 'end',
                    anchor: 'end',
                    color: function(context) {
                        return context.datasetIndex === 0 ? '#3498DB' : '#10b981';
                    },
                    font: {
                        size: 9,
                        weight: 'bold'
                    },
                    formatter: function(value) {
                        return value > 0 ? value : '';
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        font: {
                            size: 9
                        }
                    }
                },
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    },
                    ticks: {
                        precision: 0,
                        font: {
                            size: 10
                        }
                    }
                }
            }
        },
        plugins: [ChartDataLabels]
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
            <td>${user.last_access ? new Date(user.last_access).toLocaleString('pt-BR') : 'N/A'}</td>
            <td>${user.favorite_pages || 'N/A'}</td>
        </tr>
    `).join('');
}

function updateInactiveUsersTable(data) {
    const tbody = document.querySelector('#inactive-users-table tbody');
    const countElement = document.getElementById('inactive-users-count');
    
    if (!tbody || !countElement) return;
    
    countElement.textContent = `${data.length} usuários inativos`;
    
    if (data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 2rem; color: #6b7280;">Nenhum usuário inativo encontrado</td></tr>';
        return;
    }
    
    // Garantir ordenação decrescente por dias inativos (mais dias primeiro)
    const sortedData = [...data].sort((a, b) => b.days_inactive - a.days_inactive);
    
    tbody.innerHTML = sortedData.map(user => `
        <tr>
            <td>
                <div class="user-info">
                    <strong>${user.user_name || 'N/A'}</strong>
                </div>
            </td>
            <td>${user.user_email || 'N/A'}</td>
            <td>
                <span class="role-badge role-${user.user_role || 'unknown'}">${user.user_role || 'N/A'}</span>
            </td>
            <td>${user.last_access || 'Nunca acessou'}</td>
            <td>
                <span class="badge badge-warning" style="background-color: ${user.days_inactive > 30 ? '#ef4444' : '#f59e0b'}; color: white; padding: 4px 8px; border-radius: 4px;">
                    ${user.days_inactive} dias
                </span>
            </td>
        </tr>
    `).join('');
}

// Variáveis de paginação
let currentPage = 1;
let itemsPerPage = 15;
let allActivities = [];

function updateRecentActivityTable(data) {
    const tbody = document.querySelector('#recent-activity-table tbody');
    const countElement = document.getElementById('activity-count');
    
    if (!tbody || !countElement) return;
    
    // Armazenar todos os dados
    allActivities = data;
    
    // Renderizar primeira página
    renderActivityPage(1);
    
    // Criar controles de paginação
    createPaginationControls();
}

function renderActivityPage(page) {
    const tbody = document.querySelector('#recent-activity-table tbody');
    const countElement = document.getElementById('activity-count');
    
    if (!tbody || !countElement) return;
    
    currentPage = page;
    
    // Calcular índices
    const startIndex = (page - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    const pageData = allActivities.slice(startIndex, endIndex);
    
    // Atualizar contador
    const totalPages = Math.ceil(allActivities.length / itemsPerPage);
    countElement.textContent = `${allActivities.length} atividades (Página ${page} de ${totalPages})`;
    
    tbody.innerHTML = pageData.map(activity => {
        // Tratamento seguro da data
        let formattedDate = 'Data inválida';
        if (activity.timestamp) {
            try {
                const date = new Date(activity.timestamp);
                if (!isNaN(date.getTime())) {
                    formattedDate = date.toLocaleString('pt-BR');
                }
            } catch (e) {
                console.warn('Erro ao formatar data:', activity.timestamp, e);
            }
        }
        
        return `
        <tr>
            <td>${formattedDate}</td>
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
        `;
    }).join('');
}

function createPaginationControls() {
    const container = document.getElementById('recent-activity-container');
    if (!container) return;
    
    // Remover controles existentes
    const existingControls = container.querySelector('.pagination-controls');
    if (existingControls) {
        existingControls.remove();
    }
    
    const totalPages = Math.ceil(allActivities.length / itemsPerPage);
    
    if (totalPages <= 1) return; // Não mostrar paginação se tiver apenas 1 página
    
    const controls = document.createElement('div');
    controls.className = 'pagination-controls';
    controls.style.cssText = 'display: flex; justify-content: center; align-items: center; gap: 10px; padding: 20px; margin-top: 10px;';
    
    // Botão anterior
    const prevBtn = document.createElement('button');
    prevBtn.textContent = '‹ Anterior';
    prevBtn.className = 'btn btn-sm btn-outline-secondary';
    prevBtn.disabled = currentPage === 1;
    prevBtn.onclick = () => {
        if (currentPage > 1) {
            renderActivityPage(currentPage - 1);
            createPaginationControls();
        }
    };
    
    // Informação da página
    const pageInfo = document.createElement('span');
    pageInfo.textContent = `Página ${currentPage} de ${totalPages}`;
    pageInfo.style.cssText = 'color: #6b7280; font-weight: 500;';
    
    // Botão próximo
    const nextBtn = document.createElement('button');
    nextBtn.textContent = 'Próximo ›';
    nextBtn.className = 'btn btn-sm btn-outline-secondary';
    nextBtn.disabled = currentPage === totalPages;
    nextBtn.onclick = () => {
        if (currentPage < totalPages) {
            renderActivityPage(currentPage + 1);
            createPaginationControls();
        }
    };
    
    controls.appendChild(prevBtn);
    controls.appendChild(pageInfo);
    controls.appendChild(nextBtn);
    
    container.appendChild(controls);
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
        
        // Garantir que os gráficos sejam destruídos antes de recarregar
        Object.values(charts).forEach(chart => {
            if (chart && typeof chart.destroy === 'function') {
                chart.destroy();
            }
        });
        charts = {};
        
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

function refreshData() {
    logDebug('[ANALYTICS] Refresh manual iniciado');
    loadAnalyticsStats();
}

async function silentRefresh() {
    logDebug('[ANALYTICS] Refresh silencioso iniciado');
    if (isLoading) {
        logDebug('[ANALYTICS] Já está carregando, pulando refresh silencioso');
        return;
    }
    
    try {
        await loadAnalyticsStats();
        logDebug('[ANALYTICS] Refresh silencioso concluído com sucesso');
        return true;
    } catch (error) {
        console.error('[ANALYTICS] Erro no refresh silencioso:', error);
        return false;
    }
}

function resetFilters() {
    currentFilters = {
        dateRange: '30d',
        userRole: 'all',
        actionType: 'all',
        startDate: null,
        endDate: null
    };
    
    // Reset form values
    const form = document.getElementById('filters-modal');
    if (form) {
        form.querySelectorAll('select, input').forEach(input => {
            if (input.type === 'date') {
                input.value = '';
            } else {
                input.value = input.getAttribute('data-default') || input.options ? input.options[0].value : '';
            }
        });
    }
    
    closeFiltersModal();
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

// Loading States - Integrado com sistema unificado
function showLoading() {
    // Sistema unificado gerencia loading - manter apenas para compatibilidade
    logDebug('[ANALYTICS] showLoading chamado - gerenciado por sistema unificado');
}

function hideLoading() {
    // Sistema unificado gerencia loading - manter apenas para compatibilidade
    logDebug('[ANALYTICS] hideLoading chamado - gerenciado por sistema unificado');
}

function showError(message) {
    console.error('[ANALYTICS]', message);
    // Pode ser expandido para mostrar toast ou modal de erro
}

// Auto-refresh a cada 5 minutos
setInterval(() => {
    logDebug('[ANALYTICS] Auto-refresh das estatísticas');
    loadAnalyticsStats();
}, 300000);

// Expor funções globalmente para debug e validação
window.analyticsModule = {
    refresh: refreshData,
    silentRefresh: silentRefresh,
    loadStats: loadAnalyticsStats,
    showError: showError,
    currentFilters: currentFilters,
    analyticsData: analyticsData,
    charts: charts,
    isLoading: () => isLoading,
    hasData: () => {
        return analyticsData && 
               Object.keys(analyticsData).length > 0 &&
               Object.keys(charts).length > 0;
    }
};
