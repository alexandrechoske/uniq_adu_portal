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
let loadingAttempts = 0;
let dashboardInitialized = false; // Flag para evitar múltiplas inicializações
const MAX_LOADING_ATTEMPTS = 30; // 30 segundos máximo

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

// === FUNÇÕES DE LOADING ===
function showLoadingState() {
    console.log('[Dashboard] Mostrando estado de carregamento...');
    
    // Mostrar loading nos KPIs
    const kpiElements = document.querySelectorAll('.kpi-value');
    kpiElements.forEach(element => {
        element.innerHTML = '<div class="loading-dot">●</div>';
        element.classList.add('loading');
    });
    
    // Mostrar loading nos gráficos (preservar canvas)
    const chartContainers = document.querySelectorAll('.chart-container');
    chartContainers.forEach(container => {
        // Verificar se já tem um canvas
        const existingCanvas = container.querySelector('canvas');
        if (existingCanvas) {
            // Se tem canvas, apenas esconder e mostrar loading overlay
            existingCanvas.style.display = 'none';
        }
        
        // Adicionar overlay de loading se não existe
        let loadingOverlay = container.querySelector('.chart-loading');
        if (!loadingOverlay) {
            const overlay = document.createElement('div');
            overlay.className = 'chart-loading';
            overlay.innerHTML = `
                <div class="loading-spinner"></div>
                <p>Carregando dados do gráfico...</p>
            `;
            container.appendChild(overlay);
        }
    });
    
    // Mostrar loading na tabela
    const tableContainer = document.getElementById('table-container');
    if (tableContainer) {
        tableContainer.innerHTML = `
            <div class="loading">
                <div class="spinner"></div>
                Carregando operações recentes...
            </div>
        `;
    }
    
    // Animar os pontos de loading
    animateLoadingDots();
}

function animateLoadingDots() {
    const dots = document.querySelectorAll('.loading-dot');
    let frame = 0;
    
    const animation = setInterval(() => {
        dots.forEach((dot, index) => {
            const opacity = Math.sin((frame + index * 2) * 0.3) * 0.5 + 0.5;
            dot.style.opacity = opacity;
        });
        frame++;
    }, 100);
    
    // Parar animação após carregamento ou timeout
    setTimeout(() => clearInterval(animation), 30000);
}

