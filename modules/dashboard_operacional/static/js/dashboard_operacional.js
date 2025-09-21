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
    
    // Client table expand/collapse
    document.getElementById('expand-all-clients').addEventListener('click', expandAllClients);
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
    
    currentFilters.year = year;
    currentFilters.month = month;
    
    updateFilterSummary();
    operationalCache.invalidate(); // Invalidate cache when filters change
    loadOperationalData();
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
    
    if (kpis.meta_a_realizar > 0) {
        metaRealizarEl.textContent = kpis.meta_a_realizar.toLocaleString('pt-BR');
        metaStatusEl.textContent = 'a realizar';
        metaRealizarEl.parentElement.parentElement.className = 'kpi-card kpi-purple';
    } else {
        metaRealizarEl.textContent = 'Meta Atingida';
        metaStatusEl.textContent = '✓';
        metaRealizarEl.parentElement.parentElement.className = 'kpi-card kpi-success';
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
    
    // Calculate variation
    let variationHtml = '-';
    let variationClass = 'variation-neutral';
    
    if (client.periodo_anterior > 0) {
        const variation = ((client.total_registros - client.periodo_anterior) / client.periodo_anterior * 100);
        const icon = variation >= 0 ? '↗' : '↘';
        variationHtml = `${icon} ${Math.abs(variation).toFixed(1)}%`;
        variationClass = variation >= 0 ? 'variation-positive' : 'variation-negative';
    }
    
    tr.innerHTML = `
        <td>
            <div class="expand-icon" data-action="expand">+</div>
        </td>
        <td><strong>${client.cliente}</strong></td>
        <td>${client.total_registros.toLocaleString('pt-BR')}</td>
        <td>${client.periodo_anterior.toLocaleString('pt-BR')}</td>
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
        // Load modal data for this client
        const params = new URLSearchParams();
        params.append('client', client.cliente);
        if (currentFilters.year) params.append('year', currentFilters.year);
        if (currentFilters.month) params.append('month', currentFilters.month);
        
        const response = await fetch(`/dashboard-operacional/api/client-modals?${params.toString()}`);
        const data = await response.json();
        
        if (data.success) {
            insertModalRows(clientIndex, data.data.modals);
        }
    } catch (error) {
        console.error('Erro ao carregar dados do modal:', error);
    }
}

/**
 * Insert modal rows after client row
 */
function insertModalRows(clientIndex, modals) {
    const clientRow = document.querySelector(`tr[data-client-index="${clientIndex}"]`);
    const tbody = clientRow.parentElement;
    
    modals.forEach((modal, modalIndex) => {
        const modalRow = document.createElement('tr');
        modalRow.className = 'level-1-row';
        modalRow.dataset.clientIndex = clientIndex;
        modalRow.dataset.level = '1';
        
        // Calculate modal variation
        let variationHtml = '-';
        let variationClass = 'variation-neutral';
        
        if (modal.periodo_anterior > 0) {
            const variation = ((modal.total_registros - modal.periodo_anterior) / modal.periodo_anterior * 100);
            const icon = variation >= 0 ? '↗' : '↘';
            variationHtml = `${icon} ${Math.abs(variation).toFixed(1)}%`;
            variationClass = variation >= 0 ? 'variation-positive' : 'variation-negative';
        }
        
        modalRow.innerHTML = `
            <td>
                <div class="expand-icon" data-action="expand" data-modal="${modal.modal}">+</div>
            </td>
            <td class="level-indicator">→ ${modal.modal}</td>
            <td>${modal.total_registros.toLocaleString('pt-BR')}</td>
            <td>${modal.periodo_anterior.toLocaleString('pt-BR')}</td>
            <td><span class="${variationClass}">${variationHtml}</span></td>
        `;
        
        // Add event for process expansion
        modalRow.querySelector('.expand-icon').addEventListener('click', (e) => {
            e.stopPropagation();
            toggleModalExpansion(clientIndex, modal.modal, modalRow);
        });
        
        // Insert after client row (and any existing modal rows)
        let insertAfter = clientRow;
        while (insertAfter.nextElementSibling && 
               insertAfter.nextElementSibling.dataset.clientIndex === clientIndex.toString()) {
            insertAfter = insertAfter.nextElementSibling;
        }
        
        tbody.insertBefore(modalRow, insertAfter.nextElementSibling);
    });
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
        params.append('client', client.cliente);
        params.append('modal', modal);
        if (currentFilters.year) params.append('year', currentFilters.year);
        if (currentFilters.month) params.append('month', currentFilters.month);
        
        const response = await fetch(`/dashboard-operacional/api/client-processes?${params.toString()}`);
        const data = await response.json();
        
        if (data.success) {
            insertProcessRows(clientIndex, modal, data.data.processes, modalRow);
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
 * Expand all clients
 */
function expandAllClients() {
    operationalData.clients.forEach((client, index) => {
        const expandIcon = document.querySelector(`tr[data-client-index="${index}"] .expand-icon`);
        if (expandIcon && expandIcon.dataset.action === 'expand') {
            expandIcon.click();
        }
    });
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
            <td><strong>${analyst.analista}</strong></td>
            <td>${analyst.total_registros.toLocaleString('pt-BR')}</td>
            <td>${analyst.sla_medio !== null ? analyst.sla_medio.toFixed(1) + ' dias' : '-'}</td>
            <td>${efficiency}</td>
        `;
        
        // Add hover event to show top clients popup
        tr.addEventListener('mouseenter', (e) => showAnalystPopup(e, analyst));
        tr.addEventListener('mouseleave', hideAnalystPopup);
        
        tbody.appendChild(tr);
    });
}

