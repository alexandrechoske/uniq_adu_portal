from flask import Blueprint, render_template, session, request, jsonify
from extensions import supabase
from routes.auth import login_required, role_required
from permissions import check_permission
from config import Config
import pandas as pd
from datetime import datetime, timedelta

bp = Blueprint('dashboard', __name__)

def format_value_smart(value, currency=False):
    """Format values with K, M, B abbreviations for better readability"""
    if not value or value == 0 or str(value) == 'nan':
        return "0" if currency else "0"
    
    try:
        num = float(value)
        if pd.isna(num) or num == 0:
            return "0" if currency else "0"
    except (ValueError, TypeError):
        return "0" if currency else "0"
    
    # Determine suffix and divide accordingly
    if abs(num) >= 1_000_000_000:  # Bilhões
        formatted = num / 1_000_000_000
        suffix = "B"
    elif abs(num) >= 1_000_000:  # Milhões
        formatted = num / 1_000_000
        suffix = "M"
    elif abs(num) >= 1_000:  # Milhares
        formatted = num / 1_000
        suffix = "K"
    else:
        formatted = num
        suffix = ""
    
    # Format to 1 decimal place, remove .0 if not needed
    if suffix:
        if formatted == int(formatted):
            value_str = f"{int(formatted)}{suffix}"
        else:
            value_str = f"{formatted:.1f}{suffix}"
    else:
        value_str = f"{int(formatted)}" if formatted == int(formatted) else f"{formatted:.1f}"
    
    return f"{value_str}" if currency else value_str

@bp.route('/dashboard')
@check_permission()
def index(**kwargs):
    """Dashboard principal com carregamento inicial rápido e dados assíncronos"""
    # Get user companies if client
    user_companies = []
    if session['user']['role'] == 'cliente_unique':
        user_companies = session['user'].get('user_companies', [])
    
    selected_company = request.args.get('empresa')
    
    # Timestamp da última atualização
    last_update = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    
    # Get currency exchange rates
    currencies = {
        'USD': 5.50,  # Valor estimado
        'EUR': 6.00,  # Valor estimado
        'last_updated': datetime.now().strftime('%Y-%m-%d')
    }
    
    # Get all available companies for filtering
    data_limite_companies = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
    companies_query = supabase.table('importacoes_processos_aberta')\
        .select('cnpj_importador, importador')\
        .neq('cnpj_importador', '')\
        .not_.is_('cnpj_importador', 'null')\
        .gte('data_abertura', data_limite_companies)\
        .execute()
    
    all_companies = []
    if companies_query.data:
        companies_df = pd.DataFrame(companies_query.data)
        all_companies = [
            {'cpfcnpj': row['cnpj_importador'], 'nome': row['importador']}
            for _, row in companies_df.drop_duplicates(subset=['cnpj_importador']).iterrows()
        ]
    
    # Filter companies based on user role
    available_companies = all_companies
    if session['user']['role'] == 'cliente_unique' and user_companies:
        available_companies = [c for c in all_companies if c['cpfcnpj'] in user_companies]
    
    # Retornar página com estrutura básica - dados serão carregados via AJAX
    return render_template('dashboard/index.html', 
                         kpis={}, 
                         analise_material=[],
                         material_analysis=[],
                         data=[],
                         table_data=[], 
                         daily_chart=None,
                         monthly_chart=None,
                         canal_chart=None,
                         radar_chart=None,
                         material_chart=None,
                         companies=available_companies,
                         selected_company=selected_company,
                         currencies=currencies, 
                         last_update=last_update,
                         user_role=session['user']['role'],
                         async_loading=True)

