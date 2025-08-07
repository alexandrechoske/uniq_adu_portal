from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import check_password_hash
from functools import wraps
from extensions import supabase, supabase_admin
from datetime import datetime
import requests
import json
import os
import re
from services.data_cache import data_cache

# Blueprint com configuração para templates e static locais
bp = Blueprint('auth', __name__, 
               url_prefix='/auth',
               template_folder='templates',
               static_folder='static',
               static_url_path='/auth/static')
@bp.route('/test-connection')
def test_connection():
    """Endpoint para testar conexão com o Supabase (admin client)"""
    try:
        # Testa conexão com cliente admin para evitar RLS
        response = supabase_admin.table('users').select('*').limit(1).execute()
        return jsonify({
            'status': 'success',
            'data': response.data
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Verificar se é uma requisição com API key bypass
        api_bypass_key = os.getenv('API_BYPASS_KEY')
        request_api_key = request.headers.get('X-API-Key')
        
        if api_bypass_key and request_api_key == api_bypass_key:
            print(f"[AUTH] Bypass de API detectado - permitindo acesso sem autenticação")
            # Criar uma sessão temporária para o bypass
            session['user'] = {
                'id': 'api_bypass',
                'email': 'api@bypass.com',
                'role': 'admin',
                'name': 'API Bypass',
                'user_companies': []
            }
            session['created_at'] = datetime.now().timestamp()
            session['last_activity'] = datetime.now().timestamp()
            return f(*args, **kwargs)
        
        # Verificar se existe usuário na sessão
        if 'user' not in session or not session.get('user') or not isinstance(session['user'], dict):
            return redirect(url_for('auth.login'))
        
        # Verificar campos essenciais
        user_data = session['user']
        required_fields = ['id', 'email', 'role']
        missing_fields = [field for field in required_fields if not user_data.get(field)]
        
        if missing_fields:
            print(f"[AUTH] Sessão corrompida - campos faltantes: {missing_fields}")
            session.clear()
            flash('Sessão expirada. Faça login novamente.', 'warning')
            return redirect(url_for('auth.login'))
        
        # Verificar expiração da sessão (12 horas)
        session_created = session.get('created_at')
        if session_created:
            session_age = datetime.now().timestamp() - session_created
            if session_age > 43200:  # 12 horas em segundos
                print(f"[AUTH] Sessão expirada após {session_age/3600:.1f} horas")
                session.clear()
                flash('Sessão expirada. Faça login novamente.', 'warning')
                return redirect(url_for('auth.login'))
        
        # Atualizar última atividade
        session['last_activity'] = datetime.now().timestamp()
        
        return f(*args, **kwargs)
    return decorated_function

def role_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Verificar se o usuário está logado
            if 'user' not in session:
                return redirect(url_for('auth.login'))
            
            user_role = session['user'].get('role')
            if user_role not in allowed_roles:
                flash('Acesso negado. Você não tem permissão para acessar esta página.', 'error')
                return redirect(url_for('auth.acesso_negado'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('senha') or request.form.get('password')
        print(f"[AUTH-DEBUG] POST recebido. Email: {email} | Senha: {'***' if password else None}")
        if not email or not password:
            print("[AUTH-DEBUG] Email ou senha não fornecidos.")
            flash('Email e senha são obrigatórios.', 'error')
            return render_template('login.html')
        try:
            print(f"[AUTH-DEBUG] Tentando autenticação via Supabase Auth para: {email}")
            
            # Usar autenticação do Supabase
            auth_response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            print(f"[AUTH-DEBUG] Resposta da autenticação: {auth_response}")
            
            if auth_response.user:
                # Buscar dados adicionais do usuário na tabela users
                user_response = supabase_admin.table('users').select('*').eq('email', email).execute()
                print(f"[AUTH-DEBUG] Dados adicionais do usuário: {user_response.data}")
                
                if user_response.data:
                    user = user_response.data[0]
                else:
                    # Se não existir na tabela users, criar dados básicos
                    user = {
                        'id': auth_response.user.id,
                        'email': email,
                        'name': email.split('@')[0],  # Nome padrão baseado no email
                        'role': 'cliente_unique',  # Role padrão
                        'is_active': True
                    }
                
                # Buscar empresas do usuário na nova estrutura
                user_companies = []
                user_companies_info = []
                
                if user['role'] in ['cliente_unique', 'interno_unique']:
                    try:
                        print(f"[AUTH] Buscando empresas para user_id: {user['id']}")
                        
                        # Buscar vínculos do usuário
                        user_empresas_response = supabase_admin.table('user_empresas')\
                            .select('cliente_sistema_id, ativo, data_vinculo')\
                            .eq('user_id', user['id'])\
                            .eq('ativo', True)\
                            .execute()
                        
                        if user_empresas_response.data:
                            cliente_sistema_ids = [v['cliente_sistema_id'] for v in user_empresas_response.data]
                            
                            # Buscar dados das empresas
                            empresas_response = supabase_admin.table('cad_clientes_sistema')\
                                .select('id, nome_cliente, cnpjs, ativo')\
                                .in_('id', cliente_sistema_ids)\
                                .eq('ativo', True)\
                                .execute()
                            
                            if empresas_response.data:
                                for empresa in empresas_response.data:
                                    cnpjs_array = empresa.get('cnpjs', [])
                                    
                                    # Adicionar info da empresa
                                    user_companies_info.append({
                                        'id': empresa['id'],
                                        'nome': empresa['nome_cliente'],
                                        'cnpjs': cnpjs_array,
                                        'quantidade_cnpjs': len(cnpjs_array)
                                    })
                                    
                                    # Extrair CNPJs normalizados
                                    if isinstance(cnpjs_array, list):
                                        for cnpj in cnpjs_array:
                                            if cnpj:
                                                normalized_cnpj = re.sub(r'\D', '', str(cnpj))
                                                if normalized_cnpj and len(normalized_cnpj) == 14:
                                                    user_companies.append(normalized_cnpj)
                                
                                # Remover duplicatas
                                user_companies = list(set(user_companies))
                        
                        print(f"[AUTH] Empresas encontradas: {len(user_companies_info)}")
                        print(f"[AUTH] CNPJs únicos: {len(user_companies)}")
                        print(f"[AUTH] Empresas: {[emp['nome'] for emp in user_companies_info]}")
                        
                    except Exception as companies_error:
                        print(f"[AUTH] Erro ao buscar empresas: {str(companies_error)}")
                
                # Criar sessão do usuário
                session.permanent = True
                session['user'] = {
                    'id': user['id'],
                    'email': user['email'],
                    'name': user['name'],
                    'role': user['role'],
                    'is_active': user.get('is_active', True),
                    'user_companies': user_companies,
                    'user_companies_info': user_companies_info
                }
                session['created_at'] = datetime.now().timestamp()
                session['last_activity'] = datetime.now().timestamp()
                
                print(f"[AUTH] Login bem-sucedido via Supabase Auth para {email} com role {user['role']}")
                
                try:
                    data_cache.preload_user_data(user['id'], user['role'])
                    print(f"[AUTH] Dados precarregados para usuário {user['id']}")
                except Exception as cache_error:
                    print(f"[AUTH] Erro ao precarregar dados: {str(cache_error)}")
                
                flash(f'Bem-vindo, {user["name"]}!', 'success')
                return redirect(url_for('menu.menu_home'))
            else:
                print("[AUTH-DEBUG] Falha na autenticação Supabase.")
                flash('Email ou senha incorretos.', 'error')
                return render_template('login.html')
        except Exception as e:
            print(f"[AUTH] Erro no login: {str(e)}")
            flash('Erro interno do servidor. Tente novamente.', 'error')
            return render_template('login.html')
    print("[AUTH-DEBUG] GET login page.")
    return render_template('login.html')

@bp.route('/logout')
def logout():
    user_name = session.get('user', {}).get('name', 'Usuário')
    session.clear()
    flash(f'Até logo, {user_name}!', 'info')
    return redirect(url_for('auth.login'))

@bp.route('/acesso-negado')
def acesso_negado():
    return render_template('acesso_negado.html')

@bp.route('/api/session-info')
@login_required
def session_info():
    """Endpoint para obter informações da sessão atual"""
    try:
        user_data = session.get('user', {})
        session_info = {
            'user': {
                'id': user_data.get('id'),
                'name': user_data.get('name'),
                'email': user_data.get('email'),
                'role': user_data.get('role'),
                'is_active': user_data.get('is_active')
            },
            'session': {
                'created_at': session.get('created_at'),
                'last_activity': session.get('last_activity'),
                'is_authenticated': True
            }
        }
        
        return jsonify({
            'success': True,
            'data': session_info
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/api/extend-session', methods=['POST'])
@login_required
def extend_session():
    """Endpoint para estender a sessão atual"""
    try:
        session['last_activity'] = datetime.now().timestamp()
        
        return jsonify({
            'success': True,
            'message': 'Sessão estendida com sucesso'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
