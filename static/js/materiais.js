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

// =============================================================================
// INICIALIZAÇÃO
// =============================================================================
document.addEventListener('DOMContentLoaded', function() {
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
        loadMateriaisData()
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
        { id: 'kpi-valor-total', value: data.valor_total, format: 'currency' },
        { id: 'kpi-custo-total', value: data.custo_total, format: 'currency' },
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
    console.log('[MATERIAIS] Pulando carregamento de transit time por enquanto...');
    return Promise.resolve();
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
    
    // Obter meses únicos
    const months = [...new Set(data.map(item => item.mes))].sort();
    
    // Criar datasets
    const datasets = [];
    const colors = ['#3498db', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b6'];
    let colorIndex = 0;
    
    Object.keys(materialData).forEach(material => {
        const color = colors[colorIndex % colors.length];
        datasets.push({
            label: material,
            data: months.map(month => materialData[material][month] || 0),
            backgroundColor: color + '20',
            borderColor: color,
            borderWidth: 3,
            fill: false,
            tension: 0.4
        });
        colorIndex++;
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
    
    materiaisCharts.modal = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: data.map(item => item.modal),
            datasets: [{
                data: data.map(item => item.total),
                backgroundColor: [
                    '#3498db',
                    '#e74c3c',
                    '#2ecc71',
                    '#f39c12',
                    '#9b59b6'
                ],
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
                }
            }
        }
    });
}

function createCanalChart(data) {
    const ctx = document.getElementById('canal-chart').getContext('2d');
    
    if (materiaisCharts.canal) {
        materiaisCharts.canal.destroy();
    }
    
    materiaisCharts.canal = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: data.map(item => item.canal),
            datasets: [{
                data: data.map(item => item.total),
                backgroundColor: [
                    '#2ecc71',
                    '#e74c3c',
                    '#f39c12',
                    '#9b59b6',
                    '#3498db'
                ],
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
                }
            }
        }
    });
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
                }
            }
        }
    });
}

// =============================================================================
// CARREGAMENTO DE TABELAS
// =============================================================================
function loadPrincipaisMateriais() {
    console.log('[MATERIAIS] Pulando carregamento de principais materiais por enquanto...');
    return Promise.resolve();
}

function loadDetalhamentoProcessos() {
    console.log('[MATERIAIS] Pulando carregamento de detalhamento por enquanto...');
    return Promise.resolve();
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

function populateDetalhamentoTable(data) {
    const tbody = document.querySelector('#detalhamento-table tbody');
    tbody.innerHTML = '';
    
    // Limitar a 100 registros para performance
    data.slice(0, 100).forEach(item => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${item.data_abertura}</td>
            <td>${item.numero_pedido}</td>
            <td>${item.cliente}</td>
            <td>${item.material}</td>
            <td>${item.data_embarque}</td>
            <td>${item.data_chegada}</td>
            <td>${item.status_carga}</td>
            <td>${item.canal}</td>
            <td>${formatValue(item.custo_total, 'currency')}</td>
        `;
        tbody.appendChild(row);
    });
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
// FUNÇÕES GLOBAIS
// =============================================================================
window.refreshMateriaisData = function() {
    loadMateriaisData();
};

window.materiaisCharts = materiaisCharts;
