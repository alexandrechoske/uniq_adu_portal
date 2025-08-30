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
        ano = request.args.get('ano', datetime.now().year)
        mes = request.args.get('mes', None)  # None means full year
        
        # Converter para inteiros
        ano = int(ano)
        if mes:
            mes = int(mes)
        
        # Verificar qual tabela usar (usar vw_fluxo_caixa como principal)
        table_name = 'vw_fluxo_caixa'
        
        if mes:
            # Calcular datas do mês selecionado
            inicio_mes = datetime(ano, mes, 1)
            if mes == 12:
                fim_mes = datetime(ano + 1, 1, 1) - timedelta(days=1)
            else:
                fim_mes = datetime(ano, mes + 1, 1) - timedelta(days=1)
            
            # Calcular datas do mês anterior para comparação
            if mes == 1:
                inicio_mes_anterior = datetime(ano - 1, 12, 1)
                fim_mes_anterior = datetime(ano - 1, 12, 31)
            else:
                inicio_mes_anterior = datetime(ano, mes - 1, 1)
                if mes == 1:
                    fim_mes_anterior = datetime(ano - 1, 12, 31)
                else:
                    fim_mes_anterior = datetime(ano, mes, 1) - timedelta(days=1)
            
            # KPI 1: Entradas no Mês
            query_entradas = supabase_admin.table(table_name).select('valor').eq('tipo', 'Receita')
            query_entradas = query_entradas.gte('data', inicio_mes.strftime('%Y-%m-%d'))
            query_entradas = query_entradas.lte('data', fim_mes.strftime('%Y-%m-%d'))
            response_entradas = query_entradas.execute()
            entradas_mes = sum(float(item['valor']) for item in response_entradas.data)
            
            # KPI 1 - Mês anterior para comparação
            query_entradas_anterior = supabase_admin.table(table_name).select('valor').eq('tipo', 'Receita')
            query_entradas_anterior = query_entradas_anterior.gte('data', inicio_mes_anterior.strftime('%Y-%m-%d'))
            query_entradas_anterior = query_entradas_anterior.lte('data', fim_mes_anterior.strftime('%Y-%m-%d'))
            response_entradas_anterior = query_entradas_anterior.execute()
            entradas_mes_anterior = sum(float(item['valor']) for item in response_entradas_anterior.data)
            
            # KPI 2: Saídas no Mês
            query_saidas = supabase_admin.table(table_name).select('valor').eq('tipo', 'Despesa')
            query_saidas = query_saidas.gte('data', inicio_mes.strftime('%Y-%m-%d'))
            query_saidas = query_saidas.lte('data', fim_mes.strftime('%Y-%m-%d'))
            response_saidas = query_saidas.execute()
            saidas_mes = sum(float(item['valor']) for item in response_saidas.data) * -1  # Multiplicar por -1 para exibir como positivo
            
            # KPI 2 - Mês anterior para comparação
            query_saidas_anterior = supabase_admin.table(table_name).select('valor').eq('tipo', 'Despesa')
            query_saidas_anterior = query_saidas_anterior.gte('data', inicio_mes_anterior.strftime('%Y-%m-%d'))
            query_saidas_anterior = query_saidas_anterior.lte('data', fim_mes_anterior.strftime('%Y-%m-%d'))
            response_saidas_anterior = query_saidas_anterior.execute()
            saidas_mes_anterior = sum(float(item['valor']) for item in response_saidas_anterior.data) * -1
            
            # KPI 3: Resultado do Mês
            resultado_mes = entradas_mes - saidas_mes
            
            # KPI 3 - Mês anterior para comparação
            resultado_mes_anterior = entradas_mes_anterior - saidas_mes_anterior
            
            # KPI 4: Saldo Acumulado Final
            query_saldo = supabase_admin.table(table_name).select('saldo_acumulado').lte('data', fim_mes.strftime('%Y-%m-%d'))
            query_saldo = query_saldo.order('data', desc=True).limit(1)
            response_saldo = query_saldo.execute()
            saldo_acumulado = float(response_saldo.data[0]['saldo_acumulado']) if response_saldo.data else 0
            
            # KPI 4 - Mês anterior para comparação
            query_saldo_anterior = supabase_admin.table(table_name).select('saldo_acumulado').lte('data', fim_mes_anterior.strftime('%Y-%m-%d'))
            query_saldo_anterior = query_saldo_anterior.order('data', desc=True).limit(1)
            response_saldo_anterior = query_saldo_anterior.execute()
            saldo_acumulado_anterior = float(response_saldo_anterior.data[0]['saldo_acumulado']) if response_saldo_anterior.data else 0
            
            # Calcular variações percentuais
            var_entradas = _calcular_variacao_percentual(entradas_mes, entradas_mes_anterior)
            var_saidas = _calcular_variacao_percentual(saidas_mes, saidas_mes_anterior)
            var_resultado = _calcular_variacao_percentual(resultado_mes, resultado_mes_anterior)
            var_saldo = _calcular_variacao_percentual(saldo_acumulado, saldo_acumulado_anterior)
        else:
            # Full year data (year-to-date if current year, else full year)
            inicio_ano = datetime(ano, 1, 1)
            # If it's the current year, show data up to today, otherwise show full year
            if ano == datetime.now().year:
                fim_ano = datetime.now()
            else:
                fim_ano = datetime(ano, 12, 31)
            
            # Calcular datas do ano anterior para comparação
            inicio_ano_anterior = datetime(ano - 1, 1, 1)
            if ano == datetime.now().year:
                fim_ano_anterior = datetime(ano - 1, datetime.now().month, datetime.now().day)
            else:
                fim_ano_anterior = datetime(ano - 1, 12, 31)
            
            # KPI 1: Entradas no Ano
            query_entradas = supabase_admin.table(table_name).select('valor').eq('tipo', 'Receita')
            query_entradas = query_entradas.gte('data', inicio_ano.strftime('%Y-%m-%d'))
            query_entradas = query_entradas.lte('data', fim_ano.strftime('%Y-%m-%d'))
            response_entradas = query_entradas.execute()
            entradas_mes = sum(float(item['valor']) for item in response_entradas.data)
            
            # KPI 1 - Ano anterior para comparação
            query_entradas_anterior = supabase_admin.table(table_name).select('valor').eq('tipo', 'Receita')
            query_entradas_anterior = query_entradas_anterior.gte('data', inicio_ano_anterior.strftime('%Y-%m-%d'))
            query_entradas_anterior = query_entradas_anterior.lte('data', fim_ano_anterior.strftime('%Y-%m-%d'))
            response_entradas_anterior = query_entradas_anterior.execute()
            entradas_mes_anterior = sum(float(item['valor']) for item in response_entradas_anterior.data)
            
            # KPI 2: Saídas no Ano
            query_saidas = supabase_admin.table(table_name).select('valor').eq('tipo', 'Despesa')
            query_saidas = query_saidas.gte('data', inicio_ano.strftime('%Y-%m-%d'))
            query_saidas = query_saidas.lte('data', fim_ano.strftime('%Y-%m-%d'))
            response_saidas = query_saidas.execute()
            saidas_mes = sum(float(item['valor']) for item in response_saidas.data) * -1  # Multiplicar por -1 para exibir como positivo
            
            # KPI 2 - Ano anterior para comparação
            query_saidas_anterior = supabase_admin.table(table_name).select('valor').eq('tipo', 'Despesa')
            query_saidas_anterior = query_saidas_anterior.gte('data', inicio_ano_anterior.strftime('%Y-%m-%d'))
            query_saidas_anterior = query_saidas_anterior.lte('data', fim_ano_anterior.strftime('%Y-%m-%d'))
            response_saidas_anterior = query_saidas_anterior.execute()
            saidas_mes_anterior = sum(float(item['valor']) for item in response_saidas_anterior.data) * -1
            
            # KPI 3: Resultado do Ano
            resultado_mes = entradas_mes - saidas_mes
            
            # KPI 3 - Ano anterior para comparação
            resultado_mes_anterior = entradas_mes_anterior - saidas_mes_anterior
            
            # KPI 4: Saldo Acumulado Final
            query_saldo = supabase_admin.table(table_name).select('saldo_acumulado').lte('data', fim_ano.strftime('%Y-%m-%d'))
            query_saldo = query_saldo.order('data', desc=True).limit(1)
            response_saldo = query_saldo.execute()
            saldo_acumulado = float(response_saldo.data[0]['saldo_acumulado']) if response_saldo.data else 0
            
            # KPI 4 - Ano anterior para comparação
            query_saldo_anterior = supabase_admin.table(table_name).select('saldo_acumulado').lte('data', fim_ano_anterior.strftime('%Y-%m-%d'))
            query_saldo_anterior = query_saldo_anterior.order('data', desc=True).limit(1)
            response_saldo_anterior = query_saldo_anterior.execute()
            saldo_acumulado_anterior = float(response_saldo_anterior.data[0]['saldo_acumulado']) if response_saldo_anterior.data else 0
            
            # Calcular variações percentuais
            var_entradas = _calcular_variacao_percentual(entradas_mes, entradas_mes_anterior)
            var_saidas = _calcular_variacao_percentual(saidas_mes, saidas_mes_anterior)
            var_resultado = _calcular_variacao_percentual(resultado_mes, resultado_mes_anterior)
            var_saldo = _calcular_variacao_percentual(saldo_acumulado, saldo_acumulado_anterior)
        
        return jsonify({
            'entradas_mes': {
                'valor': entradas_mes,
                'variacao': var_entradas
            },
            'saidas_mes': {
                'valor': saidas_mes,
                'variacao': var_saidas
            },
            'resultado_mes': {
                'valor': resultado_mes,
                'variacao': var_resultado
            },
            'saldo_acumulado': {
                'valor': saldo_acumulado,
                'variacao': var_saldo
            }
        })
        
    except Exception as e:
        # Log the error for debugging
        import traceback
        error_details = {
            'error': str(e),
            'traceback': traceback.format_exc(),
            'ano': ano if 'ano' in locals() else 'Not defined',
            'mes': mes if 'mes' in locals() else 'Not defined'
        }
        print(f"Error in api_kpis: {error_details}")  # Simple logging
        
        # Return default/fallback values instead of failing completely
        return jsonify({
            'entradas_mes': {
                'valor': 0,
                'variacao': 0
            },
            'saidas_mes': {
                'valor': 0,
                'variacao': 0
            },
            'resultado_mes': {
                'valor': 0,
                'variacao': 0
            },
            'saldo_acumulado': {
                'valor': 0,
                'variacao': 0
            },
            'error': 'Connection error - using fallback values'
        }), 200  # Return 200 instead of 500 to prevent frontend errors

