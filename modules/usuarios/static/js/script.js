/**
 * MÓDULO DE GERENCIAMENTO DE USUÁRIOS
 * Sistema completo de CRUD com gestão de empresas e WhatsApp
 * 
 * Funcionalidades:
 * - CRUD de usuários
 * - Gestão de empresas associadas
 * - Gestão de números WhatsApp
 * - Busca e filtros
 * - Interface responsiva
 */

// =================================
// CONFIGURAÇÕES E CONSTANTES
// =================================

const CONFIG = {
    API_BASE_URL: '/usuarios',
    API_BYPASS_KEY: 'uniq_api_2025_dev_bypass_key',
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

// =================================
// ESTADO GLOBAL DA APLICAÇÃO
// =================================

let appState = {
    currentUser: null,
    currentMode: null,
    originalEmpresas: [],
    originalWhatsapp: [],
    searchTimeout: null,
    isLoading: false,
    empresaSearchTimeout: null
};

// =================================
// ELEMENTOS DOM PRINCIPAIS
// =================================

let elements = {};

// =================================
// INICIALIZAÇÃO
// =================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('[USUARIOS] Inicializando módulo de usuários...');
    
    initializeElements();
    initializeEventListeners();
    initializeTableSearch();
    
    console.log('[USUARIOS] Módulo inicializado com sucesso');
});

/**
 * Inicializa referências dos elementos DOM
 */
function initializeElements() {
    elements = {
        // Tabela e busca
        searchInput: document.getElementById('search-usuarios'),
        usersTable: document.querySelector('.users-table tbody'),
        refreshBtn: document.getElementById('btn-refresh'),
        
        // Modal principal
        modal: document.getElementById('modal-usuario'),
        modalTitle: document.getElementById('modal-title'),
        modalForm: document.getElementById('form-usuario'),
        formLoading: document.getElementById('form-loading'),
        
        // Botões do modal
        btnNovoUsuario: document.getElementById('btn-novo-usuario'),
        btnCloseModal: document.getElementById('btn-close-modal'),
        btnCancel: document.getElementById('btn-cancel'),
        btnSave: document.getElementById('btn-save'),
        saveText: document.getElementById('save-text'),
        
        // Campos do formulário
        userName: document.getElementById('user-name'),
        userEmail: document.getElementById('user-email'),
        userRole: document.getElementById('user-role'),
        userActive: document.getElementById('user-active'),
        userPassword: document.getElementById('user-password'),
        userConfirmPassword: document.getElementById('user-confirm-password'),
        
        // Seções do formulário
        passwordSection: document.getElementById('password-section'),
        empresasSection: document.getElementById('empresas-section'),
        whatsappSection: document.getElementById('whatsapp-section'),
        
        // Empresas
        empresaSearch: document.getElementById('empresa-search'),
        empresaSearchResults: document.getElementById('empresa-search-results'),
        btnAddEmpresa: document.getElementById('btn-add-empresa'),
        empresasList: document.getElementById('empresas-list'),
        empresasCount: document.getElementById('empresas-count'),
        
        // WhatsApp
        whatsappNumero: document.getElementById('whatsapp-numero'),
        whatsappNome: document.getElementById('whatsapp-nome'),
        whatsappTipo: document.getElementById('whatsapp-tipo'),
        btnAddWhatsapp: document.getElementById('btn-add-whatsapp'),
        whatsappList: document.getElementById('whatsapp-list'),
        whatsappCount: document.getElementById('whatsapp-count'),
        
        // Modal de confirmação
        deleteModal: document.getElementById('modal-delete-confirm'),
        deleteUserName: document.getElementById('delete-user-name'),
        btnCancelDelete: document.getElementById('btn-cancel-delete'),
        btnConfirmDelete: document.getElementById('btn-confirm-delete'),
        
        // Notificações
        notificationArea: document.getElementById('notification-area')
    };
}

/**
 * Inicializa todos os event listeners
 */
function initializeEventListeners() {
    // Botões principais
    elements.btnNovoUsuario?.addEventListener('click', () => openModalForCreate());
    elements.refreshBtn?.addEventListener('click', () => refreshUsersList());
    
    // Modal
    elements.btnCloseModal?.addEventListener('click', () => closeModal());
    elements.btnCancel?.addEventListener('click', () => closeModal());
    elements.modal?.addEventListener('click', (e) => {
        if (e.target === elements.modal) closeModal();
    });
    
    // Formulário
    elements.modalForm?.addEventListener('submit', handleFormSubmit);
    elements.userRole?.addEventListener('change', handleRoleChange);
    
    // Empresas
    elements.empresaSearch?.addEventListener('input', handleEmpresaSearch);
    elements.btnAddEmpresa?.addEventListener('click', handleAddEmpresa);
    
    // WhatsApp
    elements.btnAddWhatsapp?.addEventListener('click', handleAddWhatsapp);
    
    // Modal de exclusão
    elements.btnCancelDelete?.addEventListener('click', () => hideDeleteModal());
    elements.btnConfirmDelete?.addEventListener('click', handleConfirmDelete);
    
    // Botões da tabela (delegação de eventos)
    elements.usersTable?.addEventListener('click', handleTableButtonClick);
    
    // Escape key para fechar modais
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            if (!elements.modal?.classList.contains('hidden')) {
                closeModal();
            }
            if (!elements.deleteModal?.classList.contains('hidden')) {
                hideDeleteModal();
            }
        }
    });
}

