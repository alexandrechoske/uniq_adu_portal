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

def _add_transferencia_filter(query):
    """Add filter to exclude classes containing 'TRANSFERENCIA'"""
    return query.not_.ilike('classe', '%TRANSFERENCIA%')

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
            query_entradas = _add_transferencia_filter(query_entradas)
            response_entradas = query_entradas.execute()
            entradas_mes = sum(float(item['valor']) for item in response_entradas.data)
            
            # KPI 1 - Mês anterior para comparação
            query_entradas_anterior = supabase_admin.table(table_name).select('valor').eq('tipo', 'Receita')
            query_entradas_anterior = query_entradas_anterior.gte('data', inicio_mes_anterior.strftime('%Y-%m-%d'))
            query_entradas_anterior = query_entradas_anterior.lte('data', fim_mes_anterior.strftime('%Y-%m-%d'))
            query_entradas_anterior = _add_transferencia_filter(query_entradas_anterior)
            response_entradas_anterior = query_entradas_anterior.execute()
            entradas_mes_anterior = sum(float(item['valor']) for item in response_entradas_anterior.data)
            
            # KPI 2: Saídas no Mês
            query_saidas = supabase_admin.table(table_name).select('valor').eq('tipo', 'Despesa')
            query_saidas = query_saidas.gte('data', inicio_mes.strftime('%Y-%m-%d'))
            query_saidas = query_saidas.lte('data', fim_mes.strftime('%Y-%m-%d'))
            query_saidas = _add_transferencia_filter(query_saidas)
            response_saidas = query_saidas.execute()
            saidas_mes = sum(float(item['valor']) for item in response_saidas.data) * -1  # Multiplicar por -1 para exibir como positivo
            
            # KPI 2 - Mês anterior para comparação
            query_saidas_anterior = supabase_admin.table(table_name).select('valor').eq('tipo', 'Despesa')
            query_saidas_anterior = query_saidas_anterior.gte('data', inicio_mes_anterior.strftime('%Y-%m-%d'))
            query_saidas_anterior = query_saidas_anterior.lte('data', fim_mes_anterior.strftime('%Y-%m-%d'))
            query_saidas_anterior = _add_transferencia_filter(query_saidas_anterior)
            response_saidas_anterior = query_saidas_anterior.execute()
            saidas_mes_anterior = sum(float(item['valor']) for item in response_saidas_anterior.data) * -1
            
            # KPI 3: Resultado do Mês
            resultado_mes = entradas_mes - saidas_mes
            
            # KPI 3 - Mês anterior para comparação
            resultado_mes_anterior = entradas_mes_anterior - saidas_mes_anterior
            
            # KPI 4: Saldo Acumulado Final
            query_saldo = supabase_admin.table(table_name).select('saldo_acumulado').lte('data', fim_mes.strftime('%Y-%m-%d'))
            query_saldo = query_saldo.order('data', desc=True).limit(1)
            query_saldo = _add_transferencia_filter(query_saldo)
            response_saldo = query_saldo.execute()
            saldo_acumulado = float(response_saldo.data[0]['saldo_acumulado']) if response_saldo.data else 0
            
            # KPI 4 - Mês anterior para comparação
            query_saldo_anterior = supabase_admin.table(table_name).select('saldo_acumulado').lte('data', fim_mes_anterior.strftime('%Y-%m-%d'))
            query_saldo_anterior = query_saldo_anterior.order('data', desc=True).limit(1)
            query_saldo_anterior = _add_transferencia_filter(query_saldo_anterior)
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
            query_entradas = _add_transferencia_filter(query_entradas)
            response_entradas = query_entradas.execute()
            entradas_mes = sum(float(item['valor']) for item in response_entradas.data)
            
            # KPI 1 - Ano anterior para comparação
            query_entradas_anterior = supabase_admin.table(table_name).select('valor').eq('tipo', 'Receita')
            query_entradas_anterior = query_entradas_anterior.gte('data', inicio_ano_anterior.strftime('%Y-%m-%d'))
            query_entradas_anterior = query_entradas_anterior.lte('data', fim_ano_anterior.strftime('%Y-%m-%d'))
            query_entradas_anterior = _add_transferencia_filter(query_entradas_anterior)
            response_entradas_anterior = query_entradas_anterior.execute()
            entradas_mes_anterior = sum(float(item['valor']) for item in response_entradas_anterior.data)
            
            # KPI 2: Saídas no Ano
            query_saidas = supabase_admin.table(table_name).select('valor').eq('tipo', 'Despesa')
            query_saidas = query_saidas.gte('data', inicio_ano.strftime('%Y-%m-%d'))
            query_saidas = query_saidas.lte('data', fim_ano.strftime('%Y-%m-%d'))
            query_saidas = _add_transferencia_filter(query_saidas)
            response_saidas = query_saidas.execute()
            saidas_mes = sum(float(item['valor']) for item in response_saidas.data) * -1  # Multiplicar por -1 para exibir como positivo
            
            # KPI 2 - Ano anterior para comparação
            query_saidas_anterior = supabase_admin.table(table_name).select('valor').eq('tipo', 'Despesa')
            query_saidas_anterior = query_saidas_anterior.gte('data', inicio_ano_anterior.strftime('%Y-%m-%d'))
            query_saidas_anterior = query_saidas_anterior.lte('data', fim_ano_anterior.strftime('%Y-%m-%d'))
            query_saidas_anterior = _add_transferencia_filter(query_saidas_anterior)
            response_saidas_anterior = query_saidas_anterior.execute()
            saidas_mes_anterior = sum(float(item['valor']) for item in response_saidas_anterior.data) * -1
            
            # KPI 3: Resultado do Ano
            resultado_mes = entradas_mes - saidas_mes
            
            # KPI 3 - Ano anterior para comparação
            resultado_mes_anterior = entradas_mes_anterior - saidas_mes_anterior
            
            # KPI 4: Saldo Acumulado Final
            query_saldo = supabase_admin.table(table_name).select('saldo_acumulado').lte('data', fim_ano.strftime('%Y-%m-%d'))
            query_saldo = query_saldo.order('data', desc=True).limit(1)
            query_saldo = _add_transferencia_filter(query_saldo)
            response_saldo = query_saldo.execute()
            saldo_acumulado = float(response_saldo.data[0]['saldo_acumulado']) if response_saldo.data else 0
            
            # KPI 4 - Ano anterior para comparação
            query_saldo_anterior = supabase_admin.table(table_name).select('saldo_acumulado').lte('data', fim_ano_anterior.strftime('%Y-%m-%d'))
            query_saldo_anterior = query_saldo_anterior.order('data', desc=True).limit(1)
            query_saldo_anterior = _add_transferencia_filter(query_saldo_anterior)
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
            'dados': [], 
            'total': 0, 
            'page': page, 
            'limit': limit, 
            'total_pages': 0
        })

