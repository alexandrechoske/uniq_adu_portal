from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from extensions import supabase, supabase_admin
from routes.auth import login_required, role_required
import uuid
import datetime
import json
import re
import traceback
import time

# Blueprint com configuração para templates e static locais
bp = Blueprint('usuarios', __name__, 
               url_prefix='/usuarios',
               template_folder='templates',
               static_folder='static',
               static_url_path='/usuarios/static')

VALID_ROLES = ['admin', 'interno_unique', 'cliente_unique']

# Cache simples em memória para usuários (TTL: 5 minutos)
_users_cache = {'data': None, 'timestamp': 0, 'ttl': 300}

def get_cached_users():
    """Retorna usuários do cache se válido, senão recarrega"""
    current_time = time.time()
    
    if (_users_cache['data'] is not None and 
        current_time - _users_cache['timestamp'] < _users_cache['ttl']):
        print(f"[DEBUG] Usando cache de usuários ({len(_users_cache['data'])} usuários)")
        return _users_cache['data']
    
    print("[DEBUG] Cache expirado ou inexistente, recarregando usuários...")
    users = carregar_usuarios()
    
    # Atualizar cache
    _users_cache['data'] = users
    _users_cache['timestamp'] = current_time
    
    return users

def invalidate_users_cache():
    """Invalida o cache de usuários"""
    global _users_cache
    _users_cache = {'data': None, 'timestamp': 0, 'ttl': 300}
    print("[DEBUG] Cache de usuários invalidado")

def retry_supabase_operation(operation, max_retries=2, delay=0.5):
    """Executa operação no Supabase com retry otimizado (menos agressivo)"""
    for attempt in range(max_retries):
        try:
            return operation()
        except Exception as e:
            error_msg = str(e).lower()
            if 'server disconnected' in error_msg or 'connection' in error_msg:
                if attempt < max_retries - 1:
                    print(f"[DEBUG] Tentativa {attempt + 1} falhou, tentando novamente em {delay}s...")
                    time.sleep(delay)
                    continue
                else:
                    print(f"[DEBUG] Todas as tentativas falharam após {max_retries} tentativas")
                    raise
            else:
                # Se não for erro de conexão, falha imediatamente
                raise

def verificar_empresa_ja_associada(user_id, cnpj):
    """Verifica se uma empresa já está associada ao usuário"""
    def _verificar():
        empresas_response = supabase_admin.table('clientes_agentes').select('empresa').eq('user_id', user_id).execute()
        
        if not empresas_response.data:
            return False
            
        empresas = empresas_response.data[0].get('empresa', [])
        if isinstance(empresas, str):
            try:
                empresas = json.loads(empresas)
            except json.JSONDecodeError:
                empresas = [empresas] if empresas else []
        elif not isinstance(empresas, list):
            empresas = []
            
        return cnpj in empresas
    
    try:
        return retry_supabase_operation(_verificar)
    except Exception as e:
        print(f"[DEBUG] Erro ao verificar empresa associada: {str(e)}")
        return False

