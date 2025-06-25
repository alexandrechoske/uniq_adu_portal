from flask import Blueprint, render_template, session, request, jsonify
from extensions import supabase
from routes.auth import login_required, role_required
from permissions import check_permission
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import scipy.stats as stats
from datetime import datetime, timedelta
import json
import requests
import numpy as np

bp = Blueprint('dashboard', __name__)

def get_currencies():
    """Get latest USD and EUR exchange rates"""
    try:
        response = requests.get('https://api.exchangerate-api.com/v4/latest/BRL')
        if response.status_code == 200:
            data = response.json()
            usd_rate = 1 / data['rates']['USD']
            eur_rate = 1 / data['rates']['EUR']
            return {
                'USD': round(usd_rate, 4),
                'EUR': round(eur_rate, 4),
                'last_updated': data['date']
            }
    except Exception as e:
        print(f"Error fetching currency rates: {str(e)}")
    
    return {
        'USD': 0.00,
        'EUR': 0.00,
        'last_updated': datetime.now().strftime('%Y-%m-%d')
    }

def get_user_companies():
    """Get companies that the user has access to"""
    if session['user']['role'] == 'cliente_unique':
        agent_response = supabase.table('clientes_agentes').select('empresa').eq('user_id', session['user']['id']).execute()
        if agent_response.data and agent_response.data[0].get('empresa'):
            companies = agent_response.data[0].get('empresa')
            if isinstance(companies, str):
                try:
                    return json.loads(companies)
                except:
                    return [companies]
            return companies
    return []

