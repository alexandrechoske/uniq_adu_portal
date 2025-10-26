/**
 * GALERIA DE NOTÍCIAS COMEX - Carousel Interativo
 * Sistema de notícias rotativo com navegação, autoplay e integração API
 */

class NewsGallery {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error(`Container #${containerId} não encontrado`);
            return;
        }

        // Configurações padrão
        this.config = {
            autoplayInterval: options.autoplayInterval || 8000,
            autoplayEnabled: options.autoplayEnabled !== false,
            transitionDuration: options.transitionDuration || 500,
            apiEndpoint: options.apiEndpoint || '/api/noticias-comex',
            maxNewsDisplay: options.maxNewsDisplay || 10,
            ...options
        };

        // Estado interno
        this.state = {
            currentIndex: 0,
            news: [],
            isLoading: true,
            autoplayTimer: null,
            isAutoplayPaused: false
        };

        // Elementos DOM
        this.elements = {};

        this.init();
    }

    async init() {
        await this.loadNews();
        this.render();
        this.setupEventListeners();
        if (this.config.autoplayEnabled) {
            this.startAutoplay();
        }
    }

    async loadNews() {
        this.state.isLoading = true;
        this.renderLoading();

        try {
            const response = await fetch(this.config.apiEndpoint, {
                headers: this.buildRequestHeaders()
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            // Ordenar notícias por ID em ordem decrescente (mais recentes primeiro)
            const sortedNews = data.noticias.sort((a, b) => parseInt(a.id) - parseInt(b.id));
            this.state.news = sortedNews.slice(0, this.config.maxNewsDisplay);
            this.state.isLoading = false;
            console.log(`✓ ${this.state.news.length} notícias carregadas com sucesso`);
        } catch (error) {
            console.error('Erro ao carregar notícias:', error);
            this.state.isLoading = false;
            this.renderError(error.message);
        }
    }

    buildRequestHeaders() {
        const headers = {};
        const apiKey = this.getApiBypassKey();

        if (apiKey) {
            headers['X-API-Key'] = apiKey;
        }

        return headers;
    }

    getApiBypassKey() {
        if (this.container && this.container.dataset && this.container.dataset.apiBypass) {
            return this.container.dataset.apiBypass;
        }

        if (typeof window !== 'undefined' && window.API_BYPASS_KEY) {
            return window.API_BYPASS_KEY;
        }

        return '';
    }

    render() {
        if (this.state.isLoading) {
            return;
        }

        if (this.state.news.length === 0) {
            this.renderEmpty();
            this.cacheElements();
            return;
        }

        const carousel = this.container.querySelector('.news-carousel');
        if (!carousel) return;

        // Renderizar track de notícias
        let track = carousel.querySelector('.news-carousel-track');
        if (!track) {
            carousel.innerHTML = '<div class="news-carousel-track"></div>';
            track = carousel.querySelector('.news-carousel-track');
        }
        track.innerHTML = this.state.news.map((noticia, index) => 
            this.renderNewsCard(noticia, index)
        ).join('');

        // Renderizar controles
        this.renderControls();

        // Atualizar referências DOM
        this.cacheElements();

        // Atualizar estado inicial
        this.updateCarousel(false);
    }

    renderNewsCard(noticia, index) {
        const hasImage = noticia.imagem_url && noticia.imagem_url.trim() !== '';
        const imageContent = hasImage 
            ? `<img src="${noticia.imagem_url}" alt="${noticia.titulo}" loading="lazy">`
            : `<div class="news-image-placeholder">
                    <i class="mdi mdi-newspaper-variant-outline"></i>
                    <span>COMEX Brasil</span>
               </div>`;

        return `
            <div class="news-card" data-index="${index}">
                <div class="news-card-inner">
                    <div class="news-image">
                        ${imageContent}
                        ${noticia.categoria ? `<span class="news-category">${noticia.categoria}</span>` : ''}
                    </div>
                    <div class="news-content">
                        <div class="news-date">
                            <i class="mdi mdi-clock-outline"></i>
                            <span>${this.formatDate(noticia.data_publicacao)}</span>
                        </div>
                        <h4 class="news-title">${noticia.titulo}</h4>
                        <p class="news-summary">${noticia.resumo}</p>
                        <div class="news-footer">
                            <span class="news-source">${noticia.fonte || 'Portal COMEX'}</span>
                            <a href="${noticia.link}" target="_blank" rel="noopener noreferrer" class="news-read-more">
                                Ler mais <i class="mdi mdi-arrow-right"></i>
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    renderControls() {
        const controls = this.container.querySelector('.news-controls');
        if (!controls) return;

        const indicators = this.state.news.map((_, index) => 
            `<span class="news-indicator ${index === 0 ? 'active' : ''}" data-index="${index}"></span>`
        ).join('');

        controls.innerHTML = `
            <div class="news-nav-buttons">
                <button class="news-nav-btn" id="news-prev-btn" ${this.state.news.length <= 1 ? 'disabled' : ''}>
                    <i class="mdi mdi-chevron-left"></i>
                </button>
                <button class="news-nav-btn" id="news-next-btn" ${this.state.news.length <= 1 ? 'disabled' : ''}>
                    <i class="mdi mdi-chevron-right"></i>
                </button>
            </div>
            <div class="news-indicators">
                ${indicators}
            </div>
            <button class="news-autoplay-toggle ${this.config.autoplayEnabled ? 'active' : ''}" id="news-autoplay-toggle">
                <i class="mdi ${this.config.autoplayEnabled ? 'mdi-pause' : 'mdi-play'}"></i>
            </button>
        `;
    }

    renderLoading() {
        const carousel = this.container.querySelector('.news-carousel');
        if (!carousel) return;

        carousel.innerHTML = `
            <div class="news-loading">
                <i class="mdi mdi-loading"></i>
                <span>Carregando notícias...</span>
            </div>
        `;
    }

    renderError(message) {
        const carousel = this.container.querySelector('.news-carousel');
        if (!carousel) return;

        carousel.innerHTML = `
            <div class="news-error">
                <i class="mdi mdi-alert-circle-outline"></i>
                <p>Não foi possível carregar as notícias<br><small>${message}</small></p>
                <button class="news-retry-btn" id="news-retry-btn">
                    Tentar novamente
                </button>
            </div>
        `;

        // Event listener para retry
        const retryBtn = carousel.querySelector('#news-retry-btn');
        if (retryBtn) {
            retryBtn.addEventListener('click', () => {
                this.loadNews().then(() => this.render());
            });
        }
    }

    renderEmpty() {
        const carousel = this.container.querySelector('.news-carousel');
        if (!carousel) return;

        carousel.innerHTML = `
            <div class="news-error">
                <i class="mdi mdi-information-outline"></i>
                <p>Nenhuma notícia disponível no momento</p>
            </div>
        `;
    }

    cacheElements() {
        this.elements = {
            track: this.container.querySelector('.news-carousel-track'),
            prevBtn: this.container.querySelector('#news-prev-btn'),
            nextBtn: this.container.querySelector('#news-next-btn'),
            autoplayToggle: this.container.querySelector('#news-autoplay-toggle'),
            refreshBtn: this.container.querySelector('#news-refresh-btn'),
            indicators: this.container.querySelectorAll('.news-indicator')
        };
    }

    setupEventListeners() {
        const {
            prevBtn = null,
            nextBtn = null,
            autoplayToggle = null,
            refreshBtn = null,
            indicators = null
        } = this.elements || {};

        const indicatorsList = indicators ? Array.from(indicators) : [];

        // Navegação anterior
        if (prevBtn) {
            prevBtn.addEventListener('click', () => this.prev());
        }

        // Navegação próxima
        if (nextBtn) {
            nextBtn.addEventListener('click', () => this.next());
        }

        // Toggle autoplay
        if (autoplayToggle) {
            autoplayToggle.addEventListener('click', () => this.toggleAutoplay());
        }

        // Refresh manual
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.refresh());
        }

        // Indicadores
        indicatorsList.forEach(indicator => {
            indicator.addEventListener('click', (e) => {
                const index = parseInt(e.target.dataset.index);
                this.goTo(index);
            });
        });

        // ANALYTICS: Tracking de cliques nos links "Ler mais"
        const readMoreLinks = this.container.querySelectorAll('.news-read-more');
        readMoreLinks.forEach((link, index) => {
            link.addEventListener('click', (e) => {
                // Permitir que o link abra normalmente, mas registrar analytics
                const noticia = this.state.news[index];
                if (noticia && window.newsAnalytics) {
                    window.newsAnalytics.trackNewsClick(
                        noticia.id,
                        noticia.titulo,
                        noticia.fonte || 'Portal COMEX'
                    );
                    console.log(`📊 Analytics: Clique registrado na notícia #${noticia.id}`);
                }
            });
        });

        // Pausar autoplay ao passar mouse
        this.container.addEventListener('mouseenter', () => {
            if (this.config.autoplayEnabled && !this.state.isAutoplayPaused) {
                this.pauseAutoplay();
                this.state.isAutoplayPaused = true;
            }
        });

        this.container.addEventListener('mouseleave', () => {
            if (this.config.autoplayEnabled && this.state.isAutoplayPaused) {
                this.startAutoplay();
                this.state.isAutoplayPaused = false;
            }
        });

        // Suporte a keyboard navigation
        document.addEventListener('keydown', (e) => {
            if (!this.container.matches(':hover')) return;

            if (e.key === 'ArrowLeft') {
                this.prev();
            } else if (e.key === 'ArrowRight') {
                this.next();
            }
        });
    }

    updateCarousel(animate = true) {
        const { track, indicators } = this.elements;
        
        if (!track) return;

        // Atualizar posição do track
        const translateX = -this.state.currentIndex * 100;
        track.style.transition = animate ? `transform ${this.config.transitionDuration}ms ease` : 'none';
        track.style.transform = `translateX(${translateX}%)`;

        // Atualizar indicadores
        const indicatorsList = indicators ? Array.from(indicators) : [];
        indicatorsList.forEach((indicator, index) => {
            indicator.classList.toggle('active', index === this.state.currentIndex);
        });

        // Log para debug
        console.log(`Notícia ${this.state.currentIndex + 1} de ${this.state.news.length}`);
    }

    next() {
        if (this.state.news.length <= 1) return;
        
        this.state.currentIndex = (this.state.currentIndex + 1) % this.state.news.length;
        this.updateCarousel();
        this.resetAutoplay();
    }

    prev() {
        if (this.state.news.length <= 1) return;

        this.state.currentIndex = this.state.currentIndex === 0 
            ? this.state.news.length - 1 
            : this.state.currentIndex - 1;
        this.updateCarousel();
        this.resetAutoplay();
    }

    goTo(index) {
        if (index < 0 || index >= this.state.news.length) return;
        
        this.state.currentIndex = index;
        this.updateCarousel();
        this.resetAutoplay();
    }

    startAutoplay() {
        if (this.state.autoplayTimer) {
            clearInterval(this.state.autoplayTimer);
        }

        this.state.autoplayTimer = setInterval(() => {
            this.next();
        }, this.config.autoplayInterval);

        console.log('Autoplay iniciado');
    }

    pauseAutoplay() {
        if (this.state.autoplayTimer) {
            clearInterval(this.state.autoplayTimer);
            this.state.autoplayTimer = null;
        }
    }

    resetAutoplay() {
        if (this.config.autoplayEnabled && !this.state.isAutoplayPaused) {
            this.pauseAutoplay();
            this.startAutoplay();
        }
    }

    toggleAutoplay() {
        this.config.autoplayEnabled = !this.config.autoplayEnabled;
        
        const toggleBtn = this.elements.autoplayToggle;
        if (!toggleBtn) return;
        const icon = toggleBtn.querySelector('i');
        if (!icon) return;
        
        if (this.config.autoplayEnabled) {
            toggleBtn.classList.add('active');
            icon.className = 'mdi mdi-pause';
            this.startAutoplay();
            console.log('Autoplay ativado');
        } else {
            toggleBtn.classList.remove('active');
            icon.className = 'mdi mdi-play';
            this.pauseAutoplay();
            console.log('Autoplay desativado');
        }
    }

    async refresh() {
        console.log('Atualizando notícias...');
        const refreshBtn = this.elements.refreshBtn;
        
        if (refreshBtn) {
            refreshBtn.disabled = true;
            const icon = refreshBtn.querySelector('i');
            icon.style.animation = 'spin 1s linear infinite';
        }

        await this.loadNews();
        this.render();
        this.setupEventListeners();

        if (refreshBtn) {
            refreshBtn.disabled = false;
            const icon = refreshBtn.querySelector('i');
            icon.style.animation = '';
        }

        if (this.config.autoplayEnabled) {
            this.startAutoplay();
        }
    }

    formatDate(dateValue) {
        if (!dateValue) {
            return 'Data indisponível';
        }

        const rawValue = String(dateValue).trim();
        if (!rawValue) {
            return 'Data indisponível';
        }

        const relativeLabel = this.formatRelativeString(rawValue);
        if (relativeLabel) {
            return relativeLabel;
        }

        const parsedDate = this.parseDateString(rawValue);
        if (!parsedDate) {
            return rawValue;
        }

        return this.describeDate(parsedDate);
    }

    formatRelativeString(value) {
        const lower = value.toLowerCase();

        if (lower === 'just now' || lower === 'agora') {
            return 'Agora';
        }

        const englishPattern = value.match(/^(\d+)\s+(minute|minutes|hour|hours|day|days)\s+ago$/i);
        if (englishPattern) {
            const amount = parseInt(englishPattern[1], 10);
            const unitMap = {
                minute: 'minuto',
                minutes: 'minuto',
                hour: 'hora',
                hours: 'hora',
                day: 'dia',
                days: 'dia'
            };
            const baseUnit = unitMap[englishPattern[2].toLowerCase()] || 'dia';
            return `Há ${amount} ${this.pluralizeUnit(baseUnit, amount)}`;
        }

        const portuguesePattern = value.match(/^(?:há\s*)?(\d+)\s+(minuto|minutos|hora|horas|dia|dias)(?:\s*atrás)?$/i);
        if (portuguesePattern) {
            const amount = parseInt(portuguesePattern[1], 10);
            const baseUnit = this.normalizeUnit(portuguesePattern[2]);
            return `Há ${amount} ${this.pluralizeUnit(baseUnit, amount)}`;
        }

        return null;
    }

    parseDateString(value) {
        const brPattern = value.match(/^(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{2,4})(?:\s*(?:\||-)?\s*(\d{1,2}):(\d{2}))?$/);
        if (brPattern) {
            const day = parseInt(brPattern[1], 10);
            const month = parseInt(brPattern[2], 10) - 1;
            let year = brPattern[3];
            year = year.length === 2 ? parseInt(`20${year}`, 10) : parseInt(year, 10);
            const hours = brPattern[4] ? parseInt(brPattern[4], 10) : 0;
            const minutes = brPattern[5] ? parseInt(brPattern[5], 10) : 0;

            return new Date(year, month, day, hours, minutes);
        }

        const normalizedISO = value.includes('T') ? value : value.replace(' ', 'T');
        const timestamp = Date.parse(normalizedISO);
        if (!Number.isNaN(timestamp)) {
            return new Date(timestamp);
        }

        return null;
    }

    describeDate(date) {
        if (!(date instanceof Date) || Number.isNaN(date.getTime())) {
            return 'Data indisponível';
        }

        const now = new Date();
        let diffMs = now.getTime() - date.getTime();
        const isFuture = diffMs < 0;
        diffMs = Math.abs(diffMs);

        const diffMinutes = Math.floor(diffMs / 60000);
        if (diffMinutes < 1) {
            return isFuture ? 'Em instantes' : 'Agora';
        }

        if (diffMinutes < 60) {
            const amount = Math.max(diffMinutes, 1);
            const unit = this.pluralizeUnit('minuto', amount);
            return isFuture ? `Em ${amount} ${unit}` : `Há ${amount} ${unit}`;
        }

        const diffHours = Math.floor(diffMinutes / 60);
        if (diffHours < 24) {
            const unit = this.pluralizeUnit('hora', diffHours);
            return isFuture ? `Em ${diffHours} ${unit}` : `Há ${diffHours} ${unit}`;
        }

        const diffDays = Math.floor(diffHours / 24);
        const timeLabel = date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });

        if (!isFuture && diffDays === 1) {
            return `Ontem, ${timeLabel}`;
        }

        if (isFuture && diffDays === 1) {
            return `Amanhã, ${timeLabel}`;
        }

        if (diffDays < 7) {
            const unit = this.pluralizeUnit('dia', diffDays);
            return isFuture ? `Em ${diffDays} ${unit}` : `Há ${diffDays} ${unit}`;
        }

        return date.toLocaleDateString('pt-BR', {
            day: '2-digit',
            month: 'short',
            year: 'numeric'
        });
    }

    pluralizeUnit(unit, amount) {
        const base = unit.toLowerCase();

        if (base === 'minuto') {
            return amount === 1 ? 'minuto' : 'minutos';
        }

        if (base === 'hora') {
            return amount === 1 ? 'hora' : 'horas';
        }

        if (base === 'dia') {
            return amount === 1 ? 'dia' : 'dias';
        }

        return unit;
    }

    normalizeUnit(unit) {
        const lower = unit.toLowerCase();

        if (lower.startsWith('minuto')) {
            return 'minuto';
        }

        if (lower.startsWith('hora')) {
            return 'hora';
        }

        if (lower.startsWith('dia')) {
            return 'dia';
        }

        return unit;
    }

    destroy() {
        this.pauseAutoplay();
        this.container.innerHTML = '';
        console.log('Galeria de notícias destruída');
    }
}

