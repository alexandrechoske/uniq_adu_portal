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

@projecoes_metas_bp.route('/api/dados')
@login_required
@perfil_required('financeiro', 'projecoes_metas')
def api_dados():
    """API para obter dados de metas e projeções da tabela fin_metas_projecoes"""
    try:
        ano = request.args.get('ano', str(datetime.now().year))
        tipo = request.args.get('tipo', '')
        
        print(f"[PROJECOES_API] Buscando dados - Ano: {ano}, Tipo: {tipo}")
        
        # Query base
        query = supabase_admin.table('fin_metas_projecoes').select('*')
        
        # Filtros
        if ano:
            query = query.eq('ano', ano)
        if tipo:
            query = query.eq('tipo', tipo)
        
        # Executar query
        result = query.order('created_at', desc=True).execute()
        
        dados = result.data if result.data else []
        
        return jsonify({
            'success': True,
            'data': dados
        })
        
    except Exception as e:
        print(f"[PROJECOES_API] Erro na API dados: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Erro ao buscar dados'
        }), 500

@projecoes_metas_bp.route('/api/criar', methods=['POST'])
@login_required
@perfil_required('financeiro', 'projecoes_metas')
def api_criar():
    """API para criar nova meta/projeção"""
    try:
        dados = request.get_json()
        
        # Validar dados obrigatórios
        if not dados.get('ano') or not dados.get('meta') or not dados.get('tipo'):
            return jsonify({
                'success': False,
                'error': 'Campos obrigatórios: ano, meta, tipo'
            }), 400
        
        # Preparar dados para inserção
        item_data = {
            'ano': dados.get('ano'),
            'meta': int(dados.get('meta')),
            'mes': dados.get('mes'),  # Pode ser None para metas/projeções anuais
            'tipo': dados.get('tipo')
        }
        
        print(f"[PROJECOES_API] Criando item: {item_data}")
        
        # Inserir no banco
        result = supabase_admin.table('fin_metas_projecoes').insert(item_data).execute()
        
        if result.data:
            tipo_desc = {
                'meta': 'Meta anual',
                'projecao': 'Projeção anual', 
                'financeiro': 'Meta mensal'
            }.get(dados.get('tipo'), 'Item')
            
            return jsonify({
                'success': True,
                'message': f'{tipo_desc} criada com sucesso',
                'data': result.data[0]
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Erro ao inserir dados'
            }), 500
        
    except Exception as e:
        print(f"[PROJECOES_API] Erro ao criar: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Erro ao criar item'
        }), 500

@projecoes_metas_bp.route('/api/atualizar/<int:item_id>', methods=['PUT'])
@login_required
@perfil_required('financeiro', 'projecoes_metas')
def api_atualizar(item_id):
    """API para atualizar meta/projeção existente"""
    try:
        dados = request.get_json()
        
        # Validar dados obrigatórios
        if not dados.get('ano') or not dados.get('meta') or not dados.get('tipo'):
            return jsonify({
                'success': False,
                'error': 'Campos obrigatórios: ano, meta, tipo'
            }), 400
        
        # Preparar dados para atualização
        update_data = {
            'ano': dados.get('ano'),
            'meta': int(dados.get('meta')),
            'mes': dados.get('mes'),
            'tipo': dados.get('tipo')
        }
        
        print(f"[PROJECOES_API] Atualizando item {item_id}: {update_data}")
        
        # Atualizar no banco
        result = supabase_admin.table('fin_metas_projecoes').update(update_data).eq('id', item_id).execute()
        
        if result.data:
            tipo_desc = {
                'meta': 'Meta anual',
                'projecao': 'Projeção anual',
                'financeiro': 'Meta mensal'
            }.get(dados.get('tipo'), 'Item')
            
            return jsonify({
                'success': True,
                'message': f'{tipo_desc} atualizada com sucesso',
                'data': result.data[0]
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Item não encontrado'
            }), 404
        
    except Exception as e:
        print(f"[PROJECOES_API] Erro ao atualizar: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Erro ao atualizar item'
        }), 500

@projecoes_metas_bp.route('/api/excluir/<int:item_id>', methods=['DELETE'])
@login_required
@perfil_required('financeiro', 'projecoes_metas')
def api_excluir(item_id):
    """API para excluir meta/projeção"""
    try:
        print(f"[PROJECOES_API] Excluindo item {item_id}")
        
        # Excluir do banco
        result = supabase_admin.table('fin_metas_projecoes').delete().eq('id', item_id).execute()
        
        if result.data:
            return jsonify({
                'success': True,
                'message': 'Item excluído com sucesso'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Item não encontrado'
            }), 404
        
    except Exception as e:
        print(f"[PROJECOES_API] Erro ao excluir: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Erro ao excluir item'
        }), 500
