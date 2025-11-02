from flask import Flask, render_template, redirect, url_for, session, jsonify, request
from config import Config
import os
import signal
import extensions
from session_handler import init_session_handler
from services.logging_middleware import logging_middleware
from log_config import configure_logging, get_log_level_from_env

# Configurar logging da aplicação
configure_logging(level=get_log_level_from_env())

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Initialize Flask-SocketIO para rastreamento de usuários online em tempo real
from flask_socketio import SocketIO
socketio = SocketIO(
    app,
    cors_allowed_origins="*",  # Em produção, especificar domínios permitidos
    async_mode='eventlet',
    manage_session=True,
    logger=False,
    engineio_logger=False
)

# Configurar sessão para expirar após 12 horas (43200 segundos)
from datetime import timedelta
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=12)
app.config['SESSION_COOKIE_SECURE'] = False  # True apenas em HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Configurações de timeout para diferentes operações
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = timedelta(seconds=31536000)  # Cache para arquivos estáticos

# Configurar timeout para requests em produção - diferentes para diferentes operações
import requests
# Timeout padrão para operações normais
requests.adapters.DEFAULT_TIMEOUT = Config.QUERY_TIMEOUT
# Note: Para operações específicas (como Gemini), usaremos timeouts personalizados no código

# Inicializar manipulador de sessão
init_session_handler(app)

# Debug configuration
print("\n[DEBUG] ===== Configuração da Aplicação =====")
print(f"[DEBUG] Diretório atual: {os.getcwd()}")
print(f"[DEBUG] Arquivo .env existe: {os.path.exists('.env')}")
print(f"[DEBUG] SUPABASE_URL: {app.config['SUPABASE_URL']}")
print(f"[DEBUG] SUPABASE_SERVICE_KEY (primeiros 10 caracteres): {app.config['SUPABASE_SERVICE_KEY'][:10] if app.config['SUPABASE_SERVICE_KEY'] else 'None'}")
print(f"[DEBUG] SECRET_KEY: {app.config['SECRET_KEY']}")
print(f"[DEBUG] DEBUG: {app.config['DEBUG']}")
print("[DEBUG] ====================================\n")

# Initialize extensions
print("[DEBUG] Inicializando extensões...")
try:
    extensions.supabase, extensions.supabase_admin = extensions.init_supabase(app)
    print("[DEBUG] Extensões inicializadas com sucesso")
    print(f"[DEBUG] supabase type: {type(extensions.supabase)}")
    print(f"[DEBUG] supabase_admin type: {type(extensions.supabase_admin)}")
except Exception as e:
    print(f"[DEBUG] ERRO ao inicializar extensões: {str(e)}")
    raise

# Import session handler
from session_handler import init_session_handler

# Import module color helpers
from utils.module_colors import register_module_color_helpers

# Import routes after app initialization to avoid circular imports
from routes import dashboard, api
from routes import background_tasks

# Import modular users blueprint
from modules.usuarios import routes as usuarios_modular

# Import modular auth blueprint
from modules.auth.routes import bp as auth_bp

# Import modular config blueprint
from modules.config.routes import config_bp

# Import modular paginas blueprint
from modules.paginas.routes import paginas_bp

# Import modular menu blueprint
from modules.menu.routes import bp as menu_bp

# Import shared blueprint
from modules.shared.routes import shared_bp

# Import documents blueprint
from routes.documents import documents_bp

# Import importacoes blueprint and registration function (módulo consolidado)
from modules.importacoes import register_importacoes_blueprints

# Import financeiro blueprint and registration function
from modules.financeiro.routes import register_financeiro_blueprints

# Import RH blueprint and registration function
from modules.rh import register_rh_blueprints

# Import Carreiras blueprint (portal público de vagas)
from modules.carreiras import carreiras_bp

# Import analytics blueprint
from modules.analytics.routes import bp as analytics_bp

# Import portal contabilidade blueprint
from modules.contabilidade_externa import contabilidade_externa_bp
# Import i18n blueprint
from modules.i18n import i18n_bp

# Import usuarios_online blueprint (admin)
from modules.usuarios_online.routes import bp as usuarios_online_bp

# Register blueprints
# app.register_blueprint(auth.bp)  # Comentado - usando versão modular
app.register_blueprint(dashboard.bp)

app.register_blueprint(api.bp, url_prefix='/api')  # Registrando o blueprint da API com prefixo
app.register_blueprint(background_tasks.bp)  # Registrando o blueprint de Background Tasks

# Register modular users blueprint
app.register_blueprint(usuarios_modular.bp)  # Usuários modular