// Inicialização automática quando DOM estiver pronto
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initNewsGallery);
} else {
    initNewsGallery();
}

function initNewsGallery() {
    const newsContainer = document.getElementById('news-gallery-container');
    if (newsContainer) {
        window.newsGallery = new NewsGallery('news-gallery-container', {
            autoplayInterval: 8000,
            autoplayEnabled: true,
            apiEndpoint: '/api/noticias-comex'
        });
        console.log('✓ Galeria de Notícias COMEX inicializada');
    }

    // Inicializar indicadores COMEX
    const indicatorsContainer = document.getElementById('comex-indicators-container');
    if (indicatorsContainer) {
        loadComexIndicators(indicatorsContainer);
    }
}

async function loadComexIndicators(container) {
    try {
        const apiBypass = container.closest('.news-gallery-container')?.dataset?.apiBypass || 
                         document.getElementById('news-gallery-container')?.dataset?.apiBypass || '';
        
        const headers = {};
        if (apiBypass) {
            headers['X-API-Key'] = apiBypass;
        }

        const response = await fetch('/api/comex-indicators', { headers });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();
        
        if (data.success && data.indicators) {
            renderComexIndicators(container, data.indicators);
        }
    } catch (error) {
        console.error('Erro ao carregar indicadores COMEX:', error);
        container.innerHTML = '<p style="color: #6B7280; font-size: 0.875rem; padding: 0.5rem;">Indicadores indisponíveis</p>';
    }
}

