from flask import Blueprint, render_template, session, jsonify, request
from extensions import supabase, supabase_admin
from routes.auth import login_required, role_required
from decorators.perfil_decorators import perfil_required
from routes.api import get_user_companies
from permissions import check_permission
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import unicodedata
import re
import json
from services.data_cache import DataCacheService
from services.retry_utils import run_with_retries
from threading import Lock

# Instanciar o serviço de cache
data_cache = DataCacheService()
_dashboard_load_locks = {}

def _get_user_lock(user_id):
    if user_id not in _dashboard_load_locks:
        _dashboard_load_locks[user_id] = Lock()
    return _dashboard_load_locks[user_id]

def fetch_and_cache_dashboard_data(user_data, force=False):
    """Garantir que os dados base do dashboard estejam no cache.
    - Se já existir no cache e não for force: retorna direto.
    - Caso contrário, executa a query, enriquece e armazena.
    Essa função elimina dependência da ordem de chamadas (race entre /load-data e /kpis,/charts,...)
    """
    user_id = user_data.get('id')
    role = user_data.get('role')
    if not user_id:
        return []
    existing = data_cache.get_cache(user_id, 'dashboard_v2_data')
    if existing and not force:
        return existing
    lock = _get_user_lock(user_id)
    with lock:
        # Re-checar dentro do lock
        existing_inside = data_cache.get_cache(user_id, 'dashboard_v2_data')
        if existing_inside and not force:
            return existing_inside
        print(f"[DASHBOARD_EXECUTIVO] (Helper) Carregando dados fresh para user {user_id} (force={force})")
        query = supabase_admin.table('vw_importacoes_6_meses_abertos_dash').select('*')
        
        # Verificar se usuário precisa de filtragem por empresa
        perfil_principal = user_data.get('perfil_principal', '')
        
        # REGRA CORRIGIDA: admin_operacao deve ver TODAS as empresas, não apenas as associadas
        if role == 'cliente_unique':
            user_cnpjs = get_user_companies(user_data)
            if user_cnpjs:
                query = query.in_('cnpj_importador', user_cnpjs)
                print(f"[DASHBOARD_EXECUTIVO] (Helper) Cliente filtrando por CNPJs: {len(user_cnpjs)} empresas")
            else:
                print(f"[DASHBOARD_EXECUTIVO] (Helper) Cliente sem CNPJs vinculados -> dados vazios")
                data_cache.set_cache(user_id, 'dashboard_v2_data', [])
                return []
        elif role == 'interno_unique' and perfil_principal not in ['admin_operacao', 'master_admin']:
            # Interno não-admin deve ver apenas suas empresas associadas
            user_cnpjs = get_user_companies(user_data)
            if user_cnpjs:
                query = query.in_('cnpj_importador', user_cnpjs)
                print(f"[DASHBOARD_EXECUTIVO] (Helper) Interno filtrando por CNPJs: {len(user_cnpjs)} empresas")
            else:
                print(f"[DASHBOARD_EXECUTIVO] (Helper) Interno sem CNPJs vinculados -> dados vazios")
                data_cache.set_cache(user_id, 'dashboard_v2_data', [])
                return []
        else:
            print(f"[DASHBOARD_EXECUTIVO] (Helper) Admin vê todos os dados (perfil: {perfil_principal})")
        def _run_main_query():
            return query.execute()
        result = run_with_retries('dashboard_executivo.helper_load_data', _run_main_query, max_attempts=3, base_delay_seconds=0.8,
                                  should_retry=lambda e: 'Server disconnected' in str(e) or 'timeout' in str(e).lower())
        raw = result.data or []
        if not raw:
            print('[DASHBOARD_EXECUTIVO] (Helper) Nenhum dado retornado da view')
            data_cache.set_cache(user_id, 'dashboard_v2_data', [])
            return []
        enriched = enrich_data_with_despesas_view(raw)
        data_cache.set_cache(user_id, 'dashboard_v2_data', enriched)
        session['dashboard_v2_loaded'] = True
        return enriched

def calculate_custo_from_despesas_processo(despesas_processo):
    """
    Calcular custo total baseado no campo JSON despesas_processo
    Reproduz a lógica do frontend processExpensesByCategory()
    """
    try:
        if not despesas_processo:
            return 0.0
        
        # Se for string JSON, converter para lista
        if isinstance(despesas_processo, str):
            despesas_list = json.loads(despesas_processo)
        else:
            despesas_list = despesas_processo
        
        if not isinstance(despesas_list, list):
            return 0.0
        
        total_custo = 0.0
        for despesa in despesas_list:
            if isinstance(despesa, dict) and 'valor_custo' in despesa:
                valor = despesa.get('valor_custo', 0)
                
                # CORREÇÃO: Tratar valores como string também (igual ao frontend)
                if valor is not None and valor != '':
                    try:
                        # Converter para float (funciona com string e números)
                        valor_float = float(valor)
                        if not pd.isna(valor_float) and not np.isinf(valor_float):
                            total_custo += valor_float
                    except (ValueError, TypeError):
                        # Se não conseguir converter, ignore o valor
                        continue
        
        return total_custo
        
    except Exception as e:
        print(f"[CUSTO_CALCULATION] Erro ao calcular custo: {str(e)}")
        return 0.0

def calculate_custo_from_vw_despesas(ref_unique):
    """
    Calcular custo total de um processo usando a view vw_despesas_6_meses
    Esta é a fonte correta que contém os filtros aplicados
    """
    try:
        if not ref_unique:
            return 0.0
        
        print(f"[DESPESAS_VIEW] Consultando vw_despesas_6_meses para ref_unique: {ref_unique}")
        
        # Consultar view de despesas com filtros aplicados
        query = supabase_admin.table('vw_despesas_6_meses').select('valor_custo').eq('ref_unique', ref_unique)
        result = query.execute()
        
        if not result.data:
            print(f"[DESPESAS_VIEW] Nenhuma despesa encontrada para {ref_unique}")
            return 0.0
        
        total_custo = 0.0
        count_items = 0
        
        for despesa in result.data:
            valor_custo = despesa.get('valor_custo', 0)
            if valor_custo is not None and valor_custo != '':
                try:
                    valor_float = float(valor_custo)
                    if not pd.isna(valor_float) and not np.isinf(valor_float):
                        total_custo += valor_float
                        count_items += 1
                except (ValueError, TypeError):
                    continue
        
        print(f"[DESPESAS_VIEW] {ref_unique}: {count_items} itens, Total: R$ {total_custo:,.2f}")
        return total_custo
        
    except Exception as e:
        print(f"[DESPESAS_VIEW] Erro ao consultar despesas para {ref_unique}: {str(e)}")
        return 0.0

def enrich_data_with_despesas_view(data):
    """
    Enriquecer dados dos processos com custos calculados da vw_despesas_6_meses
    OTIMIZAÇÃO: Uma única consulta batch em vez de consultas individuais
    """
    try:
        print(f"[DESPESAS_VIEW] Enriquecendo {len(data)} processos com dados da view de despesas...")
        
        # Extrair todos os ref_unique de uma vez
        ref_uniques = [item.get('ref_unique') for item in data if item.get('ref_unique')]
        print(f"[DESPESAS_VIEW] Consultando custos para {len(ref_uniques)} ref_unique únicos...")
        
        # OTIMIZAÇÃO: Uma única consulta para todos os ref_unique
        despesas_map = {}
        if ref_uniques:
            try:
                # Consultar em lotes de 1000 para evitar limite de query
                batch_size = 1000
                for i in range(0, len(ref_uniques), batch_size):
                    batch = ref_uniques[i:i + batch_size]
                    print(f"[DESPESAS_VIEW] Processando lote {i//batch_size + 1}: {len(batch)} registros")
                    
                    try:
                        # Consulta batch
                        query = supabase_admin.table('vw_despesas_6_meses').select('ref_unique, valor_custo').in_('ref_unique', batch)
                        result = query.execute()
                        
                        if result.data:
                            # Agrupar por ref_unique e somar custos
                            for despesa in result.data:
                                ref_unique = despesa.get('ref_unique')
                                valor_custo = despesa.get('valor_custo', 0)
                                
                                if ref_unique:
                                    if ref_unique not in despesas_map:
                                        despesas_map[ref_unique] = 0
                                    
                                    # Somar valor_custo
                                    if valor_custo is not None and valor_custo != '':
                                        try:
                                            valor_float = float(valor_custo)
                                            if not pd.isna(valor_float) and not np.isinf(valor_float):
                                                despesas_map[ref_unique] += valor_float
                                        except (ValueError, TypeError):
                                            continue
                    
                    except Exception as batch_error:
                        # Tratar erro específico de view não encontrada
                        error_str = str(batch_error)
                        if '42P01' in error_str or 'does not exist' in error_str.lower():
                            print(f"[DESPESAS_VIEW] ⚠️ View vw_despesas_6_meses não existe - usando fallback para JSON")
                            # Marcar que a view não existe para evitar tentativas futuras
                            break
                        else:
                            print(f"[DESPESAS_VIEW] Erro na consulta batch: {batch_error}")
                            continue
                
                print(f"[DESPESAS_VIEW] Encontrados custos para {len(despesas_map)} processos")
                
            except Exception as e:
                print(f"[DESPESAS_VIEW] Erro na consulta batch: {str(e)}")
                despesas_map = {}
        
        # Enriquecer dados originais
        enriched_data = []
        total_encontrados = 0
        fallback_original = 0
        
        for item in data:
            enriched_item = item.copy()
            ref_unique = item.get('ref_unique')
            
            # Custo original do campo despesas_processo
            custo_original = calculate_custo_from_despesas_processo(item.get('despesas_processo'))
            enriched_item['custo_total_original'] = custo_original
            
            # Custo da view vw_despesas_6_meses (batch)
            custo_view = despesas_map.get(ref_unique, 0)
            enriched_item['custo_total_view'] = custo_view
            
            # Usar o custo da view como oficial (com fallback se zero)
            if custo_view > 0:
                enriched_item['custo_total'] = custo_view
            elif custo_original > 0:
                # Fallback para custo calculado pelo JSON de despesas
                enriched_item['custo_total'] = custo_original
                fallback_original += 1
            else:
                enriched_item['custo_total'] = 0.0
            
            if custo_view > 0:
                total_encontrados += 1
            
            # Log para processo 6555 especificamente
            if ref_unique and '6555' in str(ref_unique):
                print(f"[DESPESAS_VIEW] Processo 6555 -> View: R$ {custo_view:,.2f}, Original: R$ {custo_original:,.2f}")
            
            enriched_data.append(enriched_item)
        
        print(f"[DESPESAS_VIEW] Enriquecimento concluído: {total_encontrados}/{len(data)} processos com custos encontrados na view | Fallback JSON: {fallback_original}")
        return enriched_data
        
    except Exception as e:
        print(f"[DESPESAS_VIEW] Erro no enriquecimento: {str(e)}")
        return data  # Retornar dados originais em caso de erro

