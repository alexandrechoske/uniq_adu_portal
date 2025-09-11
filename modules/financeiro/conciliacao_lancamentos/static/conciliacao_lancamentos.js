// Conciliação de Lançamentos - JavaScript
console.log('[CONCILIACAO] Script carregado');

let arquivosUpload = [];
let dadosMovimentosSistema = [];
let dadosMovimentosBanco = [];
let selecionadosSistema = [];
let selecionadosBanco = [];

// Inicialização
document.addEventListener('DOMContentLoaded', function() {
    console.log('[CONCILIACAO] DOM carregado - Iniciando...');
    
    try {
        // Configurar eventos
        configurarEventos();
        
        // Configurar drag and drop
        configurarDragAndDrop();
        
        console.log('[CONCILIACAO] Inicialização completa');
    } catch (error) {
        console.error('[CONCILIACAO] Erro na inicialização:', error);
    }
});

function configurarEventos() {
    console.log('[CONCILIACAO] Configurando eventos...');
    
    try {
        // Upload de arquivos
        document.getElementById('upload-link').addEventListener('click', function(e) {
            e.preventDefault();
            document.getElementById('file-input').click();
        });
        
        document.getElementById('file-input').addEventListener('change', handleFileSelect);
        
        // Botões principais
        document.getElementById('btn-processar').addEventListener('click', processarConciliacao);
        document.getElementById('btn-limpar').addEventListener('click', limparTudo);
        document.getElementById('btn-conciliar-selecionados').addEventListener('click', abrirModalConfirmacao);
        
        // Seleção de tabelas
        document.getElementById('select-all-sistema').addEventListener('change', function() {
            selecionarTodosSistema(this.checked);
        });
        
        document.getElementById('select-all-banco').addEventListener('change', function() {
            selecionarTodosBanco(this.checked);
        });
        
        // Filtros
        document.getElementById('filter-sistema').addEventListener('input', filtrarTabelaSistema);
        document.getElementById('filter-banco').addEventListener('input', filtrarTabelaBanco);
        document.getElementById('status-sistema').addEventListener('change', filtrarTabelaSistema);
        document.getElementById('status-banco').addEventListener('change', filtrarTabelaBanco);
        document.getElementById('banco-origem').addEventListener('change', filtrarTabelaBanco);
        
        // Modal de confirmação
        document.getElementById('confirmation-modal-close').addEventListener('click', fecharModalConfirmacao);
        document.getElementById('confirmation-cancel').addEventListener('click', fecharModalConfirmacao);
        document.getElementById('confirmation-confirm').addEventListener('click', confirmarConciliacao);
        
        console.log('[CONCILIACAO] Eventos configurados');
    } catch (error) {
        console.error('[CONCILIACAO] Erro ao configurar eventos:', error);
    }
}

function configurarDragAndDrop() {
    const uploadArea = document.getElementById('upload-area');
    
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, preventDefaults, false);
    });
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    ['dragenter', 'dragover'].forEach(eventName => {
        uploadArea.addEventListener(eventName, highlight, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, unhighlight, false);
    });
    
    function highlight() {
        uploadArea.classList.add('dragover');
    }
    
    function unhighlight() {
        uploadArea.classList.remove('dragover');
    }
    
    uploadArea.addEventListener('drop', handleDrop, false);
    
    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles(files);
    }
    
    uploadArea.addEventListener('click', function() {
        document.getElementById('file-input').click();
    });
}

function handleFileSelect(e) {
    handleFiles(e.target.files);
}

function handleFiles(files) {
    console.log('[CONCILIACAO] Processando', files.length, 'arquivo(s)');
    
    for (let file of files) {
        if (validateFile(file)) {
            adicionarArquivo(file);
        }
    }
    
    atualizarListaArquivos();
    atualizarBotaoProcessar();
}

function validateFile(file) {
    // Verificar extensão
    const allowedTypes = ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/vnd.ms-excel'];
    if (!allowedTypes.includes(file.type)) {
        mostrarToast(`Arquivo ${file.name}: tipo não permitido`, 'error');
        return false;
    }
    
    // Verificar tamanho (10MB)
    const maxSize = 10 * 1024 * 1024;
    if (file.size > maxSize) {
        mostrarToast(`Arquivo ${file.name}: muito grande (máx. 10MB)`, 'error');
        return false;
    }
    
    // Verificar se já existe
    if (arquivosUpload.find(a => a.name === file.name && a.size === file.size)) {
        mostrarToast(`Arquivo ${file.name}: já foi adicionado`, 'warning');
        return false;
    }
    
    return true;
}

