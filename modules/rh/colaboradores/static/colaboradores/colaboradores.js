// ===================================================================
// JAVASCRIPT DO MÓDULO RH - COLABORADORES
// ===================================================================

// Variáveis globais para armazenar IDs de ações críticas
let colaboradorIdParaDesligar = null;
let colaboradorIdParaReativar = null;
const colaboradorCache = new Map();
let linhasFiltradas = [];
let paginaAtual = 1;
const itensPorPagina = 12;

window.RH_BENEFICIOS_CATALOGO = window.RH_BENEFICIOS_CATALOGO || [];

// Variáveis globais para ordenação
let currentSortColumn = null;
let currentSortDirection = 'asc';

// ===================================================================
// INICIALIZAÇÃO
// ===================================================================
document.addEventListener('DOMContentLoaded', function() {
    console.log('[RH] Módulo de Colaboradores inicializado');
    
    // Inicializar filtros e busca
    inicializarFiltros();
    
    // Inicializar ordenação de tabela
    inicializarOrdenacao();
    
    // Inicializar modal de desligamento
    inicializarModalDesligamento();
    inicializarModalReativacao();
    
    inicializarPromocao();
    inicializarReajuste();
    inicializarTransferencia();
    inicializarFerias();
    inicializarDependentesPerfil();
    inicializarContatosPerfil();
    inicializarBeneficiosPerfil();

    // Inicializar tooltips do Bootstrap
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    filtrarTabela();
});

// ===================================================================
// FILTROS E BUSCA
// ===================================================================
function inicializarFiltros() {
    const searchInput = document.getElementById('searchInput');
    const filterStatus = document.getElementById('filterStatus');
    const filterCargo = document.getElementById('filterCargo');
    const filterDepartamento = document.getElementById('filterDepartamento');
    const btnLimpar = document.getElementById('btnLimparFiltros');
    
    if (searchInput) {
        searchInput.addEventListener('input', filtrarTabela);
    }
    
    if (filterStatus) {
        filterStatus.addEventListener('change', filtrarTabela);
    }

    if (filterCargo) {
        filterCargo.addEventListener('change', filtrarTabela);
    }

    if (filterDepartamento) {
        filterDepartamento.addEventListener('change', filtrarTabela);
    }
    
    if (btnLimpar) {
        btnLimpar.addEventListener('click', limparFiltros);
    }
}

function filtrarTabela() {
    const searchInput = document.getElementById('searchInput');
    const filterStatus = document.getElementById('filterStatus');
    const filterCargo = document.getElementById('filterCargo');
    const filterDepartamento = document.getElementById('filterDepartamento');
    const tabela = document.getElementById('tabelaColaboradores');
    
    if (!tabela) return;
    
    const searchTerm = searchInput ? searchInput.value.toLowerCase() : '';
    const statusFiltro = filterStatus ? filterStatus.value : '';
    const cargoFiltro = filterCargo ? filterCargo.value.toLowerCase() : '';
    const departamentoFiltro = filterDepartamento ? filterDepartamento.value.toLowerCase() : '';
    
    const linhas = tabela.getElementsByTagName('tbody')[0].getElementsByTagName('tr');
    linhasFiltradas = [];

    Array.from(linhas).forEach(linha => {
        if (linha.classList.contains('empty-state-row') || linha.getAttribute('data-empty-result') === 'true') {
            linha.style.display = 'none';
            return;
        }

        const colunaMatricula = linha.cells[0] ? linha.cells[0].textContent.toLowerCase() : '';
        const colunaColaborador = linha.cells[1] ? linha.cells[1].textContent.toLowerCase() : '';
        const colunaCargo = linha.cells[2] ? linha.cells[2].textContent.toLowerCase() : '';
        const colunaDepartamento = linha.cells[3] ? linha.cells[3].textContent.toLowerCase() : '';
        const colunaAdmissao = linha.cells[4] ? linha.cells[4].textContent.toLowerCase() : '';

    const status = linha.getAttribute('data-status');
    const cargo = (linha.getAttribute('data-cargo') || '').toLowerCase();
    const departamento = (linha.getAttribute('data-departamento') || '').toLowerCase();

        const matchSearch = !searchTerm ||
            colunaMatricula.includes(searchTerm) ||
            colunaColaborador.includes(searchTerm) ||
            colunaCargo.includes(searchTerm) ||
            colunaDepartamento.includes(searchTerm) ||
            colunaAdmissao.includes(searchTerm);

        const matchStatus = !statusFiltro || status === statusFiltro;
        const matchCargo = !cargoFiltro || cargo === cargoFiltro;
        const matchDepartamento = !departamentoFiltro || departamento === departamentoFiltro;

        if (matchSearch && matchStatus && matchCargo && matchDepartamento) {
            linhasFiltradas.push(linha);
        } else {
            linha.style.display = 'none';
        }
    });

    paginaAtual = 1;
    aplicarPaginacao();

    console.log(`[RH] Filtros aplicados: ${linhasFiltradas.length} registros após filtragem (busca: "${searchTerm}", status: "${statusFiltro}", cargo: "${cargoFiltro}", departamento: "${departamentoFiltro}")`);
}

function limparFiltros() {
    const searchInput = document.getElementById('searchInput');
    const filterStatus = document.getElementById('filterStatus');
    const filterCargo = document.getElementById('filterCargo');
    const filterDepartamento = document.getElementById('filterDepartamento');
    
    if (searchInput) searchInput.value = '';
    if (filterStatus) filterStatus.value = 'Ativo';
    if (filterCargo) filterCargo.value = '';
    if (filterDepartamento) filterDepartamento.value = '';
    
    filtrarTabela();
}

function aplicarPaginacao() {
    const tabela = document.getElementById('tabelaColaboradores');
    if (!tabela) return;

    const linhaSemCadastro = tabela.querySelector('tr.empty-state-row');
    const linhasExistentes = tabela.querySelectorAll('tbody tr:not(.empty-state-row):not([data-empty-result="true"])');

    if (linhasExistentes.length === 0) {
        if (linhaSemCadastro) {
            linhaSemCadastro.style.display = '';
        }
        exibirLinhaSemResultados(false);
        atualizarPaginacaoInfo(0, 0, 0, true);
        renderizarPaginacao(0);
        return;
    }

    if (linhaSemCadastro) {
        linhaSemCadastro.style.display = 'none';
    }

    const totalRegistros = linhasFiltradas.length;
    const totalPaginas = Math.ceil(totalRegistros / itensPorPagina);
    const paginaValida = totalPaginas > 0 ? Math.min(paginaAtual, totalPaginas) : 1;
    paginaAtual = Math.max(paginaValida, 1);

    linhasFiltradas.forEach(linha => {
        linha.style.display = 'none';
    });

    if (totalRegistros === 0) {
        exibirLinhaSemResultados(true);
        atualizarPaginacaoInfo(0, 0, 0);
        renderizarPaginacao(0);
        return;
    }

    exibirLinhaSemResultados(false);

    const inicio = (paginaAtual - 1) * itensPorPagina;
    const fim = inicio + itensPorPagina;

    linhasFiltradas.forEach((linha, index) => {
        if (index >= inicio && index < fim) {
            linha.style.display = '';
        }
    });

    atualizarPaginacaoInfo(paginaAtual, totalPaginas, totalRegistros);
    renderizarPaginacao(totalPaginas);
}

