// Dashboard Executivo Financeiro - JavaScript Aprimorado

// Registrar plugin ChartDataLabels
document.addEventListener('DOMContentLoaded', function() {
    if (typeof Chart !== 'undefined' && typeof ChartDataLabels !== 'undefined') {
        Chart.register(ChartDataLabels);
        console.log('✅ ChartDataLabels plugin registered');
    } else {
        console.warn('⚠️ ChartDataLabels plugin not available');
    }
});

// Estado global do dashboard
const DashboardState = {
    periodo: 'este_ano',
    empresa: 'todas',
    dataInicio: null,
    dataFim: null,
    isCustomPeriod: false,
    charts: {
        metaGauge: null
    },
    data: {
        kpis: null,
        empresas: [],
        lastUpdate: null
    }
};

document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Dashboard Executivo Financeiro loaded');
    
    // Initialize dashboard
    initializeDashboard();
    
    // Set up event listeners
    setupEventListeners();
    
    // Load initial data
    loadInitialData();
});

function initializeDashboard() {
    console.log('📊 Initializing dashboard...');
    
    // Set up current period as default
    const currentYear = new Date().getFullYear();
    
    // Initialize filters with intelligent defaults
    initializeFilters();
    
    // Initialize charts
    initializeCharts();
    
    // Setup loading states
    setupLoadingStates();
}

function initializeFilters() {
    // Set default period
    const periodoFilter = document.getElementById('periodo-filter');
    if (periodoFilter) {
        periodoFilter.value = DashboardState.periodo;
    }
    
    // Set default empresa
    const empresaFilter = document.getElementById('empresa-filter');
    if (empresaFilter) {
        empresaFilter.value = DashboardState.empresa;
    }
    
    // Load empresas list
    loadEmpresas();
    
    // Update filter summary
    updateFilterSummary();
}

function setupEventListeners() {
    console.log('🔧 Setting up event listeners...');
    
    // Período filter change
    const periodoFilter = document.getElementById('periodo-filter');
    if (periodoFilter) {
        periodoFilter.addEventListener('change', handlePeriodoChange);
    }
    
    // Custom date inputs
    const dataInicioInput = document.getElementById('data-inicio');
    const dataFimInput = document.getElementById('data-fim');
    if (dataInicioInput && dataFimInput) {
        dataInicioInput.addEventListener('change', handleCustomDateChange);
        dataFimInput.addEventListener('change', handleCustomDateChange);
    }
    
    // Empresa filter change
    const empresaFilter = document.getElementById('empresa-filter');
    if (empresaFilter) {
        empresaFilter.addEventListener('change', handleEmpresaChange);
    }
    
    // Refresh button
    const refreshButton = document.getElementById('refresh-data');
    if (refreshButton) {
        refreshButton.addEventListener('click', handleRefreshData);
    }
    
    // Reset filters button
    const resetButton = document.getElementById('reset-filters');
    if (resetButton) {
        resetButton.addEventListener('click', handleResetFilters);
    }
    
    // Back to sectors button
    const backButton = document.getElementById('back-to-sectors');
    if (backButton) {
        backButton.addEventListener('click', () => {
            isDrillDownActive = false;
            currentDrillDownSetor = null;
            loadFaturamentoPorSetor(getCurrentYear());
        });
    }
    
    // Chart action buttons
    setupChartActionListeners();
}

function setupChartActionListeners() {
    // Toggle faturamento view
    const toggleFaturamento = document.getElementById('toggle-faturamento-view');
    if (toggleFaturamento) {
        toggleFaturamento.addEventListener('click', () => {
            showNotification('Funcionalidade em desenvolvimento', 'info');
        });
    }
    
    // Toggle despesas view
    const toggleDespesas = document.getElementById('toggle-despesas-view');
    if (toggleDespesas) {
        toggleDespesas.addEventListener('click', () => {
            showNotification('Funcionalidade em desenvolvimento', 'info');
        });
    }
    
    // Toggle resultado view
    const toggleResultado = document.getElementById('toggle-resultado-view');
    if (toggleResultado) {
        toggleResultado.addEventListener('click', () => {
            showNotification('Funcionalidade em desenvolvimento', 'info');
        });
    }
    
    // Export clientes
    const exportClientes = document.getElementById('export-clientes');
    if (exportClientes) {
        exportClientes.addEventListener('click', handleExportClientes);
    }
}

// ==========================================
// FILTER HANDLERS - Filtros Inteligentes
// ==========================================

function handlePeriodoChange(event) {
    const selectedPeriodo = event.target.value;
    DashboardState.periodo = selectedPeriodo;
    
    // Show/hide custom date inputs
    const customDateGroup = document.getElementById('custom-date-group');
    const customDateEndGroup = document.getElementById('custom-date-end-group');
    
    if (selectedPeriodo === 'personalizado') {
        DashboardState.isCustomPeriod = true;
        if (customDateGroup) customDateGroup.style.display = 'flex';
        if (customDateEndGroup) customDateEndGroup.style.display = 'flex';
        
        // Set default dates for current year
        const currentYear = new Date().getFullYear();
        const dataInicio = document.getElementById('data-inicio');
        const dataFim = document.getElementById('data-fim');
        
        if (dataInicio && !dataInicio.value) {
            dataInicio.value = `${currentYear}-01-01`;
        }
        if (dataFim && !dataFim.value) {
            dataFim.value = `${currentYear}-12-31`;
        }
    } else {
        DashboardState.isCustomPeriod = false;
        if (customDateGroup) customDateGroup.style.display = 'none';
        if (customDateEndGroup) customDateEndGroup.style.display = 'none';
        
        // Clear custom dates
        DashboardState.dataInicio = null;
        DashboardState.dataFim = null;
    }
    
    updateFilterSummary();
    updateResetButton();
    
    // Only reload data if not custom period (custom dates need to be set first)
    if (!DashboardState.isCustomPeriod) {
        loadAllData();
    }
}

function handleCustomDateChange() {
    const dataInicio = document.getElementById('data-inicio');
    const dataFim = document.getElementById('data-fim');
    
    if (dataInicio && dataFim && dataInicio.value && dataFim.value) {
        DashboardState.dataInicio = dataInicio.value;
        DashboardState.dataFim = dataFim.value;
        
        updateFilterSummary();
        updateResetButton();
        loadAllData();
    }
}