def get_arrival_date_display(row):
    """Get appropriate arrival date based on current date"""
    hoje = pd.Timestamp.now().date()
    
    if pd.notna(row['data_chegada']):
        data_chegada = pd.to_datetime(row['data_chegada']).date()
        if data_chegada <= hoje:
            return row['data_chegada']
    
    if pd.notna(row['previsao_chegada']):
        return row['previsao_chegada']
    
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

    # Build query with client filter
    query = supabase.table('importacoes_processos').select('*').neq('situacao', 'Despacho Cancelado')
    
    # Apply filters based on user role and selected company
    if session['user']['role'] == 'cliente_unique':
        if not user_companies:
            return render_template('dashboard/index.html', 
                                 kpis={}, table_data=[], companies=[], 
                                 currencies=currencies, last_update=last_update)
        
        if selected_company and selected_company in user_companies:
            query = query.eq('cliente_cpfcnpj', selected_company)
        else:
            query = query.in_('cliente_cpfcnpj', user_companies)
    elif selected_company:
        query = query.eq('cliente_cpfcnpj', selected_company)
    
    # Execute query
    operacoes = query.execute()
    data = operacoes.data if operacoes.data else []
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
    df['total_vmle_real'] = pd.to_numeric(df['total_vmle_real'], errors='coerce').fillna(0)
    df['total_vmcv_real'] = pd.to_numeric(df['total_vmcv_real'], errors='coerce').fillna(0)
    
    # Converter datas
    date_columns = ['data_abertura', 'data_embarque', 'data_chegada', 'previsao_chegada']
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')

    # Calcular métricas básicas (do OnePage)
    total_operations = len(df)
    
    # Métricas por modal de transporte
    aereo = len(df[df['via_transporte_descricao'] == 'AEREA'])
    terrestre = len(df[df['via_transporte_descricao'] == 'TERRESTRE'])
    maritimo = len(df[df['via_transporte_descricao'] == 'MARITIMA'])
    
    # Métricas por status
    aguardando_embarque = len(df[df['carga_status'] == '1 - Aguardando Embarque'])
    aguardando_chegada = len(df[df['carga_status'] == '2 - Em Trânsito'])
    di_registrada = len(df[df['carga_status'] == '3 - Desembarcada'])
    
    # Calcular períodos
    hoje = datetime.now()
    inicio_semana = hoje - timedelta(days=hoje.weekday())
    fim_semana = inicio_semana + timedelta(days=6)
    inicio_mes = hoje.replace(day=1)
    fim_mes = (inicio_mes + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    proxima_semana_inicio = fim_semana + timedelta(days=1)
    proxima_semana_fim = proxima_semana_inicio + timedelta(days=6)
    
    # Métricas de VMCV
    vmcv_total = df['total_vmcv_real'].sum()
    vmcv_mes = df[df['data_abertura'].dt.month == hoje.month]['total_vmcv_real'].sum()
    vmcv_semana = df[(df['data_abertura'] >= inicio_semana) & (df['data_abertura'] <= fim_semana)]['total_vmcv_real'].sum()
    vmcv_proxima_semana = df[(df['data_abertura'] >= proxima_semana_inicio) & (df['data_abertura'] <= proxima_semana_fim)]['total_vmcv_real'].sum()
    
    # Métricas de processos por período
    processos_mes = len(df[df['data_abertura'].dt.month == hoje.month])
    processos_semana = len(df[(df['data_abertura'] >= inicio_semana) & (df['data_abertura'] <= fim_semana)])
    processos_proxima_semana = len(df[(df['data_abertura'] >= proxima_semana_inicio) & (df['data_abertura'] <= proxima_semana_fim)])
    
    # Processos a chegar
    a_chegar_semana = len(df[
        ((df['previsao_chegada'] >= inicio_semana) & (df['previsao_chegada'] <= fim_semana)) |
        ((df['data_chegada'] >= inicio_semana) & (df['data_chegada'] <= fim_semana))
    ])
    a_chegar_mes = len(df[
        ((df['previsao_chegada'] >= inicio_mes) & (df['previsao_chegada'] <= fim_mes)) |
        ((df['data_chegada'] >= inicio_mes) & (df['data_chegada'] <= fim_mes))
    ])
    a_chegar_proxima_semana = len(df[
        ((df['previsao_chegada'] >= proxima_semana_inicio) & (df['previsao_chegada'] <= proxima_semana_fim)) |
        ((df['data_chegada'] >= proxima_semana_inicio) & (df['data_chegada'] <= proxima_semana_fim))
    ])
    
    # Preparar dados para a tabela com as colunas solicitadas
    table_data = []
    for _, row in df.iterrows():
        # Extrair primeira referência
        referencias = row.get('referencias', [])
        nro_pedido = ""
        try:
            if referencias:
                if isinstance(referencias, str):
                    # Se for string, tentar fazer parse do JSON
                    import json
                    referencias = json.loads(referencias)
                if isinstance(referencias, list) and len(referencias) > 0:
                    nro_pedido = str(referencias[0]) if referencias[0] else ""
        except (json.JSONDecodeError, TypeError, IndexError):
            nro_pedido = ""
        
        # Extrair primeiro armazém
        armazens = row.get('armazens', [])
        armazem_recinto = ""
        try:
            if armazens:
                if isinstance(armazens, str):
                    # Se for string, tentar fazer parse do JSON
                    import json
                    armazens = json.loads(armazens)
                if isinstance(armazens, list) and len(armazens) > 0:
                    armazem_recinto = str(armazens[0]) if armazens[0] else ""
        except (json.JSONDecodeError, TypeError, IndexError):
            armazem_recinto = ""
        
        # Calcular despesas (40% do VMLE se não tiver VMCV)
        try:
            vmcv = float(row.get('total_vmcv_real', 0) or 0)
            vmle = float(row.get('total_vmle_real', 0) or 0)
            despesas = vmcv if vmcv > 0 else (vmle * 0.4)
        except (ValueError, TypeError):
            despesas = 0.0
        
        # Determinar data de chegada apropriada
        data_chegada_display = get_arrival_date_display(row)
        
        # Formatar datas para exibição
        data_embarque_formatted = ""
        if pd.notna(row.get('data_embarque')):
            data_embarque_formatted = pd.to_datetime(row['data_embarque']).strftime('%d/%m/%Y')
        
        data_chegada_formatted = ""
        if data_chegada_display and pd.notna(data_chegada_display):
            data_chegada_formatted = pd.to_datetime(data_chegada_display).strftime('%d/%m/%Y')
        
        table_data.append({
            'nro_pedido': nro_pedido,
            'data_embarque': data_embarque_formatted,
            'local_embarque': row.get('local_embarque', ''),
            'via_transporte_descricao': row.get('via_transporte_descricao', ''),
            'armazem_recinto': armazem_recinto,
            'carga_status': row.get('carga_status', ''),
            'resumo_mercadoria': row.get('resumo_mercadoria', ''),
            'despesas': despesas,
            'data_chegada': data_chegada_formatted,
            'cliente_razaosocial': row.get('cliente_razaosocial', '')
        })
    
    # Organizar KPIs para compatibilidade com o novo template
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
        'vmcv_total': vmcv_total,
        'valor_total_formatted': f"R$ {vmcv_total:,.0f}".replace(',', '.') if vmcv_total > 0 else "R$ 0",
        'vmcv_mes': vmcv_mes,
        'vmcv_semana': vmcv_semana,
        'vmcv_proxima_semana': vmcv_proxima_semana,
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
        material_groups = df.groupby('resumo_mercadoria').agg({
            'numero': 'count',
            'total_vmcv_real': 'sum'
        }).reset_index()
        
        material_groups = material_groups.sort_values('total_vmcv_real', ascending=False)
        
        # Pegar top 10 materiais para análise
        for _, row in material_groups.head(10).iterrows():
            material_name = row['resumo_mercadoria'] if row['resumo_mercadoria'] else 'Não Informado'
            total_processos = int(row['numero'])
            valor_total = float(row['total_vmcv_real'])
            
            # Calcular valor da semana atual e próxima semana
            material_df = df[df['resumo_mercadoria'] == row['resumo_mercadoria']]
            valor_semana_atual = material_df[(material_df['data_abertura'] >= inicio_semana) & (material_df['data_abertura'] <= fim_semana)]['total_vmcv_real'].sum()
            valor_proxima_semana = material_df[(material_df['data_abertura'] >= proxima_semana_inicio) & (material_df['data_abertura'] <= proxima_semana_fim)]['total_vmcv_real'].sum()
            
            analise_material.append({
                'item_descricao': material_name,
                'total_processos': total_processos,
                'valor_total': valor_total,
                'valor_total_formatted': f"R$ {valor_total:,.0f}".replace(',', '.'),
                'valor_semana_atual': valor_semana_atual,
                'valor_semana_atual_formatted': f"R$ {valor_semana_atual:,.0f}".replace(',', '.'),
                'valor_proxima_semana': valor_proxima_semana,
                'valor_proxima_semana_formatted': f"R$ {valor_proxima_semana:,.0f}".replace(',', '.')
            })
        
        # Preparar dados principais da tabela
        for _, row in df.iterrows():
            data.append({
                'processo': row.get('numero', ''),
                'empresa_nome': row.get('cliente_razaosocial', ''),
                'modal': row.get('via_transporte_descricao', ''),
                'pais_origem': row.get('pais_origem', ''),
                'carga_status': row.get('carga_status', ''),
                'previsao_chegada': row.get('previsao_chegada') if pd.notna(row.get('previsao_chegada')) else None,
                'valor_fob_reais': float(row.get('total_vmcv_real', 0) or 0),
                'peso_bruto': float(row.get('peso_bruto', 0) or 0)
            })

    # Análise por Material (Compatibilidade com template antigo)
    material_analysis = []
    if not df.empty:
        # Agrupar por resumo_mercadoria
        material_groups = df.groupby('resumo_mercadoria').agg({
            'numero': 'count',
            'total_vmcv_real': 'sum'
        }).reset_index()
        
        material_groups = material_groups.sort_values('total_vmcv_real', ascending=False)
        total_vmcv_materials = material_groups['total_vmcv_real'].sum()
        
        # Pegar top 10 materiais
        for _, row in material_groups.head(10).iterrows():
            material = row['resumo_mercadoria'] if row['resumo_mercadoria'] else 'Não Informado'
            quantidade = int(row['numero'])
            valor_total = float(row['total_vmcv_real'])
            
            # Calcular valor da semana atual e próxima semana
            material_df = df[df['resumo_mercadoria'] == row['resumo_mercadoria']]
            valor_semana_atual = material_df[(material_df['data_abertura'] >= inicio_semana) & (material_df['data_abertura'] <= fim_semana)]['total_vmcv_real'].sum()
            valor_proxima_semana = material_df[(material_df['data_abertura'] >= proxima_semana_inicio) & (material_df['data_abertura'] <= proxima_semana_fim)]['total_vmcv_real'].sum()
            
            percentual = (valor_total / total_vmcv_materials * 100) if total_vmcv_materials > 0 else 0
            
            material_analysis.append({
                'material': material,
                'quantidade': quantidade,
                'valor_total': valor_total,
                'valor_total_formatado': f"R$ {valor_total:,.0f}".replace(',', '.'),
                'valor_semana_atual': valor_semana_atual,
                'valor_semana_atual_formatado': f"R$ {valor_semana_atual:,.0f}".replace(',', '.'),
                'valor_proxima_semana': valor_proxima_semana,
                'valor_proxima_semana_formatado': f"R$ {valor_proxima_semana:,.0f}".replace(',', '.'),
                'percentual': round(percentual, 1)
            })
    
    # Gráfico por Mês: Total de Processos e VMCV Total
    monthly_chart = None
    if not df.empty:
        # Agrupar por mês
        df['mes_ano'] = df['data_abertura'].dt.to_period('M')
        monthly_data = df.groupby('mes_ano').agg({
            'numero': 'count',  # Total de processos
            'total_vmcv_real': 'sum'  # VMCV total
        }).reset_index()
        
        # Converter período para datetime para plotly
        monthly_data['data'] = monthly_data['mes_ano'].dt.to_timestamp()
        monthly_data = monthly_data.sort_values('data')
        
        # Calcular regressão linear para processos
        if len(monthly_data) >= 2:
            x_numeric = np.arange(len(monthly_data))
            
            # Regressão para processos
            slope_proc, intercept_proc, r_value_proc, p_value_proc, std_err_proc = stats.linregress(x_numeric, monthly_data['numero'])
            trend_proc = slope_proc * x_numeric + intercept_proc
            
            # Regressão para VMCV
            slope_vmcv, intercept_vmcv, r_value_vmcv, p_value_vmcv, std_err_vmcv = stats.linregress(x_numeric, monthly_data['total_vmcv_real'])
            trend_vmcv = slope_vmcv * x_numeric + intercept_vmcv
            
            # Criar gráfico com duas linhas
            monthly_chart = go.Figure()
            
            # Linha de processos
            monthly_chart.add_trace(go.Scatter(
                x=monthly_data['data'],
                y=monthly_data['numero'],
                mode='lines+markers',
                name='Total de Processos',
                line=dict(color='#007BFF', width=3),
                marker=dict(size=8)
            ))
            
            # Linha de tendência para processos
            monthly_chart.add_trace(go.Scatter(
                x=monthly_data['data'],
                y=trend_proc,
                mode='lines',
                name=f'Tendência Processos (R²: {r_value_proc**2:.3f})',
                line=dict(color='#007BFF', dash='dash', width=2)
            ))
            
            # Linha de VMCV (eixo Y secundário)
            monthly_chart.add_trace(go.Scatter(
                x=monthly_data['data'],
                y=monthly_data['total_vmcv_real'],
                mode='lines+markers',
                name='VMCV Total',
                line=dict(color='#28a745', width=3),
                marker=dict(size=8),
                yaxis='y2'
            ))
            
            # Linha de tendência para VMCV
            monthly_chart.add_trace(go.Scatter(
                x=monthly_data['data'],
                y=trend_vmcv,
                mode='lines',
                name=f'Tendência VMCV (R²: {r_value_vmcv**2:.3f})',
                line=dict(color='#28a745', dash='dash', width=2),
                yaxis='y2'
            ))
            
            monthly_chart.update_layout(
                title='Evolução Mensal: Processos e VMCV',
                xaxis_title='Mês',
                yaxis=dict(title='Total de Processos', side='left'),
                yaxis2=dict(title='VMCV Total (R$)', side='right', overlaying='y'),
                hovermode='x unified',
                template='plotly_white',
                height=400
            )

    # Get all available companies for filtering
    companies_query = supabase.table('importacoes_processos').select('cliente_cpfcnpj', 'cliente_razaosocial').execute()
    all_companies = []
    if companies_query.data:
        companies_df = pd.DataFrame(companies_query.data)
        all_companies = [
            {'cpfcnpj': row['cliente_cpfcnpj'], 'nome': row['cliente_razaosocial']}
            for _, row in companies_df.drop_duplicates(subset=['cliente_cpfcnpj']).iterrows()
        ]

    # Filter companies based on user role
    available_companies = all_companies
    if session['user']['role'] == 'cliente_unique' and user_companies:
        available_companies = [c for c in all_companies if c['cpfcnpj'] in user_companies]

    # Convert charts to HTML
    chart_configs = {'displayModeBar': False, 'responsive': True}
    monthly_chart_html = monthly_chart.to_html(full_html=False, include_plotlyjs=False, div_id='monthly-chart', config=chart_configs) if monthly_chart else None
    
    return render_template('dashboard/index.html',
                         kpis=kpis,
                         analise_material=material_analysis,
                         material_analysis=material_analysis,
                         data=table_data,
                         table_data=table_data,
                         monthly_chart=monthly_chart_html,
                         companies=available_companies,
                         selected_company=selected_company,
                         currencies=currencies,
                         last_update=last_update,
                         user_role=session['user']['role'])
