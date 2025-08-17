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
    
    // Set up controlled auto-refresh (60 seconds)
    setInterval(() => {
        console.log('[AGENTE_ANALYTICS] Auto-refreshing data...');
        agenteCache.invalidate();
        loadAnalyticsData();
    }, 60000); // 60 seconds
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
        
        // Load companies data
        await loadCompaniesData();
        
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
        
        const response = await fetch('/usuarios/analytics/api/agente/kpis?' + getFilterParams());
        
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
        'avg-response-time': kpis.avg_response_time || '0s',
        'normal-responses': kpis.normal_responses || 0,
        'file-requests': kpis.file_requests || 0
    };
    
    Object.entries(elements).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
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
        
        const response = await fetch('/usuarios/analytics/api/agente/chart?' + getFilterParams());
        
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
    const ctx = document.getElementById('interactions-chart');
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
 * Load companies data
 */
async function loadCompaniesData() {
    try {
        // Check cache first
        let cachedCompanies = agenteCache.get('companies');
        if (cachedCompanies) {
            updateCompaniesTable(cachedCompanies);
            return;
        }
        
        const response = await fetch('/usuarios/analytics/api/agente/companies?' + getFilterParams());
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            agenteCache.set('companies', data.data);
            updateCompaniesTable(data.data);
        } else {
            throw new Error(data.error || 'Erro ao carregar empresas');
        }
        
    } catch (error) {
        console.error('[AGENTE_ANALYTICS] Error loading companies:', error);
        updateCompaniesTable([]);
    }
}

/**
 * Update companies table
 */
function updateCompaniesTable(companies) {
    const table = document.querySelector('#companies-table');
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
        
        const response = await fetch('/usuarios/analytics/api/agente/users?' + getFilterParams());
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            agenteCache.set('users', data.data);
            updateUsersTable(data.data);
        } else {
            throw new Error(data.error || 'Erro ao carregar usuários');
        }
        
    } catch (error) {
        console.error('[AGENTE_ANALYTICS] Error loading users:', error);
        updateUsersTable([]);
    }
}

/**
 * Update users table
 */
function updateUsersTable(users) {
    const table = document.querySelector('#users-table');
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
        
        const response = await fetch('/usuarios/analytics/api/agente/interactions?' + params.toString());
        
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
 * Update interactions table
 */
function updateInteractionsTable(interactions) {
    const tbody = document.querySelector('#interactions-table tbody');
    if (!tbody) return;
    
    // Hide loading
    const loadingEl = document.getElementById('interactions-table-loading');
    if (loadingEl) loadingEl.classList.add('hidden');
    
    tbody.innerHTML = '';
    
    if (interactions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="no-data">Nenhuma interação encontrada</td></tr>';
        return;
    }
    
    interactions.forEach(interaction => {
        const row = createInteractionRow(interaction);
        tbody.appendChild(row);
    });
}

/**
 * Append interactions to table
 */
function appendInteractionsTable(interactions) {
    const tbody = document.querySelector('#interactions-table tbody');
    if (!tbody) return;
    
    interactions.forEach(interaction => {
        const row = createInteractionRow(interaction);
        tbody.appendChild(row);
    });
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
        const response = await fetch(`/usuarios/analytics/api/agente/interaction/${interactionId}`);
        
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

// Make functions available globally
window.openInteractionModal = openInteractionModal;