function renderizarPaginacao(totalPaginas) {
    const container = document.getElementById('paginacao');
    if (!container) return;

    container.innerHTML = '';

    if (totalPaginas <= 1) {
        return;
    }

    for (let pagina = 1; pagina <= totalPaginas; pagina++) {
        const item = document.createElement('li');
        item.className = `page-item ${pagina === paginaAtual ? 'active' : ''}`;

        const link = document.createElement('a');
        link.className = 'page-link';
        link.href = '#';
        link.textContent = pagina;
        link.addEventListener('click', function(event) {
            event.preventDefault();
            navegarParaPagina(pagina);
        });

        item.appendChild(link);
        container.appendChild(item);
    }
}

function atualizarPaginacaoInfo(pagina, totalPaginas, totalRegistros, contextoVazio) {
    const info = document.getElementById('paginacaoInfo');
    if (!info) return;

    if (totalRegistros === 0) {
        info.textContent = contextoVazio ? '' : 'Nenhum colaborador encontrado com os filtros atuais';
        return;
    }

    const inicio = (pagina - 1) * itensPorPagina + 1;
    const fim = Math.min(pagina * itensPorPagina, totalRegistros);
    info.textContent = `Exibindo ${inicio}-${fim} de ${totalRegistros} colaboradores`;
}

function navegarParaPagina(novaPagina) {
    if (novaPagina === paginaAtual) return;
    paginaAtual = novaPagina;
    aplicarPaginacao();
}

function exibirLinhaSemResultados(deveExibir) {
    const tabela = document.getElementById('tabelaColaboradores');
    if (!tabela) return;

    let linha = tabela.querySelector('tr[data-empty-result="true"]');
    if (!linha) {
        linha = document.createElement('tr');
        linha.setAttribute('data-empty-result', 'true');

        const coluna = document.createElement('td');
        coluna.colSpan = tabela.querySelectorAll('thead th').length;
        coluna.className = 'text-center py-4 text-muted';
        coluna.innerHTML = '<i class="mdi mdi-account-search mdi-24px me-2"></i>Nenhum colaborador encontrado com os filtros aplicados';

        linha.appendChild(coluna);
        tabela.querySelector('tbody').appendChild(linha);
    }

    linha.style.display = deveExibir ? '' : 'none';
}

function coletarBeneficios(prefixoId) {
    const mapa = [
        { sufixo: 'Vale', chave: 'beneficio_vale_alimentacao' },
        { sufixo: 'Ajuda', chave: 'beneficio_ajuda_de_custo' },
        { sufixo: 'Creche', chave: 'beneficio_auxilio_creche' }
    ];

    const resultado = {};
    mapa.forEach(item => {
        const input = document.getElementById(`${prefixoId}${item.sufixo}`);
        if (input && input.value !== '') {
            resultado[item.chave] = input.value;
        }
    });
    return resultado;
}

function preencherBeneficios(prefixoId, beneficios) {
    const mapa = [
        { sufixo: 'Vale', chave: 'vale_alimentacao' },
        { sufixo: 'Ajuda', chave: 'ajuda_de_custo' },
        { sufixo: 'Creche', chave: 'auxilio_creche' }
    ];

    mapa.forEach(item => {
        const input = document.getElementById(`${prefixoId}${item.sufixo}`);
        if (!input) return;
        const valor = beneficios && (beneficios[item.chave] !== undefined && beneficios[item.chave] !== null)
            ? beneficios[item.chave]
            : '';
        input.value = valor;
    });
}

function normalizarBeneficios(beneficios) {
    if (!beneficios) {
        return null;
    }

    if (typeof beneficios === 'string') {
        try {
            const parsed = JSON.parse(beneficios);
            return parsed && typeof parsed === 'object' ? parsed : null;
        } catch (error) {
            console.warn('[RH] Não foi possível converter benefícios para objeto:', error);
            return null;
        }
    }

    if (typeof beneficios === 'object') {
        return beneficios;
    }

    return null;
}

// ===================================================================
// DESLIGAMENTO DE COLABORADOR
// ===================================================================
function inicializarModalDesligamento() {
    const btnConfirmar = document.getElementById('btnConfirmarDesligamento');
    
    if (btnConfirmar) {
        btnConfirmar.addEventListener('click', executarDesligamento);
    }
}

function inicializarModalReativacao() {
    const btnConfirmar = document.getElementById('btnConfirmarReativacao');
    if (btnConfirmar) {
        btnConfirmar.addEventListener('click', executarReativacao);
    }
}

function confirmarDesligamento(colaboradorId, nomeColaborador) {
    console.log(`[RH] Solicitando confirmação de desligamento: ${colaboradorId}`);
    
    colaboradorIdParaDesligar = colaboradorId;
    
    // Atualizar modal com nome do colaborador
    const nomeElement = document.getElementById('nomeColaborador');
    if (nomeElement) {
        nomeElement.textContent = nomeColaborador;
    }
    
    // Limpar campo de motivo
    const motivoInput = document.getElementById('motivoDesligamento');
    if (motivoInput) {
        motivoInput.value = '';
    }
    
    // Abrir modal
    const modal = new bootstrap.Modal(document.getElementById('modalDesligamento'));
    modal.show();
}

