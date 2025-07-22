/**
 * Dashboard Materiais - JavaScript Module
 * Handles all materials dashboard functionality
 */

// Global variables
let materiaisData = null;
let materiaisCharts = {};
let currentFilters = {};

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('[DASHBOARD_MATERIAIS] Inicializando...');
    initializeMateriais();
});

/**
 * Initialize the materials dashboard
 */
async function initializeMateriais() {
    try {
        showLoading(true);
        await loadInitialData();
        setupEventListeners();
        setupDefaultFilters();
        showLoading(false);
        updateLastUpdate();
    } catch (error) {
        console.error('[DASHBOARD_MATERIAIS] Erro na inicialização:', error);
        showError('Erro ao carregar dashboard: ' + error.message);
        showLoading(false);
    }
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // Filter modal
    const openFiltersBtn = document.getElementById('open-filters');
    const closeModalBtn = document.getElementById('close-modal');
    const filterModal = document.getElementById('filter-modal');
    const applyFiltersBtn = document.getElementById('apply-filters');
    const clearFiltersBtn = document.getElementById('clear-filters');
    
    if (openFiltersBtn) {
        openFiltersBtn.addEventListener('click', () => {
            filterModal.style.display = 'block';
        });
    }
    
    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', () => {
            filterModal.style.display = 'none';
        });
    }
    
    if (applyFiltersBtn) {
        applyFiltersBtn.addEventListener('click', applyFilters);
    }
    
    if (clearFiltersBtn) {
        clearFiltersBtn.addEventListener('click', clearFilters);
    }
    
    // Click outside modal to close
    if (filterModal) {
        filterModal.addEventListener('click', function(e) {
            if (e.target === filterModal) {
                filterModal.style.display = 'none';
            }
        });
    }
    
    // Quick period buttons
    document.querySelectorAll('.btn-quick').forEach(btn => {
        btn.addEventListener('click', function() {
            const days = parseInt(this.dataset.period);
            setQuickPeriod(days);
        });
    });
    
    // Refresh data button
    const refreshBtn = document.getElementById('refresh-data');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', refreshData);
    }
    
    // Export data button
    const exportBtn = document.getElementById('export-data');
    if (exportBtn) {
        exportBtn.addEventListener('click', exportData);
    }
}

/**
 * Setup default filters
 */
function setupDefaultFilters() {
    const hoje = new Date();
    const trintaDiasAtras = new Date(hoje.getTime() - (30 * 24 * 60 * 60 * 1000));
    
    const dataInicioInput = document.getElementById('data-inicio');
    const dataFimInput = document.getElementById('data-fim');
    
    if (dataInicioInput) {
        dataInicioInput.value = trintaDiasAtras.toISOString().split('T')[0];
    }
    if (dataFimInput) {
        dataFimInput.value = hoje.toISOString().split('T')[0];
    }
    
    // Set 30 days button as active
    document.querySelectorAll('.btn-quick').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.period === '30') {
            btn.classList.add('active');
        }
    });
}

/**
 * Load initial data
 */
async function loadInitialData() {
    try {
        console.log('[DASHBOARD_MATERIAIS] Carregando dados iniciais...');
        
        // Load filter options and data in parallel
        await Promise.all([
            loadFilterOptions(),
            loadMateriaisData()
        ]);
        
    } catch (error) {
        console.error('[DASHBOARD_MATERIAIS] Erro ao carregar dados:', error);
        throw error;
    }
}

/**
 * Load filter options
 */
async function loadFilterOptions() {
    try {
        const response = await fetch('/dashboard-materiais/api/filter-options');
        const result = await response.json();
        
        if (result.success) {
            populateFilterOptions(result.options);
        }
    } catch (error) {
        console.error('[DASHBOARD_MATERIAIS] Erro ao carregar opções de filtro:', error);
    }
}

/**
 * Populate filter select options
 */
function populateFilterOptions(options) {
    // Material filter
    const materialSelect = document.getElementById('material-filter');
    if (materialSelect && options.materiais) {
        options.materiais.forEach(material => {
            const option = document.createElement('option');
            option.value = material;
            option.textContent = material;
            materialSelect.appendChild(option);
        });
    }
    
    // Cliente filter
    const clienteSelect = document.getElementById('cliente-filter');
    if (clienteSelect && options.clientes) {
        options.clientes.forEach(cliente => {
            const option = document.createElement('option');
            option.value = cliente;
            option.textContent = cliente;
            clienteSelect.appendChild(option);
        });
    }
    
    // Canal filter
    const canalSelect = document.getElementById('canal-filter');
    if (canalSelect && options.canais) {
        options.canais.forEach(canal => {
            const option = document.createElement('option');
            option.value = canal;
            option.textContent = canal;
            canalSelect.appendChild(option);
        });
    }
}