# Blueprint com configuração para templates e static locais
bp = Blueprint('dashboard_executivo', __name__, 
               url_prefix='/dashboard-executivo',
               template_folder='templates',
               static_folder='static',
               static_url_path='/dashboard-executivo/static')

def clean_data_for_json(data):
    """Remove valores NaN e converte para tipos JSON-safe"""
    if isinstance(data, dict):
        return {k: clean_data_for_json(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_data_for_json(item) for item in data]
    elif pd.isna(data) or data is None:
        return None  # CORREÇÃO: Manter None para campos de data
    elif isinstance(data, float) and (np.isnan(data) or np.isinf(data)):
        return None  # CORREÇÃO: Manter None para campos de data
    elif isinstance(data, (np.integer, np.int64, np.int32, np.int16, np.int8)):
        # CORREÇÃO: Tratar explicitamente tipos numpy integer
        if np.isnan(data) or np.isinf(data):
            return None
        return int(data)
    elif isinstance(data, (np.floating, np.float64, np.float32)):
        # CORREÇÃO: Tratar explicitamente tipos numpy float
        if np.isnan(data) or np.isinf(data):
            return None
        return float(data)
    elif hasattr(data, 'item'):
        # CORREÇÃO: Para qualquer tipo numpy scalar, usar .item() para converter para tipo Python nativo
        try:
            return data.item()
        except (ValueError, OverflowError):
            return None
    else:
        return data

def filter_by_date_python(item_date, data_inicio, data_fim):
    """Filtrar data usando Python (formato brasileiro DD/MM/YYYY)"""
    try:
        if not item_date:
            return False
        
        # Converter data do item (DD/MM/YYYY para YYYY-MM-DD)
        if '/' in item_date:
            day, month, year = item_date.split('/')
            item_date_iso = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        else:
            item_date_iso = item_date
        
        # Converter para datetime
        item_dt = datetime.strptime(item_date_iso, '%Y-%m-%d')
        inicio_dt = datetime.strptime(data_inicio, '%Y-%m-%d')
        fim_dt = datetime.strptime(data_fim, '%Y-%m-%d')
        
        return inicio_dt <= item_dt <= fim_dt
    except Exception as e:
        print(f"[DASHBOARD_EXECUTIVO] Erro ao filtrar data: {str(e)}")
        return False

def apply_filters(data):
    """Aplicar filtros aos dados baseado nos parâmetros da requisição"""
    try:
        # Obter filtros da requisição
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        material = request.args.get('material')
        cliente = request.args.get('cliente')
        modal = request.args.get('modal')
        canal = request.args.get('canal')
        status_processo = request.args.get('status_processo')
        kpi_status = request.args.get('kpi_status')  # NOVO: Filtro por KPI clicável
        
        filtered_data = data
        
        # Pré-normalizar campos usados para contain checks em lower() para evitar recomputo por item
        def norm(s):
            return str(s).lower() if s is not None else ''
        
        # Helper para extrair número do status_timeline
        def get_timeline_number(status_timeline):
            """Extrair número do status_timeline (ex: '3 - Agd Chegada' -> 3)"""
            if not status_timeline:
                return None
            try:
                status_str = str(status_timeline).strip()
                # Ignorar N/A
                if status_str.upper() == 'N/A':
                    return None
                if '-' in status_str:
                    return int(status_str.split('-')[0].strip())
                return int(status_str)
            except:
                return None
        
        # Filtrar por data
        if data_inicio and data_fim:
            filtered_data = [item for item in filtered_data 
                           if filter_by_date_python(item.get('data_abertura'), data_inicio, data_fim)]
        
        # Filtrar por material (múltiplas seleções)
        if material:
            materiais_lista = [m.strip().lower() for m in material.split(',') if m.strip()]
            if materiais_lista:
                filtered_data = [item for item in filtered_data 
                               if any(mat in norm(item.get('mercadoria')) for mat in materiais_lista)]
        
        # Filtrar por cliente (múltiplas seleções)
        if cliente:
            clientes_lista = [c.strip().lower() for c in cliente.split(',') if c.strip()]
            if clientes_lista:
                filtered_data = [item for item in filtered_data 
                               if any(cli in norm(item.get('importador')) for cli in clientes_lista)]
        
        # Filtrar por modal (múltiplas seleções)
        if modal:
            modais_lista = [m.strip().lower() for m in modal.split(',') if m.strip()]
            if modais_lista:
                filtered_data = [item for item in filtered_data 
                               if any(mod in norm(item.get('modal')) for mod in modais_lista)]
        
        # Filtrar por canal (múltiplas seleções)
        if canal:
            canais_lista = [c.strip().lower() for c in canal.split(',') if c.strip()]
            if canais_lista:
                filtered_data = [item for item in filtered_data 
                               if any(can in norm(item.get('canal')) for can in canais_lista)]
        
        # Filtrar por status do processo (aberto/fechado) - REGRA CORRIGIDA usando status_macro_sistema
        if status_processo:
            if status_processo == 'aberto':
                # Processo aberto: status_macro_sistema ≠ "PROCESSO CONCLUIDO" (incluindo nulls)
                filtered_data = [item for item in filtered_data 
                               if item.get('status_macro_sistema') != 'PROCESSO CONCLUIDO']
            elif status_processo == 'fechado':
                # Processo fechado: status_macro_sistema = "PROCESSO CONCLUIDO"
                filtered_data = [item for item in filtered_data 
                               if item.get('status_macro_sistema') == 'PROCESSO CONCLUIDO']
        
        # NOVO: Filtrar por status de KPI clicável
        if kpi_status:
            from datetime import datetime, timedelta
            
            # Helper para verificar período de chegada
            def in_periodo_chegada(item, periodo):
                try:
                    data_chegada = item.get('data_chegada')
                    if not data_chegada:
                        return False
                    
                    # Parse data brasileira DD/MM/YYYY
                    if isinstance(data_chegada, str):
                        parts = data_chegada.split('/')
                        if len(parts) == 3:
                            data_obj = datetime(int(parts[2]), int(parts[1]), int(parts[0]))
                        else:
                            return False
                    else:
                        data_obj = data_chegada
                    
                    hoje = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                    
                    if periodo == 'semana':
                        # CORRIGIDO: Usar semana completa (segunda a domingo) como o KPI
                        dia_semana = hoje.weekday()  # 0=segunda, 6=domingo
                        inicio_semana = hoje - timedelta(days=dia_semana)
                        fim_semana = inicio_semana + timedelta(days=6)
                        return inicio_semana <= data_obj <= fim_semana
                    elif periodo == 'mes':
                        # Mês atual completo (1º ao último dia)
                        primeiro_dia_mes = hoje.replace(day=1)
                        if hoje.month == 12:
                            ultimo_dia_mes = hoje.replace(day=31)
                        else:
                            proximo_mes = hoje.replace(month=hoje.month + 1, day=1)
                            ultimo_dia_mes = proximo_mes - timedelta(days=1)
                        return primeiro_dia_mes <= data_obj <= ultimo_dia_mes
                except:
                    return False
                return False
            
            if kpi_status == 'processos_abertos':
                # Processos com timeline 2-4 (Agd Embarque, Chegada, Registro)
                filtered_data = [item for item in filtered_data 
                               if 2 <= get_timeline_number(item.get('status_timeline')) <= 4]
            elif kpi_status == 'agd_embarque':
                # Timeline 2
                filtered_data = [item for item in filtered_data 
                               if get_timeline_number(item.get('status_timeline')) == 2]
            elif kpi_status == 'agd_chegada':
                # Timeline 3
                filtered_data = [item for item in filtered_data 
                               if get_timeline_number(item.get('status_timeline')) == 3]
            elif kpi_status == 'agd_liberacao':
                # Timeline 4
                filtered_data = [item for item in filtered_data 
                               if get_timeline_number(item.get('status_timeline')) == 4]
            elif kpi_status == 'agd_fechamento':
                # Timeline 6
                filtered_data = [item for item in filtered_data 
                               if get_timeline_number(item.get('status_timeline')) == 6]
            elif kpi_status == 'chegando_semana':
                # Chegando esta semana
                filtered_data = [item for item in filtered_data 
                               if in_periodo_chegada(item, 'semana')]
            elif kpi_status == 'chegando_mes':
                # Chegando este mês
                filtered_data = [item for item in filtered_data 
                               if in_periodo_chegada(item, 'mes')]
        
        return filtered_data
        
    except Exception as e:
        print(f"[DASHBOARD_EXECUTIVO] Erro ao aplicar filtros: {str(e)}")
        return data

def user_can_view_materials(user_data):
    """
    Verificar se o usuário pode visualizar dados de materiais.
    Retorna True apenas para usuários vinculados às empresas KINGSPAN ou CISER.
    """
    try:
        if not user_data:
            return False
            
        user_role = user_data.get('role')
        
        # Admin e interno_unique sempre podem ver materiais
        if user_role in ['admin', 'interno_unique']:
            return True
            
        # Para cliente_unique, verificar empresas vinculadas
        if user_role == 'cliente_unique':
            user_companies = get_user_companies(user_data)
            if not user_companies:
                return False
                
            # Buscar nomes das empresas vinculadas ao usuário pelos CNPJs
            try:
                empresas_response = (
                    supabase_admin
                    .table('cad_clientes_sistema')
                    .select('nome_cliente, cnpjs')
                    .eq('ativo', True)
                    .execute()
                )
                
                user_company_names = []
                for empresa in empresas_response.data:
                    cnpjs_empresa = empresa.get('cnpjs', [])
                    if isinstance(cnpjs_empresa, list):
                        # Normalizar CNPJs da empresa
                        cnpjs_normalizados = [re.sub(r'\D', '', str(cnpj)) for cnpj in cnpjs_empresa if cnpj]
                        # Verificar se algum CNPJ do usuário está na empresa
                        if any(cnpj in user_companies for cnpj in cnpjs_normalizados):
                            user_company_names.append(empresa.get('nome_cliente', '').upper())
                
                print(f"[MATERIALS_PERMISSION] Usuário {user_data.get('id')} vinculado às empresas: {user_company_names}")
                
                # Verificar se o usuário pertence a KINGSPAN ou CISER
                allowed_companies = ['KINGSPAN', 'CISER']
                has_material_permission = any(
                    any(allowed in company_name for allowed in allowed_companies)
                    for company_name in user_company_names
                )
                
                print(f"[MATERIALS_PERMISSION] Usuário pode ver materiais: {has_material_permission}")
                return has_material_permission
                
            except Exception as e:
                print(f"[MATERIALS_PERMISSION] Erro ao verificar empresas: {str(e)}")
                return False
        
        return False
        
    except Exception as e:
        print(f"[MATERIALS_PERMISSION] Erro na verificação de permissão: {str(e)}")
        return False

@bp.route('/')
@login_required
@perfil_required('importacoes', 'dashboard_executivo')
def index():
    """Página principal do Dashboard Executivo - APENAS para módulo de importações"""
    print(f"[DASHBOARD_EXECUTIVO] Acesso autorizado ao dashboard executivo de importações")
    
    # Verificar se é cliente_unique sem empresas associadas
    user_data = session.get('user', {})
    user_role = user_data.get('role')
    perfil_principal = user_data.get('perfil_principal', '')
    
    if user_role == 'cliente_unique':
        user_cnpjs = get_user_companies(user_data)
        if not user_cnpjs:
            print(f"[DASHBOARD_EXECUTIVO] Cliente {user_data.get('email')} sem empresas vinculadas - exibindo aviso")
            # Passar flag para o template indicar que deve mostrar aviso
            return render_template('dashboard_executivo.html', show_company_warning=True)
    
    # Verificar se é interno_unique sem empresas associadas (exceto admin_operacao e master_admin)
    # CORREÇÃO: admin_operacao deve ver TODOS os dados quando sem empresas específicas
    if user_role == 'interno_unique' and perfil_principal not in ['admin_operacao', 'master_admin']:
        user_cnpjs = get_user_companies(user_data)
        if not user_cnpjs:
            print(f"[DASHBOARD_EXECUTIVO] Usuário interno {user_data.get('email')} (perfil: {perfil_principal}) sem empresas vinculadas - exibindo aviso")
            # Passar flag para o template indicar que deve mostrar aviso
            return render_template('dashboard_executivo.html', show_company_warning=True)
    
    return render_template('dashboard_executivo.html')

@bp.route('/api/load-data')
@login_required
@perfil_required('importacoes', 'dashboard_executivo')
def load_data():
    """Carregar dados da tabela importacoes_processos_aberta"""
    try:
        print("[DASHBOARD_EXECUTIVO] Iniciando carregamento de dados da tabela...")
        
        # Obter dados do usuário
        user_data = session.get('user', {})
        user_role = user_data.get('role')
        user_id = user_data.get('id')
        
        # Usar helper resiliente (elimina race conditions)
        enriched_data = fetch_and_cache_dashboard_data(user_data)
        if not enriched_data:
            return jsonify({'success': False, 'error': 'Nenhum dado encontrado', 'data': []})

        # Log simples de estrutura
        first_with_expenses = next((r for r in enriched_data if r.get('despesas_processo')), None)
        if first_with_expenses:
            print(f"[DASHBOARD_EXECUTIVO] Exemplo despesas_processo (primeiro com dados): {str(first_with_expenses.get('despesas_processo'))[:120]} ...")
        print(f"[DASHBOARD_EXECUTIVO] Total registros enriquecidos: {len(enriched_data)}")

        return jsonify({'success': True, 'data': enriched_data, 'total_records': len(enriched_data)})
        
    except Exception as e:
        print(f"[DASHBOARD_EXECUTIVO] Erro ao carregar dados: {str(e)}")
        # Fallback: se houver dados previamente cacheados, retorne-os para evitar quebra na UX
        try:
            user_data = session.get('user', {})
            user_id = user_data.get('id')
            cached = data_cache.get_cache(user_id, 'dashboard_v2_data')
            if cached:
                print(f"[DASHBOARD_EXECUTIVO] Retornando dados do cache após erro ({len(cached)} registros)")
                return jsonify({'success': True, 'data': cached, 'total_records': len(cached), 'source': 'server_cache_fallback'})
        except Exception:
            pass
        return jsonify({'success': False, 'error': str(e), 'data': []}), 500

@bp.route('/api/kpis')
@login_required
@perfil_required('importacoes', 'dashboard_executivo')
def dashboard_kpis():
    """Calcular KPIs para o dashboard executivo
    
    IMPORTANTE: KPIs sempre mostram valores TOTAIS, mesmo quando há filtro de kpi_status.
    Apenas tabelas e gráficos são filtrados pelo kpi_status.
    """
    try:
        # Obter dados (auto-carrega se necessário)
        user_data = session.get('user', {})
        user_id = user_data.get('id')
        data = fetch_and_cache_dashboard_data(user_data)
        if not data:
            return jsonify({'success': False, 'error': 'Dados não encontrados após tentativa de carregamento.', 'kpis': {}})
        
        # NOVO: Remover temporariamente kpi_status dos filtros para KPIs mostrarem valores totais
        kpi_status_backup = request.args.get('kpi_status')
        if kpi_status_backup:
            # Criar uma cópia do request.args sem kpi_status
            from werkzeug.datastructures import ImmutableMultiDict
            args_dict = request.args.to_dict()
            args_dict.pop('kpi_status', None)
            request.args = ImmutableMultiDict(args_dict)
        
        # Aplicar filtros (agora sem kpi_status)
        filtered_data = apply_filters(data)
        
        # Restaurar kpi_status se existia
        if kpi_status_backup:
            args_dict['kpi_status'] = kpi_status_backup
            request.args = ImmutableMultiDict(args_dict)
        
        df = pd.DataFrame(filtered_data)
        
        # Garantir colunas de custo
        if 'custo_total_view' not in df.columns:
            df['custo_total_view'] = 0.0
        if 'custo_total' not in df.columns:
            df['custo_total'] = 0.0
        if 'custo_total_original' not in df.columns:
            df['custo_total_original'] = 0.0
        
        # Construir custo_calculado com fallback (com cast explícito para evitar warning)
        df['custo_calculado'] = df['custo_total_view'].astype(float)
        mask_view_zero = df['custo_calculado'] <= 0
        df.loc[mask_view_zero, 'custo_calculado'] = df.loc[mask_view_zero, 'custo_total'].astype(float)
        mask_total_zero = df['custo_calculado'] <= 0
        df.loc[mask_total_zero, 'custo_calculado'] = df.loc[mask_total_zero, 'custo_total_original'].astype(float)
        
        # Fallback final: recalcular a partir de despesas_processo quando ainda zero
        if 'despesas_processo' in df.columns:
            recalc = 0
            for idx in df.index[df['custo_calculado'] <= 0]:
                valor = calculate_custo_from_despesas_processo(df.at[idx, 'despesas_processo'])
                if valor > 0:
                    df.at[idx, 'custo_calculado'] = valor
                    recalc += 1
            if recalc:
                print(f"[DEBUG_KPI] Recalculados {recalc} custos a partir de despesas_processo")
        
        registros_com_custo = (df['custo_calculado'] > 0).sum()
        total_despesas_debug = df['custo_calculado'].sum()
        
        # Log dos primeiros 5 registros para verificação
        for idx, row in df.head(5).iterrows():
            ref_unique = row.get('ref_unique', 'N/A')
            custo_view = row.get('custo_total_view', 0)  # CORRIGIDO: usar custo_total_view
            print(f"[DEBUG_KPI] Registro {idx}: ref={ref_unique}, custo_total_view={custo_view:,.2f}")
            
            # Log específico para o processo 6555
            if '6555' in str(ref_unique):
                print(f"[DEBUG_KPI] *** PROCESSO 6555 ENCONTRADO: custo_total_view={custo_view:,.2f} ***")
        
        print(f"[DEBUG_KPI] Registros com custo > 0: {registros_com_custo}/{len(df)}")
        print(f"[DEBUG_KPI] Total despesas calculado: {total_despesas_debug:,.2f}")
        
        # Calcular KPIs executivos usando o novo custo
        total_processos = len(df)
        total_despesas = df['custo_calculado'].sum()
        ticket_medio = (total_despesas / total_processos) if total_processos > 0 else 0
        
        print(f"[DEBUG_KPI] KPIs Calculados:")
        print(f"[DEBUG_KPI] - Total processos: {total_processos}")
        print(f"[DEBUG_KPI] - Total despesas: {total_despesas:,.2f}")
        print(f"[DEBUG_KPI] - Ticket médio: {ticket_medio:,.2f}")
        
        # Comparar com custo_total_view original se disponível
        if 'custo_total_view' in df.columns:
            total_original = df['custo_total_view'].sum()
            print(f"[DEBUG_KPI] Total original (custo_total_view): {total_original:,.2f}")
            print(f"[DEBUG_KPI] Diferença: {total_despesas - total_original:,.2f}")

        # Função robusta para normalizar status
        import unicodedata, re
        def normalize_status(status):
            if pd.isna(status) or not status:
                return ""
            status = unicodedata.normalize('NFKD', str(status)).encode('ASCII', 'ignore').decode('ASCII')
            status = status.upper()
            status = re.sub(r'[^A-Z0-9 ]', '', status)
            status = re.sub(r'\s+', ' ', status)
            status = status.strip()
            # Normalizações finais para garantir agrupamento correto
            if status in ['AG EMBARQUE', 'AG. EMBARQUE']: return 'AG EMBARQUE'
            if status in ['ABERTURA']: return 'AG EMBARQUE'
            if status in ['AG CHEGADA', 'AG. CHEGADA']: return 'AG CHEGADA'
            if status in ['AG CARREGAMENTO', 'AG CARREGAMENTO']: return 'AG CARREGAMENTO'
            if status in ['AG FECHAMENTO', 'AG FECHAMENTO']: return 'AG FECHAMENTO'
            if status in ['AG REGISTRO', 'AG REGISTRO']: return 'AG REGISTRO'
            if status in ['AG MAPA', 'AG MAPA']: return 'AG MAPA'
            if status in ['DI REGISTRADA', 'DI REGISTRADA']: return 'DI REGISTRADA'
            if status in ['DI DESEMBARACADA', 'DI DESEMBARACADA']: return 'AG ENTREGA'
            if status in ['NUMERARIO ENVIADO', 'NUMERARIO ENVIADO']: return 'NUMERARIO ENVIADO'
            return status

        # CORREÇÃO: Usar status_timeline como fonte única para KPIs
        def get_timeline_number(status_timeline):
            """Extrair número do status_timeline (ex: '2 - Agd Embarque' -> 2)"""
            if not status_timeline:
                return 0
            try:
                # Tentar extrair número do início da string
                status_str = str(status_timeline).strip()
                # Ignorar N/A
                if status_str.upper() == 'N/A':
                    return 0
                if status_str.startswith(('1', '2', '3', '4', '5', '6')):
                    return int(status_str.split(' ')[0].replace('-', '').strip())
                return 0
            except:
                return 0

        # Aplicar normalização se a coluna existir
        if 'status_timeline' in df.columns:
            # Criar coluna numérica para facilitar comparações
            df['timeline_number'] = df['status_timeline'].apply(get_timeline_number)
            
            # Calcular métricas baseadas no status_timeline - NOVA REGRA ATUALIZADA
            # 2 - Agd Embarque, 3 - Agd Chegada, 4 - Agd Registro (Liberação), 6 - Finalizado (Fechamento)
            agd_embarque = len(df[df['timeline_number'] == 2])      # 2 - Agd Embarque
            agd_chegada = len(df[df['timeline_number'] == 3])       # 3 - Agd Chegada  
            agd_liberacao = len(df[df['timeline_number'] == 4])     # 4 - Agd Registro (Liberação)
            agd_fechamento = len(df[df['timeline_number'] == 6])    # 6 - Finalizado (Fechamento)
            
            print(f"[DEBUG_KPI] Status Timeline counts (REGRA PADRONIZADA):")
            print(f"[DEBUG_KPI] 2 - Agd Embarque: {agd_embarque}")
            print(f"[DEBUG_KPI] 3 - Agd Chegada: {agd_chegada}")
            print(f"[DEBUG_KPI] 4 - Agd Registro/Liberação: {agd_liberacao}")
            print(f"[DEBUG_KPI] 6 - Finalizado/Fechamento: {agd_fechamento}")
        else:
            agd_embarque = 0
            agd_chegada = 0
            agd_liberacao = 0
            agd_fechamento = 0

        # Chegando Este Mês/Semana: considerar TODAS as datas de chegada dentro do mês/semana (igual dashboard materiais)
        hoje = pd.Timestamp.now().normalize()
        primeiro_dia_mes = hoje.replace(day=1)
        ultimo_dia_mes = (primeiro_dia_mes + pd.DateOffset(months=1)) - pd.Timedelta(days=1)
        
        # Calcular semana atual (SEGUNDA a DOMINGO) - CORRIGIDO
        # hoje.dayofweek: 0=Segunda, 1=Terça, ..., 6=Domingo
        dias_desde_segunda = hoje.dayofweek  # Dias desde a segunda-feira
        inicio_semana = hoje - pd.Timedelta(days=dias_desde_segunda)  # Volta para segunda
        fim_semana = inicio_semana + pd.Timedelta(days=6)  # Domingo (6 dias depois da segunda)
        
        chegando_mes = 0
        chegando_mes_custo = 0.0
        chegando_semana = 0
        chegando_semana_custo = 0.0
        if 'data_chegada' in df.columns:
            df['chegada_dt'] = pd.to_datetime(df['data_chegada'], format='%d/%m/%Y', errors='coerce')
            
            # Contar processos chegando esta semana
            for idx, row in df.iterrows():
                chegada = row.get('chegada_dt')
                custo = row.get('custo_calculado', 0.0)
                if custo is None:
                    custo = 0.0
                
                # Lógica para MÊS (independente de ser passado ou futuro)
                if pd.notnull(chegada) and primeiro_dia_mes <= chegada <= ultimo_dia_mes:
                    chegando_mes += 1
                    chegando_mes_custo += custo
                
                # Lógica para SEMANA (independente de ser passado ou futuro)
                if pd.notnull(chegada) and inicio_semana <= chegada <= fim_semana:
                    chegando_semana += 1
                    chegando_semana_custo += custo

        # Calcular processos abertos baseado no status_timeline
        # REGRA PADRONIZADA: Processos abertos são aqueles com timeline_number 2, 3, 4
        # Processos fechados são aqueles com timeline_number >= 5
        processos_abertos = 0
        processos_fechados = 0
        
        if 'status_timeline' in df.columns:
            # Processos abertos: timeline_number 2, 3, 4 (Agd Embarque, Chegada, Registro)
            processos_abertos = len(df[
                (df['timeline_number'] >= 2) & 
                (df['timeline_number'] <= 4)
            ])
            
            # Processos fechados: timeline_number >= 5 (Desembaraçado, Finalizado)
            processos_fechados = len(df[df['timeline_number'] >= 5])
        else:
            # Se não tiver coluna status_timeline, considerar todos como abertos
            processos_abertos = total_processos
            processos_fechados = 0

        print(f"[DEBUG_KPI] REGRA PADRONIZADA - Processos Abertos (timeline 2-4): {processos_abertos}")
        print(f"[DEBUG_KPI] REGRA PADRONIZADA - Processos Fechados (timeline ≥ 5): {processos_fechados}")
        print(f"[DEBUG_KPI] Total: {processos_abertos + processos_fechados} (deve ser igual a {total_processos})")

        kpis = {
            'total_processos': total_processos,
            'processos_abertos': processos_abertos,
            'processos_fechados': processos_fechados,
            'total_despesas': float(total_despesas),
            'ticket_medio': float(ticket_medio),
            'agd_embarque': agd_embarque,           # NOVO NOME
            'agd_chegada': agd_chegada,             # NOVO NOME
            'agd_liberacao': agd_liberacao,         # NOVO NOME  
            'agd_fechamento': agd_fechamento,       # NOVO NOME
            'chegando_mes': chegando_mes,
            'chegando_mes_custo': float(chegando_mes_custo),
            'chegando_semana': chegando_semana,
            'chegando_semana_custo': float(chegando_semana_custo)
            # Removidos: transit_time_medio, processos_mes, processos_semana
        }
        
        print(f"[DEBUG_KPI] KPIs finais: {kpis}")
        
        return jsonify({
            'success': True,
            'kpis': clean_data_for_json(kpis)
        })
        
    except Exception as e:
        print(f"[DASHBOARD_EXECUTIVO] Erro ao calcular KPIs: {str(e)}")
        # Fallback seguro
        return jsonify({'success': False, 'error': str(e), 'kpis': {}}), 200

@bp.route('/api/charts')
@login_required
@perfil_required('importacoes', 'dashboard_executivo')
def dashboard_charts():
    """Gerar dados para os gráficos do dashboard executivo"""
    try:
        # Obter dados (auto-carrega se necessário)
        user_data = session.get('user', {})
        user_id = user_data.get('id')
        data = fetch_and_cache_dashboard_data(user_data)
        if not data:
            return jsonify({'success': False, 'error': 'Dados não encontrados após tentativa de carregamento.', 'charts': {}})
        
        # Aplicar filtros se existirem
        filtered_data = apply_filters(data)
        df = pd.DataFrame(filtered_data)
        
        if 'custo_total_view' not in df.columns:
            df['custo_total_view'] = 0.0
        if 'custo_total' not in df.columns:
            df['custo_total'] = 0.0
        if 'custo_total_original' not in df.columns:
            df['custo_total_original'] = 0.0
        
        df['custo_calculado'] = df['custo_total_view'].astype(float)
        mask_view_zero = df['custo_calculado'] <= 0
        df.loc[mask_view_zero, 'custo_calculado'] = df.loc[mask_view_zero, 'custo_total'].astype(float)
        mask_total_zero = df['custo_calculado'] <= 0
        df.loc[mask_total_zero, 'custo_calculado'] = df.loc[mask_total_zero, 'custo_total_original'].astype(float)
        if 'despesas_processo' in df.columns:
            for idx in df.index[df['custo_calculado'] <= 0]:
                v = calculate_custo_from_despesas_processo(df.at[idx, 'despesas_processo'])
                if v > 0:
                    df.at[idx, 'custo_calculado'] = v
        print(f"[DEBUG_CHARTS] Total custo calculado (com fallback): {df['custo_calculado'].sum():,.2f}")
        
        # Gráfico Evolução Mensal
        monthly_chart = {'labels': [], 'datasets': []}
        if 'data_abertura' in df.columns:
            df['data_abertura_dt'] = pd.to_datetime(df['data_abertura'], format='%d/%m/%Y', errors='coerce')
            df_mensal = df.dropna(subset=['data_abertura_dt'])
            df_mensal['mes_ano'] = df_mensal['data_abertura_dt'].dt.strftime('%m/%Y')
            
            grouped = df_mensal.groupby('mes_ano').agg({
                'ref_unique': 'count',
                'custo_calculado': 'sum'  # USANDO CUSTO CALCULADO
            }).reset_index().sort_values('mes_ano')
            
            monthly_chart = {
                'labels': grouped['mes_ano'].tolist(),
                'datasets': [
                    {
                        'label': 'Quantidade de Processos',
                        'data': grouped['ref_unique'].tolist(),
                        'type': 'line',
                        'borderColor': '#007bff',
                        'backgroundColor': 'rgba(0, 123, 255, 0.1)',
                        'yAxisID': 'y1',
                        'tension': 0.4
                    },
                    {
                        'label': 'Custo Total (R$)',
                        'data': grouped['custo_calculado'].tolist(),  # USANDO CUSTO CALCULADO
                        'type': 'line',  # CORREÇÃO: Mudado de 'bar' para 'line' para consistência
                        'borderColor': '#28a745',
                        'backgroundColor': 'rgba(40, 167, 69, 0.1)',
                        'yAxisID': 'y',
                        'tension': 0.4
                    }
                ]
            }

        # Gráfico de Status do Processo - USANDO STATUS_TIMELINE PADRONIZADO
        status_chart = {'labels': [], 'data': []}
        try:
            if 'status_timeline' in df.columns:
                print('[DEBUG_CHARTS] Usando coluna status_timeline para Status Chart (PADRONIZADO)')
                # Filtrar N/A e contar status
                df_filtered = df[df['status_timeline'].str.upper() != 'N/A']
                status_counts = df_filtered['status_timeline'].fillna('Sem Info').value_counts()
                
                # Ordenar por número da timeline para manter ordem lógica
                # Extrair número de cada status para ordenação
                def extract_number(status_str):
                    try:
                        if pd.isna(status_str) or status_str == 'Sem Info':
                            return 99
                        parts = str(status_str).split('-')
                        return int(parts[0].strip()) if parts else 99
                    except:
                        return 99
                
                sorted_index = sorted(status_counts.index, key=extract_number)
                sorted_counts = [status_counts[idx] for idx in sorted_index]
                
                status_chart = {
                    'labels': sorted_index,
                    'data': sorted_counts
                }
                print(f'[DEBUG_CHARTS] Status Timeline encontrados: {sorted_index}')
            elif 'status_macro_sistema' in df.columns:
                print('[DEBUG_CHARTS] Usando coluna status_macro_sistema (fallback)')
                status_counts = df['status_macro_sistema'].fillna('Sem Info').value_counts().head(10)
                status_chart = {
                    'labels': status_counts.index.tolist(),
                    'data': status_counts.values.tolist()
                }
            elif 'status_processo' in df.columns:
                print('[DEBUG_CHARTS] Usando coluna status_processo (fallback 2)')
                status_counts = df['status_processo'].fillna('Sem Info').value_counts().head(10)
                status_chart = {
                    'labels': status_counts.index.tolist(),
                    'data': status_counts.values.tolist()
                }
            else:
                print('[DEBUG_CHARTS] Nenhuma coluna de status encontrada para o Status Chart')
        except Exception as e:
            print(f"[DEBUG_CHARTS] Erro ao montar Status Chart: {e}")

        # Gráfico de Modal
        grouped_modal_chart = {'labels': [], 'datasets': []}
        if 'modal' in df.columns:
            modal_grouped = df.groupby('modal').agg({
                'ref_unique': 'count',
                'custo_calculado': 'sum'  # USANDO CUSTO CALCULADO
            }).reset_index()
            
            grouped_modal_chart = {
                'labels': modal_grouped['modal'].tolist(),
                'datasets': [
                    {
                        'label': 'Quantidade de Processos',
                        'data': modal_grouped['ref_unique'].tolist(),
                        'type': 'bar',
                        'backgroundColor': 'rgba(54, 162, 235, 0.6)',
                        'borderColor': 'rgba(54, 162, 235, 1)',
                        'yAxisID': 'y1'
                    },
                    {
                        'label': 'Custo Total (R$)',
                        'data': modal_grouped['custo_calculado'].tolist(),  # USANDO CUSTO CALCULADO
                        'type': 'line',
                        'backgroundColor': 'rgba(255, 99, 132, 0.2)',
                        'borderColor': 'rgba(255, 99, 132, 1)',
                        'yAxisID': 'y'
                    }
                ]
            }

        # Gráfico URF Despacho (usar coluna urf_despacho)
        urf_chart = {'labels': [], 'data': []}
        if 'urf_despacho_normalizado' in df.columns:
            urf_counts = df['urf_despacho_normalizado'].value_counts().head(10)
            urf_chart = {'labels': urf_counts.index.tolist(), 'data': urf_counts.values.tolist()}
        elif 'urf_despacho' in df.columns:
            urf_counts = df['urf_despacho'].value_counts().head(10)
            urf_chart = {'labels': urf_counts.index.tolist(), 'data': urf_counts.values.tolist()}

        # Gráfico Materiais - APENAS para usuários KINGSPAN/CISER
        material_chart = {'labels': [], 'data': []}
        user_data = session.get('user', {})
        can_view_materials = user_can_view_materials(user_data)
        
        if can_view_materials and 'mercadoria' in df.columns:
            material_counts = df['mercadoria'].value_counts().head(10)
            material_chart = {
                'labels': material_counts.index.tolist(),
                'data': material_counts.values.tolist()
            }

        # NOVO: Tabela de Principais Materiais - APENAS para usuários KINGSPAN/CISER
        principais_materiais = {'data': []}
        if can_view_materials and 'mercadoria' in df.columns and 'data_chegada' in df.columns:
            try:
                print(f"[DASHBOARD_EXECUTIVO] Usuário autorizado para materiais, processando tabela...")
                # Agrupar por material e calcular métricas
                material_groups = df.groupby('mercadoria').agg({
                    'ref_unique': 'count',
                    'custo_calculado': 'sum',  # USANDO CUSTO CALCULADO
                    'data_chegada': 'first',
                    'transit_time_real': 'mean'
                }).reset_index()
                
                # Converter data_chegada para datetime para ordenação
                material_groups['data_chegada_dt'] = pd.to_datetime(
                    material_groups['data_chegada'], format='%d/%m/%Y', errors='coerce'
                )
                
                # Ordenar por data_chegada mais próxima (futura)
                hoje = pd.Timestamp.now()
                material_groups['is_future'] = material_groups['data_chegada_dt'] >= hoje
                material_groups = material_groups.sort_values([
                    'is_future', 'data_chegada_dt'
                ], ascending=[False, True])
                
                # Preparar dados da tabela
                table_data = []
                for _, row in material_groups.head(15).iterrows():
                    # Calcular se está chegando nos próximos 5 dias
                    is_urgente = False
                    dias_para_chegada = 0
                    if pd.notnull(row['data_chegada_dt']):
                        diff_days = (row['data_chegada_dt'] - hoje).days
                        is_urgente = 0 < diff_days <= 5
                        dias_para_chegada = diff_days if diff_days > 0 else 0
                    
                    table_data.append({
                        'material': row['mercadoria'],
                        'total_processos': int(row['ref_unique']),
                        'custo_total': float(row['custo_calculado']) if pd.notnull(row['custo_calculado']) else 0,  # USANDO CUSTO CALCULADO
                        'data_chegada': row['data_chegada'],
                        'transit_time': float(row['transit_time_real']) if pd.notnull(row['transit_time_real']) else 0,
                        'is_urgente': is_urgente,
                        'dias_para_chegada': dias_para_chegada
                    })
                
                principais_materiais = {'data': table_data}
                print(f"[DASHBOARD_EXECUTIVO] Tabela de materiais processada: {len(table_data)} itens")
                
            except Exception as e:
                print(f"[DASHBOARD_EXECUTIVO] Erro ao processar tabela de materiais: {str(e)}")
                principais_materiais = {'data': []}
        else:
            if not can_view_materials:
                print(f"[DASHBOARD_EXECUTIVO] Usuário não autorizado para ver materiais")
            else:
                print(f"[DASHBOARD_EXECUTIVO] Colunas de material não encontradas nos dados")

        charts = {
            'monthly': monthly_chart,
            'status': status_chart,
            'grouped_modal': grouped_modal_chart,
            'urf': urf_chart,
            'material': material_chart,
            'principais_materiais': principais_materiais  # NOVO
        }
        
        return jsonify({
            'success': True,
            'charts': clean_data_for_json(charts),
            'can_view_materials': can_view_materials  # NOVO: Informar frontend sobre permissão
        })
        
    except Exception as e:
        print(f"[DASHBOARD_EXECUTIVO] Erro ao gerar gráficos: {str(e)}")
        return jsonify({'success': False, 'error': str(e), 'charts': {}}), 200

@bp.route('/api/monthly-chart')
@login_required
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def monthly_chart():
    """Retorna dados do gráfico de evolução por granularidade (mensal, semanal, diário)"""
    try:
        granularidade = request.args.get('granularidade', 'mensal')
        user_data = session.get('user', {})
        user_id = user_data.get('id')
        data = fetch_and_cache_dashboard_data(user_data)
        if not data:
            return jsonify({'success': False, 'error': 'Dados não encontrados após tentativa de carregamento.', 'data': {}})
        
        # APLICAR FILTROS ANTES DE PROCESSAR O GRÁFICO
        filtered_data = apply_filters(data)
        df = pd.DataFrame(filtered_data)
        
        # Debug para verificar filtro de datas
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        print(f"[MONTHLY_CHART] Filtro de datas: {data_inicio} até {data_fim}")
        print(f"[MONTHLY_CHART] Dados após filtro: {len(df)} registros")
        
        # USAR CUSTO DA VIEW ENRIQUECIDA (custo_total_view calculado pelo enriquecimento)
        print("[MONTHLY_CHART] Usando custos da view vw_despesas_6_meses via enriquecimento...")
        
        # Usar o custo_total_view que foi calculado durante o enriquecimento dos dados
        if 'custo_total_view' not in df.columns:
            print("[MONTHLY_CHART] ERRO: Campo custo_total_view não encontrado! Usando fallback.")
            df['custo_total_view'] = 0.0
        
        df['custo_calculado'] = df['custo_total_view'].astype(float)
        mask_view_zero = df['custo_calculado'] <= 0
        df.loc[mask_view_zero, 'custo_calculado'] = df.loc[mask_view_zero, 'custo_total'].astype(float)
        mask_total_zero = df['custo_calculado'] <= 0
        df.loc[mask_total_zero, 'custo_calculado'] = df.loc[mask_total_zero, 'custo_total_original'].astype(float)
        if 'despesas_processo' in df.columns:
            for idx in df.index[df['custo_calculado'] <= 0]:
                v = calculate_custo_from_despesas_processo(df.at[idx, 'despesas_processo'])
                if v > 0:
                    df.at[idx, 'custo_calculado'] = v
        print(f"[MONTHLY_CHART] Total custo calculado (com fallback): {df['custo_calculado'].sum():,.2f}")
        
        # Garantir colunas necessárias
        if 'data_abertura' not in df.columns:
            return jsonify({'success': False, 'error': 'Colunas necessárias não encontradas.', 'data': {}})
        
        # Converter datas
        df['data_abertura_dt'] = pd.to_datetime(df['data_abertura'], format='%d/%m/%Y', errors='coerce')
        df = df.dropna(subset=['data_abertura_dt'])
        
        if granularidade == 'mensal':
            df['periodo'] = df['data_abertura_dt'].dt.strftime('%m/%Y')
        elif granularidade == 'semanal':
            df['periodo'] = df['data_abertura_dt'].dt.strftime('%Y-%U')
        elif granularidade == 'diario':
            df['periodo'] = df['data_abertura_dt'].dt.strftime('%d/%m/%Y')
        else:
            df['periodo'] = df['data_abertura_dt'].dt.strftime('%m/%Y')
        
        grouped = df.groupby('periodo').agg({
            'ref_unique': 'count',
            'custo_calculado': 'sum'  # USANDO CUSTO CALCULADO
        }).reset_index().sort_values('periodo')
        
        chart_data = {
            'periods': grouped['periodo'].tolist(),
            'processes': grouped['ref_unique'].tolist(),
            'values': grouped['custo_calculado'].tolist()  # USANDO CUSTO CALCULADO
        }
        
        return jsonify({'success': True, 'data': clean_data_for_json(chart_data)})
    except Exception as e:
        print(f"[DASHBOARD_EXECUTIVO] Erro ao gerar monthly_chart: {str(e)}")
        return jsonify({'success': False, 'error': str(e), 'data': {}}), 500

@bp.route('/api/recent-operations')
@login_required
@perfil_required('importacoes', 'dashboard_executivo')
def recent_operations():
    """Obter operações recentes para a tabela"""
    try:
        # Obter dados (auto-carrega se necessário)
        user_data = session.get('user', {})
        user_id = user_data.get('id')
        data = fetch_and_cache_dashboard_data(user_data)
        if not data:
            return jsonify({'success': False,'error': 'Dados não encontrados após tentativa de carregamento.','operations': []})
        
        # Aplicar filtros se existirem
        filtered_data = apply_filters(data)
        df = pd.DataFrame(filtered_data)
        
        # Garantir que há dados filtrados
        if df.empty:
            return jsonify({
                'success': True,
                'operations': []
            })
        
        # CORREÇÃO: Para mini popups funcionarem, precisamos de todos os dados
        # Separar dados para tabela (limitados) vs dados para mini popups (completos)
        
        # NOVO: Sempre mostrar TODOS os registros na tabela (sem limite de 50)
        kpi_status = request.args.get('kpi_status')
        limit_table = None  # Sem limite - sempre mostrar todos os registros
        
        # Para a tabela: Ordenar por data mais recente
        if 'data_abertura' in df.columns:
            df['data_abertura_dt'] = pd.to_datetime(df['data_abertura'], format='%d/%m/%Y', errors='coerce')
            df_sorted = df.sort_values('data_abertura_dt', ascending=False)
            df_table = df_sorted if limit_table is None else df_sorted.head(limit_table)
        else:
            df_table = df if limit_table is None else df.head(limit_table)
        
        # Para mini popups: manter todos os dados filtrados
        df_all = df
        
        # Selecionar colunas relevantes para a tabela E modal
        relevant_columns = [
            # Colunas para a tabela
            'ref_unique', 'importador', 'data_abertura', 'exportador_fornecedor', 
            'modal', 'status_processo', 'status_macro_sistema', 'custo_total', 'custo_total_view', 'data_chegada',
            
            # CORREÇÃO: Incluir status_timeline para mini popups funcionarem
            'status_timeline',
            
            # Colunas adicionais para o modal
            'ref_importador', 'cnpj_importador', 'status_macro', 'data_embarque', 'data_fechamento',
            'peso_bruto', 'urf_despacho', 'urf_despacho_normalizado', 'container',
            'transit_time_real', 'valor_cif_real', 'custo_frete_inter', 
            'custo_armazenagem', 'custo_honorarios', 'numero_di', 'data_registro',
            'canal', 'data_desembaraco', 'despesas_processo',
            
            # CORREÇÃO BUG: Incluir pais_procedencia e url_bandeira para o modal
            'pais_procedencia', 'pais_procedencia_normalizado', 'url_bandeira'
        ]
        
        # Colunas normalizadas disponíveis
        if 'mercadoria' in df_table.columns:
            relevant_columns.append('mercadoria')
        
        available_columns = [col for col in relevant_columns if col in df_table.columns]
        print(f"[DASHBOARD_EXECUTIVO] Colunas disponíveis: {available_columns}")
        print(f"[DASHBOARD_EXECUTIVO] Colunas faltando: {set(relevant_columns) - set(available_columns)}")
        
        # DEBUG: Verificar se data_fechamento está disponível
        if 'data_fechamento' in df_table.columns:
            print(f"[DASHBOARD_EXECUTIVO] ✅ Coluna 'data_fechamento' DISPONÍVEL no DataFrame")
        else:
            print(f"[DASHBOARD_EXECUTIVO] ❌ Coluna 'data_fechamento' NÃO ENCONTRADA no DataFrame")
            print(f"[DASHBOARD_EXECUTIVO] Colunas presentes no DataFrame: {list(df_table.columns)}")
        
        # Dados para a tabela (limitados a 50)
        operations_table_data = df_table[available_columns].to_dict('records')
        
        # Dados completos para mini popups (todos os dados filtrados)
        available_columns_all = [col for col in relevant_columns if col in df_all.columns]
        operations_all_data = df_all[available_columns_all].to_dict('records')
        
        # Corrigir o campo custo_total para priorizar custo_total_view/custo_total (igual ao modal)
        for operations_data in [operations_table_data, operations_all_data]:
            for op in operations_data:
                custo_view = op.get('custo_total_view')
                custo_total = op.get('custo_total')
                if custo_view is not None and custo_view > 0:
                    op['custo_total'] = custo_view
                elif custo_total is not None and custo_total > 0:
                    op['custo_total'] = custo_total
        
        # Log específico para o processo 6555 nos dados enviados para o frontend
        for op in operations_table_data:
            ref_unique = str(op.get('ref_unique', ''))
            if '6555' in ref_unique:
                print(f"[RECENT_OPERATIONS] *** PROCESSO 6555 DADOS PARA FRONTEND (TABELA) ***")
                print(f"[RECENT_OPERATIONS] ref_unique: {op.get('ref_unique', 'N/A')}")
                print(f"[RECENT_OPERATIONS] custo_total (enviado): {op.get('custo_total', 'N/A')}")
                print(f"[RECENT_OPERATIONS] custo_total_view: {op.get('custo_total_view', 'N/A')}")
                print(f"[RECENT_OPERATIONS] custo_total_original: {op.get('custo_total_original', 'N/A')}")
                break
        
        # Log específico para o processo 5360 - verificar data_fechamento
        for op in operations_all_data:
            ref_unique = str(op.get('ref_unique', ''))
            if '5360' in ref_unique:
                print(f"[RECENT_OPERATIONS] *** PROCESSO 5360 DADOS PARA FRONTEND (COMPLETO) ***")
                print(f"[RECENT_OPERATIONS] ref_unique: {op.get('ref_unique', 'N/A')}")
                print(f"[RECENT_OPERATIONS] data_abertura: {op.get('data_abertura', 'N/A')}")
                print(f"[RECENT_OPERATIONS] data_embarque: {op.get('data_embarque', 'N/A')}")
                print(f"[RECENT_OPERATIONS] data_chegada: {op.get('data_chegada', 'N/A')}")
                print(f"[RECENT_OPERATIONS] data_fechamento: {op.get('data_fechamento', 'N/A')}")
                print(f"[RECENT_OPERATIONS] data_registro: {op.get('data_registro', 'N/A')}")
                print(f"[RECENT_OPERATIONS] Campos disponíveis: {list(op.keys())}")
                break
        
        return jsonify({
            'success': True,
            'operations': clean_data_for_json(operations_table_data),
            'operations_all': clean_data_for_json(operations_all_data)  # NOVO: dados completos para mini popups
        })
        
    except Exception as e:
        print(f"[DASHBOARD_EXECUTIVO] Erro ao obter operações recentes: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'operations': []
        }), 500

