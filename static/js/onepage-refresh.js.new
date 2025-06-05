/**
 * OnePage Refresh - Versão simplificada sem dependência de cache
 */

// Função para mostrar o indicador de carregamento
function showLoading() {
    document.getElementById('loading-overlay').classList.remove('hidden');
}

// Função para esconder o indicador de carregamento
function hideLoading() {
    document.getElementById('loading-overlay').classList.add('hidden');
}

// Função para atualizar a OnePage
function refreshOnepage(forceUpdate = false) {
    showLoading();
    
    // Resetar contador global
    window.countdown = 60;
    if (window.countdownElement) {
        window.countdownElement.textContent = window.countdown;
    }
    
    // Verificar se deve buscar dados do banco (a cada 5 minutos) ou usar cache
    const currentTime = Math.floor(Date.now() / 1000); // Timestamp atual em segundos
    const timeSinceLastFetch = currentTime - (window.lastDatabaseFetch || 0);
    const shouldFetchFromDatabase = forceUpdate || timeSinceLastFetch >= window.databaseFetchInterval || !window.cachedOnepageData;
    
    // Validar sessão
    const sessionValidPromise = fetch('/paginas/check-session', {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'Cache-Control': 'no-cache'
        }
    })
    .then(response => {
        if (!response.ok) {
            if (response.status === 401) {
                console.warn("Sessão expirada durante atualização da OnePage. Redirecionando para login...");
                window.location.href = '/login';
                return Promise.reject('Sessão inválida');
            }
            throw new Error('Erro ao verificar sessão: ' + response.status);
        }
        return response.json();
    })
    .then(sessionData => {
        if (!sessionData || sessionData.status !== 'success') {
            console.warn('Sessão inválida ou expirada:', sessionData);
            return Promise.reject('Sessão inválida');
        }
        return true;
    });

    // Verificar e atualizar dados da OnePage
    sessionValidPromise
        .then(() => {
            if (shouldFetchFromDatabase) {
                console.log("Buscando dados atualizados da OnePage do banco de dados...");
                
                return fetch('/onepage/update-data', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Cache-Control': 'no-cache'
                    },
                    body: JSON.stringify({ force_update: forceUpdate })
                })
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Erro ao atualizar dados da OnePage: ' + response.status);
                    }
                    return response.json();
                })
                .then(data => {
                    console.log("Dados da OnePage atualizados com sucesso:", data);
                    
                    // Atualizar timestamp da última atualização do banco
                    window.lastDatabaseFetch = Math.floor(Date.now() / 1000);
                    
                    // Armazenar dados em cache na memória
                    window.cachedOnepageData = data;
                    
                    // Atualizar a página com os novos dados
                    updatePageWithData(data);
                    
                    return data;
                });
            } else {
                console.log("Usando dados em cache da OnePage...");
                updatePageWithData(window.cachedOnepageData);
                return window.cachedOnepageData;
            }
        })
        .catch(error => {
            console.error("Erro durante a atualização da OnePage:", error);
            // Tentar mostrar uma mensagem de erro na página
            const errorContainer = document.getElementById('error-container');
            if (errorContainer) {
                errorContainer.classList.remove('hidden');
                errorContainer.textContent = `Erro ao atualizar dados: ${error}`;
            }
        })
        .finally(() => {
            hideLoading();
            // Reiniciar o contador de atualização automática
            startCountdown();
        });
}

