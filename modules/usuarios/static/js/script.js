/**
 * MÓDULO DE GERENCIAMENTO DE USUÁRIOS - REDESIGN 2025
 * Sistema moderno com KPIs e organização por perfil
 * 
 * Funcionalidades:
 * - CRUD de usuários
 * - KPIs em tempo real
 * - Organização por perfil/role
 * - Cards modernos em vez de tabela
 * - Filtros avançados
 * - Interface responsiva
 */

// =================================
// CONFIGURAÇÕES E CONSTANTES
// =================================

const CONFIG = {
    API_BASE_URL: '/usuarios',
    DEBOUNCE_DELAY: 300,
    MAX_RETRIES: 3,
    RETRY_DELAY: 1000
};

const NOTIFICATION_TYPES = {
    SUCCESS: 'success',
    ERROR: 'error',
    WARNING: 'warning',
    INFO: 'info'
};

const MODAL_MODES = {
    CREATE: 'create',
    EDIT: 'edit'
};

const ROLE_CONFIG = {
    admin: {
        label: 'Administrador',
        icon: 'mdi-shield-crown',
        color: 'success',
        description: 'Acesso total ao sistema',
        perfil_principal_allowed: ['master_admin']
    },
    interno_unique: {
        label: 'Equipe Interna',
        icon: 'mdi-account-tie',
        color: 'info',
        description: 'Colaboradores da Unique',
        perfil_principal_allowed: ['basico', 'admin_operacao', 'admin_financeiro']
    },
    cliente_unique: {
        label: 'Cliente',
        icon: 'mdi-domain',
        color: 'warning',
        description: 'Empresas clientes',
        perfil_principal_allowed: ['basico']
    }
};

const PERFIL_PRINCIPAL_CONFIG = {
    basico: {
        label: 'Básico',
        description: 'Acesso básico para consulta',
        icon: 'mdi-account'
    },
    master_admin: {
        label: 'Master Admin',
        description: 'Administração completa do sistema',
        icon: 'mdi-shield-crown'
    },
    admin_operacao: {
        label: 'Admin Operacional',
        description: 'Administra módulos operacionais (Importação, Consultoria, Exportação)',
        icon: 'mdi-ship'
    },
    admin_financeiro: {
        label: 'Admin Financeiro',
        description: 'Administra apenas o módulo financeiro',
        icon: 'mdi-cash-multiple'
    }
};

// =================================
// ESTADO GLOBAL DA APLICAÇÃO
// =================================

let appState = {
    users: [],
    filteredUsers: [],
    currentUser: null,
    currentMode: null,
    originalEmpresas: [],
    originalWhatsapp: [],
    searchTimeout: null,
    isLoading: false,
    empresaSearchTimeout: null,
    activeFilters: {
        search: '',
        role: '',
        status: ''
    },
    // Novo estado para perfis
    perfis: {
        available: [],
        selected: [],
        searchTimeout: null
    }
};

// =================================
// ELEMENTOS DOM PRINCIPAIS
// =================================

let elements = {};

// =================================
// INICIALIZAÇÃO
// =================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('[USUARIOS] Inicializando módulo de usuários redesenhado...');
    
    initializeElements();
    initializeEventListeners();
    loadUsersData();
    
    console.log('[USUARIOS] Módulo inicializado com sucesso');
});

/**
 * Inicializa referências dos elementos DOM
 */
function initializeElements() {
    elements = {
        // Buttons
        btnNovoUsuario: document.getElementById('btn-novo-usuario'),
        btnNovoUsuarioEmpty: document.getElementById('btn-novo-usuario-empty'),
        btnRefresh: document.getElementById('btn-refresh'),
        btnCloseModal: document.getElementById('btn-close-modal'),
        btnSave: document.getElementById('btn-save'),
        btnCancel: document.getElementById('btn-cancel'),
        // Header buttons
        btnCancelHeader: document.getElementById('btn-cancel-header'),
        btnSaveHeader: document.getElementById('btn-save-header'),
        
        // Modal
        modalUsuario: document.getElementById('modal-usuario'),
        modalTitle: document.getElementById('modal-title'),
        modalDeleteConfirm: document.getElementById('modal-delete-confirm'),
        
        // View Modal
        modalViewUsuario: document.getElementById('modal-view-usuario'),
        viewModalTitle: document.getElementById('view-modal-title'),
        userDetailsContent: document.getElementById('user-details-content'),
        btnEditFromView: document.getElementById('btn-edit-from-view'),
        btnCloseView: document.getElementById('btn-close-view'),
        
        // Form
        formUsuario: document.getElementById('form-usuario'),
        formLoading: document.getElementById('form-loading'),
        
        // Search and Filters
        searchInput: document.getElementById('search-usuarios'),
        filterPerfil: document.getElementById('filter-perfil'),
        filterStatus: document.getElementById('filter-status'),
        
        // KPI Elements
        kpiTotalUsuarios: document.getElementById('kpi-total-usuarios'),
        kpiAdmin: document.getElementById('kpi-admin'),
        kpiInterno: document.getElementById('kpi-interno'),
        kpiClientes: document.getElementById('kpi-clientes'),
        kpiAtivos: document.getElementById('kpi-ativos'),
        
        // Sections
        sectionAdmin: document.getElementById('section-admin'),
        sectionInterno: document.getElementById('section-interno'),
        sectionClientes: document.getElementById('section-clientes'),
        
        // Table Bodies (replacing grids)
        tbodyAdmin: document.getElementById('tbody-admin'),
        tbodyInterno: document.getElementById('tbody-interno'),
        tbodyClientes: document.getElementById('tbody-clientes'),
        
        // Tables
        tableAdmin: document.getElementById('table-admin'),
        tableInterno: document.getElementById('table-interno'),
        tableClientes: document.getElementById('table-clientes'),
        
        // Empty States
        emptyAdmin: document.getElementById('empty-admin'),
        emptyInterno: document.getElementById('empty-interno'),
        emptyClientes: document.getElementById('empty-clientes'),
        
        // Counts
        countAdmin: document.getElementById('count-admin'),
        countInterno: document.getElementById('count-interno'),
        countClientes: document.getElementById('count-clientes'),
        
        // Empty State
        emptyState: document.getElementById('empty-state'),
        
        // Notification
        notificationArea: document.getElementById('notification-area'),
        
        // User Card Template
        userCardTemplate: document.getElementById('user-card-template'),
        
        // Perfis Elements
        perfisSearch: document.getElementById('perfis-search'),
        perfisList: document.getElementById('perfis-list'),
        perfisEmpty: document.getElementById('perfis-empty'),
        perfisSelectedCount: document.getElementById('perfis-selected-count'),
        
        // Collapsible Headers
        collapsibleHeaders: document.querySelectorAll('.collapsible-header')
    };
    
    // DEBUG: Verificar elementos críticos
    console.log('[USUARIOS] DEBUG - Elementos encontrados:', {
        modalDeleteConfirm: !!elements.modalDeleteConfirm,
        modalUsuario: !!elements.modalUsuario,
        userCardTemplate: !!elements.userCardTemplate,
        tbodyAdmin: !!elements.tbodyAdmin,
        tbodyInterno: !!elements.tbodyInterno,
        tbodyClientes: !!elements.tbodyClientes
    });
    
    // Verificar se algum elemento crítico está faltando
    if (!elements.modalDeleteConfirm) {
        console.error('[USUARIOS] ERRO: Modal de exclusão não encontrado!');
    }
    if (!elements.userCardTemplate) {
        console.error('[USUARIOS] ERRO: Template de card não encontrado!');
    }
}

/**
 * Inicializa todos os event listeners
 */
function initializeEventListeners() {
    // Botões principais
    if (elements.btnNovoUsuario) {
        elements.btnNovoUsuario.addEventListener('click', openModalForCreate);
    }
    
    if (elements.btnNovoUsuarioEmpty) {
        elements.btnNovoUsuarioEmpty.addEventListener('click', openModalForCreate);
    }
    
    if (elements.btnRefresh) {
        elements.btnRefresh.addEventListener('click', refreshData);
    }
    
    // Modal
    if (elements.btnCloseModal) {
        elements.btnCloseModal.addEventListener('click', closeModal);
    }
    
    if (elements.btnCancel) {
        elements.btnCancel.addEventListener('click', closeModal);
    }
    
    // Header buttons (duplicated for convenience)
    if (elements.btnCancelHeader) {
        elements.btnCancelHeader.addEventListener('click', closeModal);
    }
    
    if (elements.btnSaveHeader) {
        elements.btnSaveHeader.addEventListener('click', function(e) {
            e.preventDefault();
            // Trigger form submission
            if (elements.formUsuario) {
                elements.formUsuario.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
            }
        });
    }
    
    if (elements.modalUsuario) {
        elements.modalUsuario.addEventListener('click', function(e) {
            if (e.target === elements.modalUsuario) {
                closeModal();
            }
        });
    }
    
    // View Modal
    if (elements.btnCloseView) {
        elements.btnCloseView.addEventListener('click', closeViewModal);
    }
    
    if (elements.btnEditFromView) {
        elements.btnEditFromView.addEventListener('click', handleEditFromView);
    }
    
    if (elements.modalViewUsuario) {
        elements.modalViewUsuario.addEventListener('click', function(e) {
            if (e.target === elements.modalViewUsuario) {
                closeViewModal();
            }
        });
    }
    
    // Formulário
    if (elements.formUsuario) {
        elements.formUsuario.addEventListener('submit', handleFormSubmit);
    }
    
    // Search e Filters
    if (elements.searchInput) {
        elements.searchInput.addEventListener('input', handleSearchInput);
    }
    
    if (elements.filterPerfil) {
        elements.filterPerfil.addEventListener('change', handleFilterChange);
    }
    
    if (elements.filterStatus) {
        elements.filterStatus.addEventListener('change', handleFilterChange);
    }
    
    // Role change no formulário
    const roleSelect = document.getElementById('role');
    if (roleSelect) {
        roleSelect.addEventListener('change', handleRoleChange);
    }
    
    // Modal de exclusão - CORRIGIDO
    const btnCancelDelete = document.getElementById('btn-cancel-delete');
    if (btnCancelDelete) {
        btnCancelDelete.addEventListener('click', hideDeleteModal);
    }
    
    // Empresas e WhatsApp
    initializeEmpresasEventListeners();
    initializeWhatsappEventListeners();
    
    // Perfis e Seções Colapsáveis
    initializePerfisEventListeners();
    initializeCollapsibleSections();
    
    // ESC para fechar modal - MELHORADO
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            if (elements.modalDeleteConfirm && !elements.modalDeleteConfirm.classList.contains('hidden')) {
                hideDeleteModal();
            } else if (elements.modalViewUsuario && !elements.modalViewUsuario.classList.contains('hidden')) {
                closeViewModal();
            } else if (elements.modalUsuario && !elements.modalUsuario.classList.contains('hidden')) {
                closeModal();
            }
        }
    });
}

/**
 * Carrega dados dos usuários
 */