function handleEmpresaChange(event) {
    DashboardState.empresa = event.target.value;
    updateFilterSummary();
    updateResetButton();
    loadAllData();
}

function handleRefreshData() {
    showNotification('Atualizando dados...', 'info');
    loadAllData();
}

function handleResetFilters() {
    // Reset to defaults
    DashboardState.periodo = 'este_ano';
    DashboardState.empresa = 'todas';
    DashboardState.dataInicio = null;
    DashboardState.dataFim = null;
    DashboardState.isCustomPeriod = false;
    
    // Update UI
    const periodoFilter = document.getElementById('periodo-filter');
    const empresaFilter = document.getElementById('empresa-filter');
    const customDateGroup = document.getElementById('custom-date-group');
    const customDateEndGroup = document.getElementById('custom-date-end-group');
    
    if (periodoFilter) periodoFilter.value = 'este_ano';
    if (empresaFilter) empresaFilter.value = 'todas';
    if (customDateGroup) customDateGroup.style.display = 'none';
    if (customDateEndGroup) customDateEndGroup.style.display = 'none';
    
    updateFilterSummary();
    updateResetButton();
    loadAllData();
    
    showNotification('Filtros resetados', 'success');
}

function handleExportClientes() {
    // TODO: Implement CSV export of top clients
    showNotification('Funcionalidade de exportação em desenvolvimento', 'info');
}

// ==========================================
// DATA LOADING FUNCTIONS
// ==========================================

function loadInitialData() {
    showLoading();
    
    Promise.all([
        loadEmpresas(),
        loadAllData()
    ]).then(() => {
        hideLoading();
        DashboardState.data.lastUpdate = new Date();
        updateLastUpdateInfo();
    }).catch(error => {
        console.error('❌ Error loading initial data:', error);
        hideLoading();
        showError('Erro ao carregar dados iniciais');
    });
}

function loadAllData() {
    console.log('📡 Loading all dashboard data...');
    showLoading();
    
    const dateParams = getDateParams();
    
    // Load all data in parallel
    Promise.all([
        loadKPIs(dateParams),
        loadResultadoMensal(dateParams),
        loadFaturamentoPorSetor(dateParams),
        loadFaturamentoSunburst(dateParams),
        loadProjecoesSaldo(dateParams), // Esta função agora cuida do gráfico de saldo acumulado
        loadTopDespesas(dateParams),
        loadTopClientes(dateParams),
        loadFaturamentoMensal(dateParams),
        loadMetaAtingimento(dateParams)
    ]).then(() => {
        hideLoading();
        DashboardState.data.lastUpdate = new Date();
        updateLastUpdateInfo();
        showNotification('Dados atualizados com sucesso', 'success');
    }).catch(error => {
        console.error('❌ Error loading data:', error);
        hideLoading();
        showError('Erro ao carregar dados do dashboard');
    });
}

function loadEmpresas() {
    return fetch('/financeiro/faturamento/api/empresas')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                DashboardState.data.empresas = data.data;
                updateEmpresasFilter();
            }
        })
        .catch(error => {
            console.error('❌ Error loading empresas:', error);
        });
}

function loadKPIs(dateParams) {
    console.log('📊 Loading KPIs...');
    
    const url = `/financeiro/dashboard-executivo/api/kpis?${new URLSearchParams(dateParams)}`;
    
    return fetch(url)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                DashboardState.data.kpis = data.data;
                updateKPIs(data.data);
                updateMargems(data.data); // Calculate derived metrics
            }
        });
}

function loadResultadoMensal(dateParams) {
    const url = `/financeiro/dashboard-executivo/api/resultado-mensal?${new URLSearchParams(dateParams)}`;
    
    return fetch(url)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateResultadoMensalChart(data.data);
            }
        });
}

function loadSaldoAcumulado(dateParams) {
    const url = `/financeiro/dashboard-executivo/api/saldo-acumulado?${new URLSearchParams(dateParams)}`;
    
    return fetch(url)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateSaldoAcumuladoChart(data.data);
            }
        });
}

function loadFaturamentoPorSetor(dateParams) {
    const url = `/financeiro/dashboard-executivo/api/faturamento-sunburst?${new URLSearchParams(dateParams)}`;
    
    return fetch(url)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateFaturamentoSunburst(data.data);
            }
        });
}

function loadTopDespesas(dateParams) {
    const url = `/financeiro/dashboard-executivo/api/top-despesas?${new URLSearchParams(dateParams)}`;
    
    return fetch(url)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateTopDespesasChart(data.data);
            }
        });
}

function loadTopClientes(dateParams) {
    const url = `/financeiro/dashboard-executivo/api/top-clientes?${new URLSearchParams(dateParams)}`;
    
    return fetch(url)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateTopClientes(data.data);
            }
        });
}

function loadFaturamentoMensal(dateParams) {
    const url = `/financeiro/faturamento/api/geral/mensal?${new URLSearchParams(dateParams)}`;
    
    return fetch(url)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateFaturamentoMensalChart(data.data);
            }
        });
}

function loadMetaAtingimento(dateParams) {
    console.log('📊 Loading metas segmentadas data...');
    
    const url = `/financeiro/dashboard-executivo/api/metas-segmentadas?${new URLSearchParams(dateParams)}`;
    
    return fetch(url)
        .then(response => response.json())
        .then(data => {
            console.log('📊 Metas segmentadas data:', data);
            
            if (data.success) {
                updateMetasSegmentadas(data.data);
            } else {
                console.error('❌ Error loading metas segmentadas:', data.error);
                updateMetasSegmentadas(null);
            }
        })
        .catch(error => {
            console.error('❌ Error loading metas segmentadas:', error);
            updateMetasSegmentadas(null);
        });
}

function loadFaturamentoSunburst(dateParams) {
    console.log('🌻 Loading faturamento sunburst data...');
    
    const url = `/financeiro/dashboard-executivo/api/faturamento-sunburst?${new URLSearchParams(dateParams)}`;
    
    return fetch(url)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateFaturamentoSunburst(data.data);
            }
        });
}

