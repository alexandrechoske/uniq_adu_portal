"""
Rotas principais do módulo Financeiro

Este arquivo consolida todos os blueprints dos submódulos financeiros
e exporta o blueprint principal para registro no app.py
"""

from flask import Blueprint

# Importar todos os blueprints dos submódulos
from .dashboard_executivo.routes import dashboard_executivo_financeiro_bp
from .fluxo_de_caixa.routes import fluxo_de_caixa_bp
from .despesas.routes import despesas_bp
from .faturamento.routes import faturamento_bp

# Criar blueprint principal do módulo financeiro
financeiro_bp = Blueprint('financeiro', __name__, url_prefix='/financeiro')

# Lista de todos os blueprints do módulo financeiro
FINANCEIRO_BLUEPRINTS = [
    dashboard_executivo_financeiro_bp,
    fluxo_de_caixa_bp,
    despesas_bp,
    faturamento_bp
]

def register_financeiro_blueprints(app):
    """
    Registra todos os blueprints do módulo financeiro na aplicação
    
    Args:
        app: Instância da aplicação Flask
    """
    for bp in FINANCEIRO_BLUEPRINTS:
        app.register_blueprint(bp)
