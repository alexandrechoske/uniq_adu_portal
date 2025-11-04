/**
 * Dashboard Executivo RH - JavaScript
 * Baseado no Dashboard Executivo Financeiro
 * Versão: 3.7 - Novos KPIs de Admissões e Demissões
 * Data: 04/11/2025
 * 
 * Novidades v3.7:
 * - Adicionados KPIs de Total de Admissões e Total de Demissões no período
 * 
 * Correções anteriores (v3.6):
 * - IDs corretos para campos de data personalizada (data-inicio e data-fim)
 * - Adição do parâmetro empresa na requisição API
 * - Logs de debug para troubleshooting
 */

// ========================================
// VARIÁVEIS GLOBAIS
// ========================================

let chartEvolucaoHeadcount = null;
let chartTurnoverDepartamento = null;
let chartDistribuicaoDepartamento = null;
let chartDispersaoTempoSalario = null;

// ========================================
// INICIALIZAÇÃO
// ========================================

// Registrar plugin de datalabels
Chart.register(ChartDataLabels);

document.addEventListener('DOMContentLoaded', function() {
    console.log('📊 Dashboard Executivo RH - Inicializado (v3.6 - Correção de Filtros)');
    console.log('✅ Correções aplicadas: IDs de data, filtro de empresa, logs de debug');
    
    // Inicializar componentes
    inicializarFiltros();
    configurarEventosFiltros();
    
    // Carregar dados iniciais
    carregarDadosDashboard();
});

// ========================================
// FILTROS
// ========================================

/**
 * Inicializar opções dos filtros
 */
function inicializarFiltros() {
    // TODO: Carregar empresas e departamentos dinamicamente
    // Será implementado quando necessário
    
    console.log('🔍 Filtros inicializados');
}

/**
 * Configurar eventos dos filtros
 */
function configurarEventosFiltros() {
    const periodoFilter = document.getElementById('periodo-filter');
    const empresaFilter = document.getElementById('empresa-filter');
    const departamentoFilter = document.getElementById('departamento-filter');
    const customDateGroup = document.getElementById('custom-date-group');
    const customDateEndGroup = document.getElementById('custom-date-end-group');
    const resetFiltersBtn = document.getElementById('reset-filters');
    
    // Mostrar/ocultar campos de data personalizada
    if (periodoFilter) {
        periodoFilter.addEventListener('change', function() {
            const isCustom = this.value === 'personalizado';
            if (customDateGroup) customDateGroup.style.display = isCustom ? 'flex' : 'none';
            if (customDateEndGroup) customDateEndGroup.style.display = isCustom ? 'flex' : 'none';
            if (resetFiltersBtn) resetFiltersBtn.style.display = 'inline-flex';
            
            // Atualizar dashboard automaticamente (exceto quando personalizado - aguarda datas)
            if (!isCustom) {
                console.log('🔄 Período alterado, atualizando dashboard...');
                atualizarDashboard();
            }
        });
    }
    
    // Atualizar dashboard automaticamente quando mudar empresa
    if (empresaFilter) {
        empresaFilter.addEventListener('change', function() {
            console.log('🔄 Empresa alterada, atualizando dashboard...');
            if (resetFiltersBtn) resetFiltersBtn.style.display = 'inline-flex';
            atualizarDashboard();
        });
    }
    
    // Atualizar dashboard automaticamente quando mudar departamento
    if (departamentoFilter) {
        departamentoFilter.addEventListener('change', function() {
            console.log('🔄 Departamento alterado, atualizando dashboard...');
            if (resetFiltersBtn) resetFiltersBtn.style.display = 'inline-flex';
            atualizarDashboard();
        });
    }
    
    // Atualizar dashboard quando mudar datas personalizadas
    const dataInicioInput = document.getElementById('data-inicio');
    const dataFimInput = document.getElementById('data-fim');
    
    if (dataInicioInput) {
        dataInicioInput.addEventListener('change', function() {
            // Só atualiza se ambas as datas estiverem preenchidas
            if (dataFimInput && dataFimInput.value) {
                console.log('🔄 Datas alteradas, atualizando dashboard...');
                atualizarDashboard();
            }
        });
    }
    
    if (dataFimInput) {
        dataFimInput.addEventListener('change', function() {
            // Só atualiza se ambas as datas estiverem preenchidas
            if (dataInicioInput && dataInicioInput.value) {
                console.log('🔄 Datas alteradas, atualizando dashboard...');
                atualizarDashboard();
            }
        });
    }
    
    console.log('✅ Event listeners de filtros configurados');
}

