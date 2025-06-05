/**
 * Sistema de Cache para Menu e Permissões
 * Reduz requisições ao servidor usando localStorage e validação periódica
 */

class MenuCache {
    constructor() {
        this.CACHE_DURATION = 5 * 60 * 1000; // 5 minutos em millisegundos
        this.SESSION_CHECK_INTERVAL = 60 * 1000; // Verificar sessão a cada 1 minuto
        this.CACHE_KEY_MENU = 'unique_menu_cache';
        this.CACHE_KEY_SESSION = 'unique_session_cache';
        this.CACHE_KEY_PERMISSIONS = 'unique_permissions_cache';
        
        this.lastSessionCheck = 0;
        this.menuLoaded = false;
        this.sessionValid = false;
        
        console.log('[MenuCache] Sistema de cache inicializado');
    }

    /**
     * Verifica se o cache está válido baseado no timestamp
     */
    isCacheValid(cacheData) {
        if (!cacheData || !cacheData.timestamp) {
            return false;
        }
        const now = Date.now();
        const age = now - cacheData.timestamp;
        return age < this.CACHE_DURATION;
    }

    /**
     * Obtém dados do cache
     */
    getFromCache(key) {
        try {
            const cached = localStorage.getItem(key);
            if (cached) {
                const data = JSON.parse(cached);
                if (this.isCacheValid(data)) {
                    console.log(`[MenuCache] Cache hit para ${key}`);
                    return data;
                }
                console.log(`[MenuCache] Cache expirado para ${key}`);
            }
        } catch (error) {
            console.warn(`[MenuCache] Erro ao ler cache ${key}:`, error);
        }
        return null;
    }

    /**
     * Salva dados no cache
     */
    saveToCache(key, data) {
        try {
            const cacheData = {
                data: data,
                timestamp: Date.now()
            };
            localStorage.setItem(key, JSON.stringify(cacheData));
            console.log(`[MenuCache] Dados salvos no cache ${key}`);
        } catch (error) {
            console.warn(`[MenuCache] Erro ao salvar cache ${key}:`, error);
        }
    }

    /**
     * Limpa cache específico ou todo o cache
     */
    clearCache(key = null) {
        try {
            if (key) {
                localStorage.removeItem(key);
                console.log(`[MenuCache] Cache ${key} limpo`);
            } else {
                localStorage.removeItem(this.CACHE_KEY_MENU);
                localStorage.removeItem(this.CACHE_KEY_SESSION);
                localStorage.removeItem(this.CACHE_KEY_PERMISSIONS);
                console.log('[MenuCache] Todo o cache limpo');
            }
        } catch (error) {
            console.warn('[MenuCache] Erro ao limpar cache:', error);
        }
    }

    /**
     * Verifica se precisa validar a sessão
     */
    needsSessionCheck() {
        const now = Date.now();
        const timeSinceLastCheck = now - this.lastSessionCheck;
        return timeSinceLastCheck > this.SESSION_CHECK_INTERVAL;
    }

    /**
     * Valida a sessão com cache
     */
    async validateSession() {
        console.log('[MenuCache] Validando sessão...');
        
        // Verificar se não estamos em páginas que não precisam de validação de sessão
        const isLoginPage = window.location.pathname.includes('/login') || 
                           window.location.pathname.includes('/register') ||
                           window.location.pathname.includes('/reset-password');
        
        if (isLoginPage) {
            console.log('[MenuCache] Página de login detectada, não validando sessão');
            return false;
        }
        
        // Verifica cache da sessão primeiro
        const cachedSession = this.getFromCache(this.CACHE_KEY_SESSION);
        if (cachedSession && !this.needsSessionCheck()) {
            console.log('[MenuCache] Sessão válida no cache');
            this.sessionValid = cachedSession.data.valid;
            return this.sessionValid;
        }

        try {
            const response = await fetch('/paginas/check-session', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'Cache-Control': 'no-cache'
                }
            });

            this.lastSessionCheck = Date.now();