function renderComexIndicators(container, indicators) {
    const chips = [];

    // Dólar (apenas símbolo)
    if (indicators.dolar_venda) {
        chips.push(`
            <div class="comex-chip currency">
                <i class="mdi mdi-currency-usd"></i>
                <span class="comex-chip-value">R$ ${indicators.dolar_venda}</span>
            </div>
        `);
    }

    // Euro (apenas símbolo)
    if (indicators.euro_venda) {
        chips.push(`
            <div class="comex-chip currency">
                <i class="mdi mdi-currency-eur"></i>
                <span class="comex-chip-value">R$ ${indicators.euro_venda}</span>
            </div>
        `);
    }

    // Selic
    if (indicators.selic_meta) {
        chips.push(`
            <div class="comex-chip rate">
                <i class="mdi mdi-percent"></i>
                <span class="comex-chip-value">Selic ${indicators.selic_meta}%</span>
            </div>
        `);
    }

    // IPCA 12 meses
    if (indicators.ipca_12_meses) {
        chips.push(`
            <div class="comex-chip rate">
                <i class="mdi mdi-chart-line"></i>
                <span class="comex-chip-value">IPCA ${indicators.ipca_12_meses}%</span>
            </div>
        `);
    }

    // Exportações com tooltip
    if (indicators.expo_bi) {
        const expoValue = indicators.expo_bi.replace(' Exportações', '').trim();
        chips.push(`
            <div class="comex-chip trade">
                <i class="mdi mdi-arrow-up-bold"></i>
                <span class="comex-chip-value">US$ ${expoValue} Bi</span>
                <div class="comex-chip-tooltip">
                    <div class="comex-chip-tooltip-title">Comércio Exterior - Set/2025</div>
                    <div class="comex-chip-tooltip-row">
                        <span class="comex-chip-tooltip-label">Exportações:</span>
                        <span class="comex-chip-tooltip-value">US$ ${expoValue} Bi</span>
                    </div>
                    ${indicators.impo_bi ? `
                    <div class="comex-chip-tooltip-row">
                        <span class="comex-chip-tooltip-label">Importações:</span>
                        <span class="comex-chip-tooltip-value">US$ ${indicators.impo_bi.replace(' Importações', '').trim()} Bi</span>
                    </div>
                    ` : ''}
                    ${indicators.saldo_comex ? `
                    <div class="comex-chip-tooltip-row">
                        <span class="comex-chip-tooltip-label">Saldo Comercial:</span>
                        <span class="comex-chip-tooltip-value">${indicators.saldo_comex}</span>
                    </div>
                    ` : ''}
                    <div class="comex-chip-tooltip-footer">Valores FOB em US$ bilhões</div>
                </div>
            </div>
        `);
    }

    // Importações com tooltip
    if (indicators.impo_bi) {
        const impoValue = indicators.impo_bi.replace(' Importações', '').trim();
        chips.push(`
            <div class="comex-chip trade">
                <i class="mdi mdi-arrow-down-bold"></i>
                <span class="comex-chip-value">US$ ${impoValue} Bi</span>
                <div class="comex-chip-tooltip">
                    <div class="comex-chip-tooltip-title">Comércio Exterior - Set/2025</div>
                    ${indicators.expo_bi ? `
                    <div class="comex-chip-tooltip-row">
                        <span class="comex-chip-tooltip-label">Exportações:</span>
                        <span class="comex-chip-tooltip-value">US$ ${indicators.expo_bi.replace(' Exportações', '').trim()} Bi</span>
                    </div>
                    ` : ''}
                    <div class="comex-chip-tooltip-row">
                        <span class="comex-chip-tooltip-label">Importações:</span>
                        <span class="comex-chip-tooltip-value">US$ ${impoValue} Bi</span>
                    </div>
                    ${indicators.saldo_comex ? `
                    <div class="comex-chip-tooltip-row">
                        <span class="comex-chip-tooltip-label">Saldo Comercial:</span>
                        <span class="comex-chip-tooltip-value">${indicators.saldo_comex}</span>
                    </div>
                    ` : ''}
                    <div class="comex-chip-tooltip-footer">Valores FOB em US$ bilhões</div>
                </div>
            </div>
        `);
    }

    // Saldo Comercial com tooltip
    if (indicators.saldo_comex) {
        const isPositive = indicators.saldo_comex.includes('+');
        const saldoValue = indicators.saldo_comex.replace('Saldo Comercial', '').trim();
        chips.push(`
            <div class="comex-chip trade ${isPositive ? 'positive' : 'negative'}">
                <i class="mdi mdi-scale-balance"></i>
                <span class="comex-chip-value">${saldoValue}</span>
                <div class="comex-chip-tooltip">
                    <div class="comex-chip-tooltip-title">Comércio Exterior - Set/2025</div>
                    ${indicators.expo_bi ? `
                    <div class="comex-chip-tooltip-row">
                        <span class="comex-chip-tooltip-label">Exportações:</span>
                        <span class="comex-chip-tooltip-value">US$ ${indicators.expo_bi.replace(' Exportações', '').trim()} Bi</span>
                    </div>
                    ` : ''}
                    ${indicators.impo_bi ? `
                    <div class="comex-chip-tooltip-row">
                        <span class="comex-chip-tooltip-label">Importações:</span>
                        <span class="comex-chip-tooltip-value">US$ ${indicators.impo_bi.replace(' Importações', '').trim()} Bi</span>
                    </div>
                    ` : ''}
                    <div class="comex-chip-tooltip-row">
                        <span class="comex-chip-tooltip-label">Saldo Comercial:</span>
                        <span class="comex-chip-tooltip-value">${indicators.saldo_comex}</span>
                    </div>
                    <div class="comex-chip-tooltip-footer">Valores FOB em US$ bilhões</div>
                </div>
            </div>
        `);
    }

    container.innerHTML = `<div class="comex-indicators">${chips.join('')}</div>`;
}

