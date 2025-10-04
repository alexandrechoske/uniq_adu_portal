/**
 * Módulo Recrutamento - JavaScript
 * Gestão de Vagas e Candidatos
 */

// ========================================
// FUNÇÕES PARA GESTÃO DE VAGAS
// ========================================

/**
 * Abre modal para criar nova vaga
 */
function abrirModalNovaVaga() {
    document.getElementById('modalVagaLabel').textContent = 'Nova Vaga';
    document.getElementById('formVaga').reset();
    document.getElementById('vaga_id').value = '';
}

/**
 * Editar vaga existente
 */
async function editarVaga(vagaId) {
    try {
        const response = await fetch(`/rh/recrutamento/api/vagas/${vagaId}`, {
            credentials: 'same-origin'
        });
        const data = await response.json();
        
        if (data.data) {
            const vaga = data.data;
            
            // Preencher formulário
            document.getElementById('modalVagaLabel').textContent = 'Editar Vaga';
            document.getElementById('vaga_id').value = vaga.id;
            document.getElementById('titulo').value = vaga.titulo || '';
            document.getElementById('cargo_id').value = vaga.cargo_id || '';
            document.getElementById('tipo_contratacao').value = vaga.tipo_contratacao || 'CLT';
            document.getElementById('localizacao').value = vaga.localizacao || '';
            document.getElementById('descricao').value = vaga.descricao || '';
            document.getElementById('requisitos').value = vaga.requisitos || '';
            
            // Abrir modal
            const modal = new bootstrap.Modal(document.getElementById('modalVaga'));
            modal.show();
        } else {
            alert('❌ Erro ao carregar dados da vaga');
        }
    } catch (error) {
        console.error('Erro:', error);
        alert('❌ Erro ao carregar vaga');
    }
}

/**
 * Salvar vaga (criar ou atualizar)
 */
async function salvarVaga() {
    const vagaId = document.getElementById('vaga_id').value;
    const titulo = document.getElementById('titulo').value.trim();
    const cargo_id = document.getElementById('cargo_id').value.trim();
    const tipo_contratacao = document.getElementById('tipo_contratacao').value.trim();
    const localizacao = document.getElementById('localizacao').value.trim();
    const descricao = document.getElementById('descricao').value.trim();
    const requisitos = document.getElementById('requisitos').value.trim();
    
    // Validação
    if (!titulo) {
        alert('⚠️ Título da vaga é obrigatório');
        return;
    }
    
    if (!cargo_id) {
        alert('⚠️ Cargo oficial é obrigatório');
        return;
    }
    
    if (!descricao) {
        alert('⚠️ Descrição da vaga é obrigatória');
        return;
    }
    
    if (!requisitos) {
        alert('⚠️ Requisitos são obrigatórios');
        return;
    }
    
    // Preparar dados
    const vagaData = {
        titulo: titulo,
        cargo_id: cargo_id,
        tipo_contratacao: tipo_contratacao || 'CLT',
        localizacao: localizacao || null,
        descricao: descricao,
        requisitos: requisitos
    };
    
    try {
        let response;
        
        if (vagaId) {
            // Atualizar vaga existente
            response = await fetch(`/rh/recrutamento/api/vagas/${vagaId}`, {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                credentials: 'same-origin',
                body: JSON.stringify(vagaData)
            });
        } else {
            // Criar nova vaga
            response = await fetch('/rh/recrutamento/api/vagas', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                credentials: 'same-origin',
                body: JSON.stringify(vagaData)
            });
        }
        
        const data = await response.json();
        
        if (data.success) {
            alert('✅ ' + data.message);
            // Fechar modal e recarregar página
            bootstrap.Modal.getInstance(document.getElementById('modalVaga')).hide();
            location.reload();
        } else {
            alert('❌ Erro: ' + data.message);
        }
    } catch (error) {
        console.error('Erro:', error);
        alert('❌ Erro ao salvar vaga');
    }
}

/**
 * Alterar status da vaga
 */
async function alterarStatusVaga(vagaId, novoStatus) {
    const statusDescricao = {
        'Aberta': 'reabrir',
        'Pausada': 'pausar',
        'Fechada': 'fechar'
    };
    
    const acao = statusDescricao[novoStatus] || 'alterar';
    
    if (!confirm(`Deseja ${acao} esta vaga?`)) {
        return;
    }
    
    try {
        const response = await fetch(`/rh/recrutamento/api/vagas/${vagaId}/status`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            credentials: 'same-origin',
            body: JSON.stringify({status: novoStatus})
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert('✅ ' + data.message);
            location.reload();
        } else {
            alert('❌ Erro: ' + data.message);
        }
    } catch (error) {
        console.error('Erro:', error);
        alert('❌ Erro ao alterar status da vaga');
    }
}

/**
 * Confirmar exclusão de vaga
 */
function confirmarExclusao(vagaId, vagaTitulo) {
    document.getElementById('vagaNomeExcluir').textContent = vagaTitulo;
    
    const modal = new bootstrap.Modal(document.getElementById('modalConfirmarExclusao'));
    modal.show();
    
    // Configurar botão de confirmação
    document.getElementById('btnConfirmarExclusao').onclick = async function() {
        await excluirVaga(vagaId);
    };
}

