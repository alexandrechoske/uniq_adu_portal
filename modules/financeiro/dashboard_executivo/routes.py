from flask import Blueprint, render_template, session, jsonify, request
from modules.auth.routes import login_required
from decorators.perfil_decorators import perfil_required
from extensions import supabase_admin
import pandas as pd
from datetime import datetime
from collections import defaultdict

# Blueprint para Dashboard Executivo Financeiro
dashboard_executivo_financeiro_bp = Blueprint(
    'fin_dashboard_executivo', 
    __name__,
    url_prefix='/financeiro/dashboard-executivo',
    template_folder='templates',
    static_folder='static',
    static_url_path='/financeiro/dashboard-executivo/static'
)

@dashboard_executivo_financeiro_bp.route('/')
@login_required
@perfil_required('financeiro', 'dashboard_executivo')
def index():
    """Dashboard Executivo Financeiro - Visão estratégica das finanças"""
    return render_template('dashboard_executivo_financeiro.html')

@dashboard_executivo_financeiro_bp.route('/api/kpis')
@login_required
@perfil_required('financeiro', 'dashboard_executivo')
def api_kpis():
    """API para KPIs principais do dashboard executivo"""
    try:
        ano = request.args.get('ano', datetime.now().year)
        
        # Buscar dados de faturamento
        response_faturamento = supabase_admin.table('fin_faturamento_anual') \
            .select('valor') \
            .gte('data', f'{ano}-01-01') \
            .lte('data', f'{ano}-12-31') \
            .execute()
        
        faturamento_atual = sum(float(item['valor']) for item in response_faturamento.data) if response_faturamento.data else 0
        
        # Buscar dados de faturamento do ano anterior para comparação
        ano_anterior = int(ano) - 1
        response_faturamento_anterior = supabase_admin.table('fin_faturamento_anual') \
            .select('valor') \
            .gte('data', f'{ano_anterior}-01-01') \
            .lte('data', f'{ano_anterior}-12-31') \
            .execute()
        
        faturamento_anterior = sum(float(item['valor']) for item in response_faturamento_anterior.data) if response_faturamento_anterior.data else 0
        
        # Calcular variação percentual do faturamento
        if faturamento_anterior > 0:
            faturamento_variacao = ((faturamento_atual - faturamento_anterior) / faturamento_anterior) * 100
        else:
            faturamento_variacao = 0 if faturamento_atual == 0 else 100
        
        # Buscar dados de despesas
        response_despesas = supabase_admin.table('fin_despesa_anual') \
            .select('valor') \
            .gte('data', f'{ano}-01-01') \
            .lte('data', f'{ano}-12-31') \
            .neq('classe', 'TRANSFERENCIA DE CONTAS') \
            .execute()
        
        despesas_atual = sum(float(item['valor']) for item in response_despesas.data) if response_despesas.data else 0
        
        # Buscar dados de despesas do ano anterior para comparação
        response_despesas_anterior = supabase_admin.table('fin_despesa_anual') \
            .select('valor') \
            .gte('data', f'{ano_anterior}-01-01') \
            .lte('data', f'{ano_anterior}-12-31') \
            .neq('classe', 'TRANSFERENCIA DE CONTAS') \
            .execute()
        
        despesas_anterior = sum(float(item['valor']) for item in response_despesas_anterior.data) if response_despesas_anterior.data else 0
        
        # Calcular variação percentual das despesas
        if despesas_anterior > 0:
            despesas_variacao = ((despesas_atual - despesas_anterior) / despesas_anterior) * 100
        else:
            despesas_variacao = 0 if despesas_atual == 0 else 100
        
        # Calcular resultado líquido
        resultado_atual = faturamento_atual - despesas_atual
        
        # Calcular resultado líquido do ano anterior
        resultado_anterior = faturamento_anterior - despesas_anterior
        
        # Calcular variação percentual do resultado
        if resultado_anterior != 0:
            resultado_variacao = ((resultado_atual - resultado_anterior) / abs(resultado_anterior)) * 100
        else:
            resultado_variacao = 0 if resultado_atual == 0 else 100
        
        # Calcular margem líquida
        margem_liquida = (resultado_atual / faturamento_atual * 100) if faturamento_atual > 0 else 0
        
        # Calcular margem líquida do ano anterior
        margem_liquida_anterior = (resultado_anterior / faturamento_anterior * 100) if faturamento_anterior > 0 else 0
        
        # Calcular variação percentual da margem
        if margem_liquida_anterior != 0:
            margem_variacao = margem_liquida - margem_liquida_anterior
        else:
            margem_variacao = 0 if margem_liquida == 0 else 100
        
        return jsonify({
            'success': True,
            'data': {
                'faturamento_total': faturamento_atual,
                'faturamento_variacao': round(faturamento_variacao, 2),
                'despesas_total': despesas_atual,
                'despesas_variacao': round(despesas_variacao, 2),
                'resultado_liquido': resultado_atual,
                'resultado_variacao': round(resultado_variacao, 2),
                'margem_liquida': round(margem_liquida, 2),
                'margem_variacao': round(margem_variacao, 2)
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@dashboard_executivo_financeiro_bp.route('/api/metas-segmentadas')
@login_required
@perfil_required('financeiro', 'dashboard_executivo')
def api_metas_segmentadas():
    """API para metas segmentadas (Geral, Consultoria, IMP/EXP)"""
    try:
        ano = request.args.get('ano', datetime.now().year)
        
        # Buscar todas as metas do ano da tabela correta fin_metas_projecoes
        response_metas = supabase_admin.table('fin_metas_projecoes') \
            .select('meta, tipo, mes') \
            .eq('ano', str(ano)) \
            .execute()
        
        # Separar metas por tipo
        meta_consultoria = 0
        meta_imp_exp = 0
        
        for item in response_metas.data:
            valor_meta = float(item['meta']) if item['meta'] else 0
            tipo = item.get('tipo', '').lower()
            
            if 'financeiro_consultoria' in tipo or 'consultoria' in tipo:
                meta_consultoria += valor_meta
            elif 'financeiro_imp_exp' in tipo or 'solucoes' in tipo or 'importacao' in tipo:
                meta_imp_exp += valor_meta
        
        meta_geral = meta_consultoria + meta_imp_exp
        
        # Buscar faturamento realizado usando a mesma lógica da distribuição por setor
        response_faturamento = supabase_admin.table('fin_faturamento_anual') \
            .select('valor, categoria') \
            .gte('data', f'{ano}-01-01') \
            .lte('data', f'{ano}-12-31') \
            .execute()

        # Separar faturamento por categoria (mesma lógica do gráfico de rosca)
        faturamento_consultoria = 0
        faturamento_importacao = 0
        faturamento_exportacao = 0

        for item in response_faturamento.data:
            valor = float(item['valor']) if item['valor'] else 0
            categoria = item.get('categoria', '').upper()

            if 'CONS' in categoria or 'CONSULT' in categoria:
                faturamento_consultoria += valor
            elif 'IMP' in categoria or 'IMPORT' in categoria:
                faturamento_importacao += valor
            elif 'EXP' in categoria or 'EXPORT' in categoria:
                faturamento_exportacao += valor

        # IMP/EXP é a soma de importação + exportação
        faturamento_imp_exp = faturamento_importacao + faturamento_exportacao
        faturamento_geral = faturamento_consultoria + faturamento_imp_exp
        
        # Calcular percentuais de atingimento
        atingimento_geral = (faturamento_geral / meta_geral * 100) if meta_geral > 0 else 0
        atingimento_consultoria = (faturamento_consultoria / meta_consultoria * 100) if meta_consultoria > 0 else 0
        atingimento_imp_exp = (faturamento_imp_exp / meta_imp_exp * 100) if meta_imp_exp > 0 else 0
        
        return jsonify({
            'success': True,
            'ano': int(ano),
            'data': {
                'geral': {
                    'meta': meta_geral,
                    'realizado': faturamento_geral,
                    'atingimento': round(atingimento_geral, 1)
                },
                'consultoria': {
                    'meta': meta_consultoria,
                    'realizado': faturamento_consultoria,
                    'atingimento': round(atingimento_consultoria, 1)
                },
                'imp_exp': {
                    'meta': meta_imp_exp,
                    'realizado': faturamento_imp_exp,
                    'atingimento': round(atingimento_imp_exp, 1)
                }
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@dashboard_executivo_financeiro_bp.route('/api/meta-atingimento')
@login_required
@perfil_required('financeiro', 'dashboard_executivo')
def api_meta_atingimento():
    """API para meta de atingimento de faturamento"""
    try:
        ano = request.args.get('ano', datetime.now().year)
        
        # Buscar meta do ano
        response_meta = supabase_admin.table('fin_metas_financeiras') \
            .select('meta') \
            .eq('ano', str(ano)) \
            .execute()
        
        meta = sum(float(item['meta']) for item in response_meta.data) if response_meta.data else 0
        
        # Buscar faturamento realizado
        response_faturamento = supabase_admin.table('fin_faturamento_anual') \
            .select('valor') \
            .gte('data', f'{ano}-01-01') \
            .lte('data', f'{ano}-12-31') \
            .execute()
        
        realizado = sum(float(item['valor']) for item in response_faturamento.data) if response_faturamento.data else 0
        
        # Calcular percentual
        percentual = (realizado / meta * 100) if meta > 0 else 0
        
        return jsonify({
            'success': True,
            'data': {
                'meta': meta,
                'realizado': realizado,
                'percentual': round(percentual, 2)
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@dashboard_executivo_financeiro_bp.route('/api/resultado-mensal')
@login_required
@perfil_required('financeiro', 'dashboard_executivo')
def api_resultado_mensal():
    """API para resultado mensal"""
    try:
        ano = request.args.get('ano', datetime.now().year)
        
        # Buscar dados de fluxo de caixa mensal
        response_fluxo = supabase_admin.table('vw_fluxo_caixa') \
            .select('data, valor, tipo') \
            .gte('data', f'{ano}-01-01') \
            .lte('data', f'{ano}-12-31') \
            .neq('classe', 'TRANSFERENCIA DE CONTAS') \
            .execute()
        
        # Processar dados mensais
        dados_mensais = defaultdict(lambda: {'receitas': 0, 'despesas': 0})
        
        for item in response_fluxo.data:
            data = datetime.strptime(item['data'], '%Y-%m-%d')
            mes = data.strftime('%Y-%m')
            valor = float(item['valor'])
            
            if item['tipo'] == 'Receita':
                dados_mensais[mes]['receitas'] += valor
            else:
                dados_mensais[mes]['despesas'] += valor
        
        # Calcular resultados mensais
        resultados = []
        for mes in sorted(dados_mensais.keys()):
            receitas = dados_mensais[mes]['receitas']
            despesas = dados_mensais[mes]['despesas']
            resultado = receitas - despesas
            
            resultados.append({
                'mes': mes,
                'receitas': receitas,
                'despesas': despesas,
                'resultado': resultado
            })
        
        return jsonify({
            'success': True,
            'data': resultados
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@dashboard_executivo_financeiro_bp.route('/api/saldo-acumulado')
@login_required
@perfil_required('financeiro', 'dashboard_executivo')
def api_saldo_acumulado():
    """API para evolução do saldo acumulado - CORRIGIDO"""
    try:
        ano = request.args.get('ano', datetime.now().year)

        # Buscar dados de valor (não saldo_acumulado) para recalcular corretamente
        response_saldo = supabase_admin.table('vw_fluxo_caixa') \
            .select('data, valor') \
            .gte('data', f'{ano}-01-01') \
            .lte('data', f'{ano}-12-31') \
            .neq('classe', 'TRANSFERENCIA DE CONTAS') \
            .order('data') \
            .execute()

        # Recalcular saldo acumulado corretamente
        saldo_acumulado = 0
        registros_com_saldo = []

        for item in response_saldo.data:
            valor = float(item['valor']) if item['valor'] else 0
            saldo_acumulado += valor  # O valor já vem com sinal correto

            registros_com_saldo.append({
                'data': item['data'],
                'saldo_calculado': saldo_acumulado
            })

        # Processar dados mensais
        dados_mensais = defaultdict(list)

        for item in registros_com_saldo:
            data = datetime.strptime(item['data'], '%Y-%m-%d')
            mes = data.strftime('%Y-%m')
            saldo = item['saldo_calculado']

            dados_mensais[mes].append(saldo)

        # Calcular saldo acumulado final de cada mês
        saldos_mensais = []
        for mes in sorted(dados_mensais.keys()):
            # Pegar o último saldo do mês
            saldo_final = dados_mensais[mes][-1] if dados_mensais[mes] else 0

            saldos_mensais.append({
                'mes': mes,
                'saldo_acumulado': saldo_final
            })

        return jsonify({
            'success': True,
            'data': saldos_mensais
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@dashboard_executivo_financeiro_bp.route('/api/faturamento-sunburst')
@login_required
@perfil_required('financeiro', 'dashboard_executivo')
def api_faturamento_sunburst():
    """API para dados Sunburst: Meta Grupo → Centro de Resultado"""
    try:
        ano = request.args.get('ano', datetime.now().year)
        
        # Buscar dados usando a view com meta_grupo e classe
        response_faturamento = supabase_admin.table('vw_fin_faturamento_anual_tratado') \
            .select('meta_grupo, classe, valor') \
            .gte('data', f'{ano}-01-01') \
            .lte('data', f'{ano}-12-31') \
            .execute()
        
        # Estruturar dados para Sunburst
        sunburst_data = []
        meta_grupos = {}
        
        # Processar dados
        for item in response_faturamento.data:
            meta_grupo = item.get('meta_grupo', 'Outros')
            classe = item.get('classe', 'Sem Classe')
            valor = float(item.get('valor', 0))
            
            # Inicializar meta_grupo se não existe
            if meta_grupo not in meta_grupos:
                meta_grupos[meta_grupo] = {
                    'name': meta_grupo,
                    'value': 0,
                    'children': {}
                }
            
            # Adicionar valor ao meta_grupo
            meta_grupos[meta_grupo]['value'] += valor
            
            # Inicializar classe se não existe
            if classe not in meta_grupos[meta_grupo]['children']:
                meta_grupos[meta_grupo]['children'][classe] = {
                    'name': classe,
                    'value': 0
                }
            
            # Adicionar valor à classe
            meta_grupos[meta_grupo]['children'][classe]['value'] += valor
        
        # Converter para formato esperado pelo Sunburst
        for meta_grupo, data in meta_grupos.items():
            children = list(data['children'].values())
            sunburst_data.append({
                'name': meta_grupo,
                'value': data['value'],
                'children': children
            })
        
        return jsonify({
            'success': True,
            'data': sunburst_data
        })
        
    except Exception as e:
        print(f"[DASHBOARD] Erro na API Sunburst: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@dashboard_executivo_financeiro_bp.route('/api/projecoes-saldo')
@login_required
@perfil_required('financeiro', 'dashboard_executivo')
def api_projecoes_saldo():
    """API para saldo acumulado com projeções (replicada do fluxo de caixa)"""
    try:
        ano = request.args.get('ano', datetime.now().year)
        ano = int(ano)
        
        # API 1: Saldo Acumulado Real (até hoje) - usando mesma lógica do fluxo de caixa
        table_name = 'vw_fluxo_caixa'
        
        # Buscar todos os dados até hoje para calcular saldo acumulado
        query = supabase_admin.table(table_name).select('data, valor, tipo')
        query = query.lte('data', datetime.now().strftime('%Y-%m-%d'))
        query = query.not_.ilike('classe', '%TRANSFERENCIA%')  # Filtro transferências
        query = query.order('data')
        response = query.execute()
        dados = response.data
        
        # Recalcular saldo acumulado real
        saldo_acumulado = 0
        registros_com_saldo = []
        
        for item in dados:
            valor = float(item['valor']) if item['valor'] else 0
            saldo_acumulado += valor  # O valor já vem com sinal correto da view
            
            registros_com_saldo.append({
                'data': item['data'],
                'saldo_calculado': saldo_acumulado
            })
        
        # Agregar por mês para o ano atual (último saldo de cada mês)
        saldos_mensais = {}
        for item in registros_com_saldo:
            data_obj = datetime.strptime(item['data'], '%Y-%m-%d')
            if data_obj.year == ano:
                mes_key = data_obj.strftime('%Y-%m')
                # Manter sempre o último saldo do mês
                if mes_key not in saldos_mensais or data_obj.day >= saldos_mensais[mes_key]['day']:
                    saldos_mensais[mes_key] = {
                        'saldo': item['saldo_calculado'],
                        'day': data_obj.day
                    }
        
        # Preparar dados reais
        meses_ordenados = sorted(saldos_mensais.keys())
        datas_reais = []
        saldos_reais = []
        
        for mes_key in meses_ordenados:
            data_obj = datetime.strptime(mes_key, '%Y-%m')
            datas_reais.append(data_obj.strftime('%b/%y'))
            saldos_reais.append(saldos_mensais[mes_key]['saldo'])
        
        # API 2: Projeções Futuras
        projecoes_query = supabase_admin.table('fin_metas_projecoes') \
            .select('ano, mes, meta') \
            .eq('tipo', 'projecao') \
            .order('ano, mes')
        projecoes_response = projecoes_query.execute()
        projecoes_dados = projecoes_response.data
        
        # Processar projeções futuras
        datas_futuras = []
        saldos_futuros = []
        
        # Pegar último saldo real como base
        ultimo_saldo_real = saldos_reais[-1] if saldos_reais else 0
        saldo_projetado = ultimo_saldo_real
        
        # Agrupar projeções por ano-mês para o futuro
        mes_atual = datetime.now().month
        for proj in projecoes_dados:
            proj_ano = int(proj['ano'])
            proj_mes = int(proj['mes'])
            meta = float(proj['meta'])
            
            # Só incluir meses futuros
            if (proj_ano > ano) or (proj_ano == ano and proj_mes > mes_atual):
                saldo_projetado += meta
                
                data_obj = datetime(proj_ano, proj_mes, 1)
                datas_futuras.append(data_obj.strftime('%b/%y'))
                saldos_futuros.append(saldo_projetado)
        
        return jsonify({
            'success': True,
            'data': {
                'saldo_real': {
                    'datas': datas_reais,
                    'saldos': saldos_reais
                },
                'projecao': {
                    'datas': datas_futuras, 
                    'saldos': saldos_futuros
                }
            }
        })
        
    except Exception as e:
        print(f"[DASHBOARD] Erro na API Saldo com Projeções: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@dashboard_executivo_financeiro_bp.route('/api/faturamento-setor')
@login_required
@perfil_required('financeiro', 'dashboard_executivo')
def api_faturamento_setor():
    """API para faturamento por setor"""
    try:
        ano = request.args.get('ano', datetime.now().year)
        
        # Buscar dados de faturamento
        response_faturamento = supabase_admin.table('fin_faturamento_anual') \
            .select('categoria, valor') \
            .gte('data', f'{ano}-01-01') \
            .lte('data', f'{ano}-12-31') \
            .execute()
        
        # Calcular totais por setor
        total_importacao = 0
        total_consultoria = 0
        total_exportacao = 0
        
        for item in response_faturamento.data:
            categoria = item.get('categoria', '').upper()
            valor = float(item['valor'])
            
            if 'IMP' in categoria or 'IMPORT' in categoria:
                total_importacao += valor
            elif 'CONS' in categoria or 'CONSULT' in categoria:
                total_consultoria += valor
            elif 'EXP' in categoria or 'EXPORT' in categoria:
                total_exportacao += valor
        
        return jsonify({
            'success': True,
            'data': [
                {
                    'setor': 'Importação',
                    'valor': total_importacao,
                    'percentual': (total_importacao / (total_importacao + total_consultoria + total_exportacao) * 100) if (total_importacao + total_consultoria + total_exportacao) > 0 else 0
                },
                {
                    'setor': 'Consultoria', 
                    'valor': total_consultoria,
                    'percentual': (total_consultoria / (total_importacao + total_consultoria + total_exportacao) * 100) if (total_importacao + total_consultoria + total_exportacao) > 0 else 0
                },
                {
                    'setor': 'Exportação',
                    'valor': total_exportacao,
                    'percentual': (total_exportacao / (total_importacao + total_consultoria + total_exportacao) * 100) if (total_importacao + total_consultoria + total_exportacao) > 0 else 0
                }
            ]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@dashboard_executivo_financeiro_bp.route('/api/top-despesas')
@login_required
@perfil_required('financeiro', 'dashboard_executivo')
def api_top_despesas():
    """API para top 5 categorias de despesa"""
    try:
        ano = request.args.get('ano', datetime.now().year)
        
        # Buscar dados de despesas
        response_despesas = supabase_admin.table('fin_despesa_anual') \
            .select('categoria, valor') \
            .gte('data', f'{ano}-01-01') \
            .lte('data', f'{ano}-12-31') \
            .neq('classe', 'TRANSFERENCIA DE CONTAS') \
            .execute()
        
        # Agrupar por categoria
        despesas_por_categoria = defaultdict(float)
        
        for item in response_despesas.data:
            categoria = item.get('categoria', 'Não categorizado')
            valor = float(item['valor'])
            
            despesas_por_categoria[categoria] += valor
        
        # Ordenar e pegar top 5
        top_despesas = sorted(despesas_por_categoria.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Formatar resultado
        resultado = []
        total_geral = sum(valor for _, valor in top_despesas)
        
        for categoria, total in top_despesas:
            resultado.append({
                'categoria': categoria,
                'total': total,
                'percentual': (total / total_geral * 100) if total_geral > 0 else 0
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

@dashboard_executivo_financeiro_bp.route('/api/top-clientes')
@login_required
@perfil_required('financeiro', 'dashboard_executivo')
def api_top_clientes():
    """API para top 10 clientes por faturamento"""
    try:
        ano = request.args.get('ano', datetime.now().year)
        ano_anterior = int(ano) - 1
        
        # Buscar dados de faturamento por cliente do ano atual
        response_faturamento = supabase_admin.table('fin_faturamento_anual') \
            .select('cliente, valor') \
            .gte('data', f'{ano}-01-01') \
            .lte('data', f'{ano}-12-31') \
            .execute()
        
        # Buscar dados de faturamento por cliente do ano anterior
        response_faturamento_anterior = supabase_admin.table('fin_faturamento_anual') \
            .select('cliente, valor') \
            .gte('data', f'{ano_anterior}-01-01') \
            .lte('data', f'{ano_anterior}-12-31') \
            .execute()
        
        # Agrupar por cliente - ano atual
        faturamento_por_cliente = defaultdict(float)
        for item in response_faturamento.data:
            cliente = item.get('cliente', 'Não identificado')
            valor = float(item['valor']) if item['valor'] else 0
            faturamento_por_cliente[cliente] += valor
        
        # Agrupar por cliente - ano anterior
        faturamento_anterior_por_cliente = defaultdict(float)
        for item in response_faturamento_anterior.data:
            cliente = item.get('cliente', 'Não identificado')
            valor = float(item['valor']) if item['valor'] else 0
            faturamento_anterior_por_cliente[cliente] += valor
        
        # Ordenar e pegar top 10
        top_clientes = sorted(faturamento_por_cliente.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Formatar resultado com trend
        resultado = []
        total_geral = sum(valor for _, valor in top_clientes)
        
        for i, (cliente, total) in enumerate(top_clientes):
            # Calcular trend
            total_anterior = faturamento_anterior_por_cliente.get(cliente, 0)
            
            if total_anterior == 0:
                trend = 'up' if total > 0 else 'stable'
            else:
                variacao_percentual = ((total - total_anterior) / total_anterior) * 100
                if variacao_percentual > 5:
                    trend = 'up'
                elif variacao_percentual < -5:
                    trend = 'down'
                else:
                    trend = 'stable'
            
            resultado.append({
                'cliente': cliente,
                'total_faturado': total,
                'total_anterior': total_anterior,
                'percentual': (total / total_geral * 100) if total_geral > 0 else 0,
                'rank': i + 1,
                'trend': trend,
                'variacao_percentual': ((total - total_anterior) / total_anterior * 100) if total_anterior > 0 else 0
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

@dashboard_executivo_financeiro_bp.route('/api/faturamento-classe')
@login_required
@perfil_required('financeiro', 'dashboard_executivo')
def api_faturamento_classe():
    """API para faturamento por classe dentro de um setor específico"""
    try:
        ano = request.args.get('ano', datetime.now().year)
        setor = request.args.get('setor', 'importacao')
        
        # Definir filtro de categoria com base no setor
        filtro_categoria = ''
        if setor == 'importacao':
            filtro_categoria = 'IMPORTAÇÃO'
        elif setor == 'consultoria':
            filtro_categoria = 'CONSULTORIA'
        elif setor == 'exportacao':
            filtro_categoria = 'EXPORTAÇÃO'
        
        # Buscar dados de faturamento com filtro de categoria
        response_faturamento = supabase_admin.table('fin_faturamento_anual') \
            .select('categoria, classe, valor') \
            .eq('categoria', filtro_categoria) \
            .gte('data', f'{ano}-01-01') \
            .lte('data', f'{ano}-12-31') \
            .execute()
        
        # Agrupar por classe específica
        faturamento_por_classe = defaultdict(float)
        
        for item in response_faturamento.data:
            classe = item.get('classe', 'Não especificado')
            valor = float(item['valor'])
            
            faturamento_por_classe[classe] += valor
        
        # Converter para lista e ordenar
        classe_data = []
        total_setor = sum(faturamento_por_classe.values())
        
        for classe, valor in faturamento_por_classe.items():
            percentual = (valor / total_setor * 100) if total_setor > 0 else 0
            classe_data.append({
                'classe': classe,
                'valor': valor,
                'percentual': percentual
            })
        
        # Ordenar por valor (decrescente)
        classe_data.sort(key=lambda x: x['valor'], reverse=True)
        
        return jsonify({
            'success': True,
            'data': classe_data,
            'setor': setor,
            'total': total_setor
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