// Função para atualizar a página com os dados recebidos
function updatePageWithData(data) {
    if (!data) {
        console.error("Dados inválidos recebidos para atualização da página");
        return;
    }
    
    try {
        // Atualizar contador total de processos
        document.getElementById('total-processos').textContent = data.total_processos || 0;
        
        // Atualizar últimas atualizações
        const ultimasAtualizacoesContainer = document.getElementById('ultimas-atualizacoes');
        if (ultimasAtualizacoesContainer && data.ultimas_atualizacoes) {
            ultimasAtualizacoesContainer.innerHTML = '';
            
            if (data.ultimas_atualizacoes.length === 0) {
                const noDataMessage = document.createElement('div');
                noDataMessage.className = 'text-center text-gray-500 p-4';
                noDataMessage.textContent = 'Nenhuma atualização recente';
                ultimasAtualizacoesContainer.appendChild(noDataMessage);
            } else {
                data.ultimas_atualizacoes.forEach(atualizacao => {
                    const card = document.createElement('div');
                    card.className = 'bg-white rounded-lg shadow p-4 mb-4';
                    
                    const header = document.createElement('div');
                    header.className = 'flex justify-between items-center mb-2';
                    
                    const processNumber = document.createElement('h3');
                    processNumber.className = 'text-primary font-semibold';
                    processNumber.textContent = atualizacao.numero_processo || 'Sem número';
                    
                    const date = document.createElement('span');
                    date.className = 'text-gray-500 text-sm';
                    date.textContent = atualizacao.data_atualizacao || 'Data desconhecida';
                    
                    header.appendChild(processNumber);
                    header.appendChild(date);
                    card.appendChild(header);
                    
                    const status = document.createElement('div');
                    status.className = 'text-gray-700';
                    status.textContent = atualizacao.status_atual || 'Status desconhecido';
                    card.appendChild(status);
                    
                    ultimasAtualizacoesContainer.appendChild(card);
                });
            }
        }
        
        // Atualizar tabela de processos
        updateProcessTable(data.processos || []);
        
        // Atualizar gráficos
        updateCharts(data.charts || {});
        
        // Exibir timestamp da última atualização
        const lastUpdateElement = document.getElementById('ultima-atualizacao');
        if (lastUpdateElement) {
            const now = new Date();
            lastUpdateElement.textContent = `Última atualização: ${now.toLocaleTimeString()}`;
        }
        
        // Esconder mensagens de erro se existirem
        const errorContainer = document.getElementById('error-container');
        if (errorContainer) {
            errorContainer.classList.add('hidden');
        }
        
    } catch (error) {
        console.error("Erro ao atualizar elementos da página:", error);
    }
}

// Função para atualizar a tabela de processos
function updateProcessTable(processos) {
    const tableBody = document.querySelector('#processos-table tbody');
    if (!tableBody) return;
    
    tableBody.innerHTML = '';
    
    if (processos.length === 0) {
        const emptyRow = document.createElement('tr');
        const emptyCell = document.createElement('td');
        emptyCell.colSpan = 5; // Ajustar conforme o número de colunas da tabela
        emptyCell.className = 'text-center py-4 text-gray-500';
        emptyCell.textContent = 'Nenhum processo encontrado';
        emptyRow.appendChild(emptyCell);
        tableBody.appendChild(emptyRow);
    } else {
        processos.forEach(processo => {
            const row = document.createElement('tr');
            row.className = 'hover:bg-gray-50';
            
            // Número do processo
            const numeroCell = document.createElement('td');
            numeroCell.className = 'px-4 py-2 border-b';
            numeroCell.textContent = processo.numero_processo || '';
            row.appendChild(numeroCell);
            
            // Cliente
            const clienteCell = document.createElement('td');
            clienteCell.className = 'px-4 py-2 border-b';
            clienteCell.textContent = processo.cliente || '';
            row.appendChild(clienteCell);
            
            // Status
            const statusCell = document.createElement('td');
            statusCell.className = 'px-4 py-2 border-b';
            statusCell.textContent = processo.status || '';
            row.appendChild(statusCell);
            
            // Data de atualização
            const dataCell = document.createElement('td');
            dataCell.className = 'px-4 py-2 border-b';
            dataCell.textContent = processo.data_atualizacao || '';
            row.appendChild(dataCell);
            
            // Responsável
            const respCell = document.createElement('td');
            respCell.className = 'px-4 py-2 border-b';
            respCell.textContent = processo.responsavel || '';
            row.appendChild(respCell);
            
            tableBody.appendChild(row);
        });
    }
}

