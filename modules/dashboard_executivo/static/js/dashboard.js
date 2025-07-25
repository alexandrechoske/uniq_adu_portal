/**
 * Dashboard Executivo - JavaScript Module
 * Handles all dashboard executive functionality
 * 
 * MELHORIAS IMPLEMENTADAS:
 * - Gráfico Evolução Mensal: rótulos, linhas suaves, layout 70%
 * - Gráfico Modal: eixos separados, rótulos, layout 30%
 * - Gráficos URF e Material: rótulos de dados
 * - Layout responsivo com CSS Grid
 */

// Global variables
let dashboardData = null;
let dashboardCharts = {};
let monthlyChartPeriod = 'mensal';
let recentOperationsTable = null;

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('[DASHBOARD_EXECUTIVO] Inicializando...');
    
    // Simple initialization - wait a bit for scripts to load
    setTimeout(() => {
        console.log('[DASHBOARD_EXECUTIVO] Chart.js disponível:', typeof Chart !== 'undefined');
        if (typeof Chart !== 'undefined') {
            // Register ChartDataLabels plugin if available
            if (typeof ChartDataLabels !== 'undefined') {
                try {
                    Chart.register(ChartDataLabels);
                    console.log('[DASHBOARD_EXECUTIVO] ChartDataLabels plugin registrado');
                } catch (error) {
                    console.warn('[DASHBOARD_EXECUTIVO] Erro ao registrar plugin:', error);
                }
            }
            initializeDashboard();
        } else {
            console.error('[DASHBOARD_EXECUTIVO] Chart.js não foi carregado');
        }
    }, 1000);
});

/**
 * Initialize the dashboard
 */
async function initializeDashboard() {
    try {
        showLoading(true);
        
        // Initialize enhanced table FIRST, before loading data
        initializeEnhancedTable();
        
        // Then load initial data
        await loadInitialData();
        
        // Setup event listeners and filters
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
 * Initialize enhanced table for recent operations
 */
function initializeEnhancedTable() {
    console.log('[DASHBOARD_EXECUTIVO] Inicializando Enhanced Table...');
    
    // Check if EnhancedDataTable is available
    if (typeof EnhancedDataTable === 'undefined') {
        console.error('[DASHBOARD_EXECUTIVO] EnhancedDataTable não está disponível');
        return;
    }
    
    // Create enhanced table instance
    recentOperationsTable = new EnhancedDataTable('recent-operations-table', {
        containerId: 'recent-operations-container',
        searchInputId: 'recent-operations-search',
        itemsPerPage: 15,
        searchFields: ['ref_unique', 'ref_importador', 'importador', 'exportador_fornecedor', 'modal', 'status_processo', 'status_macro_sistema', 'mercadoria', 'urf_entrada_normalizado'],
        sortField: 'data_chegada',
        sortOrder: 'desc'
    });

    // Override row rendering method
    recentOperationsTable.renderRow = function(operation, index) {
        // Check if global array exists
        if (!window.currentOperations) {
            console.error(`[RENDER_ROW_DEBUG] window.currentOperations não existe ainda!`);
            return '<td colspan="11">Carregando...</td>';
        }
        // Use ref_importador to find the correct index in the global array
        const globalIndex = window.currentOperations.findIndex(op => op.ref_importador === operation.ref_importador);
        console.log(`[RENDER_ROW] Processo: ${operation.ref_importador}, Index local: ${index}, Index global: ${globalIndex}`);
        console.log(`[RENDER_ROW_DEBUG] operation.status_macro_sistema:`, operation.status_macro_sistema);
        console.log(`[RENDER_ROW_DEBUG] operation.status:`, operation.status);
        console.log(`[RENDER_ROW_DEBUG] Todos os campos do objeto:`, Object.keys(operation));
        // Validation check
        if (globalIndex === -1) {
            console.warn(`[RENDER_ROW] Processo ${operation.ref_importador} não encontrado no array global!`);
            console.warn(`[RENDER_ROW] Primeiros 5 do array global:`, 
                window.currentOperations.slice(0, 5).map(op => op.ref_importador));
        }
        return `
            <td>
                <button class="table-action-btn" onclick="openProcessModal(${globalIndex})" title="Ver detalhes">
                    <i class="mdi mdi-eye-outline"></i>
                </button>
            </td>
            <td><strong>${operation.ref_importador || '-'}</strong></td>
            <td>${operation.importador || '-'}</td>
            <td>${formatDate(operation.data_abertura)}</td>
            <td>${operation.exportador_fornecedor || '-'}</td>
            <td>${getModalBadge(operation.modal)}</td>
            <td>${getStatusBadge(operation.status_macro_sistema || operation.status)}</td>
            <td><span class="currency-value">${formatCurrency(operation.custo_total || 0)}</span></td>
            <td>${formatDataChegada(operation.data_chegada)}</td>
            <td>${operation.mercadoria || '-'}</td>
            <td>${operation.urf_entrada_normalizado || operation.urf_entrada || '-'}</td>
        `;
    };

    console.log('[DASHBOARD_EXECUTIVO] Enhanced Table inicializada');
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

    // Modal event listeners
    setupModalEventListeners();
}

/**
 * Setup modal event listeners
 */
function setupModalEventListeners() {
    // Close modal button
    const modalClose = document.getElementById('modal-close');
    if (modalClose) {
        modalClose.addEventListener('click', closeProcessModal);
    }

    // Close modal when clicking outside
    const modalOverlay = document.getElementById('process-modal');
    if (modalOverlay) {
        modalOverlay.addEventListener('click', function(e) {
            if (e.target === modalOverlay) {
                closeProcessModal();
            }
        });
    }

    // Close modal with ESC key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeProcessModal();
        }
    });
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
    updateKPIValue('kpi-chegando-mes', formatNumber(kpis.chegando_mes));
    updateKPIValue('kpi-chegando-mes-custo', formatCurrencyCompact(kpis.chegando_mes_custo));
    updateKPIValue('kpi-chegando-semana', formatNumber(kpis.chegando_semana));
    updateKPIValue('kpi-chegando-semana-custo', formatCurrencyCompact(kpis.chegando_semana_custo));
    updateKPIValue('kpi-aguardando-embarque', formatNumber(kpis.aguardando_embarque || 0));
    updateKPIValue('kpi-aguardando-chegada', formatNumber(kpis.aguardando_chegada || 0));
    updateKPIValue('kpi-aguardando-liberacao', formatNumber(kpis.aguardando_liberacao || 0));
    updateKPIValue('kpi-agd-entrega', formatNumber(kpis.agd_entrega || 0));
    updateKPIValue('kpi-aguardando-fechamento', formatNumber(kpis.aguardando_fechamento || 0));
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
    console.log('[DASHBOARD_EXECUTIVO] Criando gráficos (versão simplificada)...', charts);
    
    // Create monthly chart
    if (charts.monthly) {
        console.log('[DASHBOARD_EXECUTIVO] Criando gráfico mensal...');
        createMonthlyChart(charts.monthly);
    }
    
    // Create status chart
    if (charts.status) {
        console.log('[DASHBOARD_EXECUTIVO] Criando gráfico de status...');
        createStatusChart(charts.status);
    }
    
    // Create grouped modal chart
    if (charts.grouped_modal) {
        console.log('[DASHBOARD_EXECUTIVO] Criando gráfico modal...');
        createGroupedModalChart(charts.grouped_modal);
    }
    
    // Create URF chart
    if (charts.urf) {
        console.log('[DASHBOARD_EXECUTIVO] Criando gráfico URF...');
        createUrfChart(charts.urf);
    }
    
    // Create material chart
    if (charts.material) {
        console.log('[DASHBOARD_EXECUTIVO] Criando gráfico material...');
        createMaterialChart(charts.material);
    }
}

