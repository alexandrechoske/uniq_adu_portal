// filepath: v:\02. Desenvolvimento\Projetos - Dev\UniqueAduaneira\uniq_adu_portal\static\js\dashboard-refresh.js
// Função para mostrar o indicador de carregamento
function showLoading() {
    document.getElementById('loading-overlay').classList.remove('hidden');
}

// Função para esconder o indicador de carregamento
function hideLoading() {
    document.getElementById('loading-overlay').classList.add('hidden');
}

// Função para atualizar o dashboard 
function refreshDashboard() {
    showLoading();
    
    // Resetar contador
    countdown = 60;
    countdownElement.textContent = countdown;
    
    const currentTime = Math.floor(Date.now() / 1000); // Timestamp atual em segundos
    const timeSinceLastFetch = currentTime - lastDatabaseFetch;
    
    // Verificar se precisa buscar dados do banco (a cada 5 minutos) ou usar cache
    if (timeSinceLastFetch >= databaseFetchInterval || !cachedDashboardData) {
        console.log('Buscando dados atualizados do banco de dados (intervalo de 5 minutos)');
        
        // Buscar dados frescos do banco
        // Chamar a API de atualização para buscar os dados mais recentes do Supabase
        fetch('/dashboard/update-data', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            console.log('Resposta da atualização:', data);
            
            // Agora, obter os dados dos gráficos atualizados em formato JSON
            return fetch('/dashboard/chart-data');
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                // Atualizar cache
                cachedDashboardData = data;
                lastDatabaseFetch = currentTime;
                console.log('Dados do banco atualizados e armazenados em cache');
                
                // Atualizar interface
                updateDashboardInterface(data);
            } else {
                throw new Error('Falha ao obter dados do dashboard');
            }
        })
        .catch(error => {
            console.error('Erro ao buscar dados do banco:', error);
            
            // Se houver dados em cache, usar como fallback
            if (cachedDashboardData) {
                console.log('Usando dados em cache como fallback');
                updateDashboardInterface(cachedDashboardData);
            } else {
                console.error('Nenhum dado disponível (nem fresco nem em cache)');
                hideLoading();
            }
        });
    } else {
        console.log(`Usando dados em cache (última atualização há ${timeSinceLastFetch} segundos)`);
        // Usar dados em cache
        updateDashboardInterface(cachedDashboardData);
    }
}

// Função auxiliar para atualizar a interface com os dados
function updateDashboardInterface(data) {
    if (data.status === 'success') {
        // Atualizar KPIs
        updateKPIs(data.kpis);
        
        // Atualizar gráficos
        if (data.charts) {
            try {
                console.log("Atualizando gráficos...");
                
                if (data.charts.chart_cliente) {
                    updateChart('chart-cliente-container', data.charts.chart_cliente);
                }
                
                if (data.charts.chart_data) {
                    updateChart('chart-data-container', data.charts.chart_data);
                }
                
                if (data.charts.chart_tipo) {
                    updateChart('chart-tipo-container', data.charts.chart_tipo);
                }
                
                if (data.charts.chart_canal) {
                    updateChart('chart-canal-container', data.charts.chart_canal);
                }
            } catch (chartError) {
                console.error("Erro ao atualizar gráficos:", chartError);
                
                // Método alternativo: forçar atualização dos gráficos
                console.warn("Tentando forçar atualização dos gráficos...");
                forceUpdateCharts();
            }
        }
        
        // Atualizar timestamp
        updateTimestamp(data.last_update);
        
        console.log('Dashboard atualizado com sucesso');
    } else {
        console.error('Erro na resposta do servidor:', data);
    }
    
    hideLoading();
}

