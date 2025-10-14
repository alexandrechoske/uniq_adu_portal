/**
 * JavaScript para o módulo de Estrutura Organizacional
 * Gestão de Cargos e Departamentos
 */

// ========================================
// FUNÇÕES PARA CARGOS
// ========================================

/**
 * Abre modal para criar novo cargo
 */
function abrirModalNovo() {
    document.getElementById('modalTitle').textContent = 'Novo Cargo';
    document.getElementById('formCargo').reset();
    document.getElementById('cargo_id').value = '';
}

/**
 * Editar cargo existente
 */
async function editarCargo(cargoId) {
    try {
        const response = await fetch(`/rh/estrutura/api/cargos/${cargoId}`, {
            credentials: 'same-origin'  // Envia cookies de sessão
        });
        const data = await response.json();
        
        if (data.data) {
            const cargo = data.data;
            
            // Preencher formulário
            document.getElementById('modalTitle').textContent = 'Editar Cargo';
            document.getElementById('cargo_id').value = cargo.id;
            document.getElementById('nome').value = cargo.nome_cargo || '';
            document.getElementById('grupo').value = cargo.grupo_cargo || '';
            document.getElementById('descricao').value = cargo.descricao || '';
            
            // Abrir modal
            const modal = new bootstrap.Modal(document.getElementById('modalCargo'));
            modal.show();
        } else {
            alert('❌ Erro ao carregar dados do cargo');
        }
    } catch (error) {
        console.error('Erro:', error);
        alert('❌ Erro ao carregar cargo');
    }
}

/**
 * Salvar cargo (criar ou atualizar)
 */
async function salvarCargo() {
    const cargoId = document.getElementById('cargo_id').value;
    const nome = document.getElementById('nome').value.trim();
    const grupo = document.getElementById('grupo').value.trim();
    const descricao = document.getElementById('descricao').value.trim();
    
    // Validação
    if (!nome) {
        alert('⚠️ Nome do cargo é obrigatório');
        return;
    }
    
    // Preparar dados
    const cargoData = {
        nome: nome,
        grupo: grupo || null,
        descricao: descricao || null
    };
    
    try {
        let response;
        
        if (cargoId) {
            // Atualizar cargo existente
            response = await fetch(`/rh/estrutura/api/cargos/${cargoId}`, {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                credentials: 'same-origin',
                body: JSON.stringify(cargoData)
            });
        } else {
            // Criar novo cargo
            response = await fetch('/rh/estrutura/api/cargos', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                credentials: 'same-origin',
                body: JSON.stringify(cargoData)
            });
        }
        
        const data = await response.json();
        
        if (data.success) {
            alert('✅ ' + data.message);
            // Fechar modal e recarregar página
            bootstrap.Modal.getInstance(document.getElementById('modalCargo')).hide();
            location.reload();
        } else {
            alert('❌ Erro: ' + data.message);
        }
    } catch (error) {
        console.error('Erro:', error);
        alert('❌ Erro ao salvar cargo');
    }
}

/**
 * Confirmar exclusão de cargo
 */
function confirmarExclusao(cargoId, cargoNome) {
    document.getElementById('cargoNomeExcluir').textContent = cargoNome;
    
    // Configurar botão de confirmação
    const btnConfirmar = document.getElementById('btnConfirmarExclusao');
    btnConfirmar.onclick = function() {
        excluirCargo(cargoId);
    };
    
    // Abrir modal
    const modal = new bootstrap.Modal(document.getElementById('modalExcluir'));
    modal.show();
}

/**
 * Excluir cargo
 */
