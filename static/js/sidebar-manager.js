/**
 * Gerenciador de Sidebar - Versão simplificada sem sistema dinâmico
 */

document.addEventListener('DOMContentLoaded', function() {
    // Sidebar toggle functionality - SEMPRE INICIA COLAPSADA
    let sidebarExpanded = false; // Sempre inicia colapsada
    
    function toggleSidebar() {
        const sidebar = document.getElementById('sidebar');
        const mainContent = document.getElementById('main-content');
        
        sidebarExpanded = !sidebarExpanded;
        
        if (sidebarExpanded) {
            sidebar.classList.remove('collapsed');
            mainContent.classList.remove('sidebar-collapsed');
        } else {
            sidebar.classList.add('collapsed');
            mainContent.classList.add('sidebar-collapsed');
        }
        
        // Store preference in localStorage
        localStorage.setItem('sidebarExpanded', sidebarExpanded);
    }
    
    // Apply initial state - SEMPRE COLAPSADA
    const sidebar = document.getElementById('sidebar');
    const mainContent = document.getElementById('main-content');
    
    sidebar.classList.add('collapsed');
    mainContent.classList.add('sidebar-collapsed');
    
    // Add event listener to hamburger button
    document.getElementById('sidebar-toggle')?.addEventListener('click', toggleSidebar);
    
    // Mobile menu functionality
    function toggleMobileMenu() {
        const sidebar = document.getElementById('sidebar');
        const overlay = document.getElementById('mobile-overlay');
        const isOpen = sidebar.classList.contains('mobile-open');
        
        if (isOpen) {
            sidebar.classList.remove('mobile-open');
            overlay.classList.remove('show');
        } else {
            sidebar.classList.add('mobile-open');
            overlay.classList.add('show');
        }
    }
    
    document.getElementById('mobile-menu-toggle')?.addEventListener('click', toggleMobileMenu);
    
    // Close mobile menu when clicking overlay
    document.getElementById('mobile-overlay')?.addEventListener('click', toggleMobileMenu);
    
    // Hide mobile menu on window resize
    window.addEventListener('resize', function() {
        const sidebar = document.getElementById('sidebar');
        const overlay = document.getElementById('mobile-overlay');
        
        if (window.innerWidth >= 1024) {
            sidebar.classList.remove('mobile-open');
            sidebar.classList.remove('hidden');
            overlay.classList.remove('show');
        } else {
            sidebar.classList.remove('mobile-open');
            sidebar.classList.add('hidden');
            overlay.classList.remove('show');
        }
    });
});