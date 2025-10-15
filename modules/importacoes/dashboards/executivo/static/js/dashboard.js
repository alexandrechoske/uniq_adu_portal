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

// Paleta consistente para tipos de dado
const DASH_COLORS = {
    processos: '#007bff', // azul
    custo: '#f59e0b'      // laranja
};

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
    
    // Check if user has company warning - if so, don't initialize dashboard
    if (window.showCompanyWarning) {
        console.log('[DASHBOARD_EXECUTIVO] Dashboard bloqueado - usuário sem empresas vinculadas');
        return; // Exit early, don't initialize any dashboard functionality
    }
    
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
    
    // Inicializar sistema de filtro por KPI clicável
    initializeKpiClickFilters();
    
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
            // Inicializa direto, sem depender do sistema unificado (desativado nesta página)
            initializeDashboard();
        } else {
            console.error('[DASHBOARD_EXECUTIVO] Chart.js não foi carregado');
        }
    }, 1000);
});

// ===== SISTEMA DE FILTRO POR KPI CLICÁVEL =====
/**
 * Inicializa o sistema de filtros clicáveis nos KPIs
 * Quando um KPI é clicado, filtra os dados do dashboard baseado no status correspondente
 */
function initializeKpiClickFilters() {
    console.log('[KPI_FILTER] Inicializando sistema de filtros clicáveis');
    
    const clickableKpis = document.querySelectorAll('.kpi-card.kpi-clickable');
    
    clickableKpis.forEach(kpi => {
        kpi.addEventListener('click', function() {
            const status = this.getAttribute('data-kpi-status');
            console.log('[KPI_FILTER] KPI clicado:', status);
            
            // Toggle filtro: se já está ativo, remove; senão aplica
            if (this.classList.contains('kpi-active')) {
                clearKpiFilter();
            } else {
                applyKpiFilter(status);
            }
        });
    });
}

/**
 * Aplica filtro baseado no status do KPI
 */
async function applyKpiFilter(status) {
    console.log('[KPI_FILTER] Aplicando filtro:', status);
    
    // Remover classe active de todos os KPIs
    document.querySelectorAll('.kpi-card.kpi-active').forEach(kpi => {
        kpi.classList.remove('kpi-active');
    });
    
    // Adicionar classe active no KPI clicado
    const activeKpi = document.querySelector(`.kpi-card[data-kpi-status="${status}"]`);
    if (activeKpi) {
        activeKpi.classList.add('kpi-active');
    }
    
    // Aplicar filtro baseado no status
    currentFilters.kpi_status = status;
    
    // Invalidar cache para forçar reload com filtro
    dashboardCache.invalidate();
    
    // Recarregar todos os componentes com filtro
    try {
        console.log('[KPI_FILTER] Recarregando componentes com filtro...');
        await loadComponentsWithRetry();
        console.log('[KPI_FILTER] Componentes recarregados com sucesso');
    } catch (error) {
        console.error('[KPI_FILTER] Erro ao recarregar componentes:', error);
    }
}

/**
 * Limpa o filtro de KPI ativo
 */
async function clearKpiFilter() {
    console.log('[KPI_FILTER] Limpando filtro de KPI');
    
    // Remover classe active de todos os KPIs
    document.querySelectorAll('.kpi-card.kpi-active').forEach(kpi => {
        kpi.classList.remove('kpi-active');
    });
    
    // Remover filtro
    delete currentFilters.kpi_status;
    
    // Invalidar cache para forçar reload sem filtro
    dashboardCache.invalidate();
    
    // Recarregar todos os componentes sem filtro
    try {
        console.log('[KPI_FILTER] Recarregando componentes sem filtro...');
        await loadComponentsWithRetry();
        console.log('[KPI_FILTER] Componentes recarregados com sucesso');
    } catch (error) {
        console.error('[KPI_FILTER] Erro ao recarregar componentes:', error);
    }
}

// ===== Stubs leves para evitar ReferenceError sem mudar comportamento =====
// Algumas funções podem não existir dependendo da ordem de scripts; criamos stubs no-ops
if (typeof window.createDashboardChartsWithValidation !== 'function') {
    window.createDashboardChartsWithValidation = function(charts) {
        // fallback para createDashboardCharts se existir
        if (typeof window.createDashboardCharts === 'function') {
            return window.createDashboardCharts(charts);
        }
        console.warn('[DASHBOARD_EXECUTIVO] Stub: createDashboardChartsWithValidation ausente');
    };
}
if (typeof window.updateDashboardKPIs !== 'function') {
    window.updateDashboardKPIs = function(kpis) {
        console.warn('[DASHBOARD_EXECUTIVO] Stub: updateDashboardKPIs ausente');
        // No-op: manter sem UI change; loaders por componente já serão ocultados via wrappers
    };
}
if (typeof window.setMonthlyChartPeriod !== 'function') {
    window.setMonthlyChartPeriod = function(period) {
        // Ajusta variável local e dispara loadMonthlyChart
        try {
            monthlyChartPeriod = period || monthlyChartPeriod || 'mensal';
            loadMonthlyChart(monthlyChartPeriod);
        } catch (e) {
            console.warn('[DASHBOARD_EXECUTIVO] Stub: setMonthlyChartPeriod ausente');
        }
    };
}
if (typeof window.createMonthlyChartWithValidation !== 'function') {
    window.createMonthlyChartWithValidation = function() { /* no-op */ };
}
if (typeof window.createStatusChartWithValidation !== 'function') {
    window.createStatusChartWithValidation = function() { /* no-op */ };
}
if (typeof window.createGroupedModalChartWithValidation !== 'function') {
    window.createGroupedModalChartWithValidation = function() { /* no-op */ };
}
if (typeof window.createUrfChartWithValidation !== 'function') {
    window.createUrfChartWithValidation = function() { /* no-op */ };
}
if (typeof window.createMaterialChartWithValidation !== 'function') {
    window.createMaterialChartWithValidation = function() { /* no-op */ };
}

// ===== Implementações reais de KPIs e gráficos (com validação) =====
// Helpers de Chart.js
function getCanvasContext(id) {
    const el = document.getElementById(id);
    if (!el) {
        console.error(`[DASHBOARD_EXECUTIVO] Canvas #${id} não encontrado`);
        return null;
    }
    return el.getContext ? el.getContext('2d') : el;
}

function destroyChartIfExists(id) {
    const canvas = document.getElementById(id);
    if (!canvas) return;
    const existing = Chart.getChart(canvas);
    if (existing) {
        try { existing.destroy(); } catch (_) {}
    }
}

// Atualização de KPIs
window.updateDashboardKPIs = function(kpis) {
    try {
        if (!kpis || typeof kpis !== 'object') return;
        const setText = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
        // Processos Abertos = total geral (todos da view)
        setText('kpi-processos-abertos', formatNumber(kpis.processos_abertos || 0));
        setText('kpi-chegando-mes', formatNumber(kpis.chegando_mes || 0));
        setText('kpi-chegando-mes-custo', formatCurrencyCompact(kpis.chegando_mes_custo || 0));
        setText('kpi-chegando-semana', formatNumber(kpis.chegando_semana || 0));
        setText('kpi-chegando-semana-custo', formatCurrencyCompact(kpis.chegando_semana_custo || 0));
        setText('kpi-agd-embarque', formatNumber(kpis.agd_embarque || 0));
        setText('kpi-agd-chegada', formatNumber(kpis.agd_chegada || 0));
        setText('kpi-agd-registro', formatNumber(kpis.agd_registro || 0));         // NOVO
        setText('kpi-agd-desembaraco', formatNumber(kpis.agd_desembaraco || 0));   // NOVO
        setText('kpi-agd-fechamento', formatNumber(kpis.agd_fechamento || 0));
        setText('kpi-total-despesas', formatCurrencyCompact(kpis.total_despesas || 0));
    } finally {
        try { if (window.DASH_EXEC_HIDE_LOADER) window.DASH_EXEC_HIDE_LOADER('kpi-loading'); } catch (_) {}
    }
};

// Orquestrador principal dos gráficos (usa funções com validação)
window.createDashboardChartsWithValidation = function(charts) {
    try {
        if (!charts || typeof charts !== 'object') return;
        if (charts.monthly) window.createMonthlyChartWithValidation(charts.monthly);
        if (charts.status) window.createStatusChartWithValidation(charts.status);
        if (charts.grouped_modal) window.createGroupedModalChartWithValidation(charts.grouped_modal);
        if (charts.urf) window.createUrfChartWithValidation(charts.urf);
        if (charts.principais_materiais) window.createPrincipaisMateriaisTableWithValidation(charts.principais_materiais);
        // material (barras) opcional – mantemos somente a tabela principais_materiais
    } catch (e) {
        console.error('[DASHBOARD_EXECUTIVO] Erro ao criar gráficos:', e);
    }
};

