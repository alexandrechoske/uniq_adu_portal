/**
 * Conciliação Bancária V2 - Sistema de Abas com Estado Local
 * Gerenciamento completo de sessão no frontend
 */

// ========================================
// ESTADO GLOBAL DA APLICAÇÃO
// ========================================
const AppState = {
    // Dados da sessão
    lancamentosSistema: [],      // Todos os lançamentos do sistema (originais)
    lancamentosBanco: [],         // Todos os lançamentos do banco (originais)
    
    // Dados filtrados/pendentes (atualizados dinamicamente)
    sistemasPendentes: [],
    bancosPendentes: [],
    
    // Conciliações realizadas (grupos)
    conciliacoes: [],
    statusResumo: {},
    
    // Seleções atuais
    sistemasSelecionados: new Set(),
    bancosSelecionados: new Set(),
    
    // Controle de UI
    abaAtiva: 'conciliar',
    arquivosCarregados: [],
    ordenacaoSistema: { campo: 'data', ordem: 'desc' },
    ordenacaoBanco: { campo: 'data', ordem: 'desc' },
    buscaSistema: '',
    buscaBanco: '',
    filtroBanco: ''
};

// ========================================
// INICIALIZAÇÃO
// ========================================
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Inicializando Conciliação V2');
    inicializarEventos();
    inicializarDragAndDrop();
    inicializarOrdenacao();
});

function inicializarEventos() {
    // Navegação de abas
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => trocarAba(btn.dataset.tab));
    });
    
    // Upload de arquivos
    document.getElementById('arquivoBancario').addEventListener('change', handleFileSelect);
    document.getElementById('uploadForm').addEventListener('submit', processarArquivos);
    
    // Busca e filtros
    document.getElementById('searchSistema').addEventListener('input', filtrarTabelaSistema);
    document.getElementById('searchBanco').addEventListener('input', filtrarTabelaBanco);
    document.getElementById('filtroBanco').addEventListener('change', filtrarTabelaBanco);
    
    // Checkboxes
    document.getElementById('checkAllSistema').addEventListener('change', toggleSelectAllSistema);
    document.getElementById('checkAllBanco').addEventListener('change', toggleSelectAllBanco);
    
    // Conciliação manual
    document.getElementById('btnConciliarManual').addEventListener('click', conciliarManual);
    
    // Filtros da aba Conciliados
    document.getElementById('filtroTipoConciliacao').addEventListener('change', filtrarConciliados);
    document.getElementById('filtroBancoConciliados').addEventListener('change', filtrarConciliados);
    document.getElementById('searchConciliados').addEventListener('input', filtrarConciliados);
    
    // Limpar sessão
    document.getElementById('btnLimparSessao').addEventListener('click', limparSessao);
}

// ========================================
// DRAG AND DROP
// ========================================
function inicializarDragAndDrop() {
    const zone = document.getElementById('uploadZone');
    const btnSelect = document.getElementById('btnSelecionarArquivos');
    
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        zone.addEventListener(eventName, preventDefaults, false);
    });
    
    ['dragenter', 'dragover'].forEach(eventName => {
        zone.addEventListener(eventName, () => zone.classList.add('drag-over'), false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        zone.addEventListener(eventName, () => zone.classList.remove('drag-over'), false);
    });
    
    zone.addEventListener('drop', handleDrop, false);
    zone.addEventListener('click', () => document.getElementById('arquivoBancario').click());

    if (btnSelect) {
        btnSelect.addEventListener('click', (event) => {
            event.preventDefault();
            event.stopPropagation();
            document.getElementById('arquivoBancario').click();
        });
    }
}

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

function handleDrop(e) {
    const dt = e.dataTransfer;
    const files = dt.files;
    document.getElementById('arquivoBancario').files = files;
    handleFileSelect({ target: { files } });
}

function handleFileSelect(e) {
    const files = Array.from(e.target.files);
    AppState.arquivosCarregados = files;
    
    if (files.length > 0) {
        exibirArquivosSelecionados(files);
        document.getElementById('btnProcessar').disabled = false;
    }
}

function exibirArquivosSelecionados(files) {
    const filesList = document.getElementById('filesList');
    const placeholder = document.querySelector('.upload-placeholder');
    
    placeholder.style.display = 'none';
    filesList.style.display = 'block';
    filesList.innerHTML = files.map(f => `
        <div class="file-item">
            <i class="mdi mdi-file-document"></i>
            <span class="file-name">${f.name}</span>
            <span class="file-size">${formatBytes(f.size)}</span>
        </div>
    `).join('');
}

function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

