"""
Rotas - Dashboard Executivo RH
Endpoints para visualização de indicadores executivos de RH

Dashboard Executivo (Visão da Diretoria):
- 5 KPIs Principais: Headcount, Turnover, Tempo Médio Contratação, Vagas Abertas, Custo Total
- 4 Gráficos: Evolução Headcount, Admissões vs Desligamentos, Turnover por Departamento, Vagas Abertas por Mais Tempo
"""

from flask import render_template, jsonify, request
from modules.auth.routes import login_required
from decorators.perfil_decorators import perfil_required
from . import dashboard_rh_bp
from extensions import supabase_admin as supabase
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from collections import defaultdict
import os

# ========================================
# PÁGINAS HTML
# ========================================

@dashboard_rh_bp.route('/')
@login_required
@perfil_required('rh', 'dashboard')
def dashboard_executivo():
    """
    Página principal do Dashboard Executivo de RH
    Exibe indicadores e métricas consolidadas
    """
    try:
        # Carregar departamentos para o filtro
        response_deps = supabase.table('rh_departamentos').select('id, nome_departamento').order('nome_departamento').execute()
        departamentos = response_deps.data if response_deps.data else []
        
        dados_dashboard = {
            'data_atualizacao': datetime.now().strftime('%d/%m/%Y %H:%M'),
            'departamentos': departamentos
        }
        
        return render_template(
            'dashboard/dashboard_executivo.html',
            dados=dados_dashboard
        )
        
    except Exception as e:
        print(f"❌ Erro ao carregar dashboard executivo: {str(e)}")
        return render_template(
            'dashboard/dashboard_executivo.html',
            error=str(e)
        ), 500


# ========================================
# APIs REST
# ========================================

