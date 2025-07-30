"""
Módulo de Analytics - Dashboard de Logs de Acesso
Apenas para administradores
"""
from flask import render_template, request, jsonify, session, redirect, url_for, current_app
from datetime import datetime, timedelta
import json
import os
from extensions import supabase_admin

def admin_required(f):
    """Decorator para verificar se o usuário é admin"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check for API bypass first
        api_bypass_key = os.getenv('API_BYPASS_KEY')
        api_key = request.headers.get('X-API-Key')
        if api_key == api_bypass_key:
            return f(*args, **kwargs)
            
        if 'user' not in session:
            return redirect(url_for('auth.login'))
        
        user_role = session.get('user', {}).get('role')
        if user_role != 'admin':
            return jsonify({'error': 'Acesso negado - Apenas administradores'}), 403
        
        return f(*args, **kwargs)
    return decorated_function

def register_routes(analytics_bp):
    """Registra as rotas no blueprint fornecido"""
    
    @analytics_bp.route('/')
    @admin_required
    def analytics_dashboard():
        """Página principal do dashboard de analytics"""
        return render_template('analytics_simple_test.html')

    @analytics_bp.route('/api/stats')
    @admin_required
    def get_stats():
        """API para estatísticas básicas dos cards"""
        try:
            # Últimos 30 dias
            thirty_days_ago = datetime.now() - timedelta(days=30)
            
            # Total de acessos nos últimos 30 dias
            total_access_result = supabase_admin.table('access_logs')\
                .select('id', count='exact')\
                .gte('created_at', thirty_days_ago.isoformat())\
                .execute()
            
            total_access = total_access_result.count or 0
            
            # Usuários únicos nos últimos 30 dias
            unique_users_result = supabase_admin.table('access_logs')\
                .select('user_email')\
                .gte('created_at', thirty_days_ago.isoformat())\
                .not_.is_('user_email', 'null')\
                .execute()
            
            unique_emails = set()
            if unique_users_result.data:
                unique_emails = set(row['user_email'] for row in unique_users_result.data if row['user_email'])
            
            unique_users = len(unique_emails)
            
            # Logins hoje
            today = datetime.now().date()
            logins_today_result = supabase_admin.table('access_logs')\
                .select('id', count='exact')\
                .eq('action_type', 'login')\
                .gte('created_at_br', today.isoformat())\
                .execute()
            
            logins_today = logins_today_result.count or 0
            
            # Total de logins (todos os tempos)
            total_logins_result = supabase_admin.table('access_logs')\
                .select('id', count='exact')\
                .eq('action_type', 'login')\
                .execute()
            
            total_logins = total_logins_result.count or 0
            
            return jsonify({
                'success': True,
                'total_access': total_access,
                'unique_users': unique_users,
                'logins_today': logins_today,
                'total_logins': total_logins
            })
            
        except Exception as e:
            print(f"[ANALYTICS ERROR] {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e),
                'total_access': 0,
                'unique_users': 0,
                'logins_today': 0,
                'total_logins': 0
            }), 500
    
    return analytics_bp
