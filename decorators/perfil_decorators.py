"""
Decoradores de Proteção por Perfil
Sistema de segurança avançado que valida acesso a módulos e páginas
baseado nos perfis configurados para o usuário
"""

from functools import wraps
from flask import session, render_template, jsonify, request
from services.perfil_access_service import PerfilAccessService
import json

def perfil_required(modulo_codigo, pagina_codigo=None):
    """
    Decorador que valida se o usuário tem acesso ao módulo/página específico
    
    Args:
        modulo_codigo (str): Código do módulo (ex: 'financeiro', 'importacao')
        pagina_codigo (str, optional): Código da página dentro do módulo
        
    Usage:
        @perfil_required('financeiro', 'fluxo_caixa')
        def fluxo_caixa():
            return render_template('fluxo_caixa.html')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Primeiro verificar se usuário está logado
            user = session.get('user', {})
            if not user:
                print(f"[SECURITY] Acesso negado: usuário não logado")
                if request.is_json:
                    return jsonify({'error': 'Usuário não autenticado', 'redirect': '/auth/login'}), 401
                return render_template('errors/401.html'), 401
            
            user_email = user.get('email', 'unknown')
            user_role = user.get('role', '')
            
            print(f"[SECURITY] Validando acesso para {user_email} ao módulo '{modulo_codigo}'" + 
                  (f" página '{pagina_codigo}'" if pagina_codigo else ""))
            
            # Admin tem acesso total
            if user_role == 'admin':
                print(f"[SECURITY] ✅ Admin {user_email} - acesso liberado")
                return f(*args, **kwargs)
            
            # Verificar se o usuário tem acesso ao módulo
            if not PerfilAccessService.user_can_access_module(modulo_codigo):
                print(f"[SECURITY] ❌ {user_email} SEM ACESSO ao módulo '{modulo_codigo}'")
                if request.is_json:
                    return jsonify({
                        'error': f'Acesso negado ao módulo {modulo_codigo}',
                        'details': 'Usuário não possui perfil adequado',
                        'user_modules': PerfilAccessService.get_user_accessible_modules()
                    }), 403
                return render_template('errors/403.html', 
                                     message=f'Acesso negado ao módulo {modulo_codigo}'), 403
            
            # Se especificado, verificar acesso à página específica
            if pagina_codigo:
                if not PerfilAccessService.user_can_access_page(modulo_codigo, pagina_codigo):
                    print(f"[SECURITY] ❌ {user_email} SEM ACESSO à página '{pagina_codigo}' do módulo '{modulo_codigo}'")
                    if request.is_json:
                        return jsonify({
                            'error': f'Acesso negado à página {pagina_codigo}',
                            'details': 'Usuário não possui perfil adequado para esta página',
                            'user_pages': PerfilAccessService.get_user_accessible_pages(modulo_codigo)
                        }), 403
                    return render_template('errors/403.html', 
                                         message=f'Acesso negado à página {pagina_codigo}'), 403
            
            print(f"[SECURITY] ✅ {user_email} - acesso liberado ao módulo '{modulo_codigo}'" + 
                  (f" página '{pagina_codigo}'" if pagina_codigo else ""))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def debug_user_access():
    """
    Função auxiliar para debug - mostra os acessos do usuário atual
    """
    user = session.get('user', {})
    if not user:
        return "Usuário não logado"
    
    user_perfis_info = user.get('user_perfis_info', [])
    accessible_modules = PerfilAccessService.get_user_accessible_modules()
    
    debug_info = {
        'email': user.get('email'),
        'role': user.get('role'),
        'perfis_count': len(user_perfis_info),
        'accessible_modules': accessible_modules,
        'module_pages': {}
    }
    
    for module in accessible_modules:
        debug_info['module_pages'][module] = PerfilAccessService.get_user_accessible_pages(module)
    
    return debug_info
