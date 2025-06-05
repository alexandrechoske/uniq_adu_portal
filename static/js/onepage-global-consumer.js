// OnePage Global Data Consumer
// Consome dados do sistema global de refresh ao invés de fazer requisições próprias

(function() {
    'use strict';
    
    // Verificar se GlobalRefresh está disponível
    if (!window.GlobalRefresh) {
        console.error('[OnePage] GlobalRefresh não está disponível');
        return;
    }

    console.log('[OnePage] Inicializando consumer de dados globais...');

    // Função para atualizar os cards de KPI
    function updateKPICards(kpis) {
        if (!kpis) return;
        
        const kpiElements = {
            total: document.querySelector('[data-kpi="total"]'),
            aereo: document.querySelector('[data-kpi="aereo"]'),
            terrestre: document.querySelector('[data-kpi="terrestre"]'),
            maritimo: document.querySelector('[data-kpi="maritimo"]'),
            aguardando_chegada: document.querySelector('[data-kpi="aguardando_chegada"]'),
            aguardando_embarque: document.querySelector('[data-kpi="aguardando_embarque"]'),
            di_registrada: document.querySelector('[data-kpi="di_registrada"]')
        };

        Object.keys(kpiElements).forEach(key => {
            const element = kpiElements[key];
            if (element && kpis.hasOwnProperty(key)) {
                element.textContent = kpis[key];
            }
        });
    }

    // Função para atualizar a tabela
    function updateTable(tableData) {
        const tableBody = document.querySelector('.data-table tbody');
        if (!tableBody || !Array.isArray(tableData)) return;

        if (tableData.length === 0) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="100%" class="text-center py-8 text-gray-500">
                        <div class="empty-state">
                            <p class="text-lg font-medium">Nenhum processo encontrado</p>
                            <p class="text-sm">Não há processos correspondentes aos filtros selecionados.</p>
                        </div>
                    </td>
                </tr>
            `;
            return;
        }

        // Filtrar dados baseado na empresa selecionada
        const currentUrl = new URL(window.location);
        const selectedCompany = currentUrl.searchParams.get('empresa');
        
        let filteredData = tableData;
        if (selectedCompany) {
            filteredData = tableData.filter(row => row.cliente_cpfcnpj === selectedCompany);
        }

        // Reconstruct table rows
        tableBody.innerHTML = filteredData.map(row => {
            return `
                <tr>
                    <td>${row.processo || ''}</td>
                    <td>${row.cliente_razaosocial || ''}</td>
                    <td>${row.data_embarque || ''}</td>
                    <td>${row.data_chegada || ''}</td>
                    <td>${row.via_transporte_descricao || ''}</td>
                    <td>${row.carga_status || ''}</td>
                    <td>${row.status_doc || ''}</td>
                    <td>
                        <span class="canal-badge ${getCanalClass(row.canal_parametrizado)}">
                            ${row.canal_parametrizado || ''}
                        </span>
                    </td>
                </tr>
            `;
        }).join('');
    }

    // Função para determinar a classe CSS do canal
    function getCanalClass(canal) {
        if (!canal) return '';
        
        switch (canal.toLowerCase()) {
            case 'verde':
                return 'canal-verde';
            case 'amarelo':
                return 'canal-amarelo';
            case 'vermelho':
                return 'canal-vermelho';
            default:
                return '';
        }
    }

    // Função para atualizar a moeda
    function updateCurrencyDisplay(currencies) {
        if (!currencies) return;
        
        const usdElement = document.querySelector('[data-currency="USD"]');
        const eurElement = document.querySelector('[data-currency="EUR"]');
        
        if (usdElement && currencies.USD) {
            usdElement.textContent = `R$ ${currencies.USD.toFixed(4)}`;
        }
        
        if (eurElement && currencies.EUR) {
            eurElement.textContent = `R$ ${currencies.EUR.toFixed(4)}`;
        }
    }

    // Função para atualizar os dados da página com dados do cache global
    function updatePageWithGlobalData() {
        const globalData = window.GlobalRefresh.getData();
        
        if (!globalData) {
            console.warn('[OnePage] Dados globais não disponíveis');
            return;
        }

        console.log('[OnePage] Atualizando página com dados globais...');

        // Atualizar KPIs
        if (globalData.dashboard_stats) {
            // Mapear nomes dos campos para compatibilidade
            const kpis = {
                total: globalData.dashboard_stats.total_processos || 0,
                aereo: globalData.dashboard_stats.aereo || 0,
                terrestre: globalData.dashboard_stats.terrestre || 0,
                maritimo: globalData.dashboard_stats.maritimo || 0,
                aguardando_chegada: globalData.dashboard_stats.aguardando_chegada || 0,
                aguardando_embarque: globalData.dashboard_stats.aguardando_embarque || 0,
                di_registrada: globalData.dashboard_stats.di_registrada || 0
            };
            updateKPICards(kpis);
        }

        // Atualizar tabela
        if (globalData.importacoes) {
            updateTable(globalData.importacoes);
        }

        // Atualizar câmbio
        if (globalData.currencies) {
            updateCurrencyDisplay(globalData.currencies);
        }

        console.log('[OnePage] Página atualizada com sucesso');
    }

    // Callback para quando os dados globais são atualizados
    function onGlobalDataUpdate(event) {
        console.log('[OnePage] Dados globais atualizados, atualizando página...');
        updatePageWithGlobalData();
    }

    // Função para filtrar por empresa
    function filterByCompany(value) {
        const url = new URL(window.location);
        if (value && value !== '') {
            url.searchParams.set('empresa', value);
        } else {
            url.searchParams.delete('empresa');
        }
        window.location.href = url.toString();
    }

    // Event listeners e inicialização
    document.addEventListener('DOMContentLoaded', function() {
        console.log('[OnePage] Inicializando consumer de dados globais...');
        
        // Registrar callback para atualizações de dados globais
        window.GlobalRefresh.onDataUpdate(onGlobalDataUpdate);
        
        // Atualizar página com dados iniciais (se disponíveis)
        updatePageWithGlobalData();
        
        // Event listener para mudança de filtro de empresa
        const companySelect = document.getElementById('company-select');
        if (companySelect) {
            companySelect.addEventListener('change', function() {
                console.log('[OnePage] Filtro de empresa alterado');
                const selectedCompany = this.value;
                filterByCompany(selectedCompany);
            });
        }
        
        console.log('[OnePage] Consumer inicializado com sucesso');
    });

    // Expor funções globalmente para compatibilidade
    window.filterByCompany = filterByCompany;
    window.updateOnePage = updatePageWithGlobalData;

    console.log('[OnePage] Consumer de dados globais configurado');

})();