# Register modular auth blueprint
app.register_blueprint(auth_bp)  # Auth modular

# Register modular config blueprint
app.register_blueprint(config_bp)  # Config modular

# Register modular paginas blueprint
app.register_blueprint(paginas_bp)  # Páginas modular

# Register shared blueprint
app.register_blueprint(shared_bp)  # Shared static files

# Register documents blueprint
app.register_blueprint(documents_bp)  # Document management

# Register modular menu blueprint
app.register_blueprint(menu_bp)  # Menu modular

# Register noticias COMEX API blueprint
try:
    from routes.noticias_comex import bp as noticias_comex_bp
    app.register_blueprint(noticias_comex_bp)
    print("✅ Notícias COMEX API registrado")
except Exception as e:
    print(f"⚠️ Não foi possível registrar notícias COMEX API: {e}")

# Register importacoes blueprints (módulo de importações completo)
register_importacoes_blueprints(app)

# Register financeiro blueprints (módulo financeiro completo)
register_financeiro_blueprints(app)

# Register RH blueprints (módulo de RH completo)
register_rh_blueprints(app)

# Register Carreiras blueprint (portal público de vagas)
app.register_blueprint(carreiras_bp)

# Register analytics blueprint
app.register_blueprint(analytics_bp)
print("✅ Analytics blueprint registrado")

# Register external accounting portal blueprint
app.register_blueprint(contabilidade_externa_bp)
print("✅ Portal contabilidade externo registrado")
# Register i18n blueprint
app.register_blueprint(i18n_bp)
print("✅ i18n blueprint registrado")

# Register usuarios_online blueprint (admin)
app.register_blueprint(usuarios_online_bp)
print("✅ Usuários Online (Admin) blueprint registrado")

# Register module color helpers for templates
register_module_color_helpers(app)

# Initialize logging middleware (após registrar todos os blueprints)
logging_middleware.init_app(app)

# Initialize page tracking middleware (rastreamento de páginas para usuários online)
from middleware.page_tracking import page_tracking
page_tracking.init_app(app)
print("✅ Page Tracking Middleware inicializado")

# -------------------------------------------------------------
# i18n Language Initialization Middleware
# -------------------------------------------------------------
@app.before_request
def init_i18n_language():
    """Inicializa o idioma na session antes de cada requisição"""
    from modules.i18n.routes import init_language
    init_language()

# -------------------------------------------------------------
# Security Headers Middleware
# -------------------------------------------------------------
@app.after_request
def add_security_headers(response):
    """Add security headers to all responses"""
    # Prevent MIME type sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'
    
    # Prevent clickjacking attacks
    response.headers['X-Frame-Options'] = 'DENY'
    
    # Enable XSS protection
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # Strict Transport Security (HTTPS)
    # response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    # Content Security Policy (basic)
    response.headers['Content-Security-Policy'] = "default-src 'self' 'unsafe-inline' 'unsafe-eval' data: https:; img-src 'self' data: https:; font-src 'self' data: https:;"
    
    # Referrer Policy
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    return response

# -------------------------------------------------------------
# Global Client Branding Context
# -------------------------------------------------------------
from services.client_branding import get_client_branding, DEFAULT_BRANDING

def _resolve_client_branding():
    """Resolve and cache client branding in session (lazy)."""
    # If already cached, return it
    branding = session.get('client_branding')
    user = session.get('user') or {}
    
    if branding and isinstance(branding, dict):
        return branding
        
    if not user:
        return DEFAULT_BRANDING
        
    user_email = user.get('email')
    if not user_email:
        return DEFAULT_BRANDING
    
    # Use the shared branding utility
    branding = get_client_branding(user_email)
    
    # Cache in session
    session['client_branding'] = branding
    session.modified = True
    
    return branding

@app.context_processor
def inject_client_branding():
    return {'client_branding': _resolve_client_branding()}

@app.context_processor
def inject_i18n_helpers():
    """Disponibiliza funções de tradução para templates"""
    from utils.i18n_helper import translate, t, get_current_language, get_all_translations
    return {
        'translate': translate,
        't': t,
        'current_language': get_current_language,
        'get_translations': get_all_translations
    }

@app.context_processor
def inject_perfil_access_functions():
    """Disponibiliza funções de controle de acesso baseado em perfis para templates"""
    from services.perfil_access_service import PerfilAccessService
    return {
        'get_filtered_menu_structure': PerfilAccessService.get_filtered_menu_structure,
        'get_user_accessible_modules': PerfilAccessService.get_user_accessible_modules,
        'get_user_accessible_pages': PerfilAccessService.get_user_accessible_pages,
        'user_can_access_module': PerfilAccessService.user_can_access_module,
        'user_can_access_page': PerfilAccessService.user_can_access_page,
        'get_user_admin_capabilities': PerfilAccessService.get_user_admin_capabilities
    }