/**
 * Inicializa a busca na tabela
 */
function initializeTableSearch() {
    if (!elements.searchInput) return;
    
    elements.searchInput.addEventListener('input', (e) => {
        clearTimeout(appState.searchTimeout);
        appState.searchTimeout = setTimeout(() => {
            filterUsersTable(e.target.value);
        }, CONFIG.DEBOUNCE_DELAY);
    });
}

// =================================
// GERENCIAMENTO DE MODAL
// =================================

/**
 * Abre modal para criar novo usuário
 */
function openModalForCreate() {
    console.log('[USUARIOS] Abrindo modal para novo usuário');
    
    appState.currentMode = MODAL_MODES.CREATE;
    appState.currentUser = null;
    appState.originalEmpresas = [];
    appState.originalWhatsapp = [];
    
    // Atualizar título e textos
    elements.modalTitle.textContent = 'Novo Usuário';
    elements.saveText.textContent = 'Criar Usuário';
    
    // Limpar formulário
    clearForm();
    
    // Mostrar campos de senha
    showPasswordSection();
    
    // Ocultar seção de empresas por padrão
    hideEmpresasSection();
    
    // Limpar listas
    clearEmpresasList();
    clearWhatsappList();
    
    // Mostrar modal
    showModal();
}

/**
 * Abre modal para editar usuário existente
 */
async function openModalForEdit(userId) {
    console.log(`[USUARIOS] Abrindo modal para editar usuário: ${userId}`);
    
    appState.currentMode = MODAL_MODES.EDIT;
    appState.currentUser = { id: userId };
    
    // Atualizar título e textos
    elements.modalTitle.textContent = 'Editar Usuário';
    elements.saveText.textContent = 'Salvar Alterações';
    
    // Ocultar campos de senha
    hidePasswordSection();
    
    // Mostrar loading
    showFormLoading();
    
    // Mostrar modal
    showModal();
    
    try {
        // Carregar dados do usuário
        await loadUserData(userId);
        
    } catch (error) {
        console.error('[USUARIOS] Erro ao carregar dados:', error);
        showNotification('Erro ao carregar dados do usuário', NOTIFICATION_TYPES.ERROR);
        closeModal();
    } finally {
        hideFormLoading();
    }
}

/**
 * Carrega os dados completos do usuário
 */
async function loadUserData(userId) {
    console.log(`[USUARIOS] Carregando dados do usuário: ${userId}`);
    
    const [userData, empresasData, whatsappData] = await Promise.all([
        apiRequest(`/api/user/${userId}`, 'GET'),
        apiRequest(`/api/user/${userId}/empresas`, 'GET'),
        apiRequest(`/api/user/${userId}/whatsapp`, 'GET')
    ]);
    
    if (!userData.success) {
        throw new Error(userData.error || 'Erro ao carregar dados do usuário');
    }
    
    // Preencher dados básicos
    fillUserForm(userData.user);
    
    // Carregar empresas se aplicável
    if (empresasData.success && empresasData.empresas) {
        appState.originalEmpresas = [...empresasData.empresas];
        populateEmpresasList(empresasData.empresas);
    }
    
    // Carregar WhatsApp
    if (whatsappData.success && whatsappData.whatsapp) {
        appState.originalWhatsapp = [...whatsappData.whatsapp];
        populateWhatsappList(whatsappData.whatsapp);
    }
    
    // Ajustar visibilidade das seções baseado no role
    handleRoleChange();
    
    console.log('[USUARIOS] Dados carregados com sucesso');
}

/**
 * Preenche o formulário com dados do usuário
 */
function fillUserForm(user) {
    elements.userName.value = user.name || '';
    elements.userEmail.value = user.email || '';
    elements.userRole.value = user.role || '';
    elements.userActive.checked = user.is_active !== false;
    
    // Salvar dados do usuário atual
    appState.currentUser = { ...user };
}

/**
 * Fecha o modal
 */
function closeModal() {
    console.log('[USUARIOS] Fechando modal');
    
    hideModal();
    clearForm();
    appState.currentUser = null;
    appState.currentMode = null;
    appState.originalEmpresas = [];
    appState.originalWhatsapp = [];
}

/**
 * Mostra o modal
 */
function showModal() {
    elements.modal?.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
    
    // Focus no primeiro campo
    setTimeout(() => {
        elements.userName?.focus();
    }, 100);
}

/**
 * Oculta o modal
 */
function hideModal() {
    elements.modal?.classList.add('hidden');
    document.body.style.overflow = '';
}

/**
 * Mostra indicador de loading no formulário
 */
function showFormLoading() {
    elements.formLoading?.classList.remove('hidden');
    elements.modalForm?.style.setProperty('display', 'none');
}

/**
 * Oculta indicador de loading no formulário
 */
function hideFormLoading() {
    elements.formLoading?.classList.add('hidden');
    elements.modalForm?.style.removeProperty('display');
}

// =================================
// GERENCIAMENTO DE SEÇÕES
// =================================

/**
 * Manipula mudança no campo Role
 */
