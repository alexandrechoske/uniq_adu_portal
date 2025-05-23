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
                    
                    # Configurar sessão
                    session['user'] = {
                        'id': user['id'],
                        'email': user['email'],
                        'nome': user['nome'],
                        'role': user['role']
                    }
                    
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