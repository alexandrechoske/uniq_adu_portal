/**
 * Sistema Unificado de Loading UX
 * Uma única animação fluida do clique até o carregamento completo da página
 */

class UnifiedLoadingManager {
    constructor() {
        this.isTransitioning = false;
        this.currentPage = this.detectPage();
        this.loadingStartTime = null;
        this.minimumLoadingTime = 3500; // Tempo mínimo para suavidade - 3.5s para ser mais consistente
        
        console.log('[UNIFIED_LOADING] Inicializado para:', this.currentPage);
        this.init();
    }
    
    detectPage() {
        const path = window.location.pathname;
        if (path.includes('/dashboard-executivo')) return 'dashboard_executivo';
        if (path.includes('/analytics')) return 'analytics';
        if (path.includes('/materiais')) return 'materiais';
        if (path.includes('/conferencia')) return 'conferencia';
        return 'general';
    }
    
    init() {
        // Limpar qualquer sistema de loading conflitante
        this.cleanupConflictingSystems();
        
        this.createLoadingOverlay();
        this.interceptNavigationLinks();
        
        // Se já estamos numa página que precisa de loading
        if (this.needsLoading()) {
            this.startPageLoading();
        }
    }
    
    cleanupConflictingSystems() {
        // Remover overlays antigos periodicamente
        const cleanupInterval = () => {
            const oldOverlays = document.querySelectorAll('#loading-overlay, .loading-overlay:not(#unified-loading-overlay)');
            if (oldOverlays.length > 0) {
                console.log('[UNIFIED_LOADING] Limpando', oldOverlays.length, 'overlays conflitantes');
                oldOverlays.forEach(overlay => {
                    if (overlay.id !== 'unified-loading-overlay') {
                        overlay.style.display = 'none';
                        overlay.remove();
                    }
                });
            }
        };
        
        // Limpeza inicial
        cleanupInterval();
        
        // Limpeza periódica a cada 500ms durante os primeiros 5 segundos
        let cleanupCount = 0;
        const maxCleanups = 10;
        const intervalId = setInterval(() => {
            cleanupInterval();
            cleanupCount++;
            if (cleanupCount >= maxCleanups) {
                clearInterval(intervalId);
            }
        }, 500);
    }
    
    createLoadingOverlay() {
        // Remover TODOS os overlays antigos
        const existingOverlays = document.querySelectorAll('#unified-loading-overlay, #loading-overlay, .loading-overlay');
        existingOverlays.forEach(overlay => overlay.remove());
        
        console.log('[UNIFIED_LOADING] Removidos', existingOverlays.length, 'overlays antigos');
        
        const overlay = document.createElement('div');
        overlay.id = 'unified-loading-overlay';
        overlay.className = 'unified-loading-overlay';
        overlay.innerHTML = `
            <div class="unified-loading-content">
                <div class="unified-loading-spinner">
                    <div class="spinner-ring"></div>
                    <div class="spinner-ring"></div>
                    <div class="spinner-ring"></div>
                </div>
                <div class="unified-loading-text">
                    <h3 id="loading-title">Carregando...</h3>
                    <p id="loading-subtitle">Preparando dados</p>
                </div>
                <div class="unified-loading-progress">
                    <div class="progress-bar">
                        <div class="progress-fill" id="progress-fill"></div>
                    </div>
                    <div class="progress-text" id="progress-text">0%</div>
                </div>
                <div class="skeleton-container" id="skeleton-container"></div>
            </div>
        `;
        
        // Adicionar CSS
        if (!document.getElementById('unified-loading-styles')) {
            const style = document.createElement('style');
            style.id = 'unified-loading-styles';
            style.textContent = this.getLoadingCSS();
            document.head.appendChild(style);
        }
        
        document.body.appendChild(overlay);
        overlay.style.display = 'none';
    }
    
