from flask import Blueprint, render_template, session, jsonify, request
from extensions import supabase, supabase_admin
from routes.auth import login_required, role_required
from routes.api import get_user_companies
from permissions import check_permission
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import unicodedata
import re
import json
from services.data_cache import DataCacheService

# Instanciar o serviço de cache
data_cache = DataCacheService()

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
                
                print(f"[DESPESAS_VIEW] Encontrados custos para {len(despesas_map)} processos")
                
            except Exception as e:
                print(f"[DESPESAS_VIEW] Erro na consulta batch: {str(e)}")
                despesas_map = {}
        
        # Enriquecer dados originais
        enriched_data = []
        total_encontrados = 0
        
        for item in data:
            enriched_item = item.copy()
            ref_unique = item.get('ref_unique')
            
            # Custo original do campo despesas_processo
            custo_original = calculate_custo_from_despesas_processo(item.get('despesas_processo'))
            enriched_item['custo_total_original'] = custo_original
            
            # Custo da view vw_despesas_6_meses (batch)
            custo_view = despesas_map.get(ref_unique, 0)
            enriched_item['custo_total_view'] = custo_view
            
            # Usar o custo da view como oficial
            enriched_item['custo_total'] = custo_view
            
            if custo_view > 0:
                total_encontrados += 1
            
            # Log para processo 6555 especificamente
            if ref_unique and '6555' in str(ref_unique):
                print(f"[DESPESAS_VIEW] Processo 6555 -> View: R$ {custo_view:,.2f}, Original: R$ {custo_original:,.2f}")
            
            enriched_data.append(enriched_item)
        
        print(f"[DESPESAS_VIEW] Enriquecimento concluído: {total_encontrados}/{len(data)} processos com custos encontrados na view")
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
        
        filtered_data = data
        
        # Filtrar por data
        if data_inicio and data_fim:
            filtered_data = [item for item in filtered_data 
                           if filter_by_date_python(item.get('data_abertura'), data_inicio, data_fim)]
        
        # Filtrar por material (múltiplas seleções)
        if material:
            materiais_lista = [m.strip() for m in material.split(',') if m.strip()]
            if materiais_lista:
                filtered_data = [item for item in filtered_data 
                               if any(mat.lower() in item.get('mercadoria', '').lower() 
                                     for mat in materiais_lista)]
        
        # Filtrar por cliente (múltiplas seleções)
        if cliente:
            clientes_lista = [c.strip() for c in cliente.split(',') if c.strip()]
            if clientes_lista:
                filtered_data = [item for item in filtered_data 
                               if any(cli.lower() in item.get('importador', '').lower() 
                                     for cli in clientes_lista)]
        
        # Filtrar por modal (múltiplas seleções)
        if modal:
            modais_lista = [m.strip() for m in modal.split(',') if m.strip()]
            if modais_lista:
                filtered_data = [item for item in filtered_data 
                               if any(mod.lower() in item.get('modal', '').lower() 
                                     for mod in modais_lista)]
        
        # Filtrar por canal (múltiplas seleções)
        if canal:
            canais_lista = [c.strip() for c in canal.split(',') if c.strip()]
            if canais_lista:
                filtered_data = [item for item in filtered_data 
                               if any(can.lower() in item.get('canal', '').lower() 
                                     for can in canais_lista)]
        
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
        
        return filtered_data
        
    except Exception as e:
        print(f"[DASHBOARD_EXECUTIVO] Erro ao aplicar filtros: {str(e)}")
        return data

@bp.route('/')
@login_required
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def index():
    """Página principal do Dashboard Executivo"""
    return render_template('dashboard_executivo.html')

