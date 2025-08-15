// === SISTEMA DE TOASTS ===
class ToastManager {
    constructor() {
        this.container = this.createContainer();
    }

    createContainer() {
        let container = document.querySelector('.toast-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'toast-container';
            document.body.appendChild(container);
        }
        return container;
    }

    show(type, title, message, duration = 5000) {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        const icons = {
            success: 'mdi-check-circle',
            error: 'mdi-alert-circle',
            warning: 'mdi-alert',
            info: 'mdi-information'
        };

        toast.innerHTML = `
            <i class="mdi ${icons[type]} toast-icon"></i>
            <div class="toast-content">
                <div class="toast-title">${title}</div>
                <div class="toast-message">${message}</div>
            </div>
            <button class="toast-close" onclick="this.parentElement.remove()">
                <i class="mdi mdi-close"></i>
            </button>
        `;

        this.container.appendChild(toast);

        // Animar entrada
        setTimeout(() => toast.classList.add('show'), 100);

        // Auto-remove
        if (duration > 0) {
            setTimeout(() => {
                toast.classList.remove('show');
                setTimeout(() => toast.remove(), 300);
            }, duration);
        }

        return toast;
    }

    success(title, message) {
        return this.show('success', title, message);
    }

    error(title, message) {
        return this.show('error', title, message);
    }

    warning(title, message) {
        return this.show('warning', title, message);
    }

    info(title, message) {
        return this.show('info', title, message);
    }
}

// Instância global do toast manager
const toast = new ToastManager();

// === VALIDAÇÕES ===
function validatePhoneNumber(number) {
    // Remove espaços e caracteres especiais
    const cleaned = number.replace(/\D/g, '');
    
    // Deve ter entre 10 e 15 dígitos
    if (cleaned.length < 10 || cleaned.length > 15) {
        return { valid: false, message: 'Número deve ter entre 10 e 15 dígitos' };
    }
    
    let formatted;
    
    // Se já tem 13 dígitos e começa com 55, mantém
    if (cleaned.length === 13 && cleaned.startsWith('55')) {
        formatted = `+${cleaned}`;
    }
    // Se tem 11 dígitos (formato brasileiro sem código de país)
    else if (cleaned.length === 11) {
        formatted = `+55${cleaned}`;
    }
    // Se tem 10 dígitos, verificar se é número Unique (3 no terceiro dígito) ou celular comum
    else if (cleaned.length === 10) {
        const thirdDigit = cleaned[2];
        
        // Números Unique com 3 no terceiro dígito (ex: 4733059070) - mantém 10 dígitos
        if (thirdDigit === '3') {
            formatted = `+55${cleaned}`;
        }
        // Celular comum sem o 9, adiciona o 9
        else if (['6', '7', '8', '9'].includes(thirdDigit)) {
            formatted = `+55${cleaned.slice(0, 2)}9${cleaned.slice(2)}`;
        }
        // Telefones fixos com 2, 4, 5 - mantém como está
        else if (['2', '4', '5'].includes(thirdDigit)) {
            formatted = `+55${cleaned}`;
        }
        else {
            return { valid: false, message: `Terceiro dígito inválido: ${thirdDigit}. Deve ser 2, 3, 4, 5, 6, 7, 8 ou 9` };
        }
    }
    // Se tem 12 dígitos mas não começa com 55, assume que é 55 + número
    else if (cleaned.length === 12) {
        formatted = `+55${cleaned.slice(2)}`;
    }
    // Se tem 14 dígitos e começa com 55, remove um dígito extra
    else if (cleaned.length === 14 && cleaned.startsWith('55')) {
        formatted = `+${cleaned.slice(0, 13)}`;
    }
    // Se tem 15 dígitos e começa com 55, só adiciona o +
    else if (cleaned.length === 15 && cleaned.startsWith('55')) {
        formatted = `+${cleaned}`;
    }
    // Se não conseguiu identificar o padrão, tenta formato mínimo +55
    else if (cleaned.length >= 10) {
        const phonePart = cleaned.slice(-11);
        formatted = `+55${phonePart}`;
    }
    else {
        return { valid: false, message: 'Formato de número inválido' };
    }
    
    // Validação final do formato - aceita 13 ou 14 caracteres para números Unique
    if (formatted.length !== 13 && formatted.length !== 14) {
        return { valid: false, message: `Formato inválido. Esperado: +5511999999999 (14 chars) ou +551133333333 (13 chars), recebido: ${formatted.length}` };
    }
    
    if (!formatted.startsWith('+55')) {
        return { valid: false, message: 'Número deve ser brasileiro (+55)' };
    }
    
    const phonePart = formatted.slice(3); // Remove +55
    
    // Validar número de dígitos baseado no terceiro dígito
    const thirdDigit = phonePart[2];
    const expectedLength = thirdDigit === '3' ? 10 : 11;
    
    if (phonePart.length !== expectedLength) {
        return { valid: false, message: `Parte do telefone deve ter ${expectedLength} dígitos para números iniciados com ${thirdDigit}, encontrado: ${phonePart.length}` };
    }
    
    const areaCode = phonePart.slice(0, 2);
    if (!/^\d{2}$/.test(areaCode) || parseInt(areaCode) < 11 || parseInt(areaCode) > 99) {
        return { valid: false, message: `Código de área inválido: ${areaCode}` };
    }
    
    if (!['2', '3', '4', '5', '9'].includes(thirdDigit)) {
        return { valid: false, message: `Primeiro dígito do telefone inválido: ${thirdDigit}` };
    }
    
    return { valid: true, formatted: formatted };
}

