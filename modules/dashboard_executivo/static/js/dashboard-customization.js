/**
 * Dashboard Customization System
 * Permite ao usuário personalizar o layout do dashboard através de drag and drop
 * 
 * FUNCIONALIDADES:
 * - Modo de edição com botão toggle
 * - Drag and drop de componentes
 * - Persistência no localStorage
 * - Visual feedback durante o drag
 * - Restauração do layout personalizado
 */

(function() {
    'use strict';
    
    // Configuração do sistema de customização
    const CUSTOMIZATION_CONFIG = {
        localStorageKey: 'dashboard_executivo_layout',
        dragClass: 'dashboard-dragging',
        editModeClass: 'dashboard-edit-mode',
        dragOverClass: 'dashboard-drag-over',
        dragPlaceholderClass: 'dashboard-drag-placeholder'
    };
    
    // Estado do sistema
    let isEditMode = false;
    let draggedElement = null;
    let dragPlaceholder = null;
    
    // Seletores dos containers customizáveis
    const CUSTOMIZABLE_CONTAINERS = [
        { selector: '.kpi-grid', type: 'kpi-grid', allowedChildren: ['.kpi-card'] },
        { selector: '.dashboard-line-1', type: 'charts-line-1', allowedChildren: ['.chart-section'] },
        { selector: '.dashboard-line-2', type: 'charts-line-2', allowedChildren: ['.chart-section'] },
        { selector: '#recent-operations-container', type: 'table-section', allowedChildren: [] } // Não permite mover a tabela por agora
    ];
    
    /**
     * Inicializar sistema de customização
     */
    function initCustomizationSystem() {
        console.log('[DASHBOARD_CUSTOMIZATION] Inicializando sistema de customização');
        
        // Criar botão de edição
        createEditButton();
        
        // Restaurar layout salvo
        restoreCustomLayout();
        
        // Setup event listeners
        setupEventListeners();
        
        console.log('[DASHBOARD_CUSTOMIZATION] Sistema inicializado');
    }
    
    /**
     * Criar botão "Edite seu Dashboard"
     */
    function createEditButton() {
        const actionsRight = document.querySelector('.actions-right');
        if (!actionsRight) {
            console.warn('[DASHBOARD_CUSTOMIZATION] .actions-right não encontrado');
            return;
        }
        
        const editButton = document.createElement('button');
        editButton.id = 'dashboard-edit-toggle';
        editButton.className = 'btn btn-outline-light';
        editButton.innerHTML = `
            <i class="mdi mdi-pencil" style="margin-right: 6px;"></i>
            <span id="edit-button-text">Edite seu Dashboard</span>
        `;
        editButton.title = 'Personalizar layout do dashboard';
        
        // Inserir antes dos outros botões
        actionsRight.insertBefore(editButton, actionsRight.firstChild);
        
        console.log('[DASHBOARD_CUSTOMIZATION] Botão de edição criado');
    }
    
    /**
     * Setup event listeners
     */
    function setupEventListeners() {
        // Event listener para botão de edição
        document.addEventListener('click', function(e) {
            if (e.target.closest('#dashboard-edit-toggle')) {
                toggleEditMode();
            }
        });
        
        // Prevenir drag padrão em imagens
        document.addEventListener('dragstart', function(e) {
            if (e.target.tagName === 'IMG') {
                e.preventDefault();
            }
        });
        
        console.log('[DASHBOARD_CUSTOMIZATION] Event listeners configurados');
    }
    
    /**
     * Alternar modo de edição
     */
    function toggleEditMode() {
        isEditMode = !isEditMode;
        
        const button = document.getElementById('dashboard-edit-toggle');
        const buttonText = document.getElementById('edit-button-text');
        const dashboardContainer = document.querySelector('.dashboard-container');
        
        if (isEditMode) {
            // Ativar modo de edição
            dashboardContainer.classList.add(CUSTOMIZATION_CONFIG.editModeClass);
            button.classList.remove('btn-outline-light');
            button.classList.add('btn-success');
            buttonText.textContent = 'Salvar Layout';
            button.querySelector('i').className = 'mdi mdi-content-save';
            
            enableDragAndDrop();
            showEditModeInstructions();
            
            console.log('[DASHBOARD_CUSTOMIZATION] Modo de edição ATIVADO');
        } else {
            // Desativar modo de edição
            dashboardContainer.classList.remove(CUSTOMIZATION_CONFIG.editModeClass);
            button.classList.remove('btn-success');
            button.classList.add('btn-outline-light');
            buttonText.textContent = 'Edite seu Dashboard';
            button.querySelector('i').className = 'mdi mdi-pencil';
            
            disableDragAndDrop();
            saveCustomLayout();
            hideEditModeInstructions();
            
            console.log('[DASHBOARD_CUSTOMIZATION] Modo de edição DESATIVADO - Layout salvo');
        }
    }
    
    /**
     * Mostrar instruções do modo de edição
     */
    function showEditModeInstructions() {
        // Remover instruções existentes
        const existingInstructions = document.querySelector('.edit-mode-instructions');
        if (existingInstructions) {
            existingInstructions.remove();
        }
        
        const instructionsDiv = document.createElement('div');
        instructionsDiv.className = 'edit-mode-instructions';
        instructionsDiv.innerHTML = `
            <div class="alert alert-info" style="margin: 0 0 20px 0; border-radius: 8px;">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <i class="mdi mdi-information" style="font-size: 20px;"></i>
                    <div>
                        <strong>Modo de Edição Ativado</strong>
                        <p style="margin: 4px 0 0 0; font-size: 14px;">
                            Arraste os componentes para reorganizá-los. Clique em "Salvar Layout" quando terminar.
                        </p>
                    </div>
                </div>
            </div>
        `;
        
        const dashboardContainer = document.querySelector('.dashboard-container');
        dashboardContainer.insertBefore(instructionsDiv, dashboardContainer.firstChild);
    }
    
    /**
     * Ocultar instruções do modo de edição
     */
    function hideEditModeInstructions() {
        const instructions = document.querySelector('.edit-mode-instructions');
        if (instructions) {
            instructions.remove();
        }
    }
    
    /**
     * Habilitar drag and drop
     */
    function enableDragAndDrop() {
        CUSTOMIZABLE_CONTAINERS.forEach(container => {
            const containerElement = document.querySelector(container.selector);
            if (!containerElement) return;
            
            // Configurar container como drop zone
            setupDropZone(containerElement, container);
            
            // Configurar elementos filhos como draggable
            container.allowedChildren.forEach(childSelector => {
                const children = containerElement.querySelectorAll(childSelector);
                children.forEach(child => {
                    setupDraggableElement(child);
                });
            });
        });
    }
    
    /**
     * Desabilitar drag and drop
     */
    function disableDragAndDrop() {
        // Remover draggable de todos os elementos
        const draggableElements = document.querySelectorAll('[draggable="true"]');
        draggableElements.forEach(element => {
            element.draggable = false;
            element.classList.remove(CUSTOMIZATION_CONFIG.dragClass);
        });
        
        // Limpar event listeners de drop zones
        CUSTOMIZABLE_CONTAINERS.forEach(container => {
            const containerElement = document.querySelector(container.selector);
            if (containerElement) {
                containerElement.classList.remove(CUSTOMIZATION_CONFIG.dragOverClass);
                // Note: não podemos remover event listeners específicos sem referência
                // mas o modo de edição controla se as ações são executadas
            }
        });
        
        // Limpar elementos temporários
        if (dragPlaceholder) {
            dragPlaceholder.remove();
            dragPlaceholder = null;
        }
        
        draggedElement = null;
    }
    
    /**
     * Configurar elemento como draggable
     */
    function setupDraggableElement(element) {
        element.draggable = true;
        element.classList.add('dashboard-draggable');
        
        element.addEventListener('dragstart', handleDragStart);
        element.addEventListener('dragend', handleDragEnd);
    }
    
    /**
     * Configurar container como drop zone
     */
    function setupDropZone(container, config) {
        container.classList.add('dashboard-drop-zone');
        container.addEventListener('dragover', handleDragOver);
        container.addEventListener('drop', (e) => handleDrop(e, config));
        container.addEventListener('dragenter', handleDragEnter);
        container.addEventListener('dragleave', handleDragLeave);
    }
    
    /**
     * Handle drag start
     */
    function handleDragStart(e) {
        if (!isEditMode) {
            e.preventDefault();
            return;
        }
        
        draggedElement = e.target;
        draggedElement.classList.add(CUSTOMIZATION_CONFIG.dragClass);
        
        // Criar placeholder
        dragPlaceholder = document.createElement('div');
        dragPlaceholder.className = `${CUSTOMIZATION_CONFIG.dragPlaceholderClass} ${draggedElement.className}`;
        dragPlaceholder.innerHTML = `
            <div style="display: flex; align-items: center; justify-content: center; height: 100%; opacity: 0.5; border: 2px dashed var(--unique-primary);">
                <span style="color: var(--unique-primary); font-weight: bold;">Solte aqui</span>
            </div>
        `;
        
        // Definir dados de transferência
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/html', draggedElement.outerHTML);
        
        console.log('[DASHBOARD_CUSTOMIZATION] Drag iniciado:', draggedElement.className);
    }
    
    /**
     * Handle drag end
     */
    function handleDragEnd(e) {
        if (!isEditMode) return;
        
        if (draggedElement) {
            draggedElement.classList.remove(CUSTOMIZATION_CONFIG.dragClass);
        }
        
        if (dragPlaceholder) {
            dragPlaceholder.remove();
            dragPlaceholder = null;
        }
        
        // Remover drag over classes
        document.querySelectorAll(`.${CUSTOMIZATION_CONFIG.dragOverClass}`).forEach(el => {
            el.classList.remove(CUSTOMIZATION_CONFIG.dragOverClass);
        });
        
        draggedElement = null;
        console.log('[DASHBOARD_CUSTOMIZATION] Drag finalizado');
    }
    
    /**
     * Handle drag over
     */
    function handleDragOver(e) {
        if (!isEditMode || !draggedElement) return;
        
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        
        const container = e.currentTarget;
        const afterElement = getDragAfterElement(container, e.clientY, e.clientX);
        
        if (dragPlaceholder) {
            if (afterElement == null) {
                container.appendChild(dragPlaceholder);
            } else {
                container.insertBefore(dragPlaceholder, afterElement);
            }
        }
    }
    
    /**
     * Handle drag enter
     */
    function handleDragEnter(e) {
        if (!isEditMode || !draggedElement) return;
        
        e.preventDefault();
        e.currentTarget.classList.add(CUSTOMIZATION_CONFIG.dragOverClass);
    }
    
    /**
     * Handle drag leave
     */
    function handleDragLeave(e) {
        if (!isEditMode || !draggedElement) return;
        
        // Verificar se realmente saiu do container (não apenas de um filho)
        if (!e.currentTarget.contains(e.relatedTarget)) {
            e.currentTarget.classList.remove(CUSTOMIZATION_CONFIG.dragOverClass);
        }
    }
    
    /**
     * Handle drop
     */
    function handleDrop(e, config) {
        if (!isEditMode || !draggedElement) return;
        
        e.preventDefault();
        e.currentTarget.classList.remove(CUSTOMIZATION_CONFIG.dragOverClass);
        
        const container = e.currentTarget;
        
        // Verificar se o elemento pode ser dropado neste container
        const isAllowed = config.allowedChildren.some(selector => {
            return draggedElement.matches(selector);
        });
        
        if (!isAllowed) {
            console.warn('[DASHBOARD_CUSTOMIZATION] Drop não permitido neste container');
            return;
        }
        
        // Mover elemento para nova posição
        const afterElement = getDragAfterElement(container, e.clientY, e.clientX);
        
        if (afterElement == null) {
            container.appendChild(draggedElement);
        } else {
            container.insertBefore(draggedElement, afterElement);
        }
        
        // Remover placeholder
        if (dragPlaceholder) {
            dragPlaceholder.remove();
            dragPlaceholder = null;
        }
        
        console.log('[DASHBOARD_CUSTOMIZATION] Elemento movido para:', container.className);
    }
    
    /**
     * Obter elemento após a posição do cursor
     */
    function getDragAfterElement(container, y, x) {
        const draggableElements = [...container.querySelectorAll('.dashboard-draggable:not(.dashboard-dragging)')];
        
        return draggableElements.reduce((closest, child) => {
            const box = child.getBoundingClientRect();
            const offset = y - box.top - box.height / 2;
            
            if (offset < 0 && offset > closest.offset) {
                return { offset: offset, element: child };
            } else {
                return closest;
            }
        }, { offset: Number.NEGATIVE_INFINITY }).element;
    }
    
    /**
     * Salvar layout customizado
     */
    function saveCustomLayout() {
        const layout = {};
        
        CUSTOMIZABLE_CONTAINERS.forEach(container => {
            const containerElement = document.querySelector(container.selector);
            if (!containerElement) return;
            
            const children = [];
            container.allowedChildren.forEach(childSelector => {
                const childElements = containerElement.querySelectorAll(childSelector);
                childElements.forEach((child, index) => {
                    // Criar identificador único baseado no conteúdo
                    const id = generateElementId(child);
                    children.push({
                        id: id,
                        originalIndex: index,
                        className: child.className,
                        dataAttributes: getDataAttributes(child)
                    });
                });
            });
            
            layout[container.type] = children;
        });
        
        localStorage.setItem(CUSTOMIZATION_CONFIG.localStorageKey, JSON.stringify(layout));
        
        // Mostrar confirmação
        showSuccessMessage('Layout personalizado salvo com sucesso!');
        
        console.log('[DASHBOARD_CUSTOMIZATION] Layout salvo:', layout);
    }
    
    /**
     * Restaurar layout customizado
     */
    function restoreCustomLayout() {
        try {
            const savedLayout = localStorage.getItem(CUSTOMIZATION_CONFIG.localStorageKey);
            if (!savedLayout) {
                console.log('[DASHBOARD_CUSTOMIZATION] Nenhum layout personalizado encontrado');
                return;
            }
            
            const layout = JSON.parse(savedLayout);
            
            CUSTOMIZABLE_CONTAINERS.forEach(container => {
                const containerElement = document.querySelector(container.selector);
                if (!containerElement || !layout[container.type]) return;
                
                const savedOrder = layout[container.type];
                const elements = [];
                
                // Coletar elementos atuais
                container.allowedChildren.forEach(childSelector => {
                    const children = [...containerElement.querySelectorAll(childSelector)];
                    elements.push(...children);
                });
                
                // Reordenar elementos conforme layout salvo
                const reorderedElements = [];
                savedOrder.forEach(savedElement => {
                    const matchingElement = elements.find(el => {
                        return generateElementId(el) === savedElement.id;
                    });
                    if (matchingElement) {
                        reorderedElements.push(matchingElement);
                    }
                });
                
                // Adicionar elementos que não estavam no layout salvo (novos)
                elements.forEach(el => {
                    if (!reorderedElements.includes(el)) {
                        reorderedElements.push(el);
                    }
                });
                
                // Reorganizar DOM
                reorderedElements.forEach(element => {
                    containerElement.appendChild(element);
                });
            });
            
            console.log('[DASHBOARD_CUSTOMIZATION] Layout restaurado:', layout);
            
        } catch (error) {
            console.error('[DASHBOARD_CUSTOMIZATION] Erro ao restaurar layout:', error);
            // Limpar dados corrompidos
            localStorage.removeItem(CUSTOMIZATION_CONFIG.localStorageKey);
        }
    }
    
    /**
     * Gerar ID único para elemento
     */
    function generateElementId(element) {
        // Usar data attributes se disponível
        if (element.dataset.kpiStatus) {
            return `kpi-${element.dataset.kpiStatus}`;
        }
        
        // Para gráficos, usar o título ou ID
        const title = element.querySelector('.chart-title');
        if (title) {
            return `chart-${title.textContent.toLowerCase().replace(/\s+/g, '-')}`;
        }
        
        // Para KPIs, usar classe específica ou conteúdo
        const kpiTitle = element.querySelector('.kpi-title');
        if (kpiTitle) {
            return `kpi-${kpiTitle.textContent.toLowerCase().replace(/\s+/g, '-')}`;
        }
        
        // Fallback: usar classes CSS
        return element.className.replace(/\s+/g, '-');
    }
    
    /**
     * Obter data attributes de elemento
     */
    function getDataAttributes(element) {
        const data = {};
        [...element.attributes].forEach(attr => {
            if (attr.name.startsWith('data-')) {
                data[attr.name] = attr.value;
            }
        });
        return data;
    }
    
    /**
     * Mostrar mensagem de sucesso
     */
    function showSuccessMessage(message) {
        // Usar sistema de mensagens existente se disponível
        if (window.showSuccess) {
            window.showSuccess(message);
            return;
        }
        
        // Fallback: criar mensagem temporária
        const messageDiv = document.createElement('div');
        messageDiv.className = 'alert alert-success';
        messageDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            padding: 12px 20px;
            border-radius: 8px;
            background-color: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        `;
        messageDiv.innerHTML = `
            <i class="mdi mdi-check-circle" style="margin-right: 8px;"></i>
            ${message}
        `;
        
        document.body.appendChild(messageDiv);
        
        setTimeout(() => {
            messageDiv.remove();
        }, 3000);
    }
    
    /**
     * Reset layout para padrão
     */
    function resetLayout() {
        localStorage.removeItem(CUSTOMIZATION_CONFIG.localStorageKey);
        location.reload();
    }
    
    // Expor funções públicas
    window.dashboardCustomization = {
        init: initCustomizationSystem,
        toggleEditMode: toggleEditMode,
        saveLayout: saveCustomLayout,
        restoreLayout: restoreCustomLayout,
        resetLayout: resetLayout,
        isEditMode: () => isEditMode
    };
    
    // Auto-inicializar quando DOM estiver pronto
    document.addEventListener('DOMContentLoaded', function() {
        // Aguardar um pouco para garantir que outros scripts foram carregados
        setTimeout(() => {
            initCustomizationSystem();
        }, 500);
    });
    
})();
