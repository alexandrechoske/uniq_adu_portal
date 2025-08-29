/**
 * Despesas Anuais - JavaScript
 * Sistema de análise de despesas com gráficos e KPIs
 */

class DespesasController {
    constructor() {
        // Verificar se jQuery está disponível
        if (typeof $ === 'undefined') {
            console.error('jQuery não está carregado. Carregando página de despesas...');
            setTimeout(() => {
                window.location.reload();
            }, 1000);
            return;
        }
        
        this.currentPeriodo = 'ano_atual';
        this.currentCategoriaDrill = null;
        this.currentPage = 1;
        this.pageLimit = 25;
        
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
        this.initializeLayout();
        this.loadData();
    }
    
    initializeLayout() {
        // Inicializar com layout de tabela única
        $('.tables-grid').addClass('single-table');
        $('#detalhes-container').hide();
        $('#btn-voltar-categorias').hide();
    }
    
    setupEventListeners() {
        // Filtros principais
        $('#open-filters').on('click', () => this.openFiltersModal());
        $('#close-modal').on('click', () => this.closeFiltersModal());
        $('#apply-filters').on('click', () => this.applyFilters());
        $('#clear-filters').on('click', () => this.resetFilters());
        
        // Modal de detalhes
        $('#close-detalhes-modal, #modal-close-btn').on('click', () => this.closeDetalhesModal());
        $('#modal-export-btn').on('click', () => this.exportarDetalhes());
        
        // Paginação do modal
        $('#modal-btn-prev-page').on('click', () => this.changePage(this.currentPage - 1));
        $('#modal-btn-next-page').on('click', () => this.changePage(this.currentPage + 1));
        
        // Filtros do modal
        $('#modal-search').on('input', () => this.applyModalFilters());
        $('#modal-classe-filter').on('change', () => this.applyModalFilters());
        
        // Período personalizado
        $('#periodo-select').on('change', (e) => {
            if (e.target.value === 'personalizado') {
                $('#periodo-personalizado').show();
            } else {
                $('#periodo-personalizado').hide();
            }
        });
        
        // Fechar modais ao clicar no backdrop
        $(document).on('click', '.modal-backdrop', (e) => {
            if (e.target === e.currentTarget) {
                this.closeFiltersModal();
                this.closeDetalhesModal();
            }
        });
        
        // Esc key para fechar modais
        $(document).on('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeFiltersModal();
                this.closeDetalhesModal();
            }
        });
    }
    
    showLoading() {
        $('#loading-overlay').show();
    }
    
    hideLoading() {
        $('#loading-overlay').hide();
    }
    
    async loadData() {
        this.showLoading();
        
        try {
            // Carregar todos os dados em paralelo
            await Promise.all([
                this.loadKPIs(),
                this.loadCategorias(),
                this.loadTendencias(),
                this.loadFornecedores()
            ]);
            
            this.updateFilterSummary();
        } catch (error) {
            console.error('Erro ao carregar dados:', error);
            this.showError('Erro ao carregar dados de despesas');
        } finally {
            this.hideLoading();
        }
    }
    
    async loadKPIs() {
        try {
            const response = await fetch(`/financeiro/despesas/api/kpis?periodo=${this.currentPeriodo}`);
            const result = await response.json();
            
            if (result.success) {
                this.updateKPIs(result.data);
            } else {
                throw new Error(result.error);
            }
        } catch (error) {
            console.error('Erro ao carregar KPIs:', error);
            throw error;
        }
    }
    
    updateKPIs(data) {
        // Total de Despesas
        $('#valor-total-despesas').text(formatCurrencyShort(data.total_despesas));
        this.updateVariacao('#var-total-despesas', data.variacoes.total_despesas);
        
        // Despesas com Funcionários
        $('#valor-funcionarios').text(formatCurrencyShort(data.despesas_funcionarios));
        this.updateVariacao('#var-funcionarios', data.variacoes.despesas_funcionarios);
        
        // Folha Líquida
        $('#valor-folha-liquida').text(formatCurrencyShort(data.folha_liquida));
        this.updateVariacao('#var-folha-liquida', data.variacoes.folha_liquida);
        
        // Impostos
        $('#valor-impostos').text(formatCurrencyShort(data.impostos));
        this.updateVariacao('#var-impostos', data.variacoes.impostos);
        
        // Percentual Folha sobre Faturamento
        $('#valor-percentual-folha').text(data.percentual_folha_faturamento.toFixed(1) + '%');
    }
    
    updateVariacao(selector, variacao) {
        const element = $(selector);
        
        if (variacao === undefined || variacao === null) {
            element.text('-').removeClass('positive negative neutral');
            return;
        }
        
        const icon = variacao > 0 ? '▲' : variacao < 0 ? '▼' : '●';
        const className = variacao > 0 ? 'positive' : variacao < 0 ? 'negative' : 'neutral';
        
        element
            .html(`${icon} ${Math.abs(variacao).toFixed(1)}% vs. período anterior`)
            .removeClass('positive negative neutral')
            .addClass(className);
    }
    
    async loadCategorias() {
        try {
            const response = await fetch(`/financeiro/despesas/api/categorias?periodo=${this.currentPeriodo}`);
            const result = await response.json();
            
            if (result.success) {
                this.updateGraficoCategorias(result.data);
                this.updateTabelaCategorias(result.data);
            } else {
                throw new Error(result.error);
            }
        } catch (error) {
            console.error('Erro ao carregar categorias:', error);
            throw error;
        }
    }
    
    updateGraficoCategorias(data) {
        const ctx = document.getElementById('chart-categorias').getContext('2d');
        
        // Destruir gráfico anterior se existir
        if (this.charts.categorias) {
            this.charts.categorias.destroy();
        }
        
        // Preparar dados para o gráfico
        const labels = data.map(item => item.categoria);
        const valores = data.map(item => item.valor);
        
        // Cores para as barras
        const backgroundColors = [
            '#dc3545', '#fd7e14', '#ffc107', '#198754', '#0dcaf0',
            '#6f42c1', '#d63384', '#20c997', '#0d6efd', '#6610f2'
        ];
        
        this.charts.categorias = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Valor',
                    data: valores,
                    backgroundColor: backgroundColors.slice(0, data.length),
                    borderColor: backgroundColors.slice(0, data.length),
                    borderWidth: 1,
                    borderRadius: 4,
                    borderSkipped: false
                }]
            },
            options: {
                ...this.chartDefaults,
                onClick: (event, elements) => {
                    if (elements.length > 0) {
                        const index = elements[0].index;
                        const categoria = labels[index];
                        this.openDetalhesModal(categoria);
                    }
                },
                plugins: {
                    ...this.chartDefaults.plugins,
                    legend: {
                        display: false
                    },
                    tooltip: {
                        ...this.chartDefaults.plugins.tooltip,
                        callbacks: {
                            label: function(context) {
                                return `${context.dataset.label}: ${formatCurrencyShort(context.parsed.y)}`;
                            },
                            afterLabel: function(context) {
                                return 'Clique para ver detalhes';
                            }
                        }
                    },
                    datalabels: {
                        display: true,
                        anchor: 'end',
                        align: 'top',
                        offset: 4,
                        color: '#495057',
                        font: {
                            weight: 'bold',
                            size: 11
                        },
                        formatter: function(value) {
                            return formatCurrencyShort(value);
                        }
                    }
                },
                scales: {
                    y: {
                        display: false, // Ocultar eixo Y
                        beginAtZero: true
                    },
                    x: {
                        ...this.chartDefaults.scales.x,
                        ticks: {
                            maxRotation: 45,
                            minRotation: 0,
                            color: '#495057',
                            font: {
                                size: 11
                            }
                        }
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                hover: {
                    animationDuration: 200
                }
            },
            plugins: [{
                // Plugin customizado para rótulos nas barras
                id: 'barLabels',
                afterDatasetsDraw: function(chart) {
                    const ctx = chart.ctx;
                    chart.data.datasets.forEach((dataset, i) => {
                        const meta = chart.getDatasetMeta(i);
                        meta.data.forEach((bar, index) => {
                            const data = dataset.data[index];
                            
                            ctx.fillStyle = '#495057';
                            ctx.font = 'bold 11px Inter, sans-serif';
                            ctx.textAlign = 'center';
                            ctx.textBaseline = 'bottom';
                            
                            const label = formatCurrencyShort(data);
                            ctx.fillText(label, bar.x, bar.y - 5);
                        });
                    });
                }
            }]
        });
    }
    
    updateTabelaCategorias(data) {
        const tbody = $('#table-categorias tbody');
        tbody.empty();
        
        data.forEach((item, index) => {
            const row = `
                <tr>
                    <td>${item.categoria}</td>
                    <td class="currency">${formatCurrency(item.valor)}</td>
                    <td class="percentage">${item.percentual.toFixed(1)}%</td>
                    <td>
                        <button class="action-btn" onclick="despesasController.drillDownCategoria('${item.categoria}')">
                            <i class="mdi mdi-magnify"></i>
                            Detalhes
                        </button>
                    </td>
                </tr>
            `;
            tbody.append(row);
        });
    }
    
    async loadTendencias() {
        try {
            const response = await fetch(`/financeiro/despesas/api/tendencias`);
            const result = await response.json();
            
            if (result.success) {
                this.updateGraficoTendencias(result.data, result.categorias);
            } else {
                throw new Error(result.error);
            }
        } catch (error) {
            console.error('Erro ao carregar tendências:', error);
            throw error;
        }
    }
    
    updateGraficoTendencias(data, categorias) {
        const ctx = document.getElementById('chart-tendencias').getContext('2d');
        
        // Destruir gráfico anterior se existir
        if (this.charts.tendencias) {
            this.charts.tendencias.destroy();
        }
        
        if (categorias.length === 0) {
            ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
            return;
        }
        
        // Preparar dados para o gráfico de linhas
        const allLabels = new Set();
        categorias.forEach(categoria => {
            if (data[categoria] && data[categoria].labels) {
                data[categoria].labels.forEach(label => allLabels.add(label));
            }
        });
        
        const sortedLabels = Array.from(allLabels).sort();
        
        const datasets = categorias.map((categoria, index) => {
            const categoryData = data[categoria] || { labels: [], valores: [] };
            
            // Mapear valores para os labels ordenados
            const mappedValues = sortedLabels.map(label => {
                const labelIndex = categoryData.labels.indexOf(label);
                return labelIndex >= 0 ? categoryData.valores[labelIndex] : 0;
            });
            
            const colors = [
                '#dc3545', '#fd7e14', '#198754', '#0dcaf0', '#6f42c1'
            ];
            
            return {
                label: categoria,
                data: mappedValues,
                borderColor: colors[index % colors.length],
                backgroundColor: colors[index % colors.length] + '20',
                borderWidth: 2,
                fill: false,
                tension: 0.4
            };
        });
        
        this.charts.tendencias = new Chart(ctx, {
            type: 'line',
            data: {
                labels: sortedLabels,
                datasets: datasets
            },
            options: {
                ...this.chartDefaults,
                scales: {
                    ...this.chartDefaults.scales,
                    x: {
                        ...this.chartDefaults.scales.x,
                        ticks: {
                            maxTicksLimit: 12
                        }
                    }
                }
            }
        });
    }
    
    async loadFornecedores() {
        try {
            const response = await fetch(`/financeiro/despesas/api/fornecedores?periodo=${this.currentPeriodo}`);
            const result = await response.json();
            
            if (result.success) {
                this.updateTabelaFornecedores(result.data);
            } else {
                throw new Error(result.error);
            }
        } catch (error) {
            console.error('Erro ao carregar fornecedores:', error);
            throw error;
        }
    }
    
    updateTabelaFornecedores(data) {
        const tbody = $('#table-fornecedores tbody');
        tbody.empty();
        
        data.forEach((item, index) => {
            const row = `
                <tr>
                    <td>${index + 1}º</td>
                    <td>${item.descricao}</td>
                    <td class="currency">${formatCurrency(item.valor)}</td>
                    <td class="percentage">${item.percentual.toFixed(1)}%</td>
                </tr>
            `;
            tbody.append(row);
        });
    }
    
    async openDetalhesModal(categoria) {
        this.currentCategoriaDrill = categoria;
        this.currentPage = 1;
        
        try {
            this.showLoading();
            
            // Carregar dados da categoria
            await this.loadDetalhesCategoria();
            
            // Configurar modal
            $('#modal-categoria-selecionada').text(categoria);
            $('#modal-search').val('');
            $('#modal-classe-filter').val('');
            
            // Mostrar modal
            $('#detalhes-modal').show();
            
        } catch (error) {
            console.error('Erro ao abrir modal de detalhes:', error);
            this.showError('Erro ao carregar detalhes da categoria');
        } finally {
            this.hideLoading();
        }
    }
    
    closeDetalhesModal() {
        $('#detalhes-modal').hide();
        this.currentCategoriaDrill = null;
        this.currentPage = 1;
    }
    
    async loadDetalhesCategoria() {
        try {
            const response = await fetch(
                `/financeiro/despesas/api/detalhes/${encodeURIComponent(this.currentCategoriaDrill)}?periodo=${this.currentPeriodo}&page=${this.currentPage}&limit=${this.pageLimit}`
            );
            const result = await response.json();
            
            if (result.success) {
                this.updateModalDetalhes(result.data, result.pagination);
                this.updateModalStats(result.data);
                this.updateModalFilters(result.data);
            } else {
                throw new Error(result.error);
            }
        } catch (error) {
            console.error('Erro ao carregar detalhes:', error);
            throw error;
        }
    }
    
    updateModalDetalhes(data, pagination) {
        const tbody = $('#modal-table-detalhes tbody');
        tbody.empty();
        
        if (data.length === 0) {
            tbody.append(`
                <tr>
                    <td colspan="5" style="text-align: center; padding: 2rem; color: #6c757d;">
                        <i class="mdi mdi-information-outline" style="font-size: 2rem; margin-bottom: 0.5rem; display: block;"></i>
                        Nenhum registro encontrado para esta categoria no período selecionado
                    </td>
                </tr>
            `);
            $('#modal-pagination-info').text('Nenhum registro');
            $('#modal-btn-prev-page, #modal-btn-next-page').prop('disabled', true);
            return;
        }
        
        data.forEach(item => {
            const dataFormatada = new Date(item.data).toLocaleDateString('pt-BR');
            const row = `
                <tr>
                    <td>${dataFormatada}</td>
                    <td title="${item.descricao}">${item.descricao}</td>
                    <td>${item.classe || '-'}</td>
                    <td>${item.codigo || '-'}</td>
                    <td class="currency">${formatCurrency(item.valor)}</td>
                </tr>
            `;
            tbody.append(row);
        });
        
        // Atualizar informações de paginação
        const info = `Página ${pagination.current_page} de ${pagination.total_pages} (${pagination.total_records} registros)`;
        $('#modal-pagination-info').text(info);
        
        // Controlar botões de paginação
        $('#modal-btn-prev-page').prop('disabled', !pagination.has_prev);
        $('#modal-btn-next-page').prop('disabled', !pagination.has_next);
    }
    
    updateModalStats(data) {
        if (data.length === 0) {
            $('#modal-total-categoria').text('R$ 0,00');
            $('#modal-num-transacoes').text('0');
            $('#modal-valor-medio').text('R$ 0,00');
            return;
        }
        
        const total = data.reduce((sum, item) => sum + item.valor, 0);
        const numTransacoes = data.length;
        const valorMedio = total / numTransacoes;
        
        $('#modal-total-categoria').text(formatCurrencyShort(total));
        $('#modal-num-transacoes').text(numTransacoes.toLocaleString('pt-BR'));
        $('#modal-valor-medio').text(formatCurrencyShort(valorMedio));
    }
    
    updateModalFilters(data) {
        // Atualizar filtro de classes
        const classes = [...new Set(data.map(item => item.classe).filter(classe => classe))];
        const classeSelect = $('#modal-classe-filter');
        
        // Limpar opções existentes (exceto a primeira)
        classeSelect.find('option:not(:first)').remove();
        
        // Adicionar novas opções
        classes.forEach(classe => {
            classeSelect.append(`<option value="${classe}">${classe}</option>`);
        });
    }
    
    applyModalFilters() {
        // Por simplicidade, recarregar dados quando filtros mudarem
        // Em uma implementação mais sofisticada, filtraria localmente
        const search = $('#modal-search').val();
        const classe = $('#modal-classe-filter').val();
        
        if (search || classe) {
            // Implementar filtros locais ou via API
            console.log('Aplicando filtros:', { search, classe });
        }
    }
    
    exportarDetalhes() {
        // Implementar exportação dos dados
        console.log('Exportando detalhes da categoria:', this.currentCategoriaDrill);
        this.showError('Funcionalidade de exportação será implementada em breve');
    }
    
    modalPreviousPage() {
        if (this.currentPage > 1) {
            this.currentPage--;
            this.loadDetalhesCategoria();
        }
    }
    
    modalNextPage() {
        this.currentPage++;
        this.loadDetalhesCategoria();
    }
    
    changePage(newPage) {
        if (newPage >= 1) {
            this.currentPage = newPage;
            this.loadDetalhesCategoria();
        }
    }
    
    async changePage(newPage) {
        if (newPage < 1 || !this.currentCategoriaDrill) return;
        
        this.currentPage = newPage;
        
        try {
            this.showLoading();
            await this.loadDetalhesCategoria();
        } catch (error) {
            console.error('Erro ao mudar página:', error);
            this.showError('Erro ao carregar página');
        } finally {
            this.hideLoading();
        }
    }
    
    openFiltersModal() {
        $('#filters-modal').show();
        $('#periodo-select').val(this.currentPeriodo);
        
        if (this.currentPeriodo === 'personalizado') {
            $('#periodo-personalizado').show();
        } else {
            $('#periodo-personalizado').hide();
        }
    }
    
    closeFiltersModal() {
        $('#filters-modal').hide();
    }
    
    async applyFilters() {
        const periodo = $('#periodo-select').val();
        let dataInicio = '';
        let dataFim = '';
        
        if (periodo === 'personalizado') {
            dataInicio = $('#data-inicio').val();
            dataFim = $('#data-fim').val();
            
            if (!dataInicio || !dataFim) {
                this.showError('Por favor, selecione as datas de início e fim');
                return;
            }
            
            if (new Date(dataInicio) > new Date(dataFim)) {
                this.showError('A data de início deve ser anterior à data de fim');
                return;
            }
        }
        
        this.currentPeriodo = periodo;
        this.currentCategoriaDrill = null;
        this.currentPage = 1;
        
        this.closeFiltersModal();
        this.voltarCategorias();
        await this.loadData();
    }
    
    resetFilters() {
        this.currentPeriodo = 'ano_atual';
        this.currentCategoriaDrill = null;
        this.currentPage = 1;
        
        $('#periodo-select').val('ano_atual');
        $('#periodo-personalizado').hide();
        $('#data-inicio').val('');
        $('#data-fim').val('');
        
        this.closeFiltersModal();
        this.voltarCategorias();
        this.loadData();
    }
    
    updateFilterSummary() {
        let texto = '';
        
        switch (this.currentPeriodo) {
            case 'mes_atual':
                texto = 'Vendo dados do mês atual';
                break;
            case 'trimestre_atual':
                texto = 'Vendo dados do trimestre atual';
                break;
            case 'ano_atual':
                texto = 'Vendo dados do ano atual';
                break;
            case 'ultimos_12_meses':
                texto = 'Vendo dados dos últimos 12 meses';
                break;
            case 'personalizado':
                const inicio = $('#data-inicio').val();
                const fim = $('#data-fim').val();
                if (inicio && fim) {
                    texto = `Período: ${new Date(inicio).toLocaleDateString('pt-BR')} a ${new Date(fim).toLocaleDateString('pt-BR')}`;
                } else {
                    texto = 'Período personalizado';
                }
                break;
            default:
                texto = 'Vendo dados do ano atual';
        }
        
        $('#filter-summary-text').text(texto);
    }
    
    showError(message) {
        // Implementar notificação de erro
        console.error(message);
        alert(message); // Substituir por sistema de notificação mais elegante
    }
}

// Funções utilitárias
function formatCurrency(value) {
    if (value === null || value === undefined || isNaN(value)) {
        return 'R$ 0,00';
    }
    
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(value);
}

function formatCurrencyShort(value) {
    if (value === null || value === undefined || isNaN(value)) {
        return 'R$ 0';
    }
    
    const absValue = Math.abs(value);
    let suffix = '';
    let divisor = 1;
    let maxDecimals = 0;
    
    if (absValue >= 1000000000) {
        suffix = 'B';
        divisor = 1000000000;
        maxDecimals = 2; // Bilhões com 2 casas decimais
    } else if (absValue >= 1000000) {
        suffix = 'M';
        divisor = 1000000;
        maxDecimals = 2; // Milhões com 2 casas decimais
    } else if (absValue >= 1000) {
        suffix = 'K';
        divisor = 1000;
        maxDecimals = 1; // Milhares com 1 casa decimal
    }
    
    const shortValue = value / divisor;
    
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL',
        minimumFractionDigits: suffix ? maxDecimals : 0,
        maximumFractionDigits: suffix ? maxDecimals : 0
    }).format(shortValue) + suffix;
}

// Inicializar quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', function() {
    // A instância será criada no template HTML
    console.log('DespesasController módulo carregado');
});
