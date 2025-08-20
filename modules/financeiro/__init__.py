"""
Módulo Financeiro - UniSystem Portal

Este módulo contém todas as funcionalidades financeiras do sistema:
- Dashboard Executivo Financeiro
- Fluxo de Caixa
- Controle de Despesas
- Faturamento

Cada submódulo possui suas próprias rotas, templates e arquivos estáticos.
"""

from flask import Blueprint

# Criar blueprint principal do módulo financeiro
financeiro_bp = Blueprint('financeiro', __name__, url_prefix='/financeiro')