function loadProjecoesSaldo(dateParams) {
    console.log('📈 Loading projecoes saldo data (replicando fluxo de caixa)...');
    
    const url = `/financeiro/dashboard-executivo/api/projecoes-saldo?${new URLSearchParams(dateParams)}`;
    
    return fetch(url)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Armazenar os dados para usar no updateSaldoAcumuladoChart
                DashboardState.data.saldoProjecao = data.data;
                updateSaldoAcumuladoChart(data.data);
            } else {
                console.error('❌ Error loading saldo projecao:', data.error);
            }
        })
        .catch(error => {
            console.error('❌ Error in loadProjecoesSaldo:', error);
        });
}

// ==========================================
// UTILITY FUNCTIONS
// ==========================================

function getDateParams() {
    const params = {};
    
    if (DashboardState.isCustomPeriod && DashboardState.dataInicio && DashboardState.dataFim) {
        params.start_date = DashboardState.dataInicio;
        params.end_date = DashboardState.dataFim;
    } else {
        const currentYear = new Date().getFullYear();
        
        switch (DashboardState.periodo) {
            case 'este_ano':
                params.ano = currentYear;
                break;
            case 'este_mes':
                params.ano = currentYear;
                params.mes = new Date().getMonth() + 1;
                break;
            case 'ultimos_12_meses':
                const lastYear = new Date();
                lastYear.setFullYear(lastYear.getFullYear() - 1);
                params.start_date = lastYear.toISOString().split('T')[0];
                params.end_date = new Date().toISOString().split('T')[0];
                break;
            case 'ano_anterior':
                params.ano = currentYear - 1;
                break;
            case 'trimestre_atual':
                const currentMonth = new Date().getMonth();
                const currentQuarter = Math.floor(currentMonth / 3) + 1;
                const quarterStart = (currentQuarter - 1) * 3 + 1;
                const quarterEnd = currentQuarter * 3;
                params.start_date = `${currentYear}-${quarterStart.toString().padStart(2, '0')}-01`;
                params.end_date = `${currentYear}-${quarterEnd.toString().padStart(2, '0')}-31`;
                break;
        }
    }
    
    if (DashboardState.empresa !== 'todas') {
        params.empresa = DashboardState.empresa;
    }
    
    return params;
}

function getCurrentYear() {
    if (DashboardState.isCustomPeriod && DashboardState.dataInicio) {
        return new Date(DashboardState.dataInicio).getFullYear();
    }
    
    switch (DashboardState.periodo) {
        case 'ano_anterior':
            return new Date().getFullYear() - 1;
        default:
            return new Date().getFullYear();
    }
}

function updateFilterSummary() {
    const filterSummary = document.getElementById('filter-summary');
    const filterSummaryText = document.getElementById('filter-summary-text');
    
    if (!filterSummary || !filterSummaryText) return;
    
    let summaryText = '';
    
    // Period summary
    const periodoMap = {
        'este_ano': 'Este Ano',
        'este_mes': 'Este Mês',
        'ultimos_12_meses': 'Últimos 12 Meses',
        'ano_anterior': 'Ano Anterior',
        'trimestre_atual': 'Trimestre Atual',
        'personalizado': 'Período Personalizado'
    };
    
    summaryText += periodoMap[DashboardState.periodo] || 'Este Ano';
    
    if (DashboardState.isCustomPeriod && DashboardState.dataInicio && DashboardState.dataFim) {
        summaryText += ` (${formatDate(DashboardState.dataInicio)} - ${formatDate(DashboardState.dataFim)})`;
    }
    
    // Empresa summary
    if (DashboardState.empresa !== 'todas') {
        summaryText += ` • Empresa: ${DashboardState.empresa}`;
    }
    
    filterSummaryText.textContent = summaryText;
    
    // Show/hide summary
    if (DashboardState.periodo !== 'este_ano' || DashboardState.empresa !== 'todas') {
        filterSummary.style.display = 'block';
    } else {
        filterSummary.style.display = 'none';
    }
}

function updateResetButton() {
    const resetButton = document.getElementById('reset-filters');
    
    if (resetButton) {
        if (DashboardState.periodo !== 'este_ano' || DashboardState.empresa !== 'todas') {
            resetButton.style.display = 'inline-flex';
        } else {
            resetButton.style.display = 'none';
        }
    }
}

function updateEmpresasFilter() {
    const empresaFilter = document.getElementById('empresa-filter');
    
    if (empresaFilter && DashboardState.data.empresas) {
        // Clear existing options except "Todas as Empresas"
        while (empresaFilter.children.length > 1) {
            empresaFilter.removeChild(empresaFilter.lastChild);
        }
        
        // Add empresa options
        DashboardState.data.empresas.forEach(empresa => {
            const option = document.createElement('option');
            option.value = empresa;
            option.textContent = empresa;
            empresaFilter.appendChild(option);
        });
    }
}

function updateLastUpdateInfo() {
    if (DashboardState.data.lastUpdate) {
        const timeString = DashboardState.data.lastUpdate.toLocaleTimeString('pt-BR');
        console.log(`📊 Dashboard atualizado às ${timeString}`);
    }
}

// ==========================================
// KPI UPDATE FUNCTIONS - Métricas Inteligentes
// ==========================================

function updateKPIs(data) {
    console.log('📊 Updating KPIs:', data);
    
    // Resultado Operacional
    updateKPIValue('valor-resultado', data.resultado_liquido, data.resultado_variacao, 'currency');
    
    // Faturamento Total
    updateKPIValue('valor-faturamento', data.faturamento_total, data.faturamento_variacao, 'currency');
    
    // Despesas Totais
    updateKPIValue('valor-despesas', data.despesas_total, data.despesas_variacao, 'currency');
}

function updateMargems(data) {
    // Margem de Resultado (Métrica Derivada)
    const margemResultado = data.faturamento_total > 0 
        ? (data.resultado_liquido / data.faturamento_total) * 100 
        : 0;
    
    updateKPIValue('valor-margem-resultado', margemResultado, null, 'percentage');
    
    // Folha / Faturamento (buscar da API de despesas)
    loadFolhaFaturamentoMetric();
}

