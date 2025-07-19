// Sistema de gerenciamento de formulários de usuários
document.addEventListener('DOMContentLoaded', function() {
    console.log('[DEBUG] Inicializando formulário de usuários');

    // === ELEMENTOS DOM ===
    const form = document.getElementById('userForm');
    const roleSelect = document.getElementById('role');
    const empresasSection = document.getElementById('empresas-section');
    const empresasGrid = document.getElementById('empresas-grid');
    const loadEmpresasBtn = document.getElementById('load-empresas-btn');
    
    // Estado do formulário
    let empresasLoaded = false;
    let selectedEmpresas = new Set();

    // === INICIALIZAÇÃO ===
    init();

    function init() {
        setupEventListeners();
        
        // Se estamos editando um usuário cliente, carregar empresas automaticamente
        if (roleSelect && roleSelect.value === 'cliente_unique') {
            showEmpresasSection();
            loadEmpresas();
        }
        
        // Carregar empresas selecionadas se estiver editando
        loadSelectedEmpresas();
    }

    function setupEventListeners() {
        // Mudança de role
        if (roleSelect) {
            roleSelect.addEventListener('change', handleRoleChange);
        }

        // Carregar empresas
        if (loadEmpresasBtn) {
            loadEmpresasBtn.addEventListener('click', loadEmpresas);
        }

        // Envio do formulário
        if (form) {
            form.addEventListener('submit', handleFormSubmit);
        }

        // Validação em tempo real
        setupRealTimeValidation();
    }

    // === GERENCIAMENTO DE ROLE ===
    function handleRoleChange() {
        const role = roleSelect.value;
        console.log('[DEBUG] Role alterada para:', role);

        if (role === 'cliente_unique') {
            showEmpresasSection();
            if (!empresasLoaded) {
                loadEmpresas();
            }
        } else {
            hideEmpresasSection();
            selectedEmpresas.clear();
        }
    }

    function showEmpresasSection() {
        if (empresasSection) {
            empresasSection.style.display = 'block';
            empresasSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }

    function hideEmpresasSection() {
        if (empresasSection) {
            empresasSection.style.display = 'none';
        }
    }

    // === GERENCIAMENTO DE EMPRESAS ===
    async function loadEmpresas() {
        if (empresasLoaded) {
            console.log('[DEBUG] Empresas já carregadas');
            return;
        }

        console.log('[DEBUG] Carregando lista de empresas');
        
        if (loadEmpresasBtn) {
            const originalText = loadEmpresasBtn.innerHTML;
            loadEmpresasBtn.innerHTML = '<i class="mdi mdi-loading mdi-spin"></i> Carregando...';
            loadEmpresasBtn.disabled = true;
        }

        showLoadingState();

        try {
            const response = await fetch('/usuarios/api/empresas');
            const data = await response.json();

            if (data.success && data.empresas) {
                renderEmpresas(data.empresas);
                empresasLoaded = true;
                console.log('[DEBUG] Empresas carregadas:', data.empresas.length);
            } else {
                showErrorState(data.error || 'Erro ao carregar empresas');
            }
        } catch (error) {
            console.error('[DEBUG] Erro ao carregar empresas:', error);
            showErrorState('Erro de conexão ao carregar empresas');
        } finally {
            if (loadEmpresasBtn) {
                loadEmpresasBtn.innerHTML = '<i class="mdi mdi-refresh"></i> Recarregar';
                loadEmpresasBtn.disabled = false;
            }
        }
    }

    function renderEmpresas(empresas) {
        if (!empresasGrid) return;

        if (empresas.length === 0) {
            empresasGrid.innerHTML = '<div class="empresas-empty">Nenhuma empresa encontrada</div>';
            return;
        }

        empresasGrid.innerHTML = empresas.map(empresa => `
            <div class="empresa-option">
                <input type="checkbox" 
                       class="empresa-checkbox" 
                       id="empresa-${empresa.cnpj}" 
                       value="${empresa.cnpj}"
                       ${selectedEmpresas.has(empresa.cnpj) ? 'checked' : ''}>
                <label for="empresa-${empresa.cnpj}" class="empresa-info">
                    <div class="empresa-cnpj">${empresa.cnpj}</div>
                    <div class="empresa-razao">${empresa.razao_social}</div>
                </label>
            </div>
        `).join('');

        // Adicionar event listeners aos checkboxes
        empresasGrid.querySelectorAll('.empresa-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', handleEmpresaSelection);
        });
    }

    function handleEmpresaSelection(event) {
        const cnpj = event.target.value;
        const isChecked = event.target.checked;

        if (isChecked) {
            selectedEmpresas.add(cnpj);
            console.log('[DEBUG] Empresa selecionada:', cnpj);
        } else {
            selectedEmpresas.delete(cnpj);
            console.log('[DEBUG] Empresa desmarcada:', cnpj);
        }

        console.log('[DEBUG] Empresas selecionadas:', Array.from(selectedEmpresas));
    }

    function showLoadingState() {
        if (empresasGrid) {
            empresasGrid.innerHTML = `
                <div class="empresas-loading">
                    <i class="mdi mdi-loading mdi-spin" style="font-size: 1.5rem; margin-bottom: 0.5rem;"></i>
                    <div>Carregando empresas...</div>
                </div>
            `;
        }
    }

    function showErrorState(message) {
        if (empresasGrid) {
            empresasGrid.innerHTML = `
                <div class="empresas-empty">
                    <i class="mdi mdi-alert-circle" style="color: var(--color-danger); margin-bottom: 0.5rem;"></i>
                    <div>${message}</div>
                </div>
            `;
        }
    }

    // === CARREGAR EMPRESAS SELECIONADAS ===
    function loadSelectedEmpresas() {
        const userId = form?.dataset?.userId;
        if (!userId) return;

        console.log('[DEBUG] Carregando empresas selecionadas para usuário:', userId);

        fetch(`/usuarios/${userId}/empresas`)
            .then(response => response.json())
            .then(data => {
                if (data.success && data.empresas) {
                    selectedEmpresas = new Set(data.empresas);
                    console.log('[DEBUG] Empresas pré-selecionadas:', Array.from(selectedEmpresas));
                    
                    // Marcar checkboxes se já estão renderizados
                    selectedEmpresas.forEach(cnpj => {
                        const checkbox = document.getElementById(`empresa-${cnpj}`);
                        if (checkbox) {
                            checkbox.checked = true;
                        }
                    });
                }
            })
            .catch(error => {
                console.error('[DEBUG] Erro ao carregar empresas selecionadas:', error);
            });
    }

    // === ENVIO DO FORMULÁRIO ===
    async function handleFormSubmit(event) {
        console.log('[DEBUG] Enviando formulário');

        // Se for cliente_unique, salvar empresas associadas
        if (roleSelect?.value === 'cliente_unique' && selectedEmpresas.size > 0) {
            event.preventDefault();
            
            showFormLoading(true);
            
            try {
                // Primeiro, enviar o formulário de usuário
                const formData = new FormData(form);
                const response = await fetch(form.action, {
                    method: form.method,
                    body: formData
                });

                if (response.ok) {
                    // Se o usuário foi salvo com sucesso, associar empresas
                    const userId = form.dataset.userId || await extractUserIdFromResponse(response);
                    
                    if (userId) {
                        await saveEmpresasAssociation(userId);
                    }
                    
                    // Redirecionar para a lista de usuários
                    window.location.href = '/usuarios/';
                } else {
                    throw new Error('Erro ao salvar usuário');
                }
            } catch (error) {
                console.error('[DEBUG] Erro ao enviar formulário:', error);
                showNotification('Erro ao salvar usuário', 'error');
                showFormLoading(false);
            }
        }
    }

    async function saveEmpresasAssociation(userId) {
        console.log('[DEBUG] Salvando associação de empresas para usuário:', userId);
        
        const empresasList = Array.from(selectedEmpresas);
        
        const response = await fetch(`/usuarios/${userId}/empresas`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ empresas: empresasList })
        });

        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || 'Erro ao associar empresas');
        }
        
        console.log('[DEBUG] Empresas associadas com sucesso');
    }

    function showFormLoading(loading) {
        const submitButton = form?.querySelector('button[type="submit"]');
        if (!submitButton) return;

        if (loading) {
            submitButton.disabled = true;
            submitButton.innerHTML = '<i class="mdi mdi-loading mdi-spin"></i> Salvando...';
        } else {
            submitButton.disabled = false;
            submitButton.innerHTML = '<i class="mdi mdi-check"></i> Salvar';
        }
    }

    // === VALIDAÇÃO ===
    function setupRealTimeValidation() {
        // Validação de email
        const emailInput = document.getElementById('email');
        if (emailInput) {
            emailInput.addEventListener('blur', validateEmail);
            emailInput.addEventListener('input', debounce(validateEmail, 500));
        }

        // Validação de nome
        const nameInput = document.getElementById('name');
        if (nameInput) {
            nameInput.addEventListener('blur', validateName);
        }
    }

    function validateEmail() {
        const emailInput = document.getElementById('email');
        if (!emailInput) return;

        const email = emailInput.value.trim();
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

        if (email && !emailRegex.test(email)) {
            showFieldError(emailInput, 'Formato de email inválido');
        } else {
            clearFieldError(emailInput);
        }
    }

    function validateName() {
        const nameInput = document.getElementById('name');
        if (!nameInput) return;

        const name = nameInput.value.trim();

        if (name.length < 2) {
            showFieldError(nameInput, 'Nome deve ter pelo menos 2 caracteres');
        } else {
            clearFieldError(nameInput);
        }
    }

    function showFieldError(input, message) {
        input.style.borderColor = 'var(--color-danger)';
        
        let errorElement = input.parentNode.querySelector('.field-error');
        if (!errorElement) {
            errorElement = document.createElement('div');
            errorElement.className = 'field-error';
            errorElement.style.cssText = `
                color: var(--color-danger);
                font-size: 0.75rem;
                margin-top: 0.25rem;
            `;
            input.parentNode.appendChild(errorElement);
        }
        
        errorElement.textContent = message;
    }

    function clearFieldError(input) {
        input.style.borderColor = '';
        
        const errorElement = input.parentNode.querySelector('.field-error');
        if (errorElement) {
            errorElement.remove();
        }
    }

    // === UTILITÁRIOS ===
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    function showNotification(message, type = 'info') {
        // Implementação simples de notificação
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 20px;
            border-radius: 8px;
            color: white;
            font-weight: 500;
            z-index: 9999;
            animation: slideInRight 0.3s ease;
        `;
        
        const colors = {
            info: '#3b82f6',
            success: '#10b981',
            warning: '#f59e0b',
            error: '#ef4444'
        };
        
        notification.style.background = colors[type] || colors.info;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            if (notification.parentNode) {
                notification.style.animation = 'slideOutRight 0.3s ease';
                setTimeout(() => notification.remove(), 300);
            }
        }, 3000);
    }

    async function extractUserIdFromResponse(response) {
        // Tentar extrair ID do usuário da resposta ou redirecionamento
        // Implementação simplificada - pode precisar ser ajustada conforme a API
        const text = await response.text();
        const match = text.match(/user_id['":][\s]*['"]([^'"]+)['"]/);
        return match ? match[1] : null;
    }

    console.log('[DEBUG] Formulário de usuários inicializado com sucesso');
});