/**
 * Excluir vaga
 */
async function excluirVaga(vagaId) {
    try {
        const response = await fetch(`/rh/recrutamento/api/vagas/${vagaId}`, {
            method: 'DELETE',
            credentials: 'same-origin'
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert('✅ ' + data.message);
            bootstrap.Modal.getInstance(document.getElementById('modalConfirmarExclusao')).hide();
            location.reload();
        } else {
            alert('❌ Erro: ' + data.message);
        }
    } catch (error) {
        console.error('Erro:', error);
        alert('❌ Erro ao excluir vaga');
    }
}

// ========================================
// FUNÇÕES PARA GESTÃO DE CANDIDATOS (KANBAN)
// ========================================

/**
 * Inicializar Drag and Drop no Kanban
 */
function initKanbanDragDrop() {
    const cards = document.querySelectorAll('.candidato-card');
    const columns = document.querySelectorAll('.kanban-cards');
    
    // Configurar cards para serem arrastáveis
    cards.forEach(card => {
        card.addEventListener('dragstart', handleDragStart);
        card.addEventListener('dragend', handleDragEnd);
    });
    
    // Configurar colunas para receber drops
    columns.forEach(column => {
        column.addEventListener('dragover', handleDragOver);
        column.addEventListener('drop', handleDrop);
        column.addEventListener('dragleave', handleDragLeave);
    });
}

let draggedCard = null;

function handleDragStart(e) {
    draggedCard = this;
    this.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/html', this.innerHTML);
}

function handleDragEnd(e) {
    this.classList.remove('dragging');
    
    // Remover classe drag-over de todas as colunas
    document.querySelectorAll('.kanban-column').forEach(col => {
        col.classList.remove('drag-over');
    });
}

function handleDragOver(e) {
    if (e.preventDefault) {
        e.preventDefault();
    }
    
    e.dataTransfer.dropEffect = 'move';
    
    // Adicionar visual de drag over
    const column = this.closest('.kanban-column');
    column.classList.add('drag-over');
    
    return false;
}

function handleDragLeave(e) {
    const column = this.closest('.kanban-column');
    column.classList.remove('drag-over');
}

async function handleDrop(e) {
    if (e.stopPropagation) {
        e.stopPropagation();
    }
    
    const kanbanCards = this; // Este é o elemento .kanban-cards onde o drop aconteceu
    const column = this.closest('.kanban-column');
    column.classList.remove('drag-over');
    
    if (draggedCard) {
        // Pegar o novo status da coluna - o data-status está no .kanban-cards (this)
        const novoStatus = kanbanCards.dataset.status;
        const candidatoId = draggedCard.dataset.candidatoId;
        
        console.log('🔍 DEBUG Drag-and-Drop:');
        console.log('   Candidato ID:', candidatoId);
        console.log('   Elemento drop (this):', kanbanCards);
        console.log('   Novo Status (data-status):', novoStatus);
        console.log('   Tipo do novo status:', typeof novoStatus);
        console.log('   novoStatus é undefined?', novoStatus === undefined);
        
        // Mover o card visualmente
        this.appendChild(draggedCard);
        
        // Atualizar contador
        atualizarContadores();
        
        // Atualizar no backend
        await moverCandidato(candidatoId, novoStatus);
    }
    
    return false;
}

/**
 * Mover candidato para novo status (API)
 */
async function moverCandidato(candidatoId, novoStatus) {
    try {
        console.log('📡 Enviando para API:');
        console.log('   URL:', `/rh/recrutamento/api/candidatos/${candidatoId}/mover`);
        console.log('   Payload:', {novo_status: novoStatus});
        
        // Validar antes de enviar
        if (!novoStatus || novoStatus === 'undefined') {
            console.error('❌ ERRO: novoStatus está vazio ou undefined!');
            alert('❌ Erro: Status da coluna não foi encontrado. Recarregue a página.');
            location.reload();
            return;
        }
        
        const response = await fetch(`/rh/recrutamento/api/candidatos/${candidatoId}/mover`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            credentials: 'same-origin',
            body: JSON.stringify({novo_status: novoStatus})
        });
        
        const data = await response.json();
        
        console.log('📥 Resposta da API:');
        console.log('   Status HTTP:', response.status);
        console.log('   Data:', data);
        
        if (!data.success) {
            alert('❌ Erro ao mover candidato: ' + data.message);
            location.reload(); // Recarregar para desfazer mudança visual
        } else {
            console.log('✅ Candidato movido com sucesso!');
        }
    } catch (error) {
        console.error('❌ Erro na requisição:', error);
        alert('❌ Erro ao mover candidato');
        location.reload();
    }
}

/**
 * Atualizar contadores de candidatos nas colunas
 */
function atualizarContadores() {
    document.querySelectorAll('.kanban-column').forEach(column => {
        const count = column.querySelectorAll('.candidato-card').length;
        const countBadge = column.querySelector('.kanban-column-count');
        if (countBadge) {
            countBadge.textContent = count;
        }
    });
}

