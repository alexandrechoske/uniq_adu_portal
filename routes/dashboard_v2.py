from flask import Blueprint, render_template, session, jsonify, request
from extensions import supabase, supabase_admin
from routes.auth import login_required, role_required
from routes.api import get_user_companies
from permissions import check_permission
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from services.data_cache import DataCacheService

bp = Blueprint('dashboard_v2', __name__, url_prefix='/dashboard-v2')

# Instanciar o serviço de cache
data_cache = DataCacheService()

def clean_data_for_json(data):
    """Remove valores NaN e converte para tipos JSON-safe"""
    if isinstance(data, dict):
        return {k: clean_data_for_json(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_data_for_json(item) for item in data]
    elif pd.isna(data) or data is None or (isinstance(data, float) and np.isnan(data)):
        return 0
    elif isinstance(data, (np.integer, np.floating)):
        if np.isnan(data) or np.isinf(data):
            return 0
        return int(data) if isinstance(data, np.integer) else float(data)
    else:
        return data

@bp.route('/')
@login_required
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def index():
    """Página principal unificada - Dashboard + Materiais"""
    return render_template('dashboard_v2/index.html')

@bp.route('/api/load-data')
@login_required
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def load_data():
    """Carregar dados da view vw_importacoes_6_meses"""
    try:
        print("[DASHBOARD_V2] Iniciando carregamento de dados da view...")
        
        # Obter dados do usuário
        user_data = session.get('user', {})
        user_role = user_data.get('role')
        user_id = user_data.get('id')
        
        # Verificar se já existe cache
        cache_key = f"dashboard_v2_data_{user_id}"
        cached_data = data_cache.get_cache(user_id, 'dashboard_v2_data')
        
        if cached_data:
            print(f"[DASHBOARD_V2] Cache encontrado: {len(cached_data)} registros")
            # Armazenar apenas um flag na sessão
            session['dashboard_v2_loaded'] = True
            return jsonify({
                'success': True,
                'data': cached_data,
                'total_records': len(cached_data)
            })
        
        # Query base da view
        query = supabase_admin.table('vw_importacoes_6_meses').select('*')
        
        # Filtrar por empresa se for cliente
        if user_role == 'cliente_unique':
            user_companies = get_user_companies()
            if user_companies:
                query = query.in_('cnpj_importador', user_companies)
        
        # Executar query
        result = query.execute()
        
        if not result.data:
            print("[DASHBOARD_V2] Nenhum dado encontrado")
            return jsonify({
                'success': False,
                'error': 'Nenhum dado encontrado',
                'data': []
            })
        
        print(f"[DASHBOARD_V2] Dados carregados: {len(result.data)} registros")
        
        # Armazenar dados no cache do servidor
        data_cache.set_cache(user_id, 'dashboard_v2_data', result.data)
        print(f"[DASHBOARD_V2] Cache armazenado para user_id: {user_id} com {len(result.data)} registros")
        
        # Armazenar apenas um flag na sessão
        session['dashboard_v2_loaded'] = True
        
        return jsonify({
            'success': True,
            'data': result.data,
            'total_records': len(result.data)
        })
        
    except Exception as e:
        print(f"[DASHBOARD_V2] Erro ao carregar dados: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': []
        }), 500

@bp.route('/api/dashboard-kpis')
@login_required
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def dashboard_kpis():
    """Calcular KPIs para o dashboard"""
    try:
        # Obter dados do cache
        user_data = session.get('user', {})
        user_id = user_data.get('id')
        
        data = data_cache.get_cache(user_id, 'dashboard_v2_data')
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Dados não encontrados. Recarregue a página.',
                'kpis': {}
            })
        
        df = pd.DataFrame(data)
        
        # Calcular KPIs básicos
        kpis = {
            'total_processos': len(df),
            'total_despesas': df['custo_total'].sum() if 'custo_total' in df.columns else 0,
            'modal_aereo': len(df[df['modal'] == 'Aérea']) if 'modal' in df.columns else 0,
            'modal_maritimo': len(df[df['modal'] == 'Marítima']) if 'modal' in df.columns else 0,
            'em_transito': len(df[df['status_processo'].str.contains('trânsito', case=False, na=False)]) if 'status_processo' in df.columns else 0,
            'di_registrada': len(df[df['status_processo'].str.contains('registrada', case=False, na=False)]) if 'status_processo' in df.columns else 0,
            'despesa_media_por_processo': df['custo_total'].mean() if 'custo_total' in df.columns else 0,
            'despesa_mes_atual': df[df['data_abertura'].str.contains(datetime.now().strftime('%m/%Y'), na=False)]['custo_total'].sum() if 'data_abertura' in df.columns and 'custo_total' in df.columns else 0
        }
        
        return jsonify({
            'success': True,
            'kpis': clean_data_for_json(kpis)
        })
        
    except Exception as e:
        print(f"[DASHBOARD_V2] Erro ao calcular KPIs: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'kpis': {}
        }), 500

