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
    from modules.importacoes.analytics import analytics_bp
    from modules.importacoes.conferencia.routes import conferencia_bp
    from modules.importacoes.dashboards.executivo.routes import bp as dashboard_executivo_bp
    from modules.importacoes.dashboards.operacional.routes import dashboard_operacional
    from modules.importacoes.dashboards.resumido import dash_importacoes_resumido_bp
    from modules.importacoes.relatorios.routes import relatorios_bp
    from modules.importacoes.export_relatorios.routes import export_relatorios_bp
    
    # Registrar blueprints
    app.register_blueprint(agente_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(conferencia_bp)
    app.register_blueprint(dashboard_executivo_bp)
    app.register_blueprint(dashboard_operacional)
    app.register_blueprint(dash_importacoes_resumido_bp)
    app.register_blueprint(relatorios_bp)
    app.register_blueprint(export_relatorios_bp)
    
    print("✅ Módulo de Importações registrado com sucesso")