@bp.route('/api/dashboard-data')
@check_permission()
def dashboard_data_api():
    """API endpoint para carregamento assíncrono de dados do dashboard"""
    try:
        # Parâmetros da requisição
        periodo = request.args.get('periodo', '30')  # Padrão: 30 dias
        empresa = request.args.get('empresa')
        charts_only = request.args.get('charts', '0') == '1'  # Novo parâmetro para dados de gráficos
        
        # Get user companies if client
        user_companies = []
        if session['user']['role'] == 'cliente_unique':
            user_companies = session['user'].get('user_companies', [])
        
        current_role = session['user']['role']
        admin_roles = ['interno_unique', 'adm', 'admin', 'system']
        
        # Calcular data limite baseada no período
        if periodo == 'all':
            data_limite = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        else:
            dias = int(periodo) if periodo.isdigit() else 30
            data_limite = (datetime.now() - timedelta(days=dias)).strftime('%Y-%m-%d')
        
        print(f"[DEBUG DASHBOARD API] Carregando dados para período: {periodo} dias (desde: {data_limite})")
        
        # Build query
        query = supabase.table('importacoes_processos_aberta').select(
            'id, status_processo, canal, data_chegada, '
            'valor_cif_real, cnpj_importador, importador, '
            'modal, data_abertura, mercadoria, data_embarque, '
            'urf_entrada, ref_unique'
        ).neq('status_processo', 'Despacho Cancelado')\
         .gte('data_abertura', data_limite)\
         .order('data_abertura.desc')
        
        # Apply filters based on user role and selected company
        if current_role == 'cliente_unique':
            if not user_companies:
                return jsonify({'error': 'Nenhuma empresa associada ao usuário'})
            
            if empresa and empresa in user_companies:
                query = query.eq('cnpj_importador', empresa)
            else:
                query = query.in_('cnpj_importador', user_companies)
        elif empresa:
            query = query.eq('cnpj_importador', empresa)
        
        # Execute query
        operacoes = query.execute()
        data = operacoes.data if operacoes.data else []
        print(f"[DEBUG DASHBOARD API] Registros retornados: {len(data)}")
        
        if not data:
            return jsonify({
                'success': True,
                'data': {
                    'kpis': {},
                    'material_analysis': [],
                    'table_data': [],
                    'record_count': 0,
                    'periodo_info': f"Últimos {periodo} dias" if periodo != 'all' else "Todos os registros",
                    'charts': {}
                }
            })
        
        df = pd.DataFrame(data)
        
        # Processamento rápido dos dados
        df['valor_cif_real'] = pd.to_numeric(df['valor_cif_real'], errors='coerce').fillna(0)
        df['data_abertura'] = pd.to_datetime(df['data_abertura'], format='%d/%m/%Y', errors='coerce')
        df['data_embarque'] = pd.to_datetime(df['data_embarque'], format='%d/%m/%Y', errors='coerce')
        df['data_chegada'] = pd.to_datetime(df['data_chegada'], format='%d/%m/%Y', errors='coerce')
        
        # Preparar dados Chart.js
        charts_data = {}
        
        # 1. Gráfico Mensal (Line Chart)
        df_monthly = df.copy()
        df_monthly['mes_ano'] = df_monthly['data_abertura'].dt.to_period('M')
        monthly_data = df_monthly.groupby('mes_ano').agg({
            'ref_unique': 'count',
            'valor_cif_real': 'sum'
        }).reset_index()
        
        monthly_data['data'] = monthly_data['mes_ano'].dt.to_timestamp()
        monthly_data = monthly_data.sort_values('data').tail(12)
        
        # Sanitizar valores para evitar NaN
        processes_values = monthly_data['ref_unique'].fillna(0).tolist()
        value_values = monthly_data['valor_cif_real'].fillna(0).tolist()
        
        charts_data['monthly'] = {
            'months': [d.strftime('%b %Y') for d in monthly_data['data']],
            'processes': [int(v) for v in processes_values],
            'values': [round(float(v)/1000000, 1) if v > 0 else 0.0 for v in value_values]
        }
        
        # 2. Gráfico de Canal DI (Doughnut Chart)
        canal_data = df['canal'].value_counts()
        charts_data['canal'] = {
            'labels': canal_data.index.tolist(),
            'values': [int(v) for v in canal_data.values.tolist()]
        }
        
        # 3. Gráfico de Armazéns/URF (Horizontal Bar Chart)
        armazem_data = df.groupby('urf_entrada').agg({
            'ref_unique': 'count'
        }).reset_index()
        armazem_data = armazem_data.sort_values('ref_unique', ascending=True).tail(8)
        
        charts_data['armazem'] = {
            'labels': [str(label)[:20] + '...' if len(str(label)) > 20 else str(label) 
                      for label in armazem_data['urf_entrada'].tolist()],
            'values': [int(v) for v in armazem_data['ref_unique'].fillna(0).tolist()]
        }
        
        # 4. Gráfico de Materiais (Horizontal Bar Chart)
        material_data = df.groupby('mercadoria').agg({
            'valor_cif_real': 'sum'
        }).reset_index()
        material_data = material_data.sort_values('valor_cif_real', ascending=True).tail(8)
        
        material_values = material_data['valor_cif_real'].fillna(0).tolist()
        charts_data['material'] = {
            'labels': [str(label)[:25] + '...' if len(str(label)) > 25 else str(label) 
                      for label in material_data['mercadoria'].tolist()],
            'values': [round(float(v)/1000000, 1) if v > 0 else 0.0 for v in material_values]
        }
        
        # Se for apenas para gráficos, retornar apenas os dados dos gráficos
        if charts_only:
            return jsonify({
                'success': True,
                'data': charts_data
            })
        
        # Calcular KPIs
        total_operations = len(df)
        
        # Métricas por modal
        modal_counts = df['modal'].value_counts()
        aereo = modal_counts.get('AÉREA', 0)
        terrestre = modal_counts.get('RODOVIÁRIA', 0)
        maritimo = modal_counts.get('MARÍTIMA', 0)
        
        # Métricas por status
        aguardando_embarque = len(df[df['status_processo'].str.contains('DECLARACAO', na=False, case=False)])
        aguardando_chegada = len(df[df['status_processo'].str.contains('TRANSITO', na=False, case=False)])
        di_registrada = len(df[df['status_processo'].str.contains('DESEMBARACADA', na=False, case=False)])
        
        # Métricas de VMCV
        vmcv_total = df['valor_cif_real'].sum()
        valor_medio_processo = vmcv_total / total_operations if total_operations > 0 else 0
        despesas_total = vmcv_total * 0.4
        despesa_media_processo = despesas_total / total_operations if total_operations > 0 else 0
        
        # KPIs response
        kpis = {
            'total': int(total_operations),
            'aereo': int(aereo),
            'terrestre': int(terrestre),
            'maritimo': int(maritimo),
            'aguardando_embarque': int(aguardando_embarque),
            'aguardando_chegada': int(aguardando_chegada),
            'di_registrada': int(di_registrada),
            'vmcv_total': float(vmcv_total),
            'valor_total_formatted': format_value_smart(vmcv_total, currency=True),
            'valor_medio_processo': float(valor_medio_processo),
            'valor_medio_processo_formatted': format_value_smart(valor_medio_processo, currency=True),
            'despesas_total': float(despesas_total),
            'despesas_total_formatted': format_value_smart(despesas_total, currency=True),
            'despesa_media_processo': float(despesa_media_processo),
            'despesa_media_processo_formatted': format_value_smart(despesa_media_processo, currency=True)
        }
        
        # Análise de materiais (top 10)
        material_analysis = []
        if not df.empty:
            material_groups = df.groupby('mercadoria').agg({
                'ref_unique': 'count',
                'valor_cif_real': 'sum'
            }).reset_index()
            
            material_groups = material_groups.sort_values('valor_cif_real', ascending=False)
            total_vmcv_materials = material_groups['valor_cif_real'].sum()
            
            for _, row in material_groups.head(10).iterrows():
                material = row['mercadoria'] if row['mercadoria'] else 'Não Informado'
                quantidade = int(row['ref_unique'])
                valor_total = float(row['valor_cif_real'])
                percentual = (valor_total / total_vmcv_materials * 100) if total_vmcv_materials > 0 else 0
                
                material_analysis.append({
                    'material': material,
                    'quantidade': quantidade,
                    'valor_total': valor_total,
                    'valor_total_formatado': format_value_smart(valor_total, currency=True),
                    'percentual': round(percentual, 1)
                })
        
        # Dados da tabela (limitados para performance)
        table_data = []
        for _, row in df.head(100).iterrows():
            table_data.append({
                'importador': row.get('importador', ''),
                'modal': row.get('modal', ''),
                'urf_entrada': row.get('urf_entrada', ''),
                'status_processo': row.get('status_processo', ''),
                'mercadoria': row.get('mercadoria', ''),
                'valor_cif_real': float(row.get('valor_cif_real', 0) or 0),
                'valor_cif_formatted': format_value_smart(row.get('valor_cif_real', 0) or 0, currency=True)
            })
        
        return jsonify({
            'success': True,
            'data': {
                'kpis': kpis,
                'material_analysis': material_analysis,
                'table_data': table_data,
                'record_count': total_operations,
                'periodo_info': f"Últimos {periodo} dias" if periodo != 'all' else "Todos os registros",
                'last_update': datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                'charts': charts_data
            }
        })
        
    except Exception as e:
        print(f"[ERROR DASHBOARD API] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})
