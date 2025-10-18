/**
 * FILTROS DE COLUNA ESTILO EXCEL
 * Permite filtrar múltiplas colunas simultaneamente com dropdowns de seleção
 */

(function() {
    'use strict';

    const CURRENCY_FORMATTER = new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    });

    // Estado dos filtros ativos
    const activeFilters = {};
    let allTableData = [];
    
    /**
     * Inicializar filtros de coluna
     */
    window.initColumnFilters = function(tableId = 'recent-operations-table') {
        console.log('[COLUMN_FILTERS] Inicializando filtros de coluna...');
        
        const table = document.getElementById(tableId);
        if (!table) {
            console.error('[COLUMN_FILTERS] Tabela não encontrada:', tableId);
            return;
        }
        
        // Adicionar ícones de filtro nos headers
        const headers = table.querySelectorAll('thead th');
        headers.forEach((header, index) => {
            // Pular coluna de ações
            if (index === 0) return;
            
            const columnName = header.getAttribute('data-sort') || `col_${index}`;
            const headerText = header.textContent.trim();
            
            // Criar estrutura do header com filtro
            const headerContent = document.createElement('div');
            headerContent.className = 'column-header-content';
            headerContent.innerHTML = `
                <span class="column-header-text">${headerText}</span>
                <i class="mdi mdi-filter-outline column-filter-icon" 
                   data-column="${columnName}" 
                   data-column-index="${index}"
                   title="Filtrar ${headerText}"></i>
            `;
            
            header.innerHTML = '';
            header.appendChild(headerContent);
            
            // Evento de clique no ícone de filtro
            const filterIcon = headerContent.querySelector('.column-filter-icon');
            filterIcon.addEventListener('click', (e) => {
                e.stopPropagation();
                toggleFilterDropdown(columnName, index, header, headerText);
            });
        });
        
        // Criar badge de filtros ativos
        createActiveFiltersBadge();
        
        // Fechar dropdown ao clicar fora
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.column-filter-dropdown') && 
                !e.target.closest('.column-filter-icon')) {
                closeAllDropdowns();
            }
        });
        
        console.log('[COLUMN_FILTERS] Filtros inicializados com sucesso');
    };
    
    /**
     * Alternar dropdown de filtro
     */
    function toggleFilterDropdown(columnName, columnIndex, headerElement, headerText) {
        // Fechar outros dropdowns
        closeAllDropdowns();
        
        // Verificar se já existe dropdown
        let dropdown = document.querySelector('.column-filter-dropdown.show');
        if (dropdown) {
            dropdown.remove();
            return;
        }
        
        // Coletar valores únicos da coluna
        const values = getUniqueColumnValues(columnIndex);
        
        // Criar dropdown
        dropdown = createFilterDropdown(columnName, columnIndex, headerText, values);
        
        // Posicionar dropdown
        const rect = headerElement.getBoundingClientRect();
        dropdown.style.left = `${rect.left}px`;
        dropdown.style.top = `${rect.bottom + window.scrollY}px`;
        
        document.body.appendChild(dropdown);
        dropdown.classList.add('show');
        
        // Focar na busca
        const searchInput = dropdown.querySelector('.filter-dropdown-search input');
        if (searchInput) {
            setTimeout(() => searchInput.focus(), 100);
        }
    }
    
    /**
     * Criar dropdown de filtro
     */
    function createFilterDropdown(columnName, columnIndex, headerText, values) {
        const dropdown = document.createElement('div');
        dropdown.className = 'column-filter-dropdown';
        dropdown.setAttribute('data-column', columnName);
        
        const currentFilters = activeFilters[columnName] || [];
        const allSelected = currentFilters.length === 0 || currentFilters.length === values.length;
        
        dropdown.innerHTML = `
            <div class="filter-dropdown-header">
                <div class="filter-dropdown-title">
                    <span>${headerText}</span>
                    <button class="filter-dropdown-close" title="Fechar">
                        <i class="mdi mdi-close"></i>
                    </button>
                </div>
                <div class="filter-dropdown-search">
                    <input type="text" placeholder="Buscar..." />
                    <i class="mdi mdi-magnify filter-dropdown-search-icon"></i>
                </div>
            </div>
            <div class="filter-dropdown-options">
                <label class="filter-option select-all">
                    <input type="checkbox" ${allSelected ? 'checked' : ''} data-action="select-all" />
                    <span class="filter-option-label">(Selecionar Todos)</span>
                    <span class="filter-option-count">${values.length}</span>
                </label>
                ${values.map(item => {
                    const isChecked = currentFilters.length === 0 || currentFilters.includes(item.value);
                    const displayWithIcon = getDisplayWithIcon(item.value, columnName);
                    return `
                        <label class="filter-option" data-value="${escapeHtml(item.value)}">
                            <input type="checkbox" ${isChecked ? 'checked' : ''} data-value="${escapeHtml(item.value)}" />
                            <span class="filter-option-label" title="${escapeHtml(item.display)}">${displayWithIcon}</span>
                            <span class="filter-option-count">${item.count}</span>
                        </label>
                    `;
                }).join('')}
            </div>
            <div class="filter-dropdown-footer">
                <button class="filter-dropdown-btn filter-dropdown-btn-clear">
                    <i class="mdi mdi-filter-remove"></i> Limpar
                </button>
                <button class="filter-dropdown-btn filter-dropdown-btn-apply">
                    <i class="mdi mdi-check"></i> Aplicar
                </button>
            </div>
        `;
        
        // Eventos
        setupDropdownEvents(dropdown, columnName, columnIndex);
        
        return dropdown;
    }
    
    /**
     * Configurar eventos do dropdown
     */
    function setupDropdownEvents(dropdown, columnName, columnIndex) {
        // Fechar
        dropdown.querySelector('.filter-dropdown-close').addEventListener('click', () => {
            dropdown.remove();
        });
        
        // Busca
        const searchInput = dropdown.querySelector('.filter-dropdown-search input');
        searchInput.addEventListener('input', (e) => {
            const searchTerm = e.target.value.toLowerCase();
            const options = dropdown.querySelectorAll('.filter-option:not(.select-all)');
            
            options.forEach(option => {
                const label = option.querySelector('.filter-option-label').textContent.toLowerCase();
                option.style.display = label.includes(searchTerm) ? 'flex' : 'none';
            });
        });
        
        // Selecionar todos
        const selectAllCheckbox = dropdown.querySelector('[data-action="select-all"]');
        selectAllCheckbox.addEventListener('change', (e) => {
            const checkboxes = dropdown.querySelectorAll('.filter-option:not(.select-all) input[type="checkbox"]');
            const visibleCheckboxes = Array.from(checkboxes).filter(cb => {
                const option = cb.closest('.filter-option');
                return option.style.display !== 'none';
            });
            
            visibleCheckboxes.forEach(cb => {
                cb.checked = e.target.checked;
            });
        });
        
        // Sincronizar "Selecionar Todos" quando checkboxes individuais mudam
        const individualCheckboxes = dropdown.querySelectorAll('.filter-option:not(.select-all) input[type="checkbox"]');
        individualCheckboxes.forEach(cb => {
            cb.addEventListener('change', () => {
                updateSelectAllState(dropdown);
            });
        });
        
        // Botão Limpar
        dropdown.querySelector('.filter-dropdown-btn-clear').addEventListener('click', () => {
            delete activeFilters[columnName];
            applyAllFilters();
            updateFilterIcon(columnName);
            dropdown.remove();
            updateActiveFiltersBadge();
        });
        
        // Botão Aplicar
        dropdown.querySelector('.filter-dropdown-btn-apply').addEventListener('click', () => {
            const checkedValues = Array.from(
                dropdown.querySelectorAll('.filter-option:not(.select-all) input[type="checkbox"]:checked')
            ).map(cb => cb.getAttribute('data-value'));
            
            if (checkedValues.length === 0) {
                delete activeFilters[columnName];
            } else {
                activeFilters[columnName] = checkedValues;
            }
            
            applyAllFilters();
            updateFilterIcon(columnName);
            dropdown.remove();
            updateActiveFiltersBadge();
        });
    }
    
    /**
     * Atualizar estado do "Selecionar Todos"
     */
    function updateSelectAllState(dropdown) {
        const selectAllCheckbox = dropdown.querySelector('[data-action="select-all"]');
        const checkboxes = dropdown.querySelectorAll('.filter-option:not(.select-all) input[type="checkbox"]');
        const visibleCheckboxes = Array.from(checkboxes).filter(cb => {
            const option = cb.closest('.filter-option');
            return option.style.display !== 'none';
        });
        
        const checkedCount = visibleCheckboxes.filter(cb => cb.checked).length;
        selectAllCheckbox.checked = checkedCount === visibleCheckboxes.length;
        selectAllCheckbox.indeterminate = checkedCount > 0 && checkedCount < visibleCheckboxes.length;
    }
    
    /**
     * Coletar valores únicos de uma coluna
     */
    function getUniqueColumnValues(columnIndex) {
        const table = document.getElementById('recent-operations-table');
        const headers = table.querySelectorAll('thead th');
        const columnName = headers[columnIndex]?.getAttribute('data-sort');
        
        console.log(`[COLUMN_FILTERS] Coletando valores únicos para coluna ${columnName} (index ${columnIndex})`);
        
        // CORRIGIDO: Buscar do array global completo em vez da tabela renderizada
        if (!window.currentOperations || !Array.isArray(window.currentOperations)) {
            console.warn('[COLUMN_FILTERS] window.currentOperations não disponível, usando tabela renderizada como fallback');
            return getUniqueValuesFromTable(columnIndex, columnName);
        }
        
        const valueCounts = {};
        
        // Buscar valores do array global completo (todos os 1,128+ registros)
        window.currentOperations.forEach(operation => {
            const rawValue = getColumnValueFromOperation(operation, columnName);
            const values = Array.isArray(rawValue) ? rawValue : [rawValue];

            if (!values.length) {
                values.push('');
            }

            values.forEach(entry => {
                let value = entry;

                if (value === '' || value === '-' || value === null || value === undefined) {
                    value = '(Vazio)';
                }

                valueCounts[value] = (valueCounts[value] || 0) + 1;
            });
        });
        
        console.log(`[COLUMN_FILTERS] ${Object.keys(valueCounts).length} valores únicos encontrados:`, Object.keys(valueCounts));
        
        // Converter para array e ordenar POR CONTAGEM (maior → menor)
        return Object.entries(valueCounts)
            .map(([value, count]) => ({ value, display: value, count }))
            .sort((a, b) => {
                // "(Vazio)" sempre por último
                if (a.value === '(Vazio)') return 1;
                if (b.value === '(Vazio)') return -1;
                
                // Ordenar por contagem (MAIOR para MENOR)
                if (b.count !== a.count) {
                    return b.count - a.count;
                }
                
                // Se contagem igual, ordenar alfabeticamente
                return a.display.localeCompare(b.display);
            });
    }
    
    /**
     * Extrair valor da coluna do objeto operation
     * Lógica especial para colunas com ícones (ex: modal)
     */
    function getColumnValueFromOperation(operation, columnName) {
        if (!operation || !columnName) {
            return '';
        }

        const normalizedColumn = columnName.trim();

        switch (normalizedColumn) {
            case 'modal':
                return normalizeModalValue(operation.modal);
            case 'container':
                return extractContainerValues(operation);
            case 'transit_time':
                return operation.transit_time ?? operation.transit_time_real ?? '';
            case 'peso_bruto':
                return getPesoBrutoValue(operation);
            case 'data_registro':
                return operation.data_registro || operation.data_registro_di || '';
            case 'numero_di':
                return operation.numero_di || operation.numero_declaracao || '';
            case 'canal':
                return operation.canal || operation.canal_parametrizado || '';
            case 'pais':
                return operation.pais || operation.pais_procedencia_normalizado || operation.pais_procedencia || '';
            case 'produtos':
                return summarizeProdutosForFilter(operation);
            case 'despesas':
                return summarizeDespesasForFilter(operation);
            case 'data_desova':
            case 'limite_primeiro_periodo':
            case 'limite_segundo_periodo':
            case 'dias_extras_armazenagem':
            case 'valor_despesas_extras':
                return getArmazenagemFieldValue(operation, normalizedColumn);
            default:
                break;
        }

        const columnMap = {
            'ref_unique': 'ref_unique',
            'ref_importador': 'ref_importador',
            'importador': 'importador',
            'data_abertura': 'data_abertura',
            'exportador_fornecedor': 'exportador_fornecedor',
            'status': 'status_sistema',
            'status_sistema': 'status_sistema',
            'custo_total': 'custo_total',
            'data_chegada': 'data_chegada',
            'material': 'mercadoria',
            'mercadoria': 'mercadoria',
            'urf_despacho': 'urf_despacho_normalizado',
            'urf_despacho_normalizado': 'urf_despacho_normalizado'
        };

        const fieldName = columnMap[normalizedColumn] || normalizedColumn;
        return operation[fieldName];
    }

    function normalizeModalValue(rawModal) {
        if (!rawModal) {
            return '';
        }

        const value = String(rawModal).toUpperCase().trim();

        if (value.includes('MARÍTIMA') || value.includes('MARITIMA')) {
            return 'MARÍTIMO';
        }
        if (value.includes('AÉREA') || value.includes('AEREA')) {
            return 'AÉREO';
        }
        if (value.includes('RODOVIÁRIA') || value.includes('RODOVIARIA')) {
            return 'RODOVIÁRIO';
        }
        if (value.includes('FERROVIÁRIA') || value.includes('FERROVIARIA')) {
            return 'FERROVIÁRIO';
        }
        if (value.includes('POSTAL') || value.includes('CORREIO')) {
            return 'POSTAL';
        }
        if (value.includes('COURIER') || value.includes('EXPRESS')) {
            return 'COURIER';
        }

        return value;
    }

    function extractContainerValues(operation) {
        if (Array.isArray(operation?.__container_values)) {
            return operation.__container_values;
        }

        const rawValue = operation.container || operation.numero_container || operation.conteiner || operation.conteineres;

        if (Array.isArray(rawValue)) {
            return rawValue
                .map(item => (item == null ? '' : String(item).trim()))
                .filter(Boolean);
        }

        if (typeof rawValue !== 'string') {
            return [];
        }

        return rawValue
            .split(/[,;|\n]+/)
            .map(value => value.trim())
            .filter(Boolean);
    }

    function getPesoBrutoValue(operation) {
        return operation.peso_bruto || operation.peso_bruto_kg || operation.peso_bruto_total || '';
    }

    function summarizeProdutosForFilter(operation) {
        if (!operation || !Array.isArray(operation.produtos_processo) || !operation.produtos_processo.length) {
            return [];
        }

        return operation.produtos_processo
            .map(produto => {
                if (!produto || typeof produto !== 'object') {
                    return '';
                }

                const descricao = (produto.descricao || produto.descricao_produto || produto.descricao_adicao || '').toString().trim();
                const ncm = (produto.ncm || produto.ncm_sh || '').toString().trim();

                if (descricao) {
                    return descricao;
                }

                if (ncm) {
                    return `NCM ${ncm}`;
                }

                return '';
            })
            .filter(Boolean);
    }

    function summarizeDespesasForFilter(operation) {
        const totals = {};

        if (Array.isArray(operation?.despesas_processo)) {
            operation.despesas_processo.forEach(item => {
                if (!item) {
                    return;
                }

                const categoria = (item.categoria || item.tipo || '').toString().trim() || 'Outros';
                const valor = parseFloat(item.valor_total || item.valor || item.total);

                if (Number.isFinite(valor) && valor !== 0) {
                    totals[categoria] = (totals[categoria] || 0) + valor;
                }
            });
        }

        return Object.entries(totals)
            .filter(([, total]) => Number.isFinite(total) && total !== 0)
            .map(([categoria, total]) => {
                const formatter = typeof window.formatCurrency === 'function'
                    ? window.formatCurrency
                    : (value) => CURRENCY_FORMATTER.format(value);
                return `${categoria}: ${formatter(total)}`;
            });
    }

    function getArmazenagemFieldValue(operation, field) {
        const data = operation?.armazenagem_data;
        if (!data || typeof data !== 'object') {
            return '';
        }

        const value = data[field];

        if (value === null || value === undefined || value === '' || value === '-') {
            return '';
        }

        if (field === 'dias_extras_armazenagem') {
            const numeric = Number(value);
            if (!Number.isFinite(numeric) || numeric === 0) {
                return '';
            }
            return `${numeric} ${numeric === 1 ? 'dia' : 'dias'}`;
        }

        if (field === 'valor_despesas_extras') {
            const numeric = Number(value);
            if (!Number.isFinite(numeric) || numeric === 0) {
                return '';
            }
            const formatter = typeof window.formatCurrency === 'function'
                ? window.formatCurrency
                : (val) => CURRENCY_FORMATTER.format(val);
            return formatter(numeric);
        }

        return value;
    }
    
    /**
     * Fallback: coletar valores da tabela renderizada (método antigo)
     */
    function getUniqueValuesFromTable(columnIndex, columnName) {
        const table = document.getElementById('recent-operations-table');
        const tbody = table.querySelector('tbody');
        const rows = tbody.querySelectorAll('tr');
        
        const valueCounts = {};
        
        rows.forEach(row => {
            const cell = row.cells[columnIndex];
            if (!cell) return;
            
            let value;
            
            // LÓGICA ESPECIAL PARA MODAL: extrair do atributo title
            if (columnName === 'modal') {
                const modalBadge = cell.querySelector('.modal-icon-badge');
                if (modalBadge) {
                    value = modalBadge.getAttribute('title') || '';
                } else {
                    value = cell.textContent.trim();
                }
            } else {
                // Extrair texto do cell (ignorando HTML)
                value = cell.textContent.trim();
            }
            
            // Tratar valores vazios
            if (value === '' || value === '-') {
                value = '(Vazio)';
            }
            
            valueCounts[value] = (valueCounts[value] || 0) + 1;
        });
        
        // Converter para array e ordenar POR CONTAGEM (maior → menor)
        return Object.entries(valueCounts)
            .map(([value, count]) => ({ value, display: value, count }))
            .sort((a, b) => {
                // "(Vazio)" sempre por último
                if (a.value === '(Vazio)') return 1;
                if (b.value === '(Vazio)') return -1;
                
                // Ordenar por contagem (MAIOR para MENOR)
                if (b.count !== a.count) {
                    return b.count - a.count;
                }
                
                // Se contagem igual, ordenar alfabeticamente
                return a.display.localeCompare(b.display);
            });
    }
    
    /**
     * Aplicar todos os filtros ativos
     */
    function applyAllFilters() {
        const table = document.getElementById('recent-operations-table');
        const tbody = table.querySelector('tbody');
        const rows = tbody.querySelectorAll('tr');
        
        let visibleCount = 0;
        
        rows.forEach(row => {
            let shouldShow = true;
            
            // Verificar cada filtro ativo
            for (const [columnName, allowedValues] of Object.entries(activeFilters)) {
                const columnIndex = getColumnIndex(columnName);
                if (columnIndex === -1) continue;
                
                const cell = row.cells[columnIndex];
                if (!cell) {
                    shouldShow = false;
                    break;
                }
                
                // Extrair valor da célula (com lógica especial para modal)
                let cellValue = getCellValue(cell, columnName);
                
                if (cellValue === '' || cellValue === '-') {
                    cellValue = '(Vazio)';
                }
                
                if (!allowedValues.includes(cellValue)) {
                    shouldShow = false;
                    break;
                }
            }
            
            row.style.display = shouldShow ? '' : 'none';
            if (shouldShow) visibleCount++;
        });
        
        // Atualizar contador de registros
        updateRecordCount(visibleCount);
        
        console.log(`[COLUMN_FILTERS] Filtros aplicados. ${visibleCount} registros visíveis.`);
    }
    
    /**
     * Extrair valor de uma célula (com lógica especial para colunas com ícones)
     */
    function getCellValue(cell, columnName) {
        // LÓGICA ESPECIAL PARA MODAL: extrair do atributo title
        if (columnName === 'modal') {
            const modalBadge = cell.querySelector('.modal-icon-badge');
            if (modalBadge) {
                const titleValue = modalBadge.getAttribute('title') || '';
                // Normalizar para corresponder ao formato do filtro
                if (titleValue.includes('MARÍTIMA') || titleValue.includes('MARITIMA')) {
                    return 'MARÍTIMO';
                } else if (titleValue.includes('AÉREA') || titleValue.includes('AEREA')) {
                    return 'AÉREO';
                } else if (titleValue.includes('RODOVIÁRIA') || titleValue.includes('RODOVIARIA')) {
                    return 'RODOVIÁRIO';
                } else if (titleValue.includes('FERROVIÁRIA') || titleValue.includes('FERROVIARIA')) {
                    return 'FERROVIÁRIO';
                } else if (titleValue.includes('POSTAL') || titleValue.includes('CORREIO')) {
                    return 'POSTAL';
                } else if (titleValue.includes('COURIER') || titleValue.includes('EXPRESS')) {
                    return 'COURIER';
                }
                return titleValue;
            }
        }
        
        // Para outras colunas, extrair texto normalmente
        return cell.textContent.trim();
    }
    
    /**
     * Obter índice da coluna pelo nome
     */
    function getColumnIndex(columnName) {
        const table = document.getElementById('recent-operations-table');
        const headers = table.querySelectorAll('thead th');
        
        for (let i = 0; i < headers.length; i++) {
            if (headers[i].getAttribute('data-sort') === columnName) {
                return i;
            }
        }
        
        return -1;
    }
    
    /**
     * Atualizar ícone de filtro
     */
    function updateFilterIcon(columnName) {
        const icon = document.querySelector(`.column-filter-icon[data-column="${columnName}"]`);
        if (!icon) return;
        
        if (activeFilters[columnName] && activeFilters[columnName].length > 0) {
            icon.classList.add('active');
            icon.classList.remove('mdi-filter-outline');
            icon.classList.add('mdi-filter');
        } else {
            icon.classList.remove('active');
            icon.classList.remove('mdi-filter');
            icon.classList.add('mdi-filter-outline');
        }
    }
    
    /**
     * Criar badge de filtros ativos
     */
    function createActiveFiltersBadge() {
        if (document.querySelector('.active-filters-badge')) return;
        
        const badge = document.createElement('div');
        badge.className = 'active-filters-badge';
        badge.innerHTML = `
            <div class="active-filters-header">
                <div class="active-filters-title">
                    <i class="mdi mdi-filter"></i>
                    Filtros Ativos
                    <span class="active-filters-count">0</span>
                </div>
                <button class="clear-all-filters-btn">
                    <i class="mdi mdi-filter-remove"></i> Limpar Todos
                </button>
            </div>
            <div class="active-filters-list"></div>
        `;
        
        document.body.appendChild(badge);
        
        // Evento de limpar todos
        badge.querySelector('.clear-all-filters-btn').addEventListener('click', clearAllFilters);
    }
    
    /**
     * Atualizar badge de filtros ativos
     */
    function updateActiveFiltersBadge() {
        const badge = document.querySelector('.active-filters-badge');
        if (!badge) return;
        
        const filterCount = Object.keys(activeFilters).length;
        const countElement = badge.querySelector('.active-filters-count');
        const listElement = badge.querySelector('.active-filters-list');
        
        countElement.textContent = filterCount;
        
        if (filterCount === 0) {
            badge.classList.remove('show');
            return;
        }
        
        badge.classList.add('show');
        
        // Construir lista de filtros
        listElement.innerHTML = Object.entries(activeFilters).map(([columnName, values]) => {
            const columnLabel = getColumnLabel(columnName);
            return `
                <div class="active-filter-item">
                    <span class="active-filter-column">${columnLabel}:</span>
                    <span>${values.length} valor(es)</span>
                    <button class="active-filter-remove" data-column="${columnName}" title="Remover filtro">
                        <i class="mdi mdi-close"></i>
                    </button>
                </div>
            `;
        }).join('');
        
        // Eventos de remover filtro individual
        listElement.querySelectorAll('.active-filter-remove').forEach(btn => {
            btn.addEventListener('click', () => {
                const columnName = btn.getAttribute('data-column');
                delete activeFilters[columnName];
                applyAllFilters();
                updateFilterIcon(columnName);
                updateActiveFiltersBadge();
            });
        });
    }
    
    /**
     * Obter label da coluna
     */
    function getColumnLabel(columnName) {
        const table = document.getElementById('recent-operations-table');
        const headers = table.querySelectorAll('thead th');
        
        for (const header of headers) {
            if (header.getAttribute('data-sort') === columnName) {
                return header.querySelector('.column-header-text')?.textContent || columnName;
            }
        }
        
        return columnName;
    }
    
    /**
     * Limpar todos os filtros
     */
    function clearAllFilters() {
        Object.keys(activeFilters).forEach(columnName => {
            delete activeFilters[columnName];
            updateFilterIcon(columnName);
        });
        
        applyAllFilters();
        updateActiveFiltersBadge();
        closeAllDropdowns();
    }
    
    /**
     * Exportar função de limpeza
     */
    window.clearColumnFilters = clearAllFilters;
    
    /**
     * Fechar todos os dropdowns
     */
    function closeAllDropdowns() {
        document.querySelectorAll('.column-filter-dropdown').forEach(dropdown => {
            dropdown.remove();
        });
    }
    
    /**
     * Atualizar contador de registros
     */
    function updateRecordCount(visibleCount) {
        const paginationInfo = document.querySelector('.pagination-info');
        if (!paginationInfo) return;
        
        const totalCount = document.querySelectorAll('#recent-operations-table tbody tr').length;
        
        if (visibleCount === totalCount) {
            paginationInfo.textContent = `Mostrando 1 - ${Math.min(15, totalCount)} de ${totalCount} registros`;
        } else {
            paginationInfo.textContent = `Mostrando ${visibleCount} de ${totalCount} registros (filtrado)`;
        }
    }
    
    /**
     * Escape HTML
     */
    function escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, m => map[m]);
    }
    
    /**
     * Adicionar ícone ao display (para coluna modal)
     */
    function getDisplayWithIcon(value, columnName) {
        // Adicionar ícones para a coluna modal
        if (columnName === 'modal') {
            const modalIcons = {
                'MARÍTIMO': '<i class="mdi mdi-ferry" style="margin-right: 6px; color: #007bff;"></i>',
                'AÉREO': '<i class="mdi mdi-airplane" style="margin-right: 6px; color: #28a745;"></i>',
                'RODOVIÁRIO': '<i class="mdi mdi-truck" style="margin-right: 6px; color: #ffc107;"></i>',
                'FERROVIÁRIO': '<i class="mdi mdi-train" style="margin-right: 6px; color: #6c757d;"></i>',
                'POSTAL': '<i class="mdi mdi-email" style="margin-right: 6px; color: #17a2b8;"></i>',
                'COURIER': '<i class="mdi mdi-package-variant" style="margin-right: 6px; color: #e83e8c;"></i>'
            };
            
            const icon = modalIcons[value] || '';
            return `${icon}${escapeHtml(value)}`;
        }
        
        // Para outras colunas, retornar texto normal
        return escapeHtml(value);
    }
    
    console.log('[COLUMN_FILTERS] Módulo carregado');
})();
