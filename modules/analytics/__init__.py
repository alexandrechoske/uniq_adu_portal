"""
Módulo Analytics - Sistema de análise de logs de acesso
"""
from flask import Blueprint
import os

# Criar blueprint do módulo analytics
analytics_bp = Blueprint(
    'analytics',
    __name__,
    url_prefix='/usuarios/analytics',
    template_folder='templates',
    static_folder='static'
)

# Registrar rotas sem importação circular
from .routes import register_routes
register_routes(analytics_bp)

__all__ = ['analytics_bp']
