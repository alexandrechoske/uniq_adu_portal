from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from extensions import supabase, supabase_admin
from routes.auth import login_required, role_required
import re
import time
import uuid
import datetime
import json
import traceback
from services.retry_utils import run_with_retries

# Blueprint com configuração para templates e static locais
bp = Blueprint('usuarios', __name__, 
               url_prefix='/usuarios',
               template_folder='templates',
               static_folder='static',
               static_url_path='/static')

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
    """Backwards-compatible wrapper that now delegates to centralized retry utility."""
    return run_with_retries(
        'usuarios.retry_op',
        operation,
        max_attempts=max_retries,
        base_delay_seconds=delay,
        should_retry=lambda e: 'server disconnected' in str(e).lower() or 'timeout' in str(e).lower() or 'connection' in str(e).lower()
    )

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
        
        # 2. Buscar todas as associações de empresas na nova estrutura
        def _buscar_todas_empresas():
            # Buscar apenas os vínculos ativos
            return supabase_admin.table('user_empresas').select('user_id, cliente_sistema_id, ativo').eq('ativo', True).execute()
        
        empresas_response = retry_supabase_operation(_buscar_todas_empresas)
        
        # 3. Buscar todas as empresas do sistema para poder fazer o mapeamento
        def _buscar_clientes_sistema():
            return supabase_admin.table('cad_clientes_sistema').select('id, nome_cliente, cnpjs, ativo').eq('ativo', True).execute()
        
        clientes_response = retry_supabase_operation(_buscar_clientes_sistema)
        
        # Criar mapa de empresa_id -> dados da empresa
        empresas_data_map = {}
        if clientes_response.data:
            for empresa in clientes_response.data:
                empresas_data_map[empresa['id']] = empresa
        
        # Criar mapa de usuário -> empresas (nova estrutura)
        user_empresas_map = {}
        
        if empresas_response.data:
            print(f"[DEBUG] {len(empresas_response.data)} vínculos de empresas encontrados")
            for vinculo in empresas_response.data:
                user_id = vinculo.get('user_id')
                cliente_sistema_id = vinculo.get('cliente_sistema_id')
                
                if not user_id or not cliente_sistema_id:
                    continue
                
                # Buscar dados da empresa no mapa
                empresa_info = empresas_data_map.get(cliente_sistema_id)
                if not empresa_info:
                    continue
                
                if user_id not in user_empresas_map:
                    user_empresas_map[user_id] = []
                
                user_empresas_map[user_id].append({
                    'id': empresa_info.get('id'),
                    'nome_cliente': empresa_info.get('nome_cliente'),
                    'cnpjs': empresa_info.get('cnpjs', []),
                    'vinculo_ativo': vinculo.get('ativo')
                })
        
        # 4. Buscar números de WhatsApp de todos os usuários
        def _buscar_whatsapp():
            return supabase_admin.table('user_whatsapp').select('*').eq('ativo', True).execute()
        
        whatsapp_response = retry_supabase_operation(_buscar_whatsapp)
        
        # Criar mapa de usuário -> whatsapp
        user_whatsapp_map = {}
        
        if whatsapp_response.data:
            print(f"[DEBUG] {len(whatsapp_response.data)} números de WhatsApp encontrados")
            for whatsapp in whatsapp_response.data:
                user_id = whatsapp.get('user_id')
                if user_id:
                    if user_id not in user_whatsapp_map:
                        user_whatsapp_map[user_id] = []
                    user_whatsapp_map[user_id].append(whatsapp)

        # 5. Montar dados finais dos usuários com nova estrutura
        for user in users:
            if not isinstance(user, dict):
                continue
            
            user_id = user.get('id')
            
            # Incluir tanto cliente_unique quanto interno_unique
            if user.get('role') in ['cliente_unique', 'interno_unique']:
                empresas_info = user_empresas_map.get(user_id, [])
                
                # Adaptar formato para compatibilidade com o frontend
                empresas_detalhadas = []
                for empresa in empresas_info:
                    # Mostrar apenas o nome da empresa na listagem (conforme solicitado)
                    empresas_detalhadas.append({
                        'nome_cliente': empresa.get('nome_cliente'),
                        'id': empresa.get('id'),
                        'cnpjs_count': len(empresa.get('cnpjs', []))  # Apenas contador
                    })
                
                user['agent_info'] = {'empresas': empresas_detalhadas}
            else:
                user['agent_info'] = {'empresas': []}
            
            # Adicionar números de WhatsApp para todos os usuários
            user['whatsapp_numbers'] = user_whatsapp_map.get(user_id, [])
        
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
    # Redirecionar para a página principal - o modal é usado para criação
    return redirect(url_for('usuarios.index'))

@bp.route('/<user_id>/editar', methods=['GET'])
@login_required
@role_required(['admin'])
def editar(user_id):
    # Redirecionar para a página principal - o modal é usado para edição
    return redirect(url_for('usuarios.index'))

