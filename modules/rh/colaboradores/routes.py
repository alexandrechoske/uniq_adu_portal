"""
Sub-módulo de Colaboradores - Gestão de RH
Gerencia o CRUD completo de colaboradores
"""

from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash
from extensions import supabase_admin
from modules.auth.routes import login_required
from decorators.perfil_decorators import perfil_required
from datetime import datetime, date, timezone
import os

from modules.rh.colaboradores.benefits_utils import (
    BENEFICIOS_CATALOGO,
    build_beneficios_view,
    format_currency_br,
    has_beneficios,
    normalize_beneficios,
    normalize_decimal,
)
from services.event_notification_service import EventNotificationService

# Criar blueprint
colaboradores_bp = Blueprint(
    'colaboradores',
    __name__,
    url_prefix='/rh/colaboradores',
    template_folder='templates',
    static_folder='static',
    static_url_path='/rh/colaboradores/static'
)

# API Bypass para testes
API_BYPASS_KEY = os.getenv('API_BYPASS_KEY')

event_notifier = EventNotificationService()


BENEFICIOS_CATALOGO = [
    {'slug': 'vale_alimentacao', 'label': 'Vale Alimentação'},
    {'slug': 'vale_refeicao', 'label': 'Vale Refeição'},
    {'slug': 'vale_transporte', 'label': 'Vale Transporte'},
    {'slug': 'ajuda_de_custo', 'label': 'Ajuda de Custo'},
    {'slug': 'auxilio_creche', 'label': 'Auxílio Creche'},
    {'slug': 'plano_saude', 'label': 'Plano de Saúde'},
    {'slug': 'plano_odontologico', 'label': 'Plano Odontológico'},
    {'slug': 'seguro_vida', 'label': 'Seguro de Vida'},
    {'slug': 'auxilio_educacao', 'label': 'Auxílio Educação'},
    {'slug': 'outros', 'label': 'Outro Benefício'}
]


def _ensure_date(value):
    """Converte diferentes formatos de data para objeto date."""
    if not value:
        return None

    if isinstance(value, date) and not isinstance(value, datetime):
        return value

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, str):
        candidate = value.strip()
        if not candidate:
            return None

        candidate = candidate.replace('Z', '+00:00')

        try:
            return datetime.fromisoformat(candidate).date()
        except ValueError:
            try:
                return datetime.strptime(candidate.split('T')[0], '%Y-%m-%d').date()
            except ValueError:
                try:
                    return datetime.strptime(candidate, '%d/%m/%Y').date()
                except ValueError:
                    return None

    return None


def _ensure_datetime(value):
    """Converte diferentes formatos para objeto datetime."""
    if not value:
        return None

    dt = None

    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        candidate = value.strip()
        if not candidate:
            return None

        candidate = candidate.replace('Z', '+00:00')

        for fmt in ('%Y-%m-%dT%H:%M:%S.%f%z', '%Y-%m-%dT%H:%M:%S%z', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S'):
            try:
                dt = datetime.strptime(candidate, fmt)
                break
            except ValueError:
                continue

        if dt is None:
            try:
                dt = datetime.fromisoformat(candidate)
            except ValueError:
                return None

    if dt and dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)

    return dt


def _calculate_age(birth_date):
    """Calcula idade em anos completos."""
    reference = _ensure_date(birth_date)
    if not reference:
        return None

    today = date.today()
    years = today.year - reference.year
    if (today.month, today.day) < (reference.month, reference.day):
        years -= 1
    return max(years, 0)


def _format_currency_br(value):
    return format_currency_br(value)


def _normalizar_valor_decimal(valor):
    return normalize_decimal(valor)


def _format_time_br(value):
    referencia = _ensure_datetime(value)
    if not referencia:
        return None
    return referencia.strftime('%H:%M')


def _parse_beneficios_payload(payload, prefix='beneficio_'):
    if not isinstance(payload, dict):
        return normalize_beneficios({})

    flat = {}
    for key, value in payload.items():
        if key.startswith(prefix):
            slug = key[len(prefix):]
            flat[slug] = value

    return normalize_beneficios(flat)


def _coletar_beneficios_anteriores(historico):
    beneficios = historico.get('beneficios_jsonb') if historico else None
    return normalize_beneficios(beneficios)


def format_date_br(value):
    """Converte datas para o formato brasileiro (DD/MM/AAAA)."""
    if not value:
        return None

    if isinstance(value, datetime):
        return value.strftime('%d/%m/%Y')

    if isinstance(value, date):
        return value.strftime('%d/%m/%Y')

    if isinstance(value, str):
        candidate = value.strip()
        if not candidate:
            return None

        candidate = candidate.replace('Z', '+00:00')

        try:
            parsed = datetime.fromisoformat(candidate)
            return parsed.strftime('%d/%m/%Y')
        except ValueError:
            base = candidate.split('T')[0]
            try:
                parsed = datetime.strptime(base, '%Y-%m-%d')
                return parsed.strftime('%d/%m/%Y')
            except ValueError:
                try:
                    parsed = datetime.strptime(candidate, '%d/%m/%Y')
                    return parsed.strftime('%d/%m/%Y')
                except ValueError:
                    return candidate

    return str(value)

def check_api_bypass():
    """Verifica se a requisição usa a chave de bypass para testes"""
    api_key = request.headers.get('X-API-Key')
    return api_key == API_BYPASS_KEY

def check_auth():
    """Verifica autenticação (session ou bypass)"""
    if check_api_bypass():
        return True
    return 'user' in session

# Decorator personalizado que permite perfil OU bypass
def perfil_or_bypass_required(modulo, pagina=None):
    """
    Decorator que permite acesso por perfil OU por API bypass
    Usado para rotas que precisam de testes via API
    """
    def decorator(f):
        # Aplicar primeiro o decorator de perfil
        decorated = perfil_required(modulo, pagina)(f)
        
        # Wrapper para verificar bypass ANTES do perfil
        def wrapper(*args, **kwargs):
            if check_api_bypass():
                return f(*args, **kwargs)
            return decorated(*args, **kwargs)
        
        wrapper.__name__ = f.__name__
        wrapper.__doc__ = f.__doc__
        return wrapper
    return decorator

# =====================================================================
# ROTAS DE VISUALIZAÇÃO (HTML)
# =====================================================================

@colaboradores_bp.route('/')
@login_required
@perfil_required('rh', 'colaboradores')
def lista_colaboradores():
    """Página principal - Lista de colaboradores"""
    try:
        # Buscar todos os colaboradores usando a view
        response = supabase_admin.table('vw_colaboradores_atual')\
            .select('*')\
            .order('nome_completo')\
            .execute()
        
        colaboradores = response.data if response.data else []
        
        # Contar por status
        total = len(colaboradores)
        ativos = len([c for c in colaboradores if c.get('status') == 'Ativo'])
        inativos = len([c for c in colaboradores if c.get('status') == 'Inativo'])
        
        cargos_response = supabase_admin.table('rh_cargos')\
            .select('id, nome_cargo')\
            .order('nome_cargo')\
            .execute()

        departamentos_response = supabase_admin.table('rh_departamentos')\
            .select('id, nome_departamento')\
            .order('nome_departamento')\
            .execute()

        gestores_response = supabase_admin.table('rh_colaboradores')\
            .select('id, nome_completo, matricula')\
            .eq('status', 'Ativo')\
            .order('nome_completo')\
            .execute()

        return render_template(
            'colaboradores/lista_colaboradores.html',
            colaboradores=colaboradores,
            total=total,
            ativos=ativos,
            inativos=inativos,
            cargos=cargos_response.data if cargos_response.data else [],
            departamentos=departamentos_response.data if departamentos_response.data else [],
            gestores=gestores_response.data if gestores_response.data else [],
            beneficios_catalogo=BENEFICIOS_CATALOGO
        )
    
    except Exception as e:
        print(f"[ERRO] Erro ao buscar colaboradores: {str(e)}")
        flash(f'Erro ao buscar colaboradores: {str(e)}', 'danger')
        return render_template('colaboradores/lista_colaboradores.html', colaboradores=[], total=0, ativos=0, inativos=0)