// Evolução Mensal (mixed chart)
window.createMonthlyChart = function(data) {
    try {
        if (!data || !data.labels || !data.datasets) {
            console.warn('[DASHBOARD_EXECUTIVO] Dados inválidos para gráfico mensal');
            return;
        }
        destroyChartIfExists('monthly-chart');
        const ctx = getCanvasContext('monthly-chart');
        if (!ctx) return;
    const labelsCount = Array.isArray(data.labels) ? data.labels.length : 0;
    const dense = (typeof monthlyChartPeriod !== 'undefined' && monthlyChartPeriod === 'diario') || labelsCount > 45;
        dashboardCharts.monthly = new Chart(ctx, {
            data: {
                labels: data.labels,
                datasets: data.datasets.map(ds => {
                    const isCusto = /custo/i.test(ds.label || '');
                    const color = isCusto ? DASH_COLORS.custo : DASH_COLORS.processos;
                    const bg = isCusto ? 'rgba(245, 158, 11, 0.08)' : 'rgba(0, 123, 255, 0.08)';
                    return {
                        ...ds,
                        type: 'line',
                        fill: 'origin',
                        borderColor: color,
                        backgroundColor: bg,
                        borderWidth: 2,
                        pointRadius: dense ? 0 : 2,
                        pointHoverRadius: dense ? 0 : 4,
                        tension: ds.tension ?? 0.35
                    };
                })
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: { display: true, position: 'top' },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => {
                                const yId = ctx.dataset.yAxisID;
                                const v = ctx.parsed.y;
                return yId === 'y' ? ` ${formatCurrencyCompact(v)}` : ` ${formatNumber(v)}`;
                            }
                        }
                    },
                    datalabels: {
                        display: !dense,
                        anchor: 'end',
                        align: (ctx) => (/custo/i.test(ctx.dataset.label || '') ? 'top' : 'bottom'),
                        offset: 3,
                        clamp: true,
                        formatter: (value, ctx) => {
                            const isCusto = /custo/i.test(ctx.dataset.label || '');
                            return isCusto ? formatCurrencyCompact(value) : formatNumber(value);
                        },
                        color: (ctx) => (/custo/i.test(ctx.dataset.label || '') ? DASH_COLORS.custo : DASH_COLORS.processos),
                        font: { weight: '600', size: 11 }
                    }
                },
                scales: {
                    y: {
                        type: 'linear',
                        position: 'left',
                        ticks: { display: false },
                        grid: { display: false },
                        border: { display: false }
                    },
                    y1: {
                        type: 'linear',
                        position: 'right',
                        beginAtZero: true,
                        ticks: { display: false },
                        grid: { display: false },
                        border: { display: false }
                    }
                }
            }
        });
    } finally {
        try { if (window.DASH_EXEC_HIDE_LOADER) window.DASH_EXEC_HIDE_LOADER('monthly-loading'); } catch (_) {}
    }
};

window.createMonthlyChartWithValidation = function(payload) {
    try {
        // Aceita payload em dois formatos: já pronto (labels/datasets) ou {labels, data/processes/values}
        if (!payload) return;
        if (payload.labels && payload.datasets) {
            return window.createMonthlyChart(payload);
        }
        if (payload.periods) {
            return window.createMonthlyChart({
                labels: payload.periods,
                datasets: [
                    {
                        label: 'Quantidade de Processos',
                        data: payload.processes || [],
                        type: 'line',
                        borderColor: DASH_COLORS.processos,
                        backgroundColor: 'rgba(0, 123, 255, 0.08)',
                        yAxisID: 'y1',
                        tension: 0.4
                    },
                    {
                        label: 'Custo Total (R$)',
                        data: payload.values || [],
                        type: 'line',
                        borderColor: DASH_COLORS.custo,
                        backgroundColor: 'rgba(40, 167, 69, 0.08)',
                        yAxisID: 'y',
                        tension: 0.4
                    }
                ]
            });
        }
    } finally {
        try { if (window.DASH_EXEC_HIDE_LOADER) window.DASH_EXEC_HIDE_LOADER('monthly-loading'); } catch (_) {}
    }
};

// Status (doughnut)
window.createStatusChart = function(data) {
    try {
        if (!data || !data.labels || !data.data) return;
        destroyChartIfExists('status-chart');
        const ctx = getCanvasContext('status-chart');
        if (!ctx) return;
    // Normalizar labels vazias para 'Sem Info'
    data.labels = data.labels.map(l => (l && (''+l).trim()) ? l : 'Sem Info');
        dashboardCharts.status = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: data.labels,
                datasets: [{
                    data: data.data,
                    backgroundColor: [
                        '#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444',
                        '#06b6d4', '#84cc16', '#f97316', '#e11d48', '#64748b'
                    ],
                    borderColor: '#ffffff',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { 
                        position: 'right',
                        labels: {
                            font: {
                                weight: 'bold', // Labels da legenda em negrito
                                size: 12
                            },
                            generateLabels(chart) {
                                const baseGen = (Chart.overrides && Chart.overrides.doughnut && Chart.overrides.doughnut.plugins && Chart.overrides.doughnut.plugins.legend && Chart.overrides.doughnut.plugins.legend.labels && Chart.overrides.doughnut.plugins.legend.labels.generateLabels)
                                    || (Chart.defaults && Chart.defaults.plugins && Chart.defaults.plugins.legend && Chart.defaults.plugins.legend.labels && Chart.defaults.plugins.legend.labels.generateLabels);
                                const original = baseGen ? baseGen(chart) : [];
                                return original.map(lbl => {
                                    const text = Array.isArray(lbl.text) ? lbl.text.join(' ') : (lbl.text || '');
                                    if (text.length > 18) {
                                        const words = text.split(/\s+/);
                                        const lines = [];
                                        let current = '';
                                        words.forEach(w => {
                                            if ((current + ' ' + w).trim().length > 18) {
                                                if (current) lines.push(current.trim());
                                                current = w;
                                            } else {
                                                current += ' ' + w;
                                            }
                                        });
                                        if (current) lines.push(current.trim());
                                        lbl.text = lines.length ? lines : text; // multiline if split
                                    }
                                    return lbl;
                                });
                            }
                        }
                    },
                    datalabels: {
                        color: (ctx) => {
                            try {
                                const bg = ctx.dataset.backgroundColor[ctx.dataIndex];
                                return getContrastTextColor(bg);
                            } catch (_) { return '#111'; }
                        },
                        formatter: (value) => `${formatNumber(value)}`,
                        font: { weight: 'bold', size: 11 } // Valores dentro do gráfico em negrito
                    }
                }
            }
        });
    } finally {
        try { if (window.DASH_EXEC_HIDE_LOADER) window.DASH_EXEC_HIDE_LOADER('status-loading'); } catch (_) {}
    }
};

window.createStatusChartWithValidation = function(payload) {
    try { if (payload) return window.createStatusChart(payload); }
    finally { try { if (window.DASH_EXEC_HIDE_LOADER) window.DASH_EXEC_HIDE_LOADER('status-loading'); } catch (_) {} }
};

// Modal (barras + Barras)
window.createGroupedModalChart = function(data) {
    try {
        if (!data || !data.labels || !data.datasets) return;
        destroyChartIfExists('grouped-modal-chart');
        const ctx = getCanvasContext('grouped-modal-chart');
        if (!ctx) return;
        const datasets = data.datasets.map(ds => {
            const isCusto = /custo/i.test((ds.label || ''));
            return {
                ...ds,
                type: 'bar',
                backgroundColor: isCusto ? 'rgba(245, 158, 11, 0.6)' : 'rgba(0, 123, 255, 0.6)',
                borderColor: isCusto ? DASH_COLORS.custo : DASH_COLORS.processos
            };
        });
        dashboardCharts.groupedModal = new Chart(ctx, {
            data: { labels: data.labels, datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: { 
                        position: 'top',
                        labels: {
                            font: {
                                weight: 'bold', // Legenda em negrito
                                size: 12
                            }
                        }
                    },
                    datalabels: {
                        anchor: 'end',
                        align: 'end',
                        clip: false,
                        offset: -2,
                        formatter: (value, ctx) => {
                            const label = ctx.dataset.label || '';
                            return /custo/i.test(label) ? formatCurrencyCompact(value) : formatNumber(value);
                        },
                        font: { size: 11, weight: 'bold' }, // Valores em negrito
                        color: (ctx) => /custo/i.test(ctx.dataset.label || '') ? '#92400e' : '#1e3a8a'
                    },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => {
                                const label = ctx.dataset.label || '';
                                const v = ctx.parsed.y;
                                return /custo/i.test(label) ? ` ${formatCurrencyCompact(v)}` : ` ${formatNumber(v)}`;
                            }
                        }
                    }
                },
                // Reduzido padding superior para encostar mais no topo
                layout: { padding: { top: 8 } },
                scales: {
                    x: {
                        ticks: {
                            font: {
                                weight: 'bold', // Categorias do eixo X em negrito
                                size: 11
                            }
                        }
                    },
                    y: { type: 'linear', position: 'left', ticks: { display: false }, grid: { display: false }, border: { display: false } },
                    y1: { type: 'linear', position: 'right', beginAtZero: true, ticks: { display: false }, grid: { display: false }, border: { display: false } }
                }
            }
        });
    } finally {
        try { if (window.DASH_EXEC_HIDE_LOADER) window.DASH_EXEC_HIDE_LOADER('modal-loading'); } catch (_) {}
    }
};