/**
 * Aplicar filtros selecionados
 */
function aplicarFiltros() {
    const periodo = document.getElementById('periodo-filter').value;
    const empresa = document.getElementById('empresa-filter')?.value || 'todas';
    const departamento = document.getElementById('departamento-filter')?.value || 'todos';
    
    console.log('🔄 Aplicando filtros:', {
        periodo: periodo,
        empresa: empresa,
        departamento: departamento
    });
    
    // Recarregar dashboard com novos filtros
    carregarDadosDashboard();
}

/**
 * Limpar todos os filtros
 */
function limparFiltros() {
    // Resetar filtros para valores padrão
    const periodoFilter = document.getElementById('periodo-filter');
    const empresaFilter = document.getElementById('empresa-filter');
    const departamentoFilter = document.getElementById('departamento-filter');
    const customDateGroup = document.getElementById('custom-date-group');
    const customDateEndGroup = document.getElementById('custom-date-end-group');
    const resetFiltersBtn = document.getElementById('reset-filters');
    const filterSummary = document.getElementById('filter-summary');
    
    if (periodoFilter) periodoFilter.value = 'este_ano';
    if (empresaFilter) empresaFilter.value = 'todas';
    if (departamentoFilter) departamentoFilter.value = 'todos';
    if (customDateGroup) customDateGroup.style.display = 'none';
    if (customDateEndGroup) customDateEndGroup.style.display = 'none';
    if (resetFiltersBtn) resetFiltersBtn.style.display = 'none';
    if (filterSummary) filterSummary.style.display = 'none';
    
    console.log('🔄 Filtros resetados');
    
    // Recarregar dados com filtros padrão
    aplicarFiltros();
}

/**
 * Atualizar resumo dos filtros aplicados
 */
function atualizarResumoFiltros() {
    const periodo = document.getElementById('periodo-filter').value;
    const empresa = document.getElementById('empresa-filter').value;
    const departamento = document.getElementById('departamento-filter').value;
    const filterSummary = document.getElementById('filter-summary');
    const filterSummaryText = document.getElementById('filter-summary-text');
    
    // Verificar se há filtros aplicados além dos padrões
    const hasFilters = 
        periodo !== 'este_ano' || 
        empresa !== 'todas' || 
        departamento !== 'todos';
    
    if (hasFilters && filterSummary && filterSummaryText) {
        let summaryParts = [];
        
        // Texto do período
        const periodoTexts = {
            'este_ano': 'Este Ano',
            'este_mes': 'Este Mês',
            'ultimos_12_meses': 'Últimos 12 Meses',
            'ano_anterior': 'Ano Anterior',
            'trimestre_atual': 'Trimestre Atual',
            'personalizado': 'Período Personalizado'
        };
        
        if (periodo !== 'este_ano') {
            summaryParts.push(`Período: ${periodoTexts[periodo] || periodo}`);
        }
        
        if (empresa !== 'todas') {
            const empresaText = document.getElementById('empresa-filter').selectedOptions[0]?.text;
            summaryParts.push(`Empresa: ${empresaText}`);
        }
        
        if (departamento !== 'todos') {
            const departamentoText = document.getElementById('departamento-filter').selectedOptions[0]?.text;
            summaryParts.push(`Departamento: ${departamentoText}`);
        }
        
        filterSummaryText.textContent = summaryParts.join(' • ');
        filterSummary.style.display = 'block';
    } else if (filterSummary) {
        filterSummary.style.display = 'none';
    }
}

// ========================================
// ATUALIZAÇÃO DE DADOS
// ========================================

/**
 * Atualizar dados do dashboard
 */
async function atualizarDashboard() {
    console.log('🔄 Atualizando dashboard...');
    await carregarDadosDashboard();
}

/**
 * Carregar dados do dashboard
 */
