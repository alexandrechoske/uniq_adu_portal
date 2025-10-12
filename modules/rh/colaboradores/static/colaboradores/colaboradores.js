// ===================================================================
// JAVASCRIPT DO MÓDULO RH - COLABORADORES
// ===================================================================

// Variáveis globais para armazenar IDs de ações críticas
let colaboradorIdParaDesligar = null;
let colaboradorIdParaReativar = null;
const colaboradorCache = new Map();

// ===================================================================
// INICIALIZAÇÃO
// ===================================================================
document.addEventListener('DOMContentLoaded', function() {
    console.log('[RH] Módulo de Colaboradores inicializado');
    
    // Inicializar filtros e busca
    inicializarFiltros();
    
    // Inicializar modal de desligamento
    inicializarModalDesligamento();
    inicializarModalReativacao();
    
    inicializarPromocao();
    inicializarReajuste();
    inicializarTransferencia();
    inicializarFerias();

    // Inicializar tooltips do Bootstrap
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});

// ===================================================================
// FILTROS E BUSCA
// ===================================================================
function inicializarFiltros() {
    const searchInput = document.getElementById('searchInput');
    const filterStatus = document.getElementById('filterStatus');
    const btnLimpar = document.getElementById('btnLimparFiltros');
    
    if (searchInput) {
        searchInput.addEventListener('input', filtrarTabela);
    }
    
    if (filterStatus) {
        filterStatus.addEventListener('change', filtrarTabela);
    }
    
    if (btnLimpar) {
        btnLimpar.addEventListener('click', limparFiltros);
    }
}

function filtrarTabela() {
    const searchInput = document.getElementById('searchInput');
    const filterStatus = document.getElementById('filterStatus');
    const tabela = document.getElementById('tabelaColaboradores');
    
    if (!tabela) return;
    
    const searchTerm = searchInput ? searchInput.value.toLowerCase() : '';
    const statusFiltro = filterStatus ? filterStatus.value : '';
    
    const linhas = tabela.getElementsByTagName('tbody')[0].getElementsByTagName('tr');
    let visibleCount = 0;
    
    Array.from(linhas).forEach(linha => {
        // Ignorar linha de "nenhum colaborador"
        if (linha.cells.length === 1) return;
        
        // Buscar especificamente nas colunas de dados (não incluir botões)
        const matricula = linha.cells[0] ? linha.cells[0].textContent.toLowerCase() : '';
        const nome = linha.cells[1] ? linha.cells[1].textContent.toLowerCase() : '';
        const cpf = linha.cells[2] ? linha.cells[2].textContent.toLowerCase() : '';
        const cargo = linha.cells[3] ? linha.cells[3].textContent.toLowerCase() : '';
        const departamento = linha.cells[4] ? linha.cells[4].textContent.toLowerCase() : '';
        
        const status = linha.getAttribute('data-status');
        
        // Verificar se o termo de busca existe em qualquer campo
        const matchSearch = !searchTerm || 
                          matricula.includes(searchTerm) || 
                          nome.includes(searchTerm) || 
                          cpf.includes(searchTerm) ||
                          cargo.includes(searchTerm) ||
                          departamento.includes(searchTerm);
        
        const matchStatus = !statusFiltro || status === statusFiltro;
        
        if (matchSearch && matchStatus) {
            linha.style.display = '';
            visibleCount++;
        } else {
            linha.style.display = 'none';
        }
    });
    
    console.log(`[RH] Filtros aplicados: ${visibleCount} colaboradores visíveis (busca: "${searchTerm}", status: "${statusFiltro}")`);
}

function limparFiltros() {
    const searchInput = document.getElementById('searchInput');
    const filterStatus = document.getElementById('filterStatus');
    
    if (searchInput) searchInput.value = '';
    if (filterStatus) filterStatus.value = '';
    
    filtrarTabela();
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

        const modal = new bootstrap.Modal(document.getElementById('modalReajuste'));
        modal.show();
    } catch (error) {
        console.error('[RH] Erro ao abrir modal de reajuste:', error);
        mostrarAlerta('Não foi possível carregar dados do colaborador.', 'danger');
    }
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

    colaboradorCache.set(colaboradorId, data.data);
    return data.data;
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
window.formatarData = formatarData;
window.abrirModalPromocao = abrirModalPromocao;
window.abrirModalReajuste = abrirModalReajuste;
window.abrirModalTransferencia = abrirModalTransferencia;
window.abrirModalFerias = abrirModalFerias;
window.confirmarReativacao = confirmarReativacao;
