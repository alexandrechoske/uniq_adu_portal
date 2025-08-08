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
from services.retry_utils import run_with_retries
from services.data_cache import data_cache

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
        if isinstance(data, np.floating) and (np.isnan(data) or np.isinf(data)):
            return None
        return float(data) if isinstance(data, np.floating) else int(data)
    else:
        return data

# Helper: obter empresas do usuário via nova estrutura
# users -> user_empresas -> cad_clientes_sistema(cnpjs[])

def get_user_companies(user_data):
    try:
        if not user_data:
            return []
        user_role = user_data.get('role')
        user_id = user_data.get('id')
        if user_role not in ['cliente_unique', 'interno_unique'] or not user_id:
            # Somente clientes/interno tem filtragem por empresas
            return []

        # Buscar vínculos ativos do usuário
        user_empresas_response = (
            supabase_admin
            .table('user_empresas')
            .select('cliente_sistema_id, ativo, data_vinculo')
            .eq('user_id', user_id)
            .eq('ativo', True)
            .execute()
        )
        if not user_empresas_response.data:
            return []

        cliente_sistema_ids = [v['cliente_sistema_id'] for v in user_empresas_response.data]
        # Buscar dados das empresas
        empresas_response = (
            supabase_admin
            .table('cad_clientes_sistema')
            .select('id, nome_cliente, cnpjs, ativo')
            .in_('id', cliente_sistema_ids)
            .eq('ativo', True)
            .execute()
        )
        if not empresas_response.data:
            return []

        # Extrair e normalizar CNPJs
        all_cnpjs = []
        for empresa in empresas_response.data:
            cnpjs_array = empresa.get('cnpjs', [])
            if isinstance(cnpjs_array, list):
                for cnpj in cnpjs_array:
                    if not cnpj:
                        continue
                    normalized = re.sub(r'\D', '', str(cnpj))
                    if len(normalized) == 14:
                        all_cnpjs.append(normalized)
        return list(set(all_cnpjs))
    except Exception as e:
        logger.error(f"Erro get_user_companies: {e}")
        traceback.print_exc()
        return []

# Helper: obter câmbio (mínimo resiliente)

def get_currencies():
    try:
        # Placeholder resiliente: retorne estrutura vazia com timestamp
        return {
            'rates': {},
            'updated_at': datetime.now().isoformat()
        }
    except Exception:
        return {'rates': {}, 'updated_at': datetime.now().isoformat()}

