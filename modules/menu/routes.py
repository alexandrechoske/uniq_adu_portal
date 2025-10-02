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


@bp.route('/api/quick-access')
@login_required
def get_quick_access():
    """Retorna os módulos mais acessados do usuário para o componente de Acesso Rápido.
    
    Consulta a VIEW vw_user_most_accessed_modules e retorna os top 6 módulos.
    Inclui mapeamento de ícones e URLs para cada módulo.
    """
    try:
        # LOG 1: Informações da sessão
        app.logger.info('[QUICK_ACCESS] === INÍCIO DEBUG ===')
        app.logger.info(f'[QUICK_ACCESS] Session keys: {list(session.keys())}')
        
        # FIX: Buscar user_id de session['user']['id'] ao invés de session['user_id']
        user_data = session.get('user')
        app.logger.info(f'[QUICK_ACCESS] user na session: {user_data}')
        
        if not user_data or not isinstance(user_data, dict):
            app.logger.warning('[QUICK_ACCESS] ❌ Dados de usuário não encontrados na sessão')
            return jsonify({'success': False, 'error': 'Usuário não autenticado'}), 401
        
        user_id = user_data.get('id')
        
        # LOG 2: Verificação de user_id
        if not user_id:
            app.logger.warning('[QUICK_ACCESS] ❌ user_id não encontrado em session["user"]')
            app.logger.warning(f'[QUICK_ACCESS] user_data completo: {user_data}')
            return jsonify({'success': False, 'error': 'Usuário não autenticado'}), 401
        
        app.logger.info(f'[QUICK_ACCESS] ✅ user_id encontrado: {user_id}')
        
        # LOG 3: Consulta à VIEW
        app.logger.info('[QUICK_ACCESS] Consultando VIEW vw_user_most_accessed_modules...')
        response = supabase_admin.table('vw_user_most_accessed_modules')\
            .select('module_name, page_name, access_count, last_url')\
            .eq('user_id', user_id)\
            .order('access_count', desc=True)\
            .limit(6)\
            .execute()
        
        # LOG 4: Resultado da consulta
        app.logger.info(f'[QUICK_ACCESS] Registros encontrados: {len(response.data) if response.data else 0}')
        if response.data:
            app.logger.info(f'[QUICK_ACCESS] Primeiros 3 módulos: {response.data[:3]}')
        
        if not response.data:
            app.logger.info('[QUICK_ACCESS] ℹ️ Nenhum módulo encontrado para este usuário')
            return jsonify({'success': True, 'modules': []})
        
        # Mapeamento de módulos para ícones e rotas
        module_mapping = {
            'dashboard_executivo': {
                'icon': 'mdi-chart-box',
                'route': 'dashboard_executivo.index',
                'display_name': 'Dashboard Executivo'
            },
            'dashboard_operacional': {
                'icon': 'mdi-monitor-dashboard',
                'route': 'dashboard_operacional.index',
                'display_name': 'Dashboard Operacional'
            },
            'dash_importacoes_resumido': {
                'icon': 'mdi-television-guide',
                'route': 'dash_importacoes_resumido.dashboard',
                'display_name': 'Dashboard TV'
            },
            'financeiro': {
                'icon': 'mdi-cash-multiple',
                'route': 'financeiro.index',
                'display_name': 'Financeiro'
            },
            'fin_dashboard_executivo': {
                'icon': 'mdi-chart-box',
                'route': 'fin_dashboard_executivo.index',
                'display_name': 'Financeiro - Dashboard'
            },
            'fin_fluxo_de_caixa': {
                'icon': 'mdi-chart-timeline-variant',
                'route': 'fin_fluxo_de_caixa.index',
                'display_name': 'Fluxo de Caixa'
            },
            'fin_conciliacao_bancaria': {
                'icon': 'mdi-bank-check',
                'route': 'fin_conciliacao_bancaria.index',
                'display_name': 'Conciliação Bancária'
            },
            'relatorios': {
                'icon': 'mdi-file-document-multiple',
                'route': 'relatorios.index',
                'display_name': 'Relatórios'
            },
            'export_relatorios': {
                'icon': 'mdi-file-export',
                'route': 'export_relatorios.index',
                'display_name': 'Exportar Relatórios'
            },
            'config': {
                'icon': 'mdi-cog',
                'route': 'config.index',
                'display_name': 'Configurações'
            }
        }
        
        # Processar dados e adicionar informações de rota/ícone
        quick_access_modules = []
        for module in response.data:
            module_name = module.get('module_name')
            mapping = module_mapping.get(module_name)
            
            if mapping:
                quick_access_modules.append({
                    'module_name': module_name,
                    'display_name': mapping['display_name'],
                    'icon': mapping['icon'],
                    'route': mapping['route'],
                    'access_count': module.get('access_count', 0),
                    'last_url': module.get('last_url')
                })
        
        app.logger.info(f'[MENU] Quick Access retornou {len(quick_access_modules)} módulos para user_id={user_id}')
        
        return jsonify({
            'success': True,
            'modules': quick_access_modules
        })
        
    except Exception as e:
        app.logger.exception('[MENU] Erro ao buscar módulos de acesso rápido: %s', e)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
