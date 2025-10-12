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
        
        if (data.success && data.vaga) {
            const vaga = data.vaga;
            
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
            alert('❌ Erro ao carregar dados da vaga: ' + (data.message || 'Erro desconhecido'));
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
    const requisitos_obrigatorios = document.getElementById('requisitos_obrigatorios').value.trim();
    const requisitos_desejaveis = document.getElementById('requisitos_desejaveis').value.trim();
    const diferenciais = document.getElementById('diferenciais').value.trim();
    
    // Novos campos
    const faixa_salarial_min = document.getElementById('faixa_salarial_min').value;
    const faixa_salarial_max = document.getElementById('faixa_salarial_max').value;
    
    // Benefícios (array JSON)
    let beneficios = [];
    try {
        const beneficiosValue = document.getElementById('beneficios').value;
        if (beneficiosValue) {
            beneficios = JSON.parse(beneficiosValue);
        }
    } catch (e) {
        console.warn('Erro ao parsear benefícios, usando array vazio:', e);
    }
    
    const nivel_senioridade = document.getElementById('nivel_senioridade').value;
    const quantidade_vagas = document.getElementById('quantidade_vagas').value;
    const regime_trabalho = document.getElementById('regime_trabalho').value;
    const carga_horaria = document.getElementById('carga_horaria').value.trim();
    
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
    
    if (!requisitos_obrigatorios) {
        alert('⚠️ Requisitos obrigatórios são necessários');
        return;
    }
    
    // Preparar dados
    const vagaData = {
        titulo: titulo,
        cargo_id: cargo_id,
        tipo_contratacao: tipo_contratacao || 'CLT',
        localizacao: localizacao || null,
        descricao: descricao,
        requisitos: requisitos_obrigatorios, // Campo antigo (compatibilidade)
        requisitos_obrigatorios: requisitos_obrigatorios,
        requisitos_desejaveis: requisitos_desejaveis || null,
        diferenciais: diferenciais || null,
        // Novos campos de remuneração
        faixa_salarial_min: faixa_salarial_min ? parseFloat(faixa_salarial_min) : null,
        faixa_salarial_max: faixa_salarial_max ? parseFloat(faixa_salarial_max) : null,
        beneficios: beneficios.length > 0 ? beneficios : null,
        // Novos campos de detalhes
        nivel_senioridade: nivel_senioridade || null,
        quantidade_vagas: quantidade_vagas ? parseInt(quantidade_vagas) : 1,
        regime_trabalho: regime_trabalho || null,
        carga_horaria: carga_horaria || null
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
        'Aberta': 'ativar',
        'Pausada': 'pausar',
        'Fechada': 'desativar',
        'Cancelada': 'cancelar'
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
 * Helpers para ativar/desativar com semântica clara na camada de UI
 */
function desativarVaga(vagaId) {
    alterarStatusVaga(vagaId, 'Fechada');
}

function ativarVaga(vagaId) {
    alterarStatusVaga(vagaId, 'Aberta');
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
        
        // Remover mensagem "Nenhum candidato" se existir no destino
        const emptyMessage = kanbanCards.querySelector('.text-center.text-muted');
        if (emptyMessage) {
            emptyMessage.remove();
        }
        
        // Verificar se a coluna de origem ficou vazia e adicionar mensagem
        const sourceColumn = draggedCard.closest('.kanban-cards');
        if (sourceColumn && sourceColumn !== kanbanCards) {
            const cardsInSource = sourceColumn.querySelectorAll('.candidato-card').length;
            if (cardsInSource === 0 && !sourceColumn.querySelector('.text-center.text-muted')) {
                const emptyDiv = document.createElement('div');
                emptyDiv.className = 'text-center text-muted py-4';
                emptyDiv.innerHTML = `
                    <i class="mdi mdi-inbox-outline" style="font-size: 2rem;"></i>
                    <p class="mb-0 mt-2 small">Nenhum candidato</p>
                `;
                sourceColumn.appendChild(emptyDiv);
            }
        }
        
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
            // Atualizar KPIs após mover com sucesso
            atualizarKPIs();
            
            // 🔥 NOVO: Se moveu para "Contratado", adicionar botão de efetivação
            if (novoStatus === 'Contratado' && data.data && !data.data.colaborador_id) {
                const card = document.querySelector(`.candidato-card[data-candidato-id="${candidatoId}"]`);
                if (card) {
                    console.log('🎯 Candidato movido para Contratado - adicionando botão');
                    adicionarBotaoEfetivacao(card, candidatoId);
                }
            }
        }
    } catch (error) {
        console.error('❌ Erro na requisição:', error);
        alert('❌ Erro ao mover candidato');
        location.reload();
    }
}