/**
 * Abrir detalhes do candidato
 */
async function verDetalhesCandidato(candidatoId) {
    try {
        const response = await fetch(`/rh/recrutamento/api/candidatos/${candidatoId}`, {
            credentials: 'same-origin'
        });
        const data = await response.json();
        
        if (data.data) {
            const candidato = data.data;
            
            // Preencher modal com detalhes
            document.getElementById('detalheCandidatoNome').textContent = candidato.nome_completo;
            document.getElementById('detalheCandidatoEmail').textContent = candidato.email || 'Não informado';
            document.getElementById('detalheCandidatoTelefone').textContent = candidato.telefone || 'Não informado';
            document.getElementById('detalheCandidatoData').textContent = candidato.data_candidatura ? 
                new Date(candidato.data_candidatura).toLocaleDateString('pt-BR') : 'Não informado';
            document.getElementById('detalheCandidatoFonte').textContent = candidato.fonte_candidatura || 'Não informado';
            document.getElementById('detalheCandidatoStatus').textContent = candidato.status_processo || 'Triagem';
            document.getElementById('candidatoIdObservacoes').value = candidato.id;
            
            // Link de currículo
            if (candidato.url_curriculo) {
                document.getElementById('btnDownloadCurriculo').href = candidato.url_curriculo;
                document.getElementById('btnDownloadCurriculo').style.display = 'inline-flex';
            } else {
                document.getElementById('btnDownloadCurriculo').style.display = 'none';
            }
            
            // Carregar histórico de observações
            await carregarHistoricoObservacoes(candidato.id);
            
            // Limpar campo de nova observação
            document.getElementById('novaObservacao').value = '';
            
            // Abrir modal
            const modal = new bootstrap.Modal(document.getElementById('modalDetalhesCandidato'));
            modal.show();
        } else {
            alert('❌ Erro ao carregar dados do candidato');
        }
    } catch (error) {
        console.error('Erro:', error);
        alert('❌ Erro ao carregar candidato');
    }
}

/**
 * Carregar histórico de observações do candidato
 */
async function carregarHistoricoObservacoes(candidatoId) {
    try {
        const response = await fetch(`/rh/recrutamento/api/candidatos/${candidatoId}/observacoes`, {
            credentials: 'same-origin'
        });
        const data = await response.json();
        
        if (data.success) {
            const historico = data.data.historico || [];
            const container = document.getElementById('timelineObservacoes');
            const totalBadge = document.getElementById('totalObservacoes');
            
            totalBadge.textContent = historico.length;
            
            if (historico.length === 0) {
                container.innerHTML = `
                    <div class="text-center text-muted py-4">
                        <i class="mdi mdi-information-outline" style="font-size: 2rem;"></i>
                        <p class="mb-0">Nenhuma observação registrada ainda</p>
                    </div>
                `;
            } else {
                container.innerHTML = historico.map(obs => {
                    const data = new Date(obs.data);
                    const dataFormatada = data.toLocaleDateString('pt-BR', {
                        day: '2-digit',
                        month: '2-digit',
                        year: 'numeric'
                    });
                    const horaFormatada = data.toLocaleTimeString('pt-BR', {
                        hour: '2-digit',
                        minute: '2-digit'
                    });
                    
                    return `
                        <div class="timeline-item">
                            <div class="timeline-item-marker"></div>
                            <div class="timeline-item-header">
                                <div class="timeline-item-usuario">
                                    <i class="mdi mdi-account-circle"></i>
                                    ${obs.usuario || 'Sistema'}
                                </div>
                                <div class="timeline-item-date">
                                    ${dataFormatada} às ${horaFormatada}
                                </div>
                            </div>
                            <div class="timeline-item-content">
                                ${obs.observacao}
                            </div>
                        </div>
                    `;
                }).join('');
            }
        }
    } catch (error) {
        console.error('Erro ao carregar histórico:', error);
    }
}

/**
 * Salvar nova observação
 */
async function salvarObservacao() {
    const candidatoId = document.getElementById('candidatoIdObservacoes').value;
    const novaObservacao = document.getElementById('novaObservacao').value.trim();
    
    if (!novaObservacao) {
        alert('⚠️ Digite uma observação antes de salvar');
        return;
    }
    
    try {
        const response = await fetch(`/rh/recrutamento/api/candidatos/${candidatoId}/observacoes`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            credentials: 'same-origin',
            body: JSON.stringify({observacao: novaObservacao})
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Limpar campo
            document.getElementById('novaObservacao').value = '';
            
            // Recarregar histórico
            await carregarHistoricoObservacoes(candidatoId);
            
            // Mostrar mensagem de sucesso
            alert('✅ Observação adicionada com sucesso!');
        } else {
            alert('❌ Erro: ' + data.message);
        }
    } catch (error) {
        console.error('Erro:', error);
        alert('❌ Erro ao salvar observação');
    }
}

// Inicializar quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', function() {
    // Se estiver na página de Kanban, inicializar drag-and-drop
    if (document.querySelector('.kanban-container')) {
        initKanbanDragDrop();
    }
});
