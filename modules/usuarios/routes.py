from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from extensions import supabase, supabase_admin
from routes.auth import login_required, role_required
import uuid
import datetime
import json
import re
import traceback

# Blueprint com configuração para templates e static locais
bp = Blueprint('usuarios', __name__, 
               url_prefix='/usuarios',
               template_folder='templates',
               static_folder='static',
               static_url_path='/usuarios/static')

VALID_ROLES = ['admin', 'interno_unique', 'cliente_unique']

def carregar_usuarios():
    """Função auxiliar para carregar usuários do banco de dados"""
    try:
        print("[DEBUG] Iniciando busca de usuários")
        
        if not supabase:
            raise Exception("Cliente Supabase não está inicializado")
          # Adicionar timeout e tratamento específico para erros do Supabase
        users_response = supabase_admin.table('users').select('*').execute()
        
        print(f"[DEBUG] Resposta da busca: {users_response}")
        print(f"[DEBUG] Tipo da resposta: {type(users_response)}")
          # Verificar se houve erro na resposta
        if hasattr(users_response, 'error') and users_response.error:
            raise Exception(f"Erro do Supabase: {users_response.error}")
        
        if not hasattr(users_response, 'data'):
            raise Exception("Resposta do Supabase não contém dados")
            
        users = users_response.data
        
        print(f"[DEBUG] Usuários encontrados: {len(users) if users else 0}")
        
        if not users:
            print("[DEBUG] Nenhum usuário encontrado - retornando lista vazia")
            return []
        
        for user in users:
            if not isinstance(user, dict):
                print(f"[DEBUG] Usuário em formato inválido: {user}")
                continue
                
            if user.get('role') == 'cliente_unique':
                try:
                    agent_response = supabase_admin.table('clientes_agentes').select('empresa').eq('user_id', user['id']).execute()
                    user['agent_info'] = {'empresas': []}
                    
                    if agent_response.data and len(agent_response.data) > 0 and agent_response.data[0].get('empresa'):
                        empresas = agent_response.data[0].get('empresa', [])
                        if isinstance(empresas, str):
                            try:
                                empresas = json.loads(empresas)
                            except json.JSONDecodeError:
                                empresas = [empresas] if empresas else []
                        elif not isinstance(empresas, list):
                            empresas = []
                        
                        empresas_detalhadas = []
                        for cnpj in empresas:
                            if isinstance(cnpj, str):
                                try:
                                    empresa_info = supabase_admin.table('vw_aux_cnpj_importador').select('cnpj, razao_social').eq('cnpj', cnpj).execute()
                                    if empresa_info.data and len(empresa_info.data) > 0:
                                        empresa_data = empresa_info.data[0]
                                        razao = empresa_data.get('razao_social')
                                        empresas_detalhadas.append({
                                            'cnpj': empresa_data.get('cnpj'),
                                            'razao_social': razao if razao else None
                                        })
                                    else:
                                        empresas_detalhadas.append({
                                            'cnpj': cnpj
                                        })
                                except Exception as empresa_error:
                                    print(f"[DEBUG] Erro ao buscar dados da empresa {cnpj}: {str(empresa_error)}")
                                    empresas_detalhadas.append({
                                        'cnpj': cnpj
                                    })
                        user['agent_info']['empresas'] = empresas_detalhadas
                except Exception as e:
                    print(f"[DEBUG] Erro ao buscar empresas para usuário {user.get('id')}: {str(e)}")
                    user['agent_info'] = {'empresas': []}
            else:
                user['agent_info'] = {'empresas': []}
        
        return users
    except Exception as e:
        print(f"[DEBUG] Erro ao carregar usuários: {str(e)}\nTipo do erro: {type(e)}")
        print("[DEBUG] Traceback completo:")
        print(traceback.format_exc())
        raise e

@bp.route('/')
@login_required
@role_required(['admin'])
def index():
    try:
        users = carregar_usuarios()
        return render_template('usuarios.html', users=users)
    except Exception as e:
        flash(f'Erro ao carregar usuários: {str(e)}', 'error')
        return render_template('usuarios.html', users=[])

@bp.route('/refresh')
@login_required
@role_required(['admin'])
def refresh():
    """Endpoint para forçar atualização da lista de usuários"""
    try:
        users = carregar_usuarios()
        flash('Lista de usuários atualizada com sucesso!', 'success')
        return render_template('index.html', users=users)
    except Exception as e:
        flash(f'Erro ao atualizar lista de usuários: {str(e)}', 'error')
        return render_template('index.html', users=[])

