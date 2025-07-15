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
    except Exception as e:
        print(f"[MATERIAIS] Erro ao filtrar data: {str(e)}")
        return False

@bp.route('/')
@login_required
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def index():
    """Página principal de materiais - nova versão"""
    return render_template('materiais/materiais.html')

@bp.route('/materiais_data')
@login_required  
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def materiais_data():
    """API para obter dados dos materiais (KPIs e gráficos) - usando cache"""
    try:
        print("[MATERIAIS API] Iniciando busca de dados nos caches")
        
        # Verificar se é um teste
        is_test = request.args.get('test_mode') == 'true'
        
        if is_test:
            # Modo teste - carrega dados diretamente
            from extensions import supabase
            response = supabase.table('importacoes_processos').select('*').limit(200).execute()
            cached_data = response.data if response.data else []
            print(f"[MATERIAIS API] Modo teste: {len(cached_data)} registros carregados")
        else:
            # Modo normal - busca do cache
            # Tentar obter dados do cache server-side primeiro
            user_id = session.get('user', {}).get('id')
            cached_data = None
            
            if user_id:
                cached_data = data_cache.get_cache(user_id, 'raw_data')
            
            # Fallback para cache da sessão
            if not cached_data:
                cached_data = session.get('cached_data', [])
                
            # Se ainda não há dados, retornar vazio
            if not cached_data:
                print("[MATERIAIS API] Nenhum cache encontrado")
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
        
        # Usar os dados brutos do cache
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
            if not item.get('resumo_mercadoria') or not item.get('resumo_mercadoria').strip():
                continue
                
            # Filtrar por modal se especificado
            if modal and modal != 'Todos':
                if item.get('via_transporte_descricao') != modal:
                    continue
                    
            # Filtrar por cliente se especificado
            if cliente:
                importador = item.get('cliente_razaosocial', '')
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
                        mercadoria = item.get('resumo_mercadoria', '').upper()
                        if any(keyword in mercadoria for keyword in keywords):
                            busca_aplicada = True
                            break
                
                if not busca_aplicada:
                    # Busca normal no texto original
                    mercadoria = item.get('resumo_mercadoria', '')
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
            material = p.get('resumo_mercadoria')  # Campo correto
            if material and isinstance(material, str):
                material = material.strip()
                if material and material.lower() not in ['', 'não informado', 'nao informado']:
                    # Limpar material usando o MaterialCleaner
                    material_info = material_cleaner.clean_material(material)
                    material_limpo = material_info['material_limpo']
                    
                    if material_limpo:
                        materiais_unicos.add(material_limpo)
            
            # Valores usando campos corretos
            valor_cif = float(p.get('total_vmle_real') or 0)
            if valor_cif > 0:
                valores_processos.append(valor_cif)
            
            custo_total = float(p.get('total_vmcv_real') or 0)
            if custo_total > 0:
                custos_processos.append(custo_total)
            
            # Transit time - campo não disponível, usar 0
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


