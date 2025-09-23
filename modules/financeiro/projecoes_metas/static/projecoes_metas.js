console.log('[PROJECOES] Script carregado');

let dadosProjecoes = [];
let editandoItem = null;
let tipoEdicao = null;
let tabAtiva = 'metas-financeiras-geral';
let modoModal = 'individual';

document.addEventListener('DOMContentLoaded', function() {
    console.log('[PROJECOES] DOM carregado - Iniciando...');
    
    try {
        configurarTabs();
        configurarEventos();
        
        // Garantir que a aba inicial esteja corretamente ativa
        switchTab(tabAtiva);
        
        // Aguardar um pouco para garantir que todos os elementos estejam prontos
        setTimeout(function() {
            console.log('[PROJECOES] Iniciando busca de dados...');
            buscarDados();
        }, 100);
        
        console.log('[PROJECOES] Inicialização completa');
    } catch (error) {
        console.error('[PROJECOES] Erro na inicialização:', error);
    }
});

function configurarTabs() {
    console.log('[PROJECOES] Configurando tabs...');
    const tabButtons = document.querySelectorAll('.tab-button');
    
    tabButtons.forEach(button => {
        button.addEventListener('click', function() {
            const tabId = this.getAttribute('data-tab');
            switchTab(tabId);
        });
    });
}

function switchTab(tabId) {
    console.log('[PROJECOES] Mudando para aba:', tabId);
    
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector('[data-tab="' + tabId + '"]').classList.add('active');
    
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    
    document.getElementById('content-' + tabId).classList.add('active');
    
    tabAtiva = tabId;
    console.log('[PROJECOES] Aba ativa:', tabId);
}

function configurarEventos() {
    console.log('[PROJECOES] Configurando eventos...');
    
    try {
        // Eventos dos botões de nova meta/projeção
        document.getElementById('btn-nova-meta-financeira-geral').addEventListener('click', function() { abrirModal('financeiro_geral'); });
        document.getElementById('btn-nova-meta-financeira-consultoria').addEventListener('click', function() { abrirModal('financeiro_consultoria'); });
        document.getElementById('btn-nova-meta-operacional').addEventListener('click', function() { abrirModal('operacional'); });
        document.getElementById('btn-nova-projecao').addEventListener('click', function() { abrirModal('projecao'); });
        
        configurarModais();
        
        console.log('[PROJECOES] Eventos configurados');
    } catch (error) {
        console.error('[PROJECOES] Erro ao configurar eventos:', error);
    }
}

function configurarModais() {
    console.log('[PROJECOES] Configurando modais...');
    
    document.getElementById('meta-modal-close').addEventListener('click', fecharModal);
    document.getElementById('meta-modal-cancel').addEventListener('click', fecharModal);
    document.getElementById('meta-modal-save').addEventListener('click', salvarItem);
    
    document.getElementById('meta-modal').addEventListener('click', function(e) {
        if (e.target === this) fecharModal();
    });
    
    document.getElementById('tab-individual').addEventListener('click', function() { switchModalTab('individual'); });
    document.getElementById('tab-lote').addEventListener('click', function() { switchModalTab('lote'); });
    
    document.getElementById('btn-adicionar-mes-valor').addEventListener('click', adicionarLinhaMesValor);
    
    configurarFormatacaoMoeda();
    preencherAnosDinamicos();
}

function buscarDados() {
    console.log('[PROJECOES] Buscando todos os dados...');
    
    mostrarLoading(true);
    
    const url = '/financeiro/projecoes-metas/api/dados';
    console.log('[PROJECOES] URL da requisição:', url);
    
    fetch(url)
        .then(response => {
            console.log('[PROJECOES] Status da resposta:', response.status);
            return response.json();
        })
        .then(data => {
            console.log('[PROJECOES] Dados recebidos:', data);
            
            if (data.success !== false) {
                dadosProjecoes = data.data || [];
                renderizarDados();
                atualizarEstatisticas();
            } else {
                console.error('[PROJECOES] Erro na resposta:', data.error);
                mostrarToast('Erro ao carregar dados: ' + (data.error || 'Erro desconhecido'), 'error');
            }
        })
        .catch(error => {
            console.error('[PROJECOES] Erro na requisição:', error);
            mostrarToast('Erro ao carregar dados', 'error');
            dadosProjecoes = [];
        })
        .finally(function() {
            mostrarLoading(false);
        });
}

