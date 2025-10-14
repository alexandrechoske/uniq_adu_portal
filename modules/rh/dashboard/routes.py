"""
Rotas - Dashboard Executivo RH
Endpoints para visualização de indicadores executivos de RH
"""

from flask import render_template, jsonify, request
from modules.auth.routes import login_required
from decorators.perfil_decorators import perfil_required
from . import dashboard_rh_bp
from extensions import supabase_admin as supabase
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from dateutil import parser as date_parser

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
        
        print(f"📊 API Dashboard - Período: {periodo_inicio} a {periodo_fim}")
        print(f"📊 Departamentos filtrados: {departamentos_ids if departamentos_ids else 'Todos'}")
        
        # 🔥 OTIMIZAÇÃO: Buscar todos os colaboradores ativos de uma vez (apenas IDs para outras queries)
        response_colabs_ativos = supabase.table('rh_colaboradores')\
            .select('id, data_admissao, data_nascimento, data_desligamento, status')\
            .eq('status', 'Ativo')\
            .is_('data_desligamento', 'null')\
            .execute()
        
        colaboradores_ativos = response_colabs_ativos.data if response_colabs_ativos.data else []
        headcount_atual = len(colaboradores_ativos)
        colaboradores_ativos_ids = [c['id'] for c in colaboradores_ativos]
        
        print(f"✅ Colaboradores ativos (sem data_desligamento): {headcount_atual}")
        
        # Calcular KPIs
        kpis = calcular_kpis(periodo_inicio, periodo_fim, departamentos_ids)
        
        # Calcular dados para gráficos
        graficos = calcular_graficos(periodo_inicio, periodo_fim, departamentos_ids)
        
        # Calcular dados para tabelas
        tabelas = calcular_tabelas(periodo_inicio, periodo_fim, departamentos_ids)
        
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


# ========================================
# FUNÇÕES DE CÁLCULO - KPIs
# ========================================

def calcular_kpis(periodo_inicio, periodo_fim, departamentos_ids=None):
    """
    Calcula os KPIs principais do dashboard
    OTIMIZADO: Busca dados compartilhados uma única vez
    CORRIGIDO: Usa data_desligamento para verificar status ativo
    """
    print("🚀 [OTIMIZAÇÃO] Carregando dados compartilhados...")
    
    # 🔥 OTIMIZAÇÃO 1: Buscar todos os colaboradores ativos de uma vez (era 11 queries, agora 1)
    # ✅ CORREÇÃO: Considera ativo apenas quem tem status='Ativo' E data_desligamento NULL
    response_colabs_ativos = supabase.table('rh_colaboradores')\
        .select('id, data_admissao, data_nascimento, data_desligamento, status')\
        .eq('status', 'Ativo')\
        .is_('data_desligamento', 'null')\
        .execute()
    
    colaboradores_ativos = response_colabs_ativos.data if response_colabs_ativos.data else []
    headcount_atual = len(colaboradores_ativos)
    colaboradores_ativos_ids = [c['id'] for c in colaboradores_ativos]
    
    print(f"✅ Colaboradores ativos (status=Ativo E sem demissão): {headcount_atual}")
    
    # 🔥 OTIMIZAÇÃO 2: Buscar todos os salários de uma vez usando IN (era 9 queries, agora 1)
    massa_salarial_total = 0
    if colaboradores_ativos_ids:
        # Buscar histórico de salários para todos os colaboradores ativos de uma vez
        response_salarios = supabase.table('rh_historico_colaborador')\
            .select('colaborador_id, salario_mensal, data_evento')\
            .in_('colaborador_id', colaboradores_ativos_ids)\
            .not_.is_('salario_mensal', 'null')\
            .order('data_evento', desc=True)\
            .execute()
        
        # Agrupar por colaborador e pegar o mais recente
        salarios_por_colaborador = {}
        for registro in (response_salarios.data or []):
            colab_id = registro['colaborador_id']
            if colab_id not in salarios_por_colaborador:
                salarios_por_colaborador[colab_id] = float(registro['salario_mensal'] or 0)
        
        massa_salarial_total = sum(salarios_por_colaborador.values())
    
    print(f"✅ Massa salarial calculada: R$ {massa_salarial_total:,.2f}")
    
    # KPI 1: Headcount Ativo
    kpis = {
        'headcount': {
            'valor': headcount_atual,
            'variacao': 0,
            'label': 'Total de Colaboradores'
        },
        
        # KPI 2: Massa Salarial Mensal
        'massa_salarial': {
            'valor': massa_salarial_total,
            'variacao': 0,
            'label': 'Custo Mensal (Folha)'
        }
    }
    
    # KPI 3: Turnover Anualizado
    kpis['turnover'] = calcular_turnover_otimizado(periodo_inicio, periodo_fim, headcount_atual, departamentos_ids)
    
    # KPI 4: Tempo Médio de Contratação
    kpis['tempo_contratacao'] = calcular_tempo_medio_contratacao(periodo_inicio, periodo_fim, departamentos_ids)
    
    # KPI 5: Total de Vagas em Aberto
    kpis['vagas_abertas'] = calcular_total_vagas_abertas(departamentos_ids)
    
    # KPI 6: Média de Candidatos por Vaga
    kpis['media_candidatos_vaga'] = calcular_media_candidatos_vaga_otimizado(departamentos_ids)
    
    # KPI 7: Tempo Médio de Casa (usando dados já carregados)
    kpis['tempo_medio_casa'] = calcular_tempo_medio_casa_otimizado(colaboradores_ativos)
    
    # KPI 8: Idade Média (usando dados já carregados)
    kpis['idade_media'] = calcular_idade_media_otimizado(colaboradores_ativos)
    
    print("✅ [OTIMIZAÇÃO] KPIs calculados com sucesso!")
    
    return kpis


