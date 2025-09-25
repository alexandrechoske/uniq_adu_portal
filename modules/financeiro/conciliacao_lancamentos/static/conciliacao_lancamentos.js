// JavaScript para Conciliação Bancária - Versão atualizada com filtros e seleção múltipla
class ConciliacaoBancaria {
    constructor() {
        this.dadosSistema = [];
        this.dadosBanco = [];
        this.dadosSistemaOriginais = [];
        this.dadosBancoOriginais = [];
        this.conciliacoes = [];
        this.selecionadosSistema = new Set();
        this.selecionadosBanco = new Set();
        this.bancoAtivo = 'todos';
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupFormValidation();
        this.setupFiltros();
        this.setupSelecaoMultipla();
    }

    setupEventListeners() {
        // Eventos do formulário de carregamento
        document.getElementById('banco').addEventListener('change', this.validateForm.bind(this));
        document.getElementById('periodo').addEventListener('change', this.toggleDataPersonalizada.bind(this));
        document.getElementById('uploadForm').addEventListener('submit', this.handleCarregamento.bind(this));

        // Evento para upload de arquivo bancário
        document.getElementById('uploadArquivoForm').addEventListener('submit', this.handleUploadArquivo.bind(this));

        // Eventos dos botões de ação
        document.getElementById('btnConciliarAuto').addEventListener('click', this.conciliarAutomaticamente.bind(this));
        document.getElementById('btnConciliarManual').addEventListener('click', this.conciliarManualmente.bind(this));
        document.getElementById('btnExportarRelatorio').addEventListener('click', this.exportarRelatorio.bind(this));
        document.getElementById('btnLimparTudo').addEventListener('click', this.limparTudo.bind(this));

        // Eventos dos checkboxes "selecionar todos"
        document.getElementById('selectAllSistema').addEventListener('change', this.toggleSelectAllSistema.bind(this));
        document.getElementById('selectAllBanco').addEventListener('change', this.toggleSelectAllBanco.bind(this));

        // Eventos dos novos botões
        document.getElementById('btnConciliarSelecionados').addEventListener('click', this.conciliarSelecionados.bind(this));
        document.getElementById('btnLimparSelecao').addEventListener('click', this.limparSelecao.bind(this));
    }

