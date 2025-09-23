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

@faturamento_bp.route('/api/geral/kpis')
@login_required
@perfil_required('financeiro', 'faturamento')
def api_geral_kpis():
    """API para KPIs da Visão Geral de Faturamento"""
    try:
        ano = request.args.get('ano', datetime.now().year)
        
        # Buscar dados de faturamento do ano
        response = supabase_admin.table('fin_faturamento_anual').select('*').gte('data', f'{ano}-01-01').lte('data', f'{ano}-12-31').execute()
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
        
        # Buscar dados de faturamento do ano atual
        query_atual = supabase_admin.table('fin_faturamento_anual').select('*').gte('data', f'{ano}-01-01').lte('data', f'{ano}-12-31')
        if empresa and empresa.strip() and empresa != 'ambos':
            query_atual = query_atual.eq('empresa', empresa)
        response_atual = query_atual.execute()
        dados_atual = response_atual.data
        
        # Buscar dados de faturamento do ano anterior
        ano_anterior = int(ano) - 1
        query_anterior = supabase_admin.table('fin_faturamento_anual').select('*').gte('data', f'{ano_anterior}-01-01').lte('data', f'{ano_anterior}-12-31')
        if empresa and empresa.strip() and empresa != 'ambos':
            query_anterior = query_anterior.eq('empresa', empresa)
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
    """API para gráficos de proporção da Visão Geral"""
    try:
        ano = request.args.get('ano', datetime.now().year)
        
        # Buscar dados de faturamento do ano
        response = supabase_admin.table('fin_faturamento_anual').select('*').gte('data', f'{ano}-01-01').lte('data', f'{ano}-12-31').execute()
        dados_faturamento = response.data
        
        # Calcular totais por setor
        total_importacao = 0
        total_consultoria = 0
        total_exportacao = 0
        
        for item in dados_faturamento:
            classe = item.get('classe', '').upper()
            valor = float(item['valor'])
            
            if 'IMP' in classe or 'IMPORT' in classe:
                total_importacao += valor
            elif 'CONS' in classe or 'CONSULT' in classe:
                total_consultoria += valor
            elif 'EXP' in classe or 'EXPORT' in classe:
                total_exportacao += valor
        
        total_geral = total_importacao + total_consultoria + total_exportacao
        
        # Calcular percentuais
        pct_importacao = (total_importacao / total_geral * 100) if total_geral > 0 else 0
        pct_consultoria = (total_consultoria / total_geral * 100) if total_geral > 0 else 0
        pct_exportacao = (total_exportacao / total_geral * 100) if total_geral > 0 else 0
        
        return jsonify({
            'setores': {
                'importacao': {
                    'valor': total_importacao,
                    'percentual': pct_importacao
                },
                'consultoria': {
                    'valor': total_consultoria,
                    'percentual': pct_consultoria
                },
                'exportacao': {
                    'valor': total_exportacao,
                    'percentual': pct_exportacao
                }
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@faturamento_bp.route('/api/geral/comparativo_anos')
@login_required
@perfil_required('financeiro', 'faturamento')
def api_geral_comparativo_anos():
    """API para comparativo anual usando tabela fin_faturamento_anual"""
    try:
        empresa = request.args.get('empresa', '')
        
        # Buscar dados da tabela base que tem a coluna empresa
        query = supabase_admin.table('fin_faturamento_anual').select('data, valor, empresa')
        
        # Aplicar filtro de empresa se especificado
        if empresa and empresa.strip() and empresa != 'ambos':
            query = query.eq('empresa', empresa)
        
        response = query.execute()
        dados = response.data
        
        # Log para debug
        print(f"📊 Comparativo anos - Empresa: {empresa}, Registros: {len(dados)}")
        
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
        
        # Buscar dados com centro_resultado e categoria
        query = supabase_admin.table('fin_faturamento_anual').select('centro_resultado, categoria, valor')
        
        # Aplicar filtros
        if start_date:
            query = query.gte('data', start_date)
        if end_date:
            query = query.lte('data', end_date)
        if empresa and empresa.strip():
            query = query.eq('empresa', empresa)
            
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
        
        # Buscar dados de faturamento
        query = supabase_admin.table('fin_faturamento_anual').select('centro_resultado, valor')
        
        # Aplicar filtros
        if start_date:
            query = query.gte('data', start_date)
        if end_date:
            query = query.lte('data', end_date)
        if empresa and empresa.strip():
            query = query.eq('empresa', empresa)
            
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
    """API para gráfico de rosca - Faturamento por Categoria usando tabela base"""
    try:
        start_date = request.args.get('start_date', f'{datetime.now().year}-01-01')
        end_date = request.args.get('end_date', f'{datetime.now().year}-12-31')
        empresa = request.args.get('empresa', '')
        
        # Usar a tabela base que tem a coluna empresa
        query = supabase_admin.table('fin_faturamento_anual').select('categoria, valor, empresa')
        
        # Aplicar filtros
        if start_date:
            query = query.gte('data', start_date)
        if end_date:
            query = query.lte('data', end_date)
        if empresa and empresa.strip() and empresa != 'ambos':
            query = query.eq('empresa', empresa)
            
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
        
        if not centro_resultado:
            return jsonify({'error': 'Centro de resultado é obrigatório'}), 400
        
        # Usar a view tratada que tem a hierarquia correta
        try:
            query = supabase_admin.table('vw_fin_faturamento_anual_tratado').select('categoria, valor, centro_resultado')
        except:
            # Fallback para tabela original
            query = supabase_admin.table('fin_faturamento_anual').select('categoria, valor, centro_resultado')
        
        # Filtrar por centro de resultado
        query = query.eq('centro_resultado', centro_resultado)
        
        # Aplicar filtros de data
        if start_date:
            query = query.gte('data', start_date)
        if end_date:
            query = query.lte('data', end_date)
            
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
    """API para tabela de top clientes usando campo 'cliente'"""
    try:
        start_date = request.args.get('start_date', f'{datetime.now().year}-01-01')
        end_date = request.args.get('end_date', f'{datetime.now().year}-12-31')
        empresa = request.args.get('empresa', '')
        limit = int(request.args.get('limit', 10))
        
        # Buscar dados de faturamento
        query = supabase_admin.table('fin_faturamento_anual').select('cliente, valor')
        
        # Aplicar filtros
        if start_date:
            query = query.gte('data', start_date)
        if end_date:
            query = query.lte('data', end_date)
        if empresa and empresa.strip():
            query = query.eq('empresa', empresa)
            
        response = query.execute()
        dados = response.data
        
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
                'percentual': percentual
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
        
        # Determinar tipo de meta baseado na empresa
        if empresa == 'Unique Consultoria':
            tipo_meta = 'financeiro_consultoria'
        elif empresa == 'Unique Soluções':
            tipo_meta = 'financeiro_solucoes'
        else:
            # Para 'ambos' ou empresa não especificada, usar ambos os tipos
            tipo_meta = None
        
        if tipo_meta:
            # Meta específica (consultoria ou soluções)
            query = supabase_admin.table('fin_metas_projecoes').select('mes, meta').eq('ano', str(ano)).eq('tipo', tipo_meta).order('mes')
            response = query.execute()
            dados_metas = response.data
            
            # Organizar dados por mês
            metas_por_mes = {}
            for item in dados_metas:
                mes = int(item.get('mes', 0))
                meta = float(item.get('meta', 0))
                metas_por_mes[mes] = meta
        else:
            # Para 'ambos', somar consultoria + soluções
            query_consultoria = supabase_admin.table('fin_metas_projecoes').select('mes, meta').eq('ano', str(ano)).eq('tipo', 'financeiro_consultoria').order('mes')
            query_solucoes = supabase_admin.table('fin_metas_projecoes').select('mes, meta').eq('ano', str(ano)).eq('tipo', 'financeiro_solucoes').order('mes')
            
            response_consultoria = query_consultoria.execute()
            response_solucoes = query_solucoes.execute()
            
            # Organizar e somar metas por mês
            metas_por_mes = {}
            
            # Adicionar metas de consultoria
            for item in response_consultoria.data:
                mes = int(item.get('mes', 0))
                meta = float(item.get('meta', 0))
                metas_por_mes[mes] = metas_por_mes.get(mes, 0) + meta
            
            # Adicionar metas de soluções
            for item in response_solucoes.data:
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

@faturamento_bp.route('/api/geral/aderencia_meta')
@login_required
@perfil_required('financeiro', 'faturamento')
def api_geral_aderencia_meta():
    """API para calcular aderência à meta dinâmica baseada no filtro de empresa (consultoria ou soluções)"""
    try:
        empresa = request.args.get('empresa', 'ambos')
        ano = request.args.get('ano', datetime.now().year)
        
        print(f"🎯 [ADERENCIA_META] Calculando para empresa: {empresa}, ano: {ano}")
        
        # Determinar tipo de meta baseado na empresa
        if empresa in ['consultoria', 'Unique Consultoria']:
            tipo_meta = 'financeiro_consultoria'
            empresa_filtro = 'Unique Consultoria'
        elif empresa in ['solucoes', 'Unique Soluções']:
            tipo_meta = 'financeiro_solucoes'
            empresa_filtro = 'Unique Soluções'
        else:
            # Para 'ambos', usar ambos os tipos e somar
            tipo_meta = None
            empresa_filtro = None
        
        # Obter mês atual para calcular período acumulado
        mes_atual = datetime.now().month
        
        # 1. Buscar metas do ano até o mês atual
        if tipo_meta:
            # Meta específica (consultoria ou soluções)
            query_meta = supabase_admin.table('fin_metas_projecoes').select('mes, meta').eq('ano', str(ano)).eq('tipo', tipo_meta).lte('mes', f'{mes_atual:02d}')
            response_meta = query_meta.execute()
            dados_metas = response_meta.data
            
            meta_acumulada = sum(float(item.get('meta', 0)) for item in dados_metas)
            
        else:
            # Para 'ambos', somar consultoria + soluções
            query_consultoria = supabase_admin.table('fin_metas_projecoes').select('mes, meta').eq('ano', str(ano)).eq('tipo', 'financeiro_consultoria').lte('mes', f'{mes_atual:02d}')
            query_solucoes = supabase_admin.table('fin_metas_projecoes').select('mes, meta').eq('ano', str(ano)).eq('tipo', 'financeiro_solucoes').lte('mes', f'{mes_atual:02d}')
            
            response_consultoria = query_consultoria.execute()
            response_solucoes = query_solucoes.execute()
            
            meta_consultoria = sum(float(item.get('meta', 0)) for item in response_consultoria.data)
            meta_solucoes = sum(float(item.get('meta', 0)) for item in response_solucoes.data)
            meta_acumulada = meta_consultoria + meta_solucoes
        
        print(f"🎯 [ADERENCIA_META] Meta acumulada até mês {mes_atual}: R$ {meta_acumulada:,.2f}")
        
        # 2. Buscar faturamento realizado do ano até o mês atual
        # Calcular último dia do mês atual para evitar erro de data inválida
        ultimo_dia_mes = calendar.monthrange(int(ano), mes_atual)[1]
        data_fim = f'{ano}-{mes_atual:02d}-{ultimo_dia_mes:02d}'
        
        query_faturamento = supabase_admin.table('fin_faturamento_anual').select('valor, data, empresa').gte('data', f'{ano}-01-01').lte('data', data_fim)
        
        # Aplicar filtro de empresa se não for 'ambos'
        if empresa_filtro:
            query_faturamento = query_faturamento.eq('empresa', empresa_filtro)
            
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
        ano = request.args.get('ano', datetime.now().year)
        ano = int(ano)
        
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
        
        # Período do ano especificado
        inicio = f'{ano}-01-01'
        fim = f'{ano}-12-31'
        
        # Buscar dados de faturamento do setor no ano
        query = supabase_admin.table('fin_faturamento_anual').select('*')
        if filtro_classe:
            query = query.ilike('classe', f'%{filtro_classe}%')
        query = query.gte('data', inicio).lte('data', fim)
        
        response = query.execute()
        dados_faturamento = response.data
        
        # Calcular faturamento total do setor
        total_setor = sum(float(item['valor']) for item in dados_faturamento)
        
        # Buscar faturamento total da empresa no mesmo período
        total_query = supabase_admin.table('fin_faturamento_anual').select('valor')
        total_query = total_query.gte('data', inicio).lte('data', fim)
        total_response = total_query.execute()
        total_empresa = sum(float(item['valor']) for item in total_response.data)
        
        # Calcular participação percentual
        pct_participacao = (total_setor / total_empresa * 100) if total_empresa > 0 else 0
        
        # Buscar dados do ano anterior para calcular crescimento
        inicio_anterior = f'{ano-1}-01-01'
        fim_anterior = f'{ano-1}-12-31'
        
        query_anterior = supabase_admin.table('fin_faturamento_anual').select('valor')
        if filtro_classe:
            query_anterior = query_anterior.ilike('classe', f'%{filtro_classe}%')
        query_anterior = query_anterior.gte('data', inicio_anterior).lte('data', fim_anterior)
        
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
        mapeamento_response = supabase_admin.table('fin_clientes_mapeamento').select('nome_original, nome_padronizado').execute()
        mapeamento_clientes = {}
        if mapeamento_response.data:
            for item in mapeamento_response.data:
                mapeamento_clientes[item['nome_original']] = item['nome_padronizado']
        
        # Ranking de clientes
        clientes_ranking = defaultdict(float)
        for item in dados_faturamento:
            cliente_original = item.get('cliente', 'Não identificado')
            cliente_padronizado = mapeamento_clientes.get(cliente_original, cliente_original)
            clientes_ranking[cliente_padronizado] += float(item['valor'])
        
        # Converter para lista e ordenar (top 10)
        ranking_lista = []
        for cliente, valor in clientes_ranking.items():
            participacao = (valor / total_setor * 100) if total_setor > 0 else 0
            ranking_lista.append({
                'id': cliente.lower().replace(' ', '_'),  # ID simples para drill-down
                'nome': cliente,
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
        ano = request.args.get('ano', datetime.now().year)
        ano = int(ano)
        
        # Definir filtro de classe com base no setor
        filtro_classe = ''
        if setor == 'importacao':
            filtro_classe = 'IMP'
        elif setor == 'consultoria':
            filtro_classe = 'CONS'
        elif setor == 'exportacao':
            filtro_classe = 'EXP'
        
        # Buscar mapeamento de clientes para encontrar o nome real
        mapeamento_response = supabase_admin.table('fin_clientes_mapeamento').select('nome_original, nome_padronizado').execute()
        mapeamento_clientes = {}
        nome_cliente = None
        
        if mapeamento_response.data:
            for item in mapeamento_response.data:
                mapeamento_clientes[item['nome_original']] = item['nome_padronizado']
                # Encontrar o nome do cliente baseado no ID
                if item['nome_padronizado'].lower().replace(' ', '_') == cliente_id:
                    nome_cliente = item['nome_padronizado']
        
        if not nome_cliente:
            # Se não encontrar no mapeamento, tentar encontrar diretamente
            nome_cliente = cliente_id.replace('_', ' ').title()
        
        # Período do ano especificado
        inicio = f'{ano}-01-01'
        fim = f'{ano}-12-31'
        
        # Buscar dados de faturamento do cliente no setor
        query = supabase_admin.table('fin_faturamento_anual').select('*')
        if filtro_classe:
            query = query.ilike('classe', f'%{filtro_classe}%')
        query = query.gte('data', inicio).lte('data', fim)
        # Buscar por nome original ou padronizado
        query = query.or_(f'cliente.ilike.%{nome_cliente}%')
        
        response = query.execute()
        dados_cliente = response.data
        
        # Calcular faturamento total do cliente
        total_cliente = sum(float(item['valor']) for item in dados_cliente)
        
        # Buscar total do setor para calcular participação
        query_setor = supabase_admin.table('fin_faturamento_anual').select('valor')
        if filtro_classe:
            query_setor = query_setor.ilike('classe', f'%{filtro_classe}%')
        query_setor = query_setor.gte('data', inicio).lte('data', fim)
        
        response_setor = query_setor.execute()
        total_setor = sum(float(item['valor']) for item in response_setor.data)
        
        # Calcular participação
        participacao_setor = (total_cliente / total_setor * 100) if total_setor > 0 else 0
        
        # Dados do ano anterior para calcular crescimento
        inicio_anterior = f'{ano-1}-01-01'
        fim_anterior = f'{ano-1}-12-31'
        
        query_anterior = supabase_admin.table('fin_faturamento_anual').select('valor')
        if filtro_classe:
            query_anterior = query_anterior.ilike('classe', f'%{filtro_classe}%')
        query_anterior = query_anterior.gte('data', inicio_anterior).lte('data', fim_anterior)
        query_anterior = query_anterior.or_(f'cliente.ilike.%{nome_cliente}%')
        
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
