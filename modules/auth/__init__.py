"""
Módulo de Autenticação - UniSystem Portal

Este módulo gerencia:
- Login e logout de usuários
- Decoradores de autenticação (login_required, role_required)
- Gerenciamento de sessões
- Verificação de permissões
- API bypass para testes
"""

from .routes import bp

__all__ = ['bp']
