"""
Módulo de Relatórios - UniSystem Portal

Este módulo gerencia:
- Geração de relatórios de operações aduaneiras
- Filtros por período e cliente
- Exportação em PDF
- Visualização de dados consolidados
"""

from .routes import relatorios_bp

__all__ = ['relatorios_bp']
