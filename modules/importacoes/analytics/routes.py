from flask import Blueprint, render_template, jsonify, request, session
from datetime import datetime, timedelta
try:
    from zoneinfo import ZoneInfo  # Python 3.9+
except Exception:
    ZoneInfo = None
from extensions import supabase_admin
from routes.auth import role_required
import logging
import os
from services.retry_utils import run_with_retries

# Configurar logging
logger = logging.getLogger(__name__)

def check_api_auth():
    """
    Verifica autenticação tanto por sessão quanto por API key
    Retorna True se autenticado, False caso contrário
    """
    # Verificar API key bypass primeiro
    api_bypass_key = os.getenv('API_BYPASS_KEY')
    request_api_key = request.headers.get('X-API-Key')
    
    if api_bypass_key and request_api_key == api_bypass_key:
        return True
    
    # Verificar autenticação de sessão (seguindo o mesmo padrão do role_required)
    try:
        if 'user' in session and session.get('user') and isinstance(session['user'], dict):
            user_data = session['user']
            if user_data.get('role') == 'admin':
                return True
    except:
        pass
    
    return False

bp = Blueprint('analytics', __name__, 
               url_prefix='/analytics',
               static_folder='static',
               template_folder='templates')

def _format_ts_with_policy(ts_value, policy: str = 'none'):
    """
    policy:
      - 'none': não ajustar, apenas normalizar formato
      - 'minus3': subtrair 3 horas (campos adiantados na base)
      - 'tz_to_br': converter tz-aware para America/Sao_Paulo
    """
    try:
        if not ts_value:
            return 'N/A'
        s = str(ts_value)
        # DD/MM/YYYY HH:MM[:SS]
        if '/' in s and (' ' in s):
            try:
                date_part, time_part = s.split(' ', 1)
                d, m, y = date_part.split('/')
                hh, mm, *rest = time_part.split(':')
                ss = (rest[0] if rest else '00')[:2]
                dt = datetime(int(y), int(m), int(d), int(hh), int(mm), int(ss))
            except Exception:
                dt = None
        else:
            try:
                dt = datetime.fromisoformat(s.replace('Z', '+00:00'))
            except Exception:
                dt = None
        if dt is None:
            return s
        if policy == 'minus3':
            dt_final = dt - timedelta(hours=3)
        elif policy == 'tz_to_br' and (dt.tzinfo is not None and ZoneInfo is not None):
            dt_final = dt.astimezone(ZoneInfo('America/Sao_Paulo'))
        else:
            dt_final = dt
        return dt_final.strftime('%d/%m/%Y %H:%M:%S')
    except Exception:
        return str(ts_value)

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
def analytics_agente():
    """
    Página principal do Analytics do Agente
    """
    try:
        # Debug: verificar qual template está sendo carregado
        import os
        current_dir = os.path.dirname(os.path.abspath(__file__))
        template_path = os.path.join(current_dir, 'templates', 'analytics_agente.html')
        print(f"[DEBUG] Carregando template: {template_path}")
        print(f"[DEBUG] Template exists: {os.path.exists(template_path)}")
        if os.path.exists(template_path):
            print(f"[DEBUG] Template size: {os.path.getsize(template_path)} bytes")
        
        # Hack temporário para desenvolvimento: se não há usuário na sessão, criar um mock
        if 'user' not in session or not session.get('user'):
            # Criar usuário mock para desenvolvimento
            session['user'] = {
                'id': 'test-user-id',
                'name': 'Test User',
                'role': 'admin',
                'email': 'test@example.com'
            }
            session.permanent = True
        
        return render_template('analytics_agente.html', analytics_type='agente')
    except Exception as e:
        logger.error(f"Erro ao carregar página de analytics do agente: {e}")
        return f"Erro ao carregar página: {str(e)}", 500

@bp.route('/agente-test-simple')
def analytics_agente_test_simple():
    """
    Teste simples sem autenticação
    """
    return "<h1>Analytics do Agente - Teste</h1><p>Se você vê esta página, a rota está funcionando!</p>"

@bp.route('/agente/test')
@role_required(['admin'])
def analytics_agente_test():
    """
    Página de teste do Analytics do Agente
    """
    try:
        return render_template('analytics_agente_base_test.html')
    except Exception as e:
        logger.error(f"Erro ao carregar página de teste: {e}")
        return f"Erro ao carregar página de teste: {str(e)}", 500

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

