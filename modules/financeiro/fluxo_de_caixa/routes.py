from flask import Blueprint, render_template, session, jsonify, request
from extensions import supabase, supabase_admin
from routes.auth import login_required, role_required
from decorators.perfil_decorators import perfil_required
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import json
from collections import defaultdict

# Blueprint para Fluxo de Caixa
fluxo_de_caixa_bp = Blueprint(
    'fin_fluxo_de_caixa', 
    __name__,
    url_prefix='/financeiro/fluxo-de-caixa',
    template_folder='templates',
    static_folder='static',
    static_url_path='/financeiro/static'
)

@fluxo_de_caixa_bp.route('/')
@login_required
@perfil_required('financeiro', 'fluxo_caixa')
def index():
    """Fluxo de Caixa - Controle de entradas e saídas"""
    return render_template('fluxo_de_caixa.html')

@fluxo_de_caixa_bp.route('/api/kpis')
@login_required
@perfil_required('financeiro', 'fluxo_caixa')
def api_kpis():
    """API para KPIs principais do fluxo de caixa"""
    try:
        # Obter parâmetros de período
        periodo = request.args.get('periodo', 'ano_atual')
        data_inicio, data_fim = _get_periodo_dates(periodo)
        
        # Verificar qual tabela usar (priorizar fin_resultado_anual se existir)
        table_name = _get_financial_table()
        
        # Buscar dados do período atual
        query = supabase_admin.table(table_name).select('*').order('ordem')
        if data_inicio and data_fim:
            query = query.gte('data', data_inicio).lte('data', data_fim)
        
        # Filtrar TRANSFERENCIA DE CONTAS
        query = query.neq('classe', 'TRANSFERENCIA DE CONTAS')
        
        response = query.execute()
        dados_periodo = response.data
        
        # Calcular KPIs do período atual usando a nova estrutura
        total_entradas = sum(float(item['valor_fluxo']) for item in dados_periodo if item['tipo_movto'] == 'Receita')
        total_saidas = sum(float(item['valor_fluxo']) for item in dados_periodo if item['tipo_movto'] == 'Despesa')
        resultado_liquido = total_entradas - total_saidas
        
        # Buscar dados do período anterior para comparação
        data_inicio_anterior, data_fim_anterior = _get_periodo_anterior_dates(periodo)
        
        query_anterior = supabase_admin.table(table_name).select('*').order('ordem')
        if data_inicio_anterior and data_fim_anterior:
            query_anterior = query_anterior.gte('data', data_inicio_anterior).lte('data', data_fim_anterior)
        
        # Filtrar TRANSFERENCIA DE CONTAS também no período anterior
        query_anterior = query_anterior.neq('classe', 'TRANSFERENCIA DE CONTAS')
        
        response_anterior = query_anterior.execute()
        dados_anterior = response_anterior.data
        
        # Calcular KPIs do período anterior
        entradas_anterior = sum(float(item['valor_fluxo']) for item in dados_anterior if item['tipo_movto'] == 'Receita')
        saidas_anterior = sum(float(item['valor_fluxo']) for item in dados_anterior if item['tipo_movto'] == 'Despesa')
        resultado_anterior = entradas_anterior - saidas_anterior
        
        # Calcular variações percentuais
        var_entradas = _calcular_variacao_percentual(total_entradas, entradas_anterior)
        var_saidas = _calcular_variacao_percentual(total_saidas, saidas_anterior)
        var_resultado = _calcular_variacao_percentual(resultado_liquido, resultado_anterior)
        
        # Calcular saldo acumulado (usando saldo_acumulado da view se disponível)
        if dados_periodo and 'saldo_acumulado' in dados_periodo[0]:
            saldo_final = max(float(item['saldo_acumulado']) for item in dados_periodo)
        else:
            saldo_final = resultado_liquido
        
        # NOVOS KPIs MENSAIS - Mês atual
        from datetime import datetime
        mes_atual = datetime.now().strftime('%Y-%m')
        mes_anterior = (datetime.now().replace(day=1) - timedelta(days=1)).strftime('%Y-%m')
        
        # Filtrar dados do mês atual
        dados_mes_atual = [item for item in dados_periodo if item['ano_mes'] == mes_atual]
        entradas_mes_atual = sum(float(item['valor_fluxo']) for item in dados_mes_atual if item['tipo_movto'] == 'Receita')
        saidas_mes_atual = sum(float(item['valor_fluxo']) for item in dados_mes_atual if item['tipo_movto'] == 'Despesa')
        
        # Saldo do mês atual (pode pegar o último saldo_acumulado do mês)
        if dados_mes_atual and 'saldo_acumulado' in dados_mes_atual[0]:
            saldo_mes_atual = max(float(item['saldo_acumulado']) for item in dados_mes_atual)
        else:
            saldo_mes_atual = entradas_mes_atual - saidas_mes_atual
        
        # Buscar dados do mês anterior
        query_mes_anterior = supabase_admin.table(table_name).select('*').eq('ano_mes', mes_anterior)
        query_mes_anterior = query_mes_anterior.neq('classe', 'TRANSFERENCIA DE CONTAS')
        response_mes_anterior = query_mes_anterior.execute()
        dados_mes_anterior = response_mes_anterior.data
        
        # Calcular KPIs do mês anterior
        entradas_mes_anterior = sum(float(item['valor_fluxo']) for item in dados_mes_anterior if item['tipo_movto'] == 'Receita')
        saidas_mes_anterior = sum(float(item['valor_fluxo']) for item in dados_mes_anterior if item['tipo_movto'] == 'Despesa')
        
        if dados_mes_anterior and 'saldo_acumulado' in dados_mes_anterior[0]:
            saldo_mes_anterior = max(float(item['saldo_acumulado']) for item in dados_mes_anterior)
        else:
            saldo_mes_anterior = entradas_mes_anterior - saidas_mes_anterior
        
        # Calcular variações mensais
        var_entradas_mes = _calcular_variacao_percentual(entradas_mes_atual, entradas_mes_anterior)
        var_saidas_mes = _calcular_variacao_percentual(saidas_mes_atual, saidas_mes_anterior)
        var_saldo_mes = _calcular_variacao_percentual(saldo_mes_atual, saldo_mes_anterior)
        
        # Calcular indicadores estratégicos
        burn_rate = _calcular_burn_rate(dados_periodo)
        runway = _calcular_runway(saldo_final, burn_rate)
        
        return jsonify({
            # KPIs Acumulados do Período
            'resultado_liquido': {
                'valor': resultado_liquido,
                'variacao': var_resultado
            },
            'total_entradas': {
                'valor': total_entradas,
                'variacao': var_entradas
            },
            'total_saidas': {
                'valor': -total_saidas,  # Exibir como negativo na interface
                'variacao': var_saidas
            },
            'saldo_final': {
                'valor': saldo_final,
                'variacao': 0  # Para implementação futura
            },
            
            # NOVOS KPIs Mensais (Mês Atual vs Mês Anterior)
            'entradas_mes_atual': {
                'valor': entradas_mes_atual,
                'variacao': var_entradas_mes
            },
            'saidas_mes_atual': {
                'valor': -saidas_mes_atual,  # Exibir como negativo
                'variacao': var_saidas_mes
            },
            'saldo_mes_atual': {
                'valor': saldo_mes_atual,
                'variacao': var_saldo_mes
            },
            
            'burn_rate': burn_rate,
            'runway': runway,
            'table_used': table_name  # Info para debug
        })
        
    except Exception as e:
        # Log the error for debugging
        import traceback
        error_details = {
            'error': str(e),
            'traceback': traceback.format_exc(),
            'periodo': periodo,
            'table_name': table_name if 'table_name' in locals() else 'Not defined'
        }
        print(f"Error in api_kpis: {error_details}")  # Simple logging
        
        # Return default/fallback values instead of failing completely
        return jsonify({
            # KPIs Acumulados do Período
            'resultado_liquido': {
                'valor': 0,
                'variacao': 0
            },
            'total_entradas': {
                'valor': 0,
                'variacao': 0
            },
            'total_saidas': {
                'valor': 0,
                'variacao': 0
            },
            'saldo_final': {
                'valor': 0,
                'variacao': 0
            },
            
            # NOVOS KPIs Mensais (Mês Atual vs Mês Anterior)
            'entradas_mes_atual': {
                'valor': 0,
                'variacao': 0
            },
            'saidas_mes_atual': {
                'valor': 0,
                'variacao': 0
            },
            'saldo_mes_atual': {
                'valor': 0,
                'variacao': 0
            },
            
            'burn_rate': 0,
            'runway': 0,
            'table_used': table_name if 'table_name' in locals() else 'undefined',
            'error': 'Connection error - using fallback values'
        }), 200  # Return 200 instead of 500 to prevent frontend errors

