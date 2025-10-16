/**
 * ARMAZENAGEM KINGSPAN - Gerenciamento de Modal e API
 * Funcionalidades para editar dados complementares de armazenagem para processos Kingspan
 */

const ArmazenagemKingspan = {
    // Estado do modal
    isOpen: false,
    currentRefUnique: null,
    hasKingspanAccess: false,
    canEdit: false,  // NOVO: controla se pode editar
    
    /**
     * Inicializar módulo
     */
    init() {
        console.log('[ARMAZENAGEM] ===== INICIALIZANDO MÓDULO =====');
        console.log('[ARMAZENAGEM] Timestamp:', new Date().toISOString());
        
        // Verificar acesso do usuário
        this.checkUserAccess();
        
        // Configurar event listeners
        this.setupEventListeners();
        
        console.log('[ARMAZENAGEM] ===== MÓDULO INICIALIZADO =====');
    },
    
    /**
     * Verificar se usuário tem acesso aos recursos Kingspan
     */
    async checkUserAccess() {
        console.log('[ARMAZENAGEM] ===== VERIFICANDO ACESSO DO USUÁRIO =====');
        
        try {
            console.log('[ARMAZENAGEM] Fazendo requisição para: /api/armazenagem/check-access');
            
            const response = await fetch('/api/armazenagem/check-access', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            console.log('[ARMAZENAGEM] Status da resposta:', response.status);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            console.log('[ARMAZENAGEM] ===== RESPOSTA DA API =====');
            console.log('[ARMAZENAGEM] Dados completos:', JSON.stringify(data, null, 2));
            console.log('[ARMAZENAGEM] has_access:', data.has_access);
            console.log('[ARMAZENAGEM] can_edit:', data.can_edit);
            console.log('[ARMAZENAGEM] can_view:', data.can_view);
            console.log('[ARMAZENAGEM] user_role:', data.user_role);
            console.log('[ARMAZENAGEM] perfil_principal:', data.perfil_principal);
            console.log('[ARMAZENAGEM] kingspan_cnpjs:', data.kingspan_cnpjs);
            console.log('[ARMAZENAGEM] ================================');
            
            this.hasKingspanAccess = data.has_access;
            this.canEdit = data.can_edit;
            
            // Log do resultado
            if (this.hasKingspanAccess) {
                console.log('[ARMAZENAGEM] ✅ USUÁRIO TEM ACESSO AOS DADOS KINGSPAN');
                console.log('[ARMAZENAGEM] Modo de edição:', this.canEdit ? 'HABILITADO' : 'SOMENTE LEITURA');
                console.log('[ARMAZENAGEM] Total de CNPJs Kingspan:', data.kingspan_cnpjs?.length || 0);
                
                // Adicionar flags globais para o dashboard usar
                window.hasKingspanAccess = true;
                window.canEditKingspan = this.canEdit;
                
                console.log('[ARMAZENAGEM] ✅ Ícone de bagagem será exibido em processos Kingspan');
            } else {
                console.warn('[ARMAZENAGEM] ⚠️ USUÁRIO NÃO TEM ACESSO - Funcionalidades desabilitadas');
                console.warn('[ARMAZENAGEM] Possíveis motivos:');
                console.warn('[ARMAZENAGEM] - Não é admin master/operação');
                console.warn('[ARMAZENAGEM] - Não tem CNPJs Kingspan associados');
                console.warn('[ARMAZENAGEM] - Não há processos Kingspan no sistema');
            }
            
        } catch (error) {
            console.error('[ARMAZENAGEM] ❌ ERRO ao verificar acesso:', error);
            console.error('[ARMAZENAGEM] Stack trace:', error.stack);
            this.hasKingspanAccess = false;
            this.canEdit = false;
        }
    },
    
    /**
     * Configurar event listeners
     */
    setupEventListeners() {
        // Fechar modal ao clicar no X
        document.addEventListener('click', (e) => {
            if (e.target.closest('.armazenagem-modal-close')) {
                this.closeModal();
            }
        });
        
        // Fechar modal ao clicar fora
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('armazenagem-modal-overlay')) {
                this.closeModal();
            }
        });
        
        // Fechar modal com ESC
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isOpen) {
                this.closeModal();
            }
        });
        
        // Botão de cancelar
        document.addEventListener('click', (e) => {
            if (e.target.id === 'armazenagem-btn-cancel') {
                this.closeModal();
            }
        });
        
        // Botão de salvar
        document.addEventListener('click', (e) => {
            if (e.target.id === 'armazenagem-btn-save') {
                this.saveArmazenagem();
            }
        });
        
        // Botão de deletar
        document.addEventListener('click', (e) => {
            if (e.target.id === 'armazenagem-btn-delete') {
                this.deleteArmazenagem();
            }
        });
        
        // Formatação automática de data ao digitar
        document.addEventListener('input', (e) => {
            if (e.target.classList.contains('armazenagem-date-input')) {
                this.formatDateInput(e.target);
            }
        });
        
        console.log('[ARMAZENAGEM] Event listeners configurados');
    },
    
    /**
     * Abrir modal de edição
     */
    async openModal(refUnique, processData = null) {
        console.log('[ARMAZENAGEM] Abrindo modal para ref_unique:', refUnique);
        
        this.currentRefUnique = refUnique;
        this.isOpen = true;
        
        // Preencher informações do processo
        const refUniqueEl = document.getElementById('armazenagem-ref-unique');
        if (refUniqueEl) refUniqueEl.textContent = refUnique;
        
        if (processData) {
            const importador = processData.importador || 'N/A';
            const container = processData.container || 'N/A';
            const infoEl = document.getElementById('armazenagem-process-info');
            if (infoEl) infoEl.textContent = `${importador} - ${container}`;
        }
        
        // Resetar formulário
        this.resetForm();
        
        // Mostrar loading
        this.showLoading(true);
        
        // Buscar dados existentes
        await this.loadArmazenagemData(refUnique);
        
        // Esconder loading
        this.showLoading(false);
        
        // Configurar modo read-only se necessário
        if (!this.canEdit) {
            this.setReadOnlyMode(true);
        }
        
        // Mostrar modal
        const overlay = document.querySelector('.armazenagem-modal-overlay');
        if (overlay) overlay.classList.add('active');
    },
    
    /**
     * Fechar modal
     */
    closeModal() {
        console.log('[ARMAZENAGEM] Fechando modal');
        
        this.isOpen = false;
        this.currentRefUnique = null;
        
        const overlay = document.querySelector('.armazenagem-modal-overlay');
        if (overlay) overlay.classList.remove('active');
        
        // Resetar formulário
        this.resetForm();
        this.hideMessages();
    },
    
    /**
     * Carregar dados de armazenagem existentes
     */
    async loadArmazenagemData(refUnique) {
        try {
            const response = await fetch(`/api/armazenagem/${refUnique}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            // 404 é esperado quando não há dados ainda - não é erro
            if (response.status === 404) {
                console.log('[ARMAZENAGEM] ℹ️ Nenhum dado cadastrado ainda - formulário vazio');
                (document.getElementById('armazenagem-btn-delete').style.display = 'none');
                return;
            }
            
            // Outros erros HTTP são problemas reais
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const result = await response.json();
            
            if (result.success && result.data) {
                console.log('[ARMAZENAGEM] ✅ Dados existentes carregados:', result.data);
                this.fillForm(result.data);
                
                // Mostrar botão de deletar se tem dados
                (document.getElementById('armazenagem-btn-delete').style.display = 'block');
            } else {
                console.log('[ARMAZENAGEM] ℹ️ Resposta vazia - formulário vazio');
                (document.getElementById('armazenagem-btn-delete').style.display = 'none');
            }
            
        } catch (error) {
            console.error('[ARMAZENAGEM] ❌ Erro ao carregar dados:', error);
            this.showError('Erro ao carregar dados de armazenagem. Tente novamente.');
            (document.getElementById('armazenagem-btn-delete').style.display = 'none');
        }
    },
    
    /**
     * Preencher formulário com dados existentes
     */
    fillForm(data) {
        (document.getElementById('armazenagem-data-desova').value = data.data_desova || '');
        (document.getElementById('armazenagem-limite-primeiro').value = data.limite_primeiro_periodo || '');
        (document.getElementById('armazenagem-limite-segundo').value = data.limite_segundo_periodo || '');
        (document.getElementById('armazenagem-dias-extras').value = data.dias_extras_armazenagem || '');
        (document.getElementById('armazenagem-valor-despesas').value = data.valor_despesas_extras || '');
    },
    
    /**
     * Resetar formulário
     */
    resetForm() {
        document.getElementById('armazenagem-form').reset();
        this.hideMessages();
    },
    
    /**
     * Configurar modo read-only
     */
    setReadOnlyMode(readOnly) {
        if (readOnly) {
            console.log('[ARMAZENAGEM] Modo somente leitura ativado');
            
            // Desabilitar todos os inputs
            document.querySelectorAll('#armazenagem-form input').forEach(el => el.disabled = true);
            
            // Esconder botões de edição
            (document.getElementById('armazenagem-btn-save').style.display = 'none');
            (document.getElementById('armazenagem-btn-delete').style.display = 'none');
            
            // Mudar texto do botão cancelar para "Fechar"
            (document.getElementById('armazenagem-btn-cancel').innerHTML = '<i class="mdi mdi-close"></i> Fechar');
            
            // Adicionar aviso de read-only
            if (!document.querySelector('.armazenagem-readonly-warning')) {
                document.querySelector('.armazenagem-modal-body').insertAdjacentHTML('afterbegin', `
                    <div class="armazenagem-info-box armazenagem-readonly-warning" style="background: #fff3cd; border-left-color: #ffc107;">
                        <h4 style="color: #856404;">
                            <i class="mdi mdi-eye"></i> Modo Somente Leitura
                        </h4>
                        <p style="color: #856404;">
                            Você pode visualizar os dados, mas não tem permissão para editá-los.
                            Somente analistas internos e administradores podem modificar estas informações.
                        </p>
                    </div>
                `);
            }
        } else {
            console.log('[ARMAZENAGEM] Modo edição ativado');
            
            // Habilitar inputs
            document.querySelectorAll('#armazenagem-form input').forEach(el => el.disabled = false);
            
            // Mostrar botões de edição
            (document.getElementById('armazenagem-btn-save').style.display = 'block');
            // Delete só aparece se tiver dados
            
            // Restaurar texto do botão cancelar
            (document.getElementById('armazenagem-btn-cancel').innerHTML = '<i class="mdi mdi-close"></i> Cancelar');
            
            // Remover aviso de read-only
            document.querySelectorAll('.armazenagem-readonly-warning').forEach(el => el.remove());
        }
    },
    
    /**
     * Salvar dados de armazenagem
     */
    async saveArmazenagem() {
        console.log('[ARMAZENAGEM] Salvando dados...');
        
        // Validar formulário
        if (!this.validateForm()) {
            return;
        }
        
        // Coletar dados do formulário
        const data = {
            data_desova: document.getElementById('armazenagem-data-desova').value || null,
            limite_primeiro_periodo: document.getElementById('armazenagem-limite-primeiro').value || null,
            limite_segundo_periodo: document.getElementById('armazenagem-limite-segundo').value || null,
            dias_extras_armazenagem: parseInt(document.getElementById('armazenagem-dias-extras').value) || null,
            valor_despesas_extras: parseFloat(document.getElementById('armazenagem-valor-despesas').value) || null
        };
        
        console.log('[ARMAZENAGEM] Dados a serem salvos:', data);
        
        // Mostrar loading
        this.showLoading(true);
        (document.getElementById('armazenagem-btn-save').disabled = true);
        
        try {
            const response = await fetch(`/api/armazenagem/${this.currentRefUnique}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });
            
            const result = await response.json();
            
            if (response.ok && result.success) {
                console.log('[ARMAZENAGEM] Dados salvos com sucesso');
                this.showSuccess('Dados de armazenagem salvos com sucesso!');
                
                // Atualizar tabela após 1 segundo e fechar modal
                setTimeout(() => {
                    this.closeModal();
                    // Recarregar dados do dashboard se disponível
                    if (typeof DashboardController !== 'undefined' && DashboardController.loadDashboardData) {
                        DashboardController.loadDashboardData(true);
                    }
                }, 1500);
                
            } else {
                throw new Error(result.error || 'Erro desconhecido ao salvar');
            }
            
        } catch (error) {
            console.error('[ARMAZENAGEM] Erro ao salvar:', error);
            this.showError(`Erro ao salvar dados: ${error.message}`);
        } finally {
            this.showLoading(false);
            (document.getElementById('armazenagem-btn-save').disabled = false);
        }
    },
    
    /**
     * Deletar dados de armazenagem
     */
    async deleteArmazenagem() {
        if (!confirm('Tem certeza que deseja deletar os dados de armazenagem deste processo?')) {
            return;
        }
        
        console.log('[ARMAZENAGEM] Deletando dados...');
        
        // Mostrar loading
        this.showLoading(true);
        (document.getElementById('armazenagem-btn-delete').disabled = true);
        
        try {
            const response = await fetch(`/api/armazenagem/${this.currentRefUnique}`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const result = await response.json();
            
            if (response.ok && result.success) {
                console.log('[ARMAZENAGEM] Dados deletados com sucesso');
                this.showSuccess('Dados de armazenagem deletados com sucesso!');
                
                // Fechar modal após 1 segundo
                setTimeout(() => {
                    this.closeModal();
                    // Recarregar dados do dashboard se disponível
                    if (typeof DashboardController !== 'undefined' && DashboardController.loadDashboardData) {
                        DashboardController.loadDashboardData(true);
                    }
                }, 1500);
                
            } else {
                throw new Error(result.error || 'Erro desconhecido ao deletar');
            }
            
        } catch (error) {
            console.error('[ARMAZENAGEM] Erro ao deletar:', error);
            this.showError(`Erro ao deletar dados: ${error.message}`);
        } finally {
            this.showLoading(false);
            (document.getElementById('armazenagem-btn-delete').disabled = false);
        }
    },
    
    /**
     * Validar formulário
     */
    validateForm() {
        this.hideMessages();
        
        // Validar datas (formato DD/MM/YYYY)
        const dateFields = [
            { id: '#armazenagem-data-desova', label: 'Data de Desova' },
            { id: '#armazenagem-limite-primeiro', label: 'Limite 1º Período' },
            { id: '#armazenagem-limite-segundo', label: 'Limite 2º Período' }
        ];
        
        for (const field of dateFields) {
            const value = document.querySelector(field.id).value;
            if (value && !this.isValidDate(value)) {
                this.showError(`${field.label}: formato de data inválido. Use DD/MM/AAAA`);
                document.querySelector(field.id).focus();
                return false;
            }
        }
        
        // Validar dias extras (deve ser número inteiro positivo)
        const diasExtras = document.getElementById('armazenagem-dias-extras').value;
        if (diasExtras && (isNaN(diasExtras) || parseInt(diasExtras) < 0)) {
            this.showError('Dias extras deve ser um número inteiro positivo');
            document.querySelector('#armazenagem-dias-extras').focus();
            return false;
        }
        
        // Validar valor despesas (deve ser número positivo)
        const valorDespesas = document.getElementById('armazenagem-valor-despesas').value;
        if (valorDespesas && (isNaN(valorDespesas) || parseFloat(valorDespesas) < 0)) {
            this.showError('Valor despesas extras deve ser um número positivo');
            document.querySelector('#armazenagem-valor-despesas').focus();
            return false;
        }
        
        return true;
    },
    
    /**
     * Validar formato de data DD/MM/YYYY
     */
    isValidDate(dateString) {
        const regex = /^(\d{2})\/(\d{2})\/(\d{4})$/;
        const match = dateString.match(regex);
        
        if (!match) return false;
        
        const day = parseInt(match[1]);
        const month = parseInt(match[2]);
        const year = parseInt(match[3]);
        
        if (month < 1 || month > 12) return false;
        if (day < 1 || day > 31) return false;
        if (year < 1900 || year > 2100) return false;
        
        return true;
    },
    
    /**
     * Formatar input de data automaticamente
     */
    formatDateInput(input) {
        let value = input.value.replace(/\D/g, ''); // Remove não-dígitos
        
        if (value.length >= 2) {
            value = value.substring(0, 2) + '/' + value.substring(2);
        }
        if (value.length >= 5) {
            value = value.substring(0, 5) + '/' + value.substring(5, 9);
        }
        
        input.value = value;
    },
    
    /**
     * Mostrar/esconder loading
     */
    showLoading(show) {
        if (show) {
            document.querySelectorAll('.armazenagem-loading').forEach(el => el.classList.add('active'));
            (document.getElementById('armazenagem-form').style.display = 'none');
        } else {
            document.querySelectorAll('.armazenagem-loading').forEach(el => el.classList.remove('active'));
            (document.getElementById('armazenagem-form').style.display = 'block');
        }
    },
    
    /**
     * Mostrar mensagem de erro
     */
    showError(message) {
        this.hideMessages();
        (function() { const el = document.querySelector('.armazenagem-error-message'); el.textContent = message; el.classList.add('active'); })();
    },
    
    /**
     * Mostrar mensagem de sucesso
     */
    showSuccess(message) {
        this.hideMessages();
        (function() { const el = document.querySelector('.armazenagem-success-message'); el.textContent = message; el.classList.add('active'); })();
    },
    
    /**
     * Esconder todas as mensagens
     */
    hideMessages() {
        document.querySelectorAll('.armazenagem-error-message, .armazenagem-success-message').forEach(el => el.classList.remove('active'));
    }
};

// Exportar para escopo global imediatamente (não precisa de jQuery)
window.ArmazenagemKingspan = ArmazenagemKingspan;

// Inicializar quando o DOM estiver pronto (sem jQuery)
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
        console.log('[ARMAZENAGEM] DOM pronto - inicializando...');
        ArmazenagemKingspan.init();
    });
} else {
    // DOM já está pronto
    console.log('[ARMAZENAGEM] DOM já carregado - inicializando imediatamente...');
    ArmazenagemKingspan.init();
}

