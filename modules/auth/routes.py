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

# ===========================================================
# FUNÇÕES DE VERIFICAÇÃO DE MANUTENÇÃO
# ===========================================================

def check_maintenance_mode():
    """
    Verifica se o portal está em modo de manutenção.
    
    Returns:
        tuple: (em_manutencao: bool, dados_manutencao: dict)
    """
    try:
        # Consultar tabela de manutenção usando cliente admin (bypass RLS)
        response = supabase_admin.table('DANGER_TABLE_MANUTENCAO')\
            .select('*')\
            .eq('id', '1')\
            .single()\
            .execute()
        
        if response.data:
            dados = response.data
            em_manutencao = dados.get('manutencao', False)
            
            print(f"[MANUTENCAO] Status verificado: {'🔴 EM MANUTENÇÃO' if em_manutencao else '🟢 OPERACIONAL'}")
            
            return em_manutencao, dados
        else:
            print("[MANUTENCAO] ⚠️ Tabela de manutenção não encontrada - assumindo modo operacional")
            return False, {}
            
    except Exception as e:
        print(f"[MANUTENCAO] ❌ Erro ao verificar modo de manutenção: {e}")
        # Em caso de erro, permitir acesso (fail-safe)
        return False, {}

def render_maintenance_page(dados_manutencao):
    """
    Renderiza a página de manutenção com informações customizadas.
    
    Args:
        dados_manutencao (dict): Dados da tabela de manutenção
    
    Returns:
        Rendered template
    """
    mensagem = dados_manutencao.get('mensagem_customizada', None)
    data_prevista = dados_manutencao.get('data_prevista_fim', None)
    
    # Formatar data prevista se existir
    if data_prevista:
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(data_prevista.replace('Z', '+00:00'))
            data_prevista = dt.strftime('%d/%m/%Y às %H:%M')
        except:
            pass
    
    return render_template(
        'manutencao.html',
        mensagem_customizada=mensagem,
        data_prevista_fim=data_prevista
    )

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
                'perfil_principal': 'master_admin',  # CRITICAL FIX: API bypass needs master_admin privileges
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
            
            user = session['user']
            user_role = user.get('role')
            user_perfil_principal = user.get('perfil_principal', 'basico')
            
            # Verificar acesso tradicional por role
            if user_role in allowed_roles:
                return f(*args, **kwargs)
            
            # Verificar se é Module Admin tentando acessar gestão de usuários
            if 'admin' in allowed_roles:
                # Master Admins: admin + master_admin
                if user_role == 'admin' and user_perfil_principal == 'master_admin':
                    print(f"[AUTH] Master Admin (master_admin) autorizado para {allowed_roles}")
                    return f(*args, **kwargs)
                
                # Module Admins: interno_unique + admin_operacao/admin_financeiro
                if user_role == 'interno_unique' and user_perfil_principal.startswith('admin_'):
                    print(f"[AUTH] Module Admin ({user_perfil_principal}) autorizado para {allowed_roles}")
                    return f(*args, **kwargs)
            
            print(f"[AUTH] Acesso negado - role {user_role} (perfil_principal {user_perfil_principal}) não autorizado para {allowed_roles}")
            flash('Acesso negado. Você não tem permissão para acessar esta página.', 'error')
            return redirect(url_for('menu.menu_home'))  # Redirect to menu instead of non-existent endpoint
            
        return decorated_function
    return decorator

@bp.route('/login', methods=['GET', 'POST'])
def login():
    # ===========================================================
    # 1. VERIFICAR MODO DE MANUTENÇÃO (ANTES DE QUALQUER COISA)
    # ===========================================================
    em_manutencao, dados_manutencao = check_maintenance_mode()
    
    if em_manutencao:
        print("[MANUTENCAO] 🚫 Portal em manutenção - bloqueando acesso ao login")
        return render_maintenance_page(dados_manutencao)
    
    # ===========================================================
    # 2. PROCESSAR LOGIN NORMALMENTE
    # ===========================================================
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
                    'perfil_principal': user.get('perfil_principal', 'basico'),  # Novo campo perfil_principal
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

# =============================================================================
# ENDPOINTS DE RECUPERAÇÃO DE SENHA
# =============================================================================

@bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Página e endpoint para solicitação de recuperação de senha"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        print(f"[PASSWORD_RESET] Solicitação de reset para email: {email}")
        
        if not email:
            flash('Email é obrigatório.', 'error')
            return render_template('forgot_password.html')
        
        # Validar formato do email
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, email):
            flash('Por favor, insira um email válido.', 'error')
            return render_template('forgot_password.html')
        
        try:
            # Verificar se o email existe na base de dados
            from modules.usuarios.routes import get_users_table
            users_table = get_users_table()
            user_check = supabase_admin.table(users_table).select('email, is_active').eq('email', email).execute()
            
            if not user_check.data:
                print(f"[PASSWORD_RESET] Email {email} não encontrado na base de dados")
                # Por segurança, não revelar se o email existe ou não
                flash('Se o email estiver cadastrado, você receberá instruções para redefinir sua senha.', 'info')
                return render_template('forgot_password.html')
            
            user_data = user_check.data[0]
            if not user_data.get('is_active', True):
                print(f"[PASSWORD_RESET] Usuário {email} está inativo")
                flash('Esta conta está desativada. Entre em contato com o suporte.', 'error')
                return render_template('forgot_password.html')
            
            # Enviar email de recuperação usando Supabase Auth
            print(f"[PASSWORD_RESET] Enviando email de recuperação para: {email}")
            
            # Configurar URL de redirecionamento
            redirect_url = request.url_root.rstrip('/') + url_for('auth.reset_password')
            
            # Try to send the password reset email
            try:
                auth_response = supabase.auth.reset_password_for_email(
                    email,
                    {
                        "redirect_to": redirect_url
                    }
                )
                print(f"[PASSWORD_RESET] Resposta do Supabase: {auth_response}")
                flash('Se o email estiver cadastrado, você receberá instruções para redefinir sua senha.', 'info')
            except Exception as email_error:
                print(f"[PASSWORD_RESET] Erro ao enviar email de recuperação: {str(email_error)}")
                print(f"[PASSWORD_RESET] Tipo de erro: {type(email_error)}")
                # Log more detailed error information
                import traceback
                print(f"[PASSWORD_RESET] Traceback completo:")
                traceback.print_exc()
                
                # Check if it's a specific Supabase error
                if hasattr(email_error, 'message'):
                    print(f"[PASSWORD_RESET] Mensagem de erro detalhada: {email_error.message}")
                
                flash('Erro ao enviar email de recuperação. Por favor, tente novamente mais tarde ou entre em contato com o suporte.', 'error')
            
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            print(f"[PASSWORD_RESET] Erro geral no processo de reset: {str(e)}")
            import traceback
            traceback.print_exc()
            flash('Erro interno. Tente novamente mais tarde.', 'error')
            return render_template('forgot_password.html')
    
    return render_template('forgot_password.html')

@bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    """Página e endpoint para redefinição de senha com token"""
    
    # GET: Mostrar página de reset
    if request.method == 'GET':
        print(f"[PASSWORD_RESET] GET - URL: {request.url}")
        
        # Verificar se há parâmetros tradicionais da query string
        token = request.args.get('token')
        token_type = request.args.get('type')
        access_token = request.args.get('access_token')
        refresh_token = request.args.get('refresh_token')
        
        print(f"[PASSWORD_RESET] Query params - token: {bool(token)}, type: {token_type}")
        print(f"[PASSWORD_RESET] Query params - access_token: {bool(access_token)}")
        
        # Se temos tokens na query string (método antigo), processar normalmente
        if access_token and refresh_token:
            print(f"[PASSWORD_RESET] Processando tokens da query string")
            try:
                auth_response = supabase.auth.set_session(access_token, refresh_token)
                if auth_response.user:
                    session['reset_access_token'] = access_token
                    session['reset_refresh_token'] = refresh_token
                    session['reset_user_email'] = auth_response.user.email
                    return render_template('reset_password.html', user_email=auth_response.user.email)
                else:
                    print(f"[PASSWORD_RESET] Falha ao autenticar com tokens da query string")
                    flash('Link de recuperação inválido ou expirado. Solicite um novo link.', 'error')
                    return redirect(url_for('auth.forgot_password'))
            except Exception as e:
                print(f"[PASSWORD_RESET] Erro ao processar tokens da query string: {str(e)}")
                import traceback
                traceback.print_exc()
                flash('Link de recuperação inválido. Solicite um novo link.', 'error')
                return redirect(url_for('auth.forgot_password'))
        
        # Se temos token simples (método de fallback), mostrar confirmação
        elif token and token_type == 'recovery':
            print(f"[PASSWORD_RESET] Token simples detectado, mostrando confirmação")
            return render_template('reset_password_confirm.html', token=token)
        
        # Caso padrão: mostrar template que processa hash fragment
        # Isso vai capturar os tokens do hash fragment via JavaScript
        print(f"[PASSWORD_RESET] Mostrando template para processar hash fragment")
        return render_template('reset_password_confirm.html')
    
    # POST: Processar nova senha
    elif request.method == 'POST':
        new_password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        
        # Recuperar tokens do formulário (vindos do hash fragment)
        access_token = request.form.get('access_token', '').strip()
        refresh_token = request.form.get('refresh_token', '').strip()
        user_email = request.form.get('user_email', '').strip()
        
        # Também verificar métodos antigos da sessão para compatibilidade
        if not access_token:
            access_token = session.get('reset_access_token')
            refresh_token = session.get('reset_refresh_token')
            user_email = session.get('reset_user_email')
        
        print(f"[PASSWORD_RESET] POST - Processando nova senha")
        print(f"[PASSWORD_RESET] Email: {user_email}")
        print(f"[PASSWORD_RESET] Tem access_token: {bool(access_token)}")
        print(f"[PASSWORD_RESET] Tem refresh_token: {bool(refresh_token)}")
        
        if not user_email or not access_token or not refresh_token:
            flash('Sessão de recuperação inválida. Solicite um novo link.', 'error')
            return redirect(url_for('auth.forgot_password'))
        
        # Validações
        if not new_password or not confirm_password:
            flash('Todos os campos são obrigatórios.', 'error')
            return render_template('reset_password.html', user_email=user_email)
        
        if new_password != confirm_password:
            flash('As senhas não coincidem.', 'error')
            return render_template('reset_password.html', user_email=user_email)
        
        if len(new_password) < 6:
            flash('A senha deve ter pelo menos 6 caracteres.', 'error')
            return render_template('reset_password.html', user_email=user_email)
        
        try:
            print(f"[PASSWORD_RESET] Configurando sessão com tokens do hash fragment")
            
            # Configurar sessão com os tokens de recuperação
            auth_response = supabase.auth.set_session(access_token, refresh_token)
            
            if not auth_response.user:
                print(f"[PASSWORD_RESET] Falha ao configurar sessão com tokens")
                flash('Tokens de recuperação inválidos ou expirados.', 'error')
                return redirect(url_for('auth.forgot_password'))
            
            print(f"[PASSWORD_RESET] Sessão configurada, atualizando senha...")
            
            # Atualizar senha no Supabase Auth
            update_response = supabase.auth.update_user({"password": new_password})
            
            if update_response.user:
                print(f"[PASSWORD_RESET] Senha atualizada com sucesso para: {user_email}")
                
                # Limpar sessão
                session.pop('reset_access_token', None)
                session.pop('reset_refresh_token', None)
                session.pop('reset_user_email', None)
                session.pop('reset_user_id', None)
                session.pop('reset_token_confirmed', None)
                session.pop('reset_method', None)
                
                # Fazer logout da sessão de recuperação
                try:
                    supabase.auth.sign_out()
                except:
                    pass
                
                flash('Senha redefinida com sucesso! Faça login com sua nova senha.', 'success')
                return redirect(url_for('auth.login'))
            else:
                print(f"[PASSWORD_RESET] Falha ao atualizar senha")
                flash('Erro ao redefinir senha. Tente novamente.', 'error')
                return render_template('reset_password.html', user_email=user_email)
                
        except Exception as e:
            print(f"[PASSWORD_RESET] Erro ao processar reset: {str(e)}")
            import traceback
            traceback.print_exc()
            flash('Erro interno. Tente novamente ou solicite um novo link.', 'error')
            return redirect(url_for('auth.forgot_password'))
                
        except Exception as e:
            print(f"[PASSWORD_RESET] Erro ao atualizar senha: {str(e)}")
            flash('Erro interno. Tente novamente.', 'error')
            return render_template('reset_password.html', user_email=user_email)

