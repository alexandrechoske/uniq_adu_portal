"""
Rotas - Dashboard Executivo RH
Endpoints para visualização de indicadores executivos de RH
"""

from flask import render_template, jsonify, request
from modules.auth.routes import login_required
from . import dashboard_rh_bp
from extensions import supabase_admin as supabase
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# ========================================
# PÁGINAS HTML
# ========================================

@dashboard_rh_bp.route('/')
@login_required
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
    """
    kpis = {}
    
    # KPI 1: Headcount Ativo
    kpis['headcount'] = calcular_headcount_ativo(departamentos_ids)
    
    # KPI 2: Massa Salarial Mensal
    kpis['massa_salarial'] = calcular_massa_salarial(departamentos_ids)
    
    # KPI 3: Turnover Anualizado
    kpis['turnover'] = calcular_turnover(periodo_inicio, periodo_fim, departamentos_ids)
    
    # KPI 4: Tempo Médio de Contratação
    kpis['tempo_contratacao'] = calcular_tempo_medio_contratacao(periodo_inicio, periodo_fim, departamentos_ids)
    
    # KPI 5: Total de Vagas em Aberto
    kpis['vagas_abertas'] = calcular_total_vagas_abertas(departamentos_ids)
    
    # KPI 6: Média de Candidatos por Vaga
    kpis['media_candidatos_vaga'] = calcular_media_candidatos_vaga(departamentos_ids)
    
    # KPI 7: Tempo Médio de Casa
    kpis['tempo_medio_casa'] = calcular_tempo_medio_casa(departamentos_ids)
    
    # KPI 8: Idade Média dos Colaboradores
    kpis['idade_media'] = calcular_idade_media(departamentos_ids)
    
    return kpis


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
        
        # Calcular para cada mês
        labels = []
        headcount_data = []
        admissoes_data = []
        demissoes_data = []
        
        for mes in meses:
            mes_inicio = f"{mes}-01"
            mes_fim = datetime.strptime(mes_inicio, '%Y-%m-%d') + relativedelta(months=1) - timedelta(days=1)
            mes_fim_str = mes_fim.strftime('%Y-%m-%d')
            
            # Contar admissões
            resp_adm = supabase.table('rh_historico_colaborador')\
                .select('id', count='exact')\
                .eq('tipo_evento', 'Admissão')\
                .gte('data_evento', mes_inicio)\
                .lte('data_evento', mes_fim_str)\
                .execute()
            admissoes = resp_adm.count if resp_adm.count is not None else 0
            
            # Contar demissões
            resp_dem = supabase.table('rh_historico_colaborador')\
                .select('id', count='exact')\
                .eq('tipo_evento', 'Demissão')\
                .gte('data_evento', mes_inicio)\
                .lte('data_evento', mes_fim_str)\
                .execute()
            demissoes = resp_dem.count if resp_dem.count is not None else 0
            
            # Headcount (simplificado - usar atual para todos)
            resp_head = supabase.table('rh_colaboradores').select('id', count='exact').eq('status', 'Ativo').execute()
            headcount = resp_head.count if resp_head.count is not None else 0
            
            labels.append(mes)
            headcount_data.append(headcount)
            admissoes_data.append(admissoes)
            demissoes_data.append(demissoes)
        
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
        return {'labels': [], 'datasets': {'headcount': [], 'admissoes': [], 'demissoes': []}}


def calcular_turnover_por_departamento(periodo_inicio, periodo_fim):
    """
    Gráfico 2: Taxa de Turnover por Departamento
    """
    try:
        # Buscar departamentos
        resp_deps = supabase.table('rh_departamentos').select('id, nome_departamento').execute()
        departamentos = resp_deps.data if resp_deps.data else []
        
        labels = []
        data = []
        
        for dept in departamentos:
            dept_id = dept['id']
            dept_nome = dept['nome_departamento']
            
            # Contar demissões do departamento
            resp_dem = supabase.table('rh_historico_colaborador')\
                .select('id', count='exact')\
                .eq('tipo_evento', 'Demissão')\
                .eq('departamento_id', dept_id)\
                .gte('data_evento', periodo_inicio)\
                .lte('data_evento', periodo_fim)\
                .execute()
            demissoes = resp_dem.count if resp_dem.count is not None else 0
            
            # Headcount do departamento (simplificado)
            # TODO: Implementar contagem correta por departamento
            headcount_dept = 10  # Placeholder
            
            turnover = (demissoes / headcount_dept * 100) if headcount_dept > 0 else 0
            
            labels.append(dept_nome)
            data.append(round(turnover, 1))
        
        return {
            'labels': labels,
            'data': data
        }
    except Exception as e:
        print(f"❌ Erro ao calcular turnover por departamento: {str(e)}")
        return {'labels': [], 'data': []}


def calcular_distribuicao_departamento():
    """
    Gráfico 3: Distribuição de Colaboradores Ativos por Departamento
    """
    try:
        # Buscar departamentos
        resp_deps = supabase.table('rh_departamentos').select('id, nome_departamento').execute()
        departamentos = resp_deps.data if resp_deps.data else []
        
        labels = []
        data = []
        
        for dept in departamentos:
            dept_id = dept['id']
            dept_nome = dept['nome_departamento']
            
            # TODO: Implementar contagem correta por departamento
            # Por enquanto, placeholder
            count = 5
            
            labels.append(dept_nome)
            data.append(count)
        
        return {
            'labels': labels,
            'data': data
        }
    except Exception as e:
        print(f"❌ Erro ao calcular distribuição por departamento: {str(e)}")
        return {'labels': [], 'data': []}


def calcular_dispersao_tempo_salario():
    """
    Gráfico 4: Dispersão - Tempo de Casa vs Salário
    Retorna dados para scatter plot
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
        
        hoje = datetime.now()
        labels = []
        tempo_casa_anos = []
        salarios = []
        
        for colab in colaboradores:
            # Calcular tempo de casa em anos
            if colab.get('data_admissao'):
                data_admissao = datetime.strptime(colab['data_admissao'], '%Y-%m-%d')
                tempo_anos = round((hoje - data_admissao).days / 365.25, 1)
                
                # Buscar salário mais recente
                resp_hist = supabase.table('rh_historico_colaborador')\
                    .select('salario_mensal')\
                    .eq('colaborador_id', colab['id'])\
                    .not_.is_('salario_mensal', 'null')\
                    .order('data_evento', desc=True)\
                    .limit(1)\
                    .execute()
                
                if resp_hist.data and len(resp_hist.data) > 0:
                    salario = float(resp_hist.data[0].get('salario_mensal', 0))
                    
                    # Adicionar ao gráfico
                    labels.append(colab['nome_completo'])
                    tempo_casa_anos.append(tempo_anos)
                    salarios.append(salario)
        
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
    """
    try:
        # Buscar vagas abertas
        response = supabase.table('rh_vagas')\
            .select('id, titulo, data_abertura, departamento_id, rh_departamentos(nome_departamento)')\
            .eq('status', 'Aberta')\
            .order('data_abertura')\
            .execute()
        
        vagas = []
        hoje = datetime.now()
        
        for vaga in response.data if response.data else []:
            # Calcular dias em aberto
            data_abertura = datetime.strptime(vaga['data_abertura'], '%Y-%m-%d')
            dias_aberto = (hoje - data_abertura).days
            
            # Contar candidatos
            resp_cands = supabase.table('rh_candidatos')\
                .select('id', count='exact')\
                .eq('vaga_id', vaga['id'])\
                .execute()
            num_candidatos = resp_cands.count if resp_cands.count is not None else 0
            
            # TODO: Contar candidatos com score alto (quando implementado)
            candidatos_score_alto = 0
            
            vagas.append({
                'id': vaga['id'],
                'titulo': vaga['titulo'],
                'departamento': vaga['rh_departamentos']['nome_departamento'] if vaga.get('rh_departamentos') else 'N/A',
                'dias_aberto': dias_aberto,
                'num_candidatos': num_candidatos,
                'candidatos_score_alto': candidatos_score_alto,
                'status_urgencia': 'alta' if dias_aberto > 45 else 'media' if dias_aberto > 30 else 'normal'
            })
        
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
