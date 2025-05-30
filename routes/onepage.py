from flask import Blueprint, render_template, session, request, jsonify
from extensions import supabase
from routes.auth import login_required
import pandas as pd
from datetime import datetime
import json
import requests

bp = Blueprint('onepage', __name__, url_prefix='/onepage')

def update_importacoes_processos():
    try:
        response = requests.post(
            'https://ixytthtngeifjumvbuwe.supabase.co/functions/v1/att_importacoes-processos',
            headers={
                'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml4eXR0aHRuZ2VpZmp1bXZidXdlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDc5MjIwMDQsImV4cCI6MjA2MzQ5ODAwNH0.matnofV1H9hi2bEQGak6fo-RtmJIOyU455fcgsKbPfk',
                'Content-Type': 'application/json'
            },
            json={'name': 'Functions'}
        )
        return response.status_code == 200
    except:
        return False

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

def get_currencies():
    """Get latest USD and EUR exchange rates"""
    try:
        # Use the Banco Central do Brasil API or a public currency API
        response = requests.get('https://api.exchangerate-api.com/v4/latest/BRL')
        if response.status_code == 200:
            data = response.json()
            # We want BRL to USD/EUR rates (how many USD/EUR per 1 BRL)
            # The API returns USD/EUR to BRL, so we take the inverse
            usd_rate = 1 / data['rates']['USD']
            eur_rate = 1 / data['rates']['EUR']
            return {
                'USD': round(usd_rate, 4),
                'EUR': round(eur_rate, 4),
                'last_updated': data['date']
            }
    except Exception as e:
        print(f"Error fetching currency rates: {str(e)}")
    
    # Return default values if API fails
    return {
        'USD': 0.00,
        'EUR': 0.00,
        'last_updated': datetime.now().strftime('%Y-%m-%d')
    }

@bp.route('/')
@login_required
def index():
    """OnePage dashboard view"""
    if session['user']['role'] not in ['cliente_unique', 'interno_unique']:
        return render_template('errors/401.html'), 401

    # Get user's companies and selected filter
    user_companies = get_user_companies()
    selected_company = request.args.get('empresa')
    
    # Timestamp da última atualização
    last_update = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    
    # Get currency exchange rates
    currencies = get_currencies()

    # Build initial query without sorting (will sort after date conversion)
    query = supabase.table('importacoes_processos').select('*')

    # Apply filters based on user role and selected company
    if session['user']['role'] == 'cliente_unique':
        # If cliente_unique user has no companies, return empty data immediately
        if not user_companies:
            kpis = {
                'total': 0,
                'aereo': 0,
                'terrestre': 0,
                'maritimo': 0,
                'aguardando_chegada': 0,
                'aguardando_embarque': 0,
                'di_registrada': 0
            }            
            table_data = []
            
            available_companies = [] # No companies to filter if user has none
            return render_template(
                'onepage/index.html',
                kpis=kpis,
                table_data=table_data,
                companies=available_companies,
                selected_company=selected_company,
                user_role=session['user']['role'],
                last_update=last_update,
                currencies=currencies
            )

        # Filter by user's companies
        if selected_company and selected_company in user_companies:
            query = query.eq('cliente_cpfcnpj', selected_company)
        else:
            query = query.in_('cliente_cpfcnpj', user_companies)

    elif selected_company:  # interno_unique with filter
        query = query.eq('cliente_cpfcnpj', selected_company)

    # Execute query and process data
    result = query.execute()
    df = pd.DataFrame(result.data if result.data else [])

    if df.empty:
        kpis = {
            'total': 0,
            'aereo': 0,
            'terrestre': 0,
            'maritimo': 0,
            'aguardando_chegada': 0,
            'aguardando_embarque': 0,
            'di_registrada': 0
        }
        table_data = []
    else:
        # Calculate KPIs
        kpis = {
            'total': len(df),
            'aereo': len(df[df['via_transporte_descricao'] == 'AEREA']),
            'terrestre': len(df[df['via_transporte_descricao'] == 'TERRESTRE']),
            'maritimo': len(df[df['via_transporte_descricao'] == 'MARITIMA']),
            'aguardando_chegada': len(df[df['carga_status'] == '2 - Em Trânsito']),
            'aguardando_embarque': len(df[df['carga_status'] == '1 - Aguardando Embarque']),
            'di_registrada': len(df[df['status_doc'] == '3 - Desembarcada'])
        }

        # Prepare table data
        # First convert dates to datetime for proper sorting
        date_columns = ['data_embarque', 'data_chegada'] # Add other date columns if necessary
        for col in date_columns:
            # Convert to datetime, errors='coerce' will turn invalid parsing into NaT (Not a Time)
            df[col] = pd.to_datetime(df[col], errors='coerce')
        
        # Sort by data_embarque (most recent first)
        df = df.sort_values(by='data_embarque', ascending=False, na_position='last')
        
        # Format dates for display
        for col in date_columns:
            # Format valid dates and replace NaT with " "
            df[col] = df[col].apply(lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) else " ")

        table_data = df.to_dict('records')

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

    # Get currency rates
    currency_rates = get_currencies()

    return render_template(
        'onepage/index.html',
        kpis=kpis,
        table_data=table_data,
        companies=available_companies,        
        selected_company=selected_company,
        user_role=session['user']['role'],
        last_update=last_update,
        currencies=currencies
    )
    
