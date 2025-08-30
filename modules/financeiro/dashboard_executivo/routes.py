from flask import Blueprint, render_template, session, jsonify
from modules.auth.routes import login_required
from decorators.perfil_decorators import perfil_required

# Blueprint para Dashboard Executivo Financeiro
dashboard_executivo_financeiro_bp = Blueprint(
    'fin_dashboard_executivo', 
    __name__,
    url_prefix='/financeiro/dashboard-executivo',
    template_folder='templates',
    static_folder='static',
    static_url_path='/financeiro/dashboard-executivo/static'
)

@dashboard_executivo_financeiro_bp.route('/')
@login_required
@perfil_required('financeiro', 'fin_dashboard_executivo')
def index():
    """Dashboard Executivo Financeiro - Visão estratégica das finanças"""
    return render_template('dashboard_executivo_financeiro.html')

@dashboard_executivo_financeiro_bp.route('/api/dados-financeiros')
@login_required
@perfil_required('financeiro', 'fin_dashboard_executivo')
def api_dados_financeiros():
    """API para dados do dashboard executivo financeiro"""
    # TODO: Implementar lógica de dados financeiros
    dados_mock = {
        'receita_total': 150000.00,
        'despesas_total': 120000.00,
        'lucro_liquido': 30000.00,
        'margem_lucro': 20.0
    }
    
    return jsonify(dados_mock)