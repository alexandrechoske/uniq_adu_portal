from flask import Blueprint, render_template, session, request, jsonify
from datetime import datetime, timedelta
from extensions import supabase, supabase_admin
from routes.auth import login_required, role_required
from routes.api import get_user_companies
from services.data_cache import DataCacheService
import pandas as pd
import numpy as np

# Instanciar o serviço de cache
data_cache = DataCacheService()

# Blueprint com configuração para templates e static locais
bp = Blueprint('dashboard_materiais', __name__, 
               url_prefix='/dashboard-materiais',
               template_folder='templates',
               static_folder='static',
               static_url_path='/dashboard-materiais/static')

def get_or_reload_cache(user_id, user_role):
    """Função helper para obter cache ou recarregar se não existir"""
    data = data_cache.get_cache(user_id, 'dashboard_v2_data')
    
    if not data:
        print(f"[DASHBOARD_MATERIAIS] Cache não encontrado para user_id: {user_id}, recarregando...")
        
        query = supabase_admin.table('vw_importacoes_6_meses').select('*')
        
        if user_role == 'cliente_unique':
            user_data = session.get('user', {})
            user_companies = get_user_companies(user_data)
            if user_companies:
                query = query.in_('cnpj_importador', user_companies)
        
        result = query.execute()
        
        if result.data:
            data = result.data
            data_cache.set_cache(user_id, 'dashboard_v2_data', data)
            print(f"[DASHBOARD_MATERIAIS] Cache recarregado: {len(data)} registros")
    
    return data

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

def filter_by_date_python(item_date, data_inicio, data_fim):
    """Filtrar data usando Python (formato brasileiro DD/MM/YYYY)"""
    try:
        if not item_date:
            return False
        
        # Converter data do item (DD/MM/YYYY para YYYY-MM-DD)
        if '/' in item_date:
            day, month, year = item_date.split('/')
            item_date_iso = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        else:
            item_date_iso = item_date
        
        # Converter para datetime
        item_dt = datetime.strptime(item_date_iso, '%Y-%m-%d')
        inicio_dt = datetime.strptime(data_inicio, '%Y-%m-%d')
        fim_dt = datetime.strptime(data_fim, '%Y-%m-%d')
        
        return inicio_dt <= item_dt <= fim_dt
    except Exception as e:
        print(f"[DASHBOARD_MATERIAIS] Erro ao filtrar data: {str(e)}")
        return False

def apply_filters(data):
    """Aplicar filtros aos dados baseado nos parâmetros da requisição"""
    try:
        # Obter filtros da requisição
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        material = request.args.get('material')
        cliente = request.args.get('cliente')
        modal = request.args.get('modal')
        canal = request.args.get('canal')
        
        filtered_data = data
        
        # Filtrar por data
        if data_inicio and data_fim:
            filtered_data = [item for item in filtered_data 
                           if filter_by_date_python(item.get('data_abertura'), data_inicio, data_fim)]
        
        # Filtrar por material
        if material:
            filtered_data = [item for item in filtered_data 
                           if material.lower() in item.get('mercadoria', '').lower()]
        
        # Filtrar por cliente
        if cliente:
            filtered_data = [item for item in filtered_data 
                           if cliente.lower() in item.get('importador', '').lower()]
        
        # Filtrar por modal
        if modal:
            filtered_data = [item for item in filtered_data 
                           if modal.lower() in item.get('modal', '').lower()]
        
        # Filtrar por canal
        if canal:
            filtered_data = [item for item in filtered_data 
                           if canal.lower() in item.get('canal', '').lower()]
        
        return filtered_data
        
    except Exception as e:
        print(f"[DASHBOARD_MATERIAIS] Erro ao aplicar filtros: {str(e)}")
        return data

@bp.route('/')
@login_required
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def index():
    """Página principal do Dashboard de Materiais"""
    return render_template('dashboard_materiais.html')

