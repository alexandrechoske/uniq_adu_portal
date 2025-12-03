from flask import Blueprint, render_template, session, jsonify, request
from extensions import supabase, supabase_admin
from routes.auth import login_required
from decorators.perfil_decorators import perfil_required
from datetime import datetime
import calendar
import json
from collections import defaultdict

# Blueprint para Faturamento
faturamento_bp = Blueprint(
    'fin_faturamento', 
    __name__,
    url_prefix='/financeiro/faturamento',
    template_folder='templates',
    static_folder='static'
)

@faturamento_bp.route('/')
@login_required
@perfil_required('financeiro', 'faturamento')
def index():
    """Faturamento Anual - Controle de receitas"""
    return render_template('faturamento.html')

@faturamento_bp.route('/api/empresas')
@login_required
@perfil_required('financeiro', 'faturamento')
def api_empresas():
    """API para buscar empresas disponíveis no banco de dados"""
    try:
        # Buscar empresas distintas da tabela de faturamento
        response = supabase_admin.table('fin_faturamento_anual').select('empresa').execute()
        dados = response.data
        
        # Extrair empresas únicas
        empresas_set = set()
        for item in dados:
            if item.get('empresa') and item['empresa'].strip():
                empresas_set.add(item['empresa'].strip())
        
        empresas_lista = sorted(list(empresas_set))
        
        # Log para debug
        print(f"📊 Empresas encontradas: {empresas_lista}")
        
        return jsonify({
            'success': True,
            'data': empresas_lista
        })
        
    except Exception as e:
        print(f"❌ Erro ao buscar empresas: {str(e)}")
        return jsonify({
            'success': False, 
            'error': str(e)
        }), 500

@faturamento_bp.route('/api/clientes')
@login_required
@perfil_required('financeiro', 'faturamento')
def api_clientes():
    """API para buscar clientes disponíveis"""
    try:
        # Buscar clientes distintos da tabela de faturamento
        response = supabase_admin.table('fin_faturamento_anual').select('cliente').execute()
        dados = response.data
        
        # Extrair clientes únicos
        clientes_set = set()
        for item in dados:
            if item.get('cliente') and item['cliente'].strip():
                clientes_set.add(item['cliente'].strip())
        
        clientes_lista = sorted(list(clientes_set))
        
        print(f"📊 Clientes encontrados: {len(clientes_lista)}")
        
        return jsonify({
            'success': True,
            'data': clientes_lista
        })
        
    except Exception as e:
        print(f"❌ Erro ao buscar clientes: {str(e)}")
        return jsonify({
            'success': False, 
            'error': str(e)
        }), 500

@faturamento_bp.route('/api/centros-resultado')
@login_required
@perfil_required('financeiro', 'faturamento')
def api_centros_resultado():
    """API para buscar centros de resultado disponíveis"""
    try:
        # Buscar centros de resultado distintos da tabela de faturamento
        response = supabase_admin.table('fin_faturamento_anual').select('centro_resultado').execute()
        dados = response.data
        
        # Extrair centros únicos
        centros_set = set()
        for item in dados:
            if item.get('centro_resultado') and item['centro_resultado'].strip():
                centros_set.add(item['centro_resultado'].strip())
        
        centros_lista = sorted(list(centros_set))
        
        print(f"📊 Centros de resultado encontrados: {len(centros_lista)}")
        
        return jsonify({
            'success': True,
            'data': centros_lista
        })
        
    except Exception as e:
        print(f"❌ Erro ao buscar centros de resultado: {str(e)}")
        return jsonify({
            'success': False, 
            'error': str(e)
        }), 500