    setupFiltros() {
        // Configurar filtros de banco
        const filtrosBanco = document.querySelectorAll('.banco-filter-btn');
        filtrosBanco.forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.aplicarFiltroBanco(e.target.dataset.banco);
            });
        });
    }

    setupSelecaoMultipla() {
        // Event delegation para checkboxes individuais
        document.addEventListener('change', (e) => {
            if (e.target.type === 'checkbox' && e.target.dataset.tipo) {
                this.handleCheckboxChange(e.target);
            }
        });
    }

    setupFormValidation() {
        this.validateForm();
    }

    validateForm() {
        const banco = document.getElementById('banco').value;
        const btnUpload = document.getElementById('btnUpload');

        // Para carregamento de dados, apenas o banco é necessário (pode ser "todos")
        const isValid = banco;
        btnUpload.disabled = !isValid;

        if (isValid) {
            btnUpload.classList.remove('btn-secondary');
            btnUpload.classList.add('btn-primary');
        } else {
            btnUpload.classList.remove('btn-primary');
            btnUpload.classList.add('btn-secondary');
        }
    }

    toggleDataPersonalizada() {
        const periodo = document.getElementById('periodo').value;
        const dataPersonalizada = document.getElementById('data-personalizada');
        
        if (periodo === 'personalizado') {
            dataPersonalizada.style.display = 'block';
            dataPersonalizada.classList.add('fade-in');
        } else {
            dataPersonalizada.style.display = 'none';
        }
    }

    async handleCarregamento(event) {
        event.preventDefault();
        
        const formData = new FormData();
        const banco = document.getElementById('banco').value;
        const periodo = document.getElementById('periodo').value;

        formData.append('banco', banco);
        formData.append('periodo', periodo);

        if (periodo === 'personalizado') {
            const dataInicio = document.getElementById('data_inicio').value;
            const dataFim = document.getElementById('data_fim').value;
            formData.append('data_inicio', dataInicio);
            formData.append('data_fim', dataFim);
        }

        this.showLoading(true);
        this.showUploadProgress(true);

        try {
            console.log('[CARREGAMENTO] Enviando requisição para carregar dados...');
            
            const response = await fetch('/financeiro/conciliacao-lancamentos/processar', {
                method: 'POST',
                headers: {
                    'X-API-Key': window.API_BYPASS_KEY || '$env:API_BYPASS_KEY'
                },
                body: formData
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const result = await response.json();
            console.log('[CARREGAMENTO] Resposta recebida:', result);
            
            this.processarResultado(result);

        } catch (error) {
            console.error('Erro no carregamento:', error);
            this.showError('Erro ao carregar dados: ' + error.message);
        } finally {
            this.showLoading(false);
            this.showUploadProgress(false);
        }
    }

    processarResultado(result) {
        console.log('[PROCESSAR] Processando resultado:', result);
        
        if (result.success) {
            // Nova estrutura: result tem dados_aberta e dados_banco
            this.dadosSistemaOriginais = result.dados_aberta || [];
            this.dadosBancoOriginais = result.dados_banco || [];
            
            console.log('[PROCESSAR] Dados carregados - Sistema:', this.dadosSistemaOriginais.length, 'Banco:', this.dadosBancoOriginais.length);
            
            // Aplicar filtro atual
            this.aplicarFiltroBanco(this.bancoAtivo);
            
            this.showStatus(result.status);
            this.renderizarDados();
            this.showSections(['statusSection', 'dadosSection', 'resumoSection']);
            this.atualizarResumo();
            
            this.showSuccess(`Arquivos processados com sucesso! ${this.dadosSistema.length} lançamentos do sistema e ${this.dadosBanco.length} do banco encontrados.`);
        } else {
            console.error('[PROCESSAR] Erro no resultado:', result);
            this.showError(result.message || result.error || 'Erro ao processar arquivos');
        }
    }

    async handleUploadArquivo(event) {
        event.preventDefault();
        
        const formData = new FormData();
        const arquivo = document.getElementById('arquivo_banco').files[0];
        const bancoOrigem = document.getElementById('banco_origem').value;
        
        if (!arquivo) {
            this.showError('Por favor, selecione um arquivo para upload.');
            return;
        }
        
        // Validar tamanho do arquivo (10MB)
        if (arquivo.size > 10 * 1024 * 1024) {
            this.showError('Arquivo muito grande. Máximo permitido: 10MB');
            return;
        }
        
        // Validar extensão
        const allowedExtensions = ['.xlsx', '.xls', '.txt', '.csv'];
        const fileExtension = arquivo.name.toLowerCase().substring(arquivo.name.lastIndexOf('.'));
        if (!allowedExtensions.includes(fileExtension)) {
            this.showError('Formato não suportado. Use .xlsx, .xls, .txt ou .csv');
            return;
        }
        
        formData.append('arquivo', arquivo);
        formData.append('banco_origem', bancoOrigem);
        
        this.showLoading(true, 'Processando arquivo bancário...');
        this.showUploadProgressArquivo(true);
        
        try {
            console.log('[UPLOAD] Iniciando upload do arquivo:', arquivo.name);
            
            const response = await fetch('/financeiro/conciliacao-lancamentos/upload-arquivo', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            console.log('[UPLOAD] Resposta recebida:', result);
            
            if (result.success) {
                // Armazenar dados do banco processados
                this.dadosBancoOriginais = result.data.lancamentos || [];
                
                // Aplicar filtro atual
                this.aplicarFiltroBanco(this.bancoAtivo);
                
                this.renderizarDados();
                this.showSections(['statusSection', 'dadosSection']);
                
                this.showSuccess(`Arquivo ${arquivo.name} processado com sucesso! ${result.data.total_registros} lançamentos encontrados (${result.data.banco_identificado}).`);
                
                // Limpar formulário
                document.getElementById('uploadArquivoForm').reset();
            } else {
                this.showError(result.error || 'Erro ao processar arquivo');
            }
            
        } catch (error) {
            console.error('Erro no upload:', error);
            this.showError('Erro ao fazer upload: ' + error.message);
        } finally {
            this.showLoading(false);
            this.showUploadProgressArquivo(false);
        }
    }

    aplicarFiltroBanco(banco) {
        console.log(`[FILTRO] Aplicando filtro para banco: ${banco}`);
        
        // Atualizar botões ativos
        document.querySelectorAll('.banco-filter-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-banco="${banco}"]`).classList.add('active');
        
        this.bancoAtivo = banco;
        
        if (banco === 'todos') {
            this.dadosSistema = [...this.dadosSistemaOriginais];
            this.dadosBanco = [...this.dadosBancoOriginais];
        } else {
            // Filtrar dados do sistema por banco
            this.dadosSistema = this.dadosSistemaOriginais.filter(item => {
                const nomeBanco = (item.nome_banco || '').toUpperCase();
                return nomeBanco.includes(banco.toUpperCase());
            });
            
            // Filtrar dados do banco por banco (caso os dados do extrato tenham identificação)
            this.dadosBanco = this.dadosBancoOriginais.filter(item => {
                const nomeBanco = (item.nome_banco || item.banco || '').toUpperCase();
                return nomeBanco.includes(banco.toUpperCase());
            });
        }
        
        // Limpar seleções
        this.selecionadosSistema.clear();
        this.selecionadosBanco.clear();
        
        // Re-renderizar tabelas
        this.renderizarDados();
        this.atualizarSomatorio();
        
        console.log(`[FILTRO] Dados filtrados - Sistema: ${this.dadosSistema.length}, Banco: ${this.dadosBanco.length}`);
    }

    showStatus(status) {
        const statusContent = document.getElementById('statusContent');
        statusContent.innerHTML = `
            <div class="alert alert-info">
                <h6><i class="mdi mdi-information"></i> Processamento Concluído</h6>
                <ul class="mb-0">
                    <li>Banco identificado: <strong>${status.banco_identificado}</strong></li>
                    <li>Formato do arquivo: <strong>${status.formato_arquivo}</strong></li>
                    <li>Registros processados no extrato: <strong>${status.registros_banco}</strong></li>
                    <li>Lançamentos do sistema: <strong>${status.registros_sistema}</strong></li>
                    <li>Período analisado: <strong>${status.periodo}</strong></li>
                </ul>
            </div>
        `;
    }

    renderizarDados() {
        this.renderizarTabelaSistema();
        this.renderizarTabelaBanco();
    }

    renderizarTabelaSistema() {
        console.log('[RENDER] Renderizando tabela sistema com', this.dadosSistema.length, 'registros');
        
        const tbody = document.querySelector('#tabelaSistema tbody');
        const count = document.getElementById('countSistema');
        const countTotal = document.getElementById('countSistemaTotal');
        
        tbody.innerHTML = '';
        count.textContent = this.dadosSistema.length;
        countTotal.textContent = this.dadosSistema.length;

        this.dadosSistema.forEach((item, index) => {
            const row = tbody.insertRow();
            
            // Usar os novos campos da implementação hierárquica
            const data = item.data_lancamento || item.data_movimento || item.data || '-';
            const valor = parseFloat(item.valor || 0);
            const tipo = (item.tipo_lancamento || item.tipo_movimento || item.tipo || 'N/A').toString();
            const descricao = item.descricao_original || item.descricao || 'Sem descrição';
            const status = item.status || 'pendente';
            const refNorm = item.ref_unique_norm || '-';
            const nomeBanco = item.nome_banco || 'N/A';
            const numeroConta = item.numero_conta || 'N/A';
            
            // Classe CSS baseada no status
            const statusClass = status.toLowerCase();
            const statusText = this.formatarStatus(status);
            
            row.innerHTML = `
                <td class="checkbox-cell">
                    <input type="checkbox" data-tipo="sistema" data-index="${index}">
                </td>
                <td>${this.formatarData(data)}</td>
                <td><strong>${nomeBanco}</strong></td>
                <td>${numeroConta}</td>
                <td class="${valor >= 0 ? 'valor-positivo' : 'valor-negativo'}">${this.formatarValor(valor)}</td>
                <td><span class="tipo-${tipo.toLowerCase()}">${tipo}</span></td>
                <td title="${descricao}">${this.truncarTexto(descricao, 30)}</td>
                <td><span class="status-badge status-${statusClass}">${statusText}</span></td>
            `;
            row.dataset.index = index;
            row.dataset.tipo = 'sistema';
            
            // Adicionar classe visual baseada no status
            if (status === 'conciliado') {
                row.classList.add('conciliado');
            }
        });
    }

    renderizarTabelaBanco() {
        console.log('[RENDER] Renderizando tabela banco com', this.dadosBanco.length, 'registros');
        
        const tbody = document.querySelector('#tabelaBanco tbody');
        const count = document.getElementById('countBanco');
        const countTotal = document.getElementById('countBancoTotal');
        
        tbody.innerHTML = '';
        count.textContent = this.dadosBanco.length;
        countTotal.textContent = this.dadosBanco.length;

        this.dadosBanco.forEach((item, index) => {
            const row = tbody.insertRow();
            
            // Usar os novos campos da implementação hierárquica
            const data = item.data || item.data_movimento || '-';
            const valor = parseFloat(item.valor || 0);
            const historico = item.descricao || item.historico || 'Sem histórico';
            const status = item.status || 'pendente';
            const refNorm = item.ref_unique_norm || '-';
            const nomeBanco = item.nome_banco || item.banco || 'N/A';
            const numeroConta = item.numero_conta || item.conta || 'N/A';
            
            // Classe CSS baseada no status
            const statusClass = status.toLowerCase();
            const statusText = this.formatarStatus(status);
            
            row.innerHTML = `
                <td class="checkbox-cell">
                    <input type="checkbox" data-tipo="banco" data-index="${index}">
                </td>
                <td>${this.formatarData(data)}</td>
                <td><strong>${nomeBanco}</strong></td>
                <td>${numeroConta}</td>
                <td class="${valor >= 0 ? 'valor-positivo' : 'valor-negativo'}">${this.formatarValor(valor)}</td>
                <td><span class="tipo-${valor >= 0 ? 'receita' : 'despesa'}">${valor >= 0 ? 'RECEITA' : 'DESPESA'}</span></td>
                <td title="${historico}">${this.truncarTexto(historico, 30)}</td>
                <td><span class="status-badge status-${statusClass}">${statusText}</span></td>
            `;
            row.dataset.index = index;
            row.dataset.tipo = 'banco';
            
            // Adicionar classe visual baseada no status
            if (status === 'conciliado') {
                row.classList.add('conciliado');
            }
        });
    }

    async conciliarAutomaticamente() {
        this.showLoading(true);
        
        try {
            const response = await fetch('/financeiro/conciliacao-lancamentos/api/processar-conciliacao', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-API-Key': window.API_BYPASS_KEY || '$env:API_BYPASS_KEY'
                },
                body: JSON.stringify({})
            });

            const result = await response.json();
            
            if (result.success) {
                // Atualizar dados com a resposta da conciliação hierárquica
                const responseData = result.data;
                
                // Processar dados_aberta (sistema) - estrutura direta sem .dados
                if (responseData.dados_aberta) {
                    this.dadosSistema = responseData.dados_aberta;
                    this.dadosSistemaOriginais = responseData.dados_aberta;
                }
                
                // Processar dados_banco - estrutura direta sem .dados
                if (responseData.dados_banco) {
                    this.dadosBanco = responseData.dados_banco;
                    this.dadosBancoOriginais = responseData.dados_banco;
                }
                
                // Renderizar dados atualizados
                this.renderizarDados();
                this.atualizarResumo();
                
                const stats = responseData.status;
                this.showSuccess(`Conciliação automática concluída! ${stats.conciliados_automatico} conciliações automáticas realizadas.`);
            } else {
                this.showError(result.error || 'Erro na conciliação automática');
            }
        } catch (error) {
            console.error('Erro na conciliação automática:', error);
            this.showError('Erro na conciliação automática: ' + error.message);
        } finally {
            this.showLoading(false);
        }
    }

    // Funções auxiliares
    formatarStatus(status) {
        const statusMap = {
            'pendente': 'Pendente',
            'conciliado': 'Conciliado',
            'duplicado': 'Duplicado',
            'divergente': 'Divergente'
        };
        return statusMap[status.toLowerCase()] || status;
    }

    formatarData(data) {
        if (!data || data === '-') return '-';
        
        try {
            // Se já está no formato DD/MM/YYYY, retorna como está
            if (data.includes('/')) {
                return data;
            }
            
            // Se está no formato YYYY-MM-DD, converte para DD/MM/YYYY
            if (data.includes('-')) {
                const [ano, mes, dia] = data.split('-');
                return `${dia}/${mes}/${ano}`;
            }
            
            return data;
        } catch (error) {
            return data;
        }
    }

    formatarValor(valor) {
        return new Intl.NumberFormat('pt-BR', {
            style: 'currency',
            currency: 'BRL'
        }).format(valor);
    }

    truncarTexto(texto, limite) {
        if (!texto) return '';
        return texto.length > limite ? texto.substring(0, limite) + '...' : texto;
    }

    // Métodos de UI
    showLoading(show) {
        const overlay = document.getElementById('loading-overlay');
        overlay.style.display = show ? 'flex' : 'none';
    }

    showUploadProgress(show) {
        // Implementar se necessário
    }

    showUploadProgressArquivo(show) {
        const progressContainer = document.querySelector('.upload-progress-arquivo');
        if (progressContainer) {
            progressContainer.style.display = show ? 'block' : 'none';
            if (show) {
                const progressBar = progressContainer.querySelector('.progress-bar');
                if (progressBar) {
                    // Simular progresso
                    let progress = 0;
                    const interval = setInterval(() => {
                        progress += 10;
                        progressBar.style.width = progress + '%';
                        if (progress >= 90) {
                            clearInterval(interval);
                        }
                    }, 200);
                }
            }
        }
    }

    showSections(sections) {
        sections.forEach(sectionId => {
            const section = document.getElementById(sectionId);
            if (section) {
                section.style.display = 'block';
            }
        });
    }

    showSuccess(message) {
        // Implementar notificação de sucesso
        console.log('Sucesso:', message);
        alert('Sucesso: ' + message);
    }

    showError(message) {
        // Implementar notificação de erro
        console.error('Erro:', message);
        alert('Erro: ' + message);
    }

    atualizarResumo() {
        // Implementar atualização do resumo
        console.log('Atualizando resumo...');
    }

    // Métodos aprimorados para funcionalidades implementadas
    conciliarManualmente() {
        this.showError('Use a funcionalidade "Conciliar Selecionados" para conciliação manual');
    }

    exportarRelatorio() {
        this.showError('Exportação de relatório ainda não implementada');
    }

    limparTudo() {
        if (confirm('Tem certeza que deseja limpar todos os dados?')) {
            this.dadosSistema = [];
            this.dadosBanco = [];
            this.dadosSistemaOriginais = [];
            this.dadosBancoOriginais = [];
            this.selecionadosSistema.clear();
            this.selecionadosBanco.clear();
            this.conciliacoes = [];
            this.renderizarDados();
            this.atualizarSomatorio();
            this.showSections([]);
            this.showSuccess('Dados limpos com sucesso!');
        }
    }

    // Funções de seleção múltipla
    handleCheckboxChange(checkbox) {
        const tipo = checkbox.dataset.tipo;
        const index = parseInt(checkbox.dataset.index);
        const row = checkbox.closest('tr');
        
        if (checkbox.checked) {
            if (tipo === 'sistema') {
                this.selecionadosSistema.add(index);
            } else {
                this.selecionadosBanco.add(index);
            }
            row.classList.add('selected-multiple');
            row.classList.add('selection-highlight');
        } else {
            if (tipo === 'sistema') {
                this.selecionadosSistema.delete(index);
            } else {
                this.selecionadosBanco.delete(index);
            }
            row.classList.remove('selected-multiple');
        }
        
        this.atualizarContadores();
        this.atualizarSomatorio();
        this.atualizarBotoesConciliacao();
        
        // Remove a animação após um tempo
        setTimeout(() => {
            row.classList.remove('selection-highlight');
        }, 600);
    }

    toggleSelectAllSistema() {
        const checkbox = document.getElementById('selectAllSistema');
        const checkboxes = document.querySelectorAll('#tabelaSistema input[type="checkbox"][data-tipo="sistema"]');
        
        checkboxes.forEach(cb => {
            cb.checked = checkbox.checked;
            this.handleCheckboxChange(cb);
        });
    }

    toggleSelectAllBanco() {
        const checkbox = document.getElementById('selectAllBanco');
        const checkboxes = document.querySelectorAll('#tabelaBanco input[type="checkbox"][data-tipo="banco"]');
        
        checkboxes.forEach(cb => {
            cb.checked = checkbox.checked;
            this.handleCheckboxChange(cb);
        });
    }

    atualizarContadores() {
        // Atualizar contadores de selecionados
        document.getElementById('countSistemaSelecionados').textContent = this.selecionadosSistema.size;
        document.getElementById('countBancoSelecionados').textContent = this.selecionadosBanco.size;
    }

    atualizarSomatorio() {
        const sistemaValor = this.calcularSomatorio('sistema');
        const bancoValor = this.calcularSomatorio('banco');
        const diferenca = sistemaValor - bancoValor;
        
        // Atualizar contadores
        document.getElementById('somatorioSistemaCount').textContent = `${this.selecionadosSistema.size} itens`;
        document.getElementById('somatorioBancoCount').textContent = `${this.selecionadosBanco.size} itens`;
        
        // Atualizar valores
        const sistemaValorEl = document.getElementById('somatorioSistemaValor');
        const bancoValorEl = document.getElementById('somatorioBancoValor');
        const diferencaEl = document.getElementById('somatorioDiferenca');
        
        sistemaValorEl.textContent = this.formatarValor(sistemaValor);
        sistemaValorEl.className = 'somatorio-valor ' + (sistemaValor >= 0 ? 'positivo' : 'negativo');
        
        bancoValorEl.textContent = this.formatarValor(bancoValor);
        bancoValorEl.className = 'somatorio-valor ' + (bancoValor >= 0 ? 'positivo' : 'negativo');
        
        diferencaEl.textContent = this.formatarValor(diferenca);
        diferencaEl.className = 'somatorio-valor ' + (diferenca >= 0 ? 'positivo' : 'negativo');
        
        // Mostrar/ocultar seção de somatório
        const somatorioSection = document.getElementById('somatorioSection');
        const temSelecao = this.selecionadosSistema.size > 0 || this.selecionadosBanco.size > 0;
        somatorioSection.style.display = temSelecao ? 'block' : 'none';
    }

    calcularSomatorio(tipo) {
        let total = 0;
        
        if (tipo === 'sistema') {
            for (let index of this.selecionadosSistema) {
                const item = this.dadosSistema[index];
                if (item) {
                    total += parseFloat(item.valor || 0);
                }
            }
        } else {
            for (let index of this.selecionadosBanco) {
                const item = this.dadosBanco[index];
                if (item) {
                    total += parseFloat(item.valor || 0);
                }
            }
        }
        
        return total;
    }

    atualizarBotoesConciliacao() {
        const btnConciliarSelecionados = document.getElementById('btnConciliarSelecionados');
        const temSelecaoSistema = this.selecionadosSistema.size > 0;
        const temSelecaoBanco = this.selecionadosBanco.size > 0;
        
        // Habilitar botão apenas se tiver seleção em ambos os lados
        btnConciliarSelecionados.disabled = !(temSelecaoSistema && temSelecaoBanco);
        
        // Atualizar texto do botão baseado no tipo de conciliação
        let tipoConciliacao = '';
        if (temSelecaoSistema && temSelecaoBanco) {
            if (this.selecionadosSistema.size === 1 && this.selecionadosBanco.size === 1) {
                tipoConciliacao = ' (1:1)';
            } else if (this.selecionadosSistema.size === 1) {
                tipoConciliacao = ` (1:${this.selecionadosBanco.size})`;
            } else if (this.selecionadosBanco.size === 1) {
                tipoConciliacao = ` (${this.selecionadosSistema.size}:1)`;
            } else {
                tipoConciliacao = ` (${this.selecionadosSistema.size}:${this.selecionadosBanco.size})`;
            }
        }
        
        btnConciliarSelecionados.innerHTML = `
            <i class="mdi mdi-link"></i>
            Conciliar Selecionados${tipoConciliacao}
        `;
    }

    conciliarSelecionados() {
        if (this.selecionadosSistema.size === 0 || this.selecionadosBanco.size === 0) {
            this.showError('Selecione pelo menos um item de cada lado para conciliar');
            return;
        }
        
        const sistemaIds = Array.from(this.selecionadosSistema);
        const bancoIds = Array.from(this.selecionadosBanco);
        
        this.showLoading(true);
        
        // Simular conciliação (substituir por chamada real da API)
        setTimeout(() => {
            this.processarConciliacaoSelecionada(sistemaIds, bancoIds);
            this.showLoading(false);
        }, 1000);
    }

    processarConciliacaoSelecionada(sistemaIds, bancoIds) {
        // Marcar itens como conciliados
        sistemaIds.forEach(index => {
            if (this.dadosSistema[index]) {
                this.dadosSistema[index].status = 'conciliado';
            }
        });
        
        bancoIds.forEach(index => {
            if (this.dadosBanco[index]) {
                this.dadosBanco[index].status = 'conciliado';
            }
        });
        
        // Determinar tipo de conciliação
        let tipoConciliacao = '';
        if (sistemaIds.length === 1 && bancoIds.length === 1) {
            tipoConciliacao = '1:1';
        } else if (sistemaIds.length === 1) {
            tipoConciliacao = '1:N';
        } else {
            tipoConciliacao = 'N:1';
        }
        
        // Limpar seleções
        this.limparSelecao();
        
        // Re-renderizar tabelas com animação
        this.renderizarDados();
        
        // Remover itens conciliados após animação
        setTimeout(() => {
            this.removerItensConciliados();
        }, 1000);
        
        this.showSuccess(`Conciliação ${tipoConciliacao} realizada com sucesso! ${sistemaIds.length} item(ns) do sistema e ${bancoIds.length} item(ns) do banco foram conciliados.`);
    }

    removerItensConciliados() {
        // Aplicar animação de fade out
        document.querySelectorAll('.conciliado').forEach(row => {
            row.classList.add('fade-out');
        });
        
        // Remover itens após animação
        setTimeout(() => {
            this.dadosSistema = this.dadosSistema.filter(item => item.status !== 'conciliado');
            this.dadosBanco = this.dadosBanco.filter(item => item.status !== 'conciliado');
            this.renderizarDados();
            this.atualizarResumo();
        }, 500);
    }

    limparSelecao() {
        this.selecionadosSistema.clear();
        this.selecionadosBanco.clear();
        
        // Desmarcar todos os checkboxes
        document.querySelectorAll('input[type="checkbox"]').forEach(cb => {
            cb.checked = false;
        });
        
        // Remover classes de seleção
        document.querySelectorAll('.selected-multiple').forEach(row => {
            row.classList.remove('selected-multiple');
        });
        
        this.atualizarContadores();
        this.atualizarSomatorio();
        this.atualizarBotoesConciliacao();
    }

    updateManualConciliationButton() {
        // Mantido para compatibilidade, funcionalidade movida para atualizarBotoesConciliacao
        this.atualizarBotoesConciliacao();
    }
}

// Inicializar quando o DOM estiver carregado
document.addEventListener('DOMContentLoaded', function() {
    window.conciliacaoBancaria = new ConciliacaoBancaria();
    
    // Event listeners adicionais para checkboxes individuais
    document.addEventListener('change', function(e) {
        if (e.target.type === 'checkbox' && e.target.dataset.tipo) {
            window.conciliacaoBancaria.updateManualConciliationButton();
        }
    });
});