/**
 * Create monthly evolution chart
 */
function createMonthlyChart(data) {
    const ctx = document.getElementById('monthly-chart');
    if (!ctx) {
        console.error('[DASHBOARD_EXECUTIVO] Canvas monthly-chart não encontrado');
        return;
    }

    if (typeof Chart === 'undefined') {
        console.error('[DASHBOARD_EXECUTIVO] Chart.js não disponível');
        return;
    }

    // Destroy existing chart
    if (dashboardCharts.monthly) {
        dashboardCharts.monthly.destroy();
    }

    try {
        // Adiciona área ao dataset de custo (área sob a linha)
        const datasets = (data.datasets || []).map((ds, idx) => {
            // O dataset de custo é o segundo (idx === 1)
            if (idx === 1) {
                return {
                    ...ds,
                    fill: {
                        target: 'origin',
                        above: 'rgba(40, 167, 69, 0.08)', // verde claro
                    },
                    pointBackgroundColor: ds.borderColor,
                };
            }
            // O dataset de processos é o primeiro (idx === 0)
            return {
                ...ds,
                fill: false,
                pointBackgroundColor: ds.borderColor,
            };
        });

        // Lógica inteligente para exibir rótulos de dados:
        // - Até 15 pontos: mostra todos
        // - 16-30 pontos: mostra a cada 2
        // - 31-60 pontos: mostra a cada 4
        // - 61-120 pontos: mostra a cada 8
        // - >120 pontos: mostra só o primeiro, último e a cada 15
        const totalPoints = (data.labels || []).length;
        let showLabelAtIndex = () => true;
        if (totalPoints > 120) {
            showLabelAtIndex = (i) => i === 0 || i === totalPoints - 1 || i % 15 === 0;
        } else if (totalPoints > 60) {
            showLabelAtIndex = (i) => i % 8 === 0 || i === totalPoints - 1;
        } else if (totalPoints > 30) {
            showLabelAtIndex = (i) => i % 4 === 0 || i === totalPoints - 1;
        } else if (totalPoints > 15) {
            showLabelAtIndex = (i) => i % 2 === 0 || i === totalPoints - 1;
        }

        dashboardCharts.monthly = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels || [],
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                    },
                    legend: {
                        position: 'top'
                    },
                    datalabels: {
                        display: function(context) {
                            // Só mostra rótulo se for um índice permitido
                            return showLabelAtIndex(context.dataIndex);
                        },
                        align: function(context) {
                            // Primeiro dataset (processos): label em cima
                            // Segundo dataset (custo): label embaixo
                            return context.datasetIndex === 0 ? 'top' : 'bottom';
                        },
                        anchor: function(context) {
                            return context.datasetIndex === 0 ? 'end' : 'start';
                        },
                        backgroundColor: function(context) {
                            // Fundo igual à cor da linha/barra
                            return context.dataset.borderColor || 'rgba(0,0,0,0.1)';
                        },
                        borderRadius: 4,
                        color: '#fff',
                        font: {
                            weight: 'bold',
                            size: 11
                        },
                        padding: {top: 2, bottom: 2, left: 6, right: 6},
                        formatter: function(value, context) {
                            // Formatação diferente para cada dataset
                            if (context.datasetIndex === 0) {
                                // Processos
                                return value;
                            } else {
                                // Custo
                                if (typeof value === 'number') {
                                    if (value >= 1e6) {
                                        return 'R$ ' + (value / 1e6).toFixed(1).replace('.0', '') + 'M';
                                    } else if (value >= 1e3) {
                                        return 'R$ ' + (value / 1e3).toFixed(0) + 'k';
                                    }
                                    return 'R$ ' + value.toLocaleString('pt-BR', {minimumFractionDigits: 0});
                                }
                                return value;
                            }
                        },
                        z: 10
                    }
                },
                scales: {
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: 'Custo Total (R$)'
                        },
                        grid: {
                            drawOnChartArea: false, // Remove grades do fundo
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {
                            display: true,
                            text: 'Quantidade de Processos'
                        },
                        grid: {
                            drawOnChartArea: false, // Remove grades do fundo
                        },
                    }
                },
                interaction: {
                    mode: 'index',
                    intersect: false,
                }
            },
            plugins: typeof ChartDataLabels !== 'undefined' ? [ChartDataLabels] : []
        });
        console.log('[DASHBOARD_EXECUTIVO] Gráfico mensal criado com sucesso');
    } catch (error) {
        console.error('[DASHBOARD_EXECUTIVO] Erro ao criar gráfico mensal:', error);
    }
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

    // Função para quebrar o label em múltiplas linhas (máx 14 chars por linha)
    const breakLabel = label => {
        if (!label) return '';
        const words = label.split(' ');
        let lines = [];
        let current = '';
        words.forEach(word => {
            if ((current + ' ' + word).trim().length > 14) {
                if (current) lines.push(current.trim());
                current = word;
            } else {
                current += ' ' + word;
            }
        });
        if (current) lines.push(current.trim());
        return lines;
    };

    dashboardCharts.status = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: (data.labels || []).map(breakLabel),
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
                    position: 'right',
                    labels: {
                        // Permite múltiplas linhas na legenda
                        usePointStyle: true,
                        textAlign: 'left',
                        font: {
                            size: 13
                        }
                    }
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
    if (!ctx) {
        console.error('[DASHBOARD_EXECUTIVO] Canvas grouped-modal-chart não encontrado');
        return;
    }

    if (typeof Chart === 'undefined') {
        console.error('[DASHBOARD_EXECUTIVO] Chart.js não disponível');
        return;
    }

    // Destroy existing chart
    if (dashboardCharts.groupedModal) {
        dashboardCharts.groupedModal.destroy();
    }

    try {
        // Inverta a ordem dos datasets para que o de processos venha antes do de custo
        // Supondo que o dataset de processos é o primeiro (index 0) e o de custo é o segundo (index 1)
        let datasets = data.datasets || [];
        if (datasets.length === 2) {
            // Troca a ordem dos datasets
            datasets = [datasets[1], datasets[0]];
        }

        dashboardCharts.groupedModal = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.labels || [],
                datasets: datasets.map(ds => ({
                    ...ds,
                    datalabels: {
                        display: true
                    }
                }))
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Processos e Custos por Modal de Transporte'
                    },
                    datalabels: {
                        display: true,
                        backgroundColor: function(context) {
                            return context.dataset.backgroundColor || 'rgba(0,0,0,0.1)';
                        },
                        borderRadius: 4,
                        color: '#fff',
                        font: {
                            weight: 'bold',
                            size: 11
                        },
                        padding: {top: 2, bottom: 2, left: 6, right: 6},
                        formatter: function(value, context) {
                            // Se o dataset for de custo, formata como moeda compacta
                            if (context.dataset.label && context.dataset.label.toLowerCase().includes('custo')) {
                                if (typeof value === 'number') {
                                    if (value >= 1e6) {
                                        return 'R$ ' + (value / 1e6).toFixed(1).replace('.0', '') + 'M';
                                    } else if (value >= 1e3) {
                                        return 'R$ ' + (value / 1e3).toFixed(0) + 'k';
                                    }
                                    return 'R$ ' + value.toLocaleString('pt-BR', {minimumFractionDigits: 0});
                                }
                                return value;
                            }
                            // Caso contrário, mostra número formatado
                            return Number(value).toLocaleString('pt-BR');
                        }
                    }
                },
                scales: {
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Quantidade de Processos'
                        },
                        grid: {
                            drawOnChartArea: false // Remove grades do fundo
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Custo Total (R$)'
                        },
                        grid: {
                            drawOnChartArea: false // Remove grades do fundo
                        }
                    }
                }
            },
            plugins: typeof ChartDataLabels !== 'undefined' ? [ChartDataLabels] : []
        });
        console.log('[DASHBOARD_EXECUTIVO] Gráfico modal criado com sucesso');
    } catch (error) {
        console.error('[DASHBOARD_EXECUTIVO] Erro ao criar gráfico modal:', error);
    }
}