async function carregarDadosDashboard() {
    console.log('📥 Carregando dados do dashboard...');
    
    mostrarLoading();
    
    try {
        const periodo = document.getElementById('periodo-filter').value;
        const empresa = document.getElementById('empresa-filter')?.value || 'todas';
        const departamento = document.getElementById('departamento-filter')?.value || 'todos';
        
        // Calcular datas baseado no período selecionado
        const { inicio, fim } = calcularPeriodo(periodo);
        
        console.log('📅 Período calculado:', { periodo, inicio, fim, empresa, departamento });
        
        // Buscar dados da API
        const params = new URLSearchParams({
            periodo_inicio: inicio,
            periodo_fim: fim
        });
        
        // Adicionar empresa ao filtro
        if (empresa && empresa !== 'todas') {
            params.append('empresa', empresa);
        }
        
        // Adicionar departamento ao filtro
        if (departamento !== 'todos') {
            params.append('departamentos[]', departamento);
        }
        
        console.log('🔗 URL da API:', `/rh/dashboard/api/dados?${params.toString()}`);
        
        const response = await fetch(`/rh/dashboard/api/dados?${params.toString()}`, {
            credentials: 'same-origin'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        if (!result.success) {
            throw new Error(result.message || 'Erro ao carregar dados');
        }
        
        console.log('✅ Dados carregados com sucesso:', result.data);
        
        // Renderizar componentes
        renderizarKPIs(result.data.kpis);
        renderizarGraficos(result.data.graficos);
        renderizarTabelas(result.data.tabelas);
        
    } catch (error) {
        console.error('❌ Erro ao carregar dados:', error);
        alert('❌ Erro ao carregar dados do dashboard. Verifique o console.');
    } finally {
        esconderLoading();
    }
}

/**
 * Calcular período baseado na seleção
 */
function calcularPeriodo(periodo) {
    const hoje = new Date();
    let inicio, fim;
    
    switch(periodo) {
        case 'este_mes':
            inicio = new Date(hoje.getFullYear(), hoje.getMonth(), 1);
            fim = hoje;
            break;
            
        case 'este_trimestre':
            const trimestreAtual = Math.floor(hoje.getMonth() / 3);
            inicio = new Date(hoje.getFullYear(), trimestreAtual * 3, 1);
            fim = hoje;
            break;
            
        case 'este_ano':
            inicio = new Date(hoje.getFullYear(), 0, 1);
            fim = hoje;
            break;
            
        case 'ultimos_12_meses':
            inicio = new Date(hoje.getFullYear(), hoje.getMonth() - 11, 1);
            fim = hoje;
            break;
            
        case 'ano_anterior':
            inicio = new Date(hoje.getFullYear() - 1, 0, 1);
            fim = new Date(hoje.getFullYear() - 1, 11, 31);
            break;
            
        case 'personalizado':
            // CORREÇÃO: IDs corretos dos campos de data
            const dataInicioInput = document.getElementById('data-inicio');
            const dataFimInput = document.getElementById('data-fim');
            
            if (!dataInicioInput || !dataFimInput) {
                console.error('❌ Campos de data personalizada não encontrados');
                inicio = new Date(hoje.getFullYear(), 0, 1);
                fim = hoje;
            } else {
                const dataInicio = dataInicioInput.value;
                const dataFim = dataFimInput.value;
                inicio = dataInicio ? new Date(dataInicio) : new Date(hoje.getFullYear(), 0, 1);
                fim = dataFim ? new Date(dataFim) : hoje;
            }
            break;
            
        default:
            inicio = new Date(hoje.getFullYear(), 0, 1);
            fim = hoje;
    }
    
    return {
        inicio: formatarDataISO(inicio),
        fim: formatarDataISO(fim)
    };
}

/**
 * Formatar data para ISO (YYYY-MM-DD)
 */
function formatarDataISO(data) {
    const ano = data.getFullYear();
    const mes = String(data.getMonth() + 1).padStart(2, '0');
    const dia = String(data.getDate()).padStart(2, '0');
    return `${ano}-${mes}-${dia}`;
}

// ========================================
// UTILITÁRIOS
// ========================================

/**
 * Mostrar overlay de loading
 */
function mostrarLoading() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.style.display = 'flex';
    }
}

/**
 * Esconder overlay de loading
 */
function esconderLoading() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.style.display = 'none';
    }
}

/**
 * Formatar número com separadores
 */
function formatarNumero(numero) {
    return numero.toLocaleString('pt-BR');
}

/**
 * Formatar valor monetário
 */
