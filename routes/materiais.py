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

def get_user_companies():
    """Get companies that the user has access to - cached from session"""
    try:
        # Verificar se a sessão e usuário existem
        if 'user' not in session or not session['user']:
            return []
            
        # Usar dados da sessão em vez de consultar o banco novamente
        if session['user']['role'] == 'cliente_unique':
            return session['user'].get('user_companies', [])
        return []
    except Exception as e:
        print(f"[ERROR get_user_companies] {str(e)}")
        return []

def apply_company_filter(query):
    """Apply company filter to query based on user role"""
    try:
        # Verificar se a sessão existe
        if 'user' not in session or not session['user']:
            print("[DEBUG apply_company_filter] Nenhum usuário na sessão")
            return query
            
        # Obter empresas do usuário
        user_companies = get_user_companies()
        selected_company = request.args.get('empresa')
        
        # Aplicar filtros baseados no papel do usuário e empresa selecionada
        if session['user']['role'] == 'cliente_unique':
            if not user_companies:
                # Se o cliente não tem empresas, retornar query que não encontra nada
                print("[DEBUG apply_company_filter] Cliente sem empresas, filtrando tudo")
                return query.eq('cnpj_importador', '___NENHUMA___')
            
            if selected_company and selected_company in user_companies:
                # Filtrar por empresa específica selecionada
                print(f"[DEBUG apply_company_filter] Filtrando por empresa específica: {selected_company}")
                query = query.eq('cnpj_importador', selected_company)
            else:
                # Filtrar por todas as empresas do usuário
                print(f"[DEBUG apply_company_filter] Filtrando por empresas do usuário: {user_companies}")
                query = query.in_('cnpj_importador', user_companies)
        elif selected_company:
            # Para admin/interno, aplicar filtro da empresa selecionada se houver
            print(f"[DEBUG apply_company_filter] Admin/interno filtrando por empresa: {selected_company}")
            query = query.eq('cnpj_importador', selected_company)
        else:
            print("[DEBUG apply_company_filter] Admin/interno sem filtro específico")
        
        return query
    except Exception as e:
        print(f"[ERROR apply_company_filter] {str(e)}")
        # Em caso de erro, retornar a query original
        return query

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
    """Normaliza o nome do material preservando o conteúdo original quando possível"""
    if not text or (isinstance(text, str) and not text.strip()):
        return 'Não informado'
    
    # Converter para string e fazer trim básico
    text = str(text).strip()
    
    # Se ainda está vazio após trim, retornar padrão
    if not text:
        return 'Não informado'
    
    # Apenas capitalizar corretamente, mantendo caracteres especiais e acentos
    # Isso preserva "MANUTENÇÃO" como "Manutenção"
    text = text.title()
    
    return text

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
        material_filter = request.args.get('material', '')
        date_start = request.args.get('date_start', '')
        date_end = request.args.get('date_end', '')
        cliente_filter = request.args.get('cliente', '')
        modal_filter = request.args.get('modal', '')
        
        # Buscar dados básicos diretamente do Supabase com filtros
        query_builder = supabase.table('importacoes_processos_aberta').select(
            'id, valor_fob_real, valor_cif_real, mercadoria, cnpj_importador, importador, status_processo, modal, data_abertura'
        )
        
        # Aplicar filtro de empresa baseado no usuário
        query_builder = apply_company_filter(query_builder)
        
        # Aplicar filtros adicionais da requisição
        if material_filter:
            query_builder = query_builder.ilike('mercadoria', f'%{material_filter}%')
        
        if date_start:
            query_builder = query_builder.gte('data_abertura', date_start)
        
        if date_end:
            query_builder = query_builder.lte('data_abertura', date_end)
            
        if cliente_filter:
            query_builder = query_builder.eq('cnpj_importador', cliente_filter)
        
        if modal_filter:
            query_builder = query_builder.eq('modal', modal_filter)
        
        result = query_builder.limit(2000).execute()
        
        if not result.data:
            return jsonify({'success': False, 'error': 'Nenhum dado encontrado'})
        
        data = result.data
        
        # Calcular KPIs manualmente
        total_processos = len(data)
        total_vmle = sum(float(item.get('valor_fob_real', 0) or 0) for item in data)
        total_vmcv = sum(float(item.get('valor_cif_real', 0) or 0) for item in data)
        total_despesas = total_vmcv * 0.4  # 40% do VMCV
        total_com_despesas = total_vmcv + total_despesas
        total_clientes = len(set(item.get('cnpj_importador') for item in data if item.get('cnpj_importador')))
        valor_medio = total_vmle / total_processos if total_processos > 0 else 0
        valor_medio_com_despesas = total_com_despesas / total_processos if total_processos > 0 else 0
        
        # Calcular processos em andamento
        processos_andamento = len([item for item in data if item.get('status_processo') in ['Em andamento', 'Aguardando']])
        
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
        query = supabase.table('importacoes_processos_aberta').select(
            'id, valor_cif_real, data_embarque, data_chegada, mercadoria, importador, cnpj_importador'
        )
        
        # Aplicar filtro de empresa baseado no usuário
        query = apply_company_filter(query)
        
        # Aplicar filtros do usuário
        if material_filter:
            query = query.ilike('mercadoria', f'%{material_filter}%')
        
        if date_start:
            query = query.gte('data_abertura', date_start)
        
        if date_end:
            query = query.lte('data_abertura', date_end)
            
        if cliente_filter:
            query = query.eq('cnpj_importador', cliente_filter)
        
        if modal_filter:
            query = query.eq('modal', modal_filter)
        
        # Executar query principal
        processos_result = query.limit(2000).execute()
        processos = processos_result.data or []
        
        # Agrupar por material
        materiais = defaultdict(lambda: {'valor': 0, 'quantidade': 0})
        for p in processos:
            material = normalize_material_name(p.get('mercadoria'))
            # Calcular despesa (40% do valor total)
            valor_total = float(p.get('valor_cif_real') or 0)
            despesa = valor_total * 0.4
            materiais[material]['valor'] += despesa
            materiais[material]['quantidade'] += 1
        
        # Ordenar por valor e pegar top 10
        top_materiais = sorted(materiais.items(), key=lambda x: x[1]['valor'], reverse=False)[:10]
        
        return jsonify({
            'status': 'success',
            'data': {
                'labels': [item[0] for item in top_materiais],
                'values': [item[1]['valor'] for item in top_materiais],
                'quantities': [item[1]['quantidade'] for item in top_materiais]
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
        query = supabase.table('importacoes_processos_aberta').select(
            'data_abertura, valor_cif_real, mercadoria, cliente_cpfcnpj'
        )
        
        # Aplicar filtro de empresa baseado no usuário
        query = apply_company_filter(query)
        
        if material_filter:
            query = query.ilike('mercadoria', f'%{material_filter}%')
        
        result = query.limit(2000).execute()
        processos = result.data or []
        
        # Agrupar por mês
        meses = defaultdict(lambda: {'valor': 0, 'quantidade': 0})
        for p in processos:
            if p.get('data_abertura'):
                try:
                    data = datetime.fromisoformat(p['data_abertura'].replace('Z', '+00:00'))
                    mes_ano = f"{data.year}-{data.month:02d}"
                    # Calcular despesa (40% do valor total)
                    valor_total = float(p.get('valor_cif_real') or 0)
                    despesa = valor_total * 0.4
                    meses[mes_ano]['valor'] += despesa
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
        query = supabase.table('importacoes_processos_aberta').select('id, cliente_cpfcnpj')
        
        # Aplicar filtro de empresa baseado no usuário
        query = apply_company_filter(query)
        
        if material_filter:
            query = query.ilike('mercadoria', f'%{material_filter}%')
        
        processos_result = query.limit(2000).execute()
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
        # Obter filtros da requisição
        material_filter = request.args.get('material', '')
        date_start = request.args.get('date_start', '')
        date_end = request.args.get('date_end', '')
        cliente_filter = request.args.get('cliente', '')
        modal_filter = request.args.get('modal', '')
        
        # Construir query base
        query = supabase.table('importacoes_processos_aberta').select(
            'mercadoria, canal, cnpj_importador, importador, data_abertura, via_transporte_descricao'
        )
        
        # Aplicar filtro de empresa baseado no usuário
        query = apply_company_filter(query)
        
        # Aplicar filtros do usuário
        if material_filter:
            query = query.ilike('mercadoria', f'%{material_filter}%')
        
        if date_start:
            query = query.gte('data_abertura', date_start)
        
        if date_end:
            query = query.lte('data_abertura', date_end)
            
        if cliente_filter:
            query = query.eq('cnpj_importador', cliente_filter)
        
        if modal_filter:
            query = query.eq('modal', modal_filter)
        
        result = query.limit(2000).execute()
        processos = result.data or []
        
        # Agrupar por material e canal
        materiais_canal = defaultdict(lambda: defaultdict(int))
        for p in processos:
            material = normalize_material_name(p.get('mercadoria'))
            canal = p.get('canal') or 'Não informado'
            materiais_canal[material][canal] += 1
        
        # Pegar top 5 materiais por total de processos
        totais_por_material = {mat: sum(canais.values()) for mat, canais in materiais_canal.items()}
        top_materiais = sorted(totais_por_material.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Preparar dados para o gráfico com barras 100%
        labels = [item[0] for item in top_materiais]
        verde = []
        amarelo = []
        vermelho = []
        verde_qtd = []
        amarelo_qtd = []
        vermelho_qtd = []
        
        for material in labels:
            canais = materiais_canal[material]
            total = sum(canais.values())
            if total > 0:
                verde_count = canais.get('VERDE', 0)
                amarelo_count = canais.get('AMARELO', 0)
                vermelho_count = canais.get('VERMELHO', 0)
                
                verde_pct = (verde_count / total * 100)
                amarelo_pct = (amarelo_count / total * 100)
                vermelho_pct = (vermelho_count / total * 100)
                
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
                verde_qtd.append(verde_count)
                amarelo_qtd.append(amarelo_count)
                vermelho_qtd.append(vermelho_count)
            else:
                verde.append(0)
                amarelo.append(0)
                vermelho.append(0)
                verde_qtd.append(0)
                amarelo_qtd.append(0)
                vermelho_qtd.append(0)
        
        return jsonify({
            'status': 'success',
            'data': {
                'labels': labels,
                'verde': verde,
                'amarelo': amarelo,
                'vermelho': vermelho,
                'verde_qtd': verde_qtd,
                'amarelo_qtd': amarelo_qtd,
                'vermelho_qtd': vermelho_qtd,
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
        query = supabase.table('importacoes_processos_aberta').select(
            'cliente_razaosocial, valor_cif_real, cliente_cpfcnpj'
        ).ilike('mercadoria', f'%{material_filter}%')
        
        # Aplicar filtro de empresa baseado no usuário
        query = apply_company_filter(query)
        
        result = query.limit(2000).execute()
        processos = result.data or []
        
        # Agrupar por cliente
        clientes = defaultdict(float)
        for p in processos:
            cliente = p.get('importador') or 'Não informado'
            valor = float(p.get('valor_cif_real') or 0)
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
        
        # Construir query base - incluindo campo referencias
        query = supabase.table('importacoes_processos_aberta').select(
            'id, numero_di, importador, data_embarque, data_chegada, data_chegada, status_processo, canal, valor_cif_real, mercadoria, cnpj_importador'
        )
        
        # Aplicar filtro de empresa baseado no usuário
        query = apply_company_filter(query)
        
        if material_filter:
            query = query.ilike('mercadoria', f'%{material_filter}%')
        
        # Aplicar paginação
        offset = (page - 1) * per_page
        result = query.range(offset, offset + per_page - 1).execute()
        processos = result.data or []
        
        # Calcular despesas e extrair número do pedido para cada processo
        for p in processos:
            vmcv = float(p.get('valor_cif_real') or 0)
            # Calcular despesas como 40% do VMCV
            p['total_despesas'] = vmcv * 0.4
            # Normalizar nome do material
            p['mercadoria'] = normalize_material_name(p.get('mercadoria'))
            
            # Extrair número do pedido das referências (mesmo código do dashboard)
            nro_pedido = ""
            # Campo referencias não existe na nova tabela - usando ref_importador como alternativa
            nro_pedido = p.get('ref_importador', '') or ''
            
            # try:
            #     if referencias:
            #         if isinstance(referencias, str):
            #             # Se for string, tentar fazer parse do JSON
            #             import json
            #             referencias = json.loads(referencias)
            #         
            #         # Se for uma lista com dicionários
            #         if isinstance(referencias, list) and len(referencias) > 0:
            #             primeiro_item = referencias[0]
            #             if isinstance(primeiro_item, dict) and 'referencia' in primeiro_item:
            #                 nro_pedido = str(primeiro_item['referencia'])
            #             elif primeiro_item:
            #                 nro_pedido = str(primeiro_item)
            #         
            #         # Se for um dicionário direto
            #         elif isinstance(referencias, dict) and 'referencia' in referencias:
            #             nro_pedido = str(referencias['referencia'])
            #             
            # except (json.JSONDecodeError, TypeError, IndexError, KeyError):
            #     nro_pedido = ""
            
            
            # Adicionar número do pedido ao processo
            p['nro_pedido'] = nro_pedido
        
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

@bp.route('/api/principais-materiais')
@login_required
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def get_principais_materiais():
    """Resumo dos principais materiais ordenados por total de processos"""
    try:
        # Obter filtros da requisição
        material_filter = request.args.get('material', '')
        date_start = request.args.get('date_start', '')
        date_end = request.args.get('date_end', '')
        cliente_filter = request.args.get('cliente', '')
        modal_filter = request.args.get('modal', '')
        
        # Construir query base
        query = supabase.table('importacoes_processos_aberta').select(
            'id, valor_fob_real, data_embarque, data_chegada, mercadoria, importador, cliente_cpfcnpj'
        )
        
        # Aplicar filtro de empresa baseado no usuário
        query = apply_company_filter(query)
        
        # Aplicar filtros do usuário
        if material_filter:
            query = query.ilike('mercadoria', f'%{material_filter}%')
        
        if date_start:
            query = query.gte('data_abertura', date_start)
        
        if date_end:
            query = query.lte('data_abertura', date_end)
            
        if cliente_filter:
            query = query.eq('cnpj_importador', cliente_filter)
        
        if modal_filter:
            query = query.eq('modal', modal_filter)
        
        # Executar query principal
        processos_result = query.limit(2000).execute()
        processos = processos_result.data or []
        
        # Agrupar dados por material
        materiais_data = defaultdict(lambda: {
            'total_processos': 0,
            'vmle_total': 0,
            'data_chegada_mais_recente': None
        })
        
        for p in processos:
            material = normalize_material_name(p.get('mercadoria'))
            vmle = float(p.get('valor_fob_real') or 0)
            data_chegada = p.get('data_chegada')
            
            # Acumular dados por material
            materiais_data[material]['total_processos'] += 1
            materiais_data[material]['vmle_total'] += vmle
            
            # Atualizar data de chegada mais recente
            if data_chegada:
                try:
                    data_chegada_dt = datetime.fromisoformat(data_chegada.replace('Z', '+00:00'))
                    if (materiais_data[material]['data_chegada_mais_recente'] is None or 
                        data_chegada_dt > materiais_data[material]['data_chegada_mais_recente']):
                        materiais_data[material]['data_chegada_mais_recente'] = data_chegada_dt
                except:
                    pass
        
        # Converter para lista e ordenar por total de processos
        principais_materiais = []
        for material, data in materiais_data.items():
            data_chegada_str = ''
            if data['data_chegada_mais_recente']:
                data_chegada_str = data['data_chegada_mais_recente'].strftime('%d/%m/%Y')
            
            principais_materiais.append({
                'material': material,
                'total_processos': data['total_processos'],
                'vmle_total': data['vmle_total'],
                'data_chegada': data_chegada_str,
                'vmle_total_formatted': f"R$ {data['vmle_total']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            })
        
        # Ordenar por total de processos (decrescente) e pegar top 15
        principais_materiais.sort(key=lambda x: x['total_processos'], reverse=True)
        principais_materiais = principais_materiais[:15]
        
        return jsonify({
            'success': True,
            'data': principais_materiais
        })
        
    except Exception as e:
        print(f"[ERROR get_principais_materiais] {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/radar-cliente-material')
@login_required
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def get_radar_cliente_material():
    """Gráfico de radar comparando performance de materiais por métricas normalizadas"""
    try:
        print("\n[DEBUG RADAR] === INICIANDO ANÁLISE DO RADAR ===")
        
        # Verificar se a sessão está válida
        if 'user' not in session or not session['user']:
            print("[DEBUG RADAR] ERRO: Sessão inválida")
            return jsonify({
                'status': 'error',
                'message': 'Sessão inválida',
                'data': {'labels': [], 'datasets': []}
            }), 401
        
        print(f"[DEBUG RADAR] Usuário: {session['user'].get('role', 'Unknown')}")
        
        # Buscar todos os processos com dados necessários
        query = supabase.table('importacoes_processos_aberta').select(
            'mercadoria, valor_cif_real, data_embarque, data_chegada, data_chegada, canal, cliente_cpfcnpj'
        )
        
        # Aplicar filtro de empresa baseado no usuário com tratamento de erro
        try:
            query = apply_company_filter(query)
            print("[DEBUG RADAR] Filtro de empresa aplicado com sucesso")
        except Exception as filter_error:
            print(f"[DEBUG RADAR] Erro ao aplicar filtro de empresa: {filter_error}")
            # Continuar sem o filtro em caso de erro
        
        result = query.limit(2000).execute()
        processos = result.data or []
        
        print(f"[DEBUG RADAR] Processos encontrados: {len(processos)}")
        
        if not processos:
            print("[DEBUG RADAR] ERRO: Nenhum processo encontrado na query inicial")
            return jsonify({
                'status': 'success',
                'data': {'labels': [], 'datasets': []}
            })
        
        # Debug dos primeiros processos
        print(f"[DEBUG RADAR] Exemplo dos primeiros 3 processos:")
        for i, p in enumerate(processos[:3]):
            print(f"  Processo {i+1}:")
            print(f"    Material: {p.get('mercadoria')}")
            print(f"    VMCV: {p.get('valor_cif_real')}")
            print(f"    Data embarque: {p.get('data_embarque')}")
            print(f"    Data chegada: {p.get('data_chegada')}")
            print(f"    Canal: {p.get('canal')}")
        
        # Agrupar dados por material
        material_data = defaultdict(lambda: {
            'valores': [],
            'despesas': [],
            'tempos_transito': [],
            'processos_count': 0,
            'inspecoes': 0
        })
        
        processos_validos = 0
        processos_sem_material = 0
        processos_sem_vmcv = 0
        
        for p in processos:
            material = normalize_material_name(p.get('mercadoria'))
            if not material or material == 'Não informado':
                processos_sem_material += 1
                continue
                
            vmcv = float(p.get('valor_cif_real') or 0)
            if vmcv <= 0:
                processos_sem_vmcv += 1
                continue
                
            processos_validos += 1
            
            # Calcular despesas como 40% do VMCV
            despesa = vmcv * 0.4
            
            # Calcular tempo de trânsito
            tempo_transito = 0
            data_embarque = p.get('data_embarque')
            data_chegada = p.get('data_chegada') or p.get('data_chegada')
            
            if data_embarque and data_chegada:
                try:
                    embarque = datetime.fromisoformat(data_embarque.replace('Z', '+00:00'))
                    chegada = datetime.fromisoformat(data_chegada.replace('Z', '+00:00'))
                    tempo_transito = (chegada - embarque).days
                    if tempo_transito < 0:
                        tempo_transito = 0
                except Exception as e:
                    print(f"[DEBUG RADAR] Erro ao calcular tempo de trânsito: {e}")
                    tempo_transito = 0
            
            # Verificar se houve inspeção (canal diferente de verde)
            canal = p.get('canal', '').lower()
            tem_inspecao = canal not in ['verde', '', None]
            
            # Adicionar aos dados do material
            material_data[material]['valores'].append(vmcv)
            material_data[material]['despesas'].append(despesa)
            if tempo_transito > 0:
                material_data[material]['tempos_transito'].append(tempo_transito)
            material_data[material]['processos_count'] += 1
            if tem_inspecao:
                material_data[material]['inspecoes'] += 1
        
        print(f"[DEBUG RADAR] Resumo do processamento:")
        print(f"  Processos válidos: {processos_validos}")
        print(f"  Processos sem material: {processos_sem_material}")
        print(f"  Processos sem VMCV: {processos_sem_vmcv}")
        print(f"  Materiais únicos encontrados: {len(material_data)}")
        
        # Debug dos materiais encontrados
        print(f"[DEBUG RADAR] Top 10 materiais por quantidade de processos:")
        materiais_por_qtd = sorted(material_data.items(), key=lambda x: x[1]['processos_count'], reverse=True)
        for i, (material, data) in enumerate(materiais_por_qtd[:10]):
            print(f"  {i+1}. {material}: {data['processos_count']} processos")
        
        # Calcular métricas agregadas por material
        metricas_materiais = {}
        materiais_filtrados = 0
        for material, data in material_data.items():
            # REDUZIR CRITÉRIO: aceitar materiais com pelo menos 1 processo (ao invés de 3)
            if data['processos_count'] < 1:  # Filtrar materiais com nenhum processo
                materiais_filtrados += 1
                continue
                
            # Calcular médias e métricas
            valor_medio = np.mean(data['valores']) if data['valores'] else 0
            despesa_media = np.mean(data['despesas']) if data['despesas'] else 0
            tempo_medio = np.mean(data['tempos_transito']) if data['tempos_transito'] else 30  # Default 30 dias se não há dados
            volume_processos = data['processos_count']
            taxa_inspecao = (data['inspecoes'] / data['processos_count']) * 100 if data['processos_count'] > 0 else 0
            
            metricas_materiais[material] = {
                'valor_medio': valor_medio,
                'despesa_media': despesa_media,
                'tempo_medio': tempo_medio,
                'volume_processos': volume_processos,
                'taxa_inspecao': taxa_inspecao
            }
        
        print(f"[DEBUG RADAR] Materiais filtrados (< 1 processo): {materiais_filtrados}")
        print(f"[DEBUG RADAR] Materiais qualificados: {len(metricas_materiais)}")
        
        if not metricas_materiais:
            print("[DEBUG RADAR] ERRO: Nenhum material qualificado após filtros")
            return jsonify({
                'status': 'success',
                'data': {'labels': [], 'datasets': []},
                'debug': 'Nenhum material com dados suficientes encontrado'
            })
        
        # Debug das métricas dos materiais qualificados
        print(f"[DEBUG RADAR] Métricas dos materiais qualificados:")
        for material, metricas in list(metricas_materiais.items())[:5]:
            print(f"  {material}:")
            print(f"    Valor médio: R$ {metricas['valor_medio']:,.2f}")
            print(f"    Despesa média: R$ {metricas['despesa_media']:,.2f}")
            print(f"    Tempo médio: {metricas['tempo_medio']:.1f} dias")
            print(f"    Volume: {metricas['volume_processos']} processos")
            print(f"    Taxa inspeção: {metricas['taxa_inspecao']:.1f}%")
        
        # Selecionar top materiais por valor total (ajustar quantidade se necessário)
        num_materiais = min(len(metricas_materiais), 6)  # Máximo 6 (todos os disponíveis)
        totais_por_material = {}
        for material, data in material_data.items():
            if material in metricas_materiais:
                totais_por_material[material] = sum(data['valores'])
        
        top_materiais = sorted(totais_por_material.items(), key=lambda x: x[1], reverse=True)[:num_materiais]
        materiais_selecionados = [material for material, _ in top_materiais]
        
        print(f"[DEBUG RADAR] Top {num_materiais} materiais selecionados para o radar:")
        for i, (material, valor_total) in enumerate(top_materiais):
            print(f"  {i+1}. {material}: R$ {valor_total:,.2f}")
        
        if not materiais_selecionados:
            print("[DEBUG RADAR] ERRO: Nenhum material selecionado para o top")
            return jsonify({
                'status': 'success',
                'data': {'labels': [], 'datasets': []},
                'debug': 'Nenhum material encontrado'
            })
        
        # Extrair valores de cada métrica para normalização
        valores_medios = [metricas_materiais[m]['valor_medio'] for m in materiais_selecionados]
        despesas_medias = [metricas_materiais[m]['despesa_media'] for m in materiais_selecionados]
        tempos_medios = [metricas_materiais[m]['tempo_medio'] for m in materiais_selecionados]
        volumes_processos = [metricas_materiais[m]['volume_processos'] for m in materiais_selecionados]
        taxas_inspecao = [metricas_materiais[m]['taxa_inspecao'] for m in materiais_selecionados]
        
        print(f"[DEBUG RADAR] Valores para normalização:")
        print(f"  Valores médios: {valores_medios}")
        print(f"  Despesas médias: {despesas_medias}")
        print(f"  Tempos médios: {tempos_medios}")
        print(f"  Volumes processos: {volumes_processos}")
        print(f"  Taxas inspeção: {taxas_inspecao}")
        
        # Função para normalizar métricas (0-100)
        def normalizar_metrica(valores, inverter=False):
            if not valores or all(v == 0 for v in valores):
                print(f"[DEBUG RADAR] Normalização: valores vazios ou todos zero")
                return [0] * len(valores)
            
            min_val = min(valores)
            max_val = max(valores)
            
            print(f"[DEBUG RADAR] Normalização: min={min_val}, max={max_val}, inverter={inverter}")
            
            if min_val == max_val:
                print(f"[DEBUG RADAR] Normalização: todos valores iguais, retornando 50")
                return [50] * len(valores)  # Valor médio se todos iguais
            
            normalized = []
            for v in valores:
                if inverter:  # Para métricas onde menor é melhor (tempo, despesa, inspeção)
                    norm = 100 - ((v - min_val) / (max_val - min_val)) * 100
                else:  # Para métricas onde maior é melhor (valor, volume)
                    norm = ((v - min_val) / (max_val - min_val)) * 100
                normalized.append(round(norm, 1))
            
            print(f"[DEBUG RADAR] Valores normalizados: {normalized}")
            return normalized
        
        # Normalizar todas as métricas
        print(f"[DEBUG RADAR] === INICIANDO NORMALIZAÇÃO ===")
        valores_norm = normalizar_metrica(valores_medios, inverter=False)
        despesas_norm = normalizar_metrica(despesas_medias, inverter=True)
        tempos_norm = normalizar_metrica(tempos_medios, inverter=True)
        volumes_norm = normalizar_metrica(volumes_processos, inverter=False)
        inspecoes_norm = normalizar_metrica(taxas_inspecao, inverter=True)
        
        # Preparar dados para o radar
        labels = ['Valor Médio', 'Eficiência Custo', 'Rapidez Trânsito', 'Volume Processos', 'Taxa Aprovação']
        
        print(f"[DEBUG RADAR] === MONTANDO DATASETS ===")
        
        datasets = []
        colors = [
            'rgba(79, 172, 254, 0.2)',   # Azul
            'rgba(34, 197, 94, 0.2)',    # Verde
            'rgba(251, 191, 36, 0.2)',   # Amarelo
            'rgba(239, 68, 68, 0.2)',    # Vermelho
            'rgba(168, 85, 247, 0.2)'    # Roxo
        ]
        border_colors = [
            'rgba(79, 172, 254, 1)',
            'rgba(34, 197, 94, 1)',
            'rgba(251, 191, 36, 1)',
            'rgba(239, 68, 68, 1)',
            'rgba(168, 85, 247, 1)'
        ]
        
        for i, material in enumerate(materiais_selecionados):
            # Dados normalizados para cada material
            data_points = [
                valores_norm[i],    # Valor Médio
                despesas_norm[i],   # Eficiência Custo (inverso da despesa)
                tempos_norm[i],     # Rapidez Trânsito (inverso do tempo)
                volumes_norm[i],    # Volume Processos
                inspecoes_norm[i]   # Taxa Aprovação (inverso da inspeção)
            ]
            
            print(f"[DEBUG RADAR] Material {i+1} - {material}:")
            print(f"  Data points: {data_points}")
            
            datasets.append({
                'label': material,
                'data': data_points,
                'backgroundColor': colors[i % len(colors)],
                'borderColor': border_colors[i % len(border_colors)],
                'borderWidth': 2,
                'pointBackgroundColor': border_colors[i % len(border_colors)],
                'pointBorderColor': '#fff',
                'pointBorderWidth': 2,
                'pointRadius': 4
            })
        
        print(f"[DEBUG RADAR] === RESULTADO FINAL ===")
        print(f"Labels: {labels}")
        print(f"Datasets criados: {len(datasets)}")
        
        resposta_final = {
            'status': 'success',
            'data': {
                'labels': labels,
                'datasets': datasets
            }
        }
        
        print(f"[DEBUG RADAR] Resposta final: {resposta_final}")
        print(f"[DEBUG RADAR] === FIM DA ANÁLISE DO RADAR ===\n")
        
        return jsonify(resposta_final)
        
    except Exception as e:
        print(f"[ERROR RADAR] Erro geral no radar: {str(e)}")
        import traceback
        print(f"[ERROR RADAR] Traceback: {traceback.format_exc()}")
        
        return jsonify({
            'status': 'error', 
            'message': f'Erro no radar: {str(e)}',
            'data': {'labels': [], 'datasets': []}
        }), 500

@bp.route('/api/materiais-opcoes')
@login_required
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def get_materiais_opcoes():
    """Buscar todos os materiais únicos para o dropdown"""
    try:
        # Buscar todos os materiais únicos
        query = supabase.table('importacoes_processos_aberta').select('mercadoria, cliente_cpfcnpj')
        
        # Aplicar filtro de empresa baseado no usuário
        query = apply_company_filter(query)
        
        result = query.limit(2000).execute()
        processos = result.data or []
        
        # Normalizar e obter materiais únicos
        materiais_set = set()
        for p in processos:
            material = normalize_material_name(p.get('mercadoria'))
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
        query = supabase.table('importacoes_processos_aberta').select(
            'id, numero_di, data_chegada, mercadoria, importador, urf_entrada, modal, valor_cif_real, cliente_cpfcnpj'
        ).gte('data_chegada', str(hoje)).lte('data_chegada', str(data_limite))
        
        # Aplicar filtro de empresa baseado no usuário
        query = apply_company_filter(query)
        
        processos_result = query.order('data_chegada').limit(20).execute()
        
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
            status_processo = d.get('situacao_descricao', '').lower()
            
            if processo_id and valor:
                try:
                    valor_float = float(valor)
                    if status_processo == 'aprovado':
                        despesas_por_processo[processo_id]['aprovadas'] += valor_float
                    elif status_processo == 'pendente':
                        despesas_por_processo[processo_id]['pendentes'] += valor_float
                    
                    if status_processo in ['aprovado', 'pendente']:
                        despesas_por_processo[processo_id]['total'] += valor_float
                except (ValueError, TypeError):
                    continue
        
        # Processar os dados para incluir material normalizado e despesas
        for processo in processos:
            processo['mercadoria'] = normalize_material_name(processo.get('mercadoria'))
            
            # Adicionar dados de despesas
            despesas_info = despesas_por_processo.get(processo['id'], {'aprovadas': 0, 'pendentes': 0, 'total': 0})
            processo['total_despesas_aprovadas'] = despesas_info['aprovadas']
            processo['total_despesas_pendentes'] = despesas_info['pendentes']
            processo['total_despesas_previsto'] = despesas_info['total']
            
            # Garantir que valores numéricos não sejam None
            processo['valor_cif_real'] = float(processo.get('valor_cif_real') or 0)
        
        return jsonify({
            'status': 'success',
            'data': processos
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@bp.route('/api/material-modal')
@login_required
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def get_material_modal():
    """Análise de material por modal de transporte"""
    try:
        # Obter filtros da requisição
        material_filter = request.args.get('material', '')
        date_start = request.args.get('date_start', '')
        date_end = request.args.get('date_end', '')
        cliente_filter = request.args.get('cliente', '')
        modal_filter = request.args.get('modal', '')
        
        # Construir query base
        query = supabase.table('importacoes_processos_aberta').select(
            'mercadoria, modal, cliente_cpfcnpj'
        )
        
        # Aplicar filtro de empresa baseado no usuário
        query = apply_company_filter(query)
        
        # Aplicar filtros do usuário
        if material_filter:
            query = query.ilike('mercadoria', f'%{material_filter}%')
        
        if date_start:
            query = query.gte('data_abertura', date_start)
        
        if date_end:
            query = query.lte('data_abertura', date_end)
            
        if cliente_filter:
            query = query.eq('cnpj_importador', cliente_filter)
        
        if modal_filter:
            query = query.eq('modal', modal_filter)
        
        result = query.limit(2000).execute()
        processos = result.data or []
        
        # Agrupar por material e modal
        materiais_modal = defaultdict(lambda: defaultdict(int))
        for p in processos:
            material = normalize_material_name(p.get('mercadoria'))
            modal = p.get('modal') or 'Não informado'
            
            # Normalizar nomes dos modais
            if modal == 'AEREA':
                modal = 'Aéreo'
            elif modal == 'MARITIMA':
                modal = 'Marítimo'
            elif modal == 'TERRESTRE':
                modal = 'Terrestre'
            else:
                modal = 'Outros'
                
            materiais_modal[material][modal] += 1
        
        # Pegar top 5 materiais por total de processos
        totais_por_material = {mat: sum(modais.values()) for mat, modais in materiais_modal.items()}
        top_materiais = sorted(totais_por_material.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Preparar dados para o gráfico com barras 100%
        labels = [item[0] for item in top_materiais]
        aereo = []
        maritimo = []
        rodoviario = []
        outros = []
        aereo_qtd = []
        maritimo_qtd = []
        rodoviario_qtd = []
        outros_qtd = []
        
        for material in labels:
            modais = materiais_modal[material]
            total = sum(modais.values())
            if total > 0:
                aereo_count = modais.get('Aéreo', 0)
                maritimo_count = modais.get('Marítimo', 0)
                rodoviario_count = modais.get('Terrestre', 0)
                outros_count = modais.get('Outros', 0)
                
                aereo_pct = (aereo_count / total * 100)
                maritimo_pct = (maritimo_count / total * 100)
                rodoviario_pct = (rodoviario_count / total * 100)
                outros_pct = (outros_count / total * 100)
                
                # Garantir que a soma seja exatamente 100%
                total_pct = aereo_pct + maritimo_pct + rodoviario_pct + outros_pct
                if total_pct > 0:
                    factor = 100 / total_pct
                    aereo_pct *= factor
                    maritimo_pct *= factor
                    rodoviario_pct *= factor
                    outros_pct *= factor
                
                aereo.append(aereo_pct)
                maritimo.append(maritimo_pct)
                rodoviario.append(rodoviario_pct)
                outros.append(outros_pct)
                aereo_qtd.append(aereo_count)
                maritimo_qtd.append(maritimo_count)
                rodoviario_qtd.append(rodoviario_count)
                outros_qtd.append(outros_count)
            else:
                aereo.append(0)
                maritimo.append(0)
                rodoviario.append(0)
                outros.append(0)
                aereo_qtd.append(0)
                maritimo_qtd.append(0)
                rodoviario_qtd.append(0)
                outros_qtd.append(0)
        
        return jsonify({
            'status': 'success',
            'data': {
                'labels': labels,
                'aereo': aereo,
                'maritimo': maritimo,
                'rodoviario': rodoviario,
                'outros': outros,
                'aereo_qtd': aereo_qtd,
                'maritimo_qtd': maritimo_qtd,
                'rodoviario_qtd': rodoviario_qtd,
                'outros_qtd': outros_qtd,
                'horizontal': True
            }
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@bp.route('/api/clientes-opcoes')
@login_required
def clientes_opcoes():
    """Endpoint para buscar clientes para autocomplete"""
    try:
        search_term = request.args.get('search', '').strip()
        
        # Base query - usar a tabela correta de importações
        query = supabase.table('importacoes_processos_aberta') \
                        .select('cliente_razaosocial, cliente_cpfcnpj') \
                        .not_.is_('importador', 'null') \
                        .not_.eq('importador', '')
        
        # Aplicar filtros de empresa do usuário
        query = apply_company_filter(query)
        
        # Aplicar filtro de busca se fornecido
        if search_term:
            query = query.ilike('importador', f'%{search_term}%')
        
        # Buscar dados únicos
        response = query.limit(100).execute()
        
        if response.data:
            # Criar lista única de clientes
            clientes_set = set()
            for item in response.data:
                if item.get('importador'):
                    clientes_set.add((item['importador'], item['cnpj_importador']))
            
            # Converter para lista ordenada
            clientes = [
                {'label': cliente[0], 'value': cliente[1]} 
                for cliente in sorted(clientes_set, key=lambda x: x[0])
            ]
            
            return jsonify({
                'success': True,
                'data': clientes[:50]  # Limitar a 50 resultados
            })
        
        return jsonify({
            'success': True,
            'data': []
        })
        
    except Exception as e:
        print(f"[ERROR clientes_opcoes] {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@bp.route('/api/modais-opcoes')
@login_required
def modais_opcoes():
    """Endpoint para buscar modais de transporte disponíveis"""
    try:
        # Base query - usar a tabela correta de importações
        query = supabase.table('importacoes_processos_aberta') \
                        .select('modal') \
                        .not_.is_('modal', 'null') \
                        .not_.eq('modal', '')
        
        # Aplicar filtros de empresa do usuário
        query = apply_company_filter(query)
        
        # Buscar dados únicos
        response = query.limit(1000).execute()
        
        if response.data:
            # Criar lista única de modais
            modais_set = set()
            for item in response.data:
                if item.get('modal'):
                    modais_set.add(item['modal'])
            
            # Converter para lista ordenada
            modais = [
                {'label': modal, 'value': modal} 
                for modal in sorted(modais_set)
            ]
            
            return jsonify({
                'success': True,
                'data': modais
            })
        
        return jsonify({
            'success': True,
            'data': []
        })
        
    except Exception as e:
        print(f"[ERROR modais_opcoes] {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

def get_multiple_filter_values(param_name):
    """Get multiple values for a filter parameter"""
    # Suporte para parâmetros múltiplos (ex: ?cliente=A&cliente=B)
    values = request.args.getlist(param_name)
    if values:
        return [v.strip() for v in values if v.strip()]
    
    # Fallback para valor único
    single_value = request.args.get(param_name, '').strip()
    if single_value:
        return [single_value]
    
    return []

def apply_multiple_filter(query, field_name, values, filter_type='ilike'):
    """Apply multiple values filter to a query"""
    if not values:
        return query
    
    if len(values) == 1:
        # Single value
        if filter_type == 'ilike':
            return query.ilike(field_name, f'%{values[0]}%')
        elif filter_type == 'eq':
            return query.eq(field_name, values[0])
    else:
        # Multiple values - use OR condition
        if filter_type == 'ilike':
            # Para ilike, construir condição OR manualmente
            conditions = []
            for value in values:
                conditions.append(f'{field_name}.ilike.%{value}%')
            # Usar or_ para múltiplas condições
            return query.or_(','.join(conditions))
        elif filter_type == 'eq':
            # Para eq, usar in_
            return query.in_(field_name, values)
    
    return query
