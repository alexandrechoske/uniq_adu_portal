// Materiais Simple JavaScript
// Baseado no dashboard-simple.js mas adaptado para materiais

class MateriaisManager {
    constructor() {
        this.apiBaseUrl = '/materiais';
        this.lastUpdate = null;
        this.refreshInterval = null;
        this.currentFilters = {};
        this.init();
    }

    init() {
        console.log('🔧 Inicializando MateriaisManager...');
        this.setupEventListeners();
        this.setupDefaultDates();
        this.loadFilterOptions(); // Carregar opções dos filtros
        this.loadData();
        this.startAutoRefresh();
    }

    setupEventListeners() {
        // Botão de refresh manual
        const refreshBtn = document.getElementById('refresh-data');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                console.log('🔄 Refresh manual solicitado');
                this.loadData(true);
            });
        }

        // Botão de carregar do cache
        const cacheBtn = document.getElementById('load-from-cache');
        if (cacheBtn) {
            cacheBtn.addEventListener('click', () => {
                console.log('💾 Carregando dados do cache');
                this.loadData(false);
            });
        }

        // Filtros
        const applyFiltersBtn = document.getElementById('apply-filters');
        if (applyFiltersBtn) {
            applyFiltersBtn.addEventListener('click', () => {
                console.log('🔍 Aplicando filtros');
                this.applyFilters();
            });
        }

        const clearFiltersBtn = document.getElementById('clear-filters');
        if (clearFiltersBtn) {
            clearFiltersBtn.addEventListener('click', () => {
                console.log('🧹 Limpando filtros');
                this.clearFilters();
            });
        }

        // Filtros rápidos
        const quickFilterBtns = document.querySelectorAll('.btn-quick');
        quickFilterBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                this.applyQuickFilter(btn.dataset.period);
            });
        });

        // Enter key nos campos de data
        const dateInputs = document.querySelectorAll('#data-inicio, #data-fim');
        dateInputs.forEach(input => {
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.applyFilters();
                }
            });
        });

        // Listener para limpar filtros ativos
        const clearActiveFiltersBtn = document.getElementById('clear-active-filters');
        if (clearActiveFiltersBtn) {
            clearActiveFiltersBtn.addEventListener('click', () => {
                this.clearFilters();
            });
        }

        // Listener para visibilidade da página
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden) {
                console.log('👁️ Página ficou visível, atualizando dados');
                this.loadData();
            }
        });
    }

    setupDefaultDates() {
        // Configurar datas padrão (ano atual)
        const hoje = new Date();
        const inicioAno = new Date(hoje.getFullYear(), 0, 1); // 1º de janeiro do ano atual
        const fimAno = new Date(hoje.getFullYear(), 11, 31); // 31 de dezembro do ano atual

        const dataInicio = document.getElementById('data-inicio');
        const dataFim = document.getElementById('data-fim');

        if (dataInicio) {
            dataInicio.value = inicioAno.toISOString().split('T')[0];
        }
        if (dataFim) {
            dataFim.value = fimAno.toISOString().split('T')[0];
        }

        console.log('📅 Datas padrão configuradas:', {
            inicio: inicioAno.toISOString().split('T')[0],
            fim: fimAno.toISOString().split('T')[0]
        });

        // Marcar o filtro "Ano Atual" como ativo
        this.setActiveQuickFilter('current-year');
    }

    applyQuickFilter(period) {
        const hoje = new Date();
        let dataInicio, dataFim;

        switch (period) {
            case 'current-year':
                dataInicio = new Date(hoje.getFullYear(), 0, 1);
                dataFim = new Date(hoje.getFullYear(), 11, 31);
                break;
            case 'this-week':
                const inicioSemana = new Date(hoje);
                inicioSemana.setDate(hoje.getDate() - hoje.getDay());
                dataInicio = inicioSemana;
                dataFim = new Date(hoje);
                break;
            case 'this-month':
                dataInicio = new Date(hoje.getFullYear(), hoje.getMonth(), 1);
                dataFim = new Date(hoje.getFullYear(), hoje.getMonth() + 1, 0);
                break;
            case '3-months':
                dataInicio = new Date(hoje);
                dataInicio.setMonth(hoje.getMonth() - 3);
                dataFim = new Date(hoje);
                break;
            case '6-months':
                dataInicio = new Date(hoje);
                dataInicio.setMonth(hoje.getMonth() - 6);
                dataFim = new Date(hoje);
                break;
            default:
                return;
        }

        // Atualizar campos de data
        const dataInicioInput = document.getElementById('data-inicio');
        const dataFimInput = document.getElementById('data-fim');

        if (dataInicioInput) {
            dataInicioInput.value = dataInicio.toISOString().split('T')[0];
        }
        if (dataFimInput) {
            dataFimInput.value = dataFim.toISOString().split('T')[0];
        }

        // Marcar botão como ativo
        this.setActiveQuickFilter(period);

        // Aplicar filtros automaticamente
        this.applyFilters();
    }

    setActiveQuickFilter(period) {
        // Remover classe active de todos os botões
        document.querySelectorAll('.btn-quick').forEach(btn => {
            btn.classList.remove('active');
        });

        // Adicionar classe active ao botão selecionado
        const activeBtn = document.querySelector(`[data-period="${period}"]`);
        if (activeBtn) {
            activeBtn.classList.add('active');
        }
    }

    applyFilters() {
        const dataInicio = document.getElementById('data-inicio').value;
        const dataFim = document.getElementById('data-fim').value;
        const material = document.getElementById('material-filter').value;
        const cliente = document.getElementById('cliente-filter').value;
        const modal = document.getElementById('modal-filter').value;

        // Validações
        if (dataInicio && dataFim && new Date(dataInicio) > new Date(dataFim)) {
            this.showError('Data de início não pode ser maior que data de fim');
            return;
        }

        // Atualizar filtros atuais
        this.currentFilters = {};
        if (dataInicio) this.currentFilters.data_inicio = dataInicio;
        if (dataFim) this.currentFilters.data_fim = dataFim;
        if (material) this.currentFilters.material = material;
        if (cliente) this.currentFilters.cliente = cliente;
        if (modal) this.currentFilters.modal = modal;

        // Atualizar status dos filtros
        this.updateFilterStatus();

        // Carregar dados com filtros
        this.loadData(true);

        console.log('🔍 Filtros aplicados:', this.currentFilters);
    }

    clearFilters() {
        // Limpar campos
        document.getElementById('data-inicio').value = '';
        document.getElementById('data-fim').value = '';
        document.getElementById('material-filter').value = '';
        document.getElementById('cliente-filter').value = '';
        document.getElementById('modal-filter').value = '';

        // Remover seleção dos filtros rápidos
        document.querySelectorAll('.btn-quick').forEach(btn => {
            btn.classList.remove('active');
        });

        // Limpar filtros internos
        this.currentFilters = {};

        // Configurar datas padrão novamente
        this.setupDefaultDates();

        // Atualizar status
        this.updateFilterStatus();

        // Recarregar dados
        this.loadData(true);

        console.log('🧹 Filtros limpos');
    }

    updateFilterStatus() {
        const statusElement = document.getElementById('filter-status');
        const filtersCard = document.querySelector('.filters-card');

        if (Object.keys(this.currentFilters).length > 0) {
            let statusText = 'Filtros ativos: ';
            const filtros = [];

            if (this.currentFilters.data_inicio) {
                filtros.push(`Início: ${this.formatDate(this.currentFilters.data_inicio)}`);
            }
            if (this.currentFilters.data_fim) {
                filtros.push(`Fim: ${this.formatDate(this.currentFilters.data_fim)}`);
            }

            statusText += filtros.join(', ');
            statusElement.textContent = statusText;
            filtersCard.classList.add('active');
            
            // Atualizar resumo completo dos filtros
            this.updateActiveFiltersSummary();
        } else {
            statusElement.textContent = '';
            filtersCard.classList.remove('active');
            this.hideActiveFiltersSummary();
        }
    }

    updateActiveFiltersSummary() {
        const summaryElement = document.getElementById('active-filters-summary');
        const contentElement = document.getElementById('active-filters-content');
        
        if (Object.keys(this.currentFilters).length === 0) {
            this.hideActiveFiltersSummary();
            return;
        }

        const filtros = [];

        // Filtros temporais
        if (this.currentFilters.data_inicio) {
            filtros.push(`<strong>Início:</strong> ${this.formatDate(this.currentFilters.data_inicio)}`);
        }
        if (this.currentFilters.data_fim) {
            filtros.push(`<strong>Fim:</strong> ${this.formatDate(this.currentFilters.data_fim)}`);
        }

        // Filtros de busca
        if (this.currentFilters.material) {
            filtros.push(`<strong>Material:</strong> ${this.currentFilters.material}`);
        }
        if (this.currentFilters.cliente) {
            filtros.push(`<strong>Cliente:</strong> ${this.currentFilters.cliente}`);
        }
        if (this.currentFilters.modal) {
            filtros.push(`<strong>Modal:</strong> ${this.currentFilters.modal}`);
        }

        if (filtros.length > 0) {
            contentElement.innerHTML = filtros.join(' • ');
            summaryElement.style.display = 'block';
        } else {
            this.hideActiveFiltersSummary();
        }
    }

    hideActiveFiltersSummary() {
        const summaryElement = document.getElementById('active-filters-summary');
        if (summaryElement) {
            summaryElement.style.display = 'none';
        }
    }

    async loadData(forceRefresh = false) {
        console.log(`📊 Carregando dados de materiais... ${forceRefresh ? '(força refresh)' : ''}`);
        
        try {
            this.setLoadingState();
            
            // Construir URL com filtros
            let url = `${this.apiBaseUrl}/materiais_data`;
            const params = new URLSearchParams();
            
            if (forceRefresh) {
                params.append('refresh', 'true');
            }
            
            // Adicionar filtros à URL
            Object.keys(this.currentFilters).forEach(key => {
                params.append(key, this.currentFilters[key]);
            });
            
            if (params.toString()) {
                url += `?${params.toString()}`;
            }
            
            console.log('🌐 URL da requisição:', url);
            
            const response = await fetch(url);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            console.log('✅ Dados de materiais carregados:', data);
            
            this.updateKPIs(data);
            this.updateLastUpdate();
            this.setSuccessState();
            
        } catch (error) {
            console.error('❌ Erro ao carregar dados de materiais:', error);
            this.setErrorState();
            this.showError('Erro ao carregar dados de materiais');
        }
    }

    updateKPIs(data) {
        if (!data) {
            console.warn('⚠️ Dados de materiais não fornecidos');
            return;
        }

        // Atualizar KPIs individuais
        this.updateKPI('kpi-processos', this.formatNumber(data.total_processos), 'success');
        this.updateKPI('kpi-materiais', this.formatNumber(data.total_materiais), 'success');
        this.updateKPI('kpi-valor', this.formatCurrency(data.valor_total), 'success');
        this.updateKPI('kpi-custo', this.formatCurrency(data.custo_total), 'success');
        this.updateKPI('kpi-ticket', this.formatCurrency(data.ticket_medio), 'success');
        this.updateKPI('kpi-transit', this.formatDays(data.transit_time_medio), 'success');

        console.log('📈 KPIs de materiais atualizados');
    }

    async loadFilterOptions() {
        try {
            console.log('🔧 Carregando opções dos filtros...');
            
            // Carregar materiais únicos
            const materiaisResponse = await fetch(`${this.apiBaseUrl}/filter-options/materiais`);
            if (materiaisResponse.ok) {
                const materiais = await materiaisResponse.json();
                this.populateSelect('material-filter', materiais, 'mercadoria');
            }

            // Carregar clientes únicos
            const clientesResponse = await fetch(`${this.apiBaseUrl}/filter-options/clientes`);
            if (clientesResponse.ok) {
                const clientes = await clientesResponse.json();
                this.populateSelect('cliente-filter', clientes, 'importador');
            }

            console.log('✅ Opções dos filtros carregadas');
        } catch (error) {
            console.warn('⚠️ Erro ao carregar opções dos filtros:', error);
            // Não é um erro crítico, apenas log de warning
        }
    }

    populateSelect(selectId, options, valueField) {
        const select = document.getElementById(selectId);
        if (!select || !options) return;

        // Limpar opções existentes (exceto a primeira que é "Todos")
        const firstOption = select.firstElementChild;
        select.innerHTML = '';
        if (firstOption) {
            select.appendChild(firstOption);
        }

        // Adicionar novas opções (limitando a 50 para performance)
        const limitedOptions = options.slice(0, 50);
        limitedOptions.forEach(option => {
            const optionElement = document.createElement('option');
            optionElement.value = option[valueField];
            optionElement.textContent = option[valueField];
            select.appendChild(optionElement);
        });

        console.log(`📝 ${limitedOptions.length} opções adicionadas ao select ${selectId}`);
    }

    updateKPI(elementId, value, state = 'success') {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = value;
            
            // Atualizar estado visual do card pai
            const card = element.closest('.kpi-card');
            if (card) {
                // Remover estados anteriores
                card.classList.remove('loading', 'error', 'success');
                // Adicionar novo estado
                card.classList.add(state);
            }
        }
    }

    setLoadingState() {
        const kpiCards = document.querySelectorAll('.kpi-card');
        kpiCards.forEach(card => {
            card.classList.remove('error', 'success');
            card.classList.add('loading');
        });

        // Atualizar valores para loading
        const kpiValues = document.querySelectorAll('.kpi-value');
        kpiValues.forEach(value => {
            value.textContent = '...';
        });

        console.log('⏳ Estado de carregamento ativado');
    }

    setSuccessState() {
        const kpiCards = document.querySelectorAll('.kpi-card');
        kpiCards.forEach(card => {
            card.classList.remove('loading', 'error');
            card.classList.add('success');
        });
        console.log('✅ Estado de sucesso ativado');
    }

    setErrorState() {
        const kpiCards = document.querySelectorAll('.kpi-card');
        kpiCards.forEach(card => {
            card.classList.remove('loading', 'success');
            card.classList.add('error');
        });

        // Atualizar valores para erro
        const kpiValues = document.querySelectorAll('.kpi-value');
        kpiValues.forEach(value => {
            value.textContent = 'Erro';
        });

        console.log('❌ Estado de erro ativado');
    }

    updateLastUpdate() {
        const now = new Date();
        this.lastUpdate = now;
        
        const lastUpdateElement = document.getElementById('last-update');
        if (lastUpdateElement) {
            lastUpdateElement.textContent = `Última atualização: ${this.formatDateTime(now)}`;
        }
    }

    startAutoRefresh() {
        // Refresh automático a cada 5 minutos
        this.refreshInterval = setInterval(() => {
            console.log('⏰ Auto-refresh executado');
            this.loadData();
        }, 5 * 60 * 1000);
        
        console.log('🔄 Auto-refresh configurado para 5 minutos');
    }

    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
            console.log('⏹️ Auto-refresh parado');
        }
    }

    // Formatação de dados
    formatNumber(num) {
        if (num === null || num === undefined || isNaN(num)) return '0';
        return new Intl.NumberFormat('pt-BR').format(num);
    }

    formatCurrency(num) {
        if (num === null || num === undefined || isNaN(num)) return 'R$ 0,00';
        return new Intl.NumberFormat('pt-BR', {
            style: 'currency',
            currency: 'BRL'
        }).format(num);
    }

    formatDays(num) {
        if (num === null || num === undefined || isNaN(num)) return '0 dias';
        const days = Math.round(num);
        return `${days} dia${days !== 1 ? 's' : ''}`;
    }

    formatDate(dateString) {
        const date = new Date(dateString);
        return new Intl.DateTimeFormat('pt-BR').format(date);
    }

    formatDateTime(date) {
        return new Intl.DateTimeFormat('pt-BR', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        }).format(date);
    }

    showError(message) {
        // Simple error display - can be enhanced with toast notifications
        console.error('💥 Erro exibido:', message);
        
        // Opcional: mostrar um alert temporário
        const alertDiv = document.createElement('div');
        alertDiv.className = 'alert alert-danger';
        alertDiv.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 9999; max-width: 300px;';
        alertDiv.innerHTML = `
            <strong>Erro:</strong> ${message}
            <button type="button" class="close" style="margin-left: 10px;" onclick="this.parentElement.remove()">×</button>
        `;
        
        document.body.appendChild(alertDiv);
        
        // Auto-remover após 5 segundos
        setTimeout(() => {
            if (alertDiv.parentElement) {
                alertDiv.remove();
            }
        }, 5000);
    }

    // Método para cleanup
    destroy() {
        this.stopAutoRefresh();
        console.log('🧹 MateriaisManager destruído');
    }
}

// Inicialização quando DOM estiver pronto
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 DOM carregado, inicializando materiais...');
    
    // Verificar se estamos na página de materiais
    if (window.location.pathname.includes('/materiais')) {
        window.materiaisManager = new MateriaisManager();
        console.log('✅ MateriaisManager inicializado e anexado ao window');
    }
});

// Cleanup quando a página for descarregada
window.addEventListener('beforeunload', function() {
    if (window.materiaisManager) {
        window.materiaisManager.destroy();
    }
});

// Expor algumas funções úteis globalmente
window.MaterialsUtils = {
    refresh: () => {
        if (window.materiaisManager) {
            window.materiaisManager.loadData(true);
        }
    },
    
    getLastUpdate: () => {
        if (window.materiaisManager) {
            return window.materiaisManager.lastUpdate;
        }
        return null;
    }
};
