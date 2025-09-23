from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import check_password_hash
from functools import wraps
from extensions import supabase, supabase_admin
from datetime import datetime
import requests
import json
import os
import re  # para normalização de CNPJ
from services.data_cache import data_cache
from services.auth_logging import safe_log_login_success, safe_log_login_failure, safe_log_logout, safe_log_access_denied

bp = Blueprint('auth', __name__)

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
                return f(*args, **kwargs)
        
        # Só usar bypass se NÃO existe sessão válida
        api_bypass_key = os.getenv('API_BYPASS_KEY')
        request_api_key = request.headers.get('X-API-Key')
        
        print(f"[AUTH DEBUG] Sessão inválida/inexistente, verificando bypass")
        print(f"[AUTH DEBUG] API_BYPASS_KEY configurada: {bool(api_bypass_key)}")
        print(f"[AUTH DEBUG] X-API-Key recebida: {bool(request_api_key)}")
        print(f"[AUTH DEBUG] Chaves são iguais: {api_bypass_key == request_api_key}")
        
        if api_bypass_key and request_api_key == api_bypass_key:
            print(f"[AUTH] Bypass de API detectado - criando sessão temporária")
            # Criar uma sessão temporária para o bypass com UUID válido
            session['user'] = {
                'id': '00000000-0000-0000-0000-000000000000',  # UUID válido para bypass
                'email': 'api@bypass.com',
                'role': 'admin',  # Acesso total para bypass
                'name': 'API Bypass',
                'user_companies': []  # Admin vê todas as empresas
            }
            session['created_at'] = datetime.now().timestamp()
            session['last_activity'] = datetime.now().timestamp()
            return f(*args, **kwargs)
        
        # Se não tem sessão válida nem bypass, redirecionar para login
        print(f"[AUTH] Redirecionando para login - sem sessão válida nem bypass")
        return redirect(url_for('auth.login'))
        
    return decorated_function

