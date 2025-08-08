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
from services.data_cache import DataCacheService

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
    
    return render_template('dash_importacoes_resumido/dash_importacoes_resumido.html')

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

        if not user_id:
            return jsonify({'error': 'Usuário não autenticado'}), 401

        print(f"[DEBUG] Dashboard API chamada por user_id: {user_id}, role: {user_role}")

        # Obter filtros da requisição
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        filtro_embarque = request.args.get('filtro_embarque', '')

        print(f"[DEBUG] Parâmetros: page={page}, per_page={per_page}, filtro_embarque={filtro_embarque}")

        # Buscar branding (logo e nome da empresa do usuário) na view vw_user_client_logos
        client_branding = {'name': 'Unique', 'logo_url': '/static/medias/Logo_Unique.png'}
        try:
            if user_email:
                branding_q = supabase_admin.table('vw_user_client_logos') \
                    .select('empresa, logo_url') \
                    .eq('user_email', user_email) \
                    .limit(1).execute()
                if branding_q.data:
                    row = branding_q.data[0]
                    if row.get('empresa'):
                        client_branding['name'] = row.get('empresa')
                    if row.get('logo_url'):
                        client_branding['logo_url'] = row.get('logo_url')
            print(f"[DEBUG] Branding selecionado: {client_branding}")
        except Exception as be:
            print(f"[DEBUG] Erro ao obter branding do cliente: {be}")

        # Verificar cache primeiro
        cached_data = session.get('cached_data')
        print(f"[DEBUG] Cache session: {type(cached_data)} com {len(cached_data) if cached_data else 0} registros")

        if not cached_data:
            cached_data = data_cache.get_cache(user_id, 'raw_data')
            print(f"[DEBUG] Cache service: {type(cached_data)} com {len(cached_data) if cached_data else 0} registros")

        # Se ainda não há dados, tentar buscar direto da view
        if not cached_data or not isinstance(cached_data, list):
            print("[DEBUG] Buscando dados direto da view vw_importacoes_6_meses_abertos_dash...")
            try:
                query = supabase.table('vw_importacoes_6_meses_abertos_dash').select('*')

                if user_role in ['cliente_unique', 'interno_unique']:
                    user_cnpjs = get_user_companies(user)
                    print(f"[DEBUG] Role: {user_role}, CNPJs encontrados: {user_cnpjs}")
                    if user_cnpjs:
                        query = query.in_('cnpj_importador', user_cnpjs)
                        print(f"[DEBUG] Query filtrada por CNPJs das empresas vinculadas: {user_cnpjs}")
                    else:
                        print(f"[DEBUG] Usuário {user_role} sem CNPJs vinculados - retornando vazio")
                        return jsonify({
                            'success': True,
                            'message': 'Usuário sem empresas vinculadas',
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

                result = query.limit(100).execute()
                cached_data = result.data or []
                print(f"[DEBUG] Dados obtidos direto da view: {len(cached_data)} registros")
            except Exception as e:
                print(f"[DEBUG] Erro ao buscar da view: {e}")

        # Se ainda não há dados, retornar dados de exemplo
        if not cached_data or not isinstance(cached_data, list) or len(cached_data) == 0:
            print("[DEBUG] Retornando dados de exemplo para teste")
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
                    { 'modal': '1', 'numero': 1, 'numero_di': '25/1641705-4', 'ref_unique': 'UN25/6495', 'ref_importador': '0337/25 - SHANGHAI SCHULZ', 'data_embarque': '16/07/2025', 'data_chegada': '25/07/2025', 'data_registro': '25/07/2025', 'canal': 'Verde', 'canal_color': '#4CAF50', 'data_entrega': '29/07/2025' },
                    { 'modal': '4', 'numero': 2, 'numero_di': '25/1641706-2', 'ref_unique': 'UN25/6496', 'ref_importador': '0338/25 - AIRBUS PARTS', 'data_embarque': '18/07/2025', 'data_chegada': '19/07/2025', 'data_registro': '20/07/2025', 'canal': 'Amarelo', 'canal_color': '#FF9800', 'data_entrega': '22/07/2025' },
                    { 'modal': '1', 'numero': 3, 'numero_di': '25/1641707-0', 'ref_unique': 'UN25/6497', 'ref_importador': '0339/25 - MARINE SUPPLY', 'data_embarque': '20/07/2025', 'data_chegada': '30/07/2025', 'data_registro': '01/08/2025', 'canal': 'Vermelho', 'canal_color': '#F44336', 'data_entrega': '' }
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

        # Aplicar filtro adicional por empresa se necessário
        if user_role in ['cliente_unique', 'interno_unique'] and 'cnpj_importador' in df.columns:
            user_cnpjs = get_user_companies(user)
            if user_cnpjs:
                before = len(df)
                df = df[df['cnpj_importador'].isin(user_cnpjs)]
                print(f"[DEBUG] Filtrado por CNPJs: {before} -> {len(df)} registros")
            else:
                df = df.iloc[0:0]

        # Filtro de data de embarque
        if filtro_embarque == 'preenchida' and 'data_embarque' in df.columns:
            df = df[df['data_embarque'].notna() & (df['data_embarque'] != '')]
            print(f"[DEBUG] Filtrado por data embarque: {len(df)} registros")

        # Métricas
        total_processos = len(df)
        modal_counts = df['modal'].value_counts() if 'modal' in df.columns else pd.Series(dtype=int)
        count_maritimo = count_aereo = count_terrestre = 0
        for modal, count in modal_counts.items():
            m = str(modal).upper()
            if m in ['1', 'MARÍTIMO', 'MARÍTIMA', 'MARITIMO', 'SHIP']:
                count_maritimo += int(count)
            elif m in ['4', 'AÉREO', 'AÉREA', 'AEREO', 'AIRPLANE', 'PLANE']:
                count_aereo += int(count)
            elif m in ['7', 'TERRESTRE', 'RODOVIÁRIO', 'RODOVIARIO', 'TRUCK']:
                count_terrestre += int(count)

        # Padronização de colunas
        column_mapping = {
            'modal': 'modal',
            'numero_di': 'numero_di',
            'ref_unique': 'ref_unique',
            'ref_importador': 'ref_importador',
            'data_embarque': 'data_embarque',
            'data_chegada': 'data_chegada',
            'data_registro': 'data_registro',
            'canal': 'canal',
            'data_entrega': 'data_desembaraco',
            'urf_destino': 'urf_despacho'
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
            table_data.append({
                'modal': str(r.get('modal', '') or ''),
                'numero': start_idx + len(table_data) + 1,
                'numero_di': str(r.get('numero_di', '') or ''),
                'ref_unique': str(r.get('ref_unique', '') or ''),
                'ref_importador': str(r.get('ref_importador', '') or ''),
                'data_embarque': str(r.get('data_embarque', '') or ''),
                'data_chegada': str(r.get('data_chegada', '') or ''),
                'data_registro': str(r.get('data_registro', '') or ''),
                'canal': str(r.get('canal', '') or ''),
                'canal_color': get_canal_color(str(r.get('canal', '') or '')),
                'data_entrega': str(r.get('data_entrega', '') or ''),
                'urf_destino': str(r.get('urf_destino', '') or '')
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

@dash_importacoes_resumido_bp.route('/test')
def test():
    """Endpoint de teste para validar o módulo."""
    return jsonify({
        'module': 'dash_importacoes_resumido',
        'status': 'ok',
        'timestamp': datetime.now().isoformat()
    })
