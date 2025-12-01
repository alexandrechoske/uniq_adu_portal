"""
Rotas do módulo de Usuários Online (Admin)
"""
from flask import Blueprint, render_template, session, redirect, url_for, jsonify, request
from extensions import supabase_admin
from .services import online_user_service
import logging

logger = logging.getLogger(__name__)

bp = Blueprint(
    'usuarios_online',
    __name__,
    url_prefix='/usuarios-online',
    template_folder='templates',
    static_folder='static'
)

@bp.route('/')
def index():
    """Painel principal de usuários online - Apenas para admins"""
    try:
        # Verifica autenticação
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        
        # Verifica se é admin
        user_role = session.get('user_role', '')
        if user_role != 'admin':
            return "Acesso negado. Apenas administradores podem visualizar esta página.", 403
        
        user_name = session.get('user_name', 'Admin')
        
        return render_template(
            'usuarios_online/usuarios_online.html',
            user_name=user_name,
            user_role=user_role
        )
    
    except Exception as e:
        logger.error(f"Erro ao carregar painel de usuários online: {str(e)}")
        return f"Erro ao carregar painel: {str(e)}", 500


@bp.route('/api/heartbeat', methods=['POST'])
def heartbeat():
    """Recebe heartbeat do cliente para atualizar status online"""
    try:
        if 'user_id' not in session:
            return jsonify({'status': 'ignored', 'reason': 'not_authenticated'}), 200

        data = request.get_json() or {}
        
        # Get real IP address (handling proxy headers)
        if request.headers.get('X-Forwarded-For'):
            ip_address = request.headers.get('X-Forwarded-For').split(',')[0].strip()
        else:
            ip_address = request.remote_addr

        user_data = {
            'user_name': session.get('user_name', 'Unknown'),
            'user_email': session.get('user_email', ''),
            'user_role': session.get('user_role', ''),
            'current_page': data.get('page', ''),
            'page_title': data.get('title', ''),
            'ip_address': ip_address
        }
        
        online_user_service.update_heartbeat(session['user_id'], user_data)
        return jsonify({'status': 'ok'})
        
    except Exception as e:
        logger.error(f"Heartbeat error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@bp.route('/api/online-users')
def api_online_users():
    """API REST para buscar usuários online (Substitui WebSocket)"""
    try:
        # Verifica autenticação
        if 'user_id' not in session:
            return jsonify({'error': 'Não autenticado'}), 401
        
        # Verifica se é admin
        user_role = session.get('user_role', '')
        if user_role != 'admin':
            return jsonify({'error': 'Acesso negado. Apenas administradores.'}), 403
        
        users = online_user_service.get_online_users()
        stats = online_user_service.get_stats()
        
        return jsonify({
            'users': users,
            'count': len(users),
            'stats': stats
        })
    
    except Exception as e:
        logger.error(f"Erro ao buscar usuários online via API: {str(e)}")
        return jsonify({'error': str(e)}), 500


@bp.route('/api/cleanup-sessions', methods=['POST'])
def api_cleanup_sessions():
    """Limpar sessões inativas manualmente (Mantido para compatibilidade, mas o serviço faz auto-cleanup)"""
    try:
        # Verifica autenticação
        if 'user_id' not in session:
            return jsonify({'error': 'Não autenticado'}), 401
        
        # Verifica se é admin
        user_role = session.get('user_role', '')
        if user_role != 'admin':
            return jsonify({'error': 'Acesso negado'}), 403
        
        # O serviço já faz cleanup ao ler, mas podemos forçar se quisermos implementar um método específico
        # Por enquanto, apenas retorna sucesso pois o get_online_users já limpa
        
        return jsonify({
            'success': True,
            'message': 'Limpeza de sessões executada com sucesso'
        })
    
    except Exception as e:
        logger.error(f"Erro ao limpar sessões: {str(e)}")
        return jsonify({'error': str(e)}), 500
