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
    static_folder='static'
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
        
        # Validar dados obrigatórios - aceitar tanto 'meta' quanto 'valor_meta'
        meta_value = dados.get('meta') or dados.get('valor_meta')
        tipo = dados.get('tipo')
        ano = dados.get('ano')
        mes = dados.get('mes')
        
        if not ano or not meta_value or not tipo:
            return jsonify({
                'success': False,
                'error': 'Campos obrigatórios: ano, meta/valor_meta, tipo'
            }), 400
        
        # Validação de tipos aceitos
        tipos_validos = ['financeiro', 'operacional', 'projecao']
        if tipo not in tipos_validos:
            return jsonify({
                'success': False,
                'error': f'Tipo deve ser um dos seguintes: {", ".join(tipos_validos)}'
            }), 400
        
        # Para todos os tipos, mês é obrigatório
        if not mes:
            return jsonify({
                'success': False,
                'error': 'Mês é obrigatório'
            }), 400
        
        # Normalizar mês para 2 dígitos
        try:
            mes_int = int(mes)
            if mes_int < 1 or mes_int > 12:
                return jsonify({
                    'success': False,
                    'error': 'Mês deve estar entre 1 e 12'
                }), 400
            mes_normalizado = f"{mes_int:02d}"
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Mês deve ser um número válido'
            }), 400
        
        # Preparar dados para inserção
        item_data = {
            'ano': int(ano),
            'meta': int(meta_value),
            'mes': mes_normalizado,
            'tipo': tipo
        }
        
        print(f"[PROJECOES_API] Criando item: {item_data}")
        
        # Inserir no banco
        result = supabase_admin.table('fin_metas_projecoes').insert(item_data).execute()
        
        if result.data:
            tipo_desc = {
                'financeiro': 'Meta financeira',
                'operacional': 'Meta operacional', 
                'projecao': 'Projeção'
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

@projecoes_metas_bp.route('/api/criar-lote', methods=['POST'])
@login_required
@perfil_required('financeiro', 'projecoes_metas')
def api_criar_lote():
    """API para criar múltiplas metas/projeções de uma vez"""
    try:
        dados = request.get_json()
        
        # Opção 1: Lista de itens completos
        if 'itens' in dados and isinstance(dados['itens'], list):
            itens_para_inserir = []
            
            for item in dados['itens']:
                # Validação de cada item
                meta_value = item.get('meta') or item.get('valor_meta')
                tipo = item.get('tipo')
                ano = item.get('ano')
                mes = item.get('mes')
                
                if not ano or not meta_value or not tipo or not mes:
                    return jsonify({
                        'success': False,
                        'error': 'Cada item deve ter: ano, mes, meta/valor_meta, tipo'
                    }), 400
                
                # Validação de tipos aceitos
                tipos_validos = ['financeiro', 'operacional', 'projecao']
                if tipo not in tipos_validos:
                    return jsonify({
                        'success': False,
                        'error': f'Tipo deve ser um dos seguintes: {", ".join(tipos_validos)}'
                    }), 400
                
                # Normalizar mês
                try:
                    mes_int = int(mes)
                    if mes_int < 1 or mes_int > 12:
                        return jsonify({
                            'success': False,
                            'error': 'Mês deve estar entre 1 e 12'
                        }), 400
                    mes_normalizado = f"{mes_int:02d}"
                except ValueError:
                    return jsonify({
                        'success': False,
                        'error': 'Mês deve ser um número válido'
                    }), 400
                
                itens_para_inserir.append({
                    'ano': int(ano),
                    'meta': int(meta_value),
                    'mes': mes_normalizado,
                    'tipo': tipo
                })
        
        # Opção 2: Ano + meses + meta + tipo (para criar vários meses do mesmo ano/tipo/valor)
        elif all(key in dados for key in ['ano', 'meses', 'meta', 'tipo']):
            ano = dados.get('ano')
            meses = dados.get('meses')  # Lista de meses
            meta_value = dados.get('meta')
            tipo = dados.get('tipo')
            
            if not isinstance(meses, list) or len(meses) == 0:
                return jsonify({
                    'success': False,
                    'error': 'Meses deve ser uma lista não vazia'
                }), 400
            
            # Validação de tipos aceitos
            tipos_validos = ['financeiro', 'operacional', 'projecao']
            if tipo not in tipos_validos:
                return jsonify({
                    'success': False,
                    'error': f'Tipo deve ser um dos seguintes: {", ".join(tipos_validos)}'
                }), 400
            
            itens_para_inserir = []
            for mes in meses:
                # Normalizar mês
                try:
                    mes_int = int(mes)
                    if mes_int < 1 or mes_int > 12:
                        return jsonify({
                            'success': False,
                            'error': 'Mês deve estar entre 1 e 12'
                        }), 400
                    mes_normalizado = f"{mes_int:02d}"
                except ValueError:
                    return jsonify({
                        'success': False,
                        'error': 'Mês deve ser um número válido'
                    }), 400
                
                itens_para_inserir.append({
                    'ano': int(ano),
                    'meta': int(meta_value),
                    'mes': mes_normalizado,
                    'tipo': tipo
                })
        
        else:
            return jsonify({
                'success': False,
                'error': 'Envie "itens" (lista) ou "ano", "meses", "meta", "tipo"'
            }), 400
        
        if not itens_para_inserir:
            return jsonify({
                'success': False,
                'error': 'Nenhum item válido para inserir'
            }), 400
        
        print(f"[PROJECOES_API] Criando {len(itens_para_inserir)} itens em lote")
        
        # Inserir todos os itens de uma vez
        result = supabase_admin.table('fin_metas_projecoes').insert(itens_para_inserir).execute()
        
        if result.data:
            return jsonify({
                'success': True,
                'message': f'{len(result.data)} itens criados com sucesso',
                'data': result.data
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Erro ao inserir dados em lote'
            }), 500
        
    except Exception as e:
        print(f"[PROJECOES_API] Erro ao criar lote: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Erro ao criar itens em lote'
        }), 500