@bp.route('/api/kpis')
@login_required
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def materiais_kpis():
    """Calcular KPIs específicos de materiais"""
    try:
        # Obter dados do cache ou recarregar
        user_data = session.get('user', {})
        user_id = user_data.get('id')
        user_role = user_data.get('role')
        
        data = get_or_reload_cache(user_id, user_role)
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Dados não encontrados. Recarregue a página.',
                'kpis': {}
            })
        
        # Aplicar filtros se existirem
        filtered_data = apply_filters(data)
        df = pd.DataFrame(filtered_data)
        
        # Calcular KPIs específicos de materiais
        total_processos = len(df)
        
        # Materiais únicos (filtrar vazios e "não informado")
        materiais_unicos = set()
        valores_processos = []
        custos_processos = []
        
        for _, row in df.iterrows():
            mercadoria = str(row.get('mercadoria', '')).strip().lower()
            if mercadoria and mercadoria not in ['', 'não informado', 'nan', 'none']:
                materiais_unicos.add(mercadoria)
            
            valor_cif = row.get('valor_cif_usd', 0) or 0
            custo_total = row.get('custo_total', 0) or 0
            valores_processos.append(valor_cif)
            custos_processos.append(custo_total)
        
        total_materiais = len(materiais_unicos)
        valor_total = sum(valores_processos)
        custo_total = sum(custos_processos)
        ticket_medio = valor_total / total_processos if total_processos > 0 else 0
        
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
        
        # KPIs de processos a chegar este mês/semana e custos
        hoje = datetime.now()
        primeiro_dia_mes = hoje.replace(day=1)
        inicio_semana = hoje - timedelta(days=hoje.weekday())

        processos_mes = 0
        processos_semana = 0
        custo_total_mes = 0
        custo_total_semana = 0

        for _, row in df.iterrows():
            data_chegada_str = row.get('data_chegada')
            custo = row.get('custo_total', 0) or 0
            
            if data_chegada_str:
                try:
                    data_chegada = datetime.strptime(data_chegada_str, '%d/%m/%Y')
                    
                    # Verificar se chegada é neste mês
                    if data_chegada >= primeiro_dia_mes and data_chegada.month == hoje.month and data_chegada.year == hoje.year:
                        processos_mes += 1
                        custo_total_mes += custo
                    
                    # Verificar se chegada é nesta semana
                    if data_chegada >= inicio_semana and data_chegada <= hoje + timedelta(days=7):
                        processos_semana += 1
                        custo_total_semana += custo
                except:
                    continue

        kpis = {
            'total_processos': total_processos,
            'total_materiais': total_materiais,
            'valor_total': valor_total,
            'custo_total': custo_total,
            'ticket_medio': ticket_medio,
            'transit_time': transit_time,
            'total_processos_mes': processos_mes,
            'total_processos_semana': processos_semana,
            'custo_total_mes': custo_total_mes,
            'custo_total_semana': custo_total_semana
        }

        return jsonify({
            'success': True,
            'kpis': clean_data_for_json(kpis)
        })
        
    except Exception as e:
        print(f"[DASHBOARD_MATERIAIS] Erro ao calcular KPIs: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'kpis': {}
        }), 500

@bp.route('/api/top-materiais')
@login_required
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def api_top_materiais():
    """Top 10 materiais por quantidade"""
    try:
        # Obter dados do cache ou recarregar
        user_data = session.get('user', {})
        user_id = user_data.get('id')
        user_role = user_data.get('role')
        
        data = get_or_reload_cache(user_id, user_role)
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Dados não encontrados. Recarregue a página.',
                'data': []
            })
        
        # Aplicar filtros
        filtered_data = apply_filters(data)
        df = pd.DataFrame(filtered_data)
        
        if 'mercadoria' in df.columns:
            material_counts = df['mercadoria'].value_counts().head(10)
            result = {
                'labels': material_counts.index.tolist(),
                'data': material_counts.values.tolist()
            }
        else:
            result = {'labels': [], 'data': []}
        
        return jsonify({
            'success': True,
            'data': clean_data_for_json(result)
        })
        
    except Exception as e:
        print(f"[DASHBOARD_MATERIAIS] Erro ao obter top materiais: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': []
        }), 500

