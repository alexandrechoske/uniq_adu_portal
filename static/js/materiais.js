/**
 * MATERIAIS JAVASCRIPT - Portal UniSystem
 * Gerenciamento completo da página de análise de materiais
 * Inclui: KPIs, Gráficos, Filtros, Tabelas e Modal
 */

// =============================================================================
// VARIÁVEIS GLOBAIS
// =============================================================================
let materiaisCharts = {};
let currentFilters = {};
let isLoading = false;

// Variáveis de paginação
let currentPage = 1;
let pageSize = 10;
let totalRecords = 0;
let totalPages = 0;
let originalTableData = [];

// =============================================================================
// INICIALIZAÇÃO
// =============================================================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('[MATERIAIS] Inicializando página de materiais...');
    
    // Registrar plugin de data labels se disponível
    if (typeof ChartDataLabels !== 'undefined') {
        Chart.register(ChartDataLabels);
        console.log('[MATERIAIS] Plugin ChartDataLabels registrado');
    } else {
        console.warn('[MATERIAIS] Plugin ChartDataLabels não encontrado');
    }
    console.log('[MATERIAIS] Inicializando página de materiais...');
    
    // Inicializar componentes
    initializeModal();
    initializeFilters();
    initializeEventListeners();
    
    // Carregar dados iniciais
    loadInitialData();
    
    console.log('[MATERIAIS] Página inicializada com sucesso!');
});

// =============================================================================
// INICIALIZAÇÃO DE COMPONENTES
// =============================================================================
function initializeModal() {
    console.log('[MATERIAIS] Inicializando modal...');
    
    const modal = document.getElementById('filter-modal');
    const openBtn = document.getElementById('open-filters');
    const closeBtn = document.getElementById('close-modal');
    const applyBtn = document.getElementById('apply-filters');
    const clearBtn = document.getElementById('clear-filters');
    
    if (!modal) {
        console.warn('[MATERIAIS] Modal não encontrado');
        return;
    }
    
    // Abrir modal
    if (openBtn) {
        openBtn.addEventListener('click', () => {
            modal.style.display = 'block';
            document.body.style.overflow = 'hidden';
        });
    }
    
    // Fechar modal
    const closeModal = () => {
        modal.style.display = 'none';
        document.body.style.overflow = 'auto';
    };
    
    if (closeBtn) {
        closeBtn.addEventListener('click', closeModal);
    }
    
    // Fechar modal clicando fora
    window.addEventListener('click', (event) => {
        if (event.target === modal) {
            closeModal();
        }
    });
    
    // Aplicar filtros
    if (applyBtn) {
        applyBtn.addEventListener('click', () => {
            applyFilters();
            closeModal();
        });
    }
    
    // Limpar filtros
    if (clearBtn) {
        clearBtn.addEventListener('click', clearFilters);
    }
}

function initializeFilters() {
    console.log('[MATERIAIS] Inicializando filtros...');
    
    // Definir período padrão (últimos 30 dias)
    const hoje = new Date();
    const trintaDiasAtras = new Date(hoje.getTime() - (30 * 24 * 60 * 60 * 1000));
    
    const dataInicioElement = document.getElementById('data-inicio');
    const dataFimElement = document.getElementById('data-fim');
    
    if (dataInicioElement) {
        dataInicioElement.value = formatDateForInput(trintaDiasAtras);
    }
    
    if (dataFimElement) {
        dataFimElement.value = formatDateForInput(hoje);
    }
    
    // Filtros rápidos
    document.querySelectorAll('.btn-quick').forEach(button => {
        button.addEventListener('click', function() {
            const period = this.dataset.period;
            setQuickDateFilter(period);
        });
    });
}

function initializeEventListeners() {
    // Botão de atualizar
    document.getElementById('refresh-chart').addEventListener('click', () => {
        loadMateriaisData();
    });
    
    // Botão de exportar
    document.getElementById('export-data').addEventListener('click', exportData);
    
    // Tecla ESC para fechar modal
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            const modal = document.getElementById('filter-modal');
            if (modal.style.display === 'block') {
                modal.style.display = 'none';
                document.body.style.overflow = 'auto';
            }
        }
    });
}