/**
 * Atualizar KPIs da página de candidatos
 */
function atualizarKPIs() {
    // Status que indicam "em processo" (não finalizados)
    const statusEmProcesso = ['Triagem', 'Contato Inicial', 'Entrevista RH', 'Teste Técnico', 
                              'Entrevista Gestor', 'Proposta Enviada', 'Aguardando Resposta'];
    
    // Status que indicam "aprovados"
    const statusAprovados = ['Aprovado', 'Contratado'];
    
    // Contar todos os cards de candidatos
    const todosCards = document.querySelectorAll('.candidato-card');
    const totalCandidatos = todosCards.length;
    
    // Contar candidatos em processo
    let emProcesso = 0;
    todosCards.forEach(card => {
        const coluna = card.closest('.kanban-cards');
        if (coluna) {
            const status = coluna.dataset.status;
            if (statusEmProcesso.includes(status)) {
                emProcesso++;
            }
        }
    });
    
    // Contar candidatos aprovados
    let aprovados = 0;
    todosCards.forEach(card => {
        const coluna = card.closest('.kanban-cards');
        if (coluna) {
            const status = coluna.dataset.status;
            if (statusAprovados.includes(status)) {
                aprovados++;
            }
        }
    });
    
    // Calcular taxa de conversão
    const taxaConversao = totalCandidatos > 0 
        ? ((aprovados / totalCandidatos) * 100).toFixed(1)
        : 0;
    
    // Atualizar valores nos KPIs
    const kpiTotal = document.querySelector('.kpi-primary .kpi-value');
    if (kpiTotal) kpiTotal.textContent = totalCandidatos;
    
    const kpiEmProcesso = document.querySelector('.kpi-warning .kpi-value');
    if (kpiEmProcesso) kpiEmProcesso.textContent = emProcesso;
    
    const kpiAprovados = document.querySelector('.kpi-success .kpi-value');
    if (kpiAprovados) kpiAprovados.textContent = aprovados;
    
    const kpiTaxa = document.querySelector('.kpi-info .kpi-value');
    if (kpiTaxa) kpiTaxa.textContent = `${taxaConversao}%`;
    
    console.log('📊 KPIs atualizados:', {
        total: totalCandidatos,
        emProcesso: emProcesso,
        aprovados: aprovados,
        taxaConversao: taxaConversao + '%'
    });
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
 * Abrir detalhes COMPLETOS do candidato - FASE 2
 * Preenche todos os 37 campos do modal organizado
 */
async function verDetalhesCandidato(candidatoId) {
    try {
        const response = await fetch(`/rh/recrutamento/api/candidatos/${candidatoId}`, {
            credentials: 'same-origin'
        });
        const data = await response.json();
        
        if (data.data) {
            const candidato = data.data;
            console.log('📄 Candidato carregado (FASE 2):', candidato);
            
            // Armazenar ID do candidato
            document.getElementById('candidatoIdAtual').value = candidato.id;
            document.getElementById('candidatoIdObservacoes').value = candidato.id;
            
            // Atualizar título do modal
            document.getElementById('modalCandidatoTitulo').textContent = 
                `${candidato.nome_completo || 'Candidato'}`;
            
            // ============================================
            // SEÇÃO 1: INFORMAÇÕES PESSOAIS
            // ============================================
            setText('view_nome_completo', candidato.nome_completo);
            
            // Data de nascimento + idade
            let dataNascTexto = '-';
            if (candidato.data_nascimento) {
                const dataNasc = new Date(candidato.data_nascimento);
                const idade = calcularIdade(dataNasc);
                dataNascTexto = `${formatarData(candidato.data_nascimento)} (${idade} anos)`;
            } else if (candidato.idade) {
                dataNascTexto = `${candidato.idade} anos`;
            }
            setText('view_data_nascimento', dataNascTexto);
            
            setText('view_email', candidato.email);
            setText('view_telefone', candidato.telefone);
            setText('view_sexo', candidato.sexo);
            setText('view_estado_civil', candidato.estado_civil);
            setText('view_cidade_estado', candidato.cidade_estado);
            
            // ============================================
            // SEÇÃO 2: FORMAÇÃO E EXPERIÊNCIA
            // ============================================
            setText('view_formacao_academica', candidato.formacao_academica);
            setText('view_curso_especifico', candidato.curso_especifico);
            setText('view_area_objetivo', candidato.area_objetivo);
            setText('view_experiencia_na_area', candidato.experiencia_na_area);
            setText('view_trabalha_atualmente', formatarBoolean(candidato.trabalha_atualmente));
            
            // ============================================
            // SEÇÃO 3: CANDIDATURA
            // ============================================
            setText('view_fonte_candidatura', candidato.fonte_candidatura);
            setText('view_data_candidatura', formatarData(candidato.data_candidatura));
            setText('view_foi_indicacao', formatarBoolean(candidato.foi_indicacao));
            setText('view_indicado_por', candidato.indicado_por);
            
            // LinkedIn (com link clicável)
            setLink('view_linkedin_url', candidato.linkedin_url);
            
            // Portfólio (com link clicável)
            setLink('view_portfolio_url', candidato.portfolio_url);
            
            // Currículo
            if (candidato.url_curriculo || candidato.curriculo_path) {
                const curriculoUrl = candidato.url_curriculo || candidato.curriculo_path;
                document.getElementById('btnDownloadCurriculo').href = curriculoUrl;
                document.getElementById('btnDownloadCurriculo').style.display = 'inline-block';
            } else {
                document.getElementById('btnDownloadCurriculo').style.display = 'none';
            }
            
            // ============================================
            // SEÇÃO 4: ANÁLISE DA IA
            // ============================================
            const secaoIA = document.getElementById('secaoIA');
            if (candidato.ai_status && candidato.ai_status !== 'pending') {
                secaoIA.style.display = 'block';
                
                setHTML('view_ai_status', formatarAIStatus(candidato.ai_status));
                setHTML('view_ai_pre_filter_status', formatarPreFilterStatus(candidato.ai_pre_filter_status));
                setHTML('view_ai_match_score', formatarScore(candidato.ai_match_score));
                
                // Análise completa - extrair do JSONB
                if (candidato.ai_extracted_data_jsonb) {
                    try {
                        // Parsear JSONB se for string, ou usar diretamente se já for objeto
                        const aiData = typeof candidato.ai_extracted_data_jsonb === 'string' 
                            ? JSON.parse(candidato.ai_extracted_data_jsonb)
                            : candidato.ai_extracted_data_jsonb;
                        
                        if (aiData && aiData.analise) {
                            setText('view_ai_analise', aiData.analise);
                        } else {
                            setText('view_ai_analise', 'Análise não disponível.');
                        }
                    } catch (e) {
                        console.error('Erro ao parsear análise da IA:', e);
                        setText('view_ai_analise', 'Erro ao carregar análise.');
                    }
                } else {
                    setText('view_ai_analise', 'Análise em processamento...');
                }
            } else {
                secaoIA.style.display = 'none';
            }
            
            // ============================================
            // SEÇÃO 5: PROCESSO SELETIVO
            // ============================================
            setText('view_status_processo', candidato.status_processo || 'Triagem');
            setText('view_realizou_entrevista', formatarBoolean(candidato.realizou_entrevista));
            setText('view_data_entrevista', formatarData(candidato.data_entrevista));
            
            // ============================================
            // SEÇÃO 6: CONTRATAÇÃO (apenas visualização, ação está no card)
            // ============================================
            const secaoContratacao = document.getElementById('secaoContratacao');
            
            if (candidato.status_processo === 'Contratado' || candidato.foi_contratado) {
                secaoContratacao.style.display = 'block';
                
                setText('view_foi_contratado', formatarBoolean(candidato.foi_contratado));
                setText('view_data_contratacao', formatarData(candidato.data_contratacao));
                
                // Mostrar link para colaborador se já foi efetivado
                if (candidato.colaborador_id) {
                    const linkColaborador = `<a href="/rh/colaboradores/visualizar/${candidato.colaborador_id}" 
                                                class="btn btn-sm btn-info">
                        <i class="mdi mdi-account-eye"></i> Ver Colaborador
                    </a>`;
                    document.getElementById('view_colaborador_id').innerHTML = linkColaborador;
                } else {
                    // Instruir usuário a usar o botão no card
                    document.getElementById('view_colaborador_id').innerHTML = 
                        '<span class="text-warning"><i class="mdi mdi-alert"></i> Use o botão "Efetivar Contratação" no card do Kanban</span>';
                }
            } else {
                secaoContratacao.style.display = 'none';
            }
            
            // ============================================
            // SEÇÃO 7: OBSERVAÇÕES
            // ============================================
            await carregarHistoricoObservacoes(candidato.id);
            
            // Limpar campo de nova observação
            document.getElementById('novaObservacao').value = '';
            
            // Garantir que está em modo visualização
            document.getElementById('modoEdicao').value = 'false';
            document.getElementById('modo-visualizacao').style.display = 'block';
            document.getElementById('modo-edicao').style.display = 'none';
            document.getElementById('btnEditarCandidato').innerHTML = '<i class="mdi mdi-pencil"></i> Editar';
            document.getElementById('btnSalvarEdicao').style.display = 'none';
            
            // Abrir modal
            const modal = new bootstrap.Modal(document.getElementById('modalDetalhesCandidato'));
            modal.show();
        } else {
            alert('❌ Erro ao carregar dados do candidato');
        }
    } catch (error) {
        console.error('❌ Erro ao carregar candidato (FASE 2):', error);
        alert('❌ Erro ao carregar candidato');
    }
}

// ========================================
// FUNÇÕES AUXILIARES - FASE 2
// ========================================

/**
 * Define texto em um elemento (ou "-" se vazio)
 */
function setText(elementId, value) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = value || '-';
    }
}