async function loadUsersData() {
    try {
        showLoading(true);
        
        const response = await apiRequest('/api/usuarios');
        console.log('[USUARIOS] Resposta bruta da API:', response);
        
        // Verificar estrutura da resposta
        let users = [];
        
        if (Array.isArray(response)) {
            // Resposta é array direto
            users = response;
            console.log('[USUARIOS] Resposta é array direto com', users.length, 'usuários');
        } else if (response.success && response.data) {
            // Resposta é objeto com success/data
            users = response.data;
            console.log('[USUARIOS] Resposta tem success/data com', users.length, 'usuários');
        } else if (response.data && Array.isArray(response.data)) {
            // Resposta tem data mas sem success
            users = response.data;
            console.log('[USUARIOS] Resposta tem data sem success com', users.length, 'usuários');
        } else {
            // Fallback - tentar usar response diretamente
            users = response || [];
            console.log('[USUARIOS] Usando fallback com', users.length, 'usuários');
        }
        
        console.log('[USUARIOS] Usuários processados:', users);
        
        appState.users = users;
        updateKPIs();
        filterAndDisplayUsers();
        
    } catch (error) {
        console.error('[USUARIOS] Erro ao carregar dados:', error);
        showNotification('Erro ao carregar usuários: ' + error.message, NOTIFICATION_TYPES.ERROR);
        appState.users = [];
        updateKPIs();
        showEmptyState();
    } finally {
        showLoading(false);
    }
}

/**
 * Atualiza KPIs com base nos dados
 */
function updateKPIs() {
    const users = appState.users;
    
    // Total de usuários
    const total = users.length;
    elements.kpiTotalUsuarios.textContent = total;
    
    // Contar por role
    const adminCount = users.filter(u => u.role === 'admin').length;
    const internoCount = users.filter(u => u.role === 'interno_unique').length;
    const clientesCount = users.filter(u => u.role === 'cliente_unique').length;
    
    // Usuários ativos
    const ativosCount = users.filter(u => u.ativo === true || u.ativo === 'true').length;
    
    // Atualizar KPIs (verificar se elementos existem)
    if (elements.kpiAdmin) {
        elements.kpiAdmin.textContent = adminCount;
    }
    elements.kpiInterno.textContent = internoCount;
    elements.kpiClientes.textContent = clientesCount;
    elements.kpiAtivos.textContent = ativosCount;
    
    console.log('[USUARIOS] KPIs atualizados:', {
        total, adminCount, internoCount, clientesCount, ativosCount
    });
}

/**
 * Manipula input de busca com debounce
 */
function handleSearchInput(e) {
    clearTimeout(appState.searchTimeout);
    
    appState.searchTimeout = setTimeout(() => {
        appState.activeFilters.search = e.target.value.trim().toLowerCase();
        filterAndDisplayUsers();
    }, CONFIG.DEBOUNCE_DELAY);
}

/**
 * Manipula mudança de filtros
 */
function handleFilterChange() {
    appState.activeFilters.role = elements.filterPerfil.value;
    appState.activeFilters.status = elements.filterStatus.value;
    filterAndDisplayUsers();
}

/**
 * Filtra e exibe usuários baseado nos filtros ativos
 */
function filterAndDisplayUsers() {
    let filtered = [...appState.users];
    
    // Filtro de busca
    if (appState.activeFilters.search) {
        filtered = filtered.filter(user => {
            const searchTerm = appState.activeFilters.search;
            return (
                user.nome?.toLowerCase().includes(searchTerm) ||
                user.email?.toLowerCase().includes(searchTerm) ||
                ROLE_CONFIG[user.role]?.label.toLowerCase().includes(searchTerm)
            );
        });
    }
    
    // Filtro de role
    if (appState.activeFilters.role) {
        filtered = filtered.filter(user => user.role === appState.activeFilters.role);
    }
    
    // Filtro de status
    if (appState.activeFilters.status) {
        const isActive = appState.activeFilters.status === 'active';
        filtered = filtered.filter(user => (user.ativo === true || user.ativo === 'true') === isActive);
    }
    
    appState.filteredUsers = filtered;
    displayUsersByRole();
}

/**
 * Exibe usuários organizados por role
 */
function displayUsersByRole() {
    console.log('[USUARIOS] Separando usuários por role. Total filtrado:', appState.filteredUsers.length);
    
    // Separar usuários por role
    const usersByRole = {
        admin: appState.filteredUsers.filter(u => u.role === 'admin'),
        interno_unique: appState.filteredUsers.filter(u => u.role === 'interno_unique'),
        cliente_unique: appState.filteredUsers.filter(u => u.role === 'cliente_unique')
    };
    
    console.log('[USUARIOS] Usuários por role:', usersByRole);
    
    // Atualizar contadores das seções (verificar se elementos existem)
    if (elements.countAdmin) {
        elements.countAdmin.textContent = usersByRole.admin.length;
    }
    elements.countInterno.textContent = usersByRole.interno_unique.length;
    elements.countClientes.textContent = usersByRole.cliente_unique.length;
    
    // Renderizar usuários em cada seção (apenas se as seções existirem)
    if (elements.tbodyAdmin) {
        renderUsersInTable(elements.tbodyAdmin, usersByRole.admin, 'admin');
    }
    renderUsersInTable(elements.tbodyInterno, usersByRole.interno_unique, 'interno');
    renderUsersInTable(elements.tbodyClientes, usersByRole.cliente_unique, 'clientes');
    
    // Mostrar/ocultar seções baseado na presença de usuários (apenas se existirem)
    if (elements.sectionAdmin) {
        toggleSectionVisibility(elements.sectionAdmin, usersByRole.admin.length > 0);
    }
    toggleSectionVisibility(elements.sectionInterno, usersByRole.interno_unique.length > 0);
    toggleSectionVisibility(elements.sectionClientes, usersByRole.cliente_unique.length > 0);
    
    // Mostrar empty state se não há usuários filtrados
    const hasUsers = appState.filteredUsers.length > 0;
    showEmptyState(!hasUsers);
}

/**
 * Renderiza usuários em uma tabela específica
 */
function renderUsersInTable(tbodyElement, users, role) {
    if (!tbodyElement) {
        console.warn('[USUARIOS] Tbody element não encontrado para renderização');
        return;
    }
    
    console.log('[USUARIOS] Renderizando', users.length, 'usuários na tabela', tbodyElement.id);
    
    tbodyElement.innerHTML = '';
    
    users.forEach((user, index) => {
        console.log(`[USUARIOS] Criando linha ${index + 1}:`, user);
        const rowElement = createUserTableRow(user);
        tbodyElement.appendChild(rowElement);
    });
    
    // Show/hide empty states
    const emptyElement = document.getElementById(`empty-${role}`);
    if (emptyElement) {
        emptyElement.style.display = users.length === 0 ? 'block' : 'none';
    }
    
    console.log('[USUARIOS] Renderização completa para tabela', tbodyElement.id);
}

/**
 * Cria linha de tabela para usuário - NOVA VERSÃO PARA TABELAS
 */
function createUserTableRow(user) {
    console.log('[USUARIOS] Criando linha para usuário:', user.id, user.nome || user.name);
    
    // Criar elemento da linha
    const rowElement = document.createElement('tr');
    rowElement.className = 'user-row';
    rowElement.setAttribute('data-user-id', user.id);
    rowElement.setAttribute('data-role', user.role);
    
    // Determinar status
    const isActive = user.ativo === true || user.ativo === 'true' || user.is_active === true;
    const statusClass = isActive ? 'active' : 'inactive';
    rowElement.setAttribute('data-status', statusClass);
    
    // Determinar se é administrador de módulo
    const isModuleAdmin = user.perfil_principal && ['admin_operacao', 'admin_financeiro'].includes(user.perfil_principal);
    const isMasterAdmin = user.perfil_principal === 'master_admin';
    
    // NOVA LÓGICA: Verificar se tem perfis de admin baseado em is_admin_profile
    const hasAdminProfile = user.perfis && Array.isArray(user.perfis) && user.perfis.some(perfil => perfil.is_admin_profile === true);
    
    console.log(`[DEBUG] Admin check for ${user.nome || user.name}:`, {
        perfil_principal: user.perfil_principal,
        isModuleAdmin: isModuleAdmin,
        isMasterAdmin: isMasterAdmin,
        hasAdminProfile: hasAdminProfile,
        perfis: user.perfis
    });
    
    // Contar totais
    const totalEmpresas = (user.agent_info?.empresas && Array.isArray(user.agent_info.empresas)) ? user.agent_info.empresas.length : 0;
    const totalNumeros = (user.whatsapp_numbers && Array.isArray(user.whatsapp_numbers)) ? user.whatsapp_numbers.length : 0;
    const totalPerfis = (user.perfis && Array.isArray(user.perfis)) ? user.perfis.length : 0;
    
    // Montar HTML da linha
    rowElement.innerHTML = `
        <td class="user-name-cell">
            <div class="user-name-container">
                <span class="user-name">${user.nome || user.name || 'Sem nome'}</span>
            </div>
        </td>
        <td class="user-email-cell">
            <span class="user-email">${user.email || 'Sem email'}</span>
        </td>
        <td class="user-count-cell">
            <span class="count-badge">${totalEmpresas}</span>
        </td>
        <td class="user-count-cell">
            <span class="count-badge">${totalNumeros}</span>
        </td>
        <td class="user-count-cell">
            <span class="count-badge">${totalPerfis}</span>
        </td>
        <td class="user-admin-cell">
            ${
                isMasterAdmin ? '<i class="admin-shield mdi mdi-shield-crown" title="Master Admin"></i>' :
                hasAdminProfile ? '<i class="admin-shield mdi mdi-shield" title="Administrador de Módulo"></i>' :
                '<span class="admin-none">-</span>'
            }
        </td>
        <td class="user-status-cell">
            <span class="status-badge status-${statusClass}">
                <span class="status-dot"></span>
                ${isActive ? 'Ativo' : 'Inativo'}
            </span>
        </td>
        <td class="user-actions-cell">
            <div class="table-actions">
                <button class="btn-table-action btn-view" title="Visualizar usuário" data-action="view" data-user-id="${user.id}">
                    <i class="mdi mdi-eye"></i>
                </button>
                <button class="btn-table-action btn-edit" title="Editar usuário" data-action="edit" data-user-id="${user.id}">
                    <i class="mdi mdi-pencil"></i>
                </button>
                <button class="btn-table-action btn-delete" title="Excluir usuário" data-action="delete" data-user-id="${user.id}">
                    <i class="mdi mdi-delete"></i>
                </button>
            </div>
        </td>
    `;
    
    // Adicionar event listeners aos botões
    const viewBtn = rowElement.querySelector('.btn-view');
    const editBtn = rowElement.querySelector('.btn-edit');
    const deleteBtn = rowElement.querySelector('.btn-delete');
    
    console.log('[USUARIOS] DEBUG - Botões encontrados:', {
        viewBtn: !!viewBtn,
        editBtn: !!editBtn,
        deleteBtn: !!deleteBtn,
        userId: user.id
    });
    
    if (viewBtn) {
        viewBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            console.log('[USUARIOS] ✓ Botão VISUALIZAR clicado para usuário:', user.id);
            openModalForView(user.id);
        });
        console.log('[USUARIOS] ✓ Event listener VISUALIZAR adicionado para usuário:', user.id);
    } else {
        console.error('[USUARIOS] ✗ Botão VISUALIZAR não encontrado para usuário:', user.id);
    }
    
    if (editBtn) {
        editBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            console.log('[USUARIOS] ✓ Botão EDITAR clicado para usuário:', user.id);
            openModalForEdit(user.id);
        });
        console.log('[USUARIOS] ✓ Event listener EDITAR adicionado para usuário:', user.id);
    } else {
        console.error('[USUARIOS] ✗ Botão EDITAR não encontrado para usuário:', user.id);
    }
    
    if (deleteBtn) {
        deleteBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            console.log('[USUARIOS] ✓ Botão EXCLUIR clicado para usuário:', user.id, user.nome || user.name);
            showDeleteConfirmation(user.id, user.nome || user.name || 'Usuário');
        });
        console.log('[USUARIOS] ✓ Event listener EXCLUIR adicionado para usuário:', user.id);
    } else {
        console.error('[USUARIOS] ✗ Botão EXCLUIR não encontrado para usuário:', user.id);
    }
    
    return rowElement;
}

