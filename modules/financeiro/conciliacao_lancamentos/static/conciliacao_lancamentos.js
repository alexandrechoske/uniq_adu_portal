/**
 * Conciliação Bancária V2 - Sistema de Abas com Estado Local
 * Gerenciamento completo de sessão no frontend
 */

// ========================================
// ESTADO GLOBAL DA APLICAÇÃO
// ========================================
const AppState = {
    // Dados da sessão
    lancamentosSistema: [],      // Todos os lançamentos do sistema (originais)
    lancamentosBanco: [],         // Todos os lançamentos do banco (originais)
    
    // Dados filtrados/pendentes (atualizados dinamicamente)
    sistemasPendentes: [],
    bancosPendentes: [],
    
    // Conciliações realizadas (grupos)
    conciliacoes: [],
    statusResumo: {},
    
    // Seleções atuais
    sistemasSelecionados: new Set(),
    bancosSelecionados: new Set(),
    
    // Controle de UI
    abaAtiva: 'conciliar',
    arquivosCarregados: [],
    ordenacaoSistema: { campo: 'data', ordem: 'desc' },
    ordenacaoBanco: { campo: 'data', ordem: 'desc' },
    buscaSistema: '',
    buscaBanco: '',
    filtroBanco: '',
    empresaSelecionada: 'todas',
    paginacaoSistema: { paginaAtual: 1, itensPorPagina: 100 },
    paginacaoBanco: { paginaAtual: 1, itensPorPagina: 100 }
};

function obterCamposDatasSistema() {
    return {
        inicio: document.getElementById('data_inicio_sistema'),
        fim: document.getElementById('data_fim_sistema')
    };
}

function garantirDatasSistemaPreenchidas() {
    const { inicio, fim } = obterCamposDatasSistema();
    if (!inicio || !fim) {
        return;
    }

    // Período padrão: data inicial = ontem, data final = hoje (2 dias)
    const hoje = new Date();
    const ontem = new Date(hoje);
    ontem.setDate(ontem.getDate() - 1);

    if (!inicio.value) {
        inicio.value = formatarISO(ontem);
    }

    if (!fim.value) {
        fim.value = formatarISO(hoje);
    }

    fim.min = inicio.value || '';
    inicio.max = fim.value || '';
}

function registrarRegrasDatasSistema() {
    const { inicio, fim } = obterCamposDatasSistema();
    if (!inicio || !fim) {
        return;
    }

    inicio.addEventListener('change', () => {
        if (fim.value && inicio.value && inicio.value > fim.value) {
            fim.value = inicio.value;
        }
        fim.min = inicio.value || '';
    });

    fim.addEventListener('change', () => {
        if (inicio.value && fim.value && fim.value < inicio.value) {
            inicio.value = fim.value;
        }
        inicio.max = fim.value || '';
    });
}

function obterPeriodoSistemaSelecionado() {
    const { inicio, fim } = obterCamposDatasSistema();
    const periodoPadrao = calcularPeriodoSistema('mes_atual');

    if (!inicio || !fim) {
        return periodoPadrao;
    }

    let dataInicio = inicio.value;
    let dataFim = fim.value;

    if (!dataInicio) {
        dataInicio = periodoPadrao.inicio;
        inicio.value = dataInicio;
    }

    if (!dataFim) {
        dataFim = periodoPadrao.fim;
        fim.value = dataFim;
    }

    if (new Date(dataInicio) > new Date(dataFim)) {
        throw new Error('A data inicial não pode ser maior que a data final.');
    }

    return {
        inicio: dataInicio,
        fim: dataFim
    };
}

// ========================================
// INICIALIZAÇÃO
// ========================================
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Inicializando Conciliação V2');
    garantirDatasSistemaPreenchidas();
    registrarRegrasDatasSistema();
    inicializarEventos();
    inicializarDragAndDrop();
    inicializarOrdenacao();
    inicializarModalContas(); // Novo: modal de seleção de contas
});

// ========================================
// MODAL DE SELEÇÃO DE CONTAS
// ========================================
let contasDisponiveis = [];
let contasSelecionadas = [];
let infoContasUsuario = {
    carregado: false,
    restrito: false,
    contas: [],
    success: false
};
let promessaContasUsuario = null;

function inicializarModalContas() {
    const modal = document.getElementById('modalSelecionarContas');
    const btnAplicar = document.getElementById('btnAplicarContas');
    const btnSelecionar = document.getElementById('btnSelecionarContas');
    const buscarInput = document.getElementById('buscarConta');
    const selecionarTodas = document.getElementById('selecionarTodasContas');
    
    // Carregar contas quando o modal abrir
    modal.addEventListener('show.bs.modal', carregarContasDisponiveis);
    
    // Aplicar seleção
    btnAplicar.addEventListener('click', aplicarSelecaoContas);
    
    // Busca de contas
    buscarInput.addEventListener('input', filtrarListaContas);
    
    // Selecionar todas
    selecionarTodas.addEventListener('change', toggleSelecionarTodasContas);
}

async function carregarContasDisponiveis() {
    const listaContas = document.getElementById('listaContas');
    const btnAplicar = document.getElementById('btnAplicarContas');
    const selecionarTodas = document.getElementById('selecionarTodasContas');
    
    try {
        console.log('🏦 Carregando contas disponíveis...');

        const infoUsuario = await obterInfoContasUsuario();

        const response = await fetch('/financeiro/conciliacao-lancamentos/api/contas-disponiveis');
        const data = await response.json();
        
        if (data.success) {
            let contasFiltradas = data.contas;

            if (infoUsuario.success && infoUsuario.restrito) {
                contasFiltradas = data.contas.filter(conta => infoUsuario.contas.includes(conta));
                console.log(`🔒 Usuário restrito. Exibindo ${contasFiltradas.length} de ${data.contas.length} contas permitidas.`);
            }

            contasDisponiveis = contasFiltradas;
            contasSelecionadas = contasSelecionadas.filter(conta => contasDisponiveis.includes(conta));
            atualizarBotaoSelecionarContas();
            console.log(`✅ ${contasDisponiveis.length} contas disponíveis para seleção`);
            renderizarListaContas(contasDisponiveis);

            if (contasDisponiveis.length === 0 && infoUsuario.restrito) {
                listaContas.innerHTML = `
                    <div class="alert alert-warning">
                        <i class="mdi mdi-information"></i>
                        Você não possui contas atribuídas. Solicite ao administrador para liberar o acesso.
                    </div>
                `;
                if (btnAplicar) btnAplicar.disabled = true;
                if (selecionarTodas) selecionarTodas.disabled = true;
            } else {
                if (btnAplicar) btnAplicar.disabled = false;
                if (selecionarTodas) selecionarTodas.disabled = false;
            }
        } else {
            throw new Error(data.error || 'Erro ao carregar contas');
        }
        
    } catch (error) {
        console.error('❌ Erro ao carregar contas:', error);
        listaContas.innerHTML = `
            <div class="alert alert-danger">
                <i class="mdi mdi-alert"></i>
                Erro ao carregar contas: ${error.message}
            </div>
        `;
        if (btnAplicar) btnAplicar.disabled = true;
        if (selecionarTodas) selecionarTodas.disabled = true;
    }
}

function renderizarListaContas(contas) {
    const listaContas = document.getElementById('listaContas');
    
    if (contas.length === 0) {
        listaContas.innerHTML = `
            <div class="text-center py-3 text-muted">
                <i class="mdi mdi-information"></i>
                <p>Nenhuma conta encontrada</p>
            </div>
        `;
        return;
    }
    
    listaContas.innerHTML = contas.map(conta => `
        <div class="conta-item">
            <div class="form-check">
                <input class="form-check-input conta-checkbox" type="checkbox" 
                       value="${conta}" id="conta-${conta.replace(/[^a-zA-Z0-9]/g, '')}"
                       ${contasSelecionadas.includes(conta) ? 'checked' : ''}>
                <label class="form-check-label" for="conta-${conta.replace(/[^a-zA-Z0-9]/g, '')}">
                    <span class="conta-badge">${conta}</span>
                </label>
            </div>
        </div>
    `).join('');
    
    // Adicionar event listeners
    document.querySelectorAll('.conta-checkbox').forEach(checkbox => {
        checkbox.addEventListener('change', atualizarContadorContas);
    });
    
    atualizarContadorContas();
}

function filtrarListaContas() {
    const busca = document.getElementById('buscarConta').value.toLowerCase();
    const contasFiltradas = contasDisponiveis.filter(conta => 
        conta.toLowerCase().includes(busca)
    );
    renderizarListaContas(contasFiltradas);
}

function toggleSelecionarTodasContas(e) {
    const checkboxes = document.querySelectorAll('.conta-checkbox');
    checkboxes.forEach(cb => {
        cb.checked = e.target.checked;
    });
    atualizarContadorContas();
}

function atualizarContadorContas() {
    const checkboxes = document.querySelectorAll('.conta-checkbox:checked');
    const contador = document.getElementById('contadorContasSelecionadas');
    contador.textContent = checkboxes.length;
    
    // Atualizar checkbox "Selecionar Todas"
    const selecionarTodas = document.getElementById('selecionarTodasContas');
    const totalCheckboxes = document.querySelectorAll('.conta-checkbox').length;
    selecionarTodas.checked = checkboxes.length === totalCheckboxes && totalCheckboxes > 0;
}

function aplicarSelecaoContas() {
    const checkboxes = document.querySelectorAll('.conta-checkbox:checked');
    contasSelecionadas = Array.from(checkboxes).map(cb => cb.value);
    
    atualizarBotaoSelecionarContas();
    
    console.log('✅ Contas selecionadas:', contasSelecionadas);
    
    // Fechar modal
    const modal = bootstrap.Modal.getInstance(document.getElementById('modalSelecionarContas'));
    modal.hide();
}

function atualizarBotaoSelecionarContas() {
    const btnSelecionar = document.getElementById('btnSelecionarContas');
    if (btnSelecionar) {
        btnSelecionar.innerHTML = `
            <i class="mdi mdi-bank"></i> Selecionar Contas (${contasSelecionadas.length})
        `;
    }
}