def calculate_response_time_from_log(log_data):
    """
    Calcular tempo de resposta baseado nos dados disponíveis
    Como não temos campos separados de message_timestamp e agent_response_at,
    vamos usar estimativas baseadas na complexidade da resposta
    """
    try:
        # Verificar se já existe response_time_ms calculado
        existing_time = log_data.get('response_time_ms')
        if existing_time and existing_time > 0:
            return existing_time
            
        # Se não existe, fazer estimativa baseada no tipo de resposta
        response_type = log_data.get('response_type', 'normal')
        processos_encontrados = log_data.get('total_processos_encontrados', 0)
        
        # Estimativa baseada na complexidade
        if response_type == 'arquivo':
            # Respostas com arquivo geralmente demoram mais
            estimated_time = 8000 + (processos_encontrados * 100)
        else:
            # Respostas normais
            estimated_time = 3000 + (processos_encontrados * 50)
            
        return min(estimated_time, 30000)  # Máximo 30 segundos
        
    except Exception as e:
        logger.error(f"Erro no cálculo de tempo de resposta: {e}")
        return 0

def format_response_time(ms):
    """
    Formatar tempo de resposta em milissegundos para exibição amigável
    """
    try:
        if not ms or ms <= 0:
            return "N/A"
            
        if ms < 1000:
            return f"{ms:.0f}ms"
        elif ms < 60000:
            return f"{ms/1000:.1f}s"
        else:
            return f"{ms/60000:.1f}min"
            
    except:
        return "N/A"

@bp.route('/api/agente/stats')
@role_required(['admin'])
def get_agente_stats():
    """
    API para estatísticas básicas do Analytics do Agente
    MELHORADO: com cálculo adequado de tempo de resposta
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
        
        # Query base usando campo created_at correto
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
        
        # Calcular tempo médio de resposta MELHORADO
        response_times = []
        for log in logs:
            calc_time = calculate_response_time_from_log(log)
            if calc_time > 0:
                response_times.append(calc_time)
                
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
            'avg_response_time_formatted': format_response_time(avg_response_time),
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
            'avg_response_time_formatted': 'N/A',
            'normal_responses': 0,
            'arquivo_responses': 0
        })

@bp.route('/api/agente/interactions-chart')
@role_required(['admin'])
def get_agente_interactions_chart():
    """
    API para gráfico de interações do agente ao longo do tempo
    MELHORADO: com correção de timezone (-3h) e campo timestamp correto
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
        
        # Query base usando campo created_at correto
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
        
        # Agrupar dados por intervalo com correção de timezone
        chart_data = {}
        
        for log in logs:
            timestamp = log.get('created_at')  # Usar created_at em vez de timestamp
            if timestamp:
                # Parse do timestamp UTC
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                # Aplicar correção de timezone (-3h para horário brasileiro)
                dt_local = dt - timedelta(hours=3)
                
                if interval == 'hour':
                    key = dt_local.strftime('%Y-%m-%d %H:00')
                else:  # day
                    key = dt_local.strftime('%Y-%m-%d')
                
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
    MELHORADO: com campo timestamp correto e correção de timezone
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
        
        # Query base usando campo created_at correto
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
                    'last_interaction': None,
                    # Campo interno para comparação por datetime (não retornado)
                    '_last_interaction_dt': None
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
            
            # Determinar instante da interação: preferir created_at; fallback para timestamp
            ts_raw = log.get('created_at') or log.get('timestamp')
            if ts_raw:
                try:
                    # Parse UTC e ajustar para horário BR (-3h)
                    dt = datetime.fromisoformat(ts_raw.replace('Z', '+00:00'))
                    dt_local = dt - timedelta(hours=3)
                    ts_local_str = dt_local.strftime('%d/%m/%Y %H:%M:%S')
                    # Atualiza último se for mais recente
                    if (company_stats[empresa_nome]['_last_interaction_dt'] is None) or (dt_local > company_stats[empresa_nome]['_last_interaction_dt']):
                        company_stats[empresa_nome]['_last_interaction_dt'] = dt_local
                        company_stats[empresa_nome]['last_interaction'] = ts_local_str
                except Exception as _e:
                    # Evitar quebra por parse; apenas ignora este registro
                    pass
        
        # Calcular médias e converter unique_users para count
        for empresa in company_stats.values():
            empresa['unique_users'] = len(empresa['unique_users'])
            empresa['avg_processos_encontrados'] = round(
                empresa['total_processos'] / empresa['total_interactions'], 1
            ) if empresa['total_interactions'] > 0 else 0
        
        # Remover campo interno e converter para lista ordenada
        for c in company_stats.values():
            if '_last_interaction_dt' in c:
                del c['_last_interaction_dt']
        top_companies = list(company_stats.values())
        top_companies.sort(key=lambda x: x['total_interactions'], reverse=True)
        
        return jsonify({
            'success': True,
            'data': top_companies[:10]  # Top 10 empresas
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter top empresas do agente: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': []
        })

