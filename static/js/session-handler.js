/**
 * Session Handler - Gerencia a sessão do usuário no frontend
 */

class SessionHandler {
    constructor() {
        this.checkInterval = 5 * 60 * 1000; // Verificar a cada 5 minutos
        this.warningThreshold = 15 * 60 * 1000; // Avisar 15 minutos antes de expirar
        this.isActive = true;
        
        this.init();
    }
    
    init() {
        // Iniciar monitoramento da sessão
        this.startSessionMonitoring();
        
        // Monitorar atividade do usuário
        this.monitorUserActivity();
        
        // Interceptar requisições AJAX para verificar status da sessão
        this.interceptAjaxRequests();
    }
    
    startSessionMonitoring() {
        setInterval(() => {
            if (this.isActive) {
                this.checkSession();
            }
        }, this.checkInterval);
        
        // Primeira verificação após 1 minuto
        setTimeout(() => {
            this.checkSession();
        }, 60000);
    }
    
    async checkSession() {
        try {
            const response = await fetch('/paginas/check-session', {
                method: 'GET',
                credentials: 'same-origin',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            if (response.status === 401) {
                this.handleSessionExpired();
                return;
            }
            
            const data = await response.json();
            
            if (!data.valid) {
                this.handleSessionExpired();
            } else {
                // Sessão válida, continuar normalmente
                console.log('[SESSION] Sessão válida');
            }
            
        } catch (error) {
            console.warn('[SESSION] Erro ao verificar sessão:', error);
        }
    }
    
    monitorUserActivity() {
        const events = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click'];
        
        events.forEach(event => {
            document.addEventListener(event, () => {
                this.updateActivity();
            }, { passive: true });
        });
    }
    
    updateActivity() {
        // Atualizar timestamp de atividade (se necessário)
        // Por enquanto, apenas resetar qualquer timer de warning
        this.clearWarnings();
    }
    
    interceptAjaxRequests() {
        const originalFetch = window.fetch;
        
        // Armazenar referência ao fetch original para uso por outras partes do código
        this.originalFetch = originalFetch;
        window.sessionHandler = this;
        
        window.fetch = async (...args) => {
            try {
                // Aplicar o contexto correto do window, não do SessionHandler
                const response = await originalFetch.apply(window, args);
                
                // Verificar se a resposta indica sessão expirada
                if (response.status === 401) {
                    const responseData = await response.clone().json().catch(() => ({}));
                    if (responseData.code === 'session_expired') {
                        this.handleSessionExpired();
                    }
                }
                
                return response;
            } catch (error) {
                throw error;
            }
        };
    }
    
    handleSessionExpired() {
        this.isActive = false;
        
        // Mostrar aviso ao usuário
        this.showExpiredMessage();
        
        // Redirecionar para login após um breve delay
        setTimeout(() => {
            window.location.href = '/login';
        }, 3000);
    }
    
    showExpiredMessage() {
        // Remover mensagens anteriores
        const existingAlert = document.getElementById('session-expired-alert');
        if (existingAlert) {
            existingAlert.remove();
        }
        
        // Criar nova mensagem
        const alert = document.createElement('div');
        alert.id = 'session-expired-alert';
        alert.className = 'fixed top-4 right-4 bg-red-500 text-white px-6 py-4 rounded-lg shadow-lg z-50';
        alert.innerHTML = `
            <div class="flex items-center">
                <svg class="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path>
                </svg>
                <div>
                    <p class="font-semibold">Sessão Expirada</p>
                    <p class="text-sm">Você será redirecionado para o login...</p>
                </div>
            </div>
        `;
        
        document.body.appendChild(alert);
    }
    
    clearWarnings() {
        const existingAlert = document.getElementById('session-warning-alert');
        if (existingAlert) {
            existingAlert.remove();
        }
    }
}

// Inicializar o gerenciador de sessão quando a página carregar
document.addEventListener('DOMContentLoaded', () => {
    // Só inicializar se o usuário estiver logado
    if (document.body.classList.contains('logged-in')) {
        window.sessionHandler = new SessionHandler();
        console.log('[SESSION] Session handler initialized');
    }
});

// Exportar para uso global se necessário
window.SessionHandler = SessionHandler;