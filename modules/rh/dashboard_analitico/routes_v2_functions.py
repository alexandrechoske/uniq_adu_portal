# -*- coding: utf-8 -*-
"""
Funções de Cálculo - Dashboard Analítico V2.0
Seção 1: Recrutamento & Seleção
Seção 2: Turnover & Retenção
Seção 3: Administração de Pessoal
Seção 4: Compliance & Eventos Operacionais
"""

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from collections import defaultdict
from extensions import supabase


# ========================================
# FUNÇÕES AUXILIARES COMUNS
# ========================================

def _parse_float(value, default=0.0):
    """Converte valores numéricos em float de forma resiliente"""
    if value is None:
        return default

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        value = value.strip().replace('R$ ', '').replace('.', '').replace(',', '.')

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalizar_genero(valor):
    if not valor:
        return 'Não informado'

    valor_normalizado = valor.strip().lower()
    if valor_normalizado.startswith('m'):
        return 'Masculino'
    if valor_normalizado.startswith('f'):
        return 'Feminino'
    if valor_normalizado in {'outro', 'não binário', 'nao binario'}:
        return 'Outro'
    return valor.strip().title()


def _map_escolaridade(valor):
    if not valor:
        return 'Outros'

    texto = valor.strip().lower()
    if 'fundamental' in texto:
        return 'Fundamental'
    if 'médio' in texto or 'medio' in texto:
        return 'Médio'
    if 'superior incompleto' in texto:
        return 'Superior Incompleto'
    if 'superior completo' in texto:
        return 'Superior Completo'
    if any(keyword in texto for keyword in ['pós', 'pos', 'mba', 'mestrado', 'doutor', 'especializa']):
        return 'Pós'
    return 'Outros'


def _status_filter_value(filtro):
    if not filtro or filtro == 'todos':
        return None
    mapa = {
        'ativo': 'Ativo',
        'inativo': 'Inativo',
        'desligado': 'Desligado'
    }
    return mapa.get(filtro.lower(), filtro)


def _percentual(parcial, total):
    if not total:
        return 0.0
    try:
        return round((parcial / total) * 100, 1)
    except ZeroDivisionError:
        return 0.0


def _parse_date(value):
    if not value:
        return None

    if isinstance(value, datetime):
        return value

    if isinstance(value, str):
        texto = value.strip()
        if not texto:
            return None

        formatos = ['%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%S.%f', '%d/%m/%Y']
        for formato in formatos:
            try:
                return datetime.strptime(texto, formato)
            except ValueError:
                continue
    
    return None


def _format_iso_date(date_obj):
    if not date_obj:
        return None
    return date_obj.strftime('%Y-%m-%d')


def _dias_entre(inicio, fim):
    if not inicio or not fim:
        return None
    delta = fim - inicio
    return delta.days


def _carregar_mapas_basicos():
    """Carrega mapas de departamentos e cargos para reutilização nas seções"""
    departamentos_map = {}
    cargos_map = {}

    try:
        response_deps = supabase.table('rh_departamentos')\
            .select('id, nome_departamento')\
            .execute()
        departamentos_map = {
            str(item['id']): item.get('nome_departamento', 'Sem departamento')
            for item in (response_deps.data or [])
        }
    except Exception as exc:
        print(f"⚠️ Erro ao carregar departamentos: {exc}")

    try:
        response_cargos = supabase.table('rh_cargos')\
            .select('id, nome_cargo')\
            .execute()
        cargos_map = {
            str(item['id']): item.get('nome_cargo', 'Sem cargo')
            for item in (response_cargos.data or [])
        }
    except Exception as exc:
        print(f"⚠️ Erro ao carregar cargos: {exc}")

    return departamentos_map, cargos_map


