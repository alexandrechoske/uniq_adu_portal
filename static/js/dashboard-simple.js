// === DASHBOARD EXECUTIVO - JAVASCRIPT ===

// === CONFIGURAÇÕES GLOBAIS ===
console.log('[Dashboard] Inicializando dashboard simplificado...');

// Variáveis globais
let monthlyChart = null;
let canalChart = null;
let armazemChart = null;
let materialChart = null;
let dashboardData = null;
let currentPage = 1;
let pageSize = 10;
let totalRecords = 0;
let allOperations = [];

// === UTILITÁRIOS ===
function formatValue(value, type = 'number') {
    if (!value || value === 0 || isNaN(value)) return type === 'currency' ? 'R$ 0' : '0';
    
    const num = parseFloat(value);
    let formatted;
    let suffix = '';
    
    if (num >= 1000000000) {
        formatted = (num / 1000000000).toFixed(1);
        suffix = 'B';
    } else if (num >= 1000000) {
        formatted = (num / 1000000).toFixed(1);
        suffix = 'M';
    } else if (num >= 1000) {
        formatted = (num / 1000).toFixed(1);
        suffix = 'K';
    } else {
        formatted = num.toFixed(0);
    }
    
    // Remove .0 desnecessário
    if (formatted.endsWith('.0')) {
        formatted = formatted.slice(0, -2);
    }
    
    if (type === 'currency') {
        return `R$ ${formatted}${suffix}`;
    }
    
    return `${formatted}${suffix}`;
}

// === CARREGAMENTO DE DADOS ===
async function loadDashboardData() {
    try {
        const response = await fetch('/api/dashboard-data?charts=1');
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        if (result.success && result.data) {
            dashboardData = result.data;
            return dashboardData;
        } else {
            throw new Error(result.error || 'Resposta inválida da API');
        }
    } catch (error) {
        console.error('Erro ao carregar dados:', error);
        throw error;
    }
}

async function loadFullDashboardData() {
    try {
        const response = await fetch('/api/dashboard-data');
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        if (result.success && result.data) {
            // Ordenar por data de abertura (mais recente primeiro)
            if (result.data.recent_operations) {
                result.data.recent_operations.sort((a, b) => {
                    const dateA = new Date(a.data_registro);
                    const dateB = new Date(b.data_registro);
                    return dateB - dateA; // Ordem decrescente
                });
                
                allOperations = result.data.recent_operations;
                totalRecords = allOperations.length;
            }
            
            return result.data;
        } else {
            throw new Error(result.error || 'Resposta inválida da API');
        }
    } catch (error) {
        console.error('Erro ao carregar dados completos:', error);
        throw error;
    }
}

// === ATUALIZAÇÃO DE KPIs ===
function updateKPIs(kpis) {
    if (!kpis) return;
    
    document.getElementById('kpi-total').textContent = formatValue(kpis.total);
    document.getElementById('kpi-valor').textContent = formatValue(kpis.vmcv_total, 'currency');
    document.getElementById('kpi-aereo').textContent = formatValue(kpis.aereo);
    document.getElementById('kpi-maritimo').textContent = formatValue(kpis.maritimo);
}

// === RENDERIZAÇÃO DA TABELA COM PAGINAÇÃO ===
function renderTable(data) {
    const container = document.getElementById('table-container');
    
    if (!data || !data.recent_operations || data.recent_operations.length === 0) {
        container.innerHTML = '<div class="table-empty">Nenhuma operação encontrada</div>';
        return;
    }
    
    allOperations = data.recent_operations;
    totalRecords = allOperations.length;
    
    renderTablePage();
}