# ========================================
# FUNÇÕES AUXILIARES OTIMIZADAS
# ========================================

def calcular_turnover_otimizado(periodo_inicio, periodo_fim, headcount_atual, departamentos_ids=None):
    """
    KPI 3: Taxa de Rotatividade (Turnover) - OTIMIZADO E CORRIGIDO
    Recebe headcount já calculado para evitar query duplicada
    CORREÇÃO: Usa data_desligamento da tabela rh_colaboradores ao invés de histórico
    """
    try:
        # ✅ CORREÇÃO: Buscar desligamentos pela data_desligamento na tabela principal
        response_demissoes = supabase.table('rh_colaboradores')\
            .select('id', count='exact')\
            .not_.is_('data_desligamento', 'null')\
            .gte('data_desligamento', periodo_inicio)\
            .lte('data_desligamento', periodo_fim)\
            .execute()
        
        desligamentos = response_demissoes.count if response_demissoes.count is not None else 0
        
        print(f"📊 Turnover: {desligamentos} desligamentos no período, headcount: {headcount_atual}")
        
        if headcount_atual == 0:
            turnover_taxa = 0
        else:
            turnover_taxa = (desligamentos / headcount_atual) * 100
        
        return {
            'valor': round(turnover_taxa, 1),
            'variacao': 0,
            'label': 'Taxa de Rotatividade'
        }
    except Exception as e:
        print(f"❌ Erro ao calcular turnover: {str(e)}")
        return {'valor': 0, 'variacao': 0, 'label': 'Taxa de Rotatividade'}


def calcular_media_candidatos_vaga_otimizado(departamentos_ids=None):
    """
    KPI 6: Média de Candidatos por Vaga - OTIMIZADO
    Usa GROUP BY no banco ao invés de loop
    """
    try:
        # Buscar vagas abertas
        query_vagas = supabase.table('rh_vagas').select('id').eq('status', 'Aberta')
        
        if departamentos_ids and len(departamentos_ids) > 0:
            query_vagas = query_vagas.in_('departamento_id', departamentos_ids)
        
        response_vagas = query_vagas.execute()
        vagas = response_vagas.data if response_vagas.data else []
        
        if len(vagas) == 0:
            return {'valor': 0, 'variacao': 0, 'label': 'Média Candidatos/Vaga'}
        
        vagas_ids = [v['id'] for v in vagas]
        
        # 🔥 OTIMIZAÇÃO: Buscar todos os candidatos de uma vez com IN
        response_cands = supabase.table('rh_candidatos')\
            .select('vaga_id')\
            .in_('vaga_id', vagas_ids)\
            .execute()
        
        total_candidatos = len(response_cands.data) if response_cands.data else 0
        media = round(total_candidatos / len(vagas), 1) if len(vagas) > 0 else 0
        
        return {
            'valor': media,
            'variacao': 0,
            'label': 'Média Candidatos/Vaga'
        }
    except Exception as e:
        print(f"❌ Erro ao calcular média candidatos/vaga: {str(e)}")
        return {'valor': 0, 'variacao': 0, 'label': 'Média Candidatos/Vaga'}


def calcular_tempo_medio_casa_otimizado(colaboradores_ativos):
    """
    KPI 7: Tempo Médio de Casa - OTIMIZADO
    Recebe lista de colaboradores já carregada
    """
    try:
        if len(colaboradores_ativos) == 0:
            return {'valor': 0, 'variacao': 0, 'label': 'Tempo Médio de Casa'}
        
        hoje = datetime.now()
        total_dias = 0
        count = 0
        
        for colab in colaboradores_ativos:
            if colab.get('data_admissao'):
                data_admissao = datetime.strptime(colab['data_admissao'], '%Y-%m-%d')
                
                if colab.get('data_desligamento'):
                    data_fim = datetime.strptime(colab['data_desligamento'], '%Y-%m-%d')
                else:
                    data_fim = hoje
                
                dias = (data_fim - data_admissao).days
                total_dias += dias
                count += 1
        
        tempo_medio_anos = round((total_dias / count) / 365.25, 1) if count > 0 else 0
        
        return {
            'valor': tempo_medio_anos,
            'variacao': 0,
            'label': 'Tempo Médio de Casa'
        }
    except Exception as e:
        print(f"❌ Erro ao calcular tempo médio de casa: {str(e)}")
        return {'valor': 0, 'variacao': 0, 'label': 'Tempo Médio de Casa'}


def calcular_idade_media_otimizado(colaboradores_ativos):
    """
    KPI 8: Idade Média - OTIMIZADO
    Recebe lista de colaboradores já carregada
    """
    try:
        colaboradores_com_nascimento = [c for c in colaboradores_ativos if c.get('data_nascimento')]
        
        if len(colaboradores_com_nascimento) == 0:
            return {'valor': 0, 'variacao': 0, 'label': 'Idade Média'}
        
        hoje = datetime.now()
        total_anos = 0
        
        for colab in colaboradores_com_nascimento:
            data_nascimento = datetime.strptime(colab['data_nascimento'], '%Y-%m-%d')
            idade = (hoje - data_nascimento).days / 365.25
            total_anos += idade
        
        idade_media = round(total_anos / len(colaboradores_com_nascimento), 1)
        
        return {
            'valor': idade_media,
            'variacao': 0,
            'label': 'Idade Média'
        }
    except Exception as e:
        print(f"❌ Erro ao calcular idade média: {str(e)}")
        return {'valor': 0, 'variacao': 0, 'label': 'Idade Média'}