def _carregar_complementos_colaboradores(colaboradores_ids):
    """Busca o último departamento, cargo e salário registrados para cada colaborador."""
    if not colaboradores_ids:
        return {}

    complementos = {}
    ids_validos = [colab_id for colab_id in colaboradores_ids if colab_id is not None]

    if not ids_validos:
        return {}

    tamanho_lote = 100

    for inicio in range(0, len(ids_validos), tamanho_lote):
        lote = ids_validos[inicio:inicio + tamanho_lote]

        try:
            response = supabase.table('rh_historico_colaborador')\
                .select('colaborador_id, departamento_id, cargo_id, salario_mensal, data_evento')\
                .in_('colaborador_id', lote)\
                .order('data_evento', desc=True)\
                .execute()

            for registro in (response.data or []):
                colab_id = registro.get('colaborador_id')
                if colab_id is None:
                    continue

                chave = str(colab_id)
                complemento = complementos.setdefault(chave, {
                    'departamento_id': None,
                    'cargo_id': None,
                    'salario_mensal': None
                })

                if complemento['departamento_id'] is None and registro.get('departamento_id') is not None:
                    complemento['departamento_id'] = registro.get('departamento_id')

                if complemento['cargo_id'] is None and registro.get('cargo_id') is not None:
                    complemento['cargo_id'] = registro.get('cargo_id')

                salario_registro = registro.get('salario_mensal')
                if complemento['salario_mensal'] is None and salario_registro not in (None, ''):
                    complemento['salario_mensal'] = salario_registro

                if all(valor is not None for valor in complemento.values()):
                    continue

        except Exception as exc:
            print(f"⚠️ Erro ao carregar complementos de colaboradores: {exc}")

    return complementos


def _coletar_data(evento, campos):
    for campo in campos:
        if campo in evento:
            data = _parse_date(evento.get(campo))
            if data:
                return data
    return None


def _normalizar_status_evento_valor(valor):
    if not valor:
        return 'pendente'

    texto = valor.strip().lower()
    if any(substr in texto for substr in ['realizado', 'conclu', 'finalizado', 'completo']):
        return 'realizado'
    if any(substr in texto for substr in ['vencido', 'atrasado', 'expirado', 'vencido']):
        return 'vencido'
    if any(substr in texto for substr in ['andamento', 'progresso', 'iniciado']):
        return 'em_andamento'
    return 'pendente'


def _status_evento_normalizado(evento):
    campos_status = ['status', 'status_evento', 'situacao', 'situacao_evento']
    for campo in campos_status:
        if campo in evento and evento.get(campo):
            return _normalizar_status_evento_valor(evento.get(campo))
    return 'pendente'


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


# ========================================
# SEÇÃO 3: ADMINISTRAÇÃO DE PESSOAL
# ========================================


def _estrutura_secao_pessoal_vazia():
    return {
        'kpis': {
            'headcount_total': 0,
            'masculinos': {'quantidade': 0, 'percentual': 0.0},
            'femininos': {'quantidade': 0, 'percentual': 0.0},
            'salario_medio': 0.0,
            'superior_completo': {'quantidade': 0, 'percentual': 0.0}
        },
        'graficos': {
            'headcount_departamento': {'labels': [], 'values': []},
            'salario_departamento': {'labels': [], 'values': []},
            'genero': {'labels': ['Masculino', 'Feminino', 'Outros'], 'values': [0, 0, 0]},
            'escolaridade': {
                'labels': ['Fundamental', 'Médio', 'Superior Incompleto', 'Superior Completo', 'Pós'],
                'values': [0, 0, 0, 0, 0]
            },
            'raca': {'labels': [], 'values': []},
            'piramide_etaria': {
                'labels': ['18-24', '25-34', '35-44', '45-54', '55+'],
                'masculino': [0, 0, 0, 0, 0],
                'feminino': [0, 0, 0, 0, 0]
            },
            'tempo_medio_departamento': {'labels': [], 'values': []}
        }
    }


