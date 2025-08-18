/**
 * Analytics do Agente - JavaScript Module
 * Handles all agent analytics functionality
 */

// Global variables
let agenteAnalyticsData = null;
let agenteCharts = {};
let currentFilters = {};
let currentPage = 1;
let pageSize = 20;
let isLoading = false;

// Colors for charts
const AGENTE_COLORS = {
    normal: '#007bff',
    arquivo: '#f59e0b',
    success: '#10b981',
    error: '#ef4444'
};

// Cache system
let agenteCache = {
    kpis: null,
    chart: null,
    companies: null,
    users: null,
    interactions: null,
    lastUpdate: null,
    cacheTimeout: 5 * 60 * 1000, // 5 minutes
    
    isValid: function() {
        return this.lastUpdate && (Date.now() - this.lastUpdate) < this.cacheTimeout;
    },
    
    invalidate: function() {
        this.kpis = null;
        this.chart = null;
        this.companies = null;
        this.users = null;
        this.interactions = null;
        this.lastUpdate = null;
        console.log('[AGENTE_ANALYTICS] Cache invalidated');
    },
    
    set: function(type, data) {
        this[type] = data;
        this.lastUpdate = Date.now();
        console.log(`[AGENTE_ANALYTICS] Cache updated for ${type}`);
    },
    
    get: function(type) {
        if (this.isValid() && this[type]) {
            console.log(`[AGENTE_ANALYTICS] Using cache for ${type}`);
            return this[type];
        }
        return null;
    }
};

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('[AGENTE_ANALYTICS] Initializing...');
    
    // Wait for Chart.js to load - increased timeout and better check
    let attempts = 0;
    const maxAttempts = 20;
    
    function checkChartJs() {
        attempts++;
        if (typeof Chart !== 'undefined') {
            console.log('[AGENTE_ANALYTICS] Chart.js loaded successfully');
            initializeAgenteAnalytics();
        } else if (attempts < maxAttempts) {
            console.log(`[AGENTE_ANALYTICS] Waiting for Chart.js... (attempt ${attempts})`);
            setTimeout(checkChartJs, 250);
        } else {
            console.error('[AGENTE_ANALYTICS] Chart.js not loaded after 5 seconds');
            // Initialize anyway without charts
            initializeAgenteAnalytics();
        }
    }
    
    checkChartJs();
});

/**
 * Initialize the analytics dashboard
 */
function initializeAgenteAnalytics() {
    console.log('[AGENTE_ANALYTICS] Starting initialization...');
    
    // Disable any global auto-refresh
    if (window.globalRefreshSystem) {
        window.globalRefreshSystem.disable();
        console.log('[AGENTE_ANALYTICS] Disabled global refresh system');
    }
    
    // Set up event listeners
    setupEventListeners();
    
    // Load initial data
    loadAnalyticsData();
    
    // Note: Auto-refresh removido - apenas refresh manual via botão
}

/**
 * Set up event listeners
 */
function setupEventListeners() {
    // Refresh button
    const refreshBtn = document.getElementById('refresh-data');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            agenteCache.invalidate();
            loadAnalyticsData();
        });
    }
    
    // Filters button
    const filtersBtn = document.getElementById('open-filters');
    if (filtersBtn) {
        filtersBtn.addEventListener('click', () => {
            openFiltersModal();
        });
    }
    
    // Reset filters button
    const resetFiltersBtn = document.getElementById('reset-filters');
    if (resetFiltersBtn) {
        resetFiltersBtn.addEventListener('click', () => {
            resetFilters();
        });
    }
    
    // Modal close buttons
    const closeModalBtns = document.querySelectorAll('.modal-close');
    closeModalBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const modal = e.target.closest('.modal');
            if (modal) {
                modal.style.display = 'none';
            }
        });
    });
    
    // Apply filters button
    const applyFiltersBtn = document.getElementById('apply-filters');
    if (applyFiltersBtn) {
        applyFiltersBtn.addEventListener('click', () => {
            applyFilters();
        });
    }
    
    // Clear filters button
    const clearFiltersBtn = document.getElementById('clear-filters');
    if (clearFiltersBtn) {
        clearFiltersBtn.addEventListener('click', () => {
            clearFilters();
        });
    }
    
    // Load more interactions button
    const loadMoreBtn = document.getElementById('load-more-interactions');
    if (loadMoreBtn) {
        loadMoreBtn.addEventListener('click', () => {
            loadMoreInteractions();
        });
    }
    
    // Click outside modal to close
    window.addEventListener('click', (e) => {
        if (e.target.classList.contains('modal')) {
            e.target.style.display = 'none';
        }
    });
}

/**
 * Load analytics data
 */
async function loadAnalyticsData() {
    if (isLoading) return;
    
    isLoading = true;
    showAllLoading();
    
    try {
        // Load KPIs
        await loadKPIs();
        
        // Load chart data
        await loadInteractionsChart();
        
        // Load interaction types chart (rosca)
        await loadInteractionTypesChart();
        
        // Load top users chart
        await loadTopUsersChart();
        
        // Load users data (for table)
        await loadUsersData();
        
        // Load company summary
        await loadCompanySummary();
        
        // Load users data
        await loadUsersData();
        
        // Load interactions table
        await loadInteractionsTable();
        
        console.log('[AGENTE_ANALYTICS] All data loaded successfully');
        
    } catch (error) {
        console.error('[AGENTE_ANALYTICS] Error loading data:', error);
        showError('Erro ao carregar dados do analytics');
    } finally {
        isLoading = false;
        hideAllLoading();
    }
}

/**
 * Load KPIs
 */
async function loadKPIs() {
    try {
        // Check cache first
        let cachedKpis = agenteCache.get('kpis');
        if (cachedKpis) {
            updateKPIs(cachedKpis);
            return;
        }
        
        const response = await fetch('/analytics/api/agente/kpis?' + getFilterParams());
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            agenteCache.set('kpis', data.data);
            updateKPIs(data.data);
        } else {
            throw new Error(data.error || 'Erro ao carregar KPIs');
        }
        
    } catch (error) {
        console.error('[AGENTE_ANALYTICS] Error loading KPIs:', error);
        updateKPIs({
            total_interactions: 0,
            unique_users: 0,
            companies_served: 0,
            success_rate: 0,
            avg_response_time: '0s',
            normal_responses: 0,
            file_requests: 0
        });
    }
}

