/**
 * Dashboard Executivo - JavaScript Module
 * Handles all dashboard executive functionality
 */

// Global variables
let dashboardData = null;
let dashboardCharts = {};
let monthlyChartPeriod = 'mensal';

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('[DASHBOARD_EXECUTIVO] Inicializando...');
    initializeDashboard();
});

/**
 * Initialize the dashboard
 */
async function initializeDashboard() {
    try {
        showLoading(true);
        await loadInitialData();
        setupEventListeners();
        setMonthlyChartPeriod('mensal');
        showLoading(false);
        updateLastUpdate();
    } catch (error) {
        console.error('[DASHBOARD_EXECUTIVO] Erro na inicialização:', error);
        showError('Erro ao carregar dashboard: ' + error.message);
        showLoading(false);
    }
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // Refresh data button
    const refreshBtn = document.getElementById('refresh-data');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', refreshData);
    }

    // Period buttons for monthly chart
    document.querySelectorAll('.period-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const period = this.dataset.period;
            setMonthlyChartPeriod(period);
        });
    });

    // Export data button
    const exportBtn = document.getElementById('export-data');
    if (exportBtn) {
        exportBtn.addEventListener('click', exportData);
    }
}

/**
 * Load initial data
 */
async function loadInitialData() {
    try {
        console.log('[DASHBOARD_EXECUTIVO] Carregando dados iniciais...');
        
        // Load data
        const response = await fetch('/dashboard-executivo/api/load-data');
        const result = await response.json();
        
        if (!result.success) {
            throw new Error(result.error || 'Erro ao carregar dados');
        }
        
        dashboardData = result.data;
        console.log(`[DASHBOARD_EXECUTIVO] Dados carregados: ${result.total_records} registros`);
        
        // Load KPIs and charts
        await Promise.all([
            loadDashboardKPIs(),
            loadDashboardCharts(),
            loadRecentOperations()
        ]);
        
    } catch (error) {
        console.error('[DASHBOARD_EXECUTIVO] Erro ao carregar dados:', error);
        throw error;
    }
}

/**
 * Load dashboard KPIs
 */
async function loadDashboardKPIs() {
    try {
        console.log('[DASHBOARD_EXECUTIVO] Carregando KPIs...');
        
        const response = await fetch('/dashboard-executivo/api/kpis');
        const result = await response.json();
        
        if (result.success) {
            updateDashboardKPIs(result.kpis);
        } else {
            console.error('[DASHBOARD_EXECUTIVO] Erro ao carregar KPIs:', result.error);
        }
    } catch (error) {
        console.error('[DASHBOARD_EXECUTIVO] Erro ao carregar KPIs:', error);
    }
}

/**
 * Load dashboard charts
 */
async function loadDashboardCharts() {
    try {
        console.log('[DASHBOARD_EXECUTIVO] Carregando gráficos...');
        
        const response = await fetch('/dashboard-executivo/api/charts');
        const result = await response.json();
        
        if (result.success) {
            createDashboardCharts(result.charts);
        } else {
            console.error('[DASHBOARD_EXECUTIVO] Erro ao carregar gráficos:', result.error);
        }
    } catch (error) {
        console.error('[DASHBOARD_EXECUTIVO] Erro ao carregar gráficos:', error);
    }
}

/**
 * Load recent operations
 */
async function loadRecentOperations() {
    try {
        console.log('[DASHBOARD_EXECUTIVO] Carregando operações recentes...');
        
        const response = await fetch('/dashboard-executivo/api/recent-operations');
        const result = await response.json();
        
        if (result.success) {
            updateRecentOperationsTable(result.operations);
        } else {
            console.error('[DASHBOARD_EXECUTIVO] Erro ao carregar operações:', result.error);
        }
    } catch (error) {
        console.error('[DASHBOARD_EXECUTIVO] Erro ao carregar operações:', error);
    }
}

/**
 * Update dashboard KPIs
 */