@colaboradores_bp.route('/novo')
def novo_colaborador():
    """Página para cadastrar novo colaborador
    
    Se receber ?candidato_id=UUID, pré-preenche com dados do candidato
    """
    if not check_auth():
        return redirect(url_for('auth.login'))
    
    try:
        # Data de hoje para validação de datas
        hoje = datetime.now().strftime('%Y-%m-%d')
        
        # 🔥 NOVO: Detectar se vem de um candidato contratado
        candidato_id = request.args.get('candidato_id')
        candidato = None
        
        if candidato_id:
            print(f"📥 Detectado candidato_id: {candidato_id}")
            # Buscar dados do candidato para pré-preencher
            candidato_response = supabase_admin.table('rh_candidatos')\
                .select('*')\
                .eq('id', candidato_id)\
                .single()\
                .execute()
            
            if candidato_response.data:
                candidato = candidato_response.data
                print(f"✅ Candidato encontrado: {candidato.get('nome_completo')}")
            else:
                print(f"⚠️ Candidato {candidato_id} não encontrado")
        
        # Buscar dados para os selects
        cargos = supabase_admin.table('rh_cargos').select('*').order('nome_cargo').execute()
        departamentos = supabase_admin.table('rh_departamentos').select('*').order('nome_departamento').execute()
        empresas = supabase_admin.table('rh_empresas').select('*').order('razao_social').execute()
        
        # Buscar colaboradores para select de gestor
        colaboradores = supabase_admin.table('rh_colaboradores')\
            .select('id, nome_completo, matricula')\
            .eq('status', 'Ativo')\
            .order('nome_completo')\
            .execute()
        
        return render_template(
            'colaboradores/form_colaborador.html',
            modo='novo',
            hoje=hoje,
            candidato_id=candidato_id,  # Passar para template
            candidato=candidato,  # Passar dados do candidato
            cargos=cargos.data if cargos.data else [],
            departamentos=departamentos.data if departamentos.data else [],
            empresas=empresas.data if empresas.data else [],
            gestores=colaboradores.data if colaboradores.data else [],
            ultimo_historico=None,
            info_atual=None,
            dependentes=[],
            beneficios_catalogo=BENEFICIOS_CATALOGO,
            is_editing=False
        )
    
    except Exception as e:
        print(f"[ERRO] Erro ao carregar formulário: {str(e)}")
        flash(f'Erro ao carregar formulário: {str(e)}', 'danger')
        return redirect(url_for('colaboradores.lista_colaboradores'))

@colaboradores_bp.route('/editar/<colaborador_id>')
def editar_colaborador(colaborador_id):
    """Página para editar colaborador existente"""
    if not check_auth():
        return redirect(url_for('auth.login'))
    
    try:
        # Data de hoje para validação de datas
        hoje = datetime.now().strftime('%Y-%m-%d')
        
        # Buscar colaborador
        colab_response = supabase_admin.table('rh_colaboradores')\
            .select('*')\
            .eq('id', colaborador_id)\
            .single()\
            .execute()

        if not colab_response.data:
            flash('Colaborador não encontrado', 'warning')
            return redirect(url_for('colaboradores.lista_colaboradores'))

        colaborador_data = colab_response.data
        colaborador_data['data_nascimento_br'] = format_date_br(colaborador_data.get('data_nascimento'))
        colaborador_data['data_admissao_br'] = format_date_br(colaborador_data.get('data_admissao'))
        colaborador_data['data_desligamento_br'] = format_date_br(colaborador_data.get('data_desligamento'))
        colaborador_data['rg_data_expedicao_br'] = format_date_br(colaborador_data.get('rg_data_expedicao'))
        
        # Buscar dados para os selects
        cargos = supabase_admin.table('rh_cargos').select('*').order('nome_cargo').execute()
        departamentos = supabase_admin.table('rh_departamentos').select('*').order('nome_departamento').execute()
        empresas = supabase_admin.table('rh_empresas').select('*').order('razao_social').execute()
        
        # Buscar colaboradores para select de gestor (excluindo o próprio)
        colaboradores = supabase_admin.table('rh_colaboradores')\
            .select('id, nome_completo, matricula')\
            .eq('status', 'Ativo')\
            .neq('id', colaborador_id)\
            .order('nome_completo')\
            .execute()
        
        # Buscar último registro do histórico para preencher campos
        historico = supabase_admin.table('rh_historico_colaborador')\
            .select('*')\
            .eq('colaborador_id', colaborador_id)\
            .order('data_evento', desc=True)\
            .order('created_at', desc=True)\
            .limit(1)\
            .execute()
        
        ultimo_historico = historico.data[0] if historico.data else {}

        dependentes = []
        dependentes_response = supabase_admin.table('rh_colaborador_dependentes')\
            .select('*')\
            .eq('colaborador_id', colaborador_id)\
            .order('nome_completo')\
            .execute()

        for dependente in dependentes_response.data or []:
            data_nascimento_dt = _ensure_date(dependente.get('data_nascimento'))
            dependente['data_nascimento_br'] = format_date_br(data_nascimento_dt)
            dependente['data_nascimento_iso'] = data_nascimento_dt.isoformat() if data_nascimento_dt else ''
            dependente['idade'] = _calculate_age(data_nascimento_dt)
            dependentes.append(dependente)

        contatos_emergencia = []
        contatos_response = supabase_admin.table('rh_colaborador_contatos_emergencia')\
            .select('*')\
            .eq('colaborador_id', colaborador_id)\
            .order('nome_contato')\
            .execute()

        for contato in contatos_response.data or []:
            contato['telefone_contato'] = (contato.get('telefone_contato') or '').strip()
            contatos_emergencia.append(contato)

        info_atual = None
        try:
            rpc_response = supabase_admin.rpc(
                'get_colaborador_info_atual',
                {'p_colaborador_id': colaborador_id}
            ).execute()
            if rpc_response.data:
                info_atual = rpc_response.data[0]
        except Exception as rpc_error:
            print(f"[AVISO] Falha ao obter info atual via RPC: {rpc_error}")
            info_atual = None

        base_evento = ultimo_historico or _buscar_ultimo_historico(colaborador_id)
        if base_evento:
            beneficios_dict = _coletar_beneficios_anteriores(base_evento)
            beneficios_view = build_beneficios_view(beneficios_dict)
            salario_atual = _normalizar_valor_decimal(base_evento.get('salario_mensal'))
            salario_formatado = _format_currency_br(salario_atual) if salario_atual is not None else None
            total_remuneracao = (salario_atual or 0.0) + beneficios_view['total_geral']

            info_atual = info_atual or {}
            info_atual.update({
                'salario_mensal': salario_atual,
                'salario_formatado': salario_formatado,
                'beneficios_jsonb': beneficios_dict,
                'beneficios_view': beneficios_view,
                'beneficios_total': beneficios_view['total_geral'],
                'beneficios_total_formatado': beneficios_view['total_geral_formatado'],
                'remuneracao_adicional_total': beneficios_view['remuneracao_adicional']['total'],
                'remuneracao_adicional_total_formatado': beneficios_view['remuneracao_adicional']['total_formatado'],
                'beneficios_padrao_total': beneficios_view['beneficios_padrao']['total'],
                'beneficios_padrao_total_formatado': beneficios_view['beneficios_padrao']['total_formatado'],
                'total_remuneracao': total_remuneracao,
                'total_remuneracao_formatado': _format_currency_br(total_remuneracao) if total_remuneracao else 'R$ 0,00'
            })
        
        return render_template(
            'colaboradores/form_colaborador.html',
            modo='editar',
            hoje=hoje,
            colaborador=colab_response.data,
            ultimo_historico=ultimo_historico,
            cargos=cargos.data if cargos.data else [],
            departamentos=departamentos.data if departamentos.data else [],
            empresas=empresas.data if empresas.data else [],
            gestores=colaboradores.data if colaboradores.data else [],
            info_atual=info_atual,
            dependentes=dependentes,
            contatos_emergencia=contatos_emergencia,
            beneficios_catalogo=BENEFICIOS_CATALOGO,
            is_editing=True
        )
    
    except Exception as e:
        print(f"[ERRO] Erro ao carregar colaborador: {str(e)}")
        flash(f'Erro ao carregar colaborador: {str(e)}', 'danger')
        return redirect(url_for('colaboradores.lista_colaboradores'))