@bp.route('/api/filter-options')
@login_required
@perfil_required('importacoes', 'dashboard_executivo')
def filter_options():
    """Obter opções para filtros"""
    try:
        # Obter dados (auto-carrega se necessário)
        user_data = session.get('user', {})
        user_id = user_data.get('id')
        data = fetch_and_cache_dashboard_data(user_data)
        if not data:
            return jsonify({'success': False, 'error': 'Dados não encontrados após tentativa de carregamento.', 'options': {}})
        
        df = pd.DataFrame(data)
        
        # Extrair opções únicas para os filtros
        materiais = []
        clientes = []
        canais = []
        modais = []
        
        # Materiais únicos (filtrar vazios)
        if 'mercadoria' in df.columns:
            materiais = sorted([
                mat for mat in df['mercadoria'].dropna().unique() 
                if str(mat).strip() and str(mat).lower() not in ['nan', 'none', 'null', '', 'não informado']
            ])
        
        # Clientes únicos (filtrar vazios)
        if 'importador' in df.columns:
            clientes = sorted([
                cli for cli in df['importador'].dropna().unique()
                if str(cli).strip() and str(cli).lower() not in ['nan', 'none', 'null', '']
            ])
        
        # Canais únicos
        if 'canal' in df.columns:
            canais = sorted([
                canal for canal in df['canal'].dropna().unique()
                if str(canal).strip() and str(canal).lower() not in ['nan', 'none', 'null', '']
            ])
        
        # Modais únicos
        if 'modal' in df.columns:
            modais = sorted([
                modal for modal in df['modal'].dropna().unique()
                if str(modal).strip() and str(modal).lower() not in ['nan', 'none', 'null', '']
            ])
        
        options = {
            'materiais': materiais[:50],  # Limitar a 50 itens para performance
            'clientes': clientes[:50],
            'canais': canais,
            'modais': modais
        }
        
        print(f"[DASHBOARD_EXECUTIVO] Opções de filtro: {len(materiais)} materiais, {len(clientes)} clientes, {len(canais)} canais, {len(modais)} modais")
        
        return jsonify({
            'success': True,
            'options': clean_data_for_json(options)
        })
        
    except Exception as e:
        print(f"[DASHBOARD_EXECUTIVO] Erro ao obter opções de filtro: {str(e)}")
        return jsonify({'success': False, 'error': str(e), 'options': {}}), 200

