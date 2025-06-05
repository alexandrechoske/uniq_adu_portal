from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for, flash
from extensions import supabase
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
        
        # Opcional: Verificar se o usuário ainda existe no banco
        try:
            response = supabase.table('usuarios').select('id, nome, email, ativo').eq('id', user_id).single().execute()
            if not response.data or not response.data.get('ativo'):
                logger.warning(f"Usuário {user_id} não encontrado ou inativo")
                return jsonify({
                    'status': 'error',
                    'message': 'Usuário inativo ou inexistente'
                }), 401
        except Exception as db_error:
            logger.error(f"Erro ao verificar usuário no banco: {str(db_error)}")
            # Em caso de erro de banco, permitir continuar se a sessão local é válida
            pass
        
        logger.info(f"Verificação de sessão bem-sucedida para usuário {user_id}")
        return jsonify({
            'status': 'success',
            'message': 'Sessão válida',
            'user': {
                'id': user_data.get('id'),
                'nome': user_data.get('nome'),
                'email': user_data.get('email')
            }
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
        response = supabase.table('paginas_portal').select('*').eq('id', pagina_id).single().execute()
        if not response.data:
            flash('Página não encontrada', 'error')
            return redirect(url_for('paginas.index'))
        
        return render_template('paginas/edit.html', pagina=response.data)
        
    except Exception as e:
        logger.error(f"Erro ao carregar página para edição: {str(e)}")
        flash(f'Erro ao carregar página: {str(e)}', 'error')
        return redirect(url_for('paginas.index'))
