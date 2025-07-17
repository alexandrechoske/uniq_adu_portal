from flask import Blueprint, render_template, session, request, jsonify
from datetime import datetime, timedelta
from extensions import supabase, supabase_admin
from routes.auth import login_required, role_required
from routes.api import get_user_companies
from services.data_cache import DataCacheService
import pandas as pd
import numpy as np
import pandas as pd
import numpy as np

data_cache = DataCacheService()

bp = Blueprint('materiais_v2', __name__, url_prefix='/materiais-v2')

def get_or_reload_cache(user_id, user_role):
    """Função helper para obter cache ou recarregar se não existir"""
    data = data_cache.get_cache(user_id, 'dashboard_v2_data')
    
    if not data:
        print(f"[MATERIAIS_V2] Cache não encontrado para user_id: {user_id}, recarregando...")
        
        from extensions import supabase_admin
        from routes.api import get_user_companies
        
        query = supabase_admin.table('vw_importacoes_6_meses').select('*')
        
        if user_role == 'cliente_unique':
            # Obter dados do usuário da sessão para passar para get_user_companies
            user_data = session.get('user', {})
            user_companies = get_user_companies(user_data)
            if user_companies:
                query = query.in_('cnpj_importador', user_companies)
        
        result = query.execute()
        
        if result.data:
            data = result.data
            data_cache.set_cache(user_id, 'dashboard_v2_data', data)
            print(f"[MATERIAIS_V2] Cache recarregado: {len(data)} registros")
    
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
        print(f"[MATERIAIS_V2] Erro ao filtrar data: {str(e)}")
        return False

@bp.route('/api/materiais-kpis')
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
            
            # Valores CIF
            if 'valor_cif_real' in row and pd.notna(row['valor_cif_real']):
                valores_processos.append(float(row['valor_cif_real']))
            
            # Custos/Despesas
            if 'custo_total' in row and pd.notna(row['custo_total']):
                custos_processos.append(float(row['custo_total']))
        
        total_materiais = len(materiais_unicos)
        valor_total = sum(valores_processos)
        custo_total = sum(custos_processos)
        ticket_medio = valor_total / total_processos if total_processos > 0 else 0
        
        # Transit time médio (se disponível)
        transit_time = 0
        if 'data_embarque' in df.columns and 'data_chegada' in df.columns:
            transit_times = []
            for _, row in df.iterrows():
                try:
                    if pd.notna(row['data_embarque']) and pd.notna(row['data_chegada']):
                        embarque = pd.to_datetime(row['data_embarque'], format='%d/%m/%Y', errors='coerce')
                        chegada = pd.to_datetime(row['data_chegada'], format='%d/%m/%Y', errors='coerce')
                        if pd.notna(embarque) and pd.notna(chegada):
                            transit_times.append((chegada - embarque).days)
                except:
                    continue
            
            if transit_times:
                transit_time = sum(transit_times) / len(transit_times)
        
        # KPIs de processos a chegar este mês/semana e custos
        hoje = datetime.now()
        primeiro_dia_mes = hoje.replace(day=1)
        inicio_semana = hoje - timedelta(days=hoje.weekday())

        processos_mes = 0
        processos_semana = 0
        custo_total_mes = 0
        custo_total_semana = 0

        for _, row in df.iterrows():
            # Data chegada (DD/MM/YYYY)
            data_chegada = row.get('data_chegada', '')
            custo = float(row.get('custo_total', 0)) if pd.notna(row.get('custo_total', 0)) else 0
            try:
                if data_chegada and '/' in data_chegada:
                    chegada_dt = datetime.strptime(data_chegada, '%d/%m/%Y')
                    if chegada_dt >= primeiro_dia_mes and chegada_dt <= hoje:
                        processos_mes += 1
                        custo_total_mes += custo
                    if chegada_dt >= inicio_semana and chegada_dt <= hoje:
                        processos_semana += 1
                        custo_total_semana += custo
            except Exception as e:
                continue

        kpis = {
            'total_processos': total_processos,
            'total_materiais': total_materiais,
            'valor_total': valor_total,
            'custo_total': custo_total,
            'ticket_medio': ticket_medio,
            'transit_time': transit_time,
            # Novos KPIs
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
        print(f"[MATERIAIS_V2] Erro ao calcular KPIs: {str(e)}")
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
                'error': 'Dados não encontrados.',
                'data': []
            })
        
        # Aplicar filtros
        filtered_data = apply_filters(data)
        df = pd.DataFrame(filtered_data)
        
        if 'mercadoria' in df.columns:
            # Limpar e agrupar materiais
            df['mercadoria_clean'] = df['mercadoria'].astype(str).str.strip().str.lower()
            df_filtered = df[~df['mercadoria_clean'].isin(['', 'não informado', 'nan', 'none'])]
            
            top_materiais = df_filtered['mercadoria_clean'].value_counts().head(10)
            
            result = {
                'labels': top_materiais.index.tolist(),
                'values': top_materiais.values.tolist()
            }
        else:
            result = {'labels': [], 'values': []}
        
        return jsonify({
            'success': True,
            'data': clean_data_for_json(result)
        })
        
    except Exception as e:
        print(f"[MATERIAIS_V2] Erro ao obter top materiais: {str(e)}")
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
                'error': 'Dados não encontrados.',
                'data': []
            })
        
        # Aplicar filtros
        filtered_data = apply_filters(data)
        df = pd.DataFrame(filtered_data)
        
        if 'mercadoria' in df.columns and 'data_abertura' in df.columns:
            # Obter top 3 materiais
            df['mercadoria_clean'] = df['mercadoria'].astype(str).str.strip().str.lower()
            df_filtered = df[~df['mercadoria_clean'].isin(['', 'não informado', 'nan', 'none'])]
            
            top_3_materiais = df_filtered['mercadoria_clean'].value_counts().head(3).index.tolist()
            
            # Criar coluna mês/ano
            df_filtered['mes_ano'] = df_filtered['data_abertura'].apply(
                lambda x: x.split('/')[1] + '/' + x.split('/')[2] if '/' in str(x) else ''
            )
            
            result = []
            for material in top_3_materiais:
                material_data = df_filtered[df_filtered['mercadoria_clean'] == material]
                monthly_counts = material_data.groupby('mes_ano').size().reset_index(name='count')
                
                result.append({
                    'material': material,
                    'periods': monthly_counts['mes_ano'].tolist(),
                    'values': monthly_counts['count'].tolist()
                })
        else:
            result = []
        
        return jsonify({
            'success': True,
            'data': clean_data_for_json(result)
        })
        
    except Exception as e:
        print(f"[MATERIAIS_V2] Erro ao obter evolução mensal: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': []
        }), 500

