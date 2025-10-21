"""
Upload de Foto do Colaborador

Bucket Supabase: rh-colaboradores-fotos
Pasta: {empresa_id}/{colaborador_id}/

Estrutura:
- rh-colaboradores-fotos/
  ├── dc984b7c-3156-43f7-a1bf-f7a0b77db535/  (Unique)
  │   ├── a5957ffd-a71f-4022-94aa-3d5969379bac/
  │   │   └── foto_perfil.jpg
  │   └── ...outros colaboradores...
  ├── 2d025a9f-67a0-44a8-81a7-21fdea851c5d/  (DUX)
  └── ...outras empresas...
"""

from flask import Blueprint, request, jsonify, session
from extensions import supabase_admin
from modules.auth.routes import login_required
from decorators.perfil_decorators import perfil_required
import os
import mimetypes
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Configurações
BUCKET_NAME = 'rh-colaboradores-fotos'
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
SUPPORTED_MIMETYPES = {'image/jpeg', 'image/png', 'image/gif'}


def allowed_file(filename):
    """Validar extensão do arquivo"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_file_extension(filename):
    """Obter extensão do arquivo"""
    return filename.rsplit('.', 1)[1].lower() if '.' in filename else 'jpg'


def upload_foto_colaborador(colaborador_id, empresa_id, file):
    """
    Upload de foto do colaborador
    
    Args:
        colaborador_id: UUID do colaborador
        empresa_id: UUID da empresa
        file: Objeto de arquivo do Flask
        
    Returns:
        dict: {
            'success': bool,
            'path': str (caminho no bucket),
            'url': str (URL pública),
            'message': str
        }
    """
    try:
        # Validações
        if not file or file.filename == '':
            return {'success': False, 'message': 'Nenhum arquivo selecionado'}
        
        if not allowed_file(file.filename):
            return {'success': False, 'message': 'Tipo de arquivo não permitido. Use JPG, PNG ou GIF'}
        
        # Ler conteúdo
        file_content = file.read()
        
        if len(file_content) > MAX_FILE_SIZE:
            return {'success': False, 'message': 'Arquivo muito grande. Máximo de 5MB'}
        
        # Construir caminho
        ext = get_file_extension(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_name = f'foto_{timestamp}.{ext}'
        file_path = f'{empresa_id}/{colaborador_id}/{file_name}'
        
        # Upload via Supabase Storage
        response = supabase_admin.storage.from_(BUCKET_NAME).upload(
            file_path,
            file_content,
            file_options={
                'content-type': file.content_type,
                'x-upsert': 'false'  # Não sobrescrever
            }
        )
        
        # Gerar URL pública
        public_url = supabase_admin.storage.from_(BUCKET_NAME).get_public_url(file_path)
        
        # Atualizar coluna foto_colab na tabela
        supabase_admin.table('rh_colaboradores').update({
            'foto_colab': public_url,
            'updated_at': datetime.utcnow().isoformat()
        }).eq('id', colaborador_id).execute()
        
        logger.info(f'✅ Foto enviada: {colaborador_id} - {file_path}')
        
        return {
            'success': True,
            'path': file_path,
            'url': public_url,
            'message': 'Foto enviada com sucesso!'
        }
        
    except Exception as e:
        logger.error(f'❌ Erro ao fazer upload: {str(e)}')
        return {
            'success': False,
            'message': f'Erro ao fazer upload: {str(e)}'
        }


def delete_foto_colaborador(colaborador_id, empresa_id, file_path):
    """
    Deletar foto do colaborador
    
    Args:
        colaborador_id: UUID do colaborador
        empresa_id: UUID da empresa
        file_path: Caminho do arquivo no bucket
        
    Returns:
        dict: {'success': bool, 'message': str}
    """
    try:
        # Deletar do Supabase Storage
        supabase_admin.storage.from_(BUCKET_NAME).remove([file_path])
        
        # Limpar coluna foto_colab
        supabase_admin.table('rh_colaboradores').update({
            'foto_colab': None,
            'updated_at': datetime.utcnow().isoformat()
        }).eq('id', colaborador_id).execute()
        
        logger.info(f'✅ Foto deletada: {colaborador_id} - {file_path}')
        
        return {
            'success': True,
            'message': 'Foto removida com sucesso!'
        }
        
    except Exception as e:
        logger.error(f'❌ Erro ao deletar foto: {str(e)}')
        return {
            'success': False,
            'message': f'Erro ao deletar foto: {str(e)}'
        }


def get_lista_fotos_colaborador(colaborador_id, empresa_id):
    """
    Listar todas as fotos do colaborador
    
    Returns:
        dict: {'success': bool, 'fotos': list, 'message': str}
    """
    try:
        path = f'{empresa_id}/{colaborador_id}'
        fotos = supabase_admin.storage.from_(BUCKET_NAME).list(path)
        
        return {
            'success': True,
            'fotos': fotos,
            'message': f'{len(fotos)} fotos encontradas'
        }
        
    except Exception as e:
        logger.error(f'❌ Erro ao listar fotos: {str(e)}')
        return {
            'success': False,
            'fotos': [],
            'message': f'Erro ao listar fotos: {str(e)}'
        }