window.createGroupedModalChartWithValidation = function(payload) {
    try { if (payload) return window.createGroupedModalChart(payload); }
    finally { try { if (window.DASH_EXEC_HIDE_LOADER) window.DASH_EXEC_HIDE_LOADER('modal-loading'); } catch (_) {} }
};

// URF (horizontal bar)
window.createUrfChart = function(data) {
    try {
        if (!data || !data.labels || !data.data) return;
        destroyChartIfExists('urf-chart');
        const ctx = getCanvasContext('urf-chart');
        if (!ctx) return;
        dashboardCharts.urf = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Processos',
                    data: data.data,
                    backgroundColor: 'rgba(59, 130, 246, 0.6)',
                    borderColor: 'rgba(59, 130, 246, 1)'
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { 
                        beginAtZero: true, 
                        grid: { display: false }, 
                        border: { display: false },
                        ticks: {
                            font: {
                                weight: 'bold'
                            }
                        }
                    },
                    y: { 
                        grid: { display: false }, 
                        border: { display: false },
                        ticks: {
                            font: {
                                weight: 'bold', // Deixa as categorias (URFs/Destinos) em negrito
                                size: 12        // Tamanho da fonte (opcional)
                            }
                        }
                    }
                }
            }
        });
    } finally {
        try { if (window.DASH_EXEC_HIDE_LOADER) window.DASH_EXEC_HIDE_LOADER('urf-loading'); } catch (_) {}
    }
};

window.createUrfChartWithValidation = function(payload) {
    try { if (payload) return window.createUrfChart(payload); }
    finally { try { if (window.DASH_EXEC_HIDE_LOADER) window.DASH_EXEC_HIDE_LOADER('urf-loading'); } catch (_) {} }
};

// Principais Materiais (tabela)
window.createPrincipaisMateriaisTableWithValidation = function(payload) {
    try { if (payload) return window.createPrincipaisMateriaisTable(payload); }
    finally { try { if (window.DASH_EXEC_HIDE_LOADER) window.DASH_EXEC_HIDE_LOADER('material-loading'); } catch (_) {} }
};

// Ajuste de período do gráfico mensal
window.setMonthlyChartPeriod = function(period) {
    try {
        monthlyChartPeriod = period || 'mensal';
        // Atualizar botões ativos
        document.querySelectorAll('.period-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.period === monthlyChartPeriod);
        });
        loadMonthlyChart(monthlyChartPeriod);
    } catch (e) {
        console.warn('[DASHBOARD_EXECUTIVO] Erro ao definir período do gráfico mensal:', e);
    }
};

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
                // Tratar labels vazias e adicionar bucket 'Sem Info' com base nas operações carregadas
                try {
                    const ops = Array.isArray(window.currentOperations) ? window.currentOperations : [];
                    // Aqui, 'data' não está definido neste escopo, então este bloco deve ser removido ou ajustado.
                    // Se necessário, adicione lógica de recriação do gráfico aqui.
                } catch(e){ console.warn('[URF_CHART] Ajuste Sem Info falhou', e); }
            }
        }
    });
    // Adicione lógica para recriar os gráficos ausentes, se necessário
}

