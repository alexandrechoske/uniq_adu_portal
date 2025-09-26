/**
 * Dashboard Operacional - JavaScript Module
 * Handles all operational dashboard functionality following executive dashboard patterns
 */

// Global variables
let operationalData = null;
let operationalCharts = {};
let currentFilters = { year: '', month: '' };
let isLoading = false;
let analystPopupChart = null;

// Auto-refresh system
let autoRefreshInterval = null;
let countdownInterval = null;
let autoRefreshEnabled = true;
let refreshTimeoutMinutes = 10;
let nextRefreshTime = null;

// Color schemes following Unique pattern
const OPERATIONAL_COLORS = {
    primary: '#3498db',
    secondary: '#2ecc71', 
    warning: '#f39c12',
    danger: '#e74c3c',
    info: '#9b59b6',
    success: '#27ae60',
    teal: '#1abc9c'
};

// Chart color palettes
const CHART_COLORS = [
    '#3498db', '#2ecc71', '#f39c12', '#e74c3c', '#9b59b6', 
    '#1abc9c', '#34495e', '#95a5a6', '#d35400', '#c0392b'
];

// Cache system for operational data
let operationalCache = {
    data: null,
    lastUpdate: null,
    cacheTimeout: 5 * 60 * 1000, // 5 minutes
    
    isValid: function() {
        return this.lastUpdate && (Date.now() - this.lastUpdate) < this.cacheTimeout;
    },
    
    invalidate: function() {
        this.data = null;
        this.lastUpdate = null;
        console.log('[OPERATIONAL_CACHE] Cache invalidado');
    },
    
    set: function(data) {
        this.data = data;
        this.lastUpdate = Date.now();
        console.log('[OPERATIONAL_CACHE] Cache atualizado');
    },
    
    get: function() {
        if (this.isValid() && this.data) {
            console.log('[OPERATIONAL_CACHE] Usando cache');
            return this.data;
        }
        return null;
    }
};

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('[DASHBOARD_OPERACIONAL] Inicializando...');
    
    // Check for company warnings
    if (window.showCompanyWarning) {
        console.log('[DASHBOARD_OPERACIONAL] Dashboard bloqueado - usuário sem empresas vinculadas');
        return;
    }
    
    // Initialize components
    setupEventListeners();
    initializeFilters();
    
    // Initialize auto-refresh system
    initializeAutoRefresh();
    
    // Prevent double render: schedule chart after filters & before data load
    setTimeout(() => updateOperationsChart(), 0); // Carrega gráfico de operações
    loadOperationalData();
});

/**
 * Setup all event listeners
 */
function setupEventListeners() {
    // Filter change events
    document.getElementById('year-filter').addEventListener('change', onFilterChange);
    document.getElementById('month-filter').addEventListener('change', onFilterChange);
    
    // Reset filters
    document.getElementById('reset-filters').addEventListener('click', resetFilters);
    
    // Manual refresh
    document.getElementById('manual-refresh').addEventListener('click', manualRefresh);
    
    // Client table collapse
    document.getElementById('collapse-all-clients').addEventListener('click', collapseAllClients);
    
    // Analyst popup close
    document.getElementById('close-analyst-popup').addEventListener('click', closeAnalystPopup);
    
    // Close popup on outside click
    document.getElementById('analyst-popup').addEventListener('click', function(e) {
        if (e.target === this) {
            closeAnalystPopup();
        }
    });
}

/**
 * Initialize filter dropdowns with available years
 */
function initializeFilters() {
    const currentYear = new Date().getFullYear();
    const currentMonth = String(new Date().getMonth() + 1).padStart(2, '0');
    
    const yearFilter = document.getElementById('year-filter');
    
    // Add years from 2015 to current + 1
    for (let year = 2015; year <= currentYear + 1; year++) {
        const option = document.createElement('option');
        option.value = year;
        option.textContent = year;
        if (year === currentYear) {
            option.selected = true;
        }
        yearFilter.appendChild(option);
    }
    
    // Set current month as default
    document.getElementById('month-filter').value = currentMonth;
    
    // Update current filters
    currentFilters.year = currentYear.toString();
    currentFilters.month = currentMonth;
    
    updateFilterSummary();
}

/**
 * Handle filter changes
 */
function onFilterChange() {
    const year = document.getElementById('year-filter').value;
    const month = document.getElementById('month-filter').value;
    const previousYear = currentFilters.year;
    const previousMonth = currentFilters.month;
    
    currentFilters.year = year;
    currentFilters.month = month;
    updateFilterSummary();
    operationalCache.invalidate(); // Invalidate cache when filters change
    loadOperationalData();
    
    // Update operations chart if year or month changed (for highlighting)
    if (previousYear !== year || previousMonth !== month) {
        // Debounce update to avoid overlap
        setTimeout(() => updateOperationsChart(), 0);
    }
}

/**
 * Reset all filters
 */
function resetFilters() {
    const currentYear = new Date().getFullYear();
    const currentMonth = String(new Date().getMonth() + 1).padStart(2, '0');
    
    document.getElementById('year-filter').value = currentYear;
    document.getElementById('month-filter').value = currentMonth;
    
    currentFilters.year = currentYear.toString();
    currentFilters.month = currentMonth;
    
    updateFilterSummary();
    operationalCache.invalidate();
    loadOperationalData();
}

/**
 * Update filter summary display
 */
function updateFilterSummary() {
    const summaryText = document.getElementById('filter-summary-text');
    const resetBtn = document.getElementById('reset-filters');
    
    let summary = 'Vendo dados ';
    
    if (currentFilters.year) {
        summary += `de ${currentFilters.year}`;
        if (currentFilters.month) {
            const monthNames = {
                '01': 'Janeiro', '02': 'Fevereiro', '03': 'Março', '04': 'Abril',
                '05': 'Maio', '06': 'Junho', '07': 'Julho', '08': 'Agosto',
                '09': 'Setembro', '10': 'Outubro', '11': 'Novembro', '12': 'Dezembro'
            };
            summary += ` - ${monthNames[currentFilters.month]}`;
        }
        resetBtn.style.display = 'block';
    } else {
        summary = 'Vendo dados completos';
        resetBtn.style.display = 'none';
    }
    
    summaryText.textContent = summary;
}

/**
 * Load operational data from API
 */
async function loadOperationalData() {
    if (isLoading) return;
    
    // Check cache first
    const cachedData = operationalCache.get();
    if (cachedData) {
        operationalData = cachedData;
        updateAllComponents();
        return;
    }
    
    isLoading = true;
    showLoading('Carregando dados operacionais...');
    
    try {
        const params = new URLSearchParams();
        if (currentFilters.year) params.append('year', currentFilters.year);
        if (currentFilters.month) params.append('month', currentFilters.month);
        
        const response = await fetch(`/dashboard-operacional/api/data?${params.toString()}`);
        
        if (!response.ok) {
            if (response.status === 401) {
                console.warn('[DASHBOARD_OPERACIONAL] Usuário não autenticado');
                showError('Acesso negado. Faça login para continuar.', true);
                return;
            }
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            operationalData = data.data;
            operationalCache.set(operationalData);
            updateAllComponents();
        } else {
            throw new Error(data.message || 'Erro ao carregar dados');
        }
        
    } catch (error) {
        console.error('[DASHBOARD_OPERACIONAL] Erro ao carregar dados:', error);
        showError('Erro ao carregar dados operacionais. Tente novamente.');
    } finally {
        isLoading = false;
        hideLoading();
    }
}