@fluxo_de_caixa_bp.route('/api/saldo-acumulado')
@login_required
@perfil_required('financeiro', 'fluxo_caixa')
def api_saldo_acumulado():
    """API para gráfico de evolução do saldo acumulado"""
    try:
        ano = request.args.get('ano', datetime.now().year)
        mes = request.args.get('mes', None)  # None means full year
        
        ano = int(ano)
        if mes:
            mes = int(mes)
        
        table_name = 'vw_fluxo_caixa'
        
        if mes:
            # Para um mês específico - evolução dia a dia
            query = supabase_admin.table(table_name).select('data, saldo_acumulado')
            query = query.gte('data', f'{ano}-{mes:02d}-01')
            # Calculate last day of month
            import calendar
            last_day = calendar.monthrange(ano, mes)[1]
            query = query.lte('data', f'{ano}-{mes:02d}-{last_day}')
        else:
            # Para um ano completo - evolução mensal (último saldo de cada mês)
            query = supabase_admin.table(table_name).select('data, saldo_acumulado')
            query = query.gte('data', f'{ano}-01-01')
            query = query.lte('data', f'{ano}-12-31')
        
        query = query.order('data')
        response = query.execute()
        dados = response.data
        
        if mes:
            # Para mês específico, mostrar evolução diária
            datas = []
            saldos = []
            
            for item in dados:
                data_formatada = datetime.strptime(item['data'], '%Y-%m-%d').strftime('%d/%m')
                datas.append(data_formatada)
                saldos.append(float(item['saldo_acumulado']) if item['saldo_acumulado'] else 0)
        else:
            # Para ano completo, agregar por mês (último saldo de cada mês)
            from collections import defaultdict
            saldos_mensais = defaultdict(float)
            
            for item in dados:
                data_obj = datetime.strptime(item['data'], '%Y-%m-%d')
                mes_key = data_obj.strftime('%Y-%m')
                # Keep the last (highest date) saldo for each month
                if mes_key not in saldos_mensais or data_obj.day > saldos_mensais[mes_key]['day']:
                    saldos_mensais[mes_key] = {
                        'saldo': float(item['saldo_acumulado']) if item['saldo_acumulado'] else 0,
                        'day': data_obj.day
                    }
            
            # Convert to lists and sort
            meses_ordenados = sorted(saldos_mensais.keys())
            datas = []
            saldos = []
            
            for mes_key in meses_ordenados:
                data_obj = datetime.strptime(mes_key, '%Y-%m')
                datas.append(data_obj.strftime('%b/%y'))
                saldos.append(saldos_mensais[mes_key]['saldo'])
        
        return jsonify({
            'datas': datas,
            'saldos': saldos
        })
        
    except Exception as e:
        # Log the error for debugging
        print(f"Erro na API de saldo acumulado: {str(e)}")
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
            'saldos': []
        })