@fluxo_de_caixa_bp.route('/api/despesas-categoria')
@login_required
@perfil_required('financeiro', 'fluxo_caixa')
def api_despesas_categoria():
    """API para gráfico de despesas por categoria"""
    try:
        periodo = request.args.get('periodo', 'ano_atual')
        categoria_drill = request.args.get('categoria')  # Para drill-down
        exclude_admin = request.args.get('exclude_admin', 'false').lower() == 'true'  # Novo parâmetro
        
        data_inicio, data_fim = _get_periodo_dates(periodo)
        table_name = _get_financial_table()
        
        # Query para despesas usando a nova estrutura
        query = supabase_admin.table(table_name).select('*').eq('tipo_movto', 'Despesa')
        if data_inicio and data_fim:
            query = query.gte('data', data_inicio).lte('data', data_fim)
        
        # Filtrar TRANSFERENCIA DE CONTAS
        query = query.neq('classe', 'TRANSFERENCIA DE CONTAS')
        
        response = query.execute()
        dados = response.data
        
        # Filtrar "Despesas Administrativas" se solicitado
        if exclude_admin and not categoria_drill:
            dados = [item for item in dados if item['categoria'] != 'Despesas Administrativas']
        
        if categoria_drill:
            # Drill-down: agrupar por classe dentro da categoria
            dados_filtrados = [item for item in dados if item['categoria'] == categoria_drill]
            agrupamento = defaultdict(float)
            for item in dados_filtrados:
                classe = item.get('classe', 'Sem Classe')
                valor = float(item['valor_fluxo'])  # Usar valor_fluxo que é sempre positivo
                agrupamento[classe] += valor
        else:
            # Visão principal: agrupar por categoria
            agrupamento = defaultdict(float)
            for item in dados:
                categoria = item.get('categoria', 'Sem Categoria')
                valor = float(item['valor_fluxo'])  # Usar valor_fluxo que é sempre positivo
                agrupamento[categoria] += valor
        
        # Converter para listas e ordenar do maior para menor
        items = list(agrupamento.items())
        items.sort(key=lambda x: x[1], reverse=True)  # Ordenação do maior para menor
        
        labels = [item[0] for item in items]
        valores = [item[1] for item in items]
        
        return jsonify({
            'labels': labels,
            'valores': valores,
            'drill_categoria': categoria_drill,
            'exclude_admin': exclude_admin
        })
        
    except Exception as e:
        # Log the error for debugging
        import traceback
        error_details = {
            'error': str(e),
            'traceback': traceback.format_exc(),
            'periodo': periodo,
            'table_name': table_name if 'table_name' in locals() else 'Not defined'
        }
        print(f"Error in api_despesas_categoria: {error_details}")  # Simple logging
        
        # Return default/fallback values instead of failing completely
        return jsonify({
            'labels': [],
            'valores': [],
            'drill_categoria': categoria_drill if 'categoria_drill' in locals() else None,
            'exclude_admin': exclude_admin if 'exclude_admin' in locals() else False,
            'error': 'Connection error - using fallback values'
        }), 200  # Return 200 instead of 500 to prevent frontend errors