// ========================================
// PROCESSAMENTO E UPLOAD
// ========================================
async function processarArquivos(e) {
    e.preventDefault();
    
    if (AppState.arquivosCarregados.length === 0) {
        mostrarNotificacao('Selecione ao menos um arquivo bancário antes de processar.', 'info');
        return;
    }

    prepararNovaSessaoProcessamento();

    const periodoSelecionado = document.getElementById('periodo_sistema').value;
    const bancoSelecionado = document.getElementById('banco_origem').value;
    const periodo = calcularPeriodoSistema(periodoSelecionado);

    const formData = new FormData();
    AppState.arquivosCarregados.forEach(file => {
        formData.append('arquivo_bancario', file);
    });
    formData.append('banco_origem', bancoSelecionado);
    formData.append('periodo_sistema', periodoSelecionado);
    
    try {
        mostrarLoading('Carregando lançamentos do sistema...');

        const params = new URLSearchParams({
            data_inicio: periodo.inicio,
            data_fim: periodo.fim
        });

        if (bancoSelecionado && bancoSelecionado !== 'auto') {
            params.append('banco', bancoSelecionado);
        }

        const sistemaResp = await fetch(`/financeiro/conciliacao-lancamentos/api/movimentos-sistema?${params.toString()}`);
        const sistemaData = await sistemaResp.json();

        if (!sistemaResp.ok || !sistemaData.success) {
            throw new Error(sistemaData.error || 'Erro ao carregar lançamentos do sistema');
        }

        const dadosSistema = Array.isArray(sistemaData.data) ? sistemaData.data : [];
        const dadosSistemaNormalizados = dadosSistema
            .map(normalizarMovimentoSistema)
            .filter(Boolean);

        if (dadosSistemaNormalizados.length === 0) {
            mostrarNotificacao('Nenhum lançamento do sistema encontrado para o período selecionado.', 'info');
            esconderLoading();
            return;
        }

        AppState.lancamentosSistema = dadosSistemaNormalizados;
        AppState.sistemasPendentes = [...AppState.lancamentosSistema];

        mostrarLoading('Enviando arquivos bancários...');
        
        // 1. Upload dos arquivos
        const uploadResp = await fetch('/financeiro/conciliacao-lancamentos/upload-arquivo', {
            method: 'POST',
            body: formData
        });
        
        if (!uploadResp.ok) throw new Error('Erro no upload');
        const uploadData = await uploadResp.json();
        if (uploadData && uploadData.success === false) {
            throw new Error(uploadData.error || uploadData.message || 'Erro no upload');
        }
        if (uploadData && uploadData.data && Array.isArray(uploadData.data.lancamentos)) {
            const dadosBancoNormalizados = uploadData.data.lancamentos
                .map(normalizarMovimentoBanco)
                .filter(Boolean);
            AppState.lancamentosBanco = dadosBancoNormalizados;
            AppState.bancosPendentes = [...dadosBancoNormalizados];
        }
        
        mostrarLoading('Processando conciliação automática...');
        
        // 2. Conciliação automática
        const conciliarResp = await fetch('/financeiro/conciliacao-lancamentos/api/processar-conciliacao', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json'
            }
        });
        
        if (!conciliarResp.ok) throw new Error('Erro na conciliação');
        const conciliarData = await conciliarResp.json();
        if (!conciliarData.success) {
            throw new Error(conciliarData.error || 'Erro na conciliação');
        }
        
        // 3. Processar resultados
        processarResultados(conciliarData.data);
        
        mostrarNotificacao('✅ Processamento concluído com sucesso!', 'success');
        
    } catch (error) {
        console.error('Erro:', error);
        mostrarNotificacao('❌ Erro ao processar: ' + error.message, 'error');
    } finally {
        esconderLoading();
    }
}

function processarResultados(responseData) {
    if (!responseData) {
        mostrarNotificacao('Retorno de conciliação inválido.', 'error');
        return;
    }

    const payload = responseData.data ? responseData.data : responseData;
    console.log('📊 Processando resultados:', payload);

    const dadosSistemaBrutos = payload.dados_aberta || payload.lancamentos_sistema || [];
    const dadosBancoBrutos = payload.dados_banco || payload.lancamentos_banco || [];
    const resumoStatus = payload.status || {};

    const dadosSistema = dadosSistemaBrutos.map(normalizarMovimentoSistema).filter(Boolean);
    const dadosBanco = dadosBancoBrutos.map(normalizarMovimentoBanco).filter(Boolean);

    AppState.lancamentosSistema = dadosSistema;
    AppState.lancamentosBanco = dadosBanco;
    AppState.statusResumo = resumoStatus;
    AppState.conciliacoes = gerarConciliacoesAutomaticas(dadosSistema, dadosBanco);

    // Reaplicar estado inicial de filtros/ordenadores
    AppState.buscaSistema = '';
    AppState.buscaBanco = '';
    AppState.filtroBanco = '';
    AppState.ordenacaoSistema = { campo: 'data', ordem: 'desc' };
    AppState.ordenacaoBanco = { campo: 'data', ordem: 'desc' };

    const searchSistema = document.getElementById('searchSistema');
    const searchBanco = document.getElementById('searchBanco');
    const filtroBancoSelect = document.getElementById('filtroBanco');
    if (searchSistema) searchSistema.value = '';
    if (searchBanco) searchBanco.value = '';
    if (filtroBancoSelect) filtroBancoSelect.value = '';

    // Calcular pendentes (remover conciliados automáticos)
    calcularPendentes();

    // Atualizar UI
    atualizarKPIs();
    renderizarTabelaSistema();
    renderizarTabelaBanco();
    renderizarTabelaConciliados();

    // Exibir seções
    document.getElementById('kpisSection').style.display = 'block';
    document.getElementById('workspace').style.display = 'block';
    document.getElementById('btnLimparSessao').style.display = 'inline-block';
    document.getElementById('btnExportarRelatorio').style.display = 'inline-block';

    // Esconder upload
    document.querySelector('.upload-section').style.display = 'none';
}