@bp.route('/global-data')
@login_required
def global_data():
    """
    Endpoint que retorna todos os dados globais em uma única requisição
    Inclui: importações, usuários (admin/interno), lista de empresas, câmbio.
    """
    try:
        logger.info("Buscando dados globais da aplicação")
        user_data = session.get('user') or {}
        user_id = user_data.get('id')
        user_role = user_data.get('role')

        # Inicializar dados de retorno
        payload = {
            'importacoes': [],
            'usuarios': [],
            'dashboard_stats': {},
            'currencies': {},
            'companies': [],
            'user_companies': []
        }

        # 1) Importações/processos (com retries)
        try:
            query = supabase.table('importacoes_processos_aberta').select('*').neq('status_processo', 'Despacho Cancelado')
            if user_role == 'cliente_unique':
                user_companies = get_user_companies(user_data)
                payload['user_companies'] = user_companies
                if user_companies:
                    query = query.in_('cnpj_importador', user_companies)
                else:
                    query = query.eq('cnpj_importador', 'NENHUMA_EMPRESA_ENCONTRADA')

            def _run_importacoes():
                return query.execute()

            result = run_with_retries(
                'api.global_data.importacoes',
                _run_importacoes,
                max_attempts=3,
                base_delay_seconds=0.8,
                should_retry=lambda e: 'Server disconnected' in str(e) or 'timeout' in str(e).lower()
            )
            importacoes_data = result.data or []

            if importacoes_data:
                df = pd.DataFrame(importacoes_data)
                date_columns = ['data_embarque', 'data_chegada', 'data_abertura']
                for col in date_columns:
                    if col in df.columns:
                        df[col] = pd.to_datetime(df[col], errors='coerce', dayfirst=True)
                if 'data_embarque' in df.columns:
                    df = df.sort_values('data_embarque', ascending=False, na_position='last')
                for col in date_columns:
                    if col in df.columns:
                        df[col] = df[col].dt.strftime('%d/%m/%Y').fillna('')
                payload['importacoes'] = df.to_dict('records')
                payload['dashboard_stats'] = {
                    'total_processos': len(df),
                    'aereo': int((df['modal'] == 'AEREA').sum()) if 'modal' in df.columns else 0,
                    'terrestre': int((df['modal'] == 'TERRESTRE').sum()) if 'modal' in df.columns else 0,
                    'maritimo': int((df['modal'] == 'MARITIMA').sum()) if 'modal' in df.columns else 0,
                    'aguardando_chegada': int(df['status_processo'].str.contains('TRANSITO', na=False, case=False).sum()) if 'status_processo' in df.columns else 0,
                    'aguardando_embarque': int(df['status_processo'].str.contains('DECLARACAO', na=False, case=False).sum()) if 'status_processo' in df.columns else 0,
                    'di_registrada': int(df['status_processo'].str.contains('DESEMBARACADA', na=False, case=False).sum()) if 'status_processo' in df.columns else 0,
                }
            else:
                payload['dashboard_stats'] = {
                    'total_processos': 0, 'aereo': 0, 'terrestre': 0, 'maritimo': 0,
                    'aguardando_chegada': 0, 'aguardando_embarque': 0, 'di_registrada': 0
                }
        except Exception as e:
            logger.error(f"Erro ao buscar importações: {e}")
            payload['importacoes'] = []
            payload['dashboard_stats'] = {}

        # 2) Usuários (somente admin/interno)
        if user_role in ['admin', 'interno_unique']:
            try:
                def _run_users():
                    return supabase_admin.table('users').select('*').execute()
                usuarios_response = run_with_retries(
                    'api.global_data.users',
                    _run_users,
                    max_attempts=3,
                    base_delay_seconds=0.8,
                    should_retry=lambda e: 'Server disconnected' in str(e) or 'timeout' in str(e).lower()
                )
                payload['usuarios'] = usuarios_response.data or []
            except Exception as e:
                logger.error(f"Erro ao buscar usuários: {e}")
                payload['usuarios'] = []

        # 3) Lista de empresas
        try:
            def _run_companies():
                return supabase.table('importacoes_processos_aberta').select('cnpj_importador, importador').execute()
            companies_query = run_with_retries(
                'api.global_data.companies',
                _run_companies,
                max_attempts=3,
                base_delay_seconds=0.8,
                should_retry=lambda e: 'Server disconnected' in str(e) or 'timeout' in str(e).lower()
            )
            if companies_query.data:
                companies_df = pd.DataFrame(companies_query.data)
                companies_unique = companies_df.drop_duplicates(subset=['cnpj_importador']).to_dict('records')
                if user_role == 'cliente_unique' and payload['user_companies']:
                    companies_unique = [c for c in companies_unique if c['cnpj_importador'] in payload['user_companies']]
                payload['companies'] = companies_unique
        except Exception as e:
            logger.error(f"Erro ao buscar empresas: {e}")
            payload['companies'] = []

        # 4) Câmbio
        try:
            payload['currencies'] = get_currencies()
        except Exception as e:
            logger.error(f"Erro ao buscar câmbio: {e}")
            payload['currencies'] = get_currencies()

        logger.info("Dados globais coletados com sucesso")

        # Limpeza e cache NO SERVIDOR (evitar crescer cookies/sessão)
        payload_clean = clean_data_for_json(payload)
        try:
            if user_id:
                data_cache.set_cache(user_id, 'global_data', payload_clean)
                logger.info(f"[GLOBAL_DATA] Cache atualizado para usuário {user_id} (tamanho aprox.: {len(str(payload_clean))} chars)")
        except Exception as cache_err:
            logger.warning(f"[GLOBAL_DATA] Falha ao gravar no cache do servidor: {cache_err}")

        return jsonify({'status': 'success', 'data': payload_clean, 'timestamp': datetime.now().isoformat()})

    except Exception as e:
        logger.exception(f"Erro ao buscar dados globais: {e}")
        # Fallback: usar cache do servidor se disponível
        try:
            user = session.get('user') or {}
            user_id = user.get('id')
            if user_id:
                fallback = data_cache.get_cache(user_id, 'global_data')
                if fallback:
                    logger.info(f"[GLOBAL_DATA] Servindo fallback do cache do servidor para usuário {user_id}")
                    return jsonify({
                        'status': 'success',
                        'data': fallback,
                        'timestamp': datetime.now().isoformat(),
                        'source': 'server_cache_fallback'
                    })
        except Exception as cache_err:
            logger.warning(f"[GLOBAL_DATA] Erro ao obter fallback do cache: {cache_err}")

        return jsonify({'status': 'error', 'message': f'Erro ao buscar dados globais: {str(e)}'}), 500

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
