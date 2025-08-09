// Clientes Sistema Management - CRUD com Múltiplos CNPJs
let clientes = [];
let editingClienteId = null;
let cnpjOptions = [];
let selectedCnpjs = []; // CNPJs selecionados no modal
let cnpjImportadorCache = {}; // cache simples por termo
let cnpjSuggestionIndex = -1; // índice navegação teclado
let latestCnpjSuggestions = []; // guarda último payload

document.addEventListener('DOMContentLoaded', function() {
    console.log('[CLIENTES SISTEMA] Iniciando carregamento...');
    loadClientes();
    setupEventListeners();
    setupPesquisaEmpresasFlow();
});

// Função para atualizar KPIs
function updateKPIs() {
    console.log('[CLIENTES SISTEMA] Atualizando KPIs...');
    
    const totalClientes = clientes.length;
    const totalCnpjs = clientes.reduce((total, cliente) => {
        return total + (cliente.cnpjs ? cliente.cnpjs.length : 0);
    }, 0);
    
    const comLogos = clientes.filter(cliente => 
        cliente.logo_url && cliente.logo_url.trim() !== ''
    ).length;
    
    const semLogos = totalClientes - comLogos;
    
    // Atualizar elementos KPI
    const updateKPI = (id, value) => {
        const element = document.getElementById(id);
        if (element) {
            // Animação de contagem se o valor mudou
            const currentValue = parseInt(element.textContent) || 0;
            if (currentValue !== value) {
                animateCountUp(element, currentValue, value);
            }
        }
    };
    
    updateKPI('kpi-total-clientes', totalClientes);
    updateKPI('kpi-total-cnpjs', totalCnpjs);
    updateKPI('kpi-com-logos', comLogos);
    updateKPI('kpi-sem-logos', semLogos);
    
    // Atualizar contador da tabela
    const countDisplay = document.getElementById('count-display');
    if (countDisplay) {
        const text = totalClientes === 1 ? 'cliente' : 'clientes';
        countDisplay.textContent = `${totalClientes} ${text}`;
    }
}

// Animação de contagem para KPIs
function animateCountUp(element, start, end, duration = 800) {
    const startTime = performance.now();
    const range = end - start;
    
    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        // Easing function para suavizar a animação
        const easeOutQuart = 1 - Math.pow(1 - progress, 4);
        
        const current = Math.round(start + (range * easeOutQuart));
        element.textContent = current;
        
        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }
    
    requestAnimationFrame(update);
}

// Função para mostrar/esconder empty state
function toggleEmptyState() {
    const tbody = document.getElementById('clientes-tbody');
    const emptyState = document.getElementById('empty-state');
    const tableSection = document.querySelector('.enhanced-table-section');
    
    if (clientes.length === 0) {
        if (tbody) tbody.style.display = 'none';
        if (emptyState) emptyState.style.display = 'block';
        if (tableSection) tableSection.style.display = 'none';
    } else {
        if (tbody) tbody.style.display = '';
        if (emptyState) emptyState.style.display = 'none';
        if (tableSection) tableSection.style.display = 'block';
    }
}

