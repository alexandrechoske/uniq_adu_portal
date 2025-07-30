// Analytics Module JavaScript - Minimal using global KPI system
document.addEventListener('DOMContentLoaded', function() {
    console.log('[ANALYTICS] Module loaded');
    loadAnalyticsStats();
});

async function loadAnalyticsStats() {
    try {
        console.log('[ANALYTICS] Carregando estatísticas...');
        
        // Mostrar loading
        showLoading();
        
        // Fazer requisição para a API
        const response = await fetch('/usuarios/analytics/api/stats');
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        
        if (result.success) {
            console.log('[ANALYTICS] Estatísticas carregadas:', result);
            updateStatsCards(result);
        } else {
            console.error('[ANALYTICS] Erro ao carregar estatísticas:', result.error);
            showError('Erro ao carregar dados: ' + result.error);
        }
        
    } catch (error) {
        console.error('[ANALYTICS] Erro na requisição:', error);
        showError('Erro de conexão');
    } finally {
        hideLoading();
    }
}

function updateStatsCards(data) {
    // Atualizar valores dos KPI cards usando o sistema global
    updateKPIValue('total-access', data.total_access);
    updateKPIValue('unique-users', data.unique_users);
    updateKPIValue('logins-today', data.logins_today);
    updateKPIValue('total-logins', data.total_logins);
    
    console.log('[ANALYTICS] Cards atualizados com sucesso');
}

function updateKPIValue(elementId, value) {
    const element = document.getElementById(elementId);
    if (element) {
        // Animar o número usando a função global (se existir) ou fazer uma simples
        if (typeof animateKPINumber === 'function') {
            animateKPINumber(element, value);
        } else {
            animateNumber(element, value);
        }
    } else {
        console.warn(`[ANALYTICS] Elemento ${elementId} não encontrado`);
    }
}

function animateNumber(element, targetValue) {
    const startValue = 0;
    const duration = 1200; // 1.2 segundos
    const startTime = performance.now();
    
    function updateNumber(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        // Usar easing para animação mais suave
        const easeOutQuart = 1 - Math.pow(1 - progress, 4);
        const currentValue = Math.floor(startValue + (targetValue - startValue) * easeOutQuart);
        
        element.textContent = currentValue.toLocaleString('pt-BR');
        
        if (progress < 1) {
            requestAnimationFrame(updateNumber);
        }
    }
    
    requestAnimationFrame(updateNumber);
}

function showLoading() {
    const loadingStatus = document.getElementById('loading-status');
    if (loadingStatus) {
        loadingStatus.style.display = 'flex';
    }
    
    // Definir valores de loading nos cards
    const values = ['total-access', 'unique-users', 'logins-today', 'total-logins'];
    values.forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = '--';
            element.style.opacity = '0.5';
        }
    });
}

function hideLoading() {
    const loadingStatus = document.getElementById('loading-status');
    if (loadingStatus) {
        loadingStatus.style.display = 'none';
    }
    
    // Restaurar opacidade
    const values = ['total-access', 'unique-users', 'logins-today', 'total-logins'];
    values.forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            element.style.opacity = '1';
        }
    });
}

function showError(message) {
    console.error('[ANALYTICS]', message);
    
    // Mostrar erro nos cards
    const values = ['total-access', 'unique-users', 'logins-today', 'total-logins'];
    values.forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = '--';
            element.style.color = '#dc2626';
        }
    });
    
    // Mostrar mensagem de erro no console (pode ser expandido para UI)
    console.warn('[ANALYTICS] Para debug, verifique:', {
        message,
        time: new Date().toISOString()
    });
}

// Função para atualizar dados (pode ser chamada por um botão)
function refreshStats() {
    console.log('[ANALYTICS] Atualizando estatísticas...');
    loadAnalyticsStats();
}

// Expor funções globalmente para debug e integração
window.analyticsModule = {
    refresh: refreshStats,
    loadStats: loadAnalyticsStats,
    showError: showError,
    updateStats: updateStatsCards
};

// Auto-refresh a cada 5 minutos (300 segundos)
setInterval(() => {
    console.log('[ANALYTICS] Auto-refresh das estatísticas');
    loadAnalyticsStats();
}, 300000);
