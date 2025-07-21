/**
 * Test Dashboard Executivo - Simple Version
 * This file contains simplified chart functions for debugging
 */

// Test if Chart.js is available
function testChartJs() {
    console.log('=== TESTE CHART.JS ===');
    console.log('Chart disponível:', typeof Chart !== 'undefined');
    console.log('ChartDataLabels disponível:', typeof ChartDataLabels !== 'undefined');
    
    if (typeof Chart !== 'undefined') {
        console.log('Versão Chart.js:', Chart.version || 'Desconhecida');
        
        // Try to register plugin
        if (typeof ChartDataLabels !== 'undefined') {
            try {
                Chart.register(ChartDataLabels);
                console.log('Plugin ChartDataLabels registrado com sucesso');
            } catch (error) {
                console.error('Erro ao registrar plugin:', error);
            }
        }
    }
}

// Simple chart creation function for testing
function createSimpleChart() {
    const ctx = document.getElementById('monthly-chart');
    if (!ctx) {
        console.error('Canvas monthly-chart não encontrado');
        return;
    }
    
    if (typeof Chart === 'undefined') {
        console.error('Chart.js não está disponível');
        return;
    }
    
    try {
        const chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['Jan', 'Fev', 'Mar', 'Abr', 'Mai'],
                datasets: [{
                    label: 'Teste',
                    data: [10, 20, 15, 25, 18],
                    borderColor: '#007bff',
                    backgroundColor: 'rgba(0, 123, 255, 0.1)'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        });
        
        console.log('Gráfico simples criado com sucesso:', chart);
        return chart;
    } catch (error) {
        console.error('Erro ao criar gráfico simples:', error);
    }
}

// Run tests when page loads
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(() => {
        testChartJs();
        createSimpleChart();
    }, 2000);
});

console.log('Arquivo de teste carregado');
