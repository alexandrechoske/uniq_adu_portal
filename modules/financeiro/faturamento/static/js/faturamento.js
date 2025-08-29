/**
 * Faturamento - JavaScript
 * Sistema de análise de faturamento com gráficos e KPIs
 */

class FaturamentoController {
    constructor() {
        this.currentAno = new Date().getFullYear();
        this.currentSetor = 'importacao';
        this.activeTab = 'visao-geral';
        
        // Armazenar instâncias dos gráficos
        this.charts = {};
        
        // Configurações padrão do Chart.js
        this.chartDefaults = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 20,
                        usePointStyle: true,
                        font: {
                            size: 12
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: 'white',
                    bodyColor: 'white',
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    borderWidth: 1,
                    cornerRadius: 8,
                    displayColors: true,
                    callbacks: {
                        label: function(context) {
                            let value = context.parsed.y || context.parsed;
                            return context.dataset.label + ': ' + formatCurrency(value);
                        }
                    }
                }
            },
            scales: {
                y: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        callback: function(value) {
                            return formatCurrencyShort(value);
                        }
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            }
        };
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.loadData();
    }
    
    setupEventListeners() {
        // Tab navigation
        $('.tab-button').on('click', (e) => {
            const tab = $(e.target).data('tab');
            this.switchTab(tab);
        });
        
        // Filtros
        $('#open-filters').on('click', () => this.openFiltersModal());
        $('#close-modal').on('click', () => this.closeFiltersModal());
        $('#apply-filters').on('click', () => this.applyFilters());
        $('#clear-filters').on('click', () => this.resetFilters());
        
        // Setor filter
        $('#setor-select').on('change', (e) => {
            this.currentSetor = e.target.value;
            const setorNames = {
                'importacao': 'Importação',
                'consultoria': 'Consultoria',
                'exportacao': 'Exportação'
            };
            $('#setor-filter-summary-text').text(`Vendo dados do setor de ${setorNames[this.currentSetor]}`);
            this.loadSetorData();
        });
        
        // Fechar modal ao clicar fora
        $('#filter-modal').on('click', (e) => {
            if (e.target.id === 'filter-modal') {
                this.closeFiltersModal();
            }
        });
    }
    
    switchTab(tab) {
        // Update active tab buttons
        $('.tab-button').removeClass('active');
        $(`.tab-button[data-tab="${tab}"]`).addClass('active');
        
        // Update active tab content
        $('.tab-content').removeClass('active');
        $(`#${tab}-tab`).addClass('active');
        
        this.activeTab = tab;
        this.loadData();
    }
    
    async loadData() {
        this.showLoading(true);
        
        try {
            if (this.activeTab === 'visao-geral') {
                await Promise.all([
                    this.loadGeralKPIs(),
                    this.loadGeralMensal(),
                    this.loadGeralProporcao()
                ]);
            } else if (this.activeTab === 'analise-setor') {
                await this.loadSetorData();
            }
        } catch (error) {
            console.error('Erro ao carregar dados:', error);
            this.showError('Erro ao carregar dados. Tente novamente.');
        } finally {
            this.showLoading(false);
        }
    }
    
    async loadGeralKPIs() {
        try {
            const response = await fetch(`/financeiro/faturamento/api/geral/kpis?ano=${this.currentAno}`);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Erro ao carregar KPIs');
            }
            
            this.updateGeralKPIs(data);
        } catch (error) {
            console.error('Erro ao carregar KPIs gerais:', error);
        }
    }
    
    updateGeralKPIs(data) {
        // Total Faturado
        $('#valor-total-faturado').text(formatCurrencyShort(data.total_faturado));
        
        // Meta Anual
        $('#valor-meta-anual').text(formatCurrencyShort(data.meta_anual));
        
        // Target Realizado
        $('#valor-target-realizado').text(formatCurrencyShort(data.target_realizado));
        
        // Target a Realizar
        $('#valor-target-a-realizar').text(formatCurrencyShort(data.target_a_realizar));
    }
    
    async loadGeralMensal() {
        try {
            const response = await fetch(`/financeiro/faturamento/api/geral/mensal?ano=${this.currentAno}`);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Erro ao carregar dados mensais');
            }
            
            this.renderTabelaMensal(data);
        } catch (error) {
            console.error('Erro ao carregar tabela mensal:', error);
        }
    }
    
    renderTabelaMensal(data) {
        const tbody = $('#tabela-faturamento-mensal tbody');
        tbody.empty();
        
        const monthNames = [
            'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
            'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
        ];
        
        data.forEach(row => {
            const variacaoClass = row.variacao > 0 ? 'text-success' : row.variacao < 0 ? 'text-danger' : '';
            const variacaoIcon = row.variacao > 0 ? 'mdi mdi-trending-up' : row.variacao < 0 ? 'mdi mdi-trending-down' : 'mdi mdi-minus';
            
            tbody.append(`
                <tr>
                    <td>${row.ano}</td>
                    <td>${monthNames[row.mes - 1]}</td>
                    <td class="fw-bold">${formatCurrency(row.faturamento_total)}</td>
                    <td>${formatCurrency(row.faturamento_anterior)}</td>
                    <td class="${variacaoClass}">
                        <i class="${variacaoIcon}"></i>
                        ${row.variacao.toFixed(1)}%
                    </td>
                </tr>
            `);
        });
    }
    
    async loadGeralProporcao() {
        try {
            const response = await fetch(`/financeiro/faturamento/api/geral/proporcao?ano=${this.currentAno}`);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Erro ao carregar dados de proporção');
            }
            
            this.renderProporcaoCharts(data);
        } catch (error) {
            console.error('Erro ao carregar gráficos de proporção:', error);
        }
    }
    
    renderProporcaoCharts(data) {
        // Gráfico de Proporção do Faturamento
        const proporcaoCtx = document.getElementById('chart-proporcao-faturamento').getContext('2d');
        
        // Destruir gráfico anterior se existir
        if (this.charts.proporcao) {
            this.charts.proporcao.destroy();
        }
        
        this.charts.proporcao = new Chart(proporcaoCtx, {
            type: 'doughnut',
            data: {
                labels: ['Importação', 'Consultoria', 'Exportação'],
                datasets: [{
                    data: [
                        data.setores.importacao.percentual,
                        data.setores.consultoria.percentual,
                        data.setores.exportacao.percentual
                    ],
                    backgroundColor: [
                        '#007bff',
                        '#28a745',
                        '#ffc107'
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
                            padding: 20,
                            usePointStyle: true
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.parsed;
                                return `${label}: ${value.toFixed(1)}%`;
                            }
                        }
                    }
                }
            }
        });
        
        // Gráfico de Meta Anual - Faturado vs A Realizar
        const metaCtx = document.getElementById('chart-meta-realizacao').getContext('2d');
        
        // Destruir gráfico anterior se existir
        if (this.charts.meta) {
            this.charts.meta.destroy();
        }
        
        this.charts.meta = new Chart(metaCtx, {
            type: 'doughnut',
            data: {
                labels: ['Faturado', 'A Realizar'],
                datasets: [{
                    data: [
                        data.meta.faturado.percentual,
                        data.meta.a_realizar.percentual
                    ],
                    backgroundColor: [
                        '#28a745',
                        '#dc3545'
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
                            padding: 20,
                            usePointStyle: true
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.parsed;
                                return `${label}: ${value.toFixed(1)}%`;
                            }
                        }
                    }
                }
            }
        });
    }
    
    async loadSetorData() {
        try {
            const response = await fetch(`/financeiro/faturamento/api/setor/dados_completos?setor=${this.currentSetor}`);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Erro ao carregar dados do setor');
            }
            
            this.updateSetorKPIs(data.kpis);
            this.renderSetorChart(data.grafico_mensal);
            this.renderClientesTable(data.ranking_clientes);
        } catch (error) {
            console.error('Erro ao carregar dados do setor:', error);
        }
    }
    
    updateSetorKPIs(kpis) {
        // Faturamento Total [Setor]
        $('#valor-faturamento-setor').text(formatCurrencyShort(kpis.faturamento_total));
        
        // % [Setor]
        $('#valor-percentual-setor').text(`${kpis.percentual_participacao.toFixed(1)}%`);
    }
    
    renderSetorChart(data) {
        const ctx = document.getElementById('chart-faturamento-setor').getContext('2d');
        
        // Destruir gráfico anterior se existir
        if (this.charts.setor) {
            this.charts.setor.destroy();
        }
        
        // Preparar dados para o gráfico
        const meses = data.map(item => {
            const date = new Date(item.mes + '-01');
            return date.toLocaleDateString('pt-BR', { month: 'short', year: '2-digit' });
        });
        
        const valoresAtuais = data.map(item => item.faturamento);
        const valoresAnteriores = data.map(item => item.faturamento_anterior);
        
        this.charts.setor = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: meses,
                datasets: [{
                    label: 'Faturamento Atual',
                    data: valoresAtuais,
                    backgroundColor: 'rgba(40, 167, 69, 0.8)',
                    borderColor: 'rgba(40, 167, 69, 1)',
                    borderWidth: 2
                }, {
                    label: 'Faturamento Ano Anterior',
                    data: valoresAnteriores,
                    type: 'line',
                    borderColor: 'rgba(23, 162, 184, 1)',
                    backgroundColor: 'rgba(23, 162, 184, 0.1)',
                    borderWidth: 3,
                    fill: false,
                    tension: 0.4,
                    pointBackgroundColor: 'rgba(23, 162, 184, 1)',
                    pointBorderColor: 'white',
                    pointBorderWidth: 2,
                    pointRadius: 6
                }]
            },
            options: {
                ...this.chartDefaults,
                scales: {
                    y: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            callback: function(value) {
                                return formatCurrencyShort(value);
                            }
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
    
    renderClientesTable(data) {
        const tbody = $('#tabela-ranking-clientes tbody');
        tbody.empty();
        
        if (data.length === 0) {
            tbody.append(`
                <tr>
                    <td colspan="4" class="text-center text-muted">
                        Nenhum cliente encontrado
                    </td>
                </tr>
            `);
            return;
        }
        
        data.forEach((row, index) => {
            tbody.append(`
                <tr>
                    <td>${row.cliente}</td>
                    <td>${row.classe}</td>
                    <td class="fw-bold">${formatCurrency(row.valor)}</td>
                    <td>${row.pct_gt.toFixed(1)}%</td>
                </tr>
            `);
        });
    }
    
    openFiltersModal() {
        const modal = document.getElementById('filter-modal');
        if (modal) {
            modal.style.display = 'block';
            // Set current year in select
            $('#ano-select').val(this.currentAno);
        }
    }
    
    closeFiltersModal() {
        const modal = document.getElementById('filter-modal');
        if (modal) {
            modal.style.display = 'none';
        }
    }
    
    applyFilters() {
        const ano = $('#ano-select').val();
        this.currentAno = ano;
        $('#filter-summary-text').text(`Vendo dados do ano ${ano}`);
        $('#reset-filters').show();
        
        // Fechar modal
        this.closeFiltersModal();
        
        // Recarregar dados
        this.loadData();
    }
    
    resetFilters() {
        this.currentAno = new Date().getFullYear();
        $('#filter-summary-text').text('Vendo dados do ano atual');
        $('#reset-filters').hide();
        $('#ano-select').val(this.currentAno);
        
        this.loadData();
    }
    
    showLoading(show) {
        if (show) {
            $('#loading-overlay').show();
        } else {
            $('#loading-overlay').hide();
        }
    }
    
    showError(message) {
        // Implementar notificação de erro
        console.error(message);
        alert(message); // Temporário - substituir por toast/notification
    }
}

// Funções utilitárias
function formatCurrency(value) {
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(value);
}

function formatCurrencyShort(value) {
    const absValue = Math.abs(value);
    const prefix = value < 0 ? '-' : '';
    
    if (absValue >= 1000000) {
        // Milhões: usar 2 casas decimais para maior precisão
        return `${prefix}R$ ${(absValue / 1000000).toFixed(2)}M`;
    } else if (absValue >= 1000) {
        // Milhares: usar 1 casa decimal (exemplo: 8.9K)
        return `${prefix}R$ ${(absValue / 1000).toFixed(1)}K`;
    }
    // Valores menores que 1000: formato completo
    return formatCurrency(value);
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('pt-BR');
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Inicializar quando o documento estiver pronto
$(document).ready(function() {
    window.FaturamentoController = FaturamentoController;
});