@bp.route('/api/modal-distribution')
@login_required
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def api_modal_distribution():
    """Distribuição por modal de transporte"""
    try:
        # Debug: imprimir parâmetros recebidos
        print(f"[MATERIAIS_V2] Modal Distribution - Parâmetros recebidos: {dict(request.args)}")
        
        # Obter dados do cache ou recarregar
        user_data = session.get('user', {})
        user_id = user_data.get('id')
        user_role = user_data.get('role')
        
        data = get_or_reload_cache(user_id, user_role)
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Dados não encontrados.',
                'data': []
            })
        
        print(f"[MATERIAIS_V2] Modal Distribution - Total de registros no cache: {len(data)}")
        
        # Aplicar filtros
        filtered_data = apply_filters(data)
        df = pd.DataFrame(filtered_data)
        
        print(f"[MATERIAIS_V2] Modal Distribution - Registros após filtros: {len(filtered_data)}")
        
        if 'modal' in df.columns:
            modal_counts = df['modal'].value_counts()
            
            # Calcular custo total por modal
            modal_custos = {}
            if 'custo_total' in df.columns:
                modal_custos = df.groupby('modal')['custo_total'].sum().to_dict()
            
            print(f"[MATERIAIS_V2] Modal Distribution - Distribuição: {modal_counts.to_dict()}")
            print(f"[MATERIAIS_V2] Modal Distribution - Custos por modal: {modal_custos}")
            
            result = {
                'labels': modal_counts.index.tolist(),
                'values': modal_counts.values.tolist(),
                'custos': [modal_custos.get(modal, 0) for modal in modal_counts.index.tolist()]
            }
        else:
            result = {'labels': [], 'values': [], 'custos': []}
        
        print(f"[MATERIAIS_V2] Modal Distribution - Resultado final: {result}")
        
        return jsonify({
            'success': True,
            'data': clean_data_for_json(result)
        })
        
    except Exception as e:
        print(f"[MATERIAIS_V2] Erro ao obter distribuição modal: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': []
        }), 500

