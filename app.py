from flask import Flask, render_template, redirect, url_for, session
from config import Config
import os
from extensions import init_supabase

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

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

# Import routes after app initialization to avoid circular imports
from routes import auth, dashboard, relatorios, usuarios, agente, api, onepage

# Register blueprints
app.register_blueprint(auth.bp)
app.register_blueprint(dashboard.bp)
app.register_blueprint(relatorios.bp)
app.register_blueprint(usuarios.bp)
app.register_blueprint(agente.bp)
app.register_blueprint(api.bp)  # Registrando o blueprint da API
app.register_blueprint(onepage.bp)  # Registrando o blueprint do OnePage

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