            if (response.ok) {
                const sessionData = await response.json();
                const isValid = sessionData && sessionData.status === 'success';
                
                // Salva no cache
                this.saveToCache(this.CACHE_KEY_SESSION, {
                    valid: isValid,
                    data: sessionData
                });
                
                this.sessionValid = isValid;
                console.log('[MenuCache] Sessão validada e salva no cache');
                return isValid;
            } else {
                console.warn('[MenuCache] Sessão inválida - status:', response.status);
                this.sessionValid = false;
                this.clearCache(this.CACHE_KEY_SESSION);
                
                if (response.status === 401) {
                    this.clearCache(); // Limpa todo o cache
                    window.location.href = '/login';
                }
                return false;
            }
        } catch (error) {
            console.error('[MenuCache] Erro ao validar sessão:', error);
            // Em caso de erro, usa o último estado conhecido se disponível
            const cachedSession = this.getFromCache(this.CACHE_KEY_SESSION);
            if (cachedSession) {
                console.log('[MenuCache] Usando sessão do cache devido a erro');
                return cachedSession.data.valid;
            }
            return false;
        }
    }

    /**
     * Carrega o menu com cache
     */
    async loadMenu() {
        console.log('[MenuCache] Carregando menu...');

        // Verifica se a sessão é válida primeiro
        const sessionValid = await this.validateSession();
        if (!sessionValid) {
            console.warn('[MenuCache] Sessão inválida, não carregando menu');
            return false;
        }

        // Verifica cache do menu
        const cachedMenu = this.getFromCache(this.CACHE_KEY_MENU);
        if (cachedMenu) {
            console.log('[MenuCache] Menu encontrado no cache');
            console.log('[MenuCache] Dados do cache:', cachedMenu.data);
            this.renderMenu(cachedMenu.data);
            this.menuLoaded = true;
            return true;
        }

        // Se não há cache, busca do servidor
        try {
            console.log('[MenuCache] Buscando menu do servidor...');
            const response = await fetch('/paginas/api', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'Cache-Control': 'no-cache'
                }
            });

            if (response.ok) {
                const menuData = await response.json();
                console.log('[MenuCache] Menu recebido do servidor:', menuData);
                console.log('[MenuCache] Estrutura dos dados:', {
                    status: menuData.status,
                    success: menuData.success,
                    data: menuData.data,
                    pages: menuData.pages,
                    dataLength: Array.isArray(menuData.data) ? menuData.data.length : 'não é array',
                    pagesLength: Array.isArray(menuData.pages) ? menuData.pages.length : 'não é array'
                });
                
                // Salva no cache
                this.saveToCache(this.CACHE_KEY_MENU, menuData);
                
                // Renderiza o menu
                this.renderMenu(menuData);
                this.menuLoaded = true;
                return true;
            } else {
                console.error('[MenuCache] Erro ao buscar menu - status:', response.status);
                return false;
            }
        } catch (error) {
            console.error('[MenuCache] Erro ao carregar menu:', error);
            return false;
        }
    }

    /**
     * Renderiza o menu na interface
     */
    renderMenu(menuData) {
        const sidebarNav = document.getElementById('sidebar-nav');
        if (!sidebarNav) {
            console.warn('[MenuCache] Elemento sidebar-nav não encontrado');
            return;
        }

        console.log('[MenuCache] Iniciando renderização do menu');
        console.log('[MenuCache] Data recebida:', menuData);

        // Extrair páginas dos dados recebidos
        let pages = [];
        if (menuData && menuData.status === 'success' && menuData.data) {
            pages = menuData.data;
        } else if (menuData && Array.isArray(menuData)) {
            pages = menuData;
        } else if (menuData && menuData.pages) {
            pages = menuData.pages;
        }

        console.log('[MenuCache] Páginas extraídas:', pages);

        // Limpar conteúdo anterior
        sidebarNav.innerHTML = '';

        if (pages && pages.length > 0) {
            console.log(`[MenuCache] Renderizando ${pages.length} páginas`);
            
            // Obter o caminho atual para destacar página ativa
            const currentPath = window.location.pathname;
            
            pages.forEach((page, index) => {
                console.log(`[MenuCache] Renderizando página ${index + 1}:`, page);
                
                const link = document.createElement('a');
                
                // Se a página está ativa ou em manutenção
                if (page.flg_ativo) {
                    link.href = page.url_rota;
                    link.className = `sidebar-item ${currentPath === page.url_rota ? 'active' : ''}`;
                } else {
                    link.href = 'javascript:void(0)';  // Link desabilitado
                    link.className = 'sidebar-item opacity-60 cursor-not-allowed';
                }
                
                // Criar elementos separadamente para evitar problemas com template literals
                const iconSvg = document.createElement('div');
                iconSvg.className = 'sidebar-icon';
                iconSvg.innerHTML = `<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">${page.icone}</svg>`;
                
                const textSpan = document.createElement('span');
                textSpan.className = 'sidebar-text';
                textSpan.textContent = page.flg_ativo ? page.nome_pagina : page.nome_pagina + ' (' + page.mensagem_manutencao + ')';
                
                link.appendChild(iconSvg);
                link.appendChild(textSpan);
                
                // Adicionar ícone de aviso para páginas em manutenção
                if (!page.flg_ativo) {
                    const warningIcon = document.createElement('span');
                    warningIcon.className = 'ml-1 text-yellow-500 sidebar-text';
                    warningIcon.innerHTML = '<svg class="w-4 h-4 inline-block" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>';
                    link.appendChild(warningIcon);
                    
                    // Adicionar evento para páginas em manutenção
                    link.addEventListener('click', function(e) {
                        e.preventDefault();
                        alert('A página ' + page.nome_pagina + ' está temporariamente em manutenção.');
                    });
                }
                
                sidebarNav.appendChild(link);
            });

            console.log('[MenuCache] Menu renderizado com sucesso');
        } else {
            console.warn('[MenuCache] Nenhuma página disponível para renderização');
            sidebarNav.innerHTML = '<div class="text-center text-gray-500 py-2"><span class="sidebar-text">Nenhuma página disponível.</span></div>';
        }
    }

    /**
     * Atualiza cache de permissões
     */
    async updatePermissions() {
        try {
            console.log('[MenuCache] Atualizando permissões...');
            const response = await fetch('/paginas/permissions', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'Cache-Control': 'no-cache'
                }
            });

            if (response.ok) {
                const permissionsData = await response.json();
                this.saveToCache(this.CACHE_KEY_PERMISSIONS, permissionsData);
                console.log('[MenuCache] Permissões atualizadas');
                return true;
            } else {
                console.error('[MenuCache] Erro ao buscar permissões');
                return false;
            }
        } catch (error) {
            console.error('[MenuCache] Erro ao atualizar permissões:', error);
            return false;
        }
    }

    /**
     * Força atualização do menu
     */
    async forceRefresh() {
        console.log('[MenuCache] Forçando atualização do menu...');
        this.clearCache();
        this.menuLoaded = false;
        await this.loadMenu();
    }

    /**
     * Verifica se tem acesso a uma página específica
     */
    hasPageAccess(pageUrl) {
        const cachedMenu = this.getFromCache(this.CACHE_KEY_MENU);
        if (!cachedMenu) return false;

        const pages = cachedMenu.data.data || cachedMenu.data;
        const page = pages.find(p => p.url_rota === pageUrl);
        return page && page.flg_ativo;
    }
}

