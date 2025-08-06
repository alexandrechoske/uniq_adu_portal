from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for, flash
from extensions import supabase, supabase_admin
from routes.auth import login_required
import logging

# Configurar logging
logger = logging.getLogger(__name__)

# Criar blueprint com configuração modular
paginas_bp = Blueprint(
    'paginas', 
    __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/paginas/static',
    url_prefix='/paginas'
)

@paginas_bp.route('/check-session')
@login_required
def check_session():
    """
    Endpoint para verificação de sessão usado pelo sistema de auto-refresh
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
        
        # Pular verificação do banco para usuário bypass de API
        if user_id == '00000000-0000-0000-0000-000000000000':
            logger.info("Usuário bypass de API detectado - pulando verificação do banco")
            user_exists_in_db = True
        else:
            try:
                # Usar cliente admin para contornar problemas de RLS
                response = supabase_admin.table('users').select('id, name, email').eq('id', user_id).execute()
                if not response.data or len(response.data) == 0:
                    user_exists_in_db = False
                else:
                    db_user_data = response.data[0]
                    logger.info(f"Usuário {user_id} encontrado no banco: {db_user_data.get('name', 'Nome não disponível')}")
            except Exception as db_error:
                logger.error(f"Erro ao verificar usuário no banco: {str(db_error)}")
                # Não bloquear se houver erro de conexão com o banco
                user_exists_in_db = True
        
        # Se o usuário não existe mais no banco, invalidar sessão
        if not user_exists_in_db:
            logger.warning(f"Usuário {user_id} não encontrado no banco, invalidando sessão")
            session.clear()
            return jsonify({
                'status': 'error',
                'message': 'Usuário não encontrado no sistema'
            }), 401
        
        # Retornar dados da sessão válida
        response_data = {
            'status': 'success',
            'user': {
                'id': user_data.get('id'),
                'name': user_data.get('name'),
                'email': user_data.get('email'),
                'role': user_data.get('role'),
                'active': user_data.get('active', True)
            },
            'session_valid': True,
            'timestamp': session.get('last_activity')
        }
        
        # Adicionar dados do banco se disponíveis
        if db_user_data:
            response_data['user'].update({
                'db_name': db_user_data.get('name'),
                'db_email': db_user_data.get('email')
            })
        
        logger.info(f"Verificação de sessão bem-sucedida para usuário {user_id}")
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Erro na verificação de sessão: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Erro interno do servidor'
        }), 500

@paginas_bp.route('/health')
def health_check():
    """
    Endpoint de verificação de saúde do sistema
    """
    try:
        # Verificar conexão com o banco
        db_status = 'ok'
        try:
            response = supabase.table('users').select('id').limit(1).execute()
            if not hasattr(response, 'data'):
                db_status = 'error'
        except Exception:
            db_status = 'error'
        
        return jsonify({
            'status': 'ok',
            'database': db_status,
            'timestamp': session.get('last_activity'),
            'authenticated': 'user' in session
        })
        
    except Exception as e:
        logger.error(f"Erro no health check: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@paginas_bp.route('/clear-session', methods=['POST'])
def clear_session():
    """
    Endpoint para limpar sessão (logout forçado)
    """
    try:
        user_id = session.get('user', {}).get('id', 'desconhecido')
        session.clear()
        
        logger.info(f"Sessão limpa para usuário {user_id}")
        return jsonify({
            'status': 'success',
            'message': 'Sessão limpa com sucesso'
        })
        
    except Exception as e:
        logger.error(f"Erro ao limpar sessão: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Erro ao limpar sessão'
        }), 500

@paginas_bp.route('/session-info')
@login_required
def session_info():
    """
    Endpoint para obter informações detalhadas da sessão
    """
    try:
        user_data = session.get('user', {})
        
        return jsonify({
            'status': 'success',
            'session_data': {
                'user_id': user_data.get('id'),
                'user_name': user_data.get('name'),
                'user_email': user_data.get('email'),
                'user_role': user_data.get('role'),
                'user_active': user_data.get('active'),
                'last_activity': session.get('last_activity'),
                'session_id': session.get('session_id'),
                'csrf_token': session.get('csrf_token')
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter informações da sessão: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Erro ao obter informações da sessão'
        }), 500

@paginas_bp.route('/update-activity', methods=['POST'])
@login_required
def update_activity():
    """
    Endpoint para atualizar timestamp de atividade do usuário
    """
    try:
        from datetime import datetime
        session['last_activity'] = datetime.now().isoformat()
        
        return jsonify({
            'status': 'success',
            'last_activity': session['last_activity']
        })
        
    except Exception as e:
        logger.error(f"Erro ao atualizar atividade: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Erro ao atualizar atividade'
        }), 500
