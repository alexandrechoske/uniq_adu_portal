from flask import Blueprint, render_template, session
import flask
import datetime
import sys
import platform
import os

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