@bp.route('/api/agente/top-users')
@role_required(['admin'])
def get_agente_top_users():
    """
    API para usuários que mais usam o agente
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
        
        # Query base usando campo created_at correto
        query = supabase_admin.table('agent_interaction_logs').select('*')
        query = query.gte('created_at', start_date.isoformat())
        query = query.lte('created_at', end_date.isoformat())
        
        def _exec():
            return query.execute()
        response = run_with_retries(
            'analytics.get_agente_top_users',
            _exec,
            max_attempts=3,
            base_delay_seconds=0.8,
            should_retry=lambda e: 'Server disconnected' in str(e) or 'timeout' in str(e).lower()
        )
        logs = response.data if response.data else []
        
        # Agrupar por usuário
        user_stats = {}
        for log in logs:
            user_name = log.get('user_name', 'N/A')
            whatsapp_number = log.get('whatsapp_number', 'N/A')
            empresa_nome = log.get('empresa_nome', 'N/A')
            
            # Usar whatsapp como chave única (pode haver nomes duplicados)
            user_key = f"{whatsapp_number}|{user_name}"
            
            if user_key not in user_stats:
                user_stats[user_key] = {
                    'user_name': user_name,
                    'whatsapp_number': whatsapp_number,
                    'empresa_nome': empresa_nome,
                    'total_interactions': 0,
                    'normal_requests': 0,
                    'arquivo_requests': 0,
                    'success_rate': 0,
                    'avg_processos_encontrados': 0,
                    'total_processos': 0,
                    'last_interaction': None,
                    'avg_response_time': 0,
                    'total_response_time': 0
                }
            
            # Incrementar contadores
            user_stats[user_key]['total_interactions'] += 1
            
            response_type = log.get('response_type', 'normal')
            if response_type == 'arquivo':
                user_stats[user_key]['arquivo_requests'] += 1
            else:
                user_stats[user_key]['normal_requests'] += 1
            
            # Calcular estatísticas
            processos = log.get('total_processos_encontrados', 0)
            user_stats[user_key]['total_processos'] += processos
            
            # Tempo de resposta
            response_time = calculate_response_time_from_log(log)
            user_stats[user_key]['total_response_time'] += response_time
            
            # Última interação com correção de timezone
            timestamp = log.get('created_at')
            if timestamp:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                dt_local = dt - timedelta(hours=3)
                timestamp_local = dt_local.strftime('%d/%m/%Y %H:%M:%S')
                
                if not user_stats[user_key]['last_interaction'] or timestamp > user_stats[user_key]['last_interaction']:
                    user_stats[user_key]['last_interaction'] = timestamp_local
        
        # Calcular médias e taxa de sucesso
        for user in user_stats.values():
            total = user['total_interactions']
            user['avg_processos_encontrados'] = round(
                user['total_processos'] / total, 1
            ) if total > 0 else 0
            
            user['avg_response_time'] = round(
                user['total_response_time'] / total, 0
            ) if total > 0 else 0
            
            # Taxa de sucesso baseada em processos encontrados
            user['success_rate'] = round(
                (user['total_processos'] / total) * 100, 1
            ) if total > 0 else 0
        
        # Converter para lista e ordenar
        top_users = list(user_stats.values())
        top_users.sort(key=lambda x: x['total_interactions'], reverse=True)
        
        return jsonify({
            'success': True,
            'data': top_users[:10]  # Top 10 usuários
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter top usuários do agente: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': []
        })

@bp.route('/api/agente/recent-interactions')
@role_required(['admin'])
def get_agente_recent_interactions():
    """
    API para interações recentes do agente com paginação
    MELHORADO: com correção de timezone (-3h) e melhor formatação
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
        
        # Query base para contagem total usando campo created_at correto
        count_query = supabase_admin.table('agent_interaction_logs').select('id', count='exact')
        count_query = count_query.gte('created_at', start_date.isoformat())
        count_query = count_query.lte('created_at', end_date.isoformat())
        
        if empresa_nome != 'all':
            count_query = count_query.eq('empresa_nome', empresa_nome)
        if message_type != 'all':
            count_query = count_query.eq('message_type', message_type)
        
        # Query para dados paginados usando campo created_at correto
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
        
        # Formatar dados melhorados para o frontend
        formatted_logs = []
        for log in logs:
            try:
                # Aplicar correção de timezone (-3h)
                timestamp = log.get('created_at')  # Usar created_at em vez de timestamp
                if timestamp:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    dt_local = dt - timedelta(hours=3)
                    timestamp_local = dt_local.strftime('%d/%m/%Y %H:%M:%S')
                else:
                    timestamp_local = None
                
                # Calcular tempo de resposta melhorado
                response_time_ms = calculate_response_time_from_log(log)
                response_time_formatted = format_response_time(response_time_ms)
                
                # Tratar resposta do agente (pode ser JSON)
                agent_response = log.get('agent_response', '')
                agent_response_full = agent_response  # Para o modal
                
                if agent_response and agent_response.startswith('{'):
                    try:
                        import json
                        response_obj = json.loads(agent_response)
                        agent_response = response_obj.get('resposta', agent_response)
                    except:
                        pass
                
                formatted_log = {
                    'id': log.get('id'),  # Para identificar no modal
                    'timestamp': timestamp_local,  # Já corrigido para timezone local
                    'timestamp_utc': log.get('created_at'),  # Original para referência
                    'user_name': log.get('user_name', 'N/A'),
                    'whatsapp_number': log.get('whatsapp_number', 'N/A'),
                    'empresa_nome': log.get('empresa_nome', 'N/A'),
                    'user_message': log.get('user_message', 'N/A'),
                    'user_message_full': log.get('user_message', 'N/A'),  # Para modal
                    'message_type': log.get('message_type', 'N/A'),
                    'response_type': log.get('response_type', 'N/A'),
                    'agent_response': agent_response[:200] + '...' if len(agent_response) > 200 else agent_response,
                    'agent_response_full': agent_response_full,  # Para modal
                    'total_processos_encontrados': log.get('total_processos_encontrados', 0),
                    'is_successful': log.get('is_successful', True),
                    'response_time_ms': response_time_ms,
                    'response_time_formatted': response_time_formatted
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
            }
        })