// =============================================================================
// CARREGAMENTO DE DADOS
// =============================================================================
function loadInitialData() {
    console.log('[MATERIAIS] Iniciando carregamento de dados...');
    showLoadingOverlay();
    
    Promise.all([
        loadFilterOptions(),
        loadMateriaisData(),
        loadPrincipaisMateriais(),
        loadDetalhamentoProcessos(),
        loadTransitTime()
    ]).then(() => {
        console.log('[MATERIAIS] Todos os dados carregados com sucesso');
        hideLoadingOverlay();
        updateLastUpdate();
    }).catch(error => {
        console.error('[MATERIAIS] Erro ao carregar dados iniciais:', error);
        hideLoadingOverlay();
    });
}

function loadMateriaisData() {
    if (isLoading) return;
    
    console.log('[MATERIAIS] Carregando dados...');
    isLoading = true;
    showLoadingOverlay();
    
    const params = new URLSearchParams(currentFilters);
    console.log('[MATERIAIS] Filtros aplicados:', currentFilters);
    
    // Carregar KPIs - usando endpoint bypass com filtros
    fetch(`/materiais/bypass-materiais-data?${params}`)
        .then(response => {
            console.log('[MATERIAIS] Response status:', response.status);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('[MATERIAIS] KPIs carregados:', data);
            updateKPIs(data);
        })
        .catch(error => {
            console.error('[MATERIAIS] Erro ao carregar KPIs:', error);
        });
    
    // Carregar gráficos
    Promise.all([
        loadTopMateriais(),
        loadEvolucaoMensal(),
        loadModalDistribution(),
        loadCanalDistribution(),
        loadTransitTime()
    ]).then(() => {
        console.log('[MATERIAIS] Gráficos carregados com sucesso');
    });
    
    // Carregar tabelas
    Promise.all([
        loadPrincipaisMateriais(),
        loadDetalhamentoProcessos()
    ]).then(() => {
        console.log('[MATERIAIS] Tabelas carregadas com sucesso');
        isLoading = false;
        hideLoadingOverlay();
    });
}

// =============================================================================
// ATUALIZAÇÃO DE KPIs
// =============================================================================
function updateKPIs(data) {
    const kpis = [
        { id: 'kpi-total-processos', value: data.total_processos, format: 'number' },
        { id: 'kpi-total-materiais', value: data.total_materiais, format: 'number' },
        { id: 'kpi-valor-total', value: data.valor_total, format: 'currency-thousands' },
        { id: 'kpi-custo-total', value: data.custo_total, format: 'currency-thousands' },
        { id: 'kpi-ticket-medio', value: data.ticket_medio, format: 'currency' },
        { id: 'kpi-transit-time', value: data.transit_time_medio, format: 'days' }
    ];
    
    kpis.forEach(kpi => {
        const element = document.getElementById(kpi.id);
        if (element) {
            element.textContent = formatValue(kpi.value, kpi.format);
        }
    });
}

// =============================================================================
// CARREGAMENTO DE GRÁFICOS
// =============================================================================
function loadTopMateriais() {
    console.log('[MATERIAIS] Iniciando carregamento de top materiais...');
    const params = new URLSearchParams(currentFilters);
    
    return fetch(`/materiais/bypass-top-materiais?${params}`)
        .then(response => {
            console.log('[MATERIAIS] Top materiais response status:', response.status);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('[MATERIAIS] Top materiais carregados:', data);
            createTopMateriaisChart(data);
        })
        .catch(error => {
            console.error('[MATERIAIS] Erro ao carregar top materiais:', error);
        });
}

function loadEvolucaoMensal() {
    const params = new URLSearchParams(currentFilters);
    
    return fetch(`/materiais/bypass-evolucao-mensal?${params}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('[MATERIAIS] Evolução mensal carregada:', data);
            createEvolucaoMensalChart(data);
        })
        .catch(error => {
            console.error('[MATERIAIS] Erro ao carregar evolução mensal:', error);
        });
}

function loadModalDistribution() {
    const params = new URLSearchParams(currentFilters);
    
    return fetch(`/materiais/bypass-modal-distribution?${params}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('[MATERIAIS] Distribuição modal carregada:', data);
            createModalChart(data);
        })
        .catch(error => {
            console.error('[MATERIAIS] Erro ao carregar distribuição modal:', error);
        });
}