function inicializarEventos() {
    // Navegação de abas
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => trocarAba(btn.dataset.tab));
    });
    
    // Upload de arquivos
    document.getElementById('arquivoBancario').addEventListener('change', handleFileSelect);
    document.getElementById('uploadForm').addEventListener('submit', processarArquivos);
    
    // Busca e filtros
    document.getElementById('searchSistema').addEventListener('input', filtrarTabelaSistema);
    document.getElementById('searchBanco').addEventListener('input', filtrarTabelaBanco);
    document.getElementById('filtroBanco').addEventListener('change', filtrarTabelaBanco);
    
    // Checkboxes
    document.getElementById('checkAllSistema').addEventListener('change', toggleSelectAllSistema);
    document.getElementById('checkAllBanco').addEventListener('change', toggleSelectAllBanco);
    
    // Conciliação manual
    document.getElementById('btnConciliarManual').addEventListener('click', conciliarManual);
    document.getElementById('btnOcultarTransacoes').addEventListener('click', ocultarTransacoes);
    
    // Exportar relatório (botão no topo da página)
    const btnExportar = document.getElementById('btnExportarRelatorio');
    if (btnExportar) {
        btnExportar.addEventListener('click', exportarRelatorio);
    }
    
    // Gestão de Usuários e Contas (apenas para admins)
    const btnGestaoUsuarios = document.getElementById('btnGestaoUsuarios');
    if (btnGestaoUsuarios) {
        btnGestaoUsuarios.addEventListener('click', abrirModalGestaoUsuarios);
    }
    
    // Filtros da aba Conciliados
    document.getElementById('filtroTipoConciliacao').addEventListener('change', filtrarConciliados);
    document.getElementById('filtroBancoConciliados').addEventListener('change', filtrarConciliados);
    document.getElementById('searchConciliados').addEventListener('input', filtrarConciliados);
    
    // Limpar sessão
    document.getElementById('btnLimparSessao').addEventListener('click', limparSessao);
    
    // Carregar contas atribuídas ao usuário (se for analista)
    carregarContasAtribuidas();
}

// ========================================
// EXIBIR CONTAS ATRIBUÍDAS DO USUÁRIO
// ========================================
async function obterInfoContasUsuario(forceRefresh = false) {
    if (infoContasUsuario.carregado && !forceRefresh) {
        return infoContasUsuario;
    }

    if (promessaContasUsuario && !forceRefresh) {
        return promessaContasUsuario;
    }

    promessaContasUsuario = (async () => {
        try {
            console.log('🔍 Verificando contas atribuídas ao usuário...');
            const response = await fetch('/financeiro/conciliacao-lancamentos/api/minhas-contas');
            const data = await response.json();
            console.log('📡 Resposta /api/minhas-contas:', data);

            infoContasUsuario = {
                carregado: true,
                restrito: Boolean(data.restrito),
                contas: Array.isArray(data.contas) ? data.contas : [],
                success: data.success !== false
            };

            return infoContasUsuario;
        } catch (error) {
            console.error('❌ Erro ao consultar contas atribuídas:', error);
            infoContasUsuario = {
                carregado: true,
                restrito: false,
                contas: [],
                success: false,
                error
            };
            throw error;
        } finally {
            promessaContasUsuario = null;
        }
    })();

    return promessaContasUsuario;
}

async function carregarContasAtribuidas() {
    try {
        const dados = await obterInfoContasUsuario();

        const containerInfo = document.getElementById('contasAtribuidasInfo');
        const listaContas = document.getElementById('contasAtribuidasLista');

        if (!dados.success) {
            console.warn('⚠️ Não foi possível obter contas atribuídas do usuário');
            if (containerInfo) {
                containerInfo.style.display = 'none';
            }
            return;
        }

        if (dados.restrito && dados.contas.length > 0) {
            if (listaContas) {
                listaContas.innerHTML = dados.contas.map(conta => `
                    <span class="conta-chip">
                        <i class="mdi mdi-bank"></i>
                        ${conta}
                    </span>
                `).join('');
            }
            if (containerInfo) {
                containerInfo.style.display = 'flex';
            }
            console.log(`✅ Exibindo ${dados.contas.length} conta(s) atribuída(s):`, dados.contas);
        } else if (dados.restrito && dados.contas.length === 0) {
            console.warn('⚠️ Usuário é analista mas não tem contas atribuídas');
            if (listaContas) {
                listaContas.innerHTML = `
                    <span class="text-muted small">Nenhuma conta atribuída. Contate um administrador.</span>
                `;
            }
            if (containerInfo) {
                containerInfo.style.display = 'flex';
            }
        } else {
            console.log('ℹ️ Usuário sem restrições de conta (não é analista ou possui acesso total)');
            if (containerInfo) {
                containerInfo.style.display = 'none';
            }
        }
    } catch (error) {
        console.error('❌ Erro ao carregar contas atribuídas:', error);
        const containerInfo = document.getElementById('contasAtribuidasInfo');
        if (containerInfo) {
            containerInfo.style.display = 'none';
        }
    }
}

// ========================================
// DRAG AND DROP
// ========================================
function inicializarDragAndDrop() {
    const zone = document.getElementById('uploadZone');
    const btnSelect = document.getElementById('btnSelecionarArquivos');
    
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        zone.addEventListener(eventName, preventDefaults, false);
    });
    
    ['dragenter', 'dragover'].forEach(eventName => {
        zone.addEventListener(eventName, () => zone.classList.add('drag-over'), false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        zone.addEventListener(eventName, () => zone.classList.remove('drag-over'), false);
    });
    
    zone.addEventListener('drop', handleDrop, false);
    zone.addEventListener('click', () => document.getElementById('arquivoBancario').click());

    if (btnSelect) {
        btnSelect.addEventListener('click', (event) => {
            event.preventDefault();
            event.stopPropagation();
            document.getElementById('arquivoBancario').click();
        });
    }
}

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

function handleDrop(e) {
    const dt = e.dataTransfer;
    const files = dt.files;
    document.getElementById('arquivoBancario').files = files;
    handleFileSelect({ target: { files } });
}

function handleFileSelect(e) {
    const files = Array.from(e.target.files);
    AppState.arquivosCarregados = files;
    
    if (files.length > 0) {
        exibirArquivosSelecionados(files);
        document.getElementById('btnProcessar').disabled = false;
    }
}

function exibirArquivosSelecionados(files) {
    const filesList = document.getElementById('filesList');
    const placeholder = document.querySelector('.upload-placeholder');
    
    placeholder.style.display = 'none';
    filesList.style.display = 'block';
    filesList.innerHTML = files.map(f => `
        <div class="file-item">
            <i class="mdi mdi-file-document"></i>
            <span class="file-name">${f.name}</span>
            <span class="file-size">${formatBytes(f.size)}</span>
        </div>
    `).join('');
}

function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

// ========================================
// PROCESSAMENTO E UPLOAD
// ========================================
async function processarArquivos(e) {
    e.preventDefault();
    
    if (AppState.arquivosCarregados.length === 0) {
        mostrarNotificacao('Selecione ao menos um arquivo bancário antes de processar.', 'info');
        return;
    }

    prepararNovaSessaoProcessamento();

    let periodo;
    try {
        periodo = obterPeriodoSistemaSelecionado();
    } catch (erroPeriodo) {
        console.warn('[CONCILIACAO] Período inválido:', erroPeriodo);
        mostrarNotificacao(erroPeriodo.message || 'Informe um período válido para os lançamentos do sistema.', 'warning');
        return;
    }

    // Verificar se usuário é analista e aplicar filtro de contas
    try {
        const minhasContasResp = await fetch('/financeiro/conciliacao-lancamentos/api/minhas-contas');
        const minhasContasData = await minhasContasResp.json();
        
        if (minhasContasData.success && minhasContasData.restrito) {
            // Usuário é analista - filtrar contas permitidas
            const contasPermitidas = minhasContasData.contas || [];
            
            if (contasPermitidas.length === 0) {
                mostrarNotificacao('⚠️ Você não tem contas atribuídas. Contate o administrador.', 'warning');
                return;
            }
            
            // Filtrar apenas contas que o usuário tem permissão
            const contasValidas = contasSelecionadas.filter(c => contasPermitidas.includes(c));
            
            if (contasValidas.length === 0) {
                mostrarNotificacao(`⚠️ Você não tem permissão para acessar as contas selecionadas. Contas permitidas: ${contasPermitidas.join(', ')}`, 'warning');
                return;
            }
            
            if (contasValidas.length < contasSelecionadas.length) {
                console.log(`🔒 Filtro aplicado: ${contasSelecionadas.length} → ${contasValidas.length} contas`);
                contasSelecionadas = contasValidas;
                mostrarNotificacao(`🔒 Processando apenas contas permitidas: ${contasValidas.join(', ')}`, 'info');
            }
        }
    } catch (error) {
        console.warn('[PERFIL] Erro ao verificar permissões de contas:', error);
        // Continuar normalmente se houver erro na verificação
    }

    // Validar se há contas selecionadas (após filtro)
    if (!contasSelecionadas || contasSelecionadas.length === 0) {
        mostrarNotificacao('Selecione ao menos uma conta bancária para processar.', 'warning');
        return;
    }

    const formData = new FormData();
    AppState.arquivosCarregados.forEach(file => {
        formData.append('arquivo_bancario', file);
    });
    
    // Adicionar contas selecionadas
    contasSelecionadas.forEach(conta => {
        formData.append('contas_selecionadas', conta);
    });
    
    formData.append('data_inicio_sistema', periodo.inicio);
    formData.append('data_fim_sistema', periodo.fim);
    
    try {
        mostrarLoading('Carregando lançamentos do sistema...');

        const params = new URLSearchParams({
            data_inicio: periodo.inicio,
            data_fim: periodo.fim
        });

        // Adicionar contas selecionadas aos parâmetros
        contasSelecionadas.forEach(conta => {
            params.append('contas', conta);
        });

        const sistemaResp = await fetch(`/financeiro/conciliacao-lancamentos/api/movimentos-sistema?${params.toString()}`);
        const sistemaData = await sistemaResp.json();

        if (!sistemaResp.ok || !sistemaData.success) {
            throw new Error(sistemaData.error || 'Erro ao carregar lançamentos do sistema');
        }

        const dadosSistema = Array.isArray(sistemaData.data) ? sistemaData.data : [];
        const dadosSistemaNormalizados = dadosSistema
            .map(normalizarMovimentoSistema)
            .filter(Boolean);

        if (dadosSistemaNormalizados.length === 0) {
            mostrarNotificacao('Nenhum lançamento do sistema encontrado para o período selecionado.', 'info');
            esconderLoading();
            return;
        }

        AppState.lancamentosSistema = dadosSistemaNormalizados;
        AppState.sistemasPendentes = [...AppState.lancamentosSistema];

        mostrarLoading('Enviando arquivos bancários...');
        
        // 1. Upload dos arquivos
        const uploadResp = await fetch('/financeiro/conciliacao-lancamentos/upload-arquivo', {
            method: 'POST',
            body: formData
        });
        
        if (!uploadResp.ok) throw new Error('Erro no upload');
        const uploadData = await uploadResp.json();
        if (uploadData && uploadData.success === false) {
            throw new Error(uploadData.error || uploadData.message || 'Erro no upload');
        }
        if (uploadData && uploadData.data && Array.isArray(uploadData.data.lancamentos)) {
            const dadosBancoNormalizados = uploadData.data.lancamentos
                .map(normalizarMovimentoBanco)
                .filter(Boolean);
            AppState.lancamentosBanco = dadosBancoNormalizados;
            AppState.bancosPendentes = [...dadosBancoNormalizados];
        }
        
        mostrarLoading('Processando conciliação automática...');
        
        // Iniciar polling de progresso
        const intervalId = setInterval(async () => {
            try {
                const progressoResp = await fetch('/financeiro/conciliacao-lancamentos/api/progresso-conciliacao');
                if (progressoResp.ok) {
                    const progresso = await progressoResp.json();
                    if (progresso.em_andamento) {
                        const mensagem = `${progresso.mensagem}<br><div class="progress mt-2"><div class="progress-bar progress-bar-striped progress-bar-animated" role="progressbar" style="width: ${progresso.percentual}%">${progresso.percentual}%</div></div>`;
                        mostrarLoading(mensagem);
                    }
                }
            } catch (err) {
                console.error('Erro ao consultar progresso:', err);
            }
        }, 500); // Atualizar a cada 500ms
        
        // 2. Conciliação automática
        const conciliarResp = await fetch('/financeiro/conciliacao-lancamentos/api/processar-conciliacao', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json'
            }
        });
        
        // Parar polling
        clearInterval(intervalId);
        
        if (!conciliarResp.ok) throw new Error('Erro na conciliação');
        const conciliarData = await conciliarResp.json();
        if (!conciliarData.success) {
            throw new Error(conciliarData.error || 'Erro na conciliação');
        }
        
        // 3. Processar resultados
        processarResultados(conciliarData.data);
        
        mostrarNotificacao('✅ Processamento concluído com sucesso!', 'success');
        
    } catch (error) {
        console.error('Erro:', error);
        mostrarNotificacao('❌ Erro ao processar: ' + error.message, 'error');
    } finally {
        esconderLoading();
    }
}

