/**
 * Script para ordenação de tabelas no Portal UniSystem
 * Implementa funcionalidade para ordenar dados em tabelas por diferentes colunas e tipos de dados
 */

document.addEventListener('DOMContentLoaded', function() {
    // Selecionar todos os cabeçalhos de tabela com a classe 'sortable'
    const sortableColumns = document.querySelectorAll('.sortable');
    let currentSort = { column: 'data_embarque', direction: 'desc' }; // Ordenação padrão: data de embarque decrescente
    
    sortableColumns.forEach(th => {
        th.addEventListener('click', function() {
            const columnName = this.getAttribute('data-sort');
            let direction = 'asc';
            
            // Se já estiver ordenando por esta coluna, inverta a direção
            if (currentSort.column === columnName) {
                direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
            }
            
            // Atualizar a ordenação atual
            currentSort = { column: columnName, direction: direction };
            
            // Remover classes de ordenação de todos os cabeçalhos
            sortableColumns.forEach(col => {
                col.classList.remove('asc', 'desc');
            });
            
            // Adicionar classe de ordenação ao cabeçalho atual
            this.classList.add(direction);
            
            // Ordenar os dados da tabela
            sortTable(columnName, direction);
        });
    });
    
    // Função para ordenar a tabela
    function sortTable(column, direction) {
        const table = document.querySelector('.data-table');
        const tbody = table.querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        
        // Mostrar overlay de carregamento
        const loadingOverlay = document.getElementById('loading-overlay');
        if (loadingOverlay) {
            loadingOverlay.classList.remove('hidden');
        }
        
        // Ordenar com um pequeno atraso para permitir que o overlay seja exibido
        setTimeout(() => {
            // Verificar se há linha de mensagem vazia
            const emptyRows = rows.filter(row => row.querySelector('.empty-state'));
            if (emptyRows.length) {
                // Ocultar overlay de carregamento
                if (loadingOverlay) {
                    loadingOverlay.classList.add('hidden');
                }
                return; // Se tiver mensagem vazia, não precisa ordenar
            }
            
            // Ordenar as linhas
            const sortedRows = rows.sort((a, b) => {
                // Obter a célula correspondente à coluna
                const aCell = a.querySelector(`td:nth-child(${getColumnIndex(column)})`);
                const bCell = b.querySelector(`td:nth-child(${getColumnIndex(column)})`);
                
                // Obter os valores de texto
                const aValue = aCell?.textContent.trim() || '';
                const bValue = bCell?.textContent.trim() || '';
                
                // Caso especial para colunas com imagens (como modal de transporte)
                if (column === 'via_transporte_descricao' && (aCell?.classList.contains('img_modal') || bCell?.classList.contains('img_modal'))) {
                    // Tentar obter o alt da imagem, que contém o tipo de transporte
                    const aImg = aCell?.querySelector('img');
                    const bImg = bCell?.querySelector('img');
                    
                    const aAlt = aImg?.getAttribute('alt') || aValue;
                    const bAlt = bImg?.getAttribute('alt') || bValue;
                    
                    return direction === 'asc' ? 
                        aAlt.localeCompare(bAlt) : 
                        bAlt.localeCompare(aAlt);
                }
                
                // Verificar se os valores são datas (no formato DD/MM/YYYY)
                if (isDateFormat(aValue) && isDateFormat(bValue)) {
                    // Converter para objeto Date para comparação
                    const [aDay, aMonth, aYear] = aValue.split('/').map(num => parseInt(num, 10));
                    const [bDay, bMonth, bYear] = bValue.split('/').map(num => parseInt(num, 10));
                    
                    const aDate = new Date(aYear, aMonth - 1, aDay);
                    const bDate = new Date(bYear, bMonth - 1, bDay);
                    
                    // Verificar se as datas são válidas
                    const aValid = !isNaN(aDate.getTime());
                    const bValid = !isNaN(bDate.getTime());
                    
                    // Se alguma data for inválida, tratá-la como menor valor
                    if (!aValid && !bValid) return 0;
                    if (!aValid) return direction === 'asc' ? -1 : 1;
                    if (!bValid) return direction === 'asc' ? 1 : -1;
                    
                    return direction === 'asc' ? aDate - bDate : bDate - aDate;
                }
                
                // Verificar se os valores podem ser números
                const aNum = parseFloat(aValue);
                const bNum = parseFloat(bValue);
                const aIsNum = !isNaN(aNum);
                const bIsNum = !isNaN(bNum);
                
                // Para valores numéricos
                if (aIsNum && bIsNum) {
                    return direction === 'asc' ? aNum - bNum : bNum - aNum;
                }
                
                // Para valores vazios ou nulos
                if (!aValue && !bValue) return 0;
                if (!aValue) return direction === 'asc' ? -1 : 1;
                if (!bValue) return direction === 'asc' ? 1 : -1;
                
                // Para valores de texto (não numéricos)
                return direction === 'asc' ? 
                    aValue.localeCompare(bValue, undefined, {numeric: true, sensitivity: 'base'}) : 
                    bValue.localeCompare(aValue, undefined, {numeric: true, sensitivity: 'base'});
            });
            
            // Limpar e recriar a tabela
            while (tbody.firstChild) {
                tbody.removeChild(tbody.firstChild);
            }
            
            // Adicionar as linhas ordenadas de volta à tabela
            sortedRows.forEach(row => {
                tbody.appendChild(row);
            });
            
            // Ocultar overlay de carregamento
            if (loadingOverlay) {
                loadingOverlay.classList.add('hidden');
            }
        }, 100);
    }
    
    // Função auxiliar para verificar se uma string está no formato de data DD/MM/YYYY
    function isDateFormat(dateStr) {
        if (!dateStr || typeof dateStr !== 'string') return false;
        // Verifica formato DD/MM/YYYY ou com horas DD/MM/YYYY HH:MM
        return /^\d{2}\/\d{2}\/\d{4}(\s\d{2}:\d{2})?$/.test(dateStr);
    }
    
    // Função para obter o índice da coluna com base no nome da coluna
    function getColumnIndex(columnName) {
        // Obtém dinamicamente os índices das colunas baseado nos cabeçalhos
        const headers = document.querySelectorAll('th.sortable');
        for (let i = 0; i < headers.length; i++) {
            if (headers[i].getAttribute('data-sort') === columnName) {
                return i + 1; // +1 porque nth-child é baseado em 1, não em 0
            }
        }
        
        // Mapa fallback caso não consiga determinar dinamicamente
        const columnMap = {
            'numero': 1,
            'data_embarque': 2,
            'via_transporte_descricao': 3,
            'data_registro': 4,
            'ref_unique': 5,
            'carga_status': 6,
            'diduimp_canal': 7,
            'data_chegada': 8,
            'observacoes': 9
        };
        return columnMap[columnName] || 1;
    }
    
    // Inicialmente, ordenar pela data de embarque (decrescente)
    const defaultSortColumn = document.querySelector(`th[data-sort="data_embarque"]`);
    if (defaultSortColumn) {
        defaultSortColumn.classList.add('desc');
        
        // Opcionalmente, iniciar com a tabela já ordenada na carga inicial
        setTimeout(() => {
            sortTable('data_embarque', 'desc');
        }, 200);
    }
});