/**
 * Show analyst popup with top 5 clients
 */
async function showAnalystPopup(event, analyst) {
    try {
        const params = new URLSearchParams();
        params.append('analyst', analyst.analista);
        if (currentFilters.year) params.append('year', currentFilters.year);
        if (currentFilters.month) params.append('month', currentFilters.month);
        
        const response = await fetch(`/dashboard-operacional/api/analyst-clients?${params.toString()}`);
        const data = await response.json();
        
        if (data.success) {
            displayAnalystPopup(analyst.analista, data.data.clients, event);
        }
    } catch (error) {
        console.error('Erro ao carregar clientes do analista:', error);
    }
}

/**
 * Display analyst popup
 */
function displayAnalystPopup(analystName, clients, event) {
    const popup = document.getElementById('analyst-popup');
    const nameEl = document.getElementById('popup-analyst-name');
    const canvas = document.getElementById('popup-analyst-chart');
    
    nameEl.textContent = `Top 5 Clientes - ${analystName}`;
    
    // Create chart
    if (analystPopupChart) {
        analystPopupChart.destroy();
    }
    
    const ctx = canvas.getContext('2d');
    analystPopupChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: clients.map(c => c.cliente),
            datasets: [{
                label: 'Total de Registros',
                data: clients.map(c => c.total_registros),
                backgroundColor: OPERATIONAL_COLORS.primary,
                borderColor: OPERATIONAL_COLORS.primary,
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            indexAxis: 'y',
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                x: {
                    beginAtZero: true
                }
            }
        }
    });
    
    popup.style.display = 'flex';
}

/**
 * Hide analyst popup
 */
function hideAnalystPopup() {
    // Add delay to prevent immediate hiding when moving to popup
    setTimeout(() => {
        const popup = document.getElementById('analyst-popup');
        if (!popup.matches(':hover')) {
            popup.style.display = 'none';
        }
    }, 100);
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
    
    const ctx = canvas.getContext('2d');
    operationalCharts.modalChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: operationalData.distribution.modal.map(item => item.modal),
            datasets: [{
                label: 'Registros',
                data: operationalData.distribution.modal.map(item => item.total),
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
                }
            },
            scales: {
                x: {
                    beginAtZero: true
                }
            }
        }
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
    
    const ctx = canvas.getContext('2d');
    operationalCharts.canalChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: operationalData.distribution.canal.map(item => item.canal || 'Não informado'),
            datasets: [{
                label: 'Registros',
                data: operationalData.distribution.canal.map(item => item.total),
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
                }
            },
            scales: {
                x: {
                    beginAtZero: true
                }
            }
        }
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
        const dateStr = `${year}-${month.padStart(2, '0')}-${day.toString().padStart(2, '0')}`;
        const dayData = calendarData.find(d => d.date === dateStr);
        const count = dayData ? dayData.count : 0;
        
        const hasData = count > 0;
        const intensity = hasData ? Math.min(count / 10, 1) : 0; // Scale intensity
        
        html += `<div class="calendar-day ${hasData ? 'has-data' : ''}" 
                      style="${hasData ? `opacity: ${0.3 + intensity * 0.7}` : ''}"
                      title="${count} registros em ${day}/${month}/${year}">
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
        
        // Status based on days open
        let statusClass = 'badge-warning';
        let statusText = 'Atenção';
        
        if (process.dias_aberto > 30) {
            statusClass = 'badge-danger';
            statusText = 'Crítico';
        } else if (process.dias_aberto > 15) {
            statusClass = 'badge-warning';
            statusText = 'Alerta';
        }
        
        tr.innerHTML = `
            <td><strong>${process.ref_unique}</strong></td>
            <td>${process.cliente}</td>
            <td>${process.analista}</td>
            <td>${formatDate(process.data_registro)}</td>
            <td><strong>${process.dias_aberto}</strong></td>
            <td><span class="badge ${statusClass}">${statusText}</span></td>
        `;
        
        tbody.appendChild(tr);
    });
}

/**
 * Update SLA comparison chart
 */
function updateSLAComparison() {
    const canvas = document.getElementById('sla-comparison-chart');
    
    if (operationalCharts.slaChart) {
        operationalCharts.slaChart.destroy();
    }
    
    const ctx = canvas.getContext('2d');
    operationalCharts.slaChart = new Chart(ctx, {
        type: 'boxplot',
        data: {
            labels: operationalData.sla_comparison.map(item => item.analista),
            datasets: [{
                label: 'SLA (Dias)',
                data: operationalData.sla_comparison.map(item => ({
                    min: item.min_sla,
                    q1: item.q1_sla,
                    median: item.median_sla,
                    q3: item.q3_sla,
                    max: item.max_sla
                })),
                backgroundColor: OPERATIONAL_COLORS.primary + '40',
                borderColor: OPERATIONAL_COLORS.primary,
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const data = context.raw;
                            return [
                                `Mínimo: ${data.min} dias`,
                                `Q1: ${data.q1} dias`,
                                `Mediana: ${data.median} dias`,
                                `Q3: ${data.q3} dias`,
                                `Máximo: ${data.max} dias`
                            ];
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'SLA (Dias)'
                    }
                }
            }
        }
    });
}

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

function showError(message) {
    // You can implement a proper error modal here
    alert(message);
}

function formatDate(dateString) {
    if (!dateString) return '-';
    
    const date = new Date(dateString);
    return date.toLocaleDateString('pt-BR');
}

// Export for testing purposes
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        loadOperationalData,
        updateAllComponents,
        currentFilters,
        operationalCache
    };
}