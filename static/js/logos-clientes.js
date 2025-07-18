// Logos Clientes Management
let clientes = [];
let editingCnpj = null;

document.addEventListener('DOMContentLoaded', function() {
    loadClientes();
    loadCnpjOptions();
    setupEventListeners();
});

function setupEventListeners() {
    // Botão adicionar
    document.getElementById('btn-adicionar').addEventListener('click', function() {
        openModal();
    });
    
    // Botão cancelar modal
    document.getElementById('btn-cancelar').addEventListener('click', function() {
        closeModal();
    });
    
    // Fechar modal clicando no fundo
    document.getElementById('modal-cliente').addEventListener('click', function(e) {
        if (e.target === this) {
            closeModal();
        }
    });
    
    // Submit do formulário
    document.getElementById('form-cliente').addEventListener('submit', function(e) {
        e.preventDefault();
        saveCliente();
    });
    
    // Upload de arquivo
    document.getElementById('logo_file').addEventListener('change', function(e) {
        if (e.target.files.length > 0) {
            uploadLogo(e.target.files[0]);
        }
    });
    
    // Preview da URL
    document.getElementById('logo_url').addEventListener('input', function(e) {
        const url = e.target.value.trim();
        if (url) {
            showPreview(url);
        } else {
            hidePreview();
        }
    });
    
    // Dropdown de CNPJ
    document.getElementById('cnpj-select').addEventListener('change', function(e) {
        const selectedOption = e.target.selectedOptions[0];
        if (selectedOption.value) {
            document.getElementById('cnpj').value = selectedOption.value;
            document.getElementById('razao_social').value = selectedOption.dataset.razaoSocial || '';
        }
    });
    
    // Máscara de CNPJ
    document.getElementById('cnpj').addEventListener('input', function(e) {
        let value = e.target.value.replace(/\D/g, '');
        value = value.replace(/^(\d{2})(\d)/, '$1.$2');
        value = value.replace(/^(\d{2})\.(\d{3})(\d)/, '$1.$2.$3');
        value = value.replace(/\.(\d{3})(\d)/, '.$1/$2');
        value = value.replace(/(\d{4})(\d)/, '$1-$2');
        e.target.value = value;
    });
}

function loadCnpjOptions() {
    fetch('/config/api/cnpj-options')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const select = document.getElementById('cnpj-select');
                select.innerHTML = '<option value="">Selecionar CNPJ dos importadores cadastrados</option>';
                
                data.data.forEach(item => {
                    const option = document.createElement('option');
                    option.value = item.cnpj;
                    option.textContent = `${item.cnpj} - ${item.razao_social}`;
                    option.dataset.razaoSocial = item.razao_social;
                    select.appendChild(option);
                });
            }
        })
        .catch(error => {
            console.error('Erro ao carregar opções de CNPJ:', error);
        });
}

async function loadClientes() {
    try {
        const response = await fetch('/config/api/logos-clientes');
        const result = await response.json();
        
        if (result.success) {
            clientes = result.data;
            renderClientes();
        } else {
            console.error('Erro ao carregar clientes:', result.error);
            showError('Erro ao carregar clientes: ' + result.error);
        }
    } catch (error) {
        console.error('Erro na requisição:', error);
        showError('Erro ao conectar com o servidor');
    }
}

