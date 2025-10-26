"""
Blueprint: Recrutamento e Seleção
Rotas para gestão de vagas e candidatos
"""
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from extensions import supabase_admin
from modules.auth.routes import login_required
from decorators.perfil_decorators import perfil_required
from functools import wraps
import json
import os

# Criar Blueprint
recrutamento_bp = Blueprint(
    'recrutamento',
    __name__,
    url_prefix='/rh/recrutamento',
    template_folder='templates',
    static_folder='static'
)

TIPOS_CONTRATACAO_VALIDOS = {'CLT', 'PJ', 'Estágio'}
REGIMES_TRABALHO_VALIDOS = {'Presencial', 'Híbrido', 'Remoto'}
UNIQUE_EMPRESA_ID = 'dc984b7c-3156-43f7-a1bf-f7a0b77db535'


def _texto_obrigatorio(valor):
    return (valor or '').strip()


def _texto_opcional(valor):
    texto = (valor or '').strip()
    return texto or None


def _numero_float(valor):
    try:
        if valor in (None, ''):
            return None
        return float(valor)
    except (TypeError, ValueError):
        return None


def _numero_int(valor, default=None):
    try:
        if valor in (None, ''):
            return default
        return int(valor)
    except (TypeError, ValueError):
        return default


def _serializar_beneficios(valor):
    if not valor:
        return None
    if isinstance(valor, list):
        return json.dumps(valor, ensure_ascii=False)
    if isinstance(valor, str):
        texto = valor.strip()
        return texto or None
    return None

def check_api_bypass():
    """Verifica se a requisição tem a chave de bypass de API"""
    api_bypass_key = os.getenv('API_BYPASS_KEY')
    request_key = request.headers.get('X-API-Key')
    return api_bypass_key and request_key == api_bypass_key

def perfil_or_bypass_required(modulo, pagina=None):
    """Decorator que permite acesso por perfil OU bypass key"""
    def decorator(f):
        decorated = perfil_required(modulo, pagina)(f)
        @wraps(f)
        def wrapper(*args, **kwargs):
            if check_api_bypass():
                return f(*args, **kwargs)
            return decorated(*args, **kwargs)
        wrapper.__name__ = f.__name__
        return wrapper
    return decorator

# ========================================
# ROTAS HTML - GESTÃO DE VAGAS
# ========================================

