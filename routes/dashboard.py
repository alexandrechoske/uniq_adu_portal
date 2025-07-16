from flask import Blueprint, render_template, session, jsonify
from extensions import supabase, supabase_admin
from routes.auth import login_required, role_required
from routes.api import get_user_companies
from permissions import check_permission
from services.data_cache import data_cache
import pandas as pd
from datetime import datetime, timedelta
import numpy as np

bp = Blueprint('dashboard', __name__)

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
    """Página principal do dashboard"""
    return render_template('dashboard/index_simple.html')

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
@bp.route('/api/dashboard-data')
@check_permission()
def dashboard_data_api(permissions=None):
    """API endpoint para carregamento de dados do dashboard - Cache First Architecture"""
    try:
        # Obter dados do usuário para acessar o cache do servidor
        user_data = session.get('user', {})
        user_id = user_data.get('id')
        
        if not user_id:
            return jsonify({'success': False, 'error': 'Usuário não identificado'}), 401
        
        # Verificar cache do servidor primeiro
        cached_data = data_cache.get_cache(user_id, 'raw_data')
        
        
        if cached_data and isinstance(cached_data, list) and len(cached_data) > 0:
            
            # Calcular KPIs a partir do cache
            df = pd.DataFrame(cached_data)
            
            if not df.empty:
                # Se usuário for cliente_unique, normalizar e filtrar apenas suas empresas
                user_data = session.get('user', {})
                if user_data.get('role') == 'cliente_unique':
                    companies = user_data.get('user_companies', [])
                    # Normalizar cnpj_importador no DataFrame para dígitos puros
                    df['cnpj_importador'] = (
                        df['cnpj_importador']
                        .astype(str)
                        .str.replace(r'\D', '', regex=True)
                    )
                    if companies:
                        df = df[df['cnpj_importador'].isin(companies)]
                
                # Preparar dados para análise
                df['data_abertura'] = pd.to_datetime(df['data_abertura'], format='%d/%m/%Y', errors='coerce')
                df['valor_total'] = pd.to_numeric(df.get('custo_total', 0), errors='coerce').fillna(0)
                
                # Filtrar último mês
                hoje = datetime.now()
                inicio_mes = hoje.replace(day=1)
                inicio_mes_anterior = (inicio_mes - timedelta(days=1)).replace(day=1)
                
                df_mes_atual = df[df['data_abertura'] >= inicio_mes]
                df_mes_anterior = df[(df['data_abertura'] >= inicio_mes_anterior) & (df['data_abertura'] < inicio_mes)]
                
                # KPIs calculados do cache
                total_processos = len(df)
                processos_mes_atual = len(df_mes_atual)
                processos_mes_anterior = len(df_mes_anterior)
                valor_total = df['valor_total'].sum()
                valor_mes_atual = df_mes_atual['valor_total'].sum()
                valor_mes_anterior = df_mes_anterior['valor_total'].sum()
                
                # Taxa de crescimento
                if processos_mes_anterior > 0:
                    taxa_crescimento = ((processos_mes_atual - processos_mes_anterior) / processos_mes_anterior) * 100
                else:
                    taxa_crescimento = 0
                
                # Contagem por modal
                modal_counts = df['modal'].value_counts()
                
                # Garantir que todos os valores são números válidos
                total_processos = int(total_processos) if not pd.isna(total_processos) else 0
                valor_total = float(valor_total) if not pd.isna(valor_total) else 0.0
                valor_mes_atual = float(valor_mes_atual) if not pd.isna(valor_mes_atual) else 0.0
                
                kpis = {
                    'total_processos': total_processos,
                    'total_despesas': valor_total,
                    'modal_aereo': int(modal_counts.get('AEREA', 0)),
                    'modal_maritimo': int(modal_counts.get('MARITIMA', 0)),
                    'em_transito': int(len(df[df.get('status_processo', '') == 'Em andamento'])),
                    'di_registrada': int(len(df[df.get('status_processo', '') == 'Finalizada'])),
                    'despesa_media_por_processo': valor_total / total_processos if total_processos > 0 else 0.0,
                    'despesa_mes_atual': valor_mes_atual
                }
                
                # Gráficos baseados no cache
                charts = {}
                
                # Evolução Mensal do cache
                df_valid_dates = df.dropna(subset=['data_abertura'])
                if not df_valid_dates.empty:
                    df_monthly = df_valid_dates.groupby(df_valid_dates['data_abertura'].dt.to_period('M')).agg({
                        'id': 'count',
                        'valor_total': 'sum'
                    }).reset_index()
                    
                    charts['monthly'] = {
                        'periods': [str(p) for p in df_monthly['data_abertura']],
                        'processes': [int(x) if not pd.isna(x) else 0 for x in df_monthly['id'].tolist()],
                        'values': [float(x) if not pd.isna(x) else 0.0 for x in df_monthly['valor_total'].tolist()]
                    }
                    
                    print(f"[DASHBOARD] Monthly chart data: {len(charts['monthly']['periods'])} periods")
                else:
                    charts['monthly'] = {'periods': [], 'processes': [], 'values': []}
                
                # Evolução Semanal do cache
                if not df_valid_dates.empty:
                    df_weekly = df_valid_dates.groupby(df_valid_dates['data_abertura'].dt.to_period('W')).agg({
                        'id': 'count',
                        'valor_total': 'sum'
                    }).reset_index().tail(12)  # Últimas 12 semanas
                    
                    charts['weekly'] = {
                        'periods': [str(p) for p in df_weekly['data_abertura']],
                        'processes': [int(x) if not pd.isna(x) else 0 for x in df_weekly['id'].tolist()],
                        'values': [float(x) if not pd.isna(x) else 0.0 for x in df_weekly['valor_total'].tolist()]
                    }
                else:
                    charts['weekly'] = {'periods': [], 'processes': [], 'values': []}
                
                # Distribuição por Modal
                if 'modal' in df.columns:
                    modal_dist = df['modal'].value_counts().head(10)
                    print(f"[DASHBOARD] Modal distribution: {modal_dist.to_dict()}")
                    charts['canal'] = {
                        'labels': [str(x) for x in modal_dist.index.tolist()],
                        'values': [int(x) if not pd.isna(x) else 0 for x in modal_dist.values.tolist()]
                    }
                    print(f"[DASHBOARD] Canal chart data: {charts['canal']}")
                else:
                    charts['canal'] = {'labels': [], 'values': []}
                
                # Top URF Despacho
                if 'urf_entrada' in df.columns:
                    urf_dist = df['urf_entrada'].value_counts().head(10)
                    charts['urf'] = {
                        'labels': [str(x) for x in urf_dist.index.tolist()],
                        'values': [int(x) if not pd.isna(x) else 0 for x in urf_dist.values.tolist()]
                    }
                else:
                    charts['urf'] = {'labels': [], 'values': []}
                
                # Top Mercadoria
                if 'mercadoria' in df.columns:
                    # Filtrar materiais válidos (não nulos, não vazios, não "não informado")
                    df_materiais = df[df['mercadoria'].notna()]
                    df_materiais = df_materiais[df_materiais['mercadoria'].str.strip() != '']
                    df_materiais = df_materiais[~df_materiais['mercadoria'].str.lower().str.contains('não informado|nao informado|n/a|vazio', na=False)]
                    
                    if not df_materiais.empty:
                        merc_dist = df_materiais['mercadoria'].value_counts().head(10)
                        charts['top_material'] = {
                            'labels': [str(x) for x in merc_dist.index.tolist()],
                            'values': [int(x) if not pd.isna(x) else 0 for x in merc_dist.values.tolist()]
                        }
                    else:
                        charts['top_material'] = {'labels': [], 'values': []}
                else:
                    charts['top_material'] = {'labels': [], 'values': []}
                
                # Últimas Operações
                df_sorted = df.sort_values('data_abertura', ascending=False)
                # Limpar DataFrame antes de converter para dict
                # Permitir até 1000 registros para tabela (pode ser paginado no frontend)
                df_clean = df_sorted.head(1000).fillna('')  # Substituir NaN por string vazia
                
                # Mapear campos para compatibilidade com o frontend
                recent_ops_data = []
                for _, row in df_clean.iterrows():
                    op = {
                        'cliente': str(row.get('importador', '') or ''),
                        'numero_pedido': str(row.get('ref_importador', '') or row.get('numero_processo', '') or row.get('processo', '') or ''),
                        'data_embarque': str(row.get('data_abertura', '') or row.get('data_registro', '') or ''),
                        'local_embarque': str(row.get('urf_despacho', '') or row.get('urf_entrada', '') or row.get('urf_entrada_descricao', '') or ''),
                        'modal': str(row.get('modal', '') or row.get('modal_descricao', '') or ''),
                        'status': str(row.get('canal', '') or row.get('canal_di', '') or row.get('canal_descricao', '') or 'N/D'),
                        'mercadoria': str(row.get('material', '') or row.get('mercadoria', '') or ''),
                        'despesas': float(row.get('valor', 0) or row.get('valor_cif_real', 0) or row.get('valor_cif', 0) or 0) if pd.notna(row.get('valor', 0) or row.get('valor_cif_real', 0) or row.get('valor_cif', 0) or 0) else 0,
                        'recinto': '',  # Não disponível no cache
                        'data_chegada': ''  # Não disponível no cache
                    }
                    recent_ops_data.append(op)
                
                recent_ops = recent_ops_data
                
            else:
                print("[DASHBOARD] DataFrame vazio, não há dados para processar")
                # Cache vazio, usar valores padrão
                kpis = {
                    'total_processos': 0, 'total_despesas': 0, 'modal_aereo': 0,
                    'modal_maritimo': 0, 'em_transito': 0, 'di_registrada': 0,
                    'despesa_media_por_processo': 0, 'despesa_mes_atual': 0
                }
                charts = {
                    'monthly': {'periods': [], 'processes': [], 'values': []},
                    'weekly': {'periods': [], 'processes': [], 'values': []},
                    'canal': {'labels': [], 'values': []},
                    'urf': {'labels': [], 'values': []},
                    'top_material': {'labels': [], 'values': []}
                }
                recent_ops = []
                
        else:
            print("[DASHBOARD] Cache não disponível, tentando recarregar...")
            
            # Tentar recarregar o cache antes de usar fallback
            try:
                # usar data_cache global em vez de import interno
                cache_reloaded = data_cache.preload_user_data(user_id, user_data)
                if cache_reloaded:
                    cached_data = data_cache.get_cache(user_id, 'raw_data')
                    print(f"[DASHBOARD] Cache recarregado com sucesso: {len(cached_data) if cached_data else 0} registros")
                    
                    if cached_data and isinstance(cached_data, list) and len(cached_data) > 0:
                        # Processar cache recarregado igual ao processo normal do cache
                        df = pd.DataFrame(cached_data)
                        
                        if not df.empty:
                            # Mesma lógica de processamento do cache
                            df['data_abertura'] = pd.to_datetime(df['data_abertura'], format='%d/%m/%Y', errors='coerce')
                            df['valor_total'] = pd.to_numeric(df.get('custo_total', 0), errors='coerce').fillna(0)
                            
                            # KPIs básicos
                            kpis = {
                                'total_processos': len(df['ref_unique'].unique()),
                                'total_despesas': df['valor_total'].sum(),
                                'modal_aereo': len(df[df['modal'] == 'AEREA']) if 'modal' in df.columns else 0,
                                'modal_maritimo': len(df[df['modal'] == 'MARITIMA']) if 'modal' in df.columns else 0,
                                'em_transito': int(len(df[df.get('status_processo', '') == 'Em andamento'])),
                                'di_registrada': int(len(df[df.get('status_processo', '') == 'Finalizada'])),
                                'despesa_media_por_processo': df['valor_total'].mean() if len(df) > 0 else 0,
                                'despesa_mes_atual': 0
                            }
                            
                            # Gráficos do cache recarregado
                            charts = {}
                            
                            # Distribuição por Modal
                            if 'modal' in df.columns:
                                modal_dist = df['modal'].value_counts().head(10)
                                print(f"[DASHBOARD] Reloaded cache modal distribution: {modal_dist.to_dict()}")
                                charts['canal'] = {
                                    'labels': [str(x) for x in modal_dist.index.tolist()],
                                    'values': [int(x) if not pd.isna(x) else 0 for x in modal_dist.values.tolist()]
                                }
                                print(f"[DASHBOARD] Reloaded cache canal chart: {charts['canal']}")
                            else:
                                charts['canal'] = {'labels': [], 'values': []}
                            
                            # URF
                            if 'urf_entrada' in df.columns:
                                urf_dist = df['urf_entrada'].value_counts().head(10)
                                charts['urf'] = {
                                    'labels': [str(x) for x in urf_dist.index.tolist()],
                                    'values': [int(x) if not pd.isna(x) else 0 for x in urf_dist.values.tolist()]
                                }
                            else:
                                charts['urf'] = {'labels': [], 'values': []}
                            
                            # Materiais
                            if 'mercadoria' in df.columns:
                                df_materiais = df[df['mercadoria'].notna()]
                                df_materiais = df_materiais[df_materiais['mercadoria'].str.strip() != '']
                                df_materiais = df_materiais[~df_materiais['mercadoria'].str.lower().str.contains('não informado|nao informado|n/a|vazio', na=False)]
                                
                                if not df_materiais.empty:
                                    merc_dist = df_materiais['mercadoria'].value_counts().head(10)
                                    charts['top_material'] = {
                                        'labels': [str(x) for x in merc_dist.index.tolist()],
                                        'values': [int(x) if not pd.isna(x) else 0 for x in merc_dist.values.tolist()]
                                    }
                                else:
                                    charts['top_material'] = {'labels': [], 'values': []}
                            else:
                                charts['top_material'] = {'labels': [], 'values': []}
                            
                            # Outros gráficos vazios por simplicidade
                            charts['monthly'] = {'periods': [], 'processes': [], 'values': []}
                            charts['weekly'] = {'periods': [], 'processes': [], 'values': []}
                            
                            # Últimas operações
                            df_sorted = df.sort_values('data_abertura', ascending=False)
                            df_clean = df_sorted.head(1000).fillna('')
                            
                            recent_ops_data = []
                            for _, row in df_clean.iterrows():
                                op = {
                                    'cliente': str(row.get('importador', '') or ''),
                                    'numero_pedido': str(row.get('ref_importador', '') or row.get('numero_processo', '') or row.get('processo', '') or ''),
                                    'data_embarque': str(row.get('data_abertura', '') or row.get('data_registro', '') or ''),
                                    'local_embarque': str(row.get('urf_despacho', '') or row.get('urf_entrada', '') or row.get('urf_entrada_descricao', '') or ''),
                                    'modal': str(row.get('modal', '') or row.get('modal_descricao', '') or ''),
                                    'status': str(row.get('canal', '') or row.get('canal_di', '') or row.get('canal_descricao', '') or 'N/D'),
                                    'mercadoria': str(row.get('material', '') or row.get('mercadoria', '') or ''),
                                    'despesas': float(row.get('valor', 0) or row.get('valor_cif_real', 0) or row.get('valor_cif', 0) or 0) if pd.notna(row.get('valor', 0) or row.get('valor_cif_real', 0) or row.get('valor_cif', 0) or 0) else 0,
                                    'recinto': '',
                                    'data_chegada': ''
                                }
                                recent_ops_data.append(op)
                            recent_ops = recent_ops_data
                            
                            # Retornar dados do cache recarregado
                            dashboard_data = {
                                'kpis': clean_data_for_json(kpis),
                                'charts': clean_data_for_json(charts),
                                'recent_operations': clean_data_for_json(recent_ops)
                            }
                            
                            return jsonify({
                                'success': True,
                                'data': dashboard_data,
                                'source': 'cache_reloaded'
                            })
                        
            except Exception as reload_error:
                print(f"[DASHBOARD] Erro ao recarregar cache: {reload_error}")
            
            print("[DASHBOARD] Cache não disponível, buscando dados diretamente do Supabase")
            try:
                # Buscar dados diretamente da tabela principal usando supabase_admin
                # para evitar problemas com RLS
                user_role = user_data.get('role')
                print(f"[DASHBOARD] User role: {user_role}")
                
                query = supabase_admin.table('importacoes_processos_aberta').select('*').neq('status_processo', 'Despacho Cancelado')
                
                # Aplicar filtros baseados no role do usuário
                if user_role == 'cliente_unique':
                    # Obter lista de empresas do cliente via API utility
                    from routes.api import get_user_companies
                    user_companies = get_user_companies(user_data)
                    print(f"[DASHBOARD] Empresas do cliente: {user_companies}")
                    
                    if user_companies:
                        print(f"[DASHBOARD] Aplicando filtro IN para empresas: {user_companies}")
                        query = query.in_('cnpj_importador', user_companies)
                    else:
                        print("[DASHBOARD] Nenhuma empresa encontrada, aplicando filtro impossível")
                        query = query.eq('cnpj_importador', 'NENHUMA_EMPRESA_ENCONTRADA')
                else:
                    print("[DASHBOARD] Usuário não é cliente_unique, sem filtro de empresa")
                
                result = query.execute()
                fresh_data = result.data if result.data else []
                print(f"[DASHBOARD] Dados frescos obtidos: {len(fresh_data)} registros")
                
                # Log alguns CNPJs para debug
                if fresh_data:
                    cnpjs_encontrados = [r.get('cnpj_importador') for r in fresh_data[:5]]
                    print(f"[DASHBOARD] Primeiros 5 CNPJs encontrados: {cnpjs_encontrados}")
                else:
                    print("[DASHBOARD] Nenhum dado encontrado - possível problema de filtro")
                
                if fresh_data:
                    print(f"[DASHBOARD] Dados frescos obtidos: {len(fresh_data)} registros")
                    # Processar dados frescos igual ao cache
                    df = pd.DataFrame(fresh_data)
                    
                    # Preparar dados para análise
                    df['data_abertura'] = pd.to_datetime(df['data_abertura'], format='%d/%m/%Y', errors='coerce')
                    df['valor_total'] = pd.to_numeric(df.get('custo_total', 0), errors='coerce').fillna(0)
                    
                    # Calcular KPIs básicos
                    kpis = {
                        'total_processos': len(df),
                        'total_despesas': df['valor_total'].sum(),
                        'modal_aereo': len(df[df['modal'] == 'AÉREA']) if 'modal' in df.columns else 0,
                        'modal_maritimo': len(df[df['modal'] == 'MARÍTIMA']) if 'modal' in df.columns else 0,
                        'em_transito': 0,  # Simplificado
                        'di_registrada': 0,  # Simplificado 
                        'despesa_media_por_processo': df['valor_total'].mean() if len(df) > 0 else 0,
                        'despesa_mes_atual': 0  # Simplificado
                    }
                    
                    # Gráficos básicos
                    charts = {}
                    
                    # Distribuição por Modal
                    if 'modal' in df.columns:
                        modal_dist = df['modal'].value_counts().head(10)
                        print(f"[DASHBOARD] Fresh data modal distribution: {modal_dist.to_dict()}")
                        charts['canal'] = {
                            'labels': [str(x) for x in modal_dist.index.tolist()],
                            'values': [int(x) if not pd.isna(x) else 0 for x in modal_dist.values.tolist()]
                        }
                        print(f"[DASHBOARD] Fresh data canal chart: {charts['canal']}")
                    else:
                        charts['canal'] = {'labels': [], 'values': []}
                    
                    # URF
                    if 'urf_entrada' in df.columns:
                        urf_dist = df['urf_entrada'].value_counts().head(10)
                        charts['urf'] = {
                            'labels': [str(x) for x in urf_dist.index.tolist()],
                            'values': [int(x) if not pd.isna(x) else 0 for x in urf_dist.values.tolist()]
                        }
                    else:
                        charts['urf'] = {'labels': [], 'values': []}
                    
                    # Material (com filtro)
                    if 'mercadoria' in df.columns:
                        df_materiais = df[df['mercadoria'].notna()]
                        df_materiais = df_materiais[df_materiais['mercadoria'].str.strip() != '']
                        df_materiais = df_materiais[~df_materiais['mercadoria'].str.lower().str.contains('não informado|nao informado|n/a|vazio', na=False)]
                        
                        if not df_materiais.empty:
                            merc_dist = df_materiais['mercadoria'].value_counts().head(10)
                            charts['top_material'] = {
                                'labels': [str(x) for x in merc_dist.index.tolist()],
                                'values': [int(x) if not pd.isna(x) else 0 for x in merc_dist.values.tolist()]
                            }
                        else:
                            charts['top_material'] = {'labels': [], 'values': []}
                    else:
                        charts['top_material'] = {'labels': [], 'values': []}
                    
                    # Evolução mensal simplificada
                    charts['monthly'] = {'periods': [], 'processes': [], 'values': []}
                    charts['weekly'] = {'periods': [], 'processes': [], 'values': []}
                    
                    # Últimas operações
                    df_sorted = df.sort_values('data_abertura', ascending=False, na_position='last')
                    recent_ops_data = []
                    # Permitir até 1000 registros para tabela (pode ser paginado no frontend)
                    for _, row in df_sorted.head(1000).iterrows():
                        op = {
                            'cliente': str(row.get('importador', '') or ''),
                            'numero_pedido': str(row.get('ref_importador', '') or row.get('numero_processo', '') or row.get('processo', '') or ''),
                            'data_embarque': str(row.get('data_abertura', '') or row.get('data_registro', '') or ''),
                            'local_embarque': str(row.get('urf_despacho', '') or row.get('urf_entrada', '') or row.get('urf_entrada_descricao', '') or ''),
                            'modal': str(row.get('modal', '') or row.get('modal_descricao', '') or ''),
                            'status': str(row.get('canal', '') or row.get('canal_di', '') or row.get('canal_descricao', '') or 'N/D'),
                            'mercadoria': str(row.get('material', '') or row.get('mercadoria', '') or ''),
                            'despesas': float(row.get('valor', 0) or row.get('valor_cif_real', 0) or row.get('valor_cif', 0) or 0) if pd.notna(row.get('valor', 0) or row.get('valor_cif_real', 0) or row.get('valor_cif', 0) or 0) else 0,
                            'recinto': '',  # Não disponível no cache
                            'data_chegada': ''  # Não disponível no cache
                        }
                        recent_ops_data.append(op)
                    recent_ops = recent_ops_data
                    
                else:
                    print("[DASHBOARD] Nenhum dado encontrado na tabela")
                    # Usar fallback das views antigas
                    raise Exception("Sem dados frescos, usar views")
                    
            except Exception as e:
                print(f"[DASHBOARD] Erro ao buscar dados frescos ou fallback para views: {e}")
                # Usar fallback das views antigas
            # Fallback para views do banco (mantém funcionamento atual)
            try:
                stats = supabase.table('vw_dashboard_kpis').select('*').limit(1).execute().data
                stats = stats[0] if stats else {}
            except Exception as e:
                print(f"[DASHBOARD] Erro ao buscar KPIs: {e}")
                stats = {}
            
            kpis = {
                'total_processos': stats.get('total_processos', 0),
                'total_despesas': stats.get('total_despesas', 0),
                'modal_aereo': stats.get('modal_aereo', 0),
                'modal_maritimo': stats.get('modal_maritimo', 0),
                'em_transito': stats.get('em_transito', 0),
                'di_registrada': stats.get('di_registrada', 0),
                'despesa_media_por_processo': stats.get('despesa_media_por_processo', 0),
                'despesa_mes_atual': stats.get('despesa_mes_atual', 0)
            }
            
            # Gráficos das views
            charts = {}
            # Evolução Mensal
            try:
                mensal = supabase.table('vw_dashboard_evolucao_mensal')\
                    .select('periodo, total_processos, total_despesas')\
                    .order('periodo').execute().data or []
            except Exception as e:
                print(f"[DASHBOARD] Erro ao buscar evolução mensal: {e}")
                mensal = []
            charts['monthly'] = {
                'periods': [r.get('periodo') for r in mensal],
                'processes': [r.get('total_processos') for r in mensal],
                'values': [r.get('total_despesas') for r in mensal]
            }
            
            # Gráfico de Canal (Modal) a partir da tabela principal
            try:
                print("[DASHBOARD] Buscando dados de modal para gráfico de canal...")
                user_role = user_data.get('role')
                print(f"[DASHBOARD] User role para modal: {user_role}")
                
                modal_query = supabase_admin.table('importacoes_processos_aberta').select('modal').neq('status_processo', 'Despacho Cancelado')
                
                # Aplicar filtros baseados no role do usuário
                if user_role == 'cliente_unique':
                    user_companies = get_user_companies(user_data)
                    print(f"[DASHBOARD] Empresas para modal: {user_companies}")
                    
                    if user_companies:
                        modal_query = modal_query.in_('cnpj_importador', user_companies)
                    else:
                        modal_query = modal_query.eq('cnpj_importador', 'NENHUMA_EMPRESA_ENCONTRADA')
                
                modal_result = modal_query.execute()
                modal_data = modal_result.data if modal_result.data else []
                print(f"[DASHBOARD] Dados de modal obtidos: {len(modal_data)} registros")
                
                if modal_data:
                    # Processar dados de modal
                    df_modal = pd.DataFrame(modal_data)
                    modal_dist = df_modal['modal'].value_counts().head(10)
                    print(f"[DASHBOARD] Views modal distribution: {modal_dist.to_dict()}")
                    charts['canal'] = {
                        'labels': [str(x) for x in modal_dist.index.tolist()],
                        'values': [int(x) if not pd.isna(x) else 0 for x in modal_dist.values.tolist()]
                    }
                    print(f"[DASHBOARD] Views canal chart: {charts['canal']}")
                else:
                    charts['canal'] = {'labels': [], 'values': []}
                    print("[DASHBOARD] Nenhum dado de modal encontrado")
            except Exception as e:
                print(f"[DASHBOARD] Erro ao buscar dados de modal: {e}")
                charts['canal'] = {'labels': [], 'values': []}
            
            # Gráfico de URF a partir da tabela principal
            try:
                print("[DASHBOARD] Buscando dados de URF...")
                urf_query = supabase_admin.table('importacoes_processos_aberta').select('urf_entrada').neq('status_processo', 'Despacho Cancelado')
                
                # Aplicar filtros baseados no role do usuário
                if user_role == 'cliente_unique':
                    from routes.api import get_user_companies
                    user_companies = get_user_companies(user_data)
                    print(f"[DASHBOARD] Empresas para URF: {user_companies}")
                    
                    if user_companies:
                        urf_query = urf_query.in_('cnpj_importador', user_companies)
                    else:
                        urf_query = urf_query.eq('cnpj_importador', 'NENHUMA_EMPRESA_ENCONTRADA')
                
                urf_result = urf_query.execute()
                urf_data = urf_result.data if urf_result.data else []
                print(f"[DASHBOARD] Dados de URF obtidos: {len(urf_data)} registros")
                
                if urf_data:
                    df_urf = pd.DataFrame(urf_data)
                    df_urf = df_urf[df_urf['urf_entrada'].notna()]
                    urf_dist = df_urf['urf_entrada'].value_counts().head(10)
                    charts['urf'] = {
                        'labels': [str(x) for x in urf_dist.index.tolist()],
                        'values': [int(x) if not pd.isna(x) else 0 for x in urf_dist.values.tolist()]
                    }
                else:
                    charts['urf'] = {'labels': [], 'values': []}
            except Exception as e:
                print(f"[DASHBOARD] Erro ao buscar dados de URF: {e}")
                charts['urf'] = {'labels': [], 'values': []}
            
            # Gráfico de Materiais a partir da tabela principal
            try:
                print("[DASHBOARD] Buscando dados de materiais...")
                material_query = supabase_admin.table('importacoes_processos_aberta').select('mercadoria').neq('status_processo', 'Despacho Cancelado')
                
                # Aplicar filtros baseados no role do usuário
                if user_role == 'cliente_unique':
                    from routes.api import get_user_companies
                    user_companies = get_user_companies(user_data)
                    print(f"[DASHBOARD] Empresas para materiais: {user_companies}")
                    
                    if user_companies:
                        material_query = material_query.in_('cnpj_importador', user_companies)
                    else:
                        material_query = material_query.eq('cnpj_importador', 'NENHUMA_EMPRESA_ENCONTRADA')
                
                material_result = material_query.execute()
                material_data = material_result.data if material_result.data else []
                print(f"[DASHBOARD] Dados de materiais obtidos: {len(material_data)} registros")
                
                if material_data:
                    df_materiais = pd.DataFrame(material_data)
                    df_materiais = df_materiais[df_materiais['mercadoria'].notna()]
                    df_materiais = df_materiais[df_materiais['mercadoria'].str.strip() != '']
                    df_materiais = df_materiais[~df_materiais['mercadoria'].str.lower().str.contains('não informado|nao informado|n/a|vazio', na=False)]
                    
                    if not df_materiais.empty:
                        merc_dist = df_materiais['mercadoria'].value_counts().head(10)
                        charts['top_material'] = {
                            'labels': [str(x) for x in merc_dist.index.tolist()],
                            'values': [int(x) if not pd.isna(x) else 0 for x in merc_dist.values.tolist()]
                        }
                    else:
                        charts['top_material'] = {'labels': [], 'values': []}
                else:
                    charts['top_material'] = {'labels': [], 'values': []}
            except Exception as e:
                print(f"[DASHBOARD] Erro ao buscar dados de materiais: {e}")
                charts['top_material'] = {'labels': [], 'values': []}
            
            # Evolução semanal vazia para manter compatibilidade
            charts['weekly'] = {'periods': [], 'processes': [], 'values': []}
            
            try:
                recent_ops = supabase.table('vw_dashboard_ultimas_operacoes')\
                    .select('*').order('data_abertura', desc=True).execute().data or []
                
                # Mapear campos da view para o formato esperado pelo frontend
                if recent_ops:
                    mapped_ops = []
                    for op in recent_ops:
                        mapped_op = {
                            'cliente': str(op.get('cliente', '') or ''),
                            'numero_pedido': str(op.get('numero_pedido', '') or ''),
                            'data_embarque': str(op.get('data_embarque', '') or ''),
                            'local_embarque': str(op.get('local_embarque', '') or ''),
                            'modal': str(op.get('modal', '') or ''),
                            'status': str(op.get('status', '') or ''),
                            'mercadoria': str(op.get('mercadoria', '') or ''),
                            'despesas': float(op.get('despesas', 0) or 0) if op.get('despesas') else 0,
                            'recinto': str(op.get('recinto', '') or ''),
                            'data_chegada': str(op.get('data_chegada', '') or '')
                        }
                        mapped_ops.append(mapped_op)
                    recent_ops = mapped_ops
                    
            except Exception as e:
                print(f"[DASHBOARD] Erro ao buscar últimas operações: {e}")
                recent_ops = []
        
        # Estruturar dados no formato esperado pelo JavaScript
        dashboard_data = {
            'kpis': clean_data_for_json(kpis),
            'charts': clean_data_for_json(charts),
            'recent_operations': clean_data_for_json(recent_ops)
        }
        
        return jsonify({
            'success': True,
            'data': dashboard_data,
            'source': 'cache' if cached_data else 'views'
        })
        
    except Exception as e:
        print(f"[DASHBOARD] Erro na API dashboard-data: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': {
                'kpis': {},
                'charts': {},
                'recent_operations': []
            }
        }), 500