function loadFolhaFaturamentoMetric() {
    const dateParams = getDateParams();
    const url = `/financeiro/despesas/api/kpis?${new URLSearchParams(dateParams)}`;
    
    fetch(url)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const percentualFolha = data.data.percentual_folha_faturamento || 0;
                updateKPIValue('valor-folha-faturamento', percentualFolha, null, 'percentage');
            }
        })
        .catch(error => {
            console.error('❌ Error loading folha/faturamento metric:', error);
        });
}

function updateKPIValue(elementId, value, variation, format = 'currency') {
    const valueElement = document.getElementById(elementId);
    const variationElement = document.getElementById(elementId.replace('valor-', 'var-'));
    
    if (valueElement) {
        let formattedValue;
        let tooltipValue; // Valor completo para tooltip
        
        switch (format) {
            case 'currency':
                formattedValue = formatCurrencyCompact(value); // Nova formatação compacta
                tooltipValue = formatCurrency(value); // Valor completo para tooltip
                break;
            case 'percentage':
                formattedValue = `${value.toFixed(1)}%`;
                tooltipValue = `${value.toFixed(2)}%`; // Maior precisão no tooltip
                break;
            case 'number':
                formattedValue = formatNumber(value);
                tooltipValue = formattedValue;
                break;
            default:
                formattedValue = formatCurrencyCompact(value);
                tooltipValue = formatCurrency(value);
        }
        
        valueElement.textContent = formattedValue;
        
        // Adicionar tooltip com valor completo para valores monetários
        if (format === 'currency' && tooltipValue !== formattedValue) {
            valueElement.setAttribute('title', `Valor exato: ${tooltipValue}`);
            valueElement.style.cursor = 'help';
        }
    }
    
    if (variationElement && variation !== null && variation !== undefined) {
        const isPositive = variation > 0;
        const isNegative = variation < 0;
        
        // Format variation with appropriate icon and "vs período anterior" text
        const icon = isPositive ? '▲' : isNegative ? '▼' : '●';
        const formattedVariation = `${icon} ${Math.abs(variation).toFixed(1)}% vs período anterior`;
        
        variationElement.textContent = formattedVariation;
        
        // Update classes for the new compact structure
        variationElement.className = 'kpi-comparison';
        if (isPositive) {
            variationElement.classList.add('positive');
        } else if (isNegative) {
            variationElement.classList.add('negative');
        } else {
            variationElement.classList.add('neutral');
        }
    }
}

// ==========================================
// CHART UPDATE FUNCTIONS
// ==========================================

function updateResultadoMensalChart(data) {
    console.log('📊 Updating resultado mensal chart:', data);
    
    const ctx = document.getElementById('chart-resultado-mensal');
    if (!ctx) return;
    
    // Destroy existing chart
    if (DashboardState.charts.resultadoMensal) {
        DashboardState.charts.resultadoMensal.destroy();
    }
    
    // Prepare data
    const labels = data.map(item => getMonthName(item.mes.split('-')[1]));
    const receitas = data.map(item => item.receitas);
    const despesas = data.map(item => Math.abs(item.despesas)); // Make positive for display
    const resultados = data.map(item => item.resultado);
    
    DashboardState.charts.resultadoMensal = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Receitas',
                    data: receitas,
                    backgroundColor: 'rgba(16, 185, 129, 0.8)',
                    borderWidth: 0,
                    borderRadius: 4
                },
                {
                    label: 'Despesas',
                    data: despesas,
                    backgroundColor: 'rgba(239, 68, 68, 0.8)',
                    borderWidth: 0,
                    borderRadius: 4
                },
                {
                    label: 'Resultado',
                    data: resultados,
                    type: 'line',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    borderColor: 'rgba(59, 130, 246, 1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        padding: 20
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: 'white',
                    bodyColor: 'white',
                    callbacks: {
                        label: function(context) {
                            return context.dataset.label + ': ' + formatCurrency(context.parsed.y);
                        }
                    }
                },
                datalabels: {
                    display: true,
                    anchor: 'end',
                    align: 'top',
                    formatter: function(value) {
                        return formatCurrencyShort(value);
                    },
                    color: '#212529',
                    backgroundColor: 'rgba(255, 255, 255, 0.9)',
                    borderColor: '#dee2e6',
                    borderWidth: 1,
                    borderRadius: 4,
                    padding: {
                        top: 4,
                        bottom: 4,
                        left: 6,
                        right: 6
                    },
                    font: {
                        size: 11,
                        weight: 'bold'
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return formatCurrencyShort(value);
                        }
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

function updateFaturamentoSunburst(data) {
    console.log('🌻 Updating faturamento sunburst chart (Meta Grupo → Classe):', data);
    
    const ctx = document.getElementById('chart-faturamento-por-setor');
    if (!ctx) {
        console.error('❌ Canvas not found: chart-faturamento-por-setor');
        return;
    }
    
    // Destroy existing chart
    if (DashboardState.charts.faturamentoPorSetor) {
        DashboardState.charts.faturamentoPorSetor.destroy();
    }
    
    if (!data || data.length === 0) {
        console.warn('⚠️ No data for sunburst chart');
        return;
    }
    
    // Cores mais distintas para Meta Grupos
    const coresPorMetaGrupo = {
        'Consultoria': '#0d6efd',    // Azul
        'IMP/EXP': '#fd7e14',        // Laranja  
        'Outros': '#6c757d'          // Cinza
    };
    
    // Cores mais claras para as Classes (tons da cor do Meta Grupo)
    const coresPorClasse = {
        // Consultoria - tons de azul
        'Classificação Fiscal': '#4285f4',
        'HABILITAÇÃO NO RADAR': '#1e88e5', 
        'DRAWBACK': '#039be5',
        'CATALOGO DE PRODUTOS': '#00acc1',
        'Atestado de Inexistencia': '#00838f',
        'MAQUINAS USADAS': '#0277bd',
        'EX-TARIFARIO': '#0288d1',
        'SISCOSERV': '#0097a7',
        'CONSULTORIA': '#0d6efd',
        
        // IMP/EXP - tons de laranja
        'IMPORTAÇÃO': '#ff6f00',
        'EXPORTAÇÃO': '#ff8f00',
        'OUTSOURCING': '#ffa000',
        
        // Outros - tons de cinza  
        'Outros': '#6c757d'
    };
    
    // Preparar dados para gráficos de rosca aninhados
    const metaGrupos = data.map(item => item.name);
    const metaGrupoValues = data.map(item => item.value);
    const metaGrupoCores = metaGrupos.map(name => coresPorMetaGrupo[name] || '#6c757d');
    
    // Preparar dados das classes (anel interno)
    let classes = [];
    let classeValues = [];
    let classeCores = [];
    
    data.forEach(metaGrupo => {
        if (metaGrupo.children && metaGrupo.children.length > 0) {
            metaGrupo.children.forEach(classe => {
                classes.push(classe.name);
                classeValues.push(classe.value);
                classeCores.push(coresPorClasse[classe.name] || coresPorMetaGrupo[metaGrupo.name] || '#6c757d');
            });
        }
    });
    
    DashboardState.charts.faturamentoPorSetor = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: metaGrupos, // Legenda mostra Meta Grupos
            datasets: [
                {
                    // Dataset interno (classes) 
                    label: 'Por Classe',
                    data: classeValues,
                    backgroundColor: classeCores,
                    borderWidth: 2,
                    borderColor: '#fff',
                    radius: '70%',
                    cutout: '45%'
                },
                {
                    // Dataset externo (meta grupos)
                    label: 'Por Meta Grupo', 
                    data: metaGrupoValues,
                    backgroundColor: metaGrupoCores,
                    borderWidth: 3,
                    borderColor: '#fff',
                    radius: '95%',
                    cutout: '72%'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            aspectRatio: 1.2,
            plugins: {
                legend: {
                    display: true,
                    position: 'right',
                    labels: {
                        usePointStyle: true,
                        padding: 15,
                        font: { size: 11 },
                        generateLabels: function(chart) {
                            const labels = [];
                            
                            // Adicionar Meta Grupos
                            metaGrupos.forEach((metaGrupo, index) => {
                                labels.push({
                                    text: metaGrupo,
                                    fillStyle: metaGrupoCores[index],
                                    strokeStyle: metaGrupoCores[index],
                                    pointStyle: 'circle',
                                    fontColor: '#333',
                                    fontWeight: 'bold'
                                });
                            });
                            
                            return labels;
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const isMetaGrupo = context.datasetIndex === 1;
                            let label = '';
                            
                            if (isMetaGrupo) {
                                label = `Meta: ${context.label}`;
                            } else {
                                label = `Classe: ${classes[context.dataIndex]}`;
                            }
                            
                            const value = formatCurrency(context.parsed);
                            const dataset = context.dataset;
                            const total = dataset.data.reduce((sum, val) => sum + val, 0);
                            const percentage = ((context.parsed / total) * 100).toFixed(1);
                            
                            return `${label}\nValor: ${value} (${percentage}%)`;
                        }
                    }
                },
                datalabels: {
                    display: false
                }
            }
        }
    });
}