function processarResultados(responseData) {
    if (!responseData) {
        mostrarNotificacao('Retorno de conciliação inválido.', 'error');
        return;
    }

    const payload = responseData.data ? responseData.data : responseData;
    console.log('📊 Processando resultados:', payload);

    const dadosSistemaBrutos = payload.dados_aberta || payload.lancamentos_sistema || [];
    const dadosBancoBrutos = payload.dados_banco || payload.lancamentos_banco || [];
    const resumoStatus = payload.status || {};

    const dadosSistema = dadosSistemaBrutos.map(normalizarMovimentoSistema).filter(Boolean);
    const dadosBanco = dadosBancoBrutos.map(normalizarMovimentoBanco).filter(Boolean);

    AppState.lancamentosSistema = dadosSistema;
    AppState.lancamentosBanco = dadosBanco;
    AppState.statusResumo = resumoStatus;
    AppState.conciliacoes = gerarConciliacoesAutomaticas(dadosSistema, dadosBanco);

    // Reaplicar estado inicial de filtros/ordenadores
    AppState.buscaSistema = '';
    AppState.buscaBanco = '';
    AppState.filtroBanco = '';
    AppState.ordenacaoSistema = { campo: 'data', ordem: 'desc' };
    AppState.ordenacaoBanco = { campo: 'data', ordem: 'desc' };
    AppState.paginacaoSistema.paginaAtual = 1;
    AppState.paginacaoBanco.paginaAtual = 1;

    const searchSistema = document.getElementById('searchSistema');
    const searchBanco = document.getElementById('searchBanco');
    const filtroBancoSelect = document.getElementById('filtroBanco');
    if (searchSistema) searchSistema.value = '';
    if (searchBanco) searchBanco.value = '';
    if (filtroBancoSelect) filtroBancoSelect.value = '';

    // Calcular pendentes (remover conciliados automáticos)
    calcularPendentes();

    // Atualizar UI
    atualizarKPIs();
    renderizarTabelaSistema();
    renderizarTabelaBanco();
    renderizarTabelaConciliados();

    // Exibir seções
    document.getElementById('kpisSection').style.display = 'block';
    document.getElementById('workspace').style.display = 'block';
    document.getElementById('btnLimparSessao').style.display = 'inline-block';
    document.getElementById('btnExportarRelatorio').style.display = 'inline-block';

    // Esconder upload
    document.querySelector('.upload-section').style.display = 'none';
}

function calcularPendentes() {
    const idsConcilidosSistema = new Set();
    const idsConcilidosBanco = new Set();
    
    AppState.conciliacoes.forEach(grupo => {
        grupo.sistema.forEach(item => idsConcilidosSistema.add(item.id));
        grupo.banco.forEach(item => idsConcilidosBanco.add(item.id));
    });
    
    AppState.sistemasPendentes = AppState.lancamentosSistema.filter(
        item => !idsConcilidosSistema.has(item.id)
    );
    
    AppState.bancosPendentes = AppState.lancamentosBanco.filter(
        item => !idsConcilidosBanco.has(item.id)
    );
}

// ========================================
// RENDERIZAÇÃO DAS TABELAS
// ========================================
function renderizarTabelaSistema() {
    const tbody = document.getElementById('tableSistema');
    if (!tbody) return;

    const termoBusca = (AppState.buscaSistema || '').trim().toLowerCase();
    const itensFiltrados = AppState.sistemasPendentes.filter(item => {
        if (!termoBusca) return true;
        const textoComparacao = [
            item.descricao,
            item.descricao_original,
            item.ref_unique,
            item.ref_unique_norm,
            item.empresa,
            formatarMoeda(item.valor),
            formatarData(item.data)
        ].join(' ').toLowerCase();
        return textoComparacao.includes(termoBusca);
    });

    const itensOrdenados = obterItensOrdenados(itensFiltrados, AppState.ordenacaoSistema);
    const paginacao = AppState.paginacaoSistema;
    const itensPorPagina = paginacao.itensPorPagina || 100;
    const totalItens = itensOrdenados.length;
    const totalPaginas = totalItens > 0 ? Math.ceil(totalItens / itensPorPagina) : 0;
    const paginaAjustada = totalPaginas === 0 ? 1 : Math.min(Math.max(paginacao.paginaAtual || 1, 1), totalPaginas);
    paginacao.paginaAtual = paginaAjustada;

    if (totalItens === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-3">Nenhum lançamento pendente</td></tr>';
        document.getElementById('countSistema').textContent = '0';
        document.getElementById('totalSistema').textContent = 'R$ 0,00';
        const checkAll = document.getElementById('checkAllSistema');
        if (checkAll) checkAll.checked = false;
        AppState.paginacaoSistema.paginaAtual = 1;
        atualizarPaginacao('sistema', 0, 1);
        atualizarIndicadoresOrdenacao();
        return;
    }

    const startIndex = (paginaAjustada - 1) * itensPorPagina;
    const itensPagina = itensOrdenados.slice(startIndex, startIndex + itensPorPagina);

    tbody.innerHTML = itensPagina.map(item => {
        const checked = AppState.sistemasSelecionados.has(item.id) ? 'checked' : '';
        const descricao = item.descricao || '-';
        const descricaoDisplay = escapeHtml(descricao);
    const empresaDisplay = escapeHtml(item.empresa || 'Sem empresa cadastrada');
        return `
        <tr>
            <td><input type="checkbox" class="check-sistema" data-id="${item.id}" ${checked}></td>
            <td>${formatarData(item.data)}</td>
            <td style="max-width: 240px;">
                <div class="d-flex flex-column">
                    <span class="text-truncate" title="${descricaoDisplay}">${descricaoDisplay}</span>
                    <small class="text-muted">${empresaDisplay}</small>
                </div>
            </td>
            <td><span class="badge bg-info">${escapeHtml(item.ref_unique || '-')}</span></td>
            <td class="text-end"><strong>${formatarMoeda(item.valor)}</strong></td>
        </tr>`;
    }).join('');

    tbody.querySelectorAll('.check-sistema').forEach(chk => {
        chk.addEventListener('change', handleSelecaoSistema);
    });

    const total = itensFiltrados.reduce((sum, item) => sum + parseFloat(item.valor || 0), 0);
    document.getElementById('countSistema').textContent = itensFiltrados.length;
    document.getElementById('totalSistema').textContent = formatarMoeda(total);

    const checkAll = document.getElementById('checkAllSistema');
    if (checkAll) {
        const todosSelecionados = itensPagina.length > 0 && itensPagina.every(item => AppState.sistemasSelecionados.has(item.id));
        checkAll.checked = todosSelecionados;
    }

    atualizarPaginacao('sistema', totalPaginas, paginaAjustada);
    atualizarIndicadoresOrdenacao();
}

function renderizarTabelaBanco() {
    const tbody = document.getElementById('tableBanco');
    if (!tbody) return;

    const totalItensArray = AppState.bancosPendentes.length;
    const itensOcultos = AppState.bancosPendentes.filter(item => item.oculto === true).length;
    const itensVisiveis = totalItensArray - itensOcultos;
    
    console.log('🎨 renderizarTabelaBanco: Total:', totalItensArray, '| Ocultos:', itensOcultos, '| Visíveis:', itensVisiveis);

    const filtroAtual = AppState.filtroBanco || '';
    const termoBusca = (AppState.buscaBanco || '').trim().toLowerCase();

    const itensFiltrados = AppState.bancosPendentes.filter(item => {
        // Filtrar itens ocultos
        if (item.oculto === true) return false;
        
        if (filtroAtual && item.banco !== filtroAtual) return false;
        if (!termoBusca) return true;
        const textoComparacao = [
            item.descricao,
            item.codigo_referencia,
            item.ref_unique,
            item.ref_unique_norm,
            item.banco,
            formatarMoeda(item.valor),
            formatarData(item.data)
        ].join(' ').toLowerCase();
        return textoComparacao.includes(termoBusca);
    });

    const itensOrdenados = obterItensOrdenados(itensFiltrados, AppState.ordenacaoBanco);
    const paginacao = AppState.paginacaoBanco;
    const itensPorPagina = paginacao.itensPorPagina || 100;
    const totalItens = itensOrdenados.length;
    const totalPaginas = totalItens > 0 ? Math.ceil(totalItens / itensPorPagina) : 0;
    const paginaAjustada = totalPaginas === 0 ? 1 : Math.min(Math.max(paginacao.paginaAtual || 1, 1), totalPaginas);
    paginacao.paginaAtual = paginaAjustada;

    if (totalItens === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted py-3">Nenhum lançamento pendente</td></tr>';
        document.getElementById('countBanco').textContent = '0';
        document.getElementById('totalBanco').textContent = 'R$ 0,00';
        const checkAll = document.getElementById('checkAllBanco');
        if (checkAll) checkAll.checked = false;
        AppState.paginacaoBanco.paginaAtual = 1;
        atualizarPaginacao('banco', 0, 1);
        atualizarIndicadoresOrdenacao();
        return;
    }

    const startIndex = (paginaAjustada - 1) * itensPorPagina;
    const itensPagina = itensOrdenados.slice(startIndex, startIndex + itensPorPagina);

    tbody.innerHTML = itensPagina.map(item => {
        const checked = AppState.bancosSelecionados.has(item.id) ? 'checked' : '';
        const descricao = item.descricao || item.historico || '-';
        return `
        <tr>
            <td><input type="checkbox" class="check-banco" data-id="${item.id}" ${checked}></td>
            <td>${formatarData(item.data)}</td>
            <td class="text-truncate" style="max-width: 180px;" title="${descricao}">${descricao}</td>
            <td><span class="badge bg-info">${item.ref_unique || '-'}</span></td>
            <td><span class="badge bg-secondary">${formatarBanco(item.banco)}</span></td>
            <td class="text-end"><strong>${formatarMoeda(item.valor)}</strong></td>
        </tr>`;
    }).join('');

    tbody.querySelectorAll('.check-banco').forEach(chk => {
        chk.addEventListener('change', handleSelecaoBanco);
    });

    const total = itensFiltrados.reduce((sum, item) => sum + parseFloat(item.valor || 0), 0);
    document.getElementById('countBanco').textContent = itensFiltrados.length;
    document.getElementById('totalBanco').textContent = formatarMoeda(total);

    const checkAll = document.getElementById('checkAllBanco');
    if (checkAll) {
        const todosSelecionados = itensPagina.length > 0 && itensPagina.every(item => AppState.bancosSelecionados.has(item.id));
        checkAll.checked = todosSelecionados;
    }

    atualizarPaginacao('banco', totalPaginas, paginaAjustada);
    atualizarIndicadoresOrdenacao();
}

