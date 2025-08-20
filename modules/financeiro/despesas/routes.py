from flask import Blueprint, render_template, session, jsonify
from modules.auth.routes import login_required

# Blueprint para Despesas
despesas_bp = Blueprint(
    'fin_despesas', 
    __name__,
    url_prefix='/financeiro/despesas',
    template_folder='templates',
    static_folder='static',
    static_url_path='/financeiro/despesas/static'
)

@despesas_bp.route('/')
@login_required
def index():
    """Despesas Anuais - Controle de gastos"""
    user = session.get('user', {})
    user_role = user.get('role', '')
    
    # Verificar permissões - apenas admin e interno_unique
    if user_role not in ['admin', 'interno_unique']:
        return render_template('errors/403.html'), 403
    
    return render_template('despesas.html')

@despesas_bp.route('/api/dados-despesas')
@login_required
def api_dados_despesas():
    """API para dados de despesas"""
    user = session.get('user', {})
    user_role = user.get('role', '')
    
    # Verificar permissões
    if user_role not in ['admin', 'interno_unique']:
        return jsonify({'error': 'Acesso negado'}), 403
    
    # TODO: Implementar lógica de despesas
    dados_mock = {
        'despesas_operacionais': 80000.00,
        'despesas_administrativas': 25000.00,
        'despesas_financeiras': 15000.00,
        'total_despesas': 120000.00
    }
    
    return jsonify(dados_mock)