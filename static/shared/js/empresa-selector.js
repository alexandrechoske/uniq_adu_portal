/**
 * 🏢 Componente: Seletor de Empresa
 * 
 * Componente reutilizável para filtrar dados por empresa controladora
 * no módulo RH (colaboradores, cargos, departamentos, vagas)
 * 
 * @example
 * // No HTML:
 * <div id="empresa-selector-container"></div>
 * 
 * // No JavaScript:
 * const selector = new EmpresaSelector('empresa-selector-container', (empresaId) => {
 *     console.log('Empresa selecionada:', empresaId);
 *     recarregarDados(empresaId);
 * });
 */

class EmpresaSelector {
    constructor(containerId, onChangeCallback) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error(`Elemento #${containerId} não encontrado`);
            return;
        }
        
        this.callback = onChangeCallback;
        this.empresas = [];
        this.selectedEmpresa = null;
        
        // Cores por empresa
        this.empresaCores = {
            'dc984b7c-3156-43f7-a1bf-f7a0b77db535': { nome: 'Unique', cor: '#1e40af' },    // Azul
            '2d025a9f-67a0-44a8-81a7-21fdea851c5d': { nome: 'DUX', cor: '#7c3aed' },       // Roxo
            '39abaad6-39d9-48e8-91b8-d6190df93c82': { nome: 'OnSet', cor: '#059669' },    // Verde
            '9069b93d-9bbd-4ae5-b28f-234c77fcd4ce': { nome: 'Cercargo', cor: '#dc2626' }  // Vermelho
        };
        
        this.init();
    }
    
    /**
     * Inicializa o componente
     */
    async init() {
        try {
            await this.loadEmpresas();
            this.loadFromStorage();
            this.render();
        } catch (error) {
            console.error('Erro ao inicializar seletor de empresa:', error);
            this.renderError();
        }
    }
    
    /**
     * Carrega lista de empresas da API
     */
    async loadEmpresas() {
        const response = await fetch('/rh/colaboradores/api/empresas-controladoras');
        const data = await response.json();
        
        if (!data.success) {
            throw new Error('Erro ao carregar empresas');
        }
        
        this.empresas = data.data;
        
        // Se não há empresa selecionada, seleciona a primeira (Unique)
        if (!this.selectedEmpresa && this.empresas.length > 0) {
            // Buscar Unique como padrão
            const unique = this.empresas.find(e => e.nome === 'Unique');
            this.selectedEmpresa = unique ? unique.id : this.empresas[0].id;
        }
    }
    
    /**
     * Carrega empresa selecionada do localStorage
     */
    loadFromStorage() {
        const stored = localStorage.getItem('rh_selected_empresa_id');
        if (stored) {
            this.selectedEmpresa = stored;
        }
    }
    
    /**
     * Salva empresa selecionada no localStorage
     */
    saveToStorage(empresaId) {
        localStorage.setItem('rh_selected_empresa_id', empresaId);
    }
    
    /**
     * Renderiza o componente
     */
    render() {
        const empresaAtual = this.empresas.find(e => e.id === this.selectedEmpresa);
        const corAtual = this.empresaCores[this.selectedEmpresa];
        
        const html = `
            <div class="empresa-selector-wrapper">
                <label class="empresa-selector-label">
                    <i class="fas fa-building"></i> Empresa:
                </label>
                <div class="empresa-selector-dropdown">
                    <button class="empresa-selector-btn" id="empresa-selector-btn">
                        <span class="empresa-badge" style="background-color: ${corAtual.cor}">
                            ${empresaAtual.nome}
                        </span>
                        <i class="fas fa-chevron-down"></i>
                    </button>
                    <div class="empresa-selector-menu" id="empresa-selector-menu">
                        ${this.empresas.map(empresa => {
                            const cor = this.empresaCores[empresa.id];
                            const isSelected = empresa.id === this.selectedEmpresa;
                            return `
                                <button 
                                    class="empresa-selector-item ${isSelected ? 'selected' : ''}"
                                    data-empresa-id="${empresa.id}"
                                    data-empresa-nome="${empresa.nome}"
                                >
                                    <span class="empresa-badge" style="background-color: ${cor.cor}">
                                        ${empresa.nome}
                                    </span>
                                    ${isSelected ? '<i class="fas fa-check"></i>' : ''}
                                </button>
                            `;
                        }).join('')}
                    </div>
                </div>
            </div>
        `;
        
        this.container.innerHTML = html;
        this.attachEvents();
    }
    
    /**
     * Renderiza mensagem de erro
     */
    renderError() {
        this.container.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle"></i>
                Erro ao carregar seletor de empresas
            </div>
        `;
    }
    
    /**
     * Anexa event listeners
     */
    attachEvents() {
        const btn = document.getElementById('empresa-selector-btn');
        const menu = document.getElementById('empresa-selector-menu');
        const items = menu.querySelectorAll('.empresa-selector-item');
        
        // Toggle menu
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            menu.classList.toggle('show');
        });
        
        // Fechar ao clicar fora
        document.addEventListener('click', () => {
            menu.classList.remove('show');
        });
        
        // Selecionar empresa
        items.forEach(item => {
            item.addEventListener('click', (e) => {
                e.stopPropagation();
                const empresaId = item.dataset.empresaId;
                const empresaNome = item.dataset.empresaNome;
                this.onChange(empresaId, empresaNome);
                menu.classList.remove('show');
            });
        });
    }
    
    /**
     * Handler de mudança de empresa
     */
    onChange(empresaId, empresaNome) {
        if (empresaId === this.selectedEmpresa) return;
        
        this.selectedEmpresa = empresaId;
        this.saveToStorage(empresaId);
        this.render();
        
        if (this.callback) {
            this.callback(empresaId, empresaNome);
        }
    }
    
    /**
     * Retorna empresa selecionada
     */
    getSelectedEmpresa() {
        return this.selectedEmpresa;
    }
    
    /**
     * Define empresa selecionada programaticamente
     */
    setSelectedEmpresa(empresaId) {
        this.onChange(empresaId);
    }
}

// Exportar para uso global
window.EmpresaSelector = EmpresaSelector;
