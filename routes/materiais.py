from flask import Blueprint, render_template, session, request, jsonify
from datetime import datetime, timedelta
import traceback
from extensions import supabase


from services.data_cache import DataCacheService
from material_cleaner import MaterialCleaner
from routes.auth import login_required, role_required

# Initialize services
data_cache = DataCacheService()
material_cleaner = MaterialCleaner()

bp = Blueprint('materiais', __name__, url_prefix='/materiais')

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
    except:
        return False

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
    """API para obter dados dos materiais (KPIs e gráficos) - usando cache"""
    try:
        print("[MATERIAIS API] Iniciando busca de dados no cache server-side")
        # Recuperar cache server-side pelo user_id
        user_id = session.get('user', {}).get('id')
        cached_data = data_cache.get_cache(user_id, 'raw_data')
        print(f"[MATERIAIS API] Cache server-side retornado: {type(cached_data)}")

        # Fallback vazio se cache não existir
        if not cached_data:
            print("[MATERIAIS API] Cache server-side vazio ou expirado")
            return jsonify({
                'total_processos': 0,
                'total_materiais': 0,
                'valor_total': 0,
                'custo_total': 0,
                'ticket_medio': 0,
                'transit_time_medio': 0
            })
        
        # Obter parâmetros de filtro da requisição
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        material = request.args.get('material')
        cliente = request.args.get('cliente')
        modal = request.args.get('modal')
        force_refresh = request.args.get('refresh', 'false').lower() == 'true'
        
        print(f"[MATERIAIS API] Filtros recebidos - Início: {data_inicio}, Fim: {data_fim}, Material: {material}, Cliente: {cliente}, Modal: {modal}, Refresh: {force_refresh}")
        
        # Usar os dados brutos do cache da sessão (mesmo que o dashboard)
        raw_data = cached_data
        
        if not raw_data or not isinstance(raw_data, list):
            print(f"[MATERIAIS API] Dados brutos inválidos no cache: {type(raw_data)}")
            return jsonify({
                'total_processos': 0,
                'total_materiais': 0,
                'valor_total': 0,
                'custo_total': 0,
                'ticket_medio': 0,
                'transit_time_medio': 0
            })
        
        print(f"[MATERIAIS API] Dados do cache carregados: {len(raw_data)} registros")
        
        # Se não há filtros de data específicos, aplicar filtro de 30 dias (igual ao dashboard)
        if not data_inicio and not data_fim:
            # Usar mesma lógica do dashboard: últimos 30 dias
            data_limite = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            data_inicio = data_limite
            data_fim = datetime.now().strftime('%Y-%m-%d')
            print(f"[MATERIAIS API] Aplicando filtro padrão (30 dias): {data_inicio} a {data_fim}")
        
        # Aplicar filtros em Python nos dados do cache
        filtered_data = []
        for item in raw_data:
            # Filtrar apenas registros com material
            if not item.get('mercadoria') or not item.get('mercadoria').strip():
                continue
                
            # Filtrar por modal se especificado
            if modal and modal != 'Todos':
                if item.get('modal') != modal:
                    continue
                    
            # Filtrar por cliente se especificado
            if cliente:
                importador = item.get('importador', '')
                if cliente.lower() not in importador.lower():
                    continue
            
            # Filtrar por material se especificado
            if material:
                # Busca inteligente - mapear categoria para busca por palavra-chave
                material_upper = material.upper()
                busca_aplicada = False
                
                # Verificar se o termo de busca corresponde a uma categoria
                for categoria, keywords in material_cleaner.category_mappings.items():
                    if categoria in material_upper or any(keyword in material_upper for keyword in keywords):
                        # Verificar se o material do item contém algum keyword da categoria
                        mercadoria = item.get('mercadoria', '').upper()
                        if any(keyword in mercadoria for keyword in keywords):
                            busca_aplicada = True
                            break
                
                if not busca_aplicada:
                    # Busca normal no texto original
                    mercadoria = item.get('mercadoria', '')
                    if material.lower() not in mercadoria.lower():
                        continue
            
            # Aplicar filtro de data em Python para maior precisão
            if data_inicio and data_fim:
                item_date = item.get('data_abertura', '')
                if not filter_by_date_python(item_date, data_inicio, data_fim):
                    continue
            
            filtered_data.append(item)
        
        print(f"[MATERIAIS API] Dados após filtros: {len(filtered_data)} registros")
        
        # Calcular KPIs
        kpis = calculate_materiais_kpis(filtered_data)
        
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
    """API para obter lista de materiais únicos para filtros - usando cache"""
    try:
        print("[MATERIAIS FILTER] Carregando materiais do cache")
        
        # Verificar se os dados estão no cache da sessão
        cached_data = session.get('cached_data')
        if not cached_data:
            print("[MATERIAIS FILTER] Cache não encontrado na sessão")
            return jsonify([])
        
        # Usar os dados brutos do cache da sessão
        raw_data = cached_data
        
        if not raw_data or not isinstance(raw_data, list):
            print("[MATERIAIS FILTER] Dados brutos inválidos no cache")
            return jsonify([])
        
        # Extrair materiais únicos, limpar e ordenar
        materiais_set = set()
        for item in raw_data:
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
    """API para obter lista de clientes únicos para filtros - usando cache"""
    try:
        print("[MATERIAIS FILTER] Carregando clientes do cache")
        
        # Verificar se os dados estão no cache da sessão
        cached_data = session.get('cached_data')
        if not cached_data:
            print("[MATERIAIS FILTER] Cache não encontrado na sessão")
            return jsonify([])
        
        # Usar os dados brutos do cache da sessão
        raw_data = cached_data
        
        if not raw_data or not isinstance(raw_data, list):
            print("[MATERIAIS FILTER] Dados brutos inválidos no cache")
            return jsonify([])
        
        # Extrair clientes únicos e ordenar
        clientes_set = set()
        for item in raw_data:
            importador = item.get('importador')
            if importador and importador.strip():
                clientes_set.add(importador.strip())
        
        clientes_list = [{'importador': c} for c in sorted(clientes_set)]
        
        print(f"[MATERIAIS FILTER] Encontrados {len(clientes_list)} clientes únicos")
        return jsonify(clientes_list)
        
    except Exception as e:
        print(f"[MATERIAIS FILTER] Erro ao carregar clientes: {str(e)}")
        return jsonify([])