// Função para atualizar um gráfico Plotly
function updateChart(containerId, chartData) {
    try {
        const container = document.getElementById(containerId);
        if (!container) {
            console.error(`Container ${containerId} não encontrado`);
            return;
        }
        
        // Extrair o ID do gráfico a partir do ID do container ou usar o ID fornecido
        // Por exemplo, 'chart-cliente-container' -> 'chart-cliente'
        const chartId = chartData.id || containerId.replace('-container', '');
        console.log(`Atualizando gráfico ${chartId} no container ${containerId}`);
        
        // Método 1: Usar diretamente os dados JSON do Plotly para atualização
        try {
            // Verificar se temos os dados em JSON do servidor
            if (chartData.data && window.Plotly) {
                // Converter a string JSON para objeto
                const plotlyData = JSON.parse(chartData.data);
                
                // Usar newPlot para substituir completamente o gráfico com o mesmo ID
                window.Plotly.newPlot(
                    chartId, 
                    plotlyData.data, 
                    plotlyData.layout, 
                    {
                        responsive: true,
                        displayModeBar: false,
                        displaylogo: false
                    }
                );
                console.log(`Gráfico ${chartId} atualizado com sucesso via JSON`);
                return; // Método 1 bem-sucedido, não continuar
            }
            throw new Error('Dados do gráfico em formato JSON não encontrados');
        } catch (jsonError) {
            console.warn(`Método 1 falhou para ${chartId} (JSON):`, jsonError);
            
            // Método 2: Usar o HTML fornecido pelo servidor
            try {
                // Verificar se temos HTML
                if (chartData.html) {
                    // Guardar uma cópia do HTML original para caso de erro
                    const originalHTML = container.innerHTML;
                    
                    // Limpar o container e substituir pelo novo HTML
                    container.innerHTML = '';
                    container.innerHTML = chartData.html;
                    
                    // Verificar se o gráfico foi criado
                    const newChart = container.querySelector('.js-plotly-plot');
                    if (!newChart) {
                        throw new Error('O novo gráfico não foi criado corretamente');
                    }
                    
                    console.log(`Gráfico ${chartId} atualizado via substituição HTML`);
                    
                    // Redimensionar após um pequeno atraso para garantir que o DOM foi atualizado
                    setTimeout(() => {
                        try {
                            if (window.Plotly && newChart) {
                                window.Plotly.Plots.resize(newChart);
                            }
                        } catch (resizeError) {
                            console.warn(`Erro ao redimensionar ${chartId}:`, resizeError);
                        }
                    }, 100);
                    
                    return; // Método 2 bem-sucedido, não continuar
                } else {
                    throw new Error('HTML do gráfico não encontrado');
                }
            } catch (htmlError) {
                console.error(`Método 2 falhou para ${chartId} (HTML):`, htmlError);
                
                // Método 3: Recriar manualmente o gráfico (fallback)
                try {
                    // Limpar completamente o container
                    container.innerHTML = '';
                    
                    // Criar um novo div com o ID correto para o gráfico
                    const newDiv = document.createElement('div');
                    newDiv.id = chartId;
                    container.appendChild(newDiv);
                    
                    // Se temos HTML, usamos ele diretamente
                    if (chartData.html) {
                        newDiv.outerHTML = chartData.html;
                    } 
                    // Se temos dados e não HTML, tentamos plotar diretamente
                    else if (chartData.data && window.Plotly) {
                        const plotlyData = JSON.parse(chartData.data);
                        window.Plotly.newPlot(
                            chartId, 
                            plotlyData.data, 
                            plotlyData.layout, 
                            { responsive: true }
                        );
                    }
                    // Se não temos nem dados nem HTML, usamos qualquer string que temos
                    else if (typeof chartData === 'string') {
                        newDiv.outerHTML = chartData;
                    } else {
                        throw new Error('Nenhum dado disponível para reconstruir o gráfico');
                    }
                    
                    console.log(`Gráfico ${chartId} reconstruído completamente`);
                } catch (reconstructError) {
                    console.error(`Todos os métodos falharam para ${chartId}. Erro final:`, reconstructError);
                }
            }
        }
    } catch (error) {
        console.error(`Erro crítico na atualização do gráfico ${containerId}:`, error);
    }
}