function handleRoleChange() {
    const role = elements.userRole?.value;
    
    if (role === 'interno_unique' || role === 'cliente_unique') {
        showEmpresasSection();
    } else {
        hideEmpresasSection();
    }
}

/**
 * Mostra seção de empresas
 */
function showEmpresasSection() {
    elements.empresasSection?.classList.remove('hidden');
}

/**
 * Oculta seção de empresas
 */
function hideEmpresasSection() {
    elements.empresasSection?.classList.add('hidden');
}

/**
 * Mostra seção de senha
 */
function showPasswordSection() {
    elements.passwordSection?.classList.remove('hidden');
    elements.userPassword.required = true;
    elements.userConfirmPassword.required = true;
}

/**
 * Oculta seção de senha
 */
function hidePasswordSection() {
    elements.passwordSection?.classList.add('hidden');
    elements.userPassword.required = false;
    elements.userConfirmPassword.required = false;
}

// =================================
// GERENCIAMENTO DE EMPRESAS
// =================================

/**
 * Manipula busca de empresas
 */
function handleEmpresaSearch(e) {
    const query = e.target.value.trim();
    
    clearTimeout(appState.empresaSearchTimeout);
    
    if (query.length < 3) {
        hideEmpresaSearchResults();
        elements.btnAddEmpresa.disabled = true;
        return;
    }
    
    appState.empresaSearchTimeout = setTimeout(async () => {
        await searchEmpresas(query);
    }, CONFIG.DEBOUNCE_DELAY);
}

/**
 * Busca empresas na API
 */
async function searchEmpresas(query) {
    console.log(`[USUARIOS] Buscando empresas: ${query}`);
    
    try {
        const response = await apiRequest('/api/empresas/buscar', 'POST', { cnpj: query });
        
        if (response.success) {
            if (response.empresas && response.empresas.length > 0) {
                showEmpresaSearchResults(response.empresas);
            } else if (response.empresa) {
                showEmpresaSearchResults([response.empresa]);
            } else {
                showEmpresaSearchResults([]);
            }
        } else {
            showEmpresaSearchResults([]);
        }
    } catch (error) {
        console.error('[USUARIOS] Erro ao buscar empresas:', error);
        showEmpresaSearchResults([]);
    }
}

/**
 * Mostra resultados da busca de empresas
 */
function showEmpresaSearchResults(empresas) {
    const resultsContainer = elements.empresaSearchResults;
    
    if (empresas.length === 0) {
        resultsContainer.innerHTML = `
            <div class="search-result-item">
                <div class="search-result-name">Nenhuma empresa encontrada</div>
            </div>
        `;
        elements.btnAddEmpresa.disabled = true;
    } else {
        resultsContainer.innerHTML = empresas.map(empresa => `
            <div class="search-result-item" data-empresa-id="${empresa.id}" data-empresa-cnpj="${empresa.cnpj || empresa.cnpjs}">
                <div class="search-result-name">${empresa.nome_cliente || empresa.razao_social}</div>
                <div class="search-result-cnpj">${empresa.cnpj || empresa.cnpjs}</div>
            </div>
        `).join('');
        
        // Adicionar event listeners aos resultados
        resultsContainer.querySelectorAll('.search-result-item').forEach(item => {
            if (!item.textContent.includes('Nenhuma empresa')) {
                item.addEventListener('click', () => selectEmpresaFromSearch(item));
            }
        });
        
        elements.btnAddEmpresa.disabled = false;
    }
    
    resultsContainer.classList.remove('hidden');
}

/**
 * Seleciona empresa dos resultados
 */
function selectEmpresaFromSearch(item) {
    const empresaId = item.dataset.empresaId;
    const empresaCnpj = item.dataset.empresaCnpj;
    const empresaNome = item.querySelector('.search-result-name').textContent;
    
    elements.empresaSearch.value = `${empresaNome} - ${empresaCnpj}`;
    elements.empresaSearch.dataset.selectedId = empresaId;
    elements.empresaSearch.dataset.selectedCnpj = empresaCnpj;
    elements.empresaSearch.dataset.selectedNome = empresaNome;
    
    hideEmpresaSearchResults();
    elements.btnAddEmpresa.disabled = false;
}

/**
 * Oculta resultados da busca
 */
function hideEmpresaSearchResults() {
    elements.empresaSearchResults?.classList.add('hidden');
}

/**
 * Adiciona empresa à lista
 */
function handleAddEmpresa() {
    const empresaId = elements.empresaSearch.dataset.selectedId;
    const empresaCnpj = elements.empresaSearch.dataset.selectedCnpj;
    const empresaNome = elements.empresaSearch.dataset.selectedNome;
    
    if (!empresaId || !empresaCnpj || !empresaNome) {
        showNotification('Selecione uma empresa válida', NOTIFICATION_TYPES.WARNING);
        return;
    }
    
    // Verificar se já está na lista
    const existingItem = elements.empresasList.querySelector(`[data-empresa-id="${empresaId}"]`);
    if (existingItem) {
        showNotification('Empresa já está na lista', NOTIFICATION_TYPES.WARNING);
        return;
    }
    
    // Adicionar à lista
    addEmpresaToList({
        id: empresaId,
        cnpjs: empresaCnpj,
        nome_cliente: empresaNome
    });
    
    // Limpar busca
    elements.empresaSearch.value = '';
    delete elements.empresaSearch.dataset.selectedId;
    delete elements.empresaSearch.dataset.selectedCnpj;
    delete elements.empresaSearch.dataset.selectedNome;
    elements.btnAddEmpresa.disabled = true;
    hideEmpresaSearchResults();
    
    showNotification('Empresa adicionada à lista', NOTIFICATION_TYPES.SUCCESS);
}