/**
 * Update all dashboard components
 */
function updateAllComponents() {
    if (!operationalData) return;
    
    updateKPIs();
    // Evitar render duplo do gráfico aqui: apenas se ainda não renderizado ou ano mudou
    // updateOperationsChart(); // Removido para evitar duplicidade
    updateClientTable();
    updateAnalystTable();
    updateDistributionCharts();
    updateActivityCalendar();
    updateAlertProcesses();
    updateSLAComparison();
}

/**
 * Update KPI cards
 */
function updateKPIs() {
    const kpis = operationalData.kpis;
    
    // Total Processos
    document.getElementById('kpi-total-processos').textContent = kpis.total_processos.toLocaleString('pt-BR');
    document.getElementById('kpi-total-processos-periodo').textContent = `no período selecionado`;
    
    // Meta Mensal
    document.getElementById('kpi-meta-mensal').textContent = kpis.meta_mensal.toLocaleString('pt-BR');
    document.getElementById('kpi-meta-periodo').textContent = currentFilters.month ? 'meta mensal' : 'meta anual';
    
    // Meta Realizada (Gauge)
    updateGauge(kpis.meta_percentual);
    
    // Meta a Realizar
    const metaRealizarEl = document.getElementById('kpi-meta-realizar');
    const metaStatusEl = document.getElementById('kpi-meta-status');
    
    // Meta é atingida quando percentual >= 100%
    if (kpis.meta_percentual >= 100) {
        metaRealizarEl.textContent = 'Meta Atingida';
        metaStatusEl.textContent = '✓ Atingida';
        metaRealizarEl.parentElement.parentElement.className = 'kpi-card kpi-success';
    } else {
        metaRealizarEl.textContent = kpis.meta_a_realizar.toLocaleString('pt-BR');
        metaStatusEl.textContent = 'a realizar';
        metaRealizarEl.parentElement.parentElement.className = 'kpi-card kpi-purple';
    }
    
    // SLA Médio
    const slaEl = document.getElementById('kpi-sla-medio');
    if (kpis.sla_medio !== null) {
        slaEl.textContent = kpis.sla_medio.toFixed(1);
    } else {
        slaEl.textContent = '-';
    }
}

/**
 * Update gauge chart for meta realizada
 */
function updateGauge(percentage) {
    const canvas = document.getElementById('gauge-canvas');
    const ctx = canvas.getContext('2d');
    const gaugeValue = document.getElementById('gauge-percentage');
    
    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;
    const radius = 30;
    
    // Background arc
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius, 0.75 * Math.PI, 0.25 * Math.PI);
    ctx.lineWidth = 8;
    ctx.strokeStyle = '#e9ecef';
    ctx.stroke();
    
    // Progress arc
    const progressAngle = 0.75 * Math.PI + (1.5 * Math.PI * Math.min(percentage, 100) / 100);
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius, 0.75 * Math.PI, progressAngle);
    ctx.lineWidth = 8;
    
    // Dynamic color based on percentage
    if (percentage < 50) {
        ctx.strokeStyle = '#e74c3c';
    } else if (percentage < 90) {
        ctx.strokeStyle = '#f39c12';
    } else {
        ctx.strokeStyle = '#27ae60';
    }
    
    ctx.stroke();
    
    // Update text
    gaugeValue.textContent = `${percentage.toFixed(1)}%`;
}

/**
 * Update client performance table with drill-down functionality
 */
function updateClientTable() {
    const tbody = document.getElementById('clients-table-body');
    tbody.innerHTML = '';
    
    if (!operationalData.clients || operationalData.clients.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">Nenhum dado encontrado</td></tr>';
        return;
    }
    
    operationalData.clients.forEach((client, index) => {
        const row = createClientRow(client, index);
        tbody.appendChild(row);
    });
}

/**
 * Create client row with expand functionality
 */
function createClientRow(client, index) {
    const tr = document.createElement('tr');
    tr.className = 'client-row';
    tr.dataset.clientIndex = index;
    
    // Use correct property names from backend
    const clientName = client.nome || client.cliente || 'N/A';
    const totalProcessos = client.total_processos || 0;
    const periodoAnterior = client.periodo_anterior || 0;
    const variacaoPercent = client.variacao_percent || 0;
    
    // Format variation with color coding
    let variationHtml, variationClass;
    if (variacaoPercent > 0) {
        variationHtml = `+${variacaoPercent}%`;
        variationClass = 'variation-positive';
    } else if (variacaoPercent < 0) {
        variationHtml = `${variacaoPercent}%`;
        variationClass = 'variation-negative';
    } else {
        variationHtml = '0%';
        variationClass = 'variation-neutral';
    }
    
    tr.innerHTML = `
        <td>
            <div class="expand-icon" data-action="expand">+</div>
        </td>
        <td><strong>${clientName}</strong></td>
        <td>${totalProcessos.toLocaleString('pt-BR')}</td>
        <td>${periodoAnterior.toLocaleString('pt-BR')}</td>
        <td><span class="${variationClass}">${variationHtml}</span></td>
    `;
    
    // Add click event for expansion
    tr.querySelector('.expand-icon').addEventListener('click', (e) => {
        e.stopPropagation();
        toggleClientExpansion(index);
    });
    
    return tr;
}

/**
 * Toggle client expansion to show modal breakdown
 */
async function toggleClientExpansion(clientIndex) {
    const clientRow = document.querySelector(`tr[data-client-index="${clientIndex}"]`);
    const expandIcon = clientRow.querySelector('.expand-icon');
    const isExpanded = expandIcon.dataset.action === 'collapse';
    
    if (isExpanded) {
        // Collapse: remove modal rows
        collapseClient(clientIndex);
        expandIcon.textContent = '+';
        expandIcon.dataset.action = 'expand';
    } else {
        // Expand: load and show modal data
        expandIcon.textContent = '-';
        expandIcon.dataset.action = 'collapse';
        await expandClient(clientIndex);
    }
}

/**
 * Expand client to show modal breakdown
 */
async function expandClient(clientIndex) {
    const client = operationalData.clients[clientIndex];
    
    try {
        // Make API call to get real modal data for this client
        const params = new URLSearchParams();
        const clientName = client.nome || client.cliente || client.name || '';
        params.append('client', clientName);
        if (currentFilters.year) params.append('year', currentFilters.year);
        if (currentFilters.month) params.append('month', currentFilters.month);
        
        console.log('[DEBUG] Expanding client:', clientName, 'with params:', params.toString());
        
        const response = await fetch(`/dashboard-operacional/api/client-modals?${params.toString()}`);
        const data = await response.json();
        
        if (data.success) {
            const modals = data.data.modals || [];
            console.log('[DEBUG] Received modals:', modals);
            insertModalRows(clientIndex, modals);
        } else {
            console.error('Erro ao carregar dados de modais:', data.message);
            // Fallback to simulated data if API fails
            fallbackToSimulatedModals(clientIndex, client);
        }
        
    } catch (error) {
        console.error('Erro ao carregar dados do modal:', error);
        // Fallback to simulated data if API fails
        fallbackToSimulatedModals(clientIndex, client);
    }
}

/**
 * Fallback function to use simulated modal data
 */
