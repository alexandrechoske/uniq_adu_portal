from flask import Blueprint, request, jsonify, session
from extensions import supabase, supabase_admin
from routes.auth import login_required
import pandas as pd
from datetime import datetime
import requests
import logging

# Configurar logging
logger = logging.getLogger(__name__)

bp = Blueprint('api', __name__)

def get_currencies():
    """Get latest USD and EUR exchange rates"""
    try:
        # Use the Banco Central do Brasil API or a public currency API
        response = requests.get('https://api.exchangerate-api.com/v4/latest/BRL', timeout=10)
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
        logger.error(f"Error fetching currency rates: {str(e)}")
    
    # Return default values if API fails
    return {
        'USD': 0.00,
        'EUR': 0.00,
        'last_updated': datetime.now().strftime('%Y-%m-%d')
    }

def get_user_companies(user_data):
    """Get companies that the user has access to"""
    if user_data['role'] == 'cliente_unique':
        try:
            agent_response = supabase.table('clientes_agentes').select('empresa').eq('user_id', user_data['id']).execute()
            if agent_response.data and agent_response.data[0].get('empresa'):
                companies = agent_response.data[0].get('empresa')
                if isinstance(companies, str):
                    companies = [companies]
                return companies
        except Exception as e:
            logger.error(f"Erro ao buscar empresas do usuário: {str(e)}")
    return []

@bp.route('/global-data')
@login_required
def global_data():
    """
    Endpoint que retorna todos os dados globais da aplicação em uma única requisição
    Inclui: importações, usuários, estatísticas do dashboard, câmbio, etc.
    """
    try:
        logger.info("Buscando dados globais da aplicação")
        
        user_data = session.get('user')
        user_role = user_data.get('role')
        
        # Inicializar dados de retorno
        global_data = {
            'importacoes': [],
            'usuarios': [],
            'dashboard_stats': {},
            'currencies': {},
            'companies': [],
            'user_companies': []
        }
        
        # 1. Buscar importações/processos
        try:
            logger.info("Buscando dados de importações...")
            # Filtrar para excluir registros com "Despacho Cancelado"
            query = supabase.table('importacoes_processos').select('*').neq('situacao', 'Despacho Cancelado')
            
            # Aplicar filtros baseados no role do usuário
            if user_role == 'cliente_unique':
                user_companies = get_user_companies(user_data)
                global_data['user_companies'] = user_companies
                
                if user_companies:
                    # Filtrar por empresas do usuário
                    query = query.in_('cliente_cpfcnpj', user_companies)
                else:
                    # Se não tem empresas, retornar dados vazios para este usuário
                    query = query.eq('cliente_cpfcnpj', 'NENHUMA_EMPRESA_ENCONTRADA')
            
            result = query.execute()
            importacoes_data = result.data if result.data else []
            
            # Processar dados de importações
            if importacoes_data:
                df = pd.DataFrame(importacoes_data)
                
                # Converter datas para datetime para ordenação adequada
                date_columns = ['data_embarque', 'data_chegada']
                for col in date_columns:
                    if col in df.columns:
                        df[col] = pd.to_datetime(df[col], errors='coerce', dayfirst=True)
                
                # Ordenar por data_embarque (mais recente primeiro)
                if 'data_embarque' in df.columns:
                    df = df.sort_values('data_embarque', ascending=False, na_position='last')
                
                # Converter de volta para strings para JSON
                for col in date_columns:
                    if col in df.columns:
                        df[col] = df[col].dt.strftime('%d/%m/%Y').fillna('')
                
                global_data['importacoes'] = df.to_dict('records')
                
                # Calcular estatísticas
                global_data['dashboard_stats'] = {
                    'total_processos': len(df),
                    'aereo': len(df[df['via_transporte_descricao'] == 'AEREA']),
                    'terrestre': len(df[df['via_transporte_descricao'] == 'TERRESTRE']),
                    'maritimo': len(df[df['via_transporte_descricao'] == 'MARITIMA']),
                    'aguardando_chegada': len(df[df['carga_status'] == '2 - Em Trânsito']),
                    'aguardando_embarque': len(df[df['carga_status'] == '1 - Aguardando Embarque']),
                    'di_registrada': len(df[df['status_doc'] == '3 - Desembarcada'])
                }
            else:
                global_data['dashboard_stats'] = {
                    'total_processos': 0, 'aereo': 0, 'terrestre': 0, 'maritimo': 0,
                    'aguardando_chegada': 0, 'aguardando_embarque': 0, 'di_registrada': 0
                }
            
            logger.info(f"Dados de importações processados: {len(global_data['importacoes'])} registros")
            
        except Exception as e:
            logger.error(f"Erro ao buscar importações: {str(e)}")
            global_data['importacoes'] = []
            global_data['dashboard_stats'] = {}
          # 2. Buscar usuários (apenas para admin e interno_unique)
        if user_role in ['admin', 'interno_unique']:
            try:
                logger.info("Buscando dados de usuários...")
                usuarios_response = supabase_admin.table('users').select('*').execute()
                global_data['usuarios'] = usuarios_response.data if usuarios_response.data else []
                logger.info(f"Dados de usuários processados: {len(global_data['usuarios'])} registros")
            except Exception as e:
                logger.error(f"Erro ao buscar usuários: {str(e)}")
                global_data['usuarios'] = []
        
        # 3. Buscar lista de empresas disponíveis
        try:
            logger.info("Buscando lista de empresas...")
            companies_query = supabase.table('importacoes_processos').select('cliente_cpfcnpj', 'cliente_razaosocial').execute()
            
            if companies_query.data:
                companies_df = pd.DataFrame(companies_query.data)
                companies_unique = companies_df.drop_duplicates(subset=['cliente_cpfcnpj']).to_dict('records')
                
                # Filtrar empresas baseado no role do usuário
                if user_role == 'cliente_unique' and global_data['user_companies']:
                    companies_unique = [c for c in companies_unique if c['cliente_cpfcnpj'] in global_data['user_companies']]
                
                global_data['companies'] = companies_unique
                logger.info(f"Lista de empresas processada: {len(global_data['companies'])} empresas")
            
        except Exception as e:
            logger.error(f"Erro ao buscar empresas: {str(e)}")
            global_data['companies'] = []
        
        # 4. Buscar cotações de câmbio
        try:
            logger.info("Buscando cotações de câmbio...")
            global_data['currencies'] = get_currencies()
        except Exception as e:
            logger.error(f"Erro ao buscar câmbio: {str(e)}")
            global_data['currencies'] = get_currencies()  # Retorna valores padrão
        
        logger.info("Dados globais coletados com sucesso")
        
        return jsonify({
            'status': 'success',
            'data': global_data,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.exception(f"Erro ao buscar dados globais: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Erro ao buscar dados globais: {str(e)}'
        }), 500

# Any other API endpoints can go here
