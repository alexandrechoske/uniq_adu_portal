/**
 * Process Modal - Shared Module
 * Modal reutilizável para exibir detalhes de processos
 */

/**
 * Open process details modal
 * @param {number} operationIndex - Index da operação no array global
 */
function openProcessModal(operationIndex) {
    console.log('[PROCESS_MODAL] Abrindo modal para processo:', operationIndex);
    
    if (!window.currentOperations || !window.currentOperations[operationIndex]) {
        console.error('[PROCESS_MODAL] Operação não encontrada:', operationIndex);
        console.error('[PROCESS_MODAL] window.currentOperations:', window.currentOperations ? window.currentOperations.length : 'undefined');
        return;
    }
    
    const operation = window.currentOperations[operationIndex];
    console.log('[PROCESS_MODAL] Dados da operação completos:', operation);
    console.log('[PROCESS_MODAL] ref_unique do processo:', operation.ref_unique);
    
    // Debug específico dos campos problemáticos
    console.log('[MODAL_DEBUG] ref_importador:', operation.ref_importador);
    console.log('[MODAL_DEBUG] cnpj_importador:', operation.cnpj_importador);
    console.log('[MODAL_DEBUG] status_macro:', operation.status_macro);
    console.log('[MODAL_DEBUG] data_embarque:', operation.data_embarque);
    console.log('[MODAL_DEBUG] peso_bruto:', operation.peso_bruto);
    console.log('[MODAL_DEBUG] urf_despacho:', operation.urf_despacho);
    console.log('[MODAL_DEBUG] urf_despacho_normalizado:', operation.urf_despacho_normalizado);
    
    // Update modal title
    const modalTitle = document.getElementById('modal-title');
    if (modalTitle) {
        modalTitle.textContent = `Detalhes do Processo ${operation.ref_unique || 'N/A'}`;
        console.log('[PROCESS_MODAL] Título do modal atualizado para:', operation.ref_unique);
    }
    
    // Update timeline - extract numeric value from status_timeline like "2 - Agd Chegada"
    const statusTimelineNumber = extractTimelineNumber(operation.status_timeline);
    console.log('[MODAL_DEBUG] Status timeline extraído:', statusTimelineNumber);
    console.log('[MODAL_DEBUG] operation.status_timeline:', operation.status_timeline);
    console.log('[MODAL_DEBUG] operation.status_processo:', operation.status_processo);
    console.log('[MODAL_DEBUG] operation.status_macro_sistema:', operation.status_macro_sistema);
    updateProcessTimeline(statusTimelineNumber);
    
    // Update general information
    updateElementValue('detail-ref-unique', operation.ref_unique);
    updateElementValue('detail-ref-importador', operation.ref_importador);
    updateElementValue('detail-data-abertura', operation.data_abertura);
    updateElementValue('detail-importador', operation.importador);
    updateElementValue('detail-cnpj', formatCNPJ(operation.cnpj_importador));
    
    // CORREÇÃO: Usar status_timeline, mas ignorar "N/A" e usar fallback
    let statusDisplay = operation.status_timeline;
    
    console.log('[MODAL_DEBUG] ========================================');
    console.log('[MODAL_DEBUG] INÍCIO DO PROCESSAMENTO DE STATUS');
    console.log('[MODAL_DEBUG] status_timeline original:', operation.status_timeline);
    console.log('[MODAL_DEBUG] typeof status_timeline:', typeof operation.status_timeline);
    
    // Se for N/A, null, undefined ou vazio, tentar fallbacks
    if (!statusDisplay || statusDisplay.toUpperCase() === 'N/A' || statusDisplay.trim() === '') {
        console.log('[MODAL_DEBUG] Status timeline é inválido, usando fallback...');
        statusDisplay = operation.status_macro_sistema || operation.status_processo || 'Sem Informação';
        console.log('[MODAL_DEBUG] Status após fallback:', statusDisplay);
    } else {
        console.log('[MODAL_DEBUG] Status timeline é VÁLIDO:', statusDisplay);
    }
    
    console.log('[MODAL_DEBUG] Status display FINAL:', statusDisplay);
    console.log('[MODAL_DEBUG] ========================================');
    
    // Forçar atualização do elemento
    const statusElement = document.getElementById('detail-status');
    if (statusElement) {
        statusElement.textContent = statusDisplay;
        console.log('[MODAL_DEBUG] ✅ Elemento detail-status atualizado diretamente!');
        console.log('[MODAL_DEBUG] Valor no DOM após atualização:', statusElement.textContent);
    } else {
        console.error('[MODAL_DEBUG] ❌ Elemento detail-status NÃO ENCONTRADO!');
    }
    
    // Também usar a função helper
    updateElementValue('detail-status', statusDisplay);
    
    // Update cargo and transport details
    updateElementValue('detail-modal', operation.modal);
    updateElementValue('detail-container', operation.container);
    updateElementValue('detail-data-embarque', operation.data_embarque);
    updateElementValue('detail-data-chegada', operation.data_chegada);
    updateElementValue('detail-data-fechamento', operation.data_fechamento);
    updateElementValue('detail-transit-time', operation.transit_time_real ? operation.transit_time_real + ' dias' : '-');
    
    // FIX: Normalize peso_bruto if value seems incorrectly scaled
    const pesoNormalized = normalizePesoBruto(operation.peso_bruto);
    updateElementValue('detail-peso-bruto', pesoNormalized ? formatNumber(pesoNormalized) + ' Kg' : '-');
    
    // Update customs information
    updateElementValue('detail-numero-di', operation.numero_di);
    updateElementValue('detail-data-registro', operation.data_registro);
    updateElementValue('detail-canal', operation.canal);
    updateElementValue('detail-data-desembaraco', operation.data_desembaraco);
    updateElementValue('detail-urf-despacho', operation.urf_despacho_normalizado || operation.urf_despacho);
    
    // Update financial summary
    updateElementValue('detail-valor-cif', formatCurrency(operation.valor_cif_real || 0));
    updateElementValue('detail-frete-inter', formatCurrency(operation.custo_frete_inter || 0));
    updateElementValue('detail-armazenagem', formatCurrency(operation.custo_armazenagem || 0));
    updateElementValue('detail-honorarios', formatCurrency(operation.custo_honorarios || 0));
    
    // Calculate other expenses
    const otherExpenses = calculateOtherExpenses(operation);
    updateElementValue('detail-outras-despesas', formatCurrency(otherExpenses));
    updateElementValue('detail-custo-total', formatCurrency(operation.custo_total || 0));
    
    // Update documents (placeholder for now)
    updateDocumentsList(operation);
    
    // Show modal
    const modal = document.getElementById('process-modal');
    if (modal) {
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
}

/**
 * Close process details modal
 */
function closeProcessModal() {
    console.log('[PROCESS_MODAL] Fechando modal');
    
    const modal = document.getElementById('process-modal');
    if (modal) {
        modal.classList.remove('active');
        document.body.style.overflow = '';
    }
}

/**
 * Extract numeric value from status_timeline like "2 - Agd Embarque"
 */
function extractTimelineNumber(statusTimeline) {
    if (!statusTimeline) return 1; // Default para Abertura
    
    try {
        const status_str = String(statusTimeline).trim().toUpperCase();
        
        // Ignorar N/A
        if (status_str === 'N/A') return 1;
        
        // Extract the first number from strings like "2 - Agd Embarque"
        if (/^[1-9]/.test(status_str)) {
            return parseInt(status_str.split(' ')[0].replace('-', '').trim());
        }
        return 1;
    } catch {
        return 1;
    }
}

/**
 * Extract numeric value from status_macro like "5 - AG REGISTRO" (LEGACY - mantido para compatibilidade)
 */
function extractStatusMacroNumber(statusMacro) {
    if (!statusMacro) return 1;
    
    // Extract the first number from strings like "5 - AG REGISTRO"
    const match = statusMacro.toString().match(/^(\d+)/);
    return match ? parseInt(match[1]) : 1;
}

/**
 * Format CNPJ for display
 */
function formatCNPJ(cnpj) {
    if (!cnpj) return '-';
    
    // Remove non-digits
    const cleanCNPJ = cnpj.replace(/\D/g, '');
    
    // Format as XX.XXX.XXX/XXXX-XX
    if (cleanCNPJ.length === 14) {
        return cleanCNPJ.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, '$1.$2.$3/$4-$5');
    }
    
    return cnpj;
}

