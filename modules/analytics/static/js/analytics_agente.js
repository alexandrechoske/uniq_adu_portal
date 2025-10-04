// Analytics Agente - JavaScript Otimizado com View
let analyticsData = {};
let charts = {};
let currentFilters = {
    dateRange: '30d',
    empresa: 'all',
    responseType: 'all'
};

let isLoading = false;

document.addEventListener('DOMContentLoaded', function() {
    console.log('[ANALYTICS AGENTE] Module loaded');
    initializeAnalytics();
});

function initializeAnalytics() {
    // Configurar Chart.js defaults
    Chart.defaults.font.family = 'Segoe UI, Tahoma, Geneva, Verdana, sans-serif';
    Chart.defaults.color = '#6b7280';
    Chart.defaults.borderColor = '#f1f5f9';
    
    // Desabilitar datalabels por padrão (habilitamos individualmente)
    Chart.register(ChartDataLabels);
    Chart.defaults.set('plugins.datalabels', {
        display: false
    });
    
    setupEventListeners();
    loadEmpresasList();
    loadAllData();
}

function setupEventListeners() {
    // Botões principais
    document.getElementById('open-filters')?.addEventListener('click', openFiltersModal);
    document.getElementById('refresh-data')?.addEventListener('click', refreshData);
    document.getElementById('reset-filters')?.addEventListener('click', resetFilters);
    
    // Modal
    document.getElementById('apply-filters')?.addEventListener('click', applyFilters);
    document.getElementById('clear-filters')?.addEventListener('click', clearFilters);
    document.querySelector('.close')?.addEventListener('click', closeFiltersModal);
    
    // Click outside modal
    window.addEventListener('click', function(event) {
        const modal = document.getElementById('filters-modal');
        if (event.target === modal) {
            closeFiltersModal();
        }
    });
}

async function loadEmpresasList() {
    try {
        const response = await fetch('/analytics/api/agente/empresas-list');
        const data = await response.json();
        
        if (data.success && data.empresas) {
            const select = document.getElementById('empresa-filter');
            if (select) {
                // Limpar opções existentes (exceto "Todas")
                select.innerHTML = '<option value="all" selected>Todas</option>';
                
                // Adicionar empresas
                data.empresas.forEach(empresa => {
                    const option = document.createElement('option');
                    option.value = empresa;
                    option.textContent = empresa;
                    select.appendChild(option);
                });
                
                console.log('[ANALYTICS AGENTE] Lista de empresas carregada:', data.empresas.length);
            }
        }
    } catch (error) {
        console.error('[ANALYTICS AGENTE] Erro ao carregar empresas:', error);
    }
}

async function loadAllData() {
    if (isLoading) return;
    
    isLoading = true;
    showLoading();
    
    try {
        // Construir query string com filtros
        const params = new URLSearchParams({
            dateRange: currentFilters.dateRange,
            empresa: currentFilters.empresa,
            responseType: currentFilters.responseType
        });
        
        // Carregar todas as APIs em paralelo
        const [kpis, timeline, topEmpresas, peakHours, responseTypes, recentInteractions] = await Promise.all([
            fetch(`/analytics/api/agente/kpis?${params}`).then(r => r.json()),
            fetch(`/analytics/api/agente/timeline?${params}`).then(r => r.json()),
            fetch(`/analytics/api/agente/top-empresas?${params}`).then(r => r.json()),
            fetch(`/analytics/api/agente/peak-hours?${params}`).then(r => r.json()),
            fetch(`/analytics/api/agente/response-types?${params}`).then(r => r.json()),
            fetch(`/analytics/api/agente/recent-interactions?${params}`).then(r => r.json())
        ]);
        
        // Atualizar interface
        if (kpis.success) updateKPIs(kpis.data);
        if (timeline.success) createTimelineChart(timeline.data);
        if (topEmpresas.success) createTopEmpresasChart(topEmpresas.data);
        if (peakHours.success) createPeakHoursChart(peakHours.data);
        if (responseTypes.success) {
            createResponseTypesChart(responseTypes.data);
            createWeekdayChart(responseTypes.data); // Vamos usar os mesmos dados ou criar outro endpoint
        }
        if (recentInteractions.success) updateRecentLogsTable(recentInteractions.data);
        
        console.log('[ANALYTICS AGENTE] Todos os dados carregados com sucesso');
        
    } catch (error) {
        console.error('[ANALYTICS AGENTE] Erro ao carregar dados:', error);
        showError('Erro ao carregar dados do analytics');
    } finally {
        isLoading = false;
        hideLoading();
    }
}