/**
 * Load materials data with current filters
 */
async function loadMateriaisData() {
    try {
        const queryString = buildFilterQueryString();
        
        // Load all materials data in parallel
        await Promise.all([
            loadMateriaisKPIs(queryString),
            loadMateriaisCharts(queryString),
            loadMateriaisTable(queryString),
            loadDetalhamentoTable(queryString)
        ]);
        
    } catch (error) {
        console.error('[DASHBOARD_MATERIAIS] Erro ao carregar dados dos materiais:', error);
        throw error;
    }
}

/**
 * Build filter query string
 */
function buildFilterQueryString() {
    const params = new URLSearchParams();
    
    const dataInicio = document.getElementById('data-inicio')?.value;
    const dataFim = document.getElementById('data-fim')?.value;
    const material = document.getElementById('material-filter')?.value;
    const cliente = document.getElementById('cliente-filter')?.value;
    const modal = document.getElementById('modal-filter')?.value;
    const canal = document.getElementById('canal-filter')?.value;
    
    if (dataInicio) params.append('data_inicio', dataInicio);
    if (dataFim) params.append('data_fim', dataFim);
    if (material) params.append('material', material);
    if (cliente) params.append('cliente', cliente);
    if (modal) params.append('modal', modal);
    if (canal) params.append('canal', canal);
    
    return params.toString();
}

/**
 * Load materials KPIs
 */
async function loadMateriaisKPIs(queryString) {
    try {
        const response = await fetch(`/dashboard-materiais/api/kpis?${queryString}`);
        const result = await response.json();
        
        if (result.success) {
            updateMateriaisKPIs(result.kpis);
        } else {
            console.error('[DASHBOARD_MATERIAIS] Erro ao carregar KPIs:', result.error);
        }
    } catch (error) {
        console.error('[DASHBOARD_MATERIAIS] Erro ao carregar KPIs:', error);
    }
}

/**
 * Load materials charts
 */
async function loadMateriaisCharts(queryString) {
    try {
        // Load all charts in parallel
        await Promise.all([
            loadTopMateriaisChart(queryString),
            loadProcessosModalChart(queryString),
            loadModalDistributionChart(queryString),
            loadCanalDistributionChart(queryString),
            loadTransitTimeChart(queryString)
        ]);
        
    } catch (error) {
        console.error('[DASHBOARD_MATERIAIS] Erro ao carregar gráficos:', error);
    }
}

/**
 * Load top materials chart
 */
async function loadTopMateriaisChart(queryString) {
    try {
        const response = await fetch(`/dashboard-materiais/api/top-materiais?${queryString}`);
        const result = await response.json();
        
        if (result.success) {
            createTopMateriaisChart(result.data);
        }
    } catch (error) {
        console.error('[DASHBOARD_MATERIAIS] Erro ao carregar top materiais:', error);
    }
}

/**
 * Load processos por modal chart
 */
async function loadProcessosModalChart(queryString) {
    try {
        const response = await fetch(`/dashboard-materiais/api/processos-modal?${queryString}`);
        const result = await response.json();
        
        if (result.success) {
            createProcessosModalChart(result.data);
        }
    } catch (error) {
        console.error('[DASHBOARD_MATERIAIS] Erro ao carregar processos por modal:', error);
    }
}

/**
 * Load modal distribution chart
 */
async function loadModalDistributionChart(queryString) {
    try {
        const response = await fetch(`/dashboard-materiais/api/modal-distribution?${queryString}`);
        const result = await response.json();
        
        if (result.success) {
            createModalChart(result.data);
        }
    } catch (error) {
        console.error('[DASHBOARD_MATERIAIS] Erro ao carregar distribuição modal:', error);
    }
}

/**
 * Load canal distribution chart
 */
async function loadCanalDistributionChart(queryString) {
    try {
        const response = await fetch(`/dashboard-materiais/api/canal-distribution?${queryString}`);
        const result = await response.json();
        
        if (result.success) {
            createCanalChart(result.data);
        }
    } catch (error) {
        console.error('[DASHBOARD_MATERIAIS] Erro ao carregar distribuição por canal:', error);
    }
}

/**
 * Load transit time chart
 */
