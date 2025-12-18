from flask import Blueprint, render_template, jsonify, request, session
from datetime import datetime, timedelta
try:
    from zoneinfo import ZoneInfo  # Python 3.9+
except Exception:
    ZoneInfo = None
import pytz  # Adicionar import do pytz
from extensions import supabase_admin
from modules.auth.routes import login_required
from services.perfil_access_service import PerfilAccessService
import logging
import os
from services.retry_utils import run_with_retries

# Configurar logging
logger = logging.getLogger(__name__)

def check_api_auth():
    """
    Verifica autenticação tanto por sessão quanto por API key
    Retorna True se autenticado, False caso contrário
    Aceita: Master Admin (role='admin') ou Module Admins (role='interno_unique' com perfil_principal=admin_*)
    """
    # Verificar API key bypass primeiro
    api_bypass_key = os.getenv('API_BYPASS_KEY')
    request_api_key = request.headers.get('X-API-Key')
    
    if api_bypass_key and request_api_key == api_bypass_key:
        return True
    
    # Verificar autenticação de sessão
    try:
        if 'user' in session and session.get('user') and isinstance(session['user'], dict):
            user_data = session['user']
            user_role = user_data.get('role')
            
            # Master Admin sempre tem acesso
            if user_role == 'admin':
                return True
            
            # Module Admins (interno_unique com perfil admin_*)
            if user_role == 'interno_unique':
                perfil_principal = user_data.get('perfil_principal', '')
                # Qualquer perfil que comece com 'admin_' tem acesso ao analytics
                if perfil_principal.startswith('admin_'):
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
@login_required
def analytics_dashboard():
    """
    Página principal do Analytics do Portal
    Acesso: Todos os admins (master_admin, admin_operacao, admin_financeiro, admin_recursos_humanos)
    """
    try:
        # Verificar se usuário tem acesso ao analytics_portal
        accessible_modules = PerfilAccessService.get_user_accessible_modules()
        if 'analytics_portal' not in accessible_modules and 'analytics' not in accessible_modules:
            logger.warning(f"Usuário sem permissão para acessar analytics portal. Módulos: {accessible_modules}")
            return render_template('errors/403.html'), 403
            
        return render_template('analytics.html', analytics_type='portal')
    except Exception as e:
        logger.error(f"Erro ao carregar página de analytics: {e}")
        return f"Erro ao carregar página: {str(e)}", 500