/**
 * Update process timeline based on status_timeline
 * REGRA NOVA: 6 etapas
 * - 1: Abertura (sempre azul)
 * - 2: Agd Embarque (azul quando status = 2)
 * - 3: Agd Chegada (azul quando status = 3)
 * - 4: Agd Registro (azul quando status = 4)
 * - 5: Desembaraçado (azul quando status = 5)
 * - 6: Finalizado (TODAS as bolinhas ficam VERDES quando status = 6)
 */
function updateProcessTimeline(statusNumber) {
    console.log('[TIMELINE_DEBUG] Atualizando timeline com status:', statusNumber);
    
    const timelineSteps = document.querySelectorAll('.timeline-step');
    console.log('[TIMELINE_DEBUG] Steps encontrados:', timelineSteps.length);
    
    // REGRA ESPECIAL: Se status = 6 (Finalizado), todas as bolinhas ficam verdes
    if (statusNumber === 6) {
        console.log('[TIMELINE_DEBUG] Status 6 - FINALIZADO! Todas as etapas ficam verdes (completed)');
        timelineSteps.forEach((step, index) => {
            step.classList.remove('active');
            step.classList.add('completed');
            console.log(`[TIMELINE_DEBUG] Step ${index + 1} marcado como completed (verde)`);
        });
        return; // Sai da função
    }
    
    // REGRA NORMAL: Etapas progridem de acordo com o status
    timelineSteps.forEach((step, index) => {
        const stepNumber = index + 1;
        step.classList.remove('completed', 'active');
        
        console.log(`[TIMELINE_DEBUG] Step ${stepNumber}: status=${statusNumber}`);
        
        // Etapa 1 (Abertura) sempre está azul (active ou completed)
        if (stepNumber === 1) {
            if (statusNumber === 1) {
                step.classList.add('active');
                console.log(`[TIMELINE_DEBUG] Step 1 (Abertura) marcado como active (azul)`);
            } else {
                step.classList.add('completed');
                console.log(`[TIMELINE_DEBUG] Step 1 (Abertura) marcado como completed (azul)`);
            }
        }
        // Etapas 2-5: Azul se for o status atual, completed se já passou
        else if (stepNumber > 1 && stepNumber <= 5) {
            if (stepNumber < statusNumber) {
                step.classList.add('completed');
                console.log(`[TIMELINE_DEBUG] Step ${stepNumber} marcado como completed (azul - passou)`);
            } else if (stepNumber === statusNumber) {
                step.classList.add('active');
                console.log(`[TIMELINE_DEBUG] Step ${stepNumber} marcado como active (azul - atual)`);
            }
            // Senão, fica cinza (sem classe)
        }
    });
}