@bp.route('/api/bypass-modal-distribution')
def api_bypass_modal_distribution():
    """Distribuição por modal de transporte - SEM autenticação para testes"""
    try:
        # Debug: imprimir parâmetros recebidos
        print(f"[MATERIAIS_V2] Bypass Modal Distribution - Parâmetros recebidos: {dict(request.args)}")
        
        # Obter dados direto do Supabase para teste
        from extensions import supabase_admin
        
        # Obter filtros da requisição
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        
        # Query base - pegar todos os dados primeiro
        query = supabase_admin.table('vw_importacoes_6_meses').select('*')
        
        # Não aplicar filtros de data no Supabase, pois o formato é DD/MM/YYYY
        # Vamos filtrar em Python depois
        
        result = query.limit(2000).execute()
        data = result.data if result.data else []
        
        print(f"[MATERIAIS_V2] Bypass Modal Distribution - Total de registros: {len(data)}")
        
        # Aplicar filtros de data em Python se fornecidos
        if data_inicio and data_fim:
            filtered_data = []
            for item in data:
                if filter_by_date_python(item.get('data_abertura', ''), data_inicio, data_fim):
                    filtered_data.append(item)
            data = filtered_data
            print(f"[MATERIAIS_V2] Bypass Modal Distribution - Após filtro de data: {len(data)} registros")
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Nenhum dado encontrado.',
                'data': {'labels': [], 'values': [], 'custos': []}
            })
        
        df = pd.DataFrame(data)
        
        if 'modal' in df.columns:
            modal_counts = df['modal'].value_counts()
            
            # Calcular custo total por modal
            modal_custos = {}
            if 'custo_total' in df.columns:
                modal_custos = df.groupby('modal')['custo_total'].sum().to_dict()
            
            print(f"[MATERIAIS_V2] Bypass Modal Distribution - Distribuição: {modal_counts.to_dict()}")
            print(f"[MATERIAIS_V2] Bypass Modal Distribution - Custos por modal: {modal_custos}")
            
            result = {
                'labels': modal_counts.index.tolist(),
                'values': modal_counts.values.tolist(),
                'custos': [modal_custos.get(modal, 0) for modal in modal_counts.index.tolist()]
            }
        else:
            result = {'labels': [], 'values': [], 'custos': []}
        
        print(f"[MATERIAIS_V2] Bypass Modal Distribution - Resultado final: {result}")
        
        return jsonify({
            'success': True,
            'data': clean_data_for_json(result)
        })
        
    except Exception as e:
        print(f"[MATERIAIS_V2] Erro ao obter distribuição modal bypass: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': {'labels': [], 'values': [], 'custos': []}
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
                'error': 'Dados não encontrados.',
                'data': []
            })
        
        # Aplicar filtros
        filtered_data = apply_filters(data)
        df = pd.DataFrame(filtered_data)
        
        if 'canal' in df.columns:
            canal_counts = df['canal'].value_counts()
            
            result = {
                'labels': canal_counts.index.tolist(),
                'values': canal_counts.values.tolist()
            }
        else:
            result = {'labels': [], 'values': []}
        
        return jsonify({
            'success': True,
            'data': clean_data_for_json(result)
        })
        
    except Exception as e:
        print(f"[MATERIAIS_V2] Erro ao obter distribuição canal: {str(e)}")
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
                'error': 'Dados não encontrados.',
                'data': []
            })
        
        # Aplicar filtros
        filtered_data = apply_filters(data)
        df = pd.DataFrame(filtered_data)
        
        if 'mercadoria' in df.columns and 'data_embarque' in df.columns and 'data_chegada' in df.columns:
            # Calcular transit time por material
            transit_times = []
            
            for _, row in df.iterrows():
                try:
                    mercadoria = str(row.get('mercadoria', '')).strip().lower()
                    if not mercadoria or mercadoria in ['', 'não informado', 'nan', 'none']:
                        continue
                    
                    if pd.notna(row['data_embarque']) and pd.notna(row['data_chegada']):
                        embarque = pd.to_datetime(row['data_embarque'], format='%d/%m/%Y', errors='coerce')
                        chegada = pd.to_datetime(row['data_chegada'], format='%d/%m/%Y', errors='coerce')
                        
                        if pd.notna(embarque) and pd.notna(chegada):
                            transit_time = (chegada - embarque).days
                            transit_times.append({
                                'material': mercadoria,
                                'transit_time': transit_time
                            })
                except:
                    continue
            
            if transit_times:
                transit_df = pd.DataFrame(transit_times)
                avg_transit = transit_df.groupby('material')['transit_time'].mean().sort_values(ascending=False).head(10)
                
                result = {
                    'labels': avg_transit.index.tolist(),
                    'values': avg_transit.values.tolist()
                }
            else:
                result = {'labels': [], 'values': []}
        else:
            result = {'labels': [], 'values': []}
        
        return jsonify({
            'success': True,
            'data': clean_data_for_json(result)
        })
        
    except Exception as e:
        print(f"[MATERIAIS_V2] Erro ao obter transit time: {str(e)}")
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
                'error': 'Dados não encontrados.',
                'data': []
            })
        
        # Aplicar filtros
        filtered_data = apply_filters(data)
        
        # Selecionar colunas relevantes
        relevant_columns = [
            'ref_unique', 'importador', 'data_abertura', 'mercadoria', 'modal',
            'valor_cif_real', 'custo_total', 'status_processo', 'urf_entrada'
        ]
        
        df = pd.DataFrame(filtered_data)
        available_columns = [col for col in relevant_columns if col in df.columns]
        
        if available_columns:
            result_data = df[available_columns].head(100).to_dict('records')
        else:
            result_data = filtered_data[:100]
        
        return jsonify({
            'success': True,
            'data': clean_data_for_json(result_data),
            'total': len(filtered_data)
        })
        
    except Exception as e:
        print(f"[MATERIAIS_V2] Erro ao obter detalhamento: {str(e)}")
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
                'error': 'Dados não encontrados.',
                'options': {}
            })
        
        df = pd.DataFrame(data)
        
        options = {}
        
        # Materiais
        if 'mercadoria' in df.columns:
            materiais = df['mercadoria'].dropna().unique()
            options['materiais'] = [mat for mat in materiais if str(mat).strip() not in ['', 'não informado']]
        
        # Clientes
        if 'importador' in df.columns:
            clientes = df['importador'].dropna().unique()
            options['clientes'] = [cli for cli in clientes if str(cli).strip() not in ['', 'não informado']]
        
        # Modais
        if 'modal' in df.columns:
            modais = df['modal'].dropna().unique()
            options['modais'] = modais.tolist()
        
        # Canais
        if 'canal' in df.columns:
            canais = df['canal'].dropna().unique()
            options['canais'] = canais.tolist()
        
        return jsonify({
            'success': True,
            'options': options
        })
        
    except Exception as e:
        print(f"[MATERIAIS_V2] Erro ao obter opções de filtro: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'options': {}
        }), 500

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
            filtered_data = [
                item for item in filtered_data
                if filter_by_date_python(item.get('data_abertura', ''), data_inicio, data_fim)
            ]
        
        # Filtrar por material
        if material:
            filtered_data = [
                item for item in filtered_data
                if material.lower() in str(item.get('mercadoria', '')).lower()
            ]
        
        # Filtrar por cliente
        if cliente:
            filtered_data = [
                item for item in filtered_data
                if cliente.lower() in str(item.get('importador', '')).lower()
            ]
        
        # Filtrar por modal
        if modal:
            filtered_data = [
                item for item in filtered_data
                if item.get('modal') == modal
            ]
        
        # Filtrar por canal
        if canal:
            filtered_data = [
                item for item in filtered_data
                if item.get('canal') == canal
            ]
        
        return filtered_data
        
    except Exception as e:
        print(f"[MATERIAIS_V2] Erro ao aplicar filtros: {str(e)}")
        return data