function hideLoadingState() {
    console.log('[Dashboard] Ocultando estado de carregamento...');
    
    const loadingElements = document.querySelectorAll('.loading');
    loadingElements.forEach(element => {
        element.classList.remove('loading');
    });
    
    // Remover loading overlays dos gráficos e mostrar canvas
    const chartContainers = document.querySelectorAll('.chart-container');
    chartContainers.forEach(container => {
        const loadingOverlay = container.querySelector('.chart-loading');
        if (loadingOverlay) {
            loadingOverlay.remove();
        }
        
        const canvas = container.querySelector('canvas');
        if (canvas) {
            canvas.style.display = 'block';
        }
    });
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
    
    // Atualizar cada KPI usando os novos IDs e campos corretos
    document.getElementById('kpi-total-processos').textContent = formatValue(kpis.total_processos);
    document.getElementById('kpi-total-despesas').textContent = formatValue(kpis.total_despesas, 'currency');
    document.getElementById('kpi-modal-aereo').textContent = formatValue(kpis.modal_aereo);
    document.getElementById('kpi-modal-maritimo').textContent = formatValue(kpis.modal_maritimo);
    document.getElementById('kpi-em-transito').textContent = formatValue(kpis.em_transito);
    document.getElementById('kpi-di-registrada').textContent = formatValue(kpis.di_registrada);
    document.getElementById('kpi-despesa-media').textContent = formatValue(kpis.despesa_media_por_processo, 'currency');
    document.getElementById('kpi-mes-atual').textContent = formatValue(kpis.despesa_mes_atual, 'currency');
    
    console.log('[Dashboard] KPIs atualizados:', kpis);
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
    
    console.log('[Dashboard] Dados da tabela:', allOperations.slice(0, 2)); // Debug: mostrar primeiros 2 registros
    
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
                    <th>Cliente</th>
                    <th>Pedido</th>
                    <th>Data Embarque</th>
                    <th>Local Embarque</th>
                    <th>Modal</th>
                    <th>Status</th>
                    <th>Mercadoria</th>
                    <th>Despesas (R$)</th>
                    <th>Recinto</th>
                    <th>Previsão Chegada</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    pageOperations.forEach(op => {
        // Formatação do modal
        const modal = op.modal || '';
        const modalClass = modal ? 
            `modal-${modal.toLowerCase().replace(/[^a-z]/g, '')}` : 'modal-terrestre';
        
        // Formatação do status
        const status = op.status || '';
        const statusClass = status ? 
            `status-${status.toLowerCase().replace(/[^a-z]/g, '')}` : 'status-default';
        
        // Formatação das datas
        const dataEmbarque = op.data_embarque ? 
            new Date(op.data_embarque).toLocaleDateString('pt-BR') : '-';
        const dataChegada = op.data_chegada ? 
            new Date(op.data_chegada).toLocaleDateString('pt-BR') : '-';
        
        // Truncar textos longos
        const cliente = op.cliente ? 
            (op.cliente.length > 25 ? 
                op.cliente.substring(0, 22) + '...' : 
                op.cliente) : '-';
                
        const localEmbarque = op.local_embarque ? 
            (op.local_embarque.length > 25 ? 
                op.local_embarque.substring(0, 22) + '...' : 
                op.local_embarque) : '-';
        
        const material = op.mercadoria ? 
            (op.mercadoria.length > 30 ? 
                op.mercadoria.substring(0, 27) + '...' : 
                op.mercadoria) : '-';
                
        const recinto = op.recinto ? 
            (op.recinto.length > 20 ? 
                op.recinto.substring(0, 17) + '...' : 
                op.recinto) : '-';
        
        // Valor das despesas
        const despesas = op.despesas || 0;
        
        tableHTML += `
            <tr>
                <td title="${op.cliente || ''}">${cliente}</td>
                <td>${op.numero_pedido || '-'}</td>
                <td>${dataEmbarque}</td>
                <td title="${op.local_embarque || ''}">${localEmbarque}</td>
                <td>
                    <span class="table-modal ${modalClass}">
                        ${modal || 'N/D'}
                    </span>
                </td>
                <td>
                    <span class="table-status ${statusClass}">
                        ${status || 'N/D'}
                    </span>
                </td>
                <td title="${op.mercadoria || ''}">${material}</td>
                <td class="table-value">${formatValue(despesas, 'currency')}</td>
                <td title="${op.recinto || ''}">${recinto}</td>
                <td>${dataChegada}</td>
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
                    <option value="250" ${pageSize === 250 ? 'selected' : ''}>250</option>
                    <option value="500" ${pageSize === 500 ? 'selected' : ''}>500</option>
                    <option value="1000" ${pageSize === 1000 ? 'selected' : ''}>1000</option>
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
    
    console.log('[Chart] Canvas monthly-chart encontrado:', ctx);
    console.log('[Chart] Canvas display style:', ctx.style.display);
    console.log('[Chart] Canvas visível:', ctx.offsetWidth > 0 && ctx.offsetHeight > 0);
    
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
                        display: false,
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
    console.log('[Chart] Iniciando criação do gráfico de canal com dados:', data);
    
    const ctx = document.getElementById('canal-chart');
    if (!ctx) {
        console.error('Canvas canal-chart não encontrado');
        return;
    }
    
    console.log('[Chart] Canvas canal-chart encontrado:', ctx);
    
    // Destruir gráfico existente
    if (canalChart) {
        canalChart.destroy();
        canalChart = null;
    }
    
    // Verificar dados
    if (!data || !data.labels || !data.values) {
        console.error('Dados inválidos para gráfico de canal:', data);
        return;
    }
      // Cores específicas para modais - função de mapeamento robusta
    function getModalColor(modalName) {
        const colorMap = {
            'AEREA': '#3b82f6',      // Azul para aéreo
            'AÉREA': '#3b82f6',      // Azul para aéreo (com acento)
            'MARITIMA': '#10b981',   // Verde para marítimo
            'MARÍTIMA': '#10b981',   // Verde para marítimo (com acento)
            'TERRESTRE': '#f59e0b',  // Amarelo para terrestre
            'LACUSTRE': '#8b5cf6',   // Roxo para lacustre
            'MULTIMODAL': '#ef4444', // Vermelho para multimodal
            'RODOVIARIO': '#f59e0b', // Amarelo para rodoviário
            'RODOVIÁRIA': '#f59e0b', // Amarelo para rodoviário (com acento)
            'FERROVIARIO': '#6b7280',// Cinza para ferroviário
            'FERROVIÁRIA': '#6b7280' // Cinza para ferroviário (com acento)
        };
        
        // Normalizar o nome (remover espaços, converter para maiúsculo)
        const normalizedName = modalName ? modalName.toString().trim().toUpperCase() : '';
        
        // Buscar cor exata
        if (colorMap[normalizedName]) {
            return colorMap[normalizedName];
        }
        
        // Buscar por substring (para casos como "MODAL AÉREO")
        for (const [key, color] of Object.entries(colorMap)) {
            if (normalizedName.includes(key) || key.includes(normalizedName)) {
                return color;
            }
        }
        
        // Cor padrão
        return '#6b7280';
    }

    const backgroundColors = data.labels.map((label, index) => {
        const color = getModalColor(label);
        console.log(`[Chart] Modal: "${label}" -> Cor: ${color}`);
        return color;
    });
    
    try {
        canalChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: data.labels,
                datasets: [{
                    data: data.values,
                    backgroundColor: backgroundColors,
                    borderColor: '#ffffff',  // Borda branca para destacar
                    borderWidth: 2,
                    hoverBorderWidth: 4,
                    hoverBackgroundColor: backgroundColors  // Manter cores no hover
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
    console.log('[Chart] Iniciando criação do gráfico de armazém com dados:', data);
    
    const ctx = document.getElementById('armazem-chart');
    if (!ctx) {
        console.error('Canvas armazem-chart não encontrado');
        return;
    }
    
    console.log('[Chart] Canvas armazem-chart encontrado:', ctx);
    
    // Destruir gráfico existente
    if (armazemChart) {
        armazemChart.destroy();
        armazemChart = null;
    }
    
    // Verificar dados
    if (!data || !data.labels || !data.values) {
        console.error('Dados inválidos para gráfico de armazém:', data);
        return;
    }
    
    // Ordenar por valor (maior para menor) - dados já vêm ordenados crescente, então reverter
    const sortedData = data.labels.map((label, index) => ({
        label: label,
        value: data.values[index]
    })).sort((a, b) => b.value - a.value); // Ordem decrescente
    
    const sortedLabels = sortedData.map(item => item.label);
    const sortedValues = sortedData.map(item => item.value);
    
    // Cores para armazéns (tons mais claros e variados)
    const colors = [
        '#60a5fa', '#34d399', '#fbbf24', '#f87171', '#a78bfa',
        '#fb7185', '#4ade80', '#facc15', '#38bdf8', '#c084fc'
    ];
    
    try {
        armazemChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: sortedLabels.map(label => {
                    // Quebrar labels longos em múltiplas linhas
                    if (label.length > 15) {
                        const words = label.split(' ');
                        const lines = [];
                        let currentLine = '';
                        
                        for (const word of words) {
                            if ((currentLine + ' ' + word).length > 15) {
                                if (currentLine) lines.push(currentLine);
                                currentLine = word;
                            } else {
                                currentLine = currentLine ? currentLine + ' ' + word : word;
                            }
                        }
                        if (currentLine) lines.push(currentLine);
                        
                        return lines.slice(0, 2); // Máximo 2 linhas
                    }
                    return label;
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
                    datalabels: {
                        display: true,
                        anchor: 'end',
                        align: 'right',
                        formatter: (value) => value,
                        font: {
                            size: 11,
                            weight: 'bold'
                        },
                        color: '#374151',
                        backgroundColor: 'rgba(255, 255, 255, 0.8)',
                        borderColor: '#d1d5db',
                        borderRadius: 3,
                        borderWidth: 1,
                        padding: 2
                    },
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
                                size: 9
                            },
                            maxRotation: 0,
                            minRotation: 0
                        }
                    }
                }
            },
            plugins: [ChartDataLabels]
        });
        
        console.log('Gráfico de armazém criado com sucesso');
        
    } catch (error) {
        console.error('Erro ao criar gráfico de armazém:', error);
    }
}

// === CRIAÇÃO DE GRÁFICO DE MATERIAL ===
function createMaterialChart(data) {
    console.log('[Chart] Iniciando criação do gráfico de material com dados:', data);
    
    const ctx = document.getElementById('material-chart');
    if (!ctx) {
        console.error('Canvas material-chart não encontrado');
        return;
    }
    
    console.log('[Chart] Canvas material-chart encontrado:', ctx);
    
    // Destruir gráfico existente
    if (materialChart) {
        materialChart.destroy();
        materialChart = null;
    }
    
    // Verificar dados
    if (!data || !data.labels || !data.values) {
        console.error('Dados inválidos para gráfico de material:', data);
        return;
    }
    
    // Ordenar por valor (maior para menor) - dados já vêm ordenados crescente, então reverter
    const sortedData = data.labels.map((label, index) => ({
        label: label,
        value: data.values[index]
    })).sort((a, b) => b.value - a.value); // Ordem decrescente
    
    const sortedLabels = sortedData.map(item => item.label);
    const sortedValues = sortedData.map(item => item.value);
    
    // Cores para materiais (tons mais claros e variados)
    const colors = [
        '#34d399', '#4ade80', '#6ee7b7', '#86efac', '#a7f3d0',
        '#10b981', '#059669', '#047857', '#065f46', '#064e3b'
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
                    datalabels: {
                        display: true,
                        anchor: 'end',
                        align: 'right',
                        formatter: (value) => `R$ ${value.toFixed(1)}M`,
                        font: {
                            size: 11,
                            weight: 'bold'
                        },
                        color: '#374151',
                        backgroundColor: 'rgba(255, 255, 255, 0.8)',
                        borderColor: '#d1d5db',
                        borderRadius: 3,
                        borderWidth: 1,
                        padding: 2
                    },
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
            },
            plugins: [ChartDataLabels]
        });
        
        console.log('Gráfico de material criado com sucesso');
        
    } catch (error) {
        console.error('Erro ao criar gráfico de material:', error);
    }
}

// === INICIALIZAÇÃO ===
async function initializeDashboard() {
    // Evitar múltiplas inicializações
    if (dashboardInitialized) {
        console.log('[Dashboard] Dashboard já inicializado, ignorando nova inicialização');
        return;
    }
    
    dashboardInitialized = true;
    console.log('Inicializando dashboard...');
    
    // Mostrar estado de loading
    showLoadingState();
    
    try {
        // Carregar dados da API diretamente (sem retry infinito)
        const response = await fetch('/api/dashboard-data');
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        if (result.success && result.data) {
            console.log(`[Dashboard] Dados carregados com sucesso (fonte: ${result.source})`);
            hideLoadingState();
            
            const data = result.data;
            
            // Atualizar KPIs
            if (data.kpis) {
                updateKPIs(data.kpis);
            }
            
            // Aguardar um pouco para o DOM atualizar antes de criar gráficos
            setTimeout(() => {
                // Criar gráficos com dados das charts
                if (data.charts) {
                    console.log('[Dashboard] Charts data:', data.charts);
                
                // Gráfico mensal - converter dados das views
                if (data.charts.monthly) {
                    console.log('[Dashboard] Monthly data:', data.charts.monthly);
                    const monthlyData = {
                        months: data.charts.monthly.periods.map(p => {
                            if (!p) return 'N/A';
                            // Converter ISO date para formato legível
                            const date = new Date(p);
                            return date.toLocaleDateString('pt-BR', { month: 'short', year: 'numeric' });
                        }),
                        processes: data.charts.monthly.processes
                    };
                    console.log('[Dashboard] Processed monthly data:', monthlyData);
                    createMonthlyChart(monthlyData);
                }
                
                // Gráfico de canal - já está no formato correto
                if (data.charts.canal) {
                    console.log('[Dashboard] Canal data:', data.charts.canal);
                    createCanalChart(data.charts.canal);
                }
                
                // Gráfico de URF (usando como armazém)
                if (data.charts.urf) {
                    console.log('[Dashboard] URF data:', data.charts.urf);
                    createArmazemChart(data.charts.urf);
                }
                
                // Gráfico de material
                if (data.charts.top_material) {
                    console.log('[Dashboard] Material data:', data.charts.top_material);
                    createMaterialChart(data.charts.top_material);
                }
                }
            }, 100); // Aguardar 100ms para DOM atualizar
            
            // Renderizar tabela
            if (data.recent_operations) {
                renderTable(data);
            }
            
            // Atualizar timestamp
            document.getElementById('last-update').textContent = 
                `Última atualização: ${new Date().toLocaleString('pt-BR')}`;
            
        } else {
            throw new Error(result.error || 'Resposta inválida da API');
        }
        
    } catch (error) {
        console.error('Erro ao carregar dashboard:', error);
        hideLoadingState();
        showErrorState(`Erro ao carregar dados: ${error.message}`);
    }
}

function showErrorState(message) {
    console.log('[Dashboard] Mostrando estado de erro:', message);
    
    // Mostrar erro nos KPIs
    const kpiElements = document.querySelectorAll('.kpi-value');
    kpiElements.forEach(element => {
        element.innerHTML = '⚠️';
        element.style.color = '#dc3545';
    });
    
    // Mostrar erro nos gráficos
    const chartContainers = document.querySelectorAll('.chart-container');
    chartContainers.forEach(container => {
        container.innerHTML = `
            <div class="chart-error">
                <div class="error-icon">⚠️</div>
                <p>${message}</p>
                <button onclick="location.reload()" class="retry-btn">Recarregar Página</button>
            </div>
        `;
    });
    
    // Mostrar erro na tabela
    const tableContainer = document.getElementById('table-container');
    if (tableContainer) {
        tableContainer.innerHTML = `
            <div class="error-state">
                <div class="error-icon">⚠️</div>
                <p>${message}</p>
            </div>
        `;
    }
    
    // Atualizar timestamp com erro
    document.getElementById('last-update').textContent = `Erro: ${message}`;
    document.getElementById('last-update').style.color = '#dc3545';
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
            dashboardInitialized = false; // Reset flag para permitir reinicialização
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