async function excluirCargo(cargoId) {
    try {
        const response = await fetch(`/rh/estrutura/api/cargos/${cargoId}`, {
            method: 'DELETE',
            credentials: 'same-origin'
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert('✅ ' + data.message);
            // Fechar modal e recarregar página
            bootstrap.Modal.getInstance(document.getElementById('modalExcluir')).hide();
            location.reload();
        } else {
            alert('❌ ' + data.message);
            // Fechar modal mesmo em caso de erro
            bootstrap.Modal.getInstance(document.getElementById('modalExcluir')).hide();
        }
    } catch (error) {
        console.error('Erro:', error);
        alert('❌ Erro ao excluir cargo');
        bootstrap.Modal.getInstance(document.getElementById('modalExcluir')).hide();
    }
}

// ========================================
// FUNÇÕES PARA DEPARTAMENTOS
// ========================================

/**
 * Abre modal para criar novo departamento
 */
function abrirModalNovoDepartamento() {
    document.getElementById('modalTitleDepto').textContent = 'Novo Departamento';
    document.getElementById('formDepartamento').reset();
    document.getElementById('departamento_id').value = '';
}

/**
 * Editar departamento existente
 */
async function editarDepartamento(deptoId) {
    try {
        const response = await fetch(`/rh/estrutura/api/departamentos/${deptoId}`, {
            credentials: 'same-origin'
        });
        const data = await response.json();
        
        // API retorna: {success: true, departamento: {...}}
        if (data.success && data.departamento) {
            const depto = data.departamento;
            
            // Preencher formulário
            document.getElementById('modalTitleDepto').textContent = 'Editar Departamento';
            document.getElementById('departamento_id').value = depto.id;
            document.getElementById('nome_depto').value = depto.nome_departamento || '';
            document.getElementById('codigo_centro_custo').value = depto.codigo_centro_custo || '';
            document.getElementById('descricao_depto').value = depto.descricao || '';
            
            // Abrir modal
            const modal = new bootstrap.Modal(document.getElementById('modalDepartamento'));
            modal.show();
        } else {
            alert('❌ Erro ao carregar dados do departamento: ' + (data.message || 'Erro desconhecido'));
        }
    } catch (error) {
        console.error('Erro:', error);
        alert('❌ Erro ao carregar departamento: ' + error.message);
    }
}

/**
 * Salvar departamento (criar ou atualizar)
 */
async function salvarDepartamento() {
    const deptoId = document.getElementById('departamento_id').value;
    const nome = document.getElementById('nome_depto').value.trim();
    const codigoCentroCusto = document.getElementById('codigo_centro_custo').value.trim();
    const descricao = document.getElementById('descricao_depto').value.trim();
    
    // Validação
    if (!nome) {
        alert('⚠️ Nome do departamento é obrigatório');
        return;
    }
    
    // Preparar dados
    const deptoData = {
        nome: nome,
        codigo_centro_custo: codigoCentroCusto || null,
        descricao: descricao || null
    };
    
    try {
        let response;
        
        if (deptoId) {
            // Atualizar departamento existente
            response = await fetch(`/rh/estrutura/api/departamentos/${deptoId}`, {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                credentials: 'same-origin',
                body: JSON.stringify(deptoData)
            });
        } else {
            // Criar novo departamento
            response = await fetch('/rh/estrutura/api/departamentos', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                credentials: 'same-origin',
                body: JSON.stringify(deptoData)
            });
        }
        
        const data = await response.json();
        
        if (data.success) {
            alert('✅ ' + data.message);
            // Fechar modal e recarregar página
            bootstrap.Modal.getInstance(document.getElementById('modalDepartamento')).hide();
            location.reload();
        } else {
            alert('❌ Erro: ' + data.message);
        }
    } catch (error) {
        console.error('Erro:', error);
        alert('❌ Erro ao salvar departamento');
    }
}

/**
 * Confirmar exclusão de departamento
 */
function confirmarExclusaoDepto(deptoId, deptoNome) {
    document.getElementById('deptoNomeExcluir').textContent = deptoNome;
    
    // Configurar botão de confirmação
    const btnConfirmar = document.getElementById('btnConfirmarExclusaoDepto');
    btnConfirmar.onclick = function() {
        excluirDepartamento(deptoId);
    };
    
    // Abrir modal
    const modal = new bootstrap.Modal(document.getElementById('modalExcluirDepto'));
    modal.show();
}

/**
 * Excluir departamento
 */