@fluxo_de_caixa_bp.route('/api/fluxo-mensal')
@login_required
@perfil_required('financeiro', 'fluxo_caixa')
def api_fluxo_mensal():
    """API para gráfico de fluxo de caixa mês a mês com receitas e despesas separadas"""
    try:
        periodo = request.args.get('periodo', 'ano_atual')
        data_inicio, data_fim = _get_periodo_dates(periodo)
        table_name = _get_financial_table()
        
        query = supabase_admin.table(table_name).select('*').order('ordem')
        if data_inicio and data_fim:
            query = query.gte('data', data_inicio).lte('data', data_fim)
        
        # Filtrar TRANSFERENCIA DE CONTAS
        query = query.neq('classe', 'TRANSFERENCIA DE CONTAS')
        
        response = query.execute()
        dados = response.data
        
        # Agrupar por mês usando o campo ano_mes da view
        fluxo_mensal = defaultdict(lambda: {'receitas': 0, 'despesas': 0, 'saldo_acumulado': 0})
        
        for item in dados:
            ano_mes = item['ano_mes']  # Usar o campo ano_mes da view
            valor_fluxo = float(item['valor_fluxo'])  # Sempre positivo
            saldo_acumulado = float(item['saldo_acumulado'])
            
            if item['tipo_movto'] == 'Receita':
                fluxo_mensal[ano_mes]['receitas'] += valor_fluxo
            else:  # Despesa
                fluxo_mensal[ano_mes]['despesas'] += valor_fluxo
            
            # Usar o último saldo acumulado do mês
            fluxo_mensal[ano_mes]['saldo_acumulado'] = saldo_acumulado
        
        # Converter para formato do gráfico
        meses = sorted(fluxo_mensal.keys())
        receitas_mes = []
        despesas_mes = []
        resultados = []
        saldo_acumulado_mes = []
        saldo_acumulado = []
        saldo_atual = 0
        
        for mes in meses:
            receita = fluxo_mensal[mes]['receitas']
            despesa = fluxo_mensal[mes]['despesas']
            resultado_mes = receita - despesa
            saldo_final_mes = fluxo_mensal[mes]['saldo_acumulado']
            
            receitas_mes.append(receita)
            despesas_mes.append(despesa)
            resultados.append(resultado_mes)
            saldo_acumulado_mes.append(saldo_final_mes)
        
        # Formatar nomes dos meses
        meses_formatados = []
        for mes in meses:
            ano, mes_num = mes.split('-')
            data_temp = datetime.strptime(f"{ano}-{mes_num}-01", '%Y-%m-%d')
            mes_formatado = data_temp.strftime('%b/%Y')
            meses_formatados.append(mes_formatado)
        
        return jsonify({
            'meses': meses_formatados,
            'receitas': receitas_mes,
            'despesas': despesas_mes,
            'resultados': resultados,
            'saldo_acumulado': saldo_acumulado_mes  # Usar saldo já calculado na view
        })
        
    except Exception as e:
        # Log the error for debugging
        import traceback
        error_details = {
            'error': str(e),
            'traceback': traceback.format_exc(),
            'periodo': periodo,
            'table_name': table_name if 'table_name' in locals() else 'Not defined'
        }
        print(f"Error in api_fluxo_mensal: {error_details}")  # Simple logging
        
        # Return default/fallback values instead of failing completely
        return jsonify({
            'meses': [],
            'receitas': [],
            'despesas': [],
            'resultados': [],
            'saldo_acumulado': [],
            'error': 'Connection error - using fallback values'
        }), 200  # Return 200 instead of 500 to prevent frontend errors