@bp.route('/agente')
@login_required
def analytics_agente():
    """
    Página principal do Analytics do Agente
    Acesso: Todos os admins (master_admin, admin_operacao, admin_financeiro, admin_recursos_humanos)
    """
    try:
        # Verificar se usuário tem acesso ao analytics_agente
        accessible_modules = PerfilAccessService.get_user_accessible_modules()
        if 'analytics_agente' not in accessible_modules and 'analytics' not in accessible_modules:
            logger.warning(f"Usuário sem permissão para acessar analytics agente. Módulos: {accessible_modules}")
            return render_template('errors/403.html'), 403
        
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
@login_required
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
@login_required
def get_stats():
    """
    API para estatísticas básicas do Analytics
    OTIMIZADO: Usa vw_analytics_portal para filtros otimizados
    """
    try:
        # Obter parâmetros de filtro
        date_range = request.args.get('dateRange', '30d')
        user_role = request.args.get('userRole', 'all')
        
        # Calcular datas com timezone do Brasil (UTC-3)
        try:
            from zoneinfo import ZoneInfo
            br_tz = ZoneInfo('America/Sao_Paulo')
        except:
            import pytz
            br_tz = pytz.timezone('America/Sao_Paulo')
        
        end_date = datetime.now(br_tz).date()
        if date_range == '1d':
            start_date = end_date
        elif date_range == '7d':
            start_date = end_date - timedelta(days=7)
        elif date_range == '30d':
            start_date = end_date - timedelta(days=30)
        else:
            start_date = end_date - timedelta(days=30)
        
        # Query base usando view otimizada (já filtra action_type='page_access' e exclui APIs/sistema)
        query = supabase_admin.table('vw_analytics_portal').select('*')
        query = query.gte('access_date', start_date.isoformat())
        query = query.lte('access_date', end_date.isoformat())
        
        if user_role != 'all':
            query = query.eq('user_role', user_role)
        
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

        # Calcular estatísticas (view já filtra page_access)
        total_access = len(logs)
        unique_users = len(set(log.get('user_id') for log in logs if log.get('user_id')))

        # CORREÇÃO: Logins hoje - contar USUÁRIOS ÚNICOS que fizeram login hoje
        today_start = datetime.now(br_tz).replace(hour=0, minute=0, second=0, microsecond=0)
        # Converter para UTC corretamente
        import pytz as tz_lib
        today_start_utc = today_start.astimezone(tz_lib.UTC)
        
        try:
            def _exec_today():
                # Contar usuários ativos hoje (qualquer ação no log conta como "login/acesso" para o dia)
                # Isso garante que mostre dados mesmo se o evento explícito de login não foi capturado
                return supabase_admin.table('access_logs')\
                    .select('user_id, ip_address')\
                    .gte('created_at', today_start_utc.isoformat())\
                    .execute()
            
            logins_today_response = run_with_retries(
                'analytics.get_stats.logins_today',
                _exec_today,
                max_attempts=3,
                base_delay_seconds=0.8,
                should_retry=lambda e: 'Server disconnected' in str(e) or 'timeout' in str(e).lower()
            )
            
            logins_data = logins_today_response.data if logins_today_response.data else []
            
            # Contar USUÁRIOS ÚNICOS que fizeram login hoje
            unique_users_today = set()
            for log in logins_data:
                # Filtrar localhost apenas se IP for explicitamente 127.0.0.1
                # (Assumindo que o bug do IP foi corrigido e usuários reais terão IPs reais)
                if log.get('ip_address') not in ['127.0.0.1', 'localhost', None]:
                    if log.get('user_id'):
                        unique_users_today.add(log.get('user_id'))
            
            logins_today = len(unique_users_today)
            logger.info(f"[ANALYTICS] Logins hoje: {logins_today} usuários únicos de {len(logins_data)} registros de login")
        except Exception as e:
            logger.warning(f"Erro ao contar logins de hoje: {e}")
            logins_today = 0

        # CORREÇÃO: Total de logins (todos os tempos) - usar user_sessions
        try:
            def _exec_total():
                return supabase_admin.table('user_sessions').select('user_id', count='exact').execute()
            total_sessions_response = run_with_retries(
                'analytics.get_stats.total_logins',
                _exec_total,
                max_attempts=3,
                base_delay_seconds=0.8,
                should_retry=lambda e: 'Server disconnected' in str(e) or 'timeout' in str(e).lower()
            )
            all_sessions = total_sessions_response.data if total_sessions_response.data else []
            # Filtrar localhost
            all_sessions = [s for s in all_sessions if s.get('ip_address') != '127.0.0.1' and s.get('ip_address') != 'localhost']
            total_logins = len(all_sessions)
        except Exception as e:
            logger.warning(f"Erro ao contar total de logins: {e}")
            total_logins = 0

        # CORREÇÃO: Sessão média - calcular com base em sessões que têm disconnected_at
        try:
            def _exec_sessions():
                return supabase_admin.table('user_sessions').select('*').not_.is_('disconnected_at', 'null').limit(500).execute()
            sessions_response = run_with_retries(
                'analytics.get_stats.avg_session',
                _exec_sessions,
                max_attempts=3,
                base_delay_seconds=0.8,
                should_retry=lambda e: 'Server disconnected' in str(e) or 'timeout' in str(e).lower()
            )
            sessions_with_duration = sessions_response.data if sessions_response.data else []
            
            durations = []
            for session in sessions_with_duration:
                connected_at = session.get('connected_at')
                disconnected_at = session.get('disconnected_at')
                
                if connected_at and disconnected_at:
                    try:
                        dt_connected = datetime.fromisoformat(connected_at.replace('Z', '+00:00'))
                        dt_disconnected = datetime.fromisoformat(disconnected_at.replace('Z', '+00:00'))
                        duration_minutes = (dt_disconnected - dt_connected).total_seconds() / 60
                        
                        # Filtrar sessões muito longas (> 12 horas) ou muito curtas (< 1 minuto)
                        if 1 <= duration_minutes <= 720:
                            durations.append(duration_minutes)
                    except:
                        pass
            
            if durations:
                avg_session_minutes = int(sum(durations) / len(durations))
            else:
                avg_session_minutes = 0
        except Exception as e:
            logger.warning(f"Erro ao calcular sessão média: {e}")
            avg_session_minutes = 0

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
@login_required
def get_charts():
    """
    API para dados dos gráficos
    OTIMIZADO: Usa vw_analytics_portal com colunas access_date e access_hour
    """
    try:
        # Obter parâmetros de filtro
        date_range = request.args.get('dateRange', '30d')
        user_role = request.args.get('userRole', 'all')
        
        # Calcular datas com timezone do Brasil (UTC-3)
        try:
            from zoneinfo import ZoneInfo
            br_tz = ZoneInfo('America/Sao_Paulo')
        except:
            import pytz
            br_tz = pytz.timezone('America/Sao_Paulo')
        
        end_date = datetime.now(br_tz).date()
        if date_range == '1d':
            start_date = end_date
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
        
        # Query usando view otimizada (já filtra action_type='page_access' e exclui APIs/sistema)
        query = supabase_admin.table('vw_analytics_portal').select('*')
        query = query.gte('access_date', start_date.isoformat())
        query = query.lte('access_date', end_date.isoformat())
        
        if user_role != 'all':
            query = query.eq('user_role', user_role)
        
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
        
        # Acessos diários usando access_date da view
        from collections import Counter, defaultdict
        
        logs_by_date = defaultdict(list)
        for log in logs:
            access_date = log.get('access_date')
            if access_date:
                logs_by_date[access_date].append(log)
        
        # Processar todos os dias do período
        daily_access = []
        daily_users = []
        today_br = datetime.now(br_tz).date()
        
        for i in range(days_back + 1):
            day = start_date + timedelta(days=i)
            if day > today_br:
                break
            
            day_str = day.isoformat()
            logs_day = logs_by_date.get(day_str, [])
            unique_users_day = set(log.get('user_id') for log in logs_day if log.get('user_id'))
            
            daily_access.append({
                'date': day_str,
                'count': len(logs_day)
            })
            daily_users.append({
                'date': day_str,
                'count': len(unique_users_day)
            })
        
        logger.info(f"[ANALYTICS] Processando {len(logs)} logs para acessos diários")
        logger.info(f"[ANALYTICS] Total de dias: {len(daily_access)}")
        
        # Top páginas
        page_counts = Counter(log.get('page_name', 'Sem nome') for log in logs if log.get('user_name'))
        top_pages = [
            {'page_name': page, 'count': count}
            for page, count in page_counts.most_common()
        ]
        
        # Atividade de usuários
        user_counts = Counter(log.get('user_name') for log in logs if log.get('user_name'))
        users_activity = [
            {'user_name': user, 'access_count': count}
            for user, count in user_counts.most_common()
        ]
        
        # Mapa de calor por horário usando access_hour da view
        hourly_counts = Counter()
        hourly_users = defaultdict(set)
        
        for log in logs:
            if log.get('user_name'):
                hour = log.get('access_hour')
                if hour is not None:
                    hour = int(hour)
                    hourly_counts[hour] += 1
                    user_id = log.get('user_id')
                    if user_id:
                        hourly_users[hour].add(user_id)
        
        hourly_heatmap = [
            {
                'hour': hour,
                'count': hourly_counts.get(hour, 0),
                'unique_users': len(hourly_users.get(hour, set()))
            }
            for hour in range(24)
        ]
        
        return jsonify({
            'success': True,
            'daily_access': daily_access,
            'daily_users': daily_users,
            'top_pages': top_pages,
            'users_activity': users_activity,
            'hourly_heatmap': hourly_heatmap
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter dados de gráficos: {e}")
        return jsonify({
            'success': True,
            'daily_access': [],
            'top_pages': [],
            'users_activity': [],
            'hourly_heatmap': [],
            'error': str(e)
        })

@bp.route('/api/top-users')
@login_required
def get_top_users():
    """
    API para dados dos top usuários
    OTIMIZADO: Usa vw_analytics_portal
    """
    try:
        # Obter parâmetros de filtro
        date_range = request.args.get('dateRange', '30d')
        user_role = request.args.get('userRole', 'all')
        
        # Calcular datas
        end_date = datetime.now().date()
        if date_range == '1d':
            start_date = end_date
        elif date_range == '7d':
            start_date = end_date - timedelta(days=7)
        elif date_range == '30d':
            start_date = end_date - timedelta(days=30)
        else:
            start_date = end_date - timedelta(days=30)
        
        # Query usando view otimizada (já filtra action_type='page_access')
        query = supabase_admin.table('vw_analytics_portal').select('*')
        query = query.gte('access_date', start_date.isoformat())
        query = query.lte('access_date', end_date.isoformat())
        
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

        # Agrupar por usuário (view já filtra page_access)
        user_stats = {}
        for log in logs:
            user_id = log.get('user_id')
            user_name = log.get('user_name')
            
            if not user_id or not user_name:
                continue
            
            if user_id not in user_stats:
                user_stats[user_id] = {
                    'user_id': user_id,
                    'user_name': user_name,
                    'user_email': log.get('user_email', 'N/A'),
                    'user_role': log.get('user_role', 'N/A'),
                    'total_access': 0,
                    'last_access': None,
                    'favorite_pages': []
                }
            
            user_stats[user_id]['total_access'] += 1
            page_name = log.get('page_name', 'N/A')
            if page_name not in user_stats[user_id]['favorite_pages']:
                user_stats[user_id]['favorite_pages'].append(page_name)
            
            # Usar access_timestamp_br para último acesso
            log_time = log.get('access_timestamp_br')
            if log_time and (not user_stats[user_id]['last_access'] or log_time > user_stats[user_id]['last_access']):
                user_stats[user_id]['last_access'] = log_time

        # Converter para lista e ordenar
        top_users = list(user_stats.values())
        top_users.sort(key=lambda x: x['total_access'], reverse=True)

        # Limitar páginas favoritas
        for user in top_users:
            user['favorite_pages'] = ', '.join(user['favorite_pages'][:3])

        return jsonify(top_users[:20])
        
    except Exception as e:
        logger.error(f"Erro ao obter top usuários: {e}")
        return jsonify([])

@bp.route('/api/recent-activity')
@login_required
def get_recent_activity():
    """
    API para atividade recente (últimos 7 dias por padrão)
    OTIMIZADO: Usa vw_analytics_portal
    """
    try:
        # Obter parâmetros de filtro
        date_range = request.args.get('dateRange', '30d')
        user_role = request.args.get('userRole', 'all')
        
        # Calcular datas - forçar pelo menos 7 dias para a tabela de atividades recentes
        end_date = datetime.now().date()
        if date_range == '1d':
            start_date = end_date - timedelta(days=7)
        elif date_range == '7d':
            start_date = end_date - timedelta(days=7)
        elif date_range == '30d':
            start_date = end_date - timedelta(days=30)
        else:
            start_date = end_date - timedelta(days=7)
        
        # Query usando view otimizada (já filtra page_access e exclui sistema)
        query = supabase_admin.table('vw_analytics_portal').select('*')
        query = query.gte('access_date', start_date.isoformat())
        query = query.lte('access_date', end_date.isoformat())
        query = query.not_.is_('user_name', 'null')
        query = query.order('access_timestamp_br', desc=True)
        query = query.limit(150)
        
        if user_role != 'all':
            query = query.eq('user_role', user_role)
        
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
        
        # Formatar dados para o frontend
        formatted_logs = []
        for log in logs:
            try:
                formatted_log = {
                    'timestamp': log.get('access_timestamp_br'),
                    'user_name': log.get('user_name', 'N/A'),
                    'user_email': log.get('user_email', 'N/A'),
                    'action_type': log.get('action_type', 'page_access'),
                    'page_name': log.get('page_name', 'N/A'),
                    'module_name': log.get('module_name', 'N/A'),
                    'device_type': log.get('device_type', 'N/A'),
                    'browser': log.get('browser', 'N/A')
                }
                formatted_logs.append(formatted_log)
            except Exception as format_error:
                logger.warning(f"Erro ao formatar log: {format_error}")
                continue
        return jsonify(formatted_logs)
        
    except Exception as e:
        logger.error(f"Erro ao obter atividade recente: {e}")
        return jsonify([])

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


# ======== NOVAS ROTAS OTIMIZADAS - ANALYTICS DO PORTAL ========

@bp.route('/api/portal/kpis')
@login_required
def get_portal_kpis():
    """
    API para KPIs principais do Portal usando view otimizada
    """
    try:
        # Obter filtros
        date_range = request.args.get('dateRange', '30d')
        user_role_filter = request.args.get('userRole', 'all')
        module_filter = request.args.get('moduleName', 'all')
        
        # Calcular período
        end_date = datetime.now().date()
        if date_range == '1d':
            start_date = end_date
        elif date_range == '7d':
            start_date = end_date - timedelta(days=7)
        elif date_range == '30d':
            start_date = end_date - timedelta(days=30)
        else:
            start_date = end_date - timedelta(days=30)
        
        # Query base usando a view otimizada
        query = supabase_admin.table('vw_analytics_portal').select('*')
        query = query.gte('access_date', start_date.isoformat())
        query = query.lte('access_date', end_date.isoformat())
        query = query.eq('action_type', 'page_access')  # Apenas acessos a páginas
        
        if user_role_filter != 'all':
            query = query.eq('user_role', user_role_filter)
        if module_filter != 'all':
            query = query.eq('module_name', module_filter)
        
        response = query.execute()
        logs = response.data if response.data else []
        
        # Calcular KPIs
        total_access = len(logs)
        unique_users = len(set(log['user_id'] for log in logs if log.get('user_id')))
        
        # Tempo médio de resposta (apenas sucessos)
        successful_logs = [log for log in logs if log.get('is_successful')]
        if successful_logs and any(log.get('response_time_ms') for log in successful_logs):
            valid_times = [log['response_time_ms'] for log in successful_logs if log.get('response_time_ms') and log['response_time_ms'] > 0]
            avg_response_time = int(sum(valid_times) / len(valid_times)) if valid_times else 0
        else:
            avg_response_time = 0
        
        # Taxa de sucesso
        success_rate = round((len(successful_logs) / total_access * 100), 2) if total_access > 0 else 100.0
        
        return jsonify({
            'success': True,
            'data': {
                'total_access': total_access,
                'unique_users': unique_users,
                'avg_response_time_ms': avg_response_time,
                'success_rate': success_rate
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter KPIs do portal: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': {
                'total_access': 0,
                'unique_users': 0,
                'avg_response_time_ms': 0,
                'success_rate': 100.0
            }
        })

@bp.route('/api/portal/timeline')
@login_required
def get_portal_timeline():
    """
    API para gráfico de acessos ao longo do tempo
    """
    try:
        date_range = request.args.get('dateRange', '30d')
        user_role_filter = request.args.get('userRole', 'all')
        module_filter = request.args.get('moduleName', 'all')
        
        end_date = datetime.now().date()
        if date_range == '1d':
            start_date = end_date
        elif date_range == '7d':
            start_date = end_date - timedelta(days=7)
        elif date_range == '30d':
            start_date = end_date - timedelta(days=30)
        else:
            start_date = end_date - timedelta(days=30)
        
        query = supabase_admin.table('vw_analytics_portal').select('access_date')
        query = query.gte('access_date', start_date.isoformat())
        query = query.lte('access_date', end_date.isoformat())
        query = query.eq('action_type', 'page_access')
        
        if user_role_filter != 'all':
            query = query.eq('user_role', user_role_filter)
        if module_filter != 'all':
            query = query.eq('module_name', module_filter)
        
        response = query.execute()
        logs = response.data if response.data else []
        
        # Agrupar por data
        from collections import Counter
        dates_count = Counter(log['access_date'] for log in logs if log.get('access_date'))
        
        # Gerar todas as datas do período
        date_list = []
        current = start_date
        while current <= end_date:
            date_list.append(current)
            current += timedelta(days=1)
        
        # Formatar resposta
        labels = [d.strftime('%d/%m') for d in date_list]
        values = [dates_count.get(d.isoformat(), 0) for d in date_list]
        
        return jsonify({
            'success': True,
            'data': {
                'labels': labels,
                'values': values
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter timeline: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': {'labels': [], 'values': []}
        })

@bp.route('/api/portal/top-modules')
@login_required
def get_portal_top_modules():
    """
    API para Top 5 módulos mais acessados
    """
    try:
        date_range = request.args.get('dateRange', '30d')
        user_role_filter = request.args.get('userRole', 'all')
        
        end_date = datetime.now().date()
        if date_range == '1d':
            start_date = end_date
        elif date_range == '7d':
            start_date = end_date - timedelta(days=7)
        elif date_range == '30d':
            start_date = end_date - timedelta(days=30)
        else:
            start_date = end_date - timedelta(days=30)
        
        query = supabase_admin.table('vw_analytics_portal').select('module_name')
        query = query.gte('access_date', start_date.isoformat())
        query = query.lte('access_date', end_date.isoformat())
        query = query.eq('action_type', 'page_access')
        
        if user_role_filter != 'all':
            query = query.eq('user_role', user_role_filter)
        
        response = query.execute()
        logs = response.data if response.data else []
        
        # Contar módulos
        from collections import Counter
        modules_count = Counter(log['module_name'] for log in logs if log.get('module_name'))
        top_modules = modules_count.most_common(5)
        
        labels = [mod[0] for mod in top_modules]
        values = [mod[1] for mod in top_modules]
        
        return jsonify({
            'success': True,
            'data': {
                'labels': labels,
                'values': values
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter top módulos: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': {'labels': [], 'values': []}
        })

@bp.route('/api/portal/device-breakdown')
@login_required
def get_portal_device_breakdown():
    """
    API para distribuição por tipo de dispositivo
    """
    try:
        date_range = request.args.get('dateRange', '30d')
        user_role_filter = request.args.get('userRole', 'all')
        module_filter = request.args.get('moduleName', 'all')
        
        end_date = datetime.now().date()
        if date_range == '1d':
            start_date = end_date
        elif date_range == '7d':
            start_date = end_date - timedelta(days=7)
        elif date_range == '30d':
            start_date = end_date - timedelta(days=30)
        else:
            start_date = end_date - timedelta(days=30)
        
        query = supabase_admin.table('vw_analytics_portal').select('device_type')
        query = query.gte('access_date', start_date.isoformat())
        query = query.lte('access_date', end_date.isoformat())
        query = query.eq('action_type', 'page_access')
        
        if user_role_filter != 'all':
            query = query.eq('user_role', user_role_filter)
        if module_filter != 'all':
            query = query.eq('module_name', module_filter)
        
        response = query.execute()
        logs = response.data if response.data else []
        
        # Contar dispositivos
        from collections import Counter
        devices_count = Counter(log['device_type'] for log in logs if log.get('device_type'))
        
        labels = list(devices_count.keys())
        values = list(devices_count.values())
        
        return jsonify({
            'success': True,
            'data': {
                'labels': labels,
                'values': values
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter breakdown de dispositivos: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': {'labels': [], 'values': []}
        })

@bp.route('/api/portal/top-pages')
@login_required
def get_portal_top_pages():
    """
    API para Top 10 páginas mais acessadas
    """
    try:
        date_range = request.args.get('dateRange', '30d')
        user_role_filter = request.args.get('userRole', 'all')
        module_filter = request.args.get('moduleName', 'all')
        
        end_date = datetime.now().date()
        if date_range == '1d':
            start_date = end_date
        elif date_range == '7d':
            start_date = end_date - timedelta(days=7)
        elif date_range == '30d':
            start_date = end_date - timedelta(days=30)
        else:
            start_date = end_date - timedelta(days=30)
        
        query = supabase_admin.table('vw_analytics_portal').select('page_name')
        query = query.gte('access_date', start_date.isoformat())
        query = query.lte('access_date', end_date.isoformat())
        query = query.eq('action_type', 'page_access')
        
        if user_role_filter != 'all':
            query = query.eq('user_role', user_role_filter)
        if module_filter != 'all':
            query = query.eq('module_name', module_filter)
        
        response = query.execute()
        logs = response.data if response.data else []
        
        # Contar páginas
        from collections import Counter
        pages_count = Counter(log['page_name'] for log in logs if log.get('page_name'))
        top_pages = pages_count.most_common(10)
        
        labels = [page[0] for page in top_pages]
        values = [page[1] for page in top_pages]
        
        return jsonify({
            'success': True,
            'data': {
                'labels': labels,
                'values': values
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter top páginas: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': {'labels': [], 'values': []}
        })

@bp.route('/api/portal/recent-logs')
@login_required
def get_portal_recent_logs():
    """
    API para logs de acesso recentes (tabela paginada)
    """
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('perPage', 20))
        date_range = request.args.get('dateRange', '30d')
        user_role_filter = request.args.get('userRole', 'all')
        module_filter = request.args.get('moduleName', 'all')
        
        end_date = datetime.now().date()
        if date_range == '1d':
            start_date = end_date
        elif date_range == '7d':
            start_date = end_date - timedelta(days=7)
        elif date_range == '30d':
            start_date = end_date - timedelta(days=30)
        else:
            start_date = end_date - timedelta(days=30)
        
        # Query com paginação
        query = supabase_admin.table('vw_analytics_portal').select('*')
        query = query.gte('access_date', start_date.isoformat())
        query = query.lte('access_date', end_date.isoformat())
        query = query.eq('action_type', 'page_access')
        
        if user_role_filter != 'all':
            query = query.eq('user_role', user_role_filter)
        if module_filter != 'all':
            query = query.eq('module_name', module_filter)
        
        # Ordenar por timestamp mais recente
        query = query.order('access_timestamp_br', desc=True)
        
        # Aplicar paginação
        start_index = (page - 1) * per_page
        query = query.range(start_index, start_index + per_page - 1)
        
        response = query.execute()
        logs = response.data if response.data else []
        
        # Formatar logs para exibição
        formatted_logs = []
        for log in logs:
            formatted_logs.append({
                'log_id': log.get('log_id'),
                'user_name': log.get('user_name', 'N/A'),
                'user_email': log.get('user_email', ''),
                'user_role': log.get('user_role', ''),
                'module_name': log.get('module_name', 'N/A'),
                'page_name': log.get('page_name', 'N/A'),
                'access_timestamp': log.get('access_timestamp_br', 'N/A'),
                'http_status': log.get('http_status', 0),
                'is_successful': log.get('is_successful', True),
                'device_type': log.get('device_type', 'N/A'),
                'browser': log.get('browser', 'N/A')
            })
        
        return jsonify({
            'success': True,
            'data': formatted_logs,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': len(formatted_logs)
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter logs recentes: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': [],
            'pagination': {'page': 1, 'per_page': 20, 'total': 0}
        })

@bp.route('/api/portal/user-profile-breakdown')
@login_required
def get_portal_user_profile_breakdown():
    """
    API para distribuição por perfil de usuário
    """
    try:
        date_range = request.args.get('dateRange', '30d')
        module_filter = request.args.get('moduleName', 'all')
        
        end_date = datetime.now().date()
        if date_range == '1d':
            start_date = end_date
        elif date_range == '7d':
            start_date = end_date - timedelta(days=7)
        elif date_range == '30d':
            start_date = end_date - timedelta(days=30)
        else:
            start_date = end_date - timedelta(days=30)
        
        query = supabase_admin.table('vw_analytics_portal').select('user_role')
        query = query.gte('access_date', start_date.isoformat())
        query = query.lte('access_date', end_date.isoformat())
        query = query.eq('action_type', 'page_access')
        
        if module_filter != 'all':
            query = query.eq('module_name', module_filter)
        
        response = query.execute()
        logs = response.data if response.data else []
        
        # Contar perfis
        from collections import Counter
        roles_count = Counter(log['user_role'] for log in logs if log.get('user_role'))
        
        labels = list(roles_count.keys())
        values = list(roles_count.values())
        
        return jsonify({
            'success': True,
            'data': {
                'labels': labels,
                'values': values
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter breakdown de perfis: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': {'labels': [], 'values': []}
        })

@bp.route('/api/portal/most-active-users')
@login_required
def get_portal_most_active_users():
    """
    API para usuários mais ativos
    """
    try:
        date_range = request.args.get('dateRange', '30d')
        module_filter = request.args.get('moduleName', 'all')
        limit = int(request.args.get('limit', 10))
        
        end_date = datetime.now().date()
        if date_range == '1d':
            start_date = end_date
        elif date_range == '7d':
            start_date = end_date - timedelta(days=7)
        elif date_range == '30d':
            start_date = end_date - timedelta(days=30)
        else:
            start_date = end_date - timedelta(days=30)
        
        query = supabase_admin.table('vw_analytics_portal').select('user_name, user_email, user_role, access_timestamp_br')
        query = query.gte('access_date', start_date.isoformat())
        query = query.lte('access_date', end_date.isoformat())
        query = query.eq('action_type', 'page_access')
        
        if module_filter != 'all':
            query = query.eq('module_name', module_filter)
        
        response = query.execute()
        logs = response.data if response.data else []
        
        # Agrupar por usuário
        from collections import Counter
        user_access = {}
        for log in logs:
            user_key = log.get('user_email', 'N/A')
            access_timestamp = log.get('access_timestamp_br', '')
            
            if user_key not in user_access:
                user_access[user_key] = {
                    'user_name': log.get('user_name', 'N/A'),
                    'user_email': user_key,
                    'user_role': log.get('user_role', 'N/A'),
                    'access_count': 0,
                    'last_access': access_timestamp
                }
            else:
                user_access[user_key]['access_count'] += 1
                # Atualizar último acesso se for mais recente
                if access_timestamp > user_access[user_key]['last_access']:
                    user_access[user_key]['last_access'] = access_timestamp
        
        # Ordenar e pegar top N
        sorted_users = sorted(user_access.values(), key=lambda x: x['access_count'], reverse=True)[:limit]
        
        return jsonify({
            'success': True,
            'data': sorted_users
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter usuários mais ativos: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': []
        })

# ============================================================================
# ANALYTICS DO AGENTE WHATSAPP - APIs Otimizadas
# ============================================================================

@bp.route('/api/agente/kpis')
@login_required
def get_agente_kpis():
    """
    API para KPIs principais do agente WhatsApp
    """
    try:
        date_range = request.args.get('dateRange', '30d')
        empresa_filter = request.args.get('empresaNome', 'all')
        
        end_date = datetime.now().date()
        if date_range == '1d':
            start_date = end_date
        elif date_range == '7d':
            start_date = end_date - timedelta(days=7)
        elif date_range == '30d':
            start_date = end_date - timedelta(days=30)
        else:
            start_date = end_date - timedelta(days=30)
        
        query = supabase_admin.table('vw_analytics_agente').select('*')
        query = query.gte('interaction_date', start_date.isoformat())
        query = query.lte('interaction_date', end_date.isoformat())
        
        if empresa_filter != 'all':
            query = query.eq('empresa_nome', empresa_filter)
        
        response = query.execute()
        logs = response.data if response.data else []
        
        # KPIs
        total_interactions = len(logs)
        unique_users = len(set(log.get('user_id') for log in logs if log.get('user_id')))
        unique_companies = len(set(log.get('empresa_nome') for log in logs if log.get('empresa_nome')))
        
        # AJUSTE: response_time agora vem em SEGUNDOS da view
        response_times = [log.get('response_time_seconds', 0) for log in logs if log.get('response_time_seconds')]
        avg_response_time_seconds = round(sum(response_times) / len(response_times), 2) if response_times else 0
        
        return jsonify({
            'success': True,
            'data': {
                'total_interactions': total_interactions,
                'unique_users': unique_users,
                'companies_served': unique_companies,
                'avg_response_time_seconds': avg_response_time_seconds
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter KPIs do agente: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': {}
        })

@bp.route('/api/agente/timeline')
@login_required
def get_agente_timeline():
    """
    API para linha do tempo de interações
    """
    try:
        date_range = request.args.get('dateRange', '30d')
        empresa_filter = request.args.get('empresaNome', 'all')
        
        end_date = datetime.now().date()
        if date_range == '1d':
            start_date = end_date
        elif date_range == '7d':
            start_date = end_date - timedelta(days=7)
        elif date_range == '30d':
            start_date = end_date - timedelta(days=30)
        else:
            start_date = end_date - timedelta(days=30)
        
        query = supabase_admin.table('vw_analytics_agente').select('interaction_date')
        query = query.gte('interaction_date', start_date.isoformat())
        query = query.lte('interaction_date', end_date.isoformat())
        
        if empresa_filter != 'all':
            query = query.eq('empresa_nome', empresa_filter)
        
        response = query.execute()
        logs = response.data if response.data else []
        
        # Agrupar por data
        from collections import Counter
        date_counts = Counter(log.get('interaction_date') for log in logs if log.get('interaction_date'))
        
        # Ordenar
        sorted_dates = sorted(date_counts.items())
        
        labels = [datetime.fromisoformat(date).strftime('%d/%m') for date, _ in sorted_dates]
        values = [count for _, count in sorted_dates]
        
        return jsonify({
            'success': True,
            'data': {
                'labels': labels,
                'values': values
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter timeline do agente: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': {'labels': [], 'values': []}
        })

@bp.route('/api/agente/top-empresas')
@login_required
def get_agente_top_empresas():
    """
    API para top empresas por volume
    """
    try:
        date_range = request.args.get('dateRange', '30d')
        limit = int(request.args.get('limit', 5))
        
        end_date = datetime.now().date()
        if date_range == '1d':
            start_date = end_date
        elif date_range == '7d':
            start_date = end_date - timedelta(days=7)
        elif date_range == '30d':
            start_date = end_date - timedelta(days=30)
        else:
            start_date = end_date - timedelta(days=30)
        
        query = supabase_admin.table('vw_analytics_agente').select('empresa_nome')
        query = query.gte('interaction_date', start_date.isoformat())
        query = query.lte('interaction_date', end_date.isoformat())
        
        response = query.execute()
        logs = response.data if response.data else []
        
        # Agrupar por empresa
        from collections import Counter
        empresa_counts = Counter(log.get('empresa_nome', 'N/A') for log in logs)
        
        # Top N
        top_empresas = empresa_counts.most_common(limit)
        
        labels = [empresa for empresa, _ in top_empresas]
        values = [count for _, count in top_empresas]
        
        return jsonify({
            'success': True,
            'data': {
                'labels': labels,
                'values': values
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter top empresas: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': {'labels': [], 'values': []}
        })

@bp.route('/api/agente/peak-hours')
@login_required
def get_agente_peak_hours():
    """
    API para horários de pico
    """
    try:
        date_range = request.args.get('dateRange', '30d')
        empresa_filter = request.args.get('empresaNome', 'all')
        
        end_date = datetime.now().date()
        if date_range == '1d':
            start_date = end_date
        elif date_range == '7d':
            start_date = end_date - timedelta(days=7)
        elif date_range == '30d':
            start_date = end_date - timedelta(days=30)
        else:
            start_date = end_date - timedelta(days=30)
        
        query = supabase_admin.table('vw_analytics_agente').select('interaction_hour')
        query = query.gte('interaction_date', start_date.isoformat())
        query = query.lte('interaction_date', end_date.isoformat())
        
        if empresa_filter != 'all':
            query = query.eq('empresa_nome', empresa_filter)
        
        response = query.execute()
        logs = response.data if response.data else []
        
        # Agrupar por hora
        from collections import Counter
        hour_counts = Counter(int(log.get('interaction_hour', 0)) for log in logs if log.get('interaction_hour') is not None)
        
        # Ordenar por hora
        sorted_hours = sorted(hour_counts.items())
        
        labels = [f"{hour:02d}:00" for hour, _ in sorted_hours]
        values = [count for _, count in sorted_hours]
        
        return jsonify({
            'success': True,
            'data': {
                'labels': labels,
                'values': values
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter horários de pico: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': {'labels': [], 'values': []}
        })

@bp.route('/api/agente/response-types')
@login_required
def get_agente_response_types():
    """
    API para distribuição de tipos de resposta
    """
    try:
        date_range = request.args.get('dateRange', '30d')
        empresa_filter = request.args.get('empresaNome', 'all')
        
        end_date = datetime.now().date()
        if date_range == '1d':
            start_date = end_date
        elif date_range == '7d':
            start_date = end_date - timedelta(days=7)
        elif date_range == '30d':
            start_date = end_date - timedelta(days=30)
        else:
            start_date = end_date - timedelta(days=30)
        
        query = supabase_admin.table('vw_analytics_agente').select('response_type')
        query = query.gte('interaction_date', start_date.isoformat())
        query = query.lte('interaction_date', end_date.isoformat())
        
        if empresa_filter != 'all':
            query = query.eq('empresa_nome', empresa_filter)
        
        response = query.execute()
        logs = response.data if response.data else []
        
        # Agrupar por tipo
        from collections import Counter
        type_counts = Counter(log.get('response_type', 'Normal') for log in logs)
        
        labels = list(type_counts.keys())
        values = list(type_counts.values())
        
        return jsonify({
            'success': True,
            'data': {
                'labels': labels,
                'values': values
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter tipos de resposta: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': {'labels': [], 'values': []}
        })

@bp.route('/api/agente/recent-interactions')
@login_required
def get_agente_recent_interactions():
    """
    API para interações recentes com detalhes completos
    """
    try:
        date_range = request.args.get('dateRange', '30d')
        empresa_filter = request.args.get('empresaNome', 'all')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('perPage', 20))
        
        end_date = datetime.now().date()
        if date_range == '1d':
            start_date = end_date
        elif date_range == '7d':
            start_date = end_date - timedelta(days=7)
        elif date_range == '30d':
            start_date = end_date - timedelta(days=30)
        else:
            start_date = end_date - timedelta(days=30)
        
        query = supabase_admin.table('vw_analytics_agente').select('*')
        query = query.gte('interaction_date', start_date.isoformat())
        query = query.lte('interaction_date', end_date.isoformat())
        
        if empresa_filter != 'all':
            query = query.eq('empresa_nome', empresa_filter)
        
        query = query.order('interaction_timestamp_br', desc=True)
        query = query.limit(per_page)
        
        response = query.execute()
        logs = response.data if response.data else []
        
        # Formatar dados para retorno
        formatted_logs = []
        for log in logs:
            formatted_logs.append({
                'log_id': log.get('log_id'),
                'user_name': log.get('user_name', 'N/A'),
                'empresa_nome': log.get('empresa_nome', 'N/A'),
                'message_type': log.get('message_type', 'N/A'),
                'response_type': log.get('response_type', 'Normal'),
                'response_time_seconds': log.get('response_time_seconds', 0),
                'total_cnpjs_consultados': log.get('total_cnpjs_consultados', 0),
                'total_processos_encontrados': log.get('total_processos_encontrados', 0),
                'interaction_timestamp_br': log.get('interaction_timestamp_br', ''),
                'user_message': log.get('user_message', 'Mensagem não disponível'),
                'agent_response': log.get('agent_response', 'Resposta não disponível')
            })
        
        return jsonify({
            'success': True,
            'data': formatted_logs,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': len(formatted_logs)
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter interações recentes: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': [],
            'pagination': {'page': 1, 'per_page': 20, 'total': 0}
        })

@bp.route('/api/agente/empresas-list')
@login_required
def get_agente_empresas_list():
    """
    API para listar todas as empresas disponíveis
    """
    try:
        query = supabase_admin.table('vw_analytics_agente').select('empresa_nome')
        response = query.execute()
        logs = response.data if response.data else []
        
        # Empresas únicas
        empresas = sorted(set(log.get('empresa_nome') for log in logs if log.get('empresa_nome')))
        
        return jsonify({
            'success': True,
            'empresas': empresas
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter lista de empresas: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'empresas': []
        })

@bp.route('/api/inactive-users')
@login_required
def get_inactive_users():
    """
    API para obter usuários sem acesso há mais de 15 dias
    """
    try:
        from datetime import timezone
        
        # Data limite: 15 dias atrás (com timezone aware)
        now = datetime.now(timezone.utc)
        inactive_threshold = now - timedelta(days=15)
        
        logger.info(f"[INACTIVE_USERS] Buscando usuários inativos desde {inactive_threshold}")
        
        # Buscar último acesso de cada usuário nos logs
        logs_query = supabase_admin.table('access_logs').select('user_id, user_name, user_email, user_role, created_at').order('created_at', desc=True)
        logs_response = run_with_retries(
            'analytics.get_inactive_users.logs',
            lambda: logs_query.execute(),
            max_attempts=3,
            base_delay_seconds=0.8,
            should_retry=lambda e: 'Server disconnected' in str(e) or 'timeout' in str(e).lower()
        )
        all_logs = logs_response.data if logs_response.data else []
        logger.info(f"[INACTIVE_USERS] Total de logs encontrados: {len(all_logs)}")
        
        # Filtrar logs de desenvolvimento e sem user_name
        all_logs = [log for log in all_logs if log.get('user_name') and not (
            (log.get('page_url') and log['page_url'].startswith('http://127.0.0.1:5000')) or
            (log.get('ip_address') == '127.0.0.1')
        )]
        logger.info(f"[INACTIVE_USERS] Logs após filtro: {len(all_logs)}")
        
        # Mapear último acesso por usuário
        last_access_map = {}
        for log in all_logs:
            user_id = log.get('user_id')
            user_name = log.get('user_name')
            
            if user_id and user_id not in last_access_map:
                last_access_map[user_id] = {
                    'last_access': log.get('created_at'),
                    'user_name': user_name,
                    'user_email': log.get('user_email', 'N/A'),
                    'user_role': log.get('user_role', 'N/A')
                }
        
        logger.info(f"[INACTIVE_USERS] Total de usuários únicos: {len(last_access_map)}")
        
        # Identificar usuários inativos (mais de 15 dias sem acesso)
        inactive_users = []
        for user_id, user_data in last_access_map.items():
            last_access_str = user_data['last_access']
            try:
                last_access = datetime.fromisoformat(last_access_str.replace('Z', '+00:00'))
                days_inactive = (now - last_access).days
                
                logger.debug(f"[INACTIVE_USERS] {user_data['user_name']}: {days_inactive} dias inativo")
                
                if days_inactive > 15:
                    inactive_users.append({
                        'user_id': user_id,
                        'user_name': user_data['user_name'],
                        'user_email': user_data['user_email'],
                        'user_role': user_data['user_role'],
                        'last_access': _format_ts_with_policy(last_access_str, 'none'),
                        'days_inactive': days_inactive
                    })
            except Exception as e:
                logger.warning(f"[INACTIVE_USERS] Erro ao processar usuário {user_id}: {e}")
                continue
        
        # Ordenar por dias inativos (decrescente)
        inactive_users.sort(key=lambda x: x['days_inactive'], reverse=True)
        
        logger.info(f"[ANALYTICS] Encontrados {len(inactive_users)} usuários inativos (+15 dias)")
        
        return jsonify({
            'success': True,
            'inactive_users': inactive_users
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter usuários inativos: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'inactive_users': []
        })

@bp.route('/api/agente/interaction-details/<log_id>')
@login_required
def get_agente_interaction_details(log_id):
    """
    API para buscar detalhes completos de uma interação (prompt + resposta)
    """
    try:
        # Buscar na tabela original para pegar prompt e resposta
        query = supabase_admin.table('agent_interaction_logs').select('*')
        query = query.eq('id', log_id)
        query = query.limit(1)
        
        response = query.execute()
        
        if not response.data or len(response.data) == 0:
            return jsonify({
                'success': False,
                'error': 'Interação não encontrada',
                'data': None
            }), 404
        
        log = response.data[0]
        
        return jsonify({
            'success': True,
            'data': {
                'log_id': log.get('id'),
                'user_name': log.get('user_name'),
                'empresa_nome': log.get('empresa_nome'),
                'user_prompt': log.get('user_prompt', ''),  # Prompt do usuário
                'agent_response_text': log.get('agent_response_text', ''),  # Resposta do agente
                'message_type': log.get('message_type'),
                'response_type': log.get('response_type'),
                'response_time_seconds': log.get('response_time_seconds'),
                'total_cnpjs': log.get('total_cnpjs'),
                'total_processos_encontrados': log.get('total_processos_encontrados'),
                'processed_at': log.get('processed_at')
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar detalhes da interação: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': None
        }), 500
