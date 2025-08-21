/**
 * Fluxo de Caixa - JavaScript
 * Sistema de análise de fluxo de caixa com gráficos e KPIs
 */

class FluxoCaixaController {
    constructor() {
        this.currentPeriodo = 'ultimos_12_meses';
        this.currentCategoriaDrill = null;
        this.currentPage = 1;
        this.pageLimit = 25;
        this.excludeAdmin = false; // Controle para filtrar despesas administrativas
        
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
        // Filtros
        $('#open-filters').on('click', () => this.openFiltersModal());
        $('#close-modal').on('click', () => this.closeFiltersModal());
        $('#apply-filters').on('click', () => this.applyFilters());
        $('#clear-filters').on('click', () => this.resetFilters());
        
        // Período personalizado
        $('#periodo-select').on('change', (e) => {
            if (e.target.value === 'personalizado') {
                $('#periodo-personalizado').show();
            } else {
                $('#periodo-personalizado').hide();
            }
        });
        
        // Drill-down categorias
        $('#btn-voltar-categorias').on('click', () => this.voltarCategorias());
        
        // Toggle despesas administrativas
        $('#btn-toggle-admin').on('click', () => this.toggleDespesasAdmin());
        
        // Paginação da tabela
        $('#btn-prev-page').on('click', () => this.changePage(this.currentPage - 1));
        $('#btn-next-page').on('click', () => this.changePage(this.currentPage + 1));
        
        // Busca na tabela
        $('#search-table').on('input', debounce(() => this.loadTableData(), 300));
        
        // Fechar modal ao clicar fora
        $('#filter-modal').on('click', (e) => {
            if (e.target.id === 'filter-modal') {
                this.closeFiltersModal();
            }
        });
    }
    
    async loadData() {
        this.showLoading(true);
        
        try {
            await Promise.all([
                this.loadKPIs(),
                this.loadDespesasCategoria(),
                this.loadFluxoMensal(),
                this.loadFluxoEstrutural(),
                this.loadProjecao(),
                this.loadTableData()
            ]);
        } catch (error) {
            console.error('Erro ao carregar dados:', error);
            this.showError('Erro ao carregar dados. Tente novamente.');
        } finally {
            this.showLoading(false);
        }
    }
    