def calcular_secao_administracao_pessoal(periodo_inicio, periodo_fim, departamentos_ids=None, cargos_ids=None, status_filter='todos'):
    """Calcula KPIs e gráficos da Seção 3: Administração de Pessoal"""
    print("👥 [SEÇÃO 3] Calculando Administração de Pessoal...")

    try:
        departamentos_map, cargos_map = _carregar_mapas_basicos()

        response_colabs = supabase.table('rh_colaboradores')\
            .select('id, nome_completo, status, genero, raca_cor, escolaridade, data_nascimento, data_admissao, data_desligamento')\
            .execute()

        colaboradores = response_colabs.data if response_colabs.data else []
        if not colaboradores:
            print("⚠️ Nenhum colaborador encontrado para a Seção 3.")
            return _estrutura_secao_pessoal_vazia()

        complementos = _carregar_complementos_colaboradores([colab.get('id') for colab in colaboradores])

        status_value = _status_filter_value(status_filter)
        departamentos_set = {str(item) for item in (departamentos_ids or []) if item}
        cargos_set = {str(item) for item in (cargos_ids or []) if item}

        colaboradores_filtrados = []
        for colab in colaboradores:
            colab_id = colab.get('id')
            chave_id = str(colab_id) if colab_id is not None else None
            complemento = complementos.get(chave_id, {})

            departamento_id = complemento.get('departamento_id')
            cargo_id = complemento.get('cargo_id')
            salario_mensal = complemento.get('salario_mensal')

            colab_completo = colab.copy()
            colab_completo['departamento_id'] = departamento_id
            colab_completo['cargo_id'] = cargo_id
            colab_completo['salario_mensal'] = salario_mensal

            status_colab = colab.get('status')

            if status_value and status_colab != status_value:
                continue
            if status_filter and status_filter != 'todos' and not status_value:
                if (status_colab or '').lower() != status_filter.lower():
                    continue

            if departamentos_set:
                if departamento_id is None or str(departamento_id) not in departamentos_set:
                    continue
            if cargos_set:
                if cargo_id is None or str(cargo_id) not in cargos_set:
                    continue

            colaboradores_filtrados.append(colab_completo)

        if not colaboradores_filtrados:
            print("⚠️ Nenhum colaborador após aplicação de filtros na Seção 3.")
            return _estrutura_secao_pessoal_vazia()

        total_colaboradores = len(colaboradores_filtrados)

        genero_counts = defaultdict(int)
        salarios_validos = []
        superior_count = 0
        education_counts = defaultdict(int)
        raca_counts = defaultdict(int)
        headcount_departamento = defaultdict(int)
        salario_departamento = defaultdict(lambda: {'soma': 0.0, 'qtd': 0})
        tempo_empresa_departamento = defaultdict(list)

        hoje = datetime.now()
        faixas_etarias = [
            ('18-24', 18, 24),
            ('25-34', 25, 34),
            ('35-44', 35, 44),
            ('45-54', 45, 54),
            ('55+', 55, 120)
        ]
        piramide = {label: {'Masculino': 0, 'Feminino': 0} for label, _, _ in faixas_etarias}

        for colab in colaboradores_filtrados:
            genero_label = _normalizar_genero(colab.get('genero'))
            genero_counts[genero_label] += 1

            departamento_nome = departamentos_map.get(str(colab.get('departamento_id')), 'Sem departamento')
            headcount_departamento[departamento_nome] += 1

            salario_valor = _parse_float(colab.get('salario_mensal'), None)
            if salario_valor is not None and salario_valor > 0:
                salarios_validos.append(salario_valor)
                salario_departamento[departamento_nome]['soma'] += salario_valor
                salario_departamento[departamento_nome]['qtd'] += 1

            education_label = _map_escolaridade(colab.get('escolaridade'))
            education_counts[education_label] += 1
            if education_label in {'Superior Completo', 'Pós'}:
                superior_count += 1

            raca_label = (colab.get('raca_cor') or 'Não informado').strip().title()
            raca_counts[raca_label] += 1

            admissao = _parse_date(colab.get('data_admissao'))
            fim_vinculo = _parse_date(colab.get('data_desligamento')) or hoje
            if admissao and fim_vinculo >= admissao:
                delta = relativedelta(fim_vinculo, admissao)
                meses_totais = (delta.years * 12) + delta.months + (delta.days / 30.4375)
                tempo_empresa_departamento[departamento_nome].append(max(meses_totais, 0))

            nascimento = _parse_date(colab.get('data_nascimento'))
            if nascimento:
                idade = hoje.year - nascimento.year - ((hoje.month, hoje.day) < (nascimento.month, nascimento.day))
                for label, minimo, maximo in faixas_etarias:
                    if idade >= minimo and (idade <= maximo or maximo == 120):
                        if genero_label in {'Masculino', 'Feminino'}:
                            piramide[label][genero_label] += 1
                        else:
                            piramide[label]['Feminino'] += 0
                        break

        masculino = genero_counts.get('Masculino', 0)
        feminino = genero_counts.get('Feminino', 0)
        outros_genero = total_colaboradores - masculino - feminino

        salario_medio = round(sum(salarios_validos) / len(salarios_validos), 2) if salarios_validos else 0.0

        education_order = ['Fundamental', 'Médio', 'Superior Incompleto', 'Superior Completo', 'Pós']
        escolaridade_labels = list(education_order)
        escolaridade_values = [education_counts.get(cat, 0) for cat in education_order]
        outros_escolaridade = sum(count for cat, count in education_counts.items() if cat not in education_order)
        if outros_escolaridade:
            escolaridade_labels.append('Outros')
            escolaridade_values.append(outros_escolaridade)
        
        # Ordenar de forma descendente (maior para menor)
        escolaridade_pairs = sorted(zip(escolaridade_labels, escolaridade_values), key=lambda item: item[1], reverse=True)
        escolaridade_labels = [item[0] for item in escolaridade_pairs]
        escolaridade_values = [item[1] for item in escolaridade_pairs]

        headcount_ordenado = sorted(headcount_departamento.items(), key=lambda item: item[1], reverse=True)
        headcount_ordenado = headcount_ordenado[:8]
        headcount_labels = [item[0] for item in headcount_ordenado]
        headcount_values = [item[1] for item in headcount_ordenado]

        salario_departamento_labels = []
        salario_departamento_values = []
        for depto, dados in salario_departamento.items():
            if dados['qtd'] > 0:
                salario_departamento_labels.append(depto)
                salario_departamento_values.append(round(dados['soma'] / dados['qtd'], 2))
        salario_departamento_pairs = sorted(zip(salario_departamento_labels, salario_departamento_values), key=lambda item: item[1], reverse=True)[:8]
        salario_departamento_labels = [item[0] for item in salario_departamento_pairs]
        salario_departamento_values = [item[1] for item in salario_departamento_pairs]

        tempo_departamento_labels = []
        tempo_departamento_values = []
        for depto, tempos in tempo_empresa_departamento.items():
            if tempos:
                tempo_departamento_labels.append(depto)
                tempo_departamento_values.append(round(sum(tempos) / len(tempos), 1))

        tempo_pairs = sorted(
            zip(tempo_departamento_labels, tempo_departamento_values),
            key=lambda item: item[1],
            reverse=True
        )[:8]
        tempo_departamento_labels = [item[0] for item in tempo_pairs]
        tempo_departamento_values = [item[1] for item in tempo_pairs]

        raca_ordenada = sorted(raca_counts.items(), key=lambda item: item[1], reverse=True)
        if len(raca_ordenada) > 8:
            raca_ordenada = raca_ordenada[:8]
        raca_labels = [item[0] for item in raca_ordenada]
        raca_values = [item[1] for item in raca_ordenada]

        piramide_labels = [label for label, _, _ in faixas_etarias]
        piramide_masculino = [piramide[label]['Masculino'] for label in piramide_labels]
        piramide_feminino = [piramide[label]['Feminino'] for label in piramide_labels]

        resultado = {
            'kpis': {
                'headcount_total': total_colaboradores,
                'masculinos': {'quantidade': masculino, 'percentual': _percentual(masculino, total_colaboradores)},
                'femininos': {'quantidade': feminino, 'percentual': _percentual(feminino, total_colaboradores)},
                'salario_medio': salario_medio,
                'superior_completo': {
                    'quantidade': superior_count,
                    'percentual': _percentual(superior_count, total_colaboradores)
                }
            },
            'graficos': {
                'headcount_departamento': {
                    'labels': headcount_labels,
                    'values': headcount_values
                },
                'salario_departamento': {
                    'labels': salario_departamento_labels,
                    'values': salario_departamento_values
                },
                'genero': {
                    'labels': ['Masculino', 'Feminino', 'Outros'],
                    'values': [masculino, feminino, max(outros_genero, 0)]
                },
                'escolaridade': {
                    'labels': escolaridade_labels,
                    'values': escolaridade_values
                },
                'raca': {
                    'labels': raca_labels,
                    'values': raca_values
                },
                'piramide_etaria': {
                    'labels': piramide_labels,
                    'masculino': piramide_masculino,
                    'feminino': piramide_feminino
                },
                'tempo_medio_departamento': {
                    'labels': tempo_departamento_labels,
                    'values': tempo_departamento_values
                }
            }
        }

        print("📈 [SEÇÃO 3] Tempo médio por departamento:", list(zip(tempo_departamento_labels, tempo_departamento_values)))
        print("📊 [SEÇÃO 3] Pirâmide etária - masculino:", piramide_masculino, "| feminino:", piramide_feminino)

        print("✅ [SEÇÃO 3] Administração de Pessoal calculada com sucesso!")
        return resultado

    except Exception as exc:
        print(f"❌ Erro na Seção 3 (Administração de Pessoal): {exc}")
        return _estrutura_secao_pessoal_vazia()