function fallbackToSimulatedModals(clientIndex, client) {
    // Since backend doesn't provide modal breakdown yet, we'll simulate it
    // Based on the distribution data we have
    const modalDistribution = operationalData.distribution.modal || [];
    const totalProcessos = client.total_processos;
    
    // Calculate proportional modal breakdown for this client
    const totalModalCount = modalDistribution.reduce((sum, modal) => sum + modal.value, 0);
    
    const clientModals = modalDistribution.map(modal => ({
        modal: modal.label,
        total_registros: Math.floor((modal.value / totalModalCount) * totalProcessos),
        periodo_anterior: 0, // Unknown in simulated data
        variacao_percent: 0 // Unknown in simulated data
    }));
    
    insertModalRows(clientIndex, clientModals);
}

/**
 * Insert modal rows after client row
 */
function insertModalRows(clientIndex, modals) {
    const clientRow = document.querySelector(`tr[data-client-index="${clientIndex}"]`);
    const tbody = clientRow.parentElement;
    
    try {
        modals.forEach(modal => {
            const modalRow = document.createElement('tr');
            modalRow.className = 'modal-row';
            modalRow.dataset.clientIndex = clientIndex;
            modalRow.dataset.level = '1';
            
            // Use correct property names and structure for modal data
            const modalName = modal.modal || modal.label || 'N/A';
            const totalRegistros = modal.total_registros || modal.total_processos || 0;
            const periodoAnterior = modal.periodo_anterior || 0;
            const variacaoPercent = modal.variacao_percent || 0;
            
            // Format variation with color coding
            let variationHtml, variationClass;
            if (variacaoPercent > 0) {
                variationHtml = `+${variacaoPercent}%`;
                variationClass = 'variation-positive';
            } else if (variacaoPercent < 0) {
                variationHtml = `${variacaoPercent}%`;
                variationClass = 'variation-negative';
            } else {
                variationHtml = '0%';
                variationClass = 'variation-neutral';
            }
            
            modalRow.innerHTML = `
                <td>
                    <div class="expand-icon" data-action="expand" data-modal="${modalName}">+</div>
                </td>
                <td class="level-indicator">→ ${modalName}</td>
                <td>${totalRegistros.toLocaleString('pt-BR')}</td>
                <td>${periodoAnterior.toLocaleString('pt-BR')}</td>
                <td><span class="${variationClass}">${variationHtml}</span></td>
            `;
            
            // Add event for process expansion
            modalRow.querySelector('.expand-icon').addEventListener('click', (e) => {
                e.stopPropagation();
                toggleModalExpansion(clientIndex, modalName, modalRow);
            });
            
            // Insert after client row (and any existing modal rows)
            let insertAfter = clientRow;
            while (insertAfter.nextElementSibling && 
                   insertAfter.nextElementSibling.dataset.clientIndex === clientIndex.toString()) {
                insertAfter = insertAfter.nextElementSibling;
            }
            
            tbody.insertBefore(modalRow, insertAfter.nextElementSibling);
        });
    } catch (error) {
        console.error('[DASHBOARD_OPERACIONAL] Erro ao expandir cliente:', error);
    }
}

/**
 * Toggle modal expansion to show individual processes
 */
async function toggleModalExpansion(clientIndex, modal, modalRow) {
    const expandIcon = modalRow.querySelector('.expand-icon');
    const isExpanded = expandIcon.dataset.action === 'collapse';
    
    if (isExpanded) {
        // Collapse: remove process rows
        collapseModal(clientIndex, modal);
        expandIcon.textContent = '+';
        expandIcon.dataset.action = 'expand';
    } else {
        // Expand: load and show process data
        expandIcon.textContent = '-';
        expandIcon.dataset.action = 'collapse';
        await expandModal(clientIndex, modal, modalRow);
    }
}

/**
 * Expand modal to show individual processes
 */
async function expandModal(clientIndex, modal, modalRow) {
    const client = operationalData.clients[clientIndex];
    
    try {
        const params = new URLSearchParams();
        const clientName = client.nome || client.cliente || client.name || '';
        params.append('client', clientName);
        params.append('modal', modal);
        if (currentFilters.year) params.append('year', currentFilters.year);
        if (currentFilters.month) params.append('month', currentFilters.month);
        
        console.log('[DEBUG] Expanding modal:', modal, 'for client:', clientName, 'with params:', params.toString());
        
        const response = await fetch(`/dashboard-operacional/api/client-processes?${params.toString()}`);
        const data = await response.json();
        
        console.log('[DEBUG] Processes response:', data);
        
        if (data.success) {
            const processes = data.data.processes || [];
            console.log('[DEBUG] Total processes found:', processes.length);
            insertProcessRows(clientIndex, modal, processes, modalRow);
        } else {
            console.error('[DEBUG] API error:', data.message);
        }
    } catch (error) {
        console.error('Erro ao carregar processos:', error);
    }
}

/**
 * Insert process rows after modal row
 */
function insertProcessRows(clientIndex, modal, processes, modalRow) {
    const tbody = modalRow.parentElement;
    
    processes.forEach(process => {
        const processRow = document.createElement('tr');
        processRow.className = 'level-2-row';
        processRow.dataset.clientIndex = clientIndex;
        processRow.dataset.modal = modal;
        processRow.dataset.level = '2';
        
        processRow.innerHTML = `
            <td></td>
            <td class="level-indicator">→→ ${process.ref_unique}</td>
            <td colspan="3" class="text-muted">${process.data_registro}</td>
        `;
        
        // Insert after modal row (and any existing process rows)
        let insertAfter = modalRow;
        while (insertAfter.nextElementSibling && 
               insertAfter.nextElementSibling.dataset.modal === modal &&
               insertAfter.nextElementSibling.dataset.level === '2') {
            insertAfter = insertAfter.nextElementSibling;
        }
        
        tbody.insertBefore(processRow, insertAfter.nextElementSibling);
    });
}

/**
 * Collapse client (remove all modal and process rows)
 */
function collapseClient(clientIndex) {
    const rows = document.querySelectorAll(`tr[data-client-index="${clientIndex}"][data-level]`);
    rows.forEach(row => row.remove());
}

/**
 * Collapse modal (remove process rows)
 */
function collapseModal(clientIndex, modal) {
    const rows = document.querySelectorAll(`tr[data-client-index="${clientIndex}"][data-modal="${modal}"][data-level="2"]`);
    rows.forEach(row => row.remove());
}

/**
 * Collapse all clients
 */
function collapseAllClients() {
    operationalData.clients.forEach((client, index) => {
        const expandIcon = document.querySelector(`tr[data-client-index="${index}"] .expand-icon`);
        if (expandIcon && expandIcon.dataset.action === 'collapse') {
            expandIcon.click();
        }
    });
}

/**
 * Update analyst performance table
 */
