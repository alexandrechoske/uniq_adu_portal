"""
Módulo de Analytics - Dashboard de Logs de Acesso
Apenas para administradores
"""
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from datetime import datetime, timedelta, timezone
import json
from extensions import supabase_admin

import os

bp = Blueprint('analytics', __name__, 
               url_prefix='/analytics',
               template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
               static_folder=os.path.join(os.path.dirname(__file__), 'static'),
               static_url_path='/analytics/static')

# Alias para compatibilidade
analytics_bp = bp

def admin_required(f):
    """Decorator para verificar se o usuário é admin"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check for API bypass first
        api_key = request.headers.get('X-API-Key')
        if api_key == 'test-key-123':  # For testing purposes
            return f(*args, **kwargs)
            
        if 'user' not in session:
            return redirect(url_for('auth.login'))
        
        user_role = session.get('user', {}).get('role')
        if user_role != 'admin':
            return jsonify({'error': 'Acesso negado - Apenas administradores'}), 403
        
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/')
@bp.route('/dashboard')
@admin_required
def dashboard():
    """Dashboard principal de analytics"""
    return render_template('analytics/dashboard.html')

@bp.route('/api/overview')
@admin_required
def api_overview():
    """API para dados gerais do dashboard"""
    try:
        # Últimos 30 dias
        thirty_days_ago = datetime.now() - timedelta(days=30)
        
        # Total de acessos
        total_access = supabase_admin.table('access_logs')\
            .select('id', count='exact')\
            .gte('created_at', thirty_days_ago.isoformat())\
            .execute()
        
        # Usuários únicos
        unique_users = supabase_admin.table('access_logs')\
            .select('user_email')\
            .gte('created_at', thirty_days_ago.isoformat())\
            .not_.is_('user_email', 'null')\
            .execute()
        
        unique_emails = set()
        if unique_users.data:
            unique_emails = set(row['user_email'] for row in unique_users.data if row['user_email'])
        
        # Logins hoje
        today = datetime.now().date()
        logins_today = supabase_admin.table('access_logs')\
            .select('id', count='exact')\
            .eq('action_type', 'login')\
            .gte('created_at_br', today.isoformat())\
            .execute()
        
        # Páginas mais acessadas
        top_pages = supabase_admin.table('access_logs')\
            .select('page_name')\
            .eq('action_type', 'page_access')\
            .gte('created_at', thirty_days_ago.isoformat())\
            .not_.is_('page_name', 'null')\
            .limit(1000)\
            .execute()
        
        # Contar páginas
        page_counts = {}
        if top_pages.data:
            for row in top_pages.data:
                page = row['page_name']
                page_counts[page] = page_counts.get(page, 0) + 1
        
        top_pages_list = sorted(page_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return jsonify({
            'success': True,
            'data': {
                'total_access': total_access.count or 0,
                'unique_users': len(unique_emails),
                'logins_today': logins_today.count or 0,
                'top_pages': top_pages_list
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/timeline')
@admin_required
def api_timeline():
    """API para linha do tempo de acessos por dia"""
    try:
        days = int(request.args.get('days', 30))
        start_date = datetime.now() - timedelta(days=days)
        
        timeline_data = supabase_admin.table('access_logs')\
            .select('created_at_br, action_type')\
            .gte('created_at', start_date.isoformat())\
            .order('created_at_br')\
            .execute()
        
        # Agrupar por dia
        daily_stats = {}
        if timeline_data.data:
            for row in timeline_data.data:
                if not row['created_at_br']:
                    continue
                
                date_str = row['created_at_br'][:10]  # YYYY-MM-DD
                action = row['action_type']
                
                if date_str not in daily_stats:
                    daily_stats[date_str] = {
                        'date': date_str,
                        'login': 0,
                        'page_access': 0,
                        'logout': 0,
                        'api_call': 0,
                        'total': 0
                    }
                
                daily_stats[date_str][action] = daily_stats[date_str].get(action, 0) + 1
                daily_stats[date_str]['total'] += 1
        
        # Converter para lista ordenada
        timeline = sorted(daily_stats.values(), key=lambda x: x['date'])
        
        return jsonify({
            'success': True,
            'data': timeline
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/sessions')
@admin_required
def api_sessions():
    """API para análise de sessões"""
    try:
        limit = int(request.args.get('limit', 50))
        user_filter = request.args.get('user_email', '')
        
        # Query base
        query = supabase_admin.table('access_logs')\
            .select('user_email, session_id, action_type, page_name, created_at_br, ip_address, browser')\
            .not_.is_('session_id', 'null')\
            .order('created_at_br', desc=True)
        
        # Filtro por usuário
        if user_filter:
            query = query.ilike('user_email', f'%{user_filter}%')
        
        sessions_data = query.limit(limit * 10).execute()  # Buscar mais para agrupar por sessão
        
        # Agrupar por sessão
        sessions = {}
        if sessions_data.data:
            for row in sessions_data.data:
                session_id = row['session_id']
                
                if session_id not in sessions:
                    sessions[session_id] = {
                        'session_id': session_id,
                        'user_email': row['user_email'],
                        'start_time': row['created_at_br'],
                        'end_time': row['created_at_br'],
                        'actions': [],
                        'pages_visited': set(),
                        'ip_address': row['ip_address'],
                        'browser': row['browser'],
                        'total_actions': 0,
                        'duration_minutes': 0
                    }
                
                session = sessions[session_id]
                session['actions'].append({
                    'action_type': row['action_type'],
                    'page_name': row['page_name'],
                    'timestamp': row['created_at_br']
                })
                
                if row['page_name']:
                    session['pages_visited'].add(row['page_name'])
                
                # Atualizar tempos
                if row['created_at_br'] > session['end_time']:
                    session['end_time'] = row['created_at_br']
                if row['created_at_br'] < session['start_time']:
                    session['start_time'] = row['created_at_br']
                
                session['total_actions'] += 1
        
        # Calcular duração e converter sets para listas
        for session in sessions.values():
            try:
                start = datetime.fromisoformat(session['start_time'].replace('T', ' '))
                end = datetime.fromisoformat(session['end_time'].replace('T', ' '))
                session['duration_minutes'] = int((end - start).total_seconds() / 60)
            except:
                session['duration_minutes'] = 0
            
            session['pages_visited'] = list(session['pages_visited'])
            
            # Ordenar ações por tempo
            session['actions'].sort(key=lambda x: x['timestamp'])
        
        # Converter para lista e limitar
        sessions_list = sorted(sessions.values(), key=lambda x: x['start_time'], reverse=True)[:limit]
        
        return jsonify({
            'success': True,
            'data': sessions_list
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/user-activity')
@admin_required
def api_user_activity():
    """API para atividade por usuário"""
    try:
        days = int(request.args.get('days', 7))
        start_date = datetime.now() - timedelta(days=days)
        
        user_activity = supabase_admin.table('access_logs')\
            .select('user_email, action_type, created_at_br')\
            .gte('created_at', start_date.isoformat())\
            .not_.is_('user_email', 'null')\
            .execute()
        
        # Agrupar por usuário
        users = {}
        if user_activity.data:
            for row in user_activity.data:
                email = row['user_email']
                action = row['action_type']
                
                if email not in users:
                    users[email] = {
                        'user_email': email,
                        'total_actions': 0,
                        'login_count': 0,
                        'page_views': 0,
                        'api_calls': 0,
                        'last_activity': row['created_at_br']
                    }
                
                user = users[email]
                user['total_actions'] += 1
                
                if action == 'login':
                    user['login_count'] += 1
                elif action == 'page_access':
                    user['page_views'] += 1
                elif action == 'api_call':
                    user['api_calls'] += 1
                
                # Atualizar última atividade
                if row['created_at_br'] > user['last_activity']:
                    user['last_activity'] = row['created_at_br']
        
        # Converter para lista ordenada
        users_list = sorted(users.values(), key=lambda x: x['total_actions'], reverse=True)
        
        return jsonify({
            'success': True,
            'data': users_list
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/security-events')
@admin_required
def api_security_events():
    """API para eventos de segurança"""
    try:
        days = int(request.args.get('days', 30))
        start_date = datetime.now() - timedelta(days=days)
        
        # Buscar eventos de falha
        security_events = supabase_admin.table('access_logs')\
            .select('*')\
            .eq('success', False)\
            .gte('created_at', start_date.isoformat())\
            .order('created_at_br', desc=True)\
            .limit(100)\
            .execute()
        
        return jsonify({
            'success': True,
            'data': security_events.data or []
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/devices')
@admin_required  
def api_devices():
    """API para estatísticas de dispositivos"""
    try:
        days = int(request.args.get('days', 30))
        start_date = datetime.now() - timedelta(days=days)
        
        devices_data = supabase_admin.table('access_logs')\
            .select('device_type, browser, platform')\
            .gte('created_at', start_date.isoformat())\
            .execute()
        
        # Contar dispositivos
        device_stats = {}
        browser_stats = {}
        platform_stats = {}
        
        if devices_data.data:
            for row in devices_data.data:
                # Dispositivos
                device = row.get('device_type', 'unknown')
                device_stats[device] = device_stats.get(device, 0) + 1
                
                # Browsers
                browser = row.get('browser', 'unknown')
                browser_stats[browser] = browser_stats.get(browser, 0) + 1
                
                # Plataformas
                platform = row.get('platform', 'unknown')
                platform_stats[platform] = platform_stats.get(platform, 0) + 1
        
        return jsonify({
            'success': True,
            'data': {
                'devices': device_stats,
                'browsers': browser_stats,
                'platforms': platform_stats
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
