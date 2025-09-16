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
        
        // Configurações globais
        Chart.register(ChartDataLabels);
        Chart.defaults.plugins.datalabels.display = false;
        
        this.coresGraficos = {
            receita: '#28a745',
            despesa: '#dc3545',
            resultado: '#007bff',
            neutro: '#6c757d',
            anos: ['#007bff', '#28a745', '#dc3545', '#ffc107', '#6c757d', '#17a2b8']
        };
        
        this.init();
    }
    
    async init() {
        console.log('Inicializando FaturamentoControllerNovo...');
        
        try {
            await this.buscarAnosDisponiveis();
            await this.carregarTodosOsDados();
        } catch (error) {
            console.error('Erro na inicialização:', error);
        }
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
            const response = await fetch('/financeiro/faturamento/api/geral/comparativo_anos');
            const data = await response.json();
            
            if (data.success) {
                this.anosDisponiveis = [...new Set(data.data.map(item => item.ano))].sort((a, b) => b - a);
                this.anosAtivos = new Set(this.anosDisponiveis.slice(0, 3));
                this.renderizarToggleAnos();
                console.log('Anos disponíveis:', this.anosDisponiveis);
            }
        } catch (error) {
            console.error('Erro ao buscar anos disponíveis:', error);
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
            'loading-sunburst',
            'loading-tabela'
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
                this.carregarGraficoSunburst(),
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
            console.log('Carregando KPIs...');
            const response = await fetch('/financeiro/faturamento/api/geral/mensal');
            const data = await response.json();
            
            if (data.success && data.data.length > 0) {
                this.calcularKPIs(data.data);
            } else if (data.anos_disponiveis && data.meses) {
                // Formato antigo - converter
                this.calcularKPIsFormatoAntigo(data);
            }
        } catch (error) {
            console.error('Erro ao carregar KPIs:', error);
        }
    }
    
    calcularKPIs(dados) {
        const anoAtual = new Date().getFullYear();
        const mesAtual = new Date().getMonth() + 1;
        
        // Filtrar dados do ano atual
        const dadosAnoAtual = dados.filter(item => item.ano === anoAtual);
        const dadosAnoAnterior = dados.filter(item => item.ano === anoAtual - 1);
        
        // KPI 1: Resultado do mês atual
        const resultadoMesAtual = dadosAnoAtual.find(item => item.mes === mesAtual)?.resultado_mensal || 0;
        this.atualizarElemento('resultado-mes-atual', this.formatarMoeda(resultadoMesAtual));
        
        // KPI 2: Resultado acumulado do ano
        const resultadoAcumulado = dadosAnoAtual.reduce((acc, item) => acc + item.resultado_mensal, 0);
        this.atualizarElemento('resultado-acumulado-ano', this.formatarMoeda(resultadoAcumulado));
        
        // KPI 3: Comparação com ano anterior
        const resultadoAnoAnteriorTotal = dadosAnoAnterior.reduce((acc, item) => acc + item.resultado_mensal, 0);
        const variacaoAnual = resultadoAnoAnteriorTotal ? 
            ((resultadoAcumulado - resultadoAnoAnteriorTotal) / Math.abs(resultadoAnoAnteriorTotal)) * 100 : 0;
        
        const elementoVariacao = document.getElementById('variacao-ano-anterior');
        if (elementoVariacao) {
            elementoVariacao.textContent = `${variacaoAnual >= 0 ? '+' : ''}${variacaoAnual.toFixed(1)}%`;
            elementoVariacao.className = `badge ${variacaoAnual >= 0 ? 'bg-success' : 'bg-danger'}`;
        }
        
        // KPI 4: Melhor mês do ano
        const melhorMes = dadosAnoAtual.reduce((melhor, atual) => {
            return atual.resultado_mensal > melhor.resultado_mensal ? atual : melhor;
        }, { resultado_mensal: -Infinity, mes: 0 });
        
        const nomesMeses = ['', 'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
        if (melhorMes.mes > 0) {
            this.atualizarElemento('melhor-mes', `${nomesMeses[melhorMes.mes]} (${this.formatarMoeda(melhorMes.resultado_mensal)})`);
        }
        
        console.log('KPIs calculados e atualizados');
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
        const elemento = document.getElementById(id);
        if (elemento) {
            elemento.textContent = valor;
        } else {
            console.warn(`Elemento ${id} não encontrado`);
        }
    }
    
    async carregarGraficoComparativo() {
        try {
            console.log('Carregando gráfico comparativo...');
            const response = await fetch('/financeiro/faturamento/api/geral/comparativo_anos');
            const data = await response.json();
            
            if (data.success) {
                this.renderizarGraficoComparativo(data.data);
            }
        } catch (error) {
            console.error('Erro ao carregar gráfico comparativo:', error);
        }
    }
    
    renderizarGraficoComparativo(dados) {
        const canvas = document.getElementById('grafico-comparativo-anos');
        if (!canvas) {
            console.error('Canvas grafico-comparativo-anos não encontrado');
            return;
        }
        
        const ctx = canvas.getContext('2d');
        
        // Destruir gráfico anterior
        if (this.charts.comparativo) {
            this.charts.comparativo.destroy();
        }
        
        // Filtrar dados pelos anos ativos
        const dadosFiltrados = dados.filter(item => this.anosAtivos.has(item.ano));
        
        // Preparar datasets por ano
        const datasets = [];
        const anosOrdenados = [...this.anosAtivos].sort((a, b) => b - a);
        
        anosOrdenados.forEach((ano, index) => {
            const dadosAno = dadosFiltrados.filter(item => item.ano === ano);
            
            datasets.push({
                label: ano.toString(),
                data: dadosAno.map(item => ({
                    x: item.mes,
                    y: item.resultado_mensal
                })),
                borderColor: this.coresGraficos.anos[index % this.coresGraficos.anos.length],
                backgroundColor: this.coresGraficos.anos[index % this.coresGraficos.anos.length] + '20',
                borderWidth: 2,
                fill: false,
                tension: 0.1
            });
        });

        this.charts.comparativo = new Chart(ctx, {
            type: 'line',
            data: { datasets: datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        type: 'linear',
                        position: 'bottom',
                        min: 1,
                        max: 12,
                        ticks: {
                            stepSize: 1,
                            callback: function(value) {
                                const meses = ['', 'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
                                             'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
                                return meses[value] || '';
                            }
                        },
                        title: { display: true, text: 'Mês' }
                    },
                    y: {
                        ticks: {
                            callback: (value) => this.formatarMoedaCompacta(value)
                        },
                        title: { display: true, text: 'Resultado Mensal' }
                    }
                },
                plugins: {
                    legend: { display: true, position: 'top' },
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                const meses = ['', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                                             'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];
                                return `${context.dataset.label} - ${meses[context.parsed.x]}: ${this.formatarMoeda(context.parsed.y)}`;
                            }
                        }
                    },
                    datalabels: { display: false }
                }
            }
        });
        
        console.log('Gráfico comparativo renderizado');
    }
    
    async carregarGraficoSunburst() {
        try {
            console.log('Carregando gráfico sunburst...');
            const response = await fetch('/financeiro/faturamento/api/geral/proporcao');
            const data = await response.json();
            
            if (data.success) {
                this.renderizarGraficoSunburst(data.data);
            }
        } catch (error) {
            console.error('Erro ao carregar sunburst:', error);
        }
    }
    
    renderizarGraficoSunburst(dados) {
        const canvas = document.getElementById('grafico-sunburst');
        if (!canvas) {
            console.error('Canvas grafico-sunburst não encontrado');
            return;
        }
        
        const ctx = canvas.getContext('2d');
        
        // Destruir gráfico anterior
        if (this.charts.sunburst) {
            this.charts.sunburst.destroy();
        }
        
        // Processar dados para sunburst
        const resultados = {};
        dados.forEach(item => {
            if (!resultados[item.resultado]) {
                resultados[item.resultado] = { total: 0, categorias: {} };
            }
            resultados[item.resultado].total += Math.abs(item.valor_total);
            resultados[item.resultado].categorias[item.categoria] = Math.abs(item.valor_total);
        });

        // Criar datasets
        const labels = [];
        const data = [];
        const backgroundColor = [];
        
        Object.keys(resultados).forEach((resultado, resultadoIndex) => {
            const corBase = resultado === 'Receita' ? '#28a745' : '#dc3545';
            
            Object.keys(resultados[resultado].categorias).forEach((categoria, categoriaIndex) => {
                labels.push(`${resultado} - ${categoria}`);
                data.push(resultados[resultado].categorias[categoria]);
                
                const opacity = 0.6 + (categoriaIndex * 0.1);
                backgroundColor.push(corBase + Math.floor(opacity * 255).toString(16).padStart(2, '0'));
            });
        });

        this.charts.sunburst = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: backgroundColor,
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
                        position: 'right'
                    },
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((context.parsed / total) * 100).toFixed(1);
                                return `${context.label}: ${this.formatarMoeda(context.parsed)} (${percentage}%)`;
                            }
                        }
                    },
                    datalabels: { display: false }
                }
            }
        });
        
        console.log('Gráfico sunburst renderizado');
    }
    
    async carregarTabelaComparativa() {
        try {
            console.log('Carregando tabela comparativa...');
            const response = await fetch('/financeiro/faturamento/api/geral/mensal');
            const data = await response.json();
            
            if (data.success) {
                this.renderizarTabelaComparativa(data.data);
            } else if (data.anos_disponiveis && data.meses) {
                // Formato antigo
                this.renderizarTabelaFormatoAntigo(data);
            }
        } catch (error) {
            console.error('Erro ao carregar tabela:', error);
        }
    }
    
    renderizarTabelaComparativa(dados) {
        const tbody = document.querySelector('#tabela-comparativo-mensal tbody');
        if (!tbody) {
            console.error('Tbody da tabela não encontrado');
            return;
        }
        
        tbody.innerHTML = '';
        
        // Organizar dados por mês e ano
        const dadosPorMes = {};
        const anos = new Set();
        
        dados.forEach(item => {
            const mes = item.mes;
            const ano = item.ano;
            anos.add(ano);
            
            if (!dadosPorMes[mes]) {
                dadosPorMes[mes] = {};
            }
            dadosPorMes[mes][ano] = item.resultado_mensal;
        });
        
        const anosOrdenados = [...anos].sort((a, b) => b - a);
        
        // Atualizar cabeçalho
        const thead = document.querySelector('#tabela-comparativo-mensal thead tr');
        if (thead) {
            thead.innerHTML = '<th>Mês</th>';
            anosOrdenados.forEach(ano => {
                thead.innerHTML += `<th class="text-center year-column-${ano}">${ano}</th>`;
            });
        }
        
        // Criar linhas para cada mês
        const meses = [
            { num: 1, nome: 'Janeiro' }, { num: 2, nome: 'Fevereiro' }, { num: 3, nome: 'Março' },
            { num: 4, nome: 'Abril' }, { num: 5, nome: 'Maio' }, { num: 6, nome: 'Junho' },
            { num: 7, nome: 'Julho' }, { num: 8, nome: 'Agosto' }, { num: 9, nome: 'Setembro' },
            { num: 10, nome: 'Outubro' }, { num: 11, nome: 'Novembro' }, { num: 12, nome: 'Dezembro' }
        ];
        
        meses.forEach(mes => {
            const row = document.createElement('tr');
            row.innerHTML = `<td>${mes.nome}</td>`;
            
            anosOrdenados.forEach(ano => {
                const valor = dadosPorMes[mes.num] && dadosPorMes[mes.num][ano] || 0;
                const classe = valor >= 0 ? 'text-success' : 'text-danger';
                row.innerHTML += `<td class="text-end ${classe} year-column-${ano}">${this.formatarMoeda(valor)}</td>`;
            });
            
            tbody.appendChild(row);
        });
        
        console.log('Tabela comparativa renderizada');
    }
    
    renderizarTabelaFormatoAntigo(data) {
        // Implementar renderização para formato antigo se necessário
        console.log('Renderizando tabela formato antigo...');
    }
}

// Inicializar quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', function() {
    // Verificar se os novos elementos existem antes de inicializar
    if (document.getElementById('year-toggles') || 
        document.getElementById('grafico-comparativo-anos') ||
        document.getElementById('grafico-sunburst')) {
        
        console.log('Detectados novos componentes - inicializando FaturamentoControllerNovo');
        window.faturamentoNovo = new FaturamentoControllerNovo();
    } else {
        console.log('Componentes antigos detectados - mantendo FaturamentoController original');
    }
});