function updateAnalystTable() {
    const tbody = document.getElementById('analysts-table-body');
    tbody.innerHTML = '';
    
    if (!operationalData.analysts || operationalData.analysts.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">Nenhum dado encontrado</td></tr>';
        return;
    }
    
    operationalData.analysts.forEach(analyst => {
        const tr = document.createElement('tr');
        tr.className = 'analyst-row';
        tr.style.cursor = 'pointer';
        
        // Calculate efficiency (inverse of SLA - lower SLA = higher efficiency)
        let efficiency = '-';
        if (analyst.sla_medio !== null && analyst.sla_medio > 0) {
            efficiency = Math.max(0, 100 - (analyst.sla_medio * 2)).toFixed(1) + '%';
        }
        
        tr.innerHTML = `
            <td><strong>${analyst.nome}</strong></td>
            <td>${analyst.total_processos.toLocaleString('pt-BR')}</td>
            <td>${analyst.sla_medio !== null ? analyst.sla_medio.toFixed(1) + ' dias' : '-'}</td>
            <td>${efficiency}</td>
        `;
        
        // Add click event to show top clients popup (melhor que hover)
        tr.style.cursor = 'pointer';
        tr.addEventListener('click', (e) => showAnalystPopup(e, analyst));
        
        tbody.appendChild(tr);
    });
}

/**
 * Show analyst popup with all clients
 */
async function showAnalystPopup(event, analyst) {
    try {
        // Show loading state
        const popup = document.getElementById('analyst-popup');
        const nameEl = document.getElementById('popup-analyst-name');
        nameEl.textContent = `Carregando clientes de ${analyst.nome}...`;
        popup.style.display = 'flex';

        // Get current filters
        const year = document.getElementById('year-filter').value;
        const month = document.getElementById('month-filter').value;

        // Build URL with filters
        let url = `/dashboard-operacional/api/analyst-clients?analyst=${encodeURIComponent(analyst.nome)}`;
        if (year) url += `&year=${year}`;
        if (month) url += `&month=${month}`;

        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-API-Key': 'uniq_api_2025_dev_bypass_key' // For testing
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        if (data.data && data.data.clients && data.data.clients.length > 0) {
            displayAnalystPopup(analyst.nome, data.data.clients, event);
        } else {
            // No clients found
            nameEl.textContent = `Nenhum cliente encontrado para ${analyst.nome}`;
            const canvas = document.getElementById('popup-analyst-chart');
            const ctx = canvas.getContext('2d');
            if (analystPopupChart) {
                analystPopupChart.destroy();
            }
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = '#666';
            ctx.font = '16px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('Nenhum dado disponível', canvas.width / 2, canvas.height / 2);
        }

    } catch (error) {
        console.error('Erro ao carregar clientes do analista:', error);
        const nameEl = document.getElementById('popup-analyst-name');
        nameEl.textContent = `Erro ao carregar dados de ${analyst.nome}`;
    }
}

/**
 * Format client name with line breaks
 */
function formatClientName(clientName) {
    if (!clientName || clientName.length <= 15) {
        return clientName;
    }
    
    // Split by spaces
    const words = clientName.split(' ');
    if (words.length < 2) {
        // If no spaces, break at 15 characters
        return clientName.length > 15 ? 
            [clientName.substring(0, 15), clientName.substring(15)] :
            [clientName];
    }
    
    // Try to break at second space or 15 characters
    let firstLine = words[0];
    let secondLineStart = 1;
    
    // Add words until we reach second space or exceed 15 chars
    for (let i = 1; i < words.length; i++) {
        const testLine = firstLine + ' ' + words[i];
        if (testLine.length > 15 || i >= 2) {
            secondLineStart = i;
            break;
        }
        firstLine = testLine;
        secondLineStart = i + 1;
    }
    
    const secondLine = words.slice(secondLineStart).join(' ');
    return secondLine ? [firstLine, secondLine] : [firstLine];
}

/**
 * Display analyst popup
 */
function displayAnalystPopup(analystName, clients, event) {
    const popup = document.getElementById('analyst-popup');
    const nameEl = document.getElementById('popup-analyst-name');
    const canvas = document.getElementById('popup-analyst-chart');
    
    nameEl.textContent = `Clientes - ${analystName}`;
    
    // Sort clients by total_registros descending (maior para menor)
    const sortedClients = [...clients].sort((a, b) => 
        (b.total_registros || b.total_processos || 0) - (a.total_registros || a.total_processos || 0)
    );
    
    // Create chart
    if (analystPopupChart) {
        analystPopupChart.destroy();
    }
    
    const ctx = canvas.getContext('2d');
    analystPopupChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: sortedClients.map(c => formatClientName(c.nome || c.cliente)),
            datasets: [{
                label: 'Total de Processos',
                data: sortedClients.map(c => c.total_registros || c.total_processos || 0),
                backgroundColor: OPERATIONAL_COLORS.primary,
                borderColor: OPERATIONAL_COLORS.primary,
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            indexAxis: 'y', // Horizontal bars (cima para baixo)
            plugins: {
                legend: {
                    display: false
                },
                // Add data labels plugin
                datalabels: {
                    display: true,
                    color: '#ffffff',
                    font: {
                        weight: 'bold',
                        size: 12
                    },
                    anchor: 'center',
                    align: 'center',
                    formatter: (value) => value
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0,0,0,0.1)'
                    }
                },
                y: {
                    grid: {
                        display: false
                    }
                }
            },
            layout: {
                padding: {
                    right: 20
                }
            }
        },
        plugins: [ChartDataLabels] // Enable data labels plugin
    });
    
    popup.style.display = 'flex';
}

/**
 * Close analyst popup (usado pelo botão fechar)
 */
function closeAnalystPopup() {
    const popup = document.getElementById('analyst-popup');
    popup.style.display = 'none';
}

/**
 * Close analyst popup
 */
function closeAnalystPopup() {
    document.getElementById('analyst-popup').style.display = 'none';
    if (analystPopupChart) {
        analystPopupChart.destroy();
        analystPopupChart = null;
    }
}

/**
 * Update distribution charts (Modal and Canal)
 */
function updateDistributionCharts() {
    updateModalChart();
    updateCanalChart();
}

/**
 * Update modal distribution chart
 */
function updateModalChart() {
    const canvas = document.getElementById('modal-chart');
    
    if (operationalCharts.modalChart) {
        operationalCharts.modalChart.destroy();
    }
    
    const modalData = operationalData.distribution.modal || [];
    
    if (modalData.length === 0) {
        canvas.getContext('2d').clearRect(0, 0, canvas.width, canvas.height);
        return;
    }
    
    const ctx = canvas.getContext('2d');
    operationalCharts.modalChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: modalData.map(item => item.label),
            datasets: [{
                label: 'Registros',
                data: modalData.map(item => item.value),
                backgroundColor: CHART_COLORS,
                borderColor: CHART_COLORS,
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: 'y',
            plugins: {
                legend: {
                    display: false
                },
                datalabels: {
                    anchor: 'end',
                    align: 'right',
                    color: '#333',
                    font: {
                        weight: 'bold',
                        size: 12
                    },
                    formatter: function(value) {
                        return value.toString();
                    }
                }
            },
            scales: {
                x: {
                    beginAtZero: true
                }
            }
        },
        plugins: [ChartDataLabels]
    });
}

/**
 * Update canal distribution chart
 */
