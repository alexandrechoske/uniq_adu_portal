// Ícones Materiais Management
let materiais = [];
let editingId = null;

document.addEventListener('DOMContentLoaded', function() {
    loadMateriais();
    loadMercadoriasOptions();
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
    document.getElementById('modal-material').addEventListener('click', function(e) {
        if (e.target === this) {
            closeModal();
        }
    });
    
    // Submit do formulário
    document.getElementById('form-material').addEventListener('submit', function(e) {
        e.preventDefault();
        saveMaterial();
    });
    
    // Upload de arquivo
    document.getElementById('icone_file').addEventListener('change', function(e) {
        if (e.target.files.length > 0) {
            uploadIcone(e.target.files[0]);
        }
    });
    
    // Preview da URL
    document.getElementById('icone_url').addEventListener('input', function(e) {
        const url = e.target.value.trim();
        if (url) {
            showPreview(url);
        } else {
            hidePreview();
        }
    });
    
    // Dropdown de mercadorias
    document.getElementById('mercadoria-select').addEventListener('change', function(e) {
        if (e.target.value) {
            // Normalizar o nome da mercadoria (minúsculas, sem acentos, etc.)
            // Aplicar a mesma normalização que o backend
            const nomeNormalizado = e.target.value.toLowerCase()
                .normalize('NFD')
                .replace(/[\u0300-\u036f]/g, '')  // Remove acentos
                .replace(/[^a-z0-9\s]/g, '')      // Remove caracteres especiais
                .replace(/\s+/g, ' ')             // Remove múltiplos espaços
                .trim();
            document.getElementById('nome_normalizado').value = nomeNormalizado;
        }
    });
    
    // Normalizar nome do material em tempo real
    document.getElementById('nome_normalizado').addEventListener('input', function(e) {
        // Aplicar a mesma normalização que o backend
        let value = e.target.value.toLowerCase();
        value = value.normalize('NFD')
                    .replace(/[\u0300-\u036f]/g, '')  // Remove acentos
                    .replace(/[^a-z0-9\s]/g, '')      // Remove caracteres especiais
                    .replace(/\s+/g, ' ')             // Remove múltiplos espaços
                    .trim();
        e.target.value = value;
    });
}

function loadMercadoriasOptions() {
    fetch('/config/api/mercadorias-options')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const select = document.getElementById('mercadoria-select');
                select.innerHTML = '<option value="">Selecionar mercadoria dos processos cadastrados</option>';
                
                data.data.forEach(item => {
                    const option = document.createElement('option');
                    option.value = item.mercadoria;
                    option.textContent = item.mercadoria;
                    select.appendChild(option);
                });
            }
        })
        .catch(error => {
            console.error('Erro ao carregar opções de mercadorias:', error);
        });
}

async function loadMateriais() {
    try {
        const response = await fetch('/config/api/icones-materiais');
        const result = await response.json();
        
        if (result.success) {
            materiais = result.data;
            renderMateriais();
        } else {
            console.error('Erro ao carregar materiais:', result.error);
            showError('Erro ao carregar materiais: ' + result.error);
        }
    } catch (error) {
        console.error('Erro na requisição:', error);
        showError('Erro ao conectar com o servidor');
    }
}