/**
 * Create URF chart
 */
function createUrfChart(data) {
    const ctx = document.getElementById('urf-chart');
    if (!ctx) {
        console.error('[DASHBOARD_EXECUTIVO] Canvas urf-chart não encontrado');
        return;
    }

    if (typeof Chart === 'undefined') {
        console.error('[DASHBOARD_EXECUTIVO] Chart.js não disponível');
        return;
    }

    // Destroy existing chart
    if (dashboardCharts.urf) {
        dashboardCharts.urf.destroy();
    }

    try {
        // Quebra de linha nos labels longos (máx 12 chars por linha)
        const breakLabel = label => {
            if (!label) return '';
            // Quebra em espaços, tenta não cortar palavras
            const words = label.split(' ');
            let lines = [];
            let current = '';
            words.forEach(word => {
                if ((current + ' ' + word).trim().length > 14) {
                    if (current) lines.push(current.trim());
                    current = word;
                } else {
                    current += ' ' + word;
                }
            });
            if (current) lines.push(current.trim());
            return lines;
        };

        dashboardCharts.urf = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: (data.labels || []).map(breakLabel),
                datasets: [{
                    label: 'Quantidade de Processos',
                    data: data.data || [],
                    backgroundColor: '#36A2EB',
                    borderColor: '#36A2EB'
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    datalabels: {
                        display: true,
                        color: '#fff', // Branco para contraste
                        font: {
                            weight: 'bold',
                            size: 11
                        },
                        backgroundColor: '#36A2EB',
                        borderRadius: 4,
                        padding: {top: 2, bottom: 2, left: 6, right: 6},
                        formatter: function(value) {
                            return Number(value).toLocaleString('pt-BR');
                        }
                    }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        grid: {
                            drawOnChartArea: false // Remove grades do fundo
                        }
                    },
                    y: {
                        grid: {
                            drawOnChartArea: false // Remove grades do fundo
                        }
                    }
                }
            },
            plugins: typeof ChartDataLabels !== 'undefined' ? [ChartDataLabels] : []
        });
        console.log('[DASHBOARD_EXECUTIVO] Gráfico URF criado com sucesso');
    } catch (error) {
        console.error('[DASHBOARD_EXECUTIVO] Erro ao criar gráfico URF:', error);
    }
}

