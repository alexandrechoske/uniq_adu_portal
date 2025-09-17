/**
 * Novo JavaScript para Faturamento com componentes atualizados
 * Compatível com o novo template HTML
 */

class FaturamentoControllerNovo {
    constructor() {
        this.currentAno = new Date().getFullYear();
        this.anosDisponiveis = [];
        this.anosAtivos = new Set();
        this.charts = {};
        this.exibindoMeta = false; // Estado do toggle Meta vs Realizado
        this.dataLabelsAtivos = false; // Estado dos rótulos de dados
        
        // Configurações globais
        Chart.register(ChartDataLabels);
        Chart.defaults.plugins.datalabels.display = false;
        
        this.coresGraficos = {
            receita: '#28a745',
            despesa: '#dc3545',
            resultado: '#007bff',
            neutro: '#6c757d',
            anos: ['#007bff', '#28a745', '#dc3545', '#ffc107', '#6c757d', '#17a2b8'],
            meta: '#ff6b35' // Cor para a linha de meta
        };
        
        this.init();
    }
    
    async init() {
        console.log('Inicializando FaturamentoControllerNovo...');
        
        try {
            this.setupToggleLabels();
            this.setupSectorFunctionality(); // Configurar funcionalidade do setor
            await this.buscarAnosDisponiveis();
            await this.carregarTodosOsDados();
        } catch (error) {
            console.error('Erro na inicialização:', error);
        }
    }
    
    setupToggleLabels() {
        const toggleButton = document.getElementById('toggle-data-labels');
        if (toggleButton) {
            toggleButton.addEventListener('click', () => {
                this.toggleDataLabels();
            });
            console.log('✅ Toggle de rótulos configurado');
        } else {
            console.warn('⚠️ Botão toggle-data-labels não encontrado');
        }
        
        // Configurar toggle para Meta vs Realizado
        const toggleMetaButton = document.getElementById('toggle-meta-comparativo');
        if (toggleMetaButton) {
            toggleMetaButton.addEventListener('click', () => {
                this.toggleMetaComparativo();
            });
            console.log('✅ Toggle Meta vs Realizado configurado');
        } else {
            console.warn('⚠️ Botão toggle-meta-comparativo não encontrado');
        }
    }
    
    toggleDataLabels() {
        this.dataLabelsAtivos = !this.dataLabelsAtivos;
        
        if (this.charts.comparativo) {
            const datalabelsPlugin = this.charts.comparativo.options.plugins.datalabels;
            datalabelsPlugin.display = this.dataLabelsAtivos;
            this.charts.comparativo.update();
            
            const button = document.getElementById('toggle-data-labels');
            if (button) {
                if (this.dataLabelsAtivos) {
                    button.classList.remove('btn-outline-secondary');
                    button.classList.add('btn-secondary');
                } else {
                    button.classList.remove('btn-secondary');
                    button.classList.add('btn-outline-secondary');
                }
            }
            
            console.log(`🏷️ Rótulos ${this.dataLabelsAtivos ? 'ativados' : 'desativados'}`);
        }
    }
    
    async toggleMetaComparativo() {
        this.exibindoMeta = !this.exibindoMeta;
        
        const button = document.getElementById('toggle-meta-comparativo');
        const title = document.getElementById('comparativo-chart-title');
        
        if (button) {
            if (this.exibindoMeta) {
                button.classList.remove('btn-outline-primary');
                button.classList.add('btn-primary');
                button.innerHTML = '<i class="mdi mdi-chart-timeline-variant"></i> Comparativo Anos';
            } else {
                button.classList.remove('btn-primary');
                button.classList.add('btn-outline-primary');
                button.innerHTML = '<i class="mdi mdi-target"></i> Meta vs Realizado';
            }
        }
        
        if (title) {
            title.textContent = this.exibindoMeta ? 'Meta vs Realizado' : 'Comparativo Anual de Faturamento';
        }
        
        // Recarregar o gráfico com os dados apropriados
        if (this.exibindoMeta) {
            await this.carregarGraficoMeta();
        } else {
            await this.carregarGraficoComparativo();
        }
        
        console.log(`🎯 ${this.exibindoMeta ? 'Exibindo Meta vs Realizado' : 'Exibindo Comparativo Anos'}`);
    }
    
    formatarMoeda(valor) {
        if (valor === null || valor === undefined) return 'R$ 0,00';
        return new Intl.NumberFormat('pt-BR', {
            style: 'currency',
            currency: 'BRL',
            minimumFractionDigits: 2
        }).format(valor);
    }
    
    formatarMoedaCompacta(valor) {
        if (!valor) return 'R$ 0';
        
        const abs = Math.abs(valor);
        if (abs >= 1000000) {
            return `R$ ${(valor / 1000000).toFixed(1)}M`;
        } else if (abs >= 1000) {
            return `R$ ${(valor / 1000).toFixed(1)}K`;
        } else {
            return `R$ ${valor.toFixed(0)}`;
        }
    }
    
    async buscarAnosDisponiveis() {
        try {
            console.log('🔄 Buscando anos disponíveis...');
            const response = await fetch('/financeiro/faturamento/api/geral/comparativo_anos');
            console.log('📡 Response anos:', response.status);
            const data = await response.json();
            console.log('📊 Data anos:', data);
            
            if (data.success && data.data) {
                // data.data é um objeto onde as chaves são os anos
                this.anosDisponiveis = Object.keys(data.data).map(ano => parseInt(ano)).sort((a, b) => b - a);
                this.anosAtivos = new Set(this.anosDisponiveis.slice(0, 3));
                this.renderizarToggleAnos();
                console.log('✅ Anos disponíveis:', this.anosDisponiveis);
            } else {
                console.warn('⚠️ Dados de anos vazios ou inválidos:', data);
                // Fallback para ano atual
                this.anosDisponiveis = [new Date().getFullYear()];
                this.anosAtivos = new Set(this.anosDisponiveis);
                this.renderizarToggleAnos();
            }
        } catch (error) {
            console.error('❌ Erro ao buscar anos disponíveis:', error);
            // Fallback para ano atual em caso de erro
            this.anosDisponiveis = [new Date().getFullYear()];
            this.anosAtivos = new Set(this.anosDisponiveis);
            this.renderizarToggleAnos();
        }
    }
    
    renderizarToggleAnos() {
        const container = document.getElementById('year-toggles');
        if (!container) {
            console.error('Container year-toggles não encontrado');
            return;
        }
        
        container.innerHTML = '';
        
        this.anosDisponiveis.forEach(ano => {
            const button = document.createElement('button');
            button.className = `year-toggle ${this.anosAtivos.has(ano) ? 'active' : ''}`;
            button.textContent = ano;
            button.onclick = () => this.toggleAno(ano);
            container.appendChild(button);
        });
    }
    
    toggleAno(ano) {
        if (this.anosAtivos.has(ano)) {
            this.anosAtivos.delete(ano);
        } else {
            this.anosAtivos.add(ano);
        }
        
        this.renderizarToggleAnos();
        this.carregarGraficoComparativo();
    }
    
