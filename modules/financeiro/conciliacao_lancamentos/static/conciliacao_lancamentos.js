// JavaScript para Conciliação Bancária - Versão corrigida
class ConciliacaoBancaria {
    constructor() {
        this.dadosSistema = [];
        this.dadosBanco = [];
        this.conciliacoes = [];
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupFormValidation();
    }

    setupEventListeners() {
        // Eventos do formulário de upload
        document.getElementById('banco').addEventListener('change', this.validateForm.bind(this));
        document.getElementById('arquivo_extrato').addEventListener('change', this.validateForm.bind(this));
        document.getElementById('periodo').addEventListener('change', this.toggleDataPersonalizada.bind(this));
        document.getElementById('uploadForm').addEventListener('submit', this.handleUpload.bind(this));

        // Eventos dos botões de ação
        document.getElementById('btnConciliarAuto').addEventListener('click', this.conciliarAutomaticamente.bind(this));
        document.getElementById('btnConciliarManual').addEventListener('click', this.conciliarManualmente.bind(this));
        document.getElementById('btnExportarRelatorio').addEventListener('click', this.exportarRelatorio.bind(this));
        document.getElementById('btnLimparTudo').addEventListener('click', this.limparTudo.bind(this));

        // Eventos dos checkboxes "selecionar todos"
        document.getElementById('selectAllSistema').addEventListener('change', this.toggleSelectAllSistema.bind(this));
        document.getElementById('selectAllBanco').addEventListener('change', this.toggleSelectAllBanco.bind(this));
    }

    setupFormValidation() {
        this.validateForm();
    }

    validateForm() {
        const banco = document.getElementById('banco').value;
        const arquivo = document.getElementById('arquivo_extrato').files[0];
        const btnUpload = document.getElementById('btnUpload');

        const isValid = banco && arquivo;
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

    async handleUpload(event) {
        event.preventDefault();
        
        const formData = new FormData();
        const banco = document.getElementById('banco').value;
        const arquivo = document.getElementById('arquivo_extrato').files[0];
        const periodo = document.getElementById('periodo').value;

        formData.append('banco', banco);
        formData.append('arquivo_extrato', arquivo);
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
            const response = await fetch('/financeiro/conciliacao-lancamentos/processar', {
                method: 'POST',
                headers: {
                    'X-API-Key': window.API_BYPASS_KEY || '$env:API_BYPASS_KEY'
                },
                body: formData
            });

            if (!response.ok) {
                throw new Error(`Erro HTTP: ${response.status}`);
            }

            const result = await response.json();
            this.processarResultado(result);

        } catch (error) {
            console.error('Erro no upload:', error);
            this.showError('Erro ao processar arquivos: ' + error.message);
        } finally {
            this.showLoading(false);
            this.showUploadProgress(false);
        }
    }

    processarResultado(result) {
        if (result.success) {
            // Nova estrutura: result tem dados_aberta e dados_banco
            this.dadosSistema = result.dados_aberta || [];
            this.dadosBanco = result.dados_banco || [];
            
            this.showStatus(result.status);
            this.renderizarDados();
            this.showSections(['statusSection', 'dadosSection', 'resumoSection']);
            this.atualizarResumo();
            
            this.showSuccess(`Arquivos processados com sucesso! ${this.dadosSistema.length} lançamentos do sistema e ${this.dadosBanco.length} do banco encontrados.`);
        } else {
            this.showError(result.message || result.error || 'Erro ao processar arquivos');
        }
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
        const tbody = document.querySelector('#tabelaSistema tbody');
        const count = document.getElementById('countSistema');
        
        tbody.innerHTML = '';
        count.textContent = this.dadosSistema.length;

        this.dadosSistema.forEach((item, index) => {
            const row = tbody.insertRow();
            
            // Usar os novos campos da implementação hierárquica
            const data = item.data_lancamento || item.data_movimento || item.data || '-';
            const valor = parseFloat(item.valor || 0);
            const tipo = (item.tipo_lancamento || item.tipo_movimento || item.tipo || 'N/A').toString();
            const descricao = item.descricao_original || item.descricao || 'Sem descrição';
            const status = item.status || 'pendente';
            const refNorm = item.ref_unique_norm || '-';
            
            // Classe CSS baseada no status
            const statusClass = status.toLowerCase();
            const statusText = this.formatarStatus(status);
            
            row.innerHTML = `
                <td><input type="checkbox" data-tipo="sistema" data-index="${index}"></td>
                <td>${this.formatarData(data)}</td>
                <td class="${valor >= 0 ? 'valor-positivo' : 'valor-negativo'}">${this.formatarValor(valor)}</td>
                <td><span class="tipo-${tipo.toLowerCase()}">${tipo}</span></td>
                <td title="${descricao}">${this.truncarTexto(descricao, 50)}</td>
                <td><span class="status-badge status-${statusClass}">${statusText}</span></td>
                <td><small class="text-muted">${refNorm}</small></td>
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
        const tbody = document.querySelector('#tabelaBanco tbody');
        const count = document.getElementById('countBanco');
        
        tbody.innerHTML = '';
        count.textContent = this.dadosBanco.length;

        this.dadosBanco.forEach((item, index) => {
            const row = tbody.insertRow();
            
            // Usar os novos campos da implementação hierárquica
            const data = item.data || item.data_movimento || '-';
            const valor = parseFloat(item.valor || 0);
            const historico = item.descricao || item.historico || 'Sem histórico';
            const status = item.status || 'pendente';
            const refNorm = item.ref_unique_norm || '-';
            
            // Classe CSS baseada no status
            const statusClass = status.toLowerCase();
            const statusText = this.formatarStatus(status);
            
            row.innerHTML = `
                <td><input type="checkbox" data-tipo="banco" data-index="${index}"></td>
                <td>${this.formatarData(data)}</td>
                <td class="${valor >= 0 ? 'valor-positivo' : 'valor-negativo'}">${this.formatarValor(valor)}</td>
                <td><span class="tipo-${valor >= 0 ? 'receita' : 'despesa'}">${valor >= 0 ? 'RECEITA' : 'DESPESA'}</span></td>
                <td title="${historico}">${this.truncarTexto(historico, 50)}</td>
                <td><span class="status-badge status-${statusClass}">${statusText}</span></td>
                <td><small class="text-muted">${refNorm}</small></td>
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
                
                // Processar dados_aberta (sistema)
                if (responseData.dados_aberta && responseData.dados_aberta.dados) {
                    this.dadosSistema = responseData.dados_aberta.dados;
                }
                
                // Processar dados_banco
                if (responseData.dados_banco && responseData.dados_banco.dados) {
                    this.dadosBanco = responseData.dados_banco.dados;
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

    // Métodos stubs para funcionalidades não implementadas ainda
    conciliarManualmente() {
        this.showError('Conciliação manual ainda não implementada');
    }

    exportarRelatorio() {
        this.showError('Exportação de relatório ainda não implementada');
    }

    limparTudo() {
        if (confirm('Tem certeza que deseja limpar todos os dados?')) {
            this.dadosSistema = [];
            this.dadosBanco = [];
            this.conciliacoes = [];
            this.renderizarDados();
            this.showSuccess('Dados limpos com sucesso!');
        }
    }

    toggleSelectAllSistema() {
        // Implementar seleção de todos os itens do sistema
    }

    toggleSelectAllBanco() {
        // Implementar seleção de todos os itens do banco
    }

    updateManualConciliationButton() {
        // Implementar atualização do botão de conciliação manual
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