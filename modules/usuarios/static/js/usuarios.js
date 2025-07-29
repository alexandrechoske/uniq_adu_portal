// Sistema de gerenciamento de usuários
document.addEventListener('DOMContentLoaded', function() {
    console.log('[DEBUG] DOM carregado, inicializando sistema de usuários');

    // === ELEMENTOS DOM ===
    const searchInput = document.getElementById('search-input');
    const roleFilter = document.getElementById('role-filter');
    const empresaFilter = document.getElementById('empresa-filter');
    const clearButton = document.getElementById('clear-filters');
    
    console.log('[DEBUG] Elementos encontrados:', {
        searchInput,
        roleFilter,
        empresaFilter,
        clearButton
    });

    // === MODAL DE EDIÇÃO ===
    let currentEditUserId = null;
    let currentEditUserData = null;

    window.openEditModal = function(userId) {
        console.log('[DEBUG] Abrindo modal de edição para usuário:', userId);
        
        currentEditUserId = userId;
        
        // Limpar lista local de empresas para novo usuário
        empresasLocais = [];
        
        // Buscar dados do usuário via AJAX
        fetch(`/usuarios/${userId}/dados`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    currentEditUserData = data.user;
                    populateEditForm(data.user);
                    
                    // Mostrar modal
                    const modal = document.getElementById('editModal');
                    if (modal) {
                        modal.style.display = 'flex';
                    }
                } else {
                    console.error('[DEBUG] Erro ao buscar dados do usuário:', data.error);
                    alert('Erro ao carregar dados do usuário: ' + data.error);
                }
            })
            .catch(error => {
                console.error('[DEBUG] Erro na requisição:', error);
                alert('Erro ao carregar dados do usuário');
            });
    };

    window.closeEditModal = function() {
        console.log('[DEBUG] Fechando modal de edição');
        
        const modal = document.getElementById('editModal');
        if (modal) {
            modal.style.display = 'none';
        }
        
        // Limpar dados
        currentEditUserId = null;
        currentEditUserData = null;
        
        // Limpar lista local de empresas
        empresasLocais = [];
        
        // Limpar formulário
        document.getElementById('editUserForm').reset();
        
        // Esconder seção de empresas
        const empresasSection = document.getElementById('edit-empresas-section');
        if (empresasSection) {
            empresasSection.style.display = 'none';
        }
    };

    function populateEditForm(user) {
        console.log('[DEBUG] Preenchendo formulário com dados:', user);
        
        // Preencher campos básicos
        document.getElementById('edit-name').value = user.name || '';
        document.getElementById('edit-email').value = user.email || '';
        document.getElementById('edit-role').value = user.role || '';
        document.getElementById('edit-is_active').value = user.is_active ? 'true' : 'false';
        
        // Configurar action do formulário
        const form = document.getElementById('editUserForm');
        form.action = `/usuarios/${user.id}/editar`;
        
        // Mostrar/esconder seção de empresas
        const empresasSection = document.getElementById('edit-empresas-section');
        if (user.role === 'cliente_unique' || user.role === 'interno_unique') {
            empresasSection.style.display = 'block';
            loadUserEmpresas(user.id);
        } else {
            empresasSection.style.display = 'none';
        }
    }

    function loadUserEmpresas(userId, empresas = null) {
        console.log('[DEBUG] Carregando empresas do usuário:', userId);
        
        const empresasList = document.getElementById('edit-empresas-list');
        
        if (!empresasList) {
            console.error('[DEBUG] Elemento edit-empresas-list não encontrado');
            return;
        }
        
        // Se empresas não foram passadas, buscar do servidor
        if (empresas === null) {
            // Mostrar indicador de carregamento
            empresasList.innerHTML = '<div style="display: flex; align-items: center; gap: 8px; padding: 1rem; color: var(--color-text-muted);"><i class="mdi mdi-loading mdi-spin"></i>Carregando empresas...</div>';
            
            // Usar timeout para evitar travamento
            const fetchPromise = fetch(`/usuarios/${userId}/empresas-detalhadas`, {
                signal: AbortSignal.timeout(15000) // 15 segundos timeout
            });
            
            fetchPromise
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }
                    return response.json();
                })
                .then(data => {
                    if (data.success) {
                        // Carregar empresas do servidor na lista local
                        empresasLocais = data.empresas || [];
                        atualizarListaEmpresasVisuais();
                    } else {
                        console.error('[DEBUG] Erro do servidor ao carregar empresas:', data.error);
                        empresasList.innerHTML = '<p style="color: var(--color-text-muted); font-style: italic;">Erro ao carregar empresas</p>';
                    }
                })
                .catch(error => {
                    console.error('[DEBUG] Erro ao buscar empresas:', error);
                    
                    let mensagemErro = 'Erro ao carregar empresas';
                    if (error.name === 'TimeoutError') {
                        mensagemErro = 'Timeout ao carregar empresas';
                    } else if (error.name === 'AbortError') {
                        mensagemErro = 'Operação cancelada';
                    } else if (error.message.includes('Server disconnected')) {
                        mensagemErro = 'Conexão perdida - Tente novamente';
                    }
                    
                    empresasList.innerHTML = `
                        <div style="color: var(--color-text-muted); font-style: italic; padding: 1rem; text-align: center;">
                            <div>${mensagemErro}</div>
                            <button onclick="loadUserEmpresas(${userId})" style="margin-top: 8px; padding: 4px 12px; border: 1px solid #ccc; border-radius: 4px; background: white; cursor: pointer;">
                                Tentar Novamente
                            </button>
                        </div>
                    `;
                });
        } else {
            // Carregar empresas passadas como parâmetro na lista local
            empresasLocais = empresas || [];
            atualizarListaEmpresasVisuais();
        }
    }
    
    function displayEmpresas(empresas, userId, container) {
        container.innerHTML = '';
        
        if (!empresas || empresas.length === 0) {
            container.innerHTML = '<p style="color: var(--color-text-muted); font-style: italic;">Nenhuma empresa associada</p>';
            return;
        }
        
        empresas.forEach(empresa => {
            // Suporte para array de CNPJ ou objeto { cnpj, razao_social }
            let cnpj = empresa;
            let razao = '';
            
            if (typeof empresa === 'object' && empresa !== null) {
                cnpj = empresa.cnpj || '';
                razao = empresa.razao_social || '';
            }
            
            const empresaItem = document.createElement('div');
            empresaItem.className = 'empresa-item';
            empresaItem.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.75rem; background: var(--color-bg-secondary); border-radius: 6px; margin-bottom: 0.5rem; border: 1px solid #e5e7eb;">
                    <div style="flex: 1;">
                        <div style="font-weight: 600; color: var(--color-text-primary);">${cnpj}</div>
                        ${razao ? `<div style="color: var(--color-text-muted); font-size: 0.875rem; margin-top: 2px;">${razao}</div>` : ''}
                    </div>
                    <button type="button" onclick="removeEmpresaFromUser('${userId}', '${cnpj}')" class="btn" style="background: var(--color-danger); color: white; padding: 0.375rem 0.75rem; font-size: 0.75rem; border: none; border-radius: 4px; cursor: pointer; display: flex; align-items: center; gap: 4px;">
                        <i class="mdi mdi-delete"></i>
                        Remover
                    </button>
                </div>
            `;
            container.appendChild(empresaItem);
        });
    }

    // Event listeners para busca de empresa
    document.addEventListener('DOMContentLoaded', function() {
        // Buscar empresa ao clicar no botão
        const btnBuscar = document.getElementById('edit-btn-buscar-empresa');
        if (btnBuscar) {
            btnBuscar.addEventListener('click', window.buscarEmpresaEdit);
        }
        
        // Buscar empresa ao pressionar Enter
        const inputBusca = document.getElementById('edit-cnpj-search');
        if (inputBusca) {
            inputBusca.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    window.buscarEmpresaEdit();
                }
            });
        }
    });

    // Função para buscar empresa
    window.buscarEmpresaEdit = function() {
        const cnpjInput = document.getElementById('edit-cnpj-search');
        const termo_busca = cnpjInput.value.trim();
        
        if (!termo_busca) {
            alert('Digite um CNPJ ou Nome da empresa para buscar');
            return;
        }
        
        console.log('[DEBUG] Buscando empresa:', termo_busca);
        
        fetch('/usuarios/api/empresas/buscar', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ cnpj: termo_busca })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                if (data.multiple) {
                    // Múltiplas empresas encontradas - mostrar seletor
                    mostrarSeletorEmpresas(data.empresas, cnpjInput);
                } else {
                    // Uma empresa encontrada - adicionar diretamente
                    addEmpresaToUser(currentEditUserId, data.empresa.cnpj, data.empresa.razao_social);
                    cnpjInput.value = '';
                }
            } else {
                alert('Erro ao buscar empresa: ' + data.error);
            }
        })
        .catch(error => {
            console.error('[DEBUG] Erro ao buscar empresa:', error);
            alert('Erro ao buscar empresa');
        });
    };

    function mostrarSeletorEmpresas(empresas, inputElement) {
        // Remove seletor anterior se existir
        const seletorExistente = document.getElementById('empresa-selector');
        if (seletorExistente) {
            seletorExistente.remove();
        }

        // Array para armazenar empresas selecionadas
        let empresasSelecionadas = [];

        // Criar dropdown de seleção
        const seletor = document.createElement('div');
        seletor.id = 'empresa-selector';
        seletor.className = 'empresa-selector';
        seletor.style.cssText = `
            position: absolute;
            background: white;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            max-height: 300px;
            overflow-y: auto;
            z-index: 1000;
            width: 100%;
            margin-top: 2px;
        `;

        // Header com instruções
        const header = document.createElement('div');
        header.style.cssText = `
            padding: 8px 12px;
            background: #f3f4f6;
            border-bottom: 1px solid #e5e7eb;
            font-size: 0.9em;
            color: #6b7280;
            font-weight: 500;
        `;
        header.innerHTML = `
            <i class="mdi mdi-information-outline"></i>
            Clique para selecionar múltiplas empresas
        `;
        seletor.appendChild(header);

        // Container das empresas
        const containerEmpresas = document.createElement('div');
        seletor.appendChild(containerEmpresas);

        empresas.forEach((empresa, index) => {
            const opcao = document.createElement('div');
            opcao.className = 'empresa-option';
            opcao.dataset.index = index;
            opcao.style.cssText = `
                padding: 10px 12px;
                cursor: pointer;
                border-bottom: 1px solid #eee;
                display: flex;
                align-items: center;
                gap: 10px;
                transition: background-color 0.2s;
            `;

            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.id = `empresa-checkbox-${index}`;
            checkbox.style.cssText = `
                width: 16px;
                height: 16px;
                cursor: pointer;
            `;

            const conteudoEmpresa = document.createElement('div');
            conteudoEmpresa.style.cssText = `flex: 1;`;
            conteudoEmpresa.innerHTML = `
                <div style="font-weight: bold; color: #1f2937;">${empresa.razao_social}</div>
                <div style="font-size: 0.9em; color: #666;">${empresa.cnpj}</div>
            `;

            opcao.appendChild(checkbox);
            opcao.appendChild(conteudoEmpresa);

            // Eventos para seleção
            const toggleSelection = () => {
                checkbox.checked = !checkbox.checked;
                
                if (checkbox.checked) {
                    if (!empresasSelecionadas.find(e => e.cnpj === empresa.cnpj)) {
                        empresasSelecionadas.push(empresa);
                        opcao.style.backgroundColor = '#dbeafe';
                        opcao.style.borderColor = '#3b82f6';
                    }
                } else {
                    empresasSelecionadas = empresasSelecionadas.filter(e => e.cnpj !== empresa.cnpj);
                    opcao.style.backgroundColor = 'white';
                    opcao.style.borderColor = '#eee';
                }
                
                atualizarContadorSelecionadas();
            };

            opcao.addEventListener('click', function(e) {
                if (e.target !== checkbox) {
                    toggleSelection();
                }
            });

            checkbox.addEventListener('change', toggleSelection);

            opcao.addEventListener('mouseenter', function() {
                if (!checkbox.checked) {
                    this.style.backgroundColor = '#f5f5f5';
                }
            });

            opcao.addEventListener('mouseleave', function() {
                if (!checkbox.checked) {
                    this.style.backgroundColor = 'white';
                }
            });

            containerEmpresas.appendChild(opcao);
        });

        // Footer com ações
        const footer = document.createElement('div');
        footer.style.cssText = `
            padding: 12px;
            background: #f9fafb;
            border-top: 1px solid #e5e7eb;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 10px;
        `;

        const contador = document.createElement('div');
        contador.id = 'contador-selecionadas';
        contador.style.cssText = `
            font-size: 0.9em;
            color: #6b7280;
            font-weight: 500;
        `;

        const acoesContainer = document.createElement('div');
        acoesContainer.style.cssText = `
            display: flex;
            gap: 8px;
        `;

        const btnAdicionar = document.createElement('button');
        btnAdicionar.textContent = 'Adicionar à Lista';
        btnAdicionar.style.cssText = `
            background: #28a745;
            color: white;
            padding: 8px 16px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.9em;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 4px;
        `;
        btnAdicionar.innerHTML = `<i class="mdi mdi-plus-circle"></i> Adicionar à Lista`;

        const btnFechar = document.createElement('button');
        btnFechar.textContent = 'Fechar';
        btnFechar.style.cssText = `
            background: #6b7280;
            color: white;
            padding: 8px 16px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.9em;
        `;

        btnAdicionar.addEventListener('click', function() {
            if (empresasSelecionadas.length === 0) {
                alert('Selecione pelo menos uma empresa');
                return;
            }

            // Adicionar todas as empresas selecionadas
            adicionarEmpresasSelecionadas(empresasSelecionadas, inputElement, seletor);
        });

        btnFechar.addEventListener('click', () => {
            seletor.remove();
            inputElement.value = '';
        });

        function atualizarContadorSelecionadas() {
            const total = empresasSelecionadas.length;
            contador.textContent = `${total} empresa${total !== 1 ? 's' : ''} selecionada${total !== 1 ? 's' : ''}`;
            
            btnAdicionar.disabled = total === 0;
            btnAdicionar.style.opacity = total === 0 ? '0.5' : '1';
            
            // Atualizar texto do botão com contador
            btnAdicionar.innerHTML = total > 0 
                ? `<i class="mdi mdi-plus-circle"></i> Adicionar à Lista (${total})`
                : `<i class="mdi mdi-plus-circle"></i> Adicionar à Lista`;
            btnAdicionar.style.cursor = total === 0 ? 'not-allowed' : 'pointer';
        }

        acoesContainer.appendChild(btnAdicionar);
        acoesContainer.appendChild(btnFechar);
        
        footer.appendChild(contador);
        footer.appendChild(acoesContainer);
        seletor.appendChild(footer);

        atualizarContadorSelecionadas();

        // Posicionar o seletor
        const container = inputElement.parentElement;
        container.style.position = 'relative';
        container.appendChild(seletor);

        // Fechar ao clicar fora
        document.addEventListener('click', function fecharSeletor(e) {
            if (!seletor.contains(e.target) && e.target !== inputElement) {
                seletor.remove();
                document.removeEventListener('click', fecharSeletor);
            }
        });
    }

    // Lista local de empresas (não salva até clicar em Salvar do formulário)
    let empresasLocais = [];

    // Funções globais para manipulação das empresas
    window.removerEmpresaLocal = function(cnpj) {
        console.log('[DEBUG] Removendo empresa local:', cnpj);
        empresasLocais = empresasLocais.filter(emp => emp.cnpj !== cnpj);
        atualizarListaEmpresasVisuais();
        mostrarNotificacao('Empresa removida da lista', 'info');
    };

    window.limparEmpresasLocais = function() {
        console.log('[DEBUG] Limpando lista local de empresas');
        empresasLocais = [];
        atualizarListaEmpresasVisuais();
        mostrarNotificacao('Lista de empresas limpa', 'info');
    };

    function adicionarEmpresasLocalmente(empresas) {
        console.log('[DEBUG] Adicionando empresas localmente:', empresas);
        
        // Filtrar empresas que já estão na lista local
        const novasEmpresas = empresas.filter(empresa => 
            !empresasLocais.some(local => local.cnpj === empresa.cnpj)
        );
        
        if (novasEmpresas.length === 0) {
            mostrarNotificacao('Todas as empresas já estão na lista', 'warning');
            return 0;
        }
        
        empresasLocais.push(...novasEmpresas);
        console.log(`[DEBUG] Lista local atualizada: ${empresasLocais.length} empresas`);
        
        // Atualizar a lista visual no modal
        atualizarListaEmpresasVisuais();
        
        // Mostrar feedback
        mostrarNotificacao(`${novasEmpresas.length} empresa${novasEmpresas.length !== 1 ? 's' : ''} adicionada${novasEmpresas.length !== 1 ? 's' : ''} à lista`, 'success');
        
        return novasEmpresas.length;
    }

    function removerEmpresaLocal(cnpj) {
        console.log('[DEBUG] Removendo empresa local:', cnpj);
        empresasLocais = empresasLocais.filter(emp => emp.cnpj !== cnpj);
        atualizarListaEmpresasVisuais();
        mostrarNotificacao('Empresa removida da lista', 'info');
    }

    function limparEmpresasLocais() {
        console.log('[DEBUG] Limpando lista local de empresas');
        empresasLocais = [];
        atualizarListaEmpresasVisuais();
    }

    function atualizarListaEmpresasVisuais() {
        const container = document.getElementById('edit-empresas-list');
        if (!container) return;

        container.innerHTML = '';

        if (empresasLocais.length === 0) {
            container.innerHTML = '<p style="color: var(--color-text-muted); font-style: italic;">Nenhuma empresa adicionada</p>';
            return;
        }

        // Criar header da lista
        const header = document.createElement('div');
        header.style.cssText = `
            background: #f8f9fa;
            padding: 8px 12px;
            border-radius: 6px;
            margin-bottom: 8px;
            font-weight: 600;
            color: #495057;
            border: 1px solid #dee2e6;
        `;
        header.innerHTML = `📋 ${empresasLocais.length} empresa${empresasLocais.length !== 1 ? 's' : ''} selecionada${empresasLocais.length !== 1 ? 's' : ''} (não salva${empresasLocais.length !== 1 ? 's' : ''} ainda)`;
        container.appendChild(header);

        // Criar lista de empresas
        empresasLocais.forEach((empresa, index) => {
            const empresaItem = document.createElement('div');
            empresaItem.className = 'empresa-item-local';
            empresaItem.style.cssText = `
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 12px;
                background: #fff3cd;
                border: 1px solid #ffeaa7;
                border-radius: 6px;
                margin-bottom: 6px;
                transition: all 0.2s;
            `;
            
            empresaItem.innerHTML = `
                <div style="flex: 1;">
                    <div style="font-weight: 600; color: #856404;">${empresa.cnpj}</div>
                    ${empresa.razao_social ? `<div style="color: #6c757d; font-size: 0.875rem; margin-top: 2px;">${empresa.razao_social}</div>` : ''}
                </div>
                <button onclick="window.removerEmpresaLocal('${empresa.cnpj}')" 
                        style="background: #dc3545; color: white; border: none; border-radius: 4px; padding: 6px 8px; cursor: pointer; font-size: 0.8rem;">
                    <i class="mdi mdi-trash-can"></i>
                </button>
            `;
            
            container.appendChild(empresaItem);
        });

        // Botão para limpar todas
        if (empresasLocais.length > 1) {
            const btnLimpar = document.createElement('button');
            btnLimpar.style.cssText = `
                width: 100%;
                padding: 8px;
                background: #6c757d;
                color: white;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                margin-top: 8px;
                font-size: 0.85rem;
            `;
            btnLimpar.innerHTML = '<i class="mdi mdi-broom"></i> Limpar Todas';
            btnLimpar.onclick = window.limparEmpresasLocais;
            container.appendChild(btnLimpar);
        }
    }

    function mostrarNotificacao(mensagem, tipo = 'info') {
        const cores = {
            success: '#10b981',
            warning: '#f59e0b', 
            error: '#ef4444',
            info: '#3b82f6'
        };

        const icones = {
            success: 'mdi-check-circle',
            warning: 'mdi-alert',
            error: 'mdi-alert-circle', 
            info: 'mdi-information'
        };

        const notificacao = document.createElement('div');
        notificacao.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${cores[tipo]};
            color: white;
            padding: 12px 16px;
            border-radius: 8px;
            z-index: 9999;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 8px;
            max-width: 350px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        `;
        notificacao.innerHTML = `<i class="mdi ${icones[tipo]}"></i><span>${mensagem}</span>`;
        
        document.body.appendChild(notificacao);
        
        setTimeout(() => {
            if (notificacao.parentNode) {
                notificacao.parentNode.removeChild(notificacao);
            }
        }, 3000);
    }

    function adicionarEmpresasSelecionadas(empresas, inputElement, seletor) {
        console.log('[DEBUG] Adicionando empresas selecionadas à lista local:', empresas);
        
        const novasAdicionadas = adicionarEmpresasLocalmente(empresas);
        
        // Fechar seletor e limpar input
        inputElement.value = '';
        seletor.remove();
    }

    function addEmpresaToUser(userId, cnpj, razaoSocial = null) {
        console.log('[DEBUG] Adicionando empresa ao usuário:', userId, cnpj);
        
        fetch(`/usuarios/${userId}/empresas/adicionar`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ cnpj: cnpj })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Recarregar lista de empresas
                if (currentEditUserData) {
                    if (!currentEditUserData.empresas) {
                        currentEditUserData.empresas = [];
                    }
                    currentEditUserData.empresas.push({
                        cnpj: data.empresa ? data.empresa.cnpj : cnpj,
                        razao_social: data.empresa ? data.empresa.razao_social : razaoSocial
                    });
                    loadUserEmpresas(userId);
                }
                
                // Mostrar mensagem de sucesso
                const successMsg = document.createElement('div');
                successMsg.style.cssText = `
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    background: #10b981;
                    color: white;
                    padding: 12px 16px;
                    border-radius: 4px;
                    z-index: 9999;
                `;
                successMsg.textContent = 'Empresa adicionada com sucesso!';
                document.body.appendChild(successMsg);
                
                setTimeout(() => {
                    if (successMsg.parentNode) {
                        successMsg.parentNode.removeChild(successMsg);
                    }
                }, 3000);
                
            } else {
                alert('Erro ao adicionar empresa: ' + data.error);
            }
        })
        .catch(error => {
            console.error('[DEBUG] Erro ao adicionar empresa:', error);
            alert('Erro ao adicionar empresa');
        });
    }

    window.removeEmpresaFromUser = function(userId, cnpj) {
        console.log('[DEBUG] Removendo empresa do usuário:', userId, cnpj);
        
        if (!confirm('Tem certeza que deseja remover esta empresa?')) {
            return;
        }
        
        fetch(`/usuarios/${userId}/empresas/remover`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ cnpj: cnpj })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Remover da lista local e recarregar
                if (currentEditUserData && currentEditUserData.empresas) {
                    currentEditUserData.empresas = currentEditUserData.empresas.filter(e => 
                        (typeof e === 'string' ? e : e.cnpj) !== cnpj
                    );
                }
                loadUserEmpresas(userId);
            } else {
                alert('Erro ao remover empresa: ' + data.error);
            }
        })
        .catch(error => {
            console.error('[DEBUG] Erro ao remover empresa:', error);
            alert('Erro ao remover empresa');
        });
    };

    // Event listener para botão de buscar empresa
    const btnBuscarEmpresa = document.getElementById('edit-btn-buscar-empresa');
    if (btnBuscarEmpresa) {
        btnBuscarEmpresa.addEventListener('click', buscarEmpresaEdit);
    }

    // Event listener para mudança de role
    const editRoleSelect = document.getElementById('edit-role');
    if (editRoleSelect) {
        editRoleSelect.addEventListener('change', function() {
            const empresasSection = document.getElementById('edit-empresas-section');
            if (this.value === 'cliente_unique' || this.value === 'interno_unique') {
                empresasSection.style.display = 'block';
            } else {
                empresasSection.style.display = 'none';
            }
        });
    }

    // Event listener para fechar modal ao clicar fora
    const editModal = document.getElementById('editModal');
    if (editModal) {
        // Event listener para o modal de edição
        const editModal = document.getElementById('editModal');
        const editForm = document.getElementById('editUserForm');
        
        // Interceptar submit do formulário para salvar empresas
        if (editForm) {
            editForm.addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const formData = new FormData(this);
                const submitButton = this.querySelector('button[type="submit"]');
                const originalText = submitButton ? submitButton.innerHTML : '';
                
                try {
                    // Mostrar loading
                    if (submitButton) {
                        submitButton.innerHTML = '<i class="mdi mdi-loading mdi-spin"></i> Salvando...';
                        submitButton.disabled = true;
                    }
                    
                    // Sempre salvar a lista de empresas (mesmo se vazia)
                    console.log('[DEBUG] Salvando lista de empresas:', empresasLocais);
                    
                    const cnpjs = empresasLocais.map(emp => emp.cnpj);
                    
                    // Se a lista está vazia, enviar array vazio para limpar
                    const empresasResponse = await fetch(`/usuarios/${currentEditUserId}/empresas/definir-lista`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ cnpjs: cnpjs }),
                        signal: AbortSignal.timeout(30000)
                    });
                    
                    const empresasData = await empresasResponse.json();
                    
                    if (!empresasData.success) {
                        throw new Error(`Erro ao salvar empresas: ${empresasData.error}`);
                    }
                    
                    console.log('[DEBUG] Lista de empresas salva com sucesso:', empresasData);
                    
                    // Mostrar resultado das empresas
                    if (cnpjs.length === 0) {
                        mostrarNotificacao('Todas as empresas removidas do usuário', 'success');
                    } else {
                        const resultado = empresasData.resultado || {};
                        if (resultado.sucessos > 0) {
                            mostrarNotificacao(`${resultado.sucessos} empresa${resultado.sucessos !== 1 ? 's' : ''} salva${resultado.sucessos !== 1 ? 's' : ''} com sucesso!`, 'success');
                        }
                        if (resultado.erros > 0) {
                            mostrarNotificacao(`${resultado.erros} empresa${resultado.erros !== 1 ? 's' : ''} com erro`, 'warning');
                        }
                        if (resultado.ja_existentes > 0) {
                            mostrarNotificacao(`${resultado.ja_existentes} empresa${resultado.ja_existentes !== 1 ? 's' : ''} já existia${resultado.ja_existentes !== 1 ? 'm' : ''}`, 'info');
                        }
                    }
                    
                    // Agora salvar os dados do usuário normalmente
                    const userResponse = await fetch(this.action || `/usuarios/${currentEditUserId}/editar`, {
                        method: 'POST',
                        body: formData
                    });
                    
                    if (userResponse.ok) {
                        mostrarNotificacao('Usuário atualizado com sucesso!', 'success');
                        
                        // Fechar modal e recarregar página
                        setTimeout(() => {
                            closeEditModal();
                            window.location.reload();
                        }, 1500);
                    } else {
                        throw new Error('Erro ao salvar usuário');
                    }
                    
                } catch (error) {
                    console.error('[DEBUG] Erro no salvamento:', error);
                    mostrarNotificacao(`Erro: ${error.message}`, 'error');
                } finally {
                    // Restaurar botão
                    if (submitButton) {
                        submitButton.innerHTML = originalText;
                        submitButton.disabled = false;
                    }
                }
            });
        }

        editModal.addEventListener('click', function(e) {
            if (e.target === editModal) {
                closeEditModal();
            }
        });
    }

    // Event listener para fechar modal com ESC
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            const editModal = document.getElementById('editModal');
            if (editModal && editModal.style.display !== 'none') {
                closeEditModal();
            }
            const deleteModal = document.getElementById('deleteModal');
            if (deleteModal && deleteModal.classList.contains('show')) {
                closeDeleteModal();
            }
        }
    });

    // === MODAL DE EXCLUSÃO ===
    let currentDeleteUserId = null;
    let currentDeleteUserName = null;

    window.openDeleteModal = function(userId) {
        console.log('[DEBUG] Abrindo modal de exclusão para usuário:', userId);
        
        currentDeleteUserId = userId;
        
        // Buscar informações do usuário na tabela
        const userRow = document.querySelector(`tr[data-user-id="${userId}"]`);
        if (userRow) {
            const userName = userRow.dataset.name || 'Usuário desconhecido';
            const userEmail = userRow.dataset.email || '';
            const userRole = userRow.dataset.role || '';
            
            currentDeleteUserName = userName;
            
            // Atualizar informações no modal
            document.getElementById('delete-user-name').textContent = userName;
            document.getElementById('delete-user-email').textContent = userEmail;
            document.getElementById('delete-user-role').textContent = getRoleDisplayName(userRole);
            
            // Configurar formulário
            const deleteForm = document.getElementById('deleteForm');
            if (deleteForm) {
                deleteForm.action = `/usuarios/${userId}/deletar`;
                console.log('[DEBUG] Action do formulário configurado:', deleteForm.action);
            }
        }
        
        // Mostrar modal
        const modal = document.getElementById('deleteModal');
        if (modal) {
            modal.classList.add('show');
            modal.style.display = 'flex';
            
            // Focar no botão de cancelar para acessibilidade
            const cancelButton = modal.querySelector('.btn-outline');
            if (cancelButton) {
                setTimeout(() => cancelButton.focus(), 100);
            }
        }
    };

    window.closeDeleteModal = function() {
        console.log('[DEBUG] Fechando modal de exclusão');
        
        const modal = document.getElementById('deleteModal');
        if (modal) {
            modal.classList.remove('show');
            modal.style.display = 'none';
        }
        
        currentDeleteUserId = null;
        currentDeleteUserName = null;
    };

    // === SISTEMA DE FILTROS ===
    function filterUsers() {
        if (!searchInput || !roleFilter || !empresaFilter) {
            console.warn('[DEBUG] Elementos de filtro não encontrados');
            return;
        }

        const searchTerm = searchInput.value.toLowerCase();
        const selectedRole = roleFilter.value;
        const empresaTerm = empresaFilter.value.toLowerCase();
        
        console.log('[DEBUG] Filtrando com:', { searchTerm, selectedRole, empresaTerm });
        
        // Filtrar todas as linhas de usuários
        const userRows = document.querySelectorAll('.user-row');
        const sections = document.querySelectorAll('.users-section');
        
        let visibleCounts = {
            admin: 0,
            interno_unique: 0,
            cliente_unique: 0
        };
        
        userRows.forEach(row => {
            const name = (row.dataset.name || '').toLowerCase();
            const email = (row.dataset.email || '').toLowerCase();
            const role = row.dataset.role || '';
            const empresas = (row.dataset.empresas || '').toLowerCase();
            
            const matchesSearch = !searchTerm || 
                                name.includes(searchTerm) || 
                                email.includes(searchTerm);
            const matchesRole = !selectedRole || role === selectedRole;
            const matchesEmpresa = !empresaTerm || empresas.includes(empresaTerm);
            
            const isVisible = matchesSearch && matchesRole && matchesEmpresa;
            
            row.style.display = isVisible ? '' : 'none';
            
            if (isVisible) {
                visibleCounts[role] = (visibleCounts[role] || 0) + 1;
            }
        });
        
        // Atualizar contadores das seções
        updateSectionCounts(visibleCounts);
        
        // Mostrar/ocultar seções vazias
        updateSectionVisibility(sections, visibleCounts, selectedRole, searchTerm, empresaTerm);
    }

    function updateSectionCounts(visibleCounts) {
        const counters = {
            'admin-section-count': visibleCounts.admin || 0,
            'interno-section-count': visibleCounts.interno_unique || 0,
            'cliente-section-count': visibleCounts.cliente_unique || 0
        };

        Object.entries(counters).forEach(([id, count]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = `${count} usuário${count !== 1 ? 's' : ''}`;
            }
        });
    }

    function updateSectionVisibility(sections, visibleCounts, selectedRole, searchTerm, empresaTerm) {
        sections.forEach(section => {
            const role = section.dataset.role;
            const hasVisibleUsers = role && visibleCounts[role] > 0;
            const shouldShow = !selectedRole || selectedRole === role;
            
            if (!hasVisibleUsers && shouldShow && (searchTerm || empresaTerm)) {
                // Mostrar seção com mensagem de nenhum resultado
                section.style.display = 'block';
                showNoResultsMessage(section);
            } else if (hasVisibleUsers || (!searchTerm && !empresaTerm && !selectedRole)) {
                // Mostrar seção normalmente
                section.style.display = shouldShow ? 'block' : 'none';
                hideNoResultsMessage(section);
            } else {
                // Ocultar seção
                section.style.display = 'none';
                hideNoResultsMessage(section);
            }
        });
    }

    function showNoResultsMessage(section) {
        const tbody = section.querySelector('tbody');
        if (tbody && !tbody.querySelector('.no-results')) {
            const noResultsRow = document.createElement('tr');
            noResultsRow.className = 'no-results';
            noResultsRow.innerHTML = `
                <td colspan="4" class="empty-state">
                    <i class="mdi mdi-filter-remove"></i>
                    <p>Nenhum usuário encontrado com os filtros aplicados</p>
                </td>
            `;
            tbody.appendChild(noResultsRow);
        }
    }

    function hideNoResultsMessage(section) {
        const noResults = section.querySelector('.no-results');
        if (noResults) {
            noResults.remove();
        }
    }

    // === UTILITÁRIOS ===
    function getRoleDisplayName(role) {
        const roleNames = {
            'admin': 'Administrador',
            'interno_unique': 'Interno Unique',
            'cliente_unique': 'Cliente Unique'
        };
        return roleNames[role] || role;
    }

    function showNotification(message, type = 'info', duration = 3000) {
        // Implementação simples de notificação
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 20px;
            border-radius: 8px;
            color: white;
            font-weight: 500;
            z-index: 9999;
            animation: slideInRight 0.3s ease;
        `;
        
        const colors = {
            info: '#3b82f6',
            success: '#10b981',
            warning: '#f59e0b',
            error: '#ef4444'
        };
        
        notification.style.background = colors[type] || colors.info;
        
        document.body.appendChild(notification);
        
        if (duration > 0) {
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.style.animation = 'slideOutRight 0.3s ease';
                    setTimeout(() => {
                        notification.remove();
                    }, 300);
                }
            }, duration);
        }
        
        return notification;
    }

    // === EVENT LISTENERS ===
    
    // Filtros
    if (searchInput) {
        searchInput.addEventListener('input', filterUsers);
    }
    
    if (roleFilter) {
        roleFilter.addEventListener('change', filterUsers);
    }
    
    if (empresaFilter) {
        empresaFilter.addEventListener('input', filterUsers);
    }
    
    // Limpar filtros
    if (clearButton) {
        clearButton.addEventListener('click', function() {
            if (searchInput) searchInput.value = '';
            if (roleFilter) roleFilter.value = '';
            if (empresaFilter) empresaFilter.value = '';
            filterUsers();
        });
    }
    
    // Botão de atualizar
    const refreshButton = document.querySelector('a[href*="/usuarios/refresh"]');
    if (refreshButton) {
        refreshButton.addEventListener('click', function(e) {
            const originalContent = this.innerHTML;
            this.innerHTML = '<i class="mdi mdi-loading mdi-spin"></i> Atualizando...';
            this.style.pointerEvents = 'none';
            this.style.opacity = '0.75';
            
            // Restaurar após um tempo (caso a página não recarregue)
            setTimeout(() => {
                this.innerHTML = originalContent;
                this.style.pointerEvents = '';
                this.style.opacity = '';
            }, 10000);
        });
    }
    
    // Modal - fechar ao clicar fora
    const deleteModal = document.getElementById('deleteModal');
    if (deleteModal) {
        deleteModal.addEventListener('click', function(e) {
            if (e.target === this) {
                closeDeleteModal();
            }
        });
    }
    
    // Modal - fechar com ESC
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeDeleteModal();
        }
    });
    
    // Formulário de exclusão - debug e feedback
    const deleteForm = document.getElementById('deleteForm');
    if (deleteForm) {
        console.log('[DEBUG] Formulário de exclusão encontrado');
        
        deleteForm.addEventListener('submit', function(e) {
            console.log('[DEBUG] Formulário de exclusão enviado');
            console.log('[DEBUG] Action:', this.action);
            console.log('[DEBUG] Method:', this.method);
            
            // Mostrar feedback de loading
            const submitButton = this.querySelector('button[type="submit"]');
            if (submitButton) {
                const originalContent = submitButton.innerHTML;
                submitButton.innerHTML = '<i class="mdi mdi-loading mdi-spin"></i> Excluindo...';
                submitButton.disabled = true;
            }
            
            // Mostrar notificação
            showNotification('Excluindo usuário...', 'info', 0);
        });
    } else {
        console.error('[DEBUG] Formulário de exclusão NÃO encontrado!');
    }
    
    // Debug dos botões de exclusão
    const deleteButtons = document.querySelectorAll('button[onclick*="openDeleteModal"]');
    console.log('[DEBUG] Botões de exclusão encontrados:', deleteButtons.length);
    
    deleteButtons.forEach((button, index) => {
        console.log(`[DEBUG] Botão ${index + 1}:`, button.getAttribute('onclick'));
        
        button.addEventListener('click', function(e) {
            console.log(`[DEBUG] Botão de exclusão ${index + 1} clicado`);
        });
    });

    // === INICIALIZAÇÃO ===
    console.log('[DEBUG] Sistema de usuários inicializado com sucesso');
    
    // Aplicar filtros iniciais se houver valores
    if (searchInput?.value || roleFilter?.value || empresaFilter?.value) {
        filterUsers();
    }
});