async function executarDesligamento() {
    if (!colaboradorIdParaDesligar) {
        mostrarAlerta('Erro ao identificar colaborador', 'danger');
        return;
    }
    
    const motivo = document.getElementById('motivoDesligamento').value;
    
    if (!motivo.trim()) {
        mostrarAlerta('Por favor, informe o motivo do desligamento', 'warning');
        return;
    }
    
    // Desabilitar botão e mostrar loading
    const btnConfirmar = document.getElementById('btnConfirmarDesligamento');
    const textoOriginal = btnConfirmar.innerHTML;
    btnConfirmar.disabled = true;
    btnConfirmar.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processando...';
    
    try {
        console.log(`[RH] Executando desligamento do colaborador: ${colaboradorIdParaDesligar}`);
        
        const response = await fetch(`/rh/colaboradores/api/colaboradores/${colaboradorIdParaDesligar}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ motivo: motivo })
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            console.log('[RH] Colaborador desligado com sucesso');
            mostrarAlerta('Colaborador desligado com sucesso', 'success');
            
            // Fechar modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('modalDesligamento'));
            modal.hide();
            
            // Recarregar página após 1 segundo
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            throw new Error(data.error || 'Erro ao desligar colaborador');
        }
    } catch (error) {
        console.error('[RH] Erro ao desligar colaborador:', error);
        mostrarAlerta(`Erro ao desligar colaborador: ${error.message}`, 'danger');
        
        // Restaurar botão
        btnConfirmar.disabled = false;
        btnConfirmar.innerHTML = textoOriginal;
    }
}

function confirmarReativacao(colaboradorId, nomeColaborador) {
    colaboradorIdParaReativar = colaboradorId;

    const nomeElement = document.getElementById('nomeColaboradorReativar');
    if (nomeElement) {
        nomeElement.textContent = nomeColaborador;
    }

    const dataInput = document.getElementById('dataReativacao');
    definirDataHoje(dataInput);

    const descricao = document.getElementById('descricaoReativacao');
    if (descricao) {
        descricao.value = '';
    }

    const hiddenId = document.getElementById('colaboradorIdReativar');
    if (hiddenId) {
        hiddenId.value = colaboradorId;
    }

    const modal = new bootstrap.Modal(document.getElementById('modalReativacao'));
    modal.show();
}

async function executarReativacao() {
    if (!colaboradorIdParaReativar) {
        mostrarAlerta('Erro ao identificar colaborador', 'danger');
        return;
    }

    const dataReativacao = document.getElementById('dataReativacao');
    const descricao = document.getElementById('descricaoReativacao');
    const dataValor = dataReativacao ? dataReativacao.value : '';

    if (!dataValor) {
        mostrarAlerta('Informe a data de retorno', 'warning');
        return;
    }

    const btnConfirmar = document.getElementById('btnConfirmarReativacao');
    if (!btnConfirmar) {
        mostrarAlerta('Componente de reativação não está disponível.', 'danger');
        return;
    }

    const textoOriginal = btnConfirmar.innerHTML;
    btnConfirmar.disabled = true;
    btnConfirmar.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processando...';

    try {
        const response = await fetch(`/rh/colaboradores/api/colaboradores/${colaboradorIdParaReativar}/reativar`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                data_evento: dataValor,
                descricao: descricao ? descricao.value : ''
            })
        });

        const data = await response.json();
        if (!response.ok || !data.success) {
            throw new Error(data.error || 'Erro ao reativar colaborador');
        }

        mostrarAlerta('Colaborador reativado com sucesso', 'success');
        colaboradorCache.delete(colaboradorIdParaReativar);
        colaboradorIdParaReativar = null;

        const modal = bootstrap.Modal.getInstance(document.getElementById('modalReativacao'));
        modal.hide();
        setTimeout(() => window.location.reload(), 800);
    } catch (error) {
        console.error('[RH] Erro ao reativar colaborador:', error);
        mostrarAlerta(error.message, 'danger');
    } finally {
        btnConfirmar.disabled = false;
        btnConfirmar.innerHTML = textoOriginal;
    }
}

// ===================================================================
// MOVIMENTAÇÕES DE CARREIRA
// ===================================================================
function inicializarPromocao() {
    const form = document.getElementById('formPromocao');
    if (!form) return;

    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        const colaboradorId = document.getElementById('colaboradorIdPromocao').value;
        const submitBtn = form.querySelector('button[type="submit"]');
        const textoOriginal = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Salvando...';

        const payload = {
            data_evento: document.getElementById('dataPromocao').value,
            novo_cargo_id: document.getElementById('novoCargo').value,
            novo_salario: document.getElementById('novoSalarioPromocao').value,
            descricao: document.getElementById('descricaoPromocao').value
        };

        Object.assign(payload, coletarBeneficios('beneficioPromocao'));

        try {
            const response = await fetch(`/rh/colaboradores/api/colaboradores/${colaboradorId}/promover`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            });

            const data = await response.json();
            if (!response.ok || !data.success) {
                throw new Error(data.error || 'Erro ao registrar promoção');
            }

            mostrarAlerta('Promoção registrada com sucesso', 'success');
            colaboradorCache.delete(colaboradorId);
            bootstrap.Modal.getInstance(document.getElementById('modalPromocao')).hide();
            form.reset();
            preencherBeneficios('beneficioPromocao', null);
            setTimeout(() => window.location.reload(), 800);
        } catch (error) {
            console.error('[RH] Erro ao registrar promoção:', error);
            mostrarAlerta(error.message, 'danger');
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = textoOriginal;
        }
    });
}

async function abrirModalPromocao(colaboradorId, nomeColaborador) {
    try {
        const dados = await obterDadosColaborador(colaboradorId);
        document.getElementById('colaboradorIdPromocao').value = colaboradorId;
        document.getElementById('nomeColaboradorPromocao').textContent = nomeColaborador;
        definirDataHoje(document.getElementById('dataPromocao'));
        popularSelect(document.getElementById('novoCargo'), window.RH_CARGOS, 'id', 'nome_cargo', 'Selecione um cargo');
        document.getElementById('novoCargo').value = dados.cargo_id || '';
        document.getElementById('novoSalarioPromocao').value = dados.salario_mensal || '';
        document.getElementById('descricaoPromocao').value = '';
        preencherBeneficios('beneficioPromocao', normalizarBeneficios(dados.beneficios_jsonb || (dados.info_atual && dados.info_atual.beneficios_jsonb)));

        const modal = new bootstrap.Modal(document.getElementById('modalPromocao'));
        modal.show();
    } catch (error) {
        console.error('[RH] Erro ao abrir modal de promoção:', error);
        mostrarAlerta('Não foi possível carregar dados do colaborador.', 'danger');
    }
}

function inicializarReajuste() {
    const form = document.getElementById('formReajuste');
    if (!form) return;

    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        const colaboradorId = document.getElementById('colaboradorIdReajuste').value;
        const submitBtn = form.querySelector('button[type="submit"]');
        const textoOriginal = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Salvando...';

        const payload = {
            data_evento: document.getElementById('dataReajuste').value,
            novo_salario: document.getElementById('novoSalarioReajuste').value,
            descricao: document.getElementById('descricaoReajuste').value
        };

        Object.assign(payload, coletarBeneficios('beneficioReajuste'));

        try {
            const response = await fetch(`/rh/colaboradores/api/colaboradores/${colaboradorId}/reajustar`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            });

            const data = await response.json();
            if (!response.ok || !data.success) {
                throw new Error(data.error || 'Erro ao registrar reajuste');
            }

            mostrarAlerta('Reajuste registrado com sucesso', 'success');
            colaboradorCache.delete(colaboradorId);
            bootstrap.Modal.getInstance(document.getElementById('modalReajuste')).hide();
            form.reset();
            preencherBeneficios('beneficioReajuste', null);
            setTimeout(() => window.location.reload(), 800);
        } catch (error) {
            console.error('[RH] Erro ao registrar reajuste:', error);
            mostrarAlerta(error.message, 'danger');
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = textoOriginal;
        }
    });
}

async function abrirModalReajuste(colaboradorId, nomeColaborador) {
    try {
        const dados = await obterDadosColaborador(colaboradorId);
        document.getElementById('colaboradorIdReajuste').value = colaboradorId;
        document.getElementById('nomeColaboradorReajuste').textContent = nomeColaborador;
        definirDataHoje(document.getElementById('dataReajuste'));
        document.getElementById('novoSalarioReajuste').value = dados.salario_mensal || '';
        document.getElementById('descricaoReajuste').value = '';
        preencherBeneficios('beneficioReajuste', normalizarBeneficios(dados.beneficios_jsonb || (dados.info_atual && dados.info_atual.beneficios_jsonb)));

        const modal = new bootstrap.Modal(document.getElementById('modalReajuste'));
        modal.show();
    } catch (error) {
        console.error('[RH] Erro ao abrir modal de reajuste:', error);
        mostrarAlerta('Não foi possível carregar dados do colaborador.', 'danger');
    }
}

function inicializarDependentesPerfil() {
    const form = document.getElementById('formDependente');
    if (!form) return;

    form.addEventListener('submit', async function(event) {
        event.preventDefault();

        const colaboradorId = obterColaboradorIdContexto();
        if (!colaboradorId) {
            mostrarAlerta('Colaborador não identificado para salvar dependente.', 'danger');
            return;
        }

        const btnSalvar = document.getElementById('btnSalvarDependente');
        const textoOriginal = btnSalvar.innerHTML;
        btnSalvar.disabled = true;
        btnSalvar.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Salvando...';

        const dependenteId = document.getElementById('dependenteId').value;
        const payload = {
            nome_completo: document.getElementById('dependenteNome').value,
            parentesco: document.getElementById('dependenteParentesco').value,
            data_nascimento: document.getElementById('dependenteDataNascimento').value
        };

        const url = dependenteId
            ? `/rh/colaboradores/api/dependentes/${dependenteId}`
            : `/rh/colaboradores/api/colaboradores/${colaboradorId}/dependentes`;
        const method = dependenteId ? 'PUT' : 'POST';

        try {
            const response = await fetch(url, {
                method,
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            });

            const data = await response.json();
            if (!response.ok || data.error) {
                throw new Error(data.error || 'Erro ao salvar dependente');
            }

            mostrarAlerta('Dependente salvo com sucesso.', 'success');
            const modal = bootstrap.Modal.getInstance(document.getElementById('modalDependente'));
            modal.hide();
            setTimeout(() => window.location.reload(), 700);
        } catch (error) {
            console.error('[RH] Falha ao salvar dependente:', error);
            mostrarAlerta(error.message, 'danger');
        } finally {
            btnSalvar.disabled = false;
            btnSalvar.innerHTML = textoOriginal;
        }
    });
}

function abrirModalDependente(colaboradorId, nomeColaborador) {
    if (colaboradorId) {
        atualizarContextoColaborador({
            colaboradorId,
            nome: nomeColaborador
        });
    }

    const form = document.getElementById('formDependente');
    if (!form) return;

    form.reset();
    document.getElementById('dependenteId').value = '';
    document.getElementById('tituloModalDependente').textContent = 'Adicionar Dependente';

    const modal = new bootstrap.Modal(document.getElementById('modalDependente'));
    modal.show();
}

function editarDependente(button) {
    const raw = button.getAttribute('data-dependente');
    if (!raw) return;

    let dependente;
    try {
        dependente = JSON.parse(raw);
    } catch (error) {
        console.error('[RH] Dados de dependente inválidos:', error);
        mostrarAlerta('Não foi possível carregar os dados do dependente.', 'danger');
        return;
    }

    document.getElementById('dependenteId').value = dependente.id || '';
    document.getElementById('dependenteNome').value = dependente.nome_completo || '';
    document.getElementById('dependenteParentesco').value = dependente.parentesco || '';
    document.getElementById('dependenteDataNascimento').value = dependente.data_nascimento_iso || dependente.data_nascimento || '';
    document.getElementById('tituloModalDependente').textContent = 'Editar Dependente';

    const modal = new bootstrap.Modal(document.getElementById('modalDependente'));
    modal.show();
}

async function confirmarRemocaoDependente(dependenteId, nomeDependente) {
    if (!dependenteId) return;

    const confirma = window.confirm(`Confirma remover o dependente "${nomeDependente}"?`);
    if (!confirma) return;

    try {
        const response = await fetch(`/rh/colaboradores/api/dependentes/${dependenteId}`, {
            method: 'DELETE',
            headers: {'Content-Type': 'application/json'}
        });

        const data = await response.json();
        if (!response.ok || data.error) {
            throw new Error(data.error || 'Erro ao remover dependente');
        }

        mostrarAlerta('Dependente removido com sucesso.', 'success');
        setTimeout(() => window.location.reload(), 700);
    } catch (error) {
        console.error('[RH] Falha ao remover dependente:', error);
        mostrarAlerta(error.message, 'danger');
    }
}

function inicializarContatosPerfil() {
    const form = document.getElementById('formContato');
    if (!form) return;

    form.addEventListener('submit', async function(event) {
        event.preventDefault();

        const colaboradorId = obterColaboradorIdContexto();
        if (!colaboradorId) {
            mostrarAlerta('Colaborador não identificado para salvar contato.', 'danger');
            return;
        }

        const btnSalvar = document.getElementById('btnSalvarContato');
        const textoOriginal = btnSalvar.innerHTML;
        btnSalvar.disabled = true;
        btnSalvar.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Salvando...';

        const contatoId = document.getElementById('contatoId').value;
        const payload = {
            nome_contato: document.getElementById('contatoNome').value,
            telefone_contato: document.getElementById('contatoTelefone').value,
            parentesco: document.getElementById('contatoParentesco').value
        };

        const url = contatoId
            ? `/rh/colaboradores/api/contatos-emergencia/${contatoId}`
            : `/rh/colaboradores/api/colaboradores/${colaboradorId}/contatos-emergencia`;
        const method = contatoId ? 'PUT' : 'POST';

        try {
            const response = await fetch(url, {
                method,
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            });

            const data = await response.json();
            if (!response.ok || data.error) {
                throw new Error(data.error || 'Erro ao salvar contato de emergência');
            }

            mostrarAlerta('Contato de emergência salvo com sucesso.', 'success');
            const modal = bootstrap.Modal.getInstance(document.getElementById('modalContato'));
            modal.hide();
            setTimeout(() => window.location.reload(), 700);
        } catch (error) {
            console.error('[RH] Falha ao salvar contato de emergência:', error);
            mostrarAlerta(error.message, 'danger');
        } finally {
            btnSalvar.disabled = false;
            btnSalvar.innerHTML = textoOriginal;
        }
    });
}

function abrirModalContato(colaboradorId, nomeColaborador) {
    if (colaboradorId) {
        atualizarContextoColaborador({
            colaboradorId,
            nome: nomeColaborador
        });
    }

    const form = document.getElementById('formContato');
    if (!form) return;

    form.reset();
    document.getElementById('contatoId').value = '';
    document.getElementById('tituloModalContato').textContent = 'Adicionar Contato de Emergência';

    const modal = new bootstrap.Modal(document.getElementById('modalContato'));
    modal.show();
}

function editarContato(button) {
    const raw = button.getAttribute('data-contato');
    if (!raw) return;

    let contato;
    try {
        contato = JSON.parse(raw);
    } catch (error) {
        console.error('[RH] Dados de contato inválidos:', error);
        mostrarAlerta('Não foi possível carregar os dados do contato.', 'danger');
        return;
    }

    document.getElementById('contatoId').value = contato.id || '';
    document.getElementById('contatoNome').value = contato.nome_contato || '';
    document.getElementById('contatoTelefone').value = contato.telefone_contato || '';
    document.getElementById('contatoParentesco').value = contato.parentesco || '';
    document.getElementById('tituloModalContato').textContent = 'Editar Contato de Emergência';

    const modal = new bootstrap.Modal(document.getElementById('modalContato'));
    modal.show();
}

async function confirmarRemocaoContato(contatoId, nomeContato) {
    if (!contatoId) return;

    const confirma = window.confirm(`Confirma remover o contato "${nomeContato}"?`);
    if (!confirma) return;

    try {
        const response = await fetch(`/rh/colaboradores/api/contatos-emergencia/${contatoId}`, {
            method: 'DELETE',
            headers: {'Content-Type': 'application/json'}
        });

        const data = await response.json();
        if (!response.ok || data.error) {
            throw new Error(data.error || 'Erro ao remover contato de emergência');
        }

        mostrarAlerta('Contato de emergência removido com sucesso.', 'success');
        setTimeout(() => window.location.reload(), 700);
    } catch (error) {
        console.error('[RH] Falha ao remover contato de emergência:', error);
        mostrarAlerta(error.message, 'danger');
    }
}

function inicializarBeneficiosPerfil() {
    const modalElement = document.getElementById('modalAlterarBeneficios');
    const form = document.getElementById('formAlterarBeneficios');
    const lista = document.getElementById('beneficiosLista');
    const aviso = document.getElementById('beneficiosAviso');
    const btnAdicionar = document.getElementById('btnAdicionarBeneficioLinha');
    const dataInput = document.getElementById('beneficiosData');
    const descricaoInput = document.getElementById('beneficiosDescricao');
    const colaboradorIdInput = document.getElementById('beneficiosColaboradorId');
    const nomeSpan = document.getElementById('beneficiosColaboradorNome');
    const btnAlterar = document.getElementById('btnAlterarBeneficios');

    if (!modalElement || !form || !lista || !btnAdicionar || !colaboradorIdInput || !nomeSpan) {
        return;
    }

    const catalogo = Array.isArray(window.RH_BENEFICIOS_CATALOGO) ? window.RH_BENEFICIOS_CATALOGO.slice() : [];
    if (!catalogo.some(item => item.slug === 'outros')) {
        catalogo.push({ slug: 'outros', label: 'Outro Benefício' });
    }
    const catalogSlugSet = new Set(catalogo.map(item => item.slug));

    if (dataInput) {
        dataInput.addEventListener('change', () => {
            dataInput.classList.remove('is-invalid');
            limparAviso();
        });
    }

    if (descricaoInput) {
        descricaoInput.addEventListener('input', () => {
            descricaoInput.classList.remove('is-invalid');
            limparAviso();
        });
    }

    function limparAviso() {
        if (!aviso) return;
        aviso.style.display = 'none';
        aviso.textContent = '';
    }

    function exibirAviso(mensagem, tipo = 'warning') {
        if (!aviso) return;
        aviso.className = `alert alert-${tipo} mt-3 mb-0`;
        aviso.textContent = mensagem;
        aviso.style.display = 'block';
    }

    function formatarSlugParaLabel(slug) {
        if (!slug) return '';
        return slug
            .toString()
            .split(/[-_]/)
            .filter(Boolean)
            .map(parte => parte.charAt(0).toUpperCase() + parte.slice(1))
            .join(' ');
    }

    function obterDatasetBase() {
        const container = document.getElementById('colaboradorPerfil');
        if (!container) {
            return {};
        }

        return {
            colaboradorId: container.dataset.colaboradorId || '',
            nome: container.dataset.nome || '',
            salario: container.dataset.salario || '',
            beneficios: container.dataset.beneficios || ''
        };
    }

    const datasetBase = obterDatasetBase();

    function montarSelectOptions(select, selectedValue) {
        if (!select) return;

        select.innerHTML = '';
        const placeholder = document.createElement('option');
        placeholder.value = '';
        placeholder.textContent = 'Selecione...';
        select.appendChild(placeholder);

        catalogo.forEach(item => {
            const option = document.createElement('option');
            option.value = item.slug;
            option.textContent = item.label;
            if (selectedValue && item.slug === selectedValue) {
                option.selected = true;
            }
            select.appendChild(option);
        });
    }

    function criarLinhaBeneficio(config = {}) {
        const linha = document.createElement('div');
        linha.className = 'beneficio-item border rounded-3 p-3 mb-2 bg-light';
        linha.innerHTML = `
            <div class="row g-2 align-items-end">
                <div class="col-md-5">
                    <label class="form-label mb-1">Tipo de Benefício</label>
                    <select class="form-select beneficio-select"></select>
                </div>
                <div class="col-md-4">
                    <label class="form-label mb-1">Valor Mensal</label>
                    <div class="input-group">
                        <span class="input-group-text">R$</span>
                        <input type="number" class="form-control beneficio-valor" min="0" step="0.01" placeholder="0,00">
                    </div>
                </div>
                <div class="col-md-3 text-md-end">
                    <button type="button" class="btn btn-outline-danger btn-sm w-100 beneficio-remover">
                        <i class="mdi mdi-trash-can"></i> Remover
                    </button>
                </div>
                <div class="col-12 mt-2 beneficio-custom-wrapper d-none">
                    <label class="form-label mb-1">Descreva o benefício</label>
                    <input type="text" class="form-control beneficio-custom-label" placeholder="Ex: Bônus de produtividade">
                </div>
            </div>
        `;

        const select = linha.querySelector('.beneficio-select');
        const valorInput = linha.querySelector('.beneficio-valor');
        const removerBtn = linha.querySelector('.beneficio-remover');
        const customWrapper = linha.querySelector('.beneficio-custom-wrapper');
        const customInput = linha.querySelector('.beneficio-custom-label');

        montarSelectOptions(select, config.slug);

        if (valorInput && config.valor !== undefined && config.valor !== null && config.valor !== '') {
            const valorNumerico = parseFloat(config.valor);
            if (!Number.isNaN(valorNumerico)) {
                valorInput.value = valorNumerico;
            }
        }

        if (config.customLabel && customInput) {
            customInput.value = config.customLabel;
        }

        function atualizarEstadoCustom() {
            const selecionado = select.value;
            const deveMostrarCustom = selecionado === 'outros' || (selecionado && !catalogSlugSet.has(selecionado));
            if (deveMostrarCustom) {
                customWrapper.classList.remove('d-none');
                customInput.required = true;
            } else {
                customWrapper.classList.add('d-none');
                customInput.required = false;
                customInput.value = deveMostrarCustom ? customInput.value : '';
            }
        }

        atualizarEstadoCustom();

        select.addEventListener('change', () => {
            select.classList.remove('is-invalid');
            limparAviso();
            atualizarEstadoCustom();
        });

        valorInput.addEventListener('input', () => {
            valorInput.classList.remove('is-invalid');
            limparAviso();
        });

        if (customInput) {
            customInput.addEventListener('input', () => {
                customInput.classList.remove('is-invalid');
                limparAviso();
            });
        }

        removerBtn.addEventListener('click', () => {
            linha.remove();
            limparAviso();
        });

        return linha;
    }

    function adicionarLinha(config = {}) {
        const linha = criarLinhaBeneficio(config);
        lista.appendChild(linha);
        const select = linha.querySelector('.beneficio-select');
        if (select) {
            select.focus();
        }
    }

    function carregarBeneficios(fonte) {
        lista.innerHTML = '';
        const normalizados = normalizarBeneficios(fonte) || {};
        const entradas = Object.entries(normalizados);

        if (entradas.length === 0) {
            adicionarLinha();
            return;
        }

        entradas.forEach(([slug, valor]) => {
            const ehCatalogo = catalogSlugSet.has(slug);
            const configLinha = {
                slug: ehCatalogo ? slug : 'outros',
                valor: valor,
                customLabel: ehCatalogo ? '' : formatarSlugParaLabel(slug)
            };
            adicionarLinha(configLinha);
        });
    }

    function coletarBeneficiosDoFormulario() {
        const linhas = lista.querySelectorAll('.beneficio-item');
        const beneficios = [];
        const erros = new Set();
        const chaves = new Set();

        linhas.forEach(linha => {
            const select = linha.querySelector('.beneficio-select');
            const valorInput = linha.querySelector('.beneficio-valor');
            const customInput = linha.querySelector('.beneficio-custom-label');
            const customWrapper = linha.querySelector('.beneficio-custom-wrapper');

            [select, valorInput, customInput].forEach(elemento => elemento && elemento.classList.remove('is-invalid'));

            const slugSelecionado = select ? select.value : '';
            const valorBruto = valorInput ? valorInput.value : '';
            const valorFloat = valorBruto !== '' ? parseFloat(valorBruto) : NaN;
            const customTexto = customInput ? customInput.value.trim() : '';

            if (!slugSelecionado) {
                erros.add('Selecione o tipo de benefício para todas as linhas.');
                if (select) select.classList.add('is-invalid');
                return;
            }

            if (!Number.isFinite(valorFloat) || valorFloat <= 0) {
                erros.add('Informe valores positivos para todos os benefícios.');
                if (valorInput) valorInput.classList.add('is-invalid');
                return;
            }

            const item = { valor: Number(valorFloat.toFixed(2)) };
            let chaveUnica = slugSelecionado;

            if (slugSelecionado === 'outros' || !catalogSlugSet.has(slugSelecionado)) {
                if (!customTexto) {
                    erros.add('Descreva os benefícios personalizados.');
                    if (customInput) customInput.classList.add('is-invalid');
                    if (customWrapper) customWrapper.classList.remove('d-none');
                    return;
                }

                item.nome = customTexto;
                chaveUnica = `custom:${customTexto.toLowerCase()}`;
            } else {
                item.slug = slugSelecionado;
            }

            if (chaves.has(chaveUnica)) {
                erros.add('Evite duplicar o mesmo benefício.');
                if (select) select.classList.add('is-invalid');
                return;
            }

            chaves.add(chaveUnica);
            beneficios.push(item);
        });

        return { beneficios, erros: Array.from(erros) };
    }

    btnAdicionar.addEventListener('click', event => {
        event.preventDefault();
        limparAviso();
        adicionarLinha();
    });

    async function prepararEMostrarModalBeneficios(config = {}) {
        limparAviso();

        const colaboradorId = config.colaboradorId || datasetBase.colaboradorId;
        if (!colaboradorId) {
            exibirAviso('Colaborador não identificado para alteração de benefícios.');
            return;
        }

        const contexto = atualizarContextoColaborador({
            colaboradorId,
            nome: config.nome,
            salario: config.salario,
            beneficios: config.beneficios
        });

        colaboradorIdInput.value = colaboradorId;
        nomeSpan.textContent = config.nome || contexto.nome || datasetBase.nome || 'Colaborador(a)';

        if (dataInput) {
            definirDataHoje(dataInput);
        }

        if (descricaoInput) {
            descricaoInput.value = '';
        }

        const beneficiosFonte = config.beneficios !== undefined ? config.beneficios : contexto.beneficios;
        carregarBeneficios(beneficiosFonte);

        const modal = bootstrap.Modal.getOrCreateInstance(modalElement);
        modal.show();
    }

    if (btnAlterar) {
        btnAlterar.addEventListener('click', () => {
            prepararEMostrarModalBeneficios({
                colaboradorId: btnAlterar.dataset.colaboradorId || datasetBase.colaboradorId,
                nome: btnAlterar.dataset.nome || datasetBase.nome,
                beneficios: btnAlterar.dataset.beneficios || datasetBase.beneficios,
                salario: btnAlterar.dataset.salario || datasetBase.salario
            });
        });
    }

    form.addEventListener('submit', async event => {
        event.preventDefault();
        limparAviso();

        const colaboradorId = colaboradorIdInput.value;
        if (!colaboradorId) {
            exibirAviso('Colaborador não identificado para alteração de benefícios.');
            return;
        }

        const dataEvento = dataInput ? dataInput.value : '';
        const descricao = (descricaoInput ? descricaoInput.value : '').trim();

        if (!dataEvento) {
            exibirAviso('Informe a data da alteração.');
            if (dataInput) dataInput.classList.add('is-invalid');
            return;
        }

        if (!descricao) {
            exibirAviso('Descreva o motivo da alteração.');
            if (descricaoInput) descricaoInput.classList.add('is-invalid');
            return;
        }

        const { beneficios, erros } = coletarBeneficiosDoFormulario();

        if (erros.length > 0) {
            exibirAviso(erros.join(' '));
            return;
        }

        if (beneficios.length === 0) {
            exibirAviso('Adicione ao menos um benefício com valor positivo.');
            return;
        }

        const payload = {
            data_evento: dataEvento,
            descricao,
            beneficios
        };

        const btnSalvar = document.getElementById('btnSalvarBeneficios');
        const textoOriginal = btnSalvar.innerHTML;
        btnSalvar.disabled = true;
        btnSalvar.innerHTML = '<i class="mdi mdi-loading mdi-spin"></i> Salvando...';

        try {
            const response = await fetch(`/rh/colaboradores/api/colaboradores/${colaboradorId}/alterar-beneficios`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            });

            const data = await response.json();
            if (!response.ok || !data.success) {
                throw new Error(data.error || 'Não foi possível salvar as alterações de benefícios.');
            }

            mostrarAlerta('Alteração de benefícios registrada com sucesso.', 'success');
            bootstrap.Modal.getInstance(modalElement).hide();
            setTimeout(() => window.location.reload(), 800);
        } catch (error) {
            console.error('[RH] Falha ao alterar benefícios:', error);
            exibirAviso(error.message || 'Ocorreu um erro ao comunicar com o servidor.');
        } finally {
            btnSalvar.disabled = false;
            btnSalvar.innerHTML = textoOriginal;
        }
    });
    window.abrirModalBeneficios = async function(colaboradorId, nomeColaborador) {
        if (!colaboradorId) {
            mostrarAlerta('Colaborador não identificado para alteração de benefícios.', 'danger');
            return;
        }

        try {
            const dados = await obterDadosColaborador(colaboradorId);
            const beneficiosOrigem = (dados.info_atual && dados.info_atual.beneficios_jsonb) || dados.beneficios_jsonb || {};
            const salarioAtual = (dados.info_atual && dados.info_atual.salario_mensal !== undefined)
                ? dados.info_atual.salario_mensal
                : dados.salario_mensal;

            await prepararEMostrarModalBeneficios({
                colaboradorId,
                nome: nomeColaborador,
                beneficios: beneficiosOrigem,
                salario: salarioAtual
            });
        } catch (error) {
            console.error('[RH] Falha ao carregar benefícios do colaborador:', error);
            mostrarAlerta('Não foi possível carregar os benefícios atuais.', 'danger');
        }
    };
}

function inicializarTransferencia() {
    const form = document.getElementById('formTransferencia');
    if (!form) return;

    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        const colaboradorId = document.getElementById('colaboradorIdTransferencia').value;
        const submitBtn = form.querySelector('button[type="submit"]');
        const textoOriginal = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Salvando...';

        const payload = {
            data_evento: document.getElementById('dataTransferencia').value,
            novo_departamento_id: document.getElementById('novoDepartamento').value,
            novo_gestor_id: document.getElementById('novoGestor').value,
            descricao: document.getElementById('descricaoTransferencia').value
        };

        try {
            const response = await fetch(`/rh/colaboradores/api/colaboradores/${colaboradorId}/transferir`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            });

            const data = await response.json();
            if (!response.ok || !data.success) {
                throw new Error(data.error || 'Erro ao registrar transferência');
            }

            mostrarAlerta('Transferência registrada com sucesso', 'success');
            colaboradorCache.delete(colaboradorId);
            bootstrap.Modal.getInstance(document.getElementById('modalTransferencia')).hide();
            form.reset();
            setTimeout(() => window.location.reload(), 800);
        } catch (error) {
            console.error('[RH] Erro ao registrar transferência:', error);
            mostrarAlerta(error.message, 'danger');
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = textoOriginal;
        }
    });
}

async function abrirModalTransferencia(colaboradorId, nomeColaborador) {
    try {
        const dados = await obterDadosColaborador(colaboradorId);
        document.getElementById('colaboradorIdTransferencia').value = colaboradorId;
        document.getElementById('nomeColaboradorTransferencia').textContent = nomeColaborador;
        definirDataHoje(document.getElementById('dataTransferencia'));
        popularSelect(document.getElementById('novoDepartamento'), window.RH_DEPARTAMENTOS, 'id', 'nome_departamento', 'Selecione um departamento');
        document.getElementById('novoDepartamento').value = dados.departamento_id || '';
        popularSelectGestores(document.getElementById('novoGestor'), window.RH_GESTORES);
        document.getElementById('novoGestor').value = dados.gestor_id || '';
        document.getElementById('descricaoTransferencia').value = '';

        const modal = new bootstrap.Modal(document.getElementById('modalTransferencia'));
        modal.show();
    } catch (error) {
        console.error('[RH] Erro ao abrir modal de transferência:', error);
        mostrarAlerta('Não foi possível carregar dados do colaborador.', 'danger');
    }
}

function inicializarFerias() {
    const form = document.getElementById('formFerias');
    if (!form) return;

    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        const colaboradorId = document.getElementById('colaboradorIdFerias').value;
        const submitBtn = form.querySelector('button[type="submit"]');
        const textoOriginal = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Salvando...';

        const payload = {
            tipo_evento: 'Férias',
            data_inicio: document.getElementById('dataInicioFerias').value,
            data_fim: document.getElementById('dataFimFerias').value,
            descricao: document.getElementById('descricaoFerias').value
        };

        try {
            const response = await fetch(`/rh/colaboradores/api/colaboradores/${colaboradorId}/registrar-evento`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            });

            const data = await response.json();
            if (!response.ok || !data.success) {
                throw new Error(data.error || 'Erro ao registrar férias');
            }

            mostrarAlerta('Férias registradas com sucesso', 'success');
            colaboradorCache.delete(colaboradorId);
            bootstrap.Modal.getInstance(document.getElementById('modalFerias')).hide();
            form.reset();
            setTimeout(() => window.location.reload(), 800);
        } catch (error) {
            console.error('[RH] Erro ao registrar férias:', error);
            mostrarAlerta(error.message, 'danger');
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = textoOriginal;
        }
    });
}

function abrirModalFerias(colaboradorId, nomeColaborador) {
    document.getElementById('colaboradorIdFerias').value = colaboradorId;
    document.getElementById('nomeColaboradorFerias').textContent = nomeColaborador;
    definirDataHoje(document.getElementById('dataInicioFerias'));
    definirDataHoje(document.getElementById('dataFimFerias'));
    document.getElementById('descricaoFerias').value = '';

    const modal = new bootstrap.Modal(document.getElementById('modalFerias'));
    modal.show();
}

// ===================================================================
// UTILITÁRIOS
// ===================================================================
async function obterDadosColaborador(colaboradorId) {
    if (colaboradorCache.has(colaboradorId)) {
        return colaboradorCache.get(colaboradorId);
    }

    const response = await fetch(`/rh/colaboradores/api/colaboradores/${colaboradorId}`, {
        credentials: 'same-origin'
    });

    const data = await response.json();
    if (!response.ok || !data.success) {
        throw new Error(data.error || 'Erro ao buscar colaborador');
    }

    const combinado = Object.assign({}, data.data || {});
    if (data.info_atual) {
        combinado.info_atual = data.info_atual;
        if (data.info_atual.salario_mensal !== undefined && data.info_atual.salario_mensal !== null) {
            combinado.salario_mensal = data.info_atual.salario_mensal;
        }
        if (data.info_atual.cargo_id) {
            combinado.cargo_id = data.info_atual.cargo_id;
        }
        if (data.info_atual.departamento_id) {
            combinado.departamento_id = data.info_atual.departamento_id;
        }
        if (data.info_atual.gestor_id) {
            combinado.gestor_id = data.info_atual.gestor_id;
        }
        if (data.info_atual.beneficios_jsonb) {
            combinado.beneficios_jsonb = data.info_atual.beneficios_jsonb;
        }
    }

    colaboradorCache.set(colaboradorId, combinado);
    return combinado;
}

function obterColaboradorIdContexto() {
    const container = document.getElementById('colaboradorPerfil');
    return container ? container.dataset.colaboradorId : null;
}

function atualizarContextoColaborador(config = {}) {
    let container = document.getElementById('colaboradorPerfil');
    if (!container) {
        container = document.createElement('div');
        container.id = 'colaboradorPerfil';
        container.className = 'd-none';
        document.body.appendChild(container);
    }

    if (config.colaboradorId !== undefined) {
        container.dataset.colaboradorId = config.colaboradorId || '';
    }

    if (config.nome !== undefined) {
        container.dataset.nome = config.nome || '';
    }

    if (config.salario !== undefined) {
        const valorSalario = config.salario;
        container.dataset.salario = valorSalario !== null && valorSalario !== undefined ? valorSalario : '';
    }

    if (config.beneficios !== undefined) {
        try {
            container.dataset.beneficios = typeof config.beneficios === 'string'
                ? config.beneficios
                : JSON.stringify(config.beneficios || {});
        } catch (error) {
            console.warn('[RH] Falha ao serializar benefícios do contexto:', error);
            container.dataset.beneficios = '{}';
        }
    }

    return container.dataset;
}

function definirDataHoje(input) {
    if (!input) return;
    const hoje = new Date().toISOString().split('T')[0];
    input.value = hoje;
}

function popularSelect(select, dados, valueKey, labelKey, placeholder) {
    if (!select) return;
    select.innerHTML = '';
    if (placeholder) {
        const optionPlaceholder = document.createElement('option');
        optionPlaceholder.value = '';
        optionPlaceholder.textContent = placeholder;
        select.appendChild(optionPlaceholder);
    }

    (dados || []).forEach(item => {
        const option = document.createElement('option');
        option.value = item[valueKey];
        option.textContent = item[labelKey];
        select.appendChild(option);
    });
}

function popularSelectGestores(select, gestores) {
    if (!select) return;
    const manterOption = select.querySelector('option[value=""]');
    select.innerHTML = '';
    if (manterOption) {
        select.appendChild(manterOption);
    } else {
        const opt = document.createElement('option');
        opt.value = '';
        opt.textContent = 'Manter gestor atual';
        select.appendChild(opt);
    }

    (gestores || []).forEach(gestor => {
        const option = document.createElement('option');
        option.value = gestor.id;
        const matricula = gestor.matricula ? ` (${gestor.matricula})` : '';
        option.textContent = `${gestor.nome_completo}${matricula}`;
        select.appendChild(option);
    });
}

function mostrarAlerta(mensagem, tipo = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${tipo} alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-3`;
    alertDiv.style.zIndex = '9999';
    alertDiv.style.minWidth = '300px';
    alertDiv.innerHTML = `
        ${mensagem}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    document.body.appendChild(alertDiv);

    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

function formatarCPF(cpf) {
    return cpf.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4');
}

function formatarTelefone(telefone) {
    if (!telefone) {
        return '-';
    }

    const digits = telefone.replace(/\D/g, '');

    if (digits.length === 11) {
        return digits.replace(/(\d{2})(\d{5})(\d{4})/, '($1) $2-$3');
    }

    if (digits.length === 10) {
        return digits.replace(/(\d{2})(\d{4})(\d{4})/, '($1) $2-$3');
    }

    if (digits.length > 0 && digits.length <= 9) {
        return digits.replace(/(\d{2})(\d{0,4})(\d{0,4})/, function(_, ddd, parte1, parte2) {
            let resultado = '(' + ddd;
            if (parte1) {
                resultado += ') ' + parte1;
            }
            if (parte2) {
                resultado += '-' + parte2;
            }
            return resultado;
        });
    }

    return telefone;
}

function formatarData(data) {
    if (!data) return '-';
    
    // Se já está em formato brasileiro
    if (data.includes('/')) return data;
    
    // Converter de YYYY-MM-DD para DD/MM/YYYY
    const partes = data.split('-');
    if (partes.length === 3) {
        return `${partes[2]}/${partes[1]}/${partes[0]}`;
    }
    
    return data;
}

// Exportar funções para uso global
window.confirmarDesligamento = confirmarDesligamento;
window.mostrarAlerta = mostrarAlerta;
window.formatarCPF = formatarCPF;
window.formatarTelefone = formatarTelefone;

// ===================================================================
// ORDENAÇÃO DE TABELA
// ===================================================================

/**
 * Inicializa a funcionalidade de ordenação na tabela
 */
function inicializarOrdenacao() {
    const tabela = document.getElementById('tabelaColaboradores');
    if (!tabela) return;

    const headers = tabela.querySelectorAll('thead th.sortable');
    
    headers.forEach(header => {
        header.addEventListener('click', function() {
            const column = this.getAttribute('data-column');
            const type = this.getAttribute('data-type');
            ordenarTabela(column, type);
        });
    });
    
    console.log('[ORDENAÇÃO] Sistema de ordenação inicializado para', headers.length, 'colunas');
}

/**
 * Ordena a tabela por uma coluna específica
 * @param {string} column - Nome da coluna (data attribute)
 * @param {string} type - Tipo de dado (text, number, date)
 */
function ordenarTabela(column, type) {
    const tabela = document.getElementById('tabelaColaboradores');
    const tbody = tabela.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr:not(.empty-state-row)'));
    
    // Determinar direção de ordenação
    if (currentSortColumn === column) {
        currentSortDirection = currentSortDirection === 'asc' ? 'desc' : 'asc';
    } else {
        currentSortColumn = column;
        currentSortDirection = 'asc';
    }
    
    // Adicionar classe de loading
    tabela.classList.add('sorting');
    
    // Ordenar as linhas
    rows.sort((a, b) => {
        let valueA, valueB;
        
        // Extrair valores baseado no tipo de coluna
        switch(column) {
            case 'matricula':
                valueA = a.getAttribute('data-matricula') || '';
                valueB = b.getAttribute('data-matricula') || '';
                break;
            case 'nome':
                valueA = a.getAttribute('data-nome') || '';
                valueB = b.getAttribute('data-nome') || '';
                break;
            case 'cargo':
                valueA = a.getAttribute('data-cargo') || '';
                valueB = b.getAttribute('data-cargo') || '';
                break;
            case 'departamento':
                valueA = a.getAttribute('data-departamento') || '';
                valueB = b.getAttribute('data-departamento') || '';
                break;
            case 'admissao':
                valueA = a.getAttribute('data-admissao') || '';
                valueB = b.getAttribute('data-admissao') || '';
                break;
            case 'status':
                valueA = a.getAttribute('data-status') || '';
                valueB = b.getAttribute('data-status') || '';
                break;
            default:
                valueA = '';
                valueB = '';
        }
        
        // Comparar valores baseado no tipo
        let comparison = 0;
        
        if (type === 'number') {
            const numA = parseFloat(valueA) || 0;
            const numB = parseFloat(valueB) || 0;
            comparison = numA - numB;
        } else if (type === 'date') {
            const dateA = valueA ? new Date(valueA) : new Date(0);
            const dateB = valueB ? new Date(valueB) : new Date(0);
            comparison = dateA - dateB;
        } else {
            // text comparison
            comparison = valueA.toLowerCase().localeCompare(valueB.toLowerCase());
        }
        
        return currentSortDirection === 'asc' ? comparison : -comparison;
    });
    
    // Atualizar indicadores visuais no header
    atualizarIndicadoresOrdenacao(column);
    
    // Reorganizar as linhas na tabela
    setTimeout(() => {
        rows.forEach(row => tbody.appendChild(row));
        tabela.classList.remove('sorting');
        
        // Reaplicar paginação após ordenação
        aplicarPaginacao();
        
        console.log(`[ORDENAÇÃO] Tabela ordenada por ${column} (${currentSortDirection})`);
    }, 150);
}

/**
 * Atualiza os indicadores visuais de ordenação nos headers
 * @param {string} activeColumn - Coluna atualmente ordenada
 */
function atualizarIndicadoresOrdenacao(activeColumn) {
    const tabela = document.getElementById('tabelaColaboradores');
    const headers = tabela.querySelectorAll('thead th.sortable');
    
    headers.forEach(header => {
        const column = header.getAttribute('data-column');
        
        // Remover classes de ordenação antigas
        header.classList.remove('sort-asc', 'sort-desc');
        
        // Adicionar classe na coluna ativa
        if (column === activeColumn) {
            header.classList.add(currentSortDirection === 'asc' ? 'sort-asc' : 'sort-desc');
        }
    });
}
window.formatarData = formatarData;
window.abrirModalPromocao = abrirModalPromocao;
window.abrirModalReajuste = abrirModalReajuste;
window.abrirModalTransferencia = abrirModalTransferencia;
window.abrirModalFerias = abrirModalFerias;
window.confirmarReativacao = confirmarReativacao;
window.abrirModalDependente = abrirModalDependente;
window.editarDependente = editarDependente;
window.confirmarRemocaoDependente = confirmarRemocaoDependente;
window.abrirModalContato = abrirModalContato;
window.editarContato = editarContato;
window.confirmarRemocaoContato = confirmarRemocaoContato;
