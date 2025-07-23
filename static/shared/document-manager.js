/**
 * Document Manager - JavaScript Module
 * Gerenciamento de documentos nos modals de processo
 */

class DocumentManager {
    constructor(processRefUnique) {
        this.processRefUnique = processRefUnique;
        this.documents = [];
        this.userRole = null;
        this.init();
    }

    init() {
        console.log('[DOCUMENT_MANAGER] Inicializando para processo:', this.processRefUnique);
        this.getUserRole();
        this.loadDocuments();
        this.setupEventListeners();
    }

    getUserRole() {
        // Assumindo que role está disponível globalmente
        this.userRole = window.userRole || 'cliente_unique';
        console.log('[DOCUMENT_MANAGER] Role do usuário:', this.userRole);
    }

    setupEventListeners() {
        // Botão de upload (apenas para admin/interno)
        const uploadBtn = document.getElementById('upload-document-btn');
        if (uploadBtn && ['admin', 'interno_unique'].includes(this.userRole)) {
            uploadBtn.addEventListener('click', () => this.showUploadModal());
        }

        // Form de upload
        const uploadForm = document.getElementById('document-upload-form');
        if (uploadForm) {
            uploadForm.addEventListener('submit', (e) => this.handleUpload(e));
        }

        // Fechar modal de upload
        const closeUploadBtn = document.getElementById('close-upload-modal');
        if (closeUploadBtn) {
            closeUploadBtn.addEventListener('click', () => this.hideUploadModal());
        }

        // Preview de arquivo
        const fileInput = document.getElementById('document-file');
        if (fileInput) {
            fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
        }
    }

    async loadDocuments() {
        try {
            console.log('[DOCUMENT_MANAGER] Carregando documentos...');
            
            const response = await fetch(`/api/documents/process/${this.processRefUnique}`);
            const result = await response.json();

            if (result.success) {
                this.documents = result.data;
                this.renderDocuments();
                console.log('[DOCUMENT_MANAGER] Documentos carregados:', this.documents.length);
            } else {
                console.error('[DOCUMENT_MANAGER] Erro ao carregar documentos:', result.error);
                this.showError('Erro ao carregar documentos: ' + result.error);
            }
        } catch (error) {
            console.error('[DOCUMENT_MANAGER] Erro de rede:', error);
            this.showError('Erro de conexão ao carregar documentos');
        }
    }

    renderDocuments() {
        const container = document.getElementById('documents-list');
        if (!container) {
            console.warn('[DOCUMENT_MANAGER] Container documents-list não encontrado');
            return;
        }

        if (this.documents.length === 0) {
            container.innerHTML = `
                <div class="no-documents">
                    <i class="mdi mdi-file-document-outline"></i>
                    <p>Nenhum documento anexado</p>
                    ${this.canUpload() ? '<p class="text-muted">Use o botão "Anexar Documento" para adicionar arquivos</p>' : ''}
                </div>
            `;
            return;
        }

        const documentsHtml = this.documents.map(doc => this.renderDocumentItem(doc)).join('');
        container.innerHTML = `
            <div class="documents-grid">
                ${documentsHtml}
            </div>
        `;
    }

    renderDocumentItem(doc) {
        const canEdit = ['admin', 'interno_unique'].includes(this.userRole);
        const uploadDate = new Date(doc.data_upload).toLocaleDateString('pt-BR');
        
        return `
            <div class="document-item" data-doc-id="${doc.id}">
                <div class="document-icon">
                    <i class="mdi ${this.getFileIcon(doc.extensao)}"></i>
                </div>
                <div class="document-info">
                    <div class="document-name" title="${doc.nome_original}">
                        ${doc.nome_exibicao}
                    </div>
                    <div class="document-meta">
                        <span class="document-size">${doc.tamanho_formatado}</span>
                        <span class="document-date">${uploadDate}</span>
                    </div>
                    ${doc.descricao ? `<div class="document-description">${doc.descricao}</div>` : ''}
                    <div class="document-uploader">
                        Enviado por: ${doc.usuario_upload_email}
                    </div>
                </div>
                <div class="document-actions">
                    <button class="btn-icon download-btn" onclick="documentManager.downloadDocument('${doc.id}')" title="Download">
                        <i class="mdi mdi-download"></i>
                    </button>
                    ${canEdit ? `
                        <button class="btn-icon edit-btn" onclick="documentManager.editDocument('${doc.id}')" title="Editar">
                            <i class="mdi mdi-pencil"></i>
                        </button>
                        ${this.userRole === 'admin' ? `
                            <button class="btn-icon delete-btn" onclick="documentManager.deleteDocument('${doc.id}')" title="Remover">
                                <i class="mdi mdi-delete"></i>
                            </button>
                        ` : ''}
                    ` : ''}
                </div>
                ${!doc.visivel_cliente && canEdit ? '<div class="document-badge">Oculto do cliente</div>' : ''}
            </div>
        `;
    }

    getFileIcon(extension) {
        const iconMap = {
            'pdf': 'mdi-file-pdf-box',
            'jpg': 'mdi-file-image',
            'jpeg': 'mdi-file-image',
            'png': 'mdi-file-image',
            'gif': 'mdi-file-image',
            'webp': 'mdi-file-image',
            'xlsx': 'mdi-file-excel',
            'xls': 'mdi-file-excel',
            'docx': 'mdi-file-word',
            'doc': 'mdi-file-word',
            'txt': 'mdi-file-document',
            'csv': 'mdi-file-delimited',
            'zip': 'mdi-folder-zip'
        };
        return iconMap[extension] || 'mdi-file-document-outline';
    }