async function initializeDashboard() {
    // Check if user has company warning - exit early if so
    if (window.showCompanyWarning) {
        console.log('[DASHBOARD_EXECUTIVO] Dashboard bloqueado - usuário sem empresas vinculadas');
        return;
    }
    
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
        searchFields: ['ref_unique', 'ref_importador', 'importador', 'exportador_fornecedor', 'modal', 'status_timeline', 'status_processo', 'status_macro_sistema', 'mercadoria', 'urf_despacho_normalizado', 'urf_despacho'],
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
        
        // CORREÇÃO: Tratar "N/A" como valor inválido no fallback URF
        const urfValue = (operation.urf_despacho_normalizado && operation.urf_despacho_normalizado !== 'N/A') 
                         ? operation.urf_despacho_normalizado 
                         : (operation.urf_despacho || '-');
        const urfColumn = `<td>${urfValue}</td>`;
        
        // Truncar Exportador/Fornecedor para 18 caracteres
        const exportadorFull = operation.exportador_fornecedor || '-';
        const exportadorDisplay = (exportadorFull && exportadorFull.length > 18)
            ? exportadorFull.substring(0, 18) + '…'
            : exportadorFull;
        
        // CORREÇÃO: Mostrar status_sistema (campo existe na view vw_importacoes_6_meses_abertos_dash)
        // Se não houver status_sistema, usar fallback
        let statusDisplay = operation.status_sistema;
        
        // Debug para identificar problema
        if (!statusDisplay && globalIndex === 0) {
            console.warn('[STATUS_DEBUG] Primeiro registro sem status_sistema:', operation);
            console.warn('[STATUS_DEBUG] Campos disponíveis:', Object.keys(operation));
        }
        
        // Fallback se status_sistema estiver vazio
        if (!statusDisplay || statusDisplay.trim() === '') {
            statusDisplay = operation.status_processo || operation.status || 'Sem Info';
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
            <td title="${exportadorFull}">${exportadorDisplay}</td>
            <td>${getModalBadge(operation.modal)}</td>
            <td>${getStatusBadge(statusDisplay)}</td>
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
        { name: 'Países', loadFunction: () => loadPaisesProcedenciaWithRetry() },
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
 * IMPORTANTE: KPIs sempre carregam SEM filtro de kpi_status
 */
async function loadDashboardKPIs() {
    try {
        console.log('[DASHBOARD_EXECUTIVO] Carregando KPIs...');
        const queryString = buildFilterQueryString(true); // true = excluir kpi_status
        const response = await fetchWithAbort('kpis', `/dashboard-executivo/api/kpis?${queryString}`);
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
 * IMPORTANTE: KPIs sempre carregam SEM filtro de kpi_status
 */
async function loadDashboardKPIsWithCache() {
    try {
        console.log('[DASHBOARD_EXECUTIVO] Carregando KPIs com cache...');
        const queryString = buildFilterQueryString(true); // true = excluir kpi_status
        const response = await fetchWithAbort('kpis', `/dashboard-executivo/api/kpis?${queryString}`);
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
 * IMPORTANTE: KPIs sempre carregam SEM filtro de kpi_status para mostrar valores totais
 */
async function loadDashboardKPIsWithRetry(maxRetries = 2) {
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
        try {
            console.log(`[DASHBOARD_EXECUTIVO] Carregando KPIs (tentativa ${attempt}/${maxRetries})...`);
            
            // NOVO: Construir query string SEM kpi_status para KPIs mostrarem valores totais
            const queryString = buildFilterQueryString(true); // true = excluir kpi_status
            
            const response = await fetchWithAbort('kpis', `/dashboard-executivo/api/kpis?${queryString}`);
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
        const response = await fetchWithAbort('charts', `/dashboard-executivo/api/charts?${queryString}`);
        const result = await response.json();
        if (result.success) {
            // Processar permissão de materiais
            if (typeof result.can_view_materials !== 'undefined') {
                window.canViewMaterials = result.can_view_materials;
                console.log('[MATERIAL_PERMISSION] Permissão de materiais:', window.canViewMaterials);
                if (typeof window.toggleMaterialSections === 'function') {
                    window.toggleMaterialSections(window.canViewMaterials);
                }
            }
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
        const response = await fetchWithAbort('charts', `/dashboard-executivo/api/charts?${queryString}`);
        const result = await response.json();
        if (result.success) {
            // Processar permissão de materiais
            if (typeof result.can_view_materials !== 'undefined') {
                window.canViewMaterials = result.can_view_materials;
                console.log('[MATERIAL_PERMISSION] Permissão de materiais:', window.canViewMaterials);
                if (typeof window.toggleMaterialSections === 'function') {
                    window.toggleMaterialSections(window.canViewMaterials);
                }
            }
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
            const response = await fetchWithAbort('charts', `/dashboard-executivo/api/charts?${queryString}`);
            const result = await response.json();
            if (result.success && result.charts) {
                console.log('[DASHBOARD_EXECUTIVO] Gráficos carregados com sucesso');
                // Processar permissão de materiais
                if (typeof result.can_view_materials !== 'undefined') {
                    window.canViewMaterials = result.can_view_materials;
                    console.log('[MATERIAL_PERMISSION] Permissão de materiais:', window.canViewMaterials);
                    if (typeof window.toggleMaterialSections === 'function') {
                        window.toggleMaterialSections(window.canViewMaterials);
                    }
                }
                dashboardCache.set('charts', result.charts);
                createDashboardChartsWithValidation(result.charts);
                return;
            } else {
                throw new Error(result.error || 'Gráficos não encontrados');
            }
        } catch (error) {
            console.warn(`[DASHBOARD_EXECUTIVO] Tentativa ${attempt} de gráficos falhou:`, error.message);
            if (attempt === maxRetries) {
                const cachedCharts = dashboardCache.get('charts');
                if (cachedCharts) {
                    console.log('[DASHBOARD_EXECUTIVO] Usando gráficos do cache como fallback');
                    createDashboardChartsWithValidation(cachedCharts);
                    return;
                }
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
        const response = await fetchWithAbort('operations', `/dashboard-executivo/api/recent-operations?${queryString}`);
        const result = await response.json();
        if (result.success) {
            // CORREÇÃO: Usar dados completos para mini popups E modal
            if (result.operations_all) {
                // Armazenar dados completos para mini popups E modal
                if (!window.dashboardData) {
                    window.dashboardData = {};
                }
                window.dashboardData.data = result.operations_all;
                console.log('[DASHBOARD_EXECUTIVO] Dados completos para mini popups:', result.operations_all.length);
                
                // CORREÇÃO BUG: Usar operations_all (dados completos) para a tabela E modal
                // operations_all contém TODOS os campos incluindo pais_procedencia
                updateRecentOperationsTable(result.operations_all);
            } else {
                // Fallback: usar operations se operations_all não existir
                updateRecentOperationsTable(result.operations);
            }
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
        const response = await fetchWithAbort('operations', `/dashboard-executivo/api/recent-operations?${queryString}`);
        const result = await response.json();
        if (result.success) {
            // CORREÇÃO: Usar dados completos para mini popups E modal
            if (result.operations_all) {
                // Armazenar dados completos para mini popups E modal
                if (!window.dashboardData) {
                    window.dashboardData = {};
                }
                window.dashboardData.data = result.operations_all;
                console.log('[DASHBOARD_EXECUTIVO] Dados completos para mini popups (cache):', result.operations_all.length);
                
                // CORREÇÃO BUG: Usar operations_all para cache e tabela
                dashboardCache.set('operations', result.operations_all);
                updateRecentOperationsTable(result.operations_all);
            } else {
                // Fallback: usar operations se operations_all não existir
                dashboardCache.set('operations', result.operations);
                updateRecentOperationsTable(result.operations);
            }
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
            const response = await fetchWithAbort('operations', `/dashboard-executivo/api/recent-operations?${queryString}`);
            const result = await response.json();
            if (result.success && result.operations) {
                console.log(`[DASHBOARD_EXECUTIVO] Operações carregadas: ${result.operations.length} registros`);
                
                // CORREÇÃO BUG: Usar operations_all se disponível, pois contém todos os campos
                const operationsToUse = result.operations_all || result.operations;
                dashboardCache.set('operations', operationsToUse);
                updateRecentOperationsTable(operationsToUse);
                return;
            } else {
                throw new Error(result.error || 'Operações não encontradas');
            }
        } catch (error) {
            console.warn(`[DASHBOARD_EXECUTIVO] Tentativa ${attempt} de operações falhou:`, error.message);
            if (attempt === maxRetries) {
                const cachedOperations = dashboardCache.get('operations');
                if (cachedOperations) {
                    console.log('[DASHBOARD_EXECUTIVO] Usando operações do cache como fallback');
                    updateRecentOperationsTable(cachedOperations);
                    return;
                }
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
            const response = await fetchWithAbort('filter-options', '/dashboard-executivo/api/filter-options');
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
                const cachedOptions = dashboardCache.get('filterOptions');
                if (cachedOptions) {
                    console.log('[DASHBOARD_EXECUTIVO] Usando filtros do cache como fallback');
                    populateFilterOptions(cachedOptions);
                    return;
                }
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

// ===== Request deduplication: abort previous in-flight requests per endpoint =====
const requestControllers = {};
function fetchWithAbort(key, url, options = {}) {
    try {
        if (requestControllers[key]) {
            requestControllers[key].abort();
        }
        const controller = new AbortController();
        requestControllers[key] = controller;
        const opts = { ...(options || {}), signal: controller.signal };
        return fetch(url, opts);
    } catch (e) {
        return fetch(url, options);
    }
}

// ...existing code...

async function loadMonthlyChart(granularidade) {
    try {
        const filterQueryString = buildFilterQueryString();
        const separator = filterQueryString ? '&' : '';
        const url = `/dashboard-executivo/api/monthly-chart?granularidade=${granularidade}${separator}${filterQueryString}`;
        console.log(`[DASHBOARD_EXECUTIVO] Carregando gráfico ${granularidade} com filtros:`, url);
        const response = await fetchWithAbort('monthly', url);
        const result = await response.json();
        if (result.success) {
            createMonthlyChart({
                labels: result.data.periods,
                datasets: [
                    {
                        label: 'Quantidade de Processos',
                        data: result.data.processes,
                        type: 'line',
                        borderColor: DASH_COLORS.processos,
                        backgroundColor: 'rgba(0, 123, 255, 0.08)',
                        yAxisID: 'y1',
                        tension: 0.4
                    },
                    {
                        label: 'Custo Total (R$)',
                        data: result.data.values,
                        type: 'line',
                        borderColor: DASH_COLORS.custo,
                        backgroundColor: 'rgba(40, 167, 69, 0.08)',
                        yAxisID: 'y',
                        tension: 0.4
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
    
    // CORREÇÃO: Armazenar também em window.dashboardData para consistência com mini popups
    if (!window.dashboardData) {
        window.dashboardData = {};
    }
    window.dashboardData.data = sortedOperations;
    
    console.log('[DASHBOARD_EXECUTIVO] Operações armazenadas globalmente:', window.currentOperations.length);
    console.log('[DASHBOARD_EXECUTIVO] Dados também em window.dashboardData.data para mini popups');
    
    // Debug: verificar campos disponíveis no primeiro item
    if (sortedOperations.length > 0) {
        console.log('[DASHBOARD_EXECUTIVO] Campos disponíveis no primeiro item:', Object.keys(sortedOperations[0]));
        console.log('[DASHBOARD_EXECUTIVO] Primeiro item completo:', sortedOperations[0]);
        
        // DEBUG ESPECÍFICO: Verificar se data_fechamento está presente no processo 5360
        const processo5360 = sortedOperations.find(op => op.ref_unique && op.ref_unique.includes('5360'));
        if (processo5360) {
            console.log('[DASHBOARD_EXECUTIVO] *** PROCESSO 5360 NO ARRAY GLOBAL ***');
            console.log('[DASHBOARD_EXECUTIVO] data_fechamento presente?', 'data_fechamento' in processo5360);
            console.log('[DASHBOARD_EXECUTIVO] data_fechamento valor:', processo5360.data_fechamento);
            console.log('[DASHBOARD_EXECUTIVO] Campos de data disponíveis:', Object.keys(processo5360).filter(k => k.includes('data')));
        }
    }
    
    // Then set data to enhanced table (this triggers render)
    recentOperationsTable.setData(sortedOperations);
    
    // Inicializar filtros de coluna após carregar dados
    if (typeof window.initColumnFilters === 'function') {
        console.log('[DASHBOARD_EXECUTIVO] Inicializando filtros de coluna...');
        setTimeout(() => {
            window.initColumnFilters('recent-operations-table');
        }, 500);
    } else {
        console.warn('[DASHBOARD_EXECUTIVO] Função initColumnFilters não encontrada');
    }
    
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

// Global safe value display helper
function safeValue(v, placeholder = 'n/a') {
    if (v === null || v === undefined) return placeholder;
    if (typeof v === 'string') {
        const trimmed = v.trim();
        if (!trimmed || trimmed === '-' || /^(null|undefined)$/i.test(trimmed)) return placeholder;
        return trimmed;
    }
    if (Number.isNaN(v)) return placeholder;
    return v;
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
        return 'R$ ' + Math.round(value / 1e6) + ' m';
    } else if (abs >= 1e3) {
        return 'R$ ' + Math.round(value / 1e3) + ' k';
    } else {
        return formatCurrency(value);
    }
}

// Helper: choose readable text color based on background color
function getContrastTextColor(bgColor) {
    try {
        let r, g, b;
        if (typeof bgColor === 'string' && bgColor.startsWith('#')) {
            const hex = bgColor.replace('#', '');
            const full = hex.length === 3 ? hex.split('').map(h => h + h).join('') : hex;
            const bigint = parseInt(full, 16);
            r = (bigint >> 16) & 255; g = (bigint >> 8) & 255; b = bigint & 255;
        } else if (typeof bgColor === 'string' && bgColor.startsWith('rgb')) {
            const parts = bgColor.replace(/rgba?\(|\)|\s/g, '').split(',');
            r = parseInt(parts[0]); g = parseInt(parts[1]); b = parseInt(parts[2]);
        } else {
            return '#111';
        }
        const lum = (c) => { c /= 255; return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); };
        const L = 0.2126 * lum(r) + 0.7152 * lum(g) + 0.0722 * lum(b);
        return L > 0.5 ? '#111' : '#fff';
    } catch (_) { return '#111'; }
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
    
    // NOVO: Debug específico do campo pais_procedencia
    console.log('[MODAL_DEBUG] === ANÁLISE PAÍS PROCEDÊNCIA ===');
    console.log('[MODAL_DEBUG] pais_procedencia:', operation.pais_procedencia);
    console.log('[MODAL_DEBUG] pais_procedencia_normalizado:', operation.pais_procedencia_normalizado);
    console.log('[MODAL_DEBUG] url_bandeira:', operation.url_bandeira);
    console.log('[MODAL_DEBUG] Tipo pais_procedencia:', typeof operation.pais_procedencia);
    console.log('[MODAL_DEBUG] Valor após safeValue será:', safeValue(operation.pais_procedencia_normalizado || operation.pais_procedencia));
    
    // NOVO: Debug específico do campo data_fechamento
    console.log('[MODAL_DEBUG] === ANÁLISE DATA FECHAMENTO ===');
    console.log('[MODAL_DEBUG] data_fechamento:', operation.data_fechamento);
    console.log('[MODAL_DEBUG] Tipo data_fechamento:', typeof operation.data_fechamento);
    console.log('[MODAL_DEBUG] Valor após safeValue será:', safeValue(operation.data_fechamento));
    
    // Update modal title
    const modalTitle = document.getElementById('modal-title');
    if (modalTitle) {
        modalTitle.textContent = `Detalhes do Processo ${operation.ref_unique || 'N/A'}`;
        console.log('[DASHBOARD_EXECUTIVO] Título do modal atualizado para:', operation.ref_unique);
    }
    
    // Update timeline - extract numeric value from status_timeline like "2 - Agd Embarque"
    console.log('[TIMELINE_DEBUG] Status timeline original:', operation.status_timeline);
    console.log('[TIMELINE_DEBUG] Status processo fallback:', operation.status_processo);
    console.log('[TIMELINE_DEBUG] Status macro fallback:', operation.status_macro_sistema);
    
    // CORREÇÃO: Usar função do process_modal.js que suporta 6 etapas
    if (typeof window.openProcessModal === 'undefined') {
        // Se a função do process_modal.js não estiver disponível, usar a local
        const statusTimeline = operation.status_timeline || operation.status_processo || operation.status_macro_sistema;
        console.log('[TIMELINE_DEBUG] Usando função local - Status final:', statusTimeline);
        updateProcessTimelineFromStatusTimeline(statusTimeline);
    } else {
        // Usar a função correta do process_modal.js (6 etapas)
        const statusTimelineNumber = extractTimelineNumber(operation.status_timeline);
        console.log('[TIMELINE_DEBUG] Usando função do process_modal.js - Número extraído:', statusTimelineNumber);
        updateProcessTimeline(statusTimelineNumber);
    }
    
    // Update general information
    updateElementValue('detail-ref-unique', operation.ref_unique);
    updateElementValue('detail-ref-importador', operation.ref_importador);
    updateElementValue('detail-data-abertura', operation.data_abertura);
    updateElementValue('detail-importador', operation.importador);
    updateElementValue('detail-exportador', operation.exportador_fornecedor);
    updateElementValue('detail-cnpj', formatCNPJ(operation.cnpj_importador));
    
    // CORREÇÃO: Mostrar status_sistema (campo existe na view vw_importacoes_6_meses_abertos_dash)
    let statusToDisplay = operation.status_sistema;
    
    console.log('[MODAL_DEBUG] ========================================');
    console.log('[MODAL_DEBUG] DASHBOARD.JS - STATUS PROCESSING');
    console.log('[MODAL_DEBUG] status_sistema:', operation.status_sistema);
    console.log('[MODAL_DEBUG] Campos disponíveis:', Object.keys(operation));
    
    // Fallback se status_sistema estiver vazio
    if (!statusToDisplay || statusToDisplay.trim() === '') {
        console.log('[MODAL_DEBUG] status_sistema vazio, usando fallback...');
        statusToDisplay = operation.status_processo || operation.status || 'Sem Informação';
    }
    
    console.log('[MODAL_DEBUG] Status final para exibição:', statusToDisplay);
    console.log('[MODAL_DEBUG] ========================================');
    
    updateElementValue('detail-status', statusToDisplay);
    
    // CORREÇÃO: Remover referências a elementos inexistentes no template
    // Os elementos 'detail-country-name' e 'detail-country-flag' não existem no process_modal.html
    // Removido para evitar erro "Cannot read properties of null"
    
    // Update cargo and transport details
    updateElementValue('detail-modal', operation.modal);
    updateContainerField(operation.container); // NOVO: Função para processar containers múltiplos
    updateElementValue('detail-data-embarque', operation.data_embarque);
    updateElementValue('detail-data-chegada', operation.data_chegada);
    updateElementValue('detail-data-fechamento', operation.data_fechamento); // NOVA data
    updateElementValue('detail-transit-time', operation.transit_time_real ? operation.transit_time_real + ' dias' : null);
    updateElementValue('detail-peso-bruto', operation.peso_bruto ? formatNumber(operation.peso_bruto) + ' Kg' : null);
    
    // Update customs information
    updateElementValue('detail-numero-di', operation.numero_di);
    updateElementValue('detail-data-registro', operation.data_registro);
    updateElementValue('detail-canal', operation.canal, true);
    updateElementValue('detail-data-desembaraco', operation.data_desembaraco);
    updateElementValue('detail-pais-procedencia', operation.pais_procedencia_normalizado || operation.pais_procedencia);
    // CORREÇÃO: Tratar "N/A" como valor inválido no fallback
    const urfDespacho = (operation.urf_despacho_normalizado && operation.urf_despacho_normalizado !== 'N/A') 
                        ? operation.urf_despacho_normalizado 
                        : operation.urf_despacho;
    updateElementValue('detail-urf-despacho', urfDespacho);
    
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
    
    // ATUALIZADO: Mapear status_processo ou status_timeline para steps (6 etapas)
    // 1. Abertura, 2. Embarque, 3. Chegada, 4. Registro, 5. Desembaraço, 6. Finalizado
    const timelineMap = {
        // Estágio 1: Aberto/Aguardando Embarque
        'ABERTO': 1,
        'ABERTURA': 1,
        'PROCESSO ABERTO': 1,
        'AGUARDANDO EMBARQUE': 1,
        'MERCADORIA EMBARCADA': 1,
        
        // Estágio 2: Embarque/Em Trânsito
        'EMBARQUE': 2, 
        'EMBARCADO': 2,
        'EM TRANSITO': 2,
        'EMBARQUE CONFIRMADO': 2,
        'MERCADORIA EM TRANSITO': 2,
        
        // Estágio 3: Chegada
        'CHEGADA': 3,
        'CHEGOU': 3,
        'CHEGADA CONFIRMADA': 3,
        'MERCADORIA CHEGOU': 3,
        'AGUARDANDO CHEGADA': 3,
        
        // Estágio 4: Registro
        'REGISTRO': 4,
        'REGISTRADO': 4,
        'DI REGISTRADA': 4,
        'DECLARACAO REGISTRADA': 4,
        'NUMERARIO ENVIADO': 4,
        'NUMERÁRIO ENVIADO': 4,
        'DI AGUARDANDO PARAMETRIZACAO': 4,
        'DI AGUARDANDO PARAMETRIZAÇÃO': 4,
        'DI ALTERADA PELO USUÁRIO': 4,
        'DI ALTERADA PELO USUARIO': 4,
        'PREENCHIMENTO DA DECLARAÇÃO DE IMPORTAÇÃO ESTÁ OK.': 4,
        'PREENCHIMENTO DA DECLARACAO DE IMPORTACAO ESTA OK.': 4,
        'DECLARAÇÃO DE IMPORTAÇÃO NÃO FOI REGISTRADA': 4,
        'DECLARACAO DE IMPORTACAO NAO FOI REGISTRADA': 4,
        
        // Estágio 5: Desembaraço
        'DESEMBARACO': 5,
        'DESEMBARAÇO': 5,
        'DESEMBARACADO': 5,
        'LIBERADO': 5,
        'DECLARACAO DESEMBARACADA': 5,
        'DECLARAÇÃO DESEMBARAÇADA': 5,
        'DESEMBARACO AUTORIZADO': 5,
        'DESEMBARAÇO AUTORIZADO': 5,
        
        // Estágio 6: Finalizado
        'FINALIZADO': 6,
        'PROCESSO CONCLUIDO': 6,
        'PROCESSO CONCLUÍDO': 6,
        'CONCLUIDO': 6,
        'CONCLUÍDO': 6,
        'ENTREGUE': 6
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
            if (numero >= 1 && numero <= 6) {
                // Mapear números para steps (1-6 são diretos)
                currentStep = numero;
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
    
    // Suportar múltiplos separadores: vírgula, ponto e vírgula, quebra de linha
    const rawParts = containerValue
        .split(/[,;\n]/)
        .map(c => c.trim())
        .filter(c => c.length > 0);

    // Sanitizar (remover pontos, traços, espaços) e upper + deduplicar preservando ordem
    const seen = new Set();
    const containers = [];
    rawParts.forEach(raw => {
        const sanitized = raw.replace(/[.\-\s]/g, '').toUpperCase();
        if (sanitized && !seen.has(sanitized)) {
            seen.add(sanitized);
            containers.push(sanitized);
        }
    });

    if (containers.length === 0) {
        containerElement.innerHTML = '-';
        return;
    }

    // Montar links externos direto para SeaRates (abrir em nova aba)
    const linksHtml = containers.map(ctn => {
        const url = `https://www.searates.com/container/tracking/?number=${encodeURIComponent(ctn)}&sealine=AUTO`;
        return `<a class="container-tag" href="${url}" target="_blank" rel="noopener" title="Abrir rastreamento em nova aba: ${ctn}">${ctn}</a>`;
    }).join('');

    containerElement.innerHTML = linksHtml;
    console.log(`[MODAL_DEBUG] Containers renderizados como links externos:`, containers);
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
            const displayValue = safeValue(value);
            element.textContent = displayValue;
            console.log(`[MODAL_DEBUG] Elemento ${elementId} atualizado com: "${displayValue}"`);
        }
    } else {
        console.warn(`[MODAL_DEBUG] Elemento ${elementId} não encontrado no DOM - operação ignorada`);
    }
}

/**
 * Processar despesas por categoria do campo JSON despesas_processo
 * VERSÃO DINÂMICA - mantém categorias exatamente como vêm do banco de dados
 */
function processExpensesByCategory(despesasProcesso) {
    try {
        console.log('[DASHBOARD_EXECUTIVO] === INÍCIO processExpensesByCategory (DINÂMICO) ===');
        console.log('[DASHBOARD_EXECUTIVO] Entrada - despesasProcesso:', despesasProcesso);
        console.log('[DASHBOARD_EXECUTIVO] Tipo:', typeof despesasProcesso);
        console.log('[DASHBOARD_EXECUTIVO] É array:', Array.isArray(despesasProcesso));
        
        if (!despesasProcesso || !Array.isArray(despesasProcesso)) {
            console.warn('[DASHBOARD_EXECUTIVO] Despesas processo não é um array válido:', despesasProcesso);
            return {
                categorias: {},
                total: 0,
                categoriasAjustadas: {}
            };
        }

        const categorias = {};
        let total = 0;

        console.log('[DASHBOARD_EXECUTIVO] Processando', despesasProcesso.length, 'despesas...');

        despesasProcesso.forEach((despesa, index) => {
            console.log(`[DASHBOARD_EXECUTIVO] Despesa ${index + 1}:`, despesa);
            
            // Categoria exatamente como vem do banco
            const categoria = despesa.categoria_custo || 'Outros Custos';
            const valorStr = despesa.valor_custo;
            const valor = parseFloat(valorStr) || 0;
            
            console.log(`[DASHBOARD_EXECUTIVO] Processando: categoria="${categoria}", valorStr="${valorStr}", valor=${valor}`);

            // Acumular valor na categoria
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
        console.log('[DASHBOARD_EXECUTIVO] === FIM processExpensesByCategory (DINÂMICO) ===');

        // Retornar categorias exatamente como foram calculadas (sem ajustes)
        return {
            categorias: categorias,
            total: total,
            categoriasAjustadas: categorias // Mesmo objeto, sem ajustes
        };

    } catch (error) {
        console.error('[DASHBOARD_EXECUTIVO] Erro ao processar despesas por categoria:', error);
        return {
            categorias: {},
            total: 0,
            categoriasAjustadas: {}
        };
    }
}

/**
 * Gerar HTML para o novo resumo financeiro - VERSÃO DINÂMICA
 * Renderiza automaticamente todas as categorias vindas do banco de dados
 * Não requer alteração de código ao adicionar/remover categorias
 */
function generateFinancialSummaryHTML(expenseData, valorCif = 0) {
    try {
        const { categorias, categoriasAjustadas, fretes, total } = expenseData;

        let html = '';

        // CORREÇÃO: Só mostrar Valor CIF se for maior que 0
        if (valorCif > 0) {
            html += `
                <div class="info-item valor-cif-item">
                    <label>Valor CIF (R$):</label>
                    <span>${formatCurrency(valorCif)}</span>
                </div>
            `;
        }

        // Usar categorias ajustadas se disponível, senão usar categorias originais
        const catAdj = categoriasAjustadas && Object.keys(categoriasAjustadas).length ? categoriasAjustadas : categorias;
        
        // NOVA LÓGICA DINÂMICA: Renderizar TODAS as categorias que vieram do banco
        // Ordenar alfabeticamente para consistência visual
        const categoriasOrdenadas = Object.entries(catAdj || {})
            .filter(([k, v]) => v > 0) // Só mostrar categorias com valor > 0
            .sort(([a], [b]) => a.localeCompare(b, 'pt-BR')); // Ordem alfabética
        
        console.log('[DASHBOARD_EXECUTIVO] Categorias dinâmicas ordenadas:', categoriasOrdenadas);
        
        // Renderizar cada categoria dinamicamente
        categoriasOrdenadas.forEach(([categoria, valor]) => {
            html += `
                <div class="info-item">
                    <label>${categoria} (R$):</label>
                    <span>${formatCurrency(valor)}</span>
                </div>
            `;
        });

        // Total com destaque (sempre ao final)
        html += `
            <div class="info-item total-item">
                <label>Custo Total (R$):</label>
                <span class="total-value">${formatCurrency(total)}</span>
            </div>
        `;

        console.log('[DASHBOARD_EXECUTIVO] HTML dinâmico gerado com', categoriasOrdenadas.length, 'categorias');

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
 * Atualizar resumo financeiro no modal usando o novo sistema de categorias DINÂMICO
 * Renderiza automaticamente todas as categorias vindas do banco de dados
 */
function updateFinancialSummary(operation) {
    try {
        console.log('[DASHBOARD_EXECUTIVO] === INÍCIO updateFinancialSummary (DINÂMICO) ===');
        console.log('[DASHBOARD_EXECUTIVO] Atualizando resumo financeiro para operação:', operation.ref_unique);

        // LOG ESPECÍFICO PARA PROCESSO 6555 (do exemplo)
        if (operation.ref_unique && operation.ref_unique.includes('6763')) {
            console.log('[DASHBOARD_EXECUTIVO] *** PROCESSO 6763 NO FRONTEND (DINÂMICO) ***');
            console.log('[DASHBOARD_EXECUTIVO] custo_total:', operation.custo_total);
            console.log('[DASHBOARD_EXECUTIVO] custo_total_view:', operation.custo_total_view);
            console.log('[DASHBOARD_EXECUTIVO] despesas_processo disponível:', !!operation.despesas_processo);
            if (operation.despesas_processo && Array.isArray(operation.despesas_processo)) {
                console.log('[DASHBOARD_EXECUTIVO] Total de despesas:', operation.despesas_processo.length);
                console.log('[DASHBOARD_EXECUTIVO] Despesas:', operation.despesas_processo);
            }
        }

        let expenseData;
        
        // LÓGICA SIMPLIFICADA:
        // 1. Se temos despesas_processo, calcular sempre manualmente (mais confiável)
        // 2. Senão, usar custo_total do backend como fallback
        if (operation.despesas_processo && Array.isArray(operation.despesas_processo) && operation.despesas_processo.length > 0) {
            console.log('[DASHBOARD_EXECUTIVO] Calculando via despesas_processo (dinâmico)');
            expenseData = processExpensesByCategory(operation.despesas_processo);
        } else {
            console.log('[DASHBOARD_EXECUTIVO] Fallback: usando custo_total do backend');
            
            // Priorizar custo_total_view, depois custo_total
            let custoTotal = 0;
            if (operation.custo_total_view !== undefined && operation.custo_total_view !== null && operation.custo_total_view > 0) {
                custoTotal = operation.custo_total_view;
            } else if (operation.custo_total !== undefined && operation.custo_total !== null && operation.custo_total > 0) {
                custoTotal = operation.custo_total;
            }
            
            expenseData = {
                categorias: { 'Total de Custos': custoTotal },
                total: custoTotal,
                categoriasAjustadas: { 'Total de Custos': custoTotal }
            };
        }
        
        console.log('[DASHBOARD_EXECUTIVO] expenseData final:', expenseData);
        
        // Não mostrar "Valor CIF" separadamente no resumo
        const valorCif = 0;
        
        // Gerar HTML dinâmico
        const summaryHTML = generateFinancialSummaryHTML(expenseData, valorCif);

        // Atualizar o DOM
        const cardGrid = document.querySelector('#process-modal .info-card:nth-child(4) .card-grid-2');
        if (cardGrid) {
            cardGrid.innerHTML = summaryHTML;
            console.log('[DASHBOARD_EXECUTIVO] Resumo financeiro atualizado com sucesso (dinâmico)');
        } else {
            console.error('[DASHBOARD_EXECUTIVO] Elemento card-grid-2 não encontrado no modal');
        }

        console.log('[DASHBOARD_EXECUTIVO] === FIM updateFinancialSummary (DINÂMICO) ===');

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

    // NOVO: Ignorar "N/A" - retornar badge vazio
    if (typeof status === 'string' && status.trim().toUpperCase() === 'N/A') {
        console.log('[STATUS_BADGE_DEBUG] Status é N/A - retornando badge vazio');
        return '<span class="badge badge-secondary">N/A</span>';
    }

    // Se o status tem formato "2 - AG EMBARQUE", extrair apenas a parte após o traço
    let displayStatus = status;
    if (typeof status === 'string' && status.includes(' - ')) {
        displayStatus = status.split(' - ')[1].trim();
        console.log('[STATUS_BADGE_DEBUG] Status extraído:', displayStatus);
    }

    // CORREÇÃO: Pegada monocromática - todos os status usam cinza claro
    // Removido mapeamento de cores diferentes para manter design minimalista
    console.log('[STATUS_BADGE_DEBUG] Aplicando estilo monocromático para:', displayStatus);

    return `<span class="badge badge-light-monochrome">${displayStatus}</span>`;
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
    } else if (modalUpper.includes('RODOVIÁRIA') || modalUpper.includes('RODOVIARIA')) {
        return `<span class="modal-icon-badge" title="${modalUpper}"><i class="mdi mdi-truck"></i></span>`;
    } else if (modalUpper.includes('FERROVIÁRIA') || modalUpper.includes('FERROVIARIA')) {
        return `<span class="modal-icon-badge" title="${modalUpper}"><i class="mdi mdi-train"></i></span>`;
    } else if (modalUpper.includes('POSTAL') || modalUpper.includes('CORREIO')) {
        return `<span class="modal-icon-badge" title="${modalUpper}"><i class="mdi mdi-email"></i></span>`;
    } else if (modalUpper.includes('COURIER') || modalUpper.includes('EXPRESS')) {
        return `<span class="modal-icon-badge" title="${modalUpper}"><i class="mdi mdi-package-variant"></i></span>`;
    }
    
    return `<span class="modal-icon-badge" title="${modalUpper}"><i class="mdi mdi-help"></i></span>`;
}

function formatDataChegada(dateString) {
    if (!dateString) return '-';
    
    const hoje = new Date();
    const chegadaDate = parseDate(dateString);
    
    if (!chegadaDate) return formatDate(dateString);
    
    // Zerar horários para comparação apenas da data
    chegadaDate.setHours(0, 0, 0, 0);
    hoje.setHours(0, 0, 0, 0);
    
    // Se a data de chegada é exatamente hoje, mostrar indicador
    if (chegadaDate.getTime() === hoje.getTime()) {
        return `<span class="chegada-proxima">
            <i class="mdi mdi-clock"></i>
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
        const response = await fetchWithAbort('filter-options', '/dashboard-executivo/api/filter-options');
        const result = await response.json();
        if (result.success) {
            console.log('[DASHBOARD_EXECUTIVO] Opções de filtros recebidas:', {
                materiais: result.options.materiais?.length || 0,
                clientes: result.options.clientes?.length || 0,
                modais: result.options.modais?.length || 0,
                canais: result.options.canais?.length || 0
            });
            populateFilterOptions(result.options);
            dashboardCache.set('filterOptions', result.options);
        } else {
            console.error('[DASHBOARD_EXECUTIVO] Erro ao carregar opções de filtros:', result.error);
            throw new Error(result.error || 'Erro ao carregar opções de filtros');
        }
    } catch (error) {
        console.error('[DASHBOARD_EXECUTIVO] Erro ao carregar opções de filtros:', error);
        const cachedOptions = dashboardCache.get('filterOptions');
        if (cachedOptions) {
            console.log('[DASHBOARD_EXECUTIVO] Usando opções de filtros do cache como fallback');
            populateFilterOptions(cachedOptions);
        } else {
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
            
            // Remover event listeners existentes clonando o elemento
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
/**
 * Build filter query string from current filters
 * @param {boolean} excludeKpiStatus - Se true, exclui o filtro kpi_status (usado para KPIs mostrarem valores totais)
 */
function buildFilterQueryString(excludeKpiStatus = false) {
    const params = new URLSearchParams();
    
    const dataInicio = document.getElementById('data-inicio')?.value;
    const dataFim = document.getElementById('data-fim')?.value;
    
    // Get multi-select values
    const materiais = getMultiSelectValues('material');
    const clientes = getMultiSelectValues('cliente');
    const modais = getMultiSelectValues('modal');
    const canais = getMultiSelectValues('canal');
    
    if (dataInicio) params.append('data_inicio', dataInicio);
    if (dataFim) params.append('data_fim', dataFim);
    
    // Add multi-select values as comma-separated strings
    if (materiais.length > 0) params.append('material', materiais.join(','));
    if (clientes.length > 0) params.append('cliente', clientes.join(','));
    if (modais.length > 0) params.append('modal', modais.join(','));
    if (canais.length > 0) params.append('canal', canais.join(','));
    
    // NOVO: Adicionar filtro de KPI clicável apenas se não for para excluir
    if (!excludeKpiStatus && currentFilters.kpi_status) {
        params.append('kpi_status', currentFilters.kpi_status);
    }
    
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
            loadRecentOperationsWithCache(),
            loadPaisesProcedenciaWithRetry()  // CORREÇÃO: Incluir tabela de países
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
    
    // Clear stored filters (incluindo KPI filter)
    currentFilters = {};
    
    // NOVO: Remover classe active dos KPIs clicáveis
    document.querySelectorAll('.kpi-card.kpi-active').forEach(kpi => {
        kpi.classList.remove('kpi-active');
    });
    
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
        
        // Clear stored filters (incluindo KPI filter)
        currentFilters = {};
        
        // NOVO: Remover classe active dos KPIs clicáveis
        document.querySelectorAll('.kpi-card.kpi-active').forEach(kpi => {
            kpi.classList.remove('kpi-active');
        });
        
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
            loadRecentOperationsWithCache(),
            loadPaisesProcedenciaWithRetry()  // CORREÇÃO: Incluir tabela de países
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
    
    let summaryText = 'Analisando dados completos';
    
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
        tableBody.innerHTML = '<tr><td colspan="4" class="text-center">Nenhum material encontrado</td></tr>';
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
    } else if (modalLower.includes('rodoviá') || modalLower.includes('rodoviaria')) {
        iconClass = 'mdi-truck';
        cssClass = 'rodoviaria';
    } else if (modalLower.includes('ferroviá') || modalLower.includes('ferroviaria')) {
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

/**
 * Load países de procedência data with retry mechanism
 */
async function loadPaisesProcedenciaWithRetry(maxRetries = 3) {
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
        try {
            console.log(`[DASHBOARD_EXECUTIVO] Tentativa ${attempt}/${maxRetries} - Carregando países de procedência...`);
            
            // CORREÇÃO: Incluir filtros na requisição
            const queryString = buildFilterQueryString();
            const url = `/dashboard-executivo/api/paises-procedencia${queryString ? '?' + queryString : ''}`;
            console.log(`[DASHBOARD_EXECUTIVO] URL com filtros: ${url}`);
            
            const response = await fetch(url);
            const result = await response.json();
            
            if (result.success) {
                console.log(`[DASHBOARD_EXECUTIVO] Países de procedência carregados: ${result.data.length} países`);
                await renderPaisesProcedenciaTable(result.data);
                return;
            } else {
                throw new Error(result.error || 'Erro ao carregar países de procedência');
            }
            
        } catch (error) {
            console.warn(`[DASHBOARD_EXECUTIVO] Tentativa ${attempt} para países falhou:`, error.message);
            
            if (attempt === maxRetries) {
                console.error('[DASHBOARD_EXECUTIVO] Falha final ao carregar países de procedência:', error);
                showPaisesError();
            } else {
                // Wait before retry
                await new Promise(resolve => setTimeout(resolve, 1000 * attempt));
            }
        }
    }
}

/**
 * Render países de procedência table
 */
async function renderPaisesProcedenciaTable(paisesData) {
    const loadingElement = document.getElementById('paises-loading');
    const tableBody = document.querySelector('#paises-procedencia-table tbody');
    
    try {
        // Hide loading
        if (loadingElement) {
            loadingElement.style.display = 'none';
        }
        
        // Clear existing data
        if (tableBody) {
            tableBody.innerHTML = '';
        }
        
        // Check if data is empty
        if (!paisesData || paisesData.length === 0) {
            if (tableBody) {
                tableBody.innerHTML = `
                    <tr>
                        <td colspan="3" class="text-center">
                            <i class="mdi mdi-earth-off"></i>
                            Nenhum país de procedência encontrado
                        </td>
                    </tr>
                `;
            }
            return;
        }
        
        // Render table rows
        paisesData.forEach(pais => {
            const row = document.createElement('tr');
            
            // Formatar valores
            const totalCusto = formatCurrency(pais.total_custo || 0);
            const totalProcessos = (pais.total_processos || 0).toLocaleString('pt-BR');
            
            // Extrair apenas o nome do país (remove código se existir)
            let nomePais = pais.pais_procedencia || 'N/A';
            // Remove códigos como "249 - US - " e mantém apenas "ESTADOS UNIDOS"
            const match = nomePais.match(/\d+\s*-\s*[A-Z]{2}\s*-\s*(.+)/);
            if (match) {
                nomePais = match[1].trim();
            }
            
            // HTML da linha
            row.innerHTML = `
                <td class="pais-cell">
                    ${pais.url_bandeira ? 
                        `<img src="${pais.url_bandeira}" alt="${nomePais}" class="bandeira-icon" onerror="this.style.display='none';">` 
                        : '<i class="mdi mdi-earth"></i>'
                    }
                    <span class="pais-nome">${nomePais}</span>
                </td>
                <td class="text-center">
                    <span class="badge badge-info">${totalProcessos}</span>
                </td>
                <td class="text-center">
                    <span class="valor-custo">${totalCusto}</span>
                </td>
            `;
            
            if (tableBody) {
                tableBody.appendChild(row);
            }
        });
        
        console.log(`[DASHBOARD_EXECUTIVO] Tabela de países renderizada com ${paisesData.length} países`);
        
    } catch (error) {
        console.error('[DASHBOARD_EXECUTIVO] Erro ao renderizar tabela de países:', error);
        showPaisesError();
    }
}

/**
 * Show error message for países table
 */
function showPaisesError() {
    const loadingElement = document.getElementById('paises-loading');
    const tableBody = document.querySelector('#paises-procedencia-table tbody');
    
    if (loadingElement) {
        loadingElement.style.display = 'none';
    }
    
    if (tableBody) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="3" class="text-center error-message">
                    <i class="mdi mdi-alert-circle"></i>
                    Erro ao carregar dados de países
                </td>
            </tr>
        `;
    }
}

/**
 * Get country code for flag API based on country name
 */
function getCountryCode(countryName) {
    const COUNTRY_MAPPING = {
        'CHINA': 'CN',
        'ESTADOS UNIDOS': 'US',
        'ALEMANHA': 'DE',
        'JAPAO': 'JP',
        'JAPÃO': 'JP',
        'ITALIA': 'IT',
        'ITÁLIA': 'IT',
        'FRANCA': 'FR',
        'FRANÇA': 'FR',
        'COREIA DO SUL': 'KR',
        'REINO UNIDO': 'GB',
        'HOLANDA': 'NL',
        'PAISES BAIXOS': 'NL',
        'PAÍSES BAIXOS': 'NL',
        'ESPANHA': 'ES',
        'SINGAPURA': 'SG',
        'INDIA': 'IN',
        'ÍNDIA': 'IN',
        'TAILANDIA': 'TH',
        'TAILÂNDIA': 'TH',
        'TAIWAN': 'TW',
        'MALASIA': 'MY',
        'MALÁSIA': 'MY',
        'HONG KONG': 'HK',
        'VIETNAM': 'VN',
        'VIETNÃ': 'VN',
        'TURQUIA': 'TR',
        'CANADA': 'CA',
        'CANADÁ': 'CA',
        'MEXICO': 'MX',
        'MÉXICO': 'MX',
        'CHILE': 'CL',
        'ARGENTINA': 'AR',
        'COLOMBIA': 'CO',
        'COLÔMBIA': 'CO',
        'PERU': 'PE',
        'PARAGUAI': 'PY',
        'URUGUAI': 'UY',
        'BOLIVIA': 'BO',
        'BOLÍVIA': 'BO',
        'EQUADOR': 'EC',
        'VENEZUELA': 'VE',
        'AUSTRALIA': 'AU',
        'AUSTRÁLIA': 'AU',
        'NOVA ZELANDIA': 'NZ',
        'NOVA ZELÂNDIA': 'NZ',
        'RUSSIA': 'RU',
        'RÚSSIA': 'RU',
        'UCRANIA': 'UA',
        'UCRÂNIA': 'UA',
        'POLONIA': 'PL',
        'POLÔNIA': 'PL',
        'REPUBLICA TCHECA': 'CZ',
        'REPÚBLICA TCHECA': 'CZ',
        'HUNGRIA': 'HU',
        'ROMENIA': 'RO',
        'ROMÊNIA': 'RO',
        'BULGÁRIA': 'BG',
        'BULGARIA': 'BG',
        'GRECIA': 'GR',
        'GRÉCIA': 'GR',
        'PORTUGAL': 'PT',
        'SUECIA': 'SE',
        'SUÉCIA': 'SE',
        'NORUEGA': 'NO',
        'DINAMARCA': 'DK',
        'FINLANDIA': 'FI',
        'FINLÂNDIA': 'FI',
        'AUSTRIA': 'AT',
        'ÁUSTRIA': 'AT',
        'SUICA': 'CH',
        'SUÍÇA': 'CH',
        'BELGICA': 'BE',
        'BÉLGICA': 'BE',
        'LUXEMBURGO': 'LU',
        'ISRAEL': 'IL',
        'EMIRADOS ARABES UNIDOS': 'AE',
        'EMIRADOS ÁRABES UNIDOS': 'AE',
        'ARABIA SAUDITA': 'SA',
        'ARÁBIA SAUDITA': 'SA',
        'EGITO': 'EG',
        'AFRICA DO SUL': 'ZA',
        'ÁFRICA DO SUL': 'ZA',
        'MARROCOS': 'MA',
        'TUNISIA': 'TN',
        'TUNÍSIA': 'TN',
        'INDONESIA': 'ID',
        'INDONÉSIA': 'ID',
        'FILIPINAS': 'PH',
        'BANGLADESH': 'BD',
        'PAQUISTAO': 'PK',
        'PAQUISTÃO': 'PK',
        'SRI LANKA': 'LK',
        'MYANMAR': 'MM',
        'CAMBOJA': 'KH',
        'LAOS': 'LA',
        'NEPAL': 'NP',
        'BRUNEI': 'BN',
        'CAZAQUISTAO': 'KZ',
        'CAZAQUISTÃO': 'KZ',
        'UZBEQUISTAO': 'UZ',
        'UZBEQUISTÃO': 'UZ'
    };
    
    if (!countryName) return null;
    
    const normalizedName = countryName.toString().toUpperCase().trim();
    return COUNTRY_MAPPING[normalizedName] || null;
}