/**
 * Define HTML em um elemento
 */
function setHTML(elementId, html) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = html || '-';
    }
}

/**
 * Define link clicável (ou "-" se vazio)
 */
function setLink(elementId, url) {
    const element = document.getElementById(elementId);
    if (element) {
        if (url) {
            element.innerHTML = `<a href="${url}" target="_blank" class="text-primary">
                <i class="mdi mdi-open-in-new"></i> Acessar
            </a>`;
        } else {
            element.textContent = '-';
        }
    }
}

/**
 * Formatar data DD/MM/YYYY
 */
function formatarData(dataStr) {
    if (!dataStr) return '-';
    try {
        const data = new Date(dataStr);
        if (isNaN(data.getTime())) return '-';
        return data.toLocaleDateString('pt-BR');
    } catch {
        return '-';
    }
}

/**
 * Formatar boolean como Sim/Não
 */
function formatarBoolean(valor) {
    if (valor === null || valor === undefined) return '-';
    return valor ? 'Sim' : 'Não';
}

/**
 * Calcular idade a partir de data de nascimento
 */
function calcularIdade(dataNascimento) {
    const hoje = new Date();
    let idade = hoje.getFullYear() - dataNascimento.getFullYear();
    const mes = hoje.getMonth() - dataNascimento.getMonth();
    if (mes < 0 || (mes === 0 && hoje.getDate() < dataNascimento.getDate())) {
        idade--;
    }
    return idade;
}

