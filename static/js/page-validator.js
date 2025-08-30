/**
 * Page Validator - Sistema de validação e refresh silencioso
 * Verifica se dados estão carregados corretamente e força refresh quando necessário
 */

class PageValidator {
    constructor(options = {}) {
        this.options = {
            checkInterval: 3000, // 3 segundos
            maxRetries: 3,
            retryDelay: 2000, // 2 segundos
            debug: true,
            ...options
        };
        
        this.retryCount = 0;
        this.isValidating = false;
        this.validationTimer = null;
        this.page = this.detectPage();
        
        this.log('[PAGE_VALIDATOR] Inicializado para página:', this.page);
        this.startValidation();
    }
    
    log(message, ...args) {
        if (this.options.debug) {
            console.log(message, ...args);
        }
    }
    
    detectPage() {
        const path = window.location.pathname;
        
        // Excluir páginas financeiras do PageValidator
        if (path.includes('/financeiro/')) return 'financeiro_skip';
        
        if (path.includes('/dashboard-executivo')) return 'dashboard_executivo';
        if (path.includes('/analytics')) return 'analytics';
        if (path.includes('/materiais')) return 'materiais';
        if (path.includes('/relatorios')) return 'relatorios';
        return 'unknown';
    }
    
    startValidation() {
        // Não iniciar validação para páginas financeiras
        if (this.page === 'financeiro_skip') {
            this.log('[PAGE_VALIDATOR] Página financeira detectada - validação desabilitada');
            return;
        }
        
        // Aguardar um tempo antes de iniciar validação (para permitir carregamento inicial)
        setTimeout(() => {
            this.validatePage();
            
            // Configurar validação periódica
            this.validationTimer = setInterval(() => {
                if (!this.isValidating) {
                    this.validatePage();
                }
            }, this.options.checkInterval);
        }, 5000); // 5 segundos após carregamento da página
    }
    
    stopValidation() {
        if (this.validationTimer) {
            clearInterval(this.validationTimer);
            this.validationTimer = null;
        }
    }
    
    async validatePage() {
        if (this.isValidating || this.retryCount >= this.options.maxRetries) {
            return;
        }
        
        this.isValidating = true;
        
        try {
            const isEmpty = this.checkIfPageIsEmpty();
            
            if (isEmpty) {
                this.log('[PAGE_VALIDATOR] Página detectada como vazia, iniciando refresh silencioso...');
                await this.performSilentRefresh();
            } else {
                this.log('[PAGE_VALIDATOR] Página validada com sucesso');
                this.retryCount = 0; // Reset retry count on success
            }
        } catch (error) {
            this.log('[PAGE_VALIDATOR] Erro durante validação:', error);
        } finally {
            this.isValidating = false;
        }
    }
    
    checkIfPageIsEmpty() {
        switch (this.page) {
            case 'analytics':
                return this.checkAnalyticsEmpty();
            case 'dashboard_executivo':
                return this.checkDashboardEmpty();
            case 'materiais':
                return this.checkMateriaisEmpty();
            default:
                return false;
        }
    }
    
    checkAnalyticsEmpty() {
        // Verificar KPIs
        const kpiElements = [
            'total-access', 'unique-users', 'logins-today', 
            'total-logins', 'avg-session'
        ];
        
        const kpisEmpty = kpiElements.every(id => {
            const element = document.getElementById(id);
            return !element || element.textContent.trim() === '--' || element.textContent.trim() === '0';
        });
        
        // Verificar se charts existem
        const chartsEmpty = !window.analyticsModule || 
                           !window.analyticsModule.charts || 
                           Object.keys(window.analyticsModule.charts).length === 0;
        
        // Verificar se dados estão vazios
        const dataEmpty = !window.analyticsModule ||
                         !window.analyticsModule.analyticsData ||
                         Object.keys(window.analyticsModule.analyticsData).length === 0;
        
        this.log('[PAGE_VALIDATOR] Analytics - KPIs vazios:', kpisEmpty, 
                 'Charts vazios:', chartsEmpty, 'Dados vazios:', dataEmpty);
        
        return kpisEmpty && (chartsEmpty || dataEmpty);
    }
    