@bp.route('/novo', methods=['GET'])
@login_required
@role_required(['admin'])
def novo():
    return render_template('form.html')

@bp.route('/<user_id>/editar', methods=['GET'])
@login_required
@role_required(['admin'])
def editar(user_id):
    try:
        user_response = supabase_admin.table('users').select('*').eq('id', user_id).execute()
        if user_response.data:
            user = user_response.data[0]
            # Buscar empresas associadas se for cliente_unique
            if user.get('role') == 'cliente_unique':
                agent_response = supabase_admin.table('clientes_agentes').select('empresa').eq('user_id', user['id']).execute()
                user['agent_info'] = {'empresas': []}
                if agent_response.data and len(agent_response.data) > 0 and agent_response.data[0].get('empresa'):
                    empresas = agent_response.data[0].get('empresa', [])
                    if isinstance(empresas, str):
                        try:
                            empresas = json.loads(empresas)
                        except json.JSONDecodeError:
                            empresas = [empresas] if empresas else []
                    elif not isinstance(empresas, list):
                        empresas = []
                    empresas_detalhadas = []
                    for cnpj in empresas:
                        if isinstance(cnpj, str):
                            empresas_detalhadas.append({'cnpj': cnpj})
                    user['agent_info']['empresas'] = empresas_detalhadas
            else:
                user['agent_info'] = {'empresas': []}
            return render_template('form.html', user=user)
        else:
            flash('Usuário não encontrado', 'error')
            return redirect(url_for('usuarios.index'))
    except Exception as e:
        flash(f'Erro ao carregar usuário: {str(e)}', 'error')
        return redirect(url_for('usuarios.index'))

@bp.route('/novo', methods=['POST'])
@bp.route('/<user_id>/editar', methods=['POST'])
@login_required
@role_required(['admin'])
def salvar(user_id=None):
    try:
        # Coletar dados do formulário
        name = request.form.get('name')
        email = request.form.get('email')
        role = request.form.get('role')
        is_active = request.form.get('is_active') == 'true'

        # Validações básicas
        if not name or not email or not role:
            flash('Nome, email e role são obrigatórios', 'error')
            if user_id:
                return redirect(url_for('usuarios.editar', user_id=user_id))
            else:
                return redirect(url_for('usuarios.novo'))

        # Validar formato do email
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            flash('Formato de email inválido', 'error')
            if user_id:
                return redirect(url_for('usuarios.editar', user_id=user_id))
            else:
                return redirect(url_for('usuarios.novo'))

        # Validar role
        if role not in VALID_ROLES:
            flash('Role inválida', 'error')
            if user_id:
                return redirect(url_for('usuarios.editar', user_id=user_id))
            else:
                return redirect(url_for('usuarios.novo'))

        user_data = {
            'name': name,
            'email': email,
            'role': role,
            'is_active': is_active,
            'updated_at': datetime.datetime.now().isoformat()
        }

        if user_id:
            # Atualizar usuário existente
            print(f"[DEBUG] Atualizando usuário {user_id} com dados: {user_data}")
            response = supabase_admin.table('users').update(user_data).eq('id', user_id).execute()
            
            if response.data:
                print(f"[DEBUG] Usuário atualizado com sucesso: {response.data}")
                flash('Usuário atualizado com sucesso!', 'success')
            else:
                print(f"[DEBUG] Erro ao atualizar usuário: {response}")
                flash('Erro ao atualizar usuário', 'error')
                return redirect(url_for('usuarios.editar', user_id=user_id))
        else:
            # Criar novo usuário
            user_data['id'] = str(uuid.uuid4())
            user_data['created_at'] = datetime.datetime.now().isoformat()
            
            # Verificar se email já existe
            existing_user = supabase_admin.table('users').select('id').eq('email', email).execute()
            if existing_user.data:
                flash('Email já está em uso por outro usuário', 'error')
                return redirect(url_for('usuarios.novo'))
            
            print(f"[DEBUG] Criando novo usuário com dados: {user_data}")
            response = supabase_admin.table('users').insert(user_data).execute()
            
            if response.data:
                print(f"[DEBUG] Usuário criado com sucesso: {response.data}")
                flash('Usuário criado com sucesso!', 'success')
            else:
                print(f"[DEBUG] Erro ao criar usuário: {response}")
                flash('Erro ao criar usuário', 'error')
                return redirect(url_for('usuarios.novo'))

        return redirect(url_for('usuarios.index'))
        
    except Exception as e:
        print(f"[DEBUG] Erro ao salvar usuário: {str(e)}")
        print("[DEBUG] Traceback completo:")
        print(traceback.format_exc())
        flash(f'Erro ao salvar usuário: {str(e)}', 'error')
        
        if user_id:
            return redirect(url_for('usuarios.editar', user_id=user_id))
        else:
            return redirect(url_for('usuarios.novo'))