function setupEventListeners() {
    console.log('[CLIENTES SISTEMA] Configurando event listeners...');
    
    // Botão adicionar
    const btnAdicionar = document.getElementById('btn-adicionar');
    if (btnAdicionar) {
        btnAdicionar.addEventListener('click', () => openModal());
    }
    
    // Formulário
    const form = document.getElementById('form-cliente');
    if (form) {
        form.addEventListener('submit', handleSubmit);
    }
    
    // Adicionar CNPJ
    const addCnpjBtn = document.getElementById('add-cnpj');
    if (addCnpjBtn) {
        addCnpjBtn.addEventListener('click', addCnpjFromInput);
    }
    
    // Campo de CNPJ com Enter
    const cnpjInput = document.getElementById('cnpj-input');
    if (cnpjInput) {
        cnpjInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                // Se houver sugestão selecionada, usa ela
                const suggestions = document.querySelectorAll('#cnpj-suggestions .autocomplete-suggestion');
                if (suggestions.length && cnpjSuggestionIndex >= 0 && suggestions[cnpjSuggestionIndex]) {
                    suggestions[cnpjSuggestionIndex].click();
                } else {
                    addCnpjFromInput();
                }
            }
        });
        
        // Formatação automática de CNPJ somente quando conteúdo for apenas dígitos (permitir texto para busca por razão social)
        cnpjInput.addEventListener('input', function(e) {
            const raw = e.target.value;
            const hasLetters = /[A-Za-z]/.test(raw);
            // Se não há letras e somente dígitos (ignorando pontuação de CNPJ) formatar
            const digits = raw.replace(/\D/g, '');
            if (!hasLetters && digits.length && digits.length <= 14 && raw.replace(/[\.\-/]/g,'') === digits) {
                e.target.value = formatCnpjInput(digits);
            } else {
                // Manter texto livre para busca por nome
                // Opcional: limitar tamanho geral
                if (raw.length > 60) {
                    e.target.value = raw.slice(0,60);
                }
            }
            // Autocomplete desativado (economia de recursos)
        });

        cnpjInput.addEventListener('keydown', function(e) {
            const container = document.getElementById('cnpj-suggestions');
            if (!container || container.classList.contains('hidden')) return;
            const items = container.querySelectorAll('.autocomplete-suggestion');
            if (!items.length) return;
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                cnpjSuggestionIndex = (cnpjSuggestionIndex + 1) % items.length;
                updateSuggestionActive(items);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                cnpjSuggestionIndex = (cnpjSuggestionIndex - 1 + items.length) % items.length;
                updateSuggestionActive(items);
            } else if (e.key === 'Escape') {
                hideCnpjSuggestions();
            }
        });
    }
    
    // Preview de logo
    const logoFile = document.getElementById('logo_file');
    const logoUrl = document.getElementById('logo_url');
    
    if (logoFile) {
        logoFile.addEventListener('change', handleFileChange);
    }
    
    if (logoUrl) {
        logoUrl.addEventListener('input', handleUrlChange);
    }
    
    // Busca com debounce para performance
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        let debounceTimer;
        
        // Filtro em tempo real com debounce
        searchInput.addEventListener('input', function(e) {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                filterClientes();
            }, 300); // 300ms de debounce
        });
        
        // Busca instantânea ao pressionar Enter
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                clearTimeout(debounceTimer);
                filterClientes();
            }
        });
        
        // Limpar filtro com Escape
        searchInput.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                e.preventDefault();
                clearFilters();
            }
        });
    }
    
    // Limpar filtros
    const clearFilters = document.getElementById('clear-filters');
    if (clearFilters) {
        clearFilters.addEventListener('click', clearAllFilters);
    }
    
    console.log('[CLIENTES SISTEMA] Event listeners configurados');
}

// ================= Novo Fluxo: Pesquisa de Empresas (reduz chamadas) =================
let ultimaBuscaEmpresas = '';
let cacheBuscaEmpresas = {}; // { termoLower: [ {cnpj, razao_social}, ... ] }

function setupPesquisaEmpresasFlow() {
    const btnPesquisar = document.getElementById('btn-pesquisar-empresas');
    if (btnPesquisar) {
        btnPesquisar.addEventListener('click', () => {
            const termo = (document.getElementById('cnpj-input')?.value || '').trim();
            if (termo.length < 2) {
                showError('Digite ao menos 2 caracteres para pesquisar');
                return;
            }
            abrirModalPesquisaEmpresas(termo);
        });
    }
    const refazer = document.getElementById('btn-refazer-pesquisa');
    if (refazer) {
        refazer.addEventListener('click', () => {
            const termo = (document.getElementById('input-termo-pesquisa-empresas')?.value || '').trim();
            if (termo.length < 2) {
                showError('Digite ao menos 2 caracteres');
                return;
            }
            executarPesquisaEmpresas(termo, true);
        });
    }
    const termoRefine = document.getElementById('input-termo-pesquisa-empresas');
    if (termoRefine) {
        termoRefine.addEventListener('keypress', (e)=>{
            if (e.key === 'Enter') { e.preventDefault(); document.getElementById('btn-refazer-pesquisa').click(); }
        });
        termoRefine.addEventListener('input', ()=>{
            // Filtro local se já tem resultados
            const termoAtual = termoRefine.value.trim().toLowerCase();
            const lista = cacheBuscaEmpresas[ultimaBuscaEmpresas.toLowerCase()] || [];
            if (lista.length) {
                const filtrados = lista.filter(item => item.razao_social.toLowerCase().includes(termoAtual) || item.cnpj.includes(termoAtual.replace(/\D/g,'')));
                renderResultadosEmpresas(filtrados, termoAtual);
            }
        });
    }
    const btnAddSel = document.getElementById('btn-adicionar-empresas-selecionadas');
    if (btnAddSel) {
        btnAddSel.addEventListener('click', adicionarEmpresasSelecionadas);
    }
}

