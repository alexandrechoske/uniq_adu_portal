// Projeções e Metas - JavaScript
console.log('[PROJECOES] Script carregado');

let dados = [];
let editandoItem = null;
let tipoEdicao = null;
let tabAtiva = 'metas-financeiras';

// Inicialização
document.addEventListener('DOMContentLoaded', function() {
    console.log('[PROJECOES] DOM carregado - Iniciando...');
    
    try {
        // Configurar tabs
        configurarTabs();
        
        // Configurar eventos
        configurarEventos();
        
        // Carregar dados iniciais
        buscarDados();
        
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
            const tabId = this.dataset.tab;
            console.log('[PROJECOES] Clicou na aba:', tabId);
            switchTab(tabId);
        });
    });
}

function switchTab(tabId) {
    console.log('[PROJECOES] Mudando para aba:', tabId);
    
    // Atualizar botões
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`[data-tab="${tabId}"]`).classList.add('active');
    
    // Esconder todos os conteúdos
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    
    // Mostrar conteúdo selecionado
    document.getElementById(`content-${tabId}`).classList.add('active');
    
    tabAtiva = tabId;
    console.log('[PROJECOES] Aba ativa:', tabId);
}

function configurarEventos() {
    console.log('[PROJECOES] Configurando eventos...');
    
    try {
        // Filtros
        document.getElementById('btn-buscar').addEventListener('click', buscarDados);
        document.getElementById('btn-limpar-filtros').addEventListener('click', limparFiltros);
        
        // Botões de nova meta/projeção
        document.getElementById('btn-nova-meta-financeira').addEventListener('click', () => abrirModal('financeiro'));
        document.getElementById('btn-nova-meta-operacional').addEventListener('click', () => abrirModal('operacional'));
        document.getElementById('btn-nova-projecao').addEventListener('click', () => abrirModal('projecao'));
        
        // Modais
        configurarModais();
        
        console.log('[PROJECOES] Eventos configurados');
    } catch (error) {
        console.error('[PROJECOES] Erro ao configurar eventos:', error);
    }
}

function configurarModais() {
    console.log('[PROJECOES] Configurando modais...');
    
    // Modal centralizado
    document.getElementById('meta-modal-close').addEventListener('click', fecharModal);
    document.getElementById('meta-modal-cancel').addEventListener('click', fecharModal);
    document.getElementById('meta-modal-save').addEventListener('click', salvarItem);
    
    // Fechar modal ao clicar no overlay
    document.getElementById('meta-modal').addEventListener('click', function(e) {
        if (e.target === this) fecharModal();
    });
}

function buscarDados() {
    const ano = document.getElementById('ano-filtro').value;
    const tipo = document.getElementById('tipo-filtro').value;
    
    console.log('[PROJECOES] Buscando dados - Ano:', ano, 'Tipo:', tipo);
    
    mostrarLoading(true);
    
    const params = new URLSearchParams();
    if (ano) params.append('ano', ano);
    if (tipo) params.append('tipo', tipo);
    
    const url = `/financeiro/projecoes-metas/api/dados?${params.toString()}`;
    console.log('[PROJECOES] URL da requisição:', url);
    
    fetch(url)
        .then(response => {
            console.log('[PROJECOES] Status da resposta:', response.status);
            return response.json();
        })
        .then(data => {
            console.log('[PROJECOES] Dados recebidos:', data);
            
            if (data.success !== false) {
                // Se não tem propriedade success ou success é true
                dados = Array.isArray(data) ? data : (data.data || []);
                renderizarDados();
                atualizarEstatisticas();
                console.log('[PROJECOES] Dados carregados:', dados.length, 'itens');
            } else {
                mostrarToast(data.error || 'Erro ao buscar dados', 'error');
                dados = [];
                renderizarDados();
                atualizarEstatisticas();
            }
        })
        .catch(error => {
            console.error('[PROJECOES] Erro ao buscar dados:', error);
            mostrarToast('Erro de comunicação com o servidor', 'error');
            dados = [];
            renderizarDados();
            atualizarEstatisticas();
        })
        .finally(() => {
            mostrarLoading(false);
        });
}

function renderizarDados() {
    console.log('[PROJECOES] Renderizando dados:', dados.length, 'itens');
    renderizarMetasFinanceiras();
    renderizarMetasOperacionais();
    renderizarProjecoes();
}

