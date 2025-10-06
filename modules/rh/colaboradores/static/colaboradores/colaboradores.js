// ===================================================================
// JAVASCRIPT DO MÓDULO RH - COLABORADORES
// ===================================================================

// Variável global para armazenar ID do colaborador a ser desligado
let colaboradorIdParaDesligar = null;

// ===================================================================
// INICIALIZAÇÃO
// ===================================================================
document.addEventListener('DOMContentLoaded', function() {
    console.log('[RH] Módulo de Colaboradores inicializado');
    
    // Inicializar filtros e busca
    inicializarFiltros();
    
    // Inicializar modal de desligamento
    inicializarModalDesligamento();
    
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

// ===================================================================
// UTILITÁRIOS
// ===================================================================
function mostrarAlerta(mensagem, tipo = 'info') {
    // Criar elemento de alerta
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${tipo} alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-3`;
    alertDiv.style.zIndex = '9999';
    alertDiv.style.minWidth = '300px';
    alertDiv.innerHTML = `
        ${mensagem}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(alertDiv);
    
    // Remover após 5 segundos
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

function formatarCPF(cpf) {
    return cpf.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4');
}

function formatarTelefone(telefone) {
    if (telefone.length === 11) {
        return telefone.replace(/(\d{2})(\d{5})(\d{4})/, '($1) $2-$3');
    } else if (telefone.length === 10) {
        return telefone.replace(/(\d{2})(\d{4})(\d{4})/, '($1) $2-$3');
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
