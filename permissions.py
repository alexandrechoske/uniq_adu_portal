from flask import session
from functools import wraps
from extensions import supabase, supabase_admin
from flask import redirect, url_for, flash, current_app
import time

def get_user_permissions(user_id, role=None, force_refresh=False):
    """
    Busca as permissões do usuário no banco de dados com cache em sessão otimizado
    
    Args:
        user_id (str): ID do usuário
        role (str, optional): Papel do usuário para cache
        force_refresh (bool): Força atualização do cache
        
    Returns:
        dict: Dicionário com as permissões do usuário
    """
    try:
        # Verificar se já temos permissões em cache na sessão
        cache_key = f'permissions_{user_id}'
        cache_expiry = 1800  # 30 minutos de cache
        
        if not force_refresh and 'permissions_cache' in session and cache_key in session['permissions_cache']:
            cached_data = session['permissions_cache'][cache_key]
            # Verificar se o cache ainda é válido
            if 'cached_at' in cached_data and (time.time() - cached_data['cached_at']) < cache_expiry:
                return cached_data['data']
            else:
                # Cache expirado, será renovado
                pass
        
        if role is None and 'user' in session:
            role = session['user'].get('role')
            
        permissions = None
        
        # Se for admin, retorna todas as permissões
        if role == 'admin':
            permissions = {
                'is_admin': True,
                'is_active': True,
                'has_full_access': True,
                'pages': [],  # Será preenchido com todas as páginas pelo endpoint
                'accessible_companies': []  # Admin tem acesso total, não precisa listar
            }
        
        # Para clientes_unique - otimizado para reduzir consultas DB
        elif role == 'cliente_unique':
            # Buscar dados do agente - consulta única otimizada
            agent_data = supabase_admin.table('clientes_agentes')\
                .select('empresa, usuario_ativo, numero, aceite_termos')\
                .eq('user_id', user_id)\
                .execute()
            
            if not agent_data.data:
                permissions = {
                    'is_admin': False,
                    'is_active': False,
                    'has_full_access': False,
                    'pages': [],
                    'accessible_companies': []
                }
            else:
                # Extrair empresas e status em um loop otimizado
                user_companies = []
                is_active = False
                terms_accepted = False
                agent_number = None
                
                for agent in agent_data.data:
                    # Verificar status ativo
                    agent_active = agent.get('usuario_ativo')
                    if agent_active is True:
                        is_active = True
                    elif agent_active is None:
                        # Para usuários antigos sem o campo definido, assumir como ativo
                        is_active = True
                    
                    # Verificar termos
                    if agent.get('aceite_termos'):
                        terms_accepted = True
                        
                    # Número do agente
                    if agent.get('numero'):
                        agent_number = agent.get('numero')
                    
                    if agent.get('empresa'):
                        # Tratar formatos diferentes (string ou array)
                        companies = agent['empresa']
                        if isinstance(companies, str):
                            try:
                                companies = eval(companies)  # Tratar formato string ["company1", "company2"]
                            except:
                                companies = [companies]  # Tratar formato string única
                        user_companies.extend(companies)
                
                user_companies = list(set(user_companies))  # Remover duplicatas
                
                permissions = {
                    'is_admin': False,
                    'is_active': is_active,
                    'has_full_access': False,
                    'agent_number': agent_number,
                    'terms_accepted': terms_accepted,
                    'pages': [],  # Será preenchido pelo endpoint de páginas
                    'accessible_companies': user_companies
                }
        
        # Para outros papéis
        else:
            permissions = {
                'is_admin': False,
                'is_active': True,  # Assume-se que outros papéis estão ativos por padrão
                'has_full_access': False,
                'pages': [],  # Será preenchido pelo endpoint de páginas
                'accessible_companies': []
            }
        
        # Salvar no cache da sessão com timestamp
        if 'permissions_cache' not in session:
            session['permissions_cache'] = {}
        session['permissions_cache'][cache_key] = {
            'data': permissions,
            'cached_at': time.time()
        }
        
        return permissions
        
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar permissões: {str(e)}")
        # Em caso de erro, retornar permissões mínimas
        return {
            'is_admin': False,
            'is_active': False,
            'has_full_access': False,
            'pages': [],
            'accessible_companies': [],
            'error': str(e)
        }

def check_permission(required_roles=None, required_companies=None):
    """
    Decorador para verificar permissões de acesso a rotas
    
    Args:
        required_roles (list): Papéis permitidos para acessar a rota
        required_companies (list): Empresas permitidas para acessar a rota (para clientes_unique)
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Verificar se o usuário está logado
            if 'user' not in session:
                flash('Faça login para acessar esta página.', 'error')
                return redirect(url_for('auth.login'))
            
            user_id = session['user']['id']
            user_role = session['user']['role']
            
            # Admins têm acesso total
            if user_role == 'admin':
                return f(*args, **kwargs)
            
            # Verificar papéis requeridos
            if required_roles and user_role not in required_roles:
                flash('Acesso não autorizado para este perfil.', 'error')
                return redirect(url_for('dashboard.index'))
            
            # Buscar permissões do usuário
            permissions = get_user_permissions(user_id, user_role)
            
            # Verificar se o usuário está ativo
            if not permissions.get('is_active', False):
                flash('Seu acesso está desativado. Entre em contato com o suporte.', 'error')
                return redirect(url_for('auth.acesso_negado'))  # Redirecionar para página específica
            
            # Para clientes_unique, verificar acesso às empresas
            if user_role == 'cliente_unique' and required_companies:
                user_companies = permissions.get('accessible_companies', [])
                has_company_access = any(company in user_companies for company in required_companies)
                
                if not has_company_access:
                    flash('Você não tem permissão para acessar esta empresa.', 'error')
                    return redirect(url_for('auth.login'))  # Redirecionar para login
            
            # Atualizar permissões na sessão para uso em templates
            session['permissions'] = permissions
            
            # Passar as permissões para a função decorada
            kwargs['permissions'] = permissions
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
