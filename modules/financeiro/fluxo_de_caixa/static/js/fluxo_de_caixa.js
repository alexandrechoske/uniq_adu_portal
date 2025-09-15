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

// Debounce function
function debounce(func, wait, immediate) {
    let timeout;
    return function executedFunction() {
        const context = this;
        const args = arguments;
        const later = function() {
            timeout = null;
            if (!immediate) func.apply(context, args);
        };
        const callNow = immediate && !timeout;
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
        if (callNow) func.apply(context, args);
    };
}

class FluxoCaixaController {
    constructor() {
        this.currentAno = new Date().getFullYear();
        this.currentMes = null; // Changed to null for year-only default
        this.currentPage = 1;
        this.pageLimit = 25;
        this.currentDrillCentro = null; // For drill-down level 1
        this.currentDrillCategoria = null; // For drill-down level 2
        this.drillLevel = 1; // Track current drill level (1=Centro, 2=Categoria, 3=Classe)
        
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
        // Register ChartJS plugins
        if (typeof Chart !== 'undefined' && typeof ChartDataLabels !== 'undefined') {
            Chart.register(ChartDataLabels);
        }
        
        this.setupEventListeners();
        this.populateYearSelect();
        this.setInitialMonth();
        this.loadData();
    }
    
    setupEventListeners() {
        // Filtros
        $('#open-filters').on('click', () => this.openFiltersModal());
        $('#close-modal').on('click', () => this.closeFiltersModal());
        $('#apply-filters').on('click', () => this.applyFilters());
        $('#clear-filters').on('click', () => this.resetFilters());
        
        // Paginação da tabela
        $('#btn-prev-page').on('click', () => this.changePage(this.currentPage - 1));
        $('#btn-next-page').on('click', () => this.changePage(this.currentPage + 1));
        
        // Busca na tabela
        $('#search-table').on('input', debounce(() => this.loadTableData(), 300));
        
        // Drill-down button for expenses chart
        $('#btn-voltar-categorias').on('click', () => this.voltarNivelAnterior());
        
        // Fechar modal ao clicar fora
        $('#filter-modal').on('click', (e) => {
            if (e.target.id === 'filter-modal') {
                this.closeFiltersModal();
            }
        });
    }
    
    populateYearSelect() {
        const currentYear = new Date().getFullYear();
        const select = $('#ano-select');
        
        // Adicionar anos de 2015 até o ano atual
        for (let year = 2015; year <= currentYear; year++) {
            select.append(`<option value="${year}" ${year === currentYear ? 'selected' : ''}>${year}</option>`);
        }
    }
    
    setInitialMonth() {
        // Set to empty (year-only) by default
        $('#mes-select').val('');
    }
    
    async loadData(retryCount = 0) {
        this.showLoading(true);
        this.updateFilterSummary();
        
        try {
            // Load data in parallel but handle errors individually
            const kpisPromise = this.loadKPIs().catch(error => {
                console.error('Erro ao carregar KPIs:', error);
                this.showError('Erro ao carregar KPIs. Os valores serão exibidos como "Erro ao carregar".');
                return null;
            });
            
            const fluxoMensalPromise = this.loadFluxoMensal().catch(error => {
                console.error('Erro ao carregar fluxo mensal:', error);
                return null;
            });
            
            const despesasCategoriaPromise = this.loadDespesasCategoria().catch(error => {
                console.error('Erro ao carregar despesas por categoria:', error);
                return null;
            });
            
            const projecaoPromise = this.loadProjecao().catch(error => {
                console.error('Erro ao carregar projeção:', error);
                return null;
            });
            
            const saldoAcumuladoPromise = this.loadSaldoAcumulado().catch(error => {
                console.error('Erro ao carregar saldo acumulado:', error);
                return null;
            });
            
            const tableDataPromise = this.loadTableData().catch(error => {
                console.error('Erro ao carregar dados da tabela:', error);
                return null;
            });
            
            // Wait for all promises to complete
            await Promise.all([
                kpisPromise,
                fluxoMensalPromise,
                despesasCategoriaPromise,
                projecaoPromise,
                saldoAcumuladoPromise,
                tableDataPromise
            ]);
        } catch (error) {
            console.error('Erro ao carregar dados:', error);
            
            // Retry logic for temporary failures
            if (retryCount < 2) {
                console.log(`Tentando novamente... (${retryCount + 1}/3)`);
                setTimeout(() => {
                    this.loadData(retryCount + 1);
                }, 2000); // Wait 2 seconds before retry
                return;
            }
            
            this.showError('Erro ao carregar dados. Tente novamente.');
        } finally {
            this.showLoading(false);
        }
    }
    
