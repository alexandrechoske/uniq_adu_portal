// Analytics do Agente - JavaScript
document.addEventListener('DOMContentLoaded', function() {
    let currentFilters = {
        dateRange: '30d',
        empresa: 'all',
        messageType: 'all'
    };
    let currentPage = 1;
    let totalPages = 1;
    const pageLimit = 10;

    // Inicializar página
    init();

    function init() {
        console.log('Inicializando Analytics do Agente...');
        
        // Event listeners
        setupEventListeners();
        
        // Carregar dados iniciais
        loadData();
        
        // Configurar auto-refresh (a cada 5 minutos)
        setInterval(loadData, 5 * 60 * 1000);
    }

    function setupEventListeners() {
        // Botão de refresh
        document.getElementById('refresh-data').addEventListener('click', loadData);
    }

    function loadData() {
        console.log('Carregando dados do Analytics do Agente...', currentFilters);
        
        showLoadingState();
        
        Promise.all([
            loadStats(),
            loadInteractionsChart(),
            loadTopCompanies(),
            loadRecentInteractions()
        ]).then(() => {
            hideLoadingState();
            console.log('Todos os dados carregados com sucesso');
        }).catch(error => {
            console.error('Erro ao carregar dados:', error);
            hideLoadingState();
            showError('Erro ao carregar dados do Analytics do Agente');
        });
    }

    function showLoadingState() {
        document.getElementById('kpi-loading').style.display = 'flex';
        document.getElementById('interactions-chart-loading').style.display = 'flex';
        document.getElementById('top-companies-loading').style.display = 'flex';
        document.getElementById('recent-interactions-loading').style.display = 'flex';
    }

    function hideLoadingState() {
        document.getElementById('kpi-loading').style.display = 'none';
        document.getElementById('interactions-chart-loading').style.display = 'none';
        document.getElementById('top-companies-loading').style.display = 'none';
        document.getElementById('recent-interactions-loading').style.display = 'none';
    }

    function loadStats() {
        const params = new URLSearchParams(currentFilters);
        
        return fetch(`/usuarios/analytics/api/agente/stats?${params}`)
            .then(response => response.json())
            .then(data => {
                updateKPICards(data);
            })
            .catch(error => {
                console.error('Erro ao carregar estatísticas:', error);
                throw error;
            });
    }

    function updateKPICards(stats) {
        document.getElementById('total-interactions').textContent = stats.total_interactions || 0;
        document.getElementById('unique-users').textContent = stats.unique_users || 0;
        document.getElementById('unique-companies').textContent = stats.unique_companies || 0;
        document.getElementById('success-rate').textContent = `${stats.success_rate || 0}%`;
        
        // Formatear tempo de resposta
        const responseTime = stats.avg_response_time || 0;
        if (responseTime >= 1000) {
            document.getElementById('avg-response-time').textContent = `${(responseTime / 1000).toFixed(1)}s`;
        } else {
            document.getElementById('avg-response-time').textContent = `${responseTime}ms`;
        }
        
        document.getElementById('normal-responses').textContent = stats.normal_responses || 0;
        document.getElementById('arquivo-responses').textContent = stats.arquivo_responses || 0;
    }

    function loadInteractionsChart() {
        const params = new URLSearchParams(currentFilters);
        
        return fetch(`/usuarios/analytics/api/agente/interactions-chart?${params}`)
            .then(response => response.json())
            .then(data => {
                renderInteractionsChart(data);
            })
            .catch(error => {
                console.error('Erro ao carregar gráfico de interações:', error);
                throw error;
            });
    }

    function renderInteractionsChart(data) {
        const chartDiv = document.getElementById('interactions-chart');
        
        if (!data || data.length === 0) {
            chartDiv.innerHTML = '<div class="no-data">Nenhum dado disponível para o período selecionado</div>';
            return;
        }

        // Destruir gráfico existente se houver
        if (window.interactionsChart) {
            window.interactionsChart.destroy();
        }

        // Preparar dados
        const dates = data.map(d => {
            const date = new Date(d.date);
            return date.toLocaleDateString('pt-BR', { 
                day: '2-digit', 
                month: '2-digit' 
            });
        });
        const totalValues = data.map(d => d.total);
        const normalValues = data.map(d => d.normal);
        const arquivoValues = data.map(d => d.arquivo);

        const ctx = chartDiv.getContext('2d');
        
        window.interactionsChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: dates,
                datasets: [
                    {
                        label: 'Total',
                        data: totalValues,
                        borderColor: '#3498DB',
                        backgroundColor: 'rgba(52, 152, 219, 0.1)',
                        fill: false,
                        tension: 0.4,
                        pointRadius: 6,
                        pointBackgroundColor: '#3498DB',
                        pointBorderColor: '#ffffff',
                        pointBorderWidth: 2,
                        borderWidth: 3
                    },
                    {
                        label: 'Respostas Normais',
                        data: normalValues,
                        borderColor: '#2ECC71',
                        backgroundColor: 'rgba(46, 204, 113, 0.1)',
                        fill: false,
                        tension: 0.4,
                        pointRadius: 4,
                        pointBackgroundColor: '#2ECC71',
                        pointBorderColor: '#ffffff',
                        pointBorderWidth: 2,
                        borderWidth: 2
                    },
                    {
                        label: 'Solicitações de Arquivo',
                        data: arquivoValues,
                        borderColor: '#E74C3C',
                        backgroundColor: 'rgba(231, 76, 60, 0.1)',
                        fill: false,
                        tension: 0.4,
                        pointRadius: 4,
                        pointBackgroundColor: '#E74C3C',
                        pointBorderColor: '#ffffff',
                        pointBorderWidth: 2,
                        borderWidth: 2
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'bottom',
                        labels: {
                            usePointStyle: true,
                            padding: 20
                        }
                    },
                    title: {
                        display: false
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Data'
                        },
                        grid: {
                            color: '#f0f0f0'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Número de Interações'
                        },
                        grid: {
                            color: '#f0f0f0'
                        },
                        beginAtZero: true
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                elements: {
                    point: {
                        hoverRadius: 8
                    }
                }
            }
        });
    }

    function loadTopCompanies() {
        const params = new URLSearchParams(currentFilters);
        
        return fetch(`/usuarios/analytics/api/agente/top-companies?${params}`)
            .then(response => response.json())
            .then(data => {
                renderTopCompaniesTable(data);
            })
            .catch(error => {
                console.error('Erro ao carregar top empresas:', error);
                throw error;
            });
    }

    function renderTopCompaniesTable(data) {
        const container = document.getElementById('top-companies-table');
        
        if (!data || data.length === 0) {
            container.innerHTML = '<div class="no-data">Nenhuma empresa encontrada para o período selecionado</div>';
            return;
        }

        let html = `
            <table class="enhanced-table">
                <thead>
                    <tr>
                        <th>Empresa</th>
                        <th>Total Interações</th>
                        <th>Usuários Únicos</th>
                        <th>Média Processos</th>
                        <th>Última Interação</th>
                    </tr>
                </thead>
                <tbody>
        `;

        data.forEach(company => {
            const lastInteraction = company.last_interaction ? 
                formatDate(company.last_interaction) : 'N/A';
            
            html += `
                <tr>
                    <td><strong>${company.empresa_nome}</strong></td>
                    <td>${company.total_interactions}</td>
                    <td>${company.unique_users}</td>
                    <td>${company.avg_processos_encontrados}</td>
                    <td>${lastInteraction}</td>
                </tr>
            `;
        });

        html += `
                </tbody>
            </table>
        `;

        container.innerHTML = html;
    }

    function loadRecentInteractions() {
        const params = new URLSearchParams(currentFilters);
        params.append('page', currentPage);
        params.append('limit', pageLimit);
        
        return fetch(`/usuarios/analytics/api/agente/recent-interactions?${params}`)
            .then(response => response.json())
            .then(result => {
                renderRecentInteractionsTable(result.data, result.pagination);
            })
            .catch(error => {
                console.error('Erro ao carregar interações recentes:', error);
                throw error;
            });
    }

    function renderRecentInteractionsTable(data, pagination) {
        const container = document.getElementById('recent-interactions-table');
        
        if (!data || data.length === 0) {
            container.innerHTML = '<div class="no-data">Nenhuma interação encontrada para o período selecionado</div>';
            return;
        }

        // Atualizar estado de paginação
        currentPage = pagination.current_page;
        totalPages = pagination.total_pages;

        let html = `
            <table class="enhanced-table">
                <thead>
                    <tr>
                        <th>Data/Hora</th>
                        <th>Usuário</th>
                        <th>Empresa</th>
                        <th>Mensagem</th>
                        <th>Tipo</th>
                        <th>Processos</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
        `;

        data.forEach(interaction => {
            const timestamp = interaction.timestamp ? 
                formatDateTime(interaction.timestamp) : 'N/A';
            
            const statusClass = interaction.is_successful ? 'success' : 'error';
            const statusIcon = interaction.is_successful ? 'check-circle' : 'alert-circle';
            const statusText = interaction.is_successful ? 'Sucesso' : 'Erro';
            
            const messagePreview = interaction.user_message.length > 50 ? 
                interaction.user_message.substring(0, 50) + '...' : 
                interaction.user_message;

            html += `
                <tr class="interaction-row" data-interaction='${JSON.stringify(interaction)}' style="cursor: pointer;">
                    <td>${timestamp}</td>
                    <td>
                        <div><strong>${interaction.user_name}</strong></div>
                        <div class="text-muted">${interaction.whatsapp_number}</div>
                    </td>
                    <td>${interaction.empresa_nome}</td>
                    <td title="${interaction.user_message}">${messagePreview}</td>
                    <td>
                        <span class="badge badge-${interaction.response_type}">
                            ${interaction.response_type}
                        </span>
                    </td>
                    <td>${interaction.total_processos_encontrados}</td>
                    <td>
                        <span class="status ${statusClass}">
                            <i class="mdi mdi-${statusIcon}"></i>
                            ${statusText}
                        </span>
                    </td>
                </tr>
            `;
        });

        html += `
                </tbody>
            </table>
        `;

        // Adicionar controles de paginação
        html += renderPaginationControls(pagination);

        container.innerHTML = html;
        
        // Add click event listeners to table rows
        document.querySelectorAll('.interaction-row').forEach(row => {
            row.addEventListener('click', function() {
                const interactionData = JSON.parse(this.dataset.interaction);
                showInteractionModal(interactionData);
            });
        });
        
        // Adicionar event listeners para paginação
        setupPaginationEvents();
    }

    function loadFilterOptions() {
        // Carregar opções de empresas para o filtro
        const params = new URLSearchParams(currentFilters);
        
        fetch(`/usuarios/analytics/api/agente/top-companies?${params}`)
            .then(response => response.json())
            .then(data => {
                const empresaSelect = document.getElementById('empresa');
                
                // Limpar opções existentes (exceto "Todas")
                empresaSelect.innerHTML = '<option value="all">Todas as empresas</option>';
                
                // Adicionar empresas
                data.forEach(company => {
                    const option = document.createElement('option');
                    option.value = company.empresa_nome;
                    option.textContent = company.empresa_nome;
                    empresaSelect.appendChild(option);
                });
                
                // Definir valor atual
                empresaSelect.value = currentFilters.empresa;
            })
            .catch(error => {
                console.error('Erro ao carregar opções de filtro:', error);
            });
        
        // Definir valores atuais nos filtros
        document.getElementById('dateRange').value = currentFilters.dateRange;
        document.getElementById('messageType').value = currentFilters.messageType;
    }

    function applyFilters() {
        const form = document.getElementById('filters-form');
        const formData = new FormData(form);
        
        currentFilters = {
            dateRange: formData.get('dateRange') || '30d',
            empresa: formData.get('empresa') || 'all',
            messageType: formData.get('messageType') || 'all'
        };
        
        // Resetar para primeira página quando filtros mudarem
        currentPage = 1;
        
        updateFilterSummary();
        loadData();
        
        // Fechar modal
        document.getElementById('filters-modal').style.display = 'none';
        
        // Mostrar botão de reset se há filtros aplicados
        const hasFilters = currentFilters.dateRange !== '30d' || 
                          currentFilters.empresa !== 'all' || 
                          currentFilters.messageType !== 'all';
        
        document.getElementById('reset-filters').style.display = hasFilters ? 'inline-block' : 'none';
    }

    function clearFilters() {
        currentFilters = {
            dateRange: '30d',
            empresa: 'all',
            messageType: 'all'
        };
        currentPage = 1; // Resetar página também
        
        // Resetar formulário
        document.getElementById('filters-form').reset();
        document.getElementById('dateRange').value = '30d';
        
        updateFilterSummary();
        loadData();
        
        // Fechar modal
        document.getElementById('filters-modal').style.display = 'none';
        
        // Esconder botão de reset
        document.getElementById('reset-filters').style.display = 'none';
    }

    function resetFilters() {
        clearFilters();
    }

    function updateFilterSummary() {
        let summary = '';
        
        if (currentFilters.dateRange === '1d') {
            summary = 'Vendo dados do último dia';
        } else if (currentFilters.dateRange === '7d') {
            summary = 'Vendo dados dos últimos 7 dias';
        } else {
            summary = 'Vendo dados dos últimos 30 dias';
        }
        
        if (currentFilters.empresa !== 'all') {
            summary += ` • Empresa: ${currentFilters.empresa}`;
        }
        
        if (currentFilters.messageType !== 'all') {
            summary += ` • Tipo: ${currentFilters.messageType}`;
        }
        
        document.getElementById('filter-summary-text').textContent = summary;
    }

    function formatDate(dateString) {
        try {
            const date = new Date(dateString);
            return date.toLocaleDateString('pt-BR');
        } catch (error) {
            return 'N/A';
        }
    }

    function formatDateTime(dateString) {
        try {
            const date = new Date(dateString);
            return date.toLocaleString('pt-BR');
        } catch (error) {
            return 'N/A';
        }
    }

    function showError(message) {
        console.error('Erro:', message);
        
        // Mostrar uma notificação de erro simples
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-notification';
        errorDiv.textContent = message;
        errorDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #e74c3c;
            color: white;
            padding: 15px;
            border-radius: 5px;
            z-index: 10000;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        `;
        
        document.body.appendChild(errorDiv);
        
        // Remover após 5 segundos
        setTimeout(() => {
            errorDiv.remove();
        }, 5000);
    }

    // Funções de paginação
    function renderPaginationControls(pagination) {
        const { current_page, total_pages, total_records, has_prev, has_next } = pagination;
        
        const startRecord = ((current_page - 1) * pageLimit) + 1;
        const endRecord = Math.min(current_page * pageLimit, total_records);
        
        let html = `
            <div class="pagination-container">
                <div class="pagination-info">
                    Mostrando ${startRecord} a ${endRecord} de ${total_records} registros
                </div>
                <div class="pagination-controls">
        `;
        
        // Botão anterior
        html += `
            <button class="pagination-btn" data-page="${current_page - 1}" ${!has_prev ? 'disabled' : ''}>
                <i class="mdi mdi-chevron-left"></i>
                Anterior
            </button>
        `;
        
        // Números das páginas
        const maxVisiblePages = 5;
        const startPage = Math.max(1, current_page - Math.floor(maxVisiblePages / 2));
        const endPage = Math.min(total_pages, startPage + maxVisiblePages - 1);
        
        for (let i = startPage; i <= endPage; i++) {
            html += `
                <button class="pagination-btn ${i === current_page ? 'active' : ''}" data-page="${i}">
                    ${i}
                </button>
            `;
        }
        
        // Botão próximo
        html += `
            <button class="pagination-btn" data-page="${current_page + 1}" ${!has_next ? 'disabled' : ''}>
                Próximo
                <i class="mdi mdi-chevron-right"></i>
            </button>
        `;
        
        html += `
                </div>
            </div>
        `;
        
        return html;
    }

    function setupPaginationEvents() {
        document.querySelectorAll('.pagination-btn[data-page]').forEach(btn => {
            if (!btn.disabled) {
                btn.addEventListener('click', () => {
                    const page = parseInt(btn.dataset.page);
                    if (page >= 1 && page <= totalPages) {
                        currentPage = page;
                        loadRecentInteractions();
                    }
                });
            }
        });
    }
    
    function showInteractionModal(interaction) {
        // Populate modal with interaction data
        document.getElementById('modal-user-name').textContent = interaction.user_name;
        document.getElementById('modal-whatsapp').textContent = interaction.whatsapp_number;
        document.getElementById('modal-empresa').textContent = interaction.empresa_nome;
        document.getElementById('modal-timestamp').textContent = new Date(interaction.timestamp_utc + 'Z').toLocaleString('pt-BR');
        document.getElementById('modal-user-message').textContent = interaction.user_message;
        document.getElementById('modal-response-type').textContent = interaction.response_type;
        document.getElementById('modal-processos').textContent = interaction.total_processos_encontrados || 'N/A';
        
        // Response data - handle different formats
        let responseText = 'N/A';
        if (interaction.response_data) {
            if (typeof interaction.response_data === 'string') {
                responseText = interaction.response_data;
            } else if (typeof interaction.response_data === 'object') {
                responseText = JSON.stringify(interaction.response_data, null, 2);
            }
        }
        document.getElementById('modal-agent-response').textContent = responseText;
        
        // Response time
        document.getElementById('modal-response-time').textContent = interaction.response_time_formatted || 'N/A';
        
        // Status
        const statusElement = document.getElementById('modal-success-status');
        if (interaction.success) {
            statusElement.className = 'alert alert-success';
            statusElement.textContent = 'Interação bem-sucedida';
        } else {
            statusElement.className = 'alert alert-danger';
            statusElement.textContent = 'Interação com falha';
        }
        
        // Show the modal
        $('#interactionModal').modal('show');
    }
});