@bp.route('/salvar', methods=['POST'])
@login_required
@role_required(['admin'])
def salvar_usuario():
    """Nova função simplificada para salvar usuários via JSON API"""
    try:
        # Verificar se a requisição é JSON
        if not request.is_json:
            return jsonify({'success': False, 'error': 'Content-Type deve ser application/json'}), 400
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Dados não fornecidos'}), 400
        
        # Extrair dados - apenas campos que existem na tabela users
        user_id = data.get('user_id')  # Se fornecido, é edição
        name = data.get('name', '').strip()
        email = data.get('email', '').strip()
        role = data.get('role', '').strip()
        is_active = data.get('is_active', True)
        password = data.get('password', '').strip() if not user_id else None
        confirm_password = data.get('confirm_password', '').strip() if not user_id else None
        
        # Campos extras que não vão para a tabela users (podem ser salvos separadamente depois)
        telefone = data.get('telefone', '').strip()  # Para usar depois

        # Validações básicas
        errors = []
        if not name:
            errors.append('Nome é obrigatório')
        if not email:
            errors.append('Email é obrigatório')
        if not role:
            errors.append('Perfil é obrigatório')
        
        # Validar formato do email
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if email and not re.match(email_pattern, email):
            errors.append('Formato de email inválido')

        # Validar role
        if role and role not in VALID_ROLES:
            errors.append('Perfil inválido')

        # Validações específicas para novo usuário
        if not user_id:
            if not password:
                errors.append('Senha é obrigatória')
            elif len(password) < 6:
                errors.append('Senha deve ter pelo menos 6 caracteres')
            
            if password != confirm_password:
                errors.append('Senhas não coincidem')

        if errors:
            return jsonify({'success': False, 'error': '; '.join(errors)}), 400

        # Dados que vão para a tabela users (apenas colunas existentes)
        user_data = {
            'name': name,
            'email': email,
            'role': role,
            'is_active': bool(is_active),
            'updated_at': datetime.datetime.now().isoformat()
        }

        if user_id:
            # Atualizar usuário existente
            print(f"[DEBUG] Atualizando usuário {user_id} com dados: {user_data}")
            response = supabase_admin.table('users').update(user_data).eq('id', user_id).execute()
            
            if response.data:
                print(f"[DEBUG] Usuário atualizado com sucesso")
                invalidate_users_cache()
                
                # TODO: Atualizar cargo/telefone em tabela separada se necessário
                
                return jsonify({'success': True, 'message': 'Usuário atualizado com sucesso', 'user_id': user_id})
            else:
                return jsonify({'success': False, 'error': 'Erro ao atualizar usuário'}), 500
        else:
            # Criar novo usuário
            # Verificar se email já existe primeiro (tanto na tabela users quanto no auth)
            existing_user = supabase_admin.table('users').select('id').eq('email', email).execute()
            if existing_user.data:
                return jsonify({'success': False, 'error': 'Email já está em uso por outro usuário'}), 400
            
            print(f"[DEBUG] Criando novo usuário com email: {email}")
            
            try:
                # Primeiro, criar o usuário no auth do Supabase
                print(f"[DEBUG] Criando usuário auth com dados: email={email}, name={name}, role={role}")
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
                    
                    # Verificar se já existe na tabela users (isso pode acontecer em retry)
                    existing_in_table = supabase_admin.table('users').select('id').eq('id', auth_user_id).execute()
                    if existing_in_table.data:
                        print(f"[DEBUG] Usuário já existe na tabela users, atualizando...")
                        # Atualizar dados se já existe (caso de retry)
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
                        invalidate_users_cache()
                        
                        # TODO: Salvar cargo/telefone em tabela separada se necessário
                        
                        return jsonify({'success': True, 'message': 'Usuário criado com sucesso', 'user_id': auth_user_id})
                    else:
                        print(f"[DEBUG] Erro ao inserir/atualizar usuário na tabela: {response}")
                        # Se falhar, tentar deletar o usuário auth criado
                        try:
                            print(f"[DEBUG] Tentando deletar usuário auth: {auth_user_id}")
                            supabase_admin.auth.admin.delete_user(auth_user_id)
                        except Exception as cleanup_error:
                            print(f"[DEBUG] Erro ao limpar usuário auth: {str(cleanup_error)}")
                        return jsonify({'success': False, 'error': 'Erro ao criar usuário na tabela do sistema'}), 500
                else:
                    print(f"[DEBUG] Erro ao criar usuário auth: {auth_response}")
                    return jsonify({'success': False, 'error': 'Erro ao criar usuário no sistema de autenticação'}), 500
                        
            except Exception as create_error:
                print(f"[DEBUG] Erro ao criar usuário: {str(create_error)}")
                print(f"[DEBUG] Tipo do erro: {type(create_error)}")
                
                # Tratar erros específicos do Supabase Auth
                error_message = str(create_error)
                if "A user with this email address has already been registered" in error_message:
                    return jsonify({'success': False, 'error': 'Este email já está cadastrado no sistema. Use outro email ou faça login.'}), 400
                elif "email" in error_message.lower():
                    return jsonify({'success': False, 'error': 'Erro relacionado ao email. Verifique se o formato está correto.'}), 400
                elif "password" in error_message.lower():
                    return jsonify({'success': False, 'error': 'Erro relacionado à senha. Verifique se atende aos critérios mínimos.'}), 400
                else:
                    return jsonify({'success': False, 'error': f'Erro ao criar usuário: {error_message}'}), 500
        
    except Exception as e:
        print(f"[DEBUG] Erro geral ao salvar usuário: {str(e)}")
        print("[DEBUG] Traceback completo:")
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': f'Erro interno: {str(e)}'}), 500

@bp.route('/deletar/<user_id>', methods=['POST'])
@login_required
@role_required(['admin'])
def deletar_usuario(user_id):
    """
    EXCLUSÃO EM CASCATA COMPLETA DE USUÁRIO
    Deleta em ordem:
    1. Tabelas relacionadas (user_empresas, user_whatsapp, clientes_agentes)
    2. Tabela public.users
    3. Tabela auth.users (Supabase Auth)
    """
    try:
        print(f"[DEBUG] === INICIANDO EXCLUSÃO EM CASCATA DO USUÁRIO: {user_id} ===")
        
        # Verificar se o usuário existe na tabela public.users
        user_response = supabase_admin.table('users').select('*').eq('id', user_id).execute()
        if not user_response.data:
            print(f"[DEBUG] Usuário {user_id} não encontrado na tabela public.users")
            if request.is_json:
                return jsonify({'success': False, 'error': 'Usuário não encontrado'}), 404
            else:
                flash('Usuário não encontrado', 'error')
                return redirect(url_for('usuarios.index'))
        
        user = user_response.data[0]
        user_name = user.get('name', 'Usuário Desconhecido')
        user_email = user.get('email', 'Email Desconhecido')
        
        print(f"[DEBUG] Usuário encontrado: {user_name} ({user_email})")
        
        # Verificar se não está tentando deletar o próprio usuário
        current_user = session.get('user', {})
        if current_user.get('id') == user_id:
            error_msg = 'Você não pode deletar seu próprio usuário'
            print(f"[DEBUG] {error_msg}")
            if request.is_json:
                return jsonify({'success': False, 'error': error_msg}), 400
            else:
                flash(error_msg, 'error')
                return redirect(url_for('usuarios.index'))
        
        # === ETAPA 1: DELETAR DADOS RELACIONADOS ===
        print(f"[DEBUG] Etapa 1: Deletando dados relacionados...")
        
        # 1.1. Deletar associações de empresa (nova estrutura)
        try:
            empresas_response = supabase_admin.table('user_empresas').delete().eq('user_id', user_id).execute()
            empresas_count = len(empresas_response.data) if empresas_response.data else 0
            print(f"[DEBUG] ✅ {empresas_count} associações de empresa deletadas (user_empresas)")
        except Exception as e:
            print(f"[DEBUG] ⚠️ Erro ao deletar associações de empresa (user_empresas): {str(e)}")
        
        # 1.2. Deletar números de WhatsApp
        try:
            whatsapp_response = supabase_admin.table('user_whatsapp').delete().eq('user_id', user_id).execute()
            whatsapp_count = len(whatsapp_response.data) if whatsapp_response.data else 0
            print(f"[DEBUG] ✅ {whatsapp_count} números WhatsApp deletados (user_whatsapp)")
        except Exception as e:
            print(f"[DEBUG] ⚠️ Erro ao deletar números WhatsApp (user_whatsapp): {str(e)}")
        
        # 1.3. Deletar associações legacy (clientes_agentes) se existir
        try:
            legacy_response = supabase_admin.table('clientes_agentes').delete().eq('user_id', user_id).execute()
            legacy_count = len(legacy_response.data) if legacy_response.data else 0
            if legacy_count > 0:
                print(f"[DEBUG] ✅ {legacy_count} associações legacy deletadas (clientes_agentes)")
            else:
                print(f"[DEBUG] ✅ Nenhuma associação legacy encontrada (clientes_agentes)")
        except Exception as e:
            print(f"[DEBUG] ⚠️ Erro ao deletar associações legacy (clientes_agentes): {str(e)}")
        
        # === ETAPA 2: DELETAR DA TABELA PUBLIC.USERS ===
        print(f"[DEBUG] Etapa 2: Deletando da tabela public.users...")
        
        try:
            users_response = supabase_admin.table('users').delete().eq('id', user_id).execute()
            if users_response.data or users_response.count == 0:  # Supabase pode retornar count=0 para deletes bem-sucedidos
                print(f"[DEBUG] ✅ Usuário deletado da tabela public.users")
            else:
                print(f"[DEBUG] ❌ Falha ao deletar da tabela public.users: {users_response}")
                raise Exception("Falha ao deletar usuário da tabela public.users")
        except Exception as e:
            print(f"[DEBUG] ❌ Erro crítico ao deletar da tabela public.users: {str(e)}")
            raise e
        
        # === ETAPA 3: DELETAR DO SUPABASE AUTH ===
        print(f"[DEBUG] Etapa 3: Deletando do Supabase Auth (auth.users)...")
        
        try:
            auth_response = supabase_admin.auth.admin.delete_user(user_id)
            print(f"[DEBUG] ✅ Usuário deletado do Supabase Auth (auth.users)")
            print(f"[DEBUG] Auth response: {auth_response}")
        except Exception as e:
            print(f"[DEBUG] ⚠️ Erro ao deletar do Supabase Auth (pode não existir): {str(e)}")
            # Não é crítico se falhar, pois o usuário pode não existir no auth
        
        # === ETAPA 4: LIMPEZA E FINALIZAÇÃO ===
        print(f"[DEBUG] Etapa 4: Finalizando exclusão...")
        
        # Invalidar cache após exclusão
        invalidate_users_cache()
        print(f"[DEBUG] ✅ Cache de usuários invalidado")
        
        success_message = f'Usuário {user_name} deletado com sucesso (cascata completa)'
        print(f"[DEBUG] === EXCLUSÃO EM CASCATA CONCLUÍDA COM SUCESSO ===")
        print(f"[DEBUG] Usuário: {user_name} ({user_email})")
        print(f"[DEBUG] ID: {user_id}")
        
        if request.is_json:
            return jsonify({
                'success': True, 
                'message': success_message,
                'details': {
                    'user_id': user_id,
                    'user_name': user_name,
                    'user_email': user_email,
                    'cascade_complete': True
                }
            })
        else:
            flash(success_message, 'success')
            return redirect(url_for('usuarios.index'))
        
    except Exception as e:
        print(f"[DEBUG] ❌ ERRO CRÍTICO NA EXCLUSÃO EM CASCATA: {str(e)}")
        print(f"[DEBUG] Traceback completo:")
        print(traceback.format_exc())
        
        error_msg = f'Erro na exclusão em cascata do usuário: {str(e)}'
        
        if request.is_json:
            return jsonify({
                'success': False, 
                'error': error_msg,
                'details': {
                    'user_id': user_id,
                    'cascade_failed': True
                }
            }), 500
        else:
            flash(error_msg, 'error')
            return redirect(url_for('usuarios.index'))