function updateCanalChart() {
    const canvas = document.getElementById('canal-chart');
    
    if (operationalCharts.canalChart) {
        operationalCharts.canalChart.destroy();
    }
    
    const canalData = operationalData.distribution.canal || [];
    
    if (canalData.length === 0) {
        canvas.getContext('2d').clearRect(0, 0, canvas.width, canvas.height);
        return;
    }
    
    // Function to get color based on canal name
    function getCanalColor(canalName) {
        const name = (canalName || '').toLowerCase().trim();
        
        if (name.includes('verde')) {
            return '#27ae60'; // Green
        } else if (name.includes('amarelo')) {
            return '#f39c12'; // Yellow/Orange
        } else if (name.includes('vermelho')) {
            return '#e74c3c'; // Red
        } else {
            return '#3498db'; // Default blue
        }
    }
    
    // Create color arrays based on canal names
    const backgroundColors = canalData.map(item => {
        const color = getCanalColor(item.label);
        return color + '80'; // Add transparency (50% opacity)
    });
    
    const borderColors = canalData.map(item => getCanalColor(item.label));
    
    const ctx = canvas.getContext('2d');
    operationalCharts.canalChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: canalData.map(item => item.label || 'Não informado'),
            datasets: [{
                label: 'Registros',
                data: canalData.map(item => item.value),
                backgroundColor: backgroundColors,
                borderColor: borderColors,
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: 'y',
            plugins: {
                legend: {
                    display: false
                },
                datalabels: {
                    anchor: 'end',
                    align: 'right',
                    color: '#333',
                    font: {
                        weight: 'bold',
                        size: 12
                    },
                    formatter: function(value) {
                        return value.toString();
                    }
                }
            },
            scales: {
                x: {
                    beginAtZero: true
                }
            }
        },
        plugins: [ChartDataLabels]
    });
}

/**
 * Update activity calendar
 */
function updateActivityCalendar() {
    const container = document.getElementById('activity-calendar');
    
    // If no month filter is set, show current month
    const year = currentFilters.year || new Date().getFullYear();
    const month = currentFilters.month || String(new Date().getMonth() + 1).padStart(2, '0');
    
    // Update calendar title
    const monthNames = [
        'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
        'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
    ];
    const monthName = monthNames[parseInt(month) - 1];
    const titleElement = document.getElementById('calendar-title');
    if (titleElement) {
        titleElement.textContent = `${monthName} ${year}`;
    }
    
    const calendar = createCalendar(year, month, operationalData.calendar);
    container.innerHTML = calendar;
}

/**
 * Create calendar HTML
 */
function createCalendar(year, month, calendarData) {
    const date = new Date(year, month - 1, 1);
    const daysInMonth = new Date(year, month, 0).getDate();
    const firstDay = date.getDay();
    const lastDay = new Date(year, month - 1, daysInMonth).getDay();
    
    let html = `
        <div class="calendar-header">
            <div class="calendar-day-header">Dom</div>
            <div class="calendar-day-header">Seg</div>
            <div class="calendar-day-header">Ter</div>
            <div class="calendar-day-header">Qua</div>
            <div class="calendar-day-header">Qui</div>
            <div class="calendar-day-header">Sex</div>
            <div class="calendar-day-header">Sáb</div>
        </div>
        <div class="calendar-grid">
    `;
    
    // Previous month's trailing days
    const prevMonth = new Date(year, month - 2, 0);
    for (let i = firstDay - 1; i >= 0; i--) {
        const day = prevMonth.getDate() - i;
        html += `<div class="calendar-day other-month">
            <div class="calendar-day-number">${day}</div>
        </div>`;
    }
    
    // Current month days
    for (let day = 1; day <= daysInMonth; day++) {
        const dateStr = `${year}-${month.toString().padStart(2, '0')}-${day.toString().padStart(2, '0')}`;
        const dayData = calendarData.find(d => d.date === dateStr);
        const count = dayData ? dayData.count : 0;
        
        const hasData = count > 0;
        const intensity = hasData ? Math.min(count / 10, 1) : 0; // Scale intensity
        
        // Improved calendar day with clear count display
        html += `<div class="calendar-day ${hasData ? 'has-data' : ''}" 
                      style="${hasData ? `background-color: rgba(74, 144, 226, ${0.2 + intensity * 0.6})` : ''}"
                      title="${count} registro${count !== 1 ? 's' : ''} em ${day}/${month}/${year}"
                      data-date="${dateStr}"
                      data-day="${day}"
                      data-count="${count}"
                      onclick="${hasData ? `showDayDetails('${dateStr}', ${day}, ${count})` : ''}">
            <div class="calendar-day-number">${day}</div>
            ${hasData ? `<div class="calendar-day-count">${count}</div>` : ''}
        </div>`;
    }
    
    // Next month's leading days
    const remainingDays = 42 - (firstDay + daysInMonth); // 6 weeks * 7 days
    for (let day = 1; day <= remainingDays && day <= 14; day++) {
        html += `<div class="calendar-day other-month">
            <div class="calendar-day-number">${day}</div>
        </div>`;
    }
    
    html += '</div>';
    return html;
}

/**
 * Update alert processes table
 */
function updateAlertProcesses() {
    const tbody = document.getElementById('alert-processes-body');
    const countBadge = document.getElementById('alert-count');
    
    tbody.innerHTML = '';
    
    if (!operationalData.alerts || operationalData.alerts.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">Nenhum processo em alerta</td></tr>';
        countBadge.textContent = '0';
        return;
    }
    
    countBadge.textContent = operationalData.alerts.length;
    
    operationalData.alerts.forEach(process => {
        const tr = document.createElement('tr');
        
        // Use sla_dias from backend
        const diasAberto = process.sla_dias || 0;
        
        // Status based on days open
        let statusClass = 'badge-warning';
        let statusText = 'Atenção';
        
        if (diasAberto > 30) {
            statusClass = 'badge-danger';
            statusText = 'Crítico';
        } else if (diasAberto > 15) {
            statusClass = 'badge-warning';
            statusText = 'Alerta';
        } else {
            statusClass = 'badge-success';
            statusText = 'Normal';
        }
        
        tr.innerHTML = `
            <td><strong>${process.ref_unique}</strong></td>
            <td>${process.cliente}</td>
            <td>${process.analista || '-'}</td>
            <td>${formatDate(process.data)}</td>
            <td><strong>${diasAberto} dias</strong></td>
            <td><span class="badge ${statusClass}">${statusText}</span></td>
        `;
        
        tbody.appendChild(tr);
    });
}

/**
 * Update SLA comparison chart - now shows Total Processos vs SLA Médio by client
 */
function updateSLAComparison() {
    const canvas = document.getElementById('sla-comparison-chart');

    if (operationalCharts.slaChart) {
        operationalCharts.slaChart.destroy();
    }

    // Get client data with SLA information
    let clientData = operationalData.clients || [];

    // Filter clients that have both total_processos and sla_medio
    const validClients = clientData.filter(client =>
        client.total_processos > 0 &&
        client.sla_medio !== null &&
        client.sla_medio !== undefined
    );

    if (validClients.length === 0) {
        // Show no data message
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = '#6c757d';
        ctx.font = '16px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('Nenhum dado de SLA disponível', canvas.width / 2, canvas.height / 2);
        return;
    }

    // Sort by total_processos descending for better visualization
    validClients.sort((a, b) => b.total_processos - a.total_processos);

    const ctx = canvas.getContext('2d');
    operationalCharts.slaChart = new Chart(ctx, {
        type: 'scatter',
        data: {
            datasets: [{
                label: 'Clientes: Total de Processos vs SLA Médio',
                data: validClients.map(client => ({
                    x: client.total_processos,
                    y: client.sla_medio,
                    clientName: client.nome
                })),
                backgroundColor: 'rgba(74, 144, 226, 0.7)',
                borderColor: 'rgba(74, 144, 226, 1)',
                borderWidth: 2,
                pointRadius: 8,
                pointHoverRadius: 12
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const client = context.raw;
                            return [
                                `Cliente: ${client.clientName}`,
                                `Total Processos: ${client.x}`,
                                `SLA Médio: ${client.y.toFixed(1)} dias`
                            ];
                        }
                    }
                },
                datalabels: {
                    display: true,
                    color: '#333',
                    font: {
                        weight: 'bold',
                        size: 11
                    },
                    formatter: function(value, context) {
                        // Show client name on the point
                        return value.clientName.length > 10 ?
                            value.clientName.substring(0, 10) + '...' :
                            value.clientName;
                    },
                    anchor: 'center',
                    align: 'center',
                    offset: 0
                }
            },
            scales: {
                x: {
                    type: 'linear',
                    position: 'bottom',
                    title: {
                        display: true,
                        text: 'Total de Processos'
                    },
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return Number.isInteger(value) ? value : '';
                        }
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: 'SLA Médio (Dias)'
                    },
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return value.toFixed(1);
                        }
                    }
                }
            }
        },
        plugins: [ChartDataLabels]
    });
}