function calcularPendentes() {
    const idsConcilidosSistema = new Set();
    const idsConcilidosBanco = new Set();
    
    AppState.conciliacoes.forEach(grupo => {
        grupo.sistema.forEach(item => idsConcilidosSistema.add(item.id));
        grupo.banco.forEach(item => idsConcilidosBanco.add(item.id));
    });
    
    AppState.sistemasPendentes = AppState.lancamentosSistema.filter(
        item => !idsConcilidosSistema.has(item.id)
    );
    
    AppState.bancosPendentes = AppState.lancamentosBanco.filter(
        item => !idsConcilidosBanco.has(item.id)
    );
}

// ========================================
// RENDERIZAÇÃO DAS TABELAS
// ========================================
function renderizarTabelaSistema() {
    const tbody = document.getElementById('tableSistema');
    if (!tbody) return;

    const termoBusca = (AppState.buscaSistema || '').trim().toLowerCase();
    const itensFiltrados = AppState.sistemasPendentes.filter(item => {
        if (!termoBusca) return true;
        const textoComparacao = [
            item.descricao,
            item.descricao_original,
            item.ref_unique,
            item.ref_unique_norm,
            formatarMoeda(item.valor),
            formatarData(item.data)
        ].join(' ').toLowerCase();
        return textoComparacao.includes(termoBusca);
    });

    const itensOrdenados = obterItensOrdenados(itensFiltrados, AppState.ordenacaoSistema);

    if (itensOrdenados.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-3">Nenhum lançamento pendente</td></tr>';
        document.getElementById('countSistema').textContent = '0';
        document.getElementById('totalSistema').textContent = 'R$ 0,00';
        const checkAll = document.getElementById('checkAllSistema');
        if (checkAll) checkAll.checked = false;
        atualizarIndicadoresOrdenacao();
        return;
    }

    tbody.innerHTML = itensOrdenados.map(item => {
        const checked = AppState.sistemasSelecionados.has(item.id) ? 'checked' : '';
        const descricao = item.descricao || '-';
        return `
        <tr>
            <td><input type="checkbox" class="check-sistema" data-id="${item.id}" ${checked}></td>
            <td>${formatarData(item.data)}</td>
            <td class="text-truncate" style="max-width: 200px;" title="${descricao}">${descricao}</td>
            <td><span class="badge bg-info">${item.ref_unique || '-'}</span></td>
            <td class="text-end"><strong>${formatarMoeda(item.valor)}</strong></td>
        </tr>`;
    }).join('');

    tbody.querySelectorAll('.check-sistema').forEach(chk => {
        chk.addEventListener('change', handleSelecaoSistema);
    });

    const total = itensFiltrados.reduce((sum, item) => sum + parseFloat(item.valor || 0), 0);
    document.getElementById('countSistema').textContent = itensFiltrados.length;
    document.getElementById('totalSistema').textContent = formatarMoeda(total);

    const checkAll = document.getElementById('checkAllSistema');
    if (checkAll) {
        const todosSelecionados = itensOrdenados.length > 0 && itensOrdenados.every(item => AppState.sistemasSelecionados.has(item.id));
        checkAll.checked = todosSelecionados;
    }

    atualizarIndicadoresOrdenacao();
}

function renderizarTabelaBanco() {
    const tbody = document.getElementById('tableBanco');
    if (!tbody) return;

    const filtroAtual = AppState.filtroBanco || '';
    const termoBusca = (AppState.buscaBanco || '').trim().toLowerCase();

    const itensFiltrados = AppState.bancosPendentes.filter(item => {
        if (filtroAtual && item.banco !== filtroAtual) return false;
        if (!termoBusca) return true;
        const textoComparacao = [
            item.descricao,
            item.codigo_referencia,
            item.ref_unique,
            item.ref_unique_norm,
            item.banco,
            formatarMoeda(item.valor),
            formatarData(item.data)
        ].join(' ').toLowerCase();
        return textoComparacao.includes(termoBusca);
    });

    const itensOrdenados = obterItensOrdenados(itensFiltrados, AppState.ordenacaoBanco);

    if (itensOrdenados.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted py-3">Nenhum lançamento pendente</td></tr>';
        document.getElementById('countBanco').textContent = '0';
        document.getElementById('totalBanco').textContent = 'R$ 0,00';
        const checkAll = document.getElementById('checkAllBanco');
        if (checkAll) checkAll.checked = false;
        atualizarIndicadoresOrdenacao();
        return;
    }

    tbody.innerHTML = itensOrdenados.map(item => {
        const checked = AppState.bancosSelecionados.has(item.id) ? 'checked' : '';
        const descricao = item.descricao || item.historico || '-';
        return `
        <tr>
            <td><input type="checkbox" class="check-banco" data-id="${item.id}" ${checked}></td>
            <td>${formatarData(item.data)}</td>
            <td class="text-truncate" style="max-width: 180px;" title="${descricao}">${descricao}</td>
            <td><span class="badge bg-info">${item.ref_unique || '-'}</span></td>
            <td><span class="badge bg-secondary">${formatarBanco(item.banco)}</span></td>
            <td class="text-end"><strong>${formatarMoeda(item.valor)}</strong></td>
        </tr>`;
    }).join('');

    tbody.querySelectorAll('.check-banco').forEach(chk => {
        chk.addEventListener('change', handleSelecaoBanco);
    });

    const total = itensFiltrados.reduce((sum, item) => sum + parseFloat(item.valor || 0), 0);
    document.getElementById('countBanco').textContent = itensFiltrados.length;
    document.getElementById('totalBanco').textContent = formatarMoeda(total);

    const checkAll = document.getElementById('checkAllBanco');
    if (checkAll) {
        const todosSelecionados = itensOrdenados.length > 0 && itensOrdenados.every(item => AppState.bancosSelecionados.has(item.id));
        checkAll.checked = todosSelecionados;
    }

    atualizarIndicadoresOrdenacao();
}