    getLoadingCSS() {
        return `
            .unified-loading-overlay {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(255, 255, 255, 0.98);
                backdrop-filter: blur(8px);
                z-index: 9999;
                display: flex;
                align-items: center;
                justify-content: center;
                opacity: 0;
                transition: opacity 0.3s ease;
            }
            
            .unified-loading-overlay.show {
                opacity: 1;
            }
            
            .unified-loading-content {
                text-align: center;
                max-width: 400px;
                padding: 40px;
            }
            
            .unified-loading-spinner {
                position: relative;
                width: 80px;
                height: 80px;
                margin: 0 auto 30px;
            }
            
            .spinner-ring {
                position: absolute;
                border: 3px solid transparent;
                border-top: 3px solid #3498DB;
                border-radius: 50%;
                animation: spin 1.2s linear infinite;
            }
            
            .spinner-ring:nth-child(1) {
                width: 80px;
                height: 80px;
                animation-delay: 0s;
            }
            
            .spinner-ring:nth-child(2) {
                width: 60px;
                height: 60px;
                top: 10px;
                left: 10px;
                animation-delay: -0.4s;
                border-top-color: #2ecc71;
            }
            
            .spinner-ring:nth-child(3) {
                width: 40px;
                height: 40px;
                top: 20px;
                left: 20px;
                animation-delay: -0.8s;
                border-top-color: #e74c3c;
            }
            
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            
            .unified-loading-text h3 {
                color: #2c3e50;
                font-size: 24px;
                font-weight: 600;
                margin: 0 0 8px 0;
            }
            
            .unified-loading-text p {
                color: #7f8c8d;
                font-size: 16px;
                margin: 0 0 30px 0;
            }
            
            .unified-loading-progress {
                margin-bottom: 30px;
            }
            
            .progress-bar {
                width: 100%;
                height: 6px;
                background: #ecf0f1;
                border-radius: 3px;
                overflow: hidden;
                margin-bottom: 10px;
            }
            
            .progress-fill {
                height: 100%;
                background: linear-gradient(90deg, #3498DB, #2ecc71);
                border-radius: 3px;
                width: 0%;
                transition: width 0.3s ease;
            }
            
            .progress-text {
                color: #7f8c8d;
                font-size: 14px;
                font-weight: 500;
            }
            
            .skeleton-container {
                display: none;
                text-align: left;
                margin-top: 20px;
            }
            
            .skeleton-item {
                height: 12px;
                background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
                background-size: 200% 100%;
                animation: skeleton-loading 1.5s infinite;
                margin: 8px 0;
                border-radius: 6px;
            }
            
            @keyframes skeleton-loading {
                0% { background-position: 200% 0; }
                100% { background-position: -200% 0; }
            }
        `;
    }
    
    interceptNavigationLinks() {
        document.addEventListener('click', (e) => {
            const link = e.target.closest('a[href]');
            if (!link) return;
            
            const href = link.getAttribute('href');
            
            // Verificar se é navegação interna que precisa de loading
            if (this.shouldInterceptLink(href)) {
                e.preventDefault();
                this.startNavigationLoading(href, this.getPageType(href));
            }
        });
    }
    
    shouldInterceptLink(href) {
        if (!href || href.startsWith('#') || href.startsWith('http') || href.startsWith('mailto:')) {
            return false;
        }
        
        // Interceptar apenas páginas que sabemos que têm dados para carregar
        return href.includes('/dashboard-executivo') || 
               href.includes('/analytics') || 
               href.includes('/materiais') ||
               href.includes('/conferencia');
    }
    
    getPageType(href) {
        if (href.includes('/dashboard-executivo')) return 'dashboard_executivo';
        if (href.includes('/analytics')) return 'analytics';
        if (href.includes('/materiais')) return 'materiais';
        if (href.includes('/conferencia')) return 'conferencia';
        return 'general';
    }
    
    startNavigationLoading(href, pageType) {
        if (this.isTransitioning) return;
        
        this.isTransitioning = true;
        this.loadingStartTime = Date.now();
        
        console.log('[UNIFIED_LOADING] Iniciando navegação para:', pageType);
        
        this.showLoadingOverlay(pageType);
        this.updateLoadingContent(pageType, 'Navegando...');
        this.animateProgress(0, 20, 800); // Progresso inicial da navegação
        
        // Salvar estado no sessionStorage para continuidade
        sessionStorage.setItem('unifiedLoading', JSON.stringify({
            isNavigating: true,
            targetPage: pageType,
            startTime: this.loadingStartTime,
            currentProgress: 20
        }));
        
        // Navegar após mostrar loading
        setTimeout(() => {
            window.location.href = href;
        }, 100);
    }
    