@colaboradores_bp.route('/visualizar/<colaborador_id>')
def visualizar_colaborador(colaborador_id):
    """Página para visualizar detalhes completos do colaborador"""
    if not check_auth():
        return redirect(url_for('auth.login'))
    
    try:
        # Buscar colaborador
        colab_response = supabase_admin.table('rh_colaboradores')\
            .select('*')\
            .eq('id', colaborador_id)\
            .single()\
            .execute()
        
        if not colab_response.data:
            flash('Colaborador não encontrado', 'warning')
            return redirect(url_for('colaboradores.lista_colaboradores'))

        colaborador_data = colab_response.data
        colaborador_data['data_nascimento_br'] = format_date_br(colaborador_data.get('data_nascimento'))
        colaborador_data['data_admissao_br'] = format_date_br(colaborador_data.get('data_admissao'))
        colaborador_data['data_desligamento_br'] = format_date_br(colaborador_data.get('data_desligamento'))
        colaborador_data['rg_data_expedicao_br'] = format_date_br(colaborador_data.get('rg_data_expedicao'))

        # Buscar histórico completo de RH
        historico = supabase_admin.table('rh_historico_colaborador')\
            .select('*, cargo:rh_cargos(nome_cargo), departamento:rh_departamentos(nome_departamento), empresa:rh_empresas(razao_social)')\
            .eq('colaborador_id', colaborador_id)\
            .order('data_evento', desc=True)\
            .order('created_at', desc=True)\
            .execute()

        historico_data = historico.data if historico.data else []
        historico_data.sort(
            key=lambda evento: (
                _ensure_date(evento.get('data_evento')) or date.min,
                _ensure_datetime(evento.get('created_at')) or datetime.min,
                str(evento.get('id') or '')
            ),
            reverse=True
        )
        for evento in historico_data:
            status_atual = (evento.get('status_contabilidade') or '').strip()
            evento['status_contabilidade'] = status_atual or 'Pendente'
            evento['data_evento_br'] = format_date_br(evento.get('data_evento'))
            evento['hora_evento_br'] = _format_time_br(evento.get('created_at'))

            beneficios_dict = _coletar_beneficios_anteriores(evento)
            beneficios_view = build_beneficios_view(beneficios_dict)

            salario_atual = _normalizar_valor_decimal(evento.get('salario_mensal')) or 0.0
            evento['salario_formatado'] = _format_currency_br(salario_atual) if salario_atual else None
            evento['beneficios_view'] = beneficios_view
            evento['beneficios_total'] = beneficios_view['total_geral']
            evento['beneficios_total_formatado'] = beneficios_view['total_geral_formatado']

            total_remuneracao = salario_atual + beneficios_view['total_geral']
            evento['total_remuneracao'] = total_remuneracao if (salario_atual or beneficios_view['has_beneficios']) else None
            evento['total_remuneracao_formatado'] = (
                _format_currency_br(total_remuneracao)
                if evento['total_remuneracao'] is not None
                else None
            )

        ultimo_evento = historico_data[0] if historico_data else _buscar_ultimo_historico(colaborador_id)
        info_atual = None

        if ultimo_evento:
            beneficios_dict = _coletar_beneficios_anteriores(ultimo_evento)
            beneficios_view = build_beneficios_view(beneficios_dict)
            salario_atual = _normalizar_valor_decimal(ultimo_evento.get('salario_mensal'))
            salario_para_total = salario_atual if salario_atual is not None else 0.0
            total_remuneracao = salario_para_total + beneficios_view['total_geral']

            info_atual = {
                'salario_mensal': salario_atual,
                'salario_formatado': _format_currency_br(salario_atual) if salario_atual is not None else None,
                'beneficios_jsonb': beneficios_dict,
                'beneficios_view': beneficios_view,
                'beneficios_total': beneficios_view['total_geral'],
                'beneficios_total_formatado': beneficios_view['total_geral_formatado'],
                'remuneracao_adicional_total': beneficios_view['remuneracao_adicional']['total'],
                'remuneracao_adicional_total_formatado': beneficios_view['remuneracao_adicional']['total_formatado'],
                'beneficios_padrao_total': beneficios_view['beneficios_padrao']['total'],
                'beneficios_padrao_total_formatado': beneficios_view['beneficios_padrao']['total_formatado'],
                'total_remuneracao': total_remuneracao,
                'total_remuneracao_formatado': _format_currency_br(total_remuneracao) if total_remuneracao is not None else 'R$ 0,00',
                'data_evento': ultimo_evento.get('data_evento')
            }
        
        # Buscar dados de candidatura (se houver)
        candidatura = None
        try:
            candidatura_response = supabase_admin.table('rh_candidatos')\
                .select('*, vaga:rh_vagas(titulo_vaga, tipo_vaga, local_trabalho)')\
                .eq('colaborador_id', colaborador_id)\
                .execute()
            
            if candidatura_response.data and len(candidatura_response.data) > 0:
                candidatura = candidatura_response.data[0]
                print(f"[INFO] Candidatura encontrada para colaborador {colaborador_id}: {candidatura.get('id')}")
                candidatura['data_candidatura_br'] = format_date_br(candidatura.get('data_candidatura'))
                candidatura['updated_at_br'] = format_date_br(candidatura.get('updated_at'))
        except Exception as e:
            print(f"[AVISO] Erro ao buscar candidatura (pode ser que o campo ainda não exista): {str(e)}")
            # Não falha se não encontrar candidatura, é opcional

        dependentes_response = supabase_admin.table('rh_colaborador_dependentes')\
            .select('*')\
            .eq('colaborador_id', colaborador_id)\
            .order('nome_completo')\
            .execute()

        dependentes = []
        for dependente in dependentes_response.data or []:
            data_nascimento_dt = _ensure_date(dependente.get('data_nascimento'))
            dependente['data_nascimento_br'] = format_date_br(data_nascimento_dt)
            dependente['data_nascimento_iso'] = data_nascimento_dt.isoformat() if data_nascimento_dt else ''
            dependente['idade'] = _calculate_age(data_nascimento_dt)
            dependentes.append(dependente)

        contatos_response = supabase_admin.table('rh_colaborador_contatos_emergencia')\
            .select('*')\
            .eq('colaborador_id', colaborador_id)\
            .order('nome_contato')\
            .execute()

        contatos_emergencia = []
        for contato in contatos_response.data or []:
            contato['telefone_contato'] = (contato.get('telefone_contato') or '').strip()
            contatos_emergencia.append(contato)
        
        return render_template(
            'colaboradores/visualizar_colaborador.html',
            colaborador=colaborador_data,
            historico=historico_data,
            candidatura=candidatura,
            dependentes=dependentes,
            contatos_emergencia=contatos_emergencia,
            info_atual=info_atual,
            beneficios_catalogo=BENEFICIOS_CATALOGO
        )
    
    except Exception as e:
        print(f"[ERRO] Erro ao visualizar colaborador: {str(e)}")
        flash(f'Erro ao visualizar colaborador: {str(e)}', 'danger')
        return redirect(url_for('colaboradores.lista_colaboradores'))