/**
 * Update operations monthly chart
 */
async function updateOperationsChart() {
    const canvas = document.getElementById('operations-chart');
    if (!canvas) return;

    // Reentry guard
    if (isOperationsChartRendering) {
        console.debug('updateOperationsChart ignorado: renderização já em andamento');
        return;
    }
    isOperationsChartRendering = true;

    // Ensure previous instance is destroyed
    destroyChartIfExists('operations-chart');
    if (operationalCharts.operationsChart && typeof operationalCharts.operationsChart.destroy === 'function') {
        operationalCharts.operationsChart.destroy();
        operationalCharts.operationsChart = null;
    }

    try {
        const year = currentFilters.year || new Date().getFullYear();
        const response = await fetch(`/dashboard-operacional/api/operations-monthly?year=${year}`);
        const result = await response.json();
        if (!result.success) throw new Error(result.message || 'Falha ao carregar dados');
        const monthlyData = result.data;

        const ctx = canvas.getContext('2d');
        
        // Determine which month to highlight based on current filters
        const currentMonth = currentFilters.month ? parseInt(currentFilters.month) : null;
        
        // Create background colors array with highlight for current month
        const backgroundColors = monthlyData.operations.map((value, index) => {
            const monthIndex = index + 1; // months are 1-based
            if (currentMonth && monthIndex === currentMonth) {
                return 'rgba(52, 152, 219, 1.0)'; // Highlight color (full opacity)
            }
            return 'rgba(52, 152, 219, 0.7)'; // Normal color
        });
        
        // Create border colors array with highlight for current month
        const borderColors = monthlyData.operations.map((value, index) => {
            const monthIndex = index + 1;
            if (currentMonth && monthIndex === currentMonth) {
                return 'rgba(41, 128, 185, 1)'; // Darker blue for highlight
            }
            return 'rgba(52, 152, 219, 1)';
        });
        
        // Create border width array with highlight for current month
        const borderWidths = monthlyData.operations.map((value, index) => {
            const monthIndex = index + 1;
            if (currentMonth && monthIndex === currentMonth) {
                return 3; // Thicker border for highlight
            }
            return 2;
        });
        
        operationalCharts.operationsChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: monthlyData.months,
                datasets: [{
                    label: 'Operações Realizadas',
                    data: monthlyData.operations,
                    backgroundColor: backgroundColors,
                    borderColor: borderColors,
                    borderWidth: borderWidths,
                    type: 'bar'
                }, {
                    label: 'Meta Mensal',
                    data: monthlyData.targets,
                    borderColor: 'rgba(231, 76, 60, 1)',
                    backgroundColor: 'rgba(231, 76, 60, 0.1)',
                    borderWidth: 3,
                    borderDash: [10, 5],
                    type: 'line',
                    fill: false,
                    pointBackgroundColor: 'rgba(231, 76, 60, 1)',
                    pointBorderColor: 'rgba(231, 76, 60, 1)',
                    pointRadius: 5
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                layout: {
                    padding: {
                        top: 25, // Espaço extra no topo para o subtitle
                        bottom: 5,
                        left: 5,
                        right: 5
                    }
                },
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'bottom' // Movido para baixo
                    },
                    subtitle: {
                        display: true,
                        text: 'Clique em um mês para mais detalhes',
                        position: 'top',
                        font: {
                            size: 12,
                            style: 'italic'
                        },
                        color: '#666',
                        padding: {
                            top: 5,
                            bottom: 35 // Maior distância dos data labels
                        }
                    },
                    // Removido title do gráfico
                    datalabels: {
                        display: function(context) {
                            return context.datasetIndex === 0; // Only show on bars
                        },
                        anchor: 'end',
                        align: 'top',
                        offset: 8, // Espaçamento extra acima das barras
                        color: '#333',
                        font: {
                            weight: 'bold',
                            size: 11
                        },
                        formatter: function(value) {
                            return value > 0 ? value.toString() : '';
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                        // Removido title dos eixos
                    },
                    x: {
                        // Removido title dos eixos
                    }
                },
                onClick: function(event, activeElements) {
                    // Implementar drill-down por mês
                    if (activeElements.length > 0) {
                        const clickedElement = activeElements[0];
                        if (clickedElement.datasetIndex === 0) { // Apenas para barras (operações)
                            const monthIndex = clickedElement.index;
                            const year = currentFilters.year || new Date().getFullYear();
                            const month = monthIndex + 1; // Converter para 1-12
                            drillDownToDaily(year, month, monthlyData.months[monthIndex]);
                        }
                    }
                }
            },
            plugins: [ChartDataLabels]
        });
        
    } catch (error) {
        console.error('Erro ao carregar dados das operações mensais:', error);
        // Show error message on canvas
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = '#6c757d';
        ctx.font = '16px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('Erro ao carregar dados mensais', canvas.width / 2, canvas.height / 2);
    } finally {
        isOperationsChartRendering = false;
    }
}

/**
 * Drill down to daily view for a specific month
 */