function updateSaldoAcumuladoChart(data) {
    console.log('📊 Updating saldo acumulado chart (replicado do fluxo de caixa):', data);
    
    const ctx = document.getElementById('chart-saldo-acumulado');
    if (!ctx) return;
    
    // Destroy existing chart
    if (DashboardState.charts.saldoAcumulado) {
        DashboardState.charts.saldoAcumulado.destroy();
    }
    
    if (!data || !data.saldo_real) {
        console.warn('⚠️ No saldo real data for chart');
        return;
    }
    
    // Prepare datasets
    const datasets = [];
    let allDates = [];
    let allValues = [];
    
    // Dataset 1: Saldo Acumulado Real
    const realValues = data.saldo_real.saldos.filter(val => val !== null && val !== undefined);
    datasets.push({
        label: 'Saldo Acumulado Real',
        data: data.saldo_real.saldos,
        borderColor: 'rgba(0, 123, 255, 1)',
        backgroundColor: 'rgba(0, 123, 255, 0.1)',
        borderWidth: 3,
        fill: true,
        tension: 0.4,
        pointBackgroundColor: data.saldo_real.saldos.map(value => 
            value >= 0 ? 'rgba(40, 167, 69, 1)' : 'rgba(220, 53, 69, 1)'
        ),
        pointBorderColor: 'white',
        pointBorderWidth: 2,
        pointRadius: 3
    });
    
    allDates = [...data.saldo_real.datas];
    allValues = [...realValues];
    
    // Dataset 2: Projeção (if available and has future data)
    if (data.projecao && data.projecao.datas && data.projecao.datas.length > 0) {
        // Create null values for past dates + projection values
        const pastNulls = new Array(data.saldo_real.datas.length - 1).fill(null);
        
        // Start projection from last real value
        const lastRealValue = data.saldo_real.saldos[data.saldo_real.saldos.length - 1] || 0;
        const projectionData = [...pastNulls, lastRealValue, ...data.projecao.saldos];
        
        datasets.push({
            label: 'Saldo Acumulado Projetado',
            data: projectionData,
            borderColor: 'rgba(255, 193, 7, 1)',
            backgroundColor: 'rgba(255, 193, 7, 0.1)', 
            borderWidth: 3,
            borderDash: [5, 5], // Dashed line for projection
            fill: false,
            tension: 0.4,
            pointBackgroundColor: 'rgba(255, 193, 7, 1)',
            pointBorderColor: 'white',
            pointBorderWidth: 2,
            pointRadius: 4
        });
        
        // Combine dates for x-axis
        allDates = [...data.saldo_real.datas, ...data.projecao.datas];
        allValues = [...allValues, ...data.projecao.saldos];
    }
    
    // Find min and max values for proper scaling
    const minValue = Math.min(...allValues);
    const maxValue = Math.max(...allValues);
    const range = maxValue - minValue;
    const minPadded = minValue - (range * 0.1);
    const maxPadded = maxValue + (range * 0.1);
    
    DashboardState.charts.saldoAcumulado = new Chart(ctx, {
        type: 'line',
        data: {
            labels: allDates,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: datasets.length > 1, // Show legend only if we have projection data
                    labels: {
                        usePointStyle: true,
                        padding: 20
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            const value = formatCurrency(context.parsed.y);
                            return `${context.dataset.label}: ${value}`;
                        }
                    }
                },
                datalabels: {
                    display: true,
                    anchor: 'end',
                    align: 'top',
                    formatter: function(value) {
                        return formatCurrencyCompact(value);
                    },
                    color: '#212529',
                    backgroundColor: 'rgba(255, 255, 255, 0.9)',
                    borderColor: '#dee2e6',
                    borderWidth: 1,
                    borderRadius: 4,
                    padding: {
                        top: 4,
                        bottom: 4,
                        left: 6,
                        right: 6
                    },
                    font: {
                        size: 10,
                        weight: 'bold'
                    }
                }
            },
            scales: {
                y: {
                    min: minPadded,
                    max: maxPadded,
                    grid: {
                        display: true,
                        color: 'rgba(0, 0, 0, 0.1)',
                        drawBorder: false
                    },
                    ticks: {
                        callback: function(value) {
                            return formatCurrencyCompact(value);
                        }
                    }
                },
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        maxTicksLimit: 12 // Limit number of x-axis labels
                    }
                }
            },
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            }
        }
    });
}

