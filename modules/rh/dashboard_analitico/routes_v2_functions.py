# -*- coding: utf-8 -*-
"""
Funções de Cálculo - Dashboard Analítico V2.0
Seção 1: Recrutamento & Seleção
Seção 2: Turnover & Retenção
"""

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from collections import defaultdict
from extensions import supabase


# ========================================
# SEÇÃO 1 E 2: FUNÇÕES PRINCIPAIS
# ========================================

def calcular_secao_recrutamento(periodo_inicio, periodo_fim, departamentos_ids=None, cargos_ids=None):
    """
    Calcula todos os dados da Seção 1: Recrutamento & Seleção
    
    Retorna:
    {
        'kpis': {...},
        'graficos': {...},
        'tabelas': {...}
    }
    """
    print("📊 [SEÇÃO 1] Calculando Recrutamento & Seleção...")
    
    # KPIs
    kpis = {
        'tempo_medio_contratacao': calcular_tempo_medio_contratacao_v2(periodo_inicio, periodo_fim, cargos_ids),
        'vagas_abertas': calcular_vagas_abertas_v2(),
        'vagas_fechadas': calcular_vagas_fechadas_v2(periodo_inicio, periodo_fim),
        'vagas_canceladas': calcular_vagas_canceladas_v2(periodo_inicio, periodo_fim)
    }
    
    # Gráficos
    graficos = {
        'tempo_por_cargo': calcular_tempo_contratacao_por_cargo_v2(periodo_inicio, periodo_fim),
        'tempo_por_departamento': calcular_tempo_contratacao_por_departamento_v2(periodo_inicio, periodo_fim),
        'evolucao_vagas': calcular_evolucao_vagas_v2(periodo_inicio, periodo_fim)
    }
    
    # Tabelas
    tabelas = {
        'vagas_abertas': calcular_tabela_vagas_abertas_v2()
    }
    
    print("✅ [SEÇÃO 1] Recrutamento calculado com sucesso!")
    return {
        'kpis': kpis,
        'graficos': graficos,
        'tabelas': tabelas
    }


def calcular_secao_turnover(periodo_inicio, periodo_fim, departamentos_ids=None, cargos_ids=None, status_filter='todos'):
    """
    Calcula todos os dados da Seção 2: Turnover & Retenção
    
    Retorna:
    {
        'kpis': {...},
        'graficos': {...},
        'tabelas': {...}
    }
    """
    print("🔄 [SEÇÃO 2] Calculando Turnover & Retenção...")
    
    # KPIs
    kpis = {
        'turnover_geral': calcular_turnover_geral_v2(periodo_inicio, periodo_fim),
        'desligamentos': calcular_total_desligamentos_v2(periodo_inicio, periodo_fim, departamentos_ids, cargos_ids),
        'admissoes': calcular_total_admissoes_v2(periodo_inicio, periodo_fim, departamentos_ids, cargos_ids),
        'tempo_medio_permanencia': calcular_tempo_medio_permanencia_v2(),
        'saldo_liquido': 0,  # Calculado depois
        'headcount_atual': calcular_headcount_atual_v2()
    }
    
    # Calcular saldo líquido
    kpis['saldo_liquido'] = kpis['admissoes'] - kpis['desligamentos']
    
    # Gráficos
    graficos = {
        'turnover_por_departamento': calcular_turnover_por_departamento_v2(periodo_inicio, periodo_fim),
        'turnover_por_cargo': calcular_turnover_por_cargo_v2(periodo_inicio, periodo_fim),
        'desligamentos_por_tempo_casa': calcular_desligamentos_por_tempo_casa_v2(periodo_inicio, periodo_fim),
        'turnover_por_faixa_etaria': calcular_turnover_por_faixa_etaria_v2(periodo_inicio, periodo_fim),
        'evolucao_turnover': calcular_evolucao_turnover_v2(periodo_inicio, periodo_fim)
    }
    
    # Tabelas
    tabelas = {
        'desligamentos_recentes': calcular_tabela_desligamentos_recentes_v2()
    }
    
    print("✅ [SEÇÃO 2] Turnover calculado com sucesso!")
    return {
        'kpis': kpis,
        'graficos': graficos,
        'tabelas': tabelas
    }


