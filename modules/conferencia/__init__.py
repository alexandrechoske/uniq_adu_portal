"""
Módulo de Conferência - UniSystem Portal

Este módulo gerencia:
- Upload e processamento de PDFs aduaneiros
- Análise com IA (Gemini) para identificar inconsistências
- Extração de dados estruturados de documentos
- Processamento em background com feedback em tempo real
- Geração de relatórios de análise
"""

from .routes import conferencia_bp

__all__ = ['conferencia_bp']