/**
 * Gera informações de empresas para o card
 */
function generateEmpresasInfo(user) {
    // Usar a estrutura correta retornada pela API
    const empresas = user.agent_info?.empresas || [];
    const empresasCount = empresas.length;
    
    if (empresasCount > 0) {
        return `<span class="user-companies" title="${empresasCount} empresa(s) vinculada(s)">
            <i class="mdi mdi-domain"></i>
            <span>${empresasCount}</span>
        </span>`;
    }
    
    return `<span class="user-companies no-data" title="Nenhuma empresa vinculada">
        <i class="mdi mdi-domain-off"></i>
    </span>`;
}

/**
 * Gera informações de WhatsApp para o card
 */
function generateWhatsappInfo(user) {
    // Usar a estrutura correta retornada pela API
    const whatsappNumbers = user.whatsapp_numbers || [];
    const whatsappCount = whatsappNumbers.length;
    
    if (whatsappCount > 0) {
        return `<span class="user-whatsapp" title="${whatsappCount} número(s) cadastrado(s)">
            <i class="mdi mdi-whatsapp"></i>
            <span>${whatsappCount}</span>
        </span>`;
    }
    
    return `<span class="user-whatsapp no-data" title="Nenhum número cadastrado">
        <i class="mdi mdi-phone-off"></i>
    </span>`;
}
    

/**
 * Toggle visibilidade da seção
 */
function toggleSectionVisibility(sectionElement, show) {
    if (sectionElement) {
        if (show) {
            sectionElement.classList.remove('hidden');
        } else {
            sectionElement.classList.add('hidden');
        }
    }
}

/**
 * Mostra/oculta estado vazio
 */
function showEmptyState(show = true) {
    if (elements.emptyState) {
        if (show) {
            elements.emptyState.classList.remove('hidden');
        } else {
            elements.emptyState.classList.add('hidden');
        }
    }
}

/**
 * Mostra/oculta loading
 */
function showLoading(show = true) {
    // Implementar loading visual se necessário
    appState.isLoading = show;
    
    if (elements.btnRefresh) {
        elements.btnRefresh.disabled = show;
        if (show) {
            elements.btnRefresh.innerHTML = '<i class="mdi mdi-loading mdi-spin"></i> Carregando...';
        } else {
            elements.btnRefresh.innerHTML = '<i class="mdi mdi-refresh"></i> Atualizar';
        }
    }
}

/**
 * Atualiza dados
 */
async function refreshData() {
    await loadUsersData();
    showNotification('Dados atualizados com sucesso!', NOTIFICATION_TYPES.SUCCESS);
}

// =================================
// MODAL E FORMULÁRIO
// =================================

/**
 * Abre modal para criar novo usuário
 */
function openModalForCreate() {
    appState.currentMode = MODAL_MODES.CREATE;
    appState.currentUser = null;
    
    elements.modalTitle.textContent = 'Novo Usuário';
    clearForm();
    clearPerfisSelection();
    removeEmailFieldRestrictions(); // Ensure email field is enabled for new users
    showPasswordSection();
    hideEmpresasSection();
    showModal();
}

/**
 * Abre modal para editar usuário existente
 */
async function openModalForEdit(userId) {
    try {
        appState.currentMode = MODAL_MODES.EDIT;
        elements.modalTitle.textContent = 'Editar Usuário';
        
        showModal();
        showFormLoading();
        
        const userData = await loadUserData(userId);
        fillUserForm(userData);
        
        // Carregar perfis do usuário
        await loadUserPerfis(userId);
        
        hideFormLoading();
        
    } catch (error) {
        console.error('[USUARIOS] Erro ao carregar dados do usuário:', error);
        showNotification('Erro ao carregar dados do usuário: ' + error.message, NOTIFICATION_TYPES.ERROR);
        closeModal();
    }
}

/**
 * Carrega dados completos do usuário
 */
async function loadUserData(userId) {
    console.log('[USUARIOS] Carregando dados do usuário:', userId);
    const response = await apiRequest(`/${userId}/dados`);
    
    console.log('[USUARIOS] Resposta da API para dados do usuário:', response);
    
    if (!response.success) {
        throw new Error(response.error || 'Erro ao carregar dados do usuário');
    }
    
    if (!response.data) {
        throw new Error('Dados do usuário não encontrados na resposta');
    }
    
    // A API retorna os dados em response.data, não response.user
    appState.currentUser = response.data;
    return response.data;
}

/**
 * Preenche formulário com dados do usuário
 */
function fillUserForm(user) {
    if (!user) {
        console.error('[USUARIOS] Usuário não definido para preencher formulário');
        throw new Error('Dados do usuário não foram carregados corretamente');
    }
    
    console.log('[USUARIOS] Preenchendo formulário com dados:', user);
    
    // A API retorna 'name' ao invés de 'nome'
    document.getElementById('nome').value = user.name || user.nome || '';
    document.getElementById('email').value = user.email || '';
    document.getElementById('role').value = user.role || '';
    // A API retorna 'is_active' ao invés de 'ativo'
    document.getElementById('ativo').checked = user.is_active === true || user.ativo === true || user.ativo === 'true';
    
    // Apply email field restrictions if in edit mode
    if (appState.currentMode === MODAL_MODES.EDIT) {
        applyEmailFieldRestrictions();
    } else {
        removeEmailFieldRestrictions();
    }
    
    handleRoleChange();
    
    // CRITICAL FIX: Set the correct module admin radio button based on user's perfil_principal
    setModuleAdminSelection(user);
    
    hidePasswordSection();
    
    // Carregar empresas e WhatsApp se necessário
    // Empresas são permitidas para cliente_unique E interno_unique
    if (user.role === 'cliente_unique' || user.role === 'interno_unique') {
        showEmpresasSection();
        loadUserEmpresas(user.id);
    } else {
        hideEmpresasSection();
    }
    
    loadUserWhatsapp(user.id);
}

/**
 * Manipula mudança no campo Role
 */
function handleRoleChange() {
    const role = document.getElementById('role').value;
    
    // Mostrar empresas para cliente_unique E interno_unique
    if (role === 'cliente_unique' || role === 'interno_unique') {
        showEmpresasSection();
    } else {
        hideEmpresasSection();
    }
    
    // Module Administrator section - only for Master Admins creating Equipe Interna users
    handleModuleAdminSection(role);
}

/**
 * Handles Module Administrator section visibility and functionality
 */
function handleModuleAdminSection(role) {
    const moduleAdminSection = document.getElementById('module-admin-section');
    
    if (!moduleAdminSection) {
        // Module admin section not available (user is not Master Admin)
        return;
    }
    
    if (role === 'interno_unique') {
        // Show module admin section for Equipe Interna
        moduleAdminSection.style.display = 'block';
        moduleAdminSection.classList.add('active');
        
        // Initialize module admin event listeners if not already done
        initializeModuleAdminEventListeners();
    } else {
        // Hide module admin section for other roles
        moduleAdminSection.style.display = 'none';
        moduleAdminSection.classList.remove('active');
        
        // Reset to regular user when hidden
        const noneRadio = document.querySelector('input[name="module_admin"][value="none"]');
        if (noneRadio) {
            noneRadio.checked = true;
        }
    }
}

/**
 * Initializes Module Administrator section event listeners
 */
function initializeModuleAdminEventListeners() {
    const moduleAdminRadios = document.querySelectorAll('input[name="module_admin"]');
    
    moduleAdminRadios.forEach(radio => {
        // Remove existing listeners to avoid duplicates
        radio.removeEventListener('change', handleModuleAdminChange);
        // Add listener
        radio.addEventListener('change', handleModuleAdminChange);
    });
}

/**
 * Handles Module Administrator radio button changes
 */
function handleModuleAdminChange(event) {
    const selectedValue = event.target.value;
    const moduleAdminSection = document.getElementById('module-admin-section');
    
    console.log('[MODULE_ADMIN] Selected module admin type:', selectedValue);
    
    // Update visual feedback based on selection
    if (selectedValue !== 'none') {
        moduleAdminSection.classList.add('active');
        
        // Show notification about module admin selection
        const moduleLabel = selectedValue === 'admin_operacao' ? 'Operacional' : 'Financeiro';
        console.log(`[MODULE_ADMIN] User will be Module Administrator for: ${moduleLabel}`);
    } else {
        moduleAdminSection.classList.remove('active');
        console.log('[MODULE_ADMIN] User will be regular internal user');
    }
}

/**
 * Mostra/oculta seções do formulário
 */
function showEmpresasSection() {
    const section = document.getElementById('empresas-section');
    if (section) section.classList.remove('hidden');
}

function hideEmpresasSection() {
    const section = document.getElementById('empresas-section');
    if (section) section.classList.add('hidden');
}

function showPasswordSection() {
    const section = document.getElementById('password-section');
    const senhaField = document.getElementById('senha');
    const confirmarSenhaField = document.getElementById('confirmar_senha');
    
    if (section) {
        section.classList.remove('hidden');
        // Tornar campos obrigatórios quando seção estiver visível
        if (senhaField) senhaField.required = true;
        if (confirmarSenhaField) confirmarSenhaField.required = true;
    }
}

function hidePasswordSection() {
    const section = document.getElementById('password-section');
    const senhaField = document.getElementById('senha');
    const confirmarSenhaField = document.getElementById('confirmar_senha');
    
    if (section) {
        section.classList.add('hidden');
        // Remover obrigatoriedade quando seção estiver oculta
        if (senhaField) {
            senhaField.required = false;
            senhaField.value = '';
        }
        if (confirmarSenhaField) {
            confirmarSenhaField.required = false;
            confirmarSenhaField.value = '';
        }
    }
}

/**
 * Apply email field restrictions for edit mode
 * Similar to profile name restrictions - email cannot be changed
 * as it's used as authentication key and linked to other tables
 */
function applyEmailFieldRestrictions() {
    const emailField = document.getElementById('email');
    const warningDiv = document.getElementById('email-readonly-warning');
    
    if (emailField) {
        // Disable the email field
        emailField.disabled = true;
        emailField.style.backgroundColor = '#f8f9fa';
        emailField.style.cursor = 'not-allowed';
        
        console.log('[USUARIOS] Email field disabled for edit mode - preserving authentication key');
    }
    
    if (warningDiv) {
        // Show warning message
        warningDiv.style.display = 'block';
    }
}

/**
 * Remove email field restrictions for create mode
 */
function removeEmailFieldRestrictions() {
    const emailField = document.getElementById('email');
    const warningDiv = document.getElementById('email-readonly-warning');
    
    if (emailField) {
        // Re-enable the email field
        emailField.disabled = false;
        emailField.style.backgroundColor = '';
        emailField.style.cursor = '';
    }
    
    if (warningDiv) {
        // Hide warning message
        warningDiv.style.display = 'none';
    }
}

/**
 * Mostra/oculta modal
 */
function showModal() {
    if (elements.modalUsuario) {
        elements.modalUsuario.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
    }
}

