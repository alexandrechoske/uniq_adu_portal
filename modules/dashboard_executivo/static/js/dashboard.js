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
let currentFilters = {};  // NOVO: Para armazenar filtros ativos
let isLoading = false;
let loadAttempts = 0;
const maxLoadAttempts = 3;

// CACHE INTELIGENTE: Sistema de cache para evitar recarregamentos desnecessários
let dashboardCache = {
    kpis: null,
    charts: null,
    operations: null,
    filterOptions: null,
    lastUpdate: null,
    cacheTimeout: 5 * 60 * 1000, // 5 minutos
    
    // Verificar se o cache é válido
    isValid: function() {
        return this.lastUpdate && (Date.now() - this.lastUpdate) < this.cacheTimeout;
    },
    
    // Invalidar cache
    invalidate: function() {
        this.kpis = null;
        this.charts = null;
        this.operations = null;
        this.lastUpdate = null;
        console.log('[DASHBOARD_CACHE] Cache invalidado');
    },
    
    // Definir dados no cache
    set: function(type, data) {
        this[type] = data;
        this.lastUpdate = Date.now();
        console.log(`[DASHBOARD_CACHE] Cache atualizado para ${type}`);
    },
    
    // Obter dados do cache
    get: function(type) {
        if (this.isValid() && this[type]) {
            console.log(`[DASHBOARD_CACHE] Usando cache para ${type}`);
            return this[type];
        }
        return null;
    }
};

// Estado do dashboard para evitar múltiplos carregamentos simultâneos
let dashboardState = {
    isLoading: false,
    isInitialized: false
};

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('[DASHBOARD_EXECUTIVO] Inicializando...');
    
    // Aguardar sistema unificado de loading estar pronto
    const waitForUnifiedSystem = () => {
        if (window.unifiedLoadingManager) {
            console.log('[DASHBOARD_EXECUTIVO] Sistema unificado detectado');
            initializeDashboard();
        } else {
            setTimeout(waitForUnifiedSystem, 100);
        }
    };
    
    // Detectar se o usuário está voltando para a página (cache do navegador)
    window.addEventListener('pageshow', function(event) {
        if (event.persisted || (window.performance && window.performance.navigation.type === 2)) {
            console.log('[DASHBOARD_EXECUTIVO] Página restaurada do cache do navegador');
            
            // Se o dashboard já foi inicializado mas os gráficos estão vazios, recriar
            if (dashboardState.isInitialized) {
                setTimeout(() => {
                    validateAndRecreateCharts();
                }, 500);
            }
        }
    });
    
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
            waitForUnifiedSystem();
        } else {
            console.error('[DASHBOARD_EXECUTIVO] Chart.js não foi carregado');
        }
    }, 1000);
});

/**
 * Validate and recreate charts if they are missing
 */
function validateAndRecreateCharts() {
    console.log('[DASHBOARD_EXECUTIVO] Validando estado dos gráficos...');
    
    // Lista de gráficos esperados
    const expectedCharts = [
        'monthly-chart',
        'status-chart', 
        'grouped-modal-chart',
        'urf-chart'
    ];
    
    let missingCharts = 0;
    
    // Verificar se os canvas existem e se têm gráficos ativos
    expectedCharts.forEach(chartId => {
        const canvas = document.getElementById(chartId);
        if (canvas) {
            const chartInstance = Chart.getChart(canvas);
            if (!chartInstance) {
                console.warn(`[DASHBOARD_EXECUTIVO] Gráfico ${chartId} não encontrado - será recriado`);
                missingCharts++;
            }
        }
    });
    
    // Se algum gráfico estiver faltando, recriar todos usando o cache
    if (missingCharts > 0) {
        console.log(`[DASHBOARD_EXECUTIVO] ${missingCharts} gráficos faltando - recriando com cache...`);
        
        const cachedCharts = dashboardCache.get('charts');
        if (cachedCharts) {
            createDashboardChartsWithValidation(cachedCharts);
        } else {
            console.log('[DASHBOARD_EXECUTIVO] Cache não disponível - recarregando gráficos...');
            loadDashboardChartsWithCache();
        }
    } else {
        console.log('[DASHBOARD_EXECUTIVO] Todos os gráficos estão presentes');
    }
}

/**
 * Initialize the dashboard
 */
async function initializeDashboard() {
    // Evitar múltiplas inicializações simultâneas
    if (dashboardState.isLoading || dashboardState.isInitialized) {
        console.log('[DASHBOARD_EXECUTIVO] Dashboard já está carregando ou inicializado');
        return;
    }
    
    try {
        dashboardState.isLoading = true;
        
        console.log('[DASHBOARD_EXECUTIVO] Iniciando carregamento do dashboard...');
        
        // Initialize enhanced table FIRST, before loading data
        initializeEnhancedTable();
        
        // Then load initial data with cache check
        await loadInitialDataWithCache();
        
        // Setup event listeners and filters
        setupEventListeners();
        setMonthlyChartPeriod('mensal');
        
        dashboardState.isInitialized = true;
        updateLastUpdate();
        
        console.log('[DASHBOARD_EXECUTIVO] Dashboard inicializado com sucesso');
        
        // Notificar sistema unificado que o carregamento foi concluído
        if (window.unifiedLoadingManager && window.unifiedLoadingManager.isTransitioning) {
            console.log('[DASHBOARD_EXECUTIVO] Notificando sistema unificado - dados carregados');
            // O sistema unificado detectará automaticamente que os dados carregaram
        }
        
    } catch (error) {
        console.error('[DASHBOARD_EXECUTIVO] Erro na inicialização:', error);
        showError('Erro ao carregar dashboard: ' + error.message);
        dashboardState.isInitialized = false;
    } finally {
        dashboardState.isLoading = false;
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
        searchFields: ['ref_unique', 'ref_importador', 'importador', 'exportador_fornecedor', 'modal', 'status_processo', 'status_macro_sistema', 'mercadoria', 'urf_despacho_normalizado', 'urf_despacho'],
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
        
        // Calcular custo total - PRIORIZAR custo_total_view/custo_total (igual ao modal)
        let custoTotal = 0;
        if (operation.custo_total_view !== undefined && operation.custo_total_view !== null && operation.custo_total_view > 0) {
            custoTotal = operation.custo_total_view;
            console.log(`[RENDER_ROW] Usando custo_total_view para ${operation.ref_unique}: ${custoTotal}`);
        } else if (operation.custo_total !== undefined && operation.custo_total !== null && operation.custo_total > 0) {
            custoTotal = operation.custo_total;
            console.log(`[RENDER_ROW] Usando custo_total para ${operation.ref_unique}: ${custoTotal}`);
        } else if (operation.despesas_processo && Array.isArray(operation.despesas_processo)) {
            // Fallback: calcular manualmente
            const expenseData = processExpensesByCategory(operation.despesas_processo);
            custoTotal = expenseData.total;
            console.log(`[RENDER_ROW] Calculado manualmente para ${operation.ref_unique}: ${custoTotal}`);
        }
        
        // Log específico para processo 6555 na tabela
        if (operation.ref_unique && operation.ref_unique.includes('6555')) {
            console.log(`[RENDER_ROW] *** PROCESSO 6555 NA TABELA ***`);
            console.log(`[RENDER_ROW] custo_total_view: ${operation.custo_total_view}`);
            console.log(`[RENDER_ROW] custo_total: ${operation.custo_total}`);
            console.log(`[RENDER_ROW] custoTotal final usado: ${custoTotal}`);
        }
        
        // Determinar se deve mostrar coluna Material
        // Verificar se há clientes KINGSPAN nos dados atuais da tabela
        const hasKingspanInCurrentData = window.currentOperations && 
            window.currentOperations.some(op => 
                op.importador && op.importador.toUpperCase().includes('KING')
            );
        
        // Se há clientes KINGSPAN nos dados, mostrar a coluna
        // Para clientes KINGSPAN, mostrar o material; para outros, mostrar "-"
        const isKingspanClient = operation.importador && operation.importador.toUpperCase().includes('KING');
        const materialColumn = hasKingspanInCurrentData ? 
            `<td>${isKingspanClient ? (operation.mercadoria || '-') : '-'}</td>` : '';
        const urfColumn = `<td>${operation.urf_despacho_normalizado || operation.urf_despacho || '-'}</td>`;
        
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
            <td>${getStatusBadge(operation.status_macro_sistema || operation.status_processo || operation.status)}</td>
            <td><span class="currency-value">${formatCurrency(custoTotal)}</span></td>
            <td>${formatDataChegada(operation.data_chegada)}</td>
            ${materialColumn}
            ${urfColumn}
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
    
    // NOVO: Filter event listeners
    setupFilterEventListeners();
}

/**
 * Setup filter event listeners
 */
function setupFilterEventListeners() {
    console.log('[DASHBOARD_EXECUTIVO] Configurando event listeners dos filtros...');
    
    // Filter modal
    const openFiltersBtn = document.getElementById('open-filters');
    const closeModalBtn = document.getElementById('close-modal');
    const filterModal = document.getElementById('filter-modal');
    const applyFiltersBtn = document.getElementById('apply-filters');
    const clearFiltersBtn = document.getElementById('clear-filters');
    const resetFiltersBtn = document.getElementById('reset-filters'); // NOVO
    
    if (openFiltersBtn) {
        openFiltersBtn.addEventListener('click', function() {
            console.log('[DASHBOARD_EXECUTIVO] Botão Filtros clicado');
            
            // Verificar se as opções de filtros foram carregadas
            const materialOptions = document.getElementById('material-options');
            if (materialOptions && materialOptions.children.length === 0) {
                console.log('[DASHBOARD_EXECUTIVO] Opções de filtros não carregadas - recarregando...');
                loadFilterOptions().then(() => {
                    openFilterModal();
                });
            } else {
                openFilterModal();
            }
        });
    }
    
    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', closeFilterModal);
    }
    
    if (applyFiltersBtn) {
        applyFiltersBtn.addEventListener('click', applyFilters);
    }
    
    if (clearFiltersBtn) {
        clearFiltersBtn.addEventListener('click', clearFilters);
    }
    
    // NOVO: Reset filters button
    if (resetFiltersBtn) {
        resetFiltersBtn.addEventListener('click', resetAllFilters);
    }
    
    // Click outside modal to close
    if (filterModal) {
        filterModal.addEventListener('click', function(e) {
            if (e.target === filterModal) {
                closeFilterModal();
            }
        });
    }
    
    // Quick period buttons
    document.querySelectorAll('.btn-quick').forEach(btn => {
        btn.addEventListener('click', function() {
            const days = parseInt(this.dataset.days);
            setQuickPeriod(days);
        });
    });
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
    if (isLoading) {
        console.log('[DASHBOARD_EXECUTIVO] Já está carregando, aguardando...');
        return;
    }
    
    isLoading = true;
    loadAttempts++;
    
    try {
        console.log('[DASHBOARD_EXECUTIVO] Carregando dados iniciais... (tentativa', loadAttempts, ')');
        
        // Load data
        const response = await fetch('/dashboard-executivo/api/load-data');
        const result = await response.json();
        
        if (!result.success) {
            throw new Error(result.error || 'Erro ao carregar dados');
        }
        
        dashboardData = result.data;
        console.log(`[DASHBOARD_EXECUTIVO] Dados carregados: ${result.total_records} registros`);
        
        // Load KPIs, charts and filter options
        await Promise.all([
            loadDashboardKPIs(),
            loadDashboardCharts(),
            loadRecentOperations(),
            loadFilterOptions()  // NOVO: Carregar opções de filtros
        ]);
        
        console.log('[DASHBOARD_EXECUTIVO] Dados iniciais carregados com sucesso');
        loadAttempts = 0; // Reset attempts on success
        
    } catch (error) {
        console.error('[DASHBOARD_EXECUTIVO] Erro ao carregar dados:', error);
        
        // Tentar novamente se não atingiu o máximo
        if (loadAttempts < maxLoadAttempts) {
            console.log('[DASHBOARD_EXECUTIVO] Tentando novamente em 2 segundos...');
            setTimeout(() => {
                isLoading = false;
                loadInitialData();
            }, 2000);
            return;
        } else {
            loadAttempts = 0;
            throw error;
        }
    } finally {
        isLoading = false;
    }
}