function setButtonLoading(button, loading) {
    if (loading) {
        button.classList.add('loading');
        button.disabled = true;
    } else {
        button.classList.remove('loading');
        button.disabled = false;
    }
}

// === GERENCIAMENTO DE NÚMEROS ===
function addNumber() {
    const input = document.getElementById('novo-numero');
    const nomeInput = document.getElementById('nome-contato');
    const tipoSelect = document.getElementById('tipo-numero');
    const button = document.getElementById('btn-add-numero');
    // Remove qualquer caractere não numérico para garantir padronização
    input.value = input.value.replace(/\D/g, '');
    const numero = input.value.trim();
    const nome = nomeInput ? nomeInput.value.trim() : '';
    const tipo = tipoSelect ? tipoSelect.value : 'pessoal';
    
    if (!numero) {
        toast.warning('Campo obrigatório', 'Por favor, informe um número de WhatsApp');
        input.focus();
        return;
    }
    
    if (!nome) {
        toast.warning('Campo obrigatório', 'Por favor, informe um nome para identificar este número');
        nomeInput.focus();
        return;
    }
    
    const validation = validatePhoneNumber(numero);
    if (!validation.valid) {
        toast.error('Número inválido', validation.message);
        input.focus();
        return;
    }
    console.log('[AGENTE FRONT] Número normalizado para envio:', validation.formatted);
    
    setButtonLoading(button, true);
    
    fetch('/agente/ajax/add-numero', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            numero: validation.formatted,
            nome: nome,
            tipo: tipo
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            toast.success('Sucesso!', data.message || 'Número adicionado com sucesso');
            input.value = '';
            if (nomeInput) nomeInput.value = '';
            if (tipoSelect) tipoSelect.value = 'pessoal';
            setTimeout(() => window.location.reload(), 1000);
        } else {
            toast.error('Erro', data.message || 'Não foi possível adicionar o número');
        }
    })
    .catch(error => {
        console.error('Erro:', error);
        toast.error('Erro de conexão', 'Verifique sua conexão e tente novamente');
    })
    .finally(() => {
        setButtonLoading(button, false);
    });
}

function removeNumber(numeroId, numeroDisplay) {
    if (!numeroDisplay) {
        const el = document.querySelector(`.number-item[data-numero-id="${numeroId}"] .number-text`);
        if (el) {
            numeroDisplay = el.textContent.replace('★ Principal','').trim();
        }
    }
    if (!confirm(`Tem certeza que deseja remover o número ${numeroDisplay}?`)) {
        return;
    }
    
    const button = document.querySelector(`[data-numero-id="${numeroId}"]`);
    if (button) setButtonLoading(button, true);
    
    fetch('/agente/ajax/remove-numero', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ numero_id: numeroId })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            toast.success('Sucesso!', data.message || 'Número removido com sucesso');
            setTimeout(() => window.location.reload(), 1000);
        } else {
            toast.error('Erro', data.message || 'Não foi possível remover o número');
        }
    })
    .catch(error => {
        console.error('Erro:', error);
        toast.error('Erro de conexão', 'Verifique sua conexão e tente novamente');
    })
    .finally(() => {
        if (button) setButtonLoading(button, false);
    });
}

