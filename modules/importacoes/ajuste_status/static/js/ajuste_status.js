// Ajuste de Status - JavaScript modular inspirado na página de relatórios

// Ajuste de Status - CRUD Management

// Estado global
let currentMappings = [];
let currentEditingStatus = null;

// Inicialização
document.addEventListener('DOMContentLoaded', () => {
    console.log('Inicializando módulo de Ajuste de Status (CRUD)...');
    initAjusteStatus();
});

function initAjusteStatus() {
    setupEventListeners();
    loadMappings();
}

// ==================== Event Listeners ====================

function setupEventListeners() {
    // Botão adicionar
    document.getElementById('btn-adicionar')?.addEventListener('click', openAddModal);
    
    // Botão salvar no modal
    document.getElementById('btn-salvar-mapping')?.addEventListener('click', saveMappingModal);
    
    // Botão confirmar delete
    document.getElementById('btn-confirmar-delete')?.addEventListener('click', confirmDelete);
    
    // Reset do formulário ao fechar modal
    const mappingModal = document.getElementById('mappingModal');
    mappingModal?.addEventListener('hidden.bs.modal', resetMappingForm);
    
    // Auto-preencher ordem quando status timeline é selecionado
    const statusTimelineSelect = document.getElementById('status-timeline');
    statusTimelineSelect?.addEventListener('change', function() {
        const timelineOrderInput = document.getElementById('timeline-order');
        const orderMap = {
            'PROCESSOS ABERTOS': 1,
            'AG. EMBARQUE': 2,
            'AG. CHEGADA': 3,
            'AG. REGISTRO': 4,
            'AG. DESEMBARAÇO': 5,
            'AG. FECHAMENTO': 6
        };
        
        if (this.value && orderMap[this.value]) {
            timelineOrderInput.value = orderMap[this.value];
            timelineOrderInput.readOnly = true; // Travar o campo
        } else {
            timelineOrderInput.readOnly = false;
        }
    });
}

// ==================== API Calls ====================

async function loadMappings() {
    try {
        showLoadingState();
        
        const response = await fetch('/ajuste-status/api/mappings');
        const result = await response.json();
        
        if (result.success) {
            currentMappings = result.data || [];
            renderMappingsTable(currentMappings);
            updateMappingsCount(currentMappings.length);
        } else {
            showError('Erro ao carregar mapeamentos: ' + result.error);
            renderEmptyState();
        }
    } catch (error) {
        console.error('Erro ao carregar mapeamentos:', error);
        showError('Erro ao carregar mapeamentos');
        renderEmptyState();
    }
}

async function createMapping(data) {
    try {
        const response = await fetch('/ajuste-status/api/mappings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showSuccess('Mapeamento criado com sucesso!');
            await loadMappings();
            bootstrap.Modal.getInstance(document.getElementById('mappingModal'))?.hide();
        } else {
            showError(result.error || 'Erro ao criar mapeamento');
        }
    } catch (error) {
        console.error('Erro ao criar mapeamento:', error);
        showError('Erro ao criar mapeamento');
    }
}

async function updateMapping(statusSistema, data) {
    try {
        const response = await fetch(`/ajuste-status/api/mappings/${encodeURIComponent(statusSistema)}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showSuccess('Mapeamento atualizado com sucesso!');
            await loadMappings();
            bootstrap.Modal.getInstance(document.getElementById('mappingModal'))?.hide();
        } else {
            showError(result.error || 'Erro ao atualizar mapeamento');
        }
    } catch (error) {
        console.error('Erro ao atualizar mapeamento:', error);
        showError('Erro ao atualizar mapeamento');
    }
}

async function deleteMapping(statusSistema) {
    try {
        const response = await fetch(`/ajuste-status/api/mappings/${encodeURIComponent(statusSistema)}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.success) {
            showSuccess('Mapeamento excluído com sucesso!');
            await loadMappings();
            await loadUnmappedStatuses();
            bootstrap.Modal.getInstance(document.getElementById('deleteModal'))?.hide();
        } else {
            showError(result.error || 'Erro ao excluir mapeamento');
        }
    } catch (error) {
        console.error('Erro ao excluir mapeamento:', error);
        showError('Erro ao excluir mapeamento');
    }
}

// ==================== UI Rendering ====================