/**
 * Adiciona empresa à lista visualmente
 */
function addEmpresaToList(empresa) {
    // Remover empty state se existir
    const emptyState = elements.empresasList.querySelector('.empty-list');
    if (emptyState) {
        emptyState.remove();
    }
    
    const empresaElement = document.createElement('div');
    empresaElement.className = 'empresa-item fade-in';
    empresaElement.dataset.empresaId = empresa.id;
    empresaElement.innerHTML = `
        <div class="empresa-info">
            <div class="empresa-name">${empresa.nome_cliente}</div>
            <div class="empresa-cnpj">${empresa.cnpjs}</div>
        </div>
        <div class="item-actions">
            <button type="button" class="btn-remove" onclick="removeEmpresaFromList(this)" title="Remover empresa">
                <i class="mdi mdi-delete"></i>
            </button>
        </div>
    `;
    
    elements.empresasList.appendChild(empresaElement);
    updateEmpresasCount();
}

/**
 * Remove empresa da lista
 */
function removeEmpresaFromList(button) {
    const empresaItem = button.closest('.empresa-item');
    if (empresaItem) {
        empresaItem.remove();
        updateEmpresasCount();
        
        // Adicionar empty state se necessário
        if (elements.empresasList.children.length === 0) {
            elements.empresasList.innerHTML = `
                <div class="empty-list">
                    <i class="mdi mdi-domain-off"></i>
                    <p>Nenhuma empresa associada</p>
                </div>
            `;
        }
        
        showNotification('Empresa removida da lista', NOTIFICATION_TYPES.SUCCESS);
    }
}

/**
 * Popula lista de empresas com dados carregados
 */
function populateEmpresasList(empresas) {
    clearEmpresasList();
    
    if (!empresas || empresas.length === 0) {
        return;
    }
    
    empresas.forEach(empresa => {
        addEmpresaToList(empresa);
    });
}

/**
 * Limpa lista de empresas
 */
function clearEmpresasList() {
    elements.empresasList.innerHTML = `
        <div class="empty-list">
            <i class="mdi mdi-domain-off"></i>
            <p>Nenhuma empresa associada</p>
        </div>
    `;
    updateEmpresasCount();
}

/**
 * Atualiza contador de empresas
 */
function updateEmpresasCount() {
    const count = elements.empresasList.querySelectorAll('.empresa-item').length;
    elements.empresasCount.textContent = count;
}

/**
 * Obtém lista atual de empresas
 */
function getCurrentEmpresas() {
    const empresaItems = elements.empresasList.querySelectorAll('.empresa-item');
    return Array.from(empresaItems).map(item => ({
        id: parseInt(item.dataset.empresaId), // Converter para número
        nome_cliente: item.querySelector('.empresa-name').textContent,
        cnpjs: item.querySelector('.empresa-cnpj').textContent
    }));
}

// =================================
// GERENCIAMENTO DE WHATSAPP
// =================================

/**
 * Adiciona número WhatsApp
 */
function handleAddWhatsapp() {
    const numero = elements.whatsappNumero.value.trim();
    const nome = elements.whatsappNome.value.trim();
    const tipo = elements.whatsappTipo.value;
    
    // Validações
    if (!numero || !nome) {
        showNotification('Número e nome são obrigatórios', NOTIFICATION_TYPES.WARNING);
        return;
    }
    
    // Validar formato do número
    const phoneRegex = /^\+[1-9]\d{1,14}$/;
    if (!phoneRegex.test(numero)) {
        showNotification('Formato do número inválido. Use formato internacional (+55...)', NOTIFICATION_TYPES.WARNING);
        return;
    }
    
    // Verificar se já existe
    const existingItem = elements.whatsappList.querySelector(`[data-whatsapp-numero="${numero}"]`);
    if (existingItem) {
        showNotification('Número já está na lista', NOTIFICATION_TYPES.WARNING);
        return;
    }
    
    // Adicionar à lista
    addWhatsappToList({
        numero_whatsapp: numero,
        nome_contato: nome,
        tipo_numero: tipo,
        principal: false
    });
    
    // Limpar campos
    elements.whatsappNumero.value = '';
    elements.whatsappNome.value = '';
    elements.whatsappTipo.value = 'pessoal';
    
    showNotification('Número WhatsApp adicionado à lista', NOTIFICATION_TYPES.SUCCESS);
}

/**
 * Adiciona WhatsApp à lista visualmente
 */