function adicionarArquivo(file) {
    const arquivo = {
        id: generateId(),
        file: file,
        name: file.name,
        size: file.size,
        banco: identificarBanco(file.name),
        status: 'waiting'
    };
    
    arquivosUpload.push(arquivo);
    console.log('[CONCILIACAO] Arquivo adicionado:', arquivo.name);
}

function atualizarListaArquivos() {
    const container = document.getElementById('files-container');
    const filesList = document.getElementById('files-list');
    
    if (arquivosUpload.length === 0) {
        filesList.style.display = 'none';
        return;
    }
    
    filesList.style.display = 'block';
    container.innerHTML = '';
    
    arquivosUpload.forEach(arquivo => {
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';
        fileItem.innerHTML = `
            <div class="file-info">
                <div class="file-icon">
                    <i class="mdi mdi-file-excel"></i>
                </div>
                <div class="file-details">
                    <h5>${arquivo.name}</h5>
                    <p>${formatFileSize(arquivo.size)} • ${arquivo.banco}</p>
                </div>
            </div>
            <div class="file-status">
                <span class="status-badge status-${arquivo.status}">
                    ${getStatusText(arquivo.status)}
                </span>
                <button class="btn-remove" onclick="removerArquivo('${arquivo.id}')">
                    <i class="mdi mdi-close"></i>
                </button>
            </div>
        `;
        container.appendChild(fileItem);
    });
}

function atualizarBotaoProcessar() {
    const btn = document.getElementById('btn-processar');
    btn.disabled = arquivosUpload.length === 0;
}

function removerArquivo(id) {
    arquivosUpload = arquivosUpload.filter(a => a.id !== id);
    atualizarListaArquivos();
    atualizarBotaoProcessar();
    console.log('[CONCILIACAO] Arquivo removido:', id);
}

function processarConciliacao() {
    console.log('[CONCILIACAO] Iniciando processamento...');
    
    if (arquivosUpload.length === 0) {
        mostrarToast('Adicione pelo menos um arquivo de extrato', 'warning');
        return;
    }
    
    mostrarLoading(true);
    
    // Atualizar status dos arquivos
    arquivosUpload.forEach(arquivo => {
        arquivo.status = 'processing';
    });
    atualizarListaArquivos();
    
    // Fazer upload dos arquivos
    uploadArquivos()
        .then(() => {
            // Buscar movimentos do sistema
            return buscarMovimentosSistema();
        })
        .then(() => {
            // Processar conciliação
            return processarConciliacaoBackend();
        })
        .then((resultado) => {
            // Atualizar interface com resultados
            atualizarInterface(resultado);
            mostrarToast('Conciliação processada com sucesso', 'success');
        })
        .catch((error) => {
            console.error('[CONCILIACAO] Erro no processamento:', error);
            mostrarToast('Erro ao processar conciliação', 'error');
            
            // Reverter status dos arquivos
            arquivosUpload.forEach(arquivo => {
                arquivo.status = 'error';
            });
            atualizarListaArquivos();
        })
        .finally(() => {
            mostrarLoading(false);
        });
}

async function uploadArquivos() {
    console.log('[CONCILIACAO] Fazendo upload dos arquivos...');
    
    const formData = new FormData();
    arquivosUpload.forEach(arquivo => {
        formData.append('files', arquivo.file);
    });
    
    const response = await fetch('/financeiro/conciliacao-lancamentos/api/upload-extratos', {
        method: 'POST',
        body: formData
    });
    
    if (!response.ok) {
        throw new Error('Erro no upload dos arquivos');
    }
    
    const result = await response.json();
    if (!result.success) {
        throw new Error(result.error || 'Erro no upload');
    }
    
    // Atualizar status dos arquivos
    arquivosUpload.forEach(arquivo => {
        arquivo.status = 'success';
    });
    atualizarListaArquivos();
    
    return result.data;
}

async function buscarMovimentosSistema() {
    console.log('[CONCILIACAO] Buscando movimentos do sistema...');
    
    const response = await fetch('/financeiro/conciliacao-lancamentos/api/movimentos-sistema');
    
    if (!response.ok) {
        throw new Error('Erro ao buscar movimentos do sistema');
    }
    
    const result = await response.json();
    if (!result.success) {
        throw new Error(result.error || 'Erro na busca');
    }
    
    dadosMovimentosSistema = result.data;
    return result.data;
}