@bp.route('/api/top-materiais')
@login_required
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def api_top_materiais():
    """API para obter top 10 materiais por quantidade"""
    try:
        # Obter dados do cache - mesma lógica da função anterior
        user_id = session.get('user', {}).get('id')
        cached_data = None
        
        if user_id:
            cached_data = data_cache.get_cache(user_id, 'raw_data')
        
        if not cached_data:
            cached_data = session.get('cached_data', [])
            
        if not cached_data:
            return jsonify([])
        
        # Aplicar filtros
        filtered_data = apply_filters(cached_data)
        
        # Agrupar por material e contar
        material_counts = {}
        for item in filtered_data:
            material = item.get('resumo_mercadoria')  # Campo correto
            if material and material.strip():
                material_info = material_cleaner.clean_material(material)
                material_limpo = material_info.get('material_limpo', material)
                
                if material_limpo not in material_counts:
                    material_counts[material_limpo] = 0
                material_counts[material_limpo] += 1
        
        # Ordenar e pegar top 10
        top_materiais = sorted(material_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return jsonify([{
            'material': material,
            'qtde_processos': count
        } for material, count in top_materiais])
        
    except Exception as e:
        print(f"[API TOP MATERIAIS] Erro: {str(e)}")
        return jsonify([])


@bp.route('/api/evolucao-mensal')
@login_required
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def api_evolucao_mensal():
    """API para obter evolução mensal dos top 3 materiais"""
    try:
        # Obter dados do cache - mesma lógica da função anterior
        user_id = session.get('user', {}).get('id')
        cached_data = None
        
        if user_id:
            cached_data = data_cache.get_cache(user_id, 'raw_data')
        
        if not cached_data:
            cached_data = session.get('cached_data', [])
            
        if not cached_data:
            return jsonify([])
        
        # Aplicar filtros
        filtered_data = apply_filters(cached_data)
        
        # Primeiro, obter os top 3 materiais
        material_counts = {}
        for item in filtered_data:
            material = item.get('resumo_mercadoria')  # Campo correto
            if material and material.strip():
                material_info = material_cleaner.clean_material(material)
                material_limpo = material_info.get('material_limpo', material)
                
                if material_limpo not in material_counts:
                    material_counts[material_limpo] = 0
                material_counts[material_limpo] += 1
        
        top_3_materiais = [material for material, count in sorted(material_counts.items(), key=lambda x: x[1], reverse=True)[:3]]
        
        # Agrupar por mês e material
        monthly_data = {}
        for item in filtered_data:
            try:
                data_abertura = item.get('data_abertura')
                if not data_abertura:
                    continue
                    
                # Converter data ISO para datetime
                if 'T' in data_abertura:
                    date_obj = datetime.strptime(data_abertura[:10], '%Y-%m-%d')
                elif '/' in data_abertura:
                    day, month, year = data_abertura.split('/')
                    date_obj = datetime(int(year), int(month), int(day))
                else:
                    date_obj = datetime.strptime(data_abertura, '%Y-%m-%d')
                
                month_key = date_obj.strftime('%Y-%m')
                
                material = item.get('resumo_mercadoria')  # Campo correto
                if material and material.strip():
                    material_info = material_cleaner.clean_material(material)
                    material_limpo = material_info.get('material_limpo', material)
                    
                    if material_limpo in top_3_materiais:
                        if month_key not in monthly_data:
                            monthly_data[month_key] = {}
                        
                        if material_limpo not in monthly_data[month_key]:
                            monthly_data[month_key][material_limpo] = 0
                        monthly_data[month_key][material_limpo] += 1
                        
            except Exception as e:
                continue
        
        # Converter para formato do Chart.js
        result = []
        for month, materials in sorted(monthly_data.items()):
            month_obj = datetime.strptime(month, '%Y-%m')
            month_str = month_obj.strftime('%m/%Y')
            
            for material, count in materials.items():
                result.append({
                    'mes': month_str,
                    'categoria_material': material,
                    'qtde': count
                })
        
        return jsonify(result)
        
    except Exception as e:
        print(f"[API EVOLUÇÃO MENSAL] Erro: {str(e)}")
        return jsonify([])


@bp.route('/api/modal-distribution')
@login_required
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def api_modal_distribution():
    """API para obter distribuição por modal"""
    try:
        # Obter dados do cache - mesma lógica da função anterior
        user_id = session.get('user', {}).get('id')
        cached_data = None
        
        if user_id:
            cached_data = data_cache.get_cache(user_id, 'raw_data')
        
        if not cached_data:
            cached_data = session.get('cached_data', [])
            
        if not cached_data:
            return jsonify([])
        
        # Aplicar filtros
        filtered_data = apply_filters(cached_data)
        
        # Agrupar por modal
        modal_counts = {}
        for item in filtered_data:
            modal = item.get('via_transporte_descricao', 'Não Informado')  # Campo correto
            if not modal or modal.strip() == '':
                modal = 'Não Informado'
            
            if modal not in modal_counts:
                modal_counts[modal] = 0
            modal_counts[modal] += 1
        
        return jsonify([{
            'modal': modal,
            'total': count
        } for modal, count in modal_counts.items()])
        
    except Exception as e:
        print(f"[API MODAL DISTRIBUTION] Erro: {str(e)}")
        return jsonify([])


@bp.route('/api/canal-distribution')
@login_required
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def api_canal_distribution():
    """API para obter distribuição por canal"""
    try:
        # Obter dados do cache - mesma lógica da função anterior
        user_id = session.get('user', {}).get('id')
        cached_data = None
        
        if user_id:
            cached_data = data_cache.get_cache(user_id, 'raw_data')
        
        if not cached_data:
            cached_data = session.get('cached_data', [])
            
        if not cached_data:
            return jsonify([])
        
        # Aplicar filtros
        filtered_data = apply_filters(cached_data)
        
        # Agrupar por canal
        canal_counts = {}
        for item in filtered_data:
            canal = item.get('diduimp_canal', 'Não Informado')  # Campo correto
            if not canal or canal.strip() == '':
                canal = 'Não Informado'
            
            if canal not in canal_counts:
                canal_counts[canal] = 0
            canal_counts[canal] += 1
        
        return jsonify([{
            'canal': canal,
            'total': count
        } for canal, count in canal_counts.items()])
        
    except Exception as e:
        print(f"[API CANAL DISTRIBUTION] Erro: {str(e)}")
        return jsonify([])


@bp.route('/api/transit-time-por-material')
@login_required
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def api_transit_time_por_material():
    """API para obter tempo de trânsito por material"""
    try:
        # Obter dados do cache - mesma lógica da função anterior
        user_id = session.get('user', {}).get('id')
        cached_data = None
        
        if user_id:
            cached_data = data_cache.get_cache(user_id, 'raw_data')
        
        if not cached_data:
            cached_data = session.get('cached_data', [])
            
        if not cached_data:
            return jsonify([])
        
        # Aplicar filtros
        filtered_data = apply_filters(cached_data)
        
        # Agrupar por material e calcular médias
        material_transit = {}
        for item in filtered_data:
            material = item.get('mercadoria')
            transit_time = item.get('transit_time_real')
            
            if material and material.strip() and transit_time:
                try:
                    transit_time_float = float(transit_time)
                    if transit_time_float > 0:
                        material_info = material_cleaner.clean_material(material)
                        material_limpo = material_info.get('material_limpo', material)
                        
                        if material_limpo not in material_transit:
                            material_transit[material_limpo] = []
                        material_transit[material_limpo].append(transit_time_float)
                except ValueError:
                    continue
        
        # Calcular média e pegar top 10
        result = []
        for material, times in material_transit.items():
            if times:
                avg_time = sum(times) / len(times)
                result.append({
                    'categoria_material': material,
                    'transit_time_medio': round(avg_time, 1)
                })
        
        # Ordenar por tempo médio (decrescente) e pegar top 10
        result.sort(key=lambda x: x['transit_time_medio'], reverse=True)
        return jsonify(result[:10])
        
    except Exception as e:
        print(f"[API TRANSIT TIME] Erro: {str(e)}")
        return jsonify([])


@bp.route('/api/principais-materiais')
@login_required
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def api_principais_materiais():
    """API para obter principais materiais com detalhes"""
    try:
        # Obter dados do cache - mesma lógica da função anterior
        user_id = session.get('user', {}).get('id')
        cached_data = None
        
        if user_id:
            cached_data = data_cache.get_cache(user_id, 'raw_data')
        
        if not cached_data:
            cached_data = session.get('cached_data', [])
            
        if not cached_data:
            return jsonify([])
        
        # Aplicar filtros
        filtered_data = apply_filters(cached_data)
        
        # Agrupar por material
        material_stats = {}
        for item in filtered_data:
            material = item.get('mercadoria')
            if material and material.strip():
                material_info = material_cleaner.clean_material(material)
                material_limpo = material_info.get('material_limpo', material)
                
                if material_limpo not in material_stats:
                    material_stats[material_limpo] = {
                        'qtde_processos': 0,
                        'custo_total': 0,
                        'proximas_chegadas': []
                    }
                
                material_stats[material_limpo]['qtde_processos'] += 1
                
                # Custo total
                custo = item.get('custo_total', 0)
                try:
                    material_stats[material_limpo]['custo_total'] += float(custo) if custo else 0
                except:
                    pass
                
                # Próximas chegadas
                data_chegada = item.get('data_chegada')
                if data_chegada and data_chegada.strip():
                    try:
                        if '/' in data_chegada:
                            day, month, year = data_chegada.split('/')
                            date_obj = datetime(int(year), int(month), int(day))
                        else:
                            date_obj = datetime.strptime(data_chegada, '%Y-%m-%d')
                        
                        if date_obj >= datetime.now():
                            material_stats[material_limpo]['proximas_chegadas'].append(date_obj)
                    except:
                        pass
        
        # Converter para formato da API
        result = []
        for material, stats in material_stats.items():
            proxima_chegada = None
            if stats['proximas_chegadas']:
                proxima_chegada = min(stats['proximas_chegadas']).strftime('%d/%m/%Y')
            
            result.append({
                'material': material,
                'qtde_processos': stats['qtde_processos'],
                'custo_total': round(stats['custo_total'], 2),
                'proxima_chegada': proxima_chegada
            })
        
        # Ordenar por quantidade de processos
        result.sort(key=lambda x: x['qtde_processos'], reverse=True)
        return jsonify(result[:10])
        
    except Exception as e:
        print(f"[API PRINCIPAIS MATERIAIS] Erro: {str(e)}")
        return jsonify([])


@bp.route('/api/detalhamento-processos')
@login_required
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def api_detalhamento_processos():
    """API para obter detalhamento dos processos"""
    try:
        # Obter dados do cache - mesma lógica da função anterior
        user_id = session.get('user', {}).get('id')
        cached_data = None
        
        if user_id:
            cached_data = data_cache.get_cache(user_id, 'raw_data')
        
        if not cached_data:
            cached_data = session.get('cached_data', [])
            
        if not cached_data:
            return jsonify([])
        
        # Aplicar filtros
        filtered_data = apply_filters(cached_data)
        
        # Converter para formato da tabela
        result = []
        for item in filtered_data:
            # Limpar material
            material = item.get('mercadoria', '')
            if material:
                material_info = material_cleaner.clean_material(material)
                material = material_info.get('material_limpo', material)
            
            result.append({
                'data_abertura': item.get('data_abertura', ''),
                'numero_pedido': item.get('ref_unique', ''),
                'cliente': item.get('importador', ''),
                'material': material,
                'data_embarque': item.get('data_embarque', ''),
                'data_chegada': item.get('data_chegada', ''),
                'status_carga': item.get('status_processo', ''),
                'canal': item.get('canal', ''),
                'custo_total': round(float(item.get('custo_total', 0)), 2) if item.get('custo_total') else 0
            })
        
        return jsonify(result)
        
    except Exception as e:
        print(f"[API DETALHAMENTO] Erro: {str(e)}")
        return jsonify([])


def apply_filters(data):
    """Aplicar filtros aos dados baseado nos parâmetros da requisição"""
    try:
        # Obter parâmetros de filtro
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        material = request.args.get('material')
        cliente = request.args.get('cliente')
        modal = request.args.get('modal')
        
        # Se não há filtros de data específicos, aplicar filtro de 30 dias
        if not data_inicio and not data_fim:
            data_limite = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            data_inicio = data_limite
            data_fim = datetime.now().strftime('%Y-%m-%d')
        
        filtered_data = []
        for item in data:
            # Filtrar apenas registros com material
            if not item.get('resumo_mercadoria') or not item.get('resumo_mercadoria').strip():
                continue
            
            # Filtrar por modal se especificado
            if modal and modal != 'Todos':
                if item.get('via_transporte_descricao') != modal:
                    continue
            
            # Filtrar por cliente se especificado
            if cliente:
                importador = item.get('cliente_razaosocial', '')
                if cliente.lower() not in importador.lower():
                    continue
            
            # Filtrar por material se especificado
            if material:
                material_upper = material.upper()
                busca_aplicada = False
                
                # Verificar se o termo de busca corresponde a uma categoria
                for categoria, keywords in material_cleaner.category_mappings.items():
                    if categoria in material_upper or any(keyword in material_upper for keyword in keywords):
                        # Verificar se o material do item contém algum keyword da categoria
                        mercadoria = item.get('resumo_mercadoria', '').upper()
                        if any(keyword in mercadoria for keyword in keywords):
                            busca_aplicada = True
                            break
                
                if not busca_aplicada:
                    # Busca normal no texto original
                    mercadoria = item.get('resumo_mercadoria', '')
                    if material.lower() not in mercadoria.lower():
                        continue
            
            # Aplicar filtro de data
            if data_inicio and data_fim:
                item_date = item.get('data_abertura', '')
                if not filter_by_date_python(item_date, data_inicio, data_fim):
                    continue
            
            filtered_data.append(item)
        
        return filtered_data
        
    except Exception as e:
        print(f"[APPLY FILTERS] Erro: {str(e)}")
        return data

@bp.route('/test-cache')
def test_cache():
    """Endpoint de teste para verificar cache - sem autenticação"""
    try:
        # Testar cache com user_id fixo (Lucas)
        test_user_id = "379966ab-6d30-4bbe-a31c-e9fa2232ca5f"
        
        # Testar cache server-side
        cached_data = data_cache.get_cache(test_user_id, 'raw_data')
        cache_info = {
            'has_server_cache': bool(cached_data),
            'server_cache_count': len(cached_data) if cached_data else 0,
            'server_cache_sample': cached_data[:2] if cached_data else None
        }
        
        return jsonify({
            'status': 'success',
            'cache_info': cache_info
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        })

@bp.route('/test-no-auth')
def test_no_auth():
    """Endpoint de teste sem autenticação"""
    return jsonify({
        'status': 'success',
        'message': 'Endpoint funcionando sem autenticação'
    })

@bp.route('/test-direct-data')
def test_direct_data():
    """Endpoint de teste carregando dados diretamente da base"""
    try:
        from extensions import supabase_client
        
        # Buscar dados diretamente da base
        response = supabase_client.table('importacoes_processos').select('*').limit(5).execute()
        
        total_records = len(response.data) if response.data else 0
        
        return jsonify({
            'status': 'success',
            'total_records': total_records,
            'sample_data': response.data[:2] if response.data else None,
            'message': f'Dados carregados diretamente da base: {total_records} registros'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        })

@bp.route('/test-load-cache')
def test_load_cache():
    """Endpoint de teste para carregar dados no cache"""
    try:
        from extensions import supabase_client
        
        # Buscar dados da base (limitando a 100 para teste)
        response = supabase_client.table('importacoes_processos').select('*').limit(100).execute()
        
        if response.data:
            # Colocar dados no cache
            test_user_id = "379966ab-6d30-4bbe-a31c-e9fa2232ca5f"
            data_cache.set_cache(test_user_id, 'raw_data', response.data)
            
            return jsonify({
                'status': 'success',
                'message': f'Cache carregado com {len(response.data)} registros',
                'total_records': len(response.data)
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Nenhum dado encontrado na base'
            })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        })