function formatarMoeda(valor) {
    return valor.toLocaleString('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    });
}

/**
 * Formatar percentual
 */
function formatarPercentual(valor, casasDecimais = 1) {
    return valor.toFixed(casasDecimais) + '%';
}

/**
 * Calcular variação percentual
 */
function calcularVariacao(valorAtual, valorAnterior) {
    if (valorAnterior === 0) return 0;
    return ((valorAtual - valorAnterior) / valorAnterior) * 100;
}

/**
 * Obter classe CSS para variação (positive, negative, neutral)
 */
function getVariationClass(value) {
    if (value > 0) return 'positive';
    if (value < 0) return 'negative';
    return 'neutral';
}

/**
 * Formatar variação com ícone
 */
function formatarVariacaoComIcone(valor) {
    const variacao = formatarPercentual(Math.abs(valor));
    const classe = getVariationClass(valor);
    const icone = valor > 0 ? '↑' : valor < 0 ? '↓' : '→';
    
    return `<span class="kpi-comparison ${classe}">${icone} ${variacao}</span>`;
}

// ========================================
// FUNÇÕES DE RENDERIZAÇÃO (PLACEHOLDERS)
// ========================================

/**
 * Renderizar KPIs
 */
function renderizarKPIs(dados) {
    console.log('📊 Renderizando KPIs...', dados);
    
    // KPI 1: Headcount
    if (dados.headcount) {
        const elemento = document.getElementById('kpi-headcount-valor');
        console.log('KPI Headcount - Elemento:', elemento, 'Valor:', dados.headcount.valor);
        if (elemento) {
            elemento.textContent = formatarNumero(dados.headcount.valor);
        }
        atualizarVariacaoKPI('kpi-headcount-variacao', dados.headcount.variacao);
    }
    
    // KPI 2: Custo Salários (Folha)
    if (dados.custo_salarios) {
        const elemento = document.getElementById('kpi-custo-salarios-valor');
        console.log('KPI Custo Salários - Elemento:', elemento, 'Valor:', dados.custo_salarios.valor);
        if (elemento) {
            elemento.textContent = formatarMoeda(dados.custo_salarios.valor);
        }
        atualizarVariacaoKPI('kpi-custo-salarios-variacao', dados.custo_salarios.variacao);
    }
    
    // KPI 3: Custo Benefícios
    if (dados.custo_beneficios) {
        const elemento = document.getElementById('kpi-custo-beneficios-valor');
        console.log('KPI Custo Benefícios - Elemento:', elemento, 'Valor:', dados.custo_beneficios.valor);
        if (elemento) {
            elemento.textContent = formatarMoeda(dados.custo_beneficios.valor);
        }
        atualizarVariacaoKPI('kpi-custo-beneficios-variacao', dados.custo_beneficios.variacao);
    }
    
    // KPI 4: Custo Total (Pessoal)
    if (dados.custo_total) {
        const elemento = document.getElementById('kpi-custo-total-valor');
        console.log('KPI Custo Total - Elemento:', elemento, 'Valor:', dados.custo_total.valor);
        if (elemento) {
            elemento.textContent = formatarMoeda(dados.custo_total.valor);
        }
        atualizarVariacaoKPI('kpi-custo-total-variacao', dados.custo_total.variacao);
    }
    
    // KPI 5: Turnover
    if (dados.turnover) {
        const elemento = document.getElementById('kpi-turnover-valor');
        console.log('KPI Turnover - Elemento:', elemento, 'Valor:', dados.turnover.valor);
        if (elemento) {
            elemento.textContent = formatarPercentual(dados.turnover.valor);
        }
        atualizarVariacaoKPI('kpi-turnover-variacao', dados.turnover.variacao);
    }
    
    // KPI 6: Tempo de Contratação
    if (dados.tempo_contratacao) {
        const valor = dados.tempo_contratacao.valor;
        const elemento = document.getElementById('kpi-tempo-contratacao-valor');
        console.log('KPI Tempo Contratação - Elemento:', elemento, 'Valor:', valor);
        if (elemento) {
            elemento.textContent = valor + ' dias';
        }
        atualizarVariacaoKPI('kpi-tempo-contratacao-variacao', dados.tempo_contratacao.variacao);
    }
    
    // KPI 7: Vagas em Aberto
    if (dados.vagas_abertas) {
        const elemento = document.getElementById('kpi-vagas-abertas-valor');
        if (elemento) {
            elemento.textContent = formatarNumero(dados.vagas_abertas.valor);
        }
        atualizarVariacaoKPI('kpi-vagas-abertas-variacao', dados.vagas_abertas.variacao);
    }
    
    // KPI 8: Média Candidatos/Vaga
    if (dados.media_candidatos_vaga) {
        const elemento = document.getElementById('kpi-media-candidatos-valor');
        if (elemento) {
            elemento.textContent = dados.media_candidatos_vaga.valor.toFixed(1);
        }
        atualizarVariacaoKPI('kpi-media-candidatos-variacao', dados.media_candidatos_vaga.variacao);
    }
    
    // KPI 9: Tempo Médio de Casa
    if (dados.tempo_medio_casa) {
        const elemento = document.getElementById('kpi-tempo-casa-valor');
        if (elemento) {
            elemento.textContent = dados.tempo_medio_casa.valor.toFixed(1) + ' anos';
        }
        atualizarVariacaoKPI('kpi-tempo-casa-variacao', dados.tempo_medio_casa.variacao);
    }
    
    // KPI 10: Idade Média
    if (dados.idade_media) {
        const elemento = document.getElementById('kpi-idade-media-valor');
        if (elemento) {
            elemento.textContent = dados.idade_media.valor + ' anos';
        }
        atualizarVariacaoKPI('kpi-idade-media-variacao', dados.idade_media.variacao);
    }
    
    // KPI 11: Total de Admissões
    if (dados.total_admissoes) {
        const elemento = document.getElementById('kpi-admissoes-valor');
        if (elemento) {
            elemento.textContent = formatarNumero(dados.total_admissoes.valor);
        }
        atualizarVariacaoKPI('kpi-admissoes-variacao', dados.total_admissoes.variacao);
    }
    
    // KPI 12: Total de Demissões
    if (dados.total_demissoes) {
        const elemento = document.getElementById('kpi-demissoes-valor');
        if (elemento) {
            elemento.textContent = formatarNumero(dados.total_demissoes.valor);
        }
        atualizarVariacaoKPI('kpi-demissoes-variacao', dados.total_demissoes.variacao);
    }
    
    console.log('✅ KPIs renderizados com sucesso');
}

/**
 * Atualizar badge de variação do KPI
 */
function atualizarVariacaoKPI(elementId, variacao) {
    const element = document.getElementById(elementId);
    if (!element || variacao === 0) {
        if (element) element.style.display = 'none';
        return;
    }
    
    const classe = getVariationClass(variacao);
    const icone = variacao > 0 ? '↑' : '↓';
    
    element.className = `kpi-comparison ${classe}`;
    element.textContent = `${icone} ${formatarPercentual(Math.abs(variacao))}`;
    element.style.display = 'inline-flex';
}

/**
 * Renderizar gráficos
 */
function renderizarGraficos(dados) {
    console.log('� Renderizando gráficos...', dados);
    
    // Gráfico 1: Evolução Headcount
    if (dados.evolucao_headcount) {
        renderizarGraficoEvolucao(dados.evolucao_headcount);
    }
    
    // Gráfico 2: Turnover por Departamento
    if (dados.turnover_departamento) {
        renderizarGraficoTurnoverDepartamento(dados.turnover_departamento);
    }
    
    // Gráfico 3: Custo Total por Departamento (NOVO - substitui distribuição)
    if (dados.custo_departamento) {
        renderizarGraficoCustoDepartamento(dados.custo_departamento);
    }
    
    // Gráfico 4: Dispersão Tempo vs Salário
    if (dados.dispersao_tempo_salario) {
        renderizarGraficoDispersao(dados.dispersao_tempo_salario);
    }
}

/**
 * Renderizar gráfico de evolução de headcount
 */
function renderizarGraficoEvolucao(dados) {
    const ctx = document.getElementById('chart-evolucao-headcount');
    if (!ctx) return;
    
    // Destruir gráfico anterior se existir
    if (chartEvolucaoHeadcount) {
        chartEvolucaoHeadcount.destroy();
    }
    
    // Formatar labels (YYYY-MM para Mês/Ano)
    const labels = dados.labels.map(label => {
        const [ano, mes] = label.split('-');
        const meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
        return `${meses[parseInt(mes) - 1]}/${ano.substring(2)}`;
    });
    
    // Calcular saldo líquido (Admissões - Demissões)
    const saldoLiquido = dados.datasets.admissoes.map((admissao, index) => {
        return admissao - dados.datasets.desligamentos[index];
    });
    
    chartEvolucaoHeadcount = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Admissões',
                    data: dados.datasets.admissoes,
                    backgroundColor: '#28a745',
                    yAxisID: 'y',
                    order: 2
                },
                {
                    label: 'Demissões',
                    data: dados.datasets.desligamentos,
                    backgroundColor: '#dc3545',
                    yAxisID: 'y',
                    order: 3
                },
                {
                    label: 'Saldo Líquido',
                    data: saldoLiquido,
                    type: 'line',
                    borderColor: '#0d6efd',
                    backgroundColor: 'rgba(13, 110, 253, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    yAxisID: 'y',
                    order: 1,
                    tension: 0.4,
                    pointRadius: 4,
                    pointHoverRadius: 6
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                },
                title: {
                    display: true,
                    text: 'Admissões e Demissões Mensais (com Saldo Líquido)',
                    font: { size: 16, weight: 'bold' }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.parsed.y !== null) {
                                const value = context.parsed.y;
                                if (context.dataset.label === 'Saldo Líquido') {
                                    label += value >= 0 ? `+${value}` : value;
                                    label += ' pessoas';
                                } else {
                                    label += value + ' pessoas';
                                }
                            }
                            return label;
                        }
                    }
                },
                datalabels: {
                    anchor: 'end',
                    align: 'top',
                    font: {
                        weight: 'bold',
                        size: 10
                    },
                    color: function(context) {
                        if (context.dataset.label === 'Saldo Líquido') {
                            const value = context.parsed && context.parsed.y ? context.parsed.y : 0;
                            return value >= 0 ? '#28a745' : '#dc3545';
                        }
                        return context.dataset.borderColor || '#000';
                    },
                    formatter: function(value, context) {
                        if (context.dataset.label === 'Saldo Líquido') {
                            return value >= 0 ? `+${value}` : value;
                        }
                        return value;
                    },
                    display: function(context) {
                        // Mostrar labels apenas para datasets visíveis
                        return true;
                    }
                }
            },
            scales: {
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: {
                        display: true,
                        text: 'Quantidade de Pessoas'
                    },
                    beginAtZero: true
                }
            }
        }
    });
}