@bp.route('/confirm-reset-email', methods=['POST'])
def confirm_reset_email():
    """Endpoint para confirmar email e processar token de reset"""
    
    email = request.form.get('email', '').strip()
    token = request.form.get('token', '').strip()
    
    print(f"[CONFIRM_RESET] Email: {email}, Token: {token[:20] + '...' if token else None}")
    
    if not email or not token:
        flash('Email e token são obrigatórios.', 'error')
        return redirect(url_for('auth.forgot_password'))
    
    # Verificar se o email existe na base de dados
    try:
        from modules.usuarios.routes import get_users_table
        users_table = get_users_table()
        user_check = supabase_admin.table(users_table).select('*').eq('email', email).execute()
        
        if not user_check.data:
            print(f"[CONFIRM_RESET] Email {email} não encontrado")
            flash('Email não encontrado.', 'error')
            return render_template('reset_password_confirm.html', token=token)
        
        user_data = user_check.data[0]
        if not user_data.get('is_active', True):
            print(f"[CONFIRM_RESET] Usuário {email} está inativo")
            flash('Esta conta está desativada.', 'error')
            return render_template('reset_password_confirm.html', token=token)
        
        print(f"[CONFIRM_RESET] Email confirmado: {email}")
        
        # Armazenar informações na sessão para permitir o reset
        session['reset_user_email'] = email
        session['reset_user_id'] = user_data['id']
        session['reset_token_confirmed'] = token
        session['reset_method'] = 'email_confirmed'
        
        # Limpar tokens temporários
        session.pop('reset_token_temp', None)
        session.pop('reset_type_temp', None)
        
        flash('Email confirmado! Defina sua nova senha.', 'success')
        return render_template('reset_password.html', user_email=email)
        
    except Exception as e:
        print(f"[CONFIRM_RESET] Erro ao confirmar email: {str(e)}")
        flash('Erro interno. Tente novamente.', 'error')
        return render_template('reset_password_confirm.html', token=token)

@bp.route('/api/test-password-reset', methods=['POST'])
def test_password_reset():
    """Endpoint de teste para recuperação de senha (apenas para desenvolvimento)"""
    api_bypass_key = os.getenv('API_BYPASS_KEY')
    request_api_key = request.headers.get('X-API-Key')
    
    if not api_bypass_key or request_api_key != api_bypass_key:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({'error': 'Email é obrigatório'}), 400
        
        # Verificar se email existe
        from modules.usuarios.routes import get_users_table
        users_table = get_users_table()
        user_check = supabase_admin.table(users_table).select('email, is_active').eq('email', email).execute()
        
        result = {
            'email': email,
            'user_exists': bool(user_check.data),
            'is_active': user_check.data[0].get('is_active', False) if user_check.data else False,
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/redirect-after-login')
@login_required
def redirect_after_login():
    """Redireciona o usuário para a página apropriada baseada no seu perfil"""
    try:
        user = session.get('user', {})
        perfis_json = user.get('perfis_json', [])
        
        print(f"[REDIRECT] Redirecionando usuário: {user.get('email')}")
        print(f"[REDIRECT] Perfis: {perfis_json}")
        
        # Se tem perfil financeiro, redireciona para dashboard financeiro
        perfis_financeiros = ['financeiro_completo', 'admin_financeiro', 'financeiro']
        if any(perfil in perfis_financeiros for perfil in perfis_json):
            print(f"[REDIRECT] Usuário tem perfil financeiro - redirecionando para dashboard financeiro")
            return redirect(url_for('fin_dashboard_executivo.index'))
        
        # Se tem perfil admin, redireciona para dashboard de importações
        if user.get('role') == 'admin':
            print(f"[REDIRECT] Usuário admin - redirecionando para dashboard executivo")
            return redirect(url_for('dashboard_executivo.index'))
        
        # Para outros casos, redireciona para o menu
        print(f"[REDIRECT] Redirecionamento padrão - menu principal")
        return redirect(url_for('menu.menu_home'))
        
    except Exception as e:
        print(f"[REDIRECT] Erro no redirecionamento: {str(e)}")
        # Em caso de erro, redireciona para o menu
        return redirect(url_for('menu.menu_home'))