function renderizarDados() {
    console.log('[PROJECOES] Renderizando dados:', dadosProjecoes.length, 'itens');
    renderizarMetasFinanceirasGeral();
    renderizarMetasFinanceirasConsultoria();
    renderizarMetasOperacionais();
    renderizarProjecoes();
}

function renderizarMetasFinanceirasGeral() {
    const tbody = document.getElementById('table-metas-financeiras-geral-tbody');
    const metas = dadosProjecoes.filter(item => item.tipo === 'financeiro_solucoes');
    
    console.log('[PROJECOES] Metas financeiras soluções:', metas.length);
    tbody.innerHTML = '';
    
    if (metas.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: #666; padding: 40px;"><i class="mdi mdi-information-outline" style="font-size: 24px; margin-bottom: 10px; display: block;"></i>Nenhuma meta financeira soluções encontrada</td></tr>';
        return;
    }
    
    // Agrupar por ano
    const metasPorAno = {};
    metas.forEach(meta => {
        if (!metasPorAno[meta.ano]) {
            metasPorAno[meta.ano] = [];
        }
        metasPorAno[meta.ano].push(meta);
    });
    
    // Ordenar anos (mais recente primeiro)
    const anosOrdenados = Object.keys(metasPorAno).sort((a, b) => b - a);
    
    anosOrdenados.forEach(ano => {
        // Verificar estado salvo no localStorage
        const estadoSalvo = localStorage.getItem(`projecoes_ano_${ano}_${tabAtiva}`);
        const expandido = estadoSalvo !== null ? estadoSalvo === 'true' : true; // Padrão: expandido
        
        // Cabeçalho do ano
        const headerRow = document.createElement('tr');
        headerRow.className = 'ano-header';
        headerRow.setAttribute('data-ano', ano);
        headerRow.innerHTML = `
            <td colspan="5">
                <button class="btn-ano-toggle" onclick="toggleAno('${ano}', '${tabAtiva}')" data-ano="${ano}" data-tab="${tabAtiva}">
                    <i class="mdi ${expandido ? 'mdi-chevron-down' : 'mdi-chevron-right'}"></i>
                </button>
                <i class="mdi mdi-calendar"></i> ${ano}
            </td>`;
        tbody.appendChild(headerRow);
        
        // Metas do ano
        metasPorAno[ano].sort((a, b) => a.mes - b.mes).forEach(meta => {
            const row = document.createElement('tr');
            row.className = `ano-data ano-${ano}`;
            row.style.display = expandido ? 'table-row' : 'none';
            row.innerHTML = '<td>' + meta.ano + '</td><td>' + formatarMes(meta.mes) + '</td><td class="valor-financeira">' + formatarMoeda(meta.meta) + '</td><td>' + formatarData(meta.created_at) + '</td><td><button class="btn btn-sm btn-primary" onclick="editarItem(' + meta.id + ', \'financeiro_solucoes\')" title="Editar"><i class="mdi mdi-pencil"></i></button><button class="btn btn-sm" style="background: #dc3545; color: white;" onclick="excluirItem(' + meta.id + ')" title="Excluir"><i class="mdi mdi-delete"></i></button></td>';
            tbody.appendChild(row);
        });
    });
}