@fluxo_de_caixa_bp.route('/api/fluxo-estrutural')
@login_required
@perfil_required('financeiro', 'fluxo_caixa')
def api_fluxo_estrutural():
    """API para análise estrutural do caixa (FCO, FCI, FCF)"""
    try:
        periodo = request.args.get('periodo', 'ano_atual')
        data_inicio, data_fim = _get_periodo_dates(periodo)
        table_name = _get_financial_table()
        
        query = supabase_admin.table(table_name).select('*').order('ordem')
        if data_inicio and data_fim:
            query = query.gte('data', data_inicio).lte('data', data_fim)
        
        # Filtrar TRANSFERENCIA DE CONTAS
        query = query.neq('classe', 'TRANSFERENCIA DE CONTAS')
        
        response = query.execute()
        dados = response.data
        
        # Classificar por tipo de fluxo baseado na categoria
        classificacao_fluxo = {
            'FCO': ['IMPORTAÇÃO', 'EXPORTAÇÃO', 'CONSULTORIA', 'DESPESAS COM FUNCIONÁRIOS', 'DIRETORIA', 'IMPOSTOS', 'DESPESAS OPERACIONAIS', 'COMERCIAIS', 'ADMINISTRATIVAS'],
            'FCI': ['ATIVO'],
            'FCF': ['EMPRÉSTIMOS', 'RENDIMENTO']
        }
        
        # Agrupar por mês e tipo de fluxo usando a nova estrutura
        fluxo_estrutural = defaultdict(lambda: {'FCO': 0, 'FCI': 0, 'FCF': 0})
        
        for item in dados:
            ano_mes = item['ano_mes']  # Usar ano_mes da view
            categoria = item['categoria'].upper()
            valor_fluxo = float(item['valor_fluxo'])  # Sempre positivo
            
            # Aplicar sinal correto baseado no tipo_movto
            if item['tipo_movto'] == 'Despesa':
                valor = -valor_fluxo
            else:
                valor = valor_fluxo
            
            # Classificar em FCO, FCI ou FCF
            tipo_fluxo = 'FCO'  # Default - Fluxo de Caixa Operacional
            for fluxo, categorias in classificacao_fluxo.items():
                if any(cat in categoria for cat in categorias):
                    tipo_fluxo = fluxo
                    break
            
            fluxo_estrutural[ano_mes][tipo_fluxo] += valor
        
        # Converter para formato do gráfico
        meses = sorted(fluxo_estrutural.keys())
        fco_valores = [fluxo_estrutural[mes]['FCO'] for mes in meses]
        fci_valores = [fluxo_estrutural[mes]['FCI'] for mes in meses]
        fcf_valores = [fluxo_estrutural[mes]['FCF'] for mes in meses]
        
        # Formatar nomes dos meses
        meses_formatados = []
        for mes in meses:
            ano, mes_num = mes.split('-')
            data_temp = datetime.strptime(f"{ano}-{mes_num}-01", '%Y-%m-%d')
            mes_formatado = data_temp.strftime('%b/%Y')
            meses_formatados.append(mes_formatado)
        
        return jsonify({
            'meses': meses_formatados,
            'fco': fco_valores,
            'fci': fci_valores,
            'fcf': fcf_valores,
            'total_registros': len(dados)
        })
        
    except Exception as e:
        # Log the error for debugging
        import traceback
        error_details = {
            'error': str(e),
            'traceback': traceback.format_exc(),
            'periodo': periodo,
            'table_name': table_name if 'table_name' in locals() else 'Not defined'
        }
        print(f"Error in api_fluxo_estrutural: {error_details}")  # Simple logging
        
        # Return default/fallback values instead of failing completely
        return jsonify({
            'meses': [],
            'fco': [],
            'fci': [],
            'fcf': [],
            'total_registros': 0,
            'error': 'Connection error - using fallback values'
        }), 200  # Return 200 instead of 500 to prevent frontend errors

