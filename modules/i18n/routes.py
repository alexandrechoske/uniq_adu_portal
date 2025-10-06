"""
Rotas para controle de idioma
"""

from flask import session, redirect, request, url_for, jsonify, g
from . import i18n_bp
import os

# Idiomas suportados
SUPPORTED_LANGUAGES = ['pt-BR', 'en-US']
DEFAULT_LANGUAGE = 'pt-BR'

def init_language():
    """
    Inicializa o idioma na session se não existir
    Deve ser chamado em before_request
    """
    if 'language' not in session:
        session['language'] = DEFAULT_LANGUAGE
        session.modified = True
    
    # Armazena no contexto global para fácil acesso
    g.language = session.get('language', DEFAULT_LANGUAGE)

def _check_api_bypass():
    """Verifica se a requisição tem bypass de API"""
    api_bypass_key = os.getenv('API_BYPASS_KEY')
    request_api_key = request.headers.get('X-API-Key')
    return api_bypass_key and request_api_key == api_bypass_key

@i18n_bp.route('/set-language/<lang>', methods=['POST', 'GET'])
def set_language(lang):
    """
    Define o idioma preferido do usuário
    """
    # Verifica API bypass ou usuário logado
    has_bypass = _check_api_bypass()
    has_user = 'user' in session
    
    if not (has_bypass or has_user):
        return jsonify({'error': 'Não autorizado', 'success': False}), 401
    
    if lang not in SUPPORTED_LANGUAGES:
        lang = DEFAULT_LANGUAGE
    
    # Armazena na session
    session['language'] = lang
    session.modified = True
    
    # Redireciona de volta para a página anterior ou para home
    next_page = request.referrer or '/'
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'language': lang})
    
    return redirect(next_page)

@i18n_bp.route('/get-language', methods=['GET'])
def get_language():
    """
    Retorna o idioma atual
    """
    current_lang = session.get('language', DEFAULT_LANGUAGE)
    return jsonify({'language': current_lang})

@i18n_bp.route('/get-translations', methods=['GET'])
def get_translations():
    """
    Retorna todas as traduções do idioma atual em JSON
    Para uso no JavaScript
    """
    from utils.i18n_helper import get_all_translations
    translations = get_all_translations()
    return jsonify(translations)

@i18n_bp.route('/test', methods=['GET'])
def test_page():
    """
    Página de teste de tradução
    """
    from flask import render_template
    return render_template('test_traducao.html')