/**
 * Update element value safely
 */
function updateElementValue(elementId, value) {
    const element = document.getElementById(elementId);
    if (element) {
        const displayValue = value || '-';
        element.textContent = displayValue;
        console.log(`[MODAL_DEBUG] Elemento ${elementId} atualizado com: "${displayValue}"`);
    } else {
        console.warn(`[MODAL_DEBUG] Elemento ${elementId} não encontrado no DOM`);
    }
}

/**
 * Calculate other expenses
 */
function calculateOtherExpenses(operation) {
    const expenseFields = [
        'custo_ii', 'custo_ipi', 'custo_pis', 'custo_cofins', 'custo_icms',
        'custo_afrmm', 'custo_seguro', 'custo_adicional_frete', 'custo_taxa_siscomex',
        'custo_licenca_importacao', 'custo_taxa_utilizacao_siscomex', 'custo_multa',
        'custo_juros_mora', 'custo_outros'
    ];
    
    let total = 0;
    expenseFields.forEach(field => {
        const value = operation[field];
        if (value && !isNaN(value)) {
            total += Number(value);
        }
    });
    
    return total;
}

/**
 * Update documents list - Now integrated with Document Manager
 */
function updateDocumentsList(operation) {
    console.log('[PROCESS_MODAL] Inicializando seção de documentos para:', operation.ref_unique);
    
    // Initialize document manager for this process
    if (typeof initializeDocumentManager === 'function') {
        initializeDocumentManager(operation.ref_unique);
    } else {
        console.warn('[PROCESS_MODAL] Document Manager não disponível');
        
        // Fallback: show placeholder
        const documentsList = document.getElementById('documents-list');
        if (documentsList) {
            documentsList.innerHTML = `
                <div class="no-documents">
                    <i class="mdi mdi-file-document-outline"></i>
                    <p>Sistema de documentos não carregado</p>
                    <p class="text-muted">Verifique se o script document-manager.js foi incluído</p>
                </div>
            `;
        }
    }
}

/**
 * Normalize peso_bruto value if it seems to be incorrectly scaled
 * FIX: Database stores peso_bruto with wrong scale (multiplied by 100)
 * Example: User enters 17905 but DB stores 1790512
 * @param {number} peso - The peso_bruto value from database
 * @returns {number} - Normalized peso value
 */
function normalizePesoBruto(peso) {
    if (!peso || isNaN(peso)) return 0;
    
    const pesoNum = Number(peso);
    
    // If peso is > 100,000 kg (100 tons), it's probably scaled wrong
    // Divide by 100 to get the correct value
    // Example: 1790512 -> 17905.12 kg
    if (pesoNum > 100000) {
        console.log(`[PESO_FIX] Detected wrong scale: ${pesoNum} -> ${pesoNum / 100}`);
        return pesoNum / 100;
    }
    
    return pesoNum;
}

/**
 * Format number with thousands separator
 */
function formatNumber(value) {
    if (!value || isNaN(value)) return '0';
    return Number(value).toLocaleString('pt-BR');
}

/**
 * Format currency in Brazilian Real
 */
function formatCurrency(value) {
    if (!value || isNaN(value)) return 'R$ 0,00';
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(value);
}

/**
 * Initialize modal event listeners
 */
function initProcessModal() {
    console.log('[PROCESS_MODAL] Inicializando event listeners do modal');
    
    // Close modal event listeners
    const modalCloseBtn = document.getElementById('modal-close');
    const modalOverlay = document.getElementById('process-modal');
    
    if (modalCloseBtn) {
        modalCloseBtn.addEventListener('click', closeProcessModal);
    }
    
    if (modalOverlay) {
        modalOverlay.addEventListener('click', function(e) {
            if (e.target === modalOverlay) {
                closeProcessModal();
            }
        });
    }
    
    // ESC key to close modal
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeProcessModal();
        }
    });
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    initProcessModal();
});