@fluxo_de_caixa_bp.route('/api/projecao')
@login_required
@perfil_required('financeiro', 'fluxo_caixa')
def api_projecao():
    """API para projeção de fluxo de caixa com dados históricos + projeção"""
    try:
        # Buscar dados dos últimos 24 meses para base da projeção + os últimos 6 meses para mostrar histórico
        data_fim = datetime.now()
        data_inicio_calculo = data_fim - timedelta(days=730)  # 24 meses para cálculo (mais assertivo)
        data_inicio_historico = data_fim - timedelta(days=180)  # 6 meses para mostrar no gráfico
        table_name = _get_financial_table()
        
        # Buscar dados para cálculo (24 meses)
        query_calculo = supabase_admin.table(table_name).select('*').order('ordem')
        query_calculo = query_calculo.gte('data', data_inicio_calculo.strftime('%Y-%m-%d'))
        query_calculo = query_calculo.lte('data', data_fim.strftime('%Y-%m-%d'))
        query_calculo = query_calculo.neq('classe', 'TRANSFERENCIA DE CONTAS')
        
        response_calculo = query_calculo.execute()
        dados_calculo = response_calculo.data
        
        # Buscar dados históricos para exibir (6 meses)
        query_historico = supabase_admin.table(table_name).select('*').order('ordem')
        query_historico = query_historico.gte('data', data_inicio_historico.strftime('%Y-%m-%d'))
        query_historico = query_historico.lte('data', data_fim.strftime('%Y-%m-%d'))
        query_historico = query_historico.neq('classe', 'TRANSFERENCIA DE CONTAS')
        
        response_historico = query_historico.execute()
        dados_historicos = response_historico.data
        
        # Processar dados históricos para exibição
        fluxo_historico = defaultdict(lambda: {'entradas': 0, 'saidas': 0, 'saldo_final': 0})
        
        for item in dados_historicos:
            ano_mes = item['ano_mes']
            valor_fluxo = float(item['valor_fluxo'])
            saldo_acumulado = float(item['saldo_acumulado'])
            
            if item['tipo_movto'] == 'Receita':
                fluxo_historico[ano_mes]['entradas'] += valor_fluxo
            else:
                fluxo_historico[ano_mes]['saidas'] += valor_fluxo
            
            # Manter o último saldo acumulado do mês
            fluxo_historico[ano_mes]['saldo_final'] = max(fluxo_historico[ano_mes]['saldo_final'], saldo_acumulado)
        
        # Calcular médias mensais dos últimos 6 meses para projeção
        fluxo_mensal_calculo = defaultdict(lambda: {'entradas': 0, 'saidas': 0})
        
        for item in dados_calculo:
            ano_mes = item['ano_mes']
            valor_fluxo = float(item['valor_fluxo'])
            
            if item['tipo_movto'] == 'Receita':
                fluxo_mensal_calculo[ano_mes]['entradas'] += valor_fluxo
            else:
                fluxo_mensal_calculo[ano_mes]['saidas'] += valor_fluxo
        
        # Calcular médias
        total_meses = len(fluxo_mensal_calculo)
        if total_meses > 0:
            media_entradas = sum(m['entradas'] for m in fluxo_mensal_calculo.values()) / total_meses
            media_saidas = sum(m['saidas'] for m in fluxo_mensal_calculo.values()) / total_meses
        else:
            media_entradas = media_saidas = 0
        
        # Obter último saldo acumulado dos dados históricos
        if dados_historicos:
            ultimo_saldo = max(float(item['saldo_acumulado']) for item in dados_historicos)
        else:
            ultimo_saldo = 0
        
        # Preparar dados históricos para retorno (últimos 3 meses)
        meses_historicos = []
        entradas_historicas = []
        saidas_historicas = []
        saldo_historico = []
        
        # Ordenar por ano_mes
        historico_ordenado = sorted(fluxo_historico.keys())
        for ano_mes in historico_ordenado:
            # Converter formato "2025-08" para "Ago/2025"
            ano, mes = ano_mes.split('-')
            mes_names = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 
                        'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
            mes_nome = f"{mes_names[int(mes)-1]}/{ano}"
            
            meses_historicos.append(mes_nome)
            entradas_historicas.append(fluxo_historico[ano_mes]['entradas'])
            saidas_historicas.append(fluxo_historico[ano_mes]['saidas'])
            saldo_historico.append(fluxo_historico[ano_mes]['saldo_final'])
        
        # Gerar projeção para os próximos 6 meses
        meses_projecao = []
        entradas_projetadas = []
        saidas_projetadas = []
        saldo_projetado = []
        saldo_atual = ultimo_saldo
        
        for i in range(6):
            data_projecao = data_fim + timedelta(days=30 * (i + 1))
            mes_nome = data_projecao.strftime('%b/%Y')
            meses_projecao.append(mes_nome)
            
            # Projetar valores com pequena variação (±5%)
            import random
            variacao = random.uniform(0.95, 1.05)
            entrada_projetada = media_entradas * variacao
            saida_projetada = media_saidas * variacao
            
            entradas_projetadas.append(entrada_projetada)
            saidas_projetadas.append(saida_projetada)
            
            saldo_atual += (entrada_projetada - saida_projetada)
            saldo_projetado.append(saldo_atual)
        
        # Combinar dados históricos + projeção
        todos_meses = meses_historicos + meses_projecao
        todas_entradas = entradas_historicas + entradas_projetadas
        todas_saidas = saidas_historicas + saidas_projetadas
        todos_saldos = saldo_historico + saldo_projetado
        
        # Marcar onde termina o histórico e começa a projeção
        historico_length = len(meses_historicos)
        
        return jsonify({
            'meses': todos_meses,
            'entradas': todas_entradas,
            'saidas': todas_saidas,
            'saldo': todos_saldos,
            'historico_length': historico_length,  # Para saber onde dividir no gráfico
            'media_entradas': media_entradas,
            'media_saidas': media_saidas,
            'ultimo_saldo': ultimo_saldo,
            'meses_base': total_meses
        })
        
    except Exception as e:
        # Log the error for debugging
        import traceback
        error_details = {
            'error': str(e),
            'traceback': traceback.format_exc(),
            'table_name': table_name if 'table_name' in locals() else 'Not defined'
        }
        print(f"Error in api_projecao: {error_details}")  # Simple logging
        
        # Return default/fallback values instead of failing completely
        return jsonify({
            'meses': [],
            'entradas': [],
            'saidas': [],
            'saldo': [],
            'historico_length': 0,
            'media_entradas': 0,
            'media_saidas': 0,
            'ultimo_saldo': 0,
            'meses_base': 0,
            'error': 'Connection error - using fallback values'
        }), 200  # Return 200 instead of 500 to prevent frontend errors