function gerarDetalhesConciliados(itens, origem) {
    if (!Array.isArray(itens) || itens.length === 0) {
        return '<div class="conciliado-detalhes-vazio">Nenhum lançamento</div>';
    }

    const header = `<div class="conciliado-detalhes-header">${itens.length} lançamento(s)</div>`;
    const registros = itens.map(item => {
        const descricaoBase = item.descricao || item.descricao_original || item.historico || '-';
        const referenciaBase = item.ref_unique || item.codigo_referencia || '';
        const referenciaTratada = referenciaBase ? escapeHtml(referenciaBase) : '-';
        const metaBanco = origem === 'banco' && item.banco
            ? `<span>Banco: ${escapeHtml(formatarBanco(item.banco))}</span>`
            : '';

        return `
            <div class="conciliado-item">
                <div class="conciliado-item-header">
                    <span>${formatarData(item.data)}</span>
                    <span class="conciliado-item-valor">${formatarMoeda(item.valor)}</span>
                </div>
                <div class="conciliado-item-descricao">${escapeHtml(descricaoBase)}</div>
                <div class="conciliado-item-meta">
                    <span>Ref.: ${referenciaTratada || '-'}</span>
                    ${metaBanco}
                </div>
            </div>
        `;
    }).join('');

    return `<div class="conciliado-detalhes">${header}${registros}</div>`;
}

