"""
Document Management API Endpoints
Endpoints para gerenciamento de documentos dos processos
"""

from flask import Blueprint, request, jsonify, send_file, abort, session
from werkzeug.utils import secure_filename
import mimetypes
from datetime import datetime

from services.document_service import document_service
from routes.auth import login_required, role_required
from permissions import get_user_info
from extensions import supabase

# Blueprint para documentos
documents_bp = Blueprint('documents', __name__, url_prefix='/api/documents')

@documents_bp.route('/upload', methods=['POST'])
@login_required
def upload_document():
    """
    Upload de documento para um processo
    Apenas usuários admin/interno podem fazer upload
    """
    try:
        user_info = get_user_info()
        user_role = user_info.get('role')
        user_email = user_info.get('email')
        
        # Verificar permissão
        if user_role not in ['admin', 'interno_unique']:
            return jsonify({
                'success': False,
                'error': 'Acesso negado. Apenas usuários internos podem enviar documentos.'
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

@documents_bp.route('/process/<ref_unique>', methods=['GET'])
@login_required
def get_process_documents(ref_unique):
    """
    Lista documentos de um processo
    Filtra por permissão do usuário
    """
    try:
        user_info = get_user_info()
        user_role = user_info.get('role')
        user_companies = user_info.get('companies', [])
        
        result = document_service.get_process_documents(
            ref_unique=ref_unique,
            user_role=user_role,
            user_companies=user_companies
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
    Apenas usuários admin/interno podem editar
    """
    try:
        user_info = get_user_info()
        user_role = user_info.get('role')
        
        # Verificar permissão
        if user_role not in ['admin', 'interno_unique']:
            return jsonify({
                'success': False,
                'error': 'Acesso negado. Apenas usuários internos podem editar documentos.'
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
    Apenas usuários admin podem remover
    """
    try:
        user_info = get_user_info()
        user_role = user_info.get('role')
        
        # Verificar permissão (apenas admin)
        if user_role != 'admin':
            return jsonify({
                'success': False,
                'error': 'Acesso negado. Apenas administradores podem remover documentos.'
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