def carregar_usuarios():
    """Função auxiliar otimizada para carregar usuários do banco de dados"""
    try:
        print("[DEBUG] Iniciando busca otimizada de usuários")
        start_time = time.time()
        
        if not supabase:
            raise Exception("Cliente Supabase não está inicializado")
        
        # 1. Buscar todos os usuários ordenados por nome
        def _buscar_usuarios():
            return supabase_admin.table('users').select('*').order('name').execute()
        
        users_response = retry_supabase_operation(_buscar_usuarios)
        
        if hasattr(users_response, 'error') and users_response.error:
            raise Exception(f"Erro do Supabase: {users_response.error}")
        
        if not hasattr(users_response, 'data'):
            raise Exception("Resposta do Supabase não contém dados")
            
        users = users_response.data
        
        if not users:
            print("[DEBUG] Nenhum usuário encontrado")
            return []
        
        print(f"[DEBUG] {len(users)} usuários encontrados")
        
        # 2. Buscar todas as associações de empresas de uma vez
        def _buscar_todas_empresas():
            return supabase_admin.table('clientes_agentes').select('user_id, empresa').execute()
        
        empresas_response = retry_supabase_operation(_buscar_todas_empresas)
        
        # Criar mapa de usuário -> empresas
        user_empresas_map = {}
        all_cnpjs = set()
        
        if empresas_response.data:
            for item in empresas_response.data:
                user_id = item.get('user_id')
                empresas = item.get('empresa', [])
                
                # Normalizar formato da lista de empresas
                if isinstance(empresas, str):
                    try:
                        empresas = json.loads(empresas)
                    except json.JSONDecodeError:
                        empresas = [empresas] if empresas else []
                elif not isinstance(empresas, list):
                    empresas = []
                
                user_empresas_map[user_id] = empresas
                all_cnpjs.update(empresas)
        
        # 3. Buscar informações de todas as empresas em lotes
        empresas_info_map = {}
        if all_cnpjs:
            cnpjs_list = list(all_cnpjs)
            print(f"[DEBUG] Buscando informações de {len(cnpjs_list)} empresas em lotes...")
            
            # Buscar em lotes de 50 para evitar URLs muito grandes
            batch_size = 50
            for i in range(0, len(cnpjs_list), batch_size):
                batch = cnpjs_list[i:i + batch_size]
                try:
                    def _buscar_lote_empresas():
                        return supabase_admin.table('vw_aux_cnpj_importador').select('cnpj, razao_social').in_('cnpj', batch).execute()
                    
                    batch_response = retry_supabase_operation(_buscar_lote_empresas)
                    
                    if batch_response.data:
                        for empresa in batch_response.data:
                            empresas_info_map[empresa['cnpj']] = empresa
                            
                except Exception as e:
                    print(f"[DEBUG] Erro ao buscar lote de empresas: {str(e)}")
        
        # 4. Montar dados finais dos usuários
        for user in users:
            if not isinstance(user, dict):
                continue
                
            # Incluir tanto cliente_unique quanto interno_unique
            if user.get('role') in ['cliente_unique', 'interno_unique']:
                user_id = user.get('id')
                empresas_cnpjs = user_empresas_map.get(user_id, [])
                
                empresas_detalhadas = []
                for cnpj in empresas_cnpjs:
                    if isinstance(cnpj, str) and cnpj:
                        empresa_info = empresas_info_map.get(cnpj, {'cnpj': cnpj, 'razao_social': None})
                        empresas_detalhadas.append(empresa_info)
                
                user['agent_info'] = {'empresas': empresas_detalhadas}
            else:
                user['agent_info'] = {'empresas': []}
        
        end_time = time.time()
        print(f"[DEBUG] Carregamento otimizado concluído em {end_time - start_time:.2f}s")
        
        return users
        
    except Exception as e:
        print(f"[DEBUG] Erro ao carregar usuários: {str(e)}")
        print(traceback.format_exc())
        raise e

@bp.route('/')
@login_required
@role_required(['admin'])
def index():
    try:
        users = get_cached_users()
        return render_template('usuarios.html', users=users)
    except Exception as e:
        flash(f'Erro ao carregar usuários: {str(e)}', 'error')
        return render_template('usuarios.html', users=[])