// ========================================
// PAGINAÇÃO DAS TABELAS
// ========================================
function atualizarPaginacao(tabela, totalPaginas, paginaAtual) {
    const containerId = tabela === 'sistema' ? 'paginationSistema' : 'paginationBanco';
    const container = document.getElementById(containerId);
    if (!container) return;

    if (!totalPaginas || totalPaginas <= 1) {
        container.innerHTML = '';
        return;
    }

    const anteriorDisabled = paginaAtual <= 1 ? 'disabled' : '';
    const proximaDisabled = paginaAtual >= totalPaginas ? 'disabled' : '';

    container.innerHTML = `
        <button type="button" class="page-btn" data-page="${paginaAtual - 1}" ${anteriorDisabled}>Anterior</button>
        <span class="pagination-info">Página ${paginaAtual} de ${totalPaginas}</span>
        <button type="button" class="page-btn" data-page="${paginaAtual + 1}" ${proximaDisabled}>Próxima</button>
    `;

    container.querySelectorAll('button[data-page]').forEach(btn => {
        if (btn.disabled) return;
        btn.addEventListener('click', () => alterarPagina(tabela, Number(btn.dataset.page)));
    });
}

function alterarPagina(tabela, novaPagina) {
    if (!Number.isFinite(novaPagina) || novaPagina < 1) {
        return;
    }

    if (tabela === 'sistema') {
        if (AppState.paginacaoSistema.paginaAtual === novaPagina) return;
        AppState.paginacaoSistema.paginaAtual = novaPagina;
        renderizarTabelaSistema();
    } else if (tabela === 'banco') {
        if (AppState.paginacaoBanco.paginaAtual === novaPagina) return;
        AppState.paginacaoBanco.paginaAtual = novaPagina;
        renderizarTabelaBanco();
    }
}

function gerarDetalhesConciliados(itens, origem) {
    if (!Array.isArray(itens) || itens.length === 0) {
        return '<div class="conciliado-detalhes-vazio">Nenhum lançamento</div>';
    }

    const header = `<div class="conciliado-detalhes-header">${itens.length} lançamento(s)</div>`;
    const registros = itens.map(item => {
        const descricaoBase = item.descricao || item.descricao_original || item.historico || '-';
        const referenciaBase = item.ref_unique || item.codigo_referencia || '';
        const referenciaTratada = referenciaBase ? escapeHtml(referenciaBase) : '-';
        const metaBanco = origem === 'banco' && item.banco
            ? `<span>Banco: ${escapeHtml(formatarBanco(item.banco))}</span>`
            : '';

        return `
            <div class="conciliado-item">
                <div class="conciliado-item-header">
                    <span>${formatarData(item.data)}</span>
                    <span class="conciliado-item-valor">${formatarMoeda(item.valor)}</span>
                </div>
                <div class="conciliado-item-descricao">${escapeHtml(descricaoBase)}</div>
                <div class="conciliado-item-meta">
                    <span>Ref.: ${referenciaTratada || '-'}</span>
                    ${metaBanco}
                </div>
            </div>
        `;
    }).join('');

    return `<div class="conciliado-detalhes">${header}${registros}</div>`;
}