function updateDashboardKPIs(kpis) {
    console.log('[DASHBOARD_EXECUTIVO] Atualizando KPIs...', kpis);
    
    // Update KPI values
    updateKPIValue('kpi-total-processos', formatNumber(kpis.total_processos));
    updateKPIValue('kpi-total-despesas', formatCurrencyCompact(kpis.total_despesas));
    updateKPIValue('kpi-ticket-medio', formatCurrencyCompact(kpis.ticket_medio));
    updateKPIValue('kpi-em-transito', formatNumber(kpis.em_transito));
    updateKPIValue('kpi-total-agd-embarque', formatNumber(kpis.total_agd_embarque || 0));
    updateKPIValue('kpi-total-ag-chegada', formatNumber(kpis.total_ag_chegada || 0));
    updateKPIValue('kpi-chegando-mes', formatNumber(kpis.chegando_mes || 0));
    updateKPIValue('kpi-chegando-mes-custo', formatCurrencyCompact(kpis.chegando_mes_custo || 0));
    updateKPIValue('kpi-chegando-semana', formatNumber(kpis.chegando_semana || 0));
    updateKPIValue('kpi-chegando-semana-custo', formatCurrencyCompact(kpis.chegando_semana_custo || 0));
    updateKPIValue('kpi-transit-time', formatNumber(kpis.transit_time_medio, 1) + ' dias');
    updateKPIValue('kpi-proc-mes', formatNumber(kpis.processos_mes, 1));
    updateKPIValue('kpi-proc-semana', formatNumber(kpis.processos_semana, 1));
}

/**
 * Update KPI value safely
 */
function updateKPIValue(elementId, value) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = value;
    }
}

/**
 * Create dashboard charts
 */
function createDashboardCharts(charts) {
    console.log('[DASHBOARD_EXECUTIVO] Criando gráficos...', charts);
    
    // Create monthly chart
    if (charts.monthly) {
        createMonthlyChart(charts.monthly);
    }
    
    // Create status chart
    if (charts.status) {
        createStatusChart(charts.status);
    }
    
    // Create grouped modal chart
    if (charts.grouped_modal) {
        createGroupedModalChart(charts.grouped_modal);
    }
    
    // Create URF chart
    if (charts.urf) {
        createUrfChart(charts.urf);
    }
    
    // Create material chart
    if (charts.material) {
        createMaterialChart(charts.material);
    }
}

/**
 * Create monthly evolution chart
 */
function createMonthlyChart(data) {
    const ctx = document.getElementById('monthly-chart');
    if (!ctx) return;
    
    // Destroy existing chart
    if (dashboardCharts.monthly) {
        dashboardCharts.monthly.destroy();
    }
    
    dashboardCharts.monthly = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels || [],
            datasets: data.datasets || []
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Evolução Mensal de Processos e Custos'
                },
                legend: {
                    position: 'top'
                }
            },
            scales: {
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    grid: {
                        drawOnChartArea: false,
                    },
                }
            },
            interaction: {
                mode: 'index',
                intersect: false,
            }
        }
    });
}

/**
 * Create status distribution chart
 */
function createStatusChart(data) {
    const ctx = document.getElementById('status-chart');
    if (!ctx) return;
    
    // Destroy existing chart
    if (dashboardCharts.status) {
        dashboardCharts.status.destroy();
    }
    
    dashboardCharts.status = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: data.labels || [],
            datasets: [{
                data: data.data || [],
                backgroundColor: [
                    '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0',
                    '#9966FF', '#FF9F40', '#FF6384', '#C9CBCF',
                    '#4BC0C0', '#FF6384'
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right'
                }
            }
        }
    });
}

/**
 * Create grouped modal chart
 */
function createGroupedModalChart(data) {
    const ctx = document.getElementById('grouped-modal-chart');
    if (!ctx) return;
    
    // Destroy existing chart
    if (dashboardCharts.groupedModal) {
        dashboardCharts.groupedModal.destroy();
    }
    
    dashboardCharts.groupedModal = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.labels || [],
            datasets: data.datasets || []
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Processos e Custos por Modal de Transporte'
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

/**
 * Create URF chart
 */
function createUrfChart(data) {
    const ctx = document.getElementById('urf-chart');
    if (!ctx) return;
    
    // Destroy existing chart
    if (dashboardCharts.urf) {
        dashboardCharts.urf.destroy();
    }
    
    dashboardCharts.urf = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.labels || [],
            datasets: [{
                label: 'Quantidade de Processos',
                data: data.data || [],
                backgroundColor: '#36A2EB'
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    beginAtZero: true
                }
            }
        }
    });
}

/**
 * Create material chart
 */
function createMaterialChart(data) {
    const ctx = document.getElementById('material-chart');
    if (!ctx) return;
    
    // Destroy existing chart
    if (dashboardCharts.material) {
        dashboardCharts.material.destroy();
    }
    
    dashboardCharts.material = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.labels || [],
            datasets: [{
                label: 'Quantidade de Processos',
                data: data.data || [],
                backgroundColor: '#4BC0C0'
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    beginAtZero: true
                }
            }
        }
    });
}

/**
 * Set monthly chart period
 */