    canUpload() {
        return ['admin', 'interno_unique'].includes(this.userRole);
    }

    showUploadModal() {
        const modal = document.getElementById('document-upload-modal');
        if (modal) {
            modal.classList.add('active');
            document.body.style.overflow = 'hidden';
            
            // Limpar form
            const form = document.getElementById('document-upload-form');
            if (form) form.reset();
            
            // Limpar preview
            this.clearFilePreview();
        }
    }

    hideUploadModal() {
        const modal = document.getElementById('document-upload-modal');
        if (modal) {
            modal.classList.remove('active');
            document.body.style.overflow = '';
        }
    }

    handleFileSelect(event) {
        const file = event.target.files[0];
        if (file) {
            this.showFilePreview(file);
            
            // Auto-preencher nome de exibição se vazio
            const displayNameInput = document.getElementById('document-display-name');
            if (displayNameInput && !displayNameInput.value) {
                displayNameInput.value = file.name;
            }
        } else {
            this.clearFilePreview();
        }
    }

    showFilePreview(file) {
        const preview = document.getElementById('file-preview');
        if (!preview) return;

        const sizeFormatted = this.formatFileSize(file.size);
        
        preview.innerHTML = `
            <div class="file-preview-item">
                <i class="mdi ${this.getFileIcon(file.name.split('.').pop())}"></i>
                <div class="file-info">
                    <div class="file-name">${file.name}</div>
                    <div class="file-size">${sizeFormatted}</div>
                </div>
            </div>
        `;
        preview.style.display = 'block';
    }

    clearFilePreview() {
        const preview = document.getElementById('file-preview');
        if (preview) {
            preview.innerHTML = '';
            preview.style.display = 'none';
        }
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    async handleUpload(event) {
        event.preventDefault();
        
        const form = event.target;
        const formData = new FormData(form);
        
        // Adicionar ref_unique
        formData.append('ref_unique', this.processRefUnique);
        
        try {
            this.showUploadProgress(true);
            
            const response = await fetch('/api/documents/upload', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showSuccess('Documento enviado com sucesso!');
                this.hideUploadModal();
                await this.loadDocuments(); // Recarregar lista
            } else {
                this.showError('Erro no upload: ' + result.error);
            }
        } catch (error) {
            console.error('[DOCUMENT_MANAGER] Erro no upload:', error);
            this.showError('Erro de conexão durante o upload');
        } finally {
            this.showUploadProgress(false);
        }
    }

    showUploadProgress(show) {
        const button = document.querySelector('#document-upload-form button[type="submit"]');
        const spinner = document.getElementById('upload-spinner');
        
        if (button) {
            button.disabled = show;
            button.textContent = show ? 'Enviando...' : 'Enviar Documento';
        }
        
        if (spinner) {
            spinner.style.display = show ? 'block' : 'none';
        }
    }

    async downloadDocument(documentId) {
        try {
            console.log('[DOCUMENT_MANAGER] Iniciando download:', documentId);
            
            const response = await fetch(`/api/documents/${documentId}/download`);
            const result = await response.json();

            if (result.success) {
                // Abrir URL de download em nova janela
                window.open(result.download_url, '_blank');
            } else {
                this.showError('Erro no download: ' + result.error);
            }
        } catch (error) {
            console.error('[DOCUMENT_MANAGER] Erro no download:', error);
            this.showError('Erro de conexão durante o download');
        }
    }

    async editDocument(documentId) {
        // TODO: Implementar modal de edição
        console.log('[DOCUMENT_MANAGER] Editar documento:', documentId);
        this.showInfo('Funcionalidade de edição será implementada em breve');
    }

    async deleteDocument(documentId) {
        if (!confirm('Tem certeza que deseja remover este documento?')) {
            return;
        }

        try {
            const response = await fetch(`/api/documents/${documentId}/delete`, {
                method: 'DELETE'
            });
            
            const result = await response.json();

            if (result.success) {
                this.showSuccess('Documento removido com sucesso!');
                await this.loadDocuments(); // Recarregar lista
            } else {
                this.showError('Erro ao remover: ' + result.error);
            }
        } catch (error) {
            console.error('[DOCUMENT_MANAGER] Erro ao remover:', error);
            this.showError('Erro de conexão ao remover documento');
        }
    }

    showSuccess(message) {
        this.showNotification(message, 'success');
    }

    showError(message) {
        this.showNotification(message, 'error');
    }

    showInfo(message) {
        this.showNotification(message, 'info');
    }

    showNotification(message, type) {
        // Implementação simples com alert
        // TODO: Implementar sistema de toast/notificação mais elegante
        console.log(`[DOCUMENT_MANAGER] ${type.toUpperCase()}: ${message}`);
        
        if (type === 'error') {
            alert('Erro: ' + message);
        } else if (type === 'success') {
            alert('Sucesso: ' + message);
        } else {
            alert(message);
        }
    }
}

// Variável global para gerenciador de documentos
let documentManager = null;

// Função para inicializar gerenciador no modal
function initializeDocumentManager(processRefUnique) {
    console.log('[DOCUMENT_MANAGER] Inicializando para processo:', processRefUnique);
    documentManager = new DocumentManager(processRefUnique);
    return documentManager;
}
