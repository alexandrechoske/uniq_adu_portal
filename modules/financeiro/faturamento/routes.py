from flask import Blueprint, render_template, session, jsonify
from modules.auth.routes import login_required

# Blueprint para Faturamento
faturamento_bp = Blueprint(
    'fin_faturamento', 
    __name__,
    url_prefix='/financeiro/faturamento',
    template_folder='templates',
    static_folder='static',
    static_url_path='/financeiro/faturamento/static'
)

@faturamento_bp.route('/')
@login_required
def index():
    """Faturamento Anual - Controle de receitas"""
    user = session.get('user', {})
    user_role = user.get('role', '')
    
    # Verificar permissões - apenas admin e interno_unique
    if user_role not in ['admin', 'interno_unique']:
        return render_template('errors/403.html'), 403
    
    return render_template('faturamento.html')

@faturamento_bp.route('/api/dados-faturamento')
@login_required
def api_dados_faturamento():
    """API para dados de faturamento"""
    user = session.get('user', {})
    user_role = user.get('role', '')
    
    # Verificar permissões
    if user_role not in ['admin', 'interno_unique']:
        return jsonify({'error': 'Acesso negado'}), 403
    
    # TODO: Implementar lógica de faturamento
    dados_mock = {
        'faturamento_servicos': 120000.00,
        'faturamento_consultoria': 30000.00,
        'faturamento_total': 150000.00,
        'crescimento_mensal': 5.2
    }
    
    return jsonify(dados_mock)