function closeModal() {
    if (elements.modalUsuario) {
        elements.modalUsuario.classList.add('hidden');
        document.body.style.overflow = '';
    }
    
    clearForm();
    appState.currentUser = null;
    appState.currentMode = null;
}

/**
 * Mostra/oculta loading do formulário
 */
function showFormLoading() {
    if (elements.formLoading) {
        elements.formLoading.classList.remove('hidden');
    }
}

function hideFormLoading() {
    if (elements.formLoading) {
        elements.formLoading.classList.add('hidden');
    }
}

/**
 * Limpa formulário
 */
function clearForm() {
    if (elements.formUsuario) {
        elements.formUsuario.reset();
    }
    
    // Reset module admin section
    const moduleAdminSection = document.getElementById('module-admin-section');
    if (moduleAdminSection) {
        moduleAdminSection.style.display = 'none';
        moduleAdminSection.classList.remove('active');
        
        // Reset to "none" option
        const noneRadio = document.querySelector('input[name="module_admin"][value="none"]');
        if (noneRadio) {
            noneRadio.checked = true;
        }
    }
    
    clearEmpresasList();
    clearWhatsappList();
}

// =================================
// CRUD OPERATIONS
// =================================

/**
 * Manipula submissão do formulário
 */
async function handleFormSubmit(e) {
    e.preventDefault();
    
    // Use await since validateForm is now async
    if (!(await validateForm())) {
        return;
    }
    
    try {
        showSaveLoading();
        
        if (appState.currentMode === MODAL_MODES.CREATE) {
            await createUser();
        } else {
            await updateUser();
        }
        
        closeModal();
        await loadUsersData(); // Recarregar dados
        
    } catch (error) {
        console.error('[USUARIOS] Erro ao salvar usuário:', error);
        showNotification('Erro ao salvar usuário: ' + error.message, NOTIFICATION_TYPES.ERROR);
    } finally {
        hideSaveLoading();
    }
}

/**
 * Valida se o usuário pode atribuir os perfis selecionados
 */
async function validatePerfisSelection() {
    try {
        if (appState.perfis.selected.length === 0) {
            return { valid: true, message: 'Nenhum perfil selecionado' };
        }
        
        console.log('[PERFIS_VALIDATION] Validando perfis:', appState.perfis.selected);
        
        const response = await apiRequest('/api/validate-perfis', 'POST', {
            perfis_ids: appState.perfis.selected
        });
        
        if (response.success) {
            console.log('[PERFIS_VALIDATION] Perfis válidos');
            return { valid: true, message: response.message };
        } else {
            console.error('[PERFIS_VALIDATION] Perfis inválidos:', response.message);
            return { valid: false, message: response.message };
        }
    } catch (error) {
        console.error('[PERFIS_VALIDATION] Erro na validação:', error);
        return { valid: false, message: 'Erro ao validar perfis: ' + error.message };
    }
}

/**
 * Cria novo usuário
 */
async function createUser() {
    const userData = collectUserFormData();
    
    // STEP 1: Validate perfis BEFORE creating user
    const perfilValidation = await validatePerfisSelection();
    if (!perfilValidation.valid) {
        throw new Error(perfilValidation.message);
    }
    
    // STEP 2: Create user only if perfis are valid
    const response = await apiRequest('/salvar', 'POST', userData);
    
    if (!response.success) {
        throw new Error(response.error || 'Erro ao criar usuário');
    }
    
    const userId = response.user_id;
    
    // STEP 3: Save related data (empresas, whatsapp, perfis)
    try {
        // Salvar empresas e WhatsApp se necessário
        // Empresas são permitidas para cliente_unique E interno_unique
        if (userData.role === 'cliente_unique' || userData.role === 'interno_unique') {
            await saveUserEmpresas(userId);
        }
        
        await saveUserWhatsapp(userId);
        
        // Salvar perfis
        await saveUserPerfis(userId);
        
        showNotification('Usuário criado com sucesso!', NOTIFICATION_TYPES.SUCCESS);
    } catch (relatedDataError) {
        // Se falhar ao salvar dados relacionados, avisar mas não falhar completamente
        console.error('[USUARIOS] Erro ao salvar dados relacionados:', relatedDataError);
        showNotification('Usuário criado, mas houve problemas ao salvar alguns dados: ' + relatedDataError.message, NOTIFICATION_TYPES.WARNING);
    }
}

/**
 * Atualiza usuário existente
 */
async function updateUser() {
    const userData = collectUserFormData();
    const userId = appState.currentUser.id;
    
    const response = await apiRequest(`/api/user/${userId}`, 'PUT', userData);
    
    if (!response.success) {
        throw new Error(response.error || 'Erro ao atualizar usuário');
    }
    
    // Salvar empresas e WhatsApp se necessário
    // Empresas são permitidas para cliente_unique E interno_unique
    if (userData.role === 'cliente_unique' || userData.role === 'interno_unique') {
        await saveUserEmpresas(userId);
    }
    
    await saveUserWhatsapp(userId);
    
    // Salvar perfis
    await saveUserPerfis(userId);
    
    showNotification('Usuário atualizado com sucesso!', NOTIFICATION_TYPES.SUCCESS);
}

/**
 * Coleta dados do formulário
 */
function collectUserFormData() {
    const formData = {
        name: document.getElementById('nome').value.trim(),
        email: document.getElementById('email').value.trim(),
        role: document.getElementById('role').value,
        is_active: document.getElementById('ativo').checked,
        password: document.getElementById('senha')?.value,
        confirm_password: document.getElementById('confirmar_senha')?.value
    };
    
    // Handle Module Administrator selection for perfil_principal
    const moduleAdminSelection = getModuleAdminSelection();
    
    if (moduleAdminSelection && moduleAdminSelection !== 'none') {
        // User selected a module admin role
        formData.perfil_principal = moduleAdminSelection;
        console.log('[MODULE_ADMIN] Setting perfil_principal to:', moduleAdminSelection);
    } else {
        // Regular user or admin role
        if (formData.role === 'admin') {
            formData.perfil_principal = 'master_admin';
        } else if (appState.currentMode === MODAL_MODES.EDIT && appState.currentUser) {
            // CRITICAL FIX: When editing existing user and no module admin selected,
            // preserve the existing perfil_principal if it's a valid one
            const currentPerfilPrincipal = appState.currentUser.perfil_principal;
            if (currentPerfilPrincipal && 
                ['admin_operacao', 'admin_financeiro', 'basico'].includes(currentPerfilPrincipal)) {
                formData.perfil_principal = currentPerfilPrincipal;
                console.log('[MODULE_ADMIN] Preserving existing perfil_principal:', currentPerfilPrincipal);
            } else {
                formData.perfil_principal = 'basico';
                console.log('[MODULE_ADMIN] Defaulting to basico (invalid or missing current perfil_principal)');
            }
        } else {
            // Creating new user - default to basico
            formData.perfil_principal = 'basico';
            console.log('[MODULE_ADMIN] New user defaulting to basico');
        }
    }
    
    console.log('[FORM_DATA] Collected user data:', formData);
    return formData;
}

/**
 * Gets the selected module administrator option
 */
function getModuleAdminSelection() {
    const selectedRadio = document.querySelector('input[name="module_admin"]:checked');
    return selectedRadio ? selectedRadio.value : 'none';
}

/**
 * Sets the module administrator radio button based on user's perfil_principal
 * CRITICAL FIX: This ensures the correct radio button is selected when editing users
 */
function setModuleAdminSelection(user) {
    console.log('[MODULE_ADMIN] Setting module admin selection for user:', user);
    
    // Only proceed if the module admin section exists (Master Admin interface)
    const moduleAdminSection = document.getElementById('module-admin-section');
    if (!moduleAdminSection) {
        console.log('[MODULE_ADMIN] Module admin section not found - user is not Master Admin');
        return;
    }
    
    // Only set for interno_unique users
    if (user.role !== 'interno_unique') {
        console.log('[MODULE_ADMIN] User is not interno_unique, skipping module admin selection');
        return;
    }
    
    const perfilPrincipal = user.perfil_principal;
    console.log('[MODULE_ADMIN] User perfil_principal:', perfilPrincipal);
    
    // Determine which radio button to select based on perfil_principal
    let targetValue = 'none'; // Default to regular user
    
    if (perfilPrincipal === 'admin_operacao') {
        targetValue = 'admin_operacao';
        console.log('[MODULE_ADMIN] User is Operational Module Admin');
    } else if (perfilPrincipal === 'admin_financeiro') {
        targetValue = 'admin_financeiro';
        console.log('[MODULE_ADMIN] User is Financial Module Admin');
    } else if (perfilPrincipal === 'basico') {
        targetValue = 'none';
        console.log('[MODULE_ADMIN] User is regular internal user');
    } else {
        console.warn('[MODULE_ADMIN] Unexpected perfil_principal for interno_unique user:', perfilPrincipal);
        targetValue = 'none'; // Default to safe option
    }
    
    // Set the correct radio button
    const targetRadio = document.querySelector(`input[name="module_admin"][value="${targetValue}"]`);
    if (targetRadio) {
        targetRadio.checked = true;
        console.log('[MODULE_ADMIN] Successfully set radio button to:', targetValue);
        
        // Trigger change event to update UI if needed
        targetRadio.dispatchEvent(new Event('change', { bubbles: true }));
    } else {
        console.error('[MODULE_ADMIN] Could not find radio button for value:', targetValue);
    }
}

/**
 * Valida formulário
 */
async function validateForm() {
    const nome = document.getElementById('nome').value.trim();
    const email = document.getElementById('email').value.trim();
    const role = document.getElementById('role').value;
    
    if (!nome) {
        showNotification('Nome é obrigatório', NOTIFICATION_TYPES.ERROR);
        return false;
    }
    
    if (!email || !isValidEmail(email)) {
        showNotification('Email válido é obrigatório', NOTIFICATION_TYPES.ERROR);
        return false;
    }
    
    if (!role) {
        showNotification('Perfil é obrigatório', NOTIFICATION_TYPES.ERROR);
        return false;
    }
    
    // Validar senha apenas para novo usuário
    if (appState.currentMode === MODAL_MODES.CREATE) {
        const senha = document.getElementById('senha').value;
        const confirmarSenha = document.getElementById('confirmar_senha').value;
        
        if (!senha || senha.length < 6) {
            showNotification('Senha deve ter pelo menos 6 caracteres', NOTIFICATION_TYPES.ERROR);
            return false;
        }
        
        if (senha !== confirmarSenha) {
            showNotification('Senhas não coincidem', NOTIFICATION_TYPES.ERROR);
            return false;
        }
        
        // Validate perfis selection for CREATE mode
        const perfilValidation = await validatePerfisSelection();
        if (!perfilValidation.valid) {
            showNotification(perfilValidation.message, NOTIFICATION_TYPES.ERROR);
            return false;
        }
    }
    
    return true;
}

/**
 * Valida formato de email
 */
function isValidEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

/**
 * Mostra/oculta loading no botão salvar
 */
function showSaveLoading() {
    if (elements.btnSave) {
        elements.btnSave.disabled = true;
        elements.btnSave.innerHTML = '<i class="mdi mdi-loading mdi-spin"></i> Salvando...';
    }
}

function hideSaveLoading() {
    if (elements.btnSave) {
        elements.btnSave.disabled = false;
        elements.btnSave.innerHTML = '<i class="mdi mdi-check"></i> <span id="save-text">Salvar</span>';
    }
}