async function loadTransitTimeChart(queryString) {
    try {
        const response = await fetch(`/dashboard-materiais/api/transit-time-por-material?${queryString}`);
        const result = await response.json();
        
        if (result.success) {
            createTransitTimeChart(result.data);
        }
    } catch (error) {
        console.error('[DASHBOARD_MATERIAIS] Erro ao carregar transit time:', error);
    }
}

/**
 * Load materials table
 */
async function loadMateriaisTable(queryString) {
    try {
        const response = await fetch(`/dashboard-materiais/api/tabela-materiais?${queryString}`);
        const result = await response.json();
        
        if (result.success) {
            updateMateriaisTable(result.data);
        }
    } catch (error) {
        console.error('[DASHBOARD_MATERIAIS] Erro ao carregar tabela de materiais:', error);
    }
}

/**
 * Load detalhamento table
 */
async function loadDetalhamentoTable(queryString) {
    try {
        const response = await fetch(`/dashboard-materiais/api/detalhamento-processos?${queryString}`);
        const result = await response.json();
        
        if (result.success) {
            updateDetalhamentoTable(result.data);
        }
    } catch (error) {
        console.error('[DASHBOARD_MATERIAIS] Erro ao carregar detalhamento:', error);
    }
}

/**
 * Update materials KPIs
 */
function updateMateriaisKPIs(kpis) {
    console.log('[DASHBOARD_MATERIAIS] Atualizando KPIs...', kpis);
    
    updateKPIValue('mat-total-processos', formatNumber(kpis.total_processos));
    updateKPIValue('mat-total-materiais', formatNumber(kpis.total_materiais));
    updateKPIValue('mat-valor-total', formatCurrencyCompact(kpis.valor_total));
    updateKPIValue('mat-custo-total', formatCurrencyCompact(kpis.custo_total));
    updateKPIValue('mat-ticket-medio', formatCurrencyCompact(kpis.ticket_medio));
    updateKPIValue('mat-transit-time', formatNumber(kpis.transit_time, 1) + ' dias');
    updateKPIValue('mat-processos-mes', formatNumber(kpis.total_processos_mes));
    updateKPIValue('mat-custo-mes', formatCurrencyCompact(kpis.custo_total_mes));
    updateKPIValue('mat-processos-semana', formatNumber(kpis.total_processos_semana));
    updateKPIValue('mat-custo-semana', formatCurrencyCompact(kpis.custo_total_semana));
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
 * Create top materials chart com rótulos visíveis
 */
function createTopMateriaisChart(data) {
    const ctx = document.getElementById('top-materiais-chart');
    if (!ctx) return;
    
    if (materiaisCharts.topMateriais) {
        materiaisCharts.topMateriais.destroy();
    }
    
    materiaisCharts.topMateriais = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.labels || [],
            datasets: [{
                label: 'Quantidade de Processos',
                data: data.data || [],
                backgroundColor: '#198754', // Verde mais escuro para melhor contraste
                borderColor: '#146c43',
                borderWidth: 1
            }]
        },
        options: {
            indexAxis: 'y', // Gráfico horizontal
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                },
                datalabels: {
                    display: true,
                    anchor: 'end',
                    align: 'right',
                    color: '#ffffff',
                    font: {
                        weight: 'bold',
                        size: 12
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
                        display: true
                    }
                },
                y: {
                    grid: {
                        display: false
                    }
                }
            }
        },
        plugins: [ChartDataLabels] // Plugin para mostrar rótulos
    });
}

/**
 * Create processos por modal chart (substituindo evolução mensal)
 */
function createProcessosModalChart(data) {
    const ctx = document.getElementById('processos-modal-chart');
    if (!ctx) return;
    
    if (materiaisCharts.processosModal) {
        materiaisCharts.processosModal.destroy();
    }
    
    const colors = [
        '#007bff', // Azul
        '#28a745', // Verde
        '#ffc107', // Amarelo
        '#dc3545', // Vermelho
        '#6c757d'  // Cinza
    ];
    
    materiaisCharts.processosModal = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: data.labels || [],
            datasets: [{
                label: 'Processos',
                data: data.data || [],
                backgroundColor: colors.slice(0, (data.labels || []).length),
                borderWidth: 2,
                borderColor: '#ffffff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'right'
                },
                datalabels: {
                    display: true,
                    color: '#ffffff',
                    font: {
                        weight: 'bold',
                        size: 14
                    },
                    formatter: function(value, context) {
                        const total = context.dataset.data.reduce((a, b) => a + b, 0);
                        const percentage = ((value / total) * 100).toFixed(1);
                        return `${value}\n(${percentage}%)`;
                    }
                }
            }
        },
        plugins: [ChartDataLabels]
    });
}