function abrirModalPesquisaEmpresas(termoInicial) {
    ultimaBuscaEmpresas = termoInicial;
    const modal = document.getElementById('modal-pesquisa-empresas');
    const inputRefine = document.getElementById('input-termo-pesquisa-empresas');
    if (inputRefine) inputRefine.value = termoInicial;
    if (modal) modal.style.display = 'flex';
    executarPesquisaEmpresas(termoInicial, false);
}
function fecharModalPesquisaEmpresas() {
    const modal = document.getElementById('modal-pesquisa-empresas');
    if (modal) modal.style.display = 'none';
    document.getElementById('resultado-pesquisa-empresas').innerHTML = '<div class="placeholder" style="padding:1rem; color:#6b7280; font-size:.9rem;">Digite um termo e clique em Pesquisar empresas.</div>';
    document.getElementById('status-pesquisa-empresas').textContent = '';
    const btnAdd = document.getElementById('btn-adicionar-empresas-selecionadas');
    if (btnAdd) { btnAdd.disabled = true; btnAdd.textContent = 'Adicionar selecionados (0)'; }
}
function executarPesquisaEmpresas(termo, forcar) {
    const status = document.getElementById('status-pesquisa-empresas');
    const listaDiv = document.getElementById('resultado-pesquisa-empresas');
    const lower = termo.toLowerCase();
    status.textContent = 'Pesquisando...';
    listaDiv.innerHTML = '<div style="padding:1rem; font-size:.85rem; color:#374151;">Carregando resultados...</div>';
    if (!forcar && cacheBuscaEmpresas[lower]) {
        renderResultadosEmpresas(cacheBuscaEmpresas[lower], lower);
        status.textContent = `${cacheBuscaEmpresas[lower].length} resultado(s) em cache.`;
        return;
    }
    fetch(`/config/api/cnpj-importadores?q=${encodeURIComponent(termo)}&limit=120`)
        .then(r=>r.json())
        .then(json => {
            if (!json.success) throw new Error(json.error || 'Falha');
            cacheBuscaEmpresas[lower] = json.data || [];
            renderResultadosEmpresas(cacheBuscaEmpresas[lower], lower);
            status.textContent = `${cacheBuscaEmpresas[lower].length} resultado(s).`;
        })
        .catch(err => {
            console.error('[PESQUISA EMPRESAS] Erro', err);
            listaDiv.innerHTML = '<div style="padding:1rem; color:#b91c1c;">Erro ao buscar empresas.</div>';
            status.textContent = 'Erro na pesquisa.';
        });
}
function renderResultadosEmpresas(lista, termo) {
    const listaDiv = document.getElementById('resultado-pesquisa-empresas');
    const btnAdd = document.getElementById('btn-adicionar-empresas-selecionadas');
    if (!listaDiv) return;
    if (!lista || !lista.length) {
        listaDiv.innerHTML = '<div style="padding:1rem; font-size:.85rem; color:#6b7280;">Sem resultados.</div>';
        if (btnAdd) { btnAdd.disabled = true; btnAdd.textContent = 'Adicionar selecionados (0)'; }
        return;
    }
    const highlight = (texto) => {
        if (!termo) return texto;
        const safe = termo.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        return texto.replace(new RegExp(`(${safe})`, 'ig'), '<mark style="background:#FEF3C7;">$1</mark>');
    };
    listaDiv.innerHTML = `
        <table class="table" style="width:100%; border-collapse:collapse;">
            <thead>
                <tr>
                    <th style="width:50px; text-align:center;"><input type="checkbox" id="chk-select-all-empresas" /></th>
                    <th>Razão Social</th>
                    <th style="width:180px;">CNPJ</th>
                </tr>
            </thead>
            <tbody>
                ${lista.map(item => {
                    const ja = selectedCnpjs.some(i => i.cnpj === item.cnpj);
                    return `<tr class="linha-empresa${ja ? ' linha-ja-adicionada' : ''}">
                        <td style="text-align:center;">
                            <input type="checkbox" class="chk-empresa" value="${item.cnpj}" ${ja ? 'disabled' : ''} />
                        </td>
                        <td>${highlight(item.razao_social)}</td>
                        <td>${formatCnpj(item.cnpj)}</td>
                    </tr>`;
                }).join('')}
            </tbody>
        </table>
    `;
    // Eventos
    const chkAll = document.getElementById('chk-select-all-empresas');
    if (chkAll) {
        chkAll.addEventListener('change', () => {
            document.querySelectorAll('#resultado-pesquisa-empresas .chk-empresa:not(:disabled)').forEach(cb => { cb.checked = chkAll.checked; });
            atualizarBtnAddEmpresas();
        });
    }
    listaDiv.querySelectorAll('.chk-empresa').forEach(cb => {
        cb.addEventListener('change', atualizarBtnAddEmpresas);
    });
    atualizarBtnAddEmpresas();
}
function atualizarBtnAddEmpresas() {
    const btnAdd = document.getElementById('btn-adicionar-empresas-selecionadas');
    if (!btnAdd) return;
    const selecionados = [...document.querySelectorAll('#resultado-pesquisa-empresas .chk-empresa:checked')];
    btnAdd.disabled = selecionados.length === 0;
    btnAdd.textContent = `Adicionar selecionados (${selecionados.length})`;
}
function adicionarEmpresasSelecionadas() {
    const selecionados = [...document.querySelectorAll('#resultado-pesquisa-empresas .chk-empresa:checked')];
    if (!selecionados.length) return;
    let novos = 0;
    selecionados.forEach(cb => {
        const cnpj = cb.value;
        if (!selectedCnpjs.some(i => i.cnpj === cnpj)) {
            // Recuperar razão social do cache original (ultimaBuscaEmpresas)
            const lista = cacheBuscaEmpresas[ultimaBuscaEmpresas.toLowerCase()] || [];
            const found = lista.find(i => i.cnpj === cnpj);
            selectedCnpjs.push({ cnpj, razao_social: found ? found.razao_social : '' });
            novos++;
        }
    });
    if (novos) {
        renderSelectedCnpjs();
        showSuccess(`${novos} CNPJ(s) adicionados`);
    } else {
        showError('Nenhum novo CNPJ adicionado');
    }
    fecharModalPesquisaEmpresas();
}