function renderClientes() {
    const tbody = document.getElementById('clientes-tbody');
    
    if (clientes.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="4" class="px-6 py-4 text-center text-gray-500">
                    Nenhum cliente cadastrado
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = clientes.map(cliente => `
        <tr>
            <td class="px-6 py-4 whitespace-nowrap">
                ${cliente.logo_url ? 
                    `<img src="${cliente.logo_url}" alt="Logo" class="w-12 h-12 object-contain rounded border" onerror="this.src='data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDgiIGhlaWdodD0iNDgiIHZpZXdCb3g9IjAgMCA0OCA0OCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHJlY3Qgd2lkdGg9IjQ4IiBoZWlnaHQ9IjQ4IiBmaWxsPSIjRjNGNEY2Ii8+CjxwYXRoIGQ9Ik0yNCAzNkMzMC42Mjc0IDM2IDM2IDMwLjYyNzQgMzYgMjRDMzYgMTcuMzcyNiAzMC42Mjc0IDEyIDI0IDEyQzE3LjM3MjYgMTIgMTIgMTcuMzcyNiAxMiAyNEMxMiAzMC42Mjc0IDE3LjM3MjYgMzYgMjQgMzYiIGZpbGw9IiM5Q0EzQUYiLz4KPC9zdmc+Cg==';this.alt='Sem logo';">` :
                    `<div class="w-12 h-12 bg-gray-200 rounded border flex items-center justify-center text-gray-400 text-xs">
                        Sem logo
                    </div>`
                }
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                ${cliente.cnpj}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                ${cliente.razao_social}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                <button onclick="editCliente('${cliente.cnpj}')" 
                        class="text-blue-600 hover:text-blue-900 mr-3">
                    Editar
                </button>
                <button onclick="deleteCliente('${cliente.cnpj}')" 
                        class="text-red-600 hover:text-red-900">
                    Excluir
                </button>
            </td>
        </tr>
    `).join('');
}

function openModal(cliente = null) {
    editingCnpj = cliente ? cliente.cnpj : null;
    
    if (cliente) {
        document.getElementById('modal-title').textContent = 'Editar Cliente';
        document.getElementById('cnpj').value = cliente.cnpj;
        document.getElementById('cnpj').disabled = true;
        document.getElementById('razao_social').value = cliente.razao_social;
        document.getElementById('logo_url').value = cliente.logo_url || '';
        
        if (cliente.logo_url) {
            showPreview(cliente.logo_url);
        }
    } else {
        document.getElementById('modal-title').textContent = 'Adicionar Cliente';
        document.getElementById('form-cliente').reset();
        document.getElementById('cnpj').disabled = false;
        hidePreview();
    }
    
    document.getElementById('modal-cliente').classList.remove('hidden');
}

function closeModal() {
    document.getElementById('modal-cliente').classList.add('hidden');
    document.getElementById('form-cliente').reset();
    hidePreview();
    editingCnpj = null;
}

async function saveCliente() {
    const formData = new FormData(document.getElementById('form-cliente'));
    const data = {
        cnpj: formData.get('cnpj').replace(/\D/g, ''), // Remove formatação
        razao_social: formData.get('razao_social'),
        logo_url: formData.get('logo_url')
    };
    
    if (!data.cnpj || !data.razao_social) {
        showError('CNPJ e Razão Social são obrigatórios');
        return;
    }
    
    try {
        const response = await fetch('/config/api/logos-clientes', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showSuccess(editingCnpj ? 'Cliente atualizado com sucesso!' : 'Cliente adicionado com sucesso!');
            closeModal();
            loadClientes();
        } else {
            showError('Erro ao salvar cliente: ' + result.error);
        }
    } catch (error) {
        console.error('Erro na requisição:', error);
        showError('Erro ao conectar com o servidor');
    }
}

function editCliente(cnpj) {
    const cliente = clientes.find(c => c.cnpj === cnpj);
    if (cliente) {
        openModal(cliente);
    }
}

async function deleteCliente(cnpj) {
    if (!confirm('Tem certeza que deseja excluir este cliente?')) {
        return;
    }
    
    try {
        const response = await fetch(`/config/api/logos-clientes/${cnpj}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.success) {
            showSuccess('Cliente excluído com sucesso!');
            loadClientes();
        } else {
            showError('Erro ao excluir cliente: ' + result.error);
        }
    } catch (error) {
        console.error('Erro na requisição:', error);
        showError('Erro ao conectar com o servidor');
    }
}

async function uploadLogo(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch('/config/api/upload-logo', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            document.getElementById('logo_url').value = result.url;
            showPreview(result.url);
            showSuccess('Logo enviado com sucesso!');
        } else {
            showError('Erro no upload: ' + result.error);
        }
    } catch (error) {
        console.error('Erro no upload:', error);
        showError('Erro ao enviar arquivo');
    }
}

function showPreview(url) {
    const preview = document.getElementById('logo-preview');
    const img = document.getElementById('logo-preview-img');
    
    img.src = url;
    preview.classList.remove('hidden');
}

function hidePreview() {
    document.getElementById('logo-preview').classList.add('hidden');
}

function showSuccess(message) {
    // Implementação simples de notificação
    alert('✅ ' + message);
}

function showError(message) {
    // Implementação simples de notificação
    alert('❌ ' + message);
}