    async loadKPIs() {
        try {
            const response = await fetch(`/financeiro/fluxo-de-caixa/api/kpis?periodo=${this.currentPeriodo}`);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Erro ao carregar KPIs');
            }
            
            this.updateKPIs(data);
        } catch (error) {
            console.error('Erro ao carregar KPIs:', error);
        }
    }
    
    updateKPIs(data) {
        // Resultado Líquido
        $('#valor-resultado').text(formatCurrencyShort(data.resultado_liquido.valor));
        this.updateVariation('#var-resultado', data.resultado_liquido.variacao);
        this.updateKPICardColor('#kpi-resultado', data.resultado_liquido.valor);
        
        // Entradas
        $('#valor-entradas').text(formatCurrencyShort(data.total_entradas.valor));
        this.updateVariation('#var-entradas', data.total_entradas.variacao);
        
        // Saídas
        $('#valor-saidas').text(formatCurrencyShort(data.total_saidas.valor));
        this.updateVariation('#var-saidas', data.total_saidas.variacao);
        
        // Saldo Final
        $('#valor-saldo').text(formatCurrencyShort(data.saldo_final.valor));
        this.updateVariation('#var-saldo', data.saldo_final.variacao);
        
        // Burn Rate
        $('#valor-burn-rate').text(data.burn_rate > 0 ? formatCurrencyShort(data.burn_rate) : 'N/A');
        
        // Runway
        if (data.runway === Infinity || data.runway === null || data.runway === undefined) {
            $('#valor-runway').text('∞ anos');
        } else if (data.runway <= 0) {
            $('#valor-runway').text('0 meses');
        } else if (data.runway > 60) {
            $('#valor-runway').text('5+ anos');
        } else {
            $('#valor-runway').text(`${Math.round(data.runway)} meses`);
        }
    }
    
    updateVariation(selector, variation) {
        const element = $(selector);
        const isPositive = variation > 0;
        const isNegative = variation < 0;
        
        element.removeClass('variation-positive variation-negative variation-neutral');
        
        if (isPositive) {
            element.addClass('variation-positive');
            element.html(`<i class="mdi mdi-trending-up"></i> +${variation.toFixed(1)}% vs. período anterior`);
        } else if (isNegative) {
            element.addClass('variation-negative');
            element.html(`<i class="mdi mdi-trending-down"></i> ${variation.toFixed(1)}% vs. período anterior`);
        } else {
            element.addClass('variation-neutral');
            element.html(`<i class="mdi mdi-minus"></i> Sem variação`);
        }
    }
    
    updateKPICardColor(cardSelector, value) {
        const card = $(cardSelector);
        card.removeClass('kpi-success kpi-danger kpi-warning');
        
        if (value > 0) {
            card.addClass('kpi-success');
        } else if (value < 0) {
            card.addClass('kpi-danger');
        } else {
            card.addClass('kpi-warning');
        }
    }
    
    async loadDespesasCategoria() {
        try {
            let url = `/financeiro/fluxo-de-caixa/api/despesas-categoria?periodo=${this.currentPeriodo}`;
            
            if (this.currentCategoriaDrill) {
                url += `&categoria=${encodeURIComponent(this.currentCategoriaDrill)}`;
            }
            
            if (this.excludeAdmin) {
                url += `&exclude_admin=true`;
            }
            
            const response = await fetch(url);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Erro ao carregar despesas por categoria');
            }
            
            this.renderDespesasChart(data);
        } catch (error) {
            console.error('Erro ao carregar despesas por categoria:', error);
        }
    }
    
    renderDespesasChart(data) {
        const ctx = document.getElementById('chart-despesas-categoria').getContext('2d');
        
        // Destruir gráfico anterior se existir
        if (this.charts.despesas) {
            this.charts.despesas.destroy();
        }
        
        // Atualizar título
        const title = data.drill_categoria ? 
            `Classes em ${data.drill_categoria}` : 
            'Despesas por Categoria';
        $('#chart-despesas-title').text(title);
        
        // Mostrar/ocultar botões
        if (data.drill_categoria) {
            $('#btn-voltar-categorias').show();
            $('#btn-toggle-admin').hide(); // Esconder toggle no drill-down
        } else {
            $('#btn-voltar-categorias').hide();
            $('#btn-toggle-admin').show(); // Mostrar toggle na visão principal
            
            // Atualizar estado do botão toggle
            if (this.excludeAdmin) {
                $('#btn-toggle-admin').removeClass('btn-warning').addClass('btn-success');
                $('#btn-toggle-admin i').removeClass('mdi-eye-off').addClass('mdi-eye');
                $('#btn-toggle-text').text('Mostrar Admin');
            } else {
                $('#btn-toggle-admin').removeClass('btn-success').addClass('btn-warning');
                $('#btn-toggle-admin i').removeClass('mdi-eye').addClass('mdi-eye-off');
                $('#btn-toggle-text').text('Ocultar Admin');
            }
        }
        
        // Configurar cores para gráfico de barras
        const colors = this.generateColors(data.labels.length);
        
        this.charts.despesas = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Valor das Despesas',
                    data: data.valores,
                    backgroundColor: colors.background,
                    borderColor: colors.border,
                    borderWidth: 2,
                    borderRadius: 6,
                    borderSkipped: false
                }]
            },
            options: {
                ...this.chartDefaults,
                indexAxis: 'y', // Barras horizontais para melhor visualização de categorias
                onClick: (event, elements) => {
                    if (elements.length > 0 && !data.drill_categoria) {
                        const index = elements[0].index;
                        const categoria = data.labels[index];
                        this.drillDownCategoria(categoria);
                    }
                },
                plugins: {
                    ...this.chartDefaults.plugins,
                    tooltip: {
                        ...this.chartDefaults.plugins.tooltip,
                        callbacks: {
                            label: function(context) {
                                const value = context.parsed.x;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((value / total) * 100).toFixed(1);
                                return `${context.label}: ${formatCurrencyShort(value)} (${percentage}%)`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            callback: function(value) {
                                return formatCurrencyShort(value);
                            }
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
    
    async drillDownCategoria(categoria) {
        this.currentCategoriaDrill = categoria;
        await this.loadDespesasCategoria();
    }
    
    async voltarCategorias() {
        this.currentCategoriaDrill = null;
        await this.loadDespesasCategoria();
    }
    
    async toggleDespesasAdmin() {
        this.excludeAdmin = !this.excludeAdmin;
        await this.loadDespesasCategoria();
    }
    
    async loadFluxoMensal() {
        try {
            const response = await fetch(`/financeiro/fluxo-de-caixa/api/fluxo-mensal?periodo=${this.currentPeriodo}`);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Erro ao carregar fluxo mensal');
            }
            
            this.renderFluxoMensalChart(data);
        } catch (error) {
            console.error('Erro ao carregar fluxo mensal:', error);
        }
    }
    
    renderFluxoMensalChart(data) {
        const ctx = document.getElementById('chart-fluxo-mensal').getContext('2d');
        
        if (this.charts.fluxoMensal) {
            this.charts.fluxoMensal.destroy();
        }
        
        // Cores baseadas no valor (verde para positivo, vermelho para negativo)
        const backgroundColors = data.resultados.map(value => 
            value >= 0 ? 'rgba(40, 167, 69, 0.8)' : 'rgba(220, 53, 69, 0.8)'
        );
        const borderColors = data.resultados.map(value => 
            value >= 0 ? 'rgba(40, 167, 69, 1)' : 'rgba(220, 53, 69, 1)'
        );
        
        this.charts.fluxoMensal = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.meses,
                datasets: [{
                    label: 'Resultado Mensal',
                    data: data.resultados,
                    backgroundColor: backgroundColors,
                    borderColor: borderColors,
                    borderWidth: 2,
                    borderRadius: 6,
                    borderSkipped: false
                }, {
                    label: 'Saldo Acumulado',
                    data: data.saldo_acumulado,
                    type: 'line',
                    borderColor: 'rgba(23, 162, 184, 1)',
                    backgroundColor: 'rgba(23, 162, 184, 0.1)',
                    borderWidth: 3,
                    fill: false,
                    tension: 0.4,
                    pointBackgroundColor: 'rgba(23, 162, 184, 1)',
                    pointBorderColor: 'white',
                    pointBorderWidth: 2,
                    pointRadius: 6,
                    yAxisID: 'y1'
                }]
            },
            options: {
                ...this.chartDefaults,
                scales: {
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        grid: {
                            display: false
                        },
                        ticks: {
                            callback: function(value) {
                                return formatCurrencyShort(value);
                            }
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        grid: {
                            drawOnChartArea: false,
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
    
    async loadFluxoEstrutural() {
        try {
            const response = await fetch(`/financeiro/fluxo-de-caixa/api/fluxo-estrutural?periodo=${this.currentPeriodo}`);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Erro ao carregar fluxo estrutural');
            }
            
            this.renderFluxoEstruturalChart(data);
        } catch (error) {
            console.error('Erro ao carregar fluxo estrutural:', error);
        }
    }
    
    renderFluxoEstruturalChart(data) {
        const ctx = document.getElementById('chart-fluxo-estrutural').getContext('2d');
        
        if (this.charts.fluxoEstrutural) {
            this.charts.fluxoEstrutural.destroy();
        }
        
        this.charts.fluxoEstrutural = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.meses,
                datasets: [{
                    label: 'FCO (Operacional)',
                    data: data.fco,
                    backgroundColor: 'rgba(40, 167, 69, 0.8)',
                    borderColor: 'rgba(40, 167, 69, 1)',
                    borderWidth: 2
                }, {
                    label: 'FCI (Investimento)',
                    data: data.fci,
                    backgroundColor: 'rgba(255, 193, 7, 0.8)',
                    borderColor: 'rgba(255, 193, 7, 1)',
                    borderWidth: 2
                }, {
                    label: 'FCF (Financiamento)',
                    data: data.fcf,
                    backgroundColor: 'rgba(23, 162, 184, 0.8)',
                    borderColor: 'rgba(23, 162, 184, 1)',
                    borderWidth: 2
                }]
            },
            options: {
                ...this.chartDefaults,
                scales: {
                    x: {
                        stacked: true,
                        grid: {
                            display: false
                        }
                    },
                    y: {
                        stacked: true,
                        grid: {
                            display: false
                        },
                        ticks: {
                            callback: function(value) {
                                return formatCurrencyShort(value);
                            }
                        }
                    }
                }
            }
        });
    }
    
    async loadProjecao() {
        try {
            const response = await fetch('/financeiro/fluxo-de-caixa/api/projecao');
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Erro ao carregar projeção');
            }
            
            this.renderProjecaoChart(data);
        } catch (error) {
            console.error('Erro ao carregar projeção:', error);
        }
    }
    
    renderProjecaoChart(data) {
        const ctx = document.getElementById('chart-projecao').getContext('2d');
        
        if (this.charts.projecao) {
            this.charts.projecao.destroy();
        }
        
        // Combinar dados históricos e projeção
        const allLabels = [...data.meses_historicos, ...data.meses_projecao];
        const historicoData = [...data.saldo_historico, ...Array(data.meses_projecao.length).fill(null)];
        const projecaoData = [...Array(data.meses_historicos.length).fill(null), ...data.saldo_projetado];
        
        this.charts.projecao = new Chart(ctx, {
            type: 'line',
            data: {
                labels: allLabels,
                datasets: [{
                    label: 'Saldo Histórico',
                    data: historicoData,
                    borderColor: 'rgba(40, 167, 69, 1)',
                    backgroundColor: 'rgba(40, 167, 69, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: 'rgba(40, 167, 69, 1)',
                    pointBorderColor: 'white',
                    pointBorderWidth: 2,
                    pointRadius: 4
                }, {
                    label: 'Projeção',
                    data: projecaoData,
                    borderColor: 'rgba(220, 53, 69, 1)',
                    backgroundColor: 'rgba(220, 53, 69, 0.1)',
                    borderWidth: 3,
                    borderDash: [10, 5],
                    fill: false,
                    tension: 0.4,
                    pointBackgroundColor: 'rgba(220, 53, 69, 1)',
                    pointBorderColor: 'white',
                    pointBorderWidth: 2,
                    pointRadius: 4
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
    
    async loadTableData() {
        try {
            const searchTerm = $('#search-table').val();
            const url = `/financeiro/fluxo-de-caixa/api/tabela-dados?periodo=${this.currentPeriodo}&page=${this.currentPage}&limit=${this.pageLimit}`;
            
            const response = await fetch(url);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Erro ao carregar dados da tabela');
            }
            
            this.renderTable(data);
            this.updatePagination(data);
        } catch (error) {
            console.error('Erro ao carregar dados da tabela:', error);
        }
    }
    
    renderTable(data) {
        const tbody = $('#tabela-dados tbody');
        tbody.empty();
        
        if (data.dados.length === 0) {
            tbody.append(`
                <tr>
                    <td colspan="7" class="text-center text-muted">
                        Nenhum registro encontrado
                    </td>
                </tr>
            `);
            return;
        }
        
        data.dados.forEach(row => {
            const tipoClass = row.tipo === 'Receita' ? 'text-success' : 'text-danger';
            const valorFormatted = row.tipo === 'Receita' ? 
                formatCurrency(row.valor) : 
                `-${formatCurrency(row.valor)}`;
            
            tbody.append(`
                <tr>
                    <td>${formatDate(row.data)}</td>
                    <td>${row.categoria}</td>
                    <td>${row.classe}</td>
                    <td>${row.codigo}</td>
                    <td>${row.descricao}</td>
                    <td><span class="badge ${row.tipo === 'Receita' ? 'bg-success' : 'bg-danger'}">${row.tipo}</span></td>
                    <td class="${tipoClass} fw-bold">${valorFormatted}</td>
                </tr>
            `);
        });
    }
    
    updatePagination(data) {
        // Atualizar informações
        $('#pagination-info').text(
            `Mostrando ${((data.page - 1) * data.limit) + 1} a ${Math.min(data.page * data.limit, data.total)} de ${data.total} registros`
        );
        
        // Atualizar botões
        $('#btn-prev-page').prop('disabled', data.page <= 1);
        $('#btn-next-page').prop('disabled', data.page >= data.total_pages);
        
        // Atualizar páginas
        const pagesContainer = $('#pagination-pages');
        pagesContainer.empty();
        
        const startPage = Math.max(1, data.page - 2);
        const endPage = Math.min(data.total_pages, data.page + 2);
        
        for (let i = startPage; i <= endPage; i++) {
            const button = $(`<button class="pagination-page ${i === data.page ? 'active' : ''}">${i}</button>`);
            button.on('click', () => this.changePage(i));
            pagesContainer.append(button);
        }
    }
    
    changePage(page) {
        this.currentPage = page;
        this.loadTableData();
    }
    
    generateColors(count) {
        const baseColors = [
            '#007bff', '#28a745', '#dc3545', '#ffc107', '#17a2b8',
            '#6f42c1', '#fd7e14', '#20c997', '#6610f2', '#e83e8c',
            '#495057', '#f8f9fa', '#e9ecef', '#dee2e6', '#ced4da'
        ];
        
        const background = [];
        const border = [];
        
        for (let i = 0; i < count; i++) {
            const color = baseColors[i % baseColors.length];
            background.push(color + 'CC'); // 80% opacity para barras
            border.push(color);
        }
        
        return { background, border };
    }
    
    openFiltersModal() {
        const modal = document.getElementById('filter-modal');
        if (modal) {
            modal.style.display = 'block';
        }
    }
    
    closeFiltersModal() {
        const modal = document.getElementById('filter-modal');
        if (modal) {
            modal.style.display = 'none';
        }
    }
    
    applyFilters() {
        const periodo = $('#periodo-select').val();
        
        if (periodo === 'personalizado') {
            const dataInicio = $('#data-inicio').val();
            const dataFim = $('#data-fim').val();
            
            if (!dataInicio || !dataFim) {
                alert('Por favor, selecione as datas de início e fim');
                return;
            }
            
            this.currentPeriodo = `${dataInicio}|${dataFim}`;
            $('#filter-summary-text').text(`Período: ${formatDate(dataInicio)} a ${formatDate(dataFim)}`);
        } else {
            this.currentPeriodo = periodo;
            const periodNames = {
                'mes_atual': 'Mês Atual',
                'ultimo_mes': 'Último Mês',
                'trimestre_atual': 'Trimestre Atual',
                'ultimos_12_meses': 'Últimos 12 Meses',
                'ano_atual': 'Ano Atual',
                'ultimo_ano': 'Último Ano'
            };
            $('#filter-summary-text').text(`Período: ${periodNames[periodo]}`);
        }
        
        $('#reset-filters').show();
        
        // Fechar modal
        this.closeFiltersModal();
        
        // Recarregar dados
        this.loadData();
    }
    
    resetFilters() {
        this.currentPeriodo = 'ano_atual';
        this.currentCategoriaDrill = null;
        $('#filter-summary-text').text('Vendo dados do ano atual');
        $('#reset-filters').hide();
        $('#periodo-select').val('ano_atual');
        $('#periodo-personalizado').hide();
        
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
        return `${prefix}R$ ${(absValue / 1000000).toFixed(1)}M`;
    } else if (absValue >= 1000) {
        return `${prefix}R$ ${(absValue / 1000).toFixed(1)}K`;
    }
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
    window.fluxoCaixa = new FluxoCaixaController();
});