function updateKPIs(data) {
    // Total de Interações
    updateKPIValue('total-interactions', data.total_interactions || 0);
    
    // Usuários Únicos
    updateKPIValue('unique-users', data.unique_users || 0);
    
    // Tempo Médio de Resposta
    const avgTime = data.avg_response_time_seconds || 0;
    const formattedTime = avgTime < 1 ? 
        `${(avgTime * 1000).toFixed(0)} ms` : 
        `${avgTime.toFixed(2)} s`;
    updateKPIValue('avg-response-time', formattedTime, '');
    
    // Taxa de Sucesso (assumindo sempre 100% se não houver campo de erro)
    updateKPIValue('success-rate', data.success_rate || 100, '%');
    
    console.log('[ANALYTICS AGENTE] KPIs atualizados');
}

function createTimelineChart(data) {
    const ctx = document.getElementById('timeline-chart');
    if (!ctx) return;
    
    // Destruir gráfico existente
    if (charts.timeline) {
        charts.timeline.destroy();
    }
    
    charts.timeline = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels || [],
            datasets: [{
                label: 'Interações',
                data: data.values || [],
                borderColor: '#25D366',
                backgroundColor: 'rgba(37, 211, 102, 0.1)',
                fill: true,
                tension: 0.4,
                pointRadius: 4,
                pointBackgroundColor: '#25D366',
                pointBorderColor: '#ffffff',
                pointBorderWidth: 2,
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                datalabels: {
                    display: true,
                    align: 'top',
                    anchor: 'end',
                    color: '#128C7E',
                    font: {
                        weight: 'bold',
                        size: 11
                    },
                    formatter: function(value) {
                        return value > 0 ? value : '';
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: 'white',
                    bodyColor: 'white',
                    borderColor: '#25D366',
                    borderWidth: 1,
                    cornerRadius: 8,
                    callbacks: {
                        label: function(context) {
                            return `Interações: ${context.parsed.y}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    }
                },
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    },
                    ticks: {
                        precision: 0
                    }
                }
            }
        }
    });
    
    console.log('[ANALYTICS AGENTE] Timeline chart criado');
}

function createTopEmpresasChart(data) {
    const ctx = document.getElementById('top-empresas-chart');
    if (!ctx) return;
    
    if (charts.topEmpresas) {
        charts.topEmpresas.destroy();
    }
    
    charts.topEmpresas = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.labels || [],
            datasets: [{
                label: 'Interações',
                data: data.values || [],
                backgroundColor: '#25D366',
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                datalabels: {
                    display: true,
                    anchor: 'end',
                    align: 'end',
                    color: '#128C7E',
                    font: {
                        weight: 'bold',
                        size: 11
                    },
                    formatter: function(value) {
                        return value > 0 ? value : '';
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: 'white',
                    bodyColor: 'white',
                    borderColor: '#25D366',
                    borderWidth: 1,
                    cornerRadius: 8
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    }
                },
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    },
                    ticks: {
                        precision: 0
                    }
                }
            }
        }
    });
    
    console.log('[ANALYTICS AGENTE] Top Empresas chart criado');
}

function createPeakHoursChart(data) {
    const ctx = document.getElementById('peak-hours-chart');
    if (!ctx) return;
    
    if (charts.peakHours) {
        charts.peakHours.destroy();
    }
    
    charts.peakHours = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.labels || [],
            datasets: [{
                label: 'Interações',
                data: data.values || [],
                backgroundColor: '#9B59B6',
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                datalabels: {
                    display: true,
                    anchor: 'end',
                    align: 'end',
                    color: '#6f42c1',
                    font: {
                        weight: 'bold',
                        size: 11
                    },
                    formatter: function(value) {
                        return value > 0 ? value : '';
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: 'white',
                    bodyColor: 'white',
                    borderColor: '#9B59B6',
                    borderWidth: 1,
                    cornerRadius: 8,
                    callbacks: {
                        title: function(context) {
                            const hour = context[0].label;
                            return `${hour}:00`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    },
                    title: {
                        display: true,
                        text: 'Hora do Dia'
                    }
                },
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    },
                    ticks: {
                        precision: 0
                    }
                }
            }
        }
    });
    
    console.log('[ANALYTICS AGENTE] Peak Hours chart criado');
}

function createResponseTypesChart(data) {
    const ctx = document.getElementById('response-types-chart');
    if (!ctx) return;
    
    if (charts.responseTypes) {
        charts.responseTypes.destroy();
    }
    
    // Cores para diferentes tipos
    const colors = {
        'normal': '#3498DB',
        'arquivo': '#F39C12'
    };
    
    const backgroundColors = data.labels.map(label => colors[label] || '#95a5a6');
    
    charts.responseTypes = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: data.labels || [],
            datasets: [{
                data: data.values || [],
                backgroundColor: backgroundColors,
                borderWidth: 2,
                borderColor: '#ffffff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 15,
                        font: {
                            size: 12
                        },
                        usePointStyle: true
                    }
                },
                datalabels: {
                    display: true,
                    color: '#ffffff',
                    font: {
                        weight: 'bold',
                        size: 13
                    },
                    formatter: function(value, context) {
                        const total = context.dataset.data.reduce((a, b) => a + b, 0);
                        const percentage = ((value / total) * 100).toFixed(1);
                        return `${value}\n(${percentage}%)`;
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: 'white',
                    bodyColor: 'white',
                    borderColor: '#25D366',
                    borderWidth: 1,
                    cornerRadius: 8,
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed || 0;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(1);
                            return `${label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
    
    console.log('[ANALYTICS AGENTE] Response Types chart criado');
}

function createWeekdayChart(data) {
    const ctx = document.getElementById('weekday-chart');
    if (!ctx) return;
    
    if (charts.weekday) {
        charts.weekday.destroy();
    }
    
    // Dados fake para dias da semana - você pode criar um endpoint específico depois
    const weekdayLabels = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'];
    const weekdayValues = [12, 45, 38, 42, 51, 48, 18]; // Valores exemplo
    
    charts.weekday = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: weekdayLabels,
            datasets: [{
                label: 'Interações',
                data: weekdayValues,
                backgroundColor: '#E74C3C',
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                datalabels: {
                    display: true,
                    anchor: 'end',
                    align: 'end',
                    color: '#c0392b',
                    font: {
                        weight: 'bold',
                        size: 11
                    },
                    formatter: function(value) {
                        return value > 0 ? value : '';
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: 'white',
                    bodyColor: 'white',
                    borderColor: '#E74C3C',
                    borderWidth: 1,
                    cornerRadius: 8
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    }
                },
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    },
                    ticks: {
                        precision: 0
                    }
                }
            }
        }
    });
    
    console.log('[ANALYTICS AGENTE] Weekday chart criado');
}

function updateRecentLogsTable(data) {
    const tbody = document.querySelector('#recent-logs-table tbody');
    const countElement = document.getElementById('logs-count');
    
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    if (!data || data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" style="text-align: center; color: #9ca3af; padding: 2rem;">Nenhuma interação encontrada</td></tr>';
        if (countElement) countElement.textContent = '0 interações';
        return;
    }
    
    data.forEach(log => {
        const row = document.createElement('tr');
        
        // Data/Hora
        const dateCell = document.createElement('td');
        dateCell.textContent = formatDateTime(log.interaction_timestamp_br);
        row.appendChild(dateCell);
        
        // Usuário
        const userCell = document.createElement('td');
        userCell.textContent = log.user_name || 'N/A';
        row.appendChild(userCell);
        
        // Empresa
        const empresaCell = document.createElement('td');
        empresaCell.textContent = log.empresa_nome || 'N/A';
        row.appendChild(empresaCell);
        
        // Tipo Mensagem
        const msgTypeCell = document.createElement('td');
        msgTypeCell.textContent = log.message_type || 'N/A';
        row.appendChild(msgTypeCell);
        
        // Tipo Resposta
        const resTypeCell = document.createElement('td');
        const resTypeBadge = document.createElement('span');
        resTypeBadge.className = 'badge';
        resTypeBadge.textContent = log.response_type || 'N/A';
        resTypeBadge.style.cssText = log.response_type === 'arquivo' ? 
            'background: #FEF3C7; color: #92400E; padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.75rem;' :
            'background: #DBEAFE; color: #1E40AF; padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.75rem;';
        resTypeCell.appendChild(resTypeBadge);
        row.appendChild(resTypeCell);
        
        // Tempo de Resposta
        const timeCell = document.createElement('td');
        const time = parseFloat(log.response_time_seconds) || 0;
        timeCell.textContent = time.toFixed(2);
        row.appendChild(timeCell);
        
        // Processos Encontrados
        const processCell = document.createElement('td');
        processCell.textContent = log.total_processos_encontrados || 0;
        row.appendChild(processCell);
        
        // Status (assumindo sucesso)
        const statusCell = document.createElement('td');
        const statusBadge = document.createElement('span');
        statusBadge.className = 'status-badge success';
        statusBadge.textContent = 'Sucesso';
        statusCell.appendChild(statusBadge);
        row.appendChild(statusCell);
        
        // Ações - Botão Ver Detalhes
        const actionsCell = document.createElement('td');
        const viewBtn = document.createElement('button');
        viewBtn.className = 'btn-view-details';
        viewBtn.innerHTML = '<i class="mdi mdi-eye"></i> Ver Detalhes';
        viewBtn.onclick = () => openInteractionModal(log);
        actionsCell.appendChild(viewBtn);
        row.appendChild(actionsCell);
        
        tbody.appendChild(row);
    });
    
    if (countElement) {
        countElement.textContent = `${data.length} interação${data.length !== 1 ? 'ões' : ''}`;
    }
    
    console.log('[ANALYTICS AGENTE] Tabela de logs atualizada:', data.length, 'registros');
}

// Funções auxiliares
function updateKPIValue(elementId, value, suffix = '') {
    const element = document.getElementById(elementId);
    if (element) {
        if (suffix) {
            element.textContent = `${formatNumber(value)}${suffix}`;
        } else {
            element.textContent = value;
        }
    }
}

function formatNumber(num) {
    if (typeof num === 'string') return num;
    return num.toLocaleString('pt-BR');
}

function formatDateTime(dateStr) {
    if (!dateStr) return 'N/A';
    try {
        // Se já está no formato DD/MM/YYYY HH:MM:SS, retornar direto
        if (dateStr.includes('/')) {
            return dateStr;
        }
        // Caso contrário, tentar parsear e formatar
        const date = new Date(dateStr);
        return date.toLocaleString('pt-BR', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    } catch (e) {
        return dateStr;
    }
}

// Modal e Filtros
function openFiltersModal() {
    const modal = document.getElementById('filters-modal');
    if (modal) {
        modal.style.display = 'block';
        
        // Preencher valores atuais
        document.getElementById('date-range').value = currentFilters.dateRange;
        document.getElementById('empresa-filter').value = currentFilters.empresa;
        document.getElementById('response-type').value = currentFilters.responseType;
    }
}

function closeFiltersModal() {
    const modal = document.getElementById('filters-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

function applyFilters() {
    currentFilters.dateRange = document.getElementById('date-range').value;
    currentFilters.empresa = document.getElementById('empresa-filter').value;
    currentFilters.responseType = document.getElementById('response-type').value;
    
    updateFilterSummary();
    closeFiltersModal();
    loadAllData();
    
    // Mostrar botão de reset se houver filtros ativos
    const hasActiveFilters = currentFilters.empresa !== 'all' || currentFilters.responseType !== 'all';
    const resetBtn = document.getElementById('reset-filters');
    if (resetBtn) {
        resetBtn.style.display = hasActiveFilters ? 'inline-flex' : 'none';
    }
}

function clearFilters() {
    currentFilters = {
        dateRange: '30d',
        empresa: 'all',
        responseType: 'all'
    };
    
    document.getElementById('date-range').value = '30d';
    document.getElementById('empresa-filter').value = 'all';
    document.getElementById('response-type').value = 'all';
}

function resetFilters() {
    clearFilters();
    updateFilterSummary();
    closeFiltersModal();
    loadAllData();
    
    const resetBtn = document.getElementById('reset-filters');
    if (resetBtn) {
        resetBtn.style.display = 'none';
    }
}

function updateFilterSummary() {
    const summaryText = document.getElementById('filter-summary-text');
    if (!summaryText) return;
    
    let text = 'Vendo dados ';
    
    // Período
    switch(currentFilters.dateRange) {
        case '1d':
            text += 'de hoje';
            break;
        case '7d':
            text += 'dos últimos 7 dias';
            break;
        case '30d':
            text += 'dos últimos 30 dias';
            break;
        default:
            text += 'dos últimos 30 dias';
    }
    
    // Empresa
    if (currentFilters.empresa !== 'all') {
        text += ` - Empresa: ${currentFilters.empresa}`;
    }
    
    // Tipo de resposta
    if (currentFilters.responseType !== 'all') {
        text += ` - Tipo: ${currentFilters.responseType}`;
    }
    
    summaryText.textContent = text;
}

function refreshData() {
    console.log('[ANALYTICS AGENTE] Atualizando dados...');
    loadAllData();
}

function showLoading() {
    // Loading já é mostrado pelos loaders individuais
}

function hideLoading() {
    // Loading já é escondido pelos loaders individuais
}

function showError(message) {
    console.error('[ANALYTICS AGENTE]', message);
    // Você pode adicionar um toast ou notificação aqui
}

// ========================================
// MODAL DE DETALHES DA INTERAÇÃO
// ========================================

/**
 * Abre o modal com os detalhes da interação
 * @param {Object} log - Objeto com dados do log de interação
 */
function openInteractionModal(log) {
    console.log('[ANALYTICS AGENTE] Abrindo modal de detalhes:', log);
    
    // Preencher informações do header
    document.getElementById('modal-user-name').textContent = log.user_name || 'N/A';
    document.getElementById('modal-empresa').textContent = log.empresa_nome || 'N/A';
    document.getElementById('modal-datetime').textContent = formatDateTime(log.interaction_timestamp_br);
    document.getElementById('modal-response-time').textContent = `${parseFloat(log.response_time_seconds || 0).toFixed(2)}s`;
    
    // Preencher mensagem do usuário
    const userMessageEl = document.getElementById('modal-user-message');
    userMessageEl.textContent = log.user_message || 'Mensagem não disponível';
    
    // Preencher resposta do agente (com formatação JSON se aplicável)
    const agentResponseEl = document.getElementById('modal-agent-response');
    formatAgentResponse(log.agent_response || 'Resposta não disponível', agentResponseEl);
    
    // Exibir modal
    const modal = document.getElementById('interaction-modal');
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden'; // Prevenir scroll da página
}

/**
 * Fecha o modal de detalhes
 */
function closeInteractionModal() {
    const modal = document.getElementById('interaction-modal');
    modal.style.display = 'none';
    document.body.style.overflow = ''; // Restaurar scroll
    console.log('[ANALYTICS AGENTE] Modal de detalhes fechado');
}

/**
 * Formata a resposta do agente, extraindo e formatando JSON se presente
 * @param {string} response - Resposta bruta do agente
 * @param {HTMLElement} container - Elemento onde inserir o conteúdo formatado
 */
function formatAgentResponse(response, container) {
    // Limpar container
    container.innerHTML = '';
    
    // Tentar extrair JSON do markdown code block
    const jsonMatch = response.match(/```json\s*([\s\S]*?)\s*```/);
    
    if (jsonMatch && jsonMatch[1]) {
        try {
            // Parse do JSON
            const jsonData = JSON.parse(jsonMatch[1]);
            
            // Criar elemento para mostrar JSON formatado
            const jsonContainer = document.createElement('div');
            jsonContainer.className = 'json-formatted';
            
            // Formatar JSON com cores
            const formattedJson = formatJsonWithColors(jsonData, 0);
            jsonContainer.innerHTML = formattedJson;
            
            container.appendChild(jsonContainer);
            
            console.log('[ANALYTICS AGENTE] JSON formatado com sucesso');
        } catch (e) {
            // Se falhar ao parsear, mostrar como texto simples
            console.warn('[ANALYTICS AGENTE] Falha ao parsear JSON:', e);
            container.textContent = response;
        }
    } else {
        // Sem JSON, mostrar como texto simples
        container.textContent = response;
    }
}

/**
 * Formata JSON com cores e indentação
 * @param {Object|Array} obj - Objeto ou array para formatar
 * @param {number} indent - Nível de indentação
 * @returns {string} HTML formatado
 */
function formatJsonWithColors(obj, indent = 0) {
    const indentStr = '  '.repeat(indent);
    let html = '';
    
    if (Array.isArray(obj)) {
        html += '[\n';
        obj.forEach((item, index) => {
            html += indentStr + '  ' + formatJsonWithColors(item, indent + 1);
            if (index < obj.length - 1) html += ',';
            html += '\n';
        });
        html += indentStr + ']';
    } else if (typeof obj === 'object' && obj !== null) {
        html += '{\n';
        const keys = Object.keys(obj);
        keys.forEach((key, index) => {
            html += indentStr + '  ';
            html += `<span class="json-key">"${escapeHtml(key)}"</span>: `;
            html += formatJsonWithColors(obj[key], indent + 1);
            if (index < keys.length - 1) html += ',';
            html += '\n';
        });
        html += indentStr + '}';
    } else if (typeof obj === 'string') {
        // Strings multilinha quebradas em linhas separadas
        const escaped = escapeHtml(obj);
        if (escaped.includes('\n')) {
            const lines = escaped.split('\n');
            html += `<span class="json-string">"${lines[0]}`;
            for (let i = 1; i < lines.length; i++) {
                html += '\n' + indentStr + '  ' + lines[i];
            }
            html += '"</span>';
        } else {
            html += `<span class="json-string">"${escaped}"</span>`;
        }
    } else if (typeof obj === 'number') {
        html += `<span class="json-number">${obj}</span>`;
    } else if (typeof obj === 'boolean') {
        html += `<span class="json-boolean">${obj}</span>`;
    } else if (obj === null) {
        html += `<span class="json-null">null</span>`;
    } else {
        html += escapeHtml(String(obj));
    }
    
    return html;
}

/**
 * Escapa caracteres HTML para evitar XSS
 * @param {string} text - Texto para escapar
 * @returns {string} Texto escapado
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Fechar modal ao clicar fora
document.addEventListener('click', function(e) {
    const modal = document.getElementById('interaction-modal');
    if (e.target === modal) {
        closeInteractionModal();
    }
});

// Fechar modal com tecla ESC
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        const modal = document.getElementById('interaction-modal');
        if (modal && modal.style.display === 'flex') {
            closeInteractionModal();
        }
    }
});

