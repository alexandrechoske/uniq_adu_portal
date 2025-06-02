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
    }    /**
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
        }        // Verifica cache do menu
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
            });            if (response.ok) {
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
     */    renderMenu(menuData) {
        const sidebarNav = document.getElementById('sidebar-nav');
        if (!sidebarNav) {
            console.warn('[MenuCache] Elemento sidebar-nav não encontrado');
            return;
        }        try {
            // Corrigindo estrutura dos dados - API retorna {status: 'success', data: array}
            const pages = menuData.data || menuData.pages || [];
            const isSuccess = menuData.status === 'success' || menuData.success === true;
            
            if (isSuccess && pages && pages.length > 0) {
                console.log(`[MenuCache] Renderizando ${pages.length} páginas`);
                
                // Limpar o conteúdo atual
                sidebarNav.innerHTML = '';
                
                // Obter endpoint atual para marcar página ativa (não disponível no contexto, usando pathname)
                const currentPath = window.location.pathname;
                
                // Construir links de navegação
                pages.forEach(page => {
                    console.log(`[MenuCache] Processando página: ${page.nome_pagina}`);
                    const link = document.createElement('a');
                    
                    // Se a página está ativa ou em manutenção
                    if (page.flg_ativo) {
                        link.href = page.url_rota;
                        link.className = `sidebar-item ${currentPath === page.url_rota ? 'active' : ''}`;
                    } else {
                        link.href = 'javascript:void(0)';  // Link desabilitado
                        link.className = 'sidebar-item opacity-60 cursor-not-allowed';
                    }
                    
                    // Montar o link com ícone e texto
                    link.innerHTML = `
                        <svg class="sidebar-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            ${page.icone}
                        </svg>
                        <span>${page.flg_ativo ? page.nome_pagina : page.nome_pagina + ' (' + page.mensagem_manutencao + ')'}</span>
                        ${!page.flg_ativo ? '<span class="ml-1 text-yellow-500"><svg class="w-4 h-4 inline-block" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg></span>' : ''}
                    `;
                    
                    // Adicionar evento para páginas em manutenção
                    if (!page.flg_ativo) {
                        link.addEventListener('click', function(e) {
                            e.preventDefault();
                            alert(`A página ${page.nome_pagina} está temporariamente em manutenção.`);
                        });
                    }
                    
                    sidebarNav.appendChild(link);
                });

                console.log('[MenuCache] Menu renderizado com sucesso');
            } else {
                console.warn('[MenuCache] Nenhuma página disponível no menu');
                console.warn('[MenuCache] Dados recebidos:', menuData);
                sidebarNav.innerHTML = '<p class="text-gray-400 px-4 py-2">Nenhuma página disponível</p>';
            }
        } catch (error) {
            console.error('[MenuCache] Erro ao renderizar menu:', error);
            sidebarNav.innerHTML = '<p class="text-red-400 px-4 py-2">Erro ao carregar menu</p>';
        }
    }

    /**
     * Força uma atualização do menu (limpa cache e recarrega)
     */
    async forceRefreshMenu() {
        console.log('[MenuCache] Forçando atualização do menu...');
        this.clearCache(this.CACHE_KEY_MENU);
        this.clearCache(this.CACHE_KEY_SESSION);
        this.menuLoaded = false;
        return await this.loadMenu();
    }

    /**
     * Inicializa o sistema de cache
     */
    async initialize() {
        console.log('[MenuCache] Inicializando sistema...');
        
        // Carrega o menu imediatamente
        await this.loadMenu();
        
        // Configura verificação periódica de sessão (apenas sessão, não menu)
        setInterval(async () => {
            if (this.needsSessionCheck()) {
                console.log('[MenuCache] Verificação periódica de sessão...');
                const sessionValid = await this.validateSession();
                if (!sessionValid) {
                    console.warn('[MenuCache] Sessão inválida detectada');
                    this.clearCache();
                    // Não redireciona automaticamente, deixa para a próxima interação
                }
            }
        }, this.SESSION_CHECK_INTERVAL);

        console.log('[MenuCache] Sistema inicializado com sucesso');
    }
}

// Criar instância global
window.menuCache = new MenuCache();

// Função de compatibilidade para o código existente
window.loadSidebarMenu = function() {
    console.log('[MenuCache] Função de compatibilidade chamada');
    return window.menuCache.loadMenu();
};

// Função para recarregar menu de forma robusta (compatibilidade)
window.reloadSidebarMenuRobust = function() {
    console.log('[MenuCache] Recarga robusta solicitada');
    return window.menuCache.forceRefreshMenu();
};

// Inicializar quando a página carregar
document.addEventListener('DOMContentLoaded', function() {
    // Verificar se não estamos na página de login ou em páginas não autenticadas
    const isLoginPage = window.location.pathname.includes('/login') || 
                       window.location.pathname.includes('/register') ||
                       window.location.pathname.includes('/reset-password');
    
    // Verificar se o usuário está logado (baseado na classe do body)
    const isUserLoggedIn = document.body.classList.contains('logged-in');
    
    if (isLoginPage) {
        console.log('[MenuCache] Página de login detectada, não inicializando sistema de cache');
        return;
    }
    
    if (!isUserLoggedIn) {
        console.log('[MenuCache] Usuário não logado, não inicializando sistema de cache');
        return;
    }
    
    console.log('[MenuCache] Página carregada, inicializando...');
    window.menuCache.initialize();
});

// Limpar cache quando o usuário fizer logout ou a página for fechada
window.addEventListener('beforeunload', function() {
    // Opcional: Você pode manter o cache entre sessões ou limpar
    // window.menuCache.clearCache();
});

// Exportar para uso em outros módulos se necessário
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MenuCache;
}
