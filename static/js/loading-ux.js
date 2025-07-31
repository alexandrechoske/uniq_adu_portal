/**
 * Loading UX Manager - Melhoria da experiência de carregamento
 * Sistema inteligente de loading que melhora a UX das páginas
 */

class LoadingUXManager {
    constructor(options = {}) {
        this.options = {
            showSkeletonTime: 800,    // Tempo para mostrar skeleton
            minLoadingTime: 1200,     // Tempo mínimo de loading
            fadeOutDuration: 300,     // Duração do fade out
            enableSkeleton: true,     // Habilitar skeleton loading
            enableProgressBar: true,  // Habilitar barra de progresso
            debug: true,
            ...options
        };
        
        this.isLoading = false;
        this.loadingStartTime = null;
        this.currentPage = this.detectPage();
        
        this.log('[LOADING_UX] Inicializado para página:', this.currentPage);
        this.init();
    }
    
    log(message, ...args) {
        if (this.options.debug) {
            console.log(message, ...args);
        }
    }
    
    detectPage() {
        const path = window.location.pathname;
        if (path.includes('/dashboard-executivo')) return 'dashboard_executivo';
        if (path.includes('/analytics')) return 'analytics';
        if (path.includes('/materiais')) return 'materiais';
        return 'unknown';
    }
    
    init() {
        this.createLoadingElements();
        this.setupPageSpecificLoading();
        this.interceptNavigationLoading();
    }
    
    createLoadingElements() {
        // Criar overlay de loading melhorado
        if (!document.getElementById('ux-loading-overlay')) {
            const overlay = document.createElement('div');
            overlay.id = 'ux-loading-overlay';
            overlay.className = 'ux-loading-overlay';
            overlay.innerHTML = `
                <div class="ux-loading-content">
                    <div class="ux-loading-logo">
                        <i class="mdi mdi-chart-box"></i>
                    </div>
                    <div class="ux-loading-spinner"></div>
                    <div class="ux-loading-text">Carregando dados...</div>
                    ${this.options.enableProgressBar ? '<div class="ux-progress-bar"><div class="ux-progress-fill"></div></div>' : ''}
                </div>
            `;
            document.body.appendChild(overlay);
        }
        
        // Criar skeleton loaders
        if (this.options.enableSkeleton) {
            this.createSkeletonLoaders();
        }
    }
    
    createSkeletonLoaders() {
        const skeletonHTML = {
            dashboard_executivo: this.createDashboardSkeleton(),
            analytics: this.createAnalyticsSkeleton(),
            materiais: this.createMateriaisSkeleton()
        };
        
        if (skeletonHTML[this.currentPage]) {
            const skeleton = document.createElement('div');
            skeleton.id = 'ux-skeleton-loader';
            skeleton.className = 'ux-skeleton-container';
            skeleton.innerHTML = skeletonHTML[this.currentPage];
            skeleton.style.display = 'none';
            
            // Inserir após o container principal
            const mainContainer = document.querySelector('.dashboard-container, .analytics-container, .materiais-container') || document.body;
            mainContainer.appendChild(skeleton);
        }
    }
    
    createDashboardSkeleton() {
        return `
            <div class="ux-skeleton-kpis">
                ${Array(12).fill().map(() => `
                    <div class="ux-skeleton-kpi">
                        <div class="ux-skeleton-line ux-skeleton-title"></div>
                        <div class="ux-skeleton-line ux-skeleton-value"></div>
                        <div class="ux-skeleton-line ux-skeleton-subtitle"></div>
                    </div>
                `).join('')}
            </div>
            <div class="ux-skeleton-charts">
                ${Array(5).fill().map(() => `
                    <div class="ux-skeleton-chart">
                        <div class="ux-skeleton-line ux-skeleton-chart-title"></div>
                        <div class="ux-skeleton-chart-area"></div>
                    </div>
                `).join('')}
            </div>
            <div class="ux-skeleton-table">
                <div class="ux-skeleton-line ux-skeleton-table-title"></div>
                ${Array(8).fill().map(() => `
                    <div class="ux-skeleton-table-row">
                        ${Array(6).fill().map(() => '<div class="ux-skeleton-line ux-skeleton-cell"></div>').join('')}
                    </div>
                `).join('')}
            </div>
        `;
    }
    
