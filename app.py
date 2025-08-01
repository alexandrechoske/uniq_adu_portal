from flask import Flask, render_template, redirect, url_for, session, jsonify
from config import Config
import os
import signal
from extensions import init_supabase
from session_handler import init_session_handler
from services.logging_middleware import logging_middleware

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

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
print(f"[DEBUG] SUPABASE_SERVICE_KEY (primeiros 10 caracteres): {app.config['SUPABASE_SERVICE_KEY'][:10] if app.config['SUPABASE_SERVICE_KEY'] else 'None'}")
print(f"[DEBUG] SECRET_KEY: {app.config['SECRET_KEY']}")
print(f"[DEBUG] DEBUG: {app.config['DEBUG']}")
print("[DEBUG] ====================================\n")

# Initialize extensions
print("[DEBUG] Inicializando extensões...")
try:
    init_supabase(app)
    print("[DEBUG] Extensões inicializadas com sucesso")
except Exception as e:
    print(f"[DEBUG] ERRO ao inicializar extensões: {str(e)}")
    raise

# Import session handler
from session_handler import init_session_handler

# Import routes after app initialization to avoid circular imports
from routes import dashboard, api
from routes import conferencia_pdf, debug, paginas
from routes import background_tasks

# Import modular dashboard blueprints
from modules.dashboard_executivo import routes as dashboard_executivo

# Import modular users blueprint
from modules.usuarios import routes as usuarios_modular

# Import modular agente blueprint
from modules.agente import routes as agente_modular

# Import modular auth blueprint
from modules.auth.routes import bp as auth_bp

# Import modular relatorios blueprint
from modules.relatorios.routes import relatorios_bp

# Import modular conferencia blueprint
from modules.conferencia.routes import conferencia_bp as conferencia_modular_bp

# Import modular config blueprint
from modules.config.routes import config_bp

# Import modular paginas blueprint
from modules.paginas.routes import paginas_bp

# Import modular menu blueprint
from modules.menu.routes import bp as menu_bp

# Import modular analytics blueprint
from modules.analytics import analytics_bp

# Import shared blueprint
from modules.shared.routes import shared_bp

# Import documents blueprint
from routes.documents import documents_bp

# Register blueprints
# app.register_blueprint(auth.bp)  # Comentado - usando versão modular
app.register_blueprint(dashboard.bp)
# app.register_blueprint(relatorios.bp)  # Comentado - usando versão modular
# app.register_blueprint(usuarios.bp)  # Comentado - usando versão modular
# app.register_blueprint(agente.bp)  # Comentado - usando versão modular
app.register_blueprint(api.bp, url_prefix='/api')  # Registrando o blueprint da API com prefixo
# app.register_blueprint(conferencia.bp)  # Comentado - usando versão modular
app.register_blueprint(conferencia_pdf.bp)  # Registrando o blueprint de PDF anotado para Conferência
app.register_blueprint(debug.bp)  # Registrando o blueprint de Debug
# app.register_blueprint(paginas.bp)  # Comentado - usando versão modular
# app.register_blueprint(config.bp)  # Comentado - usando versão modular
app.register_blueprint(background_tasks.bp)  # Registrando o blueprint de Background Tasks

# Register modular dashboard blueprints
app.register_blueprint(dashboard_executivo.bp)  # Dashboard Executivo modular

# Register modular users blueprint
app.register_blueprint(usuarios_modular.bp)  # Usuários modular

# Register modular agente blueprint
app.register_blueprint(agente_modular.bp)  # Agente modular

# Register modular auth blueprint
app.register_blueprint(auth_bp)  # Auth modular

# Register modular relatorios blueprint
app.register_blueprint(relatorios_bp)  # Relatórios modular

# Register modular conferencia blueprint
app.register_blueprint(conferencia_modular_bp)  # Conferência modular

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

# Register modular analytics blueprint
app.register_blueprint(analytics_bp)  # Analytics modular

# Initialize logging middleware (após registrar todos os blueprints)
logging_middleware.init_app(app)

# Debug das rotas registradas
print("\n[DEBUG] ===== Rotas Registradas =====")
for rule in app.url_map.iter_rules():
    print(f"[DEBUG] Rota: {rule.rule} - Endpoint: {rule.endpoint}")
print("[DEBUG] ============================\n")

# Error handlers
@app.errorhandler(401)
def unauthorized_error(error):
    return render_template('errors/401.html'), 401

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.route('/')
def index():
    if 'user' in session:
        return redirect(url_for('dashboard_executivo.index'))
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

if __name__ == '__main__':
    # Registrar rotas de teste apenas em desenvolvimento
    if app.config['DEBUG']:
        try:
            from test_usuarios_api import register_test_routes
            register_test_routes(app)
            print("[DEBUG] Rotas de teste registradas")
        except Exception as e:
            print(f"[DEBUG] Erro ao registrar rotas de teste: {str(e)}")
    
    app.run(debug=True)  # Forçando debug para true