async function processarConciliacaoBackend() {
    console.log('[CONCILIACAO] Processando conciliação no backend...');
    
    const response = await fetch('/financeiro/conciliacao-lancamentos/api/processar-conciliacao', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    });
    
    if (!response.ok) {
        throw new Error('Erro no processamento da conciliação');
    }
    
    const result = await response.json();
    if (!result.success) {
        throw new Error(result.error || 'Erro no processamento');
    }
    
    return result.data;
}

function atualizarInterface(resultado) {
    console.log('[CONCILIACAO] Atualizando interface com resultados:', resultado);
    
    // Mostrar seções de KPI e conciliação
    document.getElementById('kpi-section').style.display = 'block';
    document.getElementById('conciliacao-section').style.display = 'block';
    
    // Atualizar KPIs
    document.getElementById('total-sistema').textContent = resultado.total_sistema || 0;
    document.getElementById('total-extratos').textContent = resultado.total_extratos || 0;
    document.getElementById('total-conciliados').textContent = resultado.conciliados_automatico || 0;
    document.getElementById('total-pendentes').textContent = (resultado.pendentes_sistema || 0) + (resultado.pendentes_banco || 0);
    
    document.getElementById('valor-sistema').textContent = formatarMoeda(resultado.valor_sistema || 0);
    document.getElementById('valor-extratos').textContent = formatarMoeda(resultado.valor_extratos || 0);
    document.getElementById('valor-conciliados').textContent = formatarMoeda(resultado.valor_conciliado || 0);
    document.getElementById('valor-pendentes').textContent = formatarMoeda((resultado.valor_pendente_sistema || 0) + (resultado.valor_pendente_banco || 0));
    
    // Renderizar tabelas (dados simulados por enquanto)
    renderizarTabelaSistema();
    renderizarTabelaBanco();
    
    // Scroll para a área de conciliação
    document.getElementById('conciliacao-section').scrollIntoView({ behavior: 'smooth' });
}

function renderizarTabelaSistema() {
    const tbody = document.getElementById('table-sistema-tbody');
    
    // Dados simulados - será substituído pelos dados reais
    const dadosSimulados = [
        {
            id: 1,
            data_lancamento: '2025-09-10',
            tipo_lancamento: 'RECEITA',
            descricao: 'Receita de Serviços',
            valor: 5000.00,
            ref_unique: 'REC001',
            status: 'pendente'
        },
        {
            id: 2,
            data_lancamento: '2025-09-09',
            tipo_lancamento: 'DESPESA',
            descricao: 'Pagamento Fornecedor',
            valor: -2500.00,
            ref_unique: 'DEP001',
            status: 'conciliado'
        }
    ];
    
    tbody.innerHTML = '';
    
    dadosSimulados.forEach(item => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>
                <input type="checkbox" data-id="${item.id}" class="sistema-checkbox" 
                       onchange="toggleSelecionadoSistema(${item.id}, this.checked)">
            </td>
            <td>${formatarData(item.data_lancamento)}</td>
            <td><span class="tipo-${item.tipo_lancamento.toLowerCase()}">${item.tipo_lancamento}</span></td>
            <td>${item.descricao}</td>
            <td class="${item.valor >= 0 ? 'valor-positivo' : 'valor-negativo'}">${formatarMoeda(item.valor)}</td>
            <td>${item.ref_unique}</td>
            <td><span class="status-${item.status}">${item.status.toUpperCase()}</span></td>
        `;
        tbody.appendChild(row);
    });
}

function renderizarTabelaBanco() {
    const tbody = document.getElementById('table-banco-tbody');
    
    // Dados simulados - será substituído pelos dados reais
    const dadosSimulados = [
        {
            id: 1,
            data: '2025-09-10',
            tipo: 'CREDITO',
            descricao: 'TED RECEBIDA',
            valor: 5000.00,
            banco: 'Itaú',
            status: 'pendente'
        },
        {
            id: 2,
            data: '2025-09-09',
            tipo: 'DEBITO',
            descricao: 'PAGAMENTO PIX',
            valor: -2500.00,
            banco: 'Santander',
            status: 'conciliado'
        }
    ];
    
    tbody.innerHTML = '';
    
    dadosSimulados.forEach(item => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>
                <input type="checkbox" data-id="${item.id}" class="banco-checkbox" 
                       onchange="toggleSelecionadoBanco(${item.id}, this.checked)">
            </td>
            <td>${formatarData(item.data)}</td>
            <td><span class="tipo-${item.tipo.toLowerCase()}">${item.tipo}</span></td>
            <td>${item.descricao}</td>
            <td class="${item.valor >= 0 ? 'valor-positivo' : 'valor-negativo'}">${formatarMoeda(item.valor)}</td>
            <td><span class="banco-badge banco-${item.banco.toLowerCase().replace(' ', '-')}">${item.banco}</span></td>
            <td><span class="status-${item.status}">${item.status.toUpperCase()}</span></td>
        `;
        tbody.appendChild(row);
    });
    
    // Atualizar filtro de bancos
    atualizarFiltroBancos();
}

