from flask import Blueprint, render_template, session, jsonify, request
from extensions import supabase, supabase_admin
from routes.auth import login_required, role_required
from decorators.perfil_decorators import perfil_required
from permissions import check_permission
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import json
from collections import defaultdict

# Blueprint para Despesas
despesas_bp = Blueprint(
    'fin_despesas', 
    __name__,
    url_prefix='/financeiro/despesas',
    template_folder='templates',
    static_folder='static',
    static_url_path='/financeiro/static'
)

@despesas_bp.route('/')
@login_required
@perfil_required('financeiro', 'despesas')
def index():
    """Despesas Anuais - Controle de gastos"""
    return render_template('despesas.html')

@despesas_bp.route('/api/kpis')
@login_required
def api_kpis():
    """API para KPIs principais das despesas"""
    user = session.get('user', {})
    user_role = user.get('role', '')
    
    if user_role not in ['admin', 'interno_unique']:
        return jsonify({'error': 'Acesso negado'}), 403
    
    try:
        # Obter parâmetros de período
        periodo = request.args.get('periodo', 'ano_atual')
        data_inicio, data_fim = _get_periodo_dates(periodo)
        
        # Buscar despesas do período atual
        print(f"Debug - Querying despesas from fin_despesa_anual table for period {data_inicio} to {data_fim}")
        response_atual = supabase_admin.table('fin_despesa_anual') \
            .select('categoria, classe, valor') \
            .gte('data', data_inicio) \
            .lte('data', data_fim) \
            .neq('classe', 'TRANSFERENCIA DE CONTAS') \
            .execute()
        print(f"Debug - Found {len(response_atual.data) if response_atual.data else 0} records in despesas data")
        
        if response_atual.data:
            df_atual = pd.DataFrame(response_atual.data)
            
            # Calcular KPIs
            total_despesas = df_atual['valor'].sum()
            
            # Despesas com Funcionários - buscar por várias categorias possíveis
            despesas_funcionarios_categorias = [
                'Despesas com Funcionários',
                'Funcionários',
                'Folha de Pagamento',
                'Salários',
                'Pessoal'
            ]
            
            despesas_funcionarios = 0
            for categoria in despesas_funcionarios_categorias:
                categoria_data = df_atual[
                    df_atual['categoria'].str.upper().str.contains(categoria.upper(), na=False)
                ]
                if not categoria_data.empty:
                    despesas_funcionarios += categoria_data['valor'].sum()
                    print(f"Debug - Categoria '{categoria}': {categoria_data['valor'].sum()}")
            
            # Se ainda não encontrou, mostrar todas as categorias disponíveis
            if despesas_funcionarios == 0:
                print(f"Debug - Available categories: {sorted(df_atual['categoria'].unique())}")
                # Buscar qualquer categoria que contenha 'funcionario', 'pessoal', 'salario'
                func_data = df_atual[
                    df_atual['categoria'].str.upper().str.contains('FUNCIONARIO|PESSOAL|SALARIO|FOLHA', na=False)
                ]
                if not func_data.empty:
                    despesas_funcionarios = func_data['valor'].sum()
                    print(f"Debug - Funcionários (fallback): {despesas_funcionarios}")
                    print(f"Debug - Categorias encontradas: {func_data['categoria'].unique()}")
            
            # Impostos - buscar por várias categorias possíveis
            impostos_categorias = [
                'Imposto sobre faturamento',
                'Impostos',
                'Tributos',
                'Taxas'
            ]
            
            impostos = 0
            for categoria in impostos_categorias:
                categoria_data = df_atual[
                    df_atual['categoria'].str.upper().str.contains(categoria.upper(), na=False)
                ]
                if not categoria_data.empty:
                    impostos += categoria_data['valor'].sum()
                    print(f"Debug - Categoria impostos '{categoria}': {categoria_data['valor'].sum()}")
            
            # Se ainda não encontrou, buscar por patterns
            if impostos == 0:
                impostos_data = df_atual[
                    df_atual['categoria'].str.upper().str.contains('IMPOSTO|TRIBUTO|TAXA|ICMS|IPI|ISS|PIS|COFINS', na=False)
                ]
                if not impostos_data.empty:
                    impostos = impostos_data['valor'].sum()
                    print(f"Debug - Impostos (fallback): {impostos}")
                    print(f"Debug - Categorias de impostos encontradas: {impostos_data['categoria'].unique()}")
            
            # Folha Líquida (classe específica)
            print(f"Debug - Available classes in data: {df_atual['classe'].unique()}")
            # Try exact match first
            folha_liquida_data = df_atual[
                df_atual['classe'].str.upper() == 'SALARIOS E ORDENADOS'
            ]
            folha_liquida = folha_liquida_data['valor'].sum()
            print(f"Debug - Registros de SALARIOS E ORDENADOS (exact match): {len(folha_liquida_data)}, Valor total: {folha_liquida}")
            
            # If no data found, try case-insensitive match
            if len(folha_liquida_data) == 0:
                folha_liquida_data = df_atual[
                    df_atual['classe'].str.upper().str.contains('SALARIOS', na=False)
                ]
                folha_liquida = folha_liquida_data['valor'].sum()
                print(f"Debug - Fallback registros com 'SALARIOS': {len(folha_liquida_data)}, Valor total: {folha_liquida}")
                
                # If still no data, show all classes containing 'SALARIO' for debugging
                if len(folha_liquida_data) == 0:
                    salario_classes = df_atual[df_atual['classe'].str.upper().str.contains('SALARIO', na=False)]
                    print(f"Debug - All classes containing 'SALARIO': {salario_classes['classe'].unique() if not salario_classes.empty else 'None'}")
                    
                    # Try to find any class related to payroll/salary
                    if len(salario_classes) > 0:
                        folha_liquida_data = salario_classes
                        folha_liquida = folha_liquida_data['valor'].sum()
                        print(f"Debug - Using all SALARIO classes: {len(folha_liquida_data)}, Valor total: {folha_liquida}")
            
            print(f"Debug - Final KPIs: Total={total_despesas}, Funcionários={despesas_funcionarios}, Folha={folha_liquida}, Impostos={impostos}")
            
            # Buscar período anterior para comparação
            data_inicio_anterior, data_fim_anterior = _get_periodo_anterior_dates(periodo)
            
            response_anterior = supabase_admin.table('fin_despesa_anual') \
                .select('categoria, classe, valor') \
                .gte('data', data_inicio_anterior) \
                .lte('data', data_fim_anterior) \
                .neq('classe', 'TRANSFERENCIA DE CONTAS') \
                .execute()
            
            # Calcular variações
            variacoes = {}
            if response_anterior.data:
                df_anterior = pd.DataFrame(response_anterior.data)
                
                total_anterior = df_anterior['valor'].sum()
                funcionarios_anterior = df_anterior[
                    df_anterior['categoria'] == 'Despesas com Funcionários'
                ]['valor'].sum()
                print(f"Debug - Available classes in previous period data: {df_anterior['classe'].unique()}")
                # Try exact match first
                folha_anterior_data = df_anterior[
                    df_anterior['classe'].str.upper() == 'SALARIOS E ORDENADOS'
                ]
                folha_anterior = folha_anterior_data['valor'].sum()
                print(f"Debug - Previous period registros de SALARIOS E ORDENADOS (exact match): {len(folha_anterior_data)}, Valor total: {folha_anterior}")
                
                # If no data found, try case-insensitive match
                if len(folha_anterior_data) == 0:
                    folha_anterior_data = df_anterior[
                        df_anterior['classe'].str.upper().str.contains('SALARIOS', na=False)
                    ]
                    folha_anterior = folha_anterior_data['valor'].sum()
                    print(f"Debug - Previous period fallback registros com 'SALARIOS': {len(folha_anterior_data)}, Valor total: {folha_anterior}")
                    
                    # If still no data, show all classes containing 'SALARIO' for debugging
                    if len(folha_anterior_data) == 0:
                        salario_classes = df_anterior[df_anterior['classe'].str.upper().str.contains('SALARIO', na=False)]
                        print(f"Debug - Previous period all classes containing 'SALARIO': {salario_classes['classe'].unique() if not salario_classes.empty else 'None'}")
                        
                        # Try to find any class related to payroll/salary
                        if len(salario_classes) > 0:
                            folha_anterior_data = salario_classes
                            folha_anterior = folha_anterior_data['valor'].sum()
                            print(f"Debug - Previous period using all SALARIO classes: {len(folha_anterior_data)}, Valor total: {folha_anterior}")
                impostos_anterior = df_anterior[
                    df_anterior['categoria'] == 'Imposto sobre faturamento'
                ]['valor'].sum()
                
                variacoes = {
                    'total_despesas': _calcular_variacao(total_despesas, total_anterior),
                    'despesas_funcionarios': _calcular_variacao(despesas_funcionarios, funcionarios_anterior),
                    'folha_liquida': _calcular_variacao(folha_liquida, folha_anterior),
                    'impostos': _calcular_variacao(impostos, impostos_anterior)
                }
            
            # Buscar faturamento para % Folha sobre Faturamento
            try:
                # Buscar dados de faturamento da tabela correta
                response_faturamento = supabase_admin.table('fin_faturamento_anual') \
                    .select('valor') \
                    .gte('data', data_inicio) \
                    .lte('data', data_fim) \
                    .execute()
                
                faturamento_total = 0
                if response_faturamento.data:
                    # Somar todos os valores de faturamento do período
                    faturamento_total = sum(float(item['valor']) for item in response_faturamento.data)
                    print(f"Debug - Faturamento total found: {faturamento_total}")
                else:
                    print("Debug - No faturamento data found")
                
                percentual_folha = (folha_liquida / faturamento_total * 100) if faturamento_total > 0 else 0
                
                # Debug logging
                print(f"Debug - Folha Líquida: {folha_liquida}, Faturamento Total: {faturamento_total}, Percentual: {percentual_folha}")
            except Exception as faturamento_error:
                percentual_folha = 0
                print(f"Erro ao buscar faturamento: {str(faturamento_error)}")
                import traceback
                traceback.print_exc()
            
            return jsonify({
                'success': True,
                'data': {
                    'total_despesas': float(total_despesas),
                    'despesas_funcionarios': float(despesas_funcionarios),
                    'folha_liquida': float(folha_liquida),
                    'impostos': float(impostos),
                    'percentual_folha_faturamento': float(percentual_folha),
                    'variacoes': variacoes,
                    'periodo': {
                        'inicio': data_inicio,
                        'fim': data_fim
                    }
                }
            })
        else:
            return jsonify({
                'success': True,
                'data': {
                    'total_despesas': 0,
                    'despesas_funcionarios': 0,
                    'folha_liquida': 0,
                    'impostos': 0,
                    'percentual_folha_faturamento': 0,
                    'variacoes': {},
                    'periodo': {
                        'inicio': data_inicio,
                        'fim': data_fim
                    }
                }
            })
            
    except Exception as e:
        print(f"Erro ao buscar KPIs de despesas: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@despesas_bp.route('/api/categorias')
@login_required
def api_categorias():
    """API para análise por categorias"""
    user = session.get('user', {})
    user_role = user.get('role', '')
    
    if user_role not in ['admin', 'interno_unique']:
        return jsonify({'error': 'Acesso negado'}), 403
    
    try:
        periodo = request.args.get('periodo', 'ano_atual')
        data_inicio, data_fim = _get_periodo_dates(periodo)
        
        response = supabase_admin.table('fin_despesa_anual') \
            .select('categoria, valor') \
            .gte('data', data_inicio) \
            .lte('data', data_fim) \
            .neq('classe', 'TRANSFERENCIA DE CONTAS') \
            .execute()
        
        if response.data:
            df = pd.DataFrame(response.data)
            
            # Agrupar por categoria
            categorias = df.groupby('categoria')['valor'].sum().reset_index()
            categorias = categorias.sort_values('valor', ascending=False)
            
            # Calcular percentuais
            total = categorias['valor'].sum()
            categorias['percentual'] = (categorias['valor'] / total * 100) if total > 0 else 0
            
            return jsonify({
                'success': True,
                'data': categorias.to_dict('records'),
                'total': float(total)
            })
        else:
            return jsonify({
                'success': True,
                'data': [],
                'total': 0
            })
            
    except Exception as e:
        print(f"Erro ao buscar categorias de despesas: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@despesas_bp.route('/api/centro-resultado')
@login_required
def api_centro_resultado():
    """API para análise por centro de resultado"""
    user = session.get('user', {})
    user_role = user.get('role', '')
    
    if user_role not in ['admin', 'interno_unique']:
        return jsonify({'error': 'Acesso negado'}), 403
    
    try:
        periodo = request.args.get('periodo', 'ano_atual')
        centro_resultado_filter = request.args.get('centro_resultado', '')
        categoria_filter = request.args.get('categoria', '')
        classe_filter = request.args.get('classe', '')
        
        data_inicio, data_fim = _get_periodo_dates(periodo)
        
        query = supabase_admin.table('fin_despesa_anual') \
            .select('centro_resultado, categoria, classe, valor') \
            .gte('data', data_inicio) \
            .lte('data', data_fim) \
            .neq('classe', 'TRANSFERENCIA DE CONTAS')
        
        # Aplicar filtros opcionais
        if centro_resultado_filter:
            query = query.eq('centro_resultado', centro_resultado_filter)
        if categoria_filter:
            query = query.eq('categoria', categoria_filter)
        if classe_filter:
            query = query.eq('classe', classe_filter)
        
        response = query.execute()
        
        if response.data:
            df = pd.DataFrame(response.data)
            
            # Agrupar por centro de resultado
            centros = df.groupby('centro_resultado')['valor'].sum().reset_index()
            centros = centros.sort_values('valor', ascending=False)
            
            # Calcular percentuais
            total = centros['valor'].sum()
            centros['percentual'] = (centros['valor'] / total * 100) if total > 0 else 0
            
            return jsonify({
                'success': True,
                'data': centros.to_dict('records'),
                'total': float(total)
            })
        else:
            return jsonify({
                'success': True,
                'data': [],
                'total': 0
            })
            
    except Exception as e:
        print(f"Erro ao buscar centros de resultado: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@despesas_bp.route('/api/tendencias')
@login_required
def api_tendencias():
    """API para gráfico de tendências mensais - Top 5 Centro de Resultado -> Categoria"""
    user = session.get('user', {})
    user_role = user.get('role', '')
    
    if user_role not in ['admin', 'interno_unique']:
        return jsonify({'error': 'Acesso negado'}), 403
    
    try:
        # Buscar dados dos últimos 12 meses
        data_fim = datetime.now()
        data_inicio = data_fim - timedelta(days=365)
        
        response = supabase_admin.table('fin_despesa_anual') \
            .select('data, centro_resultado, categoria, valor') \
            .gte('data', data_inicio.strftime('%Y-%m-%d')) \
            .lte('data', data_fim.strftime('%Y-%m-%d')) \
            .neq('classe', 'TRANSFERENCIA DE CONTAS') \
            .execute()
        
        if response.data:
            df = pd.DataFrame(response.data)
            df['data'] = pd.to_datetime(df['data'])
            df['mes_ano'] = df['data'].dt.to_period('M')
            
            # Encontrar top 5 centros de resultado por valor total
            top_centros = df.groupby('centro_resultado')['valor'].sum() \
                .sort_values(ascending=False).head(5).index.tolist()
            
            # Filtrar apenas os top 5 centros de resultado
            df_top = df[df['centro_resultado'].isin(top_centros)]
            
            # Criar combinação centro_resultado -> categoria
            df_top['centro_categoria'] = df_top['centro_resultado'] + ' -> ' + df_top['categoria']
            
            # Encontrar top 5 combinações centro->categoria
            top_combinacoes = df_top.groupby('centro_categoria')['valor'].sum() \
                .sort_values(ascending=False).head(5).index.tolist()
            
            # Filtrar apenas as top 5 combinações
            df_final = df_top[df_top['centro_categoria'].isin(top_combinacoes)]
            
            # Agrupar por mês e combinação centro->categoria
            tendencias = df_final.groupby(['mes_ano', 'centro_categoria'])['valor'].sum().reset_index()
            tendencias['mes_ano_str'] = tendencias['mes_ano'].astype(str)
            
            # Reorganizar dados para o gráfico
            resultado = {}
            for combinacao in top_combinacoes:
                dados_combinacao = tendencias[tendencias['centro_categoria'] == combinacao]
                resultado[combinacao] = {
                    'labels': dados_combinacao['mes_ano_str'].tolist(),
                    'valores': dados_combinacao['valor'].tolist()
                }
            
            return jsonify({
                'success': True,
                'data': resultado,
                'combinacoes': top_combinacoes
            })
        else:
            return jsonify({
                'success': True,
                'data': {},
                'combinacoes': []
            })
            
    except Exception as e:
        print(f"Erro ao buscar tendências de despesas: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@despesas_bp.route('/api/detalhes/<path:categoria>')
@login_required
def api_detalhes_categoria(categoria):
    """API para detalhes de uma categoria específica"""
    user = session.get('user', {})
    user_role = user.get('role', '')
    
    if user_role not in ['admin', 'interno_unique']:
        return jsonify({'error': 'Acesso negado'}), 403
    
    try:
        periodo = request.args.get('periodo', 'ano_atual')
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 25))
        centro_resultado_mode = request.args.get('centro_resultado', '').lower() == 'true'
        
        data_inicio, data_fim = _get_periodo_dates(periodo)
        offset = (page - 1) * limit
        
        # Query base para detalhes paginados
        query = supabase_admin.table('fin_despesa_anual') \
            .select('data, descricao, valor, classe, codigo, centro_resultado') \
            .gte('data', data_inicio) \
            .lte('data', data_fim) \
            .neq('classe', 'TRANSFERENCIA DE CONTAS') \
            .order('data', desc=True)
        
        # Query base para totais (sem paginação)
        totals_query = supabase_admin.table('fin_despesa_anual') \
            .select('valor') \
            .gte('data', data_inicio) \
            .lte('data', data_fim) \
            .neq('classe', 'TRANSFERENCIA DE CONTAS')
        
        # Aplicar filtros
        if centro_resultado_mode:
            # Se filtrado por centro de resultado
            query = query.eq('centro_resultado', categoria)
            totals_query = totals_query.eq('centro_resultado', categoria)
        else:
            # Se filtrado por categoria tradicional
            query = query.eq('categoria', categoria)
            totals_query = totals_query.eq('categoria', categoria)
        
        # Buscar detalhes paginados
        response = query.range(offset, offset + limit - 1).execute()
        
        # Buscar totais de toda a categoria/centro de resultado
        totals_response = totals_query.execute()
        
        # Contar total de registros
        count_query = supabase_admin.table('fin_despesa_anual') \
            .select('id', count='exact') \
            .gte('data', data_inicio) \
            .lte('data', data_fim) \
            .neq('classe', 'TRANSFERENCIA DE CONTAS')
        
        if centro_resultado_mode:
            count_query = count_query.eq('centro_resultado', categoria)
        else:
            count_query = count_query.eq('categoria', categoria)
        
        count_response = count_query.execute()
        
        total_records = count_response.count if count_response.count else 0
        total_pages = (total_records + limit - 1) // limit
        
        # Calcular estatísticas totais (não apenas da página atual)
        total_valor = 0
        valor_medio = 0
        if totals_response.data:
            valores = [float(item['valor']) for item in totals_response.data]
            total_valor = sum(valores)
            valor_medio = total_valor / len(valores) if len(valores) > 0 else 0
        
        return jsonify({
            'success': True,
            'data': response.data,
            'pagination': {
                'current_page': page,
                'total_pages': total_pages,
                'total_records': total_records,
                'has_next': page < total_pages,
                'has_prev': page > 1
            },
            'totals': {
                'total_valor': total_valor,
                'num_transacoes': total_records,
                'valor_medio': valor_medio
            }
        })
        
    except Exception as e:
        print(f"Erro ao buscar detalhes da categoria: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@despesas_bp.route('/api/fornecedores')
@login_required
def api_fornecedores():
    """API para ranking de fornecedores/credores"""
    user = session.get('user', {})
    user_role = user.get('role', '')
    
    if user_role not in ['admin', 'interno_unique']:
        return jsonify({'error': 'Acesso negado'}), 403
    
    try:
        periodo = request.args.get('periodo', 'ano_atual')
        data_inicio, data_fim = _get_periodo_dates(periodo)
        
        response = supabase_admin.table('fin_despesa_anual') \
            .select('descricao, valor') \
            .gte('data', data_inicio) \
            .lte('data', data_fim) \
            .neq('classe', 'TRANSFERENCIA DE CONTAS') \
            .execute()
        
        if response.data:
            df = pd.DataFrame(response.data)
            
            # Agrupar por descrição e somar valores
            fornecedores = df.groupby('descricao')['valor'].sum().reset_index()
            fornecedores = fornecedores.sort_values('valor', ascending=False).head(10)
            
            # Calcular percentual do total
            total = df['valor'].sum()
            fornecedores['percentual'] = (fornecedores['valor'] / total * 100) if total > 0 else 0
            
            return jsonify({
                'success': True,
                'data': fornecedores.to_dict('records')
            })
        else:
            return jsonify({
                'success': True,
                'data': []
            })
            
    except Exception as e:
        print(f"Erro ao buscar ranking de fornecedores: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@despesas_bp.route('/api/filtros-opcoes')
@login_required
def api_filtros_opcoes():
    """API para obter opções de filtros (centro de resultado, categoria, classe)"""
    user = session.get('user', {})
    user_role = user.get('role', '')
    
    if user_role not in ['admin', 'interno_unique']:
        return jsonify({'error': 'Acesso negado'}), 403
    
    try:
        # Buscar todos os valores únicos para os filtros
        response = supabase_admin.table('fin_despesa_anual') \
            .select('centro_resultado, categoria, classe') \
            .neq('classe', 'TRANSFERENCIA DE CONTAS') \
            .execute()
        
        if response.data:
            df = pd.DataFrame(response.data)
            
            # Obter valores únicos para cada campo
            centros_resultado = sorted(df['centro_resultado'].dropna().unique().tolist())
            categorias = sorted(df['categoria'].dropna().unique().tolist())
            classes = sorted(df['classe'].dropna().unique().tolist())
            
            return jsonify({
                'success': True,
                'data': {
                    'centros_resultado': centros_resultado,
                    'categorias': categorias,
                    'classes': classes
                }
            })
        else:
            return jsonify({
                'success': True,
                'data': {
                    'centros_resultado': [],
                    'categorias': [],
                    'classes': []
                }
            })
            
    except Exception as e:
        print(f"Erro ao buscar opções de filtros: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Funções auxiliares
def _get_periodo_dates(periodo):
    """Retorna as datas de início e fim baseado no período"""
    hoje = datetime.now()
    
    if periodo == 'mes_atual':
        inicio = hoje.replace(day=1)
        fim = hoje
    elif periodo == 'trimestre_atual':
        trimestre = (hoje.month - 1) // 3
        inicio = hoje.replace(month=trimestre * 3 + 1, day=1)
        fim = hoje
    elif periodo == 'ano_atual':
        inicio = hoje.replace(month=1, day=1)
        fim = hoje
    elif periodo == 'ultimos_12_meses':
        inicio = hoje - timedelta(days=365)
        fim = hoje
    elif periodo == 'personalizado':
        # Implementar lógica para período personalizado
        inicio = hoje.replace(month=1, day=1)
        fim = hoje
    else:
        # Padrão: ano atual
        inicio = hoje.replace(month=1, day=1)
        fim = hoje
    
    return inicio.strftime('%Y-%m-%d'), fim.strftime('%Y-%m-%d')

def _get_periodo_anterior_dates(periodo):
    """Retorna as datas do período anterior para comparação"""
    hoje = datetime.now()
    
    if periodo == 'mes_atual':
        # Mês anterior
        mes_anterior = hoje.replace(day=1) - timedelta(days=1)
        inicio = mes_anterior.replace(day=1)
        fim = mes_anterior
    elif periodo == 'trimestre_atual':
        # Trimestre anterior
        trimestre_atual = (hoje.month - 1) // 3
        if trimestre_atual == 0:
            # Se estamos no primeiro trimestre, pegar o último do ano anterior
            inicio = hoje.replace(year=hoje.year-1, month=10, day=1)
            fim = hoje.replace(year=hoje.year-1, month=12, day=31)
        else:
            inicio = hoje.replace(month=(trimestre_atual-1) * 3 + 1, day=1)
            fim = hoje.replace(month=trimestre_atual * 3, day=1) - timedelta(days=1)
    elif periodo == 'ano_atual':
        # Ano anterior
        inicio = hoje.replace(year=hoje.year-1, month=1, day=1)
        fim = hoje.replace(year=hoje.year-1, month=12, day=31)
    elif periodo == 'ultimos_12_meses':
        # 12 meses anteriores aos últimos 12
        inicio = hoje - timedelta(days=730)  # 2 anos atrás
        fim = hoje - timedelta(days=365)     # 1 ano atrás
    else:
        # Padrão: ano anterior
        inicio = hoje.replace(year=hoje.year-1, month=1, day=1)
        fim = hoje.replace(year=hoje.year-1, month=12, day=31)
    
    return inicio.strftime('%Y-%m-%d'), fim.strftime('%Y-%m-%d')

def _calcular_variacao(valor_atual, valor_anterior):
    """Calcula a variação percentual entre dois valores"""
    if valor_anterior == 0:
        return 0 if valor_atual == 0 else 100
    
    variacao = ((valor_atual - valor_anterior) / valor_anterior) * 100
    return round(variacao, 2)