// Função para atualizar os KPIs
function updateKPIs(kpis) {
    try {
        // Atualizar o total de operações
        if (kpis.total_operations !== undefined) {
            const totalOpsElement = document.querySelector('#total-operations .metric-value');
            if (totalOpsElement) {
                totalOpsElement.textContent = kpis.total_operations;
            }
        }
        
        // Atualizar processos abertos
        if (kpis.processos_abertos !== undefined) {
            const processosAbertosElement = document.querySelector('#processos-abertos .metric-value');
            if (processosAbertosElement) {
                processosAbertosElement.textContent = kpis.processos_abertos;
            }
        }
        
        // Atualizar novos na semana
        if (kpis.novos_semana !== undefined) {
            const novosSemanaElement = document.querySelector('#novos-semana .metric-value');
            if (novosSemanaElement) {
                novosSemanaElement.textContent = kpis.novos_semana;
            }
        }
        
        // Atualizar em trânsito
        if (kpis.em_transito !== undefined) {
            const emTransitoElement = document.querySelector('#em-transito .metric-value');
            if (emTransitoElement) {
                emTransitoElement.textContent = kpis.em_transito;
            }
        }
        
        // Atualizar a chegar nessa semana
        if (kpis.a_chegar_semana !== undefined) {
            const aChegarSemanaElement = document.querySelector('#a-chegar-semana .metric-value');
            if (aChegarSemanaElement) {
                aChegarSemanaElement.textContent = kpis.a_chegar_semana;
            }
        }
        
        // Atualizar variações
        if (kpis.variations) {
            // Total operations variation
            if (kpis.variations.total_var) {
                const totalVarElement = document.querySelector('#total-operations .metric-variation');
                if (totalVarElement) {
                    totalVarElement.textContent = kpis.variations.total_var;
                    if (kpis.variations.total_var.includes('+')) {
                        totalVarElement.className = 'metric-variation variation-up';
                    } else {
                        totalVarElement.className = 'metric-variation variation-down';
                    }
                }
            }
            
            // Processos abertos variation
            if (kpis.variations.abertos_var) {
                const abertosVarElement = document.querySelector('#processos-abertos .metric-variation');
                if (abertosVarElement) {
                    abertosVarElement.textContent = kpis.variations.abertos_var;
                    if (kpis.variations.abertos_var.includes('+')) {
                        abertosVarElement.className = 'metric-variation variation-up';
                    } else {
                        abertosVarElement.className = 'metric-variation variation-down';
                    }
                }
            }
            
            // Novos na semana variation
            if (kpis.variations.novos_var) {
                const novosVarElement = document.querySelector('#novos-semana .metric-variation');
                if (novosVarElement) {
                    novosVarElement.textContent = kpis.variations.novos_var;
                    if (kpis.variations.novos_var.includes('+')) {
                        novosVarElement.className = 'metric-variation variation-up';
                    } else {
                        novosVarElement.className = 'metric-variation variation-down';
                    }
                }
            }
            
            // Em trânsito variation
            if (kpis.variations.transito_var) {
                const transitoVarElement = document.querySelector('#em-transito .metric-variation');
                if (transitoVarElement) {
                    transitoVarElement.textContent = kpis.variations.transito_var;
                    if (kpis.variations.transito_var.includes('+')) {
                        transitoVarElement.className = 'metric-variation variation-up';
                    } else {
                        transitoVarElement.className = 'metric-variation variation-down';
                    }
                }
            }
            
            // A chegar nessa semana variation
            if (kpis.variations.chegar_var) {
                const chegarVarElement = document.querySelector('#a-chegar-semana .metric-variation');
                if (chegarVarElement) {
                    chegarVarElement.textContent = kpis.variations.chegar_var;
                    if (kpis.variations.chegar_var.includes('+')) {
                        chegarVarElement.className = 'metric-variation variation-up';
                    } else {
                        chegarVarElement.className = 'metric-variation variation-down';
                    }
                }
            }
        }
    } catch (error) {
        console.error('Erro ao atualizar KPIs:', error);
    }
}

// Função para atualizar o timestamp
function updateTimestamp(lastUpdate) {
    try {
        const spans = document.querySelectorAll('span');
        for (const span of spans) {
            if (span.textContent && span.textContent.includes('Última atualização:')) {
                span.textContent = `Última atualização: ${lastUpdate}`;
                break;
            }
        }
    } catch (error) {
        console.error('Erro ao atualizar timestamp:', error);
    }
}

// Função para redimensionar gráficos Plotly
function resizeGraphs() {
    const graphs = document.querySelectorAll('.js-plotly-plot');
    graphs.forEach(graph => {
        try {
            if (graph && window.Plotly) {
                window.Plotly.Plots.resize(graph);
            }
        } catch (err) {
            console.warn('Erro ao redimensionar gráfico:', err);
        }
    });
}

