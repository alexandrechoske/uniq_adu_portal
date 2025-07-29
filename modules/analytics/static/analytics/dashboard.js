// Analytics Dashboard JavaScript
// Global variables
let timelineChart, devicesChart;
let currentPeriod = 30;
let currentUserFilter = '';

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    console.log('Analytics Dashboard - Inicializando...');
    
    // Aguardar carregamento do Chart.js
    if (typeof Chart === 'undefined') {
        console.log('Chart.js não carregado ainda, aguardando...');
        let attempts = 0;
        const checkChart = setInterval(() => {
            attempts++;
            if (typeof Chart !== 'undefined') {
                console.log('Chart.js carregado!');
                clearInterval(checkChart);
                initializeCharts();
                loadDashboardData();
                setupEventListeners();
            } else if (attempts > 50) { // 5 segundos de timeout
                console.error('Timeout esperando Chart.js');
                clearInterval(checkChart);
            }
        }, 100);
    } else {
        initializeCharts();
        loadDashboardData();
        setupEventListeners();
    }
});

function setupEventListeners() {
    // Period filter
    document.getElementById('periodFilter').addEventListener('change', function() {
        currentPeriod = parseInt(this.value);
        loadDashboardData();
    });

    // Refresh button
    document.getElementById('refreshBtn').addEventListener('click', function() {
        const icon = this.querySelector('i');
        icon.style.animation = 'spin 1s linear infinite';
        loadDashboardData().finally(() => {
            icon.style.animation = '';
        });
    });

    // User search
    document.getElementById('searchBtn').addEventListener('click', function() {
        currentUserFilter = document.getElementById('userSearch').value;
        loadSessions();
    });

    document.getElementById('userSearch').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            currentUserFilter = this.value;
            loadSessions();
        }
    });
}

function initializeCharts() {
    console.log('Inicializando gráficos...');
    
    // Timeline Chart
    const timelineCtx = document.getElementById('timelineChart');
    if (timelineCtx) {
        timelineChart = new Chart(timelineCtx.getContext('2d'), {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Total de Acessos',
                    data: [],
                    borderColor: '#3498DB',
                    backgroundColor: 'rgba(52, 152, 219, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4
                }, {
                    label: 'Logins',
                    data: [],
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    borderWidth: 2,
                    fill: false,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: '#e5e7eb'
                        }
                    },
                    x: {
                        grid: {
                            color: '#e5e7eb'
                        }
                    }
                }
            }
        });
    }

    // Devices Chart
    const devicesCtx = document.getElementById('devicesChart');
    if (devicesCtx) {
        devicesChart = new Chart(devicesCtx.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    backgroundColor: [
                        '#3498DB',
                        '#10b981',
                        '#f59e0b',
                        '#ef4444',
                        '#8b5cf6'
                    ],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }
    
    console.log('Gráficos inicializados com sucesso!');
}

async function loadDashboardData() {
    try {
        console.log('Carregando dados do dashboard...');
        
        // Load overview data
        const overviewResponse = await fetch('/analytics/api/overview');
        const overviewData = await overviewResponse.json();
        
        if (overviewData.success) {
            updateStatsCards(overviewData.data);
        }

        // Load timeline data
        const timelineResponse = await fetch(`/analytics/api/timeline?days=${currentPeriod}`);
        const timelineData = await timelineResponse.json();
        
        if (timelineData.success) {
            updateTimelineChart(timelineData.data);
        }

        // Load devices data
        const devicesResponse = await fetch(`/analytics/api/devices?days=${currentPeriod}`);
        const devicesData = await devicesResponse.json();
        
        if (devicesData.success) {
            updateDevicesChart(devicesData.data);
        }

        // Load sessions
        loadSessions();
        
        console.log('Dados carregados com sucesso!');
        
    } catch (error) {
        console.error('Erro ao carregar dados:', error);
    }
}

function updateStatsCards(data) {
    const totalAccess = document.getElementById('totalAccess');
    const uniqueUsers = document.getElementById('uniqueUsers');
    const loginsToday = document.getElementById('loginsToday');
    const activeSessions = document.getElementById('activeSessions');
    
    if (totalAccess) totalAccess.textContent = data.total_access.toLocaleString();
    if (uniqueUsers) uniqueUsers.textContent = data.unique_users.toLocaleString();
    if (loginsToday) loginsToday.textContent = data.logins_today.toLocaleString();
    if (activeSessions) activeSessions.textContent = Math.floor(Math.random() * 50) + 10; // Mock data
}