@fluxo_de_caixa_bp.route('/api/tabela-dados')
@login_required
@perfil_required('financeiro', 'fluxo_caixa')
def api_tabela_dados():
    """API para dados da tabela completa"""
    try:
        periodo = request.args.get('periodo', 'ano_atual')
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))
        search = request.args.get('search', '').strip()  # Parâmetro de busca
        
        data_inicio, data_fim = _get_periodo_dates(periodo)
        table_name = _get_financial_table()
        
        # Query para dados paginados
        query = supabase_admin.table(table_name).select('*')
        if data_inicio and data_fim:
            query = query.gte('data', data_inicio).lte('data', data_fim)
        
        # Filtrar TRANSFERENCIA DE CONTAS
        query = query.neq('classe', 'TRANSFERENCIA DE CONTAS')
        
        # Aplicar filtro de busca se fornecido
        if search:
            # Buscar em descrição, categoria, classe ou código
            query = query.or_(f'descricao.ilike.%{search}%,categoria.ilike.%{search}%,classe.ilike.%{search}%,codigo.ilike.%{search}%')
        
        # Aplicar ordenação e paginação
        offset = (page - 1) * limit
        query = query.order('data', desc=True).range(offset, offset + limit - 1)
        
        response = query.execute()
        dados = response.data
        
        # Contar total de registros (com filtro se aplicável)
        count_query = supabase_admin.table(table_name).select('*', count='exact')
        if data_inicio and data_fim:
            count_query = count_query.gte('data', data_inicio).lte('data', data_fim)
        
        # Filtrar TRANSFERENCIA DE CONTAS na contagem também
        count_query = count_query.neq('classe', 'TRANSFERENCIA DE CONTAS')
        
        if search:
            count_query = count_query.or_(f'descricao.ilike.%{search}%,categoria.ilike.%{search}%,classe.ilike.%{search}%,codigo.ilike.%{search}%')
        
        count_response = count_query.execute()
        total_registros = count_response.count
        
        return jsonify({
            'dados': dados,
            'total': total_registros,
            'page': page,
            'limit': limit,
            'total_pages': (total_registros + limit - 1) // limit
        })
        
    except Exception as e:
        # Log the error for debugging
        import traceback
        error_details = {
            'error': str(e),
            'traceback': traceback.format_exc(),
            'periodo': periodo,
            'table_name': table_name if 'table_name' in locals() else 'Not defined'
        }
        print(f"Error in api_tabela_dados: {error_details}")  # Simple logging
        
        # Return default/fallback values instead of failing completely
        return jsonify({
            'dados': [],
            'total': 0,
            'page': page if 'page' in locals() else 1,
            'limit': limit if 'limit' in locals() else 50,
            'total_pages': 0,
            'error': 'Connection error - using fallback values'
        }), 200  # Return 200 instead of 500 to prevent frontend errors

