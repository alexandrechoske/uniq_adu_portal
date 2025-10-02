from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, session
from routes.auth import login_required, role_required
from extensions import supabase_admin
import os
import uuid
import re
import unicodedata
from datetime import datetime

bp = Blueprint('config', __name__, url_prefix='/config')

@bp.route('/logos-clientes')
@login_required
@role_required(['admin'])
def logos_clientes():
    """Página de gerenciamento de Clientes"""
    return render_template('config/logos_clientes.html')

@bp.route('/api/cnpj-options')
@login_required
@role_required(['admin'])
def api_cnpj_options():
    """API para listar opções de CNPJ da view auxiliar"""
    try:
        response = supabase_admin.table('vw_aux_cnpj_importador').select('cnpj, razao_social').order('razao_social').execute()
        
        return jsonify({
            'success': True,
            'data': response.data or []
        })
    except Exception as e:
        print(f"[CONFIG] Erro ao buscar opções de CNPJ: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/api/logos-clientes')
@login_required
@role_required(['admin'])
def api_logos_clientes():
    """API para listar Clientes"""
    try:
        response = supabase_admin.table('cad_clientes').select('*').order('razao_social').execute()
        
        return jsonify({
            'success': True,
            'data': response.data or []
        })
    except Exception as e:
        print(f"[CONFIG] Erro ao buscar Clientes: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/api/logos-clientes', methods=['POST'])
@login_required
@role_required(['admin'])
def api_create_logo_cliente():
    """API para criar/atualizar logo de cliente"""
    try:
        data = request.get_json()
        cnpj = data.get('cnpj', '').strip()
        razao_social = data.get('razao_social', '').strip()
        logo_url = data.get('logo_url', '').strip()
        
        if not cnpj or not razao_social:
            return jsonify({
                'success': False,
                'error': 'CNPJ e Razão Social são obrigatórios'
            }), 400
        
        # Verificar se já existe
        existing = supabase_admin.table('cad_clientes').select('*').eq('cnpj', cnpj).execute()
        
        if existing.data:
            # Atualizar
            response = supabase_admin.table('cad_clientes').update({
                'razao_social': razao_social,
                'logo_url': logo_url
            }).eq('cnpj', cnpj).execute()
        else:
            # Criar
            response = supabase_admin.table('cad_clientes').insert({
                'cnpj': cnpj,
                'razao_social': razao_social,
                'logo_url': logo_url
            }).execute()
        
        return jsonify({
            'success': True,
            'data': response.data[0] if response.data else None
        })
        
    except Exception as e:
        print(f"[CONFIG] Erro ao salvar logo de cliente: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/api/logos-clientes/<cnpj>', methods=['DELETE'])
@login_required
@role_required(['admin'])
def api_delete_logo_cliente(cnpj):
    """API para deletar logo de cliente"""
    try:
        response = supabase_admin.table('cad_clientes').delete().eq('cnpj', cnpj).execute()
        
        return jsonify({
            'success': True,
            'message': 'Cliente removido com sucesso'
        })
        
    except Exception as e:
        print(f"[CONFIG] Erro ao deletar logo de cliente: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/icones-materiais')
@login_required
@role_required(['admin'])
def icones_materiais():
    """Página de gerenciamento de ícones de materiais"""
    return render_template('config/icones_materiais.html')

@bp.route('/api/mercadorias-options')
@login_required
@role_required(['admin'])
def api_mercadorias_options():
    """API para listar opções de mercadorias da view auxiliar"""
    try:
        response = supabase_admin.table('vw_aux_mercadorias').select('mercadoria').order('mercadoria').execute()
        
        return jsonify({
            'success': True,
            'data': response.data or []
        })
    except Exception as e:
        print(f"[CONFIG] Erro ao buscar opções de mercadorias: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/api/icones-materiais')
@login_required
@role_required(['admin'])
def api_icones_materiais():
    """API para listar ícones de materiais"""
    try:
        response = supabase_admin.table('cad_materiais').select('*').order('nome_normalizado').execute()
        
        return jsonify({
            'success': True,
            'data': response.data or []
        })
    except Exception as e:
        print(f"[CONFIG] Erro ao buscar ícones de materiais: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/api/icones-materiais', methods=['POST'])
@login_required
@role_required(['admin'])
def api_create_icone_material():
    """API para criar/atualizar ícone de material"""
    try:
        data = request.get_json()
        nome_normalizado = data.get('nome_normalizado', '').strip().lower()
        icone_url = data.get('icone_url', '').strip()
        
        if not nome_normalizado:
            return jsonify({
                'success': False,
                'error': 'Nome do material é obrigatório'
            }), 400
        
        # Normalizar o nome do material para garantir consistência
        # Remove acentos, caracteres especiais e múltiplos espaços
        nome_normalizado = unicodedata.normalize('NFD', nome_normalizado)
        nome_normalizado = re.sub(r'[\u0300-\u036f]', '', nome_normalizado)  # Remove acentos
        nome_normalizado = re.sub(r'[^a-z0-9\s]', '', nome_normalizado)      # Remove caracteres especiais
        nome_normalizado = re.sub(r'\s+', ' ', nome_normalizado).strip()     # Remove múltiplos espaços
        
        print(f"[CONFIG] Nome normalizado: '{nome_normalizado}'")
        
        # Verificar se já existe
        existing = supabase_admin.table('cad_materiais').select('*').eq('nome_normalizado', nome_normalizado).execute()
        
        if existing.data:
            # Atualizar
            response = supabase_admin.table('cad_materiais').update({
                'icone_url': icone_url
            }).eq('nome_normalizado', nome_normalizado).execute()
        else:
            # Criar
            response = supabase_admin.table('cad_materiais').insert({
                'nome_normalizado': nome_normalizado,
                'icone_url': icone_url
            }).execute()
        
        return jsonify({
            'success': True,
            'data': response.data[0] if response.data else None
        })
        
    except Exception as e:
        print(f"[CONFIG] Erro ao salvar ícone de material: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/api/icones-materiais/<int:material_id>', methods=['DELETE'])
@login_required
@role_required(['admin'])
def api_delete_icone_material(material_id):
    """API para deletar ícone de material"""
    try:
        response = supabase_admin.table('cad_materiais').delete().eq('id', material_id).execute()
        
        return jsonify({
            'success': True,
            'message': 'Material removido com sucesso'
        })
        
    except Exception as e:
        print(f"[CONFIG] Erro ao deletar ícone de material: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/api/upload-logo', methods=['POST'])
@login_required
@role_required(['admin'])
def api_upload_logo():
    """API para upload de logo via Supabase Storage"""
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'Nenhum arquivo enviado'
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'Nenhum arquivo selecionado'
            }), 400
        
        # Validar tipo de arquivo
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'svg'}
        file_extension = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        
        if file_extension not in allowed_extensions:
            return jsonify({
                'success': False,
                'error': f'Tipo de arquivo não permitido. Use: {", ".join(allowed_extensions)}'
            }), 400
        
        # Gerar nome único para o arquivo
        import uuid
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        storage_path = f"logos_clientes/{unique_filename}"
        
        # Upload para Supabase Storage
        file_content = file.read()
        
        print(f"[CONFIG] Fazendo upload de logo para: {storage_path}")
        print(f"[CONFIG] Tamanho do arquivo: {len(file_content)} bytes")
        
        # Upload usando supabase_admin
        response = supabase_admin.storage.from_('assets').upload(storage_path, file_content, {
            'content-type': file.content_type,
            'cache-control': '3600'
        })
        
        print(f"[CONFIG] Resposta do upload: {response}")
        
        # Verificar se houve erro no upload
        if hasattr(response, 'error') and response.error:
            print(f"[CONFIG] Erro no upload: {response.error}")
            return jsonify({
                'success': False,
                'error': f'Erro no upload: {response.error}'
            }), 500
        
        # Obter URL pública
        public_url = supabase_admin.storage.from_('assets').get_public_url(storage_path)
        
        print(f"[CONFIG] URL pública gerada: {public_url}")
        
        return jsonify({
            'success': True,
            'url': public_url
        })
        
    except Exception as e:
        print(f"[CONFIG] Erro no upload de logo: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
        
    except Exception as e:
        print(f"[CONFIG] Erro no upload de logo: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/api/upload-icone', methods=['POST'])
@login_required
@role_required(['admin'])
def api_upload_icone():
    """API para upload de ícone via Supabase Storage"""
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'Nenhum arquivo enviado'
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'Nenhum arquivo selecionado'
            }), 400
        
        # Validar tipo de arquivo
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'svg'}
        file_extension = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        
        if file_extension not in allowed_extensions:
            return jsonify({
                'success': False,
                'error': f'Tipo de arquivo não permitido. Use: {", ".join(allowed_extensions)}'
            }), 400
        
        # Gerar nome único para o arquivo
        import uuid
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        storage_path = f"icones_materiais/{unique_filename}"
        
        # Upload para Supabase Storage
        file_content = file.read()
        
        print(f"[CONFIG] Fazendo upload para: {storage_path}")
        print(f"[CONFIG] Tamanho do arquivo: {len(file_content)} bytes")
        
        # Upload usando supabase_admin
        response = supabase_admin.storage.from_('assets').upload(storage_path, file_content, {
            'content-type': file.content_type,
            'cache-control': '3600'
        })
        
        print(f"[CONFIG] Resposta do upload: {response}")
        
        # Verificar se houve erro no upload
        if hasattr(response, 'error') and response.error:
            print(f"[CONFIG] Erro no upload: {response.error}")
            return jsonify({
                'success': False,
                'error': f'Erro no upload: {response.error}'
            }), 500
        
        # Obter URL pública
        public_url = supabase_admin.storage.from_('assets').get_public_url(storage_path)
        
        print(f"[CONFIG] URL pública gerada: {public_url}")
        
        return jsonify({
            'success': True,
            'url': public_url
        })
        
    except Exception as e:
        print(f"[CONFIG] Erro no upload de ícone: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
