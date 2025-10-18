(function () {
    const OVERLAY_SELECTOR = '.columns-config-modal-overlay';
    const DRAG_HANDLE_SELECTOR = '.column-item-handle';

    let draggedItem = null;

    function dependenciesReady() {
        if (!window.dashboardColumns) {
            console.warn('[COLUMNS_CONFIG] Dependências das colunas não disponíveis');
            return false;
        }
        return true;
    }

    function getOverlay() {
        return document.querySelector(OVERLAY_SELECTOR);
    }

    function openColumnsConfig() {
        if (!dependenciesReady()) {
            return;
        }

        const overlay = getOverlay();
        if (!overlay) {
            console.warn('[COLUMNS_CONFIG] Overlay não encontrado');
            return;
        }

        const currentConfig = window.dashboardColumns.getColumnConfig();
        window.dashboardColumns.setTempColumnConfig(currentConfig);

        renderColumnsList();
        overlay.classList.add('active');

        const searchInput = document.getElementById('columns-search');
        if (searchInput) {
            searchInput.value = '';
            searchInput.focus();
        }

        overlay.addEventListener('click', handleOverlayClick);
        document.addEventListener('keydown', handleEscClose);
    }

    function closeColumnsConfig() {
        const overlay = getOverlay();
        if (!overlay) {
            return;
        }

        overlay.classList.remove('active');
        overlay.removeEventListener('click', handleOverlayClick);
        document.removeEventListener('keydown', handleEscClose);
        window.dashboardColumns.clearTempColumnConfig();
    }

    function handleOverlayClick(event) {
        const modal = event.currentTarget.querySelector('.columns-config-modal');
        if (modal && !modal.contains(event.target)) {
            closeColumnsConfig();
        }
    }

    function handleEscClose(event) {
        if (event.key === 'Escape') {
            closeColumnsConfig();
        }
    }

    function renderColumnsList() {
        if (!dependenciesReady()) {
            return;
        }

        const container = document.getElementById('columns-list');
        if (!container) {
            return;
        }

        const available = window.dashboardColumns.getAvailableColumns();
        const configurableColumns = available.filter(column => column.showInConfig !== false);
        const config = window.dashboardColumns.getColumnConfig();
        const configMap = new Map(config.map(col => [col.id, col.visible]));
        const orderMap = new Map(config.map(col => [col.id, col.order]));

        const grouped = configurableColumns.reduce((acc, column) => {
            if (!acc[column.category]) {
                acc[column.category] = [];
            }
            acc[column.category].push({
                ...column,
                visible: configMap.has(column.id) ? configMap.get(column.id) : column.visible,
                order: orderMap.has(column.id) ? orderMap.get(column.id) : column.order
            });
            return acc;
        }, {});

        Object.values(grouped).forEach(columns => {
            columns.sort((a, b) => {
                const orderA = typeof a.order === 'number' ? a.order : 0;
                const orderB = typeof b.order === 'number' ? b.order : 0;
                return orderA - orderB;
            });
        });

        container.innerHTML = '';

        Object.entries(grouped).forEach(([category, columns]) => {
            const section = document.createElement('section');
            section.className = 'columns-category';

            const title = document.createElement('h4');
            title.className = 'columns-category-title';
            title.textContent = category;

            const body = document.createElement('div');
            body.className = 'columns-category-body';

            columns.forEach(column => {
                const item = document.createElement('label');
                item.className = `column-item${column.fixed ? ' fixed' : ''}`;
                item.dataset.columnId = column.id;

                const handle = document.createElement('span');
                handle.className = 'column-item-handle';
                handle.innerHTML = '<i class="mdi mdi-drag-vertical"></i>';
                handle.title = 'Arraste para reordenar';

                const input = document.createElement('input');
                input.type = 'checkbox';
                input.checked = Boolean(column.visible);
                input.disabled = Boolean(column.fixed);
                input.addEventListener('change', (event) => {
                    toggleColumn(column.id, event.target.checked);
                });

                const text = document.createElement('span');
                text.className = 'column-item-label';
                text.textContent = column.label;

                if (column.fixed) {
                    const lock = document.createElement('i');
                    lock.className = 'mdi mdi-lock';
                    text.appendChild(lock);
                }

                item.appendChild(handle);
                item.appendChild(input);
                item.appendChild(text);
                body.appendChild(item);
            });

            section.appendChild(title);
            section.appendChild(body);
            container.appendChild(section);
        });

        setupDragAndDrop(container);
    }

    function toggleColumn(columnId, isVisible) {
        const config = window.dashboardColumns.getColumnConfig();
        const column = config.find(col => col.id === columnId);
        if (column) {
            column.visible = isVisible;
            window.dashboardColumns.setTempColumnConfig(config);
        }
    }

    function selectAllColumns() {
        const available = window.dashboardColumns.getAvailableColumns();
        const nextConfig = available.map(column => ({
            id: column.id,
            visible: column.fixed ? true : true,
            order: column.order
        }));
        window.dashboardColumns.setTempColumnConfig(nextConfig);
        renderColumnsList();
    }

    function deselectAllColumns() {
        const available = window.dashboardColumns.getAvailableColumns();
        const nextConfig = available.map(column => ({
            id: column.id,
            visible: column.fixed ? true : false,
            order: column.order
        }));
        window.dashboardColumns.setTempColumnConfig(nextConfig);
        renderColumnsList();
    }

    function resetColumnsToDefault() {
        if (!confirm('Deseja restaurar as colunas padrão?')) {
            return;
        }
        window.dashboardColumns.resetColumnConfigToDefault();
        renderColumnsList();
        notify('Configuração padrão restaurada.');
    }

    function applyColumnsConfig() {
        const config = window.dashboardColumns.getColumnConfig();
        window.dashboardColumns.saveColumnConfig(config);
        closeColumnsConfig();

        if (Array.isArray(window.currentOperations) && window.currentOperations.length) {
            updateRecentOperationsTable(window.currentOperations);
        } else if (typeof refreshData === 'function') {
            refreshData();
        }

        notify('Configuração de colunas aplicada com sucesso.');
    }

    function filterColumns(term) {
        const searchTerm = term.trim().toLowerCase();
        const container = document.getElementById('columns-list');
        if (!container) {
            return;
        }

        container.querySelectorAll('.columns-category').forEach(section => {
            let visibleCount = 0;
            section.querySelectorAll('.column-item').forEach(item => {
                const label = item.querySelector('.column-item-label');
                const text = label ? label.textContent.toLowerCase() : '';
                const shouldShow = !searchTerm || text.includes(searchTerm);
                item.style.display = shouldShow ? 'flex' : 'none';
                if (shouldShow) {
                    visibleCount += 1;
                }
            });
            section.style.display = visibleCount ? 'block' : 'none';
        });
    }

    function setupDragAndDrop(container) {
        if (!container) {
            return;
        }

        const handles = container.querySelectorAll(DRAG_HANDLE_SELECTOR);
        handles.forEach(handle => {
            const item = handle.closest('.column-item');
            if (!item || item.classList.contains('fixed')) {
                handle.removeAttribute('draggable');
                return;
            }

            handle.setAttribute('draggable', 'true');
            handle.addEventListener('dragstart', handleDragStart);
            handle.addEventListener('dragend', handleDragEnd);
            handle.addEventListener('click', event => {
                event.preventDefault();
                event.stopPropagation();
            });
        });

        const bodies = container.querySelectorAll('.columns-category-body');
        bodies.forEach(body => {
            body.addEventListener('dragover', handleDragOver);
            body.addEventListener('drop', handleDrop);
            body.addEventListener('dragleave', handleDragLeave);
        });
    }

    function handleDragStart(event) {
        const item = event.currentTarget.closest('.column-item');
        if (!item || item.classList.contains('fixed')) {
            return;
        }

        draggedItem = item;
        item.classList.add('dragging');
        event.dataTransfer.effectAllowed = 'move';
        event.dataTransfer.setData('text/plain', item.dataset.columnId || '');

        if (event.dataTransfer.setDragImage) {
            const rect = item.getBoundingClientRect();
            event.dataTransfer.setDragImage(item, rect.width / 2, rect.height / 2);
        }
    }

    function handleDragEnd() {
        if (draggedItem) {
            draggedItem.classList.remove('dragging');
            draggedItem = null;
        }

        document.querySelectorAll('.columns-category-body').forEach(body => {
            body.classList.remove('drag-over');
        });

        updateOrderFromDOM();
    }

    function handleDragOver(event) {
        if (!draggedItem) {
            return;
        }

        event.preventDefault();
        const body = event.currentTarget;
        body.classList.add('drag-over');

        const afterElement = getDragAfterElement(body, event.clientY);
        if (!afterElement) {
            body.appendChild(draggedItem);
        } else if (afterElement !== draggedItem) {
            body.insertBefore(draggedItem, afterElement);
        }
    }

    function handleDrop(event) {
        if (!draggedItem) {
            return;
        }

        event.preventDefault();
        event.currentTarget.classList.remove('drag-over');
        updateOrderFromDOM();
    }

    function handleDragLeave(event) {
        if (!event.currentTarget.contains(event.relatedTarget)) {
            event.currentTarget.classList.remove('drag-over');
        }
    }

    function getDragAfterElement(container, y) {
        const items = [...container.querySelectorAll('.column-item:not(.dragging)')];

        return items.reduce((closest, child) => {
            const box = child.getBoundingClientRect();
            const offset = y - box.top - box.height / 2;

            if (offset < 0 && offset > closest.offset) {
                return { offset, element: child };
            }

            return closest;
        }, { offset: Number.NEGATIVE_INFINITY, element: null }).element;
    }

    function updateOrderFromDOM() {
        if (!dependenciesReady()) {
            return;
        }

        const currentConfig = window.dashboardColumns.getColumnConfig();
        const orderMap = new Map();
        let orderIndex = 1;

        document.querySelectorAll('#columns-list .column-item').forEach(item => {
            const columnId = item.dataset.columnId;
            if (columnId) {
                orderMap.set(columnId, orderIndex++);
            }
        });

        const nextConfig = currentConfig.map(column => ({
            ...column,
            order: orderMap.has(column.id) ? orderMap.get(column.id) : column.order
        }));

        window.dashboardColumns.setTempColumnConfig(nextConfig);
    }

    function notify(message) {
        if (typeof showSuccess === 'function') {
            showSuccess(message);
            return;
        }

        const toast = document.createElement('div');
        toast.textContent = message;
        toast.style.cssText = 'position:fixed;top:20px;right:20px;background:#2563eb;color:#fff;padding:12px 16px;border-radius:8px;box-shadow:0 10px 28px rgba(37,99,235,0.25);z-index:1200;font-size:0.9rem;';
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 2500);
    }

    function bindStaticEvents() {
        const overlay = getOverlay();
        if (!overlay) {
            return;
        }

        const closeButton = overlay.querySelector('.columns-config-close');
        if (closeButton) {
            closeButton.addEventListener('click', closeColumnsConfig);
        }

        const searchInput = document.getElementById('columns-search');
        if (searchInput) {
            searchInput.addEventListener('input', (event) => {
                filterColumns(event.target.value);
            });
        }

        const selectAllBtn = document.getElementById('columns-select-all');
        if (selectAllBtn) {
            selectAllBtn.addEventListener('click', selectAllColumns);
        }

        const deselectAllBtn = document.getElementById('columns-deselect-all');
        if (deselectAllBtn) {
            deselectAllBtn.addEventListener('click', deselectAllColumns);
        }

        const resetBtn = document.getElementById('columns-reset-default');
        if (resetBtn) {
            resetBtn.addEventListener('click', resetColumnsToDefault);
        }

        const applyBtn = document.getElementById('columns-apply');
        if (applyBtn) {
            applyBtn.addEventListener('click', applyColumnsConfig);
        }

        const cancelBtn = document.getElementById('columns-cancel');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', closeColumnsConfig);
        }

        const triggerBtn = document.getElementById('open-columns-config');
        if (triggerBtn) {
            triggerBtn.addEventListener('click', (event) => {
                event.preventDefault();
                openColumnsConfig();
            });
        }
    }

    document.addEventListener('DOMContentLoaded', () => {
        bindStaticEvents();
    });

    window.openColumnsConfig = openColumnsConfig;
    window.closeColumnsConfig = closeColumnsConfig;
    window.applyColumnsConfig = applyColumnsConfig;
    window.resetColumnsToDefault = resetColumnsToDefault;
    window.selectAllColumns = selectAllColumns;
    window.deselectAllColumns = deselectAllColumns;
})();