function renderizarMetasFinanceirasConsultoria() {
    const tbody = document.getElementById('table-metas-financeiras-consultoria-tbody');
    const metas = dadosProjecoes.filter(item => item.tipo === 'financeiro_consultoria');
    
    console.log('[PROJECOES] Metas financeiras consultoria:', metas.length);
    tbody.innerHTML = '';
    
    if (metas.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: #666; padding: 40px;"><i class="mdi mdi-information-outline" style="font-size: 24px; margin-bottom: 10px; display: block;"></i>Nenhuma meta financeira consultoria encontrada</td></tr>';
        return;
    }
    
    // Agrupar por ano
    const metasPorAno = {};
    metas.forEach(meta => {
        if (!metasPorAno[meta.ano]) {
            metasPorAno[meta.ano] = [];
        }
        metasPorAno[meta.ano].push(meta);
    });
    
    // Ordenar anos (mais recente primeiro)
    const anosOrdenados = Object.keys(metasPorAno).sort((a, b) => b - a);
    
    anosOrdenados.forEach(ano => {
        // Verificar estado salvo no localStorage
        const estadoSalvo = localStorage.getItem(`projecoes_ano_${ano}_${tabAtiva}`);
        const expandido = estadoSalvo !== null ? estadoSalvo === 'true' : true; // Padrão: expandido
        
        // Cabeçalho do ano
        const headerRow = document.createElement('tr');
        headerRow.className = 'ano-header';
        headerRow.setAttribute('data-ano', ano);
        headerRow.innerHTML = `
            <td colspan="5">
                <button class="btn-ano-toggle" onclick="toggleAno('${ano}', '${tabAtiva}')" data-ano="${ano}" data-tab="${tabAtiva}">
                    <i class="mdi ${expandido ? 'mdi-chevron-down' : 'mdi-chevron-right'}"></i>
                </button>
                <i class="mdi mdi-calendar"></i> ${ano}
            </td>`;
        tbody.appendChild(headerRow);
        
        // Metas do ano
        metasPorAno[ano].sort((a, b) => a.mes - b.mes).forEach(meta => {
            const row = document.createElement('tr');
            row.className = `ano-data ano-${ano}`;
            row.style.display = expandido ? 'table-row' : 'none';
            row.innerHTML = '<td>' + meta.ano + '</td><td>' + formatarMes(meta.mes) + '</td><td class="valor-financeira">' + formatarMoeda(meta.meta) + '</td><td>' + formatarData(meta.created_at) + '</td><td><button class="btn btn-sm btn-primary" onclick="editarItem(' + meta.id + ', \'financeiro_consultoria\')" title="Editar"><i class="mdi mdi-pencil"></i></button><button class="btn btn-sm" style="background: #dc3545; color: white;" onclick="excluirItem(' + meta.id + ')" title="Excluir"><i class="mdi mdi-delete"></i></button></td>';
            tbody.appendChild(row);
        });
    });
}

function renderizarMetasOperacionais() {
    const tbody = document.getElementById('table-metas-operacionais-tbody');
    const metas = dadosProjecoes.filter(item => item.tipo === 'operacional');
    
    console.log('[PROJECOES] Metas operacionais:', metas.length);
    tbody.innerHTML = '';
    
    if (metas.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: #666; padding: 40px;"><i class="mdi mdi-information-outline" style="font-size: 24px; margin-bottom: 10px; display: block;"></i>Nenhuma meta operacional encontrada</td></tr>';
        return;
    }
    
    // Agrupar por ano
    const metasPorAno = {};
    metas.forEach(meta => {
        if (!metasPorAno[meta.ano]) {
            metasPorAno[meta.ano] = [];
        }
        metasPorAno[meta.ano].push(meta);
    });
    
    // Ordenar anos (mais recente primeiro)
    const anosOrdenados = Object.keys(metasPorAno).sort((a, b) => b - a);
    
    anosOrdenados.forEach(ano => {
        // Verificar estado salvo no localStorage
        const estadoSalvo = localStorage.getItem(`projecoes_ano_${ano}_${tabAtiva}`);
        const expandido = estadoSalvo !== null ? estadoSalvo === 'true' : true; // Padrão: expandido
        
        // Cabeçalho do ano
        const headerRow = document.createElement('tr');
        headerRow.className = 'ano-header';
        headerRow.setAttribute('data-ano', ano);
        headerRow.innerHTML = `
            <td colspan="5">
                <button class="btn-ano-toggle" onclick="toggleAno('${ano}', '${tabAtiva}')" data-ano="${ano}" data-tab="${tabAtiva}">
                    <i class="mdi ${expandido ? 'mdi-chevron-down' : 'mdi-chevron-right'}"></i>
                </button>
                <i class="mdi mdi-calendar"></i> ${ano}
            </td>`;
        tbody.appendChild(headerRow);
        
        // Metas do ano
        metasPorAno[ano].sort((a, b) => a.mes - b.mes).forEach(meta => {
            const row = document.createElement('tr');
            row.className = `ano-data ano-${ano}`;
            row.style.display = expandido ? 'table-row' : 'none';
            row.innerHTML = '<td>' + meta.ano + '</td><td>' + formatarMes(meta.mes) + '</td><td class="valor-operacional">' + formatarMoeda(meta.meta) + '</td><td>' + formatarData(meta.created_at) + '</td><td><button class="btn btn-sm btn-warning" onclick="editarItem(' + meta.id + ', \'operacional\')" title="Editar"><i class="mdi mdi-pencil"></i></button><button class="btn btn-sm" style="background: #dc3545; color: white;" onclick="excluirItem(' + meta.id + ')" title="Excluir"><i class="mdi mdi-delete"></i></button></td>';
            tbody.appendChild(row);
        });
    });
}

