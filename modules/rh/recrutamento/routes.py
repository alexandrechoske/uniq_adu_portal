"""
Blueprint: Recrutamento e Seleção
Rotas para gestão de vagas e candidatos
"""
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from extensions import supabase_admin
from modules.auth.routes import login_required
from decorators.perfil_decorators import perfil_required
from functools import wraps
import os

# Criar Blueprint
recrutamento_bp = Blueprint(
    'recrutamento',
    __name__,
    url_prefix='/rh/recrutamento',
    template_folder='templates',
    static_folder='static'
)

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
        vagas_response = supabase_admin.table('rh_vagas')\
            .select('*')\
            .order('data_abertura', desc=True)\
            .execute()
        
        vagas = vagas_response.data if vagas_response.data else []
        print(f"   ✅ {len(vagas)} vaga(s) encontrada(s)")
        
        # Calcular KPIs
        total_vagas = len(vagas)
        vagas_abertas = len([v for v in vagas if v.get('status') == 'Aberta'])
        vagas_fechadas = len([v for v in vagas if v.get('status') == 'Fechada'])
        
        # 🚀 OTIMIZAÇÃO: Buscar TODOS os candidatos de uma vez (1 requisição ao invés de N)
        print("\n   🚀 Buscando candidatos (requisição única otimizada)...")
        try:
            todos_candidatos_response = supabase_admin.table('rh_candidatos')\
                .select('vaga_id')\
                .execute()
            
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
        response = supabase_admin.table('rh_vagas')\
            .select('*')\
            .order('data_abertura', desc=True)\
            .execute()
        
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
        data = request.get_json()
        
        # Validações
        titulo = data.get('titulo', '').strip()
        if not titulo:
            return jsonify({'success': False, 'message': 'Título da vaga é obrigatório'}), 400
        
        cargo_id = data.get('cargo_id', '').strip()
        if not cargo_id:
            return jsonify({'success': False, 'message': 'Cargo é obrigatório'}), 400
        
        descricao = data.get('descricao', '').strip()
        if not descricao:
            return jsonify({'success': False, 'message': 'Descrição é obrigatória'}), 400
        
        requisitos = data.get('requisitos', '').strip()
        if not requisitos:
            return jsonify({'success': False, 'message': 'Requisitos são obrigatórios'}), 400
        
        # Criar vaga
        vaga_data = {
            'titulo': titulo,
            'cargo_id': cargo_id,
            'descricao': descricao,
            'requisitos': requisitos,
            'localizacao': data.get('localizacao', '').strip() or None,
            'tipo_contratacao': data.get('tipo_contratacao', '').strip() or 'CLT',
            'status': 'Aberta'
        }
        
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
        
        # Atualizar vaga
        update_data = {}
        if 'titulo' in data:
            titulo = data['titulo'].strip()
            if titulo:
                update_data['titulo'] = titulo
        
        if 'cargo_id' in data:
            update_data['cargo_id'] = data['cargo_id']
        
        if 'descricao' in data:
            update_data['descricao'] = data['descricao'].strip()
        
        if 'requisitos' in data:
            update_data['requisitos'] = data['requisitos'].strip()
        
        if 'localizacao' in data:
            update_data['localizacao'] = data['localizacao'].strip() or None
        
        if 'tipo_contratacao' in data:
            update_data['tipo_contratacao'] = data['tipo_contratacao'].strip()
        
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
        # Verificar se vaga tem candidatos
        candidatos_response = supabase_admin.table('rh_candidatos')\
            .select('id', count='exact')\
            .eq('vaga_id', vaga_id)\
            .execute()
        
        if candidatos_response.count and candidatos_response.count > 0:
            return jsonify({
                'success': False,
                'message': f'Não é possível excluir. Esta vaga possui {candidatos_response.count} candidato(s) associado(s).'
            }), 409
        
        # Deletar vaga
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