@bp.route('/api/force-refresh', methods=['POST'])
@login_required
@perfil_required('importacoes', 'dashboard_executivo')
def force_refresh_dashboard():
    """
    Force refresh específico para o Dashboard Executivo
    Limpa o cache e busca dados atualizados do banco
    VERSÃO OTIMIZADA: Consulta batch de despesas
    """
    try:
        print("[DASHBOARD_EXECUTIVO] === INICIANDO FORCE REFRESH OTIMIZADO ===")
        
        # Obter dados do usuário
        user_data = session.get('user', {})
        user_id = user_data.get('id')
        user_role = user_data.get('role')
        
        # 1. Limpar cache do usuário
        print(f"[DASHBOARD_EXECUTIVO] Limpando cache para user_id: {user_id}")
        data_cache.clear_user_cache(user_id)
        
        # 2. Limpar cache da sessão também
        if 'dashboard_v2_loaded' in session:
            del session['dashboard_v2_loaded']
        
        # 3. Buscar dados frescos do banco
        print("[DASHBOARD_EXECUTIVO] Buscando dados frescos do banco...")
        
        # Query base da view com dados de despesas - SEMPRE buscar dados frescos (já filtrada)
        query = supabase_admin.table('vw_importacoes_6_meses_abertos_dash').select('*')
        
        # REGRA CORRIGIDA: Filtrar por CNPJs apenas para clientes e internos não-admin
        perfil_principal = user_data.get('perfil_principal', '')
        
        if user_role == 'cliente_unique' or (user_role == 'interno_unique' and perfil_principal not in ['admin_operacao', 'master_admin']):
            user_cnpjs = get_user_companies(user_data)
            if user_cnpjs:
                print(f"[DASHBOARD_EXECUTIVO] Filtrando por CNPJs das empresas vinculadas: {user_cnpjs}")
                query = query.in_('cnpj_importador', user_cnpjs)
            else:
                print(f"[DASHBOARD_EXECUTIVO] Usuário {user_role} (perfil: {perfil_principal}) sem CNPJs vinculados")
                return jsonify({
                    'success': False,
                    'error': 'Usuário sem empresas vinculadas'
                })
        else:
            print(f"[DASHBOARD_EXECUTIVO] Admin operacional ({perfil_principal}) - visualizando todos os dados")
        
        # Executar query
        result = query.execute()
        
        if not result.data:
            return jsonify({
                'success': False,
                'error': 'Nenhum dado encontrado',
                'total_records': 0
            }), 404
        
        print(f"[DASHBOARD_EXECUTIVO] Dados frescos carregados: {len(result.data)} registros")
        
        # 4. Enriquecer dados com custos da view vw_despesas_6_meses (VERSÃO OTIMIZADA)
        print("[DASHBOARD_EXECUTIVO] Force refresh - Enriquecendo dados com custos (versão otimizada)...")
        enriched_data = enrich_data_with_despesas_view(result.data)
        
        # 5. Armazenar dados frescos ENRIQUECIDOS no cache
        data_cache.set_cache(user_id, 'dashboard_v2_data', enriched_data)
        session['dashboard_v2_loaded'] = True
        
        print(f"[DASHBOARD_EXECUTIVO] Cache atualizado com dados frescos para user_id: {user_id}")
        
        # 6. Calcular estatísticas rápidas para retorno
        df = pd.DataFrame(enriched_data)
        
        # Calcular custo total usando custos da view (corrigidos) - CONVERTER PARA TIPOS JSON-SAFE
        total_custo_raw = df['custo_total_view'].sum() if 'custo_total_view' in df.columns else 0
        registros_com_custo_raw = (df['custo_total_view'] > 0).sum() if 'custo_total_view' in df.columns else 0
        
        # CORREÇÃO: Converter tipos numpy/pandas para tipos Python nativos
        total_custo = float(total_custo_raw) if not pd.isna(total_custo_raw) else 0.0
        registros_com_custo = int(registros_com_custo_raw) if not pd.isna(registros_com_custo_raw) else 0
        
        # Preparar resposta com dados limpos para JSON
        response_data = {
            'success': True,
            'message': 'Cache atualizado com dados frescos do banco (versão otimizada)',
            'total_records': len(enriched_data),
            'total_custo': total_custo,
            'registros_com_custo': registros_com_custo,
            'refresh_timestamp': datetime.now().isoformat(),
            'source': 'vw_despesas_6_meses (consulta batch otimizada)'
        }
        
        # CORREÇÃO: Usar clean_data_for_json para garantir compatibilidade JSON
        return jsonify(clean_data_for_json(response_data))
        
    except Exception as e:
        print(f"[DASHBOARD_EXECUTIVO] Erro no force refresh: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Erro ao atualizar cache'
        }), 500