@bp.route('/api/load-data')
@login_required
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def load_data():
    """Carregar dados da tabela importacoes_processos_aberta"""
    try:
        print("[DASHBOARD_EXECUTIVO] Iniciando carregamento de dados da tabela...")
        
        # Obter dados do usuário
        user_data = session.get('user', {})
        user_role = user_data.get('role')
        user_id = user_data.get('id')
        
        # Verificar se já existe cache
        cached_data = data_cache.get_cache(user_id, 'dashboard_v2_data')
        
        if cached_data:
            print(f"[DASHBOARD_EXECUTIVO] Cache encontrado: {len(cached_data)} registros")
            session['dashboard_v2_loaded'] = True
            return jsonify({
                'success': True,
                'data': cached_data,
                'total_records': len(cached_data)
            })
        
        # Query base da view com dados de despesas
        query = supabase_admin.table('vw_importacoes_6_meses').select('*')
        
        # Filtrar por empresa se for cliente
        if user_role == 'cliente_unique':
            user_companies = get_user_companies(user_data)
            if user_companies:
                query = query.in_('cnpj_importador', user_companies)
        
        # Executar query
        result = query.execute()
        
        if not result.data:
            print("[DASHBOARD_EXECUTIVO] Nenhum dado encontrado")
            return jsonify({
                'success': False,
                'error': 'Nenhum dado encontrado',
                'data': []
            })
        
        print(f"[DASHBOARD_EXECUTIVO] Dados carregados: {len(result.data)} registros")
        
        # NOVA IMPLEMENTAÇÃO: Enriquecer dados com custos da view vw_despesas_6_meses
        print("[DASHBOARD_EXECUTIVO] Enriquecendo dados com custos da vw_despesas_6_meses...")
        enriched_data = enrich_data_with_despesas_view(result.data)
        
        # Log para verificar estrutura do campo despesas_processo
        records_with_expenses = 0
        for record in enriched_data:
            if 'despesas_processo' in record and record['despesas_processo']:
                records_with_expenses += 1
                if records_with_expenses == 1:  # Log apenas do primeiro registro
                    print(f"[DASHBOARD_EXECUTIVO] Exemplo despesas_processo: {record['despesas_processo'][:2] if len(record['despesas_processo']) > 2 else record['despesas_processo']}")
        
        print(f"[DASHBOARD_EXECUTIVO] Registros com despesas_processo: {records_with_expenses}/{len(enriched_data)}")
        
        # Armazenar dados ENRIQUECIDOS no cache do servidor
        data_cache.set_cache(user_id, 'dashboard_v2_data', enriched_data)
        print(f"[DASHBOARD_EXECUTIVO] Cache armazenado para user_id: {user_id} com {len(enriched_data)} registros (dados enriquecidos)")
        
        session['dashboard_v2_loaded'] = True
        
        return jsonify({
            'success': True,
            'data': enriched_data,
            'total_records': len(result.data)
        })
        
    except Exception as e:
        print(f"[DASHBOARD_EXECUTIVO] Erro ao carregar dados: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': []
        }), 500

