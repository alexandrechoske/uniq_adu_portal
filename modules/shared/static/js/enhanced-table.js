/**
 * Enhanced Data Table - UniSystem Portal
 * Classe para gerenciar tabelas com paginação, ordenação e busca
 */
class EnhancedDataTable {
    constructor(tableId, config = {}) {
        // Support both signatures: constructor(tableId, config) and constructor(config)
        if (typeof tableId === 'string') {
            this.config = {
                tableId: tableId,
                containerId: config.containerId || tableId + '-container',
                searchInputId: config.searchInputId || tableId + '-search',
                itemsPerPage: config.itemsPerPage || 15,
                sortable: config.sortable !== false,
                searchable: config.searchable !== false,
                searchFields: config.searchFields || [],
                sortField: config.sortField || null,
                sortOrder: config.sortOrder || 'asc',
                ...config
            };
        } else {
            // Legacy support for constructor(config)
            this.config = {
                tableId: tableId.tableId,
                containerId: tableId.containerId || tableId.tableId + '-container',
                searchInputId: tableId.searchInputId || tableId.tableId + '-search',
                itemsPerPage: tableId.pageSize || tableId.itemsPerPage || 15,
                sortable: tableId.sortable !== false,
                searchable: tableId.searchable !== false,
                columns: tableId.columns || [],
                searchFields: tableId.searchFields || [],
                sortField: tableId.sortField || null,
                sortOrder: tableId.sortOrder || 'asc',
                ...tableId
            };
        }

        this.data = [];
        this.filteredData = [];
        this.currentPage = 1;
        this.sortColumn = null;
        this.sortDirection = this.config.sortOrder;
        this.searchQuery = '';

        this.init();
    }

    init() {
        this.setupDOM();
        this.setupEventListeners();
    }

    setupDOM() {
        this.table = document.getElementById(this.config.tableId);
        
        if (!this.table) {
            console.error(`Table with ID ${this.config.tableId} not found`);
            return;
        }

        // Find container - try multiple strategies
        this.container = document.getElementById(this.config.containerId);
        
        if (!this.container) {
            // Try to find parent container with enhanced-table-section class
            this.container = this.table.closest('.enhanced-table-section');
        }
        
        if (!this.container) {
            // Try to find any parent container that might work
            this.container = this.table.closest('div');
        }
        
        if (!this.container) {
            console.error(`Container for table ${this.config.tableId} not found`);
            return;
        }

        // Find search input
        this.searchInput = document.getElementById(this.config.searchInputId);
        if (!this.searchInput) {
            // Try to find search input within container
            this.searchInput = this.container.querySelector('input[type="text"]');
        }

        // Add enhanced classes
        this.table.classList.add('enhanced-data-table');
        
        // Setup search container
        if (this.config.searchable && this.searchInput) {
            this.setupSearchContainer();
        }

        // Setup pagination container
        this.setupPaginationContainer();

        // Setup table headers
        this.setupTableHeaders();
        
        // Setup initial sorting if specified
        this.setupInitialSorting();
        
        console.log('[ENHANCED_TABLE] DOM setup completed for', this.config.tableId);
    }

    setupInitialSorting() {
        if (this.config.sortField) {
            // Find column index by field name
            const headers = Array.from(this.table.querySelectorAll('thead th'));
            const columnIndex = headers.findIndex((header, index) => {
                const columnKey = this.getColumnKey(index);
                return columnKey === this.config.sortField;
            });
            
            if (columnIndex >= 0) {
                this.sortColumn = columnIndex;
                console.log(`[ENHANCED_TABLE] Initial sort set to column ${columnIndex} (${this.config.sortField}), direction: ${this.config.sortOrder}`);
            } else {
                console.warn(`[ENHANCED_TABLE] Sort field '${this.config.sortField}' not found in table headers`);
            }
        }
    }

    setupTableHeaders() {
        // Make headers sortable
        if (this.config.sortable) {
            this.setupSortableHeaders();
        }
    }