    createAnalyticsSkeleton() {
        return `
            <div class="ux-skeleton-kpis">
                ${Array(5).fill().map(() => `
                    <div class="ux-skeleton-kpi">
                        <div class="ux-skeleton-line ux-skeleton-title"></div>
                        <div class="ux-skeleton-line ux-skeleton-value"></div>
                        <div class="ux-skeleton-line ux-skeleton-subtitle"></div>
                    </div>
                `).join('')}
            </div>
            <div class="ux-skeleton-charts">
                <div class="ux-skeleton-chart ux-skeleton-chart-full">
                    <div class="ux-skeleton-line ux-skeleton-chart-title"></div>
                    <div class="ux-skeleton-chart-area"></div>
                </div>
                ${Array(3).fill().map(() => `
                    <div class="ux-skeleton-chart">
                        <div class="ux-skeleton-line ux-skeleton-chart-title"></div>
                        <div class="ux-skeleton-chart-area"></div>
                    </div>
                `).join('')}
            </div>
        `;
    }
    
    createMateriaisSkeleton() {
        return `
            <div class="ux-skeleton-filters">
                <div class="ux-skeleton-line ux-skeleton-filter"></div>
                <div class="ux-skeleton-line ux-skeleton-filter"></div>
                <div class="ux-skeleton-line ux-skeleton-filter"></div>
            </div>
            <div class="ux-skeleton-table">
                ${Array(15).fill().map(() => `
                    <div class="ux-skeleton-table-row">
                        ${Array(8).fill().map(() => '<div class="ux-skeleton-line ux-skeleton-cell"></div>').join('')}
                    </div>
                `).join('')}
            </div>
        `;
    }
    
    setupPageSpecificLoading() {
        // Interceptar carregamento específico de cada página
        switch (this.currentPage) {
            case 'dashboard_executivo':
                this.setupDashboardLoading();
                break;
            case 'analytics':
                this.setupAnalyticsLoading();
                break;
            case 'materiais':
                this.setupMateriaisLoading();
                break;
        }
    }
    
    setupDashboardLoading() {
        // Interceptar loadInitialData
        if (window.loadInitialData) {
            const originalLoadInitialData = window.loadInitialData;
            window.loadInitialData = async (...args) => {
                this.startLoading('Carregando dashboard...');
                try {
                    const result = await originalLoadInitialData.apply(this, args);
                    this.finishLoading();
                    return result;
                } catch (error) {
                    this.finishLoading();
                    throw error;
                }
            };
        }
    }
    
    setupAnalyticsLoading() {
        // Interceptar loadAnalyticsStats
        if (window.analyticsModule && window.analyticsModule.loadStats) {
            const originalLoadStats = window.analyticsModule.loadStats;
            window.analyticsModule.loadStats = async (...args) => {
                this.startLoading('Carregando analytics...');
                try {
                    const result = await originalLoadStats.apply(this, args);
                    this.finishLoading();
                    return result;
                } catch (error) {
                    this.finishLoading();
                    throw error;
                }
            };
        }
    }
    
    setupMateriaisLoading() {
        // Interceptar funções de carregamento de materiais
        // Será implementado quando necessário
    }
    
    interceptNavigationLoading() {
        // Interceptar cliques em links de navegação
        document.addEventListener('click', (e) => {
            const link = e.target.closest('a[href]');
            if (link && this.isInternalLink(link.href)) {
                this.startLoading('Navegando...');
            }
        });
    }
    
    isInternalLink(href) {
        return href.startsWith(window.location.origin) || href.startsWith('/');
    }
    