@bp.route('/api/kpis')
@login_required
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def dashboard_kpis():
    """Calcular KPIs para o dashboard executivo"""
    try:
        # Obter dados do cache
        user_data = session.get('user', {})
        user_id = user_data.get('id')
        
        data = data_cache.get_cache(user_id, 'dashboard_v2_data')
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Dados não encontrados. Recarregue a página.',
                'kpis': {}
            })
        
        # Aplicar filtros se existirem
        filtered_data = apply_filters(data)
        df = pd.DataFrame(filtered_data)
        
        # USAR CUSTO DA VIEW ENRIQUECIDA (custo_total_view calculado pelo enriquecimento)
        print("[DEBUG_KPI] Usando custos da view vw_despesas_6_meses via enriquecimento...")
        
        # Usar o custo_total_view que foi calculado durante o enriquecimento dos dados
        if 'custo_total_view' not in df.columns:
            print("[DEBUG_KPI] ERRO: Campo custo_total_view não encontrado! Usando fallback.")
            df['custo_total_view'] = 0.0
        
        df['custo_calculado'] = df['custo_total_view']
        
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
            if status in ['AG EMBARQUE', 'AG EMBARQUE']: return 'AG EMBARQUE'
            if status in ['AG CHEGADA', 'AG CHEGADA']: return 'AG CHEGADA'
            if status in ['AG CARREGAMENTO', 'AG CARREGAMENTO']: return 'AG CARREGAMENTO'
            if status in ['AG FECHAMENTO', 'AG FECHAMENTO']: return 'AG FECHAMENTO'
            if status in ['AG REGISTRO', 'AG REGISTRO']: return 'AG REGISTRO'
            if status in ['AG MAPA', 'AG MAPA']: return 'AG MAPA'
            if status in ['DI REGISTRADA', 'DI REGISTRADA']: return 'DI REGISTRADA'
            if status in ['DI DESEMBARACADA', 'DI DESEMBARACADA']: return 'DI DESEMBARACADA'
            if status in ['NUMERARIO ENVIADO', 'NUMERARIO ENVIADO']: return 'NUMERARIO ENVIADO'
            return status

        # Aplicar normalização se a coluna existir
        if 'status_macro_sistema' in df.columns:
            df['status_normalizado'] = df['status_macro_sistema'].apply(normalize_status)
            
            # Calcular métricas baseadas nos status normalizados
            aguardando_embarque = len(df[df['status_normalizado'] == 'AG EMBARQUE'])
            aguardando_chegada = len(df[df['status_normalizado'] == 'AG CHEGADA'])
            aguardando_liberacao = len(df[df['status_normalizado'].isin(['DI REGISTRADA', 'AG REGISTRO', 'AG MAPA'])])
            agd_entrega = len(df[df['status_normalizado'].isin([
                'AG. CARREGAMENTO', 'AG CARREGAMENTO', 'CARREGAMENTO AGENDADO'
            ])])
            aguardando_fechamento = len(df[df['status_normalizado'] == 'AG FECHAMENTO'])
            
            print(f"[DEBUG_KPI] Status counts:")
            print(f"[DEBUG_KPI] Aguardando Embarque: {aguardando_embarque}")
            print(f"[DEBUG_KPI] Aguardando Chegada: {aguardando_chegada}")
            print(f"[DEBUG_KPI] Aguardando Liberação: {aguardando_liberacao}")
            print(f"[DEBUG_KPI] Agd Entrega: {agd_entrega}")
            print(f"[DEBUG_KPI] Aguardando Fechamento: {aguardando_fechamento}")
        else:
            aguardando_embarque = 0
            aguardando_chegada = 0
            aguardando_liberacao = 0
            agd_entrega = 0
            aguardando_fechamento = 0

        # Chegando Este Mês/Semana: considerar TODAS as datas de chegada dentro do mês/semana (igual dashboard materiais)
        hoje = pd.Timestamp.now().normalize()
        primeiro_dia_mes = hoje.replace(day=1)
        ultimo_dia_mes = (primeiro_dia_mes + pd.DateOffset(months=1)) - pd.Timedelta(days=1)
        # Calcular semana atual (domingo a sábado)
        dias_desde_domingo = (hoje.dayofweek + 1) % 7  # 0=domingo, 1=segunda, etc.
        inicio_semana = hoje - pd.Timedelta(days=dias_desde_domingo)
        fim_semana = inicio_semana + pd.Timedelta(days=6)
        chegando_mes = 0
        chegando_mes_custo = 0.0
        chegando_semana = 0
        chegando_semana_custo = 0.0
        if 'data_chegada' in df.columns:
            df['chegada_dt'] = pd.to_datetime(df['data_chegada'], format='%d/%m/%Y', errors='coerce')
            print(f"[DEBUG_KPI] Total registros: {len(df)}")
            print(f"[DEBUG_KPI] Registros com data_chegada válida: {df['chegada_dt'].notnull().sum()}")
            print(f"[DEBUG_KPI] Hoje: {hoje.strftime('%d/%m/%Y')}")
            print(f"[DEBUG_KPI] Semana: {inicio_semana.strftime('%d/%m/%Y')} a {fim_semana.strftime('%d/%m/%Y')}")
            print(f"[DEBUG_KPI] Mês: {primeiro_dia_mes.strftime('%d/%m/%Y')} a {ultimo_dia_mes.strftime('%d/%m/%Y')}")
            for idx, row in df.iterrows():
                chegada = row.get('chegada_dt')
                custo = row.get('custo_calculado', 0.0)  # USANDO CUSTO CALCULADO
                if custo is None:
                    custo = 0.0
                data_str = row.get('data_chegada', 'SEM DATA')
                if pd.notnull(chegada) and idx < 5:
                    print(f"[DEBUG_KPI] {data_str} -> {chegada.strftime('%d/%m/%Y')} | Custo: {custo} | Semana: {inicio_semana <= chegada <= fim_semana} | Mês: {primeiro_dia_mes <= chegada <= ultimo_dia_mes}")
                # Lógica para MÊS (independente de ser passado ou futuro)
                if pd.notnull(chegada) and primeiro_dia_mes <= chegada <= ultimo_dia_mes:
                    chegando_mes += 1
                    chegando_mes_custo += custo
                # Lógica para SEMANA (independente de ser passado ou futuro)
                if pd.notnull(chegada) and inicio_semana <= chegada <= fim_semana:
                    chegando_semana += 1
                    chegando_semana_custo += custo
            print(f"[DEBUG_KPI] Resultados - Chegando semana: {chegando_semana}, Custo: {chegando_semana_custo:,.2f}")
            print(f"[DEBUG_KPI] Resultados - Chegando mês: {chegando_mes}, Custo: {chegando_mes_custo:,.2f}")

        # Calcular processos abertos e fechados baseado no status_macro_sistema
        # REGRA CORRETA: 
        # - Fechados: status_macro_sistema = "PROCESSO CONCLUIDO"
        # - Abertos: status_macro_sistema ≠ "PROCESSO CONCLUIDO" (incluindo nulls)
        processos_abertos = 0
        processos_fechados = 0
        
        if 'status_macro_sistema' in df.columns:
            # Processos fechados: status_macro_sistema = "PROCESSO CONCLUIDO"
            processos_fechados = len(df[
                df['status_macro_sistema'] == 'PROCESSO CONCLUIDO'
            ])
            
            # Processos abertos: status_macro_sistema ≠ "PROCESSO CONCLUIDO" (incluindo nulls)
            processos_abertos = len(df[
                (df['status_macro_sistema'] != 'PROCESSO CONCLUIDO') | 
                (df['status_macro_sistema'].isna())
            ])
        else:
            # Se não tiver coluna status_macro_sistema, considerar todos como abertos
            processos_abertos = total_processos
            processos_fechados = 0

        print(f"[DEBUG_KPI] REGRA CORRIGIDA - Processos Fechados (status_macro_sistema = 'PROCESSO CONCLUIDO'): {processos_fechados}")
        print(f"[DEBUG_KPI] REGRA CORRIGIDA - Processos Abertos (status_macro_sistema ≠ 'PROCESSO CONCLUIDO'): {processos_abertos}")
        print(f"[DEBUG_KPI] Total: {processos_abertos + processos_fechados} (deve ser igual a {total_processos})")

        kpis = {
            'total_processos': total_processos,
            'processos_abertos': processos_abertos,
            'processos_fechados': processos_fechados,
            'total_despesas': float(total_despesas),
            'ticket_medio': float(ticket_medio),
            'aguardando_embarque': aguardando_embarque,
            'aguardando_chegada': aguardando_chegada,
            'aguardando_liberacao': aguardando_liberacao,
            'agd_entrega': agd_entrega,
            'aguardando_fechamento': aguardando_fechamento,
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
        return jsonify({
            'success': False,
            'error': str(e),
            'kpis': {}
        }), 500

@bp.route('/api/charts')
@login_required
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def dashboard_charts():
    """Gerar dados para os gráficos do dashboard executivo"""
    try:
        # Obter dados do cache
        user_data = session.get('user', {})
        user_id = user_data.get('id')
        
        data = data_cache.get_cache(user_id, 'dashboard_v2_data')
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Dados não encontrados. Recarregue a página.',
                'charts': {}
            })
        
        # Aplicar filtros se existirem
        filtered_data = apply_filters(data)
        df = pd.DataFrame(filtered_data)
        
        # USAR CUSTO DA VIEW ENRIQUECIDA (custo_total_view calculado pelo enriquecimento)
        print("[DEBUG_CHARTS] Usando custos da view vw_despesas_6_meses via enriquecimento...")
        
        # Usar o custo_total_view que foi calculado durante o enriquecimento dos dados
        if 'custo_total_view' not in df.columns:
            print("[DEBUG_CHARTS] ERRO: Campo custo_total_view não encontrado! Usando fallback.")
            df['custo_total_view'] = 0.0
        
        df['custo_calculado'] = df['custo_total_view']
        print(f"[DEBUG_CHARTS] Total custo da view nos gráficos: {df['custo_calculado'].sum():,.2f}")
        
        # Log específico para o processo 6555 nos gráficos também
        for idx, row in df.iterrows():
            ref_unique = row.get('ref_unique', 'N/A')
            if '6555' in str(ref_unique):
                custo_view = row.get('custo_total_view', 0)  # CORRIGIDO: usar custo_total_view
                print(f"[DEBUG_CHARTS] *** PROCESSO 6555 nos gráficos: custo_total_view={custo_view:,.2f} ***")
                break
        
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

        # Gráfico de Status do Processo
        status_chart = {'labels': [], 'data': []}
        if 'status_processo' in df.columns:
            status_counts = df['status_processo'].value_counts().head(10)
            status_chart = {
                'labels': status_counts.index.tolist(),
                'data': status_counts.values.tolist()
            }

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

        # Gráfico Materiais
        material_chart = {'labels': [], 'data': []}
        if 'mercadoria' in df.columns:
            material_counts = df['mercadoria'].value_counts().head(10)
            material_chart = {
                'labels': material_counts.index.tolist(),
                'data': material_counts.values.tolist()
            }

        # NOVO: Tabela de Principais Materiais (migrada do dashboard materiais)
        principais_materiais = {'data': []}
        if 'mercadoria' in df.columns and 'data_chegada' in df.columns:
            try:
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
                
            except Exception as e:
                print(f"[DASHBOARD_EXECUTIVO] Erro ao processar tabela de materiais: {str(e)}")
                principais_materiais = {'data': []}

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
            'charts': clean_data_for_json(charts)
        })
        
    except Exception as e:
        print(f"[DASHBOARD_EXECUTIVO] Erro ao gerar gráficos: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'charts': {}
        }), 500

