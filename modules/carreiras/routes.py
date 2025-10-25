"""
Blueprint: Portal Público de Carreiras
Rotas para candidaturas externas (sem autenticação)
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from extensions import supabase_admin
from werkzeug.utils import secure_filename
import json
import os
import uuid
from datetime import datetime
import requests

# Criar Blueprint PÚBLICO (sem url_prefix de módulo interno)
carreiras_bp = Blueprint(
    'carreiras',
    __name__,
    url_prefix='/carreiras',
    template_folder='templates',
    static_folder='static'
)

# Configurações
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}
WEBHOOK_N8N_URL = os.getenv('WEBHOOK_N8N_URL')  # URL do webhook n8n
API_SECRET_KEY = os.getenv('API_SECRET_KEY_IA')  # Chave para proteger endpoint de IA
UNIQUE_EMPRESA_ID = 'dc984b7c-3156-43f7-a1bf-f7a0b77db535'  # Unique Aduaneira


def allowed_file(filename):
    """Verifica se o arquivo tem extensão permitida"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ========================================
# ROTAS PÚBLICAS - PORTAL DE VAGAS
# ========================================

@carreiras_bp.route('/')
def portal_vagas():
    """Página pública com lista de vagas abertas (somente Unique)"""
    try:
        # ID da empresa Unique (portal público mostra apenas vagas da Unique)
        UNIQUE_ID = 'dc984b7c-3156-43f7-a1bf-f7a0b77db535'
        
        # Buscar apenas vagas abertas da Unique
        response = supabase_admin.table('rh_vagas')\
            .select('id, titulo, localizacao, tipo_contratacao, data_abertura, descricao')\
            .eq('status', 'Aberta')\
            .eq('empresa_controladora_id', UNIQUE_ID)\
            .order('data_abertura', desc=True)\
            .execute()
        
        vagas = response.data if response.data else []
        
        return render_template('carreiras/portal_vagas.html', vagas=vagas)
    
    except Exception as e:
        print(f"❌ Erro ao carregar vagas públicas: {str(e)}")
        return render_template('carreiras/portal_vagas.html', vagas=[])


@carreiras_bp.route('/<uuid:vaga_id>')
def detalhe_vaga(vaga_id):
    """Página pública com detalhes da vaga e formulário de candidatura"""
    try:
        # Buscar detalhes da vaga
        response = supabase_admin.table('rh_vagas')\
            .select('*')\
            .eq('id', str(vaga_id))\
            .execute()
        
        if not response.data or len(response.data) == 0:
            return render_template('carreiras/vaga_nao_encontrada.html'), 404
        
        vaga = response.data[0]

        def _split_text(value):
            if not value:
                return []
            if isinstance(value, list):
                return [item.strip() for item in value if isinstance(item, str) and item.strip()]
            linhas = []
            for linha in str(value).splitlines():
                texto = linha.strip().lstrip('•-*–—')
                if texto:
                    linhas.append(texto)
            return linhas

        beneficios_raw = vaga.get('beneficios')
        beneficios_list = []
        if isinstance(beneficios_raw, str):
            try:
                parsed = json.loads(beneficios_raw)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, list):
                beneficios_list = [item.strip() for item in parsed if isinstance(item, str) and item.strip()]
            else:
                beneficios_list = _split_text(beneficios_raw)
        elif isinstance(beneficios_raw, list):
            beneficios_list = [item.strip() for item in beneficios_raw if isinstance(item, str) and item.strip()]

        vaga['beneficios_list'] = beneficios_list
        vaga['requisitos_obrigatorios_list'] = _split_text(vaga.get('requisitos_obrigatorios'))
        vaga['requisitos_desejaveis_list'] = _split_text(vaga.get('requisitos_desejaveis'))
        vaga['diferenciais_list'] = _split_text(vaga.get('diferenciais'))

        quantidade = vaga.get('quantidade_vagas')
        quantidade_formatada = None
        try:
            if quantidade is not None:
                quantidade_int = int(quantidade)
                if quantidade_int > 0:
                    sufixo = 's' if quantidade_int > 1 else ''
                    quantidade_formatada = f"{quantidade_int} vaga{sufixo}"
        except (TypeError, ValueError):
            quantidade_formatada = None

        vaga['quantidade_vagas_display'] = quantidade_formatada
        
        # Se a vaga não está aberta, mostrar mensagem
        if vaga.get('status') != 'Aberta':
            return render_template('carreiras/vaga_encerrada.html', vaga=vaga)
        
        return render_template('carreiras/detalhe_vaga.html', vaga=vaga)
    
    except Exception as e:
        print(f"❌ Erro ao carregar detalhes da vaga: {str(e)}")
        return render_template('carreiras/erro.html'), 500


