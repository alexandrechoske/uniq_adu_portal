from flask import Blueprint, render_template, session, jsonify
from modules.auth.routes import login_required

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
def index():
    """Dashboard Executivo Financeiro - Visão estratégica das finanças"""
    user = session.get('user', {})
    user_role = user.get('role', '')
    
    # Verificar permissões - apenas admin e interno_unique
    if user_role not in ['admin', 'interno_unique']:
        return render_template('errors/403.html'), 403
    
    return render_template('dashboard_executivo_financeiro.html')

@dashboard_executivo_financeiro_bp.route('/api/dados-financeiros')
@login_required
def api_dados_financeiros():
    """API para dados do dashboard executivo financeiro"""
    user = session.get('user', {})
    user_role = user.get('role', '')
    
    # Verificar permissões
    if user_role not in ['admin', 'interno_unique']:
        return jsonify({'error': 'Acesso negado'}), 403
    
    # TODO: Implementar lógica de dados financeiros
    dados_mock = {
        'receita_total': 150000.00,
        'despesas_total': 120000.00,
        'lucro_liquido': 30000.00,
        'margem_lucro': 20.0
    }
    
    return jsonify(dados_mock)