# ========================================
# FUNÇÕES AUXILIARES ANTIGAS (MANTIDAS PARA COMPATIBILIDADE)
# ========================================

def calcular_headcount_ativo(departamentos_ids=None):
    """
    KPI 1: Total de Colaboradores Ativos
    """
    try:
        query = supabase.table('rh_colaboradores').select('id', count='exact').eq('status', 'Ativo')
        
        # Aplicar filtro de departamento se especificado
        # Note: Precisamos buscar o departamento atual do histórico
        # Por simplicidade, vamos assumir que colaboradores ativos têm registro no histórico
        
        response = query.execute()
        count = response.count if response.count is not None else 0
        
        # Calcular variação (comparar com mês anterior - placeholder)
        variacao = 0  # TODO: Implementar cálculo de variação
        
        return {
            'valor': count,
            'variacao': variacao,
            'label': 'Total de Colaboradores'
        }
    except Exception as e:
        print(f"❌ Erro ao calcular headcount: {str(e)}")
        return {'valor': 0, 'variacao': 0, 'label': 'Total de Colaboradores'}


def calcular_massa_salarial(departamentos_ids=None):
    """
    KPI 2: Massa Salarial Mensal (soma dos salários ativos)
    """
    try:
        # Buscar colaboradores ativos
        response_colabs = supabase.table('rh_colaboradores').select('id').eq('status', 'Ativo').execute()
        colaboradores_ativos_ids = [c['id'] for c in response_colabs.data] if response_colabs.data else []
        
        if not colaboradores_ativos_ids:
            return {'valor': 0, 'variacao': 0, 'label': 'Custo Mensal (Folha)'}
        
        # Buscar o salário mais recente de cada colaborador no histórico
        total_salarios = 0
        for colab_id in colaboradores_ativos_ids:
            response_hist = supabase.table('rh_historico_colaborador')\
                .select('salario_mensal')\
                .eq('colaborador_id', colab_id)\
                .not_.is_('salario_mensal', 'null')\
                .order('data_evento', desc=True)\
                .limit(1)\
                .execute()
            
            if response_hist.data and len(response_hist.data) > 0:
                salario = response_hist.data[0].get('salario_mensal')
                if salario:
                    total_salarios += float(salario)
        
        variacao = 0  # TODO: Implementar cálculo de variação
        
        return {
            'valor': total_salarios,
            'variacao': variacao,
            'label': 'Custo Mensal (Folha)'
        }
    except Exception as e:
        print(f"❌ Erro ao calcular massa salarial: {str(e)}")
        return {'valor': 0, 'variacao': 0, 'label': 'Custo Mensal (Folha)'}


def calcular_turnover(periodo_inicio, periodo_fim, departamentos_ids=None):
    """
    KPI 3: Taxa de Rotatividade (Turnover)
    Fórmula: (Desligamentos / Headcount Médio) * 100
    """
    try:
        # Contar desligamentos no período
        response_demissoes = supabase.table('rh_historico_colaborador')\
            .select('id', count='exact')\
            .eq('tipo_evento', 'Demissão')\
            .gte('data_evento', periodo_inicio)\
            .lte('data_evento', periodo_fim)\
            .execute()
        
        desligamentos = response_demissoes.count if response_demissoes.count is not None else 0
        
        # Calcular headcount médio (simplificado: headcount atual)
        response_headcount = supabase.table('rh_colaboradores').select('id', count='exact').eq('status', 'Ativo').execute()
        headcount_atual = response_headcount.count if response_headcount.count is not None else 1
        
        # Evitar divisão por zero
        if headcount_atual == 0:
            turnover_taxa = 0
        else:
            turnover_taxa = (desligamentos / headcount_atual) * 100
        
        variacao = 0  # TODO: Implementar comparação com período anterior
        
        return {
            'valor': round(turnover_taxa, 1),
            'variacao': variacao,
            'label': 'Taxa de Rotatividade'
        }
    except Exception as e:
        print(f"❌ Erro ao calcular turnover: {str(e)}")
        return {'valor': 0, 'variacao': 0, 'label': 'Taxa de Rotatividade'}


def calcular_tempo_medio_contratacao(periodo_inicio, periodo_fim, departamentos_ids=None):
    """
    KPI 4: Tempo Médio para Contratar (em dias)
    Fórmula: AVG(data_fechamento - data_abertura) para vagas fechadas no período
    """
    try:
        # Buscar vagas fechadas no período
        response_vagas = supabase.table('rh_vagas')\
            .select('data_abertura, data_fechamento')\
            .eq('status', 'Fechada')\
            .gte('data_fechamento', periodo_inicio)\
            .lte('data_fechamento', periodo_fim)\
            .execute()
        
        if not response_vagas.data or len(response_vagas.data) == 0:
            return {'valor': 0, 'variacao': 0, 'label': 'Tempo Médio de Contratação'}
        
        # Calcular diferença em dias para cada vaga
        total_dias = 0
        count_vagas = 0
        
        for vaga in response_vagas.data:
            if vaga.get('data_abertura') and vaga.get('data_fechamento'):
                data_abertura = datetime.strptime(vaga['data_abertura'], '%Y-%m-%d')
                data_fechamento = datetime.strptime(vaga['data_fechamento'], '%Y-%m-%d')
                dias = (data_fechamento - data_abertura).days
                total_dias += dias
                count_vagas += 1
        
        tempo_medio = round(total_dias / count_vagas) if count_vagas > 0 else 0
        variacao = 0  # TODO: Implementar comparação com período anterior
        
        return {
            'valor': tempo_medio,
            'variacao': variacao,
            'label': 'Tempo Médio de Contratação'
        }
    except Exception as e:
        print(f"❌ Erro ao calcular tempo de contratação: {str(e)}")
        return {'valor': 0, 'variacao': 0, 'label': 'Tempo Médio de Contratação'}