# =====================================================================
# ROTAS DE API (JSON)
# =====================================================================

@colaboradores_bp.route('/api/colaboradores', methods=['GET'])
@perfil_or_bypass_required('rh', 'colaboradores')
def api_get_colaboradores():
    """API: Lista todos os colaboradores"""
    try:
        status = request.args.get('status')
        
        query = supabase_admin.table('vw_colaboradores_atual').select('*')
        
        if status:
            query = query.eq('status', status)
        
        response = query.order('nome_completo').execute()
        
        return jsonify({
            'success': True,
            'data': response.data,
            'count': len(response.data) if response.data else 0
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@colaboradores_bp.route('/api/colaboradores/<colaborador_id>', methods=['GET'])
@perfil_or_bypass_required('rh', 'colaboradores')
def api_get_colaborador(colaborador_id):
    """API: Detalhes de um colaborador específico"""
    try:
        colab_response = supabase_admin.table('rh_colaboradores')\
            .select('*')\
            .eq('id', colaborador_id)\
            .single()\
            .execute()
        
        if not colab_response.data:
            return jsonify({'error': 'Colaborador não encontrado'}), 404

        info_atual = None
        try:
            rpc_response = supabase_admin.rpc(
                'get_colaborador_info_atual',
                {'p_colaborador_id': colaborador_id}
            ).execute()
            if rpc_response.data:
                info_atual = rpc_response.data[0]
                beneficios_atual = normalize_beneficios(info_atual.get('beneficios_jsonb'))
                info_atual['beneficios_jsonb'] = beneficios_atual
                beneficios_view = build_beneficios_view(beneficios_atual)
                info_atual['beneficios_view'] = beneficios_view
                info_atual['beneficios_total'] = beneficios_view['total_geral']
                info_atual['beneficios_total_formatado'] = beneficios_view['total_geral_formatado']
                info_atual['remuneracao_adicional_total'] = beneficios_view['remuneracao_adicional']['total']
                info_atual['remuneracao_adicional_total_formatado'] = beneficios_view['remuneracao_adicional']['total_formatado']
                info_atual['beneficios_padrao_total'] = beneficios_view['beneficios_padrao']['total']
                info_atual['beneficios_padrao_total_formatado'] = beneficios_view['beneficios_padrao']['total_formatado']
        except Exception as exc:
            print(f"[AVISO] Falha ao obter dados atuais do colaborador via RPC: {exc}")

        return jsonify({
            'success': True,
            'data': colab_response.data,
            'info_atual': info_atual
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@colaboradores_bp.route('/api/colaboradores', methods=['POST'])
@perfil_or_bypass_required('rh', 'colaboradores')
def api_create_colaborador():
    """API: Criar novo colaborador"""
    try:
        data = request.get_json()
        
        # Validar campos obrigatórios
        required_fields = ['nome_completo', 'cpf', 'data_nascimento', 'data_admissao']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Campo obrigatório: {field}'}), 400
        
        # Verificar se CPF já existe
        existing = supabase_admin.table('rh_colaboradores')\
            .select('id')\
            .eq('cpf', data['cpf'])\
            .execute()
        
        if existing.data:
            return jsonify({'error': 'CPF já cadastrado'}), 409
        
        # Preparar dados do colaborador
        colaborador_data = {
            'nome_completo': data['nome_completo'],
            'cpf': data['cpf'],
            'data_nascimento': data['data_nascimento'],
            'data_admissao': data['data_admissao'],
            'status': 'Ativo'
        }
        
        # Campos opcionais
        optional_fields = [
            'email_corporativo', 'matricula', 'genero', 'raca_cor', 'nacionalidade',
            'pis_pasep', 'ctps_numero', 'ctps_serie', 'cnh_numero', 'tel_contato',
            'endereco_completo', 'escolaridade'
        ]
        
        for field in optional_fields:
            if field in data:
                value = data[field]
                # Evita persistir strings vazias como valores válidos
                if isinstance(value, str) and value.strip() == '':
                    continue
                colaborador_data[field] = value
        
        # Inserir colaborador
        colab_response = supabase_admin.table('rh_colaboradores')\
            .insert(colaborador_data)\
            .execute()
        
        if not colab_response.data:
            return jsonify({'error': 'Erro ao criar colaborador'}), 500
        
        colaborador_id = colab_response.data[0]['id']
        
        # Criar registro de admissão no histórico
        historico_data = {
            'colaborador_id': colaborador_id,
            'data_evento': data['data_admissao'],
            'tipo_evento': 'Admissão',
            'descricao_e_motivos': data.get('observacoes', 'Admissão inicial')
        }
        
        # Dados opcionais do histórico
        def set_if_present(dest, field_name):
            if field_name in data:
                value = data[field_name]
                if isinstance(value, str):
                    value = value.strip()
                if value not in (None, '', []):
                    dest[field_name] = value

        set_if_present(historico_data, 'cargo_id')
        set_if_present(historico_data, 'departamento_id')
        set_if_present(historico_data, 'empresa_id')
        set_if_present(historico_data, 'gestor_id')
        set_if_present(historico_data, 'tipo_contrato')
        set_if_present(historico_data, 'modelo_trabalho')

        salario_inicial = _normalizar_valor_decimal(data.get('salario_mensal'))
        if salario_inicial is not None:
            historico_data['salario_mensal'] = salario_inicial

        beneficios_iniciais = _parse_beneficios_payload(data)
        if has_beneficios(beneficios_iniciais):
            historico_data['beneficios_jsonb'] = beneficios_iniciais
        
        # Inserir no histórico
        _registrar_evento_historico(historico_data)
        
        # 🔥 NOVO: Se veio de um candidato, vincular
        if 'candidato_id' in data and data['candidato_id']:
            print(f"🔗 Vinculando candidato {data['candidato_id']} ao colaborador {colaborador_id}")
            supabase_admin.table('rh_candidatos')\
                .update({'colaborador_id': colaborador_id, 'foi_contratado': True})\
                .eq('id', data['candidato_id'])\
                .execute()
            print("✅ Vínculo criado com sucesso!")
        
        return jsonify({
            'success': True,
            'colaborador_id': colaborador_id,
            'message': 'Colaborador criado com sucesso'
        }), 201
    
    except Exception as e:
        print(f"[ERRO] Erro ao criar colaborador: {str(e)}")
        return jsonify({'error': str(e)}), 500

@colaboradores_bp.route('/api/colaboradores/<colaborador_id>', methods=['PUT'])
@perfil_or_bypass_required('rh', 'colaboradores')
def api_update_colaborador(colaborador_id):
    """API: Atualizar colaborador existente"""
    try:
        data = request.get_json()
        
        # Verificar se colaborador existe
        existing = supabase_admin.table('rh_colaboradores')\
            .select('*')\
            .eq('id', colaborador_id)\
            .single()\
            .execute()
        
        if not existing.data:
            return jsonify({'error': 'Colaborador não encontrado'}), 404

        # Campos que não podem ser atualizados diretamente nesta rota
        data.pop('salario_mensal', None)
        
        # Preparar dados para atualização
        update_data = {}
        
        # Campos que podem ser atualizados
        updatable_fields = [
            'nome_completo', 'email_corporativo', 'matricula', 'data_nascimento',
            'genero', 'raca_cor', 'nacionalidade', 'pis_pasep', 'ctps_numero',
            'ctps_serie', 'cnh_numero', 'tel_contato', 'endereco_completo',
            'status', 'escolaridade'
        ]
        
        for field in updatable_fields:
            if field in data:
                value = data[field]
                if isinstance(value, str) and value.strip() == '':
                    continue
                update_data[field] = value
        
        # Atualizar colaborador
        if update_data:
            supabase_admin.table('rh_colaboradores')\
                .update(update_data)\
                .eq('id', colaborador_id)\
                .execute()

        # Registrar alterações estruturais no histórico (sem alterar salário por aqui)
        ultimo_historico = _buscar_ultimo_historico(colaborador_id)
        campos_movimentacao = ['cargo_id', 'departamento_id', 'gestor_id', 'tipo_contrato', 'modelo_trabalho']
        houve_alteracao = False
        snapshot = {}

        for campo in campos_movimentacao:
            valor_novo = data.get(campo)
            valor_novo_normalizado = valor_novo.strip() if isinstance(valor_novo, str) else valor_novo
            valor_atual = ultimo_historico.get(campo) if ultimo_historico else None

            if valor_novo_normalizado not in (None, '', []):
                snapshot[campo] = valor_novo_normalizado
                if str(valor_novo_normalizado) != str(valor_atual):
                    houve_alteracao = True
            elif valor_atual not in (None, '', []):
                snapshot[campo] = valor_atual

        observacoes = data.get('observacoes')
        if isinstance(observacoes, str):
            observacoes = observacoes.strip()
        if observacoes:
            houve_alteracao = True

        if houve_alteracao:
            historico_data = {
                'colaborador_id': colaborador_id,
                'data_evento': data.get('data_evento') or datetime.now().strftime('%Y-%m-%d'),
                'tipo_evento': 'Alteração Estrutural',
                'descricao_e_motivos': observacoes or 'Atualização cadastral'
            }

            historico_data.update(snapshot)

            # Garantir consistência das informações copiando valores já existentes
            _copiar_campos_validos(
                historico_data,
                ultimo_historico,
                ['empresa_id', 'salario_mensal']
            )

            _registrar_evento_historico(historico_data)
        
        # Buscar dados atualizados do colaborador
        colab_atualizado = supabase_admin.table('rh_colaboradores')\
            .select('*')\
            .eq('id', colaborador_id)\
            .single()\
            .execute()
        
        return jsonify({
            'success': True,
            'message': 'Colaborador atualizado com sucesso',
            'data': colab_atualizado.data
        }), 200
    
    except Exception as e:
        print(f"[ERRO] Erro ao atualizar colaborador: {str(e)}")
        return jsonify({'error': str(e)}), 500


def _buscar_colaborador_ativo(colaborador_id):
    response = supabase_admin.table('rh_colaboradores')\
        .select('*')\
        .eq('id', colaborador_id)\
        .single()\
        .execute()
    return response.data if response.data else None


def _buscar_ultimo_historico(colaborador_id):
    response = supabase_admin.table('rh_historico_colaborador')\
        .select('*')\
        .eq('colaborador_id', colaborador_id)\
        .order('data_evento', desc=True)\
        .order('created_at', desc=True)\
        .limit(1)\
        .execute()
    if response.data:
        return response.data[0]
    return None


def _registrar_evento_historico(historico_data):
    payload = dict(historico_data)
    payload['status_contabilidade'] = payload.get('status_contabilidade') or 'Pendente'

    beneficios = payload.get('beneficios_jsonb')
    if isinstance(beneficios, dict) and not beneficios:
        payload.pop('beneficios_jsonb', None)

    response = supabase_admin.table('rh_historico_colaborador').insert(payload).execute()
    if not response.data:
        return None

    evento = response.data[0]
    evento_id = evento.get('id')

    if evento_id:
        try:
            event_notifier.notify_accounting_new_event(str(evento_id))
        except Exception as exc:  # pragma: no cover
            print(f"[NOTIFY] Falha ao notificar contabilidade: {exc}")

    return evento


def _copiar_campos_validos(destino, origem, campos):
    if not origem:
        return
    for campo in campos:
        valor = origem.get(campo)
        if valor not in (None, ''):
            destino[campo] = valor


def _montar_dados_adicionais_historico(historico, mapeamentos):
    if not historico:
        return {}
    dados = {}
    for origem, destino in mapeamentos:
        valor = historico.get(origem)
        if valor not in (None, ''):
            dados[destino] = valor
    return dados

@colaboradores_bp.route('/api/colaboradores/<colaborador_id>/promover', methods=['POST'])
@perfil_or_bypass_required('rh', 'colaboradores')
def api_promover_colaborador(colaborador_id):
    try:
        payload = request.get_json() or {}
        data_evento = payload.get('data_evento')
        novo_cargo_id = payload.get('novo_cargo_id')
        novo_salario = payload.get('novo_salario')

        if not all([data_evento, novo_cargo_id, novo_salario]):
            return jsonify({'error': 'Campos obrigatórios ausentes'}), 400

        colaborador = _buscar_colaborador_ativo(colaborador_id)
        if not colaborador:
            return jsonify({'error': 'Colaborador não encontrado'}), 404

        if colaborador.get('status') == 'Inativo':
            return jsonify({'error': 'Colaborador inativo não pode ser promovido'}), 400

        ultimo_historico = _buscar_ultimo_historico(colaborador_id)

        novo_salario_valor = _normalizar_valor_decimal(novo_salario)
        if novo_salario_valor is None:
            return jsonify({'error': 'Valor de salário inválido'}), 400

        dados_adicionais = _montar_dados_adicionais_historico(
            ultimo_historico,
            [('cargo_id', 'cargo_anterior_id'), ('salario_mensal', 'salario_anterior')]
        )

        historico_data = {
            'colaborador_id': colaborador_id,
            'data_evento': data_evento,
            'tipo_evento': 'Promoção',
            'cargo_id': novo_cargo_id,
            'salario_mensal': novo_salario_valor,
            'descricao_e_motivos': payload.get('descricao') or 'Promoção registrada'
        }

        _copiar_campos_validos(
            historico_data,
            ultimo_historico,
            ['departamento_id', 'gestor_id', 'empresa_id', 'tipo_contrato', 'modelo_trabalho']
        )

        if dados_adicionais:
            historico_data['dados_adicionais_jsonb'] = dados_adicionais

        beneficios_novos = _parse_beneficios_payload(payload)
        if has_beneficios(beneficios_novos):
            historico_data['beneficios_jsonb'] = beneficios_novos
        else:
            beneficios_atuais = _coletar_beneficios_anteriores(ultimo_historico)
            if has_beneficios(beneficios_atuais):
                historico_data['beneficios_jsonb'] = beneficios_atuais

        _registrar_evento_historico(historico_data)

        return jsonify({'success': True}), 201
    except Exception as e:
        print(f"[ERRO] Erro ao promover colaborador: {str(e)}")
        return jsonify({'error': str(e)}), 500


@colaboradores_bp.route('/api/colaboradores/<colaborador_id>/reajustar', methods=['POST'])
@perfil_or_bypass_required('rh', 'colaboradores')
def api_reajustar_salario(colaborador_id):
    try:
        payload = request.get_json() or {}
        data_evento = payload.get('data_evento')
        novo_salario = payload.get('novo_salario')

        if not all([data_evento, novo_salario]):
            return jsonify({'error': 'Campos obrigatórios ausentes'}), 400

        colaborador = _buscar_colaborador_ativo(colaborador_id)
        if not colaborador:
            return jsonify({'error': 'Colaborador não encontrado'}), 404

        if colaborador.get('status') == 'Inativo':
            return jsonify({'error': 'Colaborador inativo não pode receber reajuste'}), 400

        ultimo_historico = _buscar_ultimo_historico(colaborador_id)

        novo_salario_valor = _normalizar_valor_decimal(novo_salario)
        if novo_salario_valor is None:
            return jsonify({'error': 'Valor de salário inválido'}), 400

        dados_adicionais = _montar_dados_adicionais_historico(
            ultimo_historico,
            [('salario_mensal', 'salario_anterior')]
        )

        historico_data = {
            'colaborador_id': colaborador_id,
            'data_evento': data_evento,
            'tipo_evento': 'Alteração Salarial',
            'salario_mensal': novo_salario_valor,
            'descricao_e_motivos': payload.get('descricao') or 'Reajuste salarial registrado'
        }

        _copiar_campos_validos(
            historico_data,
            ultimo_historico,
            ['cargo_id', 'departamento_id', 'gestor_id', 'empresa_id', 'tipo_contrato', 'modelo_trabalho']
        )

        if dados_adicionais:
            historico_data['dados_adicionais_jsonb'] = dados_adicionais

        beneficios_novos = _parse_beneficios_payload(payload)
        if has_beneficios(beneficios_novos):
            historico_data['beneficios_jsonb'] = beneficios_novos
        else:
            beneficios_atuais = _coletar_beneficios_anteriores(ultimo_historico)
            if has_beneficios(beneficios_atuais):
                historico_data['beneficios_jsonb'] = beneficios_atuais

        _registrar_evento_historico(historico_data)

        return jsonify({'success': True}), 201
    except Exception as e:
        print(f"[ERRO] Erro ao reajustar salário: {str(e)}")
        return jsonify({'error': str(e)}), 500


@colaboradores_bp.route('/api/colaboradores/<colaborador_id>/alterar-beneficios', methods=['POST'])
@perfil_or_bypass_required('rh', 'colaboradores')
def api_alterar_beneficios(colaborador_id):
    try:
        payload = request.get_json() or {}
        data_evento = payload.get('data_evento')
        descricao = (payload.get('descricao') or '').strip()
        beneficios_payload = payload.get('beneficios') or {}

        if not data_evento or not descricao:
            return jsonify({'error': 'Informe a data e o motivo da alteração.'}), 400

        colaborador = _buscar_colaborador_ativo(colaborador_id)
        if not colaborador:
            return jsonify({'error': 'Colaborador não encontrado.'}), 404

        ultimo_historico = _buscar_ultimo_historico(colaborador_id)
        if not ultimo_historico:
            return jsonify({'error': 'Ainda não há histórico para este colaborador.'}), 400

        beneficios_normalizados = normalize_beneficios(beneficios_payload)
        if not has_beneficios(beneficios_normalizados):
            return jsonify({'error': 'Informe ao menos um benefício válido.'}), 400

        beneficios_anteriores = _coletar_beneficios_anteriores(ultimo_historico)

        historico_data = {
            'colaborador_id': colaborador_id,
            'data_evento': data_evento,
            'tipo_evento': 'Alteração de Benefícios',
            'descricao_e_motivos': descricao,
            'beneficios_jsonb': beneficios_normalizados
        }

        _copiar_campos_validos(
            historico_data,
            ultimo_historico,
            ['cargo_id', 'departamento_id', 'gestor_id', 'empresa_id', 'tipo_contrato', 'modelo_trabalho', 'salario_mensal']
        )

        beneficios_anteriores_formatados = None
        if has_beneficios(beneficios_anteriores):
            historico_data['dados_adicionais_jsonb'] = {
                'beneficios_anteriores': beneficios_anteriores
            }
            beneficios_anteriores_formatados = beneficios_anteriores

        evento = _registrar_evento_historico(historico_data)
        if not evento:
            return jsonify({'error': 'Não foi possível registrar o evento de alteração de benefícios.'}), 500

        beneficios_view = build_beneficios_view(beneficios_normalizados)
        salario_atual = _normalizar_valor_decimal(historico_data.get('salario_mensal'))
        salario_para_total = salario_atual if salario_atual is not None else 0.0
        beneficios_total = beneficios_view.get('total_geral', 0.0) or 0.0
        total_remuneracao = salario_para_total + beneficios_total

        return jsonify({
            'success': True,
            'evento': {
                'id': evento.get('id'),
                'data_evento': evento.get('data_evento'),
                'tipo_evento': evento.get('tipo_evento'),
                'descricao_e_motivos': evento.get('descricao_e_motivos'),
                'beneficios_jsonb': beneficios_normalizados,
                'beneficios': beneficios_view,
                'beneficios_anteriores': beneficios_anteriores_formatados,
                'totais': {
                    'beneficios_formatado': beneficios_view.get('total_geral_formatado'),
                    'salario_formatado': _format_currency_br(salario_atual) if salario_atual is not None else None,
                    'total_remuneracao_formatado': _format_currency_br(total_remuneracao)
                }
            }
        }), 201

    except Exception as exc:
        print(f"[ERRO] Erro ao alterar benefícios: {exc}")
        return jsonify({'error': str(exc)}), 500


@colaboradores_bp.route('/api/colaboradores/<colaborador_id>/transferir', methods=['POST'])
@perfil_or_bypass_required('rh', 'colaboradores')
def api_transferir_colaborador(colaborador_id):
    try:
        payload = request.get_json() or {}
        data_evento = payload.get('data_evento')
        novo_departamento = payload.get('novo_departamento_id')

        if not all([data_evento, novo_departamento]):
            return jsonify({'error': 'Campos obrigatórios ausentes'}), 400

        colaborador = _buscar_colaborador_ativo(colaborador_id)
        if not colaborador:
            return jsonify({'error': 'Colaborador não encontrado'}), 404

        if colaborador.get('status') == 'Inativo':
            return jsonify({'error': 'Colaborador inativo não pode ser transferido'}), 400

        ultimo_historico = _buscar_ultimo_historico(colaborador_id)

        dados_adicionais = _montar_dados_adicionais_historico(
            ultimo_historico,
            [('departamento_id', 'departamento_anterior_id'), ('gestor_id', 'gestor_anterior_id')]
        )

        novo_gestor = payload.get('novo_gestor_id')

        historico_data = {
            'colaborador_id': colaborador_id,
            'data_evento': data_evento,
            'tipo_evento': 'Alteração Estrutural',
            'departamento_id': novo_departamento,
            'gestor_id': novo_gestor if novo_gestor not in (None, '') else (ultimo_historico.get('gestor_id') if ultimo_historico else None),
            'descricao_e_motivos': payload.get('descricao') or 'Transferência registrada'
        }

        _copiar_campos_validos(
            historico_data,
            ultimo_historico,
            ['cargo_id', 'salario_mensal', 'empresa_id', 'tipo_contrato', 'modelo_trabalho']
        )

        if dados_adicionais:
            historico_data['dados_adicionais_jsonb'] = dados_adicionais

        _registrar_evento_historico(historico_data)

        return jsonify({'success': True}), 201
    except Exception as e:
        print(f"[ERRO] Erro ao transferir colaborador: {str(e)}")
        return jsonify({'error': str(e)}), 500


@colaboradores_bp.route('/api/colaboradores/<colaborador_id>/registrar-evento', methods=['POST'])
@perfil_or_bypass_required('rh', 'colaboradores')
def api_registrar_evento(colaborador_id):
    try:
        payload = request.get_json() or {}

        tipo_evento = payload.get('tipo_evento')
        data_inicio = payload.get('data_inicio')
        data_fim = payload.get('data_fim')

        if not all([tipo_evento, data_inicio, data_fim]):
            return jsonify({'error': 'Campos obrigatórios ausentes'}), 400

        colaborador = _buscar_colaborador_ativo(colaborador_id)
        if not colaborador:
            return jsonify({'error': 'Colaborador não encontrado'}), 404

        evento_data = {
            'colaborador_id': colaborador_id,
            'tipo_evento': tipo_evento,
            'data_inicio': data_inicio,
            'data_fim': data_fim,
            'status': payload.get('status') or 'Realizado',
            'descricao': payload.get('descricao')
        }

        supabase_admin.table('rh_eventos_colaborador').insert(evento_data).execute()

        return jsonify({'success': True}), 201
    except Exception as e:
        print(f"[ERRO] Erro ao registrar evento de colaborador: {str(e)}")
        return jsonify({'error': str(e)}), 500


def _carregar_dependente(dependente_id):
    return supabase_admin.table('rh_colaborador_dependentes')\
        .select('*')\
        .eq('id', dependente_id)\
        .single()\
        .execute()


def _carregar_contato(contato_id):
    return supabase_admin.table('rh_colaborador_contatos_emergencia')\
        .select('*')\
        .eq('id', contato_id)\
        .single()\
        .execute()


@colaboradores_bp.route('/api/colaboradores/<colaborador_id>/dependentes', methods=['GET'])
@perfil_or_bypass_required('rh', 'colaboradores')
def api_listar_dependentes(colaborador_id):
    try:
        resposta = supabase_admin.table('rh_colaborador_dependentes')\
            .select('*')\
            .eq('colaborador_id', colaborador_id)\
            .order('nome_completo')\
            .execute()

        dependentes = []
        for dependente in resposta.data or []:
            data_nascimento = _ensure_date(dependente.get('data_nascimento'))
            dependente['data_nascimento_br'] = format_date_br(data_nascimento)
            dependente['data_nascimento_iso'] = data_nascimento.isoformat() if data_nascimento else ''
            dependente['idade'] = _calculate_age(data_nascimento)
            dependentes.append(dependente)

        return jsonify({'success': True, 'data': dependentes}), 200
    except Exception as exc:
        print(f"[ERRO] Falha ao listar dependentes: {exc}")
        return jsonify({'error': str(exc)}), 500


@colaboradores_bp.route('/api/colaboradores/<colaborador_id>/dependentes', methods=['POST'])
@perfil_or_bypass_required('rh', 'colaboradores')
def api_criar_dependente(colaborador_id):
    try:
        payload = request.get_json() or {}

        nome = (payload.get('nome_completo') or '').strip()
        parentesco = (payload.get('parentesco') or '').strip()
        data_nascimento = payload.get('data_nascimento')

        if not nome or not parentesco or not data_nascimento:
            return jsonify({'error': 'Nome, parentesco e data de nascimento são obrigatórios.'}), 400

        data_dt = _ensure_date(data_nascimento)
        if not data_dt:
            return jsonify({'error': 'Data de nascimento inválida.'}), 400

        registro = {
            'colaborador_id': colaborador_id,
            'nome_completo': nome,
            'parentesco': parentesco,
            'data_nascimento': data_dt.isoformat()
        }

        resposta = supabase_admin.table('rh_colaborador_dependentes').insert(registro).execute()
        dependente = resposta.data[0] if resposta.data else None

        if not dependente:
            return jsonify({'error': 'Não foi possível criar o dependente.'}), 500

        data_dt = _ensure_date(dependente.get('data_nascimento'))
        dependente['data_nascimento_br'] = format_date_br(data_dt)
        dependente['data_nascimento_iso'] = data_dt.isoformat() if data_dt else ''
        dependente['idade'] = _calculate_age(data_dt)

        return jsonify({'success': True, 'data': dependente}), 201
    except Exception as exc:
        print(f"[ERRO] Falha ao criar dependente: {exc}")
        return jsonify({'error': str(exc)}), 500


@colaboradores_bp.route('/api/dependentes/<dependente_id>', methods=['PUT'])
@perfil_or_bypass_required('rh', 'colaboradores')
def api_atualizar_dependente(dependente_id):
    try:
        payload = request.get_json() or {}
        resposta = _carregar_dependente(dependente_id)

        if not resposta.data:
            return jsonify({'error': 'Dependente não encontrado.'}), 404

        atualizacoes = {}

        if 'nome_completo' in payload:
            nome = (payload.get('nome_completo') or '').strip()
            if nome:
                atualizacoes['nome_completo'] = nome

        if 'parentesco' in payload:
            parentesco = (payload.get('parentesco') or '').strip()
            if parentesco:
                atualizacoes['parentesco'] = parentesco

        if 'data_nascimento' in payload:
            data_dt = _ensure_date(payload.get('data_nascimento'))
            if not data_dt:
                return jsonify({'error': 'Data de nascimento inválida.'}), 400
            atualizacoes['data_nascimento'] = data_dt.isoformat()

        if not atualizacoes:
            return jsonify({'error': 'Nenhum dado válido para atualizar.'}), 400

        supabase_admin.table('rh_colaborador_dependentes')\
            .update(atualizacoes)\
            .eq('id', dependente_id)\
            .execute()

        resposta = _carregar_dependente(dependente_id)
        dependente = resposta.data if resposta.data else {}
        data_dt = _ensure_date(dependente.get('data_nascimento'))
        dependente['data_nascimento_br'] = format_date_br(data_dt)
        dependente['data_nascimento_iso'] = data_dt.isoformat() if data_dt else ''
        dependente['idade'] = _calculate_age(data_dt)

        return jsonify({'success': True, 'data': dependente}), 200
    except Exception as exc:
        print(f"[ERRO] Falha ao atualizar dependente: {exc}")
        return jsonify({'error': str(exc)}), 500


@colaboradores_bp.route('/api/dependentes/<dependente_id>', methods=['DELETE'])
@perfil_or_bypass_required('rh', 'colaboradores')
def api_excluir_dependente(dependente_id):
    try:
        resposta = _carregar_dependente(dependente_id)
        if not resposta.data:
            return jsonify({'error': 'Dependente não encontrado.'}), 404

        supabase_admin.table('rh_colaborador_dependentes')\
            .delete()\
            .eq('id', dependente_id)\
            .execute()

        return jsonify({'success': True}), 200
    except Exception as exc:
        print(f"[ERRO] Falha ao excluir dependente: {exc}")
        return jsonify({'error': str(exc)}), 500


@colaboradores_bp.route('/api/colaboradores/<colaborador_id>/contatos-emergencia', methods=['GET'])
@perfil_or_bypass_required('rh', 'colaboradores')
def api_listar_contatos_emergencia(colaborador_id):
    try:
        resposta = supabase_admin.table('rh_colaborador_contatos_emergencia')\
            .select('*')\
            .eq('colaborador_id', colaborador_id)\
            .order('nome_contato')\
            .execute()

        contatos = resposta.data if resposta.data else []
        return jsonify({'success': True, 'data': contatos}), 200
    except Exception as exc:
        print(f"[ERRO] Falha ao listar contatos de emergência: {exc}")
        return jsonify({'error': str(exc)}), 500


@colaboradores_bp.route('/api/colaboradores/<colaborador_id>/contatos-emergencia', methods=['POST'])
@perfil_or_bypass_required('rh', 'colaboradores')
def api_criar_contato_emergencia(colaborador_id):
    try:
        payload = request.get_json() or {}

        nome = (payload.get('nome_contato') or '').strip()
        telefone = (payload.get('telefone_contato') or '').strip()
        parentesco = (payload.get('parentesco') or '').strip() or None

        if not nome or not telefone:
            return jsonify({'error': 'Nome e telefone são obrigatórios.'}), 400

        registro = {
            'colaborador_id': colaborador_id,
            'nome_contato': nome,
            'telefone_contato': telefone,
            'parentesco': parentesco
        }

        resposta = supabase_admin.table('rh_colaborador_contatos_emergencia').insert(registro).execute()
        contato = resposta.data[0] if resposta.data else None

        if not contato:
            return jsonify({'error': 'Não foi possível criar o contato de emergência.'}), 500

        return jsonify({'success': True, 'data': contato}), 201
    except Exception as exc:
        print(f"[ERRO] Falha ao criar contato de emergência: {exc}")
        return jsonify({'error': str(exc)}), 500


@colaboradores_bp.route('/api/contatos-emergencia/<contato_id>', methods=['PUT'])
@perfil_or_bypass_required('rh', 'colaboradores')
def api_atualizar_contato_emergencia(contato_id):
    try:
        payload = request.get_json() or {}
        resposta = _carregar_contato(contato_id)

        if not resposta.data:
            return jsonify({'error': 'Contato de emergência não encontrado.'}), 404

        atualizacoes = {}

        if 'nome_contato' in payload:
            nome = (payload.get('nome_contato') or '').strip()
            if nome:
                atualizacoes['nome_contato'] = nome

        if 'telefone_contato' in payload:
            telefone = (payload.get('telefone_contato') or '').strip()
            if telefone:
                atualizacoes['telefone_contato'] = telefone

        if 'parentesco' in payload:
            parentesco = (payload.get('parentesco') or '').strip()
            atualizacoes['parentesco'] = parentesco or None

        if not atualizacoes:
            return jsonify({'error': 'Nenhum dado válido para atualizar.'}), 400

        supabase_admin.table('rh_colaborador_contatos_emergencia')\
            .update(atualizacoes)\
            .eq('id', contato_id)\
            .execute()

        resposta = _carregar_contato(contato_id)
        contato = resposta.data if resposta.data else {}
        return jsonify({'success': True, 'data': contato}), 200
    except Exception as exc:
        print(f"[ERRO] Falha ao atualizar contato de emergência: {exc}")
        return jsonify({'error': str(exc)}), 500


@colaboradores_bp.route('/api/contatos-emergencia/<contato_id>', methods=['DELETE'])
@perfil_or_bypass_required('rh', 'colaboradores')
def api_excluir_contato_emergencia(contato_id):
    try:
        resposta = _carregar_contato(contato_id)
        if not resposta.data:
            return jsonify({'error': 'Contato de emergência não encontrado.'}), 404

        supabase_admin.table('rh_colaborador_contatos_emergencia')\
            .delete()\
            .eq('id', contato_id)\
            .execute()

        return jsonify({'success': True}), 200
    except Exception as exc:
        print(f"[ERRO] Falha ao excluir contato de emergência: {exc}")
        return jsonify({'error': str(exc)}), 500


@colaboradores_bp.route('/api/colaboradores/<colaborador_id>/reativar', methods=['POST'])
@perfil_or_bypass_required('rh', 'colaboradores')
def api_reativar_colaborador(colaborador_id):
    """API: Reativar colaborador previamente desligado"""
    try:
        payload = request.get_json(silent=True) or {}

        existing = supabase_admin.table('rh_colaboradores')\
            .select('*')\
            .eq('id', colaborador_id)\
            .single()\
            .execute()

        if not existing.data:
            return jsonify({'error': 'Colaborador não encontrado'}), 404

        if existing.data.get('status') == 'Ativo':
            return jsonify({'error': 'Colaborador já está ativo'}), 400

        data_evento = payload.get('data_evento') or datetime.now().strftime('%Y-%m-%d')
        descricao = payload.get('descricao') or 'Reativação do colaborador'

        supabase_admin.table('rh_colaboradores')\
            .update({'status': 'Ativo', 'data_desligamento': None})\
            .eq('id', colaborador_id)\
            .execute()

        historico_data = {
            'colaborador_id': colaborador_id,
            'data_evento': data_evento,
            'tipo_evento': 'Reativação',
            'descricao_e_motivos': descricao
        }

        ultimo_historico = _buscar_ultimo_historico(colaborador_id)
        _copiar_campos_validos(
            historico_data,
            ultimo_historico,
            ['cargo_id', 'departamento_id', 'gestor_id', 'salario_mensal', 'empresa_id', 'tipo_contrato', 'modelo_trabalho']
        )

        _registrar_evento_historico(historico_data)

        return jsonify({'success': True}), 200
    except Exception as e:
        print(f"[ERRO] Erro ao reativar colaborador: {str(e)}")
        return jsonify({'error': str(e)}), 500

@colaboradores_bp.route('/api/colaboradores/<colaborador_id>', methods=['DELETE'])
@perfil_or_bypass_required('rh', 'colaboradores')
def api_delete_colaborador(colaborador_id):
    """API: Deletar colaborador (soft delete - marca como inativo)"""
    try:
        # Verificar se colaborador existe
        existing = supabase_admin.table('rh_colaboradores')\
            .select('*')\
            .eq('id', colaborador_id)\
            .single()\
            .execute()
        
        if not existing.data:
            return jsonify({'error': 'Colaborador não encontrado'}), 404
        
        # Soft delete - marcar como inativo
        update_response = supabase_admin.table('rh_colaboradores')\
            .update({
                'status': 'Inativo',
                'data_desligamento': datetime.now().strftime('%Y-%m-%d')
            })\
            .eq('id', colaborador_id)\
            .execute()
        
        # Obter dados opcionais do body (se houver)
        motivo = 'Desligamento'
        try:
            body_data = request.get_json(silent=True)
            if body_data and 'motivo' in body_data:
                motivo = body_data['motivo']
        except:
            pass
        
        # Criar registro de demissão no histórico
        historico_demissao = {
            'colaborador_id': colaborador_id,
            'data_evento': datetime.now().strftime('%Y-%m-%d'),
            'tipo_evento': 'Demissão',
            'descricao_e_motivos': motivo
        }
        _registrar_evento_historico(historico_demissao)
        
        # Buscar dados atualizados do colaborador
        colab_atualizado = supabase_admin.table('rh_colaboradores')\
            .select('*')\
            .eq('id', colaborador_id)\
            .single()\
            .execute()
        
        return jsonify({
            'success': True,
            'message': 'Colaborador desligado com sucesso',
            'data': colab_atualizado.data
        }), 200
    
    except Exception as e:
        print(f"[ERRO] Erro ao deletar colaborador: {str(e)}")
        return jsonify({'error': str(e)}), 500


# =====================================================================
# ROTA DE DEBUG PARA CSS
# =====================================================================
@colaboradores_bp.route('/debug/css-test')
def debug_css_test():
    """Página de teste para verificar se o CSS está carregando"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Teste CSS RH</title>
        <link rel="stylesheet" href="{url_for('colaboradores.static', filename='colaboradores/colaboradores.css')}?v=2.0">
    </head>
    <body>
        <h1>Teste de CSS - Módulo RH</h1>
        <p>URL do CSS: {url_for('colaboradores.static', filename='colaboradores/colaboradores.css')}</p>
        <p>Blueprint name: {colaboradores_bp.name}</p>
        <p>Static URL path: {colaboradores_bp.static_url_path}</p>
        
        <div class="btn-group btn-group-sm" style="margin: 20px;">
            <button class="btn btn-outline-info">
                <i class="fas fa-eye"></i>
            </button>
            <button class="btn btn-outline-primary">
                <i class="fas fa-edit"></i>
            </button>
            <button class="btn btn-outline-secondary">
                <i class="fas fa-ellipsis-v"></i>
            </button>
        </div>
        
        <p>Se os botões acima aparecerem corretamente estilizados, o CSS está carregando!</p>
    </body>
    </html>
    """