function setMonthlyChartPeriod(period) {
    monthlyChartPeriod = period;
    
    // Update active button
    document.querySelectorAll('.period-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.period === period) {
            btn.classList.add('active');
        }
    });
    
    // Reload monthly chart with new granularity
    loadMonthlyChart(period);
}

/**
 * Load monthly chart with specific granularity
 */
async function loadMonthlyChart(granularidade) {
    try {
        const response = await fetch(`/dashboard-executivo/api/monthly-chart?granularidade=${granularidade}`);
        const result = await response.json();
        
        if (result.success) {
            createMonthlyChart({
                labels: result.data.periods,
                datasets: [
                    {
                        label: 'Quantidade de Processos',
                        data: result.data.processes,
                        type: 'line',
                        borderColor: '#007bff',
                        backgroundColor: 'rgba(0, 123, 255, 0.1)',
                        yAxisID: 'y1'
                    },
                    {
                        label: 'Custo Total (R$)',
                        data: result.data.values,
                        type: 'bar',
                        backgroundColor: 'rgba(0, 123, 255, 0.6)',
                        yAxisID: 'y'
                    }
                ]
            });
        }
    } catch (error) {
        console.error('[DASHBOARD_EXECUTIVO] Erro ao carregar gráfico mensal:', error);
    }
}

/**
 * Update recent operations table
 */
function updateRecentOperationsTable(operations) {
    const tableBody = document.querySelector('#recent-operations-table tbody');
    if (!tableBody) return;
    
    tableBody.innerHTML = '';
    
    operations.forEach(operation => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${operation.ref_unique || '-'}</td>
            <td>${operation.importador || '-'}</td>
            <td>${operation.data_abertura || '-'}</td>
            <td>${operation.exportador_fornecedor || '-'}</td>
            <td>${operation.modal || '-'}</td>
            <td>${operation.status_processo || '-'}</td>
            <td>${formatCurrency(operation.custo_total || 0)}</td>
            <td>${operation.data_chegada || '-'}</td>
            <td>${operation.mercadoria || '-'}</td>
            <td>${operation.urf_entrada_normalizado || operation.urf_entrada || '-'}</td>
        `;
        tableBody.appendChild(row);
    });
}

/**
 * Refresh data
 */
async function refreshData() {
    try {
        showLoading(true);
        await loadInitialData();
        updateLastUpdate();
        showLoading(false);
        showSuccess('Dados atualizados com sucesso!');
    } catch (error) {
        console.error('[DASHBOARD_EXECUTIVO] Erro ao atualizar dados:', error);
        showError('Erro ao atualizar dados: ' + error.message);
        showLoading(false);
    }
}

/**
 * Export data
 */
function exportData() {
    if (!dashboardData) {
        showError('Nenhum dado disponível para exportar');
        return;
    }
    
    // Create CSV content
    const headers = Object.keys(dashboardData[0]);
    const csvContent = [
        headers.join(','),
        ...dashboardData.map(row => headers.map(header => `"${row[header] || ''}"`).join(','))
    ].join('\n');
    
    // Download file
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `dashboard_executivo_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

/**
 * Show/hide loading overlay
 */
function showLoading(show) {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.style.display = show ? 'flex' : 'none';
    }
}

/**
 * Update last update time
 */
function updateLastUpdate() {
    const element = document.getElementById('last-update');
    if (element) {
        element.textContent = `Última atualização: ${new Date().toLocaleString('pt-BR')}`;
    }
}

/**
 * Show success message
 */
function showSuccess(message) {
    // Simple alert for now - could be replaced with toast notification
    alert(message);
}

/**
 * Show error message
 */
function showError(message) {
    // Simple alert for now - could be replaced with toast notification
    alert('Erro: ' + message);
}

/**
 * Format number
 */
function formatNumber(value, decimals = 0) {
    if (!value || value === 0) return '0';
    return Number(value).toLocaleString('pt-BR', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    });
}

/**
 * Format currency
 */
function formatCurrency(value) {
    if (!value || value === 0) return 'R$ 0,00';
    return Number(value).toLocaleString('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    });
}

/**
 * Format currency compact
 */
function formatCurrencyCompact(value) {
    if (!value || value === 0) return 'R$ 0,00';
    const abs = Math.abs(value);
    if (abs >= 1e6) {
        return 'R$ ' + (value / 1e6).toFixed(1).replace('.0', '') + 'M';
    } else if (abs >= 1e3) {
        return 'R$ ' + (value / 1e3).toFixed(0) + 'k';
    } else {
        return formatCurrency(value);
    }
}