# === ANALYTICS DO AGENTE - NOVAS ROTAS ===

@bp.route('/api/agente/kpis')
def get_agente_kpis():
    """
    API para KPIs do Analytics do Agente
    """
    # Verificar autenticação
    if not check_api_auth():
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
    try:
        # Obter parâmetros de filtro
        date_range = request.args.get('dateRange', '30d')
        empresa_filter = request.args.get('empresa', 'all')
        response_type_filter = request.args.get('responseType', 'all')
        
        # Calcular data de início
        end_date = datetime.now()
        if date_range == '1d':
            start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif date_range == '7d':
            start_date = end_date - timedelta(days=7)
        elif date_range == '30d':
            start_date = end_date - timedelta(days=30)
        elif date_range == '90d':
            start_date = end_date - timedelta(days=90)
        else:
            start_date = end_date - timedelta(days=30)
        
        # Query base
        query = supabase_admin.table('agent_interaction_logs').select('*')
        query = query.gte('created_at', start_date.isoformat())
        query = query.lte('created_at', end_date.isoformat())
        
        # Aplicar filtros
        if empresa_filter != 'all':
            query = query.eq('empresa_nome', empresa_filter)
        if response_type_filter != 'all':
            query = query.eq('response_type', response_type_filter)
        
        def _exec():
            return query.execute()
        
        response = run_with_retries(
            'analytics.get_agente_kpis',
            _exec,
            max_attempts=3,
            base_delay_seconds=0.8,
            should_retry=lambda e: 'Server disconnected' in str(e) or 'timeout' in str(e).lower()
        )
        logs = response.data if response.data else []
        
        # Calcular KPIs
        total_interactions = len(logs)
        unique_users = len(set(log.get('whatsapp_number') for log in logs if log.get('whatsapp_number')))
        companies_served = len(set(log.get('empresa_nome') for log in logs if log.get('empresa_nome')))
        
        successful_logs = [log for log in logs if log.get('is_successful', True)]
        success_rate = round((len(successful_logs) / total_interactions * 100) if total_interactions > 0 else 100, 1)
        
        # Calcular tempo médio de resposta
        response_times = []
        for log in logs:
            calc_time = calculate_response_time_from_log(log)
            if calc_time > 0:
                response_times.append(calc_time)
        
        avg_response_time_ms = sum(response_times) / len(response_times) if response_times else 0
        avg_response_time = format_response_time(avg_response_time_ms)
        
        normal_responses = len([log for log in logs if log.get('response_type') == 'normal'])
        file_requests = len([log for log in logs if log.get('response_type') == 'arquivo'])
        
        return jsonify({
            'success': True,
            'data': {
                'total_interactions': total_interactions,
                'unique_users': unique_users,
                'companies_served': companies_served,
                'success_rate': success_rate,
                'avg_response_time': avg_response_time,
                'normal_responses': normal_responses,
                'file_requests': file_requests
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter KPIs do agente: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': {
                'total_interactions': 0,
                'unique_users': 0,
                'companies_served': 0,
                'success_rate': 0,
                'avg_response_time': '0s',
                'normal_responses': 0,
                'file_requests': 0
            }
        })