@fluxo_de_caixa_bp.route('/api/fluxo-mensal')
@login_required
@perfil_required('financeiro', 'fluxo_caixa')
def api_fluxo_mensal():
    """API para gráfico de fluxo de caixa mês a mês (cascata)"""
    try:
        ano = request.args.get('ano', datetime.now().year)
        ano = int(ano)
        
        table_name = 'vw_fluxo_caixa'
        
        # SQL: SELECT TO_CHAR(data, 'YYYY-MM') AS mes, SUM(valor) AS resultado_liquido
        # FROM public.vw_fin_resultado_consolidado
        # WHERE EXTRACT(YEAR FROM data) = [ano_selecionado] AND categoria <> 'SALDO INICIAL'
        # GROUP BY mes
        # ORDER BY mes;
        
        query = supabase_admin.table(table_name).select('data, valor, categoria')
        query = query.gte('data', f'{ano}-01-01')
        query = query.lte('data', f'{ano}-12-31')
        query = query.neq('categoria', 'SALDO INICIAL')
        response = query.execute()
        dados = response.data
        
        # Agrupar por mês
        fluxo_mensal = defaultdict(float)
        
        for item in dados:
            data_item = datetime.strptime(item['data'], '%Y-%m-%d')
            mes = data_item.strftime('%Y-%m')
            valor = float(item['valor'])
            fluxo_mensal[mes] += valor
        
        # Converter para formato do gráfico
        meses = sorted(fluxo_mensal.keys())
        resultados = [fluxo_mensal[mes] for mes in meses]
        
        # Formatar nomes dos meses
        meses_formatados = []
        for mes in meses:
            ano, mes_num = mes.split('-')
            data_temp = datetime.strptime(f"{ano}-{mes_num}-01", '%Y-%m-%d')
            mes_formatado = data_temp.strftime('%b/%Y')
            meses_formatados.append(mes_formatado)
        
        return jsonify({
            'meses': meses_formatados,
            'resultados': resultados
        })
        
    except Exception as e:
        # Log the error for debugging
        import traceback
        error_details = {
            'error': str(e),
            'traceback': traceback.format_exc(),
            'ano': ano if 'ano' in locals() else 'Not defined'
        }
        print(f"Error in api_fluxo_mensal: {error_details}")  # Simple logging
        
        # Return default/fallback values instead of failing completely
        return jsonify({
            'meses': [],
            'resultados': [],
            'error': 'Connection error - using fallback values'
        }), 200  # Return 200 instead of 500 to prevent frontend errors

