"""
Document Management API Endpoints
Endpoints para gerenciamento de documentos dos processos
"""

from flask import Blueprint, request, jsonify, send_file, abort, session
from werkzeug.utils import secure_filename
import mimetypes
from datetime import datetime
import os
from functools import wraps

from services.document_service import document_service
from routes.auth import login_required, role_required
from permissions import get_user_info
from extensions import supabase

# Blueprint para documentos
documents_bp = Blueprint('documents', __name__, url_prefix='/api/documents')

def api_auth_required(f):
    """
    Decorador personalizado para APIs que:
    1. Permite bypass com X-API-Key
    2. Verifica sessão Flask para usuários logados
    3. Retorna JSON error em vez de redirect para login
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 1. Verificar bypass key primeiro
        api_bypass_key = os.getenv('API_BYPASS_KEY')
        request_api_key = request.headers.get('X-API-Key')
        
        print(f"[AUTH DEBUG] API_BYPASS_KEY configurada: {bool(api_bypass_key)}")
        print(f"[AUTH DEBUG] X-API-Key recebida: {bool(request_api_key)}")
        print(f"[AUTH DEBUG] Chaves são iguais: {request_api_key == api_bypass_key}")
        
        if api_bypass_key and request_api_key == api_bypass_key:
            print(f"[AUTH DEBUG] Usando bypass key para acesso")
            # Para bypass, simular user_info admin
            return f(*args, **kwargs)
        
        # 2. Verificar se usuário está logado via sessão
        if 'user' not in session:
            return jsonify({
                'success': False,
                'error': 'Usuário não autenticado. Faça login para acessar esta funcionalidade.'
            }), 401
        
        return f(*args, **kwargs)
    return decorated_function

@documents_bp.route('/upload', methods=['POST'])
@login_required
def upload_document():
    """
    Upload de documento para um processo
    Todas as roles podem fazer upload
    """
    try:
        user_info = get_user_info()
        user_role = user_info.get('role')
        user_email = user_info.get('email')
        
        # Verificar permissão - TODAS as roles podem fazer upload
        if user_role not in ['admin', 'interno_unique', 'cliente_unique']:
            return jsonify({
                'success': False,
                'error': 'Acesso negado. Role não autorizada.'
            }), 403
        
        # Validar dados da requisição
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'Nenhum arquivo enviado'
            }), 400
        
        file = request.files['file']
        ref_unique = request.form.get('ref_unique')
        display_name = request.form.get('display_name', '')
        description = request.form.get('description', '')
        visible_to_client = request.form.get('visible_to_client', 'true').lower() == 'true'
        
        if not ref_unique:
            return jsonify({
                'success': False,
                'error': 'ref_unique é obrigatório'
            }), 400
        
        # Usar nome original se display_name não fornecido
        if not display_name:
            display_name = secure_filename(file.filename)
        
        # Fazer upload
        result = document_service.upload_document(
            file=file,
            ref_unique=ref_unique,
            display_name=display_name,
            user_email=user_email,
            description=description,
            visible_to_client=visible_to_client
        )
        
        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500

@documents_bp.route('/process/<path:ref_unique>', methods=['GET'])
@api_auth_required
def get_process_documents(ref_unique):
    """
    Lista documentos de um processo
    Filtra por permissão do usuário
    """
    try:
        print(f"[DOC DEBUG] Iniciando get_process_documents para ref_unique: {ref_unique}")
        
        # Verificar se é bypass key
        api_bypass_key = os.getenv('API_BYPASS_KEY')
        request_api_key = request.headers.get('X-API-Key')
        
        if api_bypass_key and request_api_key == api_bypass_key:
            print(f"[DOC DEBUG] Usando bypass - admin acesso total")
            result = document_service.get_process_documents(
                ref_unique=ref_unique,
                user_role='admin',
                user_companies=[]
            )
        else:
            # Usuário logado normal
            user_info = get_user_info()
            print(f"[DOC DEBUG] user_info recebido: {user_info}")
            
            user_role = user_info.get('role')
            user_companies = user_info.get('companies', [])
            
            print(f"[DOC DEBUG] Role: {user_role}, Companies: {user_companies}")
            
            result = document_service.get_process_documents(
                ref_unique=ref_unique,
                user_role=user_role,
                user_companies=user_companies
            )
        
        print(f"[DOC DEBUG] Resultado do service: {result}")
        
        if result['success']:
            return jsonify(result)
        else:
            # Verificar se é erro de token expirado
            error_msg = str(result.get('error', ''))
            if 'JWT expired' in error_msg or 'PGRST301' in error_msg:
                print(f"[DOC DEBUG] Token expirado detectado: {error_msg}")
                return jsonify({
                    'success': False,
                    'error': 'Sessão expirada. Por favor, faça login novamente.',
                    'code': 'session_expired'
                }), 401
            
            return jsonify(result), 400
            
    except Exception as e:
        print(f"[DOC DEBUG] Erro na função get_process_documents: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500

@documents_bp.route('/<document_id>/download', methods=['GET'])
@login_required
def download_document(document_id):
    """
    Download de documento
    Gera URL de download temporária do Supabase Storage
    """
    try:
        user_info = get_user_info()
        user_role = user_info.get('role')
        user_companies = user_info.get('companies', [])
        
        result = document_service.get_download_url(
            document_id=document_id,
            user_role=user_role,
            user_companies=user_companies
        )
        
        if result['success']:
            # Retornar a URL para o frontend fazer o download
            return jsonify({
                'success': True,
                'download_url': result['url'],
                'filename': result['filename'],
                'mime_type': result['mime_type']
            })
        else:
            return jsonify(result), 403
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500

@documents_bp.route('/<document_id>/update', methods=['PUT'])
@login_required
def update_document(document_id):
    """
    Atualiza informações do documento
    Todas as roles podem editar documentos
    """
    try:
        user_info = get_user_info()
        user_role = user_info.get('role')
        
        # Verificar permissão - TODAS as roles podem editar
        if user_role not in ['admin', 'interno_unique', 'cliente_unique']:
            return jsonify({
                'success': False,
                'error': 'Acesso negado. Role não autorizada.'
            }), 403
        
        data = request.get_json()
        
        result = document_service.update_document_info(
            document_id=document_id,
            display_name=data.get('display_name'),
            description=data.get('description'),
            visible_to_client=data.get('visible_to_client')
        )
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500

@documents_bp.route('/<document_id>/delete', methods=['DELETE'])
@login_required
def delete_document(document_id):
    """
    Remove documento (soft delete)
    TODAS as roles podem remover documentos
    """
    try:
        user_info = get_user_info()
        user_role = user_info.get('role')
        
        # Verificar permissão - TODAS as roles podem deletar
        if user_role not in ['admin', 'interno_unique', 'cliente_unique']:
            return jsonify({
                'success': False,
                'error': 'Acesso negado. Role não autorizada.'
            }), 403
        
        result = document_service.delete_document(document_id)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500

@documents_bp.route('/test-upload', methods=['GET'])
def test_upload_form():
    """
    Página de teste para upload (desenvolvimento)
    """
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Document Upload</title>
    </head>
    <body>
        <h2>Test Document Upload</h2>
        <form action="/api/documents/upload" method="post" enctype="multipart/form-data">
            <p>
                <label>Arquivo:</label><br>
                <input type="file" name="file" required>
            </p>
            <p>
                <label>Ref Unique:</label><br>
                <input type="text" name="ref_unique" value="UN25/0001" required>
            </p>
            <p>
                <label>Nome de Exibição:</label><br>
                <input type="text" name="display_name" placeholder="Deixe vazio para usar nome original">
            </p>
            <p>
                <label>Descrição:</label><br>
                <textarea name="description" rows="3" cols="50"></textarea>
            </p>
            <p>
                <label>
                    <input type="checkbox" name="visible_to_client" value="true" checked>
                    Visível para cliente
                </label>
            </p>
            <p>
                <button type="submit">Enviar</button>
            </p>
        </form>
    </body>
    </html>
    '''

# Função para registrar blueprint
def register_documents_blueprint(app):
    """Registra blueprint de documentos na aplicação"""
    app.register_blueprint(documents_bp)
