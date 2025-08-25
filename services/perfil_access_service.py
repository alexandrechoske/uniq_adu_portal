"""
Serviço de Controle de Acesso baseado em Perfis
Filtra menu e páginas conforme os perfis associados ao usuário
"""

from flask import session
import json

class PerfilAccessService:
    
    @staticmethod
    def get_user_accessible_modules():
        """
        Retorna lista de módulos que o usuário tem acesso baseado em seus perfis
        
        Returns:
            list: Lista de códigos de módulos acessíveis
        """
        user = session.get('user', {})
        user_role = user.get('role')
        user_perfis_info = user.get('user_perfis_info', [])
        
        print(f"[ACCESS_SERVICE] Verificando módulos acessíveis para {user.get('email')}")
        
        # Admin tem acesso a tudo
        if user_role == 'admin':
            accessible_modules = [
                'dashboard', 'importacoes', 'fin', 'relatorios', 
                'usuarios', 'agente', 'conferencia', 'materiais', 'config'
            ]
            print(f"[ACCESS_SERVICE] Admin - módulos disponíveis: {accessible_modules}")
            return accessible_modules
        
        # Usuários com perfis específicos
        accessible_modules = set()
        
        for perfil_info in user_perfis_info:
            perfil_nome = perfil_info.get('perfil_nome')
            modulos = perfil_info.get('modulos', [])
            
            for modulo in modulos:
                modulo_codigo = modulo.get('codigo')
                if modulo_codigo:
                    accessible_modules.add(modulo_codigo)
                    print(f"[ACCESS_SERVICE] Adicionado módulo: {modulo_codigo} (perfil: {perfil_nome})")
        
        accessible_modules = list(accessible_modules)
        print(f"[ACCESS_SERVICE] Módulos acessíveis finais: {accessible_modules}")
        return accessible_modules
    
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
        user_perfis_info = user.get('user_perfis_info', [])
        
        print(f"[ACCESS_SERVICE] Verificando páginas acessíveis no módulo {modulo_codigo}")
        
        # Admin tem acesso a tudo
        if user_role == 'admin':
            print(f"[ACCESS_SERVICE] Admin - todas as páginas disponíveis no módulo {modulo_codigo}")
            return ['*']
        
        # Verificar nos perfis do usuário
        accessible_pages = set()
        
        for perfil_info in user_perfis_info:
            perfil_nome = perfil_info.get('perfil_nome')
            modulos = perfil_info.get('modulos', [])
            
            for modulo in modulos:
                if modulo.get('codigo') == modulo_codigo:
                    modulo_paginas = modulo.get('paginas', [])
                    
                    # Se lista vazia ou contém '*', acesso a todas as páginas
                    if not modulo_paginas or '*' in modulo_paginas:
                        print(f"[ACCESS_SERVICE] Perfil {perfil_nome} permite todas as páginas do módulo {modulo_codigo}")
                        return ['*']
                    
                    # Adicionar páginas específicas
                    for pagina in modulo_paginas:
                        accessible_pages.add(pagina)
                        print(f"[ACCESS_SERVICE] Adicionada página: {pagina} (perfil: {perfil_nome})")
        
        accessible_pages = list(accessible_pages)
        print(f"[ACCESS_SERVICE] Páginas acessíveis no módulo {modulo_codigo}: {accessible_pages}")
        return accessible_pages
    
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
        can_access = modulo_codigo in accessible_modules
        
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
            'fin': {
                'nome': 'Financeiro',
                'icone': 'fas fa-dollar-sign',
                'url': '/financeiro',
                'paginas': {
                    'fluxo_caixa': {'nome': 'Fluxo de Caixa', 'url': '/financeiro/fluxo-caixa'},
                    'despesas': {'nome': 'Despesas', 'url': '/financeiro/despesas'},
                    'receitas': {'nome': 'Receitas', 'url': '/financeiro/receitas'}
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
