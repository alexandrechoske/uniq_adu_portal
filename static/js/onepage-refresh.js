// OnePage Auto-refresh System
// Sistema simplificado de atualização automática da OnePage sem dependências de cache

// Criar namespace isolado para evitar conflitos
(function() {
    'use strict';
    
    // Verificar se já foi inicializado
    if (window.OnePageRefresh) {
        console.warn('[OnePage] Sistema já inicializado, ignorando nova inicialização');
        return;
    }
    
    // Variáveis privadas do namespace
    let refreshInterval = null;
    let countdownInterval = null;
    let countdown = 60; // 60 segundos

    // Configuração do sistema
    const CONFIG = {
        AUTO_REFRESH_INTERVAL: 60, // 60 segundos
        DATA_UPDATE_ENDPOINT: '/onepage/update-data',
        PAGE_DATA_ENDPOINT: '/onepage/page-data',
        CHECK_SESSION_ENDPOINT: '/paginas/check-session'
    };

// Função para verificar se a sessão ainda é válida
async function checkSession() {
    try {
        console.log('[OnePage] Verificando sessão...');
        const response = await fetch(CONFIG.CHECK_SESSION_ENDPOINT, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Cache-Control': 'no-cache'
            }
        });

        if (!response.ok) {
            if (response.status === 401) {
                console.warn('[OnePage] Sessão expirada, redirecionando para login...');
                window.location.href = '/login';
                return false;
            }
            throw new Error(`Erro ao verificar sessão: ${response.status}`);
        }

        const sessionData = await response.json();
        if (!sessionData || sessionData.status !== 'success') {
            console.warn('[OnePage] Sessão inválida:', sessionData);
            window.location.href = '/login';
            return false;
        }

        console.log('[OnePage] Sessão válida');
        return true;
    } catch (error) {
        console.error('[OnePage] Erro na verificação de sessão:', error);
        // Se não conseguir verificar a sessão, assume que é válida para não interromper o fluxo
        return true;
    }
}

// Função para mostrar indicador de carregamento
function showLoading() {
    const loadingOverlay = document.getElementById('loading-overlay');
    if (loadingOverlay) {
        loadingOverlay.classList.remove('hidden');
    }
}

// Função para esconder indicador de carregamento
function hideLoading() {
    const loadingOverlay = document.getElementById('loading-overlay');
    if (loadingOverlay) {
        loadingOverlay.classList.add('hidden');
    }
}