# ========================================
# SEÇÃO 1: RECRUTAMENTO - FUNÇÕES AUXILIARES
# ========================================

def calcular_tempo_medio_contratacao_v2(periodo_inicio, periodo_fim, cargos_ids=None):
    """KPI: Tempo Médio de Contratação em dias"""
    try:
        query = supabase.table('rh_vagas')\
            .select('data_abertura, data_fechamento')\
            .eq('status', 'Fechada')\
            .gte('data_fechamento', periodo_inicio)\
            .lte('data_fechamento', periodo_fim)
        
        response = query.execute()
        vagas = response.data if response.data else []
        
        if not vagas:
            return 0
        
        tempos = []
        for vaga in vagas:
            if vaga.get('data_abertura') and vaga.get('data_fechamento'):
                abertura = datetime.strptime(vaga['data_abertura'][:10], '%Y-%m-%d')
                fechamento = datetime.strptime(vaga['data_fechamento'][:10], '%Y-%m-%d')
                dias = (fechamento - abertura).days
                if dias > 0:
                    tempos.append(dias)
        
        if not tempos:
            return 0
        
        media = sum(tempos) / len(tempos)
        return round(media, 1)
        
    except Exception as e:
        print(f"❌ Erro ao calcular tempo médio de contratação: {str(e)}")
        return 0


def calcular_vagas_abertas_v2():
    """KPI: Total de Vagas Abertas no momento"""
    try:
        response = supabase.table('rh_vagas')\
            .select('id', count='exact')\
            .eq('status', 'Aberta')\
            .execute()
        
        return response.count if response.count else 0
        
    except Exception as e:
        print(f"❌ Erro ao calcular vagas abertas: {str(e)}")
        return 0


def calcular_vagas_fechadas_v2(periodo_inicio, periodo_fim):
    """KPI: Total de Vagas Fechadas no período"""
    try:
        response = supabase.table('rh_vagas')\
            .select('id', count='exact')\
            .eq('status', 'Fechada')\
            .gte('data_fechamento', periodo_inicio)\
            .lte('data_fechamento', periodo_fim)\
            .execute()
        
        return response.count if response.count else 0
        
    except Exception as e:
        print(f"❌ Erro ao calcular vagas fechadas: {str(e)}")
        return 0


def calcular_vagas_canceladas_v2(periodo_inicio, periodo_fim):
    """KPI: Total de Vagas Canceladas no período"""
    try:
        response = supabase.table('rh_vagas')\
            .select('id', count='exact')\
            .eq('status', 'Cancelada')\
            .gte('data_fechamento', periodo_inicio)\
            .lte('data_fechamento', periodo_fim)\
            .execute()
        
        return response.count if response.count else 0
        
    except Exception as e:
        print(f"❌ Erro ao calcular vagas canceladas: {str(e)}")
        return 0


