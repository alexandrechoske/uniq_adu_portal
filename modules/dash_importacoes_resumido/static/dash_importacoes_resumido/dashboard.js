// Dashboard Importações Resumido - JavaScript

class DashboardImportacoesResumido {
    constructor() {
        this.currentPage = 1;
        this.totalPages = 1;
        this.perPage = 10;
        this.isLoading = false;
        this.autoRefreshInterval = null;
        this.autoRefreshEnabled = true;
        this.autoRefreshTimer = 30000; // 30 segundos
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.loadData();
        this.startAutoRefresh();
        this.updateClock();
        
        // Atualizar relógio a cada minuto
        setInterval(() => this.updateClock(), 60000);
    }
    
    bindEvents() {
        // Botão de atualização manual
        document.getElementById('btn-refresh').addEventListener('click', () => {
            this.loadData();
        });
        
        // Checkbox de filtro
        document.getElementById('filtro-embarque').addEventListener('change', () => {
            this.currentPage = 1;
            this.loadData();
        });
        
        // Botões de paginação
        document.getElementById('btn-prev-page').addEventListener('click', () => {
            if (this.currentPage > 1) {
                this.currentPage--;
                this.loadData();
            }
        });
        
        document.getElementById('btn-next-page').addEventListener('click', () => {
            if (this.currentPage < this.totalPages) {
                this.currentPage++;
                this.loadData();
            }
        });
        
        // Pausar auto-refresh quando o usuário está interagindo
        document.addEventListener('click', () => {
            this.resetAutoRefresh();
        });
        
        document.addEventListener('keydown', () => {
            this.resetAutoRefresh();
        });
    }
    