// Função para atualizar os dados da página
async function updatePageData() {
    try {
        console.log('[OnePage] Atualizando dados da página...');
        
        const currentUrl = new URL(window.location);
        const empresa = currentUrl.searchParams.get('empresa');
        
        const params = new URLSearchParams();
        if (empresa) {
            params.append('empresa', empresa);
        }
        
        const response = await fetch(`${CONFIG.PAGE_DATA_ENDPOINT}?${params.toString()}`, {
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
            updateKPICards(data.kpis);
            updateTable(data.table_data);
            updateLastUpdateTime(data.last_update);
            if (data.currencies) {
                updateCurrencyDisplay(data.currencies);
            }
            console.log('[OnePage] Dados atualizados com sucesso');
        } else {
            throw new Error(data.message || 'Erro desconhecido');
        }
    } catch (error) {
        console.error('[OnePage] Erro ao atualizar dados da página:', error);
        showNotification('Erro ao atualizar dados: ' + error.message, 'error');
    }
}

// Função para atualizar os cards de KPI
function updateKPICards(kpis) {
    if (!kpis) return;
    
    const kpiElements = {
        total: document.querySelector('[data-kpi="total"]'),
        aereo: document.querySelector('[data-kpi="aereo"]'),
        terrestre: document.querySelector('[data-kpi="terrestre"]'),
        maritimo: document.querySelector('[data-kpi="maritimo"]'),
        aguardando_chegada: document.querySelector('[data-kpi="aguardando_chegada"]'),
        aguardando_embarque: document.querySelector('[data-kpi="aguardando_embarque"]'),
        di_registrada: document.querySelector('[data-kpi="di_registrada"]')
    };

    Object.keys(kpiElements).forEach(key => {
        const element = kpiElements[key];
        if (element && kpis.hasOwnProperty(key)) {
            element.textContent = kpis[key];
        }
    });
}

// Função para atualizar a tabela
function updateTable(tableData) {
    const tableBody = document.querySelector('.data-table tbody');
    if (!tableBody || !Array.isArray(tableData)) return;

    if (tableData.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="100%" class="text-center py-8 text-gray-500">
                    <div class="empty-state">
                        <p class="text-lg font-medium">Nenhum processo encontrado</p>
                        <p class="text-sm">Não há processos correspondentes aos filtros selecionados.</p>
                    </div>
                </td>
            </tr>
        `;
        return;
    }

    // Reconstruct table rows
    tableBody.innerHTML = tableData.map(row => {
        return `
            <tr>
                <td>${row.processo || ''}</td>
                <td>${row.cliente_razaosocial || ''}</td>
                <td>${row.data_embarque || ''}</td>
                <td>${row.data_chegada || ''}</td>
                <td>${row.via_transporte_descricao || ''}</td>
                <td>${row.carga_status || ''}</td>
                <td>${row.status_doc || ''}</td>
                <td>
                    <span class="canal-badge ${getCanalClass(row.canal_parametrizado)}">
                        ${row.canal_parametrizado || ''}
                    </span>
                </td>
            </tr>
        `;
    }).join('');
}

// Função para determinar a classe CSS do canal
function getCanalClass(canal) {
    if (!canal) return '';
    
    switch (canal.toLowerCase()) {
        case 'verde':
            return 'canal-verde';
        case 'amarelo':
            return 'canal-amarelo';
        case 'vermelho':
            return 'canal-vermelho';
        default:
            return '';
    }
}

// Função para atualizar a moeda
function updateCurrencyDisplay(currencies) {
    if (!currencies) return;
    
    const usdElement = document.querySelector('[data-currency="USD"]');
    const eurElement = document.querySelector('[data-currency="EUR"]');
    
    if (usdElement && currencies.USD) {
        usdElement.textContent = `R$ ${currencies.USD.toFixed(4)}`;
    }
    
    if (eurElement && currencies.EUR) {
        eurElement.textContent = `R$ ${currencies.EUR.toFixed(4)}`;
    }
}

// Função para atualizar o timestamp da última atualização
function updateLastUpdateTime(lastUpdate) {
    const timestampElement = document.querySelector('[data-timestamp]');
    if (timestampElement && lastUpdate) {
        timestampElement.textContent = lastUpdate;
    }
}

// Função para mostrar notificações
function showNotification(message, type = 'info') {
    // Criar elemento de notificação se não existir
    let notificationContainer = document.getElementById('notification-container');
    if (!notificationContainer) {
        notificationContainer = document.createElement('div');
        notificationContainer.id = 'notification-container';
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
    const countdownElement = document.querySelector('[data-countdown]');
    
    countdownInterval = setInterval(() => {
        countdown--;
        
        if (countdownElement) {
            countdownElement.textContent = countdown;
        }
        
        if (countdown <= 0) {
            countdown = CONFIG.AUTO_REFRESH_INTERVAL;
            refreshOnePage();
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

// Função principal de refresh da OnePage
async function refreshOnePage(forceUpdate = false) {
    try {
        console.log('[OnePage] Iniciando refresh...');
        
        // Verificar sessão primeiro
        const sessionValid = await checkSession();
        if (!sessionValid) {
            return;
        }

        showLoading();
        
        // Se forceUpdate for true, chamar a atualização de dados primeiro
        if (forceUpdate) {
            console.log('[OnePage] Forçando atualização de dados...');
            try {
                const updateResponse = await fetch(CONFIG.DATA_UPDATE_ENDPOINT, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Cache-Control': 'no-cache'
                    }
                });

                const updateResult = await updateResponse.json();
                if (updateResult.status === 'success' || updateResult.status === 'warning') {
                    showNotification(updateResult.message, updateResult.status === 'warning' ? 'info' : 'success');
                } else {
                    showNotification('Erro na atualização: ' + updateResult.message, 'error');
                }
            } catch (updateError) {
                console.error('[OnePage] Erro na atualização forçada:', updateError);
                showNotification('Erro ao atualizar dados: ' + updateError.message, 'error');
            }
        }        // Atualizar dados da página
        await updatePageData();
        
        // Resetar contador
        countdown = CONFIG.AUTO_REFRESH_INTERVAL;
        
    } catch (error) {
        console.error('[OnePage] Erro durante refresh:', error);
        showNotification('Erro durante atualização: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// Função para inicializar o sistema de auto-refresh
function initializeAutoRefresh() {
    console.log('[OnePage] Inicializando sistema de auto-refresh...');
    
    // Parar qualquer intervalo existente
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
    
    // Iniciar contador
    countdown = CONFIG.AUTO_REFRESH_INTERVAL;
    startCountdown();
    
    console.log('[OnePage] Sistema de auto-refresh iniciado');
}

// Função para parar o sistema de auto-refresh
function stopAutoRefresh() {
    console.log('[OnePage] Parando sistema de auto-refresh...');
    
    if (refreshInterval) {
        clearInterval(refreshInterval);
        refreshInterval = null;
    }
    
    stopCountdown();
    
    console.log('[OnePage] Sistema de auto-refresh parado');
}

// Event listeners e inicialização
document.addEventListener('DOMContentLoaded', function() {
    console.log('[OnePage] Inicializando OnePage...');
    
    // Inicializar sistema de auto-refresh
    initializeAutoRefresh();
    
    // Event listener para botão de refresh manual
    const refreshButton = document.getElementById('refresh-button');
    if (refreshButton) {
        refreshButton.addEventListener('click', function() {
            console.log('[OnePage] Refresh manual solicitado');
            refreshOnePage(true); // true = forceUpdate
        });
    }
    
    // Event listener para mudança de filtro de empresa
    const companySelect = document.getElementById('company-select');
    if (companySelect) {
        companySelect.addEventListener('change', function() {
            console.log('[OnePage] Filtro de empresa alterado');
            const selectedCompany = this.value;
            filterByCompany(selectedCompany);
        });
    }
    
    // Parar auto-refresh quando a página não estiver visível
    document.addEventListener('visibilitychange', function() {
        if (document.hidden) {
            console.log('[OnePage] Página oculta, pausando auto-refresh');
            stopCountdown();
        } else {
            console.log('[OnePage] Página visível, retomando auto-refresh');
            startCountdown();
        }
    });
    
    console.log('[OnePage] Inicialização concluída');
});

// Função para filtrar por empresa (mantida para compatibilidade)
function filterByCompany(value) {
    const url = new URL(window.location);
    if (value && value !== '') {
        url.searchParams.set('empresa', value);
    } else {
        url.searchParams.delete('empresa');
    }
    window.location.href = url.toString();
}

// Expor funções globalmente para uso externo
window.refreshOnePage = refreshOnePage;
window.filterByCompany = filterByCompany;
window.onepageAutoRefresh = {
    start: initializeAutoRefresh,
    stop: stopAutoRefresh,
    refresh: refreshOnePage
};

// Marcar como inicializado
window.OnePageRefresh = true;

})(); // Fim do namespace