@recrutamento_bp.route('/vagas')
@login_required
@perfil_required('rh', 'recrutamento')
def gestao_vagas():
    """Página de gerenciamento de vagas"""
    print("\n" + "="*70)
    print("🔍 DEBUG: Acessando rota /rh/recrutamento/vagas")
    print("="*70)
    
    print("✅ DEBUG: Usuário autenticado")
    
    try:
        print("\n1️⃣ Buscando vagas...")
        # Buscar todas as vagas
        vagas_response = (
            supabase_admin
            .table('rh_vagas')
            .select('*')
            .order('data_abertura', desc=True)
            .execute()
        )
        
        vagas = vagas_response.data if vagas_response.data else []
        print(f"   ✅ {len(vagas)} vaga(s) encontrada(s)")
        
        # Calcular KPIs
        total_vagas = len(vagas)
        vagas_abertas = len([v for v in vagas if v.get('status') == 'Aberta'])
        vagas_fechadas = len([v for v in vagas if v.get('status') == 'Fechada'])
        
        # 🚀 OTIMIZAÇÃO: Buscar TODOS os candidatos de uma vez (1 requisição ao invés de N)
        print("\n   🚀 Buscando candidatos (requisição única otimizada)...")
        try:
            todos_candidatos_response = (
                supabase_admin
                .table('rh_candidatos')
                .select('vaga_id')
                .execute()
            )
            
            # Agrupar candidatos por vaga_id em memória (processamento local = rápido)
            candidatos_por_vaga = {}
            for candidato in (todos_candidatos_response.data or []):
                vaga_id = candidato.get('vaga_id')
                if vaga_id:
                    candidatos_por_vaga[vaga_id] = candidatos_por_vaga.get(vaga_id, 0) + 1
            
            print(f"   ✅ Total de candidatos encontrados: {len(todos_candidatos_response.data or [])}")
            print(f"   ✅ Distribuídos em {len(candidatos_por_vaga)} vagas")
            
            # Associar contagens às vagas
            total_candidatos_geral = 0
            for vaga in vagas:
                vaga['total_candidatos'] = candidatos_por_vaga.get(vaga['id'], 0)
                total_candidatos_geral += vaga['total_candidatos']
            
        except Exception as e:
            print(f"   ⚠️ Erro ao buscar candidatos: {str(e)}")
            # Fallback: zerar contagens
            total_candidatos_geral = 0
            for vaga in vagas:
                vaga['total_candidatos'] = 0
        
        # Calcular média de candidatos por vaga
        candidatos_media = round(total_candidatos_geral / total_vagas, 1) if total_vagas > 0 else 0
        
        print(f"\n📊 KPIs Calculados:")
        print(f"   Total de Vagas: {total_vagas}")
        print(f"   Vagas Abertas: {vagas_abertas}")
        print(f"   Vagas Fechadas: {vagas_fechadas}")
        print(f"   Média Candidatos/Vaga: {candidatos_media}")
        
        print("\n2️⃣ Buscando cargos para dropdown...")
        # Buscar cargos para o dropdown
        cargos_response = supabase_admin.table('rh_cargos')\
            .select('*')\
            .order('nome_cargo')\
            .execute()
        
        cargos = cargos_response.data if cargos_response.data else []
        
        print(f"\n3️⃣ Total de cargos carregados: {len(cargos)}")
        
        print(f"\n4️⃣ Renderizando template...")
        print(f"   vagas = {len(vagas)} itens")
        print(f"   cargos = {len(cargos)} itens")
        print("="*70 + "\n")
        
        return render_template(
            'recrutamento/gestao_vagas.html', 
            vagas=vagas, 
            cargos=cargos,
            total_vagas=total_vagas,
            vagas_abertas=vagas_abertas,
            vagas_fechadas=vagas_fechadas,
            candidatos_media=candidatos_media
        )
    
    except Exception as e:
        print(f"\n❌ ERRO ao carregar vagas: {str(e)}")
        import traceback
        traceback.print_exc()
        print("="*70 + "\n")
        return render_template(
            'recrutamento/gestao_vagas.html', 
            vagas=[], 
            cargos=[],
            total_vagas=0,
            vagas_abertas=0,
            vagas_fechadas=0,
            candidatos_media=0
        )


@recrutamento_bp.route('/vagas/<vaga_id>/candidatos')
@login_required
@perfil_required('rh', 'recrutamento')
def gestao_candidatos(vaga_id):
    """Página Kanban de gestão de candidatos de uma vaga"""
    try:
        # Buscar detalhes da vaga
        vaga_response = supabase_admin.table('rh_vagas')\
            .select('*')\
            .eq('id', vaga_id)\
            .execute()
        
        if not vaga_response.data or len(vaga_response.data) == 0:
            return "Vaga não encontrada", 404
        
        vaga = vaga_response.data[0]
        
        # Buscar candidatos da vaga (ordenar por score de IA primeiro, depois data)
        candidatos_response = supabase_admin.table('rh_candidatos')\
            .select('*')\
            .eq('vaga_id', vaga_id)\
            .order('ai_match_score', desc=True)\
            .order('data_candidatura', desc=True)\
            .execute()
        
        candidatos = candidatos_response.data if candidatos_response.data else []
        
        # Calcular KPIs
        total_candidatos = len(candidatos)
        
        # Candidatos em processo (não são Aprovado, Reprovado, Contratado, Refutado)
        em_processo = len([c for c in candidatos if c.get('status_processo') not in ['Aprovado', 'Reprovado', 'Contratado', 'Refutado']])
        
        # Candidatos aprovados (Aprovado + Contratado)
        aprovados = len([c for c in candidatos if c.get('status_processo') in ['Aprovado', 'Contratado']])
        
        # Taxa de conversão (aprovados / total * 100)
        taxa_conversao = round((aprovados / total_candidatos * 100), 1) if total_candidatos > 0 else 0
        
        # Agrupar candidatos por status
        candidatos_por_status = {
            'Triagem': [],
            'Contato/Agendamento': [],
            'Entrevista RH': [],
            'Entrevista Técnica': [],
            'Aprovado': [],
            'Reprovado': [],
            'Contratado': [],
            'Refutado': []
        }
        
        for candidato in candidatos:
            status = candidato.get('status_processo', 'Triagem')
            if status in candidatos_por_status:
                candidatos_por_status[status].append(candidato)
            else:
                candidatos_por_status['Triagem'].append(candidato)
        
        return render_template(
            'recrutamento/gestao_candidatos.html',
            vaga=vaga,
            candidatos_por_status=candidatos_por_status,
            total_candidatos=total_candidatos,
            em_processo=em_processo,
            aprovados=aprovados,
            taxa_conversao=taxa_conversao
        )
    
    except Exception as e:
        print(f"❌ Erro ao carregar candidatos: {str(e)}")
        return f"Erro ao carregar candidatos: {str(e)}", 500


