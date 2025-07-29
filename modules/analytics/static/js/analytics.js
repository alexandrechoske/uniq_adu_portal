// Analytics Module JavaScript
document.addEventListener('DOMContentLoaded', function() {
    console.log('Analytics module loaded');
    loadAnalyticsStats();
});

async function loadAnalyticsStats() {
    try {
        console.log('Carregando estatísticas do analytics...');
        
        // Mostrar loading
        showLoading();
        
        // Fazer requisição para a API
        const response = await fetch('/usuarios/analytics/api/stats');
        const result = await response.json();
        
        if (result.success) {
            console.log('Estatísticas carregadas:', result);
            updateStatsCards(result);
        } else {
            console.error('Erro ao carregar estatísticas:', result.error);
            showError('Erro ao carregar dados');
        }
        
    } catch (error) {
        console.error('Erro na requisição:', error);
        showError('Erro de conexão');
    }
}

function updateStatsCards(data) {
    // Atualizar valores dos cartões
    updateCardValue('total-access', data.total_access);
    updateCardValue('unique-users', data.unique_users);
    updateCardValue('logins-today', data.logins_today);
    updateCardValue('total-logins', data.total_logins);
    
    // Remover loading
    hideLoading();
}

function updateCardValue(cardId, value) {
    const element = document.getElementById(cardId);
    if (element) {
        // Animar o número
        animateNumber(element, value);
    }
}

function animateNumber(element, targetValue) {
    const startValue = 0;
    const duration = 1000; // 1 segundo
    const startTime = performance.now();
    
    function updateNumber(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        const currentValue = Math.floor(startValue + (targetValue - startValue) * progress);
        element.textContent = currentValue.toLocaleString('pt-BR');
        
        if (progress < 1) {
            requestAnimationFrame(updateNumber);
        }
    }
    
    requestAnimationFrame(updateNumber);
}

function showLoading() {
    const cards = document.querySelectorAll('.stat-value');
    cards.forEach(card => {
        card.innerHTML = '<div class="spinner"></div>';
    });
}

function hideLoading() {
    // Loading será removido quando os valores forem atualizados
}

function showError(message) {
    const cards = document.querySelectorAll('.stat-value');
    cards.forEach(card => {
        card.textContent = '--';
    });
    
    // Mostrar mensagem de erro (opcional)
    console.error(message);
}

// Função para atualizar dados (pode ser chamada por um botão)
function refreshStats() {
    console.log('Atualizando estatísticas...');
    loadAnalyticsStats();
}

// Expor função globalmente para debug
window.analyticsModule = {
    refresh: refreshStats,
    loadStats: loadAnalyticsStats
};