function loadCanalDistribution() {
    const params = new URLSearchParams(currentFilters);
    
    return fetch(`/materiais/bypass-canal-distribution?${params}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('[MATERIAIS] Distribuição canal carregada:', data);
            createCanalChart(data);
        })
        .catch(error => {
            console.error('[MATERIAIS] Erro ao carregar distribuição canal:', error);
        });
}

function loadTransitTime() {
    console.log('[MATERIAIS] Carregando transit time...');
    const params = new URLSearchParams(currentFilters);
    
    return fetch(`/materiais/bypass-transit-time?${params}`)
        .then(response => response.json())
        .then(data => {
            console.log('[MATERIAIS] Transit time carregado:', data.length);
            createTransitTimeChart(data);
        })
        .catch(error => {
            console.error('[MATERIAIS] Erro ao carregar transit time:', error);
            // Criar gráfico vazio em caso de erro
            createTransitTimeChart([]);
        });
}

// =============================================================================
// CRIAÇÃO DE GRÁFICOS
// =============================================================================
function createTopMateriaisChart(data) {
    const ctx = document.getElementById('top-materiais-chart').getContext('2d');
    
    if (materiaisCharts.topMateriais) {
        materiaisCharts.topMateriais.destroy();
    }
    
    materiaisCharts.topMateriais = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.map(item => item.material),
            datasets: [{
                label: 'Quantidade de Processos',
                data: data.map(item => item.qtde_processos),
                backgroundColor: 'rgba(52, 152, 219, 0.7)',
                borderColor: 'rgba(52, 152, 219, 1)',
                borderWidth: 2,
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.1)'
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.dataset.label}: ${context.parsed.y} processos`;
                        }
                    }
                }
            }
        }
    });
}