    async carregarTodosOsDados() {
        console.log('Carregando todos os dados...');
        
        const loadingElements = [
            'loading-kpis',
            'loading-comparativo', 
            'loading-centro-resultado',
            'loading-categoria-operacao',
            'loading-top-clientes'
        ];
        
        // Mostrar loadings
        loadingElements.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.style.display = 'block';
        });
        
        try {
            await Promise.all([
                this.carregarKPIs(),
                this.carregarGraficoComparativo(),
                this.carregarGraficoCentroResultado(),
                this.carregarGraficoCategoriaOperacao(),
                this.carregarTopClientes(),
                this.carregarTabelaComparativa()
            ]);
        } catch (error) {
            console.error('Erro ao carregar dados:', error);
        } finally {
            // Esconder loadings
            loadingElements.forEach(id => {
                const el = document.getElementById(id);
                if (el) el.style.display = 'none';
            });
        }
    }
    
    async carregarKPIs() {
        try {
            console.log('🔄 Carregando KPIs...');
            // Usar o endpoint comparativo que tem todos os anos
            const response = await fetch('/financeiro/faturamento/api/geral/comparativo_anos');
            console.log('📡 Response KPIs:', response.status);
            const data = await response.json();
            console.log('📊 Data KPIs:', data);
            
            if (data.success && data.data) {
                console.log('✅ Calculando KPIs com dados comparativos');
                this.calcularKPIsComparativo(data.data);
            } else {
                console.warn('⚠️ Dados de KPIs vazios ou inválidos:', data);
            }
        } catch (error) {
            console.error('❌ Erro ao carregar KPIs:', error);
        }
    }
    
    calcularKPIs(dados) {
        console.log('🧮 Calculando KPIs com dados:', dados);
        const anoAtual = new Date().getFullYear();
        const mesAtual = new Date().getMonth() + 1;
        
        // Filtrar dados do ano atual
        const dadosAnoAtual = dados.filter(item => item.ano === anoAtual);
        const dadosAnoAnterior = dados.filter(item => item.ano === anoAtual - 1);
        
        console.log(`📅 Dados ano atual (${anoAtual}):`, dadosAnoAtual.length);
        console.log(`📅 Dados ano anterior (${anoAtual - 1}):`, dadosAnoAnterior.length);
        
        // KPI 1: Total faturado do ano atual (soma de todos os meses)
        const totalFaturadoAno = dadosAnoAtual.reduce((acc, item) => acc + (item.faturamento_total || 0), 0);
        this.atualizarElemento('kpi-total-faturamento', this.formatarMoeda(totalFaturadoAno));
        console.log('💰 Total faturado ano:', totalFaturadoAno);
        
        // KPI 2: Comparação inteligente com ano anterior (mesmo período)
        // Filtrar ano atual até o mês atual
        const dadosAnoAtualAteMesAtual = dadosAnoAtual.filter(item => item.mes <= mesAtual);
        const totalAnoAtualAteMesAtual = dadosAnoAtualAteMesAtual.reduce((acc, item) => acc + (item.faturamento_total || 0), 0);
        
        // Filtrar ano anterior até o mesmo mês do ano atual
        const dadosAnoAnteriorAteMesAtual = dadosAnoAnterior.filter(item => item.mes <= mesAtual);
        const totalAnoAnteriorAteMesAtual = dadosAnoAnteriorAteMesAtual.reduce((acc, item) => acc + (item.faturamento_total || 0), 0);
        
        let crescimento = 0;
        let crescimentoTexto = 'N/A';
        
        if (totalAnoAnteriorAteMesAtual > 0) {
            crescimento = ((totalAnoAtualAteMesAtual - totalAnoAnteriorAteMesAtual) / totalAnoAnteriorAteMesAtual) * 100;
            const sinal = crescimento >= 0 ? '+' : '';
            crescimentoTexto = `${sinal}${crescimento.toFixed(1)}%`;
        }
        this.atualizarElemento('kpi-crescimento-anual', crescimentoTexto);
        console.log(`📈 Crescimento até mês ${mesAtual}: ${totalAnoAtualAteMesAtual} vs ${totalAnoAnteriorAteMesAtual} = ${crescimentoTexto}`);
        
        // KPI 3: Melhor mês do ano atual
        let melhorMes = { mes: 0, faturamento_total: -Infinity };
        dadosAnoAtual.forEach(item => {
            if (item.faturamento_total > melhorMes.faturamento_total) {
                melhorMes = item;
            }
        });
        
        const nomesMeses = ['', 'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
        if (melhorMes.mes > 0) {
            const melhorMesTexto = `${nomesMeses[melhorMes.mes]} - ${this.formatarMoeda(melhorMes.faturamento_total)}`;
            this.atualizarElemento('kpi-melhor-mes', melhorMesTexto);
            console.log('🏆 Melhor mês:', melhorMesTexto);
        }
        
        // KPI 4: Pior mês do ano atual (apenas meses com dados > 0)
        let piorMes = { mes: 0, faturamento_total: Infinity };
        dadosAnoAtual.forEach(item => {
            if (item.faturamento_total > 0 && item.faturamento_total < piorMes.faturamento_total) {
                piorMes = item;
            }
        });
        
        if (piorMes.mes > 0 && piorMes.faturamento_total < Infinity) {
            const piorMesTexto = `${nomesMeses[piorMes.mes]} - ${this.formatarMoeda(piorMes.faturamento_total)}`;
            this.atualizarElemento('kpi-pior-mes', piorMesTexto);
            console.log('📉 Pior mês:', piorMesTexto);
        }
        
        console.log('✅ KPIs calculados e atualizados');
    }

    calcularKPIsComparativo(dados) {
        console.log('🧮 Calculando KPIs com dados comparativos:', dados);
        const anoAtual = new Date().getFullYear();
        const mesAtual = new Date().getMonth() + 1;
        
        // Acessar dados dos anos específicos
        const dadosAnoAtual = dados[anoAtual.toString()] || [];
        const dadosAnoAnterior = dados[(anoAtual - 1).toString()] || [];
        
        console.log(`📅 Dados ${anoAtual}:`, dadosAnoAtual.length, 'meses');
        console.log(`📅 Dados ${anoAtual - 1}:`, dadosAnoAnterior.length, 'meses');
        
        // KPI 1: Total faturado do ano atual (todos os meses)
        const totalFaturadoAno = dadosAnoAtual.reduce((acc, item) => {
            return acc + (parseFloat(item.total_valor) || 0);
        }, 0);
        this.atualizarElemento('kpi-total-faturamento', this.formatarMoeda(totalFaturadoAno));
        console.log('💰 Total faturado ano:', totalFaturadoAno);
        
        // KPI 2: Comparação inteligente (até mês atual)
        const dadosAtualAteMes = dadosAnoAtual.filter(item => {
            const mes = parseInt(item.mes);
            return mes <= mesAtual;
        });
        
        const dadosAnteriorAteMes = dadosAnoAnterior.filter(item => {
            const mes = parseInt(item.mes);
            return mes <= mesAtual;
        });
        
        const totalAtualAteMes = dadosAtualAteMes.reduce((acc, item) => {
            return acc + (parseFloat(item.total_valor) || 0);
        }, 0);
        
        const totalAnteriorAteMes = dadosAnteriorAteMes.reduce((acc, item) => {
            return acc + (parseFloat(item.total_valor) || 0);
        }, 0);
        
        let crescimentoTexto = 'N/A';
        if (totalAnteriorAteMes > 0) {
            const crescimento = ((totalAtualAteMes - totalAnteriorAteMes) / totalAnteriorAteMes) * 100;
            const sinal = crescimento >= 0 ? '+' : '';
            crescimentoTexto = `${sinal}${crescimento.toFixed(1)}%`;
        }
        
        this.atualizarElemento('kpi-crescimento-anual', crescimentoTexto);
        console.log('Crescimento ate mes ' + mesAtual + ': R$ ' + totalAtualAteMes.toLocaleString('pt-BR') + ' vs R$ ' + totalAnteriorAteMes.toLocaleString('pt-BR') + ' = ' + crescimentoTexto);
        
        // KPI 3: Melhor mês do ano atual
        let melhorMes = { mes: 0, valor: -Infinity };
        dadosAnoAtual.forEach(item => {
            const valor = parseFloat(item.total_valor) || 0;
            if (valor > melhorMes.valor) {
                melhorMes = { mes: parseInt(item.mes), valor: valor };
            }
        });
        
        const nomesMeses = ['', 'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
        if (melhorMes.mes > 0) {
            const textoMelhor = `${nomesMeses[melhorMes.mes]} - ${this.formatarMoeda(melhorMes.valor)}`;
            this.atualizarElemento('kpi-melhor-mes', textoMelhor);
        }
        
        // KPI 4: Pior mês do ano atual (com dados > 0)
        let piorMes = { mes: 0, valor: Infinity };
        dadosAnoAtual.forEach(item => {
            const valor = parseFloat(item.total_valor) || 0;
            if (valor > 0 && valor < piorMes.valor) {
                piorMes = { mes: parseInt(item.mes), valor: valor };
            }
        });
        
        if (piorMes.mes > 0 && piorMes.valor < Infinity) {
            const textoPior = `${nomesMeses[piorMes.mes]} - ${this.formatarMoeda(piorMes.valor)}`;
            this.atualizarElemento('kpi-pior-mes', textoPior);
        }
        
        // KPI Aderência Meta (usar dadosAnoAtual para realizado)
        this.calcularAderenciaMeta(anoAtual, mesAtual, dadosAnoAtual);
        
        console.log('✅ KPIs comparativos calculados e atualizados');
    }

    async calcularAderenciaMeta(anoAtual, mesAtual, dadosAnoAtual) {
        try {
            // Evitar múltiplas chamadas se já armazenado
            if (!this._cacheMetas || this._cacheMetas.ano !== anoAtual) {
                const resp = await fetch('/financeiro/faturamento/api/geral/metas_mensais');
                const metaJson = await resp.json();
                if (metaJson.success) {
                    this._cacheMetas = { ano: metaJson.ano || anoAtual, data: metaJson.data };
                } else {
                    console.warn('⚠️ Não foi possível carregar metas para KPI Aderência');
                    return;
                }
            }
            const metas = this._cacheMetas.data || [];
            // Acumulados até mês atual
            const realizadoAcumulado = dadosAnoAtual
                .filter(item => parseInt(item.mes) <= mesAtual)
                .reduce((acc, item) => acc + (parseFloat(item.total_valor || item.faturamento_total) || 0), 0);
            const metaAcumulada = metas
                .filter(m => parseInt(m.mes) <= mesAtual)
                .reduce((acc, m) => acc + (parseFloat(m.meta) || 0), 0);
            if (metaAcumulada > 0) {
                const aderencia = (realizadoAcumulado / metaAcumulada) * 100;
                const texto = `${aderencia.toFixed(1)}%`;
                this.atualizarElemento('kpi-aderencia-meta', texto);
                
                // Aplicar classe CSS dinâmica baseada no valor
                const cardElement = document.getElementById('kpi-aderencia-meta-card');
                if (cardElement) {
                    // Remover classes anteriores
                    cardElement.classList.remove('positive', 'negative');
                    // Adicionar classe baseada no valor (>= 100% = positive, < 100% = negative)
                    if (aderencia >= 100) {
                        cardElement.classList.add('positive');
                    } else {
                        cardElement.classList.add('negative');
                    }
                }
                
                console.log(`🎯 Aderência Meta: Realizado ${realizadoAcumulado} / Meta ${metaAcumulada} = ${texto}`);
            } else {
                this.atualizarElemento('kpi-aderencia-meta', 'N/A');
                // Remover classes quando não há dados
                const cardElement = document.getElementById('kpi-aderencia-meta-card');
                if (cardElement) {
                    cardElement.classList.remove('positive', 'negative');
                }
            }
        } catch (e) {
            console.error('Erro calcularAderenciaMeta:', e);
        }
    }
    
    calcularKPIsFormatoAntigo(data) {
        // Trabalhar com formato antigo
        const anoAtual = new Date().getFullYear();
        const mesAtual = new Date().getMonth() + 1;
        
        // Calcular total faturado
        let totalFaturado = 0;
        data.meses.forEach(mes => {
            Object.keys(mes).forEach(key => {
                if (key.startsWith('ano_')) {
                    totalFaturado += mes[key] || 0;
                }
            });
        });
        
        this.atualizarElemento('resultado-acumulado-ano', this.formatarMoeda(totalFaturado));
        
        // Outros KPIs podem ser calculados de forma similar
        console.log('KPIs formato antigo calculados');
    }
    
    atualizarElemento(id, valor) {
        console.log(`📝 Atualizando elemento ${id} com valor: ${valor}`);
        const elemento = document.getElementById(id);
        if (elemento) {
            elemento.textContent = valor;
            console.log(`✅ Elemento ${id} atualizado com sucesso`);
        } else {
            console.warn(`❌ Elemento ${id} não encontrado no DOM`);
        }
    }
    
    async carregarGraficoComparativo() {
        try {
            console.log('🔄 Carregando gráfico comparativo...');
            const response = await fetch('/financeiro/faturamento/api/geral/comparativo_anos');
            console.log('📡 Response comparativo:', response.status);
            const data = await response.json();
            console.log('📊 Data comparativo:', data);
            
            if (data.success && data.data) {
                console.log('✅ Renderizando gráfico comparativo');
                this.renderizarGraficoComparativo(data.data);
            } else {
                console.warn('⚠️ Dados de comparativo vazios ou inválidos:', data);
            }
        } catch (error) {
            console.error('❌ Erro ao carregar gráfico comparativo:', error);
        }
    }
    
    renderizarGraficoComparativo(dados) {
        const canvas = document.getElementById('comparativo-chart');
        if (!canvas) {
            console.error('Canvas comparativo-chart não encontrado');
            return;
        }
        
        const ctx = canvas.getContext('2d');
        
        // Destruir gráfico anterior
        if (this.charts.comparativo) {
            this.charts.comparativo.destroy();
        }
        
        // Processar dados do endpoint comparativo (formato por ano)
        console.log('Dados recebidos para comparativo:', dados);
        
        const datasets = [];
        const meses = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                      'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];
        
        let corIndex = 0;
        
        for (const [ano, dadosAno] of Object.entries(dados)) {
            const valoresMensais = new Array(12).fill(0);
            
            dadosAno.forEach(item => {
                const mesIndex = parseInt(item.mes) - 1;
                // Usar total_valor que é o campo correto no endpoint comparativo
                valoresMensais[mesIndex] = item.total_valor || 0;
            });
            
            // Destacar o ano atual
            const anoAtual = new Date().getFullYear();
            const isAnoAtual = parseInt(ano) === anoAtual;
            
            datasets.push({
                label: ano,
                data: valoresMensais,
                borderColor: this.coresGraficos.anos[corIndex % this.coresGraficos.anos.length],
                backgroundColor: this.coresGraficos.anos[corIndex % this.coresGraficos.anos.length] + '20',
                borderWidth: isAnoAtual ? 4 : 2, // Linha mais grossa para ano atual
                fill: false,
                tension: 0.1,
                pointRadius: isAnoAtual ? 6 : 4, // Pontos maiores para ano atual
                pointHoverRadius: isAnoAtual ? 8 : 6,
                borderOpacity: isAnoAtual ? 1 : 0.7 // Mais opaco para ano atual
            });
            
            corIndex++;
        }

        this.charts.comparativo = new Chart(ctx, {
            type: 'line',
            data: {
                labels: meses,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: (value) => this.formatarMoedaCompacta(value)
                        },
                        title: { display: true, text: 'Faturamento' }
                    }
                },
                plugins: {
                    legend: { display: true, position: 'top' },
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                return `${context.dataset.label}: ${this.formatarMoeda(context.parsed.y)}`;
                            }
                        }
                    },
                    datalabels: {
                        display: this.dataLabelsAtivos,
                        align: 'top',
                        anchor: 'end',
                        color: '#333',
                        font: {
                            size: 10,
                            weight: 'bold'
                        },
                        formatter: (value) => {
                            if (value === 0) return '';
                            return this.formatarMoedaCompacta(value);
                        }
                    }
                }
            }
        });
        
        console.log('Gráfico comparativo renderizado');
    }
    
    async carregarGraficoMeta() {
        try {
            console.log('🎯 Carregando gráfico Meta vs Realizado...');
            
            // Buscar dados do ano atual
            const responseRealizado = await fetch('/financeiro/faturamento/api/geral/mensal');
            const dataRealizado = await responseRealizado.json();
            
            // Buscar dados da meta
            const responseMeta = await fetch('/financeiro/faturamento/api/geral/metas_mensais');
            const dataMeta = await responseMeta.json();
            
            console.log('📊 Data realizado:', dataRealizado);
            console.log('🎯 Data meta:', dataMeta);
            
            if (dataRealizado.success && dataMeta.success) {
                console.log('✅ Renderizando gráfico Meta vs Realizado');
                this.renderizarGraficoMeta(dataRealizado.data, dataMeta.data);
            } else {
                console.warn('⚠️ Dados de meta ou realizado vazios ou inválidos');
            }
        } catch (error) {
            console.error('❌ Erro ao carregar gráfico meta:', error);
        }
    }
    
    renderizarGraficoMeta(dadosRealizado, dadosMeta) {
        const canvas = document.getElementById('comparativo-chart');
        if (!canvas) {
            console.error('Canvas comparativo-chart não encontrado');
            return;
        }
        
        const ctx = canvas.getContext('2d');
        
        // Destruir gráfico anterior
        if (this.charts.comparativo) {
            this.charts.comparativo.destroy();
        }
        
        const meses = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                      'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];
        
        // Preparar dados do realizado (do endpoint mensal)
        const valoresRealizado = new Array(12).fill(0);
        dadosRealizado.forEach(item => {
            const mesIndex = parseInt(item.mes) - 1;
            valoresRealizado[mesIndex] = item.faturamento_total || 0; // Campo correto
        });
        
        // Preparar dados da meta (do endpoint metas_mensais)
        const valoresMeta = new Array(12).fill(0);
        dadosMeta.forEach(item => {
            const mesIndex = parseInt(item.mes) - 1;
            valoresMeta[mesIndex] = item.meta || 0; // Campo correto
        });
        
        const datasets = [
            {
                label: `Realizado ${this.currentAno}`,
                data: valoresRealizado,
                borderColor: this.coresGraficos.anos[0],
                backgroundColor: this.coresGraficos.anos[0] + '20',
                borderWidth: 3,
                fill: false,
                tension: 0.1,
                pointRadius: 5,
                pointHoverRadius: 7
            },
            {
                label: `Meta ${this.currentAno}`,
                data: valoresMeta,
                borderColor: this.coresGraficos.meta,
                backgroundColor: this.coresGraficos.meta + '20',
                borderWidth: 3,
                borderDash: [5, 5], // Linha tracejada para meta
                fill: false,
                tension: 0.1,
                pointRadius: 5,
                pointHoverRadius: 7
            }
        ];
        
        this.charts.comparativo = new Chart(ctx, {
            type: 'line',
            data: {
                labels: meses,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: (value) => this.formatarMoedaCompacta(value)
                        },
                        title: { display: true, text: 'Faturamento' }
                    }
                },
                plugins: {
                    legend: { display: true, position: 'top' },
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                return `${context.dataset.label}: ${this.formatarMoeda(context.parsed.y)}`;
                            }
                        }
                    },
                    datalabels: {
                        display: this.dataLabelsAtivos,
                        align: 'top',
                        anchor: 'end',
                        color: '#333',
                        font: {
                            size: 10,
                            weight: 'bold'
                        },
                        formatter: (value) => {
                            if (value === 0) return '';
                            return this.formatarMoedaCompacta(value);
                        }
                    }
                }
            }
        });
        
        console.log('✅ Gráfico Meta vs Realizado renderizado');
    }
    
    async carregarGraficoCentroResultado() {
        try {
            console.log('🔄 Carregando gráfico centro resultado...');
            const response = await fetch('/financeiro/faturamento/api/geral/centro_resultado');
            console.log('📡 Response centro resultado:', response.status);
            const data = await response.json();
            console.log('📊 Data centro resultado:', data);
            
            if (data.success && data.data && data.data.length > 0) {
                console.log('✅ Renderizando gráfico centro resultado com', data.data.length, 'itens');
                this.renderizarGraficoCentroResultado(data.data);
            } else {
                console.warn('⚠️ Dados de centro resultado vazios ou inválidos:', data);
            }
        } catch (error) {
            console.error('❌ Erro ao carregar centro resultado:', error);
        }
    }
    
    renderizarGraficoCentroResultado(dados) {
        console.log('🎨 Iniciando renderização centro resultado...');
        const canvas = document.getElementById('centro-resultado-chart');
        if (!canvas) {
            console.error('❌ Canvas centro-resultado-chart não encontrado');
            return;
        }
        console.log('✅ Canvas centro resultado encontrado:', canvas);
        
        const ctx = canvas.getContext('2d');
        
        // Destruir gráfico anterior
        if (this.charts.centroResultado) {
            this.charts.centroResultado.destroy();
        }
        
        // Preparar dados
        const labels = dados.map(item => item.centro_resultado);
        const valores = dados.map(item => item.valor);
        const percentuais = dados.map(item => item.percentual);
        
        // Cores para diferentes centros de resultado
        const cores = [
            '#007bff', '#28a745', '#dc3545', '#ffc107', 
            '#6c757d', '#17a2b8', '#e83e8c', '#fd7e14'
        ];
        
        this.charts.centroResultado = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: valores,
                    backgroundColor: cores.slice(0, dados.length),
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                onClick: (event, elements) => {
                    if (elements.length > 0) {
                        const dataIndex = elements[0].index;
                        const centroResultado = labels[dataIndex];
                        this.renderCentroResultadoDetalhado(centroResultado);
                    }
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'bottom'
                    },
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                const valor = context.parsed;
                                const percentual = percentuais[context.dataIndex];
                                return `${context.label}: ${this.formatarMoeda(valor)} (${percentual.toFixed(1)}%)`;
                            }
                        }
                    },
                    datalabels: {
                        display: true,
                        color: '#fff',
                        font: {
                            weight: 'bold',
                            size: 12
                        },
                        formatter: (value, context) => {
                            const percentual = percentuais[context.dataIndex];
                            return percentual > 5 ? `${percentual.toFixed(1)}%` : '';
                        }
                    }
                }
            }
        });
        
        console.log('Gráfico centro resultado renderizado');
    }
    
    async carregarGraficoCategoriaOperacao() {
        try {
            console.log('🔄 Carregando gráfico categoria operação...');
            const response = await fetch('/financeiro/faturamento/api/geral/categoria_operacao');
            console.log('📡 Response categoria:', response.status);
            const data = await response.json();
            console.log('📊 Data categoria:', data);
            
            if (data.success && data.data && data.data.length > 0) {
                console.log('✅ Renderizando gráfico categoria com', data.data.length, 'itens');
                this.renderizarGraficoCategoriaOperacao(data.data);
            } else {
                console.warn('⚠️ Dados de categoria vazios ou inválidos:', data);
            }
        } catch (error) {
            console.error('❌ Erro ao carregar categoria operação:', error);
        }
    }
    
    renderizarGraficoCategoriaOperacao(dados) {
        const canvas = document.getElementById('categoria-operacao-chart');
        if (!canvas) {
            console.error('Canvas categoria-operacao-chart não encontrado');
            return;
        }
        
        const ctx = canvas.getContext('2d');
        
        // Destruir gráfico anterior
        if (this.charts.categoriaOperacao) {
            this.charts.categoriaOperacao.destroy();
        }
        
        // Preparar dados
        const labels = dados.map(item => item.categoria);
        const valores = dados.map(item => item.valor);
        const percentuais = dados.map(item => item.percentual);
        
        // Cores para diferentes categorias de operação
        const cores = [
            '#28a745', '#007bff', '#dc3545', '#ffc107', 
            '#6c757d', '#17a2b8', '#e83e8c', '#fd7e14'
        ];
        
        this.charts.categoriaOperacao = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: valores,
                    backgroundColor: cores.slice(0, dados.length),
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'bottom'
                    },
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                const valor = context.parsed;
                                const percentual = percentuais[context.dataIndex];
                                return `${context.label}: ${this.formatarMoeda(valor)} (${percentual.toFixed(1)}%)`;
                            }
                        }
                    },
                    datalabels: {
                        display: true,
                        color: '#fff',
                        font: {
                            weight: 'bold',
                            size: 12
                        },
                        formatter: (value, context) => {
                            const percentual = percentuais[context.dataIndex];
                            return percentual > 5 ? `${percentual.toFixed(1)}%` : '';
                        }
                    }
                }
            }
        });
        
        console.log('Gráfico categoria operação renderizado');
    }
    
    async carregarTopClientes() {
        try {
            console.log('🔄 Carregando top clientes...');
            const response = await fetch('/financeiro/faturamento/api/geral/top_clientes?limit=10');
            console.log('📡 Response top clientes:', response.status);
            const data = await response.json();
            console.log('📊 Data top clientes:', data);
            
            if (data.success && data.data && data.data.length > 0) {
                console.log('✅ Renderizando top clientes com', data.data.length, 'itens');
                this.renderizarTopClientes(data.data);
            } else {
                console.warn('⚠️ Dados de top clientes vazios ou inválidos:', data);
            }
        } catch (error) {
            console.error('❌ Erro ao carregar top clientes:', error);
        }
    }
    
    renderizarTopClientes(dados) {
        console.log('🎨 Iniciando renderização top clientes...');
        const tbody = document.querySelector('#top-clientes-table tbody');
        if (!tbody) {
            console.error('❌ Tabela top-clientes-table não encontrada');
            return;
        }
        console.log('✅ Tabela top clientes encontrada:', tbody);
        
        tbody.innerHTML = '';
        
        dados.forEach((cliente, index) => {
            const row = document.createElement('tr');
            
            // Aplicar classes de destaque para o top 3
            if (index === 0) row.classList.add('top-1');
            else if (index === 1) row.classList.add('top-2');
            else if (index === 2) row.classList.add('top-3');
            
            // Truncar nome do cliente para 15 caracteres
            const nomeCliente = cliente.cliente || 'N/A';
            const nomeClienteTruncado = nomeCliente.length > 15 ? 
                nomeCliente.substring(0, 15) + '...' : nomeCliente;
            
            row.innerHTML = `
                <td class="fw-bold" title="${nomeCliente}">${nomeClienteTruncado}</td>
                <td class="text-end">${this.formatarMoeda(cliente.valor)}</td>
                <td class="text-center">
                    <span class="badge bg-primary">${cliente.percentual.toFixed(1)}%</span>
                </td>
            `;
            
            tbody.appendChild(row);
        });
        
        console.log('Top clientes renderizado');
    }
    
    async carregarTabelaComparativa() {
        try {
            console.log('🔄 Carregando tabela comparativa...');
            const response = await fetch('/financeiro/faturamento/api/geral/comparativo_anos');
            console.log('📡 Response tabela:', response.status);
            const data = await response.json();
            console.log('📊 Data tabela:', data);
            
            if (data.success && data.data) {
                console.log('✅ Renderizando tabela comparativa');
                this.renderizarTabelaComparativa(data.data);
            } else {
                console.warn('⚠️ Dados de tabela vazios ou inválidos:', data);
            }
        } catch (error) {
            console.error('❌ Erro ao carregar tabela:', error);
        }
    }
    
    renderizarTabelaComparativa(dados) {
        const table = document.querySelector('#resumo-mensal');
        if (!table) {
            console.error('Tabela resumo-mensal não encontrada');
            return;
        }
        
        // Obter todos os anos disponíveis
        const anos = Object.keys(dados).sort((a, b) => parseInt(a) - parseInt(b));
        const mesesNomes = ['JAN', 'FEV', 'MAR', 'ABR', 'MAI', 'JUN', 
                           'JUL', 'AGO', 'SET', 'OUT', 'NOV', 'DEZ'];
        
        // Criar cabeçalho
        const thead = table.querySelector('thead');
        thead.innerHTML = `
            <tr>
                <th>Ano</th>
                ${mesesNomes.map(mes => `<th class="text-center">${mes}</th>`).join('')}
                <th class="text-center bg-info text-white">TOTAL</th>
                <th class="text-center bg-warning text-dark">MÉDIA</th>
                <th class="text-center bg-success text-white">% AUMENTO</th>
            </tr>
        `;
        
        // Criar corpo da tabela
        const tbody = table.querySelector('tbody');
        tbody.innerHTML = '';
        
        let totalAnoAnterior = 0;
        
        anos.forEach((ano, index) => {
            const dadosAno = dados[ano];
            const row = document.createElement('tr');
            
            // Coluna do ano
            row.innerHTML = `<td class="fw-bold">${ano}</td>`;
            
            // Colunas dos meses
            let totalAno = 0;
            let mesesComDados = 0;
            
            for (let mes = 1; mes <= 12; mes++) {
                const mesStr = mes.toString().padStart(2, '0');
                const dadoMes = dadosAno.find(item => item.mes === mesStr);
                const valor = dadoMes ? dadoMes.total_valor : 0;
                
                if (valor > 0) mesesComDados++;
                totalAno += valor;
                
                const classe = valor > 0 ? 'text-success' : 'text-muted';
                const valorFormatado = valor > 0 ? this.formatarMoedaCompacta(valor) : '-';
                row.innerHTML += `<td class="text-end ${classe}">${valorFormatado}</td>`;
            }
            
            // Coluna TOTAL
            row.innerHTML += `<td class="text-end fw-bold bg-info text-white">${this.formatarMoeda(totalAno)}</td>`;
            
            // Coluna MÉDIA
            const media = mesesComDados > 0 ? totalAno / mesesComDados : 0;
            row.innerHTML += `<td class="text-end fw-bold bg-warning text-dark">${this.formatarMoeda(media)}</td>`;
            
            // Coluna % AUMENTO
            let percentualAumento = 'N/A';
            let classeAumento = 'text-muted';
            
            if (totalAnoAnterior > 0) {
                const aumento = ((totalAno - totalAnoAnterior) / totalAnoAnterior) * 100;
                percentualAumento = `${aumento >= 0 ? '+' : ''}${aumento.toFixed(1)}%`;
                classeAumento = aumento >= 0 ? 'text-success' : 'text-danger';
            }
            
            row.innerHTML += `<td class="text-end fw-bold bg-success text-white ${classeAumento}">${percentualAumento}</td>`;
            
            tbody.appendChild(row);
            totalAnoAnterior = totalAno;
        });
        
        console.log('✅ Tabela comparativa completa renderizada');
    }
    
    renderizarTabelaFormatoAntigo(data) {
        // Implementar renderização para formato antigo se necessário
        console.log('Renderizando tabela formato antigo...');
    }

    async renderCentroResultadoDetalhado(centroResultado) {
        try {
            console.log(`🔍 Carregando drill-down para Centro de Resultado: ${centroResultado}`);
            
            // Mostrar info de drill-down (usar IDs corretos do HTML)
            const infoElement = document.getElementById('centro-resultado-info');
            const btnVoltar = document.getElementById('centro-resultado-voltar');
            const titleElement = document.getElementById('centro-resultado-title');
            
            if (infoElement) {
                infoElement.textContent = `💡 Categorias dentro de: ${centroResultado}`;
                infoElement.style.display = 'block';
            }
            
            if (btnVoltar) {
                btnVoltar.style.display = 'inline-block';
                console.log('✅ Botão voltar mostrado');
            } else {
                console.warn('⚠️ Botão voltar não encontrado');
            }
            
            if (titleElement) {
                titleElement.textContent = `${centroResultado} - Categorias`;
            }
            
            // Buscar dados detalhados
            const response = await fetch(`/financeiro/faturamento/api/geral/centro_resultado_detalhado?centro_resultado=${encodeURIComponent(centroResultado)}`);
            const data = await response.json();
            
            if (data.sucesso && data.dados.length > 0) {
                // Renderizar gráfico detalhado
                this.renderGraficoCentroResultadoDetalhado(data.dados, centroResultado);
            } else {
                console.warn('Nenhum dado detalhado encontrado para:', centroResultado);
            }
            
        } catch (error) {
            console.error('Erro ao carregar drill-down:', error);
        }
    }

    renderGraficoCentroResultadoDetalhado(dados, centroResultado) {
        const ctx = document.getElementById('centro-resultado-chart');
        if (!ctx) return;

        // Destruir gráfico anterior se existir
        if (this.charts.centroResultado) {
            this.charts.centroResultado.destroy();
        }

        const labels = dados.map(item => item.cliente || item.subcategoria || 'Não informado');
        const valores = dados.map(item => parseFloat(item.valor_faturamento) || 0);
        const total = valores.reduce((acc, val) => acc + val, 0);
        const percentuais = valores.map(val => (val / total) * 100);

        // Cores para o gráfico detalhado
        const cores = [
            '#28a745', '#007bff', '#dc3545', '#ffc107', 
            '#6c757d', '#17a2b8', '#e83e8c', '#fd7e14',
            '#20c997', '#6f42c1', '#e83e8c', '#fd7e14'
        ];

        this.charts.centroResultado = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: valores,
                    backgroundColor: cores.slice(0, dados.length),
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'bottom'
                    },
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                const valor = context.parsed;
                                const percentual = percentuais[context.dataIndex];
                                return `${context.label}: ${this.formatarMoeda(valor)} (${percentual.toFixed(1)}%)`;
                            }
                        }
                    },
                    datalabels: {
                        display: true,
                        color: '#fff',
                        font: {
                            weight: 'bold',
                            size: 12
                        },
                        formatter: (value, context) => {
                            const percentual = percentuais[context.dataIndex];
                            return percentual > 3 ? `${percentual.toFixed(1)}%` : '';
                        }
                    }
                }
            }
        });

        console.log(`✅ Gráfico detalhado renderizado para: ${centroResultado}`);
    }

    voltarCentroResultadoGeral() {
        console.log('🔙 Voltando para visão geral do Centro de Resultado');
        
        // Esconder info de drill-down (usar IDs corretos)
        const infoElement = document.getElementById('centro-resultado-info');
        const btnVoltar = document.getElementById('centro-resultado-voltar');
        const titleElement = document.getElementById('centro-resultado-title');
        
        if (infoElement) {
            infoElement.textContent = '💡 Clique em uma fatia do gráfico para ver mais detalhes';
            infoElement.style.display = 'block';
        }
        
        if (btnVoltar) {
            btnVoltar.style.display = 'none';
            console.log('✅ Botão voltar escondido');
        }
        
        if (titleElement) {
            titleElement.textContent = 'Centro de Resultado';
        }
        
        // Recarregar gráfico geral
        this.carregarGraficoCentroResultado();
    }
    
    // ============ FUNCIONALIDADE DINÂMICA DO SETOR ============
    setupSectorFunctionality() {
        const sectorButtons = document.querySelectorAll('.sector-btn');
        const togglePrevYear = document.getElementById('toggle-prev-year-setor');
        
        // Setup tab listeners
        this.setupTabListeners();
        
        // Setup sector buttons
        if (sectorButtons.length > 0) {
            sectorButtons.forEach(button => {
                button.addEventListener('click', (e) => {
                    const setor = e.currentTarget.getAttribute('data-setor');
                    
                    // Atualizar visual dos botões
                    sectorButtons.forEach(btn => btn.classList.remove('active'));
                    e.currentTarget.classList.add('active');
                    
                    // Carregar dados do setor
                    this.carregarDadosSetor(setor);
                });
            });
            console.log('✅ Botões de setor configurados');
        }
        
        if (togglePrevYear) {
            togglePrevYear.addEventListener('click', () => {
                this.toggleComparacaoAnoAnteriorSetor();
            });
            console.log('✅ Toggle ano anterior setor configurado');
        }
    }
    
    setupTabListeners() {
        // Listener para detectar quando a aba "Análise por Setor" é clicada
        const tabButtons = document.querySelectorAll('.tab-button');
        
        tabButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                const tabName = e.target.getAttribute('data-tab');
                
                // Atualizar visual das abas
                tabButtons.forEach(btn => btn.classList.remove('active'));
                e.target.classList.add('active');
                
                // Mostrar/esconder conteúdo das abas
                const allTabContents = document.querySelectorAll('.tab-content');
                allTabContents.forEach(content => content.classList.remove('active'));
                
                const targetTab = document.getElementById(`${tabName}-tab`);
                if (targetTab) {
                    targetTab.classList.add('active');
                }
                
                if (tabName === 'analise-setor') {
                    console.log('🔍 Aba Análise por Setor ativada');
                    
                    // Pequeno delay para garantir que a aba seja exibida
                    setTimeout(() => {
                        this.inicializarDadosSetor();
                    }, 100);
                }
            });
        });
        
        console.log('✅ Listeners das abas configurados');
    }
    
    inicializarDadosSetor() {
        const activeButton = document.querySelector('.sector-btn.active');
        if (activeButton) {
            const setor = activeButton.getAttribute('data-setor');
            console.log(`🚀 Inicializando dados do setor: ${setor}`);
            this.carregarDadosSetor(setor);
        } else {
            console.log('🚀 Carregando dados do setor padrão: importacao');
            this.carregarDadosSetor('importacao');
        }
    }
    
    async carregarDadosSetor(setor) {
        console.log(`📊 Carregando dados do setor: ${setor}`);
        
        try {
            // Buscar dados do setor específico
            const response = await fetch(`/financeiro/faturamento/api/geral/setor/${setor}?ano=${this.currentAno}`);
            const data = await response.json();
            
            if (!data.success) {
                throw new Error(data.message || 'Erro ao carregar dados do setor');
            }
            
            // Atualizar KPIs
            this.atualizarKPIsSetor(data.data, setor);
            
            // Atualizar gráfico mensal
            this.atualizarGraficoMensalSetor(data.data, setor);
            
            // Atualizar ranking de clientes
            this.atualizarRankingClientesSetor(data.data, setor);
            
            // Atualizar títulos
            this.atualizarTitulosSetor(setor);
            
        } catch (error) {
            console.error('Erro ao carregar dados do setor:', error);
            this.mostrarErroSetor();
        }
    }
    
    atualizarKPIsSetor(data, setor) {
        const setorNomes = {
            'importacao': 'Importação',
            'exportacao': 'Exportação',
            'consultoria': 'Consultoria'
        };
        
        // Faturamento Total
        const valorFaturamento = data.faturamento_total || 0;
        document.getElementById('valor-faturamento-setor').textContent = 
            this.formatarMoeda(valorFaturamento);
        document.getElementById('desc-faturamento-setor').textContent = 
            `${setorNomes[setor]} em ${this.currentAno}`;
        
        // Participação
        const participacao = data.participacao_percentual || 0;
        document.getElementById('valor-participacao-setor').textContent = 
            `${participacao.toFixed(1)}%`;
        
        // Crescimento
        const crescimento = data.crescimento_percentual || 0;
        const valorCrescimento = document.getElementById('valor-crescimento-setor');
        valorCrescimento.textContent = `${crescimento >= 0 ? '+' : ''}${crescimento.toFixed(1)}%`;
        
        // Atualizar cor baseado no crescimento
        const kpiCrescimento = document.getElementById('kpi-crescimento-setor');
        kpiCrescimento.className = 'kpi-card ' + (crescimento >= 0 ? 'kpi-success' : 'kpi-danger');
        
        // Melhor Mês
        const melhorMes = data.melhor_mes || {};
        document.getElementById('valor-melhor-mes-setor').textContent = 
            melhorMes.mes || 'N/A';
        document.getElementById('desc-melhor-mes-setor').textContent = 
            melhorMes.valor ? this.formatarMoeda(melhorMes.valor) : 'Sem dados';
    }
    
    atualizarGraficoMensalSetor(data, setor) {
        const ctx = document.getElementById('chart-mensal-setor');
        if (!ctx) return;
        
        // Destruir gráfico existente
        if (this.charts.setorMensal) {
            this.charts.setorMensal.destroy();
        }
        
        const dadosMensais = data.dados_mensais || [];
        const meses = dadosMensais.map(item => item.mes);
        const valores = dadosMensais.map(item => item.valor);
        
        this.charts.setorMensal = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: meses,
                datasets: [{
                    label: `Faturamento ${this.currentAno}`,
                    data: valores,
                    backgroundColor: this.coresGraficos.receita,
                    borderColor: this.coresGraficos.receita,
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true
                    },
                    title: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: (value) => this.formatarMoeda(value)
                        }
                    }
                }
            }
        });
    }
    
    atualizarRankingClientesSetor(data, setor) {
        const tbody = document.querySelector('#tabela-ranking-setor tbody');
        if (!tbody) return;
        
        const clientes = data.ranking_clientes || [];
        
        tbody.innerHTML = '';
        
        clientes.forEach((cliente, index) => {
            const row = tbody.insertRow();
            
            row.innerHTML = `
                <td><strong>#${index + 1}</strong></td>
                <td title="${cliente.nome}">${cliente.nome}</td>
                <td>${this.formatarMoeda(cliente.valor)}</td>
                <td>${cliente.participacao?.toFixed(1) || 0}%</td>
                <td>
                    <button class="btn-drill-cliente" 
                            onclick="window.faturamentoNovo.drillDownCliente('${cliente.id}', '${cliente.nome}')">
                        <i class="mdi mdi-eye"></i>
                    </button>
                </td>
            `;
        });
        
        console.log(`✅ Ranking de clientes atualizado para setor ${setor}: ${clientes.length} clientes`);
    }
    
    atualizarTitulosSetor(setor) {
        const setorNomes = {
            'importacao': 'Importação',
            'exportacao': 'Exportação',
            'consultoria': 'Consultoria'
        };
        
        const chartTitle = document.getElementById('chart-title-setor');
        const tableTitle = document.getElementById('table-title-setor');
        
        if (chartTitle) {
            chartTitle.textContent = `Faturamento Mensal - ${setorNomes[setor]}`;
        }
        
        if (tableTitle) {
            tableTitle.textContent = `Ranking de Clientes - ${setorNomes[setor]}`;
        }
    }
    
    toggleComparacaoAnoAnteriorSetor() {
        const button = document.getElementById('toggle-prev-year-setor');
        const isActive = button.classList.contains('active');
        
        if (isActive) {
            button.classList.remove('active');
            // Remover dados do ano anterior
            this.removerAnoAnteriorGraficoSetor();
        } else {
            button.classList.add('active');
            // Adicionar dados do ano anterior
            this.adicionarAnoAnteriorGraficoSetor();
        }
    }
    
    async adicionarAnoAnteriorGraficoSetor() {
        const activeButton = document.querySelector('.sector-btn.active');
        const setor = activeButton?.getAttribute('data-setor') || 'importacao';
        const anoAnterior = this.currentAno - 1;
        
        try {
            const response = await fetch(`/financeiro/faturamento/api/geral/setor/${setor}?ano=${anoAnterior}`);
            const data = await response.json();
            
            if (data.success && this.charts.setorMensal) {
                const dadosMensais = data.data.dados_mensais || [];
                const valores = dadosMensais.map(item => item.valor);
                
                this.charts.setorMensal.data.datasets.push({
                    label: `Faturamento ${anoAnterior}`,
                    data: valores,
                    backgroundColor: this.coresGraficos.anos[1] + '80', // Transparência
                    borderColor: this.coresGraficos.anos[1],
                    borderWidth: 1
                });
                
                this.charts.setorMensal.update();
                console.log(`✅ Adicionado ano anterior (${anoAnterior}) ao gráfico do setor`);
            }
        } catch (error) {
            console.error('Erro ao adicionar ano anterior:', error);
        }
    }
    
    removerAnoAnteriorGraficoSetor() {
        if (this.charts.setorMensal && this.charts.setorMensal.data.datasets.length > 1) {
            this.charts.setorMensal.data.datasets.pop();
            this.charts.setorMensal.update();
            console.log('✅ Removido ano anterior do gráfico do setor');
        }
    }
    
    async drillDownCliente(clienteId, nomeCliente) {
        console.log(`🔍 Drill-down para cliente: ${nomeCliente} (ID: ${clienteId})`);
        
        try {
            // Mostrar modal
            this.mostrarDrillModal(nomeCliente);
            
            // Buscar dados detalhados do cliente
            await this.carregarDadosCliente(clienteId, nomeCliente);
            
        } catch (error) {
            console.error('Erro no drill-down:', error);
            alert('Erro ao carregar dados do cliente. Tente novamente.');
        }
    }
    
    mostrarDrillModal(nomeCliente) {
        const modal = document.getElementById('cliente-drill-modal');
        const clienteNome = document.getElementById('drill-cliente-nome');
        
        if (modal && clienteNome) {
            clienteNome.textContent = `Detalhes - ${nomeCliente}`;
            modal.style.display = 'block';
            
            // Setup close listeners
            this.setupDrillModalListeners();
            
            console.log('✅ Modal de drill-down exibido');
        }
    }
    
    setupDrillModalListeners() {
        const modal = document.getElementById('cliente-drill-modal');
        const closeBtn = document.getElementById('close-drill-modal');
        const closeFooterBtn = document.getElementById('drill-close-btn');
        
        const fecharModal = () => {
            if (modal) {
                modal.style.display = 'none';
                
                // Destruir gráfico se existir
                if (this.charts.drillMensal) {
                    this.charts.drillMensal.destroy();
                    delete this.charts.drillMensal;
                }
            }
        };
        
        if (closeBtn) {
            closeBtn.onclick = fecharModal;
        }
        
        if (closeFooterBtn) {
            closeFooterBtn.onclick = fecharModal;
        }
        
        // Fechar ao clicar fora do modal
        window.onclick = (event) => {
            if (event.target == modal) {
                fecharModal();
            }
        };
    }
    
    async carregarDadosCliente(clienteId, nomeCliente) {
        try {
            // Obter setor ativo
            const activeButton = document.querySelector('.sector-btn.active');
            const setor = activeButton?.getAttribute('data-setor') || 'importacao';
            
            // Chamar API
            const response = await fetch(`/financeiro/faturamento/api/geral/cliente/${clienteId}/detalhes?setor=${setor}&ano=${this.currentAno}`);
            const data = await response.json();
            
            if (!data.success) {
                throw new Error(data.message || 'Erro ao carregar dados do cliente');
            }
            
            const clienteData = data.data;
            
            // Atualizar KPIs
            this.atualizarKPIsCliente(clienteData);
            
            // Atualizar gráfico mensal
            this.atualizarGraficoMensalCliente(clienteData);
            
            // Atualizar breakdown
            this.atualizarBreakdownCliente(clienteData);
            
            console.log('✅ Dados do cliente carregados');
            
        } catch (error) {
            console.error('Erro ao carregar dados do cliente:', error);
            this.mostrarErroCliente();
        }
    }
    
    atualizarKPIsCliente(data) {
        // Faturamento Total
        document.getElementById('drill-faturamento-total').textContent = 
            this.formatarMoeda(data.faturamento_total || 0);
        
        // Participação no Setor
        document.getElementById('drill-participacao-setor').textContent = 
            `${(data.participacao_setor || 0).toFixed(1)}%`;
        
        // Crescimento
        const crescimento = data.crescimento_percentual || 0;
        const crescimentoElement = document.getElementById('drill-crescimento');
        crescimentoElement.textContent = `${crescimento >= 0 ? '+' : ''}${crescimento.toFixed(1)}%`;
        
        // Atualizar cor baseado no crescimento
        const kpiCard = crescimentoElement.closest('.drill-kpi-card');
        if (kpiCard) {
            const icon = kpiCard.querySelector('.drill-kpi-icon');
            if (crescimento >= 0) {
                icon.style.background = 'linear-gradient(135deg, #28a745 0%, #20c997 100%)';
            } else {
                icon.style.background = 'linear-gradient(135deg, #dc3545 0%, #e74c3c 100%)';
            }
        }
    }
    
    atualizarGraficoMensalCliente(data) {
        const ctx = document.getElementById('drill-chart-mensal');
        if (!ctx) return;
        
        // Destruir gráfico existente
        if (this.charts.drillMensal) {
            this.charts.drillMensal.destroy();
        }
        
        const dadosMensais = data.dados_mensais || [];
        const meses = dadosMensais.map(item => item.mes);
        const valores = dadosMensais.map(item => item.valor);
        
        this.charts.drillMensal = new Chart(ctx, {
            type: 'line',
            data: {
                labels: meses,
                datasets: [{
                    label: 'Faturamento Mensal',
                    data: valores,
                    borderColor: '#007bff',
                    backgroundColor: 'rgba(0,123,255,0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: (value) => this.formatarMoeda(value)
                        }
                    }
                }
            }
        });
    }
    
    atualizarBreakdownCliente(data) {
        const container = document.getElementById('drill-breakdown-content');
        if (!container) return;
        
        const breakdown = data.breakdown_centro_resultado || [];
        
        container.innerHTML = '';
        
        breakdown.forEach(centro => {
            const centroDiv = document.createElement('div');
            centroDiv.className = 'drill-breakdown-item';
            
            centroDiv.innerHTML = `
                <div class="drill-breakdown-header">
                    <span>${centro.centro_resultado}</span>
                    <span class="drill-breakdown-value">${this.formatarMoeda(centro.valor)}</span>
                </div>
                <div class="drill-breakdown-details">
                    ${centro.participacao.toFixed(1)}% do total • ${centro.categorias.length} categoria(s)
                </div>
            `;
            
            container.appendChild(centroDiv);
        });
        
        console.log(`✅ Breakdown atualizado: ${breakdown.length} centros de resultado`);
    }
    
    mostrarErroCliente() {
        // Reset KPIs
        document.getElementById('drill-faturamento-total').textContent = 'Erro';
        document.getElementById('drill-participacao-setor').textContent = 'Erro';
        document.getElementById('drill-crescimento').textContent = 'Erro';
        
        // Limpar breakdown
        const container = document.getElementById('drill-breakdown-content');
        if (container) {
            container.innerHTML = '<p style="color: #dc3545; text-align: center;">Erro ao carregar dados</p>';
        }
        
        console.error('❌ Erro exibido na interface do cliente');
    }
    
    mostrarErroSetor() {
        // Resetar KPIs
        document.getElementById('valor-faturamento-setor').textContent = 'Erro';
        document.getElementById('valor-participacao-setor').textContent = 'Erro';
        document.getElementById('valor-crescimento-setor').textContent = 'Erro';
        document.getElementById('valor-melhor-mes-setor').textContent = 'Erro';
        
        // Limpar tabela
        const tbody = document.querySelector('#tabela-ranking-setor tbody');
        if (tbody) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center">Erro ao carregar dados</td></tr>';
        }
        
        console.error('❌ Erro exibido na interface do setor');
    }
}

// Inicializar quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', function() {
    // Event listener para o botão voltar do drill-down
    const btnVoltar = document.getElementById('centro-resultado-voltar');
    if (btnVoltar) {
        btnVoltar.addEventListener('click', function() {
            if (window.faturamentoNovo) {
                window.faturamentoNovo.voltarCentroResultadoGeral();
            }
        });
        console.log('✅ Event listener do botão voltar configurado');
    } else {
        console.warn('⚠️ Botão voltar não encontrado');
    }

    // Verificar se os novos elementos existem antes de inicializar
    if (document.getElementById('year-toggles') || 
        document.getElementById('grafico-comparativo-anos') ||
        document.getElementById('centro-resultado-chart')) {
        
        console.log('Detectados novos componentes - inicializando FaturamentoControllerNovo');
        window.faturamentoNovo = new FaturamentoControllerNovo();
    } else {
        console.log('Componentes antigos detectados - mantendo FaturamentoController original');
    }
});