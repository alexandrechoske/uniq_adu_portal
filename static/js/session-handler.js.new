/**
 * Session Handler - Versão simplificada sem dependência do sistema de cache
 * Verifica a validade da sessão do usuário periodicamente
 */

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

// Função para verificar o status da sessão
function checkSession() {
    console.log("[SessionHandler] Verificando status da sessão...");
    
    return new Promise((resolve, reject) => {
        console.log("[SessionHandler] Enviando requisição de verificação...");
        fetch('/paginas/check-session', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Cache-Control': 'no-cache'
            },
        })
        .then(response => {
            console.log("[SessionHandler] Resposta recebida:", response.status);
            if (!response.ok) {
                if (response.status === 401) {
                    console.warn("[SessionHandler] Sessão expirada. Redirecionando para login...");
                    window.location.href = '/login';
                    resolve(false);
                    return null;
                }
                throw new Error('Erro na verificação da sessão: ' + response.status);
            }
            return response.json();
        })
        .then(data => {
            if (!data) return; // Caso tenha sido redirecionado
            
            console.log("[SessionHandler] Dados recebidos:", data);
            
            if (data && data.status === 'success') {
                console.log("[SessionHandler] Sessão válida:", data.message);
                resolve(true);
            } else {
                console.warn("[SessionHandler] Dados inválidos recebidos do servidor:", data);
                resolve(false);
            }
        })
        .catch(error => {
            console.error("[SessionHandler] Erro ao verificar sessão:", error);
            reject(error);
        });
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