@bp.route('/api/dashboard-charts')
@login_required
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def dashboard_charts():
    """Gerar dados para os gráficos do dashboard"""
    try:
        # Obter dados do cache
        user_data = session.get('user', {})
        user_id = user_data.get('id')
        
        data = data_cache.get_cache(user_id, 'dashboard_v2_data')
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Dados não encontrados.',
                'charts': {}
            })
        
        df = pd.DataFrame(data)
        
        # Gráfico Evolução Mensal
        if 'data_abertura' in df.columns and 'custo_total' in df.columns:
            df['mes_ano'] = df['data_abertura'].apply(lambda x: x.split('/')[1] + '/' + x.split('/')[2] if '/' in str(x) else '')
            monthly_data = df.groupby('mes_ano').agg({
                'ref_unique': 'count',
                'custo_total': 'sum'
            }).reset_index()
            
            monthly_chart = {
                'periods': monthly_data['mes_ano'].tolist(),
                'processes': monthly_data['ref_unique'].tolist(),
                'values': monthly_data['custo_total'].tolist()
            }
        else:
            monthly_chart = {'periods': [], 'processes': [], 'values': []}
        
        # Gráfico Modal
        if 'modal' in df.columns:
            modal_data = df['modal'].value_counts().head(10)
            modal_chart = {
                'labels': modal_data.index.tolist(),
                'values': modal_data.values.tolist()
            }
        else:
            modal_chart = {'labels': [], 'values': []}
        
        # Gráfico URF
        if 'urf_entrada' in df.columns:
            urf_data = df['urf_entrada'].value_counts().head(10)
            urf_chart = {
                'labels': urf_data.index.tolist(),
                'values': urf_data.values.tolist()
            }
        else:
            urf_chart = {'labels': [], 'values': []}
        
        # Gráfico Materiais
        if 'mercadoria' in df.columns:
            material_data = df['mercadoria'].value_counts().head(10)
            material_chart = {
                'labels': material_data.index.tolist(),
                'values': material_data.values.tolist()
            }
        else:
            material_chart = {'labels': [], 'values': []}
        
        charts = {
            'monthly': monthly_chart,
            'modal': modal_chart,
            'urf': urf_chart,
            'material': material_chart
        }
        
        return jsonify({
            'success': True,
            'charts': clean_data_for_json(charts)
        })
        
    except Exception as e:
        print(f"[DASHBOARD_V2] Erro ao gerar gráficos: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'charts': {}
        }), 500

@bp.route('/api/recent-operations')
@login_required
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def recent_operations():
    """Obter operações recentes para a tabela"""
    try:
        # Obter dados do cache
        user_data = session.get('user', {})
        user_id = user_data.get('id')
        
        data = data_cache.get_cache(user_id, 'dashboard_v2_data')
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Dados não encontrados.',
                'operations': []
            })
        
        # Ordenar por data mais recente e limitar a 50 registros
        df = pd.DataFrame(data)
        
        if 'data_abertura' in df.columns:
            # Converter data para ordenação (assumindo formato DD/MM/YYYY)
            df['data_sort'] = pd.to_datetime(df['data_abertura'], format='%d/%m/%Y', errors='coerce')
            df_sorted = df.sort_values('data_sort', ascending=False).head(50)
        else:
            df_sorted = df.head(50)
        
        # Selecionar colunas relevantes
        relevant_columns = [
            'ref_unique', 'importador', 'data_abertura', 'exportador_fornecedor', 
            'modal', 'status_processo', 'mercadoria', 'custo_total', 
            'urf_entrada', 'data_chegada'
        ]
        
        available_columns = [col for col in relevant_columns if col in df_sorted.columns]
        operations_data = df_sorted[available_columns].to_dict('records')
        
        return jsonify({
            'success': True,
            'operations': clean_data_for_json(operations_data)
        })
        
    except Exception as e:
        print(f"[DASHBOARD_V2] Erro ao obter operações recentes: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'operations': []
        }), 500