function createEvolucaoMensalChart(data) {
    const ctx = document.getElementById('evolucao-mensal-chart').getContext('2d');
    
    if (materiaisCharts.evolucaoMensal) {
        materiaisCharts.evolucaoMensal.destroy();
    }
    
    // Agrupar dados por material
    const materialData = {};
    data.forEach(item => {
        if (!materialData[item.categoria_material]) {
            materialData[item.categoria_material] = {};
        }
        materialData[item.categoria_material][item.mes] = item.qtde;
    });
    
    // Calcular total por material e pegar top 3
    const materialTotals = {};
    Object.keys(materialData).forEach(material => {
        materialTotals[material] = Object.values(materialData[material]).reduce((a, b) => a + b, 0);
    });
    
    const top3Materials = Object.entries(materialTotals)
        .sort(([,a], [,b]) => b - a)
        .slice(0, 3)
        .map(([material]) => material);
    
    // Obter meses únicos
    const months = [...new Set(data.map(item => item.mes))].sort();
    
    // Criar datasets apenas para top 3
    const datasets = [];
    const colors = ['#3498db', '#e74c3c', '#2ecc71'];
    
    top3Materials.forEach((material, index) => {
        const color = colors[index];
        datasets.push({
            label: material,
            data: months.map(month => materialData[material][month] || 0),
            backgroundColor: color + '20',
            borderColor: color,
            borderWidth: 3,
            fill: false,
            tension: 0.4
        });
    });
    
    materiaisCharts.evolucaoMensal = new Chart(ctx, {
        type: 'line',
        data: {
            labels: months,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.1)'
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            },
            plugins: {
                legend: {
                    position: 'top'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.dataset.label}: ${context.parsed.y} processos`;
                        }
                    }
                }
            }
        }
    });
}

function createModalChart(data) {
    const ctx = document.getElementById('modal-chart').getContext('2d');
    
    if (materiaisCharts.modal) {
        materiaisCharts.modal.destroy();
    }
    
    // Cores específicas para modais
    const modalColors = {
        'AEREA': '#3498db',      // Azul
        'AÉREA': '#3498db',      // Azul
        'MARITIMA': '#2ecc71',   // Verde
        'MARÍTIMA': '#2ecc71',   // Verde
        'TERRESTRE': '#f39c12',  // Laranja
        'Nao informado': '#95a5a6' // Cinza
    };
    
    const colors = data.map(item => modalColors[item.modal] || '#e74c3c');
    
    // Configuração base do gráfico
    const chartConfig = {
        type: 'doughnut',
        data: {
            labels: data.map(item => item.modal),
            datasets: [{
                data: data.map(item => item.total),
                backgroundColor: colors,
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((context.parsed / total) * 100).toFixed(1);
                            return `${context.label}: ${context.parsed} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    };
    
    // Adicionar plugin de data labels se disponível
    if (typeof ChartDataLabels !== 'undefined') {
        chartConfig.options.plugins.datalabels = {
            display: true,
            color: '#fff',
            font: {
                weight: 'bold',
                size: 12
            },
            formatter: (value, ctx) => {
                const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                const percentage = ((value / total) * 100).toFixed(1);
                return percentage > 5 ? percentage + '%' : ''; // Só mostra se > 5%
            }
        };
    }
    
    materiaisCharts.modal = new Chart(ctx, chartConfig);
}

function createCanalChart(data) {
    const ctx = document.getElementById('canal-chart').getContext('2d');
    
    if (materiaisCharts.canal) {
        materiaisCharts.canal.destroy();
    }
    
    // Cores específicas para canais baseadas nos nomes
    const canalColors = {
        'VERDE': '#2ecc71',      // Verde
        'Verde': '#2ecc71',      // Verde
        'AMARELO': '#f1c40f',    // Amarelo
        'Amarelo': '#f1c40f',    // Amarelo
        'VERMELHO': '#e74c3c',   // Vermelho
        'Vermelho': '#e74c3c',   // Vermelho
        'AZUL': '#3498db',       // Azul
        'Azul': '#3498db',       // Azul
        'Não Informado': '#95a5a6' // Cinza
    };
    
    const colors = data.map(item => canalColors[item.canal] || '#95a5a6');
    
    // Configuração base do gráfico
    const chartConfig = {
        type: 'doughnut',
        data: {
            labels: data.map(item => item.canal),
            datasets: [{
                data: data.map(item => item.total),
                backgroundColor: colors,
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((context.parsed / total) * 100).toFixed(1);
                            return `${context.label}: ${context.parsed} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    };
    
    // Adicionar plugin de data labels se disponível
    if (typeof ChartDataLabels !== 'undefined') {
        chartConfig.options.plugins.datalabels = {
            display: true,
            color: '#fff',
            font: {
                weight: 'bold',
                size: 12
            },
            formatter: (value, ctx) => {
                const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                const percentage = ((value / total) * 100).toFixed(1);
                return percentage > 5 ? percentage + '%' : ''; // Só mostra se > 5%
            }
        };
    }
    
    materiaisCharts.canal = new Chart(ctx, chartConfig);
}

function createTransitTimeChart(data) {
    const ctx = document.getElementById('transit-time-chart').getContext('2d');
    
    if (materiaisCharts.transitTime) {
        materiaisCharts.transitTime.destroy();
    }
    
    materiaisCharts.transitTime = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.map(item => item.categoria_material),
            datasets: [{
                label: 'Tempo Médio (dias)',
                data: data.map(item => item.transit_time_medio),
                backgroundColor: 'rgba(231, 76, 60, 0.7)',
                borderColor: 'rgba(231, 76, 60, 1)',
                borderWidth: 2,
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.1)'
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.dataset.label}: ${context.parsed.y.toFixed(1)} dias`;
                        }
                    }
                }
            }
        }
    });
}

// =============================================================================
// CARREGAMENTO DE TABELAS
// =============================================================================
function loadPrincipaisMateriais() {
    console.log('[MATERIAIS] Carregando principais materiais...');
    const params = new URLSearchParams(currentFilters);
    
    return fetch(`/materiais/bypass-principais-materiais?${params}`)
        .then(response => response.json())
        .then(data => {
            console.log('[MATERIAIS] Principais materiais carregados:', data.length);
            populatePrincipaisMateriaisTable(data);
        })
        .catch(error => {
            console.error('[MATERIAIS] Erro ao carregar principais materiais:', error);
        });
}

