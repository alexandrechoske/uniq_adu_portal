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
import os
from datetime import datetime

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

def check_api_bypass():
    """Verifica se a requisição tem a chave de bypass da API"""
    api_key = request.headers.get('X-API-Key')
    return api_key == API_BYPASS_KEY

def check_auth():
    """Verifica autenticação (session ou bypass)"""
    if check_api_bypass():
        return True
    return 'user' in session

# ========================================
# ROTA RAIZ - REDIRECT
# ========================================

@estrutura_org_bp.route('/')
def index():
    """Rota raiz - redireciona para cargos"""
    return redirect(url_for('estrutura_org.gestao_cargos'))

# ========================================
# ROTAS WEB - CARGOS
# ========================================

@estrutura_org_bp.route('/cargos')
def gestao_cargos():
    """Página de gestão de cargos"""
    if not check_auth():
        return redirect('/login')
    
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
def gestao_departamentos():
    """Página de gestão de departamentos"""
    if not check_auth():
        return redirect('/login')
    
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
def api_list_cargos():
    """API: Listar todos os cargos"""
    if not check_api_bypass() and 'user' not in session:
        return jsonify({'success': False, 'message': 'Não autenticado'}), 401
    
    try:
        response = supabase_admin.table('rh_cargos')\
            .select('*')\
            .order('nome_cargo')\
            .execute()
        
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
def api_get_cargo(cargo_id):
    """API: Buscar cargo específico por ID"""
    if not check_api_bypass() and 'user' not in session:
        return jsonify({'success': False, 'message': 'Não autenticado'}), 401
    
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
def api_create_cargo():
    """API: Criar novo cargo"""
    if not check_api_bypass() and 'user' not in session:
        return jsonify({'success': False, 'message': 'Não autenticado'}), 401
    
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
            'descricao': data.get('descricao', '').strip() or None
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
def api_update_cargo(cargo_id):
    """API: Atualizar cargo"""
    if not check_api_bypass() and 'user' not in session:
        return jsonify({'success': False, 'message': 'Não autenticado'}), 401
    
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
def api_delete_cargo(cargo_id):
    """API: Deletar cargo (com verificação de dependências)"""
    if not check_api_bypass() and 'user' not in session:
        return jsonify({'success': False, 'message': 'Não autenticado'}), 401
    
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
def api_list_departamentos():
    """API: Listar todos os departamentos"""
    if not check_api_bypass() and 'user' not in session:
        return jsonify({'success': False, 'message': 'Não autenticado'}), 401
    
    try:
        response = supabase_admin.table('rh_departamentos')\
            .select('*')\
            .order('nome_departamento')\
            .execute()
        
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
def api_get_departamento(departamento_id):
    """API: Buscar departamento específico por ID"""
    if not check_api_bypass() and 'user' not in session:
        return jsonify({'success': False, 'message': 'Não autenticado'}), 401
    
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
def api_create_departamento():
    """API: Criar novo departamento"""
    if not check_api_bypass() and 'user' not in session:
        return jsonify({'success': False, 'message': 'Não autenticado'}), 401
    
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
def api_update_departamento(departamento_id):
    """API: Atualizar departamento"""
    if not check_api_bypass() and 'user' not in session:
        return jsonify({'success': False, 'message': 'Não autenticado'}), 401
    
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
def api_delete_departamento(departamento_id):
    """API: Deletar departamento (com verificação de dependências)"""
    if not check_api_bypass() and 'user' not in session:
        return jsonify({'success': False, 'message': 'Não autenticado'}), 401
    
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

