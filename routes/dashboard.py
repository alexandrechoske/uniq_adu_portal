from flask import Blueprint, render_template, session, request, jsonify
from extensions import supabase
from routes.auth import login_required, role_required
from permissions import check_permission
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import scipy.stats as stats
from datetime import datetime, timedelta

bp = Blueprint('dashboard', __name__)

@bp.route('/dashboard')
@check_permission()  # Usando o novo sistema de permissões
def index(**kwargs):
    # Get user companies if client
    user_companies = []
    if session['user']['role'] == 'cliente_unique':
        agent_response = supabase.table('clientes_agentes').select('empresa').eq('user_id', session['user']['id']).execute()
        if agent_response.data and agent_response.data[0].get('empresa'):
            user_companies = agent_response.data[0].get('empresa')
            if isinstance(user_companies, str):
                import json
                try:
                    user_companies = json.loads(user_companies)
                except:
                    user_companies = [user_companies]

    # Build query with client filter
    query = supabase.table('importacoes_processos').select('*').neq('situacao', 'Despacho Cancelado').order('data_abertura', desc=True)
    if user_companies:
        query = query.in_('cliente_cpfcnpj', user_companies)
    
    operacoes = query.execute()
    data = operacoes.data if operacoes.data else []
    df = pd.DataFrame(data)

    # Calculate metrics
    total_operations = len(df)
    processos_abertos = len(df[df['situacao'] == 'Aberto']) if not df.empty else 0
    
    uma_semana_atras = datetime.now() - timedelta(days=7)
    df['data_abertura'] = pd.to_datetime(df['data_abertura'])
    novos_semana = len(df[df['data_abertura'] > uma_semana_atras]) if not df.empty else 0
    em_transito = len(df[df['carga_status'].notna()]) if not df.empty else 0
    
    # Calculate new metric: "A chegar nessa semana" (Arriving This Week)
    semana_atual = datetime.now()
    fim_semana = semana_atual + timedelta(days=(6 - semana_atual.weekday()))  # Find the end of current week (Sunday)
    
    # Check if a predicted arrival date field exists in the dataset
    a_chegar_semana = 0
    if 'data_prevista_chegada' in df.columns:
        df['data_prevista_chegada'] = pd.to_datetime(df['data_prevista_chegada'])
        # Filter processes arriving this week (from today until end of week)
        a_chegar_semana = len(df[(df['data_prevista_chegada'] >= semana_atual.date()) & 
                                (df['data_prevista_chegada'] <= fim_semana.date()) &
                                (df['situacao'] == 'Aberto')]) if not df.empty else 0
    elif 'eta' in df.columns:  # Alternative field name for estimated arrival
        df['eta'] = pd.to_datetime(df['eta'])
        # Filter processes arriving this week (from today until end of week)
        a_chegar_semana = len(df[(df['eta'] >= semana_atual.date()) & 
                                (df['eta'] <= fim_semana.date()) &
                                (df['situacao'] == 'Aberto')]) if not df.empty else 0

    # Create charts
    if not df.empty:
        # Client Distribution (horizontal bar with gradient)
        df_cliente = df['cliente_razaosocial'].value_counts().reset_index()
        df_cliente.columns = ['Cliente', 'Quantidade']
        df_cliente = df_cliente.head(10)  # Limit to top 10 clients
        
        chart_cliente = go.Figure()
        chart_cliente.add_trace(go.Bar(
            x=df_cliente['Quantidade'],
            y=df_cliente['Cliente'],
            orientation='h',
            marker=dict(
                color=df_cliente['Quantidade'],
                colorscale=[[0, '#007BFF'], [1, '#0056b3']],
                showscale=False
            )
        ))
        
        chart_cliente.update_layout(
            title_text='Distribuição por Cliente',
            title_x=0.5,
            title_font={'family': 'Roboto, sans-serif'},
            showlegend=False,
            yaxis={'categoryorder':'total ascending'},
            xaxis_title='Volume de Processos',
            yaxis_title='',
            margin=dict(l=0, r=0, t=40, b=0),
            height=400,
            template='plotly_white',
            paper_bgcolor='white',
            plot_bgcolor='white'
        )        # Temporal Evolution - adaptativo entre diário e semanal com base no volume de registros
        
        # Determinar o tipo de visualização baseado no volume de dados
        show_daily = len(df) < 30  # Mostrar visualização diária se tiver menos de 30 registros
        
        if show_daily:
            # Agrupamento diário
            df['date'] = df['data_abertura'].dt.date
            df_time = df.groupby('date').size().reset_index(name='Quantidade')
            df_time.columns = ['Data', 'Quantidade']
            df_time['Data'] = pd.to_datetime(df_time['Data'])
            
            # Ordenar por data
            df_time = df_time.sort_values('Data')
            
            # Se houver menos de 7 registros, preencher os dias intermediários
            if len(df_time) < 7:
                date_range = pd.date_range(start=df_time['Data'].min(), end=df_time['Data'].max())
                date_df = pd.DataFrame({'Data': date_range})
                df_time = pd.merge(date_df, df_time, on='Data', how='left').fillna(0)
            
            # Calcular média móvel de 3 dias
            window_size = min(3, len(df_time))
            df_time['Media_Movel'] = df_time['Quantidade'].rolling(window=window_size).mean()
            
            period_text = "Diária"
            hover_format = 'Data: %{x|%d/%m/%Y}<br>Processos: %{y}<extra></extra>'
            mm_name = 'Média 3 dias'
        else:
            # Agrupamento semanal (código original)
            df['week_year'] = df['data_abertura'].dt.strftime('%Y-%U')
            df_time = df.groupby('week_year').size().reset_index(name='Quantidade')
            df_time.columns = ['Semana', 'Quantidade']
            
            # Converter week_year de volta para datetime para melhor visualização
            df_time['Data'] = pd.to_datetime([f"{w.split('-')[0]}-W{w.split('-')[1]}-1" for w in df_time['Semana']], format='%Y-W%W-%w')
            
            # Ordenar por data
            df_time = df_time.sort_values('Data')
            
            # Calcular média móvel de 4 semanas
            df_time['Media_Movel'] = df_time['Quantidade'].rolling(window=4).mean()
            
            period_text = "Semanal"
            hover_format = 'Semana: %{x|%d/%m/%Y}<br>Processos: %{y}<extra></extra>'
            mm_name = 'Média 4 semanas'
        
        # Preparar dados para regressão linear e previsão
        has_trend = False
        if len(df_time) > 1:
            # Criar índices numéricos para x
            df_time['idx'] = range(len(df_time))
            
            # Filtrar pontos nulos para regressão
            regression_data = df_time.dropna()
            
            if len(regression_data) > 1:
                # Calcular regressão linear
                slope, intercept, r_value, p_value, std_err = stats.linregress(
                    regression_data['idx'], regression_data['Quantidade']
                )
                
                # Criar linha de tendência
                df_time['Tendencia'] = intercept + slope * df_time['idx']
                
                # Adicionar pontos de previsão futura (3 períodos)
                future_periods = 3
                future_indices = range(len(df_time), len(df_time) + future_periods)
                future_dates = pd.date_range(start=df_time['Data'].max(), periods=future_periods+1, freq='W' if not show_daily else 'D')[1:]
                
                future_df = pd.DataFrame({
                    'Data': future_dates,
                    'idx': future_indices
                })
                future_df['Tendencia'] = intercept + slope * future_df['idx']
                
                # Texto da equação da tendência
                trend_equation = f"y = {intercept:.2f} + {slope:.2f}x (R² = {r_value**2:.2f})"
                has_trend = True
        
        chart_data = go.Figure()
        
        # Área com gradiente
        chart_data.add_trace(go.Scatter(
            x=df_time['Data'],
            y=df_time['Quantidade'],
            fill='tozeroy',
            mode='lines',
            line=dict(width=0.5, color='#007BFF'),
            fillcolor='rgba(0, 123, 255, 0.2)',
            name=f'Volume {period_text}',
            hovertemplate=hover_format
        ))
        
        # Linha de média móvel
        chart_data.add_trace(go.Scatter(
            x=df_time['Data'],
            y=df_time['Media_Movel'],
            mode='lines',
            line=dict(color='#0056b3', width=2, dash='dot'),
            name=mm_name,
            hovertemplate=f'Data: %{{x|%d/%m/%Y}}<br>Média: %{{y:.1f}}<extra></extra>'
        ))
        
        # Adicionar linha de tendência e previsão se disponível
        if has_trend:
            # Linha de tendência para dados existentes
            chart_data.add_trace(go.Scatter(
                x=df_time['Data'],
                y=df_time['Tendencia'],
                mode='lines',
                line=dict(color='#DC143C', width=1.5),  # Vermelho carmesim
                name='Tendência',
                hovertemplate=f'Data: %{{x|%d/%m/%Y}}<br>Tendência: %{{y:.1f}}<extra></extra>'
            ))
            
            # Linha de previsão para períodos futuros
            chart_data.add_trace(go.Scatter(
                x=future_df['Data'],
                y=future_df['Tendencia'],
                mode='lines+markers',
                line=dict(color='#DC143C', width=1.5, dash='dash'),  # Vermelho carmesim tracejado
                marker=dict(symbol='circle', size=8, color='#DC143C'),
                name='Previsão',
                hovertemplate=f'Data: %{{x|%d/%m/%Y}}<br>Previsão: %{{y:.1f}}<extra></extra>'
            ))
              # Comentado para remover a equação de tendência do gráfico
            # chart_data.add_annotation(
            #     x=0.02,
            #     y=0.98,
            #     xref="paper",
            #     yref="paper",
            #     text=trend_equation,
            #     showarrow=False,
            #     font=dict(size=10, color="#666"),
            #     bgcolor="rgba(255, 255, 255, 0.8)",
            #     bordercolor="#DDD",
            #     borderwidth=1,
            #     borderpad=4,
            #     align="left"
            # )
        
        chart_data.update_layout(
            title_text=f'Evolução Temporal ({period_text})',
            title_x=0.5,
            title_font={'family': 'Roboto, sans-serif'},
            xaxis_title='',
            yaxis_title='Volume de Processos',
            hovermode='x unified',
            margin=dict(l=0, r=0, t=40, b=0),
            height=400,
            template='plotly_white',
            paper_bgcolor='white',
            plot_bgcolor='white',
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.15,
                xanchor="center",
                x=0.5
            )
        )

        # Transport Modal (enhanced donut chart)
        df_modal = df['via_transporte_descricao'].value_counts().reset_index()
        df_modal.columns = ['Modal', 'Quantidade']
        
        chart_tipo = go.Figure(data=[go.Pie(
            labels=df_modal['Modal'],
            values=df_modal['Quantidade'],
            hole=.4,
            marker=dict(colors=[
                '#007BFF', '#0056b3', '#28a745', '#6c757d', '#FFFFFF'
            ]),
            textinfo='label+percent',
            hovertemplate='Modal: %{label}<br>Processos: %{value}<br>Percentual: %{percent}<extra></extra>'
        )])
        
        chart_tipo.update_layout(
            title_text='Modal de Transporte',
            title_x=0.5,
            title_font={'family': 'Roboto, sans-serif'},
            showlegend=False,
            margin=dict(l=0, r=0, t=40, b=0),
            height=400,
            paper_bgcolor='white',
            annotations=[dict(text='Total<br>' + str(df_modal['Quantidade'].sum()), 
                           x=0.5, y=0.5, font_size=20, font_family='Roboto, sans-serif', 
                           showarrow=False)]
        )

        # Status by Channel (stacked vertical bars with gradient)
        df_canal = df['diduimp_canal'].value_counts().reset_index()
        df_canal.columns = ['Canal', 'Quantidade']
        
        # Define colors based on channel names
        color_mapping = {
            'VERDE': '#28a745',     # Green
            'AMARELO': '#ffc107',   # Yellow  
            'VERMELHO': '#dc3545'   # Red
        }
        
        chart_canal = go.Figure()
        
        for i, row in df_canal.iterrows():
            # Get color based on channel name, fallback to gray if not found
            color = color_mapping.get(row['Canal'], '#6c757d')
            
            chart_canal.add_trace(go.Bar(
            x=[row['Canal']],
            y=[row['Quantidade']],
            name=row['Canal'],
            marker_color=color,
            text=[row['Quantidade']],
            textposition='auto',
            ))
        
        chart_canal.update_layout(
            title_text='Status por Canal',
            title_x=0.5,
            title_font={'family': 'Roboto, sans-serif'},
            showlegend=True,
            xaxis_title='',
            yaxis_title='Quantidade',
            margin=dict(l=0, r=0, t=40, b=0),
            height=400,
            template='plotly_white',
            paper_bgcolor='white',
            plot_bgcolor='white',
            barmode='group'
        )
    else:
        chart_cliente = chart_data = chart_tipo = chart_canal = None

    # Add last update timestamp
    last_update = datetime.now().strftime('%d/%m/%Y %H:%M')

    # Calculate KPI variations
    # You would need historical data for proper calculations
    # For now using dummy values for demonstration
    variations = {
        'total_var': '+5%',
        'abertos_var': '-2%',
        'novos_var': '+10%',
        'transito_var': '+3%',
        'chegar_var': '+7%'  # Variation for the new "A chegar nessa semana" metric
    }
    
    # Configurar IDs específicos para cada gráfico para facilitar atualização
    chart_configs = {
        'responsive': True,
        'displayModeBar': False,
        'displaylogo': False,
        'scrollZoom': False
    }
          # Prepare chart HTML for initial rendering
    chart_cliente_html = chart_cliente.to_html(full_html=False, include_plotlyjs=False,div_id='chart-cliente', config=chart_configs) if chart_cliente else None
    chart_data_html = chart_data.to_html(full_html=False, include_plotlyjs=False,div_id='chart-data', config=chart_configs) if chart_data else None
    chart_tipo_html = chart_tipo.to_html(full_html=False, include_plotlyjs=False,div_id='chart-tipo', config=chart_configs) if chart_tipo else None
    chart_canal_html = chart_canal.to_html(full_html=False, include_plotlyjs=False,div_id='chart-canal', config=chart_configs) if chart_canal else None
    return render_template('dashboard/index.html',
                         now=datetime.now(),
                         operacoes=data,
                         total_operations=total_operations,
                         processos_abertos=processos_abertos,
                         novos_semana=novos_semana,
                         em_transito=em_transito,
                         a_chegar_semana=a_chegar_semana,
                         last_update=last_update,
                         variations=variations,
                         chart_cliente=chart_cliente_html,
                         chart_data=chart_data_html,
                         chart_tipo=chart_tipo_html,
                         chart_canal=chart_canal_html,
                         user_role=session['user']['role'])

