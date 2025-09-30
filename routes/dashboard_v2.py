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

@bp.route('/api/monthly-chart')
@login_required
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def monthly_chart():
    """Retorna dados do gráfico de evolução por granularidade (mensal, semanal, diário)"""
    try:
        granularidade = request.args.get('granularidade', 'mensal')
        user_data = session.get('user', {})
        user_id = user_data.get('id')
        data = data_cache.get_cache(user_id, 'dashboard_v2_data')
        if not data:
            return jsonify({'success': False, 'error': 'Dados não encontrados.', 'data': {}})
        df = pd.DataFrame(data)
        # Garantir colunas necessárias
        if 'data_abertura' not in df.columns or 'custo_total' not in df.columns:
            return jsonify({'success': False, 'error': 'Colunas necessárias não encontradas.', 'data': {}})
        # Converter datas
        df['data_abertura_dt'] = pd.to_datetime(df['data_abertura'], format='%d/%m/%Y', errors='coerce')
        df = df.dropna(subset=['data_abertura_dt'])
        if granularidade == 'mensal':
            df['periodo'] = df['data_abertura_dt'].dt.strftime('%m/%Y')
        elif granularidade == 'semanal':
            # Agrupar por ano-semana
            df['periodo'] = df['data_abertura_dt'].dt.strftime('%Y-%U')
        elif granularidade == 'diario':
            df['periodo'] = df['data_abertura_dt'].dt.strftime('%d/%m/%Y')
        else:
            df['periodo'] = df['data_abertura_dt'].dt.strftime('%m/%Y')
        grouped = df.groupby('periodo').agg({
            'ref_unique': 'count',
            'custo_total': 'sum'
        }).reset_index().sort_values('periodo')
        chart_data = {
            'periods': grouped['periodo'].tolist(),
            'processes': grouped['ref_unique'].tolist(),
            'values': grouped['custo_total'].tolist()
        }
        return jsonify({'success': True, 'data': clean_data_for_json(chart_data)})
    except Exception as e:
        print(f"[DASHBOARD_V2] Erro ao gerar monthly_chart: {str(e)}")
        return jsonify({'success': False, 'error': str(e), 'data': {}}), 500

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
        
        # Filtrar por empresa se for cliente ou admin operação
        if user_role == 'cliente_unique':
            user_companies = get_user_companies(user_data)
            if user_companies:
                query = query.in_('cnpj_importador', user_companies)
            else:
                # Cliente sem empresas não deve ver nada
                query = query.eq('cnpj_importador', 'NENHUMA_EMPRESA_ENCONTRADA')
        elif user_role == 'interno_unique':
            user_perfil_principal = user_data.get('perfil_principal', 'basico')
            
            if user_perfil_principal == 'admin_operacao':
                user_companies = get_user_companies(user_data)
                if user_companies:
                    query = query.in_('cnpj_importador', user_companies)
                else:
                    # Admin operação sem empresas não deve ver nada
                    query = query.eq('cnpj_importador', 'NENHUMA_EMPRESA_ENCONTRADA')
        
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
        
        # Calcular KPIs executivos
        total_processos = len(df)
        total_despesas = df['custo_total'].sum() if 'custo_total' in df.columns else 0
        ticket_medio = (total_despesas / total_processos) if total_processos > 0 else 0
        em_transito = len(df[df['status_processo'].str.contains('trânsito', case=False, na=False)]) if 'status_processo' in df.columns else 0

        # Total Agd Embarque: status_processo contém 'aguardando embarque'
        total_agd_embarque = len(df[df['status_processo'].str.contains('aguardando embarque', case=False, na=False)]) if 'status_processo' in df.columns else 0
        # Total Ag Chegada: status_processo contém 'aguardando chegada'
        total_ag_chegada = len(df[df['status_processo'].str.contains('aguardando chegada', case=False, na=False)]) if 'status_processo' in df.columns else 0

        # Chegando este mês/semana (quantidade e custo)
        hoje = pd.Timestamp.now().normalize()
        primeiro_dia_mes = hoje.replace(day=1)
        inicio_semana = hoje - pd.Timedelta(days=hoje.dayofweek)
        chegando_mes = 0
        chegando_mes_custo = 0
        chegando_semana = 0
        chegando_semana_custo = 0
        if 'data_chegada' in df.columns:
            df['chegada_dt'] = pd.to_datetime(df['data_chegada'], format='%d/%m/%Y', errors='coerce')
            for _, row in df.iterrows():
                chegada = row.get('chegada_dt')
                custo = row.get('custo_total', 0)
                if pd.notnull(chegada):
                    if chegada >= primeiro_dia_mes and chegada <= hoje + pd.Timedelta(days=31):
                        chegando_mes += 1
                        chegando_mes_custo += custo if pd.notnull(custo) else 0
                    if chegada >= inicio_semana and chegada <= hoje + pd.Timedelta(days=7):
                        chegando_semana += 1
                        chegando_semana_custo += custo if pd.notnull(custo) else 0

        # Transit time médio
        transit_time = 0
        if 'data_embarque' in df.columns and 'data_chegada' in df.columns:
            datas_validas = df.dropna(subset=['data_embarque', 'data_chegada'])
            if not datas_validas.empty:
                datas_validas['embarque_dt'] = pd.to_datetime(datas_validas['data_embarque'], format='%d/%m/%Y', errors='coerce')
                datas_validas['chegada_dt'] = pd.to_datetime(datas_validas['data_chegada'], format='%d/%m/%Y', errors='coerce')
                datas_validas = datas_validas.dropna(subset=['embarque_dt', 'chegada_dt'])
                if not datas_validas.empty:
                    transit_time = (datas_validas['chegada_dt'] - datas_validas['embarque_dt']).dt.days.mean()
        # Processos médios por mês/semana
        if 'data_abertura' in df.columns:
            datas = pd.to_datetime(df['data_abertura'], format='%d/%m/%Y', errors='coerce')
            datas = datas.dropna()
            if not datas.empty:
                min_data = datas.min()
                max_data = datas.max()
                total_meses = max(1, ((max_data.year - min_data.year) * 12 + (max_data.month - min_data.month) + 1))
                total_semanas = max(1, int((max_data - min_data).days / 7) + 1)
                processos_mes = total_processos / total_meses
                processos_semana = total_processos / total_semanas
            else:
                processos_mes = processos_semana = 0
        else:
            processos_mes = processos_semana = 0
        kpis = {
            'total_processos': total_processos,
            'total_despesas': total_despesas,
            'ticket_medio': ticket_medio,
            'em_transito': em_transito,
            'total_agd_embarque': total_agd_embarque,
            'total_ag_chegada': total_ag_chegada,
            'chegando_mes': chegando_mes,
            'chegando_mes_custo': chegando_mes_custo,
            'chegando_semana': chegando_semana,
            'chegando_semana_custo': chegando_semana_custo,
            'transit_time_medio': transit_time,
            'processos_mes': processos_mes,
            'processos_semana': processos_semana
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
        
        # Gráfico Evolução Mensal (mantido)
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

        # Gráfico de Status do Processo
        if 'status_processo' in df.columns:
            status_data = df['status_processo'].value_counts()
            status_chart = {
                'labels': status_data.index.tolist(),
                'values': status_data.values.tolist()
            }
        else:
            status_chart = {'labels': [], 'values': []}

        # Gráfico de Barras Agrupadas: Processos e Custo Total por Modal
        print(f"[DASHBOARD_V2] Grouped Modal Chart - Colunas disponíveis: {df.columns.tolist()}")
        print(f"[DASHBOARD_V2] Grouped Modal Chart - Verificando colunas: modal={('modal' in df.columns)}, custo_total={('custo_total' in df.columns)}")
        
        if 'modal' in df.columns and 'custo_total' in df.columns:
            print(f"[DASHBOARD_V2] Grouped Modal Chart - Valores únicos de modal: {df['modal'].unique()}")
            print(f"[DASHBOARD_V2] Grouped Modal Chart - Valores de custo_total (primeiros 5): {df['custo_total'].head().tolist()}")
            print(f"[DASHBOARD_V2] Grouped Modal Chart - Total de registros: {len(df)}")
            
            modal_group = df.groupby('modal').agg({
                'ref_unique': 'count',
                'custo_total': 'sum'
            }).reset_index()
            
            print(f"[DASHBOARD_V2] Grouped Modal Chart - Resultado do groupby: {modal_group.to_dict('records')}")
            
            grouped_modal_chart = {
                'labels': modal_group['modal'].tolist(),
                'processos': modal_group['ref_unique'].tolist(),
                'custos': modal_group['custo_total'].tolist()
            }
            
            print(f"[DASHBOARD_V2] Grouped Modal Chart - Dados finais: {grouped_modal_chart}")
        else:
            print(f"[DASHBOARD_V2] Grouped Modal Chart - Colunas não encontradas, retornando vazio")
            grouped_modal_chart = {'labels': [], 'processos': [], 'custos': []}

        # Gráfico País Procedência (usando coluna normalizada)
        if 'pais_procedencia_normalizado' in df.columns:
            pais_data = df['pais_procedencia_normalizado'].value_counts().head(10)
            urf_chart = {
                'labels': pais_data.index.tolist(),
                'values': pais_data.values.tolist()
            }
        elif 'pais_procedencia' in df.columns:
            pais_data = df['pais_procedencia'].value_counts().head(10)
            urf_chart = {
                'labels': pais_data.index.tolist(),
                'values': pais_data.values.tolist()
            }
        else:
            urf_chart = {'labels': [], 'values': []}

        # Gráfico Materiais (usando coluna normalizada)
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
            'status': status_chart,
            'grouped_modal': grouped_modal_chart,
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
        
        # Selecionar colunas relevantes (priorizando normalizadas)
        relevant_columns = [
            'ref_unique', 'importador', 'data_abertura', 'exportador_fornecedor', 
            'modal', 'status_processo', 'custo_total', 'data_chegada'
        ]
        
        # Adicionar colunas normalizadas se disponíveis, senão usar originais
        if 'mercadoria' in df_sorted.columns:
            relevant_columns.append('mercadoria')
        elif 'mercadoria' in df_sorted.columns:
            relevant_columns.append('mercadoria')
            
        if 'pais_procedencia_normalizado' in df_sorted.columns:
            relevant_columns.append('pais_procedencia_normalizado')
        elif 'pais_procedencia' in df_sorted.columns:
            relevant_columns.append('pais_procedencia')
        
        available_columns = [col for col in relevant_columns if col in df_sorted.columns]
        operations_data = df_sorted[available_columns].to_dict('records')
        
        # Renomear colunas normalizadas para exibição
        for record in operations_data:
            if 'mercadoria' in record:
                record['mercadoria'] = record.pop('mercadoria')
            if 'pais_procedencia_normalizado' in record:
                record['pais_procedencia'] = record.pop('pais_procedencia_normalizado')
        
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
