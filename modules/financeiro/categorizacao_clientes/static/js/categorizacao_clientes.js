// JavaScript para página de Categorização de Clientes
// Variáveis globais
let clientes = [];
let clientesEditados = new Set();
let paginacao = { total: 0, limit: 50, offset: 0, has_more: false };

// Inicialização
document.addEventListener('DOMContentLoaded', function() {
    M.AutoInit();
    
    carregarEstatisticas();
    buscarClientes();
    
    // Event listeners
    const selectAll = document.getElementById('select-all');
    if (selectAll) {
        selectAll.addEventListener('change', selecionarTodos);
    }
    
    const buscaCliente = document.getElementById('busca-cliente');
    if (buscaCliente) {
        buscaCliente.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') buscarClientes();
        });
    }
});

function carregarEstatisticas() {
    fetch('/financeiro/categorizacao-clientes/api/estatisticas')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                document.getElementById('total-clientes').textContent = data.data.total_clientes;
                document.getElementById('total-categorizados').textContent = data.data.total_categorizados;
                document.getElementById('total-nao-categorizados').textContent = data.data.total_nao_categorizados;
                document.getElementById('percentual-categorizado').textContent = data.data.percentual_categorizado + '%';
            }
        })
        .catch(error => {
            console.error('Erro:', error);
            M.toast({html: 'Erro ao carregar estatísticas', classes: 'red'});
        });
}

function popularTabela() {
    mostrarLoading(true);
    
    fetch('/financeiro/categorizacao-clientes/api/popular-tabela', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            M.toast({html: data.message, classes: 'green'});
            carregarEstatisticas();
            buscarClientes();
        } else {
            M.toast({html: data.error, classes: 'red'});
        }
    })
    .catch(error => {
        console.error('Erro:', error);
        M.toast({html: 'Erro ao atualizar base de dados', classes: 'red'});
    })
    .finally(() => {
        mostrarLoading(false);
    });
}

