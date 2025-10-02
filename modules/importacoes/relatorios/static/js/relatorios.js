// Relatórios - JavaScript Modular

document.addEventListener('DOMContentLoaded', function() {
    // Inicializar módulo de relatórios
    initRelatorios();
});

function initRelatorios() {
    console.log('Inicializando módulo de relatórios...');
    
    // Configurar filtros
    setupFilters();
    
    // Configurar tabela
    setupOperationsTable();
    
    // Configurar eventos de export
    setupExportEvents();
    
    // Auto-atualizar dados a cada 5 minutos
    setInterval(refreshData, 5 * 60 * 1000);
}

function setupFilters() {
    const filterForm = document.querySelector('.filter-form');
    const startDateInput = document.getElementById('start_date');
    const endDateInput = document.getElementById('end_date');
    
    if (!filterForm) return;
    
    // Validação de datas
    if (startDateInput && endDateInput) {
        startDateInput.addEventListener('change', function() {
            if (this.value && endDateInput.value) {
                if (new Date(this.value) > new Date(endDateInput.value)) {
                    endDateInput.value = this.value;
                }
            }
            endDateInput.min = this.value;
        });
        
        endDateInput.addEventListener('change', function() {
            if (this.value && startDateInput.value) {
                if (new Date(this.value) < new Date(startDateInput.value)) {
                    startDateInput.value = this.value;
                }
            }
            startDateInput.max = this.value;
        });
    }
    
    // Loading state no formulário
    filterForm.addEventListener('submit', function() {
        showLoadingState();
    });
}

function setupOperationsTable() {
    const table = document.querySelector('.operations-table');
    if (!table) return;
    
    // Adicionar funcionalidade de ordenação
    const headers = table.querySelectorAll('th');
    headers.forEach((header, index) => {
        if (index < 4) { // Excluir coluna de ações
            header.style.cursor = 'pointer';
            header.addEventListener('click', () => sortTable(index));
        }
    });
    
    // Tooltip para dados truncados
    const cells = table.querySelectorAll('.operation-details');
    cells.forEach(cell => {
        if (cell.scrollWidth > cell.clientWidth) {
            cell.title = cell.textContent;
        }
    });
}

function sortTable(columnIndex) {
    const table = document.querySelector('.operations-table tbody');
    const rows = Array.from(table.querySelectorAll('tr'));
    
    // Determinar direção da ordenação
    const header = document.querySelector(`.operations-table th:nth-child(${columnIndex + 1})`);
    const isAscending = !header.classList.contains('sort-desc');
    
    // Remover classes de ordenação anteriores
    document.querySelectorAll('.operations-table th').forEach(th => {
        th.classList.remove('sort-asc', 'sort-desc');
    });
    
    // Adicionar classe de ordenação atual
    header.classList.add(isAscending ? 'sort-asc' : 'sort-desc');
    
    // Ordenar linhas
    rows.sort((a, b) => {
        const aValue = a.children[columnIndex].textContent.trim();
        const bValue = b.children[columnIndex].textContent.trim();
        
        // Ordenação por data
        if (columnIndex === 0) {
            return isAscending ? 
                new Date(aValue) - new Date(bValue) : 
                new Date(bValue) - new Date(aValue);
        }
        
        // Ordenação alfabética
        return isAscending ? 
            aValue.localeCompare(bValue) : 
            bValue.localeCompare(aValue);
    });
    
    // Reordenar DOM
    rows.forEach(row => table.appendChild(row));
}

function setupExportEvents() {
    // PDF Export com feedback visual
    const pdfButtons = document.querySelectorAll('a[href*="generate_pdf"]');
    pdfButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            // Mostrar feedback visual
            const originalText = this.innerHTML;
            this.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Gerando...';
            this.classList.add('disabled');
            
            // Restaurar após 3 segundos
            setTimeout(() => {
                this.innerHTML = originalText;
                this.classList.remove('disabled');
            }, 3000);
        });
    });
}

function showLoadingState() {
    const operationsCard = document.querySelector('.operations-card');
    if (!operationsCard) return;
    
    // Criar overlay de loading
    const loadingOverlay = document.createElement('div');
    loadingOverlay.className = 'loading-overlay';
    loadingOverlay.innerHTML = `
        <div class="loading-spinner"></div>
    `;
    
    operationsCard.style.position = 'relative';
    operationsCard.appendChild(loadingOverlay);
}

function hideLoadingState() {
    const loadingOverlay = document.querySelector('.loading-overlay');
    if (loadingOverlay) {
        loadingOverlay.remove();
    }
}

function refreshData() {
    // Verificar se há filtros ativos
    const form = document.querySelector('.filter-form');
    if (!form) return;
    
    const formData = new FormData(form);
    const hasFilters = formData.get('start_date') || formData.get('end_date');
    
    if (hasFilters) {
        console.log('Atualizando dados dos relatórios...');
        // Aqui você pode implementar uma atualização AJAX se necessário
    }
}

// Funções utilitárias
function showMessage(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    const container = document.querySelector('.relatorios-container');
    container.insertBefore(alertDiv, container.firstChild);
    
    // Auto-remover após 5 segundos
    setTimeout(() => {
        if (alertDiv && alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 5000);
}

function formatDate(dateString) {
    if (!dateString) return 'N/A';
    
    const date = new Date(dateString);
    return date.toLocaleDateString('pt-BR');
}

function exportToCSV() {
    const table = document.querySelector('.operations-table');
    if (!table) return;
    
    const rows = table.querySelectorAll('tr');
    const csv = [];
    
    rows.forEach(row => {
        const cols = row.querySelectorAll('td, th');
        const rowData = [];
        
        cols.forEach((col, index) => {
            if (index < 4) { // Excluir coluna de ações
                rowData.push(col.textContent.trim());
            }
        });
        
        csv.push(rowData.join(','));
    });
    
    const csvContent = csv.join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = 'relatorio_operacoes.csv';
    a.click();
    
    window.URL.revokeObjectURL(url);
}

// Expor funções globalmente se necessário
window.RelatoriosModule = {
    exportToCSV,
    refreshData,
    showMessage
};