/**
 * Load initial data with intelligent caching and retry mechanism
 */
async function loadInitialDataWithCache() {
    try {
        console.log('[DASHBOARD_EXECUTIVO] Iniciando carregamento com cache...');
        
        // Carregar dados base com retry
        dashboardData = await loadDataWithRetry();
        
        // Carregar componentes com retry automático
        await loadComponentsWithRetry();
        
    } catch (error) {
        console.error('[DASHBOARD_EXECUTIVO] Erro fatal ao carregar dados:', error);
        
        // Tentar recuperação usando cache como último recurso
        await attemptCacheRecovery();
    }
}

/**
 * Load data with automatic retry mechanism
 */
async function loadDataWithRetry(maxRetries = 3) {
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
        try {
            console.log(`[DASHBOARD_EXECUTIVO] Tentativa ${attempt}/${maxRetries} - Carregando dados base...`);
            
            const response = await fetch('/dashboard-executivo/api/load-data');
            const result = await response.json();
            
            if (result.success && result.data && result.data.length > 0) {
                console.log(`[DASHBOARD_EXECUTIVO] Dados carregados com sucesso: ${result.total_records} registros`);
                return result.data;
            } else {
                throw new Error(result.error || 'Dados não encontrados ou vazios');
            }
            
        } catch (error) {
            console.warn(`[DASHBOARD_EXECUTIVO] Tentativa ${attempt} falhou:`, error.message);
            
            if (attempt === maxRetries) {
                throw new Error(`Falha após ${maxRetries} tentativas: ${error.message}`);
            }
            
            // Aguardar antes da próxima tentativa (backoff exponencial)
            const delay = Math.pow(2, attempt) * 1000; // 2s, 4s, 8s
            console.log(`[DASHBOARD_EXECUTIVO] Aguardando ${delay}ms antes da próxima tentativa...`);
            await new Promise(resolve => setTimeout(resolve, delay));
        }
    }
}

/**
 * Load components with retry mechanism
 */
async function loadComponentsWithRetry() {
    const components = [
        { name: 'KPIs', loadFunction: () => loadDashboardKPIsWithRetry() },
        { name: 'Gráficos', loadFunction: () => loadDashboardChartsWithRetry() },
        { name: 'Operações', loadFunction: () => loadRecentOperationsWithRetry() },
        { name: 'Filtros', loadFunction: () => loadFilterOptionsWithRetry() }
    ];
    
    // Carregar componentes em paralelo com tratamento individual de erros
    const results = await Promise.allSettled(components.map(async (component) => {
        try {
            await component.loadFunction();
            console.log(`[DASHBOARD_EXECUTIVO] ✅ ${component.name} carregado com sucesso`);
            return { component: component.name, success: true };
        } catch (error) {
            console.error(`[DASHBOARD_EXECUTIVO] ❌ ${component.name} falhou:`, error.message);
            return { component: component.name, success: false, error: error.message };
        }
    }));
    
    // Verificar resultados
    const failed = results.filter(r => r.value && !r.value.success);
    if (failed.length > 0) {
        console.warn(`[DASHBOARD_EXECUTIVO] ${failed.length} componentes falharam:`, failed.map(f => f.value.component));
        
        // Mostrar mensagem discreta para o usuário
        showWarningMessage(`Alguns dados podem estar desatualizados. ${failed.length} componente(s) com problema.`);
    }
}

/**
 * Load components with intelligent caching
 */
async function loadComponentsWithCache() {
    try {
        // Verificar cache antes de fazer requisições
        let kpisData = dashboardCache.get('kpis');
        let chartsData = dashboardCache.get('charts');
        let operationsData = dashboardCache.get('operations');
        
        const promises = [];
        
        // Carregar KPIs (sempre, pois podem mudar com filtros)
        promises.push(loadDashboardKPIsWithCache());
        
        // Carregar gráficos se não estiver em cache ou se filtros mudaram
        if (!chartsData || hasFiltersChanged()) {
            promises.push(loadDashboardChartsWithCache());
        } else {
            console.log('[DASHBOARD_EXECUTIVO] Usando gráficos em cache');
            createDashboardChartsWithValidation(chartsData);
        }
        
        // Carregar operações recentes
        promises.push(loadRecentOperationsWithCache());
        
        await Promise.all(promises);
        
    } catch (error) {
        console.error('[DASHBOARD_EXECUTIVO] Erro ao carregar componentes:', error);
        throw error;
    }
}

/**
 * Check if filters have changed since last cache
 */
function hasFiltersChanged() {
    const currentFilterString = buildFilterQueryString();
    const cachedFilterString = dashboardCache.lastFilterString || '';
    
    if (currentFilterString !== cachedFilterString) {
        dashboardCache.lastFilterString = currentFilterString;
        return true;
    }
    return false;
}

/**
 * Load dashboard KPIs
 */
