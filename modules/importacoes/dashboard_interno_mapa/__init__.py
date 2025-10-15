"""Dashboard Interno com foco em mapa interativo."""

from flask import Blueprint


def register_module(app):
    """Helper to register blueprint via app factory."""
    from .routes import dashboard_interno_mapa_bp

    app.register_blueprint(dashboard_interno_mapa_bp)
    return dashboard_interno_mapa_bp