@faturamento_bp.route('/api/geral/kpis')
@login_required
@perfil_required('financeiro', 'faturamento')
def api_geral_kpis():
    """API para KPIs da Visão Geral de Faturamento"""
    try:
        ano = request.args.get('ano', datetime.now().year)
        empresa = request.args.get('empresa', '')
        centro_resultado = request.args.get('centro_resultado', '')
        cliente = request.args.get('cliente', '')
        
        # Buscar dados de faturamento do ano usando a nova tabela
        query = supabase_admin.table('vw_fin_faturamento_anual_tratado').select('*').gte('data', f'{ano}-01-01').lte('data', f'{ano}-12-31')
        if empresa and empresa.strip() and empresa != 'ambos':
            if empresa == 'consultoria':
                query = query.eq('meta_grupo', 'Consultoria')
            elif empresa == 'imp_exp':
                query = query.eq('meta_grupo', 'IMP/EXP')
        
        if centro_resultado:
            query = query.eq('centro_resultado', centro_resultado)
            
        if cliente:
            query = query.eq('cliente', cliente)
            
        response = query.execute()
        dados_faturamento = response.data
        
        # Calcular total faturado
        total_faturado = sum(float(item['valor']) for item in dados_faturamento)
        
        return jsonify({
            'total_faturado': total_faturado
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@faturamento_bp.route('/api/geral/mensal')
@login_required
@perfil_required('financeiro', 'faturamento')
def api_geral_mensal():
    """API para tabela de faturamento mensal da Visão Geral"""
    try:
        ano = request.args.get('ano', datetime.now().year)
        empresa = request.args.get('empresa', '')
        centro_resultado = request.args.get('centro_resultado', '')
        cliente = request.args.get('cliente', '')
        
        # Buscar dados de faturamento do ano atual usando a nova tabela
        query_atual = supabase_admin.table('vw_fin_faturamento_anual_tratado').select('*').gte('data', f'{ano}-01-01').lte('data', f'{ano}-12-31')
        if empresa and empresa.strip() and empresa != 'ambos':
            if empresa == 'consultoria':
                query_atual = query_atual.eq('meta_grupo', 'Consultoria')
            elif empresa == 'imp_exp':
                query_atual = query_atual.eq('meta_grupo', 'IMP/EXP')
        
        if centro_resultado:
            query_atual = query_atual.eq('centro_resultado', centro_resultado)
            
        if cliente:
            query_atual = query_atual.eq('cliente', cliente)
            
        response_atual = query_atual.execute()
        dados_atual = response_atual.data
        
        # Buscar dados de faturamento do ano anterior
        ano_anterior = int(ano) - 1
        query_anterior = supabase_admin.table('vw_fin_faturamento_anual_tratado').select('*').gte('data', f'{ano_anterior}-01-01').lte('data', f'{ano_anterior}-12-31')
        if empresa and empresa.strip() and empresa != 'ambos':
            if empresa == 'consultoria':
                query_anterior = query_anterior.eq('meta_grupo', 'Consultoria')
            elif empresa == 'imp_exp':
                query_anterior = query_anterior.eq('meta_grupo', 'IMP/EXP')
                
        if centro_resultado:
            query_anterior = query_anterior.eq('centro_resultado', centro_resultado)
            
        if cliente:
            query_anterior = query_anterior.eq('cliente', cliente)
            
        response_anterior = query_anterior.execute()
        dados_anterior = response_anterior.data
        
        # Agrupar por mês para o ano atual
        faturamento_atual = defaultdict(float)
        for item in dados_atual:
            data_item = datetime.strptime(item['data'], '%Y-%m-%d')
            mes_key = data_item.strftime('%Y-%m')
            faturamento_atual[mes_key] += float(item['valor'])
        
        # Agrupar por mês para o ano anterior
        faturamento_anterior = defaultdict(float)
        for item in dados_anterior:
            data_item = datetime.strptime(item['data'], '%Y-%m-%d')
            mes_key = data_item.strftime('%Y-%m')
            faturamento_anterior[mes_key] += float(item['valor'])
        
        # Preparar dados para a tabela
        meses = []
        for mes in range(1, 13):
            mes_atual = f"{ano}-{mes:02d}"
            mes_anterior = f"{ano_anterior}-{mes:02d}"
            
            faturamento_mes = faturamento_atual.get(mes_atual, 0)
            faturamento_mes_anterior = faturamento_anterior.get(mes_anterior, 0)
            
            # Calcular variação percentual
            if faturamento_mes_anterior > 0:
                variacao = ((faturamento_mes - faturamento_mes_anterior) / faturamento_mes_anterior) * 100
            else:
                variacao = 0 if faturamento_mes == 0 else 100
            
            meses.append({
                'ano': ano,
                'mes': mes,
                'faturamento_total': faturamento_mes,
                'faturamento_anterior': faturamento_mes_anterior,
                'variacao': variacao
            })
        
        return jsonify({
            'success': True,
            'data': meses
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@faturamento_bp.route('/api/geral/proporcao')
@login_required
@perfil_required('financeiro', 'faturamento')
def api_geral_proporcao():
    """API para gráficos de proporção da Visão Geral usando meta_grupo"""
    try:
        ano = request.args.get('ano', datetime.now().year)
        empresa = request.args.get('empresa', '')
        centro_resultado = request.args.get('centro_resultado', '')
        cliente = request.args.get('cliente', '')
        
        # Buscar dados de faturamento do ano usando a nova tabela
        query = supabase_admin.table('vw_fin_faturamento_anual_tratado').select('*').gte('data', f'{ano}-01-01').lte('data', f'{ano}-12-31')
        if empresa and empresa.strip() and empresa != 'ambos':
            if empresa == 'consultoria':
                query = query.eq('meta_grupo', 'Consultoria')
            elif empresa == 'imp_exp':
                query = query.eq('meta_grupo', 'IMP/EXP')
        
        if centro_resultado:
            query = query.eq('centro_resultado', centro_resultado)
            
        if cliente:
            query = query.eq('cliente', cliente)
            
        response = query.execute()
        dados_faturamento = response.data
        
        # Calcular totais por meta_grupo
        total_consultoria = 0
        total_imp_exp = 0
        
        for item in dados_faturamento:
            meta_grupo = item.get('meta_grupo', '')
            valor = float(item['valor'])
            
            if meta_grupo == 'Consultoria':
                total_consultoria += valor
            elif meta_grupo == 'IMP/EXP':
                total_imp_exp += valor
        
        total_geral = total_consultoria + total_imp_exp
        
        # Calcular percentuais
        pct_consultoria = (total_consultoria / total_geral * 100) if total_geral > 0 else 0
        pct_imp_exp = (total_imp_exp / total_geral * 100) if total_geral > 0 else 0
        
        return jsonify({
            'setores': {
                'consultoria': {
                    'valor': total_consultoria,
                    'percentual': pct_consultoria
                },
                'imp_exp': {
                    'valor': total_imp_exp,
                    'percentual': pct_imp_exp
                }
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@faturamento_bp.route('/api/geral/comparativo_anos')
@login_required
@perfil_required('financeiro', 'faturamento')
def api_geral_comparativo_anos():
    """API para comparativo anual usando nova classificação por meta_grupo"""
    try:
        # Pegar filtros
        empresa = request.args.get('empresa', '')
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        centro_resultado = request.args.get('centro_resultado', '')
        cliente = request.args.get('cliente', '')
        
        # Usar a view atualizada com meta_grupo
        query = supabase_admin.table('vw_fin_faturamento_anual_tratado').select('data, valor, meta_grupo, centro_resultado, cliente')
        
        # Aplicar filtro de data
        if start_date:
            query = query.gte('data', start_date)
        if end_date:
            query = query.lte('data', end_date)
        
        # Aplicar filtro baseado no meta_grupo se especificado
        if empresa and empresa.strip() and empresa != 'ambos':
            if empresa.lower() in ['consultoria']:
                query = query.eq('meta_grupo', 'Consultoria')
            elif empresa.lower() in ['imp/exp', 'imp_exp', 'importacao', 'exportacao']:
                query = query.eq('meta_grupo', 'IMP/EXP')
        
        # Aplicar filtro de centro de resultado
        if centro_resultado:
            query = query.eq('centro_resultado', centro_resultado)
        
        # Aplicar filtro de cliente
        if cliente:
            query = query.eq('cliente', cliente)
        
        response = query.execute()
        dados = response.data
        
        # Log para debug
        print(f"📊 Comparativo anos - Empresa: {empresa}, Start: {start_date}, End: {end_date}, CR: {centro_resultado}, Cliente: {cliente}, Registros: {len(dados)}")
        
        # Agrupar dados por ano e mês
        anos_data = defaultdict(lambda: defaultdict(float))
        
        for item in dados:
            if item.get('data') and item.get('valor'):
                try:
                    data_str = item['data']
                    # Assumindo formato YYYY-MM-DD
                    ano = data_str[:4]
                    mes = data_str[5:7]
                    valor = float(item['valor'])
                    
                    anos_data[ano][mes] += valor
                except Exception as e:
                    print(f"Erro ao processar data {item.get('data')}: {e}")
                    continue
        
        # Formatar dados para o frontend
        resultado = {}
        for ano in sorted(anos_data.keys()):
            meses_data = []
            for mes in ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12']:
                valor = anos_data[ano].get(mes, 0)
                meses_data.append({
                    'mes': mes,
                    'total_valor': valor
                })
            resultado[ano] = meses_data
        
        return jsonify({
            'success': True,
            'data': resultado
        })
        
    except Exception as e:
        print(f"Erro no comparativo_anos: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@faturamento_bp.route('/api/geral/sunburst_data')
@login_required
@perfil_required('financeiro', 'faturamento')
def api_geral_sunburst_data():
    """API para dados do gráfico sunburst: Centro Resultado -> Categoria"""
    try:
        start_date = request.args.get('start_date', '2024-01-01')
        end_date = request.args.get('end_date', '2024-12-31')
        empresa = request.args.get('empresa', '')
        centro_resultado = request.args.get('centro_resultado', '')
        cliente = request.args.get('cliente', '')
        
        # Buscar dados com centro_resultado e categoria
        query = supabase_admin.table('fin_faturamento_anual').select('centro_resultado, categoria, valor, cliente')
        
        # Aplicar filtros
        if start_date:
            query = query.gte('data', start_date)
        if end_date:
            query = query.lte('data', end_date)
        if empresa and empresa.strip():
            query = query.eq('empresa', empresa)
        
        if centro_resultado:
            query = query.eq('centro_resultado', centro_resultado)
            
        if cliente:
            query = query.eq('cliente', cliente)
            
        response = query.execute()
        dados = response.data
        
        # Organizar dados para o sunburst
        resultado = []
        
        for item in dados:
            centro = item.get('centro_resultado') or 'Não Classificado'
            categoria = item.get('categoria') or 'Outros'
            valor = float(item.get('valor', 0))
            
            resultado.append({
                'centro_resultado': centro,
                'categoria': categoria,
                'total_valor': valor
            })
        
        return jsonify({
            'success': True,
            'data': resultado
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@faturamento_bp.route('/api/setor/dados_completos')
@login_required
@perfil_required('financeiro', 'faturamento')
def api_setor_dados_completos():
    """API para dados completos de um setor específico"""
    try:
        setor = request.args.get('setor', 'importacao')
        inicio = request.args.get('inicio')
        fim = request.args.get('fim')
        
        # Definir filtro de classe com base no setor
        filtro_classe = ''
        if setor == 'importacao':
            filtro_classe = 'IMP'
        elif setor == 'consultoria':
            filtro_classe = 'CONS'
        elif setor == 'exportacao':
            filtro_classe = 'EXP'
        
        # Buscar dados de faturamento com filtro de classe
        query = supabase_admin.table('fin_faturamento_anual').select('*')
        if filtro_classe:
            query = query.ilike('classe', f'%{filtro_classe}%')
        if inicio and fim:
            query = query.gte('data', inicio).lte('data', fim)
        
        response = query.execute()
        dados_faturamento = response.data
        
        # Calcular faturamento total do setor
        total_setor = sum(float(item['valor']) for item in dados_faturamento)
        
        # Calcular participação percentual no faturamento total
        # Buscar faturamento total da empresa no mesmo período
        total_query = supabase_admin.table('fin_faturamento_anual').select('*')
        if inicio and fim:
            total_query = total_query.gte('data', inicio).lte('data', fim)
        total_response = total_query.execute()
        total_empresa = sum(float(item['valor']) for item in total_response.data)
        
        pct_participacao = (total_setor / total_empresa * 100) if total_empresa > 0 else 0
        
        # Agrupar faturamento mensal do setor
        faturamento_mensal = defaultdict(float)
        faturamento_mensal_anterior = defaultdict(float)
        
        for item in dados_faturamento:
            data_item = datetime.strptime(item['data'], '%Y-%m-%d')
            mes_key = data_item.strftime('%Y-%m')
            
            # Fix the date error by ensuring we don't go out of range when creating the previous year date
            try:
                # Para comparação com ano anterior
                if data_item.month == 2 and data_item.day == 29:
                    # Handle leap year case - use Feb 28 of previous year
                    data_anterior = data_item.replace(year=data_item.year - 1, day=28)
                else:
                    data_anterior = data_item.replace(year=data_item.year - 1)
                mes_anterior_key = data_anterior.strftime('%Y-%m')
                faturamento_mensal_anterior[mes_anterior_key] += float(item['valor'])
            except ValueError:
                # Handle any other date errors by skipping this item for previous year comparison
                pass
            
            faturamento_mensal[mes_key] += float(item['valor'])
        
        # Preparar dados mensais
        meses_data = []
        # Get all unique months from the current period data
        meses_unicos = set(faturamento_mensal.keys())
        for mes_key in sorted(meses_unicos):
            # For each month in current period, we want to show:
            # 1. Current period value (faturamento)
            # 2. Previous period value (faturamento_anterior) for the same month
            
            # Calculate the previous year's month key for comparison
            year, month = mes_key.split('-')
            mes_anterior_key = f"{int(year)-1}-{month}"
            
            meses_data.append({
                'mes': mes_key,
                'faturamento': faturamento_mensal.get(mes_key, 0),
                'faturamento_anterior': faturamento_mensal_anterior.get(mes_anterior_key, 0)
            })
        
        # Buscar mapeamento de clientes
        mapeamento_response = supabase_admin.table('fin_clientes_mapeamento').select('nome_original, nome_padronizado').execute()
        mapeamento_clientes = {}
        if mapeamento_response.data:
            for item in mapeamento_response.data:
                mapeamento_clientes[item['nome_original']] = item['nome_padronizado']
        
        # Ranking de clientes com nomes padronizados
        clientes_ranking = defaultdict(lambda: {'valor': 0, 'classe': ''})
        for item in dados_faturamento:
            cliente_original = item.get('cliente', 'Não identificado')
            # Usar nome padronizado se existir, senão usar o original
            cliente_padronizado = mapeamento_clientes.get(cliente_original, cliente_original)
            clientes_ranking[cliente_padronizado]['valor'] += float(item['valor'])
            clientes_ranking[cliente_padronizado]['classe'] = item.get('classe', '')
        
        # Converter para lista e ordenar
        ranking_lista = []
        for cliente, dados in clientes_ranking.items():
            pct_gt = (dados['valor'] / total_setor * 100) if total_setor > 0 else 0
            ranking_lista.append({
                'cliente': cliente,
                'classe': dados['classe'],
                'valor': dados['valor'],
                'pct_gt': pct_gt
            })
        
        ranking_lista.sort(key=lambda x: x['valor'], reverse=True)
        
        return jsonify({
            'kpis': {
                'faturamento_total': total_setor,
                'percentual_participacao': pct_participacao
            },
            'grafico_mensal': meses_data,
            'ranking_clientes': ranking_lista
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@faturamento_bp.route('/api/geral/centro_resultado')
@login_required
@perfil_required('financeiro', 'faturamento')
def api_geral_centro_resultado():
    """API para gráfico de rosca - Faturamento por Centro de Resultado"""
    try:
        start_date = request.args.get('start_date', f'{datetime.now().year}-01-01')
        end_date = request.args.get('end_date', f'{datetime.now().year}-12-31')
        empresa = request.args.get('empresa', '')
        centro_resultado = request.args.get('centro_resultado', '')
        cliente = request.args.get('cliente', '')
        
        # Usar a view atualizada
        query = supabase_admin.table('vw_fin_faturamento_anual_tratado').select('centro_resultado, valor, meta_grupo, cliente')
        
        # Aplicar filtros
        if start_date:
            query = query.gte('data', start_date)
        if end_date:
            query = query.lte('data', end_date)
        
        # Filtro por meta_grupo baseado no parâmetro empresa
        if empresa and empresa.strip() and empresa != 'ambos':
            if empresa.lower() in ['consultoria']:
                query = query.eq('meta_grupo', 'Consultoria')
            elif empresa.lower() in ['imp/exp', 'imp_exp', 'importacao', 'exportacao']:
                query = query.eq('meta_grupo', 'IMP/EXP')
        
        if centro_resultado:
            query = query.eq('centro_resultado', centro_resultado)
            
        if cliente:
            query = query.eq('cliente', cliente)
            
        response = query.execute()
        dados = response.data
        
        # Agrupar por centro de resultado
        centro_resultado_data = defaultdict(float)
        total_geral = 0
        
        for item in dados:
            centro = item.get('centro_resultado', 'Não Classificado')
            valor = float(item.get('valor', 0))
            centro_resultado_data[centro] += valor
            total_geral += valor
        
        # Preparar dados para o gráfico de rosca
        resultado = []
        for centro, valor in centro_resultado_data.items():
            percentual = (valor / total_geral * 100) if total_geral > 0 else 0
            resultado.append({
                'centro_resultado': centro,
                'valor': valor,
                'percentual': percentual
            })
        
        # Ordenar por valor decrescente
        resultado.sort(key=lambda x: x['valor'], reverse=True)
        
        return jsonify({
            'success': True,
            'data': resultado,
            'total': total_geral
        })
        
    except Exception as e:
        print(f"Erro em api_geral_centro_resultado: {str(e)}")
        return jsonify({'error': str(e)}), 500

@faturamento_bp.route('/api/geral/categoria_operacao')
@login_required
@perfil_required('financeiro', 'faturamento')
def api_geral_categoria_operacao():
    """API para gráfico de rosca - Faturamento por Categoria usando nova classificação"""
    try:
        start_date = request.args.get('start_date', f'{datetime.now().year}-01-01')
        end_date = request.args.get('end_date', f'{datetime.now().year}-12-31')
        empresa = request.args.get('empresa', '')
        centro_resultado = request.args.get('centro_resultado', '')
        cliente = request.args.get('cliente', '')
        
        # Usar a view atualizada com meta_grupo
        query = supabase_admin.table('vw_fin_faturamento_anual_tratado').select('categoria, valor, meta_grupo, centro_resultado, cliente')
        
        # Aplicar filtros
        if start_date:
            query = query.gte('data', start_date)
        if end_date:
            query = query.lte('data', end_date)
        
        # Filtro por meta_grupo baseado no parâmetro empresa
        if empresa and empresa.strip() and empresa != 'ambos':
            if empresa.lower() in ['consultoria']:
                query = query.eq('meta_grupo', 'Consultoria')
            elif empresa.lower() in ['imp/exp', 'imp_exp', 'importacao', 'exportacao']:
                query = query.eq('meta_grupo', 'IMP/EXP')
        
        if centro_resultado:
            query = query.eq('centro_resultado', centro_resultado)
            
        if cliente:
            query = query.eq('cliente', cliente)
            
        response = query.execute()
        dados = response.data
        
        # Log para debug
        print(f"📊 Categoria operação - Empresa: {empresa}, Registros: {len(dados)}")
        
        # Agrupar por categoria
        categoria_data = defaultdict(float)
        total_geral = 0
        
        for item in dados:
            categoria = item.get('categoria', 'Não Classificado')
            valor = float(item.get('valor', 0))
            categoria_data[categoria] += valor
            total_geral += valor
        
        # Preparar dados para o gráfico de rosca
        resultado = []
        for categoria, valor in categoria_data.items():
            percentual = (valor / total_geral * 100) if total_geral > 0 else 0
            resultado.append({
                'categoria': categoria,
                'valor': valor,
                'percentual': percentual
            })
        
        # Ordenar por valor decrescente
        resultado.sort(key=lambda x: x['valor'], reverse=True)
        
        return jsonify({
            'success': True,
            'data': resultado,
            'total': total_geral
        })
        
    except Exception as e:
        print(f"Erro em api_geral_categoria_operacao: {str(e)}")
        return jsonify({'error': str(e)}), 500

@faturamento_bp.route('/api/geral/centro_resultado_detalhado')
@login_required
@perfil_required('financeiro', 'faturamento')
def api_geral_centro_resultado_detalhado():
    """API para drill-down do centro de resultado - mostra categorias dentro do centro (hierarquia correta)"""
    try:
        centro_resultado = request.args.get('centro_resultado', '')
        start_date = request.args.get('start_date', f'{datetime.now().year}-01-01')
        end_date = request.args.get('end_date', f'{datetime.now().year}-12-31')
        empresa = request.args.get('empresa', '')
        cliente = request.args.get('cliente', '')
        
        if not centro_resultado:
            return jsonify({'error': 'Centro de resultado é obrigatório'}), 400
        
        # Usar a view tratada que tem a hierarquia correta
        try:
            query = supabase_admin.table('vw_fin_faturamento_anual_tratado').select('categoria, valor, centro_resultado, meta_grupo, cliente')
        except:
            # Fallback para tabela original
            query = supabase_admin.table('fin_faturamento_anual').select('categoria, valor, centro_resultado, meta_grupo, cliente')
        
        # Filtrar por centro de resultado
        query = query.eq('centro_resultado', centro_resultado)
        
        # Aplicar filtros de data
        if start_date:
            query = query.gte('data', start_date)
        if end_date:
            query = query.lte('data', end_date)
            
        # Filtro por meta_grupo baseado no parâmetro empresa
        if empresa and empresa.strip() and empresa != 'ambos':
            if empresa.lower() in ['consultoria']:
                query = query.eq('meta_grupo', 'Consultoria')
            elif empresa.lower() in ['imp/exp', 'imp_exp', 'importacao', 'exportacao']:
                query = query.eq('meta_grupo', 'IMP/EXP')
        
        # Filtro por cliente
        if cliente:
            query = query.eq('cliente', cliente)
            
        response = query.execute()
        dados = response.data
        
        # Agrupar por categoria (hierarquia correta: centro_resultado -> categoria)
        categoria_data = defaultdict(float)
        total_geral = 0
        
        for item in dados:
            categoria = item.get('categoria', 'Não Classificado')
            valor = float(item.get('valor', 0))
            categoria_data[categoria] += valor
            total_geral += valor
        
        # Preparar dados para o gráfico
        resultado = []
        for categoria, valor in categoria_data.items():
            percentual = (valor / total_geral * 100) if total_geral > 0 else 0
            resultado.append({
                'cliente': categoria,  # Mantendo o campo 'cliente' para compatibilidade com o frontend
                'valor_faturamento': valor,
                'percentual': percentual
            })
        
        # Ordenar por valor decrescente
        resultado.sort(key=lambda x: x['valor_faturamento'], reverse=True)
        
        return jsonify({
            'sucesso': True,
            'dados': resultado,
            'total': total_geral,
            'centro_resultado_pai': centro_resultado
        })
        
    except Exception as e:
        print(f"Erro em api_geral_centro_resultado_detalhado: {str(e)}")
        return jsonify({'error': str(e)}), 500

@faturamento_bp.route('/api/geral/top_clientes')
@login_required
@perfil_required('financeiro', 'faturamento')
def api_geral_top_clientes():
    """API para tabela de top clientes usando nova classificação"""
    try:
        start_date = request.args.get('start_date', f'{datetime.now().year}-01-01')
        end_date = request.args.get('end_date', f'{datetime.now().year}-12-31')
        empresa = request.args.get('empresa', '')
        centro_resultado = request.args.get('centro_resultado', '')
        cliente = request.args.get('cliente', '')
        limit = int(request.args.get('limit', 10))
        
        # Usar a view atualizada com meta_grupo
        query = supabase_admin.table('vw_fin_faturamento_anual_tratado').select('cliente, valor, meta_grupo, centro_resultado')
        
        # Aplicar filtros
        if start_date:
            query = query.gte('data', start_date)
        if end_date:
            query = query.lte('data', end_date)
        
        # Filtro por meta_grupo baseado no parâmetro empresa
        if empresa and empresa.strip() and empresa != 'ambos':
            if empresa.lower() in ['consultoria']:
                query = query.eq('meta_grupo', 'Consultoria')
            elif empresa.lower() in ['imp/exp', 'imp_exp', 'importacao', 'exportacao']:
                query = query.eq('meta_grupo', 'IMP/EXP')
        
        # Filtro por centro de resultado
        if centro_resultado:
            query = query.eq('centro_resultado', centro_resultado)
        
        # Filtro por cliente
        if cliente:
            query = query.eq('cliente', cliente)
            
        response = query.execute()
        dados = response.data
        
        # Log para debug
        print(f"📊 Top Clientes - Start: {start_date}, End: {end_date}, Empresa: {empresa}, CR: {centro_resultado}, Cliente: {cliente}, Registros: {len(dados)}")
        
        # Buscar mapeamento de clientes para padronização (se existir)
        try:
            mapeamento_response = supabase_admin.table('fin_clientes_mapeamento').select('nome_original, nome_padronizado').execute()
            mapeamento_clientes = {}
            if mapeamento_response.data:
                for item in mapeamento_response.data:
                    mapeamento_clientes[item['nome_original']] = item['nome_padronizado']
        except:
            # Se a tabela de mapeamento não existir, usar lista vazia
            mapeamento_clientes = {}
        
        # Agrupar por cliente
        clientes_data = defaultdict(float)
        total_geral = 0
        
        for item in dados:
            cliente_original = item.get('cliente', '').strip()
            
            # Usar mapeamento se disponível, senão usar o cliente original
            if cliente_original in mapeamento_clientes:
                nome_final = mapeamento_clientes[cliente_original]
            else:
                nome_final = cliente_original
                
            valor = float(item.get('valor', 0))
            clientes_data[nome_final] += valor
            total_geral += valor
        
        # Preparar dados para a tabela
        resultado = []
        for cliente, valor in clientes_data.items():
            percentual = (valor / total_geral * 100) if total_geral > 0 else 0
            resultado.append({
                'cliente': cliente,
                'valor': valor,
                'percentual': round(percentual)  # Arredondar para inteiro
            })
        
        # Ordenar por valor decrescente e pegar top N
        resultado.sort(key=lambda x: x['valor'], reverse=True)
        resultado = resultado[:limit]
        
        return jsonify({
            'success': True,
            'data': resultado,
            'total': total_geral
        })
        
    except Exception as e:
        print(f"Erro em api_geral_top_clientes: {str(e)}")
        return jsonify({'error': str(e)}), 500

@faturamento_bp.route('/api/geral/metas_mensais')
@login_required
@perfil_required('financeiro', 'faturamento')
def api_geral_metas_mensais():
    """API para buscar metas mensais de faturamento"""
    try:
        ano = request.args.get('ano', datetime.now().year)
        empresa = request.args.get('empresa', '')
        
        print(f"📊 [METAS_MENSAIS] Buscando metas para empresa: {empresa}, ano: {ano}")
        
        # Determinar tipo de meta baseado na empresa
        if empresa in ['consultoria', 'Unique Consultoria']:
            tipo_meta = 'financeiro_consultoria'
        elif empresa in ['imp/exp', 'imp_exp', 'solucoes', 'Unique Soluções']:
            tipo_meta = 'financeiro_imp_exp'
        else:
            # Para 'ambos' ou empresa não especificada, usar ambos os tipos
            tipo_meta = None
        
        print(f"📊 [METAS_MENSAIS] Tipo de meta determinado: {tipo_meta}")
        
        if tipo_meta:
            # Meta específica (consultoria ou imp/exp)
            query = supabase_admin.table('fin_metas_projecoes').select('mes, meta').eq('ano', str(ano)).eq('tipo', tipo_meta).order('mes')
            response = query.execute()
            dados_metas = response.data
            
            print(f"📊 [METAS_MENSAIS] Registros encontrados para {tipo_meta}: {len(dados_metas)}")
            
            # Organizar dados por mês
            metas_por_mes = {}
            for item in dados_metas:
                mes = int(item.get('mes', 0))
                meta = float(item.get('meta', 0))
                metas_por_mes[mes] = meta
                
        else:
            # Para 'ambos', somar consultoria + imp/exp
            query_consultoria = supabase_admin.table('fin_metas_projecoes').select('mes, meta').eq('ano', str(ano)).eq('tipo', 'financeiro_consultoria').order('mes')
            query_imp_exp = supabase_admin.table('fin_metas_projecoes').select('mes, meta').eq('ano', str(ano)).eq('tipo', 'financeiro_imp_exp').order('mes')
            
            response_consultoria = query_consultoria.execute()
            response_imp_exp = query_imp_exp.execute()
            
            print(f"📊 [METAS_MENSAIS] Registros consultoria: {len(response_consultoria.data)}")
            print(f"📊 [METAS_MENSAIS] Registros imp/exp: {len(response_imp_exp.data)}")
            
            # Organizar e somar metas por mês
            metas_por_mes = {}
            
            # Adicionar metas de consultoria
            for item in response_consultoria.data:
                mes = int(item.get('mes', 0))
                meta = float(item.get('meta', 0))
                metas_por_mes[mes] = metas_por_mes.get(mes, 0) + meta
            
            # Adicionar metas de imp/exp
            for item in response_imp_exp.data:
                mes = int(item.get('mes', 0))
                meta = float(item.get('meta', 0))
                metas_por_mes[mes] = metas_por_mes.get(mes, 0) + meta
        
        # Garantir que todos os 12 meses existam
        metas_completas = []
        for mes in range(1, 13):
            metas_completas.append({
                'mes': mes,
                'meta': metas_por_mes.get(mes, 0),
                'mes_nome': ['', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                           'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'][mes]
            })
        
        return jsonify({
            'success': True,
            'data': metas_completas,
            'ano': ano
        })
        
    except Exception as e:
        print(f"Erro em api_geral_metas_mensais: {str(e)}")
        return jsonify({'error': str(e)}), 500

@faturamento_bp.route('/api/geral/dados_hierarquicos')
@login_required
@perfil_required('financeiro', 'faturamento')
def api_geral_dados_hierarquicos():
    """API para dados hierárquicos: Meta Grupo → Centro Resultado → Categoria → Classe"""
    try:
        start_date = request.args.get('start_date', f'{datetime.now().year}-01-01')
        end_date = request.args.get('end_date', f'{datetime.now().year}-12-31')
        empresa = request.args.get('empresa', '')
        nivel = request.args.get('nivel', 'meta_grupo')  # meta_grupo, centro_resultado, categoria, classe
        parent = request.args.get('parent', '')  # Filtro do nível pai
        centro_resultado = request.args.get('centro_resultado', '')  # Filtro adicional
        cliente = request.args.get('cliente', '')  # Filtro adicional
        
        print(f"🌳 [DADOS_HIERARQUICOS] Nível: {nivel}, Parent: {parent}, Empresa: {empresa}, Centro: {centro_resultado}, Cliente: {cliente}")
        
        # Campos para seleção baseados no nível
        campos_por_nivel = {
            'meta_grupo': ['meta_grupo', 'valor'],
            'centro_resultado': ['centro_resultado', 'valor', 'meta_grupo'],
            'categoria': ['categoria', 'valor', 'centro_resultado', 'meta_grupo'],
            'classe': ['classe', 'valor', 'categoria', 'centro_resultado', 'meta_grupo']
        }
        
        # Verificar se o nível é válido
        if nivel not in campos_por_nivel:
            return jsonify({'error': 'Nível inválido'}), 400
        
        # Selecionar campos necessários
        campos = campos_por_nivel[nivel]
        query = supabase_admin.table('vw_fin_faturamento_anual_tratado').select(','.join(campos))
        
        # Aplicar filtros de data
        if start_date:
            query = query.gte('data', start_date)
        if end_date:
            query = query.lte('data', end_date)
        
        # Filtro por meta_grupo baseado no parâmetro empresa
        if empresa and empresa.strip() and empresa != 'ambos':
            if empresa.lower() in ['consultoria']:
                query = query.eq('meta_grupo', 'Consultoria')
            elif empresa.lower() in ['imp/exp', 'imp_exp']:
                query = query.eq('meta_grupo', 'IMP/EXP')
        
        # Aplicar filtro do nível pai (drill-down)
        if parent and parent.strip():
            if nivel == 'centro_resultado':
                query = query.eq('meta_grupo', parent)
            elif nivel == 'categoria':
                query = query.eq('centro_resultado', parent)
            elif nivel == 'classe':
                query = query.eq('categoria', parent)
        
        # Aplicar filtro de centro de resultado (se fornecido)
        if centro_resultado and centro_resultado.strip():
            query = query.eq('centro_resultado', centro_resultado)
        
        # Aplicar filtro de cliente (se fornecido)
        if cliente and cliente.strip():
            query = query.eq('cliente', cliente)
        
        response = query.execute()
        dados = response.data
        
        # Agrupar dados pelo campo principal do nível
        campo_principal = nivel
        agrupados = {}
        total_geral = 0
        
        for item in dados:
            chave = item.get(campo_principal, 'N/A')
            valor = float(item.get('valor', 0))
            
            if chave not in agrupados:
                agrupados[chave] = {
                    'nome': chave,
                    'valor': 0,
                    'tem_filhos': True  # Todos os níveis exceto classe podem ter filhos
                }
            
            agrupados[chave]['valor'] += valor
            total_geral += valor
        
        # Se for o nível classe, não tem filhos
        if nivel == 'classe':
            for item in agrupados.values():
                item['tem_filhos'] = False
        
        # Converter para lista e ordenar por valor
        resultado = list(agrupados.values())
        resultado.sort(key=lambda x: x['valor'], reverse=True)
        
        # Calcular percentuais
        for item in resultado:
            if total_geral > 0:
                item['percentual'] = (item['valor'] / total_geral) * 100
            else:
                item['percentual'] = 0
        
        print(f"🌳 [DADOS_HIERARQUICOS] Retornando {len(resultado)} itens para nível {nivel}")
        
        return jsonify({
            'success': True,
            'data': resultado,
            'nivel': nivel,
            'parent': parent,
            'total': total_geral,
            'tem_nivel_inferior': nivel != 'classe'
        })
        
    except Exception as e:
        print(f"❌ [DADOS_HIERARQUICOS] Erro: {str(e)}")
        return jsonify({'error': str(e)}), 500

@faturamento_bp.route('/api/geral/aderencia_meta')
@login_required
@perfil_required('financeiro', 'faturamento')
def api_geral_aderencia_meta():
    """API para calcular aderência à meta dinâmica baseada no filtro de empresa (consultoria ou imp/exp)"""
    try:
        empresa = request.args.get('empresa', 'ambos')
        ano = request.args.get('ano', datetime.now().year)
        centro_resultado = request.args.get('centro_resultado', '')
        cliente = request.args.get('cliente', '')
        
        print(f"🎯 [ADERENCIA_META] Calculando para empresa: {empresa}, ano: {ano}, CR: {centro_resultado}, Cliente: {cliente}")
        
        # Determinar tipo de meta baseado na empresa
        if empresa in ['consultoria', 'Unique Consultoria']:
            tipo_meta = 'financeiro_consultoria'
            meta_grupo_filtro = 'Consultoria'
        elif empresa in ['imp/exp', 'imp_exp', 'solucoes', 'Unique Soluções']:
            tipo_meta = 'financeiro_imp_exp'
            meta_grupo_filtro = 'IMP/EXP'
        else:
            # Para 'ambos', usar ambos os tipos e somar
            tipo_meta = None
            meta_grupo_filtro = None
        
        # Obter mês atual para calcular período acumulado
        mes_atual = datetime.now().month
        
        # 1. Buscar metas do ano completo (12 meses) para comparação
        if tipo_meta:
            # Meta específica (consultoria ou imp/exp) - ano completo
            query_meta = supabase_admin.table('fin_metas_projecoes').select('mes, meta').eq('ano', str(ano)).eq('tipo', tipo_meta)
            response_meta = query_meta.execute()
            dados_metas = response_meta.data
            
            meta_anual_total = sum(float(item.get('meta', 0)) for item in dados_metas)
            
            # Meta acumulada até o mês atual (para cálculo de aderência)
            meta_acumulada = sum(float(item.get('meta', 0)) for item in dados_metas if int(item.get('mes', 0)) <= mes_atual)
            
        else:
            # Para 'ambos', somar consultoria + imp/exp - ano completo
            query_consultoria = supabase_admin.table('fin_metas_projecoes').select('mes, meta').eq('ano', str(ano)).eq('tipo', 'financeiro_consultoria')
            query_imp_exp = supabase_admin.table('fin_metas_projecoes').select('mes, meta').eq('ano', str(ano)).eq('tipo', 'financeiro_imp_exp')
            
            response_consultoria = query_consultoria.execute()
            response_imp_exp = query_imp_exp.execute()
            
            # Total anual
            meta_consultoria_anual = sum(float(item.get('meta', 0)) for item in response_consultoria.data)
            meta_imp_exp_anual = sum(float(item.get('meta', 0)) for item in response_imp_exp.data)
            meta_anual_total = meta_consultoria_anual + meta_imp_exp_anual
            
            # Acumulado até mês atual
            meta_consultoria_acumulada = sum(float(item.get('meta', 0)) for item in response_consultoria.data if int(item.get('mes', 0)) <= mes_atual)
            meta_imp_exp_acumulada = sum(float(item.get('meta', 0)) for item in response_imp_exp.data if int(item.get('mes', 0)) <= mes_atual)
            meta_acumulada = meta_consultoria_acumulada + meta_imp_exp_acumulada
        
        print(f"🎯 [ADERENCIA_META] Meta anual total: R$ {meta_anual_total:,.2f}")
        print(f"🎯 [ADERENCIA_META] Meta acumulada até mês {mes_atual}: R$ {meta_acumulada:,.2f}")
        
        # 2. Buscar faturamento realizado do ano até o mês atual
        # Calcular último dia do mês atual para evitar erro de data inválida
        ultimo_dia_mes = calendar.monthrange(int(ano), mes_atual)[1]
        data_fim = f'{ano}-{mes_atual:02d}-{ultimo_dia_mes:02d}'
        
        # Usar a view atualizada com meta_grupo
        query_faturamento = supabase_admin.table('vw_fin_faturamento_anual_tratado').select('valor, data, meta_grupo, centro_resultado, cliente').gte('data', f'{ano}-01-01').lte('data', data_fim)
        
        # Aplicar filtro de meta_grupo se não for 'ambos'
        if meta_grupo_filtro:
            query_faturamento = query_faturamento.eq('meta_grupo', meta_grupo_filtro)
            
        if centro_resultado:
            query_faturamento = query_faturamento.eq('centro_resultado', centro_resultado)
            
        if cliente:
            query_faturamento = query_faturamento.eq('cliente', cliente)
            
        response_faturamento = query_faturamento.execute()
        dados_faturamento = response_faturamento.data
        
        realizado_acumulado = sum(float(item.get('valor', 0)) for item in dados_faturamento)
        
        print(f"🎯 [ADERENCIA_META] Realizado acumulado até mês {mes_atual}: R$ {realizado_acumulado:,.2f}")
        
        # 3. Calcular aderência
        if meta_acumulada > 0:
            aderencia_percentual = (realizado_acumulado / meta_acumulada) * 100
            aderencia_valor = realizado_acumulado - meta_acumulada
            status = 'atingiu' if aderencia_percentual >= 100 else 'abaixo'
        else:
            aderencia_percentual = 0
            aderencia_valor = realizado_acumulado
            status = 'sem_dados'
        
        print(f"🎯 [ADERENCIA_META] Aderência: {aderencia_percentual:.1f}% ({status})")
        
        return jsonify({
            'success': True,
            'data': {
                'meta_anual_total': meta_anual_total,
                'meta_acumulada': meta_acumulada,
                'faturamento_acumulado': realizado_acumulado,
                'aderencia_percentual': aderencia_percentual,
                'aderencia_valor': aderencia_valor,
                'status': status,
                'mes_atual': mes_atual,
                'ano': ano,
                'empresa': empresa,
                'tipo_meta': tipo_meta or 'combinado'
            }
        })
        
    except Exception as e:
        print(f"❌ [ADERENCIA_META] Erro: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@faturamento_bp.route('/api/geral/setor/<setor>')
@login_required
@perfil_required('financeiro', 'faturamento')
def api_geral_setor_dinamico(setor):
    """API dinâmica para dados completos de um setor específico"""
    try:
        start_date = request.args.get('start_date', f'{datetime.now().year}-01-01')
        end_date = request.args.get('end_date', f'{datetime.now().year}-12-31')
        centro_resultado = request.args.get('centro_resultado', '')
        cliente = request.args.get('cliente', '')
        empresa = request.args.get('empresa', '')
        
        # Definir filtro de classe com base no setor
        filtro_classe = ''
        if setor == 'importacao':
            filtro_classe = 'IMP'
        elif setor == 'consultoria':
            filtro_classe = 'CONS'
        elif setor == 'exportacao':
            filtro_classe = 'EXP'
        else:
            return jsonify({'success': False, 'message': 'Setor inválido'}), 400
        
        # Buscar dados de faturamento do setor no período
        # Usar a view tratada se possível, ou a tabela original
        try:
            query = supabase_admin.table('vw_fin_faturamento_anual_tratado').select('*')
        except:
            query = supabase_admin.table('fin_faturamento_anual').select('*')
            
        if filtro_classe:
            query = query.ilike('classe', f'%{filtro_classe}%')
            
        query = query.gte('data', start_date).lte('data', end_date)
        
        # Aplicar filtros adicionais
        if centro_resultado:
            query = query.eq('centro_resultado', centro_resultado)
        if cliente:
            query = query.eq('cliente', cliente)
            
        # Filtro por meta_grupo baseado no parâmetro empresa (se aplicável)
        if empresa and empresa.strip() and empresa != 'ambos':
            if empresa.lower() in ['consultoria']:
                query = query.eq('meta_grupo', 'Consultoria')
            elif empresa.lower() in ['imp/exp', 'imp_exp', 'importacao', 'exportacao']:
                query = query.eq('meta_grupo', 'IMP/EXP')
        
        response = query.execute()
        dados_faturamento = response.data
        
        # Calcular faturamento total do setor
        total_setor = sum(float(item['valor']) for item in dados_faturamento)
        
        # Buscar faturamento total da empresa no mesmo período (para participação)
        try:
            total_query = supabase_admin.table('vw_fin_faturamento_anual_tratado').select('valor')
        except:
            total_query = supabase_admin.table('fin_faturamento_anual').select('valor')
            
        total_query = total_query.gte('data', start_date).lte('data', end_date)
        
        if centro_resultado:
            total_query = total_query.eq('centro_resultado', centro_resultado)
        if cliente:
            total_query = total_query.eq('cliente', cliente)
        if empresa and empresa.strip() and empresa != 'ambos':
            if empresa.lower() in ['consultoria']:
                total_query = total_query.eq('meta_grupo', 'Consultoria')
            elif empresa.lower() in ['imp/exp', 'imp_exp', 'importacao', 'exportacao']:
                total_query = total_query.eq('meta_grupo', 'IMP/EXP')
            
        total_response = total_query.execute()
        total_empresa = sum(float(item['valor']) for item in total_response.data)
        
        # Calcular participação percentual
        pct_participacao = (total_setor / total_empresa * 100) if total_empresa > 0 else 0
        
        # Buscar dados do ano anterior para calcular crescimento
        # Calcular datas do ano anterior
        try:
            dt_start = datetime.strptime(start_date, '%Y-%m-%d')
            dt_end = datetime.strptime(end_date, '%Y-%m-%d')
            
            start_prev = dt_start.replace(year=dt_start.year - 1).strftime('%Y-%m-%d')
            # Handle leap year for end date
            if dt_end.month == 2 and dt_end.day == 29:
                end_prev = dt_end.replace(year=dt_end.year - 1, day=28).strftime('%Y-%m-%d')
            else:
                end_prev = dt_end.replace(year=dt_end.year - 1).strftime('%Y-%m-%d')
        except:
            # Fallback
            start_prev = f"{int(start_date[:4])-1}-01-01"
            end_prev = f"{int(end_date[:4])-1}-12-31"
        
        try:
            query_anterior = supabase_admin.table('vw_fin_faturamento_anual_tratado').select('valor')
        except:
            query_anterior = supabase_admin.table('fin_faturamento_anual').select('valor')
            
        if filtro_classe:
            query_anterior = query_anterior.ilike('classe', f'%{filtro_classe}%')
            
        query_anterior = query_anterior.gte('data', start_prev).lte('data', end_prev)
        
        if centro_resultado:
            query_anterior = query_anterior.eq('centro_resultado', centro_resultado)
        if cliente:
            query_anterior = query_anterior.eq('cliente', cliente)
        if empresa and empresa.strip() and empresa != 'ambos':
            if empresa.lower() in ['consultoria']:
                query_anterior = query_anterior.eq('meta_grupo', 'Consultoria')
            elif empresa.lower() in ['imp/exp', 'imp_exp', 'importacao', 'exportacao']:
                query_anterior = query_anterior.eq('meta_grupo', 'IMP/EXP')
        
        response_anterior = query_anterior.execute()
        total_anterior = sum(float(item['valor']) for item in response_anterior.data)
        
        # Calcular crescimento
        crescimento = 0
        if total_anterior > 0:
            crescimento = ((total_setor - total_anterior) / total_anterior) * 100
        
        # Agrupar faturamento mensal
        faturamento_mensal = defaultdict(float)
        melhor_mes_valor = 0
        melhor_mes_nome = ''
        
        for item in dados_faturamento:
            data_item = datetime.strptime(item['data'], '%Y-%m-%d')
            mes_num = data_item.month
            mes_nome = ['', 'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
                       'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'][mes_num]
            
            faturamento_mensal[mes_nome] += float(item['valor'])
            
            # Identificar melhor mês
            if faturamento_mensal[mes_nome] > melhor_mes_valor:
                melhor_mes_valor = faturamento_mensal[mes_nome]
                melhor_mes_nome = mes_nome
        
        # Preparar dados mensais para o gráfico
        dados_mensais = []
        for mes_nome in ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
                        'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']:
            dados_mensais.append({
                'mes': mes_nome,
                'valor': faturamento_mensal.get(mes_nome, 0)
            })
        
        # Buscar mapeamento de clientes
        try:
            mapeamento_response = supabase_admin.table('fin_clientes_mapeamento').select('nome_original, nome_padronizado').execute()
            mapeamento_clientes = {}
            if mapeamento_response.data:
                for item in mapeamento_response.data:
                    mapeamento_clientes[item['nome_original']] = item['nome_padronizado']
        except:
            mapeamento_clientes = {}
        
        # Ranking de clientes
        clientes_ranking = defaultdict(float)
        for item in dados_faturamento:
            cliente_original = item.get('cliente', 'Não identificado')
            cliente_padronizado = mapeamento_clientes.get(cliente_original, cliente_original)
            clientes_ranking[cliente_padronizado] += float(item['valor'])
        
        # Converter para lista e ordenar (top 10)
        ranking_lista = []
        for cliente_nome, valor in clientes_ranking.items():
            participacao = (valor / total_setor * 100) if total_setor > 0 else 0
            ranking_lista.append({
                'id': cliente_nome.lower().replace(' ', '_'),  # ID simples para drill-down
                'nome': cliente_nome,
                'valor': valor,
                'participacao': participacao
            })
        
        ranking_lista.sort(key=lambda x: x['valor'], reverse=True)
        ranking_lista = ranking_lista[:10]  # Top 10
        
        return jsonify({
            'success': True,
            'data': {
                'faturamento_total': total_setor,
                'participacao_percentual': pct_participacao,
                'crescimento_percentual': crescimento,
                'melhor_mes': {
                    'mes': melhor_mes_nome,
                    'valor': melhor_mes_valor
                },
                'dados_mensais': dados_mensais,
                'ranking_clientes': ranking_lista
            }
        })
        
    except Exception as e:
        print(f"Erro em api_geral_setor_dinamico: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@faturamento_bp.route('/api/geral/cliente/<cliente_id>/detalhes')
@login_required
@perfil_required('financeiro', 'faturamento')
def api_cliente_detalhes(cliente_id):
    """API para dados detalhados de um cliente específico"""
    try:
        setor = request.args.get('setor', 'importacao')
        start_date = request.args.get('start_date', f'{datetime.now().year}-01-01')
        end_date = request.args.get('end_date', f'{datetime.now().year}-12-31')
        centro_resultado = request.args.get('centro_resultado', '')
        empresa = request.args.get('empresa', '')
        
        # Definir filtro de classe com base no setor
        filtro_classe = ''
        if setor == 'importacao':
            filtro_classe = 'IMP'
        elif setor == 'consultoria':
            filtro_classe = 'CONS'
        elif setor == 'exportacao':
            filtro_classe = 'EXP'
        
        # Buscar mapeamento de clientes para encontrar o nome real
        try:
            mapeamento_response = supabase_admin.table('fin_clientes_mapeamento').select('nome_original, nome_padronizado').execute()
            mapeamento_clientes = {}
            nome_cliente = None
            
            if mapeamento_response.data:
                for item in mapeamento_response.data:
                    mapeamento_clientes[item['nome_original']] = item['nome_padronizado']
                    # Encontrar o nome do cliente baseado no ID
                    if item['nome_padronizado'].lower().replace(' ', '_') == cliente_id:
                        nome_cliente = item['nome_padronizado']
        except:
            nome_cliente = None
        
        if not nome_cliente:
            # Se não encontrar no mapeamento, tentar encontrar diretamente
            nome_cliente = cliente_id.replace('_', ' ').title()
        
        # Buscar dados de faturamento do cliente no setor
        try:
            query = supabase_admin.table('vw_fin_faturamento_anual_tratado').select('*')
        except:
            query = supabase_admin.table('fin_faturamento_anual').select('*')
            
        if filtro_classe:
            query = query.ilike('classe', f'%{filtro_classe}%')
            
        query = query.gte('data', start_date).lte('data', end_date)
        # Buscar por nome original ou padronizado
        query = query.or_(f'cliente.ilike.%{nome_cliente}%')
        
        # Aplicar filtro de centro de resultado
        if centro_resultado:
            query = query.eq('centro_resultado', centro_resultado)
            
        # Filtro por meta_grupo baseado no parâmetro empresa
        if empresa and empresa.strip() and empresa != 'ambos':
            if empresa.lower() in ['consultoria']:
                query = query.eq('meta_grupo', 'Consultoria')
            elif empresa.lower() in ['imp/exp', 'imp_exp', 'importacao', 'exportacao']:
                query = query.eq('meta_grupo', 'IMP/EXP')
        
        response = query.execute()
        dados_cliente = response.data
        
        # Calcular faturamento total do cliente
        total_cliente = sum(float(item['valor']) for item in dados_cliente)
        
        # Buscar total do setor para calcular participação
        try:
            query_setor = supabase_admin.table('vw_fin_faturamento_anual_tratado').select('valor')
        except:
            query_setor = supabase_admin.table('fin_faturamento_anual').select('valor')
            
        if filtro_classe:
            query_setor = query_setor.ilike('classe', f'%{filtro_classe}%')
            
        query_setor = query_setor.gte('data', start_date).lte('data', end_date)
        
        if centro_resultado:
            query_setor = query_setor.eq('centro_resultado', centro_resultado)
        if empresa and empresa.strip() and empresa != 'ambos':
            if empresa.lower() in ['consultoria']:
                query_setor = query_setor.eq('meta_grupo', 'Consultoria')
            elif empresa.lower() in ['imp/exp', 'imp_exp', 'importacao', 'exportacao']:
                query_setor = query_setor.eq('meta_grupo', 'IMP/EXP')
        
        response_setor = query_setor.execute()
        total_setor = sum(float(item['valor']) for item in response_setor.data)
        
        # Calcular participação
        participacao_setor = (total_cliente / total_setor * 100) if total_setor > 0 else 0
        
        # Dados do ano anterior para calcular crescimento
        try:
            dt_start = datetime.strptime(start_date, '%Y-%m-%d')
            dt_end = datetime.strptime(end_date, '%Y-%m-%d')
            
            start_prev = dt_start.replace(year=dt_start.year - 1).strftime('%Y-%m-%d')
            # Handle leap year for end date
            if dt_end.month == 2 and dt_end.day == 29:
                end_prev = dt_end.replace(year=dt_end.year - 1, day=28).strftime('%Y-%m-%d')
            else:
                end_prev = dt_end.replace(year=dt_end.year - 1).strftime('%Y-%m-%d')
        except:
            # Fallback
            start_prev = f"{int(start_date[:4])-1}-01-01"
            end_prev = f"{int(end_date[:4])-1}-12-31"
        
        try:
            query_anterior = supabase_admin.table('vw_fin_faturamento_anual_tratado').select('valor')
        except:
            query_anterior = supabase_admin.table('fin_faturamento_anual').select('valor')
            
        if filtro_classe:
            query_anterior = query_anterior.ilike('classe', f'%{filtro_classe}%')
            
        query_anterior = query_anterior.gte('data', start_prev).lte('data', end_prev)
        query_anterior = query_anterior.or_(f'cliente.ilike.%{nome_cliente}%')
        
        if centro_resultado:
            query_anterior = query_anterior.eq('centro_resultado', centro_resultado)
        if empresa and empresa.strip() and empresa != 'ambos':
            if empresa.lower() in ['consultoria']:
                query_anterior = query_anterior.eq('meta_grupo', 'Consultoria')
            elif empresa.lower() in ['imp/exp', 'imp_exp', 'importacao', 'exportacao']:
                query_anterior = query_anterior.eq('meta_grupo', 'IMP/EXP')
        
        response_anterior = query_anterior.execute()
        total_anterior = sum(float(item['valor']) for item in response_anterior.data)
        
        # Calcular crescimento
        crescimento = 0
        if total_anterior > 0:
            crescimento = ((total_cliente - total_anterior) / total_anterior) * 100
        
        # Agrupar faturamento mensal
        faturamento_mensal = defaultdict(float)
        
        for item in dados_cliente:
            data_item = datetime.strptime(item['data'], '%Y-%m-%d')
            mes_nome = ['', 'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
                       'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'][data_item.month]
            faturamento_mensal[mes_nome] += float(item['valor'])
        
        # Preparar dados mensais para o gráfico
        dados_mensais = []
        for mes_nome in ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
                        'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']:
            dados_mensais.append({
                'mes': mes_nome,
                'valor': faturamento_mensal.get(mes_nome, 0)
            })
        
        # Breakdown por Centro de Resultado → Categoria → Classe
        breakdown_centro = defaultdict(lambda: {
            'valor': 0,
            'categorias': defaultdict(lambda: {
                'valor': 0,
                'classes': defaultdict(float)
            })
        })
        
        for item in dados_cliente:
            centro = item.get('centro_resultado', 'Não identificado')
            categoria = item.get('categoria', 'Não identificada')
            classe = item.get('classe', 'Não identificada')
            valor = float(item['valor'])
            
            breakdown_centro[centro]['valor'] += valor
            breakdown_centro[centro]['categorias'][categoria]['valor'] += valor
            breakdown_centro[centro]['categorias'][categoria]['classes'][classe] += valor
        
        # Converter para estrutura mais amigável
        breakdown_final = []
        for centro, dados in breakdown_centro.items():
            centro_item = {
                'centro_resultado': centro,
                'valor': dados['valor'],
                'participacao': (dados['valor'] / total_cliente * 100) if total_cliente > 0 else 0,
                'categorias': []
            }
            
            for categoria, cat_dados in dados['categorias'].items():
                categoria_item = {
                    'categoria': categoria,
                    'valor': cat_dados['valor'],
                    'participacao': (cat_dados['valor'] / dados['valor'] * 100) if dados['valor'] > 0 else 0,
                    'classes': []
                }
                
                for classe, valor in cat_dados['classes'].items():
                    categoria_item['classes'].append({
                        'classe': classe,
                        'valor': valor,
                        'participacao': (valor / cat_dados['valor'] * 100) if cat_dados['valor'] > 0 else 0
                    })
                
                # Ordenar classes por valor
                categoria_item['classes'].sort(key=lambda x: x['valor'], reverse=True)
                centro_item['categorias'].append(categoria_item)
            
            # Ordenar categorias por valor
            centro_item['categorias'].sort(key=lambda x: x['valor'], reverse=True)
            breakdown_final.append(centro_item)
        
        # Ordenar centros por valor
        breakdown_final.sort(key=lambda x: x['valor'], reverse=True)
        
        return jsonify({
            'success': True,
            'data': {
                'cliente_nome': nome_cliente,
                'faturamento_total': total_cliente,
                'participacao_setor': participacao_setor,
                'crescimento_percentual': crescimento,
                'dados_mensais': dados_mensais,
                'breakdown_centro_resultado': breakdown_final
            }
        })
        
    except Exception as e:
        print(f"Erro em api_cliente_detalhes: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500
