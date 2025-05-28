from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from extensions import supabase, supabase_admin
from routes.auth import login_required, role_required
import uuid
import datetime
import json
import re

bp = Blueprint('usuarios', __name__)

VALID_ROLES = ['admin', 'interno_unique', 'cliente_unique']

@bp.route('/usuarios')
@login_required
@role_required(['admin'])
def index():
    try:
        print("[DEBUG] Iniciando busca de usuários")
        
        if not supabase:
            raise Exception("Cliente Supabase não está inicializado")
        
        users_response = supabase.table('users').select('*').execute()
        
        print(f"[DEBUG] Resposta da busca: {users_response}")
        print(f"[DEBUG] Tipo da resposta: {type(users_response)}")
        
        if not hasattr(users_response, 'data'):
            raise Exception("Resposta do Supabase não contém dados")
            
        users = users_response.data
        
        print(f"[DEBUG] Usuários encontrados: {len(users) if users else 0}")
        
        if not users:
            print("[DEBUG] Nenhum usuário encontrado")
            return render_template('usuarios/index.html', users=[])
        
        for user in users:
            if not isinstance(user, dict):
                print(f"[DEBUG] Usuário em formato inválido: {user}")
                continue
                
            if user.get('role') == 'cliente_unique':
                try:
                    agent_response = supabase.table('clientes_agentes').select('empresa').eq('user_id', user['id']).execute()
                    user['agent_info'] = {'empresas': []}
                    
                    if agent_response.data and agent_response.data[0].get('empresa'):
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
                                empresa_info = supabase.table('importacoes_clientes').select('cnpj, razao_social').eq('cnpj', cnpj).execute()
                                if empresa_info.data:
                                    empresa_data = empresa_info.data[0]
                                    empresas_detalhadas.append({
                                        'cnpj': empresa_data.get('cnpj'),
                                        'razao_social': empresa_data.get('razao_social', 'Não informado')
                                    })
                                else:
                                    empresas_detalhadas.append({
                                        'cnpj': cnpj,
                                        'razao_social': 'Empresa não encontrada'
                                    })
                        user['agent_info']['empresas'] = empresas_detalhadas
                except Exception as e:
                    print(f"[DEBUG] Erro ao buscar empresas para usuário {user.get('id')}: {str(e)}")
                    user['agent_info'] = {'empresas': []}
            else:
                user['agent_info'] = {'empresas': []}
        
        return render_template('usuarios/index.html', users=users)
    except Exception as e:
        print(f"[DEBUG] Erro ao carregar usuários: {str(e)}\nTipo do erro: {type(e)}")
        import traceback
        print("[DEBUG] Traceback completo:")
        print(traceback.format_exc())
        flash(f'Erro ao carregar usuários: {str(e)}', 'error')
        return render_template('usuarios/index.html', users=[])

@bp.route('/usuarios/novo', methods=['GET'])
@login_required
@role_required(['admin'])
def novo():
    return render_template('usuarios/form.html')

@bp.route('/usuarios/<user_id>/editar', methods=['GET'])
@login_required
@role_required(['admin'])
def editar(user_id):
    try:
        user_response = supabase.table('users').select('*').eq('id', user_id).execute()
        if user_response.data:
            user = user_response.data[0]
            return render_template('usuarios/form.html', user=user)
        else:
            flash('Usuário não encontrado', 'error')
            return redirect(url_for('usuarios.index'))
    except Exception as e:
        flash(f'Erro ao carregar usuário: {str(e)}', 'error')
        return redirect(url_for('usuarios.index'))
    