/**
 * Update KPI display
 */
function updateKPIs(kpis) {
    const elements = {
        'total-interactions': kpis.total_interactions || 0,
        'unique-users': kpis.unique_users || 0,
        'companies-served': kpis.companies_served || 0,
        'success-rate': `${kpis.success_rate || 0}%`,
        'avg-response-time': kpis.avg_response_time || '0s'
    };
    
    Object.entries(elements).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
            console.log(`[AGENTE_ANALYTICS] Updated KPI ${id}:`, value);
        }
    });
}

/**
 * Load interactions chart
 */
async function loadInteractionsChart() {
    try {
        // Check cache first
        let cachedChart = agenteCache.get('chart');
        if (cachedChart) {
            createInteractionsChart(cachedChart);
            return;
        }
        
        const response = await fetch('/analytics/api/agente/chart?' + getFilterParams());
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            agenteCache.set('chart', data.data);
            createInteractionsChart(data.data);
        } else {
            throw new Error(data.error || 'Erro ao carregar gráfico');
        }
        
    } catch (error) {
        console.error('[AGENTE_ANALYTICS] Error loading chart:', error);
        createInteractionsChart({
            labels: [],
            normal_responses: [],
            file_requests: []
        });
    }
}

/**
 * Create interactions chart
 */
function createInteractionsChart(chartData) {
    const ctx = document.getElementById('daily-interactions-chart');
    if (!ctx) {
        console.error('[AGENTE_ANALYTICS] Chart canvas not found');
        return;
    }
    
    console.log('[AGENTE_ANALYTICS] Creating chart with data:', chartData);
    
    // Check if Chart.js is available
    if (typeof Chart === 'undefined' && typeof window.Chart === 'undefined') {
        console.error('[AGENTE_ANALYTICS] Chart.js not available');
        showChartError(ctx.parentElement, 'Chart.js não foi carregado');
        return;
    }
    
    // Use the correct Chart reference
    const ChartConstructor = typeof Chart !== 'undefined' ? Chart : window.Chart;
    
    // Destroy existing chart
    if (agenteCharts.interactions) {
        agenteCharts.interactions.destroy();
    }
    
    try {
        // Hide loading
        const loadingEl = document.getElementById('interactions-loading');
        if (loadingEl) loadingEl.classList.add('hidden');
        
        // Prepare chart data with better structure
        const processedData = {
            labels: chartData.labels || [],
            datasets: [
                {
                    label: 'Total de Interações',
                    data: chartData.total_interactions || 
                          // Se não tem total_interactions, somar normal_responses + file_requests
                          (chartData.normal_responses && chartData.file_requests ? 
                              chartData.normal_responses.map((val, i) => val + (chartData.file_requests[i] || 0)) :
                              chartData.data || []),
                    borderColor: '#007bff',
                    backgroundColor: 'rgba(0, 123, 255, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    pointBackgroundColor: '#007bff',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2
                }
            ]
        };
        
        agenteCharts.interactions = new ChartConstructor(ctx, {
            type: 'line',
            data: processedData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                plugins: {
                    legend: {
                        display: false // Hide default legend, we have custom
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleColor: '#ffffff',
                        bodyColor: '#ffffff',
                        borderColor: '#007bff',
                        borderWidth: 1,
                        cornerRadius: 6,
                        displayColors: false,
                        callbacks: {
                            title: function(context) {
                                return context[0].label;
                            },
                            label: function(context) {
                                return `Interações: ${context.parsed.y}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        display: true,
                        grid: {
                            display: false
                        },
                        ticks: {
                            color: '#64748b',
                            font: {
                                size: 12
                            }
                        }
                    },
                    y: {
                        display: true,
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(148, 163, 184, 0.1)'
                        },
                        ticks: {
                            color: '#64748b',
                            font: {
                                size: 12
                            },
                            callback: function(value) {
                                return Number.isInteger(value) ? value : '';
                            }
                        }
                    }
                }
            }
        });
        
        console.log('[AGENTE_ANALYTICS] Chart created successfully');
        
    } catch (error) {
        console.error('[AGENTE_ANALYTICS] Error creating chart:', error);
        showChartError(ctx.parentElement, 'Erro ao criar gráfico: ' + error.message);
    }
}

/**
 * Show chart error
 */
function showChartError(container, message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'chart-error';
    errorDiv.innerHTML = `
        <i class="mdi mdi-chart-line-variant"></i>
        <div>${message}</div>
        <small>Verifique os logs do console para mais detalhes</small>
    `;
    
    // Replace canvas with error message
    const canvas = container.querySelector('canvas');
    if (canvas) {
        container.replaceChild(errorDiv, canvas);
    }
}

/**
 * Create response types chart
 */
function createResponseTypesChart(data) {
    const ctx = document.getElementById('response-types-chart');
    if (!ctx) return;
    
    const ChartConstructor = typeof Chart !== 'undefined' ? Chart : window.Chart;
    
    if (agenteCharts.responseTypes) {
        agenteCharts.responseTypes.destroy();
        delete agenteCharts.responseTypes;
    }
    
    try {
        agenteCharts.responseTypes = new ChartConstructor(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Normal', 'Arquivo', 'Erro'],
                datasets: [{
                    data: [
                        data.normal || 0,
                        data.arquivo || 0,
                        data.error || 0
                    ],
                    backgroundColor: [
                        '#10b981',
                        '#f59e0b',
                        '#ef4444'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    } catch (error) {
        console.error('[AGENTE_ANALYTICS] Error creating response types chart:', error);
    }
}

/**
 * Create hourly activity chart
 */
function createHourlyActivityChart(data) {
    const ctx = document.getElementById('hourly-activity-chart');
    if (!ctx) return;
    
    const ChartConstructor = typeof Chart !== 'undefined' ? Chart : window.Chart;
    
    if (agenteCharts.hourlyActivity) {
        agenteCharts.hourlyActivity.destroy();
        delete agenteCharts.hourlyActivity;
    }
    
    try {
        const labels = Array.from({length: 24}, (_, i) => `${i.toString().padStart(2, '0')}:00`);
        const chartData = labels.map((_, hour) => {
            const hourData = data.find(item => item.hour === hour);
            return hourData ? hourData.count : 0;
        });
        
        agenteCharts.hourlyActivity = new ChartConstructor(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Interações',
                    data: chartData,
                    backgroundColor: '#3498DB',
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
                        beginAtZero: true
                    }
                }
            }
        });
    } catch (error) {
        console.error('[AGENTE_ANALYTICS] Error creating hourly activity chart:', error);
    }
}

/**
 * Create companies activity chart
 */
function createCompaniesActivityChart(data) {
    const ctx = document.getElementById('companies-activity-chart');
    if (!ctx) return;
    
    const ChartConstructor = typeof Chart !== 'undefined' ? Chart : window.Chart;
    
    if (agenteCharts.companiesActivity) {
        agenteCharts.companiesActivity.destroy();
        delete agenteCharts.companiesActivity;
    }
    
    try {
        const labels = data.map(item => item.empresa || 'N/A').slice(0, 5);
        const chartData = data.map(item => item.total_interacoes || 0).slice(0, 5);
        
        agenteCharts.companiesActivity = new ChartConstructor(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Interações',
                    data: chartData,
                    backgroundColor: '#10b981',
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y',
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    x: {
                        beginAtZero: true
                    }
                }
            }
        });
    } catch (error) {
        console.error('[AGENTE_ANALYTICS] Error creating companies activity chart:', error);
    }
}

/**
 * Update users table (renomeado de updateCompaniesTable)
 */
function updateUsersTable(users) {
    const table = document.querySelector('#top-users-table');
    const tbody = table.querySelector('tbody');
    
    if (!tbody) return;
    
    // Hide loading
    const loadingEl = document.getElementById('top-users-loading');
    if (loadingEl) loadingEl.style.display = 'none';
    
    // Update users count
    const countEl = document.getElementById('users-count');
    if (countEl) {
        countEl.textContent = `${users.length} usuários encontrados`;
    }
    
    tbody.innerHTML = '';
    
    if (users.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">Nenhum usuário encontrado</td></tr>';
        if (countEl) countEl.textContent = 'Nenhum usuário encontrado';
        return;
    }
    
    users.forEach(user => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>
                <div class="user-info">
                    <strong>${user.nome_usuario || 'N/A'}</strong>
                    <br><small>${user.email || 'N/A'}</small>
                </div>
            </td>
            <td>${user.whatsapp || 'N/A'}</td>
            <td>${user.empresa || 'N/A'}</td>
            <td class="text-center">${user.total_interacoes || 0}</td>
            <td class="text-center">${user.tempo_medio || '0s'}</td>
            <td class="text-center">${user.ultima_interacao || 'N/A'}</td>
        `;
        tbody.appendChild(row);
    });
}

/**
 * Load companies data
 */
async function loadCompaniesData() {
    try {
        // Check cache first
        let cachedCompanies = agenteCache.get('companies');
        if (cachedCompanies) {
            createTopCompaniesChart(cachedCompanies);
            return;
        }
        
        const response = await fetch('/analytics/api/agente/top-companies?' + getFilterParams());
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            agenteCache.set('companies', data.data);
            createTopCompaniesChart(data.data);
        } else {
            throw new Error(data.error || 'Erro ao carregar empresas');
        }
        
    } catch (error) {
        console.error('[AGENTE_ANALYTICS] Error loading companies:', error);
        createTopCompaniesChart([]);
    }
}

/**
 * Update companies table
 */
function updateCompaniesTable(companies) {
    // Para analytics agente, usamos gráfico em vez de tabela
    // Se quiser tabela, precisa adicionar no template
    console.log('[AGENTE_ANALYTICS] Companies data received:', companies);
    return;
    
    const table = document.querySelector('#companies-table');
    if (!table) {
        console.log('[AGENTE_ANALYTICS] Companies table not found - using chart instead');
        return;
    }
    const thead = table.querySelector('thead');
    const tbody = table.querySelector('tbody');
    
    if (!tbody) return;
    
    // Add headers if not exist
    if (!thead.children.length) {
        thead.innerHTML = `
            <tr>
                <th>Empresa</th>
                <th>Interações</th>
                <th>Usuários</th>
                <th>Média Processos</th>
                <th>Última Interação</th>
            </tr>
        `;
    }
    
    // Hide loading
    const loadingEl = document.getElementById('companies-loading');
    if (loadingEl) loadingEl.classList.add('hidden');
    
    tbody.innerHTML = '';
    
    if (companies.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">Nenhuma empresa encontrada</td></tr>';
        return;
    }
    
    companies.forEach(company => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="font-medium">${company.empresa_nome || 'N/A'}</td>
            <td class="text-center">${company.total_interactions || 0}</td>
            <td class="text-center">${company.unique_users || 0}</td>
            <td class="text-center">${company.avg_processes || 0}</td>
            <td class="text-sm text-muted">${formatDateTime(company.last_interaction) || 'N/A'}</td>
        `;
        tbody.appendChild(row);
    });
}

/**
 * Load users data
 */
async function loadUsersData() {
    try {
        // Check cache first
        let cachedUsers = agenteCache.get('users');
        if (cachedUsers) {
            updateUsersTable(cachedUsers);
            return;
        }
        
        const response = await fetch('/analytics/api/agente/users?' + getFilterParams());
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.success && Array.isArray(data)) {
            agenteCache.set('users', data);
            updateTopUsersTable(data);
        } else if (data.success && data.data && Array.isArray(data.data)) {
            agenteCache.set('users', data.data);
            updateTopUsersTable(data.data);
        } else if (Array.isArray(data)) {
            // Compatibilidade: se retornar array diretamente
            agenteCache.set('users', data);
            updateTopUsersTable(data);
        } else {
            throw new Error(data.error || 'Erro ao carregar usuários');
        }
        
    } catch (error) {
        console.error('[AGENTE_ANALYTICS] Error loading users:', error);
        updateTopUsersTable([]);
    }
}

/**
 * Update top users table (Analytics Agente specific)
 */
function updateTopUsersTable(users) {
    const table = document.querySelector('#top-users-table');
    if (!table) {
        console.log('[AGENTE_ANALYTICS] Top users table not found');
        return;
    }
    
    const tbody = table.querySelector('tbody');
    if (!tbody) return;
    
    // Hide loading
    const loadingEl = document.getElementById('top-users-loading');
    if (loadingEl) loadingEl.classList.add('hidden');
    
    // Update count
    const countEl = document.getElementById('users-count');
    if (countEl) {
        countEl.textContent = `${users.length} usuário${users.length !== 1 ? 's' : ''} encontrado${users.length !== 1 ? 's' : ''}`;
    }
    
    // Clear existing rows
    tbody.innerHTML = '';
    
    // Add data rows
    if (users && users.length > 0) {
        users.slice(0, 10).forEach((user, index) => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>
                    <div class="user-info">
                        <div class="user-name">${user.user_name || 'N/A'}</div>
                    </div>
                </td>
                <td><span class="contact-text">${user.whatsapp_number || 'N/A'}</span></td>
                <td><span class="company-text">${user.empresa_nome || 'N/A'}</span></td>
                <td><span class="metric-value">${user.total_interactions || 0}</span></td>
                <td><span class="time-text">${user.avg_response_time || 'N/A'}</span></td>
                <td><span class="date-text">${user.last_interaction || 'N/A'}</span></td>
            `;
            tbody.appendChild(row);
        });
    } else {
        tbody.innerHTML = '<tr><td colspan="6" class="no-data">Nenhum usuário encontrado</td></tr>';
    }
}

/**
 * Update interactions table (Analytics Agente specific)
 */
function updateInteractionsTable(interactions) {
    const table = document.querySelector('#interaction-details-table');
    if (!table) {
        console.log('[AGENTE_ANALYTICS] Interaction details table not found');
        return;
    }
    
    const tbody = table.querySelector('tbody');
    if (!tbody) return;
    
    // Hide loading
    const loadingEl = document.getElementById('interaction-details-loading');
    if (loadingEl) loadingEl.classList.add('hidden');
    
    // Update count
    const countEl = document.getElementById('interaction-details-count');
    if (countEl) {
        countEl.textContent = `${interactions.length} interaç${interactions.length !== 1 ? 'ões' : 'ão'} carregada${interactions.length !== 1 ? 's' : ''}`;
    }
    
    // Clear existing rows
    tbody.innerHTML = '';
    
    // Add data rows
    if (interactions && interactions.length > 0) {
        interactions.forEach((interaction, index) => {
            const row = document.createElement('tr');
            
            // Determinar tipo baseado no response_type
            let typeText = 'Normal';
            let typeClass = 'type-normal';
            if (interaction.response_type === 'arquivo') {
                typeText = 'Documento';
                typeClass = 'type-document';
            }
            
            // Status baseado no is_successful
            const statusText = interaction.is_successful ? 'Sucesso' : 'Erro';
            const statusClass = interaction.is_successful ? 'status-success' : 'status-error';
            
            row.innerHTML = `
                <td><span class="date-text">${interaction.message_timestamp || 'N/A'}</span></td>
                <td>
                    <div class="user-info-simple">
                        <span class="user-name-simple">${interaction.user_name || 'N/A'}</span>
                    </div>
                </td>
                <td><span class="company-text">${interaction.empresa_nome || 'N/A'}</span></td>
                <td><span class="message-text">${truncateText(interaction.user_message || 'N/A', 50)}</span></td>
                <td><span class="response-text">${interaction.total_processos_encontrados || 0} processo${(interaction.total_processos_encontrados || 0) !== 1 ? 's' : ''} encontrado${(interaction.total_processos_encontrados || 0) !== 1 ? 's' : ''}</span></td>
                <td><span class="type-badge ${typeClass}">${typeText}</span></td>
                <td><span class="time-text">N/A</span></td>
                <td><span class="status-badge ${statusClass}">${statusText}</span></td>
                <td>
                    <button class="btn-view-details" onclick="openInteractionModal('${interaction.id}')" title="Ver detalhes">
                        <i class="mdi mdi-eye"></i>
                    </button>
                </td>
            `;
            tbody.appendChild(row);
        });
    } else {
        tbody.innerHTML = '<tr><td colspan="9" class="no-data">Nenhuma interação encontrada</td></tr>';
    }
}

/**
 * Update users table
 */
function updateUsersTable(users) {
    const table = document.querySelector('#users-table');
    if (!table) {
        console.log('[AGENTE_ANALYTICS] Users table not found - using top-users-table instead');
        updateTopUsersTable(users);
        return;
    }
    const thead = table.querySelector('thead');
    const tbody = table.querySelector('tbody');
    
    if (!tbody) return;
    
    // Add headers if not exist
    if (!thead.children.length) {
        thead.innerHTML = `
            <tr>
                <th>Usuário</th>
                <th>WhatsApp</th>
                <th>Empresa</th>
                <th>Interações</th>
                <th>Tempo Médio</th>
                <th>Última Interação</th>
            </tr>
        `;
    }
    
    // Hide loading
    const loadingEl = document.getElementById('users-loading');
    if (loadingEl) loadingEl.classList.add('hidden');
    
    tbody.innerHTML = '';
    
    if (users.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">Nenhum usuário encontrado</td></tr>';
        return;
    }
    
    users.forEach(user => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="font-medium">${user.user_name || 'N/A'}</td>
            <td class="text-sm">${user.whatsapp_number || 'N/A'}</td>
            <td class="text-sm">${user.empresa_nome || 'N/A'}</td>
            <td class="text-center">${user.total_interactions || 0}</td>
            <td class="text-center text-sm">${user.avg_response_time || 'N/A'}</td>
            <td class="text-sm text-muted">${formatDateTime(user.last_interaction) || 'N/A'}</td>
        `;
        tbody.appendChild(row);
    });
}

/**
 * Load interactions table
 */
async function loadInteractionsTable(reset = true) {
    try {
        if (reset) {
            currentPage = 1;
        }
        
        const params = new URLSearchParams({
            ...getFilterParamsObject(),
            page: currentPage,
            limit: pageSize
        });
        
        const response = await fetch('/analytics/api/agente/interactions?' + params.toString());
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            if (reset) {
                updateInteractionsTable(data.data);
            } else {
                appendInteractionsTable(data.data);
            }
            
            // Update load more button visibility
            const loadMoreBtn = document.getElementById('load-more-interactions');
            if (loadMoreBtn) {
                loadMoreBtn.style.display = data.data.length < pageSize ? 'none' : 'block';
            }
        } else {
            throw new Error(data.error || 'Erro ao carregar interações');
        }
        
    } catch (error) {
        console.error('[AGENTE_ANALYTICS] Error loading interactions:', error);
        if (reset) {
            updateInteractionsTable([]);
        }
    }
}

/**
 * Append interactions to table
 */
function appendInteractionsTable(interactions) {
    const tbody = document.querySelector('#interaction-details-table tbody');
    if (!tbody) return;
    
    interactions.forEach(interaction => {
        const row = createInteractionRow(interaction);
        tbody.appendChild(row);
    });
    
    // Update interactions count
    const countEl = document.getElementById('interactions-count');
    if (countEl) {
        const currentRows = tbody.querySelectorAll('tr').length;
        countEl.textContent = `${currentRows} interações encontradas`;
    }
}

/**
 * Create interaction table row
 */
function createInteractionRow(interaction) {
    const row = document.createElement('tr');
    
    const statusClass = interaction.is_successful ? 'success' : 'error';
    const statusText = interaction.is_successful ? 'Sucesso' : 'Erro';
    
    const messagePreview = truncateText(interaction.user_message || '', 50);
    
    row.innerHTML = `
        <td>
            <button class="action-btn details" onclick="openInteractionModal('${interaction.id}')" title="Ver detalhes">
                <i class="mdi mdi-eye"></i>
            </button>
        </td>
        <td>${formatDateTime(interaction.message_timestamp) || 'N/A'}</td>
        <td>${interaction.user_name || 'N/A'}</td>
        <td>${interaction.empresa_nome || 'N/A'}</td>
        <td title="${interaction.user_message || ''}" class="truncate">${messagePreview}</td>
        <td><span class="badge ${interaction.response_type || 'normal'}">${interaction.response_type || 'Normal'}</span></td>
        <td>${interaction.total_processos_encontrados || 0}</td>
        <td><span class="status-indicator ${statusClass}">${statusText}</span></td>
    `;
    
    return row;
}

/**
 * Open interaction details modal
 */
async function openInteractionModal(interactionId) {
    try {
        const response = await fetch(`/analytics/api/agente/interaction/${interactionId}`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            populateInteractionModal(data.data);
            document.getElementById('interaction-modal').style.display = 'block';
        } else {
            throw new Error(data.error || 'Erro ao carregar detalhes da interação');
        }
        
    } catch (error) {
        console.error('[AGENTE_ANALYTICS] Error loading interaction details:', error);
        showError('Erro ao carregar detalhes da interação');
    }
}

/**
 * Format agent response for better display
 */
function formatAgentResponse(responseText) {
    console.log('🔍 formatAgentResponse - Input:', responseText);
    console.log('🔍 formatAgentResponse - Input Type:', typeof responseText);
    
    if (!responseText) {
        console.log('🔍 formatAgentResponse - Empty input, returning N/A');
        return 'N/A';
    }
    
    // Clean the response text - remove markdown json formatting if present
    let cleanedText = responseText.trim();
    
    // Remove markdown code blocks (```json and ```)
    if (cleanedText.startsWith('```json')) {
        cleanedText = cleanedText.replace(/^```json\s*/, '').replace(/\s*```$/, '');
        console.log('🔍 formatAgentResponse - Removed markdown formatting');
    } else if (cleanedText.startsWith('```')) {
        cleanedText = cleanedText.replace(/^```\s*/, '').replace(/\s*```$/, '');
        console.log('🔍 formatAgentResponse - Removed generic markdown formatting');
    }
    
    cleanedText = cleanedText.trim();
    console.log('🔍 formatAgentResponse - Cleaned text:', cleanedText);
    
    try {
        // Check if it's JSON format (starts with { or [)
        if (cleanedText.startsWith('{') || cleanedText.startsWith('[')) {
            console.log('🔍 formatAgentResponse - Detected JSON format');
            const jsonData = JSON.parse(cleanedText);
            console.log('🔍 formatAgentResponse - Parsed JSON:', jsonData);
            
            // Format structured response
            let formattedHtml = '<div class="agent-response-formatted">';
            
            if (jsonData.resposta) {
                console.log('🔍 formatAgentResponse - Found resposta field:', jsonData.resposta);
                formattedHtml += `
                    <div class="response-content">
                        ${jsonData.resposta.replace(/\n/g, '<br>')}
                    </div>
                `;
            } else {
                console.log('🔍 formatAgentResponse - No resposta field found in JSON');
            }
            
            if (jsonData.justificativa) {
                console.log('🔍 formatAgentResponse - Found justificativa field:', jsonData.justificativa);
                formattedHtml += `
                    <div class="response-justification">
                        <span class="label">Justificativa:</span>
                        <div class="content">${jsonData.justificativa}</div>
                    </div>
                `;
            }
            
            formattedHtml += '</div>';
            console.log('🔍 formatAgentResponse - Final HTML:', formattedHtml);
            return formattedHtml;
        } else {
            console.log('🔍 formatAgentResponse - Not JSON format, treating as plain text');
        }
    } catch (e) {
        console.log('🔍 formatAgentResponse - JSON parse error:', e.message);
        // If not valid JSON, treat as plain text
    }
    
    // For plain text responses, just format line breaks
    console.log('🔍 formatAgentResponse - Treating as plain text, final result:', cleanedText.replace(/\n/g, '<br>'));
    return cleanedText.replace(/\n/g, '<br>');
}

/**
 * Populate interaction modal with data
 */
function populateInteractionModal(interaction) {
    // User info
    document.getElementById('modal-user-name').textContent = interaction.user_name || 'N/A';
    document.getElementById('modal-whatsapp').textContent = interaction.whatsapp_number || 'N/A';
    document.getElementById('modal-empresa').textContent = interaction.empresa_nome || 'N/A';
    document.getElementById('modal-timestamp').textContent = formatDateTime(interaction.message_timestamp) || 'N/A';
    
    // Message
    document.getElementById('modal-user-message').textContent = interaction.user_message || 'N/A';
    
    // Response info
    const responseTypeEl = document.getElementById('modal-response-type');
    responseTypeEl.textContent = interaction.response_type || 'Normal';
    responseTypeEl.className = `badge ${interaction.response_type || 'normal'}`;
    
    document.getElementById('modal-processes-found').textContent = interaction.total_processos_encontrados || 0;
    document.getElementById('modal-companies-found').textContent = interaction.empresas_encontradas || 0;
    document.getElementById('modal-response-time').textContent = formatResponseTime(interaction.response_time_ms);
    
    // Agent response - formatted for better readability
    const agentResponseEl = document.getElementById('modal-agent-response');
    let agentResponse = 'N/A';
    if (interaction.agent_response) {
        agentResponse = formatAgentResponse(interaction.agent_response);
    }
    agentResponseEl.innerHTML = agentResponse;
    
    // Technical info
    const statusEl = document.getElementById('modal-status');
    statusEl.textContent = interaction.is_successful ? 'Sucesso' : 'Erro';
    statusEl.className = `badge ${interaction.is_successful ? 'success' : 'error'}`;
    
    document.getElementById('modal-session-id').textContent = interaction.session_id || 'N/A';
    document.getElementById('modal-instance').textContent = interaction.whatsapp_instance || 'N/A';
    
    // CNPJs
    let cnpjsText = 'N/A';
    if (interaction.cnpjs_consultados) {
        try {
            const cnpjs = JSON.parse(interaction.cnpjs_consultados);
            cnpjsText = Array.isArray(cnpjs) ? cnpjs.join(', ') : cnpjs;
        } catch {
            cnpjsText = interaction.cnpjs_consultados;
        }
    }
    document.getElementById('modal-cnpjs').textContent = cnpjsText;
}

/**
 * Load more interactions
 */
function loadMoreInteractions() {
    currentPage++;
    loadInteractionsTable(false);
}

/**
 * Open filters modal
 */
function openFiltersModal() {
    // Load filter options if needed
    loadFilterOptions();
    
    // Set current filter values
    document.getElementById('filter-date-range').value = currentFilters.dateRange || '30d';
    document.getElementById('filter-response-type').value = currentFilters.responseType || 'all';
    document.getElementById('filter-empresa').value = currentFilters.empresa || 'all';
    document.getElementById('filter-user').value = currentFilters.user || 'all';
    
    document.getElementById('filters-modal').style.display = 'block';
}

/**
 * Load filter options
 */
async function loadFilterOptions() {
    try {
        // This could be extended to load dynamic filter options
        // For now, we'll keep it simple
    } catch (error) {
        console.error('[AGENTE_ANALYTICS] Error loading filter options:', error);
    }
}

/**
 * Apply filters
 */
function applyFilters() {
    currentFilters = {
        dateRange: document.getElementById('filter-date-range').value,
        responseType: document.getElementById('filter-response-type').value,
        empresa: document.getElementById('filter-empresa').value,
        user: document.getElementById('filter-user').value
    };
    
    // Update filter summary
    updateFilterSummary();
    
    // Invalidate cache and reload data
    agenteCache.invalidate();
    loadAnalyticsData();
    
    // Close modal
    document.getElementById('filters-modal').style.display = 'none';
    
    // Show/hide reset filters button
    const hasActiveFilters = Object.values(currentFilters).some(value => 
        value && value !== 'all' && value !== '30d'
    );
    
    const resetBtn = document.getElementById('reset-filters');
    if (resetBtn) {
        resetBtn.style.display = hasActiveFilters ? 'block' : 'none';
    }
}

/**
 * Clear filters
 */
function clearFilters() {
    document.getElementById('filter-date-range').value = '30d';
    document.getElementById('filter-response-type').value = 'all';
    document.getElementById('filter-empresa').value = 'all';
    document.getElementById('filter-user').value = 'all';
}

/**
 * Reset filters
 */
function resetFilters() {
    currentFilters = {};
    updateFilterSummary();
    agenteCache.invalidate();
    loadAnalyticsData();
    
    const resetBtn = document.getElementById('reset-filters');
    if (resetBtn) {
        resetBtn.style.display = 'none';
    }
}

/**
 * Update filter summary
 */
function updateFilterSummary() {
    const summaryEl = document.getElementById('filter-summary-text');
    if (!summaryEl) return;
    
    const dateRange = currentFilters.dateRange || '30d';
    const dateRangeText = {
        '1d': 'último dia',
        '7d': 'últimos 7 dias',
        '30d': 'últimos 30 dias',
        '90d': 'últimos 90 dias'
    };
    
    let summary = `Vendo dados dos ${dateRangeText[dateRange] || 'últimos 30 dias'}`;
    
    const activeFilters = [];
    if (currentFilters.responseType && currentFilters.responseType !== 'all') {
        activeFilters.push(`tipo: ${currentFilters.responseType}`);
    }
    if (currentFilters.empresa && currentFilters.empresa !== 'all') {
        activeFilters.push(`empresa: ${currentFilters.empresa}`);
    }
    if (currentFilters.user && currentFilters.user !== 'all') {
        activeFilters.push(`usuário: ${currentFilters.user}`);
    }
    
    if (activeFilters.length > 0) {
        summary += ` | Filtros: ${activeFilters.join(', ')}`;
    }
    
    summaryEl.textContent = summary;
}

/**
 * Get filter parameters for API calls
 */
function getFilterParams() {
    return new URLSearchParams(getFilterParamsObject()).toString();
}

/**
 * Get filter parameters as object
 */
function getFilterParamsObject() {
    return {
        dateRange: currentFilters.dateRange || '30d',
        responseType: currentFilters.responseType || 'all',
        empresa: currentFilters.empresa || 'all',
        user: currentFilters.user || 'all'
    };
}

/**
 * Show loading for all components
 */
function showAllLoading() {
    const loadingElements = document.querySelectorAll('.component-loading');
    loadingElements.forEach(el => {
        el.classList.remove('hidden');
    });
}

/**
 * Hide loading for all components
 */
function hideAllLoading() {
    const loadingElements = document.querySelectorAll('.component-loading');
    loadingElements.forEach(el => {
        el.classList.add('hidden');
    });
}

/**
 * Show error message
 */
function showError(message) {
    console.error('[AGENTE_ANALYTICS] Error:', message);
    // Could implement a toast notification system here
}

/**
 * Format date time
 */
function formatDateTime(dateString) {
    if (!dateString) return 'N/A';
    
    try {
        let date;
        
        // Try different date formats
        if (dateString.includes('/')) {
            // Format: DD/MM/YYYY HH:MM:SS
            const [datePart, timePart] = dateString.split(' ');
            const [day, month, year] = datePart.split('/');
            const [hour, minute, second] = (timePart || '00:00:00').split(':');
            date = new Date(year, month - 1, day, hour, minute, second);
        } else {
            // ISO format or other
            date = new Date(dateString);
        }
        
        // Check if date is valid
        if (isNaN(date.getTime())) {
            return dateString; // Return original if invalid
        }
        
        return date.toLocaleString('pt-BR', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            timeZone: 'America/Sao_Paulo'
        });
    } catch (error) {
        console.error('[AGENTE_ANALYTICS] Error formatting date:', dateString, error);
        return dateString;
    }
}

/**
 * Format response time
 */
function formatResponseTime(ms) {
    if (!ms || ms <= 0) return 'N/A';
    
    if (ms < 1000) {
        return `${ms}ms`;
    } else if (ms < 60000) {
        return `${(ms / 1000).toFixed(1)}s`;
    } else {
        const minutes = Math.floor(ms / 60000);
        const seconds = Math.floor((ms % 60000) / 1000);
        return `${minutes}m ${seconds}s`;
    }
}

/**
 * Truncate text
 */
function truncateText(text, maxLength) {
    if (!text || text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

/**
 * Load interaction types chart data
 */
async function loadInteractionTypesChart() {
    try {
        const response = await fetch('/analytics/api/agente/interaction-types?' + getFilterParams());
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            createInteractionTypesChart(data.data);
        } else {
            throw new Error(data.error || 'Erro ao carregar tipos de interação');
        }
        
    } catch (error) {
        console.error('[AGENTE_ANALYTICS] Error loading interaction types:', error);
        createInteractionTypesChart({
            labels: ['Interações Normais', 'Solicitações de Documento'],
            values: [0, 0],
            percentages: [0, 0],
            total: 0
        });
    }
}

/**
 * Create interaction types chart (doughnut)
 */
function createInteractionTypesChart(data) {
    const ctx = document.getElementById('interaction-types-chart');
    if (!ctx) {
        console.error('[AGENTE_ANALYTICS] Interaction types chart canvas not found');
        return;
    }
    
    // Check if Chart.js is available
    if (typeof Chart === 'undefined' && typeof window.Chart === 'undefined') {
        console.error('[AGENTE_ANALYTICS] Chart.js not available');
        return;
    }
    
    const ChartConstructor = typeof Chart !== 'undefined' ? Chart : window.Chart;
    
    // Destroy existing chart
    if (agenteCharts.interactionTypes) {
        agenteCharts.interactionTypes.destroy();
    }
    
    try {
        // Hide loading
        const loadingEl = document.getElementById('interaction-types-loading');
        if (loadingEl) loadingEl.classList.add('hidden');
        
        agenteCharts.interactionTypes = new ChartConstructor(ctx, {
            type: 'doughnut',
            data: {
                labels: data.labels || ['Interações Normais', 'Solicitações de Documento'],
                datasets: [{
                    data: data.values || [0, 0],
                    backgroundColor: [
                        AGENTE_COLORS.normal,
                        AGENTE_COLORS.arquivo,
                        '#6b7280' // Para "outros" se existir
                    ],
                    borderWidth: 2,
                    borderColor: '#ffffff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 20,
                            usePointStyle: true,
                            font: {
                                size: 12
                            }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.parsed || 0;
                                const percentage = data.percentages ? data.percentages[context.dataIndex] : 0;
                                return `${label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
        
        console.log('[AGENTE_ANALYTICS] Interaction types chart created successfully');
        
    } catch (error) {
        console.error('[AGENTE_ANALYTICS] Error creating interaction types chart:', error);
    }
}

/**
 * Load top users chart data
 */
async function loadTopUsersChart() {
    try {
        const response = await fetch('/analytics/api/agente/top-users?' + getFilterParams());
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            createTopUsersChart(data.data);
        } else {
            throw new Error(data.error || 'Erro ao carregar top usuários');
        }
        
    } catch (error) {
        console.error('[AGENTE_ANALYTICS] Error loading top users:', error);
        createTopUsersChart([]);
    }
}

/**
 * Create top users chart (bar)
 */
function createTopUsersChart(data) {
    const ctx = document.getElementById('top-users-chart');
    if (!ctx) {
        console.error('[AGENTE_ANALYTICS] Top users chart canvas not found');
        return;
    }
    
    // Check if Chart.js is available
    if (typeof Chart === 'undefined' && typeof window.Chart === 'undefined') {
        console.error('[AGENTE_ANALYTICS] Chart.js not available');
        return;
    }
    
    const ChartConstructor = typeof Chart !== 'undefined' ? Chart : window.Chart;
    
    // Destroy existing chart
    if (agenteCharts.topUsers) {
        agenteCharts.topUsers.destroy();
    }
    
    try {
        // Hide loading
        const loadingEl = document.getElementById('top-users-chart-loading');
        if (loadingEl) loadingEl.classList.add('hidden');
        
        // Prepare data - take top 5 users
        const topUsers = data.slice(0, 5);
        const labels = topUsers.map(user => user.user_name || 'N/A');
        const values = topUsers.map(user => user.total_interactions || 0);
        
        agenteCharts.topUsers = new ChartConstructor(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Interações',
                    data: values,
                    backgroundColor: AGENTE_COLORS.normal,
                    borderColor: AGENTE_COLORS.normal,
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y', // Horizontal bar chart
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            title: function(context) {
                                const index = context[0].dataIndex;
                                const user = topUsers[index];
                                return user ? user.user_name : 'N/A';
                            },
                            label: function(context) {
                                const index = context.dataIndex;
                                const user = topUsers[index];
                                return `${context.parsed.x} interações - ${user.empresa_nome || 'N/A'}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        grid: {
                            display: false
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
        
        console.log('[AGENTE_ANALYTICS] Top users chart created successfully');
        
    } catch (error) {
        console.error('[AGENTE_ANALYTICS] Error creating top users chart:', error);
    }
}

/**
 * Update companies chart (instead of table for agente)
 */
function createTopCompaniesChart(data) {
    const ctx = document.getElementById('top-companies-chart');
    if (!ctx) {
        console.error('[AGENTE_ANALYTICS] Top companies chart canvas not found');
        return;
    }
    
    // Check if Chart.js is available
    if (typeof Chart === 'undefined' && typeof window.Chart === 'undefined') {
        console.error('[AGENTE_ANALYTICS] Chart.js not available');
        return;
    }
    
    const ChartConstructor = typeof Chart !== 'undefined' ? Chart : window.Chart;
    
    // Destroy existing chart
    if (agenteCharts.topCompanies) {
        agenteCharts.topCompanies.destroy();
    }
    
    try {
        // Hide loading
        const loadingEl = document.getElementById('top-companies-chart-loading');
        if (loadingEl) loadingEl.classList.add('hidden');
        
        // Prepare data - take top 5 companies
        const topCompanies = data.slice(0, 5);
        const labels = topCompanies.map(company => company.empresa_nome || 'N/A');
        const values = topCompanies.map(company => company.total_interactions || 0);
        
        agenteCharts.topCompanies = new ChartConstructor(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Interações',
                    data: values,
                    backgroundColor: AGENTE_COLORS.arquivo,
                    borderColor: AGENTE_COLORS.arquivo,
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y', // Horizontal bar chart
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            title: function(context) {
                                const index = context[0].dataIndex;
                                const company = topCompanies[index];
                                return company ? company.empresa_nome : 'N/A';
                            },
                            label: function(context) {
                                const index = context.dataIndex;
                                const company = topCompanies[index];
                                return `${context.parsed.x} interações - ${company.unique_users || 0} usuários`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        grid: {
                            display: false
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
        
        console.log('[AGENTE_ANALYTICS] Top companies chart created successfully');
        
    } catch (error) {
        console.error('[AGENTE_ANALYTICS] Error creating top companies chart:', error);
    }
}

/**
 * Load company summary data
 */
async function loadCompanySummary() {
    try {
        const response = await fetch('/analytics/api/agente/top-companies?' + getFilterParams());
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            updateCompanySummary(data.data);
        } else {
            throw new Error(data.error || 'Erro ao carregar resumo da empresa');
        }
        
    } catch (error) {
        console.error('[AGENTE_ANALYTICS] Error loading company summary:', error);
        updateCompanySummary([]);
    }
}

/**
 * Update company summary display
 */
function updateCompanySummary(companies) {
    const container = document.getElementById('company-summary-content');
    if (!container) {
        console.log('[AGENTE_ANALYTICS] Company summary container not found');
        return;
    }
    
    // Hide loading
    const loadingEl = document.getElementById('company-summary-loading');
    if (loadingEl) loadingEl.classList.add('hidden');
    
    // Update count
    const countEl = document.getElementById('company-summary-count');
    if (countEl) {
        countEl.textContent = `${companies.length} empresa${companies.length !== 1 ? 's' : ''} ativa${companies.length !== 1 ? 's' : ''}`;
    }
    
    // Clear existing content
    container.innerHTML = '';
    
    if (companies && companies.length > 0) {
        companies.forEach(company => {
            const card = document.createElement('div');
            card.className = 'summary-card';
            
            card.innerHTML = `
                <div class="summary-card-header">
                    <h3 class="summary-card-title">${company.empresa_nome || 'N/A'}</h3>
                    <i class="mdi mdi-office-building summary-card-icon"></i>
                </div>
                <div class="summary-card-content">
                    <div class="summary-metric">
                        <span class="summary-metric-label">Total de Interações:</span>
                        <span class="summary-metric-value">${company.total_interactions || 0}</span>
                    </div>
                    <div class="summary-metric">
                        <span class="summary-metric-label">Usuários Únicos:</span>
                        <span class="summary-metric-value">${company.unique_users || 0}</span>
                    </div>
                    <div class="summary-metric">
                        <span class="summary-metric-label">Solicitações Normais:</span>
                        <span class="summary-metric-value">${company.normal_requests || 0}</span>
                    </div>
                    <div class="summary-metric">
                        <span class="summary-metric-label">Solicitações de Arquivo:</span>
                        <span class="summary-metric-value">${company.arquivo_requests || 0}</span>
                    </div>
                    <div class="summary-metric">
                        <span class="summary-metric-label">Média de Processos:</span>
                        <span class="summary-metric-value">${company.avg_processos_encontrados || 0}</span>
                    </div>
                    <div class="summary-metric">
                        <span class="summary-metric-label">Última Interação:</span>
                        <span class="summary-metric-value">${company.last_interaction || 'N/A'}</span>
                    </div>
                </div>
            `;
            
            container.appendChild(card);
        });
    } else {
        container.innerHTML = '<div class="no-data">Nenhuma empresa encontrada</div>';
    }
}

// Make functions available globally
window.openInteractionModal = openInteractionModal;