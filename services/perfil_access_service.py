"""
Serviço de Controle de Acesso baseado em Perfis
Filtra menu e páginas conforme os perfis associados ao usuário
"""

from flask import session
import json
import logging

logger = logging.getLogger(__name__)

class PerfilAccessService:
    # Mapeamento de códigos de módulos para compatibilidade
    MODULE_MAPPING = {
        'fin': 'financeiro',  # Mapear 'fin' para 'financeiro'
        'imp': 'importacoes',  # Mapear 'imp' para 'importacoes' (com S para coincidir com menu)
        'exp': 'exportacao',  # Mapear 'exp' para 'exportacao' (futuro)
        'con': 'consultoria', # Mapear 'con' para 'consultoria' (futuro)
        'rh': 'rh',  # Mapear 'rh' para 'rh' (recursos humanos)
    }
    
    # Mapeamento de códigos de páginas para endpoints/módulos
    PAGE_TO_ENDPOINT_MAPPING = {
        # Páginas do módulo Importação (imp)
        'dashboard_executivo': 'dashboard_executivo',  # Dashboard Executivo
        'dashboard_operacional': 'dashboard_operacional',  # Dashboard Operacional
        'dashboard_resumido': 'dash_importacoes_resumido',  # Dashboard Importações
        'documentos': 'conferencia',  # Conferência Documental 
        'relatorio': 'export_relatorios',  # Exportação de Relatórios
        'agente': 'agente',  # Agente UniQ
    'ajuste_status': 'ajuste_status',  # Ajuste de Status das Importações
        
        # Páginas do módulo Financeiro (fin)
        'fin_dashboard_executivo': 'fin_dashboard_executivo',  # Dashboard Executivo Financeiro
        'fluxo_caixa': 'fluxo_de_caixa',  # Fluxo de Caixa
        'despesas': 'despesas_anual',  # Despesas
        'faturamento': 'faturamento_anual',  # Faturamento
        # Novas páginas do módulo Financeiro
        'conciliacao_lancamentos': 'fin_conciliacao_lancamentos',  # Conciliação de Lançamentos
        'categorizacao_clientes': 'fin_categorizacao_clientes',  # Categorização de Clientes
        'projecoes_metas': 'fin_projecoes_metas',  # Projeções e Metas
        
        # Páginas do módulo RH (rh)
        'rh_dashboard': 'rh_dashboard',  # Dashboard Executivo RH
        'rh_colaboradores': 'rh_colaboradores',  # Gestão de Colaboradores
        'rh_estrutura_cargos': 'rh_estrutura_cargos',  # Gestão de Cargos
        'rh_estrutura_departamentos': 'rh_estrutura_departamentos',  # Gestão de Departamentos
        'rh_recrutamento': 'rh_recrutamento',  # Recrutamento e Seleção
        'rh_desempenho': 'rh_desempenho',  # Avaliações de Desempenho
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
        
        logger.debug(f"[ACCESS_SERVICE] Verificando módulos acessíveis para {user_email}")
        logger.debug(f"[ACCESS_SERVICE] Role: {user_role}, Perfil Principal: {user_perfil_principal}")
        
        # Master Admins: admin + master_admin - acesso total
        if user_role == 'admin' and user_perfil_principal == 'master_admin':
            accessible_modules = [
                'dashboard', 'importacoes', 'financeiro', 'relatorios', 
                'usuarios', 'agente', 'conferencia', 'materiais', 'config', 'rh', 'analytics', 'ajuste_status',
                'dashboard_executivo', 'dashboard_operacional', 'dash_importacoes_resumido', 'export_relatorios',
                'fin_dashboard_executivo', 'fluxo_de_caixa', 'despesas_anual', 'faturamento_anual',
                'rh_dashboard', 'rh_colaboradores', 'rh_estrutura_cargos', 'rh_estrutura_departamentos', 
                'rh_recrutamento', 'rh_desempenho',
                'analytics_portal', 'analytics_agente'  # Analytics disponíveis para todos os admins
            ]
            logger.debug(f"[ACCESS_SERVICE] Master Admin (master_admin) - módulos disponíveis: {accessible_modules}")
            return accessible_modules
        
        # Module Admins: interno_unique + admin_operacao/admin_financeiro/admin_recursos_humanos
        if user_role == 'interno_unique' and user_perfil_principal.startswith('admin_'):
            accessible_modules = set()
            
            if user_perfil_principal == 'admin_operacao':
                # Admin Operacional - módulos operacionais: Importação, Consultoria, Exportação + gestão de usuários + configurações + Analytics
                accessible_modules.update([
                    'importacoes', 'dashboard_executivo', 'dashboard_operacional', 'dash_importacoes_resumido', 
                    'export_relatorios', 'relatorios', 'conferencia', 'agente', 'ajuste_status', 'usuarios', 'config', 'analytics',
                    'analytics_portal', 'analytics_agente',  # Analytics disponíveis para todos os admins
                    # Future modules ready for implementation:
                    'consultoria', 'exportacao'
                ])
                logger.debug(f"[ACCESS_SERVICE] Module Admin (admin_operacao) - módulos disponíveis: {list(accessible_modules)}")
                
            elif user_perfil_principal == 'admin_financeiro':
                # Admin de Financeiro - APENAS módulos financeiros + gestão de usuários + Analytics
                accessible_modules.update([
                    'financeiro', 'fin_dashboard_executivo', 'fluxo_de_caixa', 
                    'despesas_anual', 'faturamento_anual', 'usuarios', 'analytics',
                    'analytics_portal', 'analytics_agente'  # Analytics disponíveis para todos os admins
                ])
                logger.debug(f"[ACCESS_SERVICE] Module Admin (admin_financeiro) - módulos disponíveis: {list(accessible_modules)}")
            
            elif user_perfil_principal == 'admin_recursos_humanos':
                # Admin de RH - APENAS módulos de RH + gestão de usuários + Analytics
                accessible_modules.update([
                    'rh', 'rh_dashboard', 'rh_colaboradores', 'rh_estrutura_cargos', 
                    'rh_estrutura_departamentos', 'rh_recrutamento', 'rh_desempenho', 'usuarios', 'analytics',
                    'analytics_portal', 'analytics_agente'  # Analytics disponíveis para todos os admins
                ])
                logger.debug(f"[ACCESS_SERVICE] Module Admin (admin_recursos_humanos) - módulos disponíveis: {list(accessible_modules)}")
            
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
                        logger.debug(f"[ACCESS_SERVICE] Adicionado módulo: {modulo_codigo} → {modulo_mapeado} (perfil: {perfil_nome})")
                        
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
                            logger.debug(f"[ACCESS_SERVICE] Adicionado módulo por página: {pagina_codigo} → {endpoint_module}")
                        
                        # Adicionar módulos gerais para compatibilidade com sidebar/menu (com contexto)
                        if pagina_codigo == 'dashboard_executivo':
                            # Dashboard Executivo é específico por módulo - só adicionar se for do módulo de importação
                            if modulo_codigo == 'imp':
                                accessible_modules.add('dashboard_executivo')
                                logger.debug(f"[ACCESS_SERVICE] Adicionado módulo geral: dashboard_executivo (contexto: importação)")
                            # Para financeiro, o dashboard executivo é interno ao submenu
                        elif pagina_codigo == 'dashboard_operacional':
                            # Dashboard Operacional é específico por módulo - só adicionar se for do módulo de importação
                            if modulo_codigo == 'imp':
                                accessible_modules.add('dashboard_operacional')
                                logger.debug(f"[ACCESS_SERVICE] Adicionado módulo geral: dashboard_operacional (contexto: importação)")
                        elif pagina_codigo == 'fin_dashboard_executivo':
                            # Dashboard Executivo Financeiro - específico do módulo financeiro
                            if modulo_codigo == 'fin':
                                accessible_modules.add('fin_dashboard_executivo')
                                logger.debug(f"[ACCESS_SERVICE] Adicionado módulo geral: fin_dashboard_executivo (contexto: financeiro)")
                        elif pagina_codigo == 'dashboard_resumido':
                            accessible_modules.add('importacoes')
                            logger.debug(f"[ACCESS_SERVICE] Adicionado módulo geral: importacoes")
                        elif pagina_codigo == 'documentos':
                            accessible_modules.add('conferencia')
                            logger.debug(f"[ACCESS_SERVICE] Adicionado módulo geral: conferencia")
                        elif pagina_codigo == 'relatorio':
                            accessible_modules.add('relatorios')  # For sidebar compatibility
                            accessible_modules.add('export_relatorios')  # For direct access
                            logger.debug(f"[ACCESS_SERVICE] Adicionado módulo geral: relatorios + export_relatorios")
                        elif pagina_codigo == 'agente':
                            accessible_modules.add('agente')
                            logger.debug(f"[ACCESS_SERVICE] Adicionado módulo geral: agente")
                        elif pagina_codigo == 'ajuste_status':
                            accessible_modules.add('ajuste_status')
                            logger.debug(f"[ACCESS_SERVICE] Adicionado módulo geral: ajuste_status")
            
            accessible_modules = list(accessible_modules)
            logger.debug(f"[ACCESS_SERVICE] Basic Users ({user_perfil_principal}) - módulos acessíveis finais: {accessible_modules}")
            return accessible_modules
        
        # Specific Profile Users: Users with specific profile names as perfil_principal
        # Handle users like Kauan with perfil_principal='financeiro_fluxo_de_caixa'
        # AND client users like Schulz with perfil_principal='operacao_importacoes_acesso_comum'
        if ((user_role == 'interno_unique' or user_role == 'cliente_unique') and 
            user_perfil_principal not in ['basico'] and not user_perfil_principal.startswith('admin_')):
            accessible_modules = set()
            
            # PRIMARY METHOD: Try to derive access from database (user_perfis_info)
            found_in_database = False
            for perfil_info in user_perfis_info:
                perfil_nome = perfil_info.get('perfil_nome')
                if perfil_nome == user_perfil_principal:
                    found_in_database = True
                    modulos = perfil_info.get('modulos', [])
                    
                    for modulo in modulos:
                        modulo_codigo = modulo.get('codigo')
                        if modulo_codigo:
                            # Apply module mapping
                            modulo_mapeado = PerfilAccessService.MODULE_MAPPING.get(modulo_codigo, modulo_codigo)
                            accessible_modules.add(modulo_mapeado)
                            logger.debug(f"[ACCESS_SERVICE] Adicionado módulo do perfis_json: {modulo_codigo} → {modulo_mapeado}")
                            
                            # Add specific page modules and sidebar compatibility
                            modulo_paginas = modulo.get('paginas', [])
                            for pagina in modulo_paginas:
                                pagina_codigo = pagina if isinstance(pagina, str) else pagina.get('codigo', '')
                                
                                if pagina_codigo in PerfilAccessService.PAGE_TO_ENDPOINT_MAPPING:
                                    endpoint_module = PerfilAccessService.PAGE_TO_ENDPOINT_MAPPING[pagina_codigo]
                                    accessible_modules.add(endpoint_module)
                                    logger.debug(f"[ACCESS_SERVICE] Adicionado módulo por página: {pagina_codigo} → {endpoint_module}")
                                
                                # Add sidebar compatibility modules with module context
                                if pagina_codigo == 'relatorio':
                                    accessible_modules.add('relatorios')  # For sidebar compatibility
                                    accessible_modules.add('export_relatorios')  # For direct access
                                    logger.debug(f"[ACCESS_SERVICE] Adicionado módulos para relatorio: relatorios + export_relatorios")
                                elif pagina_codigo == 'documentos':
                                    accessible_modules.add('conferencia')
                                elif pagina_codigo == 'agente':
                                    accessible_modules.add('agente')
                                elif pagina_codigo == 'dashboard_executivo':
                                    # Dashboard Executivo é específico por módulo - só adicionar se for do módulo de importação
                                    if modulo_codigo in ['imp', 'importacoes']:
                                        accessible_modules.add('dashboard_executivo')
                                        logger.debug(f"[ACCESS_SERVICE] Adicionado módulo geral: dashboard_executivo (contexto: importação)")
                                elif pagina_codigo == 'dashboard_operacional':
                                    # Dashboard Operacional é específico por módulo - só adicionar se for do módulo de importação
                                    if modulo_codigo in ['imp', 'importacoes']:
                                        accessible_modules.add('dashboard_operacional')
                                        logger.debug(f"[ACCESS_SERVICE] Adicionado módulo geral: dashboard_operacional (contexto: importação)")
                                elif pagina_codigo == 'dashboard_resumido':
                                    accessible_modules.add('dash_importacoes_resumido')
                                elif pagina_codigo == 'ajuste_status':
                                    accessible_modules.add('ajuste_status')
                    break
            
            if found_in_database:
                logger.debug(f"[ACCESS_SERVICE] Profile {user_perfil_principal} found in database - using dynamic access")
            else:
                # FALLBACK: Use hardcoded profile access patterns for legacy profiles
                logger.debug(f"[ACCESS_SERVICE] Profile {user_perfil_principal} not found in database - checking legacy mappings")
                profile_access_map = {
                    'financeiro_fluxo_de_caixa': {
                        'modules': ['financeiro', 'fluxo_de_caixa'],
                        'pages': ['fluxo_caixa']
                    },
                    'financeiro_completo': {
                        'modules': ['financeiro', 'fin_dashboard_executivo', 'fluxo_de_caixa', 'despesas_anual', 'faturamento_anual'],
                        'pages': ['fin_dashboard_executivo', 'fluxo_caixa', 'despesas', 'faturamento']  # Only financial pages
                    }
                    # Note: Most profiles should now be database-driven, only keep essential legacy ones
                }
                
                if user_perfil_principal in profile_access_map:
                    profile_config = profile_access_map[user_perfil_principal]
                    accessible_modules.update(profile_config['modules'])
                    logger.debug(f"[ACCESS_SERVICE] Using legacy mapping for {user_perfil_principal}: {profile_config['modules']}")
                else:
                    logger.debug(f"[ACCESS_SERVICE] No access found for profile {user_perfil_principal} - user may need profile assignment")
            
            accessible_modules = list(accessible_modules)
            logger.debug(f"[ACCESS_SERVICE] Specific Profile User ({user_role}/{user_perfil_principal}) - módulos acessíveis finais: {accessible_modules}")
            return accessible_modules
        
        # Fallback - sem acesso
        logger.debug(f"[ACCESS_SERVICE] Sem acesso definido para role={user_role}, perfil_principal={user_perfil_principal}")
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
        
        logger.debug(f"[ACCESS_SERVICE] Verificando páginas acessíveis no módulo {modulo_codigo}")
        logger.debug(f"[ACCESS_SERVICE] Role: {user_role}, Perfil Principal: {user_perfil_principal}")
        
        # Master Admins: admin + master_admin - acesso total
        if user_role == 'admin' and user_perfil_principal == 'master_admin':
            logger.debug(f"[ACCESS_SERVICE] Master Admin (master_admin) - todas as páginas disponíveis no módulo {modulo_codigo}")
            return ['*']
        
        # Module Admins: interno_unique + admin_operacao/admin_financeiro
        if user_role == 'interno_unique' and user_perfil_principal.startswith('admin_'):
            # Verificar se o usuário administra este módulo
            user_manages_module = False
            
            if user_perfil_principal == 'admin_operacao':
                # Mapear módulos operacionais: Importações, Consultoria, Exportação, Configurações, Analytics
                operational_modules = [
                    'importacoes', 'dashboard_executivo', 'dash_importacoes_resumido', 'export_relatorios', 'relatorios',
                    'conferencia', 'agente',  # Existing importacao modules
                    'ajuste_status',
                    'consultoria', 'con',  # Future consultoria modules 
                    'exportacao', 'exp',  # Future exportacao modules
                    'config',  # Configuration module for system setup
                    'analytics_portal', 'analytics_agente'  # Analytics modules - todos os admins
                ]
                user_manages_module = modulo_codigo in operational_modules
                
            elif user_perfil_principal == 'admin_financeiro':
                # Mapear módulos financeiros + Analytics
                financeiro_modules = [
                    'financeiro', 'fin_dashboard_executivo', 'fluxo_de_caixa', 
                    'despesas_anual', 'faturamento_anual',
                    'analytics_portal', 'analytics_agente'  # Analytics modules - todos os admins
                ]
                user_manages_module = modulo_codigo in financeiro_modules
            
            elif user_perfil_principal == 'admin_recursos_humanos':
                # Mapear módulos de RH + Analytics
                rh_modules = [
                    'rh', 'rh_dashboard', 'rh_colaboradores', 'rh_estrutura_cargos', 
                    'rh_estrutura_departamentos', 'rh_recrutamento', 'rh_desempenho',
                    'analytics_portal', 'analytics_agente'  # Analytics modules - todos os admins
                ]
                user_manages_module = modulo_codigo in rh_modules
            
            # Todos os Module Admins podem acessar gestão de usuários
            if modulo_codigo == 'usuarios':
                user_manages_module = True
            
            if user_manages_module:
                logger.debug(f"[ACCESS_SERVICE] Module Admin ({user_perfil_principal}) - acesso total ao módulo {modulo_codigo}")
                return ['*']
            else:
                logger.debug(f"[ACCESS_SERVICE] Module Admin ({user_perfil_principal}) - sem acesso ao módulo {modulo_codigo}")
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
                            logger.debug(f"[ACCESS_SERVICE] Perfil {perfil_nome} permite todas as páginas do módulo {modulo_codigo}")
                            return ['*']
                        
                        # Adicionar páginas específicas
                        for pagina in modulo_paginas:
                            # Se pagina é um dict, extrair o código
                            if isinstance(pagina, dict):
                                pagina_codigo = pagina.get('codigo')
                                if pagina_codigo:
                                    accessible_pages.add(pagina_codigo)
                                    logger.debug(f"[ACCESS_SERVICE] Adicionada página: {pagina_codigo} (perfil: {perfil_nome})")
                            else:
                                # Se é string, usar diretamente
                                accessible_pages.add(pagina)
                                logger.debug(f"[ACCESS_SERVICE] Adicionada página: {pagina} (perfil: {perfil_nome})")
            
            accessible_pages = list(accessible_pages)
            logger.debug(f"[ACCESS_SERVICE] Basic Users - páginas acessíveis no módulo {modulo_codigo}: {accessible_pages}")
            return accessible_pages
        
        # Specific Profile Users: Handle users with specific profile names as perfil_principal
        # Both interno_unique and cliente_unique users can have specific profiles
        if ((user_role == 'interno_unique' or user_role == 'cliente_unique') and 
            user_perfil_principal not in ['basico'] and not user_perfil_principal.startswith('admin_')):
            # PRIMARY METHOD: Try to derive from database (user_perfis_info)
            accessible_pages = set()
            
            # Create reverse mapping for original module search
            reverse_mapping = {v: k for k, v in PerfilAccessService.MODULE_MAPPING.items()}
            modulo_original = reverse_mapping.get(modulo_codigo, modulo_codigo)
            
            found_in_database = False
            for perfil_info in user_perfis_info:
                perfil_nome = perfil_info.get('perfil_nome')
                if perfil_nome == user_perfil_principal:
                    found_in_database = True
                    modulos = perfil_info.get('modulos', [])
                    
                    for modulo in modulos:
                        # Check both original and mapped module codes
                        modulo_db = modulo.get('codigo')
                        if modulo_db == modulo_codigo or modulo_db == modulo_original:
                            modulo_paginas = modulo.get('paginas', [])
                            
                            # If empty list or contains '*', access to all pages
                            if not modulo_paginas or '*' in modulo_paginas:
                                logger.debug(f"[ACCESS_SERVICE] Perfil {perfil_nome} permite todas as páginas do módulo {modulo_codigo}")
                                return ['*']
                            
                            # Add specific pages
                            for pagina in modulo_paginas:
                                if isinstance(pagina, dict):
                                    pagina_codigo = pagina.get('codigo')
                                    if pagina_codigo:
                                        accessible_pages.add(pagina_codigo)
                                        logger.debug(f"[ACCESS_SERVICE] Adicionada página: {pagina_codigo} (perfil: {perfil_nome})")
                                else:
                                    accessible_pages.add(pagina)
                                    logger.debug(f"[ACCESS_SERVICE] Adicionada página: {pagina} (perfil: {perfil_nome})")
                    break
            
            if found_in_database:
                accessible_pages = list(accessible_pages)
                logger.debug(f"[ACCESS_SERVICE] Database-driven access for {user_role}/{user_perfil_principal} in {modulo_codigo}: {accessible_pages}")
                return accessible_pages
            else:
                # FALLBACK: Use hardcoded mappings for legacy profiles only
                logger.debug(f"[ACCESS_SERVICE] Profile {user_perfil_principal} not found in database - checking legacy page mappings")
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
                    }
                    # Note: Most profiles should now be database-driven
                }
                
                if user_perfil_principal in profile_page_access_map:
                    profile_config = profile_page_access_map[user_perfil_principal]
                    module_access = profile_config.get(modulo_codigo, [])
                    
                    if module_access:
                        logger.debug(f"[ACCESS_SERVICE] Legacy mapping for {user_perfil_principal} in {modulo_codigo}: {module_access}")
                        return module_access
                
                logger.debug(f"[ACCESS_SERVICE] No page access found for profile {user_perfil_principal} in module {modulo_codigo}")
                return []
        
        # Fallback - sem acesso
        logger.debug(f"[ACCESS_SERVICE] Sem acesso definido para role={user_role}, perfil_principal={user_perfil_principal}")
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
        
        logger.debug(f"[ACCESS_SERVICE] Capacidades administrativas para {user_email}: {capabilities}")
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
        
        logger.debug(f"[ACCESS_SERVICE] Usuário pode acessar módulo {modulo_codigo}: {can_access}")
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
            logger.debug(f"[ACCESS_SERVICE] Acesso negado - sem acesso ao módulo {modulo_codigo}")
            return False
        
        # Verificar acesso à página específica
        accessible_pages = PerfilAccessService.get_user_accessible_pages(modulo_codigo)
        
        # Se tem acesso a todas as páginas
        if '*' in accessible_pages:
            logger.debug(f"[ACCESS_SERVICE] Acesso permitido - todas as páginas do módulo {modulo_codigo}")
            return True
        
        # Verificar página específica
        can_access = pagina_codigo in accessible_pages
        logger.debug(f"[ACCESS_SERVICE] Usuário pode acessar página {pagina_codigo} do módulo {modulo_codigo}: {can_access}")
        return can_access
    
    @staticmethod
    def get_filtered_menu_structure():
        """
        Retorna estrutura de menu filtrada baseada nos perfis do usuário
        
        Returns:
            dict: Estrutura de menu com apenas itens acessíveis
        """
        user = session.get('user', {})
        logger.debug(f"[ACCESS_SERVICE] Gerando menu filtrado para {user.get('email')}")
        
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
            },
            'rh': {
                'nome': 'Recursos Humanos',
                'icone': 'fas fa-users',
                'url': '/rh/colaboradores',
                'paginas': {
                    'dashboard': {'nome': 'Dashboard Executivo', 'url': '/rh/dashboard'},
                    'colaboradores': {'nome': 'Gestão de Colaboradores', 'url': '/rh/colaboradores'},
                    'estrutura_cargos': {'nome': 'Gestão de Cargos', 'url': '/rh/estrutura/cargos'},
                    'estrutura_departamentos': {'nome': 'Gestão de Departamentos', 'url': '/rh/estrutura/departamentos'},
                    'recrutamento': {'nome': 'Recrutamento', 'url': '/rh/recrutamento'},
                    'desempenho': {'nome': 'Avaliações', 'url': '/rh/desempenho'}
                }
            },
            'analytics': {
                'nome': 'Analytics',
                'icone': 'fas fa-chart-bar',
                'url': '/analytics',
                'paginas': {
                    'portal': {'nome': 'Analytics do Portal', 'url': '/analytics'},
                    'agente': {'nome': 'Analytics do Agente', 'url': '/analytics/agente'}
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
                logger.debug(f"[ACCESS_SERVICE] Módulo {modulo_codigo} adicionado ao menu filtrado")
        
        logger.debug(f"[ACCESS_SERVICE] Menu filtrado gerado com {len(filtered_menu)} módulos")
        return filtered_menu