function addCnpjFromInput() {
    const cnpjInput = document.getElementById('cnpj-input');
    if (!cnpjInput || !cnpjInput.value.trim()) {
        showError('Digite um CNPJ válido');
        return;
    }
    
    const cnpjValue = cnpjInput.value.replace(/\D/g, '');
    
    // Validar CNPJ
    if (cnpjValue.length !== 14) {
        showError('CNPJ deve ter 14 dígitos');
        return;
    }
    
    // Verificar se já não está na lista
    if (selectedCnpjs.some(item => item.cnpj === cnpjValue)) {
        showError('CNPJ já adicionado à lista');
        return;
    }
    
    // Adicionar à lista de selecionados
    selectedCnpjs.push({
        cnpj: cnpjValue,
        razao_social: `Empresa ${formatCnpj(cnpjValue)}` // Nome genérico por enquanto
    });
    
    // Atualizar interface
    renderSelectedCnpjs();
    cnpjInput.value = ''; // Limpar campo
    
    console.log('[CLIENTES SISTEMA] CNPJ adicionado:', cnpjValue);
}
// (Autocomplete helpers removidos para reduzir chamadas)
function removeSelectedCnpj(cnpj) {
    selectedCnpjs = selectedCnpjs.filter(item => item.cnpj !== cnpj);
    renderSelectedCnpjs();
}

function renderSelectedCnpjs() {
    const container = document.getElementById('selected-cnpjs');
    if (!container) return;
    
    if (selectedCnpjs.length === 0) {
        container.className = 'selected-cnpjs-list empty';
        container.innerHTML = '';
        return;
    }
    
    container.className = 'selected-cnpjs-list';
    container.innerHTML = selectedCnpjs.map(item => `
        <div class="cnpj-tag">
            <span>${formatCnpj(item.cnpj)}</span>
            <button type="button" class="remove-cnpj" onclick="removeSelectedCnpj('${item.cnpj}')">
                <i class="mdi mdi-close"></i>
            </button>
        </div>
    `).join('');
}

