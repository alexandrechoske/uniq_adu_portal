function showTab(tabName) {
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.querySelectorAll('.tab-button').forEach(button => {
        button.classList.remove('active');
    });
    document.getElementById(tabName + '-content').classList.add('active');
    document.getElementById('tab-' + tabName).classList.add('active');
    if (tabName === 'executivo') {
        loadExecutivoDashboard();
    } else if (tabName === 'materiais') {
        loadMateriaisDashboard();
    }
}

function loadExecutivoDashboard() {
    const container = document.getElementById('executivo-dashboard');
    container.innerHTML = '<div>Carregando dados executivos...</div>';
    fetch('/dashboard-executivo/api/kpis')
        .then(res => res.json())
        .then(data => {
            container.innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
        })
        .catch(() => {
            container.innerHTML = '<div>Erro ao carregar dados executivos.</div>';
        });
}

function loadMateriaisDashboard() {
    const container = document.getElementById('materiais-dashboard');
    container.innerHTML = '<div>Carregando dados de materiais...</div>';
    fetch('/dashboard-materiais/api/kpis')
        .then(res => res.json())
        .then(data => {
            container.innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
        })
        .catch(() => {
            container.innerHTML = '<div>Erro ao carregar dados de materiais.</div>';
        });
}

document.addEventListener('DOMContentLoaded', function() {
    showTab('executivo');
});