/**
 * ANALYTICS - Tracking de cliques em notícias
 */
class NewsAnalytics {
    constructor() {
        this.endpoint = '/api/noticias-comex';
        this.apiKey = this.getApiBypassKey();
    }

    getApiBypassKey() {
        if (typeof window !== 'undefined' && window.API_BYPASS_KEY) {
            return window.API_BYPASS_KEY;
        }
        return '';
    }

    getUserData() {
        // Tenta obter dados do usuário do sessionStorage ou variáveis globais
        const userData = {
            user_id: null,
            user_email: null,
            user_name: null,
            user_role: null,
            session_id: null
        };

        // Tentar pegar do sessionStorage
        try {
            const storedUser = sessionStorage.getItem('user_data');
            if (storedUser) {
                const parsed = JSON.parse(storedUser);
                Object.assign(userData, parsed);
            }
        } catch (e) {
            console.warn('Não foi possível recuperar dados do usuário do sessionStorage');
        }

        // Fallback para variáveis globais
        if (typeof window !== 'undefined') {
            if (window.currentUser) {
                Object.assign(userData, window.currentUser);
            }
        }

        return userData;
    }

    async trackNewsClick(newsId, newsTitle, newsSource) {
        try {
            const userData = this.getUserData();
            
            const payload = {
                ...userData,
                news_title: newsTitle,
                news_source: newsSource
            };

            const response = await fetch(`${this.endpoint}/${newsId}/analytics`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-API-Key': this.apiKey
                },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                console.warn('Erro ao registrar analytics:', response.statusText);
            } else {
                console.log(`✓ Analytics registrado: Notícia #${newsId}`);
            }
        } catch (error) {
            console.error('Erro ao enviar analytics:', error);
        }
    }
}

// Instância global do analytics
window.newsAnalytics = new NewsAnalytics();

// Expor para uso global
window.NewsGallery = NewsGallery;