function setPrincipal(numeroId, numeroDisplay) {
    if (!numeroDisplay) {
        const el = document.querySelector(`.number-item[data-numero-id="${numeroId}"] .number-text`);
        if (el) numeroDisplay = el.textContent.replace('★ Principal','').trim();
    }
    if (!confirm(`Definir ${numeroDisplay} como número principal?`)) {
        return;
    }
    
    const button = document.querySelector(`[data-principal-id="${numeroId}"]`);
    if (button) setButtonLoading(button, true);
    
    fetch('/agente/ajax/set-principal', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ numero_id: numeroId })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            toast.success('Sucesso!', data.message || 'Número principal atualizado');
            setTimeout(() => window.location.reload(), 1000);
        } else {
            toast.error('Erro', data.message || 'Não foi possível definir como principal');
        }
    })
    .catch(error => {
        console.error('Erro:', error);
        toast.error('Erro de conexão', 'Verifique sua conexão e tente novamente');
    })
    .finally(() => {
        if (button) setButtonLoading(button, false);
    });
}

// editNumber removido (função descontinuada; para alterar dados remova e adicione novamente)

function showAddNumberForm() {
    const placeholder = document.getElementById('add-number-placeholder');
    const addForm = document.getElementById('add-number-form');
    const addSection = document.querySelector('.add-number-section');
    
    if (placeholder && addForm) {
        placeholder.style.display = 'none';
        addForm.style.display = 'block';
        
        // Desabilitar o onclick do elemento pai para evitar conflitos
        if (addSection) {
            addSection.style.pointerEvents = 'none';
            addForm.style.pointerEvents = 'all';
        }
        
        // Focar no primeiro input
        const firstInput = addForm.querySelector('input');
        if (firstInput) {
            setTimeout(() => firstInput.focus(), 100);
        }
    }
}

function hideAddNumberForm() {
    const placeholder = document.getElementById('add-number-placeholder');
    const addForm = document.getElementById('add-number-form');
    const addSection = document.querySelector('.add-number-section');
    
    if (placeholder && addForm) {
        placeholder.style.display = 'block';
        addForm.style.display = 'none';
        
        // Reabilitar o onclick do elemento pai
        if (addSection) {
            addSection.style.pointerEvents = 'auto';
        }
        
        // Limpar campos
        const inputs = addForm.querySelectorAll('input');
        inputs.forEach(input => input.value = '');
        
        const selects = addForm.querySelectorAll('select');
        selects.forEach(select => select.selectedIndex = 0);
    }
}

function cancelSubscription() {
    if (!confirm('Tem certeza que deseja cancelar sua adesão ao Agente Unique?\n\nIsso removerá todos os seus números cadastrados e desativará o serviço.')) {
        return;
    }
    
    const button = document.getElementById('btn-cancelar-adesao');
    setButtonLoading(button, true);
    
    fetch('/agente/ajax/cancelar-adesao', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            toast.success('Adesão cancelada', data.message || 'Sua adesão foi cancelada com sucesso');
            setTimeout(() => window.location.reload(), 1500);
        } else {
            toast.error('Erro', data.message || 'Não foi possível cancelar a adesão');
        }
    })
    .catch(error => {
        console.error('Erro:', error);
        toast.error('Erro de conexão', 'Verifique sua conexão e tente novamente');
    })
    .finally(() => {
        setButtonLoading(button, false);
    });
}

// === VALIDAÇÃO EM TEMPO REAL ===
function setupFormValidation() {
    const numberInput = document.getElementById('numero_whatsapp');
    const termsCheckbox = document.getElementById('aceite_terms');
    const submitButton = document.getElementById('btn-ativar-agente');
    
    if (numberInput) {
        numberInput.addEventListener('input', function() {
            // Sanitiza removendo tudo que não seja número
            const original = this.value;
            const digits = original.replace(/\D/g, '');
            if (original !== digits) {
                this.value = digits;
            }
            const validation = validatePhoneNumber(this.value);
            const feedback = this.parentElement.querySelector('.form-feedback');
            if (feedback) feedback.remove();
            if (this.value.trim() && !validation.valid) {
                const feedbackDiv = document.createElement('div');
                feedbackDiv.className = 'form-feedback error';
                feedbackDiv.innerHTML = `<i class="mdi mdi-alert-circle"></i> ${validation.message}`;
                this.parentElement.appendChild(feedbackDiv);
            }
        });
    }
    
    if (submitButton) {
        const form = submitButton.closest('form');
        if (form) {
            form.addEventListener('submit', function(e) {
                const numero = numberInput?.value.trim();
                const aceite = termsCheckbox?.checked;
                
                console.log('[AGENTE FRONT] Submit do formulário!');
                console.log('[AGENTE FRONT] Número:', numero);
                console.log('[AGENTE FRONT] Aceite termos:', aceite);
                
                if (numero) {
                    const validation = validatePhoneNumber(numero);
                    if (!validation.valid) {
                        e.preventDefault();
                        toast.error('Número inválido', validation.message);
                        numberInput.focus();
                        return false;
                    }
                    // Substitui campo pelo número formatado padronizado +55 antes do submit
                    numberInput.value = validation.formatted.replace(/\D/g,''); // backend deve reformatar para +55
                    console.log('[AGENTE FRONT] Enviando número normalizado (apenas dígitos):', numberInput.value);
                }
                
                setButtonLoading(submitButton, true);
                
                // Permitir submit para ver logs do backend
                setTimeout(() => {
                    if (submitButton) setButtonLoading(submitButton, false);
                }, 3000);
            });
        }
    }
}