// Função para atualizar os gráficos
function updateCharts(chartData) {
    try {
        // Gráfico de Status
        if (chartData.status && document.getElementById('status-chart')) {
            const labels = Object.keys(chartData.status);
            const values = Object.values(chartData.status);
            
            Plotly.newPlot('status-chart', [{
                type: 'pie',
                labels: labels,
                values: values,
                textinfo: 'label+percent',
                hoverinfo: 'label+value',
                hole: 0.4,
                marker: {
                    colors: ['#1F406F', '#3498DB', '#9b59b6', '#f1c40f', '#e74c3c']
                }
            }], {
                height: 300,
                margin: { l: 0, r: 0, t: 30, b: 0 },
                showlegend: false,
                title: {
                    text: 'Status dos Processos',
                    font: {
                        size: 16
                    }
                }
            });
        }
        
        // Gráfico de Modalidades
        if (chartData.modalidades && document.getElementById('modalidades-chart')) {
            const labels = Object.keys(chartData.modalidades);
            const values = Object.values(chartData.modalidades);
            
            Plotly.newPlot('modalidades-chart', [{
                type: 'pie',
                labels: labels,
                values: values,
                textinfo: 'label+percent',
                hoverinfo: 'label+value',
                hole: 0.4,
                marker: {
                    colors: ['#2ecc71', '#f39c12', '#3498db', '#1F406F']
                }
            }], {
                height: 300,
                margin: { l: 0, r: 0, t: 30, b: 0 },
                showlegend: false,
                title: {
                    text: 'Modalidades de Operação',
                    font: {
                        size: 16
                    }
                }
            });
        }
    } catch (error) {
        console.error("Erro ao atualizar gráficos:", error);
    }
}

// Função de contagem regressiva para próxima atualização
function startCountdown() {
    if (window.countdownTimer) {
        clearInterval(window.countdownTimer);
    }
    
    window.countdown = 60; // 60 segundos
    
    // Elemento que exibe a contagem regressiva
    window.countdownElement = document.getElementById('countdown-timer');
    
    if (window.countdownElement) {
        window.countdownElement.textContent = window.countdown;
    }
    
    // Atualizar contador a cada segundo
    window.countdownTimer = setInterval(updateCountdown, 1000);
}

// Função para atualizar a contagem regressiva
function updateCountdown() {
    if (window.countdown > 0) {
        window.countdown -= 1;
        
        if (window.countdownElement) {
            // Atualizar texto do contador
            window.countdownElement.textContent = window.countdown;
            
            // Animação de pulsar nos últimos 5 segundos
            if (window.countdown <= 5) {
                window.countdownElement.classList.add('text-red-500');
                
                // Animação de pulso
                window.countdownElement.style.transform = 'scale(1.1)';
                setTimeout(() => {
                    if (window.countdownElement) {
                        window.countdownElement.style.transform = 'scale(1)';
                    }
                }, 200);
            }
        }
    } else {
        // Quando o contador chegar a zero
        clearInterval(window.countdownTimer);
        
        // Remover classes visuais
        if (window.countdownElement) {
            window.countdownElement.classList.remove('text-red-500');
        }
        
        // Atualizar a página
        refreshOnepage();
    }
}

// Inicialização quando o documento estiver pronto
document.addEventListener('DOMContentLoaded', function() {
    console.log("Inicializando OnePage...");
    
    // Definir intervalo de atualização do banco para 5 minutos (300 segundos)
    window.databaseFetchInterval = 300;
    
    // Iniciar com uma atualização completa
    refreshOnepage(true);
    
    // Adicionar evento para o botão de atualização manual
    const refreshButton = document.getElementById('refresh-button');
    if (refreshButton) {
        refreshButton.addEventListener('click', function() {
            // Força buscar do banco de dados
            refreshOnepage(true);
        });
    }
    
    // Adicionar eventos para ordenação de tabela, se o script table-sort.js estiver carregado
    if (typeof initTableSort === 'function') {
        initTableSort();
    }
});
