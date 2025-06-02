from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import check_password_hash
from functools import wraps
from extensions import supabase, supabase_admin
import requests
import json
from permissions import get_user_permissions, check_permission

bp = Blueprint('auth', __name__)

# Decorador simplificado para compatibilidade com código existente (login_required)
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

# Decorador role_required, agora usando o novo sistema de permissões
def role_required(roles):
    """
    Decorador legado que chama o novo check_permission - mantido para compatibilidade
    """
    if isinstance(roles, str):
        roles = [roles]  # Converter string para lista
    
    # Usar o novo decorador
    return check_permission(required_roles=roles)

def update_importacoes_processos():
    try:
        from config import Config
        
        response = requests.post(
            f'{Config.SUPABASE_URL}/functions/v1/att_importacoes-processos',
            headers={
                'Authorization': f'Bearer {Config.SUPABASE_CURL_BEARER}',
                'Content-Type': 'application/json'
            },
            json={'name': 'Functions'}
        )
        return response.status_code == 200
    except:
        return False

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
        
        # Para facilitar as animações, adicionamos um pequeno delay
        import time
        time.sleep(0.5)  # Delay de 0.5 segundos para permitir a animação
        
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
                
                # Call the Supabase function to update importacoes_processos
                print("[DEBUG] Chamando função de atualização de importacoes_processos")
                update_success = update_importacoes_processos()
                print(f"[DEBUG] Atualização de importações: {'sucesso' if update_success else 'falha'}")
                
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
                    
                    # Store user companies for cliente_unique users
                    user_companies = []
                    
                    if user.get('role') == 'cliente_unique':
                        print(f"[DEBUG] Buscando dados de agente para user_id: {user_id}")
                        
                        # Get agent data with companies
                        agent_data = supabase.table('clientes_agentes')\
                            .select('empresa, usuario_ativo, numero, aceite_termos')\
                            .eq('user_id', user_id)\
                            .execute()
                        
                        print(f"[DEBUG] Dados do agente: {agent_data.data}")
                        
                        if agent_data.data:
                            # Extract companies from all records
                            for agent in agent_data.data:
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
                                'is_active': any(agent.get('usuario_ativo', False) for agent in agent_data.data),
                                'numero': agent_data.data[0].get('numero'),
                                'aceite_termos': any(agent.get('aceite_termos', False) for agent in agent_data.data)
                            })
                      # Store user info in session
                    session['user'] = {
                        'id': user_id,
                        'email': user.get('email'),
                        'role': user.get('role'),
                        'agent_status': agent_status,
                        'user_companies': user_companies
                    }
                    
                    # Adicionar permissões à sessão
                    permissions = get_user_permissions(user_id, user.get('role'))
                    session['permissions'] = permissions
                    
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
