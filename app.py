from flask import Flask, render_template, redirect, url_for, session
from config import Config
import os
import signal
from extensions import init_supabase
from session_handler import init_session_handler

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
print(f"[DEBUG] SUPABASE_KEY (primeiros 10 caracteres): {app.config['SUPABASE_KEY'][:10] if app.config['SUPABASE_KEY'] else 'None'}")
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
from routes import auth, dashboard, relatorios, usuarios, agente, api, onepage, conferencia
from routes import conferencia_pdf, debug, paginas, materiais
from routes import background_tasks

# Register blueprints
app.register_blueprint(auth.bp)
app.register_blueprint(dashboard.bp)
app.register_blueprint(relatorios.bp)
app.register_blueprint(usuarios.bp)
app.register_blueprint(agente.bp)
app.register_blueprint(api.bp, url_prefix='/api')  # Registrando o blueprint da API com prefixo
app.register_blueprint(onepage.bp)  # Registrando o blueprint do OnePage
app.register_blueprint(conferencia.bp)  # Registrando o blueprint de Conferência Documental IA
app.register_blueprint(conferencia_pdf.bp)  # Registrando o blueprint de PDF anotado para Conferência
app.register_blueprint(debug.bp)  # Registrando o blueprint de Debug
app.register_blueprint(paginas.bp)  # Registrando o blueprint de Páginas
app.register_blueprint(materiais.bp, url_prefix='/materiais')  # Registrando o blueprint de Materiais
app.register_blueprint(background_tasks.bp)  # Registrando o blueprint de Background Tasks

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
        return redirect(url_for('dashboard.index'))
    return redirect(url_for('auth.login'))

if __name__ == '__main__':
    app.run(debug=True)  # Forçando debug para true