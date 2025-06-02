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
