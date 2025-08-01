from flask import Blueprint, render_template, session, jsonify
import flask
import datetime
import sys
import platform
import os
from extensions import supabase_admin

bp = Blueprint('debug', __name__, url_prefix='/debug')

@bp.route('/')
def index():
    """
    Página de debug do sistema para auxiliar no diagnóstico de problemas.
    """
    flask_version = flask.__version__
    env = os.environ.get('FLASK_ENV', 'Não definido')
    debug = os.environ.get('FLASK_DEBUG', 'Não definido')
    now = datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    
    return render_template('debug.html', 
                           flask_version=flask_version,
                           env=env,
                           debug=debug,
                           now=now)

@bp.route('/log-session')
def log_session():
    """
    Loga as variáveis da sessão atual
    """
    session_data = {key: session[key] for key in session}
    return {
        'status': 'success',
        'session': session_data
    }

@bp.route('/check-materiais-cache')
def check_materiais_cache():
    """
    Verifica o estado do cache de materiais
    """
    from services.data_cache import data_cache
    
    try:
        # Verificar se usuário está logado
        user_id = session.get('user', {}).get('id')
        user_role = session.get('user', {}).get('role')
        
        if not user_id:
            return {
                'status': 'error',
                'message': 'Usuário não logado'
            }
        
        # Verificar cache server-side
        cached_data = data_cache.get_cache(user_id, 'raw_data')
        
        # Verificar cache da sessão
        session_cache = session.get('cached_data', [])
        
        return {
            'status': 'success',
            'user_id': user_id,
            'user_role': user_role,
            'server_cache': {
                'exists': cached_data is not None,
                'type': type(cached_data).__name__,
                'length': len(cached_data) if cached_data and isinstance(cached_data, list) else 0
            },
            'session_cache': {
                'exists': len(session_cache) > 0,
                'type': type(session_cache).__name__,
                'length': len(session_cache) if isinstance(session_cache, list) else 0
            }
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }

@bp.route('/check-paginas-table')
def check_paginas_table():
    """
    Verifica o estado da tabela paginas_portal no Supabase
    """
    from extensions import supabase
    
    try:
        # Verificar se a tabela existe tentando consultar ela
        response = supabase.table('paginas_portal').select('*').execute()
        
        table_info = {
            'table_exists': True,
            'total_records': len(response.data) if response.data else 0,
            'records': response.data if response.data else [],
            'status': 'success'
        }
        
        # Se não há registros, mostrar estrutura esperada
        if not response.data:
            table_info['expected_structure'] = {
                'id': 'integer (auto-increment)',
                'id_pagina': 'text (unique identifier)',
                'nome_pagina': 'text (display name)',
                'url_rota': 'text (route URL)',
                'icone': 'text (MDI icon class)',
                'roles': 'json array (user roles)',
                'flg_ativo': 'boolean (active flag)',
                'ordem': 'integer (display order)',
                'mensagem_manutencao': 'text (maintenance message)'
            }
        
        return table_info
        
    except Exception as e:
        return {
            'status': 'error',
            'table_exists': False,
            'error': str(e),
            'message': 'Tabela paginas_portal não existe ou não é acessível'
        }

@bp.route('/recent-logs')
def recent_logs():
    """
    Endpoint para visualizar logs recentes do sistema
    """
    try:
        # Buscar logs das últimas 2 horas
        response = supabase_admin.table('access_logs').select('*').order('timestamp', desc=True).limit(50).execute()
        
        logs = []
        for log in response.data:
            logs.append({
                'timestamp': log.get('timestamp'),
                'user_id': log.get('user_id'),
                'user_name': log.get('user_name'),
                'user_role': log.get('user_role'),
                'endpoint': log.get('endpoint'),
                'page_name': log.get('page_name'),
                'module': log.get('module'),
                'ip_address': log.get('ip_address'),
                'user_agent': log.get('user_agent')
            })
        
        return jsonify(logs)
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Erro ao buscar logs: {str(e)}'
        }), 500
