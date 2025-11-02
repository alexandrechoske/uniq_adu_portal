"""
Rotas do módulo de Usuários Online (Admin)
"""
from flask import Blueprint, render_template, session, redirect, url_for, jsonify
from extensions import supabase_admin
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


@bp.route('/api/online-users')
def api_online_users():
    """API REST para buscar usuários online (backup do WebSocket)"""
    try:
        # Verifica autenticação
        if 'user_id' not in session:
            return jsonify({'error': 'Não autenticado'}), 401
        
        # Verifica se é admin
        user_role = session.get('user_role', '')
        if user_role != 'admin':
            return jsonify({'error': 'Acesso negado. Apenas administradores.'}), 403
        
        from websocket_events import get_online_users, cleanup_inactive_sessions

        # Remove sessões antigas e retorna lista tratada
        cleanup_inactive_sessions(supabase_admin, timeout_minutes=5)
        online_users = get_online_users(supabase_admin)
        
        return jsonify({
            'users': online_users,
            'count': len(online_users)
        })
    
    except Exception as e:
        logger.error(f"Erro ao buscar usuários online via API: {str(e)}")
        return jsonify({'error': str(e)}), 500


@bp.route('/api/cleanup-sessions', methods=['POST'])
def api_cleanup_sessions():
    """Limpar sessões inativas manualmente"""
    try:
        # Verifica autenticação
        if 'user_id' not in session:
            return jsonify({'error': 'Não autenticado'}), 401
        
        # Verifica se é admin
        user_role = session.get('user_role', '')
        if user_role != 'admin':
            return jsonify({'error': 'Acesso negado'}), 403
        
        # Importa e executa limpeza
        from websocket_events import cleanup_inactive_sessions
        cleanup_inactive_sessions(supabase_admin, timeout_minutes=30)
        
        return jsonify({
            'success': True,
            'message': 'Limpeza de sessões executada com sucesso'
        })
    
    except Exception as e:
        logger.error(f"Erro ao limpar sessões: {str(e)}")
        return jsonify({'error': str(e)}), 500
