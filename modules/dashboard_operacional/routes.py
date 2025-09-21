from flask import Blueprint, render_template, request, jsonify, session
from extensions import supabase, supabase_admin
from routes.auth import login_required, role_required
from decorators.perfil_decorators import perfil_required
from routes.api import get_user_companies
from permissions import check_permission
from datetime import datetime, timedelta
import logging
from functools import wraps
import os

# Create blueprint
dashboard_operacional = Blueprint('dashboard_operacional', __name__,
                                  template_folder='templates',
                                  static_folder='static',
                                  url_prefix='/dashboard-operacional')

logger = logging.getLogger(__name__)

def require_login(f):
    """Decorator to require login for routes with API bypass"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check for API bypass
        api_bypass_key = os.getenv('API_BYPASS_KEY')
        if api_bypass_key and request.headers.get('X-API-Key') == api_bypass_key:
            # API bypass mode - continue without login check
            return f(*args, **kwargs)
        
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Login required'}), 401
        return f(*args, **kwargs)
    return decorated_function

def get_user_companies():
    """Get user companies for filtering"""
    # Check for API bypass mode
    api_bypass_key = os.getenv('API_BYPASS_KEY')
    if api_bypass_key and request.headers.get('X-API-Key') == api_bypass_key:
        # In bypass mode, return None to see all data
        return None
    
    user_id = session.get('user_id')
    user_role = session.get('role', '')
    
    # Admin sees all data
    if user_role == 'admin':
        return None
    
    # Cliente_unique sees only their companies
    if user_role == 'cliente_unique':
        user_companies = session.get('user_companies', [])
        if not user_companies:
            return []
        return user_companies
    
    # Interno_unique sees all data
    return None

@dashboard_operacional.route('/')
@login_required
@role_required(['admin', 'interno_unique'])
def index():
    """Dashboard operacional main page"""
    try:
        user_role = session.get('role', '')
        user_companies = get_user_companies()
        
        # Check if user has company restrictions but no companies
        show_company_warning = (user_role == 'cliente_unique' and 
                               (not user_companies or len(user_companies) == 0))
        
        return render_template('dashboard_operacional.html',
                             show_company_warning=show_company_warning)
    
    except Exception as e:
        logger.error(f"Erro ao carregar dashboard operacional: {str(e)}")
        return f"Erro interno: {str(e)}", 500

@dashboard_operacional.route('/api/data')
@require_login
def get_dashboard_data():
    """Get main dashboard data including KPIs, tables, and chart data"""
    try:
        year = request.args.get('year')
        month = request.args.get('month')
        user_companies = get_user_companies()
        
        # Build base query with filters
        filters = []
        params = {}
        
        # Date filters
        if year and month:
            # Specific month filter
            filters.append("EXTRACT(year FROM data_registro::date) = %(year)s")
            filters.append("EXTRACT(month FROM data_registro::date) = %(month)s")
            params['year'] = int(year)
            params['month'] = int(month)
        elif year:
            # Whole year filter
            filters.append("EXTRACT(year FROM data_registro::date) = %(year)s")
            params['year'] = int(year)
        
        # Company filter for clients
        if user_companies is not None and len(user_companies) > 0:
            placeholders = ','.join([f"%(company_{i})s" for i in range(len(user_companies))])
            filters.append(f"cliente IN ({placeholders})")
            for i, company in enumerate(user_companies):
                params[f'company_{i}'] = company
        
        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
        
        # Get KPIs
        kpis = get_kpis_data(year, month, where_clause, params)
        
        # Get client performance data
        clients = get_client_performance_data(year, month, where_clause, params)
        
        # Get analyst performance data
        analysts = get_analyst_performance_data(year, month, where_clause, params)
        
        # Get distribution data (modal and canal)
        distribution = get_distribution_data(where_clause, params)
        
        # Get calendar data
        calendar_data = get_calendar_data(year, month, where_clause, params)
        
        # Get alert processes
        alerts = get_alert_processes(user_companies)
        
        # Get SLA comparison data
        sla_comparison = get_sla_comparison_data(where_clause, params)
        
        response_data = {
            'kpis': kpis,
            'clients': clients,
            'analysts': analysts,
            'distribution': distribution,
            'calendar': calendar_data,
            'alerts': alerts,
            'sla_comparison': sla_comparison
        }
        
        return jsonify({
            'success': True,
            'data': response_data,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter dados do dashboard: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Erro ao carregar dados: {str(e)}'
        }), 500

def get_kpis_data(year, month, where_clause, params):
    """Get KPI data for the dashboard"""
    try:
        # Total processes
        query = f"""
            SELECT COUNT(*) as total_processos
            FROM importacoes_processos_operacional
            {where_clause}
        """
        
        result = supabase_admin.rpc('execute_sql', {'sql_query': query, 'params': params}).execute()
        total_processos = result.data[0]['total_processos'] if result.data else 0
        
        # Get meta for the period
        meta_mensal = get_meta_data(year, month)
        
        # Calculate meta percentual
        meta_percentual = 0
        if meta_mensal > 0:
            meta_percentual = (total_processos / meta_mensal) * 100
        
        # Meta a realizar
        meta_a_realizar = max(0, meta_mensal - total_processos)
        
        # Average SLA for closed processes
        sla_query = f"""
            SELECT AVG(sla_dias) as sla_medio
            FROM importacoes_processos_operacional
            {where_clause} AND data_fechamento IS NOT NULL AND sla_dias IS NOT NULL
        """
        
        sla_result = supabase_admin.rpc('execute_sql', {'sql_query': sla_query, 'params': params}).execute()
        sla_medio = sla_result.data[0]['sla_medio'] if sla_result.data and sla_result.data[0]['sla_medio'] else None
        
        return {
            'total_processos': total_processos,
            'meta_mensal': meta_mensal,
            'meta_percentual': round(meta_percentual, 1),
            'meta_a_realizar': meta_a_realizar,
            'sla_medio': round(sla_medio, 1) if sla_medio else None
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter KPIs: {str(e)}")
        return {
            'total_processos': 0,
            'meta_mensal': 0,
            'meta_percentual': 0,
            'meta_a_realizar': 0,
            'sla_medio': None
        }

def get_meta_data(year, month):
    """Get meta data from fin_metas_projecoes table"""
    try:
        if year and month:
            # Get specific month meta
            result = supabase_admin.table('fin_metas_projecoes').select('meta').eq('ano', year).eq('mes', month).eq('tipo', 'operacional').limit(1).execute()
            
            if result.data:
                return float(result.data[0]['meta'])
        
        elif year:
            # Get sum of all months for the year
            result = supabase_admin.table('fin_metas_projecoes').select('meta').eq('ano', year).eq('tipo', 'operacional').execute()
            
            if result.data:
                total_meta = sum(float(row['meta']) for row in result.data if row['meta'])
                return total_meta
        
        return 0
        
    except Exception as e:
        logger.error(f"Erro ao obter meta: {str(e)}")
        return 0

def get_client_performance_data(year, month, where_clause, params):
    """Get client performance data with comparison to previous period"""
    try:
        # Current period data
        query = f"""
            SELECT 
                cliente,
                COUNT(*) as total_registros
            FROM importacoes_processos_operacional
            {where_clause}
            GROUP BY cliente
            ORDER BY total_registros DESC
        """
        
        result = supabase_admin.rpc('execute_sql', {'sql_query': query, 'params': params}).execute()
        current_data = {row['cliente']: row['total_registros'] for row in result.data}
        
        # Previous period data for comparison
        previous_data = get_previous_period_data(year, month, 'cliente', params)
        
        # Combine data
        clients = []
        for cliente, total_registros in current_data.items():
            periodo_anterior = previous_data.get(cliente, 0)
            
            clients.append({
                'cliente': cliente,
                'total_registros': total_registros,
                'periodo_anterior': periodo_anterior
            })
        
        return sorted(clients, key=lambda x: x['total_registros'], reverse=True)[:20]  # Top 20
        
    except Exception as e:
        logger.error(f"Erro ao obter dados de clientes: {str(e)}")
        return []

def get_analyst_performance_data(year, month, where_clause, params):
    """Get analyst performance data"""
    try:
        query = f"""
            SELECT 
                analista,
                COUNT(*) as total_registros,
                AVG(CASE WHEN data_fechamento IS NOT NULL THEN sla_dias END) as sla_medio
            FROM importacoes_processos_operacional
            {where_clause} AND analista IS NOT NULL
            GROUP BY analista
            ORDER BY total_registros DESC
        """
        
        result = supabase_admin.rpc('execute_sql', {'sql_query': query, 'params': params}).execute()
        
        analysts = []
        for row in result.data:
            analysts.append({
                'analista': row['analista'],
                'total_registros': row['total_registros'],
                'sla_medio': float(row['sla_medio']) if row['sla_medio'] else None
            })
        
        return analysts
        
    except Exception as e:
        logger.error(f"Erro ao obter dados de analistas: {str(e)}")
        return []

def get_distribution_data(where_clause, params):
    """Get distribution data for modal and canal"""
    try:
        # Modal distribution
        modal_query = f"""
            SELECT 
                modal,
                COUNT(*) as total
            FROM importacoes_processos_operacional
            {where_clause} AND modal IS NOT NULL
            GROUP BY modal
            ORDER BY total DESC
        """
        
        modal_result = supabase_admin.rpc('execute_sql', {'sql_query': modal_query, 'params': params}).execute()
        modal_data = [{'modal': row['modal'], 'total': row['total']} for row in modal_result.data]
        
        # Canal distribution
        canal_query = f"""
            SELECT 
                COALESCE(canal, 'Não informado') as canal,
                COUNT(*) as total
            FROM importacoes_processos_operacional
            {where_clause}
            GROUP BY canal
            ORDER BY total DESC
        """
        
        canal_result = supabase_admin.rpc('execute_sql', {'sql_query': canal_query, 'params': params}).execute()
        canal_data = [{'canal': row['canal'], 'total': row['total']} for row in canal_result.data]
        
        return {
            'modal': modal_data,
            'canal': canal_data
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter dados de distribuição: {str(e)}")
        return {'modal': [], 'canal': []}

def get_calendar_data(year, month, where_clause, params):
    """Get calendar data showing registrations per day"""
    try:
        # If no specific month, use current month
        if not month:
            month = str(datetime.now().month).zfill(2)
        if not year:
            year = str(datetime.now().year)
        
        # Modify where clause to focus on specific month
        month_filters = []
        month_params = params.copy()
        
        month_filters.append("EXTRACT(year FROM data_registro::date) = %(cal_year)s")
        month_filters.append("EXTRACT(month FROM data_registro::date) = %(cal_month)s")
        month_params['cal_year'] = int(year)
        month_params['cal_month'] = int(month)
        
        # Add existing filters but replace date filters
        original_where = where_clause.replace("WHERE ", "") if where_clause else ""
        date_independent_filters = []
        
        if "cliente IN" in original_where:
            # Extract company filter
            start = original_where.find("cliente IN")
            end = original_where.find(")", start) + 1
            date_independent_filters.append(original_where[start:end])
        
        all_filters = month_filters + date_independent_filters
        calendar_where = f"WHERE {' AND '.join(all_filters)}" if all_filters else ""
        
        query = f"""
            SELECT 
                data_registro::date as date,
                COUNT(*) as count
            FROM importacoes_processos_operacional
            {calendar_where}
            GROUP BY data_registro::date
            ORDER BY date
        """
        
        result = supabase_admin.rpc('execute_sql', {'sql_query': query, 'params': month_params}).execute()
        
        calendar_data = []
        for row in result.data:
            calendar_data.append({
                'date': row['date'],
                'count': row['count']
            })
        
        return calendar_data
        
    except Exception as e:
        logger.error(f"Erro ao obter dados do calendário: {str(e)}")
        return []

def get_alert_processes(user_companies):
    """Get processes that require attention (open for too long)"""
    try:
        # Company filter
        company_filter = ""
        params = {}
        
        if user_companies is not None and len(user_companies) > 0:
            placeholders = ','.join([f"%(company_{i})s" for i in range(len(user_companies))])
            company_filter = f"AND cliente IN ({placeholders})"
            for i, company in enumerate(user_companies):
                params[f'company_{i}'] = company
        
        query = f"""
            SELECT 
                ref_unique,
                cliente,
                analista,
                data_registro,
                ABS(desempenho) as dias_aberto
            FROM importacoes_processos_operacional
            WHERE data_fechamento IS NULL 
            {company_filter}
            ORDER BY dias_aberto DESC
            LIMIT 10
        """
        
        result = supabase_admin.rpc('execute_sql', {'sql_query': query, 'params': params}).execute()
        
        alerts = []
        for row in result.data:
            alerts.append({
                'ref_unique': row['ref_unique'],
                'cliente': row['cliente'],
                'analista': row['analista'],
                'data_registro': row['data_registro'],
                'dias_aberto': row['dias_aberto']
            })
        
        return alerts
        
    except Exception as e:
        logger.error(f"Erro ao obter processos em alerta: {str(e)}")
        return []

def get_sla_comparison_data(where_clause, params):
    """Get SLA comparison data by analyst (for box plot)"""
    try:
        query = f"""
            SELECT 
                analista,
                MIN(sla_dias) as min_sla,
                PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY sla_dias) as q1_sla,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY sla_dias) as median_sla,
                PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY sla_dias) as q3_sla,
                MAX(sla_dias) as max_sla
            FROM importacoes_processos_operacional
            {where_clause} AND analista IS NOT NULL 
            AND data_fechamento IS NOT NULL 
            AND sla_dias IS NOT NULL
            GROUP BY analista
            HAVING COUNT(*) >= 3
            ORDER BY median_sla
        """
        
        result = supabase_admin.rpc('execute_sql', {'sql_query': query, 'params': params}).execute()
        
        sla_data = []
        for row in result.data:
            sla_data.append({
                'analista': row['analista'],
                'min_sla': float(row['min_sla']),
                'q1_sla': float(row['q1_sla']),
                'median_sla': float(row['median_sla']),
                'q3_sla': float(row['q3_sla']),
                'max_sla': float(row['max_sla'])
            })
        
        return sla_data
        
    except Exception as e:
        logger.error(f"Erro ao obter dados de comparação SLA: {str(e)}")
        return []

def get_previous_period_data(year, month, group_by, params):
    """Get data from previous period for comparison"""
    try:
        if not year:
            return {}
        
        if month:
            # Previous month
            prev_year = int(year)
            prev_month = int(month) - 1
            if prev_month == 0:
                prev_month = 12
                prev_year -= 1
            
            prev_filters = [
                "EXTRACT(year FROM data_registro::date) = %(prev_year)s",
                "EXTRACT(month FROM data_registro::date) = %(prev_month)s"
            ]
            prev_params = {'prev_year': prev_year, 'prev_month': prev_month}
        else:
            # Previous year
            prev_filters = ["EXTRACT(year FROM data_registro::date) = %(prev_year)s"]
            prev_params = {'prev_year': int(year) - 1}
        
        # Add company filters if present
        if 'company_0' in params:
            company_count = sum(1 for key in params.keys() if key.startswith('company_'))
            placeholders = ','.join([f"%(company_{i})s" for i in range(company_count)])
            prev_filters.append(f"cliente IN ({placeholders})")
            for i in range(company_count):
                prev_params[f'company_{i}'] = params[f'company_{i}']
        
        where_clause = f"WHERE {' AND '.join(prev_filters)}"
        
        query = f"""
            SELECT 
                {group_by},
                COUNT(*) as total_registros
            FROM importacoes_processos_operacional
            {where_clause}
            GROUP BY {group_by}
        """
        
        result = supabase_admin.rpc('execute_sql', {'sql_query': query, 'params': prev_params}).execute()
        
        return {row[group_by]: row['total_registros'] for row in result.data}
        
    except Exception as e:
        logger.error(f"Erro ao obter dados do período anterior: {str(e)}")
        return {}

@dashboard_operacional.route('/api/client-modals')
@require_login
def get_client_modals():
    """Get modal breakdown for a specific client"""
    try:
        client = request.args.get('client')
        year = request.args.get('year')
        month = request.args.get('month')
        user_companies = get_user_companies()
        
        if not client:
            return jsonify({'success': False, 'message': 'Cliente não especificado'}), 400
        
        # Build filters
        filters = ["cliente = %(client)s"]
        params = {'client': client}
        
        if year and month:
            filters.extend([
                "EXTRACT(year FROM data_registro::date) = %(year)s",
                "EXTRACT(month FROM data_registro::date) = %(month)s"
            ])
            params.update({'year': int(year), 'month': int(month)})
        elif year:
            filters.append("EXTRACT(year FROM data_registro::date) = %(year)s")
            params['year'] = int(year)
        
        # Company filter
        if user_companies is not None and client not in user_companies:
            return jsonify({'success': False, 'message': 'Acesso negado'}), 403
        
        where_clause = f"WHERE {' AND '.join(filters)}"
        
        # Current period
        query = f"""
            SELECT 
                modal,
                COUNT(*) as total_registros
            FROM importacoes_processos_operacional
            {where_clause} AND modal IS NOT NULL
            GROUP BY modal
            ORDER BY total_registros DESC
        """
        
        result = supabase_admin.rpc('execute_sql', {'sql_query': query, 'params': params}).execute()
        current_data = {row['modal']: row['total_registros'] for row in result.data}
        
        # Previous period data
        previous_data = get_previous_period_client_modals(client, year, month)
        
        # Combine data
        modals = []
        for modal, total_registros in current_data.items():
            periodo_anterior = previous_data.get(modal, 0)
            
            modals.append({
                'modal': modal,
                'total_registros': total_registros,
                'periodo_anterior': periodo_anterior
            })
        
        return jsonify({
            'success': True,
            'data': {'modals': modals}
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter modais do cliente: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

def get_previous_period_client_modals(client, year, month):
    """Get previous period modal data for a client"""
    try:
        if not year:
            return {}
        
        if month:
            prev_year = int(year)
            prev_month = int(month) - 1
            if prev_month == 0:
                prev_month = 12
                prev_year -= 1
            
            filters = [
                "cliente = %(client)s",
                "EXTRACT(year FROM data_registro::date) = %(prev_year)s",
                "EXTRACT(month FROM data_registro::date) = %(prev_month)s"
            ]
            params = {'client': client, 'prev_year': prev_year, 'prev_month': prev_month}
        else:
            filters = [
                "cliente = %(client)s",
                "EXTRACT(year FROM data_registro::date) = %(prev_year)s"
            ]
            params = {'client': client, 'prev_year': int(year) - 1}
        
        where_clause = f"WHERE {' AND '.join(filters)}"
        
        query = f"""
            SELECT 
                modal,
                COUNT(*) as total_registros
            FROM importacoes_processos_operacional
            {where_clause} AND modal IS NOT NULL
            GROUP BY modal
        """
        
        result = supabase_admin.rpc('execute_sql', {'sql_query': query, 'params': params}).execute()
        
        return {row['modal']: row['total_registros'] for row in result.data}
        
    except Exception as e:
        logger.error(f"Erro ao obter dados anteriores de modais: {str(e)}")
        return {}

@dashboard_operacional.route('/api/client-processes')
@require_login
def get_client_processes():
    """Get individual processes for a specific client and modal"""
    try:
        client = request.args.get('client')
        modal = request.args.get('modal')
        year = request.args.get('year')
        month = request.args.get('month')
        user_companies = get_user_companies()
        
        if not client or not modal:
            return jsonify({'success': False, 'message': 'Cliente e modal devem ser especificados'}), 400
        
        # Company filter
        if user_companies is not None and client not in user_companies:
            return jsonify({'success': False, 'message': 'Acesso negado'}), 403
        
        # Build filters
        filters = ["cliente = %(client)s", "modal = %(modal)s"]
        params = {'client': client, 'modal': modal}
        
        if year and month:
            filters.extend([
                "EXTRACT(year FROM data_registro::date) = %(year)s",
                "EXTRACT(month FROM data_registro::date) = %(month)s"
            ])
            params.update({'year': int(year), 'month': int(month)})
        elif year:
            filters.append("EXTRACT(year FROM data_registro::date) = %(year)s")
            params['year'] = int(year)
        
        where_clause = f"WHERE {' AND '.join(filters)}"
        
        query = f"""
            SELECT 
                ref_unique,
                data_registro
            FROM importacoes_processos_operacional
            {where_clause}
            ORDER BY data_registro DESC
            LIMIT 50
        """
        
        result = supabase_admin.rpc('execute_sql', {'sql_query': query, 'params': params}).execute()
        
        processes = []
        for row in result.data:
            processes.append({
                'ref_unique': row['ref_unique'],
                'data_registro': row['data_registro']
            })
        
        return jsonify({
            'success': True,
            'data': {'processes': processes}
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter processos do cliente: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@dashboard_operacional.route('/api/analyst-clients')
@require_login
def get_analyst_clients():
    """Get top 5 clients for a specific analyst"""
    try:
        analyst = request.args.get('analyst')
        year = request.args.get('year')
        month = request.args.get('month')
        user_companies = get_user_companies()
        
        if not analyst:
            return jsonify({'success': False, 'message': 'Analista não especificado'}), 400
        
        # Build filters
        filters = ["analista = %(analyst)s"]
        params = {'analyst': analyst}
        
        if year and month:
            filters.extend([
                "EXTRACT(year FROM data_registro::date) = %(year)s",
                "EXTRACT(month FROM data_registro::date) = %(month)s"
            ])
            params.update({'year': int(year), 'month': int(month)})
        elif year:
            filters.append("EXTRACT(year FROM data_registro::date) = %(year)s")
            params['year'] = int(year)
        
        # Company filter
        if user_companies is not None and len(user_companies) > 0:
            placeholders = ','.join([f"%(company_{i})s" for i in range(len(user_companies))])
            filters.append(f"cliente IN ({placeholders})")
            for i, company in enumerate(user_companies):
                params[f'company_{i}'] = company
        
        where_clause = f"WHERE {' AND '.join(filters)}"
        
        query = f"""
            SELECT 
                cliente,
                COUNT(*) as total_registros
            FROM importacoes_processos_operacional
            {where_clause}
            GROUP BY cliente
            ORDER BY total_registros DESC
            LIMIT 5
        """
        
        result = supabase_admin.rpc('execute_sql', {'sql_query': query, 'params': params}).execute()
        
        clients = []
        for row in result.data:
            clients.append({
                'cliente': row['cliente'],
                'total_registros': row['total_registros']
            })
        
        return jsonify({
            'success': True,
            'data': {'clients': clients}
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter clientes do analista: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

# API Bypass for testing (using environment variable)
@dashboard_operacional.route('/api/test-data')
def test_dashboard_data():
    """Test endpoint with API bypass"""
    api_bypass_key = os.getenv('API_BYPASS_KEY')
    provided_key = request.headers.get('X-API-Key')
    
    if not api_bypass_key or provided_key != api_bypass_key:
        return jsonify({'success': False, 'message': 'API key required'}), 401
    
    try:
        # Return sample data for testing
        test_data = {
            'kpis': {
                'total_processos': 1250,
                'meta_mensal': 1500,
                'meta_percentual': 83.3,
                'meta_a_realizar': 250,
                'sla_medio': 18.5
            },
            'clients': [
                {'cliente': 'AZIMUT', 'total_registros': 45, 'periodo_anterior': 38},
                {'cliente': 'MIDAS SC', 'total_registros': 23, 'periodo_anterior': 29},
                {'cliente': 'ONCOIMPORT', 'total_registros': 15, 'periodo_anterior': 12}
            ],
            'analysts': [
                {'analista': 'RAFAEL', 'total_registros': 83, 'sla_medio': 16.2},
                {'analista': 'MARIA', 'total_registros': 67, 'sla_medio': 22.1}
            ],
            'distribution': {
                'modal': [
                    {'modal': 'AÉREA', 'total': 45},
                    {'modal': 'MARÍTIMA', 'total': 38}
                ],
                'canal': [
                    {'canal': 'Verde', 'total': 78},
                    {'canal': 'Não informado', 'total': 5}
                ]
            },
            'calendar': [],
            'alerts': [],
            'sla_comparison': []
        }
        
        return jsonify({
            'success': True,
            'data': test_data,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Erro no teste: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500