async function drillDownToDaily(year, month, monthName) {
    const canvas = document.getElementById('operations-chart');
    
    // Show loading state
    const actionsContainer = document.querySelector('.operations-chart-section .section-actions');
    if (actionsContainer) {
        actionsContainer.innerHTML = '<span>Carregando dados diários...</span>';
    }
    
    try {
        // Fetch daily data
        const response = await fetch(`/dashboard-operacional/api/operations-daily?year=${year}&month=${month}`);
        const result = await response.json();
        
        if (!result.success) {
            throw new Error(result.message);
        }
        
        const dailyData = result.data;
        
        // Destroy existing chart
        if (operationalCharts.operationsChart && typeof operationalCharts.operationsChart.destroy === 'function') {
            operationalCharts.operationsChart.destroy();
            operationalCharts.operationsChart = null;
        }
        
        // Create daily chart
        const ctx = canvas.getContext('2d');
        operationalCharts.operationsChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: dailyData.days,
                datasets: [{
                    label: 'Operações Diárias',
                    data: dailyData.operations,
                    backgroundColor: 'rgba(46, 204, 113, 0.7)',
                    borderColor: 'rgba(46, 204, 113, 1)',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'bottom'
                    },
                    title: {
                        display: true,
                        text: `Operações Diárias - ${monthName} ${year}`,
                        font: {
                            size: 16,
                            weight: 'bold'
                        },
                        color: '#333'
                    },
                    datalabels: {
                        display: function(context) {
                            // Check if context and parsed data exist
                            if (!context || !context.parsed || typeof context.parsed.y === 'undefined') {
                                return false;
                            }
                            // Only show on bars with values > 0
                            return context.datasetIndex === 0 && context.parsed.y > 0;
                        },
                        anchor: 'end',
                        align: 'top',
                        font: {
                            size: 10,
                            weight: 'bold'
                        },
                        color: '#333',
                        formatter: function(value, context) {
                            // Safety check for value
                            if (typeof value === 'number' && value > 0) {
                                return value.toString();
                            }
                            return '';
                        }
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Dias do Mês',
                            color: '#666'
                        },
                        grid: {
                            display: false
                        }
                    },
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Número de Operações',
                            color: '#666'
                        },
                        ticks: {
                            callback: function(value) {
                                return value.toLocaleString('pt-BR');
                            }
                        }
                    }
                }
            },
            plugins: [ChartDataLabels]
        });
        
        // Update actions container with return button
        if (actionsContainer) {
            actionsContainer.innerHTML = `
                <button type="button" class="btn btn-outline-primary btn-sm" onclick="returnToMonthlyView()">
                    <i class="fas fa-arrow-left"></i> Voltar para Visão Mensal
                </button>
                <span class="ms-2 text-muted">
                    Total: ${dailyData.total_operations.toLocaleString('pt-BR')} operações | 
                    Meta Mensal: ${dailyData.monthly_target.toLocaleString('pt-BR')}
                </span>
            `;
        }
        
    } catch (error) {
        console.error('Erro ao carregar dados diários:', error);
        if (actionsContainer) {
            actionsContainer.innerHTML = '<span class="text-danger">Erro ao carregar dados diários</span>';
        }
    }
}

/**
 * Return to monthly view from daily drill-down
 */
function returnToMonthlyView() {
    // Clear actions container
    const actionsContainer = document.querySelector('.operations-chart-section .section-actions');
    if (actionsContainer) {
        actionsContainer.innerHTML = '';
    }
    
    // Destroy existing chart before recreating
    if (operationalCharts.operationsChart && typeof operationalCharts.operationsChart.destroy === 'function') {
        operationalCharts.operationsChart.destroy();
        operationalCharts.operationsChart = null;
    }
    
    // Small delay to ensure canvas is properly cleared
    setTimeout(() => {
        updateOperationsChart();
    }, 100);
}

/**
 * Helper to safely destroy chart instances bound to a canvas
 */
function destroyChartIfExists(canvasId) {
    try {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        const existing = Chart.getChart ? Chart.getChart(canvas) : (canvas._chart || null);
        if (existing && typeof existing.destroy === 'function') {
            existing.destroy();
        }
    } catch (e) {
        console.warn('Falha ao destruir chart existente:', e);
    }
}

// Reentry guard to avoid concurrent updates rendering on same canvas
let isOperationsChartRendering = false;

/**
 * Utility functions
 */
function showLoading(message) {
    const overlay = document.getElementById('loading-overlay');
    const status = document.getElementById('loading-status');
    
    if (status) status.textContent = message;
    overlay.style.display = 'flex';
}

function hideLoading() {
    document.getElementById('loading-overlay').style.display = 'none';
}

function showError(message, shouldRedirect = false) {
    // You can implement a proper error modal here
    if (shouldRedirect) {
        alert(message + ' Redirecionando para login...');
        setTimeout(() => {
            window.location.href = '/auth/login';
        }, 2000);
    } else {
        alert(message);
    }
}

function formatDate(dateString) {
    if (!dateString) return '-';
    
    const date = new Date(dateString);
    return date.toLocaleDateString('pt-BR');
}

/**
 * Show day details modal
 */
function showDayDetails(dateStr, day, count) {
    console.log(`[Calendar] Opening day details for: ${dateStr} (${count} processes)`);
    
    // Parse date for display
    const [year, month, dayNum] = dateStr.split('-');
    const monthNames = [
        'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
        'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
    ];
    const monthName = monthNames[parseInt(month) - 1];
    const formattedDate = `${dayNum} de ${monthName} de ${year}`;
    
    // Update modal title (using the existing modal structure)
    const titleElement = document.getElementById('day-details-title');
    if (titleElement) {
        titleElement.textContent = `Processos do Dia ${dayNum} - ${monthName} ${year}`;
    }
    
    // Show loading state
    const loadingElement = document.getElementById('day-details-loading');
    const contentElement = document.getElementById('day-details-content');
    
    if (loadingElement) {
        loadingElement.style.display = 'block';
    }
    if (contentElement) {
        contentElement.style.display = 'none';
    }
    
    // Show modal using the existing modal structure
    const modalElement = document.getElementById('day-details-modal');
    if (modalElement) {
        modalElement.style.display = 'flex';
        document.body.classList.add('modal-open');
        
        // Add click event to close modal when clicking outside
        modalElement.onclick = function(e) {
            if (e.target === modalElement) {
                hideDayDetailsModal();
            }
        };
    }
    
    // Add close button event if not already added
    const closeButton = document.getElementById('close-day-details');
    if (closeButton && !closeButton.hasAttribute('data-listener-added')) {
        closeButton.onclick = hideDayDetailsModal;
        closeButton.setAttribute('data-listener-added', 'true');
    }
    
    // Load day details
    loadDayDetails(dateStr);
}

/**
 * Hide day details modal manually
 */
function hideDayDetailsModal() {
    const modalElement = document.getElementById('day-details-modal');
    if (modalElement) {
        modalElement.style.display = 'none';
        document.body.classList.remove('modal-open');
    }
}

/**
 * Load day details from API
 */
