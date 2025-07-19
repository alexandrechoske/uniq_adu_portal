from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, session
from routes.auth import login_required, role_required
from extensions import supabase_admin
import os
import uuid
import re
import unicodedata
from datetime import datetime

# Criar blueprint com configuração modular
config_bp = Blueprint(
    'config', 
    __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/config/static',
    url_prefix='/config'
)

@config_bp.route('/logos-clientes')
@login_required
@role_required(['admin'])
def logos_clientes():
    """Página de gerenciamento de logos de clientes"""
    return render_template('logos_clientes.html')

@config_bp.route('/icones-materiais')
@login_required
@role_required(['admin'])
def icones_materiais():
    """Página de gerenciamento de ícones de materiais"""
    return render_template('icones_materiais.html')

@config_bp.route('/api/cnpj-options')
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

@config_bp.route('/api/logos-clientes')
@login_required
@role_required(['admin'])
def api_logos_clientes():
    """API para listar logos de clientes"""
    try:
        response = supabase_admin.table('cad_clientes').select('*').order('razao_social').execute()
        
        return jsonify({
            'success': True,
            'data': response.data or []
        })
    except Exception as e:
        print(f"[CONFIG] Erro ao buscar logos de clientes: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@config_bp.route('/api/logos-clientes', methods=['POST'])
@login_required
@role_required(['admin'])
def api_create_logo_cliente():
    """API para criar novo logo de cliente"""
    try:
        data = request.get_json()
        
        # Validar dados obrigatórios
        required_fields = ['cnpj', 'razao_social']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'error': f'Campo {field} é obrigatório'
                }), 400
        
        # Inserir no banco
        response = supabase_admin.table('cad_clientes').insert(data).execute()
        
        return jsonify({
            'success': True,
            'data': response.data[0] if response.data else None
        })
        
    except Exception as e:
        print(f"[CONFIG] Erro ao criar logo de cliente: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@config_bp.route('/api/logos-clientes/<cnpj>', methods=['DELETE'])
@login_required
@role_required(['admin'])
def api_delete_logo_cliente(cnpj):
    """API para deletar logo de cliente"""
    try:
        response = supabase_admin.table('cad_clientes').delete().eq('cnpj', cnpj).execute()
        
        return jsonify({
            'success': True,
            'message': 'Logo removido com sucesso'
        })
        
    except Exception as e:
        print(f"[CONFIG] Erro ao deletar logo de cliente: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@config_bp.route('/api/mercadorias-options')
@login_required
@role_required(['admin'])
def api_mercadorias_options():
    """API para listar opções de mercadorias"""
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

@config_bp.route('/api/icones-materiais')
@login_required
@role_required(['admin'])
def api_icones_materiais():
    """API para listar ícones de materiais"""
    try:
        response = supabase_admin.table('cad_icones_materiais').select('*').order('material').execute()
        
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

@config_bp.route('/api/icones-materiais', methods=['POST'])
@login_required
@role_required(['admin'])
def api_create_icone_material():
    """API para criar novo ícone de material"""
    try:
        data = request.get_json()
        
        # Validar dados obrigatórios
        required_fields = ['material', 'icone']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'error': f'Campo {field} é obrigatório'
                }), 400
        
        # Inserir no banco
        response = supabase_admin.table('cad_icones_materiais').insert(data).execute()
        
        return jsonify({
            'success': True,
            'data': response.data[0] if response.data else None
        })
        
    except Exception as e:
        print(f"[CONFIG] Erro ao criar ícone de material: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@config_bp.route('/api/icones-materiais/<int:material_id>', methods=['DELETE'])
@login_required
@role_required(['admin'])
def api_delete_icone_material(material_id):
    """API para deletar ícone de material"""
    try:
        response = supabase_admin.table('cad_icones_materiais').delete().eq('id', material_id).execute()
        
        return jsonify({
            'success': True,
            'message': 'Ícone removido com sucesso'
        })
        
    except Exception as e:
        print(f"[CONFIG] Erro ao deletar ícone de material: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@config_bp.route('/api/upload-logo', methods=['POST'])
@login_required
@role_required(['admin'])
def api_upload_logo():
    """API para upload de logo de cliente"""
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'Nenhum arquivo enviado'
            }), 400
        
        file = request.files['file']
        cnpj = request.form.get('cnpj')
        
        if not cnpj:
            return jsonify({
                'success': False,
                'error': 'CNPJ é obrigatório'
            }), 400
        
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'Nenhum arquivo selecionado'
            }), 400
        
        # Validar tipo de arquivo
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'svg'}
        if not ('.' in file.filename and 
                file.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
            return jsonify({
                'success': False,
                'error': 'Tipo de arquivo não permitido'
            }), 400
        
        # Processar upload (implementar lógica de salvamento)
        # Por enquanto, retornar sucesso simulado
        return jsonify({
            'success': True,
            'message': 'Logo carregado com sucesso',
            'file_url': f'/static/logos/{cnpj}.png'  # URL simulada
        })
        
    except Exception as e:
        print(f"[CONFIG] Erro no upload de logo: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@config_bp.route('/api/upload-icone', methods=['POST'])
@login_required
@role_required(['admin'])
def api_upload_icone():
    """API para upload de ícone de material"""
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'Nenhum arquivo enviado'
            }), 400
        
        file = request.files['file']
        material = request.form.get('material')
        
        if not material:
            return jsonify({
                'success': False,
                'error': 'Material é obrigatório'
            }), 400
        
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'Nenhum arquivo selecionado'
            }), 400
        
        # Validar tipo de arquivo
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'svg'}
        if not ('.' in file.filename and 
                file.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
            return jsonify({
                'success': False,
                'error': 'Tipo de arquivo não permitido'
            }), 400
        
        # Processar upload (implementar lógica de salvamento)
        # Por enquanto, retornar sucesso simulado
        return jsonify({
            'success': True,
            'message': 'Ícone carregado com sucesso',
            'file_url': f'/static/icones/{material}.png'  # URL simulada
        })
        
    except Exception as e:
        print(f"[CONFIG] Erro no upload de ícone: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Funções auxiliares
def normalize_string(s):
    """Normaliza string removendo acentos e caracteres especiais"""
    return ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))

def validate_cnpj(cnpj):
    """Valida formato de CNPJ"""
    cnpj = re.sub(r'[^0-9]', '', cnpj)
    return len(cnpj) == 14