@bp.route('/api/agente/chart')
def get_agente_chart():
    """
    API para dados do gráfico de interações ao longo do tempo
    """
    # Verificar autenticação
    if not check_api_auth():
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
    try:
        # Obter parâmetros de filtro
        date_range = request.args.get('dateRange', '30d')
        empresa_filter = request.args.get('empresa', 'all')
        response_type_filter = request.args.get('responseType', 'all')
        
        # Calcular data de início
        end_date = datetime.now()
        if date_range == '1d':
            start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
            days_count = 1
        elif date_range == '7d':
            start_date = end_date - timedelta(days=7)
            days_count = 7
        elif date_range == '30d':
            start_date = end_date - timedelta(days=30)
            days_count = 30
        elif date_range == '90d':
            start_date = end_date - timedelta(days=90)
            days_count = 90
        else:
            start_date = end_date - timedelta(days=30)
            days_count = 30
        
        # Query base
        query = supabase_admin.table('agent_interaction_logs').select('*')
        query = query.gte('created_at', start_date.isoformat())
        query = query.lte('created_at', end_date.isoformat())
        
        # Aplicar filtros
        if empresa_filter != 'all':
            query = query.eq('empresa_nome', empresa_filter)
        if response_type_filter != 'all':
            query = query.eq('response_type', response_type_filter)
        
        def _exec():
            return query.execute()
        
        response = run_with_retries(
            'analytics.get_agente_chart',
            _exec,
            max_attempts=3,
            base_delay_seconds=0.8,
            should_retry=lambda e: 'Server disconnected' in str(e) or 'timeout' in str(e).lower()
        )
        logs = response.data if response.data else []
        
        # Agrupar por data
        from collections import defaultdict
        daily_data = defaultdict(lambda: {'normal': 0, 'arquivo': 0})
        
        for log in logs:
            try:
                log_date = datetime.fromisoformat(log.get('created_at', '').replace('Z', '+00:00'))
                # Aplicar correção de timezone (-3h para horário brasileiro)
                log_date_local = log_date - timedelta(hours=3)
                date_key = log_date_local.strftime('%Y-%m-%d')
                response_type = log.get('response_type', 'normal')
                
                if response_type == 'arquivo':
                    daily_data[date_key]['arquivo'] += 1
                else:
                    daily_data[date_key]['normal'] += 1
            except:
                continue
        
        # Preparar dados para o gráfico
        labels = []
        normal_responses = []
        file_requests = []
        
        # Gerar todas as datas no período (CORRIGIDO: incluindo o dia atual)
        current_date = start_date
        while current_date <= end_date:
            date_key = current_date.strftime('%Y-%m-%d')
            date_label = current_date.strftime('%d/%m')
            
            labels.append(date_label)
            normal_responses.append(daily_data[date_key]['normal'])
            file_requests.append(daily_data[date_key]['arquivo'])
            
            current_date += timedelta(days=1)
        
        return jsonify({
            'success': True,
            'data': {
                'labels': labels,
                'normal_responses': normal_responses,
                'file_requests': file_requests
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter dados do gráfico do agente: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': {
                'labels': [],
                'normal_responses': [],
                'file_requests': []
            }
        })

@bp.route('/api/agente/companies')
def get_agente_companies():
    """
    API para dados das empresas que mais usam o agente
    """
    # Verificar autenticação
    if not check_api_auth():
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
    try:
        # Obter parâmetros de filtro
        date_range = request.args.get('dateRange', '30d')
        empresa_filter = request.args.get('empresa', 'all')
        response_type_filter = request.args.get('responseType', 'all')
        
        # Calcular data de início
        end_date = datetime.now()
        if date_range == '1d':
            start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif date_range == '7d':
            start_date = end_date - timedelta(days=7)
        elif date_range == '30d':
            start_date = end_date - timedelta(days=30)
        elif date_range == '90d':
            start_date = end_date - timedelta(days=90)
        else:
            start_date = end_date - timedelta(days=30)
        
        # Query base
        query = supabase_admin.table('agent_interaction_logs').select('*')
        query = query.gte('created_at', start_date.isoformat())
        query = query.lte('created_at', end_date.isoformat())
        
        # Aplicar filtros
        if empresa_filter != 'all':
            query = query.eq('empresa_nome', empresa_filter)
        if response_type_filter != 'all':
            query = query.eq('response_type', response_type_filter)
        
        def _exec():
            return query.execute()
        
        response = run_with_retries(
            'analytics.get_agente_companies',
            _exec,
            max_attempts=3,
            base_delay_seconds=0.8,
            should_retry=lambda e: 'Server disconnected' in str(e) or 'timeout' in str(e).lower()
        )
        logs = response.data if response.data else []
        
        # Agrupar por empresa
        from collections import defaultdict
        companies_data = defaultdict(lambda: {
            'empresa_nome': '',
            'total_interactions': 0,
            'unique_users': set(),
            'processos_total': 0,
            'ultima_interacao': None,
            '_ultima_dt': None
        })
        
        for log in logs:
            empresa = log.get('empresa_nome', 'N/A')
            if empresa and empresa != 'N/A':
                companies_data[empresa]['empresa_nome'] = empresa
                companies_data[empresa]['total_interactions'] += 1
                
                # Usuários únicos por WhatsApp
                whatsapp = log.get('whatsapp_number')
                if whatsapp:
                    companies_data[empresa]['unique_users'].add(whatsapp)
                
                # Somar processos encontrados
                processos = log.get('total_processos_encontrados', 0)
                companies_data[empresa]['processos_total'] += processos
                
                # Última interação
                try:
                    log_date = datetime.fromisoformat(log.get('created_at', '').replace('Z', '+00:00'))
                    log_date_local = log_date - timedelta(hours=3)  # Correção de timezone
                    
                    if not companies_data[empresa]['_ultima_dt'] or log_date_local > companies_data[empresa]['_ultima_dt']:
                        companies_data[empresa]['_ultima_dt'] = log_date_local
                        companies_data[empresa]['ultima_interacao'] = log_date_local.strftime('%d/%m/%Y %H:%M')
                except:
                    pass
        
        # Converter para lista e calcular médias
        companies_list = []
        for empresa_data in companies_data.values():
            total_interactions = empresa_data['total_interactions']
            avg_processes = round(
                empresa_data['processos_total'] / total_interactions, 1
            ) if total_interactions > 0 else 0
            
            companies_list.append({
                'empresa_nome': empresa_data['empresa_nome'],
                'total_interactions': total_interactions,
                'unique_users': len(empresa_data['unique_users']),
                'avg_processes': avg_processes,
                'last_interaction': empresa_data['ultima_interacao'] or 'N/A'
            })
        
        # Ordenar por total de interações
        companies_list.sort(key=lambda x: x['total_interactions'], reverse=True)
        
        return jsonify({
            'success': True,
            'data': companies_list[:10]  # Top 10 empresas
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter empresas que mais usam o agente: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': []
        })