    startAutoRefresh() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
        }
        
        this.autoRefreshInterval = setInterval(() => {
            if (this.autoRefreshEnabled && !this.isLoading) {
                this.loadData(true); // true = silent refresh
            }
        }, this.autoRefreshTimer);
    }
    
    resetAutoRefresh() {
        this.startAutoRefresh();
    }
    
    stopAutoRefresh() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
            this.autoRefreshInterval = null;
        }
    }
    
    showLoading() {
        const loadingOverlay = document.getElementById('loading-overlay');
        if (loadingOverlay) {
            loadingOverlay.style.display = 'flex';
        }
        this.isLoading = true;
    }
    
    hideLoading() {
        const loadingOverlay = document.getElementById('loading-overlay');
        if (loadingOverlay) {
            loadingOverlay.style.display = 'none';
        }
        this.isLoading = false;
    }
    
    updateClock() {
        const now = new Date();
        const time = now.toLocaleTimeString('pt-BR', { 
            hour: '2-digit', 
            minute: '2-digit',
            hour12: false 
        });
        
        const months = [
            'JANEIRO', 'FEVEREIRO', 'MARÇO', 'ABRIL', 'MAIO', 'JUNHO',
            'JULHO', 'AGOSTO', 'SETEMBRO', 'OUTUBRO', 'NOVEMBRO', 'DEZEMBRO'
        ];
        
        const day = now.getDate();
        const month = months[now.getMonth()];
        const date = `${day} ${month}`;
        
        document.getElementById('current-time').textContent = time;
        document.getElementById('current-date').textContent = date;
    }
    
    async loadData(silent = false) {
        if (this.isLoading) return;
        
        if (!silent) {
            this.showLoading();
        }
        
        try {
            const filtroEmbarque = document.getElementById('filtro-embarque').checked ? 'preenchida' : '';
            
            const params = new URLSearchParams({
                page: this.currentPage,
                per_page: this.perPage,
                filtro_embarque: filtroEmbarque
            });
            
            const response = await fetch(`/dash-importacoes-resumido/api/data?${params}`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                this.updateHeader(data.header);
                this.updateTable(data.data);
                this.updatePagination(data.pagination);
            } else {
                this.showError(data.error || 'Erro ao carregar dados');
            }
            
        } catch (error) {
            console.error('Erro ao carregar dados:', error);
            
            if (error.message.includes('404')) {
                this.showNoDataMessage();
            } else {
                this.showError('Erro ao carregar dados. Tente novamente.');
            }
        } finally {
            if (!silent) {
                this.hideLoading();
            }
        }
    }
    
    updateHeader(headerData) {
        // Atualizar métricas do cabeçalho
        document.getElementById('total-processos').textContent = 
            `TOTAL: ${headerData.total_processos} PROCESSOS`;
        
        document.getElementById('count-maritimo').textContent = headerData.count_maritimo || 0;
        document.getElementById('count-aereo').textContent = headerData.count_aereo || 0;
        document.getElementById('count-terrestre').textContent = headerData.count_terrestre || 0;
        
        // Atualizar cotações
        if (headerData.exchange_rates) {
            const dolarRate = headerData.exchange_rates.dolar;
            const euroRate = headerData.exchange_rates.euro;
            
            // Atualizar cotações no topo
            document.getElementById('dolar-rate-top').textContent = 
                dolarRate ? dolarRate.toFixed(4) : '-.----';
            document.getElementById('euro-rate-top').textContent = 
                euroRate ? euroRate.toFixed(4) : '-.----';
        }
    }
    
    updateTable(tableData) {
        const tbody = document.getElementById('table-body');
        tbody.innerHTML = '';
        
        if (!tableData || tableData.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="10" style="text-align: center; padding: 2rem; color: #6b7280;">
                        Nenhum dado encontrado
                    </td>
                </tr>
            `;
            return;
        }
        
        tableData.forEach(row => {
            const tr = document.createElement('tr');
            
            // Formatar data de embarque com cor condicional
            const dataEmbarqueFormatted = this.formatDataEmbarque(row.data_embarque);
            
            // Obter imagem do modal
            const modalImage = this.getModalImage(row.modal);
            
            tr.innerHTML = `
                <td>
                    <img src="${modalImage}" alt="Modal ${row.modal}" class="modal-icon">
                </td>
                <td>${row.numero || ''}</td>
                <td>${row.numero_di || ''}</td>
                <td>${row.ref_unique || ''}</td>
                <td>${row.ref_importador || ''}</td>
                <td>${dataEmbarqueFormatted}</td>
                <td>${row.data_chegada || ''}</td>
                <td>${row.data_registro || ''}</td>
                <td>
                    ${row.canal ? `<div class="canal-indicator" style="background-color: ${row.canal_color || '#9E9E9E'}"></div>` : ''}
                </td>
                <td>${row.data_entrega || ''}</td>
            `;
            
            tbody.appendChild(tr);
        });
        
        // Preencher linhas vazias se necessário para manter o layout
        const remainingRows = this.perPage - tableData.length;
        for (let i = 0; i < remainingRows; i++) {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>&nbsp;</td>
                <td>&nbsp;</td>
                <td>&nbsp;</td>
                <td>&nbsp;</td>
                <td>&nbsp;</td>
                <td>&nbsp;</td>
                <td>&nbsp;</td>
                <td>&nbsp;</td>
                <td>&nbsp;</td>
                <td>&nbsp;</td>
            `;
            tr.style.opacity = '0.3';
            tbody.appendChild(tr);
        }
    }
    
    formatDataEmbarque(dataStr) {
        if (!dataStr || dataStr.trim() === '') {
            return '';
        }
        
        try {
            // Assumindo formato DD/MM/YYYY
            const [day, month, year] = dataStr.split('/');
            const dataEmbarque = new Date(year, month - 1, day);
            const hoje = new Date();
            
            const className = dataEmbarque >= hoje ? 'data-embarque-red' : 'data-embarque-white';
            return `<span class="${className}">${dataStr}</span>`;
        } catch (error) {
            return dataStr;
        }
    }
    
    getModalImage(modal) {
        const modalImages = {
            '1': '/static/medias/minimal_ship.png',      // Marítimo
            '4': '/static/medias/minimal_plane.png',     // Aéreo
            '7': '/static/medias/minimal_truck.png'      // Terrestre
        };
        
        return modalImages[modal] || '/static/medias/minimal_ship.png';
    }
    
    updatePagination(paginationData) {
        this.totalPages = paginationData.pages || 1;
        this.currentPage = paginationData.current_page || 1;
        
        // Atualizar apenas as informações de paginação no rodapé
        document.getElementById('page-info').textContent = 
            `Página ${this.currentPage} de ${this.totalPages}`;
        
        // Atualizar estado dos botões
        const btnPrev = document.getElementById('btn-prev-page');
        const btnNext = document.getElementById('btn-next-page');
        
        btnPrev.disabled = this.currentPage <= 1;
        btnNext.disabled = this.currentPage >= this.totalPages;
    }
    
    showNoDataMessage() {
        // Mostrar mensagem de "sem dados" na tabela
        const tbody = document.getElementById('table-body');
        if (tbody) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="10" style="text-align: center; padding: 3rem; color: #6b7280;">
                        <div style="display: flex; flex-direction: column; align-items: center; gap: 1rem;">
                            <i class="mdi mdi-database-off" style="font-size: 3rem; color: #d1d5db;"></i>
                            <div>
                                <h3 style="margin: 0; color: #374151;">Nenhum dado encontrado</h3>
                                <p style="margin: 0.5rem 0 0 0; color: #6b7280;">
                                    Os dados ainda não foram carregados no cache.<br>
                                    Tente fazer login novamente ou aguarde o carregamento dos dados.
                                </p>
                            </div>
                        </div>
                    </td>
                </tr>
            `;
        }
        
        // Resetar métricas do cabeçalho
        this.updateHeader({
            total_processos: 0,
            count_maritimo: 0,
            count_aereo: 0,
            count_terrestre: 0,
            current_time: new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', hour12: false }),
            current_date: this.getCurrentDate(),
            exchange_rates: { dolar: null, euro: null }
        });
        
        // Resetar paginação
        this.updatePagination({
            total: 0,
            pages: 1,
            current_page: 1,
            per_page: this.perPage
        });
    }
    
    getCurrentDate() {
        const now = new Date();
        const months = [
            'JANEIRO', 'FEVEREIRO', 'MARÇO', 'ABRIL', 'MAIO', 'JUNHO',
            'JULHO', 'AGOSTO', 'SETEMBRO', 'OUTUBRO', 'NOVEMBRO', 'DEZEMBRO'
        ];
        const day = now.getDate();
        const month = months[now.getMonth()];
        return `${day} ${month}`;
    }
    
    showError(message) {
        // Criar e mostrar um toast de erro simples
        const errorDiv = document.createElement('div');
        errorDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #F44336;
            color: white;
            padding: 1rem 1.5rem;
            border-radius: 6px;
            z-index: 10000;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
            font-weight: 500;
        `;
        errorDiv.textContent = message;
        
        document.body.appendChild(errorDiv);
        
        // Remover após 5 segundos
        setTimeout(() => {
            if (errorDiv.parentNode) {
                errorDiv.parentNode.removeChild(errorDiv);
            }
        }, 5000);
    }
    
    destroy() {
        this.stopAutoRefresh();
    }
}

// Inicializar quando o DOM estiver carregado
document.addEventListener('DOMContentLoaded', () => {
    window.dashboardImportacoes = new DashboardImportacoesResumido();
});

// Limpar ao sair da página
window.addEventListener('beforeunload', () => {
    if (window.dashboardImportacoes) {
        window.dashboardImportacoes.destroy();
    }
});