@bp.route('/<user_id>/deletar', methods=['POST'])
@login_required
@role_required(['admin'])
def deletar(user_id):
    try:
        print(f"[DEBUG] Tentando deletar usuário: {user_id}")
        
        # Verificar se o usuário existe
        user_response = supabase_admin.table('users').select('*').eq('id', user_id).execute()
        if not user_response.data:
            flash('Usuário não encontrado', 'error')
            return redirect(url_for('usuarios.index'))
        
        user = user_response.data[0]
        
        # Verificar se não está tentando deletar o próprio usuário
        current_user = session.get('user', {})
        if current_user.get('id') == user_id:
            flash('Você não pode deletar seu próprio usuário', 'error')
            return redirect(url_for('usuarios.index'))
        
        # Deletar associações de empresa se existirem
        if user.get('role') == 'cliente_unique':
            supabase_admin.table('clientes_agentes').delete().eq('user_id', user_id).execute()
        
        # Deletar usuário
        response = supabase_admin.table('users').delete().eq('id', user_id).execute()
        
        if response.data or response.count == 0:  # Supabase pode retornar count=0 para deletes bem-sucedidos
            print(f"[DEBUG] Usuário deletado com sucesso")
            flash(f'Usuário {user.get("name", "desconhecido")} deletado com sucesso!', 'success')
        else:
            print(f"[DEBUG] Erro ao deletar usuário: {response}")
            flash('Erro ao deletar usuário', 'error')
        
        return redirect(url_for('usuarios.index'))
        
    except Exception as e:
        print(f"[DEBUG] Erro ao deletar usuário: {str(e)}")
        print("[DEBUG] Traceback completo:")
        print(traceback.format_exc())
        flash(f'Erro ao deletar usuário: {str(e)}', 'error')
        return redirect(url_for('usuarios.index'))