/**
 * Renderizar gráfico de turnover por departamento
 */
function renderizarGraficoTurnoverDepartamento(dados) {
    const ctx = document.getElementById('chart-turnover-departamento');
    if (!ctx) return;
    
    if (chartTurnoverDepartamento) {
        chartTurnoverDepartamento.destroy();
    }
    
    chartTurnoverDepartamento = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: dados.labels,
            datasets: [{
                label: 'Turnover (%)',
                data: dados.data,
                backgroundColor: '#6f42c1',
                borderColor: '#5a32a3',
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
                title: {
                    display: true,
                    text: 'Taxa de Turnover por Departamento',
                    font: { size: 16, weight: 'bold' }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return context.parsed.x.toFixed(1) + '%';
                        }
                    }
                },
                datalabels: {
                    anchor: 'end',
                    align: 'right',
                    font: {
                        weight: 'bold',
                        size: 12
                    },
                    color: '#333',
                    formatter: function(value) {
                        return value.toFixed(1) + '%';
                    }
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Taxa de Turnover (%)'
                    }
                }
            }
        }
    });
}

/**
 * Renderizar gráfico de distribuição por departamento
 */
function renderizarGraficoDistribuicao(dados) {
    const ctx = document.getElementById('chart-distribuicao-departamento');
    if (!ctx) return;
    
    if (chartDistribuicaoDepartamento) {
        chartDistribuicaoDepartamento.destroy();
    }
    
    // Cores para cada departamento
    const cores = [
        '#6f42c1', '#5a32a3', '#9b72d4', '#7952b3', '#6610f2', 
        '#e83e8c', '#fd7e14', '#20c997', '#17a2b8', '#28a745'
    ];
    
    chartDistribuicaoDepartamento = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: dados.labels,
            datasets: [{
                data: dados.data,
                backgroundColor: cores.slice(0, dados.labels.length),
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
                title: {
                    display: true,
                    text: 'Distribuição de Colaboradores por Departamento',
                    font: { size: 16, weight: 'bold' }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(1);
                            return `${label}: ${value} (${percentage}%)`;
                        }
                    }
                },
                datalabels: {
                    anchor: 'center',
                    align: 'center',
                    font: {
                        weight: 'bold',
                        size: 12
                    },
                    color: '#fff',
                    formatter: function(value, context) {
                        const total = context.dataset.data.reduce((a, b) => a + b, 0);
                        const percentage = ((value / total) * 100).toFixed(1);
                        return percentage + '%';
                    }
                }
            }
        }
    });
}