# ========================================
# API REST - VAGAS
# ========================================

@recrutamento_bp.route('/api/vagas', methods=['GET'])
@perfil_or_bypass_required('rh', 'recrutamento')
def api_list_vagas():
    """API: Listar todas as vagas"""
    try:
        empresa_id = request.args.get('empresa_id')  # NOVO: Filtro por empresa
        
        query = supabase_admin.table('rh_vagas').select('*')
        
        # NOVO: Filtrar por empresa se fornecido
        if empresa_id:
            query = query.eq('empresa_controladora_id', empresa_id)
        
        response = query.order('data_abertura', desc=True).execute()
        
        vagas = response.data if response.data else []
        
        # Contar candidatos para cada vaga
        for vaga in vagas:
            candidatos_response = supabase_admin.table('rh_candidatos')\
                .select('id', count='exact')\
                .eq('vaga_id', vaga['id'])\
                .execute()
            
            vaga['total_candidatos'] = candidatos_response.count if candidatos_response.count else 0
        
        return jsonify({
            'success': True,
            'data': vagas,
            'count': len(vagas)
        })
    
    except Exception as e:
        print(f"❌ Erro ao listar vagas: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@recrutamento_bp.route('/api/vagas/<vaga_id>', methods=['GET'])
@perfil_or_bypass_required('rh', 'recrutamento')
def api_get_vaga(vaga_id):
    """API: Buscar vaga por ID"""
    try:
        response = supabase_admin.table('rh_vagas')\
            .select('*')\
            .eq('id', vaga_id)\
            .execute()
        
        if response.data and len(response.data) > 0:
            return jsonify({'success': True, 'vaga': response.data[0]})
        else:
            return jsonify({'success': False, 'message': 'Vaga não encontrada'}), 404
    
    except Exception as e:
        print(f"❌ Erro ao buscar vaga: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@recrutamento_bp.route('/api/vagas', methods=['POST'])
@perfil_or_bypass_required('rh', 'recrutamento')
def api_create_vaga():
    """API: Criar nova vaga"""
    try:
        data = request.get_json(silent=True) or {}

        titulo = _texto_obrigatorio(data.get('titulo'))
        if not titulo:
            return jsonify({'success': False, 'message': 'Título da vaga é obrigatório'}), 400

        cargo_id = _texto_obrigatorio(data.get('cargo_id'))
        if not cargo_id:
            return jsonify({'success': False, 'message': 'Cargo é obrigatório'}), 400

        descricao = _texto_obrigatorio(data.get('descricao'))
        if not descricao:
            return jsonify({'success': False, 'message': 'Descrição é obrigatória'}), 400

        requisitos_obrigatorios = _texto_obrigatorio(
            data.get('requisitos_obrigatorios') or data.get('requisitos')
        )
        if not requisitos_obrigatorios:
            return jsonify({'success': False, 'message': 'Requisitos obrigatórios são necessários'}), 400

        requisitos_desejaveis = _texto_opcional(data.get('requisitos_desejaveis'))
        diferenciais = _texto_opcional(data.get('diferenciais'))
        localizacao = _texto_opcional(data.get('localizacao'))

        tipo_contratacao = _texto_obrigatorio(data.get('tipo_contratacao') or 'CLT')
        if tipo_contratacao not in TIPOS_CONTRATACAO_VALIDOS:
            tipo_contratacao = 'CLT'

        faixa_salarial_min = _numero_float(data.get('faixa_salarial_min'))
        faixa_salarial_max = _numero_float(data.get('faixa_salarial_max'))
        beneficios = _serializar_beneficios(data.get('beneficios'))
        nivel_senioridade = _texto_opcional(data.get('nivel_senioridade'))
        quantidade_vagas = _numero_int(data.get('quantidade_vagas'), default=1)
        if quantidade_vagas is None or quantidade_vagas <= 0:
            quantidade_vagas = 1
        regime_trabalho = _texto_opcional(data.get('regime_trabalho'))
        if regime_trabalho and regime_trabalho not in REGIMES_TRABALHO_VALIDOS:
            regime_trabalho = None
        carga_horaria = _texto_opcional(data.get('carga_horaria'))

        vaga_data = {
            'titulo': titulo,
            'cargo_id': cargo_id,
            'descricao': descricao,
            'requisitos_obrigatorios': requisitos_obrigatorios,
            'requisitos_desejaveis': requisitos_desejaveis,
            'diferenciais': diferenciais,
            'localizacao': localizacao,
            'tipo_contratacao': tipo_contratacao,
            'status': 'Aberta',
            'beneficios': beneficios,
            'nivel_senioridade': nivel_senioridade,
            'quantidade_vagas': quantidade_vagas,
            'regime_trabalho': regime_trabalho,
            'carga_horaria': carga_horaria,
            'empresa_controladora_id': UNIQUE_EMPRESA_ID
        }

        if faixa_salarial_min is not None:
            vaga_data['faixa_salarial_min'] = faixa_salarial_min
        if faixa_salarial_max is not None:
            vaga_data['faixa_salarial_max'] = faixa_salarial_max

        response = supabase_admin.table('rh_vagas').insert(vaga_data).execute()
        
        if response.data:
            return jsonify({
                'success': True,
                'message': 'Vaga criada com sucesso',
                'vaga_id': response.data[0]['id'],
                'data': response.data[0]
            }), 201
        else:
            return jsonify({'success': False, 'message': 'Erro ao criar vaga'}), 500
    
    except Exception as e:
        print(f"❌ Erro ao criar vaga: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@recrutamento_bp.route('/api/vagas/<vaga_id>', methods=['PUT'])
@perfil_or_bypass_required('rh', 'recrutamento')
def api_update_vaga(vaga_id):
    """API: Atualizar vaga"""
    try:
        data = request.get_json(silent=True) or {}
        
        # Verificar se vaga existe
        check_response = supabase_admin.table('rh_vagas')\
            .select('*')\
            .eq('id', vaga_id)\
            .execute()
        
        if not check_response.data or len(check_response.data) == 0:
            return jsonify({'success': False, 'message': 'Vaga não encontrada'}), 404
        
        vaga_existente = check_response.data[0]
        
        # Atualizar vaga
        update_data = {}
        if 'titulo' in data:
            titulo = _texto_obrigatorio(data.get('titulo'))
            if titulo:
                update_data['titulo'] = titulo

        if 'cargo_id' in data:
            cargo_id = _texto_obrigatorio(data.get('cargo_id'))
            if cargo_id:
                update_data['cargo_id'] = cargo_id

        if 'descricao' in data:
            descricao = _texto_obrigatorio(data.get('descricao'))
            if descricao:
                update_data['descricao'] = descricao

        if 'requisitos_obrigatorios' in data or 'requisitos' in data:
            novos_requisitos = data.get('requisitos_obrigatorios')
            if novos_requisitos is None:
                novos_requisitos = data.get('requisitos')
            novos_requisitos = _texto_obrigatorio(novos_requisitos)
            if not novos_requisitos:
                return jsonify({'success': False, 'message': 'Requisitos obrigatórios não podem ficar em branco'}), 400
            update_data['requisitos_obrigatorios'] = novos_requisitos

        if 'requisitos_desejaveis' in data and 'requisitos_desejaveis' in vaga_existente:
            update_data['requisitos_desejaveis'] = _texto_opcional(data.get('requisitos_desejaveis'))

        if 'diferenciais' in data and 'diferenciais' in vaga_existente:
            update_data['diferenciais'] = _texto_opcional(data.get('diferenciais'))

        if 'localizacao' in data:
            update_data['localizacao'] = _texto_opcional(data.get('localizacao'))

        if 'tipo_contratacao' in data:
            tipo_contratacao = _texto_obrigatorio(data.get('tipo_contratacao'))
            if tipo_contratacao not in TIPOS_CONTRATACAO_VALIDOS:
                tipo_contratacao = 'CLT'
            update_data['tipo_contratacao'] = tipo_contratacao

        if 'faixa_salarial_min' in data and 'faixa_salarial_min' in vaga_existente:
            faixa_min = _numero_float(data.get('faixa_salarial_min'))
            update_data['faixa_salarial_min'] = faixa_min

        if 'faixa_salarial_max' in data and 'faixa_salarial_max' in vaga_existente:
            faixa_max = _numero_float(data.get('faixa_salarial_max'))
            update_data['faixa_salarial_max'] = faixa_max

        if 'beneficios' in data and 'beneficios' in vaga_existente:
            update_data['beneficios'] = _serializar_beneficios(data.get('beneficios'))

        if 'nivel_senioridade' in data and 'nivel_senioridade' in vaga_existente:
            update_data['nivel_senioridade'] = _texto_opcional(data.get('nivel_senioridade'))

        if 'quantidade_vagas' in data and 'quantidade_vagas' in vaga_existente:
            quantidade_vagas = _numero_int(data.get('quantidade_vagas'))
            if quantidade_vagas is None or quantidade_vagas <= 0:
                quantidade_vagas = 1
            update_data['quantidade_vagas'] = quantidade_vagas

        if 'regime_trabalho' in data and 'regime_trabalho' in vaga_existente:
            regime_trabalho = _texto_opcional(data.get('regime_trabalho'))
            if regime_trabalho and regime_trabalho not in REGIMES_TRABALHO_VALIDOS:
                regime_trabalho = None
            update_data['regime_trabalho'] = regime_trabalho

        if 'carga_horaria' in data and 'carga_horaria' in vaga_existente:
            update_data['carga_horaria'] = _texto_opcional(data.get('carga_horaria'))

        response = supabase_admin.table('rh_vagas')\
            .update(update_data)\
            .eq('id', vaga_id)\
            .execute()
        
        if response.data:
            return jsonify({
                'success': True,
                'message': 'Vaga atualizada com sucesso',
                'data': response.data[0]
            })
        else:
            return jsonify({'success': False, 'message': 'Erro ao atualizar vaga'}), 500
    
    except Exception as e:
        print(f"❌ Erro ao atualizar vaga: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@recrutamento_bp.route('/api/vagas/<vaga_id>/status', methods=['PUT'])
@perfil_or_bypass_required('rh', 'recrutamento')
def api_update_vaga_status(vaga_id):
    """API: Alterar status da vaga (Aberta/Pausada/Fechada)"""
    try:
        data = request.get_json()
        novo_status = data.get('status', '').strip()
        
        if novo_status not in ['Aberta', 'Pausada', 'Fechada']:
            return jsonify({'success': False, 'message': 'Status inválido'}), 400
        
        response = supabase_admin.table('rh_vagas')\
            .update({'status': novo_status})\
            .eq('id', vaga_id)\
            .execute()
        
        if response.data:
            return jsonify({
                'success': True,
                'message': f'Vaga {novo_status.lower()} com sucesso',
                'data': response.data[0]
            })
        else:
            return jsonify({'success': False, 'message': 'Erro ao alterar status'}), 500
    
    except Exception as e:
        print(f"❌ Erro ao alterar status: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@recrutamento_bp.route('/api/vagas/<vaga_id>', methods=['DELETE'])
@perfil_or_bypass_required('rh', 'recrutamento')
def api_delete_vaga(vaga_id):
    """API: Deletar vaga (com verificação de candidatos)"""
    try:
        # Verificar se vaga existe
        check_response = supabase_admin.table('rh_vagas')\
            .select('*')\
            .eq('id', vaga_id)\
            .execute()
        
        if not check_response.data or len(check_response.data) == 0:
            return jsonify({'success': False, 'message': 'Vaga não encontrada'}), 404

        vaga = check_response.data[0]

        # Se existirem candidatos vinculados, aplica soft delete (status Cancelada)
        candidatos_response = supabase_admin.table('rh_candidatos')\
            .select('id', count='exact')\
            .eq('vaga_id', vaga_id)\
            .execute()

        candidatos_vinculados = candidatos_response.count or 0

        if candidatos_vinculados > 0:
            print(f"[WARN] Vaga {vaga_id} possui {candidatos_vinculados} candidato(s); aplicando soft delete.")

            # Atualiza status somente se já não estiver marcado como Cancelada
            if vaga.get('status') != 'Cancelada':
                update_response = supabase_admin.table('rh_vagas')\
                    .update({'status': 'Cancelada'})\
                    .eq('id', vaga_id)\
                    .execute()
                vaga_atualizada = update_response.data[0] if update_response.data else None
            else:
                vaga_atualizada = vaga

            return jsonify({
                'success': True,
                'soft_delete': True,
                'message': 'Vaga possui candidatos vinculados e foi marcada como Cancelada.',
                'candidatos_vinculados': candidatos_vinculados,
                'data': vaga_atualizada
            }), 200

        response = supabase_admin.table('rh_vagas')\
            .delete()\
            .eq('id', vaga_id)\
            .execute()
        
        return jsonify({
            'success': True,
            'message': 'Vaga excluída com sucesso'
        })
    
    except Exception as e:
        print(f"❌ Erro ao excluir vaga: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ========================================
# API REST - CANDIDATOS
# ========================================

@recrutamento_bp.route('/api/candidatos', methods=['GET'])
@perfil_or_bypass_required('rh', 'recrutamento')
def api_list_candidatos():
    """API: Listar candidatos de uma vaga"""
    try:
        vaga_id = request.args.get('vaga_id')
        
        if not vaga_id:
            return jsonify({'success': False, 'message': 'vaga_id é obrigatório'}), 400
        
        response = supabase_admin.table('rh_candidatos')\
            .select('*')\
            .eq('vaga_id', vaga_id)\
            .order('data_candidatura', desc=True)\
            .execute()
        
        candidatos = response.data if response.data else []
        
        return jsonify({
            'success': True,
            'data': candidatos,
            'count': len(candidatos)
        })
    
    except Exception as e:
        print(f"❌ Erro ao listar candidatos: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@recrutamento_bp.route('/api/candidatos/<candidato_id>/mover', methods=['PUT'])
@perfil_or_bypass_required('rh', 'recrutamento')
def api_mover_candidato(candidato_id):
    """API: Mover candidato para outro status (drag-and-drop no Kanban)"""
    try:
        data = request.get_json()
        novo_status = data.get('novo_status', '').strip()
        
        # 🔍 DEBUG: Log detalhado
        print("\n" + "="*70)
        print("🔍 DEBUG - API MOVER CANDIDATO")
        print("="*70)
        print(f"📥 Request recebido:")
        print(f"   Candidato ID: {candidato_id}")
        print(f"   Payload completo: {data}")
        print(f"   novo_status (raw): '{data.get('novo_status')}'")
        print(f"   novo_status (stripped): '{novo_status}'")
        print(f"   Tipo: {type(novo_status)}")
        print(f"   Comprimento: {len(novo_status)}")
        print(f"   Bytes: {novo_status.encode('utf-8')}")
        
        status_validos = [
            'Triagem', 'Contato/Agendamento', 'Entrevista RH', 
            'Entrevista Técnica', 'Aprovado', 'Reprovado', 
            'Contratado', 'Refutado'
        ]
        
        print(f"\n✅ Status válidos:")
        for s in status_validos:
            match = '✅ MATCH' if s == novo_status else '❌'
            print(f"   {match} '{s}'")
        
        if novo_status not in status_validos:
            print(f"\n❌ ERRO: Status '{novo_status}' não está na lista de válidos!")
            print("="*70 + "\n")
            return jsonify({'success': False, 'message': f'Status inválido: "{novo_status}"'}), 400
        
        print(f"\n✅ Status válido! Atualizando no banco de dados...")
        
        response = supabase_admin.table('rh_candidatos')\
            .update({'status_processo': novo_status})\
            .eq('id', candidato_id)\
            .execute()
        
        if response.data:
            print(f"✅ Candidato atualizado com sucesso!")
            print(f"   Novo status: {novo_status}")
            print("="*70 + "\n")
            return jsonify({
                'success': True,
                'message': f'Candidato movido para {novo_status}',
                'data': response.data[0]
            })
        else:
            print(f"❌ Erro: response.data vazio")
            print("="*70 + "\n")
            return jsonify({'success': False, 'message': 'Erro ao mover candidato'}), 500
    
    except Exception as e:
        print(f"❌ EXCEPTION ao mover candidato: {str(e)}")
        import traceback
        traceback.print_exc()
        print("="*70 + "\n")
        return jsonify({'success': False, 'message': str(e)}), 500


@recrutamento_bp.route('/api/candidatos/<candidato_id>', methods=['GET'])
@perfil_or_bypass_required('rh', 'recrutamento')
def api_get_candidato(candidato_id):
    """API: Buscar detalhes de um candidato"""
    try:
        response = supabase_admin.table('rh_candidatos')\
            .select('*')\
            .eq('id', candidato_id)\
            .execute()
        
        if response.data and len(response.data) > 0:
            return jsonify({'data': response.data[0]})
        else:
            return jsonify({'success': False, 'message': 'Candidato não encontrado'}), 404
    
    except Exception as e:
        print(f"❌ Erro ao buscar candidato: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@recrutamento_bp.route('/api/candidatos/<candidato_id>/observacoes', methods=['GET'])
def api_get_observacoes(candidato_id):
    """API: Buscar histórico de observações do candidato"""
    if not check_api_bypass() and 'user' not in session:
        return jsonify({'success': False, 'message': 'Não autenticado'}), 401
    
    try:
        response = supabase_admin.table('rh_candidatos')\
            .select('historico_observacoes, nome_completo')\
            .eq('id', candidato_id)\
            .execute()
        
        if response.data and len(response.data) > 0:
            candidato = response.data[0]
            historico = candidato.get('historico_observacoes', [])
            
            # Garantir que seja uma lista
            if not isinstance(historico, list):
                historico = []
            
            return jsonify({
                'success': True,
                'data': {
                    'nome_completo': candidato.get('nome_completo'),
                    'historico': historico,
                    'total': len(historico)
                }
            })
        else:
            return jsonify({'success': False, 'message': 'Candidato não encontrado'}), 404
    
    except Exception as e:
        print(f"❌ Erro ao buscar observações: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@recrutamento_bp.route('/api/candidatos/<candidato_id>/observacoes', methods=['POST'])
@perfil_or_bypass_required('rh', 'recrutamento')
def api_add_observacao(candidato_id):
    """API: Adicionar nova observação ao histórico do candidato"""
    try:
        data = request.get_json()
        nova_observacao = data.get('observacao', '').strip()
        
        if not nova_observacao:
            return jsonify({'success': False, 'message': 'Observação não pode estar vazia'}), 400
        
        # Buscar histórico atual
        response = supabase_admin.table('rh_candidatos')\
            .select('historico_observacoes, nome_completo')\
            .eq('id', candidato_id)\
            .execute()
        
        if not response.data or len(response.data) == 0:
            return jsonify({'success': False, 'message': 'Candidato não encontrado'}), 404
        
        candidato = response.data[0]
        historico_atual = candidato.get('historico_observacoes', [])
        
        # Garantir que seja uma lista
        if not isinstance(historico_atual, list):
            historico_atual = []
        
        # Pegar nome do usuário da sessão
        usuario_nome = session.get('user', {}).get('name', 'Sistema')
        
        # Criar nova entrada
        from datetime import datetime
        nova_entrada = {
            'data': datetime.now().isoformat(),
            'usuario': usuario_nome,
            'observacao': nova_observacao
        }
        
        # Adicionar ao início da lista (mais recente primeiro)
        historico_atualizado = [nova_entrada] + historico_atual
        
        # Atualizar no banco
        update_response = supabase_admin.table('rh_candidatos')\
            .update({'historico_observacoes': historico_atualizado})\
            .eq('id', candidato_id)\
            .execute()
        
        if update_response.data:
            return jsonify({
                'success': True,
                'message': 'Observação adicionada com sucesso',
                'data': {
                    'historico': historico_atualizado,
                    'total': len(historico_atualizado)
                }
            })
        else:
            return jsonify({'success': False, 'message': 'Erro ao salvar observação'}), 500
    
    except Exception as e:
        print(f"❌ Erro ao adicionar observação: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


@recrutamento_bp.route('/api/candidatos/<candidato_id>', methods=['PUT'])
@perfil_or_bypass_required('rh', 'recrutamento')
def api_update_candidato(candidato_id):
    """API: Atualizar informações do candidato (modo edição)"""
    try:
        data = request.get_json()
        
        # Campos editáveis permitidos (exclui campos de IA e ID)
        campos_permitidos = {
            # Informações Pessoais
            'nome_completo',
            'data_nascimento',
            'email',
            'telefone',
            'sexo',
            'estado_civil',
            'cidade_estado',
            # Formação e Experiência
            'formacao_academica',
            'curso_especifico',
            'area_objetivo',
            'experiencia_na_area',
            'trabalha_atualmente',
            # Candidatura
            'fonte_candidatura',
            'data_candidatura',
            'foi_indicacao',
            'indicado_por',
            'linkedin_url',
            'portfolio_url',
            # Processo Seletivo
            'status_processo',
            'realizou_entrevista',
            'data_entrevista',
            # Contratação
            'foi_contratado',
            'data_contratacao'
        }
        
        # Filtrar apenas campos permitidos e que foram enviados
        campos_atualizar = {k: v for k, v in data.items() if k in campos_permitidos and k in data}
        
        if not campos_atualizar:
            return jsonify({
                'success': False,
                'message': 'Nenhum campo válido para atualizar'
            }), 400
        
        # Atualizar no banco
        response = supabase_admin.table('rh_candidatos')\
            .update(campos_atualizar)\
            .eq('id', candidato_id)\
            .execute()
        
        if response.data and len(response.data) > 0:
            candidato_atualizado = response.data[0]
            return jsonify({
                'success': True,
                'message': 'Candidato atualizado com sucesso',
                'data': candidato_atualizado
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Erro ao atualizar candidato'
            }), 500
    
    except Exception as e:
        print(f"❌ Erro ao atualizar candidato: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500
