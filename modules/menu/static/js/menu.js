/**
 * Sistema de Tabs para Menu Principal
 * Controla a navegação entre módulos (Importações, Financeiro, Ferramentas)
 */

(function() {
    'use strict';

    // Estado da aplicação
    const state = {
        activeTab: null,
        lastActiveTab: localStorage.getItem('lastMenuTab') || null
    };

    /**
     * Inicializa o sistema de tabs
     */
    function init() {
        console.log('🚀 Inicializando sistema de tabs do menu');
        
        const tabs = document.querySelectorAll('.menu-tab');
        
        if (!tabs.length) {
            console.warn('⚠️ Nenhuma tab encontrada');
            return;
        }

        // Adicionar event listeners nas tabs
        tabs.forEach(tab => {
            tab.addEventListener('click', handleTabClick);
        });

        // Restaurar última tab ativa (se existir e estiver disponível)
        if (state.lastActiveTab) {
            const lastTab = document.querySelector(`.menu-tab[data-tab="${state.lastActiveTab}"]`);
            if (lastTab) {
                activateTab(state.lastActiveTab);
                console.log(`📌 Restaurando última tab ativa: ${state.lastActiveTab}`);
                return;
            }
        }

        // Se não houver última tab, ativar a primeira
        const firstTab = tabs[0];
        const firstTabName = firstTab.getAttribute('data-tab');
        activateTab(firstTabName);
        console.log(`✅ Tab inicial ativada: ${firstTabName}`);
    }

    /**
     * Handler para clique em tab
     * @param {Event} event 
     */
    function handleTabClick(event) {
        const tab = event.currentTarget;
        const tabName = tab.getAttribute('data-tab');
        
        if (state.activeTab === tabName) {
            console.log(`ℹ️ Tab já ativa: ${tabName}`);
            return;
        }

        activateTab(tabName);
        console.log(`🔄 Tab alterada para: ${tabName}`);
    }

    /**
     * Ativa uma tab específica
     * @param {string} tabName - Nome da tab (importacoes, financeiro, ferramentas)
     */
    function activateTab(tabName) {
        // Remover classe active de todas as tabs
        document.querySelectorAll('.menu-tab').forEach(tab => {
            tab.classList.remove('active');
        });

        // Remover classe active de todos os conteúdos
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });

        // Adicionar classe active na tab clicada
        const activeTab = document.querySelector(`.menu-tab[data-tab="${tabName}"]`);
        if (activeTab) {
            activeTab.classList.add('active');
        }

        // Adicionar classe active no conteúdo correspondente
        const activeContent = document.querySelector(`.tab-content[data-content="${tabName}"]`);
        if (activeContent) {
            activeContent.classList.add('active');
            
            // Animação de entrada suave
            activeContent.style.opacity = '0';
            activeContent.style.transform = 'translateY(10px)';
            
            requestAnimationFrame(() => {
                activeContent.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
                activeContent.style.opacity = '1';
                activeContent.style.transform = 'translateY(0)';
            });
        }

        // Atualizar estado
        state.activeTab = tabName;
        
        // Salvar no localStorage para persistir entre sessões
        localStorage.setItem('lastMenuTab', tabName);

        // Scroll suave para o topo do conteúdo
        const mainContent = document.querySelector('.main-content');
        if (mainContent) {
            mainContent.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }

        // Disparar evento customizado (para analytics ou outras integrações)
        window.dispatchEvent(new CustomEvent('menuTabChanged', { 
            detail: { tabName, timestamp: Date.now() }
        }));
    }

    /**
     * API pública para controle externo das tabs
     */
    window.MenuTabs = {
        /**
         * Ativa uma tab programaticamente
         * @param {string} tabName 
         */
        activateTab: function(tabName) {
            const tab = document.querySelector(`.menu-tab[data-tab="${tabName}"]`);
            if (!tab) {
                console.error(`❌ Tab não encontrada: ${tabName}`);
                return false;
            }
            activateTab(tabName);
            return true;
        },

        /**
         * Retorna a tab atualmente ativa
         * @returns {string|null}
         */
        getActiveTab: function() {
            return state.activeTab;
        },

        /**
         * Retorna lista de todas as tabs disponíveis
         * @returns {Array<string>}
         */
        getAvailableTabs: function() {
            const tabs = document.querySelectorAll('.menu-tab');
            return Array.from(tabs).map(tab => tab.getAttribute('data-tab'));
        },

        /**
         * Conta quantos cards existem em cada tab
         * @returns {Object}
         */
        getTabCounts: function() {
            const counts = {};
            document.querySelectorAll('.tab-content').forEach(content => {
                const tabName = content.getAttribute('data-content');
                const cardCount = content.querySelectorAll('.module-card').length;
                counts[tabName] = cardCount;
            });
            return counts;
        }
    };

    // Aguardar DOM estar pronto
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    console.log('✅ Sistema de tabs do menu carregado');
})();

/**
 * Analytics de uso das tabs (opcional)
 */
window.addEventListener('menuTabChanged', function(event) {
    const { tabName, timestamp } = event.detail;
    console.log(`📊 Analytics: Tab "${tabName}" acessada em ${new Date(timestamp).toLocaleTimeString()}`);
    
    // Aqui você pode integrar com Google Analytics, Mixpanel, etc.
    // Exemplo:
    // if (typeof gtag !== 'undefined') {
    //     gtag('event', 'menu_tab_change', {
    //         'event_category': 'Navigation',
    //         'event_label': tabName,
    //         'value': 1
    //     });
    // }
});

/**
 * Atalhos de teclado (opcional - para power users)
 */
document.addEventListener('keydown', function(event) {
    // Ctrl/Cmd + 1/2/3 para mudar de tab
    if ((event.ctrlKey || event.metaKey) && !event.shiftKey && !event.altKey) {
        const tabs = window.MenuTabs.getAvailableTabs();
        const keyNumber = parseInt(event.key);
        
        if (keyNumber >= 1 && keyNumber <= tabs.length) {
            event.preventDefault();
            const targetTab = tabs[keyNumber - 1];
            window.MenuTabs.activateTab(targetTab);
            console.log(`⌨️ Atalho de teclado: Ctrl+${keyNumber} → ${targetTab}`);
        }
    }
});

/**
 * Debug helper - mostra informações do sistema de tabs no console
 */
if (window.location.hostname === 'localhost' || window.location.hostname === '192.168.0.75') {
    setTimeout(() => {
        console.log('🔍 Debug Info - Menu Tabs:');
        console.log('  Tabs disponíveis:', window.MenuTabs.getAvailableTabs());
        console.log('  Tab ativa:', window.MenuTabs.getActiveTab());
        console.log('  Contagem de cards:', window.MenuTabs.getTabCounts());
        console.log('  Última tab salva:', localStorage.getItem('lastMenuTab'));
    }, 500);
}
