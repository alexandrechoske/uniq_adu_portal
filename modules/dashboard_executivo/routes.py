from flask import Blueprint, render_template, session, jsonify, request
from extensions import supabase, supabase_admin
from routes.auth import login_required, role_required
from routes.api import get_user_companies
from permissions import check_permission
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from services.data_cache import DataCacheService

# Instanciar o serviço de cache
data_cache = DataCacheService()

# Blueprint com configuração para templates e static locais
bp = Blueprint('dashboard_executivo', __name__, 
               url_prefix='/dashboard-executivo',
               template_folder='templates',
               static_folder='static',
               static_url_path='/dashboard-executivo/static')

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
    """Página principal do Dashboard Executivo"""
    return render_template('dashboard_executivo.html')

@bp.route('/api/load-data')
@login_required
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def load_data():
    """Carregar dados da view vw_importacoes_6_meses"""
    try:
        print("[DASHBOARD_EXECUTIVO] Iniciando carregamento de dados da view...")
        
        # Obter dados do usuário
        user_data = session.get('user', {})
        user_role = user_data.get('role')
        user_id = user_data.get('id')
        
        # Verificar se já existe cache
        cached_data = data_cache.get_cache(user_id, 'dashboard_v2_data')
        
        if cached_data:
            print(f"[DASHBOARD_EXECUTIVO] Cache encontrado: {len(cached_data)} registros")
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
            user_companies = get_user_companies(user_data)
            if user_companies:
                query = query.in_('cnpj_importador', user_companies)
        
        # Executar query
        result = query.execute()
        
        if not result.data:
            print("[DASHBOARD_EXECUTIVO] Nenhum dado encontrado")
            return jsonify({
                'success': False,
                'error': 'Nenhum dado encontrado',
                'data': []
            })
        
        print(f"[DASHBOARD_EXECUTIVO] Dados carregados: {len(result.data)} registros")
        
        # Armazenar dados no cache do servidor
        data_cache.set_cache(user_id, 'dashboard_v2_data', result.data)
        print(f"[DASHBOARD_EXECUTIVO] Cache armazenado para user_id: {user_id} com {len(result.data)} registros")
        
        session['dashboard_v2_loaded'] = True
        
        return jsonify({
            'success': True,
            'data': result.data,
            'total_records': len(result.data)
        })
        
    except Exception as e:
        print(f"[DASHBOARD_EXECUTIVO] Erro ao carregar dados: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': []
        }), 500

