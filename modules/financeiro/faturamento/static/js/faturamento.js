/**
 * Faturamento - JavaScript
 * Sistema de análise de faturamento com gráficos e KPIs
 */

class FaturamentoController {
    constructor() {
        this.currentAno = new Date().getFullYear();
        this.currentSetor = 'importacao';
        this.activeTab = 'visao-geral';
        
        // Initialize filters with default values - buscar todos os anos desde 2015
        this.filters = {
            start_date: '2015-01-01',  // Buscar desde 2015 para ter todos os anos
            end_date: `${this.currentAno}-12-31`,
            empresa: '',
            centro_resultado: '',
            cliente: '',
            mes: ''
        };
        
        // Controle de visualização de anos (padrão: últimos 5 anos)
        this.defaultYearsToShow = 5;
        this.allYears = [];
        this.visibleYears = [];
        this.dataLabelsEnabled = true; // Controle dos rótulos de dados
        
        // Armazenar instâncias dos gráficos
        this.charts = {};
        
        // New chart instances for enhanced dashboard
        this.comparativoChart = null;
        this.sunburstChart = null;
        
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
        this.updateFilterSummary(); // Inicializar resumo de filtros
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
        $('#reset-filters').on('click', () => this.resetFilters());
        
        // Listener para ajustar datas quando ano é selecionado
        $('#ano-select').on('change', (e) => {
            const ano = e.target.value;
            if (ano) {
                $('#start-date').val(`${ano}-01-01`);
                $('#end-date').val(`${ano}-12-31`);
                $('#mes-select').val(''); // Limpar seleção de mês
            }
        });
        
        // Listener para ajustar datas quando mês é selecionado
        $('#mes-select').on('change', (e) => {
            const mes = e.target.value;
            const ano = $('#ano-select').val() || new Date().getFullYear();
            
            if (mes) {
                const ultimoDia = new Date(ano, parseInt(mes), 0).getDate();
                $('#start-date').val(`${ano}-${mes.padStart(2, '0')}-01`);
                $('#end-date').val(`${ano}-${mes.padStart(2, '0')}-${ultimoDia}`);
            } else if ($('#ano-select').val()) {
                // Se limpar mês mas mantém ano, volta para ano completo
                $('#start-date').val(`${ano}-01-01`);
                $('#end-date').val(`${ano}-12-31`);
            }
        });
        
        // Setor filter - Removed as we now load all sectors at once
        // $('#setor-select').on('change', (e) => {
        //     this.currentSetor = e.target.value;
        //     const setorNames = {
        //         'importacao': 'Importação',
        //         'consultoria': 'Consultoria',
        //         'exportacao': 'Exportação'
        //     };
        //     $('#setor-filter-summary-text').text(`Vendo dados do setor de ${setorNames[this.currentSetor]}`);
        //     this.loadSetorData();
        // });
        
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
                    this.loadEnhancedKPIs(),
                    this.loadComparativoAnos(),
                    this.loadSunburstData(),
                    this.loadResumoMensal()
                ]);
            } else if (this.activeTab === 'analise-setor') {
                // Load all sectors data for onepage layout
                await this.loadAllSetoresData();
            }
        } catch (error) {
            console.error('Erro ao carregar dados:', error);
            this.showError('Erro ao carregar dados. Tente novamente.');
        } finally {
            this.showLoading(false);
        }
    }
    
    // Enhanced KPIs for new dashboard
    async loadEnhancedKPIs() {
        try {
            const response = await $.get(`/financeiro/faturamento/api/geral/comparativo_anos?start_date=${this.filters.start_date}&end_date=${this.filters.end_date}&empresa=${this.filters.empresa}&centro_resultado=${this.filters.centro_resultado}&cliente=${this.filters.cliente || ''}`);
            
            if (response.success && response.data) {
                const anos = Object.keys(response.data);
                const anoAtual = Math.max(...anos.map(a => parseInt(a)));
                const anoAnterior = anoAtual - 1;
                
                const dadosAtual = response.data[anoAtual] || [];
                const dadosAnterior = response.data[anoAnterior] || [];
                
                // Totais
                const totalAtual = dadosAtual.reduce((sum, item) => sum + (item.total_valor || 0), 0);
                const totalAnterior = dadosAnterior.reduce((sum, item) => sum + (item.total_valor || 0), 0);
                
                // Growth rate
                const crescimento = totalAnterior > 0 ? ((totalAtual - totalAnterior) / totalAnterior * 100) : 0;
                
                // Mês com maior/menor faturamento
                const melhorMes = dadosAtual.length > 0 ? 
                    dadosAtual.reduce((max, item) => (item.total_valor || 0) > (max.total_valor || 0) ? item : max) : null;
                
                const piorMes = dadosAtual.length > 0 ? 
                    dadosAtual.reduce((min, item) => (item.total_valor || 0) < (min.total_valor || 0) ? item : min) : null;
                
                // Update KPIs
                $('#kpi-total-faturamento').text(formatCurrencyShort(totalAtual));
                $('#kpi-crescimento-anual').text(`${crescimento >= 0 ? '+' : ''}${crescimento.toFixed(1)}%`);
                $('#kpi-crescimento-anual').closest('.kpi-card').removeClass('negative positive').addClass(crescimento >= 0 ? 'positive' : 'negative');
                
                $('#kpi-melhor-mes').text(melhorMes ? this.getMonthName(melhorMes.mes) : 'N/A');
                $('#kpi-pior-mes').text(piorMes ? this.getMonthName(piorMes.mes) : 'N/A');
            }
        } catch (error) {
            console.error('Erro ao carregar KPIs:', error);
        }
    }

    async loadComparativoAnos() {
        try {
            const response = await $.get(`/financeiro/faturamento/api/geral/comparativo_anos?start_date=${this.filters.start_date}&end_date=${this.filters.end_date}&empresa=${this.filters.empresa}&centro_resultado=${this.filters.centro_resultado}&cliente=${this.filters.cliente || ''}`);
            
            if (response.success && response.data) {
                this.renderComparativoChart(response.data);
            }
        } catch (error) {
            console.error('Erro ao carregar comparativo anos:', error);
        }
    }

    async loadSunburstData() {
        console.log('🌅 Carregando dados do sunburst...');
        try {
            const url = `/financeiro/faturamento/api/geral/sunburst_data?start_date=${this.filters.start_date}&end_date=${this.filters.end_date}&empresa=${this.filters.empresa}`;
            console.log('📍 URL da requisição:', url);
            
            const response = await $.get(url);
            console.log('📥 Resposta recebida:', response);
            
            if (response.success && response.data) {
                console.log('✅ Chamando renderSunburstChart com dados:', response.data.length, 'registros');
                this.renderSunburstChart(response.data);
            } else {
                console.error('❌ Dados do sunburst inválidos:', response);
            }
        } catch (error) {
            console.error('❌ Erro ao carregar dados sunburst:', error);
        }
    }

    async loadResumoMensal() {
        try {
            const response = await $.get(`/financeiro/faturamento/api/geral/comparativo_anos?start_date=${this.filters.start_date}&end_date=${this.filters.end_date}&empresa=${this.filters.empresa}&centro_resultado=${this.filters.centro_resultado}&cliente=${this.filters.cliente || ''}`);
            
            if (response.success && response.data) {
                this.renderResumoMensal(response.data);
            }
        } catch (error) {
            console.error('Erro ao carregar resumo mensal:', error);
        }
    }

    // New Chart Rendering Functions
    renderComparativoChart(data) {
        const ctx = document.getElementById('comparativo-chart');
        if (!ctx) return;

        // Destroy existing chart
        if (this.comparativoChart) {
            this.comparativoChart.destroy();
        }

        // Armazenar todos os anos disponíveis (sem controle de visibilidade)
        this.allYears = Object.keys(data).sort();
        
        console.log('📅 Anos disponíveis:', this.allYears);
        
        const meses = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12'];
        
        // Criar datasets para todos os anos (sem filtro)
        const datasets = this.allYears.map((ano, index) => {
            const anoData = data[ano] || [];
            const valores = meses.map(mes => {
                const item = anoData.find(d => d.mes === mes);
                return item ? item.total_valor : 0;
            });

            return {
                label: ano,
                data: valores,
                borderColor: this.getYearColor(index),
                backgroundColor: this.getYearColor(index, 0.1),
                borderWidth: 3,
                fill: false,
                tension: 0.4,
                pointRadius: 5,
                pointHoverRadius: 8
            };
        });

        this.comparativoChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: meses.map(mes => this.getMonthName(mes)),
                datasets: datasets
            },
            plugins: [ChartDataLabels],
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                plugins: {
                    title: {
                        display: true,
                        text: 'Comparativo Mensal por Ano',
                        font: { size: 16, weight: 'bold' }
                    },
                    legend: {
                        position: 'top'
                    },
                    datalabels: {
                        display: this.dataLabelsEnabled, // Usar propriedade dinâmica
                        align: 'top',
                        anchor: 'end',
                        color: '#666',
                        font: {
                            size: 10,
                            weight: 'bold'
                        },
                        formatter: (value) => {
                            // Garantir que value é um número válido
                            if (typeof value === 'object' || value === null || value === undefined) {
                                return '';
                            }
                            const numValue = typeof value === 'number' ? value : (isNaN(parseFloat(value)) ? 0 : parseFloat(value));
                            if (numValue > 0) {
                                return formatCurrencyShort(numValue);
                            }
                            return '';
                        },
                        backgroundColor: function(context) {
                            return context.dataset.borderColor;
                        },
                        borderColor: '#fff',
                        borderRadius: 4,
                        borderWidth: 1,
                        padding: 2
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: value => formatCurrencyShort(value)
                        }
                    }
                },
                elements: {
                    point: {
                        hoverBackgroundColor: '#fff',
                        hoverBorderWidth: 3
                    }
                }
            }
        });

        // Setup apenas toggle de rótulos (funcionalidade nativa Chart.js para anos)
        this.setupDataLabelsToggle();
        
        console.log('✅ Gráfico comparativo renderizado com toggle de rótulos configurado');
    }

    renderSunburstChart(data) {
        console.log('🌅 Renderizando sunburst chart com dados:', data);
        
        const ctx = document.getElementById('sunburst-chart');
        if (!ctx) {
            console.error('❌ Elemento sunburst-chart não encontrado!');
            return;
        }

        // Destroy existing chart
        if (this.sunburstChart) {
            this.sunburstChart.destroy();
        }

        // Transform data for Chart.js doughnut (simulating sunburst)
        const centerData = {};
        
        data.forEach(item => {
            const centro = item.centro_resultado || 'Outros';
            const categoria = item.categoria || 'Não Categorizado';
            const valor = item.total_valor || 0;
            
            if (!centerData[centro]) {
                centerData[centro] = { total: 0, categorias: {} };
            }
            
            centerData[centro].total += valor;
            centerData[centro].categorias[categoria] = (centerData[centro].categorias[categoria] || 0) + valor;
        });

        console.log('📊 Dados processados para sunburst:', centerData);

        const labels = [];
        const values = [];
        const colors = [];
        
        Object.entries(centerData).forEach(([centro, info], centerIndex) => {
            // Add center level
            labels.push(centro);
            values.push(info.total);
            colors.push(this.getCenterColor(centerIndex));
            
            // Add category levels (as separate segments)
            Object.entries(info.categorias).forEach(([categoria, valor], catIndex) => {
                labels.push(`${centro} - ${categoria}`);
                values.push(valor);
                colors.push(this.getCenterColor(centerIndex, 0.6 + (catIndex * 0.1)));
            });
        });

        console.log('🎨 Labels:', labels);
        console.log('📈 Values:', values);
        console.log('🌈 Colors:', colors);

        this.sunburstChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: colors,
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Proporção por Centro de Resultado → Categoria',
                        font: { size: 16, weight: 'bold' }
                    },
                    legend: {
                        position: 'right',
                        labels: {
                            generateLabels: function(chart) {
                                const original = Chart.defaults.plugins.legend.labels.generateLabels;
                                const labels = original.call(this, chart);
                                
                                // Filter to show only main centers
                                return labels.filter(label => label && label.text && !label.text.includes(' - '));
                            }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((context.parsed * 100) / total).toFixed(1);
                                return `${context.label}: ${formatCurrency(context.parsed)} (${percentage}%)`;
                            }
                        }
                    }
                },
                onClick: (event, elements) => {
                    if (elements.length > 0) {
                        const elementIndex = elements[0].index;
                        const label = labels[elementIndex];
                        const value = values[elementIndex];
                        
                        console.log('🎯 Clique no sunburst:', label, formatCurrency(value));
                        
                        // Mostrar detalhes ou filtrar dados
                        this.showSunburstDetails(label, value);
                    }
                }
            }
        });
    }
    
    showSunburstDetails(label, value) {
        // Implementar modal ou área de detalhes
        const message = `Detalhes de ${label}:\nValor: ${formatCurrency(value)}`;
        
        // Por enquanto, mostrar alert (pode ser substituído por modal)
        if (confirm(`${message}\n\nDeseja filtrar dados por "${label}"?`)) {
            console.log('🔍 Filtrando por:', label);
            // Aqui pode implementar filtro específico
        }
    }

    renderResumoMensal(data) {
        console.log('📊 Renderizando resumo mensal com dados:', data);
        
        const table = $('#resumo-mensal');
        const thead = table.find('thead tr');
        const tbody = table.find('tbody');
        
        if (!table.length) {
            console.error('❌ Elemento resumo-mensal não encontrado');
            return;
        }
        
        // Limpar conteúdo
        thead.empty();
        tbody.empty();

        // Organizar dados por ano
        const anos = Object.keys(data).sort();
        
        if (anos.length === 0) {
            tbody.append('<tr><td colspan="100%" class="text-center">Nenhum dado encontrado</td></tr>');
            return;
        }

        // Definir meses
        const meses = [
            {num: '01', nome: 'Jan'},
            {num: '02', nome: 'Fev'},
            {num: '03', nome: 'Mar'},
            {num: '04', nome: 'Abr'},
            {num: '05', nome: 'Mai'},
            {num: '06', nome: 'Jun'},
            {num: '07', nome: 'Jul'},
            {num: '08', nome: 'Ago'},
            {num: '09', nome: 'Set'},
            {num: '10', nome: 'Out'},
            {num: '11', nome: 'Nov'},
            {num: '12', nome: 'Dez'}
        ];

        // Criar cabeçalho dinâmico: Ano + Meses + Colunas calculadas
        thead.append('<th>Ano</th>');
        meses.forEach(mes => {
            thead.append(`<th>${mes.nome}</th>`);
        });
        // Adicionar colunas calculadas
        thead.append('<th class="text-info">TOTAL</th>');
        thead.append('<th class="text-warning">MÉDIA MÊS</th>');
        thead.append('<th class="text-success">% AUMENTO</th>');
        
        // Criar linhas para cada ano
        anos.forEach((ano, anoIndex) => {
            const row = $('<tr></tr>');
            row.append(`<td class="fw-bold">${ano}</td>`);
            
            const anoData = data[ano] || [];
            let totalAno = 0;
            const valoresAno = [];
            
            // Adicionar dados de cada mês para este ano
            meses.forEach(mes => {
                const item = anoData.find(d => d.mes === mes.num);
                const valor = item ? item.total_valor : 0;
                
                totalAno += valor;
                valoresAno.push(valor);
                
                const cell = $('<td></td>');
                cell.text(formatCurrencyShort(valor));
                cell.addClass(valor > 0 ? 'text-success fw-bold' : 'text-muted');
                row.append(cell);
            });
            
            // Calcular colunas adicionais
            const mediaAno = valoresAno.length > 0 ? totalAno / valoresAno.filter(v => v > 0).length : 0;
            
            // % aumento (comparar com ano anterior)
            let percentualAumento = 0;
            if (anoIndex > 0) {
                const anoAnterior = anos[anoIndex - 1];
                const anoAnteriorData = data[anoAnterior] || [];
                const totalAnoAnterior = anoAnteriorData.reduce((sum, item) => sum + (item.total_valor || 0), 0);
                
                if (totalAnoAnterior > 0 && totalAno > 0) {
                    percentualAumento = ((totalAno - totalAnoAnterior) / totalAnoAnterior) * 100;
                }
            }
            
            // Adicionar colunas calculadas
            const totalCell = $('<td class="text-info fw-bold"></td>');
            totalCell.text(formatCurrencyShort(totalAno));
            row.append(totalCell);
            
            const mediaCell = $('<td class="text-warning fw-bold"></td>');
            mediaCell.text(formatCurrencyShort(mediaAno));
            row.append(mediaCell);
            
            const percentCell = $('<td class="fw-bold"></td>');
            if (anoIndex === 0) {
                percentCell.text('-');
                percentCell.addClass('text-muted');
            } else {
                percentCell.text(percentualAumento.toFixed(1) + '%');
                percentCell.addClass(percentualAumento > 0 ? 'text-success' : percentualAumento < 0 ? 'text-danger' : 'text-muted');
            }
            row.append(percentCell);
            
            tbody.append(row);
        });
        
        console.log('✅ Tabela resumo renderizada:', anos.length, 'anos x 12 meses + colunas calculadas');
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
            
            tbody.append(row);
        });
    }
    
    async loadGeralProporcao() {
        try {
            const response = await fetch(`/financeiro/faturamento/api/geral/proporcao?ano=${this.currentAno}`);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Erro ao carregar dados de proporção');
            }
            
            this.renderChartProporcao(data.setores);
        } catch (error) {
            console.error('Erro ao carregar gráficos de proporção:', error);
        }
    }
    
    renderChartProporcao(setores) {
        const ctx = document.getElementById('chart-proporcao-setores');
        if (!ctx) {
            console.error('Chart context not found: chart-proporcao-setores');
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
                            size: 10,
                            weight: 'bold'
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
            },
            plugins: [ChartDataLabels] // Add the data labels plugin
        });
    }
    
    renderClientesTable(data) {
        const tbody = $('#tabela-ranking-clientes tbody');
        tbody.empty();
        
        if (data.length === 0) {
            tbody.append(`
                <tr>
                    <td colspan="3" class="text-center text-muted">
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
                    <td class="fw-bold">${formatCurrency(row.valor)}</td>
                    <td>${row.pct_gt.toFixed(1)}%</td>
                </tr>
            `);
        });
    }
    
    // OnePage Layout Functions for Setores Analysis
    async loadAllSetoresData() {
        try {
            // Load data for all sectors in parallel
            const setores = ['importacao', 'exportacao', 'consultoria'];
            const promises = setores.map(setor => this.loadSetorEspecificoData(setor));
            await Promise.all(promises);
        } catch (error) {
            console.error('Erro ao carregar dados de todos os setores:', error);
            this.showError('Erro ao carregar dados dos setores: ' + error.message);
        }
    }
    
    async loadSetorEspecificoData(setor) {
        try {
            const response = await fetch(`/financeiro/faturamento/api/setor/dados_completos?setor=${setor}`);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Erro ao carregar dados do setor');
            }
            
            this.updateSetorEspecificoKPIs(setor, data.kpis);
            this.renderSetorEspecificoChart(setor, data.grafico_mensal);
            this.renderSetorEspecificoTable(setor, data.ranking_clientes);
        } catch (error) {
            console.error(`Erro ao carregar dados do setor ${setor}:`, error);
            // Don't show error for individual sectors, just log it
        }
    }
    
    updateSetorEspecificoKPIs(setor, kpis) {
        // Update specific setor KPIs
        $(`#valor-faturamento-${setor}`).text(formatCurrencyShort(kpis.faturamento_total));
        $(`#valor-percentual-${setor}`).text(`${kpis.percentual_participacao.toFixed(1)}%`);
    }
    
    renderSetorEspecificoChart(setor, data) {
        const ctx = document.getElementById(`chart-faturamento-${setor}`).getContext('2d');
        
        // Destroy previous chart if exists
        if (this.charts[`setor-${setor}`]) {
            this.charts[`setor-${setor}`].destroy();
        }
        
        // Prepare data for chart
        const months = [];
        const currentPeriodData = [];
        const previousPeriodData = [];
        
        // Extract unique months and sort them
        const monthKeys = [...new Set(data.map(item => item.mes))].sort();
        
        // Create month labels and populate data arrays
        monthKeys.forEach(monthKey => {
            const monthData = data.find(item => item.mes === monthKey);
            if (monthData) {
                const [year, month] = monthKey.split('-');
                const monthName = new Date(year, month - 1, 1).toLocaleDateString('pt-BR', { month: 'short' });
                months.push(`${monthName}/${year.slice(2)}`);
                
                currentPeriodData.push(monthData.faturamento || 0);
                previousPeriodData.push(monthData.faturamento_anterior || 0);
            }
        });
        
        // Set colors based on setor
        const setorColors = {
            'importacao': { primary: 'rgba(5, 150, 105, 1)', secondary: 'rgba(17, 94, 89, 1)' },
            'exportacao': { primary: 'rgba(245, 158, 11, 1)', secondary: 'rgba(217, 119, 6, 1)' },
            'consultoria': { primary: 'rgba(124, 58, 237, 1)', secondary: 'rgba(109, 40, 217, 1)' }
        };
        
        const colors = setorColors[setor] || setorColors['importacao'];
        
        this.charts[`setor-${setor}`] = new Chart(ctx, {
            type: 'line',
            data: {
                labels: months,
                datasets: [{
                    label: 'Período Atual',
                    data: currentPeriodData,
                    borderColor: colors.primary,
                    backgroundColor: colors.primary.replace('1)', '0.1)'),
                    borderWidth: 3,
                    fill: false,
                    tension: 0.4,
                    pointBackgroundColor: colors.primary,
                    pointBorderColor: 'white',
                    pointBorderWidth: 2,
                    pointRadius: 5
                }, {
                    label: 'Mesmo Período Anterior',
                    data: previousPeriodData,
                    borderColor: colors.secondary,
                    backgroundColor: colors.secondary.replace('1)', '0.1)'),
                    borderWidth: 3,
                    fill: false,
                    tension: 0.4,
                    pointBackgroundColor: colors.secondary,
                    pointBorderColor: 'white',
                    pointBorderWidth: 2,
                    pointRadius: 5
                }]
            },
            options: {
                ...this.chartDefaults,
                plugins: {
                    ...this.chartDefaults.plugins,
                    datalabels: {
                        display: true,
                        anchor: 'end',
                        align: 'top',
                        formatter: function(value, context) {
                            return formatCurrencyShort(value);
                        },
                        font: {
                            size: 10,
                            weight: 'bold'
                        },
                        color: '#333'
                    }
                }
            },
            plugins: [ChartDataLabels]
        });
    }
    
    renderSetorEspecificoTable(setor, data) {
        const tbody = $(`#tabela-ranking-${setor} tbody`);
        tbody.empty();
        
        if (data.length === 0) {
            tbody.append(`
                <tr>
                    <td colspan="3" class="text-center text-muted">
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
            
            // Preencher campos com valores atuais
            $('#start-date').val(this.filters.start_date || '');
            $('#end-date').val(this.filters.end_date || '');
            $('#empresa-select').val(this.filters.empresa || '');
            $('#centro-resultado-select').val(this.filters.centro_resultado || '');
            $('#cliente-select').val(this.filters.cliente || '');
            $('#mes-select').val(this.filters.mes || '');
            
            // Detectar ano do start_date se existir
            if (this.filters.start_date) {
                const ano = this.filters.start_date.split('-')[0];
                $('#ano-select').val(ano);
            }
            
            // Carregar opções dinâmicas
            this.loadFilterOptions();
        }
    }
    
    async loadFilterOptions() {
        // Carregar clientes
        $('#loading-clientes').show();
        try {
            const response = await $.get('/financeiro/faturamento/api/clientes');
            if (response.success) {
                const select = $('#cliente-select');
                select.find('option:not(:first)').remove(); // Remove todas exceto "Todos"
                response.data.forEach(cliente => {
                    select.append(`<option value="${cliente}">${cliente}</option>`);
                });
            }
        } catch (error) {
            console.error('Erro ao carregar clientes:', error);
        } finally {
            $('#loading-clientes').hide();
        }
        
        // Carregar centros de resultado
        $('#loading-centros').show();
        try {
            const response = await $.get('/financeiro/faturamento/api/centros-resultado');
            if (response.success) {
                const select = $('#centro-resultado-select');
                select.find('option:not(:first)').remove(); // Remove todas exceto "Todos"
                response.data.forEach(centro => {
                    select.append(`<option value="${centro}">${centro}</option>`);
                });
            }
        } catch (error) {
            console.error('Erro ao carregar centros:', error);
        } finally {
            $('#loading-centros').hide();
        }
    }
    
    closeFiltersModal() {
        const modal = document.getElementById('filter-modal');
        if (modal) {
            modal.style.display = 'none';
        }
    }
    
    applyFilters() {
        // Coletar valores dos filtros
        const startDate = $('#start-date').val();
        const endDate = $('#end-date').val();
        const anoSelecionado = $('#ano-select').val();
        const mesSelecionado = $('#mes-select').val();
        const empresaSelecionada = $('#empresa-select').val();
        const centroResultado = $('#centro-resultado-select').val();
        const cliente = $('#cliente-select').val();
        
        // Se ano foi selecionado, ajusta datas automaticamente
        if (anoSelecionado) {
            if (mesSelecionado) {
                // Mês específico de um ano
                const ultimoDia = new Date(anoSelecionado, parseInt(mesSelecionado), 0).getDate();
                this.filters.start_date = `${anoSelecionado}-${mesSelecionado.padStart(2, '0')}-01`;
                this.filters.end_date = `${anoSelecionado}-${mesSelecionado.padStart(2, '0')}-${ultimoDia}`;
            } else {
                // Ano completo
                this.filters.start_date = `${anoSelecionado}-01-01`;
                this.filters.end_date = `${anoSelecionado}-12-31`;
            }
        } else if (startDate && endDate) {
            // Usar datas personalizadas
            this.filters.start_date = startDate;
            this.filters.end_date = endDate;
        }
        
        // Aplicar outros filtros
        this.filters.empresa = empresaSelecionada;
        this.filters.centro_resultado = centroResultado;
        this.filters.cliente = cliente;
        this.filters.mes = mesSelecionado;
        
        // Atualizar resumo de filtros
        this.updateFilterSummary();
        
        // Mostrar botão de remover filtros
        if (this.hasActiveFilters()) {
            $('#reset-filters').show();
        }
        
        // Fechar modal
        this.closeFiltersModal();
        
        // Recarregar dados
        this.loadData();
    }
    
    hasActiveFilters() {
        const currentYear = new Date().getFullYear();
        return this.filters.start_date !== `${currentYear}-01-01` ||
               this.filters.end_date !== `${currentYear}-12-31` ||
               this.filters.empresa !== '' ||
               this.filters.centro_resultado !== '' ||
               this.filters.cliente !== '' ||
               this.filters.mes !== '';
    }
    
    updateFilterSummary() {
        const parts = [];
        
        // Período
        if (this.filters.start_date && this.filters.end_date) {
            const startDate = new Date(this.filters.start_date);
            const endDate = new Date(this.filters.end_date);
            
            // Verificar se é um ano completo
            if (startDate.getMonth() === 0 && startDate.getDate() === 1 &&
                endDate.getMonth() === 11 && endDate.getDate() === 31 &&
                startDate.getFullYear() === endDate.getFullYear()) {
                parts.push(`Ano ${startDate.getFullYear()}`);
            } else if (this.filters.mes) {
                const meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
                parts.push(`${meses[parseInt(this.filters.mes) - 1]}/${startDate.getFullYear()}`);
            } else {
                parts.push(`${startDate.toLocaleDateString('pt-BR')} a ${endDate.toLocaleDateString('pt-BR')}`);
            }
        }
        
        // Empresa
        if (this.filters.empresa) {
            const empresaNome = this.filters.empresa === 'consultoria' ? 'Consultoria' : 'IMP/EXP';
            parts.push(empresaNome);
        }
        
        // Centro de Resultado
        if (this.filters.centro_resultado) {
            parts.push(`CR: ${this.filters.centro_resultado}`);
        }
        
        // Cliente
        if (this.filters.cliente) {
            parts.push(`Cliente: ${this.filters.cliente}`);
        }
        
        // Atualizar texto do resumo
        const resumoTexto = parts.length > 0 ? parts.join(' • ') : 'Todos os dados';
        $('#filter-summary-text').text(resumoTexto);
    }
    
    resetFilters() {
        const currentYear = new Date().getFullYear();
        
        // Reset filters to default
        this.filters = {
            start_date: `${currentYear}-01-01`,
            end_date: `${currentYear}-12-31`,
            empresa: '',
            centro_resultado: '',
            cliente: '',
            mes: ''
        };
        
        // Reset UI
        $('#start-date').val('');
        $('#end-date').val('');
        $('#ano-select').val(currentYear);
        $('#mes-select').val('');
        $('#empresa-select').val('');
        $('#centro-resultado-select').val('');
        $('#cliente-select').val('');
        
        // Update summary
        this.updateFilterSummary();
        
        // Hide reset button
        $('#reset-filters').hide();
        
        // Reload data
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
        // Verificar se os datalabels devem ser exibidos
        const datalabelsOptions = chart.options.plugins && chart.options.plugins.datalabels;
        if (!datalabelsOptions || datalabelsOptions.display === false) {
            return; // Não desenhar se display for false
        }
        
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
                if (datalabelsOptions && datalabelsOptions.formatter) {
                    try {
                        formattedValue = datalabelsOptions.formatter(numericValue, { dataIndex: index, dataset });
                    } catch (e) {
                        formattedValue = formatCurrencyShort(numericValue);
                    }
                } else {
                    formattedValue = formatCurrencyShort(numericValue);
                }
                
                // Style
                ctx.font = datalabelsOptions && datalabelsOptions.font ? 
                    `${datalabelsOptions.font.weight || 'bold'} ${datalabelsOptions.font.size || 12}px sans-serif` : 
                    'bold 12px sans-serif';
                ctx.fillStyle = datalabelsOptions && datalabelsOptions.color ? 
                    datalabelsOptions.color : '#666';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                
                // Draw text
                ctx.fillText(formattedValue, x, y - 10);
            });
        });
        
        ctx.restore();
    }
};

// Auxiliary functions for new charts
FaturamentoController.prototype.getYearColor = function(index, alpha = 1) {
    const colors = [
        `rgba(54, 162, 235, ${alpha})`,   // Blue
        `rgba(255, 99, 132, ${alpha})`,   // Red
        `rgba(75, 192, 192, ${alpha})`,   // Teal
        `rgba(255, 206, 86, ${alpha})`,   // Yellow
        `rgba(153, 102, 255, ${alpha})`,  // Purple
        `rgba(255, 159, 64, ${alpha})`    // Orange
    ];
    return colors[index % colors.length];
};

FaturamentoController.prototype.getCenterColor = function(index, alpha = 1) {
    const colors = [
        `rgba(75, 192, 192, ${alpha})`,   // Teal
        `rgba(255, 99, 132, ${alpha})`,   // Red
        `rgba(54, 162, 235, ${alpha})`,   // Blue
        `rgba(255, 206, 86, ${alpha})`,   // Yellow
        `rgba(153, 102, 255, ${alpha})`,  // Purple
        `rgba(255, 159, 64, ${alpha})`,   // Orange
        `rgba(199, 199, 199, ${alpha})`,  // Gray
        `rgba(83, 102, 147, ${alpha})`    // Dark Blue
    ];
    return colors[index % colors.length];
};

FaturamentoController.prototype.setupDataLabelsToggle = function() {
    const toggleButton = document.getElementById('toggle-data-labels');
    if (!toggleButton) {
        console.warn('Botão toggle-data-labels não encontrado');
        return;
    }

    // Remover listeners anteriores para evitar duplicação
    const newButton = toggleButton.cloneNode(true);
    toggleButton.parentNode.replaceChild(newButton, toggleButton);

    // Configurar estado inicial baseado na propriedade da classe
    newButton.classList.toggle('active', this.dataLabelsEnabled);

    // Adicionar listener para toggle
    newButton.addEventListener('click', () => {
        this.dataLabelsEnabled = !this.dataLabelsEnabled;
        newButton.classList.toggle('active', this.dataLabelsEnabled);
        
        console.log('🏷️ Toggle rótulos:', this.dataLabelsEnabled ? 'Ativado' : 'Desativado');
        
        this.updateDataLabels();
    });

    console.log('✅ Toggle de rótulos configurado com sucesso');
};

FaturamentoController.prototype.updateDataLabels = function() {
    if (!this.comparativoChart) {
        console.warn('Gráfico comparativo não encontrado para atualização');
        return;
    }
    
    try {
        // Atualizar configuração dos datalabels no gráfico
        if (this.comparativoChart.options.plugins && this.comparativoChart.options.plugins.datalabels) {
            this.comparativoChart.options.plugins.datalabels.display = this.dataLabelsEnabled;
        }
        
        // Forçar atualização do gráfico
        this.comparativoChart.update();
        
        console.log('🏷️ Rótulos de dados:', this.dataLabelsEnabled ? 'Habilitados' : 'Desabilitados');
        
        // Verificar se a atualização foi aplicada
        setTimeout(() => {
            console.log('🔍 Verificação - datalabels.display:', this.comparativoChart.options.plugins.datalabels.display);
        }, 100);
        
    } catch (error) {
        console.error('❌ Erro ao atualizar rótulos de dados:', error);
    }
};

FaturamentoController.prototype.getMonthName = function(mes) {
    const months = {
        '01': 'Jan', '02': 'Fev', '03': 'Mar', '04': 'Abr',
        '05': 'Mai', '06': 'Jun', '07': 'Jul', '08': 'Ago',
        '09': 'Set', '10': 'Out', '11': 'Nov', '12': 'Dez'
    };
    return months[mes] || mes;
};

// Funções utilitárias
function formatCurrency(value) {
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(value);
}

function formatCurrencyShort(value) {
    if (value >= 1000000000) {
        return 'R$ ' + (value / 1000000000).toFixed(2) + 'B';
    } else if (value >= 1000000) {
        return 'R$ ' + (value / 1000000).toFixed(2) + 'M';
    } else if (value >= 1000) {
        return 'R$ ' + (value / 1000).toFixed(2) + 'K';
    } else {
        return 'R$ ' + value.toFixed(2);
    }
}

// Inicializar controlador após o carregamento do DOM
document.addEventListener('DOMContentLoaded', function() {
    // Garantir que jQuery esteja disponível
    if (typeof $ !== 'undefined') {
        window.faturamentoController = new FaturamentoController();
        console.log('FaturamentoController inicializado com sucesso');
    } else {
        console.error('jQuery não está disponível');
        // Tentar novamente após um pequeno delay
        setTimeout(() => {
            if (typeof $ !== 'undefined') {
                window.faturamentoController = new FaturamentoController();
                console.log('FaturamentoController inicializado com sucesso (retry)');
            }
        }, 100);
    }
});