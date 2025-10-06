"""
Módulo de RH - UniSystem Portal
Gerencia todas as funcionalidades de Recursos Humanos
"""

from flask import Blueprint

__version__ = '1.0.0'
__author__ = 'UniSystem Team'

def register_rh_blueprints(app):
    """
    Registra todos os blueprints relacionados ao módulo de RH
    
    Args:
        app: Instância do Flask app
    """
    
    # Import blueprints (imports aqui para evitar circular imports)
    from modules.rh.colaboradores.routes import colaboradores_bp
    from modules.rh.estrutura_org import estrutura_org_bp
    from modules.rh.recrutamento import recrutamento_bp
    from modules.rh.dashboard import dashboard_rh_bp
    
    # Registrar blueprints
    app.register_blueprint(colaboradores_bp)
    app.register_blueprint(estrutura_org_bp)
    app.register_blueprint(recrutamento_bp)
    app.register_blueprint(dashboard_rh_bp)
    
    print("✅ Módulo de RH registrado com sucesso (Colaboradores + Estrutura + Recrutamento + Dashboard)")