@bp.route('/api/kpis')
@login_required
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def dashboard_kpis():
    """Calcular KPIs para o dashboard executivo"""
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

        # Total Aguardando Embarque
        total_agd_embarque = len(df[df['status_processo'].str.contains('aguardando embarque', case=False, na=False)]) if 'status_processo' in df.columns else 0
        # Total Aguardando Chegada
        total_ag_chegada = len(df[df['status_processo'].str.contains('aguardando chegada', case=False, na=False)]) if 'status_processo' in df.columns else 0

        # Chegando/Chegou este mês/semana (quantidade e custo)
        hoje = pd.Timestamp.now().normalize()
        primeiro_dia_mes = hoje.replace(day=1)
        ultimo_dia_mes = (primeiro_dia_mes + pd.DateOffset(months=1)) - pd.Timedelta(days=1)
        
        # Calcular semana atual (domingo a sábado)
        dias_desde_domingo = (hoje.dayofweek + 1) % 7  # 0=domingo, 1=segunda, etc.
        inicio_semana = hoje - pd.Timedelta(days=dias_desde_domingo)
        fim_semana = inicio_semana + pd.Timedelta(days=6)
        
        # Chegando = data_chegada >= hoje (futuro)
        chegando_mes = 0
        chegando_mes_custo = 0
        chegando_semana = 0
        chegando_semana_custo = 0
        
        # Chegou = data_chegada < hoje (passado)
        chegou_mes = 0
        chegou_mes_custo = 0
        chegou_semana = 0
        chegou_semana_custo = 0
        
        if 'data_chegada' in df.columns:
            df['chegada_dt'] = pd.to_datetime(df['data_chegada'], format='%d/%m/%Y', errors='coerce')
            print(f"[DEBUG_KPI] Total registros: {len(df)}")
            print(f"[DEBUG_KPI] Registros com data_chegada válida: {df['chegada_dt'].notnull().sum()}")
            print(f"[DEBUG_KPI] Hoje: {hoje.strftime('%d/%m/%Y')}")
            print(f"[DEBUG_KPI] Semana: {inicio_semana.strftime('%d/%m/%Y')} a {fim_semana.strftime('%d/%m/%Y')}")
            print(f"[DEBUG_KPI] Mês: {primeiro_dia_mes.strftime('%d/%m/%Y')} a {ultimo_dia_mes.strftime('%d/%m/%Y')}")
            
            for idx, row in df.iterrows():
                chegada = row.get('chegada_dt')
                custo = row.get('custo_total', 0) or 0
                data_str = row.get('data_chegada', 'SEM DATA')
                
                if pd.notnull(chegada) and idx < 5:  # Log apenas os primeiros 5
                    print(f"[DEBUG_KPI] {data_str} -> {chegada.strftime('%d/%m/%Y')} | Futuro: {chegada >= hoje} | Semana: {inicio_semana <= chegada <= fim_semana} | Mês: {primeiro_dia_mes <= chegada <= ultimo_dia_mes}")
                
                if pd.notnull(chegada):
                    # Lógica para MÊS
                    if primeiro_dia_mes <= chegada <= ultimo_dia_mes:
                        if chegada >= hoje:
                            # CHEGANDO este mês (futuro)
                            chegando_mes += 1
                            chegando_mes_custo += custo
                        else:
                            # CHEGOU este mês (passado)
                            chegou_mes += 1
                            chegou_mes_custo += custo
                    
                    # Lógica para SEMANA
                    if inicio_semana <= chegada <= fim_semana:
                        if chegada >= hoje:
                            # CHEGANDO esta semana (futuro)
                            chegando_semana += 1
                            chegando_semana_custo += custo
                        else:
                            # CHEGOU esta semana (passado)
                            chegou_semana += 1
                            chegou_semana_custo += custo
            
            print(f"[DEBUG_KPI] Resultados - Chegando semana: {chegando_semana}, Chegou semana: {chegou_semana}")
            print(f"[DEBUG_KPI] Resultados - Chegando mês: {chegando_mes}, Chegou mês: {chegou_mes}")

        # Transit time médio
        transit_time = 0
        if 'data_embarque' in df.columns and 'data_chegada' in df.columns:
            datas_validas = df.dropna(subset=['data_embarque', 'data_chegada'])
            if not datas_validas.empty:
                datas_validas['embarque_dt'] = pd.to_datetime(datas_validas['data_embarque'], format='%d/%m/%Y', errors='coerce')
                datas_validas['chegada_dt'] = pd.to_datetime(datas_validas['data_chegada'], format='%d/%m/%Y', errors='coerce')
                datas_validas = datas_validas.dropna(subset=['embarque_dt', 'chegada_dt'])
                if not datas_validas.empty:
                    datas_validas['transit_days'] = (datas_validas['chegada_dt'] - datas_validas['embarque_dt']).dt.days
                    transit_time = datas_validas['transit_days'].mean()

        # Processos médios por mês/semana
        processos_mes = 0
        processos_semana = 0
        if 'data_abertura' in df.columns:
            datas = pd.to_datetime(df['data_abertura'], format='%d/%m/%Y', errors='coerce')
            datas_validas = datas.dropna()
            if not datas_validas.empty:
                # Calcular média mensal
                meses_unicos = datas_validas.dt.to_period('M').nunique()
                processos_mes = total_processos / meses_unicos if meses_unicos > 0 else 0
                
                # Calcular média semanal
                semanas_unicas = datas_validas.dt.to_period('W').nunique()
                processos_semana = total_processos / semanas_unicas if semanas_unicas > 0 else 0

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
            'chegou_mes': chegou_mes,
            'chegou_mes_custo': chegou_mes_custo,
            'chegou_semana': chegou_semana,
            'chegou_semana_custo': chegou_semana_custo,
            'transit_time_medio': transit_time,
            'processos_mes': processos_mes,
            'processos_semana': processos_semana
        }
        
        return jsonify({
            'success': True,
            'kpis': clean_data_for_json(kpis)
        })
        
    except Exception as e:
        print(f"[DASHBOARD_EXECUTIVO] Erro ao calcular KPIs: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'kpis': {}
        }), 500

