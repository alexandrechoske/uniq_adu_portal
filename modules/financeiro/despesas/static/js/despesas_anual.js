/**
 * Despesas Anuais - JavaScript Atualizado
 * Sistema de análise de despesas com gráficos e KPIs
 * Versão com suporte a Centro de Resultado
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
        this.currentCentroResultado = '';
        this.currentCategoria = '';
        this.currentClasse = '';
        this.currentCategoriaDrill = null;
        this.currentPage = 1;
        this.pageLimit = 25;
        this.currentMode = 'centro_resultado'; // 'centro_resultado' ou 'categoria'
        
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
        this.loadFilterOptions();
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
        
        // Alternar modo entre categoria e centro de resultado
        $('input[name="chart-mode"]').on('change', (e) => {
            this.currentMode = e.target.value;
            this.updateChartTitle();
            this.loadCategoriasData();
        });
        
        $('input[name="table-mode"]').on('change', (e) => {
            this.currentMode = e.target.value;
            this.updateTableTitle();
            this.loadCategoriasData();
        });
        
        // Modal de detalhes
        $('#close-detalhes-modal, #modal-close-btn').on('click', () => this.closeDetalhesModal());
        $('#modal-export-btn').on('click', () => this.exportarDetalhes());
        
        // Paginação do modal
        $('#modal-btn-prev-page').on('click', () => this.prevPageModal());
        $('#modal-btn-next-page').on('click', () => this.nextPageModal());
        
        // Busca no modal
        $('#modal-search').on('input', debounce(() => this.searchDetalhes(), 500));
        $('#modal-classe-filter').on('change', () => this.filterDetalhes());
        
        // Período personalizado
        $('#periodo-select').on('change', (e) => {
            if (e.target.value === 'personalizado') {
                $('#periodo-personalizado').show();
            } else {
                $('#periodo-personalizado').hide();
            }
        });
        
        // Fechar modal ao clicar fora
        $(document).on('click', '.modal-backdrop', (e) => {
            if (e.target === e.currentTarget) {
                this.closeFiltersModal();
                this.closeDetalhesModal();
            }
        });
    }
    
    async loadFilterOptions() {
        try {
            const response = await fetch('/financeiro/despesas/api/filtros-opcoes');
            const result = await response.json();
            
            if (result.success) {
                this.populateFilterOptions(result.data);
            }
        } catch (error) {
            console.error('Erro ao carregar opções de filtros:', error);
        }
    }
    
    populateFilterOptions(data) {
        // Limpar e popular centro de resultado
        const centroSelect = $('#centro-resultado-select');
        centroSelect.html('<option value="">Todos os Centros de Resultado</option>');
        data.centros_resultado.forEach(centro => {
            centroSelect.append(`<option value="${centro}">${centro}</option>`);
        });
        
        // Limpar e popular categoria
        const categoriaSelect = $('#categoria-select');
        categoriaSelect.html('<option value="">Todas as Categorias</option>');
        data.categorias.forEach(categoria => {
            categoriaSelect.append(`<option value="${categoria}">${categoria}</option>`);
        });
        
        // Limpar e popular classe
        const classeSelect = $('#classe-select');
        classeSelect.html('<option value="">Todas as Classes</option>');
        data.classes.forEach(classe => {
            classeSelect.append(`<option value="${classe}">${classe}</option>`);
        });
    }
    
    updateChartTitle() {
        const title = this.currentMode === 'centro_resultado' ? 
            'Despesas por Centro de Resultado' : 
            'Despesas por Categoria';
        $('#chart-title').text(title);
    }
    
    updateTableTitle() {
        const title = this.currentMode === 'centro_resultado' ? 
            'Análise por Centro de Resultado' : 
            'Análise por Categoria';
        $('#table-title').text(title);
        
        // Atualizar cabeçalho da coluna
        const headerText = this.currentMode === 'centro_resultado' ? 
            'Centro de Resultado' : 
            'Categoria';
        $('#col-header-name').text(headerText);
    }
    
    showLoading() {
        $('#loading-overlay').fadeIn(300);
    }
    
    hideLoading() {
        $('#loading-overlay').fadeOut(300);
    }
    
    async loadData() {
        this.showLoading();
        
        try {
            await Promise.all([
                this.loadKPIs(),
                this.loadCategoriasData(),
                this.loadTendencias(),
                this.loadFornecedores()
            ]);
        } catch (error) {
            console.error('Erro ao carregar dados:', error);
            this.showError('Erro ao carregar dados das despesas');
        } finally {
            this.hideLoading();
        }
    }
    
    async loadKPIs() {
        try {
            const params = new URLSearchParams({
                periodo: this.currentPeriodo,
                centro_resultado: this.currentCentroResultado,
                categoria: this.currentCategoria,
                classe: this.currentClasse
            });
            
            const response = await fetch(`/financeiro/despesas/api/kpis?${params}`);
            const result = await response.json();
            
            if (result.success) {
                this.updateKPIs(result.data);
            } else {
                throw new Error(result.error || 'Erro ao carregar KPIs');
            }
        } catch (error) {
            console.error('Erro ao carregar KPIs:', error);
            this.showError('Erro ao carregar indicadores principais');
        }
    }
    
    async loadCategoriasData() {
        try {
            const endpoint = this.currentMode === 'centro_resultado' ? 
                '/financeiro/despesas/api/centro-resultado' : 
                '/financeiro/despesas/api/categorias';
            
            const params = new URLSearchParams({
                periodo: this.currentPeriodo,
                centro_resultado: this.currentCentroResultado,
                categoria: this.currentCategoria,
                classe: this.currentClasse
            });
            
            const response = await fetch(`${endpoint}?${params}`);
            const result = await response.json();
            
            if (result.success) {
                this.updateCategoriasChart(result.data);
                this.updateCategoriasTable(result.data);
            } else {
                throw new Error(result.error || 'Erro ao carregar dados de categorias');
            }
        } catch (error) {
            console.error('Erro ao carregar categorias:', error);
            this.showError('Erro ao carregar análise por categoria/centro de resultado');
        }
    }
    
    async loadTendencias() {
        try {
            const response = await fetch('/financeiro/despesas/api/tendencias');
            const result = await response.json();
            
            if (result.success) {
                this.updateTendenciasChart(result.data, result.combinacoes || result.categorias);
            } else {
                throw new Error(result.error || 'Erro ao carregar tendências');
            }
        } catch (error) {
            console.error('Erro ao carregar tendências:', error);
            this.showError('Erro ao carregar tendências mensais');
        }
    }
    
    async loadFornecedores() {
        try {
            const params = new URLSearchParams({
                periodo: this.currentPeriodo,
                centro_resultado: this.currentCentroResultado,
                categoria: this.currentCategoria,
                classe: this.currentClasse
            });
            
            const response = await fetch(`/financeiro/despesas/api/fornecedores?${params}`);
            const result = await response.json();
            
            if (result.success) {
                this.updateFornecedoresTable(result.data);
            } else {
                throw new Error(result.error || 'Erro ao carregar fornecedores');
            }
        } catch (error) {
            console.error('Erro ao carregar fornecedores:', error);
            this.showError('Erro ao carregar ranking de fornecedores');
        }
    }
    
    updateKPIs(data) {
        // Atualizar valores
        $('#valor-total-despesas').text(formatCurrency(data.total_despesas || 0));
        $('#valor-funcionarios').text(formatCurrency(data.despesas_funcionarios || 0));
        $('#valor-folha-liquida').text(formatCurrency(data.folha_liquida || 0));
        $('#valor-impostos').text(formatCurrency(data.impostos || 0));
        $('#valor-percentual-folha').text(formatPercentage(data.percentual_folha_faturamento || 0));
        
        // Atualizar variações se disponível
        if (data.variacoes) {
            this.updateVariacoes(data.variacoes);
        }
    }
    
    updateVariacoes(variacoes) {
        const kpis = [
            { element: '#var-total-despesas', value: variacoes.total_despesas },
            { element: '#var-funcionarios', value: variacoes.despesas_funcionarios },
            { element: '#var-folha-liquida', value: variacoes.folha_liquida },
            { element: '#var-impostos', value: variacoes.impostos }
        ];
        
        kpis.forEach(kpi => {
            if (kpi.value !== undefined) {
                const element = $(kpi.element);
                const isPositive = kpi.value > 0;
                const icon = isPositive ? 'mdi-trending-up' : 'mdi-trending-down';
                const className = isPositive ? 'variation-up' : 'variation-down';
                
                element.html(`
                    <i class="mdi ${icon}"></i>
                    ${Math.abs(kpi.value).toFixed(1)}%
                `).removeClass('variation-up variation-down').addClass(className);
            }
        });
    }
    
    updateCategoriasChart(data) {
        const ctx = document.getElementById('chart-categorias').getContext('2d');
        
        // Destruir gráfico anterior se existir
        if (this.charts.categorias) {
            this.charts.categorias.destroy();
        }
        
        const labels = data.map(item => 
            this.currentMode === 'centro_resultado' ? 
                (item.centro_resultado || 'Não informado') : 
                (item.categoria || 'Não informado')
        );
        const valores = data.map(item => item.valor);
        
        this.charts.categorias = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Valor das Despesas',
                    data: valores,
                    backgroundColor: 'rgba(54, 162, 235, 0.8)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                ...this.chartDefaults,
                onClick: (event, elements) => {
                    if (elements.length > 0) {
                        const index = elements[0].index;
                        const label = labels[index];
                        this.openDetalhesModal(label);
                    }
                }
            }
        });
    }
    
    updateCategoriasTable(data) {
        const tbody = $('#table-categorias tbody');
        tbody.empty();
        
        data.forEach(item => {
            const nome = this.currentMode === 'centro_resultado' ? 
                (item.centro_resultado || 'Não informado') : 
                (item.categoria || 'Não informado');
            
            const row = `
                <tr>
                    <td>${nome}</td>
                    <td>${formatCurrency(item.valor)}</td>
                    <td>${formatPercentage(item.percentual)}</td>
                    <td>
                        <button class="btn btn-sm btn-primary" onclick="window.despesasController.openDetalhesModal('${nome}')">
                            <i class="mdi mdi-eye"></i>
                            Ver Detalhes
                        </button>
                    </td>
                </tr>
            `;
            tbody.append(row);
        });
    }
    
    updateTendenciasChart(data, series) {
        const ctx = document.getElementById('chart-tendencias').getContext('2d');
        
        // Destruir gráfico anterior se existir
        if (this.charts.tendencias) {
            this.charts.tendencias.destroy();
        }
        
        // Preparar dados para o gráfico de linha
        const allLabels = new Set();
        Object.values(data).forEach(item => {
            item.labels.forEach(label => allLabels.add(label));
        });
        
        const sortedLabels = Array.from(allLabels).sort();
        
        const datasets = series.map((serie, index) => {
            const serieData = data[serie] || { labels: [], valores: [] };
            const valores = sortedLabels.map(label => {
                const labelIndex = serieData.labels.indexOf(label);
                return labelIndex >= 0 ? serieData.valores[labelIndex] : 0;
            });
            
            const colors = [
                'rgba(255, 99, 132, 0.8)',
                'rgba(54, 162, 235, 0.8)',
                'rgba(255, 205, 86, 0.8)',
                'rgba(75, 192, 192, 0.8)',
                'rgba(153, 102, 255, 0.8)'
            ];
            
            return {
                label: serie,
                data: valores,
                borderColor: colors[index % colors.length],
                backgroundColor: colors[index % colors.length].replace('0.8', '0.2'),
                tension: 0.1
            };
        });
        
        this.charts.tendencias = new Chart(ctx, {
            type: 'line',
            data: {
                labels: sortedLabels,
                datasets: datasets
            },
            options: this.chartDefaults
        });
    }
    
    updateFornecedoresTable(data) {
        const tbody = $('#table-fornecedores tbody');
        tbody.empty();
        
        data.forEach((item, index) => {
            const row = `
                <tr>
                    <td>${index + 1}</td>
                    <td>${item.descricao}</td>
                    <td>${formatCurrency(item.valor)}</td>
                    <td>${formatPercentage(item.percentual)}</td>
                </tr>
            `;
            tbody.append(row);
        });
    }
    
    // Continua com os métodos restantes...
    async openDetalhesModal(categoria) {
        this.currentCategoriaDrill = categoria;
        this.currentPage = 1;
        
        $('#modal-categoria-selecionada').text(categoria);
        $('#detalhes-modal').fadeIn(300);
        
        await this.loadDetalhesData();
    }
    
    async loadDetalhesData() {
        try {
            const params = new URLSearchParams({
                periodo: this.currentPeriodo,
                page: this.currentPage,
                limit: this.pageLimit
            });
            
            // Adicionar parâmetro para indicar que estamos filtrando por centro de resultado
            if (this.currentMode === 'centro_resultado') {
                params.append('centro_resultado', 'true');
            }
            
            const response = await fetch(`/financeiro/despesas/api/detalhes/${encodeURIComponent(this.currentCategoriaDrill)}?${params}`);
            const result = await response.json();
            
            if (result.success) {
                this.updateDetalhesModal(result.data, result.pagination, result.totals);
            } else {
                throw new Error(result.error || 'Erro ao carregar detalhes');
            }
        } catch (error) {
            console.error('Erro ao carregar detalhes:', error);
            this.showError('Erro ao carregar detalhes da categoria');
        }
    }
    
    updateDetalhesModal(data, pagination, totals) {
        // Atualizar estatísticas
        if (totals) {
            $('#modal-total-categoria').text(formatCurrency(totals.total_valor || 0));
            $('#modal-num-transacoes').text(totals.num_transacoes || 0);
            $('#modal-valor-medio').text(formatCurrency(totals.valor_medio || 0));
        }
        
        // Atualizar tabela
        const tbody = $('#modal-table-detalhes tbody');
        tbody.empty();
        
        data.forEach(item => {
            const row = `
                <tr>
                    <td>${formatDate(item.data)}</td>
                    <td>${item.descricao}</td>
                    <td>${item.classe}</td>
                    <td>${item.codigo}</td>
                    <td>${formatCurrency(item.valor)}</td>
                </tr>
            `;
            tbody.append(row);
        });
        
        // Atualizar paginação
        this.updateModalPagination(pagination);
    }
    
    updateModalPagination(pagination) {
        $('#modal-pagination-info').text(
            `Página ${pagination.current_page} de ${pagination.total_pages} (${pagination.total_records} registros)`
        );
        
        $('#modal-btn-prev-page').prop('disabled', !pagination.has_prev);
        $('#modal-btn-next-page').prop('disabled', !pagination.has_next);
    }
    
    closeDetalhesModal() {
        $('#detalhes-modal').fadeOut(300);
        this.currentCategoriaDrill = null;
    }
    
    openFiltersModal() {
        // Carregar valores atuais nos filtros
        $('#periodo-select').val(this.currentPeriodo);
        $('#centro-resultado-select').val(this.currentCentroResultado);
        $('#categoria-select').val(this.currentCategoria);
        $('#classe-select').val(this.currentClasse);
        
        $('#filters-modal').fadeIn(300);
    }
    
    closeFiltersModal() {
        $('#filters-modal').fadeOut(300);
    }
    
    async applyFilters() {
        // Obter valores dos filtros
        this.currentPeriodo = $('#periodo-select').val();
        this.currentCentroResultado = $('#centro-resultado-select').val();
        this.currentCategoria = $('#categoria-select').val();
        this.currentClasse = $('#classe-select').val();
        
        // Atualizar resumo de filtros
        this.updateFilterSummary();
        
        // Recarregar dados
        this.closeFiltersModal();
        await this.loadData();
    }
    
    resetFilters() {
        this.currentPeriodo = 'ano_atual';
        this.currentCentroResultado = '';
        this.currentCategoria = '';
        this.currentClasse = '';
        
        this.updateFilterSummary();
        this.closeFiltersModal();
        this.loadData();
    }
    
    updateFilterSummary() {
        let summary = '';
        
        // Período
        const periodoText = {
            'mes_atual': 'mês atual',
            'trimestre_atual': 'trimestre atual',
            'ano_atual': 'ano atual',
            'ultimos_12_meses': 'últimos 12 meses'
        };
        summary += `Vendo dados do ${periodoText[this.currentPeriodo] || this.currentPeriodo}`;
        
        // Filtros adicionais
        const filtros = [];
        if (this.currentCentroResultado) filtros.push(`Centro: ${this.currentCentroResultado}`);
        if (this.currentCategoria) filtros.push(`Categoria: ${this.currentCategoria}`);
        if (this.currentClasse) filtros.push(`Classe: ${this.currentClasse}`);
        
        if (filtros.length > 0) {
            summary += ` | Filtros: ${filtros.join(', ')}`;
            $('#reset-filters').show();
        } else {
            $('#reset-filters').hide();
        }
        
        $('#filter-summary-text').text(summary);
    }
    
    prevPageModal() {
        if (this.currentPage > 1) {
            this.currentPage--;
            this.loadDetalhesData();
        }
    }
    
    nextPageModal() {
        this.currentPage++;
        this.loadDetalhesData();
    }
    
    showError(message) {
        console.error(message);
        // Implementar notificação de erro conforme o sistema
    }
    
    exportarDetalhes() {
        // Implementar exportação
        console.log('Exportar detalhes não implementado ainda');
    }
    
    searchDetalhes() {
        // Implementar busca
        console.log('Busca em detalhes não implementada ainda');
    }
    
    filterDetalhes() {
        // Implementar filtro
        console.log('Filtro de detalhes não implementado ainda');
    }
}

// Funções utilitárias
function formatCurrency(value) {
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(value || 0);
}

function formatCurrencyShort(value) {
    if (value >= 1000000) {
        return `R$ ${(value / 1000000).toFixed(1)}M`;
    } else if (value >= 1000) {
        return `R$ ${(value / 1000).toFixed(1)}K`;
    }
    return formatCurrency(value);
}

function formatPercentage(value) {
    return `${(value || 0).toFixed(1)}%`;
}

function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString('pt-BR');
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