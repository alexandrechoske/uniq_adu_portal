from flask import Blueprint, render_template, session, jsonify, request
from extensions import supabase, supabase_admin
from routes.auth import login_required, role_required
from routes.api import get_user_companies
from permissions import check_permission
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import json
import requests
import traceback
import os
from services.data_cache import DataCacheService
from services.retry_utils import run_with_retries
from services.client_branding import get_client_branding

# Instanciar o serviço de cache
data_cache = DataCacheService()

# Criar blueprint para o módulo
dash_importacoes_resumido_bp = Blueprint(
    'dash_importacoes_resumido', 
    __name__,
    template_folder='templates',
    static_folder='static',
    url_prefix='/dash-importacoes-resumido'
)

def format_currency(value):
    """Formatar valores monetários em formato brasileiro."""
    if value is None or pd.isna(value):
        return "R$ 0,00"
    try:
        return f"R$ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return "R$ 0,00"

def get_modal_icon(modal):
    """Retornar o ícone do modal de transporte."""
    modal_icons = {
        '1': 'mdi-ship',      # Marítimo
        '4': 'mdi-airplane',  # Aéreo
        '7': 'mdi-truck'      # Terrestre
    }
    return modal_icons.get(str(modal), 'mdi-help-circle')

def get_canal_color(canal):
    """Retornar a cor do canal aduaneiro."""
    canal_colors = {
        'Verde': '#4CAF50',
        'Amarelo': '#FF9800', 
        'Vermelho': '#F44336'
    }
    return canal_colors.get(canal, '#9E9E9E')

def normalize_modal(value):
    """Normaliza diferentes representações de modal para códigos '1','4','7'.
    Aceita valores numéricos, strings com acentuação e sinônimos.
    Retorna string vazia se não reconhecido (frontend tratará fallback).
    """
    if value is None:
        return ''
    v = str(value).strip().upper()
    # Remover sufixos .0 de conversões de float
    if v.endswith('.0'):
        v = v[:-2]
    # Tentar mapear diretamente números
    if v in {'1','4','7'}:
        return v
    # Sinônimos marítimo
    if v in {'MARITIMO','MARÍTIMO','MARÍTIMA','MARITIMA','SHIP','NAVIO','SEA','OCEAN'}:
        return '1'
    # Sinônimos aéreo
    if v in {'AEREO','AÉREO','AÉREA','AEREA','AIR','AIRPLANE','PLANE','AVIAO','AVIÃO'}:
        return '4'
    # Sinônimos terrestre
    if v in {'TERRESTRE','RODOVIARIO','RODOVIÁRIO','TRUCK','ROAD'}:
        return '7'
    # Se contiver dígitos tentamos pegar primeiro
    digits = ''.join(ch for ch in v if ch.isdigit())
    if digits in {'1','4','7'}:
        return digits
    return ''

def get_exchange_rates():
    """Obter cotações do dólar e euro do Banco Central."""
    try:
        url = 'https://www.bcb.gov.br/api/servico/sitebcb/indicadorCambio'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        dolar_rate = None
        euro_rate = None
        
        for item in data.get('conteudo', []):
            if item.get('tipoCotacao') == 'Intermediária':
                if item.get('moeda') == 'Dólar':
                    dolar_rate = (item.get('valorCompra', 0) + item.get('valorVenda', 0)) / 2
                elif item.get('moeda') == 'Euro':
                    euro_rate = (item.get('valorCompra', 0) + item.get('valorVenda', 0)) / 2
        
        return {
            'dolar': round(dolar_rate, 4) if dolar_rate else None,
            'euro': round(euro_rate, 4) if euro_rate else None
        }
    
    except Exception as e:
        print(f"Erro ao obter cotações: {e}")
        return {'dolar': None, 'euro': None}

