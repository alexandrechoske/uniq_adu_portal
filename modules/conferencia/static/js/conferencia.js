// === CONFERÊNCIA DOCUMENTAL IA - JAVASCRIPT ===

class ConferenciaDocumental {
    constructor() {
        this.uploadedFiles = [];
        this.currentJobId = null;
        this.progressInterval = null;
        this.tipoConferencia = 'inconsistencias';
        
        this.init();
    }
    
    init() {
        console.log('Iniciando configuração dos event listeners...');
        try {
            // Garantir que loading está oculto na inicialização
            this.hideLoading();
            
            this.setupEventListeners();
            this.setupDropzone();
            this.setupRadioOptions();
            console.log('Configuração concluída com sucesso!');
        } catch (error) {
            console.error('Erro durante a inicialização:', error);
        }
    }
    
    setupEventListeners() {
        // Botão de upload
        const uploadBtn = document.getElementById('upload-btn');
        if (uploadBtn) {
            uploadBtn.addEventListener('click', () => this.processFiles());
        }
        
        // Input de arquivo
        const fileInput = document.getElementById('file-input');
        if (fileInput) {
            fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
        }
        
        // Botão de fechar modal
        const closeModal = document.getElementById('close-details');
        if (closeModal) {
            closeModal.addEventListener('click', () => this.closeDetailsModal());
        }
        
        // Fechar modal clicando fora
        const detailsContainer = document.getElementById('details-container');
        if (detailsContainer) {
            detailsContainer.addEventListener('click', (e) => {
                if (e.target === detailsContainer) {
                    this.closeDetailsModal();
                }
            });
        }
    }
    
