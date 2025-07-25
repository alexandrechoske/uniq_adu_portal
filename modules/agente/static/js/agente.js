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
    
    // Verifica se é número brasileiro (código 55)
    if (cleaned.length === 13 && cleaned.startsWith('55')) {
        return { valid: true, formatted: cleaned };
    }
    
    // Se tem 11 dígitos, assume que é brasileiro sem código do país
    if (cleaned.length === 11) {
        return { valid: true, formatted: '55' + cleaned };
    }
    
    // Aceita outros formatos
    return { valid: true, formatted: cleaned };
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
    const button = document.getElementById('btn-add-numero');
    const numero = input.value.trim();
    
    if (!numero) {
        toast.warning('Campo obrigatório', 'Por favor, informe um número de WhatsApp');
        input.focus();
        return;
    }
    
    const validation = validatePhoneNumber(numero);
    if (!validation.valid) {
        toast.error('Número inválido', validation.message);
        input.focus();
        return;
    }
    
    setButtonLoading(button, true);
    
    fetch('/agente/ajax/add-numero', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ numero: validation.formatted })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            toast.success('Sucesso!', data.message || 'Número adicionado com sucesso');
            input.value = '';
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

function removeNumber(numero) {
    if (!confirm(`Tem certeza que deseja remover o número ${numero}?`)) {
        return;
    }
    
    const button = document.querySelector(`[data-numero="${numero}"]`);
    if (button) setButtonLoading(button, true);
    
    fetch('/agente/ajax/remove-numero', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ numero })
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
});