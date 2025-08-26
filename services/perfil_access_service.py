"""
Serviço de Controle de Acesso baseado em Perfis
Filtra menu e páginas conforme os perfis associados ao usuário
"""

from flask import session
import json

class PerfilAccessService:
    # Mapeamento de códigos de módulos para compatibilidade
    MODULE_MAPPING = {
        'fin': 'financeiro',  # Mapear 'fin' para 'financeiro'
        'imp': 'importacoes',  # Mapear 'imp' para 'importacoes' (com S para coincidir com menu)
        'exp': 'exportacao',  # Mapear 'exp' para 'exportacao' (futuro)
        'con': 'consultoria', # Mapear 'con' para 'consultoria' (futuro)
    }
    
    # Mapeamento de códigos de páginas para endpoints/módulos
    PAGE_TO_ENDPOINT_MAPPING = {
        # Páginas do módulo Importação (imp)
        'dashboard_executivo': 'dashboard_executivo',  # Dashboard Executivo
        'dashboard_resumido': 'dash_importacoes_resumido',  # Dashboard Importações
        'documentos': 'conferencia',  # Conferência Documental 
        'relatorio': 'export_relatorios',  # Exportação de Relatórios
        'agente': 'agente',  # Agente UniQ
        
        # Páginas do módulo Financeiro (fin)
        'fin_dashboard_executivo': 'fin_dashboard_executivo',  # Dashboard Executivo Financeiro
        'fluxo_caixa': 'fluxo_de_caixa',  # Fluxo de Caixa
        'despesas': 'despesas_anual',  # Despesas
        'faturamento': 'faturamento_anual',  # Faturamento
        # 'dashboard_executivo' já mapeado acima (compartilhado)
    }
    
    @staticmethod
    def get_user_accessible_modules():
        """
        Retorna lista de módulos que o usuário tem acesso baseado em seu perfil_principal
        
        Returns:
            list: Lista de códigos de módulos acessíveis
        """
        user = session.get('user', {})
        user_role = user.get('role')
        user_perfil_principal = user.get('perfil_principal', 'basico')
        user_email = user.get('email')
        user_perfis_info = user.get('user_perfis_info', [])
        
        print(f"[ACCESS_SERVICE] Verificando módulos acessíveis para {user_email}")
        print(f"[ACCESS_SERVICE] Role: {user_role}, Perfil Principal: {user_perfil_principal}")
        
        # Master Admins: admin + master_admin - acesso total
        if user_role == 'admin' and user_perfil_principal == 'master_admin':
            accessible_modules = [
                'dashboard', 'importacoes', 'financeiro', 'relatorios', 
                'usuarios', 'agente', 'conferencia', 'materiais', 'config',
                'dashboard_executivo', 'dash_importacoes_resumido', 'export_relatorios',
                'fin_dashboard_executivo', 'fluxo_de_caixa', 'despesas_anual', 'faturamento_anual'
            ]
            print(f"[ACCESS_SERVICE] Master Admin (master_admin) - módulos disponíveis: {accessible_modules}")
            return accessible_modules
        
        # Module Admins: interno_unique + admin_operacao/admin_financeiro
        if user_role == 'interno_unique' and user_perfil_principal.startswith('admin_'):
            accessible_modules = set()
            
            if user_perfil_principal == 'admin_operacao':
                # Admin Operacional - módulos operacionais: Importação, Consultoria, Exportação + gestão de usuários
                accessible_modules.update([
                    'importacoes', 'dashboard_executivo', 'dash_importacoes_resumido', 
                    'export_relatorios', 'conferencia', 'agente', 'usuarios',
                    # Future modules ready for implementation:
                    'consultoria', 'exportacao'
                ])
                print(f"[ACCESS_SERVICE] Module Admin (admin_operacao) - módulos disponíveis: {list(accessible_modules)}")
                
            elif user_perfil_principal == 'admin_financeiro':
                # Admin de Financeiro - APENAS módulos financeiros + gestão de usuários
                accessible_modules.update([
                    'financeiro', 'fin_dashboard_executivo', 'fluxo_de_caixa', 
                    'despesas_anual', 'faturamento_anual', 'usuarios'
                ])
                print(f"[ACCESS_SERVICE] Module Admin (admin_financeiro) - módulos disponíveis: {list(accessible_modules)}")
            
            return list(accessible_modules)
        
        # Basic Users: interno_unique/cliente_unique + basico - acesso baseado em perfis
        if user_perfil_principal == 'basico':
            accessible_modules = set()
            accessible_pages_all = set()  # Para rastrear todas as páginas acessíveis
            
            for perfil_info in user_perfis_info:
                perfil_nome = perfil_info.get('perfil_nome')
                modulos = perfil_info.get('modulos', [])
                
                for modulo in modulos:
                    modulo_codigo = modulo.get('codigo')
                    if modulo_codigo:
                        # Aplicar mapeamento de módulos se necessário
                        modulo_mapeado = PerfilAccessService.MODULE_MAPPING.get(modulo_codigo, modulo_codigo)
                        accessible_modules.add(modulo_mapeado)
                        print(f"[ACCESS_SERVICE] Adicionado módulo: {modulo_codigo} → {modulo_mapeado} (perfil: {perfil_nome})")
                        
                        # Rastrear páginas para determinar acesso adicional a módulos
                        modulo_paginas = modulo.get('paginas', [])
                        for pagina in modulo_paginas:
                            if isinstance(pagina, str):
                                accessible_pages_all.add(pagina)
                            elif isinstance(pagina, dict):
                                accessible_pages_all.add(pagina.get('codigo', ''))
            
            # Adicionar módulos baseados em páginas específicas com contexto de módulo
            for perfil_info in user_perfis_info:
                modulos = perfil_info.get('modulos', [])
                
                for modulo in modulos:
                    modulo_codigo = modulo.get('codigo')
                    modulo_paginas = modulo.get('paginas', [])
                    
                    for pagina in modulo_paginas:
                        pagina_codigo = pagina if isinstance(pagina, str) else pagina.get('codigo', '')
                        
                        if pagina_codigo in PerfilAccessService.PAGE_TO_ENDPOINT_MAPPING:
                            endpoint_module = PerfilAccessService.PAGE_TO_ENDPOINT_MAPPING[pagina_codigo]
                            accessible_modules.add(endpoint_module)
                            print(f"[ACCESS_SERVICE] Adicionado módulo por página: {pagina_codigo} → {endpoint_module}")
                        
                        # Adicionar módulos gerais para compatibilidade com sidebar/menu (com contexto)
                        if pagina_codigo == 'dashboard_executivo':
                            # Dashboard Executivo é específico por módulo - só adicionar se for do módulo de importação
                            if modulo_codigo == 'imp':
                                accessible_modules.add('dashboard_executivo')
                                print(f"[ACCESS_SERVICE] Adicionado módulo geral: dashboard_executivo (contexto: importação)")
                            # Para financeiro, o dashboard executivo é interno ao submenu
                        elif pagina_codigo == 'fin_dashboard_executivo':
                            # Dashboard Executivo Financeiro - específico do módulo financeiro
                            if modulo_codigo == 'fin':
                                accessible_modules.add('fin_dashboard_executivo')
                                print(f"[ACCESS_SERVICE] Adicionado módulo geral: fin_dashboard_executivo (contexto: financeiro)")
                        elif pagina_codigo == 'dashboard_resumido':
                            accessible_modules.add('importacoes')
                            print(f"[ACCESS_SERVICE] Adicionado módulo geral: importacoes")
                        elif pagina_codigo == 'documentos':
                            accessible_modules.add('conferencia')
                            print(f"[ACCESS_SERVICE] Adicionado módulo geral: conferencia")
                        elif pagina_codigo == 'relatorio':
                            accessible_modules.add('relatorios')
                            print(f"[ACCESS_SERVICE] Adicionado módulo geral: relatorios")
                        elif pagina_codigo == 'agente':
                            accessible_modules.add('agente')
                            print(f"[ACCESS_SERVICE] Adicionado módulo geral: agente")
            
            accessible_modules = list(accessible_modules)
            print(f"[ACCESS_SERVICE] Basic Users ({user_perfil_principal}) - módulos acessíveis finais: {accessible_modules}")
            return accessible_modules
        
        # Specific Profile Users: Users with specific profile names as perfil_principal
        # Handle users like Kauan with perfil_principal='financeiro_fluxo_de_caixa'
        if user_role == 'interno_unique' and user_perfil_principal not in ['basico'] and not user_perfil_principal.startswith('admin_'):
            accessible_modules = set()
            
            # Define specific profile access patterns
            profile_access_map = {
                'financeiro_fluxo_de_caixa': {
                    'modules': ['financeiro', 'fluxo_de_caixa'],
                    'pages': ['fluxo_caixa']
                },
                'financeiro_completo': {
                    'modules': ['financeiro', 'fin_dashboard_executivo', 'fluxo_de_caixa', 'despesas_anual', 'faturamento_anual'],
                    'pages': ['fin_dashboard_executivo', 'fluxo_caixa', 'despesas', 'faturamento']  # Only financial pages
                },
                'importacao_basico': {
                    'modules': ['importacoes', 'dashboard_executivo'],
                    'pages': ['dashboard_executivo', 'dashboard_resumido']
                },
                'importacao_completo': {
                    'modules': ['importacoes', 'dashboard_executivo', 'dash_importacoes_resumido', 'export_relatorios', 'conferencia', 'agente'],
                    'pages': ['*']  # All importation pages
                },
                'importacoes_completo': {
                    'modules': ['importacoes', 'dashboard_executivo', 'dash_importacoes_resumido', 'export_relatorios', 'conferencia', 'agente'],
                    'pages': ['*']  # All importation pages
                }
            }
            
            # Check if user's profile is in the map
            if user_perfil_principal in profile_access_map:
                profile_config = profile_access_map[user_perfil_principal]
                accessible_modules.update(profile_config['modules'])
                print(f"[ACCESS_SERVICE] Specific Profile User ({user_perfil_principal}) - módulos definidos: {profile_config['modules']}")
            else:
                # If specific profile not found, try to derive access from perfis_json
                print(f"[ACCESS_SERVICE] Profile {user_perfil_principal} não encontrado no mapa, tentando derivar do perfis_json")
                
                # Try to get access from user_perfis_info if available
                for perfil_info in user_perfis_info:
                    perfil_nome = perfil_info.get('perfil_nome')
                    if perfil_nome == user_perfil_principal:
                        modulos = perfil_info.get('modulos', [])
                        
                        for modulo in modulos:
                            modulo_codigo = modulo.get('codigo')
                            if modulo_codigo:
                                # Apply module mapping
                                modulo_mapeado = PerfilAccessService.MODULE_MAPPING.get(modulo_codigo, modulo_codigo)
                                accessible_modules.add(modulo_mapeado)
                                print(f"[ACCESS_SERVICE] Adicionado módulo do perfis_json: {modulo_codigo} → {modulo_mapeado}")
                                
                                # Add specific page modules
                                modulo_paginas = modulo.get('paginas', [])
                                for pagina in modulo_paginas:
                                    pagina_codigo = pagina if isinstance(pagina, str) else pagina.get('codigo', '')
                                    
                                    if pagina_codigo in PerfilAccessService.PAGE_TO_ENDPOINT_MAPPING:
                                        endpoint_module = PerfilAccessService.PAGE_TO_ENDPOINT_MAPPING[pagina_codigo]
                                        accessible_modules.add(endpoint_module)
                                        print(f"[ACCESS_SERVICE] Adicionado módulo por página: {pagina_codigo} → {endpoint_module}")
            
            accessible_modules = list(accessible_modules)
            print(f"[ACCESS_SERVICE] Specific Profile User ({user_perfil_principal}) - módulos acessíveis finais: {accessible_modules}")
            return accessible_modules
        
        # Fallback - sem acesso
        print(f"[ACCESS_SERVICE] Sem acesso definido para role={user_role}, perfil_principal={user_perfil_principal}")
        return []
    
    @staticmethod
    def get_user_accessible_pages(modulo_codigo):
        """
        Retorna lista de páginas que o usuário tem acesso em um módulo específico
        
        Args:
            modulo_codigo (str): Código do módulo
            
        Returns:
            list: Lista de códigos de páginas acessíveis ou ['*'] para todas
        """
        user = session.get('user', {})
        user_role = user.get('role')
        user_perfil_principal = user.get('perfil_principal', 'basico')
        user_perfis_info = user.get('user_perfis_info', [])
        
        print(f"[ACCESS_SERVICE] Verificando páginas acessíveis no módulo {modulo_codigo}")
        print(f"[ACCESS_SERVICE] Role: {user_role}, Perfil Principal: {user_perfil_principal}")
        
        # Master Admins: admin + master_admin - acesso total
        if user_role == 'admin' and user_perfil_principal == 'master_admin':
            print(f"[ACCESS_SERVICE] Master Admin (master_admin) - todas as páginas disponíveis no módulo {modulo_codigo}")
            return ['*']
        
        # Module Admins: interno_unique + admin_operacao/admin_financeiro
        if user_role == 'interno_unique' and user_perfil_principal.startswith('admin_'):
            # Verificar se o usuário administra este módulo
            user_manages_module = False
            
            if user_perfil_principal == 'admin_operacao':
                # Mapear módulos operacionais: Importações, Consultoria, Exportação
                operational_modules = [
                    'importacoes', 'dashboard_executivo', 'dash_importacoes_resumido', 'export_relatorios',
                    'conferencia', 'agente',  # Existing importacao modules
                    'consultoria', 'con',  # Future consultoria modules 
                    'exportacao', 'exp'  # Future exportacao modules
                ]
                user_manages_module = modulo_codigo in operational_modules
                
            elif user_perfil_principal == 'admin_financeiro':
                # Mapear módulos financeiros
                financeiro_modules = ['financeiro', 'fin_dashboard_executivo', 'fluxo_de_caixa', 'despesas_anual', 'faturamento_anual']
                user_manages_module = modulo_codigo in financeiro_modules
            
            # Todos os Module Admins podem acessar gestão de usuários
            if modulo_codigo == 'usuarios':
                user_manages_module = True
            
            if user_manages_module:
                print(f"[ACCESS_SERVICE] Module Admin ({user_perfil_principal}) - acesso total ao módulo {modulo_codigo}")
                return ['*']
            else:
                print(f"[ACCESS_SERVICE] Module Admin ({user_perfil_principal}) - sem acesso ao módulo {modulo_codigo}")
                return []
        
        # Basic Users: acesso baseado em perfis
        if user_perfil_principal == 'basico':
            accessible_pages = set()
            
            # Criar mapeamento reverso para buscar módulo original
            reverse_mapping = {v: k for k, v in PerfilAccessService.MODULE_MAPPING.items()}
            modulo_original = reverse_mapping.get(modulo_codigo, modulo_codigo)
            
            for perfil_info in user_perfis_info:
                perfil_nome = perfil_info.get('perfil_nome')
                modulos = perfil_info.get('modulos', [])
                
                for modulo in modulos:
                    # Verificar tanto o código original quanto o mapeado
                    modulo_db = modulo.get('codigo')
                    if modulo_db == modulo_codigo or modulo_db == modulo_original:
                        modulo_paginas = modulo.get('paginas', [])
                        
                        # Se lista vazia ou contém '*', acesso a todas as páginas
                        if not modulo_paginas or '*' in modulo_paginas:
                            print(f"[ACCESS_SERVICE] Perfil {perfil_nome} permite todas as páginas do módulo {modulo_codigo}")
                            return ['*']
                        
                        # Adicionar páginas específicas
                        for pagina in modulo_paginas:
                            # Se pagina é um dict, extrair o código
                            if isinstance(pagina, dict):
                                pagina_codigo = pagina.get('codigo')
                                if pagina_codigo:
                                    accessible_pages.add(pagina_codigo)
                                    print(f"[ACCESS_SERVICE] Adicionada página: {pagina_codigo} (perfil: {perfil_nome})")
                            else:
                                # Se é string, usar diretamente
                                accessible_pages.add(pagina)
                                print(f"[ACCESS_SERVICE] Adicionada página: {pagina} (perfil: {perfil_nome})")
            
            accessible_pages = list(accessible_pages)
            print(f"[ACCESS_SERVICE] Basic Users - páginas acessíveis no módulo {modulo_codigo}: {accessible_pages}")
            return accessible_pages
        
        # Specific Profile Users: Handle users with specific profile names as perfil_principal
        if user_role == 'interno_unique' and user_perfil_principal not in ['basico'] and not user_perfil_principal.startswith('admin_'):
            # Define specific profile page access patterns
            profile_page_access_map = {
                'financeiro_fluxo_de_caixa': {
                    'financeiro': ['fluxo_caixa'],
                    'fluxo_de_caixa': ['*']  # Full access to fluxo_de_caixa module
                },
                'financeiro_completo': {
                    'financeiro': ['*'],  # All financial pages
                    'fin_dashboard_executivo': ['*'],
                    'fluxo_de_caixa': ['*'],
                    'despesas_anual': ['*'],
                    'faturamento_anual': ['*']
                },
                'importacao_basico': {
                    'importacoes': ['dashboard_executivo', 'dashboard_resumido'],
                    'dashboard_executivo': ['*']
                },
                'importacao_completo': {
                    'importacoes': ['*'],
                    'dashboard_executivo': ['*'],
                    'dash_importacoes_resumido': ['*'],
                    'export_relatorios': ['*'],
                    'conferencia': ['*'],
                    'agente': ['*']
                },
                'importacoes_completo': {
                    'importacoes': ['*'],
                    'dashboard_executivo': ['*'],
                    'dash_importacoes_resumido': ['*'],
                    'export_relatorios': ['*'],
                    'conferencia': ['*'],
                    'agente': ['*']
                }
            }
            
            # Check if user's profile has defined access to this module
            if user_perfil_principal in profile_page_access_map:
                profile_config = profile_page_access_map[user_perfil_principal]
                module_access = profile_config.get(modulo_codigo, [])
                
                if module_access:
                    print(f"[ACCESS_SERVICE] Specific Profile User ({user_perfil_principal}) - páginas no módulo {modulo_codigo}: {module_access}")
                    return module_access
            
            # Fallback: try to derive from user_perfis_info
            accessible_pages = set()
            
            # Create reverse mapping for original module search
            reverse_mapping = {v: k for k, v in PerfilAccessService.MODULE_MAPPING.items()}
            modulo_original = reverse_mapping.get(modulo_codigo, modulo_codigo)
            
            for perfil_info in user_perfis_info:
                perfil_nome = perfil_info.get('perfil_nome')
                if perfil_nome == user_perfil_principal:
                    modulos = perfil_info.get('modulos', [])
                    
                    for modulo in modulos:
                        # Check both original and mapped module codes
                        modulo_db = modulo.get('codigo')
                        if modulo_db == modulo_codigo or modulo_db == modulo_original:
                            modulo_paginas = modulo.get('paginas', [])
                            
                            # If empty list or contains '*', access to all pages
                            if not modulo_paginas or '*' in modulo_paginas:
                                print(f"[ACCESS_SERVICE] Perfil {perfil_nome} permite todas as páginas do módulo {modulo_codigo}")
                                return ['*']
                            
                            # Add specific pages
                            for pagina in modulo_paginas:
                                if isinstance(pagina, dict):
                                    pagina_codigo = pagina.get('codigo')
                                    if pagina_codigo:
                                        accessible_pages.add(pagina_codigo)
                                        print(f"[ACCESS_SERVICE] Adicionada página: {pagina_codigo} (perfil: {perfil_nome})")
                                else:
                                    accessible_pages.add(pagina)
                                    print(f"[ACCESS_SERVICE] Adicionada página: {pagina} (perfil: {perfil_nome})")
            
            accessible_pages = list(accessible_pages)
            print(f"[ACCESS_SERVICE] Specific Profile User ({user_perfil_principal}) - páginas acessíveis no módulo {modulo_codigo}: {accessible_pages}")
            return accessible_pages
        
        # Fallback - sem acesso
        print(f"[ACCESS_SERVICE] Sem acesso definido para role={user_role}, perfil_principal={user_perfil_principal}")
        return []
    
    @staticmethod
    def get_user_admin_capabilities():
        """
        Retorna as capacidades administrativas do usuário baseadas no perfil_principal
        
        Returns:
            dict: Dicionário com capacidades administrativas
        """
        user = session.get('user', {})
        user_role = user.get('role')
        user_perfil_principal = user.get('perfil_principal', 'basico')
        user_email = user.get('email')
        
        capabilities = {
            'can_manage_users': False,
            'can_manage_all_users': False,
            'can_manage_profiles': False,
            'can_manage_system_config': False,
            'managed_modules': [],
            'perfil_principal': user_perfil_principal,
            'admin_scope': 'none'
        }
        
        # Master Admins: admin + master_admin
        if user_role == 'admin' and user_perfil_principal == 'master_admin':
            capabilities.update({
                'can_manage_users': True,
                'can_manage_all_users': True,
                'can_manage_profiles': True,
                'can_manage_system_config': True,
                'managed_modules': ['imp', 'fin', 'exp', 'con'],  # Todos os módulos
                'admin_scope': 'system'
            })
            
        # Module Admins: interno_unique + admin_operacao/admin_financeiro
        elif user_role == 'interno_unique' and user_perfil_principal.startswith('admin_'):
            managed_modules = []
            
            if user_perfil_principal == 'admin_operacao':
                managed_modules = ['imp', 'con', 'exp']  # Operational modules
            elif user_perfil_principal == 'admin_financeiro':
                managed_modules = ['fin']
            
            capabilities.update({
                'can_manage_users': True,
                'can_manage_all_users': False,
                'can_manage_profiles': True,  # Apenas perfis do seu módulo
                'can_manage_system_config': False,
                'managed_modules': managed_modules,
                'admin_scope': 'module'
            })
        
        # Basic Users: sem capacidades administrativas
        # (capabilities já inicializadas com False)
        
        print(f"[ACCESS_SERVICE] Capacidades administrativas para {user_email}: {capabilities}")
        return capabilities
    
    @staticmethod
    def user_can_access_module(modulo_codigo):
        """
        Verifica se o usuário pode acessar um módulo específico
        
        Args:
            modulo_codigo (str): Código do módulo
            
        Returns:
            bool: True se tem acesso, False caso contrário
        """
        accessible_modules = PerfilAccessService.get_user_accessible_modules()
        
        # Verificar tanto o código fornecido quanto possível mapeamento
        can_access = modulo_codigo in accessible_modules
        
        # Se não encontrou, verificar mapeamento reverso
        if not can_access:
            # Procurar se algum módulo acessível mapeia para o código solicitado
            for module in accessible_modules:
                # Verificar se module pode ser um mapeamento para modulo_codigo
                mapped_code = PerfilAccessService.MODULE_MAPPING.get(modulo_codigo)
                if mapped_code and mapped_code == module:
                    can_access = True
                    break
                # Verificar mapeamento reverso (se modulo_codigo é o valor mapeado)
                for key, value in PerfilAccessService.MODULE_MAPPING.items():
                    if value == modulo_codigo and key in accessible_modules:
                        can_access = True
                        break
        
        print(f"[ACCESS_SERVICE] Usuário pode acessar módulo {modulo_codigo}: {can_access}")
        return can_access
    
    @staticmethod
    def user_can_access_page(modulo_codigo, pagina_codigo):
        """
        Verifica se o usuário pode acessar uma página específica
        
        Args:
            modulo_codigo (str): Código do módulo
            pagina_codigo (str): Código da página
            
        Returns:
            bool: True se tem acesso, False caso contrário
        """
        # Primeiro verificar se tem acesso ao módulo
        if not PerfilAccessService.user_can_access_module(modulo_codigo):
            print(f"[ACCESS_SERVICE] Acesso negado - sem acesso ao módulo {modulo_codigo}")
            return False
        
        # Verificar acesso à página específica
        accessible_pages = PerfilAccessService.get_user_accessible_pages(modulo_codigo)
        
        # Se tem acesso a todas as páginas
        if '*' in accessible_pages:
            print(f"[ACCESS_SERVICE] Acesso permitido - todas as páginas do módulo {modulo_codigo}")
            return True
        
        # Verificar página específica
        can_access = pagina_codigo in accessible_pages
        print(f"[ACCESS_SERVICE] Usuário pode acessar página {pagina_codigo} do módulo {modulo_codigo}: {can_access}")
        return can_access
    
    @staticmethod
    def get_filtered_menu_structure():
        """
        Retorna estrutura de menu filtrada baseada nos perfis do usuário
        
        Returns:
            dict: Estrutura de menu com apenas itens acessíveis
        """
        user = session.get('user', {})
        print(f"[ACCESS_SERVICE] Gerando menu filtrado para {user.get('email')}")
        
        # Estrutura completa do menu (definir conforme sua estrutura atual)
        complete_menu = {
            'dashboard': {
                'nome': 'Dashboard',
                'icone': 'fas fa-chart-line',
                'url': '/dashboard',
                'paginas': {
                    'importacoes': {'nome': 'Importações', 'url': '/dashboard/importacoes'},
                    'executivo': {'nome': 'Executivo', 'url': '/dashboard/executivo'}
                }
            },
            'importacoes': {
                'nome': 'Importações',
                'icone': 'fas fa-ship',
                'url': '/importacoes',
                'paginas': {
                    'lista': {'nome': 'Lista de Importações', 'url': '/importacoes'},
                    'resumo': {'nome': 'Resumo', 'url': '/importacoes/resumo'}
                }
            },
            'financeiro': {
                'nome': 'Financeiro',
                'icone': 'fas fa-dollar-sign',
                'url': '/financeiro',
                'paginas': {
                    'fluxo_caixa': {'nome': 'Fluxo de Caixa', 'url': '/financeiro/fluxo-caixa'},
                    'despesas': {'nome': 'Despesas', 'url': '/financeiro/despesas'},
                    'receitas': {'nome': 'Receitas', 'url': '/financeiro/receitas'},
                    'dashboard_executivo': {'nome': 'Dashboard Executivo', 'url': '/financeiro/dashboard'},
                    'faturamento': {'nome': 'Faturamento', 'url': '/financeiro/faturamento'}
                }
            },
            'relatorios': {
                'nome': 'Relatórios',
                'icone': 'fas fa-file-alt',
                'url': '/relatorios',
                'paginas': {
                    'exportar': {'nome': 'Exportar Relatórios', 'url': '/relatorios/exportar'},
                    'dashboard': {'nome': 'Dashboard de Relatórios', 'url': '/relatorios/dashboard'}
                }
            },
            'usuarios': {
                'nome': 'Usuários',
                'icone': 'fas fa-users',
                'url': '/usuarios',
                'paginas': {
                    'lista': {'nome': 'Lista de Usuários', 'url': '/usuarios'},
                    'perfis': {'nome': 'Perfis de Acesso', 'url': '/usuarios/perfis'}
                }
            },
            'agente': {
                'nome': 'Agente',
                'icone': 'fas fa-user-tie',
                'url': '/agente',
                'paginas': {
                    'lista': {'nome': 'Lista de Agentes', 'url': '/agente'}
                }
            },
            'conferencia': {
                'nome': 'Conferência',
                'icone': 'fas fa-check-double',
                'url': '/conferencia',
                'paginas': {
                    'documentos': {'nome': 'Documentos', 'url': '/conferencia/documentos'}
                }
            },
            'config': {
                'nome': 'Configurações',
                'icone': 'fas fa-cog',
                'url': '/config',
                'paginas': {
                    'sistema': {'nome': 'Sistema', 'url': '/config/sistema'}
                }
            }
        }
        
        # Filtrar menu baseado nos módulos acessíveis
        accessible_modules = PerfilAccessService.get_user_accessible_modules()
        filtered_menu = {}
        
        for modulo_codigo, modulo_info in complete_menu.items():
            if modulo_codigo in accessible_modules:
                # Módulo é acessível, agora filtrar páginas
                accessible_pages = PerfilAccessService.get_user_accessible_pages(modulo_codigo)
                
                filtered_modulo = {
                    'nome': modulo_info['nome'],
                    'icone': modulo_info['icone'],
                    'url': modulo_info['url'],
                    'paginas': {}
                }
                
                # Filtrar páginas do módulo
                if '*' in accessible_pages:
                    # Acesso a todas as páginas
                    filtered_modulo['paginas'] = modulo_info.get('paginas', {})
                else:
                    # Filtrar páginas específicas
                    for pagina_codigo, pagina_info in modulo_info.get('paginas', {}).items():
                        if pagina_codigo in accessible_pages:
                            filtered_modulo['paginas'][pagina_codigo] = pagina_info
                
                filtered_menu[modulo_codigo] = filtered_modulo
                print(f"[ACCESS_SERVICE] Módulo {modulo_codigo} adicionado ao menu filtrado")
        
        print(f"[ACCESS_SERVICE] Menu filtrado gerado com {len(filtered_menu)} módulos")
        return filtered_menu