@bp.route('/api/empresas')
@login_required
@role_required(['admin'])
def api_empresas():
    """API para buscar empresas disponíveis"""
    try:
        empresas_response = supabase_admin.table('vw_aux_cnpj_importador').select('cnpj, razao_social').execute()
        
        if empresas_response.data:
            empresas = [
                {
                    'cnpj': empresa['cnpj'],
                    'razao_social': empresa['razao_social']
                }
                for empresa in empresas_response.data
            ]
            return jsonify({'success': True, 'empresas': empresas})
        else:
            return jsonify({'success': False, 'error': 'Nenhuma empresa encontrada'})
            
    except Exception as e:
        print(f"[DEBUG] Erro ao buscar empresas: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/<user_id>/empresas', methods=['POST'])
@login_required
@role_required(['admin'])
def associar_empresas(user_id):
    """Associar empresas a um usuário cliente"""
    try:
        empresas_selecionadas = request.json.get('empresas', [])
        
        # Verificar se o usuário é do tipo cliente_unique
        user_response = supabase_admin.table('users').select('role').eq('id', user_id).execute()
        if not user_response.data or user_response.data[0]['role'] != 'cliente_unique':
            return jsonify({'success': False, 'error': 'Usuário deve ser do tipo cliente_unique'})
        
        # Verificar se já existe associação
        existing_response = supabase_admin.table('clientes_agentes').select('id').eq('user_id', user_id).execute()
        
        association_data = {
            'user_id': user_id,
            'empresa': empresas_selecionadas,
            'updated_at': datetime.datetime.now().isoformat()
        }
        
        if existing_response.data:
            # Atualizar associação existente
            response = supabase_admin.table('clientes_agentes').update(association_data).eq('user_id', user_id).execute()
        else:
            # Criar nova associação
            association_data['id'] = str(uuid.uuid4())
            association_data['created_at'] = datetime.datetime.now().isoformat()
            response = supabase_admin.table('clientes_agentes').insert(association_data).execute()
        
        if response.data:
            return jsonify({'success': True, 'message': 'Empresas associadas com sucesso!'})
        else:
            return jsonify({'success': False, 'error': 'Erro ao associar empresas'})
            
    except Exception as e:
        print(f"[DEBUG] Erro ao associar empresas: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/<user_id>/empresas', methods=['GET'])
@login_required
@role_required(['admin'])
def obter_empresas_usuario(user_id):
    """Obter empresas associadas a um usuário"""
    try:
        response = supabase_admin.table('clientes_agentes').select('empresa').eq('user_id', user_id).execute()
        
        if response.data and response.data[0].get('empresa'):
            empresas = response.data[0]['empresa']
            if isinstance(empresas, str):
                try:
                    empresas = json.loads(empresas)
                except json.JSONDecodeError:
                    empresas = [empresas] if empresas else []
            elif not isinstance(empresas, list):
                empresas = []
            
            return jsonify({'success': True, 'empresas': empresas})
        else:
            return jsonify({'success': True, 'empresas': []})
            
    except Exception as e:
        print(f"[DEBUG] Erro ao obter empresas do usuário: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/api/empresas/buscar', methods=['POST'])
@login_required
@role_required(['admin'])
def buscar_empresa():
    """Buscar empresa por CNPJ"""
    try:
        data = request.get_json()
        cnpj = data.get('cnpj', '').strip()
        
        if not cnpj:
            return jsonify({'success': False, 'error': 'CNPJ não informado'})
        
        print(f"[DEBUG] Buscando empresa com CNPJ: {cnpj}")
        
        # Buscar empresa na view
        empresa_response = supabase_admin.table('vw_aux_cnpj_importador').select('cnpj, razao_social').eq('cnpj', cnpj).execute()
        
        if empresa_response.data and len(empresa_response.data) > 0:
            empresa = empresa_response.data[0]
            return jsonify({
                'success': True,
                'empresa': {
                    'cnpj': empresa['cnpj'],
                    'razao_social': empresa['razao_social']
                }
            })
        else:
            return jsonify({'success': False, 'error': 'Empresa não encontrada'})
            
    except Exception as e:
        print(f"[DEBUG] Erro ao buscar empresa: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/<user_id>/empresas/adicionar', methods=['POST'])
@login_required
@role_required(['admin'])
def adicionar_empresa_usuario(user_id):
    """Adicionar empresa a um usuário"""
    try:
        data = request.get_json()
        cnpj = data.get('cnpj', '').strip()
        
        if not cnpj:
            return jsonify({'success': False, 'error': 'CNPJ não informado'})
        
        print(f"[DEBUG] Adicionando empresa {cnpj} ao usuário {user_id}")
        
        # Verificar se o usuário é cliente_unique
        user_response = supabase_admin.table('users').select('role').eq('id', user_id).execute()
        if not user_response.data or user_response.data[0]['role'] != 'cliente_unique':
            return jsonify({'success': False, 'error': 'Usuário deve ser do tipo cliente_unique'})
        
        # Buscar empresas atuais
        empresas_response = supabase_admin.table('clientes_agentes').select('empresa').eq('user_id', user_id).execute()
        
        empresas = []
        if empresas_response.data and empresas_response.data[0].get('empresa'):
            empresas = empresas_response.data[0]['empresa']
            if isinstance(empresas, str):
                try:
                    empresas = json.loads(empresas)
                except json.JSONDecodeError:
                    empresas = [empresas] if empresas else []
            elif not isinstance(empresas, list):
                empresas = []
        
        # Verificar se empresa já está associada
        if cnpj in empresas:
            return jsonify({'success': False, 'error': 'Empresa já está associada ao usuário'})
        
        # Adicionar nova empresa
        empresas.append(cnpj)
        
        # Atualizar no banco
        if empresas_response.data:
            # Atualizar registro existente
            supabase_admin.table('clientes_agentes').update({
                'empresa': empresas,
                'updated_at': datetime.datetime.now().isoformat()
            }).eq('user_id', user_id).execute()
        else:
            # Criar novo registro
            supabase_admin.table('clientes_agentes').insert({
                'id': str(uuid.uuid4()),
                'user_id': user_id,
                'empresa': empresas,
                'created_at': datetime.datetime.now().isoformat(),
                'updated_at': datetime.datetime.now().isoformat()
            }).execute()
        
        return jsonify({'success': True, 'message': 'Empresa adicionada com sucesso'})
        
    except Exception as e:
        print(f"[DEBUG] Erro ao adicionar empresa: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/<user_id>/empresas/remover', methods=['POST'])
@login_required
@role_required(['admin'])
def remover_empresa_usuario(user_id):
    """Remover empresa de um usuário"""
    try:
        data = request.get_json()
        cnpj = data.get('cnpj', '').strip()
        
        if not cnpj:
            return jsonify({'success': False, 'error': 'CNPJ não informado'})
        
        print(f"[DEBUG] Removendo empresa {cnpj} do usuário {user_id}")
        
        # Buscar empresas atuais
        empresas_response = supabase_admin.table('clientes_agentes').select('empresa').eq('user_id', user_id).execute()
        
        if not empresas_response.data:
            return jsonify({'success': False, 'error': 'Usuário não possui empresas associadas'})
        
        empresas = empresas_response.data[0].get('empresa', [])
        if isinstance(empresas, str):
            try:
                empresas = json.loads(empresas)
            except json.JSONDecodeError:
                empresas = [empresas] if empresas else []
        elif not isinstance(empresas, list):
            empresas = []
        
        # Verificar se empresa está na lista
        if cnpj not in empresas:
            return jsonify({'success': False, 'error': 'Empresa não está associada ao usuário'})
        
        # Remover empresa
        empresas.remove(cnpj)
        
        # Atualizar no banco
        supabase_admin.table('clientes_agentes').update({
            'empresa': empresas,
            'updated_at': datetime.datetime.now().isoformat()
        }).eq('user_id', user_id).execute()
        
        return jsonify({'success': True, 'message': 'Empresa removida com sucesso'})
        
    except Exception as e:
        print(f"[DEBUG] Erro ao remover empresa: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/<user_id>/dados', methods=['GET'])
@login_required
@role_required(['admin'])
def obter_dados_usuario(user_id):
    """Obter dados completos de um usuário para edição"""
    try:
        print(f"[DEBUG] Buscando dados do usuário: {user_id}")
        
        # Buscar dados básicos do usuário
        user_response = supabase_admin.table('users').select('*').eq('id', user_id).execute()
        
        if not user_response.data:
            print(f"[DEBUG] Usuário {user_id} não encontrado")
            return jsonify({'success': False, 'error': 'Usuário não encontrado'})
        
        user = user_response.data[0]
        print(f"[DEBUG] Dados do usuário encontrados: {user}")
        
        # Se for cliente_unique, buscar empresas associadas e detalhar com razão social
        if user.get('role') == 'cliente_unique':
            empresas_response = supabase_admin.table('clientes_agentes').select('empresa').eq('user_id', user_id).execute()
            empresas = []
            if empresas_response.data and empresas_response.data[0].get('empresa'):
                empresas = empresas_response.data[0]['empresa']
                if isinstance(empresas, str):
                    try:
                        empresas = json.loads(empresas)
                    except json.JSONDecodeError:
                        empresas = [empresas] if empresas else []
                elif not isinstance(empresas, list):
                    empresas = []
            empresas_detalhadas = []
            for cnpj in empresas:
                if isinstance(cnpj, str):
                    try:
                        empresa_info = supabase_admin.table('vw_aux_cnpj_importador').select('cnpj, razao_social').eq('cnpj', cnpj).execute()
                        if empresa_info.data and len(empresa_info.data) > 0:
                            empresa_data = empresa_info.data[0]
                            razao = empresa_data.get('razao_social')
                            empresas_detalhadas.append({
                                'cnpj': empresa_data.get('cnpj'),
                                'razao_social': razao if razao else None
                            })
                        else:
                            empresas_detalhadas.append({'cnpj': cnpj})
                    except Exception as empresa_error:
                        print(f"[DEBUG] Erro ao buscar dados da empresa {cnpj}: {str(empresa_error)}")
                        empresas_detalhadas.append({'cnpj': cnpj})
            user['empresas'] = empresas_detalhadas
        else:
            user['empresas'] = []
        return jsonify({'success': True, 'user': user})
        
    except Exception as e:
        print(f"[DEBUG] Erro ao obter dados do usuário: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})