def calcular_tempo_contratacao_por_cargo_v2(periodo_inicio, periodo_fim):
    """Gráfico: Tempo Médio de Contratação por Cargo (Barras Horizontais)"""
    try:
        # Buscar vagas fechadas no período
        response = supabase.table('rh_vagas')\
            .select('cargo_id, data_abertura, data_fechamento')\
            .eq('status', 'Fechada')\
            .gte('data_fechamento', periodo_inicio)\
            .lte('data_fechamento', periodo_fim)\
            .execute()
        
        vagas = response.data if response.data else []
        
        # Buscar cargos
        response_cargos = supabase.table('rh_cargos')\
            .select('id, nome_cargo')\
            .execute()
        cargos_map = {c['id']: c['nome_cargo'] for c in (response_cargos.data or [])}
        
        # Agrupar por cargo
        cargo_tempos = defaultdict(list)
        for vaga in vagas:
            if vaga.get('data_abertura') and vaga.get('data_fechamento') and vaga.get('cargo_id'):
                abertura = datetime.strptime(vaga['data_abertura'][:10], '%Y-%m-%d')
                fechamento = datetime.strptime(vaga['data_fechamento'][:10], '%Y-%m-%d')
                dias = (fechamento - abertura).days
                if dias > 0:
                    cargo_tempos[vaga['cargo_id']].append(dias)
        
        # Calcular médias
        cargo_medias = []
        for cargo_id, tempos in cargo_tempos.items():
            cargo_medias.append({
                'cargo': cargos_map.get(cargo_id, 'Desconhecido'),
                'media': sum(tempos) / len(tempos)
            })
        
        # Ordenar por média DESC e pegar Top 10
        cargo_medias_sorted = sorted(cargo_medias, key=lambda x: x['media'], reverse=True)[:10]
        
        return {
            'labels': [c['cargo'] for c in cargo_medias_sorted],
            'values': [round(c['media'], 1) for c in cargo_medias_sorted]
        }
        
    except Exception as e:
        print(f"❌ Erro ao calcular tempo por cargo: {str(e)}")
        return {'labels': [], 'values': []}


def calcular_tempo_contratacao_por_departamento_v2(periodo_inicio, periodo_fim):
    """Gráfico: Tempo Médio de Contratação por Departamento"""
    try:
        # TODO: Implementar lógica para vincular vaga -> departamento
        # Por enquanto, retornar dados mock
        return {
            'labels': ['Importação', 'Exportação', 'Financeiro'],
            'values': [45, 38, 52]
        }
        
    except Exception as e:
        print(f"❌ Erro ao calcular tempo por departamento: {str(e)}")
        return {'labels': [], 'values': []}


def calcular_evolucao_vagas_v2(periodo_inicio, periodo_fim):
    """Gráfico: Evolução de Vagas no Tempo (Linha)"""
    try:
        # Gerar meses do período
        inicio = datetime.strptime(periodo_inicio, '%Y-%m-%d')
        fim = datetime.strptime(periodo_fim, '%Y-%m-%d')
        
        meses = []
        current = inicio
        while current <= fim:
            meses.append(current.strftime('%Y-%m'))
            current += relativedelta(months=1)
        
        # TODO: Implementar contagem real por mês
        # Por enquanto, retornar dados mock
        return {
            'labels': [m.split('-')[1] + '/' + m.split('-')[0][2:] for m in meses[-6:]],
            'abertas': [3, 5, 4, 6, 2, 4],
            'fechadas': [2, 3, 3, 4, 5, 3],
            'canceladas': [0, 1, 0, 0, 1, 0]
        }
        
    except Exception as e:
        print(f"❌ Erro ao calcular evolução de vagas: {str(e)}")
        return {'labels': [], 'abertas': [], 'fechadas': [], 'canceladas': []}


def calcular_tabela_vagas_abertas_v2():
    """Tabela: Vagas em Aberto (Operacional)"""
    try:
        response = supabase.table('rh_vagas')\
            .select('id, titulo, cargo_id, data_abertura')\
            .eq('status', 'Aberta')\
            .order('data_abertura', desc=False)\
            .execute()
        
        vagas = response.data if response.data else []
        
        # Buscar cargos
        response_cargos = supabase.table('rh_cargos')\
            .select('id, nome_cargo')\
            .execute()
        cargos_map = {c['id']: c['nome_cargo'] for c in (response_cargos.data or [])}
        
        hoje = datetime.now()
        vagas_tabela = []
        
        for vaga in vagas:
            if vaga.get('data_abertura'):
                abertura = datetime.strptime(vaga['data_abertura'][:10], '%Y-%m-%d')
                dias_aberto = (hoje - abertura).days
                
                vagas_tabela.append({
                    'id': vaga['id'],
                    'titulo': vaga.get('titulo', 'Sem título'),
                    'cargo': cargos_map.get(vaga.get('cargo_id'), 'Não especificado'),
                    'departamento': 'N/A',  # TODO: Implementar vínculo
                    'data_abertura': abertura.strftime('%Y-%m-%d'),
                    'dias_aberto': dias_aberto
                })
        
        return vagas_tabela
        
    except Exception as e:
        print(f"❌ Erro ao calcular tabela de vagas abertas: {str(e)}")
        return []


