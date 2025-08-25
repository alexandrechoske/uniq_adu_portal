"""
Sistema de Navegação Contextual
Detecta o módulo atual e gera a sidebar apropriada
"""

def get_module_context(request_endpoint):
    """
    Detecta o módulo macro baseado no endpoint da requisição
    """
    if not request_endpoint:
        return 'menu'
    
    # Módulo Financeiro - todos os blueprints financeiros
    if any(x in request_endpoint for x in [
        'dashboard_executivo_financeiro', 'fin_dashboard_executivo', 'faturamento_anual', 'despesas_anual',
        'resultado_anual', 'metas_financeiras', 'fluxo_de_caixa',
        'financeiro.'  # Para URLs que começam com financeiro.
    ]):
        return 'financeiro'
    
    # Módulo Importações
    if any(x in request_endpoint for x in [
        'dashboard_executivo', 'dash_importacoes_resumido', 'export_relatorios',
        'conferencia', 'materiais', 'importacoes.'
    ]):
        return 'importacoes'
    
    # Sistema/Administração
    if any(x in request_endpoint for x in [
        'usuarios', 'config', 'analytics', 'debug'
    ]):
        return 'sistema'
    
    # Menu principal ou outros
    return 'menu'

def get_sidebar_navigation(current_module, user_role='guest'):
    """
    Gera a estrutura de navegação da sidebar baseada no módulo atual
    """
    
    # Navegação do Menu Principal
    if current_module == 'menu':
        return {
            'module_title': 'Portal UniSystem',
            'items': [
                {
                    'title': 'Menu Principal',
                    'icon': 'mdi-home',
                    'url': 'menu.menu_home',
                    'active_endpoints': ['menu.menu_home']
                },
                {
                    'title': 'Importações',
                    'icon': 'mdi-ferry',
                    'url': 'dashboard_executivo.index',
                    'description': 'Módulo de Importações'
                },
                {
                    'title': 'Financeiro',
                    'icon': 'mdi-finance',
                    'url': 'fin_dashboard_executivo.index',
                    'description': 'Módulo Financeiro',
                    'roles': ['admin', 'interno_unique']
                },
                {
                    'title': 'Agente IA',
                    'icon': 'mdi-robot',
                    'url': 'agente.index',
                    'active_endpoints': ['agente.index']
                }
            ]
        }
    
    # Navegação do Módulo Importações
    elif current_module == 'importacoes':
        return {
            'module_title': 'Importações',
            'items': [
                {
                    'title': 'Voltar ao Menu',
                    'icon': 'mdi-arrow-left',
                    'url': 'menu.menu_home',
                    'is_back': True
                },
                {
                    'title': 'Dashboard Executivo',
                    'icon': 'mdi-view-dashboard',
                    'url': 'dashboard_executivo.index',
                    'active_endpoints': ['dashboard_executivo.index']
                },
                {
                    'title': 'Dashboard Importações',
                    'icon': 'mdi-ferry',
                    'url': 'dash_importacoes_resumido.dashboard',
                    'active_endpoints': ['dash_importacoes_resumido.dashboard']
                },
                {
                    'title': 'Exportação',
                    'icon': 'mdi-file-export',
                    'url': 'export_relatorios.index',
                    'active_endpoints': ['export_relatorios.index']
                },
                {
                    'title': 'Conferência Documental',
                    'icon': 'mdi-file-check',
                    'url': 'conferencia.index',
                    'active_endpoints': ['conferencia.index'],
                    'roles': ['admin', 'interno_unique']
                }
            ]
        }
    
    # Navegação do Módulo Financeiro
    elif current_module == 'financeiro':
        return {
            'module_title': 'Financeiro',
            'items': [
                {
                    'title': 'Voltar ao Menu',
                    'icon': 'mdi-arrow-left',
                    'url': 'menu.menu_home',
                    'is_back': True
                },
                {
                    'title': 'Dashboard Executivo',
                    'icon': 'mdi-view-dashboard',
                    'url': 'fin_dashboard_executivo.index',
                    'active_endpoints': ['fin_dashboard_executivo.index']
                },
                {
                    'title': 'Faturamento Anual',
                    'icon': 'mdi-currency-usd',
                    'url': 'faturamento_anual.index',
                    'active_endpoints': ['faturamento_anual.index']
                },
                {
                    'title': 'Despesas Anuais',
                    'icon': 'mdi-credit-card',
                    'url': 'despesas_anual.index',
                    'active_endpoints': ['despesas_anual.index']
                },
                {
                    'title': 'Resultado Anual (DRE)',
                    'icon': 'mdi-chart-line',
                    'url': 'resultado_anual.index',
                    'active_endpoints': ['resultado_anual.index']
                },
                {
                    'title': 'Metas Financeiras',
                    'icon': 'mdi-target',
                    'url': 'metas_financeiras.index',
                    'active_endpoints': ['metas_financeiras.index']
                },
                {
                    'title': 'Fluxo de Caixa',
                    'icon': 'mdi-cash-flow',
                    'url': 'fluxo_de_caixa.index',
                    'active_endpoints': ['fluxo_de_caixa.index']
                }
            ]
        }
    
    # Navegação do Sistema/Administração
    elif current_module == 'sistema':
        admin_items = [
            {
                'title': 'Voltar ao Menu',
                'icon': 'mdi-arrow-left',
                'url': 'menu.menu_home',
                'is_back': True
            },
            {
                'title': 'Usuários',
                'icon': 'mdi-account-group',
                'url': 'usuarios.index',
                'active_endpoints': ['usuarios.index'],
                'roles': ['admin']
            },
            {
                'title': 'Logos Clientes',
                'icon': 'mdi-domain',
                'url': 'config.logos_clientes',
                'active_endpoints': ['config.logos_clientes'],
                'roles': ['admin']
            },
            {
                'title': 'Analytics',
                'icon': 'mdi-chart-line',
                'url': 'analytics.analytics_dashboard',
                'active_endpoints': ['analytics.analytics_dashboard', 'analytics.analytics_agente'],
                'roles': ['admin'],
                'submenu': [
                    {
                        'title': 'Portal',
                        'icon': 'mdi-chart-bar',
                        'url': 'analytics.analytics_dashboard'
                    },
                    {
                        'title': 'Agente',
                        'icon': 'mdi-robot',
                        'url': 'analytics.analytics_agente'
                    }
                ]
            }
        ]
        
        return {
            'module_title': 'Sistema',
            'items': admin_items
        }
    
    # Fallback para menu padrão
    return {
        'module_title': 'Portal UniSystem',
        'items': []
    }
