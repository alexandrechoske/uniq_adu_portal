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
        
        if 'user' not in session:
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
    
    user_data = session.get('user', {})
    user_id = user_data.get('id')
    user_role = user_data.get('role', '')
    
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
@login_required
def get_dashboard_data():
    """Get main dashboard data including KPIs, tables, and chart data"""
    try:
        year = request.args.get('year', type=int)
        month = request.args.get('month', type=int)
        
        # Get all data from correct table
        response = supabase_admin.table('importacoes_processos_operacional').select('*').execute()
        all_data = response.data
        
        # Filter by date using Python (data_registro is in YYYY-MM-DD format)
        filtered_data = all_data
        if year or month:
            filtered_data = []
            for record in all_data:
                data_registro_str = record.get('data_registro', '')
                if data_registro_str and isinstance(data_registro_str, str):
                    try:
                        # Parse YYYY-MM-DD format
                        if len(data_registro_str) >= 10:  # YYYY-MM-DD
                            year_str = data_registro_str[:4]
                            month_str = data_registro_str[5:7]
                            
                            if year_str and month_str:
                                record_year = int(year_str)
                                record_month = int(month_str)
                                
                                # Apply filters
                                if year and month:
                                    if record_year == year and record_month == month:
                                        filtered_data.append(record)
                                elif year:
                                    if record_year == year:
                                        filtered_data.append(record)
                    except (ValueError, TypeError):
                        continue  # Skip invalid dates
        
        # Calculate KPIs
        total_processos = len(filtered_data)
        
        # Get meta from fin_metas_projecoes table
        meta_mensal = 0
        if year and month:
            meta_response = supabase_admin.table('fin_metas_projecoes')\
                .select('meta')\
                .eq('ano', str(year))\
                .eq('mes', f"{month:02d}")\
                .eq('tipo', 'operacional')\
                .execute()
            
            if meta_response.data:
                meta_mensal = int(meta_response.data[0]['meta'])
        
        # Calculate meta percentage and remaining
        meta_percentual = round((total_processos / meta_mensal * 100), 2) if meta_mensal > 0 else 0
        meta_a_realizar = max(0, meta_mensal - total_processos) if meta_mensal > 0 else 0
        
        # Calculate average SLA
        sla_values = [record.get('sla_dias') for record in filtered_data if record.get('sla_dias') is not None]
        sla_medio = round(sum(sla_values) / len(sla_values), 1) if sla_values else None
        
        # Get unique clients
        unique_clients = {}
        for record in filtered_data:
            cliente = record.get('cliente', '')
            if cliente and isinstance(cliente, str) and cliente.strip():
                if cliente not in unique_clients:
                    unique_clients[cliente] = {
                        'nome': cliente,
                        'total_processos': 0,
                        'sla_medio': [],
                        'canais': {}
                    }
                unique_clients[cliente]['total_processos'] += 1
                
                # Add SLA for average calculation
                sla = record.get('sla_dias')
                if sla is not None:
                    unique_clients[cliente]['sla_medio'].append(sla)
                
                # Count canais
                canal = record.get('canal', 'N/A')
                if not canal:
                    canal = 'N/A'
                if canal not in unique_clients[cliente]['canais']:
                    unique_clients[cliente]['canais'][canal] = 0
                unique_clients[cliente]['canais'][canal] += 1
        
        # Get data from same period in previous year for comparison
        previous_year_data = {}
        if year:
            try:
                if month:
                    # Same month in previous year
                    prev_year = int(year) - 1
                    prev_month = int(month)
                    prev_year_records = [r for r in all_data 
                                       if r.get('data_registro', '')[:4] == str(prev_year) 
                                       and r.get('data_registro', '')[5:7] == f"{prev_month:02d}"]
                else:
                    # Previous year (all months)
                    prev_year = int(year) - 1
                    prev_year_records = [r for r in all_data 
                                       if r.get('data_registro', '')[:4] == str(prev_year)]
                
                # Count by client in previous period
                for record in prev_year_records:
                    cliente = record.get('cliente', '')
                    if cliente and isinstance(cliente, str) and cliente.strip():
                        if cliente not in previous_year_data:
                            previous_year_data[cliente] = 0
                        previous_year_data[cliente] += 1
                        
            except Exception as e:
                logger.error(f"Erro ao obter dados do período anterior: {str(e)}")
        
        # Convert to list and calculate averages with period comparison
        clients_list = []
        for cliente_data in unique_clients.values():
            sla_values = cliente_data['sla_medio']
            avg_sla = round(sum(sla_values) / len(sla_values), 1) if sla_values else None
            
            # Get previous year data for this client
            cliente_nome = cliente_data['nome']
            total_atual = cliente_data['total_processos']
            total_anterior = previous_year_data.get(cliente_nome, 0)
            
            # Calculate variation percentage
            if total_anterior > 0:
                variacao_percent = round(((total_atual - total_anterior) / total_anterior) * 100, 1)
            else:
                variacao_percent = 100.0 if total_atual > 0 else 0.0
            
            clients_list.append({
                'nome': cliente_nome,
                'total_processos': total_atual,
                'periodo_anterior': total_anterior,
                'variacao_percent': variacao_percent,
                'sla_medio': avg_sla,
                'canais': cliente_data['canais']
            })
        
        clients_list.sort(key=lambda x: x['total_processos'], reverse=True)
        
        # Get unique analysts
        unique_analysts = {}
        for record in filtered_data:
            analista = record.get('analista', '')
            if analista and isinstance(analista, str) and analista.strip():
                if analista not in unique_analysts:
                    unique_analysts[analista] = {
                        'nome': analista,
                        'total_processos': 0,
                        'sla_medio': [],
                        'desempenho_medio': []
                    }
                unique_analysts[analista]['total_processos'] += 1
                
                # Add SLA and performance for averages
                sla = record.get('sla_dias')
                if sla is not None:
                    unique_analysts[analista]['sla_medio'].append(sla)
                
                desempenho = record.get('desempenho')
                if desempenho is not None:
                    unique_analysts[analista]['desempenho_medio'].append(int(desempenho))
        
        # Convert analysts to list
        analysts_list = []
        for analyst_data in unique_analysts.values():
            sla_values = analyst_data['sla_medio']
            perf_values = analyst_data['desempenho_medio']
            
            avg_sla = round(sum(sla_values) / len(sla_values), 1) if sla_values else None
            avg_perf = round(sum(perf_values) / len(perf_values), 1) if perf_values else None
            
            analysts_list.append({
                'nome': analyst_data['nome'],
                'total_processos': analyst_data['total_processos'],
                'sla_medio': avg_sla,
                'desempenho_medio': avg_perf
            })
        
        analysts_list.sort(key=lambda x: x['total_processos'], reverse=True)
        
        # Calculate distribution by modal
        modal_distribution = {}
        for record in filtered_data:
            modal = record.get('modal', 'N/A')
            if not modal:
                modal = 'N/A'
            if modal not in modal_distribution:
                modal_distribution[modal] = 0
            modal_distribution[modal] += 1
        
        modal_dist_list = [{'label': k, 'value': v} for k, v in modal_distribution.items()]
        
        # Calculate distribution by canal
        canal_distribution = {}
        for record in filtered_data:
            canal = record.get('canal', 'N/A')
            if not canal:
                canal = 'N/A'
            if canal not in canal_distribution:
                canal_distribution[canal] = 0
            canal_distribution[canal] += 1
        
        canal_dist_list = [{'label': k, 'value': v} for k, v in canal_distribution.items()]
        
        # Calendar data - group by date
        calendar_data = []
        date_counts = {}
        for record in filtered_data:
            data_str = record.get('data_registro', '')
            if data_str and isinstance(data_str, str) and len(data_str) >= 10:
                # Already in YYYY-MM-DD format
                date_key = data_str[:10]  # Take only YYYY-MM-DD part
                if date_key not in date_counts:
                    date_counts[date_key] = 0
                date_counts[date_key] += 1
        
        for date, count in date_counts.items():
            calendar_data.append({
                'date': date,
                'count': count
            })
        
        # Alerts - processes with high SLA or performance issues
        alerts = []
        for record in filtered_data:
            sla = record.get('sla_dias')
            if sla and sla > 30:  # SLA above 30 days
                alerts.append({
                    'id': record.get('id_processo'),
                    'ref_unique': record.get('ref_unique', ''),
                    'cliente': record.get('cliente', ''),
                    'analista': record.get('analista', ''),
                    'sla_dias': sla,
                    'data': record.get('data_registro', '')
                })
        
        # Sort alerts by SLA (highest first)
        alerts.sort(key=lambda x: x.get('sla_dias', 0), reverse=True)
        
        # SLA comparison by analyst
        sla_comparison = []
        for analyst in analysts_list[:5]:  # Top 5 analysts
            sla_comparison.append({
                'analista': analyst['nome'],
                'sla_medio': analyst['sla_medio'],
                'total_processos': analyst['total_processos']
            })
        
        # Response data
        response_data = {
            'kpis': {
                'total_processos': total_processos,
                'meta_mensal': meta_mensal,
                'meta_percentual': meta_percentual,
                'meta_a_realizar': meta_a_realizar,
                'sla_medio': sla_medio
            },
            'clients': clients_list[:20],  # Top 20
            'analysts': analysts_list[:10],  # Top 10
            'distribution': {
                'modal': modal_dist_list,
                'canal': canal_dist_list
            },
            'calendar': calendar_data,
            'alerts': alerts[:10],  # Top 10 alerts
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
        # Use Supabase table query instead of execute_sql
        query = supabase_admin.table('importacoes_processos_aberta').select('*', count='exact')
        
        # Apply date filters if provided
        if year and month:
            start_date = f"{year}-{month:02d}-01"
            end_date = f"{year}-{month:02d}-31" 
            query = query.gte('data_registro', start_date).lte('data_registro', end_date)
        elif year:
            query = query.gte('data_registro', f"{year}-01-01").lte('data_registro', f"{year}-12-31")
        
        result = query.execute()
        total_processos = result.count if hasattr(result, 'count') else len(result.data or [])
        
        # Get meta for the period
        meta_mensal = get_meta_data(year, month)
        
        # Calculate meta percentual
        meta_percentual = 0
        if meta_mensal > 0:
            meta_percentual = (total_processos / meta_mensal) * 100
        
        # Meta a realizar
        meta_a_realizar = max(0, meta_mensal - total_processos)
        
        # Average SLA for closed processes - using simple approach
        # For now, return a default value since SLA calculation is complex
        sla_medio = None
        
        # TODO: Implement proper SLA calculation using Supabase queries
        # This would require understanding the exact schema and SLA logic
        
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
            FROM importacoes_processos_aberta
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
            FROM importacoes_processos_aberta
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
            FROM importacoes_processos_aberta
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
            FROM importacoes_processos_aberta
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
            FROM importacoes_processos_aberta
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
            FROM importacoes_processos_aberta
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
            FROM importacoes_processos_aberta
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
    """Get data from same period in previous year for comparison"""
    try:
        if not year:
            return {}
        
        # Always compare to same period in previous year
        # Example: Sep 2025 vs Sep 2024, or Year 2025 vs Year 2024
        if month:
            # Same month in previous year
            prev_year = int(year) - 1
            prev_month = int(month)
            
            prev_filters = [
                "EXTRACT(year FROM data_registro::date) = %(prev_year)s",
                "EXTRACT(month FROM data_registro::date) = %(prev_month)s"
            ]
            prev_params = {'prev_year': prev_year, 'prev_month': prev_month}
        else:
            # Previous year (same as before)
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
            FROM importacoes_processos_aberta
            {where_clause}
            GROUP BY {group_by}
        """
        
        result = supabase_admin.rpc('execute_sql', {'sql_query': query, 'params': prev_params}).execute()
        
        return {row[group_by]: row['total_registros'] for row in result.data}
        
    except Exception as e:
        logger.error(f"Erro ao obter dados do período anterior: {str(e)}")
        return {}

@dashboard_operacional.route('/api/client-modals')
@login_required
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
            FROM importacoes_processos_aberta
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
            FROM importacoes_processos_aberta
            {where_clause} AND modal IS NOT NULL
            GROUP BY modal
        """
        
        result = supabase_admin.rpc('execute_sql', {'sql_query': query, 'params': params}).execute()
        
        return {row['modal']: row['total_registros'] for row in result.data}
        
    except Exception as e:
        logger.error(f"Erro ao obter dados anteriores de modais: {str(e)}")
        return {}

@dashboard_operacional.route('/api/client-processes')
@login_required
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
            FROM importacoes_processos_aberta
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
@login_required
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
            FROM importacoes_processos_aberta
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

@dashboard_operacional.route('/api/operations-monthly')
@login_required
def get_operations_monthly():
    """Get monthly operations data with targets for chart"""
    try:
        year = request.args.get('year', type=int, default=datetime.now().year)
        
        # Get all data from correct table
        response = supabase_admin.table('importacoes_processos_operacional').select('*').execute()
        all_data = response.data
        
        # Group data by month for the specified year
        monthly_data = {}
        for record in all_data:
            data_registro_str = record.get('data_registro', '')
            if data_registro_str and isinstance(data_registro_str, str):
                try:
                    if len(data_registro_str) >= 10:  # YYYY-MM-DD
                        year_str = data_registro_str[:4]
                        month_str = data_registro_str[5:7]
                        
                        if year_str and month_str:
                            record_year = int(year_str)
                            record_month = int(month_str)
                            
                            if record_year == year:
                                month_key = f"{year}-{month_str}"
                                if month_key not in monthly_data:
                                    monthly_data[month_key] = 0
                                monthly_data[month_key] += 1
                except (ValueError, TypeError):
                    continue
        
        # Get monthly targets from fin_metas_projecoes
        monthly_targets = {}
        for month in range(1, 13):
            meta_response = supabase_admin.table('fin_metas_projecoes')\
                .select('meta')\
                .eq('ano', str(year))\
                .eq('mes', f"{month:02d}")\
                .eq('tipo', 'operacional')\
                .execute()
            
            if meta_response.data:
                month_key = f"{year}-{month:02d}"
                monthly_targets[month_key] = int(meta_response.data[0]['meta'])
            else:
                month_key = f"{year}-{month:02d}"
                monthly_targets[month_key] = 0
        
        # Prepare chart data
        months = []
        operations = []
        targets = []
        
        month_names = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 
                      'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
        
        for month in range(1, 13):
            month_key = f"{year}-{month:02d}"
            months.append(month_names[month-1])
            operations.append(monthly_data.get(month_key, 0))
            targets.append(monthly_targets.get(month_key, 0))
        
        return jsonify({
            'success': True,
            'data': {
                'year': year,
                'months': months,
                'operations': operations,
                'targets': targets,
                'total_operations': sum(operations),
                'total_targets': sum(targets)
            },
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter dados mensais: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Erro ao carregar dados mensais: {str(e)}'
        }), 500

@dashboard_operacional.route('/api/operations-daily')
@login_required
def get_operations_daily():
    """Get daily operations data for a specific month"""
    try:
        year = request.args.get('year', type=int, default=datetime.now().year)
        month = request.args.get('month', type=int, default=datetime.now().month)
        
        # Get all data from correct table
        response = supabase_admin.table('importacoes_processos_operacional').select('*').execute()
        all_data = response.data
        
        # Group data by day for the specified year/month
        daily_data = {}
        for record in all_data:
            data_registro_str = record.get('data_registro', '')
            if data_registro_str and isinstance(data_registro_str, str):
                try:
                    if len(data_registro_str) >= 10:  # YYYY-MM-DD
                        year_str = data_registro_str[:4]
                        month_str = data_registro_str[5:7]
                        day_str = data_registro_str[8:10]
                        
                        if year_str and month_str and day_str:
                            record_year = int(year_str)
                            record_month = int(month_str)
                            record_day = int(day_str)
                            
                            if record_year == year and record_month == month:
                                day_key = f"{year}-{month:02d}-{record_day:02d}"
                                if day_key not in daily_data:
                                    daily_data[day_key] = 0
                                daily_data[day_key] += 1
                except (ValueError, TypeError):
                    continue
        
        # Get number of days in the month
        from calendar import monthrange
        _, days_in_month = monthrange(year, month)
        
        # Prepare chart data
        days = []
        operations = []
        
        for day in range(1, days_in_month + 1):
            day_key = f"{year}-{month:02d}-{day:02d}"
            days.append(f"{day:02d}")
            operations.append(daily_data.get(day_key, 0))
        
        # Get monthly target for reference
        meta_response = supabase_admin.table('fin_metas_projecoes')\
            .select('meta')\
            .eq('ano', str(year))\
            .eq('mes', f"{month:02d}")\
            .eq('tipo', 'operacional')\
            .execute()
        
        monthly_target = int(meta_response.data[0]['meta']) if meta_response.data else 0
        daily_target = round(monthly_target / days_in_month, 1) if monthly_target > 0 else 0
        
        # Month names in Portuguese
        month_names = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                      'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
        
        return jsonify({
            'success': True,
            'data': {
                'year': year,
                'month': month,
                'month_name': month_names[month-1],
                'days': days,
                'operations': operations,
                'daily_target': daily_target,
                'total_operations': sum(operations),
                'monthly_target': monthly_target
            },
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter dados diários: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Erro ao carregar dados diários: {str(e)}'
        }), 500
