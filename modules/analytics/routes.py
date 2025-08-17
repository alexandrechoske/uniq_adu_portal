from flask import Blueprint, render_template, jsonify, request, session
from datetime import datetime, timedelta
from extensions import supabase_admin
from routes.auth import role_required
import logging
from services.retry_utils import run_with_retries

# Configurar logging
logger = logging.getLogger(__name__)

bp = Blueprint('analytics', __name__, 
               url_prefix='/usuarios/analytics',
               static_folder='static',
               template_folder='templates')

@bp.route('/')
@role_required(['admin'])
def analytics_dashboard():
    """
    Página principal do Analytics do Portal
    """
    try:
        return render_template('analytics.html', analytics_type='portal')
    except Exception as e:
        logger.error(f"Erro ao carregar página de analytics: {e}")
        return f"Erro ao carregar página: {str(e)}", 500

@bp.route('/agente')
@role_required(['admin'])
def analytics_agente():
    """
    Página principal do Analytics do Agente
    """
    try:
        return render_template('analytics_agente.html', analytics_type='agente')
    except Exception as e:
        logger.error(f"Erro ao carregar página de analytics do agente: {e}")
        return f"Erro ao carregar página: {str(e)}", 500

@bp.route('/api/stats')
@role_required(['admin'])
def get_stats():
    """
    API para estatísticas básicas do Analytics
    """
    try:
        # Obter parâmetros de filtro
        date_range = request.args.get('dateRange', '30d')
        user_role = request.args.get('userRole', 'all')
        action_type = request.args.get('actionType', 'all')
        
        # Calcular datas
        end_date = datetime.now()
        if date_range == '1d':
            start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif date_range == '7d':
            start_date = end_date - timedelta(days=7)
        elif date_range == '30d':
            start_date = end_date - timedelta(days=30)
        else:
            start_date = end_date - timedelta(days=30)
        
        # Query base
        query = supabase_admin.table('access_logs').select('*')
        
        # Aplicar filtros de data
        query = query.gte('created_at', start_date.isoformat())
        query = query.lte('created_at', end_date.isoformat())
        
        if user_role != 'all':
            query = query.eq('user_role', user_role)
            
        if action_type != 'all':
            query = query.eq('action_type', action_type)
        
        # Executar query
        def _exec():
            return query.execute()
        response = run_with_retries(
            'analytics.get_stats',
            _exec,
            max_attempts=3,
            base_delay_seconds=0.8,
            should_retry=lambda e: 'Server disconnected' in str(e) or 'timeout' in str(e).lower()
        )
        logs = response.data if response.data else []
        # Filtrar logs para remover acessos de IP/desenv (page_url de localhost:5000)
        logs = [log for log in logs if not (
            (log.get('page_url') and log['page_url'].startswith('http://127.0.0.1:5000')) or
            (log.get('ip_address') == '127.0.0.1')
        )]

        # Calcular estatísticas
        total_access = len([log for log in logs if log.get('action_type') == 'page_access'])
        unique_users = len(set(log.get('user_id') for log in logs if log.get('user_id')))

        # Logins hoje
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        logins_today = len([
            log for log in logs 
            if log.get('action_type') == 'login' and 
            log.get('created_at') and
            datetime.fromisoformat(log.get('created_at').replace('Z', '+00:00')) >= today_start
        ])

        # Total de logins (todos os tempos)
        try:
            def _exec_total():
                return supabase_admin.table('access_logs').select('*').eq('action_type', 'login').execute()
            total_logins_response = run_with_retries(
                'analytics.get_stats.total_logins',
                _exec_total,
                max_attempts=3,
                base_delay_seconds=0.8,
                should_retry=lambda e: 'Server disconnected' in str(e) or 'timeout' in str(e).lower()
            )
            total_logins = len([
                log for log in total_logins_response.data
                if not (
                    (log.get('page_url') and log['page_url'].startswith('http://127.0.0.1:5000')) or
                    (log.get('ip_address') == '127.0.0.1')
                )
            ]) if total_logins_response.data else 0
        except:
            total_logins = 0

        # Sessão média (simulado - pode ser calculado com base nos dados de logout)
        avg_session_minutes = 45  # Placeholder

        return jsonify({
            'success': True,
            'total_access': total_access,
            'unique_users': unique_users,
            'logins_today': logins_today,
            'total_logins': total_logins,
            'avg_session_minutes': avg_session_minutes
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {e}")
        return jsonify({
            'success': True,  # Retornar success=True com dados vazios para não quebrar a interface
            'total_access': 0,
            'unique_users': 0,
            'logins_today': 0,
            'total_logins': 0,
            'avg_session_minutes': 0,
            'error': str(e)
        })

@bp.route('/api/charts')
@role_required(['admin'])
def get_charts():
    """
    API para dados dos gráficos
    """
    try:
        # Obter parâmetros de filtro
        date_range = request.args.get('dateRange', '30d')
        user_role = request.args.get('userRole', 'all')
        action_type = request.args.get('actionType', 'all')
        
        # Calcular datas
        end_date = datetime.now()
        if date_range == '1d':
            start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
            days_back = 1
        elif date_range == '7d':
            start_date = end_date - timedelta(days=7)
            days_back = 7
        elif date_range == '30d':
            start_date = end_date - timedelta(days=30)
            days_back = 30
        else:
            start_date = end_date - timedelta(days=30)
            days_back = 30
        
        # Query base
        query = supabase_admin.table('access_logs').select('*')
        query = query.gte('created_at', start_date.isoformat())
        query = query.lte('created_at', end_date.isoformat())
        
        if user_role != 'all':
            query = query.eq('user_role', user_role)
            
        if action_type != 'all':
            query = query.eq('action_type', action_type)
        
        def _exec():
            return query.execute()
        response = run_with_retries(
            'analytics.get_charts',
            _exec,
            max_attempts=3,
            base_delay_seconds=0.8,
            should_retry=lambda e: 'Server disconnected' in str(e) or 'timeout' in str(e).lower()
        )
        logs = response.data if response.data else []
        # Filtrar logs para remover acessos de IP/desenv (page_url de localhost:5000)
        logs = [log for log in logs if not (
            (log.get('page_url') and log['page_url'].startswith('http://127.0.0.1:5000')) or
            (log.get('ip_address') == '127.0.0.1')
        )]
        
        # Acessos diários (duas métricas: total de acessos e total de usuários únicos)
        daily_access = []  # total de acessos por dia
        daily_users = []   # total de usuários únicos por dia
        logger.info(f"[ANALYTICS] Processando {len(logs)} logs para acessos diários")
        logger.info(f"[ANALYTICS] Intervalo: {start_date} até {end_date} ({days_back} dias)")
        
        # Melhorar processamento: agrupar logs por data primeiro
        from datetime import timezone
        logs_by_date = {}
        logs_ids_in_days = set()
        
        # Agrupar logs por data para processamento mais eficiente
        for log in logs:
            if log.get('action_type') != 'page_access':
                continue
                
            try:
                created_at_raw = log.get('created_at', '')
                if not created_at_raw:
                    continue
                    
                log_time = datetime.fromisoformat(created_at_raw.replace('Z', '+00:00'))
                log_date = log_time.date()
                
                if log_date not in logs_by_date:
                    logs_by_date[log_date] = []
                logs_by_date[log_date].append(log)
                
                # Marcar log_id como usado
                if log.get('id'):
                    logs_ids_in_days.add(log['id'])
                    
            except Exception as e:
                logger.warning(f"[ANALYTICS] Erro ao processar log: {e}")
                continue
        
        # Processar apenas dias que tenham dados (evitar dias com 0 desnecessários)
        days_with_data = []
        for i in range(days_back):
            day = start_date + timedelta(days=i)
            day_date = day.date()
            
            logs_day = logs_by_date.get(day_date, [])
            unique_users_day = set()
            logs_count_day = len(logs_day)
            
            for log in logs_day:
                user_id = log.get('user_id')
                if user_id:
                    unique_users_day.add(user_id)
            
            # Só incluir o dia se tiver dados OU se for um dos últimos 7 dias
            recent_threshold = (datetime.now() - timedelta(days=7)).date()
            should_include = logs_count_day > 0 or day_date >= recent_threshold
            
            if should_include:
                daily_access.append({
                    'date': day.strftime('%Y-%m-%d'),
                    'count': logs_count_day
                })
                daily_users.append({
                    'date': day.strftime('%Y-%m-%d'),
                    'count': len(unique_users_day)
                })
                
                if logs_count_day > 0:
                    days_with_data.append(day.strftime('%Y-%m-%d'))
            
            logger.info(f"[ANALYTICS] Dia {day.strftime('%Y-%m-%d')}: {logs_count_day} acessos, {len(unique_users_day)} usuários únicos")
        
        logger.info(f"[ANALYTICS] Dias com dados incluídos: {len(days_with_data)}")
        # LOG EXTRA: Soma dos acessos diários
        soma_diaria = sum(d['count'] for d in daily_access)
        total_acessos = len([log for log in logs if log.get('action_type') == 'page_access'])
        logger.info(f"[ANALYTICS] Soma dos acessos diários: {soma_diaria}")
        logger.info(f"[ANALYTICS] Total de acessos no período: {total_acessos}")
        # LOG EXTRA: Logs de page_access que não entraram em nenhum dia
        ids_logs_page_access = set(log['id'] for log in logs if log.get('action_type') == 'page_access' and log.get('id'))
        ids_fora = ids_logs_page_access - logs_ids_in_days
        if ids_fora:
            logger.warning(f"[ANALYTICS] {len(ids_fora)} logs de page_access não entraram em nenhum dia do gráfico. IDs: {list(ids_fora)[:10]} ...")
        
        # Top páginas
        page_counts = {}
        for log in logs:
            if log.get('action_type') == 'page_access':
                page_name = log.get('page_name', 'Sem nome')
                page_counts[page_name] = page_counts.get(page_name, 0) + 1
        
        top_pages = [
            {'page_name': page, 'count': count}
            for page, count in sorted(page_counts.items(), key=lambda x: x[1], reverse=True)
        ]
        
        # Atividade de usuários
        user_counts = {}
        for log in logs:
            if log.get('action_type') == 'page_access':
                user_name = log.get('user_name', 'Usuário')
                user_counts[user_name] = user_counts.get(user_name, 0) + 1
        
        users_activity = [
            {'user_name': user, 'access_count': count}
            for user, count in sorted(user_counts.items(), key=lambda x: x[1], reverse=True)
        ]
        
        # Mapa de calor por horário
        hourly_counts = {}
        for log in logs:
            try:
                hour = datetime.fromisoformat(log.get('created_at', '').replace('Z', '+00:00')).hour
                hourly_counts[hour] = hourly_counts.get(hour, 0) + 1
            except:
                continue
        
        hourly_heatmap = [
            {'hour': hour, 'count': hourly_counts.get(hour, 0)}
            for hour in range(24)
        ]
        
        return jsonify({
            'success': True,
            'daily_access': daily_access,   # total de acessos por dia
            'daily_users': daily_users,     # total de usuários únicos por dia
            'top_pages': top_pages,
            'users_activity': users_activity,
            'hourly_heatmap': hourly_heatmap
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter dados de gráficos: {e}")
        return jsonify({
            'success': True,  # Retornar dados vazios para não quebrar
            'daily_access': [],
            'top_pages': [],
            'users_activity': [],
            'hourly_heatmap': [],
            'error': str(e)
        })

@bp.route('/api/top-users')
@role_required(['admin'])
def get_top_users():
    """
    API para dados dos top usuários
    """
    try:
        # Obter parâmetros de filtro
        date_range = request.args.get('dateRange', '30d')
        user_role = request.args.get('userRole', 'all')
        
        # Calcular datas
        end_date = datetime.now()
        if date_range == '1d':
            start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif date_range == '7d':
            start_date = end_date - timedelta(days=7)
        elif date_range == '30d':
            start_date = end_date - timedelta(days=30)
        else:
            start_date = end_date - timedelta(days=30)
        
        # Query base
        query = supabase_admin.table('access_logs').select('*')
        query = query.gte('created_at', start_date.isoformat())
        query = query.lte('created_at', end_date.isoformat())
        
        if user_role != 'all':
            query = query.eq('user_role', user_role)
        
        def _exec():
            return query.execute()
        response = run_with_retries(
            'analytics.get_top_users',
            _exec,
            max_attempts=3,
            base_delay_seconds=0.8,
            should_retry=lambda e: 'Server disconnected' in str(e) or 'timeout' in str(e).lower()
        )
        logs = response.data if response.data else []
        # Filtrar logs para remover acessos de IP/desenv (page_url de localhost:5000)
        logs = [log for log in logs if not (
            (log.get('page_url') and log['page_url'].startswith('http://127.0.0.1:5000')) or
            (log.get('ip_address') == '127.0.0.1')
        )]

        # Agrupar por usuário
        user_stats = {}
        for log in logs:
            user_id = log.get('user_id')
            if not user_id:
                continue
            
            if user_id not in user_stats:
                user_stats[user_id] = {
                    'user_id': user_id,
                    'user_name': log.get('user_name', 'N/A'),
                    'user_email': log.get('user_email', 'N/A'),
                    'user_role': log.get('user_role', 'N/A'),
                    'total_access': 0,
                    'last_login': None,
                    'avg_session_minutes': 30,  # Placeholder
                    'favorite_pages': []
                }
            
            if log.get('action_type') == 'page_access':
                user_stats[user_id]['total_access'] += 1
                page_name = log.get('page_name', 'N/A')
                if page_name not in user_stats[user_id]['favorite_pages']:
                    user_stats[user_id]['favorite_pages'].append(page_name)
            
            if log.get('action_type') == 'login':
                if not user_stats[user_id]['last_login'] or log.get('created_at') > user_stats[user_id]['last_login']:
                    user_stats[user_id]['last_login'] = log.get('created_at')

        # Converter para lista e ordenar
        top_users = list(user_stats.values())
        top_users.sort(key=lambda x: x['total_access'], reverse=True)

        # Limitar páginas favoritas
        for user in top_users:
            user['favorite_pages'] = ', '.join(user['favorite_pages'][:3])

        return jsonify(top_users[:20])  # Top 20 usuários
        
    except Exception as e:
        logger.error(f"Erro ao obter top usuários: {e}")
        return jsonify([])  # Retornar lista vazia

@bp.route('/api/recent-activity')
@role_required(['admin'])
def get_recent_activity():
    """
    API para atividade recente
    """
    try:
        # Obter parâmetros de filtro
        date_range = request.args.get('dateRange', '30d')
        user_role = request.args.get('userRole', 'all')
        action_type = request.args.get('actionType', 'all')
        
        # Calcular datas
        end_date = datetime.now()
        if date_range == '1d':
            start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif date_range == '7d':
            start_date = end_date - timedelta(days=7)
        elif date_range == '30d':
            start_date = end_date - timedelta(days=30)
        else:
            start_date = end_date - timedelta(days=30)
        
        # Query base
        query = supabase_admin.table('access_logs').select('*')
        query = query.gte('created_at', start_date.isoformat())
        query = query.lte('created_at', end_date.isoformat())
        query = query.order('created_at', desc=True)
        query = query.limit(50)  # Limitar a 50 registros mais recentes
        
        if user_role != 'all':
            query = query.eq('user_role', user_role)
            
        if action_type != 'all':
            query = query.eq('action_type', action_type)
        
        def _exec():
            return query.execute()
        response = run_with_retries(
            'analytics.get_recent_activity',
            _exec,
            max_attempts=3,
            base_delay_seconds=0.8,
            should_retry=lambda e: 'Server disconnected' in str(e) or 'timeout' in str(e).lower()
        )
        logs = response.data if response.data else []
        # Filtrar logs para remover acessos de IP/desenv (page_url de localhost:5000)
        logs = [log for log in logs if not (
            (log.get('page_url') and log['page_url'].startswith('http://127.0.0.1:5000')) or
            (log.get('ip_address') == '127.0.0.1')
        )]
        
        # Formatar dados para o frontend
        formatted_logs = []
        for log in logs:
            try:
                # Tratar a data corretamente
                created_at = log.get('created_at')
                if created_at:
                    # Converter para datetime e depois para timestamp
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    timestamp = dt.isoformat()
                else:
                    timestamp = None
                
                formatted_log = {
                    'timestamp': timestamp,
                    'user_name': log.get('user_name', 'N/A'),
                    'user_email': log.get('user_email', 'N/A'),
                    'action_type': log.get('action_type', 'N/A'),
                    'page_name': log.get('page_name', 'N/A'),
                    'endpoint': log.get('endpoint', 'N/A'),
                    'ip_address': log.get('ip_address', 'N/A'),
                    'user_agent': log.get('user_agent', 'N/A')
                }
                formatted_logs.append(formatted_log)
            except Exception as format_error:
                logger.warning(f"Erro ao formatar log: {format_error}")
                continue
        return jsonify(formatted_logs)
        
    except Exception as e:
        logger.error(f"Erro ao obter atividade recente: {e}")
        return jsonify([])  # Retornar lista vazia

# ======== ANALYTICS DO AGENTE ========

@bp.route('/api/agente/stats')
@role_required(['admin'])
def get_agente_stats():
    """
    API para estatísticas básicas do Analytics do Agente
    """
    try:
        # Obter parâmetros de filtro
        date_range = request.args.get('dateRange', '30d')
        empresa_nome = request.args.get('empresa', 'all')
        message_type = request.args.get('messageType', 'all')
        
        # Calcular datas
        end_date = datetime.now()
        if date_range == '1d':
            start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif date_range == '7d':
            start_date = end_date - timedelta(days=7)
        elif date_range == '30d':
            start_date = end_date - timedelta(days=30)
        else:
            start_date = end_date - timedelta(days=30)
        
        # Query base
        query = supabase_admin.table('agent_interaction_logs').select('*')
        query = query.gte('created_at', start_date.isoformat())
        query = query.lte('created_at', end_date.isoformat())
        
        if empresa_nome != 'all':
            query = query.eq('empresa_nome', empresa_nome)
            
        if message_type != 'all':
            query = query.eq('message_type', message_type)
        
        def _exec():
            return query.execute()
        response = run_with_retries(
            'analytics.get_agente_stats',
            _exec,
            max_attempts=3,
            base_delay_seconds=0.8,
            should_retry=lambda e: 'Server disconnected' in str(e) or 'timeout' in str(e).lower()
        )
        logs = response.data if response.data else []
        
        # Calcular estatísticas
        total_interactions = len(logs)
        unique_users = len(set(log.get('whatsapp_number') for log in logs if log.get('whatsapp_number')))
        unique_companies = len(set(log.get('empresa_nome') for log in logs if log.get('empresa_nome')))
        
        # Calcular sucessos
        successful_interactions = len([log for log in logs if log.get('is_successful', True)])
        success_rate = (successful_interactions / total_interactions * 100) if total_interactions > 0 else 0
        
        # Calcular tempo médio de resposta
        response_times = [log.get('response_time_ms') for log in logs if log.get('response_time_ms')]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        # Tipos de resposta
        normal_responses = len([log for log in logs if log.get('response_type') == 'normal'])
        arquivo_responses = len([log for log in logs if log.get('response_type') == 'arquivo'])
        
        stats = {
            'total_interactions': total_interactions,
            'unique_users': unique_users,
            'unique_companies': unique_companies,
            'success_rate': round(success_rate, 1),
            'avg_response_time': round(avg_response_time, 0),
            'normal_responses': normal_responses,
            'arquivo_responses': arquivo_responses
        }
        
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas do agente: {e}")
        return jsonify({
            'total_interactions': 0,
            'unique_users': 0,
            'unique_companies': 0,
            'success_rate': 0,
            'avg_response_time': 0,
            'normal_responses': 0,
            'arquivo_responses': 0
        })

@bp.route('/api/agente/interactions-chart')
@role_required(['admin'])
def get_agente_interactions_chart():
    """
    API para gráfico de interações do agente ao longo do tempo
    """
    try:
        # Obter parâmetros de filtro
        date_range = request.args.get('dateRange', '30d')
        empresa_nome = request.args.get('empresa', 'all')
        
        # Calcular datas
        end_date = datetime.now()
        if date_range == '1d':
            start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
            interval = 'hour'
        elif date_range == '7d':
            start_date = end_date - timedelta(days=7)
            interval = 'day'
        elif date_range == '30d':
            start_date = end_date - timedelta(days=30)
            interval = 'day'
        else:
            start_date = end_date - timedelta(days=30)
            interval = 'day'
        
        # Query base
        query = supabase_admin.table('agent_interaction_logs').select('*')
        query = query.gte('created_at', start_date.isoformat())
        query = query.lte('created_at', end_date.isoformat())
        query = query.order('created_at', desc=False)
        
        if empresa_nome != 'all':
            query = query.eq('empresa_nome', empresa_nome)
        
        def _exec():
            return query.execute()
        response = run_with_retries(
            'analytics.get_agente_interactions_chart',
            _exec,
            max_attempts=3,
            base_delay_seconds=0.8,
            should_retry=lambda e: 'Server disconnected' in str(e) or 'timeout' in str(e).lower()
        )
        logs = response.data if response.data else []
        
        # Agrupar dados por intervalo
        chart_data = {}
        
        for log in logs:
            created_at = log.get('created_at')
            if created_at:
                dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                
                if interval == 'hour':
                    key = dt.strftime('%Y-%m-%d %H:00')
                else:  # day
                    key = dt.strftime('%Y-%m-%d')
                
                if key not in chart_data:
                    chart_data[key] = {
                        'date': key,
                        'total': 0,
                        'normal': 0,
                        'arquivo': 0,
                        'success': 0,
                        'error': 0
                    }
                
                chart_data[key]['total'] += 1
                
                response_type = log.get('response_type', 'normal')
                if response_type == 'arquivo':
                    chart_data[key]['arquivo'] += 1
                else:
                    chart_data[key]['normal'] += 1
                
                if log.get('is_successful', True):
                    chart_data[key]['success'] += 1
                else:
                    chart_data[key]['error'] += 1
        
        # Converter para lista ordenada
        chart_list = list(chart_data.values())
        chart_list.sort(key=lambda x: x['date'])
        
        return jsonify(chart_list)
        
    except Exception as e:
        logger.error(f"Erro ao obter gráfico de interações do agente: {e}")
        return jsonify([])

@bp.route('/api/agente/top-companies')
@role_required(['admin'])
def get_agente_top_companies():
    """
    API para empresas que mais usam o agente
    """
    try:
        # Obter parâmetros de filtro
        date_range = request.args.get('dateRange', '30d')
        
        # Calcular datas
        end_date = datetime.now()
        if date_range == '1d':
            start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif date_range == '7d':
            start_date = end_date - timedelta(days=7)
        elif date_range == '30d':
            start_date = end_date - timedelta(days=30)
        else:
            start_date = end_date - timedelta(days=30)
        
        # Query base
        query = supabase_admin.table('agent_interaction_logs').select('*')
        query = query.gte('created_at', start_date.isoformat())
        query = query.lte('created_at', end_date.isoformat())
        
        def _exec():
            return query.execute()
        response = run_with_retries(
            'analytics.get_agente_top_companies',
            _exec,
            max_attempts=3,
            base_delay_seconds=0.8,
            should_retry=lambda e: 'Server disconnected' in str(e) or 'timeout' in str(e).lower()
        )
        logs = response.data if response.data else []
        
        # Agrupar por empresa
        company_stats = {}
        for log in logs:
            empresa_nome = log.get('empresa_nome', 'N/A')
            if empresa_nome not in company_stats:
                company_stats[empresa_nome] = {
                    'empresa_nome': empresa_nome,
                    'total_interactions': 0,
                    'unique_users': set(),
                    'normal_requests': 0,
                    'arquivo_requests': 0,
                    'success_rate': 0,
                    'avg_processos_encontrados': 0,
                    'total_processos': 0,
                    'last_interaction': None
                }
            
            company_stats[empresa_nome]['total_interactions'] += 1
            
            whatsapp_number = log.get('whatsapp_number')
            if whatsapp_number:
                company_stats[empresa_nome]['unique_users'].add(whatsapp_number)
            
            response_type = log.get('response_type', 'normal')
            if response_type == 'arquivo':
                company_stats[empresa_nome]['arquivo_requests'] += 1
            else:
                company_stats[empresa_nome]['normal_requests'] += 1
            
            processos_encontrados = log.get('total_processos_encontrados', 0)
            company_stats[empresa_nome]['total_processos'] += processos_encontrados
            
            created_at = log.get('created_at')
            if created_at:
                if not company_stats[empresa_nome]['last_interaction'] or created_at > company_stats[empresa_nome]['last_interaction']:
                    company_stats[empresa_nome]['last_interaction'] = created_at
        
        # Calcular médias e converter unique_users para count
        for empresa in company_stats.values():
            empresa['unique_users'] = len(empresa['unique_users'])
            empresa['avg_processos_encontrados'] = round(
                empresa['total_processos'] / empresa['total_interactions'], 1
            ) if empresa['total_interactions'] > 0 else 0
        
        # Converter para lista e ordenar
        top_companies = list(company_stats.values())
        top_companies.sort(key=lambda x: x['total_interactions'], reverse=True)
        
        return jsonify(top_companies[:10])  # Top 10 empresas
        
    except Exception as e:
        logger.error(f"Erro ao obter top empresas do agente: {e}")
        return jsonify([])

@bp.route('/api/agente/recent-interactions')
@role_required(['admin'])
def get_agente_recent_interactions():
    """
    API para interações recentes do agente com paginação
    """
    try:
        # Obter parâmetros de filtro
        date_range = request.args.get('dateRange', '30d')
        empresa_nome = request.args.get('empresa', 'all')
        message_type = request.args.get('messageType', 'all')
        
        # Parâmetros de paginação
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        offset = (page - 1) * limit
        
        # Calcular datas
        end_date = datetime.now()
        if date_range == '1d':
            start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif date_range == '7d':
            start_date = end_date - timedelta(days=7)
        elif date_range == '30d':
            start_date = end_date - timedelta(days=30)
        else:
            start_date = end_date - timedelta(days=30)
        
        # Query base para contagem total
        count_query = supabase_admin.table('agent_interaction_logs').select('id', count='exact')
        count_query = count_query.gte('created_at', start_date.isoformat())
        count_query = count_query.lte('created_at', end_date.isoformat())
        
        if empresa_nome != 'all':
            count_query = count_query.eq('empresa_nome', empresa_nome)
        if message_type != 'all':
            count_query = count_query.eq('message_type', message_type)
        
        # Query para dados paginados
        query = supabase_admin.table('agent_interaction_logs').select('*')
        query = query.gte('created_at', start_date.isoformat())
        query = query.lte('created_at', end_date.isoformat())
        query = query.order('created_at', desc=True)
        query = query.range(offset, offset + limit - 1)
        
        if empresa_nome != 'all':
            query = query.eq('empresa_nome', empresa_nome)
        if message_type != 'all':
            query = query.eq('message_type', message_type)
        
        def _exec_count():
            return count_query.execute()
        def _exec_data():
            return query.execute()
            
        # Executar queries
        count_response = run_with_retries(
            'analytics.get_agente_recent_interactions.count',
            _exec_count,
            max_attempts=3,
            base_delay_seconds=0.8,
            should_retry=lambda e: 'Server disconnected' in str(e) or 'timeout' in str(e).lower()
        )
        
        data_response = run_with_retries(
            'analytics.get_agente_recent_interactions.data',
            _exec_data,
            max_attempts=3,
            base_delay_seconds=0.8,
            should_retry=lambda e: 'Server disconnected' in str(e) or 'timeout' in str(e).lower()
        )
        
        total_records = count_response.count if count_response else 0
        logs = data_response.data if data_response.data else []
        
        # Formatar dados para o frontend
        formatted_logs = []
        for log in logs:
            try:
                # Tratar a data corretamente
                created_at = log.get('created_at')
                if created_at:
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    timestamp = dt.isoformat()
                else:
                    timestamp = None
                
                # Tratar resposta do agente (pode ser JSON)
                agent_response = log.get('agent_response', '')
                if agent_response and agent_response.startswith('{'):
                    try:
                        import json
                        response_obj = json.loads(agent_response)
                        agent_response = response_obj.get('resposta', agent_response)
                    except:
                        pass
                
                formatted_log = {
                    'timestamp': timestamp,
                    'user_name': log.get('user_name', 'N/A'),
                    'whatsapp_number': log.get('whatsapp_number', 'N/A'),
                    'empresa_nome': log.get('empresa_nome', 'N/A'),
                    'user_message': log.get('user_message', 'N/A'),
                    'message_type': log.get('message_type', 'N/A'),
                    'response_type': log.get('response_type', 'N/A'),
                    'agent_response': agent_response[:200] + '...' if len(agent_response) > 200 else agent_response,
                    'total_processos_encontrados': log.get('total_processos_encontrados', 0),
                    'is_successful': log.get('is_successful', True),
                    'response_time_ms': log.get('response_time_ms')
                }
                formatted_logs.append(formatted_log)
            except Exception as format_error:
                logger.warning(f"Erro ao formatar log do agente: {format_error}")
                continue
        
        # Calcular informações de paginação
        total_pages = (total_records + limit - 1) // limit
        has_next = page < total_pages
        has_prev = page > 1
        
        return jsonify({
            'data': formatted_logs,
            'pagination': {
                'current_page': page,
                'total_pages': total_pages,
                'total_records': total_records,
                'limit': limit,
                'has_next': has_next,
                'has_prev': has_prev
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter interações recentes do agente: {e}")
        return jsonify({
            'data': [],
            'pagination': {
                'current_page': 1,
                'total_pages': 0,
                'total_records': 0,
                'limit': 10,
                'has_next': False,
                'has_prev': False
            }
        })