@bp.route('/test-full-materiais-bypass')
def test_full_materiais_bypass():
    """Endpoint de teste completo que simula usuário logado e testa todas as APIs"""
    try:
        from extensions import supabase_client
        
        # 1. Carregar dados da base
        print("[TEST] Carregando dados da base...")
        response = supabase_client.table('importacoes_processos').select('*').limit(500).execute()
        
        if not response.data:
            return jsonify({
                'status': 'error',
                'message': 'Nenhum dado encontrado na base'
            })
        
        # 2. Simular cache carregado
        test_user_id = "379966ab-6d30-4bbe-a31c-e9fa2232ca5f"
        data_cache.set_cache(test_user_id, 'raw_data', response.data)
        
        # 3. Simular sessão de usuário logado
        session['user'] = {
            'id': test_user_id,
            'name': 'Teste Usuario',
            'role': 'admin'
        }
        session['cached_data'] = response.data
        
        # 4. Testar todas as APIs
        results = {}
        
        # Testar materiais_data
        try:
            cached_data = response.data
            total_processos = len(cached_data)
            total_materiais = len(set(item.get('mercadoria', '') for item in cached_data if item.get('mercadoria')))
            
            results['materiais_data'] = {
                'total_processos': total_processos,
                'total_materiais': total_materiais,
                'status': 'success'
            }
        except Exception as e:
            results['materiais_data'] = {'status': 'error', 'error': str(e)}
        
        # Testar top-materiais
        try:
            material_counts = {}
            for item in cached_data:
                material = item.get('mercadoria')
                if material and material.strip():
                    material_info = material_cleaner.clean_material(material)
                    material_limpo = material_info.get('material_limpo', material)
                    material_counts[material_limpo] = material_counts.get(material_limpo, 0) + 1
            
            top_materiais = sorted(material_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            results['top_materiais'] = {
                'data': [{'material': m[0], 'count': m[1]} for m in top_materiais],
                'status': 'success'
            }
        except Exception as e:
            results['top_materiais'] = {'status': 'error', 'error': str(e)}
        
        # Testar evolução mensal
        try:
            from datetime import datetime
            monthly_data = {}
            for item in cached_data:
                data_str = item.get('data_abertura', '')
                if data_str:
                    try:
                        # Tentar formato brasileiro DD/MM/YYYY
                        if '/' in data_str:
                            data_obj = datetime.strptime(data_str, '%d/%m/%Y')
                        else:
                            data_obj = datetime.strptime(data_str, '%Y-%m-%d')
                        
                        mes_ano = data_obj.strftime('%Y-%m')
                        if mes_ano not in monthly_data:
                            monthly_data[mes_ano] = 0
                        monthly_data[mes_ano] += 1
                    except:
                        continue
            
            evolucao = [{'mes': k, 'count': v} for k, v in sorted(monthly_data.items())]
            results['evolucao_mensal'] = {
                'data': evolucao,
                'status': 'success'
            }
        except Exception as e:
            results['evolucao_mensal'] = {'status': 'error', 'error': str(e)}
        
        # Testar modal distribution
        try:
            modal_counts = {}
            for item in cached_data:
                modal = item.get('modal', 'Não Informado')
                if not modal or modal.strip() == '':
                    modal = 'Não Informado'
                modal_counts[modal] = modal_counts.get(modal, 0) + 1
            
            modal_data = [{'modal': k, 'count': v} for k, v in modal_counts.items()]
            results['modal_distribution'] = {
                'data': modal_data,
                'status': 'success'
            }
        except Exception as e:
            results['modal_distribution'] = {'status': 'error', 'error': str(e)}
        
        # Testar canal distribution
        try:
            canal_counts = {}
            for item in cached_data:
                canal = item.get('canal', 'Não Informado')
                if not canal or canal.strip() == '':
                    canal = 'Não Informado'
                canal_counts[canal] = canal_counts.get(canal, 0) + 1
            
            canal_data = [{'canal': k, 'count': v} for k, v in canal_counts.items()]
            results['canal_distribution'] = {
                'data': canal_data,
                'status': 'success'
            }
        except Exception as e:
            results['canal_distribution'] = {'status': 'error', 'error': str(e)}
        
        return jsonify({
            'status': 'success',
            'message': f'Teste completo executado com {len(cached_data)} registros',
            'total_records': len(cached_data),
            'results': results
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        })

@bp.route('/debug-materiais-data')
def debug_materiais_data():
    """Debug endpoint para materiais_data sem autenticação"""
    try:
        from extensions import supabase
        
        # Carregar dados da base
        response = supabase.table('importacoes_processos').select('*').limit(100).execute()
        
        if not response.data:
            return jsonify({
                'total_processos': 0,
                'total_materiais': 0,
                'valor_total': 0,
                'custo_total': 0,
                'ticket_medio': 0,
                'transit_time_medio': 0,
                'debug': 'Nenhum dado encontrado na base'
            })
        
        cached_data = response.data
        
        # Calcular KPIs
        total_processos = len(cached_data)
        
        # Contar materiais únicos
        materiais_set = set()
        for item in cached_data:
            material = item.get('resumo_mercadoria')  # Campo correto
            if material and material.strip():
                material_info = material_cleaner.clean_material(material)
                material_limpo = material_info.get('material_limpo', material)
                materiais_set.add(material_limpo)
        
        total_materiais = len(materiais_set)
        
        # Calcular valores usando campos corretos
        valor_total = sum(float(item.get('total_vmle_real', 0) or 0) for item in cached_data)
        custo_total = sum(float(item.get('total_vmcv_real', 0) or 0) for item in cached_data)
        ticket_medio = valor_total / total_processos if total_processos > 0 else 0
        
        # Calcular transit time médio
        transit_times = []
        for item in cached_data:
            transit_time = item.get('transit_time')
            if transit_time and str(transit_time).replace('.', '').isdigit():
                transit_times.append(float(transit_time))
        
        transit_time_medio = sum(transit_times) / len(transit_times) if transit_times else 0
        
        return jsonify({
            'total_processos': total_processos,
            'total_materiais': total_materiais,
            'valor_total': valor_total,
            'custo_total': custo_total,
            'ticket_medio': ticket_medio,
            'transit_time_medio': transit_time_medio,
            'debug': f'Dados carregados: {len(cached_data)} registros'
        })
        
    except Exception as e:
        return jsonify({
            'total_processos': 0,
            'total_materiais': 0,
            'valor_total': 0,
            'custo_total': 0,
            'ticket_medio': 0,
            'transit_time_medio': 0,
            'debug': f'Erro: {str(e)}'
        })

@bp.route('/debug-top-materiais')
def debug_top_materiais():
    """Debug endpoint para top materiais sem autenticação"""
    try:
        from extensions import supabase
        
        # Carregar dados da base
        response = supabase.table('importacoes_processos').select('*').limit(100).execute()
        
        if not response.data:
            return jsonify([])
        
        cached_data = response.data
        
        # Agrupar por material e contar
        material_counts = {}
        for item in cached_data:
            material = item.get('resumo_mercadoria')  # Campo correto
            if material and material.strip():
                material_info = material_cleaner.clean_material(material)
                material_limpo = material_info.get('material_limpo', material)
                
                if material_limpo not in material_counts:
                    material_counts[material_limpo] = 0
                material_counts[material_limpo] += 1
        
        # Ordenar por quantidade e pegar top 10
        top_materiais = sorted(material_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        result = []
        for material, count in top_materiais:
            result.append({
                'material': material,
                'count': count
            })
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify([])

@bp.route('/debug-evolucao-mensal')
def debug_evolucao_mensal():
    """Debug endpoint para evolução mensal sem autenticação"""
    try:
        from extensions import supabase
        from datetime import datetime
        
        # Carregar dados da base
        response = supabase.table('importacoes_processos').select('*').limit(100).execute()
        
        if not response.data:
            return jsonify([])
        
        cached_data = response.data
        
        # Primeiro, obter os top 3 materiais
        material_counts = {}
        for item in cached_data:
            material = item.get('resumo_mercadoria')  # Campo correto
            if material and material.strip():
                material_info = material_cleaner.clean_material(material)
                material_limpo = material_info.get('material_limpo', material)
                material_counts[material_limpo] = material_counts.get(material_limpo, 0) + 1
        
        top_3_materiais = sorted(material_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        top_3_names = [m[0] for m in top_3_materiais]
        
        # Evolução mensal dos top 3
        monthly_evolution = {}
        for item in cached_data:
            material = item.get('resumo_mercadoria')  # Campo correto
            if material and material.strip():
                material_info = material_cleaner.clean_material(material)
                material_limpo = material_info.get('material_limpo', material)
                
                if material_limpo in top_3_names:
                    data_str = item.get('data_abertura', '')
                    if data_str:
                        try:
                            # Tentar formato ISO primeiro
                            if 'T' in data_str:
                                data_obj = datetime.strptime(data_str[:10], '%Y-%m-%d')
                            elif '/' in data_str:
                                data_obj = datetime.strptime(data_str, '%d/%m/%Y')
                            else:
                                data_obj = datetime.strptime(data_str, '%Y-%m-%d')
                            
                            mes_ano = data_obj.strftime('%Y-%m')
                            
                            if mes_ano not in monthly_evolution:
                                monthly_evolution[mes_ano] = {}
                            
                            if material_limpo not in monthly_evolution[mes_ano]:
                                monthly_evolution[mes_ano][material_limpo] = 0
                            
                            monthly_evolution[mes_ano][material_limpo] += 1
                        except:
                            continue
        
        # Converter para formato esperado pelo Chart.js
        result = []
        for mes in sorted(monthly_evolution.keys()):
            month_data = {'mes': mes}
            for material in top_3_names:
                month_data[material] = monthly_evolution[mes].get(material, 0)
            result.append(month_data)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify([])

@bp.route('/debug-modal-distribution')
def debug_modal_distribution():
    """Debug endpoint para distribuição modal sem autenticação"""
    try:
        from extensions import supabase
        
        # Carregar dados da base
        response = supabase.table('importacoes_processos').select('*').limit(100).execute()
        
        if not response.data:
            return jsonify([])
        
        cached_data = response.data
        
        # Agrupar por modal
        modal_counts = {}
        for item in cached_data:
            modal = item.get('via_transporte_descricao', 'Não Informado')  # Campo correto
            if not modal or modal.strip() == '':
                modal = 'Não Informado'
            
            if modal not in modal_counts:
                modal_counts[modal] = 0
            modal_counts[modal] += 1
        
        # Converter para formato esperado
        result = []
        for modal, count in modal_counts.items():
            result.append({
                'modal': modal,
                'count': count
            })
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify([])

@bp.route('/debug-canal-distribution')
def debug_canal_distribution():
    """Debug endpoint para distribuição canal sem autenticação"""
    try:
        from extensions import supabase
        
        # Carregar dados da base
        response = supabase.table('importacoes_processos').select('*').limit(100).execute()
        
        if not response.data:
            return jsonify([])
        
        cached_data = response.data
        
        # Agrupar por canal
        canal_counts = {}
        for item in cached_data:
            canal = item.get('diduimp_canal', 'Não Informado')  # Campo correto
            if not canal or canal.strip() == '':
                canal = 'Não Informado'
            
            if canal not in canal_counts:
                canal_counts[canal] = 0
            canal_counts[canal] += 1
        
        # Converter para formato esperado
        result = []
        for canal, count in canal_counts.items():
            result.append({
                'canal': canal,
                'count': count
            })
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify([])

@bp.route('/debug-table-structure')
def debug_table_structure():
    """Debug endpoint para ver estrutura da tabela e dados de exemplo"""
    try:
        from extensions import supabase
        
        # Carregar uma amostra de dados
        response = supabase.table('importacoes_processos').select('*').limit(3).execute()
        
        if not response.data:
            return jsonify({
                'status': 'error',
                'message': 'Nenhum dado encontrado'
            })
        
        # Pegar o primeiro registro para ver as colunas
        sample_record = response.data[0]
        
        # Mostrar todas as colunas e seus valores
        columns_info = {}
        for key, value in sample_record.items():
            columns_info[key] = {
                'type': type(value).__name__,
                'value': value,
                'is_empty': value is None or (isinstance(value, str) and value.strip() == '')
            }
        
        return jsonify({
            'status': 'success',
            'total_records': len(response.data),
            'columns_info': columns_info,
            'sample_data': response.data
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        })

@bp.route('/test-authenticated-apis')
def test_authenticated_apis():
    """Endpoint de teste que simula usuário logado e testa as APIs principais"""
    try:
        from extensions import supabase
        from flask import current_app as app
        
        # 1. Carregar dados da base
        print("[TEST AUTH] Carregando dados da base...")
        response = supabase.table('importacoes_processos').select('*').limit(200).execute()
        
        if not response.data:
            return jsonify({
                'status': 'error',
                'message': 'Nenhum dado encontrado na base'
            })
        
        # 2. Simular cache carregado
        test_user_id = "379966ab-6d30-4bbe-a31c-e9fa2232ca5f"
        data_cache.set_cache(test_user_id, 'raw_data', response.data)
        
        # 3. Simular sessão de usuário logado
        session['user'] = {
            'id': test_user_id,
            'name': 'Teste Usuario',
            'role': 'admin'
        }
        session['cached_data'] = response.data
        
        # 4. Testar as APIs principais fazendo requisições internas
        results = {
            'cache_loaded': True,
            'total_records': len(response.data),
            'user_logged': True,
            'apis_tested': {}
        }
        
        # Simular parâmetros de request para as APIs
        with app.test_request_context('/?refresh=false'):
            
            # Testar materiais_data
            try:
                kpis = calculate_materiais_kpis(response.data)
                results['apis_tested']['materiais_data'] = {
                    'status': 'success',
                    'data': kpis
                }
            except Exception as e:
                results['apis_tested']['materiais_data'] = {
                    'status': 'error',
                    'error': str(e)
                }
            
            # Testar top materiais
            try:
                # Simular apply_filters sem request
                filtered_data = []
                for item in response.data:
                    if item.get('resumo_mercadoria') and item.get('resumo_mercadoria').strip():
                        filtered_data.append(item)
                
                # Agrupar por material
                material_counts = {}
                for item in filtered_data:
                    material = item.get('resumo_mercadoria')
                    if material and material.strip():
                        material_info = material_cleaner.clean_material(material)
                        material_limpo = material_info.get('material_limpo', material)
                        
                        if material_limpo not in material_counts:
                            material_counts[material_limpo] = 0
                        material_counts[material_limpo] += 1
                
                top_materiais = sorted(material_counts.items(), key=lambda x: x[1], reverse=True)[:10]
                top_result = [{
                    'material': material,
                    'qtde_processos': count
                } for material, count in top_materiais]
                
                results['apis_tested']['top_materiais'] = {
                    'status': 'success',
                    'data': top_result
                }
            except Exception as e:
                results['apis_tested']['top_materiais'] = {
                    'status': 'error',
                    'error': str(e)
                }
            
            # Testar modal distribution
            try:
                modal_counts = {}
                for item in filtered_data:
                    modal = item.get('via_transporte_descricao', 'Não Informado')
                    if not modal or modal.strip() == '':
                        modal = 'Não Informado'
                    
                    if modal not in modal_counts:
                        modal_counts[modal] = 0
                    modal_counts[modal] += 1
                
                modal_result = [{
                    'modal': modal,
                    'total': count
                } for modal, count in modal_counts.items()]
                
                results['apis_tested']['modal_distribution'] = {
                    'status': 'success',
                    'data': modal_result
                }
            except Exception as e:
                results['apis_tested']['modal_distribution'] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        return jsonify(results)
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        })

# Endpoints de teste sem autenticação
def apply_filters_to_query(query, filters):
    """
    Aplica filtros dinamicamente na query SQL
    
    Args:
        query: Query inicial do Supabase
        filters: Dict com os filtros a serem aplicados
    
    Returns:
        Query com filtros aplicados
    """
    if not filters:
        return query
    
    # Filtro por data de abertura
    if filters.get('data_inicio'):
        query = query.gte('data_abertura', filters['data_inicio'])
    
    if filters.get('data_fim'):
        query = query.lte('data_abertura', filters['data_fim'])
    
    # Filtro por material/mercadoria
    if filters.get('material'):
        query = query.ilike('resumo_mercadoria', f"%{filters['material']}%")
    
    # Filtro por cliente/importador
    if filters.get('cliente'):
        query = query.ilike('cliente_razaosocial', f"%{filters['cliente']}%")
    
    # Filtro por modal de transporte
    if filters.get('modal'):
        query = query.eq('via_transporte_descricao', filters['modal'])
    
    # Filtro por canal
    if filters.get('canal'):
        query = query.eq('diduimp_canal', filters['canal'])
    
    # Filtro por valor mínimo
    if filters.get('valor_min'):
        try:
            valor_min = float(filters['valor_min'])
            query = query.gte('total_vmle_real', valor_min)
        except ValueError:
            pass
    
    # Filtro por valor máximo
    if filters.get('valor_max'):
        try:
            valor_max = float(filters['valor_max'])
            query = query.lte('total_vmle_real', valor_max)
        except ValueError:
            pass
    
    return query

@bp.route('/bypass-materiais-data')
def bypass_materiais_data():
    """API de materiais sem autenticação para teste - com suporte a filtros"""
    try:
        from extensions import supabase
        
        # Obter filtros da query string
        filters = {
            'data_inicio': request.args.get('data_inicio'),
            'data_fim': request.args.get('data_fim'),
            'material': request.args.get('material'),
            'cliente': request.args.get('cliente'),
            'modal': request.args.get('modal'),
            'canal': request.args.get('canal'),
            'valor_min': request.args.get('valor_min'),
            'valor_max': request.args.get('valor_max')
        }
        
        # Remover filtros vazios
        filters = {k: v for k, v in filters.items() if v and v.strip()}
        
        # Se não há filtros de data, usar últimos 30 dias
        if not filters.get('data_inicio') and not filters.get('data_fim'):
            from datetime import datetime, timedelta
            data_limite = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            filters['data_inicio'] = data_limite
        
        # Construir query com filtros
        query = supabase.table('importacoes_processos').select('*')
        query = apply_filters_to_query(query, filters)
        
        response = query.limit(500).execute()
        cached_data = response.data if response.data else []
        
        if not cached_data:
            return jsonify({
                'total_processos': 0,
                'total_materiais': 0,
                'valor_total': 0,
                'custo_total': 0,
                'ticket_medio': 0,
                'transit_time_medio': 0
            })
        
        # Calcular KPIs
        kpis = calculate_materiais_kpis(cached_data)
        return jsonify(kpis)
        
    except Exception as e:
        return jsonify({
            'total_processos': 0,
            'total_materiais': 0,
            'valor_total': 0,
            'custo_total': 0,
            'ticket_medio': 0,
            'transit_time_medio': 0
        })

@bp.route('/bypass-top-materiais')
def bypass_top_materiais():
    """API de top materiais sem autenticação para teste - com suporte a filtros"""
    try:
        from extensions import supabase
        
        # Obter filtros da query string
        filters = {
            'data_inicio': request.args.get('data_inicio'),
            'data_fim': request.args.get('data_fim'),
            'material': request.args.get('material'),
            'cliente': request.args.get('cliente'),
            'modal': request.args.get('modal'),
            'canal': request.args.get('canal'),
            'valor_min': request.args.get('valor_min'),
            'valor_max': request.args.get('valor_max')
        }
        
        # Remover filtros vazios
        filters = {k: v for k, v in filters.items() if v and v.strip()}
        
        # Se não há filtros de data, usar últimos 30 dias
        if not filters.get('data_inicio') and not filters.get('data_fim'):
            from datetime import datetime, timedelta
            data_limite = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            filters['data_inicio'] = data_limite
        
        # Construir query com filtros
        query = supabase.table('importacoes_processos').select('*')
        query = apply_filters_to_query(query, filters)
        
        response = query.limit(500).execute()
        cached_data = response.data if response.data else []
        
        if not cached_data:
            return jsonify([])
        
        # Filtrar dados com material
        filtered_data = []
        for item in cached_data:
            if item.get('resumo_mercadoria') and item.get('resumo_mercadoria').strip():
                filtered_data.append(item)
        
        # Agrupar por material e contar
        material_counts = {}
        for item in filtered_data:
            material = item.get('resumo_mercadoria')
            if material and material.strip():
                material_info = material_cleaner.clean_material(material)
                material_limpo = material_info.get('material_limpo', material)
                
                if material_limpo not in material_counts:
                    material_counts[material_limpo] = 0
                material_counts[material_limpo] += 1
        
        # Ordenar e pegar top 10
        top_materiais = sorted(material_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return jsonify([{
            'material': material,
            'qtde_processos': count
        } for material, count in top_materiais])
        
    except Exception as e:
        return jsonify([])

@bp.route('/bypass-evolucao-mensal')
def bypass_evolucao_mensal():
    """API de evolução mensal sem autenticação para teste - com suporte a filtros"""
    try:
        from extensions import supabase
        from datetime import datetime
        
        # Obter filtros da query string
        filters = {
            'data_inicio': request.args.get('data_inicio'),
            'data_fim': request.args.get('data_fim'),
            'material': request.args.get('material'),
            'cliente': request.args.get('cliente'),
            'modal': request.args.get('modal'),
            'canal': request.args.get('canal'),
            'valor_min': request.args.get('valor_min'),
            'valor_max': request.args.get('valor_max')
        }
        
        # Remover filtros vazios
        filters = {k: v for k, v in filters.items() if v and v.strip()}
        
        # Se não há filtros de data, usar últimos 30 dias
        if not filters.get('data_inicio') and not filters.get('data_fim'):
            data_limite = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            filters['data_inicio'] = data_limite
        
        # Construir query com filtros
        query = supabase.table('importacoes_processos').select('*')
        query = apply_filters_to_query(query, filters)
        
        response = query.limit(500).execute()
        cached_data = response.data if response.data else []
        
        if not cached_data:
            return jsonify([])
        
        # Filtrar dados com material
        filtered_data = []
        for item in cached_data:
            if item.get('resumo_mercadoria') and item.get('resumo_mercadoria').strip():
                filtered_data.append(item)
        
        # Primeiro, obter os top 3 materiais
        material_counts = {}
        for item in filtered_data:
            material = item.get('resumo_mercadoria')
            if material and material.strip():
                material_info = material_cleaner.clean_material(material)
                material_limpo = material_info.get('material_limpo', material)
                
                if material_limpo not in material_counts:
                    material_counts[material_limpo] = 0
                material_counts[material_limpo] += 1
        
        top_3_materiais = [material for material, count in sorted(material_counts.items(), key=lambda x: x[1], reverse=True)[:3]]
        
        # Agrupar por mês e material
        monthly_data = {}
        for item in filtered_data:
            try:
                data_abertura = item.get('data_abertura')
                if not data_abertura:
                    continue
                    
                # Converter data ISO para datetime
                if 'T' in data_abertura:
                    date_obj = datetime.strptime(data_abertura[:10], '%Y-%m-%d')
                elif '/' in data_abertura:
                    day, month, year = data_abertura.split('/')
                    date_obj = datetime(int(year), int(month), int(day))
                else:
                    date_obj = datetime.strptime(data_abertura, '%Y-%m-%d')
                
                month_key = date_obj.strftime('%Y-%m')
                
                material = item.get('resumo_mercadoria')
                if material and material.strip():
                    material_info = material_cleaner.clean_material(material)
                    material_limpo = material_info.get('material_limpo', material)
                    
                    if material_limpo in top_3_materiais:
                        if month_key not in monthly_data:
                            monthly_data[month_key] = {}
                        
                        if material_limpo not in monthly_data[month_key]:
                            monthly_data[month_key][material_limpo] = 0
                        monthly_data[month_key][material_limpo] += 1
                        
            except Exception as e:
                continue
        
        # Converter para formato do Chart.js
        result = []
        for month, materials in sorted(monthly_data.items()):
            month_obj = datetime.strptime(month, '%Y-%m')
            month_str = month_obj.strftime('%m/%Y')
            
            for material, count in materials.items():
                result.append({
                    'mes': month_str,
                    'categoria_material': material,
                    'qtde': count
                })
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify([])

@bp.route('/bypass-modal-distribution')
def bypass_modal_distribution():
    """API de distribuição modal sem autenticação para teste - com suporte a filtros"""
    try:
        from extensions import supabase
        
        # Obter filtros da query string
        filters = {
            'data_inicio': request.args.get('data_inicio'),
            'data_fim': request.args.get('data_fim'),
            'material': request.args.get('material'),
            'cliente': request.args.get('cliente'),
            'modal': request.args.get('modal'),
            'canal': request.args.get('canal'),
            'valor_min': request.args.get('valor_min'),
            'valor_max': request.args.get('valor_max')
        }
        
        # Remover filtros vazios
        filters = {k: v for k, v in filters.items() if v and v.strip()}
        
        # Se não há filtros de data, usar últimos 30 dias
        if not filters.get('data_inicio') and not filters.get('data_fim'):
            from datetime import datetime, timedelta
            data_limite = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            filters['data_inicio'] = data_limite
        
        # Construir query com filtros
        query = supabase.table('importacoes_processos').select('*')
        query = apply_filters_to_query(query, filters)
        
        response = query.limit(500).execute()
        cached_data = response.data if response.data else []
        
        if not cached_data:
            return jsonify([])
        
        # Filtrar dados com material
        filtered_data = []
        for item in cached_data:
            if item.get('resumo_mercadoria') and item.get('resumo_mercadoria').strip():
                filtered_data.append(item)
        
        # Agrupar por modal
        modal_counts = {}
        for item in filtered_data:
            modal = item.get('via_transporte_descricao', 'Não Informado')
            if not modal or modal.strip() == '':
                modal = 'Não Informado'
            
            if modal not in modal_counts:
                modal_counts[modal] = 0
            modal_counts[modal] += 1
        
        return jsonify([{
            'modal': modal,
            'total': count
        } for modal, count in modal_counts.items()])
        
    except Exception as e:
        return jsonify([])

@bp.route('/bypass-canal-distribution')
def bypass_canal_distribution():
    """API de distribuição canal sem autenticação para teste - com suporte a filtros"""
    try:
        from extensions import supabase
        
        # Obter filtros da query string
        filters = {
            'data_inicio': request.args.get('data_inicio'),
            'data_fim': request.args.get('data_fim'),
            'material': request.args.get('material'),
            'cliente': request.args.get('cliente'),
            'modal': request.args.get('modal'),
            'canal': request.args.get('canal'),
            'valor_min': request.args.get('valor_min'),
            'valor_max': request.args.get('valor_max')
        }
        
        # Remover filtros vazios
        filters = {k: v for k, v in filters.items() if v and v.strip()}
        
        # Se não há filtros de data, usar últimos 30 dias
        if not filters.get('data_inicio') and not filters.get('data_fim'):
            from datetime import datetime, timedelta
            data_limite = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            filters['data_inicio'] = data_limite
        
        # Construir query com filtros
        query = supabase.table('importacoes_processos').select('*')
        query = apply_filters_to_query(query, filters)
        
        response = query.limit(500).execute()
        cached_data = response.data if response.data else []
        
        if not cached_data:
            return jsonify([])
        
        # Filtrar dados com material
        filtered_data = []
        for item in cached_data:
            if item.get('resumo_mercadoria') and item.get('resumo_mercadoria').strip():
                filtered_data.append(item)
        
        # Agrupar por canal
        canal_counts = {}
        for item in filtered_data:
            canal = item.get('diduimp_canal', 'Não Informado')
            if not canal or canal.strip() == '':
                canal = 'Não Informado'
            
            if canal not in canal_counts:
                canal_counts[canal] = 0
            canal_counts[canal] += 1
        
        return jsonify([{
            'canal': canal,
            'total': count
        } for canal, count in canal_counts.items()])
        
    except Exception as e:
        return jsonify([])

@bp.route('/bypass-filter-options')
def bypass_filter_options():
    """API para obter opções de filtro sem autenticação"""
    try:
        from extensions import supabase
        
        # Buscar dados com limite
        response = supabase.table('importacoes_processos').select('*').limit(1000).execute()
        cached_data = response.data if response.data else []
        
        if not cached_data:
            return jsonify({
                'materiais': [],
                'clientes': [],
                'modais': [],
                'canais': []
            })
        
        # Extrair opções únicas
        materiais = set()
        clientes = set()
        modais = set()
        canais = set()
        
        for item in cached_data:
            # Materiais categorizados
            if item.get('resumo_mercadoria') and item.get('resumo_mercadoria').strip():
                material_info = material_cleaner.clean_material(item.get('resumo_mercadoria'))
                material_limpo = material_info.get('material_limpo')
                if material_limpo:
                    materiais.add(material_limpo)
            
            # Clientes
            if item.get('cliente_razaosocial') and item.get('cliente_razaosocial').strip():
                clientes.add(item.get('cliente_razaosocial'))
            
            # Modais
            if item.get('via_transporte_descricao') and item.get('via_transporte_descricao').strip():
                modais.add(item.get('via_transporte_descricao'))
            
            # Canais
            if item.get('diduimp_canal') and item.get('diduimp_canal').strip():
                canais.add(item.get('diduimp_canal'))
        
        # Converter para listas ordenadas
        return jsonify({
            'materiais': sorted(list(materiais)),
            'clientes': sorted(list(clientes)),
            'modais': sorted(list(modais)),
            'canais': sorted(list(canais))
        })
        
    except Exception as e:
        return jsonify({
            'materiais': [],
            'clientes': [],
            'modais': [],
            'canais': []
        })

@bp.route('/bypass-principais-materiais')
def bypass_principais_materiais():
    """Endpoint para obter principais materiais sem autenticação"""
    try:
        # Obter dados do cache
        from extensions import supabase
        cached_data = session.get('cached_data', [])
        
        if not cached_data:
            # Fallback para dados diretos
            response = supabase.table('importacoes_processos').select('*').limit(200).execute()
            cached_data = response.data if response.data else []
        
        # Aplicar filtros
        filtered_data = apply_filters_to_query(cached_data, request.args)
        
        # Agrupar por material
        material_stats = {}
        for item in filtered_data:
            material = material_cleaner.clean_material(item.get('resumo_mercadoria', ''))
            material_nome = material.get('material_limpo', 'Não informado')
            
            if material_nome not in material_stats:
                material_stats[material_nome] = {
                    'material': material_nome,
                    'qtde_processos': 0,
                    'custo_total': 0,
                    'proxima_chegada': None
                }
            
            material_stats[material_nome]['qtde_processos'] += 1
            
            # Custo total
            if item.get('custo_total'):
                try:
                    material_stats[material_nome]['custo_total'] += float(item.get('custo_total', 0))
                except:
                    pass
        
        # Ordenar por quantidade e pegar top 10
        principais = sorted(material_stats.values(), key=lambda x: x['qtde_processos'], reverse=True)[:10]
        
        return jsonify(principais)
        
    except Exception as e:
        print(f"[MATERIAIS] Erro ao buscar principais materiais: {e}")
        return jsonify([])

@bp.route('/bypass-detalhamento-processos')
def bypass_detalhamento_processos():
    """Endpoint para obter detalhamento dos processos sem autenticação"""
    try:
        # Obter dados do cache
        from extensions import supabase
        cached_data = session.get('cached_data', [])
        
        if not cached_data:
            # Fallback para dados diretos
            response = supabase.table('importacoes_processos').select('*').limit(200).execute()
            cached_data = response.data if response.data else []
        
        # Aplicar filtros
        filtered_data = apply_filters_to_query(cached_data, request.args)
        
        # Processar dados para detalhamento
        detalhamento = []
        for item in filtered_data:
            material_info = material_cleaner.clean_material(item.get('resumo_mercadoria', ''))
            
            detalhamento.append({
                'data_abertura': item.get('data_abertura'),
                'numero_pedido': item.get('ref_unique'),
                'cliente': item.get('cliente_razaosocial'),
                'material': material_info.get('material_limpo', 'Não informado'),
                'data_embarque': item.get('data_embarque'),
                'data_chegada': item.get('data_chegada'),
                'status_carga': item.get('status_processo'),
                'canal': item.get('diduimp_canal'),
                'custo_total': item.get('custo_total', 0)
            })
        
        # Limitar a 100 registros para performance
        return jsonify(detalhamento[:100])
        
    except Exception as e:
        print(f"[MATERIAIS] Erro ao buscar detalhamento: {e}")
        return jsonify([])

@bp.route('/bypass-transit-time')
def bypass_transit_time():
    """Endpoint para obter transit time por material sem autenticação"""
    try:
        # Obter dados do cache
        from extensions import supabase
        cached_data = session.get('cached_data', [])
        
        if not cached_data:
            # Fallback para dados diretos
            response = supabase.table('importacoes_processos').select('*').limit(200).execute()
            cached_data = response.data if response.data else []
        
        # Aplicar filtros
        filtered_data = apply_filters_to_query(cached_data, request.args)
        
        # Calcular transit time por material
        material_transit = {}
        for item in filtered_data:
            material_info = material_cleaner.clean_material(item.get('resumo_mercadoria', ''))
            material_nome = material_info.get('material_limpo', 'Não informado')
            
            # Calcular transit time se as datas existirem
            data_embarque = item.get('data_embarque')
            data_chegada = item.get('data_chegada')
            
            if data_embarque and data_chegada:
                try:
                    # Tentar diferentes formatos de data
                    dt_embarque = None
                    dt_chegada = None
                    
                    # Formato ISO (2017-03-20T00:00:00)
                    if 'T' in str(data_embarque):
                        dt_embarque = datetime.fromisoformat(str(data_embarque).replace('T', ' ').replace('Z', ''))
                        dt_chegada = datetime.fromisoformat(str(data_chegada).replace('T', ' ').replace('Z', ''))
                    else:
                        # Formato brasileiro (DD/MM/YYYY)
                        dt_embarque = datetime.strptime(str(data_embarque), '%d/%m/%Y')
                        dt_chegada = datetime.strptime(str(data_chegada), '%d/%m/%Y')
                    
                    transit_days = (dt_chegada - dt_embarque).days
                    
                    if transit_days > 0:  # Apenas valores positivos
                        if material_nome not in material_transit:
                            material_transit[material_nome] = []
                        material_transit[material_nome].append(transit_days)
                except Exception as e:
                    print(f"[TRANSIT TIME] Erro ao processar datas {data_embarque} -> {data_chegada}: {e}")
                    pass
        
        # Calcular média por material
        result = []
        for material, days_list in material_transit.items():
            if days_list:
                avg_days = sum(days_list) / len(days_list)
                result.append({
                    'categoria_material': material,
                    'transit_time_medio': round(avg_days, 1)
                })
        
        # Ordenar por transit time e pegar top 10
        result.sort(key=lambda x: x['transit_time_medio'], reverse=True)
        return jsonify(result[:10])
        
    except Exception as e:
        print(f"[MATERIAIS] Erro ao buscar transit time: {e}")
        return jsonify([])
