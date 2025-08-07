// Clientes Sistema Management - CRUD com Múltiplos CNPJs
let clientes = [];
let editingClienteId = null;
let cnpjOptions = [];
let selectedCnpjs = []; // CNPJs selecionados no modal

document.addEventListener('DOMContentLoaded', function() {
    console.log('[CLIENTES SISTEMA] Iniciando carregamento...');
    loadClientes();
    setupEventListeners();
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
                addCnpjFromInput();
            }
        });
        
        // Formatação automática de CNPJ
        cnpjInput.addEventListener('input', function(e) {
            let value = e.target.value.replace(/\D/g, '');
            if (value.length <= 14) {
                e.target.value = formatCnpjInput(value);
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
        const response = await fetch('/config/api/logos-clientes');
        const result = await response.json();
        
        if (result.success) {
            clientes = result.data;
            renderClientes();
            updateKPIs();
            console.log(`[CLIENTES SISTEMA] ${clientes.length} clientes carregados`);
        } else {
            console.error('[CLIENTES SISTEMA] Erro ao carregar clientes:', result.error);
            showError('Erro ao carregar clientes: ' + result.error);
            // Ainda assim atualizar KPIs para mostrar zero
            updateKPIs();
        }
    } catch (error) {
        console.error('[CLIENTES SISTEMA] Erro na requisição:', error);
        showError('Erro ao conectar com o servidor');
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
