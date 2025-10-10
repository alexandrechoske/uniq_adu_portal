// Dashboard Importações Resumido - JavaScript

class DashboardImportacoesResumido {
    constructor() {
        this.currentPage = 1;
        this.totalPages = 1;
        this.perPage = 10;
        this.isLoading = false;
        this.autoRefreshInterval = null;
        this.autoRefreshEnabled = true;
        this.autoRefreshTimer = 30000; // 30 segundos
        
        // Configurações para rolagem automática de páginas
        this.autoPageLoopInterval = null;
        this.autoPageLoopEnabled = true;
        this.autoPageLoopTimer = 15000; // 15 segundos por página
        
        // Settings management
        this.settings = {
            autoLoop: true,
            autoRefresh: true,
            loopInterval: 15,
            refreshInterval: 30,
            compactMode: false,
            showFilters: true,
            pagination: 100,
            apiTimeout: 30,
            animationsEnabled: true,
            tvMode: false,
            companyFilterEnabled: false,
            selectedCompanies: []  // Mudança para array
        };
        
        // TV Mode state
        this.tvModeEnabled = false;
        this.tvExitButton = null;
        
        this.init();
    }
    
    init() {
        this.loadSettings();
        this.bindEvents();
        this.checkCompaniesAndLoad(); // Nova função que verifica empresas antes de carregar
        this.startAutoRefresh();
        this.startAutoPageLoop();
        this.updateAutoPageLoopButton();
        this.updateClock();
        this.applySettings();
        
        // Atualizar relógio a cada minuto
        setInterval(() => this.updateClock(), 60000);
    }
    
    loadSettings() {
        const savedSettings = localStorage.getItem('dashboardSettings');
        if (savedSettings) {
            this.settings = { ...this.settings, ...JSON.parse(savedSettings) };
            this.autoPageLoopTimer = this.settings.loopInterval * 1000;
            this.autoRefreshTimer = this.settings.refreshInterval * 1000;
            this.autoPageLoopEnabled = this.settings.autoLoop;
            this.autoRefreshEnabled = this.settings.autoRefresh;
        }
    }
    
    saveSettings() {
        localStorage.setItem('dashboardSettings', JSON.stringify(this.settings));
    }
    
    applySettings() {
        // Apply compact mode
        const container = document.querySelector('.dashboard-resumido-container');
        if (container) {
            if (this.settings.compactMode) {
                container.classList.add('compact-mode');
            } else {
                container.classList.remove('compact-mode');
            }
            
            // Apply animations setting
            if (this.settings.animationsEnabled) {
                container.classList.remove('animations-disabled');
            } else {
                container.classList.add('animations-disabled');
            }
        }
        
        // Apply filter visibility
        const filterSection = document.querySelector('.filters-section');
        if (filterSection) {
            filterSection.style.display = this.settings.showFilters ? 'block' : 'none';
        }
    }
    
    bindEvents() {
        // Botão de configurações
        document.getElementById('btn-settings')?.addEventListener('click', () => {
            this.openSettingsModal();
        });
        
        // Botão de modo TV
        document.getElementById('btn-fullscreen-tv')?.addEventListener('click', () => {
            this.toggleTVMode();
        });
        
        // Fechar modal
        document.getElementById('btn-close-settings')?.addEventListener('click', () => {
            this.closeSettingsModal();
        });
        
        // Fechar modal clicando fora
        document.getElementById('settings-modal')?.addEventListener('click', (e) => {
            if (e.target.id === 'settings-modal') {
                this.closeSettingsModal();
            }
        });
        
        // Checkbox de filtro (se ainda existir)
        document.getElementById('filtro-embarque')?.addEventListener('change', () => {
            this.currentPage = 1;
            this.loadData();
        });
        
        // Botões de paginação
        document.getElementById('btn-prev-page')?.addEventListener('click', () => {
            this.pauseAutoPageLoop(); // Pausar rolagem automática ao clicar
            if (this.currentPage > 1) {
                this.currentPage--;
                this.loadData();
            }
        });
        
        document.getElementById('btn-next-page')?.addEventListener('click', () => {
            this.pauseAutoPageLoop(); // Pausar rolagem automática ao clicar
            if (this.currentPage < this.totalPages) {
                this.currentPage++;
                this.loadData();
            }
        });
        
        // Settings events
        this.bindSettingsEvents();
        
        // Pausar auto-refresh e auto-page-loop quando o usuário está interagindo
        document.addEventListener('click', () => {
            this.resetAutoRefresh();
            this.pauseAutoPageLoop(10000); // Pausar por 10 segundos
        });
        
        document.addEventListener('keydown', (e) => {
            this.resetAutoRefresh();
            this.pauseAutoPageLoop(10000); // Pausar por 10 segundos
            this.handleKeyPress(e); // Adicionar handler para ESC
        });
    }
    
