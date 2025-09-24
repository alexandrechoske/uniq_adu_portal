// Export Bases Financeiro - JavaScript

// Estado global do módulo
const ExportBasesState = {
    bases: [],
    currentBase: null,
    previewData: null,
    filters: {
        ano: '',
        limite: ''
    }
};

document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Export Bases Financeiro loaded');
    
    // Initialize
    initializeExportBases();
    
    // Set up event listeners
    setupEventListeners();
    
    // Load initial data
    loadInitialData();
});

function initializeExportBases() {
    console.log('📊 Initializing export bases...');
    
    // Initialize year filter with current year and previous years
    initializeYearFilter();
    
    // Setup loading states
    setupLoadingStates();
}

function initializeYearFilter() {
    const yearFilter = document.getElementById('ano-filter');
    if (yearFilter) {
        const currentYear = new Date().getFullYear();
        
        // Add years from current to 5 years back
        for (let year = currentYear; year >= currentYear - 5; year--) {
            const option = document.createElement('option');
            option.value = year;
            option.textContent = year;
            yearFilter.appendChild(option);
        }
    }
}

function setupEventListeners() {
    console.log('🔧 Setting up event listeners...');
    
    // Filter change handlers
    const yearFilter = document.getElementById('ano-filter');
    if (yearFilter) {
        yearFilter.addEventListener('change', handleFilterChange);
    }
    
    const limitFilter = document.getElementById('limite-filter');
    if (limitFilter) {
        limitFilter.addEventListener('change', handleFilterChange);
    }
    
    // Refresh button
    const refreshBtn = document.getElementById('refresh-bases');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', handleRefreshBases);
    }
    
    // Modal event listeners
    setupModalListeners();
}

function setupModalListeners() {
    // Export button in preview modal
    const btnExportarModal = document.getElementById('btn-exportar-modal');
    if (btnExportarModal) {
        btnExportarModal.addEventListener('click', handleExportFromModal);
    }
    
    // Confirm export button
    const btnConfirmarExportacao = document.getElementById('btn-confirmar-exportacao');
    if (btnConfirmarExportacao) {
        btnConfirmarExportacao.addEventListener('click', handleConfirmExport);
    }
}

// ==========================================
// EVENT HANDLERS
// ==========================================

function handleFilterChange() {
    // Update filter state
    ExportBasesState.filters.ano = document.getElementById('ano-filter').value;
    ExportBasesState.filters.limite = document.getElementById('limite-filter').value;
    
    console.log('Filters updated:', ExportBasesState.filters);
}

function handleRefreshBases() {
    loadBasesDisponiveis();
}

function handleBaseClick(baseId) {
    const base = ExportBasesState.bases.find(b => b.id === baseId);
    if (base) {
        ExportBasesState.currentBase = base;
        loadPreviewData(baseId);
    }
}

function handleDirectExport(baseId) {
    const base = ExportBasesState.bases.find(b => b.id === baseId);
    if (base) {
        ExportBasesState.currentBase = base;
        showConfirmExportModal();
    }
}

function handleExportFromModal() {
    if (ExportBasesState.currentBase) {
        // Close preview modal
        const previewModal = bootstrap.Modal.getInstance(document.getElementById('previewModal'));
        if (previewModal) {
            previewModal.hide();
        }
        
        // Show confirm modal
        setTimeout(() => {
            showConfirmExportModal();
        }, 300);
    }
}

function handleConfirmExport() {
    if (ExportBasesState.currentBase) {
        exportBase(ExportBasesState.currentBase.id);
        
        // Close confirm modal
        const confirmModal = bootstrap.Modal.getInstance(document.getElementById('confirmExportModal'));
        if (confirmModal) {
            confirmModal.hide();
        }
    }
}

// ==========================================
// DATA LOADING FUNCTIONS
// ==========================================

function loadInitialData() {
    loadBasesDisponiveis();
}

function loadBasesDisponiveis() {
    showLoading('Carregando bases disponíveis...');
    
    fetch('/financeiro/export-bases/api/bases-disponiveis')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                ExportBasesState.bases = data.data;
                renderBasesGrid(data.data);
            } else {
                showError('Erro ao carregar bases: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Erro ao carregar bases:', error);
            showError('Erro ao carregar bases disponíveis');
        })
        .finally(() => {
            hideLoading();
        });
}