function renderizarProjecoes() {
    const tbody = document.getElementById('table-projecoes-tbody');
    const projecoes = dadosProjecoes.filter(item => item.tipo === 'projecao');
    
    console.log('[PROJECOES] Projeções:', projecoes.length);
    tbody.innerHTML = '';
    
    if (projecoes.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: #666; padding: 40px;"><i class="mdi mdi-information-outline" style="font-size: 24px; margin-bottom: 10px; display: block;"></i>Nenhuma projeção encontrada</td></tr>';
        return;
    }
    
    // Agrupar por ano
    const projecoesPorAno = {};
    projecoes.forEach(projecao => {
        if (!projecoesPorAno[projecao.ano]) {
            projecoesPorAno[projecao.ano] = [];
        }
        projecoesPorAno[projecao.ano].push(projecao);
    });
    
    // Ordenar anos (mais recente primeiro)
    const anosOrdenados = Object.keys(projecoesPorAno).sort((a, b) => b - a);
    
    anosOrdenados.forEach(ano => {
        // Verificar estado salvo no localStorage
        const estadoSalvo = localStorage.getItem(`projecoes_ano_${ano}_${tabAtiva}`);
        const expandido = estadoSalvo !== null ? estadoSalvo === 'true' : true; // Padrão: expandido
        
        // Cabeçalho do ano
        const headerRow = document.createElement('tr');
        headerRow.className = 'ano-header';
        headerRow.setAttribute('data-ano', ano);
        headerRow.innerHTML = `
            <td colspan="5">
                <button class="btn-ano-toggle" onclick="toggleAno('${ano}', '${tabAtiva}')" data-ano="${ano}" data-tab="${tabAtiva}">
                    <i class="mdi ${expandido ? 'mdi-chevron-down' : 'mdi-chevron-right'}"></i>
                </button>
                <i class="mdi mdi-calendar"></i> ${ano}
            </td>`;
        tbody.appendChild(headerRow);
        
        // Projeções do ano
        projecoesPorAno[ano].sort((a, b) => a.mes - b.mes).forEach(projecao => {
            const row = document.createElement('tr');
            row.className = `ano-data ano-${ano}`;
            row.style.display = expandido ? 'table-row' : 'none';
            row.innerHTML = '<td>' + projecao.ano + '</td><td>' + formatarMes(projecao.mes) + '</td><td class="valor-projecao">' + formatarMoeda(projecao.meta) + '</td><td>' + formatarData(projecao.created_at) + '</td><td><button class="btn btn-sm btn-success" onclick="editarItem(' + projecao.id + ', \'projecao\')" title="Editar"><i class="mdi mdi-pencil"></i></button><button class="btn btn-sm" style="background: #dc3545; color: white;" onclick="excluirItem(' + projecao.id + ')" title="Excluir"><i class="mdi mdi-delete"></i></button></td>';
            tbody.appendChild(row);
        });
    });
}

function atualizarEstatisticas() {
    const financeirasGeral = dadosProjecoes.filter(item => item.tipo === 'financeiro_solucoes').length;
    const financeirasConsultoria = dadosProjecoes.filter(item => item.tipo === 'financeiro_consultoria').length;
    const operacionais = dadosProjecoes.filter(item => item.tipo === 'operacional').length;
    const projecoes = dadosProjecoes.filter(item => item.tipo === 'projecao').length;
    
    console.log('[PROJECOES] Estatísticas - Financeiras Soluções:', financeirasGeral, 'Financeiras Consultoria:', financeirasConsultoria, 'Operacionais:', operacionais, 'Projeções:', projecoes);
    
    document.getElementById('total-financeiras-geral').textContent = financeirasGeral;
    document.getElementById('total-financeiras-consultoria').textContent = financeirasConsultoria;
    document.getElementById('total-operacionais').textContent = operacionais;
    document.getElementById('total-projecoes').textContent = projecoes;
}