function renderizarTabelaConciliados() {
    const tbody = document.getElementById('tableConciliados');
    if (!tbody) return;

    const items = AppState.conciliacoes;

    if (items.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center text-muted py-5">
                    <i class="mdi mdi-checkbox-blank-circle-outline" style="font-size: 3rem;"></i>
                    <p class="mt-2">Nenhuma conciliação realizada ainda</p>
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = items.map(grupo => {
        const tipoIcon = grupo.tipo === 'manual' ? 'hand-pointing-right' : 'robot';
        const tipoLabel = grupo.tipo === 'manual' ? 'Manual' :
            grupo.tipo === 'auto_ref' ? 'Auto-Ref' : 'Auto-Valor';
        const tipoClass = grupo.tipo === 'manual' ? 'bg-primary' : 'bg-success';

        const detalhesSistema = gerarDetalhesConciliados(grupo.sistema, 'sistema');
        const detalhesBanco = gerarDetalhesConciliados(grupo.banco, 'banco');
        const bancosGrupo = Array.isArray(grupo.banco)
            ? Array.from(new Set(grupo.banco
                .map(item => item && (item.banco || item.banco_origem || ''))
                .filter(Boolean)))
            : [];
        const bancosDataAttr = bancosGrupo.join(',');

        return `
            <tr data-tipo="${grupo.tipo}" data-bancos="${bancosDataAttr}">
                <td>
                    <span class="badge ${tipoClass}">
                        <i class="mdi mdi-${tipoIcon}"></i> ${tipoLabel}
                    </span>
                </td>
                <td>${formatarData(grupo.data)}</td>
                <td class="text-end"><strong>${formatarMoeda(grupo.valorTotal)}</strong></td>
                <td>${detalhesSistema}</td>
                <td>${detalhesBanco}</td>
                <td class="text-center">
                    ${grupo.tipo === 'manual'
                        ? `<button class="btn btn-sm btn-outline-danger" onclick="desfazerConciliacao('${grupo.id}')">
                                <i class="mdi mdi-undo"></i>
                           </button>`
                        : '<i class="mdi mdi-lock text-muted"></i>'}
                </td>
            </tr>
        `;
    }).join('');

    filtrarConciliados();
}

// ========================================
// SELEÇÃO E CONCILIAÇÃO MANUAL
// ========================================
function handleSelecaoSistema(e) {
    const id = e.target.dataset.id;
    if (e.target.checked) {
        AppState.sistemasSelecionados.add(id);
    } else {
        AppState.sistemasSelecionados.delete(id);
    }
    atualizarTotaisSelecionados();
}

function handleSelecaoBanco(e) {
    const id = e.target.dataset.id;
    if (e.target.checked) {
        AppState.bancosSelecionados.add(id);
    } else {
        AppState.bancosSelecionados.delete(id);
    }
    atualizarTotaisSelecionados();
}

function toggleSelectAllSistema(e) {
    const checkboxes = document.querySelectorAll('.check-sistema');
    checkboxes.forEach(chk => {
        chk.checked = e.target.checked;
        handleSelecaoSistema({ target: chk });
    });
}

function toggleSelectAllBanco(e) {
    const checkboxes = document.querySelectorAll('.check-banco');
    checkboxes.forEach(chk => {
        chk.checked = e.target.checked;
        handleSelecaoBanco({ target: chk });
    });
}

function atualizarTotaisSelecionados() {
    const totalSistema = calcularTotalSelecionados(AppState.sistemasPendentes, AppState.sistemasSelecionados);
    const totalBanco = calcularTotalSelecionados(AppState.bancosPendentes, AppState.bancosSelecionados);
    
    document.getElementById('totalSelSistema').textContent = formatarMoeda(totalSistema);
    document.getElementById('totalSelBanco').textContent = formatarMoeda(totalBanco);
    
    // Habilitar botão Conciliar se houver seleções em ambas as tabelas
    const btnConciliar = document.getElementById('btnConciliarManual');
    btnConciliar.disabled = AppState.sistemasSelecionados.size === 0 || AppState.bancosSelecionados.size === 0;
    
    // Habilitar botão Ocultar se houver seleções apenas na tabela de banco
    const btnOcultar = document.getElementById('btnOcultarTransacoes');
    btnOcultar.disabled = AppState.bancosSelecionados.size === 0;
}

function calcularTotalSelecionados(items, idsSet) {
    return items
        .filter(item => idsSet.has(item.id))
        .reduce((sum, item) => sum + parseFloat(item.valor || 0), 0);
}

// ========================================
// OCULTAR TRANSAÇÕES BANCO
// ========================================
function ocultarTransacoes() {
    // Validar seleção
    if (AppState.bancosSelecionados.size === 0) {
        mostrarNotificacao('Selecione pelo menos uma transação de banco para ocultar.', 'warning');
        return;
    }
    
    console.log('🔍 Ocultando transações...');
    
    // Pegar IDs das transações selecionadas
    const idsOcultar = Array.from(AppState.bancosSelecionados);
    
    // Marcar transações como ocultas (não remove do array)
    AppState.bancosPendentes.forEach(item => {
        if (idsOcultar.includes(item.id)) {
            item.oculto = true;
        }
    });
    
    console.log('✅ Marcadas como ocultas:', idsOcultar.length);
    
    // Limpar seleções
    AppState.bancosSelecionados.clear();
    
    // Resetar paginação para página 1
    AppState.paginacaoBanco.paginaAtual = 1;
    
    // Atualizar UI - forçar re-render completo
    atualizarKPIs();
    atualizarTotaisSelecionados();
    renderizarTabelaBanco();
    
    console.log('🎯 Renderização completa');
    
    mostrarNotificacao(`✅ ${idsOcultar.length} transação(ões) ocultada(s)`, 'success');
}

/**
 * Exporta relatório de conciliação em Excel com 2 abas (Sistema e Banco)
 */
async function exportarRelatorio() {
    try {
        console.log('📊 Iniciando exportação de relatório...');
        
        // Coletar dados do sistema (todos não conciliados + conciliados da aba)
        const dadosSistema = [];
        
        // Adicionar pendentes do sistema (visíveis após filtros)
        AppState.sistemasPendentes.forEach(item => {
            dadosSistema.push({
                data_movimento: item.data_lancamento || item.data || '',
                descricao: item.descricao || '',
                valor: item.valor || 0,
                tipo_movimento: item.tipo_lancamento || '',
                categoria: item.ref_unique || '',
                origem: item.empresa || '',
                conciliado: false
            });
        });
        
        // Coletar dados do banco (excluindo ocultos)
        const dadosBanco = [];
        
        // Adicionar pendentes do banco (visíveis após filtros, excluindo ocultos)
        AppState.bancosPendentes.forEach(item => {
            if (item.oculto !== true) { // Excluir ocultos
                dadosBanco.push({
                    data_lancamento: item.data_lancamento,
                    nome_banco: item.banco,
                    numero_conta: item.conta,
                    descricao: item.descricao,
                    valor: item.valor,
                    conciliado: false
                });
            }
        });
        
        // Adicionar conciliados se estivermos na aba de conciliados
        if (AppState.abaAtual === 'conciliados') {
            AppState.conciliados.forEach(item => {
                // Adicionar ao sistema
                if (item.id_sistema) {
                    dadosSistema.push({
                        data_movimento: item.data_sistema,
                        descricao: item.descricao_sistema,
                        valor: item.valor,
                        tipo_movimento: item.tipo_movimento,
                        categoria: item.categoria,
                        origem: item.origem,
                        conciliado: true
                    });
                }
                
                // Adicionar ao banco
                if (item.id_banco) {
                    dadosBanco.push({
                        data_lancamento: item.data_banco,
                        nome_banco: item.banco,
                        numero_conta: item.conta,
                        descricao: item.descricao_banco,
                        valor: item.valor,
                        conciliado: true
                    });
                }
            });
        }
        
        console.log(`📤 Exportando ${dadosSistema.length} itens do sistema e ${dadosBanco.length} itens do banco`);
        
        // Enviar para backend
        const response = await fetch('/financeiro/conciliacao-lancamentos/api/exportar-conciliacao', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                sistema: dadosSistema,
                banco: dadosBanco
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Erro ao exportar');
        }
        
        // Baixar arquivo
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `conciliacao_bancaria_${new Date().toISOString().split('T')[0]}.xlsx`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        console.log('✅ Exportação concluída com sucesso');
        mostrarNotificacao('✅ Relatório exportado com sucesso!', 'success');
        
    } catch (error) {
        console.error('❌ Erro na exportação:', error);
        mostrarNotificacao(`❌ Erro ao exportar: ${error.message}`, 'error');
    }
}

function conciliarManual() {
    const totalSistema = calcularTotalSelecionados(AppState.sistemasPendentes, AppState.sistemasSelecionados);
    const totalBanco = calcularTotalSelecionados(AppState.bancosPendentes, AppState.bancosSelecionados);
    
    const validationMsg = document.getElementById('validation-message');
    
    // Validação: valores devem ser iguais
    if (Math.abs(totalSistema - totalBanco) > 0.01) {
        validationMsg.innerHTML = `
            <i class="mdi mdi-alert"></i>
            <strong>Erro:</strong> Os valores selecionados não são iguais. 
            Sistema: ${formatarMoeda(totalSistema)} | Banco: ${formatarMoeda(totalBanco)}
        `;
        validationMsg.className = 'validation-message error';
        validationMsg.style.display = 'block';
        return;
    }
    
    validationMsg.style.display = 'none';
    
    // Criar grupo de conciliação
    const sistemaItems = AppState.sistemasPendentes.filter(item => AppState.sistemasSelecionados.has(item.id));
    const bancoItems = AppState.bancosPendentes.filter(item => AppState.bancosSelecionados.has(item.id));
    
    const grupo = {
        id: gerarId(),
        tipo: 'manual',
        data: new Date().toISOString().split('T')[0],
        valorTotal: totalSistema,
        sistema: sistemaItems,
        banco: bancoItems,
        timestamp: new Date().toISOString()
    };
    
    // Adicionar ao estado
    AppState.conciliacoes.push(grupo);
    
    // Limpar seleções
    AppState.sistemasSelecionados.clear();
    AppState.bancosSelecionados.clear();
    
    // Recalcular pendentes
    calcularPendentes();
    
    // Atualizar UI
    atualizarKPIs();
    renderizarTabelaSistema();
    renderizarTabelaBanco();
    renderizarTabelaConciliados();
    
    mostrarNotificacao('✅ Conciliação manual realizada com sucesso!', 'success');
}

window.desfazerConciliacao = function(grupoId) {
    if (!confirm('Deseja realmente desfazer esta conciliação?')) return;
    
    const index = AppState.conciliacoes.findIndex(g => g.id === grupoId);
    if (index === -1) return;
    
    // Remover do array
    AppState.conciliacoes.splice(index, 1);
    
    // Recalcular pendentes
    calcularPendentes();
    
    // Atualizar UI
    atualizarKPIs();
    renderizarTabelaSistema();
    renderizarTabelaBanco();
    renderizarTabelaConciliados();
    
    mostrarNotificacao('↩️ Conciliação desfeita', 'info');
};

// ========================================
// KPIs
// ========================================
function atualizarKPIs() {
    const totalSistema = AppState.sistemasPendentes.reduce((sum, item) => sum + parseFloat(item.valor || 0), 0);
    const totalBanco = AppState.bancosPendentes.reduce((sum, item) => sum + parseFloat(item.valor || 0), 0);
    const totalConciliado = AppState.conciliacoes.reduce((sum, grupo) => sum + parseFloat(grupo.valorTotal || 0), 0);
    const conciliadosAutomaticos = AppState.statusResumo.conciliados_automatico || 0;
    const conciliacoesManuais = AppState.conciliacoes.filter(grupo => grupo.tipo === 'manual').length;
    const totalConciliadosCount = AppState.conciliacoes.length || (conciliadosAutomaticos + conciliacoesManuais);
    const valorConciliadoResumo = typeof AppState.statusResumo.valor_conciliado === 'number'
        ? AppState.statusResumo.valor_conciliado
        : totalConciliado;
    const valorConciliadoManual = AppState.conciliacoes
        .filter(grupo => grupo.tipo === 'manual')
        .reduce((sum, grupo) => sum + parseFloat(grupo.valorTotal || 0), 0);
    const valorConciliadoTotal = valorConciliadoResumo + (valorConciliadoManual || 0);
    
    document.getElementById('kpi-pendentes-sistema-count').textContent = AppState.sistemasPendentes.length;
    document.getElementById('kpi-pendentes-sistema-valor').textContent = formatarMoeda(totalSistema);
    
    document.getElementById('kpi-pendentes-banco-count').textContent = AppState.bancosPendentes.length;
    document.getElementById('kpi-pendentes-banco-valor').textContent = formatarMoeda(totalBanco);
    
    document.getElementById('kpi-conciliados-count').textContent = totalConciliadosCount;
    document.getElementById('kpi-conciliados-valor').textContent = formatarMoeda(valorConciliadoTotal);
    
    const totalSistemaRegistros = AppState.statusResumo.total_sistema || AppState.lancamentosSistema.length;
    const totalBancoRegistros = AppState.statusResumo.total_banco || AppState.lancamentosBanco.length;

    document.getElementById('kpi-total-sistema').textContent = totalSistemaRegistros;
    document.getElementById('kpi-total-banco').textContent = totalBancoRegistros;
    
    // Atualizar badges das abas
    document.getElementById('badge-pendentes').textContent = AppState.sistemasPendentes.length + AppState.bancosPendentes.length;
    document.getElementById('badge-conciliados').textContent = AppState.conciliacoes.length;
}

// ========================================
// FILTROS E BUSCA
// ========================================
function filtrarTabelaSistema() {
    const input = document.getElementById('searchSistema');
    AppState.buscaSistema = input ? input.value.toLowerCase() : '';
    AppState.paginacaoSistema.paginaAtual = 1;
    renderizarTabelaSistema();
}

function filtrarTabelaBanco() {
    const input = document.getElementById('searchBanco');
    const selectBanco = document.getElementById('filtroBanco');
    AppState.buscaBanco = input ? input.value.toLowerCase() : '';
    AppState.filtroBanco = selectBanco ? selectBanco.value : '';
    AppState.paginacaoBanco.paginaAtual = 1;
    renderizarTabelaBanco();
}

function filtrarConciliados() {
    const tipo = document.getElementById('filtroTipoConciliacao').value;
    const banco = document.getElementById('filtroBancoConciliados').value;
    const termo = document.getElementById('searchConciliados').value.toLowerCase().trim();

    const rows = document.querySelectorAll('#tableConciliados tr[data-tipo]');
    if (rows.length === 0) {
        const emptyRow = document.getElementById('conciliados-empty-filter');
        if (emptyRow) {
            emptyRow.style.display = 'none';
        }
        return;
    }
    let algumVisivel = false;

    rows.forEach(row => {
        const rowTipo = row.dataset.tipo || '';
        const bancosDataset = row.dataset.bancos ? row.dataset.bancos.split(',').filter(Boolean) : [];
        const tipoMatch = !tipo || rowTipo === tipo;
        const bancoMatch = !banco || bancosDataset.includes(banco);
        const termoMatch = !termo || row.textContent.toLowerCase().includes(termo);

        const visivel = tipoMatch && bancoMatch && termoMatch;
        row.style.display = visivel ? '' : 'none';
        if (visivel) algumVisivel = true;
    });

    let emptyRow = document.getElementById('conciliados-empty-filter');
    if (!algumVisivel) {
        if (!emptyRow) {
            emptyRow = document.createElement('tr');
            emptyRow.id = 'conciliados-empty-filter';
            emptyRow.innerHTML = '<td colspan="6" class="text-center text-muted py-4">Nenhuma conciliação encontrada com os filtros atuais</td>';
            const tbody = document.getElementById('tableConciliados');
            if (tbody) tbody.appendChild(emptyRow);
        }
        emptyRow.style.display = '';
    } else if (emptyRow) {
        emptyRow.style.display = 'none';
    }
}

// ========================================
// NAVEGAÇÃO DE ABAS
// ========================================
function trocarAba(nomeAba) {
    AppState.abaAtiva = nomeAba;
    
    // Atualizar botões
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === nomeAba);
    });
    
    // Atualizar conteúdo
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.toggle('active', content.id === `tab-${nomeAba}`);
    });
}