/**
 * Create material chart
 */
function createMaterialChart(data) {
    const ctx = document.getElementById('material-chart');
    if (!ctx) {
        console.error('[DASHBOARD_EXECUTIVO] Canvas material-chart não encontrado');
        return;
    }

    if (typeof Chart === 'undefined') {
        console.error('[DASHBOARD_EXECUTIVO] Chart.js não disponível');
        return;
    }

    // Destroy existing chart
    if (dashboardCharts.material) {
        dashboardCharts.material.destroy();
    }

    try {
        dashboardCharts.material = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.labels || [],
                datasets: [{
                    label: 'Quantidade de Processos',
                    data: data.data || [],
                    backgroundColor: '#4BC0C0',
                    borderColor: '#4BC0C0'
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        beginAtZero: true,
                        grid: {
                            drawOnChartArea: false // Remove grades do fundo
                        }
                    },
                    y: {
                        grid: {
                            drawOnChartArea: false // Remove grades do fundo
                        }
                    }
                }
            }
        });
        console.log('[DASHBOARD_EXECUTIVO] Gráfico material criado com sucesso');
    } catch (error) {
        console.error('[DASHBOARD_EXECUTIVO] Erro ao criar gráfico material:', error);
    }
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
                        yAxisID: 'y1',
                        tension: 0.4 // Smooth curves
                    },
                    {
                        label: 'Custo Total (R$)',
                        data: result.data.values,
                        type: 'line', // Changed from 'bar' to 'line'
                        borderColor: '#28a745',
                        backgroundColor: 'rgba(40, 167, 69, 0.1)',
                        yAxisID: 'y',
                        tension: 0.4 // Smooth curves
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
    console.log('[DASHBOARD_EXECUTIVO] Atualizando tabela com', operations.length, 'operações');
    
    if (!recentOperationsTable) {
        console.warn('[DASHBOARD_EXECUTIVO] Enhanced table não inicializada, tentando inicializar...');
        initializeEnhancedTable();
        
        // Se ainda não conseguiu inicializar, retorna
        if (!recentOperationsTable) {
            console.error('[DASHBOARD_EXECUTIVO] Falha ao inicializar enhanced table');
            return;
        }
    }

    // Sort operations by data_chegada (most recent first)
    const sortedOperations = [...operations].sort((a, b) => {
        const dateA = parseDate(a.data_chegada);
        const dateB = parseDate(b.data_chegada);
        
        if (!dateA && !dateB) return 0;
        if (!dateA) return 1;
        if (!dateB) return -1;
        
        return dateB - dateA; // Descending order (newest first)
    });

    // Store operations data globally for modal access FIRST
    window.currentOperations = sortedOperations;
    console.log('[DASHBOARD_EXECUTIVO] Operações armazenadas globalmente:', window.currentOperations.length);
    
    // Debug: verificar campos disponíveis no primeiro item
    if (sortedOperations.length > 0) {
        console.log('[DASHBOARD_EXECUTIVO] Campos disponíveis no primeiro item:', Object.keys(sortedOperations[0]));
        console.log('[DASHBOARD_EXECUTIVO] Primeiro item completo:', sortedOperations[0]);
    }
    
    // Then set data to enhanced table (this triggers render)
    recentOperationsTable.setData(sortedOperations);
    
    // Debug: mostrar primeiros 10 processos do array global com detalhes
    console.log('[DASHBOARD_EXECUTIVO] Primeiros 10 processos no array global:');
    sortedOperations.slice(0, 10).forEach((op, idx) => {
        console.log(`[DASHBOARD_EXECUTIVO] Index ${idx}: ${op.ref_unique} - ${op.importador} (${typeof op.ref_unique})`);
    });
    
    // Debug: verificar se os dados estão sendo passados corretamente para a tabela
    console.log('[DASHBOARD_EXECUTIVO] Verificando dados passados para a tabela...');
    if (recentOperationsTable.data && recentOperationsTable.data.length > 0) {
        console.log('[DASHBOARD_EXECUTIVO] Primeiros 5 da tabela:');
        recentOperationsTable.data.slice(0, 5).forEach((op, idx) => {
            console.log(`[DASHBOARD_EXECUTIVO] Tabela Index ${idx}: ${op.ref_unique} - ${op.importador} (${typeof op.ref_unique})`);
        });
    }
}