# -------------------------------------------------------------
# Debug route for client branding (para testes rápidos)
# Pode ser acessada via bypass de API ou sessão autenticada.
# -------------------------------------------------------------
from services.client_branding import get_client_branding

@app.route('/debug/admin-level')
def debug_admin_level():
    """Debug route to check admin level implementation"""
    api_bypass_key = os.getenv('API_BYPASS_KEY')
    request_api_key = request.headers.get('X-API-Key')
    if not ('user' in session or (api_bypass_key and request_api_key == api_bypass_key)):
        return jsonify({'error': 'Não autenticado'}), 401
    
    user = session.get('user', {})
    
    from services.perfil_access_service import PerfilAccessService
    admin_capabilities = PerfilAccessService.get_user_admin_capabilities()
    accessible_modules = PerfilAccessService.get_user_accessible_modules()
    
    return jsonify({
        'success': True,
        'user_email': user.get('email'),
        'user_role': user.get('role'),
        'perfil_principal': user.get('perfil_principal'),
        'admin_capabilities': admin_capabilities,
        'accessible_modules': accessible_modules
    })

@app.route('/debug/client-branding')
def debug_client_branding():
    api_bypass_key = os.getenv('API_BYPASS_KEY')
    request_api_key = request.headers.get('X-API-Key')
    if not ('user' in session or (api_bypass_key and request_api_key == api_bypass_key)):
        return jsonify({'error': 'Não autenticado'}), 401
    
    # Get branding for current user or test with bypass
    user = session.get('user', {})
    user_email = user.get('email') if user else None
    
    branding = get_client_branding(user_email)
    return jsonify({'success': True, 'branding': branding, 'user_email': user_email})

# Debug das rotas registradas
print("\n[DEBUG] ===== Rotas Registradas =====")
for rule in app.url_map.iter_rules():
    print(f"[DEBUG] Rota: {rule.rule} - Endpoint: {rule.endpoint}")
print("[DEBUG] ============================\n")

# Error handlers
@app.errorhandler(401)
def unauthorized_error(error):
    return render_template('errors/401.html'), 401

@app.errorhandler(403)
def forbidden_error(error):
    return render_template('errors/403.html'), 403

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('errors/500.html'), 500

@app.route('/')
def index():
    if 'user' in session:
        # Redireciona direto para o menu ao invés do dashboard executivo
        return redirect(url_for('menu.menu_home'))
    return redirect(url_for('auth.login'))

@app.route('/test-date-sorting')
def test_date_sorting():
    """Rota temporária para testar ordenação de datas"""
    with open('test_date_sorting.html', 'r', encoding='utf-8') as f:
        return f.read()

@app.route('/test-data-chegada')
def test_data_chegada():
    """Rota temporária para testar especificamente data_chegada"""
    with open('test_data_chegada_specific.html', 'r', encoding='utf-8') as f:
        return f.read()

@app.route('/test-empresa-search')
def test_empresa_search():
    """Rota temporária para testar busca de empresas"""
    if not app.config['DEBUG']:
        return "Disponível apenas em modo debug", 404
    
    try:
        with open('test_empresa_search.html', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "Arquivo de teste não encontrado", 404

@app.route('/test-menu-noticias')
def test_menu_noticias():
    """Rota temporária para testar galeria de notícias COMEX no menu"""
    if not app.config['DEBUG']:
        return "Disponível apenas em modo debug", 404
    
    try:
        with open('test_menu_com_noticias.html', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "Arquivo de teste não encontrado", 404

if __name__ == '__main__':   
    # Registrar WebSocket event handlers
    print("\n[DEBUG] ===== Registrando WebSocket Events =====")
    from websocket_events import register_events
    register_events(socketio, extensions.supabase_admin)
    print("[DEBUG] WebSocket events registrados com sucesso")
    print("[DEBUG] ======================================\n")
    
    # Start server based on FLASK_ENV
    flask_env = os.getenv('FLASK_ENV', app.config.get('ENV', 'production'))
    if flask_env == 'development':
        # Use socketio.run() ao invés de app.run() para suportar WebSocket
        socketio.run(app, debug=True, host='192.168.0.75', port=5000)
    else:
        socketio.run(app, debug=app.config.get('DEBUG', False))