@bp.route('/update-data', methods=['POST'])
@login_required
def update_data():
    """Endpoint para atualizar os dados de importações"""
    if session['user']['role'] not in ['cliente_unique', 'interno_unique']:
        return jsonify({
            'status': 'error',
            'message': 'Acesso não autorizado'
        }), 401
        
    # Chamar a função de atualização
    update_success = update_importacoes_processos()
    
    if update_success:
        return jsonify({
            'status': 'success',
            'message': 'Dados atualizados com sucesso!',
            'timestamp': datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        })
    else:
        return jsonify({
            'status': 'error',
            'message': 'Erro ao atualizar os dados'
        }), 500
        
@bp.route('/page-data', methods=['GET'])
@login_required
def page_data():
    """Endpoint para obter dados da página em formato JSON para atualização via AJAX"""
    try:
        # Get user's companies and selected filter
        user_companies = get_user_companies()
        selected_company = request.args.get('empresa')
        
        # Timestamp da última atualização
        last_update = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        
        # Get currency exchange rates
        currencies = get_currencies()

        # Build initial query without sorting (will sort after date conversion)
        query = supabase.table('importacoes_processos').select('*')

        # Apply filters based on user role and selected company
        if session['user']['role'] == 'cliente_unique':
            # If cliente_unique user has no companies, return empty data immediately
            if not user_companies:
                kpis = {
                    'total': 0,
                    'aereo': 0,
                    'terrestre': 0,
                    'maritimo': 0,
                    'aguardando_chegada': 0,
                    'aguardando_embarque': 0,
                    'di_registrada': 0
                }                
                table_data = []
                
                return jsonify({
                    'status': 'success',
                    'kpis': kpis,
                    'table_data': table_data,
                    'last_update': last_update
                })

            # Filter by user's companies
            if selected_company and selected_company in user_companies:
                query = query.eq('cliente_cpfcnpj', selected_company)
            else:
                query = query.in_('cliente_cpfcnpj', user_companies)

        elif selected_company:  # interno_unique with filter
            query = query.eq('cliente_cpfcnpj', selected_company)

        # Execute query and process data
        result = query.execute()
        df = pd.DataFrame(result.data if result.data else [])

        if df.empty:
            kpis = {
                'total': 0,
                'aereo': 0,
                'terrestre': 0,
                'maritimo': 0,
                'aguardando_chegada': 0,
                'aguardando_embarque': 0,
                'di_registrada': 0
            }
            table_data = []
        else:
            # Calculate KPIs
            kpis = {
                'total': len(df),
                'aereo': len(df[df['via_transporte_descricao'] == 'AEREA']),
                'terrestre': len(df[df['via_transporte_descricao'] == 'TERRESTRE']),
                'maritimo': len(df[df['via_transporte_descricao'] == 'MARITIMA']),
                'aguardando_chegada': len(df[df['carga_status'] == '2 - Em Trânsito']),
                'aguardando_embarque': len(df[df['carga_status'] == '1 - Aguardando Embarque']),
                'di_registrada': len(df[df['status_doc'] == '3 - Desembarcada'])
            }

            # Prepare table data
            # First convert dates to datetime for proper sorting
            date_columns = ['data_embarque', 'data_chegada'] # Add other date columns if necessary
            for col in date_columns:
                # Convert to datetime, errors='coerce' will turn invalid parsing into NaT (Not a Time)
                df[col] = pd.to_datetime(df[col], errors='coerce')
            
            # Sort by data_embarque (most recent first)
            df = df.sort_values(by='data_embarque', ascending=False, na_position='last')
            
            # Format dates for display
            for col in date_columns:
                # Format valid dates and replace NaT with " "
                df[col] = df[col].apply(lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) else " ")

            table_data = df.to_dict('records')
            
        return jsonify({
            'status': 'success',
            'kpis': kpis,
            'table_data': table_data,
            'last_update': last_update,
            'currencies': currencies
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Erro ao gerar dados da página: {str(e)}'
        }), 500