function updateFaturamentoMensalChart(data) {
    console.log('📊 Updating faturamento mensal chart:', data);
    
    const ctx = document.getElementById('chart-faturamento-mensal');
    if (!ctx) return;
    
    // Destroy existing chart
    if (DashboardState.charts.faturamentoMensal) {
        DashboardState.charts.faturamentoMensal.destroy();
    }
    
    // Prepare data
    const labels = data.map(item => getMonthName(item.mes.toString()));
    const anoAtual = data.map(item => item.faturamento_total);
    const anoAnterior = data.map(item => item.faturamento_anterior);
    
    DashboardState.charts.faturamentoMensal = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Ano Atual',
                    data: anoAtual,
                    backgroundColor: 'rgba(25, 135, 84, 0.8)',
                    borderColor: 'rgba(25, 135, 84, 1)',
                    borderWidth: 2,
                    borderRadius: 4
                },
                {
                    label: 'Ano Anterior',
                    data: anoAnterior,
                    backgroundColor: 'rgba(108, 117, 125, 0.6)',
                    borderColor: 'rgba(108, 117, 125, 1)',
                    borderWidth: 2,
                    borderRadius: 4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false // Legend is shown separately
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return context.dataset.label + ': ' + formatCurrency(context.parsed.y);
                        }
                    }
                },
                datalabels: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return formatCurrencyShort(value);
                        }
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

function updateTopDespesasChart(data) {
    console.log('📊 Updating top despesas chart:', data);
    
    const ctx = document.getElementById('chart-top-despesas');
    if (!ctx) return;
    
    // Destroy existing chart
    if (DashboardState.charts.topDespesas) {
        DashboardState.charts.topDespesas.destroy();
    }
    
    // Prepare data
    const labels = data.map(item => item.categoria);
    const valores = data.map(item => item.total);
    
    DashboardState.charts.topDespesas = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Valor',
                data: valores,
                backgroundColor: [
                    'rgba(99, 102, 241, 0.8)',
                    'rgba(59, 130, 246, 0.8)',
                    'rgba(16, 185, 129, 0.8)',
                    'rgba(245, 158, 11, 0.8)',
                    'rgba(239, 68, 68, 0.8)'
                ],
                borderWidth: 0, // Remover bordas coloridas
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: 'y', // Torna o gráfico horizontal
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return formatCurrency(context.parsed.x);
                        }
                    }
                },
                datalabels: {
                    display: true,
                    anchor: 'end',
                    align: 'right',
                    formatter: function(value) {
                        return formatCurrencyShort(value);
                    },
                    color: '#212529',
                    backgroundColor: 'rgba(255, 255, 255, 0.9)',
                    borderColor: '#dee2e6',
                    borderWidth: 1,
                    borderRadius: 4,
                    padding: {
                        top: 4,
                        bottom: 4,
                        left: 6,
                        right: 6
                    },
                    font: {
                        size: 11,
                        weight: 'bold'
                    }
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return formatCurrencyShort(value);
                        }
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.1)'
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

function updateTendenciaDespesasChart(data) {
    console.log('📊 Updating tendencia despesas chart:', data);
    
    const ctx = document.getElementById('chart-tendencia-despesas');
    if (!ctx) return;
    
    // Destroy existing chart
    if (DashboardState.charts.tendenciaDespesas) {
        DashboardState.charts.tendenciaDespesas.destroy();
    }
    
    // Validar se data e data.data existem
    if (!data || !data.data || typeof data.data !== 'object') {
        console.warn('⚠️ Dados inválidos para tendência de despesas:', data);
        
        // Criar gráfico vazio com mensagem
        DashboardState.charts.tendenciaDespesas = new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun'],
                datasets: [{
                    label: 'Sem dados disponíveis',
                    data: [0, 0, 0, 0, 0, 0],
                    borderColor: 'rgba(108, 117, 125, 0.5)',
                    backgroundColor: 'rgba(108, 117, 125, 0.1)',
                    borderWidth: 1,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: { enabled: false }
                }
            }
        });
        return;
    }
    
    // Prepare data for multiple lines
    const colors = [
        'rgba(99, 102, 241, 1)',
        'rgba(59, 130, 246, 1)',
        'rgba(16, 185, 129, 1)',
        'rgba(245, 158, 11, 1)',
        'rgba(239, 68, 68, 1)'
    ];
    
    const datasets = [];
    let index = 0;
    
    for (const [combinacao, dadosCombinacao] of Object.entries(data.data)) {
        datasets.push({
            label: combinacao,
            data: dadosCombinacao.valores,
            borderColor: colors[index % colors.length],
            backgroundColor: colors[index % colors.length].replace('1)', '0.1)'),
            borderWidth: 2,
            fill: false,
            tension: 0.3
        });
        index++;
    }
    
    const labels = datasets.length > 0 ? datasets[0].data.map((_, i) => {
        // Generate month labels for the last 12 months
        const date = new Date();
        date.setMonth(date.getMonth() - (datasets[0].data.length - 1 - i));
        return getMonthName((date.getMonth() + 1).toString());
    }) : [];
    
    DashboardState.charts.tendenciaDespesas = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        usePointStyle: true,
                        padding: 10,
                        font: {
                            size: 10
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return context.dataset.label + ': ' + formatCurrency(context.parsed.y);
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return formatCurrencyShort(value);
                        }
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