@projecoes_metas_bp.route('/api/atualizar/<int:item_id>', methods=['PUT'])
@login_required
@perfil_required('financeiro', 'projecoes_metas')
def api_atualizar(item_id):
    """API para atualizar meta/projeção existente"""
    try:
        dados = request.get_json()
        
        # Validar dados obrigatórios - aceitar tanto 'meta' quanto 'valor_meta'
        meta_value = dados.get('meta') or dados.get('valor_meta')
        tipo = dados.get('tipo')
        ano = dados.get('ano')
        mes = dados.get('mes')
        
        if not ano or not meta_value or not tipo:
            return jsonify({
                'success': False,
                'error': 'Campos obrigatórios: ano, meta/valor_meta, tipo'
            }), 400
        
        # Validação de tipos aceitos
        tipos_validos = ['financeiro', 'operacional', 'projecao']
        if tipo not in tipos_validos:
            return jsonify({
                'success': False,
                'error': f'Tipo deve ser um dos seguintes: {", ".join(tipos_validos)}'
            }), 400
        
        # Para todos os tipos, mês é obrigatório
        if not mes:
            return jsonify({
                'success': False,
                'error': 'Mês é obrigatório'
            }), 400
        
        # Normalizar mês para 2 dígitos
        try:
            mes_int = int(mes)
            if mes_int < 1 or mes_int > 12:
                return jsonify({
                    'success': False,
                    'error': 'Mês deve estar entre 1 e 12'
                }), 400
            mes_normalizado = f"{mes_int:02d}"
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Mês deve ser um número válido'
            }), 400
        
        # Preparar dados para atualização
        update_data = {
            'ano': int(ano),
            'meta': int(meta_value),
            'mes': mes_normalizado,
            'tipo': tipo
        }
        
        print(f"[PROJECOES_API] Atualizando item {item_id}: {update_data}")
        
        # Atualizar no banco
        result = supabase_admin.table('fin_metas_projecoes').update(update_data).eq('id', item_id).execute()
        
        if result.data:
            tipo_desc = {
                'financeiro': 'Meta financeira',
                'operacional': 'Meta operacional',
                'projecao': 'Projeção'
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
