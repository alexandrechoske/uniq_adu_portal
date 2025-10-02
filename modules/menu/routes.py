from flask import Blueprint, render_template, session, jsonify, current_app as app
from modules.auth.routes import login_required
from extensions import supabase_admin
from services.perfil_access_service import PerfilAccessService
import re

bp = Blueprint('menu', __name__,
    url_prefix='/menu',
    template_folder='templates',
    static_folder='static',
    static_url_path='/menu/static')

@bp.route('/')
@login_required
def menu_home():
    """Página principal do menu.

    Inclui logs defensivos para investigar erro 500 observado em produção.
    Agora com filtragem de menu baseada em perfis de usuário.
    """
    try:
        user = session.get('user', {})
        if not isinstance(user, dict):
            app.logger.error('[MENU] session["user"] em formato inesperado: %r', user)
            user = {}
        
        app.logger.debug('[MENU] Render /menu user_id=%s role=%s',
                          user.get('id'), user.get('role'))
        
        # Obter menu filtrado baseado nos perfis do usuário
        filtered_menu = PerfilAccessService.get_filtered_menu_structure()
        accessible_modules = PerfilAccessService.get_user_accessible_modules()
        
        print(f"[MENU] Menu filtrado para {user.get('email')}: {list(filtered_menu.keys())}")
        
        return render_template('menu.html', 
                             filtered_menu=filtered_menu,
                             accessible_modules=accessible_modules,
                             user_perfis=user.get('user_perfis', []))
    except Exception as e:
        app.logger.exception('[MENU] Erro ao renderizar menu_home: %s', e)
        return render_template('errors/500.html'), 500

@bp.route('/dashboards')
@login_required
def dashboards():
    return render_template('dashboards.html')

@bp.route('/ferramentas')
@login_required
def ferramentas():
    return render_template('ferramentas.html')

@bp.route('/test-tabs')
@login_required
def test_tabs():
    """Página de teste do novo layout com tabs"""
    try:
        user = session.get('user', {})
        if not isinstance(user, dict):
            user = {}
        
        # Obter menu filtrado baseado nos perfis do usuário
        filtered_menu = PerfilAccessService.get_filtered_menu_structure()
        accessible_modules = PerfilAccessService.get_user_accessible_modules()
        
        print(f"[MENU TEST TABS] Menu filtrado para {user.get('email')}: {list(filtered_menu.keys())}")
        
        return render_template('test_menu_tabs.html', 
                             filtered_menu=filtered_menu,
                             accessible_modules=accessible_modules,
                             user_perfis=user.get('user_perfis', []))
    except Exception as e:
        app.logger.exception('[MENU TEST TABS] Erro ao renderizar: %s', e)
        return render_template('errors/500.html'), 500
def ferramentas():
    return render_template('ferramentas.html')

@bp.route('/configuracoes')
@login_required
def configuracoes():
    return render_template('configuracoes.html')

@bp.route('/test-menu-restyle')
@login_required
def test_menu_restyle():
    """Página de teste para nova versão do layout do menu (admin/interno vs cliente)."""
    user = session.get('user', {})
    user_companies_info = user.get('user_companies_info', [])
    return render_template('test_menu_restyle.html', user_companies_info=user_companies_info)

@bp.route('/api/user-companies-debug')
@login_required
def user_companies_debug():
    """Endpoint para debug das empresas do usuário"""
    try:
        user = session.get('user', {})
        user_id = user.get('id')
        user_role = user.get('role')
        
        debug_info = {
            'user_info': {
                'id': user_id,
                'email': user.get('email'),
                'role': user_role,
                'name': user.get('name')
            },
            'session_companies': user.get('user_companies', []),
            'session_companies_info': user.get('user_companies_info', []),
            'companies_from_db': []
        }
        
        # Buscar empresas diretamente do banco para comparar
        if user_role in ['cliente_unique', 'interno_unique']:
            try:
                # Buscar vínculos do usuário
                user_empresas_response = supabase_admin.table('user_empresas')\
                    .select('cliente_sistema_id, ativo, data_vinculo')\
                    .eq('user_id', user_id)\
                    .eq('ativo', True)\
                    .execute()
                
                if user_empresas_response.data:
                    cliente_sistema_ids = [v['cliente_sistema_id'] for v in user_empresas_response.data]
                    
                    # Buscar dados das empresas
                    empresas_response = supabase_admin.table('cad_clientes_sistema')\
                        .select('id, nome_cliente, cnpjs, ativo')\
                        .in_('id', cliente_sistema_ids)\
                        .eq('ativo', True)\
                        .execute()
                    
                    debug_info['companies_from_db'] = empresas_response.data
            except Exception as e:
                debug_info['db_error'] = str(e)
        
        return jsonify({
            'success': True,
            'debug_info': debug_info
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/api/menu-filtrado')
@login_required
def api_menu_filtrado():
    """API para obter menu filtrado baseado nos perfis do usuário"""
    try:
        user = session.get('user', {})
        
        # Debug: imprimir dados do usuário
        print(f"[DEBUG_MENU_API] User data: {user}")
        print(f"[DEBUG_MENU_API] User perfis: {user.get('user_perfis')}")
        print(f"[DEBUG_MENU_API] User perfis_info: {user.get('user_perfis_info')}")
        
        # Obter menu filtrado
        filtered_menu = PerfilAccessService.get_filtered_menu_structure()
        accessible_modules = PerfilAccessService.get_user_accessible_modules()
        
        # Obter informações dos perfis do usuário
        user_perfis = user.get('user_perfis', [])
        user_perfis_info = user.get('user_perfis_info', [])
        
        print(f"[DEBUG_MENU_API] Filtered menu: {filtered_menu}")
        print(f"[DEBUG_MENU_API] Accessible modules: {accessible_modules}")
        
        return jsonify({
            'success': True,
            'menu': filtered_menu,
            'accessible_modules': accessible_modules,
            'user_info': {
                'email': user.get('email'),
                'name': user.get('name'),
                'role': user.get('role'),
                'perfis': user_perfis,
                'perfis_info': user_perfis_info
            }
        })
        
    except Exception as e:
        app.logger.exception('[MENU] Erro ao obter menu filtrado: %s', e)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