// === INICIALIZAÇÃO ===
document.addEventListener('DOMContentLoaded', function() {
    setupFormValidation();
    
    // Verificar se há mensagens flash para mostrar como toast
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(msg => {
        const type = msg.classList.contains('success') ? 'success' : 
                    msg.classList.contains('error') ? 'error' : 
                    msg.classList.contains('warning') ? 'warning' : 'info';
        
        toast.show(type, 'Sistema', msg.textContent.trim());
        msg.remove();
    });
    
    // Permitir adicionar número com Enter
    const newNumberInput = document.getElementById('novo-numero');
    if (newNumberInput) {
        newNumberInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                addNumber();
            }
        });
    }

    // Inicializar funcionalidades administrativas se necessário
    if (document.querySelector('.stats-section') && document.querySelector('.admin-filters-card')) {
        initAdminPanel();
    }
});

// === FUNCIONALIDADES ADMINISTRATIVAS ===

let adminData = {
    users: [],
    filteredUsers: [],
    stats: {}
};

function initAdminPanel() {
    console.log('[ADMIN] Inicializando painel administrativo...');
    
    // Carregar dados iniciais
    loadAdminData();
    
    // Configurar filtros com debounce
    const searchInput = document.getElementById('search-users');
    if (searchInput) {
        let searchTimeout;
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(filterUsers, 300);
        });
    }
    
    // Configurar outros filtros
    const statusFilter = document.getElementById('status-filter');
    const companyFilter = document.getElementById('company-filter');
    
    if (statusFilter) statusFilter.addEventListener('change', filterUsers);
    if (companyFilter) companyFilter.addEventListener('change', filterUsers);
}

async function loadAdminData() {
    try {
        console.log('[ADMIN] Carregando dados...');
        
        const response = await fetch('/agente/api/admin/users-summary', {
            headers: {
                'Content-Type': 'application/json',
                'X-API-Key': 'uniq_api_2025_dev_bypass_key'
            }
        });
        const data = await response.json();
        
        if (data.success) {
            adminData.users = data.users;
            adminData.filteredUsers = data.users;
            adminData.stats = data.stats;
            
            console.log('[ADMIN] Dados carregados:', {
                users: adminData.users.length,
                stats: adminData.stats
            });
            
            // Atualizar interface
            updateUsersList();
            updateStatsDisplay();
            populateCompanyFilter();
        } else {
            toast.error('Erro', data.message || 'Falha ao carregar dados');
        }
    } catch (error) {
        console.error('[ADMIN] Erro ao carregar dados:', error);
        toast.error('Erro de conexão', 'Verifique sua conexão e tente novamente');
    }
}

function filterUsers() {
    const search = document.getElementById('search-users')?.value.toLowerCase() || '';
    const status = document.getElementById('status-filter')?.value || 'all';
    const company = document.getElementById('company-filter')?.value || '';
    
    console.log('[ADMIN] Filtrando usuários:', { search, status, company });
    
    adminData.filteredUsers = adminData.users.filter(user => {
        // Filtro de busca
        if (search) {
            const searchText = `${user.nome} ${user.email}`.toLowerCase();
            if (!searchText.includes(search)) return false;
        }
        
        // Filtro de status
        if (status === 'active' && !user.usuario_ativo) return false;
        if (status === 'inactive' && user.usuario_ativo) return false;
        
        // Filtro de empresa
        if (company) {
            const hasCompany = user.empresas.some(empresa => {
                const cnpj = typeof empresa === 'string' ? empresa : empresa.cnpj;
                return cnpj.includes(company);
            });
            if (!hasCompany) return false;
        }
        
        return true;
    });
    
    updateUsersList();
}