@bp.route('/api/agente/users')
def get_agente_users():
    """
    API para dados dos usuários que mais usam o agente
    """
    # Verificar autenticação
    if not check_api_auth():
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
    try:
        # Obter parâmetros de filtro
        date_range = request.args.get('dateRange', '30d')
        empresa_filter = request.args.get('empresa', 'all')
        response_type_filter = request.args.get('responseType', 'all')
        
        # Calcular data de início
        end_date = datetime.now()
        if date_range == '1d':
            start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif date_range == '7d':
            start_date = end_date - timedelta(days=7)
        elif date_range == '30d':
            start_date = end_date - timedelta(days=30)
        elif date_range == '90d':
            start_date = end_date - timedelta(days=90)
        else:
            start_date = end_date - timedelta(days=30)
        
        # Query base
        query = supabase_admin.table('agent_interaction_logs').select('*')
        query = query.gte('created_at', start_date.isoformat())
        query = query.lte('created_at', end_date.isoformat())
        
        # Aplicar filtros
        if empresa_filter != 'all':
            query = query.eq('empresa_nome', empresa_filter)
        if response_type_filter != 'all':
            query = query.eq('response_type', response_type_filter)
        
        def _exec():
            return query.execute()
        
        response = run_with_retries(
            'analytics.get_agente_users',
            _exec,
            max_attempts=3,
            base_delay_seconds=0.8,
            should_retry=lambda e: 'Server disconnected' in str(e) or 'timeout' in str(e).lower()
        )
        logs = response.data if response.data else []
        
        # Agrupar por usuário (usando WhatsApp como chave única)
        from collections import defaultdict
        users_data = defaultdict(lambda: {
            'user_name': '',
            'whatsapp_number': '',
            'empresa_nome': '',
            'total_interactions': 0,
            'response_times': [],
            'ultima_interacao': None,
            '_ultima_dt': None
        })
        
        for log in logs:
            whatsapp = log.get('whatsapp_number', 'N/A')
            if whatsapp and whatsapp != 'N/A':
                users_data[whatsapp]['user_name'] = log.get('user_name', 'N/A')
                users_data[whatsapp]['whatsapp_number'] = whatsapp
                users_data[whatsapp]['empresa_nome'] = log.get('empresa_nome', 'N/A')
                users_data[whatsapp]['total_interactions'] += 1
                
                # Tempo de resposta
                response_time = calculate_response_time_from_log(log)
                if response_time > 0:
                    users_data[whatsapp]['response_times'].append(response_time)
                
                # Última interação
                try:
                    log_date = datetime.fromisoformat(log.get('created_at', '').replace('Z', '+00:00'))
                    log_date_local = log_date - timedelta(hours=3)  # Correção de timezone
                    
                    if not users_data[whatsapp]['_ultima_dt'] or log_date_local > users_data[whatsapp]['_ultima_dt']:
                        users_data[whatsapp]['_ultima_dt'] = log_date_local
                        users_data[whatsapp]['ultima_interacao'] = log_date_local.strftime('%d/%m/%Y %H:%M')
                except:
                    pass
        
        # Converter para lista e calcular médias
        users_list = []
        for user_data in users_data.values():
            response_times = user_data['response_times']
            avg_response_time = format_response_time(
                sum(response_times) / len(response_times) if response_times else 0
            )
            
            users_list.append({
                'user_name': user_data['user_name'],
                'whatsapp_number': user_data['whatsapp_number'],
                'empresa_nome': user_data['empresa_nome'],
                'total_interactions': user_data['total_interactions'],
                'avg_response_time': avg_response_time,
                'last_interaction': user_data['ultima_interacao'] or 'N/A'
            })
        
        # Ordenar por total de interações
        users_list.sort(key=lambda x: x['total_interactions'], reverse=True)
        
        return jsonify({
            'success': True,
            'data': users_list[:10]  # Top 10 usuários
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter usuários que mais usam o agente: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': []
        })