def role_required(roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Primeiro verificar se há sessão válida
            if 'user' in session and session.get('user') and isinstance(session['user'], dict):
                user_data = session['user']
                
                # Se o role existe e tem permissão, usar sessão existente
                if user_data.get('role') and user_data['role'] in roles:
                    print(f"[AUTH] Acesso autorizado via sessão para role: {user_data['role']}")
                    return f(*args, **kwargs)
                
                # Se tem sessão mas role insuficiente
                if user_data.get('role'):
                    print(f"[AUTH] Acesso negado - role {user_data['role']} não autorizado para {roles}")
                    flash('Acesso não autorizado.', 'error')
                    return redirect(url_for('menu.menu_home'))  # Redirect to menu instead of non-existent endpoint
            
            # Só usar bypass se não há sessão válida ou role válido
            api_bypass_key = os.getenv('API_BYPASS_KEY')
            if api_bypass_key and request.headers.get('X-API-Key') == api_bypass_key:
                print(f"[AUTH] Bypass de API detectado - permitindo acesso de role sem verificação")
                return f(*args, **kwargs)
            
            # Se não tem sessão válida nem bypass, redirecionar para login
            print(f"[AUTH] Redirecionando para login - sem sessão válida ou autorização")
            return redirect(url_for('auth.login'))
            
        return decorated_function
    return decorator

# Função removida para otimização de performance do login
# A atualização de importações será feita em background ou via cron job
# def update_importacoes_processos(): - REMOVIDO

@bp.route('/test-connection')
def test_connection():
    try:
        # Testar conexão com o Supabase usando cliente admin para evitar problemas de RLS
        response = supabase_admin.table('users').select('*').limit(1).execute()
        return jsonify({
            'status': 'success',
            'message': 'Conexão com Supabase estabelecida com sucesso!',
            'data': response.data
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Erro ao conectar com Supabase: {str(e)}',
            'error_type': str(type(e))
        }), 500

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')
        
        try:
            # Autenticar usuário usando o cliente Supabase
            auth_response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": senha
            })
            
            if auth_response.user:
                user_id = auth_response.user.id
                # Armazenar JWT para RLS e configurar supabase client
                # Session object não é subscriptable, usar atributo
                session['access_token'] = getattr(auth_response.session, 'access_token', None)
                # Ajustar supabase client para usar token do usuário (RLS)
                try:
                    supabase.auth.set_session(auth_response.session)
                except Exception:
                    pass
                
                # Buscar dados do usuário na tabela users com uma única consulta
                user_data = supabase_admin.table('users').select('id, email, role, name').eq('id', user_id).single().execute()
                
                if user_data.data:
                    user = user_data.data
                    
                    # Inicializar dados básicos
                    agent_status = {
                        'is_active': True,  # Padrão True para roles não-cliente
                        'numero': None,
                        'aceite_termos': False
                    }
                    user_companies = []
                    
                    # Verificar dados do agente apenas se for cliente_unique
                    if user.get('role') == 'cliente_unique':
                        try:
                            # Consulta otimizada - buscar apenas campos necessários
                            agent_data = supabase_admin.table('clientes_agentes')\
                                .select('empresa, usuario_ativo, numero, aceite_termos')\
                                .eq('user_id', user_id)\
                                .execute()
                            
                            if agent_data.data:
                                is_user_active = False
                                
                                # Processar dados do agente em um único loop
                                for agent in agent_data.data:
                                    # Verificar se usuário está ativo
                                    agent_active = agent.get('usuario_ativo')
                                    if agent_active is True or agent_active is None:  # None = ativo por padrão
                                        is_user_active = True
                                    
                                    # Processar empresas
                                    if agent.get('empresa'):
                                        companies = agent['empresa']
                                        if isinstance(companies, str):
                                            try:
                                                # Tentar converter string para lista
                                                companies = eval(companies) if companies.startswith('[') else [companies]
                                            except:
                                                companies = [companies]
                                        user_companies.extend(companies)
                                
                                # Remover duplicatas
                                user_companies = list(set(user_companies)) if user_companies else []
                                print(f"[AUTH] Empresas antes da normalização: {user_companies}")
                                
                                # Normalizar CNPJs para dígitos puros
                                user_companies = [re.sub(r'\D', '', c) for c in user_companies]
                                print(f"[AUTH] Empresas após normalização: {user_companies}")
                                
                                # Atualizar status do agente
                                first_agent = agent_data.data[0]
                                agent_status.update({
                                    'is_active': is_user_active,
                                    'numero': first_agent.get('numero'),
                                    'aceite_termos': any(agent.get('aceite_termos', False) for agent in agent_data.data)
                                })
                                
                                # Verificar se usuário está desativado
                                if not is_user_active:
                                    # Log de acesso negado
                                    safe_log_access_denied(f'Usuário desativado: {email}')
                                    flash('Seu acesso está desativado. Entre em contato com o suporte.', 'error')
                                    return redirect(url_for('auth.acesso_negado'))
                        except Exception as agent_error:
                            print(f"[AUTH] Erro ao buscar dados do agente: {agent_error}")
                            # Em caso de erro, permitir login mas com dados limitados
                            pass
                    
                    # Configurar sessão de forma otimizada
                    session.permanent = True
                    now_timestamp = datetime.now().timestamp()
                    
                    session.update({
                        'user': {
                            'id': user_id,
                            'email': user.get('email'),
                            'name': user.get('name'),
                            'role': user.get('role'),
                            'agent_status': agent_status,
                            'user_companies': user_companies
                        },
                        'created_at': now_timestamp,
                        'last_activity': now_timestamp,
                        'permissions_cache': {},  # Cache para otimizar verificações futuras
                        'data_loading_status': 'loading'  # Status do carregamento de dados
                    })
                    
                    # Carregar perfis do usuário
                    print(f"[AUTH] 🔄 Iniciando carregamento de perfis...")
                    try:
                        from services.user_perfis_loader import load_user_perfis
                        print(f"[AUTH] Carregando perfis para usuário {user_id}")
                        user_perfis_info = load_user_perfis(user_id)
                        session['user']['user_perfis_info'] = user_perfis_info
                        print(f"[AUTH] ✅ {len(user_perfis_info)} perfis carregados na sessão")
                        
                        # Debug dos perfis carregados
                        for perfil in user_perfis_info:
                            print(f"[AUTH]   📋 Perfil: {perfil.get('perfil_nome')} ({len(perfil.get('modulos', []))} módulos)")
                    except Exception as perfis_error:
                        print(f"[AUTH] ⚠️ Erro ao carregar perfis: {perfis_error}")
                        import traceback
                        traceback.print_exc()
                        session['user']['user_perfis_info'] = []
                    
                    # Pré-carregar dados em background
                    try:
                        print(f"[AUTH] Iniciando pré-carregamento de dados para usuário {user_id}")
                        session['data_loading_status'] = 'loading'
                        session['data_loading_step'] = 'Carregando dados do ano atual...'
                        
                        # Pré-carregar dados APENAS no cache do servidor (não na sessão)
                        raw_data = data_cache.preload_user_data(
                            user_id=user_id,
                            user_role=user.get('role'),
                            user_companies=user_companies
                        )
                        
                        # NÃO armazenar na sessão (muito grande para cookies)
                        # Os dados ficam apenas no cache do servidor
                        session['data_loading_status'] = 'completed'
                        session['data_loading_step'] = 'Dados carregados com sucesso!'
                        session['cache_ready'] = True  # Flag para indicar que o cache está pronto
                        print(f"[AUTH] Pré-carregamento concluído para usuário {user_id} - {len(raw_data)} registros em cache")
                        
                    except Exception as preload_error:
                        print(f"[AUTH] Erro no pré-carregamento: {preload_error}")
                        session['data_loading_status'] = 'error'
                        session['data_loading_step'] = 'Erro ao carregar dados, mas você pode continuar'
                        session['cache_ready'] = False
                    
                    flash('Login realizado com sucesso!', 'success')
                    
                    # Log de login bem-sucedido
                    safe_log_login_success({
                        'id': user_id,
                        'email': user.get('email'),
                        'name': user.get('name'),
                        'role': user.get('role')
                    })
                    
                    # Redirecionar baseado no perfil do usuário
                    return redirect(url_for('auth.redirect_after_login'))
                else:
                    flash('Usuário não encontrado na base de dados.', 'error')
                    # Log de falha no login
                    safe_log_login_failure(email, 'Usuário não encontrado na base de dados')
            else:
                flash('Email ou senha inválidos.', 'error')
                # Log de falha no login
                safe_log_login_failure(email, 'Email ou senha inválidos')
                
        except Exception as e:
            error_message = str(e)
            print(f"[AUTH] Erro no login: {error_message}")
            
            if "Invalid login credentials" in error_message:
                flash('Email ou senha inválidos.', 'error')
                safe_log_login_failure(email, 'Email ou senha inválidos')
            elif "timeout" in error_message.lower():
                flash('Erro de conexão. Tente novamente em alguns instantes.', 'error')
                safe_log_login_failure(email, 'Erro de conexão - timeout')
            else:
                flash('Erro interno. Tente novamente.', 'error')
                safe_log_login_failure(email, f'Erro interno: {error_message}')
    
    return render_template('auth/login.html')