# ========================================
# SEÇÃO 4: COMPLIANCE & EVENTOS OPERACIONAIS
# ========================================


def _estrutura_secao_compliance_vazia():
    return {
        'kpis': {
            'exames_pendentes': 0,
            'exames_vencidos': 0,
            'eventos_pendentes': 0,
            'pendencias_contabilidade': 0
        },
        'graficos': {
            'eventos_por_status': {
                'labels': [],
                'datasets': {
                    'pendente': [],
                    'em_andamento': [],
                    'realizado': [],
                    'vencido': []
                }
            },
            'proximos_eventos': {
                'labels': [],
                'values': []
            }
        },
        'tabelas': {
            'exames_periodicos': [],
            'pendencias_contabilidade': []
        }
    }


def calcular_secao_compliance_operacional(periodo_inicio, periodo_fim, departamentos_ids=None, cargos_ids=None, status_filter='todos'):
    """Calcula KPIs, gráficos e tabelas da Seção 4: Compliance & Eventos Operacionais"""
    print("🛡️ [SEÇÃO 4] Calculando Compliance & Eventos Operacionais...")

    try:
        departamentos_map, cargos_map = _carregar_mapas_basicos()

        response_colabs = supabase.table('rh_colaboradores')\
            .select('id, nome_completo, status')\
            .execute()

        colaboradores = response_colabs.data if response_colabs.data else []
        if not colaboradores:
            print("⚠️ Nenhum colaborador encontrado para a Seção 4.")
            return _estrutura_secao_compliance_vazia()

        complementos = _carregar_complementos_colaboradores([colab.get('id') for colab in colaboradores])

        status_value = _status_filter_value(status_filter)
        departamentos_set = {str(item) for item in (departamentos_ids or []) if item}
        cargos_set = {str(item) for item in (cargos_ids or []) if item}

        colaboradores_permitidos = {}
        for colab in colaboradores:
            status_colab = colab.get('status')

            if status_value and status_colab != status_value:
                continue
            if status_filter and status_filter != 'todos' and not status_value:
                if (status_colab or '').lower() != status_filter.lower():
                    continue

            colab_id = colab.get('id')
            chave_id = str(colab_id) if colab_id is not None else None
            complemento = complementos.get(chave_id, {})

            departamento_id = complemento.get('departamento_id')
            cargo_id = complemento.get('cargo_id')

            if departamentos_set:
                if departamento_id is None or str(departamento_id) not in departamentos_set:
                    continue
            if cargos_set:
                if cargo_id is None or str(cargo_id) not in cargos_set:
                    continue

            colab_completo = colab.copy()
            colab_completo['departamento_id'] = departamento_id
            colab_completo['cargo_id'] = cargo_id

            colaboradores_permitidos[str(colab.get('id'))] = colab_completo

        if not colaboradores_permitidos:
            print("⚠️ Nenhum colaborador após filtros na Seção 4.")
            return _estrutura_secao_compliance_vazia()

        colaboradores_ids = set(colaboradores_permitidos.keys())

        response_eventos = supabase.table('rh_eventos_colaborador')\
            .select('id, colaborador_id, tipo_evento, status, data_inicio, data_fim, descricao, dados_adicionais_jsonb')\
            .execute()

        eventos = [
            evento for evento in (response_eventos.data or [])
            if str(evento.get('colaborador_id')) in colaboradores_ids
        ]

        hoje = datetime.now()
        kpi_exames_pendentes = 0
        kpi_exames_vencidos = 0
        kpi_eventos_pendentes = 0

        eventos_por_tipo = defaultdict(lambda: defaultdict(int))
        eventos_timeline = defaultdict(int)
        exames_periodicos_tabela = []

        for evento in eventos:
            tipo_evento = (evento.get('tipo_evento') or 'Evento').strip()
            status_norm = _status_evento_normalizado(evento)

            if status_norm in {'pendente', 'em_andamento'}:
                kpi_eventos_pendentes += 1

            eventos_por_tipo[tipo_evento][status_norm] += 1

            # Adaptar para nova estrutura: data_inicio é a data principal, data_fim é opcional
            data_realizada = _coletar_data(evento, ['data_inicio', 'data_evento', 'data_realizacao'])
            proximo_evento = _coletar_data(evento, ['data_fim', 'proximo_evento', 'data_prevista', 'data_proximo_exame'])

            if proximo_evento and 0 <= (proximo_evento - hoje).days <= 30:
                eventos_timeline[_format_iso_date(proximo_evento)] += 1

            if 'exame' in tipo_evento.lower():
                if status_norm == 'pendente':
                    kpi_exames_pendentes += 1
                if status_norm == 'vencido' or (proximo_evento and proximo_evento < hoje and status_norm != 'realizado'):
                    kpi_exames_vencidos += 1

                colab = colaboradores_permitidos.get(str(evento.get('colaborador_id')))
                if colab:
                    exames_periodicos_tabela.append({
                        'colaborador_id': colab.get('id'),
                        'nome': colab.get('nome_completo', 'Colaborador'),
                        'cargo': cargos_map.get(str(colab.get('cargo_id')), 'N/A'),
                        'departamento': departamentos_map.get(str(colab.get('departamento_id')), 'N/A'),
                        'ultimo_exame': _format_iso_date(data_realizada),
                        'proximo_exame': _format_iso_date(proximo_evento),
                        'status': status_norm,
                        'evento_id': evento.get('id')
                    })

        exames_periodicos_tabela.sort(key=lambda item: item.get('proximo_exame') or '')

        response_pendencias = supabase.table('rh_historico_colaborador')\
            .select('id, colaborador_id, tipo_evento, data_evento, status_contabilidade, descricao_e_motivos')\
            .eq('status_contabilidade', 'Pendente')\
            .order('data_evento', desc=False)\
            .execute()

        pendencias_brutas = [
            item for item in (response_pendencias.data or [])
            if str(item.get('colaborador_id')) in colaboradores_ids
        ]

        pendencias_contabilidade = []
        for pendencia in pendencias_brutas:
            colab = colaboradores_permitidos.get(str(pendencia.get('colaborador_id')))
            if not colab:
                continue

            data_evento = _parse_date(pendencia.get('data_evento'))
            dias_pendente = _dias_entre(data_evento, hoje) if data_evento else None

            pendencias_contabilidade.append({
                'colaborador': colab.get('nome_completo', 'Colaborador'),
                'tipo_evento': pendencia.get('tipo_evento', 'Evento'),
                'data_evento': _format_iso_date(data_evento),
                'dias_pendente': dias_pendente,
                'descricao': pendencia.get('descricao_e_motivos', 'Não informado'),
                'departamento': departamentos_map.get(str(colab.get('departamento_id')), 'N/A'),
                'cargo': cargos_map.get(str(colab.get('cargo_id')), 'N/A')
            })

        pendencias_contabilidade.sort(key=lambda item: (item.get('dias_pendente') or -1), reverse=True)
        kpi_pendencias_contabilidade = len(pendencias_contabilidade)

        status_keys = ['pendente', 'em_andamento', 'realizado', 'vencido']
        tipos_ordenados = sorted(
            eventos_por_tipo.keys(),
            key=lambda tipo: sum(eventos_por_tipo[tipo].values()),
            reverse=True
        )[:8]

        eventos_status = {
            'labels': tipos_ordenados,
            'datasets': {
                status: [eventos_por_tipo[tipo].get(status, 0) for tipo in tipos_ordenados]
                for status in status_keys
            }
        }

        timeline_labels = sorted(eventos_timeline.keys())
        proximos_eventos = {
            'labels': timeline_labels,
            'values': [eventos_timeline[label] for label in timeline_labels]
        }

        resultado = {
            'kpis': {
                'exames_pendentes': kpi_exames_pendentes,
                'exames_vencidos': kpi_exames_vencidos,
                'eventos_pendentes': kpi_eventos_pendentes,
                'pendencias_contabilidade': kpi_pendencias_contabilidade
            },
            'graficos': {
                'eventos_por_status': eventos_status,
                'proximos_eventos': proximos_eventos
            },
            'tabelas': {
                'exames_periodicos': exames_periodicos_tabela,
                'pendencias_contabilidade': pendencias_contabilidade
            }
        }

        print("✅ [SEÇÃO 4] Compliance & Eventos Operacionais calculada com sucesso!")
        return resultado

    except Exception as exc:
        print(f"❌ Erro na Seção 4 (Compliance & Eventos): {exc}")
        return _estrutura_secao_compliance_vazia()
