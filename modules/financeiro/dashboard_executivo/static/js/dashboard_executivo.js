// Dashboard Executivo Financeiro - JavaScript

document.addEventListener('DOMContentLoaded', function() {
    console.log('Dashboard Executivo Financeiro loaded');
    
    // Initialize dashboard
    initializeDashboard();
    
    // Set up event listeners
    setupEventListeners();
    
    // Load initial data
    loadData();
});

function initializeDashboard() {
    console.log('Initializing dashboard...');
    
    // Set up current year as default
    const currentYear = new Date().getFullYear();
    document.getElementById('year-filter').value = currentYear;
    
    // Initialize charts
    initializeCharts();
}

function setupEventListeners() {
    console.log('Setting up event listeners...');
    
    // Year filter change
    const yearFilter = document.getElementById('year-filter');
    if (yearFilter) {
        yearFilter.addEventListener('change', function() {
            loadData();
        });
    }
    
    // Refresh button
    const refreshButton = document.getElementById('refresh-data');
    if (refreshButton) {
        refreshButton.addEventListener('click', function() {
            loadData();
        });
    }
    
    // KPI card click handlers
    setupKPICardClickHandlers();
}

function setupKPICardClickHandlers() {
    // Resultado card - navigate to Fluxo de Caixa page
    const resultadoCard = document.getElementById('kpi-resultado');
    if (resultadoCard) {
        resultadoCard.addEventListener('click', function() {
            window.location.href = '/financeiro/fluxo-de-caixa';
        });
    }
    
    // Faturamento card - navigate to Faturamento page
    const faturamentoCard = document.getElementById('kpi-faturamento');
    if (faturamentoCard) {
        faturamentoCard.addEventListener('click', function() {
            window.location.href = '/financeiro/faturamento';
        });
    }
    
    // Despesas card - navigate to Despesas page
    const despesasCard = document.getElementById('kpi-despesas');
    if (despesasCard) {
        despesasCard.addEventListener('click', function() {
            window.location.href = '/financeiro/despesas';
        });
    }
    
    // Saldo Acumulado card - navigate to Fluxo de Caixa page
    const saldoAcumuladoCard = document.getElementById('kpi-saldo-acumulado');
    if (saldoAcumuladoCard) {
        saldoAcumuladoCard.addEventListener('click', function() {
            window.location.href = '/financeiro/fluxo-de-caixa';
        });
    }
}

function loadData() {
    console.log('Loading data...');
    showLoading();
    
    const year = document.getElementById('year-filter').value;
    
    // Load all data in parallel
    Promise.all([
        loadKPIs(year),
        loadMetaAtingimento(year),
        loadResultadoMensal(year),
        loadSaldoAcumulado(year),
        loadFaturamentoPorSetor(year),
        loadTopDespesas(year),
        loadTopClientes(year)
    ]).then(() => {
        hideLoading();
        console.log('All data loaded successfully');
    }).catch(error => {
        console.error('Error loading data:', error);
        hideLoading();
        showError('Erro ao carregar dados. Por favor, tente novamente.');
    });
}

function loadKPIs(year) {
    console.log(`Loading KPIs for year: ${year}`);
    
    return fetch(`/financeiro/dashboard-executivo/api/kpis?ano=${year}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateKPIs(data.data);
            } else {
                throw new Error(data.error || 'Erro ao carregar KPIs');
            }
        });
}

function loadMetaAtingimento(year) {
    console.log(`Loading meta atingimento for year: ${year}`);
    
    return fetch(`/financeiro/dashboard-executivo/api/meta-atingimento?ano=${year}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateMetaProgressoKPI(data.data);
            } else {
                throw new Error(data.error || 'Erro ao carregar meta de atingimento');
            }
        });
}

function loadResultadoMensal(year) {
    console.log(`Loading resultado mensal for year: ${year}`);
    
    return fetch(`/financeiro/dashboard-executivo/api/resultado-mensal?ano=${year}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateResultadoMensalChart(data.data);
            } else {
                throw new Error(data.error || 'Erro ao carregar resultado mensal');
            }
        });
}

function loadSaldoAcumulado(year) {
    console.log(`Loading saldo acumulado for year: ${year}`);
    
    return fetch(`/financeiro/dashboard-executivo/api/saldo-acumulado?ano=${year}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateSaldoAcumuladoChart(data.data);
            } else {
                throw new Error(data.error || 'Erro ao carregar saldo acumulado');
            }
        });
}