# Funções auxiliares

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
        query = _add_transferencia_filter(query)
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

@fluxo_de_caixa_bp.route('/api/despesas-categoria')
@login_required
@perfil_required('financeiro', 'fluxo_caixa')
def api_despesas_categoria():
    """API para gráfico de despesas por centro de resultado/categoria/classe com drill-down triplo"""
    try:
        ano = request.args.get('ano', datetime.now().year)
        mes = request.args.get('mes', None)  # None means full year
        centro_drill = request.args.get('centro_resultado')  # Para drill-down nível 1
        categoria_drill = request.args.get('categoria')  # Para drill-down nível 2
        
        ano = int(ano)
        if mes:
            mes = int(mes)
        
        table_name = 'vw_fluxo_caixa'
        
        # Query para despesas (incluir centro_resultado na seleção)
        query = supabase_admin.table(table_name).select('data, valor, centro_resultado, categoria, classe').eq('tipo', 'Despesa')
        
        if mes:
            inicio_mes = datetime(ano, mes, 1)
            if mes == 12:
                fim_mes = datetime(ano + 1, 1, 1) - timedelta(days=1)
            else:
                fim_mes = datetime(ano, mes + 1, 1) - timedelta(days=1)
            
            query = query.gte('data', inicio_mes.strftime('%Y-%m-%d'))
            query = query.lte('data', fim_mes.strftime('%Y-%m-%d'))
        else:
            query = query.gte('data', f'{ano}-01-01')
            query = query.lte('data', f'{ano}-12-31')
        
        query = _add_transferencia_filter(query)
        response = query.execute()
        dados = response.data
        
        # Determinar o nível de drill-down
        if categoria_drill and centro_drill:
            # Nível 3: Drill-down para classes dentro de uma categoria específica de um centro de resultado
            agrupamento = defaultdict(float)
            for item in dados:
                if item['centro_resultado'] == centro_drill and item['categoria'] == categoria_drill:
                    agrupamento[item['classe']] += abs(float(item['valor']))  # Usar valor absoluto para despesas
            drill_level = 3
            drill_title = f"Classes - {categoria_drill}"
        elif centro_drill:
            # Nível 2: Drill-down para categorias dentro de um centro de resultado
            agrupamento = defaultdict(float)
            for item in dados:
                if item['centro_resultado'] == centro_drill:
                    agrupamento[item['categoria']] += abs(float(item['valor']))  # Usar valor absoluto para despesas
            drill_level = 2
            drill_title = f"Categorias - {centro_drill}"
        else:
            # Nível 1: Visão principal por centro de resultado
            agrupamento = defaultdict(float)
            for item in dados:
                agrupamento[item['centro_resultado']] += abs(float(item['valor']))  # Usar valor absoluto para despesas
            drill_level = 1
            drill_title = "Despesas por Centro de Resultado"
        
        # Converter para listas e ordenar do maior para menor
        items = list(agrupamento.items())
        items.sort(key=lambda x: x[1], reverse=True)  # Ordenação do maior para menor
        
        # Limitar a 10 itens para melhor visualização
        items = items[:10]
        
        labels = [item[0] for item in items]
        valores = [item[1] for item in items]
        
        return jsonify({
            'labels': labels,
            'valores': valores,
            'drill_level': drill_level,
            'drill_title': drill_title,
            'centro_drill': centro_drill,
            'categoria_drill': categoria_drill
        })
        
    except Exception as e:
        # Log the error for debugging
        print(f"Erro na API de despesas por categoria: {str(e)}")
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
            'drill_level': 1,
            'drill_title': 'Despesas por Centro de Resultado',
            'centro_drill': None,
            'categoria_drill': None
        })

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
        
        query = _add_transferencia_filter(query)
        
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
        
        count_query = _add_transferencia_filter(count_query)
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
    """API para gráfico de projeção de fluxo de caixa (24 meses passados + projeções da tabela fin_metas_projecoes)"""
    try:
        # Get current date
        now = datetime.now()
        table_name = 'vw_fluxo_caixa'
        
        # Calculate date range for past 24 months
        past_start = now.replace(day=1) - timedelta(days=30*24)
        
        # Query data for past 24 months
        query = supabase_admin.table(table_name).select('data, valor')
        query = query.gte('data', past_start.strftime('%Y-%m-%d'))
        query = query.lte('data', now.strftime('%Y-%m-%d'))
        query = query.order('data')
        query = _add_transferencia_filter(query)
        response = query.execute()
        dados = response.data
        
        # Group data by month for past data (resultado líquido mensal)
        fluxo_mensal = defaultdict(float)
        
        for item in dados:
            data_item = datetime.strptime(item['data'], '%Y-%m-%d')
            mes_key = data_item.strftime('%Y-%m')
            valor = float(item['valor'])
            fluxo_mensal[mes_key] += valor
        
        # Convert to lists for past data
        past_months = sorted(fluxo_mensal.keys())
        past_fluxos = [fluxo_mensal[mes] for mes in past_months]
        
        # Format dates for past data
        past_dates = []
        for mes in past_months:
            ano, mes_num = mes.split('-')
            data_temp = datetime.strptime(f"{ano}-{mes_num}-01", '%Y-%m-%d')
            mes_formatado = data_temp.strftime('%b/%Y')
            past_dates.append(mes_formatado)
        
        # Query projeções from fin_metas_projecoes table
        projecoes_query = supabase_admin.table('fin_metas_projecoes').select('ano, mes, meta').eq('tipo', 'projecao').order('ano, mes')
        projecoes_response = projecoes_query.execute()
        projecoes_dados = projecoes_response.data
        
        # Process future projections from database
        future_dates = []
        future_fluxos = []
        
        # Get last saldo for projection base (removed saldo tracking)
        
        # Group projections by year-month
        projecoes_dict = {}
        for proj in projecoes_dados:
            ano = int(proj['ano'])
            mes = int(proj['mes'])
            meta = float(proj['meta'])
            
            # Create date key
            data_proj = datetime(ano, mes, 1)
            
            # Only include future projections (after current month)
            if data_proj > now.replace(day=1):
                mes_key = f"{ano}-{mes:02d}"
                projecoes_dict[mes_key] = meta
        
        # Sort and convert projections
        future_months = sorted(projecoes_dict.keys())
        
        for mes_key in future_months:
            ano, mes_num = mes_key.split('-')
            data_temp = datetime.strptime(f"{ano}-{mes_num}-01", '%Y-%m-%d')
            mes_formatado = data_temp.strftime('%b/%Y')
            
            future_dates.append(mes_formatado)
            future_fluxos.append(projecoes_dict[mes_key])
        
        return jsonify({
            'past_dates': past_dates,
            'past_values': past_fluxos,  # Renamed for consistency with frontend
            'future_dates': future_dates,
            'future_values': future_fluxos  # Renamed for consistency with frontend
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
            'past_values': [],  # Renamed for consistency with frontend
            'future_dates': [],
            'future_values': [],  # Renamed for consistency with frontend
            'error': 'Connection error - using fallback values'
        }), 200  # Return 200 instead of 500 to prevent frontend errors