/**
 * Renderizar gráfico de custo total por departamento
 */
function renderizarGraficoCustoDepartamento(dados) {
    const ctx = document.getElementById('chart-distribuicao-departamento');
    if (!ctx) return;
    
    if (chartDistribuicaoDepartamento) {
        chartDistribuicaoDepartamento.destroy();
    }
    
    // Cores para salários (verde/azul) e benefícios (laranja/amarelo)
    const corSalarios = '#0d6efd';  // Azul
    const corBeneficios = '#fd7e14';  // Laranja
    
    chartDistribuicaoDepartamento = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: dados.labels,
            datasets: [
                {
                    label: 'Salário',
                    data: dados.salarios || dados.data,  // Fallback para compatibilidade
                    backgroundColor: corSalarios,
                    borderColor: corSalarios + 'dd',
                    borderWidth: 1
                },
                {
                    label: 'Benefícios',
                    data: dados.beneficios || [],  // Dados de benefícios
                    backgroundColor: corBeneficios,
                    borderColor: corBeneficios + 'dd',
                    borderWidth: 1
                }
            ]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        font: { size: 12, weight: 'bold' },
                        boxWidth: 15,
                        padding: 15
                    }
                },
                title: {
                    display: true,
                    text: 'Custo por Departamento - Salários vs Benefícios',
                    font: { size: 16, weight: 'bold' }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const value = context.parsed.x;
                            const label = context.dataset.label;
                            return label + ': R$ ' + value.toLocaleString('pt-BR', {
                                minimumFractionDigits: 2,
                                maximumFractionDigits: 2
                            });
                        },
                        afterLabel: function(context) {
                            // Calcular total (salários + benefícios)
                            const index = context.dataIndex;
                            const salarios = dados.salarios[index] || 0;
                            const beneficios = dados.beneficios[index] || 0;
                            const total = salarios + beneficios;
                            return 'Total: R$ ' + total.toLocaleString('pt-BR', {
                                minimumFractionDigits: 2,
                                maximumFractionDigits: 2
                            });
                        }
                    }
                },
                datalabels: {
                    anchor: 'end',
                    align: 'right',
                    font: {
                        weight: 'bold',
                        size: 11
                    },
                    color: function(context) {
                        return context.dataset.backgroundColor;
                    },
                    formatter: function(value) {
                        return 'R$ ' + value.toLocaleString('pt-BR', {
                            minimumFractionDigits: 0,
                            maximumFractionDigits: 0
                        });
                    }
                }
            },
            scales: {
                x: {
                    stacked: false,  // Barras lado a lado (não empilhadas)
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Custo (R$)'
                    },
                    ticks: {
                        callback: function(value) {
                            return 'R$ ' + value.toLocaleString('pt-BR', {
                                minimumFractionDigits: 0,
                                maximumFractionDigits: 0
                            });
                        }
                    }
                },
                y: {
                    stacked: false  // Eixo Y não empilhado
                }
            }
        }
    });
}

