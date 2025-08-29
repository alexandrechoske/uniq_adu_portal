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
            
            # Despesas com Funcionários
            despesas_funcionarios = df_atual[
                df_atual['categoria'] == 'Despesas com Funcionários'
            ]['valor'].sum()
            
            # Folha Líquida (classe específica)
            print(f"Debug - Available classes in data: {df_atual['classe'].unique()}")
            print(f"Debug - Available categories in data: {df_atual['categoria'].unique()}")
            
            # Show all unique class names for debugging
            if 'classe' in df_atual.columns:
                all_classes = df_atual['classe'].dropna().unique()
                print(f"Debug - All non-null class names: {all_classes}")
            
            # First try exact match for "SALARIOS E ORDENADOS" as specified in the requirements
            folha_liquida_data = df_atual[
                df_atual['classe'] == 'SALARIOS E ORDENADOS'
            ]
            folha_liquida = folha_liquida_data['valor'].sum()
            print(f"Debug - Registros com 'SALARIOS E ORDENADOS' (exact match): {len(folha_liquida_data)}, Valor total: {folha_liquida}")
            
            # If no exact match, try case-insensitive match
            if len(folha_liquida_data) == 0:
                folha_liquida_data = df_atual[
                    df_atual['classe'].str.upper() == 'SALARIOS E ORDENADOS'
                ]
                folha_liquida = folha_liquida_data['valor'].sum()
                print(f"Debug - Registros com 'SALARIOS E ORDENADOS' (case-insensitive): {len(folha_liquida_data)}, Valor total: {folha_liquida}")
            
            # If still no data, try pattern matching as fallback
            if len(folha_liquida_data) == 0:
                folha_class_patterns = [
                    'SALÁRIOS E ORDENADOS',
                    'SALARIOS',
                    'SALÁRIOS',
                    'SALARIO',
                    'SALÁRIO',
                    'FOLHA DE PAGAMENTO'
                ]
                
                # Try each pattern until we find data
                for pattern in folha_class_patterns:
                    folha_liquida_data = df_atual[
                        df_atual['classe'].str.upper().str.contains(pattern, na=False)
                    ]
                    folha_liquida = folha_liquida_data['valor'].sum()
                    print(f"Debug - Registros com '{pattern}': {len(folha_liquida_data)}, Valor total: {folha_liquida}")
                    
                    if len(folha_liquida_data) > 0:
                        break
            
            # If still no data, try looking in categories as well
            if len(folha_liquida_data) == 0:
                folha_category_patterns = [
                    'Despesas com Funcionários',
                    'Folha de Pagamento',
                    'Salários'
                ]
                
                for pattern in folha_category_patterns:
                    folha_liquida_data = df_atual[
                        df_atual['categoria'].str.upper().str.contains(pattern, na=False)
                    ]
                    folha_liquida = folha_liquida_data['valor'].sum()
                    print(f"Debug - Registros com categoria '{pattern}': {len(folha_liquida_data)}, Valor total: {folha_liquida}")
                    
                    if len(folha_liquida_data) > 0:
                        break
            
            # If still no data, show all unique categories for debugging
            if len(folha_liquida_data) == 0 and 'categoria' in df_atual.columns:
                all_categories = df_atual['categoria'].dropna().unique()
                print(f"Debug - All non-null categories: {all_categories}")
            
            # Impostos
            impostos = df_atual[
                df_atual['categoria'] == 'Imposto sobre faturamento'
            ]['valor'].sum()
            
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
                
                # Calculate folha liquida for previous period using same logic
                folha_anterior = 0
                folha_anterior_data = pd.DataFrame()
                
                # First try exact match for "SALARIOS E ORDENADOS" as specified in the requirements
                folha_anterior_data = df_anterior[
                    df_anterior['classe'] == 'SALARIOS E ORDENADOS'
                ]
                folha_anterior = folha_anterior_data['valor'].sum()
                print(f"Debug - Previous period registros com 'SALARIOS E ORDENADOS' (exact match): {len(folha_anterior_data)}, Valor total: {folha_anterior}")
                
                # If no exact match, try case-insensitive match
                if len(folha_anterior_data) == 0:
                    folha_anterior_data = df_anterior[
                        df_anterior['classe'].str.upper() == 'SALARIOS E ORDENADOS'
                    ]
                    folha_anterior = folha_anterior_data['valor'].sum()
                    print(f"Debug - Previous period registros com 'SALARIOS E ORDENADOS' (case-insensitive): {len(folha_anterior_data)}, Valor total: {folha_anterior}")
                
                # If still no data, try pattern matching as fallback
                if len(folha_anterior_data) == 0:
                    # Try each pattern until we find data
                    for pattern in folha_class_patterns:
                        folha_anterior_data = df_anterior[
                            df_anterior['classe'].str.upper().str.contains(pattern, na=False)
                        ]
                        folha_anterior = folha_anterior_data['valor'].sum()
                        print(f"Debug - Previous period registros com '{pattern}': {len(folha_anterior_data)}, Valor total: {folha_anterior}")
                        
                        if len(folha_anterior_data) > 0:
                            break
                
                # If still no data, try looking in categories as well
                if len(folha_anterior_data) == 0:
                    for pattern in folha_category_patterns:
                        folha_anterior_data = df_anterior[
                            df_anterior['categoria'].str.upper().str.contains(pattern, na=False)
                        ]
                        folha_anterior = folha_anterior_data['valor'].sum()
                        print(f"Debug - Previous period registros com categoria '{pattern}': {len(folha_anterior_data)}, Valor total: {folha_anterior}")
                        
                        if len(folha_anterior_data) > 0:
                            break
                
                impostos_anterior = df_anterior[
                    df_anterior['categoria'] == 'Imposto sobre faturamento'
                ]['valor'].sum()
                
                variacoes = {
                    'total_despesas': _calcular_variacao(total_despesas, total_anterior),
                    'despesas_funcionarios': _calcular_variacao(despesas_funcionarios, funcionarios_anterior),
                    'folha_liquida': _calcular_variacao(folha_liquida, folha_anterior),
                    'impostos': _calcular_variacao(impostos, impostos_anterior)
                }
            else:
                # If no previous period data, set variations to None or 0
                variacoes = {
                    'total_despesas': None,
                    'despesas_funcionarios': None,
                    'folha_liquida': None,
                    'impostos': None
                }
            
            # Buscar faturamento para % Folha sobre Faturamento
            try:
                faturamento_total = 0
                
                # According to documentation and user requirements, use fin_faturamento_anual with valor column
                print(f"Debug - Trying to get faturamento data from fin_faturamento_anual using column valor")
                
                response_faturamento = supabase_admin.table('fin_faturamento_anual') \
                    .select('valor') \
                    .gte('data', data_inicio) \
                    .lte('data', data_fim) \
                    .execute()
                
                if response_faturamento.data:
                    df_faturamento = pd.DataFrame(response_faturamento.data)
                    print(f"Debug - fin_faturamento_anual data columns: {df_faturamento.columns.tolist()}")
                    print(f"Debug - fin_faturamento_anual data sample: {df_faturamento.head()}")
                    
                    if 'valor' in df_faturamento.columns:
                        faturamento_total = df_faturamento['valor'].sum()
                        print(f"Debug - Faturamento total from fin_faturamento_anual: {faturamento_total}")
                    else:
                        print(f"Debug - Column valor not found in fin_faturamento_anual")
                else:
                    print(f"Debug - No data found in fin_faturamento_anual")
                
                # Only try alternative tables if the primary table didn't work
                if faturamento_total == 0:
                    print("Debug - Primary faturamento table didn't work, trying alternatives...")
                    # According to documentation, try these tables in order:
                    # 1. fin_faturamento_anual (primary) - already tried above with correct column
                    # 2. fin_resultado_anual WHERE tipo = 'Receita' (alternative)
                    # 3. vw_fluxo_caixa WHERE tipo_movto = 'Receita' (detail)
                    
                    table_attempts = [
                        {'name': 'fin_resultado_anual', 'column': 'valor', 'filter': {'tipo': 'Receita'}},
                        {'name': 'vw_fluxo_caixa', 'column': 'valor_fluxo', 'filter': {'tipo_movto': 'Receita'}}
                    ]
                    
                    # First, let's check what tables actually exist and have data
                    print("Debug - Checking available tables...")
                    for table_info in table_attempts:
                        try:
                            table_name = table_info['name']
                            print(f"Debug - Checking table: {table_name}")
                            # Try to get a small sample of data
                            sample_query = supabase_admin.table(table_name).select('*').limit(1)
                            sample_response = sample_query.execute()
                            if sample_response.data:
                                print(f"Debug - Table {table_name} exists and has data")
                            else:
                                print(f"Debug - Table {table_name} exists but has no data")
                        except Exception as sample_error:
                            print(f"Debug - Table {table_info['name']} not accessible: {str(sample_error)}")
                    
                    for table_info in table_attempts:
                        try:
                            table_name = table_info['name']
                            column_name = table_info['column']
                            filter_conditions = table_info['filter']
                            
                            print(f"Debug - Trying to get faturamento data from {table_name} using column {column_name}")
                            
                            query = supabase_admin.table(table_name).select(column_name) \
                                .gte('data', data_inicio) \
                                .lte('data', data_fim)
                            
                            # Apply filter conditions if any
                            if filter_conditions:
                                for key, value in filter_conditions.items():
                                    query = query.eq(key, value)
                            
                            response_faturamento = query.execute()
                            
                            if response_faturamento.data:
                                df_faturamento = pd.DataFrame(response_faturamento.data)
                                print(f"Debug - {table_name} data columns: {df_faturamento.columns.tolist()}")
                                print(f"Debug - {table_name} data sample: {df_faturamento.head()}")
                                
                                if column_name in df_faturamento.columns:
                                    faturamento_total = df_faturamento[column_name].sum()
                                    print(f"Debug - Faturamento total from {table_name}: {faturamento_total}")
                                    if faturamento_total > 0:
                                        break  # Found valid data, exit loop
                                else:
                                    print(f"Debug - Column {column_name} not found in {table_name}")
                            else:
                                print(f"Debug - No data found in {table_name}")
                        except Exception as table_error:
                            print(f"Debug - Error accessing {table_info['name']}: {str(table_error)}")
                            continue
                
                percentual_folha = 0
                if faturamento_total and faturamento_total > 0:
                    try:
                        # Ensure we have valid numbers
                        folha_liquida_float = float(folha_liquida) if folha_liquida is not None else 0
                        faturamento_total_float = float(faturamento_total) if faturamento_total is not None else 0
                        
                        if faturamento_total_float > 0:
                            percentual_folha = (folha_liquida_float / faturamento_total_float) * 100
                            print(f"Debug - Calculated percentual: ({folha_liquida_float} / {faturamento_total_float}) * 100 = {percentual_folha}")
                        else:
                            print(f"Debug - Faturamento total is zero or negative: {faturamento_total_float}")
                    except (ValueError, TypeError) as calc_error:
                        print(f"Debug - Error calculating percentual: {str(calc_error)}")
                        percentual_folha = 0
                else:
                    print(f"Debug - Faturamento total is zero or None: {faturamento_total}")
                
                # Debug logging
                print(f"Debug - Folha Líquida: {folha_liquida}, Faturamento Total: {faturamento_total}, Percentual: {percentual_folha}")
                
                # Store faturamento_total in the response for debugging
                response_data = {
                    'total_despesas': float(total_despesas),
                    'despesas_funcionarios': float(despesas_funcionarios),
                    'folha_liquida': float(folha_liquida),
                    'impostos': float(impostos),
                    'percentual_folha_faturamento': float(percentual_folha),
                    'faturamento_total': float(faturamento_total) if faturamento_total else 0,  # Add this for debugging
                    'variacoes': variacoes,
                    'periodo': {
                        'inicio': data_inicio,
                        'fim': data_fim
                    }
                }
                print(f"Debug - Response data: {response_data}")
                return jsonify({
                    'success': True,
                    'data': response_data
                })
            except Exception as faturamento_error:
                percentual_folha = 0
                print(f"Erro ao buscar faturamento: {str(faturamento_error)}")
                import traceback
                traceback.print_exc()
            
            # This part should not be reached, but just in case
            return jsonify({
                'success': True,
                'data': {
                    'total_despesas': float(total_despesas),
                    'despesas_funcionarios': float(despesas_funcionarios),
                    'folha_liquida': float(folha_liquida),
                    'impostos': float(impostos),
                    'percentual_folha_faturamento': float(percentual_folha),
                    'faturamento_total': 0,  # Add this for debugging
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
        import traceback
        traceback.print_exc()
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

@despesas_bp.route('/api/tendencias')
@login_required
def api_tendencias():
    """API para gráfico de tendências mensais"""
    user = session.get('user', {})
    user_role = user.get('role', '')
    
    if user_role not in ['admin', 'interno_unique']:
        return jsonify({'error': 'Acesso negado'}), 403
    
    try:
        # Buscar dados dos últimos 12 meses
        data_fim = datetime.now()
        data_inicio = data_fim - timedelta(days=365)
        
        response = supabase_admin.table('fin_despesa_anual') \
            .select('data, categoria, valor') \
            .gte('data', data_inicio.strftime('%Y-%m-%d')) \
            .lte('data', data_fim.strftime('%Y-%m-%d')) \
            .neq('classe', 'TRANSFERENCIA DE CONTAS') \
            .execute()
        
        if response.data:
            df = pd.DataFrame(response.data)
            df['data'] = pd.to_datetime(df['data'])
            df['mes_ano'] = df['data'].dt.to_period('M')
            
            # Encontrar top 5 categorias por valor total
            top_categorias = df.groupby('categoria')['valor'].sum() \
                .sort_values(ascending=False).head(5).index.tolist()
            
            # Filtrar apenas as top 5 categorias
            df_top = df[df['categoria'].isin(top_categorias)]
            
            # Agrupar por mês e categoria
            tendencias = df_top.groupby(['mes_ano', 'categoria'])['valor'].sum().reset_index()
            tendencias['mes_ano_str'] = tendencias['mes_ano'].astype(str)
            
            # Reorganizar dados para o gráfico
            resultado = {}
            for categoria in top_categorias:
                dados_categoria = tendencias[tendencias['categoria'] == categoria]
                resultado[categoria] = {
                    'labels': dados_categoria['mes_ano_str'].tolist(),
                    'valores': dados_categoria['valor'].tolist()
                }
            
            return jsonify({
                'success': True,
                'data': resultado,
                'categorias': top_categorias
            })
        else:
            return jsonify({
                'success': True,
                'data': {},
                'categorias': []
            })
            
    except Exception as e:
        print(f"Erro ao buscar tendências de despesas: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@despesas_bp.route('/api/detalhes/<categoria>')
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
        
        data_inicio, data_fim = _get_periodo_dates(periodo)
        offset = (page - 1) * limit
        
        # Buscar detalhes da categoria
        response = supabase_admin.table('fin_despesa_anual') \
            .select('data, descricao, valor, classe, codigo') \
            .eq('categoria', categoria) \
            .gte('data', data_inicio) \
            .lte('data', data_fim) \
            .neq('classe', 'TRANSFERENCIA DE CONTAS') \
            .order('data', desc=True) \
            .range(offset, offset + limit - 1) \
            .execute()
        
        # Contar total de registros
        count_response = supabase_admin.table('fin_despesa_anual') \
            .select('id', count='exact') \
            .eq('categoria', categoria) \
            .gte('data', data_inicio) \
            .lte('data', data_fim) \
            .execute()
        
        total_records = count_response.count if count_response.count else 0
        total_pages = (total_records + limit - 1) // limit
        
        return jsonify({
            'success': True,
            'data': response.data,
            'pagination': {
                'current_page': page,
                'total_pages': total_pages,
                'total_records': total_records,
                'has_next': page < total_pages,
                'has_prev': page > 1
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

# Funções auxiliares
def _get_periodo_dates(periodo):
    """Retorna as datas de início e fim baseado no período"""
    hoje = datetime.now()
    
    if periodo == 'mes_atual':
        inicio = hoje.replace(day=1)
        # Set fim to the last day of the current month
        if hoje.month == 12:
            fim = hoje.replace(year=hoje.year+1, month=1, day=1) - timedelta(days=1)
        else:
            fim = hoje.replace(month=hoje.month+1, day=1) - timedelta(days=1)
    elif periodo == 'trimestre_atual':
        trimestre = (hoje.month - 1) // 3
        inicio = hoje.replace(month=trimestre * 3 + 1, day=1)
        # Set fim to the last day of the current quarter
        if (trimestre + 1) * 3 > 12:
            fim = hoje.replace(year=hoje.year+1, month=1, day=1) - timedelta(days=1)
        else:
            fim = hoje.replace(month=(trimestre + 1) * 3 + 1, day=1) - timedelta(days=1)
    elif periodo == 'ano_atual':
        inicio = hoje.replace(month=1, day=1)
        # Set fim to the last day of the current year
        fim = hoje.replace(year=hoje.year, month=12, day=31)
    elif periodo == 'ultimos_12_meses':
        fim = hoje.replace(year=hoje.year, month=hoje.month, day=1) - timedelta(days=1)
        inicio = fim - timedelta(days=365)
    elif periodo == 'personalizado':
        # Implementar lógica para período personalizado
        inicio = hoje.replace(month=1, day=1)
        fim = hoje.replace(year=hoje.year, month=12, day=31)
    else:
        # Padrão: ano atual
        inicio = hoje.replace(month=1, day=1)
        fim = hoje.replace(year=hoje.year, month=12, day=31)
    
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