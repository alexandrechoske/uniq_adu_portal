/**
 * Teste do Sistema de Cache do Menu
 * Este arquivo testa todas as funcionalidades do sistema de cache
 */

console.log('[MenuTest] Iniciando testes do sistema de cache...');

// Função para executar testes do sistema de cache
function testMenuCacheSystem() {
    console.log('[MenuTest] ===========================================');
    console.log('[MenuTest] INICIANDO TESTES DO SISTEMA DE CACHE');
    console.log('[MenuTest] ===========================================');
    
    // Teste 1: Verificar se o sistema de cache foi carregado
    console.log('[MenuTest] Teste 1: Verificando carregamento do sistema...');
    if (window.menuCache) {
        console.log('[MenuTest] ✅ Sistema de cache carregado com sucesso');
        console.log('[MenuTest] Propriedades disponíveis:', Object.keys(window.menuCache));
    } else {
        console.error('[MenuTest] ❌ Sistema de cache não foi carregado!');
        return false;
    }
    
    // Teste 2: Verificar localStorage
    console.log('[MenuTest] Teste 2: Verificando localStorage...');
    try {
        localStorage.setItem('test_cache', 'test_value');
        const testValue = localStorage.getItem('test_cache');
        localStorage.removeItem('test_cache');
        
        if (testValue === 'test_value') {
            console.log('[MenuTest] ✅ localStorage funcionando corretamente');
        } else {
            console.warn('[MenuTest] ⚠️ Problema com localStorage');
        }
    } catch (error) {
        console.error('[MenuTest] ❌ localStorage não disponível:', error);
    }
    
    // Teste 3: Verificar cache existente
    console.log('[MenuTest] Teste 3: Verificando cache existente...');
    const menuCache = window.menuCache.getFromCache(window.menuCache.CACHE_KEY_MENU);
    const sessionCache = window.menuCache.getFromCache(window.menuCache.CACHE_KEY_SESSION);
    
    console.log('[MenuTest] Cache do menu:', menuCache ? 'Encontrado' : 'Não encontrado');
    console.log('[MenuTest] Cache da sessão:', sessionCache ? 'Encontrado' : 'Não encontrado');
    
    // Teste 4: Teste de validação de sessão
    console.log('[MenuTest] Teste 4: Testando validação de sessão...');
    window.menuCache.validateSession()
        .then(isValid => {
            console.log('[MenuTest] Resultado da validação de sessão:', isValid ? '✅ Válida' : '❌ Inválida');
        })
        .catch(error => {
            console.error('[MenuTest] Erro na validação de sessão:', error);
        });
    
    // Teste 5: Teste de carregamento de menu
    console.log('[MenuTest] Teste 5: Testando carregamento de menu...');
    window.menuCache.loadMenu()
        .then(success => {
            console.log('[MenuTest] Resultado do carregamento de menu:', success ? '✅ Sucesso' : '❌ Falha');
            
            // Verificar se o menu foi renderizado
            const sidebarNav = document.getElementById('sidebar-nav');
            if (sidebarNav && sidebarNav.children.length > 0) {
                console.log('[MenuTest] ✅ Menu renderizado com', sidebarNav.children.length, 'itens');
            } else {
                console.warn('[MenuTest] ⚠️ Menu não foi renderizado ou está vazio');
            }
        })
        .catch(error => {
            console.error('[MenuTest] Erro no carregamento de menu:', error);
        });
    
    console.log('[MenuTest] ===========================================');
    console.log('[MenuTest] TESTES CONCLUÍDOS');
    console.log('[MenuTest] ===========================================');
    
    return true;
}

// Função para testar o problema específico do menu sumindo
function testMenuPersistence() {
    console.log('[MenuTest] ===========================================');
    console.log('[MenuTest] TESTE DE PERSISTÊNCIA DO MENU');
    console.log('[MenuTest] ===========================================');
    
    let testCount = 0;
    const maxTests = 5;
    
    function runPersistenceTest() {
        testCount++;
        console.log(`[MenuTest] Teste de persistência ${testCount}/${maxTests}`);
        
        // Verificar se o menu está visível
        const sidebarNav = document.getElementById('sidebar-nav');
        if (sidebarNav) {
            const menuItems = sidebarNav.querySelectorAll('a');
            console.log(`[MenuTest] Menu tem ${menuItems.length} itens visíveis`);
            
            if (menuItems.length === 0) {
                console.warn('[MenuTest] ⚠️ Menu está vazio! Tentando recarregar...');
                if (window.menuCache) {
                    window.menuCache.loadMenu();
                }
            } else {
                console.log('[MenuTest] ✅ Menu está carregado corretamente');
            }
        } else {
            console.error('[MenuTest] ❌ Elemento sidebar-nav não encontrado!');
        }
        
        if (testCount < maxTests) {
            setTimeout(runPersistenceTest, 2000); // Testa a cada 2 segundos
        } else {
            console.log('[MenuTest] Teste de persistência concluído');
        }
    }
    
    // Iniciar teste
    runPersistenceTest();
}

// Função para monitorar o status do sistema
function monitorCacheSystem() {
    console.log('[MenuTest] Iniciando monitoramento do sistema de cache...');
    
    setInterval(() => {
        if (window.menuCache) {
            const sessionValid = window.menuCache.sessionValid;
            const menuLoaded = window.menuCache.menuLoaded;
            const lastCheck = new Date(window.menuCache.lastSessionCheck).toLocaleTimeString();
            
            console.log('[MenuTest] Status:', {
                sessaoValida: sessionValid,
                menuCarregado: menuLoaded,
                ultimaVerificacao: lastCheck
            });
        }
    }, 30000); // A cada 30 segundos
}

// Executar testes quando a página carregar
document.addEventListener('DOMContentLoaded', function() {
    console.log('[MenuTest] Página carregada, aguardando inicialização do cache...');
    
    // Aguardar o sistema de cache estar pronto
    setTimeout(() => {
        if (window.menuCache) {
            testMenuCacheSystem();
            
            // Aguardar um pouco antes dos outros testes
            setTimeout(() => {
                testMenuPersistence();
                monitorCacheSystem();
            }, 2000);
        } else {
            console.error('[MenuTest] Sistema de cache não foi carregado após timeout!');
        }
    }, 1000);
});

// Adicionar comandos de teste ao console global para uso manual
window.testMenuCache = testMenuCacheSystem;
window.testMenuPersistence = testMenuPersistence;
window.monitorCache = monitorCacheSystem;

// Função para limpar todo o cache e reiniciar
window.resetMenuCache = function() {
    console.log('[MenuTest] Resetando sistema de cache...');
    if (window.menuCache) {
        window.menuCache.clearCache();
        setTimeout(() => {
            window.menuCache.initialize();
        }, 100);
    }
};

console.log('[MenuTest] Sistema de testes carregado.');
console.log('[MenuTest] Comandos disponíveis no console:');
console.log('[MenuTest] - testMenuCache(): Executa testes completos');
console.log('[MenuTest] - testMenuPersistence(): Testa persistência do menu');
console.log('[MenuTest] - monitorCache(): Inicia monitoramento');
console.log('[MenuTest] - resetMenuCache(): Reseta o cache');