@fluxo_de_caixa_bp.route('/api/saldo-acumulado')
@login_required
@perfil_required('financeiro', 'fluxo_caixa')
def api_saldo_acumulado():
    """API para gráfico de evolução do saldo acumulado"""
    try:
        ano = request.args.get('ano', datetime.now().year)
        mes = request.args.get('mes', None)  # None means full year
        ano = int(ano)
        
        table_name = 'vw_fluxo_caixa'
        
        if mes:
            # Filter by specific month
            mes = int(mes)
            inicio_mes = datetime(ano, mes, 1)
            if mes == 12:
                fim_mes = datetime(ano + 1, 1, 1) - timedelta(days=1)
            else:
                fim_mes = datetime(ano, mes + 1, 1) - timedelta(days=1)
            
            query = supabase_admin.table(table_name).select('data, saldo_acumulado')
            query = query.gte('data', inicio_mes.strftime('%Y-%m-%d'))
            query = query.lte('data', fim_mes.strftime('%Y-%m-%d'))
            query = query.order('data')
        else:
            # Full year data
            query = supabase_admin.table(table_name).select('data, saldo_acumulado')
            query = query.gte('data', f'{ano}-01-01')
            query = query.lte('data', f'{ano}-12-31')
            query = query.order('data')
        
        response = query.execute()
        dados = response.data
        
        # Converter para formato do gráfico
        datas = [item['data'] for item in dados]
        saldos = [float(item['saldo_acumulado']) for item in dados]
        
        # Formatar datas
        datas_formatadas = []
        for data_str in datas:
            data_temp = datetime.strptime(data_str, '%Y-%m-%d')
            data_formatada = data_temp.strftime('%d/%m')
            datas_formatadas.append(data_formatada)
        
        return jsonify({
            'datas': datas_formatadas,
            'saldos': saldos
        })
        
    except Exception as e:
        # Log the error for debugging
        import traceback
        error_details = {
            'error': str(e),
            'traceback': traceback.format_exc(),
            'ano': ano if 'ano' in locals() else 'Not defined',
            'mes': mes if 'mes' in locals() else 'Not defined'
        }
        print(f"Error in api_saldo_acumulado: {error_details}")  # Simple logging
        
        # Return default/fallback values instead of failing completely
        return jsonify({
            'datas': [],
            'saldos': [],
            'error': 'Connection error - using fallback values'
        }), 200  # Return 200 instead of 500 to prevent frontend errors