@bp.route('/api/bootstrap')
@login_required
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def bootstrap_dashboard():
    """Endpoint único para carregar em lote: dados base + KPIs + charts + operações + filtros.
    Reduz latência e elimina problemas de race em ambientes cloud.
    Filtros (query params) são aplicados onde pertinente.
    """
    try:
        user_data = session.get('user', {})
        user_role = user_data.get('role')
        user_email = user_data.get('email')
        
        # SECURITY: Verificar se cliente_unique tem empresas associadas
        if user_role == 'cliente_unique':
            user_cnpjs = get_user_companies(user_data)
            if not user_cnpjs:
                print(f"[DASHBOARD_EXECUTIVO] Cliente {user_email} sem empresas vinculadas - bloqueando acesso aos dados")
                return jsonify({
                    'success': False, 
                    'error': 'no_companies',
                    'message': 'Usuário sem empresas vinculadas. Entre em contato com o administrador para associar empresas ao seu perfil.',
                    'show_warning': True
                }), 200
        
        base_data = fetch_and_cache_dashboard_data(user_data)
        if not base_data:
            return jsonify({'success': False, 'error': 'Sem dados base.'}), 200

        # Reaproveitar lógica existente via DataFrame uma única vez
        filtered = apply_filters(base_data)
        df = pd.DataFrame(filtered)
        # Pequenos safeguards
        for col in ['custo_total_view','custo_total','custo_total_original']:
            if col not in df.columns:
                df[col] = 0.0
        df['custo_calculado'] = df['custo_total_view']
        mask_view_zero = df['custo_calculado'] <= 0
        df.loc[mask_view_zero,'custo_calculado'] = df.loc[mask_view_zero,'custo_total']
        mask_total_zero = df['custo_calculado'] <= 0
        df.loc[mask_total_zero,'custo_calculado'] = df.loc[mask_total_zero,'custo_total_original']

        # Tipagem segura para custos (evita FutureWarning de atribuição em col int)
        for colc in ['custo_total_view','custo_total','custo_total_original']:
            if colc in df.columns:
                df[colc] = pd.to_numeric(df[colc], errors='coerce').fillna(0).astype(float)

        # Recalcular custo_calculado com fallback adicional despesas_processo
        if 'despesas_processo' in df.columns:
            for idx in df.index[df['custo_calculado'] <= 0]:
                try:
                    valor = calculate_custo_from_despesas_processo(df.at[idx,'despesas_processo'])
                    if valor > 0:
                        df.at[idx,'custo_calculado'] = float(valor)
                except Exception:
                    pass

        # --- KPI COMPLETO (replicando lógica detalhada do endpoint /api/kpis) ---
        total_processos = len(df)
        if 'status_macro_sistema' in df.columns:
            processos_fechados = len(df[df['status_macro_sistema'] == 'PROCESSO CONCLUIDO'])
            processos_abertos = len(df[(df['status_macro_sistema'] != 'PROCESSO CONCLUIDO') | (df['status_macro_sistema'].isna())])
        else:
            processos_fechados = 0
            processos_abertos = total_processos

        total_despesas = float(df['custo_calculado'].sum()) if not df.empty else 0.0
        ticket_medio = float(total_despesas/total_processos) if total_processos else 0.0

        # CORREÇÃO: Usar status_timeline como fonte única para KPIs - NOVA REGRA
        def get_timeline_number_monthly(status_timeline):
            """Extrair número do status_timeline (ex: '2 - Agd Chegada' -> 2)"""
            if not status_timeline:
                return 0
            try:
                # Tentar extrair número do início da string
                status_str = str(status_timeline).strip()
                if status_str.startswith(('1', '2', '3', '4', '5', '6')):
                    return int(status_str.split(' ')[0].replace('-', '').strip())
                return 0
            except:
                return 0

        # Função de normalização de status (para fallback se status_timeline não existir)
        def normalize_status(status):
            import unicodedata, re
            if pd.isna(status) or not status:
                return ""
            s = unicodedata.normalize('NFKD', str(status)).encode('ASCII','ignore').decode('ASCII')
            s = re.sub(r'[^A-Za-z0-9 ]','', s).upper().strip()
            return s

        # Aplicar nova lógica se a coluna existir
        if 'status_timeline' in df.columns:
            # Criar coluna numérica para facilitar comparações
            df['timeline_number'] = df['status_timeline'].apply(get_timeline_number_monthly)
            
            # Calcular métricas baseadas no status_timeline - NOVA REGRA
            # 1 - Agd Embarque, 2 - Agd Chegada, 3 - Agd Liberação, 4 - Agd Fechamento
            agd_embarque = (df['timeline_number'] == 1).sum()      # 1 - Agd Embarque
            agd_chegada = (df['timeline_number'] == 2).sum()       # 2 - Agd Chegada  
            agd_liberacao = (df['timeline_number'] == 3).sum()     # 3 - Agd Liberação
            agd_fechamento = (df['timeline_number'] == 4).sum()    # 4 - Agd Fechamento
        else:
            # Fallback para normalização de status (caso status_timeline não exista)
            if 'status_macro_sistema' in df.columns:
                df['status_normalizado'] = df['status_macro_sistema'].apply(normalize_status)
            else:
                df['status_normalizado'] = ''

            agd_embarque = (df['status_normalizado'] == 'AG EMBARQUE').sum()
            agd_chegada = (df['status_normalizado'] == 'AG CHEGADA').sum()
            agd_liberacao = df['status_normalizado'].isin(['DI REGISTRADA','AG REGISTRO','AG MAPA']).sum()
            agd_fechamento = (df['status_normalizado'] == 'AG FECHAMENTO').sum()

        # Corrigir datas de chegada truncadas (ex: 07/08/025 -> 07/08/2025)
        if 'data_chegada' in df.columns:
            def fix_date(d):
                if isinstance(d,str) and len(d)==10 and d[2]=='/' and d[5]=='/' and len(d.split('/')[-1])==3:
                    # Inserir '2' após último '/0' se ano com 3 chars
                    parts = d.split('/')
                    year = parts[2]
                    if year.startswith('0'):
                        return f"{parts[0]}/{parts[1]}/20{year[1:]}"  # assume século 2000
                return d
            df['data_chegada'] = df['data_chegada'].apply(fix_date)

        hoje = pd.Timestamp.now().normalize()
        primeiro_dia_mes = hoje.replace(day=1)
        ultimo_dia_mes = (primeiro_dia_mes + pd.DateOffset(months=1)) - pd.Timedelta(days=1)
        dias_desde_domingo = (hoje.dayofweek + 1) % 7
        inicio_semana = hoje - pd.Timedelta(days=dias_desde_domingo)
        fim_semana = inicio_semana + pd.Timedelta(days=6)
        chegando_mes = chegando_mes_custo = 0.0
        chegando_semana = chegando_semana_custo = 0.0
        if 'data_chegada' in df.columns:
            chegada_dt = pd.to_datetime(df['data_chegada'], format='%d/%m/%Y', errors='coerce')
            custos = df['custo_calculado']
            mask_mes = (chegada_dt >= primeiro_dia_mes) & (chegada_dt <= ultimo_dia_mes)
            mask_semana = (chegada_dt >= inicio_semana) & (chegada_dt <= fim_semana)
            chegando_mes = int(mask_mes.sum())
            chegando_semana = int(mask_semana.sum())
            chegando_mes_custo = float(custos[mask_mes].sum())
            chegando_semana_custo = float(custos[mask_semana].sum())

        kpis = {
            'total_processos': total_processos,
            'processos_abertos': processos_abertos,
            'processos_fechados': processos_fechados,
            'total_despesas': total_despesas,
            'ticket_medio': ticket_medio,
            'agd_embarque': int(agd_embarque),           # NOVO NOME
            'agd_chegada': int(agd_chegada),             # NOVO NOME
            'agd_liberacao': int(agd_liberacao),         # NOVO NOME
            'agd_fechamento': int(agd_fechamento),       # NOVO NOME
            'chegando_mes': int(chegando_mes),
            'chegando_mes_custo': float(chegando_mes_custo),
            'chegando_semana': int(chegando_semana),
            'chegando_semana_custo': float(chegando_semana_custo)
        }

        # Charts completos (mensal, status, modal, urf, material, principais_materiais)
        charts = {}
        if 'data_abertura' in df.columns:
            df['data_abertura_dt'] = pd.to_datetime(df['data_abertura'], format='%d/%m/%Y', errors='coerce')
            dfm = df.dropna(subset=['data_abertura_dt']).copy()
            dfm['mes_ano'] = dfm['data_abertura_dt'].dt.strftime('%m/%Y')
            g = dfm.groupby('mes_ano').agg({'ref_unique':'count','custo_calculado':'sum'}).reset_index().sort_values('mes_ano')
            charts['monthly'] = {
                'labels': g['mes_ano'].tolist(),
                'datasets': [
                    {'label':'Quantidade de Processos','data':g['ref_unique'].tolist(),'type':'line','borderColor':'#007bff','backgroundColor':'rgba(0,123,255,0.1)','yAxisID':'y1','tension':0.4},
                    {'label':'Custo Total (R$)','data':g['custo_calculado'].tolist(),'type':'line','borderColor':'#28a745','backgroundColor':'rgba(40,167,69,0.1)','yAxisID':'y','tension':0.4}
                ]
            }
        # Alinhar com a coluna usada na tabela: status_macro_sistema (fallback para status_processo)
        try:
            if 'status_macro_sistema' in df.columns:
                print('[DEBUG_BOOTSTRAP] Usando coluna para Status Chart: status_macro_sistema')
                status_counts = df['status_macro_sistema'].fillna('Sem Info').value_counts().head(10)
                charts['status'] = {'labels': status_counts.index.tolist(),'data': status_counts.values.tolist()}
            elif 'status_processo' in df.columns:
                print('[DEBUG_BOOTSTRAP] Usando coluna para Status Chart: status_processo (fallback)')
                status_counts = df['status_processo'].fillna('Sem Info').value_counts().head(10)
                charts['status'] = {'labels': status_counts.index.tolist(),'data': status_counts.values.tolist()}
            else:
                print('[DEBUG_BOOTSTRAP] Nenhuma coluna de status encontrada para o Status Chart')
        except Exception as e:
            print(f"[DEBUG_BOOTSTRAP] Erro ao montar Status Chart: {e}")
        if 'modal' in df.columns:
            gm = df.groupby('modal').agg({'ref_unique':'count','custo_calculado':'sum'}).reset_index()
            charts['grouped_modal'] = {
                'labels': gm['modal'].tolist(),
                'datasets': [
                    {'label':'Quantidade de Processos','data':gm['ref_unique'].tolist(),'type':'bar','backgroundColor':'rgba(54,162,235,0.6)','borderColor':'rgba(54,162,235,1)','yAxisID':'y1'},
                    {'label':'Custo Total (R$)','data':gm['custo_calculado'].tolist(),'type':'line','backgroundColor':'rgba(255,99,132,0.2)','borderColor':'rgba(255,99,132,1)','yAxisID':'y'}
                ]
            }
        if 'urf_despacho_normalizado' in df.columns:
            urf_counts = df['urf_despacho_normalizado'].value_counts().head(10)
            charts['urf'] = {'labels': urf_counts.index.tolist(),'data': urf_counts.values.tolist()}
        elif 'urf_despacho' in df.columns:
            urf_counts = df['urf_despacho'].value_counts().head(10)
            charts['urf'] = {'labels': urf_counts.index.tolist(),'data': urf_counts.values.tolist()}
        if 'mercadoria' in df.columns:
            material_counts = df['mercadoria'].value_counts().head(10)
            charts['material'] = {'labels': material_counts.index.tolist(),'data': material_counts.values.tolist()}
        if 'mercadoria' in df.columns and 'data_chegada' in df.columns:
            try:
                material_groups = df.groupby('mercadoria').agg({'ref_unique':'count','custo_calculado':'sum','data_chegada':'first','transit_time_real':'mean'}).reset_index()
                material_groups['data_chegada_dt'] = pd.to_datetime(material_groups['data_chegada'], format='%d/%m/%Y', errors='coerce')
                hoje = pd.Timestamp.now()
                material_groups['is_future'] = material_groups['data_chegada_dt'] >= hoje
                material_groups = material_groups.sort_values(['is_future','data_chegada_dt'], ascending=[False,True])
                table_data = []
                for _, row in material_groups.head(15).iterrows():
                    is_urgente = False
                    dias_para_chegada = 0
                    if pd.notnull(row['data_chegada_dt']):
                        diff_days = (row['data_chegada_dt'] - hoje).days
                        is_urgente = 0 < diff_days <= 5
                        dias_para_chegada = diff_days if diff_days > 0 else 0
                    table_data.append({
                        'material': row['mercadoria'],
                        'total_processos': int(row['ref_unique']),
                        'custo_total': float(row['custo_calculado']) if pd.notnull(row['custo_calculado']) else 0,
                        'data_chegada': row['data_chegada'],
                        'transit_time': float(row['transit_time_real']) if pd.notnull(row['transit_time_real']) else 0,
                        'is_urgente': is_urgente,
                        'dias_para_chegada': dias_para_chegada
                    })
                charts['principais_materiais'] = {'data': table_data}
            except Exception as e:
                print(f"[DASHBOARD_EXECUTIVO] Erro ao processar principais materiais (bootstrap): {str(e)}")

        # Operações recentes (limit 25 para bootstrap rápido)
        operations = []
        if not df.empty:
            if 'data_abertura' in df.columns:
                df['data_abertura_dt'] = pd.to_datetime(df['data_abertura'], format='%d/%m/%Y', errors='coerce')
                dfo = df.sort_values('data_abertura_dt', ascending=False).head(100)
            else:
                dfo = df.head(100)
            core_cols = [c for c in ['ref_unique','importador','data_abertura','modal','status_processo','status_macro_sistema','custo_total_view','custo_total','data_chegada','mercadoria'] if c in dfo.columns]
            dfo = dfo.copy()
            operations = dfo[core_cols].to_dict('records')
            for op in operations:
                cv = op.get('custo_total_view')
                ct = op.get('custo_total')
                if cv and cv > 0:
                    op['custo_total'] = cv
                elif ct and ct > 0:
                    op['custo_total'] = ct

        # Opções de filtro rápidas
        filter_options_payload = {}
        if 'mercadoria' in df.columns:
            filter_options_payload['materiais'] = sorted(list({m for m in df['mercadoria'].dropna().head(50)}))
        if 'importador' in df.columns:
            filter_options_payload['clientes'] = sorted(list({m for m in df['importador'].dropna().head(50)}))
        if 'canal' in df.columns:
            filter_options_payload['canais'] = sorted(list({m for m in df['canal'].dropna()}))
        if 'modal' in df.columns:
            filter_options_payload['modais'] = sorted(list({m for m in df['modal'].dropna()}))

        # Preparar payload final. Frontend espera campos top-level (data, kpis, charts, operations, filter_options)
        # Mantemos também a chave 'bootstrap' para eventual compatibilidade retroativa.
        applied_filters = {k: v for k, v in request.args.items()}
        payload = {
            'success': True,
            'data': filtered,                 # dados já filtrados (para tabela/gráficos imediatos)
            'total_records': len(base_data),  # total bruto antes de filtro
            'total_filtered': len(filtered),
            'kpis': kpis,
            'charts': charts,
            'operations': operations,
            'filter_options': filter_options_payload,
            'applied_filters': applied_filters,
            'bootstrap': {  # wrapper opcional legado
                'kpis': kpis,
                'charts': charts,
                'operations': operations,
                'filter_options': filter_options_payload,
                'total_records': len(base_data),
                'total_filtered': len(filtered),
                'applied_filters': applied_filters
            }
        }

        return jsonify(clean_data_for_json(payload))
    except Exception as e:
        print(f"[DASHBOARD_EXECUTIVO] Erro no bootstrap: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/test-materials-permission')
@login_required
@role_required(['admin', 'interno_unique', 'cliente_unique']) 
def test_materials_permission():
    """Endpoint de teste para verificar permissão de materiais"""
    try:
        user_data = session.get('user', {})
        can_view = user_can_view_materials(user_data)
        user_companies = get_user_companies(user_data)
        
        return jsonify({
            'success': True,
            'user_data': user_data,
            'can_view_materials': can_view,
            'user_companies': user_companies,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"[DASHBOARD_EXECUTIVO] Erro no teste de permissão: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/paises-procedencia')
@login_required
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def get_paises_procedencia():
    """API para obter dados de países de procedência com bandeiras"""
    try:
        user_data = session.get('user', {})
        user_id = user_data.get('id')
        
        if not user_id:
            return jsonify({'success': False, 'error': 'Usuário não autenticado'}), 401
        
        print(f"[DASHBOARD_EXECUTIVO] Carregando dados de países de procedência para user {user_id}")
        
        # Obter dados do cache
        cached_data = fetch_and_cache_dashboard_data(user_data)
        
        if not cached_data:
            return jsonify({
                'success': True,
                'data': [],
                'message': 'Nenhum dado encontrado'
            })
        
        # CORREÇÃO: Aplicar filtros aos dados antes de processar
        filtered_data = apply_filters(cached_data)
        
        # Converter para DataFrame
        df = pd.DataFrame(filtered_data)
        
        # Filtrar apenas registros com país de procedência válido
        df_paises = df[df['pais_procedencia'].notna() & (df['pais_procedencia'] != '')]
        
        if df_paises.empty:
            return jsonify({
                'success': True,
                'data': [],
                'message': 'Nenhum país de procedência encontrado'
            })
        
        # Agrupar por país de procedência
        paises_stats = df_paises.groupby('pais_procedencia').agg({
            'id': 'count',  # Total de processos
            'custo_total': lambda x: x.sum() if x.notna().any() else 0.0,  # Total de custos
            'url_bandeira': 'first'  # Pegar a primeira URL da bandeira (todas devem ser iguais para o mesmo país)
        }).reset_index()
        
        # Renomear colunas
        paises_stats.columns = ['pais_procedencia', 'total_processos', 'total_custo', 'url_bandeira']
        
        # Ordenar por total de processos (decrescente)
        paises_stats = paises_stats.sort_values('total_processos', ascending=False)
        
        # LIMITAÇÃO PARA TOP 7 PAÍSES + OUTROS (para evitar quebra de layout)
        if len(paises_stats) > 7:
            print(f"[DASHBOARD_EXECUTIVO] Limitando exibição: {len(paises_stats)} -> 7 países + outros")
            
            # Top 7 países
            top_7 = paises_stats.head(7)
            
            # Calcular "Outros" para países restantes
            outros_stats = paises_stats.tail(len(paises_stats) - 7)
            outros_processos = outros_stats['total_processos'].sum()
            outros_custo = outros_stats['total_custo'].sum()
            
            # Converter top 7 para lista
            paises_data = []
            for _, row in top_7.iterrows():
                paises_data.append({
                    'pais_procedencia': str(row['pais_procedencia']),
                    'total_processos': int(row['total_processos']),
                    'total_custo': float(row['total_custo']) if not pd.isna(row['total_custo']) else 0.0,
                    'url_bandeira': str(row['url_bandeira']) if pd.notna(row['url_bandeira']) else None
                })
            
            # Adicionar linha "Outros" se houver países excluídos
            if len(outros_stats) > 0:
                paises_data.append({
                    'pais_procedencia': f'Outros ({len(outros_stats)} países)',
                    'total_processos': int(outros_processos),
                    'total_custo': float(outros_custo),
                    'url_bandeira': None  # Sem bandeira para "Outros"
                })
                
            print(f"[DASHBOARD_EXECUTIVO] Retornando 7 + 1 'Outros' = {len(paises_data)} itens")
            
        else:
            # Manter lógica original se já tiver 7 ou menos países
            paises_data = []
            for _, row in paises_stats.iterrows():
                paises_data.append({
                    'pais_procedencia': str(row['pais_procedencia']),
                    'total_processos': int(row['total_processos']),
                    'total_custo': float(row['total_custo']) if not pd.isna(row['total_custo']) else 0.0,
                    'url_bandeira': str(row['url_bandeira']) if pd.notna(row['url_bandeira']) else None
                })
        
        print(f"[DASHBOARD_EXECUTIVO] Retornando dados de {len(paises_data)} países")
        
        return jsonify({
            'success': True,
            'data': clean_data_for_json(paises_data)
        })
        
    except Exception as e:
        print(f"[DASHBOARD_EXECUTIVO] Erro ao obter dados de países: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
