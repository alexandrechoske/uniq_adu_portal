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
                
                # Converter datas para datetime para ordenação adequada - incluindo novos campos
                date_columns = ['data_embarque', 'data_chegada', 'data_abertura']
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
                
                # Calcular estatísticas usando campos atualizados
                global_data['dashboard_stats'] = {
                    'total_processos': len(df),
                    'aereo': len(df[df['via_transporte_descricao'] == 'AEREA']),
                    'terrestre': len(df[df['via_transporte_descricao'] == 'TERRESTRE']),
                    'maritimo': len(df[df['via_transporte_descricao'] == 'MARITIMA']),
                    'aguardando_chegada': len(df[df['carga_status'] == '2 - Em Trânsito']),
                    'aguardando_embarque': len(df[df['carga_status'] == '1 - Aguardando Embarque']),
                    'di_registrada': len(df[df['carga_status'] == '3 - Desembarcada'])  # Usando carga_status
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

@bp.route('/force-refresh', methods=['POST'])
@login_required
def force_refresh():
    """
    Endpoint para refresh forçado de todos os dados da aplicação
    Limpa qualquer cache e busca os dados mais atualizados do banco
    """
    try:
        logger.info("=== INICIANDO REFRESH FORÇADO ===")
        
        user_data = session.get('user')
        user_role = user_data.get('role')
        
        # Forçar timestamp único para garantir cache bust
        timestamp = datetime.now().isoformat()
        
        # Dados de retorno com estrutura expandida
        refresh_data = {
            'importacoes': [],
            'usuarios': [],
            'dashboard_stats': {},
            'material_stats': {},
            'currencies': {},
            'companies': [],
            'user_companies': [],
            'refresh_timestamp': timestamp,
            'total_records_updated': 0
        }
        
        # 1. REFRESH FORÇADO DE IMPORTAÇÕES/PROCESSOS
        try:
            logger.info("🔄 Fazendo refresh forçado de importações...")
            
            # Query com ordenação para garantir dados mais recentes
            query = supabase.table('importacoes_processos').select(
                'id, numero, situacao, diduimp_canal, data_chegada, previsao_chegada, '
                'total_vmle_real, total_vmcv_real, cliente_cpfcnpj, cliente_razaosocial, '
                'created_at, updated_at, via_transporte_descricao, data_abertura, '
                'carga_status, resumo_mercadoria, referencias, armazens, data_embarque, '
                'local_embarque, tipo_operacao, di_modalidade_despacho, status_doc'
            ).neq('situacao', 'Despacho Cancelado').order('updated_at', desc=True)
            
            # Aplicar filtros baseados no role do usuário
            if user_role == 'cliente_unique':
                user_companies = get_user_companies(user_data)
                refresh_data['user_companies'] = user_companies
                
                if user_companies:
                    query = query.in_('cliente_cpfcnpj', user_companies)
                else:
                    query = query.eq('cliente_cpfcnpj', 'NENHUMA_EMPRESA_ENCONTRADA')
            
            result = query.execute()
            importacoes_data = result.data if result.data else []
            refresh_data['total_records_updated'] += len(importacoes_data)
            
            # Processar dados com pandas para cálculos estatísticos
            if importacoes_data:
                df = pd.DataFrame(importacoes_data)
                
                # Converter colunas numéricas
                df['total_vmle_real'] = pd.to_numeric(df['total_vmle_real'], errors='coerce').fillna(0)
                df['total_vmcv_real'] = pd.to_numeric(df['total_vmcv_real'], errors='coerce').fillna(0)
                
                # Converter datas
                date_columns = ['data_abertura', 'data_embarque', 'data_chegada', 'previsao_chegada']
                for col in date_columns:
                    if col in df.columns:
                        df[col] = pd.to_datetime(df[col], errors='coerce')
                
                # Calcular estatísticas do dashboard
                refresh_data['dashboard_stats'] = {
                    'total_processos': len(df),
                    'aereo': len(df[df['via_transporte_descricao'] == 'AEREA']),
                    'terrestre': len(df[df['via_transporte_descricao'] == 'TERRESTRE']),
                    'maritimo': len(df[df['via_transporte_descricao'] == 'MARITIMA']),
                    'aguardando_embarque': len(df[df['carga_status'] == '1 - Aguardando Embarque']),
                    'em_transito': len(df[df['carga_status'] == '2 - Em Trânsito']),
                    'desembarcadas': len(df[df['carga_status'] == '3 - Desembarcada']),
                    'vmcv_total': float(df['total_vmcv_real'].sum()),
                    'vmle_total': float(df['total_vmle_real'].sum())
                }
                
                # Calcular estatísticas de materiais
                material_groups = df.groupby('resumo_mercadoria').agg({
                    'numero': 'count',
                    'total_vmcv_real': 'sum'
                }).reset_index().sort_values('total_vmcv_real', ascending=False)
                
                refresh_data['material_stats'] = {
                    'top_materials': [
                        {
                            'material': row['resumo_mercadoria'] if row['resumo_mercadoria'] else 'Não Informado',
                            'quantidade': int(row['numero']),
                            'valor_total': float(row['total_vmcv_real'])
                        }
                        for _, row in material_groups.head(10).iterrows()
                    ],
                    'total_materials': len(material_groups)
                }
                
                # Converter de volta para JSON serializable
                for col in date_columns:
                    if col in df.columns:
                        df[col] = df[col].dt.strftime('%Y-%m-%d %H:%M:%S').fillna('')
                
                refresh_data['importacoes'] = df.to_dict('records')
                
            logger.info(f"✅ Importações atualizadas: {len(importacoes_data)} registros")
            
        except Exception as e:
            logger.error(f"❌ Erro ao fazer refresh de importações: {str(e)}")
            refresh_data['importacoes'] = []
            refresh_data['dashboard_stats'] = {}
            refresh_data['material_stats'] = {}
        
        # 2. REFRESH FORÇADO DE USUÁRIOS (apenas admin/interno)
        if user_role in ['admin', 'interno_unique']:
            try:
                logger.info("🔄 Fazendo refresh forçado de usuários...")
                usuarios_response = supabase_admin.table('users').select('*').order('created_at', desc=True).execute()
                refresh_data['usuarios'] = usuarios_response.data if usuarios_response.data else []
                refresh_data['total_records_updated'] += len(refresh_data['usuarios'])
                logger.info(f"✅ Usuários atualizados: {len(refresh_data['usuarios'])} registros")
            except Exception as e:
                logger.error(f"❌ Erro ao fazer refresh de usuários: {str(e)}")
                refresh_data['usuarios'] = []
        
        # 3. REFRESH FORÇADO DE EMPRESAS
        try:
            logger.info("🔄 Fazendo refresh forçado de empresas...")
            companies_query = supabase.table('importacoes_processos')\
                .select('cliente_cpfcnpj, cliente_razaosocial')\
                .neq('cliente_cpfcnpj', '')\
                .not_.is_('cliente_cpfcnpj', 'null')\
                .execute()
            
            if companies_query.data:
                companies_df = pd.DataFrame(companies_query.data)
                companies_unique = companies_df.drop_duplicates(subset=['cliente_cpfcnpj']).to_dict('records')
                
                # Filtrar empresas baseado no role do usuário
                if user_role == 'cliente_unique' and refresh_data['user_companies']:
                    companies_unique = [c for c in companies_unique if c['cliente_cpfcnpj'] in refresh_data['user_companies']]
                
                refresh_data['companies'] = companies_unique
                refresh_data['total_records_updated'] += len(companies_unique)
                logger.info(f"✅ Empresas atualizadas: {len(companies_unique)} registros")
            
        except Exception as e:
            logger.error(f"❌ Erro ao fazer refresh de empresas: {str(e)}")
            refresh_data['companies'] = []
        
        # 4. REFRESH FORÇADO DE CÂMBIO
        try:
            logger.info("🔄 Fazendo refresh forçado de câmbio...")
            refresh_data['currencies'] = get_currencies()
            logger.info("✅ Câmbio atualizado")
        except Exception as e:
            logger.error(f"❌ Erro ao fazer refresh de câmbio: {str(e)}")
            refresh_data['currencies'] = get_currencies()
        
        logger.info(f"=== REFRESH FORÇADO CONCLUÍDO ===")
        logger.info(f"📊 Total de registros atualizados: {refresh_data['total_records_updated']}")
        
        return jsonify({
            'status': 'success',
            'message': f'Refresh forçado concluído com sucesso. {refresh_data["total_records_updated"]} registros atualizados.',
            'data': refresh_data,
            'timestamp': timestamp
        })
        
    except Exception as e:
        logger.exception(f"❌ Erro crítico no refresh forçado: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Erro no refresh forçado: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500

# Any other API endpoints can go here