function updateTopClientes(data) {
    console.log('👥 Updating top clientes table:', data);
    
    const tableBody = document.querySelector('#table-clientes tbody');
    if (!tableBody) return;
    
    // Clear existing rows
    tableBody.innerHTML = '';
    
    // Add new rows
    data.forEach((cliente, index) => {
        const row = document.createElement('tr');
        
        // Use real trend data from API
        const trendIcons = { up: '↗', down: '↘', stable: '→' };
        const trendLabels = { 
            up: 'Crescendo', 
            down: 'Decrescendo', 
            stable: 'Estável' 
        };
        const trendClasses = { 
            up: 'trend-up', 
            down: 'trend-down', 
            stable: 'trend-stable' 
        };
        
        const trend = cliente.trend || 'stable';
        const variacao = cliente.variacao_percentual || 0;
        
        // Create tooltip with detailed information
        const trendTooltip = `Tendência: ${trendLabels[trend]}${variacao !== 0 ? ` (${variacao > 0 ? '+' : ''}${variacao.toFixed(1)}% vs ano anterior)` : ''}`;
        
        row.innerHTML = `
            <td class="rank-col">${index + 1}</td>
            <td class="cliente-col" title="${cliente.cliente}">${cliente.cliente}</td>
            <td class="valor-col" title="Valor exato: ${formatCurrency(cliente.total_faturado || 0)}">${formatCurrencyCompact(cliente.total_faturado || 0)}</td>
            <td class="percent-col">${(cliente.percentual || 0).toFixed(1)}%</td>
            <td class="trend-col">
                <span class="trend-indicator ${trendClasses[trend]}" title="${trendTooltip}">
                    ${trendIcons[trend]}
                </span>
            </td>
        `;
        
        tableBody.appendChild(row);
    });
}

// ==========================================
// UTILITY & HELPER FUNCTIONS
// ==========================================

function updateSaldoStatus(isPositive) {
    const statusElement = document.getElementById('saldo-status');
    if (statusElement) {
        statusElement.innerHTML = isPositive 
            ? '<i class="mdi mdi-trending-up"></i> Tendência positiva'
            : '<i class="mdi mdi-trending-down"></i> Tendência negativa';
        
        statusElement.className = 'chart-status';
        if (isPositive) {
            statusElement.style.color = '#198754';
        } else {
            statusElement.style.color = '#dc3545';
        }
    }
}

function initializeCharts() {
    // Initialize Chart.js defaults
    Chart.defaults.font.family = "'Segoe UI', 'Roboto', 'Arial', sans-serif";
    Chart.defaults.color = '#495057';
    Chart.defaults.borderColor = 'rgba(0, 0, 0, 0.1)';
}

function setupLoadingStates() {
    // Add skeleton loaders for all chart containers
    const chartContainers = document.querySelectorAll('.chart-content');
    chartContainers.forEach(container => {
        container.classList.add('chart-loading');
    });
}

function showLoading() {
    const loadingOverlay = document.getElementById('loading-overlay');
    if (loadingOverlay) {
        loadingOverlay.style.display = 'flex';
    }
}

function hideLoading() {
    const loadingOverlay = document.getElementById('loading-overlay');
    if (loadingOverlay) {
        loadingOverlay.style.display = 'none';
    }
    
    // Remove skeleton loaders
    const chartContainers = document.querySelectorAll('.chart-content');
    chartContainers.forEach(container => {
        container.classList.remove('chart-loading');
    });
}

function showError(message) {
    console.error('❌ Dashboard Error:', message);
    showNotification(message, 'error');
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <i class="mdi mdi-${type === 'success' ? 'check-circle' : type === 'error' ? 'alert-circle' : 'information'}"></i>
        <span>${message}</span>
        <button class="notification-close">×</button>
    `;
    
    // Add styles
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === 'success' ? '#d4edda' : type === 'error' ? '#f8d7da' : '#d1ecf1'};
        color: ${type === 'success' ? '#155724' : type === 'error' ? '#721c24' : '#0c5460'};
        border: 1px solid ${type === 'success' ? '#c3e6cb' : type === 'error' ? '#f5c6cb' : '#bee5eb'};
        border-radius: 6px;
        padding: 12px 16px;
        z-index: 1050;
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 14px;
        font-weight: 500;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        max-width: 400px;
        animation: slideInRight 0.3s ease;
    `;
    
    // Add to page
    document.body.appendChild(notification);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.style.animation = 'slideOutRight 0.3s ease';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }
    }, 5000);
    
    // Manual close
    const closeBtn = notification.querySelector('.notification-close');
    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        });
    }
}

function formatCurrency(value) {
    // Verificar se o valor é válido
    if (value === null || value === undefined || isNaN(value)) {
        return 'R$ 0,00';
    }
    
    // Converter para número se for string
    const numValue = typeof value === 'string' ? parseFloat(value) : value;
    
    // Verificar novamente após conversão
    if (isNaN(numValue)) {
        return 'R$ 0,00';
    }
    
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(numValue);
}

function formatCurrencyCompact(value) {
    // Formatação inteligente para KPI Cards - valores grandes abreviados
    if (value === null || value === undefined || isNaN(value)) {
        return 'R$ 0,00';
    }
    
    const numValue = typeof value === 'string' ? parseFloat(value) : value;
    
    if (isNaN(numValue)) {
        return 'R$ 0,00';
    }
    
    const absValue = Math.abs(numValue);
    const isNegative = numValue < 0;
    const prefix = isNegative ? '-' : '';
    
    if (absValue >= 1000000) {
        // Milhões: R$ 5,17 mi
        return `${prefix}R$ ${(absValue / 1000000).toFixed(2).replace('.', ',')} mi`;
    } else if (absValue >= 1000) {
        // Milhares: R$ 450,3 mil
        return `${prefix}R$ ${(absValue / 1000).toFixed(1).replace('.', ',')} mil`;
    } else {
        // Valores menores que 1000: formato normal
        return formatCurrency(numValue);
    }
}

