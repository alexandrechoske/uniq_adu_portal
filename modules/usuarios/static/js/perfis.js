/**
 * MÓDULO DE GERENCIAMENTO DE PERFIS - REDESIGN 2025
 * Sistema moderno de controle de acesso por perfis
 * 
 * Funcionalidades:
 * - CRUD de perfis de acesso
 * - Configuração de módulos e páginas
 * - KPIs em tempo real
 * - Interface responsiva
 * - Validações avançadas
 */

// =================================
// CONFIGURAÇÕES E CONSTANTES
// =================================

const CONFIG = {
    API_BASE_URL: '/usuarios/perfis',
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
    EDIT: 'edit',
    VIEW: 'view'
};

const MODULOS_SISTEMA = {
    imp: {
        nome: 'Importação',
        icon: 'mdi-ship',
        color: 'primary',
        pages: [
            { code: 'dashboard_executivo', name: 'Dashboard Executivo', icon: 'mdi-chart-pie' },
            { code: 'dashboard_resumido', name: 'Dashboard Importações', icon: 'mdi-chart-bar' },
            { code: 'documentos', name: 'Conferência Documental', icon: 'mdi-file-document' },
            { code: 'relatorio', name: 'Exportação de Relatórios', icon: 'mdi-file-chart' },
            { code: 'agente', name: 'Agente UniQ', icon: 'mdi-robot' }
        ]
    },
    fin: {
        nome: 'Financeiro',
        icon: 'mdi-currency-usd',
        color: 'success',
        pages: [
            { code: 'fin_dashboard_executivo', name: 'Dashboard Executivo', icon: 'mdi-chart-pie' },
            { code: 'fluxo_caixa', name: 'Fluxo de Caixa', icon: 'mdi-cash-flow' },
            { code: 'despesas', name: 'Despesas', icon: 'mdi-receipt' },
            { code: 'faturamento', name: 'Faturamento', icon: 'mdi-file-invoice-dollar' }
        ]
    }
    // Future modules (exp: Exportação, con: Consultoria) will be added when implemented
};

// =================================
// ESTADO GLOBAL DA APLICAÇÃO
// =================================

let appState = {
    perfis: [],
    filteredPerfis: [],
    currentPerfil: null,
    currentMode: null,
    searchTimeout: null,
    isLoading: false,
    activeFilters: {
        search: '',
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
    console.log('[PERFIS] Inicializando módulo de perfis...');
    
    // Check if Bootstrap is loaded
    if (typeof bootstrap === 'undefined') {
        console.error('[PERFIS] Bootstrap não está carregado! Os modais não funcionarão.');
        showNotification('Erro: Bootstrap não carregado. Recarregue a página.', NOTIFICATION_TYPES.ERROR);
        return;
    }
    
    initializeElements();
    initializeEventListeners();
    loadPerfisData();
    
    console.log('[PERFIS] Módulo inicializado com sucesso');
});

/**
 * Inicializa referências dos elementos DOM
 */