async function loadDashboardKPIs() {
    try {
        console.log('[DASHBOARD_EXECUTIVO] Carregando KPIs...');
        
        const queryString = buildFilterQueryString();
        const response = await fetch(`/dashboard-executivo/api/kpis?${queryString}`);
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
 * Load dashboard KPIs with cache
 */
async function loadDashboardKPIsWithCache() {
    try {
        console.log('[DASHBOARD_EXECUTIVO] Carregando KPIs com cache...');
        
        const queryString = buildFilterQueryString();
        const response = await fetch(`/dashboard-executivo/api/kpis?${queryString}`);
        const result = await response.json();
        
        if (result.success) {
            dashboardCache.set('kpis', result.kpis);
            updateDashboardKPIs(result.kpis);
        } else {
            console.error('[DASHBOARD_EXECUTIVO] Erro ao carregar KPIs:', result.error);
        }
    } catch (error) {
        console.error('[DASHBOARD_EXECUTIVO] Erro ao carregar KPIs:', error);
    }
}

/**
 * Load dashboard KPIs with retry and cache fallback
 */
async function loadDashboardKPIsWithRetry(maxRetries = 2) {
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
        try {
            console.log(`[DASHBOARD_EXECUTIVO] Carregando KPIs (tentativa ${attempt}/${maxRetries})...`);
            
            const queryString = buildFilterQueryString();
            const response = await fetch(`/dashboard-executivo/api/kpis?${queryString}`);
            const result = await response.json();
            
            if (result.success && result.kpis) {
                console.log('[DASHBOARD_EXECUTIVO] KPIs carregados com sucesso');
                dashboardCache.set('kpis', result.kpis);
                updateDashboardKPIs(result.kpis);
                return;
            } else {
                throw new Error(result.error || 'KPIs não encontrados');
            }
            
        } catch (error) {
            console.warn(`[DASHBOARD_EXECUTIVO] Tentativa ${attempt} de KPIs falhou:`, error.message);
            
            if (attempt === maxRetries) {
                // Tentar usar cache como fallback
                const cachedKpis = dashboardCache.get('kpis');
                if (cachedKpis) {
                    console.log('[DASHBOARD_EXECUTIVO] Usando KPIs do cache como fallback');
                    updateDashboardKPIs(cachedKpis);
                    return;
                }
                throw error;
            }
            
            await new Promise(resolve => setTimeout(resolve, 1000 * attempt));
        }
    }
}

/**
 * Load dashboard charts
 */
async function loadDashboardCharts() {
    try {
        console.log('[DASHBOARD_EXECUTIVO] Carregando gráficos...');
        
        const queryString = buildFilterQueryString();
        const response = await fetch(`/dashboard-executivo/api/charts?${queryString}`);
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
 * Load dashboard charts with cache
 */
async function loadDashboardChartsWithCache() {
    try {
        console.log('[DASHBOARD_EXECUTIVO] Carregando gráficos com cache...');
        
        const queryString = buildFilterQueryString();
        const response = await fetch(`/dashboard-executivo/api/charts?${queryString}`);
        const result = await response.json();
        
        if (result.success) {
            dashboardCache.set('charts', result.charts);
            createDashboardChartsWithValidation(result.charts);
        } else {
            console.error('[DASHBOARD_EXECUTIVO] Erro ao carregar gráficos:', result.error);
        }
    } catch (error) {
        console.error('[DASHBOARD_EXECUTIVO] Erro ao carregar gráficos:', error);
    }
}

/**
 * Load dashboard charts with retry and cache fallback
 */
async function loadDashboardChartsWithRetry(maxRetries = 2) {
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
        try {
            console.log(`[DASHBOARD_EXECUTIVO] Carregando gráficos (tentativa ${attempt}/${maxRetries})...`);
            
            const queryString = buildFilterQueryString();
            const response = await fetch(`/dashboard-executivo/api/charts?${queryString}`);
            const result = await response.json();
            
            if (result.success && result.charts) {
                console.log('[DASHBOARD_EXECUTIVO] Gráficos carregados com sucesso');
                dashboardCache.set('charts', result.charts);
                createDashboardChartsWithValidation(result.charts);
                return;
            } else {
                throw new Error(result.error || 'Gráficos não encontrados');
            }
            
        } catch (error) {
            console.warn(`[DASHBOARD_EXECUTIVO] Tentativa ${attempt} de gráficos falhou:`, error.message);
            
            if (attempt === maxRetries) {
                // Tentar usar cache como fallback
                const cachedCharts = dashboardCache.get('charts');
                if (cachedCharts) {
                    console.log('[DASHBOARD_EXECUTIVO] Usando gráficos do cache como fallback');
                    createDashboardChartsWithValidation(cachedCharts);
                    return;
                }
                
                // Se não há cache, criar gráficos vazios para evitar telas em branco
                createEmptyCharts();
                throw error;
            }
            
            await new Promise(resolve => setTimeout(resolve, 1000 * attempt));
        }
    }
}

/**
 * Load recent operations
 */
async function loadRecentOperations() {
    try {
        console.log('[DASHBOARD_EXECUTIVO] Carregando operações recentes...');
        
        const queryString = buildFilterQueryString();
        const response = await fetch(`/dashboard-executivo/api/recent-operations?${queryString}`);
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
 * Load recent operations with cache
 */
async function loadRecentOperationsWithCache() {
    try {
        console.log('[DASHBOARD_EXECUTIVO] Carregando operações recentes com cache...');
        
        const queryString = buildFilterQueryString();
        const response = await fetch(`/dashboard-executivo/api/recent-operations?${queryString}`);
        const result = await response.json();
        
        if (result.success) {
            dashboardCache.set('operations', result.operations);
            updateRecentOperationsTable(result.operations);
        } else {
            console.error('[DASHBOARD_EXECUTIVO] Erro ao carregar operações:', result.error);
        }
    } catch (error) {
        console.error('[DASHBOARD_EXECUTIVO] Erro ao carregar operações:', error);
    }
}

/**
 * Load recent operations with retry and cache fallback
 */
async function loadRecentOperationsWithRetry(maxRetries = 2) {
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
        try {
            console.log(`[DASHBOARD_EXECUTIVO] Carregando operações (tentativa ${attempt}/${maxRetries})...`);
            
            const queryString = buildFilterQueryString();
            const response = await fetch(`/dashboard-executivo/api/recent-operations?${queryString}`);
            const result = await response.json();
            
            if (result.success && result.operations) {
                console.log(`[DASHBOARD_EXECUTIVO] Operações carregadas: ${result.operations.length} registros`);
                dashboardCache.set('operations', result.operations);
                updateRecentOperationsTable(result.operations);
                return;
            } else {
                throw new Error(result.error || 'Operações não encontradas');
            }
            
        } catch (error) {
            console.warn(`[DASHBOARD_EXECUTIVO] Tentativa ${attempt} de operações falhou:`, error.message);
            
            if (attempt === maxRetries) {
                // Tentar usar cache como fallback
                const cachedOperations = dashboardCache.get('operations');
                if (cachedOperations) {
                    console.log('[DASHBOARD_EXECUTIVO] Usando operações do cache como fallback');
                    updateRecentOperationsTable(cachedOperations);
                    return;
                }
                
                // Se não há cache, mostrar tabela vazia
                updateRecentOperationsTable([]);
                throw error;
            }
            
            await new Promise(resolve => setTimeout(resolve, 1000 * attempt));
        }
    }
}

/**
 * Load filter options with retry and cache fallback
 */
async function loadFilterOptionsWithRetry(maxRetries = 2) {
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
        try {
            console.log(`[DASHBOARD_EXECUTIVO] Carregando filtros (tentativa ${attempt}/${maxRetries})...`);
            
            const response = await fetch('/dashboard-executivo/api/filter-options');
            const result = await response.json();
            
            if (result.success && result.options) {
                console.log('[DASHBOARD_EXECUTIVO] Opções de filtros carregadas:', {
                    materiais: result.options.materiais?.length || 0,
                    clientes: result.options.clientes?.length || 0,
                    modais: result.options.modais?.length || 0,
                    canais: result.options.canais?.length || 0
                });
                
                dashboardCache.set('filterOptions', result.options);
                populateFilterOptions(result.options);
                return;
            } else {
                throw new Error(result.error || 'Opções de filtros não encontradas');
            }
            
        } catch (error) {
            console.warn(`[DASHBOARD_EXECUTIVO] Tentativa ${attempt} de filtros falhou:`, error.message);
            
            if (attempt === maxRetries) {
                // Tentar usar cache como fallback
                const cachedOptions = dashboardCache.get('filterOptions');
                if (cachedOptions) {
                    console.log('[DASHBOARD_EXECUTIVO] Usando filtros do cache como fallback');
                    populateFilterOptions(cachedOptions);
                    return;
                }
                
                // Se não há cache, criar filtros vazios
                populateFilterOptions({
                    materiais: [],
                    clientes: [],
                    modais: [],
                    canais: []
                });
                throw error;
            }
            
            await new Promise(resolve => setTimeout(resolve, 1000 * attempt));
        }
    }
}

/**
 * Update dashboard KPIs
 */
function updateDashboardKPIs(kpis) {
    console.log('[DASHBOARD_EXECUTIVO] Atualizando KPIs...', kpis);
    
    // Update KPI values com nova estrutura
    updateKPIValue('kpi-total-processos', formatNumber(kpis.total_processos));
    updateKPIValue('kpi-processos-abertos', formatNumber(kpis.processos_abertos || 0));
    updateKPIValue('kpi-processos-fechados', formatNumber(kpis.processos_fechados || 0));
    updateKPIValue('kpi-chegando-mes', formatNumber(kpis.chegando_mes));
    updateKPIValue('kpi-chegando-mes-custo', formatCurrencyCompact(kpis.chegando_mes_custo));
    updateKPIValue('kpi-chegando-semana', formatNumber(kpis.chegando_semana));
    updateKPIValue('kpi-chegando-semana-custo', formatCurrencyCompact(kpis.chegando_semana_custo));
    updateKPIValue('kpi-Agd-embarque', formatNumber(kpis.aguardando_embarque || 0));
    updateKPIValue('kpi-Agd-chegada', formatNumber(kpis.aguardando_chegada || 0));
    updateKPIValue('kpi-Agd-liberacao', formatNumber(kpis.aguardando_liberacao || 0));
    updateKPIValue('kpi-agd-entrega', formatNumber(kpis.agd_entrega || 0));
    updateKPIValue('kpi-Agd-fechamento', formatNumber(kpis.aguardando_fechamento || 0));
    updateKPIValue('kpi-total-despesas', formatCurrencyCompact(kpis.total_despesas));
    updateKPIValue('kpi-ticket-medio', formatCurrencyCompact(kpis.ticket_medio));
    // Removidos: kpi-transit-time, kpi-proc-mes, kpi-proc-semana
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
    
    // NOVO: Create principais materiais table (substitui o gráfico material)
    if (charts.principais_materiais) {
        console.log('[DASHBOARD_EXECUTIVO] Criando tabela de principais materiais...');
        createPrincipaisMateriaisTable(charts.principais_materiais);
    }
    
    // Keep material chart for transit time (pode ser removido depois se não for usado)
    if (charts.material) {
        console.log('[DASHBOARD_EXECUTIVO] Criando gráfico material...');
        createMaterialChart(charts.material);
    }
}

/**
 * Create dashboard charts with validation and error handling
 */
function createDashboardChartsWithValidation(charts) {
    if (!charts) {
        console.error('[DASHBOARD_EXECUTIVO] Dados de gráficos não fornecidos');
        return;
    }
    
    console.log('[DASHBOARD_EXECUTIVO] Criando gráficos com validação...', charts);
    
    try {
        // Verificar se Chart.js está disponível
        if (typeof Chart === 'undefined') {
            console.error('[DASHBOARD_EXECUTIVO] Chart.js não está disponível');
            return;
        }
        
        // Create monthly chart with validation
        if (charts.monthly && charts.monthly.labels && charts.monthly.datasets) {
            console.log('[DASHBOARD_EXECUTIVO] Criando gráfico mensal...');
            createMonthlyChartWithValidation(charts.monthly);
        } else {
            console.warn('[DASHBOARD_EXECUTIVO] Dados do gráfico mensal inválidos ou ausentes');
        }
        
        // Create status chart with validation
        if (charts.status && charts.status.labels && charts.status.data) {
            console.log('[DASHBOARD_EXECUTIVO] Criando gráfico de status...');
            createStatusChartWithValidation(charts.status);
        } else {
            console.warn('[DASHBOARD_EXECUTIVO] Dados do gráfico de status inválidos ou ausentes');
        }
        
        // Create grouped modal chart with validation
        if (charts.grouped_modal && charts.grouped_modal.labels && charts.grouped_modal.datasets) {
            console.log('[DASHBOARD_EXECUTIVO] Criando gráfico modal...');
            createGroupedModalChartWithValidation(charts.grouped_modal);
        } else {
            console.warn('[DASHBOARD_EXECUTIVO] Dados do gráfico modal inválidos ou ausentes');
        }
        
        // Create URF chart with validation
        if (charts.urf && charts.urf.labels && charts.urf.data) {
            console.log('[DASHBOARD_EXECUTIVO] Criando gráfico URF...');
            createUrfChartWithValidation(charts.urf);
        } else {
            console.warn('[DASHBOARD_EXECUTIVO] Dados do gráfico URF inválidos ou ausentes');
        }
        
        // Create principais materiais table with validation
        if (charts.principais_materiais && charts.principais_materiais.data) {
            console.log('[DASHBOARD_EXECUTIVO] Criando tabela de principais materiais...');
            createPrincipaisMateriaisTableWithValidation(charts.principais_materiais);
        } else {
            console.warn('[DASHBOARD_EXECUTIVO] Dados da tabela de materiais inválidos ou ausentes');
        }
        
        // CORREÇÃO: Material só tem TABELA, não gráfico
        // Removido createMaterialChartWithValidation pois canvas material-chart não existe no HTML
        
        console.log('[DASHBOARD_EXECUTIVO] Todos os gráficos foram criados com sucesso');
        
    } catch (error) {
        console.error('[DASHBOARD_EXECUTIVO] Erro ao criar gráficos:', error);
        showError('Erro ao criar gráficos. Tente recarregar a página.');
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
                    type: 'line', // Força o tipo como linha
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
                type: 'line', // Força o tipo como linha
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
                        ticks: {
                            display: false // Remove valores do eixo Y
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
                        ticks: {
                            display: false // Remove valores do eixo Y1
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
 * Create monthly evolution chart with validation
 */
function createMonthlyChartWithValidation(data) {
    try {
        // Validação robusta dos dados
        if (!data || !data.labels || !Array.isArray(data.labels) || data.labels.length === 0) {
            console.warn('[DASHBOARD_EXECUTIVO] Dados do gráfico mensal inválidos - labels ausentes ou vazios');
            return;
        }
        
        if (!data.datasets || !Array.isArray(data.datasets) || data.datasets.length === 0) {
            console.warn('[DASHBOARD_EXECUTIVO] Dados do gráfico mensal inválidos - datasets ausentes ou vazios');
            return;
        }
        
        // Verificar se cada dataset tem dados válidos
        for (let i = 0; i < data.datasets.length; i++) {
            const dataset = data.datasets[i];
            if (!dataset.data || !Array.isArray(dataset.data) || dataset.data.length === 0) {
                console.warn(`[DASHBOARD_EXECUTIVO] Dataset ${i} do gráfico mensal tem dados inválidos`);
                return;
            }
        }
        
        console.log('[DASHBOARD_EXECUTIVO] Dados do gráfico mensal validados - criando gráfico...');
        createMonthlyChart(data);
        
    } catch (error) {
        console.error('[DASHBOARD_EXECUTIVO] Erro na validação do gráfico mensal:', error);
    }
}

/**
 * Create status chart with validation
 */
function createStatusChartWithValidation(data) {
    try {
        if (!data || !data.labels || !Array.isArray(data.labels) || data.labels.length === 0) {
            console.warn('[DASHBOARD_EXECUTIVO] Dados do gráfico de status inválidos - labels ausentes ou vazios');
            return;
        }
        
        if (!data.data || !Array.isArray(data.data) || data.data.length === 0) {
            console.warn('[DASHBOARD_EXECUTIVO] Dados do gráfico de status inválidos - data ausente ou vazio');
            return;
        }
        
        console.log('[DASHBOARD_EXECUTIVO] Dados do gráfico de status validados - criando gráfico...');
        createStatusChart(data);
        
    } catch (error) {
        console.error('[DASHBOARD_EXECUTIVO] Erro na validação do gráfico de status:', error);
    }
}

/**
 * Create grouped modal chart with validation
 */
function createGroupedModalChartWithValidation(data) {
    try {
        if (!data || !data.labels || !Array.isArray(data.labels) || data.labels.length === 0) {
            console.warn('[DASHBOARD_EXECUTIVO] Dados do gráfico modal inválidos - labels ausentes ou vazios');
            return;
        }
        
        if (!data.datasets || !Array.isArray(data.datasets) || data.datasets.length === 0) {
            console.warn('[DASHBOARD_EXECUTIVO] Dados do gráfico modal inválidos - datasets ausentes ou vazios');
            return;
        }
        
        console.log('[DASHBOARD_EXECUTIVO] Dados do gráfico modal validados - criando gráfico...');
        createGroupedModalChart(data);
        
    } catch (error) {
        console.error('[DASHBOARD_EXECUTIVO] Erro na validação do gráfico modal:', error);
    }
}

/**
 * Create URF chart with validation
 */
function createUrfChartWithValidation(data) {
    try {
        if (!data || !data.labels || !Array.isArray(data.labels) || data.labels.length === 0) {
            console.warn('[DASHBOARD_EXECUTIVO] Dados do gráfico URF inválidos - labels ausentes ou vazios');
            return;
        }
        
        if (!data.data || !Array.isArray(data.data) || data.data.length === 0) {
            console.warn('[DASHBOARD_EXECUTIVO] Dados do gráfico URF inválidos - data ausente ou vazio');
            return;
        }
        
        console.log('[DASHBOARD_EXECUTIVO] Dados do gráfico URF validados - criando gráfico...');
        createUrfChart(data);
        
    } catch (error) {
        console.error('[DASHBOARD_EXECUTIVO] Erro na validação do gráfico URF:', error);
    }
}

/**
 * Create material chart with validation
 */
function createMaterialChartWithValidation(data) {
    try {
        if (!data || !data.labels || !Array.isArray(data.labels) || data.labels.length === 0) {
            console.warn('[DASHBOARD_EXECUTIVO] Dados do gráfico de material inválidos - labels ausentes ou vazios');
            return;
        }
        
        if (!data.data || !Array.isArray(data.data) || data.data.length === 0) {
            console.warn('[DASHBOARD_EXECUTIVO] Dados do gráfico de material inválidos - data ausente ou vazio');
            return;
        }
        
        console.log('[DASHBOARD_EXECUTIVO] Dados do gráfico de material validados - criando gráfico...');
        createMaterialChart(data);
        
    } catch (error) {
        console.error('[DASHBOARD_EXECUTIVO] Erro na validação do gráfico de material:', error);
    }
}

/**
 * Create principais materiais table with validation
 */
function createPrincipaisMateriaisTableWithValidation(data) {
    try {
        if (!data || !data.data || !Array.isArray(data.data)) {
            console.warn('[DASHBOARD_EXECUTIVO] Dados da tabela de materiais inválidos - data ausente ou não é array');
            
            // Criar tabela vazia com mensagem
            const tableBody = document.querySelector('#principais-materiais-table tbody');
            if (tableBody) {
                tableBody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">Nenhum material encontrado</td></tr>';
            }
            return;
        }
        
        console.log('[DASHBOARD_EXECUTIVO] Dados da tabela de materiais validados - criando tabela...');
        createPrincipaisMateriaisTable(data);
        
    } catch (error) {
        console.error('[DASHBOARD_EXECUTIVO] Erro na validação da tabela de materiais:', error);
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
        // Ajustar datasets para garantir ambos como barras, cada um em seu eixo
        let datasets = data.datasets || [];
        if (datasets.length === 2) {
            // Dataset 0: Processos, Dataset 1: Custo Total
            datasets = [
                {
                    ...datasets[0],
                    type: 'bar',
                    yAxisID: 'y',
                    backgroundColor: '#007bff', // azul
                    borderColor: '#007bff',
                    datalabels: { display: true }
                },
                {
                    ...datasets[1],
                    type: 'bar',
                    yAxisID: 'y1',
                    backgroundColor: '#ff9800', // laranja
                    borderColor: '#ff9800',
                    datalabels: { display: true }
                }
            ];
        }
        dashboardCharts.groupedModal = new Chart(ctx, {
            type: 'bar',
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
                        ticks: {
                            display: false // Remove valores do eixo Y
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
                        ticks: {
                            display: false // Remove valores do eixo Y1
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
        // CORREÇÃO: Incluir filtros na URL do gráfico mensal
        const filterQueryString = buildFilterQueryString();
        const separator = filterQueryString ? '&' : '';
        const url = `/dashboard-executivo/api/monthly-chart?granularidade=${granularidade}${separator}${filterQueryString}`;
        
        console.log(`[DASHBOARD_EXECUTIVO] Carregando gráfico ${granularidade} com filtros:`, url);
        
        const response = await fetch(url);
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
 * Ajustar cabeçalhos e colunas da tabela baseado nos dados
 */
function adjustTableHeadersAndColumns(operations) {
    // Verificar se há clientes KINGSPAN nos dados
    const hasKingspanClients = operations.some(op => 
        op.importador && op.importador.toUpperCase().includes('KING')
    );
    
    console.log('[DASHBOARD_EXECUTIVO] Clientes KINGSPAN encontrados:', hasKingspanClients);
    
    // Encontrar o cabeçalho da coluna Material
    const table = document.getElementById('recent-operations-table');
    if (!table) return;
    
    const materialHeader = Array.from(table.querySelectorAll('thead th')).find(th => 
        th.textContent.trim() === 'Material'
    );
    
    if (materialHeader) {
        // Mostrar/ocultar coluna Material baseado na presença de clientes KINGSPAN
        materialHeader.style.display = hasKingspanClients ? '' : 'none';
        console.log('[DASHBOARD_EXECUTIVO] Coluna Material:', hasKingspanClients ? 'mostrada' : 'oculta');
    }
}

/**
 * Update recent operations table
 */
function updateRecentOperationsTable(operations) {
    console.log('[DASHBOARD_EXECUTIVO] Atualizando tabela com', operations.length, 'operações');
    
    // Ajustar cabeçalhos e colunas baseado nos dados
    adjustTableHeadersAndColumns(operations);
    
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
        
        // Invalidar cache antes de recarregar
        dashboardCache.invalidate();
        console.log('[DASHBOARD_EXECUTIVO] Cache invalidado - recarregando dados...');
        
        await loadInitialDataWithCache();
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
 * Force refresh específico do Dashboard Executivo
 * Busca dados frescos diretamente do banco, ignorando cache
 */
async function forceRefreshDashboard() {
    try {
        console.log('[DASHBOARD_EXECUTIVO] === INICIANDO FORCE REFRESH ===');
        showLoading(true);
        
        // Mostrar mensagem específica para force refresh
        const loadingText = document.querySelector('.loading-spinner p');
        if (loadingText) {
            loadingText.textContent = 'Buscando dados atualizados do banco...';
        }
        
        // 1. Chamar endpoint específico de force refresh do dashboard
        console.log('[DASHBOARD_EXECUTIVO] Chamando force refresh específico...');
        
        const response = await fetch('/dashboard-executivo/api/force-refresh', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            }
        });
        
        if (!response.ok) {
            throw new Error(`Erro HTTP: ${response.status}`);
        }
        
        const result = await response.json();
        
        if (!result.success) {
            throw new Error(result.error || 'Erro desconhecido no force refresh');
        }
        
        console.log('[DASHBOARD_EXECUTIVO] Force refresh bem-sucedido:', result);
        
        // 2. Invalidar cache local
        dashboardCache.invalidate();
        
        // 3. Recarregar todos os componentes com dados frescos
        await loadInitialDataWithCache();
        
        updateLastUpdate();
        showLoading(false);
        
        // Mostrar feedback detalhado do force refresh
        const message = `
            ✅ Cache atualizado com dados frescos!<br>
            📊 ${result.total_records} registros processados<br>
            💰 Custo total: R$ ${(result.total_custo || 0).toLocaleString('pt-BR', {minimumFractionDigits: 2})}
        `;
        
        if (result.processo_6555?.encontrado) {
            const custoProcesso = result.processo_6555.custo_total || 0;
            showSuccess(`${message}<br>🎯 Processo 6555: R$ ${custoProcesso.toLocaleString('pt-BR', {minimumFractionDigits: 2})}`);
        } else {
            showSuccess(message);
        }
        
    } catch (error) {
        console.error('[DASHBOARD_EXECUTIVO] Erro no force refresh:', error);
        showError('Erro ao forçar atualização: ' + error.message);
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
 * Show/hide loading overlay - Integrado com sistema unificado
 */
function showLoading(show) {
    // Sistema unificado gerencia loading - manter apenas para compatibilidade
    console.log('[DASHBOARD_EXECUTIVO] showLoading chamado:', show, '- gerenciado por sistema unificado');
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
 * Show warning message to user
 */
function showWarningMessage(message) {
    console.warn('[DASHBOARD_EXECUTIVO] Warning:', message);
    
    // Criar elemento de aviso se não existir
    let warningDiv = document.getElementById('dashboard-warning');
    if (!warningDiv) {
        warningDiv = document.createElement('div');
        warningDiv.id = 'dashboard-warning';
        warningDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            color: #856404;
            padding: 12px 20px;
            border-radius: 5px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            z-index: 9999;
            max-width: 400px;
            font-size: 14px;
        `;
        document.body.appendChild(warningDiv);
    }
    
    warningDiv.innerHTML = `
        <strong>⚠️ Aviso:</strong> ${message}
        <button onclick="this.parentElement.remove()" style="float: right; background: none; border: none; font-size: 16px; cursor: pointer; margin-left: 10px;">×</button>
    `;
    
    // Auto remover após 8 segundos
    setTimeout(() => {
        if (warningDiv && warningDiv.parentElement) {
            warningDiv.remove();
        }
    }, 8000);
}

/**
 * Attempt cache recovery as last resort
 */
async function attemptCacheRecovery() {
    console.log('[DASHBOARD_EXECUTIVO] Tentando recuperação via cache...');
    
    try {
        // Tentar recuperar cada componente do cache
        const cachedKpis = dashboardCache.get('kpis');
        const cachedCharts = dashboardCache.get('charts');
        const cachedOperations = dashboardCache.get('operations');
        const cachedFilterOptions = dashboardCache.get('filterOptions');
        
        let recoveredComponents = 0;
        
        if (cachedKpis) {
            updateDashboardKPIs(cachedKpis);
            recoveredComponents++;
            console.log('[DASHBOARD_EXECUTIVO] ✅ KPIs recuperados do cache');
        }
        
        if (cachedCharts) {
            createDashboardChartsWithValidation(cachedCharts);
            recoveredComponents++;
            console.log('[DASHBOARD_EXECUTIVO] ✅ Gráficos recuperados do cache');
        } else {
            createEmptyCharts();
            console.log('[DASHBOARD_EXECUTIVO] ⚠️ Criados gráficos vazios');
        }
        
        if (cachedOperations) {
            updateRecentOperationsTable(cachedOperations);
            recoveredComponents++;
            console.log('[DASHBOARD_EXECUTIVO] ✅ Operações recuperadas do cache');
        } else {
            updateRecentOperationsTable([]);
            console.log('[DASHBOARD_EXECUTIVO] ⚠️ Criada tabela vazia');
        }
        
        if (cachedFilterOptions) {
            populateFilterOptions(cachedFilterOptions);
            recoveredComponents++;
            console.log('[DASHBOARD_EXECUTIVO] ✅ Filtros recuperados do cache');
        } else {
            populateFilterOptions({
                materiais: [],
                clientes: [],
                modais: [],
                canais: []
            });
            console.log('[DASHBOARD_EXECUTIVO] ⚠️ Criados filtros vazios');
        }
        
        if (recoveredComponents > 0) {
            showWarningMessage(`Dashboard carregado com dados em cache. ${recoveredComponents} componente(s) recuperado(s).`);
        } else {
            showError('Não foi possível carregar os dados. Tente recarregar a página.');
        }
        
    } catch (error) {
        console.error('[DASHBOARD_EXECUTIVO] Erro na recuperação via cache:', error);
        showError('Erro ao carregar dashboard. Recarregue a página.');
    }
}

/**
 * Create empty charts to prevent blank spaces
 */
function createEmptyCharts() {
    console.log('[DASHBOARD_EXECUTIVO] Criando gráficos vazios...');
    
    const emptyCharts = {
        monthly: {
            labels: ['Sem dados'],
            datasets: [{
                label: 'Processos',
                data: [0],
                backgroundColor: '#e9ecef',
                borderColor: '#dee2e6'
            }]
        },
        status: {
            labels: ['Sem dados'],
            data: [1]
        },
        grouped_modal: {
            labels: ['Sem dados'],
            datasets: [{
                label: 'Processos',
                data: [0],
                backgroundColor: '#e9ecef'
            }]
        },
        urf: {
            labels: ['Sem dados'],
            data: [1]
        },
        principais_materiais: {
            data: []
        }
    };
    
    createDashboardChartsWithValidation(emptyCharts);
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
    
    // LOG ESPECÍFICO PARA CAMPOS DE CUSTO
    console.log('[DASHBOARD_EXECUTIVO] === ANÁLISE DE CUSTOS ===');
    console.log('[DASHBOARD_EXECUTIVO] custo_total:', operation.custo_total);
    console.log('[DASHBOARD_EXECUTIVO] custo_total_view:', operation.custo_total_view);
    console.log('[DASHBOARD_EXECUTIVO] custo_total_original:', operation.custo_total_original);
    console.log('[DASHBOARD_EXECUTIVO] despesas_processo tipo:', typeof operation.despesas_processo);
    console.log('[DASHBOARD_EXECUTIVO] despesas_processo length:', operation.despesas_processo ? operation.despesas_processo.length : 'N/A');
    
    // LOG ESPECÍFICO PARA PROCESSO 6555
    if (operation.ref_unique && operation.ref_unique.includes('6555')) {
        console.log('[DASHBOARD_EXECUTIVO] *** DETECTADO PROCESSO 6555 NO MODAL ***');
        console.log('[DASHBOARD_EXECUTIVO] QUAL CAMPO ESTÁ SENDO USADO NO MODAL?');
        console.log('[DASHBOARD_EXECUTIVO] operation.custo_total:', operation.custo_total);
        console.log('[DASHBOARD_EXECUTIVO] operation.custo_total_view:', operation.custo_total_view);
        console.log('[DASHBOARD_EXECUTIVO] operation.custo_total_original:', operation.custo_total_original);
        
        if (operation.despesas_processo && Array.isArray(operation.despesas_processo)) {
            console.log('[DASHBOARD_EXECUTIVO] Despesas do processo 6555:');
            let total_manual = 0;
            operation.despesas_processo.forEach((despesa, i) => {
                const valor = parseFloat(despesa.valor_custo) || 0;
                total_manual += valor;
                console.log(`[DASHBOARD_EXECUTIVO] ${i+1}. ${despesa.categoria_custo}: R$ ${valor.toFixed(2)}`);
            });
            console.log('[DASHBOARD_EXECUTIVO] Total manual calculado:', total_manual.toFixed(2));
        }
    }
    
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
    
    // NOVO: Usar status_timeline ou fallback para status_macro
    const statusTimeline = operation.status_timeline || operation.status_macro;
    console.log('[TIMELINE_DEBUG] Status timeline original:', operation.status_timeline);
    console.log('[TIMELINE_DEBUG] Status macro fallback:', operation.status_macro);
    console.log('[TIMELINE_DEBUG] Status final usado:', statusTimeline);
    
    updateProcessTimelineFromStatusTimeline(statusTimeline);
    
    // Update general information
    updateElementValue('detail-ref-unique', operation.ref_unique);
    updateElementValue('detail-ref-importador', operation.ref_importador);
    updateElementValue('detail-data-abertura', operation.data_abertura);
    updateElementValue('detail-importador', operation.importador);
    updateElementValue('detail-exportador', operation.exportador_fornecedor);
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
    updateContainerField(operation.container); // NOVO: Função para processar containers múltiplos
    updateElementValue('detail-data-embarque', operation.data_embarque);
    updateElementValue('detail-data-chegada', operation.data_chegada);
    updateElementValue('detail-data-fechamento', operation.data_fechamento); // NOVA data
    updateElementValue('detail-transit-time', operation.transit_time_real ? operation.transit_time_real + ' dias' : '-');
    updateElementValue('detail-peso-bruto', operation.peso_bruto ? formatNumber(operation.peso_bruto) + ' Kg' : '-');
    
    // Update customs information
    updateElementValue('detail-numero-di', operation.numero_di);
    updateElementValue('detail-data-registro', operation.data_registro);
    updateElementValue('detail-canal', operation.canal, true);
    updateElementValue('detail-data-desembaraco', operation.data_desembaraco);
    updateElementValue('detail-urf-entrada', operation.urf_entrada_normalizado || operation.urf_entrada);
    updateElementValue('detail-urf-despacho', operation.urf_despacho_normalizado || operation.urf_despacho);
    
    // Update financial summary using new category-based system
    updateFinancialSummary(operation);
    
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
 * Update process timeline based on status_timeline from database
 */
function updateProcessTimelineFromStatusTimeline(statusTimeline) {
    console.log('[TIMELINE_DEBUG] Atualizando timeline com status_timeline:', statusTimeline);
    
    const timelineSteps = document.querySelectorAll('.timeline-step');
    console.log('[TIMELINE_DEBUG] Steps encontrados:', timelineSteps.length);
    
    // Resetar todos os steps
    timelineSteps.forEach(step => {
        step.classList.remove('completed', 'active');
    });
    
    if (!statusTimeline) {
        console.log('[TIMELINE_DEBUG] Status timeline vazio - nenhum step ativo');
        return;
    }
    
    // Mapear status_timeline para steps (remover número do início e pontos)
    const timelineMap = {
        'Aberto': 1,
        'Abertura': 1,
        'Processo Aberto': 1,
        'Embarque': 2, 
        'Embarcado': 2,
        'Chegada': 3,
        'Chegou': 3,
        'Registro': 4,
        'Registrado': 4,
        'DI Registrada': 4,
        'Desembaraço': 5,
        'Desembaracado': 5,
        'Processo Concluído': 5,
        'Finalizado': 5,
        'Liberado': 5
    };
    
    // Extrair o nome do status (remover número, pontos e traços)
    let statusName = statusTimeline.replace(/^\d+[\.\-\s]*/, '').trim().toUpperCase();
    console.log(`[TIMELINE_DEBUG] Status original: "${statusTimeline}"`);
    console.log(`[TIMELINE_DEBUG] Status limpo: "${statusName}"`);
    
    // Buscar correspondência no mapeamento (case insensitive)
    let currentStep = null;
    for (const [key, step] of Object.entries(timelineMap)) {
        if (statusName.includes(key.toUpperCase()) || key.toUpperCase().includes(statusName)) {
            currentStep = step;
            console.log(`[TIMELINE_DEBUG] Mapeamento encontrado: "${key}" -> Step ${step}`);
            break;
        }
    }
    
    // Se não encontrou correspondência, tentar extrair número diretamente
    if (!currentStep) {
        const numeroMatch = statusTimeline.match(/^(\d+)/);
        if (numeroMatch) {
            const numero = parseInt(numeroMatch[1]);
            if (numero >= 1 && numero <= 10) {
                // Mapear números para steps (1-5 são diretos, 6-10 são status 5)
                currentStep = numero <= 5 ? numero : 5;
                console.log(`[TIMELINE_DEBUG] Mapeamento por número: ${numero} -> Step ${currentStep}`);
            }
        }
    }
    
    console.log(`[TIMELINE_DEBUG] Step final: ${currentStep}`);
    
    if (currentStep) {
        timelineSteps.forEach((step, index) => {
            const stepNumber = index + 1;
            
            if (stepNumber < currentStep) {
                step.classList.add('completed');
                console.log(`[TIMELINE_DEBUG] Step ${stepNumber} marcado como completed`);
            } else if (stepNumber === currentStep) {
                step.classList.add('active');
                console.log(`[TIMELINE_DEBUG] Step ${stepNumber} marcado como active`);
            }
        });
    } else {
        console.log(`[TIMELINE_DEBUG] Nenhum mapeamento encontrado para: "${statusTimeline}"`);
    }
}

/**
 * Update container field with support for multiple containers
 */
function updateContainerField(containerValue) {
    const containerElement = document.getElementById('detail-container');
    
    if (!containerElement) {
        console.warn('[MODAL_DEBUG] Elemento detail-container não encontrado');
        return;
    }
    
    if (!containerValue || containerValue.trim() === '') {
        containerElement.innerHTML = '-';
        return;
    }
    
    // Verificar se há múltiplos containers (separados por vírgula)
    const containers = containerValue.split(',').map(c => c.trim()).filter(c => c);
    
    if (containers.length === 1) {
        // Um único container
        containerElement.innerHTML = `<span class="container-tag" title="${containers[0]}">${containers[0]}</span>`;
    } else {
        // Múltiplos containers
        const containerTags = containers.map(container => 
            `<span class="container-tag" title="${container}">${container}</span>`
        ).join('');
        
        containerElement.innerHTML = containerTags;
        console.log(`[MODAL_DEBUG] ${containers.length} containers processados:`, containers);
    }
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
 * Processar despesas por categoria do campo JSON despesas_processo
 */
function processExpensesByCategory(despesasProcesso) {
    try {
        console.log('[DASHBOARD_EXECUTIVO] === INÍCIO processExpensesByCategory ===');
        console.log('[DASHBOARD_EXECUTIVO] Entrada - despesasProcesso:', despesasProcesso);
        console.log('[DASHBOARD_EXECUTIVO] Tipo:', typeof despesasProcesso);
        console.log('[DASHBOARD_EXECUTIVO] É array:', Array.isArray(despesasProcesso));
        
        if (!despesasProcesso || !Array.isArray(despesasProcesso)) {
            console.warn('[DASHBOARD_EXECUTIVO] Despesas processo não é um array válido:', despesasProcesso);
            return {
                categorias: {},
                total: 0
            };
        }

        const categorias = {};
        let total = 0;

        console.log('[DASHBOARD_EXECUTIVO] Processando', despesasProcesso.length, 'despesas...');

        despesasProcesso.forEach((despesa, index) => {
            console.log(`[DASHBOARD_EXECUTIVO] Despesa ${index + 1}:`, despesa);
            
            const categoria = despesa.categoria_custo || 'Outros';
            const valorStr = despesa.valor_custo;
            const valor = parseFloat(valorStr) || 0;
            
            console.log(`[DASHBOARD_EXECUTIVO] Processando: categoria="${categoria}", valorStr="${valorStr}", valor=${valor}`);

            if (!categorias[categoria]) {
                categorias[categoria] = 0;
            }

            categorias[categoria] += valor;
            total += valor;
            
            console.log(`[DASHBOARD_EXECUTIVO] Categoria "${categoria}" agora tem: R$ ${categorias[categoria].toFixed(2)}`);
            console.log(`[DASHBOARD_EXECUTIVO] Total acumulado: R$ ${total.toFixed(2)}`);
        });

        console.log('[DASHBOARD_EXECUTIVO] Resultado final - categorias:', categorias);
        console.log('[DASHBOARD_EXECUTIVO] Resultado final - total:', total);
        console.log('[DASHBOARD_EXECUTIVO] === FIM processExpensesByCategory ===');

        return {
            categorias,
            total
        };

    } catch (error) {
        console.error('[DASHBOARD_EXECUTIVO] Erro ao processar despesas por categoria:', error);
        return {
            categorias: {},
            total: 0
        };
    }
}

/**
 * Gerar HTML para o novo resumo financeiro
 */
function generateFinancialSummaryHTML(expenseData, valorCif = 0) {
    try {
        const { categorias, total } = expenseData;

        let html = `
            <div class="info-item valor-cif-item">
                <label>Valor CIF (R$):</label>
                <span>${formatCurrency(valorCif)}</span>
            </div>
        `;

        // Ordenar categorias por valor (maior para menor)
        const categoriasOrdenadas = Object.entries(categorias)
            .sort(([,a], [,b]) => b - a);

        categoriasOrdenadas.forEach(([categoria, valor]) => {
            html += `
                <div class="info-item">
                    <label>${categoria} (R$):</label>
                    <span>${formatCurrency(valor)}</span>
                </div>
            `;
        });

        // Total com destaque
        html += `
            <div class="info-item total-item">
                <label>Custo Total (R$):</label>
                <span class="total-value">${formatCurrency(total)}</span>
            </div>
        `;

        return html;

    } catch (error) {
        console.error('[DASHBOARD_EXECUTIVO] Erro ao gerar HTML do resumo financeiro:', error);
        return `
            <div class="info-item">
                <label>Erro ao carregar resumo financeiro</label>
                <span>-</span>
            </div>
        `;
    }
}

/**
 * Atualizar resumo financeiro no modal usando o novo sistema de categorias
 */
function updateFinancialSummary(operation) {
    try {
        console.log('[DASHBOARD_EXECUTIVO] === INÍCIO updateFinancialSummary ===');
        console.log('[DASHBOARD_EXECUTIVO] Atualizando resumo financeiro para operação:', operation.ref_unique);
        console.log('[DASHBOARD_EXECUTIVO] Operação completa (verificação):', {
            ref_unique: operation.ref_unique,
            tem_despesas_processo: 'despesas_processo' in operation,
            tipo_despesas_processo: typeof operation.despesas_processo,
            tem_custo_total: 'custo_total' in operation,
            custo_total: operation.custo_total,
            tem_custo_total_view: 'custo_total_view' in operation,
            custo_total_view: operation.custo_total_view,
            tem_custo_total_original: 'custo_total_original' in operation,
            custo_total_original: operation.custo_total_original
        });

        // LOG ESPECÍFICO PARA PROCESSO 6555
        if (operation.ref_unique && operation.ref_unique.includes('6555')) {
            console.log('[DASHBOARD_EXECUTIVO] *** PROCESSO 6555 NO FRONTEND ***');
            console.log('[DASHBOARD_EXECUTIVO] custo_total:', operation.custo_total);
            console.log('[DASHBOARD_EXECUTIVO] custo_total_view:', operation.custo_total_view);
            console.log('[DASHBOARD_EXECUTIVO] custo_total_original:', operation.custo_total_original);
            console.log('[DASHBOARD_EXECUTIVO] despesas_processo tipo:', typeof operation.despesas_processo);
            console.log('[DASHBOARD_EXECUTIVO] despesas_processo length:', operation.despesas_processo ? operation.despesas_processo.length : 'N/A');
            if (operation.despesas_processo && Array.isArray(operation.despesas_processo)) {
                console.log('[DASHBOARD_EXECUTIVO] Primeiras 3 despesas do 6555:');
                operation.despesas_processo.slice(0, 3).forEach((despesa, i) => {
                    console.log(`[DASHBOARD_EXECUTIVO] Despesa ${i+1}:`, despesa);
                });
            }
        }

        // NOVA LÓGICA: Usar custo_total (que foi corrigido pelo backend) quando disponível
        let expenseData;
        let custoTotalCorreto = null;
        
        // Prioridade: 1) custo_total_view, 2) custo_total, 3) calcular manualmente
        if (operation.custo_total_view !== undefined && operation.custo_total_view !== null) {
            custoTotalCorreto = operation.custo_total_view;
            console.log('[DASHBOARD_EXECUTIVO] Usando custo_total_view (corrigido):', custoTotalCorreto);
        } else if (operation.custo_total !== undefined && operation.custo_total !== null) {
            custoTotalCorreto = operation.custo_total;
            console.log('[DASHBOARD_EXECUTIVO] Usando custo_total:', custoTotalCorreto);
        }
        
        // Se temos custo corrigido, usar ele + tentar quebrar por categoria
        if (custoTotalCorreto !== null) {
            console.log('[DASHBOARD_EXECUTIVO] USANDO CUSTO CORRIGIDO DO BACKEND:', custoTotalCorreto);
            
            // Tentar processar despesas por categoria, mas usar o total corrigido
            if (operation.despesas_processo && Array.isArray(operation.despesas_processo)) {
                const categorias = {};
                
                operation.despesas_processo.forEach(despesa => {
                    const categoria = despesa.categoria_custo || 'Outros';
                    const valor = parseFloat(despesa.valor_custo) || 0;
                    
                    if (!categorias[categoria]) {
                        categorias[categoria] = 0;
                    }
                    categorias[categoria] += valor;
                });
                
                // IMPORTANTE: Usar o total corrigido, não o calculado manualmente
                expenseData = {
                    categorias: categorias,
                    total: custoTotalCorreto
                };
                
                console.log('[DASHBOARD_EXECUTIVO] Usando categorias das despesas + total corrigido:', expenseData);
            } else {
                // Se não temos despesas detalhadas, mostrar apenas o total
                expenseData = {
                    categorias: { 'Total de Custos': custoTotalCorreto },
                    total: custoTotalCorreto
                };
                
                console.log('[DASHBOARD_EXECUTIVO] Sem detalhes de despesas, usando apenas total:', expenseData);
            }
        } else {
            // Fallback: calcular manualmente (método antigo)
            console.log('[DASHBOARD_EXECUTIVO] FALLBACK: Calculando manualmente via despesas_processo');
            expenseData = processExpensesByCategory(operation.despesas_processo);
        }
        
        console.log('[DASHBOARD_EXECUTIVO] expenseData final:', expenseData);
        
        // Obter valor CIF
        const valorCif = operation.valor_cif_real || 0;

        // Gerar HTML
        const summaryHTML = generateFinancialSummaryHTML(expenseData, valorCif);

        // Atualizar o DOM
        const cardGrid = document.querySelector('#process-modal .info-card:nth-child(4) .card-grid-2');
        if (cardGrid) {
            cardGrid.innerHTML = summaryHTML;
            console.log('[DASHBOARD_EXECUTIVO] Resumo financeiro atualizado com sucesso');
            console.log('[DASHBOARD_EXECUTIVO] HTML gerado:', summaryHTML.substring(0, 200) + '...');
        } else {
            console.error('[DASHBOARD_EXECUTIVO] Elemento card-grid-2 não encontrado no modal');
        }

        console.log('[DASHBOARD_EXECUTIVO] === FIM updateFinancialSummary ===');

    } catch (error) {
        console.error('[DASHBOARD_EXECUTIVO] Erro ao atualizar resumo financeiro:', error);
    }
}

/**
 * Calculate other expenses (DEPRECATED - mantido para compatibilidade)
 */
function calculateOtherExpenses(operation) {
    // Se temos o novo formato de despesas, usar ele
    if (operation.despesas_processo && Array.isArray(operation.despesas_processo)) {
        const expenseData = processExpensesByCategory(operation.despesas_processo);
        return expenseData.total;
    }
    
    // Fallback para o formato antigo
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
    
    // Mapeamento de ícones para os modais (apenas ícone, sem texto na tabela)
    if (modalUpper.includes('MARÍTIMA') || modalUpper.includes('MARITIMA')) {
        return `<span class="modal-icon-badge" title="${modalUpper}"><i class="mdi mdi-ferry"></i></span>`;
    } else if (modalUpper.includes('AÉREA') || modalUpper.includes('AEREA')) {
        return `<span class="modal-icon-badge" title="${modalUpper}"><i class="mdi mdi-airplane"></i></span>`;
    } else {
        return `<span class="modal-icon-badge" title="${modalUpper}"><i class="mdi mdi-truck"></i></span>`;
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

// ===== FUNÇÕES DE FILTROS =====

/**
 * Load filter options
 */
async function loadFilterOptions() {
    try {
        console.log('[DASHBOARD_EXECUTIVO] Carregando opções de filtros...');
        
        const response = await fetch('/dashboard-executivo/api/filter-options');
        const result = await response.json();
        
        if (result.success) {
            console.log('[DASHBOARD_EXECUTIVO] Opções de filtros recebidas:', {
                materiais: result.options.materiais?.length || 0,
                clientes: result.options.clientes?.length || 0,
                modais: result.options.modais?.length || 0,
                canais: result.options.canais?.length || 0
            });
            
            populateFilterOptions(result.options);
            
            // Armazenar no cache
            dashboardCache.set('filterOptions', result.options);
        } else {
            console.error('[DASHBOARD_EXECUTIVO] Erro ao carregar opções de filtros:', result.error);
            throw new Error(result.error || 'Erro ao carregar opções de filtros');
        }
    } catch (error) {
        console.error('[DASHBOARD_EXECUTIVO] Erro ao carregar opções de filtros:', error);
        
        // Tentar usar cache como fallback
        const cachedOptions = dashboardCache.get('filterOptions');
        if (cachedOptions) {
            console.log('[DASHBOARD_EXECUTIVO] Usando opções de filtros do cache como fallback');
            populateFilterOptions(cachedOptions);
        } else {
            // Se não há cache, criar opções vazias para evitar erro
            console.warn('[DASHBOARD_EXECUTIVO] Criando opções de filtros vazias');
            populateFilterOptions({
                materiais: [],
                clientes: [],
                modais: [],
                canais: []
            });
        }
    }
}

/**
 * Populate filter select options
 */
function populateFilterOptions(options) {
    console.log('[DASHBOARD_EXECUTIVO] Populando opções de filtros...');
    
    // Material filter
    if (options.materiais) {
        populateMultiSelect('material', options.materiais);
        console.log(`[DASHBOARD_EXECUTIVO] Materiais: ${options.materiais.length} opções`);
    }
    
    // Cliente filter
    if (options.clientes) {
        populateMultiSelect('cliente', options.clientes);
        console.log(`[DASHBOARD_EXECUTIVO] Clientes: ${options.clientes.length} opções`);
    }
    
    // Modal filter
    if (options.modais) {
        populateMultiSelect('modal', options.modais);
        console.log(`[DASHBOARD_EXECUTIVO] Modais: ${options.modais.length} opções`);
    }
    
    // Canal filter
    if (options.canais) {
        populateMultiSelect('canal', options.canais);
        console.log(`[DASHBOARD_EXECUTIVO] Canais: ${options.canais.length} opções`);
    }
    
    // NÃO initialize aqui - será feito quando o modal abrir
    console.log('[DASHBOARD_EXECUTIVO] Opções de filtros populadas - event listeners serão configurados ao abrir modal');
}

/**
 * Populate a multi-select dropdown
 */
function populateMultiSelect(type, options) {
    const optionsContainer = document.getElementById(`${type}-options`);
    if (!optionsContainer) return;
    
    optionsContainer.innerHTML = '';
    
    options.forEach((option, index) => {
        const optionElement = document.createElement('div');
        optionElement.className = 'multi-select-option';
        
        let iconHtml = '';
        
        // Add icons for modal options
        if (type === 'modal') {
            iconHtml = getModalIcon(option);
        }
        // Add colored dots for canal options
        else if (type === 'canal') {
            iconHtml = getCanalIndicator(option);
        }
        
        optionElement.innerHTML = `
            <input type="checkbox" id="${type}-${index}" value="${option}" onchange="updateMultiSelectDisplay('${type}')">
            <label for="${type}-${index}">
                ${iconHtml}
                ${option}
            </label>
        `;
        optionsContainer.appendChild(optionElement);
    });
}

/**
 * Initialize multi-select functionality
 */
function initializeMultiSelects() {
    console.log('[DASHBOARD_EXECUTIVO] Inicializando multi-selects...');
    
    const types = ['material', 'cliente', 'modal', 'canal'];
    let initializedCount = 0;
    
    types.forEach(type => {
        const header = document.getElementById(`${type}-header`);
        const dropdown = document.getElementById(`${type}-dropdown`);
        const search = document.getElementById(`${type}-search`);
        
        if (header && dropdown) {
            console.log(`[DASHBOARD_EXECUTIVO] Configurando event listeners para ${type}`);
            
            // Remover event listeners existentes para evitar duplicação
            const newHeader = header.cloneNode(true);
            header.parentNode.replaceChild(newHeader, header);
            
            // Toggle dropdown on header click
            newHeader.addEventListener('click', function() {
                console.log(`[DASHBOARD_EXECUTIVO] Clique no header ${type}`);
                
                // Close other dropdowns
                types.forEach(otherType => {
                    if (otherType !== type) {
                        const otherDropdown = document.getElementById(`${otherType}-dropdown`);
                        const otherHeader = document.getElementById(`${otherType}-header`);
                        if (otherDropdown && otherHeader) {
                            otherDropdown.classList.remove('open');
                            otherHeader.classList.remove('active');
                        }
                    }
                });
                
                // Toggle current dropdown
                dropdown.classList.toggle('open');
                newHeader.classList.toggle('active');
                
                console.log(`[DASHBOARD_EXECUTIVO] Dropdown ${type} ${dropdown.classList.contains('open') ? 'aberto' : 'fechado'}`);
            });
            
            // Search functionality
            const searchInput = document.getElementById(`${type}-search`);
            if (searchInput) {
                searchInput.addEventListener('input', function() {
                    filterMultiSelectOptions(type, this.value);
                });
            }
            
            initializedCount++;
        } else {
            console.warn(`[DASHBOARD_EXECUTIVO] Elementos não encontrados para ${type}:`, {
                header: !!header,
                dropdown: !!dropdown
            });
        }
    });
    
    // Só adicionar o event listener global se algum multi-select foi inicializado
    if (initializedCount > 0) {
        // Close dropdowns when clicking outside
        document.addEventListener('click', function(e) {
            if (!e.target.closest('.multi-select-container')) {
                types.forEach(type => {
                    const dropdown = document.getElementById(`${type}-dropdown`);
                    const header = document.getElementById(`${type}-header`);
                    if (dropdown && header) {
                        dropdown.classList.remove('open');
                        header.classList.remove('active');
                    }
                });
            }
        });
        
        console.log(`[DASHBOARD_EXECUTIVO] Multi-selects inicializados: ${initializedCount}/${types.length}`);
    } else {
        console.error('[DASHBOARD_EXECUTIVO] Nenhum multi-select foi inicializado!');
    }
}

/**
 * Filter multi-select options based on search
 */
function filterMultiSelectOptions(type, searchTerm) {
    const options = document.querySelectorAll(`#${type}-options .multi-select-option`);
    const term = searchTerm.toLowerCase();
    
    options.forEach(option => {
        const label = option.querySelector('label').textContent.toLowerCase();
        if (label.includes(term)) {
            option.style.display = 'flex';
        } else {
            option.style.display = 'none';
        }
    });
}

/**
 * Update multi-select display when selections change
 */
function updateMultiSelectDisplay(type) {
    const checkboxes = document.querySelectorAll(`#${type}-options input[type="checkbox"]:checked`);
    const placeholder = document.querySelector(`#${type}-header .multi-select-placeholder`);
    
    if (!placeholder) return;
    
    const selectedCount = checkboxes.length;
    
    if (selectedCount === 0) {
        placeholder.innerHTML = `Todos os ${getTypePlural(type)}`;
    } else if (selectedCount === 1) {
        placeholder.innerHTML = checkboxes[0].nextElementSibling.textContent;
    } else {
        placeholder.innerHTML = `${selectedCount} ${getTypePlural(type)} selecionados`;
    }
    
    // CORREÇÃO: Atualizar currentFilters e mostrar/esconder botão Reset
    if (!currentFilters) currentFilters = {};
    
    // Obter valores selecionados do multi-select
    const selectedValues = getMultiSelectValues(type);
    currentFilters[type] = selectedValues.length > 0 ? selectedValues.join(',') : '';
    
    // Atualizar visibilidade do botão Reset
    updateResetButtonVisibility();
}

/**
 * Get plural form for filter types
 */
function getTypePlural(type) {
    const plurals = {
        'material': 'materiais',
        'cliente': 'clientes', 
        'modal': 'modais',
        'canal': 'canais'
    };
    return plurals[type] || type;
}

/**
 * Get selected values from multi-select
 */
function getMultiSelectValues(type) {
    const checkboxes = document.querySelectorAll(`#${type}-options input[type="checkbox"]:checked`);
    return Array.from(checkboxes).map(cb => cb.value);
}

/**
 * Build filter query string
 */
function buildFilterQueryString() {
    const params = new URLSearchParams();
    
    const dataInicio = document.getElementById('data-inicio')?.value;
    const dataFim = document.getElementById('data-fim')?.value;
    const statusProcesso = document.getElementById('status-processo')?.value;
    
    // Get multi-select values
    const materiais = getMultiSelectValues('material');
    const clientes = getMultiSelectValues('cliente');
    const modais = getMultiSelectValues('modal');
    const canais = getMultiSelectValues('canal');
    
    if (dataInicio) params.append('data_inicio', dataInicio);
    if (dataFim) params.append('data_fim', dataFim);
    if (statusProcesso) params.append('status_processo', statusProcesso);
    
    // Add multi-select values as comma-separated strings
    if (materiais.length > 0) params.append('material', materiais.join(','));
    if (clientes.length > 0) params.append('cliente', clientes.join(','));
    if (modais.length > 0) params.append('modal', modais.join(','));
    if (canais.length > 0) params.append('canal', canais.join(','));
    
    return params.toString();
}

/**
 * Open filter modal
 */
function openFilterModal() {
    console.log('[DASHBOARD_EXECUTIVO] Abrindo modal de filtros...');
    
    const modal = document.getElementById('filter-modal');
    if (modal) {
        modal.style.display = 'block';
        
        // Aguardar o modal estar visível e então inicializar os multi-selects
        setTimeout(() => {
            console.log('[DASHBOARD_EXECUTIVO] Modal visível - inicializando multi-selects...');
            initializeMultiSelects();
        }, 100);
    } else {
        console.error('[DASHBOARD_EXECUTIVO] Modal de filtros não encontrado!');
    }
}

/**
 * Close filter modal
 */
function closeFilterModal() {
    const modal = document.getElementById('filter-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

/**
 * Set quick period filter
 */
function setQuickPeriod(days) {
    const hoje = new Date();
    const dataFim = hoje.toISOString().split('T')[0];
    const dataInicio = new Date(hoje.getTime() - (days * 24 * 60 * 60 * 1000)).toISOString().split('T')[0];
    
    document.getElementById('data-inicio').value = dataInicio;
    document.getElementById('data-fim').value = dataFim;
    
    // Update active button
    document.querySelectorAll('.btn-quick').forEach(btn => {
        btn.classList.remove('active');
        if (parseInt(btn.dataset.days) === days) {
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
        
        // CORREÇÃO: Store current filters using correct methods
        currentFilters = {
            dataInicio: document.getElementById('data-inicio')?.value,
            dataFim: document.getElementById('data-fim')?.value,
            statusProcesso: document.getElementById('status-processo')?.value,
            // CORREÇÃO: Usar getMultiSelectValues() para multi-selects
            material: getMultiSelectValues('material').join(','),
            cliente: getMultiSelectValues('cliente').join(','),
            modal: getMultiSelectValues('modal').join(','),
            canal: getMultiSelectValues('canal').join(',')
        };
        
        console.log('[DASHBOARD_EXECUTIVO] Filtros aplicados:', currentFilters);
        
        // Update filter summary
        updateFilterSummary();
        
        // Show/hide reset button based on active filters
        updateResetButtonVisibility();
        
        // Close modal
        closeFilterModal();
        
        // CORREÇÃO: NÃO invalidar cache completo - apenas recarregar dados com filtros
        // dashboardCache.invalidate(); // ❌ REMOVIDO - causa perda dos dados base
        console.log('[DASHBOARD_EXECUTIVO] Recarregando dados com novos filtros...');
        
        // Reload data with filters using cache system
        await Promise.all([
            loadDashboardKPIsWithCache(),
            loadDashboardChartsWithCache(),
            loadRecentOperationsWithCache()
        ]);
        
        showLoading(false);
        // Removido o popup de confirmação
        
    } catch (error) {
        console.error('[DASHBOARD_EXECUTIVO] Erro ao aplicar filtros:', error);
        showError('Erro ao aplicar filtros: ' + error.message);
        showLoading(false);
    }
}

/**
 * Clear all filters
 */
function clearFilters() {
    // Clear date inputs
    document.getElementById('data-inicio').value = '';
    document.getElementById('data-fim').value = '';
    
    // Clear status processo
    document.getElementById('status-processo').value = '';
    
    // Clear multi-select checkboxes
    const types = ['material', 'cliente', 'modal', 'canal'];
    types.forEach(type => {
        const checkboxes = document.querySelectorAll(`#${type}-options input[type="checkbox"]`);
        checkboxes.forEach(checkbox => {
            checkbox.checked = false;
        });
        updateMultiSelectDisplay(type);
    });
    
    // Clear active buttons
    document.querySelectorAll('.btn-quick').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Clear stored filters
    currentFilters = {};
    
    // Update summary
    updateFilterSummary();
    
    showSuccess('Filtros limpos!');
}

/**
 * Reset all filters and reload data
 */
async function resetAllFilters() {
    try {
        showLoading(true);
        
        // Clear date inputs
        document.getElementById('data-inicio').value = '';
        document.getElementById('data-fim').value = '';
        
        // CORREÇÃO: Adicionar reset do status processo
        document.getElementById('status-processo').value = '';
        
        // Clear multi-select checkboxes
        const types = ['material', 'cliente', 'modal', 'canal'];
        types.forEach(type => {
            const checkboxes = document.querySelectorAll(`#${type}-options input[type="checkbox"]`);
            checkboxes.forEach(checkbox => {
                checkbox.checked = false;
            });
            updateMultiSelectDisplay(type);
        });
        
        // Clear active buttons
        document.querySelectorAll('.btn-quick').forEach(btn => {
            btn.classList.remove('active');
        });
        
        // Clear stored filters
        currentFilters = {};
        
        // Update summary
        updateFilterSummary();
        
        // Hide reset button
        updateResetButtonVisibility();
        
        // CORREÇÃO: NÃO invalidar cache - preservar dados base para evitar erro "Dados não encontrados"
        // dashboardCache.invalidate(); // ❌ REMOVIDO - causa erro de dados
        console.log('[DASHBOARD_EXECUTIVO] Recarregando dados sem filtros (cache preservado)...');
        
        await Promise.all([
            loadDashboardKPIsWithCache(),
            loadDashboardChartsWithCache(),
            loadRecentOperationsWithCache()
        ]);
        
        showLoading(false);
        
    } catch (error) {
        console.error('[DASHBOARD_EXECUTIVO] Erro ao resetar filtros:', error);
        showError('Erro ao resetar filtros: ' + error.message);
        showLoading(false);
    }
}

/**
 * Update reset button visibility based on active filters
 */
function updateResetButtonVisibility() {
    const resetBtn = document.getElementById('reset-filters');
    if (!resetBtn) return;
    
    // Check if any filter is active
    const hasActiveFilters = Object.values(currentFilters).some(value => value && value.trim() !== '');
    
    if (hasActiveFilters) {
        resetBtn.style.display = 'inline-block';
    } else {
        resetBtn.style.display = 'none';
    }
}

/**
 * Update filter summary
 */
function updateFilterSummary() {
    const summaryElement = document.getElementById('filter-summary-text');
    if (!summaryElement) return;
    
    let summaryText = 'Vendo dados completos';
    
    if (currentFilters.dataInicio && currentFilters.dataFim) {
        const dataInicio = new Date(currentFilters.dataInicio).toLocaleDateString('pt-BR');
        const dataFim = new Date(currentFilters.dataFim).toLocaleDateString('pt-BR');
        summaryText = `Dados de ${dataInicio} até ${dataFim}`;
        
        // Add other filters
        const otherFilters = [];
        if (currentFilters.material) otherFilters.push(`Material: ${currentFilters.material}`);
        if (currentFilters.cliente) otherFilters.push(`Cliente: ${currentFilters.cliente}`);
        if (currentFilters.modal) otherFilters.push(`Modal: ${currentFilters.modal}`);
        if (currentFilters.canal) otherFilters.push(`Canal: ${currentFilters.canal}`);
        if (currentFilters.statusProcesso) {
            const statusText = currentFilters.statusProcesso === 'aberto' ? 'Processos Abertos' : 'Processos Fechados';
            otherFilters.push(`Status: ${statusText}`);
        }
        
        if (otherFilters.length > 0) {
            summaryText += ` (${otherFilters.join(', ')})`;
        }
    }
    
    summaryElement.textContent = summaryText;
}

/**
 * Create principais materiais table
 */
function createPrincipaisMateriaisTable(data) {
    const tableBody = document.querySelector('#principais-materiais-table tbody');
    if (!tableBody) {
        console.error('[DASHBOARD_EXECUTIVO] Tabela de principais materiais não encontrada');
        return;
    }
    
    tableBody.innerHTML = '';
    
    if (!data.data || data.data.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="5" class="text-center">Nenhum material encontrado</td></tr>';
        return;
    }
    
    // Exibir apenas o Top 5 materiais
    (data.data.slice(0, 5)).forEach(material => {
        const row = document.createElement('tr');
        // Add urgente class if needed
        if (material.is_urgente) {
            row.classList.add('urgente-row');
        }
        row.innerHTML = `
            <td title="${material.material}">${material.material.length > 30 ? material.material.substring(0, 30) + '...' : material.material}</td>
            <td class="text-center">${material.total_processos}</td>
            <td class="text-center">${formatCurrency(material.custo_total)}</td>
            <td class="text-center">
                ${material.is_urgente ? 
                    `<span class="material-urgente">${formatDate(material.data_chegada)} (${material.dias_para_chegada} dias)</span>` : 
                    formatDate(material.data_chegada)
                }
            </td>
            <td class="text-center">${material.transit_time ? formatNumber(material.transit_time, 1) + ' dias' : '-'}</td>
        `;
        tableBody.appendChild(row);
    });
    
    console.log(`[DASHBOARD_EXECUTIVO] Tabela de materiais criada com ${data.data.length} itens`);
}

/**
 * Get modal icon HTML
 */
function getModalIcon(modal) {
    const modalLower = modal.toLowerCase();
    let iconClass = 'mdi-help';
    let cssClass = '';
    
    if (modalLower.includes('maritim') || modalLower.includes('marítim')) {
        iconClass = 'mdi-ferry';
        cssClass = 'maritima';
    } else if (modalLower.includes('aer') || modalLower.includes('aére')) {
        iconClass = 'mdi-airplane';
        cssClass = 'aerea';
    } else if (modalLower.includes('rodovi') || modalLower.includes('rodoviári')) {
        iconClass = 'mdi-truck';
        cssClass = 'rodoviaria';
    } else if (modalLower.includes('ferr') || modalLower.includes('ferrovi')) {
        iconClass = 'mdi-train';
        cssClass = 'ferroviaria';
    } else if (modalLower.includes('postal') || modalLower.includes('correio')) {
        iconClass = 'mdi-email';
        cssClass = 'postal';
    } else if (modalLower.includes('courier') || modalLower.includes('expres')) {
        iconClass = 'mdi-package-variant';
        cssClass = 'courier';
    }
    
    return `<span class="modal-icon ${cssClass}"><i class="mdi ${iconClass}"></i></span>`;
}

/**
 * Get canal indicator HTML
 */
function getCanalIndicator(canal) {
    let dotClass = '';
    
    if (canal && canal.toLowerCase) {
        const canalLower = canal.toLowerCase();
        if (canalLower.includes('verde') || canalLower === 'verde') {
            dotClass = 'verde';
        } else if (canalLower.includes('amarelo') || canalLower === 'amarelo') {
            dotClass = 'amarelo';
        } else if (canalLower.includes('vermelho') || canalLower === 'vermelho') {
            dotClass = 'vermelho';
        }
    }
    
    return `<span class="canal-indicator"><span class="canal-dot ${dotClass}"></span></span>`;
}

/**
 * Refresh silencioso do dashboard
 */
async function silentRefresh() {
    console.log('[DASHBOARD_EXECUTIVO] Refresh silencioso iniciado');
    if (isLoading) {
        console.log('[DASHBOARD_EXECUTIVO] Já está carregando, pulando refresh silencioso');
        return;
    }
    
    try {
        await loadInitialData();
        console.log('[DASHBOARD_EXECUTIVO] Refresh silencioso concluído com sucesso');
        return true;
    } catch (error) {
        console.error('[DASHBOARD_EXECUTIVO] Erro no refresh silencioso:', error);
        return false;
    }
}

// Expor funções globalmente para validação e debug
window.dashboardModule = {
    refresh: loadInitialData,
    silentRefresh: silentRefresh,
    forceRefresh: forceRefreshDashboard, // NOVO: Force refresh específico
    loadData: loadInitialData,
    charts: dashboardCharts,
    data: dashboardData,
    isLoading: () => isLoading,
    hasData: () => {
        return dashboardData && 
               dashboardData.length > 0 &&
               Object.keys(dashboardCharts).length > 0;
    },
    validateCharts: validateAndRecreateCharts
};

// Também manter as funções globais existentes para compatibilidade
window.loadInitialData = loadInitialData;
window.dashboardCharts = dashboardCharts;

// Integração com o sistema global de refresh
document.addEventListener('DOMContentLoaded', function() {
    // Escutar evento de refresh global para executar force refresh específico
    document.addEventListener('globalRefreshRequested', function() {
        console.log('[DASHBOARD_EXECUTIVO] Refresh global detectado, executando force refresh...');
        forceRefreshDashboard();
    });
    
    // Disponibilizar função de force refresh globalmente
    window.forceRefreshDashboard = forceRefreshDashboard;
});

// INTEGRAÇÃO COM SISTEMA GLOBAL DE REFRESH
// Hook para interceptar o botão global de refresh quando estamos no dashboard executivo
document.addEventListener('DOMContentLoaded', function() {
    // Verificar se estamos na página do dashboard executivo
    const isDashboardExecutivo = window.location.pathname.includes('/dashboard-executivo');
    
    if (isDashboardExecutivo) {
        console.log('[DASHBOARD_EXECUTIVO] Integrando com sistema global de refresh...');
        
        // Substituir comportamento do botão global de refresh
        const globalRefreshButton = document.getElementById('global-refresh-button');
        if (globalRefreshButton) {
            // Remover listeners existentes clonando o elemento
            const newButton = globalRefreshButton.cloneNode(true);
            globalRefreshButton.parentNode.replaceChild(newButton, globalRefreshButton);
            
            // Adicionar novo listener específico para o dashboard
            newButton.addEventListener('click', async function() {
                console.log('[DASHBOARD_EXECUTIVO] Force refresh acionado via botão global');
                
                // Feedback visual
                const originalHtml = newButton.innerHTML;
                newButton.innerHTML = '<i class="mdi mdi-loading mdi-spin text-sm"></i>';
                newButton.disabled = true;
                newButton.classList.add('opacity-50');
                
                try {
                    await forceRefreshDashboard();
                } finally {
                    // Restaurar botão
                    newButton.innerHTML = originalHtml;
                    newButton.disabled = false;
                    newButton.classList.remove('opacity-50');
                }
            });
            
            console.log('[DASHBOARD_EXECUTIVO] Botão global de refresh redirecionado para force refresh do dashboard');
        }
        
        // Registrar módulo no sistema global (se existir)
        if (window.GlobalRefresh) {
            console.log('[DASHBOARD_EXECUTIVO] Registrando no sistema GlobalRefresh...');
            
            // Adicionar listener para refresh global
            window.addEventListener('globalRefreshCompleted', function(event) {
                console.log('[DASHBOARD_EXECUTIVO] Refresh global detectado, sincronizando dashboard...');
                // Apenas recarregar cache, não force refresh novamente
                loadInitialDataWithCache().catch(console.error);
            });
        }
    }
});