function abrirModal(tipo) {
    console.log('[PROJECOES] Abrindo modal para tipo:', tipo);
    
    tipoEdicao = tipo;
    editandoItem = null;
    
    var titulos = {
        'financeiro': 'Nova Meta Financeira',
        'financeiro_geral': 'Nova Meta Financeira - Soluções',
        'financeiro_consultoria': 'Nova Meta Financeira - Consultoria',
        'operacional': 'Nova Meta Operacional',
        'projecao': 'Nova Projeção'
    };
    
    document.getElementById('meta-modal-title').textContent = titulos[tipo];
    
    switchModalTab('individual');
    preencherAnosDinamicos();
    
    const anoAtual = new Date().getFullYear();
    document.getElementById('meta-modal-ano').value = anoAtual + 1;
    document.getElementById('meta-modal-mes').value = '01';
    document.getElementById('meta-modal-valor').value = '';
    
    document.getElementById('meta-modal-ano-lote').value = anoAtual + 1;
    limparMesesValores();
    adicionarLinhaMesValor();
    
    const modal = document.getElementById('meta-modal');
    modal.style.display = 'flex';
    setTimeout(function() { modal.classList.add('active'); }, 10);
}

window.editarItem = function(itemId, tipo) {
    console.log('[PROJECOES] Editando item:', itemId, 'tipo:', tipo);
    
    const item = dadosProjecoes.find(d => d.id === itemId);
    if (!item) {
        mostrarToast('Item não encontrado', 'error');
        return;
    }
    
    tipoEdicao = tipo;
    editandoItem = item;
    
    var titulos = {
        'financeiro': 'Editar Meta Financeira',
        'financeiro_geral': 'Editar Meta Financeira - Soluções',
        'financeiro_consultoria': 'Editar Meta Financeira - Consultoria',
        'operacional': 'Editar Meta Operacional',
        'projecao': 'Editar Projeção'
    };
    
    document.getElementById('meta-modal-title').textContent = titulos[tipo];
    
    switchModalTab('individual');
    preencherAnosDinamicos();
    
    document.getElementById('meta-modal-ano').value = item.ano;
    document.getElementById('meta-modal-mes').value = item.mes;
    
    const valorInput = document.getElementById('meta-modal-valor');
    valorInput.value = new Intl.NumberFormat('pt-BR', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(item.meta);
    
    const modal = document.getElementById('meta-modal');
    modal.style.display = 'flex';
    setTimeout(function() { modal.classList.add('active'); }, 10);
};

window.excluirItem = function(itemId) {
    console.log('[PROJECOES] Excluindo item:', itemId);
    
    if (!confirm('Tem certeza que deseja excluir este item?')) {
        return;
    }
    
    mostrarLoading(true);
    
    fetch('/financeiro/projecoes-metas/api/excluir/' + itemId, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success !== false) {
            mostrarToast(data.message || 'Item excluído com sucesso', 'success');
            buscarDados();
        } else {
            mostrarToast(data.error || 'Erro ao excluir', 'error');
        }
    })
    .catch(error => {
        console.error('[PROJECOES] Erro ao excluir:', error);
        mostrarToast('Erro de comunicação com o servidor', 'error');
    })
    .finally(function() {
        mostrarLoading(false);
    });
};

function fecharModal() {
    const modal = document.getElementById('meta-modal');
    modal.classList.remove('active');
    setTimeout(function() { modal.style.display = 'none'; }, 300);
    editandoItem = null;
    tipoEdicao = null;
}