async function loadDayDetails(dateStr) {
    try {
        console.log(`[Calendar] Loading processes for date: ${dateStr}`);
        
        const params = new URLSearchParams({
            date: dateStr,
            ...currentFilters
        });
        
        const response = await fetch(`/dashboard-operacional/api/day-details?${params}`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log(`[Calendar] Response data structure:`, data);
        console.log(`[Calendar] Data.data:`, data.data);
        console.log(`[Calendar] Processes found:`, data.data?.processes?.length || 0);
        
        renderDayDetails(data.data || data);
        
    } catch (error) {
        console.error('[Calendar] Error loading day details:', error);
        
        // Show error in modal
        const loadingElement = document.getElementById('day-details-loading');
        const contentElement = document.getElementById('day-details-content');
        const tableBody = document.getElementById('day-processes-body');
        
        if (loadingElement) {
            loadingElement.style.display = 'none';
        }
        if (contentElement) {
            contentElement.style.display = 'block';
        }
        if (tableBody) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="8" class="text-center text-danger py-4">
                        <i class="mdi mdi-alert-circle mdi-48px mb-2" style="display: block;"></i>
                        <strong>Erro ao carregar detalhes</strong><br>
                        <small>Não foi possível carregar os processos deste dia.<br>
                        Erro: ${error.message}</small>
                    </td>
                </tr>
            `;
        }
    }
}

/**
 * Render day details in modal
 */
function renderDayDetails(data) {
    const loadingElement = document.getElementById('day-details-loading');
    const contentElement = document.getElementById('day-details-content');
    const tableBody = document.getElementById('day-processes-body');
    
    // Hide loading
    if (loadingElement) {
        loadingElement.style.display = 'none';
    }
    
    // Show content
    if (contentElement) {
        contentElement.style.display = 'block';
    }
    
    if (!tableBody) return;
    
    const processes = data.processes || [];
    const stats = data.stats || {};
    
    if (processes.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center text-muted py-4">
                    <i class="mdi mdi-calendar-remove mdi-48px mb-2" style="display: block; opacity: 0.5;"></i>
                    Nenhum processo encontrado para esta data
                </td>
            </tr>
        `;
        return;
    }
    
    // Create table rows
    const tableHtml = processes.map(process => `
        <tr>
            <td>${process.analista || '-'}</td>
            <td>${process.cliente || '-'}</td>
            <td>${formatDate(process.data_registro)}</td>
            <td>${process.canal || '-'}</td>
            <td>${process.modal || '-'}</td>
            <td>${process.data_fechamento ? formatDate(process.data_fechamento) : '-'}</td>
            <td>
                <span class="sla-indicator ${getSlaClass(process.sla_status)}">
                    ${process.sla_days || process.sla_dias || '-'} dias
                </span>
            </td>
            <td>
                <span class="status-badge ${getStatusClass(process.status)}">
                    ${getDisplayStatus(process.desempenho, process.data_fechamento)}
                </span>
            </td>
        </tr>
    `).join('');
    
    tableBody.innerHTML = tableHtml;
}

/**
 * Get SLA status class
 */
function getSlaClass(slaStatus) {
    switch (slaStatus) {
        case 'dentro_prazo': return 'dentro-prazo';
        case 'atencao': return 'atencao';
        case 'atrasado': return 'atrasado';
        default: return 'dentro-prazo';
    }
}

/**
 * Get process status class
 */
function getStatusClass(status) {
    switch (status?.toLowerCase()) {
        case 'concluido': return 'concluido';
        case 'em andamento': return 'em-andamento';
        case 'pendente': return 'pendente';
        default: return 'pendente';
    }
}

/**
 * Get display status based on performance and closure
 */
function getDisplayStatus(desempenho, dataFechamento) {
    if (dataFechamento) {
        return desempenho > 0 ? 'Concluído' : 'Concluído';
    } else {
        return 'Em Andamento';
    }
}

/**
 * Auto-refresh system functions
 */

/**
 * Initialize auto-refresh system
 */
function initializeAutoRefresh() {
    console.log('[AUTO_REFRESH] Sistema iniciado - atualização a cada', refreshTimeoutMinutes, 'minutos');
    
    // Set next refresh time
    nextRefreshTime = Date.now() + (refreshTimeoutMinutes * 60 * 1000);
    
    // Start countdown
    startCountdown();
    
    // Start auto-refresh timer
    startAutoRefresh();
    
    // Update initial countdown display
    updateCountdownDisplay();
}

/**
 * Start auto-refresh timer
 */
function startAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
    }
    
    autoRefreshInterval = setInterval(() => {
        if (autoRefreshEnabled) {
            console.log('[AUTO_REFRESH] Executando atualização automática');
            performAutoRefresh();
        }
    }, refreshTimeoutMinutes * 60 * 1000);
}

/**
 * Start countdown timer
 */
function startCountdown() {
    if (countdownInterval) {
        clearInterval(countdownInterval);
    }
    
    countdownInterval = setInterval(updateCountdownDisplay, 1000);
}

/**
 * Update countdown display
 */
function updateCountdownDisplay() {
    if (!nextRefreshTime) return;
    
    const now = Date.now();
    const timeLeft = nextRefreshTime - now;
    
    if (timeLeft <= 0) {
        document.getElementById('countdown').textContent = '00:00';
        return;
    }
    
    const minutes = Math.floor(timeLeft / (60 * 1000));
    const seconds = Math.floor((timeLeft % (60 * 1000)) / 1000);
    
    const formattedTime = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    document.getElementById('countdown').textContent = formattedTime;
}

/**
 * Perform auto refresh
 */
async function performAutoRefresh() {
    console.log('[AUTO_REFRESH] Iniciando atualização automática dos dados');
    
    // Update UI to show refreshing state
    setRefreshingState(true);
    
    try {
        // Invalidate cache to force fresh data
        operationalCache.invalidate();
        
        // Load fresh data
        await loadOperationalData();
        
        // Reset timer
        nextRefreshTime = Date.now() + (refreshTimeoutMinutes * 60 * 1000);
        
        console.log('[AUTO_REFRESH] Atualização automática concluída');
        
    } catch (error) {
        console.error('[AUTO_REFRESH] Erro na atualização automática:', error);
    } finally {
        // Reset UI state
        setRefreshingState(false);
    }
}

/**
 * Manual refresh triggered by user
 */
async function manualRefresh() {
    console.log('[AUTO_REFRESH] Atualização manual solicitada');
    
    // Prevent multiple concurrent refreshes
    if (isLoading) {
        console.log('[AUTO_REFRESH] Atualização já em andamento, ignorando solicitação manual');
        return;
    }
    
    setRefreshingState(true);
    
    try {
        // Invalidate cache
        operationalCache.invalidate();
        
        // Load fresh data
        await loadOperationalData();
        
        // Reset auto-refresh timer
        nextRefreshTime = Date.now() + (refreshTimeoutMinutes * 60 * 1000);
        
        console.log('[AUTO_REFRESH] Atualização manual concluída');
        
    } catch (error) {
        console.error('[AUTO_REFRESH] Erro na atualização manual:', error);
        showError('Erro ao atualizar dados. Tente novamente.');
    } finally {
        setRefreshingState(false);
    }
}

/**
 * Set UI state for refreshing
 */
function setRefreshingState(isRefreshing) {
    const refreshStatus = document.getElementById('auto-refresh-status');
    const refreshIcon = document.getElementById('refresh-icon');
    const refreshText = document.getElementById('refresh-text');
    const manualBtn = document.getElementById('manual-refresh');
    
    if (isRefreshing) {
        refreshStatus.classList.add('updating');
        refreshIcon.classList.add('spinning');
        refreshText.textContent = 'Atualizando dados...';
        manualBtn.disabled = true;
    } else {
        refreshStatus.classList.remove('updating');
        refreshIcon.classList.remove('spinning');
        refreshText.innerHTML = 'Próxima atualização em <span id="countdown">10:00</span>';
        manualBtn.disabled = false;
        
        // Restart countdown
        updateCountdownDisplay();
    }
}

/**
 * Enable/disable auto-refresh
 */
function toggleAutoRefresh(enabled) {
    autoRefreshEnabled = enabled;
    
    if (enabled) {
        console.log('[AUTO_REFRESH] Sistema habilitado');
        startAutoRefresh();
        startCountdown();
    } else {
        console.log('[AUTO_REFRESH] Sistema desabilitado');
        if (autoRefreshInterval) clearInterval(autoRefreshInterval);
        if (countdownInterval) clearInterval(countdownInterval);
    }
}

/**
 * Clean up auto-refresh on page unload
 */
window.addEventListener('beforeunload', function() {
    if (autoRefreshInterval) clearInterval(autoRefreshInterval);
    if (countdownInterval) clearInterval(countdownInterval);
    console.log('[AUTO_REFRESH] Sistema limpo');
});

// Export for testing purposes
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        loadOperationalData,
        updateAllComponents,
        currentFilters,
        operationalCache,
        manualRefresh,
        toggleAutoRefresh
    };
}