// =================================
// FUNÇÕES GLOBAIS (para onclick dos cards)
// =================================

/**
 * Abre modal de edição (chamada pelos cards) - FUNÇÃO GLOBAL FALLBACK
 */
window.openEditModal = function(userId) {
    console.log('[USUARIOS] 🌍 window.openEditModal chamada (fallback):', userId);
    openModalForEdit(userId);
};

/**
 * Deleta usuário (chamada pelos cards) - FUNÇÃO GLOBAL FALLBACK
 */
window.deleteUser = function(userId, userName) {
    console.log('[USUARIOS] 🌍 window.deleteUser chamada (fallback):', { userId, userName });
    showDeleteConfirmation(userId, userName);
};

/**
 * Remove empresa da lista (chamada pelos botões)
 */
window.removeEmpresaFromList = function(empresaId) {
    console.log(`[DEBUG] removeEmpresaFromList chamada com ID: ${empresaId} (tipo: ${typeof empresaId})`);
    console.log(`[DEBUG] Estado atual appState.originalEmpresas:`, appState.originalEmpresas);
    
    // Converter para string para comparação consistente (fix type comparison)
    const idToRemove = String(empresaId);
    
    const before = appState.originalEmpresas.length;
    appState.originalEmpresas = appState.originalEmpresas.filter(e => String(e.id) !== idToRemove);
    const after = appState.originalEmpresas.length;
    
    console.log(`[DEBUG] Removido: ${before - after} items`);
    console.log(`[DEBUG] Estado após remoção:`, appState.originalEmpresas);
    
    renderEmpresasList();
    updateEmpresasCount();
};

/**
 * Remove WhatsApp da lista (chamada pelos botões)
 */
window.removeWhatsappFromList = function(whatsappId) {
    console.log(`[DEBUG] removeWhatsappFromList chamada com ID: ${whatsappId} (tipo: ${typeof whatsappId})`);
    console.log(`[DEBUG] Estado atual appState.originalWhatsapp:`, appState.originalWhatsapp);
    
    // Converter para string para comparação consistente (fix type comparison)
    const idToRemove = String(whatsappId);
    
    const before = appState.originalWhatsapp.length;
    appState.originalWhatsapp = appState.originalWhatsapp.filter(w => String(w.id) !== idToRemove);
    const after = appState.originalWhatsapp.length;
    
    console.log(`[DEBUG] Removido: ${before - after} items`);
    console.log(`[DEBUG] Estado após remoção:`, appState.originalWhatsapp);
    
    renderWhatsappList();
    updateWhatsappCount();
};

/**
 * Define WhatsApp como principal (chamada pelos botões)
 */
window.setWhatsappAsPrincipal = function(whatsappId) {
    console.log(`[DEBUG] setWhatsappAsPrincipal chamada com ID: ${whatsappId} (tipo: ${typeof whatsappId})`);
    
    // Converter para string para comparação consistente
    const idToSet = String(whatsappId);
    
    // Definir apenas um WhatsApp como principal
    appState.originalWhatsapp.forEach(w => {
        w.principal = String(w.id) === idToSet;
    });
    console.log(`[DEBUG] WhatsApp principal definido para ID: ${idToSet}`);
    console.log(`[DEBUG] Estado após definir principal:`, appState.originalWhatsapp);
    
    renderWhatsappList();
    updateWhatsappCount();
};

/**
 * Mostra modal de confirmação de exclusão - CORRIGIDO
 */
function showDeleteConfirmation(userId, userName) {
    console.log('[USUARIOS] 🗑️ showDeleteConfirmation chamada para:', { userId, userName });
    
    // SOLUÇÃO SIMPLES: Usar popup nativo do navegador
    const message = `Tem certeza que deseja excluir o usuário "${userName}"?\n\nEsta ação não pode ser desfeita.`;
    
    console.log('[USUARIOS] 📢 Exibindo popup nativo de confirmação');
    const confirmed = confirm(message);
    
    if (confirmed) {
        console.log('[USUARIOS] ✅ Usuário confirmou exclusão');
        confirmDelete(userId);
    } else {
        console.log('[USUARIOS] ❌ Usuário cancelou exclusão');
    }
    
    console.log('[USUARIOS] ✅ showDeleteConfirmation finalizada');
}

/**
 * Confirma exclusão do usuário
 */
async function confirmDelete(userId) {
    try {
        const response = await apiRequest(`/deletar/${userId}`, 'POST');
        
        if (!response.success) {
            throw new Error(response.error || 'Erro ao excluir usuário');
        }
        
        hideDeleteModal();
        await loadUsersData();
        showNotification('Usuário excluído com sucesso!', NOTIFICATION_TYPES.SUCCESS);
        
    } catch (error) {
        console.error('[USUARIOS] Erro ao excluir usuário:', error);
        showNotification('Erro ao excluir usuário: ' + error.message, NOTIFICATION_TYPES.ERROR);
    }
}

/**
 * Oculta modal de confirmação
 */
function hideDeleteModal() {
    console.log('[USUARIOS] 🚫 Ocultando modal de exclusão');
    
    const modal = document.getElementById('modal-delete-confirm');
    if (modal) {
        console.log('[USUARIOS] Modal encontrado, removendo classes...');
        
        // Remove todas as classes de visibilidade
        modal.classList.add('hidden');
        modal.classList.remove('force-show');
        
        // Reset do estilo do body
        document.body.style.overflow = '';
        
        console.log('[USUARIOS] ✅ Modal ocultado com sucesso');
        console.log('[USUARIOS] Classes atuais do modal:', modal.className);
    } else {
        console.error('[USUARIOS] ❌ Modal não encontrado para ocultar');
    }
}

// =================================
// EMPRESAS E WHATSAPP (Placeholder - implementar conforme necessário)
// =================================

function initializeEmpresasEventListeners() {
    console.log('[USUARIOS] Inicializando listeners de empresas');
    
    const empresaSearchInput = document.getElementById('empresa-search');
    const btnAddEmpresa = document.getElementById('btn-add-empresa');
    
    if (empresaSearchInput) {
        empresaSearchInput.addEventListener('input', handleEmpresaSearch);
        empresaSearchInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                handleEmpresaAdd();
            }
        });
    }
    
    if (btnAddEmpresa) {
        btnAddEmpresa.addEventListener('click', handleEmpresaAdd);
    }
}

function initializeWhatsappEventListeners() {
    console.log('[USUARIOS] Inicializando listeners de WhatsApp');
    
    const btnAddWhatsapp = document.getElementById('btn-add-whatsapp');
    const whatsappNumeroInput = document.getElementById('whatsapp-numero');
    
    if (btnAddWhatsapp) {
        btnAddWhatsapp.addEventListener('click', handleWhatsappAdd);
    }
    
    if (whatsappNumeroInput) {
        // Formatação automática enquanto digita
        whatsappNumeroInput.addEventListener('input', function(e) {
            let value = e.target.value.replace(/\D/g, ''); // Remove não dígitos
            
            if (value.length >= 2) {
                value = `(${value.substring(0, 2)})${value.substring(2)}`;
            }
            
            e.target.value = value;
        });
        
        // Enter para adicionar
        whatsappNumeroInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                handleWhatsappAdd();
            }
        });
        
    // Validação em tempo real
        whatsappNumeroInput.addEventListener('blur', function(e) {
            const value = e.target.value.trim();
            if (value) {
        const validation = validateWhatsappNumber(value);
        console.log('[USUARIOS][WHATSAPP] Blur validação:', { input: value, validation });
                if (!validation.valid) {
                    e.target.style.borderColor = 'var(--danger-color)';
                    e.target.title = validation.message;
                } else {
                    e.target.style.borderColor = 'var(--success-color)';
                    e.target.title = 'Formato válido';
                    e.target.value = validation.numeroFormatado;
                }
            } else {
                e.target.style.borderColor = '';
                e.target.title = '';
            }
        });
    }
}

/**
 * Manipula busca de empresas
 */
function handleEmpresaSearch(e) {
    clearTimeout(appState.empresaSearchTimeout);
    
    const termo = e.target.value.trim();
    const resultsContainer = document.getElementById('empresa-search-results');
    const btnAdd = document.getElementById('btn-add-empresa');
    
    if (termo.length < 3) {
        if (resultsContainer) {
            resultsContainer.classList.add('hidden');
            resultsContainer.innerHTML = '';
        }
        if (btnAdd) btnAdd.disabled = true;
        return;
    }
    
    appState.empresaSearchTimeout = setTimeout(async () => {
        try {
            console.log('[USUARIOS] Buscando empresas para termo:', termo);
            
            const response = await apiRequest('/api/empresas/buscar', 'POST', { cnpj: termo });
            
            if (response.success) {
                displayEmpresaSearchResults(response, resultsContainer);
                if (btnAdd) btnAdd.disabled = false;
            } else {
                if (resultsContainer) {
                    resultsContainer.innerHTML = '<div class="search-result-item">Nenhuma empresa encontrada</div>';
                    resultsContainer.classList.remove('hidden');
                }
                if (btnAdd) btnAdd.disabled = true;
            }
        } catch (error) {
            console.error('[USUARIOS] Erro ao buscar empresas:', error);
            if (resultsContainer) {
                resultsContainer.innerHTML = '<div class="search-result-item error">Erro na busca</div>';
                resultsContainer.classList.remove('hidden');
            }
            if (btnAdd) btnAdd.disabled = true;
        }
    }, CONFIG.DEBOUNCE_DELAY);
}

/**
 * Exibe resultados da busca de empresas
 */
function displayEmpresaSearchResults(response, container) {
    if (!container) return;
    
    container.innerHTML = '';
    
    if (response.multiple && response.empresas) {
        // Múltiplas empresas
        response.empresas.forEach(empresa => {
            const item = createEmpresaSearchResultItem(empresa);
            container.appendChild(item);
        });
    } else if (response.empresa) {
        // Uma empresa
        const item = createEmpresaSearchResultItem(response.empresa);
        container.appendChild(item);
    }
    
    container.classList.remove('hidden');
}

/**
 * Cria item de resultado da busca
 */
function createEmpresaSearchResultItem(empresa) {
    const div = document.createElement('div');
    div.className = 'search-result-item';
    div.innerHTML = `
        <div class="empresa-info">
            <strong>${empresa.nome_cliente}</strong>
            <span class="cnpj">${Array.isArray(empresa.cnpj) ? empresa.cnpj[0] : empresa.cnpj}</span>
        </div>
    `;
    
    div.addEventListener('click', () => {
        selectEmpresaFromSearch(empresa);
    });
    
    return div;
}

/**
 * Seleciona empresa da busca
 */
function selectEmpresaFromSearch(empresa) {
    const searchInput = document.getElementById('empresa-search');
    const resultsContainer = document.getElementById('empresa-search-results');
    
    if (searchInput) {
        searchInput.value = empresa.nome_cliente;
        searchInput.dataset.selectedEmpresaId = empresa.id;
        searchInput.dataset.selectedEmpresaNome = empresa.nome_cliente;
        searchInput.dataset.selectedEmpresaCnpj = Array.isArray(empresa.cnpj) ? empresa.cnpj[0] : empresa.cnpj;
    }
    
    if (resultsContainer) {
        resultsContainer.classList.add('hidden');
    }
}

/**
 * Adiciona empresa selecionada
 */
