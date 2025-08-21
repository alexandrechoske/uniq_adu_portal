from flask import Blueprint, render_template, session, jsonify, request
from extensions import supabase, supabase_admin
from routes.auth import login_required, role_required
from permissions import check_permission
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
def index():
    """Fluxo de Caixa - Controle de entradas e saídas"""
    user = session.get('user', {})
    user_role = user.get('role', '')
    
    # Verificar permissões - apenas admin e interno_unique
    if user_role not in ['admin', 'interno_unique']:
        return render_template('errors/403.html'), 403
    
    return render_template('fluxo_de_caixa.html')

@fluxo_de_caixa_bp.route('/api/kpis')
@login_required
def api_kpis():
    """API para KPIs principais do fluxo de caixa"""
    user = session.get('user', {})
    user_role = user.get('role', '')
    
    if user_role not in ['admin', 'interno_unique']:
        return jsonify({'error': 'Acesso negado'}), 403
    
    try:
        # Obter parâmetros de período
        periodo = request.args.get('periodo', 'ano_atual')
        data_inicio, data_fim = _get_periodo_dates(periodo)
        
        # Verificar qual tabela usar (priorizar fin_resultado_anual se existir)
        table_name = _get_financial_table()
        
        # Buscar dados do período atual
        query = supabase_admin.table(table_name).select('*')
        if data_inicio and data_fim:
            query = query.gte('data', data_inicio).lte('data', data_fim)
        
        response = query.execute()
        dados_periodo = response.data
        
        # Calcular KPIs do período atual
        total_entradas = sum(float(item['valor']) for item in dados_periodo if item['tipo'] == 'Receita')
        total_saidas = sum(float(item['valor']) for item in dados_periodo if item['tipo'] == 'Despesa')
        resultado_liquido = total_entradas - total_saidas
        
        # Buscar dados do período anterior para comparação
        data_inicio_anterior, data_fim_anterior = _get_periodo_anterior_dates(periodo)
        
        query_anterior = supabase_admin.table(table_name).select('*')
        if data_inicio_anterior and data_fim_anterior:
            query_anterior = query_anterior.gte('data', data_inicio_anterior).lte('data', data_fim_anterior)
        
        response_anterior = query_anterior.execute()
        dados_anterior = response_anterior.data
        
        # Calcular KPIs do período anterior
        entradas_anterior = sum(float(item['valor']) for item in dados_anterior if item['tipo'] == 'Receita')
        saidas_anterior = sum(float(item['valor']) for item in dados_anterior if item['tipo'] == 'Despesa')
        resultado_anterior = entradas_anterior - saidas_anterior
        
        # Calcular variações percentuais
        var_entradas = _calcular_variacao_percentual(total_entradas, entradas_anterior)
        var_saidas = _calcular_variacao_percentual(total_saidas, saidas_anterior)
        var_resultado = _calcular_variacao_percentual(resultado_liquido, resultado_anterior)
        
        # Calcular saldo acumulado (simplificado)
        saldo_final = resultado_liquido
        
        # Calcular indicadores estratégicos
        burn_rate = _calcular_burn_rate(dados_periodo)
        runway = _calcular_runway(saldo_final, burn_rate)
        
        return jsonify({
            'resultado_liquido': {
                'valor': resultado_liquido,
                'variacao': var_resultado
            },
            'total_entradas': {
                'valor': total_entradas,
                'variacao': var_entradas
            },
            'total_saidas': {
                'valor': total_saidas,
                'variacao': var_saidas
            },
            'saldo_final': {
                'valor': saldo_final,
                'variacao': 0  # Para implementação futura
            },
            'burn_rate': burn_rate,
            'runway': runway,
            'table_used': table_name  # Info para debug
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@fluxo_de_caixa_bp.route('/api/despesas-categoria')
@login_required
def api_despesas_categoria():
    """API para gráfico de despesas por categoria"""
    user = session.get('user', {})
    user_role = user.get('role', '')
    
    if user_role not in ['admin', 'interno_unique']:
        return jsonify({'error': 'Acesso negado'}), 403
    
    try:
        periodo = request.args.get('periodo', 'ano_atual')
        categoria_drill = request.args.get('categoria')  # Para drill-down
        
        data_inicio, data_fim = _get_periodo_dates(periodo)
        table_name = _get_financial_table()
        
        query = supabase_admin.table(table_name).select('*').eq('tipo', 'Despesa')
        if data_inicio and data_fim:
            query = query.gte('data', data_inicio).lte('data', data_fim)
        
        response = query.execute()
        dados = response.data
        
        if categoria_drill:
            # Drill-down: agrupar por classe dentro da categoria
            dados_filtrados = [item for item in dados if item['categoria'] == categoria_drill]
            agrupamento = defaultdict(float)
            for item in dados_filtrados:
                agrupamento[item['classe']] += float(item['valor'])
        else:
            # Visão principal: agrupar por categoria
            agrupamento = defaultdict(float)
            for item in dados:
                agrupamento[item['categoria']] += float(item['valor'])
        
        # Converter para formato do gráfico
        labels = list(agrupamento.keys())
        valores = list(agrupamento.values())
        
        return jsonify({
            'labels': labels,
            'valores': valores,
            'drill_categoria': categoria_drill
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@fluxo_de_caixa_bp.route('/api/fluxo-mensal')
@login_required
def api_fluxo_mensal():
    """API para gráfico de fluxo de caixa mês a mês (cascata)"""
    user = session.get('user', {})
    user_role = user.get('role', '')
    
    if user_role not in ['admin', 'interno_unique']:
        return jsonify({'error': 'Acesso negado'}), 403
    
    try:
        periodo = request.args.get('periodo', 'ano_atual')
        data_inicio, data_fim = _get_periodo_dates(periodo)
        table_name = _get_financial_table()
        
        query = supabase_admin.table(table_name).select('*')
        if data_inicio and data_fim:
            query = query.gte('data', data_inicio).lte('data', data_fim)
        
        response = query.execute()
        dados = response.data
        
        # Agrupar por mês
        fluxo_mensal = defaultdict(lambda: {'entradas': 0, 'saidas': 0})
        
        for item in dados:
            data_item = datetime.strptime(item['data'], '%Y-%m-%d')
            mes_key = data_item.strftime('%Y-%m')
            
            if item['tipo'] == 'Receita':
                fluxo_mensal[mes_key]['entradas'] += float(item['valor'])
            else:
                fluxo_mensal[mes_key]['saidas'] += float(item['valor'])
        
        # Converter para formato do gráfico
        meses = sorted(fluxo_mensal.keys())
        resultados = []
        saldo_acumulado = []
        saldo_atual = 0
        
        for mes in meses:
            resultado_mes = fluxo_mensal[mes]['entradas'] - fluxo_mensal[mes]['saidas']
            resultados.append(resultado_mes)
            saldo_atual += resultado_mes
            saldo_acumulado.append(saldo_atual)
        
        return jsonify({
            'meses': [datetime.strptime(mes, '%Y-%m').strftime('%b/%Y') for mes in meses],
            'resultados': resultados,
            'saldo_acumulado': saldo_acumulado
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@fluxo_de_caixa_bp.route('/api/fluxo-estrutural')
@login_required
def api_fluxo_estrutural():
    """API para análise estrutural do caixa (FCO, FCI, FCF)"""
    user = session.get('user', {})
    user_role = user.get('role', '')
    
    if user_role not in ['admin', 'interno_unique']:
        return jsonify({'error': 'Acesso negado'}), 403
    
    try:
        periodo = request.args.get('periodo', 'ano_atual')
        data_inicio, data_fim = _get_periodo_dates(periodo)
        table_name = _get_financial_table()
        
        query = supabase_admin.table(table_name).select('*')
        if data_inicio and data_fim:
            query = query.gte('data', data_inicio).lte('data', data_fim)
        
        response = query.execute()
        dados = response.data
        
        # Classificar por tipo de fluxo baseado na categoria
        classificacao_fluxo = {
            'FCO': ['IMPORTAÇÃO', 'EXPORTAÇÃO', 'CONSULTORIA', 'DESPESAS COM FUNCIONÁRIOS', 'DIRETORIA', 'IMPOSTOS', 'DESPESAS OPERACIONAIS', 'COMERCIAIS', 'ADMINISTRATIVAS'],
            'FCI': ['ATIVO'],
            'FCF': ['EMPRÉSTIMOS', 'RENDIMENTO']
        }
        
        # Agrupar por mês e tipo de fluxo
        fluxo_estrutural = defaultdict(lambda: {'FCO': 0, 'FCI': 0, 'FCF': 0})
        
        for item in dados:
            data_item = datetime.strptime(item['data'], '%Y-%m-%d')
            mes_key = data_item.strftime('%Y-%m')
            categoria = item['categoria'].upper()
            valor = float(item['valor'])
            
            # Aplicar sinal correto (receita positiva, despesa negativa)
            if item['tipo'] == 'Despesa':
                valor = -valor
            
            # Classificar em FCO, FCI ou FCF
            tipo_fluxo = 'FCO'  # Default
            for fluxo, categorias in classificacao_fluxo.items():
                if any(cat in categoria for cat in categorias):
                    tipo_fluxo = fluxo
                    break
            
            fluxo_estrutural[mes_key][tipo_fluxo] += valor
        
        # Converter para formato do gráfico
        meses = sorted(fluxo_estrutural.keys())
        fco_valores = [fluxo_estrutural[mes]['FCO'] for mes in meses]
        fci_valores = [fluxo_estrutural[mes]['FCI'] for mes in meses]
        fcf_valores = [fluxo_estrutural[mes]['FCF'] for mes in meses]
        
        return jsonify({
            'meses': [datetime.strptime(mes, '%Y-%m').strftime('%b/%Y') for mes in meses],
            'fco': fco_valores,
            'fci': fci_valores,
            'fcf': fcf_valores
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@fluxo_de_caixa_bp.route('/api/projecao')
@login_required
def api_projecao():
    """API para projeção de fluxo de caixa"""
    user = session.get('user', {})
    user_role = user.get('role', '')
    
    if user_role not in ['admin', 'interno_unique']:
        return jsonify({'error': 'Acesso negado'}), 403
    
    try:
        # Buscar dados dos últimos 6 meses para base da projeção
        data_fim = datetime.now()
        data_inicio = data_fim - timedelta(days=180)
        table_name = _get_financial_table()
        
        query = supabase_admin.table(table_name).select('*')
        query = query.gte('data', data_inicio.strftime('%Y-%m-%d'))
        query = query.lte('data', data_fim.strftime('%Y-%m-%d'))
        
        response = query.execute()
        dados = response.data
        
        # Calcular médias mensais dos últimos 6 meses
        fluxo_mensal = defaultdict(lambda: {'entradas': 0, 'saidas': 0})
        
        for item in dados:
            data_item = datetime.strptime(item['data'], '%Y-%m-%d')
            mes_key = data_item.strftime('%Y-%m')
            
            if item['tipo'] == 'Receita':
                fluxo_mensal[mes_key]['entradas'] += float(item['valor'])
            else:
                fluxo_mensal[mes_key]['saidas'] += float(item['valor'])
        
        # Calcular médias
        total_meses = len(fluxo_mensal)
        if total_meses > 0:
            media_entradas = sum(m['entradas'] for m in fluxo_mensal.values()) / total_meses
            media_saidas = sum(m['saidas'] for m in fluxo_mensal.values()) / total_meses
        else:
            media_entradas = media_saidas = 0
        
        # Gerar projeção para os próximos 6 meses
        meses_projecao = []
        saldo_projetado = []
        saldo_atual = sum(
            fluxo_mensal[mes]['entradas'] - fluxo_mensal[mes]['saidas'] 
            for mes in fluxo_mensal.keys()
        )
        
        for i in range(6):
            data_projecao = data_fim + timedelta(days=30 * (i + 1))
            mes_nome = data_projecao.strftime('%b/%Y')
            meses_projecao.append(mes_nome)
            
            saldo_atual += (media_entradas - media_saidas)
            saldo_projetado.append(saldo_atual)
        
        # Dados históricos
        meses_historicos = sorted(fluxo_mensal.keys())
        saldo_historico = []
        saldo_acum = 0
        
        for mes in meses_historicos:
            saldo_acum += fluxo_mensal[mes]['entradas'] - fluxo_mensal[mes]['saidas']
            saldo_historico.append(saldo_acum)
        
        return jsonify({
            'meses_historicos': [datetime.strptime(mes, '%Y-%m').strftime('%b/%Y') for mes in meses_historicos],
            'saldo_historico': saldo_historico,
            'meses_projecao': meses_projecao,
            'saldo_projetado': saldo_projetado,
            'media_entradas': media_entradas,
            'media_saidas': media_saidas
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@fluxo_de_caixa_bp.route('/api/tabela-dados')
@login_required
def api_tabela_dados():
    """API para dados da tabela completa"""
    user = session.get('user', {})
    user_role = user.get('role', '')
    
    if user_role not in ['admin', 'interno_unique']:
        return jsonify({'error': 'Acesso negado'}), 403
    
    try:
        periodo = request.args.get('periodo', 'ano_atual')
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))
        
        data_inicio, data_fim = _get_periodo_dates(periodo)
        table_name = _get_financial_table()
        
        # Query para dados paginados
        query = supabase_admin.table(table_name).select('*')
        if data_inicio and data_fim:
            query = query.gte('data', data_inicio).lte('data', data_fim)
        
        # Aplicar ordenação e paginação
        offset = (page - 1) * limit
        query = query.order('data', desc=True).range(offset, offset + limit - 1)
        
        response = query.execute()
        dados = response.data
        
        # Contar total de registros
        count_query = supabase_admin.table(table_name).select('*', count='exact')
        if data_inicio and data_fim:
            count_query = count_query.gte('data', data_inicio).lte('data', data_fim)
        
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
        return jsonify({'error': str(e)}), 500

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
    # Por enquanto, sempre usar fin_base_resultado que sabemos que existe
    return 'fin_base_resultado'
def _get_periodo_dates(periodo):
    """Retorna datas de início e fim baseado no período selecionado"""
    hoje = datetime.now()
    
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
    elif periodo == 'ultimo_ano':
        inicio = hoje.replace(year=hoje.year - 1, month=1, day=1)
        fim = hoje.replace(year=hoje.year - 1, month=12, day=31)
    else:
        # Período personalizado ou ano atual como padrão
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
    else:
        # Mesmo período do ano anterior
        inicio = hoje.replace(year=hoje.year - 1, month=1, day=1)
        fim = hoje.replace(year=hoje.year - 1, month=12, day=31)
    
    return inicio.strftime('%Y-%m-%d'), fim.strftime('%Y-%m-%d')

def _calcular_variacao_percentual(valor_atual, valor_anterior):
    """Calcula variação percentual entre dois valores"""
    if valor_anterior == 0:
        return 0 if valor_atual == 0 else 100
    
    return ((valor_atual - valor_anterior) / abs(valor_anterior)) * 100

def _calcular_burn_rate(dados):
    """Calcula o burn rate (média dos resultados negativos ou despesas líquidas)"""
    if not dados:
        return 0
    
    # Agrupar por mês
    fluxo_mensal = defaultdict(lambda: {'entradas': 0, 'saidas': 0})
    
    for item in dados:
        try:
            data_item = datetime.strptime(item['data'], '%Y-%m-%d')
            mes_key = data_item.strftime('%Y-%m')
            
            valor = float(item.get('valor', 0))
            
            if item['tipo'] == 'Receita':
                fluxo_mensal[mes_key]['entradas'] += valor
            else:
                fluxo_mensal[mes_key]['saidas'] += valor
        except (ValueError, KeyError):
            continue
    
    if not fluxo_mensal:
        return 0
    
    # Calcular resultado médio mensal (saídas - entradas para burn rate)
    total_saidas = sum(mes_data['saidas'] for mes_data in fluxo_mensal.values())
    total_entradas = sum(mes_data['entradas'] for mes_data in fluxo_mensal.values())
    num_meses = len(fluxo_mensal)
    
    if num_meses == 0:
        return 0
    
    # Burn rate = média de saídas líquidas por mês
    burn_rate_mensal = (total_saidas - total_entradas) / num_meses
    
    # Retornar apenas se for positivo (queima de dinheiro)
    return max(0, burn_rate_mensal)

def _calcular_runway(saldo_atual, burn_rate):
    """Calcula o runway em meses"""
    if burn_rate <= 0 or saldo_atual <= 0:
        return 0  # Não há runway se não há burn rate ou saldo positivo
    
    runway_meses = saldo_atual / burn_rate
    
    # Limitar a um valor máximo razoável (5 anos = 60 meses)
    if runway_meses > 60:
        return 60
    
    return runway_meses