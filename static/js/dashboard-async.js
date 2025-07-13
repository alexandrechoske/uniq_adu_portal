/**
 * Dashboard Async Loading with Chart.js Integration
 * Carregamento assíncrono de dados do dashboard para melhor performance
 */

class DashboardAsync {
    constructor() {
        this.currentPeriod = '30'; // Período padrão: 30 dias
        this.currentCompany = null;
        this.isLoading = false;
        this.charts = {}; // Armazenar instâncias dos gráficos
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.initializeCharts();
        this.loadInitialData();
    }

    setupEventListeners() {
        // Filtro de período
        const periodFilter = document.getElementById('period-filter');
        if (periodFilter) {
            periodFilter.addEventListener('change', (e) => {
                this.currentPeriod = e.target.value;
                this.loadData();
            });
        }

        // Filtro de empresa
        const companyFilter = document.getElementById('company-filter');
        if (companyFilter) {
            companyFilter.addEventListener('change', (e) => {
                this.currentCompany = e.target.value || null;
                this.loadData();
            });
        }

        // Botão de refresh
        const refreshBtn = document.getElementById('refresh-data');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.loadData(true); // Force refresh
            });
        }
    }

    initializeCharts() {
        // Aguardar Chart.js estar disponível
        if (typeof Chart === 'undefined') {
            setTimeout(() => this.initializeCharts(), 100);
            return;
        }

        // Inicializar gráficos vazios
        this.createMonthlyChart();
        this.createChannelChart();
        this.createWarehouseChart();
        this.createMaterialChart();
    }

    createMonthlyChart() {
        const ctx = document.getElementById('monthly-chart');
        if (!ctx) return;

        this.charts.monthly = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Processos',
                    data: [],
                    borderColor: 'rgb(59, 130, 246)',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    tension: 0.1,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    datalabels: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    }
                }
            }
        });
    }

    createChannelChart() {
        const ctx = document.getElementById('canal-chart');
        if (!ctx) return;

        this.charts.channel = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    backgroundColor: [
                        'rgb(239, 68, 68)',   // Vermelho
                        'rgb(34, 197, 94)',   // Verde
                        'rgb(59, 130, 246)',  // Azul
                        'rgb(168, 85, 247)',  // Roxo
                        'rgb(245, 158, 11)'   // Amarelo
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
                        position: 'bottom',
                        labels: {
                            padding: 15,
                            usePointStyle: true
                        }
                    },
                    datalabels: {
                        color: '#fff',
                        font: {
                            weight: 'bold'
                        },
                        formatter: (value, ctx) => {
                            const sum = ctx.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / sum) * 100).toFixed(1);
                            return percentage + '%';
                        }
                    }
                }
            }
        });
    }

    createWarehouseChart() {
        const ctx = document.getElementById('armazem-chart');
        if (!ctx) return;

        this.charts.warehouse = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: [],
                datasets: [{
                    label: 'Processos',
                    data: [],
                    backgroundColor: 'rgba(59, 130, 246, 0.8)',
                    borderColor: 'rgb(59, 130, 246)',
                    borderWidth: 1
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    datalabels: {
                        anchor: 'end',
                        align: 'right',
                        color: '#374151',
                        font: {
                            weight: 'bold'
                        }
                    }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    }
                }
            }
        });
    }

    createMaterialChart() {
        const ctx = document.getElementById('material-chart');
        if (!ctx) return;

        this.charts.material = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: [],
                datasets: [{
                    label: 'Processos',
                    data: [],
                    backgroundColor: 'rgba(34, 197, 94, 0.8)',
                    borderColor: 'rgb(34, 197, 94)',
                    borderWidth: 1
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    datalabels: {
                        anchor: 'end',
                        align: 'right',
                        color: '#374151',
                        font: {
                            weight: 'bold'
                        }
                    }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    }
                }
            }
        });
    }

    loadInitialData() {
        // Mostrar loading inicial
        this.showLoadingState();
        
        // Carregar dados padrão (30 dias)
        this.loadData();
    }

    async loadData(forceRefresh = false) {
        if (this.isLoading && !forceRefresh) return;
        
        this.isLoading = true;
        this.showLoadingState();

        try {
            const params = new URLSearchParams();
            params.append('periodo', this.currentPeriod);
            params.append('charts_only', 'false'); // Incluir dados dos gráficos
            
            if (this.currentCompany) {
                params.append('empresa', this.currentCompany);
            }

            console.log(`[DASHBOARD] Carregando dados: período=${this.currentPeriod}, empresa=${this.currentCompany || 'todas'}`);

            const response = await fetch(`/api/dashboard-data?${params.toString()}`);
            const result = await response.json();

            if (result.success) {
                this.updateUI(result.data);
                this.updateCharts(result.data.charts || {});
                this.showSuccessMessage(`Dados carregados: ${result.data.record_count} registros (${result.data.periodo_info})`);
            } else {
                this.showErrorMessage(`Erro ao carregar dados: ${result.error}`);
            }

        } catch (error) {
            console.error('[DASHBOARD] Erro na requisição:', error);
            this.showErrorMessage('Erro de conexão. Tente novamente.');
        } finally {
            this.isLoading = false;
            this.hideLoadingState();
        }
    }

    updateUI(data) {
        // Atualizar KPIs
        this.updateKPIs(data.kpis);
        
        // Atualizar análise de materiais
        this.updateMaterialAnalysis(data.material_analysis);
        
        // Atualizar tabela
        this.updateTable(data.table_data);
        
        // Atualizar info do período
        this.updatePeriodInfo(data.periodo_info, data.record_count);
        
        // Atualizar timestamp
        this.updateLastUpdate(data.last_update);
    }

    updateCharts(chartsData) {
        if (!chartsData) return;

        // Atualizar gráfico mensal
        if (chartsData.monthly && this.charts.monthly) {
            this.charts.monthly.data.labels = chartsData.monthly.labels || [];
            this.charts.monthly.data.datasets[0].data = chartsData.monthly.data || [];
            this.charts.monthly.update();
        }

        // Atualizar gráfico de canais
        if (chartsData.channel && this.charts.channel) {
            this.charts.channel.data.labels = chartsData.channel.labels || [];
            this.charts.channel.data.datasets[0].data = chartsData.channel.data || [];
            this.charts.channel.update();
        }

        // Atualizar gráfico de armazéns
        if (chartsData.warehouse && this.charts.warehouse) {
            this.charts.warehouse.data.labels = chartsData.warehouse.labels || [];
            this.charts.warehouse.data.datasets[0].data = chartsData.warehouse.data || [];
            this.charts.warehouse.update();
        }

        // Atualizar gráfico de materiais
        if (chartsData.material && this.charts.material) {
            this.charts.material.data.labels = chartsData.material.labels || [];
            this.charts.material.data.datasets[0].data = chartsData.material.data || [];
            this.charts.material.update();
        }

        console.log('[DASHBOARD] Gráficos atualizados com sucesso');
    }

    updateKPIs(kpis) {
        // Totais
        this.updateElement('#total-processos', kpis.total || 0);
        
        // Modais
        this.updateElement('#total-aereo', kpis.aereo || 0);
        this.updateElement('#total-terrestre', kpis.terrestre || 0);
        this.updateElement('#total-maritimo', kpis.maritimo || 0);
        
        // Status
        this.updateElement('#aguardando-embarque', kpis.aguardando_embarque || 0);
        this.updateElement('#aguardando-chegada', kpis.aguardando_chegada || 0);
        this.updateElement('#di-registrada', kpis.di_registrada || 0);
        
        // Valores
        this.updateElement('#vmcv-total', kpis.valor_total_formatted || 'R$ 0');
        this.updateElement('#vmcv-medio', kpis.valor_medio_processo_formatted || 'R$ 0');
        this.updateElement('#despesas-total', kpis.despesas_total_formatted || 'R$ 0');
        this.updateElement('#despesas-medio', kpis.despesa_media_processo_formatted || 'R$ 0');
    }

    updateMaterialAnalysis(materials) {
        const container = document.getElementById('material-analysis-container');
        if (!container) return;

        if (!materials || materials.length === 0) {
            container.innerHTML = '<div class="text-center text-muted">Nenhum material encontrado</div>';
            return;
        }

        let html = '<div class="row">';
        materials.forEach((material, index) => {
            if (index < 6) { // Mostrar apenas top 6
                html += `
                    <div class="col-md-6 col-lg-4 mb-3">
                        <div class="card h-100">
                            <div class="card-body">
                                <h6 class="card-title text-truncate" title="${material.material}">
                                    ${material.material}
                                </h6>
                                <div class="d-flex justify-content-between align-items-center">
                                    <span class="text-primary">${material.quantidade} processos</span>
                                    <span class="badge bg-success">${material.percentual}%</span>
                                </div>
                                <div class="mt-2">
                                    <strong class="text-success">${material.valor_total_formatado}</strong>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            }
        });
        html += '</div>';
        
        container.innerHTML = html;
    }

    updateTable(tableData) {
        const tbody = document.querySelector('#dashboard-table tbody');
        if (!tbody) return;

        if (!tableData || tableData.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">Nenhum registro encontrado</td></tr>';
            return;
        }

        let html = '';
        tableData.forEach(row => {
            html += `
                <tr>
                    <td class="text-truncate" style="max-width: 200px;" title="${row.importador}">
                        ${row.importador}
                    </td>
                    <td>
                        <span class="badge ${this.getModalBadgeClass(row.modal)}">${row.modal || 'N/A'}</span>
                    </td>
                    <td class="text-truncate" style="max-width: 150px;" title="${row.urf_entrada}">
                        ${row.urf_entrada || 'N/A'}
                    </td>
                    <td>
                        <small class="text-muted">${row.status_processo || 'N/A'}</small>
                    </td>
                    <td class="text-truncate" style="max-width: 180px;" title="${row.mercadoria}">
                        ${row.mercadoria || 'N/A'}
                    </td>
                    <td class="text-end">
                        <strong class="text-success">${row.valor_cif_formatted}</strong>
                    </td>
                </tr>
            `;
        });
        
        tbody.innerHTML = html;
    }

    getModalBadgeClass(modal) {
        switch(modal) {
            case 'AÉREA': return 'bg-primary';
            case 'MARÍTIMA': return 'bg-info';
            case 'RODOVIÁRIA': return 'bg-warning';
            default: return 'bg-secondary';
        }
    }

    updatePeriodInfo(periodInfo, recordCount) {
        const element = document.getElementById('period-info');
        if (element) {
            element.textContent = `${periodInfo} • ${recordCount} registros`;
        }
    }

    updateLastUpdate(lastUpdate) {
        const element = document.getElementById('last-update');
        if (element) {
            element.textContent = `Última atualização: ${lastUpdate}`;
        }
    }

    updateElement(selector, value) {
        const element = document.querySelector(selector);
        if (element) {
            if (typeof value === 'number') {
                element.textContent = value.toLocaleString('pt-BR');
            } else {
                element.textContent = value;
            }
        }
    }

    showLoadingState() {
        // Mostrar spinners
        document.querySelectorAll('.loading-spinner').forEach(el => {
            el.style.display = 'inline-block';
        });
        
        // Desabilitar controles
        document.querySelectorAll('#period-filter, #company-filter, #refresh-data').forEach(el => {
            el.disabled = true;
        });
        
        // Mostrar overlay de loading se existir
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.style.display = 'flex';
        }

        // Mostrar loading nos gráficos
        this.showChartsLoading();
    }

    showChartsLoading() {
        // Adicionar efeito de loading nos containers dos gráficos
        const chartContainers = document.querySelectorAll('.chart-container');
        chartContainers.forEach(container => {
            container.classList.add('loading');
        });
    }

    hideLoadingState() {
        // Ocultar spinners
        document.querySelectorAll('.loading-spinner').forEach(el => {
            el.style.display = 'none';
        });
        
        // Habilitar controles
        document.querySelectorAll('#period-filter, #company-filter, #refresh-data').forEach(el => {
            el.disabled = false;
        });
        
        // Ocultar overlay de loading
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.style.display = 'none';
        }

        // Remover loading dos gráficos
        this.hideChartsLoading();
    }

    hideChartsLoading() {
        // Remover efeito de loading dos containers dos gráficos
        const chartContainers = document.querySelectorAll('.chart-container');
        chartContainers.forEach(container => {
            container.classList.remove('loading');
        });
    }

    showSuccessMessage(message) {
        this.showMessage(message, 'success');
    }

    showErrorMessage(message) {
        this.showMessage(message, 'danger');
    }

    showMessage(message, type = 'info') {
        // Criar toast ou alert
        const alertContainer = document.getElementById('alert-container');
        if (alertContainer) {
            const alert = document.createElement('div');
            alert.className = `alert alert-${type} alert-dismissible fade show`;
            alert.innerHTML = `
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            alertContainer.appendChild(alert);
            
            // Auto-remove após 5 segundos
            setTimeout(() => {
                if (alert.parentNode) {
                    alert.parentNode.removeChild(alert);
                }
            }, 5000);
        } else {
            console.log(`[DASHBOARD] ${type.toUpperCase()}: ${message}`);
        }
    }
}

// Inicializar quando o DOM estiver carregado
document.addEventListener('DOMContentLoaded', function() {
    // Verificar se deve usar carregamento assíncrono
    const container = document.querySelector('.dashboard-container');
    if (container && container.dataset.asyncLoading === 'true') {
        window.dashboardAsync = new DashboardAsync();
    }
});
