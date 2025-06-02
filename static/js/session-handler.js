// Função para verificar e manter a sessão ativa
let sessionCheckInterval;

// Verifica o status da sessão a cada 30 segundos
function initSessionChecker() {
    // Limpar qualquer intervalo existente
    if (sessionCheckInterval) {
        clearInterval(sessionCheckInterval);
    }
    
    // Iniciar verificação de sessão
    sessionCheckInterval = setInterval(checkSession, 30000); // 30 segundos
    
    // Também verificar imediatamente
    checkSession();
}

// Função para verificar o status da sessão (integrada com cache)
function checkSession() {
    console.log("[SessionHandler] Verificando status da sessão...");
    
    // Se o sistema de cache estiver disponível, usar ele
    if (window.menuCache) {
        console.log("[SessionHandler] Usando sistema de cache para verificar sessão...");
        return window.menuCache.validateSession();
    }
    
    // Fallback para o método tradicional
    console.log("[SessionHandler] Sistema de cache não disponível, usando método tradicional...");
    return new Promise((resolve, reject) => {
        console.log("Iniciando fetch para /paginas/check-session...");
        fetch('/paginas/check-session', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Cache-Control': 'no-cache'
            },
        })        .then(response => {
            console.log("Resposta recebida:", response.status);
            if (!response.ok) {
                if (response.status === 401) {
                    console.warn("Sessão expirada. Redirecionando para login...");
                    window.location.href = '/login';
                    resolve(false);
                    return null;
                }
                throw new Error('Erro na verificação da sessão: ' + response.status);
            }
            console.log("Resposta OK, convertendo para JSON...");
            return response.json();
        })        .then(data => {
            console.log("Dados recebidos:", data);            if (data && data.status === 'success') {
                console.log("Sessão válida:", data.message);
                
                // Se o menu estiver disponível, tente recarregá-lo de forma mais robusta
                setTimeout(() => {
                    reloadSidebarMenuRobust();
                }, 100);
                
                resolve(true);
            } else {
                console.warn("Dados inválidos recebidos do servidor:", data);
                resolve(false);
            }
        })        .catch(error => {
            console.error("Erro ao verificar sessão:", error);
            console.error("Detalhes do erro:", error.message, error.stack);
            reject(error);
        });    });
}

// Função robusta para recarregar o menu lateral
// Função de compatibilidade que usa o sistema de cache quando disponível
function reloadSidebarMenuRobust() {
    console.log('[SessionHandler] Recarga robusta do menu solicitada...');
    
    // Verifica se o sistema de cache está disponível
    if (window.menuCache) {
        console.log('[SessionHandler] Usando sistema de cache para recarregar menu...');
        return window.menuCache.forceRefreshMenu();
    } else {
        console.log('[SessionHandler] Sistema de cache não disponível, usando método tradicional...');
        return reloadSidebarMenuTraditional();
    }
}

// Método tradicional mantido como fallback
function reloadSidebarMenuTraditional() {
    console.log("Recarregando menu lateral de forma robusta...");
    
    // Primeira tentativa - se loadSidebarMenu estiver disponível no escopo global
    if (typeof loadSidebarMenu === 'function') {
        console.log("Chamando função loadSidebarMenu global...");
        loadSidebarMenu();
        
        // Verificar resultado após um pequeno atraso
        setTimeout(() => {
            const menuContent = document.querySelector('#sidebar-nav');
            if (menuContent && (menuContent.textContent.includes('Nenhuma página disponível') || 
                               menuContent.textContent.includes('Erro ao carregar') ||
                               menuContent.textContent.includes('Carregando menu'))) {
                console.warn("Menu não carregou corretamente, tentando método alternativo...");
                loadMenuViaFetch();
            }
        }, 1000);
    } else {
        console.warn("Função loadSidebarMenu não encontrada, usando método alternativo...");
        loadMenuViaFetch();
    }
}

// Função para carregar o menu via fetch direto
function loadMenuViaFetch() {
    const sidebarNav = document.getElementById('sidebar-nav');
    
    if (!sidebarNav) {
        console.error("Elemento sidebar-nav não encontrado!");
        return;
    }
    
    sidebarNav.innerHTML = '<div class="text-center text-gray-500 py-2">Carregando menu...</div>';
    
    fetch('/paginas/menu', {
        method: 'GET',
        headers: {
            'Cache-Control': 'no-cache',
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Erro ' + response.status + ' ao carregar menu');
        }
        return response.json();
    })
    .then(data => {
        if (data.status === 'success' && data.menu && Array.isArray(data.menu)) {
            // Limpar menu atual
            sidebarNav.innerHTML = '';
            
            // Adicionar as páginas ao menu
            data.menu.forEach(page => {
                const link = document.createElement('a');
                
                if (page.flg_ativo) {
                    link.href = page.url_rota;
                    link.className = 'sidebar-item';
                } else {
                    link.href = 'javascript:void(0)';
                    link.className = 'sidebar-item opacity-60 cursor-not-allowed';
                    link.addEventListener('click', (e) => {
                        e.preventDefault();
                        alert(`A página ${page.nome_pagina} está temporariamente em manutenção.`);
                    });
                }
                
                link.innerHTML = `
                    <svg class="sidebar-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        ${page.icone}
                    </svg>
                    <span>${page.nome_pagina}${page.flg_ativo ? '' : ' (' + page.mensagem_manutencao + ')'}</span>
                `;
                
                sidebarNav.appendChild(link);
            });
            
            console.log("Menu carregado com sucesso via fetch");
        } else {
            throw new Error("Dados inválidos recebidos do servidor");
        }
    })
    .catch(error => {
        console.error('Erro ao carregar menu:', error);
        sidebarNav.innerHTML = '<div class="text-center text-red-500 py-2">Erro ao carregar o menu.</div>';
    });
}

// Inicializar quando o documento estiver pronto
document.addEventListener('DOMContentLoaded', function() {
    // Verificar se não estamos na página de login ou em páginas não autenticadas
    const isLoginPage = window.location.pathname.includes('/login') || 
                       window.location.pathname.includes('/register') ||
                       window.location.pathname.includes('/reset-password');
    
    // Verificar se o usuário está logado antes de iniciar o verificador de sessão
    const isUserLoggedIn = document.body.classList.contains('logged-in');
    
    if (isLoginPage) {
        console.log('[SessionHandler] Página de login detectada, não inicializando verificador de sessão');
        return;
    }
    
    if (isUserLoggedIn) {
        console.log('[SessionHandler] Usuário logado detectado, inicializando verificador de sessão');
        initSessionChecker();
    } else {
        console.log('[SessionHandler] Usuário não logado, não inicializando verificador de sessão');
    }
});