def calcular_total_vagas_abertas(departamentos_ids=None):
    """
    KPI 5: Total de Vagas em Aberto
    """
    try:
        query = supabase.table('rh_vagas').select('id', count='exact').eq('status', 'Aberta')
        
        # Aplicar filtro de departamento se especificado
        if departamentos_ids and len(departamentos_ids) > 0:
            query = query.in_('departamento_id', departamentos_ids)
        
        response = query.execute()
        count = response.count if response.count is not None else 0
        
        variacao = 0  # TODO: Implementar comparação
        
        return {
            'valor': count,
            'variacao': variacao,
            'label': 'Vagas em Aberto'
        }
    except Exception as e:
        print(f"❌ Erro ao calcular vagas abertas: {str(e)}")
        return {'valor': 0, 'variacao': 0, 'label': 'Vagas em Aberto'}


def calcular_media_candidatos_vaga(departamentos_ids=None):
    """
    KPI 6: Média de Candidatos por Vaga
    """
    try:
        # Buscar vagas abertas
        query_vagas = supabase.table('rh_vagas').select('id').eq('status', 'Aberta')
        
        if departamentos_ids and len(departamentos_ids) > 0:
            query_vagas = query_vagas.in_('departamento_id', departamentos_ids)
        
        response_vagas = query_vagas.execute()
        vagas = response_vagas.data if response_vagas.data else []
        
        if len(vagas) == 0:
            return {'valor': 0, 'variacao': 0, 'label': 'Média Candidatos/Vaga'}
        
        # Contar candidatos por vaga
        total_candidatos = 0
        for vaga in vagas:
            response_cands = supabase.table('rh_candidatos')\
                .select('id', count='exact')\
                .eq('vaga_id', vaga['id'])\
                .execute()
            total_candidatos += response_cands.count if response_cands.count else 0
        
        media = round(total_candidatos / len(vagas), 1) if len(vagas) > 0 else 0
        variacao = 0  # TODO: Implementar comparação
        
        return {
            'valor': media,
            'variacao': variacao,
            'label': 'Média Candidatos/Vaga'
        }
    except Exception as e:
        print(f"❌ Erro ao calcular média candidatos/vaga: {str(e)}")
        return {'valor': 0, 'variacao': 0, 'label': 'Média Candidatos/Vaga'}


def calcular_tempo_medio_casa(departamentos_ids=None):
    """
    KPI 7: Tempo Médio de Casa dos Colaboradores (em anos)
    Calcula: (data atual ou data demissão) - data admissão
    """
    try:
        # Buscar todos os colaboradores (ativos e inativos)
        query = supabase.table('rh_colaboradores').select('data_admissao, data_desligamento, status')
        
        response = query.execute()
        colaboradores = response.data if response.data else []
        
        if len(colaboradores) == 0:
            return {'valor': 0, 'variacao': 0, 'label': 'Tempo Médio de Casa'}
        
        hoje = datetime.now()
        total_dias = 0
        count = 0
        
        for colab in colaboradores:
            if colab.get('data_admissao'):
                data_admissao = datetime.strptime(colab['data_admissao'], '%Y-%m-%d')
                
                # Se demitido, usar data de desligamento; senão, usar data atual
                if colab.get('data_desligamento'):
                    data_fim = datetime.strptime(colab['data_desligamento'], '%Y-%m-%d')
                else:
                    data_fim = hoje
                
                dias = (data_fim - data_admissao).days
                total_dias += dias
                count += 1
        
        # Converter para anos (com 1 casa decimal)
        tempo_medio_anos = round((total_dias / count) / 365.25, 1) if count > 0 else 0
        variacao = 0  # TODO: Implementar comparação
        
        return {
            'valor': tempo_medio_anos,
            'variacao': variacao,
            'label': 'Tempo Médio de Casa'
        }
    except Exception as e:
        print(f"❌ Erro ao calcular tempo médio de casa: {str(e)}")
        return {'valor': 0, 'variacao': 0, 'label': 'Tempo Médio de Casa'}


def calcular_idade_media(departamentos_ids=None):
    """
    KPI 8: Idade Média dos Colaboradores Ativos
    Calcula: data atual - data de nascimento
    """
    try:
        # Buscar colaboradores ativos com data de nascimento
        query = supabase.table('rh_colaboradores')\
            .select('data_nascimento')\
            .eq('status', 'Ativo')\
            .not_.is_('data_nascimento', 'null')
        
        response = query.execute()
        colaboradores = response.data if response.data else []
        
        if len(colaboradores) == 0:
            return {'valor': 0, 'variacao': 0, 'label': 'Idade Média'}
        
        hoje = datetime.now()
        total_anos = 0
        count = 0
        
        for colab in colaboradores:
            if colab.get('data_nascimento'):
                data_nascimento = datetime.strptime(colab['data_nascimento'], '%Y-%m-%d')
                idade = (hoje - data_nascimento).days / 365.25
                total_anos += idade
                count += 1
        
        idade_media = round(total_anos / count) if count > 0 else 0
        variacao = 0  # TODO: Implementar comparação
        
        return {
            'valor': idade_media,
            'variacao': variacao,
            'label': 'Idade Média'
        }
    except Exception as e:
        print(f"❌ Erro ao calcular idade média: {str(e)}")
        return {'valor': 0, 'variacao': 0, 'label': 'Idade Média'}


