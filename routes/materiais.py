from flask import Blueprint, render_template, session, request, jsonify, redirect, url_for
from extensions import supabase
from routes.auth import login_required, role_required
from permissions import check_permission
from config import Config
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
import json
import numpy as np
from collections import defaultdict
import unicodedata
import re

bp = Blueprint('materiais', __name__)

def format_value_smart(value, currency=False):
    """Format values with K, M, B abbreviations for better readability"""
    if not value or value == 0:
        return "R$ 0" if currency else "0"
    
    num = float(value)
    if num == 0:
        return "R$ 0" if currency else "0"
    
    # Determine suffix and divide accordingly
    if abs(num) >= 1_000_000_000:  # Bilhões
        formatted = num / 1_000_000_000
        suffix = "B"
    elif abs(num) >= 1_000_000:  # Milhões
        formatted = num / 1_000_000
        suffix = "M"
    elif abs(num) >= 1_000:  # Milhares
        formatted = num / 1_000
        suffix = "K"
    else:
        formatted = num
        suffix = ""
    
    # Format to 1 decimal place, remove .0 if not needed
    if suffix:
        if formatted == int(formatted):
            value_str = f"{int(formatted)}{suffix}"
        else:
            value_str = f"{formatted:.1f}{suffix}"
    else:
        value_str = f"{int(formatted)}" if formatted == int(formatted) else f"{formatted:.1f}"
    
    return f"R$ {value_str}" if currency else value_str

def normalize_material_name(text):
    """Normaliza o nome do material removendo acentos, caracteres especiais e fazendo trim"""
    if not text:
        return 'Não informado'
    
    # Remover acentos
    text = unicodedata.normalize('NFD', text)
    text = ''.join(char for char in text if unicodedata.category(char) != 'Mn')
    
    # Remover caracteres especiais, manter apenas letras, números e espaços
    text = re.sub(r'[^a-zA-Z0-9\s]', '', text)
    
    # Fazer trim e remover espaços duplos
    text = ' '.join(text.split())
    
    # Capitalizar primeira letra de cada palavra
    text = text.title()
    
    return text if text else 'Não informado'

@bp.route('/')
@login_required
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def index():
    """Página principal da dashboard de materiais"""
    # Debug da sessão
    print(f"[DEBUG MATERIAIS] Usuário: {session.get('user')}")
    print(f"[DEBUG MATERIAIS] Empresa: {session.get('empresa')}")
    print(f"[DEBUG MATERIAIS] Role: {session.get('user', {}).get('role')}")
    
    # Remover verificação de empresa que pode estar causando o redirect
    # user_empresa = session.get('empresa')
    # if not user_empresa:
    #     return redirect(url_for('auth.login'))
    
    return render_template('materiais/index.html')

