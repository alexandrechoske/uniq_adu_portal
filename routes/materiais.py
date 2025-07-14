from flask import Blueprint, render_template, session, request, jsonify
from extensions import supabase
from routes.auth import login_required, role_required
from permissions import check_permission
from datetime import datetime, timedelta
from collections import defaultdict
import traceback
import sys
import os

# Adicionar o diretório raiz ao path para importar o material_cleaner
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from material_cleaner import MaterialCleaner

# Instância global do limpador
material_cleaner = MaterialCleaner()

bp = Blueprint('materiais', __name__)

@bp.route('/')
@login_required
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def index():
    """Página principal de materiais - nova versão"""
    return render_template('materiais/index.html')

@bp.route('/materiais_data')
@login_required  
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def materiais_data():
    """API para obter dados dos materiais (KPIs e gráficos)"""
    try:
        # Get user companies if client
        user_companies = []
        current_role = session['user']['role']
        
        if current_role == 'cliente_unique':
            user_companies = session['user'].get('user_companies', [])
        
        # Obter parâmetros de filtro da requisição
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        material = request.args.get('material')
        cliente = request.args.get('cliente')
        modal = request.args.get('modal')
        force_refresh = request.args.get('refresh', 'false').lower() == 'true'
        
        print(f"[MATERIAIS API] Filtros recebidos - Início: {data_inicio}, Fim: {data_fim}, Material: {material}, Cliente: {cliente}, Modal: {modal}, Refresh: {force_refresh}")
        
        # Verificar se existem dados em cache primeiro (só se não forçar refresh e não houver filtros)
        if not force_refresh and not any([data_inicio, data_fim, material, cliente, modal]):
            cached_data = session.get('cached_data', {})
            materiais_cache = cached_data.get('materiais', {})
            
            if materiais_cache:
                print("[MATERIAIS API] Usando dados em cache")
                return jsonify(materiais_cache)
        
        print("[MATERIAIS API] Buscando dados do banco")
        
        # Buscar dados base de processos com filtros de data
        # Se não há filtros específicos, usar lógica do dashboard (só data mínima)
        if data_inicio and data_fim:
            # Filtros específicos - converter datas para formato brasileiro
            try:
                # Converter de YYYY-MM-DD para DD/MM/YYYY
                data_inicio_obj = datetime.strptime(data_inicio, '%Y-%m-%d')
                data_fim_obj = datetime.strptime(data_fim, '%Y-%m-%d')
                data_limite_inicio = data_inicio_obj.strftime('%d/%m/%Y')
                data_limite_fim = data_fim_obj.strftime('%d/%m/%Y')
                
                print(f"[MATERIAIS API] Período específico: {data_limite_inicio} até {data_limite_fim}")
                
                query = supabase.table('importacoes_processos_aberta').select(
                    'id, mercadoria, custo_total, valor_cif_real, valor_fob_real, '
                    'transit_time_real, data_abertura, cnpj_importador, importador, '
                    'modal, canal, status_processo'
                ).neq('status_processo', 'Despacho Cancelado').gte('data_abertura', data_limite_inicio).lte('data_abertura', data_limite_fim)
                
            except ValueError as e:
                print(f"[MATERIAIS API] Erro na conversão de datas: {e}")
                return jsonify({'error': 'Formato de data inválido'}), 400
        else:
            # Sem filtros específicos - usar lógica do dashboard (só data mínima)
            data_limite = (datetime.now() - timedelta(days=30)).strftime('%d/%m/%Y')
            print(f"[MATERIAIS API] Período padrão (últimos 30 dias): desde {data_limite}")
            
            query = supabase.table('importacoes_processos_aberta').select(
                'id, mercadoria, custo_total, valor_cif_real, valor_fob_real, '
                'transit_time_real, data_abertura, cnpj_importador, importador, '
                'modal, canal, status_processo'
            ).gte('data_abertura', data_limite).neq('status_processo', 'Despacho Cancelado')
        
        # Aplicar filtros de busca
        if material:
            query = query.ilike('mercadoria', f'%{material}%')
        
        if cliente:
            query = query.ilike('importador', f'%{cliente}%')
        
        if modal and modal != 'Todos':
            query = query.eq('modal', modal)
        
        # Aplicar filtros baseados no usuário
        if current_role == 'cliente_unique':
            if user_companies:
                query = query.in_('cnpj_importador', user_companies)
            else:
                # Cliente sem empresas - retornar dados vazios
                return jsonify({
                    'total_processos': 0,
                    'total_materiais': 0,
                    'valor_total': 0,
                    'custo_total': 0,
                    'ticket_medio': 0,
                    'transit_time_medio': 0
                })
        
        result = query.execute()
        processos = result.data or []
        
        print(f"[MATERIAIS API] Encontrados {len(processos)} processos")
        
        # Calcular KPIs
        kpis = calculate_materiais_kpis(processos)
        
        # Retornar KPIs diretamente
        return jsonify(kpis)
        
    except Exception as e:
        print(f"[MATERIAIS API] Erro: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'total_processos': 0,
            'total_materiais': 0,
            'valor_total': 0,
            'custo_total': 0,
            'ticket_medio': 0,
            'transit_time_medio': 0
        }), 500