/**
 * Formatar status da IA
 */
function formatarAIStatus(status) {
    const statusMap = {
        'pending': '<span class="badge bg-warning">Pendente</span>',
        'processing': '<span class="badge bg-info">Processando</span>',
        'completed': '<span class="badge bg-success">Concluído</span>',
        'error': '<span class="badge bg-danger">Erro</span>'
    };
    return statusMap[status] || status || '-';
}

/**
 * Formatar pré-filtro
 */
function formatarPreFilterStatus(status) {
    const statusMap = {
        'approved': '<span class="badge bg-success"><i class="mdi mdi-check"></i> Aprovado</span>',
        'rejected': '<span class="badge bg-danger"><i class="mdi mdi-close"></i> Reprovado</span>',
        'pending': '<span class="badge bg-warning">Pendente</span>'
    };
    return statusMap[status] || status || '-';
}

/**
 * Formatar score (0-100)
 */
function formatarScore(score) {
    if (!score && score !== 0) return '-';
    const scoreNum = parseFloat(score);
    let badgeClass = 'secondary';
    if (scoreNum >= 80) badgeClass = 'success';
    else if (scoreNum >= 60) badgeClass = 'warning';
    else badgeClass = 'danger';
    
    return `<span class="badge bg-${badgeClass}" style="font-size: 1.1rem; padding: 0.5rem 1rem;">
        ${scoreNum}%
    </span>`;
}

