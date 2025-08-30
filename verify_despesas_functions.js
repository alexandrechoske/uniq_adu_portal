// Simple test to verify that the JavaScript functions are properly defined
console.log('Verifying Despesas JavaScript functions...');

// Check if DespesasController class exists
if (typeof DespesasController !== 'undefined') {
    console.log('✓ DespesasController class exists');
    
    // Check if the class has the expected methods
    const controller = new DespesasController();
    
    // List of expected methods
    const expectedMethods = [
        'loadFaturamentoData',
        'updateGraficoProporcao',
        'updateGraficoMetaGauge',
        'combineFaturamentoWithMetas',
        'updateTabelaFaturamentoMetas'
    ];
    
    expectedMethods.forEach(method => {
        if (typeof controller[method] === 'function') {
            console.log(`✓ Method ${method} exists`);
        } else {
            console.log(`✗ Method ${method} does not exist`);
        }
    });
} else {
    console.log('✗ DespesasController class does not exist');
}

// Check if Chart.js is loaded
if (typeof Chart !== 'undefined') {
    console.log('✓ Chart.js is loaded');
} else {
    console.log('✗ Chart.js is not loaded');
}

// Check if ChartDataLabels is registered
if (typeof ChartDataLabels !== 'undefined') {
    console.log('✓ ChartDataLabels plugin is loaded');
} else {
    console.log('⚠ ChartDataLabels plugin is not loaded (this is OK if it was not included)');
}

console.log('Verification complete.');