    setupSearchContainer() {
        const searchContainer = this.searchInput.closest('.enhanced-search-container');
        if (searchContainer) {
            // Add clear button if not exists
            let clearBtn = searchContainer.querySelector('.enhanced-search-clear');
            if (!clearBtn) {
                clearBtn = document.createElement('button');
                clearBtn.className = 'enhanced-search-clear';
                clearBtn.innerHTML = '<i class="mdi mdi-close"></i>';
                clearBtn.type = 'button';
                searchContainer.appendChild(clearBtn);

                clearBtn.addEventListener('click', () => {
                    this.searchInput.value = '';
                    this.handleSearch('');
                    clearBtn.classList.remove('show');
                });
            }
        }
    }

    setupPaginationContainer() {
        if (!this.container) {
            console.warn('[ENHANCED_TABLE] Container not found, creating pagination container after table');
            // Create pagination container after the table
            const paginationContainer = document.createElement('div');
            paginationContainer.className = 'enhanced-pagination';
            paginationContainer.id = this.config.tableId + '-pagination';
            
            // Insert after table or table's parent container
            const insertTarget = this.table.closest('.enhanced-table-container') || this.table.parentElement;
            if (insertTarget && insertTarget.parentElement) {
                insertTarget.parentElement.insertBefore(paginationContainer, insertTarget.nextSibling);
            } else {
                this.table.parentElement.appendChild(paginationContainer);
            }
            
            this.paginationContainer = paginationContainer;
            return;
        }

        // Find or create pagination container within the main container
        let paginationContainer = this.container.querySelector('.enhanced-pagination');
        if (!paginationContainer) {
            paginationContainer = document.createElement('div');
            paginationContainer.className = 'enhanced-pagination';
            paginationContainer.id = this.config.tableId + '-pagination';
            this.container.appendChild(paginationContainer);
        }
        this.paginationContainer = paginationContainer;
    }

    setupSortableHeaders() {
        const headers = this.table.querySelectorAll('thead th');
        headers.forEach((header, index) => {
            const headerText = header.textContent.trim().toLowerCase();
            const isSortable = header.dataset.sortable !== 'false' && headerText !== 'ações';

            if (!isSortable) {
                header.classList.remove('sortable', 'sorted-asc', 'sorted-desc');
                header.removeAttribute('data-column');
                return;
            }

            if (header.dataset.sortHandlerAttached === 'true') {
                return;
            }

            header.classList.add('sortable');
            header.dataset.column = index;
            header.dataset.sortHandlerAttached = 'true';

            header.addEventListener('click', (event) => {
                if (event.target.closest('.column-filter-icon')) {
                    return;
                }
                this.handleSort(index, header);
            });
        });
    }

    setupEventListeners() {
        if (this.searchInput) {
            this.searchInput.addEventListener('input', (e) => {
                const value = e.target.value.trim();
                this.handleSearch(value);
                
                // Show/hide clear button
                const clearBtn = this.searchInput.closest('.enhanced-search-container')?.querySelector('.enhanced-search-clear');
                if (clearBtn) {
                    clearBtn.classList.toggle('show', value.length > 0);
                }
            });
        }

        // Setup scroll shadows
        if (this.container) {
            this.container.addEventListener('scroll', () => {
                this.updateScrollShadows();
            });
        }
    }

    setData(data) {
        console.log('[ENHANCED_TABLE] setData called with', data?.length || 0, 'items');
        this.data = data || [];
        this.filteredData = [...this.data];
        this.currentPage = 1;
        
        // Apply initial sorting if configured and not already set
        if (this.config.sortField && this.sortColumn === null) {
            console.log('[ENHANCED_TABLE] Applying initial sort configuration');
            this.setupInitialSorting();
        }
        
        this.sortData();
        console.log('[ENHANCED_TABLE] Calling render with', this.filteredData.length, 'filtered items');
        this.render();
        console.log('[ENHANCED_TABLE] Render completed');
    }