function initializeElements() {
    elements = {
        // Containers principais
        perfisGrid: document.getElementById('perfis-grid'),
        loadingContainer: document.getElementById('loading-perfis'),
        emptyState: document.getElementById('empty-state'),
        
        // Controles
        searchInput: document.getElementById('search-perfis'),
        filterStatus: document.getElementById('filter-status'),
        btnRefresh: document.getElementById('btn-refresh'),
        btnNovoPerfil: document.getElementById('btn-novo-perfil'),
        btnCreateFirst: document.getElementById('btn-create-first-perfil'),
        
        // KPIs
        kpiTotalPerfis: document.getElementById('kpi-total-perfis'),
        kpiPerfisAtivos: document.getElementById('kpi-perfis-ativos'),
        kpiUsuariosVinculados: document.getElementById('kpi-usuarios-vinculados'),
        kpiModulos: document.getElementById('kpi-modulos'),
        
        // Modal Principal
        modalPerfil: document.getElementById('modalPerfil'),
        modalTitle: document.getElementById('modal-title-text'),
        formPerfil: document.getElementById('form-perfil'),
        btnSavePerfil: document.getElementById('btn-save-perfil'),
        btnSaveText: document.getElementById('btn-save-text'),
        
        // Campos do formulário
        perfilId: document.getElementById('perfil-id'),
        perfilNome: document.getElementById('perfil-nome'),
        perfilDescricao: document.getElementById('perfil-descricao'),
        perfilAtivo: document.getElementById('perfil-ativo'),
        modulosContainer: document.getElementById('modulos-container'),
        
        // Modal de visualização
        modalViewPerfil: document.getElementById('modalViewPerfil'),
        perfilDetailsContent: document.getElementById('perfil-details-content'),
        btnEditFromView: document.getElementById('btn-edit-from-view'),
        
        // Modal de exclusão
        modalDeletePerfil: document.getElementById('modalDeletePerfil'),
        deletePerfilName: document.getElementById('delete-perfil-name'),
        deleteWarningUsers: document.getElementById('delete-warning-users'),
        btnConfirmDelete: document.getElementById('btn-confirm-delete')
    };
}

/**
 * Inicializa event listeners
 */
function initializeEventListeners() {
    // Botões principais
    elements.btnRefresh?.addEventListener('click', handleRefresh);
    elements.btnNovoPerfil?.addEventListener('click', () => openPerfilModal(MODAL_MODES.CREATE));
    elements.btnCreateFirst?.addEventListener('click', () => openPerfilModal(MODAL_MODES.CREATE));
    
    // Busca e filtros
    elements.searchInput?.addEventListener('input', handleSearch);
    elements.filterStatus?.addEventListener('change', handleFilter);
    
    // Modal principal
    elements.btnSavePerfil?.addEventListener('click', handleSavePerfil);
    elements.btnEditFromView?.addEventListener('click', handleEditFromView);
    
    // Modal de exclusão
    elements.btnConfirmDelete?.addEventListener('click', handleConfirmDelete);
    
    // Bootstrap modals - Bootstrap 5 syntax
    if (elements.modalPerfil) {
        elements.modalPerfil.addEventListener('hidden.bs.modal', handleModalHidden);
        elements.modalPerfil.addEventListener('show.bs.modal', function() {
            // Reset any previous errors when opening modal
            const errorElements = elements.modalPerfil.querySelectorAll('.is-invalid');
            errorElements.forEach(el => el.classList.remove('is-invalid'));
        });
    }
    
    // Event delegation for dynamic checkbox events
    if (elements.modulosContainer) {
        elements.modulosContainer.addEventListener('change', function(e) {
            if (e.target.classList.contains('modulo-checkbox')) {
                const moduloCodigo = e.target.dataset.modulo;
                toggleModuloPages(moduloCodigo, e.target.checked);
            }
        });
        
        // Handle clicks on pagina items
        elements.modulosContainer.addEventListener('click', function(e) {
            if (e.target.classList.contains('pagina-item') || e.target.closest('.pagina-item')) {
                const paginaItem = e.target.classList.contains('pagina-item') ? e.target : e.target.closest('.pagina-item');
                const checkbox = paginaItem.querySelector('input[type="checkbox"]');
                if (checkbox && !checkbox.disabled) {
                    checkbox.checked = !checkbox.checked;
                }
            }
        });
    }
}

// =================================
// CARREGAMENTO DE DADOS
// =================================

/**
 * Carrega dados dos perfis
 */