@bp.route('/api/charts')
@login_required
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def dashboard_charts():
    """Gerar dados para os gráficos do dashboard executivo"""
    try:
        # Obter dados do cache
        user_data = session.get('user', {})
        user_id = user_data.get('id')
        
        data = data_cache.get_cache(user_id, 'dashboard_v2_data')
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Dados não encontrados. Recarregue a página.',
                'charts': {}
            })
        
        df = pd.DataFrame(data)
        
        # Gráfico Evolução Mensal
        monthly_chart = {'labels': [], 'datasets': []}
        if 'data_abertura' in df.columns and 'custo_total' in df.columns:
            df['data_abertura_dt'] = pd.to_datetime(df['data_abertura'], format='%d/%m/%Y', errors='coerce')
            df_mensal = df.dropna(subset=['data_abertura_dt'])
            df_mensal['mes_ano'] = df_mensal['data_abertura_dt'].dt.strftime('%m/%Y')
            
            grouped = df_mensal.groupby('mes_ano').agg({
                'ref_unique': 'count',
                'custo_total': 'sum'
            }).reset_index().sort_values('mes_ano')
            
            monthly_chart = {
                'labels': grouped['mes_ano'].tolist(),
                'datasets': [
                    {
                        'label': 'Quantidade de Processos',
                        'data': grouped['ref_unique'].tolist(),
                        'type': 'line',
                        'yAxisID': 'y1'
                    },
                    {
                        'label': 'Custo Total (R$)',
                        'data': grouped['custo_total'].tolist(),
                        'type': 'bar',
                        'yAxisID': 'y'
                    }
                ]
            }

        # Gráfico de Status do Processo
        status_chart = {'labels': [], 'data': []}
        if 'status_processo' in df.columns:
            status_counts = df['status_processo'].value_counts().head(10)
            status_chart = {
                'labels': status_counts.index.tolist(),
                'data': status_counts.values.tolist()
            }

        # Gráfico de Modal
        grouped_modal_chart = {'labels': [], 'datasets': []}
        if 'modal' in df.columns and 'custo_total' in df.columns:
            modal_grouped = df.groupby('modal').agg({
                'ref_unique': 'count',
                'custo_total': 'sum'
            }).reset_index()
            
            grouped_modal_chart = {
                'labels': modal_grouped['modal'].tolist(),
                'datasets': [
                    {
                        'label': 'Quantidade de Processos',
                        'data': modal_grouped['ref_unique'].tolist(),
                        'type': 'bar',
                        'backgroundColor': 'rgba(54, 162, 235, 0.6)',
                        'borderColor': 'rgba(54, 162, 235, 1)',
                        'yAxisID': 'y1'
                    },
                    {
                        'label': 'Custo Total (R$)',
                        'data': modal_grouped['custo_total'].tolist(),
                        'type': 'bar',
                        'backgroundColor': 'rgba(255, 99, 132, 0.6)',
                        'borderColor': 'rgba(255, 99, 132, 1)',
                        'yAxisID': 'y'
                    }
                ]
            }

        # Gráfico URF
        urf_chart = {'labels': [], 'data': []}
        if 'urf_entrada_normalizado' in df.columns:
            urf_counts = df['urf_entrada_normalizado'].value_counts().head(10)
            urf_chart = {
                'labels': urf_counts.index.tolist(),
                'data': urf_counts.values.tolist()
            }

        # Gráfico Materiais
        material_chart = {'labels': [], 'data': []}
        if 'mercadoria' in df.columns:
            material_counts = df['mercadoria'].value_counts().head(10)
            material_chart = {
                'labels': material_counts.index.tolist(),
                'data': material_counts.values.tolist()
            }

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
        print(f"[DASHBOARD_EXECUTIVO] Erro ao gerar gráficos: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'charts': {}
        }), 500

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
        print(f"[DASHBOARD_EXECUTIVO] Erro ao gerar monthly_chart: {str(e)}")
        return jsonify({'success': False, 'error': str(e), 'data': {}}), 500

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
                'error': 'Dados não encontrados. Recarregue a página.',
                'operations': []
            })
        
        # Ordenar por data mais recente e limitar a 50 registros
        df = pd.DataFrame(data)
        
        if 'data_abertura' in df.columns:
            df['data_abertura_dt'] = pd.to_datetime(df['data_abertura'], format='%d/%m/%Y', errors='coerce')
            df_sorted = df.sort_values('data_abertura_dt', ascending=False).head(50)
        else:
            df_sorted = df.head(50)
        
        # Selecionar colunas relevantes para a tabela E modal
        relevant_columns = [
            # Colunas para a tabela
            'ref_unique', 'importador', 'data_abertura', 'exportador_fornecedor', 
            'modal', 'status_processo', 'custo_total', 'data_chegada',
            
            # Colunas adicionais para o modal
            'ref_importador', 'cnpj_importador', 'status_macro', 'data_embarque',
            'peso_bruto', 'urf_despacho', 'urf_despacho_normalizado', 'container',
            'transit_time_real', 'valor_cif_real', 'custo_frete_inter', 
            'custo_armazenagem', 'custo_honorarios', 'numero_di', 'data_registro',
            'canal', 'data_desembaraco'
        ]
        
        # Adicionar colunas normalizadas se disponíveis
        if 'mercadoria' in df_sorted.columns:
            relevant_columns.append('mercadoria')
        if 'urf_entrada_normalizado' in df_sorted.columns:
            relevant_columns.append('urf_entrada_normalizado')
        elif 'urf_entrada' in df_sorted.columns:
            relevant_columns.append('urf_entrada')
        
        available_columns = [col for col in relevant_columns if col in df_sorted.columns]
        print(f"[DASHBOARD_EXECUTIVO] Colunas disponíveis: {available_columns}")
        print(f"[DASHBOARD_EXECUTIVO] Colunas faltando: {set(relevant_columns) - set(available_columns)}")
        
        operations_data = df_sorted[available_columns].to_dict('records')
        
        # Debug: mostrar dados de uma operação de exemplo
        if operations_data:
            print(f"[DASHBOARD_EXECUTIVO] Exemplo de operação (keys): {list(operations_data[0].keys())}")
        
        return jsonify({
            'success': True,
            'operations': clean_data_for_json(operations_data)
        })
        
    except Exception as e:
        print(f"[DASHBOARD_EXECUTIVO] Erro ao obter operações recentes: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'operations': []
        }), 500
