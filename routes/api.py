from flask import Blueprint, request, jsonify, session
from extensions import supabase, supabase_admin
from routes.auth import login_required
import pandas as pd
import numpy as np
from datetime import datetime
import requests
import logging
import re
import traceback
import os

# Configurar logging
logger = logging.getLogger(__name__)

bp = Blueprint('api', __name__)

@bp.route('/test-new-structure')
def test_new_structure():
    """Endpoint para testar a nova estrutura de tabelas relacionadas"""
    try:
        # Verificar se é uma requisição com API bypass
        api_bypass_key = os.getenv('API_BYPASS_KEY')
        request_api_key = request.headers.get('X-API-Key')
        
        if not (api_bypass_key and request_api_key == api_bypass_key):
            return jsonify({'error': 'API key required'}), 401
        
        results = {}
        
        # 1. Testar tabela users
        try:
            users_response = supabase_admin.table('users').select('id, email, name, role').limit(3).execute()
            results['users'] = {
                'status': 'success',
                'count': len(users_response.data),
                'sample': users_response.data
            }
        except Exception as e:
            results['users'] = {'status': 'error', 'error': str(e)}
        
        # 2. Testar tabela user_empresas
        try:
            user_empresas_response = supabase_admin.table('user_empresas').select('*').limit(3).execute()
            results['user_empresas'] = {
                'status': 'success',
                'count': len(user_empresas_response.data),
                'sample': user_empresas_response.data
            }
        except Exception as e:
            results['user_empresas'] = {'status': 'error', 'error': str(e)}
        
        # 3. Testar tabela cad_clientes_sistema
        try:
            clientes_response = supabase_admin.table('cad_clientes_sistema').select('*').limit(3).execute()
            results['cad_clientes_sistema'] = {
                'status': 'success',
                'count': len(clientes_response.data),
                'sample': clientes_response.data
            }
        except Exception as e:
            results['cad_clientes_sistema'] = {'status': 'error', 'error': str(e)}
        
        return jsonify({
            'success': True,
            'message': 'Teste da nova estrutura de tabelas',
            'results': results
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

def clean_data_for_json(data):
    """
    Limpa dados removendo valores NaN, NaT e outros valores problemáticos para JSON
    """
    if isinstance(data, dict):
        return {key: clean_data_for_json(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [clean_data_for_json(item) for item in data]
    elif isinstance(data, pd.Series):
        return clean_data_for_json(data.to_dict())
    elif isinstance(data, pd.DataFrame):
        # Converter DataFrame para dict e limpar
        df_clean = data.copy()
        # Substituir NaN, NaT e infinity por valores apropriados
        df_clean = df_clean.replace([np.nan, np.inf, -np.inf], None)
        # Converter datas NaT para string vazia
        for col in df_clean.columns:
            if df_clean[col].dtype.name.startswith('datetime'):
                df_clean[col] = df_clean[col].dt.strftime('%d/%m/%Y').fillna('')
        return clean_data_for_json(df_clean.to_dict('records'))
    elif pd.isna(data) or data is pd.NaT:
        return None
    elif isinstance(data, (np.integer, np.floating)):
        if np.isnan(data) or np.isinf(data):
            return None
        return float(data) if isinstance(data, np.floating) else int(data)
    else:
        return data

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
    """Get companies that the user has access to - NOVA ESTRUTURA com 3 relações"""
    print(f"[API] get_user_companies chamado para usuário: {user_data.get('id')}")
    print(f"[API] User role: {user_data.get('role')}")
    
    user_role = user_data.get('role')
    
    # Para admin, retornar lista vazia (acesso total)
    if user_role == 'admin':
        print(f"[API] Usuário admin - acesso total")
        return []
    
    # Para cliente_unique e interno_unique, buscar empresas associadas via nova estrutura
    if user_role in ['cliente_unique', 'interno_unique']:
        try:
            user_id = user_data['id']
            print(f"[API] Buscando CNPJs para user_id: {user_id} (role: {user_role})")
            
            # NOVA ESTRUTURA: users -> user_empresas -> cad_clientes_sistema -> cnpjs[]
            print(f"[API] 1. Buscando vínculos na tabela user_empresas...")
            
            # Buscar vínculos ativos do usuário
            user_empresas_response = supabase_admin.table('user_empresas')\
                .select('cliente_sistema_id, ativo, data_vinculo')\
                .eq('user_id', user_id)\
                .eq('ativo', True)\
                .execute()
            
            print(f"[API] user_empresas encontrados: {len(user_empresas_response.data) if user_empresas_response.data else 0}")
            print(f"[API] Dados user_empresas: {user_empresas_response.data}")
            
            if not user_empresas_response.data:
                print(f"[API] Nenhum vínculo ativo encontrado na tabela user_empresas")
                return []
            
            # Extrair IDs das empresas vinculadas
            cliente_sistema_ids = [vinculo['cliente_sistema_id'] for vinculo in user_empresas_response.data]
            print(f"[API] IDs das empresas vinculadas: {cliente_sistema_ids}")
            
            # Buscar dados das empresas
            print(f"[API] 2. Buscando dados das empresas na tabela cad_clientes_sistema...")
            
            empresas_response = supabase_admin.table('cad_clientes_sistema')\
                .select('id, nome_cliente, cnpjs, ativo')\
                .in_('id', cliente_sistema_ids)\
                .eq('ativo', True)\
                .execute()
            
            print(f"[API] Empresas encontradas: {len(empresas_response.data) if empresas_response.data else 0}")
            print(f"[API] Dados das empresas: {empresas_response.data}")
            
            if not empresas_response.data:
                print(f"[API] Nenhuma empresa ativa encontrada")
                return []
            
            # Extrair CNPJs das empresas
            print(f"[API] 3. Extraindo CNPJs das empresas...")
            
            all_cnpjs = []
            empresas_info = []
            
            for empresa in empresas_response.data:
                empresa_id = empresa.get('id')
                nome_cliente = empresa.get('nome_cliente', 'N/A')
                cnpjs_array = empresa.get('cnpjs', [])
                
                print(f"[API] Empresa ID {empresa_id}: {nome_cliente}")
                print(f"[API] CNPJs brutos: {cnpjs_array}")
                
                empresas_info.append({
                    'id': empresa_id,
                    'nome': nome_cliente,
                    'cnpjs_raw': cnpjs_array
                })
                
                if isinstance(cnpjs_array, list):
                    for cnpj in cnpjs_array:
                        if cnpj:
                            # Normalizar CNPJ (remover formatação)
                            normalized_cnpj = re.sub(r'\D', '', str(cnpj))
                            if normalized_cnpj and len(normalized_cnpj) == 14:  # CNPJ deve ter 14 dígitos
                                all_cnpjs.append(normalized_cnpj)
                                print(f"[API] CNPJ normalizado: {cnpj} -> {normalized_cnpj}")
                            else:
                                print(f"[API] CNPJ inválido ignorado: {cnpj} -> {normalized_cnpj}")
                else:
                    print(f"[API] CNPJs não é uma lista para empresa {nome_cliente}: {type(cnpjs_array)}")
            
            # Remover CNPJs duplicados
            unique_cnpjs = list(set(all_cnpjs))
            
            print(f"[API] === RESULTADO FINAL ===")
            print(f"[API] Total de empresas: {len(empresas_info)}")
            print(f"[API] Total de CNPJs únicos: {len(unique_cnpjs)}")
            print(f"[API] CNPJs finais: {unique_cnpjs}")
            print(f"[API] Empresas: {[emp['nome'] for emp in empresas_info]}")
            
            if unique_cnpjs:
                return unique_cnpjs
            else:
                print(f"[API] Nenhum CNPJ válido encontrado, usuário sem acesso a dados")
                return []
                
        except Exception as e:
            print(f"[API] Erro ao buscar empresas do usuário: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
    else:
        print(f"[API] Usuário role {user_role} não requer filtragem de empresas")
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
            query = supabase.table('importacoes_processos_aberta').select('*').neq('status_processo', 'Despacho Cancelado')
            
            # Aplicar filtros baseados no role do usuário
            if user_role == 'cliente_unique':
                user_companies = get_user_companies(user_data)
                global_data['user_companies'] = user_companies
                
                if user_companies:
                    # Filtrar por empresas do usuário
                    query = query.in_('cnpj_importador', user_companies)
                else:
                    # Se não tem empresas, retornar dados vazios para este usuário
                    query = query.eq('cnpj_importador', 'NENHUMA_EMPRESA_ENCONTRADA')
            
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
                    'aereo': len(df[df['modal'] == 'AEREA']),
                    'terrestre': len(df[df['modal'] == 'TERRESTRE']),
                    'maritimo': len(df[df['modal'] == 'MARITIMA']),
                    'aguardando_chegada': len(df[df['status_processo'].str.contains('TRANSITO', na=False, case=False)]),
                    'aguardando_embarque': len(df[df['status_processo'].str.contains('DECLARACAO', na=False, case=False)]),
                    'di_registrada': len(df[df['status_processo'].str.contains('DESEMBARACADA', na=False, case=False)])  # Usando carga_status
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
            companies_query = supabase.table('importacoes_processos_aberta').select('cnpj_importador', 'importador').execute()
            
            if companies_query.data:
                companies_df = pd.DataFrame(companies_query.data)
                companies_unique = companies_df.drop_duplicates(subset=['cnpj_importador']).to_dict('records')
                
                # Filtrar empresas baseado no role do usuário
                if user_role == 'cliente_unique' and global_data['user_companies']:
                    companies_unique = [c for c in companies_unique if c['cnpj_importador'] in global_data['user_companies']]
                
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
        
        # Limpar dados para evitar problemas de serialização JSON
        global_data_clean = clean_data_for_json(global_data)
        
        return jsonify({
            'status': 'success',
            'data': global_data_clean,
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
            query = supabase.table('importacoes_processos_aberta').select(
                'id, ref_unique, status_processo, canal, data_chegada, '
                'valor_fob_real, valor_cif_real, cnpj_importador, importador, '
                'created_at, updated_at, modal, data_aberture, '
                'mercadoria, data_embarque, urf_entrada, numero_di, data_registro, '
                'peso_bruto, transit_time_real, exportador_fornecedor, fabricante, '
                'presenca_carga, data_desembaraco, custo_total, firebird_di_codigo, '
                'firebird_fat_codigo, container, urf_despacho'
            ).neq('status_processo', 'Despacho Cancelado').order('updated_at', desc=True)
            
            # Aplicar filtros baseados no role do usuário
            if user_role == 'cliente_unique':
                user_companies = get_user_companies(user_data)
                refresh_data['user_companies'] = user_companies
                
                if user_companies:
                    query = query.in_('cnpj_importador', user_companies)
                else:
                    query = query.eq('cnpj_importador', 'NENHUMA_EMPRESA_ENCONTRADA')
            
            result = query.execute()
            importacoes_data = result.data if result.data else []
            refresh_data['total_records_updated'] += len(importacoes_data)
            
            # Processar dados com pandas para cálculos estatísticos
            if importacoes_data:
                df = pd.DataFrame(importacoes_data)
                
                # Converter colunas numéricas
                df['valor_fob_real'] = pd.to_numeric(df['valor_fob_real'], errors='coerce').fillna(0)
                df['valor_cif_real'] = pd.to_numeric(df['valor_cif_real'], errors='coerce').fillna(0)
                
                # Converter datas
                date_columns = ['data_abertura', 'data_embarque', 'data_chegada', 'data_chegada']
                for col in date_columns:
                    if col in df.columns:
                        df[col] = pd.to_datetime(df[col], errors='coerce')
                
                # Calcular estatísticas do dashboard
                refresh_data['dashboard_stats'] = {
                    'total_processos': len(df),
                    'aereo': len(df[df['modal'] == 'AEREA']),
                    'terrestre': len(df[df['modal'] == 'TERRESTRE']),
                    'maritimo': len(df[df['modal'] == 'MARITIMA']),
                    'aguardando_embarque': len(df[df['status_processo'].str.contains('DECLARACAO', na=False, case=False)]),
                    'em_transito': len(df[df['status_processo'].str.contains('TRANSITO', na=False, case=False)]),
                    'desembarcadas': len(df[df['status_processo'].str.contains('DESEMBARACADA', na=False, case=False)]),
                    'vmcv_total': float(df['valor_cif_real'].sum()),
                    'vmle_total': float(df['valor_fob_real'].sum())
                }
                
                # Calcular estatísticas de materiais
                material_groups = df.groupby('mercadoria').agg({
                    'ref_unique': 'count',
                    'valor_cif_real': 'sum'
                }).reset_index().sort_values('valor_cif_real', ascending=False)
                
                refresh_data['material_stats'] = {
                    'top_materials': [
                        {
                            'material': row['mercadoria'] if row['mercadoria'] else 'Não Informado',
                            'quantidade': int(row['ref_unique']),
                            'valor_total': float(row['valor_cif_real'])
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
            companies_query = supabase.table('importacoes_processos_aberta')\
                .select('cnpj_importador, importador')\
                .neq('cnpj_importador', '')\
                .not_.is_('cnpj_importador', 'null')\
                .execute()
            
            if companies_query.data:
                companies_df = pd.DataFrame(companies_query.data)
                companies_unique = companies_df.drop_duplicates(subset=['cnpj_importador']).to_dict('records')
                
                # Filtrar empresas baseado no role do usuário
                if user_role == 'cliente_unique' and refresh_data['user_companies']:
                    companies_unique = [c for c in companies_unique if c['cnpj_importador'] in refresh_data['user_companies']]
                
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

@bp.route('/test-user-companies')
@login_required
def test_user_companies():
    """Endpoint de teste para debug da função get_user_companies"""
    try:
        # Verificar bypass de API
        api_bypass_key = os.getenv('API_BYPASS_KEY')
        if not (api_bypass_key and request.headers.get('X-API-Key') == api_bypass_key):
            return jsonify({'error': 'API Bypass necessário'}), 403
        
        # Simular usuário Alexandre para teste - USANDO ID CORRETO DO LOG
        user_data = {
            'id': '13ed3af4-f6a2-4c82-ba21-dce5d33c6756',  # ID correto do log
            'email': 'alexandre.choski@gmail.com',
            'role': 'interno_unique'  # Role correto do log
        }
        
        print(f"[TEST_API] Testando get_user_companies para: {user_data}")
        
        # Chamar função diretamente
        user_companies = get_user_companies(user_data)
        
        return jsonify({
            'status': 'success',
            'user_data': user_data,
            'user_companies': user_companies,
            'count': len(user_companies),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"[TEST_API] Erro no teste: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# Any other API endpoints can go here
