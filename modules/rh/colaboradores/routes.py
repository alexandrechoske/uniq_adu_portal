"""
Sub-módulo de Colaboradores - Gestão de RH
Gerencia o CRUD completo de colaboradores
"""

from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash
from extensions import supabase_admin
from modules.auth.routes import login_required
from decorators.perfil_decorators import perfil_required
from datetime import datetime
import os

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
            gestores=gestores_response.data if gestores_response.data else []
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
            .limit(1)\
            .execute()
        
        ultimo_historico = historico.data[0] if historico.data else {}

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
        
        # Buscar histórico completo de RH
        historico = supabase_admin.table('rh_historico_colaborador')\
            .select('*, cargo:rh_cargos(nome_cargo), departamento:rh_departamentos(nome_departamento), empresa:rh_empresas(razao_social)')\
            .eq('colaborador_id', colaborador_id)\
            .order('data_evento', desc=True)\
            .execute()

        historico_data = historico.data if historico.data else []
        for evento in historico_data:
            status_atual = (evento.get('status_contabilidade') or '').strip()
            evento['status_contabilidade'] = status_atual or 'Pendente'
        
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
        except Exception as e:
            print(f"[AVISO] Erro ao buscar candidatura (pode ser que o campo ainda não exista): {str(e)}")
            # Não falha se não encontrar candidatura, é opcional
        
        return render_template(
            'colaboradores/visualizar_colaborador.html',
            colaborador=colab_response.data,
            historico=historico_data,
            candidatura=candidatura
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
        
        return jsonify({
            'success': True,
            'data': colab_response.data
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
        set_if_present(historico_data, 'salario_mensal')
        set_if_present(historico_data, 'tipo_contrato')
        set_if_present(historico_data, 'modelo_trabalho')
        
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
        .limit(1)\
        .execute()
    if response.data:
        return response.data[0]
    return None


def _registrar_evento_historico(historico_data):
    payload = dict(historico_data)
    payload['status_contabilidade'] = payload.get('status_contabilidade') or 'Pendente'

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


def _normalizar_valor_decimal(valor):
    if valor in (None, ''):
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    try:
        valor_str = str(valor)
        valor_str = valor_str.replace('R$', '').replace(' ', '')
        valor_str = valor_str.replace('.', '').replace(',', '.')
        if valor_str == '':
            return None
        return float(valor_str)
    except (ValueError, TypeError):
        return None


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

        _registrar_evento_historico(historico_data)

        return jsonify({'success': True}), 201
    except Exception as e:
        print(f"[ERRO] Erro ao reajustar salário: {str(e)}")
        return jsonify({'error': str(e)}), 500


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