function addWhatsappToList(whatsapp) {
    // Remover empty state se existir
    const emptyState = elements.whatsappList.querySelector('.empty-list');
    if (emptyState) {
        emptyState.remove();
    }
    
    const whatsappElement = document.createElement('div');
    whatsappElement.className = 'whatsapp-item fade-in';
    whatsappElement.dataset.whatsappId = whatsapp.id || 'new';
    whatsappElement.dataset.whatsappNumero = whatsapp.numero_whatsapp;
    
    const principalBadge = whatsapp.principal ? 
        '<span class="principal-badge"><i class="mdi mdi-star"></i> Principal</span>' : '';
    
    whatsappElement.innerHTML = `
        <div class="whatsapp-info">
            <div class="whatsapp-name">${whatsapp.nome_contato}</div>
            <div class="whatsapp-details">
                <span>${whatsapp.numero_whatsapp}</span>
                <span class="tipo-badge tipo-${whatsapp.tipo_numero}">${whatsapp.tipo_numero}</span>
                ${principalBadge}
            </div>
        </div>
        <div class="item-actions">
            <button type="button" class="btn-principal ${whatsapp.principal ? 'active' : ''}" 
                    onclick="toggleWhatsappPrincipal(this)" 
                    title="${whatsapp.principal ? 'Principal' : 'Definir como principal'}">
                <i class="mdi mdi-star"></i>
            </button>
            <button type="button" class="btn-remove" onclick="removeWhatsappFromList(this)" title="Remover número">
                <i class="mdi mdi-delete"></i>
            </button>
        </div>
    `;
    
    elements.whatsappList.appendChild(whatsappElement);
    updateWhatsappCount();
}

/**
 * Remove WhatsApp da lista
 */
function removeWhatsappFromList(button) {
    const whatsappItem = button.closest('.whatsapp-item');
    if (whatsappItem) {
        whatsappItem.remove();
        updateWhatsappCount();
        
        // Adicionar empty state se necessário
        if (elements.whatsappList.children.length === 0) {
            elements.whatsappList.innerHTML = `
                <div class="empty-list">
                    <i class="mdi mdi-phone-off"></i>
                    <p>Nenhum número cadastrado</p>
                </div>
            `;
        }
        
        showNotification('Número removido da lista', NOTIFICATION_TYPES.SUCCESS);
    }
}

/**
 * Alterna status principal do WhatsApp
 */
function toggleWhatsappPrincipal(button) {
    const whatsappItem = button.closest('.whatsapp-item');
    const allItems = elements.whatsappList.querySelectorAll('.whatsapp-item');
    
    // Remover principal de todos
    allItems.forEach(item => {
        const btn = item.querySelector('.btn-principal');
        const badge = item.querySelector('.principal-badge');
        
        btn.classList.remove('active');
        btn.title = 'Definir como principal';
        if (badge) badge.remove();
    });
    
    // Definir este como principal
    button.classList.add('active');
    button.title = 'Principal';
    
    const whatsappInfo = whatsappItem.querySelector('.whatsapp-details');
    const principalBadge = document.createElement('span');
    principalBadge.className = 'principal-badge';
    principalBadge.innerHTML = '<i class="mdi mdi-star"></i> Principal';
    whatsappInfo.appendChild(principalBadge);
    
    showNotification('Número definido como principal', NOTIFICATION_TYPES.SUCCESS);
}

/**
 * Popula lista de WhatsApp com dados carregados
 */
function populateWhatsappList(whatsappList) {
    clearWhatsappList();
    
    if (!whatsappList || whatsappList.length === 0) {
        return;
    }
    
    whatsappList.forEach(whatsapp => {
        addWhatsappToList(whatsapp);
    });
}

/**
 * Limpa lista de WhatsApp
 */
function clearWhatsappList() {
    elements.whatsappList.innerHTML = `
        <div class="empty-list">
            <i class="mdi mdi-phone-off"></i>
            <p>Nenhum número cadastrado</p>
        </div>
    `;
    updateWhatsappCount();
}

/**
 * Atualiza contador de WhatsApp
 */
function updateWhatsappCount() {
    const count = elements.whatsappList.querySelectorAll('.whatsapp-item').length;
    elements.whatsappCount.textContent = count;
}

/**
 * Obtém lista atual de WhatsApp
 */
function getCurrentWhatsapp() {
    const whatsappItems = elements.whatsappList.querySelectorAll('.whatsapp-item');
    return Array.from(whatsappItems).map(item => {
        const isPrincipal = item.querySelector('.btn-principal').classList.contains('active');
        const tipo = item.querySelector('.tipo-badge').textContent;
        
        return {
            id: item.dataset.whatsappId !== 'new' ? item.dataset.whatsappId : null,
            numero_whatsapp: item.dataset.whatsappNumero,
            nome_contato: item.querySelector('.whatsapp-name').textContent,
            tipo_numero: tipo,
            principal: isPrincipal
        };
    });
}

// =================================
// CRUD DE USUÁRIOS
// =================================

/**
 * Manipula submissão do formulário
 */
async function handleFormSubmit(e) {
    e.preventDefault();
    
    if (appState.isLoading) {
        console.log('[USUARIOS] Já está processando, ignorando envio');
        return;
    }
    
    console.log('[USUARIOS] Iniciando salvamento...');
    
    // Validar formulário
    if (!validateForm()) {
        return;
    }
    
    appState.isLoading = true;
    showSaveLoading();
    
    try {
        let result;
        if (appState.currentMode === MODAL_MODES.CREATE) {
            result = await createUser();
        } else {
            result = await updateUser();
        }
        
        // Sucesso - fechar modal e atualizar
        console.log('[USUARIOS] Salvamento bem-sucedido');
        closeModal();
        showNotification('Usuário salvo com sucesso!', NOTIFICATION_TYPES.SUCCESS);
        
        // Aguardar um pouco antes de recarregar para mostrar a notificação
        setTimeout(() => {
            refreshUsersList();
        }, 1000);
        
    } catch (error) {
        console.error('[USUARIOS] Erro ao salvar:', error);
        showNotification(error.message || 'Erro ao salvar usuário', NOTIFICATION_TYPES.ERROR);
    } finally {
        appState.isLoading = false;
        hideSaveLoading();
    }
}