function renderTablePage() {
    const container = document.getElementById('table-container');
    const startIndex = (currentPage - 1) * pageSize;
    const endIndex = startIndex + pageSize;
    const pageOperations = allOperations.slice(startIndex, endIndex);
    
    let tableHTML = `
        <table class="data-table">
            <thead>
                <tr>
                    <th>Processo</th>
                    <th>Data</th>
                    <th>Modal</th>
                    <th>Canal</th>
                    <th>Armazém</th>
                    <th>Material</th>
                    <th>Valor (R$)</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    pageOperations.forEach(op => {
        // Formatação do modal
        const modalClass = op.modal_descricao ? 
            `modal-${op.modal_descricao.toLowerCase().replace(/[^a-z]/g, '')}` : 'modal-terrestre';
        
        // Formatação do canal
        const canalClass = op.canal_descricao ? 
            `canal-${op.canal_descricao.toLowerCase()}` : 'canal-cinza';
        
        // Formatação da data
        const dataFormatada = op.data_registro ? 
            new Date(op.data_registro).toLocaleDateString('pt-BR') : '-';
        
        // Truncar textos longos
        const armazem = op.urf_entrada_descricao ? 
            (op.urf_entrada_descricao.length > 30 ? 
                op.urf_entrada_descricao.substring(0, 27) + '...' : 
                op.urf_entrada_descricao) : '-';
        
        const material = op.mercadoria ? 
            (op.mercadoria.length > 35 ? 
                op.mercadoria.substring(0, 32) + '...' : 
                op.mercadoria) : '-';
        
        tableHTML += `
            <tr>
                <td>${op.numero_processo || '-'}</td>
                <td>${dataFormatada}</td>
                <td>
                    <span class="table-modal ${modalClass}">
                        ${op.modal_descricao || 'N/D'}
                    </span>
                </td>
                <td>
                    <span class="table-canal ${canalClass}">
                        ${op.canal_descricao || 'N/D'}
                    </span>
                </td>
                <td title="${op.urf_entrada_descricao || ''}">${armazem}</td>
                <td title="${op.mercadoria || ''}">${material}</td>
                <td class="table-value">${formatValue(op.valor_cif_real || 0, 'currency')}</td>
            </tr>
        `;
    });
    
    tableHTML += `
            </tbody>
        </table>
    `;
    
    // Adicionar paginação
    tableHTML += renderPagination();
    
    container.innerHTML = tableHTML;
    
    // Adicionar event listeners para paginação
    attachPaginationListeners();
}

function renderPagination() {
    const totalPages = Math.ceil(totalRecords / pageSize);
    const startRecord = (currentPage - 1) * pageSize + 1;
    const endRecord = Math.min(currentPage * pageSize, totalRecords);
    
    let paginationHTML = `
        <div class="pagination-container">
            <div class="pagination-info">
                Mostrando ${startRecord} - ${endRecord} de ${totalRecords} registros
            </div>
            <div class="pagination-controls">
                <button class="pagination-btn" id="first-page" ${currentPage === 1 ? 'disabled' : ''}>
                    ⏮
                </button>
                <button class="pagination-btn" id="prev-page" ${currentPage === 1 ? 'disabled' : ''}>
                    ⏪
                </button>
    `;
    
    // Números das páginas
    const maxVisiblePages = 5;
    let startPage = Math.max(1, currentPage - Math.floor(maxVisiblePages / 2));
    let endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);
    
    // Ajustar se necessário
    if (endPage - startPage + 1 < maxVisiblePages) {
        startPage = Math.max(1, endPage - maxVisiblePages + 1);
    }
    
    for (let i = startPage; i <= endPage; i++) {
        paginationHTML += `
            <button class="pagination-btn page-num ${i === currentPage ? 'active' : ''}" data-page="${i}">
                ${i}
            </button>
        `;
    }
    
    paginationHTML += `
                <button class="pagination-btn" id="next-page" ${currentPage === totalPages ? 'disabled' : ''}>
                    ⏩
                </button>
                <button class="pagination-btn" id="last-page" ${currentPage === totalPages ? 'disabled' : ''}>
                    ⏭
                </button>
            </div>
            <div class="page-size-selector">
                <label for="page-size">Itens por página:</label>
                <select id="page-size" class="page-size-select">
                    <option value="10" ${pageSize === 10 ? 'selected' : ''}>10</option>
                    <option value="25" ${pageSize === 25 ? 'selected' : ''}>25</option>
                    <option value="50" ${pageSize === 50 ? 'selected' : ''}>50</option>
                    <option value="100" ${pageSize === 100 ? 'selected' : ''}>100</option>
                </select>
            </div>
        </div>
    `;
    
    return paginationHTML;
}

function attachPaginationListeners() {
    // Primeira página
    document.getElementById('first-page')?.addEventListener('click', () => {
        currentPage = 1;
        renderTablePage();
    });
    
    // Página anterior
    document.getElementById('prev-page')?.addEventListener('click', () => {
        if (currentPage > 1) {
            currentPage--;
            renderTablePage();
        }
    });
    
    // Próxima página
    document.getElementById('next-page')?.addEventListener('click', () => {
        const totalPages = Math.ceil(totalRecords / pageSize);
        if (currentPage < totalPages) {
            currentPage++;
            renderTablePage();
        }
    });
    
    // Última página
    document.getElementById('last-page')?.addEventListener('click', () => {
        currentPage = Math.ceil(totalRecords / pageSize);
        renderTablePage();
    });
    
    // Números das páginas
    document.querySelectorAll('.page-num').forEach(btn => {
        btn.addEventListener('click', (e) => {
            currentPage = parseInt(e.target.dataset.page);
            renderTablePage();
        });
    });
    
    // Tamanho da página
    document.getElementById('page-size')?.addEventListener('change', (e) => {
        pageSize = parseInt(e.target.value);
        currentPage = 1; // Resetar para primeira página
        renderTablePage();
    });
}

// === CRIAÇÃO DE GRÁFICO MENSAL COM DATA LABELS ===
function createMonthlyChart(data) {
    const ctx = document.getElementById('monthly-chart');
    if (!ctx) {
        console.error('Canvas monthly-chart não encontrado');
        return;
    }
    
    // Destruir gráfico existente
    if (monthlyChart) {
        monthlyChart.destroy();
        monthlyChart = null;
    }
    
    // Verificar dados
    if (!data || !data.months || !data.processes) {
        console.error('Dados inválidos para gráfico mensal');
        return;
    }
    
    try {
        monthlyChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.months,
                datasets: [{
                    label: 'Operações',
                    data: data.processes,
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    pointBackgroundColor: '#3b82f6',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    datalabels: {
                        display: true,
                        anchor: 'end',
                        align: 'top',
                        formatter: (value) => value,
                        font: {
                            size: 11,
                            weight: 'bold'
                        },
                        color: '#374151',
                        backgroundColor: '#ffffff',
                        borderColor: '#3b82f6',
                        borderRadius: 4,
                        borderWidth: 1,
                        padding: 4
                    },
                    legend: {
                        display: true,
                        position: 'top'
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleColor: '#ffffff',
                        bodyColor: '#ffffff',
                        cornerRadius: 6
                    }
                },
                scales: {
                    x: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Período'
                        }
                    },
                    y: {
                        display: true,
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Número de Operações'
                        }
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                }
            },
            plugins: [ChartDataLabels]
        });
        
        console.log('Gráfico mensal criado com sucesso');
        
    } catch (error) {
        console.error('Erro ao criar gráfico mensal:', error);
    }
}

// === CRIAÇÃO DE GRÁFICO DE CANAL COM DATA LABELS ===
function createCanalChart(data) {
    const ctx = document.getElementById('canal-chart');
    if (!ctx) {
        console.error('Canvas canal-chart não encontrado');
        return;
    }
    
    // Destruir gráfico existente
    if (canalChart) {
        canalChart.destroy();
        canalChart = null;
    }
    
    // Verificar dados
    if (!data || !data.labels || !data.values) {
        console.error('Dados inválidos para gráfico de canal');
        return;
    }
    
    // Cores específicas para canais
    const colors = {
        'Verde': '#10b981',
        'Amarelo': '#f59e0b', 
        'Vermelho': '#ef4444',
        'Cinza': '#6b7280'
    };
    
    const backgroundColors = data.labels.map(label => colors[label] || '#6b7280');
    
    try {
        canalChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: data.labels,
                datasets: [{
                    data: data.values,
                    backgroundColor: backgroundColors,
                    borderColor: backgroundColors,
                    borderWidth: 2,
                    hoverBorderWidth: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '60%',
                plugins: {
                    datalabels: {
                        display: true,
                        formatter: (value, context) => {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(1);
                            return `${value}\n(${percentage}%)`;
                        },
                        color: '#ffffff',
                        font: {
                            size: 11,
                            weight: 'bold'
                        },
                        textAlign: 'center',
                        anchor: 'center',
                        align: 'center'
                    },
                    legend: {
                        position: 'bottom',
                        labels: {
                            usePointStyle: true,
                            padding: 15
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleColor: '#ffffff',
                        bodyColor: '#ffffff',
                        cornerRadius: 6,
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.parsed || 0;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((value / total) * 100).toFixed(1);
                                return `${label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                }
            },
            plugins: [ChartDataLabels]
        });
        
        console.log('Gráfico de canal criado com sucesso');
        
    } catch (error) {
        console.error('Erro ao criar gráfico de canal:', error);
    }
}

