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
            tvMode: false
        };
        
        // TV Mode state
        this.tvModeEnabled = false;
        this.tvExitButton = null;
        
        this.init();
    }
    
    init() {
        this.loadSettings();
        this.bindEvents();
        this.loadData();
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

        // Apply filters
        document.getElementById('btn-apply-filter')?.addEventListener('click', () => {
            this.currentPage = 1;
            this.loadData();
        });

        // Cancel/Close settings
        document.getElementById('btn-cancel-settings')?.addEventListener('click', () => {
            this.closeSettingsModal();
        });
    }
    
    openSettingsModal() {
        this.updateSettingsForm();
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
        
        if (autoLoopToggle) autoLoopToggle.checked = this.settings.autoLoop;
        if (autoRefreshToggle) autoRefreshToggle.checked = this.settings.autoRefresh;
        if (loopIntervalInput) loopIntervalInput.value = this.settings.loopInterval;
        if (refreshIntervalInput) refreshIntervalInput.value = this.settings.refreshInterval;
        if (compactModeToggle) compactModeToggle.checked = this.settings.compactMode;
        if (animationsToggle) animationsToggle.checked = this.settings.animationsEnabled;
        if (filterToggle) filterToggle.checked = this.settings.showFilters;
        if (recordsPerPageSelect) recordsPerPageSelect.value = this.settings.pagination;
        
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
            
            const response = await fetch(`/dash-importacoes-resumido/api/data?${params}`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                this.updateHeader(data.header);
                this.updateTable(data.data);
                this.updatePagination(data.pagination);
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
                        <td colspan="10" style="text-align: center; padding: 2rem; color: #6b7280;">
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
                
                tr.innerHTML = `
                    <td>
                        <img src="${modalImage}" alt="Modal ${row.modal}" class="modal-icon">
                    </td>
                    <td>${row.numero || ''}</td>
                    <td>${row.numero_di || ''}</td>
                    <td>${row.ref_unique || ''}</td>
                    <td>${row.ref_importador || ''}</td>
                    <td>${dataEmbarqueFormatted}</td>
                    <td>${dataChegadaFormatted}</td>
                    <td>${row.data_registro || ''}</td>
                    <td>
                        ${row.canal ? `<div class="canal-indicator" style="background-color: ${row.canal_color || '#9E9E9E'}"></div>` : ''}
                    </td>
                    <td>${row.data_entrega || ''}</td>
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
            const diffTime = dataChegada.getTime() - hoje.getTime();
            const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
            
            // Se a data de chegada é nos próximos 7 dias, adicionar bandeirinha
            if (diffDays >= 0 && diffDays <= 7) {
                return `<div class="data-chegada-proxima">
                    <i class="mdi mdi-flag flag-icon"></i>
                    ${dataStr}
                </div>`;
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
        const modalImages = {
            '1': '/static/medias/ship_color.png',      // Marítimo
            '4': '/static/medias/plane_color.png',     // Aéreo
            '7': '/static/medias/truck_color.png'      // Terrestre
        };
        
        return modalImages[modal] || '/static/medias/ship_color.png';
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
}

// Inicializar quando o DOM estiver carregado
document.addEventListener('DOMContentLoaded', () => {
    window.dashboardImportacoes = new DashboardImportacoesResumido();
});

// Limpar ao sair da página
window.addEventListener('beforeunload', () => {
    if (window.dashboardImportacoes) {
        window.dashboardImportacoes.destroy();
    }
});