function loadPreviewData(baseId) {
    showLoading('Carregando preview da base...');
    
    fetch(`/financeiro/export-bases/api/preview/${baseId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                ExportBasesState.previewData = data.data;
                showPreviewModal(data.data);
            } else {
                showError('Erro ao carregar preview: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Erro ao carregar preview:', error);
            showError('Erro ao carregar preview da base');
        })
        .finally(() => {
            hideLoading();
        });
}

function exportBase(baseId) {
    showLoading('Preparando exportação...');
    
    // Build URL with filters
    const params = new URLSearchParams();
    if (ExportBasesState.filters.ano) {
        params.append('ano', ExportBasesState.filters.ano);
    }
    if (ExportBasesState.filters.limite) {
        params.append('limite', ExportBasesState.filters.limite);
    }
    
    const url = `/financeiro/export-bases/api/exportar/${baseId}?${params.toString()}`;
    
    // Create invisible link to trigger download
    const link = document.createElement('a');
    link.href = url;
    link.style.display = 'none';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    // Log export action
    console.log(`[EXPORT] Base ${baseId} exportada com filtros:`, ExportBasesState.filters);
    
    setTimeout(() => {
        hideLoading();
        showNotification('Exportação iniciada! O download deve começar em breve.', 'success');
    }, 1000);
}

// ==========================================
// RENDER FUNCTIONS
// ==========================================

function renderBasesGrid(bases) {
    const basesGrid = document.getElementById('bases-grid');
    if (!basesGrid) return;
    
    basesGrid.innerHTML = '';
    
    bases.forEach(base => {
        const baseCard = createBaseCard(base);
        basesGrid.appendChild(baseCard);
    });
}

function createBaseCard(base) {
    const card = document.createElement('div');
    card.className = `base-card base-${base.cor}`;
    card.onclick = () => handleBaseClick(base.id);
    
    card.innerHTML = `
        <div class="base-card-header">
            <div class="base-info">
                <h3 class="base-nome">${base.nome}</h3>
                <p class="base-descricao">${base.descricao}</p>
            </div>
            <div class="base-icon-container">
                <i class="mdi ${base.icon}"></i>
            </div>
        </div>
        
        <div class="base-stats">
            <div class="base-total">
                <strong>${formatNumber(base.total_registros)}</strong> registros disponíveis
            </div>
            <div class="base-actions">
                <button class="btn btn-outline-primary btn-sm" onclick="event.stopPropagation(); handleBaseClick('${base.id}')">
                    <i class="mdi mdi-eye"></i>
                    Preview
                </button>
                <button class="btn btn-success btn-sm" onclick="event.stopPropagation(); handleDirectExport('${base.id}')">
                    <i class="mdi mdi-download"></i>
                    Exportar
                </button>
            </div>
        </div>
    `;
    
    return card;
}

// ==========================================
// MODAL FUNCTIONS
// ==========================================

function showPreviewModal(previewData) {
    const base = ExportBasesState.currentBase;
    if (!base) return;
    
    // Update modal header
    document.getElementById('preview-base-nome').textContent = base.nome;
    document.getElementById('preview-base-descricao').textContent = base.descricao;
    document.getElementById('preview-total-registros').textContent = `${formatNumber(base.total_registros)} registros total`;
    
    // Update modal table
    renderPreviewTable(previewData);
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('previewModal'));
    modal.show();
}

function renderPreviewTable(data) {
    const table = document.getElementById('preview-table');
    if (!table || !data || data.length === 0) {
        table.innerHTML = '<tbody><tr><td colspan="100%" class="text-center">Nenhum dado disponível</td></tr></tbody>';
        return;
    }
    
    // Get headers from first row
    const headers = Object.keys(data[0]);
    
    // Create table header
    const thead = table.querySelector('thead');
    thead.innerHTML = `
        <tr>
            ${headers.map(header => `<th>${formatHeader(header)}</th>`).join('')}
        </tr>
    `;
    
    // Create table body
    const tbody = table.querySelector('tbody');
    tbody.innerHTML = data.map(row => `
        <tr>
            ${headers.map(header => `<td>${formatCellValue(row[header], header)}</td>`).join('')}
        </tr>
    `).join('');
}

function showConfirmExportModal() {
    const base = ExportBasesState.currentBase;
    if (!base) return;
    
    // Update modal content
    document.getElementById('confirm-base-nome').textContent = base.nome;
    document.getElementById('confirm-ano').textContent = ExportBasesState.filters.ano || 'Todos os anos';
    document.getElementById('confirm-limite').textContent = ExportBasesState.filters.limite || 'Todos os registros';
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('confirmExportModal'));
    modal.show();
}

// ==========================================
// UTILITY FUNCTIONS
// ==========================================

function formatHeader(header) {
    // Convert snake_case to Title Case
    return header
        .replace(/_/g, ' ')
        .split(' ')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
}

function formatCellValue(value, header) {
    if (value === null || value === undefined) return '-';
    
    // Format specific types
    if (header.includes('data')) {
        return formatDate(value);
    }
    
    if (header.includes('valor') || header.includes('price') || header.includes('amount')) {
        return formatCurrency(value);
    }
    
    if (typeof value === 'number') {
        return formatNumber(value);
    }
    
    return String(value);
}

function formatNumber(value) {
    if (!value && value !== 0) return '-';
    return new Intl.NumberFormat('pt-BR').format(value);
}

function formatCurrency(value) {
    if (!value && value !== 0) return 'R$ 0,00';
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(value);
}

function formatDate(dateString) {
    if (!dateString) return '-';
    try {
        const date = new Date(dateString);
        return date.toLocaleDateString('pt-BR');
    } catch (error) {
        return dateString;
    }
}

function setupLoadingStates() {
    // Setup loading overlay
}

function showLoading(message = 'Carregando...') {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        const messageElement = overlay.querySelector('.last-update');
        if (messageElement) {
            messageElement.textContent = message;
        }
        overlay.style.display = 'flex';
    }
}

function hideLoading() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.style.display = 'none';
    }
}

function showError(message) {
    showNotification(message, 'error');
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === 'success' ? 'var(--success)' : type === 'error' ? 'var(--danger)' : 'var(--info)'};
        color: white;
        padding: 16px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 10000;
        min-width: 300px;
        animation: slideInRight 0.3s ease;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
    `;
    
    notification.innerHTML = `
        <div>
            <i class="mdi ${type === 'success' ? 'mdi-check-circle' : type === 'error' ? 'mdi-alert-circle' : 'mdi-information'}"></i>
            ${message}
        </div>
        <button class="notification-close" onclick="this.parentElement.remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 18px; opacity: 0.8;">&times;</button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (notification.parentElement) {
            notification.style.animation = 'slideOutRight 0.3s ease';
            setTimeout(() => {
                if (notification.parentElement) {
                    notification.remove();
                }
            }, 300);
        }
    }, 5000);
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    @keyframes slideOutRight {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(style);

console.log('✅ Export Bases Financeiro - JavaScript loaded successfully');