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
    """Dashboard principal com carregamento inicial rápido e dados assíncronos"""
    # Get user companies if client
    user_companies = get_user_companies()
    selected_company = request.args.get('empresa')
    
    # Timestamp da última atualização
    last_update = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    
    # Get currency exchange rates
    currencies = get_currencies()
    
    # Verificar se é uma requisição para carregamento completo
    load_full = request.args.get('load_full', 'false') == 'true'
    
    if not load_full:
        # CARREGAMENTO INICIAL RÁPIDO - apenas estrutura da página
        print(f"[DEBUG DASHBOARD] Carregamento inicial rápido - dados serão carregados via AJAX")
        
        # Get all available companies for filtering
        data_limite_companies = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')  # Últimos 90 dias para companies
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
                             async_loading=True)  # Flag para indicar carregamento assíncrono
    
    # CARREGAMENTO COMPLETO (quando load_full=true)
    print(f"[DEBUG DASHBOARD] Carregamento completo solicitado...")
    
    # Cache simples apenas para controle de tempo, não para dados
    cache_key = f"dashboard_last_calc_{session['user']['id']}_{selected_company or 'all'}"
    cache_expiry = 300  # 5 minutos de cache
    
    # Verificar se calculamos recentemente (sem armazenar dados completos na sessão)
    if cache_key in session:
        last_calculation = session[cache_key]
        if (datetime.now().timestamp() - last_calculation) < cache_expiry:
            print(f"[DEBUG DASHBOARD] Cache de tempo válido (idade: {datetime.now().timestamp() - last_calculation:.1f}s) - mas recalculando dados para evitar cookie grande")
    
    print(f"[DEBUG DASHBOARD] Cache expirado ou inexistente, recalculando dados...")

    # Calcular data limite (12 meses atrás) para otimização
    data_limite_12_meses = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    print(f"[DEBUG DASHBOARD] Filtrando processos dos últimos 12 meses (desde: {data_limite_12_meses})")

    # Build query with client filter - OTIMIZADO: apenas campos essenciais para performance
    admin_roles = ['interno_unique', 'adm', 'admin', 'system']
    current_role = session['user']['role']
    
    # OTIMIZAÇÃO: Para admins, usar filtro de período padrão para carregamento inicial rápido
    if current_role in admin_roles:
        print("[DEBUG DASHBOARD] Usuário admin detectado - aplicando filtros de período padrão")
        # Por padrão, carregar apenas último mês para carregamento inicial rápido
        periodo_filtro = request.args.get('periodo', '30')  # 30 dias por padrão
        if periodo_filtro == 'all':
            # Se usuário solicitar todos os dados, usar filtro de 12 meses
            data_limite_filtro = data_limite_12_meses
            query_limit = None  # Sem limite para busca completa
        else:
            # Usar período específico (30, 90, 180 dias)
            dias_filtro = int(periodo_filtro) if periodo_filtro.isdigit() else 30
            data_limite_filtro = (datetime.now() - timedelta(days=dias_filtro)).strftime('%Y-%m-%d')
            query_limit = None  # Sem limite artificial
    else:
        data_limite_filtro = data_limite_12_meses
        query_limit = Config.MAX_ROWS_DASHBOARD
    
    query = supabase.table('importacoes_processos_aberta').select(
        'id, status_processo, canal, data_chegada, '
        'valor_cif_real, cnpj_importador, importador, '
        'modal, data_abertura, mercadoria, data_embarque, '
        'urf_entrada, ref_unique'  # Removidos campos desnecessários
    ).neq('status_processo', 'Despacho Cancelado')\
     .gte('data_abertura', data_limite_filtro)\
     .order('data_abertura.desc')
    
    # Aplicar limite apenas se definido
    if query_limit:
        query = query.limit(query_limit)
    
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

    # OTIMIZAÇÃO: Conversões mais rápidas usando vetorização do pandas
    print(f"[DEBUG DASHBOARD] Processando {len(data)} registros...")
    
    # Converter colunas numéricas de forma vetorizada
    df['valor_cif_real'] = pd.to_numeric(df['valor_cif_real'], errors='coerce').fillna(0)
    
    # Converter apenas datas essenciais (especificando formato brasileiro para evitar warnings)
    df['data_abertura'] = pd.to_datetime(df['data_abertura'], format='%d/%m/%Y', errors='coerce')
    df['data_embarque'] = pd.to_datetime(df['data_embarque'], format='%d/%m/%Y', errors='coerce') 
    df['data_chegada'] = pd.to_datetime(df['data_chegada'], format='%d/%m/%Y', errors='coerce')

    # OTIMIZAÇÃO: Calcular métricas usando operações vetorizadas do pandas
    total_operations = len(df)
    
    # Métricas por modal - usando value_counts para performance
    modal_counts = df['modal'].value_counts()
    aereo = modal_counts.get('AÉREA', 0)
    terrestre = modal_counts.get('RODOVIÁRIA', 0) 
    maritimo = modal_counts.get('MARÍTIMA', 0)
    
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
    
    # OTIMIZAÇÃO: Estimativa rápida de despesas sem consultas complexas
    # Para performance, usar estimativa fixa de 40% do VMCV para todos os processos
    vmcv_total = df['valor_cif_real'].sum()
    valor_medio_processo = vmcv_total / total_operations if total_operations > 0 else 0
    despesas_total = vmcv_total * 0.4  # Estimativa de 40% para todas as despesas
    despesa_media_processo = despesas_total / total_operations if total_operations > 0 else 0
    
    # Despesas por período usando a mesma estimativa
    vmcv_mes = df[df['data_abertura'].dt.month == hoje.month]['valor_cif_real'].sum()
    vmcv_semana = df[(df['data_abertura'] >= inicio_semana_ts) & (df['data_abertura'] <= fim_semana_ts)]['valor_cif_real'].sum()
    vmcv_proxima_semana = df[(df['data_abertura'] >= proxima_semana_inicio_ts) & (df['data_abertura'] <= proxima_semana_fim_ts)]['valor_cif_real'].sum()
    
    despesas_mes = vmcv_mes * 0.4
    despesas_semana = vmcv_semana * 0.4  
    despesas_proxima_semana = vmcv_proxima_semana * 0.4
    
    # Mapa vazio de despesas para compatibilidade com código existente
    despesas_map = {}
    
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

    # Preparar dados para template - SEM GRÁFICOS PLOTLY
    template_data = {
        'kpis': kpis,
        'analise_material': material_analysis,
        'material_analysis': material_analysis,
        'data': table_data,
        'table_data': table_data,
        'companies': available_companies,
        'selected_company': selected_company,
        'currencies': currencies,
        'last_update': last_update,
        'user_role': session['user']['role']
    }
    
    # OTIMIZAÇÃO: Salvar apenas timestamp na sessão para evitar cookie grande
    # Não salvar dados complexos na sessão Flask para evitar problema de tamanho de cookie
    session[cache_key] = datetime.now().timestamp()
    
    print(f"[DEBUG DASHBOARD] Timestamp de cache salvo. Processamento concluído.")
    
    return render_template('dashboard/index.html', **template_data)


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
        user_companies = get_user_companies()
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
        
        # Processamento rápido dos dados (similar ao dashboard principal)
        df['valor_cif_real'] = pd.to_numeric(df['valor_cif_real'], errors='coerce').fillna(0)
        df['data_abertura'] = pd.to_datetime(df['data_abertura'], format='%d/%m/%Y', errors='coerce')
        df['data_embarque'] = pd.to_datetime(df['data_embarque'], format='%d/%m/%Y', errors='coerce')
        df['data_chegada'] = pd.to_datetime(df['data_chegada'], format='%d/%m/%Y', errors='coerce')
        
        # Se for apenas para gráficos, preparar dados Chart.js
        charts_data = {}
        if charts_only or True:  # Sempre incluir dados de gráficos
            
            # 1. Gráfico Mensal (Line Chart)
            df_monthly = df.copy()
            df_monthly['mes_ano'] = df_monthly['data_abertura'].dt.to_period('M')
            monthly_data = df_monthly.groupby('mes_ano').agg({
                'ref_unique': 'count',
                'valor_cif_real': 'sum'
            }).reset_index()
            
            monthly_data['data'] = monthly_data['mes_ano'].dt.to_timestamp()
            monthly_data = monthly_data.sort_values('data').tail(12)
            
            charts_data['monthly'] = {
                'months': [d.strftime('%b %Y') for d in monthly_data['data']],
                'processes': monthly_data['ref_unique'].tolist(),
                'values': [round(v/1000000, 1) for v in monthly_data['valor_cif_real'].tolist()]
            }
            
            # 2. Gráfico de Canal DI (Doughnut Chart)
            canal_data = df['canal'].value_counts()
            charts_data['canal'] = {
                'labels': canal_data.index.tolist(),
                'values': canal_data.values.tolist()
            }
            
            # 3. Gráfico de Armazéns/URF (Horizontal Bar Chart)
            armazem_data = df.groupby('urf_entrada').agg({
                'ref_unique': 'count'
            }).reset_index()
            armazem_data = armazem_data.sort_values('ref_unique', ascending=True).tail(8)
            
            charts_data['armazem'] = {
                'labels': [str(label)[:20] + '...' if len(str(label)) > 20 else str(label) 
                          for label in armazem_data['urf_entrada'].tolist()],
                'values': armazem_data['ref_unique'].tolist()
            }
            
            # 4. Gráfico de Materiais (Horizontal Bar Chart)
            material_data = df.groupby('mercadoria').agg({
                'valor_cif_real': 'sum'
            }).reset_index()
            material_data = material_data.sort_values('valor_cif_real', ascending=True).tail(8)
            
            charts_data['material'] = {
                'labels': [str(label)[:25] + '...' if len(str(label)) > 25 else str(label) 
                          for label in material_data['mercadoria'].tolist()],
                'values': [round(v/1000000, 1) for v in material_data['valor_cif_real'].tolist()]
            }
        
        # Se for apenas para gráficos, retornar apenas os dados dos gráficos
        if charts_only:
            return jsonify({
                'success': True,
                'data': charts_data
            })
        
        # Caso contrário, continuar com o processamento completo...
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
        for _, row in df.head(100).iterrows():  # Limitar tabela a 100 registros na API
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
                'charts': charts_data  # Incluir dados dos gráficos sempre
            }
        })
        
    except Exception as e:
        print(f"[ERROR DASHBOARD API] {str(e)}")
        return jsonify({'success': False, 'error': str(e)})
