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
        
        # Buscar dados de faturamento do ano atual
        response_atual = supabase_admin.table('fin_faturamento_anual').select('*').gte('data', f'{ano}-01-01').lte('data', f'{ano}-12-31').execute()
        dados_atual = response_atual.data
        
        # Buscar dados de faturamento do ano anterior
        ano_anterior = int(ano) - 1
        response_anterior = supabase_admin.table('fin_faturamento_anual').select('*').gte('data', f'{ano_anterior}-01-01').lte('data', f'{ano_anterior}-12-31').execute()
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
    """API para comparativo anual usando view vw_fin_fat_anualizado"""
    try:
        # Buscar todos os dados da view (desde 2015)
        response = supabase_admin.table('vw_fin_fat_anualizado').select('*').order('ano, mes').execute()
        dados = response.data
        
        # Filtrar dados válidos (remover registros com ano/mês null)
        dados_validos = [item for item in dados if item.get('ano') and item.get('mes')]
        
        # Organizar dados por ano
        anos_data = defaultdict(list)
        
        for item in dados_validos:
            ano = str(item['ano'])
            mes = item['mes'].zfill(2)  # Garantir formato 01, 02, etc.
            valor = float(item.get('valor_faturamento', 0))
            
            anos_data[ano].append({
                'mes': mes,
                'total_valor': valor
            })
        
        # Garantir que todos os anos tenham 12 meses
        for ano in anos_data:
            meses_existentes = {item['mes'] for item in anos_data[ano]}
            for mes in range(1, 13):
                mes_str = str(mes).zfill(2)
                if mes_str not in meses_existentes:
                    anos_data[ano].append({
                        'mes': mes_str,
                        'total_valor': 0
                    })
            
            # Ordenar por mês
            anos_data[ano] = sorted(anos_data[ano], key=lambda x: x['mes'])
        
        return jsonify({
            'success': True,
            'data': dict(anos_data)
        })
        
    except Exception as e:
        print(f"Erro no comparativo_anos: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
        
    except Exception as e:
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
    """API para gráfico de rosca - Faturamento por Categoria (usando campo 'categoria_operacao')"""
    try:
        start_date = request.args.get('start_date', f'{datetime.now().year}-01-01')
        end_date = request.args.get('end_date', f'{datetime.now().year}-12-31')
        empresa = request.args.get('empresa', '')
        
        # Tentar usar a view tratada que tem categoria_operacao
        try:
            query = supabase_admin.table('vw_fin_faturamento_anual_tratado').select('categoria_operacao, valor')
        except:
            # Fallback para tabela original usando campo 'categoria'
            query = supabase_admin.table('fin_faturamento_anual').select('categoria, valor')
        
        # Aplicar filtros
        if start_date:
            query = query.gte('data', start_date)
        if end_date:
            query = query.lte('data', end_date)
        if empresa and empresa.strip():
            query = query.eq('empresa', empresa)
            
        response = query.execute()
        dados = response.data
        
        # Agrupar por categoria_operacao (ou categoria se for fallback)
        categoria_data = defaultdict(float)
        total_geral = 0
        
        for item in dados:
            # Tentar categoria_operacao primeiro, depois categoria
            categoria = item.get('categoria_operacao') or item.get('categoria', 'Não Classificado')
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
    """API para drill-down do centro de resultado - mostra clientes dentro do centro"""
    try:
        centro_resultado = request.args.get('centro_resultado', '')
        start_date = request.args.get('start_date', f'{datetime.now().year}-01-01')
        end_date = request.args.get('end_date', f'{datetime.now().year}-12-31')
        
        if not centro_resultado:
            return jsonify({'error': 'Centro de resultado é obrigatório'}), 400
        
        # Tentar usar a view tratada primeiro
        try:
            query = supabase_admin.table('vw_fin_faturamento_anual_tratado').select('cliente, valor, centro_resultado')
        except:
            # Fallback para tabela original
            query = supabase_admin.table('fin_faturamento_anual').select('cliente, valor, centro_resultado')
        
        # Filtrar por centro de resultado
        query = query.eq('centro_resultado', centro_resultado)
        
        # Aplicar filtros de data
        if start_date:
            query = query.gte('data', start_date)
        if end_date:
            query = query.lte('data', end_date)
            
        response = query.execute()
        dados = response.data
        
        # Agrupar por cliente
        cliente_data = defaultdict(float)
        total_geral = 0
        
        for item in dados:
            cliente = item.get('cliente', 'Não Informado')
            valor = float(item.get('valor', 0))
            cliente_data[cliente] += valor
            total_geral += valor
        
        # Preparar dados para o gráfico
        resultado = []
        for cliente, valor in cliente_data.items():
            percentual = (valor / total_geral * 100) if total_geral > 0 else 0
            resultado.append({
                'cliente': cliente,
                'valor_faturamento': valor,
                'percentual': percentual
            })
        
        # Ordenar por valor decrescente e pegar top 10
        resultado.sort(key=lambda x: x['valor_faturamento'], reverse=True)
        resultado = resultado[:10]  # Top 10 clientes
        
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
