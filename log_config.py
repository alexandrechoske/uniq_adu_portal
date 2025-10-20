"""
Configuração de Logging para o Portal UniqueAduaneira

Níveis de log sugeridos:
- Produção: WARNING (apenas erros e avisos críticos)
- Desenvolvimento: INFO (informações gerais + erros)
- Debug: DEBUG (todos os logs, incluindo detalhes técnicos)

Uso no app.py:
    import logging
    from log_config import configure_logging
    
    configure_logging(level='WARNING')  # ou 'INFO', 'DEBUG'
"""

import logging
import sys
import os

def configure_logging(level='INFO'):
    """
    Configura o sistema de logging da aplicação
    
    Args:
        level (str): Nível de log ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
    """
    # Converter string para nível de logging
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Configuração do formato de log
    log_format = '[%(levelname)s] %(name)s: %(message)s'
    
    # Configurar logging básico
    logging.basicConfig(
        level=numeric_level,
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Configurar loggers específicos
    
    # Silenciar logs muito verbosos de bibliotecas externas
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('werkzeug').setLevel(logging.INFO)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    # Configurar loggers da aplicação
    logging.getLogger('services.perfil_access_service').setLevel(
        logging.DEBUG if numeric_level <= logging.DEBUG else logging.INFO
    )
    
    logging.getLogger('modules.importacoes.dashboards.executivo').setLevel(
        logging.DEBUG if numeric_level <= logging.DEBUG else logging.INFO
    )
    
    # Log da configuração
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configurado com nível: {level}")
    
    return logger

def get_log_level_from_env():
    """
    Obtém o nível de log da variável de ambiente LOG_LEVEL
    Padrão: INFO
    """
    return os.getenv('LOG_LEVEL', 'INFO')

# Exemplo de uso no app.py:
# from log_config import configure_logging, get_log_level_from_env
# configure_logging(level=get_log_level_from_env())
