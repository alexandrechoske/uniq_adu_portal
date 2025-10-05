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