@carreiras_bp.route('/<uuid:vaga_id>/aplicar', methods=['POST'])
def aplicar_vaga(vaga_id):
    """Endpoint público para candidatura (com upload de currículo)"""
    try:
        # 1. Validar dados do formulário
        nome_completo = request.form.get('nome_completo', '').strip()
        email = request.form.get('email', '').strip()
        telefone = request.form.get('telefone', '').strip()
        linkedin_url = request.form.get('linkedin_url', '').strip()
        
        if not nome_completo or not email:
            return jsonify({
                'success': False,
                'message': 'Nome e e-mail são obrigatórios'
            }), 400
        
        # 2. Verificar se já existe candidatura
        check_response = supabase_admin.table('rh_candidatos')\
            .select('id')\
            .eq('vaga_id', str(vaga_id))\
            .eq('email', email)\
            .execute()
        
        if check_response.data and len(check_response.data) > 0:
            return jsonify({
                'success': False,
                'message': 'Você já se candidatou para esta vaga anteriormente'
            }), 409
        
        # 3. Upload do currículo no Supabase Storage
        curriculo_path = None
        if 'curriculo' in request.files:
            file = request.files['curriculo']
            
            if file and file.filename and allowed_file(file.filename):
                # Gerar nome único para o arquivo
                file_extension = file.filename.rsplit('.', 1)[1].lower()
                unique_filename = f"{uuid.uuid4()}.{file_extension}"
                
                try:
                    # Upload para Supabase Storage bucket 'curriculos'
                    file_content = file.read()
                    storage_response = supabase_admin.storage\
                        .from_('curriculos')\
                        .upload(unique_filename, file_content, {
                            'content-type': file.content_type,
                            'x-upsert': 'false'
                        })
                    
                    curriculo_path = unique_filename
                    print(f"✅ Currículo salvo: {curriculo_path}")
                
                except Exception as storage_error:
                    print(f"❌ Erro ao fazer upload do currículo: {str(storage_error)}")
                    # Continuar mesmo se o upload falhar
        
        # 4. Criar registro do candidato com status IA = 'Pendente'
        candidato_data = {
            'vaga_id': str(vaga_id),
            'nome_completo': nome_completo,
            'email': email,
            'telefone': telefone,
            'linkedin_url': linkedin_url if linkedin_url else None,
            'curriculo_path': curriculo_path,
            'status_processo': 'Triagem',
            'fonte_candidatura': 'Portal de Vagas',
            'ai_status': 'Pendente',
            'data_candidatura': datetime.now().isoformat(),
            'empresa_controladora_id': UNIQUE_EMPRESA_ID
        }
        
        insert_response = supabase_admin.table('rh_candidatos')\
            .insert(candidato_data)\
            .execute()
        
        if not insert_response.data or len(insert_response.data) == 0:
            return jsonify({
                'success': False,
                'message': 'Erro ao processar candidatura'
            }), 500
        
        candidato_id = insert_response.data[0]['id']
        
        # 5. Gerar URL PÚBLICA PERMANENTE do currículo (sem expiração)
        curriculo_url_publica = None
        if curriculo_path:
            try:
                # Gera URL pública PERMANENTE (sem expiração)
                curriculo_url_publica = supabase_admin.storage\
                    .from_('curriculos')\
                    .get_public_url(curriculo_path)
                
                print(f"✅ URL pública permanente gerada: {curriculo_url_publica}")
                
                # ATUALIZAR o candidato com a URL permanente
                supabase_admin.table('rh_candidatos')\
                    .update({'url_curriculo': curriculo_url_publica})\
                    .eq('id', candidato_id)\
                    .execute()
                
                print(f"✅ URL salva no banco para candidato {candidato_id}")
            
            except Exception as url_error:
                print(f"⚠️  Erro ao gerar URL pública: {str(url_error)}")
        
        # 6. Disparar webhook para n8n (processamento assíncrono com IA)
        if WEBHOOK_N8N_URL and curriculo_path:
            try:
                webhook_payload = {
                    'candidato_id': candidato_id,
                    'vaga_id': str(vaga_id),
                    'curriculo_path': curriculo_path,
                    'curriculo_url': curriculo_url_publica,  # URL PÚBLICA PERMANENTE
                    'email': email,
                    'nome_completo': nome_completo,
                    'telefone': telefone if telefone else None,
                    'linkedin_url': linkedin_url if linkedin_url else None
                }
                
                webhook_response = requests.post(
                    WEBHOOK_N8N_URL,
                    json=webhook_payload,
                    timeout=5
                )
                
                if webhook_response.status_code == 200:
                    print(f"✅ Webhook n8n disparado para candidato {candidato_id}")
                    print(f"   URL pública enviada: {curriculo_url_publica[:80] if curriculo_url_publica else 'N/A'}...")
                    
                    # Atualizar status para 'Em Processamento'
                    supabase_admin.table('rh_candidatos')\
                        .update({'ai_status': 'Em Processamento'})\
                        .eq('id', candidato_id)\
                        .execute()
                else:
                    print(f"⚠️ Webhook n8n retornou status {webhook_response.status_code}")
            
            except Exception as webhook_error:
                print(f"⚠️ Erro ao disparar webhook: {str(webhook_error)}")
                # Não retornar erro para o usuário - o processamento pode ser feito manualmente
        
        # 7. Redirecionar para página de sucesso
        return redirect(url_for('carreiras.sucesso'))
    
    except Exception as e:
        print(f"❌ Erro ao processar candidatura: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Erro ao processar candidatura: {str(e)}'
        }), 500