def calculate_materiais_kpis(processos):
    """Calcular KPIs específicos de materiais"""
    try:
        total_processos = len(processos)
        
        # Materiais únicos (filtrar vazios e "não informado")
        materiais_unicos = set()
        valores_processos = []
        custos_processos = []
        transit_times = []
        
        for p in processos:
            # Material - verificar se não é None primeiro
            material = p.get('mercadoria')
            if material and isinstance(material, str):
                material = material.strip()
                if material and material.lower() not in ['', 'não informado', 'nao informado']:
                    # Limpar material usando o MaterialCleaner
                    material_info = material_cleaner.clean_material(material)
                    material_limpo = material_info['material_limpo']
                    
                    if material_limpo:
                        materiais_unicos.add(material_limpo)
            
            # Valores
            valor_cif = float(p.get('valor_cif_real') or 0)
            if valor_cif > 0:
                valores_processos.append(valor_cif)
            
            custo_total = float(p.get('custo_total') or 0)
            if custo_total > 0:
                custos_processos.append(custo_total)
            
            # Transit time
            transit_time = p.get('transit_time_real')
            if transit_time and transit_time != '' and float(transit_time) > 0:
                transit_times.append(float(transit_time))
        
        total_materiais = len(materiais_unicos)
        valor_total = sum(valores_processos)
        custo_total = sum(custos_processos)
        ticket_medio = valor_total / total_processos if total_processos > 0 else 0
        transit_time_medio = sum(transit_times) / len(transit_times) if transit_times else 0
        
        return {
            'total_processos': total_processos,
            'total_materiais': total_materiais,
            'valor_total': round(valor_total, 2),
            'custo_total': round(custo_total, 2),
            'ticket_medio': round(ticket_medio, 2),
            'transit_time_medio': round(transit_time_medio, 1)
        }
        
    except Exception as e:
        print(f"[MATERIAIS KPI] Erro: {str(e)}")
        return {
            'total_processos': 0,
            'total_materiais': 0,
            'valor_total': 0,
            'custo_total': 0,
            'ticket_medio': 0,
            'transit_time_medio': 0
        }

@bp.route('/filter-options/materiais')
@login_required  
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def filter_options_materiais():
    """API para obter lista de materiais únicos para filtros"""
    try:
        user_companies = []
        current_role = session['user']['role']
        
        if current_role == 'cliente_unique':
            user_companies = session['user'].get('user_companies', [])
        
        query = supabase.table('importacoes_processos_aberta').select('mercadoria').neq('status_processo', 'Despacho Cancelado')
        
        # Aplicar filtros baseados no usuário
        if current_role == 'cliente_unique':
            if user_companies:
                query = query.in_('cnpj_importador', user_companies)
            else:
                return jsonify([])
        
        response = query.execute()
        
        # Extrair materiais únicos, limpar e ordenar
        materiais_set = set()
        for item in response.data:
            mercadoria = item.get('mercadoria')
            if mercadoria and mercadoria.strip():
                # Limpar material usando o MaterialCleaner
                material_info = material_cleaner.clean_material(mercadoria)
                material_limpo = material_info['material_limpo']
                
                if material_limpo:
                    materiais_set.add(material_limpo)
        
        materiais_list = [{'mercadoria': m} for m in sorted(materiais_set)]
        
        print(f"[MATERIAIS FILTER] Encontrados {len(materiais_list)} materiais únicos")
        return jsonify(materiais_list)
        
    except Exception as e:
        print(f"[MATERIAIS FILTER] Erro ao carregar materiais: {str(e)}")
        return jsonify([])

@bp.route('/filter-options/clientes')
@login_required  
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def filter_options_clientes():
    """API para obter lista de clientes únicos para filtros"""
    try:
        user_companies = []
        current_role = session['user']['role']
        
        if current_role == 'cliente_unique':
            user_companies = session['user'].get('user_companies', [])
        
        query = supabase.table('importacoes_processos_aberta').select('importador').neq('status_processo', 'Despacho Cancelado')
        
        # Aplicar filtros baseados no usuário
        if current_role == 'cliente_unique':
            if user_companies:
                query = query.in_('cnpj_importador', user_companies)
            else:
                return jsonify([])
        
        response = query.execute()
        
        # Extrair clientes únicos e ordenar
        clientes_set = set()
        for item in response.data:
            importador = item.get('importador')
            if importador and importador.strip():
                clientes_set.add(importador.strip())
        
        clientes_list = [{'importador': c} for c in sorted(clientes_set)]
        
        print(f"[MATERIAIS FILTER] Encontrados {len(clientes_list)} clientes únicos")
        return jsonify(clientes_list)
        
    except Exception as e:
        print(f"[MATERIAIS FILTER] Erro ao carregar clientes: {str(e)}")
        return jsonify([])