@bp.route('/api/preload-data', methods=['POST'])
@login_required
def preload_data():
    """API para pre-carregar dados do usuário"""
    try:
        # Pre-carrega os dados do usuário
        user_data = session.get('user', {})
        user_id = user_data.get('id')
        
        if not user_id:
            return jsonify({'success': False, 'error': 'Usuário não identificado'})
            
        # Executa o pre-loading
        cache_data = data_cache.preload_user_data(
            user_id=user_id,
            user_role=user_data.get('role'),
            user_companies=user_data.get('user_companies', [])
        )
        
        # NÃO armazenar na sessão (muito grande para cookies)
        # Os dados ficam apenas no cache do servidor
        session['cache_ready'] = True if cache_data else False
        session['data_loaded'] = True
        print(f"[AUTH API] Cache atualizado: {len(cache_data) if cache_data else 0} registros")
        session['data_load_time'] = datetime.now().isoformat()
        
        return jsonify({
            'success': True, 
            'message': 'Dados carregados com sucesso',
            'redirect_url': url_for('menu.menu_home')
        })
        
    except Exception as e:
        print(f"Erro ao pre-carregar dados: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/logout')
def logout():
    # Capturar dados do usuário antes de limpar a sessão
    user_email = None
    if 'user' in session and session['user']:
        user_email = session['user'].get('email')
    
    # Log de logout
    safe_log_logout(user_email)
    
    session.clear()
    flash('Logout realizado com sucesso!', 'success')
    return redirect(url_for('auth.login'))

# Rota para debug da tabela clientes_agentes
@bp.route('/debug-agentes')
def debug_agentes():
    """Rota temporária para debugar a tabela clientes_agentes"""
    try:
        # Buscar todos os registros
        all_data = supabase.table('clientes_agentes').select('*').execute()
        
        debug_info = {
            'total_registros': len(all_data.data) if all_data.data else 0,
            'registros': []
        }
        
        if all_data.data:
            for record in all_data.data:
                debug_info['registros'].append({
                    'user_id': record.get('user_id'),
                    'email': record.get('email'),
                    'usuario_usuario_ativo': f"{record.get('usuario_usuario_ativo')} ({type(record.get('usuario_usuario_ativo'))})",
                    'aceite_termos': f"{record.get('aceite_termos')} ({type(record.get('aceite_termos'))})",
                    'numero': record.get('numero'),
                    'empresa': record.get('empresa')
                })
        
        return jsonify(debug_info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/corrigir-user-ids')
def corrigir_user_ids():
    """Rota temporária para corrigir user_ids"""
    try:
        users = supabase_admin.table('users').select('*').execute()
        corrigidos = 0
        
        for user in users.data:
            if user.get('role') == 'cliente_unique':
                agent = supabase.table('clientes_agentes').select('*').eq('user_id', user['id']).execute()
                
                if not agent.data:
                    agent_by_email = supabase.table('clientes_agentes').select('*').eq('email', user['email']).execute()
                    
                    if agent_by_email.data:
                        supabase.table('clientes_agentes').update({
                            'user_id': user['id']
                        }).eq('email', user['email']).execute()
                        corrigidos += 1
        
        return jsonify({
            'success': True,
            'message': f'{corrigidos} registros corrigidos'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/acesso-negado')
def acesso_negado():
    """Página para usuários com acesso negado/desativado"""
    # Log de acesso à página de acesso negado
    safe_log_access_denied('Acesso à página de acesso negado')
    return render_template('auth/acesso_negado.html')
