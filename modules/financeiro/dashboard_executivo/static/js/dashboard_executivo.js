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
    
    // Resultado card - navigate to Fluxo de Caixa page
    const resultadoCard = document.getElementById('kpi-resultado');
    if (resultadoCard) {
        resultadoCard.addEventListener('click', function() {
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
                updateMetaAtingimento(data.data);
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
                updateResultadoMensal(data.data);
            } else {
                throw new Error(data.error || 'Erro ao carregar resultado mensal');
            }
        });
}

function loadFaturamentoPorSetor(year) {
    console.log(`Loading faturamento por setor for year: ${year}`);
    
    return fetch(`/financeiro/dashboard-executivo/api/faturamento-setor?ano=${year}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateFaturamentoPorSetor(data.data);
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
                updateTopDespesas(data.data);
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
    
    // Faturamento Total
    updateKPIValue('valor-faturamento', data.faturamento_total, data.faturamento_variacao);
    
    // Despesas Totais
    updateKPIValue('valor-despesas', data.despesas_total, data.despesas_variacao);
    
    // Resultado Líquido
    updateKPIValue('valor-resultado', data.resultado_liquido, data.resultado_variacao);
    
    // Margem Líquida
    updateKPIValue('valor-margem', data.margem_liquida, data.margem_variacao);
}

function updateMetaAtingimento(data) {
    console.log('Updating meta atingimento:', data);
    
    // This would update a gauge or progress chart
    // For now, we'll just log it
    console.log(`Meta: ${data.meta}, Realizado: ${data.realizado}, Percentual: ${data.percentual}%`);
}

function updateResultadoMensal(data) {
    console.log('Updating resultado mensal:', data);
    
    // This would update a bar/line chart
    // For now, we'll just log it
    console.log('Resultado mensal data:', data);
}

function updateFaturamentoPorSetor(data) {
    console.log('Updating faturamento por setor:', data);
    
    // This would update a donut chart
    // For now, we'll just log it
    console.log('Faturamento por setor data:', data);
}

function updateTopDespesas(data) {
    console.log('Updating top despesas:', data);
    
    // This would update a horizontal bar chart
    // For now, we'll just log it
    console.log('Top despesas data:', data);
}

function updateTopClientes(data) {
    console.log('Updating top clientes:', data);
    
    // Update the clientes table
    const tableBody = document.querySelector('#table-clientes tbody');
    if (tableBody) {
        tableBody.innerHTML = '';
        
        data.forEach((cliente, index) => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${index + 1}</td>
                <td>${cliente.cliente}</td>
                <td>R$ ${formatCompactNumber(cliente.total_faturado)}</td>
                <td>${cliente.percentual.toFixed(2)}%</td>
            `;
            tableBody.appendChild(row);
        });
    }
}

function initializeCharts() {
    console.log('Initializing charts...');
    // Chart initialization would go here
    // For now, we'll just log it
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
        const variationText = variation !== null ? `${variation >= 0 ? '+' : ''}${variation.toFixed(2)}%` : '-';
        variationElement.textContent = variationText;
        variationElement.className = 'kpi-variation ' + (variation > 0 ? 'positive' : variation < 0 ? 'negative' : '');
    }
}