// === CRIAÇÃO DE GRÁFICO DE ARMAZÉM ===
function createArmazemChart(data) {
    const ctx = document.getElementById('armazem-chart');
    if (!ctx) {
        console.error('Canvas armazem-chart não encontrado');
        return;
    }
    
    // Destruir gráfico existente
    if (armazemChart) {
        armazemChart.destroy();
        armazemChart = null;
    }
    
    // Verificar dados
    if (!data || !data.labels || !data.values) {
        console.error('Dados inválidos para gráfico de armazém');
        return;
    }
    
    // Ordenar por valor (maior para menor) - dados já vêm ordenados crescente, então reverter
    const sortedData = data.labels.map((label, index) => ({
        label: label,
        value: data.values[index]
    })).sort((a, b) => b.value - a.value); // Ordem decrescente
    
    const sortedLabels = sortedData.map(item => item.label);
    const sortedValues = sortedData.map(item => item.value);
    
    // Cores para armazéns (gradiente de azuis)
    const colors = [
        '#1e40af', '#2563eb', '#3b82f6', '#60a5fa', '#93c5fd',
        '#1e3a8a', '#1d4ed8', '#2dd4bf', '#06b6d4', '#0891b2'
    ];
    
    try {
        armazemChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: sortedLabels.map(label => {
                    // Truncar labels muito longos
                    return label.length > 20 ? label.substring(0, 17) + '...' : label;
                }),
                datasets: [{
                    label: 'Quantidade de Operações',
                    data: sortedValues,
                    backgroundColor: colors.slice(0, sortedLabels.length),
                    borderColor: colors.slice(0, sortedLabels.length),
                    borderWidth: 1,
                    borderRadius: 4,
                    borderSkipped: false
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
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleColor: '#ffffff',
                        bodyColor: '#ffffff',
                        cornerRadius: 6,
                        callbacks: {
                            label: function(context) {
                                const value = context.parsed.x;
                                return `Operações: ${value}`;
                            },
                            title: function(context) {
                                // Mostrar nome completo no tooltip
                                return sortedLabels[context[0].dataIndex];
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        display: true,
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Quantidade de Operações'
                        }
                    },
                    y: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Armazéns'
                        },
                        ticks: {
                            font: {
                                size: 10
                            }
                        }
                    }
                }
            }
        });
        
        console.log('Gráfico de armazém criado com sucesso');
        
    } catch (error) {
        console.error('Erro ao criar gráfico de armazém:', error);
    }
}