function updateUsersList() {
    const tableBody = document.getElementById('users-table-body');
    if (!tableBody) {
        console.error('[ADMIN] Elemento users-table-body não encontrado');
        return;
    }
    
    if (adminData.filteredUsers.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="5" class="empty-state">
                    <i class="mdi mdi-account-off"></i>
                    <h3>Nenhum usuário encontrado</h3>
                    <p>Ajuste os filtros para ver mais resultados.</p>
                </td>
            </tr>
        `;
        return;
    }
    
    tableBody.innerHTML = adminData.filteredUsers.map(user => `
        <tr data-user-id="${user.user_id}">
            <td class="user-info-cell">
                <div class="user-name-table">${user.nome || 'Nome não informado'}</div>
                <div class="user-email-table">${user.email}</div>
            </td>
            <td class="numbers-cell">
                <div class="numbers-list-table">
                    ${user.numeros && user.numeros.length > 0 ? 
                        user.numeros.map(numero => `<span class="number-badge">${numero}</span>`).join('') : 
                        '<span style="color: var(--color-text-muted); font-size: 0.75rem;">Nenhum número</span>'
                    }
                </div>
                <div class="add-number-inline" style="display: none;">
                    <input type="text" class="form-input add-number-input" placeholder="Novo número" id="new-number-${user.user_id}">
                    <button class="btn btn-success btn-table" onclick="adminAddNumber('${user.user_id}')">
                        <i class="mdi mdi-plus"></i>
                    </button>
                </div>
            </td>
            <td class="companies-cell">
                ${user.empresas && user.empresas.length > 0 ? 
                    `<span class="companies-count">${user.empresas.length} empresa(s)</span>` : 
                    '<span style="color: var(--color-text-muted); font-size: 0.75rem;">Nenhuma empresa</span>'
                }
            </td>
            <td class="status-cell">
                ${user.usuario_ativo ? 
                    '<span class="status-badge status-active"><i class="mdi mdi-check-circle"></i> Ativo</span>' : 
                    '<span class="status-badge status-inactive"><i class="mdi mdi-close-circle"></i> Inativo</span>'
                }
            </td>
            <td class="actions-cell">
                <button class="btn btn-primary btn-table" onclick="showUserDetails('${user.user_id}')">
                    <i class="mdi mdi-eye"></i>
                </button>
                ${user.usuario_ativo ? 
                    `<button class="btn btn-warning btn-table" onclick="adminToggleUser('${user.user_id}', false)">
                        <i class="mdi mdi-pause"></i>
                    </button>` : 
                    `<button class="btn btn-success btn-table" onclick="adminToggleUser('${user.user_id}', true)">
                        <i class="mdi mdi-play"></i>
                    </button>`
                }
            </td>
        </tr>
    `).join('');
}

function updateStatsDisplay() {
    const stats = adminData.stats;
    
    console.log('[ADMIN] Atualizando estatísticas:', stats);
    
    // Atualizar os valores nas estatísticas usando data-stat
    const statMappings = {
        'total_users': stats.total_users || 0,
        'active_users': stats.active_users || 0,
        'total_numbers': stats.total_numbers || 0,
        'total_companies': stats.total_companies || 0
    };
    
    Object.entries(statMappings).forEach(([key, value]) => {
        const element = document.querySelector(`[data-stat="${key}"]`);
        if (element) {
            console.log(`[ADMIN] Atualizando ${key}: ${element.textContent} -> ${value}`);
            element.textContent = value;
        } else {
            console.warn(`[ADMIN] Elemento não encontrado para stat: ${key}`);
        }
    });
}

function populateCompanyFilter() {
    const companyFilter = document.getElementById('company-filter');
    if (!companyFilter) return;
    
    const companies = new Set();
    adminData.users.forEach(user => {
        user.empresas.forEach(empresa => {
            const cnpj = typeof empresa === 'string' ? empresa : empresa.cnpj;
            if (cnpj && cnpj !== 'N/A') companies.add(cnpj);
        });
    });
    
    // Limpar opções existentes (exceto a primeira)
    while (companyFilter.children.length > 1) {
        companyFilter.removeChild(companyFilter.lastChild);
    }
    
    // Adicionar opções de empresas
    Array.from(companies).sort().forEach(cnpj => {
        const option = document.createElement('option');
        option.value = cnpj;
        option.textContent = cnpj;
        companyFilter.appendChild(option);
    });
}

// === AÇÕES ADMINISTRATIVAS ===

async function adminToggleUser(userId, activate) {
    try {
        console.log(`[ADMIN] ${activate ? 'Ativando' : 'Desativando'} usuário:`, userId);
        
        const response = await fetch('/agente/admin/toggle-user', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'X-API-Key': 'uniq_api_2025_dev_bypass_key'
            },
            body: JSON.stringify({ 
                user_id: userId, 
                ativo: activate 
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            toast.success('Sucesso!', data.message);
            
            // Atualizar dados locais
            const user = adminData.users.find(u => u.user_id === userId);
            if (user) {
                user.usuario_ativo = activate;
                filterUsers(); // Reaplica filtros
                
                // Se o modal estiver aberto, atualizar ele também
                const modal = document.getElementById('user-details-modal');
                if (modal.classList.contains('show')) {
                    showUserDetails(userId);
                }
            }
        } else {
            toast.error('Erro', data.message);
        }
    } catch (error) {
        console.error('[ADMIN] Erro ao alterar status:', error);
        toast.error('Erro de conexão', 'Verifique sua conexão e tente novamente');
    }
}

async function adminAddNumber(userId) {
    try {
        const input = document.getElementById(`new-number-${userId}`);
    const nomeInput = document.getElementById(`new-nome-${userId}`);
    const tipoSelect = document.getElementById(`new-tipo-${userId}`);
    // Sanitiza
    input.value = input.value.replace(/\D/g, '');
    const numero = input.value.trim();
    const nome = nomeInput ? nomeInput.value.trim() : '';
    const tipo = tipoSelect ? tipoSelect.value : 'pessoal';
        
        if (!numero) {
            toast.warning('Campo obrigatório', 'Digite um número válido');
            input.focus();
            return;
        }
        
    if (!nome) {
            toast.warning('Campo obrigatório', 'Digite um nome para identificar o número');
            nomeInput.focus();
            return;
        }
        
        // Validar formato
        const validation = validatePhoneNumber(numero);
        if (!validation.valid) {
            toast.error('Número inválido', validation.message);
            input.focus();
            return;
        }
        
    console.log('[ADMIN] Adicionando número:', { userId, numero: validation.formatted, nome, tipo });
        
        const response = await fetch('/agente/admin/add-numero', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                user_id: userId, 
                numero: validation.formatted,
                nome: nome,
                tipo: tipo
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            toast.success('Sucesso!', data.message);
            input.value = '';
            if (nomeInput) nomeInput.value = '';
            if (tipoSelect) tipoSelect.value = 'pessoal';
            
            // Recarregar dados
            await loadAdminData();
        } else {
            toast.error('Erro', data.message);
        }
    } catch (error) {
        console.error('[ADMIN] Erro ao adicionar número:', error);
        toast.error('Erro de conexão', 'Verifique sua conexão e tente novamente');
    }
}

async function adminRemoveNumber(userId, numeroId, numeroDisplay) {
    if (!confirm(`Tem certeza que deseja remover o número ${numeroDisplay}?`)) {
        return;
    }
    
    try {
        console.log('[ADMIN] Removendo número:', { userId, numeroId, numeroDisplay });
        
        const response = await fetch('/agente/admin/remove-numero', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'X-API-Key': 'uniq_api_2025_dev_bypass_key'
            },
            body: JSON.stringify({ 
                user_id: userId, 
                numero_id: numeroId
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            toast.success('Sucesso!', data.message);
            
            // Recarregar dados
            await loadAdminData();
            
            // Se o modal estiver aberto, atualizar ele também
            const modal = document.getElementById('user-details-modal');
            if (modal && modal.classList.contains('show')) {
                showUserDetails(userId);
            }
        } else {
            toast.error('Erro', data.message);
        }
    } catch (error) {
        console.error('[ADMIN] Erro ao remover número:', error);
        toast.error('Erro de conexão', 'Verifique sua conexão e tente novamente');
    }
}

async function adminSetPrincipal(userId, numeroId, numeroDisplay) {
    if (!confirm(`Definir ${numeroDisplay} como número principal para este usuário?`)) {
        return;
    }
    
    try {
        console.log('[ADMIN] Definindo número principal:', { userId, numeroId, numeroDisplay });
        
        const response = await fetch('/agente/admin/set-principal', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'X-API-Key': 'uniq_api_2025_dev_bypass_key'
            },
            body: JSON.stringify({ 
                user_id: userId, 
                numero_id: numeroId
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            toast.success('Sucesso!', data.message);
            
            // Recarregar dados
            await loadAdminData();
            
            // Se o modal estiver aberto, atualizar ele também
            const modal = document.getElementById('user-details-modal');
            if (modal && modal.classList.contains('show')) {
                showUserDetails(userId);
            }
        } else {
            toast.error('Erro', data.message);
        }
    } catch (error) {
        console.error('[ADMIN] Erro ao definir número principal:', error);
        toast.error('Erro de conexão', 'Verifique sua conexão e tente novamente');
    }
}

function showUserDetails(userId) {
    const user = adminData.users.find(u => u.user_id === userId);
    if (!user) return;
    
    console.log('[ADMIN] Mostrando detalhes do usuário:', user);
    
    // Formatar data de criação
    const createdAt = user.created_at ? new Date(user.created_at).toLocaleString('pt-BR') : 'Não informado';
    const dataAceite = user.data_aceite ? new Date(user.data_aceite).toLocaleString('pt-BR') : 'Não informado';
    
    // Gerar HTML do modal
    const modalContent = `
        <!-- Informações Básicas -->
        <div class="detail-section">
            <div class="detail-section-title">
                <i class="mdi mdi-account"></i>
                Informações Básicas
            </div>
            <div class="detail-grid">
                <div class="detail-item">
                    <span class="detail-label">Nome</span>
                    <span class="detail-value">${user.nome || 'Não informado'}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Email</span>
                    <span class="detail-value">${user.email}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">ID do Usuário</span>
                    <span class="detail-value" style="font-family: monospace; font-size: 0.75rem;">${user.user_id}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Status</span>
                    <span class="detail-value">
                        ${user.usuario_ativo ? 
                            '<span style="color: var(--color-success);"><i class="mdi mdi-check-circle"></i> Ativo</span>' : 
                            '<span style="color: var(--color-danger);"><i class="mdi mdi-close-circle"></i> Inativo</span>'
                        }
                    </span>
                </div>
            </div>
        </div>

        <!-- Números WhatsApp -->
        <div class="detail-section">
            <div class="detail-section-title">
                <i class="mdi mdi-whatsapp"></i>
                Números WhatsApp (${user.numeros.length})
            </div>
            ${user.numeros.length > 0 ? `
                <div class="numbers-grid-modal">
                    ${user.numeros.map(numero => `
                        <div class="number-item-modal">
                            <span>${numero}</span>
                            <div class="number-actions-modal">
                                <button class="btn btn-danger btn-modal" onclick="adminRemoveNumber('${user.user_id}', '${numero}')" title="Remover número">
                                    <i class="mdi mdi-delete"></i>
                                </button>
                            </div>
                        </div>
                    `).join('')}
                </div>
                <div style="margin-top: var(--spacing-md);">
                    <div style="display: flex; gap: var(--spacing-sm); align-items: center;">
                        <input type="text" id="new-number-modal" class="form-input" placeholder="Novo número WhatsApp" style="flex: 1;">
                        <button class="btn btn-success btn-modal" onclick="adminAddNumberModal('${user.user_id}')">
                            <i class="mdi mdi-plus"></i> Adicionar
                        </button>
                    </div>
                </div>
            ` : `
                <p style="color: var(--color-text-muted); font-style: italic;">Nenhum número cadastrado</p>
                <div style="margin-top: var(--spacing-md);">
                    <div style="display: flex; gap: var(--spacing-sm); align-items: center;">
                        <input type="text" id="new-number-modal" class="form-input" placeholder="Primeiro número WhatsApp" style="flex: 1;">
                        <button class="btn btn-success btn-modal" onclick="adminAddNumberModal('${user.user_id}')">
                            <i class="mdi mdi-plus"></i> Adicionar
                        </button>
                    </div>
                </div>
            `}
        </div>

        <!-- Empresas -->
        <div class="detail-section">
            <div class="detail-section-title">
                <i class="mdi mdi-domain"></i>
                Empresas Vinculadas (${user.empresas.length})
            </div>
            ${user.empresas.length > 0 ? `
                <div class="companies-grid-modal">
                    ${user.empresas.map(empresa => `
                        <div class="company-item-modal">${typeof empresa === 'string' ? empresa : empresa.cnpj || empresa}</div>
                    `).join('')}
                </div>
            ` : `
                <p style="color: var(--color-text-muted); font-style: italic;">Nenhuma empresa vinculada</p>
            `}
        </div>

        <!-- Informações de Sistema -->
        <div class="detail-section">
            <div class="detail-section-title">
                <i class="mdi mdi-information"></i>
                Informações do Sistema
            </div>
            <div class="detail-grid">
                <div class="detail-item">
                    <span class="detail-label">Data de Cadastro</span>
                    <span class="detail-value">${createdAt}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Aceite dos Termos</span>
                    <span class="detail-value">
                        ${user.aceite_termos ? 
                            '<span style="color: var(--color-success);"><i class="mdi mdi-check"></i> Aceito</span>' : 
                            '<span style="color: var(--color-warning);"><i class="mdi mdi-clock"></i> Pendente</span>'
                        }
                    </span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Data Aceite Termos</span>
                    <span class="detail-value">${dataAceite}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Última Atividade</span>
                    <span class="detail-value">${user.last_activity || 'Não informado'}</span>
                </div>
            </div>
        </div>

        <!-- Ações -->
        <div class="modal-actions">
            <button class="btn ${user.usuario_ativo ? 'btn-warning' : 'btn-success'}" onclick="adminToggleUser('${user.user_id}', ${!user.usuario_ativo})">
                <i class="mdi mdi-${user.usuario_ativo ? 'pause' : 'play'}"></i>
                ${user.usuario_ativo ? 'Desativar' : 'Ativar'} Usuário
            </button>
            <button class="btn btn-info" onclick="refreshData(); closeUserDetailsModal();">
                <i class="mdi mdi-refresh"></i>
                Atualizar Dados
            </button>
        </div>
    `;
    
    // Inserir conteúdo no modal
    document.getElementById('modal-body-content').innerHTML = modalContent;
    
    // Mostrar modal
    const modal = document.getElementById('user-details-modal');
    modal.classList.add('show');
    
    // Fechar modal ao clicar fora
    modal.onclick = function(e) {
        if (e.target === modal) {
            closeUserDetailsModal();
        }
    };
}

function closeUserDetailsModal() {
    const modal = document.getElementById('user-details-modal');
    modal.classList.remove('show');
}

async function adminAddNumberModal(userId) {
    const input = document.getElementById('new-number-modal');
    input.value = input.value.replace(/\D/g, '');
    const numero = input.value.trim();
    
    if (!numero) {
        toast.warning('Aviso', 'Digite um número para adicionar');
        return;
    }
    
    try {
        const validation = validatePhoneNumber(numero);
        if(!validation.valid){
            toast.error('Número inválido', validation.message);
            return;
        }
        const response = await fetch('/agente/admin/add-numero', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-Key': 'uniq_api_2025_dev_bypass_key'
            },
            body: JSON.stringify({ user_id: userId, numero: validation.formatted })
        });
        
        const data = await response.json();
        
        if (data.success) {
            toast.success('Sucesso', data.message);
            input.value = '';
            // Recarregar dados e atualizar modal
            await loadAdminData();
            showUserDetails(userId);
        } else {
            toast.error('Erro', data.message);
        }
    } catch (error) {
        console.error('[ADMIN] Erro ao adicionar número:', error);
        toast.error('Erro', 'Erro de conexão ao adicionar número');
    }
}

function refreshData() {
    console.log('[ADMIN] Atualizando dados...');
    toast.info('Atualizando', 'Carregando dados mais recentes...');
    loadAdminData();
}

async function exportAllData() {
    try {
        console.log('[ADMIN] Exportando dados...');
        
        const userIds = adminData.filteredUsers.map(u => u.user_id);
        
        const response = await fetch('/agente/admin/bulk-actions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                action: 'export',
                user_ids: userIds
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Criar e baixar arquivo
            const blob = new Blob([JSON.stringify(data.data, null, 2)], 
                                 { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `agentes_export_${new Date().toISOString().split('T')[0]}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            
            toast.success('Exportação', 'Dados exportados com sucesso!');
        } else {
            toast.error('Erro', data.message);
        }
    } catch (error) {
        console.error('[ADMIN] Erro ao exportar:', error);
        toast.error('Erro de exportação', 'Falha ao exportar dados');
    }
}

// Função para mostrar/ocultar o formulário de adicionar número na tabela
function toggleAddNumberForm(userId) {
    const row = document.querySelector(`tr[data-user-id="${userId}"]`);
    if (!row) return;
    
    const addNumberDiv = row.querySelector('.add-number-inline');
    if (!addNumberDiv) return;
    
    const isVisible = addNumberDiv.style.display !== 'none';
    addNumberDiv.style.display = isVisible ? 'none' : 'flex';
    
    if (!isVisible) {
        const input = addNumberDiv.querySelector('input');
        if (input) input.focus();
    }
}

// Função para ações em massa (placeholder)
function showBulkActions() {
    toast.info('Em breve', 'Funcionalidade de ações em massa será implementada em breve.');
}

    function openTermsModal(){
        const m = document.getElementById('terms-modal');
        if(!m) return; 
        m.style.display='block';
        setTimeout(()=>m.classList.add('show'),10);
    }
    function closeTermsModal(){
        const m = document.getElementById('terms-modal');
        if(!m) return; 
        m.classList.remove('show');
        setTimeout(()=>m.style.display='none',250);
    }
    document.addEventListener('keydown', e=>{ if(e.key==='Escape'){ closeTermsModal(); }});