@fluxo_de_caixa_bp.route('/api/test-data')
@login_required
def api_test_data():
    """API de teste para verificar acesso aos dados"""
    user = session.get('user', {})
    user_role = user.get('role', '')
    
    if user_role not in ['admin', 'interno_unique']:
        return jsonify({'error': 'Acesso negado'}), 403
    
    try:
        # Primeiro, verificar se fin_base_resultado existe e tem dados
        try:
            response_base = supabase_admin.table('fin_base_resultado').select('*').limit(5).execute()
            base_data = response_base.data
            base_count = len(base_data)
        except Exception as e:
            base_data = []
            base_count = 0
            
        # Verificar se fin_resultado_anual existe e tem dados
        try:
            response_anual = supabase_admin.table('fin_resultado_anual').select('*').limit(5).execute()
            anual_data = response_anual.data
            anual_count = len(anual_data)
        except Exception as e:
            anual_data = []
            anual_count = 0
        
        return jsonify({
            'status': 'success',
            'message': 'Teste de conectividade financeira',
            'tables': {
                'fin_base_resultado': {
                    'exists': base_count > 0,
                    'count': base_count,
                    'sample': base_data[:2] if base_data else []
                },
                'fin_resultado_anual': {
                    'exists': anual_count > 0,
                    'count': anual_count,
                    'sample': anual_data[:2] if anual_data else []
                }
            }
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@fluxo_de_caixa_bp.route('/api/check-tables')
@login_required  
def api_check_tables():
    """Verificar quais tabelas financeiras existem"""
    user = session.get('user', {})
    user_role = user.get('role', '')
    
    if user_role not in ['admin', 'interno_unique']:
        return jsonify({'error': 'Acesso negado'}), 403
    
    tables_to_check = [
        'fin_base_resultado',
        'fin_resultado_anual', 
        'vw_resultado_anual'
    ]
    
    results = {}
    
    for table_name in tables_to_check:
        try:
            # Tentar fazer uma query simples
            response = supabase_admin.table(table_name).select('*').limit(1).execute()
            results[table_name] = {
                'exists': True,
                'has_data': len(response.data) > 0,
                'sample_record': response.data[0] if response.data else None
            }
        except Exception as e:
            results[table_name] = {
                'exists': False,
                'error': str(e)
            }
    
    return jsonify({
        'status': 'success',
        'tables': results
    })

# Funções auxiliares
def _get_financial_table():
    """Retorna a tabela financeira disponível"""
    # Check if the view exists and has data
    try:
        # Try to use the view first
        response = supabase_admin.table('vw_fluxo_caixa').select('*').limit(1).execute()
        if len(response.data) > 0:
            return 'vw_fluxo_caixa'
    except Exception as e:
        print(f"Warning: Could not access vw_fluxo_caixa - {str(e)}")
        # If view doesn't exist or has issues, fall back to other tables
        pass
    
    # Try fin_resultado_anual
    try:
        response = supabase_admin.table('fin_resultado_anual').select('*').limit(1).execute()
        if len(response.data) > 0:
            return 'fin_resultado_anual'
    except Exception as e:
        print(f"Warning: Could not access fin_resultado_anual - {str(e)}")
        # If that doesn't work, try fin_base_resultado
        pass
    
    # Try fin_base_resultado
    try:
        response = supabase_admin.table('fin_base_resultado').select('*').limit(1).execute()
        if len(response.data) > 0:
            return 'fin_base_resultado'
    except Exception as e:
        print(f"Warning: Could not access fin_base_resultado - {str(e)}")
        # If nothing works, return the default
        pass
    
    # Default fallback - try to use the view even if we can't check it
    # This handles cases where the connection is temporarily unavailable
    return 'vw_fluxo_caixa'

def _get_periodo_dates(periodo):
    """Retorna datas de início e fim baseado no período selecionado"""
    try:
        hoje = datetime.now()
        
        # Verificar se é período personalizado (formato: data_inicio|data_fim)
        if '|' in periodo:
            try:
                data_inicio_str, data_fim_str = periodo.split('|')
                # Validate date format
                datetime.strptime(data_inicio_str, '%Y-%m-%d')
                datetime.strptime(data_fim_str, '%Y-%m-%d')
                return data_inicio_str, data_fim_str
            except (ValueError, IndexError):
                # Se não conseguir processar, usar padrão
                pass
        
        if periodo == 'mes_atual':
            inicio = hoje.replace(day=1)
            fim = hoje
        elif periodo == 'ultimo_mes':
            primeiro_dia_mes_atual = hoje.replace(day=1)
            fim = primeiro_dia_mes_atual - timedelta(days=1)
            inicio = fim.replace(day=1)
        elif periodo == 'trimestre_atual':
            mes_atual = hoje.month
            mes_inicio_trimestre = ((mes_atual - 1) // 3) * 3 + 1
            inicio = hoje.replace(month=mes_inicio_trimestre, day=1)
            fim = hoje
        elif periodo == 'ano_atual':
            inicio = hoje.replace(month=1, day=1)
            fim = hoje
        elif periodo == 'ultimos_12_meses':
            fim = hoje
            inicio = hoje - timedelta(days=365)
        elif periodo == 'ultimo_ano':
            inicio = hoje.replace(year=hoje.year - 1, month=1, day=1)
            fim = hoje.replace(year=hoje.year - 1, month=12, day=31)
        else:
            # Período padrão - últimos 12 meses
            fim = hoje
            inicio = hoje - timedelta(days=365)
        
        return inicio.strftime('%Y-%m-%d'), fim.strftime('%Y-%m-%d')
    except Exception as e:
        # Fallback to default period in case of any error
        hoje = datetime.now()
        inicio = hoje.replace(month=1, day=1)
        fim = hoje
        return inicio.strftime('%Y-%m-%d'), fim.strftime('%Y-%m-%d')

def _get_periodo_anterior_dates(periodo):
    """Retorna datas do período anterior para comparação"""
    hoje = datetime.now()
    
    if periodo == 'mes_atual':
        primeiro_dia_mes_atual = hoje.replace(day=1)
        fim = primeiro_dia_mes_atual - timedelta(days=1)
        inicio = fim.replace(day=1)
    elif periodo == 'ultimo_mes':
        # Dois meses atrás
        if hoje.month <= 2:
            inicio = hoje.replace(year=hoje.year - 1, month=hoje.month + 10, day=1)
        else:
            inicio = hoje.replace(month=hoje.month - 2, day=1)
        fim = inicio.replace(day=28)  # Simplificado
    elif periodo == 'ano_atual':
        inicio = hoje.replace(year=hoje.year - 1, month=1, day=1)
        fim = hoje.replace(year=hoje.year - 1, month=12, day=31)
    elif periodo == 'ultimos_12_meses':
        # 12 meses anteriores aos últimos 12 meses
        fim = hoje - timedelta(days=365)
        inicio = hoje - timedelta(days=730)
    else:
        # Mesmo período do ano anterior
        inicio = hoje.replace(year=hoje.year - 1, month=1, day=1)
        fim = hoje.replace(year=hoje.year - 1, month=12, day=31)
    
    return inicio.strftime('%Y-%m-%d'), fim.strftime('%Y-%m-%d')

def _calcular_variacao_percentual(valor_atual, valor_anterior):
    """Calcula variação percentual entre dois valores"""
    try:
        # Ensure we have valid numbers
        valor_atual = float(valor_atual) if valor_atual is not None else 0
        valor_anterior = float(valor_anterior) if valor_anterior is not None else 0
        
        if valor_anterior == 0:
            return 0 if valor_atual == 0 else 100
        
        return ((valor_atual - valor_anterior) / abs(valor_anterior)) * 100
    except (ValueError, TypeError, ZeroDivisionError):
        # Return 0 in case of any error
        return 0

def _calcular_burn_rate(dados):
    """Calcula o burn rate (média dos resultados negativos ou despesas líquidas)"""
    try:
        if not dados:
            return 0
        
        # Agrupar por mês usando a nova estrutura
        fluxo_mensal = defaultdict(lambda: {'entradas': 0, 'saidas': 0})
        
        for item in dados:
            try:
                # Check if required fields exist
                if 'ano_mes' not in item or 'valor_fluxo' not in item or 'tipo_movto' not in item:
                    continue
                    
                ano_mes = item['ano_mes']  # Usar o campo ano_mes da view
                valor_fluxo = float(item['valor_fluxo'])  # Sempre positivo
                
                if item['tipo_movto'] == 'Receita':
                    fluxo_mensal[ano_mes]['entradas'] += valor_fluxo
                else:  # Despesa
                    fluxo_mensal[ano_mes]['saidas'] += valor_fluxo
            except (ValueError, KeyError, TypeError):
                # Skip invalid items
                continue
        
        if not fluxo_mensal:
            return 0
        
        # Calcular burn rate como média de saídas mensais (não resultado líquido)
        total_saidas = sum(mes_data['saidas'] for mes_data in fluxo_mensal.values())
        num_meses = len(fluxo_mensal)
        
        if num_meses == 0:
            return 0
        
        # Burn rate = média de saídas por mês (gastos mensais)
        burn_rate_mensal = total_saidas / num_meses
        
        return burn_rate_mensal
    except Exception as e:
        # Return 0 in case of any error
        return 0

def _calcular_runway(saldo_atual, burn_rate):
    """Calcula o runway em meses baseado no saldo atual e gastos mensais"""
    try:
        # Ensure we have valid numbers
        saldo_atual = float(saldo_atual) if saldo_atual is not None else 0
        burn_rate = float(burn_rate) if burn_rate is not None else 0
        
        if burn_rate <= 0:
            return 999  # Se não há gastos, runway é muito alto (999 meses = ~83 anos)
        
        if saldo_atual <= 0:
            return 0  # Sem saldo, runway é zero
        
        runway_meses = abs(saldo_atual / burn_rate)  # Usar valor absoluto para garantir positivo
        
        # Limitar a um valor máximo razoável (5 anos = 60 meses)
        if runway_meses > 60:
            return 60
        
        return runway_meses
    except (ValueError, TypeError, ZeroDivisionError):
        # Return default value in case of any error
        return 999
