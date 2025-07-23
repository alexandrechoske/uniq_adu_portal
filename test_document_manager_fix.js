// Funções globais para serem adicionadas ao final do document-manager.js

// Função global para download que verifica se documentManager existe
function downloadDocument(documentId) {
    console.log('[GLOBAL] downloadDocument chamado para ID:', documentId);
    console.log('[GLOBAL] Verificando window.documentManager:', !!window.documentManager);
    
    if (!window.documentManager) {
        console.error('[GLOBAL] window.documentManager não está inicializado');
        alert('Sistema de documentos não está pronto. Tente novamente em alguns segundos.');
        return;
    }
    
    return window.documentManager.downloadDocument(documentId);
}

// Função global para editar documento
function editDocument(documentId) {
    console.log('[GLOBAL] editDocument chamado para ID:', documentId);
    
    if (!window.documentManager) {
        console.error('[GLOBAL] window.documentManager não está inicializado');
        alert('Sistema de documentos não está pronto. Tente novamente em alguns segundos.');
        return;
    }
    
    return window.documentManager.editDocument(documentId);
}

// Função global para deletar documento
function deleteDocument(documentId) {
    console.log('[GLOBAL] deleteDocument chamado para ID:', documentId);
    
    if (!window.documentManager) {
        console.error('[GLOBAL] window.documentManager não está inicializado');
        alert('Sistema de documentos não está pronto. Tente novamente em alguns segundos.');
        return;
    }
    
    return window.documentManager.deleteDocument(documentId);
}

// Função para inicializar gerenciador no modal
function initializeDocumentManager(processRefUnique) {
    console.log('[DOCUMENT_MANAGER] Inicializando para processo:', processRefUnique);
    window.documentManager = new DocumentManager(processRefUnique);
    return window.documentManager;
}
