/**
 * CORREÇÃO: Mobile Menu e Sidebar - Versão Simplificada
 * Remove duplicações e corrige funcionalidade mobile
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('[SIDEBAR] Iniciando correção mobile...');
    
    // Elementos principais
    const sidebar = document.getElementById('sidebar');
    const mainContent = document.getElementById('main-content');
    const overlay = document.getElementById('mobile-overlay');
    
    // Botões (vamos unificar em um só)
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const mobileMenuToggle = document.getElementById('mobile-menu-toggle');
    
    // Estado da sidebar
    let isMobile = window.innerWidth < 1024;
    let sidebarExpanded = false;
    
    console.log('[SIDEBAR] Mobile detectado:', isMobile);
    
    // Função para detectar mobile
    function updateMobileState() {
        const wasMobile = isMobile;
        isMobile = window.innerWidth < 1024;
        
        if (wasMobile !== isMobile) {
            console.log('[SIDEBAR] Mudança mobile/desktop:', isMobile);
            initializeSidebar();
        }
    }
    
    // Função para inicializar sidebar baseado no dispositivo
    function initializeSidebar() {
        if (!sidebar || !mainContent) return;
        
        // Limpar todas as classes
        sidebar.classList.remove('collapsed', 'mobile-open', 'hidden');
        mainContent.classList.remove('sidebar-collapsed');
        overlay?.classList.remove('show');
        
        if (isMobile) {
            // Mobile: sidebar oculta e sem margin no content
            sidebar.classList.add('hidden');
            mainContent.style.marginLeft = '0';
            console.log('[SIDEBAR] Configurado para mobile');
        } else {
            // Desktop: sidebar sempre visível mas colapsada
            sidebar.classList.add('collapsed');
            mainContent.classList.add('sidebar-collapsed');
            mainContent.style.marginLeft = '4rem'; // w-16 equivalent
            console.log('[SIDEBAR] Configurado para desktop (colapsada)');
        }
    }
    
    // Função para toggle desktop
    function toggleDesktopSidebar() {
        if (isMobile) return;
        
        sidebarExpanded = !sidebarExpanded;
        console.log('[SIDEBAR] Toggle desktop:', sidebarExpanded);
        
        if (sidebarExpanded) {
            sidebar.classList.remove('collapsed');
            mainContent.classList.remove('sidebar-collapsed');
            mainContent.style.marginLeft = '16rem'; // w-64 equivalent
        } else {
            sidebar.classList.add('collapsed');
            mainContent.classList.add('sidebar-collapsed');
            mainContent.style.marginLeft = '4rem'; // w-16 equivalent
        }
        
        localStorage.setItem('sidebarExpanded', sidebarExpanded);
    }
    
    // Função para toggle mobile
    function toggleMobileSidebar() {
        if (!isMobile) return;
        
        const isOpen = sidebar.classList.contains('mobile-open');
        console.log('[SIDEBAR] Toggle mobile, estava aberto:', isOpen);
        
        if (isOpen) {
            // Fechar
            sidebar.classList.remove('mobile-open');
            sidebar.classList.add('hidden');
            overlay?.classList.remove('show');
        } else {
            // Abrir
            sidebar.classList.remove('hidden');
            sidebar.classList.add('mobile-open');
            overlay?.classList.add('show');
        }
    }
    
    // Event listeners unificados
    function handleMenuClick() {
        console.log('[SIDEBAR] Clique no menu, mobile:', isMobile);
        
        if (isMobile) {
            toggleMobileSidebar();
        } else {
            toggleDesktopSidebar();
        }
    }
    
    // Adicionar listeners aos botões
    sidebarToggle?.addEventListener('click', handleMenuClick);
    mobileMenuToggle?.addEventListener('click', handleMenuClick);
    
    // Fechar menu mobile ao clicar no overlay
    overlay?.addEventListener('click', function() {
        if (isMobile) {
            toggleMobileSidebar();
        }
    });
    
    // Listener para resize
    window.addEventListener('resize', function() {
        updateMobileState();
    });
    
    // Inicialização
    initializeSidebar();
    
    console.log('[SIDEBAR] Inicialização completa');
});
