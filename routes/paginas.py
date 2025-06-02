from flask import Blueprint, jsonify, render_template, request, redirect, url_for, flash, session
from extensions import supabase
from functools import wraps
from permissions import get_user_permissions, check_permission
import json

bp = Blueprint('paginas', __name__, url_prefix='/paginas')

def admin_required(f):
    """
    Decorador legado que chama o novo check_permission - mantido para compatibilidade
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Verificar se o usuário está logado
        if not session.get('user'):
            flash('Faça login para acessar esta página.', 'error')
            return redirect(url_for('auth.login'))
            
        # Verificar se é admin
        if session['user']['role'] != 'admin':
            flash('Acesso restrito a administradores.', 'error')
            return redirect(url_for('dashboard.index'))
            
        # Buscar permissões
        permissions = get_user_permissions(session['user']['id'], 'admin')
        session['permissions'] = permissions
        
        # Passar as permissões para a função decorada
        kwargs['permissions'] = permissions
        
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/api', methods=['GET'])
def get_paginas():
    """
    Retorna as páginas do portal baseado nas permissões do usuário
    """
    try:
        # Verificar se o usuário está logado
        if not session.get('user'):
            return jsonify({
                'status': 'error',
                'message': 'Usuário não autenticado',
                'code': 'auth_required'
            }), 401
        
        # Obter o papel do usuário da sessão
        user_role = session['user']['role']
        user_id = session['user']['id']
        
        # Buscar todas as páginas
        response = supabase.table('paginas_portal').select('*').order('ordem').execute()
        
        # Filtrar as páginas no servidor baseado nas permissões do usuário
        if response.data:
            filtered_pages = []
            
            # Administradores têm acesso a todas as páginas
            if user_role == 'admin':
                filtered_pages = response.data
                print(f"[DEBUG] Usuário admin: retornando todas {len(filtered_pages)} páginas")
            else:
                for page in response.data:
                    if page.get('roles') and isinstance(page['roles'], list) and user_role in page['roles']:
                        filtered_pages.append(page)
                print(f"[DEBUG] Usuário {user_role}: retornando {len(filtered_pages)} páginas")
            
            return jsonify({
                'status': 'success',
                'data': filtered_pages
            })
        else:
            print("[DEBUG] Nenhuma página encontrada na tabela paginas_portal")
            return jsonify({
                'status': 'success',
                'data': []
            })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@bp.route('/', methods=['GET'])
@admin_required
def index():
    """
    Página de administração das páginas do portal
    """
    try:
        response = supabase.table('paginas_portal').select('*').order('ordem').execute()
        return render_template('paginas/index.html', paginas=response.data)
    except Exception as e:
        flash(f'Erro ao carregar páginas: {str(e)}', 'error')
        return redirect(url_for('dashboard.index'))

@bp.route('/toggle/<id>', methods=['POST'])
@admin_required
def toggle_page(id):
    """
    Ativa/Desativa uma página do portal
    """
    try:
        # Primeiro buscar a página para saber o status atual
        page = supabase.table('paginas_portal').select('flg_ativo').eq('id', id).execute()
        
        if not page.data:
            flash('Página não encontrada.', 'error')
            return redirect(url_for('paginas.index'))
        
        # Inverter o status
        new_status = not page.data[0]['flg_ativo']
        
        # Atualizar o status
        supabase.table('paginas_portal').update({'flg_ativo': new_status}).eq('id', id).execute()
        
        status_text = 'ativada' if new_status else 'desativada'
        flash(f'Página {status_text} com sucesso!', 'success')
    except Exception as e:
        flash(f'Erro ao alterar status da página: {str(e)}', 'error')
    
    return redirect(url_for('paginas.index'))

@bp.route('/edit/<id>', methods=['GET', 'POST'])
@admin_required
def edit_page(id):
    """
    Edita uma página do portal
    """
    try:
        if request.method == 'POST':
            # Capturar dados do formulário
            nome_pagina = request.form.get('nome_pagina')
            roles = request.form.getlist('roles')
            flg_ativo = True if request.form.get('flg_ativo') == 'on' else False
            ordem = request.form.get('ordem', type=int)
            mensagem_manutencao = request.form.get('mensagem_manutencao')
            
            # Validar dados
            if not nome_pagina:
                flash('Nome da página é obrigatório.', 'error')
                return redirect(url_for('paginas.edit_page', id=id))
            
            if not roles:
                flash('Pelo menos um perfil deve ser selecionado.', 'error')
                return redirect(url_for('paginas.edit_page', id=id))
            
            # Atualizar página
            supabase.table('paginas_portal').update({
                'nome_pagina': nome_pagina,
                'roles': roles,
                'flg_ativo': flg_ativo,
                'ordem': ordem,
                'mensagem_manutencao': mensagem_manutencao
            }).eq('id', id).execute()
            
            flash('Página atualizada com sucesso!', 'success')
            return redirect(url_for('paginas.index'))
        else:
            # Buscar página para edição
            response = supabase.table('paginas_portal').select('*').eq('id', id).execute()
            
            if not response.data:
                flash('Página não encontrada.', 'error')
                return redirect(url_for('paginas.index'))
            
            return render_template('paginas/edit.html', pagina=response.data[0])
    except Exception as e:
        flash(f'Erro ao editar página: {str(e)}', 'error')
        return redirect(url_for('paginas.index'))

@bp.route('/create', methods=['GET', 'POST'])
@admin_required
def create_page():
    """
    Cria uma nova página do portal
    """
    try:
        if request.method == 'POST':
            # Capturar dados do formulário
            id_pagina = request.form.get('id_pagina')
            nome_pagina = request.form.get('nome_pagina')
            url_rota = request.form.get('url_rota')
            icone = request.form.get('icone')
            roles = request.form.getlist('roles')
            flg_ativo = True if request.form.get('flg_ativo') == 'on' else False
            ordem = request.form.get('ordem', type=int)
            mensagem_manutencao = request.form.get('mensagem_manutencao')
            
            # Validar dados
            if not all([id_pagina, nome_pagina, url_rota, icone]):
                flash('Todos os campos são obrigatórios.', 'error')
                return redirect(url_for('paginas.create_page'))
            
            if not roles:
                flash('Pelo menos um perfil deve ser selecionado.', 'error')
                return redirect(url_for('paginas.create_page'))
            
            # Criar nova página
            supabase.table('paginas_portal').insert({
                'id_pagina': id_pagina,
                'nome_pagina': nome_pagina,
                'url_rota': url_rota,
                'icone': icone,
                'roles': roles,
                'flg_ativo': flg_ativo,
                'ordem': ordem,
                'mensagem_manutencao': mensagem_manutencao
            }).execute()
            
            flash('Página criada com sucesso!', 'success')
            return redirect(url_for('paginas.index'))
        else:
            # Buscar maior ordem para sugerir próxima
            response = supabase.table('paginas_portal').select('ordem').order('ordem', desc=True).limit(1).execute()
            next_ordem = 1
            if response.data:
                next_ordem = response.data[0]['ordem'] + 1
                
            return render_template('paginas/create.html', next_ordem=next_ordem)
    except Exception as e:
        flash(f'Erro ao criar página: {str(e)}', 'error')
        return redirect(url_for('paginas.index'))

@bp.route('/delete/<id>', methods=['POST'])
@admin_required
def delete_page(id):
    """
    Exclui uma página do portal
    """
    try:
        # Verificar se a página existe
        page = supabase.table('paginas_portal').select('id_pagina').eq('id', id).execute()
        
        if not page.data:
            flash('Página não encontrada.', 'error')
            return redirect(url_for('paginas.index'))
        
        # Excluir página
        supabase.table('paginas_portal').delete().eq('id', id).execute()
        
        flash('Página excluída com sucesso!', 'success')
    except Exception as e:
        flash(f'Erro ao excluir página: {str(e)}', 'error')
    
    return redirect(url_for('paginas.index'))

@bp.route('/check-session', methods=['GET'])
def check_session():
    """
    Endpoint para verificar e atualizar o status da sessão
    """
    try:
        # Verificar se o usuário está logado
        if not session.get('user'):
            print("[DEBUG] check-session: Usuário não autenticado")
            return jsonify({
                'status': 'error',
                'message': 'Usuário não autenticado',
                'code': 'auth_required'
            }), 401
        
        # Atualizar informações do usuário usando o novo sistema de permissões
        user_id = session['user']['id']
        user_role = session['user']['role']
        
        # Verificar se temos as informações mínimas necessárias
        if not user_id or not user_role:
            print(f"[DEBUG] check-session: Informações de usuário incompletas: id={user_id}, role={user_role}")
            return jsonify({
                'status': 'error',
                'message': 'Informações de usuário incompletas',
                'code': 'incomplete_session'
            }), 400
          # Buscar permissões atualizadas (função no permissions.py)
        permissions = get_user_permissions(user_id, user_role)
        session['permissions'] = permissions
        
        # Registrar atividade recente
        from datetime import datetime
        session['last_activity'] = datetime.now().timestamp()
        
        # Retornar status da sessão
        return jsonify({
            'status': 'success',
            'message': 'Sessão válida',
            'user': {
                'id': user_id,
                'role': user_role,
                'is_admin': permissions.get('is_admin', False)
            }
        })
    except Exception as e:
        import traceback
        print(f"[DEBUG] Erro em check-session: {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'Erro ao verificar sessão: {str(e)}',
            'code': 'server_error'
        }), 500
        
        # Para clientes_unique, atualizar status do agente na sessão também
        if user_role == 'cliente_unique':
            session['user']['agent_status'] = {
                'is_active': permissions.get('is_active', False),
                'numero': permissions.get('agent_number'),
                'aceite_termos': permissions.get('terms_accepted', False)
            }
            session['user']['user_companies'] = permissions.get('accessible_companies', [])
        
        # Responder com sucesso e incluir as permissões
        return jsonify({
            'status': 'success',
            'message': 'Sessão válida',
            'user_role': user_role,
            'permissions': permissions
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