@bp.route('/refresh')
@login_required
@role_required(['admin'])
def refresh():
    """Endpoint para forçar atualização da lista de usuários invalidando cache"""
    try:
        invalidate_users_cache()
        users = get_cached_users()
        flash('Lista de usuários atualizada com sucesso!', 'success')
        return render_template('usuarios.html', users=users)
    except Exception as e:
        flash(f'Erro ao atualizar lista de usuários: {str(e)}', 'error')
        return render_template('usuarios.html', users=[])

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
        password = request.form.get('password')  # Apenas para novos usuários
        confirm_password = request.form.get('confirm_password')  # Apenas para novos usuários

        # Validações básicas
        if not name or not email or not role:
            flash('Nome, email e role são obrigatórios', 'error')
            if user_id:
                return redirect(url_for('usuarios.editar', user_id=user_id))
            else:
                return redirect(url_for('usuarios.novo'))

        # Validações específicas para novo usuário
        if not user_id:  # Apenas para criação
            if not password or not confirm_password:
                flash('Senha e confirmação de senha são obrigatórias', 'error')
                return redirect(url_for('usuarios.novo'))
            
            if password != confirm_password:
                flash('As senhas não coincidem', 'error')
                return redirect(url_for('usuarios.novo'))
            
            if len(password) < 6:
                flash('A senha deve ter pelo menos 6 caracteres', 'error')
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
                invalidate_users_cache()  # Invalidar cache após atualização
                flash('Usuário atualizado com sucesso!', 'success')
            else:
                print(f"[DEBUG] Erro ao atualizar usuário: {response}")
                flash('Erro ao atualizar usuário', 'error')
                return redirect(url_for('usuarios.editar', user_id=user_id))
        else:
            # Criar novo usuário
            # Verificar se email já existe primeiro
            existing_user = supabase_admin.table('users').select('id').eq('email', email).execute()
            if existing_user.data:
                flash('Email já está em uso por outro usuário', 'error')
                return redirect(url_for('usuarios.novo'))
            
            print(f"[DEBUG] Iniciando criação de usuário com email: {email}")
            
            try:
                # Primeiro, criar o usuário no auth do Supabase
                auth_response = supabase_admin.auth.admin.create_user({
                    "email": email,
                    "password": password,
                    "email_confirm": True,
                    "user_metadata": {
                        "name": name,
                        "role": role
                    }
                })
                
                if auth_response.user:
                    auth_user_id = auth_response.user.id
                    print(f"[DEBUG] Usuário auth criado com ID: {auth_user_id}")
                    
                    # Verificar se já existe na tabela users (para evitar duplicata)
                    existing_in_table = supabase_admin.table('users').select('id').eq('id', auth_user_id).execute()
                    if existing_in_table.data:
                        print(f"[DEBUG] Usuário já existe na tabela users, atualizando...")
                        # Atualizar dados se já existe
                        user_data['updated_at'] = datetime.datetime.now().isoformat()
                        response = supabase_admin.table('users').update(user_data).eq('id', auth_user_id).execute()
                    else:
                        # Inserir novo registro na tabela users
                        user_data['id'] = auth_user_id
                        user_data['created_at'] = datetime.datetime.now().isoformat()
                        print(f"[DEBUG] Inserindo usuário na tabela com dados: {user_data}")
                        response = supabase_admin.table('users').insert(user_data).execute()
                    
                    if response.data:
                        print(f"[DEBUG] Usuário criado/atualizado com sucesso: {response.data}")
                        invalidate_users_cache()  # Invalidar cache após mudança
                        flash('Usuário criado com sucesso!', 'success')
                    else:
                        print(f"[DEBUG] Erro ao inserir/atualizar usuário na tabela: {response}")
                        # Se falhar, tentar deletar o usuário auth criado
                        try:
                            print(f"[DEBUG] Tentando deletar usuário auth: {auth_user_id}")
                            supabase_admin.auth.admin.delete_user(auth_user_id)
                        except Exception as cleanup_error:
                            print(f"[DEBUG] Erro ao limpar usuário auth: {str(cleanup_error)}")
                        flash('Erro ao criar usuário na tabela do sistema', 'error')
                        return redirect(url_for('usuarios.novo'))
                else:
                    print(f"[DEBUG] Erro ao criar usuário auth: {auth_response}")
                    flash('Erro ao criar usuário no sistema de autenticação', 'error')
                    return redirect(url_for('usuarios.novo'))
                    
            except Exception as auth_error:
                print(f"[DEBUG] Erro na criação do usuário: {str(auth_error)}")
                print(f"[DEBUG] Tipo do erro: {type(auth_error)}")
                flash(f'Erro ao criar usuário: {str(auth_error)}', 'error')
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
            invalidate_users_cache()  # Invalidar cache após exclusão
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

def limpar_cnpj(cnpj):
    """Remove formatação do CNPJ deixando apenas números"""
    return re.sub(r'[^0-9]', '', cnpj)

def formatar_cnpj(cnpj_limpo):
    """Aplica formatação padrão XX.XXX.XXX/XXXX-XX ao CNPJ"""
    if len(cnpj_limpo) != 14:
        return cnpj_limpo
    return f"{cnpj_limpo[:2]}.{cnpj_limpo[2:5]}.{cnpj_limpo[5:8]}/{cnpj_limpo[8:12]}-{cnpj_limpo[12:14]}"