    startLoading(message = 'Carregando...', showSkeleton = true) {
        if (this.isLoading) return;
        
        this.isLoading = true;
        this.loadingStartTime = Date.now();
        
        this.log('[LOADING_UX] Iniciando loading:', message);
        
        const overlay = document.getElementById('ux-loading-overlay');
        const skeleton = document.getElementById('ux-skeleton-loader');
        
        if (overlay) {
            overlay.querySelector('.ux-loading-text').textContent = message;
            overlay.style.display = 'flex';
            
            // Animar entrada
            requestAnimationFrame(() => {
                overlay.style.opacity = '1';
            });
            
            // Animar barra de progresso
            if (this.options.enableProgressBar) {
                this.animateProgressBar();
            }
        }
        
        // Mostrar skeleton após um delay
        if (showSkeleton && skeleton && this.options.enableSkeleton) {
            setTimeout(() => {
                if (this.isLoading) {
                    skeleton.style.display = 'block';
                    overlay.style.display = 'none';
                }
            }, this.options.showSkeletonTime);
        }
    }
    
    animateProgressBar() {
        const progressBar = document.querySelector('.ux-progress-fill');
        if (!progressBar) return;
        
        let progress = 0;
        const interval = setInterval(() => {
            if (!this.isLoading) {
                clearInterval(interval);
                return;
            }
            
            progress += Math.random() * 15;
            if (progress > 90) progress = 90;
            
            progressBar.style.width = progress + '%';
        }, 200);
    }
    
    async finishLoading() {
        if (!this.isLoading) return;
        
        const loadingTime = Date.now() - this.loadingStartTime;
        const remainingTime = Math.max(0, this.options.minLoadingTime - loadingTime);
        
        this.log('[LOADING_UX] Finalizando loading após', loadingTime + remainingTime, 'ms');
        
        // Aguardar tempo mínimo se necessário
        if (remainingTime > 0) {
            await new Promise(resolve => setTimeout(resolve, remainingTime));
        }
        
        // Completar barra de progresso
        const progressBar = document.querySelector('.ux-progress-fill');
        if (progressBar) {
            progressBar.style.width = '100%';
        }
        
        // Fade out
        const overlay = document.getElementById('ux-loading-overlay');
        const skeleton = document.getElementById('ux-skeleton-loader');
        
        if (overlay) {
            overlay.style.opacity = '0';
            setTimeout(() => {
                overlay.style.display = 'none';
                if (progressBar) {
                    progressBar.style.width = '0%';
                }
            }, this.options.fadeOutDuration);
        }
        
        if (skeleton) {
            skeleton.style.opacity = '0';
            setTimeout(() => {
                skeleton.style.display = 'none';
                skeleton.style.opacity = '1';
            }, this.options.fadeOutDuration);
        }
        
        this.isLoading = false;
    }
    
    updateMessage(message) {
        const textElement = document.querySelector('.ux-loading-text');
        if (textElement) {
            textElement.textContent = message;
        }
    }
    
    destroy() {
        const overlay = document.getElementById('ux-loading-overlay');
        const skeleton = document.getElementById('ux-skeleton-loader');
        
        if (overlay) overlay.remove();
        if (skeleton) skeleton.remove();
        
        this.log('[LOADING_UX] Destruído');
    }
}