async function loadClientes() {
    try {
        console.log('[CLIENTES SISTEMA] Carregando clientes...');
        let response = await fetch('/config/api/logos-clientes');
        if (!response.ok) {
            // Pequeno retry rápido (uma vez) em caso de 500/transiente
            console.warn('[CLIENTES SISTEMA] Primeira tentativa falhou, tentando novamente...');
            await new Promise(r => setTimeout(r, 600));
            response = await fetch('/config/api/logos-clientes');
        }
        const result = await response.json();
        
        if (result.success) {
            clientes = result.data || [];
            renderClientes();
            updateKPIs();
            console.log(`[CLIENTES SISTEMA] ${clientes.length} clientes carregados (source: ${result.source || 'live'})`);
        } else {
            console.error('[CLIENTES SISTEMA] Erro ao carregar clientes:', result.error);
            showError('Erro ao carregar clientes: ' + result.error);
            updateKPIs();
        }
    } catch (error) {
        console.error('[CLIENTES SISTEMA] Erro na requisição:', error);
        showError('Erro ao conectar com o servidor');
        updateKPIs();
    }
}

function renderClientes() {
    const tbody = document.getElementById('clientes-tbody');
    if (!tbody) return;
    
    const searchInput = document.getElementById('search-input');
    const searchTerm = searchInput?.value.toLowerCase().trim() || '';
    
    console.log(`[CLIENTES SISTEMA] Renderizando ${clientes.length} clientes. Filtro: "${searchTerm}"`);
    
    let filteredClientes = clientes;
    
    // Aplicar filtro se houver termo de busca
    if (searchTerm && searchTerm.length >= 1) {
        filteredClientes = clientes.filter(cliente => {
            // Buscar no nome do cliente
            const nomeMatch = cliente.nome_cliente.toLowerCase().includes(searchTerm);
            
            // Buscar nos CNPJs (tanto formatado quanto limpo)
            const cnpjMatch = cliente.cnpjs && cliente.cnpjs.some(cnpj => {
                const cnpjLimpo = cnpj.replace(/\D/g, '');
                const cnpjFormatado = formatCnpj(cnpj).toLowerCase();
                return cnpjLimpo.includes(searchTerm.replace(/\D/g, '')) || 
                       cnpjFormatado.includes(searchTerm);
            });
            
            return nomeMatch || cnpjMatch;
        });
        
        console.log(`[CLIENTES SISTEMA] ${filteredClientes.length} clientes após filtro`);
    }
    
    // Atualizar KPIs e empty state
    updateKPIs();
    toggleEmptyState();
    
    // Verificar se não há resultados após filtro
    if (filteredClientes.length === 0 && searchTerm) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" class="empty-search-state">
                    <div class="empty-search-content">
                        <i class="mdi mdi-magnify-close"></i>
                        <h4>Nenhum resultado encontrado</h4>
                        <p>Não encontramos clientes que correspondam ao termo "<strong>${searchTerm}</strong>"</p>
                        <button onclick="clearFilters()" class="btn btn-outline">
                            <i class="mdi mdi-filter-remove"></i>
                            Limpar Filtros
                        </button>
                    </div>
                </td>
            </tr>
        `;
        return;
    }
    
    // Se não há clientes, mostrar empty state (controlado por toggleEmptyState)
    if (clientes.length === 0) {
        return;
    }
    
    // Renderizar clientes filtrados com novos estilos
    tbody.innerHTML = filteredClientes.map(cliente => {
        // Logo com novos estilos
        const logoDisplay = cliente.logo_url ? 
            `<img src="${cliente.logo_url}" alt="Logo ${cliente.nome_cliente}" class="table-logo" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
             <div class="table-logo-placeholder" style="display: none;"><i class="mdi mdi-image-off"></i></div>` :
            '<div class="table-logo-placeholder"><i class="mdi mdi-image-off"></i></div>';
            
        // Nome do cliente com destaque na busca
        const nomeDisplay = searchTerm ? 
            highlightSearchTerm(cliente.nome_cliente, searchTerm) : 
            cliente.nome_cliente;
            
        // Renderizar CNPJs com novo layout
        const cnpjsDisplay = (cliente.cnpjs && cliente.cnpjs.length > 0) ? 
            `<div class="cnpj-list-table">
                ${cliente.cnpjs.slice(0, 4).map(cnpj => {
                    const cnpjFormatado = formatCnpj(cnpj);
                    const cnpjDestacado = searchTerm ? 
                        highlightSearchTerm(cnpjFormatado, searchTerm) : 
                        cnpjFormatado;
                    return `<span class="cnpj-badge-table">${cnpjDestacado}</span>`;
                }).join('')}
                ${cliente.cnpjs.length > 4 ? 
                    `<span class="cnpj-badge-table" style="background: #6b7280; color: white;">+${cliente.cnpjs.length - 4}</span>` : 
                    ''
                }
            </div>` :
            '<span style="color: #9ca3af; font-style: italic;">Nenhum CNPJ associado</span>';
            
        // Total de CNPJs com badge
        const totalCnpjs = cliente.cnpjs ? cliente.cnpjs.length : 0;
        
        return `
            <tr>
                <td style="text-align: center;">${logoDisplay}</td>
                <td>
                    <div class="cliente-name-cell">${nomeDisplay}</div>
                </td>
                <td>${cnpjsDisplay}</td>
                <td style="text-align: center;">
                    <span class="cnpj-count-badge">${totalCnpjs}</span>
                </td>
                <td>
                    <div class="action-buttons">
                        <button onclick="editCliente(${cliente.id})" class="btn-table-action btn-table-edit" title="Editar cliente">
                            <i class="mdi mdi-pencil"></i>
                            Editar
                        </button>
                        <button onclick="deleteCliente(${cliente.id})" class="btn-table-action btn-table-delete" title="Excluir cliente">
                            <i class="mdi mdi-delete"></i>
                            Excluir
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
    
    // Atualizar contador específico da busca se filtrada
    const countDisplay = document.getElementById('count-display');
    if (countDisplay && searchTerm) {
        const text = filteredClientes.length === 1 ? 'cliente encontrado' : 'clientes encontrados';
        countDisplay.textContent = `${filteredClientes.length} ${text}`;
    }
}

