"""
Helper para aplicar cores específicas por módulo

Este arquivo contém funções para identificar módulos e aplicar cores correspondentes
conforme as diretrizes da Unique Aduaneira
"""

from markupsafe import Markup
from flask import request

def get_module_color_class(current_route=None, module_name=None):
    """
    Determinar a classe CSS de cor baseada no módulo atual
    
    Args:
        current_route (str): Rota atual da requisição
        module_name (str): Nome do módulo (se fornecido diretamente)
    
    Returns:
        dict: Dicionário com classes CSS para cabeçalho, botões, etc.
    """
    
    # Mapeamento de rotas/módulos para cores
    module_mapping = {
        # Módulo Importações - Azul
        'importacoes': {
            'header_class': 'module-header-importacoes',
            'btn_class': 'btn-unique-importacoes', 
            'text_class': 'unique-text-importacoes',
            'bg_class': 'unique-bg-importacoes',
            'border_class': 'unique-border-importacoes',
            'color': '#2d6b92'
        },
        
        # Módulo Financeiro - Laranja  
        'financeiro': {
            'header_class': 'module-header-financeiro',
            'btn_class': 'btn-unique-financeiro',
            'text_class': 'unique-text-financeiro', 
            'bg_class': 'unique-bg-financeiro',
            'border_class': 'unique-border-financeiro',
            'color': '#e67e22'
        },
        
        # Dashboard Executivo - Azul principal
        'dashboard_executivo': {
            'header_class': 'module-header-importacoes',
            'btn_class': 'btn-unique-primary',
            'text_class': 'unique-text-primary',
            'bg_class': 'unique-bg-primary', 
            'border_class': 'unique-border-primary',
            'color': '#2d6b92'
        },
        
        # Outros módulos - Cor padrão
        'default': {
            'header_class': 'module-header-generic',
            'btn_class': 'btn-unique-primary',
            'text_class': 'unique-text-primary',
            'bg_class': 'unique-bg-primary',
            'border_class': 'unique-border-primary', 
            'color': '#2d6b92'
        }
    }
    
    # Determinar módulo atual
    detected_module = 'default'
    
    # Tentar detectar pela URL atual se não foi fornecido explicitamente
    if not module_name and not current_route:
        try:
            current_route = request.path
        except:
            current_route = None
    
    if module_name:
        detected_module = module_name.lower()
    elif current_route:
        route_lower = current_route.lower()
        
        # Verificar rotas específicas
        if '/financeiro/' in route_lower or 'financeiro' in route_lower:
            detected_module = 'financeiro'
        elif any(keyword in route_lower for keyword in ['importac', 'import', 'dashboard-exec']):
            detected_module = 'importacoes'
        elif 'dashboard' in route_lower and 'exec' in route_lower:
            detected_module = 'dashboard_executivo'
    
    # Retornar configuração do módulo ou padrão
    return module_mapping.get(detected_module, module_mapping['default'])

def get_breadcrumb_with_module_colors(breadcrumb_items, module_name=None):
    """
    Gerar breadcrumb HTML com cores específicas do módulo
    
    Args:
        breadcrumb_items (list): Lista de itens do breadcrumb
        module_name (str): Nome do módulo
    
    Returns:
        str: HTML do breadcrumb com classes de cor aplicadas
    """
    
    breadcrumb_html = '<nav aria-label="breadcrumb">'
    breadcrumb_html += '<ol class="breadcrumb mb-0">'
    
    for i, item in enumerate(breadcrumb_items):
        is_last = i == len(breadcrumb_items) - 1
        
        if is_last:
            breadcrumb_html += f'<li class="breadcrumb-item active" aria-current="page" style="color: black !important;">'
            breadcrumb_html += f'<i class="{item.get("icon", "mdi mdi-circle-small")}" style="color: black !important;"></i> {item["name"]}'
            breadcrumb_html += '</li>'
        else:
            breadcrumb_html += f'<li class="breadcrumb-item">'
            if item.get('url'):
                breadcrumb_html += f'<a href="{item["url"]}" style="color: black !important;">'
                breadcrumb_html += f'<i class="{item.get("icon", "mdi mdi-circle-small")}" style="color: black !important;"></i> {item["name"]}'
                breadcrumb_html += '</a>'
            else:
                breadcrumb_html += f'<span style="color: black !important;">'
                breadcrumb_html += f'<i class="{item.get("icon", "mdi mdi-circle-small")}" style="color: black !important;"></i> {item["name"]}'
                breadcrumb_html += '</span>'
            breadcrumb_html += '</li>'
    
    breadcrumb_html += '</ol>'
    breadcrumb_html += '</nav>'
    
    return Markup(breadcrumb_html)

# Função para usar em templates Jinja2
def register_module_color_helpers(app):
    """
    Registrar funções helper no contexto do Jinja2
    """
    
    @app.context_processor
    def inject_module_helpers():
        return {
            'get_module_color_class': get_module_color_class,
            'get_breadcrumb_with_module_colors': get_breadcrumb_with_module_colors
        }

# Exemplos de uso em templates:
"""
<!-- Cabeçalho com cor do módulo -->
{% set module_config = get_module_color_class(module_name='importacoes') %}
<div class="{{ module_config.header_class }}">
    <h1>Módulo de Importações</h1>
</div>

<!-- Botão com cor do módulo -->
<button class="{{ module_config.btn_class }}">
    Ação do Módulo
</button>

<!-- Breadcrumb com cores -->
{{ get_breadcrumb_with_module_colors([
    {'name': 'Importações', 'icon': 'mdi mdi-ship-wheel'},
    {'name': 'Dashboard', 'icon': 'mdi mdi-chart-line'}
], 'importacoes') | safe }}
"""
