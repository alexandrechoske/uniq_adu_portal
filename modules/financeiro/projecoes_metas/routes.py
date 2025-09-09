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

# Blueprint para Projeções e Metas
projecoes_metas_bp = Blueprint(
    'fin_projecoes_metas', 
    __name__,
    url_prefix='/financeiro/projecoes-metas',
    template_folder='templates',
    static_folder='static',
    static_url_path='/financeiro/projecoes/static'
)

@projecoes_metas_bp.route('/')
@login_required
@perfil_required('financeiro', 'projecoes_metas')
def index():
    """Projeções e Metas - Planejamento e controle de metas financeiras"""
    try:
        # Log de acesso
        access_logger.log_page_access('Projeções e Metas', 'financeiro')
        
        # Buscar dados iniciais se necessário
        user = session.get('user', {})
        print(f"[PROJECOES] Usuário {user.get('email')} acessou Projeções e Metas")
        
        return render_template('projecoes_metas/projecoes_metas.html')
        
    except Exception as e:
        print(f"[PROJECOES] Erro ao carregar página: {str(e)}")
        return jsonify({'error': 'Erro interno do servidor'}), 500

@projecoes_metas_bp.route('/api/metas')
@login_required
@perfil_required('financeiro', 'projecoes_metas')
def api_metas():
    """API para obter metas financeiras"""
    try:
        # Obter parâmetros de período
        ano = request.args.get('ano', datetime.now().year)
        categoria = request.args.get('categoria')
        
        print(f"[PROJECOES_API] Buscando metas - Ano: {ano}, Categoria: {categoria}")
        
        # TODO: Implementar lógica de busca de metas
        # Por enquanto retornando dados mockados
        metas_mock = [
            {
                'id': 1,
                'nome': 'Receita Anual 2024',
                'categoria': 'receita',
                'valor_meta': 1200000.00,
                'valor_realizado': 800000.00,
                'periodo_inicio': '2024-01-01',
                'periodo_fim': '2024-12-31',
                'status': 'em_andamento',
                'percentual_atingido': 66.67
            },
            {
                'id': 2,
                'nome': 'Redução de Custos',
                'categoria': 'despesa',
                'valor_meta': 100000.00,
                'valor_realizado': 75000.00,
                'periodo_inicio': '2024-01-01',
                'periodo_fim': '2024-12-31',
                'status': 'atingida',
                'percentual_atingido': 75.0
            }
        ]
        
        return jsonify({
            'success': True,
            'data': metas_mock
        })
        
    except Exception as e:
        print(f"[PROJECOES_API] Erro na API metas: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Erro ao buscar metas'
        }), 500

@projecoes_metas_bp.route('/api/projecoes')
@login_required
@perfil_required('financeiro', 'projecoes_metas')
def api_projecoes():
    """API para obter projeções financeiras"""
    try:
        # Obter parâmetros de período
        meses_futuro = request.args.get('meses', 12)
        categoria = request.args.get('categoria')
        
        print(f"[PROJECOES_API] Buscando projeções - Meses: {meses_futuro}")
        
        # TODO: Implementar lógica de cálculo de projeções
        # Por enquanto retornando dados mockados
        projecoes_mock = {
            'receita': [
                {'mes': '2024-02', 'valor_projetado': 95000.00, 'valor_realizado': 92000.00},
                {'mes': '2024-03', 'valor_projetado': 105000.00, 'valor_realizado': None},
                {'mes': '2024-04', 'valor_projetado': 110000.00, 'valor_realizado': None},
            ],
            'despesa': [
                {'mes': '2024-02', 'valor_projetado': 65000.00, 'valor_realizado': 67000.00},
                {'mes': '2024-03', 'valor_projetado': 70000.00, 'valor_realizado': None},
                {'mes': '2024-04', 'valor_projetado': 72000.00, 'valor_realizado': None},
            ],
            'resultado': [
                {'mes': '2024-02', 'valor_projetado': 30000.00, 'valor_realizado': 25000.00},
                {'mes': '2024-03', 'valor_projetado': 35000.00, 'valor_realizado': None},
                {'mes': '2024-04', 'valor_projetado': 38000.00, 'valor_realizado': None},
            ]
        }
        
        return jsonify({
            'success': True,
            'data': projecoes_mock
        })
        
    except Exception as e:
        print(f"[PROJECOES_API] Erro na API projeções: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Erro ao buscar projeções'
        }), 500

@projecoes_metas_bp.route('/api/criar-meta', methods=['POST'])
@login_required
@perfil_required('financeiro', 'projecoes_metas')
def api_criar_meta():
    """API para criar nova meta"""
    try:
        dados = request.get_json()
        
        print(f"[PROJECOES_API] Criando nova meta: {dados.get('nome')}")
        
        # TODO: Implementar lógica de criação de meta
        # Por enquanto apenas confirmando
        
        return jsonify({
            'success': True,
            'message': 'Meta criada com sucesso'
        })
        
    except Exception as e:
        print(f"[PROJECOES_API] Erro ao criar meta: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Erro ao criar meta'
        }), 500

@projecoes_metas_bp.route('/api/atualizar-meta', methods=['POST'])
@login_required
@perfil_required('financeiro', 'projecoes_metas')
def api_atualizar_meta():
    """API para atualizar meta existente"""
    try:
        dados = request.get_json()
        meta_id = dados.get('meta_id')
        
        print(f"[PROJECOES_API] Atualizando meta {meta_id}")
        
        # TODO: Implementar lógica de atualização de meta
        # Por enquanto apenas confirmando
        
        return jsonify({
            'success': True,
            'message': 'Meta atualizada com sucesso'
        })
        
    except Exception as e:
        print(f"[PROJECOES_API] Erro ao atualizar meta: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Erro ao atualizar meta'
        }), 500

@projecoes_metas_bp.route('/api/calcular-projecoes', methods=['POST'])
@login_required
@perfil_required('financeiro', 'projecoes_metas')
def api_calcular_projecoes():
    """API para recalcular projeções baseadas em novos parâmetros"""
    try:
        dados = request.get_json()
        
        print(f"[PROJECOES_API] Recalculando projeções com parâmetros: {dados}")
        
        # TODO: Implementar lógica de recálculo de projeções
        # Por enquanto apenas confirmando
        
        return jsonify({
            'success': True,
            'message': 'Projeções recalculadas com sucesso'
        })
        
    except Exception as e:
        print(f"[PROJECOES_API] Erro ao calcular projeções: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Erro ao calcular projeções'
        }), 500