# ========================================
# SEÇÃO 2: TURNOVER - FUNÇÕES AUXILIARES
# ========================================

def calcular_turnover_geral_v2(periodo_inicio, periodo_fim):
    """KPI: Turnover Geral (%) nos últimos 12 meses"""
    try:
        # Calcular 12 meses atrás
        hoje = datetime.now()
        um_ano_atras = hoje - relativedelta(months=12)
        
        # Desligamentos nos últimos 12 meses
        response = supabase.table('rh_historico_colaborador')\
            .select('id', count='exact')\
            .eq('tipo_evento', 'Demissão')\
            .gte('data_evento', um_ano_atras.strftime('%Y-%m-%d'))\
            .execute()
        
        desligamentos = response.count if response.count else 0
        
        # Headcount médio (aproximação: headcount atual)
        headcount = calcular_headcount_atual_v2()
        
        if headcount == 0:
            return 0
        
        turnover = (desligamentos / headcount) * 100
        return round(turnover, 1)
        
    except Exception as e:
        print(f"❌ Erro ao calcular turnover geral: {str(e)}")
        return 0


def calcular_total_desligamentos_v2(periodo_inicio, periodo_fim, departamentos_ids=None, cargos_ids=None):
    """KPI: Total de Desligamentos no período"""
    try:
        response = supabase.table('rh_historico_colaborador')\
            .select('id', count='exact')\
            .eq('tipo_evento', 'Demissão')\
            .gte('data_evento', periodo_inicio)\
            .lte('data_evento', periodo_fim)\
            .execute()
        
        return response.count if response.count else 0
        
    except Exception as e:
        print(f"❌ Erro ao calcular desligamentos: {str(e)}")
        return 0


def calcular_total_admissoes_v2(periodo_inicio, periodo_fim, departamentos_ids=None, cargos_ids=None):
    """KPI: Total de Admissões no período"""
    try:
        response = supabase.table('rh_historico_colaborador')\
            .select('id', count='exact')\
            .eq('tipo_evento', 'Admissão')\
            .gte('data_evento', periodo_inicio)\
            .lte('data_evento', periodo_fim)\
            .execute()
        
        return response.count if response.count else 0
        
    except Exception as e:
        print(f"❌ Erro ao calcular admissões: {str(e)}")
        return 0


def calcular_tempo_medio_permanencia_v2():
    """KPI: Tempo Médio de Permanência em anos"""
    try:
        response = supabase.table('rh_colaboradores')\
            .select('data_admissao, data_desligamento, status')\
            .execute()
        
        colaboradores = response.data if response.data else []
        
        if not colaboradores:
            return 0
        
        hoje = datetime.now()
        tempos = []
        
        for colab in colaboradores:
            if colab.get('data_admissao'):
                admissao = datetime.strptime(colab['data_admissao'][:10], '%Y-%m-%d')
                
                if colab.get('status') == 'Ativo':
                    # Colaborador ativo: tempo até hoje
                    meses = (hoje.year - admissao.year) * 12 + (hoje.month - admissao.month)
                elif colab.get('data_desligamento'):
                    # Colaborador inativo: tempo até desligamento
                    desligamento = datetime.strptime(colab['data_desligamento'][:10], '%Y-%m-%d')
                    meses = (desligamento.year - admissao.year) * 12 + (desligamento.month - admissao.month)
                else:
                    continue
                
                if meses > 0:
                    tempos.append(meses)
        
        if not tempos:
            return 0
        
        media_meses = sum(tempos) / len(tempos)
        media_anos = media_meses / 12
        return round(media_anos, 1)
        
    except Exception as e:
        print(f"❌ Erro ao calcular tempo médio de permanência: {str(e)}")
        return 0


