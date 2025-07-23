"""
Document Management Service
Sistema de gerenciamento de documentos para processos
"""

import os
import uuid
import mimetypes
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage

from extensions import supabase, supabase_admin
from config import Config

class DocumentService:
    """Service para gerenciamento de documentos dos processos"""
    
    # Configurações
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS = {
        'pdf', 'jpg', 'jpeg', 'png', 'gif', 'webp',
        'xlsx', 'xls', 'docx', 'doc', 'txt', 'csv', 'zip'
    }
    ALLOWED_MIME_TYPES = {
        'application/pdf',
        'image/jpeg', 'image/png', 'image/gif', 'image/webp',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'text/plain', 'text/csv',
        'application/zip'
    }
    STORAGE_BUCKET = 'processos-documentos'

    def __init__(self):
        pass  # Inicialização simples sem dependências externas
    
    def validate_file(self, file: FileStorage) -> Tuple[bool, str]:
        """
        Valida arquivo antes do upload
        Returns: (is_valid, error_message)
        """
        if not file:
            return False, "Nenhum arquivo selecionado"
        
        if file.filename == '':
            return False, "Nome do arquivo não pode estar vazio"
        
        # Validar tamanho
        file.seek(0, 2)  # Vai para o final
        size = file.tell()
        file.seek(0)  # Volta para o início
        
        if size > self.MAX_FILE_SIZE:
            size_mb = size / (1024 * 1024)
            return False, f"Arquivo muito grande ({size_mb:.1f}MB). Máximo permitido: {self.MAX_FILE_SIZE // (1024 * 1024)}MB"
        
        # Validar extensão
        filename = secure_filename(file.filename)
        extension = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        
        if extension not in self.ALLOWED_EXTENSIONS:
            return False, f"Tipo de arquivo não permitido. Permitidos: {', '.join(self.ALLOWED_EXTENSIONS)}"
        
        # Validar MIME type usando mimetypes nativo do Python
        detected_mime, _ = mimetypes.guess_type(filename)
        
        if detected_mime not in self.ALLOWED_MIME_TYPES:
            return False, f"Tipo de conteúdo não permitido: {detected_mime}"
        
        return True, ""
    
    def generate_storage_path(self, ref_unique: str, filename: str) -> str:
        """Gera caminho único no storage"""
        now = datetime.now()
        year = now.strftime('%Y')
        month = now.strftime('%m')
        timestamp = now.strftime('%Y%m%d%H%M%S')
        
        # Sanitizar filename
        base_name = secure_filename(filename)
        name, ext = os.path.splitext(base_name)
        
        # Remover caracteres especiais e espaços
        clean_name = ''.join(c for c in name if c.isalnum() or c in '-_').lower()
        
        # Gerar nome único
        unique_filename = f"{clean_name}-{timestamp}{ext}"
        
        return f"{year}/{month}/{ref_unique}/{unique_filename}"
    
    def upload_document(self, file: FileStorage, ref_unique: str, 
                       display_name: str, user_email: str, 
                       description: str = "", visible_to_client: bool = True) -> Dict:
        """
        Faz upload do documento
        Returns: {"success": bool, "data": dict, "error": str}
        """
        try:
            # Validar arquivo
            is_valid, error_msg = self.validate_file(file)
            if not is_valid:
                return {"success": False, "error": error_msg}
            
            # Verificar se processo existe
            process_check = supabase.table('importacoes_processos')\
                .select('ref_unique')\
                .eq('ref_unique', ref_unique)\
                .execute()
            
            if not process_check.data:
                return {"success": False, "error": "Processo não encontrado"}
            
            # Gerar dados do arquivo
            filename = secure_filename(file.filename)
            storage_path = self.generate_storage_path(ref_unique, filename)
            
            file.seek(0, 2)
            file_size = file.tell()
            file.seek(0)
            
            mime_type, _ = mimetypes.guess_type(filename)
            if not mime_type:
                mime_type = 'application/octet-stream'
            
            extension = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
            
            # Upload para Supabase Storage
            upload_result = supabase_admin.storage.from_(self.STORAGE_BUCKET)\
                .upload(storage_path, file)
            
            if upload_result.get('error'):
                return {"success": False, "error": f"Erro no upload: {upload_result['error']}"}
            
            # Inserir no banco
            document_data = {
                'ref_unique': ref_unique,
                'nome_original': filename,
                'nome_exibicao': display_name or filename,
                'extensao': extension,
                'tamanho_bytes': file_size,
                'mime_type': mime_type,
                'storage_path': storage_path,
                'storage_bucket': self.STORAGE_BUCKET,
                'usuario_upload_email': user_email,
                'visivel_cliente': visible_to_client,
                'descricao': description
            }
            
            db_result = supabase_admin.table('documentos_processos')\
                .insert(document_data)\
                .execute()
            
            if db_result.data:
                return {
                    "success": True,
                    "data": db_result.data[0],
                    "message": "Documento enviado com sucesso!"
                }
            else:
                # Rollback: remover arquivo do storage
                supabase_admin.storage.from_(self.STORAGE_BUCKET)\
                    .remove([storage_path])
                return {"success": False, "error": "Erro ao salvar no banco de dados"}
                
        except Exception as e:
            return {"success": False, "error": f"Erro interno: {str(e)}"}
    
    def get_process_documents(self, ref_unique: str, user_role: str = None, 
                            user_companies: List[str] = None) -> Dict:
        """
        Busca documentos de um processo
        Returns: {"success": bool, "data": list, "error": str}
        """
        try:
            query = supabase.table('vw_documentos_processos_completa')\
                .select('*')\
                .eq('ref_unique', ref_unique)\
                .order('data_upload', desc=True)
            
            # Filtrar por permissão de cliente
            if user_role == 'cliente_unique':
                if not user_companies:
                    return {"success": False, "error": "Usuário sem empresas associadas"}
                
                query = query.in_('cnpj_importador', user_companies)\
                    .eq('visivel_cliente', True)
            
            result = query.execute()
            
            # Formatar dados
            documents = []
            for doc in result.data:
                documents.append({
                    'id': doc['id'],
                    'nome_exibicao': doc['nome_exibicao'],
                    'nome_original': doc['nome_original'],
                    'extensao': doc['extensao'],
                    'tamanho_formatado': doc['tamanho_formatado'],
                    'tamanho_bytes': doc['tamanho_bytes'],
                    'mime_type': doc['mime_type'],
                    'data_upload': doc['data_upload'],
                    'usuario_upload_email': doc['usuario_upload_email'],
                    'visivel_cliente': doc['visivel_cliente'],
                    'descricao': doc['descricao'],
                    'download_url': f"/api/documents/{doc['id']}/download"
                })
            
            return {"success": True, "data": documents}
            
        except Exception as e:
            return {"success": False, "error": f"Erro ao buscar documentos: {str(e)}"}
    
    def get_download_url(self, document_id: str, user_role: str = None, 
                        user_companies: List[str] = None) -> Dict:
        """
        Gera URL de download segura
        Returns: {"success": bool, "url": str, "error": str}
        """
        try:
            # Buscar documento
            query = supabase.table('vw_documentos_processos_completa')\
                .select('*')\
                .eq('id', document_id)
            
            # Filtrar por permissão
            if user_role == 'cliente_unique':
                if not user_companies:
                    return {"success": False, "error": "Acesso negado"}
                
                query = query.in_('cnpj_importador', user_companies)\
                    .eq('visivel_cliente', True)
            
            result = query.execute()
            
            if not result.data:
                return {"success": False, "error": "Documento não encontrado ou sem permissão"}
            
            document = result.data[0]
            
            # Gerar URL de download temporária (1 hora)
            download_url = supabase_admin.storage.from_(self.STORAGE_BUCKET)\
                .create_signed_url(document['storage_path'], 3600)  # 1 hora
            
            if download_url.get('error'):
                return {"success": False, "error": "Erro ao gerar URL de download"}
            
            return {
                "success": True,
                "url": download_url['signedURL'],
                "filename": document['nome_exibicao'],
                "mime_type": document['mime_type']
            }
            
        except Exception as e:
            return {"success": False, "error": f"Erro interno: {str(e)}"}
    
    def update_document_info(self, document_id: str, display_name: str = None,
                           description: str = None, visible_to_client: bool = None) -> Dict:
        """
        Atualiza informações do documento
        Returns: {"success": bool, "data": dict, "error": str}
        """
        try:
            update_data = {}
            
            if display_name is not None:
                update_data['nome_exibicao'] = display_name
            if description is not None:
                update_data['descricao'] = description
            if visible_to_client is not None:
                update_data['visivel_cliente'] = visible_to_client
            
            if not update_data:
                return {"success": False, "error": "Nenhum dado para atualizar"}
            
            result = supabase_admin.table('documentos_processos')\
                .update(update_data)\
                .eq('id', document_id)\
                .execute()
            
            if result.data:
                return {"success": True, "data": result.data[0]}
            else:
                return {"success": False, "error": "Documento não encontrado"}
                
        except Exception as e:
            return {"success": False, "error": f"Erro ao atualizar: {str(e)}"}
    
    def delete_document(self, document_id: str) -> Dict:
        """
        Remove documento (soft delete)
        Returns: {"success": bool, "message": str, "error": str}
        """
        try:
            # Buscar documento
            doc_result = supabase_admin.table('documentos_processos')\
                .select('storage_path')\
                .eq('id', document_id)\
                .execute()
            
            if not doc_result.data:
                return {"success": False, "error": "Documento não encontrado"}
            
            storage_path = doc_result.data[0]['storage_path']
            
            # Soft delete no banco
            delete_result = supabase_admin.table('documentos_processos')\
                .update({'ativo': False})\
                .eq('id', document_id)\
                .execute()
            
            # Opcional: remover arquivo físico do storage
            # supabase_admin.storage.from_(self.STORAGE_BUCKET).remove([storage_path])
            
            return {"success": True, "message": "Documento removido com sucesso"}
            
        except Exception as e:
            return {"success": False, "error": f"Erro ao remover: {str(e)}"}

# Instância global do serviço
document_service = DocumentService()