    handleSearch(query) {
        this.searchQuery = query.toLowerCase();
        this.currentPage = 1;

        if (!this.searchQuery) {
            this.filteredData = [...this.data];
        } else {
            this.filteredData = this.data.filter(row => {
                return Object.values(row).some(value => {
                    if (value === null || value === undefined) return false;
                    return String(value).toLowerCase().includes(this.searchQuery);
                });
            });
        }

        this.render();
    }

    handleSort(columnIndex, headerElement) {
        // Remove previous sort indicators
        this.table.querySelectorAll('thead th').forEach(th => {
            th.classList.remove('sorted-asc', 'sorted-desc');
            const indicator = th.querySelector('.column-sort-indicator');
            if (indicator) {
                indicator.classList.remove('active');
                indicator.innerHTML = '';
            }
        });

        // Determine sort direction
        if (this.sortColumn === columnIndex) {
            this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
        } else {
            this.sortDirection = 'asc';
        }

        this.sortColumn = columnIndex;

        // Add sort indicator
        headerElement.classList.add(this.sortDirection === 'asc' ? 'sorted-asc' : 'sorted-desc');
        const indicator = headerElement.querySelector('.column-sort-indicator');
        if (indicator) {
            indicator.classList.add('active');
            indicator.innerHTML = this.sortDirection === 'asc'
                ? '<i class="mdi mdi-arrow-up"></i>'
                : '<i class="mdi mdi-arrow-down"></i>';
        }

        this.sortData();
        this.render();
    }

    sortData() {
        if (this.sortColumn === null) return;

        const headers = Array.from(this.table.querySelectorAll('thead th'));
        const columnKey = this.getColumnKey(this.sortColumn);
        
        console.log(`[ENHANCED_TABLE] Sorting by column ${this.sortColumn} (${columnKey}), direction: ${this.sortDirection}`);

        this.filteredData.sort((a, b) => {
            let aVal = this.getValueForSorting(a, columnKey);
            let bVal = this.getValueForSorting(b, columnKey);

            // Handle null/undefined values
            if (aVal === null || aVal === undefined) aVal = '';
            if (bVal === null || bVal === undefined) bVal = '';

            // Special handling for dates - check if values look like Brazilian dates first
            if (this.isBrazilianDate(aVal) || this.isBrazilianDate(bVal)) {
                console.log(`[ENHANCED_TABLE] Comparing dates: "${aVal}" vs "${bVal}"`);
                
                const aDate = this.parseDate(aVal);
                const bDate = this.parseDate(bVal);
                
                console.log(`[ENHANCED_TABLE] Parsed dates: ${aDate ? aDate.toISOString().split('T')[0] : 'null'} vs ${bDate ? bDate.toISOString().split('T')[0] : 'null'}`);

                // If both are valid dates, compare them
                if (aDate && bDate) {
                    const result = this.sortDirection === 'asc' ? aDate - bDate : bDate - aDate;
                    console.log(`[ENHANCED_TABLE] Date comparison result: ${result}`);
                    return result;
                }
                
                // If only one is a valid date, valid date comes first (or last depending on direction)
                if (aDate && !bDate) return this.sortDirection === 'asc' ? -1 : 1;
                if (!aDate && bDate) return this.sortDirection === 'asc' ? 1 : -1;
                
                // If neither is a valid date, fall back to string comparison
            }

            // Try to parse as numbers for proper sorting
            const aNum = parseFloat(String(aVal).replace(/[^\d.-]/g, ''));
            const bNum = parseFloat(String(bVal).replace(/[^\d.-]/g, ''));

            if (!isNaN(aNum) && !isNaN(bNum)) {
                return this.sortDirection === 'asc' ? aNum - bNum : bNum - aNum;
            }

            // Default string comparison
            const aStr = String(aVal).toLowerCase();
            const bStr = String(bVal).toLowerCase();

            if (this.sortDirection === 'asc') {
                return aStr.localeCompare(bStr, 'pt-BR');
            } else {
                return bStr.localeCompare(aStr, 'pt-BR');
            }
        });
        
        console.log(`[ENHANCED_TABLE] Sorting completed. First 3 items:`, 
            this.filteredData.slice(0, 3).map(item => ({ [columnKey]: item[columnKey] })));
    }

