/**
 * JavaScript para Categorização de Clientes
 * Interface tipo planilha para padronização de nomes de clientes
 */

// Funções globais para compatibilidade
function buscarClientes() {
    if (window.clienteManager) {
        window.clienteManager.buscarClientes();
    }
}

function salvarCliente(index) {
    if (window.clienteManager) {
        window.clienteManager.salvarCliente(index);
    }
}

function salvarSelecionados() {
    if (window.clienteManager) {
        window.clienteManager.salvarSelecionados();
    }
}

function aplicarPadronizacaoLote() {
    if (window.clienteManager) {
        window.clienteManager.aplicarPadronizacaoLote();
    }
}

function confirmarPadronizacaoLote() {
    if (window.clienteManager) {
        window.clienteManager.confirmarPadronizacaoLote();
    }
}

function popularTabelas() {
    if (window.clienteManager) {
        window.clienteManager.popularTabelas();
    }
}

// Classe ClienteCategorizacaoManager (mantida para compatibilidade)
class ClienteCategorizacaoManager {
    constructor() {
        this.clientes = [];
        this.clientesSelecionados = [];
        this.currentFilters = {
            busca: '',
            status: 'todos'
        };
    }

    init() {
        // Método mantido para compatibilidade
        console.log('ClienteCategorizacaoManager inicializado');
    }

    buscarClientes() {
        // Implementação movida para o template HTML
        console.log('buscarClientes chamado');
    }

    salvarCliente(index) {
        // Implementação movida para o template HTML
        console.log('salvarCliente chamado:', index);
    }

    salvarSelecionados() {
        // Implementação movida para o template HTML
        console.log('salvarSelecionados chamado');
    }

    aplicarPadronizacaoLote() {
        // Implementação movida para o template HTML
        console.log('aplicarPadronizacaoLote chamado');
    }

    confirmarPadronizacaoLote() {
        // Implementação movida para o template HTML
        console.log('confirmarPadronizacaoLote chamado');
    }

    popularTabelas() {
        // Implementação movida para o template HTML
        console.log('popularTabelas chamado');
    }

    mostrarToast(mensagem, classes = '') {
        // Implementação movida para o template HTML
        console.log('Toast:', mensagem, classes);
    }
}

// Inicializar quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', function() {
    // Criar instância do manager para compatibilidade
    window.clienteManager = new ClienteCategorizacaoManager();
    window.clienteManager.init();
});