@dashboard_rh_bp.route('/api/dados', methods=['GET'])
@login_required
@perfil_required('rh', 'dashboard')
def api_dados_dashboard():
    """
    API: Retorna dados consolidados do dashboard
    Query Params:
        - periodo_inicio: data início (YYYY-MM-DD)
        - periodo_fim: data fim (YYYY-MM-DD)
        - departamentos: array de IDs de departamentos (opcional)
    """
    try:
        # Obter parâmetros de filtro
        periodo_inicio = request.args.get('periodo_inicio')
        periodo_fim = request.args.get('periodo_fim')
        departamentos_ids = request.args.getlist('departamentos[]')
        
        # Definir período padrão se não fornecido (Este Ano)
        if not periodo_inicio or not periodo_fim:
            hoje = datetime.now()
            periodo_inicio = f"{hoje.year}-01-01"
            periodo_fim = hoje.strftime('%Y-%m-%d')
        
        print(f"\n📊 ========== DASHBOARD EXECUTIVO RH ==========")
        print(f"📊 Período: {periodo_inicio} a {periodo_fim}")
        print(f"📊 Departamentos filtrados: {departamentos_ids if departamentos_ids else 'Todos'}")
        print(f"📊 Tipo de departamentos_ids: {type(departamentos_ids)}")
        print(f"📊 Departamentos IDs (detalhado): {repr(departamentos_ids)}")
        
        # Calcular KPIs
        kpis = calcular_kpis(periodo_inicio, periodo_fim, departamentos_ids)
        
        # Calcular dados para gráficos
        graficos = calcular_graficos(periodo_inicio, periodo_fim, departamentos_ids)
        
        # Calcular dados para tabelas
        tabelas = calcular_tabelas(periodo_inicio, periodo_fim, departamentos_ids)
        
        print(f"✅ Dashboard calculado com sucesso!")
        print(f"========================================\n")
        
        return jsonify({
            'success': True,
            'data': {
                'periodo': {
                    'inicio': periodo_inicio,
                    'fim': periodo_fim
                },
                'kpis': kpis,
                'graficos': graficos,
                'tabelas': tabelas,
                'timestamp': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        print(f"❌ Erro na API de dados do dashboard: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@dashboard_rh_bp.route('/api/refresh', methods=['POST'])
@login_required
@perfil_required('rh', 'dashboard')
def api_refresh_dados():
    """
    API: Força atualização dos dados do dashboard
    """
    try:
        return jsonify({
            'success': True,
            'message': 'Dados atualizados com sucesso',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"❌ Erro ao atualizar dados: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@dashboard_rh_bp.route('/api/debug/departamentos', methods=['GET'])
def api_debug_departamentos():
    """
    API DEBUG: Lista todos os departamentos com IDs
    TEMPORÁRIO - Para debug de filtros
    """
    try:
        # Verificar chave de bypass
        api_bypass_key = os.getenv('API_BYPASS_KEY')
        if request.headers.get('X-API-Key') != api_bypass_key:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        
        response = supabase.table('rh_departamentos')\
            .select('id, nome_departamento')\
            .order('nome_departamento')\
            .execute()
        
        departamentos = response.data if response.data else []
        
        return jsonify({
            'success': True,
            'data': departamentos
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ========================================
# FUNÇÕES DE CÁLCULO - KPIs
# ========================================

def calcular_kpis(periodo_inicio, periodo_fim, departamentos_ids=None):
    """
    Calcula os 10 KPIs principais do Dashboard Executivo
    
    KPIs:
    1. Headcount - Total de colaboradores ativos
    2. Turnover - Taxa de rotatividade (%)
    3. Tempo Médio Contratação - Dias para fechar vagas
    4. Vagas Abertas - Total de vagas em aberto
    5. Custo Salários - Soma dos salários mensais (folha pura)
    6. Custo Benefícios - Soma dos benefícios mensais
    7. Custo Total - Salários + Benefícios
    8. Média Candidatos - Média de candidatos por vaga
    9. Tempo Médio de Casa - Tempo médio de permanência
    10. Idade Média - Idade média dos colaboradores
    """
    print("\n🚀 Calculando KPIs do Dashboard Executivo...")
    if departamentos_ids:
        print(f"   🔍 Filtrando KPIs por departamentos: {departamentos_ids}")
    
    kpis = {}
    
    # KPI 1: Headcount (Colaboradores Ativos) - COM FILTRO
    kpis['headcount'] = calcular_kpi_headcount(departamentos_ids)
    
    # KPI 2: Turnover (Taxa de Rotatividade) - COM FILTRO
    kpis['turnover'] = calcular_kpi_turnover(periodo_inicio, periodo_fim, kpis['headcount']['valor'], departamentos_ids)
    
    # KPI 3: Tempo Médio de Contratação
    kpis['tempo_contratacao'] = calcular_kpi_tempo_contratacao(periodo_inicio, periodo_fim)
    
    # KPI 4: Vagas Abertas
    kpis['vagas_abertas'] = calcular_kpi_vagas_abertas()
    
    # KPI 5, 6, 7: Custos (Salários, Benefícios e Total) - COM FILTRO
    custos = calcular_kpi_custo_total(departamentos_ids)
    kpis['custo_salarios'] = {
        'valor': custos['custo_salarios'],
        'variacao': 0,
        'label': 'Custo Salários (Folha)',
        'icone': 'mdi-currency-usd',
        'cor': '#28a745'
    }
    kpis['custo_beneficios'] = {
        'valor': custos['custo_beneficios'],
        'variacao': 0,
        'label': 'Custo Benefícios',
        'icone': 'mdi-gift',
        'cor': '#17a2b8'
    }
    kpis['custo_total'] = {
        'valor': custos['custo_total'],
        'variacao': 0,
        'label': 'Custo Total (Pessoal)',
        'icone': 'mdi-cash-multiple',
        'cor': '#fd7e14'
    }
    
    # KPI 8: Média de Candidatos por Vaga
    kpis['media_candidatos'] = calcular_kpi_media_candidatos()
    
    # KPI 9: Tempo Médio de Casa
    kpis['tempo_medio_casa'] = calcular_kpi_tempo_medio_casa()
    
    # KPI 10: Idade Média
    kpis['idade_media'] = calcular_kpi_idade_media()
    
    # KPI 11: Total de Admissões no Período - COM FILTRO
    kpis['total_admissoes'] = calcular_kpi_total_admissoes(periodo_inicio, periodo_fim, departamentos_ids)
    
    # KPI 12: Total de Demissões no Período - COM FILTRO
    kpis['total_demissoes'] = calcular_kpi_total_demissoes(periodo_inicio, periodo_fim, departamentos_ids)
    
    print("✅ KPIs calculados com sucesso!\n")
    return kpis


def calcular_kpi_headcount(departamentos_ids=None):
    """
    KPI 1: Headcount - Total de Colaboradores Ativos
    
    Lógica:
    - COUNT(*) da view vw_colaboradores_atual (já filtra apenas ativos)
    - Se departamentos_ids fornecido, filtrar por esses departamentos
    """
    try:
        print(f"   🔍 Calculando Headcount...")
        print(f"   🔍 Departamentos IDs recebidos: {departamentos_ids}")
        print(f"   🔍 Tipo: {type(departamentos_ids)}")
        
        # CORREÇÃO: Usar view vw_colaboradores_atual em vez de rh_colaboradores
        # A view já tem o join com histórico e traz departamento_id
        # NOTA: A view usa 'id' e não 'colaborador_id'
        query = supabase.table('vw_colaboradores_atual')\
            .select('id', count='exact')
        
        # Aplicar filtro de departamento se fornecido
        if departamentos_ids:
            print(f"   🔍 Aplicando filtro .in_('departamento_id', {departamentos_ids})")
            query = query.in_('departamento_id', departamentos_ids)
        
        response = query.execute()
        
        print(f"   🔍 Response count: {response.count}")
        print(f"   🔍 Response data length: {len(response.data) if response.data else 0}")
        
        headcount = response.count if response.count is not None else 0
        
        if departamentos_ids:
            print(f"   ✅ Headcount (filtrado): {headcount}")
        else:
            print(f"   ✅ Headcount: {headcount}")
        
        return {
            'valor': headcount,
            'variacao': 0,
            'label': 'Colaboradores Ativos',
            'icone': 'mdi-account-group',
            'cor': '#6f42c1'
        }
    except Exception as e:
        print(f"   ❌ Erro ao calcular headcount: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'valor': 0,
            'variacao': 0,
            'label': 'Colaboradores Ativos',
            'icone': 'mdi-account-group',
            'cor': '#6f42c1'
        }


def calcular_kpi_turnover(periodo_inicio, periodo_fim, headcount_atual, departamentos_ids=None):
    """
    KPI 2: Turnover - Taxa de Rotatividade (%)
    
    Fórmula:
    - Turnover (%) = (Desligamentos no Período / Headcount Médio) × 100
    
    Lógica:
    - Buscar desligamentos do histórico no período
    - Se departamentos_ids fornecido, filtrar por esses departamentos
    """
    try:
        # Contar desligamentos no período usando histórico
        query_demissoes = supabase.table('rh_historico_colaborador')\
            .select('id', count='exact')\
            .eq('tipo_evento', 'Demissão')\
            .gte('data_evento', periodo_inicio)\
            .lte('data_evento', periodo_fim)
        
        # Aplicar filtro de departamento se fornecido
        if departamentos_ids:
            query_demissoes = query_demissoes.in_('departamento_id', departamentos_ids)
        
        response_demissoes = query_demissoes.execute()
        
        desligamentos = response_demissoes.count if response_demissoes.count is not None else 0
        
        # Calcular turnover (usar headcount atual como aproximação do médio)
        if headcount_atual == 0:
            turnover_taxa = 0
        else:
            turnover_taxa = (desligamentos / headcount_atual) * 100
        
        print(f"   ✅ Turnover: {turnover_taxa:.1f}% ({desligamentos} desligamentos / {headcount_atual} headcount)")
        
        return {
            'valor': round(turnover_taxa, 1),
            'variacao': 0,
            'label': 'Taxa de Rotatividade',
            'icone': 'mdi-account-arrow-right',
            'cor': '#dc3545' if turnover_taxa > 10 else '#28a745'
        }
    except Exception as e:
        print(f"   ❌ Erro ao calcular turnover: {str(e)}")
        return {
            'valor': 0,
            'variacao': 0,
            'label': 'Taxa de Rotatividade',
            'icone': 'mdi-account-arrow-right',
            'cor': '#28a745'
        }


def calcular_kpi_tempo_contratacao(periodo_inicio, periodo_fim):
    """
    KPI 3: Tempo Médio de Contratação (Dias)
    
    Fórmula:
    - AVG(data_fechamento - data_abertura) para vagas fechadas no período
    """
    try:
        # Buscar vagas fechadas no período
        response_vagas = supabase.table('rh_vagas')\
            .select('data_abertura, data_fechamento')\
            .eq('status', 'Fechada')\
            .not_.is_('data_fechamento', 'null')\
            .gte('data_fechamento', periodo_inicio)\
            .lte('data_fechamento', periodo_fim)\
            .execute()
        
        vagas = response_vagas.data if response_vagas.data else []
        
        if not vagas:
            print(f"   ⚠️  Tempo Contratação: Nenhuma vaga fechada no período")
            return {
                'valor': 0,
                'variacao': 0,
                'label': 'Tempo Médio Contratação (dias)',
                'icone': 'mdi-clock-outline',
                'cor': '#17a2b8'
            }
        
        # Calcular diferença em dias
        total_dias = 0
        count_vagas = 0
        
        for vaga in vagas:
            if vaga.get('data_abertura') and vaga.get('data_fechamento'):
                try:
                    data_abertura = datetime.strptime(vaga['data_abertura'][:10], '%Y-%m-%d')
                    data_fechamento = datetime.strptime(vaga['data_fechamento'][:10], '%Y-%m-%d')
                    dias = (data_fechamento - data_abertura).days
                    if dias >= 0:
                        total_dias += dias
                        count_vagas += 1
                except:
                    continue
        
        tempo_medio = round(total_dias / count_vagas) if count_vagas > 0 else 0
        
        print(f"   ✅ Tempo Médio Contratação: {tempo_medio} dias ({count_vagas} vagas fechadas)")
        
        return {
            'valor': tempo_medio,
            'variacao': 0,
            'label': 'Tempo Médio Contratação (dias)',
            'icone': 'mdi-clock-outline',
            'cor': '#ffc107' if tempo_medio > 30 else '#28a745'
        }
    except Exception as e:
        print(f"   ❌ Erro ao calcular tempo de contratação: {str(e)}")
        return {
            'valor': 0,
            'variacao': 0,
            'label': 'Tempo Médio Contratação (dias)',
            'icone': 'mdi-clock-outline',
            'cor': '#17a2b8'
        }


def calcular_kpi_vagas_abertas():
    """
    KPI 4: Vagas Abertas - Total de Posições em Aberto
    """
    try:
        response = supabase.table('rh_vagas')\
            .select('id', count='exact')\
            .eq('status', 'Aberta')\
            .execute()
        
        vagas_abertas = response.count if response.count is not None else 0
        
        print(f"   ✅ Vagas Abertas: {vagas_abertas}")
        
        return {
            'valor': vagas_abertas,
            'variacao': 0,
            'label': 'Vagas em Aberto',
            'icone': 'mdi-briefcase-outline',
            'cor': '#6f42c1'
        }
    except Exception as e:
        print(f"   ❌ Erro ao calcular vagas abertas: {str(e)}")
        return {
            'valor': 0,
            'variacao': 0,
            'label': 'Vagas em Aberto',
            'icone': 'mdi-briefcase-outline',
            'cor': '#6f42c1'
        }


def calcular_kpi_media_candidatos():
    """
    KPI 6: Média de Candidatos por Vaga
    
    Fórmula:
    - Total de candidatos / Total de vagas com candidatos
    - Considera apenas vagas que receberam candidaturas
    """
    try:
        print(f"   🔍 Calculando média de candidatos por vaga")
        
        # Buscar total de candidatos
        response_candidatos = supabase.table('rh_candidatos')\
            .select('id, vaga_id', count='exact')\
            .execute()
        
        total_candidatos = response_candidatos.count if response_candidatos.count is not None else 0
        candidatos_data = response_candidatos.data if response_candidatos.data else []
        
        print(f"   📊 Total de candidatos: {total_candidatos}")
        
        # Contar vagas únicas que receberam candidaturas
        vagas_com_candidatos = set()
        for candidato in candidatos_data:
            if candidato.get('vaga_id'):
                vagas_com_candidatos.add(candidato['vaga_id'])
        
        total_vagas = len(vagas_com_candidatos)
        print(f"   📊 Total de vagas com candidatos: {total_vagas}")
        
        # Calcular média
        if total_vagas > 0:
            media = round(total_candidatos / total_vagas, 1)
        else:
            print(f"   ⚠️  Média Candidatos: Nenhuma vaga com candidatos encontrada")
            media = 0
        
        print(f"   ✅ Média de Candidatos por Vaga: {media}")
        
        return {
            'valor': media,
            'variacao': 0,
            'label': 'Média Candidatos/Vaga',
            'icone': 'mdi-account-multiple-outline',
            'cor': '#20c997' if media >= 5 else '#ffc107'
        }
    except Exception as e:
        print(f"   ❌ Erro ao calcular média de candidatos: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'valor': 0,
            'variacao': 0,
            'label': 'Média Candidatos/Vaga',
            'icone': 'mdi-account-multiple-outline',
            'cor': '#17a2b8'
        }


def calcular_kpi_tempo_medio_casa():
    """
    KPI 7: Tempo Médio de Casa (Anos)
    
    Fórmula:
    - Para cada colaborador ativo, calcular: data_atual - data_admissao
    - Retornar a média em anos
    """
    try:
        print(f"   🔍 Calculando tempo médio de casa")
        
        # Buscar colaboradores ativos com data de admissão
        response = supabase.table('rh_colaboradores')\
            .select('id, data_admissao')\
            .eq('status', 'Ativo')\
            .is_('data_desligamento', 'null')\
            .not_.is_('data_admissao', 'null')\
            .execute()
        
        colaboradores = response.data if response.data else []
        print(f"   📊 Total de colaboradores ativos com data de admissão: {len(colaboradores)}")
        
        if not colaboradores:
            print(f"   ⚠️  Tempo Médio de Casa: Nenhum colaborador ativo encontrado")
            return {
                'valor': 0,
                'variacao': 0,
                'label': 'Tempo Médio de Casa',
                'icone': 'mdi-history',
                'cor': '#6f42c1',
                'unidade': 'anos'
            }
        
        # Calcular tempo de casa para cada colaborador
        hoje = datetime.now()
        tempos_casa = []
        
        for colab in colaboradores:
            data_admissao_str = colab.get('data_admissao')
            if data_admissao_str:
                try:
                    data_admissao = datetime.strptime(data_admissao_str[:10], '%Y-%m-%d')
                    tempo_dias = (hoje - data_admissao).days
                    tempo_anos = tempo_dias / 365.25  # Considera anos bissextos
                    tempos_casa.append(tempo_anos)
                except Exception as ex:
                    print(f"      ⚠️ Erro ao processar data de admissão: {data_admissao_str} - {str(ex)}")
                    continue
        
        if not tempos_casa:
            print(f"   ⚠️  Tempo Médio de Casa: Nenhuma data válida processada")
            tempo_medio = 0
        else:
            tempo_medio = round(sum(tempos_casa) / len(tempos_casa), 1)
        
        print(f"   ✅ Tempo Médio de Casa: {tempo_medio} anos ({len(tempos_casa)} colaboradores processados)")
        
        return {
            'valor': tempo_medio,
            'variacao': 0,
            'label': 'Tempo Médio de Casa',
            'icone': 'mdi-history',
            'cor': '#6f42c1',
            'unidade': 'anos'
        }
    except Exception as e:
        print(f"   ❌ Erro ao calcular tempo médio de casa: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'valor': 0,
            'variacao': 0,
            'label': 'Tempo Médio de Casa',
            'icone': 'mdi-history',
            'cor': '#6f42c1',
            'unidade': 'anos'
        }


def calcular_kpi_idade_media():
    """
    KPI 8: Idade Média dos Colaboradores (Anos)
    
    Fórmula:
    - Para cada colaborador ativo, calcular: data_atual - data_nascimento
    - Retornar a média em anos
    """
    try:
        print(f"   🔍 Calculando idade média dos colaboradores")
        
        # Buscar colaboradores ativos com data de nascimento
        response = supabase.table('rh_colaboradores')\
            .select('id, data_nascimento')\
            .eq('status', 'Ativo')\
            .is_('data_desligamento', 'null')\
            .not_.is_('data_nascimento', 'null')\
            .execute()
        
        colaboradores = response.data if response.data else []
        print(f"   📊 Total de colaboradores ativos com data de nascimento: {len(colaboradores)}")
        
        if not colaboradores:
            print(f"   ⚠️  Idade Média: Nenhum colaborador ativo encontrado")
            return {
                'valor': 0,
                'variacao': 0,
                'label': 'Idade Média',
                'icone': 'mdi-cake-variant',
                'cor': '#6f42c1',
                'unidade': 'anos'
            }
        
        # Calcular idade para cada colaborador
        hoje = datetime.now()
        idades = []
        
        for colab in colaboradores:
            data_nascimento_str = colab.get('data_nascimento')
            if data_nascimento_str:
                try:
                    data_nascimento = datetime.strptime(data_nascimento_str[:10], '%Y-%m-%d')
                    idade_dias = (hoje - data_nascimento).days
                    idade_anos = idade_dias / 365.25  # Considera anos bissextos
                    
                    # Validar idade razoável (entre 18 e 80 anos)
                    if 18 <= idade_anos <= 80:
                        idades.append(idade_anos)
                    else:
                        print(f"      ⚠️ Idade fora do range válido ignorada: {idade_anos:.1f} anos")
                except Exception as ex:
                    print(f"      ⚠️ Erro ao processar data de nascimento: {data_nascimento_str} - {str(ex)}")
                    continue
        
        if not idades:
            print(f"   ⚠️  Idade Média: Nenhuma data válida processada")
            idade_media = 0
        else:
            idade_media = round(sum(idades) / len(idades))
        
        print(f"   ✅ Idade Média: {idade_media} anos ({len(idades)} colaboradores processados)")
        
        return {
            'valor': idade_media,
            'variacao': 0,
            'label': 'Idade Média',
            'icone': 'mdi-cake-variant',
            'cor': '#6f42c1',
            'unidade': 'anos'
        }
    except Exception as e:
        print(f"   ❌ Erro ao calcular idade média: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'valor': 0,
            'variacao': 0,
            'label': 'Idade Média',
            'icone': 'mdi-cake-variant',
            'cor': '#6f42c1',
            'unidade': 'anos'
        }


def calcular_kpi_total_admissoes(periodo_inicio, periodo_fim, departamentos_ids=None):
    """
    KPI 11: Total de Admissões no Período
    
    Lógica:
    - Conta eventos de 'Admissão' no histórico dentro do período
    - Aplica filtro de departamento se fornecido
    """
    try:
        print(f"   🔍 Calculando total de admissões no período {periodo_inicio} a {periodo_fim}")
        if departamentos_ids:
            print(f"   🔍 Filtrando por departamentos: {departamentos_ids}")
        
        # Buscar admissões do histórico
        query = supabase.table('rh_historico_colaborador')\
            .select('id', count='exact')\
            .eq('tipo_evento', 'Admissão')\
            .gte('data_evento', periodo_inicio)\
            .lte('data_evento', periodo_fim)
        
        # Aplicar filtro de departamento se fornecido
        if departamentos_ids:
            query = query.in_('departamento_id', departamentos_ids)
        
        response = query.execute()
        total_admissoes = response.count if response.count is not None else 0
        
        print(f"   ✅ Total de Admissões: {total_admissoes}")
        
        return {
            'valor': total_admissoes,
            'variacao': 0,
            'label': 'Admissões no Período',
            'icone': 'mdi-account-plus',
            'cor': '#28a745'
        }
    except Exception as e:
        print(f"   ❌ Erro ao calcular total de admissões: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'valor': 0,
            'variacao': 0,
            'label': 'Admissões no Período',
            'icone': 'mdi-account-plus',
            'cor': '#28a745'
        }


def calcular_kpi_total_demissoes(periodo_inicio, periodo_fim, departamentos_ids=None):
    """
    KPI 12: Total de Demissões no Período
    
    Lógica:
    - Conta eventos de 'Demissão' no histórico dentro do período
    - Aplica filtro de departamento se fornecido
    """
    try:
        print(f"   🔍 Calculando total de demissões no período {periodo_inicio} a {periodo_fim}")
        if departamentos_ids:
            print(f"   🔍 Filtrando por departamentos: {departamentos_ids}")
        
        # Buscar demissões do histórico
        query = supabase.table('rh_historico_colaborador')\
            .select('id', count='exact')\
            .eq('tipo_evento', 'Demissão')\
            .gte('data_evento', periodo_inicio)\
            .lte('data_evento', periodo_fim)
        
        # Aplicar filtro de departamento se fornecido
        if departamentos_ids:
            query = query.in_('departamento_id', departamentos_ids)
        
        response = query.execute()
        total_demissoes = response.count if response.count is not None else 0
        
        print(f"   ✅ Total de Demissões: {total_demissoes}")
        
        return {
            'valor': total_demissoes,
            'variacao': 0,
            'label': 'Demissões no Período',
            'icone': 'mdi-account-minus',
            'cor': '#dc3545'
        }
    except Exception as e:
        print(f"   ❌ Erro ao calcular total de demissões: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'valor': 0,
            'variacao': 0,
            'label': 'Demissões no Período',
            'icone': 'mdi-account-minus',
            'cor': '#dc3545'
        }


def calcular_kpi_custo_total(departamentos_ids=None):
    """
    KPI 5, 6, 7: Custos de Pessoal (Salários, Benefícios e Total)
    
    Retorna 3 valores separados:
    - custo_salarios: Soma dos salários mensais
    - custo_beneficios: Soma de todos os benefícios (calculados pela view)
    - custo_total: Salários + Benefícios
    
    Lógica:
    - Usa a view vw_colaboradores_atual que já tem total_beneficios calculado
    - View já traz último salário e benefícios de cada colaborador ativo
    - Se departamentos_ids fornecido, filtrar por esses departamentos
    """
    try:
        print(f"   🔍 Buscando custos da view vw_colaboradores_atual...")
        
        # 🔥 OTIMIZAÇÃO: Usar view que já calcula tudo
        query = supabase.table('vw_colaboradores_atual')\
            .select('salario_mensal, total_beneficios')
        
        # Aplicar filtro de departamento se fornecido
        if departamentos_ids:
            query = query.in_('departamento_id', departamentos_ids)
        
        response = query.execute()
        
        colaboradores = response.data if response.data else []
        
        print(f"   📊 Total de colaboradores ativos: {len(colaboradores)}")
        
        if not colaboradores:
            print(f"   ⚠️  Custos: Nenhum colaborador ativo encontrado")
            return {
                'custo_salarios': 0,
                'custo_beneficios': 0,
                'custo_total': 0
            }
        
        # Calcular custos separados
        custo_salarios = 0.0
        custo_beneficios = 0.0
        
        colaboradores_com_salario = 0
        colaboradores_com_beneficios = 0
        
        # DEBUG: Mostrar amostra dos primeiros 3 registros
        for idx, colab in enumerate(colaboradores[:3]):
            print(f"      Colaborador {idx+1}: salario={colab.get('salario_mensal')}, beneficios={colab.get('total_beneficios')}")
        
        for colab in colaboradores:
            # Processar salário
            salario_mensal = colab.get('salario_mensal')
            if salario_mensal:
                try:
                    valor_salario = float(salario_mensal)
                    custo_salarios += valor_salario
                    colaboradores_com_salario += 1
                except (ValueError, TypeError) as e:
                    print(f"      ⚠️ Erro ao converter salário: {salario_mensal}")
            
            # Processar benefícios (já calculados pela view)
            total_beneficios = colab.get('total_beneficios')
            if total_beneficios:
                try:
                    valor_beneficios = float(total_beneficios)
                    if valor_beneficios > 0:
                        custo_beneficios += valor_beneficios
                        colaboradores_com_beneficios += 1
                except (ValueError, TypeError) as e:
                    print(f"      ⚠️ Erro ao converter benefícios: {total_beneficios}")
        
        custo_total = custo_salarios + custo_beneficios
        
        print(f"   ✅ Custo Salários: R$ {custo_salarios:,.2f} ({colaboradores_com_salario} colaboradores)")
        print(f"   ✅ Custo Benefícios: R$ {custo_beneficios:,.2f} ({colaboradores_com_beneficios} colaboradores)")
        print(f"   ✅ Custo Total: R$ {custo_total:,.2f}")
        
        if custo_salarios == 0 and len(colaboradores) > 0:
            print(f"   ⚠️  ATENÇÃO: Nenhum salário encontrado! Verifique se os dados estão corretos.")
        
        return {
            'custo_salarios': custo_salarios,
            'custo_beneficios': custo_beneficios,
            'custo_total': custo_total
        }
    except Exception as e:
        print(f"   ❌ Erro ao calcular custos: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'custo_salarios': 0,
            'custo_beneficios': 0,
            'custo_total': 0
        }


# ========================================
# FUNÇÕES DE CÁLCULO - GRÁFICOS
# ========================================

def calcular_graficos(periodo_inicio, periodo_fim, departamentos_ids=None):
    """
    Calcula os gráficos principais do Dashboard Executivo
    
    Gráficos:
    1. Evolução do Headcount (Linha - 12 meses)
    2. Admissões vs Desligamentos (Barras agrupadas)
    3. Turnover por Departamento (Barras - Top 5)
    4. Distribuição por Departamento (Pizza)
    
    Args:
        departamentos_ids: Lista de IDs de departamentos para filtrar (opcional)
    """
    print("🚀 Calculando Gráficos do Dashboard Executivo...")
    if departamentos_ids:
        print(f"   🔍 Filtrando por departamentos: {departamentos_ids}")
    
    graficos = {}
    
    # Gráfico 1 e 2: Evolução e Admissões/Desligamentos (usam mesmos dados) - ✅ FILTRO IMPLEMENTADO
    dados_evolucao = calcular_grafico_evolucao_headcount(periodo_inicio, periodo_fim, departamentos_ids)
    graficos['evolucao_headcount'] = dados_evolucao
    graficos['admissoes_desligamentos'] = {
        'labels': dados_evolucao['labels'],
        'datasets': {
            'admissoes': dados_evolucao['datasets']['admissoes'],
            'desligamentos': dados_evolucao['datasets']['desligamentos']
        }
    }
    
    # Gráfico 3: Turnover por Departamento (Top 5)
    # TODO: Implementar filtro de departamentos para turnover
    graficos['turnover_departamento'] = calcular_grafico_turnover_departamento(periodo_inicio, periodo_fim)
    
    # Gráfico 4: Custo Total por Departamento (substituindo distribuição) - ✅ FILTRO IMPLEMENTADO
    graficos['custo_departamento'] = calcular_grafico_custo_departamento(departamentos_ids)
    
    # Gráfico 5: Distribuição por Departamento - ✅ FILTRO IMPLEMENTADO
    graficos['distribuicao_departamento'] = calcular_grafico_distribuicao_departamento(departamentos_ids)
    
    print("✅ Gráficos calculados com sucesso!\n")
    return graficos


def calcular_grafico_evolucao_headcount(periodo_inicio, periodo_fim, departamentos_ids=None):
    """
    Gráfico 1: Evolução do Headcount (Linha - 12 meses)
    
    Datasets:
    - Headcount no final de cada mês
    - Admissões no mês
    - Desligamentos no mês
    
    Otimização:
    - Buscar TODOS os eventos do período de uma vez
    - Agrupar em Python (O(n) ao invés de 24 queries)
    - Se departamentos_ids fornecido, filtrar por esses departamentos
    """
    try:
        print(f"   🔍 Calculando evolução de headcount para período {periodo_inicio} a {periodo_fim}")
        if departamentos_ids:
            print(f"   🔍 Filtrando evolução por departamentos: {departamentos_ids}")
        
        # Gerar lista de meses no período
        data_inicio = datetime.strptime(periodo_inicio, '%Y-%m-%d')
        data_fim = datetime.strptime(periodo_fim, '%Y-%m-%d')
        
        meses = []
        current = data_inicio.replace(day=1)
        while current <= data_fim:
            meses.append(current.strftime('%Y-%m'))
            current += relativedelta(months=1)
        
        print(f"   📊 Total de meses a processar: {len(meses)}")
        
        # 🔥 CORREÇÃO: Buscar admissões do histórico (tem departamento_id)
        query_admissoes = supabase.table('rh_historico_colaborador')\
            .select('data_evento')\
            .eq('tipo_evento', 'Admissão')\
            .gte('data_evento', periodo_inicio)\
            .lte('data_evento', periodo_fim)
        
        # Aplicar filtro de departamento se fornecido
        if departamentos_ids:
            query_admissoes = query_admissoes.in_('departamento_id', departamentos_ids)
        
        response_admissoes = query_admissoes.execute()
        
        # 🔥 CORREÇÃO: Buscar desligamentos do histórico (tem departamento_id)
        query_desligamentos = supabase.table('rh_historico_colaborador')\
            .select('data_evento')\
            .eq('tipo_evento', 'Demissão')\
            .gte('data_evento', periodo_inicio)\
            .lte('data_evento', periodo_fim)
        
        # Aplicar filtro de departamento se fornecido
        if departamentos_ids:
            query_desligamentos = query_desligamentos.in_('departamento_id', departamentos_ids)
        
        response_desligamentos = query_desligamentos.execute()
        
        print(f"   📊 Admissões encontradas: {len(response_admissoes.data or [])}")
        print(f"   📊 Desligamentos encontrados: {len(response_desligamentos.data or [])}")
        
        # DEBUG: Mostrar primeiras 3 datas de cada tipo
        if response_admissoes.data:
            print(f"   🔍 Primeiras 3 admissões:")
            for i, adm in enumerate(response_admissoes.data[:3]):
                print(f"      {i+1}. {adm.get('data_evento')}")
        
        if response_desligamentos.data:
            print(f"   🔍 Primeiros 3 desligamentos:")
            for i, desl in enumerate(response_desligamentos.data[:3]):
                print(f"      {i+1}. {desl.get('data_evento')}")
        
        # Agrupar eventos por mês em Python
        admissoes_por_mes = defaultdict(int)
        desligamentos_por_mes = defaultdict(int)
        
        for evento in (response_admissoes.data or []):
            data_evento = evento.get('data_evento')
            if data_evento:
                mes = data_evento[:7]  # YYYY-MM
                admissoes_por_mes[mes] += 1
        
        for evento in (response_desligamentos.data or []):
            data_evento = evento.get('data_evento')
            if data_evento:
                mes = data_evento[:7]  # YYYY-MM
                desligamentos_por_mes[mes] += 1
        
        # Buscar headcount inicial usando view vw_colaboradores_atual
        # Contar colaboradores que estavam ativos no início do período
        # NOTA: A view usa 'id' e não 'colaborador_id'
        query_headcount_inicial = supabase.table('vw_colaboradores_atual')\
            .select('id', count='exact')
        
        # Aplicar filtro de departamento se fornecido
        if departamentos_ids:
            query_headcount_inicial = query_headcount_inicial.in_('departamento_id', departamentos_ids)
        
        response_headcount_inicial = query_headcount_inicial.execute()
        
        headcount_inicial = response_headcount_inicial.count if response_headcount_inicial.count is not None else 0
        print(f"   📊 Headcount inicial (antes de {periodo_inicio}): {headcount_inicial}")
        
        # Montar arrays de dados calculando headcount progressivo
        labels = []
        headcount_data = []
        admissoes_data = []
        desligamentos_data = []
        
        headcount_acumulado = headcount_inicial
        
        # Retornar meses no formato YYYY-MM (JavaScript fará a formatação para legibilidade)
        for mes in meses:
            try:
                admissoes_mes = admissoes_por_mes.get(mes, 0)
                desligamentos_mes = desligamentos_por_mes.get(mes, 0)
                
                # Calcular headcount progressivo: headcount anterior + admissões - desligamentos
                headcount_acumulado = headcount_acumulado + admissoes_mes - desligamentos_mes
                
                labels.append(mes)  # Formato: "2024-10"
                headcount_data.append(headcount_acumulado)
                admissoes_data.append(admissoes_mes)
                desligamentos_data.append(desligamentos_mes)
            except Exception as ex:
                print(f"      ⚠️ Erro ao processar mês {mes}: {str(ex)}")
                continue
        
        print(f"   ✅ Evolução Headcount: {len(labels)} meses processados")
        print(f"      Headcount inicial: {headcount_inicial}")
        print(f"      Headcount final: {headcount_data[-1] if headcount_data else 0}")
        print(f"      Total admissões período: {sum(admissoes_data)}")
        print(f"      Total desligamentos período: {sum(desligamentos_data)}")
        print(f"      Variação líquida: {sum(admissoes_data) - sum(desligamentos_data)}")
        
        # Log detalhado dos primeiros 3 meses
        print(f"      Detalhamento por mês (primeiros 3):")
        for i in range(min(3, len(labels))):
            print(f"         {labels[i]}: Admissões={admissoes_data[i]}, Demissões={desligamentos_data[i]}")
        
        return {
            'labels': labels,
            'datasets': {
                'headcount': headcount_data,
                'admissoes': admissoes_data,
                'desligamentos': desligamentos_data
            }
        }
    except Exception as e:
        print(f"   ❌ Erro ao calcular evolução headcount: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'labels': [],
            'datasets': {
                'headcount': [],
                'admissoes': [],
                'desligamentos': []
            }
        }


def calcular_grafico_turnover_departamento(periodo_inicio, periodo_fim):
    """
    Gráfico 3: Turnover por Departamento (Barras - Top 5)
    
    Lógica:
    - Para cada departamento, calcular turnover (%)
    - Turnover = (Desligamentos / Headcount do Depto) × 100
    - Ordenar por turnover DESC e pegar Top 5
    
    Otimização:
    - Buscar todos os históricos de uma vez
    - Mapear colaborador → departamento em Python
    """
    try:
        print(f"   🔍 Calculando turnover por departamento para período {periodo_inicio} a {periodo_fim}")
        
        # Buscar departamentos
        response_deps = supabase.table('rh_departamentos')\
            .select('id, nome_departamento')\
            .execute()
        
        departamentos = response_deps.data if response_deps.data else []
        print(f"   📊 Total de departamentos encontrados: {len(departamentos)}")
        
        if not departamentos:
            print(f"   ⚠️  Turnover por Departamento: Nenhum departamento encontrado")
            return {'labels': [], 'data': []}
        
        # Buscar colaboradores demitidos no período
        response_demitidos = supabase.table('rh_colaboradores')\
            .select('id')\
            .not_.is_('data_desligamento', 'null')\
            .gte('data_desligamento', periodo_inicio)\
            .lte('data_desligamento', periodo_fim)\
            .execute()
        
        colaboradores_demitidos_ids = [c['id'] for c in (response_demitidos.data or [])]
        print(f"   📊 Colaboradores demitidos no período: {len(colaboradores_demitidos_ids)}")
        
        # 🔥 OTIMIZAÇÃO: Buscar TODOS os históricos de uma vez
        response_hist = supabase.table('rh_historico_colaborador')\
            .select('colaborador_id, departamento_id')\
            .not_.is_('departamento_id', 'null')\
            .order('data_evento', desc=True)\
            .execute()
        
        print(f"   📊 Total de registros no histórico: {len(response_hist.data or [])}")
        
        # Mapear colaborador → departamento (último registro)
        colaborador_dept_map = {}
        for hist in (response_hist.data or []):
            colab_id = hist['colaborador_id']
            if colab_id not in colaborador_dept_map:
                colaborador_dept_map[colab_id] = hist['departamento_id']
        
        print(f"   📊 Colaboradores mapeados para departamentos: {len(colaborador_dept_map)}")
        
        # Contar demissões por departamento
        demissoes_por_dept = defaultdict(int)
        for colab_id in colaboradores_demitidos_ids:
            dept_id = colaborador_dept_map.get(colab_id)
            if dept_id:
                demissoes_por_dept[dept_id] += 1
        
        # Contar headcount por departamento
        headcount_por_dept = defaultdict(set)
        for colab_id, dept_id in colaborador_dept_map.items():
            headcount_por_dept[dept_id].add(colab_id)
        
        # Calcular turnover por departamento
        dados_turnover = []
        
        for dept in departamentos:
            dept_id = dept['id']
            dept_nome = dept['nome_departamento']
            
            demissoes = demissoes_por_dept.get(dept_id, 0)
            headcount_dept = len(headcount_por_dept.get(dept_id, set()))
            
            if headcount_dept > 0:
                turnover = (demissoes / headcount_dept) * 100
                dados_turnover.append({
                    'departamento': dept_nome,
                    'turnover': round(turnover, 1),
                    'demissoes': demissoes,
                    'headcount': headcount_dept
                })
        
        # Ordenar por turnover DESC e pegar Top 5
        dados_turnover_sorted = sorted(dados_turnover, key=lambda x: x['turnover'], reverse=True)[:5]
        
        labels = [d['departamento'] for d in dados_turnover_sorted]
        data = [d['turnover'] for d in dados_turnover_sorted]
        
        print(f"   ✅ Turnover por Departamento: Top {len(labels)}")
        print(f"      Departamentos com maior turnover: {labels}")
        print(f"      Valores de turnover (%): {data}")
        for d in dados_turnover_sorted:
            print(f"      {d['departamento']}: {d['turnover']}% ({d['demissoes']}/{d['headcount']})")
        
        return {
            'labels': labels,
            'data': data
        }
    except Exception as e:
        print(f"   ❌ Erro ao calcular turnover por departamento: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'labels': [], 'data': []}


def calcular_grafico_distribuicao_departamento(departamentos_ids=None):
    """
    Gráfico 4: Distribuição de Colaboradores por Departamento (Pizza)
    
    Lógica:
    - Contar colaboradores ativos por departamento
    - Retornar labels (nomes dos departamentos) e data (quantidades)
    
    Args:
        departamentos_ids: Lista de IDs de departamentos para filtrar (opcional)
    """
    try:
        print(f"   🔍 Calculando distribuição por departamento")
        if departamentos_ids:
            print(f"   🔍 Filtrando por departamentos: {departamentos_ids}")
        
        # Buscar departamentos (aplicar filtro se fornecido)
        query_deps = supabase.table('rh_departamentos')\
            .select('id, nome_departamento')
        
        if departamentos_ids:
            query_deps = query_deps.in_('id', departamentos_ids)
        
        response_deps = query_deps.execute()
        
        departamentos = response_deps.data if response_deps.data else []
        print(f"   📊 Total de departamentos: {len(departamentos)}")
        
        if not departamentos:
            print(f"   ⚠️  Distribuição por Departamento: Nenhum departamento encontrado")
            return {'labels': [], 'data': []}
        
        # Buscar histórico de todos os colaboradores ativos
        response_colabs = supabase.table('rh_colaboradores')\
            .select('id')\
            .eq('status', 'Ativo')\
            .is_('data_desligamento', 'null')\
            .execute()
        
        colaboradores_ids = [c['id'] for c in (response_colabs.data or [])]
        print(f"   📊 Total de colaboradores ativos: {len(colaboradores_ids)}")
        
        if not colaboradores_ids:
            print(f"   ⚠️  Distribuição por Departamento: Nenhum colaborador ativo")
            return {'labels': [], 'data': []}
        
        # Buscar último departamento de cada colaborador
        query_hist = supabase.table('rh_historico_colaborador')\
            .select('colaborador_id, departamento_id')\
            .in_('colaborador_id', colaboradores_ids)\
            .not_.is_('departamento_id', 'null')
        
        # Aplicar filtro de departamentos se fornecido
        if departamentos_ids:
            query_hist = query_hist.in_('departamento_id', departamentos_ids)
        
        response_hist = query_hist.order('data_evento', desc=True).execute()
        
        print(f"   📊 Registros no histórico: {len(response_hist.data or [])}")
        
        # Mapear colaborador → departamento (último registro)
        colaborador_dept_map = {}
        for hist in (response_hist.data or []):
            colab_id = hist['colaborador_id']
            if colab_id not in colaborador_dept_map:
                colaborador_dept_map[colab_id] = hist['departamento_id']
        
        # Contar colaboradores por departamento
        dept_counts = defaultdict(int)
        for dept_id in colaborador_dept_map.values():
            dept_counts[dept_id] += 1
        
        # Criar mapa de ID → Nome do departamento
        dept_map = {d['id']: d['nome_departamento'] for d in departamentos}
        
        # Montar dados do gráfico
        labels = []
        data = []
        
        for dept_id, count in dept_counts.items():
            dept_nome = dept_map.get(dept_id, 'Sem Departamento')
            labels.append(dept_nome)
            data.append(count)
        
        # Ordenar por quantidade DESC
        if labels and data:
            combined = sorted(zip(labels, data), key=lambda x: x[1], reverse=True)
            labels, data = zip(*combined)
            labels = list(labels)
            data = list(data)
        
        print(f"   ✅ Distribuição por Departamento: {len(labels)} departamentos")
        print(f"      Departamentos: {labels}")
        print(f"      Quantidades: {data}")
        
        return {
            'labels': labels,
            'data': data
        }
    except Exception as e:
        print(f"   ❌ Erro ao calcular distribuição por departamento: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'labels': [], 'data': []}


def calcular_grafico_custo_departamento(departamentos_ids=None):
    """
    Gráfico 5: Custo Total (Pessoal) por Departamento
    
    Lógica:
    - Para cada departamento, somar: salário_mensal + benefícios (vale_alimentacao + ajuda_de_custo)
    - Retornar labels (nomes dos departamentos) e data (custo total em R$)
    - Ordenar por custo DESC (maior centro de custo primeiro)
    
    Args:
        departamentos_ids: Lista de IDs de departamentos para filtrar (opcional)
    """
    try:
        print(f"   🔍 Calculando custo total por departamento")
        if departamentos_ids:
            print(f"   🔍 Filtrando por departamentos: {departamentos_ids}")
        
        # Buscar departamentos (aplicar filtro se fornecido)
        query_deps = supabase.table('rh_departamentos')\
            .select('id, nome_departamento')
        
        if departamentos_ids:
            query_deps = query_deps.in_('id', departamentos_ids)
        
        response_deps = query_deps.execute()
        
        departamentos = response_deps.data if response_deps.data else []
        print(f"   📊 Total de departamentos: {len(departamentos)}")
        
        if not departamentos:
            print(f"   ⚠️  Custo por Departamento: Nenhum departamento encontrado")
            return {'labels': [], 'data': []}
        
        # Buscar colaboradores ativos
        response_colabs = supabase.table('rh_colaboradores')\
            .select('id')\
            .eq('status', 'Ativo')\
            .is_('data_desligamento', 'null')\
            .execute()
        
        colaboradores_ids = [c['id'] for c in (response_colabs.data or [])]
        print(f"   📊 Total de colaboradores ativos: {len(colaboradores_ids)}")
        
        if not colaboradores_ids:
            print(f"   ⚠️  Custo por Departamento: Nenhum colaborador ativo")
            return {'labels': [], 'data': []}
        
        # Buscar último histórico de cada colaborador (com salário, benefícios e departamento)
        query_hist = supabase.table('rh_historico_colaborador')\
            .select('colaborador_id, departamento_id, salario_mensal, beneficios_jsonb')\
            .in_('colaborador_id', colaboradores_ids)
        
        # Aplicar filtro de departamentos se fornecido
        if departamentos_ids:
            query_hist = query_hist.in_('departamento_id', departamentos_ids)
        
        response_hist = query_hist.order('data_evento', desc=True).execute()
        
        print(f"   📊 Registros no histórico: {len(response_hist.data or [])}")
        
        # Mapear colaborador → último histórico (departamento, salário, benefícios)
        colaborador_info_map = {}
        for hist in (response_hist.data or []):
            colab_id = hist['colaborador_id']
            if colab_id not in colaborador_info_map:
                colaborador_info_map[colab_id] = hist
        
        # Calcular custo total por departamento
        custo_por_dept = defaultdict(float)
        
        for colab_id, info in colaborador_info_map.items():
            dept_id = info.get('departamento_id')
            if not dept_id:
                continue
            
            # Salário mensal
            salario = float(info.get('salario_mensal') or 0)
            
            # Benefícios (vale_alimentacao + ajuda_de_custo)
            beneficios_jsonb = info.get('beneficios_jsonb') or {}
            
            vale_alimentacao = 0
            ajuda_de_custo = 0
            
            if isinstance(beneficios_jsonb, dict):
                # Estrutura: {"beneficios_padrao": {"vale_alimentacao": 635.00}, "remuneracao_adicional": {"ajuda_de_custo": 700.00}}
                beneficios_padrao = beneficios_jsonb.get('beneficios_padrao') or {}
                remuneracao_adicional = beneficios_jsonb.get('remuneracao_adicional') or {}
                
                vale_alimentacao = float(beneficios_padrao.get('vale_alimentacao') or 0)
                ajuda_de_custo = float(remuneracao_adicional.get('ajuda_de_custo') or 0)
            
            custo_total_colaborador = salario + vale_alimentacao + ajuda_de_custo
            custo_por_dept[dept_id] += custo_total_colaborador
        
        # Criar mapa de ID → Nome do departamento
        dept_map = {d['id']: d['nome_departamento'] for d in departamentos}
        
        # Montar dados do gráfico
        labels = []
        data = []
        
        for dept_id, custo_total in custo_por_dept.items():
            dept_nome = dept_map.get(dept_id, 'Sem Departamento')
            labels.append(dept_nome)
            data.append(round(custo_total, 2))
        
        # Ordenar por custo DESC (maior centro de custo primeiro)
        if labels and data:
            combined = sorted(zip(labels, data), key=lambda x: x[1], reverse=True)
            labels, data = zip(*combined)
            labels = list(labels)
            data = list(data)
        
        print(f"   ✅ Custo por Departamento: {len(labels)} departamentos")
        print(f"      Departamentos: {labels}")
        print(f"      Custos (R$): {data}")
        if labels and data:
            print(f"      Maior custo: {labels[0]} - R$ {data[0]:,.2f}")
            print(f"      Custo total geral: R$ {sum(data):,.2f}")
        
        # Recalcular separando salários e benefícios
        salarios_por_dept = defaultdict(float)
        beneficios_por_dept = defaultdict(float)
        
        for colab_id, info in colaborador_info_map.items():
            dept_id = info.get('departamento_id')
            if not dept_id:
                continue
            
            # Salário mensal
            salario = float(info.get('salario_mensal') or 0)
            salarios_por_dept[dept_id] += salario
            
            # Benefícios (vale_alimentacao + ajuda_de_custo)
            beneficios_jsonb = info.get('beneficios_jsonb') or {}
            
            vale_alimentacao = 0
            ajuda_de_custo = 0
            
            if isinstance(beneficios_jsonb, dict):
                beneficios_padrao = beneficios_jsonb.get('beneficios_padrao') or {}
                remuneracao_adicional = beneficios_jsonb.get('remuneracao_adicional') or {}
                
                vale_alimentacao = float(beneficios_padrao.get('vale_alimentacao') or 0)
                ajuda_de_custo = float(remuneracao_adicional.get('ajuda_de_custo') or 0)
            
            beneficios_total = vale_alimentacao + ajuda_de_custo
            beneficios_por_dept[dept_id] += beneficios_total
        
        # Preparar dados separados para salários e benefícios
        salarios_data = []
        beneficios_data = []
        
        for dept_nome in labels:
            # Encontrar o ID do departamento pelo nome
            dept_id = [d['id'] for d in departamentos if d['nome_departamento'] == dept_nome]
            if dept_id:
                dept_id = dept_id[0]
                salarios_data.append(round(salarios_por_dept[dept_id], 2))
                beneficios_data.append(round(beneficios_por_dept[dept_id], 2))
            else:
                salarios_data.append(0)
                beneficios_data.append(0)
        
        print(f"      Salários (R$): {salarios_data}")
        print(f"      Benefícios (R$): {beneficios_data}")
        
        return {
            'labels': labels,
            'data': data,  # Total (mantém compatibilidade)
            'salarios': salarios_data,  # NOVO: Apenas salários
            'beneficios': beneficios_data  # NOVO: Apenas benefícios
        }
    except Exception as e:
        print(f"   ❌ Erro ao calcular custo por departamento: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'labels': [], 'data': []}


# ========================================
# FUNÇÕES DE CÁLCULO - TABELAS
# ========================================

def calcular_tabelas(periodo_inicio, periodo_fim, departamentos_ids=None):
    """
    Calcula dados para tabelas do Dashboard
    
    Tabelas:
    1. Vagas Abertas por Mais Tempo (Top 5)
    """
    print("🚀 Calculando Tabelas do Dashboard Executivo...")
    
    tabelas = {}
    
    # Tabela 1: Vagas Abertas por Mais Tempo
    tabelas['vagas_abertas_mais_tempo'] = calcular_tabela_vagas_abertas_mais_tempo()
    
    print("✅ Tabelas calculadas com sucesso!\n")
    return tabelas


def calcular_tabela_vagas_abertas_mais_tempo():
    """
    Visão Geral das Vagas em Aberto
    
    Colunas:
    - Título da Vaga
    - Cargo
    - Departamento
    - Data Abertura
    - Dias em Aberto
    - Custo Estimado (Salário Base)
    
    Mostra TODAS as vagas abertas (sem filtro de 15 dias)
    """
    try:
        print(f"   🔍 Buscando todas as vagas abertas")
        
        # Buscar TODAS as vagas com status 'Aberta'
        # NOTA: rh_vagas NÃO TEM departamento_id, apenas cargo_id
        # NOTA: rh_vagas NÃO TEM salario_base, tem faixa_salarial_min e faixa_salarial_max
        response_vagas = supabase.table('rh_vagas')\
            .select('id, titulo, data_abertura, cargo_id, localizacao, status, faixa_salarial_min, faixa_salarial_max')\
            .eq('status', 'Aberta')\
            .execute()
        
        todas_vagas = response_vagas.data if response_vagas.data else []
        print(f"   📊 Total de vagas com status 'Aberta': {len(todas_vagas)}")
        
        # Contar quantas têm data_abertura
        vagas_com_data = [v for v in todas_vagas if v.get('data_abertura')]
        vagas_sem_data = [v for v in todas_vagas if not v.get('data_abertura')]
        print(f"   📊 Vagas COM data_abertura: {len(vagas_com_data)}")
        print(f"   ⚠️  Vagas SEM data_abertura: {len(vagas_sem_data)}")
        
        if not todas_vagas:
            print(f"   ⚠️  Nenhuma vaga aberta encontrada")
            return []
        
        # Buscar nomes dos cargos
        cargos_ids = [v['cargo_id'] for v in todas_vagas if v.get('cargo_id')]
        cargos_map = {}
        
        if cargos_ids:
            response_cargos = supabase.table('rh_cargos')\
                .select('id, nome_cargo')\
                .in_('id', cargos_ids)\
                .execute()
            
            for cargo in (response_cargos.data or []):
                cargos_map[cargo['id']] = cargo['nome_cargo']
            
            print(f"   📊 Cargos mapeados: {len(cargos_map)}")
        
        # NOTA: Vagas NÃO têm departamento direto - apenas cargo
        # Se precisar mostrar departamento, deve vir do cargo do colaborador

        
        # Calcular dados de todas as vagas (SEM FILTRO DE 15 DIAS)
        hoje = datetime.now()
        tabela_vagas = []
        
        for vaga in todas_vagas:
            data_abertura_str = vaga.get('data_abertura', '')
            
            # Se não tem data de abertura, pular
            if not data_abertura_str:
                print(f"      ⚠️ Vaga sem data_abertura: {vaga.get('titulo')} (ID: {vaga.get('id')})")
                continue
            
            try:
                data_abertura = datetime.strptime(data_abertura_str[:10], '%Y-%m-%d')
                dias_aberta = (hoje - data_abertura).days
                
                # Determinar status de urgência
                if dias_aberta > 60:
                    status_urgencia = 'alta'
                elif dias_aberta > 30:
                    status_urgencia = 'media'
                else:
                    status_urgencia = 'baixa'
                
                # Calcular custo estimado usando faixa salarial (média entre min e max)
                faixa_min = vaga.get('faixa_salarial_min')
                faixa_max = vaga.get('faixa_salarial_max')
                
                if faixa_min and faixa_max:
                    custo_estimado = (float(faixa_min) + float(faixa_max)) / 2
                elif faixa_min:
                    custo_estimado = float(faixa_min)
                elif faixa_max:
                    custo_estimado = float(faixa_max)
                else:
                    custo_estimado = 0.0
                
                custo_estimado_formatado = f"R$ {custo_estimado:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.') if custo_estimado > 0 else "Não especificado"
                
                tabela_vagas.append({
                    'id': vaga.get('id'),
                    'titulo': vaga.get('titulo', 'Sem título'),
                    'cargo': cargos_map.get(vaga.get('cargo_id'), 'Não especificado'),
                    'departamento': 'N/A',  # Vagas não têm departamento direto
                    'localizacao': vaga.get('localizacao', 'Não especificado'),
                    'data_abertura': data_abertura.strftime('%d/%m/%Y'),
                    'dias_aberto': dias_aberta,
                    'status_urgencia': status_urgencia,
                    'custo_estimado': custo_estimado,
                    'custo_estimado_formatado': custo_estimado_formatado
                })
            except Exception as ex:
                    print(f"      ⚠️ Erro ao processar vaga {vaga.get('id')}: {str(ex)}")
                    continue
        
        # Ordenar por dias_aberto DESC (mostrar TODAS, não apenas top 5)
        tabela_vagas_sorted = sorted(tabela_vagas, key=lambda x: x['dias_aberto'], reverse=True)
        
        print(f"   ✅ Total de vagas processadas: {len(tabela_vagas_sorted)}")
        for v in tabela_vagas_sorted:
            print(f"      {v['titulo']}: {v['dias_aberto']} dias ({v['status_urgencia']}) - {v['custo_estimado_formatado']}")
        
        return tabela_vagas_sorted
        
    except Exception as e:
        print(f"   ❌ Erro ao calcular vagas abertas: {str(e)}")
        import traceback
        traceback.print_exc()
        return []
