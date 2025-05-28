from flask import Blueprint, render_template, session, request, jsonify
from extensions import supabase
from routes.auth import login_required
import pandas as pd
from datetime import datetime
import json

bp = Blueprint('onepage', __name__, url_prefix='/onepage')

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

@bp.route('/')
@login_required
def index():
    """OnePage dashboard view"""
    if session['user']['role'] not in ['cliente_unique', 'interno_unique']:
        return render_template('errors/401.html'), 401

    # Get user's companies and selected filter
    user_companies = get_user_companies()
    selected_company = request.args.get('empresa')

    # Build query with proper filters
    query = supabase.table('importacoes_processos').select('*').order('data_embarque', desc=False)
    
    if session['user']['role'] == 'cliente_unique':
        if user_companies:
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
            'aereo': len(df[df['via_transporte_descricao'] == 'Aéreo']),
            'terrestre': len(df[df['via_transporte_descricao'] == 'Terrestre']),
            'maritimo': len(df[df['via_transporte_descricao'] == 'Marítimo']),
            'aguardando_chegada': len(df[df['carga_status'] == 'Aguardando Chegada']),
            'aguardando_embarque': len(df[df['carga_status'] == 'Aguardando Embarque']),
            'di_registrada': len(df[df['status_doc'] == 'Registrada'])
        }

        # Prepare table data
        # Convert date columns and handle NaT, replacing with " "
        date_columns = ['data_embarque', 'data_chegada'] # Add other date columns if necessary
        for col in date_columns:
            # Convert to datetime, errors='coerce' will turn invalid parsing into NaT (Not a Time)
            df[col] = pd.to_datetime(df[col], errors='coerce')
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

    return render_template(
        'onepage/index.html',
        kpis=kpis,
        table_data=table_data,
        companies=available_companies,
        selected_company=selected_company,
        user_role=session['user']['role']
    )