/**
 * Renderizar tabelas
 */
function renderizarTabelas(dados) {
    console.log('📋 Renderizando tabelas...', dados);
    
    // Tabela 1: Vagas Abertas
    if (dados.vagas_abertas_mais_tempo) {
        renderizarTabelaVagasAbertas(dados.vagas_abertas_mais_tempo);
    }
    
    // Tabela 2: Funil de Recrutamento
    if (dados.funil_recrutamento) {
        renderizarTabelaFunilRecrutamento(dados.funil_recrutamento);
    }
}

/**
 * Renderizar tabela de vagas abertas
 */
function renderizarTabelaVagasAbertas(vagas) {
    const tbody = document.getElementById('tabela-vagas-tbody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    if (vagas.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">Nenhuma vaga aberta no momento</td></tr>';
        return;
    }
    
    vagas.forEach(vaga => {
        const tr = document.createElement('tr');
        
        // Status de urgência
        let badgeClass = 'badge-success';
        if (vaga.status_urgencia === 'alta') badgeClass = 'badge-danger';
        else if (vaga.status_urgencia === 'media') badgeClass = 'badge-warning';
        
        tr.innerHTML = `
            <td><strong>${vaga.titulo}</strong></td>
            <td>${vaga.departamento}</td>
            <td>
                <span class="badge ${badgeClass}">
                    ${vaga.dias_aberto} dias
                </span>
            </td>
            <td><strong>${vaga.custo_estimado_formatado || 'Não especificado'}</strong></td>
            <td class="text-center">
                <button class="btn btn-sm btn-outline-primary" onclick="verDetalhesVaga('${vaga.id}')">
                    <i class="mdi mdi-eye"></i> Ver
                </button>
            </td>
        `;
        
        tbody.appendChild(tr);
    });
}