function renderMateriais() {
    const tbody = document.getElementById('materiais-tbody');
    
    if (materiais.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="4" class="px-6 py-4 text-center text-gray-500">
                    Nenhum material cadastrado
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = materiais.map(material => `
        <tr>
            <td class="px-6 py-4 whitespace-nowrap">
                ${material.icone_url ? 
                    `<img src="${material.icone_url}" alt="Ícone" class="w-8 h-8 object-contain rounded border" onerror="this.src='data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzIiIGhlaWdodD0iMzIiIHZpZXdCb3g9IjAgMCAzMiAzMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHJlY3Qgd2lkdGg9IjMyIiBoZWlnaHQ9IjMyIiBmaWxsPSIjRjNGNEY2Ii8+CjxwYXRoIGQ9Ik0xNiAyNEMyMC40MTgzIDI0IDI0IDIwLjQxODMgMjQgMTZDMjQgMTEuNTgxNyAyMC40MTgzIDggMTYgOEMxMS41ODE3IDggOCAxMS41ODE3IDggMTZDOCAyMC40MTgzIDExLjU4MTcgMjQgMTYgMjQiIGZpbGw9IiM5Q0EzQUYiLz4KPC9zdmc+Cg==';this.alt='Sem ícone';">` :
                    `<div class="w-8 h-8 bg-gray-200 rounded border flex items-center justify-center text-gray-400 text-xs">
                        📦
                    </div>`
                }
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                ${material.nome_normalizado}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                ${formatDate(material.created_at)}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                <button onclick="editMaterial(${material.id})" 
                        class="text-blue-600 hover:text-blue-900 mr-3">
                    Editar
                </button>
                <button onclick="deleteMaterial(${material.id})" 
                        class="text-red-600 hover:text-red-900">
                    Excluir
                </button>
            </td>
        </tr>
    `).join('');
}

function openModal(material = null) {
    editingId = material ? material.id : null;
    
    if (material) {
        document.getElementById('modal-title').textContent = 'Editar Material';
        document.getElementById('material_id').value = material.id;
        document.getElementById('nome_normalizado').value = material.nome_normalizado;
        document.getElementById('icone_url').value = material.icone_url || '';
        
        if (material.icone_url) {
            showPreview(material.icone_url);
        }
    } else {
        document.getElementById('modal-title').textContent = 'Adicionar Material';
        document.getElementById('form-material').reset();
        hidePreview();
    }
    
    document.getElementById('modal-material').classList.remove('hidden');
}

function closeModal() {
    document.getElementById('modal-material').classList.add('hidden');
    document.getElementById('form-material').reset();
    hidePreview();
    editingId = null;
}

async function saveMaterial() {
    const formData = new FormData(document.getElementById('form-material'));
    const data = {
        nome_normalizado: formData.get('nome_normalizado').trim().toLowerCase(),
        icone_url: formData.get('icone_url')
    };
    
    if (!data.nome_normalizado) {
        showError('Nome do material é obrigatório');
        return;
    }
    
    try {
        const response = await fetch('/config/api/icones-materiais', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showSuccess(editingId ? 'Material atualizado com sucesso!' : 'Material adicionado com sucesso!');
            closeModal();
            loadMateriais();
        } else {
            showError('Erro ao salvar material: ' + result.error);
        }
    } catch (error) {
        console.error('Erro na requisição:', error);
        showError('Erro ao conectar com o servidor');
    }
}

function editMaterial(id) {
    const material = materiais.find(m => m.id === id);
    if (material) {
        openModal(material);
    }
}

async function deleteMaterial(id) {
    if (!confirm('Tem certeza que deseja excluir este material?')) {
        return;
    }
    
    try {
        const response = await fetch(`/config/api/icones-materiais/${id}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.success) {
            showSuccess('Material excluído com sucesso!');
            loadMateriais();
        } else {
            showError('Erro ao excluir material: ' + result.error);
        }
    } catch (error) {
        console.error('Erro na requisição:', error);
        showError('Erro ao conectar com o servidor');
    }
}

async function uploadIcone(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch('/config/api/upload-icone', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            document.getElementById('icone_url').value = result.url;
            showPreview(result.url);
            showSuccess('Ícone enviado com sucesso!');
        } else {
            showError('Erro no upload: ' + result.error);
        }
    } catch (error) {
        console.error('Erro no upload:', error);
        showError('Erro ao enviar arquivo');
    }
}

function showPreview(url) {
    const preview = document.getElementById('icone-preview');
    const img = document.getElementById('icone-preview-img');
    
    img.src = url;
    preview.classList.remove('hidden');
}

function hidePreview() {
    document.getElementById('icone-preview').classList.add('hidden');
}

function formatDate(dateString) {
    if (!dateString) return '-';
    
    try {
        const date = new Date(dateString);
        return date.toLocaleDateString('pt-BR', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric'
        });
    } catch (error) {
        return '-';
    }
}

function showSuccess(message) {
    // Implementação simples de notificação
    alert('✅ ' + message);
}

function showError(message) {
    // Implementação simples de notificação
    alert('❌ ' + message);
}
