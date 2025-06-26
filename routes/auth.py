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
                
                # Buscar dados do usuário na tabela users
                user_data = supabase_admin.table('users').select('*').eq('id', user_id).execute()
                
                if user_data.data:
                    user = user_data.data[0]
                    
                    # Verificar status do agente se for cliente_unique - OTIMIZADO
                    agent_status = {
                        'is_active': True,  # Padrão True para outros roles
                        'numero': None,
                        'aceite_termos': False
                    }
                    
                    # Store user companies for cliente_unique users
                    user_companies = []
                    
                    if user.get('role') == 'cliente_unique':
                        # Get agent data with companies - consulta única otimizada
                        agent_data = supabase_admin.table('clientes_agentes')\
                            .select('empresa, usuario_ativo, numero, aceite_termos')\
                            .eq('user_id', user_id)\
                            .execute()
                        
                        if agent_data.data:
                            # Check if user is active
                            is_user_active = False
                            
                            # Extract companies from all records in a single loop
                            for agent in agent_data.data:
                                # Verificar se o usuário está ativo
                                agent_active = agent.get('usuario_ativo')
                                if agent_active is True:
                                    is_user_active = True
                                elif agent_active is None:
                                    # Para usuários antigos sem o campo definido, assumir como ativo
                                    is_user_active = True
                                
                                if agent.get('empresa'):
                                    # Handle both string and array formats
                                    companies = agent['empresa']
                                    if isinstance(companies, str):
                                        try:
                                            companies = eval(companies)  # Handle string format ["company1", "company2"]
                                        except:
                                            companies = [companies]  # Handle single string format
                                    user_companies.extend(companies)
                            
                            user_companies = list(set(user_companies))  # Remove duplicates
                            
                            # Update agent status
                            agent_status.update({
                                'is_active': is_user_active,  # Use the calculated active status
                                'numero': agent_data.data[0].get('numero'),
                                'aceite_termos': any(agent.get('aceite_termos', False) for agent in agent_data.data)
                            })
                            
                            # Check if user is inactive and prevent login
                            if not is_user_active:
                                flash('Seu acesso está desativado. Entre em contato com o suporte.', 'error')
                                return redirect(url_for('auth.acesso_negado'))
                    
                    # Store user info in session
                    session['user'] = {
                        'id': user_id,
                        'email': user.get('email'),
                        'role': user.get('role'),
                        'agent_status': agent_status,
                        'user_companies': user_companies
                    }
                    
                    # Cache inicial das permissões para evitar consultas repetidas
                    session['permissions_cache'] = {}
                    
                    flash('Login realizado com sucesso!', 'success')
                    return redirect(url_for('dashboard.index'))
                else:
                    flash('Usuário não encontrado na base de dados.', 'error')
            else:
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
    return render_template('auth/acesso_negado.html')
