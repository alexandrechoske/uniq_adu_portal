"""
Módulo Dashboard Executivo - RH
Dashboard com visão executiva de indicadores e métricas de Recursos Humanos
"""

from flask import Blueprint

# Criar blueprint
dashboard_rh_bp = Blueprint(
    'dashboard_rh',
    __name__,
    template_folder='templates',
    static_folder='static',
    url_prefix='/rh/dashboard'
)

# Importar rotas
from . import routes