function handleEmpresaAdd() {
    const searchInput = document.getElementById('empresa-search');
    
    if (!searchInput || !searchInput.dataset.selectedEmpresaId) {
        showNotification('Selecione uma empresa da lista de resultados', NOTIFICATION_TYPES.WARNING);
        return;
    }
    
    const empresa = {
        id: searchInput.dataset.selectedEmpresaId,
        nome_cliente: searchInput.dataset.selectedEmpresaNome,
        cnpj: searchInput.dataset.selectedEmpresaCnpj
    };
    
    addEmpresaToList(empresa);
    
    // Limpar busca
    searchInput.value = '';
    delete searchInput.dataset.selectedEmpresaId;
    delete searchInput.dataset.selectedEmpresaNome;
    delete searchInput.dataset.selectedEmpresaCnpj;
    
    const resultsContainer = document.getElementById('empresa-search-results');
    if (resultsContainer) {
        resultsContainer.classList.add('hidden');
    }
    
    const btnAdd = document.getElementById('btn-add-empresa');
    if (btnAdd) btnAdd.disabled = true;
}

/**
 * Adiciona empresa à lista
 */
function addEmpresaToList(empresa) {
    // Verificar se já existe
    if (appState.originalEmpresas.some(e => e.id === empresa.id)) {
        showNotification('Empresa já adicionada à lista', NOTIFICATION_TYPES.WARNING);
        return;
    }
    
    appState.originalEmpresas.push(empresa);
    renderEmpresasList();
    updateEmpresasCount();
}

/**
 * Renderiza lista de empresas
 */
function renderEmpresasList() {
    const container = document.getElementById('empresas-list');
    if (!container) return;
    
    if (appState.originalEmpresas.length === 0) {
        container.innerHTML = `
            <div class="empty-list">
                <i class="mdi mdi-domain-off"></i>
                <p>Nenhuma empresa vinculada</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = '';
    
    appState.originalEmpresas.forEach(empresa => {
        const item = document.createElement('div');
        item.className = 'empresa-list-item';
        item.innerHTML = `
            <div class="empresa-item-info">
                <div class="empresa-nome">${empresa.nome_cliente}</div>
                <div class="empresa-cnpj">${empresa.cnpj}</div>
            </div>
            <button type="button" class="btn-remove" onclick="removeEmpresaFromList('${empresa.id}')" title="Remover empresa">
                <i class="mdi mdi-close"></i>
            </button>
        `;
        container.appendChild(item);
    });
}

/**
 * Atualiza contador de empresas
 */
function updateEmpresasCount() {
    const countElement = document.getElementById('empresas-count');
    if (countElement) {
        countElement.textContent = appState.originalEmpresas.length;
    }
}

/**
 * Valida formato do número WhatsApp
 * Agora aceita 10 OU 11 dígitos (com ou sem o 9)
 * Exemplos válidos: (47)33059070, 4733059070, (11)987654321, 11987654321
 */
function validateWhatsappNumber(numero) {
    if (!numero) return { valid: false, message: 'Informe um número', exemplo: 'Ex.: (47)33059070' };

    // Remover formatação (parênteses, espaços, traços)
    const numeroLimpo = numero.replace(/[\(\)\s\-]/g, '');

    // Deve ter 10 ou 11 dígitos
    if (!/^\d{10,11}$/.test(numeroLimpo)) {
        return {
            valid: false,
            message: 'Número deve ter 10 ou 11 dígitos',
            exemplo: 'Ex.: (47)33059070 ou (11)987654321'
        };
    }

    // DDD válido (11-99)
    const ddd = parseInt(numeroLimpo.substring(0, 2), 10);
    if (isNaN(ddd) || ddd < 11 || ddd > 99) {
        return {
            valid: false,
            message: 'DDD inválido (use 11 a 99)',
            exemplo: 'Ex.: (47)33059070'
        };
    }

    // Formatar como (DD)resto mantendo a quantidade de dígitos informada
    const resto = numeroLimpo.substring(2);
    return {
        valid: true,
        numeroLimpo,
        numeroFormatado: `(${numeroLimpo.substring(0, 2)})${resto}`
    };
}

/**
 * Adiciona número WhatsApp
 */
function handleWhatsappAdd() {
    const nomeInput = document.getElementById('whatsapp-nome');
    const numeroInput = document.getElementById('whatsapp-numero');
    const tipoSelect = document.getElementById('whatsapp-tipo');
    
    if (!numeroInput || !numeroInput.value.trim()) {
        showNotification('Informe o número do WhatsApp', NOTIFICATION_TYPES.WARNING);
        return;
    }
    
    // Validar formato do número
    const validation = validateWhatsappNumber(numeroInput.value.trim());
    if (!validation.valid) {
        console.warn('[USUARIOS][WHATSAPP] Validação falhou ao adicionar:', validation);
        showNotification(
            `Formato inválido: ${validation.message}. ${validation.exemplo}`, 
            NOTIFICATION_TYPES.ERROR
        );
        numeroInput.focus();
        return;
    }
    console.log('[USUARIOS][WHATSAPP] Número validado para adicionar:', validation);
    
    const whatsapp = {
        id: Date.now(), // ID temporário para novos registros
        nome: nomeInput ? nomeInput.value.trim() : '',
        numero: validation.numeroFormatado, // Usar número formatado
        tipo: tipoSelect ? tipoSelect.value : 'pessoal',
        principal: appState.originalWhatsapp.length === 0 // Primeiro é principal
    };
    
    // Verificar se número já existe (comparar números limpos)
    const numeroLimpoExistente = appState.originalWhatsapp.some(w => 
        w.numero.replace(/[\(\)\s\-]/g, '') === validation.numeroLimpo
    );
    
    if (numeroLimpoExistente) {
        showNotification('Este número já foi adicionado', NOTIFICATION_TYPES.WARNING);
        return;
    }
    
    appState.originalWhatsapp.push(whatsapp);
    renderWhatsappList();
    updateWhatsappCount();
    
    // Limpar campos
    if (nomeInput) nomeInput.value = '';
    if (numeroInput) numeroInput.value = '';
    if (tipoSelect) tipoSelect.value = 'pessoal';
    
    // Mostrar confirmação
    showNotification(
        `WhatsApp ${validation.numeroFormatado} adicionado com sucesso!`, 
        NOTIFICATION_TYPES.SUCCESS
    );
}

/**
 * Define WhatsApp como principal
 */
function setWhatsappAsPrincipal(whatsappId) {
    console.log(`[DEBUG] setWhatsappAsPrincipal chamada com ID: ${whatsappId} (tipo: ${typeof whatsappId})`);
    
    // Converter para string para comparação consistente
    const idToSet = String(whatsappId);
    
    appState.originalWhatsapp.forEach(w => {
        w.principal = w.id === whatsappId;
    });
    renderWhatsappList();
}

/**
 * Renderiza lista de WhatsApp
 */
function renderWhatsappList() {
    const container = document.getElementById('whatsapp-list');
    if (!container) return;
    
    if (appState.originalWhatsapp.length === 0) {
        container.innerHTML = `
            <div class="empty-list">
                <i class="mdi mdi-phone-off"></i>
                <p>Nenhum número cadastrado</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = '';
    
    appState.originalWhatsapp.forEach(whatsapp => {
        const item = document.createElement('div');
        item.className = `whatsapp-list-item ${whatsapp.principal ? 'principal' : ''}`;
        item.innerHTML = `
            <div class="whatsapp-item-info">
                <div class="whatsapp-numero">
                    ${whatsapp.numero}
                    ${whatsapp.principal ? '<span class="badge-principal">Principal</span>' : ''}
                </div>
                <div class="whatsapp-meta">
                    ${whatsapp.nome ? `<span class="whatsapp-nome">${whatsapp.nome}</span>` : ''}
                    <span class="whatsapp-tipo">${whatsapp.tipo}</span>
                </div>
            </div>
            <div class="whatsapp-actions">
                ${!whatsapp.principal ? `<button type="button" class="btn-principal" onclick="setWhatsappAsPrincipal('${whatsapp.id}')" title="Definir como principal">
                    <i class="mdi mdi-star"></i>
                </button>` : ''}
                <button type="button" class="btn-remove" onclick="removeWhatsappFromList('${whatsapp.id}')" title="Remover número">
                    <i class="mdi mdi-close"></i>
                </button>
            </div>
        `;
        container.appendChild(item);
    });
}

/**
 * Atualiza contador de WhatsApp
 */
function updateWhatsappCount() {
    const countElement = document.getElementById('whatsapp-count');
    if (countElement) {
        countElement.textContent = appState.originalWhatsapp.length;
    }
}

function clearEmpresasList() {
    appState.originalEmpresas = [];
    renderEmpresasList();
    updateEmpresasCount();
    
    // Limpar busca
    const searchInput = document.getElementById('empresa-search');
    if (searchInput) {
        searchInput.value = '';
        delete searchInput.dataset.selectedEmpresaId;
        delete searchInput.dataset.selectedEmpresaNome;
        delete searchInput.dataset.selectedEmpresaCnpj;
    }
    
    const resultsContainer = document.getElementById('empresa-search-results');
    if (resultsContainer) {
        resultsContainer.classList.add('hidden');
    }
}

function clearWhatsappList() {
    appState.originalWhatsapp = [];
    renderWhatsappList();
    updateWhatsappCount();
    
    // Limpar campos
    const nomeInput = document.getElementById('whatsapp-nome');
    const numeroInput = document.getElementById('whatsapp-numero');
    const tipoSelect = document.getElementById('whatsapp-tipo');
    
    if (nomeInput) nomeInput.value = '';
    if (numeroInput) numeroInput.value = '';
    if (tipoSelect) tipoSelect.value = 'pessoal';
}

async function loadUserEmpresas(userId) {
    try {
        console.log('[USUARIOS] Carregando empresas do usuário:', userId);
        
        const response = await apiRequest(`/${userId}/empresas`);
        
        if (response.success && response.empresas) {
            // Mapear empresas para o formato esperado
            appState.originalEmpresas = response.empresas.map(empresa => ({
                id: empresa.id,
                nome_cliente: empresa.nome_cliente || empresa.razao_social,
                cnpj: Array.isArray(empresa.cnpj) ? empresa.cnpj[0] : empresa.cnpj
            }));
            
            renderEmpresasList();
            updateEmpresasCount();
            
            console.log('[USUARIOS] Empresas carregadas:', appState.originalEmpresas.length);
        } else {
            console.log('[USUARIOS] Nenhuma empresa encontrada para o usuário');
            clearEmpresasList();
        }
        
    } catch (error) {
        console.error('[USUARIOS] Erro ao carregar empresas:', error);
        clearEmpresasList();
    }
}

async function loadUserWhatsapp(userId) {
    try {
        console.log('[USUARIOS] Carregando WhatsApp do usuário:', userId);
        
        // Usar o endpoint moderno da API
        const response = await apiRequest(`/api/user/${userId}/whatsapp`);
        
        if (response.success && response.whatsapp) {
            appState.originalWhatsapp = response.whatsapp.map(whatsapp => ({
                id: whatsapp.id,
                nome: whatsapp.nome || '',
                numero: whatsapp.numero,
                tipo: whatsapp.tipo || 'pessoal',
                principal: whatsapp.principal || false
            }));
            
            renderWhatsappList();
            updateWhatsappCount();
            
            console.log('[USUARIOS] WhatsApp carregados:', appState.originalWhatsapp.length);
            
            if (response.fallback_used) {
                console.log('[USUARIOS] Dados WhatsApp vieram do campo telefone (fallback)');
            }
        } else {
            console.log('[USUARIOS] Nenhum WhatsApp encontrado para o usuário');
            clearWhatsappList();
        }
        
    } catch (error) {
        console.error('[USUARIOS] Erro ao carregar WhatsApp:', error);
        clearWhatsappList();
    }
}

async function saveUserEmpresas(userId) {
    try {
        console.log('[USUARIOS] Salvando empresas do usuário:', userId);
        
        if (appState.originalEmpresas.length === 0) {
            console.log('[USUARIOS] Nenhuma empresa para salvar');
            return Promise.resolve();
        }
        
        const empresaIds = appState.originalEmpresas.map(e => e.id);
        
        const response = await apiRequest(`/api/user/${userId}/empresas`, 'POST', {
            empresa_ids: empresaIds
        });
        
        if (!response.success) {
            throw new Error(response.error || 'Erro ao salvar empresas');
        }
        
        console.log('[USUARIOS] Empresas salvas com sucesso');
        return Promise.resolve();
        
    } catch (error) {
        console.error('[USUARIOS] Erro ao salvar empresas:', error);
        throw error;
    }
}

async function saveUserWhatsapp(userId) {
    try {
        console.log('[USUARIOS] Salvando WhatsApp do usuário:', userId);
    // Sempre enviar para que remoções sejam persistidas (lista vazia também)
    const whatsappData = appState.originalWhatsapp.map(w => ({
            nome: w.nome,
            numero: w.numero,
            tipo: w.tipo,
            principal: w.principal
        }));
    console.log('[USUARIOS] Payload WhatsApp a enviar:', whatsappData);
        const response = await apiRequest(`/api/user/${userId}/whatsapp`, 'POST', {
            whatsapp: whatsappData
        });
        
        if (!response.success) {
            throw new Error(response.error || 'Erro ao salvar WhatsApp');
        }
        
        console.log('[USUARIOS] WhatsApp salvos com sucesso');
        return Promise.resolve();
        
    } catch (error) {
        console.error('[USUARIOS] Erro ao salvar WhatsApp:', error);
        throw error;
    }
}

// =================================
// UTILIDADES
// =================================

/**
 * Mostra notificação
 */
function showNotification(message, type = NOTIFICATION_TYPES.INFO) {
    if (!elements.notificationArea) return;
    
    elements.notificationArea.textContent = message;
    elements.notificationArea.className = `notification-area ${type}`;
    elements.notificationArea.classList.remove('hidden');
    
    // Auto-ocultar após 5 segundos
    setTimeout(() => {
        elements.notificationArea.classList.add('hidden');
    }, 5000);
}

/**
 * Requisição à API com retry e tratamento de erros
 */
async function apiRequest(endpoint, method = 'GET', data = null) {
    const url = CONFIG.API_BASE_URL + endpoint;
    
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json',
            'X-API-Key': 'uniq_api_2025_dev_bypass_key'  // Para testes em desenvolvimento
        },
        credentials: 'same-origin'  // Incluir cookies de sessão
    };
    
    if (data && method !== 'GET') {
        options.body = JSON.stringify(data);
    }
    
    for (let attempt = 0; attempt < CONFIG.MAX_RETRIES; attempt++) {
        try {
            const response = await fetch(url, options);
            
            // Verificar se foi redirecionado para login
            if (response.url && response.url.includes('/auth/login')) {
                throw new Error('Sessão expirada. Por favor, faça login novamente.');
            }
            
            const result = await response.json();
            
            if (!response.ok) {
                throw new Error(result.error || `HTTP ${response.status}`);
            }
            
            return result;
            
        } catch (error) {
            if (attempt === CONFIG.MAX_RETRIES - 1) {
                throw error;
            }
            
            await new Promise(resolve => setTimeout(resolve, CONFIG.RETRY_DELAY));
        }
    }
}