async function loadPerfisData() {
    try {
        showLoading(true);
        
        const response = await fetch(`${CONFIG.API_BASE_URL}/list`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error(`Erro ao carregar perfis: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            appState.perfis = data.perfis || [];
            updateKPIs();
            applyFilters();
            renderPerfis();
        } else {
            throw new Error(data.message || 'Erro ao carregar perfis');
        }
        
    } catch (error) {
        console.error('[PERFIS] Erro ao carregar dados:', error);
        showNotification('Erro ao carregar perfis: ' + error.message, NOTIFICATION_TYPES.ERROR);
        showEmptyState();
    } finally {
        showLoading(false);
    }
}

// =================================
// RENDERIZAÇÃO
// =================================

/**
 * Renderiza a grid de perfis
 */
function renderPerfis() {
    if (!elements.perfisGrid) return;
    
    if (appState.filteredPerfis.length === 0) {
        showEmptyState();
        return;
    }
    
    hideEmptyState();
    
    elements.perfisGrid.innerHTML = '';
    
    appState.filteredPerfis.forEach(perfil => {
        const card = createPerfilCard(perfil);
        elements.perfisGrid.appendChild(card);
    });
}

/**
 * Cria um card de perfil
 */
function createPerfilCard(perfil) {
    const card = document.createElement('div');
    card.className = 'perfil-card';
    card.dataset.perfilId = perfil.codigo;
    
    // Contar módulos ativos
    const modulosAtivos = perfil.modulos ? perfil.modulos.filter(m => m.ativo).length : 0;
    
    // Status badge
    const statusBadge = `<span class="status-badge ${perfil.ativo ? 'ativo' : 'inativo'}">
        ${perfil.ativo ? 'Ativo' : 'Inativo'}
    </span>`;
    
    // Módulos badges
    const modulosBadges = perfil.modulos ? perfil.modulos
        .filter(m => m.ativo)
        .map(m => `<span class="modulo-badge">
            <i class="${MODULOS_SISTEMA[m.codigo]?.icon || 'mdi-cube'}"></i>
            ${MODULOS_SISTEMA[m.codigo]?.nome || m.codigo}
        </span>`).join('') : '';
    
    card.innerHTML = `
        <div class="perfil-card-header">
            <div class="perfil-info">
                <h3 class="perfil-nome">${escapeHtml(perfil.nome)}</h3>
                <div class="perfil-codigo">${escapeHtml(perfil.codigo)}</div>
            </div>
            <div class="perfil-actions">
                <button class="btn btn-sm btn-outline-primary" onclick="viewPerfil(${perfil.id})" title="Visualizar">
                    <i class="mdi mdi-eye"></i>
                </button>
                <button class="btn btn-sm btn-outline-secondary" onclick="editPerfil(${perfil.id})" title="Editar">
                    <i class="mdi mdi-pencil"></i>
                </button>
                <button class="btn btn-sm btn-outline-danger" onclick="deletePerfil(${perfil.id})" title="Excluir">
                    <i class="mdi mdi-delete"></i>
                </button>
            </div>
        </div>
        
        ${perfil.descricao ? `<div class="perfil-description">${escapeHtml(perfil.descricao)}</div>` : ''}
        
        <div class="perfil-modulos">
            <div class="perfil-modulos-title">Módulos Disponíveis (${modulosAtivos})</div>
            <div class="modulos-list">
                ${modulosBadges || '<span class="text-muted">Nenhum módulo configurado</span>'}
            </div>
        </div>
        
        <div class="perfil-stats">
            <div class="perfil-usuarios-count">
                <i class="mdi mdi-account-group"></i>
                <span>${perfil.usuarios_count || 0} usuários</span>
            </div>
            <div class="perfil-status">
                ${statusBadge}
            </div>
        </div>
    `;
    
    return card;
}

// =================================
// MODAL DE PERFIL
// =================================

/**
 * Abre modal de perfil
 */
function openPerfilModal(mode, perfilId = null) {
    appState.currentMode = mode;
    
    if (mode === MODAL_MODES.CREATE) {
        elements.modalTitle.textContent = 'Novo Perfil';
        elements.btnSaveText.textContent = 'Criar Perfil';
        resetForm();
        
        // Enable name field for create mode
        elements.perfilNome.disabled = false;
        elements.perfilNome.style.backgroundColor = '';
        
        // Hide readonly warning
        const readonlyWarning = document.getElementById('readonly-warning');
        if (readonlyWarning) {
            readonlyWarning.style.display = 'none';
        }
        
    } else if (mode === MODAL_MODES.EDIT && perfilId) {
        const perfil = appState.perfis.find(p => p.id === perfilId);
        if (perfil) {
            elements.modalTitle.textContent = 'Editar Perfil';
            elements.btnSaveText.textContent = 'Salvar Alterações';
            populateForm(perfil);
            
            // Disable name field for edit mode to prevent breaking user relationships
            elements.perfilNome.disabled = true;
            elements.perfilNome.style.backgroundColor = '#f8f9fa';
            elements.perfilNome.style.cursor = 'not-allowed';
            
            // Show readonly warning
            const readonlyWarning = document.getElementById('readonly-warning');
            if (readonlyWarning) {
                readonlyWarning.style.display = 'block';
            }
        }
    }
    
    renderModulosForm();
    
    // Bootstrap 5 modal initialization
    const modal = new bootstrap.Modal(elements.modalPerfil, {
        backdrop: 'static',
        keyboard: false
    });
    modal.show();
}

/**
 * Reseta o formulário
 */
function resetForm() {
    elements.formPerfil.reset();
    elements.perfilId.value = '';
    elements.perfilAtivo.checked = true;
    appState.currentPerfil = null;
}

/**
 * Popula o formulário com dados do perfil
 */
function populateForm(perfil) {
    elements.perfilId.value = perfil.id || '';
    elements.perfilNome.value = perfil.nome || '';
    elements.perfilDescricao.value = perfil.descricao || '';
    elements.perfilAtivo.checked = perfil.ativo !== false;
    
    appState.currentPerfil = perfil;
}

/**
 * Renderiza formulário de módulos
 */
function renderModulosForm() {
    if (!elements.modulosContainer) return;
    
    elements.modulosContainer.innerHTML = '';
    
    Object.keys(MODULOS_SISTEMA).forEach(moduloCodigo => {
        const modulo = MODULOS_SISTEMA[moduloCodigo];
        const moduloSection = createModuloSection(moduloCodigo, modulo);
        elements.modulosContainer.appendChild(moduloSection);
    });
    
    // Se estamos editando, pré-selecionar os módulos e páginas
    if (appState.currentPerfil && appState.currentPerfil.modulos) {
        appState.currentPerfil.modulos.forEach(moduloPerfil => {
            const checkbox = document.getElementById(`modulo-${moduloPerfil.codigo}`);
            if (checkbox) {
                checkbox.checked = moduloPerfil.ativo;
                toggleModuloPages(moduloPerfil.codigo, moduloPerfil.ativo);
                
                // Marcar páginas selecionadas
                if (moduloPerfil.paginas) {
                    moduloPerfil.paginas.forEach(pagina => {
                        const pageCheckbox = document.getElementById(`page-${moduloPerfil.codigo}-${pagina}`);
                        if (pageCheckbox) {
                            pageCheckbox.checked = true;
                        }
                    });
                }
            }
        });
    }
}

/**
 * Cria seção de módulo no formulário
 */
function createModuloSection(moduloCodigo, modulo) {
    const section = document.createElement('div');
    section.className = 'modulo-section';
    section.id = `modulo-section-${moduloCodigo}`;
    
    // Header do módulo
    const header = document.createElement('div');
    header.className = 'modulo-header';
    
    const title = document.createElement('h6');
    title.className = 'modulo-title';
    title.innerHTML = `
        <i class="${modulo.icon}"></i>
        ${modulo.nome}
    `;
    
    const toggle = document.createElement('div');
    toggle.className = 'modulo-toggle';
    toggle.innerHTML = `
        <label for="modulo-${moduloCodigo}">Habilitar módulo</label>
        <input type="checkbox" id="modulo-${moduloCodigo}" data-modulo="${moduloCodigo}" class="modulo-checkbox">
    `;
    
    header.appendChild(title);
    header.appendChild(toggle);
    
    // Grid de páginas
    const pagesGrid = document.createElement('div');
    pagesGrid.className = 'paginas-grid';
    pagesGrid.id = `pages-${moduloCodigo}`;
    
    if (modulo.pages && modulo.pages.length > 0) {
        modulo.pages.forEach(page => {
            const pageItem = document.createElement('div');
            pageItem.className = 'pagina-item';
            
            pageItem.innerHTML = `
                <input type="checkbox" id="page-${moduloCodigo}-${page.code}" value="${page.code}">
                <label for="page-${moduloCodigo}-${page.code}">${page.name}</label>
                <i class="${page.icon}"></i>
            `;
            
            pagesGrid.appendChild(pageItem);
        });
    } else {
        pagesGrid.innerHTML = '<div class="text-muted">Módulo em desenvolvimento</div>';
    }
    
    section.appendChild(header);
    section.appendChild(pagesGrid);
    
    return section;
}

/**
 * Toggle páginas do módulo
 */
function toggleModuloPages(moduloCodigo, enabled) {
    const section = document.getElementById(`modulo-section-${moduloCodigo}`);
    const pagesGrid = document.getElementById(`pages-${moduloCodigo}`);
    
    if (enabled) {
        section.classList.remove('disabled');
        pagesGrid.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
            checkbox.disabled = false;
        });
    } else {
        section.classList.add('disabled');
        pagesGrid.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
            checkbox.disabled = true;
            checkbox.checked = false;
        });
    }
}

// =================================
// AÇÕES DO PERFIL
// =================================

/**
 * Visualizar perfil
 */
function viewPerfil(perfilId) {
    const perfil = appState.perfis.find(p => p.id === perfilId);
    if (!perfil) return;
    
    renderPerfilDetails(perfil);
    
    // Bootstrap 5 modal initialization
    const modal = new bootstrap.Modal(elements.modalViewPerfil, {
        backdrop: true,
        keyboard: true
    });
    modal.show();
}

/**
 * Editar perfil
 */
function editPerfil(perfilId) {
    openPerfilModal(MODAL_MODES.EDIT, perfilId);
}

/**
 * Excluir perfil
 */
function deletePerfil(perfilId) {
    const perfil = appState.perfis.find(p => p.id === perfilId);
    if (!perfil) return;
    
    elements.deletePerfilName.textContent = perfil.nome;
    
    // Mostrar aviso se há usuários vinculados
    if (perfil.usuarios_count > 0) {
        elements.deleteWarningUsers.style.display = 'block';
    } else {
        elements.deleteWarningUsers.style.display = 'none';
    }
    
    // Armazenar ID do perfil para exclusão
    elements.btnConfirmDelete.dataset.perfilId = perfilId;
    
    // Bootstrap 5 modal initialization
    const modal = new bootstrap.Modal(elements.modalDeletePerfil, {
        backdrop: 'static',
        keyboard: false
    });
    modal.show();
}

/**
 * Salvar perfil
 */
async function handleSavePerfil(event) {
    // Prevenir comportamento padrão e propagação
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    
    try {
        const formData = collectFormData();
        
        if (!validateFormData(formData)) {
            return;
        }
        
        elements.btnSavePerfil.disabled = true;
        elements.btnSavePerfil.innerHTML = '<i class="mdi mdi-loading spin"></i> Salvando...';
        
        const url = appState.currentMode === MODAL_MODES.CREATE 
            ? `${CONFIG.API_BASE_URL}/create` 
            : `${CONFIG.API_BASE_URL}/update`;
        
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification(
                appState.currentMode === MODAL_MODES.CREATE 
                    ? 'Perfil criado com sucesso!' 
                    : 'Perfil atualizado com sucesso!', 
                NOTIFICATION_TYPES.SUCCESS
            );
            
            const modal = bootstrap.Modal.getInstance(elements.modalPerfil);
            if (modal) {
                modal.hide();
            }
            
            await loadPerfisData();
        } else {
            throw new Error(data.message || 'Erro ao salvar perfil');
        }
        
    } catch (error) {
        console.error('[PERFIS] Erro ao salvar:', error);
        showNotification('Erro ao salvar perfil: ' + error.message, NOTIFICATION_TYPES.ERROR);
    } finally {
        elements.btnSavePerfil.disabled = false;
        elements.btnSavePerfil.innerHTML = `<i class="mdi mdi-content-save"></i> ${elements.btnSaveText.textContent}`;
    }
}

/**
 * Confirmar exclusão
 */
async function handleConfirmDelete() {
    try {
        const perfilId = elements.btnConfirmDelete.dataset.perfilId;
        
        elements.btnConfirmDelete.disabled = true;
        elements.btnConfirmDelete.innerHTML = '<i class="mdi mdi-loading spin"></i> Excluindo...';
        
        const response = await fetch(`${CONFIG.API_BASE_URL}/delete`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ perfil_id: perfilId })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('Perfil excluído com sucesso!', NOTIFICATION_TYPES.SUCCESS);
            
            const modal = bootstrap.Modal.getInstance(elements.modalDeletePerfil);
            if (modal) {
                modal.hide();
            }
            
            await loadPerfisData();
        } else {
            throw new Error(data.message || 'Erro ao excluir perfil');
        }
        
    } catch (error) {
        console.error('[PERFIS] Erro ao excluir:', error);
        showNotification('Erro ao excluir perfil: ' + error.message, NOTIFICATION_TYPES.ERROR);
    } finally {
        elements.btnConfirmDelete.disabled = false;
        elements.btnConfirmDelete.innerHTML = '<i class="mdi mdi-delete"></i> Excluir Perfil';
    }
}

// =================================
// UTILITÁRIOS
// =================================

/**
 * Coleta dados do formulário
 */
function collectFormData() {
    const modulos = [];
    
    // Coletar dados dos módulos
    Object.keys(MODULOS_SISTEMA).forEach(moduloCodigo => {
        const moduloCheckbox = document.getElementById(`modulo-${moduloCodigo}`);
        
        if (moduloCheckbox && moduloCheckbox.checked) {
            const paginas = [];
            const pagesGrid = document.getElementById(`pages-${moduloCodigo}`);
            
            if (pagesGrid) {
                pagesGrid.querySelectorAll('input[type="checkbox"]:checked').forEach(pageCheckbox => {
                    paginas.push(pageCheckbox.value);
                });
            }
            
            modulos.push({
                codigo: moduloCodigo,
                nome: MODULOS_SISTEMA[moduloCodigo].nome,
                ativo: true,
                paginas: paginas
            });
        }
    });
    
    const formData = {
        id: elements.perfilId.value || null,  // ID do banco (null para novo perfil)
        descricao: elements.perfilDescricao.value.trim(),
        ativo: elements.perfilAtivo.checked,
        modulos: modulos
    };
    
    // RESTRIÇÃO: Só incluir nome para perfis novos (CREATE mode)
    // Em modo de edição, o nome é preservado para manter relacionamentos com usuários
    if (appState.currentMode === MODAL_MODES.CREATE) {
        formData.nome = elements.perfilNome.value.trim();
        console.log('[PERFIS] Modo CREATE - incluindo nome no formData:', formData.nome);
    } else {
        console.log('[PERFIS] Modo EDIT - nome excluído do formData para preservar relacionamentos');
    }
    
    return formData;
}

/**
 * Valida dados do formulário
 */
function validateFormData(data) {
    // Validar nome apenas em modo de criação (CREATE mode)
    // Em modo de edição, o nome não é enviado (preservação de relacionamentos)
    if (appState.currentMode === MODAL_MODES.CREATE && !data.nome) {
        showNotification('O nome do perfil é obrigatório', NOTIFICATION_TYPES.ERROR);
        elements.perfilNome.focus();
        return false;
    }
    
    // Validar que pelo menos um módulo está selecionado
    if (!data.modulos || data.modulos.length === 0) {
        showNotification('Selecione pelo menos um módulo para o perfil', NOTIFICATION_TYPES.WARNING);
        return false;
    }
    
    return true;
}

/**
 * Renderiza detalhes do perfil no modal de visualização
 */
function renderPerfilDetails(perfil) {
    if (!elements.perfilDetailsContent) return;
    
    const modulosHtml = perfil.modulos ? perfil.modulos
        .filter(m => m.ativo)
        .map(modulo => {
            const paginasHtml = modulo.paginas ? modulo.paginas
                .map(pagina => `<span class="pagina-detail-badge">
                    <i class="mdi mdi-file"></i>
                    ${pagina}
                </span>`).join('') : '';
            
            return `
                <div class="modulo-detail">
                    <div class="modulo-detail-header">
                        <i class="${MODULOS_SISTEMA[modulo.codigo]?.icon || 'mdi-cube'}"></i>
                        <h6 class="modulo-detail-title">${modulo.nome}</h6>
                    </div>
                    <div class="paginas-detail-list">
                        ${paginasHtml || '<span class="text-muted">Nenhuma página configurada</span>'}
                    </div>
                </div>
            `;
        }).join('') : '';
    
    elements.perfilDetailsContent.innerHTML = `
        <div class="perfil-details">
            <div class="detail-section">
                <h6 class="detail-section-title">
                    <i class="mdi mdi-information"></i>
                    Informações Gerais
                </h6>
                <div class="detail-item">
                    <span class="detail-label">Código:</span>
                    <span class="detail-value">${escapeHtml(perfil.codigo)}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Nome:</span>
                    <span class="detail-value">${escapeHtml(perfil.nome)}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Descrição:</span>
                    <span class="detail-value">${escapeHtml(perfil.descricao || 'Não informada')}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Status:</span>
                    <span class="detail-value">
                        <span class="status-badge ${perfil.ativo ? 'ativo' : 'inativo'}">
                            ${perfil.ativo ? 'Ativo' : 'Inativo'}
                        </span>
                    </span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Usuários Vinculados:</span>
                    <span class="detail-value">${perfil.usuarios_count || 0}</span>
                </div>
            </div>
            
            <div class="detail-section">
                <h6 class="detail-section-title">
                    <i class="mdi mdi-view-module"></i>
                    Módulos e Páginas
                </h6>
                <div class="modulos-detail-list">
                    ${modulosHtml || '<div class="text-muted">Nenhum módulo configurado</div>'}
                </div>
            </div>
        </div>
    `;
    
    // Configurar botão de edição
    elements.btnEditFromView.onclick = () => {
        const viewModal = bootstrap.Modal.getInstance(elements.modalViewPerfil);
        if (viewModal) {
            viewModal.hide();
            
            // Wait for modal to close before opening edit modal
            elements.modalViewPerfil.addEventListener('hidden.bs.modal', function openEditModal() {
                editPerfil(perfil.codigo);
                // Remove listener to avoid multiple calls
                elements.modalViewPerfil.removeEventListener('hidden.bs.modal', openEditModal);
            });
        } else {
            // Fallback if modal instance not found
            editPerfil(perfil.codigo);
        }
    };
}

/**
 * Atualiza KPIs
 */
function updateKPIs() {
    const totalPerfis = appState.perfis.length;
    const perfisAtivos = appState.perfis.filter(p => p.ativo).length;
    const usuariosVinculados = appState.perfis.reduce((total, p) => total + (p.usuarios_count || 0), 0);
    
    if (elements.kpiTotalPerfis) elements.kpiTotalPerfis.textContent = totalPerfis;
    if (elements.kpiPerfisAtivos) elements.kpiPerfisAtivos.textContent = perfisAtivos;
    if (elements.kpiUsuariosVinculados) elements.kpiUsuariosVinculados.textContent = usuariosVinculados;
}

/**
 * Aplica filtros
 */
function applyFilters() {
    let filtered = [...appState.perfis];
    
    // Filtro de busca
    if (appState.activeFilters.search) {
        const search = appState.activeFilters.search.toLowerCase();
        filtered = filtered.filter(perfil => 
            perfil.nome.toLowerCase().includes(search) ||
            perfil.codigo.toLowerCase().includes(search) ||
            (perfil.descricao && perfil.descricao.toLowerCase().includes(search))
        );
    }
    
    // Filtro de status
    if (appState.activeFilters.status) {
        const status = appState.activeFilters.status === 'ativo';
        filtered = filtered.filter(perfil => perfil.ativo === status);
    }
    
    appState.filteredPerfis = filtered;
}

/**
 * Handlers de eventos
 */
function handleRefresh() {
    loadPerfisData();
}

function handleSearch(event) {
    clearTimeout(appState.searchTimeout);
    
    appState.searchTimeout = setTimeout(() => {
        appState.activeFilters.search = event.target.value.trim();
        applyFilters();
        renderPerfis();
    }, CONFIG.DEBOUNCE_DELAY);
}

function handleFilter() {
    appState.activeFilters.status = elements.filterStatus.value;
    applyFilters();
    renderPerfis();
}

function handleModalHidden() {
    resetForm();
    appState.currentMode = null;
    appState.currentPerfil = null;
}

function handleEditFromView() {
    if (appState.currentPerfil) {
        editPerfil(appState.currentPerfil.codigo);
    }
}

/**
 * Estados de loading e empty
 */
function showLoading(show) {
    if (elements.loadingContainer) {
        elements.loadingContainer.style.display = show ? 'flex' : 'none';
    }
    if (elements.perfisGrid) {
        elements.perfisGrid.style.display = show ? 'none' : 'grid';
    }
}

function showEmptyState() {
    if (elements.emptyState) {
        elements.emptyState.style.display = 'flex';
    }
    if (elements.perfisGrid) {
        elements.perfisGrid.style.display = 'none';
    }
}

function hideEmptyState() {
    if (elements.emptyState) {
        elements.emptyState.style.display = 'none';
    }
    if (elements.perfisGrid) {
        elements.perfisGrid.style.display = 'grid';
    }
}

/**
 * Escape HTML para segurança
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Mostra notificação
 */
function showNotification(message, type = NOTIFICATION_TYPES.INFO) {
    // Create a simple toast notification
    const toastContainer = getOrCreateToastContainer();
    const toast = createToast(message, type);
    toastContainer.appendChild(toast);
    
    // Show the toast using Bootstrap
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    
    // Remove toast after it's hidden
    toast.addEventListener('hidden.bs.toast', () => {
        toast.remove();
    });
}

/**
 * Get or create toast container
 */
function getOrCreateToastContainer() {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container position-fixed top-0 end-0 p-3';
        container.style.zIndex = '9999';
        document.body.appendChild(container);
    }
    return container;
}

/**
 * Create toast element
 */
function createToast(message, type) {
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    const typeConfig = {
        [NOTIFICATION_TYPES.SUCCESS]: { 
            bgClass: 'bg-success', 
            icon: 'mdi-check-circle', 
            title: 'Sucesso' 
        },
        [NOTIFICATION_TYPES.ERROR]: { 
            bgClass: 'bg-danger', 
            icon: 'mdi-alert-circle', 
            title: 'Erro' 
        },
        [NOTIFICATION_TYPES.WARNING]: { 
            bgClass: 'bg-warning', 
            icon: 'mdi-alert-triangle', 
            title: 'Atenção' 
        },
        [NOTIFICATION_TYPES.INFO]: { 
            bgClass: 'bg-info', 
            icon: 'mdi-information', 
            title: 'Informação' 
        }
    };
    
    const config = typeConfig[type] || typeConfig[NOTIFICATION_TYPES.INFO];
    
    toast.innerHTML = `
        <div class="toast-header ${config.bgClass} text-white">
            <i class="mdi ${config.icon} me-2"></i>
            <strong class="me-auto">${config.title}</strong>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="toast-body">
            ${escapeHtml(message)}
        </div>
    `;
    
    return toast;
}

// =================================
// FUNÇÕES GLOBAIS PARA HTML
// =================================

window.viewPerfil = viewPerfil;
window.editPerfil = editPerfil;
window.deletePerfil = deletePerfil;
window.toggleModuloPages = toggleModuloPages;