    bindSettingsEvents() {
        // Auto Loop Toggle
        document.getElementById('auto-loop-enabled')?.addEventListener('change', (e) => {
            this.settings.autoLoop = e.target.checked;
            this.autoPageLoopEnabled = e.target.checked;
            this.saveSettings();
            if (e.target.checked) {
                this.startAutoPageLoop();
            } else {
                this.stopAutoPageLoop();
            }
            this.updateAutoPageLoopButton();
        });

        // Auto Refresh Toggle
        document.getElementById('auto-refresh-enabled')?.addEventListener('change', (e) => {
            this.settings.autoRefresh = e.target.checked;
            this.autoRefreshEnabled = e.target.checked;
            this.saveSettings();
            if (e.target.checked) {
                this.startAutoRefresh();
            } else {
                this.stopAutoRefresh();
            }
        });

        // Loop Interval
        document.getElementById('auto-loop-interval')?.addEventListener('change', (e) => {
            this.settings.loopInterval = parseInt(e.target.value);
            this.autoPageLoopTimer = this.settings.loopInterval * 1000;
            this.saveSettings();
            if (this.autoPageLoopEnabled) {
                this.startAutoPageLoop();
            }
        });

        // Refresh Interval
        document.getElementById('auto-refresh-interval')?.addEventListener('change', (e) => {
            this.settings.refreshInterval = parseInt(e.target.value);
            this.autoRefreshTimer = this.settings.refreshInterval * 1000;
            this.saveSettings();
            if (this.autoRefreshEnabled) {
                this.startAutoRefresh();
            }
        });

        // Records per page
        document.getElementById('records-per-page')?.addEventListener('change', (e) => {
            this.settings.pagination = parseInt(e.target.value);
            this.perPage = parseInt(e.target.value);
            this.saveSettings();
            this.currentPage = 1;
            this.loadData();
        });

        // Compact Mode
        document.getElementById('compact-mode')?.addEventListener('change', (e) => {
            this.settings.compactMode = e.target.checked;
            this.saveSettings();
            this.applySettings();
        });

        // Animations Toggle
        document.getElementById('animations-enabled')?.addEventListener('change', (e) => {
            this.settings.animationsEnabled = e.target.checked;
            this.saveSettings();
            this.applySettings();
        });

        // Filter embarque default
        document.getElementById('filter-embarque-default')?.addEventListener('change', (e) => {
            this.settings.showFilters = e.target.checked;
            this.saveSettings();
            this.applySettings();
        });

        // Manual Refresh
        document.getElementById('btn-manual-refresh')?.addEventListener('click', () => {
            this.loadData();
        });

        // Toggle Loop Control
        document.getElementById('btn-toggle-loop')?.addEventListener('click', () => {
            this.toggleAutoPageLoop();
        });

        // Reset Settings
        document.getElementById('btn-reset-settings')?.addEventListener('click', () => {
            this.resetSettings();
        });

        // Apply filters (both buttons)
        document.getElementById('btn-apply-filter')?.addEventListener('click', () => {
            this.applyAllFilters();
        });
        
        document.getElementById('btn-apply-all-filters')?.addEventListener('click', () => {
            this.applyAllFilters();
            this.closeSettingsModal();
        });

        // Company Filter Toggle - Controla visibilidade da seção
        document.getElementById('company-filter-enabled')?.addEventListener('change', (e) => {
            this.settings.companyFilterEnabled = e.target.checked;
            this.saveSettings();
            
            // Controlar visibilidade das seções de filtro de empresa
            const companyFilterSections = document.querySelectorAll('.company-filter-section');
            companyFilterSections.forEach(section => {
                section.style.display = e.target.checked ? 'block' : 'none';
            });
            
            if (e.target.checked) {
                this.loadCompanies();
            } else {
                this.settings.selectedCompanies = [];
                this.saveSettings();
                // Não aplicar automaticamente - aguardar "Aplicar Filtros"
            }
        });

        // Company Search
        document.getElementById('company-search')?.addEventListener('input', (e) => {
            this.filterCompanyList(e.target.value);
        });

        // Select All Companies
        document.getElementById('btn-select-all-companies')?.addEventListener('click', () => {
            this.selectAllCompanies();
        });

        // Clear Company Filter
        document.getElementById('btn-clear-company-filter')?.addEventListener('click', () => {
            this.clearCompanySelection();
        });

        // Cancel/Close settings
        document.getElementById('btn-cancel-settings')?.addEventListener('click', () => {
            this.closeSettingsModal();
        });
    }
    
    openSettingsModal() {
        this.updateSettingsForm();
        this.loadCompanies(); // Load companies when opening settings
        const modal = document.getElementById('settings-modal');
        if (modal) {
            modal.classList.add('show');
        }
    }
    
    closeSettingsModal() {
        const modal = document.getElementById('settings-modal');
        if (modal) {
            modal.classList.remove('show');
        }
    }
    
    updateSettingsForm() {
        // Update form values with current settings
        const autoLoopToggle = document.getElementById('auto-loop-enabled');
        const autoRefreshToggle = document.getElementById('auto-refresh-enabled');
        const loopIntervalInput = document.getElementById('auto-loop-interval');
        const refreshIntervalInput = document.getElementById('auto-refresh-interval');
        const compactModeToggle = document.getElementById('compact-mode');
        const animationsToggle = document.getElementById('animations-enabled');
        const filterToggle = document.getElementById('filter-embarque-default');
        const recordsPerPageSelect = document.getElementById('records-per-page');
        const companyFilterToggle = document.getElementById('company-filter-enabled');
        const companySelect = document.getElementById('company-select');
        
        if (autoLoopToggle) autoLoopToggle.checked = this.settings.autoLoop;
        if (autoRefreshToggle) autoRefreshToggle.checked = this.settings.autoRefresh;
        if (loopIntervalInput) loopIntervalInput.value = this.settings.loopInterval;
        if (refreshIntervalInput) refreshIntervalInput.value = this.settings.refreshInterval;
        if (compactModeToggle) compactModeToggle.checked = this.settings.compactMode;
        if (animationsToggle) animationsToggle.checked = this.settings.animationsEnabled;
        if (filterToggle) filterToggle.checked = this.settings.showFilters;
        if (recordsPerPageSelect) recordsPerPageSelect.value = this.settings.pagination;
        if (companyFilterToggle) companyFilterToggle.checked = this.settings.companyFilterEnabled;
        
        // Controlar visibilidade das seções de filtro de empresa
        const companyFilterSections = document.querySelectorAll('.company-filter-section');
        companyFilterSections.forEach(section => {
            section.style.display = this.settings.companyFilterEnabled ? 'block' : 'none';
        });
        
        // Restore multiple company selections
        if (companySelect && this.settings.selectedCompanies && this.settings.selectedCompanies.length > 0) {
            Array.from(companySelect.options).forEach(option => {
                option.selected = this.settings.selectedCompanies.includes(option.value);
            });
        }
        
        // Update status
        this.updateSettingsStatus();
        this.updateLoopControlButton();
    }
    