// =================================
// DEBUG E LOGGING
// =================================

if (window.location.hostname === 'localhost' || window.location.hostname.includes('dev')) {
    console.log('[USUARIOS] Modo debug ativado');
    
    // Exposer algumas funções para debug
    window.usuariosDebug = {
        appState,
        elements,
        loadUsersData,
        updateKPIs,
        filterAndDisplayUsers
    };
}

// =================================
// GERENCIAMENTO DE PERFIS
// =================================

/**
 * Inicializa event listeners para perfis
 */
function initializePerfisEventListeners() {
    // Busca de perfis
    if (elements.perfisSearch) {
        elements.perfisSearch.addEventListener('input', handlePerfisSearch);
    }
    
    // Carregamento inicial de perfis disponíveis
    loadAvailablePerfis();
}

/**
 * Carrega perfis disponíveis
 */
async function loadAvailablePerfis() {
    try {
        const response = await apiRequest('/api/perfis-disponivel');
        
        if (response.success) {
            appState.perfis.available = response.perfis;
            console.log('[PERFIS] Perfis disponíveis carregados:', appState.perfis.available.length);
            renderPerfisList();
        } else {
            console.error('[PERFIS] Erro ao carregar perfis:', response.message);
            appState.perfis.available = [];
            renderPerfisList();
        }
    } catch (error) {
        console.error('[PERFIS] Erro ao carregar perfis disponíveis:', error);
        appState.perfis.available = [];
        renderPerfisList();
    }
}

/**
 * Carrega perfis do usuário atual
 */
async function loadUserPerfis(userId) {
    if (!userId) return;
    
    console.log('[PERFIS_DEBUG] Loading profiles for user:', userId);
    
    try {
        const response = await apiRequest(`/${userId}/perfis`);
        
        console.log('[PERFIS_DEBUG] Raw response from backend:', response);
        
        if (response.success) {
            const profileIds = response.perfis.map(p => p.id);
            console.log('[PERFIS_DEBUG] Profile IDs extracted from response:', profileIds);
            
            appState.perfis.selected = profileIds;
            console.log('[PERFIS] Perfis do usuário carregados:', appState.perfis.selected);
            renderPerfisList();
            updatePerfisSelectedCount();
        } else {
            console.error('[PERFIS] Erro ao carregar perfis do usuário:', response.message);
            appState.perfis.selected = [];
            renderPerfisList();
        }
    } catch (error) {
        console.error('[PERFIS] Erro ao carregar perfis do usuário:', error);
        appState.perfis.selected = [];
        renderPerfisList();
    }
}

/**
 * Manipula busca de perfis
 */
function handlePerfisSearch(e) {
    const searchTerm = e.target.value.toLowerCase();
    
    clearTimeout(appState.perfis.searchTimeout);
    appState.perfis.searchTimeout = setTimeout(() => {
        renderPerfisList(searchTerm);
    }, CONFIG.DEBOUNCE_DELAY);
}

/**
 * Renderiza lista de perfis
 */
function renderPerfisList(searchTerm = '') {
    if (!elements.perfisList) return;
    
    let filteredPerfis = appState.perfis.available;
    
    // Aplicar filtro de busca
    if (searchTerm) {
        filteredPerfis = filteredPerfis.filter(perfil => 
            perfil.perfil_nome.toLowerCase().includes(searchTerm) ||
            perfil.descricao.toLowerCase().includes(searchTerm) ||
            perfil.codigo.toLowerCase().includes(searchTerm)
        );
    }
    
    // Limpar lista
    elements.perfisList.innerHTML = '';
    
    if (filteredPerfis.length === 0) {
        elements.perfisEmpty.style.display = 'block';
        return;
    }
    
    elements.perfisEmpty.style.display = 'none';
    
    // Renderizar perfis
    filteredPerfis.forEach(perfil => {
        const perfilElement = createPerfilItem(perfil);
        elements.perfisList.appendChild(perfilElement);
    });
}

/**
 * Cria elemento de perfil
 */
function createPerfilItem(perfil) {
    const div = document.createElement('div');
    div.className = 'perfil-item';
    
    const isSelected = appState.perfis.selected.includes(perfil.id);
    if (isSelected) {
        div.classList.add('selected');
    }
    
    div.innerHTML = `
        <input type="checkbox" 
               class="perfil-checkbox" 
               data-perfil-id="${perfil.id}"
               ${isSelected ? 'checked' : ''}>
        <div class="perfil-info">
            <div class="perfil-name">${perfil.perfil_nome}</div>
            <div class="perfil-description">${perfil.descricao || 'Sem descrição'}</div>
        </div>
        <div class="perfil-codigo">${perfil.codigo}</div>
    `;
    
    // Event listener para checkbox
    const checkbox = div.querySelector('.perfil-checkbox');
    checkbox.addEventListener('change', function() {
        handlePerfilToggle(perfil.id, this.checked);
    });
    
    // Event listener para o item inteiro
    div.addEventListener('click', function(e) {
        if (e.target !== checkbox) {
            checkbox.checked = !checkbox.checked;
            handlePerfilToggle(perfil.id, checkbox.checked);
        }
    });
    
    return div;
}

/**
 * Manipula seleção/desseleção de perfil
 */
function handlePerfilToggle(perfilId, isSelected) {
    console.log('[PERFIS_DEBUG] Profile toggle called:', { perfilId, isSelected });
    console.log('[PERFIS_DEBUG] Current selected before toggle:', JSON.stringify(appState.perfis.selected));
    
    if (isSelected) {
        if (!appState.perfis.selected.includes(perfilId)) {
            appState.perfis.selected.push(perfilId);
            console.log('[PERFIS_DEBUG] Added profile:', perfilId);
        }
    } else {
        appState.perfis.selected = appState.perfis.selected.filter(id => id !== perfilId);
        console.log('[PERFIS_DEBUG] Removed profile:', perfilId);
    }
    
    console.log('[PERFIS_DEBUG] Selected after toggle:', JSON.stringify(appState.perfis.selected));
    
    // Atualizar UI
    updatePerfilItemSelection(perfilId, isSelected);
    updatePerfisSelectedCount();
    
    console.log('[PERFIS] Perfis selecionados:', appState.perfis.selected);
}

/**
 * Atualiza seleção visual do item de perfil
 */
function updatePerfilItemSelection(perfilId, isSelected) {
    const checkbox = document.querySelector(`[data-perfil-id="${perfilId}"]`);
    if (checkbox) {
        const perfilItem = checkbox.closest('.perfil-item');
        if (isSelected) {
            perfilItem.classList.add('selected');
        } else {
            perfilItem.classList.remove('selected');
        }
    }
}

/**
 * Atualiza contador de perfis selecionados
 */
function updatePerfisSelectedCount() {
    if (elements.perfisSelectedCount) {
        const count = appState.perfis.selected.length;
        elements.perfisSelectedCount.textContent = `${count} selecionado${count !== 1 ? 's' : ''}`;
    }
}

/**
 * Salva perfis do usuário
 */
async function saveUserPerfis(userId) {
    if (!userId) return;
    
    // CRITICAL FIX: Filter out 'basico' from selected profiles since it belongs only in perfil_principal
    const functionalProfiles = appState.perfis.selected.filter(profileId => profileId !== 'basico');
    
    console.log('[PERFIS_DEBUG] About to save profiles for user:', userId);
    console.log('[PERFIS_DEBUG] Selected profiles before filtering:', appState.perfis.selected);
    console.log('[PERFIS_DEBUG] Functional profiles after filtering out basico:', functionalProfiles);
    console.log('[PERFIS_DEBUG] Profile array contents:', JSON.stringify(functionalProfiles));
    
    try {
        const response = await apiRequest(`/${userId}/perfis`, 'POST', {
            perfis_ids: functionalProfiles
        });
        
        if (response.success) {
            console.log('[PERFIS] Perfis do usuário salvos com sucesso');
            return true;
        } else {
            console.error('[PERFIS] Erro ao salvar perfis:', response.message);
            
            // Provide more specific error message for permission issues
            if (response.message && response.message.includes('permissão')) {
                throw new Error(`Erro de permissão: ${response.message}`);
            } else {
                throw new Error(`Erro ao salvar perfis: ${response.message}`);
            }
        }
    } catch (error) {
        console.error('[PERFIS] Erro ao salvar perfis do usuário:', error);
        throw error; // Re-throw to be handled by caller
    }
}

