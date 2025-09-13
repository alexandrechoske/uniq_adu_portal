// JavaScript para Conciliação Bancária
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
            this.dadosSistema = result.dados_sistema || [];
            this.dadosBanco = result.dados_banco || [];
            
            this.showStatus(result.status);
            this.renderizarDados();
            this.showSections(['statusSection', 'dadosSection', 'resumoSection']);
            this.atualizarResumo();
            
            this.showSuccess(`Arquivos processados com sucesso! ${this.dadosSistema.length} lançamentos do sistema e ${this.dadosBanco.length} do banco encontrados.`);
        } else {
            this.showError(result.message || 'Erro ao processar arquivos');
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
            
            // Garantir que os campos existam e tenham valores padrão
            const data = item.data_lancamento || item.data_movimento || item.data || '-';
            const valor = parseFloat(item.valor || 0);
            const tipo = (item.tipo_lancamento || item.tipo_movimento || item.tipo || 'N/A').toString();
            const descricao = item.descricao || 'Sem descrição';
            
            row.innerHTML = `
                <td><input type="checkbox" data-tipo="sistema" data-index="${index}"></td>
                <td>${this.formatarData(data)}</td>
                <td class="${valor >= 0 ? 'valor-positivo' : 'valor-negativo'}">${this.formatarValor(valor)}</td>
                <td><span class="tipo-${tipo.toLowerCase()}">${tipo}</span></td>
                <td title="${descricao}">${this.truncarTexto(descricao, 50)}</td>
                <td><span class="status-badge status-pendente">Pendente</span></td>
            `;
            row.dataset.index = index;
            row.dataset.tipo = 'sistema';
        });
    }

    renderizarTabelaBanco() {
        const tbody = document.querySelector('#tabelaBanco tbody');
        const count = document.getElementById('countBanco');
        
        tbody.innerHTML = '';
        count.textContent = this.dadosBanco.length;

        this.dadosBanco.forEach((item, index) => {
            const row = tbody.insertRow();
            
            // Garantir que os campos existam e tenham valores padrão
            const data = item.data || item.data_movimento || '-';
            const valor = parseFloat(item.valor || 0);
            const historico = item.historico || item.descricao || 'Sem histórico';
            
            row.innerHTML = `
                <td><input type="checkbox" data-tipo="banco" data-index="${index}"></td>
                <td>${this.formatarData(data)}</td>
                <td class="${valor >= 0 ? 'valor-positivo' : 'valor-negativo'}">${this.formatarValor(valor)}</td>
                <td><span class="tipo-${valor >= 0 ? 'receita' : 'despesa'}">${valor >= 0 ? 'RECEITA' : 'DESPESA'}</span></td>
                <td title="${historico}">${this.truncarTexto(historico, 50)}</td>
                <td><span class="status-badge status-pendente">Pendente</span></td>
            `;
            row.dataset.index = index;
            row.dataset.tipo = 'banco';
        });
    }

    async conciliarAutomaticamente() {
        this.showLoading(true);
        
        try {
            const response = await fetch('/financeiro/conciliacao-lancamentos/conciliar_automatico', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-API-Key': window.API_BYPASS_KEY || '$env:API_BYPASS_KEY'
                },
                body: JSON.stringify({
                    dados_sistema: this.dadosSistema,
                    dados_banco: this.dadosBanco
                })
            });

            const result = await response.json();
            
            if (result.success) {
                this.conciliacoes = result.conciliacoes;
                this.aplicarConciliacoes();
                this.atualizarResumo();
                this.showSuccess(`Conciliação automática concluída! ${result.conciliacoes.length} matches encontrados.`);
            } else {
                this.showError(result.message || 'Erro na conciliação automática');
            }
        } catch (error) {
            console.error('Erro na conciliação automática:', error);
            this.showError('Erro na conciliação automática: ' + error.message);
        } finally {
            this.showLoading(false);
        }
    }

    aplicarConciliacoes() {
        // Resetar status
        document.querySelectorAll('#tabelaSistema tbody tr').forEach(row => {
            row.classList.remove('conciliado');
            row.querySelector('.status-badge').className = 'status-badge status-pendente';
            row.querySelector('.status-badge').textContent = 'Pendente';
        });

        document.querySelectorAll('#tabelaBanco tbody tr').forEach(row => {
            row.classList.remove('conciliado');
            row.querySelector('.status-badge').className = 'status-badge status-pendente';
            row.querySelector('.status-badge').textContent = 'Pendente';
        });

        // Aplicar conciliações
        this.conciliacoes.forEach(conciliacao => {
            const rowSistema = document.querySelector(`#tabelaSistema tbody tr[data-index="${conciliacao.index_sistema}"]`);
            const rowBanco = document.querySelector(`#tabelaBanco tbody tr[data-index="${conciliacao.index_banco}"]`);

            if (rowSistema && rowBanco) {
                rowSistema.classList.add('conciliado');
                rowBanco.classList.add('conciliado');

                const statusSistema = rowSistema.querySelector('.status-badge');
                const statusBanco = rowBanco.querySelector('.status-badge');

                statusSistema.className = 'status-badge status-conciliado';
                statusSistema.textContent = 'Conciliado';
                statusBanco.className = 'status-badge status-conciliado';
                statusBanco.textContent = 'Conciliado';
            }
        });
    }

    conciliarManualmente() {
        const selectedSistema = this.getSelectedItems('sistema');
        const selectedBanco = this.getSelectedItems('banco');

        if (selectedSistema.length === 0 || selectedBanco.length === 0) {
            this.showWarning('Selecione pelo menos um item de cada tabela para conciliar manualmente.');
            return;
        }

        if (selectedSistema.length !== selectedBanco.length) {
            this.showWarning('O número de itens selecionados deve ser igual em ambas as tabelas.');
            return;
        }

        // Criar conciliações manuais
        for (let i = 0; i < selectedSistema.length; i++) {
            const conciliacao = {
                index_sistema: selectedSistema[i],
                index_banco: selectedBanco[i],
                tipo: 'manual',
                confianca: 100
            };
            this.conciliacoes.push(conciliacao);
        }

        this.aplicarConciliacoes();
        this.atualizarResumo();
        this.showSuccess(`${selectedSistema.length} conciliação(ões) manual(is) realizada(s) com sucesso!`);

        // Desmarcar checkboxes
        this.clearSelections();
    }

    getSelectedItems(tipo) {
        const checkboxes = document.querySelectorAll(`input[data-tipo="${tipo}"]:checked`);
        return Array.from(checkboxes).map(cb => parseInt(cb.dataset.index));
    }

    clearSelections() {
        document.querySelectorAll('input[type="checkbox"]').forEach(cb => cb.checked = false);
        document.getElementById('btnConciliarManual').disabled = true;
    }

    toggleSelectAllSistema() {
        const selectAll = document.getElementById('selectAllSistema');
        const checkboxes = document.querySelectorAll('input[data-tipo="sistema"]');
        
        checkboxes.forEach(cb => cb.checked = selectAll.checked);
        this.updateManualConciliationButton();
    }

    toggleSelectAllBanco() {
        const selectAll = document.getElementById('selectAllBanco');
        const checkboxes = document.querySelectorAll('input[data-tipo="banco"]');
        
        checkboxes.forEach(cb => cb.checked = selectAll.checked);
        this.updateManualConciliationButton();
    }

    updateManualConciliationButton() {
        const selectedSistema = this.getSelectedItems('sistema');
        const selectedBanco = this.getSelectedItems('banco');
        const btnManual = document.getElementById('btnConciliarManual');
        
        btnManual.disabled = selectedSistema.length === 0 || selectedBanco.length === 0;
    }

    atualizarResumo() {
        const totalSistema = this.dadosSistema.length;
        const totalBanco = this.dadosBanco.length;
        const conciliados = this.conciliacoes.length;
        const pendentes = Math.max(totalSistema, totalBanco) - conciliados;
        const divergencias = Math.abs(totalSistema - totalBanco);
        const percentual = totalSistema > 0 ? Math.round((conciliados / totalSistema) * 100) : 0;

        document.getElementById('statConciliados').textContent = conciliados;
        document.getElementById('statPendentes').textContent = pendentes;
        document.getElementById('statDivergencias').textContent = divergencias;
        document.getElementById('statPercentual').textContent = percentual + '%';

        // Habilitar botão de exportar se houver dados
        document.getElementById('btnExportarRelatorio').disabled = conciliados === 0;
    }

    async exportarRelatorio() {
        try {
            const response = await fetch('/financeiro/conciliacao-lancamentos/exportar', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-API-Key': window.API_BYPASS_KEY || '$env:API_BYPASS_KEY'
                },
                body: JSON.stringify({
                    dados_sistema: this.dadosSistema,
                    dados_banco: this.dadosBanco,
                    conciliacoes: this.conciliacoes
                })
            });

            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `conciliacao_bancaria_${new Date().toISOString().split('T')[0]}.xlsx`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
                this.showSuccess('Relatório exportado com sucesso!');
            } else {
                throw new Error('Erro ao gerar relatório');
            }
        } catch (error) {
            console.error('Erro na exportação:', error);
            this.showError('Erro ao exportar relatório: ' + error.message);
        }
    }

    limparTudo() {
        if (confirm('Tem certeza que deseja limpar todos os dados? Esta ação não pode ser desfeita.')) {
            this.dadosSistema = [];
            this.dadosBanco = [];
            this.conciliacoes = [];
            
            document.getElementById('uploadForm').reset();
            this.validateForm();
            this.hideSections(['statusSection', 'dadosSection', 'resumoSection']);
            
            this.showInfo('Dados limpos com sucesso!');
        }
    }

    // Métodos utilitários
    formatarData(data) {
        if (!data) return '';
        const date = new Date(data);
        return date.toLocaleDateString('pt-BR');
    }

    formatarValor(valor) {
        if (valor === null || valor === undefined) return '';
        return new Intl.NumberFormat('pt-BR', {
            style: 'currency',
            currency: 'BRL'
        }).format(Math.abs(valor));
    }

    truncarTexto(texto, limite) {
        if (!texto) return '';
        return texto.length > limite ? texto.substring(0, limite) + '...' : texto;
    }

    showSections(sections) {
        sections.forEach(sectionId => {
            const section = document.getElementById(sectionId);
            if (section) {
                section.style.display = 'block';
                section.classList.add('fade-in');
            }
        });
    }

    hideSections(sections) {
        sections.forEach(sectionId => {
            const section = document.getElementById(sectionId);
            if (section) {
                section.style.display = 'none';
            }
        });
    }

    showLoading(show) {
        const modalElement = document.getElementById('loadingModal');
        if (modalElement) {
            if (show) {
                const modal = new bootstrap.Modal(modalElement);
                modal.show();
            } else {
                // Garantir que o modal seja fechado, mesmo se já existir uma instância
                const existingModal = bootstrap.Modal.getInstance(modalElement);
                if (existingModal) {
                    existingModal.hide();
                } else {
                    const modal = new bootstrap.Modal(modalElement);
                    modal.hide();
                }
                // Forçar remoção do backdrop se ainda estiver presente
                setTimeout(() => {
                    document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
                        backdrop.remove();
                    });
                    document.body.classList.remove('modal-open');
                    document.body.style.removeProperty('overflow');
                    document.body.style.removeProperty('padding-right');
                }, 100);
            }
        }
    }

    showUploadProgress(show) {
        const progress = document.querySelector('.upload-progress');
        if (show) {
            progress.style.display = 'block';
            let width = 0;
            const interval = setInterval(() => {
                width += 10;
                document.querySelector('.progress-bar').style.width = width + '%';
                if (width >= 90) {
                    clearInterval(interval);
                }
            }, 200);
        } else {
            progress.style.display = 'none';
            document.querySelector('.progress-bar').style.width = '0%';
        }
    }

    showSuccess(message) {
        this.showToast(message, 'success');
    }

    showError(message) {
        this.showToast(message, 'error');
    }

    showWarning(message) {
        this.showToast(message, 'warning');
    }

    showInfo(message) {
        this.showToast(message, 'info');
    }

    showToast(message, type) {
        // Implementação básica - pode ser melhorada com biblioteca de toast
        const toast = document.createElement('div');
        toast.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed`;
        toast.style.cssText = 'top: 80px; right: 20px; z-index: 9999; min-width: 300px;';
        toast.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 5000);
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