/**
 * Renderizar tabela do funil de recrutamento
 */
function renderizarTabelaFunilRecrutamento(funil) {
    const tbody = document.getElementById('tabela-funil-tbody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    if (funil.length === 0) {
        tbody.innerHTML = '<tr><td colspan="3" class="text-center text-muted">Sem dados de funil no período</td></tr>';
        return;
    }
    
    funil.forEach(etapa => {
        const tr = document.createElement('tr');
        
        tr.innerHTML = `
            <td><strong>${etapa.etapa}</strong></td>
            <td class="text-center">${etapa.num_candidatos}</td>
            <td class="text-center">
                ${etapa.taxa_conversao > 0 ? 
                    `<span class="badge badge-info">${etapa.taxa_conversao}%</span>` : 
                    '<span class="text-muted">-</span>'
                }
            </td>
        `;
        
        tbody.appendChild(tr);
    });
}

/**
 * Ver detalhes de uma vaga (placeholder)
 */
function verDetalhesVaga(vagaId) {
    console.log('Ver detalhes da vaga:', vagaId);
    // TODO: Implementar navegação para página de detalhes da vaga
    window.location.href = `/rh/recrutamento/vagas/${vagaId}`;
}

/**
 * Renderizar gráfico de dispersão - Tempo de Casa vs Salário
 */
function renderizarGraficoDispersao(dados) {
    const ctx = document.getElementById('chart-dispersao-tempo-salario');
    if (!ctx) return;
    
    if (chartDispersaoTempoSalario) {
        chartDispersaoTempoSalario.destroy();
    }
    
    // Preparar dados para scatter plot
    const scatterData = dados.tempo_casa.map((tempo, index) => ({
        x: tempo,
        y: dados.salarios[index]
    }));
    
    chartDispersaoTempoSalario = new Chart(ctx, {
        type: 'scatter',
        data: {
            datasets: [{
                label: 'Colaboradores',
                data: scatterData,
                backgroundColor: 'rgba(111, 66, 193, 0.6)',
                borderColor: '#6f42c1',
                borderWidth: 1,
                pointRadius: 6,
                pointHoverRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                title: {
                    display: true,
                    text: 'Análise: Tempo de Casa vs Salário',
                    font: { size: 16, weight: 'bold' }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const index = context.dataIndex;
                            const nome = dados.labels[index];
                            const tempo = context.parsed.x;
                            const salario = context.parsed.y;
                            return [
                                nome,
                                `Tempo de Casa: ${tempo.toFixed(1)} anos`,
                                `Salário: ${salario.toLocaleString('pt-BR', {style: 'currency', currency: 'BRL'})}`
                            ];
                        }
                    }
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Tempo de Casa (anos)'
                    },
                    beginAtZero: true
                },
                y: {
                    title: {
                        display: true,
                        text: 'Salário (R$)'
                    },
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return value.toLocaleString('pt-BR', {style: 'currency', currency: 'BRL'});
                        }
                    }
                }
            }
        }
    });
}

// ========================================
// EXPORTAÇÃO (FUTURO)
// ========================================

/**
 * Exportar dashboard para PDF
 */
function exportarPDF() {
    console.log('📄 Exportando dashboard para PDF...');
    alert('⚠️ Funcionalidade de exportação será implementada em breve');
}

/**
 * Exportar dados para Excel
 */
function exportarExcel() {
    console.log('📊 Exportando dados para Excel...');
    alert('⚠️ Funcionalidade de exportação será implementada em breve');
}

console.log('✅ Dashboard Executivo RH - Scripts carregados (v3.0 - Completo)');