function formatCurrencyShort(value) {
    // Verificar se o valor é válido
    if (value === null || value === undefined || isNaN(value)) {
        return 'R$ 0,00';
    }
    
    // Converter para número se for string
    const numValue = typeof value === 'string' ? parseFloat(value) : value;
    
    // Verificar novamente após conversão
    if (isNaN(numValue)) {
        return 'R$ 0,00';
    }
    
    const absValue = Math.abs(numValue);
    const prefix = numValue < 0 ? '-' : '';
    
    if (absValue >= 1000000) {
        return `${prefix}R$ ${(absValue / 1000000).toFixed(1)}M`;
    } else if (absValue >= 1000) {
        return `${prefix}R$ ${(absValue / 1000).toFixed(1)}K`;
    }
    return formatCurrency(numValue);
}

function formatNumber(value) {
    return new Intl.NumberFormat('pt-BR').format(value);
}

function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString('pt-BR');
}

function getMonthName(monthNumber) {
    const months = [
        'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
        'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'
    ];
    return months[parseInt(monthNumber) - 1] || 'Jan';
}

// Drill-down variables (compatibility with existing code)
let isDrillDownActive = false;
let currentDrillDownSetor = null;

// Add CSS animations for notifications
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    @keyframes slideOutRight {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
    
    .notification-close {
        background: none;
        border: none;
        font-size: 18px;
        font-weight: bold;
        cursor: pointer;
        opacity: 0.7;
        margin-left: 8px;
    }
    
    .notification-close:hover {
        opacity: 1;
    }
    
    .chart-loading::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
        background-size: 200% 100%;
        animation: loading 1.5s infinite;
        border-radius: 8px;
        z-index: 1;
    }
    
    @keyframes loading {
        0% { background-position: 200% 0; }
        100% { background-position: -200% 0; }
    }
`;
document.head.appendChild(style);

// ==========================================
// META GAUGE FUNCTIONS
// ==========================================

// ==========================================
// METAS SEGMENTADAS - NOVO COMPONENTE COMPACTO
// ==========================================

function updateMetasSegmentadas(metasData) {
    console.log('📊 Updating metas segmentadas:', metasData);
    
    if (!metasData) {
        // Limpar dados em caso de erro
        const tipos = ['geral', 'consultoria', 'imp_exp'];
        tipos.forEach(tipo => {
            const percentageEl = document.getElementById(`percentage-${tipo.replace('_', '-')}`);
            const valuesEl = document.getElementById(`values-${tipo.replace('_', '-')}`);
            
            if (percentageEl) percentageEl.textContent = '0%';
            if (valuesEl) valuesEl.textContent = 'R$ 0 de R$ 0';
        });
        return;
    }
    
    // Atualizar cada mini-gauge
    Object.keys(metasData).forEach(tipo => {
        const data = metasData[tipo];
        updateMiniGauge(tipo, data);
    });
}

function updateMiniGauge(tipo, data) {
    // Converter tipo para ID correto (imp_exp -> imp-exp)
    const canvasId = `gauge-${tipo.replace('_', '-')}`;
    const percentageId = `percentage-${tipo.replace('_', '-')}`;
    const valuesId = `values-${tipo.replace('_', '-')}`;
    
    const canvas = document.getElementById(canvasId);
    const percentageEl = document.getElementById(percentageId);
    const valuesEl = document.getElementById(valuesId);
    
    if (!canvas) return;
    
    // Destruir gráfico existente se houver
    if (DashboardState.charts[tipo]) {
        DashboardState.charts[tipo].destroy();
    }
    
    const atingimento = data.atingimento || 0;
    const meta = data.meta || 0;
    const realizado = data.realizado || 0;
    
    // Definir cor baseada no tipo e desempenho
    let baseColor, backgroundColor;
    switch(tipo) {
        case 'geral':
            baseColor = '#0d6efd';
            break;
        case 'consultoria':
            baseColor = '#198754';
            break;
        case 'imp_exp':
            baseColor = '#fd7e14';
            break;
        default:
            baseColor = '#6c757d';
    }
    
    // Ajustar intensidade da cor baseada no desempenho
    if (atingimento >= 100) {
        backgroundColor = baseColor;
    } else if (atingimento >= 80) {
        backgroundColor = baseColor + 'CC'; // 80% opacity
    } else if (atingimento >= 60) {
        backgroundColor = baseColor + '99'; // 60% opacity  
    } else {
        backgroundColor = baseColor + '66'; // 40% opacity
    }
    
    // Atualizar elementos HTML
    if (percentageEl) {
        percentageEl.textContent = `${atingimento.toFixed(1)}%`;
        percentageEl.style.color = baseColor;
    }
    
    if (valuesEl) {
        valuesEl.textContent = `${formatCurrencyCompact(realizado)} de ${formatCurrencyCompact(meta)}`;
    }
    
    // Criar mini-gauge (doughnut chart)
    const gaugeValue = Math.min(atingimento, 150); // Limitar visualização
    
    DashboardState.charts[tipo] = new Chart(canvas, {
        type: 'doughnut',
        data: {
            datasets: [{
                data: [gaugeValue, 150 - gaugeValue],
                backgroundColor: [
                    backgroundColor,
                    'rgba(233, 236, 239, 0.2)'
                ],
                borderWidth: 0,
                cutout: '75%',
                circumference: 270, // 3/4 circle
                rotation: 225 // Start from bottom left
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { display: false },
                tooltip: {
                    enabled: true,
                    callbacks: {
                        label: function(context) {
                            return `${atingimento.toFixed(1)}% da meta atingida`;
                        },
                        afterLabel: function(context) {
                            return [
                                `Realizado: ${formatCurrency(realizado)}`,
                                `Meta: ${formatCurrency(meta)}`
                            ];
                        }
                    }
                },
                datalabels: {
                    display: false
                }
            },
            animation: {
                animateRotate: true,
                duration: 1500,
                easing: 'easeOutCubic'
            }
        }
    });
    
    console.log(`📊 Mini-Gauge ${tipo}: ${atingimento.toFixed(1)}% (${formatCurrencyCompact(realizado)} / ${formatCurrencyCompact(meta)})`);
}

console.log('✅ Dashboard Executivo Financeiro - JavaScript loaded successfully');