/**
 * Limpa seleção de perfis
 */
function clearPerfisSelection() {
    appState.perfis.selected = [];
    renderPerfisList();
    updatePerfisSelectedCount();
}

// =================================
// SEÇÕES COLAPSÁVEIS
// =================================

/**
 * Inicializa seções colapsáveis
 */
function initializeCollapsibleSections() {
    elements.collapsibleHeaders.forEach(header => {
        header.addEventListener('click', function() {
            const targetId = this.dataset.target;
            const targetContent = document.getElementById(targetId);
            
            if (targetContent) {
                toggleCollapsibleSection(this, targetContent);
            }
        });
    });
}

/**
 * Toggle de seção colapsável
 */
function toggleCollapsibleSection(header, content) {
    const isExpanded = header.classList.contains('expanded');
    
    if (isExpanded) {
        // Colapsar
        header.classList.remove('expanded');
        content.classList.remove('expanded');
        content.classList.add('collapsed');
    } else {
        // Expandir
        header.classList.add('expanded');
        content.classList.remove('collapsed');
        content.classList.add('expanded');
    }
}

/**
 * Expande seção específica
 */
function expandSection(sectionId) {
    const content = document.getElementById(sectionId);
    const header = document.querySelector(`[data-target="${sectionId}"]`);
    
    if (content && header) {
        header.classList.add('expanded');
        content.classList.remove('collapsed');
        content.classList.add('expanded');
    }
}

/**
 * Colapsa seção específica
 */
function collapseSection(sectionId) {
    const content = document.getElementById(sectionId);
    const header = document.querySelector(`[data-target="${sectionId}"]`);
    
    if (content && header) {
        header.classList.remove('expanded');
        content.classList.remove('expanded');
        content.classList.add('collapsed');
    }
}

// =================================
// VIEW MODAL FUNCTIONALITY
// =================================

/**
 * Abre modal para visualizar usuário
 */
async function openModalForView(userId) {
    console.log('[USUARIOS] Abrindo modal de visualização para usuário:', userId);
    
    try {
        // Buscar dados do usuário
        const user = await fetchUserData(userId);
        if (!user) {
            throw new Error('Usuário não encontrado');
        }
        
        appState.currentUser = user;
        renderUserDetails(user);
        
        // Configurar botão de edição
        if (elements.btnEditFromView) {
            elements.btnEditFromView.onclick = () => {
                closeViewModal();
                setTimeout(() => openModalForEdit(userId), 100);
            };
        }
        
        // Mostrar modal
        if (elements.modalViewUsuario) {
            elements.modalViewUsuario.classList.remove('hidden');
            document.body.style.overflow = 'hidden';
        }
        
    } catch (error) {
        console.error('[USUARIOS] Erro ao carregar dados do usuário:', error);
        showNotification('Erro ao carregar dados do usuário: ' + error.message, NOTIFICATION_TYPES.ERROR);
    }
}

/**
 * Fecha modal de visualização
 */
function closeViewModal() {
    console.log('[USUARIOS] Fechando modal de visualização');
    
    if (elements.modalViewUsuario) {
        elements.modalViewUsuario.classList.add('hidden');
        document.body.style.overflow = '';
    }
    
    appState.currentUser = null;
}

/**
 * Manipula clique no botão "Editar" no modal de visualização
 */
function handleEditFromView() {
    if (appState.currentUser) {
        const userId = appState.currentUser.id;
        closeViewModal();
        setTimeout(() => openModalForEdit(userId), 100);
    }
}

/**
 * Busca dados do usuário para visualização (similar ao loadUserData mas para view)
 */
async function fetchUserData(userId) {
    console.log('[USUARIOS] Buscando dados do usuário para visualização:', userId);
    const response = await apiRequest(`/${userId}/dados`);
    
    console.log('[USUARIOS] Resposta da API para dados do usuário (view):', response);
    
    if (!response.success) {
        throw new Error(response.error || 'Erro ao carregar dados do usuário');
    }
    
    if (!response.data) {
        throw new Error('Dados do usuário não encontrados na resposta');
    }
    
    return response.data;
}

/**
 * Renderiza detalhes do usuário no modal de visualização
 */
function renderUserDetails(user) {
    if (!elements.userDetailsContent) return;
    
    // Determinar se é administrador de módulo
    const isModuleAdmin = user.perfil_principal && ['admin_operacao', 'admin_financeiro'].includes(user.perfil_principal);
    const isMasterAdmin = user.perfil_principal === 'master_admin';
    
    // NOVA LÓGICA: Verificar se tem perfis de admin baseado em is_admin_profile
    const hasAdminProfile = user.perfis && Array.isArray(user.perfis) && user.perfis.some(perfil => perfil.is_admin_profile === true);
    
    // Status
    const isActive = user.ativo === true || user.ativo === 'true';
    
    // Contar totais
    const totalEmpresas = (user.agent_info?.empresas && Array.isArray(user.agent_info.empresas)) ? user.agent_info.empresas.length : 0;
    const totalNumeros = (user.whatsapp_numbers && Array.isArray(user.whatsapp_numbers)) ? user.whatsapp_numbers.length : 0;
    const totalPerfis = (user.perfis && Array.isArray(user.perfis)) ? user.perfis.length : 0;
    
    // Gerar HTML das empresas
    const empresasHtml = user.agent_info?.empresas && user.agent_info.empresas.length > 0 ? user.agent_info.empresas.map(empresa => `
        <div class="detail-item-badge">
            <i class="mdi mdi-domain"></i>
            <span>${empresa.nome_cliente || empresa.nome || empresa.empresa_nome || 'Empresa sem nome'}</span>
        </div>
    `).join('') : '<span class="text-muted">Nenhuma empresa vinculada</span>';
    
    // Gerar HTML dos perfis
    const perfisHtml = user.perfis && user.perfis.length > 0 ? user.perfis.map(perfil => `
        <div class="detail-item-badge">
            <i class="mdi mdi-shield-account"></i>
            <span>${perfil.perfil_nome || perfil.nome || 'Perfil sem nome'}</span>
        </div>
    `).join('') : '<span class="text-muted">Nenhum perfil atribuído</span>';
    
    // Gerar HTML dos números WhatsApp
    const whatsappHtml = user.whatsapp_numbers && user.whatsapp_numbers.length > 0 ? user.whatsapp_numbers.map(whatsapp => `
        <div class="detail-item-badge">
            <i class="mdi mdi-whatsapp"></i>
            <span>${whatsapp.nome || 'Sem nome'}: ${whatsapp.numero}</span>
        </div>
    `).join('') : '<span class="text-muted">Nenhum número cadastrado</span>';
    
    elements.userDetailsContent.innerHTML = `
        <div class="user-details">
            <div class="detail-section">
                <h6 class="detail-section-title">
                    <i class="mdi mdi-information"></i>
                    Informações Gerais
                </h6>
                <div class="detail-item">
                    <span class="detail-label">Nome:</span>
                    <span class="detail-value">${user.nome || user.name || 'Sem nome'}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Email:</span>
                    <span class="detail-value">${user.email || 'Sem email'}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Perfil de Acesso:</span>
                    <span class="detail-value">${ROLE_CONFIG[user.role]?.label || user.role}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Tipo de Administrador:</span>
                    <span class="detail-value">
                        ${
                            isMasterAdmin ? '<span class="admin-badge master"><i class="mdi mdi-shield-crown"></i> Master Admin</span>' :
                            hasAdminProfile ? '<span class="admin-badge module"><i class="mdi mdi-shield"></i> Administrador de Módulo</span>' :
                            '<span class="text-muted">Usuário Regular</span>'
                        }
                    </span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Status:</span>
                    <span class="detail-value">
                        <span class="status-badge status-${isActive ? 'active' : 'inactive'}">
                            <span class="status-dot"></span>
                            ${isActive ? 'Ativo' : 'Inativo'}
                        </span>
                    </span>
                </div>
            </div>
            
            <div class="detail-section">
                <h6 class="detail-section-title">
                    <i class="mdi mdi-chart-box"></i>
                    Estatísticas
                </h6>
                <div class="detail-stats-grid">
                    <div class="detail-stat">
                        <div class="detail-stat-value">${totalEmpresas}</div>
                        <div class="detail-stat-label">Empresas</div>
                    </div>
                    <div class="detail-stat">
                        <div class="detail-stat-value">${totalNumeros}</div>
                        <div class="detail-stat-label">Números WhatsApp</div>
                    </div>
                    <div class="detail-stat">
                        <div class="detail-stat-value">${totalPerfis}</div>
                        <div class="detail-stat-label">Perfis</div>
                    </div>
                </div>
            </div>
            
            <div class="detail-section">
                <h6 class="detail-section-title">
                    <i class="mdi mdi-domain"></i>
                    Empresas Vinculadas
                </h6>
                <div class="detail-items-list">
                    ${empresasHtml}
                </div>
            </div>
            
            <div class="detail-section">
                <h6 class="detail-section-title">
                    <i class="mdi mdi-shield-account"></i>
                    Perfis de Acesso
                </h6>
                <div class="detail-items-list">
                    ${perfisHtml}
                </div>
            </div>
            
            <div class="detail-section">
                <h6 class="detail-section-title">
                    <i class="mdi mdi-whatsapp"></i>
                    Números WhatsApp
                </h6>
                <div class="detail-items-list">
                    ${whatsappHtml}
                </div>
            </div>
        </div>
    `;
    
    // Atualizar título do modal
    if (elements.viewModalTitle) {
        elements.viewModalTitle.textContent = `Detalhes: ${user.nome || user.name || 'Usuário'}`;
    }
}

/**
 * Inicializa seções colapsáveis
 */
function initializeCollapsibleSections() {
    console.log('[USUARIOS] Inicializando seções colapsáveis...');
    
    const collapsibleHeaders = document.querySelectorAll('.collapsible-header');
    
    collapsibleHeaders.forEach(header => {
        header.addEventListener('click', function() {
            const targetId = this.getAttribute('data-target');
            const targetContent = document.getElementById(targetId);
            
            if (!targetContent) {
                console.warn('[USUARIOS] Elemento alvo não encontrado:', targetId);
                return;
            }
            
            // Toggle classes
            this.classList.toggle('expanded');
            targetContent.classList.toggle('collapsed');
            targetContent.classList.toggle('expanded');
            
            // Update icon
            const icon = this.querySelector('.collapse-icon');
            if (icon) {
                if (this.classList.contains('expanded')) {
                    icon.style.transform = 'rotate(180deg)';
                } else {
                    icon.style.transform = 'rotate(0deg)';
                }
            }
            
            console.log('[USUARIOS] Seção toggled:', targetId, this.classList.contains('expanded'));
        });
    });
    
    console.log('[USUARIOS] Seções colapsáveis inicializadas:', collapsibleHeaders.length);
}