// Criar instância global
window.menuCache = new MenuCache();

// Inicialização automática quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', function() {
    console.log('[MenuCache] DOM carregado, verificando se deve inicializar...');
    
    // Verificar se não estamos em páginas que não precisam do menu
    const isLoginPage = window.location.pathname.includes('/login') || 
                       window.location.pathname.includes('/register') ||
                       window.location.pathname.includes('/reset-password');
    
    if (isLoginPage) {
        console.log('[MenuCache] Página de login/registro detectada, não inicializando menu');
        return;
    }
    
    // Verificar se existe o elemento sidebar
    const sidebarNav = document.getElementById('sidebar-nav');
    if (!sidebarNav) {
        console.log('[MenuCache] Elemento sidebar-nav não encontrado, não inicializando');
        return;
    }
    
    console.log('[MenuCache] Inicializando sistema de menu...');
    
    // Aguarda um pouco para garantir que todos os scripts carregaram
    setTimeout(async () => {
        try {
            await window.menuCache.loadMenu();
            console.log('[MenuCache] Menu carregado com sucesso');
        } catch (error) {
            console.error('[MenuCache] Erro ao carregar menu:', error);
            
            // Fallback: tentar usar a função global do base.html
            if (typeof window.loadSidebarMenu === 'function') {
                console.log('[MenuCache] Tentando fallback para função global');
                window.loadSidebarMenu();
            }
        }
    }, 100);
});

// Atualizar menu a cada mudança de página (se usando SPA)
window.addEventListener('popstate', function() {
    if (window.menuCache && window.menuCache.menuLoaded) {
        console.log('[MenuCache] Página mudou, atualizando menu...');
        window.menuCache.forceRefresh();
    }
});

// Limpar cache ao fazer logout
window.addEventListener('beforeunload', function() {
    if (window.location.href.includes('/logout')) {
        console.log('[MenuCache] Logout detectado, limpando cache...');
        if (window.menuCache) {
            window.menuCache.clearCache();
        }
    }
});

// Exportar para Node.js se estiver em ambiente de testes
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MenuCache;
}
