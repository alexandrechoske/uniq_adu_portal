from flask import Blueprint, jsonify, render_template, request, redirect, url_for, flash, session
from extensions import supabase
from functools import wraps
import json

bp = Blueprint('paginas', __name__, url_prefix='/paginas')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user') or session['user']['role'] != 'admin':
            flash('Acesso restrito a administradores.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/api', methods=['GET'])
def get_paginas():
    """
    Retorna as páginas do portal baseado nas permissões do usuário
    """
    try:
        response = supabase.table('paginas_portal').select('*').order('ordem').execute()
        return jsonify({
            'status': 'success',
            'data': response.data
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
