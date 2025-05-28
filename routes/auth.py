from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import check_password_hash
from functools import wraps
from extensions import supabase, supabase_admin
import requests
import json

bp = Blueprint('auth', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user' not in session:
                return redirect(url_for('auth.login'))
            if session['user']['role'] not in roles:
                flash('Acesso não autorizado.', 'error')
                return redirect(url_for('dashboard.index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@bp.route('/test-connection')
def test_connection():
    try:
        # Testar conexão com o Supabase
        response = supabase.table('users').select('*').limit(1).execute()
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
        print(f"[DEBUG] Tentando login para email: {email}")
        
        try:
            # Autenticar usuário usando o cliente Supabase
            print("[DEBUG] Iniciando autenticação com Supabase...")
            auth_response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": senha
            })
            print(f"[DEBUG] Resposta da autenticação: {auth_response}")
            
            if auth_response.user:
                user_id = auth_response.user.id
                print(f"[DEBUG] Usuário autenticado com ID: {user_id}")
                
                # Buscar dados do usuário na tabela users
                print("[DEBUG] Buscando dados do usuário na tabela users...")
                user_data = supabase.table('users').select('*').eq('id', user_id).execute()
                print(f"[DEBUG] Dados do usuário: {user_data}")
                
                if user_data.data:
                    user = user_data.data[0]
                    print(f"[DEBUG] Role do usuário: {user['role']}")
                    
                    # Verificar status do agente se for cliente_unique
                    agent_status = {
                        'is_active': False,
                        'numero': None,
                        'aceite_termos': False
                    }
                    
                    if user.get('role') == 'cliente_unique':
                        print(f"[DEBUG] Buscando dados de agente para user_id: {user_id}")
                        
                        # Primeiro, vamos ver todos os registros para debug
                        all_agents = supabase.table('clientes_agentes').select('*').execute()
                        print(f"[DEBUG] TODOS os registros de clientes_agentes: {all_agents.data}")
                        
                        # Buscar especificamente por user_id
                        agent_data = supabase.table('clientes_agentes').select('*').eq('user_id', user_id).execute()
                        print(f"[DEBUG] Query executada: SELECT * FROM clientes_agentes WHERE user_id = '{user_id}'")
                        print(f"[DEBUG] Dados do agente brutos: {agent_data.data}")
                        print(f"[DEBUG] Número de registros encontrados: {len(agent_data.data) if agent_data.data else 0}")
                        
                        if agent_data.data and len(agent_data.data) > 0:
                            agent = agent_data.data[0]
                            print(f"[DEBUG] Registro do agente encontrado: {agent}")
                            print(f"[DEBUG] Todas as chaves disponíveis: {list(agent.keys())}")
                            
                            # Debug detalhado dos campos
                            usuario_ativo_raw = agent.get('usuario_ativo')
                            aceite_termos_raw = agent.get('aceite_termos')
                            numero_raw = agent.get('numero')
                            
                            print(f"[DEBUG] usuario_ativo RAW: {usuario_ativo_raw} (tipo: {type(usuario_ativo_raw)})")
                            print(f"[DEBUG] aceite_termos RAW: {aceite_termos_raw} (tipo: {type(aceite_termos_raw)})")
                            print(f"[DEBUG] numero RAW: {numero_raw} (tipo: {type(numero_raw)})")
                            
                            # Conversão mais robusta para booleanos
                            def convert_to_bool(value):
                                if value is None:
                                    return False
                                if isinstance(value, bool):
                                    return value
                                if isinstance(value, str):
                                    return value.lower() in ['true', '1', 't', 'yes', 'y']
                                if isinstance(value, (int, float)):
                                    return bool(value)
                                return False
                            
                            is_active = convert_to_bool(usuario_ativo_raw)
                            aceite_termos = convert_to_bool(aceite_termos_raw)
                            
                            print(f"[DEBUG] usuario_ativo CONVERTIDO: {is_active}")
                            print(f"[DEBUG] aceite_termos CONVERTIDO: {aceite_termos}")
                            
                            agent_status = {
                                'is_active': is_active,
                                'numero': numero_raw,
                                'aceite_termos': aceite_termos
                            }
                            
                            print(f"[DEBUG] Status final do agente: {agent_status}")
                        else:
                            print(f"[DEBUG] NENHUM registro encontrado para user_id: {user_id}")
                            print("[DEBUG] Vamos tentar buscar por email como fallback...")
                            
                            # Fallback: buscar por email se não encontrar por user_id
                            agent_data_email = supabase.table('clientes_agentes').select('*').eq('email', email).execute()
                            print(f"[DEBUG] Busca por email: {agent_data_email.data}")
                            
                            if agent_data_email.data:
                                agent = agent_data_email.data[0]
                                print(f"[DEBUG] Encontrado por email: {agent}")
                                # Atualizar o user_id no registro se necessário
                                supabase.table('clientes_agentes').update({'user_id': user_id}).eq('email', email).execute()
                                print(f"[DEBUG] user_id atualizado no registro")
                                
                                # Processar os dados
                                def convert_to_bool(value):
                                    if value is None:
                                        return False
                                    if isinstance(value, bool):
                                        return value
                                    if isinstance(value, str):
                                        return value.lower() in ['true', '1', 't', 'yes', 'y']
                                    if isinstance(value, (int, float)):
                                        return bool(value)
                                    return False
                                
                                is_active = convert_to_bool(agent.get('usuario_ativo'))
                                aceite_termos = convert_to_bool(agent.get('aceite_termos'))
                                
                                agent_status = {
                                    'is_active': is_active,
                                    'numero': agent.get('numero'),
                                    'aceite_termos': aceite_termos
                                }
                            else:
                                print(f"[DEBUG] NENHUM registro encontrado nem por user_id nem por email")
                    
                    # Configurar sessão
                    session['user'] = {
                        'id': user['id'],
                        'email': user['email'],
                        'nome': user['nome'],
                        'role': user['role'],
                        'agent_status': agent_status
                    }
                    
                    print(f"[FINAL DEBUG] Session user: {session['user']}")
                    print("[DEBUG] Login realizado com sucesso!")
                    flash('Login realizado com sucesso!', 'success')
                    return redirect(url_for('dashboard.index'))
                else:
                    print("[DEBUG] Usuário não encontrado na tabela users")
                    flash('Usuário não encontrado na base de dados.', 'error')
            else:
                print("[DEBUG] Falha na autenticação")
                flash('Email ou senha inválidos.', 'error')
                
        except Exception as e:
            error_message = str(e)
            print(f"[DEBUG] Erro detalhado: {error_message}")
            print(f"[DEBUG] Tipo do erro: {type(e)}")
            if "Invalid login credentials" in error_message:
                flash('Email ou senha inválidos.', 'error')
            else:
                flash(f'Erro ao fazer login: {error_message}', 'error')
    
    return render_template('auth/login.html')

@bp.route('/logout')
def logout():
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
                    'usuario_ativo': f"{record.get('usuario_ativo')} ({type(record.get('usuario_ativo'))})",
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
        users = supabase.table('users').select('*').execute()
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