/**
 * Exibir dados extraídos pela IA (JSONB) - REMOVIDA FASE 2
 * Motivo: Campo bugado mostrando [object Object], análise completa já tem tudo
 */
/*
function exibirDadosExtraidosIA(jsonData) {
    const container = document.getElementById('view_ai_extracted_data');
    
    try {
        // Se vier como string, fazer parse
        const dados = typeof jsonData === 'string' ? JSON.parse(jsonData) : jsonData;
        
        if (!dados || Object.keys(dados).length === 0) {
            container.innerHTML = '<p class="text-muted mb-0">Nenhum dado extraído</p>';
            return;
        }
        
        // Criar grid de dados
        let html = '';
        
        for (const [chave, valor] of Object.entries(dados)) {
            if (valor) {
                const chaveFormatada = chave.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                html += `
                    <div class="ai-extracted-item">
                        <div class="ai-extracted-item-label">${chaveFormatada}</div>
                        <div class="ai-extracted-item-value">${valor}</div>
                    </div>
                `;
            }
        }
        
        container.innerHTML = html;
    } catch (error) {
        console.error('Erro ao parsear dados extraídos:', error);
        container.innerHTML = '<p class="text-muted mb-0">Erro ao carregar dados extraídos</p>';
    }
}
*/

// ========================================
// MODO EDIÇÃO (FASE 2 - PREPARAÇÃO)
// ========================================

/**
 * Toggle entre modo visualização e edição
 */
function toggleModoEdicao() {
    const modoAtual = document.getElementById('modoEdicao').value;
    const btnEditar = document.getElementById('btnEditarCandidato');
    const btnSalvar = document.getElementById('btnSalvarEdicao');
    
    if (modoAtual === 'false') {
        // Ativar modo edição
        document.getElementById('modoEdicao').value = 'true';
        document.getElementById('modo-visualizacao').style.display = 'none';
        document.getElementById('modo-edicao').style.display = 'block';
        btnEditar.innerHTML = '<i class="mdi mdi-close"></i> Cancelar';
        btnSalvar.style.display = 'inline-block';
        
        // Construir formulário de edição
        construirFormularioEdicao();
    } else {
        // Voltar para visualização
        document.getElementById('modoEdicao').value = 'false';
        document.getElementById('modo-visualizacao').style.display = 'block';
        document.getElementById('modo-edicao').style.display = 'none';
        btnEditar.innerHTML = '<i class="mdi mdi-pencil"></i> Editar';
        btnSalvar.style.display = 'none';
    }
}

/**
 * Construir formulário de edição (preparação FASE 2)
 */
function construirFormularioEdicao() {
    const form = document.getElementById('formEditarCandidato');
    form.innerHTML = `
        <div class="alert alert-info">
            <i class="mdi mdi-information"></i>
            <strong>Modo Edição</strong> - Em desenvolvimento (FASE 2)
        </div>
        <p class="text-muted">
            Esta funcionalidade será implementada na próxima etapa com todos os campos editáveis.
        </p>
    `;
}

/**
 * Salvar edição do candidato (preparação FASE 2)
 */
async function salvarEdicaoCandidato() {
    alert('⚠️ Funcionalidade de edição em desenvolvimento (FASE 2)');
    // TODO: Coletar dados do formulário e enviar para API
}

/**
 * Efetivar candidato como colaborador - Redireciona para formulário de criação
 */
function efetivarContratacao(candidatoId) {
    console.log('🎯 Efetivando contratação do candidato:', candidatoId);
    window.location.href = `/rh/colaboradores/novo?candidato_id=${candidatoId}`;
}

/**
 * DEPRECATED: Manter por compatibilidade (remover em versão futura)
 */
function efetivarColaborador() {
    const candidatoId = document.getElementById('candidatoIdAtual').value;
    if (candidatoId) {
        efetivarContratacao(candidatoId);
    }
}

/**
 * Adicionar botão de efetivação ao card após mover para "Contratado"
 */