@dash_importacoes_resumido_bp.route('/')
@login_required
def dashboard():
    """Página principal do dashboard de importações resumido."""
    
    # Verificar permissões
    if not check_permission('dashboard_executivo.visualizar'):
        return render_template('errors/403.html'), 403
    
    # Verificar se é cliente_unique sem empresas associadas
    user_data = session.get('user', {})
    user_role = user_data.get('role')
    perfil_principal = user_data.get('perfil_principal', '')
    
    # Admin operação tem acesso a todas as empresas - nunca mostrar warning
    if perfil_principal in ['admin_operacao', 'master_admin']:
        print(f"[DASH_RESUMIDO] Admin {user_data.get('email')} - acesso total, sem warning")
        return render_template('dash_importacoes_resumido/dash_importacoes_resumido.html', show_company_warning=False)
    
    if user_role == 'cliente_unique':
        user_cnpjs = get_user_companies(user_data)
        if not user_cnpjs:
            print(f"[DASH_RESUMIDO] Cliente {user_data.get('email')} sem empresas vinculadas - exibindo aviso")
            # Passar flag para o template indicar que deve mostrar aviso
            return render_template('dash_importacoes_resumido/dash_importacoes_resumido.html', show_company_warning=True)
    
    # Verificar se é interno_unique sem empresas associadas (exceto admins)
    if user_role == 'interno_unique':
        user_cnpjs = get_user_companies(user_data)
        if not user_cnpjs:
            print(f"[DASH_RESUMIDO] Usuário interno {user_data.get('email')} sem empresas vinculadas - exibindo aviso")
            # Passar flag para o template indicar que deve mostrar aviso
            return render_template('dash_importacoes_resumido/dash_importacoes_resumido.html', show_company_warning=True)
    
    return render_template('dash_importacoes_resumido/dash_importacoes_resumido.html', show_company_warning=False)