/**
 * Create modal distribution chart (rosca com rótulos)
 */
function createModalChart(data) {
    const ctx = document.getElementById('modal-chart');
    if (!ctx) return;
    
    if (materiaisCharts.modal) {
        materiaisCharts.modal.destroy();
    }
    
    const colors = [
        '#007bff', // Azul
        '#28a745', // Verde
        '#ffc107', // Amarelo
        '#dc3545', // Vermelho
        '#6c757d'  // Cinza
    ];
    
    materiaisCharts.modal = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: data.labels || [],
            datasets: [{
                label: 'Processos por Modal',
                data: data.data || [],
                backgroundColor: colors.slice(0, (data.labels || []).length),
                borderWidth: 2,
                borderColor: '#ffffff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'right'
                },
                datalabels: {
                    display: true,
                    color: '#ffffff',
                    font: {
                        weight: 'bold',
                        size: 14
                    },
                    formatter: function(value, context) {
                        const total = context.dataset.data.reduce((a, b) => a + b, 0);
                        const percentage = ((value / total) * 100).toFixed(1);
                        return `${value}\n(${percentage}%)`;
                    }
                }
            }
        },
        plugins: [ChartDataLabels]
    });
}

/**
 * Create canal distribution chart (rosca com cores corretas)
 */
function createCanalChart(data) {
    const ctx = document.getElementById('canal-chart');
    if (!ctx) return;
    
    if (materiaisCharts.canal) {
        materiaisCharts.canal.destroy();
    }
    
    // Usar cores do backend se disponíveis, senão usar cores padrão
    const backgroundColors = data.backgroundColor || [
        '#28a745', // Verde
        '#dc3545', // Vermelho
        '#ffc107', // Amarelo
        '#007bff', // Azul
        '#6c757d'  // Cinza
    ];
    
    materiaisCharts.canal = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: data.labels || [],
            datasets: [{
                label: 'Processos por Canal',
                data: data.data || [],
                backgroundColor: backgroundColors,
                borderWidth: 2,
                borderColor: '#ffffff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'bottom'
                },
                datalabels: {
                    display: true,
                    color: '#ffffff',
                    font: {
                        weight: 'bold',
                        size: 14
                    },
                    formatter: function(value, context) {
                        const total = context.dataset.data.reduce((a, b) => a + b, 0);
                        const percentage = ((value / total) * 100).toFixed(1);
                        return `${value}\n(${percentage}%)`;
                    }
                }
            }
        },
        plugins: [ChartDataLabels]
    });
}

/**
 * Create transit time chart (barras horizontais com rótulos)
 */
function createTransitTimeChart(data) {
    const ctx = document.getElementById('transit-time-chart');
    if (!ctx) return;
    
    if (materiaisCharts.transitTime) {
        materiaisCharts.transitTime.destroy();
    }
    
    materiaisCharts.transitTime = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.labels || [],
            datasets: [{
                label: 'Transit Time Médio (dias)',
                data: data.data || [],
                backgroundColor: '#20c997',
                borderColor: '#17a085',
                borderWidth: 1
            }]
        },
        options: {
            indexAxis: 'y', // Barras horizontais
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                },
                datalabels: {
                    display: true,
                    anchor: 'end',
                    align: 'right',
                    color: '#ffffff',
                    font: {
                        weight: 'bold',
                        size: 12
                    },
                    formatter: function(value) {
                        return Math.round(value) + ' dias';
                    }
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    grid: {
                        display: true
                    }
                },
                y: {
                    grid: {
                        display: false
                    }
                }
            }
        },
        plugins: [ChartDataLabels]
    });
}

/**
 * Update materials table com indicativo de urgência
 */
function updateMateriaisTable(data) {
    const tableBody = document.querySelector('#principais-materiais-table tbody');
    if (!tableBody) return;
    
    tableBody.innerHTML = '';
    
    data.forEach(material => {
        const row = document.createElement('tr');
        
        // Preparar célula da próxima chegada com indicativo visual
        let proximaChegadaCell = '';
        if (material.proxima_chegada) {
            if (material.urgente) {
                proximaChegadaCell = `
                    <span class="urgente-badge">
                        <i class="mdi mdi-clock-alert"></i>
                        ${material.proxima_chegada}
                    </span>
                `;
            } else {
                proximaChegadaCell = material.proxima_chegada;
            }
        } else {
            proximaChegadaCell = '-';
        }
        
        row.innerHTML = `
            <td>${material.material || '-'}</td>
            <td>${formatNumber(material.qtd_processos || 0)}</td>
            <td>${formatCurrency(material.custo_total || 0)}</td>
            <td>${proximaChegadaCell}</td>
        `;
        
        // Adicionar classe de linha urgente se necessário
        if (material.urgente) {
            row.classList.add('urgente-row');
        }
        
        tableBody.appendChild(row);
    });
}