def calcular_headcount_atual_v2():
    """KPI: Headcount Atual (colaboradores ativos)"""
    try:
        response = supabase.table('rh_colaboradores')\
            .select('id', count='exact')\
            .eq('status', 'Ativo')\
            .execute()
        
        return response.count if response.count else 0
        
    except Exception as e:
        print(f"❌ Erro ao calcular headcount atual: {str(e)}")
        return 0


def calcular_turnover_por_departamento_v2(periodo_inicio, periodo_fim):
    """Gráfico: Turnover por Departamento (Todos)"""
    try:
        # Buscar departamentos
        response_deps = supabase.table('rh_departamentos')\
            .select('id, nome_departamento')\
            .execute()
        departamentos = response_deps.data if response_deps.data else []
        
        # TODO: Implementar cálculo real por departamento
        # Por enquanto, retornar dados mock
        return {
            'labels': [d['nome_departamento'] for d in departamentos[:5]],
            'values': [18.5, 12.3, 22.1, 8.7, 15.9]
        }
        
    except Exception as e:
        print(f"❌ Erro ao calcular turnover por departamento: {str(e)}")
        return {'labels': [], 'values': []}


def calcular_turnover_por_cargo_v2(periodo_inicio, periodo_fim):
    """Gráfico: Turnover por Cargo (Top 10)"""
    try:
        # Buscar cargos
        response_cargos = supabase.table('rh_cargos')\
            .select('id, nome_cargo')\
            .execute()
        cargos = response_cargos.data if response_cargos.data else []
        
        # TODO: Implementar cálculo real por cargo
        # Por enquanto, retornar dados mock
        return {
            'labels': [c['nome_cargo'] for c in cargos[:10]],
            'values': [25.5, 20.3, 18.7, 15.2, 12.8, 10.5, 8.9, 7.2, 5.6, 3.4]
        }
        
    except Exception as e:
        print(f"❌ Erro ao calcular turnover por cargo: {str(e)}")
        return {'labels': [], 'values': []}


def calcular_desligamentos_por_tempo_casa_v2(periodo_inicio, periodo_fim):
    """Gráfico: Desligamentos por Tempo de Casa (Faixas)"""
    try:
        # Buscar desligamentos no período
        response = supabase.table('rh_historico_colaborador')\
            .select('colaborador_id, data_evento')\
            .eq('tipo_evento', 'Demissão')\
            .gte('data_evento', periodo_inicio)\
            .lte('data_evento', periodo_fim)\
            .execute()
        
        desligamentos = response.data if response.data else []
        
        # Buscar dados dos colaboradores
        colaborador_ids = [d['colaborador_id'] for d in desligamentos]
        
        if not colaborador_ids:
            return {
                'labels': ['< 3 meses', '3-6 meses', '6-12 meses', '1-3 anos', '> 3 anos'],
                'values': [0, 0, 0, 0, 0]
            }
        
        response_colabs = supabase.table('rh_colaboradores')\
            .select('id, data_admissao')\
            .in_('id', colaborador_ids)\
            .execute()
        
        colaboradores = {c['id']: c for c in (response_colabs.data or [])}
        
        # Classificar por faixa
        faixas = {
            '< 3 meses': 0,
            '3-6 meses': 0,
            '6-12 meses': 0,
            '1-3 anos': 0,
            '> 3 anos': 0
        }
        
        for desl in desligamentos:
            colab = colaboradores.get(desl['colaborador_id'])
            if not colab or not colab.get('data_admissao'):
                continue
            
            admissao = datetime.strptime(colab['data_admissao'][:10], '%Y-%m-%d')
            desligamento = datetime.strptime(desl['data_evento'][:10], '%Y-%m-%d')
            meses = (desligamento.year - admissao.year) * 12 + (desligamento.month - admissao.month)
            
            if meses < 3:
                faixas['< 3 meses'] += 1
            elif meses < 6:
                faixas['3-6 meses'] += 1
            elif meses < 12:
                faixas['6-12 meses'] += 1
            elif meses < 36:
                faixas['1-3 anos'] += 1
            else:
                faixas['> 3 anos'] += 1
        
        return {
            'labels': list(faixas.keys()),
            'values': list(faixas.values())
        }
        
    except Exception as e:
        print(f"❌ Erro ao calcular desligamentos por tempo de casa: {str(e)}")
        return {
            'labels': ['< 3 meses', '3-6 meses', '6-12 meses', '1-3 anos', '> 3 anos'],
            'values': [0, 0, 0, 0, 0]
        }