async function excluirDepartamento(deptoId) {
    try {
        const response = await fetch(`/rh/estrutura/api/departamentos/${deptoId}`, {
            method: 'DELETE',
            credentials: 'same-origin'
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert('✅ ' + data.message);
            // Fechar modal e recarregar página
            bootstrap.Modal.getInstance(document.getElementById('modalExcluirDepto')).hide();
            location.reload();
        } else {
            alert('❌ ' + data.message);
            // Fechar modal mesmo em caso de erro
            bootstrap.Modal.getInstance(document.getElementById('modalExcluirDepto')).hide();
        }
    } catch (error) {
        console.error('Erro:', error);
        alert('❌ Erro ao excluir departamento');
        bootstrap.Modal.getInstance(document.getElementById('modalExcluirDepto')).hide();
    }
}

// ========================================
// FUNÇÕES - ACESSOS PORTAL CONTABILIDADE
// ========================================

let acessosContabilidadeCache = [];

function inicializarGestaoAcessosContabilidade() {
    try {
        const script = document.getElementById('dadosAcessosContabilidade');
        acessosContabilidadeCache = script ? JSON.parse(script.textContent || '[]') : [];
    } catch (error) {
        console.warn('Não foi possível carregar cache de acessos contabilidade', error);
        acessosContabilidadeCache = [];
    }
}

function obterModalAcesso() {
    const modalEl = document.getElementById('modalAcessoContabilidade');
    return modalEl ? new bootstrap.Modal(modalEl) : null;
}

function obterModalStatusAcesso() {
    const modalEl = document.getElementById('modalStatusAcesso');
    return modalEl ? new bootstrap.Modal(modalEl) : null;
}

function preencherFormularioAcesso(dados) {
    document.getElementById('acessoId').value = dados?.id || '';
    document.getElementById('nomeUsuarioAcesso').value = dados?.nome_usuario || '';
    document.getElementById('descricaoAcesso').value = dados?.descricao || '';
    document.getElementById('senhaAcesso').value = '';
    document.getElementById('confirmacaoSenhaAcesso').value = '';
    document.getElementById('statusAcesso').checked = dados?.is_active !== false;
}

function abrirModalNovoAcesso() {
    document.getElementById('modalAcessoTitulo').textContent = 'Novo acesso';
    preencherFormularioAcesso({ is_active: true });
}

function localizarAcessoCache(acessoId) {
    return acessosContabilidadeCache.find((item) => item.id === acessoId);
}

function editarAcessoContabilidade(acessoId) {
    const registro = localizarAcessoCache(acessoId);
    if (!registro) {
        alert('Não foi possível localizar este acesso.');
        return;
    }

    document.getElementById('modalAcessoTitulo').textContent = 'Editar acesso';
    preencherFormularioAcesso(registro);
    const modal = obterModalAcesso();
    if (modal) {
        modal.show();
    }
}

function validarSenhaCampos(senha, confirmacao) {
    if (!senha && !confirmacao) {
        return { valido: true, mensagem: '' };
    }
    if (senha.length > 0 && senha.length < 8) {
        return { valido: false, mensagem: 'A senha deve ter pelo menos 8 caracteres.' };
    }
    if (senha !== confirmacao) {
        return { valido: false, mensagem: 'As senhas informadas não conferem.' };
    }
    return { valido: true, mensagem: '' };
}

async function salvarAcessoContabilidade() {
    const acessoId = document.getElementById('acessoId').value;
    const nomeUsuario = document.getElementById('nomeUsuarioAcesso').value.trim();
    const descricao = document.getElementById('descricaoAcesso').value.trim();
    const senha = document.getElementById('senhaAcesso').value;
    const confirmacaoSenha = document.getElementById('confirmacaoSenhaAcesso').value;
    const isActive = document.getElementById('statusAcesso').checked;

    if (!nomeUsuario) {
        alert('Informe o nome de usuário.');
        return;
    }

    if (!acessoId && senha.length < 8) {
        alert('Para novos acessos, informe uma senha com pelo menos 8 caracteres.');
        return;
    }

    const validacao = validarSenhaCampos(senha, confirmacaoSenha);
    if (!validacao.valido) {
        alert(validacao.mensagem);
        return;
    }

    const payload = {
        nome_usuario: nomeUsuario,
        descricao: descricao,
        is_active: isActive
    };

    if (senha) {
        payload.senha = senha;
    }

    const url = acessoId
        ? `/rh/estrutura/api/acessos-contabilidade/${acessoId}`
        : '/rh/estrutura/api/acessos-contabilidade';
    const method = acessoId ? 'PUT' : 'POST';

    try {
        const botao = document.getElementById('btnSalvarAcesso');
        if (botao) {
            botao.disabled = true;
            botao.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Salvando...';
        }

        const response = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (!data.success) {
            alert(data.message || 'Não foi possível salvar o acesso.');
            return;
        }

        alert(data.message || 'Acesso salvo com sucesso.');
        location.reload();
    } catch (error) {
        console.error('Erro ao salvar acesso', error);
        alert('Erro inesperado ao salvar o acesso.');
    } finally {
        const botao = document.getElementById('btnSalvarAcesso');
        if (botao) {
            botao.disabled = false;
            botao.innerHTML = '<i class="mdi mdi-content-save"></i> Salvar';
        }
    }
}

function confirmarAlteracaoStatusAcesso(acessoId) {
    const registro = localizarAcessoCache(acessoId);
    if (!registro) {
        alert('Acesso não encontrado.');
        return;
    }

    const novoStatus = !registro.is_active;
    document.getElementById('acessoStatusId').value = acessoId;
    document.getElementById('novoStatusAcesso').value = novoStatus ? 'true' : 'false';

    const texto = novoStatus
        ? `Deseja reativar o acesso <strong>${registro.nome_usuario}</strong>?`
        : `Deseja desativar o acesso <strong>${registro.nome_usuario}</strong>?`;
    document.getElementById('textoStatusAcesso').innerHTML = texto;

    const modal = obterModalStatusAcesso();
    if (modal) {
        modal.show();
    }
}

async function atualizarStatusAcesso() {
    const acessoId = document.getElementById('acessoStatusId').value;
    const novoStatus = document.getElementById('novoStatusAcesso').value === 'true';

    if (!acessoId) {
        alert('Acesso não identificado.');
        return;
    }

    try {
        const botao = document.getElementById('btnConfirmarStatusAcesso');
        if (botao) {
            botao.disabled = true;
            botao.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processando...';
        }

        const response = await fetch(`/rh/estrutura/api/acessos-contabilidade/${acessoId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify({ is_active: novoStatus })
        });

        const data = await response.json();

        if (!data.success) {
            alert(data.message || 'Não foi possível atualizar o status.');
            return;
        }

        alert(data.message || 'Status atualizado com sucesso.');
        location.reload();
    } catch (error) {
        console.error('Erro ao atualizar status', error);
        alert('Erro inesperado ao atualizar o status.');
    } finally {
        const botao = document.getElementById('btnConfirmarStatusAcesso');
        if (botao) {
            botao.disabled = false;
            botao.innerHTML = 'Confirmar';
        }
    }
}
