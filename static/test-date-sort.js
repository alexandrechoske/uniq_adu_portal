// Teste direto da ordenação de datas no Enhanced Table
console.log('=== TESTE DE ORDENAÇÃO DE DATAS ===');

// Dados de teste simulando os dados reais dos dashboards
const testOperations = [
    {
        ref_unique: 'OP001',
        importador: 'Empresa A',
        data_chegada: '31/05/2025',
        status: 'Liberado'
    },
    {
        ref_unique: 'OP002',
        importador: 'Empresa B',
        data_chegada: '11/07/2025',
        status: 'Em análise'
    },
    {
        ref_unique: 'OP003',
        importador: 'Empresa C',
        data_chegada: '05/06/2025',
        status: 'Retido'
    },
    {
        ref_unique: 'OP004',
        importador: 'Empresa D',
        data_chegada: '22/12/2024',
        status: 'Liberado'
    },
    {
        ref_unique: 'OP005',
        importador: 'Empresa E',
        data_chegada: '01/01/2025',
        status: 'Em análise'
    },
    {
        ref_unique: 'OP006',
        importador: 'Empresa F',
        data_chegada: '15/03/2025',
        status: 'Liberado'
    }
];

console.log('Dados originais:', testOperations);

// Simular a função parseDate do enhanced-table.js
function parseDate(dateStr) {
    if (!dateStr) return null;
    
    // Clean the string
    const cleanStr = String(dateStr).trim();
    
    // Try Brazilian format DD/MM/YYYY (with optional time)
    const brazilianMatch = cleanStr.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})(\s.*)?$/);
    if (brazilianMatch) {
        const [, day, month, year] = brazilianMatch;
        const dayNum = parseInt(day, 10);
        const monthNum = parseInt(month, 10);
        const yearNum = parseInt(year, 10);
        
        // Basic validation
        if (dayNum >= 1 && dayNum <= 31 && monthNum >= 1 && monthNum <= 12 && yearNum >= 1900) {
            const date = new Date(yearNum, monthNum - 1, dayNum);
            // Double check the date is valid (handles things like Feb 30)
            if (date.getFullYear() === yearNum && 
                date.getMonth() === monthNum - 1 && 
                date.getDate() === dayNum) {
                return date;
            }
        }
    }

    // Try ISO format as fallback
    const date = new Date(cleanStr);
    return isNaN(date.getTime()) ? null : date;
}

// Simular a função isBrazilianDate
function isBrazilianDate(value) {
    if (!value || typeof value !== 'string') return false;
    // Check for DD/MM/YYYY format (with or without time)
    return /^\d{1,2}\/\d{1,2}\/\d{4}(\s\d{1,2}:\d{1,2}(:\d{1,2})?)?$/.test(value.trim());
}

// Testar parsing das datas
console.log('\n=== TESTE DE PARSING ===');
testOperations.forEach(op => {
    const parsed = parseDate(op.data_chegada);
    const isBrazilian = isBrazilianDate(op.data_chegada);
    console.log(`${op.data_chegada} -> Parsed: ${parsed ? parsed.toISOString().split('T')[0] : 'null'}, IsBrazilian: ${isBrazilian}`);
});

// Simular a ordenação (decrescente)
console.log('\n=== TESTE DE ORDENAÇÃO (DESC) ===');
const sortedData = [...testOperations].sort((a, b) => {
    const columnKey = 'data_chegada';
    let aVal = a[columnKey];
    let bVal = b[columnKey];

    // Handle null/undefined values
    if (aVal === null || aVal === undefined) aVal = '';
    if (bVal === null || bVal === undefined) bVal = '';

    // Special handling for dates - check if values look like Brazilian dates first
    if (isBrazilianDate(aVal) || isBrazilianDate(bVal)) {
        const aDate = parseDate(aVal);
        const bDate = parseDate(bVal);

        // If both are valid dates, compare them
        if (aDate && bDate) {
            return bDate - aDate; // DESC order
        }
        
        // If only one is a valid date, valid date comes first (or last depending on direction)
        if (aDate && !bDate) return 1; // DESC: invalid goes to end
        if (!aDate && bDate) return -1; // DESC: invalid goes to end
    }

    // Default string comparison
    const aStr = String(aVal).toLowerCase();
    const bStr = String(bVal).toLowerCase();
    return bStr.localeCompare(aStr, 'pt-BR');
});

console.log('Dados ordenados (desc):');
sortedData.forEach((op, index) => {
    const parsed = parseDate(op.data_chegada);
    console.log(`${index + 1}. ${op.ref_unique}: ${op.data_chegada} (${parsed ? parsed.toLocaleDateString('pt-BR') : 'inválida'})`);
});

// Verificar se a ordenação está correta
console.log('\n=== VERIFICAÇÃO ===');
const expectedOrder = [
    '11/07/2025', // Julho 2025 - mais recente
    '05/06/2025', // Junho 2025
    '31/05/2025', // Maio 2025
    '15/03/2025', // Março 2025
    '01/01/2025', // Janeiro 2025
    '22/12/2024'  // Dezembro 2024 - mais antigo
];

const actualOrder = sortedData.map(op => op.data_chegada);
const isCorrect = JSON.stringify(expectedOrder) === JSON.stringify(actualOrder);

console.log('Ordem esperada:', expectedOrder);
console.log('Ordem atual:', actualOrder);
console.log('Ordenação correta:', isCorrect ? '✅ SIM' : '❌ NÃO');

if (!isCorrect) {
    console.log('\n=== ANÁLISE DO PROBLEMA ===');
    expectedOrder.forEach((expected, index) => {
        const actual = actualOrder[index];
        if (expected !== actual) {
            console.log(`Posição ${index + 1}: Esperado "${expected}", Encontrado "${actual}"`);
        }
    });
}
