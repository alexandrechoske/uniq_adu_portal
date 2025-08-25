from flask import Blueprint, render_template, session, jsonify
from modules.auth.routes import login_required
from decorators.perfil_decorators import perfil_required

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
@perfil_required('financeiro', 'faturamento')
def index():
    """Faturamento Anual - Controle de receitas"""
    return render_template('faturamento.html')

@faturamento_bp.route('/api/dados-faturamento')
@login_required
@perfil_required('financeiro', 'faturamento')
def api_dados_faturamento():
    """API para dados de faturamento"""
    # TODO: Implementar lógica de faturamento
    dados_mock = {
        'faturamento_servicos': 120000.00,
        'faturamento_consultoria': 30000.00,
        'faturamento_total': 150000.00,
        'crescimento_mensal': 5.2
    }
    
    return jsonify(dados_mock)