    startPageLoading() {
        // Verificar se estamos continuando uma navegação
        const navigationState = sessionStorage.getItem('unifiedLoading');
        let isNavigationContinuation = false;
        let currentProgress = 0;
        
        if (navigationState) {
            try {
                const state = JSON.parse(navigationState);
                if (state.isNavigating && state.targetPage === this.currentPage) {
                    isNavigationContinuation = true;
                    this.loadingStartTime = state.startTime;
                    currentProgress = state.currentProgress || 20;
                    console.log('[UNIFIED_LOADING] Continuando navegação de', state.targetPage, 'com progresso', currentProgress);
                }
                // Limpar estado após uso
                sessionStorage.removeItem('unifiedLoading');
            } catch (e) {
                console.warn('[UNIFIED_LOADING] Erro ao ler estado de navegação:', e);
            }
        }
        
        if (this.isTransitioning && !isNavigationContinuation) return;
        
        if (!isNavigationContinuation) {
            this.isTransitioning = true;
            this.loadingStartTime = Date.now();
            console.log('[UNIFIED_LOADING] Iniciando carregamento da página:', this.currentPage);
            this.showLoadingOverlay(this.currentPage);
            currentProgress = 0;
        } else {
            console.log('[UNIFIED_LOADING] Continuando carregamento da página:', this.currentPage);
            // Overlay já deve estar visível da navegação
            if (!document.getElementById('unified-loading-overlay').classList.contains('show')) {
                this.showLoadingOverlay(this.currentPage);
            }
        }
        
        this.updateLoadingContent(this.currentPage, 'Carregando dados...');
        
        // Progressão baseada no estado atual
        if (isNavigationContinuation) {
            // Continuar de onde parou
            this.animateProgress(currentProgress, 50, 1000);
            
            // Próxima fase após 1.5s
            setTimeout(() => {
                this.animateProgress(50, 75, 1500);
            }, 1500);
        } else {
            // Carregamento normal (acesso direto)
            this.animateProgress(0, 40, 1000);
            
            setTimeout(() => {
                this.animateProgress(40, 70, 1500);
            }, 2000);
        }
        
        // Aguardar carregamento dos dados
        this.waitForPageReady();
    }
    
    showLoadingOverlay(pageType) {
        const overlay = document.getElementById('unified-loading-overlay');
        if (overlay) {
            overlay.style.display = 'flex';
            // Force reflow para animação funcionar
            overlay.offsetHeight;
            overlay.classList.add('show');
        }
    }
    
    updateLoadingContent(pageType, subtitle) {
        const titles = {
            dashboard_executivo: 'Dashboard Executivo',
            analytics: 'Analytics',
            materiais: 'Materiais',
            conferencia: 'Conferência',
            general: 'Carregando'
        };
        
        const titleElement = document.getElementById('loading-title');
        const subtitleElement = document.getElementById('loading-subtitle');
        
        if (titleElement) titleElement.textContent = titles[pageType] || 'Carregando';
        if (subtitleElement) subtitleElement.textContent = subtitle;
    }
    
    animateProgress(from, to, duration) {
        const progressFill = document.getElementById('progress-fill');
        const progressText = document.getElementById('progress-text');
        
        if (!progressFill || !progressText) return;
        
        const startTime = Date.now();
        const startValue = from;
        const endValue = to;
        
        const animate = () => {
            const elapsed = Date.now() - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const easeProgress = this.easeOutCubic(progress);
            const currentValue = startValue + (endValue - startValue) * easeProgress;
            
            progressFill.style.width = `${currentValue}%`;
            progressText.textContent = `${Math.round(currentValue)}%`;
            
            if (progress < 1) {
                requestAnimationFrame(animate);
            }
        };
        
        requestAnimationFrame(animate);
    }
    
    easeOutCubic(t) {
        return 1 - Math.pow(1 - t, 3);
    }
    
    waitForPageReady() {
        let checkCount = 0;
        const maxChecks = 120; // 12 segundos máximo
        
        const checkReady = () => {
            checkCount++;
            
            let isReady = false;
            const hasData = this.checkPageHasData();
            
            // Aguardar pelo menos 3 segundos antes de considerar pronto
            const minTimeElapsed = (Date.now() - this.loadingStartTime) >= 3000;
            
            if ((hasData && minTimeElapsed) || checkCount >= maxChecks) {
                isReady = true;
            }
            
            // Log mais detalhado apenas a cada 10 checks para não spam
            if (checkCount % 10 === 0 || isReady) {
                console.log('[UNIFIED_LOADING] Check', checkCount, '- Ready:', isReady, '- Has data:', hasData, '- Min time:', minTimeElapsed);
            }
            
            if (isReady) {
                this.finishLoading();
            } else {
                setTimeout(checkReady, 100);
            }
        };
        
        // Começar verificação após um delay para dar tempo da página carregar
        setTimeout(checkReady, 1500);
    }
    
