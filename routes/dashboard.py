from flask import Blueprint, render_template, session, request, jsonify
from extensions import supabase
from routes.auth import login_required, role_required
from permissions import check_permission
from config import Config
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import scipy.stats as stats
from datetime import datetime, timedelta
import json
import requests
import numpy as np
import unicodedata
import re

bp = Blueprint('dashboard', __name__)

def format_value_smart(value, currency=False):
    """Format values with K, M, B abbreviations for better readability"""
    if not value or value == 0:
        return "0" if currency else "0"
    
    num = float(value)
    if num == 0:
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

def format_millions(value):
    """Formatar valores em milhões/milhares (ex: 4.1M, 950K)"""
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.1f}B"
    elif value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    elif value >= 1_000:
        return f"{value / 1_000:.0f}K"
    else:
        return f"{value:.0f}"

def get_currencies():
    """Get latest USD and EUR exchange rates - CACHED para evitar lentidão"""
    # Usar valores fixos por enquanto para evitar timeout em APIs externas
    # TODO: Implementar cache de moedas em background job
    return {
        'USD': 5.50,  # Valor estimado
        'EUR': 6.00,  # Valor estimado
        'last_updated': datetime.now().strftime('%Y-%m-%d')
    }

def get_user_companies():
    """Get companies that the user has access to - cached from session"""
    # Usar dados da sessão em vez de consultar o banco novamente
    if session['user']['role'] == 'cliente_unique':
        return session['user'].get('user_companies', [])
    return []

def get_arrival_date_display(row):
    """Get appropriate arrival date based on current date"""
    hoje = pd.Timestamp.now().date()
    
    if pd.notna(row['data_chegada']):
        data_chegada = pd.to_datetime(row['data_chegada']).date()
        if data_chegada <= hoje:
            return row['data_chegada']
    
    if pd.notna(row['data_chegada']):
        return row['data_chegada']
    
    return ""

