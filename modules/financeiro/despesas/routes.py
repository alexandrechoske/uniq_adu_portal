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
        response_atual = supabase_admin.table('fin_despesa_anual') \
            .select('categoria, classe, valor') \
            .gte('data', data_inicio) \
            .lte('data', data_fim) \
            .execute()
        
        if response_atual.data:
            df_atual = pd.DataFrame(response_atual.data)
            
            # Calcular KPIs
            total_despesas = df_atual['valor'].sum()
            
            # Despesas com Funcionários
            despesas_funcionarios = df_atual[
                df_atual['categoria'] == 'Despesas com Funcionários'
            ]['valor'].sum()
            
            # Folha Líquida (classe específica)
            folha_liquida = df_atual[
                df_atual['classe'] == 'SALARIOS E ORDENADOS'
            ]['valor'].sum()
            
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
                .execute()
            
            # Calcular variações
            variacoes = {}
            if response_anterior.data:
                df_anterior = pd.DataFrame(response_anterior.data)
                
                total_anterior = df_anterior['valor'].sum()
                funcionarios_anterior = df_anterior[
                    df_anterior['categoria'] == 'Despesas com Funcionários'
                ]['valor'].sum()
                folha_anterior = df_anterior[
                    df_anterior['classe'] == 'SALARIOS E ORDENADOS'
                ]['valor'].sum()
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
                response_faturamento = supabase_admin.table('faturamento_consolidado') \
                    .select('valor_total') \
                    .gte('data', data_inicio) \
                    .lte('data', data_fim) \
                    .execute()
                
                faturamento_total = 0
                if response_faturamento.data:
                    df_faturamento = pd.DataFrame(response_faturamento.data)
                    faturamento_total = df_faturamento['valor_total'].sum()
                
                percentual_folha = (folha_liquida / faturamento_total * 100) if faturamento_total > 0 else 0
            except:
                percentual_folha = 0
            
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