function renderizarMetasFinanceiras() {
    const tbody = document.getElementById('table-metas-financeiras-tbody');
    const metas = dados.filter(item => item.tipo === 'financeiro');
    
    console.log('[PROJECOES] Metas financeiras:', metas.length);
    tbody.innerHTML = '';
    
    if (metas.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" style="text-align: center; padding: 40px; color: #666;">
                    <i class="mdi mdi-cash-multiple" style="font-size: 48px; display: block; margin-bottom: 10px;"></i>
                    Nenhuma meta financeira encontrada
                </td>
            </tr>
        `;
        return;
    }
    
    metas.forEach(meta => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${meta.ano}</td>
            <td>${formatarMes(meta.mes)}</td>
            <td><span class="valor-financeira">${formatarMoeda(meta.meta)}</span></td>
            <td>${formatarData(meta.created_at)}</td>
            <td>
                <button class="btn btn-primary btn-sm" onclick="editarItem(${meta.id}, 'financeiro')">
                    <i class="mdi mdi-pencil"></i>
                </button>
                <button class="btn btn-warning btn-sm" onclick="excluirItem(${meta.id})" style="margin-left: 5px;">
                    <i class="mdi mdi-delete"></i>
                </button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

function renderizarMetasOperacionais() {
    const tbody = document.getElementById('table-metas-operacionais-tbody');
    const metas = dados.filter(item => item.tipo === 'operacional');
    
    console.log('[PROJECOES] Metas operacionais:', metas.length);
    tbody.innerHTML = '';
    
    if (metas.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" style="text-align: center; padding: 40px; color: #666;">
                    <i class="mdi mdi-chart-timeline-variant" style="font-size: 48px; display: block; margin-bottom: 10px;"></i>
                    Nenhuma meta operacional encontrada
                </td>
            </tr>
        `;
        return;
    }
    
    metas.forEach(meta => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${meta.ano}</td>
            <td>${formatarMes(meta.mes)}</td>
            <td><span class="valor-operacional">${formatarMoeda(meta.meta)}</span></td>
            <td>${formatarData(meta.created_at)}</td>
            <td>
                <button class="btn btn-warning btn-sm" onclick="editarItem(${meta.id}, 'operacional')">
                    <i class="mdi mdi-pencil"></i>
                </button>
                <button class="btn btn-warning btn-sm" onclick="excluirItem(${meta.id})" style="margin-left: 5px;">
                    <i class="mdi mdi-delete"></i>
                </button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

function renderizarProjecoes() {
    const tbody = document.getElementById('table-projecoes-tbody');
    const projecoes = dados.filter(item => item.tipo === 'projecao');
    
    console.log('[PROJECOES] Projeções:', projecoes.length);
    tbody.innerHTML = '';
    
    if (projecoes.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" style="text-align: center; padding: 40px; color: #666;">
                    <i class="mdi mdi-trending-up" style="font-size: 48px; display: block; margin-bottom: 10px;"></i>
                    Nenhuma projeção encontrada
                </td>
            </tr>
        `;
        return;
    }
    
    projecoes.forEach(projecao => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${projecao.ano}</td>
            <td>${formatarMes(projecao.mes)}</td>
            <td><span class="valor-projecao">${formatarMoeda(projecao.meta)}</span></td>
            <td>${formatarData(projecao.created_at)}</td>
            <td>
                <button class="btn btn-success btn-sm" onclick="editarItem(${projecao.id}, 'projecao')">
                    <i class="mdi mdi-pencil"></i>
                </button>
                <button class="btn btn-warning btn-sm" onclick="excluirItem(${projecao.id})" style="margin-left: 5px;">
                    <i class="mdi mdi-delete"></i>
                </button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

function atualizarEstatisticas() {
    const financeiras = dados.filter(item => item.tipo === 'financeiro').length;
    const operacionais = dados.filter(item => item.tipo === 'operacional').length;
    const projecoes = dados.filter(item => item.tipo === 'projecao').length;
    
    console.log('[PROJECOES] Estatísticas - Financeiras:', financeiras, 'Operacionais:', operacionais, 'Projeções:', projecoes);
    
    document.getElementById('total-financeiras').textContent = financeiras;
    document.getElementById('total-operacionais').textContent = operacionais;
    document.getElementById('total-projecoes').textContent = projecoes;
}

function abrirModal(tipo) {
    console.log('[PROJECOES] Abrindo modal para tipo:', tipo);
    
    tipoEdicao = tipo;
    editandoItem = null;
    
    // Definir título baseado no tipo
    const titulos = {
        'financeiro': 'Nova Meta Financeira',
        'operacional': 'Nova Meta Operacional',
        'projecao': 'Nova Projeção'
    };
    
    document.getElementById('meta-modal-title').textContent = titulos[tipo];
    document.getElementById('meta-modal-ano').value = '2025';
    document.getElementById('meta-modal-mes').value = '01';
    document.getElementById('meta-modal-valor').value = '';
    
    // Mostrar modal com classe active para animação
    const modal = document.getElementById('meta-modal');
    modal.style.display = 'flex';
    setTimeout(() => modal.classList.add('active'), 10);
}

// Funções globais para os botões
window.editarItem = function(itemId, tipo) {
    console.log('[PROJECOES] Editando item:', itemId, 'tipo:', tipo);
    
    const item = dados.find(d => d.id === itemId);
    if (!item) {
        mostrarToast('Item não encontrado', 'error');
        return;
    }
    
    tipoEdicao = tipo;
    editandoItem = item;
    
    // Definir título baseado no tipo
    const titulos = {
        'financeiro': 'Editar Meta Financeira',
        'operacional': 'Editar Meta Operacional',
        'projecao': 'Editar Projeção'
    };
    
    document.getElementById('meta-modal-title').textContent = titulos[tipo];
    document.getElementById('meta-modal-ano').value = item.ano;
    document.getElementById('meta-modal-mes').value = item.mes;
    document.getElementById('meta-modal-valor').value = item.meta;
    
    // Mostrar modal
    const modal = document.getElementById('meta-modal');
    modal.style.display = 'flex';
    setTimeout(() => modal.classList.add('active'), 10);
};

window.excluirItem = function(itemId) {
    console.log('[PROJECOES] Excluindo item:', itemId);
    
    if (!confirm('Tem certeza que deseja excluir este item?')) {
        return;
    }
    
    mostrarLoading(true);
    
    fetch(`/financeiro/projecoes-metas/api/excluir/${itemId}`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success !== false) {
            mostrarToast(data.message || 'Excluído com sucesso', 'success');
            buscarDados(); // Recarregar dados
        } else {
            mostrarToast(data.error || 'Erro ao excluir', 'error');
        }
    })
    .catch(error => {
        console.error('[PROJECOES] Erro ao excluir:', error);
        mostrarToast('Erro de comunicação com o servidor', 'error');
    })
    .finally(() => {
        mostrarLoading(false);
    });
};

function fecharModal() {
    const modal = document.getElementById('meta-modal');
    modal.classList.remove('active');
    setTimeout(() => modal.style.display = 'none', 300);
    editandoItem = null;
    tipoEdicao = null;
}

function salvarItem() {
    console.log('[PROJECOES] Salvando item - Tipo:', tipoEdicao, 'Editando:', editandoItem?.id);
    
    let dadosItem = {
        ano: document.getElementById('meta-modal-ano').value,
        mes: document.getElementById('meta-modal-mes').value,
        meta: parseFloat(document.getElementById('meta-modal-valor').value),
        tipo: tipoEdicao
    };
    
    // Validação
    if (!dadosItem.ano || !dadosItem.mes || !dadosItem.meta || !dadosItem.tipo) {
        mostrarToast('Preencha todos os campos obrigatórios', 'warning');
        return;
    }
    
    console.log('[PROJECOES] Dados para salvar:', dadosItem);
    
    mostrarLoading(true);
    
    let url, method;
    if (editandoItem) {
        url = `/financeiro/projecoes-metas/api/atualizar/${editandoItem.id}`;
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
            buscarDados(); // Recarregar dados
        } else {
            mostrarToast(data.error || 'Erro ao salvar', 'error');
        }
    })
    .catch(error => {
        console.error('[PROJECOES] Erro ao salvar:', error);
        mostrarToast('Erro de comunicação com o servidor', 'error');
    })
    .finally(() => {
        mostrarLoading(false);
    });
}

function limparFiltros() {
    document.getElementById('ano-filtro').value = '2025';
    document.getElementById('tipo-filtro').value = '';
    buscarDados();
}

function mostrarLoading(mostrar) {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.style.display = mostrar ? 'flex' : 'none';
    }
}

function mostrarToast(mensagem, tipo = 'info') {
    console.log('[PROJECOES] Toast:', mensagem, tipo);
    
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
        setTimeout(() => {
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
    const meses = {
        '01': 'Janeiro', '02': 'Fevereiro', '03': 'Março',
        '04': 'Abril', '05': 'Maio', '06': 'Junho',
        '07': 'Julho', '08': 'Agosto', '09': 'Setembro',
        '10': 'Outubro', '11': 'Novembro', '12': 'Dezembro'
    };
    return meses[mes] || mes;
}