// ========================================
// UTILITÁRIOS
// ========================================
function limparSessao() {
    if (!confirm('Deseja realmente limpar todos os dados e iniciar nova sessão?')) return;
    
    AppState.lancamentosSistema = [];
    AppState.lancamentosBanco = [];
    AppState.sistemasPendentes = [];
    AppState.bancosPendentes = [];
    AppState.conciliacoes = [];
    AppState.statusResumo = {};
    AppState.sistemasSelecionados.clear();
    AppState.bancosSelecionados.clear();
    AppState.paginacaoSistema.paginaAtual = 1;
    AppState.paginacaoBanco.paginaAtual = 1;
    
    document.getElementById('kpisSection').style.display = 'none';
    document.getElementById('workspace').style.display = 'none';
    document.querySelector('.upload-section').style.display = 'block';
    document.getElementById('btnLimparSessao').style.display = 'none';
    document.getElementById('btnExportarRelatorio').style.display = 'none';
    
    document.getElementById('uploadForm').reset();
    document.querySelector('.upload-placeholder').style.display = 'block';
    document.getElementById('filesList').style.display = 'none';
    document.getElementById('btnProcessar').disabled = true;
    
    trocarAba('conciliar');
    mostrarNotificacao('🔄 Sessão limpa', 'info');
}