@fluxo_de_caixa_bp.route('/api/despesas-categoria')
@login_required
@perfil_required('financeiro', 'fluxo_caixa')
def api_despesas_categoria():
    """API para gráfico de despesas por categoria com drill-down"""
    try:
        ano = request.args.get('ano', datetime.now().year)
        mes = request.args.get('mes', None)  # None means full year
        categoria_drill = request.args.get('categoria')  # Para drill-down
        
        ano = int(ano)
        if mes:
            mes = int(mes)
        
        table_name = 'vw_fluxo_caixa'
        
        # Query para despesas
        query = supabase_admin.table(table_name).select('data, valor, categoria, classe').eq('tipo', 'Despesa')
        
        if mes:
            # Filter by specific month
            inicio_mes = datetime(ano, mes, 1)
            if mes == 12:
                fim_mes = datetime(ano + 1, 1, 1) - timedelta(days=1)
            else:
                fim_mes = datetime(ano, mes + 1, 1) - timedelta(days=1)
            query = query.gte('data', inicio_mes.strftime('%Y-%m-%d'))
            query = query.lte('data', fim_mes.strftime('%Y-%m-%d'))
        else:
            # Full year data
            query = query.gte('data', f'{ano}-01-01')
            query = query.lte('data', f'{ano}-12-31')
        
        response = query.execute()
        dados = response.data
        
        if categoria_drill:
            # Drill-down: agrupar por classe dentro da categoria
            dados_filtrados = [item for item in dados if item['categoria'] == categoria_drill]
            agrupamento = defaultdict(float)
            for item in dados_filtrados:
                classe = item.get('classe', 'Sem Classe')
                valor = float(item['valor'])  # Usar valor que é sempre positivo
                agrupamento[classe] += valor
        else:
            # Visão principal: agrupar por categoria
            agrupamento = defaultdict(float)
            for item in dados:
                categoria = item.get('categoria', 'Sem Categoria')
                valor = float(item['valor'])  # Usar valor que é sempre positivo
                agrupamento[categoria] += valor
        
        # Converter para listas e ordenar do maior para menor
        items = list(agrupamento.items())
        items.sort(key=lambda x: x[1], reverse=True)  # Ordenação do maior para menor
        
        labels = [item[0] for item in items]
        valores = [item[1] for item in items]
        
        return jsonify({
            'labels': labels,
            'valores': valores,
            'drill_categoria': categoria_drill
        })
        
    except Exception as e:
        # Log the error for debugging
        import traceback
        error_details = {
            'error': str(e),
            'traceback': traceback.format_exc(),
            'ano': ano if 'ano' in locals() else 'Not defined',
            'mes': mes if 'mes' in locals() else 'Not defined'
        }
        print(f"Error in api_despesas_categoria: {error_details}")  # Simple logging
        
        # Return default/fallback values instead of failing completely
        return jsonify({
            'labels': [],
            'valores': [],
            'drill_categoria': categoria_drill if 'categoria_drill' in locals() else None,
            'error': 'Connection error - using fallback values'
        }), 200  # Return 200 instead of 500 to prevent frontend errors