function salvarItem() {
    console.log('[PROJECOES] Salvando item - Modo:', modoModal, 'Tipo:', tipoEdicao, 'Editando:', editandoItem ? editandoItem.id : null);
    
    if (modoModal === 'lote' && !editandoItem) {
        salvarLote();
        return;
    }
    
    const valorInput = document.getElementById('meta-modal-valor');
    const valorNumerico = obterValorNumerico(valorInput);
    
    var dadosItem = {
        ano: parseInt(document.getElementById('meta-modal-ano').value),
        mes: document.getElementById('meta-modal-mes').value,
        meta: valorNumerico,
        tipo: tipoEdicao
    };
    
    if (!dadosItem.ano || !dadosItem.mes || !dadosItem.meta || !dadosItem.tipo) {
        mostrarToast('Preencha todos os campos obrigatórios', 'warning');
        return;
    }
    
    console.log('[PROJECOES] Dados para salvar:', dadosItem);
    
    mostrarLoading(true);
    
    var url, method;
    if (editandoItem) {
        url = '/financeiro/projecoes-metas/api/atualizar/' + editandoItem.id;
        method = 'PUT';
    } else {
        url = '/financeiro/projecoes-metas/api/criar';
        method = 'POST';
    }
    
    fetch(url, {
        method: method,
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(dadosItem)
    })
    .then(response => response.json())
    .then(data => {
        console.log('[PROJECOES] Resposta do servidor:', data);
        if (data.success !== false) {
            mostrarToast(data.message || 'Salvo com sucesso', 'success');
            fecharModal();
            buscarDados();
        } else {
            mostrarToast(data.error || 'Erro ao salvar', 'error');
        }
    })
    .catch(error => {
        console.error('[PROJECOES] Erro ao salvar:', error);
        mostrarToast('Erro de comunicação com o servidor', 'error');
    })
    .finally(function() {
        mostrarLoading(false);
    });
}

function salvarLote() {
    console.log('[PROJECOES] Salvando em lote');
    
    const itens = [];
    const linhas = document.querySelectorAll('.mes-valor-linha');
    
    if (linhas.length === 0) {
        mostrarToast('Adicione pelo menos um mês e valor', 'warning');
        return;
    }
    
    const ano = parseInt(document.getElementById('meta-modal-ano-lote').value);
    
    if (!ano) {
        mostrarToast('Selecione um ano válido', 'warning');
        return;
    }
    
    var valido = true;
    const mesesUsados = new Set();
    
    linhas.forEach(function(linha, index) {
        const selectMes = linha.querySelector('.select-mes');
        const inputValor = linha.querySelector('.input-valor');
        
        if (!selectMes || !inputValor) {
            valido = false;
            return;
        }
        
        const mes = selectMes.value;
        const valorNumerico = obterValorNumerico(inputValor);
        
        if (!mes) {
            mostrarToast('Linha ' + (index + 1) + ': Selecione um mês', 'warning');
            valido = false;
            return;
        }
        
        if (!valorNumerico || valorNumerico <= 0) {
            mostrarToast('Linha ' + (index + 1) + ': Digite um valor válido', 'warning');
            valido = false;
            return;
        }
        
        if (mesesUsados.has(mes)) {
            mostrarToast('Linha ' + (index + 1) + ': Mês ' + formatarMes(mes) + ' já foi usado', 'warning');
            valido = false;
            return;
        }
        
        mesesUsados.add(mes);
        
        itens.push({
            ano: ano,
            mes: mes,
            meta: valorNumerico,
            tipo: tipoEdicao
        });
    });
    
    if (!valido || itens.length === 0) {
        return;
    }
    
    const dadosLote = {
        itens: itens
    };
    
    console.log('[PROJECOES] Dados para lote:', dadosLote);
    
    mostrarLoading(true);
    
    fetch('/financeiro/projecoes-metas/api/criar-lote', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(dadosLote)
    })
    .then(response => response.json())
    .then(data => {
        console.log('[PROJECOES] Resposta do servidor (lote):', data);
        if (data.success !== false) {
            mostrarToast(data.message || 'Itens criados com sucesso', 'success');
            fecharModal();
            buscarDados();
        } else {
            mostrarToast(data.error || 'Erro ao criar itens', 'error');
        }
    })
    .catch(error => {
        console.error('[PROJECOES] Erro ao criar lote:', error);
        mostrarToast('Erro de comunicação com o servidor', 'error');
    })
    .finally(function() {
        mostrarLoading(false);
    });
}