@bp.route('/dashboard/operations')
@login_required
def operations():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    response = supabase.table('importacoes_processos')\
        .select('*')\
        .neq('situacao', 'Despacho Cancelado')\
        .order('data_abertura', desc=True)\
        .range((page-1)*per_page, page*per_page-1)\
        .execute()
        
    operations = response.data
    
    return render_template('dashboard/operations.html',
                         operations=operations,
                         page=page,
                         user_role=session['user']['role'])

@bp.route('/dashboard/refresh')
@login_required
def refresh():
    """Endpoint para atualização AJAX do dashboard"""
    print("DEBUG: /dashboard/refresh endpoint called")
    try:
        # Reutilizar a lógica do index
        user_companies = []
        if session['user']['role'] == 'cliente_unique':
            print(f"DEBUG: User role is {session['user']['role']}, fetching companies")
            agent_response = supabase.table('clientes_agentes').select('empresa').eq('user_id', session['user']['id']).execute()
            print(f"DEBUG: Agent response: {agent_response}")
            if agent_response.data and agent_response.data[0].get('empresa'):
                user_companies = agent_response.data[0].get('empresa')
                print(f"DEBUG: Raw user_companies: {user_companies}")
                if isinstance(user_companies, str):
                    import json
                    try:
                        user_companies = json.loads(user_companies)
                    except:
                        user_companies = [user_companies]
                print(f"DEBUG: Processed user_companies: {user_companies}")        
                print("DEBUG: Building query")
        query = supabase.table('importacoes_processos').select('*').neq('situacao', 'Despacho Cancelado').order('data_abertura', desc=True)
        if user_companies:
            query = query.in_('cliente_cpfcnpj', user_companies)
            print(f"DEBUG: Applied company filter: {user_companies}")
        
        print("DEBUG: Executing query")
        operacoes = query.execute()
        data = operacoes.data if operacoes.data else []
        print(f"DEBUG: Query returned {len(data)} operations")
        
        response_data = {
            'success': True,
            'data': data,
            'last_update': datetime.now().strftime('%d/%m/%Y %H:%M')
        }
        print("DEBUG: Returning successful response")
        return jsonify(response_data)
    except Exception as e:
        print(f"DEBUG: Error in refresh endpoint: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/dashboard/update-data', methods=['POST'])
@login_required
def update_data():
    """Endpoint para atualizar os dados do dashboard a partir do Supabase"""
    try:
        # Atualizar dados do Supabase
        # (Esta chamada apenas simula o processo, os dados já serão os mais recentes do Supabase)
        
        return jsonify({
            'status': 'success',
            'message': 'Dados atualizados com sucesso',
            'timestamp': datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Erro ao atualizar dados: {str(e)}'
        }), 500

@bp.route('/dashboard/chart-data', methods=['GET'])
@login_required
def chart_data():
    """Endpoint para obter dados de gráficos em formato JSON para atualização via AJAX"""
    try:
        # Get user companies if client
        user_companies = []
        if session['user']['role'] == 'cliente_unique':
            agent_response = supabase.table('clientes_agentes').select('empresa').eq('user_id', session['user']['id']).execute()
            if agent_response.data and agent_response.data[0].get('empresa'):
                user_companies = agent_response.data[0].get('empresa')
                if isinstance(user_companies, str):
                    import json
                    try:
                        user_companies = json.loads(user_companies)
                    except:
                        user_companies = [user_companies]        # Build query with client filter - exclude cancelled processes
        query = supabase.table('importacoes_processos').select('*').neq('situacao', 'Despacho Cancelado').order('data_abertura', desc=True)
        if user_companies:
            query = query.in_('cliente_cpfcnpj', user_companies)
        
        operacoes = query.execute()
        data = operacoes.data if operacoes.data else []
        df = pd.DataFrame(data)

        # Calculate metrics
        total_operations = len(df)
        processos_abertos = len(df[df['situacao'] == 'Aberto']) if not df.empty else 0
        
        uma_semana_atras = datetime.now() - timedelta(days=7)
        df['data_abertura'] = pd.to_datetime(df['data_abertura'])
        novos_semana = len(df[df['data_abertura'] > uma_semana_atras]) if not df.empty else 0
        em_transito = len(df[df['carga_status'].notna()]) if not df.empty else 0

        # Calculate new metric: "A chegar nessa semana" (Arriving This Week)
        semana_atual = datetime.now()
        fim_semana = semana_atual + timedelta(days=(6 - semana_atual.weekday()))  # Find the end of current week (Sunday)
        
        # Check if a predicted arrival date field exists in the dataset
        a_chegar_semana = 0
        if 'data_prevista_chegada' in df.columns:
            df['data_prevista_chegada'] = pd.to_datetime(df['data_prevista_chegada'])
            # Filter processes arriving this week (from today until end of week)
            a_chegar_semana = len(df[(df['data_prevista_chegada'] >= semana_atual.date()) & 
                                    (df['data_prevista_chegada'] <= fim_semana.date()) &
                                    (df['situacao'] == 'Aberto')]) if not df.empty else 0
        elif 'eta' in df.columns:  # Alternative field name for estimated arrival
            df['eta'] = pd.to_datetime(df['eta'])
            # Filter processes arriving this week (from today until end of week)
            a_chegar_semana = len(df[(df['eta'] >= semana_atual.date()) & 
                                    (df['eta'] <= fim_semana.date()) &
                                    (df['situacao'] == 'Aberto')]) if not df.empty else 0

        # Calculate KPI variations (dummy values for demonstration)
        variations = {
            'total_var': '+5%',
            'abertos_var': '-2%',
            'novos_var': '+10%',
            'transito_var': '+3%',
            'chegar_var': '+7%'  # Variation for the new "A chegar nessa semana" metric
        }
        
        # KPI data
        kpi_data = {
            'total_operations': total_operations,
            'processos_abertos': processos_abertos,
            'novos_semana': novos_semana,
            'em_transito': em_transito,
            'variations': variations,
            'a_chegar_semana': a_chegar_semana  # New metric
        }

        chart_data = {}
        
        # Create charts
        if not df.empty:
            # Client Distribution (horizontal bar with gradient)
            df_cliente = df['cliente_razaosocial'].value_counts().reset_index()
            df_cliente.columns = ['Cliente', 'Quantidade']
            df_cliente = df_cliente.head(10)  # Limit to top 10 clients
            
            chart_cliente = go.Figure()
            chart_cliente.add_trace(go.Bar(
                x=df_cliente['Quantidade'],
                y=df_cliente['Cliente'],
                orientation='h',
                marker=dict(
                    color=df_cliente['Quantidade'],
                    colorscale=[[0, '#007BFF'], [1, '#0056b3']],
                    showscale=False
                )
            ))
            
            chart_cliente.update_layout(
                title_text='Distribuição por Cliente',
                title_x=0.5,
                title_font={'family': 'Roboto, sans-serif'},
                showlegend=False,
                yaxis={'categoryorder':'total ascending'},
                xaxis_title='Volume de Processos',
                yaxis_title='',
                margin=dict(l=0, r=0, t=40, b=0),
                height=400,
                template='plotly_white',
                paper_bgcolor='white',
                plot_bgcolor='white'
            )
              # Temporal Evolution - adaptativo entre diário e semanal com base no volume de registros
            
            # Determinar o tipo de visualização baseado no volume de dados
            show_daily = len(df) < 30  # Mostrar visualização diária se tiver menos de 30 registros
            
            if show_daily:
                # Agrupamento diário
                df['date'] = df['data_abertura'].dt.date
                df_time = df.groupby('date').size().reset_index(name='Quantidade')
                df_time.columns = ['Data', 'Quantidade']
                df_time['Data'] = pd.to_datetime(df_time['Data'])
                
                # Ordenar por data
                df_time = df_time.sort_values('Data')
                
                # Se houver menos de 7 registros, preencher os dias intermediários
                if len(df_time) < 7:
                    date_range = pd.date_range(start=df_time['Data'].min(), end=df_time['Data'].max())
                    date_df = pd.DataFrame({'Data': date_range})
                    df_time = pd.merge(date_df, df_time, on='Data', how='left').fillna(0)
                
                # Calcular média móvel de 3 dias
                window_size = min(3, len(df_time))
                df_time['Media_Movel'] = df_time['Quantidade'].rolling(window=window_size).mean()
                
                period_text = "Diária"
                hover_format = 'Data: %{x|%d/%m/%Y}<br>Processos: %{y}<extra></extra>'
                mm_name = 'Média 3 dias'
            else:
                # Agrupamento semanal (código original)
                df['week_year'] = df['data_abertura'].dt.strftime('%Y-%U')
                df_time = df.groupby('week_year').size().reset_index(name='Quantidade')
                df_time.columns = ['Semana', 'Quantidade']
                
                # Converter week_year de volta para datetime para melhor visualização
                df_time['Data'] = pd.to_datetime([f"{w.split('-')[0]}-W{w.split('-')[1]}-1" for w in df_time['Semana']], format='%Y-W%W-%w')
                
                # Ordenar por data
                df_time = df_time.sort_values('Data')
                
                # Calcular média móvel de 4 semanas
                df_time['Media_Movel'] = df_time['Quantidade'].rolling(window=4).mean()
                
                period_text = "Semanal"
                hover_format = 'Semana: %{x|%d/%m/%Y}<br>Processos: %{y}<extra></extra>'
                mm_name = 'Média 4 semanas'
            
            # Preparar dados para regressão linear e previsão
            if len(df_time) > 1:
                # Criar índices numéricos para x
                df_time['idx'] = range(len(df_time))
                
                # Filtrar pontos nulos para regressão
                regression_data = df_time.dropna()
                
                if len(regression_data) > 1:                # Calcular regressão linear
                    slope, intercept, r_value, p_value, std_err = stats.linregress(
                        regression_data['idx'], regression_data['Quantidade']
                    )
                    
                    # Criar linha de tendência
                    df_time['Tendencia'] = intercept + slope * df_time['idx']
                    
                    # Adicionar pontos de previsão futura (3 períodos)
                    future_periods = 3
                    future_indices = range(len(df_time), len(df_time) + future_periods)
                    future_dates = pd.date_range(start=df_time['Data'].max(), periods=future_periods+1, freq='W' if not show_daily else 'D')[1:]
                    
                    future_df = pd.DataFrame({
                        'Data': future_dates,
                        'idx': future_indices
                    })
                    future_df['Tendencia'] = intercept + slope * future_df['idx']
                    
                    # Texto da equação da tendência
                    trend_equation = f"y = {intercept:.2f} + {slope:.2f}x (R² = {r_value**2:.2f})"
                    has_trend = True
                else:
                    has_trend = False
            else:
                has_trend = False
            
            chart_data_obj = go.Figure()
            
            # Área com gradiente
            chart_data_obj.add_trace(go.Scatter(
                x=df_time['Data'],
                y=df_time['Quantidade'],
                fill='tozeroy',
                mode='lines',
                line=dict(width=0.5, color='#007BFF'),
                fillcolor='rgba(0, 123, 255, 0.2)',
                name=f'Volume {period_text}',
                hovertemplate=hover_format
            ))
            
            # Linha de média móvel
            chart_data_obj.add_trace(go.Scatter(
                x=df_time['Data'],
                y=df_time['Media_Movel'],
                mode='lines',
                line=dict(color='#0056b3', width=2, dash='dot'),
                name=mm_name,
                hovertemplate=f'Data: %{{x|%d/%m/%Y}}<br>Média: %{{y:.1f}}<extra></extra>'
            ))
            
            # Adicionar linha de tendência e previsão se disponível
            if has_trend:
                # Linha de tendência para dados existentes
                chart_data_obj.add_trace(go.Scatter(
                    x=df_time['Data'],
                    y=df_time['Tendencia'],
                    mode='lines',
                    line=dict(color='#DC143C', width=1.5),  # Vermelho carmesim
                    name='Tendência',
                    hovertemplate=f'Data: %{{x|%d/%m/%Y}}<br>Tendência: %{{y:.1f}}<extra></extra>'
                ))
                
                # Linha de previsão para períodos futuros
                chart_data_obj.add_trace(go.Scatter(
                    x=future_df['Data'],
                    y=future_df['Tendencia'],
                    mode='lines+markers',
                    line=dict(color='#DC143C', width=1.5, dash='dash'),  # Vermelho carmesim tracejado
                    marker=dict(symbol='circle', size=8, color='#DC143C'),
                    name='Previsão',
                    hovertemplate=f'Data: %{{x|%d/%m/%Y}}<br>Previsão: %{{y:.1f}}<extra></extra>'
                ))
                
                # Adicionar anotação com a equação da tendência
                chart_data_obj.add_annotation(
                    x=0.02,
                    y=0.98,
                    xref="paper",
                    yref="paper",
                    text=trend_equation,
                    showarrow=False,
                    font=dict(size=10, color="#666"),
                    bgcolor="rgba(255, 255, 255, 0.8)",
                    bordercolor="#DDD",
                    borderwidth=1,
                    borderpad=4,
                    align="left"
                )
            
            chart_data_obj.update_layout(
                title_text=f'Evolução Temporal ({period_text})',
                title_x=0.5,
                title_font={'family': 'Roboto, sans-serif'},
                xaxis_title='',
                yaxis_title='Volume de Processos',
                hovermode='x unified',
                margin=dict(l=0, r=0, t=40, b=0),
                height=400,
                template='plotly_white',
                paper_bgcolor='white',
                plot_bgcolor='white',
                legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.15,
                xanchor="center",
                x=0.5
                )
            )

            # Transport Modal (enhanced donut chart)
            df_modal = df['via_transporte_descricao'].value_counts().reset_index()
            df_modal.columns = ['Modal', 'Quantidade']
            
            chart_tipo = go.Figure(data=[go.Pie(
                labels=df_modal['Modal'],
                values=df_modal['Quantidade'],
                hole=.4,
                marker=dict(colors=[
                    '#007BFF', '#0056b3', '#28a745', '#6c757d', '#FFFFFF'
                ]),
                textinfo='label+percent',
                hovertemplate='Modal: %{label}<br>Processos: %{value}<br>Percentual: %{percent}<extra></extra>'
            )])
            
            chart_tipo.update_layout(
                title_text='Modal de Transporte',
                title_x=0.5,
                title_font={'family': 'Roboto, sans-serif'},
                showlegend=False,
                margin=dict(l=0, r=0, t=40, b=0),
                height=400,
                paper_bgcolor='white',
                annotations=[dict(text='Total<br>' + str(df_modal['Quantidade'].sum()), 
                               x=0.5, y=0.5, font_size=20, font_family='Roboto, sans-serif', 
                               showarrow=False)]
            )

            # Status by Channel (stacked vertical bars with gradient)
            df_canal = df['diduimp_canal'].value_counts().reset_index()
            df_canal.columns = ['Canal', 'Quantidade']
            
            colors = ['#28a745', '#007BFF', '#6c757d', '#0056b3']  # Different colors for different statuses
            
            chart_canal = go.Figure()
            
            for i, row in df_canal.iterrows():
                chart_canal.add_trace(go.Bar(
                    x=[row['Canal']],
                    y=[row['Quantidade']],
                    name=row['Canal'],
                    marker_color=colors[i % len(colors)],
                    text=[row['Quantidade']],
                    textposition='auto',
                ))
            chart_canal.update_layout(
                title_text='Status por Canal',
                title_x=0.5,
                title_font={'family': 'Roboto, sans-serif'},
                showlegend=True,
                xaxis_title='',
                yaxis_title='Quantidade',
                margin=dict(l=0, r=0, t=40, b=0),
                height=400,
                template='plotly_white',
                paper_bgcolor='white',
                plot_bgcolor='white',
                barmode='group'
            )
            
            # Add charts to response - with proper config for JavaScript interaction
            chart_configs = {
                'responsive': True,
                'displayModeBar': False,
                'displaylogo': False,
                'scrollZoom': False
            }
              # Para cada gráfico, enviaremos tanto o HTML quanto os dados em JSON
            # Isso permitirá que o JavaScript use os dados diretamente para atualização
            chart_data = {
                'chart_cliente': {
                    'html': chart_cliente.to_html(full_html=False, include_plotlyjs=False, 
                                div_id='chart-cliente', config=chart_configs),
                    'data': chart_cliente.to_json(),
                    'id': 'chart-cliente'
                },
                'chart_data': {
                    'html': chart_data_obj.to_html(full_html=False, include_plotlyjs=False, 
                                div_id='chart-data', config=chart_configs),
                    'data': chart_data_obj.to_json(),
                    'id': 'chart-data'
                },
                'chart_tipo': {
                    'html': chart_tipo.to_html(full_html=False, include_plotlyjs=False, 
                                div_id='chart-tipo', config=chart_configs),
                    'data': chart_tipo.to_json(),
                    'id': 'chart-tipo'
                },
                'chart_canal': {
                    'html': chart_canal.to_html(full_html=False, include_plotlyjs=False, 
                                div_id='chart-canal', config=chart_configs),
                    'data': chart_canal.to_json(),
                    'id': 'chart-canal'
                }
            }
        
        # Add last update timestamp
        last_update = datetime.now().strftime('%d/%m/%Y %H:%M')
        
        return jsonify({
            'status': 'success',
            'charts': chart_data,
            'kpis': kpi_data,
            'last_update': last_update
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Erro ao gerar dados dos gráficos: {str(e)}'
        }), 500