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
@perfil_required('financeiro', 'fin_dashboard_executivo')
def index():
    """Dashboard Executivo Financeiro - Visão estratégica das finanças"""
    return render_template('dashboard_executivo_financeiro.html')

@dashboard_executivo_financeiro_bp.route('/api/kpis')
@login_required
@perfil_required('financeiro', 'fin_dashboard_executivo')
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

@dashboard_executivo_financeiro_bp.route('/api/meta-atingimento')
@login_required
@perfil_required('financeiro', 'fin_dashboard_executivo')
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
@perfil_required('financeiro', 'fin_dashboard_executivo')
def api_resultado_mensal():
    """API para resultado mensal"""
    try:
        ano = request.args.get('ano', datetime.now().year)
        
        # Buscar dados de fluxo de caixa mensal
        response_fluxo = supabase_admin.table('vw_fluxo_caixa') \
            .select('data, valor_fluxo, tipo_movto') \
            .gte('data', f'{ano}-01-01') \
            .lte('data', f'{ano}-12-31') \
            .neq('classe', 'TRANSFERENCIA DE CONTAS') \
            .execute()
        
        # Processar dados mensais
        dados_mensais = defaultdict(lambda: {'receitas': 0, 'despesas': 0})
        
        for item in response_fluxo.data:
            data = datetime.strptime(item['data'], '%Y-%m-%d')
            mes = data.strftime('%Y-%m')
            valor = float(item['valor_fluxo'])
            
            if item['tipo_movto'] == 'Receita':
                dados_mensais[mes]['receitas'] += valor
            else:
                dados_mensais[mes]['despesas'] += valor
        
        # Calcular resultados mensais
        resultados = []
        resultado_acumulado = 0
        
        for mes_num in range(1, 13):
            mes_key = f"{ano}-{mes_num:02d}"
            dados_mes = dados_mensais[mes_key]
            resultado_mensal = dados_mes['receitas'] - dados_mes['despesas']
            resultado_acumulado += resultado_mensal
            
            resultados.append({
                'mes': mes_key,
                'receitas': dados_mes['receitas'],
                'despesas': dados_mes['despesas'],
                'resultado_mensal': resultado_mensal,
                'resultado_acumulado': resultado_acumulado
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

@dashboard_executivo_financeiro_bp.route('/api/faturamento-setor')
@login_required
@perfil_required('financeiro', 'fin_dashboard_executivo')
def api_faturamento_setor():
    """API para faturamento por setor"""
    try:
        ano = request.args.get('ano', datetime.now().year)
        
        # Buscar dados de faturamento
        response_faturamento = supabase_admin.table('fin_faturamento_anual') \
            .select('classe, valor') \
            .gte('data', f'{ano}-01-01') \
            .lte('data', f'{ano}-12-31') \
            .execute()
        
        # Agrupar por setor
        setores = {
            'importacao': 0,
            'consultoria': 0,
            'exportacao': 0,
            'outros': 0
        }
        
        for item in response_faturamento.data:
            classe = item['classe'].upper() if item['classe'] else ''
            valor = float(item['valor'])
            
            if 'IMP' in classe or 'IMPORT' in classe:
                setores['importacao'] += valor
            elif 'CONS' in classe or 'CONSULT' in classe:
                setores['consultoria'] += valor
            elif 'EXP' in classe or 'EXPORT' in classe:
                setores['exportacao'] += valor
            else:
                setores['outros'] += valor
        
        total = sum(setores.values())
        
        # Calcular percentuais
        for setor in setores:
            setores[setor] = {
                'valor': setores[setor],
                'percentual': round((setores[setor] / total * 100) if total > 0 else 0, 2)
            }
        
        return jsonify({
            'success': True,
            'data': setores
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@dashboard_executivo_financeiro_bp.route('/api/top-despesas')
@login_required
@perfil_required('financeiro', 'fin_dashboard_executivo')
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
        
        # Agrupar por categoria e somar valores
        categorias = defaultdict(float)
        
        for item in response_despesas.data:
            categoria = item['categoria'] if item['categoria'] else 'Não categorizado'
            valor = float(item['valor'])
            categorias[categoria] += valor
        
        # Ordenar e pegar top 5
        top_categorias = sorted(categorias.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Calcular total para percentuais
        total = sum(categorias.values())
        
        # Formatar resultado
        resultado = []
        for categoria, valor in top_categorias:
            resultado.append({
                'categoria': categoria,
                'valor': valor,
                'percentual': round((valor / total * 100) if total > 0 else 0, 2)
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
@perfil_required('financeiro', 'fin_dashboard_executivo')
def api_top_clientes():
    """API para top 5 clientes por faturamento"""
    try:
        ano = request.args.get('ano', datetime.now().year)
        
        # Buscar dados de faturamento
        response_faturamento = supabase_admin.table('fin_faturamento_anual') \
            .select('cliente, valor') \
            .gte('data', f'{ano}-01-01') \
            .lte('data', f'{ano}-12-31') \
            .execute()
        
        # Agrupar por cliente e somar valores
        clientes = defaultdict(float)
        
        for item in response_faturamento.data:
            cliente = item['cliente'] if item['cliente'] else 'Não identificado'
            valor = float(item['valor'])
            clientes[cliente] += valor
        
        # Ordenar e pegar top 5
        top_clientes = sorted(clientes.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Calcular total para percentuais
        total = sum(clientes.values())
        
        # Formatar resultado
        resultado = []
        for cliente, valor in top_clientes:
            resultado.append({
                'cliente': cliente,
                'total_faturado': valor,
                'percentual': round((valor / total * 100) if total > 0 else 0, 2)
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