function mostrarLoading(mostrar) {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.style.display = mostrar ? 'flex' : 'none';
    }
}

function mostrarToast(mensagem, tipo) {
    console.log('[PROJECOES] Toast:', mensagem, tipo);
    
    const toast = document.createElement('div');
    toast.className = 'toast toast-' + tipo;
    toast.textContent = mensagem;
    
    var container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container';
        document.body.appendChild(container);
    }
    
    container.appendChild(toast);
    
    setTimeout(function() { toast.classList.add('show'); }, 100);
    
    setTimeout(function() {
        toast.classList.remove('show');
        setTimeout(function() {
            if (container.contains(toast)) {
                container.removeChild(toast);
            }
        }, 300);
    }, 3000);
}

function formatarMoeda(valor) {
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(valor || 0);
}

function formatarData(data) {
    if (!data) return '-';
    return new Date(data).toLocaleDateString('pt-BR');
}

function formatarMes(mes) {
    var meses = {
        '01': 'Janeiro', '02': 'Fevereiro', '03': 'Março',
        '04': 'Abril', '05': 'Maio', '06': 'Junho',
        '07': 'Julho', '08': 'Agosto', '09': 'Setembro',
        '10': 'Outubro', '11': 'Novembro', '12': 'Dezembro'
    };
    return meses[mes] || mes;
}

function switchModalTab(modo) {
    console.log('[PROJECOES] Mudando modo do modal para:', modo);
    
    modoModal = modo;
    
    document.querySelectorAll('.modo-tab').forEach(function(tab) {
        tab.classList.remove('active');
    });
    document.querySelector('[data-modo="' + modo + '"]').classList.add('active');
    
    document.querySelectorAll('.form-section').forEach(function(section) {
        section.classList.remove('active');
    });
    document.getElementById('form-' + modo).classList.add('active');
    
    const saveText = document.getElementById('save-text');
    if (modo === 'lote') {
        saveText.textContent = 'Criar Múltiplas';
    } else {
        saveText.textContent = 'Salvar';
    }
}

function preencherAnosDinamicos() {
    const anoAtual = new Date().getFullYear();
    const anos = [anoAtual, anoAtual + 1, anoAtual + 2];
    
    const selectIndividual = document.getElementById('meta-modal-ano');
    selectIndividual.innerHTML = '';
    anos.forEach(function(ano) {
        const option = document.createElement('option');
        option.value = ano;
        option.textContent = ano;
        if (ano === anoAtual + 1) option.selected = true;
        selectIndividual.appendChild(option);
    });
    
    const selectLote = document.getElementById('meta-modal-ano-lote');
    selectLote.innerHTML = '';
    anos.forEach(function(ano) {
        const option = document.createElement('option');
        option.value = ano;
        option.textContent = ano;
        if (ano === anoAtual + 1) option.selected = true;
        selectLote.appendChild(option);
    });
}

function configurarFormatacaoMoeda() {
    const moneyInputs = document.querySelectorAll('.money-input');
    
    moneyInputs.forEach(function(input) {
        input.addEventListener('input', function(e) {
            formatarCampoMoeda(e.target);
        });
        
        input.addEventListener('blur', function(e) {
            formatarCampoMoeda(e.target);
        });
    });
}

