from flask import Blueprint, render_template, session, request, jsonify
from extensions import supabase
from routes.auth import login_required
import pandas as pd
from datetime import datetime
import json
import requests
import os
import logging

# Configurar logging específico para este módulo
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s [%(name)s] [%(levelname)s] %(message)s'))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

bp = Blueprint('onepage', __name__, url_prefix='/onepage')

def update_importacoes_processos():
    """
    Atualiza os dados de importações e processos via Edge Function do Supabase.
    Retorna (bool, str): Tupla com status de sucesso e mensagem de erro se houver.
    """
    try:
        from config import Config
        
        # Log da tentativa de atualização
        logger.info("Iniciando atualização de importações e processos via Supabase Edge Function")
          # Verificar se as configurações necessárias existem
        if not hasattr(Config, 'SUPABASE_URL') or not Config.SUPABASE_URL:
            logger.error("SUPABASE_URL não configurado")
            return False, "Configuração de URL do Supabase ausente"
            
        if not hasattr(Config, 'SUPABASE_CURL_BEARER') or not Config.SUPABASE_CURL_BEARER:
            logger.error("SUPABASE_CURL_BEARER não configurado")
            return False, "Token de autenticação do Supabase ausente"
          # Fazer a requisição para a Edge Function
        try:            # Verificar conexão com internet antes de tentar
            try:
                test_conn = requests.get('https://supabase.com', timeout=5)
                if test_conn.status_code != 200:
                    logger.warning("Possível problema de conexão com internet")
            except requests.RequestException:
                logger.error("Problema ao verificar conexão com internet")
                return False, "Não foi possível conectar à internet"
            
            # Tentar requisição principal
            response = requests.post(
                f'{Config.SUPABASE_URL}/functions/v1/att_importacoes-processos',
                headers={
                    'Authorization': f'Bearer {Config.SUPABASE_CURL_BEARER}',
                    'Content-Type': 'application/json'
                },
                json={'name': 'Functions'},
                timeout=20  # Timeout de 20 segundos para evitar bloqueio indefinido
            )
              # Verificar resposta
            if response.status_code == 200:
                logger.info(f"Atualização bem-sucedida: {response.status_code}")
                return True, ""
            else:
                logger.error(f"Erro na atualização: Status {response.status_code}, Resposta: {response.text[:200]}")
                return False, f"Erro {response.status_code} na atualização: {response.text[:200]}"
                
        except requests.RequestException as req_err:
            logger.error(f"Erro de requisição: {str(req_err)}")
            return False, f"Erro na comunicação com Supabase: {str(req_err)}"
            
    except Exception as e:
        logger.exception(f"Erro inesperado na atualização: {str(e)}")
        return False, f"Erro inesperado: {str(e)}"

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
    if session['user']['role'] not in ['cliente_unique', 'interno_unique','admin']:
        return render_template('errors/401.html'), 401

    # Get user's companies and selected filter
    user_companies = get_user_companies()
    selected_company = request.args.get('empresa')
    
    # Timestamp da última atualização
    last_update = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    
    # Get currency exchange rates
    currencies = get_currencies()

    # Build initial query without sorting (will sort after date conversion)
    # Filtrar para excluir registros com "Despacho Cancelado"
    query = supabase.table('importacoes_processos_aberta').select('*').neq('status_processo', 'Despacho Cancelado')

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
            query = query.eq('cnpj_importador', selected_company)
        else:
            query = query.in_('cnpj_importador', user_companies)

    elif selected_company:  # interno_unique with filter
        query = query.eq('cnpj_importador', selected_company)

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
        # Calculate KPIs baseado na nova estrutura da tabela
        kpis = {
            'total': len(df),
            'aereo': len(df[df['modal'] == 'AEREA']),
            'terrestre': len(df[df['modal'] == 'TERRESTRE']),  
            'maritimo': len(df[df['modal'] == 'MARITIMA']),
            'aguardando_chegada': len(df[df['status_processo'].str.contains('TRANSITO', na=False, case=False)]),
            'aguardando_embarque': len(df[df['status_processo'].str.contains('DECLARACAO', na=False, case=False)]),
            'di_registrada': len(df[df['status_processo'].str.contains('DESEMBARACADA', na=False, case=False)])  # Usando status_processo ao invés de status_doc
        }

        # Prepare table data - usando campos que existem na tabela
        # Converter datas para datetime para ordenação correta
        date_columns = ['data_embarque', 'data_chegada', 'data_abertura']
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
    companies_query = supabase.table('importacoes_processos_aberta').select('cnpj_importador', 'importador').execute()
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
    if session['user']['role'] not in ['cliente_unique', 'interno_unique', 'admin']:
        print(f"[DEBUG] Acesso não autorizado para /update-data: usuário com role {session['user']['role']}")
        return jsonify({
            'status': 'error',
            'message': 'Acesso não autorizado'
        }), 401
      # Chamar a função de atualização
    try:
        update_success, error_message = update_importacoes_processos()
        
        if update_success:
            logger.info("Atualização de dados bem-sucedida")
            return jsonify({
                'status': 'success',
                'message': 'Dados atualizados com sucesso!',
                'timestamp': datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            })
        else:
            # Log do erro no servidor
            logger.error(f"Erro ao atualizar dados: {error_message}")
            
            # Tentar o método de fallback
            logger.info("Tentando método de fallback automático")
            fallback_success, fallback_message, records = get_importacoes_direct()
            
            if fallback_success:
                logger.info(f"Método de fallback funcionou: {records} registros obtidos")
                return jsonify({
                    'status': 'warning',
                    'message': f'Usamos método alternativo com sucesso ({records} registros)',
                    'original_error': error_message,
                    'timestamp': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
                    'was_fallback': True
                })
            else:
                logger.error(f"Ambos os métodos falharam. Principal: {error_message}, Fallback: {fallback_message}")
                return jsonify({
                    'status': 'error',
                    'message': f'Erro ao atualizar os dados: {error_message}',
                    'fallback_error': fallback_message,
                    'timestamp': datetime.now().strftime('%d/%m/%Y %H:%M:%S')
                }), 500
                
    except Exception as e:
        import traceback
        logger.error(f"Exceção não tratada em update_data: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Tentar o método de fallback como último recurso
        try:
            fallback_success, fallback_message, records = get_importacoes_direct()
            if fallback_success:
                logger.info(f"Recuperação de erro com método de fallback: {records} registros")
                return jsonify({
                    'status': 'warning',
                    'message': f'Usamos método alternativo após erro ({records} registros)',
                    'original_error': str(e),
                    'timestamp': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
                    'was_fallback': True
                })
        except:
            # Se até o fallback falhar, retornamos o erro original
            pass
            
        return jsonify({
            'status': 'error',
            'message': f'Erro interno do servidor: {str(e)}',
            'timestamp': datetime.now().strftime('%d/%m/%Y %H:%M:%S')
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
        # Filtrar para excluir registros com "Despacho Cancelado"
        query = supabase.table('importacoes_processos_aberta').select('*').neq('status_processo', 'Despacho Cancelado')

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
                query = query.eq('cnpj_importador', selected_company)
            else:
                query = query.in_('cnpj_importador', user_companies)

        elif selected_company:  # interno_unique with filter
            query = query.eq('cnpj_importador', selected_company)

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
            # Calculate KPIs - usando a estrutura atualizada da tabela
            kpis = {
                'total': len(df),
                'aereo': len(df[df['modal'] == 'AEREA']),
                'terrestre': len(df[df['modal'] == 'TERRESTRE']),
                'maritimo': len(df[df['modal'] == 'MARITIMA']),
                'aguardando_chegada': len(df[df['status_processo'].str.contains('TRANSITO', na=False, case=False)]),
                'aguardando_embarque': len(df[df['status_processo'].str.contains('DECLARACAO', na=False, case=False)]),
                'di_registrada': len(df[df['status_processo'].str.contains('DESEMBARACADA', na=False, case=False)])  # Usando carga_status
            }

            # Prepare table data - usando campos que existem na tabela
            # Converter datas para datetime para ordenação correta
            date_columns = ['data_embarque', 'data_chegada', 'data_abertura']
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

def get_importacoes_direct():
    """
    Função de fallback que busca dados diretamente da tabela no Supabase
    quando a Edge Function falha. Não faz sincronização completa, apenas lê os dados atuais.
    """
    try:
        from extensions import supabase
        logger.info("Utilizando método fallback para obtenção de dados")
          # Consulta direta à tabela de importações_processos
        # Filtrar para excluir registros com "Despacho Cancelado"
        response = supabase.table('importacoes_processos_aberta').select('*').neq('status_processo', 'Despacho Cancelado').execute()
        
        if response.data:
            return True, "", len(response.data)
        else:
            return True, "Nenhum registro encontrado", 0
            
    except Exception as e:
        logger.exception(f"Erro no método fallback: {str(e)}")
        return False, f"Erro no método fallback: {str(e)}", 0

@bp.route('/bypass-update', methods=['POST'])
@login_required
def bypass_update():
    """
    Endpoint alternativo quando o padrão falha, usando acesso direto sem Edge Function
    """
    if session['user']['role'] not in ['cliente_unique', 'interno_unique', 'admin']:
        return jsonify({
            'status': 'error',
            'message': 'Acesso não autorizado'
        }), 401
    
    # Usar o método fallback
    success, message, records_count = get_importacoes_direct()
    
    if success:
        return jsonify({
            'status': 'success',
            'message': f'Dados obtidos diretamente: {records_count} registros',
            'timestamp': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
            'was_fallback': True
        })
    else:
        return jsonify({
            'status': 'error',
            'message': message,
            'timestamp': datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        }), 500
