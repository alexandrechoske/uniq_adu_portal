from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for, flash
from extensions import supabase, supabase_admin
from routes.auth import login_required
import logging

# Configurar logging
logger = logging.getLogger(__name__)

bp = Blueprint('paginas', __name__, url_prefix='/paginas')

@bp.route('/check-session')
@login_required
def check_session():
    """
    Endpoint para verificação de sessão usado pelo sistema de auto-refresh da OnePage
    Retorna status da sessão atual do usuário
    """
    try:
        # Verificar se o usuário está logado
        if 'user' not in session:
            logger.warning("Tentativa de verificação de sessão sem usuário logado")
            return jsonify({
                'status': 'error',
                'message': 'Usuário não autenticado'
            }), 401
        
        user_data = session.get('user')
        if not user_data:
            logger.warning("Dados do usuário não encontrados na sessão")
            return jsonify({
                'status': 'error',
                'message': 'Dados do usuário não encontrados'
            }), 401
          # Verificar se a sessão ainda é válida
        user_id = user_data.get('id')
        if not user_id:
            logger.warning("ID do usuário não encontrado nos dados da sessão")
            return jsonify({
                'status': 'error',
                'message': 'ID do usuário inválido'
            }), 401
          # Verificar se o usuário ainda existe no banco (verificação opcional para compatibilidade)
        user_exists_in_db = True
        db_user_data = None
        
        try:
            # Usar cliente admin para contornar problemas de RLS
            response = supabase_admin.table('users').select('id, name, email').eq('id', user_id).execute()
            if not response.data or len(response.data) == 0:
                user_exists_in_db = False
                logger.warning(f"Usuário {user_id} não encontrado no banco, mas sessão válida - permitindo acesso")
                # Para usuários que não existem no banco mas têm sessão válida (ex: usuários system),
                # usar dados da sessão em vez de invalidar
            else:
                db_user_data = response.data[0]
                if len(response.data) > 1:
                    logger.warning(f"Múltiplos usuários encontrados para ID {user_id}")
        except Exception as db_error:
            logger.error(f"Erro ao verificar usuário no banco: {str(db_error)}")
            user_exists_in_db = False
            # Em caso de erro de banco, permitir continuar se a sessão local é válida
        # Determinar dados do usuário para resposta
        if user_exists_in_db and db_user_data:
            # Usar dados do banco se disponíveis
            response_user_data = {
                'id': db_user_data.get('id'),
                'nome': db_user_data.get('name'),
                'email': db_user_data.get('email')
            }
        else:
            # Usar dados da sessão se usuário não existe no banco
            response_user_data = {
                'id': user_data.get('id'),
                'nome': user_data.get('name'),
                'email': user_data.get('email')
            }
        
        logger.info(f"Verificação de sessão bem-sucedida para usuário {user_id} (exists_in_db: {user_exists_in_db})")
        return jsonify({
            'status': 'success',
            'message': 'Sessão válida',
            'user': response_user_data
        }), 200
        
    except Exception as e:
        logger.error(f"Erro na verificação de sessão: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Erro interno do servidor'
        }), 500

@bp.route('/api')
@login_required
def get_paginas():
    """
    API para obter lista de páginas do portal
    """
    try:
        logger.info("Iniciando busca de páginas do portal")
        
        # Buscar páginas do portal ordenadas
        response = supabase.table('paginas_portal').select('*').order('ordem').execute()
        
        if not response.data:
            logger.warning("Nenhuma página encontrada na tabela paginas_portal")
            return jsonify({
                'status': 'success',
                'data': [],
                'message': 'Nenhuma página encontrada'
            })
        
        logger.info(f"Encontradas {len(response.data)} páginas do portal")
        return jsonify({
            'status': 'success',
            'data': response.data
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar páginas: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Erro ao buscar páginas: {str(e)}'
        }), 500

@bp.route('/')
@login_required
def index():
    """
    Página principal de gerenciamento de páginas
    """
    try:
        # Buscar páginas existentes
        response = supabase.table('paginas_portal').select('*').order('ordem').execute()
        paginas = response.data if response.data else []
        
        return render_template('paginas/index.html', paginas=paginas)
        
    except Exception as e:
        logger.error(f"Erro ao carregar páginas: {str(e)}")
        flash(f'Erro ao carregar páginas: {str(e)}', 'error')
        return redirect(url_for('dashboard.index'))

@bp.route('/create')
@login_required
def create():
    """
    Página para criar nova página
    """
    return render_template('paginas/create.html')

@bp.route('/edit/<int:pagina_id>')
@login_required
def edit(pagina_id):
    """
    Página para editar página existente
    """
    try:
        response = supabase.table('paginas_portal').select('*').eq('id', pagina_id).execute()
        if not response.data or len(response.data) == 0:
            flash('Página não encontrada', 'error')
            return redirect(url_for('paginas.index'))
        
        pagina = response.data[0]  # Pegar o primeiro resultado
        return render_template('paginas/edit.html', pagina=pagina)
        
    except Exception as e:
        logger.error(f"Erro ao carregar página para edição: {str(e)}")
        flash(f'Erro ao carregar página: {str(e)}', 'error')
        return redirect(url_for('paginas.index'))