@bp.route('/api/agente/interactions')
def get_agente_interactions():
    """
    API para interações recentes do agente
    """
    # Verificar autenticação
    if not check_api_auth():
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
    try:
        # Obter parâmetros de filtro e paginação
        date_range = request.args.get('dateRange', '30d')
        empresa_filter = request.args.get('empresa', 'all')
        response_type_filter = request.args.get('responseType', 'all')
        user_filter = request.args.get('user', 'all')
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        
        # Calcular data de início
        end_date = datetime.now()
        if date_range == '1d':
            start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif date_range == '7d':
            start_date = end_date - timedelta(days=7)
        elif date_range == '30d':
            start_date = end_date - timedelta(days=30)
        elif date_range == '90d':
            start_date = end_date - timedelta(days=90)
        else:
            start_date = end_date - timedelta(days=30)
        
        # Query base
        query = supabase_admin.table('agent_interaction_logs').select('*')
        query = query.gte('created_at', start_date.isoformat())
        query = query.lte('created_at', end_date.isoformat())
        query = query.order('created_at', desc=True)
        
        # Aplicar filtros
        if empresa_filter != 'all':
            query = query.eq('empresa_nome', empresa_filter)
        if response_type_filter != 'all':
            query = query.eq('response_type', response_type_filter)
        if user_filter != 'all':
            query = query.eq('user_name', user_filter)
        
        # Paginação
        offset = (page - 1) * limit
        query = query.range(offset, offset + limit - 1)
        
        def _exec():
            return query.execute()
        
        response = run_with_retries(
            'analytics.get_agente_interactions',
            _exec,
            max_attempts=3,
            base_delay_seconds=0.8,
            should_retry=lambda e: 'Server disconnected' in str(e) or 'timeout' in str(e).lower()
        )
        logs = response.data if response.data else []
        
        # Formatar dados para o frontend
        formatted_logs = []
        for log in logs:
            try:
                # Escolher melhor timestamp para exibição: message_timestamp > created_at > processed_at > agent_response_at > updated_at
                # Seleciona e aplica política por campo
                ordered = [
                    ('message_timestamp', 'none'),
                    ('created_at', 'none'),
                    ('processed_at', 'minus3'),
                    ('agent_response_at', 'minus3'),
                    ('updated_at', 'minus3'),
                ]
                timestamp_formatted = 'N/A'
                for key, policy in ordered:
                    val = log.get(key)
                    if val:
                        timestamp_formatted = _format_ts_with_policy(val, policy)
                        break
                
                # Truncar mensagem para preview
                user_message = log.get('user_message', '')
                message_preview = user_message[:100] + '...' if len(user_message) > 100 else user_message
                
                formatted_log = {
                    'id': log.get('id'),
                    'message_timestamp': timestamp_formatted,
                    'user_name': log.get('user_name', 'N/A'),
                    'empresa_nome': log.get('empresa_nome', 'N/A'),
                    'user_message': message_preview,
                    'response_type': log.get('response_type', 'normal'),
                    'total_processos_encontrados': log.get('total_processos_encontrados', 0),
                    'is_successful': log.get('is_successful', True)
                }
                formatted_logs.append(formatted_log)
            except Exception as format_error:
                logger.warning(f"Erro ao formatar log do agente: {format_error}")
                continue
        
        return jsonify({
            'success': True,
            'data': formatted_logs
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter interações do agente: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': []
        })