    updateSettingsStatus() {
        const statusElement = document.querySelector('.settings-status');
        if (statusElement) {
            if (this.autoPageLoopEnabled) {
                statusElement.textContent = `Loop ativo - ${this.settings.loopInterval}s`;
                statusElement.style.color = '#10b981';
            } else {
                statusElement.textContent = 'Loop inativo';
                statusElement.style.color = '#6b7280';
            }
        }
    }
    
    updateLoopControlButton() {
        const toggleBtn = document.getElementById('btn-toggle-loop');
        const icon = document.getElementById('loop-control-icon');
        const text = document.getElementById('loop-control-text');
        
        if (toggleBtn && icon && text) {
            if (this.autoPageLoopEnabled) {
                icon.className = 'mdi mdi-pause';
                text.textContent = 'Parar Loop';
                toggleBtn.classList.remove('btn-secondary');
                toggleBtn.classList.add('btn-warning');
            } else {
                icon.className = 'mdi mdi-play';
                text.textContent = 'Iniciar Loop';
                toggleBtn.classList.remove('btn-warning');
                toggleBtn.classList.add('btn-secondary');
            }
        }
    }
    
    resetSettings() {
        if (confirm('Tem certeza que deseja resetar todas as configurações?')) {
            this.settings = {
                autoLoop: true,
                autoRefresh: true,
                loopInterval: 15,
                refreshInterval: 30,
                compactMode: false,
                showFilters: true,
                pagination: 10,
                apiTimeout: 30
            };
            
            this.autoPageLoopTimer = this.settings.loopInterval * 1000;
            this.autoRefreshTimer = this.settings.refreshInterval * 1000;
            this.autoPageLoopEnabled = this.settings.autoLoop;
            this.autoRefreshEnabled = this.settings.autoRefresh;
            this.perPage = this.settings.pagination;
            
            this.saveSettings();
            this.updateSettingsForm();
            this.applySettings();
            
            if (this.settings.autoLoop) {
                this.startAutoPageLoop();
            }
            if (this.settings.autoRefresh) {
                this.startAutoRefresh();
            }
            
            this.updateAutoPageLoopButton();
            this.currentPage = 1;
            this.loadData();
        }
    }
    
