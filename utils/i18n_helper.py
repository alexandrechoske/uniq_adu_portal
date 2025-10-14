"""
Helper para tradução de strings no portal
Sistema simplificado de i18n sem dependências externas
"""

from flask import session
import json
import os

# Idioma padrão
DEFAULT_LANGUAGE = 'pt-BR'

# Cache de traduções carregadas
_translations_cache = {}

def get_current_language():
    """
    Retorna o idioma atual da sessão
    """
    lang = session.get('language', DEFAULT_LANGUAGE)
    return lang

def load_translations(lang):
    """
    Carrega as traduções de um idioma específico
    """
    if lang in _translations_cache:
        return _translations_cache[lang]
    
    # Caminho para o arquivo de tradução
    translations_dir = os.path.join(os.path.dirname(__file__), '..', 'translations')
    file_path = os.path.join(translations_dir, f'{lang}.json')
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            translations = json.load(f)
            _translations_cache[lang] = translations
            return translations
    except FileNotFoundError:
        print(f"[WARNING] Arquivo de tradução não encontrado: {file_path}")
        return {}
    except json.JSONDecodeError as e:
        print(f"[ERROR] Erro ao decodificar JSON de tradução: {e}")
        return {}

def translate(key, **kwargs):
    """
    Traduz uma chave para o idioma atual
    
    Args:
        key: Chave da tradução (ex: 'common.welcome')
        **kwargs: Variáveis para interpolação (ex: name='João')
    
    Returns:
        String traduzida
    """
    lang = get_current_language()
    translations = load_translations(lang)
    
    # Navega pelo dicionário usando a chave separada por pontos
    keys = key.split('.')
    value = translations
    
    for k in keys:
        if isinstance(value, dict):
            value = value.get(k)
        else:
            value = None
            break
    
    # Se não encontrou tradução, retorna a chave
    if value is None:
        print(f"[WARNING] Tradução não encontrada: {key} (idioma: {lang})")
        return key
    
    # Interpola variáveis se fornecidas
    if kwargs:
        try:
            value = value.format(**kwargs)
        except KeyError as e:
            print(f"[WARNING] Variável não fornecida para interpolação: {e}")
    
    return value

def t(key, **kwargs):
    """
    Alias curto para translate()
    """
    return translate(key, **kwargs)

def get_all_translations():
    """
    Retorna todas as traduções do idioma atual
    Útil para disponibilizar no JavaScript
    """
    lang = get_current_language()
    return load_translations(lang)
