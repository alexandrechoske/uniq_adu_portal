"""
Módulo de Internacionalização (i18n)
Sistema de tradução PT-BR / EN-US para o portal
"""

from flask import Blueprint

i18n_bp = Blueprint('i18n', __name__, url_prefix='/i18n')

from . import routes