@fluxo_de_caixa_bp.route('/api/tabela-dados')
@login_required
@perfil_required('financeiro', 'fluxo_caixa')
def api_tabela_dados():
    """API para dados da tabela completa"""
    try:
        ano = request.args.get('ano', datetime.now().year)
        mes = request.args.get('mes', None)  # None means full year
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))
        search = request.args.get('search', '').strip()  # Parâmetro de busca
        
        ano = int(ano)
        if mes:
            mes = int(mes)
        
        table_name = 'vw_fluxo_caixa'
        
        if mes:
            # Filter by specific month
            inicio_mes = datetime(ano, mes, 1)
            if mes == 12:
                fim_mes = datetime(ano + 1, 1, 1) - timedelta(days=1)
            else:
                fim_mes = datetime(ano, mes + 1, 1) - timedelta(days=1)
            
            # Query para dados paginados
            query = supabase_admin.table(table_name).select('*')
            query = query.gte('data', inicio_mes.strftime('%Y-%m-%d'))
            query = query.lte('data', fim_mes.strftime('%Y-%m-%d'))
        else:
            # Full year data
            query = supabase_admin.table(table_name).select('*')
            query = query.gte('data', f'{ano}-01-01')
            query = query.lte('data', f'{ano}-12-31')
        
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
        if mes:
            count_query = count_query.gte('data', inicio_mes.strftime('%Y-%m-%d'))
            count_query = count_query.lte('data', fim_mes.strftime('%Y-%m-%d'))
        else:
            count_query = count_query.gte('data', f'{ano}-01-01')
            count_query = count_query.lte('data', f'{ano}-12-31')
        
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
            'ano': ano if 'ano' in locals() else 'Not defined',
            'mes': mes if 'mes' in locals() else 'Not defined'
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