// CSS para os elementos de loading
const loadingCSS = `
.ux-loading-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(255, 255, 255, 0.95);
    backdrop-filter: blur(4px);
    display: none;
    justify-content: center;
    align-items: center;
    z-index: 10000;
    opacity: 0;
    transition: opacity 0.3s ease;
}

.ux-loading-content {
    text-align: center;
    padding: 2rem;
}

.ux-loading-logo {
    font-size: 3rem;
    color: var(--color-primary, #3498DB);
    margin-bottom: 1rem;
}

.ux-loading-spinner {
    width: 40px;
    height: 40px;
    border: 3px solid #f3f3f3;
    border-top: 3px solid var(--color-primary, #3498DB);
    border-radius: 50%;
    animation: ux-spin 1s linear infinite;
    margin: 0 auto 1rem;
}

.ux-loading-text {
    font-size: 1.1rem;
    color: #6b7280;
    margin-bottom: 1rem;
}

.ux-progress-bar {
    width: 200px;
    height: 4px;
    background: #f3f3f3;
    border-radius: 2px;
    overflow: hidden;
    margin: 0 auto;
}

.ux-progress-fill {
    height: 100%;
    background: var(--color-primary, #3498DB);
    width: 0%;
    transition: width 0.3s ease;
}

@keyframes ux-spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

/* Skeleton Loaders */
.ux-skeleton-container {
    padding: 20px;
    opacity: 1;
    transition: opacity 0.3s ease;
}

.ux-skeleton-line {
    background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
    background-size: 200% 100%;
    animation: ux-skeleton-loading 1.5s infinite;
    border-radius: 4px;
    margin-bottom: 8px;
}

.ux-skeleton-kpis {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem;
    margin-bottom: 2rem;
}

.ux-skeleton-kpi {
    padding: 1.5rem;
    border: 1px solid #f1f5f9;
    border-radius: 0.75rem;
}

.ux-skeleton-title {
    height: 16px;
    width: 60%;
}

.ux-skeleton-value {
    height: 24px;
    width: 40%;
    margin: 8px 0;
}

.ux-skeleton-subtitle {
    height: 12px;
    width: 80%;
}

.ux-skeleton-charts {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 1.5rem;
    margin-bottom: 2rem;
}

.ux-skeleton-chart {
    border: 1px solid #f1f5f9;
    border-radius: 0.75rem;
    padding: 1.5rem;
}

.ux-skeleton-chart-full {
    grid-column: 1 / -1;
}

.ux-skeleton-chart-title {
    height: 20px;
    width: 50%;
    margin-bottom: 1rem;
}

.ux-skeleton-chart-area {
    height: 200px;
    background: linear-gradient(90deg, #f8f8f8 25%, #e8e8e8 50%, #f8f8f8 75%);
    background-size: 200% 100%;
    animation: ux-skeleton-loading 1.5s infinite;
    border-radius: 8px;
}

.ux-skeleton-table {
    border: 1px solid #f1f5f9;
    border-radius: 0.75rem;
    padding: 1.5rem;
}

.ux-skeleton-table-title {
    height: 20px;
    width: 30%;
    margin-bottom: 1rem;
}

.ux-skeleton-table-row {
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: 1rem;
    margin-bottom: 12px;
}

.ux-skeleton-cell {
    height: 16px;
}

.ux-skeleton-filters {
    display: flex;
    gap: 1rem;
    margin-bottom: 2rem;
}

.ux-skeleton-filter {
    height: 40px;
    width: 200px;
}

@keyframes ux-skeleton-loading {
    0% {
        background-position: -200% 0;
    }
    100% {
        background-position: 200% 0;
    }
}

@media (max-width: 768px) {
    .ux-skeleton-kpis {
        grid-template-columns: 1fr;
    }
    
    .ux-skeleton-charts {
        grid-template-columns: 1fr;
    }
    
    .ux-skeleton-table-row {
        grid-template-columns: repeat(3, 1fr);
    }
    
    .ux-skeleton-filters {
        flex-direction: column;
    }
    
    .ux-skeleton-filter {
        width: 100%;
    }
}
`;

// Injetar CSS
if (!document.getElementById('ux-loading-styles')) {
    const style = document.createElement('style');
    style.id = 'ux-loading-styles';
    style.textContent = loadingCSS;
    document.head.appendChild(style);
}

// Instanciar automaticamente
let loadingUXManager = null;

document.addEventListener('DOMContentLoaded', function() {
    loadingUXManager = new LoadingUXManager();
});

// Expor globalmente
window.LoadingUXManager = LoadingUXManager;
window.loadingUXManager = loadingUXManager;
