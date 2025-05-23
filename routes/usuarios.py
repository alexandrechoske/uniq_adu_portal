from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from extensions import supabase, supabase_admin
from routes.auth import login_required, role_required
import uuid

bp = Blueprint('usuarios', __name__)

# Lista de roles válidos - atualizada para corresponder às restrições do banco
VALID_ROLES = ['admin', 'interno_unique', 'cliente_unique']  # Removido 'cliente' e adicionado 'cliente_unique'

@bp.route('/usuarios')
@login_required
@role_required(['admin'])
def index():
    users = supabase.table('users').select('*').execute()
    return render_template('usuarios/index.html', users=users.data)

@bp.route('/usuarios/novo', methods=['GET', 'POST'])
@login_required
@role_required(['admin'])
def novo():
    if request.method == 'POST':
        email = request.form.get('email')
        nome = request.form.get('nome')
        senha = request.form.get('senha')
        role = request.form.get('role', 'cliente_unique')  # Alterado o valor padrão
        
        # Validar role
        if role not in VALID_ROLES:
            flash(f'Perfil inválido. Valores permitidos: {", ".join(VALID_ROLES)}', 'error')
            return render_template('usuarios/form.html')
        
        try:
            # Criar usuário no Supabase Auth usando o cliente admin
            auth_response = supabase_admin.auth.admin.create_user({
                "email": email,
                "password": senha,
                "email_confirm": True,
                "user_metadata": {
                    "role": role
                }
            })
            
            if auth_response.user:
                # Criar usuário na tabela users usando o cliente admin
                user_response = supabase_admin.table('users').insert({
                    'id': auth_response.user.id,
                    'email': email,
                    'nome': nome,
                    'role': role
                }).execute()
                
                if user_response.data:
                    flash('Usuário criado com sucesso!', 'success')
                    return redirect(url_for('usuarios.index'))
                else:
                    # Se falhar ao criar na tabela users, remover o usuário do auth
                    supabase_admin.auth.admin.delete_user(auth_response.user.id)
                    flash('Erro ao criar usuário na base de dados.', 'error')
            else:
                flash('Erro ao criar usuário no sistema de autenticação.', 'error')
            
        except Exception as e:
            error_message = str(e)
            print(f"Erro ao criar usuário: {error_message}")  # Debug log
            flash(f'Erro ao criar usuário: {error_message}', 'error')
    
    return render_template('usuarios/form.html')

@bp.route('/usuarios/<id>/editar', methods=['GET', 'POST'])
@login_required
@role_required(['admin'])
def editar(id):
    if request.method == 'POST':
        nome = request.form.get('nome')
        role = request.form.get('role')
        
        # Validar role
        if role not in VALID_ROLES:
            flash(f'Perfil inválido. Valores permitidos: {", ".join(VALID_ROLES)}', 'error')
            return render_template('usuarios/form.html', user={'id': id, 'nome': nome, 'role': role})
        
        try:
            # Atualizar usuário na tabela users usando o cliente admin
            supabase_admin.table('users').update({
                'nome': nome,
                'role': role
            }).eq('id', id).execute()
            
            flash('Usuário atualizado com sucesso!', 'success')
            return redirect(url_for('usuarios.index'))
            
        except Exception as e:
            flash(f'Erro ao atualizar usuário: {str(e)}', 'error')
    
    user = supabase.table('users').select('*').eq('id', id).execute()
    return render_template('usuarios/form.html', user=user.data[0] if user.data else None)

@bp.route('/usuarios/<id>/excluir', methods=['POST'])
@login_required
@role_required(['admin'])
def excluir(id):
    try:
        # Excluir usuário do Supabase Auth
        supabase_admin.auth.admin.delete_user(id)
        
        # Excluir usuário da tabela users
        supabase_admin.table('users').delete().eq('id', id).execute()
        
        flash('Usuário excluído com sucesso!', 'success')
    except Exception as e:
        flash(f'Erro ao excluir usuário: {str(e)}', 'error')
    
    return redirect(url_for('usuarios.index'))

@bp.route('/debug/create-test-user')
def create_test_user():
    try:
        # Criar usuário no Auth
        user = supabase_admin.auth.admin.create_user({
            "email": "system@uniqueaduaneira.com.br",
            "password": "admin123",
            "email_confirm": True
        })
        
        # Criar registro na tabela users
        user_data = {
            "id": user.user.id,
            "email": user.user.email,
            "nome": "System Admin",
            "role": "admin"
        }
        
        result = supabase_admin.table('users').insert(user_data).execute()
        
        flash('Usuário de teste criado com sucesso!', 'success')
        return redirect(url_for('auth.login'))
    except Exception as e:
        flash(f'Erro ao criar usuário de teste: {str(e)}', 'error')
        return redirect(url_for('auth.login')) 