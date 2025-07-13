/**
 * Dashboard Async Loading
 * Carregamento assíncrono de dados do dashboard para melhor performance
 */

class DashboardAsync {
    constructor() {
        this.currentPeriod = '30'; // Período padrão: 30 dias
        this.currentCompany = null;
        this.isLoading = false;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadInitialData();
    }

    setupEventListeners() {
        // Filtro de período
        const periodFilter = document.getElementById('period-filter');
        if (periodFilter) {
            periodFilter.addEventListener('change', (e) => {
                this.currentPeriod = e.target.value;
                this.loadData();
            });
        }

        // Filtro de empresa
        const companyFilter = document.getElementById('company-filter');
        if (companyFilter) {
            companyFilter.addEventListener('change', (e) => {
                this.currentCompany = e.target.value || null;
                this.loadData();
            });
        }

        // Botão de refresh
        const refreshBtn = document.getElementById('refresh-data');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.loadData(true); // Force refresh
            });
        }
    }

    loadInitialData() {
        // Mostrar loading inicial
        this.showLoadingState();
        
        // Carregar dados padrão (30 dias)
        this.loadData();
    }

    async loadData(forceRefresh = false) {
        if (this.isLoading && !forceRefresh) return;
        
        this.isLoading = true;
        this.showLoadingState();

        try {
            const params = new URLSearchParams();
            params.append('periodo', this.currentPeriod);
            
            if (this.currentCompany) {
                params.append('empresa', this.currentCompany);
            }

            console.log(`[DASHBOARD] Carregando dados: período=${this.currentPeriod}, empresa=${this.currentCompany || 'todas'}`);

            const response = await fetch(`/api/dashboard-data?${params.toString()}`);
            const result = await response.json();

            if (result.success) {
                this.updateUI(result.data);
                this.showSuccessMessage(`Dados carregados: ${result.data.record_count} registros (${result.data.periodo_info})`);
            } else {
                this.showErrorMessage(`Erro ao carregar dados: ${result.error}`);
            }

        } catch (error) {
            console.error('[DASHBOARD] Erro na requisição:', error);
            this.showErrorMessage('Erro de conexão. Tente novamente.');
        } finally {
            this.isLoading = false;
            this.hideLoadingState();
        }
    }

    updateUI(data) {
        // Atualizar KPIs
        this.updateKPIs(data.kpis);
        
        // Atualizar análise de materiais
        this.updateMaterialAnalysis(data.material_analysis);
        
        // Atualizar tabela
        this.updateTable(data.table_data);
        
        // Atualizar info do período
        this.updatePeriodInfo(data.periodo_info, data.record_count);
        
        // Atualizar timestamp
        this.updateLastUpdate(data.last_update);
    }

    updateKPIs(kpis) {
        // Totais
        this.updateElement('#total-processos', kpis.total || 0);
        
        // Modais
        this.updateElement('#total-aereo', kpis.aereo || 0);
        this.updateElement('#total-terrestre', kpis.terrestre || 0);
        this.updateElement('#total-maritimo', kpis.maritimo || 0);
        
        // Status
        this.updateElement('#aguardando-embarque', kpis.aguardando_embarque || 0);
        this.updateElement('#aguardando-chegada', kpis.aguardando_chegada || 0);
        this.updateElement('#di-registrada', kpis.di_registrada || 0);
        
        // Valores
        this.updateElement('#vmcv-total', kpis.valor_total_formatted || 'R$ 0');
        this.updateElement('#vmcv-medio', kpis.valor_medio_processo_formatted || 'R$ 0');
        this.updateElement('#despesas-total', kpis.despesas_total_formatted || 'R$ 0');
        this.updateElement('#despesas-medio', kpis.despesa_media_processo_formatted || 'R$ 0');
    }

    updateMaterialAnalysis(materials) {
        const container = document.getElementById('material-analysis-container');
        if (!container) return;

        if (!materials || materials.length === 0) {
            container.innerHTML = '<div class="text-center text-muted">Nenhum material encontrado</div>';
            return;
        }

        let html = '<div class="row">';
        materials.forEach((material, index) => {
            if (index < 6) { // Mostrar apenas top 6
                html += `
                    <div class="col-md-6 col-lg-4 mb-3">
                        <div class="card h-100">
                            <div class="card-body">
                                <h6 class="card-title text-truncate" title="${material.material}">
                                    ${material.material}
                                </h6>
                                <div class="d-flex justify-content-between align-items-center">
                                    <span class="text-primary">${material.quantidade} processos</span>
                                    <span class="badge bg-success">${material.percentual}%</span>
                                </div>
                                <div class="mt-2">
                                    <strong class="text-success">${material.valor_total_formatado}</strong>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            }
        });
        html += '</div>';
        
        container.innerHTML = html;
    }

    updateTable(tableData) {
        const tbody = document.querySelector('#dashboard-table tbody');
        if (!tbody) return;

        if (!tableData || tableData.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">Nenhum registro encontrado</td></tr>';
            return;
        }

        let html = '';
        tableData.forEach(row => {
            html += `
                <tr>
                    <td class="text-truncate" style="max-width: 200px;" title="${row.importador}">
                        ${row.importador}
                    </td>
                    <td>
                        <span class="badge ${this.getModalBadgeClass(row.modal)}">${row.modal || 'N/A'}</span>
                    </td>
                    <td class="text-truncate" style="max-width: 150px;" title="${row.urf_entrada}">
                        ${row.urf_entrada || 'N/A'}
                    </td>
                    <td>
                        <small class="text-muted">${row.status_processo || 'N/A'}</small>
                    </td>
                    <td class="text-truncate" style="max-width: 180px;" title="${row.mercadoria}">
                        ${row.mercadoria || 'N/A'}
                    </td>
                    <td class="text-end">
                        <strong class="text-success">${row.valor_cif_formatted}</strong>
                    </td>
                </tr>
            `;
        });
        
        tbody.innerHTML = html;
    }

    getModalBadgeClass(modal) {
        switch(modal) {
            case 'AÉREA': return 'bg-primary';
            case 'MARÍTIMA': return 'bg-info';
            case 'RODOVIÁRIA': return 'bg-warning';
            default: return 'bg-secondary';
        }
    }

    updatePeriodInfo(periodInfo, recordCount) {
        const element = document.getElementById('period-info');
        if (element) {
            element.textContent = `${periodInfo} • ${recordCount} registros`;
        }
    }

    updateLastUpdate(lastUpdate) {
        const element = document.getElementById('last-update');
        if (element) {
            element.textContent = `Última atualização: ${lastUpdate}`;
        }
    }

    updateElement(selector, value) {
        const element = document.querySelector(selector);
        if (element) {
            if (typeof value === 'number') {
                element.textContent = value.toLocaleString('pt-BR');
            } else {
                element.textContent = value;
            }
        }
    }

    showLoadingState() {
        // Mostrar spinners
        document.querySelectorAll('.loading-spinner').forEach(el => {
            el.style.display = 'inline-block';
        });
        
        // Desabilitar controles
        document.querySelectorAll('#period-filter, #company-filter, #refresh-data').forEach(el => {
            el.disabled = true;
        });
        
        // Mostrar overlay de loading se existir
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.style.display = 'flex';
        }
    }

    hideLoadingState() {
        // Ocultar spinners
        document.querySelectorAll('.loading-spinner').forEach(el => {
            el.style.display = 'none';
        });
        
        // Habilitar controles
        document.querySelectorAll('#period-filter, #company-filter, #refresh-data').forEach(el => {
            el.disabled = false;
        });
        
        // Ocultar overlay de loading
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.style.display = 'none';
        }
    }

    showSuccessMessage(message) {
        this.showMessage(message, 'success');
    }

    showErrorMessage(message) {
        this.showMessage(message, 'danger');
    }

    showMessage(message, type = 'info') {
        // Criar toast ou alert
        const alertContainer = document.getElementById('alert-container');
        if (alertContainer) {
            const alert = document.createElement('div');
            alert.className = `alert alert-${type} alert-dismissible fade show`;
            alert.innerHTML = `
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            alertContainer.appendChild(alert);
            
            // Auto-remove após 5 segundos
            setTimeout(() => {
                if (alert.parentNode) {
                    alert.parentNode.removeChild(alert);
                }
            }, 5000);
        } else {
            console.log(`[DASHBOARD] ${type.toUpperCase()}: ${message}`);
        }
    }
}

// Inicializar quando o DOM estiver carregado
document.addEventListener('DOMContentLoaded', function() {
    // Verificar se deve usar carregamento assíncrono
    const container = document.querySelector('.dashboard-container');
    if (container && container.dataset.asyncLoading === 'true') {
        window.dashboardAsync = new DashboardAsync();
    }
});
