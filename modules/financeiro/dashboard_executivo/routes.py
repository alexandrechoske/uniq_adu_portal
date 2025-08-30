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
@perfil_required('financeiro', 'fin_dashboard_executivo')
def api_saldo_acumulado():
    """API para evolução do saldo acumulado"""
    try:
        ano = request.args.get('ano', datetime.now().year)
        
        # Buscar dados de saldo acumulado mensal
        response_saldo = supabase_admin.table('vw_fluxo_caixa') \
            .select('data, saldo_acumulado') \
            .gte('data', f'{ano}-01-01') \
            .lte('data', f'{ano}-12-31') \
            .neq('classe', 'TRANSFERENCIA DE CONTAS') \
            .order('data') \
            .execute()
        
        # Processar dados mensais
        dados_mensais = defaultdict(list)
        
        for item in response_saldo.data:
            data = datetime.strptime(item['data'], '%Y-%m-%d')
            mes = data.strftime('%Y-%m')
            saldo = float(item['saldo_acumulado'])
            
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
        
        # Calcular totais por setor
        total_importacao = 0
        total_consultoria = 0
        total_exportacao = 0
        
        for item in response_faturamento.data:
            classe = item.get('classe', '').upper()
            valor = float(item['valor'])
            
            if 'IMP' in classe or 'IMPORT' in classe:
                total_importacao += valor
            elif 'CONS' in classe or 'CONSULT' in classe:
                total_consultoria += valor
            elif 'EXP' in classe or 'EXPORT' in classe:
                total_exportacao += valor
        
        return jsonify({
            'success': True,
            'data': {
                'importacao': {
                    'valor': total_importacao,
                    'percentual': (total_importacao / (total_importacao + total_consultoria + total_exportacao) * 100) if (total_importacao + total_consultoria + total_exportacao) > 0 else 0
                },
                'consultoria': {
                    'valor': total_consultoria,
                    'percentual': (total_consultoria / (total_importacao + total_consultoria + total_exportacao) * 100) if (total_importacao + total_consultoria + total_exportacao) > 0 else 0
                },
                'exportacao': {
                    'valor': total_exportacao,
                    'percentual': (total_exportacao / (total_importacao + total_consultoria + total_exportacao) * 100) if (total_importacao + total_consultoria + total_exportacao) > 0 else 0
                }
            }
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
@perfil_required('financeiro', 'fin_dashboard_executivo')
def api_top_clientes():
    """API para top 5 clientes por faturamento"""
    try:
        ano = request.args.get('ano', datetime.now().year)
        
        # Buscar dados de faturamento por cliente
        response_faturamento = supabase_admin.table('fin_faturamento_anual') \
            .select('cliente, valor') \
            .gte('data', f'{ano}-01-01') \
            .lte('data', f'{ano}-12-31') \
            .execute()
        
        # Agrupar por cliente
        faturamento_por_cliente = defaultdict(float)
        
        for item in response_faturamento.data:
            cliente = item.get('cliente', 'Não identificado')
            valor = float(item['valor'])
            
            faturamento_por_cliente[cliente] += valor
        
        # Ordenar e pegar top 5
        top_clientes = sorted(faturamento_por_cliente.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Formatar resultado
        resultado = []
        total_geral = sum(valor for _, valor in top_clientes)
        
        for i, (cliente, total) in enumerate(top_clientes):
            resultado.append({
                'cliente': cliente,
                'total_faturado': total,
                'percentual': (total / total_geral * 100) if total_geral > 0 else 0,
                'rank': i + 1
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