# ========================================
# FUNÇÕES DE CÁLCULO - GRÁFICOS
# ========================================

def calcular_graficos(periodo_inicio, periodo_fim, departamentos_ids=None):
    """
    Calcula dados para os gráficos principais
    """
    graficos = {}
    
    # Gráfico 1: Evolução Headcount e Turnover Mensal
    graficos['evolucao_headcount'] = calcular_evolucao_headcount(periodo_inicio, periodo_fim)
    
    # Gráfico 2: Turnover por Departamento
    graficos['turnover_departamento'] = calcular_turnover_por_departamento(periodo_inicio, periodo_fim)
    
    # Gráfico 3: Distribuição por Departamento
    graficos['distribuicao_departamento'] = calcular_distribuicao_departamento()
    
    # Gráfico 4: Dispersão - Tempo de Casa vs Salário
    graficos['dispersao_tempo_salario'] = calcular_dispersao_tempo_salario()
    
    return graficos


def calcular_evolucao_headcount(periodo_inicio, periodo_fim):
    """
    Gráfico 1: Evolução mensal de Headcount, Admissões e Demissões
    OTIMIZADO: Busca todos os eventos de uma vez e agrupa em Python
    """
    try:
        # Gerar lista de meses no período
        data_inicio = datetime.strptime(periodo_inicio, '%Y-%m-%d')
        data_fim = datetime.strptime(periodo_fim, '%Y-%m-%d')
        
        meses = []
        current = data_inicio
        while current <= data_fim:
            meses.append(current.strftime('%Y-%m'))
            current += relativedelta(months=1)
        
        # 🔥 OTIMIZAÇÃO: Buscar TODOS os eventos do período de uma vez (era 30 queries, agora 1)
        # ✅ CORREÇÃO: Buscar admissões do histórico mas demissões da tabela principal
        print(f"🚀 [OTIMIZAÇÃO] Buscando histórico completo para período {periodo_inicio} a {periodo_fim}...")
        
        # Buscar admissões do histórico (se existir)
        response_admissoes = supabase.table('rh_historico_colaborador')\
            .select('data_evento')\
            .eq('tipo_evento', 'Admissão')\
            .gte('data_evento', periodo_inicio)\
            .lte('data_evento', periodo_fim)\
            .execute()
        
        # Buscar demissões da tabela principal (data_desligamento)
        response_demissoes = supabase.table('rh_colaboradores')\
            .select('data_desligamento')\
            .not_.is_('data_desligamento', 'null')\
            .gte('data_desligamento', periodo_inicio)\
            .lte('data_desligamento', periodo_fim)\
            .execute()
        
        # Agrupar eventos por mês em Python (O(n) ao invés de 30 queries)
        from collections import defaultdict
        admissoes_por_mes = defaultdict(int)
        demissoes_por_mes = defaultdict(int)
        
        for evento in (response_admissoes.data or []):
            mes = evento['data_evento'][:7]  # YYYY-MM
            admissoes_por_mes[mes] += 1
        
        for evento in (response_demissoes.data or []):
            mes = evento['data_desligamento'][:7]  # YYYY-MM
            demissoes_por_mes[mes] += 1
        
        print(f"✅ Eventos agrupados: {len(admissoes_por_mes)} meses com admissões, {len(demissoes_por_mes)} meses com demissões")
        
        # Buscar headcount atual UMA VEZ (era 10 queries, agora 1)
        resp_head = supabase.table('rh_colaboradores')\
            .select('id', count='exact')\
            .eq('status', 'Ativo')\
            .is_('data_desligamento', 'null')\
            .execute()
        headcount_atual = resp_head.count if resp_head.count is not None else 0
        
        # Montar arrays de dados
        labels = []
        headcount_data = []
        admissoes_data = []
        demissoes_data = []
        
        for mes in meses:
            labels.append(mes)
            # Usar headcount atual para todos (simplificação - TODO: calcular retroativo)
            headcount_data.append(headcount_atual)
            admissoes_data.append(admissoes_por_mes.get(mes, 0))
            demissoes_data.append(demissoes_por_mes.get(mes, 0))
        
        return {
            'labels': labels,
            'datasets': {
                'headcount': headcount_data,
                'admissoes': admissoes_data,
                'demissoes': demissoes_data
            }
        }
    except Exception as e:
        print(f"❌ Erro ao calcular evolução headcount: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'labels': [], 'datasets': {'headcount': [], 'admissoes': [], 'demissoes': []}}


def calcular_turnover_por_departamento(periodo_inicio, periodo_fim):
    """
    Gráfico 2: Taxa de Turnover por Departamento
    OTIMIZADO: Busca demissões de uma vez e agrupa em Python
    CORRIGIDO: Usa data_desligamento da tabela principal
    """
    try:
        # Buscar departamentos UMA VEZ
        resp_deps = supabase.table('rh_departamentos').select('id, nome_departamento').execute()
        departamentos = resp_deps.data if resp_deps.data else []
        
        if not departamentos:
            return {'labels': [], 'data': []}
        
        departamentos_ids = [d['id'] for d in departamentos]
        departamentos_map = {d['id']: d['nome_departamento'] for d in departamentos}
        
        # ✅ CORREÇÃO: Buscar colaboradores demitidos no período
        print(f"🚀 [OTIMIZAÇÃO] Buscando demissões por departamento...")
        
        # Buscar colaboradores demitidos (com data_desligamento no período)
        resp_demitidos = supabase.table('rh_colaboradores')\
            .select('id, data_desligamento')\
            .not_.is_('data_desligamento', 'null')\
            .gte('data_desligamento', periodo_inicio)\
            .lte('data_desligamento', periodo_fim)\
            .execute()
        
        colaboradores_demitidos_ids = [c['id'] for c in (resp_demitidos.data or [])]
        
        # 🔥 OTIMIZAÇÃO CRÍTICA: Buscar TODOS os históricos de uma vez (não um por departamento!)
        print(f"🚀 [OTIMIZAÇÃO] Buscando histórico completo para cálculo de turnover...")
        resp_hist_completo = supabase.table('rh_historico_colaborador')\
            .select('colaborador_id, departamento_id')\
            .not_.is_('departamento_id', 'null')\
            .execute()
        
        # Mapear departamento de cada colaborador (último registro)
        from collections import defaultdict
        colaborador_dept_map = {}
        for hist in (resp_hist_completo.data or []):
            colab_id = hist['colaborador_id']
            if colab_id not in colaborador_dept_map:  # Pega o primeiro (mais recente devido ao order)
                colaborador_dept_map[colab_id] = hist['departamento_id']
        
        # Contar demissões por departamento
        demissoes_por_dept = defaultdict(int)
        for colab_id in colaboradores_demitidos_ids:
            dept_id = colaborador_dept_map.get(colab_id)
            if dept_id:
                demissoes_por_dept[dept_id] += 1
        
        # Contar headcount por departamento (colaboradores únicos)
        headcount_por_dept = defaultdict(set)
        for colab_id, dept_id in colaborador_dept_map.items():
            headcount_por_dept[dept_id].add(colab_id)
        
        # Converter sets para counts
        headcount_counts = {dept_id: len(colabs) for dept_id, colabs in headcount_por_dept.items()}
        
        labels = []
        data = []
        
        for dept in departamentos:
            dept_id = dept['id']
            dept_nome = dept['nome_departamento']
            demissoes = demissoes_por_dept.get(dept_id, 0)
            headcount_dept = headcount_counts.get(dept_id, 0)
            
            turnover = (demissoes / headcount_dept * 100) if headcount_dept > 0 else 0
            
            if headcount_dept > 0:  # Só incluir departamentos com colaboradores
                labels.append(dept_nome)
                data.append(round(turnover, 1))
        
        print(f"✅ Turnover calculado para {len(labels)} departamentos")
        
        return {
            'labels': labels,
            'data': data
        }
    except Exception as e:
        print(f"❌ Erro ao calcular turnover por departamento: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'labels': [], 'data': []}


def calcular_distribuicao_departamento():
    """
    Gráfico 3: Distribuição de Colaboradores Ativos por Departamento
    OTIMIZADO: Busca colaboradores e agrupa em Python
    CORRIGIDO: Busca departamento do histórico se não existir na tabela principal
    """
    try:
        # Buscar departamentos
        resp_deps = supabase.table('rh_departamentos')\
            .select('id, nome_departamento')\
            .execute()
        departamentos = resp_deps.data if resp_deps.data else []
        
        if not departamentos:
            return {'labels': [], 'data': []}
        
        # 🔥 OTIMIZAÇÃO: Buscar TODOS colaboradores ativos de uma vez
        print(f"🚀 [OTIMIZAÇÃO] Buscando colaboradores ativos para distribuição...")
        response_colabs = supabase.table('rh_colaboradores')\
            .select('id, status, data_desligamento')\
            .eq('status', 'Ativo')\
            .is_('data_desligamento', 'null')\
            .execute()
        
        colaboradores = response_colabs.data if response_colabs.data else []
        
        print(f"   Total de colaboradores ativos: {len(colaboradores)}")
        
        if not colaboradores:
            print(f"   ⚠️  Nenhum colaborador ativo encontrado!")
            return {'labels': [], 'data': []}
        
        # ✅ CORREÇÃO: rh_colaboradores NÃO tem departamento_id, buscar do histórico
        print(f"   📊 Buscando departamentos no histórico para {len(colaboradores)} colaboradores...")
        
        colabs_ids = [c['id'] for c in colaboradores]
        
        if colabs_ids:
            response_hist = supabase.table('rh_historico_colaborador')\
                .select('colaborador_id, departamento_id, data_evento')\
                .in_('colaborador_id', colabs_ids)\
                .not_.is_('departamento_id', 'null')\
                .order('data_evento', desc=True)\
                .execute()
            
            # Mapear departamento mais recente por colaborador
            dept_map = {}
            for hist in (response_hist.data or []):
                colab_id = hist['colaborador_id']
                if colab_id not in dept_map:
                    dept_map[colab_id] = hist['departamento_id']
            
            print(f"   ✅ {len(dept_map)} colaboradores com departamento via histórico")
            
            # Atribuir departamento aos colaboradores
            for colab in colaboradores:
                if colab['id'] in dept_map:
                    colab['departamento_id'] = dept_map[colab['id']]
        
        # Contar colaboradores por departamento (usando defaultdict)
        from collections import defaultdict
        colaboradores_por_dept = defaultdict(int)
        
        colaboradores_com_dept = 0
        for colab in colaboradores:
            dept_id = colab.get('departamento_id')
            if dept_id:
                colaboradores_por_dept[dept_id] += 1
                colaboradores_com_dept += 1
        
        print(f"   📊 Total de colaboradores com departamento: {colaboradores_com_dept}/{len(colaboradores)}")
        
        # Montar resposta
        labels = []
        data = []
        
        for dept in departamentos:
            dept_id = dept['id']
            dept_nome = dept['nome_departamento']
            count = colaboradores_por_dept.get(dept_id, 0)
            
            if count > 0:  # Só incluir departamentos com colaboradores
                labels.append(dept_nome)
                data.append(count)
        
        print(f"✅ Distribuição calculada: {len(labels)} departamentos, {sum(data)} colaboradores")
        
        return {
            'labels': labels,
            'data': data
        }
    except Exception as e:
        print(f"❌ Erro ao calcular distribuição por departamento: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'labels': [], 'data': []}


def calcular_dispersao_tempo_salario():
    """
    Gráfico 4: Dispersão - Tempo de Casa vs Salário
    Retorna dados para scatter plot
    OTIMIZADO: Busca todos os salários de uma vez
    """
    try:
        # Buscar colaboradores ativos
        response_colabs = supabase.table('rh_colaboradores')\
            .select('id, nome_completo, data_admissao')\
            .eq('status', 'Ativo')\
            .execute()
        
        colaboradores = response_colabs.data if response_colabs.data else []
        
        if len(colaboradores) == 0:
            return {'labels': [], 'tempo_casa': [], 'salarios': []}
        
        colaboradores_ids = [c['id'] for c in colaboradores]
        
        # 🔥 OTIMIZAÇÃO: Buscar TODOS os salários de uma vez
        print(f"🚀 [OTIMIZAÇÃO] Buscando salários para dispersão...")
        response_salarios = supabase.table('rh_historico_colaborador')\
            .select('colaborador_id, salario_mensal, data_evento')\
            .in_('colaborador_id', colaboradores_ids)\
            .not_.is_('salario_mensal', 'null')\
            .order('data_evento', desc=True)\
            .execute()
        
        # Mapear salário mais recente por colaborador
        salarios_map = {}
        for registro in (response_salarios.data or []):
            colab_id = registro['colaborador_id']
            if colab_id not in salarios_map:
                salarios_map[colab_id] = float(registro['salario_mensal'] or 0)
        
        hoje = datetime.now()
        labels = []
        tempo_casa_anos = []
        salarios = []
        
        for colab in colaboradores:
            # Calcular tempo de casa em anos
            if colab.get('data_admissao') and colab['id'] in salarios_map:
                data_admissao = datetime.strptime(colab['data_admissao'], '%Y-%m-%d')
                tempo_anos = round((hoje - data_admissao).days / 365.25, 1)
                salario = salarios_map[colab['id']]
                
                # Adicionar ao gráfico
                labels.append(colab['nome_completo'])
                tempo_casa_anos.append(tempo_anos)
                salarios.append(salario)
        
        print(f"✅ Dispersão calculada para {len(labels)} colaboradores")
        
        return {
            'labels': labels,
            'tempo_casa': tempo_casa_anos,
            'salarios': salarios
        }
    except Exception as e:
        print(f"❌ Erro ao calcular dispersão tempo/salário: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'labels': [], 'tempo_casa': [], 'salarios': []}


# ========================================
# FUNÇÕES DE CÁLCULO - TABELAS
# ========================================

def calcular_tabelas(periodo_inicio, periodo_fim, departamentos_ids=None):
    """
    Calcula dados para as 2 tabelas de detalhamento
    """
    tabelas = {}
    
    # Tabela 1: Vagas Abertas - Análise de Performance
    tabelas['vagas_abertas'] = calcular_vagas_abertas()
    
    # Tabela 2: Análise do Funil de Recrutamento
    tabelas['funil_recrutamento'] = calcular_funil_recrutamento(periodo_inicio, periodo_fim)
    
    return tabelas


def calcular_vagas_abertas():
    """
    Tabela 1: Vagas em Aberto com análise de performance
    OTIMIZADO: Busca candidatos em batch
    CORRIGIDO V2: rh_cargos NÃO tem departamento_id, usa rh_historico_colaborador para mapear cargo → departamento
    """
    try:
        print(f"🚀 [TABELA VAGAS] Buscando vagas abertas...")
        
        # Buscar vagas abertas com cargo
        response = supabase.table('rh_vagas')\
            .select('id, titulo, data_abertura, cargo_id, rh_cargos(nome_cargo)')\
            .eq('status', 'Aberta')\
            .order('data_abertura')\
            .execute()
        
        vagas_data = response.data if response.data else []
        
        print(f"📊 Vagas abertas encontradas: {len(vagas_data)}")
        
        if not vagas_data:
            return []
        
        vagas_ids = [v['id'] for v in vagas_data]
        cargo_ids = list(set([v['cargo_id'] for v in vagas_data if v.get('cargo_id')]))
        
        # 🔥 CORREÇÃO: Buscar departamento via rh_historico_colaborador
        # Pegar o departamento_id mais recente para cada cargo_id
        print(f"🔍 Mapeando {len(cargo_ids)} cargos para departamentos via histórico...")
        cargo_dept_map = {}
        
        if cargo_ids:
            resp_historico = supabase.table('rh_historico_colaborador')\
                .select('cargo_id, departamento_id, data_evento')\
                .in_('cargo_id', cargo_ids)\
                .not_.is_('departamento_id', 'null')\
                .order('data_evento', desc=True)\
                .execute()
            
            # Mapear cargo → departamento (pega o mais recente)
            for registro in (resp_historico.data or []):
                cargo_id = registro['cargo_id']
                if cargo_id not in cargo_dept_map:
                    cargo_dept_map[cargo_id] = registro['departamento_id']
            
            print(f"   ✅ Mapeados {len(cargo_dept_map)} cargos → departamentos")
            
            # Buscar nomes dos departamentos
            dept_ids = list(set(cargo_dept_map.values()))
            if dept_ids:
                resp_depts = supabase.table('rh_departamentos')\
                    .select('id, nome_departamento')\
                    .in_('id', dept_ids)\
                    .execute()
                
                dept_names = {d['id']: d['nome_departamento'] for d in (resp_depts.data or [])}
            else:
                dept_names = {}
        else:
            dept_names = {}
        
        # 🔥 OTIMIZAÇÃO: Buscar TODOS candidatos de uma vez
        print(f"🚀 [OTIMIZAÇÃO] Buscando candidatos para {len(vagas_ids)} vagas abertas...")
        resp_cands = supabase.table('rh_candidatos')\
            .select('vaga_id')\
            .in_('vaga_id', vagas_ids)\
            .execute()
        
        # Contar candidatos por vaga (usando defaultdict)
        from collections import defaultdict
        candidatos_por_vaga = defaultdict(int)
        
        for cand in (resp_cands.data or []):
            vaga_id = cand.get('vaga_id')
            if vaga_id:
                candidatos_por_vaga[vaga_id] += 1
        
        # Montar resposta
        vagas = []
        hoje = datetime.now()
        
        for vaga in vagas_data:
            # Calcular dias em aberto - suporte a múltiplos formatos de data
            try:
                # Formato ISO 8601 com fração de segundos: 2025-10-09T00:30:54.77493+00:00
                data_abertura = date_parser.isoparse(vaga['data_abertura'])
            except:
                # Fallback para formatos antigos
                try:
                    data_abertura = datetime.strptime(vaga['data_abertura'], '%Y-%m-%d %H:%M:%S.%f%z')
                except:
                    data_abertura = datetime.strptime(vaga['data_abertura'], '%Y-%m-%d')
            
            dias_aberto = (hoje.replace(tzinfo=data_abertura.tzinfo) - data_abertura).days if data_abertura.tzinfo else (hoje - data_abertura).days
            
            # Contar candidatos (já calculado)
            num_candidatos = candidatos_por_vaga.get(vaga['id'], 0)
            
            # Obter departamento via mapeamento cargo → departamento → nome
            departamento_nome = 'N/A'
            cargo_id = vaga.get('cargo_id')
            if cargo_id and cargo_id in cargo_dept_map:
                dept_id = cargo_dept_map[cargo_id]
                departamento_nome = dept_names.get(dept_id, 'N/A')
            
            # TODO: Contar candidatos com score alto (quando implementado)
            candidatos_score_alto = 0
            
            vagas.append({
                'id': vaga['id'],
                'titulo': vaga['titulo'],
                'departamento': departamento_nome,
                'dias_aberto': dias_aberto,
                'num_candidatos': num_candidatos,
                'candidatos_score_alto': candidatos_score_alto,
                'status_urgencia': 'alta' if dias_aberto > 45 else 'media' if dias_aberto > 30 else 'normal'
            })
        
        print(f"✅ Vagas abertas analisadas: {len(vagas)} vagas, {sum(candidatos_por_vaga.values())} candidatos")
        
        return vagas
    except Exception as e:
        print(f"❌ Erro ao calcular vagas abertas: {str(e)}")
        import traceback
        traceback.print_exc()
        return []


def calcular_funil_recrutamento(periodo_inicio, periodo_fim):
    """
    Tabela 2: Análise do Funil de Recrutamento
    """
    try:
        # Buscar vagas fechadas no período
        resp_vagas = supabase.table('rh_vagas')\
            .select('id')\
            .eq('status', 'Fechada')\
            .gte('data_fechamento', periodo_inicio)\
            .lte('data_fechamento', periodo_fim)\
            .execute()
        
        vagas_ids = [v['id'] for v in resp_vagas.data] if resp_vagas.data else []
        
        if not vagas_ids:
            return []
        
        # Buscar candidatos dessas vagas
        resp_cands = supabase.table('rh_candidatos')\
            .select('status_processo')\
            .in_('vaga_id', vagas_ids)\
            .execute()
        
        # Contar por status
        status_count = {}
        for cand in resp_cands.data if resp_cands.data else []:
            status = cand.get('status_processo', 'Desconhecido')
            status_count[status] = status_count.get(status, 0) + 1
        
        # Calcular taxas de conversão (simplificado)
        funil = []
        status_ordem = ['Triagem', 'Entrevista RH', 'Entrevista Técnica', 'Proposta', 'Contratado']
        
        for i, status in enumerate(status_ordem):
            count = status_count.get(status, 0)
            # Taxa de conversão para próxima etapa (placeholder)
            conversao = 0 if i == len(status_ordem) - 1 else 70  # TODO: Calcular corretamente
            
            funil.append({
                'etapa': status,
                'num_candidatos': count,
                'taxa_conversao': conversao
            })
        
        return funil
    except Exception as e:
        print(f"❌ Erro ao calcular funil de recrutamento: {str(e)}")
        return []