// Função para forçar a atualização dos gráficos em caso de falha
function forceUpdateCharts() {
    console.log("Forçando atualização dos gráficos...");
    
    // Obter novos dados via API para máxima confiabilidade
    fetch('/dashboard/chart-data')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success' && data.charts) {
                console.log("Dados obtidos com sucesso para atualização forçada");
                
                // Atualizar cada gráfico individualmente
                const charts = {
                    'chart-cliente-container': data.charts.chart_cliente,
                    'chart-data-container': data.charts.chart_data,
                    'chart-tipo-container': data.charts.chart_tipo,
                    'chart-canal-container': data.charts.chart_canal
                };
                
                Object.entries(charts).forEach(([containerId, chartData]) => {
                    if (chartData) {
                        const container = document.getElementById(containerId);
                        if (container) {
                            try {
                                // ID do gráfico (sem o -container)
                                const chartId = containerId.replace('-container', '');
                                
                                // Limpar o container
                                container.innerHTML = '';
                                
                                // Criar novo elemento para o gráfico
                                const newDiv = document.createElement('div');
                                newDiv.id = chartId;
                                container.appendChild(newDiv);
                                
                                // Usar os dados do JSON para reconstruir o gráfico
                                if (chartData.data && window.Plotly) {
                                    try {
                                        const plotlyData = JSON.parse(chartData.data);
                                        window.Plotly.newPlot(
                                            chartId, 
                                            plotlyData.data, 
                                            plotlyData.layout, 
                                            { 
                                                responsive: true,
                                                displayModeBar: false,
                                                displaylogo: false
                                            }
                                        );
                                        console.log(`Gráfico ${chartId} atualizado via força bruta (JSON)`);
                                    } catch (jsonError) {
                                        console.error(`Erro ao parsear JSON para ${chartId}:`, jsonError);
                                        
                                        // Fallback para HTML
                                        if (chartData.html) {
                                            container.innerHTML = chartData.html;
                                            console.log(`Gráfico ${chartId} atualizado via força bruta (HTML)`);
                                        }
                                    }
                                } else if (chartData.html) {
                                    container.innerHTML = chartData.html;
                                    console.log(`Gráfico ${chartId} atualizado via força bruta (HTML)`);
                                }
                            } catch (error) {
                                console.error(`Erro na atualização forçada de ${containerId}:`, error);
                            }
                        }
                    }
                });
                
                console.log("Atualização forçada concluída com sucesso");
                
                // Redimensionar todos os gráficos
                setTimeout(resizeGraphs, 200);
            } else {
                console.error("Falha ao obter dados para atualização forçada:", data);
                
                // Método alternativo - recarregar a página
                if (confirm("Não foi possível atualizar os gráficos. Deseja recarregar a página?")) {
                    window.location.reload();
                }
            }
        })
        .catch(error => {
            console.error("Erro crítico na atualização forçada:", error);
        });
}

// Inicialização quando o DOM estiver carregado
document.addEventListener('DOMContentLoaded', function() {
    // Elementos globais
    window.countdownElement = document.getElementById('countdown');
    window.countdown = 60;
    window.lastDatabaseFetch = 0; // Timestamp da última busca no banco
    window.cachedDashboardData = null; // Cache dos dados do dashboard
    window.databaseFetchInterval = 300; // 5 minutos = 300 segundos
    
    // Função de contagem regressiva
    function updateCountdown() {
        countdown--;
        countdownElement.textContent = countdown;
        
        if (countdown <= 0) {
            // Verificar se a função checkSession existe primeiro
            if (typeof checkSession === 'function') {
                // Usar a função simplificada de verificação de sessão
                checkSession().then(sessionValid => {
                    if (sessionValid) {
                        refreshDashboard();
                    } else {
                        // Se a sessão expirou, reiniciar o contador
                        countdown = 60;
                        console.log('Sessão expirada ou inválida');
                    }
                }).catch(() => {
                    // Em caso de erro, apenas atualizar
                    refreshDashboard();
                });
            } else {
                // Se a função não existir, atualizar diretamente
                refreshDashboard();
            }
            
            // Tentar recarregar o menu se a função existir
            if (typeof loadSidebarMenu === 'function') {
                loadSidebarMenu();
            }
        }
    }
    
    // Iniciar contador
    setInterval(updateCountdown, 1000);
    
    // Add resize listener with debounce for better performance
    let resizeTimer;
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(resizeGraphs, 100);
    });
});