    startAutoRefresh() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
        }
        
        this.autoRefreshInterval = setInterval(() => {
            if (this.autoRefreshEnabled && !this.isLoading) {
                this.loadData(true); // true = silent refresh
            }
        }, this.autoRefreshTimer);
    }
    
    resetAutoRefresh() {
        this.startAutoRefresh();
    }
    
    stopAutoRefresh() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
            this.autoRefreshInterval = null;
        }
    }
    
    // Métodos para controlar rolagem automática de páginas
    startAutoPageLoop() {
        if (this.autoPageLoopInterval) {
            clearInterval(this.autoPageLoopInterval);
        }
        
        this.autoPageLoopInterval = setInterval(() => {
            if (this.autoPageLoopEnabled && !this.isLoading && this.totalPages > 1) {
                this.nextPageLoop();
            }
        }, this.autoPageLoopTimer);
    }
    
    nextPageLoop() {
        // Se estiver na última página, volta para a primeira
        if (this.currentPage >= this.totalPages) {
            this.currentPage = 1;
        } else {
            this.currentPage++;
        }
        
        // Carregar dados da nova página silenciosamente
        this.loadData(true);
    }
    
    pauseAutoPageLoop(duration = null) {
        this.autoPageLoopEnabled = false;
        
        if (this.autoPageLoopInterval) {
            clearInterval(this.autoPageLoopInterval);
            this.autoPageLoopInterval = null;
        }
        
        // Se especificado um tempo, retomar após esse período
        if (duration) {
            setTimeout(() => {
                this.resumeAutoPageLoop();
            }, duration);
        }
    }
    
    resumeAutoPageLoop() {
        this.autoPageLoopEnabled = true;
        this.startAutoPageLoop();
    }
    
    stopAutoPageLoop() {
        this.autoPageLoopEnabled = false;
        if (this.autoPageLoopInterval) {
            clearInterval(this.autoPageLoopInterval);
            this.autoPageLoopInterval = null;
        }
    }
    
    toggleAutoPageLoop() {
        if (this.autoPageLoopEnabled) {
            this.pauseAutoPageLoop();
        } else {
            this.resumeAutoPageLoop();
        }
        this.updateAutoPageLoopButton();
    }
    
    updateAutoPageLoopButton() {
        const button = document.getElementById('btn-toggle-auto-loop');
        const icon = document.getElementById('auto-loop-icon');
        const text = document.getElementById('auto-loop-text');
        const indicator = document.getElementById('auto-loop-indicator');
        
        // Verificar se os elementos existem antes de tentar modificá-los
        if (button && icon && text) {
            if (this.autoPageLoopEnabled) {
                button.className = 'btn btn-secondary';
                icon.className = 'mdi mdi-pause-circle';
                text.textContent = 'Parar Loop';
                if (indicator) {
                    indicator.classList.remove('hidden');
                }
            } else {
                button.className = 'btn btn-primary';
                icon.className = 'mdi mdi-play-circle';
                text.textContent = 'Iniciar Loop';
                if (indicator) {
                    indicator.classList.add('hidden');
                }
            }
        } else {
            // Se os elementos não existem, apenas atualizar o indicador se disponível
            if (indicator) {
                if (this.autoPageLoopEnabled) {
                    indicator.classList.remove('hidden');
                } else {
                    indicator.classList.add('hidden');
                }
            }
        }
    }
    
    showLoading() {
        const loadingOverlay = document.getElementById('loading-overlay');
        if (loadingOverlay) {
            loadingOverlay.style.display = 'flex';
        }
        this.isLoading = true;
    }
    
    hideLoading() {
        const loadingOverlay = document.getElementById('loading-overlay');
        if (loadingOverlay) {
            loadingOverlay.style.display = 'none';
        }
        this.isLoading = false;
    }
    
    updateClock() {
        const now = new Date();
        const time = now.toLocaleTimeString('pt-BR', { 
            hour: '2-digit', 
            minute: '2-digit',
            hour12: false 
        });
        
        const months = [
            'JANEIRO', 'FEVEREIRO', 'MARÇO', 'ABRIL', 'MAIO', 'JUNHO',
            'JULHO', 'AGOSTO', 'SETEMBRO', 'OUTUBRO', 'NOVEMBRO', 'DEZEMBRO'
        ];
        
        const day = now.getDate();
        const month = months[now.getMonth()];
        const date = `${day} ${month}`;
        
        document.getElementById('current-time').textContent = time;
        document.getElementById('current-date').textContent = date;
    }

    async checkCompaniesAndLoad() {
        // Verifica informações das empresas do usuário e decide como carregar o dashboard
        try {
            console.log('[DASHBOARD] Verificando informações das empresas do usuário...');
            
            const response = await fetch('/dash-importacoes-resumido/api/companies-info');
            
            if (!response.ok) {
                console.error('[DASHBOARD] Erro ao buscar informações das empresas:', response.status);
                this.loadData(); // Fallback para carregamento normal
                return;
            }
            
            const data = await response.json();
            
            if (!data.success) {
                console.error('[DASHBOARD] Erro na resposta das empresas:', data.error);
                this.loadData(); // Fallback para carregamento normal
                return;
            }
            
            console.log('[DASHBOARD] Informações das empresas:', data);
            
            if (data.auto_load && data.company_count === 1) {
                // Uma empresa - carregar automaticamente
                console.log('[DASHBOARD] Usuário com 1 empresa - carregando automaticamente');
                if (data.auto_company) {
                    this.settings.selectedCompanies = [data.auto_company];
                    this.settings.companyFilterEnabled = true;
                    this.saveSettings();
                }
                this.showCompanyMessage(data.message, 'info');
                this.loadData();
                
            } else if (data.require_filter && (data.company_count === 'all' || data.company_count > 1)) {
                // Múltiplas empresas ou admin com acesso a todas - exigir filtro
                console.log('[DASHBOARD] Usuário com múltiplas empresas ou admin - mostrando mensagem de seleção');
                this.showFilterRequiredMessage(data.message, data.company_count);
                // Ativar filtro de empresa automaticamente
                this.settings.companyFilterEnabled = true;
                this.saveSettings();
                this.applySettings();
                // Remover loading e carregar header básico
                this.hideLoading();
                this.loadBasicHeader();
                
            } else if (data.company_count === 0) {
                // Nenhuma empresa - somente neste caso mostrar warning
                console.log('[DASHBOARD] Usuário sem empresas vinculadas');
                this.showCompanyMessage(data.message, 'warning');
                this.hideLoading();
                
            } else {
                // Fallback - carregar normalmente
                console.log('[DASHBOARD] Fallback - carregando normalmente');
                this.loadData();
            }
            
        } catch (error) {
            console.error('[DASHBOARD] Erro ao verificar empresas:', error);
            this.loadData(); // Fallback para carregamento normal
        }
    }

    showFilterRequiredMessage(message, companyCount) {
        // Mostra mensagem informando que é necessário selecionar empresas
        const tbody = document.getElementById('table-body');
        if (tbody) {
            const countText = companyCount === 'all' ? 'todas as empresas' : `${companyCount} empresas`;
            tbody.innerHTML = `
                <tr>
                    <td colspan="11" style="text-align: center; padding: 3rem; color: #374151;">
                        <div style="display: flex; flex-direction: column; align-items: center; gap: 1.5rem;">
                            <i class="mdi mdi-filter-variant" style="font-size: 4rem; color: #3B82F6;"></i>
                            <div>
                                <h3 style="margin: 0; color: #374151; font-size: 1.5rem;">Filtro de Empresa Necessário</h3>
                                <p style="margin: 0.75rem 0; color: #6B7280; font-size: 1.1rem; max-width: 500px;">
                                    ${message}
                                </p>
                                <p style="margin: 0.5rem 0 0 0; color: #6B7280; font-size: 0.9rem;">
                                    <strong>Você tem acesso a ${countText}</strong><br>
                                    Use o filtro de empresas na barra superior para selecionar e carregar os dados.
                                </p>
                            </div>
                        </div>
                    </td>
                </tr>
            `;
        }
    }

    showCompanyMessage(message, type = 'info') {
        // Mostra mensagem informativa sobre empresas
        const alertClass = type === 'warning' ? 'alert-warning' : 'alert-info';
        const iconClass = type === 'warning' ? 'mdi-alert' : 'mdi-information';
        
        // Criar elemento de alerta se não existir
        let alertElement = document.getElementById('company-alert');
        if (!alertElement) {
            alertElement = document.createElement('div');
            alertElement.id = 'company-alert';
            alertElement.style.cssText = `
                position: fixed; top: 20px; right: 20px; z-index: 1000; 
                max-width: 400px; padding: 1rem; border-radius: 0.5rem;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); display: flex; 
                align-items: center; gap: 0.75rem;
            `;
            document.body.appendChild(alertElement);
        }
        
        const bgColor = type === 'warning' ? '#FEF3C7' : '#DBEAFE';
        const textColor = type === 'warning' ? '#92400E' : '#1E40AF';
        const borderColor = type === 'warning' ? '#F59E0B' : '#3B82F6';
        
        alertElement.style.backgroundColor = bgColor;
        alertElement.style.color = textColor;
        alertElement.style.borderLeft = `4px solid ${borderColor}`;
        
        alertElement.innerHTML = `
            <i class="mdi ${iconClass}" style="font-size: 1.5rem; color: ${borderColor};"></i>
            <div style="flex: 1;">
                <p style="margin: 0; font-weight: 500;">${message}</p>
            </div>
            <button onclick="this.parentElement.remove()" 
                    style="background: none; border: none; color: ${textColor}; 
                           cursor: pointer; padding: 0.25rem;">
                <i class="mdi mdi-close"></i>
            </button>
        `;
        
        // Auto-remover após 10 segundos
        setTimeout(() => {
            if (alertElement && alertElement.parentElement) {
                alertElement.remove();
            }
        }, 10000);
    }
    
    async loadData(silent = false) {
        if (this.isLoading) return;
        
        if (!silent) {
            this.showLoading();
        }
        
        try {
            // Verificar se existe filtro de embarque (legacy support)
            const filtroEmbarqueElement = document.getElementById('filtro-embarque');
            const filtroEmbarque = filtroEmbarqueElement?.checked ? 'preenchida' : '';
            
            const params = new URLSearchParams({
                page: this.currentPage,
                per_page: this.perPage,
                filtro_embarque: filtroEmbarque
            });

            // Adicionar filtro de empresas se ativo (suporte múltiplas empresas)
            if (this.settings.companyFilterEnabled && this.settings.selectedCompanies && this.settings.selectedCompanies.length > 0) {
                // Enviar empresas separadas por vírgula
                params.append('company_filter', this.settings.selectedCompanies.join(','));
                console.log('[DASHBOARD] Aplicando filtro de empresas:', this.settings.selectedCompanies);
            }
            
            const response = await fetch(`/dash-importacoes-resumido/api/data?${params}`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success) {

                this.updateHeader(data.header);
                this.updateTable(data.data);
                this.updatePagination(data.pagination);
            } else if (data.require_filter) {
                // Caso especial: filtro de empresa obrigatório
                console.log('[DASHBOARD] Filtro de empresa obrigatório detectado');
                this.showFilterRequiredMessage(data.message, 'multiple');
                this.updateHeader(data.header); // Atualizar header mesmo sem dados
            } else {
                this.showError(data.error || 'Erro ao carregar dados');
            }
            
        } catch (error) {
            console.error('Erro ao carregar dados:', error);
            
            if (error.message.includes('404')) {
                this.showNoDataMessage();
            } else {
                this.showError('Erro ao carregar dados. Tente novamente.');
            }
        } finally {
            if (!silent) {
                this.hideLoading();
            }
        }
    }
    
    loadBasicHeader() {
        // Carrega header básico sem dados específicos
        document.getElementById('total-processos').textContent = 
            'TOTAL: 0 PROCESSOS';
        
        document.getElementById('count-maritimo').textContent = '0';
        document.getElementById('count-aereo').textContent = '0';
        document.getElementById('count-terrestre').textContent = '0';
        
        // Manter cotações existentes ou padrão
        const dolarEl = document.getElementById('dolar-rate-top');
        const euroEl = document.getElementById('euro-rate-top');
        if (dolarEl && (dolarEl.textContent === '' || dolarEl.textContent === 'Carregando...')) {
            dolarEl.textContent = '-.----';
        }
        if (euroEl && (euroEl.textContent === '' || euroEl.textContent === 'Carregando...')) {
            euroEl.textContent = '-.----';
        }
    }
    
    updateHeader(headerData) {
        // Atualizar métricas do cabeçalho
        document.getElementById('total-processos').textContent = 
            `TOTAL: ${headerData.total_processos} PROCESSOS`;
        
        document.getElementById('count-maritimo').textContent = headerData.count_maritimo || 0;
        document.getElementById('count-aereo').textContent = headerData.count_aereo || 0;
        document.getElementById('count-terrestre').textContent = headerData.count_terrestre || 0;
        
        // Atualizar cotações
        if (headerData.exchange_rates) {
            const dolarRate = headerData.exchange_rates.dolar;
            const euroRate = headerData.exchange_rates.euro;
            
            // Atualizar cotações no topo
            document.getElementById('dolar-rate-top').textContent = 
                dolarRate ? dolarRate.toFixed(4) : '-.----';
            document.getElementById('euro-rate-top').textContent = 
                euroRate ? euroRate.toFixed(4) : '-.----';
        }

        // Atualizar logo e nome do cliente, se disponível
        if (headerData.client) {
            const logoEl = document.getElementById('client-logo');
            const nameEl = document.getElementById('client-name');
            if (logoEl && headerData.client.logo_url) {
                logoEl.src = headerData.client.logo_url;
            }
            if (nameEl && headerData.client.name) {
                nameEl.textContent = headerData.client.name;
            }
        }
    }
    
    updateTable(tableData) {

        
        const tbody = document.getElementById('table-body');
        
        // Adicionar classe de loading se animações estão habilitadas
        if (this.settings.animationsEnabled) {
            tbody.classList.add('loading');
            tbody.classList.remove('loaded');
        }
        
        // Pequeno delay para a animação de fade out
        setTimeout(() => {
            tbody.innerHTML = '';
            
            if (!tableData || tableData.length === 0) {

                tbody.innerHTML = `
                    <tr>
                        <td colspan="11" style="text-align: center; padding: 2rem; color: #6b7280;">
                            Nenhum dado encontrado
                        </td>
                    </tr>
                `;
                return;
            }
            
            tableData.forEach(row => {
                const tr = document.createElement('tr');
                
                // Formatar data de embarque com cor condicional
                const dataEmbarqueFormatted = this.formatDataEmbarque(row.data_embarque);
                
                // Formatar data de chegada com bandeirinha se próxima
                const dataChegadaFormatted = this.formatDataChegada(row.data_chegada);
                
                // Obter imagem do modal
                const modalImage = this.getModalImage(row.modal);

                
                // Verificar se há país para mostrar bandeira
                const paisContent = (row.pais_procedencia && row.pais_procedencia.trim() !== '') 
                    ? `<img src="${row.pais_flag || '/static/medias/flag_default.png'}" alt="${row.pais_procedencia}" class="flag-icon" title="${row.pais_procedencia}">` 
                    : '';
                
                tr.innerHTML = `
                    <td>
                        <img src="${modalImage}" alt="Modal ${row.modal}" class="modal-icon">
                    </td>
                    <td>${row.numero || ''}</td>
                    <td>${row.numero_di || ''}</td>
                    <td>
                        ${paisContent}
                    </td>
                    <td>${row.ref_importador || ''}</td>
                    <td>${dataEmbarqueFormatted}</td>
                    <td>${dataChegadaFormatted}</td>
                    <td>${row.data_registro || ''}</td>
                    <td>
                        ${row.canal ? `<div class="canal-indicator" style="background-color: ${row.canal_color || '#9E9E9E'}"></div>` : ''}
                    </td>
                    <td>${row.data_entrega || ''}</td>
                    <td>${row.urf_destino || '-'}</td>
                `;
                
                tbody.appendChild(tr);
            });
            
            // Adicionar linhas vazias para manter o layout consistente
            const emptyRowsNeeded = this.perPage - tableData.length;
            for (let i = 0; i < emptyRowsNeeded; i++) {
                const tr = document.createElement('tr');
                tr.classList.add('empty-row');
                tr.innerHTML = `
                    <td>&nbsp;</td>
                    <td>&nbsp;</td>
                    <td>&nbsp;</td>
                    <td>&nbsp;</td>
                    <td>&nbsp;</td>
                    <td>&nbsp;</td>
                    <td>&nbsp;</td>
                    <td>&nbsp;</td>
                    <td>&nbsp;</td>
                    <td>&nbsp;</td>
                    <td>&nbsp;</td>
                `;
                tbody.appendChild(tr);
            }
            
            // Adicionar classe de loaded se animações estão habilitadas
            if (this.settings.animationsEnabled) {
                tbody.classList.remove('loading');
                tbody.classList.add('loaded');
            }
        }, this.settings.animationsEnabled ? 200 : 0);
    }
    
    formatDataChegada(dataStr) {
        if (!dataStr || dataStr.trim() === '') {
            return '';
        }
        
        try {
            // Assumir que a data está no formato DD/MM/YYYY
            const [dia, mes, ano] = dataStr.split('/');
            const dataChegada = new Date(ano, mes - 1, dia);
            const hoje = new Date();
            
            // Zerar horários para comparação apenas da data
            dataChegada.setHours(0, 0, 0, 0);
            hoje.setHours(0, 0, 0, 0);
            
            // Se a data de chegada é exatamente hoje, mostrar indicador
            if (dataChegada.getTime() === hoje.getTime()) {
                return `<span class="data-chegada-proxima">
                    <i class="mdi mdi-clock"></i>
                    ${dataStr}
                </span>`;
            } else {
                return dataStr;
            }
        } catch (e) {
            return dataStr;
        }
    }
    
    formatDataEmbarque(dataStr) {
        if (!dataStr || dataStr.trim() === '') {
            return '';
        }
        
        try {
            // Assumindo formato DD/MM/YYYY
            const [day, month, year] = dataStr.split('/');
            const dataEmbarque = new Date(year, month - 1, day);
            const hoje = new Date();
            
            const className = dataEmbarque >= hoje ? 'data-embarque-red' : 'data-embarque-white';
            return `<span class="${className}">${dataStr}</span>`;
        } catch (error) {
            return dataStr;
        }
    }
    
    getModalImage(modal) {
        if (modal === null || modal === undefined) return '/static/medias/ship_color.png';
        const v = String(modal).trim().toUpperCase();
        // Normalizar sufixo .0
        const base = v.endsWith('.0') ? v.slice(0, -2) : v;
        
        // Mapear sinônimos
        const map = {
            '1': 'ship', 'MARITIMO': 'ship', 'MARÍTIMO': 'ship', 'MARITIMA': 'ship', 'MARÍTIMA': 'ship', 'NAVIO': 'ship', 'SHIP': 'ship', 'SEA': 'ship', 'OCEAN': 'ship',
            '4': 'plane', 'AEREO': 'plane', 'AÉREO': 'plane', 'AEREA': 'plane', 'AÉREA': 'plane', 'PLANE': 'plane', 'AIRPLANE': 'plane', 'AIR': 'plane', 'AVIAO': 'plane', 'AVIÃO': 'plane',
            '7': 'truck', 'TERRESTRE': 'truck', 'RODOVIARIO': 'truck', 'RODOVIÁRIO': 'truck', 'TRUCK': 'truck', 'ROAD': 'truck'
        };
        const key = map[base] || map[base.replace(/\W/g,'')] || map[base.replace('.','')] || 'ship';
        
        switch (key) {
            case 'plane': 
                return '/static/medias/plane_color.png';
            case 'truck': 
                return '/static/medias/truck_color.png';
            case 'ship':
            default: 
                return '/static/medias/ship_color.png';
        }
    }
    
    updatePagination(paginationData) {
        this.totalPages = paginationData.pages || 1;
        this.currentPage = paginationData.current_page || 1;
        
        // Atualizar apenas as informações de paginação no rodapé
        const pageInfoElement = document.getElementById('page-info');
        if (pageInfoElement) {
            pageInfoElement.textContent = `Página ${this.currentPage} de ${this.totalPages}`;
        }
        
        // Atualizar estado dos botões (verificar se existem primeiro)
        const btnPrev = document.getElementById('btn-prev-page');
        const btnNext = document.getElementById('btn-next-page');
        
        if (btnPrev) {
            btnPrev.disabled = this.currentPage <= 1;
        }
        if (btnNext) {
            btnNext.disabled = this.currentPage >= this.totalPages;
        }
    }
    
    showNoDataMessage() {
        // Mostrar mensagem de "sem dados" na tabela
        const tbody = document.getElementById('table-body');
        if (tbody) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="10" style="text-align: center; padding: 3rem; color: #6b7280;">
                        <div style="display: flex; flex-direction: column; align-items: center; gap: 1rem;">
                            <i class="mdi mdi-database-off" style="font-size: 3rem; color: #d1d5db;"></i>
                            <div>
                                <h3 style="margin: 0; color: #374151;">Nenhum dado encontrado</h3>
                                <p style="margin: 0.5rem 0 0 0; color: #6b7280;">
                                    Os dados ainda não foram carregados no cache.<br>
                                    Tente fazer login novamente ou aguarde o carregamento dos dados.
                                </p>
                            </div>
                        </div>
                    </td>
                </tr>
            `;
        }
        
        // Resetar métricas do cabeçalho
        this.updateHeader({
            total_processos: 0,
            count_maritimo: 0,
            count_aereo: 0,
            count_terrestre: 0,
            current_time: new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', hour12: false }),
            current_date: this.getCurrentDate(),
            exchange_rates: { dolar: null, euro: null }
        });
        
        // Resetar paginação
        this.updatePagination({
            total: 0,
            pages: 1,
            current_page: 1,
            per_page: this.perPage
        });
    }
    
    getCurrentDate() {
        const now = new Date();
        const months = [
            'JANEIRO', 'FEVEREIRO', 'MARÇO', 'ABRIL', 'MAIO', 'JUNHO',
            'JULHO', 'AGOSTO', 'SETEMBRO', 'OUTUBRO', 'NOVEMBRO', 'DEZEMBRO'
        ];
        const day = now.getDate();
        const month = months[now.getMonth()];
        return `${day} ${month}`;
    }
    
    showError(message) {
        // Criar e mostrar um toast de erro simples
        const errorDiv = document.createElement('div');
        errorDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #F44336;
            color: white;
            padding: 1rem 1.5rem;
            border-radius: 6px;
            z-index: 10000;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
            font-weight: 500;
        `;
        errorDiv.textContent = message;
        
        document.body.appendChild(errorDiv);
        
        // Remover após 5 segundos
        setTimeout(() => {
            if (errorDiv.parentNode) {
                errorDiv.parentNode.removeChild(errorDiv);
            }
        }, 5000);
    }
    
    destroy() {
        this.stopAutoRefresh();
        this.stopAutoPageLoop();
        this.exitTVMode(); // Sair do modo TV se estiver ativo
    }
    
    // Métodos para Modo TV
    toggleTVMode() {
        if (this.tvModeEnabled) {
            this.exitTVMode();
        } else {
            this.enterTVMode();
        }
    }
    
    enterTVMode() {
        this.tvModeEnabled = true;
        
        // Adicionar classe CSS para modo TV
        const container = document.querySelector('.dashboard-resumido-container');
        if (container) {
            container.classList.add('tv-fullscreen-mode');
        }
        
        // Criar botão de saída
        this.createTVExitButton();
        
        // Entrar em fullscreen se suportado
        if (document.documentElement.requestFullscreen) {
            document.documentElement.requestFullscreen().catch(err => {
                console.log('Erro ao entrar em fullscreen:', err);
            });
        }
        
        // Parar interações automáticas durante modo TV para evitar distrações
        this.pauseAutoPageLoop(0); // Pausar indefinidamente
        
        // Atualizar botão
        this.updateTVModeButton();
        
        console.log('Modo TV ativado');
    }
    
    exitTVMode() {
        if (!this.tvModeEnabled) return;
        
        this.tvModeEnabled = false;
        
        // Remover classe CSS
        const container = document.querySelector('.dashboard-resumido-container');
        if (container) {
            container.classList.remove('tv-fullscreen-mode');
        }
        
        // Remover botão de saída
        if (this.tvExitButton) {
            this.tvExitButton.remove();
            this.tvExitButton = null;
        }
        
        // Sair do fullscreen
        if (document.exitFullscreen && document.fullscreenElement) {
            document.exitFullscreen().catch(err => {
                console.log('Erro ao sair do fullscreen:', err);
            });
        }
        
        // Retomar auto page loop
        this.resumeAutoPageLoop();
        
        // Atualizar botão
        this.updateTVModeButton();
        
        console.log('Modo TV desativado');
    }
    
    createTVExitButton() {
        // Criar botão de saída do modo TV
        this.tvExitButton = document.createElement('button');
        this.tvExitButton.className = 'tv-exit-button';
        this.tvExitButton.innerHTML = '<i class="mdi mdi-fullscreen-exit"></i> Sair do Modo TV';
        
        // Event listener para sair do modo TV
        this.tvExitButton.addEventListener('click', () => {
            this.exitTVMode();
        });
        
        // Adicionar ao body
        document.body.appendChild(this.tvExitButton);
        
        // Auto-hide após 5 segundos
        setTimeout(() => {
            if (this.tvExitButton) {
                this.tvExitButton.style.opacity = '0.3';
            }
        }, 5000);
        
        // Mostrar novamente ao mover o mouse
        document.addEventListener('mousemove', () => {
            if (this.tvExitButton) {
                this.tvExitButton.style.opacity = '1';
            }
        });
    }
    
    updateTVModeButton() {
        const button = document.getElementById('btn-fullscreen-tv');
        const icon = button?.querySelector('i');
        
        if (button && icon) {
            if (this.tvModeEnabled) {
                button.textContent = '';
                button.appendChild(icon);
                button.appendChild(document.createTextNode(' Sair do Modo TV'));
                icon.className = 'mdi mdi-fullscreen-exit';
                button.className = 'btn btn-warning';
            } else {
                button.textContent = '';
                button.appendChild(icon);
                button.appendChild(document.createTextNode(' Modo TV'));
                icon.className = 'mdi mdi-fullscreen';
                button.className = 'btn btn-secondary';
            }
        }
    }
    
    // Adicionar handler para tecla ESC sair do modo TV
    handleKeyPress(event) {
        if (event.key === 'Escape' && this.tvModeEnabled) {
            this.exitTVMode();
        }
    }

    // Load companies for filter
    async loadCompanies() {
        try {
            const companyList = document.getElementById('company-list');
            if (!companyList) return;

            // Show loading state
            companyList.innerHTML = '<div class="loading-text">Carregando empresas...</div>';

            const response = await fetch('/dash-importacoes-resumido/api/companies');
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            if (data.success) {
                console.log('Empresas carregadas:', data.empresas.length);
                this.renderCompanyList(data.empresas);
            } else {
                throw new Error(data.error || 'Erro ao carregar empresas');
            }

        } catch (error) {
            console.error('Erro ao carregar empresas:', error);
            const companyList = document.getElementById('company-list');
            if (companyList) {
                companyList.innerHTML = '<div class="loading-text">Erro ao carregar empresas</div>';
            }
        }
    }
    
    renderCompanyList(empresas) {
        const companyList = document.getElementById('company-list');
        if (!companyList) return;
        
        if (!empresas || empresas.length === 0) {
            companyList.innerHTML = '<div class="loading-text">Nenhuma empresa encontrada</div>';
            return;
        }
        
        companyList.innerHTML = '';
        
        empresas.forEach(empresa => {
            const item = document.createElement('div');
            item.className = 'company-item';
            item.dataset.cnpj = empresa.cnpj;
            item.dataset.nome = empresa.nome.toLowerCase();
            
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.id = `company-${empresa.cnpj}`;
            checkbox.value = empresa.cnpj;
            checkbox.checked = this.settings.selectedCompanies.includes(empresa.cnpj);
            
            const label = document.createElement('label');
            label.htmlFor = `company-${empresa.cnpj}`;
            
            // Versão compacta: nome truncado + CNPJ na mesma linha
            const nomeCompacto = empresa.nome.length > 25 ? 
                empresa.nome.substring(0, 25) + '...' : 
                empresa.nome;
            
            label.innerHTML = `
                <span class="company-name" title="${empresa.nome}">${nomeCompacto}</span>
                <span class="company-cnpj">${empresa.cnpj}</span>
            `;
            
            // Event listener para checkbox
            checkbox.addEventListener('change', (e) => {
                if (e.target.checked) {
                    if (!this.settings.selectedCompanies.includes(empresa.cnpj)) {
                        this.settings.selectedCompanies.push(empresa.cnpj);
                    }
                } else {
                    this.settings.selectedCompanies = this.settings.selectedCompanies.filter(cnpj => cnpj !== empresa.cnpj);
                }
                this.saveSettings();
                console.log('[DASHBOARD] Empresas selecionadas:', this.settings.selectedCompanies);
            });
            
            item.appendChild(checkbox);
            item.appendChild(label);
            companyList.appendChild(item);
        });
    }
    
    filterCompanyList(searchTerm) {
        const companyList = document.getElementById('company-list');
        if (!companyList) return;
        
        const items = companyList.querySelectorAll('.company-item');
        const term = searchTerm.toLowerCase();
        
        items.forEach(item => {
            const nome = item.dataset.nome || '';
            const cnpj = item.dataset.cnpj || '';
            
            if (nome.includes(term) || cnpj.includes(term)) {
                item.style.display = 'flex';
            } else {
                item.style.display = 'none';
            }
        });
    }
    
    selectAllCompanies() {
        const companyList = document.getElementById('company-list');
        if (!companyList) return;
        
        const checkboxes = companyList.querySelectorAll('input[type="checkbox"]:not(:disabled)');
        const visibleCheckboxes = Array.from(checkboxes).filter(cb => cb.closest('.company-item').offsetParent !== null);
        
        visibleCheckboxes.forEach(checkbox => {
            if (!checkbox.checked) {
                checkbox.checked = true;
                if (!this.settings.selectedCompanies.includes(checkbox.value)) {
                    this.settings.selectedCompanies.push(checkbox.value);
                }
            }
        });
        
        this.saveSettings();
        console.log('[DASHBOARD] Todas as empresas visíveis selecionadas:', this.settings.selectedCompanies);
    }
    
    clearCompanySelection() {
        const companyList = document.getElementById('company-list');
        if (!companyList) return;
        
        const checkboxes = companyList.querySelectorAll('input[type="checkbox"]');
        checkboxes.forEach(checkbox => {
            checkbox.checked = false;
        });
        
        const companyToggle = document.getElementById('company-filter-enabled');
        if (companyToggle) companyToggle.checked = false;
        
        const companySearch = document.getElementById('company-search');
        if (companySearch) companySearch.value = '';
        
        this.settings.companyFilterEnabled = false;
        this.settings.selectedCompanies = [];
        this.saveSettings();
        
        // Mostrar todas as empresas novamente
        this.filterCompanyList('');
        
        console.log('[DASHBOARD] Seleção de empresas limpa');
    }
    
    applyAllFilters() {
        console.log('[DASHBOARD] Aplicando todos os filtros...');
        console.log('[DASHBOARD] Configurações atuais:', {
            companyFilterEnabled: this.settings.companyFilterEnabled,
            selectedCompanies: this.settings.selectedCompanies,
            otherSettings: {
                autoLoop: this.settings.autoLoop,
                autoRefresh: this.settings.autoRefresh
            }
        });
        
        this.currentPage = 1;
        this.loadData();
    }
}

// Inicializar quando o DOM estiver carregado
document.addEventListener('DOMContentLoaded', () => {
    // Check if user has company warning - if so, don't initialize dashboard
    if (window.showCompanyWarning) {
        console.log('[DASH_RESUMIDO] Dashboard bloqueado - usuário sem empresas vinculadas');
        return; // Exit early, don't initialize any dashboard functionality
    }
    
    window.dashboardImportacoes = new DashboardImportacoesResumido();
});

// Limpar ao sair da página
window.addEventListener('beforeunload', () => {
    if (window.dashboardImportacoes) {
        window.dashboardImportacoes.destroy();
    }
});
