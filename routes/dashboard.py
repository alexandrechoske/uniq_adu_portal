from flask import Blueprint, render_template, session, request
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
    try:
        # Initialize query for importacoes_processos
        query = supabase.table('importacoes_processos').select('*')        # Add company filtering for cliente_unique users
        if session.get('user', {}).get('role') == 'cliente_unique':
            # Get user's companies from clientes_agentes table
            user_id = session.get('user', {}).get('id')
            user_companies_response = supabase.table('clientes_agentes')\
                .select('empresa')\
                .eq('user_id', user_id)\
                .execute()
            
            # Flatten the array of companies from all records
            user_companies = []
            if user_companies_response.data:
                for record in user_companies_response.data:
                    if record.get('empresa'):
                        # Handle both string and array formats
                        companies = record['empresa']
                        if isinstance(companies, str):
                            try:
                                companies = eval(companies)  # Handle string format ["company1", "company2"]
                            except:
                                companies = [companies]  # Handle single string format
                        user_companies.extend(companies)
            
            user_companies = list(set(user_companies))  # Remove duplicates
            
            if user_companies:
                # Filter by any of the user's associated companies
                query = query.in_('cliente_cpfcnpj', user_companies)

        # Execute query with ordering and limit
        operacoes = query.order('data_abertura', desc=True).limit(1000).execute()
        data = operacoes.data if operacoes.data else []

        # If no data from importacoes_processos, fallback to operacoes_aduaneiras        # Even if there's no data, we don't fallback to operacoes_aduaneiras since it doesn't exist
        # Instead, we'll just work with an empty dataset
        if not data:
            data = []

        df = pd.DataFrame(data)

        # Calcular métricas
        total_operations = len(df)
        processos_abertos = len(df[df['situacao'] == 'Aberto']) if not df.empty else 0
        
        uma_semana_atras = datetime.now() - timedelta(days=7)
        df['data_abertura'] = pd.to_datetime(df['data_abertura'])
        novos_semana = len(df[df['data_abertura'] > uma_semana_atras]) if not df.empty else 0
        em_transito = len(df[df['carga_status'].notna()]) if not df.empty else 0

        # Criar gráficos
        if not df.empty:
            # Distribuição por Cliente (horizontal bar com gradiente)
            cliente_col = 'cliente_razaosocial' if 'cliente_razaosocial' in df.columns else 'cliente_razao_social'
            df_cliente = df[cliente_col].value_counts().reset_index()
            df_cliente.columns = ['Cliente', 'Quantidade']
            df_cliente = df_cliente.head(10)  # Limitar aos top 10 clientes
            
            chart_cliente = go.Figure()
            chart_cliente.add_trace(go.Bar(
                x=df_cliente['Quantidade'],
                y=df_cliente['Cliente'],
                orientation='h',
                marker=dict(
                    color=df_cliente['Quantidade'],
                    colorscale='Blues',
                    showscale=False
                )
            ))
            
            chart_cliente.update_layout(
                title_text='Distribuição por Cliente',
                title_x=0.5,
                showlegend=False,
                yaxis={'categoryorder':'total ascending'},
                xaxis_title='Volume de Processos',
                yaxis_title='',
                margin=dict(l=0, r=0, t=40, b=0),
                height=400,
                template='plotly_white'
            )

            # Evolução Temporal (area chart com gradiente e média móvel)
            df['data_abertura_dia'] = df['data_abertura'].dt.date
            df_date = df.groupby('data_abertura_dia').size().reset_index(name='Quantidade')
            df_date.columns = ['Data', 'Quantidade']
            
            # Calcular média móvel de 7 dias
            df_date['Media_Movel'] = df_date['Quantidade'].rolling(window=7).mean()
            
            chart_data = go.Figure()
            
            # Área com gradiente
            chart_data.add_trace(go.Scatter(
                x=df_date['Data'],
                y=df_date['Quantidade'],
                fill='tozeroy',
                mode='lines',
                line=dict(width=0.5, color='rgb(73, 119, 191)'),
                fillcolor='rgba(73, 119, 191, 0.2)',
                name='Volume Diário',
                hovertemplate='Data: %{x}<br>Processos: %{y}<extra></extra>'
            ))
            
            # Linha de média móvel
            chart_data.add_trace(go.Scatter(
                x=df_date['Data'],
                y=df_date['Media_Movel'],
                mode='lines',
                line=dict(color='rgb(23, 69, 141)', width=2, dash='dot'),
                name='Média 7 dias',
                hovertemplate='Data: %{x}<br>Média: %{y:.1f}<extra></extra>'
            ))
            
            chart_data.update_layout(
                title_text='Evolução Temporal',
                title_x=0.5,
                xaxis_title='',
                yaxis_title='Volume de Processos',
                hovermode='x unified',
                margin=dict(l=0, r=0, t=40, b=0),
                height=400,
                template='plotly_white',
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                )
            )

            # Modal de Transporte (donut chart aprimorado)
            df_modal = df['via_transporte_descricao'].value_counts().reset_index()
            df_modal.columns = ['Modal', 'Quantidade']
            
            chart_tipo = go.Figure(data=[go.Pie(
                labels=df_modal['Modal'],
                values=df_modal['Quantidade'],
                hole=.4,
                marker=dict(colors=px.colors.sequential.Blues),
                textinfo='label+percent',
                hovertemplate='Modal: %{label}<br>Processos: %{value}<br>Percentual: %{percent}<extra></extra>'
            )])
            
            chart_tipo.update_layout(
                title_text='Modal de Transporte',
                title_x=0.5,
                showlegend=False,
                margin=dict(l=0, r=0, t=40, b=0),
                height=400,
                annotations=[dict(text='Total<br>' + str(df_modal['Quantidade'].sum()), x=0.5, y=0.5, font_size=20, showarrow=False)]
            )

            # Status por Canal (barras verticais com cores graduais)
            df_canal = df['carga_status'].value_counts().reset_index()
            df_canal.columns = ['Canal', 'Quantidade']
            
            chart_canal = go.Figure(data=[go.Bar(
                x=df_canal['Canal'],
                y=df_canal['Quantidade'],
                marker=dict(
                    color=df_canal['Quantidade'],
                    colorscale='Blues',
                    showscale=False
                ),
                text=df_canal['Quantidade'],
                textposition='auto',
            )])
            
            chart_canal.update_layout(
                title_text='Status por Canal',
                title_x=0.5,
                showlegend=False,
                xaxis_title='',
                yaxis_title='Quantidade',
                margin=dict(l=0, r=0, t=40, b=0),
                height=400,
                template='plotly_white'
            )
        else:
            chart_cliente = chart_data = chart_tipo = chart_canal = None

        # Adicionar timestamp de última atualização
        last_update = datetime.now().strftime('%d/%m/%Y %H:%M')

        return render_template('dashboard/index.html',
                             now=datetime.now(),
                             operacoes=data,
                             total_operations=total_operations,
                             processos_abertos=processos_abertos,
                             novos_semana=novos_semana,
                             em_transito=em_transito,
                             last_update=last_update,
                             chart_cliente=chart_cliente.to_html(full_html=False) if chart_cliente else None,
                             chart_data=chart_data.to_html(full_html=False) if chart_data else None,
                             chart_tipo=chart_tipo.to_html(full_html=False) if chart_tipo else None,
                             chart_canal=chart_canal.to_html(full_html=False) if chart_canal else None,
                             user_role=session['user']['role'])
    except Exception as e:
        # Log the exception (logging setup not shown here)
        print(f"Error in dashboard index: {e}")
        return render_template('dashboard/index.html', error=str(e))