// === CRIAÇÃO DE GRÁFICO DE MATERIAL ===
function createMaterialChart(data) {
    const ctx = document.getElementById('material-chart');
    if (!ctx) {
        console.error('Canvas material-chart não encontrado');
        return;
    }
    
    // Destruir gráfico existente
    if (materialChart) {
        materialChart.destroy();
        materialChart = null;
    }
    
    // Verificar dados
    if (!data || !data.labels || !data.values) {
        console.error('Dados inválidos para gráfico de material');
        return;
    }
    
    // Ordenar por valor (maior para menor) - dados já vêm ordenados crescente, então reverter
    const sortedData = data.labels.map((label, index) => ({
        label: label,
        value: data.values[index]
    })).sort((a, b) => b.value - a.value); // Ordem decrescente
    
    const sortedLabels = sortedData.map(item => item.label);
    const sortedValues = sortedData.map(item => item.value);
    
    // Cores para materiais (gradiente de verdes)
    const colors = [
        '#166534', '#16a34a', '#22c55e', '#4ade80', '#86efac',
        '#14532d', '#15803d', '#059669', '#0d9488', '#0f766e'
    ];
    
    try {
        materialChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: sortedLabels.map(label => {
                    // Truncar labels muito longos
                    return label.length > 25 ? label.substring(0, 22) + '...' : label;
                }),
                datasets: [{
                    label: 'Valor Total (R$ Milhões)',
                    data: sortedValues,
                    backgroundColor: colors.slice(0, sortedLabels.length),
                    borderColor: colors.slice(0, sortedLabels.length),
                    borderWidth: 1,
                    borderRadius: 4,
                    borderSkipped: false
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
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleColor: '#ffffff',
                        bodyColor: '#ffffff',
                        cornerRadius: 6,
                        callbacks: {
                            label: function(context) {
                                const value = context.parsed.x;
                                return `Valor: R$ ${value.toFixed(1)}M`;
                            },
                            title: function(context) {
                                // Mostrar nome completo no tooltip
                                return sortedLabels[context[0].dataIndex];
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        display: true,
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Valor Total (R$ Milhões)'
                        },
                        ticks: {
                            callback: function(value) {
                                return `R$ ${value.toFixed(1)}M`;
                            }
                        }
                    },
                    y: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Materiais'
                        },
                        ticks: {
                            font: {
                                size: 10
                            }
                        }
                    }
                }
            }
        });
        
        console.log('Gráfico de material criado com sucesso');
        
    } catch (error) {
        console.error('Erro ao criar gráfico de material:', error);
    }
}

