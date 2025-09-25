// Conciliação Bancária V2 - JavaScript Moderno e Completo
class ConciliacaoBancariaV2 {
    constructor() {
        // Estados da aplicação
        this.state = {
            arquivosProcessados: new Map(),
            dadosSistema: [],
            resultadosConciliacao: null,
            conciliacoesManuais: [],
            selecionadosSistema: new Set(),
            selecionadosBanco: new Set(),
            progresso: 0,
            etapaAtual: 0
        };
        
        // Configurações
        this.config = {
            maxFileSize: 10 * 1024 * 1024, // 10MB
            allowedExtensions: ['.xlsx', '.xls', '.txt', '.csv'],
            apiEndpoints: {
                uploadArquivo: '/financeiro/conciliacao-v2/api/upload-arquivo',
                carregarSistema: '/financeiro/conciliacao-v2/api/carregar-dados-sistema',
                conciliacaoAuto: '/financeiro/conciliacao-v2/api/conciliacao-automatica',
                conciliacaoManual: '/financeiro/conciliacao-v2/api/conciliacao-manual',
                limparDados: '/financeiro/conciliacao-v2/api/limpar-dados',
                status: '/financeiro/conciliacao-v2/api/status'
            },
            apiBypassKey: 'uniq_api_2025_dev_bypass_key',
            sessionId: null
        };
        
        // Charts
        this.charts = {
            gauge: null,
            progress: null
        };
        
        this.init();
    }
    
    init() {
        console.log('🚀 Inicializando Conciliação Bancária V2');
        this.setupEventListeners();
        this.setupDragAndDrop();
        this.setupSortableTables();
        this.loadStatus();
        this.updateProgress(0);
    }
    
    // API Headers helper
    getApiHeaders() {
        const headers = {};
        
        // Sempre adicionar X-API-Key para bypass
        headers['X-API-Key'] = this.config.apiBypassKey;
        
        // Gerar session ID se não existir
        if (!this.config.sessionId) {
            this.config.sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        }
        
        headers['X-Session-ID'] = this.config.sessionId;
        
        return headers;
    }
    
    // Event Listeners
    setupEventListeners() {
        // Upload de arquivos
        const fileInput = document.getElementById('fileInput');
        const btnSelectFiles = document.getElementById('btnSelectFiles');
        const btnProcessarArquivos = document.getElementById('btnProcessarArquivos');
        const btnLimparArquivos = document.getElementById('btnLimparArquivos');
        
        if (btnSelectFiles) {
            btnSelectFiles.addEventListener('click', () => fileInput.click());
        }
        
        if (fileInput) {
            fileInput.addEventListener('change', (e) => this.handleFileSelection(e.target.files));
        }
        
        if (btnProcessarArquivos) {
            btnProcessarArquivos.addEventListener('click', () => this.processarTodosArquivos());
        }
        
        if (btnLimparArquivos) {
            btnLimparArquivos.addEventListener('click', () => this.limparArquivos());
        }
        
        // Formulário do sistema
        const formSistema = document.getElementById('formSistema');
        const selectPeriodo = document.getElementById('selectPeriodo');
        
        if (formSistema) {
            formSistema.addEventListener('submit', (e) => this.handleCarregarSistema(e));
        }
        
        if (selectPeriodo) {
            selectPeriodo.addEventListener('change', () => this.toggleDataPersonalizada());
        }
        
        // Conciliação
        const btnConciliacaoAuto = document.getElementById('btnConciliacaoAuto');
        const btnConciliarManual = document.getElementById('btnConciliarManual');
        const btnLimparSelecao = document.getElementById('btnLimparSelecao');
        const btnClosePanel = document.getElementById('btnClosePanel');
        
        if (btnConciliacaoAuto) {
            btnConciliacaoAuto.addEventListener('click', () => this.executarConciliacaoAutomatica());
        }
        
        if (btnConciliarManual) {
            btnConciliarManual.addEventListener('click', () => this.conciliarManualmente());
        }
        
        if (btnLimparSelecao) {
            btnLimparSelecao.addEventListener('click', () => this.limparSelecao());
        }
        
        if (btnClosePanel) {
            btnClosePanel.addEventListener('click', () => this.fecharPainelManual());
        }
        
        // Controles globais
        const btnLimparDados = document.getElementById('btnLimparDados');
        const btnExportarRelatorio = document.getElementById('btnExportarRelatorio');
        
        if (btnLimparDados) {
            btnLimparDados.addEventListener('click', () => this.limparDados());
        }
        
        if (btnExportarRelatorio) {
            btnExportarRelatorio.addEventListener('click', () => this.exportarRelatorio());
        }
        
        // Checkboxes "selecionar todos"
        const selectAllSistema = document.getElementById('selectAllSistema');
        const selectAllBanco = document.getElementById('selectAllBanco');
        
        if (selectAllSistema) {
            selectAllSistema.addEventListener('change', (e) => this.toggleSelectAll('sistema', e.target.checked));
        }
        
        if (selectAllBanco) {
            selectAllBanco.addEventListener('change', (e) => this.toggleSelectAll('banco', e.target.checked));
        }
        
        // Filtros de tabela
        this.setupTableFilters();
    }
    
