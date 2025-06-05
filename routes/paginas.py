from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from extensions import supabase
from functools import wraps
from permissions import get_user_permissions
import json

bp = Blueprint('paginas', __name__, url_prefix='/paginas')

def admin_required(f):
    """
    Decorador para verificar se o usuário é administrador
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Verificar se o usuário está logado
        if not session.get('user'):
            flash('Faça login para acessar esta página.', 'error')
            return redirect(url_for('auth.login'))
            
        # Verificar se é admin
        if session['user']['role'] != 'admin':
            flash('Acesso restrito a administradores.', 'error')
            return redirect(url_for('dashboard.index'))
            
        # Buscar permissões
        permissions = get_user_permissions(session['user']['id'], 'admin')
        session['permissions'] = permissions
        
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/api', methods=['GET'])
def get_paginas():
    """
    API legado - mantida para compatibilidade mas sem funcionalidades
    Esta API não é mais utilizada, pois o menu agora é estático no HTML
    """
    if not session.get('user'):
        return jsonify({
            'status': 'error',
            'message': 'Usuário não autenticado',
            'code': 'auth_required'
        }), 401
    
    # Retorna uma lista vazia já que não usamos mais o sistema dinâmico
    return jsonify({
        'status': 'success',
        'message': 'Sistema estático em operação',
        'data': []
    })

@bp.route('/check-session', methods=['GET'])
def check_session():
    """
    API legado - mantida para compatibilidade mas sem funcionalidades
    Verifica se a sessão do usuário está válida
    """
    if not session.get('user'):
        return jsonify({
            'status': 'error',
            'message': 'Usuário não autenticado',
            'code': 'auth_required'
        }), 401
    
    return jsonify({
        'status': 'success',
        'message': 'Sessão válida'
    })

@bp.route('/', methods=['GET'])
@admin_required
def index():
    """
    Página de administração das páginas do portal
    """
    try:
        response = supabase.table('paginas_portal').select('*').order('ordem').execute()
        return render_template('paginas/index.html', paginas=response.data)
    except Exception as e:
        flash(f'Erro ao carregar páginas: {str(e)}', 'error')
        return redirect(url_for('dashboard.index'))