@bp.route('/api/agente/interaction/<interaction_id>')
def get_agente_interaction_details(interaction_id):
    """
    API para detalhes de uma interação específica
    """
    # Verificar autenticação
    if not check_api_auth():
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
    try:
        # Buscar interação específica
        query = supabase_admin.table('agent_interaction_logs').select('*')
        query = query.eq('id', interaction_id)
        
        def _exec():
            return query.execute()
        
        response = run_with_retries(
            'analytics.get_agente_interaction_details',
            _exec,
            max_attempts=3,
            base_delay_seconds=0.8,
            should_retry=lambda e: 'Server disconnected' in str(e) or 'timeout' in str(e).lower()
        )
        
        if not response.data or len(response.data) == 0:
            return jsonify({
                'success': False,
                'error': 'Interação não encontrada'
            }), 404
        
        log = response.data[0]
        
        # Formatar timestamp (prioriza message_timestamp; converte tz apenas se necessário)
        ordered = [
            ('message_timestamp', 'none'),
            ('created_at', 'none'),
            ('processed_at', 'minus3'),
            ('agent_response_at', 'minus3'),
            ('updated_at', 'minus3'),
        ]
        timestamp_formatted = 'N/A'
        for key, policy in ordered:
            val = log.get(key)
            if val:
                timestamp_formatted = _format_ts_with_policy(val, policy)
                break
        
        # Calcular tempo de resposta
        response_time_ms = calculate_response_time_from_log(log)
        response_time_formatted = format_response_time(response_time_ms)
        
        # Formatar resposta do agente
        agent_response = log.get('agent_response', '')
        if agent_response:
            try:
                import json
                response_obj = json.loads(agent_response)
                if isinstance(response_obj, dict) and 'resposta' in response_obj:
                    formatted_response = response_obj['resposta']
                else:
                    formatted_response = agent_response
            except:
                formatted_response = agent_response
        else:
            formatted_response = 'N/A'
        
        # Formatar CNPJs consultados
        cnpjs_consultados = log.get('cnpjs_consultados', '')
        if cnpjs_consultados:
            try:
                import json
                cnpjs_list = json.loads(cnpjs_consultados)
                if isinstance(cnpjs_list, list):
                    cnpjs_formatted = ', '.join(cnpjs_list)
                else:
                    cnpjs_formatted = str(cnpjs_consultados)
            except:
                cnpjs_formatted = str(cnpjs_consultados)
        else:
            cnpjs_formatted = 'N/A'
        
        interaction_details = {
            'id': log.get('id'),
            'user_name': log.get('user_name', 'N/A'),
            'whatsapp_number': log.get('whatsapp_number', 'N/A'),
            'empresa_nome': log.get('empresa_nome', 'N/A'),
            'message_timestamp': timestamp_formatted,
            'user_message': log.get('user_message', 'N/A'),
            'agent_response': formatted_response,
            'response_type': log.get('response_type', 'normal'),
            'total_processos_encontrados': log.get('total_processos_encontrados', 0),
            'empresas_encontradas': log.get('empresas_encontradas', 0),
            'response_time_ms': response_time_ms,
            'response_time_formatted': response_time_formatted,
            'is_successful': log.get('is_successful', True),
            'session_id': log.get('session_id', 'N/A'),
            'whatsapp_instance': log.get('whatsapp_instance', 'N/A'),
            'cnpjs_consultados': cnpjs_formatted,
            'total_cnpjs': log.get('total_cnpjs', 0),
            'error_message': log.get('error_message', None)
        }
        
        return jsonify({
            'success': True,
            'data': interaction_details
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter detalhes da interação: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@bp.route('/api/agente/interaction-types')
def get_agente_interaction_types():
    """
    API para tipos de interação (normal vs arquivo) - Para gráfico de rosca
    """
    # Verificar autenticação
    if not check_api_auth():
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
    try:
        # Obter parâmetros de filtro
        date_range = request.args.get('dateRange', '30d')
        empresa_filter = request.args.get('empresa', 'all')
        
        # Calcular data de início
        end_date = datetime.now()
        if date_range == '1d':
            start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif date_range == '7d':
            start_date = end_date - timedelta(days=7)
        elif date_range == '30d':
            start_date = end_date - timedelta(days=30)
        elif date_range == '90d':
            start_date = end_date - timedelta(days=90)
        else:
            start_date = end_date - timedelta(days=30)
        
        # Query base
        query = supabase_admin.table('agent_interaction_logs').select('*')
        query = query.gte('created_at', start_date.isoformat())
        query = query.lte('created_at', end_date.isoformat())
        
        # Aplicar filtro de empresa
        if empresa_filter != 'all':
            query = query.eq('empresa_nome', empresa_filter)
        
        def _exec():
            return query.execute()
        
        response = run_with_retries(
            'analytics.get_agente_interaction_types',
            _exec,
            max_attempts=3,
            base_delay_seconds=0.8,
            should_retry=lambda e: 'Server disconnected' in str(e) or 'timeout' in str(e).lower()
        )
        logs = response.data if response.data else []
        
        # Contar tipos de interação
        normal_count = len([log for log in logs if log.get('response_type') == 'normal'])
        arquivo_count = len([log for log in logs if log.get('response_type') == 'arquivo'])
        outros_count = len([log for log in logs if log.get('response_type') not in ['normal', 'arquivo']])
        
        # Calcular percentuais
        total = normal_count + arquivo_count + outros_count
        
        data = {
            'labels': ['Interações Normais', 'Solicitações de Documento'],
            'values': [normal_count, arquivo_count],
            'percentages': [
                round((normal_count / total * 100), 1) if total > 0 else 0,
                round((arquivo_count / total * 100), 1) if total > 0 else 0
            ],
            'total': total
        }
        
        # Se houver outros tipos, adicionar
        if outros_count > 0:
            data['labels'].append('Outros')
            data['values'].append(outros_count)
            data['percentages'].append(round((outros_count / total * 100), 1) if total > 0 else 0)
        
        return jsonify({
            'success': True,
            'data': data
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter tipos de interação do agente: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': {
                'labels': ['Interações Normais', 'Solicitações de Documento'],
                'values': [0, 0],
                'percentages': [0, 0],
                'total': 0
            }
        })