@bp.route('/usuarios/novo', methods=['POST'])
@bp.route('/usuarios/<user_id>/editar', methods=['POST'])
@login_required
@role_required(['admin']) # Apenas admins podem criar/editar usuários
def salvar(user_id=None):
    try:
        # Coletar dados do formulário
        name = request.form.get('name')
        email = request.form.get('email')
        role = request.form.get('role')
        senha = request.form.get('senha')
        
        # Validação básica
        if not all([name, email, role]):
            flash('Nome, Email e Perfil são obrigatórios.', 'error')
            return redirect(request.url)

        if role not in VALID_ROLES:
            flash(f'Perfil inválido. Perfis permitidos: {", ".join(VALID_ROLES)}', 'error')
            return redirect(request.url)
        
        if user_id:  # Editar usuário existente
            try:
                # Atualizar informações do usuário na tabela public.users
                update_data = {
                    'name': name,
                    'email': email,
                    'role': role,
                    'updated_at': datetime.datetime.utcnow().isoformat()
                }
                
                # Executa a atualização na tabela 'users'
                # O trigger de 'updated_at' cuidará do campo updated_at no DB
                supabase.table('users').update(update_data).eq('id', user_id).execute()
                
                # Atualizar metadados do usuário no Supabase Auth
                # Isso é importante para manter os metadados em auth.users sincronizados
                try:
                    supabase_admin.auth.admin.update_user_by_id(
                        user_id,
                        {'email': email, 'user_metadata': {'name': name, 'role': role}}
                    )
                except Exception as auth_error:
                    print(f"Erro ao atualizar autenticação para {user_id}: {str(auth_error)}")
                    # Continua mesmo se falhar a atualização do auth, pois a tabela 'users' já foi atualizada
                
                flash('Usuário atualizado com sucesso!', 'success')
                return redirect(url_for('usuarios.index'))
                
            except Exception as e:
                flash(f'Erro ao atualizar usuário: {str(e)}', 'error')
                return redirect(request.url)
                
        else:  # Novo usuário
            try:
                if not senha:
                    flash('A senha é obrigatória para novos usuários', 'error')
                    return redirect(request.url)
                
                # Gerar um UUID para o novo usuário.
                # A lógica para 'system@uniqueaduaneira.com.br' é mantida se for um caso especial.
                new_user_uuid = '669c13f5-f8ec-4030-be59-e5b563fa88c3' if email == 'system@uniqueaduaneira.com.br' else str(uuid.uuid4())
                
                # Criar usuário no Supabase Auth primeiro
                # O trigger no banco de dados cuidará da inserção na tabela public.users
                auth_user_response = supabase_admin.auth.admin.create_user({
                    'uid': new_user_uuid, # Passa o UUID gerado
                    'email': email,
                    'password': senha,
                    'email_confirm': True, # Define como True para confirmar o email automaticamente
                    'user_metadata': { # Metadados que serão lidos pelo trigger
                        'name': name,
                        'role': role
                    }
                })
                
                # 'auth_user_response' será um objeto com 'data' e 'error'
                if auth_user_response.get('error'):
                    raise Exception(f"Falha ao criar usuário na autenticação: {auth_user_response['error'].get('message', 'Erro desconhecido')}")
                
                # Não é mais necessário inserir explicitamente na tabela 'users' aqui.
                # O trigger 'on_auth_user_created' fará isso automaticamente.

                # Se for cliente_unique, criar registro em clientes_agentes
                if role == 'cliente_unique':
                    agent_data = {
                        'user_id': new_user_uuid, # Usa o UUID do usuário recém-criado
                        'empresa': [] # Supondo que 'empresa' é um array JSONB vazio inicialmente
                    }
                    supabase.table('clientes_agentes').insert(agent_data).execute()
                
                flash('Usuário criado com sucesso!', 'success')
                return redirect(url_for('usuarios.index'))
                
            except Exception as auth_error:
                # Se houver erro na criação do auth, tentar limpar o usuário recém-criado no Auth
                # Apenas se o erro ocorreu APÓS a criação do usuário no auth, mas ANTES de outras operações
                try:
                    # new_user_uuid deve estar definido aqui se o erro foi na criação do Auth
                    if 'new_user_uuid' in locals() and new_user_uuid:
                        supabase_admin.auth.admin.delete_user(new_user_uuid)
                        print(f"Usuário {new_user_uuid} excluído após erro na criação.")
                except Exception as cleanup_error:
                    print(f"Erro ao tentar limpar usuário após falha: {str(cleanup_error)}")
                    pass # Ignora erros na limpeza para não mascarar o erro original
                
                flash(f'Erro ao criar usuário: {str(auth_error)}', 'error')
                return redirect(request.url)
                
    except Exception as e:
        print(f"Erro geral ao salvar usuário: {str(e)}")
        flash(f'Erro ao salvar usuário: {str(e)}', 'error')
        return redirect(request.url)

