// Global Data Refresh System
// Sistema global de atualização de dados que busca tudo do Supabase a cada 60s
// e disponibiliza para todas as páginas da aplicação

(function() {
    'use strict';
    
    // Verificar se já foi inicializado
    if (window.GlobalRefresh) {
        console.warn('[GlobalRefresh] Sistema já inicializado, ignorando nova inicialização');
        return;
    }

    // Variáveis privadas do namespace
    let refreshInterval = null;
    let countdownInterval = null;
    let countdown = 60; // 60 segundos
    let isRefreshing = false;
    let lastUpdateTime = null;

    // Configuração do sistema
    const CONFIG = {
        REFRESH_INTERVAL: 60, // 60 segundos
        CHECK_SESSION_ENDPOINT: '/paginas/check-session',
        GLOBAL_DATA_ENDPOINT: '/api/global-data'
    };

    // Cache global de dados
    let globalDataCache = {
        importacoes: [],
        usuarios: [],
        dashboard_stats: {},
        last_update: null,
        session_valid: true
    };

    // Event emitter para notificar páginas sobre atualizações
    const eventEmitter = new EventTarget();

    // Função para verificar se a sessão ainda é válida
    async function checkSession() {
        try {
            console.log('[GlobalRefresh] Verificando sessão...');
            const response = await fetch(CONFIG.CHECK_SESSION_ENDPOINT, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'Cache-Control': 'no-cache'
                }
            });

            if (!response.ok) {
                if (response.status === 401) {
                    console.warn('[GlobalRefresh] Sessão expirada, redirecionando para login...');
                    window.location.href = '/login';
                    return false;
                }
                throw new Error(`Erro ao verificar sessão: ${response.status}`);
            }

            const sessionData = await response.json();
            if (!sessionData || sessionData.status !== 'success') {
                console.warn('[GlobalRefresh] Sessão inválida:', sessionData);
                window.location.href = '/login';
                return false;
            }

            console.log('[GlobalRefresh] Sessão válida');
            globalDataCache.session_valid = true;
            return true;
        } catch (error) {
            console.error('[GlobalRefresh] Erro na verificação de sessão:', error);
            globalDataCache.session_valid = false;
            return false;
        }
    }

    // Função para buscar todos os dados globais
    async function fetchGlobalData() {
        try {
            console.log('[GlobalRefresh] Buscando dados globais...');
            
            const response = await fetch(CONFIG.GLOBAL_DATA_ENDPOINT, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'Cache-Control': 'no-cache'
                }
            });

            if (!response.ok) {
                throw new Error(`Erro HTTP: ${response.status}`);
            }

            const data = await response.json();
            
            if (data.status === 'success') {
                // Atualizar cache global
                globalDataCache = {
                    ...globalDataCache,
                    ...data.data,
                    last_update: new Date().toLocaleString('pt-BR')
                };
                
                console.log('[GlobalRefresh] Dados globais atualizados:', Object.keys(data.data));
                
                // Emitir evento para notificar páginas
                eventEmitter.dispatchEvent(new CustomEvent('dataUpdated', {
                    detail: globalDataCache
                }));
                
                // Atualizar timestamp no header
                updateHeaderTimestamp();
                
                return true;
            } else {
                throw new Error(data.message || 'Erro desconhecido');
            }
        } catch (error) {
            console.error('[GlobalRefresh] Erro ao buscar dados globais:', error);
            showNotification('Erro ao atualizar dados: ' + error.message, 'error');
            return false;
        }
    }

    // Função para atualizar o timestamp no header
    function updateHeaderTimestamp() {
        const timestampElement = document.querySelector('[data-global-timestamp]');
        if (timestampElement && globalDataCache.last_update) {
            timestampElement.textContent = `Última atualização: ${globalDataCache.last_update}`;
        }
    }

    // Função para mostrar notificações
    function showNotification(message, type = 'info') {
        let notificationContainer = document.getElementById('global-notification-container');
        if (!notificationContainer) {
            notificationContainer = document.createElement('div');
            notificationContainer.id = 'global-notification-container';
            notificationContainer.className = 'fixed top-4 right-4 z-50 space-y-2';
            document.body.appendChild(notificationContainer);
        }

        const notification = document.createElement('div');
        notification.className = `
            px-4 py-3 rounded-lg shadow-lg text-white transform transition-all duration-300 translate-x-full
            ${type === 'error' ? 'bg-red-500' : type === 'success' ? 'bg-green-500' : 'bg-blue-500'}
        `;
        notification.textContent = message;

        notificationContainer.appendChild(notification);

        // Animação de entrada
        setTimeout(() => {
            notification.classList.remove('translate-x-full');
        }, 100);

        // Remover após 5 segundos
        setTimeout(() => {
            notification.classList.add('translate-x-full');
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, 5000);
    }

    // Função para iniciar o contador regressivo
    function startCountdown() {
        const countdownElement = document.querySelector('[data-global-countdown]');
        
        countdownInterval = setInterval(() => {
            countdown--;
            
            if (countdownElement) {
                countdownElement.textContent = countdown;
            }
            
            if (countdown <= 0) {
                countdown = CONFIG.REFRESH_INTERVAL;
                performGlobalRefresh();
            }
        }, 1000);
    }

    // Função para parar o contador
    function stopCountdown() {
        if (countdownInterval) {
            clearInterval(countdownInterval);
            countdownInterval = null;
        }
    }

    // Função principal de refresh global
    async function performGlobalRefresh() {
        if (isRefreshing) {
            console.log('[GlobalRefresh] Refresh já em andamento, ignorando...');
            return;
        }

        try {
            isRefreshing = true;
            console.log('[GlobalRefresh] Iniciando refresh global...');
            
            // Verificar sessão primeiro
            const sessionValid = await checkSession();
            if (!sessionValid) {
                return;
            }

            // Buscar dados globais
            const success = await fetchGlobalData();
            
            if (success) {
                lastUpdateTime = new Date();
                console.log('[GlobalRefresh] Refresh global concluído com sucesso');
            }
            
        } catch (error) {
            console.error('[GlobalRefresh] Erro durante refresh global:', error);
            showNotification('Erro durante atualização global: ' + error.message, 'error');
        } finally {
            isRefreshing = false;
        }
    }

    // Função para inicializar o sistema
    function initializeGlobalRefresh() {
        console.log('[GlobalRefresh] Inicializando sistema de refresh global...');
        
        // Parar qualquer intervalo existente
        if (refreshInterval) {
            clearInterval(refreshInterval);
        }
        
        // Fazer primeira busca imediatamente
        performGlobalRefresh();
        
        // Iniciar contador
        countdown = CONFIG.REFRESH_INTERVAL;
        startCountdown();
        
        console.log('[GlobalRefresh] Sistema de refresh global iniciado');
    }

    // Função para parar o sistema
    function stopGlobalRefresh() {
        console.log('[GlobalRefresh] Parando sistema de refresh global...');
        
        if (refreshInterval) {
            clearInterval(refreshInterval);
            refreshInterval = null;
        }
        
        stopCountdown();
        
        console.log('[GlobalRefresh] Sistema de refresh global parado');
    }    // Event listeners e inicialização
    document.addEventListener('DOMContentLoaded', function() {
        console.log('[GlobalRefresh] Verificando se deve inicializar...');
        
        // Não inicializar o sistema na página de login
        if (window.location.pathname === '/login' || window.location.pathname === '/auth/login') {
            console.log('[GlobalRefresh] Na página de login, não inicializando sistema');
            return;
        }
        
        // Verificar se existe um usuário logado antes de inicializar
        if (!document.body.classList.contains('logged-in') && !document.querySelector('[data-user-id]')) {
            console.log('[GlobalRefresh] Usuário não logado, não inicializando sistema');
            return;
        }
        
        console.log('[GlobalRefresh] Inicializando GlobalRefresh...');
        
        // Inicializar sistema
        initializeGlobalRefresh();
        
        // Event listener para botão de refresh manual global
        const globalRefreshButton = document.getElementById('global-refresh-button');
        if (globalRefreshButton) {
            globalRefreshButton.addEventListener('click', function() {
                console.log('[GlobalRefresh] Refresh manual solicitado');
                performGlobalRefresh();
                countdown = CONFIG.REFRESH_INTERVAL; // Reset countdown
            });
        }
        
        // Parar refresh quando a página não estiver visível
        document.addEventListener('visibilitychange', function() {
            if (document.hidden) {
                console.log('[GlobalRefresh] Página oculta, pausando refresh');
                stopCountdown();
            } else {
                console.log('[GlobalRefresh] Página visível, retomando refresh');
                startCountdown();
            }
        });
        
        console.log('[GlobalRefresh] Inicialização concluída');
    });

    // API pública do GlobalRefresh
    window.GlobalRefresh = {
        // Métodos de controle
        start: initializeGlobalRefresh,
        stop: stopGlobalRefresh,
        refresh: performGlobalRefresh,
        
        // Acesso aos dados
        getData: function() {
            return { ...globalDataCache };
        },
        
        getImportacoes: function() {
            return globalDataCache.importacoes || [];
        },
        
        getUsuarios: function() {
            return globalDataCache.usuarios || [];
        },
        
        getDashboardStats: function() {
            return globalDataCache.dashboard_stats || {};
        },
        
        getLastUpdate: function() {
            return globalDataCache.last_update;
        },
        
        isSessionValid: function() {
            return globalDataCache.session_valid;
        },
        
        // Event system para páginas se inscreverem em atualizações
        onDataUpdate: function(callback) {
            eventEmitter.addEventListener('dataUpdated', callback);
        },
        
        offDataUpdate: function(callback) {
            eventEmitter.removeEventListener('dataUpdated', callback);
        }
    };

    console.log('[GlobalRefresh] Sistema inicializado e API exposta');

})(); // Fim do namespace