@bp.route('/api/empresas')
@login_required
@role_required(['admin'])
def api_empresas():
    """API para buscar empresas disponíveis com IDs"""
    try:
        # Usar tabela cad_clientes_sistema ao invés da view para ter IDs
        empresas_response = supabase_admin.table('cad_clientes_sistema').select('id, cnpjs, nome_cliente, ativo').eq('ativo', True).order('nome_cliente').execute()
        
        if empresas_response.data:
            empresas = [
                {
                    'id': empresa['id'],
                    'cnpj': empresa['cnpjs'],  # cnpjs é o nome real da coluna
                    'nome_cliente': empresa['nome_cliente'],
                    'razao_social': empresa['nome_cliente']  # Para compatibilidade
                }
                for empresa in empresas_response.data
            ]
            return jsonify({'success': True, 'empresas': empresas})
        else:
            return jsonify({'success': False, 'error': 'Nenhuma empresa encontrada'})
            
    except Exception as e:
        print(f"[DEBUG] Erro ao buscar empresas: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/api/usuarios')
@login_required
@role_required(['admin'])
def api_usuarios():
    """API para retornar todos os usuários"""
    try:
        users = get_cached_users()
        
        # Simplificar estrutura para API (incluindo role e outros campos necessários)
        usuarios_api = []
        for user in users:
            usuarios_api.append({
                'id': user.get('id'),
                'nome': user.get('nome') or user.get('name'),  # Tentar nome e name
                'email': user.get('email'),
                'role': user.get('role'),  # CAMPO CRÍTICO PARA KPIs
                'ativo': user.get('ativo', True),
                'agent_info': user.get('agent_info', {'empresas': []}),
                'whatsapp_numbers': user.get('whatsapp_numbers', [])
            })
        
        return jsonify(usuarios_api)
        
    except Exception as e:
        print(f"[DEBUG] Erro na API de usuários: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/<user_id>/empresas', methods=['POST'])
@login_required
@role_required(['admin'])
def associar_empresas(user_id):
    """Associar empresas a um usuário cliente - MIGRADO PARA NOVA ESTRUTURA"""
    try:
        empresas_data = request.json.get('empresas', [])
        
        # Verificar se o usuário existe e é válido
        user_response = supabase_admin.table('users').select('role').eq('id', user_id).execute()
        if not user_response.data:
            return jsonify({'success': False, 'error': 'Usuário não encontrado'})
        
        user_role = user_response.data[0]['role']
        if user_role not in ['cliente_unique', 'interno_unique']:
            return jsonify({'success': False, 'error': 'Usuário deve ser do tipo cliente_unique ou interno_unique'})
        
        # Limpar associações existentes da nova estrutura
        supabase_admin.from_('user_empresas').delete().eq('user_id', user_id).execute()
        
        # Processar empresas recebidas
        vinculos_criados = 0
        erros = []
        
        for empresa_info in empresas_data:
            try:
                # Se recebemos um ID, usar diretamente
                if isinstance(empresa_info, dict) and 'id' in empresa_info:
                    cliente_sistema_id = empresa_info['id']
                elif isinstance(empresa_info, int):
                    cliente_sistema_id = empresa_info
                elif isinstance(empresa_info, str):
                    # Se é string, pode ser CNPJ - precisamos converter para ID
                    cnpj = empresa_info.strip()
                    empresa_response = supabase_admin.table('cad_clientes_sistema').select('id').eq('cnpjs', cnpj).eq('ativo', True).execute()
                    
                    if not empresa_response.data:
                        erros.append(f"Empresa não encontrada para CNPJ: {cnpj}")
                        continue
                    
                    cliente_sistema_id = empresa_response.data[0]['id']
                else:
                    erros.append(f"Formato de empresa inválido: {empresa_info}")
                    continue
                
                # Criar vínculo na nova estrutura
                supabase_admin.from_('user_empresas').insert({
                    'user_id': user_id,
                    'cliente_sistema_id': cliente_sistema_id,
                    'ativo': True,
                    'observacoes': 'Migrado do sistema anterior'
                }).execute()
                
                vinculos_criados += 1
                
            except Exception as e:
                erros.append(f"Erro ao processar empresa {empresa_info}: {str(e)}")
        
        # Manter compatibilidade com sistema antigo (tabela clientes_agentes)
        # Isso será removido futuramente
        try:
            existing_response = supabase_admin.table('clientes_agentes').select('id').eq('user_id', user_id).execute()
            
            if empresas_data:  # Se há empresas para associar
                # Extrair apenas CNPJs para o sistema antigo
                cnpjs_compatibilidade = []
                for empresa_info in empresas_data:
                    if isinstance(empresa_info, dict) and 'cnpj' in empresa_info:
                        cnpjs_compatibilidade.append(empresa_info['cnpj'])
                    elif isinstance(empresa_info, str):
                        cnpjs_compatibilidade.append(empresa_info)
                
                if cnpjs_compatibilidade:
                    association_data = {
                        'user_id': user_id,
                        'empresa': cnpjs_compatibilidade,
                        'updated_at': datetime.datetime.now().isoformat()
                    }
                    
                    if existing_response.data:
                        supabase_admin.table('clientes_agentes').update(association_data).eq('user_id', user_id).execute()
                    else:
                        association_data['id'] = str(uuid.uuid4())
                        association_data['created_at'] = datetime.datetime.now().isoformat()
                        supabase_admin.table('clientes_agentes').insert(association_data).execute()
            else:  # Array vazio = limpar também do sistema antigo
                if existing_response.data:
                    supabase_admin.table('clientes_agentes').delete().eq('user_id', user_id).execute()
        except Exception as e:
            print(f"[DEBUG] Erro na compatibilidade com sistema antigo: {e}")
        
        # Invalidar cache
        invalidate_users_cache()
        
        # Resposta
        if empresas_data:  # Se havia empresas para associar
            if vinculos_criados > 0:
                message = f"{vinculos_criados} empresas associadas com sucesso!"
                if erros:
                    message += f" ({len(erros)} erros encontrados)"
                
                return jsonify({
                    'success': True, 
                    'message': message,
                    'vinculos_criados': vinculos_criados,
                    'erros': erros
                })
            else:
                return jsonify({
                    'success': False, 
                    'error': 'Nenhuma empresa foi associada',
                    'erros': erros
                })
        else:  # Array vazio = remover todas as empresas
            return jsonify({
                'success': True, 
                'message': 'Todas as empresas foram removidas com sucesso!',
                'vinculos_criados': 0,
                'erros': []
            })
            
    except Exception as e:
        print(f"[DEBUG] Erro ao associar empresas: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/<user_id>/empresas', methods=['GET'])
@login_required
@role_required(['admin'])
def obter_empresas_usuario(user_id):
    """Obter empresas associadas a um usuário - NOVA ESTRUTURA"""
    try:
        # Buscar da nova estrutura relacional primeiro
        result = supabase_admin.from_('user_empresas').select('cliente_sistema_id, observacoes, cad_clientes_sistema(id, cnpjs, nome_cliente)').eq('user_id', user_id).eq('ativo', True).execute()
        
        if result.data:
            # Temos dados na nova estrutura
            empresas = []
            for item in result.data:
                empresa_info = item.get('cad_clientes_sistema', {})
                empresas.append({
                    'id': empresa_info.get('id'),
                    'cnpj': empresa_info.get('cnpjs'),  # cnpjs é o nome real da coluna
                    'nome_cliente': empresa_info.get('nome_cliente'),
                    'razao_social': empresa_info.get('nome_cliente'),  # Para compatibilidade
                    'observacoes': item.get('observacoes', '')
                })
            
            return jsonify({'success': True, 'empresas': empresas, 'source': 'nova_estrutura'})
        
        # Fallback: buscar da estrutura antiga se não encontrar na nova
        response = supabase_admin.table('clientes_agentes').select('empresa').eq('user_id', user_id).execute()
        
        if response.data and response.data[0].get('empresa'):
            empresas_antigas = response.data[0]['empresa']
            if isinstance(empresas_antigas, str):
                try:
                    empresas_antigas = json.loads(empresas_antigas)
                except json.JSONDecodeError:
                    empresas_antigas = [empresas_antigas] if empresas_antigas else []
            elif not isinstance(empresas_antigas, list):
                empresas_antigas = []
            
            # Converter CNPJs para estrutura com IDs
            empresas = []
            for cnpj in empresas_antigas:
                if isinstance(cnpj, str):
                    # Buscar ID da empresa pelo CNPJ
                    empresa_response = supabase_admin.table('cad_clientes_sistema').select('id, cnpjs, nome_cliente').eq('cnpjs', cnpj).eq('ativo', True).execute()
                    
                    if empresa_response.data:
                        empresa = empresa_response.data[0]
                        empresas.append({
                            'id': empresa['id'],
                            'cnpj': empresa['cnpjs'],
                            'nome_cliente': empresa['nome_cliente'],
                            'razao_social': empresa['nome_cliente'],
                            'observacoes': 'Migrado do sistema anterior'
                        })
                    else:
                        # Empresa não encontrada na nova estrutura
                        empresas.append({
                            'id': None,
                            'cnpj': cnpj,
                            'nome_cliente': f"Empresa não encontrada ({cnpj})",
                            'razao_social': f"Empresa não encontrada ({cnpj})",
                            'observacoes': 'ERRO: Empresa não encontrada na nova estrutura'
                        })
            
            return jsonify({'success': True, 'empresas': empresas, 'source': 'estrutura_antiga'})
        else:
            return jsonify({'success': True, 'empresas': [], 'source': 'nenhuma'})
            
    except Exception as e:
        print(f"[DEBUG] Erro ao obter empresas do usuário: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

def limpar_cnpj(cnpj):
    """Remove formatação do CNPJ deixando apenas números"""
    if not cnpj:
        return ""
    # Garantir que é string
    cnpj_str = str(cnpj)
    return re.sub(r'[^0-9]', '', cnpj_str)

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
            
            # Buscar primeiro com formatação na tabela cad_clientes_sistema
            empresa_response = supabase_admin.table('cad_clientes_sistema').select('id, cnpjs, nome_cliente').eq('cnpjs', cnpj_formatado).eq('ativo', True).execute()
            
            # Se não encontrar, tenta sem formatação
            if not empresa_response.data:
                empresa_response = supabase_admin.table('cad_clientes_sistema').select('id, cnpjs, nome_cliente').eq('cnpjs', cnpj_limpo).eq('ativo', True).execute()
                
        else:
            # Busca por razão social (usando ilike para busca parcial case-insensitive)
            print(f"[DEBUG] Buscando por razão social: {termo_busca}")
            empresa_response = supabase_admin.table('cad_clientes_sistema').select('id, cnpjs, nome_cliente').ilike('nome_cliente', f'%{termo_busca}%').eq('ativo', True).limit(10).execute()
        
        if empresa_response.data and len(empresa_response.data) > 0:
            if len(empresa_response.data) == 1:
                # Uma empresa encontrada
                empresa = empresa_response.data[0]
                return jsonify({
                    'success': True,
                    'empresa': {
                        'id': empresa['id'],
                        'cnpj': empresa['cnpjs'],  # cnpjs é o nome real da coluna
                        'nome_cliente': empresa['nome_cliente'],
                        'razao_social': empresa['nome_cliente']  # Para compatibilidade
                    }
                })
            else:
                # Múltiplas empresas encontradas
                empresas = []
                for emp in empresa_response.data:
                    empresas.append({
                        'id': emp['id'],
                        'cnpj': emp['cnpjs'],  # cnpjs é o nome real da coluna
                        'nome_cliente': emp['nome_cliente'],
                        'razao_social': emp['nome_cliente']  # Para compatibilidade
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
            # Garantir que cnpj é uma string
            if isinstance(cnpj, list):
                # Se for lista, pegar primeiro elemento
                cnpj_str = str(cnpj[0]) if cnpj else ""
            else:
                cnpj_str = str(cnpj)
            
            cnpj_limpo = limpar_cnpj(cnpj_str)
            
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
            return jsonify({'success': False, 'error': 'Usuário não encontrado'}), 404
        
        user = user_response.data[0]
        print(f"[DEBUG] Dados do usuário encontrados: {user}")
        
        # Se for cliente_unique ou interno_unique, buscar empresas associadas e detalhar com razão social
        if user.get('role') in ['cliente_unique', 'interno_unique']:
            print(f"[DEBUG] Usuário {user_id} tem role {user.get('role')}, buscando empresas associadas")
            
            try:
                # Usar a mesma lógica que funciona no endpoint /empresas
                result = supabase_admin.from_('user_empresas').select('cliente_sistema_id, observacoes, cad_clientes_sistema(id, cnpjs, nome_cliente)').eq('user_id', user_id).eq('ativo', True).execute()
                
                empresas_detalhadas = []
                if result.data:
                    print(f"[DEBUG] Empresas encontradas na nova estrutura: {len(result.data)}")
                    for item in result.data:
                        empresa_info = item.get('cad_clientes_sistema', {})
                        if empresa_info:
                            empresas_detalhadas.append({
                                'id': empresa_info.get('id'),
                                'nome_cliente': empresa_info.get('nome_cliente'),
                                'cnpjs': empresa_info.get('cnpjs', []),
                                'observacoes': item.get('observacoes', '')
                            })
                            print(f"[DEBUG] Empresa detalhada: {empresa_info.get('nome_cliente')} (CNPJs: {len(empresa_info.get('cnpjs', []))})")
                
                user['empresas'] = empresas_detalhadas
                print(f"[DEBUG] Total de empresas detalhadas: {len(empresas_detalhadas)}")
                
            except Exception as e:
                print(f"[DEBUG] Erro ao buscar empresas: {str(e)}")
                import traceback
                print(f"[DEBUG] Traceback: {traceback.format_exc()}")
                user['empresas'] = []
        else:
            user['empresas'] = []
            print(f"[DEBUG] Usuário com role {user.get('role')} não tem empresas associadas")
        
        return jsonify({'success': True, 'data': user})
        
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

# ====================================================
# NOVAS ROTAS PARA RELACIONAMENTOS E WHATSAPP
# ====================================================

@bp.route('/api/usuarios-empresas')
@login_required
@role_required(['admin'])
def api_usuarios_empresas():
    """API para listar usuários com suas empresas vinculadas"""
    try:
        # Buscar dados da view v_usuarios_empresas
        result = supabase_admin.from_('v_usuarios_empresas').select('*').order('user_email').execute()
        
        return jsonify({
            'success': True,
            'data': result.data or []
        })
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar usuários-empresas: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/<user_id>/vincular-empresa', methods=['POST'])
@login_required
@role_required(['admin'])
def vincular_empresa(user_id):
    """Vincula uma empresa a um usuário"""
    try:
        data = request.get_json()
        cliente_sistema_id = data.get('cliente_sistema_id')
        observacoes = data.get('observacoes', '')
        
        if not cliente_sistema_id:
            return jsonify({
                'success': False,
                'error': 'ID da empresa é obrigatório'
            }), 400
        
        # Verificar se vínculo já existe
        existing = supabase_admin.from_('user_empresas').select('id').eq('user_id', user_id).eq('cliente_sistema_id', cliente_sistema_id).execute()
        
        if existing.data:
            return jsonify({
                'success': False,
                'error': 'Usuário já está vinculado a esta empresa'
            }), 400
        
        # Criar vínculo
        result = supabase_admin.from_('user_empresas').insert({
            'user_id': user_id,
            'cliente_sistema_id': cliente_sistema_id,
            'observacoes': observacoes,
            'ativo': True
        }).execute()
        
        invalidate_users_cache()
        
        return jsonify({
            'success': True,
            'message': 'Empresa vinculada com sucesso',
            'data': result.data[0] if result.data else None
        })
        
    except Exception as e:
        current_app.logger.error(f"Erro ao vincular empresa: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/<user_id>/desvincular-empresa', methods=['POST'])
@login_required
@role_required(['admin'])
def desvincular_empresa(user_id):
    """Desvincula uma empresa de um usuário"""
    try:
        data = request.get_json()
        cliente_sistema_id = data.get('cliente_sistema_id')
        
        if not cliente_sistema_id:
            return jsonify({
                'success': False,
                'error': 'ID da empresa é obrigatório'
            }), 400
        
        # Remover vínculo
        result = supabase_admin.from_('user_empresas').delete().eq('user_id', user_id).eq('cliente_sistema_id', cliente_sistema_id).execute()
        
        invalidate_users_cache()
        
        return jsonify({
            'success': True,
            'message': 'Empresa desvinculada com sucesso'
        })
        
    except Exception as e:
        current_app.logger.error(f"Erro ao desvincular empresa: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/<user_id>/empresas-vinculadas')
@login_required
@role_required(['admin'])
def empresas_vinculadas(user_id):
    """Lista empresas vinculadas a um usuário"""
    try:
        result = supabase_admin.from_('v_usuarios_empresas').select('*').eq('user_id', user_id).execute()
        
        return jsonify({
            'success': True,
            'data': result.data or []
        })
        
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar empresas vinculadas: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ====================================================
# ROTAS PARA WHATSAPP
# ====================================================

@bp.route('/<user_id>/whatsapp', methods=['GET'])
@login_required
@role_required(['admin'])
def listar_whatsapp(user_id):
    """Lista números WhatsApp de um usuário - DEPRECATED: use /api/user/<user_id>/whatsapp"""
    try:
        print(f"[DEBUG] [DEPRECATED] Endpoint /<user_id>/whatsapp chamado. Use /api/user/<user_id>/whatsapp")
        
        # Buscar apenas da tabela user_whatsapp sem JOIN
        result = supabase_admin.from_('user_whatsapp').select('*').eq('user_id', user_id).eq('ativo', True).order('principal', desc=True).execute()
        
        whatsapp_list = result.data or []
        
        # Retornar no formato esperado pelo frontend antigo
        return jsonify({
            'success': True,
            'data': whatsapp_list,
            'whatsapp': whatsapp_list  # Compatibilidade
        })
        
    except Exception as e:
        print(f"[DEBUG] Erro ao buscar WhatsApp (endpoint deprecated): {e}")
        current_app.logger.error(f"Erro ao buscar WhatsApp: {e}")
        
        # Fallback para telefone do usuário
        try:
            user_result = supabase_admin.from_('users').select('telefone').eq('id', user_id).execute()
            
            if user_result.data and user_result.data[0].get('telefone'):
                telefone = user_result.data[0]['telefone']
                fallback_data = [{
                    'id': 'fallback_1',
                    'numero': telefone,
                    'nome': 'WhatsApp Principal',
                    'tipo': 'pessoal',
                    'principal': True,
                    'ativo': True,
                    'source': 'fallback'
                }]
                
                return jsonify({
                    'success': True,
                    'data': fallback_data,
                    'whatsapp': fallback_data,
                    'fallback_used': True
                })
        except:
            pass
        
        return jsonify({
            'success': False,
            'error': str(e),
            'data': [],
            'whatsapp': []
        }), 500

@bp.route('/<user_id>/whatsapp', methods=['POST'])
@login_required
@role_required(['admin'])
def adicionar_whatsapp(user_id):
    """Adiciona número WhatsApp a um usuário"""
    try:
        data = request.get_json()
        
        numero_whatsapp = data.get('numero', '').strip()
        nome_contato = data.get('nome', '').strip()
        tipo_numero = data.get('tipo', 'pessoal')
        cliente_sistema_id = data.get('user_Id')
        principal = data.get('principal', False)
        observacoes = data.get('observacoes', '')
        
        # Validações
        if not numero_whatsapp or not nome_contato:
            return jsonify({
                'success': False,
                'error': 'Número e nome do contato são obrigatórios'
            }), 400
        
        # Validar formato do número (internacional)
        if not re.match(r'^\+[1-9]\d{1,14}$', numero_whatsapp):
            return jsonify({
                'success': False,
                'error': 'Formato do número inválido. Use formato internacional (+5511999999999)'
            }), 400
        
        # Verificar se número já existe para este usuário
        existing = supabase_admin.from_('user_whatsapp').select('id').eq('user_id', user_id).eq('numero_whatsapp', numero_whatsapp).execute()
        
        if existing.data:
            return jsonify({
                'success': False,
                'error': 'Este número já está cadastrado para o usuário'
            }), 400
        
        # Se definir como principal, remover principal dos outros
        if principal:
            supabase_admin.from_('user_whatsapp').update({'principal': False}).eq('user_id', user_id).execute()
        
        # Inserir novo WhatsApp
        whatsapp_data = {
            'user_id': user_id,
            'numero_whatsapp': numero_whatsapp,
            'nome_contato': nome_contato,
            'tipo_numero': tipo_numero,
            'principal': principal,
            'ativo': True,
            'observacoes': observacoes
        }
        
        if cliente_sistema_id:
            whatsapp_data['cliente_sistema_id'] = cliente_sistema_id
        
        result = supabase_admin.from_('user_whatsapp').insert(whatsapp_data).execute()
        
        return jsonify({
            'success': True,
            'message': 'WhatsApp adicionado com sucesso',
            'data': result.data[0] if result.data else None
        })
        
    except Exception as e:
        current_app.logger.error(f"Erro ao adicionar WhatsApp: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/whatsapp/<int:whatsapp_id>', methods=['DELETE'])
@login_required
@role_required(['admin'])
def remover_whatsapp(whatsapp_id):
    """Remove número WhatsApp"""
    try:
        result = supabase_admin.from_('user_whatsapp').delete().eq('id', whatsapp_id).execute()
        
        return jsonify({
            'success': True,
            'message': 'WhatsApp removido com sucesso'
        })
        
    except Exception as e:
        current_app.logger.error(f"Erro ao remover WhatsApp: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/whatsapp/<int:whatsapp_id>/principal', methods=['POST'])
@login_required
@role_required(['admin'])
def definir_whatsapp_principal(whatsapp_id):
    """Define WhatsApp como principal"""
    try:
        # Buscar WhatsApp para saber qual usuário
        whatsapp = supabase_admin.from_('user_whatsapp').select('user_id').eq('id', whatsapp_id).single().execute()
        
        if not whatsapp.data:
            return jsonify({
                'success': False,
                'error': 'WhatsApp não encontrado'
            }), 404
        
        user_id = whatsapp.data['user_id']
        
        # Remover principal dos outros
        supabase_admin.from_('user_whatsapp').update({'principal': False}).eq('user_id', user_id).execute()
        
        # Definir este como principal
        supabase_admin.from_('user_whatsapp').update({'principal': True}).eq('id', whatsapp_id).execute()
        
        return jsonify({
            'success': True,
            'message': 'WhatsApp definido como principal'
        })
        
    except Exception as e:
        current_app.logger.error(f"Erro ao definir WhatsApp principal: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ====================================================
# FUNÇÕES AUXILIARES PARA NOVA ESTRUTURA
# ====================================================

def get_user_companies_new(user_id):
    """Busca empresas vinculadas ao usuário na nova estrutura"""
    try:
        result = supabase_admin.rpc('get_user_cnpjs', {'user_id_param': user_id}).execute()
        return result.data or []
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar CNPJs do usuário: {e}")
        return []

def get_user_whatsapp_numbers(user_id):
    """Busca números WhatsApp do usuário"""
    try:
        result = supabase_admin.from_('user_whatsapp').select('*').eq('user_id', user_id).eq('ativo', True).execute()
        return result.data or []
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar WhatsApp do usuário: {e}")
        return []

# =====================
# NOVAS ROTAS UNIFICADAS
# =====================

@bp.route('/api/user/<user_id>')
@login_required
@role_required(['admin'])
def api_get_user(user_id):
    """API para buscar dados de um usuário específico"""
    try:
        result = supabase_admin.from_('users').select('*').eq('id', user_id).execute()
        
        if not result.data:
            return jsonify({'success': False, 'message': 'Usuário não encontrado'}), 404
            
        user = result.data[0]
        return jsonify({'success': True, 'user': user})
        
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar usuário {user_id}: {e}")
        return jsonify({'success': False, 'message': 'Erro interno do servidor'}), 500

@bp.route('/api/user/<user_id>/empresas')
@login_required
@role_required(['admin'])
def api_get_user_empresas(user_id):
    """API para buscar empresas de um usuário com retry e melhor tratamento de erro"""
    try:
        print(f"[DEBUG] Buscando empresas para usuário: {user_id}")
        
        # Usar função retry_supabase_operation para conexões mais robustas
        def buscar_empresas():
            result = supabase_admin.from_('user_empresas').select('''
                cliente_sistema_id,
                cad_clientes_sistema(
                    id,
                    nome_cliente,
                    cnpj
                )
            ''').eq('user_id', user_id).eq('ativo', True).execute()
            return result
        
        result = retry_supabase_operation(buscar_empresas, max_retries=3, delay=1.0)
        
        empresas = []
        for item in result.data or []:
            if item.get('cad_clientes_sistema'):
                empresas.append({
                    'id': item['cliente_sistema_id'],
                    'nome_cliente': item['cad_clientes_sistema']['nome_cliente'],
                    'cnpj': item['cad_clientes_sistema']['cnpj']
                })
        
        print(f"[DEBUG] Encontradas {len(empresas)} empresas para usuário {user_id}")
        return jsonify({'success': True, 'empresas': empresas})
        
    except Exception as e:
        error_msg = str(e)
        print(f"[DEBUG] Erro ao buscar empresas do usuário {user_id}: {error_msg}")
        current_app.logger.error(f"Erro ao buscar empresas do usuário {user_id}: {e}")
        
        # Retornar erro mais específico
        if "Server disconnected" in error_msg or "Connection" in error_msg:
            return jsonify({'success': False, 'message': 'Erro de conexão com banco de dados', 'retry': True}), 503
        else:
            return jsonify({'success': False, 'message': 'Erro interno do servidor'}), 500

@bp.route('/api/user/<user_id>/whatsapp')
@login_required
@role_required(['admin'])
def api_get_user_whatsapp(user_id):
    """API para buscar WhatsApp de um usuário com fallback para campo telefone"""
    try:
        print(f"[DEBUG] Buscando WhatsApp para usuário: {user_id}")
        
        # Tentar buscar na tabela user_whatsapp primeiro
        try:
            def buscar_whatsapp():
                result = supabase_admin.from_('user_whatsapp').select('*').eq('user_id', user_id).eq('ativo', True).execute()
                return result
            
            result = retry_supabase_operation(buscar_whatsapp, max_retries=3, delay=1.0)
            whatsapp_list = result.data or []
            
            if whatsapp_list:
                print(f"[DEBUG] Encontrados {len(whatsapp_list)} números WhatsApp na tabela dedicada")
                return jsonify({'success': True, 'whatsapp': whatsapp_list})
                
        except Exception as table_error:
            print(f"[DEBUG] Tabela user_whatsapp não disponível: {table_error}")
        
        # Fallback: buscar no campo telefone do usuário
        try:
            print(f"[DEBUG] Usando fallback: buscando telefone do usuário")
            user_result = supabase_admin.from_('users').select('telefone').eq('id', user_id).execute()
            
            if user_result.data and user_result.data[0].get('telefone'):
                telefone = user_result.data[0]['telefone']
                print(f"[DEBUG] Telefone encontrado: {telefone}")
                
                # Converter para formato de lista como esperado pelo frontend
                whatsapp_fallback = [{
                    'id': 'fallback_1',
                    'numero': telefone,
                    'nome': 'WhatsApp Principal',
                    'tipo': 'pessoal',
                    'principal': True,
                    'ativo': True,
                    'source': 'fallback'
                }]
                
                return jsonify({
                    'success': True, 
                    'whatsapp': whatsapp_fallback,
                    'fallback_used': True,
                    'note': 'Dados vindos do campo telefone. Crie a tabela user_whatsapp para funcionalidade completa.'
                })
            else:
                print(f"[DEBUG] Nenhum telefone encontrado para o usuário")
                
        except Exception as fallback_error:
            print(f"[DEBUG] Erro no fallback: {fallback_error}")
        
        # Se nada foi encontrado, retornar lista vazia
        print(f"[DEBUG] Nenhum WhatsApp encontrado para usuário {user_id}")
        return jsonify({'success': True, 'whatsapp': []})
        
    except Exception as e:
        error_msg = str(e)
        print(f"[DEBUG] Erro geral ao buscar WhatsApp: {error_msg}")
        current_app.logger.error(f"Erro ao buscar WhatsApp do usuário {user_id}: {e}")
        return jsonify({'success': False, 'message': 'Erro interno do servidor'}), 500

@bp.route('/api/empresas')
@login_required
@role_required(['admin'])
def api_get_empresas():
    """API para buscar todas as empresas disponíveis"""
    try:
        result = supabase_admin.from_('cad_clientes_sistema').select('id, nome_cliente, cnpj').eq('ativo', True).order('nome_cliente').execute()
        
        empresas = result.data or []
        return jsonify({'success': True, 'empresas': empresas})
        
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar empresas: {e}")
        return jsonify({'success': False, 'message': 'Erro interno do servidor'}), 500

@bp.route('/api/user/<user_id>', methods=['PUT'])
@login_required
@role_required(['admin'])
def api_update_user(user_id):
    """API para atualizar informações do usuário"""
    try:
        data = request.get_json()
        
        # Validar dados obrigatórios
        if not data.get('name') or not data.get('email'):
            return jsonify({'success': False, 'message': 'Nome e email são obrigatórios'}), 400
        
        # Preparar dados para atualização - apenas campos que existem na tabela users
        update_data = {
            'name': data.get('name'),
            'email': data.get('email'),
            'role': data.get('role'),
            'is_active': data.get('is_active'),
            'updated_at': datetime.datetime.now().isoformat()
        }
        
        # Adicionar telefone apenas se fornecido (campo pode não existir)
        if data.get('telefone'):
            update_data['telefone'] = data.get('telefone')
        
        # Atualizar usuário
        result = supabase_admin.from_('users').update(update_data).eq('id', user_id).execute()
        
        if not result.data:
            return jsonify({'success': False, 'message': 'Erro ao atualizar usuário'}), 400
        
        # Invalidar cache
        invalidate_users_cache()
        
        return jsonify({'success': True, 'message': 'Usuário atualizado com sucesso'})
        
    except Exception as e:
        current_app.logger.error(f"Erro ao atualizar usuário {user_id}: {e}")
        return jsonify({'success': False, 'message': 'Erro interno do servidor'}), 500

@bp.route('/api/user/<user_id>/empresas', methods=['POST'])
@login_required
@role_required(['admin'])
def api_update_user_empresas(user_id):
    """API para atualizar empresas do usuário"""
    try:
        data = request.get_json()
        empresa_ids = data.get('empresa_ids', [])
        
        print(f"[DEBUG] Atualizando empresas para usuário {user_id}: {empresa_ids}")
        
        # Primeiro, desativar todas as empresas existentes do usuário
        result = supabase_admin.from_('user_empresas').update({'ativo': False}).eq('user_id', user_id).execute()
        print(f"[DEBUG] Desativação de empresas existentes: {result}")
        
        # Inserir/ativar empresas selecionadas
        for empresa_id in empresa_ids:
            if empresa_id:
                # Verificar se já existe associação
                existing = supabase_admin.from_('user_empresas').select('id').eq('user_id', user_id).eq('cliente_sistema_id', empresa_id).execute()
                
                if existing.data:
                    # Reativar existente
                    reactivate_result = supabase_admin.from_('user_empresas').update({
                        'ativo': True,
                        'updated_at': datetime.datetime.now().isoformat()
                    }).eq('user_id', user_id).eq('cliente_sistema_id', empresa_id).execute()
                    print(f"[DEBUG] Reativando empresa {empresa_id}: {reactivate_result}")
                else:
                    # Criar nova associação
                    create_result = supabase_admin.from_('user_empresas').insert({
                        'user_id': user_id,
                        'cliente_sistema_id': empresa_id,
                        'ativo': True,
                        'created_at': datetime.datetime.now().isoformat()
                    }).execute()
                    print(f"[DEBUG] Criando associação empresa {empresa_id}: {create_result}")
        
        return jsonify({'success': True, 'message': 'Empresas atualizadas com sucesso'})
        
    except Exception as e:
        print(f"[DEBUG] Erro ao atualizar empresas: {e}")
        current_app.logger.error(f"Erro ao atualizar empresas do usuário {user_id}: {e}")
        return jsonify({'success': False, 'message': 'Erro interno do servidor'}), 500

@bp.route('/api/user/<user_id>/whatsapp', methods=['POST'])
@login_required
@role_required(['admin'])
def api_update_user_whatsapp(user_id):
    """API para atualizar WhatsApp do usuário"""
    try:
        import re
        
        def validar_whatsapp_backend(numero):
            """Valida formato do WhatsApp no backend"""
            if not numero:
                return False, "Número não fornecido"
            
            # Remover formatação
            numero_limpo = re.sub(r'[\(\)\s\-]', '', numero)
            
            # Verificar se tem exatamente 11 dígitos
            if not re.match(r'^\d{11}$', numero_limpo):
                return False, "Número deve ter 11 dígitos no formato (dd)xxxxxxxxx"
            
            # Verificar DDD válido (11-99)
            ddd = int(numero_limpo[:2])
            if ddd < 11 or ddd > 99:
                return False, f"DDD {ddd} inválido. Use DDDs entre 11 e 99"
            
            # Verificar se terceiro dígito é 9 (celular)
            if numero_limpo[2] != '9':
                return False, "Terceiro dígito deve ser 9 (número de celular)"
            
            return True, numero_limpo
        
        data = request.get_json()
        whatsapp_list = data.get('whatsapp', [])
        
        print(f"[DEBUG] Dados recebidos para WhatsApp: {data}")
        print(f"[DEBUG] Lista de WhatsApp extraída: {whatsapp_list}")
        print(f"[DEBUG] Atualizando WhatsApp para usuário {user_id}: {whatsapp_list}")
        
        # Validar todos os números antes de processar
        numeros_validados = []
        for whatsapp in whatsapp_list:
            numero = whatsapp.get('numero')
            if numero:
                valido, resultado = validar_whatsapp_backend(numero)
                if not valido:
                    return jsonify({
                        'success': False, 
                        'message': f'WhatsApp inválido ({numero}): {resultado}'
                    }), 400
                
                numeros_validados.append({
                    'numero': resultado,  # número limpo
                    'descricao': whatsapp.get('nome', ''),  # usar descricao em vez de nome
                    'tipo': whatsapp.get('tipo', 'pessoal'),
                    'principal': whatsapp.get('principal', False)
                })
        
        # Primeiro, desativar todos os WhatsApp existentes (se a tabela existir)
        try:
            deactivate_result = supabase_admin.table('user_whatsapp')\
                .update({'ativo': False})\
                .eq('user_id', user_id)\
                .execute()
            print(f"[DEBUG] WhatsApp existentes desativados: {deactivate_result.data}")
        except Exception as table_error:
            print(f"[DEBUG] Tabela user_whatsapp pode não existir: {table_error}")
            # Tentar criar a tabela automaticamente
            try:
                print("[DEBUG] Tentando criar tabela user_whatsapp...")
                # Script SQL para criar a tabela
                create_table_sql = """
                CREATE TABLE IF NOT EXISTS user_whatsapp (
                    id SERIAL PRIMARY KEY,
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    numero VARCHAR(15) NOT NULL,
                    nome VARCHAR(100),
                    tipo VARCHAR(20) DEFAULT 'pessoal',
                    principal BOOLEAN DEFAULT FALSE,
                    ativo BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
                """
                # Nota: Supabase não suporta execução de SQL direto via cliente Python
                # A tabela deve ser criada manualmente no banco
                print("[DEBUG] Tabela deve ser criada manualmente no banco de dados")
            except Exception as create_error:
                print(f"[DEBUG] Erro ao criar tabela: {create_error}")
        
        # Inserir novos WhatsApp validados
        whatsapp_inseridos = 0
        for whatsapp_validado in numeros_validados:
            try:
                # Tentar diferentes estruturas de tabela até encontrar a correta
                possible_inserts = [
                    # Estrutura 1: Completa com todos os campos
                    {
                        'user_id': user_id,
                        'numero': whatsapp_validado['numero'],
                        'nome': whatsapp_validado.get('descricao', ''),
                        'tipo': whatsapp_validado.get('tipo', 'pessoal'),
                        'principal': whatsapp_validado['principal'],
                        'ativo': True
                    },
                    # Estrutura 2: Sem campo nome/descricao
                    {
                        'user_id': user_id,
                        'numero': whatsapp_validado['numero'],
                        'tipo': whatsapp_validado.get('tipo', 'pessoal'),
                        'principal': whatsapp_validado['principal'],
                        'ativo': True
                    },
                    # Estrutura 3: Mínima - apenas campos essenciais
                    {
                        'user_id': user_id,
                        'numero': whatsapp_validado['numero'],
                        'principal': whatsapp_validado['principal']
                    },
                    # Estrutura 4: Alternativos de nome de campo
                    {
                        'user_id': user_id,
                        'telefone': whatsapp_validado['numero'],
                        'principal': whatsapp_validado['principal']
                    },
                    # Estrutura 5: Campo whatsapp em vez de numero
                    {
                        'user_id': user_id,
                        'whatsapp': whatsapp_validado['numero'],
                        'principal': whatsapp_validado['principal']
                    }
                ]
                
                success = False
                for i, insert_data in enumerate(possible_inserts, 1):
                    try:
                        print(f"[DEBUG] Tentativa {i} de inserir WhatsApp: {insert_data}")
                        insert_result = supabase_admin.table('user_whatsapp')\
                            .insert(insert_data)\
                            .execute()
                        print(f"[DEBUG] WhatsApp inserido com sucesso (estrutura {i}): {insert_result.data}")
                        whatsapp_inseridos += 1
                        success = True
                        break
                    except Exception as structure_error:
                        error_msg = str(structure_error)
                        print(f"[DEBUG] Tentativa {i} falhou: {error_msg}")
                        
                        # Se a tabela não existe, tentar na tabela de telefones do usuário
                        if 'does not exist' in error_msg.lower() or 'user_whatsapp' in error_msg:
                            print(f"[DEBUG] Tabela user_whatsapp não existe, tentando salvar em users.telefone")
                            try:
                                # Atualizar campo telefone do usuário
                                user_update = supabase_admin.table('users')\
                                    .update({'telefone': whatsapp_validado['numero']})\
                                    .eq('id', user_id)\
                                    .execute()
                                print(f"[DEBUG] WhatsApp salvo no campo telefone do usuário: {user_update.data}")
                                whatsapp_inseridos += 1
                                success = True
                                break
                            except Exception as telefone_error:
                                print(f"[DEBUG] Erro ao salvar em telefone: {telefone_error}")
                        
                        continue
                
                if not success:
                    print(f"[DEBUG] Todas as tentativas falharam para WhatsApp: {whatsapp_validado}")
                    
            except Exception as insert_error:
                print(f"[DEBUG] Erro geral ao inserir WhatsApp: {insert_error}")
                continue
        
        # Se nenhum WhatsApp foi inserido por problemas de tabela, usar campo telefone como fallback
        if whatsapp_inseridos == 0 and len(numeros_validados) > 0:
            try:
                # Como fallback, salvar o primeiro WhatsApp no campo telefone do usuário
                primeiro_whatsapp = numeros_validados[0]['numero']
                print(f"[DEBUG] Usando fallback: salvando WhatsApp no campo telefone do usuário")
                
                user_update = supabase_admin.table('users')\
                    .update({'telefone': primeiro_whatsapp})\
                    .eq('id', user_id)\
                    .execute()
                
                print(f"[DEBUG] WhatsApp salvo como telefone do usuário: {user_update.data}")
                
                return jsonify({
                    'success': True, 
                    'message': f'WhatsApp validados e salvos (usando campo telefone temporariamente). Total: {len(numeros_validados)}',
                    'validated_numbers': [w['numero'] for w in numeros_validados],
                    'fallback_used': True,
                    'note': 'Tabela user_whatsapp não existe. Execute o script SQL em sql/create_user_whatsapp_table.sql'
                })
                
            except Exception as fallback_error:
                print(f"[DEBUG] Erro no fallback: {fallback_error}")
                return jsonify({
                    'success': True, 
                    'message': f'WhatsApp validados com sucesso mas não puderam ser salvos (tabela não existe). Total validados: {len(numeros_validados)}',
                    'validated_numbers': [w['numero'] for w in numeros_validados],
                    'error': 'Tabela user_whatsapp não existe. Execute o script SQL em sql/create_user_whatsapp_table.sql'
                })
        
        return jsonify({
            'success': True, 
            'message': f'WhatsApp atualizados com sucesso. Total: {whatsapp_inseridos}/{len(numeros_validados)}'
        })
        
    except Exception as e:
        print(f"[DEBUG] Erro geral ao atualizar WhatsApp: {str(e)}")
        current_app.logger.error(f"Erro ao atualizar WhatsApp do usuário {user_id}: {str(e)}")
        return jsonify({'success': False, 'message': 'Erro interno do servidor'}), 500