@bp.route('/api/kpis')
@login_required
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def get_kpis():
    """API para obter KPIs gerais de materiais"""
    try:
        # Debug da sessão
        print(f"[DEBUG MATERIAIS API] Usuário: {session.get('user')}")
        print(f"[DEBUG MATERIAIS API] Role: {session.get('user', {}).get('role')}")
        
        # Filtros da query
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        modalidade = request.args.get('modalidade')
        situacao = request.args.get('situacao')
        
        # Buscar dados básicos diretamente do Supabase com filtros
        query_builder = supabase.table('importacoes_processos').select(
            'id, total_vmle_real, total_vmcv_real, cliente_cpfcnpj, situacao, di_modalidade_despacho, data_abertura'
        ).not_.is_('total_vmcv_real', 'null')
        
        # Aplicar filtros
        if data_inicio:
            query_builder = query_builder.gte('data_abertura', data_inicio)
        
        if data_fim:
            query_builder = query_builder.lte('data_abertura', data_fim)
            
        if modalidade and modalidade != 'todas':
            query_builder = query_builder.eq('di_modalidade_despacho', modalidade)
            
        if situacao and situacao != 'todas':
            query_builder = query_builder.eq('situacao', situacao)
        
        result = query_builder.execute()
        
        if not result.data:
            return jsonify({'success': False, 'error': 'Nenhum dado encontrado'})
        
        data = result.data
        
        # Calcular KPIs manualmente
        total_processos = len(data)
        total_vmle = sum(float(item.get('total_vmle_real', 0) or 0) for item in data)
        total_vmcv = sum(float(item.get('total_vmcv_real', 0) or 0) for item in data)
        total_despesas = total_vmcv * 0.4  # 40% do VMCV
        total_com_despesas = total_vmcv + total_despesas
        total_clientes = len(set(item.get('cliente_cpfcnpj') for item in data if item.get('cliente_cpfcnpj')))
        valor_medio = total_vmle / total_processos if total_processos > 0 else 0
        valor_medio_com_despesas = total_com_despesas / total_processos if total_processos > 0 else 0
        
        # Calcular processos em andamento
        processos_andamento = len([item for item in data if item.get('situacao') in ['Em andamento', 'Aguardando']])
        
        # Debug dos cálculos
        print(f"[DEBUG KPIs] Total Processos: {total_processos}")
        print(f"[DEBUG KPIs] Valor Comercial (VMCV): {total_vmcv}")
        print(f"[DEBUG KPIs] Despesas Calculadas (40%): {total_despesas}")
        print(f"[DEBUG KPIs] Valor Total com Despesas: {total_com_despesas}")
        
        # Preparar resposta
        kpis = {
            'total_processos': {
                'value': total_processos,
                'formatted': format_value_smart(total_processos),
                'label': 'Total de Processos'
            },
            'valor_total': {
                'value': total_vmle,
                'formatted': format_value_smart(total_vmle, currency=True),
                'label': 'Valor Total Mercadorias'
            },
            'valor_comercial': {
                'value': total_vmcv,
                'formatted': format_value_smart(total_vmcv, currency=True),
                'label': 'Valor Comercial (VMCV)'
            },
            'total_despesas': {
                'value': total_despesas,
                'formatted': format_value_smart(total_despesas, currency=True),
                'label': 'Despesas Totais (40% VMCV)'
            },
            'valor_total_com_despesas': {
                'value': total_com_despesas,
                'formatted': format_value_smart(total_com_despesas, currency=True),
                'label': 'VMCV + Despesas'
            },
            'total_clientes': {
                'value': total_clientes,
                'formatted': format_value_smart(total_clientes),
                'label': 'Clientes Únicos'
            },
            'valor_medio': {
                'value': valor_medio,
                'formatted': format_value_smart(valor_medio, currency=True),
                'label': 'Valor Médio por Processo'
            },
            'valor_medio_com_despesas': {
                'value': valor_medio_com_despesas,
                'formatted': format_value_smart(valor_medio_com_despesas, currency=True),
                'label': 'Valor Médio + Despesas'
            },
            'processos_andamento': {
                'value': processos_andamento,
                'formatted': format_value_smart(processos_andamento),
                'label': 'Processos em Andamento'
            }
        }
        
        return jsonify({'success': True, 'data': kpis})
        
    except Exception as e:
        print(f"[ERROR KPIs] {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/top-materiais')
@login_required
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def get_top_materiais():
    """Top 10 materiais por valor"""
    try:
        # Obter filtros da requisição
        material_filter = request.args.get('material', '')
        date_start = request.args.get('date_start', '')
        date_end = request.args.get('date_end', '')
        cliente_filter = request.args.get('cliente', '')
        modal_filter = request.args.get('modal', '')
        
        # Construir query base
        query = supabase.table('importacoes_processos').select(
            'id, total_vmcv_real, data_embarque, data_chegada, resumo_mercadoria, cliente_razaosocial'
        )
        
        # Aplicar filtros do usuário
        if material_filter:
            query = query.ilike('resumo_mercadoria', f'%{material_filter}%')
        
        if date_start:
            query = query.gte('data_abertura', date_start)
        
        if date_end:
            query = query.lte('data_abertura', date_end)
            
        if cliente_filter:
            query = query.ilike('cliente_razaosocial', f'%{cliente_filter}%')
            
        if modal_filter:
            query = query.ilike('via_transporte_descricao', f'%{modal_filter}%')
        
        # Executar query principal
        processos_result = query.limit(1000).execute()
        processos = processos_result.data or []
        
        # Agrupar por material
        materiais = defaultdict(float)
        for p in processos:
            material = normalize_material_name(p.get('resumo_mercadoria'))
            valor = float(p.get('total_vmcv_real') or 0)
            materiais[material] += valor
        
        # Ordenar e pegar top 10
        top_materiais = sorted(materiais.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return jsonify({
            'status': 'success',
            'data': {
                'labels': [item[0] for item in top_materiais],
                'values': [item[1] for item in top_materiais]
            }
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@bp.route('/api/evolucao-mensal')
@login_required
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def get_evolucao_mensal():
    """Evolução mensal por material"""
    try:
        material_filter = request.args.get('material', '')
        
        # Construir query base
        query = supabase.table('importacoes_processos').select(
            'data_abertura, total_vmcv_real, resumo_mercadoria'
        )
        
        if material_filter:
            query = query.ilike('resumo_mercadoria', f'%{material_filter}%')
        
        result = query.limit(1000).execute()
        processos = result.data or []
        
        # Agrupar por mês
        meses = defaultdict(lambda: {'valor': 0, 'quantidade': 0})
        for p in processos:
            if p.get('data_abertura'):
                try:
                    data = datetime.fromisoformat(p['data_abertura'].replace('Z', '+00:00'))
                    mes_ano = f"{data.year}-{data.month:02d}"
                    valor = float(p.get('total_vmcv_real') or 0)
                    meses[mes_ano]['valor'] += valor
                    meses[mes_ano]['quantidade'] += 1
                except:
                    continue
        
        # Ordenar por data
        meses_ordenados = sorted(meses.items())
        
        return jsonify({
            'status': 'success',
            'data': {
                'labels': [item[0] for item in meses_ordenados],
                'valores': [item[1]['valor'] for item in meses_ordenados],
                'quantidades': [item[1]['quantidade'] for item in meses_ordenados]
            }
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@bp.route('/api/despesas-composicao')
@login_required
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def get_despesas_composicao():
    """Composição das despesas por material"""
    try:
        material_filter = request.args.get('material', '')
        
        # Buscar processos do material
        query = supabase.table('importacoes_processos').select('id')
        
        if material_filter:
            query = query.ilike('resumo_mercadoria', f'%{material_filter}%')
        
        processos_result = query.limit(1000).execute()
        processos = processos_result.data or []
        
        if not processos:
            return jsonify({
                'status': 'success',
                'data': {'labels': [], 'values': []}
            })
        
        # Buscar despesas
        processo_ids = [p['id'] for p in processos]
        despesas_result = supabase.table('importacoes_despesas').select(
            'descricao, valor_real'
        ).in_('processo_id', processo_ids).execute()
        
        despesas = despesas_result.data or []
        
        # Agrupar por descrição
        composicao = defaultdict(float)
        for d in despesas:
            descricao = d.get('descricao') or 'Não informado'
            # Limpar e normalizar descrição das despesas também
            descricao = descricao.strip()
            if not descricao:
                descricao = 'Não informado'
            valor = d.get('valor_real')
            if valor:
                try:
                    composicao[descricao] += float(valor)
                except (ValueError, TypeError):
                    continue
        
        # Ordenar por valor e pegar top 10
        composicao_ordenada = sorted(composicao.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return jsonify({
            'status': 'success',
            'data': {
                'labels': [item[0] for item in composicao_ordenada],
                'values': [item[1] for item in composicao_ordenada]
            }
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@bp.route('/api/canal-parametrizacao')
@login_required
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def get_canal_parametrizacao():
    """Análise de canal por material"""
    try:
        # Construir query base
        query = supabase.table('importacoes_processos').select(
            'resumo_mercadoria, diduimp_canal'
        )
        
        result = query.limit(1000).execute()
        processos = result.data or []
        
        # Agrupar por material e canal
        materiais_canal = defaultdict(lambda: defaultdict(int))
        for p in processos:
            material = normalize_material_name(p.get('resumo_mercadoria'))
            canal = p.get('diduimp_canal') or 'Não informado'
            materiais_canal[material][canal] += 1
        
        # Pegar top 5 materiais por total de processos
        totais_por_material = {mat: sum(canais.values()) for mat, canais in materiais_canal.items()}
        top_materiais = sorted(totais_por_material.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Preparar dados para o gráfico com barras 100%
        labels = [item[0] for item in top_materiais]
        verde = []
        amarelo = []
        vermelho = []
        
        for material in labels:
            canais = materiais_canal[material]
            total = sum(canais.values())
            if total > 0:
                verde_pct = (canais.get('VERDE', 0) / total * 100)
                amarelo_pct = (canais.get('AMARELO', 0) / total * 100)
                vermelho_pct = (canais.get('VERMELHO', 0) / total * 100)
                
                # Garantir que a soma seja exatamente 100%
                total_pct = verde_pct + amarelo_pct + vermelho_pct
                if total_pct > 0:
                    factor = 100 / total_pct
                    verde_pct *= factor
                    amarelo_pct *= factor
                    vermelho_pct *= factor
                
                verde.append(verde_pct)
                amarelo.append(amarelo_pct)
                vermelho.append(vermelho_pct)
            else:
                verde.append(0)
                amarelo.append(0)
                vermelho.append(0)
        
        return jsonify({
            'status': 'success',
            'data': {
                'labels': labels,
                'verde': verde,
                'amarelo': amarelo,
                'vermelho': vermelho,
                'horizontal': True  # Flag para indicar que deve ser horizontal
            }
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@bp.route('/api/clientes-por-material')
@login_required
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def get_clientes_por_material():
    """Principais clientes por material selecionado"""
    try:
        material_filter = request.args.get('material', '')
        
        if not material_filter:
            return jsonify({
                'status': 'success',
                'data': {'labels': [], 'values': []}
            })
        
        # Construir query base
        query = supabase.table('importacoes_processos').select(
            'cliente_razaosocial, total_vmcv_real'
        ).ilike('resumo_mercadoria', f'%{material_filter}%')
        
        result = query.limit(1000).execute()
        processos = result.data or []
        
        # Agrupar por cliente
        clientes = defaultdict(float)
        for p in processos:
            cliente = p.get('cliente_razaosocial') or 'Não informado'
            valor = float(p.get('total_vmcv_real') or 0)
            clientes[cliente] += valor
        
        # Ordenar e pegar top 10
        top_clientes = sorted(clientes.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return jsonify({
            'status': 'success',
            'data': {
                'labels': [item[0] for item in top_clientes],
                'values': [item[1] for item in top_clientes]
            }
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@bp.route('/api/detalhamento')
@login_required
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def get_detalhamento():
    """Tabela de detalhamento dos processos"""
    try:
        material_filter = request.args.get('material', '')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        
        # Construir query base
        query = supabase.table('importacoes_processos').select(
            'id, numero, cliente_razaosocial, data_embarque, previsao_chegada, data_chegada, carga_status, diduimp_canal, total_vmcv_real, resumo_mercadoria'
        )
        
        if material_filter:
            query = query.ilike('resumo_mercadoria', f'%{material_filter}%')
        
        # Aplicar paginação
        offset = (page - 1) * per_page
        result = query.range(offset, offset + per_page - 1).execute()
        processos = result.data or []
        
        # Calcular despesas como 40% do VMCV para cada processo
        for p in processos:
            vmcv = float(p.get('total_vmcv_real') or 0)
            # Calcular despesas como 40% do VMCV
            p['total_despesas'] = vmcv * 0.4
            # Normalizar nome do material
            p['resumo_mercadoria'] = normalize_material_name(p.get('resumo_mercadoria'))
        
        return jsonify({
            'status': 'success',
            'data': processos,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'has_more': len(processos) == per_page
            }
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@bp.route('/api/radar-cliente-material')
@login_required
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def get_radar_cliente_material():
    """Gráfico de radar comparando clientes por materiais"""
    try:
        material_filter = request.args.get('material', '')
        
        if not material_filter:
            return jsonify({
                'status': 'success',
                'data': {'labels': [], 'datasets': []}
            })
        
        # Construir query base
        query = supabase.table('importacoes_processos').select(
            'cliente_razaosocial, total_vmcv_real, resumo_mercadoria'
        ).ilike('resumo_mercadoria', f'%{material_filter}%')
        
        result = query.limit(1000).execute()
        processos = result.data or []
        
        # Agrupar por cliente e material
        cliente_material = defaultdict(lambda: defaultdict(float))
        for p in processos:
            cliente = p.get('cliente_razaosocial') or 'Não informado'
            material = normalize_material_name(p.get('resumo_mercadoria'))
            valor = float(p.get('total_vmcv_real') or 0)
            cliente_material[cliente][material] += valor
        
        # Pegar top 5 clientes
        totais_por_cliente = {cliente: sum(materiais.values()) for cliente, materiais in cliente_material.items()}
        top_clientes = sorted(totais_por_cliente.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Obter todos os materiais únicos
        todos_materiais = set()
        for cliente, _ in top_clientes:
            todos_materiais.update(cliente_material[cliente].keys())
        
        materiais_ordenados = sorted(list(todos_materiais))
        
        # Preparar dados para o radar
        datasets = []
        colors = ['rgba(255, 99, 132, 0.2)', 'rgba(54, 162, 235, 0.2)', 'rgba(255, 205, 86, 0.2)', 
                 'rgba(75, 192, 192, 0.2)', 'rgba(153, 102, 255, 0.2)']
        border_colors = ['rgba(255, 99, 132, 1)', 'rgba(54, 162, 235, 1)', 'rgba(255, 205, 86, 1)', 
                        'rgba(75, 192, 192, 1)', 'rgba(153, 102, 255, 1)']
        
        for i, (cliente, _) in enumerate(top_clientes):
            valores = []
            for material in materiais_ordenados:
                valores.append(cliente_material[cliente].get(material, 0))
            
            datasets.append({
                'label': cliente,
                'data': valores,
                'backgroundColor': colors[i % len(colors)],
                'borderColor': border_colors[i % len(border_colors)],
                'borderWidth': 2
            })
        
        return jsonify({
            'status': 'success',
            'data': {
                'labels': materiais_ordenados,
                'datasets': datasets
            }
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@bp.route('/api/materiais-opcoes')
@login_required
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def get_materiais_opcoes():
    """Buscar todos os materiais únicos para o dropdown"""
    try:
        # Buscar todos os materiais únicos
        query = supabase.table('importacoes_processos').select('resumo_mercadoria').limit(2000)
        result = query.execute()
        processos = result.data or []
        
        # Normalizar e obter materiais únicos
        materiais_set = set()
        for p in processos:
            material = normalize_material_name(p.get('resumo_mercadoria'))
            if material and material != 'Não informado':
                materiais_set.add(material)
        
        # Ordenar alfabeticamente
        materiais_ordenados = sorted(list(materiais_set))
        
        return jsonify({
            'status': 'success',
            'data': materiais_ordenados
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@bp.route('/api/linha-tempo-chegadas')
@login_required
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def get_linha_tempo_chegadas():
    """Widget de linha do tempo com próximas chegadas e despesas"""
    try:
        dias_futuro = int(request.args.get('dias', 30))  # Default 30 dias
        
        # Calcular datas
        hoje = datetime.now().date()
        data_limite = hoje + timedelta(days=dias_futuro)
        
        # Buscar processos com chegadas futuras usando Supabase diretamente
        processos_result = supabase.table('importacoes_processos').select(
            'id, numero, data_chegada, resumo_mercadoria, cliente_razaosocial, local_embarque, via_transporte_descricao, total_vmcv_real'
        ).gte('data_chegada', str(hoje)).lte('data_chegada', str(data_limite)).order('data_chegada').limit(20).execute()
        
        processos = processos_result.data or []
        
        if not processos:
            return jsonify({
                'status': 'success',
                'data': []
            })
        
        # Buscar despesas para cada processo
        processo_ids = [p['id'] for p in processos]
        despesas_result = supabase.table('importacoes_despesas').select(
            'processo_id, valor_real, situacao_descricao'
        ).in_('processo_id', processo_ids).execute()
        
        despesas = despesas_result.data or []
        
        # Agrupar despesas por processo e situação
        despesas_por_processo = defaultdict(lambda: {'aprovadas': 0, 'pendentes': 0, 'total': 0})
        for d in despesas:
            processo_id = d.get('processo_id')
            valor = d.get('valor_real')
            situacao = d.get('situacao_descricao', '').lower()
            
            if processo_id and valor:
                try:
                    valor_float = float(valor)
                    if situacao == 'aprovado':
                        despesas_por_processo[processo_id]['aprovadas'] += valor_float
                    elif situacao == 'pendente':
                        despesas_por_processo[processo_id]['pendentes'] += valor_float
                    
                    if situacao in ['aprovado', 'pendente']:
                        despesas_por_processo[processo_id]['total'] += valor_float
                except (ValueError, TypeError):
                    continue
        
        # Processar os dados para incluir material normalizado e despesas
        for processo in processos:
            processo['resumo_mercadoria'] = normalize_material_name(processo.get('resumo_mercadoria'))
            
            # Adicionar dados de despesas
            despesas_info = despesas_por_processo.get(processo['id'], {'aprovadas': 0, 'pendentes': 0, 'total': 0})
            processo['total_despesas_aprovadas'] = despesas_info['aprovadas']
            processo['total_despesas_pendentes'] = despesas_info['pendentes']
            processo['total_despesas_previsto'] = despesas_info['total']
            
            # Garantir que valores numéricos não sejam None
            processo['total_vmcv_real'] = float(processo.get('total_vmcv_real') or 0)
        
        return jsonify({
            'status': 'success',
            'data': processos
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Funções de debug para testar sem login
def debug_test_detalhamento():
    """Função para testar o endpoint de detalhamento sem login"""
    try:
        print("\n=== DEBUG: Testando endpoint de detalhamento ===")
        
        # Construir query base
        query = supabase.table('importacoes_processos').select(
            'id, numero, nro_pedido, cliente_razaosocial, data_embarque, previsao_chegada, data_chegada, carga_status, diduimp_canal, total_vmcv_real, resumo_mercadoria'
        )
        
        # Aplicar paginação
        result = query.range(0, 4).execute()  # Pegar apenas 5 registros para teste
        processos = result.data or []
        
        print(f"Processos encontrados: {len(processos)}")
        
        if processos:
            print("\nPrimeiro processo (raw data):")
            primeiro = processos[0]
            for key, value in primeiro.items():
                print(f"  {key}: {value}")
            
            # Buscar despesas para cada processo
            processo_ids = [p['id'] for p in processos]
            despesas_result = supabase.table('importacoes_despesas').select(
                'processo_id, valor_real'
            ).in_('processo_id', processo_ids).execute()
            
            despesas = despesas_result.data or []
            print(f"\nDespesas encontradas: {len(despesas)}")
            
            despesas_por_processo = defaultdict(float)
            for d in despesas:
                processo_id = d.get('processo_id')
                valor = d.get('valor_real')
                if processo_id and valor:
                    try:
                        despesas_por_processo[processo_id] += float(valor)
                    except (ValueError, TypeError):
                        continue
            
            # Adicionar total de despesas a cada processo
            for p in processos:
                p['total_despesas'] = despesas_por_processo.get(p['id'], 0)
                # Normalizar nome do material
                p['resumo_mercadoria'] = normalize_material_name(p.get('resumo_mercadoria'))
            
            print("\nPrimeiro processo (após processamento):")
            primeiro_processado = processos[0]
            for key, value in primeiro_processado.items():
                print(f"  {key}: {value}")
            
            return {
                'status': 'success',
                'data': processos[:3],  # Retornar apenas 3 para debug
                'pagination': {
                    'page': 1,
                    'per_page': 50,
                    'has_more': len(processos) == 5
                }
            }
        else:
            print("Nenhum processo encontrado!")
            return {'status': 'error', 'message': 'Nenhum processo encontrado'}
            
    except Exception as e:
        print(f"Erro no debug_test_detalhamento: {str(e)}")
        return {'status': 'error', 'message': str(e)}

def debug_test_linha_tempo():
    """Função para testar o endpoint de linha do tempo sem login"""
    try:
        print("\n=== DEBUG: Testando endpoint de linha do tempo ===")
        dias_futuro = 30
        
        # Primeiro, vamos testar uma query mais simples
        print("1. Testando query simples...")
        simple_query = supabase.table('importacoes_processos').select(
            'id, numero, data_chegada, resumo_mercadoria, cliente_razaosocial'
        ).limit(10).execute()
        
        processos_simples = simple_query.data or []
        print(f"Processos encontrados (query simples): {len(processos_simples)}")
        
        if processos_simples:
            print("Exemplo de data_chegada:")
            for i, p in enumerate(processos_simples[:3]):
                print(f"  Processo {i+1}: data_chegada = {p.get('data_chegada')}")
        
        # Testar query com filtro de data
        print("\n2. Testando com filtro de data...")
        from datetime import datetime, timedelta
        hoje = datetime.now().date()
        futuro = hoje + timedelta(days=30)
        
        print(f"Hoje: {hoje}")
        print(f"Futuro (30 dias): {futuro}")
        
        filtered_query = supabase.table('importacoes_processos').select(
            'id, numero, data_chegada, resumo_mercadoria, cliente_razaosocial'
        ).gte('data_chegada', str(hoje)).lte('data_chegada', str(futuro)).limit(10).execute()
        
        processos_filtrados = filtered_query.data or []
        print(f"Processos com chegadas futuras: {len(processos_filtrados)}")
        
        # Se não há chegadas futuras, vamos testar com passado
        if not processos_filtrados:
            print("\n3. Testando com data passada (últimos 30 dias)...")
            passado = hoje - timedelta(days=30)
            
            past_query = supabase.table('importacoes_processos').select(
                'id, numero, data_chegada, resumo_mercadoria, cliente_razaosocial'
            ).gte('data_chegada', str(passado)).lte('data_chegada', str(hoje)).limit(10).execute()
            
            processos_passados = past_query.data or []
            print(f"Processos com chegadas passadas: {len(processos_passados)}")
            
            if processos_passados:
                print("Exemplo de datas passadas:")
                for i, p in enumerate(processos_passados[:3]):
                    print(f"  Processo {i+1}: data_chegada = {p.get('data_chegada')}")
        
        # Agora vamos testar a query complexa
        print("\n4. Testando query complexa original...")
        
        # Usar query mais simples para debug
        debug_query = f"""
        SELECT
            p.id AS processo_id,
            p.numero,
            p.data_chegada,
            p.resumo_mercadoria,
            p.cliente_razaosocial,
            p.local_embarque,
            p.via_transporte_descricao,
            p.total_vmcv_real
        FROM
            importacoes_processos p
        WHERE
            p.data_chegada IS NOT NULL
        ORDER BY
            p.data_chegada DESC
        LIMIT 5
        """
        
        result = supabase.rpc('execute_sql', {
            'query': debug_query,
            'params': []
        }).execute()
        
        print(f"Resultado da query complexa: {result.data}")
        
        if result.data and result.data[0]['result']:
            processos = result.data[0]['result']
            print(f"Processos encontrados na query complexa: {len(processos)}")
            
            if processos:
                print("Primeiro processo da query complexa:")
                for key, value in processos[0].items():
                    print(f"  {key}: {value}")
            
            return {
                'status': 'success',
                'data': processos
            }
        else:
            return {
                'status': 'success',
                'data': []
            }
            
    except Exception as e:
        print(f"Erro no debug_test_linha_tempo: {str(e)}")
        return {'status': 'error', 'message': str(e)}

def debug_test_materiais_opcoes():
    """Função para testar o endpoint de opções de materiais"""
    try:
        print("\n=== DEBUG: Testando endpoint de materiais opções ===")
        
        # Buscar todos os materiais únicos
        query = supabase.table('importacoes_processos').select('resumo_mercadoria').limit(100)
        result = query.execute()
        processos = result.data or []
        
        print(f"Processos encontrados: {len(processos)}")
        
        if processos:
            print("Primeiros 5 materiais (raw):")
            for i, p in enumerate(processos[:5]):
                print(f"  {i+1}: {p.get('resumo_mercadoria')}")
        
        # Normalizar e obter materiais únicos
        materiais_set = set()
        for p in processos:
            material_raw = p.get('resumo_mercadoria')
            material = normalize_material_name(material_raw)
            print(f"Raw: '{material_raw}' -> Normalizado: '{material}'")
            if material and material != 'Não informado':
                materiais_set.add(material)
        
        # Ordenar alfabeticamente
        materiais_ordenados = sorted(list(materiais_set))
        
        print(f"\nMateriais únicos encontrados: {len(materiais_ordenados)}")
        print("Primeiros 10 materiais normalizados:")
        for i, material in enumerate(materiais_ordenados[:10]):
            print(f"  {i+1}: {material}")
        
        return {
            'status': 'success',
            'data': materiais_ordenados
        }
        
    except Exception as e:
        print(f"Erro no debug_test_materiais_opcoes: {str(e)}")
        return {'status': 'error', 'message': str(e)}

# Função principal para executar todos os testes
def run_all_debug_tests():
    """Executa todos os testes de debug"""
    print("🚀 Iniciando testes de debug...")
    
    print("\n" + "="*50)
    debug_test_materiais_opcoes()
    
    print("\n" + "="*50)
    debug_test_detalhamento()
    
    print("\n" + "="*50)
    debug_test_linha_tempo()
    
    print("\n🎉 Testes de debug concluídos!")

# Endpoint temporário para bypass de autenticação durante debug
@bp.route('/debug-test-endpoints')
def debug_test_endpoints():
    """Endpoint temporário para teste sem autenticação"""
    try:
        # Testar detalhamento
        query = supabase.table('importacoes_processos').select(
            'id, numero, cliente_razaosocial, data_embarque, previsao_chegada, data_chegada, carga_status, diduimp_canal, total_vmcv_real, resumo_mercadoria'
        ).limit(5).execute()
        
        processos = query.data or []
        
        # Testar linha do tempo
        hoje = datetime.now().date()
        futuro = hoje + timedelta(days=30)
        
        linha_tempo_query = supabase.table('importacoes_processos').select(
            'id, numero, data_chegada, resumo_mercadoria, cliente_razaosocial'
        ).gte('data_chegada', str(hoje)).lte('data_chegada', str(futuro)).limit(5).execute()
        
        linha_tempo = linha_tempo_query.data or []
        
        return jsonify({
            'detalhamento': {
                'count': len(processos),
                'sample': processos[:2] if processos else []
            },
            'linha_tempo': {
                'count': len(linha_tempo),
                'sample': linha_tempo[:2] if linha_tempo else []
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/kpis-debug')
def get_kpis_debug():
    """API temporária para testar KPIs sem autenticação"""
    try:
        print("[DEBUG KPIS] Testando cálculo de KPIs...")
        
        # Buscar dados básicos diretamente do Supabase
        query = supabase.table('importacoes_processos').select(
            'id, total_vmle_real, total_vmcv_real, cliente_cpfcnpj'
        ).not_.is_('total_vmcv_real', 'null').execute()
        
        if not query.data:
            return jsonify({'success': False, 'error': 'Nenhum dado encontrado'})
        
        data = query.data
        
        # Calcular KPIs manualmente
        total_processos = len(data)
        total_vmle = sum(float(item.get('total_vmle_real', 0) or 0) for item in data)
        total_vmcv = sum(float(item.get('total_vmcv_real', 0) or 0) for item in data)
        total_despesas = total_vmcv * 0.4  # 40% do VMCV
        total_com_despesas = total_vmcv + total_despesas
        total_clientes = len(set(item.get('cliente_cpfcnpj') for item in data if item.get('cliente_cpfcnpj')))
        valor_medio = total_vmle / total_processos if total_processos > 0 else 0
        valor_medio_com_despesas = total_com_despesas / total_processos if total_processos > 0 else 0
        
        # Debug dos cálculos
        print(f"[DEBUG KPIs] Total Processos: {total_processos}")
        print(f"[DEBUG KPIs] Valor Comercial (VMCV): {total_vmcv}")
        print(f"[DEBUG KPIs] Despesas Calculadas (40%): {total_despesas}")
        print(f"[DEBUG KPIs] Valor Total com Despesas: {total_com_despesas}")
        
        # Preparar resposta
        kpis = {
            'total_processos': {
                'value': total_processos,
                'formatted': format_value_smart(total_processos),
                'label': 'Total de Processos'
            },
            'valor_total': {
                'value': total_vmle,
                'formatted': format_value_smart(total_vmle, currency=True),
                'label': 'Valor Total Mercadorias'
            },
            'valor_comercial': {
                'value': total_vmcv,
                'formatted': format_value_smart(total_vmcv, currency=True),
                'label': 'Valor Comercial (VMCV)'
            },
            'total_despesas': {
                'value': total_despesas,
                'formatted': format_value_smart(total_despesas, currency=True),
                'label': 'Despesas Totais (40% VMCV)'
            },
            'valor_total_com_despesas': {
                'value': total_com_despesas,
                'formatted': format_value_smart(total_com_despesas, currency=True),
                'label': 'VMCV + Despesas'
            },
            'total_clientes': {
                'value': total_clientes,
                'formatted': format_value_smart(total_clientes),
                'label': 'Clientes Únicos'
            },
            'valor_medio': {
                'value': valor_medio,
                'formatted': format_value_smart(valor_medio, currency=True),
                'label': 'Valor Médio por Processo'
            },
            'valor_medio_com_despesas': {
                'value': valor_medio_com_despesas,
                'formatted': format_value_smart(valor_medio_com_despesas, currency=True),
                'label': 'Valor Médio + Despesas'
            }
        }
        
        return jsonify({'success': True, 'data': kpis})
        
    except Exception as e:
        print(f"[ERROR KPIs] {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
