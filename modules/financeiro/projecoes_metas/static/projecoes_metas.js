// Projeções e Metas - JavaScript
console.log('[PROJECOES] Script carregado');

let dados = [];
let editandoItem = null;
let tipoEdicao = null;
let tabAtiva = 'metas-anuais';

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
        document.getElementById('btn-nova-meta').addEventListener('click', () => abrirModal('meta'));
        document.getElementById('btn-nova-projecao').addEventListener('click', () => abrirModal('projecao'));
        document.getElementById('btn-nova-meta-mensal').addEventListener('click', () => abrirModal('financeiro'));
        
        // Modais
        configurarModais();
        
        console.log('[PROJECOES] Eventos configurados');
    } catch (error) {
        console.error('[PROJECOES] Erro ao configurar eventos:', error);
    }
}

function configurarModais() {
    console.log('[PROJECOES] Configurando modais...');
    
    // Modal Meta/Projeção Anual
    document.getElementById('modal-close-meta').addEventListener('click', () => fecharModal('meta'));
    document.getElementById('modal-cancel-meta').addEventListener('click', () => fecharModal('meta'));
    document.getElementById('modal-save-meta').addEventListener('click', salvarItem);
    
    // Modal Meta Mensal
    document.getElementById('modal-close-mensal').addEventListener('click', () => fecharModal('mensal'));
    document.getElementById('modal-cancel-mensal').addEventListener('click', () => fecharModal('mensal'));
    document.getElementById('modal-save-mensal').addEventListener('click', salvarItem);
    
    // Fechar modal ao clicar no overlay
    document.getElementById('modal-overlay-meta').addEventListener('click', function(e) {
        if (e.target === this) fecharModal('meta');
    });
    document.getElementById('modal-overlay-mensal').addEventListener('click', function(e) {
        if (e.target === this) fecharModal('mensal');
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
    renderizarMetasAnuais();
    renderizarProjecoesAnuais();
    renderizarMetasMensais();
}

function renderizarMetasAnuais() {
    const tbody = document.getElementById('table-metas-anuais-tbody');
    const metas = dados.filter(item => item.tipo === 'meta' && !item.mes);
    
    console.log('[PROJECOES] Metas anuais:', metas.length);
    tbody.innerHTML = '';
    
    if (metas.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="4" style="text-align: center; padding: 40px; color: #666;">
                    <i class="mdi mdi-target" style="font-size: 48px; display: block; margin-bottom: 10px;"></i>
                    Nenhuma meta anual encontrada
                </td>
            </tr>
        `;
        return;
    }
    
    metas.forEach(meta => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${meta.ano}</td>
            <td><span class="valor-meta">${formatarMoeda(meta.meta)}</span></td>
            <td>${formatarData(meta.created_at)}</td>
            <td>
                <button class="btn btn-primary btn-sm" onclick="editarItem(${meta.id}, 'meta')">
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

function renderizarProjecoesAnuais() {
    const tbody = document.getElementById('table-projecoes-anuais-tbody');
    const projecoes = dados.filter(item => item.tipo === 'projecao' && !item.mes);
    
    console.log('[PROJECOES] Projeções anuais:', projecoes.length);
    tbody.innerHTML = '';
    
    if (projecoes.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="4" style="text-align: center; padding: 40px; color: #666;">
                    <i class="mdi mdi-trending-up" style="font-size: 48px; display: block; margin-bottom: 10px;"></i>
                    Nenhuma projeção anual encontrada
                </td>
            </tr>
        `;
        return;
    }
    
    projecoes.forEach(projecao => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${projecao.ano}</td>
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

function renderizarMetasMensais() {
    const tbody = document.getElementById('table-metas-mensais-tbody');
    const mensais = dados.filter(item => item.tipo === 'financeiro' && item.mes);
    
    console.log('[PROJECOES] Metas mensais:', mensais.length);
    tbody.innerHTML = '';
    
    if (mensais.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" style="text-align: center; padding: 40px; color: #666;">
                    <i class="mdi mdi-calendar-month" style="font-size: 48px; display: block; margin-bottom: 10px;"></i>
                    Nenhuma meta mensal encontrada
                </td>
            </tr>
        `;
        return;
    }
    
    mensais.forEach(meta => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${meta.ano}</td>
            <td>${formatarMes(meta.mes)}</td>
            <td><span class="valor-mensal">${formatarMoeda(meta.meta)}</span></td>
            <td>${formatarData(meta.created_at)}</td>
            <td>
                <button class="btn btn-warning btn-sm" onclick="editarItem(${meta.id}, 'financeiro')">
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

function atualizarEstatisticas() {
    const metas = dados.filter(item => item.tipo === 'meta' && !item.mes).length;
    const projecoes = dados.filter(item => item.tipo === 'projecao' && !item.mes).length;
    const mensais = dados.filter(item => item.tipo === 'financeiro' && item.mes).length;
    
    console.log('[PROJECOES] Estatísticas - Metas:', metas, 'Projeções:', projecoes, 'Mensais:', mensais);
    
    document.getElementById('total-metas').textContent = metas;
    document.getElementById('total-projecoes').textContent = projecoes;
    document.getElementById('total-mensais').textContent = mensais;
}

function abrirModal(tipo) {
    console.log('[PROJECOES] Abrindo modal para tipo:', tipo);
    
    tipoEdicao = tipo;
    editandoItem = null;
    
    if (tipo === 'financeiro') {
        // Modal mensal
        document.getElementById('modal-title-mensal').textContent = 'Nova Meta Mensal';
        document.getElementById('meta-mensal-ano').value = '2025';
        document.getElementById('meta-mensal-mes').value = '01';
        document.getElementById('meta-mensal-valor').value = '';
        document.getElementById('modal-overlay-mensal').style.display = 'flex';
    } else {
        // Modal anual
        const titulo = tipo === 'meta' ? 'Nova Meta Anual' : 'Nova Projeção Anual';
        document.getElementById('modal-title-anual').textContent = titulo;
        document.getElementById('meta-ano').value = '2025';
        document.getElementById('meta-valor').value = '';
        document.getElementById('modal-overlay-meta').style.display = 'flex';
    }
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
    
    if (tipo === 'financeiro') {
        // Modal mensal
        document.getElementById('modal-title-mensal').textContent = 'Editar Meta Mensal';
        document.getElementById('meta-mensal-ano').value = item.ano;
        document.getElementById('meta-mensal-mes').value = item.mes;
        document.getElementById('meta-mensal-valor').value = item.meta;
        document.getElementById('modal-overlay-mensal').style.display = 'flex';
    } else {
        // Modal anual
        const titulo = tipo === 'meta' ? 'Editar Meta Anual' : 'Editar Projeção Anual';
        document.getElementById('modal-title-anual').textContent = titulo;
        document.getElementById('meta-ano').value = item.ano;
        document.getElementById('meta-valor').value = item.meta;
        document.getElementById('modal-overlay-meta').style.display = 'flex';
    }
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

function fecharModal(modalTipo) {
    if (modalTipo === 'mensal') {
        document.getElementById('modal-overlay-mensal').style.display = 'none';
    } else {
        document.getElementById('modal-overlay-meta').style.display = 'none';
    }
    editandoItem = null;
    tipoEdicao = null;
}

function salvarItem() {
    console.log('[PROJECOES] Salvando item - Tipo:', tipoEdicao, 'Editando:', editandoItem?.id);
    
    let dadosItem;
    
    if (tipoEdicao === 'financeiro') {
        dadosItem = {
            ano: document.getElementById('meta-mensal-ano').value,
            mes: document.getElementById('meta-mensal-mes').value,
            meta: parseFloat(document.getElementById('meta-mensal-valor').value),
            tipo: 'financeiro'
        };
    } else {
        dadosItem = {
            ano: document.getElementById('meta-ano').value,
            meta: parseFloat(document.getElementById('meta-valor').value),
            tipo: tipoEdicao
        };
    }
    
    // Validação
    if (!dadosItem.ano || !dadosItem.meta || !dadosItem.tipo) {
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
            fecharModal(tipoEdicao === 'financeiro' ? 'mensal' : 'meta');
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