function adicionarBotaoEfetivacao(card, candidatoId) {
    // Verificar se já não tem o botão
    if (card.querySelector('.card-footer')) {
        console.log('⚠️ Card já possui footer, não adicionando botão duplicado');
        return;
    }
    
    console.log('✨ Adicionando botão de efetivação ao card');
    const footer = document.createElement('div');
    footer.className = 'card-footer bg-success text-center p-2 mt-2';
    footer.style.cssText = 'margin: -1rem -1rem -1rem; border-bottom-left-radius: 0.375rem; border-bottom-right-radius: 0.375rem;';
    footer.innerHTML = `
        <button 
            class="btn btn-light btn-sm w-100 fw-bold" 
            onclick="efetivarContratacao('${candidatoId}'); event.stopPropagation();"
            title="Efetivar este candidato como colaborador"
            style="box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <i class="mdi mdi-account-check"></i> Efetivar Contratação
        </button>
    `;
    card.appendChild(footer);
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

/**
 * Exibir análise de IA no modal
 */
function exibirAnaliseIA(candidato) {
    const container = document.getElementById('analiseIAContainer');
    
    // Se não tem dados de IA, ocultar seção
    if (!candidato.ai_status) {
        container.style.display = 'none';
        return;
    }
    
    container.style.display = 'block';
    
    // Status do processamento
    const statusBadge = document.getElementById('aiStatusBadge');
    let badgeClass = 'bg-secondary';
    let statusText = candidato.ai_status || 'Pendente';
    
    if (candidato.ai_status === 'Concluído') {
        badgeClass = 'bg-success';
        statusText = '✓ Processamento Concluído';
    } else if (candidato.ai_status === 'Em Processamento') {
        badgeClass = 'bg-warning text-dark';
        statusText = '⏳ Processando...';
    } else if (candidato.ai_status === 'Erro') {
        badgeClass = 'bg-danger';
        statusText = '⚠ Erro no Processamento';
    } else {
        badgeClass = 'bg-secondary';
        statusText = '⏸ Pendente';
    }
    
    statusBadge.className = `badge ${badgeClass}`;
    statusBadge.textContent = statusText;
    
    // Score de compatibilidade
    const scoreDisplay = document.getElementById('aiScoreDisplay');
    if (candidato.ai_match_score !== null && candidato.ai_match_score !== undefined) {
        scoreDisplay.style.display = 'block';
        
        const scoreValue = document.getElementById('aiScoreValue');
        const scoreBar = document.getElementById('aiScoreBar');
        
        scoreValue.textContent = `${candidato.ai_match_score}%`;
        scoreBar.style.width = `${candidato.ai_match_score}%`;
        
        // Cor da barra baseada no score
        scoreBar.className = 'progress-bar';
        if (candidato.ai_match_score >= 80) {
            scoreBar.classList.add('bg-success');
        } else if (candidato.ai_match_score >= 50) {
            scoreBar.classList.add('bg-warning');
        } else {
            scoreBar.classList.add('bg-danger');
        }
    } else {
        scoreDisplay.style.display = 'none';
    }
    
    // Pré-filtro
    const prefilterDisplay = document.getElementById('aiPrefilterDisplay');
    if (candidato.ai_pre_filter_status) {
        prefilterDisplay.style.display = 'block';
        
        const prefilterValue = document.getElementById('aiPrefilterValue');
        let prefilterBadgeClass = 'bg-secondary';
        
        if (candidato.ai_pre_filter_status === 'Aprovado') {
            prefilterBadgeClass = 'bg-success';
        } else if (candidato.ai_pre_filter_status === 'Reprovado') {
            prefilterBadgeClass = 'bg-danger';
        } else if (candidato.ai_pre_filter_status === 'Revisar') {
            prefilterBadgeClass = 'bg-warning text-dark';
        }
        
        prefilterValue.className = `ms-2 badge ${prefilterBadgeClass}`;
        prefilterValue.textContent = candidato.ai_pre_filter_status;
    } else {
        prefilterDisplay.style.display = 'none';
    }
    
    // Dados extraídos
    const extractedDisplay = document.getElementById('aiExtractedDataDisplay');
    const extractedGrid = document.getElementById('aiExtractedGrid');
    
    if (candidato.ai_extracted_data_jsonb && Object.keys(candidato.ai_extracted_data_jsonb).length > 0) {
        extractedDisplay.style.display = 'block';
        extractedGrid.innerHTML = '';
        
        const data = candidato.ai_extracted_data_jsonb;
        
        // Formação
        if (data.formacao) {
            extractedGrid.innerHTML += `
                <div class="ai-extracted-item">
                    <div class="ai-extracted-item-label">
                        <i class="mdi mdi-school"></i> Formação
                    </div>
                    <div class="ai-extracted-item-value">${data.formacao}</div>
                </div>
            `;
        }
        
        // Anos de experiência
        if (data.anos_experiencia) {
            extractedGrid.innerHTML += `
                <div class="ai-extracted-item">
                    <div class="ai-extracted-item-label">
                        <i class="mdi mdi-briefcase-clock"></i> Experiência
                    </div>
                    <div class="ai-extracted-item-value">${data.anos_experiencia} anos</div>
                </div>
            `;
        }
        
        // Habilidades
        if (data.habilidades && Array.isArray(data.habilidades)) {
            extractedGrid.innerHTML += `
                <div class="ai-extracted-item">
                    <div class="ai-extracted-item-label">
                        <i class="mdi mdi-star-circle"></i> Habilidades
                    </div>
                    <div class="ai-extracted-item-value">
                        <ul>
                            ${data.habilidades.map(h => `<li>${h}</li>`).join('')}
                        </ul>
                    </div>
                </div>
            `;
        }
        
        // Idiomas
        if (data.idiomas && Array.isArray(data.idiomas)) {
            extractedGrid.innerHTML += `
                <div class="ai-extracted-item">
                    <div class="ai-extracted-item-label">
                        <i class="mdi mdi-translate"></i> Idiomas
                    </div>
                    <div class="ai-extracted-item-value">
                        <ul>
                            ${data.idiomas.map(i => `<li>${i}</li>`).join('')}
                        </ul>
                    </div>
                </div>
            `;
        }
        
        // Certificações
        if (data.certificacoes && Array.isArray(data.certificacoes)) {
            extractedGrid.innerHTML += `
                <div class="ai-extracted-item">
                    <div class="ai-extracted-item-label">
                        <i class="mdi mdi-certificate"></i> Certificações
                    </div>
                    <div class="ai-extracted-item-value">
                        <ul>
                            ${data.certificacoes.map(c => `<li>${c}</li>`).join('')}
                        </ul>
                    </div>
                </div>
            `;
        }
        
        // Experiências relevantes
        if (data.experiencias_relevantes && Array.isArray(data.experiencias_relevantes)) {
            let experienciasHTML = '<div class="ai-extracted-item" style="grid-column: 1 / -1;">';
            experienciasHTML += '<div class="ai-extracted-item-label"><i class="mdi mdi-briefcase-outline"></i> Experiências Relevantes</div>';
            experienciasHTML += '<div class="ai-extracted-item-value">';
            
            data.experiencias_relevantes.forEach(exp => {
                if (typeof exp === 'string') {
                    experienciasHTML += `<div class="ai-experiencia-item">${exp}</div>`;
                } else if (typeof exp === 'object') {
                    experienciasHTML += `
                        <div class="ai-experiencia-item">
                            <div class="ai-experiencia-cargo">${exp.cargo || 'Cargo não especificado'}</div>
                            ${exp.empresa ? `<div class="ai-experiencia-empresa">${exp.empresa}</div>` : ''}
                            ${exp.periodo ? `<div class="ai-experiencia-periodo">${exp.periodo}</div>` : ''}
                            ${exp.descricao ? `<div class="mt-2">${exp.descricao}</div>` : ''}
                        </div>
                    `;
                }
            });
            
            experienciasHTML += '</div></div>';
            extractedGrid.innerHTML += experienciasHTML;
        }
        
        // Erro (se houver)
        if (data.erro) {
            extractedGrid.innerHTML = `
                <div class="ai-extracted-item" style="grid-column: 1 / -1; border-left-color: #dc3545;">
                    <div class="ai-extracted-item-label" style="color: #dc3545;">
                        <i class="mdi mdi-alert-circle"></i> Erro
                    </div>
                    <div class="ai-extracted-item-value" style="color: #dc3545;">
                        ${data.erro}
                    </div>
                </div>
            `;
        }
    } else {
        extractedDisplay.style.display = 'none';
    }
}

// Inicializar quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', function() {
    // Se estiver na página de Kanban, inicializar drag-and-drop
    if (document.querySelector('.kanban-container')) {
        initKanbanDragDrop();
    }
});
