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
            console.log('[SESSION] ========== VERIFICANDO SESSÃO ==========');
            const response = await fetch('/paginas/check-session', {
                method: 'GET',
                credentials: 'same-origin',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            console.log('[SESSION] Response status:', response.status);

            if (response.status === 401) {
                console.warn('[SESSION] 🔴 Sessão expirada (401)');
                this.handleSessionExpired();
                return;
            }

            const data = await response.json();
            console.log('[SESSION] Response data:', data);
            console.log('[SESSION] data.status:', data?.status);
            console.log('[SESSION] data.session_valid:', data?.session_valid);

            // CORREÇÃO: Verificar usando 'status' ou 'session_valid' (o backend retorna ambos)
            const isValid = data.status === 'success' || data.session_valid === true;

            if (!isValid) {
                console.warn('[SESSION] 🔴 Sessão inválida!');
                console.warn('[SESSION] data:', JSON.stringify(data, null, 2));
                this.handleSessionExpired();
            } else {
                // Sessão válida, continuar normalmente
                console.log('[SESSION] ✅ Sessão válida');
            }

        } catch (error) {
            console.warn('[SESSION] ⚠️ Erro ao verificar sessão (não redirecionando):', error);
            // NÃO redirecionar em caso de erro de rede - pode ser erro temporário
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
        console.warn('[SESSION] Sessão expirada detectada! Redirecionando para login...');

        // Evitar múltiplos redirecionamentos
        if (this.isRedirecting) return;
        this.isRedirecting = true;

        // Salvar URL atual para redirecionamento pós-login (opcional)
        // localStorage.setItem('redirect_after_login', window.location.pathname);

        // Alertar usuário (opcional, pode ser intrusivo)
        // alert('Sua sessão expirou. Por favor, faça login novamente.');

        // Redirecionar para login
        window.location.href = '/auth/login?expired=true';
    }

    // showExpiredMessage removido: não exibe mais aviso visual

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