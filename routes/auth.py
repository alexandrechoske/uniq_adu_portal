from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import check_password_hash
from functools import wraps
from extensions import supabase, supabase_admin
from datetime import datetime
import requests
import json

bp = Blueprint('auth', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Verificar se existe usuário na sessão e se tem os dados mínimos necessários
        if 'user' not in session or not session.get('user') or not isinstance(session['user'], dict):
            print(f"[AUTH] Redirecionando para login - usuário não encontrado na sessão")
            return redirect(url_for('auth.login'))
        
        # Verificar se os dados essenciais estão presentes
        user_data = session['user']
        required_fields = ['id', 'email', 'role']
        missing_fields = [field for field in required_fields if not user_data.get(field)]
        
        if missing_fields:
            print(f"[AUTH] Sessão corrompida - campos faltantes: {missing_fields}")
            session.clear()
            return redirect(url_for('auth.login'))
        
        # Verificar integridade da sessão
        if 'created_at' not in session:
            print(f"[AUTH] Sessão sem timestamp de criação, recriando...")
            session['created_at'] = datetime.now().timestamp()
            session.permanent = True
        
        # Renovar timestamp de atividade
        session['last_activity'] = datetime.now().timestamp()
        session.permanent = True  # Garantir que a sessão permaneça permanente
        
        return f(*args, **kwargs)
    return decorated_function

def role_required(roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Verificar se existe usuário na sessão
            if 'user' not in session or not session.get('user') or not isinstance(session['user'], dict):
                print(f"[AUTH] Redirecionando para login - usuário não encontrado na sessão")
                return redirect(url_for('auth.login'))
            
            user_data = session['user']
            
            # Verificar se o role existe
            if not user_data.get('role'):
                print(f"[AUTH] Role não encontrado na sessão")
                session.clear()
                return redirect(url_for('auth.login'))
            
            # Verificar se o role tem permissão
            if user_data['role'] not in roles:
                flash('Acesso não autorizado.', 'error')
                return redirect(url_for('dashboard.index'))
            
            # Verificar integridade da sessão
            if 'created_at' not in session:
                print(f"[AUTH] Sessão sem timestamp de criação, recriando...")
                session['created_at'] = datetime.now().timestamp()
                session.permanent = True
            
            # Renovar timestamp de atividade
            session['last_activity'] = datetime.now().timestamp()
            session.permanent = True  # Garantir que a sessão permaneça permanente
            
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
                                
                                # Atualizar status do agente
                                first_agent = agent_data.data[0]
                                agent_status.update({
                                    'is_active': is_user_active,
                                    'numero': first_agent.get('numero'),
                                    'aceite_termos': any(agent.get('aceite_termos', False) for agent in agent_data.data)
                                })
                                
                                # Verificar se usuário está desativado
                                if not is_user_active:
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
                        'permissions_cache': {}  # Cache para otimizar verificações futuras
                    })
                    
                    flash('Login realizado com sucesso!', 'success')
                    return redirect(url_for('dashboard.index'))
                else:
                    flash('Usuário não encontrado na base de dados.', 'error')
            else:
                flash('Email ou senha inválidos.', 'error')
                
        except Exception as e:
            error_message = str(e)
            print(f"[AUTH] Erro no login: {error_message}")
            
            if "Invalid login credentials" in error_message:
                flash('Email ou senha inválidos.', 'error')
            elif "timeout" in error_message.lower():
                flash('Erro de conexão. Tente novamente em alguns instantes.', 'error')
            else:
                flash('Erro interno. Tente novamente.', 'error')
    
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