// === INICIALIZAÇÃO ===
async function initializeDashboard() {
    console.log('Inicializando dashboard...');
    
    try {
        // Carregar dados do gráfico
        const chartData = await loadDashboardData();
        
        // Criar gráficos
        if (chartData && chartData.monthly) {
            createMonthlyChart(chartData.monthly);
        }
        
        if (chartData && chartData.canal) {
            createCanalChart(chartData.canal);
        }
        
        if (chartData && chartData.armazem) {
            createArmazemChart(chartData.armazem);
        }
        
        if (chartData && chartData.material) {
            createMaterialChart(chartData.material);
        }
        
        // Carregar dados completos para KPIs e tabela
        const fullData = await loadFullDashboardData();
        if (fullData && fullData.kpis) {
            updateKPIs(fullData.kpis);
        }
        
        // Renderizar tabela
        renderTable(fullData);
        
        // Atualizar timestamp
        document.getElementById('last-update').textContent = 
            `Última atualização: ${new Date().toLocaleTimeString()}`;
        
        console.log('Dashboard inicializado com sucesso');
        
    } catch (error) {
        console.error('Erro na inicialização:', error);
    }
}

// === EVENT LISTENERS ===
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM carregado, aguardando 1 segundo...');
    
    setTimeout(() => {
        // Verificar se Chart.js está disponível
        if (typeof Chart === 'undefined') {
            console.error('Chart.js não está disponível');
            return;
        }
        
        console.log(`Chart.js ${Chart.version} carregado`);
        
        // Verificar se ChartDataLabels está disponível
        if (typeof ChartDataLabels === 'undefined') {
            console.error('ChartDataLabels plugin não está disponível');
            return;
        }
        
        // Registrar o plugin DataLabels
        Chart.register(ChartDataLabels);
        
        // Inicializar dashboard
        initializeDashboard();
        
    }, 1000);
});

// Botão de refresh
document.addEventListener('DOMContentLoaded', function() {
    const refreshBtn = document.getElementById('refresh-chart');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', function() {
            console.log('Refresh manual solicitado');
            initializeDashboard();
        });
    }
    
    const refreshTableBtn = document.getElementById('refresh-table');
    if (refreshTableBtn) {
        refreshTableBtn.addEventListener('click', async function() {
            console.log('Refresh da tabela solicitado');
            try {
                const fullData = await loadFullDashboardData();
                renderTable(fullData);
            } catch (error) {
                console.error('Erro ao atualizar tabela:', error);
            }
        });
    }
});

// Redimensionamento
window.addEventListener('resize', function() {
    if (monthlyChart) {
        monthlyChart.resize();
    }
    if (canalChart) {
        canalChart.resize();
    }
    if (armazemChart) {
        armazemChart.resize();
    }
    if (materialChart) {
        materialChart.resize();
    }
});

console.log('Script dashboard-simple.js carregado');