    setupDropzone() {
        const dropzone = document.getElementById('dropzone');
        if (!dropzone) return;
        
        // Prevenir comportamento padrão do browser
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropzone.addEventListener(eventName, this.preventDefaults, false);
            document.body.addEventListener(eventName, this.preventDefaults, false);
        });
        
        // Highlight na zona de drop
        ['dragenter', 'dragover'].forEach(eventName => {
            dropzone.addEventListener(eventName, () => this.highlight(dropzone), false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            dropzone.addEventListener(eventName, () => this.unhighlight(dropzone), false);
        });
        
        // Processar arquivos soltos
        dropzone.addEventListener('drop', (e) => this.handleDrop(e), false);
        
        // Click para abrir seletor de arquivo
        dropzone.addEventListener('click', () => {
            document.getElementById('file-input').click();
        });
    }
    
    setupRadioOptions() {
        const radioOptions = document.querySelectorAll('.radio-option');
        radioOptions.forEach(option => {
            option.addEventListener('click', () => {
                // Remover seleção anterior
                radioOptions.forEach(opt => opt.classList.remove('selected'));
                
                // Adicionar seleção atual
                option.classList.add('selected');
                
                // Marcar o radio button
                const radio = option.querySelector('input[type="radio"]');
                if (radio) {
                    radio.checked = true;
                    this.tipoConferencia = radio.value;
                }
            });
        });
    }
    
    preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    highlight(element) {
        element.classList.add('dragover');
    }
    
    unhighlight(element) {
        element.classList.remove('dragover');
    }
    
    handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        this.handleFiles(files);
    }
    
    handleFileSelect(e) {
        const files = e.target.files;
        this.handleFiles(files);
    }
    
    handleFiles(files) {
        ([...files]).forEach(file => {
            if (this.validateFile(file)) {
                this.addFileToList(file);
            }
        });
        this.updateUploadButton();
    }
    
    validateFile(file) {
        const allowedTypes = ['application/pdf'];
        const maxSize = 10 * 1024 * 1024; // 10MB
        
        if (!allowedTypes.includes(file.type)) {
            this.showNotification('Apenas arquivos PDF são permitidos.', 'error');
            return false;
        }
        
        if (file.size > maxSize) {
            this.showNotification('Arquivo muito grande. Tamanho máximo: 10MB.', 'error');
            return false;
        }
        
        return true;
    }
    
    addFileToList(file) {
        // Verificar se arquivo já foi adicionado
        if (this.uploadedFiles.find(f => f.name === file.name && f.size === file.size)) {
            this.showNotification('Arquivo já foi adicionado.', 'warning');
            return;
        }
        
        this.uploadedFiles.push(file);
        this.renderFileList();
    }
    
    renderFileList() {
        const fileList = document.getElementById('file-list');
        if (!fileList) return;
        
        if (this.uploadedFiles.length === 0) {
            fileList.innerHTML = '';
            return;
        }
        
        const filesHtml = this.uploadedFiles.map((file, index) => `
            <div class="file-item" data-index="${index}">
                <i class="file-icon mdi mdi-file-pdf-box"></i>
                <div class="file-info">
                    <div class="file-name" title="${file.name}">${file.name}</div>
                    <div class="file-size">${this.formatFileSize(file.size)}</div>
                </div>
                <div class="file-actions">
                    <button class="file-action" onclick="conferencia.removeFile(${index})" title="Remover arquivo">
                        <i class="mdi mdi-close"></i>
                    </button>
                </div>
            </div>
        `).join('');
        
        fileList.innerHTML = filesHtml;
    }
    
    removeFile(index) {
        this.uploadedFiles.splice(index, 1);
        this.renderFileList();
        this.updateUploadButton();
    }
    
    updateUploadButton() {
        const uploadBtn = document.getElementById('upload-btn');
        if (!uploadBtn) return;
        
        if (this.uploadedFiles.length > 0) {
            uploadBtn.disabled = false;
            uploadBtn.innerHTML = `
                <i class="mdi mdi-upload"></i>
                Processar ${this.uploadedFiles.length} arquivo${this.uploadedFiles.length > 1 ? 's' : ''}
            `;
        } else {
            uploadBtn.disabled = true;
            uploadBtn.innerHTML = `
                <i class="mdi mdi-upload"></i>
                Selecione arquivos para processar
            `;
        }
    }
    
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    async processFiles() {
        if (this.uploadedFiles.length === 0) {
            this.showNotification('Selecione pelo menos um arquivo.', 'warning');
            return;
        }
        
        console.log('Iniciando processamento...', {
            arquivos: this.uploadedFiles.length,
            tipo: this.tipoConferencia
        });
        
        // Preparar FormData
        const formData = new FormData();
        this.uploadedFiles.forEach(file => {
            formData.append('files[]', file);
        });
        formData.append('tipo_conferencia', this.tipoConferencia);
        
        try {
            this.showLoading('Enviando arquivos...');
            
            // Enviar arquivos
            const response = await fetch('/conferencia/upload', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.currentJobId = result.job_id;
                this.hideLoading();
                this.showProcessingTimeline();
                this.startProgressMonitoring();
                this.clearFileList();
                
                console.log('Upload realizado com sucesso:', {
                    job_id: result.job_id,
                    tipo_conferencia: result.tipo_conferencia || 'não informado',
                    files_count: result.files_count
                });
            } else {
                this.hideLoading();
                this.showNotification(result.message || 'Erro ao processar arquivos.', 'error');
                console.error('Erro no upload:', result);
            }
            
        } catch (error) {
            this.hideLoading();
            this.showNotification('Erro de conexão. Tente novamente.', 'error');
            console.error('Erro:', error);
        }
    }
    
    showProcessingTimeline() {
        const timeline = document.getElementById('processing-timeline');
        if (timeline) {
            timeline.style.display = 'block';
            
            // Resetar steps
            const steps = timeline.querySelectorAll('.timeline-step');
            steps.forEach(step => {
                step.className = 'timeline-step pending';
            });
            
            // Ativar primeiro step
            if (steps[0]) {
                steps[0].className = 'timeline-step active';
            }
        }
    }
    
    startProgressMonitoring() {
        if (this.progressInterval) {
            clearInterval(this.progressInterval);
        }
        
        this.progressInterval = setInterval(() => {
            this.checkProgress();
        }, 1000);
    }
    
    async checkProgress() {
        if (!this.currentJobId) return;
        
        try {
            const response = await fetch(`/conferencia/status/${this.currentJobId}`);
            const status = await response.json();
            
            if (response.ok) {
                this.updateProgress(status);
                
                if (status.status === 'completed') {
                    clearInterval(this.progressInterval);
                    this.showResults();
                } else if (status.status === 'error') {
                    clearInterval(this.progressInterval);
                    this.showNotification('Erro durante o processamento.', 'error');
                    this.hideProcessingElements();
                }
            }
            
        } catch (error) {
            console.error('Erro ao verificar progresso:', error);
        }
    }
    
    updateProgress(status) {
        // Atualizar barra de progresso
        const progressBar = document.getElementById('progress-bar');
        const progressInfo = document.getElementById('progress-info');
        const progressContainer = document.getElementById('progress-container');
        
        if (progressContainer && status.progress !== undefined) {
            progressContainer.style.display = 'block';
            
            if (progressBar) {
                progressBar.style.width = status.progress + '%';
            }
            
            if (progressInfo) {
                progressInfo.textContent = `${status.progress}% concluído`;
                if (status.current_file) {
                    progressInfo.textContent += ` - Processando: ${status.current_file}`;
                }
            }
        }
        
        // Atualizar timeline
        this.updateTimeline(status);
    }
    
    updateTimeline(status) {
        const timeline = document.getElementById('processing-timeline');
        if (!timeline) return;
        
        const steps = timeline.querySelectorAll('.timeline-step');
        
        // Lógica simples de progresso dos steps
        if (status.progress >= 25 && steps[1]) {
            steps[1].className = 'timeline-step active';
        }
        if (status.progress >= 50 && steps[2]) {
            steps[2].className = 'timeline-step active';
        }
        if (status.progress >= 75 && steps[3]) {
            steps[3].className = 'timeline-step active';
        }
        if (status.progress === 100) {
            steps.forEach(step => {
                step.className = 'timeline-step completed';
            });
        }
    }
    
    async showResults() {
        if (!this.currentJobId) return;
        
        try {
            const response = await fetch(`/conferencia/results/${this.currentJobId}`);
            const data = await response.json();
            
            if (response.ok) {
                this.renderResults(data.results);
                this.hideProcessingElements();
                this.showResultsContainer();
            }
            
        } catch (error) {
            console.error('Erro ao carregar resultados:', error);
            this.showNotification('Erro ao carregar resultados.', 'error');
        }
    }
    
    renderResults(results) {
        const resultsCards = document.getElementById('results-cards');
        if (!resultsCards) return;
        
        const cardsHtml = results.map((result, index) => {
            const statusClass = this.getStatusClass(result.status);
            const statusIcon = this.getStatusIcon(result.status);
            
            return `
                <div class="result-card">
                    <div class="result-card-header">
                        <i class="result-card-icon mdi ${statusIcon} ${statusClass}"></i>
                        <div class="result-card-info">
                            <div class="result-card-filename">${result.file}</div>
                            <div class="result-card-summary">${result.status}</div>
                        </div>
                    </div>
                    
                    <div class="result-card-stats">
                        <div class="result-card-stat stat-error">
                            <i class="result-card-stat-icon mdi mdi-alert-circle"></i>
                            ${result.inconsistencias ? result.inconsistencias.length : 0} inconsistências
                        </div>
                    </div>
                    
                    <div class="result-card-actions">
                        <button class="btn btn-outline" onclick="conferencia.showDetails(${index})">
                            <i class="mdi mdi-eye"></i>
                            Ver Detalhes
                        </button>
                    </div>
                </div>
            `;
        }).join('');
        
        resultsCards.innerHTML = cardsHtml;
        
        // Salvar resultados para visualização de detalhes
        this.currentResults = results;
    }
    
    getStatusClass(status) {
        switch (status) {
            case 'completed': return 'result-status-success';
            case 'error': return 'result-status-erro';
            case 'warning': return 'result-status-alerta';
            default: return 'result-status-ok';
        }
    }
    
    getStatusIcon(status) {
        switch (status) {
            case 'completed': return 'mdi-check-circle';
            case 'error': return 'mdi-alert-circle';
            case 'warning': return 'mdi-alert';
            default: return 'mdi-file-check';
        }
    }
    
    showDetails(index) {
        if (!this.currentResults || !this.currentResults[index]) return;
        
        const result = this.currentResults[index];
        const detailsContainer = document.getElementById('details-container');
        const detailsContent = document.getElementById('details-content');
        
        if (!detailsContainer || !detailsContent) return;
        
        // Gerar conteúdo dos detalhes
        let contentHtml = `
            <h3>Arquivo: ${result.file}</h3>
            <p><strong>Status:</strong> ${result.status}</p>
        `;
        
        if (result.inconsistencias && result.inconsistencias.length > 0) {
            contentHtml += `
                <h4>Inconsistências Encontradas:</h4>
                <ul>
                    ${result.inconsistencias.map(inc => `<li>${inc}</li>`).join('')}
                </ul>
            `;
        }
        
        if (result.dados_extraidos) {
            contentHtml += `
                <h4>Dados Extraídos:</h4>
                <pre>${JSON.stringify(result.dados_extraidos, null, 2)}</pre>
            `;
        }
        
        detailsContent.innerHTML = contentHtml;
        detailsContainer.style.display = 'flex';
    }
    
    closeDetailsModal() {
        const detailsContainer = document.getElementById('details-container');
        if (detailsContainer) {
            detailsContainer.style.display = 'none';
        }
    }
    
    showResultsContainer() {
        const resultsContainer = document.getElementById('results-container');
        if (resultsContainer) {
            resultsContainer.style.display = 'block';
        }
    }
    
    hideProcessingElements() {
        const progressContainer = document.getElementById('progress-container');
        const timeline = document.getElementById('processing-timeline');
        
        if (progressContainer) {
            progressContainer.style.display = 'none';
        }
        
        if (timeline) {
            timeline.style.display = 'none';
        }
    }
    
    clearFileList() {
        this.uploadedFiles = [];
        this.renderFileList();
        this.updateUploadButton();
    }
    
    showLoading(message = 'Processando...') {
        const loadingOverlay = document.getElementById('loading-overlay');
        const loadingMessage = document.getElementById('loading-message');
        
        if (loadingMessage) {
            loadingMessage.textContent = message;
        }
        
        if (loadingOverlay) {
            loadingOverlay.style.display = 'flex';
        }
        
        console.log(`Loading mostrado: ${message}`);
    }
    
    hideLoading() {
        const loadingOverlay = document.getElementById('loading-overlay');
        if (loadingOverlay) {
            loadingOverlay.style.display = 'none';
        }
        
        console.log('Loading ocultado');
    }
    
    showNotification(message, type = 'info') {
        // Criar elemento de notificação
        const notification = document.createElement('div');
        notification.className = `flash-message flash-${type}`;
        notification.textContent = message;
        
        // Adicionar ao topo da página
        const header = document.querySelector('.page-header');
        if (header) {
            header.parentNode.insertBefore(notification, header.nextSibling);
        } else {
            document.body.insertBefore(notification, document.body.firstChild);
        }
        
        // Remover após 5 segundos
        setTimeout(() => {
            notification.remove();
        }, 5000);
    }
}

// Inicializar quando a página carregar
let conferencia;
document.addEventListener('DOMContentLoaded', function() {
    console.log('Inicializando Conferencia Documental...');
    conferencia = new ConferenciaDocumental();
    // Expor globalmente para uso em onclick
    window.conferencia = conferencia;
    console.log('Conferencia Documental inicializada com sucesso!');
});
