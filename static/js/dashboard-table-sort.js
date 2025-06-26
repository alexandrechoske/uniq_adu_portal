/**
 * Script para ordenação de tabelas específicas no Dashboard
 * Implementa funcionalidade para ordenar dados em tabelas por diferentes colunas e tipos de dados
 * Gerencia as tabelas de Operações de Importação e Análise por Material separadamente
 */

document.addEventListener('DOMContentLoaded', function() {
    // Configurar ordenação para cada tabela específica
    setupTableSorting('importacoes-table');
    setupTableSorting('material-analysis-table');
    
    function setupTableSorting(tableId) {
        const table = document.getElementById(tableId);
        if (!table) return;
        
        const sortableColumns = table.querySelectorAll('.sortable');
        let currentSort = { column: null, direction: 'asc' };
        
        // Ordenação padrão específica por tabela
        if (tableId === 'importacoes-table') {
            currentSort = { column: 'data_embarque', direction: 'desc' };
        } else if (tableId === 'material-analysis-table') {
            currentSort = { column: 'valor_total', direction: 'desc' };
        }
        
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
                
                // Remover classes de ordenação de todos os cabeçalhos desta tabela
                sortableColumns.forEach(col => {
                    col.classList.remove('asc', 'desc');
                });
                
                // Adicionar classe de ordenação ao cabeçalho atual
                this.classList.add(direction);
                
                // Ordenar os dados da tabela específica
                sortTable(table, columnName, direction);
            });
        });
        
        // Aplicar ordenação padrão
        if (currentSort.column) {
            const defaultColumn = table.querySelector(`th[data-sort="${currentSort.column}"]`);
            if (defaultColumn) {
                defaultColumn.classList.add(currentSort.direction);
                setTimeout(() => {
                    sortTable(table, currentSort.column, currentSort.direction);
                }, 100);
            }
        }
    }
    
    // Função para ordenar uma tabela específica
    function sortTable(table, column, direction) {
        const tbody = table.querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        
        // Verificar se há linha de mensagem vazia
        const emptyRows = rows.filter(row => row.querySelector('.empty-state'));
        if (emptyRows.length) {
            return; // Se tiver mensagem vazia, não precisa ordenar
        }
        
        // Ordenar as linhas
        const sortedRows = rows.sort((a, b) => {
            // Obter a célula correspondente à coluna
            const aCell = a.querySelector(`td:nth-child(${getColumnIndex(table, column)})`);
            const bCell = b.querySelector(`td:nth-child(${getColumnIndex(table, column)})`);
            
            // Primeiro, tentar obter o valor do atributo data-sort-value (para valores numéricos formatados)
            let aValue = aCell?.getAttribute('data-sort-value');
            let bValue = bCell?.getAttribute('data-sort-value');
            
            // Se não tiver data-sort-value, usar o texto da célula
            if (aValue === null) aValue = aCell?.textContent.trim() || '';
            if (bValue === null) bValue = bCell?.textContent.trim() || '';
            
            // Caso especial para colunas com elementos complexos (como modal de transporte)
            if (column === 'via_transporte_descricao') {
                // Extrair o texto do span se existir
                const aSpan = aCell?.querySelector('span');
                const bSpan = bCell?.querySelector('span');
                
                if (aSpan) aValue = aSpan.textContent.trim();
                if (bSpan) bValue = bSpan.textContent.trim();
            }
            
            // Verificar se os valores são datas (no formato DD/MM/YYYY)
            if (isDateFormat(aValue) && isDateFormat(bValue)) {
                const aDate = parseDate(aValue);
                const bDate = parseDate(bValue);
                
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
            const aNum = parseFloat(aValue.toString().replace(/[^\d.-]/g, ''));
            const bNum = parseFloat(bValue.toString().replace(/[^\d.-]/g, ''));
            const aIsNum = !isNaN(aNum) && aValue.toString().match(/[\d,.-]/);
            const bIsNum = !isNaN(bNum) && bValue.toString().match(/[\d,.-]/);
            
            // Para valores numéricos
            if (aIsNum && bIsNum) {
                return direction === 'asc' ? aNum - bNum : bNum - aNum;
            }
            
            // Para valores vazios ou nulos
            if (!aValue && !bValue) return 0;
            if (!aValue || aValue === '-') return direction === 'asc' ? -1 : 1;
            if (!bValue || bValue === '-') return direction === 'asc' ? 1 : -1;
            
            // Para valores de texto (não numéricos)
            const aStr = aValue.toString().toLowerCase();
            const bStr = bValue.toString().toLowerCase();
            
            return direction === 'asc' ? 
                aStr.localeCompare(bStr, undefined, {numeric: true, sensitivity: 'base'}) : 
                bStr.localeCompare(aStr, undefined, {numeric: true, sensitivity: 'base'});
        });
        
        // Limpar e recriar a tabela
        while (tbody.firstChild) {
            tbody.removeChild(tbody.firstChild);
        }
        
        // Adicionar as linhas ordenadas de volta à tabela
        sortedRows.forEach(row => {
            tbody.appendChild(row);
        });
    }
    
    // Função auxiliar para verificar se uma string está no formato de data DD/MM/YYYY
    function isDateFormat(dateStr) {
        if (!dateStr || typeof dateStr !== 'string') return false;
        // Verifica formato DD/MM/YYYY ou com horas DD/MM/YYYY HH:MM
        return /^\d{1,2}\/\d{1,2}\/\d{4}(\s\d{1,2}:\d{2})?$/.test(dateStr);
    }
    
    // Função para converter string de data em objeto Date
    function parseDate(dateStr) {
        if (!dateStr || !isDateFormat(dateStr)) return new Date(NaN);
        
        const [datePart] = dateStr.split(' '); // Remover parte da hora se existir
        const [day, month, year] = datePart.split('/').map(num => parseInt(num, 10));
        
        return new Date(year, month - 1, day);
    }
    
    // Função para obter o índice da coluna com base no nome da coluna e tabela específica
    function getColumnIndex(table, columnName) {
        const headers = table.querySelectorAll('th.sortable');
        for (let i = 0; i < headers.length; i++) {
            if (headers[i].getAttribute('data-sort') === columnName) {
                return i + 1; // +1 porque nth-child é baseado em 1, não em 0
            }
        }
        return 1; // Fallback
    }
});
