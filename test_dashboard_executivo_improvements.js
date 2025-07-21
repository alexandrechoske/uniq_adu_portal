/**
 * Test file - Dashboard Executivo JavaScript Improvements
 * This is a backup and test file for the dashboard improvements
 */

// Improvements for Dashboard Executivo:

// 1. Monthly Evolution Chart - with smooth lines, data labels, and dual axis configuration
function createImprovedMonthlyChart(data) {
    const ctx = document.getElementById('monthly-chart');
    if (!ctx) return;
    
    // Destroy existing chart
    if (dashboardCharts.monthly) {
        dashboardCharts.monthly.destroy();
    }
    
    dashboardCharts.monthly = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels || [],
            datasets: [
                {
                    label: 'Quantidade de Processos',
                    data: data.datasets[0]?.data || [],
                    type: 'line',
                    borderColor: '#007bff',
                    backgroundColor: 'rgba(0, 123, 255, 0.1)',
                    yAxisID: 'y1',
                    tension: 0.4, // Smooth curves
                    pointBackgroundColor: '#007bff',
                    pointBorderColor: '#007bff',
                    pointRadius: 5,
                    pointHoverRadius: 7,
                    datalabels: {
                        backgroundColor: '#007bff',
                        borderColor: '#007bff',
                        borderRadius: 4,
                        borderWidth: 2,
                        color: 'white',
                        font: {
                            weight: 'bold',
                            size: 10
                        },
                        padding: {
                            top: 2,
                            bottom: 2,
                            left: 4,
                            right: 4
                        },
                        align: 'top',
                        anchor: 'end',
                        offset: 5
                    }
                },
                {
                    label: 'Custo Total (R$)',
                    data: data.datasets[1]?.data || [],
                    type: 'line', // Changed from 'bar' to 'line'
                    borderColor: '#28a745',
                    backgroundColor: 'rgba(40, 167, 69, 0.1)',
                    yAxisID: 'y',
                    tension: 0.4, // Smooth curves
                    pointBackgroundColor: '#28a745',
                    pointBorderColor: '#28a745',
                    pointRadius: 5,
                    pointHoverRadius: 7,
                    datalabels: {
                        backgroundColor: '#28a745',
                        borderColor: '#28a745',
                        borderRadius: 4,
                        borderWidth: 2,
                        color: 'white',
                        font: {
                            weight: 'bold',
                            size: 10
                        },
                        padding: {
                            top: 2,
                            bottom: 2,
                            left: 4,
                            right: 4
                        },
                        align: 'bottom',
                        anchor: 'start',
                        offset: -5
                    }
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Evolução Mensal de Processos e Custos'
                },
                legend: {
                    position: 'top'
                },
                datalabels: {
                    display: true
                }
            },
            scales: {
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: {
                        display: true,
                        text: 'Custo Total (R$)'
                    }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: {
                        display: true,
                        text: 'Quantidade de Processos'
                    },
                    grid: {
                        drawOnChartArea: false,
                    },
                }
            },
            interaction: {
                mode: 'index',
                intersect: false,
            }
        }
    });
}

// 2. Modal Chart with separate Y-axes and data labels
function createImprovedGroupedModalChart(data) {
    const ctx = document.getElementById('grouped-modal-chart');
    if (!ctx) return;
    
    // Destroy existing chart
    if (dashboardCharts.groupedModal) {
        dashboardCharts.groupedModal.destroy();
    }
    
    dashboardCharts.groupedModal = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.labels || [],
            datasets: data.datasets || []
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Processos e Custos por Modal de Transporte'
                },
                datalabels: {
                    display: true,
                    backgroundColor: function(context) {
                        return context.dataset.backgroundColor;
                    },
                    borderColor: function(context) {
                        return context.dataset.borderColor;
                    },
                    borderRadius: 4,
                    borderWidth: 1,
                    color: 'white',
                    font: {
                        weight: 'bold',
                        size: 10
                    },
                    padding: {
                        top: 2,
                        bottom: 2,
                        left: 4,
                        right: 4
                    },
                    align: 'end',
                    anchor: 'end',
                    offset: 2,
                    formatter: function(value, context) {
                        if (context.datasetIndex === 0) {
                            return value; // Just the number for processes
                        } else {
                            return 'R$ ' + value.toLocaleString('pt-BR'); // Formatted currency
                        }
                    }
                }
            },
            scales: {
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Custo Total (R$)'
                    }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Quantidade de Processos'
                    },
                    grid: {
                        drawOnChartArea: false,
                    }
                }
            }
        }
    });
}

// 3. URF Chart with data labels
function createImprovedUrfChart(data) {
    const ctx = document.getElementById('urf-chart');
    if (!ctx) return;
    
    // Destroy existing chart
    if (dashboardCharts.urf) {
        dashboardCharts.urf.destroy();
    }
    
    dashboardCharts.urf = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.labels || [],
            datasets: [{
                label: 'Quantidade de Processos',
                data: data.data || [],
                backgroundColor: '#36A2EB',
                borderColor: '#36A2EB',
                datalabels: {
                    backgroundColor: '#36A2EB',
                    borderColor: '#36A2EB',
                    borderRadius: 4,
                    borderWidth: 1,
                    color: 'white',
                    font: {
                        weight: 'bold',
                        size: 11
                    },
                    padding: {
                        top: 2,
                        bottom: 2,
                        left: 6,
                        right: 6
                    },
                    align: 'end',
                    anchor: 'end',
                    offset: 4
                }
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                datalabels: {
                    display: true
                }
            },
            scales: {
                x: {
                    beginAtZero: true
                }
            }
        }
    });
}

// 4. Material Chart with data labels
function createImprovedMaterialChart(data) {
    const ctx = document.getElementById('material-chart');
    if (!ctx) return;
    
    // Destroy existing chart
    if (dashboardCharts.material) {
        dashboardCharts.material.destroy();
    }
    
    dashboardCharts.material = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.labels || [],
            datasets: [{
                label: 'Quantidade de Processos',
                data: data.data || [],
                backgroundColor: '#4BC0C0',
                borderColor: '#4BC0C0',
                datalabels: {
                    backgroundColor: '#4BC0C0',
                    borderColor: '#4BC0C0',
                    borderRadius: 4,
                    borderWidth: 1,
                    color: 'white',
                    font: {
                        weight: 'bold',
                        size: 11
                    },
                    padding: {
                        top: 2,
                        bottom: 2,
                        left: 6,
                        right: 6
                    },
                    align: 'end',
                    anchor: 'end',
                    offset: 4
                }
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                datalabels: {
                    display: true
                }
            },
            scales: {
                x: {
                    beginAtZero: true
                }
            }
        }
    });
}
