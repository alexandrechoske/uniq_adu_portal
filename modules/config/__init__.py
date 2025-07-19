"""
Módulo de Configuração - UniSystem Portal

Este módulo gerencia:
- Configuração de logos de clientes
- Gerenciamento de ícones de materiais
- Configurações de CNPJ e dados cadastrais
- Upload e manipulação de assets visuais
- APIs de configuração do sistema
"""

from .routes import config_bp

__all__ = ['config_bp']