    checkDashboardEmpty() {
        // Verificar KPIs do dashboard
        const kpiCards = document.querySelectorAll('.kpi-value');
        const kpisEmpty = Array.from(kpiCards).every(card => {
            const text = card.textContent.trim();
            return text === '--' || text === '0' || text === '';
        });
        
        // Verificar se charts existem
        const chartsEmpty = !window.dashboardCharts || 
                           Object.keys(window.dashboardCharts).length === 0;
        
        // Verificar se há dados na tabela
        const tableEmpty = this.checkTableEmpty('#recent-operations-table');
        
        this.log('[PAGE_VALIDATOR] Dashboard - KPIs vazios:', kpisEmpty, 
                 'Charts vazios:', chartsEmpty, 'Tabela vazia:', tableEmpty);
        
        return kpisEmpty && chartsEmpty && tableEmpty;
    }
    
    checkMateriaisEmpty() {
        // Verificar se há dados na tabela principal
        const tableEmpty = this.checkTableEmpty('#materiais-table');
        
        // Verificar se há filtros carregados
        const filtersEmpty = !document.querySelector('.filter-summary') ||
                            document.querySelector('.filter-summary').textContent.includes('Carregando');
        
        this.log('[PAGE_VALIDATOR] Materiais - Tabela vazia:', tableEmpty, 
                 'Filtros vazios:', filtersEmpty);
        
        return tableEmpty && filtersEmpty;
    }
    
    checkTableEmpty(selector) {
        const table = document.querySelector(selector);
        if (!table) return true;
        
        const tbody = table.querySelector('tbody');
        if (!tbody) return true;
        
        const rows = tbody.querySelectorAll('tr');
        return rows.length === 0 || 
               (rows.length === 1 && rows[0].textContent.includes('Nenhum dado'));
    }
    
    async performSilentRefresh() {
        if (this.retryCount >= this.options.maxRetries) {
            this.log('[PAGE_VALIDATOR] Máximo de tentativas atingido');
            return;
        }
        
        this.retryCount++;
        this.log(`[PAGE_VALIDATOR] Tentativa ${this.retryCount} de refresh silencioso`);
        
        try {
            switch (this.page) {
                case 'analytics':
                    await this.refreshAnalytics();
                    break;
                case 'dashboard_executivo':
                    await this.refreshDashboard();
                    break;
                case 'materiais':
                    await this.refreshMateriais();
                    break;
            }
            
            // Aguardar antes de validar novamente
            setTimeout(() => {
                this.validatePage();
            }, this.options.retryDelay);
            
        } catch (error) {
            this.log('[PAGE_VALIDATOR] Erro durante refresh:', error);
        }
    }
    
    async refreshAnalytics() {
        if (window.analyticsModule && window.analyticsModule.refresh) {
            this.log('[PAGE_VALIDATOR] Executando refresh do Analytics');
            await window.analyticsModule.refresh();
        } else {
            this.log('[PAGE_VALIDATOR] Analytics module não encontrado, recarregando página');
            window.location.reload();
        }
    }
    
    async refreshDashboard() {
        if (window.loadInitialData) {
            this.log('[PAGE_VALIDATOR] Executando refresh do Dashboard');
            await window.loadInitialData();
        } else if (window.dashboardModule && window.dashboardModule.refresh) {
            await window.dashboardModule.refresh();
        } else {
            this.log('[PAGE_VALIDATOR] Dashboard functions não encontradas, recarregando página');
            window.location.reload();
        }
    }
    
    async refreshMateriais() {
        if (window.materiaisModule && window.materiaisModule.refresh) {
            this.log('[PAGE_VALIDATOR] Executando refresh dos Materiais');
            await window.materiaisModule.refresh();
        } else {
            this.log('[PAGE_VALIDATOR] Materiais module não encontrado, recarregando página');
            window.location.reload();
        }
    }
    
    destroy() {
        this.stopValidation();
        this.log('[PAGE_VALIDATOR] Destruído');
    }
}

// Instanciar automaticamente quando a página carregar
let pageValidator = null;

document.addEventListener('DOMContentLoaded', function() {
    // Permitir que páginas específicas desativem o PageValidator
    if (window.DISABLE_PAGE_VALIDATOR === true) {
        console.log('[PAGE_VALIDATOR] Desativado por DISABLE_PAGE_VALIDATOR');
        return;
    }
    // Aguardar um pouco para garantir que outros scripts carregaram
    setTimeout(() => {
        pageValidator = new PageValidator();
    }, 1000);
});

// Limpar ao sair da página
window.addEventListener('beforeunload', function() {
    if (pageValidator) {
        pageValidator.destroy();
    }
});

// Expor globalmente para debug
window.PageValidator = PageValidator;
window.pageValidator = pageValidator;