@carreiras_bp.route('/sucesso')
def sucesso():
    """Página de sucesso após candidatura"""
    return render_template('carreiras/sucesso.html')


# ========================================
# API INTERNA - ENDPOINT PARA n8n ATUALIZAR CANDIDATO COM DADOS DA IA
# ========================================

@carreiras_bp.route('/api/candidatos/<uuid:candidato_id>/ia', methods=['PATCH'])
def atualizar_dados_ia(candidato_id):
    """
    Endpoint PROTEGIDO para o n8n enviar os dados processados pela IA
    Requer header: X-API-Secret-Key
    """
    # Validar chave de API
    api_key_header = request.headers.get('X-API-Secret-Key')
    
    if not api_key_header or api_key_header != API_SECRET_KEY:
        return jsonify({
            'success': False,
            'message': 'Não autorizado - chave de API inválida'
        }), 401
    
    try:
        data = request.get_json()
        
        # Extrair dados do payload
        match_score = data.get('match_score')
        pre_filter_status = data.get('pre_filter_status', 'Aprovado')
        extracted_data = data.get('extracted_data', {})
        
        # Preparar dados para atualização
        update_data = {
            'ai_status': 'Concluído',
            'ai_match_score': match_score,
            'ai_pre_filter_status': pre_filter_status,
            'ai_extracted_data_jsonb': extracted_data,
            'updated_at': datetime.now().isoformat()
        }
        
        # Se a IA extraiu telefone ou outros dados que estavam vazios, atualizar também
        if extracted_data.get('telefone') and not data.get('telefone_original'):
            update_data['telefone'] = extracted_data['telefone']
        
        # NOVOS CAMPOS DEMOGRÁFICOS (extraídos pela IA)
        if extracted_data.get('sexo'):
            update_data['sexo'] = extracted_data['sexo']
        
        if extracted_data.get('data_nascimento'):
            update_data['data_nascimento'] = extracted_data['data_nascimento']
        
        if extracted_data.get('estado_civil'):
            update_data['estado_civil'] = extracted_data['estado_civil']
        
        if extracted_data.get('cidade'):
            update_data['cidade'] = extracted_data['cidade']
        
        if extracted_data.get('estado'):
            update_data['estado'] = extracted_data['estado']
        
        # Formação e Experiência (extraídos pela IA)
        if extracted_data.get('formacao_academica'):
            update_data['formacao_academica'] = extracted_data['formacao_academica']
        
        if extracted_data.get('curso_especifico'):
            update_data['curso_especifico'] = extracted_data['curso_especifico']
        
        if extracted_data.get('area_objetivo'):
            update_data['area_objetivo'] = extracted_data['area_objetivo']
        
        if 'trabalha_atualmente' in extracted_data:
            update_data['trabalha_atualmente'] = extracted_data['trabalha_atualmente']
        
        if 'experiencia_na_area' in extracted_data:
            update_data['experiencia_na_area'] = extracted_data['experiencia_na_area']
        
        # Atualizar registro
        response = supabase_admin.table('rh_candidatos')\
            .update(update_data)\
            .eq('id', str(candidato_id))\
            .execute()
        
        if response.data and len(response.data) > 0:
            print(f"✅ Candidato {candidato_id} atualizado com dados da IA (Score: {match_score}%)")
            return jsonify({
                'success': True,
                'message': 'Dados da IA atualizados com sucesso',
                'candidato_id': candidato_id
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Candidato não encontrado'
            }), 404
    
    except Exception as e:
        print(f"❌ Erro ao atualizar dados da IA: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Marcar como erro
        try:
            supabase_admin.table('rh_candidatos')\
                .update({'ai_status': 'Erro'})\
                .eq('id', str(candidato_id))\
                .execute()
        except:
            pass
        
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