function openModal(cliente = null) {
    console.log('[CLIENTES SISTEMA] Abrindo modal:', cliente);
    editingClienteId = cliente ? cliente.id : null;
    
    // Processar CNPJs para o modal - converter strings em objetos para compatibilidade
    if (cliente && cliente.cnpjs) {
        selectedCnpjs = cliente.cnpjs.map(cnpj => ({
            cnpj: cnpj,
            razao_social: `Empresa ${formatCnpj(cnpj)}`
        }));
    } else {
        selectedCnpjs = [];
    }
    
    // Configurar título
    const title = document.getElementById('modal-title');
    if (title) {
        title.innerHTML = `
            <i class="mdi mdi-domain"></i>
            ${cliente ? 'Editar Cliente' : 'Adicionar Cliente'}
        `;
    }
    
    // Limpar form
    const form = document.getElementById('form-cliente');
    if (form) {
        form.reset();
    }
    hidePreview();
    
    // Se editando, preencher dados
    if (cliente) {
        const nomeInput = document.getElementById('nome_cliente');
        const logoUrlInput = document.getElementById('logo_url');
        
        if (nomeInput) {
            nomeInput.value = cliente.nome_cliente;
        }
        
        if (logoUrlInput) {
            logoUrlInput.value = cliente.logo_url || '';
        }
        
        if (cliente.logo_url) {
            showPreview(cliente.logo_url);
        }
    }
    
    // Atualizar interface de CNPJs
    renderSelectedCnpjs();
    
    // Mostrar modal
    const modal = document.getElementById('modal-cliente');
    if (modal) {
        modal.style.display = 'flex';
    }
}

async function handleSubmit(e) {
    e.preventDefault();
    console.log('[CLIENTES SISTEMA] Submetendo formulário...');
    
    const formData = new FormData(e.target);
    
    if (selectedCnpjs.length === 0) {
        showError('Pelo menos um CNPJ deve ser selecionado');
        return;
    }
    
    // Preparar dados
    const data = {
        nome_cliente: formData.get('nome_cliente'),
        logo_url: formData.get('logo_url') || '',
        cnpjs: selectedCnpjs.map(item => item.cnpj)
    };
    
    console.log('[CLIENTES SISTEMA] Dados para envio:', data);
    
    await saveCliente(data);
}