/**
 * Cria novo usuário
 */
async function createUser() {
    console.log('[USUARIOS] Criando novo usuário...');
    
    // 1. Criar usuário
    const userData = collectUserFormData();
    const userResponse = await apiRequest('/salvar', 'POST', userData);
    
    if (!userResponse.success) {
        throw new Error(userResponse.error || 'Erro ao criar usuário');
    }
    
    const userId = userResponse.user_id || userResponse.id;
    if (!userId) {
        throw new Error('ID do usuário não retornado');
    }
    
    // 2. Associar empresas se aplicável
    const role = elements.userRole.value;
    if (role === 'interno_unique' || role === 'cliente_unique') {
        await saveUserEmpresas(userId);
    }
    
    // 3. Salvar WhatsApp
    await saveUserWhatsapp(userId);
    
    console.log('[USUARIOS] Usuário criado com sucesso');
}

/**
 * Atualiza usuário existente
 */
async function updateUser() {
    console.log(`[USUARIOS] Atualizando usuário: ${appState.currentUser.id}`);
    
    const userId = appState.currentUser.id;
    
    // 1. Atualizar dados básicos
    const userData = collectUserFormData();
    userData.user_id = userId; // Adicionar ID para edição
    delete userData.password; // Não enviar senha na atualização
    delete userData.confirm_password;
    
    const userResponse = await apiRequest('/salvar', 'POST', userData);
    
    if (!userResponse.success) {
        throw new Error(userResponse.error || 'Erro ao atualizar usuário');
    }
    
    // 2. Atualizar empresas se aplicável
    const role = elements.userRole.value;
    if (role === 'interno_unique' || role === 'cliente_unique') {
        await saveUserEmpresas(userId);
    }
    
    // 3. Atualizar WhatsApp
    await saveUserWhatsapp(userId);
    
    console.log('[USUARIOS] Usuário atualizado com sucesso');
}

/**
 * Coleta dados do formulário de usuário
 */
function collectUserFormData() {
    const formData = new FormData(elements.modalForm);
    
    return {
        name: formData.get('name'),
        email: formData.get('email'),
        role: formData.get('role'),
        is_active: formData.get('is_active') ? 'true' : 'false',
        password: formData.get('password'),
        confirm_password: formData.get('confirm_password')
    };
}

/**
 * Salva empresas do usuário
 */
async function saveUserEmpresas(userId) {
    console.log(`[USUARIOS] Salvando empresas do usuário: ${userId}`);
    
    const currentEmpresas = getCurrentEmpresas();
    const empresaIds = currentEmpresas.map(emp => emp.id).filter(id => !isNaN(id)); // Filtrar IDs válidos
    
    console.log(`[USUARIOS] IDs de empresas para salvar:`, empresaIds);
    
    if (empresaIds.length === 0) {
        console.log('[USUARIOS] Nenhuma empresa válida para salvar');
        return; // Não há empresas para salvar, mas não é erro
    }
    
    const response = await apiRequest(`/${userId}/empresas`, 'POST', {
        empresas: empresaIds
    });
    
    if (!response.success) {
        throw new Error(response.error || 'Erro ao salvar empresas');
    }
    
    console.log('[USUARIOS] Empresas salvas com sucesso');
}

/**
 * Salva números WhatsApp do usuário
 */
async function saveUserWhatsapp(userId) {
    console.log(`[USUARIOS] Salvando WhatsApp do usuário: ${userId}`);
    
    const currentWhatsapp = getCurrentWhatsapp();
    const originalWhatsapp = appState.originalWhatsapp || [];
    
    // Determinar ações necessárias
    const toCreate = currentWhatsapp.filter(curr => !curr.id);
    const toUpdate = currentWhatsapp.filter(curr => curr.id);
    const toDelete = originalWhatsapp.filter(orig => 
        !currentWhatsapp.some(curr => curr.id === orig.id)
    );
    
    // Criar novos números
    for (const whatsapp of toCreate) {
        await apiRequest(`/${userId}/whatsapp`, 'POST', whatsapp);
    }
    
    // Deletar números removidos
    for (const whatsapp of toDelete) {
        if (whatsapp.id) {
            await apiRequest(`/whatsapp/${whatsapp.id}`, 'DELETE');
        }
    }
    
    // Atualizar número principal se necessário
    const principalNumber = currentWhatsapp.find(w => w.principal);
    if (principalNumber && principalNumber.id) {
        await apiRequest(`/whatsapp/${principalNumber.id}/principal`, 'POST');
    }
    
    console.log('[USUARIOS] WhatsApp salvo com sucesso');
}

/**
 * Deleta usuário
 */