@bp.route('/dashboard')
@check_permission()
def index(**kwargs):
    # Get user companies if client
    user_companies = get_user_companies()
    selected_company = request.args.get('empresa')
    
    # Timestamp da última atualização
    last_update = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    
    # Get currency exchange rates
    currencies = get_currencies()

    # Calcular data limite (12 meses atrás) para otimização
    data_limite_12_meses = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    print(f"[DEBUG DASHBOARD] Filtrando processos dos últimos 12 meses (desde: {data_limite_12_meses})")

    # Build query with client filter - OTIMIZADO: campos corretos baseados no ddls.sql
    query = supabase.table('importacoes_processos_aberta').select(
        'id, numero_di, status_processo, canal, data_chegada, '
        'valor_fob_real, valor_cif_real, cnpj_importador, importador, '
        'created_at, updated_at, modal, data_abertura, '
        'mercadoria, data_embarque, urf_entrada, ref_unique'
    ).neq('status_processo', 'Despacho Cancelado')\
     .gte('data_abertura', data_limite_12_meses)\
     .order('updated_at.desc')
    
    # Para usuários internos e admins, não limitar registros
    # Para clientes, manter limite para performance
    admin_roles = ['interno_unique', 'adm', 'admin', 'system']
    current_role = session['user']['role']
    print(f"[DEBUG DASHBOARD] Role do usuário: {current_role}")
    print(f"[DEBUG DASHBOARD] É admin? {current_role in admin_roles}")
    
    if current_role not in admin_roles:
        print(f"[DEBUG DASHBOARD] Aplicando limite de {Config.MAX_ROWS_DASHBOARD} registros")
        query = query.limit(Config.MAX_ROWS_DASHBOARD)
    else:
        print("[DEBUG DASHBOARD] SEM LIMITE - usuário admin, definindo limite alto")
        # Supabase tem limite padrão de 1000, então definimos um limite alto para admins
        query = query.limit(25000)  # Limite alto o suficiente para pegar todos os registros
    
    # Apply filters based on user role and selected company
    if current_role == 'cliente_unique':
        if not user_companies:
            return render_template('dashboard/index.html', 
                                 kpis={}, table_data=[], companies=[], 
                                 currencies=currencies, last_update=last_update)
        
        if selected_company and selected_company in user_companies:
            query = query.eq('cnpj_importador', selected_company)
        else:
            query = query.in_('cnpj_importador', user_companies)
    elif selected_company:
        query = query.eq('cnpj_importador', selected_company)
    
    # Execute query
    operacoes = query.execute()
    data = operacoes.data if operacoes.data else []
    print(f"[DEBUG DASHBOARD] Registros retornados: {len(data)}")
    df = pd.DataFrame(data)

    if df.empty:
        return render_template('dashboard/index.html', 
                             kpis={}, 
                             analise_material=[],
                             data=[],
                             table_data=[], 
                             companies=[], 
                             currencies=currencies, 
                             last_update=last_update,
                             user_role=session['user']['role'])

    # Converter colunas numéricas
    df['valor_fob_real'] = pd.to_numeric(df['valor_fob_real'], errors='coerce').fillna(0)
    df['valor_cif_real'] = pd.to_numeric(df['valor_cif_real'], errors='coerce').fillna(0)
    
    # Converter datas
    date_columns = ['data_abertura', 'data_embarque', 'data_chegada', 'data_chegada']
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')

    # Calcular métricas básicas (do OnePage)
    total_operations = len(df)
    
    # Métricas por modal de transporte - CORRIGIDO para novos valores
    aereo = len(df[df['modal'] == 'AÉREA'])
    terrestre = len(df[df['modal'] == 'RODOVIÁRIA']) 
    maritimo = len(df[df['modal'] == 'MARÍTIMA'])
    
    # Métricas por status
    aguardando_embarque = len(df[df['status_processo'].str.contains('DECLARACAO', na=False, case=False)])
    aguardando_chegada = len(df[df['status_processo'].str.contains('TRANSITO', na=False, case=False)])
    di_registrada = len(df[df['status_processo'].str.contains('DESEMBARACADA', na=False, case=False)])
    
    # Calcular períodos
    hoje = datetime.now()
    inicio_semana = hoje - timedelta(days=hoje.weekday())
    fim_semana = inicio_semana + timedelta(days=6)
    inicio_mes = hoje.replace(day=1)
    fim_mes = (inicio_mes + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    proxima_semana_inicio = fim_semana + timedelta(days=1)
    proxima_semana_fim = proxima_semana_inicio + timedelta(days=6)
    
    # Converter para Timestamp do pandas para comparações consistentes
    inicio_semana_ts = pd.Timestamp(inicio_semana)
    fim_semana_ts = pd.Timestamp(fim_semana)
    inicio_mes_ts = pd.Timestamp(inicio_mes)
    fim_mes_ts = pd.Timestamp(fim_mes)
    proxima_semana_inicio_ts = pd.Timestamp(proxima_semana_inicio)
    proxima_semana_fim_ts = pd.Timestamp(proxima_semana_fim)
    
    # Métricas de VMCV
    vmcv_total = df['valor_cif_real'].sum()
    vmcv_mes = df[df['data_abertura'].dt.month == hoje.month]['valor_cif_real'].sum()
    vmcv_semana = df[(df['data_abertura'] >= inicio_semana_ts) & (df['data_abertura'] <= fim_semana_ts)]['valor_cif_real'].sum()
    vmcv_proxima_semana = df[(df['data_abertura'] >= proxima_semana_inicio_ts) & (df['data_abertura'] <= proxima_semana_fim_ts)]['valor_cif_real'].sum()
    
    # Métricas de processos por período
    processos_mes = len(df[df['data_abertura'].dt.month == hoje.month])
    processos_semana = len(df[(df['data_abertura'] >= inicio_semana_ts) & (df['data_abertura'] <= fim_semana_ts)])
    processos_proxima_semana = len(df[(df['data_abertura'] >= proxima_semana_inicio_ts) & (df['data_abertura'] <= proxima_semana_fim_ts)])
    
    # Processos a chegar
    a_chegar_semana = len(df[
        ((df['data_chegada'] >= inicio_semana_ts) & (df['data_chegada'] <= fim_semana_ts)) |
        ((df['data_chegada'] >= inicio_semana_ts) & (df['data_chegada'] <= fim_semana_ts))
    ])
    a_chegar_mes = len(df[
        ((df['data_chegada'] >= inicio_mes_ts) & (df['data_chegada'] <= fim_mes_ts)) |
        ((df['data_chegada'] >= inicio_mes_ts) & (df['data_chegada'] <= fim_mes_ts))
    ])
    a_chegar_proxima_semana = len(df[
        ((df['data_chegada'] >= proxima_semana_inicio_ts) & (df['data_chegada'] <= proxima_semana_fim_ts)) |
        ((df['data_chegada'] >= proxima_semana_inicio_ts) & (df['data_chegada'] <= proxima_semana_fim_ts))
    ])
    
    # Preparar dados para a tabela com as colunas solicitadas
    table_data = []
    for _, row in df.iterrows():
        # Campo referencias não existe na nova tabela - usar ref_importador como alternativa
        nro_pedido = row.get('ref_importador', '') or ''
        
        # Campo armazens não existe na nova tabela - usar URF como alternativa  
        armazem_nome = row.get('urf_entrada', '') or 'Não Informado'
        
        # Calcular despesas usando nova lógica otimizada:
        # 1. Se tiver despesas na tabela importacoes_despesas, usar a soma (do mapa)
        # 2. Caso contrário, estimar como 40% do VMCV (impostos/taxas/honorários estimados)
        #    Exemplo: VMCV R$ 2.343.513,78 -> Despesas estimadas R$ 937.405,52 (40%)
        try:
            despesas = 0.0
            processo_id = row.get('id')
            
            if processo_id and str(processo_id) in despesas_map:
                # Usar despesas reais do mapa (já calculado anteriormente)
                despesas = despesas_map[str(processo_id)]
            else:
                # Se não tiver despesas registradas, usar estimativa de 40% do VMCV
                # Esta é a estimativa padrão de custos adicionais (impostos/taxas/honorários)
                vmcv = float(row.get('valor_cif_real', 0) or 0)
                if vmcv > 0:
                    despesas = vmcv * 0.4  # 40% do valor da mercadoria
                
        except Exception:
            # Em caso de erro, usar fallback para 40% do VMCV
            # Esta é a estimativa padrão de impostos/taxas/honorários
            try:
                vmcv = float(row.get('valor_cif_real', 0) or 0)
                despesas = vmcv * 0.4 if vmcv > 0 else 0.0  # 40% do valor da mercadoria
            except:
                despesas = 0.0
        
        # Determinar data de chegada apropriada
        data_chegada_display = get_arrival_date_display(row)
        
        # Formatar datas para exibição
        data_embarque_formatted = ""
        data_embarque_sort = None
        if pd.notna(row.get('data_embarque')):
            data_embarque_dt = pd.to_datetime(row['data_embarque'])
            data_embarque_formatted = data_embarque_dt.strftime('%d/%m/%Y')
            data_embarque_sort = data_embarque_dt
        
        data_chegada_formatted = ""
        if data_chegada_display and pd.notna(data_chegada_display):
            data_chegada_formatted = pd.to_datetime(data_chegada_display).strftime('%d/%m/%Y')
        
        table_data.append({
            'importador': row.get('importador', ''),
            'nro_pedido': nro_pedido,
            'data_embarque': data_embarque_formatted,
            'data_embarque_sort': data_embarque_sort,  # Para ordenação
            'urf_entrada': row.get('urf_entrada', ''),
            'modal': row.get('modal', ''),
            'status_processo': row.get('status_processo', ''),
            'mercadoria': row.get('mercadoria', ''),
            'despesas': despesas,
            'armazem_nome': armazem_nome,
            'data_chegada': data_chegada_formatted
        })
    
    # Ordenar tabela por data de embarque (mais recente primeiro)
    table_data.sort(key=lambda x: x['data_embarque_sort'] if x['data_embarque_sort'] is not None else pd.Timestamp.min, reverse=True)
    
    # Organizar KPIs para compatibilidade com o novo template
    valor_medio_processo = (vmcv_total / total_operations) if total_operations > 0 else 0
    
    # ===== CÁLCULO DAS DESPESAS OTIMIZADO =====
    # Buscar todas as despesas de uma vez para evitar N+1 queries
    despesas_total = 0.0
    despesas_mes = 0.0
    despesas_semana = 0.0
    despesas_proxima_semana = 0.0
    
    # Obter todos os IDs dos processos
    processo_ids = [str(row['id']) for _, row in df.iterrows() if row.get('id')]
    
    # Fazer uma única consulta para todas as despesas
    despesas_map = {}
    if processo_ids:
        try:
            despesas_query = supabase.table('importacoes_despesas')\
                .select('processo_id, valor_real')\
                .in_('processo_id', processo_ids)\
                .execute()
            
            if despesas_query.data:
                # Agrupar despesas por processo_id
                for despesa in despesas_query.data:
                    processo_id = despesa.get('processo_id')
                    valor = float(despesa.get('valor_real', 0) or 0)
                    
                    if processo_id not in despesas_map:
                        despesas_map[processo_id] = 0.0
                    despesas_map[processo_id] += valor
        except Exception as e:
            print(f"[DASHBOARD] Erro ao buscar despesas: {e}")
            despesas_map = {}
    
    # Calcular totais usando o mapa de despesas
    for _, row in df.iterrows():
        try:
            processo_id = row.get('id')
            despesas_processo = 0.0
            
            if processo_id and str(processo_id) in despesas_map:
                # Usar despesas reais do banco
                despesas_processo = despesas_map[str(processo_id)]
            else:
                # Se não tiver despesas registradas, usar estimativa de 40% do VMCV
                vmcv = float(row.get('valor_cif_real', 0) or 0)
                if vmcv > 0:
                    despesas_processo = vmcv * 0.4  # 40% do valor da mercadoria
                    
        except Exception:
            # Em caso de erro, usar fallback para 40% do VMCV
            try:
                vmcv = float(row.get('valor_cif_real', 0) or 0)
                despesas_processo = vmcv * 0.4 if vmcv > 0 else 0.0
            except:
                despesas_processo = 0.0
        
        # Somar ao total
        despesas_total += despesas_processo
        
        # Para mês e semana atual, considerar TANTO data de abertura QUANTO data de chegada
        # Isso permite que processos com chegada no período sejam incluídos mesmo que tenham sido abertos antes
        
        # Verificar se está no mês atual (por data de abertura OU chegada)
        incluir_no_mes = False
        data_abertura = row.get('data_abertura')
        if pd.notna(data_abertura):
            data_abertura_dt = pd.to_datetime(data_abertura)
            if data_abertura_dt.month == hoje.month and data_abertura_dt.year == hoje.year:
                incluir_no_mes = True
        
        # Verificar também por data de chegada (real ou prevista)
        data_chegada_display = get_arrival_date_display(row)
        if data_chegada_display and pd.notna(data_chegada_display):
            data_chegada_dt = pd.to_datetime(data_chegada_display)
            if data_chegada_dt.month == hoje.month and data_chegada_dt.year == hoje.year:
                incluir_no_mes = True
        
        if incluir_no_mes:
            despesas_mes += despesas_processo
        
        # Verificar se está na semana atual (por data de abertura OU chegada)
        incluir_na_semana = False
        if pd.notna(data_abertura):
            data_abertura_dt = pd.to_datetime(data_abertura)
            if data_abertura_dt >= inicio_semana_ts and data_abertura_dt <= fim_semana_ts:
                incluir_na_semana = True
        
        if data_chegada_display and pd.notna(data_chegada_display):
            data_chegada_dt = pd.to_datetime(data_chegada_display)
            if data_chegada_dt >= inicio_semana_ts and data_chegada_dt <= fim_semana_ts:
                incluir_na_semana = True
        
        if incluir_na_semana:
            despesas_semana += despesas_processo
        
        # Para despesas da próxima semana, usar data de chegada prevista/real
        if data_chegada_display and pd.notna(data_chegada_display):
            data_chegada_dt = pd.to_datetime(data_chegada_display)
            if data_chegada_dt >= proxima_semana_inicio_ts and data_chegada_dt <= proxima_semana_fim_ts:
                despesas_proxima_semana += despesas_processo
    

    
    # Calcular despesa média por processo
    despesa_media_processo = (despesas_total / total_operations) if total_operations > 0 else 0
    
    kpis = {
        'total': total_operations,
        'aereo': aereo,
        'terrestre': terrestre,
        'maritimo': maritimo,
        'aguardando_embarque': aguardando_embarque,
        'em_transito': aguardando_chegada,  # Alias para compatibilidade
        'aguardando_chegada': aguardando_chegada,  # Manter para compatibilidade
        'desembarcadas': di_registrada,  # Alias para compatibilidade
        'di_registrada': di_registrada,  # Manter para compatibilidade
        
        # ===== MÉTRICAS DE VMCV (mantidas para compatibilidade) =====
        'vmcv_total': vmcv_total,
        'valor_total_formatted': format_value_smart(vmcv_total, currency=True),
        'valor_medio_processo': valor_medio_processo,
        'valor_medio_processo_formatted': format_value_smart(valor_medio_processo, currency=True),
        'vmcv_mes': vmcv_mes,
        'vmcv_semana': vmcv_semana,
        'vmcv_semana_formatted': format_value_smart(vmcv_semana, currency=True),
        'vmcv_proxima_semana': vmcv_proxima_semana,
        'vmcv_proxima_semana_formatted': format_value_smart(vmcv_proxima_semana, currency=True),
        
        # ===== NOVAS MÉTRICAS DE DESPESAS =====
        'despesas_total': despesas_total,
        'despesas_total_formatted': format_value_smart(despesas_total, currency=True),
        'despesa_media_processo': despesa_media_processo,
        'despesa_media_processo_formatted': format_value_smart(despesa_media_processo, currency=True),
        'despesas_mes': despesas_mes,
        'despesas_mes_formatted': format_value_smart(despesas_mes, currency=True),
        'despesas_semana': despesas_semana,
        'despesas_semana_formatted': format_value_smart(despesas_semana, currency=True),
        'despesas_proxima_semana': despesas_proxima_semana,
        'despesas_proxima_semana_formatted': format_value_smart(despesas_proxima_semana, currency=True),
        
        # ===== OUTRAS MÉTRICAS =====
        'processos_mes': processos_mes,
        'processos_semana': processos_semana,
        'processos_proxima_semana': processos_proxima_semana,
        'a_chegar_semana': a_chegar_semana,
        'a_chegar_mes': a_chegar_mes,
        'a_chegar_proxima_semana': a_chegar_proxima_semana
    }
    
    # Preparar dados para o novo template
    analise_material = []
    data = []
    
    # Análise por Material (Principal Tipos de Material)
    if not df.empty:
        # Agrupar por resumo_mercadoria
        material_groups = df.groupby('mercadoria').agg({
            'ref_unique': 'count',
            'valor_cif_real': 'sum'
        }).reset_index()
        
        material_groups = material_groups.sort_values('valor_cif_real', ascending=False)
        
        # Pegar top 10 materiais para análise
        for _, row in material_groups.head(10).iterrows():
            material_name = row['mercadoria'] if row['mercadoria'] else 'Não Informado'
            total_processos = int(row['ref_unique'])
            valor_total = float(row['valor_cif_real'])
            
            # Calcular valor da semana atual e próxima semana
            material_df = df[df['mercadoria'] == row['mercadoria']]
            valor_semana_atual = material_df[(material_df['data_abertura'] >= inicio_semana_ts) & (material_df['data_abertura'] <= fim_semana_ts)]['valor_cif_real'].sum()
            valor_proxima_semana = material_df[(material_df['data_abertura'] >= proxima_semana_inicio_ts) & (material_df['data_abertura'] <= proxima_semana_fim_ts)]['valor_cif_real'].sum()
            
            analise_material.append({
                'item_descricao': material_name,
                'total_processos': total_processos,
                'valor_total': valor_total,
                'valor_total_formatted': format_value_smart(valor_total, currency=True),
                'valor_semana_atual': valor_semana_atual,
                'valor_semana_atual_formatted': format_value_smart(valor_semana_atual, currency=True),
                'valor_proxima_semana': valor_proxima_semana,
                'valor_proxima_semana_formatted': format_value_smart(valor_proxima_semana, currency=True)
            })
        
        # Preparar dados principais da tabela
        for _, row in df.iterrows():
            data.append({
                'processo': row.get('ref_unique', ''),
                'empresa_nome': row.get('importador', ''),
                'modal': row.get('modal', ''),
                'urf_entrada': row.get('urf_entrada', ''),  # Campo correto
                'status_processo': row.get('status_processo', ''),
                'data_chegada': row.get('data_chegada') if pd.notna(row.get('data_chegada')) else None,
                'valor_fob_reais': float(row.get('valor_cif_real', 0) or 0),
                'modal': row.get('modal', '')  # Usar modal em vez de tipo_operacao
            })

    # Análise por Material (Compatibilidade com template antigo)
    material_analysis = []
    if not df.empty:
        # Agrupar por resumo_mercadoria
        material_groups = df.groupby('mercadoria').agg({
            'ref_unique': 'count',
            'valor_cif_real': 'sum'
        }).reset_index()
        
        material_groups = material_groups.sort_values('valor_cif_real', ascending=False)
        total_vmcv_materials = material_groups['valor_cif_real'].sum()
        
        # Pegar top 10 materiais
        for _, row in material_groups.head(10).iterrows():
            material = row['mercadoria'] if row['mercadoria'] else 'Não Informado'
            quantidade = int(row['ref_unique'])
            valor_total = float(row['valor_cif_real'])
            
            # Calcular valor da semana atual e próxima semana
            material_df = df[df['mercadoria'] == row['mercadoria']]
            valor_semana_atual = material_df[(material_df['data_abertura'] >= inicio_semana_ts) & (material_df['data_abertura'] <= fim_semana_ts)]['valor_cif_real'].sum()
            valor_proxima_semana = material_df[(material_df['data_abertura'] >= proxima_semana_inicio_ts) & (material_df['data_abertura'] <= proxima_semana_fim_ts)]['valor_cif_real'].sum()
            
            percentual = (valor_total / total_vmcv_materials * 100) if total_vmcv_materials > 0 else 0;
            
            material_analysis.append({
                'material': material,
                'quantidade': quantidade,
                'valor_total': valor_total,
                'valor_total_formatado': format_value_smart(valor_total, currency=True),
                'valor_semana_atual': valor_semana_atual,
                'valor_semana_atual_formatado': format_value_smart(valor_semana_atual, currency=True),
                'valor_proxima_semana': valor_proxima_semana,
                'valor_proxima_semana_formatado': format_value_smart(valor_proxima_semana, currency=True),
                'percentual': round(percentual, 1)
            })
    
    # Gráfico de linha com área: Processos por dia e valor
    daily_chart = None
    if not df.empty:
        # Agrupar por dia
        df['data_abertura_day'] = df['data_abertura'].dt.date
        daily_data = df.groupby('data_abertura_day').agg({
            'ref_unique': 'count',  # Total de processos
            'valor_cif_real': 'sum'  # VMCV total
        }).reset_index()
        
        # Converter para datetime
        daily_data['data'] = pd.to_datetime(daily_data['data_abertura_day'])
        daily_data = daily_data.sort_values('data')
        
        # Pegar últimos 60 dias
        if len(daily_data) > 60:
            daily_data = daily_data.tail(60)
        
        # Criar gráfico de linha com área
        daily_chart = go.Figure()
        
        # Barras para processos
        daily_chart.add_trace(go.Bar(
            x=daily_data['data'],
            y=daily_data['ref_unique'],
            name='Processos por Dia',
            marker=dict(color='#3b82f6'),
            text=daily_data['ref_unique'],
            textposition='outside',
            hovertemplate='<b>%{x}</b><br>Processos: %{y}<extra></extra>'
        ))
        
        # Linha para valor (eixo Y secundário)
        daily_chart.add_trace(go.Scatter(
            x=daily_data['data'],
            y=daily_data['valor_cif_real'] / 1000000,  # Converter para milhões
            mode='lines+markers',
            name='Valor VMCV/dia (M)',
            line=dict(color='#10b981', width=2, shape='spline'),
            marker=dict(size=4),
            yaxis='y2',
            text=[f'{val/1000000:.1f}M' for val in daily_data['valor_cif_real']],
            textposition='top center',
            hovertemplate='<b>%{x}</b><br>Valor: R$ %{text}<extra></extra>'
        ))
        
        daily_chart.update_layout(

            hovermode='x unified',
            template='plotly_white',
            height=300,
            margin=dict(t=50, b=50, l=40, r=40),
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.15,
                xanchor="center",
                x=0.5
            )
        )


    # Gráfico Mensal: Área + Linha (Processos e Valores Mensais)
    monthly_chart = None
    if not df.empty:
        # Agrupar por mês - garantindo que seja apenas dos últimos 12 meses
        df_filtered_12m = df[df['data_abertura'] >= pd.to_datetime(data_limite_12_meses)]
        df_filtered_12m['mes_ano'] = df_filtered_12m['data_abertura'].dt.to_period('M')
        monthly_data = df_filtered_12m.groupby('mes_ano').agg({
            'ref_unique': 'count',  # Total de processos
            'valor_cif_real': 'sum'  # VMCV total
        }).reset_index()
        
        # Converter período para datetime para plotly
        monthly_data['data'] = monthly_data['mes_ano'].dt.to_timestamp()
        monthly_data = monthly_data.sort_values('data')
        
        # Limitar aos últimos 12 meses para garantir
        if len(monthly_data) > 12:
            monthly_data = monthly_data.tail(12)
        
        # Criar gráfico com área e linha
        monthly_chart = go.Figure()
        
        # Série 1: Área para Nº de Processos
        monthly_chart.add_trace(go.Scatter(
            x=monthly_data['data'],
            y=monthly_data['ref_unique'],
            mode='lines+markers+text',
            name='Nº de Processos',
            fill='tozeroy',  # Preenche área até o zero
            fillcolor='rgba(255, 140, 0, 0.3)',  # Cor alaranjada com transparência
            line=dict(color="#0079A5", width=2, shape='spline'),  # Linha alaranjada suave
            marker=dict(color='#0079A5', size=6),
            text=monthly_data['ref_unique'],
            textposition='bottom center',  # Posição embaixo para evitar sobreposição
            textfont=dict(size=10, color='#0079A5'),
            hovertemplate='<b>%{x|%b %Y}</b><br>Processos: %{y}<extra></extra>'
        ))
        
        # Série 2: Linha para VMCV Total (eixo Y secundário)
        monthly_chart.add_trace(go.Scatter(
            x=monthly_data['data'],
            y=monthly_data['valor_cif_real'],
            mode='lines+markers+text',
            name='VMCV Total',
            line=dict(color='#8A2BE2', width=3, shape='spline'),  # Linha roxa suave
            marker=dict(color='#8A2BE2', size=6),
            text=[f'R$ {val/1000000:.1f}M' for val in monthly_data['valor_cif_real']],
            textposition='top center',  # Posição em cima para os valores
            textfont=dict(size=10, color='#8A2BE2'),
            yaxis='y2',
            hovertemplate='<b>%{x|%b %Y}</b><br>VMCV: R$ %{y:,.0f}<extra></extra>'
        ))
        
        monthly_chart.update_layout(
            yaxis=dict(
                side='left',
                showticklabels=False,  # Remove labels do eixo Y
                title='',  # Remove título do eixo
                showgrid=True,
                gridcolor='rgba(0,0,0,0.1)'
            ),
            yaxis2=dict(
                side='right', 
                overlaying='y',
                showticklabels=False,  # Remove labels do eixo Y secundário
                title='',  # Remove título do eixo
                showgrid=False
            ),
            xaxis=dict(
                title='',  # Remove título do eixo X
                showgrid=False
            ),
            hovermode='x unified',
            template='plotly_white',
            height=350,
            margin=dict(t=30, b=50, l=30, r=30),  # Margens reduzidas
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.15,
                xanchor="center",
                x=0.5
            )
        )
    
    # Gráfico de rosca por canal DI
    canal_chart = None
    if not df.empty:
        # Agrupar por canal DI
        canal_data = df.groupby('canal').agg({
            'ref_unique': 'count',
            'valor_cif_real': 'sum'  
        }).reset_index()
        
        # Definir cores específicas para os canais DI
        canal_colors = {
            'Verde': '#10b981',     # Verde
            'Amarelo': '#f59e0b',   # Amarelo
            'Vermelho': '#ef4444',  # Vermelho
            'Cinza': '#6b7280'      # Cinza para outros
        }
        
        # Preparar dados para o gráfico
        labels = []
        values = []
        colors = []
        
        for _, row in canal_data.iterrows():
            canal = row['canal'] if row['canal'] else 'Não Informado'
            quantidade = row['ref_unique']
            
            labels.append(canal)
            values.append(quantidade)
            colors.append(canal_colors.get(canal, '#6b7280'))
        
        # Criar gráfico de rosca (donut chart)
        canal_chart = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=0.4,  # Cria o buraco no meio (rosca)
            marker=dict(
                colors=colors,
                line=dict(color='white', width=2)
            ),
            textinfo='label+value',  # Mostra label + quantidade
            textposition='inside',  # Labels dentro dos segmentos
            insidetextorientation='radial',  # Orientação dos textos
            textfont=dict(color='white', size=12, family='Arial'),  # Texto branco e legível
            hovertemplate='<b>%{label}</b><br>Processos: %{value}<br>Percentual: %{percent}<extra></extra>',
            showlegend=False  # Remove as legendas externas
        )])
        
        canal_chart.update_layout(

            template='plotly_white',
            height=350,
            margin=dict(t=100, b=10, l=10, r=10),  # Mudança: aumenta margem superior
        )


        # Gráfico de radar por armazém
        radar_chart = None
        if not df.empty:
            # Campo armazens não existe na nova tabela - usando URF de entrada como alternativa
            df_armazens = df.copy()
            armazem_names = []
            
            for _, row in df_armazens.iterrows():
                # Usar URF de entrada como substituto para armazém
                armazem_nome = row.get('urf_entrada', 'Não Informado')
                if not armazem_nome or pd.isna(armazem_nome):
                    armazem_nome = "Não Informado"
                armazem_names.append(str(armazem_nome).strip())
            
            # Adicionar coluna de armazém processada
            df_armazens['armazem_nome'] = armazem_names
            
            # Agrupar por armazém e pegar top 6
            radar_data = df_armazens.groupby('armazem_nome').agg({
                'ref_unique': 'count',
                'valor_cif_real': 'sum'  
            }).reset_index()
            
            # Ordenar por quantidade de processos e pegar top 6
            radar_data = radar_data.sort_values('ref_unique', ascending=False).head(6)
            
            # Preparar dados para o gráfico combinado
            categories = []
            values_qtd = []
            values_vmcv = []
            
            for _, row in radar_data.iterrows():
                armazem = row['armazem_nome']
                quantidade = row['ref_unique']
                valor = row['valor_cif_real']
                
                # Truncar nome longo para melhor visualização
                if len(armazem) > 20:
                    armazem = armazem[:20] + '...'
                
                categories.append(armazem)
                values_qtd.append(quantidade)
                values_vmcv.append(valor)
            
            # Reverter as listas para mostrar maior valor no topo
            categories.reverse()
            values_qtd.reverse()
            values_vmcv.reverse()
            
            # Criar gráfico de barras horizontais agrupadas
            radar_chart = go.Figure()
            
            # Trace 1: Quantidade de Processos (eixo X principal)
            radar_chart.add_trace(go.Bar(
                x=values_qtd,
                y=categories,
                orientation='h',
                name='Qtd. de Processos',
                marker=dict(
                    color='#10b981',  # Verde
                    line=dict(color='white', width=1)
                ),
                text=values_qtd,
                textposition='inside',
                insidetextanchor='middle',
                textfont=dict(color='white', size=10),
                hovertemplate='<b>%{y}</b><br>Processos: %{x}<extra></extra>',
                offsetgroup=1
            ))
            
            # Trace 2: Valor VMCV (eixo X secundário)
            radar_chart.add_trace(go.Bar(
                x=values_vmcv,
                y=categories,
                orientation='h',
                name='Valor VMCV',
                marker=dict(
                    color='#8b5cf6',  # Roxo
                    line=dict(color='white', width=1)
                ),
                text=[format_millions(v) for v in values_vmcv],
                textposition='inside',
                insidetextanchor='middle',
                textfont=dict(color='white', size=10),
                hovertemplate='<b>%{y}</b><br>Valor: R$ %{x:,.0f}<extra></extra>',
                xaxis='x2',
                offsetgroup=2
            ))
            
            radar_chart.update_layout(
                # Remover título (já está no card HTML)
                title='',
                # Configurar eixos (ocultar elementos visuais, manter apenas nomes das categorias)
                xaxis=dict(
                    showgrid=False,
                    zeroline=False,
                    showline=False,
                    showticklabels=False
                ),
                xaxis2=dict(
                    side='top',
                    overlaying='x',
                    showgrid=False,
                    zeroline=False,
                    showline=False,
                    showticklabels=False
                ),
                yaxis=dict(
                    tickfont=dict(size=10),
                    showgrid=False,
                    zeroline=False,
                    showline=False
                ),
                template='plotly_white',
                height=350,
                margin=dict(t=20, b=20, l=180, r=30),  # Reduzir margens e espaço à esquerda para nomes
                showlegend=True,
                legend=dict(
                    orientation="h",
                    yanchor="top",
                    y=-0.1,
                    xanchor="center",
                    x=0.5
                ),
                barmode='group',  # Barras agrupadas
                bargap=0.3,  # Reduzir espaço entre grupos para ocupar melhor o espaço
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            def clean_material_name(material_name):
                """Limpa e normaliza nomes de materiais preservando o conteúdo original quando possível"""
                
                if not material_name or pd.isna(material_name):
                    return "Não Informado"
                
                # Converter para string e fazer trim
                material = str(material_name).strip()
                
                # Se ainda estiver vazio, retornar padrão
                if not material:
                    return "Não Informado"
                
                # Apenas capitalizar corretamente, mantendo caracteres especiais e acentos
                # Isso preserva "MANUTENÇÃO" como "Manutenção"
                material = material.title()
                
                return material

            # Gráfico de barras por material - DUPLO (valor + quantidade)
            material_chart = None
            if not df.empty:
                # Limpar e agrupar materiais com nomes similares
                df_materials = df.copy()
                df_materials['material_limpo'] = df_materials['mercadoria'].apply(clean_material_name)
                
                # Agrupar por material limpo
                material_groups_clean = df_materials.groupby('material_limpo').agg({
                    'ref_unique': 'count',
                    'valor_cif_real': 'sum'
                }).reset_index()
                
                material_groups_clean = material_groups_clean.sort_values('valor_cif_real', ascending=False)
                
                # Pegar top 6 materiais para melhor visualização
                top_materials_clean = material_groups_clean.head(6)
                
                if not top_materials_clean.empty:
                    labels = []
                    values_valor = []
                    values_quantidade = []
                    
                    for _, row in top_materials_clean.iterrows():
                        # Truncar nome para melhor visualização
                        nome = row['material_limpo']
                        if len(nome) > 30:
                            nome = nome[:30] + '...'
                        
                        labels.append(nome)
                        values_valor.append(float(row['valor_cif_real']))
                        values_quantidade.append(int(row['ref_unique']))
                    
                    # Reverter as listas para mostrar maior valor no topo
                    labels.reverse()
                    values_valor.reverse()
                    values_quantidade.reverse()
                    
                    # Criar gráfico de barras horizontais duplas
                    material_chart = go.Figure()
                    
                    # Barra 1: Valor VMCV
                    material_chart.add_trace(go.Bar(
                        x=values_valor,
                        y=labels,
                        orientation='h',
                        name='Valor VMCV',
                        marker=dict(
                            color='#8b5cf6',  # Roxo
                            line=dict(color='white', width=1)
                        ),
                        text=[format_value_smart(val, currency=True) for val in values_valor],
                        textposition='inside',
                        insidetextanchor='middle',
                        textfont=dict(color='white', size=10),
                        hovertemplate='<b>%{y}</b><br>Valor: R$ %{x:,.0f}<extra></extra>',
                        offsetgroup=1  # Grupo para barras lado a lado
                    ))
                    
                    # Barra 2: Quantidade de Processos (eixo secundário)
                    material_chart.add_trace(go.Bar(
                        x=values_quantidade,
                        y=labels,
                        orientation='h',
                        name='Qtd. Processos',
                        marker=dict(
                            color='#10b981',  # Verde
                            line=dict(color='white', width=1)
                        ),
                        text=[f'{val}' for val in values_quantidade],
                        textposition='inside',
                        insidetextanchor='middle',
                        textfont=dict(color='white', size=10),
                        hovertemplate='<b>%{y}</b><br>Processos: %{x}<extra></extra>',
                        xaxis='x2',  # Usar eixo X secundário
                        offsetgroup=2  # Grupo separado para barras lado a lado
                    ))
                    
                    material_chart.update_layout(
                        # Remover título (já está no card HTML)
                        title='',
                        # Configurar eixos (ocultar elementos visuais)
                        xaxis=dict(
                            showgrid=False,
                            zeroline=False,
                            showline=False,
                            showticklabels=False
                        ),
                        xaxis2=dict(
                            side='top',
                            overlaying='x',
                            showgrid=False,
                            zeroline=False,
                            showline=False,
                            showticklabels=False
                        ),
                        yaxis=dict(
                            tickfont=dict(size=10),
                            showgrid=False,
                            zeroline=False,
                            showline=False
                        ),
                        template='plotly_white',
                        height=350,
                        margin=dict(t=20, b=20, l=180, r=30),  # Reduzir margens superior e inferior
                        showlegend=True,
                        legend=dict(
                            orientation="h",
                            yanchor="top",
                            y=-0.1,
                            xanchor="center",
                            x=0.5
                        ),
                        barmode='group',  # Barras agrupadas lado a lado
                        bargap=0.3  # Reduzir espaço entre grupos para ocupar melhor o espaço
                    )


    # Get all available companies for filtering - OTIMIZADO com filtro de 12 meses
    companies_query = supabase.table('importacoes_processos_aberta')\
        .select('cnpj_importador, importador')\
        .neq('cnpj_importador', '')\
        .not_.is_('cnpj_importador', 'null')\
        .gte('data_abertura', data_limite_12_meses)\
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

    # Convert charts to HTML
    chart_configs = {'displayModeBar': False, 'responsive': True}
    daily_chart_html = daily_chart.to_html(full_html=False, include_plotlyjs=False, div_id='daily-chart', config=chart_configs) if daily_chart else None
    monthly_chart_html = monthly_chart.to_html(full_html=False, include_plotlyjs=False, div_id='monthly-chart', config=chart_configs) if monthly_chart else None
    canal_chart_html = canal_chart.to_html(full_html=False, include_plotlyjs=False, div_id='canal-chart', config=chart_configs) if canal_chart else None
    radar_chart_html = radar_chart.to_html(full_html=False, include_plotlyjs=False, div_id='radar-chart', config=chart_configs) if radar_chart else None
    material_chart_html = material_chart.to_html(full_html=False, include_plotlyjs=False, div_id='material-chart', config=chart_configs) if material_chart else None
    
    return render_template('dashboard/index.html',
                         kpis=kpis,
                         analise_material=material_analysis,
                         material_analysis=material_analysis,
                         data=table_data,
                         table_data=table_data,
                         daily_chart=daily_chart_html,
                         monthly_chart=monthly_chart_html,
                         canal_chart=canal_chart_html,
                         radar_chart=radar_chart_html,
                         material_chart=material_chart_html,
                         companies=available_companies,
                         selected_company=selected_company,
                         currencies=currencies,
                         last_update=last_update,
                         user_role=session['user']['role'])
