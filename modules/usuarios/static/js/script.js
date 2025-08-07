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
        description: 'Acesso total ao sistema'
    },
    interno_unique: {
        label: 'Equipe Interna',
        icon: 'mdi-account-tie',
        color: 'info',
        description: 'Colaboradores da Unique'
    },
    cliente_unique: {
        label: 'Cliente',
        icon: 'mdi-domain',
        color: 'warning',
        description: 'Empresas clientes'
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
        
        // Modal
        modalUsuario: document.getElementById('modal-usuario'),
        modalTitle: document.getElementById('modal-title'),
        modalDeleteConfirm: document.getElementById('modal-delete-confirm'),
        
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
        
        // Grids
        gridAdmin: document.getElementById('grid-admin'),
        gridInterno: document.getElementById('grid-interno'),
        gridClientes: document.getElementById('grid-clientes'),
        
        // Counts
        countAdmin: document.getElementById('count-admin'),
        countInterno: document.getElementById('count-interno'),
        countClientes: document.getElementById('count-clientes'),
        
        // Empty State
        emptyState: document.getElementById('empty-state'),
        
        // Notification
        notificationArea: document.getElementById('notification-area'),
        
        // User Card Template
        userCardTemplate: document.getElementById('user-card-template')
    };
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
    
    if (elements.modalUsuario) {
        elements.modalUsuario.addEventListener('click', function(e) {
            if (e.target === elements.modalUsuario) {
                closeModal();
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
    
    // Empresas e WhatsApp
    initializeEmpresasEventListeners();
    initializeWhatsappEventListeners();
    
    // ESC para fechar modal
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && !elements.modalUsuario.classList.contains('hidden')) {
            closeModal();
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
    
    // Atualizar KPIs
    elements.kpiAdmin.textContent = adminCount;
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
    
    // Atualizar contadores das seções
    elements.countAdmin.textContent = usersByRole.admin.length;
    elements.countInterno.textContent = usersByRole.interno_unique.length;
    elements.countClientes.textContent = usersByRole.cliente_unique.length;
    
    // Renderizar usuários em cada seção
    renderUsersInGrid(elements.gridAdmin, usersByRole.admin);
    renderUsersInGrid(elements.gridInterno, usersByRole.interno_unique);
    renderUsersInGrid(elements.gridClientes, usersByRole.cliente_unique);
    
    // Mostrar/ocultar seções baseado na presença de usuários
    toggleSectionVisibility(elements.sectionAdmin, usersByRole.admin.length > 0);
    toggleSectionVisibility(elements.sectionInterno, usersByRole.interno_unique.length > 0);
    toggleSectionVisibility(elements.sectionClientes, usersByRole.cliente_unique.length > 0);
    
    // Mostrar empty state se não há usuários filtrados
    const hasUsers = appState.filteredUsers.length > 0;
    showEmptyState(!hasUsers);
}

/**
 * Renderiza usuários em um grid específico
 */
function renderUsersInGrid(gridElement, users) {
    if (!gridElement) {
        console.warn('[USUARIOS] Grid element não encontrado para renderização');
        return;
    }
    
    console.log('[USUARIOS] Renderizando', users.length, 'usuários no grid', gridElement.id);
    
    gridElement.innerHTML = '';
    
    users.forEach((user, index) => {
        console.log(`[USUARIOS] Criando card ${index + 1}:`, user);
        const cardElement = createUserCard(user);
        gridElement.appendChild(cardElement);
    });
    
    console.log('[USUARIOS] Renderização completa para grid', gridElement.id);
}

/**
 * Cria card de usuário
 */
function createUserCard(user) {
    const template = elements.userCardTemplate.content.cloneNode(true);
    
    // Substituir placeholders
    const cardHtml = template.querySelector('.user-card').outerHTML
        .replace(/\{user_id\}/g, user.id)
        .replace(/\{user_name\}/g, user.nome || 'Sem nome')
        .replace(/\{user_email\}/g, user.email || 'Sem email')
        .replace(/\{role\}/g, user.role)
        .replace(/\{role_label\}/g, ROLE_CONFIG[user.role]?.label || user.role)
        .replace(/\{status\}/g, (user.ativo === true || user.ativo === 'true') ? 'active' : 'inactive')
        .replace(/\{status_class\}/g, (user.ativo === true || user.ativo === 'true') ? 'active' : 'inactive')
        .replace(/\{user_cargo_html\}/g, '') // Campo cargo removido
        .replace(/\{empresas_info\}/g, generateEmpresasInfo(user))
        .replace(/\{whatsapp_info\}/g, generateWhatsappInfo(user));
    
    // Criar elemento DOM
    const div = document.createElement('div');
    div.innerHTML = cardHtml;
    
    return div.firstElementChild;
}

/**
 * Gera informações de empresas para o card
 */
function generateEmpresasInfo(user) {
    // Usar a estrutura correta retornada pela API
    const empresas = user.agent_info?.empresas || [];
    const empresasCount = empresas.length;
    
    if (empresasCount > 0) {
        return `<div class="user-companies">
            <i class="mdi mdi-domain"></i>
            ${empresasCount} empresa(s)
        </div>`;
    }
    
    return '';
}

/**
 * Gera informações de WhatsApp para o card
 */
function generateWhatsappInfo(user) {
    // Usar a estrutura correta retornada pela API
    const whatsappNumbers = user.whatsapp_numbers || [];
    const whatsappCount = whatsappNumbers.length;
    
    if (whatsappCount > 0) {
        return `<div class="user-whatsapp">
            <i class="mdi mdi-whatsapp"></i>
            ${whatsappCount} número(s)
        </div>`;
    }
    
    return '';
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
    
    handleRoleChange();
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
    
    if (!validateForm()) {
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
 * Cria novo usuário
 */
async function createUser() {
    const userData = collectUserFormData();
    
    const response = await apiRequest('/salvar', 'POST', userData);
    
    if (!response.success) {
        throw new Error(response.error || 'Erro ao criar usuário');
    }
    
    const userId = response.user_id;
    
    // Salvar empresas e WhatsApp se necessário
    // Empresas são permitidas para cliente_unique E interno_unique
    if (userData.role === 'cliente_unique' || userData.role === 'interno_unique') {
        await saveUserEmpresas(userId);
    }
    
    await saveUserWhatsapp(userId);
    
    showNotification('Usuário criado com sucesso!', NOTIFICATION_TYPES.SUCCESS);
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
    
    showNotification('Usuário atualizado com sucesso!', NOTIFICATION_TYPES.SUCCESS);
}

/**
 * Coleta dados do formulário
 */
function collectUserFormData() {
    return {
        name: document.getElementById('nome').value.trim(),
        email: document.getElementById('email').value.trim(),
        role: document.getElementById('role').value,
        is_active: document.getElementById('ativo').checked,
        password: document.getElementById('senha')?.value,
        confirm_password: document.getElementById('confirmar_senha')?.value
    };
}

/**
 * Valida formulário
 */
function validateForm() {
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
 * Abre modal de edição (chamada pelos cards)
 */
window.openEditModal = function(userId) {
    openModalForEdit(userId);
};

/**
 * Deleta usuário (chamada pelos cards)
 */
window.deleteUser = function(userId, userName) {
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
 * Mostra modal de confirmação de exclusão
 */
function showDeleteConfirmation(userId, userName) {
    const deleteModal = elements.modalDeleteConfirm;
    const deleteUserName = document.getElementById('delete-user-name');
    const btnConfirmDelete = document.getElementById('btn-confirm-delete');
    
    if (deleteUserName) {
        deleteUserName.textContent = userName;
    }
    
    if (btnConfirmDelete) {
        btnConfirmDelete.onclick = () => confirmDelete(userId);
    }
    
    if (deleteModal) {
        deleteModal.classList.remove('hidden');
    }
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
    if (elements.modalDeleteConfirm) {
        elements.modalDeleteConfirm.classList.add('hidden');
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
 * Formato esperado: (dd)xxxxxxxxx ou ddxxxxxxxxx (11 dígitos)
 */
function validateWhatsappNumber(numero) {
    if (!numero) return false;
    
    // Remover formatação (parênteses, espaços, traços)
    const numeroLimpo = numero.replace(/[\(\)\s\-]/g, '');
    
    // Verificar se tem exatamente 11 dígitos
    if (!/^\d{11}$/.test(numeroLimpo)) {
        return {
            valid: false,
            message: 'Número deve ter 11 dígitos no formato: (dd)xxxxxxxxx',
            exemplo: 'Exemplo: (11)987654321 ou 11987654321'
        };
    }
    
    // Verificar se os dois primeiros dígitos são DDD válido (11-99)
    const ddd = parseInt(numeroLimpo.substring(0, 2));
    if (ddd < 11 || ddd > 99) {
        return {
            valid: false,
            message: 'DDD deve estar entre 11 e 99',
            exemplo: 'Exemplo: (11)987654321 ou 11987654321'
        };
    }
    
    // Verificar se o terceiro dígito é 9 (celular)
    if (numeroLimpo[2] !== '9') {
        return {
            valid: false,
            message: 'Número deve ser de celular (terceiro dígito deve ser 9)',
            exemplo: 'Exemplo: (11)987654321 ou 11987654321'
        };
    }
    
    return {
        valid: true,
        numeroLimpo: numeroLimpo,
        numeroFormatado: `(${numeroLimpo.substring(0, 2)})${numeroLimpo.substring(2)}`
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
        showNotification(
            `Formato inválido: ${validation.message}. ${validation.exemplo}`, 
            NOTIFICATION_TYPES.ERROR
        );
        numeroInput.focus();
        return;
    }
    
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
        
        if (appState.originalWhatsapp.length === 0) {
            console.log('[USUARIOS] Nenhum WhatsApp para salvar');
            return Promise.resolve();
        }
        
        const whatsappData = appState.originalWhatsapp.map(w => ({
            nome: w.nome,
            numero: w.numero,
            tipo: w.tipo,
            principal: w.principal
        }));
        
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
            'Content-Type': 'application/json'
            // REMOVIDO: X-API-Key - usar autenticação de sessão normal
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
