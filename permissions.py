from flask import session
from functools import wraps
from extensions import supabase
from flask import redirect, url_for, flash, current_app

def get_user_permissions(user_id, role=None):
    """
    Busca as permissões do usuário no banco de dados
    
    Args:
        user_id (str): ID do usuário
        role (str, optional): Papel do usuário para cache
        
    Returns:
        dict: Dicionário com as permissões do usuário
    """
    try:
        print(f"[DEBUG] Buscando permissões para user_id: {user_id}, role: {role}")
        if role is None and 'user' in session:
            role = session['user'].get('role')
            print(f"[DEBUG] Role obtida da sessão: {role}")
          # Se for admin, retorna todas as permissões
        if role == 'admin':
            print(f"[DEBUG] Usuário é admin, retornando permissões de administrador")
            
            # Buscar todas as empresas disponíveis para o admin
            try:
                companies_response = supabase.table('importacoes_processos').select('cliente_cpfcnpj').execute()
                all_companies = []
                if companies_response.data:
                    all_companies = list(set([item.get('cliente_cpfcnpj') for item in companies_response.data if item.get('cliente_cpfcnpj')]))
                    print(f"[DEBUG] Admin: encontradas {len(all_companies)} empresas únicas")
            except Exception as e:
                print(f"[DEBUG] Erro ao buscar empresas para admin: {str(e)}")
                all_companies = []
                
            return {
                'is_admin': True,
                'is_active': True,
                'has_full_access': True,
                'pages': [],  # Será preenchido com todas as páginas pelo endpoint
                'accessible_companies': all_companies  # Admins têm acesso a todas as empresas
            }
        
        # Para clientes_unique
        if role == 'cliente_unique':
            # Buscar dados do agente
            agent_data = supabase.table('clientes_agentes')\
                .select('empresa, usuario_ativo, numero, aceite_termos')\
                .eq('user_id', user_id)\
                .execute()
            
            if not agent_data.data:
                return {
                    'is_admin': False,
                    'is_active': False,
                    'has_full_access': False,
                    'pages': [],
                    'accessible_companies': []
                }
            
            # Extrair empresas
            user_companies = []
            for agent in agent_data.data:
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
            
            return {
                'is_admin': False,
                'is_active': any(agent.get('usuario_ativo', False) for agent in agent_data.data),
                'has_full_access': False,
                'agent_number': agent_data.data[0].get('numero'),
                'terms_accepted': any(agent.get('aceite_termos', False) for agent in agent_data.data),
                'pages': [],  # Será preenchido pelo endpoint de páginas
                'accessible_companies': user_companies
            }
        
        # Para outros papéis
        return {
            'is_admin': False,
            'is_active': True,  # Assume-se que outros papéis estão ativos por padrão
            'has_full_access': False,
            'pages': [],  # Será preenchido pelo endpoint de páginas
            'accessible_companies': []
        }
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar permissões: {str(e)}")
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
                return redirect(url_for('dashboard.index'))
            
            # Para clientes_unique, verificar acesso às empresas
            if user_role == 'cliente_unique' and required_companies:
                user_companies = permissions.get('accessible_companies', [])
                has_company_access = any(company in user_companies for company in required_companies)
                
                if not has_company_access:
                    flash('Você não tem permissão para acessar esta empresa.', 'error')
                    return redirect(url_for('dashboard.index'))
            
            # Atualizar permissões na sessão para uso em templates
            session['permissions'] = permissions
            
            # Passar as permissões para a função decorada
            kwargs['permissions'] = permissions
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
