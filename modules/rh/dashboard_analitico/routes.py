"""
Rotas - Dashboard AnalÃ­tico RH
Endpoints para anÃ¡lises detalhadas e mÃ©tricas analÃ­ticas de RH

Dashboard AnalÃ­tico (AnÃ¡lises Detalhadas):
- KPIs AnalÃ­ticos
- GrÃ¡ficos Detalhados de AnÃ¡lises
- MÃ©tricas AvanÃ§adas e CorrelaÃ§Ãµes
"""

from flask import render_template, jsonify, request
from modules.auth.routes import login_required
from decorators.perfil_decorators import perfil_required
from . import dashboard_analitico_rh_bp
from extensions import supabase_admin as supabase
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from collections import defaultdict

# ========================================
# PÃGINAS HTML
# ========================================

@dashboard_analitico_rh_bp.route('/')
@login_required
@perfil_required('rh', 'dashboard')
def dashboard_analitico():
    """
    PÃ¡gina principal do Dashboard AnalÃ­tico de RH
    Exibe anÃ¡lises detalhadas e mÃ©tricas analÃ­ticas
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
            'dashboard_analitico/dashboard_analitico_v2.html',
            dados=dados_dashboard
        )
        
    except Exception as e:
        print(f"âŒ Erro ao carregar dashboard analÃ­tico: {str(e)}")
        return render_template(
            'dashboard_analitico/dashboard_analitico_v2.html',
            error=str(e)
        ), 500


# ========================================
# APIs REST - Dashboard AnalÃ­tico v2.0
# ========================================

@dashboard_analitico_rh_bp.route('/api/filtros/departamentos', methods=['GET'])
@login_required
@perfil_required('rh', 'dashboard')
def api_filtros_departamentos():
    """API: Retorna lista de departamentos para filtro"""
    try:
        response = supabase.table('rh_departamentos')\
            .select('id, nome_departamento')\
            .order('nome_departamento')\
            .execute()
        
        return jsonify({
            'success': True,
            'departamentos': response.data if response.data else []
        })
    except Exception as e:
        print(f"âŒ Erro ao carregar departamentos: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@dashboard_analitico_rh_bp.route('/api/filtros/cargos', methods=['GET'])
@login_required
@perfil_required('rh', 'dashboard')
def api_filtros_cargos():
    """API: Retorna lista de cargos para filtro"""
    try:
        response = supabase.table('rh_cargos')\
            .select('id, nome_cargo')\
            .order('nome_cargo')\
            .execute()
        
        return jsonify({
            'success': True,
            'cargos': response.data if response.data else []
        })
    except Exception as e:
        print(f"âŒ Erro ao carregar cargos: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@dashboard_analitico_rh_bp.route('/api/dados', methods=['GET'])
@login_required
@perfil_required('rh', 'dashboard')
def api_dados_dashboard():
    """
    API: Retorna dados consolidados do dashboard analÃ­tico v2.0
    Query Params:
        - periodo_inicio: data inÃ­cio (YYYY-MM-DD)
        - periodo_fim: data fim (YYYY-MM-DD)
        - departamentos[]: array de IDs de departamentos (opcional)
        - cargos[]: array de IDs de cargos (opcional)
        - status: 'todos', 'ativo', 'inativo' (opcional)
    """
    try:
        # Obter parÃ¢metros de filtro
        periodo_inicio = request.args.get('periodo_inicio')
        periodo_fim = request.args.get('periodo_fim')
        departamentos_ids = request.args.getlist('departamentos[]')
        cargos_ids = request.args.getlist('cargos[]')
        status_filter = request.args.get('status', 'todos')
        
        # Definir perÃ­odo padrÃ£o se nÃ£o fornecido (Este Ano)
        if not periodo_inicio or not periodo_fim:
            hoje = datetime.now()
            periodo_inicio = f"{hoje.year}-01-01"
            periodo_fim = hoje.strftime('%Y-%m-%d')
        
        print(f"\nðŸ“Š ========== DASHBOARD ANALÃTICO RH V2.0 ==========")
        print(f"ðŸ“Š PerÃ­odo: {periodo_inicio} a {periodo_fim}")
        print(f"ðŸ“Š Departamentos: {departamentos_ids if departamentos_ids else 'Todos'}")
        print(f"ðŸ“Š Cargos: {cargos_ids if cargos_ids else 'Todos'}")
        print(f"ðŸ“Š Status: {status_filter}")
        
        # SeÃ§Ã£o 1: Recrutamento & SeleÃ§Ã£o
        recrutamento_data = calcular_secao_recrutamento(
            periodo_inicio, periodo_fim, departamentos_ids, cargos_ids
        )
        
        # SeÃ§Ã£o 2: Turnover & RetenÃ§Ã£o
        turnover_data = calcular_secao_turnover(
            periodo_inicio, periodo_fim, departamentos_ids, cargos_ids, status_filter
        )

        # SeÃ§Ã£o 3: AdministraÃ§Ã£o de Pessoal
        administracao_pessoal_data = calcular_secao_administracao_pessoal(
            periodo_inicio, periodo_fim, departamentos_ids, cargos_ids, status_filter
        )

        # SeÃ§Ã£o 4: Compliance & Eventos Operacionais
        compliance_data = calcular_secao_compliance_operacional(
            periodo_inicio, periodo_fim, departamentos_ids, cargos_ids, status_filter
        )
        
        print(f"âœ… Dashboard calculado com sucesso!")
        print(f"================================================\n")
        
        return jsonify({
            'success': True,
            'data': {
                'periodo': {
                    'inicio': periodo_inicio,
                    'fim': periodo_fim
                },
                'recrutamento': recrutamento_data,
                'turnover': turnover_data,
                'administracao_pessoal': administracao_pessoal_data,
                'compliance': compliance_data,
                'timestamp': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        print(f"âŒ Erro na API de dados do dashboard: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ========================================
# APIs REST - Dashboard Executivo (Mantido para compatibilidade)
# ========================================

@dashboard_analitico_rh_bp.route('/api/dados_old', methods=['GET'])
@login_required
@perfil_required('rh', 'dashboard')
def api_dados_dashboard_old():
    """
    API: Retorna dados consolidados do dashboard analÃ­tico (versÃ£o antiga)
    Query Params:
        - periodo_inicio: data inÃ­cio (YYYY-MM-DD)
        - periodo_fim: data fim (YYYY-MM-DD)
        - departamentos: array de IDs de departamentos (opcional)
    """
    try:
        # Obter parÃ¢metros de filtro
        periodo_inicio = request.args.get('periodo_inicio')
        periodo_fim = request.args.get('periodo_fim')
        departamentos_ids = request.args.getlist('departamentos[]')
        
        # Definir perÃ­odo padrÃ£o se nÃ£o fornecido (Este Ano)
        if not periodo_inicio or not periodo_fim:
            hoje = datetime.now()
            periodo_inicio = f"{hoje.year}-01-01"
            periodo_fim = hoje.strftime('%Y-%m-%d')
        
        print(f"\nðŸ“Š ========== DASHBOARD ANALÃTICO RH ==========")
        print(f"ðŸ“Š PerÃ­odo: {periodo_inicio} a {periodo_fim}")
        print(f"ðŸ“Š Departamentos filtrados: {departamentos_ids if departamentos_ids else 'Todos'}")
        
        # Calcular KPIs
        kpis = calcular_kpis(periodo_inicio, periodo_fim, departamentos_ids)
        
        # Calcular dados para grÃ¡ficos
        graficos = calcular_graficos(periodo_inicio, periodo_fim, departamentos_ids)
        
        # Calcular dados para tabelas
        tabelas = calcular_tabelas(periodo_inicio, periodo_fim, departamentos_ids)
        
        print(f"âœ… Dashboard calculado com sucesso!")
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
        print(f"âŒ Erro na API de dados do dashboard: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@dashboard_analitico_rh_bp.route('/api/refresh', methods=['POST'])
@login_required
@perfil_required('rh', 'dashboard')
def api_refresh_dados():
    """
    API: ForÃ§a atualizaÃ§Ã£o dos dados do dashboard analÃ­tico
    """
    try:
        return jsonify({
            'success': True,
            'message': 'Dados atualizados com sucesso',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"âŒ Erro ao atualizar dados: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ========================================
# FUNÃ‡Ã•ES DE CÃLCULO - KPIs
# ========================================

def calcular_kpis(periodo_inicio, periodo_fim, departamentos_ids=None):
    """
    Calcula os 10 KPIs principais do Dashboard Executivo
    
    KPIs:
    1. Headcount - Total de colaboradores ativos
    2. Turnover - Taxa de rotatividade (%)
    3. Tempo MÃ©dio ContrataÃ§Ã£o - Dias para fechar vagas
    4. Vagas Abertas - Total de vagas em aberto
    5. Custo SalÃ¡rios - Soma dos salÃ¡rios mensais (folha pura)
    6. Custo BenefÃ­cios - Soma dos benefÃ­cios mensais
    7. Custo Total - SalÃ¡rios + BenefÃ­cios
    8. MÃ©dia Candidatos - MÃ©dia de candidatos por vaga
    9. Tempo MÃ©dio de Casa - Tempo mÃ©dio de permanÃªncia
    10. Idade MÃ©dia - Idade mÃ©dia dos colaboradores
    """
    print("\nðŸš€ Calculando KPIs do Dashboard Executivo...")
    
    kpis = {}
    
    # KPI 1: Headcount (Colaboradores Ativos)
    kpis['headcount'] = calcular_kpi_headcount()
    
    # KPI 2: Turnover (Taxa de Rotatividade)
    kpis['turnover'] = calcular_kpi_turnover(periodo_inicio, periodo_fim, kpis['headcount']['valor'])
    
    # KPI 3: Tempo MÃ©dio de ContrataÃ§Ã£o
    kpis['tempo_contratacao'] = calcular_kpi_tempo_contratacao(periodo_inicio, periodo_fim)
    
    # KPI 4: Vagas Abertas
    kpis['vagas_abertas'] = calcular_kpi_vagas_abertas()
    
    # KPI 5, 6, 7: Custos (SalÃ¡rios, BenefÃ­cios e Total)
    custos = calcular_kpi_custo_total()
    kpis['custo_salarios'] = {
        'valor': custos['custo_salarios'],
        'variacao': 0,
        'label': 'Custo SalÃ¡rios (Folha)',
        'icone': 'mdi-currency-usd',
        'cor': '#28a745'
    }
    kpis['custo_beneficios'] = {
        'valor': custos['custo_beneficios'],
        'variacao': 0,
        'label': 'Custo BenefÃ­cios',
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
    
    # KPI 8: MÃ©dia de Candidatos por Vaga
    kpis['media_candidatos'] = calcular_kpi_media_candidatos()
    
    # KPI 9: Tempo MÃ©dio de Casa
    kpis['tempo_medio_casa'] = calcular_kpi_tempo_medio_casa()
    
    # KPI 10: Idade MÃ©dia
    kpis['idade_media'] = calcular_kpi_idade_media()
    
    print("âœ… KPIs calculados com sucesso!\n")
    return kpis


def calcular_kpi_headcount():
    """
    KPI 1: Headcount - Total de Colaboradores Ativos
    
    LÃ³gica:
    - COUNT(*) WHERE status = 'Ativo' AND data_desligamento IS NULL
    """
    try:
        response = supabase.table('rh_colaboradores')\
            .select('id', count='exact')\
            .eq('status', 'Ativo')\
            .is_('data_desligamento', 'null')\
            .execute()
        
        headcount = response.count if response.count is not None else 0
        
        print(f"   âœ… Headcount: {headcount}")
        
        return {
            'valor': headcount,
            'variacao': 0,
            'label': 'Colaboradores Ativos',
            'icone': 'mdi-account-group',
            'cor': '#6f42c1'
        }
    except Exception as e:
        print(f"   âŒ Erro ao calcular headcount: {str(e)}")
        return {
            'valor': 0,
            'variacao': 0,
            'label': 'Colaboradores Ativos',
            'icone': 'mdi-account-group',
            'cor': '#6f42c1'
        }


def calcular_kpi_turnover(periodo_inicio, periodo_fim, headcount_atual):
    """
    KPI 2: Turnover - Taxa de Rotatividade (%)
    
    FÃ³rmula:
    - Turnover (%) = (Desligamentos no PerÃ­odo / Headcount MÃ©dio) Ã— 100
    
    LÃ³gica:
    - Usar data_desligamento da tabela rh_colaboradores
    - NÃƒO usar histÃ³rico (pode ter mÃºltiplos registros)
    """
    try:
        # Contar desligamentos no perÃ­odo usando data_desligamento
        response_demissoes = supabase.table('rh_colaboradores')\
            .select('id', count='exact')\
            .not_.is_('data_desligamento', 'null')\
            .gte('data_desligamento', periodo_inicio)\
            .lte('data_desligamento', periodo_fim)\
            .execute()
        
        desligamentos = response_demissoes.count if response_demissoes.count is not None else 0
        
        # Calcular turnover (usar headcount atual como aproximaÃ§Ã£o do mÃ©dio)
        if headcount_atual == 0:
            turnover_taxa = 0
        else:
            turnover_taxa = (desligamentos / headcount_atual) * 100
        
        print(f"   âœ… Turnover: {turnover_taxa:.1f}% ({desligamentos} desligamentos / {headcount_atual} headcount)")
        
        return {
            'valor': round(turnover_taxa, 1),
            'variacao': 0,
            'label': 'Taxa de Rotatividade',
            'icone': 'mdi-account-arrow-right',
            'cor': '#dc3545' if turnover_taxa > 10 else '#28a745'
        }
    except Exception as e:
        print(f"   âŒ Erro ao calcular turnover: {str(e)}")
        return {
            'valor': 0,
            'variacao': 0,
            'label': 'Taxa de Rotatividade',
            'icone': 'mdi-account-arrow-right',
            'cor': '#28a745'
        }


def calcular_kpi_tempo_contratacao(periodo_inicio, periodo_fim):
    """
    KPI 3: Tempo MÃ©dio de ContrataÃ§Ã£o (Dias)
    
    FÃ³rmula:
    - AVG(data_fechamento - data_abertura) para vagas fechadas no perÃ­odo
    """
    try:
        # Buscar vagas fechadas no perÃ­odo
        response_vagas = supabase.table('rh_vagas')\
            .select('data_abertura, data_fechamento')\
            .eq('status', 'Fechada')\
            .not_.is_('data_fechamento', 'null')\
            .gte('data_fechamento', periodo_inicio)\
            .lte('data_fechamento', periodo_fim)\
            .execute()
        
        vagas = response_vagas.data if response_vagas.data else []
        
        if not vagas:
            print(f"   âš ï¸  Tempo ContrataÃ§Ã£o: Nenhuma vaga fechada no perÃ­odo")
            return {
                'valor': 0,
                'variacao': 0,
                'label': 'Tempo MÃ©dio ContrataÃ§Ã£o (dias)',
                'icone': 'mdi-clock-outline',
                'cor': '#17a2b8'
            }
        
        # Calcular diferenÃ§a em dias
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
        
        print(f"   âœ… Tempo MÃ©dio ContrataÃ§Ã£o: {tempo_medio} dias ({count_vagas} vagas fechadas)")
        
        return {
            'valor': tempo_medio,
            'variacao': 0,
            'label': 'Tempo MÃ©dio ContrataÃ§Ã£o (dias)',
            'icone': 'mdi-clock-outline',
            'cor': '#ffc107' if tempo_medio > 30 else '#28a745'
        }
    except Exception as e:
        print(f"   âŒ Erro ao calcular tempo de contrataÃ§Ã£o: {str(e)}")
        return {
            'valor': 0,
            'variacao': 0,
            'label': 'Tempo MÃ©dio ContrataÃ§Ã£o (dias)',
            'icone': 'mdi-clock-outline',
            'cor': '#17a2b8'
        }


def calcular_kpi_vagas_abertas():
    """
    KPI 4: Vagas Abertas - Total de PosiÃ§Ãµes em Aberto
    """
    try:
        response = supabase.table('rh_vagas')\
            .select('id', count='exact')\
            .eq('status', 'Aberta')\
            .execute()
        
        vagas_abertas = response.count if response.count is not None else 0
        
        print(f"   âœ… Vagas Abertas: {vagas_abertas}")
        
        return {
            'valor': vagas_abertas,
            'variacao': 0,
            'label': 'Vagas em Aberto',
            'icone': 'mdi-briefcase-outline',
            'cor': '#6f42c1'
        }
    except Exception as e:
        print(f"   âŒ Erro ao calcular vagas abertas: {str(e)}")
        return {
            'valor': 0,
            'variacao': 0,
            'label': 'Vagas em Aberto',
            'icone': 'mdi-briefcase-outline',
            'cor': '#6f42c1'
        }


def calcular_kpi_media_candidatos():
    """
    KPI 6: MÃ©dia de Candidatos por Vaga
    
    FÃ³rmula:
    - Total de candidatos / Total de vagas com candidatos
    - Considera apenas vagas que receberam candidaturas
    """
    try:
        print(f"   ðŸ” Calculando mÃ©dia de candidatos por vaga")
        
        # Buscar total de candidatos
        response_candidatos = supabase.table('rh_candidatos')\
            .select('id, vaga_id', count='exact')\
            .execute()
        
        total_candidatos = response_candidatos.count if response_candidatos.count is not None else 0
        candidatos_data = response_candidatos.data if response_candidatos.data else []
        
        print(f"   ðŸ“Š Total de candidatos: {total_candidatos}")
        
        # Contar vagas Ãºnicas que receberam candidaturas
        vagas_com_candidatos = set()
        for candidato in candidatos_data:
            if candidato.get('vaga_id'):
                vagas_com_candidatos.add(candidato['vaga_id'])
        
        total_vagas = len(vagas_com_candidatos)
        print(f"   ðŸ“Š Total de vagas com candidatos: {total_vagas}")
        
        # Calcular mÃ©dia
        if total_vagas > 0:
            media = round(total_candidatos / total_vagas, 1)
        else:
            print(f"   âš ï¸  MÃ©dia Candidatos: Nenhuma vaga com candidatos encontrada")
            media = 0
        
        print(f"   âœ… MÃ©dia de Candidatos por Vaga: {media}")
        
        return {
            'valor': media,
            'variacao': 0,
            'label': 'MÃ©dia Candidatos/Vaga',
            'icone': 'mdi-account-multiple-outline',
            'cor': '#20c997' if media >= 5 else '#ffc107'
        }
    except Exception as e:
        print(f"   âŒ Erro ao calcular mÃ©dia de candidatos: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'valor': 0,
            'variacao': 0,
            'label': 'MÃ©dia Candidatos/Vaga',
            'icone': 'mdi-account-multiple-outline',
            'cor': '#17a2b8'
        }


def calcular_kpi_tempo_medio_casa():
    """
    KPI 7: Tempo MÃ©dio de Casa (Anos)
    
    FÃ³rmula:
    - Para cada colaborador ativo, calcular: data_atual - data_admissao
    - Retornar a mÃ©dia em anos
    """
    try:
        print(f"   ðŸ” Calculando tempo mÃ©dio de casa")
        
        # Buscar colaboradores ativos com data de admissÃ£o
        response = supabase.table('rh_colaboradores')\
            .select('id, data_admissao')\
            .eq('status', 'Ativo')\
            .is_('data_desligamento', 'null')\
            .not_.is_('data_admissao', 'null')\
            .execute()
        
        colaboradores = response.data if response.data else []
        print(f"   ðŸ“Š Total de colaboradores ativos com data de admissÃ£o: {len(colaboradores)}")
        
        if not colaboradores:
            print(f"   âš ï¸  Tempo MÃ©dio de Casa: Nenhum colaborador ativo encontrado")
            return {
                'valor': 0,
                'variacao': 0,
                'label': 'Tempo MÃ©dio de Casa',
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
                    print(f"      âš ï¸ Erro ao processar data de admissÃ£o: {data_admissao_str} - {str(ex)}")
                    continue
        
        if not tempos_casa:
            print(f"   âš ï¸  Tempo MÃ©dio de Casa: Nenhuma data vÃ¡lida processada")
            tempo_medio = 0
        else:
            tempo_medio = round(sum(tempos_casa) / len(tempos_casa), 1)
        
        print(f"   âœ… Tempo MÃ©dio de Casa: {tempo_medio} anos ({len(tempos_casa)} colaboradores processados)")
        
        return {
            'valor': tempo_medio,
            'variacao': 0,
            'label': 'Tempo MÃ©dio de Casa',
            'icone': 'mdi-history',
            'cor': '#6f42c1',
            'unidade': 'anos'
        }
    except Exception as e:
        print(f"   âŒ Erro ao calcular tempo mÃ©dio de casa: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'valor': 0,
            'variacao': 0,
            'label': 'Tempo MÃ©dio de Casa',
            'icone': 'mdi-history',
            'cor': '#6f42c1',
            'unidade': 'anos'
        }


def calcular_kpi_idade_media():
    """
    KPI 8: Idade MÃ©dia dos Colaboradores (Anos)
    
    FÃ³rmula:
    - Para cada colaborador ativo, calcular: data_atual - data_nascimento
    - Retornar a mÃ©dia em anos
    """
    try:
        print(f"   ðŸ” Calculando idade mÃ©dia dos colaboradores")
        
        # Buscar colaboradores ativos com data de nascimento
        response = supabase.table('rh_colaboradores')\
            .select('id, data_nascimento')\
            .eq('status', 'Ativo')\
            .is_('data_desligamento', 'null')\
            .not_.is_('data_nascimento', 'null')\
            .execute()
        
        colaboradores = response.data if response.data else []
        print(f"   ðŸ“Š Total de colaboradores ativos com data de nascimento: {len(colaboradores)}")
        
        if not colaboradores:
            print(f"   âš ï¸  Idade MÃ©dia: Nenhum colaborador ativo encontrado")
            return {
                'valor': 0,
                'variacao': 0,
                'label': 'Idade MÃ©dia',
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
                    
                    # Validar idade razoÃ¡vel (entre 18 e 80 anos)
                    if 18 <= idade_anos <= 80:
                        idades.append(idade_anos)
                    else:
                        print(f"      âš ï¸ Idade fora do range vÃ¡lido ignorada: {idade_anos:.1f} anos")
                except Exception as ex:
                    print(f"      âš ï¸ Erro ao processar data de nascimento: {data_nascimento_str} - {str(ex)}")
                    continue
        
        if not idades:
            print(f"   âš ï¸  Idade MÃ©dia: Nenhuma data vÃ¡lida processada")
            idade_media = 0
        else:
            idade_media = round(sum(idades) / len(idades))
        
        print(f"   âœ… Idade MÃ©dia: {idade_media} anos ({len(idades)} colaboradores processados)")
        
        return {
            'valor': idade_media,
            'variacao': 0,
            'label': 'Idade MÃ©dia',
            'icone': 'mdi-cake-variant',
            'cor': '#6f42c1',
            'unidade': 'anos'
        }
    except Exception as e:
        print(f"   âŒ Erro ao calcular idade mÃ©dia: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'valor': 0,
            'variacao': 0,
            'label': 'Idade MÃ©dia',
            'icone': 'mdi-cake-variant',
            'cor': '#6f42c1',
            'unidade': 'anos'
        }


def calcular_kpi_custo_total():
    """
    KPI 5, 6, 7: Custos de Pessoal (SalÃ¡rios, BenefÃ­cios e Total)
    
    Retorna 3 valores separados:
    - custo_salarios: Soma dos salÃ¡rios mensais
    - custo_beneficios: Soma de todos os benefÃ­cios (calculados pela view)
    - custo_total: SalÃ¡rios + BenefÃ­cios
    
    LÃ³gica:
    - Usa a view vw_colaboradores_atual que jÃ¡ tem total_beneficios calculado
    - View jÃ¡ traz Ãºltimo salÃ¡rio e benefÃ­cios de cada colaborador ativo
    """
    try:
        print(f"   ðŸ” Buscando custos da view vw_colaboradores_atual...")
        
        # ðŸ”¥ OTIMIZAÃ‡ÃƒO: Usar view que jÃ¡ calcula tudo
        response = supabase.table('vw_colaboradores_atual')\
            .select('salario_mensal, total_beneficios')\
            .execute()
        
        colaboradores = response.data if response.data else []
        
        print(f"   ðŸ“Š Total de colaboradores ativos: {len(colaboradores)}")
        
        if not colaboradores:
            print(f"   âš ï¸  Custos: Nenhum colaborador ativo encontrado")
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
            # Processar salÃ¡rio
            salario_mensal = colab.get('salario_mensal')
            if salario_mensal:
                try:
                    valor_salario = float(salario_mensal)
                    custo_salarios += valor_salario
                    colaboradores_com_salario += 1
                except (ValueError, TypeError) as e:
                    print(f"      âš ï¸ Erro ao converter salÃ¡rio: {salario_mensal}")
            
            # Processar benefÃ­cios (jÃ¡ calculados pela view)
            total_beneficios = colab.get('total_beneficios')
            if total_beneficios:
                try:
                    valor_beneficios = float(total_beneficios)
                    if valor_beneficios > 0:
                        custo_beneficios += valor_beneficios
                        colaboradores_com_beneficios += 1
                except (ValueError, TypeError) as e:
                    print(f"      âš ï¸ Erro ao converter benefÃ­cios: {total_beneficios}")
        
        custo_total = custo_salarios + custo_beneficios
        
        print(f"   âœ… Custo SalÃ¡rios: R$ {custo_salarios:,.2f} ({colaboradores_com_salario} colaboradores)")
        print(f"   âœ… Custo BenefÃ­cios: R$ {custo_beneficios:,.2f} ({colaboradores_com_beneficios} colaboradores)")
        print(f"   âœ… Custo Total: R$ {custo_total:,.2f}")
        
        if custo_salarios == 0 and len(colaboradores) > 0:
            print(f"   âš ï¸  ATENÃ‡ÃƒO: Nenhum salÃ¡rio encontrado! Verifique se os dados estÃ£o corretos.")
        
        return {
            'custo_salarios': custo_salarios,
            'custo_beneficios': custo_beneficios,
            'custo_total': custo_total
        }
    except Exception as e:
        print(f"   âŒ Erro ao calcular custos: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'custo_salarios': 0,
            'custo_beneficios': 0,
            'custo_total': 0
        }


# ========================================
# FUNÃ‡Ã•ES DE CÃLCULO - GRÃFICOS
# ========================================

def calcular_graficos(periodo_inicio, periodo_fim, departamentos_ids=None):
    """
    Calcula os grÃ¡ficos principais do Dashboard Executivo
    
    GrÃ¡ficos:
    1. EvoluÃ§Ã£o do Headcount (Linha - 12 meses)
    2. AdmissÃµes vs Desligamentos (Barras agrupadas)
    3. Turnover por Departamento (Barras - Top 5)
    4. DistribuiÃ§Ã£o por Departamento (Pizza)
    """
    print("ðŸš€ Calculando GrÃ¡ficos do Dashboard Executivo...")
    
    graficos = {}
    
    # GrÃ¡fico 1 e 2: EvoluÃ§Ã£o e AdmissÃµes/Desligamentos (usam mesmos dados)
    dados_evolucao = calcular_grafico_evolucao_headcount(periodo_inicio, periodo_fim)
    graficos['evolucao_headcount'] = dados_evolucao
    graficos['admissoes_desligamentos'] = {
        'labels': dados_evolucao['labels'],
        'datasets': {
            'admissoes': dados_evolucao['datasets']['admissoes'],
            'desligamentos': dados_evolucao['datasets']['desligamentos']
        }
    }
    
    # GrÃ¡fico 3: Turnover por Departamento (Top 5)
    graficos['turnover_departamento'] = calcular_grafico_turnover_departamento(periodo_inicio, periodo_fim)
    
    # GrÃ¡fico 4: DistribuiÃ§Ã£o por Departamento
    graficos['distribuicao_departamento'] = calcular_grafico_distribuicao_departamento()
    
    print("âœ… GrÃ¡ficos calculados com sucesso!\n")
    return graficos


def calcular_grafico_evolucao_headcount(periodo_inicio, periodo_fim):
    """
    GrÃ¡fico 1: EvoluÃ§Ã£o do Headcount (Linha - 12 meses)
    
    Datasets:
    - Headcount no final de cada mÃªs
    - AdmissÃµes no mÃªs
    - Desligamentos no mÃªs
    
    OtimizaÃ§Ã£o:
    - Buscar TODOS os eventos do perÃ­odo de uma vez
    - Agrupar em Python (O(n) ao invÃ©s de 24 queries)
    """
    try:
        print(f"   ðŸ” Calculando evoluÃ§Ã£o de headcount para perÃ­odo {periodo_inicio} a {periodo_fim}")
        
        # Gerar lista de meses no perÃ­odo
        data_inicio = datetime.strptime(periodo_inicio, '%Y-%m-%d')
        data_fim = datetime.strptime(periodo_fim, '%Y-%m-%d')
        
        meses = []
        current = data_inicio.replace(day=1)
        while current <= data_fim:
            meses.append(current.strftime('%Y-%m'))
            current += relativedelta(months=1)
        
        print(f"   ðŸ“Š Total de meses a processar: {len(meses)}")
        
        # ðŸ”¥ OTIMIZAÃ‡ÃƒO: Buscar todas as admissÃµes do perÃ­odo de uma vez
        response_admissoes = supabase.table('rh_colaboradores')\
            .select('data_admissao')\
            .not_.is_('data_admissao', 'null')\
            .gte('data_admissao', periodo_inicio)\
            .lte('data_admissao', periodo_fim)\
            .execute()
        
        # ðŸ”¥ OTIMIZAÃ‡ÃƒO: Buscar todos os desligamentos do perÃ­odo de uma vez
        response_desligamentos = supabase.table('rh_colaboradores')\
            .select('data_desligamento')\
            .not_.is_('data_desligamento', 'null')\
            .gte('data_desligamento', periodo_inicio)\
            .lte('data_desligamento', periodo_fim)\
            .execute()
        
        print(f"   ðŸ“Š AdmissÃµes encontradas: {len(response_admissoes.data or [])}")
        print(f"   ðŸ“Š Desligamentos encontrados: {len(response_desligamentos.data or [])}")
        
        # DEBUG: Mostrar primeiras 3 datas de cada tipo
        if response_admissoes.data:
            print(f"   ðŸ” Primeiras 3 admissÃµes:")
            for i, adm in enumerate(response_admissoes.data[:3]):
                print(f"      {i+1}. {adm.get('data_admissao')}")
        
        if response_desligamentos.data:
            print(f"   ðŸ” Primeiros 3 desligamentos:")
            for i, desl in enumerate(response_desligamentos.data[:3]):
                print(f"      {i+1}. {desl.get('data_desligamento')}")
        
        # Agrupar eventos por mÃªs em Python
        admissoes_por_mes = defaultdict(int)
        desligamentos_por_mes = defaultdict(int)
        
        for evento in (response_admissoes.data or []):
            data_admissao = evento.get('data_admissao')
            if data_admissao:
                mes = data_admissao[:7]  # YYYY-MM
                admissoes_por_mes[mes] += 1
        
        for evento in (response_desligamentos.data or []):
            data_desligamento = evento.get('data_desligamento')
            if data_desligamento:
                mes = data_desligamento[:7]  # YYYY-MM
                desligamentos_por_mes[mes] += 1
        
        # Buscar headcount inicial (antes do perÃ­odo)
        # Contar colaboradores admitidos antes do perÃ­odo_inicio e que ainda estavam ativos
        response_headcount_inicial = supabase.table('rh_colaboradores')\
            .select('id', count='exact')\
            .lt('data_admissao', periodo_inicio)\
            .or_(f'data_desligamento.is.null,data_desligamento.gte.{periodo_inicio}')\
            .execute()
        
        headcount_inicial = response_headcount_inicial.count if response_headcount_inicial.count is not None else 0
        print(f"   ðŸ“Š Headcount inicial (antes de {periodo_inicio}): {headcount_inicial}")
        
        # Montar arrays de dados calculando headcount progressivo
        labels = []
        headcount_data = []
        admissoes_data = []
        desligamentos_data = []
        
        headcount_acumulado = headcount_inicial
        
        # Retornar meses no formato YYYY-MM (JavaScript farÃ¡ a formataÃ§Ã£o para legibilidade)
        for mes in meses:
            try:
                admissoes_mes = admissoes_por_mes.get(mes, 0)
                desligamentos_mes = desligamentos_por_mes.get(mes, 0)
                
                # Calcular headcount progressivo: headcount anterior + admissÃµes - desligamentos
                headcount_acumulado = headcount_acumulado + admissoes_mes - desligamentos_mes
                
                labels.append(mes)  # Formato: "2024-10"
                headcount_data.append(headcount_acumulado)
                admissoes_data.append(admissoes_mes)
                desligamentos_data.append(desligamentos_mes)
            except Exception as ex:
                print(f"      âš ï¸ Erro ao processar mÃªs {mes}: {str(ex)}")
                continue
        
        print(f"   âœ… EvoluÃ§Ã£o Headcount: {len(labels)} meses processados")
        print(f"      Headcount inicial: {headcount_inicial}")
        print(f"      Headcount final: {headcount_data[-1] if headcount_data else 0}")
        print(f"      Total admissÃµes perÃ­odo: {sum(admissoes_data)}")
        print(f"      Total desligamentos perÃ­odo: {sum(desligamentos_data)}")
        print(f"      VariaÃ§Ã£o lÃ­quida: {sum(admissoes_data) - sum(desligamentos_data)}")
        
        # Log detalhado dos primeiros 3 meses
        print(f"      Detalhamento por mÃªs (primeiros 3):")
        for i in range(min(3, len(labels))):
            print(f"         {labels[i]}: AdmissÃµes={admissoes_data[i]}, DemissÃµes={desligamentos_data[i]}")
        
        return {
            'labels': labels,
            'datasets': {
                'headcount': headcount_data,
                'admissoes': admissoes_data,
                'desligamentos': desligamentos_data
            }
        }
    except Exception as e:
        print(f"   âŒ Erro ao calcular evoluÃ§Ã£o headcount: {str(e)}")
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
    GrÃ¡fico 3: Turnover por Departamento (Barras - Top 5)
    
    LÃ³gica:
    - Para cada departamento, calcular turnover (%)
    - Turnover = (Desligamentos / Headcount do Depto) Ã— 100
    - Ordenar por turnover DESC e pegar Top 5
    
    OtimizaÃ§Ã£o:
    - Buscar todos os histÃ³ricos de uma vez
    - Mapear colaborador â†’ departamento em Python
    """
    try:
        print(f"   ðŸ” Calculando turnover por departamento para perÃ­odo {periodo_inicio} a {periodo_fim}")
        
        # Buscar departamentos
        response_deps = supabase.table('rh_departamentos')\
            .select('id, nome_departamento')\
            .execute()
        
        departamentos = response_deps.data if response_deps.data else []
        print(f"   ðŸ“Š Total de departamentos encontrados: {len(departamentos)}")
        
        if not departamentos:
            print(f"   âš ï¸  Turnover por Departamento: Nenhum departamento encontrado")
            return {'labels': [], 'data': []}
        
        # Buscar colaboradores demitidos no perÃ­odo
        response_demitidos = supabase.table('rh_colaboradores')\
            .select('id')\
            .not_.is_('data_desligamento', 'null')\
            .gte('data_desligamento', periodo_inicio)\
            .lte('data_desligamento', periodo_fim)\
            .execute()
        
        colaboradores_demitidos_ids = [c['id'] for c in (response_demitidos.data or [])]
        print(f"   ðŸ“Š Colaboradores demitidos no perÃ­odo: {len(colaboradores_demitidos_ids)}")
        
        # ðŸ”¥ OTIMIZAÃ‡ÃƒO: Buscar TODOS os histÃ³ricos de uma vez
        response_hist = supabase.table('rh_historico_colaborador')\
            .select('colaborador_id, departamento_id')\
            .not_.is_('departamento_id', 'null')\
            .order('data_evento', desc=True)\
            .execute()
        
        print(f"   ðŸ“Š Total de registros no histÃ³rico: {len(response_hist.data or [])}")
        
        # Mapear colaborador â†’ departamento (Ãºltimo registro)
        colaborador_dept_map = {}
        for hist in (response_hist.data or []):
            colab_id = hist['colaborador_id']
            if colab_id not in colaborador_dept_map:
                colaborador_dept_map[colab_id] = hist['departamento_id']
        
        print(f"   ðŸ“Š Colaboradores mapeados para departamentos: {len(colaborador_dept_map)}")
        
        # Contar demissÃµes por departamento
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
        
        print(f"   âœ… Turnover por Departamento: Top {len(labels)}")
        print(f"      Departamentos com maior turnover: {labels}")
        print(f"      Valores de turnover (%): {data}")
        for d in dados_turnover_sorted:
            print(f"      {d['departamento']}: {d['turnover']}% ({d['demissoes']}/{d['headcount']})")
        
        return {
            'labels': labels,
            'data': data
        }
    except Exception as e:
        print(f"   âŒ Erro ao calcular turnover por departamento: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'labels': [], 'data': []}


def calcular_grafico_distribuicao_departamento():
    """
    GrÃ¡fico 4: DistribuiÃ§Ã£o de Colaboradores por Departamento (Pizza)
    
    LÃ³gica:
    - Contar colaboradores ativos por departamento
    - Retornar labels (nomes dos departamentos) e data (quantidades)
    """
    try:
        print(f"   ðŸ” Calculando distribuiÃ§Ã£o por departamento")
        
        # Buscar departamentos
        response_deps = supabase.table('rh_departamentos')\
            .select('id, nome_departamento')\
            .execute()
        
        departamentos = response_deps.data if response_deps.data else []
        print(f"   ðŸ“Š Total de departamentos: {len(departamentos)}")
        
        if not departamentos:
            print(f"   âš ï¸  DistribuiÃ§Ã£o por Departamento: Nenhum departamento encontrado")
            return {'labels': [], 'data': []}
        
        # Buscar histÃ³rico de todos os colaboradores ativos
        response_colabs = supabase.table('rh_colaboradores')\
            .select('id')\
            .eq('status', 'Ativo')\
            .is_('data_desligamento', 'null')\
            .execute()
        
        colaboradores_ids = [c['id'] for c in (response_colabs.data or [])]
        print(f"   ðŸ“Š Total de colaboradores ativos: {len(colaboradores_ids)}")
        
        if not colaboradores_ids:
            print(f"   âš ï¸  DistribuiÃ§Ã£o por Departamento: Nenhum colaborador ativo")
            return {'labels': [], 'data': []}
        
        # Buscar Ãºltimo departamento de cada colaborador
        response_hist = supabase.table('rh_historico_colaborador')\
            .select('colaborador_id, departamento_id')\
            .in_('colaborador_id', colaboradores_ids)\
            .not_.is_('departamento_id', 'null')\
            .order('data_evento', desc=True)\
            .execute()
        
        print(f"   ðŸ“Š Registros no histÃ³rico: {len(response_hist.data or [])}")
        
        # Mapear colaborador â†’ departamento (Ãºltimo registro)
        colaborador_dept_map = {}
        for hist in (response_hist.data or []):
            colab_id = hist['colaborador_id']
            if colab_id not in colaborador_dept_map:
                colaborador_dept_map[colab_id] = hist['departamento_id']
        
        # Contar colaboradores por departamento
        dept_counts = defaultdict(int)
        for dept_id in colaborador_dept_map.values():
            dept_counts[dept_id] += 1
        
        # Criar mapa de ID â†’ Nome do departamento
        dept_map = {d['id']: d['nome_departamento'] for d in departamentos}
        
        # Montar dados do grÃ¡fico
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
        
        print(f"   âœ… DistribuiÃ§Ã£o por Departamento: {len(labels)} departamentos")
        print(f"      Departamentos: {labels}")
        print(f"      Quantidades: {data}")
        
        return {
            'labels': labels,
            'data': data
        }
    except Exception as e:
        print(f"   âŒ Erro ao calcular distribuiÃ§Ã£o por departamento: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'labels': [], 'data': []}


# ========================================
# FUNÃ‡Ã•ES DE CÃLCULO - TABELAS
# ========================================

def calcular_tabelas(periodo_inicio, periodo_fim, departamentos_ids=None):
    """
    Calcula dados para tabelas do Dashboard
    
    Tabelas:
    1. Vagas Abertas por Mais Tempo (Top 5)
    """
    print("ðŸš€ Calculando Tabelas do Dashboard Executivo...")
    
    tabelas = {}
    
    # Tabela 1: Vagas Abertas por Mais Tempo
    tabelas['vagas_abertas_mais_tempo'] = calcular_tabela_vagas_abertas_mais_tempo()
    
    print("âœ… Tabelas calculadas com sucesso!\n")
    return tabelas


def calcular_tabela_vagas_abertas_mais_tempo():
    """
    Tabela 1: Vagas Abertas por Mais Tempo (Top 5)
    
    Colunas:
    - TÃ­tulo da Vaga
    - Cargo
    - Departamento
    - Data Abertura
    - Dias em Aberto
    
    Mostra TODAS as vagas abertas, priorizando as mais antigas
    """
    try:
        print(f"   ðŸ” Buscando vagas abertas por mais tempo")
        
        # USAR A MESMA QUERY DO KPI - apenas status 'Aberta'
        response_vagas = supabase.table('rh_vagas')\
            .select('id, titulo, data_abertura, cargo_id, localizacao, departamento_id, status')\
            .eq('status', 'Aberta')\
            .execute()
        
        todas_vagas = response_vagas.data if response_vagas.data else []
        print(f"   ðŸ“Š Total de vagas com status 'Aberta': {len(todas_vagas)}")
        
        # Contar quantas tÃªm data_abertura
        vagas_com_data = [v for v in todas_vagas if v.get('data_abertura')]
        vagas_sem_data = [v for v in todas_vagas if not v.get('data_abertura')]
        print(f"   ðŸ“Š Vagas COM data_abertura: {len(vagas_com_data)}")
        print(f"   âš ï¸  Vagas SEM data_abertura: {len(vagas_sem_data)}")
        
        if not todas_vagas:
            print(f"   âš ï¸  Nenhuma vaga aberta encontrada")
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
            
            print(f"   ðŸ“Š Cargos mapeados: {len(cargos_map)}")
        
        # Buscar nomes dos departamentos
        departamentos_ids = [v['departamento_id'] for v in todas_vagas if v.get('departamento_id')]
        departamentos_map = {}
        
        if departamentos_ids:
            response_deps = supabase.table('rh_departamentos')\
                .select('id, nome_departamento')\
                .in_('id', departamentos_ids)\
                .execute()
            
            for dept in (response_deps.data or []):
                departamentos_map[dept['id']] = dept['nome_departamento']
            
            print(f"   ðŸ“Š Departamentos mapeados: {len(departamentos_map)}")
        
        # Calcular dias em aberto E FILTRAR por 15 dias mÃ­nimos
        hoje = datetime.now()
        tabela_vagas = []
        DIAS_MINIMOS = 15  # Filtro: apenas vagas abertas hÃ¡ mais de 15 dias
        
        for vaga in todas_vagas:
            data_abertura_str = vaga.get('data_abertura', '')
            
            # Se nÃ£o tem data de abertura, pular
            if not data_abertura_str:
                print(f"      âš ï¸ Vaga sem data_abertura: {vaga.get('titulo')} (ID: {vaga.get('id')})")
                continue
            
            try:
                data_abertura = datetime.strptime(data_abertura_str[:10], '%Y-%m-%d')
                dias_aberta = (hoje - data_abertura).days
                
                # FILTRO: Apenas vagas com 15 dias ou mais
                if dias_aberta < DIAS_MINIMOS:
                    continue
                
                # Determinar status de urgÃªncia
                if dias_aberta > 60:
                    status_urgencia = 'alta'
                elif dias_aberta > 30:
                    status_urgencia = 'media'
                else:
                    status_urgencia = 'baixa'
                
                tabela_vagas.append({
                    'id': vaga.get('id'),
                    'titulo': vaga.get('titulo', 'Sem tÃ­tulo'),
                    'cargo': cargos_map.get(vaga.get('cargo_id'), 'NÃ£o especificado'),
                    'departamento': departamentos_map.get(vaga.get('departamento_id'), 'NÃ£o especificado'),
                    'localizacao': vaga.get('localizacao', 'NÃ£o especificado'),
                    'data_abertura': data_abertura.strftime('%d/%m/%Y'),
                    'dias_aberto': dias_aberta,
                    'status_urgencia': status_urgencia,
                    'num_candidatos': 0,  # TODO: buscar da tabela rh_candidatos
                    'candidatos_score_alto': 0  # TODO: buscar candidatos com score > 80
                })
            except Exception as ex:
                    print(f"      âš ï¸ Erro ao processar vaga {vaga.get('id')}: {str(ex)}")
                    continue
        
        # Ordenar por dias_aberto DESC e pegar Top 5
        tabela_vagas_sorted = sorted(tabela_vagas, key=lambda x: x['dias_aberto'], reverse=True)[:5]
        
        print(f"   ï¿½ Vagas filtradas (>{DIAS_MINIMOS} dias): {len(tabela_vagas)}")
        print(f"   âœ… Top 5 vagas mais antigas: {len(tabela_vagas_sorted)}")
        for v in tabela_vagas_sorted:
            print(f"      {v['titulo']}: {v['dias_aberto']} dias ({v['status_urgencia']})")
        
        return tabela_vagas_sorted
        
    except Exception as e:
        print(f"   âŒ Erro ao calcular vagas abertas mais tempo: {str(e)}")
        import traceback
        traceback.print_exc()
        return []




# ========================================
# IMPORTAR FUNÇÕES DO DASHBOARD ANALÍTICO V2.0
# ========================================
from .routes_v2_functions import (
    calcular_secao_recrutamento,
    calcular_secao_turnover,
    calcular_tempo_medio_contratacao_v2,
    calcular_vagas_abertas_v2,
    calcular_vagas_fechadas_v2,
    calcular_vagas_canceladas_v2,
    calcular_tempo_contratacao_por_cargo_v2,
    calcular_tempo_contratacao_por_departamento_v2,
    calcular_evolucao_vagas_v2,
    calcular_tabela_vagas_abertas_v2,
    calcular_turnover_geral_v2,
    calcular_total_desligamentos_v2,
    calcular_total_admissoes_v2,
    calcular_tempo_medio_permanencia_v2,
    calcular_headcount_atual_v2,
    calcular_turnover_por_departamento_v2,
    calcular_turnover_por_cargo_v2,
    calcular_desligamentos_por_tempo_casa_v2,
    calcular_turnover_por_faixa_etaria_v2,
    calcular_evolucao_turnover_v2,
    calcular_tabela_desligamentos_recentes_v2,
    calcular_secao_administracao_pessoal,
    calcular_secao_compliance_operacional
)