@bp.route('/api/empresas/buscar', methods=['POST'])
@login_required
@role_required(['admin'])
def buscar_empresa():
    """Buscar empresa por CNPJ ou Razão Social"""
    try:
        data = request.get_json()
        termo_busca = data.get('cnpj', '').strip()
        
        if not termo_busca:
            return jsonify({'success': False, 'error': 'Termo de busca não informado'})
        
        print(f"[DEBUG] Buscando empresa com termo: {termo_busca}")
        
        # Verificar se é CNPJ (só números ou com formatação)
        cnpj_limpo = limpar_cnpj(termo_busca)
        
        if cnpj_limpo.isdigit() and len(cnpj_limpo) == 14:
            # Busca por CNPJ - primeiro tenta com formatação, depois sem
            cnpj_formatado = formatar_cnpj(cnpj_limpo)
            
            print(f"[DEBUG] CNPJ limpo: {cnpj_limpo}")
            print(f"[DEBUG] CNPJ formatado: {cnpj_formatado}")
            
            # Buscar primeiro com formatação
            empresa_response = supabase_admin.table('vw_aux_cnpj_importador').select('cnpj, razao_social').eq('cnpj', cnpj_formatado).execute()
            
            # Se não encontrar, tenta sem formatação
            if not empresa_response.data:
                empresa_response = supabase_admin.table('vw_aux_cnpj_importador').select('cnpj, razao_social').eq('cnpj', cnpj_limpo).execute()
                
        else:
            # Busca por razão social (usando ilike para busca parcial case-insensitive)
            print(f"[DEBUG] Buscando por razão social: {termo_busca}")
            empresa_response = supabase_admin.table('vw_aux_cnpj_importador').select('cnpj, razao_social').ilike('razao_social', f'%{termo_busca}%').limit(10).execute()
        
        if empresa_response.data and len(empresa_response.data) > 0:
            if len(empresa_response.data) == 1:
                # Uma empresa encontrada
                empresa = empresa_response.data[0]
                return jsonify({
                    'success': True,
                    'empresa': {
                        'cnpj': empresa['cnpj'],
                        'razao_social': empresa['razao_social']
                    }
                })
            else:
                # Múltiplas empresas encontradas
                empresas = []
                for emp in empresa_response.data:
                    empresas.append({
                        'cnpj': emp['cnpj'],
                        'razao_social': emp['razao_social']
                    })
                return jsonify({
                    'success': True,
                    'multiple': True,
                    'empresas': empresas
                })
        else:
            return jsonify({'success': False, 'error': 'Empresa não encontrada'})
            
    except Exception as e:
        print(f"[DEBUG] Erro ao buscar empresa: {str(e)}")
        print(f"[DEBUG] Traceback: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/<user_id>/empresas/definir-lista', methods=['POST'])
@login_required
@role_required(['admin'])
def definir_lista_empresas(user_id):
    """Define a lista completa de empresas para um usuário (substitui a existente)"""
    try:
        data = request.get_json()
        cnpjs = data.get('cnpjs', [])
        
        print(f"[DEBUG] Definindo lista completa de {len(cnpjs)} CNPJs para usuário {user_id}")
        
        # Verificar se usuário existe
        def _verificar_usuario():
            return supabase_admin.table('users').select('id').eq('id', user_id).execute()
        
        user_response = retry_supabase_operation(_verificar_usuario)
        if not user_response.data:
            return jsonify({'success': False, 'error': 'Usuário não encontrado'})
        
        # Se a lista está vazia, remover todas as empresas
        if len(cnpjs) == 0:
            print(f"[DEBUG] Lista vazia - removendo todas as empresas do usuário {user_id}")
            
            def _remover_todas_empresas():
                # Primeiro tentar update
                response = supabase_admin.table('clientes_agentes').update({
                    'empresa': []
                }).eq('user_id', user_id).execute()
                
                # Se não houve linhas afetadas, pode não existir registro
                if not response.data:
                    # Criar registro vazio
                    return supabase_admin.table('clientes_agentes').insert({
                        'user_id': user_id,
                        'empresa': []
                    }).execute()
                return response
            
            try:
                remove_response = retry_supabase_operation(_remover_todas_empresas)
                if hasattr(remove_response, 'error') and remove_response.error:
                    raise Exception(f"Erro do Supabase: {remove_response.error}")
                
                return jsonify({
                    'success': True,
                    'message': 'Todas as empresas removidas com sucesso',
                    'resultado': {'sucessos': 0, 'erros': 0, 'ja_existentes': 0, 'removidas': True}
                })
            except Exception as e:
                print(f"[DEBUG] Erro ao remover empresas: {str(e)}")
                return jsonify({'success': False, 'error': f'Erro ao remover empresas: {str(e)}'})
        
        # Se há CNPJs, validar e definir a lista
        cnpjs_validos = []
        cnpjs_invalidos = []
        
        for cnpj in cnpjs:
            cnpj_limpo = limpar_cnpj(cnpj)
            
            # Verificar se empresa existe na base
            def _verificar_cnpj():
                cnpj_formatado = formatar_cnpj(cnpj_limpo)
                # Tentar primeiro com formatação
                response = supabase_admin.table('vw_aux_cnpj_importador').select('cnpj').eq('cnpj', cnpj_formatado).execute()
                if response.data:
                    return response
                # Se não encontrar, tentar sem formatação
                return supabase_admin.table('vw_aux_cnpj_importador').select('cnpj').eq('cnpj', cnpj_limpo).execute()
            
            try:
                cnpj_response = retry_supabase_operation(_verificar_cnpj)
                if cnpj_response.data:
                    cnpjs_validos.append(cnpj_limpo)
                else:
                    cnpjs_invalidos.append(cnpj)
            except Exception as e:
                print(f"[DEBUG] Erro ao verificar CNPJ {cnpj}: {str(e)}")
                cnpjs_invalidos.append(cnpj)
        
        print(f"[DEBUG] CNPJs válidos: {len(cnpjs_validos)}")
        print(f"[DEBUG] CNPJs inválidos: {len(cnpjs_invalidos)}")
        
        # Definir a lista completa (substituindo a existente)
        if cnpjs_validos:
            try:
                def _definir_lista():
                    # Buscar se existe registro
                    existing = supabase_admin.table('clientes_agentes').select('id').eq('user_id', user_id).execute()
                    
                    if existing.data and len(existing.data) > 0:
                        # Update do registro existente
                        return supabase_admin.table('clientes_agentes').update({
                            'empresa': cnpjs_validos
                        }).eq('user_id', user_id).execute()
                    else:
                        # Insert de novo registro
                        return supabase_admin.table('clientes_agentes').insert({
                            'user_id': user_id,
                            'empresa': cnpjs_validos
                        }).execute()
                
                update_response = retry_supabase_operation(_definir_lista)
                
                if hasattr(update_response, 'error') and update_response.error:
                    raise Exception(f"Erro do Supabase: {update_response.error}")
                
                print(f"[DEBUG] Lista definida com sucesso: {len(cnpjs_validos)} empresas")
                
            except Exception as e:
                print(f"[DEBUG] Erro ao definir lista: {str(e)}")
                return jsonify({
                    'success': False, 
                    'error': f'Erro ao salvar lista de empresas: {str(e)}'
                })
        
        # Preparar resultado
        resultado = {
            'sucessos': len(cnpjs_validos),
            'erros': len(cnpjs_invalidos),
            'ja_existentes': 0,  # Não aplicável neste caso pois substituímos a lista
            'detalhes': {
                'cnpjs_definidos': cnpjs_validos,
                'cnpjs_invalidos': cnpjs_invalidos
            }
        }
        
        print(f"[DEBUG] Resultado final: {resultado}")
        
        return jsonify({
            'success': True,
            'message': f'Lista definida: {len(cnpjs_validos)} empresas válidas, {len(cnpjs_invalidos)} inválidas',
            'resultado': resultado
        })
        
    except Exception as e:
        print(f"[DEBUG] Erro no endpoint de definir lista: {str(e)}")
        print("[DEBUG] Traceback completo:")
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/<user_id>/empresas/adicionar-lote', methods=['POST'])
@login_required
@role_required(['admin'])
def adicionar_empresas_lote(user_id):
    """Adicionar múltiplas empresas de uma vez para um usuário"""
    try:
        data = request.get_json()
        cnpjs = data.get('cnpjs', [])
        
        if not cnpjs:
            return jsonify({'success': False, 'error': 'Lista de CNPJs não informada'})
        
        print(f"[DEBUG] Adicionando lote de {len(cnpjs)} CNPJs para usuário {user_id}")
        
        # Verificar se usuário existe
        def _verificar_usuario():
            return supabase_admin.table('users').select('id').eq('id', user_id).execute()
        
        user_response = retry_supabase_operation(_verificar_usuario)
        if not user_response.data:
            return jsonify({'success': False, 'error': 'Usuário não encontrado'})
        
        # Buscar empresas atuais do usuário
        def _buscar_empresas_atuais():
            return supabase_admin.table('clientes_agentes').select('empresa').eq('user_id', user_id).execute()
        
        try:
            empresas_response = retry_supabase_operation(_buscar_empresas_atuais)
            empresas_atuais = []
            
            if empresas_response.data and len(empresas_response.data) > 0:
                empresas_data = empresas_response.data[0].get('empresa', [])
                if isinstance(empresas_data, str):
                    try:
                        empresas_atuais = json.loads(empresas_data)
                    except json.JSONDecodeError:
                        empresas_atuais = [empresas_data] if empresas_data else []
                elif isinstance(empresas_data, list):
                    empresas_atuais = empresas_data
        except Exception as e:
            print(f"[DEBUG] Erro ao buscar empresas atuais: {str(e)}")
            empresas_atuais = []
        
        # Verificar quais CNPJs existem na base
        cnpjs_validos = []
        cnpjs_invalidos = []
        cnpjs_ja_existentes = []
        
        for cnpj in cnpjs:
            cnpj_limpo = limpar_cnpj(cnpj)
            
            # Verificar se já está associado
            if cnpj_limpo in empresas_atuais or cnpj in empresas_atuais:
                cnpjs_ja_existentes.append(cnpj)
                continue
            
            # Verificar se empresa existe na base
            def _verificar_cnpj():
                cnpj_formatado = formatar_cnpj(cnpj_limpo)
                # Tentar primeiro com formatação
                response = supabase_admin.table('vw_aux_cnpj_importador').select('cnpj').eq('cnpj', cnpj_formatado).execute()
                if response.data:
                    return response
                # Se não encontrar, tentar sem formatação
                return supabase_admin.table('vw_aux_cnpj_importador').select('cnpj').eq('cnpj', cnpj_limpo).execute()
            
            try:
                cnpj_response = retry_supabase_operation(_verificar_cnpj)
                if cnpj_response.data:
                    cnpjs_validos.append(cnpj_limpo)
                else:
                    cnpjs_invalidos.append(cnpj)
            except Exception as e:
                print(f"[DEBUG] Erro ao verificar CNPJ {cnpj}: {str(e)}")
                cnpjs_invalidos.append(cnpj)
        
        print(f"[DEBUG] CNPJs válidos: {len(cnpjs_validos)}")
        print(f"[DEBUG] CNPJs inválidos: {len(cnpjs_invalidos)}")
        print(f"[DEBUG] CNPJs já existentes: {len(cnpjs_ja_existentes)}")
        
        # Se há CNPJs válidos para adicionar, atualizar o registro
        sucessos = 0
        if cnpjs_validos:
            try:
                # Combinar empresas atuais com as novas
                todas_empresas = list(set(empresas_atuais + cnpjs_validos))
                
                def _atualizar_empresas():
                    if empresas_response.data and len(empresas_response.data) > 0:
                        # Update do registro existente
                        return supabase_admin.table('clientes_agentes').update({
                            'empresa': todas_empresas
                        }).eq('user_id', user_id).execute()
                    else:
                        # Insert de novo registro
                        return supabase_admin.table('clientes_agentes').insert({
                            'user_id': user_id,
                            'empresa': todas_empresas
                        }).execute()
                
                update_response = retry_supabase_operation(_atualizar_empresas)
                
                if hasattr(update_response, 'error') and update_response.error:
                    raise Exception(f"Erro do Supabase: {update_response.error}")
                
                sucessos = len(cnpjs_validos)
                print(f"[DEBUG] {sucessos} empresas adicionadas com sucesso")
                
            except Exception as e:
                print(f"[DEBUG] Erro ao atualizar empresas: {str(e)}")
                return jsonify({
                    'success': False, 
                    'error': f'Erro ao salvar empresas: {str(e)}'
                })
        
        # Preparar resultado
        resultado = {
            'sucessos': sucessos,
            'erros': len(cnpjs_invalidos),
            'ja_existentes': len(cnpjs_ja_existentes),
            'detalhes': {
                'cnpjs_adicionados': cnpjs_validos,
                'cnpjs_invalidos': cnpjs_invalidos,
                'cnpjs_ja_existentes': cnpjs_ja_existentes
            }
        }
        
        print(f"[DEBUG] Resultado final: {resultado}")
        
        return jsonify({
            'success': True,
            'message': f'Lote processado: {sucessos} adicionadas, {len(cnpjs_invalidos)} inválidas, {len(cnpjs_ja_existentes)} já existentes',
            'resultado': resultado
        })
        
    except Exception as e:
        print(f"[DEBUG] Erro no endpoint de lote: {str(e)}")
        print("[DEBUG] Traceback completo:")
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/<user_id>/empresas/adicionar', methods=['POST'])
@login_required
@role_required(['admin'])
def adicionar_empresa_usuario(user_id):
    """Adicionar empresa a um usuário com tratamento robusto de erros"""
    try:
        data = request.get_json()
        cnpj_original = data.get('cnpj', '').strip()
        
        if not cnpj_original:
            return jsonify({'success': False, 'error': 'CNPJ não informado'})
        
        # Limpar CNPJ e verificar se existe
        cnpj_limpo = limpar_cnpj(cnpj_original)
        cnpj_formatado = formatar_cnpj(cnpj_limpo)
        
        print(f"[DEBUG] Adicionando empresa {cnpj_formatado} ao usuário {user_id}")
        
        # Verificar se o usuário é cliente_unique primeiro
        def _verificar_usuario():
            return supabase_admin.table('users').select('role').eq('id', user_id).execute()
        
        try:
            user_response = retry_supabase_operation(_verificar_usuario)
            if not user_response.data or user_response.data[0]['role'] != 'cliente_unique':
                return jsonify({'success': False, 'error': 'Usuário deve ser do tipo cliente_unique'})
        except Exception as e:
            print(f"[DEBUG] Erro ao verificar usuário: {str(e)}")
            return jsonify({'success': False, 'error': 'Erro ao verificar dados do usuário'})
        
        # Verificar se empresa já está associada (check rápido)
        if verificar_empresa_ja_associada(user_id, cnpj_formatado) or verificar_empresa_ja_associada(user_id, cnpj_limpo):
            return jsonify({'success': False, 'error': 'Empresa já está associada ao usuário'})
        
        # Verificar se a empresa existe na base de dados
        def _buscar_empresa():
            # Primeiro tenta com formatação
            empresa_response = supabase_admin.table('vw_aux_cnpj_importador').select('cnpj, razao_social').eq('cnpj', cnpj_formatado).execute()
            if empresa_response.data:
                return empresa_response
            # Se não encontrar, tenta sem formatação
            return supabase_admin.table('vw_aux_cnpj_importador').select('cnpj, razao_social').eq('cnpj', cnpj_limpo).execute()
        
        try:
            empresa_response = retry_supabase_operation(_buscar_empresa)
            if not empresa_response.data:
                return jsonify({'success': False, 'error': 'Empresa não encontrada no banco de dados'})
            
            empresa_encontrada = empresa_response.data[0]
            cnpj_usar = empresa_encontrada['cnpj']  # Usar o CNPJ conforme está no banco
        except Exception as e:
            print(f"[DEBUG] Erro ao buscar empresa: {str(e)}")
            return jsonify({'success': False, 'error': 'Erro ao verificar empresa na base de dados'})
        
        # Buscar empresas atuais do usuário
        def _buscar_empresas_atuais():
            return supabase_admin.table('clientes_agentes').select('empresa').eq('user_id', user_id).execute()
        
        try:
            empresas_response = retry_supabase_operation(_buscar_empresas_atuais)
            
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
            
            # Verificação final de duplicata
            if cnpj_usar in empresas:
                return jsonify({'success': False, 'error': 'Empresa já está associada ao usuário'})
            
            # Adicionar nova empresa
            empresas.append(cnpj_usar)
            
            # Atualizar no banco
            def _atualizar_empresas():
                if empresas_response.data:
                    # Atualizar registro existente
                    return supabase_admin.table('clientes_agentes').update({
                        'empresa': empresas,
                        'updated_at': datetime.datetime.now().isoformat()
                    }).eq('user_id', user_id).execute()
                else:
                    # Criar novo registro
                    return supabase_admin.table('clientes_agentes').insert({
                        'user_id': user_id,
                        'empresa': empresas,
                        'aceite_termos': True,
                        'usuario_ativo': True,
                        'created_at': datetime.datetime.now().isoformat(),
                        'updated_at': datetime.datetime.now().isoformat()
                    }).execute()
            
            retry_supabase_operation(_atualizar_empresas)
            
            return jsonify({
                'success': True, 
                'message': 'Empresa adicionada com sucesso',
                'empresa': {
                    'cnpj': cnpj_usar,
                    'razao_social': empresa_encontrada['razao_social']
                }
            })
            
        except Exception as e:
            print(f"[DEBUG] Erro ao gerenciar empresas do usuário: {str(e)}")
            return jsonify({'success': False, 'error': 'Erro ao atualizar lista de empresas'})
        
    except Exception as e:
        print(f"[DEBUG] Erro geral ao adicionar empresa: {str(e)}")
        print(f"[DEBUG] Traceback: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': 'Erro interno do servidor'})

@bp.route('/<user_id>/empresas/verificar-lote', methods=['POST'])
@login_required
@role_required(['admin'])
def verificar_empresas_lote(user_id):
    """Verificar quais empresas já estão associadas ao usuário (para seleção múltipla)"""
    try:
        data = request.get_json()
        cnpjs = data.get('cnpjs', [])
        
        if not cnpjs:
            return jsonify({'success': False, 'error': 'Lista de CNPJs não informada'})
        
        print(f"[DEBUG] Verificando {len(cnpjs)} empresas para o usuário {user_id}")
        
        # Buscar empresas atuais do usuário
        def _buscar_empresas_atuais():
            return supabase_admin.table('clientes_agentes').select('empresa').eq('user_id', user_id).execute()
        
        try:
            empresas_response = retry_supabase_operation(_buscar_empresas_atuais)
            
            empresas_existentes = []
            if empresas_response.data and empresas_response.data[0].get('empresa'):
                empresas_existentes = empresas_response.data[0]['empresa']
                if isinstance(empresas_existentes, str):
                    try:
                        empresas_existentes = json.loads(empresas_existentes)
                    except json.JSONDecodeError:
                        empresas_existentes = [empresas_existentes] if empresas_existentes else []
                elif not isinstance(empresas_existentes, list):
                    empresas_existentes = []
            
            # Verificar cada CNPJ
            resultado = {
                'novas': [],      # Empresas que podem ser adicionadas
                'existentes': []  # Empresas já associadas
            }
            
            for cnpj in cnpjs:
                cnpj_limpo = limpar_cnpj(cnpj)
                cnpj_formatado = formatar_cnpj(cnpj_limpo)
                
                # Verificar se já existe (em qualquer formato)
                ja_existe = (cnpj in empresas_existentes or 
                           cnpj_limpo in empresas_existentes or 
                           cnpj_formatado in empresas_existentes)
                
                if ja_existe:
                    resultado['existentes'].append(cnpj)
                else:
                    resultado['novas'].append(cnpj)
            
            return jsonify({
                'success': True,
                'resultado': resultado,
                'total_verificadas': len(cnpjs)
            })
            
        except Exception as e:
            print(f"[DEBUG] Erro ao verificar empresas em lote: {str(e)}")
            return jsonify({'success': False, 'error': 'Erro ao verificar empresas'})
        
    except Exception as e:
        print(f"[DEBUG] Erro geral na verificação em lote: {str(e)}")
        return jsonify({'success': False, 'error': 'Erro interno do servidor'})

@bp.route('/<user_id>/empresas/remover', methods=['POST'])
@login_required
@role_required(['admin'])
def remover_empresa_usuario(user_id):
    """Remover empresa de um usuário com tratamento robusto de erros"""
    try:
        data = request.get_json()
        cnpj = data.get('cnpj', '').strip()
        
        if not cnpj:
            return jsonify({'success': False, 'error': 'CNPJ não informado'})
        
        print(f"[DEBUG] Removendo empresa {cnpj} do usuário {user_id}")
        
        # Buscar empresas atuais
        def _buscar_empresas():
            return supabase_admin.table('clientes_agentes').select('empresa').eq('user_id', user_id).execute()
        
        try:
            empresas_response = retry_supabase_operation(_buscar_empresas)
            
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
            def _atualizar_empresas():
                return supabase_admin.table('clientes_agentes').update({
                    'empresa': empresas,
                    'updated_at': datetime.datetime.now().isoformat()
                }).eq('user_id', user_id).execute()
            
            retry_supabase_operation(_atualizar_empresas)
            
            return jsonify({'success': True, 'message': 'Empresa removida com sucesso'})
            
        except Exception as e:
            print(f"[DEBUG] Erro ao remover empresa: {str(e)}")
            return jsonify({'success': False, 'error': 'Erro ao atualizar lista de empresas'})
        
    except Exception as e:
        print(f"[DEBUG] Erro geral ao remover empresa: {str(e)}")
        return jsonify({'success': False, 'error': 'Erro interno do servidor'})

@bp.route('/<user_id>/empresas-detalhadas', methods=['GET'])
@login_required
@role_required(['admin'])
def obter_empresas_detalhadas(user_id):
    """Obter empresas associadas a um usuário com detalhes da razão social"""
    try:
        response = supabase_admin.table('clientes_agentes').select('empresa').eq('user_id', user_id).execute()
        
        empresas_detalhadas = []
        if response.data and response.data[0].get('empresa'):
            empresas = response.data[0]['empresa']
            if isinstance(empresas, str):
                try:
                    empresas = json.loads(empresas)
                except json.JSONDecodeError:
                    empresas = [empresas] if empresas else []
            elif not isinstance(empresas, list):
                empresas = []
            
            for cnpj in empresas:
                if isinstance(cnpj, str):
                    try:
                        empresa_info = supabase_admin.table('vw_aux_cnpj_importador').select('cnpj, razao_social').eq('cnpj', cnpj).execute()
                        if empresa_info.data and len(empresa_info.data) > 0:
                            empresa_data = empresa_info.data[0]
                            empresas_detalhadas.append({
                                'cnpj': empresa_data.get('cnpj'),
                                'razao_social': empresa_data.get('razao_social')
                            })
                        else:
                            empresas_detalhadas.append({'cnpj': cnpj, 'razao_social': None})
                    except Exception as empresa_error:
                        print(f"[DEBUG] Erro ao buscar dados da empresa {cnpj}: {str(empresa_error)}")
                        empresas_detalhadas.append({'cnpj': cnpj, 'razao_social': None})
        
        return jsonify({'success': True, 'empresas': empresas_detalhadas})
        
    except Exception as e:
        print(f"[DEBUG] Erro ao obter empresas detalhadas: {str(e)}")
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

@bp.route('/performance-stats')
@login_required
@role_required(['admin'])
def performance_stats():
    """Endpoint para estatísticas de performance do módulo de usuários"""
    cache_info = {
        'users_cache_active': _users_cache['data'] is not None,
        'users_cache_size': len(_users_cache['data']) if _users_cache['data'] else 0,
        'users_cache_age_seconds': time.time() - _users_cache['timestamp'],
        'users_cache_ttl_seconds': _users_cache['ttl'],
        'valid_roles': VALID_ROLES
    }
    
    return jsonify({
        'success': True,
        'cache_info': cache_info,
        'optimizations': [
            'Cache em memória implementado (TTL: 5 minutos)',
            'Busca de empresas em lotes (batch de 50)',
            'Retry reduzido para 2 tentativas com delay menor',
            'Suporte a interno_unique com regras de cliente',
            'Invalidação automática do cache após mudanças'
        ],
        'timestamp': datetime.datetime.now().isoformat()
    })

@bp.route('/clear-cache', methods=['POST'])
@login_required
@role_required(['admin'])
def clear_cache():
    """Limpar cache de usuários manualmente"""
    try:
        invalidate_users_cache()
        
        return jsonify({
            'success': True,
            'message': 'Cache de usuários limpo com sucesso'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
