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
        this.loadMetas(); // Load metas on initialization
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
        
        // Metas
        $('#open-metas-modal').on('click', () => this.openMetasModal());
        $('#close-metas-modal, #cancel-metas').on('click', () => this.closeMetasModal());
        $('#save-meta').on('click', () => this.saveMeta());
        
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
        $('#filter-modal, #metas-modal').on('click', (e) => {
            if (e.target.id === 'filter-modal') {
                this.closeFiltersModal();
            } else if (e.target.id === 'metas-modal') {
                this.closeMetasModal();
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
        
        // Check if data exists
        if (!data || !Array.isArray(data)) {
            console.error('Invalid data for table rendering');
            return;
        }
        
        // Create a map of month data for easier access
        const monthData = {};
        let totalMeta = 0;
        
        data.forEach(row => {
            // Ensure row has required properties
            if (!row || !row.ano || !row.mes) {
                return;
            }
            
            if (!monthData[row.ano]) {
                monthData[row.ano] = {};
            }
            monthData[row.ano][row.mes] = {
                faturamento: row.faturamento_total || 0,
                anterior: row.faturamento_anterior || 0,
                variacao: row.variacao || 0
            };
        });
        
        // Create the pivoted table row
        const monthNames = [
            'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
            'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
        ];
        
        // Get metas for the current year
        this.loadMetasForYear(this.currentAno).then(metas => {
            Object.keys(monthData).forEach(ano => {
                const row = $('<tr></tr>');
                row.append(`<td>${ano}</td>`);
                
                let totalFaturamento = 0;
                
                // Add data for each month
                for (let mes = 1; mes <= 12; mes++) {
                    if (monthData[ano] && monthData[ano][mes]) {
                        const mesData = monthData[ano][mes];
                        const faturamento = typeof mesData.faturamento === 'object' ? 0 : (mesData.faturamento || 0);
                        totalFaturamento += faturamento;
                        const variacao = typeof mesData.variacao === 'object' ? 0 : (mesData.variacao || 0);
                        const variacaoClass = variacao > 0 ? 'text-success' : variacao < 0 ? 'text-danger' : '';
                        const variacaoIcon = variacao > 0 ? 'mdi mdi-trending-up' : variacao < 0 ? 'mdi mdi-trending-down' : 'mdi mdi-minus';
                        
                        row.append(`
                            <td>
                                <div class="fw-bold">${formatCurrency(faturamento)}</div>
                                <div class="${variacaoClass}">
                                    <i class="${variacaoIcon}"></i>
                                    ${Math.abs(variacao).toFixed(1)}%
                                </div>
                            </td>
                        `);
                    } else {
                        row.append(`<td>-</td>`);
                    }
                }
                
                // Add meta column
                const metaValue = metas && metas.anual ? (metas.anual.meta || 0) : 0;
                const numericMeta = typeof metaValue === 'object' ? 0 : metaValue;
                row.append(`<td class="fw-bold">${formatCurrency(numericMeta)}</td>`);
                
                tbody.append(row);
            });
        }).catch(error => {
            console.error('Error loading metas:', error);
            // Render table without metas if there's an error
            Object.keys(monthData).forEach(ano => {
                const row = $('<tr></tr>');
                row.append(`<td>${ano}</td>`);
                
                // Add data for each month
                for (let mes = 1; mes <= 12; mes++) {
                    if (monthData[ano] && monthData[ano][mes]) {
                        const mesData = monthData[ano][mes];
                        const faturamento = typeof mesData.faturamento === 'object' ? 0 : (mesData.faturamento || 0);
                        const variacao = typeof mesData.variacao === 'object' ? 0 : (mesData.variacao || 0);
                        const variacaoClass = variacao > 0 ? 'text-success' : variacao < 0 ? 'text-danger' : '';
                        const variacaoIcon = variacao > 0 ? 'mdi mdi-trending-up' : variacao < 0 ? 'mdi mdi-trending-down' : 'mdi mdi-minus';
                        
                        row.append(`
                            <td>
                                <div class="fw-bold">${formatCurrency(faturamento)}</div>
                                <div class="${variacaoClass}">
                                    <i class="${variacaoIcon}"></i>
                                    ${Math.abs(variacao).toFixed(1)}%
                                </div>
                            </td>
                        `);
                    } else {
                        row.append(`<td>-</td>`);
                    }
                }
                
                // Add meta column with 0 if there's an error
                row.append(`<td class="fw-bold">${formatCurrency(0)}</td>`);
                
                tbody.append(row);
            });
        });
    }
    
    async loadMetasForYear(ano) {
        try {
            const response = await fetch(`/financeiro/faturamento/api/metas?ano=${ano}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            
            // Process metas data
            const metas = {};
            if (Array.isArray(data)) {
                data.forEach(meta => {
                    if (meta && meta.tipo === 'financeiro') {
                        const key = meta.mes || 'anual';
                        metas[key] = meta;
                    }
                });
            }
            
            return metas;
        } catch (error) {
            console.error('Erro ao carregar metas:', error);
            return null;
        }
    }
    
    async loadGeralProporcao() {
        try {
            const response = await fetch(`/financeiro/faturamento/api/geral/proporcao?ano=${this.currentAno}`);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Erro ao carregar dados de proporção');
            }
            
            this.renderChartProporcao(data.setores);
            this.renderChartMetaRealizacao(data.meta);
        } catch (error) {
            console.error('Erro ao carregar gráficos de proporção:', error);
        }
    }
    
    renderChartProporcao(setores) {
        const ctx = document.getElementById('chart-proporcao-faturamento');
        if (!ctx) {
            console.error('Chart context not found');
            return;
        }
        
        const ctx2d = ctx.getContext('2d');
        if (!ctx2d) {
            console.error('Unable to get 2D context');
            return;
        }
        
        // Destruir gráfico anterior se existir
        if (this.charts.proporcao) {
            this.charts.proporcao.destroy();
        }
        
        // Check if setores data exists
        if (!setores) {
            console.error('Setores data is missing');
            return;
        }
        
        const labels = ['Importação', 'Consultoria', 'Exportação'];
        const valores = [
            (setores.importacao && setores.importacao.valor) || 0,
            (setores.consultoria && setores.consultoria.valor) || 0,
            (setores.exportacao && setores.exportacao.valor) || 0
        ];
        const percentuais = [
            (setores.importacao && setores.importacao.percentual) || 0,
            (setores.consultoria && setores.consultoria.percentual) || 0,
            (setores.exportacao && setores.exportacao.percentual) || 0
        ];
        
        // Calculate total for determining small values
        const total = valores.reduce((sum, value) => sum + (typeof value === 'object' ? 0 : value), 0);
        const threshold = total * 0.05; // 5% threshold for hiding labels
        
        this.charts.proporcao = new Chart(ctx2d, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: valores,
                    backgroundColor: [
                        'rgba(40, 167, 69, 0.8)',
                        'rgba(23, 162, 184, 0.8)',
                        'rgba(108, 117, 125, 0.8)'
                    ],
                    borderColor: [
                        'rgba(40, 167, 69, 1)',
                        'rgba(23, 162, 184, 1)',
                        'rgba(108, 117, 125, 1)'
                    ],
                    borderWidth: 2,
                    // Explode small slices
                    offset: valores.map(value => {
                        const numericValue = typeof value === 'object' ? 0 : value;
                        return numericValue < threshold ? 20 : 0;
                    })
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
                                const value = context.raw || 0;
                                // Ensure value is a number
                                const numericValue = typeof value === 'object' ? 0 : value;
                                const dataIndex = context.dataIndex;
                                if (dataIndex < percentuais.length) {
                                    const percent = percentuais[dataIndex] || 0;
                                    // Ensure percent is a number
                                    const numericPercent = typeof percent === 'object' ? 0 : percent;
                                    return `${label}: ${formatCurrency(numericValue)} (${numericPercent.toFixed(1)}%)`;
                                }
                                return `${label}: ${formatCurrency(numericValue)}`;
                            }
                        }
                    },
                    // Add data labels plugin
                    datalabels: {
                        formatter: (value, ctx) => {
                            // Ensure value is a number
                            const numericValue = typeof value === 'object' ? 0 : value;
                            if (numericValue === null || numericValue === undefined) return '';
                            
                            // Hide labels for very small values
                            if (numericValue < threshold) return '';
                            
                            const dataIndex = ctx.dataIndex;
                            if (dataIndex < percentuais.length) {
                                const percent = percentuais[dataIndex] || 0;
                                // Ensure percent is a number
                                const numericPercent = typeof percent === 'object' ? 0 : percent;
                                return `${numericPercent.toFixed(1)}%\n${formatCurrencyShort(numericValue)}`;
                            }
                            return formatCurrencyShort(numericValue);
                        },
                        color: '#fff',
                        font: {
                            weight: 'bold',
                            size: 12
                        },
                        textAlign: 'center'
                    }
                }
            },
            plugins: [ChartDataLabels] // Add the data labels plugin
        });
    }
    
    renderChartMetaRealizacao(meta) {
        const ctx = document.getElementById('chart-meta-realizacao');
        if (!ctx) {
            console.error('Chart context not found');
            return;
        }
        
        const ctx2d = ctx.getContext('2d');
        if (!ctx2d) {
            console.error('Unable to get 2D context');
            return;
        }
        
        // Destruir gráfico anterior se existir
        if (this.charts.meta) {
            this.charts.meta.destroy();
        }
        
        // Check if meta data exists
        if (!meta) {
            console.error('Meta data is missing');
            return;
        }
        
        // Calculate percentages
        const faturadoValor = (meta.faturado && meta.faturado.valor) || 0;
        const aRealizarValor = (meta.a_realizar && meta.a_realizar.valor) || 0;
        // Ensure values are numbers
        const numericFaturado = typeof faturadoValor === 'object' ? 0 : faturadoValor;
        const numericARealizar = typeof aRealizarValor === 'object' ? 0 : aRealizarValor;
        const total = numericFaturado + numericARealizar;
        const faturadoPercent = total > 0 ? (numericFaturado / total * 100) : 0;
        const aRealizarPercent = total > 0 ? (numericARealizar / total * 100) : 0;
        
        // Create a gauge chart instead of pie chart
        this.charts.meta = new Chart(ctx2d, {
            type: 'doughnut',
            data: {
                labels: ['Faturado', 'A Realizar'],
                datasets: [{
                    data: [numericFaturado, numericARealizar],
                    backgroundColor: [
                        numericFaturado > 0 ? 'rgba(40, 167, 69, 0.8)' : 'rgba(220, 53, 69, 0.8)',
                        numericARealizar > 0 ? 'rgba(255, 193, 7, 0.8)' : 'rgba(200, 200, 200, 0.8)'
                    ],
                    borderColor: [
                        numericFaturado > 0 ? 'rgba(40, 167, 69, 1)' : 'rgba(220, 53, 69, 1)',
                        numericARealizar > 0 ? 'rgba(255, 193, 7, 1)' : 'rgba(200, 200, 200, 1)'
                    ],
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                rotation: 270, // Start from top
                circumference: 180, // Half circle
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
                                const value = context.raw || 0;
                                // Ensure value is a number
                                const numericValue = typeof value === 'object' ? 0 : value;
                                const total = context.dataset.data.reduce((a, b) => {
                                    const aValue = typeof a === 'object' ? 0 : a;
                                    const bValue = typeof b === 'object' ? 0 : b;
                                    return (aValue || 0) + (bValue || 0);
                                }, 0);
                                const percent = total > 0 ? ((numericValue / total) * 100).toFixed(1) : '0.0';
                                return `${label}: ${formatCurrency(numericValue)} (${percent}%)`;
                            }
                        }
                    },
                    title: {
                        display: true,
                        text: `Meta: ${formatCurrency(numericFaturado + numericARealizar)}`,
                        font: {
                            size: 14
                        }
                    },
                    // Add data labels plugin
                    datalabels: {
                        formatter: (value, ctx) => {
                            // Ensure value is a number
                            const numericValue = typeof value === 'object' ? 0 : value;
                            if (numericValue === null || numericValue === undefined || numericValue === 0) return '';
                            const total = ctx.dataset.data.reduce((a, b) => {
                                const aValue = typeof a === 'object' ? 0 : a;
                                const bValue = typeof b === 'object' ? 0 : b;
                                return (aValue || 0) + (bValue || 0);
                            }, 0);
                            const percent = total > 0 ? ((numericValue / total) * 100).toFixed(1) : '0.0';
                            return `${formatCurrencyShort(numericValue)}\n${percent}%`;
                        },
                        color: '#fff',
                        font: {
                            weight: 'bold',
                            size: 12
                        },
                        textAlign: 'center'
                    }
                }
            },
            plugins: [ChartDataLabels] // Add the data labels plugin
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
            this.showError('Erro ao carregar dados do setor: ' + error.message);
        }
    }
    
    updateSetorKPIs(kpis) {
        // Faturamento Total [Setor]
        $('#valor-faturamento-setor').text(formatCurrencyShort(kpis.faturamento_total));
        
        // % [Setor] - Make it clearer what this percentage represents
        $('#valor-percentual-setor').html(`${kpis.percentual_participacao.toFixed(1)}%<br><small class="text-muted">do faturamento total</small>`);
    }
    
    renderSetorChart(data) {
        const ctx = document.getElementById('chart-faturamento-setor').getContext('2d');
        
        // Destruir gráfico anterior se existir
        if (this.charts.setor) {
            this.charts.setor.destroy();
        }
        
        // Preparar dados para o gráfico - Correctly interpret the backend data
        const months = [];
        const currentPeriodData = [];
        const previousPeriodData = [];
        
        // Extract unique months and sort them
        const monthKeys = [...new Set(data.map(item => item.mes))].sort();
        
        // Create month labels and populate data arrays
        monthKeys.forEach(monthKey => {
            const monthData = data.find(item => item.mes === monthKey);
            if (monthData) {
                // Format month label (e.g., "2024-01" -> "jan/24")
                const [year, month] = monthKey.split('-');
                const monthName = new Date(year, month - 1, 1).toLocaleDateString('pt-BR', { month: 'short' });
                months.push(`${monthName}/${year.slice(2)}`);
                
                // Use the values as sent from backend
                // faturamento = current period value
                // faturamento_anterior = previous period value for the same month
                currentPeriodData.push(monthData.faturamento || 0);
                previousPeriodData.push(monthData.faturamento_anterior || 0);
            }
        });
        
        this.charts.setor = new Chart(ctx, {
            type: 'line',
            data: {
                labels: months,
                datasets: [{
                    label: 'Período Atual',
                    data: currentPeriodData,
                    borderColor: 'rgba(40, 167, 69, 1)',
                    backgroundColor: 'rgba(40, 167, 69, 0.1)',
                    borderWidth: 3,
                    fill: false,
                    tension: 0.4,
                    pointBackgroundColor: 'rgba(40, 167, 69, 1)',
                    pointBorderColor: 'white',
                    pointBorderWidth: 2,
                    pointRadius: 6
                }, {
                    label: 'Mesmo Período Anterior',
                    data: previousPeriodData,
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
                plugins: {
                    legend: {
                        position: 'top',
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
                        },
                        title: {
                            display: true,
                            text: 'Valor (R$)',
                            font: {
                                size: 12,
                                weight: 'bold'
                            }
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        },
                        title: {
                            display: true,
                            text: 'Período',
                            font: {
                                size: 12,
                                weight: 'bold'
                            }
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
    
    // Metas Management Functions
    async loadMetas() {
        try {
            const response = await fetch(`/financeiro/faturamento/api/metas`);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Erro ao carregar metas');
            }
            
            this.renderMetasTable(data);
        } catch (error) {
            console.error('Erro ao carregar metas:', error);
        }
    }
    
    renderMetasTable(metas) {
        const tbody = $('#metas-table-body');
        tbody.empty();
        
        // Filter to show only 2025 data
        const metas2025 = metas.filter(meta => meta.ano === '2025' && meta.tipo === 'financeiro');
        
        if (metas2025.length === 0) {
            tbody.append(`
                <tr>
                    <td colspan="14" class="text-center text-muted">
                        Nenhuma meta cadastrada para 2025.
                    </td>
                </tr>
            `);
            return;
        }
        
        // Group metas by year (should only be 2025)
        const metasByYear = {};
        metas2025.forEach(meta => {
            const year = meta.ano;
            if (!metasByYear[year]) {
                metasByYear[year] = {};
            }
            // Store meta value by month (or 'anual' for annual metas)
            const monthKey = meta.mes || 'anual';
            metasByYear[year][monthKey] = meta;
        });
        
        // Create rows for each year (should only be 2025)
        Object.keys(metasByYear).sort((a, b) => b - a).forEach(year => {
            const yearMetas = metasByYear[year];
            const row = $('<tr></tr>');
            
            // Year column
            row.append(`<td>${year}</td>`);
            
            // Monthly columns (January to December)
            for (let month = 1; month <= 12; month++) {
                const monthKey = month.toString().padStart(2, '0');
                const meta = yearMetas[monthKey];
                
                if (meta) {
                    row.append(`<td>${formatCurrency(meta.meta)} <button class="btn btn-sm btn-danger delete-meta ms-2" data-id="${meta.id}"><i class="mdi mdi-delete"></i></button></td>`);
                } else {
                    row.append(`<td>-</td>`);
                }
            }
            
            // Annual column
            const annualMeta = yearMetas['anual'];
            if (annualMeta) {
                row.append(`<td>${formatCurrency(annualMeta.meta)} <button class="btn btn-sm btn-danger delete-meta ms-2" data-id="${annualMeta.id}"><i class="mdi mdi-delete"></i></button></td>`);
            } else {
                row.append(`<td>-</td>`);
            }
            
            // Actions column (empty for now)
            row.append(`<td></td>`);
            
            tbody.append(row);
        });
        
        // Add event listeners for delete buttons
        $('.delete-meta').on('click', (e) => {
            const id = $(e.target).closest('.delete-meta').data('id');
            this.deleteMeta(id);
        });
    }
    
    openMetasModal() {
        $('#metas-modal').show();
        $('#meta-ano').val(this.currentAno);
        // Set current month
        const currentMonth = String(new Date().getMonth() + 1).padStart(2, '0');
        $('#meta-mes').val(currentMonth);
        this.loadMetas();
    }
    
    closeMetasModal() {
        $('#metas-modal').hide();
    }
    
    async saveMeta() {
        const ano = $('#meta-ano').val();
        const mes = $('#meta-mes').val();
        const valor = $('#meta-valor').val();
        
        if (!ano || !valor) {
            this.showError('Por favor, preencha todos os campos obrigatórios (Ano e Valor).');
            return;
        }
        
        try {
            const response = await fetch('/financeiro/faturamento/api/metas', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    ano: ano,
                    mes: mes,
                    meta: parseFloat(valor)
                })
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Erro ao salvar meta');
            }
            
            this.showSuccess('Meta salva com sucesso!');
            $('#meta-valor').val('');
            this.loadMetas();
            this.loadData(); // Reload data to update KPIs
        } catch (error) {
            console.error('Erro ao salvar meta:', error);
            this.showError('Erro ao salvar meta: ' + error.message);
        }
    }
    
    async deleteMeta(id) {
        if (!confirm('Tem certeza que deseja excluir esta meta?')) {
            return;
        }
        
        try {
            const response = await fetch(`/financeiro/faturamento/api/metas/${id}`, {
                method: 'DELETE'
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Erro ao excluir meta');
            }
            
            this.showSuccess('Meta excluída com sucesso!');
            this.loadMetas();
            this.loadData(); // Reload data to update KPIs
        } catch (error) {
            console.error('Erro ao excluir meta:', error);
            this.showError('Erro ao excluir meta: ' + error.message);
        }
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
        alert('Erro: ' + message); // Temporário - substituir por toast/notification
    }
    
    showSuccess(message) {
        // Implementar notificação de sucesso
        console.log('Sucesso: ' + message);
        alert('Sucesso: ' + message); // Temporário - substituir por toast/notification
    }
}

// Funções utilitárias
function formatCurrency(value) {
    // Check if value is null, undefined, or not a number
    if (value === null || value === undefined || isNaN(value) || typeof value !== 'number') {
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
    // Check if value is null, undefined, or not a number
    if (value === null || value === undefined || isNaN(value) || typeof value !== 'number') {
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
    
    const formattedValue = (absValue / divisor).toLocaleString('pt-BR', {
        minimumFractionDigits: 0,
        maximumFractionDigits: maxDecimals
    });
    
    return `R$ ${formattedValue}${suffix}`;
}

// Incluir o plugin de data labels do Chart.js
const ChartDataLabels = {
    id: 'ChartDataLabels',
    afterDatasetsDraw(chart) {
        const { ctx, data, chartArea: { top, bottom, left, right, width, height }, scales: { x, y } } = chart;
        
        ctx.save();
        
        data.datasets.forEach((dataset, i) => {
            const meta = chart.getDatasetMeta(i);
            
            meta.data.forEach((datapoint, index) => {
                const { x, y } = datapoint.tooltipPosition();
                
                // Format the value
                const value = dataset.data[index];
                // Ensure value is a number
                const numericValue = typeof value === 'object' ? 0 : value;
                if (numericValue === 0 || numericValue === null || numericValue === undefined) return;
                
                // Check if there's a custom formatter in the options
                let formattedValue = numericValue;
                if (chart.options.plugins && chart.options.plugins.datalabels && chart.options.plugins.datalabels.formatter) {
                    try {
                        formattedValue = chart.options.plugins.datalabels.formatter(numericValue, { dataIndex: index, dataset });
                    } catch (e) {
                        formattedValue = formatCurrencyShort(numericValue);
                    }
                } else {
                    formattedValue = formatCurrencyShort(numericValue);
                }
                
                // Style
                ctx.font = 'bold 12px sans-serif';
                ctx.fillStyle = chart.options.plugins && chart.options.plugins.datalabels && chart.options.plugins.datalabels.color ? 
                    chart.options.plugins.datalabels.color : '#fff';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                
                // Draw text
                ctx.fillText(formattedValue, x, y - 10);
            });
        });
        
        ctx.restore();
    }
};

// Inicializar controlador após o carregamento do DOM
document.addEventListener('DOMContentLoaded', function() {
    window.faturamentoController = new FaturamentoController();
});