async function deleteUser(userId, userName) {
    console.log(`[USUARIOS] Deletando usuário: ${userId}`);
    
    if (!confirm(`Tem certeza que deseja excluir o usuário "${userName}"?\n\nEsta ação não pode ser desfeita.`)) {
        return;
    }
    
    try {
        const response = await apiRequest(`/deletar/${userId}`, 'POST');
        
        if (response.success) {
            // Remover linha da tabela
            const userRow = document.querySelector(`tr[data-user-id="${userId}"]`);
            if (userRow) {
                userRow.remove();
            }
            
            showNotification(response.message || 'Usuário excluído com sucesso!', NOTIFICATION_TYPES.SUCCESS);
        } else {
            throw new Error(response.error || 'Erro ao excluir usuário');
        }
        
    } catch (error) {
        console.error('[USUARIOS] Erro ao deletar:', error);
        showNotification(error.message || 'Erro ao excluir usuário', NOTIFICATION_TYPES.ERROR);
    }
}

// =================================
// MANIPULAÇÃO DA TABELA
// =================================

/**
 * Manipula cliques nos botões da tabela
 */
function handleTableButtonClick(e) {
    const button = e.target.closest('button');
    if (!button) return;
    
    const userId = button.dataset.userId;
    const userName = button.dataset.userName;
    
    if (button.classList.contains('btn-edit')) {
        openModalForEdit(userId);
    } else if (button.classList.contains('btn-delete')) {
        showDeleteConfirmation(userId, userName);
    }
}

/**
 * Filtra tabela de usuários
 */
function filterUsersTable(query) {
    const rows = elements.usersTable?.querySelectorAll('tr.user-row');
    if (!rows) return;
    
    const searchTerm = query.toLowerCase().trim();
    let visibleCount = 0;
    
    rows.forEach(row => {
        if (!searchTerm) {
            row.style.display = '';
            visibleCount++;
            return;
        }
        
        const name = row.querySelector('.user-name')?.textContent.toLowerCase() || '';
        const email = row.querySelector('.email-text')?.textContent.toLowerCase() || '';
        const role = row.querySelector('.role-badge')?.textContent.toLowerCase() || '';
        
        const matches = name.includes(searchTerm) || 
                       email.includes(searchTerm) || 
                       role.includes(searchTerm);
        
        row.style.display = matches ? '' : 'none';
        if (matches) visibleCount++;
    });
    
    // Mostrar mensagem se nenhum resultado
    updateEmptyState(visibleCount === 0 && searchTerm);
}

/**
 * Atualiza estado vazio da tabela
 */
function updateEmptyState(showEmpty) {
    const existingEmpty = elements.usersTable?.querySelector('.search-empty-row');
    
    if (showEmpty) {
        if (!existingEmpty) {
            const emptyRow = document.createElement('tr');
            emptyRow.className = 'search-empty-row';
            emptyRow.innerHTML = `
                <td colspan="5" class="empty-message">
                    <div class="empty-state">
                        <i class="mdi mdi-magnify-close"></i>
                        <p>Nenhum usuário encontrado para esta busca</p>
                    </div>
                </td>
            `;
            elements.usersTable.appendChild(emptyRow);
        }
    } else {
        if (existingEmpty) {
            existingEmpty.remove();
        }
    }
}

/**
 * Atualiza lista de usuários
 */
function refreshUsersList() {
    console.log('[USUARIOS] Atualizando lista de usuários...');
    window.location.reload();
}

// =================================
// MODAL DE CONFIRMAÇÃO
// =================================

/**
 * Mostra modal de confirmação de exclusão
 */
function showDeleteConfirmation(userId, userName) {
    elements.deleteUserName.textContent = userName;
    elements.deleteModal.classList.remove('hidden');
    
    // Configurar botão de confirmação
    elements.btnConfirmDelete.onclick = () => {
        hideDeleteModal();
        deleteUser(userId, userName);
    };
}

/**
 * Oculta modal de confirmação
 */
function hideDeleteModal() {
    elements.deleteModal?.classList.add('hidden');
}

/**
 * Manipula confirmação de exclusão
 */
function handleConfirmDelete() {
    // A lógica está no onclick configurado em showDeleteConfirmation
}

// =================================
// VALIDAÇÃO
// =================================

/**
 * Valida formulário antes do envio
 */
function validateForm() {
    const errors = [];
    
    // Validações básicas
    if (!elements.userName.value.trim()) {
        errors.push('Nome é obrigatório');
    }
    
    if (!elements.userEmail.value.trim()) {
        errors.push('Email é obrigatório');
    } else if (!isValidEmail(elements.userEmail.value)) {
        errors.push('Email inválido');
    }
    
    if (!elements.userRole.value) {
        errors.push('Perfil é obrigatório');
    }
    
    // Validações de senha (apenas para criação)
    if (appState.currentMode === MODAL_MODES.CREATE) {
        if (!elements.userPassword.value) {
            errors.push('Senha é obrigatória');
        } else if (elements.userPassword.value.length < 6) {
            errors.push('Senha deve ter pelo menos 6 caracteres');
        }
        
        if (elements.userPassword.value !== elements.userConfirmPassword.value) {
            errors.push('Senhas não coincidem');
        }
    }
    
    // Validar WhatsApp se houver números
    const whatsappItems = elements.whatsappList.querySelectorAll('.whatsapp-item');
    whatsappItems.forEach((item, index) => {
        const numero = item.dataset.whatsappNumero;
        if (numero && !isValidWhatsApp(numero)) {
            errors.push(`Número WhatsApp ${index + 1} inválido`);
        }
    });
    
    if (errors.length > 0) {
        showNotification(errors.join('\n'), NOTIFICATION_TYPES.ERROR);
        return false;
    }
    
    return true;
}