/**
 * Parse date string (Brazilian format DD/MM/YYYY)
 */
function parseDate(dateStr) {
    if (!dateStr) return null;
    
    const brazilianMatch = String(dateStr).match(/(\d{1,2})\/(\d{1,2})\/(\d{4})/);
    if (brazilianMatch) {
        const [, day, month, year] = brazilianMatch;
        return new Date(year, month - 1, day);
    }
    
    const date = new Date(dateStr);
    return isNaN(date.getTime()) ? null : date;
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

/**
 * Open process details modal
 */
function openProcessModal(operationIndex) {
    console.log('[DASHBOARD_EXECUTIVO] Abrindo modal para processo:', operationIndex);
    
    // Validation checks
    if (!window.currentOperations) {
        console.error('[DASHBOARD_EXECUTIVO] Array global de operações não encontrado');
        return;
    }
    
    if (operationIndex === -1) {
        console.error('[DASHBOARD_EXECUTIVO] Índice inválido (-1) - processo não encontrado no array global');
        return;
    }
    
    if (!window.currentOperations[operationIndex]) {
        console.error('[DASHBOARD_EXECUTIVO] Operação não encontrada no índice:', operationIndex);
        console.error('[DASHBOARD_EXECUTIVO] Array global tem:', window.currentOperations.length, 'elementos');
        console.error('[DASHBOARD_EXECUTIVO] Índices válidos: 0 a', window.currentOperations.length - 1);
        return;
    }
    
    const operation = window.currentOperations[operationIndex];
    console.log('[DASHBOARD_EXECUTIVO] Dados da operação completos:', operation);
    console.log('[DASHBOARD_EXECUTIVO] ref_unique do processo:', operation.ref_unique);
    
    // Debug: verificar se o índice está correto
    console.log(`[DASHBOARD_EXECUTIVO] Operação no índice ${operationIndex}:`, operation.ref_unique, '-', operation.importador);
    
    // Debug específico dos campos problemáticos
    console.log('[MODAL_DEBUG] ref_importador:', operation.ref_importador);
    console.log('[MODAL_DEBUG] cnpj_importador:', operation.cnpj_importador);
    console.log('[MODAL_DEBUG] status_macro:', operation.status_macro);
    console.log('[MODAL_DEBUG] status_macro_sistema:', operation.status_macro_sistema);
    console.log('[MODAL_DEBUG] data_embarque:', operation.data_embarque);
    console.log('[MODAL_DEBUG] peso_bruto:', operation.peso_bruto);
    console.log('[MODAL_DEBUG] urf_despacho:', operation.urf_despacho);
    console.log('[MODAL_DEBUG] urf_despacho_normalizado:', operation.urf_despacho_normalizado);
    
    // Update modal title
    const modalTitle = document.getElementById('modal-title');
    if (modalTitle) {
        modalTitle.textContent = `Detalhes do Processo ${operation.ref_unique || 'N/A'}`;
        console.log('[DASHBOARD_EXECUTIVO] Título do modal atualizado para:', operation.ref_unique);
    }
    
    // Update timeline - extract numeric value from status_macro like "5 - AG REGISTRO"
    const statusMacroNumber = extractStatusMacroNumber(operation.status_macro);
    console.log('[MODAL_DEBUG] Status macro extraído:', statusMacroNumber);
    updateProcessTimeline(statusMacroNumber);
    
    // Update general information
    updateElementValue('detail-ref-unique', operation.ref_unique);
    updateElementValue('detail-ref-importador', operation.ref_importador);
    updateElementValue('detail-data-abertura', operation.data_abertura);
    updateElementValue('detail-importador', operation.importador);
    updateElementValue('detail-cnpj', formatCNPJ(operation.cnpj_importador));
    // Processar status_macro_sistema para exibição
    let statusToDisplay = operation.status_macro_sistema || operation.status_processo || operation.status_macro;
    if (statusToDisplay && typeof statusToDisplay === 'string' && statusToDisplay.includes(' - ')) {
        statusToDisplay = statusToDisplay.split(' - ')[1].trim();
    }
    console.log('[MODAL_DEBUG] Status processado para exibição:', statusToDisplay);
    
    updateElementValue('detail-status', statusToDisplay);
    
    // Update cargo and transport details
    updateElementValue('detail-modal', operation.modal);
    updateElementValue('detail-container', operation.container);
    updateElementValue('detail-data-embarque', operation.data_embarque);
    updateElementValue('detail-data-chegada', operation.data_chegada);
    updateElementValue('detail-transit-time', operation.transit_time_real ? operation.transit_time_real + ' dias' : '-');
    updateElementValue('detail-peso-bruto', operation.peso_bruto ? formatNumber(operation.peso_bruto) + ' Kg' : '-');
    
    // Update customs information
    updateElementValue('detail-numero-di', operation.numero_di);
    updateElementValue('detail-data-registro', operation.data_registro);
    updateElementValue('detail-canal', operation.canal, true);
    updateElementValue('detail-data-desembaraco', operation.data_desembaraco);
    updateElementValue('detail-urf-entrada', operation.urf_entrada_normalizado || operation.urf_entrada);
    updateElementValue('detail-urf-despacho', operation.urf_despacho_normalizado || operation.urf_despacho);
    
    // Update financial summary
    updateElementValue('detail-valor-cif', formatCurrency(operation.valor_cif_real || 0));
    updateElementValue('detail-frete-inter', formatCurrency(operation.custo_frete_inter || 0));
    updateElementValue('detail-armazenagem', formatCurrency(operation.custo_armazenagem || 0));
    updateElementValue('detail-honorarios', formatCurrency(operation.custo_honorarios || 0));
    
    // Calculate other expenses
    const otherExpenses = calculateOtherExpenses(operation);
    updateElementValue('detail-outras-despesas', formatCurrency(otherExpenses));
    updateElementValue('detail-custo-total', formatCurrency(operation.custo_total || 0));
    
    // Update documents (placeholder for now)
    updateDocumentsList(operation);
    
    // Show modal
    const modal = document.getElementById('process-modal');
    if (modal) {
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
}

/**
 * Close process details modal
 */
function closeProcessModal() {
    console.log('[DASHBOARD_EXECUTIVO] Fechando modal');
    
    const modal = document.getElementById('process-modal');
    if (modal) {
        modal.classList.remove('active');
        document.body.style.overflow = '';
    }
}

/**
 * Extract numeric value from status_macro like "5 - AG REGISTRO"
 */
function extractStatusMacroNumber(statusMacro) {
    if (!statusMacro) return 1;
    
    // Extract the first number from strings like "5 - AG REGISTRO"
    const match = statusMacro.toString().match(/^(\d+)/);
    return match ? parseInt(match[1]) : 1;
}

/**
 * Format CNPJ for display
 */
function formatCNPJ(cnpj) {
    if (!cnpj) return '-';
    
    // Remove non-digits
    const cleanCNPJ = cnpj.replace(/\D/g, '');
    
    // Format as XX.XXX.XXX/XXXX-XX
    if (cleanCNPJ.length === 14) {
        return cleanCNPJ.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, '$1.$2.$3/$4-$5');
    }
    
    return cnpj;
}

/**
 * Update process timeline based on status_macro
 */
function updateProcessTimeline(statusMacro) {
    console.log('[TIMELINE_DEBUG] Atualizando timeline com status:', statusMacro);
    
    const timelineSteps = document.querySelectorAll('.timeline-step');
    console.log('[TIMELINE_DEBUG] Steps encontrados:', timelineSteps.length);
    
    timelineSteps.forEach((step, index) => {
        const stepNumber = index + 1;
        step.classList.remove('completed', 'active');
        
        console.log(`[TIMELINE_DEBUG] Step ${stepNumber}: status=${statusMacro}`);
        
        if (stepNumber < statusMacro) {
            step.classList.add('completed');
            console.log(`[TIMELINE_DEBUG] Step ${stepNumber} marcado como completed`);
        } else if (stepNumber === statusMacro) {
            step.classList.add('active');
            console.log(`[TIMELINE_DEBUG] Step ${stepNumber} marcado como active`);
        }
    });
}

/**
 * Update element value safely
 */
function updateElementValue(elementId, value, useCanalBadge = false) {
    const element = document.getElementById(elementId);
    if (element) {
        if (useCanalBadge && elementId === 'detail-canal') {
            element.innerHTML = getCanalBadge(value);
            console.log(`[MODAL_DEBUG] Elemento ${elementId} atualizado com badge: "${value}"`);
        } else {
            const displayValue = value || '-';
            element.textContent = displayValue;
            console.log(`[MODAL_DEBUG] Elemento ${elementId} atualizado com: "${displayValue}"`);
        }
    } else {
        console.warn(`[MODAL_DEBUG] Elemento ${elementId} não encontrado no DOM`);
    }
}

/**
 * Calculate other expenses
 */
function calculateOtherExpenses(operation) {
    const expenseFields = [
        'custo_ii', 'custo_ipi', 'custo_pis', 'custo_cofins', 'custo_icms',
        'custo_afrmm', 'custo_seguro', 'custo_adicional_frete', 'custo_taxa_siscomex',
        'custo_licenca_importacao', 'custo_taxa_utilizacao_siscomex', 'custo_multa',
        'custo_juros_mora', 'custo_outros'
    ];
    
    let total = 0;
    expenseFields.forEach(field => {
        const value = operation[field];
        if (value && !isNaN(value)) {
            total += Number(value);
        }
    });
    
    return total;
}

/**
 * Update documents list using DocumentManager
 */
function updateDocumentsList(operation) {
    const documentsList = document.getElementById('documents-list');
    if (!documentsList) return;
    
    // Verificar se temos o ref_unique da operação
    const refUnique = operation?.ref_unique;
    console.log('[DOCUMENT_MANAGER] ref_unique recebido:', refUnique);
    if (!refUnique) {
        documentsList.innerHTML = '<p class="no-documents">Referência do processo não encontrada</p>';
        return;
    }
    
    // Verificar se DocumentManager está disponível
    if (typeof DocumentManager === 'undefined') {
        console.error('DocumentManager não carregado');
        documentsList.innerHTML = '<p class="no-documents">Sistema de documentos não disponível</p>';
        return;
    }
    
    try {
        // Inicializar DocumentManager para este processo e armazenar na variável global
        // O DocumentManager já chama loadDocuments() automaticamente no init()
        window.documentManager = new DocumentManager(refUnique);
        console.log('[DASHBOARD_EXECUTIVO] DocumentManager inicializado e armazenado em window.documentManager');
        
    } catch (error) {
        console.error('Erro ao inicializar DocumentManager:', error);
        documentsList.innerHTML = '<p class="no-documents">Erro ao carregar sistema de documentos</p>';
    }
}

// Utility Functions for Enhanced Table
function formatDate(dateString) {
    if (!dateString) return '-';
    try {
        // Handle Brazilian date format (DD/MM/YYYY)
        if (dateString.includes('/')) {
            const [day, month, year] = dateString.split('/');
            const date = new Date(year, month - 1, day);
            return date.toLocaleDateString('pt-BR');
        }
        // Handle ISO date format
        const date = new Date(dateString);
        return date.toLocaleDateString('pt-BR');
    } catch (error) {
        console.warn('Error formatting date:', dateString, error);
        return dateString;
    }
}

function getStatusBadge(status) {
    if (!status) return '<span class="badge badge-secondary">-</span>';

    console.log('[STATUS_BADGE_DEBUG] Status recebido:', status);

    // Se o status tem formato "2 - AG EMBARQUE", extrair apenas a parte após o traço
    let displayStatus = status;
    if (typeof status === 'string' && status.includes(' - ')) {
        displayStatus = status.split(' - ')[1].trim();
        console.log('[STATUS_BADGE_DEBUG] Status extraído:', displayStatus);
    }

    // Mapeamento para status_macro_sistema
    const statusMap = {
        'AG. EMBARQUE': 'info',
        'AG EMBARQUE': 'info',
        'AG. FECHAMENTO': 'info',
        'AG. ENTREGA DA DHL NO IMPORTADOR': 'primary',
        'AG MAPA': 'info',
        'ABERTURA': 'secondary',
        'NUMERÁRIO ENVIADO': 'warning',
        'DECLARAÇÃO DESEMBARAÇADA': 'success',
        'AG CARREGAMENTO': 'info',
        'AG CHEGADA': 'primary',
        'AG. CARREGAMENTO': 'info',
        'AG. REGISTRO': 'primary',
        'DI REGISTRADA': 'warning',
        'DI DESEMBARAÇADA': 'success'
    };

    // Primeiro tenta match exato, depois normalizado
    let badgeClass = statusMap[displayStatus];
    if (!badgeClass) {
        const normalize = s => s?.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toUpperCase();
        badgeClass = statusMap[normalize(displayStatus)] || 'secondary';
    }

    console.log('[STATUS_BADGE_DEBUG] Badge class:', badgeClass, 'para status:', displayStatus);

    return `<span class="badge badge-${badgeClass}">${displayStatus}</span>`;
}

function getCanalBadge(canal) {
    if (!canal) return '<span class="badge badge-secondary">-</span>';
    
    // Normalizar o texto para maiúsculo
    const canalUpper = String(canal).toUpperCase().trim();
    
    // Mapeamento de cores para os canais
    const canalMap = {
        'VERDE': 'success',
        'AMARELO': 'warning', 
        'VERMELHO': 'danger'
    };
    
    const badgeClass = canalMap[canalUpper] || 'secondary';
    
    return `<span class="badge badge-${badgeClass}">${canalUpper}</span>`;
}

function getModalBadge(modal) {
    if (!modal) return '<span class="badge badge-secondary">-</span>';
    
    // Normalizar o texto para maiúsculo
    const modalUpper = String(modal).toUpperCase().trim();
    
    // Mapeamento de ícones e cores para os modais
    if (modalUpper.includes('MARÍTIMA') || modalUpper.includes('MARITIMA')) {
        return `<span class="badge badge-info"><i class="mdi mdi-ferry"></i> ${modalUpper}</span>`;
    } else if (modalUpper.includes('AÉREA') || modalUpper.includes('AEREA')) {
        return `<span class="badge badge-primary"><i class="mdi mdi-airplane"></i> ${modalUpper}</span>`;
    } else {
        return `<span class="badge badge-secondary">${modalUpper}</span>`;
    }
}

function formatDataChegada(dateString) {
    if (!dateString) return '-';
    
    const hoje = new Date();
    const chegadaDate = parseDate(dateString);
    
    if (!chegadaDate) return formatDate(dateString);
    
    // Calcular diferença em dias
    const diffMs = chegadaDate - hoje;
    const diffDias = Math.ceil(diffMs / (1000 * 60 * 60 * 24));
    
    // Se chegada for futuro e dentro de 5 dias, mostrar indicador de urgência
    const isUrgente = diffDias > 0 && diffDias <= 5;
    
    if (isUrgente) {
        return `<span class="chegada-proxima">
            <img src="https://cdn-icons-png.flaticon.com/512/6198/6198499.png" 
                 alt="Chegada próxima" class="chegada-proxima-icon">
            ${formatDate(dateString)}
        </span>`;
    }
    
    return formatDate(dateString);
}
