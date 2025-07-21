let materiais = [];
let editingId = null;

document.addEventListener('DOMContentLoaded', function() {
    loadMateriais();
    loadMaterialOptions();
    setupEventListeners();
});

function setupEventListeners() {
    document.getElementById('btn-adicionar').addEventListener('click', function() {
        openModal();
    });
    document.getElementById('btn-cancelar').addEventListener('click', function() {
        closeModal();
    });
    document.getElementById('modal-material').addEventListener('click', function(e) {
        if (e.target === this) closeModal();
    });
    document.getElementById('form-material').addEventListener('submit', function(e) {
        e.preventDefault();
        saveMaterial();
    });
    document.getElementById('icone_file').addEventListener('change', function(e) {
        if (e.target.files.length > 0) uploadIcone(e.target.files[0]);
    });
    document.getElementById('icone_url').addEventListener('input', function(e) {
        const url = e.target.value.trim();
        if (url) showPreview(url); else hidePreview();
    });
    document.getElementById('material-select').addEventListener('change', function(e) {
        // Nada extra, pois o valor já é o nome_normalizado
    });
}

function loadMaterialOptions() {
    fetch('/config/api/icones-materiais')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const select = document.getElementById('material-select');
                select.innerHTML = '<option value="">Selecione o material</option>';
                data.data.forEach(item => {
                    const option = document.createElement('option');
                    option.value = item.mercadoria;
                    option.textContent = item.mercadoria;
                    select.appendChild(option);
                });
            }
        })
        .catch(error => {
            console.error('Erro ao carregar opções de materiais:', error);
        });
}

async function loadMateriais() {
    try {
        const response = await fetch('/config/api/cad-materiais');
        const result = await response.json();
        if (result.success) {
            materiais = result.data;
            renderMateriais();
        } else {
            showError('Erro ao carregar materiais: ' + result.error);
        }
    } catch (error) {
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
                    `<div class="w-8 h-8 bg-gray-200 rounded border flex items-center justify-center text-gray-400 text-xs">📦</div>`
                }
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                ${material.nome_normalizado}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                ${formatDate(material.created_at)}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                <button onclick="editMaterial('${material.id}')" class="text-blue-600 hover:text-blue-900 mr-3">Editar</button>
                <button onclick="deleteMaterial('${material.id}')" class="text-red-600 hover:text-red-900">Excluir</button>
            </td>
        </tr>
    `).join('');
}

function openModal(id = null) {
    editingId = id;
    if (id) {
        const material = materiais.find(m => m.id == id);
        document.getElementById('modal-title').textContent = 'Editar Material';
        document.getElementById('material-select').value = material.nome_normalizado;
        document.getElementById('icone_url').value = material.icone_url || '';
        if (material.icone_url) showPreview(material.icone_url);
    } else {
        document.getElementById('modal-title').textContent = 'Adicionar Material';
        document.getElementById('form-material').reset();
        hidePreview();
    }
    document.getElementById('modal-material').style.display = 'block';
}

function closeModal() {
    document.getElementById('modal-material').style.display = 'none';
    document.getElementById('form-material').reset();
    hidePreview();
    editingId = null;
}

async function saveMaterial() {
    const nome_normalizado = document.getElementById('material-select').value;
    const icone_url = document.getElementById('icone_url').value;
    if (!nome_normalizado) {
        showError('Material é obrigatório');
        return;
    }
    const payload = { nome_normalizado, icone_url };
    let url = '/config/api/cad-materiais';
    let method = 'POST';
    if (editingId) {
        url += '/' + editingId;
        method = 'PUT';
    }
    try {
        const response = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
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
        showError('Erro ao conectar com o servidor');
    }
}

window.editMaterial = function(id) {
    openModal(id);
};

window.deleteMaterial = function(id) {
    if (!confirm('Deseja realmente excluir este material?')) return;
    fetch('/config/api/cad-materiais/' + id, { method: 'DELETE' })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                showSuccess('Material excluído com sucesso!');
                loadMateriais();
            } else {
                showError('Erro ao excluir material: ' + data.error);
            }
        });
};

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
        return date.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' });
    } catch (error) {
        return '-';
    }
}

function showSuccess(message) {
    alert('✅ ' + message);
}

function showError(message) {
    alert('❌ ' + message);
}