function atualizarFiltroBancos() {
    const select = document.getElementById('banco-origem');
    const bancosUnicos = [...new Set(dadosMovimentosBanco.map(item => item.banco))];
    
    // Limpar opções existentes (exceto "Todos os Bancos")
    select.innerHTML = '<option value="">Todos os Bancos</option>';
    
    bancosUnicos.forEach(banco => {
        const option = document.createElement('option');
        option.value = banco;
        option.textContent = banco;
        select.appendChild(option);
    });
}

function toggleSelecionadoSistema(id, checked) {
    if (checked) {
        if (!selecionadosSistema.includes(id)) {
            selecionadosSistema.push(id);
        }
    } else {
        selecionadosSistema = selecionadosSistema.filter(itemId => itemId !== id);
    }
    
    atualizarResumoSelecao();
}

function toggleSelecionadoBanco(id, checked) {
    if (checked) {
        if (!selecionadosBanco.includes(id)) {
            selecionadosBanco.push(id);
        }
    } else {
        selecionadosBanco = selecionadosBanco.filter(itemId => itemId !== id);
    }
    
    atualizarResumoSelecao();
}

function selecionarTodosSistema(checked) {
    const checkboxes = document.querySelectorAll('.sistema-checkbox');
    selecionadosSistema = [];
    
    checkboxes.forEach(checkbox => {
        checkbox.checked = checked;
        if (checked) {
            selecionadosSistema.push(parseInt(checkbox.dataset.id));
        }
    });
    
    atualizarResumoSelecao();
}

function selecionarTodosBanco(checked) {
    const checkboxes = document.querySelectorAll('.banco-checkbox');
    selecionadosBanco = [];
    
    checkboxes.forEach(checkbox => {
        checkbox.checked = checked;
        if (checked) {
            selecionadosBanco.push(parseInt(checkbox.dataset.id));
        }
    });
    
    atualizarResumoSelecao();
}

function atualizarResumoSelecao() {
    // Calcular valores selecionados (simulado)
    const valorSistema = selecionadosSistema.length * 1000; // Simulado
    const valorBanco = selecionadosBanco.length * 1000; // Simulado
    const diferenca = valorSistema - valorBanco;
    
    // Atualizar resumo
    document.getElementById('summary-sistema').textContent = 
        `Sistema: ${formatarMoeda(valorSistema)} (${selecionadosSistema.length} selecionados)`;
    
    document.getElementById('summary-banco').textContent = 
        `Banco: ${formatarMoeda(valorBanco)} (${selecionadosBanco.length} selecionados)`;
    
    const diferencaElement = document.getElementById('summary-diferenca');
    diferencaElement.textContent = `Diferença: ${formatarMoeda(diferenca)}`;
    
    // Aplicar classes de cor baseado na diferença
    diferencaElement.className = 'diferenca';
    if (diferenca > 0) {
        diferencaElement.classList.add('positive');
    } else if (diferenca < 0) {
        diferencaElement.classList.add('negative');
    } else {
        diferencaElement.classList.add('zero');
    }
    
    // Habilitar/desabilitar botão de conciliar
    const btnConciliar = document.getElementById('btn-conciliar-selecionados');
    btnConciliar.disabled = selecionadosSistema.length === 0 || selecionadosBanco.length === 0;
}

