"""
Rotas do módulo de Estrutura Organizacional (Dados Mestres)
CRUD completo para Cargos e Departamentos

IMPORTANTE: Mapeamento de colunas do banco:
- nome_cargo (não 'nome')
- grupo_cargo (não 'grupo')
- nome_departamento (não 'nome')
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, session
from extensions import supabase_admin
from modules.auth.routes import login_required
from decorators.perfil_decorators import perfil_required
from werkzeug.security import generate_password_hash
import os
from datetime import datetime, timezone

# Criar blueprint
estrutura_org_bp = Blueprint(
    'estrutura_org',
    __name__,
    template_folder='templates',
    static_folder='static',
    url_prefix='/rh/estrutura'
)

# Configuração
API_BYPASS_KEY = os.getenv('API_BYPASS_KEY')
UNIQUE_EMPRESA_ID = 'dc984b7c-3156-43f7-a1bf-f7a0b77db535'

def check_api_bypass():
    """Verifica se a requisição tem a chave de bypass da API"""
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


def _sanitize_acesso_contabilidade(registro):
    """Remove campos sensíveis e normaliza dados de acesso da contabilidade."""
    if not registro:
        return {}

    sanitized = {chave: valor for chave, valor in registro.items() if chave != 'senha_hash'}
    return sanitized


def _parse_bool(value, default=False):
    """Helper para interpretar valores booleanos enviados pelo frontend."""
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {'true', '1', 'yes', 'on', 'sim', 'ativo'}
    return default

# ========================================
# ROTA RAIZ - REDIRECT
# ========================================

@estrutura_org_bp.route('/')
@login_required
def index():
    """Rota raiz - redireciona para cargos"""
    return redirect(url_for('estrutura_org.gestao_cargos'))

# ========================================
# ROTAS WEB - CARGOS
# ========================================

@estrutura_org_bp.route('/cargos')
@login_required
@perfil_required('rh', 'estrutura_cargos')
def gestao_cargos():
    """Página de gestão de cargos"""
    try:
        response = supabase_admin.table('rh_cargos')\
            .select('*')\
            .order('nome_cargo')\
            .execute()
        
        cargos = response.data if response.data else []
        total_cargos = len(cargos)
        grupos = list(set([c.get('grupo_cargo', 'Sem Grupo') for c in cargos if c.get('grupo_cargo')]))
        total_grupos = len(grupos)
        
        return render_template(
            'estrutura_org/gestao_cargos.html',
            cargos=cargos,
            total_cargos=total_cargos,
            total_grupos=total_grupos,
            grupos=grupos
        )
    
    except Exception as e:
        print(f"❌ Erro ao carregar cargos: {str(e)}")
        flash('Erro ao carregar cargos', 'error')
        return render_template('estrutura_org/gestao_cargos.html', cargos=[], total_cargos=0, total_grupos=0, grupos=[])

# ========================================
# ROTAS WEB - DEPARTAMENTOS
# ========================================

@estrutura_org_bp.route('/departamentos')
@login_required
@perfil_required('rh', 'estrutura_departamentos')
def gestao_departamentos():
    """Página de gestão de departamentos"""
    try:
        response = supabase_admin.table('rh_departamentos')\
            .select('*')\
            .order('nome_departamento')\
            .execute()
        
        departamentos = response.data if response.data else []
        total_departamentos = len(departamentos)
        com_centro_custo = len([d for d in departamentos if d.get('codigo_centro_custo')])
        
        return render_template(
            'estrutura_org/gestao_departamentos.html',
            departamentos=departamentos,
            total_departamentos=total_departamentos,
            com_centro_custo=com_centro_custo
        )
    
    except Exception as e:
        print(f"❌ Erro ao carregar departamentos: {str(e)}")
        flash('Erro ao carregar departamentos', 'error')
        return render_template('estrutura_org/gestao_departamentos.html', departamentos=[], total_departamentos=0, com_centro_custo=0)

# ========================================
# API REST - CARGOS
# ========================================

@estrutura_org_bp.route('/api/cargos', methods=['GET'])
@perfil_or_bypass_required('rh', 'estrutura_cargos')
def api_list_cargos():
    """API: Listar todos os cargos"""
    try:
        empresa_id = request.args.get('empresa_id')  # NOVO: Filtro por empresa
        
        query = supabase_admin.table('rh_cargos').select('*')
        
        # NOVO: Filtrar por empresa se fornecido
        if empresa_id:
            query = query.eq('empresa_controladora_id', empresa_id)
        
        response = query.order('nome_cargo').execute()
        
        cargos = response.data if response.data else []
        
        return jsonify({
            'success': True,
            'data': cargos,
            'count': len(cargos)
        })
    
    except Exception as e:
        print(f"❌ Erro ao listar cargos: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@estrutura_org_bp.route('/api/cargos/<cargo_id>', methods=['GET'])
@perfil_or_bypass_required('rh', 'estrutura_cargos')
def api_get_cargo(cargo_id):
    """API: Buscar cargo específico por ID"""
    try:
        response = supabase_admin.table('rh_cargos')\
            .select('*')\
            .eq('id', cargo_id)\
            .execute()
        
        if response.data and len(response.data) > 0:
            return jsonify({'data': response.data[0]})
        else:
            return jsonify({'message': 'Cargo não encontrado'}), 404
    
    except Exception as e:
        print(f"❌ Erro ao buscar cargo: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@estrutura_org_bp.route('/api/cargos', methods=['POST'])
@perfil_or_bypass_required('rh', 'estrutura_cargos')
def api_create_cargo():
    """API: Criar novo cargo"""
    try:
        data = request.get_json()
        
        # Validações
        nome_cargo = data.get('nome', '').strip()
        if not nome_cargo:
            return jsonify({'success': False, 'message': 'Nome do cargo é obrigatório'}), 400
        
        # Verificar duplicidade
        check_response = supabase_admin.table('rh_cargos')\
            .select('id')\
            .eq('nome_cargo', nome_cargo)\
            .execute()
        
        if check_response.data and len(check_response.data) > 0:
            return jsonify({'success': False, 'message': 'Já existe um cargo com este nome'}), 409
        
        # Criar cargo
        cargo_data = {
            'nome_cargo': nome_cargo,
            'grupo_cargo': data.get('grupo', '').strip() or None,
            'descricao': data.get('descricao', '').strip() or None,
            'empresa_controladora_id': UNIQUE_EMPRESA_ID
        }
        
        response = supabase_admin.table('rh_cargos').insert(cargo_data).execute()
        
        if response.data:
            return jsonify({
                'success': True,
                'message': 'Cargo criado com sucesso',
                'cargo_id': response.data[0]['id'],
                'data': response.data[0]
            }), 201
        else:
            return jsonify({'success': False, 'message': 'Erro ao criar cargo'}), 500
    
    except Exception as e:
        print(f"❌ Erro ao criar cargo: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@estrutura_org_bp.route('/api/cargos/<cargo_id>', methods=['PUT'])
@perfil_or_bypass_required('rh', 'estrutura_cargos')
def api_update_cargo(cargo_id):
    """API: Atualizar cargo"""
    try:
        data = request.get_json(silent=True) or {}
        
        # Verificar se cargo existe
        check_response = supabase_admin.table('rh_cargos')\
            .select('*')\
            .eq('id', cargo_id)\
            .single()\
            .execute()
        
        if not check_response.data:
            return jsonify({'success': False, 'message': 'Cargo não encontrado'}), 404
        
        # Validações
        nome_cargo = data.get('nome', '').strip()
        if nome_cargo:
            # Verificar duplicidade (exceto o próprio registro)
            dup_check = supabase_admin.table('rh_cargos')\
                .select('id')\
                .eq('nome_cargo', nome_cargo)\
                .neq('id', cargo_id)\
                .execute()
            
            if dup_check.data and len(dup_check.data) > 0:
                return jsonify({'success': False, 'message': 'Já existe outro cargo com este nome'}), 409
        
        # Atualizar cargo
        update_data = {}
        if nome_cargo:
            update_data['nome_cargo'] = nome_cargo
        if 'grupo' in data:
            update_data['grupo_cargo'] = data['grupo'].strip() or None
        if 'descricao' in data:
            update_data['descricao'] = data['descricao'].strip() or None
        
        response = supabase_admin.table('rh_cargos')\
            .update(update_data)\
            .eq('id', cargo_id)\
            .execute()
        
        if response.data:
            return jsonify({
                'success': True,
                'message': 'Cargo atualizado com sucesso',
                'data': response.data[0]
            })
        else:
            return jsonify({'success': False, 'message': 'Erro ao atualizar cargo'}), 500
    
    except Exception as e:
        print(f"❌ Erro ao atualizar cargo: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@estrutura_org_bp.route('/api/cargos/<cargo_id>', methods=['DELETE'])
@perfil_or_bypass_required('rh', 'estrutura_cargos')
def api_delete_cargo(cargo_id):
    """API: Deletar cargo (com verificação de dependências)"""
    try:
        # Verificar se cargo existe
        check_response = supabase_admin.table('rh_cargos')\
            .select('*')\
            .eq('id', cargo_id)\
            .single()\
            .execute()
        
        if not check_response.data:
            return jsonify({'success': False, 'message': 'Cargo não encontrado'}), 404
        
        # CRÍTICO: Verificar dependências no histórico
        historico_check = supabase_admin.table('rh_historico_colaborador')\
            .select('id')\
            .eq('cargo_id', cargo_id)\
            .limit(1)\
            .execute()
        
        if historico_check.data and len(historico_check.data) > 0:
            return jsonify({
                'success': False,
                'message': 'Não é possível excluir este cargo, pois ele está associado a históricos de colaboradores'
            }), 409
        
        # Se não tem dependências, pode deletar
        response = supabase_admin.table('rh_cargos').delete().eq('id', cargo_id).execute()
        
        print(f"✓ DELETE executado para cargo {cargo_id}")
        print(f"  Response: {response}")
        
        return jsonify({
            'success': True,
            'message': 'Cargo excluído com sucesso',
            'data': response.data
        })
    
    except Exception as e:
        print(f"❌ Erro ao deletar cargo: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ========================================
# API REST - DEPARTAMENTOS
# ========================================

@estrutura_org_bp.route('/api/departamentos', methods=['GET'])
@perfil_or_bypass_required('rh', 'estrutura_departamentos')
def api_list_departamentos():
    """API: Listar todos os departamentos"""
    try:
        empresa_id = request.args.get('empresa_id')  # NOVO: Filtro por empresa
        
        query = supabase_admin.table('rh_departamentos').select('*')
        
        # NOVO: Filtrar por empresa se fornecido
        if empresa_id:
            query = query.eq('empresa_controladora_id', empresa_id)
        
        response = query.order('nome_departamento').execute()
        
        departamentos = response.data if response.data else []
        
        return jsonify({
            'success': True,
            'data': departamentos,
            'count': len(departamentos)
        })
    
    except Exception as e:
        print(f"❌ Erro ao listar departamentos: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@estrutura_org_bp.route('/api/departamentos/<departamento_id>', methods=['GET'])
@perfil_or_bypass_required('rh', 'estrutura_departamentos')
def api_get_departamento(departamento_id):
    """API: Buscar departamento específico por ID"""
    try:
        response = supabase_admin.table('rh_departamentos')\
            .select('*')\
            .eq('id', departamento_id)\
            .single()\
            .execute()
        
        if response.data:
            return jsonify({'success': True, 'departamento': response.data})
        else:
            return jsonify({'success': False, 'message': 'Departamento não encontrado'}), 404
    
    except Exception as e:
        print(f"❌ Erro ao buscar departamento: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@estrutura_org_bp.route('/api/departamentos', methods=['POST'])
@perfil_or_bypass_required('rh', 'estrutura_departamentos')
def api_create_departamento():
    """API: Criar novo departamento"""
    try:
        data = request.get_json()
        
        # Validações
        nome_departamento = data.get('nome', '').strip()
        if not nome_departamento:
            return jsonify({'success': False, 'message': 'Nome do departamento é obrigatório'}), 400
        
        # Verificar duplicidade
        check_response = supabase_admin.table('rh_departamentos')\
            .select('id')\
            .eq('nome_departamento', nome_departamento)\
            .execute()
        
        if check_response.data and len(check_response.data) > 0:
            return jsonify({'success': False, 'message': 'Já existe um departamento com este nome'}), 409
        
        # Criar departamento
        dept_data = {
            'nome_departamento': nome_departamento,
            'codigo_centro_custo': data.get('codigo_centro_custo', '').strip() or None,
            'descricao': data.get('descricao', '').strip() or None
        }
        
        response = supabase_admin.table('rh_departamentos').insert(dept_data).execute()
        
        if response.data:
            return jsonify({
                'success': True,
                'message': 'Departamento criado com sucesso',
                'departamento_id': response.data[0]['id'],
                'data': response.data[0]
            }), 201
        else:
            return jsonify({'success': False, 'message': 'Erro ao criar departamento'}), 500
    
    except Exception as e:
        print(f"❌ Erro ao criar departamento: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@estrutura_org_bp.route('/api/departamentos/<departamento_id>', methods=['PUT'])
@perfil_or_bypass_required('rh', 'estrutura_departamentos')
def api_update_departamento(departamento_id):
    """API: Atualizar departamento"""
    try:
        data = request.get_json(silent=True) or {}
        
        # Verificar se departamento existe
        check_response = supabase_admin.table('rh_departamentos')\
            .select('*')\
            .eq('id', departamento_id)\
            .single()\
            .execute()
        
        if not check_response.data:
            return jsonify({'success': False, 'message': 'Departamento não encontrado'}), 404
        
        # Validações
        nome_departamento = data.get('nome', '').strip()
        if nome_departamento:
            # Verificar duplicidade (exceto o próprio registro)
            dup_check = supabase_admin.table('rh_departamentos')\
                .select('id')\
                .eq('nome_departamento', nome_departamento)\
                .neq('id', departamento_id)\
                .execute()
            
            if dup_check.data and len(dup_check.data) > 0:
                return jsonify({'success': False, 'message': 'Já existe outro departamento com este nome'}), 409
        
        # Atualizar departamento
        update_data = {}
        if nome_departamento:
            update_data['nome_departamento'] = nome_departamento
        if 'codigo_centro_custo' in data:
            update_data['codigo_centro_custo'] = data['codigo_centro_custo'].strip() or None
        if 'descricao' in data:
            update_data['descricao'] = data['descricao'].strip() or None
        
        response = supabase_admin.table('rh_departamentos')\
            .update(update_data)\
            .eq('id', departamento_id)\
            .execute()
        
        if response.data:
            return jsonify({
                'success': True,
                'message': 'Departamento atualizado com sucesso',
                'data': response.data[0]
            })
        else:
            return jsonify({'success': False, 'message': 'Erro ao atualizar departamento'}), 500
    
    except Exception as e:
        print(f"❌ Erro ao atualizar departamento: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@estrutura_org_bp.route('/api/departamentos/<departamento_id>', methods=['DELETE'])
@perfil_or_bypass_required('rh', 'estrutura_departamentos')
def api_delete_departamento(departamento_id):
    """API: Deletar departamento (com verificação de dependências)"""
    try:
        # Verificar se departamento existe
        check_response = supabase_admin.table('rh_departamentos')\
            .select('*')\
            .eq('id', departamento_id)\
            .single()\
            .execute()
        
        if not check_response.data:
            return jsonify({'success': False, 'message': 'Departamento não encontrado'}), 404
        
        # CRÍTICO: Verificar dependências no histórico
        historico_check = supabase_admin.table('rh_historico_colaborador')\
            .select('id')\
            .eq('departamento_id', departamento_id)\
            .limit(1)\
            .execute()
        
        if historico_check.data and len(historico_check.data) > 0:
            return jsonify({
                'success': False,
                'message': 'Não é possível excluir este departamento, pois ele está associado a históricos de colaboradores'
            }), 409
        
        # Se não tem dependências, pode deletar
        response = supabase_admin.table('rh_departamentos').delete().eq('id', departamento_id).execute()
        
        return jsonify({
            'success': True,
            'message': 'Departamento excluído com sucesso'
        })
    
    except Exception as e:
        print(f"❌ Erro ao deletar departamento: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ========================================
# ROTAS - ACESSOS PORTAL CONTABILIDADE
# ========================================


@estrutura_org_bp.route('/acessos-contabilidade')
@login_required
@perfil_required('rh', 'estrutura_acessos_contabilidade')
def gestao_acessos_contabilidade():
    """Tela de gestão de acessos externos da contabilidade."""
    try:
        response = supabase_admin.table('rh_acesso_contabilidade')\
            .select('id, nome_usuario, descricao, is_active, created_at, updated_at')\
            .order('nome_usuario')\
            .execute()
        acessos = [_sanitize_acesso_contabilidade(item) for item in (response.data or [])]
    except Exception as exc:
        print(f"❌ Erro ao carregar acessos contabilidade: {exc}")
        acessos = []
        flash('Erro ao carregar acessos da contabilidade.', 'error')

    return render_template('estrutura_org/acessos_contabilidade.html', acessos=acessos)


@estrutura_org_bp.route('/api/acessos-contabilidade', methods=['GET'])
@perfil_or_bypass_required('rh', 'estrutura_acessos_contabilidade')
def api_list_acessos_contabilidade():
    """API: listar acessos cadastrados para o portal da contabilidade."""
    try:
        response = supabase_admin.table('rh_acesso_contabilidade')\
            .select('id, nome_usuario, descricao, is_active, created_at, updated_at')\
            .order('nome_usuario')\
            .execute()
        acessos = [_sanitize_acesso_contabilidade(item) for item in (response.data or [])]
        return jsonify({'success': True, 'data': acessos, 'count': len(acessos)})
    except Exception as exc:
        print(f"❌ Erro ao listar acessos contabilidade: {exc}")
        return jsonify({'success': False, 'message': 'Erro ao listar acessos.'}), 500


@estrutura_org_bp.route('/api/acessos-contabilidade', methods=['POST'])
@perfil_or_bypass_required('rh', 'estrutura_acessos_contabilidade')
def api_create_acesso_contabilidade():
    """API: criar novo usuário para o portal da contabilidade."""
    try:
        payload = request.get_json(silent=True) or {}
        nome_usuario = (payload.get('nome_usuario') or '').strip()
        senha = payload.get('senha') or ''
        descricao = (payload.get('descricao') or '').strip() or None
        is_active = _parse_bool(payload.get('is_active'), default=True)

        if not nome_usuario:
            return jsonify({'success': False, 'message': 'Nome de usuário é obrigatório.'}), 400
        if not senha or len(senha) < 8:
            return jsonify({'success': False, 'message': 'Informe uma senha com pelo menos 8 caracteres.'}), 400

        duplicado = supabase_admin.table('rh_acesso_contabilidade')\
            .select('id')\
            .eq('nome_usuario', nome_usuario)\
            .execute()
        if duplicado.data:
            return jsonify({'success': False, 'message': 'Já existe um acesso com este nome de usuário.'}), 409

        insert_payload = {
            'nome_usuario': nome_usuario,
            'senha_hash': generate_password_hash(senha),
            'descricao': descricao,
            'is_active': is_active
        }

        response = supabase_admin.table('rh_acesso_contabilidade').insert(insert_payload).execute()

        if not response.data:
            return jsonify({'success': False, 'message': 'Erro ao criar acesso.'}), 500

        novo_acesso = _sanitize_acesso_contabilidade(response.data[0])
        return jsonify({'success': True, 'message': 'Acesso criado com sucesso.', 'data': novo_acesso}), 201

    except Exception as exc:
        print(f"❌ Erro ao criar acesso contabilidade: {exc}")
        return jsonify({'success': False, 'message': 'Erro interno ao criar acesso.'}), 500


@estrutura_org_bp.route('/api/acessos-contabilidade/<acesso_id>', methods=['PUT'])
@perfil_or_bypass_required('rh', 'estrutura_acessos_contabilidade')
def api_update_acesso_contabilidade(acesso_id):
    """API: atualizar dados do acesso (inclui redefinição de senha)."""
    try:
        payload = request.get_json(silent=True) or {}

        registro_response = supabase_admin.table('rh_acesso_contabilidade')\
            .select('id, nome_usuario')\
            .eq('id', acesso_id)\
            .single()\
            .execute()

        if not registro_response.data:
            return jsonify({'success': False, 'message': 'Acesso não encontrado.'}), 404

        update_payload = {}

        if 'nome_usuario' in payload:
            novo_usuario = (payload.get('nome_usuario') or '').strip()
            if not novo_usuario:
                return jsonify({'success': False, 'message': 'Nome de usuário não pode ser vazio.'}), 400

            if novo_usuario != registro_response.data.get('nome_usuario'):
                duplicado = supabase_admin.table('rh_acesso_contabilidade')\
                    .select('id')\
                    .eq('nome_usuario', novo_usuario)\
                    .neq('id', acesso_id)\
                    .execute()
                if duplicado.data:
                    return jsonify({'success': False, 'message': 'Já existe outro acesso com este nome de usuário.'}), 409
            update_payload['nome_usuario'] = novo_usuario

        if 'descricao' in payload:
            descricao = (payload.get('descricao') or '').strip() or None
            update_payload['descricao'] = descricao

        if 'is_active' in payload:
            update_payload['is_active'] = _parse_bool(payload.get('is_active'))

        nova_senha = payload.get('senha') or ''
        if nova_senha:
            if len(nova_senha) < 8:
                return jsonify({'success': False, 'message': 'A nova senha deve ter pelo menos 8 caracteres.'}), 400
            update_payload['senha_hash'] = generate_password_hash(nova_senha)

        if not update_payload:
            return jsonify({'success': False, 'message': 'Nenhuma alteração informada.'}), 400

        update_payload['updated_at'] = datetime.now(timezone.utc).isoformat()

        supabase_admin.table('rh_acesso_contabilidade')\
            .update(update_payload)\
            .eq('id', acesso_id)\
            .execute()

        atualizado = supabase_admin.table('rh_acesso_contabilidade')\
            .select('id, nome_usuario, descricao, is_active, created_at, updated_at')\
            .eq('id', acesso_id)\
            .single()\
            .execute()

        return jsonify({
            'success': True,
            'message': 'Acesso atualizado com sucesso.',
            'data': _sanitize_acesso_contabilidade(atualizado.data)
        })

    except Exception as exc:
        print(f"❌ Erro ao atualizar acesso contabilidade: {exc}")
        return jsonify({'success': False, 'message': 'Erro ao atualizar acesso.'}), 500

