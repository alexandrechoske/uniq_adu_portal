from flask import Blueprint, render_template, session, jsonify, request
from extensions import supabase, supabase_admin
from routes.auth import login_required, role_required
from decorators.perfil_decorators import perfil_required
from services.access_logger import access_logger
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import json
from collections import defaultdict

# Blueprint para Conciliação de Lançamentos
conciliacao_lancamentos_bp = Blueprint(
    'fin_conciliacao_lancamentos', 
    __name__,
    url_prefix='/financeiro/conciliacao-lancamentos',
    template_folder='templates',
    static_folder='static',
    static_url_path='/financeiro/conciliacao/static'
)

@conciliacao_lancamentos_bp.route('/')
@login_required
@perfil_required('financeiro', 'conciliacao_lancamentos')
def index():
    """Conciliação de Lançamentos - Controle de conciliação bancária"""
    try:
        # Log de acesso
        access_logger.log_page_access('Conciliação de Lançamentos', 'financeiro')
        
        # Buscar dados iniciais se necessário
        user = session.get('user', {})
        print(f"[CONCILIACAO] Usuário {user.get('email')} acessou Conciliação de Lançamentos")
        
        return render_template('conciliacao_lancamentos/conciliacao_lancamentos.html')
        
    except Exception as e:
        print(f"[CONCILIACAO] Erro ao carregar página: {str(e)}")
        return jsonify({'error': 'Erro interno do servidor'}), 500

@conciliacao_lancamentos_bp.route('/api/dados-conciliacao')
@login_required
@perfil_required('financeiro', 'conciliacao_lancamentos')
def api_dados_conciliacao():
    """API para obter dados de conciliação"""
    try:
        # Obter parâmetros de período
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        conta_bancaria = request.args.get('conta_bancaria')
        
        print(f"[CONCILIACAO_API] Buscando dados - Período: {data_inicio} a {data_fim}")
        
        # TODO: Implementar lógica de busca dos dados de conciliação
        # Por enquanto retornando dados mockados
        dados_mock = {
            'lancamentos_pendentes': [
                {
                    'id': 1,
                    'data': '2024-01-15',
                    'descricao': 'Pagamento Fornecedor XYZ',
                    'valor': -1500.00,
                    'status': 'pendente',
                    'tipo': 'despesa'
                }
            ],
            'extrato_bancario': [
                {
                    'id': 1,
                    'data': '2024-01-15',
                    'descricao': 'TED ENVIADA',
                    'valor': -1500.00,
                    'status': 'nao_conciliado'
                }
            ],
            'resumo': {
                'total_pendentes': 1,
                'valor_pendente': -1500.00,
                'total_conciliados': 0,
                'diferenca': -1500.00
            }
        }
        
        return jsonify({
            'success': True,
            'data': dados_mock
        })
        
    except Exception as e:
        print(f"[CONCILIACAO_API] Erro na API: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Erro ao buscar dados de conciliação'
        }), 500

@conciliacao_lancamentos_bp.route('/api/conciliar', methods=['POST'])
@login_required
@perfil_required('financeiro', 'conciliacao_lancamentos')
def api_conciliar():
    """API para realizar conciliação de lançamentos"""
    try:
        dados = request.get_json()
        lancamento_id = dados.get('lancamento_id')
        extrato_id = dados.get('extrato_id')
        
        print(f"[CONCILIACAO_API] Conciliando lançamento {lancamento_id} com extrato {extrato_id}")
        
        # TODO: Implementar lógica de conciliação
        # Por enquanto apenas confirmando
        
        return jsonify({
            'success': True,
            'message': 'Conciliação realizada com sucesso'
        })
        
    except Exception as e:
        print(f"[CONCILIACAO_API] Erro na conciliação: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Erro ao realizar conciliação'
        }), 500