    updateFilterSummary() {
        let text = `Vendo dados de ${this.currentAno}`;
        if (this.currentMes) {
            const mesNames = ['', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 
                             'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];
            text += `/${mesNames[this.currentMes]}`;
        }
        $('#filter-summary-text').text(text);
    }
    
    async loadKPIs() {
        try {
            // For KPIs, when no month is selected, we show year-to-date data
            const mesParam = this.currentMes ? `&mes=${this.currentMes}` : '';
            const response = await fetch(`/financeiro/fluxo-de-caixa/api/kpis?ano=${this.currentAno}${mesParam}`);
            const data = await response.json();
            
            if (!response.ok || data.error) {
                throw new Error(data.error || 'Erro ao carregar KPIs');
            }
            
            this.updateKPIs(data);
        } catch (error) {
            console.error('Erro ao carregar KPIs:', error);
            this.showError('Erro ao carregar KPIs: ' + (error.message || 'Erro desconhecido'));
            // Update KPIs with error message
            this.updateKPIsWithError();
        }
    }

    updateKPIsWithError() {
        // Show error state in KPIs
        const errorText = 'Erro ao carregar';
        
        $('#valor-entradas-mes').text(errorText);
        $('#var-entradas-mes').text('');
        
        $('#valor-saidas-mes').text(errorText);
        $('#var-saidas-mes').text('');
        
        $('#valor-resultado-mes').text(errorText);
        $('#var-resultado-mes').text('');
        
        $('#valor-saldo-acumulado').text(errorText);
        $('#var-saldo-acumulado').text('');
    }
    
    updateKPIs(data) {
        // KPI 1: Entradas no Mês/Ano
        $('#valor-entradas-mes').text(formatCurrencyShort(data.entradas_mes.valor));
        this.updateVariation('#var-entradas-mes', data.entradas_mes.variacao);
        this.updateKPICardColor('#kpi-entradas-mes', data.entradas_mes.valor);
        
        // KPI 2: Saídas no Mês/Ano
        $('#valor-saidas-mes').text(formatCurrencyShort(data.saidas_mes.valor));
        this.updateVariation('#var-saidas-mes', data.saidas_mes.variacao);
        this.updateKPICardColor('#kpi-saidas-mes', -data.saidas_mes.valor); // Negative value for expenses
        
        // KPI 3: Resultado do Mês/Ano
        $('#valor-resultado-mes').text(formatCurrencyShort(data.resultado_mes.valor));
        this.updateVariation('#var-resultado-mes', data.resultado_mes.variacao);
        this.updateKPICardColor('#kpi-resultado-mes', data.resultado_mes.valor);
        
        // KPI 4: Saldo Acumulado Final
        $('#valor-saldo-acumulado').text(formatCurrencyShort(data.saldo_acumulado.valor));
        this.updateVariation('#var-saldo-acumulado', data.saldo_acumulado.variacao);
        this.updateKPICardColor('#kpi-saldo-acumulado', data.saldo_acumulado.valor);
    }
    
    updateVariation(selector, variation) {
        // Remove variation display as requested - we don't have previous period data
        const element = $(selector);
        element.text('');
        element.removeClass('variation-positive variation-negative variation-neutral');
    }
    
    updateKPICardColor(cardSelector, value) {
        const card = $(cardSelector);
        card.removeClass('kpi-success kpi-danger kpi-warning kpi-primary');
        
        if (value > 0) {
            card.addClass('kpi-success');
        } else if (value < 0) {
            card.addClass('kpi-danger');
        } else {
            card.addClass('kpi-warning');
        }
    }
    
    async loadFluxoMensal() {
        try {
            const response = await fetch(`/financeiro/fluxo-de-caixa/api/fluxo-mensal?ano=${this.currentAno}`);
            const data = await response.json();
            
            if (!response.ok || data.error) {
                throw new Error(data.error || 'Erro ao carregar fluxo mensal');
            }
            
            this.renderFluxoMensalChart(data);
        } catch (error) {
            console.error('Erro ao carregar fluxo mensal:', error);
            this.showError('Erro ao carregar fluxo mensal: ' + (error.message || 'Erro desconhecido'));
            // Render error state in chart
            this.renderFluxoMensalChartError();
        }
    }

    renderFluxoMensalChartError() {
        const ctx = document.getElementById('chart-fluxo-mensal').getContext('2d');
        
        if (this.charts.fluxoMensal) {
            this.charts.fluxoMensal.destroy();
        }
        
        // Create a simple error message chart
        this.charts.fluxoMensal = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Erro'],
                datasets: [{
                    label: 'Erro ao carregar dados',
                    data: [1],
                    backgroundColor: 'rgba(220, 53, 69, 0.8)',
                    borderColor: 'rgba(220, 53, 69, 1)',
                    borderWidth: 2
                }]
            },
            options: {
                ...this.chartDefaults,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        enabled: false
                    }
                },
                scales: {
                    y: {
                        display: false
                    },
                    x: {
                        display: false
                    }
                }
            }
        });
    }
    
    renderFluxoMensalChart(data) {
        const ctx = document.getElementById('chart-fluxo-mensal').getContext('2d');
        
        if (this.charts.fluxoMensal) {
            this.charts.fluxoMensal.destroy();
        }
        
        // Cores baseadas no valor do resultado líquido (verde para positivo, vermelho para negativo)
        const backgroundColors = data.resultados.map(value => 
            value >= 0 ? 'rgba(40, 167, 69, 0.8)' : 'rgba(220, 53, 69, 0.8)'
        );
        const borderColors = data.resultados.map(value => 
            value >= 0 ? 'rgba(40, 167, 69, 1)' : 'rgba(220, 53, 69, 1)'
        );
        
        // Find the min and max values for proper scaling
        const minValue = Math.min(...data.resultados);
        const maxValue = Math.max(...data.resultados);
        const range = maxValue - minValue;
        const minPadded = minValue - (range * 0.1);
        const maxPadded = maxValue + (range * 0.1);
        
        // Create bar chart for fluxo mensal
        this.charts.fluxoMensal = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.meses,
                datasets: [{
                    label: 'Resultado Líquido',
                    data: data.resultados,
                    backgroundColor: backgroundColors,
                    borderColor: borderColors,
                    borderWidth: 2,
                    borderRadius: 6,
                    borderSkipped: false
                }]
            },
            options: {
                ...this.chartDefaults,
                plugins: {
                    ...this.chartDefaults.plugins,
                    title: {
                        display: true,
                        text: 'Fluxo de Caixa Mês a Mês'
                    },
                    datalabels: {
                        display: true,
                        anchor: 'end',
                        align: 'top',
                        formatter: function(value) {
                            return formatCurrencyShort(value);
                        },
                        color: '#212529',
                        backgroundColor: 'rgba(255, 255, 255, 0.9)',
                        borderColor: '#dee2e6',
                        borderWidth: 1,
                        borderRadius: 4,
                        padding: {
                            top: 4,
                            bottom: 4,
                            left: 6,
                            right: 6
                        },
                        font: {
                            size: 11,
                            weight: 'bold'
                        }
                    }
                },
                scales: {
                    y: {
                        min: minPadded,
                        max: maxPadded,
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
    
    async loadDespesasCategoria() {
        try {
            // Build parameters for drill-down levels
            const params = {
                ano: this.currentAno
            };
            
            if (this.currentMes) {
                params.mes = this.currentMes;
            }
            
            if (this.currentDrillCentro) {
                params.centro_resultado = this.currentDrillCentro;
            }
            
            if (this.currentDrillCategoria) {
                params.categoria = this.currentDrillCategoria;
            }
            
            const queryString = new URLSearchParams(params).toString();
            const response = await fetch(`/financeiro/fluxo-de-caixa/api/despesas-categoria?${queryString}`);
            const data = await response.json();
            
            if (!response.ok || data.error) {
                throw new Error(data.error || 'Erro ao carregar despesas por categoria');
            }
            
            this.renderDespesasCategoriaChart(data);
        } catch (error) {
            console.error('Erro ao carregar despesas por categoria:', error);
            this.showError('Erro ao carregar despesas por categoria: ' + (error.message || 'Erro desconhecido'));
            // Render error state in chart
            this.renderDespesasCategoriaChartError();
        }
    }

    renderDespesasCategoriaChartError() {
        const ctx = document.getElementById('chart-despesas-categoria').getContext('2d');
        
        if (this.charts.despesasCategoria) {
            this.charts.despesasCategoria.destroy();
        }
        
        // Create a simple error message chart
        this.charts.despesasCategoria = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Erro'],
                datasets: [{
                    label: 'Erro ao carregar dados',
                    data: [1],
                    backgroundColor: 'rgba(220, 53, 69, 0.8)',
                    borderColor: 'rgba(220, 53, 69, 1)',
                    borderWidth: 2
                }]
            },
            options: {
                ...this.chartDefaults,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        enabled: false
                    }
                },
                scales: {
                    y: {
                        display: false
                    },
                    x: {
                        display: false
                    }
                }
            }
        });
    }
    
    renderDespesasCategoriaChart(data) {
        const ctx = document.getElementById('chart-despesas-categoria').getContext('2d');
        
        if (this.charts.despesasCategoria) {
            this.charts.despesasCategoria.destroy();
        }
        
        // Update chart title and drill-down button visibility based on drill level
        const chartTitle = data.drill_title || 'Despesas por Centro de Resultado';
        $('#chart-despesas-title').text(chartTitle);
        
        // Show/hide back button based on drill level
        if (data.drill_level > 1) {
            $('#btn-voltar-categorias').show();
        } else {
            $('#btn-voltar-categorias').hide();
        }
        
        // Convert negative values to positive for better visualization
        const valoresPositivos = data.valores.map(valor => Math.abs(valor));
        
        // For horizontal bar chart, we need to swap x and y axes
        this.charts.despesasCategoria = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.labels,
                datasets: [{
                    label: chartTitle,
                    data: valoresPositivos,
                    backgroundColor: valoresPositivos.map(() => 'rgba(111, 66, 193, 0.8)'),
                    borderColor: valoresPositivos.map(() => 'rgba(111, 66, 193, 1)'),
                    borderWidth: 2,
                    borderRadius: 6,
                    borderSkipped: false
                }]
            },
            options: {
                ...this.chartDefaults,
                indexAxis: 'y', // This makes it horizontal
                onClick: (event, elements) => {
                    // Add drill-down functionality when clicking on bars
                    if (elements.length > 0) {
                        const elementIndex = elements[0].index;
                        const selectedItem = data.labels[elementIndex];
                        this.handleDrillDown(selectedItem, data.drill_level);
                    }
                },
                plugins: {
                    ...this.chartDefaults.plugins,
                    title: {
                        display: true,
                        text: chartTitle
                    },
                    legend: {
                        display: false
                    },
                    datalabels: {
                        display: true,
                        anchor: 'end',
                        align: 'right',
                        formatter: function(value) {
                            return formatCurrencyShort(value);
                        },
                        color: '#212529',
                        backgroundColor: 'rgba(255, 255, 255, 0.9)',
                        borderColor: '#dee2e6',
                        borderWidth: 1,
                        borderRadius: 4,
                        padding: {
                            top: 4,
                            bottom: 4,
                            left: 6,
                            right: 6
                        },
                        font: {
                            size: 10,
                            weight: 'bold'
                        }
                    },
                    tooltip: {
                        ...this.chartDefaults.plugins.tooltip,
                        callbacks: {
                            label: function(context) {
                                let value = context.parsed.x || context.parsed;
                                return context.dataset.label + ': ' + formatCurrency(value);
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
                                // Show formatted currency values in the axis labels
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
    
    async loadSaldoAcumulado() {
        try {
            const queryString = new URLSearchParams({
                ano: this.currentAno,
                ...(this.currentMes && { mes: this.currentMes })
            });
            
            const response = await fetch(`/financeiro/fluxo-de-caixa/api/saldo-acumulado?${queryString}`);
            const data = await response.json();
            
            if (!response.ok || data.error) {
                throw new Error(data.error || 'Erro ao carregar evolução do saldo acumulado');
            }
            
            this.renderSaldoAcumuladoChart(data);
        } catch (error) {
            console.error('Erro ao carregar saldo acumulado:', error);
            this.showError('Erro ao carregar evolução do saldo acumulado: ' + (error.message || 'Erro desconhecido'));
            // Render error state in chart
            this.renderSaldoAcumuladoChartError();
        }
    }

    renderSaldoAcumuladoChartError() {
        const ctx = document.getElementById('chart-saldo-acumulado').getContext('2d');
        
        // Ensure proper cleanup before creating new chart
        if (this.charts.saldoAcumulado) {
            this.charts.saldoAcumulado.destroy();
            delete this.charts.saldoAcumulado;
        }
        
        // Clear any existing chart instance on the canvas
        const chartInstance = Chart.getChart(ctx);
        if (chartInstance) {
            chartInstance.destroy();
        }
        
        // Create a simple error message chart
        this.charts.saldoAcumulado = new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['Erro'],
                datasets: [{
                    label: 'Erro ao carregar dados',
                    data: [1],
                    backgroundColor: 'rgba(220, 53, 69, 0.8)',
                    borderColor: 'rgba(220, 53, 69, 1)',
                    borderWidth: 2
                }]
            },
            options: {
                ...this.chartDefaults,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        enabled: false
                    }
                },
                scales: {
                    y: {
                        display: false
                    },
                    x: {
                        display: false
                    }
                }
            }
        });
    }
    
    renderSaldoAcumuladoChart(data) {
        const ctx = document.getElementById('chart-saldo-acumulado').getContext('2d');
        
        // Ensure proper cleanup before creating new chart
        if (this.charts.saldoAcumulado) {
            this.charts.saldoAcumulado.destroy();
            delete this.charts.saldoAcumulado;
        }
        
        // Clear any existing chart instance on the canvas
        const chartInstance = Chart.getChart(ctx);
        if (chartInstance) {
            chartInstance.destroy();
        }
        
        // Find min and max values for proper scaling
        const allValues = data.saldos.filter(val => val !== null);
        const minValue = Math.min(...allValues);
        const maxValue = Math.max(...allValues);
        const range = maxValue - minValue;
        const minPadded = minValue - (range * 0.1);
        const maxPadded = maxValue + (range * 0.1);
        
        // Define colors based on positive/negative values
        const borderColors = data.saldos.map(value => 
            value >= 0 ? 'rgba(40, 167, 69, 1)' : 'rgba(220, 53, 69, 1)'
        );
        
        this.charts.saldoAcumulado = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.datas,
                datasets: [{
                    label: 'Saldo Acumulado',
                    data: data.saldos,
                    borderColor: 'rgba(0, 123, 255, 1)',
                    backgroundColor: 'rgba(0, 123, 255, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: borderColors,
                    pointBorderColor: 'white',
                    pointBorderWidth: 2,
                    pointRadius: 3
                }]
            },
            options: {
                ...this.chartDefaults,
                plugins: {
                    ...this.chartDefaults.plugins,
                    title: {
                        display: true,
                        text: 'Evolução do Saldo Acumulado'
                    },
                    legend: {
                        display: false
                    },
                    datalabels: {
                        display: true,
                        anchor: 'end',
                        align: 'top',
                        formatter: function(value, context) {
                            // Validate input data
                            if (value === null || value === undefined || isNaN(value)) {
                                return '';
                            }
                            
                            // Show labels for every 3rd point, first point, and last point to avoid clutter
                            const dataIndex = context.dataIndex;
                            const totalPoints = context.dataset.data.length;
                            
                            if (dataIndex === 0 || 
                                dataIndex === totalPoints - 1 || 
                                dataIndex % 3 === 0) {
                                return formatCurrencyShort(value);
                            }
                            return '';
                        },
                        color: '#212529',
                        backgroundColor: 'rgba(255, 255, 255, 0.9)',
                        borderColor: '#dee2e6',
                        borderWidth: 1,
                        borderRadius: 4,
                        padding: {
                            top: 2,
                            bottom: 2,
                            left: 4,
                            right: 4
                        },
                        font: {
                            size: 9,
                            weight: 'bold'
                        }
                    }
                },
                scales: {
                    y: {
                        min: minPadded,
                        max: maxPadded,
                        grid: {
                            display: true,
                            color: 'rgba(0, 0, 0, 0.1)',
                            drawBorder: false
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
                        },
                        ticks: {
                            maxTicksLimit: 10 // Limit number of x-axis labels
                        }
                    }
                }
            }
        });
    }
    
    async loadProjecao() {
        try {
            const response = await fetch(`/financeiro/fluxo-de-caixa/api/projecao`);
            const data = await response.json();
            
            if (!response.ok || data.error) {
                throw new Error(data.error || 'Erro ao carregar projeção');
            }
            
            this.renderProjecaoChart(data);
        } catch (error) {
            console.error('Erro ao carregar projeção:', error);
            this.showError('Erro ao carregar projeção: ' + (error.message || 'Erro desconhecido'));
            // Render error state in chart
            this.renderProjecaoChartError();
        }
    }

    renderProjecaoChartError() {
        const ctx = document.getElementById('chart-projecao').getContext('2d');
        
        // Ensure proper cleanup before creating new chart
        if (this.charts.projecao) {
            this.charts.projecao.destroy();
            delete this.charts.projecao;
        }
        
        // Clear any existing chart instance on the canvas
        const chartInstance = Chart.getChart(ctx);
        if (chartInstance) {
            chartInstance.destroy();
        }
        
        // Create a simple error message chart
        this.charts.projecao = new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['Erro'],
                datasets: [{
                    label: 'Erro ao carregar dados',
                    data: [1],
                    borderColor: 'rgba(220, 53, 69, 1)',
                    backgroundColor: 'rgba(220, 53, 69, 0.1)',
                    borderWidth: 2,
                    fill: true
                }]
            },
            options: {
                ...this.chartDefaults,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        enabled: false
                    }
                },
                scales: {
                    y: {
                        display: false
                    },
                    x: {
                        display: false
                    }
                }
            }
        });
    }
    
    renderProjecaoChart(data) {
        const ctx = document.getElementById('chart-projecao').getContext('2d');
        
        // Ensure proper cleanup before creating new chart
        if (this.charts.projecao) {
            this.charts.projecao.destroy();
            delete this.charts.projecao;
        }
        
        // Clear any existing chart instance on the canvas
        const chartInstance = Chart.getChart(ctx);
        if (chartInstance) {
            chartInstance.destroy();
        }
        
        // Combine past and future data
        const allDates = [...data.past_dates, ...data.future_dates];
        const allFluxos = [...data.past_values, ...data.future_values];
        
        // Split into past and future for different styling
        const pastCount = data.past_dates.length;
        
        // Find min and max values for proper scaling
        const allValues = [...allFluxos].filter(val => val !== null);
        const minValue = Math.min(...allValues);
        const maxValue = Math.max(...allValues);
        const range = maxValue - minValue;
        const minPadded = minValue - (range * 0.1);
        const maxPadded = maxValue + (range * 0.1);
        
        this.charts.projecao = new Chart(ctx, {
            type: 'line',
            data: {
                labels: allDates,
                datasets: [{
                    label: 'Fluxo de Caixa Real',
                    data: allFluxos.map((value, index) => index < pastCount ? value : null),
                    borderColor: 'rgba(40, 167, 69, 1)',
                    backgroundColor: 'rgba(40, 167, 69, 0.1)',
                    borderWidth: 3,
                    fill: false,
                    tension: 0.4,
                    pointBackgroundColor: 'rgba(40, 167, 69, 1)',
                    pointBorderColor: 'white',
                    pointBorderWidth: 2,
                    pointRadius: 4
                }, {
                    label: 'Fluxo de Caixa Projetado',
                    data: allFluxos.map((value, index) => index >= pastCount ? value : null),
                    borderColor: 'rgba(255, 193, 7, 1)',
                    backgroundColor: 'rgba(255, 193, 7, 0.1)',
                    borderWidth: 3,
                    borderDash: [5, 5], // Dashed line for projection
                    fill: false,
                    tension: 0.4,
                    pointBackgroundColor: 'rgba(255, 193, 7, 1)',
                    pointBorderColor: 'white',
                    pointBorderWidth: 2,
                    pointRadius: 4
                }]
            },
            options: {
                ...this.chartDefaults,
                plugins: {
                    ...this.chartDefaults.plugins,
                    title: {
                        display: true,
                        text: 'Projeção de Fluxo de Caixa - Resultado Líquido'
                    },
                    legend: {
                        labels: {
                            padding: 20,
                            usePointStyle: true,
                            font: {
                                size: 11
                            }
                        }
                    },
                    datalabels: {
                        display: function(context) {
                            // Safe check for valid data points
                            if (!context || !context.parsed) return false;
                            const value = context.parsed.y;
                            return value !== null && value !== undefined && !isNaN(value);
                        },
                        anchor: 'end',
                        align: 'top',
                        formatter: function(value, context) {
                            // Check if this is a valid point with data
                            if (value === null || value === undefined) {
                                return '';
                            }
                            
                            // Show labels for every 4th point, first point, and last point of the dataset
                            const datasetIndex = context.datasetIndex;
                            const dataIndex = context.dataIndex;
                            const dataset = context.dataset;
                            
                            // Find the actual data points (not null) for this dataset
                            const validDataPoints = dataset.data.map((val, idx) => ({ value: val, index: idx }))
                                .filter(item => item.value !== null && item.value !== undefined);
                            
                            // Check if this is a valid data point
                            const currentPointIndex = validDataPoints.findIndex(item => item.index === dataIndex);
                            
                            if (currentPointIndex === -1) return ''; // Not a valid point
                            
                            // Show label if it's every 3rd valid point, first valid point, or last valid point
                            if (currentPointIndex === 0 || 
                                currentPointIndex === validDataPoints.length - 1 || 
                                currentPointIndex % 3 === 0) {
                                return formatCurrencyShort(value);
                            }
                            
                            return '';
                        },
                        color: '#212529',
                        backgroundColor: 'rgba(255, 255, 255, 0.9)',
                        borderColor: '#dee2e6',
                        borderWidth: 1,
                        borderRadius: 4,
                        padding: {
                            top: 2,
                            bottom: 2,
                            left: 4,
                            right: 4
                        },
                        font: {
                            size: 9,
                            weight: 'bold'
                        }
                    }
                },
                scales: {
                    y: {
                        min: minPadded,
                        max: maxPadded,
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
    
    handleDrillDown(selectedItem, currentLevel) {
        if (currentLevel === 1) {
            // Drill down from Centro de Resultado to Categoria
            this.currentDrillCentro = selectedItem;
            this.drillLevel = 2;
        } else if (currentLevel === 2) {
            // Drill down from Categoria to Classe
            this.currentDrillCategoria = selectedItem;
            this.drillLevel = 3;
        }
        // Level 3 (Classe) is the deepest level, no further drill-down
        
        this.loadDespesasCategoria();
    }
    
    voltarNivelAnterior() {
        if (this.drillLevel === 3) {
            // Go back from Classe to Categoria
            this.currentDrillCategoria = null;
            this.drillLevel = 2;
        } else if (this.drillLevel === 2) {
            // Go back from Categoria to Centro de Resultado
            this.currentDrillCentro = null;
            this.drillLevel = 1;
        }
        
        this.loadDespesasCategoria();
    }
    
    drillDownCategoria(categoria) {
        // Legacy function - redirect to new drill-down system
        this.handleDrillDown(categoria, 1);
    }
    
    voltarCategorias() {
        // Legacy function - redirect to new system
        this.voltarNivelAnterior();
    }
    
    async loadTableData() {
        try {
            const searchTerm = $('#search-table').val();
            // When no month is selected, load full year data
            const mesParam = this.currentMes ? `&mes=${this.currentMes}` : '';
            let url = `/financeiro/fluxo-de-caixa/api/tabela-dados?ano=${this.currentAno}${mesParam}&page=${this.currentPage}&limit=${this.pageLimit}`;
            
            // Adicionar parâmetro de busca se fornecido
            if (searchTerm && searchTerm.trim() !== '') {
                url += `&search=${encodeURIComponent(searchTerm.trim())}`;
            }
            
            const response = await fetch(url);
            const data = await response.json();
            
            if (!response.ok || data.error) {
                throw new Error(data.error || 'Erro ao carregar dados da tabela');
            }
            
            this.renderTable(data);
            this.updatePagination(data);
        } catch (error) {
            console.error('Erro ao carregar dados da tabela:', error);
            this.showError('Erro ao carregar dados da tabela: ' + (error.message || 'Erro desconhecido'));
            // Render error state in table
            this.renderTableError();
        }
    }

    renderTableError() {
        const tbody = $('#tabela-dados tbody');
        tbody.empty();
        
        tbody.append(`
            <tr>
                <td colspan="6" class="text-center text-danger">
                    <i class="mdi mdi-alert-circle" style="font-size: 2rem;"></i>
                    <div>Erro ao carregar dados da tabela</div>
                    <small>Por favor, tente novamente mais tarde</small>
                </td>
            </tr>
        `);
    }
    
    renderTable(data) {
        const tbody = $('#tabela-dados tbody');
        tbody.empty();
        
        if (data.dados.length === 0) {
            tbody.append(`
                <tr>
                    <td colspan="6" class="text-center text-muted">
                        Nenhum registro encontrado
                    </td>
                </tr>
            `);
            return;
        }
        
        data.dados.forEach(row => {
            const tipoClass = row.tipo === 'Receita' ? 'text-success' : 'text-danger';
            const valorFormatted = row.tipo === 'Receita' ? 
                formatCurrency(parseFloat(row.valor)) : 
                `-${formatCurrency(parseFloat(row.valor))}`;
            
            tbody.append(`
                <tr>
                    <td>${formatDate(row.data)}</td>
                    <td>${row.categoria || '-'}</td>
                    <td>${row.classe || '-'}</td>
                    <td>${row.codigo || '-'}</td>
                    <td>${row.descricao || '-'}</td>
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
        this.currentAno = parseInt($('#ano-select').val());
        const mesValue = $('#mes-select').val();
        this.currentMes = mesValue ? parseInt(mesValue) : null; // null when no month selected
        
        this.updateFilterSummary();
        
        // Reset drill-down when applying new filters
        this.currentDrillCategoria = null;
        
        // Fechar modal
        this.closeFiltersModal();
        
        // Recarregar dados
        this.loadData();
    }
    
    resetFilters() {
        this.currentAno = new Date().getFullYear();
        this.currentMes = null; // Year-only by default
        this.currentDrillCategoria = null;
        
        $('#ano-select').val(this.currentAno);
        $('#mes-select').val('');
        this.updateFilterSummary();
        
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
        // Create or update error notification
        let errorContainer = document.getElementById('error-notification');
        if (!errorContainer) {
            errorContainer = document.createElement('div');
            errorContainer.id = 'error-notification';
            errorContainer.className = 'alert alert-danger alert-dismissible fade show';
            errorContainer.role = 'alert';
            errorContainer.style.position = 'fixed';
            errorContainer.style.top = '20px';
            errorContainer.style.right = '20px';
            errorContainer.style.zIndex = '9999';
            errorContainer.style.maxWidth = '400px';
            errorContainer.innerHTML = `
                <strong>Erro!</strong> <span class="error-message"></span>
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            `;
            document.body.appendChild(errorContainer);
        }
        
        // Update error message
        const messageElement = errorContainer.querySelector('.error-message');
        if (messageElement) {
            messageElement.textContent = message;
        }
        
        // Show the error
        errorContainer.style.display = 'block';
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            if (errorContainer) {
                errorContainer.style.display = 'none';
            }
        }, 5000);
    }
}

// Initialize the controller when the page loads
document.addEventListener('DOMContentLoaded', function() {
    window.fluxoCaixaController = new FluxoCaixaController();
});