    // New helper function to detect Brazilian date format
    isBrazilianDate(value) {
        if (!value || typeof value !== 'string') return false;
        // Check for DD/MM/YYYY format (with or without time)
        return /^\d{1,2}\/\d{1,2}\/\d{4}(\s\d{1,2}:\d{1,2}(:\d{1,2})?)?$/.test(value.trim());
    }

    parseDate(dateStr) {
        if (!dateStr) return null;
        
        // Clean the string
        const cleanStr = String(dateStr).trim();
        
        // Try Brazilian format DD/MM/YYYY (with optional time)
        const brazilianMatch = cleanStr.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})(\s.*)?$/);
        if (brazilianMatch) {
            const [, day, month, year] = brazilianMatch;
            const dayNum = parseInt(day, 10);
            const monthNum = parseInt(month, 10);
            const yearNum = parseInt(year, 10);
            
            // Basic validation
            if (dayNum >= 1 && dayNum <= 31 && monthNum >= 1 && monthNum <= 12 && yearNum >= 1900) {
                const date = new Date(yearNum, monthNum - 1, dayNum);
                // Double check the date is valid (handles things like Feb 30)
                if (date.getFullYear() === yearNum && 
                    date.getMonth() === monthNum - 1 && 
                    date.getDate() === dayNum) {
                    return date;
                }
            }
        }

        // Try ISO format as fallback
        const date = new Date(cleanStr);
        return isNaN(date.getTime()) ? null : date;
    }

    getColumnKey(columnIndex) {
        // Map column index to data key
        if (this.config.columns && this.config.columns[columnIndex]) {
            return this.config.columns[columnIndex].key;
        }

        // PRIORIZAR data-sort attribute do HTML (mais confiável)
        const headers = Array.from(this.table.querySelectorAll('thead th'));
        const headerElement = headers[columnIndex];
        
        if (!headerElement) {
            console.warn(`[ENHANCED_TABLE] Header at index ${columnIndex} not found`);
            return `column_${columnIndex}`;
        }
        
        // 1. Tentar obter de data-sort (MELHOR OPÇÃO)
        const dataSortAttr = headerElement.getAttribute('data-sort');
        if (dataSortAttr) {
            console.log(`[ENHANCED_TABLE] Using data-sort="${dataSortAttr}" for column ${columnIndex}`);
            
            // Aplicar mapeamento se necessário (mesma lógica dos filtros)
            const columnMap = {
                'status': 'status_sistema',        // data-sort="status" → status_sistema
                'material': 'mercadoria',          // data-sort="material" → mercadoria
                'urf_despacho': 'urf_despacho_normalizado' // data-sort="urf_despacho" → normalizado
            };
            
            return columnMap[dataSortAttr] || dataSortAttr;
        }
        
        // 2. Fallback: usar texto do header (menos confiável por causa de traduções)
        const headerText = headerElement.textContent?.trim()?.toLowerCase();
        
        if (!headerText) {
            console.warn(`[ENHANCED_TABLE] Header text at index ${columnIndex} is empty`);
            return `column_${columnIndex}`;
        }

        const keyMap = {
            'ações': 'actions',
            'ref. unique': 'ref_unique',
            'pedido': 'ref_importador',
            'importador': 'importador',
            'data abertura': 'data_abertura',
            'exportador': 'exportador_fornecedor',
            'modal': 'modal',
            'status': 'status_sistema',     // CORRIGIDO
            'custo total': 'custo_total',
            'previsão chegada': 'data_chegada',
            'data chegada': 'data_chegada',
            'material': 'mercadoria',        // CORRIGIDO
            'urf': 'urf_despacho_normalizado', // CORRIGIDO
            'urf despacho': 'urf_despacho_normalizado',
            'número pedido': 'numero_pedido',
            'cliente': 'cliente',
            'data embarque': 'data_embarque',
            'canal': 'canal',
            'valor (r$)': 'valor'
        };

        return keyMap[headerText] || headerText.replace(/[^a-z0-9]/g, '_');
    }

    getValueForSorting(item, columnKey) {
        // Special handling for URF column - implement fallback logic matching dashboard.js
        if (columnKey === 'urf_despacho_normalizado') {
            const normalizedValue = item.urf_despacho_normalizado;
            const originalValue = item.urf_despacho;
            
            // If normalized value exists and is not 'N/A', use it; otherwise fallback to original
            if (normalizedValue && normalizedValue !== 'N/A') {
                // console.log(`[ENHANCED_TABLE] URF - using normalized: "${normalizedValue}"`);
                return normalizedValue;
            }
            
            // console.log(`[ENHANCED_TABLE] URF - using fallback: "${originalValue}"`);
            return originalValue || '';
        }

        // Standard field access for all other columns
        return item[columnKey];
    }

    render() {
        this.renderTable();
        this.renderPagination();
        this.updateScrollShadows();
    }

    renderTable() {
        console.log('[ENHANCED_TABLE] renderTable called');
        const tbody = this.table.querySelector('tbody');
        if (!tbody) {
            console.error('[ENHANCED_TABLE] tbody not found in table');
            return;
        }

        tbody.innerHTML = '';
        console.log('[ENHANCED_TABLE] tbody cleared');

        const startIndex = (this.currentPage - 1) * this.config.itemsPerPage;
        const endIndex = startIndex + this.config.itemsPerPage;
        const pageData = this.filteredData.slice(startIndex, endIndex);
        console.log('[ENHANCED_TABLE] Page data:', pageData.length, 'items for page', this.currentPage);

        if (pageData.length === 0) {
            console.log('[ENHANCED_TABLE] No data to display, rendering empty state');
            this.renderEmptyState();
            return;
        }

        console.log('[ENHANCED_TABLE] Rendering', pageData.length, 'rows');
        pageData.forEach((row, index) => {
            const tr = document.createElement('tr');
            const absoluteIndex = startIndex + index; // Calculate absolute index in the full array
            const rowHtml = this.renderRow(row, absoluteIndex);
            console.log(`[ENHANCED_TABLE] Row ${index} HTML:`, rowHtml.substring(0, 100) + '...');
            tr.innerHTML = rowHtml;
            tbody.appendChild(tr);
        });
        console.log('[ENHANCED_TABLE] All rows appended to tbody');
    }

    renderRow(row) {
        // This should be overridden by specific implementations
        return '<td colspan="100%">Row rendering not implemented</td>';
    }

    renderEmptyState() {
        const tbody = this.table.querySelector('tbody');
        const colCount = this.table.querySelectorAll('thead th').length;
        
        tbody.innerHTML = `
            <tr>
                <td colspan="${colCount}" class="enhanced-table-empty">
                    <i class="mdi mdi-database-search"></i>
                    <h3>Nenhum resultado encontrado</h3>
                    <p>${this.searchQuery ? 'Tente ajustar os filtros de busca' : 'Não há dados para exibir'}</p>
                </td>
            </tr>
        `;
    }

    renderPagination() {
        if (!this.filteredData || !Array.isArray(this.filteredData)) {
            console.warn('[ENHANCED_TABLE] filteredData is not a valid array, initializing empty');
            this.filteredData = [];
        }
        
        const totalItems = this.filteredData.length || 0;
        const totalPages = Math.ceil(totalItems / this.config.itemsPerPage) || 1;
        const startItem = totalItems > 0 ? (this.currentPage - 1) * this.config.itemsPerPage + 1 : 0;
        const endItem = totalItems > 0 ? Math.min(this.currentPage * this.config.itemsPerPage, totalItems) : 0;

        this.paginationContainer.innerHTML = `
            <div class="pagination-info">
                Mostrando ${startItem} - ${endItem} de ${totalItems} registros
            </div>
            <div class="pagination-controls">
                <button class="pagination-btn" ${this.currentPage === 1 ? 'disabled' : ''} data-page="1">
                    <i class="mdi mdi-chevron-double-left"></i>
                </button>
                <button class="pagination-btn" ${this.currentPage === 1 ? 'disabled' : ''} data-page="${this.currentPage - 1}">
                    <i class="mdi mdi-chevron-left"></i>
                </button>
                ${this.renderPageNumbers(totalPages)}
                <button class="pagination-btn" ${this.currentPage === totalPages ? 'disabled' : ''} data-page="${this.currentPage + 1}">
                    <i class="mdi mdi-chevron-right"></i>
                </button>
                <button class="pagination-btn" ${this.currentPage === totalPages ? 'disabled' : ''} data-page="${totalPages}">
                    <i class="mdi mdi-chevron-double-right"></i>
                </button>
            </div>
        `;

        // Add pagination event listeners
        this.paginationContainer.querySelectorAll('.pagination-btn[data-page]').forEach(btn => {
            btn.addEventListener('click', () => {
                const page = parseInt(btn.dataset.page);
                if (page && page !== this.currentPage && page >= 1 && page <= totalPages) {
                    this.currentPage = page;
                    this.render();
                }
            });
        });
    }

    renderPageNumbers(totalPages) {
        if (totalPages <= 1) return '';

        const pages = [];
        const maxVisible = 5;
        
        let startPage = Math.max(1, this.currentPage - Math.floor(maxVisible / 2));
        let endPage = Math.min(totalPages, startPage + maxVisible - 1);
        
        if (endPage - startPage < maxVisible - 1) {
            startPage = Math.max(1, endPage - maxVisible + 1);
        }

        for (let i = startPage; i <= endPage; i++) {
            pages.push(`
                <button class="pagination-btn ${i === this.currentPage ? 'active' : ''}" data-page="${i}">
                    ${i}
                </button>
            `);
        }

        return pages.join('');
    }

    updateScrollShadows() {
        if (!this.container) return;

        const scrollLeft = this.container.scrollLeft;
        const scrollWidth = this.container.scrollWidth;
        const clientWidth = this.container.clientWidth;

        this.container.classList.toggle('scroll-left', scrollLeft > 0);
        this.container.classList.toggle('scroll-right', scrollLeft < scrollWidth - clientWidth);
    }

    // Utility functions
    formatCurrency(value) {
        if (value === null || value === undefined || isNaN(value)) return 'R$ 0,00';
        
        const num = parseFloat(value);
        return num.toLocaleString('pt-BR', {
            style: 'currency',
            currency: 'BRL'
        });
    }

    formatNumber(value, decimals = 0) {
        if (value === null || value === undefined || isNaN(value)) return '0';
        
        const num = parseFloat(value);
        return num.toLocaleString('pt-BR', {
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals
        });
    }

    formatDate(dateStr) {
        if (!dateStr) return '-';
        
        // If already in Brazilian format, return as is
        if (dateStr.match(/\d{1,2}\/\d{1,2}\/\d{4}/)) {
            return dateStr;
        }

        // Try to parse and format
        const date = new Date(dateStr);
        if (isNaN(date.getTime())) return dateStr;

        return date.toLocaleDateString('pt-BR');
    }

    getStatusBadge(status) {
        if (!status) return '<span class="status-badge">-</span>';

        const statusLower = status.toLowerCase();
        let className = 'status-badge';

        if (statusLower.includes('andamento') || statusLower.includes('processo')) {
            className += ' em-andamento';
        } else if (statusLower.includes('concluido') || statusLower.includes('finalizado')) {
            className += ' concluido';
        } else if (statusLower.includes('pendente') || statusLower.includes('aguardando')) {
            className += ' pendente';
        } else if (statusLower.includes('cancelado') || statusLower.includes('suspenso')) {
            className += ' cancelado';
        }

        return `<span class="${className}">${status}</span>`;
    }
}