function renderMappingsTable(mappings) {
    const tbody = document.getElementById('mappings-tbody');
    
    if (!mappings || mappings.length === 0) {
        renderEmptyState();
        return;
    }
    
    tbody.innerHTML = mappings.map(mapping => `
        <tr>
            <td>
                <span class="status-sistema-badge">${escapeHtml(mapping.status_sistema)}</span>
            </td>
            <td>
                <span class="status-timeline-badge ${getTimelineClass(mapping.status_timeline)}">
                    <i class="mdi mdi-timeline"></i>
                    ${escapeHtml(mapping.status_timeline)}
                </span>
            </td>
            <td>
                <span class="timeline-order-badge">${mapping.timeline_order}</span>
            </td>
            <td class="text-center">
                <div class="action-buttons">
                    <button class="btn btn-edit btn-sm" onclick="openEditModal('${escapeHtml(mapping.status_sistema)}')">
                        <i class="mdi mdi-pencil"></i> Editar
                    </button>
                    <button class="btn btn-delete btn-sm" onclick="openDeleteModal('${escapeHtml(mapping.status_sistema)}')">
                        <i class="mdi mdi-delete"></i> Excluir
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
}

function renderEmptyState() {
    const tbody = document.getElementById('mappings-tbody');
    tbody.innerHTML = `
        <tr>
            <td colspan="4">
                <div class="empty-state">
                    <div class="empty-state-icon">
                        <i class="mdi mdi-format-list-checks"></i>
                    </div>
                    <h4>Nenhum mapeamento cadastrado</h4>
                    <p class="text-muted">
                        Comece adicionando o primeiro mapeamento de status clicando no botão "Adicionar Mapeamento" acima.
                    </p>
                    <button class="btn btn-primary" onclick="openAddModal()">
                        <i class="mdi mdi-plus-circle me-1"></i>Adicionar Primeiro Mapeamento
                    </button>
                </div>
            </td>
        </tr>
    `;
}

function showLoadingState() {
    const tbody = document.getElementById('mappings-tbody');
    tbody.innerHTML = `
        <tr class="loading-row">
            <td colspan="4" class="text-center py-4">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Carregando...</span>
                </div>
                <p class="mt-2 mb-0 text-muted">Carregando mapeamentos...</p>
            </td>
        </tr>
    `;
}

function updateMappingsCount(count) {
    const countElement = document.getElementById('total-mappings');
    if (countElement) {
        countElement.textContent = `${count} mapeamento${count !== 1 ? 's' : ''}`;
    }
}

// ==================== Modal Management ====================

function openAddModal() {
    resetMappingForm();
    
    document.getElementById('mapping-mode').value = 'create';
    document.getElementById('modal-title-text').textContent = 'Adicionar Mapeamento';
    
    // Habilitar input de texto para digitação manual
    const inputElement = document.getElementById('status-sistema-input');
    inputElement.disabled = false;
    inputElement.placeholder = 'Digite o status do sistema (ex: AG. EMBARQUE)';
    inputElement.focus();
    
    const modal = new bootstrap.Modal(document.getElementById('mappingModal'));
    modal.show();
}

function openEditModal(statusSistema) {
    resetMappingForm();
    
    const mapping = currentMappings.find(m => m.status_sistema === statusSistema);
    if (!mapping) {
        showError('Mapeamento não encontrado');
        return;
    }
    
    currentEditingStatus = statusSistema;
    
    document.getElementById('mapping-mode').value = 'edit';
    document.getElementById('original-status-sistema').value = statusSistema;
    document.getElementById('modal-title-text').textContent = 'Editar Mapeamento';
    
    // Desabilitar input de status (não pode editar PK)
    const inputElement = document.getElementById('status-sistema-input');
    inputElement.value = mapping.status_sistema;
    inputElement.disabled = true;
    
    // Preencher outros campos
    document.getElementById('status-timeline').value = mapping.status_timeline;
    document.getElementById('timeline-order').value = mapping.timeline_order;
    
    const modal = new bootstrap.Modal(document.getElementById('mappingModal'));
    modal.show();
}

function openDeleteModal(statusSistema) {
    currentEditingStatus = statusSistema;
    document.getElementById('delete-status-name').textContent = statusSistema;
    
    const modal = new bootstrap.Modal(document.getElementById('deleteModal'));
    modal.show();
}

function saveMappingModal() {
    const mode = document.getElementById('mapping-mode').value;
    const form = document.getElementById('mapping-form');
    
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }
    
    const selectElement = document.getElementById('status-sistema-select');
    const inputElement = document.getElementById('status-sistema-input');
    
    let statusSistema;
    if (mode === 'create') {
        statusSistema = selectElement.style.display === 'none' 
            ? inputElement.value.trim().toUpperCase()
            : selectElement.value;
    } else {
        statusSistema = document.getElementById('original-status-sistema').value;
    }
    
    const data = {
        status_sistema: statusSistema,
        status_timeline: document.getElementById('status-timeline').value,
        timeline_order: parseInt(document.getElementById('timeline-order').value)
    };
    
    if (mode === 'create') {
        createMapping(data);
    } else {
        updateMapping(statusSistema, data);
    }
}

function confirmDelete() {
    if (currentEditingStatus) {
        deleteMapping(currentEditingStatus);
    }
}

function resetMappingForm() {
    document.getElementById('mapping-form').reset();
    document.getElementById('status-sistema-input').disabled = false;
    currentEditingStatus = null;
}

// ==================== Utility Functions ====================

function getTimelineClass(statusTimeline) {
    const classMap = {
        'PROCESSOS ABERTOS': 'processos-abertos',
        'AG. EMBARQUE': 'ag-embarque',
        'AG. CHEGADA': 'ag-chegada',
        'AG. REGISTRO': 'ag-registro',
        'AG. DESEMBARAÇO': 'ag-desembaraco',
        'AG. FECHAMENTO': 'ag-fechamento'
    };
    return classMap[statusTimeline] || '';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showSuccess(message) {
    showToast(message, 'success');
}

function showError(message) {
    showToast(message, 'error');
}

function showToast(message, type = 'info') {
    const toastContainer = getOrCreateToastContainer();
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    const iconMap = {
        success: 'mdi-check-circle',
        error: 'mdi-alert-circle',
        warning: 'mdi-alert',
        info: 'mdi-information'
    };
    
    toast.innerHTML = `
        <div class="toast-header">
            <i class="mdi ${iconMap[type]} me-2"></i>
            <strong class="me-auto">${type === 'success' ? 'Sucesso' : type === 'error' ? 'Erro' : 'Aviso'}</strong>
            <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
        </div>
        <div class="toast-body">${message}</div>
    `;
    
    toastContainer.appendChild(toast);
    const bsToast = new bootstrap.Toast(toast, { delay: 4000 });
    bsToast.show();
    
    toast.addEventListener('hidden.bs.toast', () => toast.remove());
}

function getOrCreateToastContainer() {
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }
    return container;
}

// Expor funções globalmente para uso nos event handlers inline
window.openAddModal = openAddModal;
window.openEditModal = openEditModal;
window.openDeleteModal = openDeleteModal;