function buscarClientes(carregarMais = false) {
    if (!carregarMais) {
        paginacao.offset = 0;
        clientes = [];
    }
    
    mostrarLoading(true);
    
    const buscaInput = document.getElementById('busca-cliente');
    const statusSelect = document.getElementById('status-filtro');
    
    const params = new URLSearchParams({
        busca: buscaInput ? buscaInput.value : '',
        status: statusSelect ? statusSelect.value : 'nao_categorizados',
        limit: paginacao.limit,
        offset: paginacao.offset
    });

    fetch(`/financeiro/categorizacao-clientes/api/clientes?${params}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                if (carregarMais) {
                    clientes = clientes.concat(data.data);
                } else {
                    clientes = data.data;
                }
                
                paginacao = data.pagination;
                renderizarTabela();
                atualizarPaginacao();
            } else {
                M.toast({html: data.error, classes: 'red'});
            }
        })
        .catch(error => {
            console.error('Erro:', error);
            M.toast({html: 'Erro ao buscar clientes', classes: 'red'});
        })
        .finally(() => {
            mostrarLoading(false);
        });
}

function renderizarTabela() {
    const tbody = document.getElementById('tabela-clientes');
    if (!tbody) return;
    
    tbody.innerHTML = '';

    clientes.forEach((cliente, index) => {
        const row = document.createElement('tr');
        row.dataset.index = index;
        row.dataset.nomeOriginal = cliente.nome_original;
        
        const foiEditado = cliente.nome_padronizado !== cliente.nome_original;
        const statusClass = foiEditado ? 'status-categorizado' : 'status-pendente';
        const statusText = foiEditado ? 'Categorizado' : 'Pendente';
        
        row.innerHTML = `
            <td class="checkbox-cell">
                <label>
                    <input type="checkbox" class="cliente-checkbox" onchange="atualizarSelecao()">
                    <span></span>
                </label>
            </td>
            <td>
                <div class="nome-original" title="${cliente.nome_original}">
                    ${cliente.nome_original}
                </div>
            </td>
            <td>
                <input type="text" 
                       class="nome-padronizado-input" 
                       value="${cliente.nome_padronizado}" 
                       data-original="${cliente.nome_original}"
                       data-valor-inicial="${cliente.nome_padronizado}"
                       onchange="marcarComoEditado(this)"
                       placeholder="Digite o nome corrigido">
            </td>
            <td>
                <span class="status-badge ${statusClass}">${statusText}</span>
            </td>
            <td>
                <small style="color: #666;">
                    ${cliente.updated_at ? formatarData(cliente.updated_at) : 'Não atualizado'}
                </small>
            </td>
        `;
        
        tbody.appendChild(row);
    });
    
    // Verificar se há itens já editados na sessão atual
    document.querySelectorAll('.nome-padronizado-input').forEach(input => {
        marcarComoEditado(input, false);
    });
}

function marcarComoEditado(input, mostrarToast = true) {
    const valorAtual = input.value.trim();
    const valorInicial = input.dataset.valorInicial;
    const nomeOriginal = input.dataset.original;
    
    if (valorAtual !== valorInicial) {
        input.classList.add('changed');
        clientesEditados.add(nomeOriginal);
        
        // Auto-selecionar checkbox da linha
        const row = input.closest('tr');
        const checkbox = row.querySelector('.cliente-checkbox');
        if (checkbox) {
            checkbox.checked = true;
        }
        
        if (mostrarToast) {
            M.toast({html: 'Cliente marcado para salvamento', classes: 'orange', displayLength: 2000});
        }
    } else {
        input.classList.remove('changed');
        clientesEditados.delete(nomeOriginal);
    }
    
    atualizarSelecao();
}

function selecionarTodos() {
    const selectAll = document.getElementById('select-all');
    const checkboxes = document.querySelectorAll('.cliente-checkbox');
    
    if (selectAll) {
        checkboxes.forEach(checkbox => {
            checkbox.checked = selectAll.checked;
        });
    }
    
    atualizarSelecao();
}

function atualizarSelecao() {
    const checkboxesMarcados = document.querySelectorAll('.cliente-checkbox:checked');
    const count = checkboxesMarcados.length;
    
    const countElement = document.getElementById('count-selecionados');
    const btnSalvar = document.getElementById('btn-salvar');
    
    if (countElement) {
        countElement.textContent = count;
    }
    
    if (btnSalvar) {
        btnSalvar.disabled = count === 0;
    }
    
    // Atualizar classe visual das linhas selecionadas
    document.querySelectorAll('.cliente-checkbox').forEach(checkbox => {
        const row = checkbox.closest('tr');
        if (checkbox.checked) {
            row.classList.add('selected');
        } else {
            row.classList.remove('selected');
        }
    });
}

function salvarSelecionados() {
    const checkboxesMarcados = document.querySelectorAll('.cliente-checkbox:checked');
    const clientesParaSalvar = [];
    
    checkboxesMarcados.forEach(checkbox => {
        const row = checkbox.closest('tr');
        const nomeOriginal = row.dataset.nomeOriginal;
        const inputNome = row.querySelector('.nome-padronizado-input');
        const nomePadronizado = inputNome.value.trim();
        
        if (nomePadronizado) {
            clientesParaSalvar.push({
                nome_original: nomeOriginal,
                nome_padronizado: nomePadronizado
            });
        }
    });
    
    if (clientesParaSalvar.length === 0) {
        M.toast({html: 'Nenhum cliente válido para salvar', classes: 'orange'});
        return;
    }
    
    mostrarLoading(true);
    
    fetch('/financeiro/categorizacao-clientes/api/salvar-categorizacao', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ clientes: clientesParaSalvar })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            M.toast({html: data.message, classes: 'green'});
            
            // Limpar edições e recarregar dados
            clientesEditados.clear();
            limparSelecao();
            carregarEstatisticas();
            buscarClientes();
        } else {
            M.toast({html: data.error, classes: 'red'});
            if (data.detalhes && data.detalhes.erros.length > 0) {
                console.error('Erros detalhados:', data.detalhes.erros);
            }
        }
    })
    .catch(error => {
        console.error('Erro:', error);
        M.toast({html: 'Erro ao salvar categorização', classes: 'red'});
    })
    .finally(() => {
        mostrarLoading(false);
    });
}

function limparSelecao() {
    const selectAll = document.getElementById('select-all');
    if (selectAll) {
        selectAll.checked = false;
    }
    
    document.querySelectorAll('.cliente-checkbox').forEach(checkbox => {
        checkbox.checked = false;
    });
    atualizarSelecao();
}

function carregarMais() {
    paginacao.offset += paginacao.limit;
    buscarClientes(true);
}

function atualizarPaginacao() {
    const info = document.getElementById('pagination-info');
    const btnCarregarMais = document.getElementById('btn-carregar-mais');
    
    if (info) {
        const exibindo = Math.min(paginacao.offset + paginacao.limit, paginacao.total);
        info.textContent = `Exibindo ${clientes.length} de ${paginacao.total} clientes`;
    }
    
    if (btnCarregarMais) {
        if (paginacao.has_more) {
            btnCarregarMais.style.display = 'inline-block';
        } else {
            btnCarregarMais.style.display = 'none';
        }
    }
}

function mostrarLoading(mostrar) {
    const loadingOverlay = document.getElementById('loading-overlay');
    if (loadingOverlay) {
        loadingOverlay.style.display = mostrar ? 'flex' : 'none';
    }
}

function formatarData(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('pt-BR') + ' ' + date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
}
