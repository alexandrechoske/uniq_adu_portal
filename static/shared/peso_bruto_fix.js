/**
 * FIX: peso_bruto formatting issue
 * 
 * The problem: Database stores peso_bruto with wrong scale
 * Example: User enters 17905 but DB stores 1790512
 * 
 * Solution: Detect and fix values that seem to be scaled incorrectly
 */

/**
 * Normalize peso_bruto value if it seems to be incorrectly scaled
 * @param {number} peso - The peso_bruto value from database
 * @returns {number} - Normalized peso value
 */
function normalizePesoBruto(peso) {
    if (!peso || isNaN(peso)) return 0;
    
    const pesoNum = Number(peso);
    
    // If peso is > 100,000 kg (100 tons), it's probably scaled wrong
    // Divide by 100 to get the correct value
    // Example: 1790512 -> 17905.12 kg
    if (pesoNum > 100000) {
        console.log(`[PESO_FIX] Detected wrong scale: ${pesoNum} -> ${pesoNum / 100}`);
        return pesoNum / 100;
    }
    
    return pesoNum;
}

/**
 * Format peso_bruto for display with normalization
 * @param {number} peso - The peso_bruto value from database
 * @returns {string} - Formatted peso with "Kg" suffix
 */
function formatPesoBruto(peso) {
    const normalized = normalizePesoBruto(peso);
    if (!normalized) return '-';
    
    return formatNumber(normalized) + ' Kg';
}

console.log('[PESO_FIX] Peso bruto fix utilities loaded');
