// Materiais Simple JavaScript

// Global variables
let materiaisCharts = {};
let currentFilters = {};

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
    console.log('[MATERIAIS] Inicializando página de materiais...');
    
    // Initialize modal
    initializeModal();
    
    // Initialize filters
    initializeFilters();
    
    // Load initial data
    loadMateriaisData();
    
    // Load filter options
    loadFilterOptions();
    
    // Initialize event listeners
    initializeEventListeners();
    
    // Hide loading overlay
    hideLoadingOverlay();
});

// Initialize modal functionality
function initializeModal() {
    const modal = document.getElementById('filter-modal');
    const openBtn = document.getElementById('open-filters');
    const closeBtn = document.querySelector('.close');
    const applyBtn = document.getElementById('apply-filters');
    const clearBtn = document.getElementById('clear-filters');
    
    // Open modal
    openBtn.addEventListener('click', function() {
        modal.style.display = 'block';
    });
    
    // Close modal
    closeBtn.addEventListener('click', function() {
        modal.style.display = 'none';
    });
    
    // Close modal when clicking outside
    window.addEventListener('click', function(event) {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    });
    
    // Apply filters
    applyBtn.addEventListener('click', function() {
        applyFilters();
        modal.style.display = 'none';
    });
    
    // Clear filters
    clearBtn.addEventListener('click', function() {
        clearFilters();
    });
}

// Initialize filters
function initializeFilters() {
    // Set default date range (last 30 days)
    const hoje = new Date();
    const trintaDiasAtras = new Date(hoje.getTime() - (30 * 24 * 60 * 60 * 1000));
    
    document.getElementById('data-inicio').value = formatDateForInput(trintaDiasAtras);
    document.getElementById('data-fim').value = formatDateForInput(hoje);
    
    // Quick filter buttons
    document.querySelectorAll('.btn-quick').forEach(button => {
        button.addEventListener('click', function() {
            const period = this.dataset.period;
            setQuickDateFilter(period);
        });
    });
}

