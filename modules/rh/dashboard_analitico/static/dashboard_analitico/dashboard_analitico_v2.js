/**
 * Dashboard Analítico RH v2.0
 * Seções: Recrutamento & Seleção, Turnover & Retenção
 * @version 2.0.0 - Análises Detalhadas
 */

// ========================================
// CONFIGURAÇÃO GLOBAL
// ========================================
const DashboardAnalitico = {
    API_BASE_URL: '/rh/dashboard-analitico/api',
    charts: {},
    currentFilters: {},
    chartDataLabelsRegistered: false,
    multiSelectValues: {
        departamento: [],
        cargo: []
    },
    multiSelectContainers: [],
    outsideClickHandler: null,
    
    // Inicialização
    async init() {
        console.log('📊 Iniciando Dashboard Analítico RH v2.0...');
        await this.ensureChartPlugins();
        this.setupEventListeners();
        await this.loadFilterOptions();
        this.loadDashboardData();
    },
    
    // ========================================
    // EVENT LISTENERS
    // ========================================
    setupEventListeners() {
        // Botão de atualizar
        document.getElementById('btn-refresh')?.addEventListener('click', () => {
            this.loadDashboardData();
        });
        
        // Botão de aplicar filtros
        document.getElementById('btn-apply-filters')?.addEventListener('click', () => {
            this.applyFilters();
        });
        
        // Período personalizado
        document.getElementById('periodo-filter')?.addEventListener('change', (e) => {
            const customGroups = ['custom-date-group', 'custom-date-end-group'];
            customGroups.forEach(id => {
                const group = document.getElementById(id);
                if (group) {
                    group.style.display = e.target.value === 'personalizado' ? 'block' : 'none';
                }
            });
        });
        
    // Navegação por abas
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                if (btn.disabled) return;
                
                const section = btn.dataset.section;
                this.switchSection(section);
            });
        });
        
        // Busca em tabelas
        document.getElementById('search-vagas')?.addEventListener('input', (e) => {
            this.searchTable('table-vagas-abertas', e.target.value);
        });
        
        document.getElementById('search-desligamentos')?.addEventListener('input', (e) => {
            this.searchTable('table-desligamentos', e.target.value);
        });
        
        // Inicializar multi-selects customizados
        this.initializeMultiSelects();
    },

    async ensureChartPlugins() {
        if (this.chartDataLabelsRegistered) {
            return;
        }

        const registerPlugin = () => {
            if (!window.Chart || !window.ChartDataLabels) {
                return false;
            }

            try {
                Chart.register(ChartDataLabels);
                this.chartDataLabelsRegistered = true;
                console.log('✅ ChartDataLabels plugin registrado com sucesso.');
                return true;
            } catch (error) {
                console.error('❌ Falha ao registrar ChartDataLabels:', error);
                return false;
            }
        };

        if (registerPlugin()) {
            return;
        }

        let script = document.querySelector('script[data-chartjs-datalabels]');
        if (!script) {
            script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.2.0';
            script.async = true;
            script.defer = true;
            script.dataset.chartjsDatalabels = 'true';
            document.head.appendChild(script);
        }

        await new Promise((resolve) => {
            const timeoutMs = 6000;
            const intervalMs = 60;
            let elapsed = 0;

            const tryRegister = () => {
                if (registerPlugin()) {
                    resolve();
                    return;
                }

                elapsed += intervalMs;
                if (elapsed >= timeoutMs) {
                    console.warn('⚠️ ChartDataLabels não carregou dentro do tempo esperado. Gráficos serão renderizados sem rótulos.');
                    resolve();
                    return;
                }

                setTimeout(tryRegister, intervalMs);
            };

            script.addEventListener('load', () => {
                if (!registerPlugin()) {
                    tryRegister();
                } else {
                    resolve();
                }
            });

            script.addEventListener('error', () => {
                console.error('❌ Erro ao carregar script ChartDataLabels.');
                resolve();
            });

            tryRegister();
        });
    },
    
    // ========================================
    // FILTROS
    // ========================================
    async loadFilterOptions() {
        try {
            // Carregar departamentos
            const response = await fetch(`${this.API_BASE_URL}/filtros/departamentos`);
            const data = await response.json();
        
            if (data.success) {
                this.populateMultiSelect('departamento', data.departamentos || []);
            }
        
            // Carregar cargos
            const responseCargos = await fetch(`${this.API_BASE_URL}/filtros/cargos`);
            const dataCargos = await responseCargos.json();
        
            if (dataCargos.success) {
                this.populateMultiSelect('cargo', dataCargos.cargos || []);
            }
            
        } catch (error) {
            console.error('❌ Erro ao carregar opções de filtro:', error);
        }
    },

    initializeMultiSelects() {
        this.multiSelectContainers = Array.from(document.querySelectorAll('.multi-select-container'));
        if (!this.multiSelectContainers.length) {
            return;
        }

        if (this.outsideClickHandler) {
            document.removeEventListener('click', this.outsideClickHandler);
        }

        this.outsideClickHandler = (event) => {
            if (!event.target.closest('.multi-select-container')) {
                this.closeAllMultiSelects();
            }
        };

        document.addEventListener('click', this.outsideClickHandler);

        this.multiSelectContainers.forEach((container) => {
            const type = container.dataset.filter;
            const header = container.querySelector('.multi-select-header');
            const searchInput = container.querySelector('.multi-select-search input');
            const clearButton = container.querySelector('[data-action="clear"]');
            const closeButton = container.querySelector('[data-action="close"]');

            if (header) {
                header.addEventListener('click', (event) => {
                    event.stopPropagation();
                    this.toggleMultiSelect(type);
                });

                header.addEventListener('keydown', (event) => {
                    if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault();
                        this.toggleMultiSelect(type);
                    } else if (event.key === 'Escape') {
                        this.toggleMultiSelect(type, false);
                    }
                });
            }

            if (searchInput) {
                searchInput.addEventListener('input', (event) => {
                    this.filterMultiSelectOptions(type, event.target.value);
                });
            }

            if (clearButton) {
                clearButton.addEventListener('click', (event) => {
                    event.stopPropagation();
                    this.clearMultiSelect(type);
                });
            }

            if (closeButton) {
                closeButton.addEventListener('click', (event) => {
                    event.stopPropagation();
                    this.toggleMultiSelect(type, false);
                });
            }
        });
    },

    populateMultiSelect(type, items) {
        const container = document.querySelector(`.multi-select-container[data-filter="${type}"]`);
        if (!container) {
            return;
        }

        const optionsWrapper = container.querySelector('.multi-select-options');
        const emptyMessage = container.querySelector('.multi-select-empty');
        const searchInput = container.querySelector('.multi-select-search input');

        optionsWrapper.innerHTML = '';

        if (searchInput) {
            searchInput.value = '';
        }

        if (!items.length) {
            if (emptyMessage) {
                emptyMessage.style.display = 'block';
            }
            this.updateMultiSelectDisplay(type);
            return;
        }

        if (emptyMessage) {
            emptyMessage.style.display = 'none';
        }

        const selectedValues = this.currentFilters[type === 'departamento' ? 'departamentos' : 'cargos'] || this.multiSelectValues[type] || [];

        items.forEach((item) => {
            const optionLabel = document.createElement('label');
            optionLabel.className = 'multi-select-option';

            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.value = item.id;
            checkbox.dataset.label = item.nome_departamento || item.nome_cargo || item.nome || 'Sem nome';
            checkbox.checked = selectedValues.includes(String(item.id));

            checkbox.addEventListener('change', () => {
                this.updateMultiSelectDisplay(type);
            });

            const textSpan = document.createElement('span');
            textSpan.textContent = checkbox.dataset.label;

            optionLabel.appendChild(checkbox);
            optionLabel.appendChild(textSpan);

            optionsWrapper.appendChild(optionLabel);
        });

        this.updateMultiSelectDisplay(type);

        if (searchInput) {
            this.filterMultiSelectOptions(type, '');
        }
    },

    toggleMultiSelect(type, forceState = null) {
        const container = document.querySelector(`.multi-select-container[data-filter="${type}"]`);
        if (!container) {
            return;
        }

        const dropdown = container.querySelector('.multi-select-dropdown');
        const header = container.querySelector('.multi-select-header');
        if (!dropdown || !header) {
            return;
        }

        const isOpen = dropdown.classList.contains('open');
        const shouldOpen = forceState === null ? !isOpen : forceState;

        if (shouldOpen) {
            this.closeAllMultiSelects(type);
            dropdown.classList.add('open');
            dropdown.setAttribute('aria-hidden', 'false');
            header.setAttribute('aria-expanded', 'true');
            const searchInput = dropdown.querySelector('.multi-select-search input');
            if (searchInput) {
                requestAnimationFrame(() => searchInput.focus());
            }
        } else {
            dropdown.classList.remove('open');
            dropdown.setAttribute('aria-hidden', 'true');
            header.setAttribute('aria-expanded', 'false');
        }
    },

    closeAllMultiSelects(exceptType = null) {
        this.multiSelectContainers.forEach((container) => {
            if (exceptType && container.dataset.filter === exceptType) {
                return;
            }
            const dropdown = container.querySelector('.multi-select-dropdown');
            const header = container.querySelector('.multi-select-header');
            if (dropdown) {
                dropdown.classList.remove('open');
                dropdown.setAttribute('aria-hidden', 'true');
            }
            if (header) {
                header.setAttribute('aria-expanded', 'false');
            }
        });
    },

    clearMultiSelect(type) {
        const container = document.querySelector(`.multi-select-container[data-filter="${type}"]`);
        if (!container) {
            return;
        }

        const checkboxes = container.querySelectorAll('.multi-select-option input[type="checkbox"]');
        checkboxes.forEach((checkbox) => {
            checkbox.checked = false;
        });

        this.updateMultiSelectDisplay(type);

        const searchInput = container.querySelector('.multi-select-search input');
        if (searchInput) {
            searchInput.value = '';
        }
        this.filterMultiSelectOptions(type, '');
    },

    filterMultiSelectOptions(type, searchTerm) {
        const container = document.querySelector(`.multi-select-container[data-filter="${type}"]`);
        if (!container) {
            return;
        }

        const normalizedSearch = searchTerm.toLowerCase();
        const options = container.querySelectorAll('.multi-select-option');

        options.forEach((option) => {
            const labelText = option.textContent.toLowerCase();
            option.classList.toggle('hidden', normalizedSearch && !labelText.includes(normalizedSearch));
        });
    },

    updateMultiSelectDisplay(type) {
        const container = document.querySelector(`.multi-select-container[data-filter="${type}"]`);
        if (!container) {
            return [];
        }

        const placeholderSpan = container.querySelector('.multi-select-placeholder');
        const checkboxes = container.querySelectorAll('.multi-select-option input[type="checkbox"]');
        const selectedCheckboxes = Array.from(checkboxes).filter((checkbox) => checkbox.checked);
        const selectedValues = selectedCheckboxes.map((checkbox) => checkbox.value);
        const selectedLabels = selectedCheckboxes.map((checkbox) => checkbox.dataset.label || checkbox.value);

        this.multiSelectValues[type] = selectedValues;

        if (placeholderSpan) {
            if (!selectedLabels.length) {
                placeholderSpan.textContent = container.dataset.placeholder || 'Todos';
            } else if (selectedLabels.length <= 2) {
                placeholderSpan.textContent = selectedLabels.join(', ');
            } else {
                placeholderSpan.innerHTML = `<span class="badge badge-primary">${selectedLabels.length} selecionados</span>`;
            }
        }

        return selectedValues;
    },

    getMultiSelectValues(type) {
        return this.multiSelectValues[type] || [];
    },
    
    getFilters() {
        const filters = {};
        
        // Período
        const periodo = document.getElementById('periodo-filter').value;
        if (periodo === 'personalizado') {
            filters.periodo_inicio = document.getElementById('data-inicio').value;
            filters.periodo_fim = document.getElementById('data-fim').value;
        } else {
            const dates = this.getPeriodDates(periodo);
            filters.periodo_inicio = dates.inicio;
            filters.periodo_fim = dates.fim;
        }
        
        // Departamentos (multi-select)
        const selectedDepts = this.getMultiSelectValues('departamento');
        if (selectedDepts.length > 0) {
            filters.departamentos = selectedDepts;
        }
        
        // Cargos (multi-select)
        const selectedCargos = this.getMultiSelectValues('cargo');
        if (selectedCargos.length > 0) {
            filters.cargos = selectedCargos;
        }
        
        // Status
        const status = document.getElementById('status-filter').value;
        if (status !== 'todos') {
            filters.status = status;
        }
        
        return filters;
    },
    
    getPeriodDates(periodo) {
        const hoje = new Date();
        let inicio, fim;
        
        switch (periodo) {
            case 'este_ano':
                inicio = `${hoje.getFullYear()}-01-01`;
                fim = hoje.toISOString().split('T')[0];
                break;
            case 'este_mes':
                inicio = `${hoje.getFullYear()}-${String(hoje.getMonth() + 1).padStart(2, '0')}-01`;
                fim = hoje.toISOString().split('T')[0];
                break;
            case 'ultimos_12_meses':
                const umAnoAtras = new Date(hoje);
                umAnoAtras.setMonth(hoje.getMonth() - 12);
                inicio = umAnoAtras.toISOString().split('T')[0];
                fim = hoje.toISOString().split('T')[0];
                break;
            case 'trimestre_atual':
                const mes = hoje.getMonth();
                const trimestreInicio = Math.floor(mes / 3) * 3;
                inicio = `${hoje.getFullYear()}-${String(trimestreInicio + 1).padStart(2, '0')}-01`;
                fim = hoje.toISOString().split('T')[0];
                break;
            case 'ano_anterior':
                const anoAnterior = hoje.getFullYear() - 1;
                inicio = `${anoAnterior}-01-01`;
                fim = `${anoAnterior}-12-31`;
                break;
            default:
                inicio = `${hoje.getFullYear()}-01-01`;
                fim = hoje.toISOString().split('T')[0];
        }
        
        return { inicio, fim };
    },
    
    applyFilters() {
        this.currentFilters = this.getFilters();
        this.loadDashboardData();
    },
    
    // ========================================
    // CARREGAMENTO DE DADOS
    // ========================================
    async loadDashboardData() {
        this.showLoading(true);
        
        try {
            const filters = this.getFilters();
            const queryString = new URLSearchParams();
            
            queryString.append('periodo_inicio', filters.periodo_inicio);
            queryString.append('periodo_fim', filters.periodo_fim);
            
            if (filters.departamentos) {
                filters.departamentos.forEach(d => queryString.append('departamentos[]', d));
            }
            
            if (filters.cargos) {
                filters.cargos.forEach(c => queryString.append('cargos[]', c));
            }
            
            if (filters.status) {
                queryString.append('status', filters.status);
            }
            
            const response = await fetch(`${this.API_BASE_URL}/dados?${queryString}`);
            const data = await response.json();
            
            if (data.success) {
                this.renderDashboard(data.data);
            } else {
                this.showError('Erro ao carregar dados do dashboard');
            }
            
        } catch (error) {
            console.error('❌ Erro ao carregar dashboard:', error);
            this.showError('Erro ao carregar dados do dashboard');
        } finally {
            this.showLoading(false);
        }
    },
    
    // ========================================
    // RENDERIZAÇÃO
    // ========================================
    renderDashboard(data) {
        console.log('✅ Dados recebidos:', data);
        
        // Renderizar Seção 1: Recrutamento
        this.renderSecaoRecrutamento(data.recrutamento);
        
        // Renderizar Seção 2: Turnover
        this.renderSecaoTurnover(data.turnover);
    },
    
    // ========================================
    // SEÇÃO 1: RECRUTAMENTO & SELEÇÃO
    // ========================================
    renderSecaoRecrutamento(data) {
        // KPIs
        document.getElementById('kpi-tempo-contratacao').textContent = 
            data.kpis.tempo_medio_contratacao || '--';
        document.getElementById('kpi-vagas-abertas').textContent = 
            data.kpis.vagas_abertas || 0;
        document.getElementById('kpi-vagas-fechadas').textContent = 
            data.kpis.vagas_fechadas || 0;
        document.getElementById('kpi-vagas-canceladas').textContent = 
            data.kpis.vagas_canceladas || 0;
        
        // Gráficos
        this.renderChartTempoCargo(data.graficos.tempo_por_cargo);
        this.renderChartTempoDepartamento(data.graficos.tempo_por_departamento);
        this.renderChartEvolucaoVagas(data.graficos.evolucao_vagas);
        
        // Tabela
        this.renderTableVagasAbertas(data.tabelas.vagas_abertas);
    },
    
    renderChartTempoCargo(dados) {
        const ctx = document.getElementById('chart-tempo-cargo');
        if (!ctx) return;
        
        // Destruir gráfico anterior
        if (this.charts.tempoCargo) {
            this.charts.tempoCargo.destroy();
        }
        
        this.charts.tempoCargo = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: dados.labels || [],
                datasets: [{
                    label: 'Tempo Médio (dias)',
                    data: dados.values || [],
                    backgroundColor: 'rgba(111, 66, 193, 0.7)',
                    borderColor: 'rgba(111, 66, 193, 1)',
                    borderWidth: 2
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (context) => `${context.parsed.x} dias`
                        }
                    }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        title: { display: true, text: 'Dias' }
                    }
                }
            }
        });
    },
    
    renderChartTempoDepartamento(dados) {
        const ctx = document.getElementById('chart-tempo-departamento');
        if (!ctx) return;
        
        if (this.charts.tempoDepartamento) {
            this.charts.tempoDepartamento.destroy();
        }
        
        this.charts.tempoDepartamento = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: dados.labels || [],
                datasets: [{
                    label: 'Tempo Médio (dias)',
                    data: dados.values || [],
                    backgroundColor: 'rgba(13, 110, 253, 0.7)',
                    borderColor: 'rgba(13, 110, 253, 1)',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: { display: true, text: 'Dias' }
                    }
                }
            }
        });
    },
    
    renderChartEvolucaoVagas(dados) {
        const ctx = document.getElementById('chart-evolucao-vagas');
        if (!ctx) return;
        
        if (this.charts.evolucaoVagas) {
            this.charts.evolucaoVagas.destroy();
        }
        
        this.charts.evolucaoVagas = new Chart(ctx, {
            type: 'line',
            data: {
                labels: dados.labels || [],
                datasets: [
                    {
                        label: 'Abertas',
                        data: dados.abertas || [],
                        borderColor: 'rgba(111, 66, 193, 1)',
                        backgroundColor: 'rgba(111, 66, 193, 0.1)',
                        borderWidth: 2,
                        tension: 0.4
                    },
                    {
                        label: 'Fechadas',
                        data: dados.fechadas || [],
                        borderColor: 'rgba(40, 167, 69, 1)',
                        backgroundColor: 'rgba(40, 167, 69, 0.1)',
                        borderWidth: 2,
                        tension: 0.4
                    },
                    {
                        label: 'Canceladas',
                        data: dados.canceladas || [],
                        borderColor: 'rgba(255, 193, 7, 1)',
                        backgroundColor: 'rgba(255, 193, 7, 0.1)',
                        borderWidth: 2,
                        tension: 0.4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: true, position: 'top' }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { stepSize: 1 }
                    }
                }
            }
        });
    },
    
    renderTableVagasAbertas(vagas) {
        const tbody = document.querySelector('#table-vagas-abertas tbody');
        if (!tbody) return;
        
        tbody.innerHTML = '';
        
        if (!vagas || vagas.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center">Nenhuma vaga em aberto no momento</td>
                </tr>
            `;
            return;
        }
        
        vagas.forEach(vaga => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${vaga.titulo}</td>
                <td>${vaga.cargo}</td>
                <td>${vaga.departamento || 'N/A'}</td>
                <td>${this.formatDate(vaga.data_abertura)}</td>
                <td class="text-center">
                    <span class="badge ${vaga.dias_aberto > 60 ? 'badge-danger' : vaga.dias_aberto > 30 ? 'badge-warning' : 'badge-info'}">
                        ${vaga.dias_aberto} dias
                    </span>
                </td>
                <td class="text-center">
                    <button class="btn btn-sm btn-primary" onclick="DashboardAnalitico.verVaga('${vaga.id}')">
                        <i class="mdi mdi-eye"></i>
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    },
    
    // ========================================
    // SEÇÃO 2: TURNOVER & RETENÇÃO
    // ========================================
    renderSecaoTurnover(data) {
        // KPIs
        document.getElementById('kpi-turnover-geral').textContent = 
            `${data.kpis.turnover_geral || 0}%`;
        document.getElementById('kpi-desligamentos').textContent = 
            data.kpis.desligamentos || 0;
        document.getElementById('kpi-admissoes').textContent = 
            data.kpis.admissoes || 0;
        document.getElementById('kpi-tempo-permanencia').textContent = 
            data.kpis.tempo_medio_permanencia || '--';
        document.getElementById('kpi-saldo-liquido').textContent = 
            data.kpis.saldo_liquido || 0;
        document.getElementById('kpi-headcount-atual').textContent = 
            data.kpis.headcount_atual || 0;
        
        // Gráficos
        this.renderChartTurnoverDepartamento(data.graficos.turnover_por_departamento);
        this.renderChartTurnoverCargo(data.graficos.turnover_por_cargo);
        this.renderChartTempoCasa(data.graficos.desligamentos_por_tempo_casa);
        this.renderChartFaixaEtaria(data.graficos.turnover_por_faixa_etaria);
        this.renderChartEvolucaoTurnover(data.graficos.evolucao_turnover);
        
        // Tabela
        this.renderTableDesligamentos(data.tabelas.desligamentos_recentes);
    },
    
    renderChartTurnoverDepartamento(dados) {
        const ctx = document.getElementById('chart-turnover-departamento');
        if (!ctx) return;
        
        if (this.charts.turnoverDept) {
            this.charts.turnoverDept.destroy();
        }
        
        this.charts.turnoverDept = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: dados.labels || [],
                datasets: [{
                    label: 'Turnover (%)',
                    data: dados.values || [],
                    backgroundColor: 'rgba(220, 53, 69, 0.7)',
                    borderColor: 'rgba(220, 53, 69, 1)',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: { display: true, text: '%' }
                    }
                }
            }
        });
    },
    
    renderChartTurnoverCargo(dados) {
        const ctx = document.getElementById('chart-turnover-cargo');
        if (!ctx) return;
        
        if (this.charts.turnoverCargo) {
            this.charts.turnoverCargo.destroy();
        }
        
        this.charts.turnoverCargo = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: dados.labels || [],
                datasets: [{
                    label: 'Turnover (%)',
                    data: dados.values || [],
                    backgroundColor: 'rgba(253, 126, 20, 0.7)',
                    borderColor: 'rgba(253, 126, 20, 1)',
                    borderWidth: 2
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        title: { display: true, text: '%' }
                    }
                }
            }
        });
    },
    
    renderChartTempoCasa(dados) {
        const ctx = document.getElementById('chart-tempo-casa');
        if (!ctx) return;
        
        if (this.charts.tempoCasa) {
            this.charts.tempoCasa.destroy();
        }
        
        this.charts.tempoCasa = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: dados.labels || ['< 3 meses', '3-6 meses', '6-12 meses', '1-3 anos', '> 3 anos'],
                datasets: [{
                    label: 'Quantidade de Desligamentos',
                    data: dados.values || [],
                    backgroundColor: 'rgba(111, 66, 193, 0.7)',
                    borderColor: 'rgba(111, 66, 193, 1)',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { stepSize: 1 }
                    }
                }
            }
        });
    },
    
    renderChartFaixaEtaria(dados) {
        const ctx = document.getElementById('chart-faixa-etaria');
        if (!ctx) return;
        
        if (this.charts.faixaEtaria) {
            this.charts.faixaEtaria.destroy();
        }
        
        this.charts.faixaEtaria = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: dados.labels || ['18-25', '26-35', '36-45', '46-55', '56+'],
                datasets: [{
                    label: 'Desligamentos',
                    data: dados.values || [],
                    backgroundColor: 'rgba(23, 162, 184, 0.7)',
                    borderColor: 'rgba(23, 162, 184, 1)',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { stepSize: 1 }
                    }
                }
            }
        });
    },
    
    renderChartEvolucaoTurnover(dados) {
        const ctx = document.getElementById('chart-evolucao-turnover');
        if (!ctx) return;
        
        if (this.charts.evolucaoTurnover) {
            this.charts.evolucaoTurnover.destroy();
        }
        
        this.charts.evolucaoTurnover = new Chart(ctx, {
            type: 'line',
            data: {
                labels: dados.labels || [],
                datasets: [{
                    label: 'Turnover (%)',
                    data: dados.values || [],
                    borderColor: 'rgba(220, 53, 69, 1)',
                    backgroundColor: 'rgba(220, 53, 69, 0.1)',
                    borderWidth: 3,
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: { display: true, text: '%' }
                    }
                }
            }
        });
    },
    
    renderTableDesligamentos(desligamentos) {
        const tbody = document.querySelector('#table-desligamentos tbody');
        if (!tbody) return;
        
        tbody.innerHTML = '';
        
        if (!desligamentos || desligamentos.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center">Nenhum desligamento nos últimos 30 dias</td>
                </tr>
            `;
            return;
        }
        
        desligamentos.forEach(desl => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${desl.nome}</td>
                <td>${desl.cargo}</td>
                <td>${desl.departamento || 'N/A'}</td>
                <td>${this.formatDate(desl.data_admissao)}</td>
                <td>${this.formatDate(desl.data_desligamento)}</td>
                <td class="text-center">
                    <span class="badge ${desl.tempo_casa_meses < 6 ? 'badge-danger' : desl.tempo_casa_meses < 12 ? 'badge-warning' : 'badge-info'}">
                        ${desl.tempo_casa}
                    </span>
                </td>
                <td>${desl.motivo || 'Não informado'}</td>
            `;
            tbody.appendChild(tr);
        });
    },
    
    // ========================================
    // NAVEGAÇÃO ENTRE SEÇÕES
    // ========================================
    switchSection(sectionName) {
        // Atualizar abas
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-section="${sectionName}"]`)?.classList.add('active');
        
        // Atualizar seções
        document.querySelectorAll('.dashboard-section').forEach(section => {
            section.classList.remove('active');
        });
        document.getElementById(`section-${sectionName}`)?.classList.add('active');
    },
    
    // ========================================
    // UTILIDADES
    // ========================================
    showLoading(show) {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.style.display = show ? 'flex' : 'none';
        }
    },
    
    showError(message) {
        alert(message); // TODO: Implementar toast/notification system
    },
    
    formatDate(dateString) {
        if (!dateString) return 'N/A';
        const date = new Date(dateString);
        return date.toLocaleDateString('pt-BR');
    },
    
    searchTable(tableId, searchTerm) {
        const table = document.getElementById(tableId);
        if (!table) return;
        
        const rows = table.querySelectorAll('tbody tr:not(.loading-row)');
        const term = searchTerm.toLowerCase();
        
        rows.forEach(row => {
            const text = row.textContent.toLowerCase();
            row.style.display = text.includes(term) ? '' : 'none';
        });
    },
    
    verVaga(vagaId) {
        console.log('Ver vaga:', vagaId);
        // TODO: Implementar visualização de vaga
    }
};

// ========================================
// INICIALIZAÇÃO
// ========================================
document.addEventListener('DOMContentLoaded', () => {
    DashboardAnalitico.init();
});