function renderizarTabelaConciliados() {
    const tbody = document.getElementById('tableConciliados');
    if (!tbody) return;

    const items = AppState.conciliacoes;

    if (items.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center text-muted py-5">
                    <i class="mdi mdi-checkbox-blank-circle-outline" style="font-size: 3rem;"></i>
                    <p class="mt-2">Nenhuma conciliação realizada ainda</p>
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = items.map(grupo => {
        const tipoIcon = grupo.tipo === 'manual' ? 'hand-pointing-right' : 'robot';
        const tipoLabel = grupo.tipo === 'manual' ? 'Manual' :
            grupo.tipo === 'auto_ref' ? 'Auto-Ref' : 'Auto-Valor';
        const tipoClass = grupo.tipo === 'manual' ? 'bg-primary' : 'bg-success';

        const detalhesSistema = gerarDetalhesConciliados(grupo.sistema, 'sistema');
        const detalhesBanco = gerarDetalhesConciliados(grupo.banco, 'banco');

        return `
            <tr>
                <td>
                    <span class="badge ${tipoClass}">
                        <i class="mdi mdi-${tipoIcon}"></i> ${tipoLabel}
                    </span>
                </td>
                <td>${formatarData(grupo.data)}</td>
                <td class="text-end"><strong>${formatarMoeda(grupo.valorTotal)}</strong></td>
                <td>${detalhesSistema}</td>
                <td>${detalhesBanco}</td>
                <td class="text-center">
                    ${grupo.tipo === 'manual'
                        ? `<button class="btn btn-sm btn-outline-danger" onclick="desfazerConciliacao('${grupo.id}')">
                                <i class="mdi mdi-undo"></i>
                           </button>`
                        : '<i class="mdi mdi-lock text-muted"></i>'}
                </td>
            </tr>
        `;
    }).join('');
}

// ========================================
// SELEÇÃO E CONCILIAÇÃO MANUAL
// ========================================
function handleSelecaoSistema(e) {
    const id = e.target.dataset.id;
    if (e.target.checked) {
        AppState.sistemasSelecionados.add(id);
    } else {
        AppState.sistemasSelecionados.delete(id);
    }
    atualizarTotaisSelecionados();
}

function handleSelecaoBanco(e) {
    const id = e.target.dataset.id;
    if (e.target.checked) {
        AppState.bancosSelecionados.add(id);
    } else {
        AppState.bancosSelecionados.delete(id);
    }
    atualizarTotaisSelecionados();
}

function toggleSelectAllSistema(e) {
    const checkboxes = document.querySelectorAll('.check-sistema');
    checkboxes.forEach(chk => {
        chk.checked = e.target.checked;
        handleSelecaoSistema({ target: chk });
    });
}

function toggleSelectAllBanco(e) {
    const checkboxes = document.querySelectorAll('.check-banco');
    checkboxes.forEach(chk => {
        chk.checked = e.target.checked;
        handleSelecaoBanco({ target: chk });
    });
}

function atualizarTotaisSelecionados() {
    const totalSistema = calcularTotalSelecionados(AppState.sistemasPendentes, AppState.sistemasSelecionados);
    const totalBanco = calcularTotalSelecionados(AppState.bancosPendentes, AppState.bancosSelecionados);
    
    document.getElementById('totalSelSistema').textContent = formatarMoeda(totalSistema);
    document.getElementById('totalSelBanco').textContent = formatarMoeda(totalBanco);
    
    // Habilitar botão se houver seleções
    const btn = document.getElementById('btnConciliarManual');
    btn.disabled = AppState.sistemasSelecionados.size === 0 || AppState.bancosSelecionados.size === 0;
}

function calcularTotalSelecionados(items, idsSet) {
    return items
        .filter(item => idsSet.has(item.id))
        .reduce((sum, item) => sum + parseFloat(item.valor || 0), 0);
}

function conciliarManual() {
    const totalSistema = calcularTotalSelecionados(AppState.sistemasPendentes, AppState.sistemasSelecionados);
    const totalBanco = calcularTotalSelecionados(AppState.bancosPendentes, AppState.bancosSelecionados);
    
    const validationMsg = document.getElementById('validation-message');
    
    // Validação: valores devem ser iguais
    if (Math.abs(totalSistema - totalBanco) > 0.01) {
        validationMsg.innerHTML = `
            <i class="mdi mdi-alert"></i>
            <strong>Erro:</strong> Os valores selecionados não são iguais. 
            Sistema: ${formatarMoeda(totalSistema)} | Banco: ${formatarMoeda(totalBanco)}
        `;
        validationMsg.className = 'validation-message error';
        validationMsg.style.display = 'block';
        return;
    }
    
    validationMsg.style.display = 'none';
    
    // Criar grupo de conciliação
    const sistemaItems = AppState.sistemasPendentes.filter(item => AppState.sistemasSelecionados.has(item.id));
    const bancoItems = AppState.bancosPendentes.filter(item => AppState.bancosSelecionados.has(item.id));
    
    const grupo = {
        id: gerarId(),
        tipo: 'manual',
        data: new Date().toISOString().split('T')[0],
        valorTotal: totalSistema,
        sistema: sistemaItems,
        banco: bancoItems,
        timestamp: new Date().toISOString()
    };
    
    // Adicionar ao estado
    AppState.conciliacoes.push(grupo);
    
    // Limpar seleções
    AppState.sistemasSelecionados.clear();
    AppState.bancosSelecionados.clear();
    
    // Recalcular pendentes
    calcularPendentes();
    
    // Atualizar UI
    atualizarKPIs();
    renderizarTabelaSistema();
    renderizarTabelaBanco();
    renderizarTabelaConciliados();
    
    mostrarNotificacao('✅ Conciliação manual realizada com sucesso!', 'success');
}

window.desfazerConciliacao = function(grupoId) {
    if (!confirm('Deseja realmente desfazer esta conciliação?')) return;
    
    const index = AppState.conciliacoes.findIndex(g => g.id === grupoId);
    if (index === -1) return;
    
    // Remover do array
    AppState.conciliacoes.splice(index, 1);
    
    // Recalcular pendentes
    calcularPendentes();
    
    // Atualizar UI
    atualizarKPIs();
    renderizarTabelaSistema();
    renderizarTabelaBanco();
    renderizarTabelaConciliados();
    
    mostrarNotificacao('↩️ Conciliação desfeita', 'info');
};

// ========================================
// KPIs
// ========================================
function atualizarKPIs() {
    const totalSistema = AppState.sistemasPendentes.reduce((sum, item) => sum + parseFloat(item.valor || 0), 0);
    const totalBanco = AppState.bancosPendentes.reduce((sum, item) => sum + parseFloat(item.valor || 0), 0);
    const totalConciliado = AppState.conciliacoes.reduce((sum, grupo) => sum + parseFloat(grupo.valorTotal || 0), 0);
    const conciliadosAutomaticos = AppState.statusResumo.conciliados_automatico || 0;
    const conciliacoesManuais = AppState.conciliacoes.filter(grupo => grupo.tipo === 'manual').length;
    const totalConciliadosCount = AppState.conciliacoes.length || (conciliadosAutomaticos + conciliacoesManuais);
    const valorConciliadoResumo = typeof AppState.statusResumo.valor_conciliado === 'number'
        ? AppState.statusResumo.valor_conciliado
        : totalConciliado;
    const valorConciliadoManual = AppState.conciliacoes
        .filter(grupo => grupo.tipo === 'manual')
        .reduce((sum, grupo) => sum + parseFloat(grupo.valorTotal || 0), 0);
    const valorConciliadoTotal = valorConciliadoResumo + (valorConciliadoManual || 0);
    
    document.getElementById('kpi-pendentes-sistema-count').textContent = AppState.sistemasPendentes.length;
    document.getElementById('kpi-pendentes-sistema-valor').textContent = formatarMoeda(totalSistema);
    
    document.getElementById('kpi-pendentes-banco-count').textContent = AppState.bancosPendentes.length;
    document.getElementById('kpi-pendentes-banco-valor').textContent = formatarMoeda(totalBanco);
    
    document.getElementById('kpi-conciliados-count').textContent = totalConciliadosCount;
    document.getElementById('kpi-conciliados-valor').textContent = formatarMoeda(valorConciliadoTotal);
    
    const totalSistemaRegistros = AppState.statusResumo.total_sistema || AppState.lancamentosSistema.length;
    const totalBancoRegistros = AppState.statusResumo.total_banco || AppState.lancamentosBanco.length;

    document.getElementById('kpi-total-sistema').textContent = totalSistemaRegistros;
    document.getElementById('kpi-total-banco').textContent = totalBancoRegistros;
    
    // Atualizar badges das abas
    document.getElementById('badge-pendentes').textContent = AppState.sistemasPendentes.length + AppState.bancosPendentes.length;
    document.getElementById('badge-conciliados').textContent = AppState.conciliacoes.length;
}

// ========================================
// FILTROS E BUSCA
// ========================================
function filtrarTabelaSistema() {
    const input = document.getElementById('searchSistema');
    AppState.buscaSistema = input ? input.value.toLowerCase() : '';
    renderizarTabelaSistema();
}

function filtrarTabelaBanco() {
    const input = document.getElementById('searchBanco');
    const selectBanco = document.getElementById('filtroBanco');
    AppState.buscaBanco = input ? input.value.toLowerCase() : '';
    AppState.filtroBanco = selectBanco ? selectBanco.value : '';
    renderizarTabelaBanco();
}

function filtrarConciliados() {
    const tipo = document.getElementById('filtroTipoConciliacao').value;
    const banco = document.getElementById('filtroBancoConciliados').value;
    const termo = document.getElementById('searchConciliados').value.toLowerCase();
    
    const rows = document.querySelectorAll('#tableConciliados tr');
    
    rows.forEach(row => {
        if (row.querySelector('td[colspan]')) return; // Skip empty state
        
        const tipoMatch = !tipo || row.textContent.includes(tipo);
        const bancoMatch = !banco; // TODO: implementar filtro de banco
        const termoMatch = !termo || row.textContent.toLowerCase().includes(termo);
        
        row.style.display = (tipoMatch && bancoMatch && termoMatch) ? '' : 'none';
    });
}

// ========================================
// NAVEGAÇÃO DE ABAS
// ========================================
function trocarAba(nomeAba) {
    AppState.abaAtiva = nomeAba;
    
    // Atualizar botões
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === nomeAba);
    });
    
    // Atualizar conteúdo
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.toggle('active', content.id === `tab-${nomeAba}`);
    });
}