function formatarCampoMoeda(input) {
    var valor = input.value.replace(/\D/g, '');
    
    if (valor === '') {
        input.value = '';
        return;
    }
    
    var numero = parseInt(valor);
    
    var formatado = new Intl.NumberFormat('pt-BR', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(numero / 100);
    
    input.value = formatado;
}

function obterValorNumerico(input) {
    var valor = input.value.replace(/\./g, '').replace(',', '.');
    return parseFloat(valor) || 0;
}

function adicionarLinhaMesValor() {
    console.log('[PROJECOES] Adicionando linha de mês-valor');
    
    const lista = document.getElementById('meses-valores-lista');
    const linhaDivv = document.createElement('div');
    linhaDivv.className = 'mes-valor-linha';
    
    const mesesUsados = new Set();
    document.querySelectorAll('.select-mes').forEach(function(select) {
        if (select.value) mesesUsados.add(select.value);
    });
    
    linhaDivv.innerHTML = '<select class="select-mes"><option value="">Selecione...</option><option value="01"' + (mesesUsados.has('01') ? ' disabled' : '') + '>Janeiro</option><option value="02"' + (mesesUsados.has('02') ? ' disabled' : '') + '>Fevereiro</option><option value="03"' + (mesesUsados.has('03') ? ' disabled' : '') + '>Março</option><option value="04"' + (mesesUsados.has('04') ? ' disabled' : '') + '>Abril</option><option value="05"' + (mesesUsados.has('05') ? ' disabled' : '') + '>Maio</option><option value="06"' + (mesesUsados.has('06') ? ' disabled' : '') + '>Junho</option><option value="07"' + (mesesUsados.has('07') ? ' disabled' : '') + '>Julho</option><option value="08"' + (mesesUsados.has('08') ? ' disabled' : '') + '>Agosto</option><option value="09"' + (mesesUsados.has('09') ? ' disabled' : '') + '>Setembro</option><option value="10"' + (mesesUsados.has('10') ? ' disabled' : '') + '>Outubro</option><option value="11"' + (mesesUsados.has('11') ? ' disabled' : '') + '>Novembro</option><option value="12"' + (mesesUsados.has('12') ? ' disabled' : '') + '>Dezembro</option></select><input type="text" class="input-valor money-input" placeholder="0,00"><button type="button" class="btn-remover-linha" onclick="removerLinhaMesValor(this)"><i class="mdi mdi-delete"></i></button>';
    
    lista.appendChild(linhaDivv);
    
    const inputValor = linhaDivv.querySelector('.input-valor');
    inputValor.addEventListener('input', function(e) {
        formatarCampoMoeda(e.target);
    });
    inputValor.addEventListener('blur', function(e) {
        formatarCampoMoeda(e.target);
    });
    
    const selectMes = linhaDivv.querySelector('.select-mes');
    selectMes.addEventListener('change', atualizarDisponibilidadeMeses);
    
    selectMes.focus();
}

function removerLinhaMesValor(botao) {
    const linha = botao.closest('.mes-valor-linha');
    linha.remove();
    
    atualizarDisponibilidadeMeses();
    
    const lista = document.getElementById('meses-valores-lista');
    if (lista.children.length === 0) {
        adicionarLinhaMesValor();
    }
}

function atualizarDisponibilidadeMeses() {
    const mesesSelecionados = new Set();
    document.querySelectorAll('.select-mes').forEach(function(select) {
        if (select.value) mesesSelecionados.add(select.value);
    });
    
    document.querySelectorAll('.select-mes').forEach(function(select) {
        const valorAtual = select.value;
        
        select.querySelectorAll('option').forEach(function(option) {
            if (option.value === '') return;
            
            if (option.value === valorAtual) {
                option.disabled = false;
            } else {
                option.disabled = mesesSelecionados.has(option.value);
            }
        });
    });
}

function limparMesesValores() {
    const lista = document.getElementById('meses-valores-lista');
    lista.innerHTML = '';
}

// Função para expandir/colapsar anos
function toggleAno(ano, tab) {
    console.log('[PROJECOES] Toggle ano:', ano, 'tab:', tab);
    
    // Encontrar o botão que foi clicado
    const botao = document.querySelector(`button[data-ano="${ano}"][data-tab="${tab}"]`);
    const icone = botao.querySelector('i');
    
    // Verificar estado atual
    const estaExpandido = icone.classList.contains('mdi-chevron-down');
    const novoEstado = !estaExpandido;
    
    // Atualizar ícone
    icone.classList.toggle('mdi-chevron-down', novoEstado);
    icone.classList.toggle('mdi-chevron-right', !novoEstado);
    
    // Mostrar/ocultar linhas do ano
    const linhasAno = document.querySelectorAll(`.ano-${ano}`);
    linhasAno.forEach(linha => {
        linha.style.display = novoEstado ? 'table-row' : 'none';
    });
    
    // Salvar estado no localStorage
    localStorage.setItem(`projecoes_ano_${ano}_${tab}`, novoEstado.toString());
    
    console.log('[PROJECOES] Ano', ano, novoEstado ? 'expandido' : 'colapsado');
}

window.removerLinhaMesValor = removerLinhaMesValor;