# Funções auxiliares
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

@fluxo_de_caixa_bp.route('/api/projecao')
@login_required
@perfil_required('financeiro', 'fluxo_caixa')
def api_projecao():
    """API para gráfico de projeção de fluxo de caixa (24 meses passados + 6 meses futuros)"""
    try:
        # Get current date
        now = datetime.now()
        table_name = 'vw_fluxo_caixa'
        
        # Calculate date range for past 24 months
        past_start = now.replace(day=1) - timedelta(days=30*24)
        
        # Query data for past 24 months
        query = supabase_admin.table(table_name).select('data, valor, saldo_acumulado')
        query = query.gte('data', past_start.strftime('%Y-%m-%d'))
        query = query.lte('data', now.strftime('%Y-%m-%d'))
        query = query.order('data')
        response = query.execute()
        dados = response.data
        
        # Group data by month for past data
        fluxo_mensal = defaultdict(lambda: {'valor': 0, 'saldo': 0, 'count': 0})
        
        for item in dados:
            data_item = datetime.strptime(item['data'], '%Y-%m-%d')
            mes_key = data_item.strftime('%Y-%m')
            valor = float(item['valor'])
            saldo = float(item['saldo_acumulado'])
            
            fluxo_mensal[mes_key]['valor'] += valor
            fluxo_mensal[mes_key]['saldo'] = saldo  # Use last saldo of the month
            fluxo_mensal[mes_key]['count'] += 1
        
        # Convert to lists for past data
        past_months = sorted(fluxo_mensal.keys())
        past_fluxos = [fluxo_mensal[mes]['valor'] for mes in past_months]
        past_saldos = [fluxo_mensal[mes]['saldo'] for mes in past_months]
        
        # Format dates for past data
        past_dates = []
        for mes in past_months:
            ano, mes_num = mes.split('-')
            data_temp = datetime.strptime(f"{ano}-{mes_num}-01", '%Y-%m-%d')
            mes_formatado = data_temp.strftime('%b/%Y')
            past_dates.append(mes_formatado)
        
        # Simple projection for next 6 months (using average of last 6 months)
        if len(past_fluxos) >= 6:
            # Calculate average of last 6 months for projection
            last_6_months = past_fluxos[-6:]
            avg_fluxo = sum(last_6_months) / len(last_6_months)
            
            # Generate next 6 months dates
            future_dates = []
            future_fluxos = []
            
            for i in range(1, 7):  # Next 6 months
                future_date = now + timedelta(days=30*i)
                mes_formatado = future_date.strftime('%b/%Y')
                future_dates.append(mes_formatado)
                future_fluxos.append(avg_fluxo)  # Simple projection
            
            # For saldo projection, continue from last saldo
            last_saldo = past_saldos[-1] if past_saldos else 0
            future_saldos = []
            current_saldo = last_saldo
            
            for fluxo in future_fluxos:
                current_saldo += fluxo
                future_saldos.append(current_saldo)
        else:
            # Not enough data for projection
            future_dates = []
            future_fluxos = []
            future_saldos = []
        
        return jsonify({
            'past_dates': past_dates,
            'past_fluxos': past_fluxos,
            'past_saldos': past_saldos,
            'future_dates': future_dates,
            'future_fluxos': future_fluxos,
            'future_saldos': future_saldos
        })
        
    except Exception as e:
        # Log the error for debugging
        import traceback
        error_details = {
            'error': str(e),
            'traceback': traceback.format_exc()
        }
        print(f"Error in api_projecao: {error_details}")  # Simple logging
        
        # Return default/fallback values instead of failing completely
        return jsonify({
            'past_dates': [],
            'past_fluxos': [],
            'past_saldos': [],
            'future_dates': [],
            'future_fluxos': [],
            'future_saldos': [],
            'error': 'Connection error - using fallback values'
        }), 200  # Return 200 instead of 500 to prevent frontend errors