@bp.route('/api/evolucao-mensal')
@login_required
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def api_evolucao_mensal():
    """Evolução mensal dos top 3 materiais"""
    try:
        # Obter dados do cache ou recarregar
        user_data = session.get('user', {})
        user_id = user_data.get('id')
        user_role = user_data.get('role')
        
        data = get_or_reload_cache(user_id, user_role)
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Dados não encontrados. Recarregue a página.',
                'data': {}
            })
        
        # Aplicar filtros
        filtered_data = apply_filters(data)
        df = pd.DataFrame(filtered_data)
        
        if 'mercadoria' in df.columns and 'data_abertura' in df.columns:
            # Obter top 3 materiais
            top_materiais = df['mercadoria'].value_counts().head(3).index.tolist()
            
            # Converter data_abertura para datetime
            df['data_abertura_dt'] = pd.to_datetime(df['data_abertura'], format='%d/%m/%Y', errors='coerce')
            df['mes_ano'] = df['data_abertura_dt'].dt.strftime('%m/%Y')
            
            # Filtrar apenas top 3 materiais
            df_filtered = df[df['mercadoria'].isin(top_materiais)]
            
            # Agrupar por mês e material
            evolucao = df_filtered.groupby(['mes_ano', 'mercadoria']).size().reset_index(name='quantidade')
            
            # Preparar dados para o gráfico
            meses = sorted(evolucao['mes_ano'].unique())
            datasets = []
            
            for material in top_materiais:
                material_data = evolucao[evolucao['mercadoria'] == material]
                quantities = []
                for mes in meses:
                    qty = material_data[material_data['mes_ano'] == mes]['quantidade'].sum()
                    quantities.append(qty)
                
                datasets.append({
                    'label': material,
                    'data': quantities
                })
            
            result = {
                'labels': meses,
                'datasets': datasets
            }
        else:
            result = {'labels': [], 'datasets': []}
        
        return jsonify({
            'success': True,
            'data': clean_data_for_json(result)
        })
        
    except Exception as e:
        print(f"[DASHBOARD_MATERIAIS] Erro ao obter evolução mensal: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': {}
        }), 500

@bp.route('/api/modal-distribution')
@login_required
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def api_modal_distribution():
    """Distribuição por modal de transporte"""
    try:
        # Obter dados do cache ou recarregar
        user_data = session.get('user', {})
        user_id = user_data.get('id')
        user_role = user_data.get('role')
        
        data = get_or_reload_cache(user_id, user_role)
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Dados não encontrados. Recarregue a página.',
                'data': []
            })
        
        # Aplicar filtros
        filtered_data = apply_filters(data)
        df = pd.DataFrame(filtered_data)
        
        if 'modal' in df.columns:
            modal_counts = df['modal'].value_counts()
            result = {
                'labels': modal_counts.index.tolist(),
                'data': modal_counts.values.tolist()
            }
        else:
            result = {'labels': [], 'data': []}
        
        return jsonify({
            'success': True,
            'data': clean_data_for_json(result)
        })
        
    except Exception as e:
        print(f"[DASHBOARD_MATERIAIS] Erro ao obter distribuição modal: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': []
        }), 500

@bp.route('/api/canal-distribution')
@login_required
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def api_canal_distribution():
    """Distribuição por canal"""
    try:
        # Obter dados do cache ou recarregar
        user_data = session.get('user', {})
        user_id = user_data.get('id')
        user_role = user_data.get('role')
        
        data = get_or_reload_cache(user_id, user_role)
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Dados não encontrados. Recarregue a página.',
                'data': []
            })
        
        # Aplicar filtros
        filtered_data = apply_filters(data)
        df = pd.DataFrame(filtered_data)
        
        if 'canal' in df.columns:
            canal_counts = df['canal'].value_counts()
            result = {
                'labels': canal_counts.index.tolist(),
                'data': canal_counts.values.tolist()
            }
        else:
            result = {'labels': [], 'data': []}
        
        return jsonify({
            'success': True,
            'data': clean_data_for_json(result)
        })
        
    except Exception as e:
        print(f"[DASHBOARD_MATERIAIS] Erro ao obter distribuição por canal: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': []
        }), 500

@bp.route('/api/transit-time-por-material')
@login_required
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def api_transit_time_por_material():
    """Transit time por material"""
    try:
        # Obter dados do cache ou recarregar
        user_data = session.get('user', {})
        user_id = user_data.get('id')
        user_role = user_data.get('role')
        
        data = get_or_reload_cache(user_id, user_role)
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Dados não encontrados. Recarregue a página.',
                'data': {}
            })
        
        # Aplicar filtros
        filtered_data = apply_filters(data)
        df = pd.DataFrame(filtered_data)
        
        result = {'labels': [], 'data': []}
        
        if 'data_embarque' in df.columns and 'data_chegada' in df.columns and 'mercadoria' in df.columns:
            # Calcular transit time
            df['embarque_dt'] = pd.to_datetime(df['data_embarque'], format='%d/%m/%Y', errors='coerce')
            df['chegada_dt'] = pd.to_datetime(df['data_chegada'], format='%d/%m/%Y', errors='coerce')
            df_valido = df.dropna(subset=['embarque_dt', 'chegada_dt', 'mercadoria'])
            
            if not df_valido.empty:
                df_valido['transit_days'] = (df_valido['chegada_dt'] - df_valido['embarque_dt']).dt.days
                
                # Agrupar por material e calcular média
                transit_por_material = df_valido.groupby('mercadoria')['transit_days'].mean().sort_values(ascending=False).head(10)
                
                result = {
                    'labels': transit_por_material.index.tolist(),
                    'data': transit_por_material.values.tolist()
                }
        
        return jsonify({
            'success': True,
            'data': clean_data_for_json(result)
        })
        
    except Exception as e:
        print(f"[DASHBOARD_MATERIAIS] Erro ao obter transit time por material: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': {}
        }), 500