function loadFaturamentoPorSetor(year) {
    console.log(`Loading faturamento por setor for year: ${year}`);
    
    return fetch(`/financeiro/dashboard-executivo/api/faturamento-setor?ano=${year}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateFaturamentoPorSetorChart(data.data);
            } else {
                throw new Error(data.error || 'Erro ao carregar faturamento por setor');
            }
        });
}

function loadTopDespesas(year) {
    console.log(`Loading top despesas for year: ${year}`);
    
    return fetch(`/financeiro/dashboard-executivo/api/top-despesas?ano=${year}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateTopDespesasChart(data.data);
            } else {
                throw new Error(data.error || 'Erro ao carregar top despesas');
            }
        });
}

function loadTopClientes(year) {
    console.log(`Loading top clientes for year: ${year}`);
    
    return fetch(`/financeiro/dashboard-executivo/api/top-clientes?ano=${year}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateTopClientes(data.data);
            } else {
                throw new Error(data.error || 'Erro ao carregar top clientes');
            }
        });
}

function updateKPIs(data) {
    console.log('Updating KPIs:', data);
    
    // Resultado Líquido
    updateKPIValue('valor-resultado', data.resultado_liquido, data.resultado_variacao);
    
    // Faturamento Total
    updateKPIValue('valor-faturamento', data.faturamento_total, data.faturamento_variacao);
    
    // Despesas Totais
    updateKPIValue('valor-despesas', data.despesas_total, data.despesas_variacao);
    
    // Margem Líquida
    updateKPIValue('valor-margem-liquida', data.margem_liquida, data.margem_variacao);
}

function updateMetaProgressoKPI(data) {
    console.log('Updating meta progresso KPI:', data);
    
    // Progresso da Meta Anual
    updateKPIValue('valor-meta-progresso', data.percentual, null);
    
    // Update variation text to show actual values
    const variationElement = document.getElementById('var-meta-progresso');
    if (variationElement) {
        variationElement.textContent = `${formatCompactNumber(data.realizado)} / ${formatCompactNumber(data.meta)}`;
        variationElement.className = 'kpi-variation';
    }
}

function updateResultadoMensalChart(data) {
    console.log('Updating resultado mensal chart:', data);
    
    const ctx = document.getElementById('chart-resultado-mensal').getContext('2d');
    
    // Destroy existing chart if it exists
    if (window.resultadoMensalChart) {
        window.resultadoMensalChart.destroy();
    }
    
    // Prepare data
    const labels = data.map(item => getMonthName(item.mes.split('-')[1]));
    const receitas = data.map(item => item.receitas);
    const despesas = data.map(item => item.despesas);
    const resultados = data.map(item => item.resultado);
    
    window.resultadoMensalChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Receitas',
                    data: receitas,
                    backgroundColor: 'rgba(25, 135, 84, 0.7)',
                    borderColor: 'rgba(25, 135, 84, 1)',
                    borderWidth: 1
                },
                {
                    label: 'Despesas',
                    data: despesas,
                    backgroundColor: 'rgba(220, 53, 69, 0.7)',
                    borderColor: 'rgba(220, 53, 69, 1)',
                    borderWidth: 1
                },
                {
                    label: 'Resultado',
                    data: resultados,
                    backgroundColor: 'rgba(13, 110, 253, 0.7)',
                    borderColor: 'rgba(13, 110, 253, 1)',
                    borderWidth: 1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                },
                title: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return 'R$ ' + formatCompactNumber(value);
                        }
                    }
                }
            }
        }
    });
}

function updateSaldoAcumuladoChart(data) {
    console.log('Updating saldo acumulado chart:', data);
    
    const ctx = document.getElementById('chart-saldo-acumulado').getContext('2d');
    
    // Destroy existing chart if it exists
    if (window.saldoAcumuladoChart) {
        window.saldoAcumuladoChart.destroy();
    }
    
    // Prepare data
    const labels = data.map(item => getMonthName(item.mes.split('-')[1]));
    const saldos = data.map(item => item.saldo_acumulado);
    
    window.saldoAcumuladoChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Saldo Acumulado',
                    data: saldos,
                    backgroundColor: 'rgba(13, 202, 240, 0.2)',
                    borderColor: 'rgba(13, 202, 240, 1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                },
                title: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: false,
                    ticks: {
                        callback: function(value) {
                            return 'R$ ' + formatCompactNumber(value);
                        }
                    }
                }
            }
        }
    });
    
    // Update KPI with final saldo acumulado value
    if (data.length > 0) {
        const finalSaldo = data[data.length - 1].saldo_acumulado;
        updateKPIValue('valor-saldo-acumulado', finalSaldo, null);
    }
}

function updateFaturamentoPorSetorChart(data) {
    console.log('Updating faturamento por setor chart:', data);
    
    const ctx = document.getElementById('chart-faturamento-setor').getContext('2d');
    
    // Destroy existing chart if it exists
    if (window.faturamentoSetorChart) {
        window.faturamentoSetorChart.destroy();
    }
    
    // Prepare data
    const labels = ['Importação', 'Consultoria', 'Exportação'];
    const values = [data.importacao.valor, data.consultoria.valor, data.exportacao.valor];
    const backgroundColors = [
        'rgba(25, 135, 84, 0.7)',
        'rgba(13, 110, 253, 0.7)',
        'rgba(255, 193, 7, 0.7)'
    ];
    
    window.faturamentoSetorChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [
                {
                    data: values,
                    backgroundColor: backgroundColors,
                    borderWidth: 1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        boxWidth: 12,
                        padding: 10
                    }
                },
                title: {
                    display: false
                }
            },
            aspectRatio: 1.5
        }
    });
}

function updateTopDespesasChart(data) {
    console.log('Updating top despesas chart:', data);
    
    const ctx = document.getElementById('chart-top-despesas').getContext('2d');
    
    // Destroy existing chart if it exists
    if (window.topDespesasChart) {
        window.topDespesasChart.destroy();
    }
    
    // Prepare data
    const labels = data.map(item => item.categoria);
    const values = data.map(item => item.total);
    
    window.topDespesasChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Valor',
                    data: values,
                    backgroundColor: 'rgba(220, 53, 69, 0.7)',
                    borderColor: 'rgba(220, 53, 69, 1)',
                    borderWidth: 1
                }
            ]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                title: {
                    display: false
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return 'R$ ' + formatCompactNumber(value);
                        }
                    }
                }
            }
        }
    });
}

function updateTopClientes(data) {
    console.log('Updating top clientes:', data);
    
    // Update the clientes table
    const tableBody = document.querySelector('#table-clientes tbody');
    if (tableBody) {
        tableBody.innerHTML = '';
        
        if (data.length === 0) {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td colspan="4" class="text-center text-muted">Nenhum cliente encontrado</td>
            `;
            tableBody.appendChild(row);
            return;
        }
        
        data.forEach((cliente, index) => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td class="text-center">${index + 1}</td>
                <td>${cliente.cliente}</td>
                <td>R$ ${formatCompactNumber(cliente.total_faturado)}</td>
                <td class="text-right">${cliente.percentual.toFixed(2)}%</td>
            `;
            tableBody.appendChild(row);
        });
    }
}

function initializeCharts() {
    console.log('Initializing charts...');
    // Chart initialization is done when data is loaded
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
}

function showError(message) {
    // In a real implementation, you would show an error notification
    console.error('Dashboard error:', message);
    alert(message);
}

function formatCurrency(value) {
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(value);
}

function formatNumber(value) {
    return new Intl.NumberFormat('pt-BR', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(value);
}

// Add this helper function for text alignment
function formatCompactNumber(value) {
    // Convert to number if it's a string
    const num = typeof value === 'string' ? parseFloat(value) : value;
    
    // Handle invalid numbers
    if (isNaN(num)) return '0,00';
    
    // Format with appropriate suffix
    if (Math.abs(num) >= 1000000) {
        // Millions
        return (num / 1000000).toLocaleString('pt-BR', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }) + 'M';
    } else if (Math.abs(num) >= 1000) {
        // Thousands
        return (num / 1000).toLocaleString('pt-BR', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }) + 'K';
    } else {
        // Less than 1000, format normally with 2 decimals
        return num.toLocaleString('pt-BR', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }
}

function updateKPIValue(elementId, value, variation) {
    const valueElement = document.getElementById(elementId);
    const variationElement = document.getElementById(elementId.replace('valor-', 'var-'));
    
    if (valueElement) {
        valueElement.textContent = formatCompactNumber(value);
    }
    
    if (variationElement) {
        if (variation !== null) {
            const variationText = `${variation >= 0 ? '+' : ''}${variation.toFixed(2)}%`;
            variationElement.textContent = variationText;
            variationElement.className = 'kpi-variation ' + (variation > 0 ? 'positive' : variation < 0 ? 'negative' : '');
        } else {
            variationElement.textContent = '';
            variationElement.className = 'kpi-variation';
        }
    }
}

function getMonthName(monthNumber) {
    const months = [
        'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
        'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'
    ];
    return months[parseInt(monthNumber) - 1] || monthNumber;
}