// Set quick date filters
function setQuickDateFilter(period) {
    const hoje = new Date();
    const dataInicio = document.getElementById('data-inicio');
    const dataFim = document.getElementById('data-fim');
    
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

// Initialize event listeners
function initializeEventListeners() {
    // Refresh button
    document.getElementById('refresh-chart').addEventListener('click', function() {
        loadMateriaisData();
    });
    
    // Export button
    document.getElementById('export-data').addEventListener('click', function() {
        exportData();
    });
}

// Load materiais data
function loadMateriaisData() {
    console.log('[MATERIAIS] Carregando dados...');
    showLoadingOverlay();
    
    const params = new URLSearchParams(currentFilters);
    
    // Load KPIs
    fetch(`/materiais/materiais_data?${params}`)
        .then(response => response.json())
        .then(data => {
            console.log('[MATERIAIS] KPIs carregados:', data);
            updateKPIs(data);
            updateLastUpdate();
        })
        .catch(error => {
            console.error('[MATERIAIS] Erro ao carregar KPIs:', error);
        });
    
    // Load charts data
    loadChartsData();
    
    // Load table data
    loadTableData();
}

// Update KPIs
function updateKPIs(data) {
    document.getElementById('kpi-total-processos').textContent = formatNumber(data.total_processos || 0);
    document.getElementById('kpi-total-materiais').textContent = formatNumber(data.total_materiais || 0);
    document.getElementById('kpi-valor-total').textContent = formatCurrency(data.valor_total || 0);
    document.getElementById('kpi-custo-total').textContent = formatCurrency(data.custo_total || 0);
    document.getElementById('kpi-ticket-medio').textContent = formatCurrency(data.ticket_medio || 0);
    document.getElementById('kpi-transit-time').textContent = formatNumber(data.transit_time_medio || 0) + ' dias';
}

// Load charts data
function loadChartsData() {
    const params = new URLSearchParams(currentFilters);
    
    // Top Materiais Chart
    fetch(`/materiais/api/top-materiais?${params}`)
        .then(response => response.json())
        .then(data => {
            console.log('[MATERIAIS] Top materiais carregados:', data);
            createTopMateriaisChart(data);
        })
        .catch(error => {
            console.error('[MATERIAIS] Erro ao carregar top materiais:', error);
        });
    
    // Evolução Mensal Chart
    fetch(`/materiais/api/evolucao-mensal?${params}`)
        .then(response => response.json())
        .then(data => {
            console.log('[MATERIAIS] Evolução mensal carregada:', data);
            createEvolucaoMensalChart(data);
        })
        .catch(error => {
            console.error('[MATERIAIS] Erro ao carregar evolução mensal:', error);
        });
    
    // Modal Distribution Chart
    fetch(`/materiais/api/modal-distribution?${params}`)
        .then(response => response.json())
        .then(data => {
            console.log('[MATERIAIS] Distribuição modal carregada:', data);
            createModalChart(data);
        })
        .catch(error => {
            console.error('[MATERIAIS] Erro ao carregar distribuição modal:', error);
        });
    
    // Canal Distribution Chart
    fetch(`/materiais/api/canal-distribution?${params}`)
        .then(response => response.json())
        .then(data => {
            console.log('[MATERIAIS] Distribuição canal carregada:', data);
            createCanalChart(data);
        })
        .catch(error => {
            console.error('[MATERIAIS] Erro ao carregar distribuição canal:', error);
        });
    
    // Transit Time Chart
    fetch(`/materiais/api/transit-time-por-material?${params}`)
        .then(response => response.json())
        .then(data => {
            console.log('[MATERIAIS] Transit time carregado:', data);
            createTransitTimeChart(data);
        })
        .catch(error => {
            console.error('[MATERIAIS] Erro ao carregar transit time:', error);
        });
}

// Load table data
function loadTableData() {
    const params = new URLSearchParams(currentFilters);
    
    // Principais Materiais Table
    fetch(`/materiais/api/principais-materiais?${params}`)
        .then(response => response.json())
        .then(data => {
            console.log('[MATERIAIS] Principais materiais carregados:', data);
            populatePrincipaisMateriaisTable(data);
        })
        .catch(error => {
            console.error('[MATERIAIS] Erro ao carregar principais materiais:', error);
        });
    
    // Detalhamento Table
    fetch(`/materiais/api/detalhamento-processos?${params}`)
        .then(response => response.json())
        .then(data => {
            console.log('[MATERIAIS] Detalhamento carregado:', data);
            populateDetalhamentoTable(data);
        })
        .catch(error => {
            console.error('[MATERIAIS] Erro ao carregar detalhamento:', error);
        });
    
    hideLoadingOverlay();
}

// Create Top Materiais Chart
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
                backgroundColor: 'rgba(52, 152, 219, 0.6)',
                borderColor: 'rgba(52, 152, 219, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true
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

// Create Evolução Mensal Chart
function createEvolucaoMensalChart(data) {
    const ctx = document.getElementById('evolucao-mensal-chart').getContext('2d');
    
    if (materiaisCharts.evolucaoMensal) {
        materiaisCharts.evolucaoMensal.destroy();
    }
    
    // Group data by material
    const materialData = {};
    data.forEach(item => {
        if (!materialData[item.categoria_material]) {
            materialData[item.categoria_material] = {};
        }
        materialData[item.categoria_material][item.mes] = item.qtde;
    });
    
    // Get unique months
    const months = [...new Set(data.map(item => item.mes))].sort();
    
    // Create datasets
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
            borderWidth: 2,
            fill: false
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
                    beginAtZero: true
                }
            }
        }
    });
}

// Create Modal Chart
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
                    '#3498db', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b6'
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
}

// Create Canal Chart
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
                    '#2ecc71', '#e74c3c', '#f39c12', '#9b59b6', '#3498db'
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
}

