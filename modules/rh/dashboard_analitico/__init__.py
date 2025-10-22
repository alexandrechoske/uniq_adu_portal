"""
Módulo Dashboard Analítico - RH
Dashboard com análises detalhadas e métricas analíticas de Recursos Humanos
"""

from flask import Blueprint

# Criar blueprint
dashboard_analitico_rh_bp = Blueprint(
    'dashboard_analitico_rh',
    __name__,
    template_folder='templates',
    static_folder='static',
    url_prefix='/rh/dashboard-analitico'
)

# Importar rotas
from . import routes