function abrirModalConfirmacao() {
    if (selecionadosSistema.length === 0 || selecionadosBanco.length === 0) {
        mostrarToast('Selecione itens em ambas as tabelas', 'warning');
        return;
    }
    
    // Calcular valores (simulado)
    const valorSistema = selecionadosSistema.length * 1000;
    const valorBanco = selecionadosBanco.length * 1000;
    const diferenca = valorSistema - valorBanco;
    
    // Atualizar modal
    document.getElementById('conf-sistema-count').textContent = selecionadosSistema.length;
    document.getElementById('conf-sistema-valor').textContent = formatarMoeda(valorSistema);
    document.getElementById('conf-banco-count').textContent = selecionadosBanco.length;
    document.getElementById('conf-banco-valor').textContent = formatarMoeda(valorBanco);
    document.getElementById('conf-diferenca').textContent = formatarMoeda(diferenca);
    
    // Mostrar aviso se valores não batem
    const warning = document.getElementById('conf-warning');
    if (diferenca !== 0) {
        warning.style.display = 'flex';
    } else {
        warning.style.display = 'none';
    }
    
    // Mostrar modal
    const modal = document.getElementById('confirmation-modal');
    modal.style.display = 'flex';
    setTimeout(() => modal.classList.add('active'), 10);
}

function fecharModalConfirmacao() {
    const modal = document.getElementById('confirmation-modal');
    modal.classList.remove('active');
    setTimeout(() => modal.style.display = 'none', 300);
}

function confirmarConciliacao() {
    console.log('[CONCILIACAO] Confirmando conciliação manual...');
    
    mostrarLoading(true);
    
    const dados = {
        sistema_ids: selecionadosSistema,
        banco_ids: selecionadosBanco
    };
    
    fetch('/financeiro/conciliacao-lancamentos/api/conciliar-manual', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(dados)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            mostrarToast(data.message || 'Conciliação realizada com sucesso', 'success');
            fecharModalConfirmacao();
            
            // Limpar seleções
            selecionadosSistema = [];
            selecionadosBanco = [];
            
            // Recarregar dados
            processarConciliacao();
        } else {
            mostrarToast(data.error || 'Erro na conciliação', 'error');
        }
    })
    .catch(error => {
        console.error('[CONCILIACAO] Erro na confirmação:', error);
        mostrarToast('Erro de comunicação', 'error');
    })
    .finally(() => {
        mostrarLoading(false);
    });
}

function filtrarTabelaSistema() {
    // TODO: Implementar filtros da tabela sistema
}

function filtrarTabelaBanco() {
    // TODO: Implementar filtros da tabela banco
}

function limparTudo() {
    console.log('[CONCILIACAO] Limpando tudo...');
    
    // Limpar arquivos
    arquivosUpload = [];
    atualizarListaArquivos();
    atualizarBotaoProcessar();
    
    // Limpar dados
    dadosMovimentosSistema = [];
    dadosMovimentosBanco = [];
    selecionadosSistema = [];
    selecionadosBanco = [];
    
    // Esconder seções
    document.getElementById('kpi-section').style.display = 'none';
    document.getElementById('conciliacao-section').style.display = 'none';
    
    // Limpar input
    document.getElementById('file-input').value = '';
    
    mostrarToast('Dados limpos', 'info');
}

// Funções utilitárias
function identificarBanco(filename) {
    const name = filename.toLowerCase();
    
    if (name.includes('itau') || name.includes('itaú')) return 'Itaú';
    if (name.includes('santander')) return 'Santander';
    if (name.includes('bb') || name.includes('brasil')) return 'Banco do Brasil';
    if (name.includes('bradesco')) return 'Bradesco';
    if (name.includes('caixa')) return 'Caixa Econômica';
    
    return 'Outros';
}

function generateId() {
    return Math.random().toString(36).substr(2, 9);
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function getStatusText(status) {
    const statusMap = {
        'waiting': 'Aguardando',
        'processing': 'Processando',
        'success': 'Sucesso',
        'error': 'Erro'
    };
    return statusMap[status] || status;
}

function formatarMoeda(valor) {
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(valor || 0);
}

function formatarData(data) {
    if (!data) return '';
    return new Date(data).toLocaleDateString('pt-BR');
}

function mostrarLoading(mostrar) {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.style.display = mostrar ? 'flex' : 'none';
    }
}

function mostrarToast(mensagem, tipo = 'info') {
    console.log('[CONCILIACAO] Toast:', mensagem, tipo);
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${tipo}`;
    toast.textContent = mensagem;
    
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container';
        document.body.appendChild(container);
    }
    
    container.appendChild(toast);
    
    setTimeout(() => toast.classList.add('show'), 100);
    
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => container.removeChild(toast), 300);
    }, 3000);
}