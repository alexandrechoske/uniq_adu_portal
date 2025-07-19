"""
Módulo de Páginas - UniSystem Portal

Este módulo gerencia:
- Verificação de sessão para auto-refresh
- Páginas auxiliares do sistema
- Endpoints de compatibilidade
- Validação de autenticação em tempo real
"""

from .routes import paginas_bp

__all__ = ['paginas_bp']
