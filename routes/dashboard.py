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
        # Extrair referência correta
        nro_pedido = ""
        referencias = row.get('referencias', [])
        try:
            if referencias:
                if isinstance(referencias, str):
                    # Se for string, tentar fazer parse do JSON
                    import json
                    referencias = json.loads(referencias)
                
                # Se for uma lista com dicionários
                if isinstance(referencias, list) and len(referencias) > 0:
                    primeiro_item = referencias[0]
                    if isinstance(primeiro_item, dict) and 'referencia' in primeiro_item:
                        nro_pedido = str(primeiro_item['referencia'])
                    elif primeiro_item:
                        nro_pedido = str(primeiro_item)
                
                # Se for um dicionário direto
                elif isinstance(referencias, dict) and 'referencia' in referencias:
                    nro_pedido = str(referencias['referencia'])
                    
        except (json.JSONDecodeError, TypeError, IndexError, KeyError):
            nro_pedido = ""
        
        # Extrair nome do armazém
        armazem_nome = ""
        armazens = row.get('armazens', [])
        try:
            if armazens:
                if isinstance(armazens, str):
                    # Se for string, tentar fazer parse do JSON
                    import json
                    armazens = json.loads(armazens)
                
                # Se for uma lista com dicionários
                if isinstance(armazens, list) and len(armazens) > 0:
                    primeiro_item = armazens[0]
                    if isinstance(primeiro_item, dict) and 'nome' in primeiro_item:
                        armazem_nome = str(primeiro_item['nome']).strip()
                    elif primeiro_item:
                        armazem_nome = str(primeiro_item).strip()
                
                # Se for um dicionário direto
                elif isinstance(armazens, dict) and 'nome' in armazens:
                    armazem_nome = str(armazens['nome']).strip()
                    
        except (json.JSONDecodeError, TypeError, IndexError, KeyError):
            armazem_nome = ""
        
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
            'armazem_nome': armazem_nome,
            'carga_status': row.get('carga_status', ''),
            'resumo_mercadoria': row.get('resumo_mercadoria', ''),
            'despesas': despesas,
            'data_chegada': data_chegada_formatted,
            'cliente_razaosocial': row.get('cliente_razaosocial', '')
        })
    
    # Organizar KPIs para compatibilidade com o novo template
    valor_medio_processo = (vmcv_total / total_operations) if total_operations > 0 else 0
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
        'valor_medio_processo': valor_medio_processo,
        'valor_medio_processo_formatted': f"R$ {valor_medio_processo:,.0f}".replace(',', '.') if valor_medio_processo > 0 else "R$ 0",
        'vmcv_mes': vmcv_mes,
        'vmcv_semana': vmcv_semana,
        'vmcv_semana_formatted': f"R$ {vmcv_semana:,.0f}".replace(',', '.') if vmcv_semana > 0 else "R$ 0",
        'vmcv_proxima_semana': vmcv_proxima_semana,
        'vmcv_proxima_semana_formatted': f"R$ {vmcv_proxima_semana:,.0f}".replace(',', '.') if vmcv_proxima_semana > 0 else "R$ 0",
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
    
    # Gráfico de linha com área: Processos por dia e valor
    daily_chart = None
    if not df.empty:
        # Agrupar por dia
        df['data_abertura_day'] = df['data_abertura'].dt.date
        daily_data = df.groupby('data_abertura_day').agg({
            'numero': 'count',  # Total de processos
            'total_vmcv_real': 'sum'  # VMCV total
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
            y=daily_data['numero'],
            name='Processos por Dia',
            marker=dict(color='#3b82f6'),
            text=daily_data['numero'],
            textposition='outside',
            hovertemplate='<b>%{x}</b><br>Processos: %{y}<extra></extra>'
        ))
        
        # Linha para valor (eixo Y secundário)
        daily_chart.add_trace(go.Scatter(
            x=daily_data['data'],
            y=daily_data['total_vmcv_real'] / 1000000,  # Converter para milhões
            mode='lines+markers',
            name='Valor VMCV/dia (M)',
            line=dict(color='#10b981', width=2, shape='spline'),
            marker=dict(size=4),
            yaxis='y2',
            text=[f'{val/1000000:.1f}M' for val in daily_data['total_vmcv_real']],
            textposition='top center',
            hovertemplate='<b>%{x}</b><br>Valor: R$ %{text}<extra></extra>'
        ))
        
        daily_chart.update_layout(
            title={
                'text': 'Processos e Valor VMCV por Dia',
                'x': 0.5,
                'xanchor': 'center',
                'y': 0.95
            },
            yaxis=dict(title='Quantidade de Processos', side='left'),
            yaxis2=dict(title='Valor VMCV (Milhões R$)', side='right', overlaying='y'),
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
        # Agrupar por mês
        df['mes_ano'] = df['data_abertura'].dt.to_period('M')
        monthly_data = df.groupby('mes_ano').agg({
            'numero': 'count',  # Total de processos
            'total_vmcv_real': 'sum'  # VMCV total
        }).reset_index()
        
        # Converter período para datetime para plotly
        monthly_data['data'] = monthly_data['mes_ano'].dt.to_timestamp()
        monthly_data = monthly_data.sort_values('data')
        
        # Criar gráfico com área e linha
        monthly_chart = go.Figure()
        
        # Série 1: Área para Nº de Processos
        monthly_chart.add_trace(go.Scatter(
            x=monthly_data['data'],
            y=monthly_data['numero'],
            mode='lines+markers+text',
            name='Nº de Processos',
            fill='tozeroy',  # Preenche área até o zero
            fillcolor='rgba(255, 140, 0, 0.3)',  # Cor alaranjada com transparência
            line=dict(color='#FF8C00', width=2, shape='spline'),  # Linha alaranjada suave
            marker=dict(color='#FF8C00', size=6),
            text=monthly_data['numero'],
            textposition='top center',
            hovertemplate='<b>%{x|%b %Y}</b><br>Processos: %{y}<extra></extra>'
        ))
        
        # Série 2: Linha para VMCV Total (eixo Y secundário)
        monthly_chart.add_trace(go.Scatter(
            x=monthly_data['data'],
            y=monthly_data['total_vmcv_real'],
            mode='lines+markers+text',
            name='VMCV Total',
            line=dict(color='#8A2BE2', width=3, shape='spline'),  # Linha roxa suave
            marker=dict(color='#8A2BE2', size=6),
            text=[f'R$ {val/1000000:.1f}M' for val in monthly_data['total_vmcv_real']],
            textposition='top center',
            yaxis='y2',
            hovertemplate='<b>%{x|%b %Y}</b><br>VMCV: R$ %{y:,.0f}<extra></extra>'
        ))
        
        monthly_chart.update_layout(
            title={
                'text': 'Processos e Valores Mensais',
                'x': 0.5,
                'xanchor': 'center',
                'y': 0.95
            },
            yaxis=dict(
                side='left'
            ),
            yaxis2=dict(
                side='right', 
                overlaying='y',
                tickformat=',.0f'  # Formato de moeda para o eixo Y secundário
            ),
            hovermode='x unified',
            template='plotly_white',
            height=350,
            margin=dict(t=50, b=80, l=60, r=60),  # Mais margem para acomodar legendas
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.2,
                xanchor="center",
                x=0.5
            )
        )
    
    # Gráfico de rosca por canal DI
    canal_chart = None
    if not df.empty:
        # Agrupar por canal DI
        canal_data = df.groupby('diduimp_canal').agg({
            'numero': 'count',
            'total_vmcv_real': 'sum'  
        }).reset_index()
        
        # Definir cores específicas para os canais DI
        canal_colors = {
            'VERDE': '#10b981',     # Verde
            'AMARELO': '#f59e0b',   # Amarelo
            'VERMELHO': '#ef4444',  # Vermelho
            'CINZA': '#6b7280'      # Cinza para outros
        }
        
        # Preparar dados para o gráfico
        labels = []
        values = []
        colors = []
        
        for _, row in canal_data.iterrows():
            canal = row['diduimp_canal'] if row['diduimp_canal'] else 'Não Informado'
            quantidade = row['numero']
            
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
            textinfo='label+value',  # Mudança: mostra label + quantidade em vez de percentual
            textposition='outside',
            hovertemplate='<b>%{label}</b><br>Processos: %{value}<br>Percentual: %{percent}<extra></extra>',
            showlegend=False  # Mudança: remove as legendas
        )])
        
        canal_chart.update_layout(
            title={
                'text': 'Processos e Valores Mensais',
                'x': 0.5,
                'xanchor': 'center',
                'y': 0.98
            },
            template='plotly_white',
            height=350,
            margin=dict(t=100, b=10, l=10, r=10),  # Mudança: aumenta margem superior
        )


        # Gráfico de radar por armazém
        radar_chart = None
        if not df.empty:
            # Processar a coluna armazens para extrair nomes
            df_armazens = df.copy()
            armazem_names = []
            
            for _, row in df_armazens.iterrows():
                armazem_nome = ""
                armazens = row.get('armazens', [])
                try:
                    if armazens:
                        if isinstance(armazens, str):
                            # Se for string, tentar fazer parse do JSON
                            armazens = json.loads(armazens)
                        
                        # Se for uma lista com dicionários
                        if isinstance(armazens, list) and len(armazens) > 0:
                            primeiro_item = armazens[0]
                            if isinstance(primeiro_item, dict) and 'nome' in primeiro_item:
                                armazem_nome = str(primeiro_item['nome']).strip()
                            elif primeiro_item:
                                armazem_nome = str(primeiro_item).strip()
                        
                        # Se for um dicionário direto
                        elif isinstance(armazens, dict) and 'nome' in armazens:
                            armazem_nome = str(armazens['nome']).strip()
                            
                except (json.JSONDecodeError, TypeError, IndexError, KeyError):
                    armazem_nome = "Não Informado"
                
                if not armazem_nome:
                    armazem_nome = "Não Informado"
                    
                armazem_names.append(armazem_nome)
            
            # Adicionar coluna de armazém processada
            df_armazens['armazem_nome'] = armazem_names
            
            # Agrupar por armazém e pegar top 6
            radar_data = df_armazens.groupby('armazem_nome').agg({
                'numero': 'count',
                'total_vmcv_real': 'sum'  
            }).reset_index()
            
            # Ordenar por quantidade de processos e pegar top 6
            radar_data = radar_data.sort_values('numero', ascending=False).head(6)
            
            # Preparar dados para o radar
            categories = []
            values_qtd = []
            values_vmcv = []
            
            for _, row in radar_data.iterrows():
                armazem = row['armazem_nome']
                quantidade = row['numero']
                valor = row['total_vmcv_real']
                
                # Truncar nome longo para melhor visualização
                if len(armazem) > 20:
                    armazem = armazem[:20] + '...'
                
                categories.append(armazem)
                values_qtd.append(quantidade)
                values_vmcv.append(valor)
            
            # Normalizar valores VMCV para ter escala comparável com quantidade
            # Determinar o fator de escala com base no maior valor de cada série
            max_qtd = max(values_qtd) if values_qtd else 1
            max_vmcv = max(values_vmcv) if values_vmcv else 1
            scale_factor = max_qtd / max_vmcv if max_vmcv > 0 else 1
            
            normalized_vmcv = [v * scale_factor for v in values_vmcv]
            
            # Fechar o radar adicionando o primeiro valor no final
            categories.append(categories[0])
            values_qtd.append(values_qtd[0])
            normalized_vmcv.append(normalized_vmcv[0])
            
            # Criar gráfico de radar
            radar_chart = go.Figure()
            
            # Adicionar primeira série (quantidade de processos)
            radar_chart.add_trace(go.Scatterpolar(
                r=values_qtd,
                theta=categories,
                fill='toself',
                fillcolor='rgba(59, 130, 246, 0.2)',
                line=dict(color='#3b82f6', width=2),
                marker=dict(color='#3b82f6', size=6),
                name='Qtd. Processos',
                hovertemplate='<b>%{theta}</b><br>Processos: %{r}<extra></extra>'
            ))
            
            # Adicionar segunda série (valores VMCV normalizados)
            radar_chart.add_trace(go.Scatterpolar(
                r=normalized_vmcv,
                theta=categories,
                fill='toself',
                fillcolor='rgba(249, 115, 22, 0.2)',  # Laranja com transparência
                line=dict(color='#f97316', width=2),
                marker=dict(color='#f97316', size=6),
                name='Valor VMCV',
                hovertemplate='<b>%{theta}</b><br>VMCV: R$ %{customdata:,.0f}<extra></extra>',
                customdata=[[v] for v in values_vmcv + [values_vmcv[0]]]  # Adiciona os valores originais
            ))
            
            radar_chart.update_layout(
                title={
                    'text': 'Top Armazéns: Quantidade e Valor',
                    'x': 0.5,
                    'xanchor': 'center',
                    'y': 0.95,
                    'font': {'size': 14}
                },
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                        range=[0, max(max(values_qtd[:-1]), max(normalized_vmcv[:-1])) * 1.1] if values_qtd else [0, 10],
                        tickformat='.0f',
                        tickfont=dict(size=9)
                    ),
                    angularaxis=dict(
                        tickfont=dict(size=8)
                    )
                ),
                template='plotly_white',
                height=350,  # Ajustado para altura padrão
                margin=dict(t=50, b=50, l=10, r=10),  # Margens ajustadas para acomodar legenda
                showlegend=True,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=-0.15,
                    xanchor="center",
                    x=0.5
                )
            )

    # Gráfico de barras por material
    material_chart = None
    if not df.empty:
        # Usar os dados já processados de material_analysis
        if material_analysis:
            # Pegar top 8 materiais
            top_materials = material_analysis[:8]
            
            labels = []
            values = []
            
            for material in top_materials:
                # Truncar nome para melhor visualização
                nome = material['material']
                if len(nome) > 25:
                    nome = nome[:25] + '...'
                
                labels.append(nome)
                values.append(material['valor_total'])
            
            # Reverter as listas para mostrar maior valor no topo
            labels.reverse()
            values.reverse()
            
            # Criar gráfico de barras horizontais
            material_chart = go.Figure()
            
            material_chart.add_trace(go.Bar(
                x=values,
                y=labels,
                orientation='h',
                marker=dict(
                    color='#8b5cf6',  # Roxo
                    line=dict(color='white', width=1)
                ),
                text=[f'{val/1000000:.1f}M' for val in values],
                textposition='outside',
                hovertemplate='<b>%{y}</b><br>Valor: R$ %{x:,.0f}<extra></extra>'
            ))
            
            material_chart.update_layout(
                title={
                    'text': 'Top Materiais por Valor VMCV',
                    'x': 0.5,
                    'xanchor': 'center',
                    'y': 0.95
                },
                xaxis_title='Valor VMCV (R$)',
                yaxis_title='Material',
                template='plotly_white',
                height=350,  # Altura ajustada para ficar alinhado
                margin=dict(t=50, b=50, l=150, r=30),
                showlegend=False
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
