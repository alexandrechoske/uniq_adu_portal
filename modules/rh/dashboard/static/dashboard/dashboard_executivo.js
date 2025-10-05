/**
 * Dashboard Executivo RH - JavaScript
 * Baseado no Dashboard Executivo Financeiro
 * Versão: 2.0
 */

// ========================================
// INICIALIZAÇÃO
// ========================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('📊 Dashboard Executivo RH - Inicializado');
    
    // Inicializar componentes
    inicializarFiltros();
    configurarEventosFiltros();
    
    // Carregar dados iniciais (será implementado conforme solicitação)
    // carregarDadosDashboard();
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
        });
    }
    
    // Mostrar botão "Limpar Filtros" quando filtros mudarem
    const filters = document.querySelectorAll('.filter-group select, .filter-group input');
    filters.forEach(filter => {
        filter.addEventListener('change', function() {
            if (resetFiltersBtn) resetFiltersBtn.style.display = 'inline-flex';
        });
    });
}

/**
 * Aplicar filtros selecionados
 */
function aplicarFiltros() {
    const periodo = document.getElementById('periodo-filter').value;
    const empresa = document.getElementById('empresa-filter').value;
    const departamento = document.getElementById('departamento-filter').value;
    
    console.log('🔄 Aplicando filtros:', {
        periodo: periodo,
        empresa: empresa,
        departamento: departamento
    });
    
    // Mostrar loading
    mostrarLoading();
    
    // TODO: Recarregar dados com novos filtros
    // Será implementado conforme solicitação do usuário
    
    // Simular carregamento
    setTimeout(() => {
        esconderLoading();
        atualizarResumoFiltros();
        console.log('✅ Filtros aplicados com sucesso');
    }, 500);
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
    
    mostrarLoading();
    
    try {
        // TODO: Buscar dados atualizados da API
        // const response = await fetch('/rh/dashboard/api/refresh', {
        //     method: 'POST',
        //     credentials: 'same-origin'
        // });
        
        // Simular atualização
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        console.log('✅ Dashboard atualizado com sucesso');
        
        // TODO: Atualizar KPIs, gráficos e tabelas
        // Será implementado conforme solicitação do usuário
        
    } catch (error) {
        console.error('❌ Erro ao atualizar dashboard:', error);
        alert('❌ Erro ao atualizar dashboard. Tente novamente.');
    } finally {
        esconderLoading();
    }
}

/**
 * Carregar dados do dashboard
 */
async function carregarDadosDashboard() {
    console.log('📥 Carregando dados do dashboard...');
    
    mostrarLoading();
    
    try {
        const periodo = document.getElementById('periodo-filter').value;
        const empresa = document.getElementById('empresa-filter').value;
        const departamento = document.getElementById('departamento-filter').value;
        
        // TODO: Buscar dados da API
        // const response = await fetch(`/rh/dashboard/api/dados?periodo=${periodo}&empresa=${empresa}&departamento=${departamento}`, {
        //     credentials: 'same-origin'
        // });
        
        // Simular carregamento
        await new Promise(resolve => setTimeout(resolve, 800));
        
        console.log('✅ Dados carregados com sucesso');
        
        // TODO: Renderizar KPIs, gráficos e tabelas
        // Funções serão implementadas conforme solicitação do usuário
        
    } catch (error) {
        console.error('❌ Erro ao carregar dados:', error);
        alert('❌ Erro ao carregar dados do dashboard. Tente novamente.');
    } finally {
        esconderLoading();
    }
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
 * Será implementado conforme solicitação do usuário
 */
function renderizarKPIs(dados) {
    console.log('📊 Renderizando KPIs...', dados);
    // TODO: Implementar renderização de KPIs
}

/**
 * Renderizar gráficos
 * Será implementado conforme solicitação do usuário
 */
function renderizarGraficos(dados) {
    console.log('📈 Renderizando gráficos...', dados);
    // TODO: Implementar renderização de gráficos
}

/**
 * Renderizar tabelas
 * Será implementado conforme solicitação do usuário
 */
function renderizarTabelas(dados) {
    console.log('📋 Renderizando tabelas...', dados);
    // TODO: Implementar renderização de tabelas
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

console.log('✅ Dashboard Executivo RH - Scripts carregados (v2.0)');