// Create Transit Time Chart
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
                backgroundColor: 'rgba(231, 76, 60, 0.6)',
                borderColor: 'rgba(231, 76, 60, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true
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

// Populate Principais Materiais Table
function populatePrincipaisMateriaisTable(data) {
    const tbody = document.querySelector('#principais-materiais-table tbody');
    tbody.innerHTML = '';
    
    data.forEach(item => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${item.material}</td>
            <td>${formatNumber(item.qtde_processos)}</td>
            <td>${formatCurrency(item.custo_total)}</td>
            <td>${item.proxima_chegada || 'N/A'}</td>
        `;
        tbody.appendChild(row);
    });
}

// Populate Detalhamento Table
function populateDetalhamentoTable(data) {
    const tbody = document.querySelector('#detalhamento-table tbody');
    tbody.innerHTML = '';
    
    data.slice(0, 100).forEach(item => { // Limit to 100 rows for performance
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
            <td>${formatCurrency(item.custo_total)}</td>
        `;
        tbody.appendChild(row);
    });
}

// Load filter options
function loadFilterOptions() {
    // Load materiais
    fetch('/materiais/filter-options/materiais')
        .then(response => response.json())
        .then(data => {
            const select = document.getElementById('material-filter');
            const dynamicGroup = document.getElementById('materiais-dinamicos');
            
            data.forEach(item => {
                const option = document.createElement('option');
                option.value = item.mercadoria;
                option.textContent = item.mercadoria;
                dynamicGroup.appendChild(option);
            });
        })
        .catch(error => {
            console.error('[MATERIAIS] Erro ao carregar filtros de materiais:', error);
        });
    
    // Load clientes
    fetch('/materiais/filter-options/clientes')
        .then(response => response.json())
        .then(data => {
            const select = document.getElementById('cliente-filter');
            
            data.forEach(item => {
                const option = document.createElement('option');
                option.value = item.importador;
                option.textContent = item.importador;
                select.appendChild(option);
            });
        })
        .catch(error => {
            console.error('[MATERIAIS] Erro ao carregar filtros de clientes:', error);
        });
}

// Apply filters
function applyFilters() {
    currentFilters = {
        data_inicio: document.getElementById('data-inicio').value,
        data_fim: document.getElementById('data-fim').value,
        material: document.getElementById('material-filter').value,
        cliente: document.getElementById('cliente-filter').value,
        modal: document.getElementById('modal-filter').value
    };
    
    // Remove empty filters
    Object.keys(currentFilters).forEach(key => {
        if (!currentFilters[key]) {
            delete currentFilters[key];
        }
    });
    
    console.log('[MATERIAIS] Aplicando filtros:', currentFilters);
    loadMateriaisData();
}

// Clear filters
function clearFilters() {
    document.getElementById('data-inicio').value = '';
    document.getElementById('data-fim').value = '';
    document.getElementById('material-filter').value = '';
    document.getElementById('cliente-filter').value = '';
    document.getElementById('modal-filter').value = '';
    
    currentFilters = {};
    loadMateriaisData();
}

// Export data
function exportData() {
    const params = new URLSearchParams(currentFilters);
    window.open(`/materiais/api/detalhamento-processos?${params}&export=csv`, '_blank');
}

// Utility functions
function formatNumber(value) {
    if (!value) return '0';
    return new Intl.NumberFormat('pt-BR').format(value);
}

function formatCurrency(value) {
    if (!value) return 'R$ 0,00';
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(value);
}

function formatDateForInput(date) {
    return date.toISOString().split('T')[0];
}

function updateLastUpdate() {
    const now = new Date();
    document.getElementById('last-update').textContent = 
        `Última atualização: ${now.toLocaleString('pt-BR')}`;
}

function showLoadingOverlay() {
    document.getElementById('loading-overlay').style.display = 'flex';
}

function hideLoadingOverlay() {
    document.getElementById('loading-overlay').style.display = 'none';
}

// Global refresh function
window.refreshMateriaisData = function() {
    loadMateriaisData();
};
