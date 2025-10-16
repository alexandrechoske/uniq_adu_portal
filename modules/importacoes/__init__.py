"""
Módulo de Importações - UniSystem Portal
Gerencia todas as funcionalidades relacionadas a importações aduaneiras
"""

from flask import Blueprint

# Este arquivo será usado para consolidar todos os blueprints do módulo de importações
__version__ = '1.0.0'
__author__ = 'UniSystem Team'

# Função para registrar todos os blueprints do módulo de importações
def register_importacoes_blueprints(app):
    """
    Registra todos os blueprints relacionados ao módulo de importações
    
    Args:
        app: Instância do Flask app
    """
    
    # Import blueprints (imports aqui para evitar circular imports)
    from modules.importacoes.agente.routes import bp as agente_bp
    from modules.importacoes.conferencia.routes import conferencia_bp
    from modules.importacoes.dashboard_interno_mapa.routes import (
        dashboard_interno_mapa_bp,
    )
    from modules.importacoes.dashboards.executivo.routes import bp as dashboard_executivo_bp
    from modules.importacoes.dashboards.executivo.api_armazenagem import api_armazenagem_bp
    from modules.importacoes.dashboards.operacional.routes import dashboard_operacional
    from modules.importacoes.dashboards.resumido import dash_importacoes_resumido_bp
    from modules.importacoes.relatorios.routes import relatorios_bp
    from modules.importacoes.export_relatorios.routes import export_relatorios_bp
    from modules.importacoes.ajuste_status.routes import ajuste_status_bp
    
    # Log de registro do blueprint de armazenagem
    print(f"[INIT_IMPORTACOES] 🔧 Registrando api_armazenagem_bp...")
    print(f"[INIT_IMPORTACOES] Blueprint name: {api_armazenagem_bp.name}")
    print(f"[INIT_IMPORTACOES] URL prefix: {api_armazenagem_bp.url_prefix}")
    
    # Registrar blueprints
    app.register_blueprint(agente_bp)
    app.register_blueprint(conferencia_bp)
    app.register_blueprint(dashboard_interno_mapa_bp)
    app.register_blueprint(dashboard_executivo_bp)
    app.register_blueprint(api_armazenagem_bp)  # API de armazenagem Kingspan
    print(f"[INIT_IMPORTACOES] ✅ api_armazenagem_bp registrado com sucesso!")
    app.register_blueprint(dashboard_operacional)
    app.register_blueprint(dash_importacoes_resumido_bp)
    app.register_blueprint(relatorios_bp)
    app.register_blueprint(export_relatorios_bp)
    app.register_blueprint(ajuste_status_bp)
    
    print("✅ Módulo de Importações registrado com sucesso")