async function saveCliente(data) {
    try {
        console.log('[CLIENTES SISTEMA] Salvando cliente:', data);
        
        const endpoint = editingClienteId ? 
            `/config/api/logos-clientes/${editingClienteId}` : 
            '/config/api/logos-clientes';
        
        const method = editingClienteId ? 'PUT' : 'POST';
        
        const response = await fetch(endpoint, {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        console.log('[CLIENTES SISTEMA] Resposta do servidor:', result);
        
        if (result.success) {
            // Se há arquivo de logo para upload, fazer upload após criar/atualizar cliente
            const logoFile = document.getElementById('logo_file');
            if (logoFile && logoFile.files[0]) {
                const clienteId = result.data.id;
                console.log('[CLIENTES SISTEMA] Fazendo upload do logo para cliente:', clienteId);
                
                try {
                    const logoUrl = await uploadLogo(clienteId, logoFile.files[0]);
                    console.log('[CLIENTES SISTEMA] Logo atualizado:', logoUrl);
                    
                    showSuccess(result.message + ' Logo enviado com sucesso!');
                } catch (uploadError) {
                    console.error('[CLIENTES SISTEMA] Erro no upload do logo:', uploadError);
                    showSuccess(result.message + ' (Cliente salvo, mas houve erro no upload do logo)');
                }
            } else {
                showSuccess(result.message || (editingClienteId ? 'Cliente atualizado com sucesso!' : 'Cliente adicionado com sucesso!'));
            }
            
            closeModal();
            loadClientes();
        } else {
            showError('Erro ao salvar cliente: ' + result.error);
        }
    } catch (error) {
        console.error('[CLIENTES SISTEMA] Erro na requisição:', error);
        showError('Erro ao conectar com o servidor');
    }
}

function editCliente(clienteId) {
    console.log('[CLIENTES SISTEMA] Editando cliente:', clienteId);
    const cliente = clientes.find(c => c.id === clienteId);
    
    if (cliente) {
        openModal(cliente);
    } else {
        console.error('[CLIENTES SISTEMA] Cliente não encontrado:', clienteId);
    }
}

async function deleteCliente(clienteId) {
    const cliente = clientes.find(c => c.id === clienteId);
    
    if (!cliente) {
        console.error('[CLIENTES SISTEMA] Cliente não encontrado para exclusão:', clienteId);
        return;
    }
    
    if (!confirm(`Tem certeza que deseja excluir o cliente "${cliente.nome_cliente}"? Todos os CNPJs associados serão removidos.`)) {
        return;
    }
    
    try {
        console.log('[CLIENTES SISTEMA] Deletando cliente:', clienteId);
        
        const response = await fetch(`/config/api/logos-clientes/${clienteId}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.success) {
            showSuccess('Cliente excluído com sucesso!');
            loadClientes();
        } else {
            showError('Erro ao excluir cliente: ' + result.error);
        }
    } catch (error) {
        console.error('[CLIENTES SISTEMA] Erro na requisição de exclusão:', error);
        showError('Erro ao conectar com o servidor');
    }
}

function handleFileChange(e) {
    const file = e.target.files[0];
    if (file) {
        // Validar tipo de arquivo
        const allowedTypes = ['image/png', 'image/jpg', 'image/jpeg', 'image/gif', 'image/webp'];
        if (!allowedTypes.includes(file.type)) {
            showError('Tipo de arquivo não permitido. Use: PNG, JPG, JPEG, GIF ou WEBP');
            e.target.value = '';
            return;
        }
        
        // Validar tamanho (5MB máximo)
        const maxSize = 5 * 1024 * 1024; // 5MB
        if (file.size > maxSize) {
            showError('Arquivo muito grande. Tamanho máximo: 5MB');
            e.target.value = '';
            return;
        }
        
        // Mostrar preview
        const reader = new FileReader();
        reader.onload = function(e) {
            showPreview(e.target.result);
        };
        reader.readAsDataURL(file);
        
        console.log('[CLIENTES SISTEMA] Arquivo selecionado:', file.name, file.size, 'bytes');
    } else {
        hidePreview();
    }
}

async function uploadLogo(clienteId, file) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('cliente_id', clienteId);
    
    try {
        console.log('[CLIENTES SISTEMA] Iniciando upload do logo...');
        
        const response = await fetch('/config/api/upload-logo', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        console.log('[CLIENTES SISTEMA] Resposta do upload:', result);
        
        if (result.success) {
            console.log('[CLIENTES SISTEMA] Upload realizado com sucesso:', result.data.logo_url);
            return result.data.logo_url;
        } else {
            throw new Error(result.error || 'Erro no upload');
        }
    } catch (error) {
        console.error('[CLIENTES SISTEMA] Erro no upload:', error);
        throw error;
    }
}

function handleUrlChange(e) {
    const url = e.target.value;
    if (url) {
        showPreview(url);
    } else {
        hidePreview();
    }
}

function showPreview(url) {
    const preview = document.getElementById('logo-preview');
    const img = document.getElementById('logo-preview-img');
    
    if (preview && img) {
        img.src = url;
        preview.classList.remove('hidden');
    }
}

function hidePreview() {
    const preview = document.getElementById('logo-preview');
    if (preview) {
        preview.classList.add('hidden');
    }
}

function filterClientes() {
    console.log('[CLIENTES SISTEMA] Aplicando filtros...');
    const searchInput = document.getElementById('search-input');
    const searchTerm = searchInput?.value.toLowerCase().trim() || '';
    
    console.log(`[CLIENTES SISTEMA] Termo de busca: "${searchTerm}"`);
    
    // Adicionar classe visual se filtro estiver ativo
    if (searchInput) {
        if (searchTerm.length > 0) {
            searchInput.classList.add('active');
        } else {
            searchInput.classList.remove('active');
        }
    }
    
    // Renderizar com o filtro aplicado
    renderClientes();
    
    // Atualizar contador se necessário
    const tbody = document.getElementById('clientes-tbody');
    if (tbody) {
        const visibleRows = tbody.querySelectorAll('tr').length;
        console.log(`[CLIENTES SISTEMA] ${visibleRows} resultado(s) exibido(s)`);
    }
}

function clearFilters() {
    console.log('[CLIENTES SISTEMA] Limpando filtros...');
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.value = '';
        searchInput.classList.remove('active');
        searchInput.focus(); // Dar foco para facilitar nova busca
    }
    renderClientes();
}

// Função auxiliar para destacar texto encontrado
function highlightSearchTerm(text, searchTerm) {
    if (!searchTerm || searchTerm.length < 2) return text;
    
    const regex = new RegExp(`(${searchTerm.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
    return text.replace(regex, '<mark style="background-color: #FEF3C7; padding: 1px 2px; border-radius: 2px;">$1</mark>');
}

function closeModal() {
    console.log('[CLIENTES SISTEMA] Fechando modal...');
    const modal = document.getElementById('modal-cliente');
    const form = document.getElementById('form-cliente');
    
    if (modal) {
        modal.style.display = 'none';
    }
    
    if (form) {
        form.reset();
    }
    
    hidePreview();
    editingClienteId = null;
    selectedCnpjs = [];
    renderSelectedCnpjs();
}

function formatCnpj(cnpj) {
    if (!cnpj) return cnpj;
    const clean = cnpj.replace(/\D/g, '');
    if (clean.length === 14) {
        return clean.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, '$1.$2.$3/$4-$5');
    }
    return cnpj;
}

function formatCnpjInput(value) {
    // Formatação em tempo real para input
    if (value.length <= 2) return value;
    if (value.length <= 5) return `${value.slice(0, 2)}.${value.slice(2)}`;
    if (value.length <= 8) return `${value.slice(0, 2)}.${value.slice(2, 5)}.${value.slice(5)}`;
    if (value.length <= 12) return `${value.slice(0, 2)}.${value.slice(2, 5)}.${value.slice(5, 8)}/${value.slice(8)}`;
    return `${value.slice(0, 2)}.${value.slice(2, 5)}.${value.slice(5, 8)}/${value.slice(8, 12)}-${value.slice(12, 14)}`;
}

function clearAllFilters() {
    console.log('[CLIENTES SISTEMA] Limpando todos os filtros...');
    clearFilters();
}

function showSuccess(message) {
    console.log('[CLIENTES SISTEMA] Sucesso:', message);
    alert('✅ ' + message);
}

function showError(message) {
    console.error('[CLIENTES SISTEMA] Erro:', message);
    alert('❌ ' + message);
}

// Função global para fechar modal (chamada pelo HTML)
window.closeClienteModal = closeModal;
window.removeSelectedCnpj = removeSelectedCnpj;