    setupTableFilters() {
        const filters = [
            'filtroTipoSistema', 'filtroBancoSistema', 'searchSistema',
            'filtroTipoBanco', 'filtroBancoBanco', 'searchBanco'
        ];
        
        filters.forEach(filterId => {
            const element = document.getElementById(filterId);
            if (element) {
                element.addEventListener('change', () => this.aplicarFiltros());
                element.addEventListener('input', () => this.aplicarFiltros());
            }
        });
    }
    
    // Drag and Drop
    setupDragAndDrop() {
        const uploadZone = document.getElementById('uploadZone');
        if (!uploadZone) return;
        
        uploadZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadZone.classList.add('dragover');
        });
        
        uploadZone.addEventListener('dragleave', () => {
            uploadZone.classList.remove('dragover');
        });
        
        uploadZone.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadZone.classList.remove('dragover');
            this.handleFileSelection(e.dataTransfer.files);
        });
        
        // Clique na zona
        uploadZone.addEventListener('click', () => {
            document.getElementById('fileInput').click();
        });
    }
    
    // File Handling
    async handleFileSelection(files) {
        console.log(`📁 ${files.length} arquivo(s) selecionado(s)`);
        
        const validFiles = Array.from(files).filter(file => this.validateFile(file));
        
        if (validFiles.length === 0) {
            this.showNotification('Nenhum arquivo válido encontrado', 'warning');
            return;
        }
        
        // Adicionar arquivos à lista
        for (const file of validFiles) {
            await this.addFileToList(file);
        }
        
        this.updateFilesList();
        this.updateProgress(25);
        this.updateStep(1);
    }
    
    validateFile(file) {
        // Validar extensão
        const extension = '.' + file.name.split('.').pop().toLowerCase();
        if (!this.config.allowedExtensions.includes(extension)) {
            this.showNotification(`Arquivo ${file.name}: Extensão não suportada`, 'error');
            return false;
        }
        
        // Validar tamanho
        if (file.size > this.config.maxFileSize) {
            this.showNotification(`Arquivo ${file.name}: Tamanho excede 10MB`, 'error');
            return false;
        }
        
        return true;
    }
    
    async addFileToList(file) {
        const fileId = `file_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        
        // Detectar banco automaticamente
        const bancoDetectado = this.detectBankFromFileName(file.name);
        
        const fileData = {
            id: fileId,
            file: file,
            name: file.name,
            size: file.size,
            type: file.type,
            banco: bancoDetectado,
            status: 'pending',
            movimentos: 0
        };
        
        this.state.arquivosProcessados.set(fileId, fileData);
    }
    
    detectBankFromFileName(filename) {
        const name = filename.toLowerCase();
        
        if (name.includes('brasil') || name.includes('bb')) {
            return 'BANCO_DO_BRASIL';
        } else if (name.includes('santander')) {
            return 'BANCO_SANTANDER';
        } else if (name.includes('itau') || name.includes('itaú')) {
            return 'BANCO_ITAU';
        }
        
        // Por extensão
        if (name.endsWith('.txt')) {
            return 'BANCO_ITAU';
        } else if (name.endsWith('.xlsx') || name.endsWith('.xls')) {
            return 'BANCO_DO_BRASIL'; // Default
        }
        
        return 'auto';
    }
    
    updateFilesList() {
        const container = document.getElementById('filesContainer');
        const filesList = document.getElementById('filesList');
        const uploadActions = document.getElementById('uploadActions');
        
        if (!container) return;
        
        container.innerHTML = '';
        
        if (this.state.arquivosProcessados.size === 0) {
            filesList.style.display = 'none';
            uploadActions.style.display = 'none';
            return;
        }
        
        filesList.style.display = 'block';
        uploadActions.style.display = 'block';
        
        this.state.arquivosProcessados.forEach((fileData) => {
            const fileItem = this.createFileItem(fileData);
            container.appendChild(fileItem);
        });
    }
    
    createFileItem(fileData) {
        const item = document.createElement('div');
        item.className = 'file-item';
        item.innerHTML = `
            <div class="file-icon ${this.getFileIconClass(fileData.name)}">
                <i class="mdi ${this.getFileIconName(fileData.name)}"></i>
            </div>
            <div class="file-info">
                <div class="file-name">${fileData.name}</div>
                <div class="file-details">
                    ${this.formatFileSize(fileData.size)} • ${fileData.banco} • 
                    ${fileData.movimentos} movimentos
                </div>
            </div>
            <div class="file-status">
                ${this.getStatusBadge(fileData.status)}
            </div>
            <div class="file-actions">
                ${fileData.status === 'pending' ? `
                    <button type="button" class="btn btn-sm btn-primary btn-file-action" onclick="conciliacao.processarArquivo('${fileData.id}')">
                        <i class="mdi mdi-play"></i>
                    </button>
                ` : ''}
                <button type="button" class="btn btn-sm btn-outline-danger btn-file-action" onclick="conciliacao.removerArquivo('${fileData.id}')">
                    <i class="mdi mdi-delete"></i>
                </button>
            </div>
        `;
        
        return item;
    }
    
    getFileIconClass(filename) {
        if (filename.toLowerCase().endsWith('.txt')) {
            return 'txt';
        }
        return 'excel';
    }
    
    getFileIconName(filename) {
        if (filename.toLowerCase().endsWith('.txt')) {
            return 'mdi-file-document';
        }
        return 'mdi-file-excel';
    }
    
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    getStatusBadge(status) {
        const badges = {
            'pending': '<span class="badge bg-warning">Pendente</span>',
            'processing': '<span class="badge bg-info">Processando...</span>',
            'completed': '<span class="badge bg-success">Processado</span>',
            'error': '<span class="badge bg-danger">Erro</span>'
        };
        
        return badges[status] || badges['pending'];
    }
    
    async processarArquivo(fileId) {
        const fileData = this.state.arquivosProcessados.get(fileId);
        if (!fileData) return;
        
        this.showLoading('Processando arquivo...', `Analisando ${fileData.name}`);
        
        try {
            fileData.status = 'processing';
            this.updateFilesList();
            
            const formData = new FormData();
            formData.append('arquivo', fileData.file);
            formData.append('banco_origem', fileData.banco);
            
            const response = await fetch(this.config.apiEndpoints.uploadArquivo, {
                method: 'POST',
                headers: this.getApiHeaders(),
                body: formData
            });
            
            const result = await response.json();
            
            if (result.success) {
                fileData.status = 'completed';
                fileData.movimentos = result.total_movimentos;
                fileData.processedData = result.movimentos;
                
                this.showNotification(`${fileData.name} processado com sucesso! ${result.total_movimentos} movimentos encontrados.`, 'success');
            } else {
                fileData.status = 'error';
                this.showNotification(`Erro ao processar ${fileData.name}: ${result.message}`, 'error');
            }
            
        } catch (error) {
            console.error('Erro no processamento:', error);
            fileData.status = 'error';
            this.showNotification(`Erro ao processar arquivo: ${error.message}`, 'error');
        } finally {
            this.hideLoading();
            this.updateFilesList();
            this.checkProgressState();
        }
    }
    
    async processarTodosArquivos() {
        const pendingFiles = Array.from(this.state.arquivosProcessados.values())
            .filter(file => file.status === 'pending');
        
        if (pendingFiles.length === 0) {
            this.showNotification('Nenhum arquivo pendente para processar', 'info');
            return;
        }
        
        for (const fileData of pendingFiles) {
            await this.processarArquivo(fileData.id);
        }
        
        this.mostrarSecaoSistema();
    }
    
    removerArquivo(fileId) {
        this.state.arquivosProcessados.delete(fileId);
        this.updateFilesList();
        this.checkProgressState();
        this.showNotification('Arquivo removido', 'info');
    }
    
    limparArquivos() {
        this.state.arquivosProcessados.clear();
        this.updateFilesList();
        this.updateProgress(0);
        this.updateStep(0);
        this.showNotification('Lista de arquivos limpa', 'info');
    }
    
    // Sistema Data Loading
    toggleDataPersonalizada() {
        const periodo = document.getElementById('selectPeriodo').value;
        const dataInicioGroup = document.getElementById('dataInicioGroup');
        const dataFimGroup = document.getElementById('dataFimGroup');
        
        if (periodo === 'personalizado') {
            dataInicioGroup.style.display = 'block';
            dataFimGroup.style.display = 'block';
        } else {
            dataInicioGroup.style.display = 'none';
            dataFimGroup.style.display = 'none';
        }
    }
    
    async handleCarregarSistema(event) {
        event.preventDefault();
        
        const formData = new FormData(event.target);
        const data = Object.fromEntries(formData);
        
        this.showLoading('Carregando dados do sistema...', 'Buscando movimentos na base de dados');
        
        try {
            const response = await fetch(this.config.apiEndpoints.carregarSistema, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...this.getApiHeaders()
                },
                body: JSON.stringify(data)
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.state.dadosSistema = result.movimentos;
                this.updateProgress(50);
                this.updateStep(2);
                
                this.mostrarSecaoConciliacao();
                this.populateTable('sistema', this.state.dadosSistema);
                this.updateMetrics();
                
                this.showNotification(`${result.total_movimentos} movimentos carregados do sistema`, 'success');
            } else {
                this.showNotification(`Erro: ${result.message}`, 'error');
            }
            
        } catch (error) {
            console.error('Erro ao carregar dados:', error);
            this.showNotification(`Erro ao carregar dados: ${error.message}`, 'error');
        } finally {
            this.hideLoading();
        }
    }
    
    // Conciliação Automática
    async executarConciliacaoAutomatica() {
        // Validar se há dados necessários
        if (this.state.dadosSistema.length === 0) {
            this.showNotification('Carregue primeiro os dados do sistema', 'warning');
            return;
        }
        
        const arquivosProcessados = Array.from(this.state.arquivosProcessados.values())
            .filter(file => file.status === 'completed');
            
        if (arquivosProcessados.length === 0) {
            this.showNotification('Processe pelo menos um arquivo bancário', 'warning');
            return;
        }
        
        this.showLoading('Executando conciliação automática...', 'Aplicando algoritmos de matching inteligente');
        
        try {
            const response = await fetch(this.config.apiEndpoints.conciliacaoAuto, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...this.getApiHeaders()
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.state.resultadosConciliacao = result;
                this.updateProgress(75);
                this.updateStep(3);
                
                this.mostrarResultados();
                this.updateMetrics();
                this.initializeGaugeChart();
                
                this.showNotification(`Conciliação automática concluída! ${result.estatisticas.conciliados} conciliações encontradas.`, 'success');
            } else {
                this.showNotification(`Erro: ${result.message}`, 'error');
            }
            
        } catch (error) {
            console.error('Erro na conciliação:', error);
            this.showNotification(`Erro na conciliação: ${error.message}`, 'error');
        } finally {
            this.hideLoading();
        }
    }
    
    // Conciliação Manual
    async conciliarManualmente() {
        const idsSistema = Array.from(this.state.selecionadosSistema);
        const idsBanco = Array.from(this.state.selecionadosBanco);
        
        if (idsSistema.length === 0 || idsBanco.length === 0) {
            this.showNotification('Selecione registros do sistema e do banco', 'warning');
            return;
        }
        
        this.showLoading('Executando conciliação manual...', 'Processando registros selecionados');
        
        try {
            const response = await fetch(this.config.apiEndpoints.conciliacaoManual, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...this.getApiHeaders()
                },
                body: JSON.stringify({
                    ids_sistema: idsSistema,
                    ids_banco: idsBanco
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                // Remover itens conciliados das tabelas
                this.removerConciliados(idsSistema, idsBanco);
                
                // Limpar seleção
                this.limparSelecao();
                
                // Atualizar métricas
                this.updateMetrics();
                
                this.showNotification(result.message, 'success');
            } else {
                this.showNotification(`Erro: ${result.message}`, 'error');
            }
            
        } catch (error) {
            console.error('Erro na conciliação manual:', error);
            this.showNotification(`Erro na conciliação manual: ${error.message}`, 'error');
        } finally {
            this.hideLoading();
        }
    }
    
    // Table Management
    populateTable(tipo, dados) {
        const tbody = document.getElementById(`tbody${tipo === 'sistema' ? 'Sistema' : 'Banco'}`);
        const badge = document.getElementById(`badge${tipo === 'sistema' ? 'Sistema' : 'Banco'}`);
        
        if (!tbody || !badge) return;
        
        tbody.innerHTML = '';
        badge.textContent = dados.length;
        
        dados.forEach((item, index) => {
            const row = this.createTableRow(tipo, item, index);
            tbody.appendChild(row);
        });
        
        this.updateSelectionInfo(tipo);
    }
    
    createTableRow(tipo, item, index) {
        const row = document.createElement('tr');
        row.dataset.id = item.id;
        row.dataset.index = index;
        
        const isSelected = tipo === 'sistema' 
            ? this.state.selecionadosSistema.has(item.id)
            : this.state.selecionadosBanco.has(item.id);
        
        if (isSelected) {
            row.classList.add('selected');
        }
        
        if (item.conciliado) {
            row.classList.add('conciliado');
        }
        
        const statusClass = item.conciliado ? 'conciliado' : 'pendente';
        const statusText = item.conciliado ? 'Conciliado' : 'Pendente';
        
        row.innerHTML = `
            <td class="text-center">
                <input type="checkbox" 
                       data-tipo="${tipo}" 
                       data-id="${item.id}"
                       ${isSelected ? 'checked' : ''}
                       ${item.conciliado ? 'disabled' : ''}>
            </td>
            <td>${tipo === 'sistema' ? item.data_formatada : item.data}</td>
            <td class="text-end">${item.valor_formatado}</td>
            <td>${item.banco}</td>
            <td><span class="badge ${item.tipo === 'RECEITA' || item.tipo === 'CREDITO' ? 'bg-success' : 'bg-danger'}">${item.tipo}</span></td>
            <td title="${item.descricao}">${this.truncateText(item.descricao, 40)}</td>
            <td class="text-center">
                <span class="status-badge ${statusClass}">${statusText}</span>
            </td>
        `;
        
        // Event listeners para checkboxes
        const checkbox = row.querySelector('input[type="checkbox"]');
        if (checkbox && !checkbox.disabled) {
            checkbox.addEventListener('change', (e) => {
                this.handleRowSelection(tipo, item.id, e.target.checked);
            });
        }
        
        return row;
    }
    
    truncateText(text, maxLength) {
        if (!text) return '';
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    }
    
    handleRowSelection(tipo, id, isSelected) {
        const set = tipo === 'sistema' ? this.state.selecionadosSistema : this.state.selecionadosBanco;
        
        if (isSelected) {
            set.add(id);
        } else {
            set.delete(id);
        }
        
        this.updateTableRowSelection(tipo, id, isSelected);
        this.updateSelectionInfo(tipo);
        this.updateManualPanel();
    }
    
    updateTableRowSelection(tipo, id, isSelected) {
        const row = document.querySelector(`#tbody${tipo === 'sistema' ? 'Sistema' : 'Banco'} tr[data-id="${id}"]`);
        if (row) {
            if (isSelected) {
                row.classList.add('selected');
            } else {
                row.classList.remove('selected');
            }
        }
    }
    
    toggleSelectAll(tipo, selectAll) {
        const set = tipo === 'sistema' ? this.state.selecionadosSistema : this.state.selecionadosBanco;
        const dados = tipo === 'sistema' ? this.state.dadosSistema : this.getAllBankMovements();
        
        set.clear();
        
        if (selectAll) {
            dados.forEach(item => {
                if (!item.conciliado) {
                    set.add(item.id);
                }
            });
        }
        
        // Atualizar checkboxes
        const checkboxes = document.querySelectorAll(`#tbody${tipo === 'sistema' ? 'Sistema' : 'Banco'} input[type="checkbox"]`);
        checkboxes.forEach(checkbox => {
            if (!checkbox.disabled) {
                checkbox.checked = selectAll;
                const row = checkbox.closest('tr');
                if (selectAll) {
                    row.classList.add('selected');
                } else {
                    row.classList.remove('selected');
                }
            }
        });
        
        this.updateSelectionInfo(tipo);
        this.updateManualPanel();
    }
    
    getAllBankMovements() {
        const allMovements = [];
        this.state.arquivosProcessados.forEach(fileData => {
            if (fileData.processedData) {
                allMovements.push(...fileData.processedData);
            }
        });
        return allMovements;
    }
    
    updateSelectionInfo(tipo) {
        const set = tipo === 'sistema' ? this.state.selecionadosSistema : this.state.selecionadosBanco;
        const dados = tipo === 'sistema' ? this.state.dadosSistema : this.getAllBankMovements();
        const infoElement = document.getElementById(`selecao${tipo === 'sistema' ? 'Sistema' : 'Banco'}Info`);
        
        if (!infoElement) return;
        
        const selecionados = Array.from(set);
        const valorTotal = selecionados.reduce((total, id) => {
            const item = dados.find(d => d.id === id);
            return total + (item ? parseFloat(item.valor) : 0);
        }, 0);
        
        const valorFormatado = new Intl.NumberFormat('pt-BR', {
            style: 'currency',
            currency: 'BRL'
        }).format(valorTotal);
        
        infoElement.innerHTML = `<strong>${selecionados.length}</strong> selecionados | Valor: <strong>${valorFormatado}</strong>`;
    }
    
    updateManualPanel() {
        const sistemaSelecionados = this.state.selecionadosSistema.size;
        const bancoSelecionados = this.state.selecionadosBanco.size;
        
        const panel = document.getElementById('manualPanel');
        const btnConciliarManual = document.getElementById('btnConciliarManual');
        
        if (sistemaSelecionados > 0 || bancoSelecionados > 0) {
            panel.style.display = 'block';
            panel.classList.add('active');
            
            // Calcular valores
            const valorSistema = this.calculateSelectedValue('sistema');
            const valorBanco = this.calculateSelectedValue('banco');
            const diferenca = valorSistema - valorBanco;
            
            // Atualizar sumário
            document.getElementById('summaryCountSistema').textContent = `${sistemaSelecionados} itens`;
            document.getElementById('summaryValueSistema').textContent = this.formatCurrency(valorSistema);
            document.getElementById('summaryCountBanco').textContent = `${bancoSelecionados} itens`;
            document.getElementById('summaryValueBanco').textContent = this.formatCurrency(valorBanco);
            document.getElementById('summaryDiferenca').textContent = this.formatCurrency(diferenca);
            
            const diferencaElement = document.getElementById('summaryDiferenca');
            diferencaElement.className = `result-value ${diferenca > 0 ? 'positive' : diferenca < 0 ? 'negative' : ''}`;
            
            // Habilitar botão se há seleções em ambas as tabelas
            btnConciliarManual.disabled = !(sistemaSelecionados > 0 && bancoSelecionados > 0);
        } else {
            this.fecharPainelManual();
        }
    }
    
    calculateSelectedValue(tipo) {
        const set = tipo === 'sistema' ? this.state.selecionadosSistema : this.state.selecionadosBanco;
        const dados = tipo === 'sistema' ? this.state.dadosSistema : this.getAllBankMovements();
        
        return Array.from(set).reduce((total, id) => {
            const item = dados.find(d => d.id === id);
            return total + (item ? parseFloat(item.valor) : 0);
        }, 0);
    }
    
    formatCurrency(value) {
        return new Intl.NumberFormat('pt-BR', {
            style: 'currency',
            currency: 'BRL'
        }).format(value);
    }
    
    fecharPainelManual() {
        const panel = document.getElementById('manualPanel');
        panel.style.display = 'none';
        panel.classList.remove('active');
    }
    
    limparSelecao() {
        this.state.selecionadosSistema.clear();
        this.state.selecionadosBanco.clear();
        
        // Desmarcar todos os checkboxes
        document.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
            checkbox.checked = false;
        });
        
        // Remover classe selected
        document.querySelectorAll('tr.selected').forEach(row => {
            row.classList.remove('selected');
        });
        
        this.updateSelectionInfo('sistema');
        this.updateSelectionInfo('banco');
        this.fecharPainelManual();
    }
    
    removerConciliados(idsSistema, idsBanco) {
        // Marcar como conciliados e ocultar
        idsSistema.forEach(id => {
            const row = document.querySelector(`#tbodySistema tr[data-id="${id}"]`);
            if (row) {
                row.classList.add('conciliado');
                const checkbox = row.querySelector('input[type="checkbox"]');
                if (checkbox) {
                    checkbox.disabled = true;
                    checkbox.checked = false;
                }
                const statusCell = row.querySelector('.status-badge');
                if (statusCell) {
                    statusCell.className = 'status-badge conciliado';
                    statusCell.textContent = 'Conciliado';
                }
            }
        });
        
        idsBanco.forEach(id => {
            const row = document.querySelector(`#tbodyBanco tr[data-id="${id}"]`);
            if (row) {
                row.classList.add('conciliado');
                const checkbox = row.querySelector('input[type="checkbox"]');
                if (checkbox) {
                    checkbox.disabled = true;
                    checkbox.checked = false;
                }
                const statusCell = row.querySelector('.status-badge');
                if (statusCell) {
                    statusCell.className = 'status-badge conciliado';
                    statusCell.textContent = 'Conciliado';
                }
            }
        });
    }
    
    // Progress Management
    updateProgress(percentage) {
        this.state.progresso = percentage;
        const progressFill = document.getElementById('progressFill');
        if (progressFill) {
            progressFill.style.width = `${percentage}%`;
        }
    }
    
    updateStep(step) {
        this.state.etapaAtual = step;
        
        // Remover classes ativas e completadas
        document.querySelectorAll('.step').forEach((stepEl, index) => {
            stepEl.classList.remove('active', 'completed');
            if (index < step) {
                stepEl.classList.add('completed');
            } else if (index === step) {
                stepEl.classList.add('active');
            }
        });
        
        // Mostrar barra de progresso se necessário
        const progressoGlobal = document.getElementById('progressoGlobal');
        if (step > 0 && progressoGlobal) {
            progressoGlobal.style.display = 'block';
        }
    }
    
    // UI State Management
    mostrarSecaoSistema() {
        const sistemaSection = document.getElementById('sistemaSection');
        if (sistemaSection) {
            sistemaSection.style.display = 'block';
            sistemaSection.scrollIntoView({ behavior: 'smooth' });
        }
    }
    
    mostrarSecaoConciliacao() {
        const conciliacaoSection = document.getElementById('conciliacaoSection');
        if (conciliacaoSection) {
            conciliacaoSection.style.display = 'block';
            conciliacaoSection.scrollIntoView({ behavior: 'smooth' });
            
            // Atualizar resumo
            document.getElementById('resumoSistema').textContent = this.state.dadosSistema.length;
            document.getElementById('resumoBanco').textContent = Array.from(this.state.arquivosProcessados.values())
                .reduce((total, file) => total + file.movimentos, 0);
            document.getElementById('resumoArquivos').textContent = this.state.arquivosProcessados.size;
        }
    }
    
    mostrarResultados() {
        const resultadosSection = document.getElementById('resultadosSection');
        const resumoFinalSection = document.getElementById('resumoFinalSection');
        
        if (resultadosSection) {
            resultadosSection.style.display = 'block';
            resultadosSection.scrollIntoView({ behavior: 'smooth' });
            
            // Populate tables with remaining data
            this.populateTable('sistema', this.state.dadosSistema.filter(item => !item.conciliado));
            this.populateTable('banco', this.getAllBankMovements().filter(item => !item.conciliado));
        }
        
        if (resumoFinalSection) {
            resumoFinalSection.style.display = 'block';
            this.updateFinalStats();
        }
        
        // Mostrar controles
        document.getElementById('btnLimparDados').style.display = 'inline-block';
        document.getElementById('btnExportarRelatorio').style.display = 'inline-block';
    }
    
    // Metrics and Charts
    updateMetrics() {
        const metricsDashboard = document.getElementById('metricsDashboard');
        if (metricsDashboard) {
            metricsDashboard.style.display = 'block';
        }
        
        // Calcular métricas
        const totalSistema = this.state.dadosSistema.length;
        const totalBanco = Array.from(this.state.arquivosProcessados.values())
            .reduce((total, file) => total + file.movimentos, 0);
        
        let conciliados = 0;
        let pendentes = totalSistema;
        let taxaSucesso = 0;
        
        if (this.state.resultadosConciliacao) {
            conciliados = this.state.resultadosConciliacao.estatisticas.conciliados;
            pendentes = this.state.resultadosConciliacao.estatisticas.nao_conciliados;
            taxaSucesso = this.state.resultadosConciliacao.estatisticas.taxa_sucesso;
        }
        
        // Atualizar displays
        document.getElementById('metricaConciliados').textContent = conciliados;
        document.getElementById('metricaPendentes').textContent = pendentes;
        document.getElementById('metricaSistema').textContent = totalSistema;
        document.getElementById('metricaBanco').textContent = totalBanco;
        document.getElementById('metricaPercentual').textContent = `${Math.round(taxaSucesso)}%`;
    }
    
    initializeGaugeChart() {
        const canvas = document.getElementById('gaugeChart');
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        
        if (this.charts.gauge) {
            this.charts.gauge.destroy();
        }
        
        const taxaSucesso = this.state.resultadosConciliacao ? 
            this.state.resultadosConciliacao.estatisticas.taxa_sucesso : 0;
        
        this.charts.gauge = new Chart(ctx, {
            type: 'doughnut',
            data: {
                datasets: [{
                    data: [taxaSucesso, 100 - taxaSucesso],
                    backgroundColor: [
                        taxaSucesso >= 80 ? '#10b981' : taxaSucesso >= 60 ? '#f59e0b' : '#ef4444',
                        '#f3f4f6'
                    ],
                    borderWidth: 0,
                    cutout: '75%'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        enabled: false
                    }
                }
            }
        });
    }
    
    updateFinalStats() {
        if (!this.state.resultadosConciliacao) return;
        
        const stats = this.state.resultadosConciliacao.estatisticas;
        const manuais = this.state.conciliacoesManuais.length;
        
        document.getElementById('finalConciliados').textContent = stats.conciliados;
        document.getElementById('finalParciais').textContent = stats.parciais || 0;
        document.getElementById('finalPendentes').textContent = stats.nao_conciliados;
        document.getElementById('finalManuais').textContent = manuais;
        document.getElementById('progressPercentage').textContent = `${Math.round(stats.taxa_sucesso)}%`;
        
        this.initializeProgressChart();
    }
    
    initializeProgressChart() {
        const canvas = document.getElementById('progressChart');
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        
        if (this.charts.progress) {
            this.charts.progress.destroy();
        }
        
        const stats = this.state.resultadosConciliacao.estatisticas;
        const manuais = this.state.conciliacoesManuais.length;
        
        this.charts.progress = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Conciliados', 'Parciais', 'Pendentes', 'Manuais'],
                datasets: [{
                    data: [stats.conciliados, stats.parciais || 0, stats.nao_conciliados, manuais],
                    backgroundColor: ['#10b981', '#f59e0b', '#ef4444', '#3b82f6'],
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            usePointStyle: true,
                            padding: 15
                        }
                    }
                }
            }
        });
    }
    
    // Utility Functions
    async loadStatus() {
        try {
            const response = await fetch(this.config.apiEndpoints.status);
            const result = await response.json();
            
            if (result.success) {
                console.log('Status atual:', result.status);
                // TODO: Restaurar estado se necessário
            }
        } catch (error) {
            console.error('Erro ao carregar status:', error);
        }
    }
    
    checkProgressState() {
        const processedFiles = Array.from(this.state.arquivosProcessados.values())
            .filter(file => file.status === 'completed').length;
        
        if (processedFiles > 0 && this.state.dadosSistema.length === 0) {
            this.mostrarSecaoSistema();
        }
    }
    
    setupSortableTables() {
        document.querySelectorAll('.sortable').forEach(header => {
            header.addEventListener('click', () => {
                const column = header.dataset.column;
                const table = header.closest('table');
                const type = table.id === 'tabelaSistema' ? 'sistema' : 'banco';
                this.sortTable(type, column);
            });
        });
    }
    
    sortTable(type, column) {
        // TODO: Implementar ordenação
        console.log(`Ordenando tabela ${type} por ${column}`);
    }
    
    aplicarFiltros() {
        // TODO: Implementar filtros
        console.log('Aplicando filtros');
    }
    
    async limparDados() {
        if (!confirm('Tem certeza que deseja limpar todos os dados? Esta ação não pode ser desfeita.')) {
            return;
        }
        
        try {
            const response = await fetch(this.config.apiEndpoints.limparDados, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...this.getApiHeaders()
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                // Reset local state
                this.state = {
                    arquivosProcessados: new Map(),
                    dadosSistema: [],
                    resultadosConciliacao: null,
                    conciliacoesManuais: [],
                    selecionadosSistema: new Set(),
                    selecionadosBanco: new Set(),
                    progresso: 0,
                    etapaAtual: 0
                };
                
                // Reset UI
                this.updateProgress(0);
                this.updateStep(0);
                this.limparArquivos();
                
                // Ocultar seções
                document.getElementById('sistemaSection').style.display = 'none';
                document.getElementById('conciliacaoSection').style.display = 'none';
                document.getElementById('resultadosSection').style.display = 'none';
                document.getElementById('resumoFinalSection').style.display = 'none';
                document.getElementById('metricsDashboard').style.display = 'none';
                document.getElementById('progressoGlobal').style.display = 'none';
                
                // Ocultar botões
                document.getElementById('btnLimparDados').style.display = 'none';
                document.getElementById('btnExportarRelatorio').style.display = 'none';
                
                this.showNotification('Dados limpos com sucesso!', 'success');
            } else {
                this.showNotification(`Erro: ${result.message}`, 'error');
            }
        } catch (error) {
            console.error('Erro ao limpar dados:', error);
            this.showNotification(`Erro: ${error.message}`, 'error');
        }
    }
    
    async exportarRelatorio() {
        this.showNotification('Funcionalidade em desenvolvimento', 'info');
    }
    
    // UI Helpers
    showLoading(title = 'Carregando...', message = 'Aguarde...') {
        const overlay = document.getElementById('loadingOverlay');
        const titleEl = document.getElementById('loadingTitle');
        const messageEl = document.getElementById('loadingMessage');
        
        if (titleEl) titleEl.textContent = title;
        if (messageEl) messageEl.textContent = message;
        if (overlay) overlay.style.display = 'flex';
    }
    
    hideLoading() {
        const overlay = document.getElementById('loadingOverlay');
        if (overlay) overlay.style.display = 'none';
    }
    
    showNotification(message, type = 'info') {
        // Criar toast notification
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <div class="toast-content">
                <i class="mdi ${this.getToastIcon(type)}"></i>
                <span>${message}</span>
            </div>
        `;
        
        // Adicionar estilos se não existirem
        if (!document.getElementById('toast-styles')) {
            const styles = document.createElement('style');
            styles.id = 'toast-styles';
            styles.textContent = `
                .toast {
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    background: #fff;
                    border-radius: 8px;
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
                    padding: 16px 20px;
                    z-index: 10000;
                    transform: translateX(400px);
                    transition: transform 0.3s ease;
                    max-width: 400px;
                    border-left: 4px solid #e5e7eb;
                }
                .toast.toast-success { border-left-color: #10b981; }
                .toast.toast-error { border-left-color: #ef4444; }
                .toast.toast-warning { border-left-color: #f59e0b; }
                .toast.toast-info { border-left-color: #3b82f6; }
                .toast.show { transform: translateX(0); }
                .toast-content { display: flex; align-items: center; gap: 12px; }
                .toast-content i { font-size: 18px; }
                .toast.toast-success i { color: #10b981; }
                .toast.toast-error i { color: #ef4444; }
                .toast.toast-warning i { color: #f59e0b; }
                .toast.toast-info i { color: #3b82f6; }
            `;
            document.head.appendChild(styles);
        }
        
        document.body.appendChild(toast);
        
        // Animar entrada
        setTimeout(() => toast.classList.add('show'), 100);
        
        // Remover após 5 segundos
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => document.body.removeChild(toast), 300);
        }, 5000);
        
        console.log(`${type.toUpperCase()}: ${message}`);
    }
    
    getToastIcon(type) {
        const icons = {
            success: 'mdi-check-circle',
            error: 'mdi-alert-circle',
            warning: 'mdi-alert',
            info: 'mdi-information'
        };
        return icons[type] || icons.info;
    }
}

// Initialize quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', () => {
    window.conciliacao = new ConciliacaoBancariaV2();
});

// Export para uso global
window.ConciliacaoBancariaV2 = ConciliacaoBancariaV2;
