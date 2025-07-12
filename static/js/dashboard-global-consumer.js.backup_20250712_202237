// Dashboard Global Data Consumer
// Consome dados do sistema global de refresh ao invés de fazer requisições próprias

(function() {
    'use strict';
    
    // Verificar se GlobalRefresh está disponível
    if (!window.GlobalRefresh) {
        console.error('[Dashboard] GlobalRefresh não está disponível');
        return;
    }

    console.log('[Dashboard] Inicializando consumer de dados globais...');

    // Função para atualizar estatísticas do dashboard
    function updateDashboardStats(stats) {
        if (!stats) return;
        
        // Atualizar cards de estatísticas
        const statElements = {
            'total-processos': stats.total_processos || 0,
            'processos-aereo': stats.aereo || 0,
            'processos-terrestre': stats.terrestre || 0,
            'processos-maritimo': stats.maritimo || 0,
            'aguardando-chegada': stats.aguardando_chegada || 0,
            'aguardando-embarque': stats.aguardando_embarque || 0,
            'di-registrada': stats.di_registrada || 0
        };

        Object.keys(statElements).forEach(key => {
            const element = document.querySelector(`[data-stat="${key}"]`);
            if (element) {
                element.textContent = statElements[key];
            }
        });
    }

    // Função para atualizar gráficos (se existirem)
    function updateCharts(importacoes) {
        if (!importacoes || !Array.isArray(importacoes)) return;
        
        console.log('[Dashboard] Atualizando gráficos com dados globais...');
        
        // Exemplo de atualização de gráfico por via de transporte
        const viaTransporte = {};
        importacoes.forEach(item => {
            const via = item.via_transporte_descricao || 'Não informado';
            viaTransporte[via] = (viaTransporte[via] || 0) + 1;
        });

        // Se existir um elemento para gráfico, atualizar
        const chartElement = document.getElementById('transport-chart');
        if (chartElement && window.Plotly) {
            const data = [{
                values: Object.values(viaTransporte),
                labels: Object.keys(viaTransporte),
                type: 'pie',
                marker: {
                    colors: ['#1F406F', '#3498DB', '#52C41A', '#FAAD14']
                }
            }];

            const layout = {
                title: 'Distribuição por Via de Transporte',
                font: { family: 'Inter, sans-serif' },
                margin: { t: 50, b: 50, l: 50, r: 50 }
            };

            Plotly.newPlot(chartElement, data, layout, {responsive: true});
        }
    }

    // Função para atualizar tabela recente de importações
    function updateRecentImportations(importacoes) {
        if (!importacoes || !Array.isArray(importacoes)) return;
        
        const tableBody = document.querySelector('#recent-importations tbody');
        if (!tableBody) return;

        // Pegar os 10 mais recentes
        const recent = importacoes.slice(0, 10);
        
        if (recent.length === 0) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="100%" class="text-center py-4 text-gray-500">
                        Nenhuma importação encontrada
                    </td>
                </tr>
            `;
            return;
        }

        tableBody.innerHTML = recent.map(item => `
            <tr class="hover:bg-gray-50">
                <td class="px-4 py-3 text-sm font-medium text-gray-900">${item.processo || ''}</td>
                <td class="px-4 py-3 text-sm text-gray-600">${item.cliente_razaosocial || ''}</td>
                <td class="px-4 py-3 text-sm text-gray-600">${item.data_embarque || ''}</td>
                <td class="px-4 py-3 text-sm text-gray-600">${item.via_transporte_descricao || ''}</td>
                <td class="px-4 py-3">
                    <span class="inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getStatusClass(item.carga_status)}">
                        ${item.carga_status || ''}
                    </span>
                </td>
            </tr>
        `).join('');
    }

    // Função para determinar classe CSS do status
    function getStatusClass(status) {
        if (!status) return 'bg-gray-100 text-gray-800';
        
        switch (status.toLowerCase()) {
            case '1 - aguardando embarque':
                return 'bg-yellow-100 text-yellow-800';
            case '2 - em trânsito':
                return 'bg-blue-100 text-blue-800';
            case '3 - desembarcada':
                return 'bg-green-100 text-green-800';
            default:
                return 'bg-gray-100 text-gray-800';
        }
    }

    // Função para atualizar os dados do dashboard com dados do cache global
    function updateDashboardWithGlobalData() {
        const globalData = window.GlobalRefresh.getData();
        
        if (!globalData) {
            console.warn('[Dashboard] Dados globais não disponíveis');
            return;
        }

        console.log('[Dashboard] Atualizando dashboard com dados globais...');

        // Atualizar estatísticas
        if (globalData.dashboard_stats) {
            updateDashboardStats(globalData.dashboard_stats);
        }

        // Atualizar gráficos
        if (globalData.importacoes) {
            updateCharts(globalData.importacoes);
            updateRecentImportations(globalData.importacoes);
        }

        console.log('[Dashboard] Dashboard atualizado com sucesso');
    }

    // Callback para quando os dados globais são atualizados
    function onGlobalDataUpdate(event) {
        console.log('[Dashboard] Dados globais atualizados, atualizando dashboard...');
        updateDashboardWithGlobalData();
    }

    // Event listeners e inicialização
    document.addEventListener('DOMContentLoaded', function() {
        console.log('[Dashboard] Inicializando consumer de dados globais...');
        
        // Registrar callback para atualizações de dados globais
        window.GlobalRefresh.onDataUpdate(onGlobalDataUpdate);
        
        // Atualizar dashboard com dados iniciais (se disponíveis)
        updateDashboardWithGlobalData();
        
        console.log('[Dashboard] Consumer inicializado com sucesso');
    });

    // Expor funções globalmente para compatibilidade
    window.updateDashboard = updateDashboardWithGlobalData;

    console.log('[Dashboard] Consumer de dados globais configurado');

})();