@dash_importacoes_resumido_bp.route('/api/data')
@login_required
def get_dashboard_data():
    """API para obter dados do dashboard."""

    try:
        # Obter informações do usuário
        user = session.get('user', {}) or {}
        user_id = user.get('id')
        user_role = user.get('role')
        user_email = user.get('email')
        perfil_principal = user.get('perfil_principal', '')

        if not user_id:
            return jsonify({'error': 'Usuário não autenticado'}), 401

        print(f"[DEBUG] Dashboard API chamada por user_id: {user_id}, role: {user_role}, perfil: {perfil_principal}")

        # Obter filtros da requisição
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        filtro_embarque = request.args.get('filtro_embarque', '')
        company_filter = request.args.get('company_filter', '')

        print(f"[DEBUG] Parâmetros: page={page}, per_page={per_page}, filtro_embarque={filtro_embarque}, company_filter={company_filter}")

        # NOVA LÓGICA: Verificar se deve exigir filtro de empresa antes de carregar dados
        api_bypass_key = os.getenv('API_BYPASS_KEY')
        request_api_key = request.headers.get('X-API-Key')
        is_bypass = api_bypass_key and request_api_key == api_bypass_key
        
        if not is_bypass:  # Não aplicar restrição em modo bypass (para testes)
            if perfil_principal == 'admin_operacao':
                # Admin com acesso a todas as empresas - exigir filtro
                if not company_filter:
                    print("[DEBUG] Admin operação sem filtro - retornando mensagem de seleção obrigatória")
                    return jsonify({
                        'success': False,
                        'require_filter': True,
                        'message': 'Selecione uma ou mais empresas para carregar o dashboard. Dashboard pesado requer filtro.',
                        'data': [],
                        'header': {
                            'total_processos': 0,
                            'count_maritimo': 0,
                            'count_aereo': 0,
                            'count_terrestre': 0,
                            'current_time': datetime.now().strftime('%H:%M'),
                            'current_date': datetime.now().strftime('%d %B').upper(),
                            'exchange_rates': get_exchange_rates(),
                            'client': get_client_branding(user_email)
                        },
                        'pagination': {'total': 0, 'pages': 0, 'current_page': 1, 'per_page': per_page}
                    })
            
            elif user_role in ['cliente_unique', 'interno_unique']:
                # Usuários com empresas específicas
                user_cnpjs = get_user_companies(user)
                company_count = len(user_cnpjs) if user_cnpjs else 0
                
                if company_count > 1 and not company_filter:
                    # Múltiplas empresas - exigir filtro
                    print(f"[DEBUG] Usuário com {company_count} empresas sem filtro - retornando mensagem de seleção obrigatória")
                    return jsonify({
                        'success': False,
                        'require_filter': True,
                        'message': f'Você tem acesso a {company_count} empresas. Selecione uma ou mais para carregar o dashboard.',
                        'data': [],
                        'header': {
                            'total_processos': 0,
                            'count_maritimo': 0,
                            'count_aereo': 0,
                            'count_terrestre': 0,
                            'current_time': datetime.now().strftime('%H:%M'),
                            'current_date': datetime.now().strftime('%d %B').upper(),
                            'exchange_rates': get_exchange_rates(),
                            'client': get_client_branding(user_email)
                        },
                        'pagination': {'total': 0, 'pages': 0, 'current_page': 1, 'per_page': per_page}
                    })
                
                elif company_count == 1:
                    # Uma empresa - carregar automaticamente
                    company_filter = user_cnpjs[0]
                    print(f"[DEBUG] Usuário com 1 empresa - carregando automaticamente: {company_filter}")
        else:
            print("[DEBUG] Bypass ativo - pulando verificação de filtro obrigatório")

        # Buscar branding (logo e nome da empresa do usuário) usando função compartilhada
        client_branding = get_client_branding(user_email)

        # Verificar se está usando bypass - se sim, pular cache e ir direto para view
        api_bypass_key = os.getenv('API_BYPASS_KEY')
        request_api_key = request.headers.get('X-API-Key')
        is_bypass = api_bypass_key and request_api_key == api_bypass_key
        
        cached_data = None
        
        if not is_bypass:
            # Verificar cache primeiro apenas se não estiver usando bypass
            cached_data = session.get('cached_data')
            print(f"[DEBUG] Cache session: {type(cached_data)} com {len(cached_data) if cached_data else 0} registros")

            if not cached_data:
                cached_data = data_cache.get_cache(user_id, 'raw_data')
                print(f"[DEBUG] Cache service: {type(cached_data)} com {len(cached_data) if cached_data else 0} registros")
        else:
            print(f"[DEBUG] BYPASS ATIVO - Ignorando cache e indo direto para a view")

        # Se ainda não há dados, tentar buscar direto da view
        if not cached_data or not isinstance(cached_data, list):
            print(f"[DEBUG] Buscando dados direto da view vw_importacoes_6_meses_abertos_dash... (is_bypass: {is_bypass})")
            try:
                query = supabase_admin.table('vw_importacoes_6_meses_abertos_dash').select('*')

                # Verificar se usuário tem perfil admin_operacao - se sim, pode ver todos os dados
                perfil_principal = user.get('perfil_principal', '')
                is_admin_operacao = perfil_principal == 'admin_operacao'

                if user_role == 'cliente_unique' or (user_role == 'interno_unique' and not is_admin_operacao):
                    user_cnpjs = get_user_companies(user)
                    print(f"[DEBUG] Role: {user_role}, CNPJs encontrados: {user_cnpjs}")
                    if user_cnpjs:
                        query = query.in_('cnpj_importador', user_cnpjs)
                        print(f"[DEBUG] Query filtrada por CNPJs das empresas vinculadas: {user_cnpjs}")
                    else:
                        print(f"[DEBUG] Usuário {user_role} sem CNPJs vinculados - retornando aviso de segurança")
                        return jsonify({
                            'success': False,
                            'error': 'no_companies', 
                            'message': 'Usuário sem empresas vinculadas. Entre em contato com o administrador para associar empresas ao seu perfil.',
                            'show_warning': True,
                            'header': {
                                'total_processos': 0,
                                'count_maritimo': 0,
                                'count_aereo': 0,
                                'count_terrestre': 0,
                                'current_time': datetime.now().strftime('%H:%M'),
                                'current_date': datetime.now().strftime('%d %B').upper(),
                                'exchange_rates': get_exchange_rates(),
                                'client': client_branding
                            },
                            'data': [],
                            'pagination': {'total': 0, 'pages': 0, 'current_page': 1, 'per_page': per_page}
                        })
                elif is_admin_operacao:
                    print(f"[DEBUG] Usuário admin_operacao -> carregando TODOS os dados (sem filtro de CNPJ)")
                elif user_role == 'admin':
                    print(f"[DEBUG] Usuário admin -> carregando TODOS os dados (sem filtro de CNPJ)")

                def _run_query():
                    print(f"[DEBUG] Executando query na view sem limite...")
                    result = query.execute()
                    print(f"[DEBUG] Query executada, resultado: {result}")
                    return result
                result = run_with_retries(
                    'dash_resumido.main_query',
                    _run_query,
                    max_attempts=3,
                    base_delay_seconds=0.8,
                    should_retry=lambda e: 'Server disconnected' in str(e) or 'timeout' in str(e).lower()
                )
                cached_data = result.data or []
                print(f"[DEBUG] Dados obtidos direto da view: {len(cached_data)} registros")
                if cached_data and len(cached_data) > 0:
                    print(f"[DEBUG] Primeiro registro da view: {cached_data[0]}")
                    print(f"[DEBUG] Campos do primeiro registro: {list(cached_data[0].keys())}")
                    # Verificar se há dados com o CNPJ filtrado
                    if company_filter:
                        matching_records = [r for r in cached_data if r.get('cnpj_importador') == company_filter]
                        print(f"[DEBUG] Registros com CNPJ {company_filter}: {len(matching_records)}")
                else:
                    print(f"[DEBUG] ATENÇÃO: View retornou dados vazios!")
            except Exception as e:
                print(f"[DEBUG] Erro ao buscar da view: {e}")

        # Se ainda não há dados, retornar dados de exemplo
        if not cached_data or not isinstance(cached_data, list) or len(cached_data) == 0:
            print(f"[DEBUG] DADOS DE EXEMPLO ATIVADOS - cached_data: {type(cached_data)}, len: {len(cached_data) if cached_data else 'None'}, is_bypass: {is_bypass}")
            return jsonify({
                'success': True,
                'message': 'Dados de exemplo - cache vazio',
                'header': {
                    'total_processos': 3,
                    'count_maritimo': 2,
                    'count_aereo': 1,
                    'count_terrestre': 0,
                    'current_time': datetime.now().strftime('%H:%M'),
                    'current_date': datetime.now().strftime('%d %B').upper(),
                    'exchange_rates': get_exchange_rates(),
                    'client': client_branding
                },
                'data': [
                    { 'modal': '1', 'numero': 1, 'numero_di': '25/1641705-4', 'pais_procedencia': 'CHINA', 'pais_flag': 'https://flagcdn.com/w40/cn.png', 'ref_importador': '0337/25 - SHANGHAI SCHULZ', 'data_embarque': '16/07/2025', 'data_chegada': '25/07/2025', 'data_registro': '25/07/2025', 'canal': 'Verde', 'canal_color': '#4CAF50', 'data_entrega': '29/07/2025', 'urf_destino': 'SANTOS' },
                    { 'modal': '4', 'numero': 2, 'numero_di': '25/1641706-2', 'pais_procedencia': 'ALEMANHA', 'pais_flag': 'https://flagcdn.com/w40/de.png', 'ref_importador': '0338/25 - AIRBUS PARTS', 'data_embarque': '18/07/2025', 'data_chegada': '19/07/2025', 'data_registro': '20/07/2025', 'canal': 'Amarelo', 'canal_color': '#FF9800', 'data_entrega': '22/07/2025', 'urf_destino': 'GUARULHOS' },
                    { 'modal': '1', 'numero': 3, 'numero_di': '25/1641707-0', 'pais_procedencia': 'COREIA DO SUL', 'pais_flag': 'https://flagcdn.com/w40/kr.png', 'ref_importador': '0339/25 - MARINE SUPPLY', 'data_embarque': '20/07/2025', 'data_chegada': '30/07/2025', 'data_registro': '01/08/2025', 'canal': 'Vermelho', 'canal_color': '#F44336', 'data_entrega': '', 'urf_destino': 'ITAJAI' }
                ],
                'pagination': { 'total': 3, 'pages': 1, 'current_page': 1, 'per_page': per_page }
            })

        # Converter para DataFrame
        df = pd.DataFrame(cached_data)

        if df.empty:
            return jsonify({
                'error': 'Cache vazio',
                'message': 'Nenhum dado encontrado no cache. Faça login novamente.',
                'data': [],
                'pagination': {'total': 0, 'pages': 0, 'current_page': 1}
            }), 404

        print(f"[DEBUG] DataFrame criado com {len(df)} registros")
        print(f"[DEBUG] Colunas disponíveis: {list(df.columns)}")
        print(f"[DEBUG] Filtros ativos: user_role={user_role}, company_filter={company_filter}, filtro_embarque={filtro_embarque}")

        # Aplicar filtro adicional por empresa se necessário (apenas para clientes específicos)
        if user_role in ['cliente_unique', 'interno_unique'] and 'cnpj_importador' in df.columns:
            # Para admin_operacao, não aplicar este filtro restritivo quando há company_filter específico
            perfil_principal = user.get('perfil_principal', '')
            if perfil_principal == 'admin_operacao' and company_filter:
                print(f"[DEBUG] Admin operação com filtro específico - pulando filtro restritivo de CNPJs")
            else:
                user_cnpjs = get_user_companies(user)
                if user_cnpjs:
                    before = len(df)
                    df = df[df['cnpj_importador'].isin(user_cnpjs)]
                    print(f"[DEBUG] Filtrado por CNPJs do usuário: {before} -> {len(df)} registros")
                else:
                    print(f"[DEBUG] Usuário sem CNPJs - zerando dataset")
                    df = df.iloc[0:0]

        # Filtro de data de embarque
        if filtro_embarque == 'preenchida' and 'data_embarque' in df.columns:
            df = df[df['data_embarque'].notna() & (df['data_embarque'] != '')]
            print(f"[DEBUG] Filtrado por data embarque: {len(df)} registros")

        # Filtro por empresa específica (quando selecionada no dropdown) - suporte múltiplas empresas
        if company_filter and 'cnpj_importador' in df.columns:
            before_filter = len(df)
            
            # Suporte para múltiplas empresas (separadas por vírgula)
            if ',' in company_filter:
                company_list = [cnpj.strip() for cnpj in company_filter.split(',') if cnpj.strip()]
                df = df[df['cnpj_importador'].isin(company_list)]
                print(f"[DEBUG] Filtrado por múltiplas empresas {company_list}: {before_filter} -> {len(df)} registros")
            else:
                # Uma empresa apenas (compatibilidade com versão anterior)
                df = df[df['cnpj_importador'] == company_filter]
                print(f"[DEBUG] Filtrado por empresa {company_filter}: {before_filter} -> {len(df)} registros")

        # Métricas
        if 'modal' in df.columns:
            print(f"[DEBUG] Valores originais únicos de modal: {sorted({str(m) for m in df['modal'].dropna().unique()})}")
            # Criar coluna normalizada para evitar inconsistências (ex: '4.0', 'AÉREO', etc.)
            df['modal_normalizado'] = df['modal'].apply(normalize_modal)
            # Substituir coluna principal para simplificar downstream
            df['modal'] = df['modal_normalizado']
            print(f"[DEBUG] Valores normalizados únicos de modal: {sorted({str(m) for m in df['modal'].dropna().unique()})}")
        else:
            df['modal_normalizado'] = ''

        total_processos = len(df)
        modal_counts = df['modal_normalizado'].value_counts() if 'modal_normalizado' in df.columns else pd.Series(dtype=int)
        count_maritimo = count_aereo = count_terrestre = 0
        for modal, count in modal_counts.items():
            if modal == '1':
                count_maritimo += int(count)
            elif modal == '4':
                count_aereo += int(count)
            elif modal == '7':
                count_terrestre += int(count)

        print(f"[DEBUG] Contagem normalizada -> Marítimo: {count_maritimo}, Aéreo: {count_aereo}, Terrestre: {count_terrestre}")

        # Padronização de colunas
        column_mapping = {
            'modal': 'modal',
            'numero_di': 'numero_di',
            'pais_procedencia': 'pais_procedencia',
            'url_bandeira': 'url_bandeira',
            'ref_importador': 'ref_importador',
            'data_embarque': 'data_embarque',
            'data_chegada': 'data_chegada',
            'data_registro': 'data_registro',
            'canal': 'canal',
            'data_entrega': 'data_desembaraco',
            'urf_destino': 'urf_despacho',
            'cnpj_importador': 'cnpj_importador'  # Incluir CNPJ para debug e validação
        }

        standardized_data = []
        for _, r in df.iterrows():
            new_row = {}
            for std_col, src_col in column_mapping.items():
                val = r[src_col] if src_col in r and pd.notna(r[src_col]) else ''
                new_row[std_col] = str(val) if val is not None else ''
            standardized_data.append(new_row)

        df_display = pd.DataFrame(standardized_data)

        # Paginação
        total_records = len(df_display)
        total_pages = (total_records + per_page - 1) // per_page if per_page > 0 else 1
        total_pages = max(total_pages, 1)
        start_idx = max((page - 1), 0) * per_page
        end_idx = start_idx + per_page
        df_page = df_display.iloc[start_idx:end_idx] if total_records > 0 else df_display

        # Dados da tabela
        table_data = []
        for _, r in df_page.iterrows():
            modal_val = r.get('modal', '')  # já substituído pelo normalizado
            pais_procedencia = str(r.get('pais_procedencia', '') or '')
            url_bandeira = str(r.get('url_bandeira', '') or '')
            
            # Só incluir bandeira se realmente houver país
            pais_flag = ''
            if pais_procedencia and pais_procedencia.strip() and url_bandeira and url_bandeira.strip():
                pais_flag = url_bandeira
            
            table_data.append({
                'modal': modal_val,
                'numero': start_idx + len(table_data) + 1,
                'numero_di': str(r.get('numero_di', '') or ''),
                'pais_procedencia': pais_procedencia,
                'pais_flag': pais_flag,
                'ref_importador': str(r.get('ref_importador', '') or ''),
                'data_embarque': str(r.get('data_embarque', '') or ''),
                'data_chegada': str(r.get('data_chegada', '') or ''),
                'data_registro': str(r.get('data_registro', '') or ''),
                'canal': str(r.get('canal', '') or ''),
                'canal_color': get_canal_color(str(r.get('canal', '') or '')),
                'data_entrega': str(r.get('data_entrega', '') or ''),
                'urf_destino': str(r.get('urf_destino', '') or ''),
                'cnpj_importador': str(r.get('cnpj_importador', '') or '')  # Incluir CNPJ para validação
            })

        exchange_rates = get_exchange_rates()

        response_data = {
            'success': True,
            'header': {
                'total_processos': total_processos,
                'count_maritimo': count_maritimo,
                'count_aereo': count_aereo,
                'count_terrestre': count_terrestre,
                'current_time': datetime.now().strftime('%H:%M'),
                'current_date': datetime.now().strftime('%d %B').upper(),
                'exchange_rates': exchange_rates,
                'client': client_branding
            },
            'data': table_data,
            'pagination': {
                'total': total_records,
                'pages': total_pages,
                'current_page': page,
                'per_page': per_page
            }
        }

        print(f"[DEBUG] Retornando {len(table_data)} registros para página {page}")
        return jsonify(response_data)

    except Exception as e:
        print(f"[ERROR] Erro ao obter dados do dashboard: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Erro interno do servidor', 'details': str(e)}), 500

@dash_importacoes_resumido_bp.route('/api/companies')
def get_companies():
    """API para obter empresas disponíveis para filtro."""
    try:
        # Verificar bypass para testes
        api_bypass_key = os.getenv('API_BYPASS_KEY')
        request_api_key = request.headers.get('X-API-Key')
        
        if api_bypass_key and request_api_key == api_bypass_key:
            print("[DEBUG] API Bypass autorizado - simulando admin_operacao")
            # Simular usuário admin_operacao para teste
            user = {'role': 'interno_unique', 'perfil_principal': 'admin_operacao'}
        else:
            # Verificar login normal
            if 'user' not in session:
                return jsonify({'success': False, 'error': 'Não autenticado'}), 401
            user = session.get('user', {})
        
        user_role = user.get('role')
        
        # Para admin_operacao, buscar todas as empresas dos dados ativos
        perfil_principal = user.get('perfil_principal', '')
        if perfil_principal == 'admin_operacao':
            print("[DEBUG] Admin operação - buscando todas as empresas dos dados")
            # Primeiro tentar buscar com limit para identificar colunas disponíveis
            query = supabase_admin.table('vw_importacoes_6_meses_abertos_dash').select('*').limit(1).execute()
            
            if query.data:
                colunas_disponiveis = list(query.data[0].keys())
                print(f"[DEBUG] Colunas disponíveis na view: {colunas_disponiveis}")
                
                # Identificar a coluna de razão social
                razao_col = None
                for col in colunas_disponiveis:
                    if 'razao' in col.lower() or 'nome' in col.lower():
                        razao_col = col
                        break
                
                if not razao_col:
                    razao_col = 'cnpj_importador'  # Fallback
                
                print(f"[DEBUG] Usando coluna para razao social: {razao_col}")
                
                # Buscar dados completos usando 'importador' como nome da empresa
                query_full = supabase_admin.table('vw_importacoes_6_meses_abertos_dash').select('cnpj_importador, importador').execute()
                
                # Agrupar por CNPJ para evitar duplicatas
                empresas_dict = {}
                for row in query_full.data or []:
                    cnpj = row.get('cnpj_importador')
                    razao = row.get('importador', 'Empresa não informada')
                    if cnpj and cnpj not in empresas_dict:
                        empresas_dict[cnpj] = razao
                
                empresas = [{'cnpj': cnpj, 'nome': razao} for cnpj, razao in empresas_dict.items()]
            else:
                print("[DEBUG] Nenhum dado encontrado na view")
                empresas = []
            
        else:
            # Para outros usuários, buscar apenas suas empresas vinculadas
            user_cnpjs = get_user_companies(user)
            if not user_cnpjs:
                return jsonify({'success': True, 'empresas': []})
            
            # Buscar dados das empresas vinculadas
            query = supabase_admin.table('vw_importacoes_6_meses_abertos_dash').select('cnpj_importador, importador').in_('cnpj_importador', user_cnpjs).execute()
            
            empresas_dict = {}
            for row in query.data or []:
                cnpj = row.get('cnpj_importador')
                razao = row.get('importador', 'Empresa não informada')
                if cnpj:
                    empresas_dict[cnpj] = razao
            
            empresas = [{'cnpj': cnpj, 'nome': razao} for cnpj, razao in empresas_dict.items()]
        
        # Ordenar por nome
        empresas.sort(key=lambda x: x['nome'])
        
        print(f"[DEBUG] Encontradas {len(empresas)} empresas para filtro")
        return jsonify({
            'success': True,
            'empresas': empresas
        })
        
    except Exception as e:
        print(f"[ERROR] Erro ao buscar empresas: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@dash_importacoes_resumido_bp.route('/api/companies-info')
def get_companies_info():
    """API para obter informações sobre empresas do usuário e lógica de carregamento."""
    try:
        # Verificar bypass para testes
        api_bypass_key = os.getenv('API_BYPASS_KEY')
        request_api_key = request.headers.get('X-API-Key')
        
        if api_bypass_key and request_api_key == api_bypass_key:
            print("[DEBUG] API Bypass autorizado - simulando admin_operacao")
            user = {'role': 'interno_unique', 'perfil_principal': 'admin_operacao'}
        else:
            if 'user' not in session:
                return jsonify({'success': False, 'error': 'Não autenticado'}), 401
            user = session.get('user', {})
        
        user_role = user.get('role')
        perfil_principal = user.get('perfil_principal', '')
        
        # Lógica de carregamento baseada na quantidade de empresas
        if perfil_principal == 'admin_operacao':
            # Admin com acesso a todas as empresas - sempre obrigar filtro
            print("[DEBUG] Admin operação - obrigando seleção de filtro")
            return jsonify({
                'success': True,
                'require_filter': True,
                'auto_load': False,
                'company_count': 'all',
                'message': 'Selecione uma ou mais empresas para carregar o dashboard',
                'reason': 'Admin com acesso a todas as empresas'
            })
        
        else:
            # Usuários com empresas específicas
            user_cnpjs = get_user_companies(user)
            company_count = len(user_cnpjs) if user_cnpjs else 0
            
            if company_count == 0:
                print(f"[DEBUG] Usuário sem empresas vinculadas")
                return jsonify({
                    'success': True,
                    'require_filter': False,
                    'auto_load': False,
                    'company_count': 0,
                    'message': 'Usuário sem empresas vinculadas. Entre em contato com o administrador.',
                    'reason': 'Nenhuma empresa vinculada'
                })
            
            elif company_count == 1:
                print(f"[DEBUG] Usuário com 1 empresa - carregamento automático")
                return jsonify({
                    'success': True,
                    'require_filter': False,
                    'auto_load': True,
                    'company_count': 1,
                    'auto_company': user_cnpjs[0],
                    'message': 'Dashboard carregado automaticamente para sua empresa',
                    'reason': 'Usuário com apenas uma empresa'
                })
            
            else:
                print(f"[DEBUG] Usuário com {company_count} empresas - obrigando filtro")
                return jsonify({
                    'success': True,
                    'require_filter': True,
                    'auto_load': False,
                    'company_count': company_count,
                    'message': f'Selecione uma ou mais das suas {company_count} empresas para carregar o dashboard',
                    'reason': 'Usuário com múltiplas empresas'
                })
        
    except Exception as e:
        print(f"[ERROR] Erro ao buscar informações das empresas: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@dash_importacoes_resumido_bp.route('/debug-view')
def debug_view():
    """Endpoint de debug para testar a view diretamente."""
    try:
        print("[DEBUG_VIEW] Testando acesso direto à view...")
        
        # Verificar bypass
        api_bypass_key = os.getenv('API_BYPASS_KEY')
        request_api_key = request.headers.get('X-API-Key')
        
        if not (api_bypass_key and request_api_key == api_bypass_key):
            return jsonify({'error': 'Bypass necessário para debug'}), 403
        
        # Tentar query direta na view
        query = supabase_admin.table('vw_importacoes_6_meses_abertos_dash').select('*').limit(5)
        result = query.execute()
        
        print(f"[DEBUG_VIEW] Resultado da query: {result}")
        
        return jsonify({
            'success': True,
            'total_registros': len(result.data) if result.data else 0,
            'dados': result.data or [],
            'status': 'view_acessada_com_sucesso'
        })
        
    except Exception as e:
        print(f"[DEBUG_VIEW] Erro: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'status': 'erro_ao_acessar_view'
        }), 500

@dash_importacoes_resumido_bp.route('/test')
def test():
    """Endpoint de teste para validar o módulo."""
    return jsonify({
        'module': 'dash_importacoes_resumido',
        'status': 'ok',
        'timestamp': datetime.now().isoformat()
    })