function loadDetalhamentoProcessos() {
    console.log('[MATERIAIS] Carregando detalhamento de processos...');
    const params = new URLSearchParams(currentFilters);
    
    return fetch(`/materiais/bypass-detalhamento-processos?${params}`)
        .then(response => response.json())
        .then(data => {
            console.log('[MATERIAIS] Detalhamento carregado:', data.length);
            populateDetalhamentoTable(data);
        })
        .catch(error => {
            console.error('[MATERIAIS] Erro ao carregar detalhamento:', error);
        });
}

function populatePrincipaisMateriaisTable(data) {
    const tbody = document.querySelector('#principais-materiais-table tbody');
    tbody.innerHTML = '';
    
    data.forEach(item => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${item.material}</td>
            <td>${formatValue(item.qtde_processos, 'number')}</td>
            <td>${formatValue(item.custo_total, 'currency')}</td>
            <td>${item.proxima_chegada || 'N/A'}</td>
        `;
        tbody.appendChild(row);
    });
}

function formatDate(dateString) {
    if (!dateString || dateString === 'null' || dateString === null) {
        return 'N/A';
    }
    
    // Se já está no formato brasileiro DD/MM/YYYY, retornar como está
    if (dateString.match(/^\d{2}\/\d{2}\/\d{4}$/)) {
        return dateString;
    }
    
    // Se está no formato ISO (2017-05-05T00:00:00), converter
    if (dateString.includes('T')) {
        try {
            const date = new Date(dateString);
            return date.toLocaleDateString('pt-BR');
        } catch (e) {
            return 'N/A';
        }
    }
    
    // Se está no formato YYYY-MM-DD, converter
    if (dateString.match(/^\d{4}-\d{2}-\d{2}$/)) {
        try {
            const [year, month, day] = dateString.split('-');
            return `${day}/${month}/${year}`;
        } catch (e) {
            return 'N/A';
        }
    }
    
    return dateString || 'N/A';
}

function formatNullValue(value) {
    if (value === null || value === 'null' || value === undefined || value === '') {
        return 'N/A';
    }
    return value;
}

function populateDetalhamentoTable(data) {
    console.log('[MATERIAIS] Populando tabela de detalhamento com paginação...');
    
    // Configurar paginação
    calculatePagination(data);
    renderTablePage();
    renderPagination();
    
    // Garantir que os listeners estão configurados
    setTimeout(() => {
        attachPaginationListeners();
    }, 100);
}

// =============================================================================
// FILTROS
// =============================================================================
function loadFilterOptions() {
    console.log('[MATERIAIS] Carregando opções de filtros...');
    return fetch('/materiais/bypass-filter-options')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('[MATERIAIS] Opções carregadas:', {
                materiais: data.materiais.length,
                clientes: data.clientes.length,
                modais: data.modais.length,
                canais: data.canais.length
            });
            
            // Atualizar select de materiais
            const materialSelect = document.getElementById('material-filter');
            const materiaisDinamicos = document.getElementById('materiais-dinamicos');
            
            if (materialSelect && materiaisDinamicos) {
                // Limpar opções existentes na seção dinâmica
                materiaisDinamicos.innerHTML = '';
                
                data.materiais.forEach(material => {
                    const option = document.createElement('option');
                    option.value = material;
                    
                    // Adicionar ícones aos materiais
                    let displayText = material;
                    const materialUpper = material.toUpperCase();
                    
                    if (materialUpper.includes('FERRAMENTA')) {
                        displayText = `🔧 ${material}`;
                    } else if (materialUpper.includes('QUIMICO')) {
                        displayText = `🧪 ${material}`;
                    } else if (materialUpper.includes('MANUTENCAO') || materialUpper.includes('MANUTENÇÃO')) {
                        displayText = `🔩 ${material}`;
                    } else if (materialUpper.includes('AÇO')) {
                        displayText = `🔗 ${material}`;
                    } else if (materialUpper.includes('EQUIPAMENTO')) {
                        displayText = `⚙️ ${material}`;
                    } else if (materialUpper.includes('EMBARCACAO') || materialUpper.includes('EMBARCAÇÃO')) {
                        displayText = `🚢 ${material}`;
                    } else {
                        displayText = `📦 ${material}`;
                    }
                    
                    option.textContent = displayText;
                    materiaisDinamicos.appendChild(option);
                });
                
                console.log('[MATERIAIS] ✅ Materiais populados:', data.materiais.length);
            } else {
                console.warn('[MATERIAIS] Elementos não encontrados:', {
                    materialSelect: !!materialSelect,
                    materiaisDinamicos: !!materiaisDinamicos
                });
            }
            
            // Atualizar select de clientes
            const clienteSelect = document.getElementById('cliente-filter');
            if (clienteSelect) {
                // Limpar opções existentes (exceto a primeira)
                while (clienteSelect.children.length > 1) {
                    clienteSelect.removeChild(clienteSelect.lastChild);
                }
                
                data.clientes.forEach(cliente => {
                    const option = document.createElement('option');
                    option.value = cliente;
                    option.textContent = `🏢 ${cliente}`;
                    clienteSelect.appendChild(option);
                });
                console.log('[MATERIAIS] ✅ Clientes populados:', data.clientes.length);
            }
            
            // Atualizar select de modais
            const modalSelect = document.getElementById('modal-filter');
            if (modalSelect) {
                // Limpar opções existentes (exceto a primeira)
                while (modalSelect.children.length > 1) {
                    modalSelect.removeChild(modalSelect.lastChild);
                }
                
                data.modais.forEach(modal => {
                    const option = document.createElement('option');
                    option.value = modal;
                    
                    // Adicionar ícones aos modais
                    let displayText = modal;
                    switch(modal.toUpperCase()) {
                        case 'AEREA':
                        case 'AÉREA':
                            displayText = `✈️ ${modal}`;
                            break;
                        case 'MARITIMA':
                        case 'MARÍTIMA':
                            displayText = `🚢 ${modal}`;
                            break;
                        case 'TERRESTRE':
                            displayText = `🚛 ${modal}`;
                            break;
                        default:
                            displayText = `🚚 ${modal}`;
                    }
                    
                    option.textContent = displayText;
                    modalSelect.appendChild(option);
                });
                console.log('[MATERIAIS] ✅ Modais populados:', data.modais.length);
            }
            
            // Atualizar select de canais
            const canalSelect = document.getElementById('canal-filter');
            if (canalSelect) {
                // Limpar opções existentes (exceto a primeira)
                while (canalSelect.children.length > 1) {
                    canalSelect.removeChild(canalSelect.lastChild);
                }
                
                data.canais.forEach(canal => {
                    const option = document.createElement('option');
                    option.value = canal;
                    
                    // Adicionar ícones aos canais
                    let displayText = canal;
                    switch(canal.toUpperCase()) {
                        case 'VERDE':
                            displayText = `🟢 ${canal}`;
                            break;
                        case 'AMARELO':
                            displayText = `🟡 ${canal}`;
                            break;
                        case 'VERMELHO':
                            displayText = `🔴 ${canal}`;
                            break;
                        case 'AZUL':
                            displayText = `🔵 ${canal}`;
                            break;
                        default:
                            displayText = `⚪ ${canal}`;
                    }
                    
                    option.textContent = displayText;
                    canalSelect.appendChild(option);
                });
                console.log('[MATERIAIS] ✅ Canais populados:', data.canais.length);
            }
            
            console.log('[MATERIAIS] ✅ Todos os dropdowns foram populados!');
        })
        .catch(error => {
            console.error('[MATERIAIS] Erro ao carregar opções de filtros:', error);
        });
}

function setQuickDateFilter(period) {
    console.log('[MATERIAIS] Definindo filtro rápido:', period);
    
    const hoje = new Date();
    const dataInicio = document.getElementById('data-inicio');
    const dataFim = document.getElementById('data-fim');
    
    if (!dataInicio || !dataFim) {
        console.warn('[MATERIAIS] Elementos de data não encontrados');
        return;
    }
    
    let startDate = new Date();
    
    switch (period) {
        case 'current-year':
            startDate = new Date(hoje.getFullYear(), 0, 1);
            break;
        case 'this-week':
            startDate = new Date(hoje.getTime() - (7 * 24 * 60 * 60 * 1000));
            break;
        case 'this-month':
            startDate = new Date(hoje.getFullYear(), hoje.getMonth(), 1);
            break;
        case '3-months':
            startDate = new Date(hoje.getTime() - (90 * 24 * 60 * 60 * 1000));
            break;
        case '6-months':
            startDate = new Date(hoje.getTime() - (180 * 24 * 60 * 60 * 1000));
            break;
        default:
            startDate = new Date(hoje.getTime() - (30 * 24 * 60 * 60 * 1000));
    }
    
    dataInicio.value = formatDateForInput(startDate);
    dataFim.value = formatDateForInput(hoje);
}

function applyFilters() {
    console.log('[MATERIAIS] Aplicando filtros...');
    
    // Função helper para obter valor do elemento
    const getElementValue = (id) => {
        const element = document.getElementById(id);
        return element ? element.value : '';
    };
    
    currentFilters = {
        data_inicio: getElementValue('data-inicio'),
        data_fim: getElementValue('data-fim'),
        material: getElementValue('material-filter'),
        cliente: getElementValue('cliente-filter'),
        modal: getElementValue('modal-filter'),
        canal: getElementValue('canal-filter'),
        valor_min: getElementValue('valor-min'),
        valor_max: getElementValue('valor-max')
    };
    
    // Remover filtros vazios
    Object.keys(currentFilters).forEach(key => {
        if (!currentFilters[key] || currentFilters[key] === '') {
            delete currentFilters[key];
        }
    });
    
    console.log('[MATERIAIS] Filtros aplicados:', currentFilters);
    
    // Fechar modal
    const modal = document.getElementById('filter-modal');
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = 'auto';
    }
    
    // Recarregar dados
    loadMateriaisData();
}

function clearFilters() {
    console.log('[MATERIAIS] Limpando filtros...');
    
    // Função helper para definir valor do elemento
    const setElementValue = (id, value) => {
        const element = document.getElementById(id);
        if (element) {
            element.value = value;
        }
    };
    
    // Limpar campos do formulário
    setElementValue('data-inicio', '');
    setElementValue('data-fim', '');
    setElementValue('material-filter', '');
    setElementValue('cliente-filter', '');
    setElementValue('modal-filter', '');
    setElementValue('canal-filter', '');
    setElementValue('valor-min', '');
    setElementValue('valor-max', '');
    
    // Definir período padrão (últimos 30 dias)
    const hoje = new Date();
    const trintaDiasAtras = new Date(hoje.getTime() - (30 * 24 * 60 * 60 * 1000));
    
    setElementValue('data-inicio', formatDateForInput(trintaDiasAtras));
    setElementValue('data-fim', formatDateForInput(hoje));
    
    // Aplicar filtros limpos
    applyFilters();
}

// =============================================================================
// UTILIDADES
// =============================================================================
function formatValue(value, type) {
    if (!value && value !== 0) return type === 'currency' ? 'R$ 0,00' : '0';
    
    switch (type) {
        case 'currency':
            return new Intl.NumberFormat('pt-BR', {
                style: 'currency',
                currency: 'BRL'
            }).format(value);
        case 'currency-thousands':
            // Formatação em milhares para valores grandes
            if (value >= 1000000) {
                return `R$ ${(value / 1000000).toFixed(1)}M`;
            } else if (value >= 1000) {
                return `R$ ${(value / 1000).toFixed(1)}K`;
            } else {
                return new Intl.NumberFormat('pt-BR', {
                    style: 'currency',
                    currency: 'BRL'
                }).format(value);
            }
        case 'number':
            return new Intl.NumberFormat('pt-BR').format(value);
        case 'days':
            return `${new Intl.NumberFormat('pt-BR').format(value)} dias`;
        default:
            return value.toString();
    }
}

function formatDateForInput(date) {
    return date.toISOString().split('T')[0];
}

function updateLastUpdate() {
    const now = new Date();
    const element = document.getElementById('last-update');
    if (element) {
        element.textContent = `Última atualização: ${now.toLocaleString('pt-BR')}`;
    }
}

function showLoadingOverlay() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.style.display = 'flex';
    }
}

function hideLoadingOverlay() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.style.display = 'none';
    }
}

function exportData() {
    const params = new URLSearchParams(currentFilters);
    const url = `/materiais/api/detalhamento-processos?${params}&export=csv`;
    
    // Criar link temporário para download
    const link = document.createElement('a');
    link.href = url;
    link.download = `materiais_detalhamento_${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// =============================================================================
// FUNÇÕES DE PAGINAÇÃO
// =============================================================================
function calculatePagination(data) {
    originalTableData = data;
    totalRecords = data.length;
    totalPages = Math.ceil(totalRecords / pageSize);
    
    // Garantir que currentPage não seja maior que totalPages
    if (currentPage > totalPages) {
        currentPage = 1;
    }
    
    console.log(`[MATERIAIS] Paginação calculada: ${totalRecords} registros, ${totalPages} páginas`);
}

function renderPagination() {
    const paginationContainer = document.getElementById('pagination-container');
    if (!paginationContainer) return;
    
    // Atualizar informações da página
    const pageInfo = document.getElementById('page-info');
    if (pageInfo) {
        const startRecord = (currentPage - 1) * pageSize + 1;
        const endRecord = Math.min(currentPage * pageSize, totalRecords);
        pageInfo.textContent = `${startRecord}-${endRecord} de ${totalRecords}`;
    }
    
    // Atualizar controles de paginação
    const paginationControls = document.getElementById('pagination-controls');
    if (!paginationControls) return;
    
    paginationControls.innerHTML = '';
    
    // Botão "Anterior"
    const prevBtn = document.createElement('button');
    prevBtn.className = 'pagination-btn';
    prevBtn.textContent = '‹';
    prevBtn.disabled = currentPage === 1;
    prevBtn.addEventListener('click', () => {
        if (currentPage > 1) {
            currentPage--;
            renderTablePage();
            renderPagination();
        }
    });
    paginationControls.appendChild(prevBtn);
    
    // Botões de páginas
    const maxVisiblePages = 5;
    let startPage = Math.max(1, currentPage - Math.floor(maxVisiblePages / 2));
    let endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);
    
    if (endPage - startPage + 1 < maxVisiblePages) {
        startPage = Math.max(1, endPage - maxVisiblePages + 1);
    }
    
    for (let i = startPage; i <= endPage; i++) {
        const pageBtn = document.createElement('button');
        pageBtn.className = 'pagination-btn';
        pageBtn.textContent = i;
        pageBtn.classList.toggle('active', i === currentPage);
        pageBtn.addEventListener('click', () => {
            currentPage = i;
            renderTablePage();
            renderPagination();
        });
        paginationControls.appendChild(pageBtn);
    }
    
    // Botão "Próximo"
    const nextBtn = document.createElement('button');
    nextBtn.className = 'pagination-btn';
    nextBtn.textContent = '›';
    nextBtn.disabled = currentPage === totalPages;
    nextBtn.addEventListener('click', () => {
        if (currentPage < totalPages) {
            currentPage++;
            renderTablePage();
            renderPagination();
        }
    });
    paginationControls.appendChild(nextBtn);
}

function renderTablePage() {
    const startIndex = (currentPage - 1) * pageSize;
    const endIndex = startIndex + pageSize;
    const pageData = originalTableData.slice(startIndex, endIndex);
    
    const tbody = document.querySelector('#detalhamento-table tbody');
    tbody.innerHTML = '';
    
    pageData.forEach(item => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${formatDate(item.data_abertura)}</td>
            <td>${formatNullValue(item.numero_pedido)}</td>
            <td>${formatNullValue(item.cliente)}</td>
            <td>${formatNullValue(item.material)}</td>
            <td>${formatDate(item.data_embarque)}</td>
            <td>${formatDate(item.data_chegada)}</td>
            <td>${formatNullValue(item.status_carga)}</td>
            <td>${formatNullValue(item.canal)}</td>
            <td>${formatValue(item.custo_total, 'currency')}</td>
        `;
        tbody.appendChild(row);
    });
}

function attachPaginationListeners() {
    const pageSizeSelect = document.getElementById('page-size-select');
    if (pageSizeSelect) {
        pageSizeSelect.addEventListener('change', (e) => {
            pageSize = parseInt(e.target.value);
            currentPage = 1;
            calculatePagination(originalTableData);
            renderTablePage();
            renderPagination();
        });
    }
}

// =============================================================================
// FUNÇÕES GLOBAIS
// =============================================================================
window.refreshMateriaisData = function() {
    loadMateriaisData();
};

window.materiaisCharts = materiaisCharts;
