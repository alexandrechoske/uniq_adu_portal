// Sistema de gerenciamento de usuários
document.addEventListener('DOMContentLoaded', function() {
    console.log('[DEBUG] DOM carregado, inicializando sistema de usuários');

    // === ELEMENTOS DOM ===
    const searchInput = document.getElementById('search-input');
    const roleFilter = document.getElementById('role-filter');
    const empresaFilter = document.getElementById('empresa-filter');
    const clearButton = document.getElementById('clear-filters');
    
    console.log('[DEBUG] Elementos encontrados:', {
        searchInput,
        roleFilter,
        empresaFilter,
        clearButton
    });

    // === MODAL DE EXCLUSÃO ===
    let currentDeleteUserId = null;
    let currentDeleteUserName = null;

    window.openDeleteModal = function(userId) {
        console.log('[DEBUG] Abrindo modal de exclusão para usuário:', userId);
        
        currentDeleteUserId = userId;
        
        // Buscar informações do usuário na tabela
        const userRow = document.querySelector(`tr[data-user-id="${userId}"]`);
        if (userRow) {
            const userName = userRow.dataset.name || 'Usuário desconhecido';
            const userEmail = userRow.dataset.email || '';
            const userRole = userRow.dataset.role || '';
            
            currentDeleteUserName = userName;
            
            // Atualizar informações no modal
            document.getElementById('delete-user-name').textContent = userName;
            document.getElementById('delete-user-email').textContent = userEmail;
            document.getElementById('delete-user-role').textContent = getRoleDisplayName(userRole);
            
            // Configurar formulário
            const deleteForm = document.getElementById('deleteForm');
            if (deleteForm) {
                deleteForm.action = `/usuarios/${userId}/deletar`;
                console.log('[DEBUG] Action do formulário configurado:', deleteForm.action);
            }
        }
        
        // Mostrar modal
        const modal = document.getElementById('deleteModal');
        if (modal) {
            modal.classList.add('show');
            modal.style.display = 'flex';
            
            // Focar no botão de cancelar para acessibilidade
            const cancelButton = modal.querySelector('.btn-outline');
            if (cancelButton) {
                setTimeout(() => cancelButton.focus(), 100);
            }
        }
    };

    window.closeDeleteModal = function() {
        console.log('[DEBUG] Fechando modal de exclusão');
        
        const modal = document.getElementById('deleteModal');
        if (modal) {
            modal.classList.remove('show');
            modal.style.display = 'none';
        }
        
        currentDeleteUserId = null;
        currentDeleteUserName = null;
    };

    // === SISTEMA DE FILTROS ===
    function filterUsers() {
        if (!searchInput || !roleFilter || !empresaFilter) {
            console.warn('[DEBUG] Elementos de filtro não encontrados');
            return;
        }

        const searchTerm = searchInput.value.toLowerCase();
        const selectedRole = roleFilter.value;
        const empresaTerm = empresaFilter.value.toLowerCase();
        
        console.log('[DEBUG] Filtrando com:', { searchTerm, selectedRole, empresaTerm });
        
        // Filtrar todas as linhas de usuários
        const userRows = document.querySelectorAll('.user-row');
        const sections = document.querySelectorAll('.users-section');
        
        let visibleCounts = {
            admin: 0,
            interno_unique: 0,
            cliente_unique: 0
        };
        
        userRows.forEach(row => {
            const name = (row.dataset.name || '').toLowerCase();
            const email = (row.dataset.email || '').toLowerCase();
            const role = row.dataset.role || '';
            const empresas = (row.dataset.empresas || '').toLowerCase();
            
            const matchesSearch = !searchTerm || 
                                name.includes(searchTerm) || 
                                email.includes(searchTerm);
            const matchesRole = !selectedRole || role === selectedRole;
            const matchesEmpresa = !empresaTerm || empresas.includes(empresaTerm);
            
            const isVisible = matchesSearch && matchesRole && matchesEmpresa;
            
            row.style.display = isVisible ? '' : 'none';
            
            if (isVisible) {
                visibleCounts[role] = (visibleCounts[role] || 0) + 1;
            }
        });
        
        // Atualizar contadores das seções
        updateSectionCounts(visibleCounts);
        
        // Mostrar/ocultar seções vazias
        updateSectionVisibility(sections, visibleCounts, selectedRole, searchTerm, empresaTerm);
    }

    function updateSectionCounts(visibleCounts) {
        const counters = {
            'admin-section-count': visibleCounts.admin || 0,
            'interno-section-count': visibleCounts.interno_unique || 0,
            'cliente-section-count': visibleCounts.cliente_unique || 0
        };

        Object.entries(counters).forEach(([id, count]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = `${count} usuário${count !== 1 ? 's' : ''}`;
            }
        });
    }

    function updateSectionVisibility(sections, visibleCounts, selectedRole, searchTerm, empresaTerm) {
        sections.forEach(section => {
            const role = section.dataset.role;
            const hasVisibleUsers = role && visibleCounts[role] > 0;
            const shouldShow = !selectedRole || selectedRole === role;
            
            if (!hasVisibleUsers && shouldShow && (searchTerm || empresaTerm)) {
                // Mostrar seção com mensagem de nenhum resultado
                section.style.display = 'block';
                showNoResultsMessage(section);
            } else if (hasVisibleUsers || (!searchTerm && !empresaTerm && !selectedRole)) {
                // Mostrar seção normalmente
                section.style.display = shouldShow ? 'block' : 'none';
                hideNoResultsMessage(section);
            } else {
                // Ocultar seção
                section.style.display = 'none';
                hideNoResultsMessage(section);
            }
        });
    }

    function showNoResultsMessage(section) {
        const tbody = section.querySelector('tbody');
        if (tbody && !tbody.querySelector('.no-results')) {
            const noResultsRow = document.createElement('tr');
            noResultsRow.className = 'no-results';
            noResultsRow.innerHTML = `
                <td colspan="4" class="empty-state">
                    <i class="mdi mdi-filter-remove"></i>
                    <p>Nenhum usuário encontrado com os filtros aplicados</p>
                </td>
            `;
            tbody.appendChild(noResultsRow);
        }
    }

    function hideNoResultsMessage(section) {
        const noResults = section.querySelector('.no-results');
        if (noResults) {
            noResults.remove();
        }
    }

    // === UTILITÁRIOS ===
    function getRoleDisplayName(role) {
        const roleNames = {
            'admin': 'Administrador',
            'interno_unique': 'Interno Unique',
            'cliente_unique': 'Cliente Unique'
        };
        return roleNames[role] || role;
    }

    function showNotification(message, type = 'info', duration = 3000) {
        // Implementação simples de notificação
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 20px;
            border-radius: 8px;
            color: white;
            font-weight: 500;
            z-index: 9999;
            animation: slideInRight 0.3s ease;
        `;
        
        const colors = {
            info: '#3b82f6',
            success: '#10b981',
            warning: '#f59e0b',
            error: '#ef4444'
        };
        
        notification.style.background = colors[type] || colors.info;
        
        document.body.appendChild(notification);
        
        if (duration > 0) {
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.style.animation = 'slideOutRight 0.3s ease';
                    setTimeout(() => {
                        notification.remove();
                    }, 300);
                }
            }, duration);
        }
        
        return notification;
    }

    // === EVENT LISTENERS ===
    
    // Filtros
    if (searchInput) {
        searchInput.addEventListener('input', filterUsers);
    }
    
    if (roleFilter) {
        roleFilter.addEventListener('change', filterUsers);
    }
    
    if (empresaFilter) {
        empresaFilter.addEventListener('input', filterUsers);
    }
    
    // Limpar filtros
    if (clearButton) {
        clearButton.addEventListener('click', function() {
            if (searchInput) searchInput.value = '';
            if (roleFilter) roleFilter.value = '';
            if (empresaFilter) empresaFilter.value = '';
            filterUsers();
        });
    }
    
    // Botão de atualizar
    const refreshButton = document.querySelector('a[href*="/usuarios/refresh"]');
    if (refreshButton) {
        refreshButton.addEventListener('click', function(e) {
            const originalContent = this.innerHTML;
            this.innerHTML = '<i class="mdi mdi-loading mdi-spin"></i> Atualizando...';
            this.style.pointerEvents = 'none';
            this.style.opacity = '0.75';
            
            // Restaurar após um tempo (caso a página não recarregue)
            setTimeout(() => {
                this.innerHTML = originalContent;
                this.style.pointerEvents = '';
                this.style.opacity = '';
            }, 10000);
        });
    }
    
    // Modal - fechar ao clicar fora
    const deleteModal = document.getElementById('deleteModal');
    if (deleteModal) {
        deleteModal.addEventListener('click', function(e) {
            if (e.target === this) {
                closeDeleteModal();
            }
        });
    }
    
    // Modal - fechar com ESC
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeDeleteModal();
        }
    });
    
    // Formulário de exclusão - debug e feedback
    const deleteForm = document.getElementById('deleteForm');
    if (deleteForm) {
        console.log('[DEBUG] Formulário de exclusão encontrado');
        
        deleteForm.addEventListener('submit', function(e) {
            console.log('[DEBUG] Formulário de exclusão enviado');
            console.log('[DEBUG] Action:', this.action);
            console.log('[DEBUG] Method:', this.method);
            
            // Mostrar feedback de loading
            const submitButton = this.querySelector('button[type="submit"]');
            if (submitButton) {
                const originalContent = submitButton.innerHTML;
                submitButton.innerHTML = '<i class="mdi mdi-loading mdi-spin"></i> Excluindo...';
                submitButton.disabled = true;
            }
            
            // Mostrar notificação
            showNotification('Excluindo usuário...', 'info', 0);
        });
    } else {
        console.error('[DEBUG] Formulário de exclusão NÃO encontrado!');
    }
    
    // Debug dos botões de exclusão
    const deleteButtons = document.querySelectorAll('button[onclick*="openDeleteModal"]');
    console.log('[DEBUG] Botões de exclusão encontrados:', deleteButtons.length);
    
    deleteButtons.forEach((button, index) => {
        console.log(`[DEBUG] Botão ${index + 1}:`, button.getAttribute('onclick'));
        
        button.addEventListener('click', function(e) {
            console.log(`[DEBUG] Botão de exclusão ${index + 1} clicado`);
        });
    });

    // === INICIALIZAÇÃO ===
    console.log('[DEBUG] Sistema de usuários inicializado com sucesso');
    
    // Aplicar filtros iniciais se houver valores
    if (searchInput?.value || roleFilter?.value || empresaFilter?.value) {
        filterUsers();
    }
});
