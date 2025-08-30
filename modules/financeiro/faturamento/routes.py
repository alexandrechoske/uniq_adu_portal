from flask import Blueprint, render_template, session, jsonify, request
from extensions import supabase, supabase_admin
from routes.auth import login_required
from decorators.perfil_decorators import perfil_required
from datetime import datetime
import calendar
import json
from collections import defaultdict

# Blueprint para Faturamento
faturamento_bp = Blueprint(
    'fin_faturamento', 
    __name__,
    url_prefix='/financeiro/faturamento',
    template_folder='templates',
    static_folder='static',
    static_url_path='/financeiro/faturamento/static'
)

@faturamento_bp.route('/')
@login_required
@perfil_required('financeiro', 'faturamento')
def index():
    """Faturamento Anual - Controle de receitas"""
    return render_template('faturamento.html')

@faturamento_bp.route('/api/geral/kpis')
@login_required
@perfil_required('financeiro', 'faturamento')
def api_geral_kpis():
    """API para KPIs da Visão Geral de Faturamento"""
    try:
        ano = request.args.get('ano', datetime.now().year)
        
        # Buscar dados de faturamento do ano
        response = supabase_admin.table('fin_faturamento_anual').select('*').gte('data', f'{ano}-01-01').lte('data', f'{ano}-12-31').execute()
        dados_faturamento = response.data
        
        # Calcular total faturado
        total_faturado = sum(float(item['valor']) for item in dados_faturamento)
        
        # Buscar meta do ano
        meta_response = supabase_admin.table('fin_metas_financeiras').select('meta').eq('ano', str(ano)).execute()
        meta_anual = sum(item['meta'] for item in meta_response.data) if meta_response.data else 0
        
        # Calcular valores
        target_realizado = total_faturado
        target_a_realizar = meta_anual - total_faturado if meta_anual > 0 else 0
        
        return jsonify({
            'total_faturado': total_faturado,
            'meta_anual': meta_anual,
            'target_realizado': target_realizado,
            'target_a_realizar': target_a_realizar
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@faturamento_bp.route('/api/geral/mensal')
@login_required
@perfil_required('financeiro', 'faturamento')
def api_geral_mensal():
    """API para tabela de faturamento mensal da Visão Geral"""
    try:
        ano = request.args.get('ano', datetime.now().year)
        
        # Buscar dados de faturamento do ano atual
        response_atual = supabase_admin.table('fin_faturamento_anual').select('*').gte('data', f'{ano}-01-01').lte('data', f'{ano}-12-31').execute()
        dados_atual = response_atual.data
        
        # Buscar dados de faturamento do ano anterior
        ano_anterior = int(ano) - 1
        response_anterior = supabase_admin.table('fin_faturamento_anual').select('*').gte('data', f'{ano_anterior}-01-01').lte('data', f'{ano_anterior}-12-31').execute()
        dados_anterior = response_anterior.data
        
        # Agrupar por mês para o ano atual
        faturamento_atual = defaultdict(float)
        for item in dados_atual:
            data_item = datetime.strptime(item['data'], '%Y-%m-%d')
            mes_key = data_item.strftime('%Y-%m')
            faturamento_atual[mes_key] += float(item['valor'])
        
        # Agrupar por mês para o ano anterior
        faturamento_anterior = defaultdict(float)
        for item in dados_anterior:
            data_item = datetime.strptime(item['data'], '%Y-%m-%d')
            mes_key = data_item.strftime('%Y-%m')
            faturamento_anterior[mes_key] += float(item['valor'])
        
        # Preparar dados para a tabela
        meses = []
        for mes in range(1, 13):
            mes_atual = f"{ano}-{mes:02d}"
            mes_anterior = f"{ano_anterior}-{mes:02d}"
            
            faturamento_mes = faturamento_atual.get(mes_atual, 0)
            faturamento_mes_anterior = faturamento_anterior.get(mes_anterior, 0)
            
            # Calcular variação percentual
            if faturamento_mes_anterior > 0:
                variacao = ((faturamento_mes - faturamento_mes_anterior) / faturamento_mes_anterior) * 100
            else:
                variacao = 0 if faturamento_mes == 0 else 100
            
            meses.append({
                'ano': ano,
                'mes': mes,
                'faturamento_total': faturamento_mes,
                'faturamento_anterior': faturamento_mes_anterior,
                'variacao': variacao
            })
        
        return jsonify(meses)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@faturamento_bp.route('/api/geral/proporcao')
@login_required
@perfil_required('financeiro', 'faturamento')
def api_geral_proporcao():
    """API para gráficos de proporção da Visão Geral"""
    try:
        ano = request.args.get('ano', datetime.now().year)
        
        # Buscar dados de faturamento do ano
        response = supabase_admin.table('fin_faturamento_anual').select('*').gte('data', f'{ano}-01-01').lte('data', f'{ano}-12-31').execute()
        dados_faturamento = response.data
        
        # Calcular totais por setor
        total_importacao = 0
        total_consultoria = 0
        total_exportacao = 0
        
        for item in dados_faturamento:
            classe = item.get('classe', '').upper()
            valor = float(item['valor'])
            
            if 'IMP' in classe or 'IMPORT' in classe:
                total_importacao += valor
            elif 'CONS' in classe or 'CONSULT' in classe:
                total_consultoria += valor
            elif 'EXP' in classe or 'EXPORT' in classe:
                total_exportacao += valor
        
        total_geral = total_importacao + total_consultoria + total_exportacao
        
        # Calcular percentuais
        pct_importacao = (total_importacao / total_geral * 100) if total_geral > 0 else 0
        pct_consultoria = (total_consultoria / total_geral * 100) if total_geral > 0 else 0
        pct_exportacao = (total_exportacao / total_geral * 100) if total_geral > 0 else 0
        
        # Buscar meta do ano
        meta_response = supabase_admin.table('fin_metas_financeiras').select('meta').eq('ano', str(ano)).execute()
        meta_anual = sum(item['meta'] for item in meta_response.data) if meta_response.data else 0
        
        # Calcular percentual faturado vs meta
        pct_faturado = (total_geral / meta_anual * 100) if meta_anual > 0 else 0
        pct_a_realizar = 100 - pct_faturado if meta_anual > 0 else 0
        
        return jsonify({
            'setores': {
                'importacao': {
                    'valor': total_importacao,
                    'percentual': pct_importacao
                },
                'consultoria': {
                    'valor': total_consultoria,
                    'percentual': pct_consultoria
                },
                'exportacao': {
                    'valor': total_exportacao,
                    'percentual': pct_exportacao
                }
            },
            'meta': {
                'faturado': {
                    'valor': total_geral,
                    'percentual': pct_faturado
                },
                'a_realizar': {
                    'valor': meta_anual - total_geral if meta_anual > 0 else 0,
                    'percentual': pct_a_realizar
                }
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@faturamento_bp.route('/api/setor/dados_completos')
@login_required
@perfil_required('financeiro', 'faturamento')
def api_setor_dados_completos():
    """API para dados completos de um setor específico"""
    try:
        setor = request.args.get('setor', 'importacao')
        inicio = request.args.get('inicio')
        fim = request.args.get('fim')
        
        # Definir filtro de classe com base no setor
        filtro_classe = ''
        if setor == 'importacao':
            filtro_classe = 'IMP'
        elif setor == 'consultoria':
            filtro_classe = 'CONS'
        elif setor == 'exportacao':
            filtro_classe = 'EXP'
        
        # Buscar dados de faturamento com filtro de classe
        query = supabase_admin.table('fin_faturamento_anual').select('*')
        if filtro_classe:
            query = query.ilike('classe', f'%{filtro_classe}%')
        if inicio and fim:
            query = query.gte('data', inicio).lte('data', fim)
        
        response = query.execute()
        dados_faturamento = response.data
        
        # Calcular faturamento total do setor
        total_setor = sum(float(item['valor']) for item in dados_faturamento)
        
        # Calcular participação percentual no faturamento total
        # Buscar faturamento total da empresa no mesmo período
        total_query = supabase_admin.table('fin_faturamento_anual').select('*')
        if inicio and fim:
            total_query = total_query.gte('data', inicio).lte('data', fim)
        total_response = total_query.execute()
        total_empresa = sum(float(item['valor']) for item in total_response.data)
        
        pct_participacao = (total_setor / total_empresa * 100) if total_empresa > 0 else 0
        
        # Agrupar faturamento mensal do setor
        faturamento_mensal = defaultdict(float)
        faturamento_mensal_anterior = defaultdict(float)
        
        for item in dados_faturamento:
            data_item = datetime.strptime(item['data'], '%Y-%m-%d')
            mes_key = data_item.strftime('%Y-%m')
            
            # Fix the date error by ensuring we don't go out of range when creating the previous year date
            try:
                # Para comparação com ano anterior
                if data_item.month == 2 and data_item.day == 29:
                    # Handle leap year case - use Feb 28 of previous year
                    data_anterior = data_item.replace(year=data_item.year - 1, day=28)
                else:
                    data_anterior = data_item.replace(year=data_item.year - 1)
                mes_anterior_key = data_anterior.strftime('%Y-%m')
                faturamento_mensal_anterior[mes_anterior_key] += float(item['valor'])
            except ValueError:
                # Handle any other date errors by skipping this item for previous year comparison
                pass
            
            faturamento_mensal[mes_key] += float(item['valor'])
        
        # Preparar dados mensais
        meses_data = []
        # Get all unique months from the current period data
        meses_unicos = set(faturamento_mensal.keys())
        for mes_key in sorted(meses_unicos):
            # For each month in current period, we want to show:
            # 1. Current period value (faturamento)
            # 2. Previous period value (faturamento_anterior) for the same month
            
            # Calculate the previous year's month key for comparison
            year, month = mes_key.split('-')
            mes_anterior_key = f"{int(year)-1}-{month}"
            
            meses_data.append({
                'mes': mes_key,
                'faturamento': faturamento_mensal.get(mes_key, 0),
                'faturamento_anterior': faturamento_mensal_anterior.get(mes_anterior_key, 0)
            })
        
        # Ranking de clientes
        clientes_ranking = defaultdict(lambda: {'valor': 0, 'classe': ''})
        for item in dados_faturamento:
            cliente = item.get('cliente', 'Não identificado')
            clientes_ranking[cliente]['valor'] += float(item['valor'])
            clientes_ranking[cliente]['classe'] = item.get('classe', '')
        
        # Converter para lista e ordenar
        ranking_lista = []
        for cliente, dados in clientes_ranking.items():
            pct_gt = (dados['valor'] / total_setor * 100) if total_setor > 0 else 0
            ranking_lista.append({
                'cliente': cliente,
                'classe': dados['classe'],
                'valor': dados['valor'],
                'pct_gt': pct_gt
            })
        
        ranking_lista.sort(key=lambda x: x['valor'], reverse=True)
        
        return jsonify({
            'kpis': {
                'faturamento_total': total_setor,
                'percentual_participacao': pct_participacao
            },
            'grafico_mensal': meses_data,
            'ranking_clientes': ranking_lista
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API endpoints for Metas management
@faturamento_bp.route('/api/metas', methods=['GET'])
@login_required
@perfil_required('financeiro', 'faturamento')
def api_get_metas():
    """API para obter todas as metas financeiras"""
    try:
        # Only get financeiro type metas
        response = supabase_admin.table('fin_metas_financeiras').select('*').eq('tipo', 'financeiro').order('ano', desc=True).order('mes').execute()
        return jsonify(response.data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@faturamento_bp.route('/api/metas', methods=['POST'])
@login_required
@perfil_required('financeiro', 'faturamento')
def api_create_meta():
    """API para criar ou atualizar uma meta financeira"""
    try:
        data = request.get_json()
        ano = data.get('ano')
        mes = data.get('mes')  # New field
        meta = data.get('meta')
        tipo = data.get('tipo', 'financeiro')  # Default to financeiro
        
        if not ano or meta is None:
            return jsonify({'error': 'Ano e meta são obrigatórios'}), 400
        
        # Verificar se já existe uma meta para este ano e mês e tipo
        query = supabase_admin.table('fin_metas_financeiras').select('*').eq('ano', str(ano)).eq('tipo', tipo)
        if mes:
            query = query.eq('mes', mes)
        else:
            query = query.is_('mes', 'null')
        
        existing_response = query.execute()
        
        if existing_response.data:
            # Atualizar meta existente
            meta_id = existing_response.data[0]['id']
            update_data = {
                'meta': meta,
                'tipo': tipo
            }
            # Only include mes in update if it was provided
            if mes is not None:
                update_data['mes'] = mes
            
            update_response = supabase_admin.table('fin_metas_financeiras').update(update_data).eq('id', meta_id).execute()
            return jsonify(update_response.data[0])
        else:
            # Criar nova meta
            create_data = {
                'ano': str(ano),
                'meta': meta,
                'tipo': tipo
            }
            # Only include mes in creation if it was provided
            if mes is not None:
                create_data['mes'] = mes
                
            create_response = supabase_admin.table('fin_metas_financeiras').insert(create_data).execute()
            return jsonify(create_response.data[0])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@faturamento_bp.route('/api/metas/<int:meta_id>', methods=['DELETE'])
@login_required
@perfil_required('financeiro', 'faturamento')
def api_delete_meta(meta_id):
    """API para excluir uma meta financeira"""
    try:
        response = supabase_admin.table('fin_metas_financeiras').delete().eq('id', meta_id).execute()
        return jsonify({'message': 'Meta excluída com sucesso'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
