// Arquivo session-handler.js simplificado
// Versão removida do sistema de cache

// Verificação de sessão simplificada
async function checkSession() {
    try {
        const response = await fetch('/paginas/check-session', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            return data.valid === true;
        }
        
        return false;
    } catch (error) {
        console.error('Erro ao verificar sessão:', error);
        return false;
    }
}

// Exporta a função para uso global
window.checkSession = checkSession;