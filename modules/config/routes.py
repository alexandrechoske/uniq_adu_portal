from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, session
from routes.auth import login_required, role_required
from extensions import supabase_admin
from services.retry_utils import run_with_retries
import os
import uuid
import re
import unicodedata
import json
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

@config_bp.route('/test-clientes')
@login_required
@role_required(['admin'])
def test_clientes():
    """Página de teste do CRUD de clientes"""
    return render_template('test_clientes.html')

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
    """API para listar CNPJs disponíveis (não atrelados a clientes)"""
    try:
        # Usar view que mostra apenas CNPJs disponíveis
        response = supabase_admin.table('vw_cnpjs_disponiveis').select('cnpj, razao_social').order('razao_social').execute()
        
        return jsonify({
            'success': True,
            'data': response.data or []
        })
    except Exception as e:
        print(f"[CONFIG] Erro ao buscar CNPJs disponíveis: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@config_bp.route('/api/logos-clientes')
@login_required
@role_required(['admin'])
def api_logos_clientes():
    """API para listar clientes do sistema com seus CNPJs"""
    try:
        # Buscar clientes ativos com seus CNPJs em array (com retries)
        def _query():
            return supabase_admin.table('cad_clientes_sistema').select('*').eq('ativo', True).order('nome_cliente').execute()

        response = run_with_retries(
            'config.api_logos_clientes',
            _query,
            max_attempts=3,
            base_delay_seconds=0.8,
            should_retry=lambda e: 'Server disconnected' in str(e) or 'timeout' in str(e).lower()
        )

        # Processar dados para o frontend
        clientes_processados = []
        for cliente in (response.data or []):
            clientes_processados.append({
                'id': cliente.get('id'),
                'nome_cliente': cliente.get('nome_cliente'),
                'logo_url': cliente.get('logo_url'),
                'cnpjs': cliente.get('cnpjs') or [],
                'total_cnpjs_ativos': len(cliente.get('cnpjs') or []),
                'created_at': cliente.get('created_at'),
                'updated_at': cliente.get('updated_at')
            })

        # Guardar em sessão como fallback leve (não sensível)
        session['config_last_clientes'] = clientes_processados
        return jsonify({'success': True, 'data': clientes_processados})
    except Exception as e:
        print(f"[CONFIG] Erro ao buscar clientes do sistema: {e}")
        # Fallback: tentar retornar último resultado válido em sessão para não quebrar a página
        fallback = session.get('config_last_clientes', [])
        if fallback:
            print(f"[CONFIG] Retornando fallback de {len(fallback)} clientes do cache de sessão")
            return jsonify({'success': True, 'data': fallback, 'source': 'session_fallback'}), 200
        return jsonify({'success': False, 'error': str(e)}), 500

@config_bp.route('/api/logos-clientes', methods=['POST'])
@login_required
@role_required(['admin'])
def api_create_logo_cliente():
    """API para criar cliente do sistema com CNPJs"""
    try:
        data = request.get_json()
        print(f"[CONFIG] Dados recebidos: {data}")
        
        # Validar dados obrigatórios
        required_fields = ['nome_cliente', 'cnpjs']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    'success': False,
                    'error': f'Campo obrigatório: {field}'
                }), 400
        
        # Validar se é lista de CNPJs
        cnpjs = data.get('cnpjs', [])
        if not isinstance(cnpjs, list) or len(cnpjs) == 0:
            return jsonify({
                'success': False,
                'error': 'Pelo menos um CNPJ deve ser informado'
            }), 400
        
        # Validar e limpar CNPJs
        cnpjs_validos = []
        for cnpj in cnpjs:
            cnpj_limpo = re.sub(r'[^0-9]', '', str(cnpj))
            if len(cnpj_limpo) != 14:
                return jsonify({
                    'success': False,
                    'error': f'CNPJ inválido: {cnpj} (deve ter 14 dígitos)'
                }), 400
            cnpjs_validos.append(cnpj_limpo)
        
        # Criar cliente no sistema
        cliente_data = {
            'nome_cliente': data['nome_cliente'],
            'cnpjs': cnpjs_validos,  # Array de CNPJs
            'logo_url': data.get('logo_url', ''),
            'ativo': True
        }
        
        response = supabase_admin.table('cad_clientes_sistema').insert(cliente_data).execute()
        
        if not response.data:
            return jsonify({
                'success': False,
                'error': 'Erro ao criar cliente no banco de dados'
            }), 500
        
        cliente_criado = response.data[0]
        print(f"[CONFIG] Cliente criado com sucesso: {cliente_criado}")
        
        return jsonify({
            'success': True,
            'data': cliente_criado,
            'message': f'Cliente criado com {len(cnpjs_validos)} CNPJ(s) associado(s)'
        })
        
    except Exception as e:
        print(f"[CONFIG] Erro ao criar cliente: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@config_bp.route('/api/logos-clientes/<int:cliente_id>', methods=['PUT'])
@login_required
@role_required(['admin'])
def api_update_logo_cliente(cliente_id):
    """API para atualizar cliente do sistema"""
    try:
        data = request.get_json()
        print(f"[CONFIG] Atualizando cliente {cliente_id} com dados: {data}")
        
        # Validar dados obrigatórios
        if 'nome_cliente' not in data or not data['nome_cliente']:
            return jsonify({
                'success': False,
                'error': 'Nome do cliente é obrigatório'
            }), 400
        
        # Processar CNPJs se informados
        updates = {
            'nome_cliente': data['nome_cliente'],
            'logo_url': data.get('logo_url', ''),
            'ativo': data.get('ativo', True)
        }
        
        if 'cnpjs' in data:
            cnpjs = data['cnpjs']
            if isinstance(cnpjs, list):
                # Validar e limpar CNPJs
                cnpjs_validos = []
                for cnpj in cnpjs:
                    cnpj_limpo = re.sub(r'[^0-9]', '', str(cnpj))
                    if len(cnpj_limpo) != 14:
                        return jsonify({
                            'success': False,
                            'error': f'CNPJ inválido: {cnpj} (deve ter 14 dígitos)'
                        }), 400
                    cnpjs_validos.append(cnpj_limpo)
                
                updates['cnpjs'] = cnpjs_validos
        
        # Atualizar no banco de dados
        response = supabase_admin.table('cad_clientes_sistema').update(updates).eq('id', cliente_id).execute()
        
        if not response.data:
            return jsonify({
                'success': False,
                'error': 'Cliente não encontrado ou erro na atualização'
            }), 404
        
        cliente_atualizado = response.data[0]
        print(f"[CONFIG] Cliente atualizado: {cliente_atualizado}")
        
        return jsonify({
            'success': True,
            'data': cliente_atualizado,
            'message': 'Cliente atualizado com sucesso'
        })
        
    except Exception as e:
        print(f"[CONFIG] Erro ao atualizar cliente: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@config_bp.route('/api/logos-clientes/<int:cliente_id>', methods=['DELETE'])
@login_required
@role_required(['admin'])
def api_delete_logo_cliente(cliente_id):
    """API para excluir cliente do sistema"""
    try:
        print(f"[CONFIG] Excluindo cliente {cliente_id}")
        
        # Verificar se cliente existe
        check_response = supabase_admin.table('cad_clientes_sistema').select('id').eq('id', cliente_id).execute()
        
        if not check_response.data:
            return jsonify({
                'success': False,
                'error': 'Cliente não encontrado'
            }), 404
        
        # Excluir cliente
        response = supabase_admin.table('cad_clientes_sistema').delete().eq('id', cliente_id).execute()
        
        print(f"[CONFIG] Cliente excluído: {cliente_id}")
        
        return jsonify({
            'success': True,
            'message': 'Cliente excluído com sucesso'
        })
        
    except Exception as e:
        print(f"[CONFIG] Erro ao excluir cliente: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
@role_required(['admin'])
def api_delete_logo_cliente(cliente_id):
    """API para deletar cliente do sistema (cascata remove CNPJs associados)"""
    try:
        # Deletar cliente (cascata remove CNPJs via foreign key)
        response = supabase_admin.table('cad_clientes_sistema').delete().eq('id', cliente_id).execute()
        
        return jsonify({
            'success': True,
            'message': 'Cliente removido com sucesso'
        })
        
    except Exception as e:
        print(f"[CONFIG] Erro ao deletar cliente: {e}")
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
    """API para listar materiais disponíveis para cadastro de ícones"""
    try:
        # Buscar lista de materiais da view vw_aux_mercadorias (coluna mercadoria)
        response = supabase_admin.table('vw_aux_mercadorias').select('mercadoria').order('mercadoria').execute()
        return jsonify({
            'success': True,
            'data': response.data or []
        })
    except Exception as e:
        print(f"[CONFIG] Erro ao buscar materiais: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@config_bp.route('/api/icones-materiais', methods=['POST'])
@login_required
@role_required(['admin'])
def api_create_icone_material():
    """API para cadastrar novo material com ícone"""
    try:
        data = request.get_json()
        # Validar dados obrigatórios
        required_fields = ['nome_normalizado', 'icone_url']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'error': f'Campo {field} é obrigatório'
                }), 400
        # Inserir na tabela cad_materiais
        response = supabase_admin.table('cad_materiais').insert({
            'nome_normalizado': data['nome_normalizado'],
            'icone_url': data['icone_url']
        }).execute()
        return jsonify({
            'success': True,
            'data': response.data[0] if response.data else None
        })
    except Exception as e:
        print(f"[CONFIG] Erro ao cadastrar material: {e}")
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
        cliente_id = request.form.get('cliente_id')
        
        if not cliente_id:
            return jsonify({
                'success': False,
                'error': 'ID do cliente é obrigatório'
            }), 400
        
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'Nenhum arquivo selecionado'
            }), 400
        
        # Validar tipo de arquivo
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
        file_extension = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        
        if file_extension not in allowed_extensions:
            return jsonify({
                'success': False,
                'error': f'Tipo de arquivo não permitido. Use: {", ".join(allowed_extensions)}'
            }), 400
        
        # Gerar nome único para o arquivo
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        
        # Path no bucket: assets/logos_clientes/
        bucket_path = f"logos_clientes/{unique_filename}"
        
        # Upload para o Supabase Storage
        try:
            # Ler o conteúdo do arquivo
            file_content = file.read()
            
            print(f"[CONFIG] Iniciando upload para: {bucket_path}")
            print(f"[CONFIG] Tamanho do arquivo: {len(file_content)} bytes")
            
            # Upload para o bucket 'assets'
            upload_response = supabase_admin.storage.from_('assets').upload(
                path=bucket_path,
                file=file_content,
                file_options={
                    'content-type': f'image/{file_extension}',
                    'cache-control': '3600'
                }
            )
            
            print(f"[CONFIG] Upload response: {upload_response}")
            
            # Verificar se upload foi bem-sucedido
            if hasattr(upload_response, 'error') and upload_response.error:
                raise Exception(f"Erro no upload: {upload_response.error}")
            
            # Gerar URL pública
            public_url_response = supabase_admin.storage.from_('assets').get_public_url(bucket_path)
            
            # Verificar se a resposta é uma string (URL) ou objeto
            if isinstance(public_url_response, str):
                public_url = public_url_response
            elif hasattr(public_url_response, 'data'):
                public_url = public_url_response.data
            else:
                public_url = str(public_url_response)
            
            print(f"[CONFIG] URL pública gerada: {public_url}")
            
            # Atualizar cliente com a nova URL do logo
            update_response = supabase_admin.table('cad_clientes_sistema').update({
                'logo_url': public_url
            }).eq('id', cliente_id).execute()
            
            if not update_response.data:
                return jsonify({
                    'success': False,
                    'error': 'Erro ao atualizar cliente com nova URL do logo'
                }), 500
            
            return jsonify({
                'success': True,
                'data': {
                    'logo_url': public_url,
                    'filename': unique_filename,
                    'cliente': update_response.data[0]
                },
                'message': 'Logo enviado com sucesso!'
            })
            
        except Exception as storage_error:
            print(f"[CONFIG] Erro no storage: {storage_error}")
            return jsonify({
                'success': False,
                'error': f'Erro no upload: {str(storage_error)}'
            }), 500
        
    except Exception as e:
        print(f"[CONFIG] Erro geral no upload: {e}")
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
