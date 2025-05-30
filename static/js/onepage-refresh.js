// Função para mostrar o indicador de carregamento
function showLoading() {
    document.getElementById('loading-overlay').classList.remove('hidden');
}

// Função para esconder o indicador de carregamento
function hideLoading() {
    document.getElementById('loading-overlay').classList.add('hidden');
}

// Função para atualizar a OnePage
function refreshDashboard() {
    showLoading();
    
    // Resetar contador
    countdown = 60;
    countdownElement.textContent = countdown;
    
    // Chamar a API de atualização para buscar os dados mais recentes do Supabase
    fetch('/onepage/update-data', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        console.log('Resposta da atualização:', data);
        
        // Agora, obter os dados atualizados
        return fetch('/onepage/page-data');
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            // Atualizar KPIs
            updateKPIs(data.kpis);
            
            // Atualizar tabela
            updateTable(data.table_data);
            
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
        
        // Método de fallback em caso de falha: recarregar a página
        if (confirm("Ocorreu um erro ao atualizar. Deseja recarregar a página?")) {
            window.location.reload();
        }
    });
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

// Inicialização quando o DOM estiver carregado
document.addEventListener('DOMContentLoaded', function() {
    // Elementos globais
    window.countdownElement = document.getElementById('countdown');
    window.countdown = 60;
    
    // Função de contagem regressiva
    function updateCountdown() {
        countdown--;
        countdownElement.textContent = countdown;
        
        if (countdown <= 0) {
            refreshDashboard();
        }
    }
    
    // Iniciar contador
    setInterval(updateCountdown, 1000);
});