@bp.route('/api/monthly-chart')
@login_required
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def monthly_chart():
    """Retorna dados do gráfico de evolução por granularidade (mensal, semanal, diário)"""
    try:
        granularidade = request.args.get('granularidade', 'mensal')
        user_data = session.get('user', {})
        user_id = user_data.get('id')
        data = data_cache.get_cache(user_id, 'dashboard_v2_data')
        
        if not data:
            return jsonify({'success': False, 'error': 'Dados não encontrados.', 'data': {}})
        
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
        
        df['custo_calculado'] = df['custo_total_view']
        print(f"[MONTHLY_CHART] Total custo da view no gráfico mensal: {df['custo_calculado'].sum():,.2f}")
        
        # Log específico para o processo 6555 no gráfico mensal também
        for idx, row in df.iterrows():
            ref_unique = row.get('ref_unique', 'N/A')
            if '6555' in str(ref_unique):
                custo_view = row.get('custo_total_view', 0)  # CORRIGIDO: usar custo_total_view
                print(f"[MONTHLY_CHART] *** PROCESSO 6555 no gráfico mensal: custo_total_view={custo_view:,.2f} ***")
                break
        
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
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def recent_operations():
    """Obter operações recentes para a tabela"""
    try:
        # Obter dados do cache
        user_data = session.get('user', {})
        user_id = user_data.get('id')
        
        data = data_cache.get_cache(user_id, 'dashboard_v2_data')
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Dados não encontrados. Recarregue a página.',
                'operations': []
            })
        
        # Aplicar filtros se existirem
        filtered_data = apply_filters(data)
        df = pd.DataFrame(filtered_data)
        
        # Garantir que há dados filtrados
        if df.empty:
            return jsonify({
                'success': True,
                'operations': []
            })
        
        # Ordenar por data mais recente e limitar a 50 registros
        if 'data_abertura' in df.columns:
            df['data_abertura_dt'] = pd.to_datetime(df['data_abertura'], format='%d/%m/%Y', errors='coerce')
            df_sorted = df.sort_values('data_abertura_dt', ascending=False).head(50)
        else:
            df_sorted = df.head(50)
        
        # Selecionar colunas relevantes para a tabela E modal
        relevant_columns = [
            # Colunas para a tabela
            'ref_unique', 'importador', 'data_abertura', 'exportador_fornecedor', 
            'modal', 'status_processo', 'status_macro_sistema', 'custo_total', 'data_chegada',
            
            # Colunas adicionais para o modal
            'ref_importador', 'cnpj_importador', 'status_macro', 'data_embarque', 'data_fechamento',
            'peso_bruto', 'urf_despacho', 'urf_despacho_normalizado', 'container',
            'transit_time_real', 'valor_cif_real', 'custo_frete_inter', 
            'custo_armazenagem', 'custo_honorarios', 'numero_di', 'data_registro',
            'canal', 'data_desembaraco', 'despesas_processo'  # NOVO CAMPO ADICIONADO
        ]
        
        # Colunas normalizadas disponíveis
        if 'mercadoria' in df_sorted.columns:
            relevant_columns.append('mercadoria')
        
        available_columns = [col for col in relevant_columns if col in df_sorted.columns]
        print(f"[DASHBOARD_EXECUTIVO] Colunas disponíveis: {available_columns}")
        print(f"[DASHBOARD_EXECUTIVO] Colunas faltando: {set(relevant_columns) - set(available_columns)}")
        
        operations_data = df_sorted[available_columns].to_dict('records')

        # Corrigir o campo custo_total para priorizar custo_total_view/custo_total (igual ao modal)
        for op in operations_data:
            custo_total_view = op.get('custo_total_view')
            custo_total = op.get('custo_total')
            if custo_total_view is not None and custo_total_view > 0:
                op['custo_total'] = custo_total_view
            elif custo_total is not None and custo_total > 0:
                op['custo_total'] = custo_total
            # Se não houver valor, mantém o original

        # Log específico para o processo 6555 nos dados enviados para o frontend
        for op in operations_data:
            ref_unique = str(op.get('ref_unique', ''))
            if '6555' in ref_unique:
                print(f"[RECENT_OPERATIONS] *** PROCESSO 6555 DADOS PARA FRONTEND (TABELA) ***")
                print(f"[RECENT_OPERATIONS] ref_unique: {op.get('ref_unique', 'N/A')}")
                print(f"[RECENT_OPERATIONS] custo_total (enviado): {op.get('custo_total', 'N/A')}")
                print(f"[RECENT_OPERATIONS] custo_total_view: {op.get('custo_total_view', 'N/A')}")
                print(f"[RECENT_OPERATIONS] custo_total_original: {op.get('custo_total_original', 'N/A')}")
                break

        return jsonify({
            'success': True,
            'operations': clean_data_for_json(operations_data)
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
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def filter_options():
    """Obter opções para filtros"""
    try:
        # Obter dados do cache
        user_data = session.get('user', {})
        user_id = user_data.get('id')
        
        data = data_cache.get_cache(user_id, 'dashboard_v2_data')
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Dados não encontrados. Recarregue a página.',
                'options': {}
            })
        
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
        return jsonify({
            'success': False,
            'error': str(e),
            'options': {}
        }), 500

@bp.route('/api/force-refresh', methods=['POST'])
@login_required
@role_required(['admin', 'interno_unique', 'cliente_unique'])
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
        
        # Query base da view com dados de despesas - SEMPRE buscar dados frescos
        query = supabase_admin.table('vw_importacoes_6_meses').select('*')
        
        # Filtrar por empresa se for cliente
        if user_role == 'cliente_unique':
            user_companies = get_user_companies(user_data)
            if user_companies:
                print(f"[DASHBOARD_EXECUTIVO] Filtrando por empresas: {user_companies}")
                query = query.in_('cnpj_importador', user_companies)
        
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