def calcular_turnover_por_faixa_etaria_v2(periodo_inicio, periodo_fim):
    """Gráfico: Turnover por Faixa Etária"""
    try:
        # Buscar desligamentos no período
        response = supabase.table('rh_historico_colaborador')\
            .select('colaborador_id')\
            .eq('tipo_evento', 'Demissão')\
            .gte('data_evento', periodo_inicio)\
            .lte('data_evento', periodo_fim)\
            .execute()
        
        desligamentos = response.data if response.data else []
        colaborador_ids = [d['colaborador_id'] for d in desligamentos]
        
        if not colaborador_ids:
            return {
                'labels': ['18-25', '26-35', '36-45', '46-55', '56+'],
                'values': [0, 0, 0, 0, 0]
            }
        
        # Buscar dados dos colaboradores
        response_colabs = supabase.table('rh_colaboradores')\
            .select('id, data_nascimento')\
            .in_('id', colaborador_ids)\
            .execute()
        
        colaboradores = response_colabs.data if response_colabs.data else []
        
        # Classificar por faixa etária
        hoje = datetime.now()
        faixas = {
            '18-25': 0,
            '26-35': 0,
            '36-45': 0,
            '46-55': 0,
            '56+': 0
        }
        
        for colab in colaboradores:
            if not colab.get('data_nascimento'):
                continue
            
            nascimento = datetime.strptime(colab['data_nascimento'][:10], '%Y-%m-%d')
            idade = hoje.year - nascimento.year - ((hoje.month, hoje.day) < (nascimento.month, nascimento.day))
            
            if idade < 26:
                faixas['18-25'] += 1
            elif idade < 36:
                faixas['26-35'] += 1
            elif idade < 46:
                faixas['36-45'] += 1
            elif idade < 56:
                faixas['46-55'] += 1
            else:
                faixas['56+'] += 1
        
        return {
            'labels': list(faixas.keys()),
            'values': list(faixas.values())
        }
        
    except Exception as e:
        print(f"❌ Erro ao calcular turnover por faixa etária: {str(e)}")
        return {
            'labels': ['18-25', '26-35', '36-45', '46-55', '56+'],
            'values': [0, 0, 0, 0, 0]
        }


def calcular_evolucao_turnover_v2(periodo_inicio, periodo_fim):
    """Gráfico: Evolução do Turnover ao Longo do Tempo (Linha)"""
    try:
        # Gerar meses do período
        inicio = datetime.strptime(periodo_inicio, '%Y-%m-%d')
        fim = datetime.strptime(periodo_fim, '%Y-%m-%d')
        
        meses = []
        current = inicio
        while current <= fim:
            meses.append(current.strftime('%Y-%m'))
            current += relativedelta(months=1)
        
        # TODO: Implementar cálculo real de turnover mensal
        # Por enquanto, retornar dados mock
        return {
            'labels': [m.split('-')[1] + '/' + m.split('-')[0][2:] for m in meses[-12:]],
            'values': [15.2, 18.5, 16.3, 14.7, 19.2, 17.8, 16.5, 15.9, 18.1, 16.7, 17.3, 18.5]
        }
        
    except Exception as e:
        print(f"❌ Erro ao calcular evolução do turnover: {str(e)}")
        return {'labels': [], 'values': []}