// ========================================
// UTILITÁRIOS
// ========================================
function limparSessao() {
    if (!confirm('Deseja realmente limpar todos os dados e iniciar nova sessão?')) return;
    
    AppState.lancamentosSistema = [];
    AppState.lancamentosBanco = [];
    AppState.sistemasPendentes = [];
    AppState.bancosPendentes = [];
    AppState.conciliacoes = [];
    AppState.statusResumo = {};
    AppState.sistemasSelecionados.clear();
    AppState.bancosSelecionados.clear();
    
    document.getElementById('kpisSection').style.display = 'none';
    document.getElementById('workspace').style.display = 'none';
    document.querySelector('.upload-section').style.display = 'block';
    document.getElementById('btnLimparSessao').style.display = 'none';
    document.getElementById('btnExportarRelatorio').style.display = 'none';
    
    document.getElementById('uploadForm').reset();
    document.querySelector('.upload-placeholder').style.display = 'block';
    document.getElementById('filesList').style.display = 'none';
    document.getElementById('btnProcessar').disabled = true;
    
    trocarAba('conciliar');
    mostrarNotificacao('🔄 Sessão limpa', 'info');
}

function gerarId() {
    return 'conc_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

function formatarData(data) {
    if (!data) return '-';
    const d = new Date(data + 'T00:00:00');
    return d.toLocaleDateString('pt-BR');
}

function formatarMoeda(valor) {
    const num = parseFloat(valor) || 0;
    return num.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

function formatarBanco(banco) {
    const bancos = {
        'itau': 'Itaú',
        'santander': 'Santander',
        'banco_brasil': 'BB'
    };
    return bancos[banco] || banco;
}

function mostrarLoading(mensagem) {
    document.getElementById('loading-message').textContent = mensagem;
    document.getElementById('loading-overlay').style.display = 'flex';
}

function esconderLoading() {
    document.getElementById('loading-overlay').style.display = 'none';
}

function mostrarNotificacao(mensagem, tipo) {
    const bar = document.getElementById('notification-bar');
    bar.textContent = mensagem;
    const classe = ['success', 'error', 'info'].includes(tipo) ? tipo : 'info';
    bar.className = `notification-bar ${classe}`;
    bar.style.display = 'block';
    
    setTimeout(() => {
        bar.style.display = 'none';
    }, 4000);
}

function prepararNovaSessaoProcessamento() {
    AppState.conciliacoes = [];
    AppState.lancamentosSistema = [];
    AppState.lancamentosBanco = [];
    AppState.sistemasPendentes = [];
    AppState.bancosPendentes = [];
    AppState.statusResumo = {};
    AppState.sistemasSelecionados.clear();
    AppState.bancosSelecionados.clear();
    AppState.buscaSistema = '';
    AppState.buscaBanco = '';
    AppState.filtroBanco = '';
    AppState.ordenacaoSistema = { campo: 'data', ordem: 'desc' };
    AppState.ordenacaoBanco = { campo: 'data', ordem: 'desc' };

    ['searchSistema', 'searchBanco'].forEach(id => {
        const campo = document.getElementById(id);
        if (campo) campo.value = '';
    });

    const filtroBanco = document.getElementById('filtroBanco');
    if (filtroBanco) filtroBanco.value = '';

    const checkAllSistema = document.getElementById('checkAllSistema');
    if (checkAllSistema) checkAllSistema.checked = false;
    const checkAllBanco = document.getElementById('checkAllBanco');
    if (checkAllBanco) checkAllBanco.checked = false;
}

function calcularPeriodoSistema(tipoPeriodo) {
    const hoje = new Date();
    let inicio;
    let fim;

    switch (tipoPeriodo) {
        case 'mes_anterior': {
            const ano = hoje.getFullYear();
            const mesAnterior = hoje.getMonth() - 1;
            inicio = new Date(ano, mesAnterior, 1);
            fim = new Date(ano, mesAnterior + 1, 0);
            break;
        }
        case 'ultimos_30_dias':
            inicio = new Date(hoje);
            inicio.setDate(inicio.getDate() - 29);
            fim = new Date(hoje);
            break;
        case 'ultimos_15_dias':
            inicio = new Date(hoje);
            inicio.setDate(inicio.getDate() - 14);
            fim = new Date(hoje);
            break;
        case 'ultimos_7_dias':
            inicio = new Date(hoje);
            inicio.setDate(inicio.getDate() - 6);
            fim = new Date(hoje);
            break;
        case 'mes_atual':
        default:
            inicio = new Date(hoje.getFullYear(), hoje.getMonth(), 1);
            fim = new Date(hoje);
            break;
    }

    return {
        inicio: formatarISO(inicio),
        fim: formatarISO(fim)
    };
}

function formatarISO(data) {
    const ano = data.getFullYear();
    const mes = String(data.getMonth() + 1).padStart(2, '0');
    const dia = String(data.getDate()).padStart(2, '0');
    return `${ano}-${mes}-${dia}`;
}

function extrairReferenciaCodigo(texto) {
    if (!texto) return '';
    const valor = String(texto).toUpperCase();
    const match = valor.match(/\b(U[NS][0-9][0-9A-Z\/-]*)/);
    if (!match) {
        return '';
    }
    const referencia = match[1].replace(/[\s,.;:]+$/, '');
    const digitos = referencia.replace(/\D/g, '');
    return digitos.length >= 4 ? referencia : '';
}

function aplicarReferenciaExtraida(normalizado, campos) {
    if (!normalizado || !Array.isArray(campos)) {
        return;
    }
    for (const campo of campos) {
        const referencia = extrairReferenciaCodigo(campo);
        if (referencia) {
            normalizado.ref_unique = referencia;
            normalizado.ref_unique_norm = referencia;
            normalizado.codigo_referencia = referencia;
            return;
        }
    }
}

function escapeHtml(valor) {
    if (valor === null || valor === undefined) {
        return '';
    }
    return String(valor)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function normalizarMovimentoSistema(item) {
    if (!item) return null;
    const normalizado = { ...item };

    const dataValor = normalizarDataISO(
        item.data_lancamento || item.data_movimento || item.data || item.data_referencia
    );

    normalizado.id = item.id ? String(item.id) : criarIdTemporario('sistema');
    normalizado.data = dataValor || '';
    if (!normalizado.data_lancamento && dataValor) {
        normalizado.data_lancamento = dataValor;
    }

    normalizado.descricao = String(item.descricao ?? item.descricao_original ?? '').trim();
    normalizado.ref_unique = item.ref_unique || item.codigo_referencia || item.ref_unique_norm || '';
    normalizado.ref_unique_norm = item.ref_unique_norm || normalizado.ref_unique || '';
    normalizado.codigo_referencia = item.codigo_referencia || normalizado.ref_unique || '';
    normalizado.valor = parseFloat(item.valor || 0);
    normalizado.status = (item.status || 'pendente').toLowerCase();

    aplicarReferenciaExtraida(normalizado, [
        normalizado.ref_unique,
        normalizado.codigo_referencia,
        normalizado.ref_unique_norm,
        item.ref_unique,
        item.codigo_referencia,
        item.ref_unique_norm,
        item.descricao,
        item.descricao_original,
        item.historico,
        item.numero_documento,
        item.identificador
    ]);

    return normalizado;
}

function normalizarMovimentoBanco(item) {
    if (!item) return null;
    const normalizado = { ...item };

    const dataValor = normalizarDataISO(item.data || item.data_lancamento || item.data_original);

    normalizado.id = item.id ? String(item.id) : criarIdTemporario('banco');
    normalizado.data = dataValor || '';
    normalizado.valor = parseFloat(item.valor || 0);
    normalizado.descricao = String(item.descricao ?? item.historico ?? '').trim();
    normalizado.ref_unique = item.ref_unique || item.codigo_referencia || item.ref_unique_norm || '';
    normalizado.ref_unique_norm = item.ref_unique_norm || normalizado.ref_unique || '';
    normalizado.banco = normalizarBancoId(item.banco || item.banco_origem || item.nome_banco);
    normalizado.codigo_referencia = item.codigo_referencia || normalizado.ref_unique || '';
    normalizado.status = (item.status || 'pendente').toLowerCase();

    aplicarReferenciaExtraida(normalizado, [
        normalizado.ref_unique,
        normalizado.codigo_referencia,
        normalizado.ref_unique_norm,
        item.ref_unique,
        item.codigo_referencia,
        item.ref_unique_norm,
        item.descricao,
        item.historico,
        item.observacoes,
        item.identificador
    ]);

    return normalizado;
}

function normalizarDataISO(valor) {
    if (!valor) return '';

    if (valor instanceof Date) {
        return valor.toISOString().slice(0, 10);
    }

    const texto = String(valor).trim();
    if (!texto) return '';

    if (/^\d{4}-\d{2}-\d{2}/.test(texto)) {
        return texto.slice(0, 10);
    }

    if (/^\d{2}\/\d{2}\/\d{4}$/.test(texto)) {
        const [dia, mes, ano] = texto.split('/');
        return `${ano}-${mes}-${dia}`;
    }

    const timestamp = Date.parse(texto);
    if (!Number.isNaN(timestamp)) {
        return new Date(timestamp).toISOString().slice(0, 10);
    }

    return '';
}

function normalizarBancoId(nome) {
    if (!nome) return '';
    const texto = nome.toString().toLowerCase();

    if (texto.includes('ita')) return 'itau';
    if (texto.includes('santander')) return 'santander';
    if (texto.includes('banco do brasil') || texto.includes('bb') || texto.includes('banco_brasil')) {
        return 'banco_brasil';
    }

    return texto.replace(/\s+/g, '_');
}

function obterItensOrdenados(lista, ordenacao) {
    if (!Array.isArray(lista)) return [];
    if (!ordenacao || !ordenacao.campo) return [...lista];

    const copia = [...lista];
    const campo = ordenacao.campo;
    const ordem = ordenacao.ordem === 'asc' ? 'asc' : 'desc';

    copia.sort((a, b) => compararOrdenacao(a, b, campo, ordem));
    return copia;
}

function compararOrdenacao(a, b, campo, ordem) {
    const valorA = obterValorOrdenacao(a, campo);
    const valorB = obterValorOrdenacao(b, campo);

    if (valorA === valorB) return 0;

    if (ordem === 'asc') {
        return valorA > valorB ? 1 : -1;
    }
    return valorA < valorB ? 1 : -1;
}

function obterValorOrdenacao(item, campo) {
    switch (campo) {
        case 'data': {
            const iso = normalizarDataISO(item.data || item.data_lancamento || '');
            return iso ? Date.parse(`${iso}T00:00:00`) : 0;
        }
        case 'valor':
            return parseFloat(item.valor || 0);
        case 'descricao':
            return (item.descricao || item.historico || '').toLowerCase();
        case 'ref':
            return (item.ref_unique || item.ref_unique_norm || '').toLowerCase();
        case 'banco':
            return (item.banco || '').toLowerCase();
        default:
            if (item[campo] === null || item[campo] === undefined) return '';
            return String(item[campo]).toLowerCase();
    }
}

function aplicarOrdenacao(tabela, campo) {
    const alvo = tabela === 'banco' ? AppState.ordenacaoBanco : AppState.ordenacaoSistema;

    if (alvo.campo === campo) {
        alvo.ordem = alvo.ordem === 'asc' ? 'desc' : 'asc';
    } else {
        alvo.campo = campo;
        alvo.ordem = campo === 'valor' ? 'desc' : 'asc';
    }

    if (tabela === 'banco') {
        renderizarTabelaBanco();
    } else {
        renderizarTabelaSistema();
    }
}

function atualizarIndicadoresOrdenacao() {
    document.querySelectorAll('th.sortable').forEach(th => {
        th.classList.remove('sorted-asc', 'sorted-desc');
        const tabela = th.dataset.table;
        const campo = th.dataset.sort;
        if (!tabela || !campo) return;

        const ordenacaoAtual = tabela === 'banco' ? AppState.ordenacaoBanco : AppState.ordenacaoSistema;
        if (ordenacaoAtual.campo === campo) {
            th.classList.add(ordenacaoAtual.ordem === 'asc' ? 'sorted-asc' : 'sorted-desc');
        }
    });
}

function inicializarOrdenacao() {
    document.querySelectorAll('th.sortable').forEach(th => {
        th.addEventListener('click', () => {
            const tabela = th.dataset.table;
            const campo = th.dataset.sort;
            if (!tabela || !campo) return;
            aplicarOrdenacao(tabela, campo);
        });
    });
    atualizarIndicadoresOrdenacao();
}

function criarIdTemporario(prefixo) {
    return `${prefixo}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

function gerarConciliacoesAutomaticas(lancamentosSistema, lancamentosBanco) {
    if (!Array.isArray(lancamentosSistema) || !Array.isArray(lancamentosBanco)) {
        return [];
    }

    const bancoPorId = new Map();
    lancamentosBanco.forEach(item => {
        if (item && item.id) {
            bancoPorId.set(String(item.id), item);
        }
    });

    const conciliacoes = [];
    const combinacoesUsadas = new Set();

    lancamentosSistema.forEach(item => {
        if (!item || item.status !== 'conciliado') {
            return;
        }

        const matchIdBanco = item.match_id_banco || item.matchIdBanco;
        if (!matchIdBanco) {
            return;
        }

        const bancoMatch = bancoPorId.get(String(matchIdBanco));
        if (!bancoMatch) {
            return;
        }

        const chave = `${item.id}|${matchIdBanco}`;
        if (combinacoesUsadas.has(chave)) {
            return;
        }

        conciliacoes.push({
            id: gerarId(),
            tipo: definirTipoConciliacaoAutomatica(item.criterios || item.criterios_conciliacao),
            data: item.data_lancamento || item.data || new Date().toISOString().split('T')[0],
            valorTotal: parseFloat(item.valor || 0),
            sistema: [item],
            banco: [bancoMatch],
            timestamp: new Date().toISOString()
        });

        combinacoesUsadas.add(chave);
    });

    return conciliacoes;
}

function definirTipoConciliacaoAutomatica(criterios) {
    if (!Array.isArray(criterios)) {
        return 'auto_valor';
    }

    if (criterios.includes('codigo_exato') || criterios.includes('codigo_parcial')) {
        return 'auto_ref';
    }

    return 'auto_valor';
}

console.log('✅ Conciliação V2 carregada');
