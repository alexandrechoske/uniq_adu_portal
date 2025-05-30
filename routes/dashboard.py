from flask import Blueprint, render_template, session, request, jsonify
from extensions import supabase
from routes.auth import login_required, role_required
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta

bp = Blueprint('dashboard', __name__)

@bp.route('/dashboard')
@login_required
def index():
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
    query = supabase.table('importacoes_processos').select('*').order('data_abertura', desc=True)
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
        # Temporal Evolution (area chart with gradient and moving average)
        df['week_year'] = df['data_abertura'].dt.strftime('%Y-%U')
        df_week = df.groupby('week_year').size().reset_index(name='Quantidade')
        df_week.columns = ['Semana', 'Quantidade']
        
        # Convert week_year back to datetime for better x-axis display
        df_week['Semana'] = pd.to_datetime([f"{w.split('-')[0]}-W{w.split('-')[1]}-1" for w in df_week['Semana']], format='%Y-W%W-%w')
        
        # Calculate 4-week moving average (monthly trend)
        df_week['Media_Movel'] = df_week['Quantidade'].rolling(window=4).mean()
        
        chart_data = go.Figure()
        
        # Area with gradient
        chart_data.add_trace(go.Scatter(
            x=df_week['Semana'],
            y=df_week['Quantidade'],
            fill='tozeroy',
            mode='lines',
            line=dict(width=0.5, color='#007BFF'),
            fillcolor='rgba(0, 123, 255, 0.2)',
            name='Volume Semanal',
            hovertemplate='Semana: %{x|%d/%m/%Y}<br>Processos: %{y}<extra></extra>'
        ))
        
        # Moving average line
        chart_data.add_trace(go.Scatter(
            x=df_week['Semana'],
            y=df_week['Media_Movel'],
            mode='lines',
            line=dict(color='#0056b3', width=2, dash='dot'),
            name='Média 4 semanas',
            hovertemplate='Semana: %{x|%d/%m/%Y}<br>Média: %{y:.1f}<extra></extra>'
        ))
        
        chart_data.update_layout(
            title_text='Evolução Temporal (Semanal)',
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
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
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
        'transito_var': '+3%'
    }    # Configurar IDs específicos para cada gráfico para facilitar atualização
    chart_configs = {
        'responsive': True,
        'displayModeBar': False,
        'displaylogo': False,
        'scrollZoom': False
    }
          # Prepare chart HTML for initial rendering
    chart_cliente_html = chart_cliente.to_html(full_html=False, include_plotlyjs=False, 
                          div_id='chart-cliente', config=chart_configs) if chart_cliente else None
    chart_data_html = chart_data.to_html(full_html=False, include_plotlyjs=False,
                          div_id='chart-data', config=chart_configs) if chart_data else None
    chart_tipo_html = chart_tipo.to_html(full_html=False, include_plotlyjs=False,
                          div_id='chart-tipo', config=chart_configs) if chart_tipo else None
    chart_canal_html = chart_canal.to_html(full_html=False, include_plotlyjs=False,
                          div_id='chart-canal', config=chart_configs) if chart_canal else None
                         
    return render_template('dashboard/index.html',
                         now=datetime.now(),
                         operacoes=data,
                         total_operations=total_operations,
                         processos_abertos=processos_abertos,
                         novos_semana=novos_semana,
                         em_transito=em_transito,
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
        query = supabase.table('importacoes_processos').select('*').order('data_abertura', desc=True)
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
                        user_companies = [user_companies]

        # Build query with client filter
        query = supabase.table('importacoes_processos').select('*').order('data_abertura', desc=True)
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

        # Calculate KPI variations (dummy values for demonstration)
        variations = {
            'total_var': '+5%',
            'abertos_var': '-2%',
            'novos_var': '+10%',
            'transito_var': '+3%'
        }
        
        # KPI data
        kpi_data = {
            'total_operations': total_operations,
            'processos_abertos': processos_abertos,
            'novos_semana': novos_semana,
            'em_transito': em_transito,
            'variations': variations
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
            
            # Temporal Evolution (area chart with gradient and moving average)
            df['week_year'] = df['data_abertura'].dt.strftime('%Y-%U')
            df_week = df.groupby('week_year').size().reset_index(name='Quantidade')
            df_week.columns = ['Semana', 'Quantidade']
            
            # Convert week_year back to datetime for better x-axis display
            df_week['Semana'] = pd.to_datetime([f"{w.split('-')[0]}-W{w.split('-')[1]}-1" for w in df_week['Semana']], format='%Y-W%W-%w')
            
            # Calculate 4-week moving average (monthly trend)
            df_week['Media_Movel'] = df_week['Quantidade'].rolling(window=4).mean()
            
            chart_data_obj = go.Figure()
            
            # Area with gradient
            chart_data_obj.add_trace(go.Scatter(
                x=df_week['Semana'],
                y=df_week['Quantidade'],
                fill='tozeroy',
                mode='lines',
                line=dict(width=0.5, color='#007BFF'),
                fillcolor='rgba(0, 123, 255, 0.2)',
                name='Volume Semanal',
                hovertemplate='Semana: %{x|%d/%m/%Y}<br>Processos: %{y}<extra></extra>'
            ))
            
            # Moving average line
            chart_data_obj.add_trace(go.Scatter(
                x=df_week['Semana'],
                y=df_week['Media_Movel'],
                mode='lines',
                line=dict(color='#0056b3', width=2, dash='dot'),
                name='Média 4 semanas',
                hovertemplate='Semana: %{x|%d/%m/%Y}<br>Média: %{y:.1f}<extra></extra>'
            ))
            
            chart_data_obj.update_layout(
                title_text='Evolução Temporal (Semanal)',
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
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
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