/**
 * Update detalhamento table
 */
function updateDetalhamentoTable(data) {
    const tableBody = document.querySelector('#detalhamento-table tbody');
    if (!tableBody) return;
    
    tableBody.innerHTML = '';
    
    // Store operations data globally for modal access
    window.currentOperations = data;
    console.log('[DASHBOARD_MATERIAIS] Operações armazenadas globalmente:', window.currentOperations.length);
    
    data.forEach((processo, index) => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>
                <button class="action-btn" onclick="openProcessModal(${index})" title="Ver detalhes">
                    <i class="mdi mdi-eye"></i>
                </button>
            </td>
            <td>${processo.data_abertura || '-'}</td>
            <td>${processo.ref_unique || '-'}</td>
            <td>${processo.importador || '-'}</td>
            <td>${processo.mercadoria || '-'}</td>
            <td>${processo.data_embarque || '-'}</td>
            <td>${processo.data_chegada || '-'}</td>
            <td>${processo.status_processo || '-'}</td>
            <td>${processo.canal || '-'}</td>
            <td>${formatCurrency(processo.custo_total || 0)}</td>
        `;
        tableBody.appendChild(row);
    });
}

/**
 * Set quick period filter
 */
function setQuickPeriod(days) {
    const end = new Date();
    const start = new Date();
    start.setDate(end.getDate() - (days - 1));
    
    const dataInicioInput = document.getElementById('data-inicio');
    const dataFimInput = document.getElementById('data-fim');
    
    if (dataInicioInput) {
        dataInicioInput.value = start.toISOString().slice(0, 10);
    }
    if (dataFimInput) {
        dataFimInput.value = end.toISOString().slice(0, 10);
    }
    
    // Update active button
    document.querySelectorAll('.btn-quick').forEach(btn => {
        btn.classList.remove('active');
        if (parseInt(btn.dataset.period) === days) {
            btn.classList.add('active');
        }
    });
}

/**
 * Apply filters
 */
async function applyFilters() {
    try {
        showLoading(true);
        
        // Close modal
        const filterModal = document.getElementById('filter-modal');
        if (filterModal) {
            filterModal.style.display = 'none';
        }
        
        // Reload data with new filters
        await loadMateriaisData();
        
        showLoading(false);
        showSuccess('Filtros aplicados com sucesso!');
    } catch (error) {
        console.error('[DASHBOARD_MATERIAIS] Erro ao aplicar filtros:', error);
        showError('Erro ao aplicar filtros: ' + error.message);
        showLoading(false);
    }
}

/**
 * Clear all filters
 */
function clearFilters() {
    // Clear all form inputs
    document.getElementById('data-inicio').value = '';
    document.getElementById('data-fim').value = '';
    document.getElementById('material-filter').value = '';
    document.getElementById('cliente-filter').value = '';
    document.getElementById('modal-filter').value = '';
    document.getElementById('canal-filter').value = '';
    
    // Remove active state from quick buttons
    document.querySelectorAll('.btn-quick').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Reset to default 30 days
    setupDefaultFilters();
}

/**
 * Refresh data
 */
async function refreshData() {
    try {
        showLoading(true);
        await loadMateriaisData();
        updateLastUpdate();
        showLoading(false);
        showSuccess('Dados atualizados com sucesso!');
    } catch (error) {
        console.error('[DASHBOARD_MATERIAIS] Erro ao atualizar dados:', error);
        showError('Erro ao atualizar dados: ' + error.message);
        showLoading(false);
    }
}

/**
 * Export data
 */
function exportData() {
    const tableBody = document.querySelector('#detalhamento-table tbody');
    if (!tableBody || tableBody.children.length === 0) {
        showError('Nenhum dado disponível para exportar');
        return;
    }
    
    // Get table data
    const headers = ['Data Abertura', 'Número Pedido', 'Cliente', 'Material', 'Data Embarque', 'Data Chegada', 'Status', 'Canal', 'Valor (R$)'];
    const rows = Array.from(tableBody.children).map(row => 
        Array.from(row.children).map(cell => cell.textContent)
    );
    
    // Create CSV content
    const csvContent = [
        headers.join(','),
        ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
    ].join('\n');
    
    // Download file
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `dashboard_materiais_${new Date().toISOString().split('T')[0]}.csv`);
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