@bp.route('/usuarios/<user_id>/excluir', methods=['POST'])
@login_required
@role_required(['admin'])
def excluir(user_id):
    try:
        # Remover da tabela users
        supabase.table('users').delete().eq('id', user_id).execute()
        
        # Remover da tabela clientes_agentes se existir
        supabase.table('clientes_agentes').delete().eq('user_id', user_id).execute()
        
        # Remover do Auth (opcional)
        try:
            supabase_admin.auth.admin.delete_user(user_id)
        except:
            pass  # Se não conseguir deletar do auth, não é crítico
        
        flash('Usuário excluído com sucesso!', 'success')
    except Exception as e:
        flash(f'Erro ao excluir usuário: {str(e)}', 'error')
    
    return redirect(url_for('usuarios.index'))

@bp.route('/usuarios/pesquisar-empresa', methods=['POST'])
@login_required
@role_required(['admin'])
def pesquisar_empresa():
    try:
        data = request.get_json()
        cnpj = data.get('cnpj')
        
        if not cnpj:
            return jsonify({'success': False, 'message': 'CNPJ não informado'})
        
        empresa_info = supabase.table('importacoes_clientes').select('cnpj, razao_social').eq('cnpj', cnpj).execute()
        
        print(f"[DEBUG] Resultado da busca de empresa: {empresa_info.data}")
        
        if empresa_info.data:
            empresa = empresa_info.data[0]
            return jsonify({
                'success': True,
                'empresa': {
                    'cnpj': empresa['cnpj'],
                    'razao_social': empresa['razao_social']
                }
            })
        else:
            return jsonify({'success': False, 'message': 'Empresa não encontrada'})
    except Exception as e:
        print(f"[DEBUG] Erro ao pesquisar empresa: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/usuarios/<user_id>/empresas', methods=['POST'])
@login_required
@role_required(['admin'])
def adicionar_empresa_usuario(user_id):
    try:
        data = request.get_json()
        cnpj = data.get('cnpj')
        
        if not cnpj:
            return jsonify({'error': 'CNPJ não informado'}), 400

        # Verificar se o usuário existe e é do tipo cliente_unique
        user_response = supabase.table('users').select('role').eq('id', user_id).execute()
        if not user_response.data or user_response.data[0].get('role') != 'cliente_unique':
            return jsonify({'error': 'Usuário inválido ou não é um cliente'}), 400
        
        # Buscar empresas atuais do usuário
        user_companies = supabase.table('clientes_agentes').select('empresa').eq('user_id', user_id).execute()
        
        if user_companies.data:
            empresas = user_companies.data[0].get('empresa', [])
            print(f"[DEBUG] Empresas atuais: {empresas}")
            
            # Normalizar formato
            if isinstance(empresas, str):
                try:
                    empresas = json.loads(empresas)
                except:
                    empresas = [empresas] if empresas else []
            elif not isinstance(empresas, list):
                empresas = []
            
            # Verificar se empresa já existe
            if cnpj in empresas:
                return jsonify({'error': 'Empresa já vinculada ao usuário'}), 400
            
            # Adicionar nova empresa
            empresas.append(cnpj)
            print(f"[DEBUG] Novas empresas: {empresas}")
            
            # Atualizar no banco
            supabase.table('clientes_agentes').update({
                'empresa': empresas
            }).eq('user_id', user_id).execute()
        else:
            # Criar novo registro na tabela clientes_agentes
            supabase.table('clientes_agentes').insert({
                'user_id': user_id,
                'empresa': [cnpj]
            }).execute()
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"[DEBUG] Erro ao adicionar empresa: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/usuarios/<user_id>/empresas-detalhadas')
@login_required
@role_required(['admin'])
def get_empresas_detalhadas(user_id):
    try:
        print(f"[DEBUG] Buscando empresas para o usuário {user_id}")
        
        # Buscar empresas do usuário
        user_companies = supabase.table('clientes_agentes').select('empresa').eq('user_id', user_id).execute()
        print(f"[DEBUG] Resultado da busca de empresas: {user_companies.data}")
        
        empresas_detalhadas = []
        if user_companies.data and user_companies.data[0].get('empresa'):
            empresas_array = user_companies.data[0]['empresa']
            
            # Normalizar formato do array
            if isinstance(empresas_array, str):
                try:
                    empresas_array = json.loads(empresas_array)
                except:
                    empresas_array = [empresas_array] if empresas_array else []
                    
            print(f"[DEBUG] Array de empresas normalizado: {empresas_array}")
            
            # Buscar detalhes de cada empresa
            for cnpj in empresas_array:
                if isinstance(cnpj, str):
                    empresa_info = supabase.table('importacoes_clientes').select('cnpj, razao_social').eq('cnpj', cnpj).execute()
                    
                    if empresa_info.data:
                        empresas_detalhadas.append({
                            'cnpj': empresa_info.data[0].get('cnpj'),
                            'razao_social': empresa_info.data[0].get('razao_social', 'Não informado')
                        })
                    else:
                        empresas_detalhadas.append({
                            'cnpj': cnpj,
                            'razao_social': 'Empresa não encontrada'
                        })
        
        print(f"[DEBUG] Empresas detalhadas: {empresas_detalhadas}")
        return jsonify({'empresas': empresas_detalhadas})
    except Exception as e:
        print(f"[DEBUG] Erro ao buscar empresas detalhadas: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/usuarios/<user_id>/empresas/remover', methods=['POST'])
@login_required
@role_required(['admin'])
def remover_empresa_usuario(user_id):
    try:
        data = request.get_json()
        cnpj = data.get('cnpj')
        
        if not cnpj:
            return jsonify({'error': 'CNPJ não informado'}), 400
        
        # Buscar empresas atuais
        user_companies = supabase.table('clientes_agentes').select('empresa').eq('user_id', user_id).execute()
        
        if not user_companies.data:
            return jsonify({'error': 'Usuário não encontrado'}), 404
            
        empresas = user_companies.data[0].get('empresa', [])
        
        # Normalizar formato
        if isinstance(empresas, str):
            try:
                empresas = json.loads(empresas)
            except:
                empresas = [empresas] if empresas else []
                
        print(f"[DEBUG] Empresas antes da remoção: {empresas}")
        
        # Remover empresa
        if cnpj in empresas:
            empresas.remove(cnpj)
            
            print(f"[DEBUG] Empresas após remoção: {empresas}")
            
            # Atualizar no banco
            supabase.table('clientes_agentes').update({
                'empresa': empresas
            }).eq('user_id', user_id).execute()
            
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Empresa não encontrada'}), 404
            
    except Exception as e:
        print(f"[DEBUG] Erro ao remover empresa: {str(e)}")
        return jsonify({'error': str(e)}), 500



@bp.route('/usuarios/<user_id>/empresas', methods=['POST'])
@login_required
@role_required(['admin'])
def adicionar_empresas(user_id):
    try:
        data = request.get_json()
        empresas = data.get('empresas', [])
        
        if not empresas:
            return jsonify({'error': 'Nenhuma empresa fornecida'}), 400
            
        current_app.logger.debug(f'Adicionando empresas para usuário {user_id}: {empresas}')
        
        # Verificar se o usuário existe
        user = supabase.table('users').select('*').eq('id', user_id).execute()
        if not user.data:
            return jsonify({'error': 'Usuário não encontrado'}), 404
            
        # Criar as associações de empresa
        for empresa in empresas:
            data = {
                'user_id': user_id,
                'cnpj': empresa['cnpj'],
                'created_at': datetime.datetime.utcnow().isoformat()
            }
            result = supabase.table('user_empresas').insert(data).execute()
            current_app.logger.debug(f'Empresa {empresa["cnpj"]} associada ao usuário {user_id}')
            
        return jsonify({'message': 'Empresas adicionadas com sucesso'})
        
    except Exception as e:
        current_app.logger.error(f'Erro ao adicionar empresas: {str(e)}')
        return jsonify({'error': 'Erro ao adicionar empresas'}), 500

@bp.route('/usuarios/<user_id>/empresas', methods=['GET'])
@login_required
@role_required(['admin'])
def listar_empresas(user_id):
    try:
        # Buscar o registro do cliente_agente
        result = supabase.table('clientes_agentes').select('*').eq('user_id', user_id).execute()
        
        if not result.data:
            return jsonify({'empresas': []})
            
        cliente_agente = result.data[0]
        empresas = cliente_agente.get('empresa', [])
        
        # Se empresas for uma string JSON, converter para lista
        if isinstance(empresas, str):
            try:
                empresas = json.loads(empresas)
            except:
                empresas = []
                
        # Buscar detalhes de cada empresa
        empresas_detalhadas = []
        for cnpj in empresas:
            empresa_info = supabase.table('importacoes_clientes').select('cnpj, razao_social').eq('cnpj', cnpj).execute()
            if empresa_info.data:
                empresas_detalhadas.append({
                    'cnpj': cnpj,
                    'razao_social': empresa_info.data[0].get('razao_social', 'Não informado')
                })
        
        return jsonify({'empresas': empresas_detalhadas})
        
    except Exception as e:
        current_app.logger.error(f'Erro ao listar empresas: {str(e)}')
        return jsonify({'error': 'Erro ao listar empresas'}), 500
        
@bp.route('/usuarios/<user_id>/empresas/remover', methods=['POST'])
@login_required
@role_required(['admin'])
def remover_empresa(user_id):
    try:
        data = request.get_json()
        cnpj = data.get('cnpj')
        
        if not cnpj:
            return jsonify({'error': 'CNPJ não informado'}), 400
            
        current_app.logger.debug(f'Removendo empresa {cnpj} do usuário {user_id}')
        
        # Buscar registro atual
        result = supabase.table('clientes_agentes').select('empresa').eq('user_id', user_id).execute()
        
        if not result.data:
            return jsonify({'error': 'Cliente não encontrado'}), 404
            
        cliente_agente = result.data[0]
        empresas = cliente_agente.get('empresa', [])
        
        # Se empresas for uma string JSON, converter para lista
        if isinstance(empresas, str):
            try:
                empresas = json.loads(empresas)
            except:
                empresas = []
                
        # Remover o CNPJ da lista
        if cnpj in empresas:
            empresas.remove(cnpj)
            
            # Atualizar o registro
            supabase.table('clientes_agentes').update({
                'empresa': empresas
            }).eq('user_id', user_id).execute()
            
        return jsonify({'message': 'Empresa removida com sucesso'})
        
    except Exception as e:
        current_app.logger.error(f'Erro ao remover empresa: {str(e)}')
        return jsonify({'error': 'Erro ao remover empresa'}), 500

@bp.route('/usuarios/criar', methods=['POST'])
@login_required
@role_required(['admin'])
def criar():
    try:
        data = request.form.to_dict()
        selected_companies = json.loads(data.get('selected_companies', '[]'))
        
        # Validar role
        if data['role'] not in VALID_ROLES:
            flash('Role inválida', 'error')
            return redirect(url_for('usuarios.novo'))
        
        # Criar usuário no Auth do Supabase
        user_data = {
            'email': data['email'],
            'password': data['password'],
            'email_confirm': True
        }
        
        auth_response = supabase_admin.auth.admin.create_user(user_data)
        
        if not auth_response.user:
            flash('Erro ao criar usuário no Auth', 'error')
            return redirect(url_for('usuarios.novo'))
            
        user_id = auth_response.user.id
        
        # Adicionar informações adicionais na tabela users
        user_metadata = {
            'id': user_id,
            'email': data['email'],
            'role': data['role'],
            'name': data['name'],
            'created_at': datetime.datetime.utcnow().isoformat()
        }
        
        supabase.table('users').insert(user_metadata).execute()
          # Se houver empresas selecionadas, criar/atualizar o registro em clientes_agentes
        if selected_companies:
            # Preparar array de CNPJs
            empresas_cnpjs = [empresa['cnpj'] for empresa in selected_companies]
            
            cliente_data = {
                'user_id': user_id,
                'empresa': empresas_cnpjs,
                'created_at': datetime.datetime.utcnow().isoformat(),
                'name': data['name'],
                'numero': data.get('numero', ''),
                'aceite_termos': data.get('aceite_termos', False)
            }
            
            # Inserir na tabela clientes_agentes
            supabase.table('clientes_agentes').insert(cliente_data).execute()
        
        flash('Usuário criado com sucesso!', 'success')
        return redirect(url_for('usuarios.index'))
        
    except Exception as e:
        current_app.logger.error(f'Erro ao criar usuário: {str(e)}')
        flash(f'Erro ao criar usuário: {str(e)}', 'error')
        return redirect(url_for('usuarios.novo'))