@bp.route('/api/tabela-materiais')
@login_required
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def api_tabela_materiais():
    """Tabela de materiais com ícone, nome, valor total, quantidade de processos e próxima chegada"""
    try:
        # Obter dados do cache ou recarregar
        user_data = session.get('user', {})
        user_id = user_data.get('id')
        user_role = user_data.get('role')
        
        data = get_or_reload_cache(user_id, user_role)
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Dados não encontrados. Recarregue a página.',
                'data': []
            })
        
        # Aplicar filtros
        filtered_data = apply_filters(data)
        df = pd.DataFrame(filtered_data)
        
        if 'mercadoria' in df.columns:
            # Agrupar por material
            materiais_grouped = df.groupby('mercadoria').agg({
                'custo_total': 'sum',
                'ref_unique': 'count',
                'data_chegada': lambda x: x.dropna().min() if not x.dropna().empty else None
            }).reset_index()
            
            materiais_grouped.columns = ['material', 'custo_total', 'qtd_processos', 'proxima_chegada']
            materiais_grouped = materiais_grouped.sort_values('custo_total', ascending=False).head(15)
            
            result = materiais_grouped.to_dict('records')
        else:
            result = []
        
        return jsonify({
            'success': True,
            'data': clean_data_for_json(result)
        })
        
    except Exception as e:
        print(f"[DASHBOARD_MATERIAIS] Erro ao obter tabela de materiais: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': []
        }), 500

@bp.route('/api/detalhamento-processos')
@login_required
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def api_detalhamento_processos():
    """Detalhamento dos processos para tabela"""
    try:
        # Obter dados do cache ou recarregar
        user_data = session.get('user', {})
        user_id = user_data.get('id')
        user_role = user_data.get('role')
        
        data = get_or_reload_cache(user_id, user_role)
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Dados não encontrados. Recarregue a página.',
                'data': []
            })
        
        # Aplicar filtros
        filtered_data = apply_filters(data)
        
        # Selecionar colunas relevantes
        relevant_columns = [
            'data_abertura', 'ref_unique', 'importador', 'mercadoria', 
            'data_embarque', 'data_chegada', 'status_processo', 'canal', 'custo_total'
        ]
        
        # Filtrar apenas as colunas que existem
        if filtered_data:
            available_columns = [col for col in relevant_columns if col in filtered_data[0].keys()]
            result = []
            for item in filtered_data:
                filtered_item = {col: item.get(col) for col in available_columns}
                result.append(filtered_item)
        else:
            result = []
        
        return jsonify({
            'success': True,
            'data': clean_data_for_json(result)
        })
        
    except Exception as e:
        print(f"[DASHBOARD_MATERIAIS] Erro ao obter detalhamento de processos: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': []
        }), 500

@bp.route('/api/filter-options')
@login_required
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def api_filter_options():
    """Obter opções para filtros"""
    try:
        # Obter dados do cache ou recarregar
        user_data = session.get('user', {})
        user_id = user_data.get('id')
        user_role = user_data.get('role')
        
        data = get_or_reload_cache(user_id, user_role)
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Dados não encontrados. Recarregue a página.',
                'options': {}
            })
        
        df = pd.DataFrame(data)
        
        # Extrair opções únicas para cada filtro
        materiais = sorted(df['mercadoria'].dropna().unique().tolist()) if 'mercadoria' in df.columns else []
        clientes = sorted(df['importador'].dropna().unique().tolist()) if 'importador' in df.columns else []
        modais = sorted(df['modal'].dropna().unique().tolist()) if 'modal' in df.columns else []
        canais = sorted(df['canal'].dropna().unique().tolist()) if 'canal' in df.columns else []
        
        options = {
            'materiais': materiais,
            'clientes': clientes,
            'modais': modais,
            'canais': canais
        }
        
        return jsonify({
            'success': True,
            'options': options
        })
        
    except Exception as e:
        print(f"[DASHBOARD_MATERIAIS] Erro ao obter opções de filtro: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'options': {}
        }), 500