def calcular_tabela_desligamentos_recentes_v2():
    """Tabela: Desligamentos Recentes (Últimos 30 dias)"""
    try:
        # Calcular data de 30 dias atrás
        hoje = datetime.now()
        trinta_dias_atras = hoje - timedelta(days=30)
        
        # Buscar desligamentos recentes
        response = supabase.table('rh_historico_colaborador')\
            .select('colaborador_id, data_evento, cargo_id, departamento_id, descricao_e_motivos')\
            .eq('tipo_evento', 'Demissão')\
            .gte('data_evento', trinta_dias_atras.strftime('%Y-%m-%d'))\
            .order('data_evento', desc=True)\
            .execute()
        
        desligamentos = response.data if response.data else []
        
        if not desligamentos:
            return []
        
        # Buscar dados dos colaboradores
        colaborador_ids = [d['colaborador_id'] for d in desligamentos]
        response_colabs = supabase.table('rh_colaboradores')\
            .select('id, nome_completo, data_admissao, data_desligamento')\
            .in_('id', colaborador_ids)\
            .execute()
        
        colaboradores = {c['id']: c for c in (response_colabs.data or [])}
        
        # Buscar cargos e departamentos
        response_cargos = supabase.table('rh_cargos')\
            .select('id, nome_cargo')\
            .execute()
        cargos_map = {c['id']: c['nome_cargo'] for c in (response_cargos.data or [])}
        
        response_deps = supabase.table('rh_departamentos')\
            .select('id, nome_departamento')\
            .execute()
        deps_map = {d['id']: d['nome_departamento'] for d in (response_deps.data or [])}
        
        # Montar tabela
        tabela = []
        for desl in desligamentos:
            colab = colaboradores.get(desl['colaborador_id'])
            if not colab:
                continue
            
            # Calcular tempo de casa
            if colab.get('data_admissao') and colab.get('data_desligamento'):
                admissao = datetime.strptime(colab['data_admissao'][:10], '%Y-%m-%d')
                desligamento = datetime.strptime(colab['data_desligamento'][:10], '%Y-%m-%d')
                meses = (desligamento.year - admissao.year) * 12 + (desligamento.month - admissao.month)
                
                if meses < 12:
                    tempo_casa = f"{meses} meses"
                else:
                    anos = meses // 12
                    meses_resto = meses % 12
                    tempo_casa = f"{anos} ano{'s' if anos > 1 else ''}"
                    if meses_resto > 0:
                        tempo_casa += f" e {meses_resto} meses"
            else:
                tempo_casa = 'N/A'
                meses = 0
            
            tabela.append({
                'id': colab['id'],
                'nome': colab.get('nome_completo', 'Desconhecido'),
                'cargo': cargos_map.get(desl.get('cargo_id'), 'N/A'),
                'departamento': deps_map.get(desl.get('departamento_id'), 'N/A'),
                'data_admissao': colab.get('data_admissao', '')[:10] if colab.get('data_admissao') else 'N/A',
                'data_desligamento': colab.get('data_desligamento', '')[:10] if colab.get('data_desligamento') else 'N/A',
                'tempo_casa': tempo_casa,
                'tempo_casa_meses': meses,
                'motivo': desl.get('descricao_e_motivos', 'Não informado')
            })
        
        return tabela
        
    except Exception as e:
        print(f"❌ Erro ao calcular tabela de desligamentos recentes: {str(e)}")
        return []
