"""
Módulo Analytics - Dashboard de estatísticas de acesso
"""

from flask import Blueprint

# Criar o blueprint do Analytics
analytics_bp = Blueprint('analytics', __name__, 
                        url_prefix='/usuarios/analytics',
                        static_folder='static',
                        template_folder='templates')

# Importar as rotas
from .routes import bp

# Registrar as rotas no blueprint principal
analytics_bp.register_blueprint(bp, url_prefix='')

__all__ = ['analytics_bp']