    checkPageHasData() {
        switch (this.currentPage) {
            case 'dashboard_executivo':
                return this.checkDashboardData();
            case 'analytics':
                return this.checkAnalyticsData();
            case 'materiais':
                return this.checkMateriaisData();
            default:
                return true; // Para páginas gerais, considerar sempre pronto
        }
    }
    
    checkDashboardData() {
        // Verificar se os KPIs carregaram com dados reais
        const kpiCards = document.querySelectorAll('.kpi-card .kpi-value');
        let hasRealKpiData = false;
        
        if (kpiCards.length > 0) {
            hasRealKpiData = Array.from(kpiCards).some(card => {
                const text = card.textContent ? card.textContent.trim() : '';
                return text && text !== '0' && text !== '...' && text !== 'Carregando...' && text !== '';
            });
        }
        
        // Verificar se há charts com canvas renderizados
        const chartCanvases = document.querySelectorAll('.chart-container canvas');
        const hasCharts = chartCanvases.length > 0;
        
        // Verificar se há dados na tabela de operações recentes
        const tableRows = document.querySelectorAll('.enhanced-table tbody tr');
        const hasTableData = tableRows.length > 0;
        
        console.log('[UNIFIED_LOADING] Dashboard check - KPIs:', hasRealKpiData, 'Charts:', hasCharts, 'Table:', hasTableData);
        
        return hasRealKpiData && hasCharts;
    }
    
    checkAnalyticsData() {
        // Verificar se as estatísticas carregaram com dados reais
        const statCards = document.querySelectorAll('.analytics-stats .stat-value, .kpi-card .kpi-value');
        let hasRealStats = false;
        
        if (statCards.length > 0) {
            hasRealStats = Array.from(statCards).some(card => {
                const text = card.textContent ? card.textContent.trim() : '';
                return text && text !== '0' && text !== '...' && text !== 'Carregando...' && text !== '';
            });
        }
        
        // Verificar se há charts com canvas renderizados
        const chartCanvases = document.querySelectorAll('.chart-container canvas, .analytics-chart canvas');
        const hasCharts = chartCanvases.length > 0;
        
        // Verificar se há dados nas tabelas
        const tableRows = document.querySelectorAll('.enhanced-table tbody tr, .analytics-table tbody tr');
        const hasTableData = tableRows.length > 0;
        
        console.log('[UNIFIED_LOADING] Analytics check - Stats:', hasRealStats, 'Charts:', hasCharts, 'Tables:', hasTableData);
        
        return hasRealStats && hasCharts;
    }
    
    checkMateriaisData() {
        // Verificar se a tabela tem dados
        const table = document.querySelector('.enhanced-table tbody');
        const hasTableData = table && table.children.length > 0;
        
        return hasTableData;
    }
    
    finishLoading() {
        console.log('[UNIFIED_LOADING] Finalizando loading...');
        
        this.updateLoadingContent(this.currentPage, 'Concluído!');
        this.animateProgress(70, 100, 300);
        
        // Aguardar tempo mínimo se necessário
        const elapsed = Date.now() - this.loadingStartTime;
        const remainingTime = Math.max(0, this.minimumLoadingTime - elapsed);
        
        setTimeout(() => {
            this.hideLoadingOverlay();
        }, remainingTime + 300); // +300ms para ver o 100%
    }
    
    hideLoadingOverlay() {
        const overlay = document.getElementById('unified-loading-overlay');
        if (overlay) {
            overlay.classList.remove('show');
            setTimeout(() => {
                overlay.style.display = 'none';
                this.isTransitioning = false;
                console.log('[UNIFIED_LOADING] Loading finalizado');
            }, 300);
        }
    }
    
    needsLoading() {
        return ['dashboard_executivo', 'analytics', 'materiais', 'conferencia'].includes(this.currentPage);
    }
}

// Inicializar quando DOM estiver pronto
document.addEventListener('DOMContentLoaded', () => {
    window.unifiedLoadingManager = new UnifiedLoadingManager();
});

// Exportar para uso global
window.UnifiedLoadingManager = UnifiedLoadingManager;
