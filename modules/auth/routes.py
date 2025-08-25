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

import json
import os
import re
from services.data_cache import data_cache

def perfil_required(modulo_codigo, pagina_codigo=None):
    """
    Decorador para verificar se o usuário tem acesso a um módulo/página específico baseado em seu perfil
    
    Args:
        modulo_codigo (str): Código do módulo (ex: 'financeiro', 'dashboard', 'usuarios')
        pagina_codigo (str, optional): Código da página específica dentro do módulo
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            print(f"[PERFIL_CHECK] Verificando acesso para módulo: {modulo_codigo}, página: {pagina_codigo}")
            
            # Verificar se usuário está logado
            if 'user' not in session:
                print(f"[PERFIL_CHECK] ❌ Usuário não logado")
                return redirect(url_for('auth.login'))
            
            user = session.get('user', {})
            user_role = user.get('role')
            user_perfis_info = user.get('user_perfis_info', [])
            
            print(f"[PERFIL_CHECK] Usuário: {user.get('email')}, Role: {user_role}")
            print(f"[PERFIL_CHECK] Perfis do usuário: {len(user_perfis_info)} encontrados")
            
            # Admins têm acesso total
            if user_role == 'admin':
                print(f"[PERFIL_CHECK] ✅ Admin tem acesso total")
                return f(*args, **kwargs)
            
            # Verificar se tem perfis configurados
            if not user_perfis_info:
                print(f"[PERFIL_CHECK] ❌ Usuário sem perfis configurados")
                flash('Você não tem perfis de acesso configurados. Entre em contato com o administrador.', 'error')
                return redirect(url_for('menu.menu_home'))
            
            # Verificar acesso ao módulo nos perfis do usuário
            acesso_permitido = False
            
            for perfil_info in user_perfis_info:
                perfil_nome = perfil_info.get('perfil_nome')
                modulos = perfil_info.get('modulos', [])
                
                print(f"[PERFIL_CHECK] Verificando perfil: {perfil_nome}")
                
                for modulo in modulos:
                    modulo_cod = modulo.get('codigo')
                    modulo_paginas = modulo.get('paginas', [])
                    
                    print(f"[PERFIL_CHECK] - Módulo: {modulo_cod}, Páginas: {modulo_paginas}")
                    
                    # Verificar se tem acesso ao módulo
                    if modulo_cod == modulo_codigo:
                        # Se não especificou página, acesso ao módulo é suficiente
                        if not pagina_codigo:
                            acesso_permitido = True
                            print(f"[PERFIL_CHECK] ✅ Acesso permitido ao módulo {modulo_codigo}")
                            break
                        
                        # Se especificou página, verificar se está na lista
                        if pagina_codigo in modulo_paginas:
                            acesso_permitido = True
                            print(f"[PERFIL_CHECK] ✅ Acesso permitido à página {pagina_codigo} do módulo {modulo_codigo}")
                            break
                        
                        # Se módulo permite todas as páginas (lista vazia ou contém '*')
                        if not modulo_paginas or '*' in modulo_paginas:
                            acesso_permitido = True
                            print(f"[PERFIL_CHECK] ✅ Acesso permitido - módulo {modulo_codigo} permite todas as páginas")
                            break
                
                if acesso_permitido:
                    break
            
            if not acesso_permitido:
                print(f"[PERFIL_CHECK] ❌ Acesso negado ao módulo {modulo_codigo}")
                flash(f'Você não tem permissão para acessar este módulo ({modulo_codigo}).', 'error')
                return redirect(url_for('menu.menu_home'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

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
        # Primeiro, verificar se existe usuário na sessão válida
        if 'user' in session and session.get('user') and isinstance(session['user'], dict):
            user_data = session['user']
            required_fields = ['id', 'email', 'role']
            missing_fields = [field for field in required_fields if not user_data.get(field)]
            
            # Se a sessão está válida e completa, usar ela (não fazer bypass)
            if not missing_fields:
                print(f"[AUTH] Sessão válida encontrada para: {user_data.get('email')} - usando sessão existente")
                
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
                session.permanent = True
                return f(*args, **kwargs)
        
        # Só usar bypass se NÃO existe sessão válida
        api_bypass_key = os.getenv('API_BYPASS_KEY')
        request_api_key = request.headers.get('X-API-Key')
        
        print(f"[AUTH] Sessão inválida/inexistente, verificando bypass")
        
        if api_bypass_key and request_api_key == api_bypass_key:
            print(f"[AUTH] Bypass de API detectado - criando sessão temporária")
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
        
        # Se não tem sessão válida nem bypass, redirecionar para login
        print(f"[AUTH] Redirecionando para login - sem sessão válida nem bypass")
        return redirect(url_for('auth.login'))
        
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
                # Buscar dados adicionais do usuário na tabela users (ambiente correto)
                from modules.usuarios.routes import get_users_table
                users_table = get_users_table()
                user_response = supabase_admin.table(users_table).select('*').eq('email', email).execute()
                print(f"[AUTH-DEBUG] Dados adicionais do usuário (tabela {users_table}): {user_response.data}")
                
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
                
                # Buscar perfis do usuário para controle de acesso
                user_perfis = []
                user_perfis_info = []
                
                # Verificar se tem perfis no campo perfis_json
                if user.get('perfis_json'):
                    try:
                        perfis_list = json.loads(user['perfis_json']) if isinstance(user['perfis_json'], str) else user['perfis_json']
                        
                        for perfil_id in perfis_list:
                            # Buscar informações detalhadas do perfil
                            perfil_response = supabase_admin.table('users_perfis').select('*').eq('perfil_nome', perfil_id).execute()
                            
                            if perfil_response.data:
                                # Agrupar módulos por perfil
                                modulos = []
                                for registro in perfil_response.data:
                                    if registro.get('is_active', True):
                                        modulos.append({
                                            'codigo': registro['modulo_codigo'],  # Campo correto: modulo_codigo
                                            'nome': registro['modulo_nome'],      # Campo correto: modulo_nome
                                            'paginas': registro.get('paginas_modulo', [])  # Campo correto: paginas_modulo
                                        })
                                
                                user_perfis_info.append({
                                    'perfil_nome': perfil_id,
                                    'modulos': modulos
                                })
                                
                        user_perfis = perfis_list
                        print(f"[AUTH] Perfis carregados: {user_perfis}")
                        print(f"[AUTH] Módulos disponíveis: {[m['codigo'] for p in user_perfis_info for m in p['modulos']]}")
                        
                    except Exception as perfil_error:
                        print(f"[AUTH] Erro ao carregar perfis: {str(perfil_error)}")
                
                # Criar sessão do usuário
                session.permanent = True
                session['user'] = {
                    'id': user['id'],
                    'email': user['email'],
                    'name': user['name'],
                    'role': user['role'],
                    'is_active': user.get('is_active', True),
                    'user_companies': user_companies,
                    'user_companies_info': user_companies_info,
                    'user_perfis': user_perfis,
                    'user_perfis_info': user_perfis_info
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
