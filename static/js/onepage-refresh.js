// Função para mostrar o indicador de carregamento
function showLoading() {
    document.getElementById('loading-overlay').classList.remove('hidden');
}

// Função para esconder o indicador de carregamento
function hideLoading() {
    document.getElementById('loading-overlay').classList.add('hidden');
}

// Função para atualizar a OnePage
function refreshOnepage() {
    showLoading();
    
    // Resetar contador global
    window.countdown = 60;
    if (window.countdownElement) {
        window.countdownElement.textContent = window.countdown;
    }
    
    // Primeiro verificar se a sessão está válida
    fetch('/paginas/check-session', {
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
        
        console.log('Sessão validada, prosseguindo com atualização');
        
        // Chamar a API de atualização para buscar os dados mais recentes do Supabase
        return fetch('/onepage/update-data', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
    })    .then(response => {
        if (!response.ok) {
            console.error('Erro ao atualizar dados:', response.status);
            // Converter resposta em JSON para possível mensagem de erro
            return response.json().then(errorData => {
                console.warn('Falha na atualização principal, tentando método alternativo...');
                // Tentar método alternativo de atualização
                return fetch('/onepage/bypass-update', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                }).then(fallbackResponse => {
                    if (!fallbackResponse.ok) {
                        throw new Error(`Falha também no método alternativo: ${fallbackResponse.status}`);
                    }
                    return fallbackResponse.json();
                });
            }).catch(() => {
                // Tentar método alternativo mesmo sem conseguir extrair a mensagem de erro original
                console.warn('Tentando método alternativo após exceção...');
                return fetch('/onepage/bypass-update', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                }).then(fallbackResponse => {
                    if (!fallbackResponse.ok) {
                        throw new Error(`Erro ${response.status} ao atualizar dados, e o método alternativo falhou`);
                    }
                    return fallbackResponse.json();
                }).catch(fallbackError => {
                    throw new Error(`Erro ${response.status} ao atualizar dados: ${fallbackError.message}`);
                });
            });
        }
        return response.json();
    }).then(data => {
        console.log('Resposta da atualização:', data);
        
        if (data.status === 'error') {
            console.warn('Erro retornado pelo servidor:', data.message);
            // Mostrar mensagem para o usuário sem interromper o fluxo
            const errorMessage = document.createElement('div');
            errorMessage.className = 'fixed top-4 right-4 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded z-50 animate-fadeIn';
            errorMessage.innerHTML = `
                <div class="flex">
                    <div class="py-1">
                        <svg class="h-6 w-6 text-red-500 mr-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                        </svg>
                    </div>
                    <div>
                        <p class="font-bold">Erro na atualização</p>
                        <p class="text-sm">${data.message}</p>
                    </div>
                </div>
            `;
            document.body.appendChild(errorMessage);
            
            // Remover após 5 segundos
            setTimeout(() => {
                errorMessage.style.opacity = '0';
                setTimeout(() => errorMessage.remove(), 500);
            }, 5000);
            
            // Mesmo com erro na atualização, tentar obter dados atuais
            console.log("Tentando obter dados existentes mesmo após erro na atualização...");
        }
        
        // Agora, obter os dados atualizados
        return fetch('/onepage/page-data');
    })    .then(response => {
        if (!response.ok) {
            console.error('Erro ao obter dados da página:', response.status);
            throw new Error(`Erro ${response.status} ao obter dados da página`);
        }
        return response.json();
    })
    .then(data => {
        if (data.status === 'success') {
            // Atualizar KPIs
            updateKPIs(data.kpis);
            
            // Atualizar tabela
            updateTable(data.table_data);
            
            // Atualizar taxas de câmbio
            if (data.currencies) {
                updateCurrencyRates(data.currencies);
            }
            
            // Atualizar timestamp
            updateTimestamp(data.last_update);
            
            console.log('OnePage atualizada com sucesso');
        } else {
            console.error('Erro na resposta do servidor:', data);
            // Método de fallback: recarregar a página
            console.warn("Tentando recarregar a página...");
            window.location.reload();
        }
        
        hideLoading();
    })
    .catch(error => {
        console.error('Erro ao atualizar onepage:', error);
        hideLoading();
        
        // Verificar se o erro está relacionado com a sessão
        if (error.toString().includes('401') || error.toString().includes('sessão') || error.toString().includes('Sessão')) {
            console.warn('Possível problema de sessão detectado. Verificando status...');
            
            // Verificar status da sessão
            fetch('/paginas/check-session', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'Cache-Control': 'no-cache'
                }
            })
            .then(response => {
                if (!response.ok) {
                    console.warn('Sessão inválida. Redirecionando para login...');
                    window.location.href = '/login';
                } else {
                    // Exibir notificação não intrusiva
                    showErrorNotification(
                        "Atualização Automática Falhou", 
                        "A atualização automática encontrou um erro. Os dados podem estar desatualizados.",
                        false
                    );
                }
            })
            .catch(() => {
                showErrorNotification(
                    "Erro de Conexão", 
                    "Não foi possível verificar o status da sessão ou atualizar os dados.",
                    true
                );
            });
        } else if (error.toString().includes('500')) {
            // Erro do servidor
            console.warn('Erro 500 detectado, possível problema com a API de atualização');
            
            // Tentar obter dados da página diretamente sem atualização
            fetch('/onepage/page-data')
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        // Ainda conseguimos mostrar os dados atuais
                        updateKPIs(data.kpis);
                        updateTable(data.table_data);
                        if (data.currencies) {
                            updateCurrencyRates(data.currencies);
                        }
                        updateTimestamp(data.last_update);
                        
                        // Mostrar notificação de erro não-bloqueante
                        showErrorNotification(
                            "Aviso de Atualização", 
                            "A atualização dos dados falhou, mas exibimos os dados disponíveis.",
                            false
                        );
                    }
                })
                .catch(() => {
                    showErrorNotification(
                        "Erro de Carregamento", 
                        "Não foi possível obter os dados atuais. Considere recarregar a página.",
                        true
                    );
                });
        } else {
            // Para outros erros, mostrar notificação não intrusiva
            showErrorNotification(
                "Erro de Atualização", 
                "Ocorreu um erro ao atualizar os dados: " + error.toString().substring(0, 100),
                true
            );
        }
    });
      // Função auxiliar para exibir notificações de erro não-intrusivas
    function showErrorNotification(title, message, isError) {
        // Adicionar estilo para animações se não existir
        if (!document.getElementById('notification-styles')) {
            const styleEl = document.createElement('style');
            styleEl.id = 'notification-styles';
            styleEl.textContent = `
                @keyframes slideInRight {
                    from { transform: translateX(100%); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
                @keyframes fadeOut {
                    from { opacity: 1; }
                    to { opacity: 0; }
                }
                .notification-slide-in {
                    animation: slideInRight 0.4s ease forwards;
                }
                .notification-fade-out {
                    animation: fadeOut 0.5s ease forwards;
                }
            `;
            document.head.appendChild(styleEl);
        }
        
        // Remover notificações anteriores
        document.querySelectorAll('.error-notification').forEach(el => {
            el.classList.add('notification-fade-out');
            setTimeout(() => el.remove(), 500);
        });
        
        // Criar nova notificação
        const notification = document.createElement('div');
        notification.className = `error-notification fixed top-4 right-4 ${isError ? 'bg-red-100 border border-red-400 text-red-700' : 'bg-yellow-100 border border-yellow-400 text-yellow-700'} px-4 py-3 rounded z-50 shadow-lg`;
        notification.style.maxWidth = '350px';
        notification.style.transform = 'translateX(100%)';
        notification.style.opacity = '0';
        
        notification.innerHTML = `
            <div class="flex justify-between items-start">
                <div class="flex">
                    <div class="py-1">
                        <svg class="h-6 w-6 ${isError ? 'text-red-500' : 'text-yellow-500'} mr-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path>
                        </svg>
                    </div>
                    <div>
                        <p class="font-bold">${title}</p>
                        <p class="text-sm">${message}</p>
                    </div>
                </div>
                <button class="ml-4" onclick="dismissNotification(this.parentNode.parentNode)">
                    <svg class="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"></path>
                    </svg>
                </button>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // Aplicar animação após inserir no DOM
        setTimeout(() => {
            notification.classList.add('notification-slide-in');
        }, 10);
        
        // Auto-remover após 8 segundos
        setTimeout(() => {
            if (document.body.contains(notification)) {
                dismissNotification(notification);
            }
        }, 8000);
    }
    
    // Função para remover notificação com animação
    function dismissNotification(notification) {
        notification.classList.add('notification-fade-out');
        setTimeout(() => {
            if (document.body.contains(notification)) {            notification.remove();
            }
        }, 500);
    }
}

// Função para atualizar os KPIs
function updateKPIs(kpis) {
    try {
        // Atualizar valores dos KPIs
        if (kpis.total !== undefined) {
            const totalElement = document.querySelector('.metric-card:nth-child(1) .metric-value');
            if (totalElement) {
                totalElement.textContent = kpis.total;
            }
        }
        
        if (kpis.aereo !== undefined) {
            const aereoElement = document.querySelector('.grid.grid-cols-1.md\\:grid-cols-7 .metric-card:nth-child(1) .metric-value');
            if (aereoElement) {
                aereoElement.textContent = kpis.aereo;
            }
        }
        
        if (kpis.terrestre !== undefined) {
            const terrestreElement = document.querySelector('.grid.grid-cols-1.md\\:grid-cols-7 .metric-card:nth-child(2) .metric-value');
            if (terrestreElement) {
                terrestreElement.textContent = kpis.terrestre;
            }
        }
        
        if (kpis.maritimo !== undefined) {
            const maritimoElement = document.querySelector('.grid.grid-cols-1.md\\:grid-cols-7 .metric-card:nth-child(3) .metric-value');
            if (maritimoElement) {
                maritimoElement.textContent = kpis.maritimo;
            }
        }
        
        if (kpis.aguardando_chegada !== undefined) {
            const aguardandoChegadaElement = document.querySelector('.grid.grid-cols-1.md\\:grid-cols-7 .metric-card:nth-child(5) .metric-value');
            if (aguardandoChegadaElement) {
                aguardandoChegadaElement.textContent = kpis.aguardando_chegada;
            }
        }
        
        if (kpis.aguardando_embarque !== undefined) {
            const aguardandoEmbarqueElement = document.querySelector('.grid.grid-cols-1.md\\:grid-cols-7 .metric-card:nth-child(6) .metric-value');
            if (aguardandoEmbarqueElement) {
                aguardandoEmbarqueElement.textContent = kpis.aguardando_embarque;
            }
        }
        
        if (kpis.di_registrada !== undefined) {
            const diRegistradaElement = document.querySelector('.grid.grid-cols-1.md\\:grid-cols-7 .metric-card:nth-child(7) .metric-value');
            if (diRegistradaElement) {
                diRegistradaElement.textContent = kpis.di_registrada;
            }
        }
    } catch (error) {
        console.error('Erro ao atualizar KPIs:', error);
    }
}

// Função para atualizar a tabela de dados
function updateTable(tableData) {
    try {
        const tableBody = document.querySelector('.data-table tbody');
        if (!tableBody) {
            console.error('Corpo da tabela não encontrado');
            return;
        }
        
        // Limpar tabela atual
        tableBody.innerHTML = '';
        
        if (tableData.length === 0) {
            // Se não há dados, mostrar mensagem de "Nenhum processo encontrado"
            const emptyRow = document.createElement('tr');
            emptyRow.innerHTML = `
                <td colspan="9" class="px-6 py-4 text-center text-sm text-slate-500 empty-state">
                    Nenhum processo encontrado
                </td>
            `;
            tableBody.appendChild(emptyRow);
            return;
        }
        
        // Preencher com novos dados
        for (const row of tableData) {
            const tableRow = document.createElement('tr');
            
            // Célula: Número DI
            tableRow.innerHTML += `
                <td class="px-6 py-4 whitespace-nowrap text-sm text-slate-900">${row.numero || ' '}</td>
            `;
            
            // Célula: Embarque
            tableRow.innerHTML += `
                <td class="px-6 py-4 whitespace-nowrap text-sm text-slate-900">${row.data_embarque || ' '}</td>
            `;
            
            // Célula: Modal (com imagens)
            let modalHtml = '';
            if (row.via_transporte_descricao === 'AEREA') {
                modalHtml = `<img src="/static/medias/aereo.png" alt="Aéreo" class="h-6 w-auto inline-block">`;
            } else if (row.via_transporte_descricao === 'TERRESTRE') {
                modalHtml = `<img src="/static/medias/terrestre.png" alt="Terrestre" class="h-6 w-auto inline-block">`;
            } else if (row.via_transporte_descricao === 'MARITIMA') {
                modalHtml = `<img src="/static/medias/maritimo.png" alt="Marítimo" class="h-6 w-auto inline-block">`;
            } else {
                modalHtml = row.via_transporte_descricao || ' ';
            }
            tableRow.innerHTML += `
                <td class="px-6 py-4 whitespace-nowrap text-sm text-slate-900 img_modal">${modalHtml}</td>
            `;
            
            // Célula: Registro
            tableRow.innerHTML += `
                <td class="px-6 py-4 whitespace-nowrap text-sm text-slate-900">${row.data_registro || ' '}</td>
            `;
            
            // Célula: REF UNIQUE
            tableRow.innerHTML += `
                <td class="px-6 py-4 whitespace-nowrap text-sm text-slate-900">${row.ref_unique || ' '}</td>
            `;
            
            // Célula: Status (com classes de cores)
            let statusClass = '';
            if (row.carga_status === '1 - Aguardando Embarque') {
                statusClass = 'text-orange-600 font-semibold status-aguardando-embarque';
            } else if (row.carga_status === '2 - Em Trânsito') {
                statusClass = 'text-blue-600 font-semibold status-em-transito';
            } else if (row.carga_status === '3 - Desembarcada') {
                statusClass = 'text-green-600 font-semibold status-desembarcada';
            }
            tableRow.innerHTML += `
                <td class="px-6 py-4 whitespace-nowrap text-sm ${statusClass}">${row.carga_status || ' '}</td>
            `;
            
            // Célula: Canal (com classes de cores)
            let canalHtml = '';
            if (row.diduimp_canal) {
                let canalClass = '';
                if (row.diduimp_canal.toLowerCase() === 'verde') {
                    canalClass = 'bg-green-100 text-green-800 canal-verde';
                } else if (row.diduimp_canal.toLowerCase() === 'amarelo') {
                    canalClass = 'bg-yellow-100 text-yellow-800 canal-amarelo';
                } else if (row.diduimp_canal.toLowerCase() === 'vermelho') {
                    canalClass = 'bg-red-100 text-red-800 canal-vermelho';
                }
                canalHtml = `<span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${canalClass}">${row.diduimp_canal}</span>`;
            }
            tableRow.innerHTML += `
                <td class="px-6 py-4 whitespace-nowrap text-sm">${canalHtml}</td>
            `;
            
            // Célula: Chegada
            tableRow.innerHTML += `
                <td class="px-6 py-4 whitespace-nowrap text-sm text-slate-900">${row.data_chegada || ' '}</td>
            `;
            
            // Célula: Observações
            tableRow.innerHTML += `
                <td class="px-6 py-4 whitespace-nowrap text-sm text-slate-900">${row.observacoes || ' '}</td>
            `;
            
            tableBody.appendChild(tableRow);
        }
    } catch (error) {
        console.error('Erro ao atualizar tabela:', error);
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

// Função para atualizar as taxas de câmbio
function updateCurrencyRates(currencies) {
    try {
        if (currencies.USD !== undefined) {
            // Atualiza na versão desktop
            const usdElements = document.querySelectorAll('#usd-rate-card p:first-child');
            if (usdElements && usdElements.length > 0) {
                usdElements[0].textContent = currencies.USD.toFixed(4);
            }
            
            // Atualiza na versão mobile
            const usdMobileElements = document.querySelectorAll('#usd-rate-card-mobile p:first-child');
            if (usdMobileElements && usdMobileElements.length > 0) {
                usdMobileElements[0].textContent = currencies.USD.toFixed(4);
            }
        }
        
        if (currencies.EUR !== undefined) {
            // Atualiza na versão desktop
            const eurElements = document.querySelectorAll('#eur-rate-card p:first-child');
            if (eurElements && eurElements.length > 0) {
                eurElements[0].textContent = currencies.EUR.toFixed(4);
            }
            
            // Atualiza na versão mobile
            const eurMobileElements = document.querySelectorAll('#eur-rate-card-mobile p:first-child');
            if (eurMobileElements && eurMobileElements.length > 0) {
                eurMobileElements[0].textContent = currencies.EUR.toFixed(4);
            }
        }
        
        console.log('Taxas de câmbio atualizadas');
    } catch (error) {
        console.error('Erro ao atualizar taxas de câmbio:', error);
    }
}

// Elementos globais para contagem regressiva
window.countdownElement = null;
window.countdown = 60;

// Função de contagem regressiva - definida no escopo global para poder ser acessada de qualquer lugar
function updateCountdown() {
    if (!window.countdownElement) {
        window.countdownElement = document.getElementById('countdown');
        if (!window.countdownElement) return; // Se ainda não encontrou o elemento, sai da função
    }
    
    window.countdown--;
    window.countdownElement.textContent = window.countdown;
    
    if (window.countdown <= 0) {
        // Verifica primeiro se a sessão está ativa
        fetch('/paginas/check-session', {
            method: 'GET',
            headers: {
                'Cache-Control': 'no-cache',
                'Content-Type': 'application/json'
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Sessão inválida');
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success') {
                console.log("Sessão verificada, iniciando atualização da OnePage...");
                refreshOnepage();
            } else {
                // Se a sessão não for válida, recarregar apenas os componentes em vez da página inteira
                window.countdown = 60; // Reiniciar contador
                console.warn("Sessão inválida ou expirada, atualizando apenas o menu.");
                
                // Tentar recarregar o menu sem refresh total
                reloadSidebarMenu();
            }
        })
        .catch(() => {
            // Em caso de erro, apenas reiniciar o contador e notificar o usuário
            window.countdown = 60;
            console.warn("Erro ao verificar sessão. Reiniciando contador.");
            
            // Mostrar notificação para o usuário
            const notification = document.createElement('div');
            notification.className = 'bg-yellow-100 border-l-4 border-yellow-500 text-yellow-700 p-4 mb-4 animate-fadeIn';
            notification.innerHTML = '<p>Houve um problema com a atualização automática. Os dados podem estar desatualizados.</p>';
            
            // Find main content container
            const onepageContainer = document.querySelector('main') || document.querySelector('.container') || document.body;
            if (onepageContainer) {
                onepageContainer.prepend(notification);
                
                // Remover notificação após 5 segundos
                setTimeout(() => {
                    notification.style.opacity = '0';
                    notification.style.transition = 'opacity 0.5s ease';
                    setTimeout(() => notification.remove(), 500);
                }, 5000);
            }
        });
    }
}

// Função auxiliar para recarregar o menu lateral de forma mais robusta
function reloadSidebarMenu() {
    // Primeira tentativa - se loadSidebarMenu estiver disponível no escopo global
    if (typeof loadSidebarMenu === 'function') {
        console.log("Chamando função loadSidebarMenu global...");
        loadSidebarMenu();
        return;
    }
    
    // Segunda tentativa - recarregar o menu via fetch
    console.log("Recarregando menu via fetch...");
    const sidebarNav = document.getElementById('sidebar-nav');
    
    if (sidebarNav) {
        fetch('/paginas/menu', {
            method: 'GET',
            headers: {
                'Cache-Control': 'no-cache',
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success' && data.menu) {
                // Implementação simplificada do carregamento do menu
                sidebarNav.innerHTML = '';
                
                // Adicionar as páginas ao menu
                data.menu.forEach(page => {
                    const link = document.createElement('a');
                    link.href = page.flg_ativo ? page.url_rota : 'javascript:void(0)';
                    link.className = `sidebar-item ${page.flg_ativo ? '' : 'opacity-60 cursor-not-allowed'}`;
                    link.innerHTML = `
                        <svg class="sidebar-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            ${page.icone}
                        </svg>
                        <span>${page.nome_pagina}${page.flg_ativo ? '' : ' (' + page.mensagem_manutencao + ')'}</span>
                    `;
                    sidebarNav.appendChild(link);
                });
            }
        })
        .catch(error => console.error('Erro ao recarregar menu:', error));
    }
}

// Inicialização quando o DOM estiver carregado
document.addEventListener('DOMContentLoaded', function() {
    // Inicializar elemento de contagem e configurações
    window.countdownElement = document.getElementById('countdown');
    window.countdown = 60;
    
    // Iniciar contador
    setInterval(updateCountdown, 1000);
});