function updateTimelineChart(data) {
    if (!timelineChart || !data) return;
    
    const labels = data.map(item => {
        const date = new Date(item.date);
        return date.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' });
    });
    
    const totalData = data.map(item => item.total || 0);
    const loginData = data.map(item => item.login || 0);
    
    timelineChart.data.labels = labels;
    timelineChart.data.datasets[0].data = totalData;
    timelineChart.data.datasets[1].data = loginData;
    timelineChart.update();
}

function updateDevicesChart(data) {
    if (!devicesChart || !data) return;
    
    const devices = data.devices || {};
    const labels = Object.keys(devices);
    const values = Object.values(devices);
    
    devicesChart.data.labels = labels.map(label => {
        return label.charAt(0).toUpperCase() + label.slice(1);
    });
    devicesChart.data.datasets[0].data = values;
    devicesChart.update();
}

async function loadSessions() {
    const timeline = document.getElementById('sessionTimeline');
    if (!timeline) return;
    
    timeline.innerHTML = '<div class="loading"><div class="spinner"></div>Carregando sessões...</div>';
    
    try {
        const params = new URLSearchParams({
            limit: 20,
            user_email: currentUserFilter
        });
        
        const response = await fetch(`/analytics/api/sessions?${params}`);
        const data = await response.json();
        
        if (data.success) {
            renderSessions(data.data);
        } else {
            timeline.innerHTML = '<div class="loading">Erro ao carregar sessões</div>';
        }
    } catch (error) {
        console.error('Erro ao carregar sessões:', error);
        timeline.innerHTML = '<div class="loading">Erro ao carregar sessões</div>';
    }
}

function renderSessions(sessions) {
    const timeline = document.getElementById('sessionTimeline');
    if (!timeline) return;
    
    if (!sessions || sessions.length === 0) {
        timeline.innerHTML = '<div class="loading">Nenhuma sessão encontrada</div>';
        return;
    }
    
    timeline.innerHTML = sessions.map(session => {
        const userInitials = session.user_email ? session.user_email.substring(0, 2).toUpperCase() : 'UN';
        const startTime = new Date(session.start_time).toLocaleString('pt-BR');
        const duration = session.duration_minutes || 0;
        
        return `
            <div class="session-item">
                <div class="session-header" onclick="toggleSession('${session.session_id}')">
                    <div class="session-info">
                        <div class="user-avatar">${userInitials}</div>
                        <div class="session-details">
                            <div class="session-user">${session.user_email || 'Usuário Anônimo'}</div>
                            <div class="session-meta">
                                <span><i class="fas fa-clock"></i> ${startTime}</span>
                                <span><i class="fas fa-hourglass-half"></i> ${duration} min</span>
                                <span><i class="fas fa-laptop"></i> ${session.browser || 'Unknown'}</span>
                                <span><i class="fas fa-map-marker-alt"></i> ${session.ip_address || 'N/A'}</span>
                            </div>
                        </div>
                    </div>
                    <div class="session-stats">
                        <span class="stat-badge primary">${session.total_actions || 0} ações</span>
                        <span class="stat-badge success">${(session.pages_visited || []).length} páginas</span>
                        <i class="fas fa-chevron-down"></i>
                    </div>
                </div>
                <div id="session-${session.session_id}" class="session-actions">
                    <div class="action-timeline">
                        ${(session.actions || []).map(action => `
                            <div class="action-item">
                                <div class="action-icon ${action.action_type}">
                                    <i class="fas fa-${getActionIcon(action.action_type)}"></i>
                                </div>
                                <div class="action-content">
                                    <div class="action-title">${action.page_name || action.action_type}</div>
                                    <div class="action-time">${new Date(action.timestamp).toLocaleTimeString('pt-BR')}</div>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

function toggleSession(sessionId) {
    const element = document.getElementById(`session-${sessionId}`);
    const chevron = event.currentTarget.querySelector('.fa-chevron-down');
    
    if (!element || !chevron) return;
    
    if (element.classList.contains('active')) {
        element.classList.remove('active');
        chevron.style.transform = 'rotate(0deg)';
    } else {
        element.classList.add('active');
        chevron.style.transform = 'rotate(180deg)';
    }
}

function getActionIcon(actionType) {
    const icons = {
        'login': 'sign-in-alt',
        'logout': 'sign-out-alt',
        'page_access': 'eye',
        'api_call': 'code',
        'access_denied': 'ban'
    };
    return icons[actionType] || 'circle';
}