/**
 * Valida formato de email
 */
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

/**
 * Valida formato de WhatsApp
 */
function isValidWhatsApp(numero) {
    const phoneRegex = /^\+[1-9]\d{1,14}$/;
    return phoneRegex.test(numero);
}

// =================================
// UTILIDADES
// =================================

/**
 * Limpa todos os campos do formulário
 */
function clearForm() {
    elements.modalForm?.reset();
    
    // Limpar dados extras
    delete elements.empresaSearch?.dataset.selectedId;
    delete elements.empresaSearch?.dataset.selectedCnpj;
    delete elements.empresaSearch?.dataset.selectedNome;
    
    // Resetar estados
    elements.userActive.checked = true;
    elements.btnAddEmpresa.disabled = true;
    
    // Limpar listas
    clearEmpresasList();
    clearWhatsappList();
    
    // Ocultar resultados de busca
    hideEmpresaSearchResults();
}

/**
 * Mostra loading no botão salvar
 */
function showSaveLoading() {
    elements.btnSave.disabled = true;
    elements.saveText.innerHTML = '<i class="mdi mdi-loading mdi-spin"></i> Salvando...';
}

/**
 * Oculta loading no botão salvar
 */
function hideSaveLoading() {
    elements.btnSave.disabled = false;
    const text = appState.currentMode === MODAL_MODES.CREATE ? 'Criar Usuário' : 'Salvar Alterações';
    elements.saveText.textContent = text;
}

/**
 * Mostra notificação
 */
function showNotification(message, type = NOTIFICATION_TYPES.INFO) {
    if (!elements.notificationArea) return;
    
    // Remover classes de tipo existentes
    elements.notificationArea.className = 'notification-area';
    
    // Adicionar classe do tipo
    elements.notificationArea.classList.add(type);
    
    // Definir ícone baseado no tipo
    let icon = 'mdi-information';
    switch (type) {
        case NOTIFICATION_TYPES.SUCCESS:
            icon = 'mdi-check-circle';
            break;
        case NOTIFICATION_TYPES.ERROR:
            icon = 'mdi-alert-circle';
            break;
        case NOTIFICATION_TYPES.WARNING:
            icon = 'mdi-alert';
            break;
    }
    
    // Definir conteúdo
    elements.notificationArea.innerHTML = `
        <i class="mdi ${icon}"></i>
        <span>${message}</span>
    `;
    
    // Mostrar notificação
    elements.notificationArea.classList.remove('hidden');
    
    // Auto-ocultar após 5 segundos (exceto erros)
    if (type !== NOTIFICATION_TYPES.ERROR) {
        setTimeout(() => {
            elements.notificationArea?.classList.add('hidden');
        }, 5000);
    }
}

/**
 * Requisição à API com retry e tratamento de erros
 */
async function apiRequest(endpoint, method = 'GET', data = null) {
    const url = `${CONFIG.API_BASE_URL}${endpoint}`;
    
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json',
            'X-API-Key': CONFIG.API_BYPASS_KEY
        }
    };
    
    if (data && method !== 'GET') {
        if (data instanceof FormData) {
            options.body = data;
            delete options.headers['Content-Type']; // Let browser set it for FormData
        } else {
            options.body = JSON.stringify(data);
        }
    }
    
    for (let attempt = 1; attempt <= CONFIG.MAX_RETRIES; attempt++) {
        try {
            console.log(`[API] ${method} ${url} (tentativa ${attempt})`);
            
            const response = await fetch(url, options);
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ error: 'Erro de comunicação' }));
                throw new Error(errorData.error || `Erro HTTP ${response.status}`);
            }
            
            const result = await response.json();
            console.log(`[API] Resposta recebida:`, result);
            
            return result;
            
        } catch (error) {
            console.error(`[API] Erro na tentativa ${attempt}:`, error);
            
            if (attempt === CONFIG.MAX_RETRIES) {
                throw error;
            }
            
            // Aguardar antes da próxima tentativa
            await new Promise(resolve => setTimeout(resolve, CONFIG.RETRY_DELAY));
        }
    }
}

// =================================
// FUNÇÕES GLOBAIS (para onclick)
// =================================

// Estas funções precisam estar no escopo global para funcionar com onclick
window.removeEmpresaFromList = removeEmpresaFromList;
window.removeWhatsappFromList = removeWhatsappFromList;
window.toggleWhatsappPrincipal = toggleWhatsappPrincipal;

// =================================
// DEBUG E LOGGING
// =================================

if (window.location.hostname === 'localhost' || window.location.hostname.includes('dev')) {
    console.log('[USUARIOS] Modo debug ativado');
    
    // Adicionar funções de debug ao window para acesso via console
    window.usuariosDebug = {
        appState,
        elements,
        CONFIG,
        getCurrentEmpresas,
        getCurrentWhatsapp,
        apiRequest
    };
}