function gerarId() {
    return 'conc_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

function formatarData(data) {
    if (!data) return '-';
    const d = new Date(data + 'T00:00:00');
    return d.toLocaleDateString('pt-BR');
}

function formatarMoeda(valor) {
    const num = parseFloat(valor) || 0;
    return num.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

function formatarBanco(banco) {
    const bancos = {
        'itau': 'Itaú',
        'santander': 'Santander',
        'banco_brasil': 'BB'
    };
    return bancos[banco] || banco;
}

function mostrarLoading(mensagem) {
    const loadingElement = document.getElementById('loading-message');
    // Usar innerHTML se mensagem contém HTML, senão textContent
    if (mensagem.includes('<')) {
        loadingElement.innerHTML = mensagem;
    } else {
        loadingElement.textContent = mensagem;
    }
    document.getElementById('loading-overlay').style.display = 'flex';
}

function esconderLoading() {
    document.getElementById('loading-overlay').style.display = 'none';
}

function mostrarNotificacao(mensagem, tipo) {
    const bar = document.getElementById('notification-bar');
    bar.textContent = mensagem;
    const classe = ['success', 'error', 'info'].includes(tipo) ? tipo : 'info';
    bar.className = `notification-bar ${classe}`;
    bar.style.display = 'block';
    
    setTimeout(() => {
        bar.style.display = 'none';
    }, 4000);
}

function prepararNovaSessaoProcessamento() {
    AppState.conciliacoes = [];
    AppState.lancamentosSistema = [];
    AppState.lancamentosBanco = [];
    AppState.sistemasPendentes = [];
    AppState.bancosPendentes = [];
    AppState.statusResumo = {};
    AppState.sistemasSelecionados.clear();
    AppState.bancosSelecionados.clear();
    AppState.buscaSistema = '';
    AppState.buscaBanco = '';
    AppState.filtroBanco = '';
    AppState.ordenacaoSistema = { campo: 'data', ordem: 'desc' };
    AppState.ordenacaoBanco = { campo: 'data', ordem: 'desc' };
    AppState.paginacaoSistema.paginaAtual = 1;
    AppState.paginacaoBanco.paginaAtual = 1;

    ['searchSistema', 'searchBanco'].forEach(id => {
        const campo = document.getElementById(id);
        if (campo) campo.value = '';
    });

    const filtroBanco = document.getElementById('filtroBanco');
    if (filtroBanco) filtroBanco.value = '';

    const checkAllSistema = document.getElementById('checkAllSistema');
    if (checkAllSistema) checkAllSistema.checked = false;
    const checkAllBanco = document.getElementById('checkAllBanco');
    if (checkAllBanco) checkAllBanco.checked = false;
}

function calcularPeriodoSistema(tipoPeriodo) {
    const hoje = new Date();
    let inicio;
    let fim;

    switch (tipoPeriodo) {
        case 'mes_anterior': {
            const ano = hoje.getFullYear();
            const mesAnterior = hoje.getMonth() - 1;
            inicio = new Date(ano, mesAnterior, 1);
            fim = new Date(ano, mesAnterior + 1, 0);
            break;
        }
        case 'ultimos_30_dias':
            inicio = new Date(hoje);
            inicio.setDate(inicio.getDate() - 29);
            fim = new Date(hoje);
            break;
        case 'ultimos_15_dias':
            inicio = new Date(hoje);
            inicio.setDate(inicio.getDate() - 14);
            fim = new Date(hoje);
            break;
        case 'ultimos_7_dias':
            inicio = new Date(hoje);
            inicio.setDate(inicio.getDate() - 6);
            fim = new Date(hoje);
            break;
        case 'mes_atual':
        default:
            inicio = new Date(hoje.getFullYear(), hoje.getMonth(), 1);
            fim = new Date(hoje);
            break;
    }

    return {
        inicio: formatarISO(inicio),
        fim: formatarISO(fim)
    };
}

function formatarISO(data) {
    const ano = data.getFullYear();
    const mes = String(data.getMonth() + 1).padStart(2, '0');
    const dia = String(data.getDate()).padStart(2, '0');
    return `${ano}-${mes}-${dia}`;
}

function extrairReferenciaCodigo(texto) {
    if (!texto) return '';
    const valor = String(texto).toUpperCase();
    const match = valor.match(/\b(U[NS][0-9][0-9A-Z\/-]*)/);
    if (!match) {
        return '';
    }
    const referencia = match[1].replace(/[\s,.;:]+$/, '');
    const digitos = referencia.replace(/\D/g, '');
    return digitos.length >= 4 ? referencia : '';
}

function aplicarReferenciaExtraida(normalizado, campos) {
    if (!normalizado || !Array.isArray(campos)) {
        return;
    }
    for (const campo of campos) {
        const referencia = extrairReferenciaCodigo(campo);
        if (referencia) {
            normalizado.ref_unique = referencia;
            normalizado.ref_unique_norm = referencia;
            normalizado.codigo_referencia = referencia;
            return;
        }
    }
}

function escapeHtml(valor) {
    if (valor === null || valor === undefined) {
        return '';
    }
    return String(valor)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function normalizarMovimentoSistema(item) {
    if (!item) return null;
    const normalizado = { ...item };

    const dataValor = normalizarDataISO(
        item.data_lancamento || item.data_movimento || item.data || item.data_referencia
    );

    normalizado.id = item.id ? String(item.id) : criarIdTemporario('sistema');
    normalizado.data = dataValor || '';
    if (!normalizado.data_lancamento && dataValor) {
        normalizado.data_lancamento = dataValor;
    }

    normalizado.descricao = String(item.descricao ?? item.descricao_original ?? '').trim();
    normalizado.ref_unique = item.ref_unique || item.codigo_referencia || item.ref_unique_norm || '';
    normalizado.ref_unique_norm = item.ref_unique_norm || normalizado.ref_unique || '';
    normalizado.codigo_referencia = item.codigo_referencia || normalizado.ref_unique || '';
    normalizado.valor = parseFloat(item.valor || 0);
    normalizado.status = (item.status || 'pendente').toLowerCase();
    normalizado.empresa = item.empresa || item.empresa_nome || '';
    
    // BUGFIX: Normalizar nome do banco para garantir compatibilidade com filtros
    // 'ITAU' → 'itau', 'Banco do Brasil'/'BANCO DO BRASIL' → 'banco_brasil'
    normalizado.banco = normalizarBancoId(item.banco || item.nome_banco || item.nome_banco_original || '');

    aplicarReferenciaExtraida(normalizado, [
        normalizado.ref_unique,
        normalizado.codigo_referencia,
        normalizado.ref_unique_norm,
        item.ref_unique,
        item.codigo_referencia,
        item.ref_unique_norm,
        item.descricao,
        item.descricao_original,
        item.historico,
        item.numero_documento,
        item.identificador
    ]);

    return normalizado;
}

function normalizarMovimentoBanco(item) {
    if (!item) return null;
    const normalizado = { ...item };

    const dataValor = normalizarDataISO(item.data || item.data_lancamento || item.data_original);

    normalizado.id = item.id ? String(item.id) : criarIdTemporario('banco');
    normalizado.data = dataValor || '';
    normalizado.valor = parseFloat(item.valor || 0);
    normalizado.descricao = String(item.descricao ?? item.historico ?? '').trim();
    normalizado.ref_unique = item.ref_unique || item.codigo_referencia || item.ref_unique_norm || '';
    normalizado.ref_unique_norm = item.ref_unique_norm || normalizado.ref_unique || '';
    normalizado.banco = normalizarBancoId(item.banco || item.banco_origem || item.nome_banco);
    normalizado.codigo_referencia = item.codigo_referencia || normalizado.ref_unique || '';
    normalizado.status = (item.status || 'pendente').toLowerCase();

    aplicarReferenciaExtraida(normalizado, [
        normalizado.ref_unique,
        normalizado.codigo_referencia,
        normalizado.ref_unique_norm,
        item.ref_unique,
        item.codigo_referencia,
        item.ref_unique_norm,
        item.descricao,
        item.historico,
        item.observacoes,
        item.identificador
    ]);

    return normalizado;
}

function normalizarDataISO(valor) {
    if (!valor) return '';

    if (valor instanceof Date) {
        return valor.toISOString().slice(0, 10);
    }

    const texto = String(valor).trim();
    if (!texto) return '';

    if (/^\d{4}-\d{2}-\d{2}/.test(texto)) {
        return texto.slice(0, 10);
    }

    if (/^\d{2}\/\d{2}\/\d{4}$/.test(texto)) {
        const [dia, mes, ano] = texto.split('/');
        return `${ano}-${mes}-${dia}`;
    }

    const timestamp = Date.parse(texto);
    if (!Number.isNaN(timestamp)) {
        return new Date(timestamp).toISOString().slice(0, 10);
    }

    return '';
}

function normalizarBancoId(nome) {
    if (!nome) return '';
    const texto = nome.toString().toLowerCase();

    if (texto.includes('ita')) return 'itau';
    if (texto.includes('santander')) return 'santander';
    if (texto.includes('banco do brasil') || texto.includes('bb') || texto.includes('banco_brasil')) {
        return 'banco_brasil';
    }

    return texto.replace(/\s+/g, '_');
}

function obterItensOrdenados(lista, ordenacao) {
    if (!Array.isArray(lista)) return [];
    if (!ordenacao || !ordenacao.campo) return [...lista];

    const copia = [...lista];
    const campo = ordenacao.campo;
    const ordem = ordenacao.ordem === 'asc' ? 'asc' : 'desc';

    copia.sort((a, b) => compararOrdenacao(a, b, campo, ordem));
    return copia;
}

function compararOrdenacao(a, b, campo, ordem) {
    const valorA = obterValorOrdenacao(a, campo);
    const valorB = obterValorOrdenacao(b, campo);

    if (valorA === valorB) return 0;

    if (ordem === 'asc') {
        return valorA > valorB ? 1 : -1;
    }
    return valorA < valorB ? 1 : -1;
}

function obterValorOrdenacao(item, campo) {
    switch (campo) {
        case 'data': {
            const iso = normalizarDataISO(item.data || item.data_lancamento || '');
            return iso ? Date.parse(`${iso}T00:00:00`) : 0;
        }
        case 'valor':
            return parseFloat(item.valor || 0);
        case 'descricao':
            return (item.descricao || item.historico || '').toLowerCase();
        case 'ref':
            return (item.ref_unique || item.ref_unique_norm || '').toLowerCase();
        case 'banco':
            return (item.banco || '').toLowerCase();
        default:
            if (item[campo] === null || item[campo] === undefined) return '';
            return String(item[campo]).toLowerCase();
    }
}

function aplicarOrdenacao(tabela, campo) {
    const alvo = tabela === 'banco' ? AppState.ordenacaoBanco : AppState.ordenacaoSistema;

    if (alvo.campo === campo) {
        alvo.ordem = alvo.ordem === 'asc' ? 'desc' : 'asc';
    } else {
        alvo.campo = campo;
        alvo.ordem = campo === 'valor' ? 'desc' : 'asc';
    }

    if (tabela === 'banco') {
        AppState.paginacaoBanco.paginaAtual = 1;
        renderizarTabelaBanco();
    } else {
        AppState.paginacaoSistema.paginaAtual = 1;
        renderizarTabelaSistema();
    }
}

function atualizarIndicadoresOrdenacao() {
    document.querySelectorAll('th.sortable').forEach(th => {
        th.classList.remove('sorted-asc', 'sorted-desc');
        const tabela = th.dataset.table;
        const campo = th.dataset.sort;
        if (!tabela || !campo) return;

        const ordenacaoAtual = tabela === 'banco' ? AppState.ordenacaoBanco : AppState.ordenacaoSistema;
        if (ordenacaoAtual.campo === campo) {
            th.classList.add(ordenacaoAtual.ordem === 'asc' ? 'sorted-asc' : 'sorted-desc');
        }
    });
}

function inicializarOrdenacao() {
    document.querySelectorAll('th.sortable').forEach(th => {
        th.addEventListener('click', () => {
            const tabela = th.dataset.table;
            const campo = th.dataset.sort;
            if (!tabela || !campo) return;
            aplicarOrdenacao(tabela, campo);
        });
    });
    atualizarIndicadoresOrdenacao();
}

function criarIdTemporario(prefixo) {
    return `${prefixo}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

function gerarConciliacoesAutomaticas(lancamentosSistema, lancamentosBanco) {
    if (!Array.isArray(lancamentosSistema) || !Array.isArray(lancamentosBanco)) {
        return [];
    }

    const bancoPorId = new Map();
    lancamentosBanco.forEach(item => {
        if (item && item.id) {
            bancoPorId.set(String(item.id), item);
        }
    });

    const conciliacoes = [];
    const usadosSistema = new Set();
    const usadosBanco = new Set();
    const tokensSistemaCache = new Map();
    const tokensBancoCache = new Map();

    const obterCacheKey = (item, prefixo) => {
        if (!item) return `${prefixo}_undefined`;
        if (item.id) return `${prefixo}_${item.id}`;
        return `${prefixo}_${item.descricao || ''}_${item.valor || ''}_${item.data || ''}`;
    };

    const obterTokensSistema = (item) => {
        const key = obterCacheKey(item, 's');
        if (!tokensSistemaCache.has(key)) {
            tokensSistemaCache.set(key, extrairTokensComparacao(item?.descricao || item?.descricao_original || item?.historico));
        }
        return tokensSistemaCache.get(key);
    };

    const obterTokensBanco = (item) => {
        const key = obterCacheKey(item, 'b');
        if (!tokensBancoCache.has(key)) {
            tokensBancoCache.set(key, extrairTokensComparacao(item?.descricao || item?.historico));
        }
        return tokensBancoCache.get(key);
    };

    const registrarConciliacao = (itemSistema, itemBanco, tipo, criterios) => {
        const valorTotal = Number.parseFloat(itemSistema?.valor ?? itemBanco?.valor ?? 0) || 0;
        const dataConciliada = obterDataNormalizada(itemSistema) || obterDataNormalizada(itemBanco) || new Date().toISOString().split('T')[0];
        conciliacoes.push({
            id: gerarId(),
            tipo,
            data: dataConciliada,
            valorTotal,
            sistema: [itemSistema],
            banco: [itemBanco],
            criterios,
            timestamp: new Date().toISOString()
        });

        usadosSistema.add(itemSistema.id);
        usadosBanco.add(itemBanco.id);
        itemSistema.status = 'conciliado';
        itemBanco.status = 'conciliado';
        itemSistema.match_id_banco = itemBanco.id;
        itemBanco.match_id_sistema = itemSistema.id;
    };

    const chaveCodigoDataValor = (item) => {
        const referencia = (item?.ref_unique || item?.codigo_referencia || item?.ref_unique_norm || '').toUpperCase().trim();
        if (!referencia) return null;
        const data = obterDataNormalizada(item);
        if (!data) return null;
        const valor = normalizarValorParaChave(item?.valor);
        if (valor === null) return null;
        return `${referencia}|${data}|${valor}`;
    };

    const chaveDataValor = (item) => {
        const data = obterDataNormalizada(item);
        if (!data) return null;
        const valor = normalizarValorParaChave(item?.valor);
        if (valor === null) return null;
        return `${data}|${valor}`;
    };

    const chaveValor = (item) => {
        const valor = normalizarValorParaChave(item?.valor);
        if (valor === null) return null;
        return valor;
    };

    const criarMapaBanco = (gerarChave) => {
        const mapa = new Map();
        lancamentosBanco.forEach(item => {
            if (!item || usadosBanco.has(item.id)) return;
            const chave = gerarChave(item);
            if (!chave) return;
            if (!mapa.has(chave)) {
                mapa.set(chave, []);
            }
            mapa.get(chave).push(item);
        });
        return mapa;
    };

    const removerDoMapa = (mapa, chave, itemBanco) => {
        if (!mapa || !mapa.has(chave)) return;
        const lista = mapa.get(chave);
        const index = lista.indexOf(itemBanco);
        if (index !== -1) {
            lista.splice(index, 1);
            if (lista.length === 0) {
                mapa.delete(chave);
            }
        }
    };

    // Passo 0 - conciliações já informadas pelo backend
    lancamentosSistema.forEach(item => {
        if (!item || item.status !== 'conciliado') {
            return;
        }

        const matchIdBanco = item.match_id_banco || item.matchIdBanco;
        if (!matchIdBanco) {
            return;
        }

        const bancoMatch = bancoPorId.get(String(matchIdBanco));
        if (!bancoMatch) {
            return;
        }

        if (usadosSistema.has(item.id) || usadosBanco.has(bancoMatch.id)) {
            return;
        }

        const criteriosOriginais = Array.isArray(item.criterios) ? item.criterios : item.criterios_conciliacao;
        registrarConciliacao(item, bancoMatch, definirTipoConciliacaoAutomatica(criteriosOriginais), criteriosOriginais || ['backend_match']);
    });

    // Passo 1 - Código + Data + Valor
    const mapaCodigoDataValor = criarMapaBanco(chaveCodigoDataValor);
    lancamentosSistema.forEach(item => {
        if (!item || usadosSistema.has(item.id)) return;
        const chave = chaveCodigoDataValor(item);
        if (!chave) return;
        const candidatos = mapaCodigoDataValor.get(chave);
        if (!candidatos || candidatos.length !== 1) return;
        const bancoItem = candidatos[0];
        registrarConciliacao(item, bancoItem, 'auto_ref', ['codigo_data_valor']);
        removerDoMapa(mapaCodigoDataValor, chave, bancoItem);
    });

    // Passo 2 - Data + Valor + Descrição aproximada
    const mapaDataValorTokens = criarMapaBanco(chaveDataValor);
    lancamentosSistema.forEach(item => {
        if (!item || usadosSistema.has(item.id)) return;
        const chave = chaveDataValor(item);
        if (!chave) return;
        const candidatos = mapaDataValorTokens.get(chave);
        if (!candidatos || candidatos.length === 0) return;

        const tokensSistema = obterTokensSistema(item);
        if (!tokensSistema || tokensSistema.length === 0) return;

        let melhor = null;
        let intersecMax = 0;
        let empate = false;

        candidatos.forEach(candidate => {
            if (usadosBanco.has(candidate.id)) return;
            const tokensBanco = obterTokensBanco(candidate);
            const intersec = contarIntersecao(tokensSistema, tokensBanco);
            if (intersec > intersecMax) {
                intersecMax = intersec;
                melhor = candidate;
                empate = false;
            } else if (intersec !== 0 && intersec === intersecMax) {
                empate = true;
            }
        });

        if (!melhor || intersecMax === 0 || empate) {
            return;
        }

        registrarConciliacao(item, melhor, 'auto_valor', ['descricao_match', 'data_igual', 'valor_exato']);
        removerDoMapa(mapaDataValorTokens, chave, melhor);
    });

    // Passo 3 - Data + Valor (nível mínimo)
    const mapaDataValorMinimo = criarMapaBanco(chaveDataValor);
    const contagemSistemaPorChave = new Map();
    lancamentosSistema.forEach(item => {
        if (!item || usadosSistema.has(item.id)) return;
        const chave = chaveDataValor(item);
        if (!chave) return;
        contagemSistemaPorChave.set(chave, (contagemSistemaPorChave.get(chave) || 0) + 1);
    });

    lancamentosSistema.forEach(item => {
        if (!item || usadosSistema.has(item.id)) return;
        const chave = chaveDataValor(item);
        if (!chave) return;
        if ((contagemSistemaPorChave.get(chave) || 0) !== 1) return;
        const candidatos = mapaDataValorMinimo.get(chave);
        if (!candidatos || candidatos.length !== 1) return;
        const bancoItem = candidatos[0];
        registrarConciliacao(item, bancoItem, 'auto_valor', ['data_igual', 'valor_exato', 'nivel_minimo']);
        removerDoMapa(mapaDataValorMinimo, chave, bancoItem);
    });

    // Passo 4 - Valor igual com data aproximada
    const mapaValor = criarMapaBanco(chaveValor);
    lancamentosSistema.forEach(item => {
        if (!item || usadosSistema.has(item.id)) return;
        const chaveValorItem = chaveValor(item);
        if (!chaveValorItem) return;
        const candidatos = mapaValor.get(chaveValorItem);
        if (!candidatos || candidatos.length === 0) return;

        const tokensSistema = obterTokensSistema(item);
        if (!tokensSistema || tokensSistema.length === 0) return;

        const dataSistema = obterDataNormalizada(item);
        if (!dataSistema) return;

        let melhor = null;
        let intersecMax = 0;
        let melhorDiff = Number.POSITIVE_INFINITY;
        let empate = false;

        candidatos.forEach(candidate => {
            if (usadosBanco.has(candidate.id)) return;
            const dataBanco = obterDataNormalizada(candidate);
            const diffDias = diferencaDiasDatas(dataSistema, dataBanco);
            if (diffDias === null || diffDias > 3) return;
            const tokensBanco = obterTokensBanco(candidate);
            const intersec = contarIntersecao(tokensSistema, tokensBanco);
            if (intersec === 0) return;

            if (intersec > intersecMax || (intersec === intersecMax && diffDias < melhorDiff)) {
                intersecMax = intersec;
                melhorDiff = diffDias;
                melhor = candidate;
                empate = false;
            } else if (intersec === intersecMax && diffDias === melhorDiff) {
                empate = true;
            }
        });

        if (!melhor || intersecMax === 0 || melhorDiff === Number.POSITIVE_INFINITY || empate) {
            return;
        }

        registrarConciliacao(item, melhor, 'auto_valor', ['data_aproximada', 'valor_exato', 'descricao_match']);
        removerDoMapa(mapaValor, chaveValorItem, melhor);
    });

    return conciliacoes;
}

function diferencaDiasDatas(dataISO1, dataISO2) {
    if (!dataISO1 || !dataISO2) return null;
    const time1 = Date.parse(`${dataISO1}T00:00:00`);
    const time2 = Date.parse(`${dataISO2}T00:00:00`);
    if (Number.isNaN(time1) || Number.isNaN(time2)) return null;
    const diffMs = Math.abs(time1 - time2);
    return Math.floor(diffMs / (24 * 60 * 60 * 1000));
}

function extrairTokensComparacao(texto) {
    if (!texto) return [];
    const normalizado = String(texto)
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .toUpperCase()
        .replace(/[^A-Z0-9\s]/g, ' ');
    return normalizado
        .split(/\s+/)
        .filter(token => token.length >= 4 && !/^\d+$/.test(token));
}

function contarIntersecao(tokensA, tokensB) {
    if (!Array.isArray(tokensA) || !Array.isArray(tokensB) || tokensA.length === 0 || tokensB.length === 0) {
        return 0;
    }
    const setB = new Set(tokensB);
    let count = 0;
    tokensA.forEach(token => {
        if (setB.has(token)) {
            count += 1;
        }
    });
    return count;
}

function normalizarValorParaChave(valor) {
    const numero = Number.parseFloat(valor);
    if (!Number.isFinite(numero)) return null;
    return numero.toFixed(2);
}

function obterDataNormalizada(item) {
    if (!item) return '';
    return item.data || item.data_lancamento || item.data_movimento || item.data_referencia || '';
}

function definirTipoConciliacaoAutomatica(criterios) {
    if (!Array.isArray(criterios)) {
        return 'auto_valor';
    }

    if (criterios.includes('codigo_exato') || criterios.includes('codigo_parcial')) {
        return 'auto_ref';
    }

    return 'auto_valor';
}

// ========================================
// GESTÃO DE USUÁRIOS E CONTAS
// ========================================

let todasContasDisponiveis = [];
let usuariosAnalistas = [];

async function abrirModalGestaoUsuarios() {
    console.log('🔧 Abrindo modal de gestão de contas...');
    
    const modal = new bootstrap.Modal(document.getElementById('modalGestaoUsuarios'));
    modal.show();
    
    await carregarContasEUsuarios();
}

async function carregarContasEUsuarios() {
    const container = document.getElementById('listaContasUsuarios');
    
    try {
        container.innerHTML = '<div class="text-center"><div class="spinner-border text-primary"></div><p class="mt-2">Carregando...</p></div>';
        
        // Buscar usuários com perfil analista
        const responseUsuarios = await fetch('/financeiro/conciliacao-lancamentos/api/usuarios-perfil-analista');
        const dataUsuarios = await responseUsuarios.json();
        
        if (!dataUsuarios.success) {
            throw new Error(dataUsuarios.error || 'Erro ao buscar usuários');
        }
        
        usuariosAnalistas = dataUsuarios.usuarios;
        
        // Buscar todas as contas disponíveis
        const responseContas = await fetch('/financeiro/conciliacao-lancamentos/api/contas-disponiveis');
        const dataContas = await responseContas.json();
        
        if (!dataContas.success) {
            throw new Error(dataContas.error || 'Erro ao buscar contas');
        }
        
        todasContasDisponiveis = dataContas.contas;
        
        console.log(`✅ Carregadas ${todasContasDisponiveis.length} contas e ${usuariosAnalistas.length} usuários`);
        
        // Renderizar lista de contas
        await renderizarListaContasUsuarios();
        
    } catch (error) {
        console.error('❌ Erro ao carregar dados:', error);
        container.innerHTML = `
            <div class="alert alert-danger">
                <i class="mdi mdi-alert"></i> Erro ao carregar dados: ${error.message}
            </div>
        `;
    }
}

async function renderizarListaContasUsuarios() {
    const container = document.getElementById('listaContasUsuarios');
    
    if (todasContasDisponiveis.length === 0) {
        container.innerHTML = `
            <div class="alert alert-warning">
                <i class="mdi mdi-alert-circle"></i>
                Nenhuma conta encontrada no sistema.
            </div>
        `;
        return;
    }
    
    // Buscar usuários atribuídos para cada conta
    const contasComUsuarios = await Promise.all(
        todasContasDisponiveis.map(async (conta) => {
            // Buscar quais usuários têm essa conta
            const usuariosComEssaConta = await Promise.all(
                usuariosAnalistas.map(async (usuario) => {
                    const response = await fetch(`/financeiro/conciliacao-lancamentos/api/contas-usuario/${usuario.id}`);
                    const data = await response.json();
                    const temConta = data.success && data.contas.includes(conta);
                    return { usuario, temConta };
                })
            );
            
            return {
                conta,
                usuarios: usuariosComEssaConta
            };
        })
    );
    
    // Renderizar cards de contas
    container.innerHTML = contasComUsuarios.map(item => {
        const usuariosSelecionados = item.usuarios.filter(u => u.temConta).length;
        
        return `
            <div class="conta-card" data-conta="${item.conta}">
                <div class="conta-header">
                    <div class="conta-info">
                        <i class="mdi mdi-bank conta-icon"></i>
                        <div class="conta-details">
                            <h6>Conta: ${item.conta}</h6>
                            <small class="text-muted">Selecione os usuários que podem acessar esta conta</small>
                        </div>
                    </div>
                    <div>
                        <span class="badge-usuario-count">${usuariosSelecionados} usuário(s)</span>
                        <button class="btn btn-sm btn-primary btn-salvar-usuarios ms-2" onclick="salvarUsuariosConta('${item.conta}')">
                            <i class="mdi mdi-content-save"></i> Salvar
                        </button>
                    </div>
                </div>
                <div class="usuarios-checkboxes">
                    ${item.usuarios.map(({ usuario, temConta }) => {
                        const checked = temConta ? 'checked' : '';
                        const idCheckbox = `usuario_${item.conta.replace(/[^a-zA-Z0-9]/g, '_')}_${usuario.id}`;
                        const iniciais = usuario.username.substring(0, 2).toUpperCase();
                        
                        return `
                            <div class="usuario-checkbox-item">
                                <div class="form-check">
                                    <input 
                                        class="form-check-input" 
                                        type="checkbox" 
                                        id="${idCheckbox}" 
                                        value="${usuario.id}"
                                        data-conta="${item.conta}"
                                        ${checked}
                                        onchange="atualizarContadorUsuarios('${item.conta}')">
                                    <label class="form-check-label d-flex align-items-center" for="${idCheckbox}">
                                        <span class="usuario-avatar-small">${iniciais}</span>
                                        <span>${usuario.username}</span>
                                    </label>
                                </div>
                            </div>
                        `;
                    }).join('')}
                </div>
            </div>
        `;
    }).join('');
}

function atualizarContadorUsuarios(conta) {
    const card = document.querySelector(`.conta-card[data-conta="${conta}"]`);
    const checkboxes = card.querySelectorAll('input[type="checkbox"]:checked');
    const badge = card.querySelector('.badge-usuario-count');
    badge.textContent = `${checkboxes.length} usuário(s)`;
}

async function salvarUsuariosConta(conta) {
    const card = document.querySelector(`.conta-card[data-conta="${conta}"]`);
    const checkboxes = card.querySelectorAll('input[type="checkbox"]:checked');
    const usuariosSelecionados = Array.from(checkboxes).map(cb => cb.value);
    
    const btnSalvar = card.querySelector('.btn-salvar-usuarios');
    const textoOriginal = btnSalvar.innerHTML;
    
    try {
        btnSalvar.disabled = true;
        btnSalvar.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Salvando...';
        
        console.log(`💾 Salvando ${usuariosSelecionados.length} usuários para conta ${conta}`);
        
        // Atualizar cada usuário com essa conta
        const promises = usuariosAnalistas.map(async (usuario) => {
            const temMarcado = usuariosSelecionados.includes(usuario.id);
            
            // Buscar contas atuais do usuário
            const responseGet = await fetch(`/financeiro/conciliacao-lancamentos/api/contas-usuario/${usuario.id}`);
            const dataGet = await responseGet.json();
            const contasAtuais = dataGet.success ? dataGet.contas : [];
            
            // Adicionar ou remover a conta
            let novasContas = [...contasAtuais];
            if (temMarcado && !novasContas.includes(conta)) {
                novasContas.push(conta);
            } else if (!temMarcado && novasContas.includes(conta)) {
                novasContas = novasContas.filter(c => c !== conta);
            }
            
            // Salvar apenas se houve mudança
            if (JSON.stringify(contasAtuais.sort()) !== JSON.stringify(novasContas.sort())) {
                const response = await fetch(`/financeiro/conciliacao-lancamentos/api/contas-usuario/${usuario.id}`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ contas: novasContas })
                });
                return response.json();
            }
            return { success: true };
        });
        
        await Promise.all(promises);
        
        btnSalvar.innerHTML = '<i class="mdi mdi-check"></i> Salvo!';
        btnSalvar.classList.remove('btn-primary');
        btnSalvar.classList.add('btn-success');
        
        setTimeout(() => {
            btnSalvar.innerHTML = textoOriginal;
            btnSalvar.classList.remove('btn-success');
            btnSalvar.classList.add('btn-primary');
            btnSalvar.disabled = false;
        }, 2000);
        
        mostrarNotificacao(`✅ Conta ${conta} atualizada com sucesso!`, 'success');
        
    } catch (error) {
        console.error('❌ Erro ao salvar usuários:', error);
        btnSalvar.innerHTML = textoOriginal;
        btnSalvar.disabled = false;
        mostrarNotificacao(`❌ Erro: ${error.message}`, 'error');
    }
}

console.log('✅ Conciliação V2 carregada');
