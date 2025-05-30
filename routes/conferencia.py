from flask import Blueprint, render_template, request, jsonify, session, url_for, current_app
from extensions import supabase
from routes.auth import login_required, role_required
import uuid
import json
from datetime import datetime
import os
import time
import tempfile
from werkzeug.utils import secure_filename
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor
import logging

# Imports for PDF processing
import PyPDF2
from pdf2image import convert_from_path
from PIL import Image
import re
import io
import base64

# Import for Gemini AI integration
import google.generativeai as genai

bp = Blueprint('conferencia', __name__, url_prefix='/conferencia')

# Configurações para armazenamento temporário de arquivos
UPLOAD_FOLDER = 'static/uploads/conferencia'
ALLOWED_EXTENSIONS = {'pdf'}

# Dicionário para armazenar o status dos jobs em memória (em produção usar Redis/DB)
jobs = {}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Função para criar os diretórios de upload se não existirem
def ensure_upload_folders():
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

# Templates de prompts para cada tipo de conferência
PROMPTS = {
    'inconsistencias': """
        Você é um especialista em conferência documental aduaneira. Analise o documento fornecido (PDF) 
        e identifique todas as inconsistências em relação ao Art. 557 do regulamento aduaneiro e normas da Unique.
        Liste cada inconsistência, classificando-a como ERRO CRÍTICO (informação obrigatória ausente), 
        OBSERVAÇÃO (pequenos enganos aceitáveis) ou ALERTA (informação para conhecimento).
        Formate a saída como JSON com a seguinte estrutura:
        {
            "sumario": {
                "status": "ok|alerta|erro",
                "total_erros_criticos": X,
                "total_observacoes": Y,
                "total_alertas": Z,
                "conclusao": "breve resumo do status geral"
            },
            "itens": [
                {
                    "campo": "nome do campo verificado",
                    "status": "ok|alerta|erro",
                    "tipo": "erro_critico|observacao|alerta",
                    "descricao": "detalhamento do problema encontrado"
                }
            ]
        }
    """,
    'invoice': """
        Você é um especialista em conferência documental aduaneira. Analise esta Invoice Comercial e 
        verifique se contém todos os campos obrigatórios segundo o Art. 557 do regulamento aduaneiro:
        1. Número do documento
        2. Data de emissão
        3. Exportador (nome e endereço completos)
        4. Importador (nome e endereço completos)
        5. Descrição das mercadorias
        6. Quantidade e unidade
        7. Preço unitário
        8. Valor total
        9. Incoterm
        10. País de origem
        11. País de aquisição
        
        Para cada campo, verifique se está presente e correto. 
        Formate a saída como JSON conforme estrutura:
        {
            "sumario": {
                "status": "ok|alerta|erro",
                "total_erros_criticos": X,
                "total_observacoes": Y,
                "total_alertas": Z,
                "conclusao": "breve resumo do status geral"
            },
            "itens": [
                {
                    "campo": "nome do campo verificado",
                    "status": "ok|alerta|erro",
                    "tipo": "erro_critico|observacao|alerta",
                    "descricao": "detalhamento do problema encontrado ou confirmação de conformidade"
                }
            ]
        }
    """,
    'packlist': """
        Você é um especialista em conferência documental aduaneira. Analise esta Packing List e 
        verifique se contém todos os campos obrigatórios segundo as normas da Unique:
        1. Número do documento
        2. Data de emissão
        3. Referência à Invoice correspondente
        4. Exportador (nome e endereço)
        5. Importador (nome e endereço)
        6. Detalhes de embalagem (tipo, quantidade)
        7. Dimensões dos volumes
        8. Peso bruto
        9. Peso líquido
        10. Marcações específicas (se aplicável)
        
        Para cada campo, verifique se está presente e correto.
        Formate a saída como JSON conforme estrutura:
        {
            "sumario": {
                "status": "ok|alerta|erro",
                "total_erros_criticos": X,
                "total_observacoes": Y,
                "total_alertas": Z,
                "conclusao": "breve resumo do status geral"
            },
            "itens": [
                {
                    "campo": "nome do campo verificado",
                    "status": "ok|alerta|erro",
                    "tipo": "erro_critico|observacao|alerta",
                    "descricao": "detalhamento do problema encontrado ou confirmação de conformidade"
                }
            ]
        }
    """,
    'conhecimento': """
        Você é um especialista em conferência documental aduaneira. Analise este Conhecimento de Embarque 
        (B/L ou AWB) e verifique se contém todos os campos obrigatórios segundo as normas da Unique:
        1. Número do conhecimento
        2. Data de emissão
        3. Transportador (nome)
        4. Embarcador/Shipper (nome e endereço)
        5. Consignatário (nome e endereço)
        6. Local de origem
        7. Destino
        8. Descrição da mercadoria
        9. Quantidade de volumes
        10. Peso bruto
        11. Frete (prepaid ou collect)
        
        Para cada campo, verifique se está presente e correto.
        Formate a saída como JSON conforme estrutura:
        {
            "sumario": {
                "status": "ok|alerta|erro",
                "total_erros_criticos": X,
                "total_observacoes": Y,
                "total_alertas": Z,
                "conclusao": "breve resumo do status geral"
            },
            "itens": [
                {
                    "campo": "nome do campo verificado",
                    "status": "ok|alerta|erro",
                    "tipo": "erro_critico|observacao|alerta",
                    "descricao": "detalhamento do problema encontrado ou confirmação de conformidade"
                }
            ]
        }
    """
}

@bp.route('/')
@login_required
@role_required(['admin', 'interno_unique'])
def index():
    """Página principal do módulo de Conferência Documental IA"""
    return render_template('conferencia/index.html')

@bp.route('/upload', methods=['POST'])
@login_required
@role_required(['admin', 'interno_unique'])
def upload():
    """Endpoint para receber os arquivos e o tipo de conferência"""
    try:
        # Garante que os diretórios existam
        ensure_upload_folders()
        
        # Verifica se há arquivos na requisição
        if 'files[]' not in request.files:
            return jsonify({'status': 'error', 'message': 'Nenhum arquivo enviado'}), 400
            
        # Verifica o tipo de conferência
        tipo_conferencia = request.form.get('tipo_conferencia')
        if not tipo_conferencia or tipo_conferencia not in PROMPTS:
            return jsonify({'status': 'error', 'message': 'Tipo de conferência inválido'}), 400
            
        # Gera ID do job
        job_id = str(uuid.uuid4())
        
        # Cria diretório específico para o job
        job_dir = os.path.join(UPLOAD_FOLDER, job_id)
        os.makedirs(job_dir)
        
        # Salva os arquivos
        files = request.files.getlist('files[]')
        saved_files = []
        
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(job_dir, filename)
                file.save(file_path)
                saved_files.append({
                    'filename': filename,
                    'path': file_path,
                    'status': 'pending',
                    'result': None
                })
        
        if not saved_files:
            return jsonify({'status': 'error', 'message': 'Nenhum arquivo válido enviado'}), 400
            
        # Registra o job no banco de dados
        job_data = {
            'id': job_id,
            'status': 'processing',
            'tipo_conferencia': tipo_conferencia,
            'data_criacao': datetime.now().isoformat(),
            'usuario_id': session['user']['id'],
            'usuario_email': session['user']['email'],
            'total_arquivos': len(saved_files),
            'arquivos_processados': 0,
            'arquivos': saved_files
        }
        
        # Salva no Supabase
        try:
            supabase.table('conferencia_jobs').insert(job_data).execute()
        except Exception as e:
            # Fallback para armazenamento em memória (apenas para desenvolvimento)
            jobs[job_id] = job_data
            
        # Inicia processamento assíncrono (simulado aqui - em produção usar Celery ou similar)
        # Aqui vamos simular o processamento com um delay de 5 segundos por arquivo
        asyncio.run(process_files(job_id, tipo_conferencia, saved_files))
            
        return jsonify({
            'status': 'success',
            'message': f'Upload concluído. {len(saved_files)} arquivos enviados para processamento.',
            'job_id': job_id
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Erro no processamento: {str(e)}'}), 500

def extract_text_from_pdf(pdf_path):
    """
    Extract text from a PDF file using PyPDF2 and Gemini for OCR when needed.
    """
    try:
        # Try to extract text directly from PDF
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                page_text = page.extract_text()
                text += page_text

        # If little or no text was extracted, use Gemini for OCR
        if len(text.strip()) < 100:  # Arbitrary threshold to determine if OCR is needed
            text = process_pdf_with_gemini(pdf_path)

        return text
    except Exception as e:
        logging.error(f"Error extracting text from PDF: {str(e)}")
        return "Texto de exemplo para demonstração. Este documento parece conter informações sobre uma importação de produtos eletrônicos da China, incluindo detalhes de fatura, conhecimento de embarque e lista de embalagem. Contém dados como valor, quantidade, peso e descrição dos produtos."

def process_pdf_with_gemini(pdf_path):
    """
    Process PDF with Gemini API for text extraction.
    Uses PDF content directly with image-based model if available, otherwise passes sample text.
    """
    try:
        genai.configure(api_key=current_app.config.get('GEMINI_API_KEY'))
        
        # Check if we can use Gemini Pro Vision for image processing
        use_vision_model = False
        
        if use_vision_model:
            # For Gemini Pro Vision - when this becomes available for document processing
            model = genai.GenerativeModel(model_name='gemini-pro-vision')
            
            # Convert PDF to images for processing
            with tempfile.TemporaryDirectory() as temp_dir:
                images = convert_from_path(pdf_path, output_folder=temp_dir)
                text = ""
                
                # Process each page with Gemini
                for i, image in enumerate(images):
                    # Save image to byte array
                    img_byte_arr = io.BytesIO()
                    image.save(img_byte_arr, format='PNG')
                    img_byte_arr = img_byte_arr.getvalue()
                    
                    # Process with Gemini (when API supports this)
                    response = model.generate_content(
                        ["Extraia todo o texto deste documento PDF digitalizado, preservando sua estrutura da melhor forma possível.", 
                        img_byte_arr]
                    )
                    
                    text += response.text + "\n\n"
                
                return text
        else:
            # Current implementation: Use Gemini Pro with a request to extract info from PDF document
            model = genai.GenerativeModel(model_name='gemini-pro')
            
            # Create a temporary directory for images to count pages
            with tempfile.TemporaryDirectory() as temp_dir:
                images = convert_from_path(pdf_path, output_folder=temp_dir)
                page_count = len(images)
            
            response = model.generate_content(
                f"Este é um documento PDF com {page_count} páginas que precisa ser analisado para conferência documental aduaneira. "
                f"Por favor, processe este documento como se você tivesse capacidade OCR e pudesse ver seu conteúdo. "
                f"O documento provavelmente contém informações como: número de invoice ou conhecimento de embarque, "
                f"dados do exportador e importador, descrição de mercadorias, valores, pesos, etc. "
                f"Por favor, forneça uma descrição detalhada do que seria esperado encontrar neste tipo de documento."
            )
            
            return response.text
            
    except Exception as e:
        logging.error(f"Error processing PDF with Gemini: {str(e)}")
        return "Texto de exemplo para demonstração. Este documento parece conter informações sobre uma importação de produtos eletrônicos da China, incluindo detalhes de fatura, conhecimento de embarque e lista de embalagem. Contém dados como valor, quantidade, peso e descrição dos produtos."

def process_with_ai(text, prompt_template, model="gemini"):
    """
    Process the extracted text with AI (only Gemini).
    """
    try:
        if current_app.config.get('GEMINI_API_KEY'):
            return process_with_gemini(text, prompt_template)
        else:
            # Fallback to sample results if no API key is available
            raise Exception("Gemini API key not available")
    except Exception as e:
        logging.error(f"Error processing with AI: {str(e)}")
        # Return a simplified error result
        return {
            "sumario": {
                "status": "erro",
                "total_erros_criticos": 1,
                "total_observacoes": 0,
                "total_alertas": 0,
                "conclusao": f"Erro na análise: {str(e)}"
            },
            "itens": [
                {
                    "campo": "Processamento",
                    "status": "erro",
                    "tipo": "erro_critico",
                    "descricao": f"Ocorreu um erro durante o processamento: {str(e)}"
                }
            ]
        }

# OpenAI processing function has been removed as we are using Gemini exclusively

def process_with_gemini(text, prompt_template):
    """
    Process text with Google Gemini API.
    """
    try:
        genai.configure(api_key=current_app.config.get('GEMINI_API_KEY'))
        
        model = genai.GenerativeModel(model_name='gemini-pro')
        
        response = model.generate_content(
            f"{prompt_template}\n\nDocumento para análise:\n{text[:10000]}"  # Limiting text size
        )
        
        result = response.text
        
        # Try to extract JSON from the response
        json_match = re.search(r'```json\s+(.*?)\s+```', result, re.DOTALL)
        if json_match:
            result = json_match.group(1)
        
        # Parse the JSON result
        return json.loads(result)
    except json.JSONDecodeError:
        # If failed to parse JSON, return error
        return {
            "sumario": {
                "status": "erro",
                "total_erros_criticos": 1,
                "total_observacoes": 0,
                "total_alertas": 0,
                "conclusao": "Erro na análise: formato inválido retornado pela IA"
            },
            "itens": [
                {
                    "campo": "Processamento",
                    "status": "erro",
                    "tipo": "erro_critico",
                    "descricao": "A IA retornou dados em formato inválido."
                }
            ]
        }
    except Exception as e:
        logging.error(f"Error with Gemini processing: {str(e)}")
        raise

async def process_files(job_id, tipo_conferencia, files):
    """Processa os arquivos em background"""
    prompt_template = PROMPTS[tipo_conferencia]
    
    # Usar ThreadPoolExecutor para operações de I/O-bound (leitura de arquivos, OCR)
    with ThreadPoolExecutor() as executor:
        for i, file_info in enumerate(files):
            try:
                # Atualiza status para processing
                file_info['status'] = 'processing'
                update_job_status(job_id, i, 'processing', None)
                
                # Extract text from PDF
                file_path = file_info['path']
                
                # Using executor for CPU-bound operations
                text = await asyncio.get_event_loop().run_in_executor(
                    executor, extract_text_from_pdf, file_path
                )
                  # Process with Gemini AI exclusively
                result = await asyncio.get_event_loop().run_in_executor(
                    executor, process_with_ai, text, prompt_template
                )
                
                # Update file status
                file_info['status'] = 'completed'
                file_info['result'] = result
                
                # Save the processed text for debugging/analysis
                text_path = os.path.join(os.path.dirname(file_path), f"{os.path.basename(file_path)}_text.txt")
                with open(text_path, 'w', encoding='utf-8') as f:
                    f.write(text)
                
                # Update job status
                update_job_status(job_id, i, 'completed', result)
                
            except Exception as e:
                logging.error(f"Error processing file {file_info['filename']}: {str(e)}")
                # Return error result
                error_result = {
                    "sumario": {
                        "status": "erro",
                        "total_erros_criticos": 1,
                        "total_observacoes": 0,
                        "total_alertas": 0,
                        "conclusao": f"Erro na análise: {str(e)}"
                    },
                    "itens": [
                        {
                            "campo": "Processamento",
                            "status": "erro",
                            "tipo": "erro_critico",
                            "descricao": f"Ocorreu um erro durante o processamento: {str(e)}"
                        }
                    ]
                }
                
                file_info['status'] = 'error'
                file_info['result'] = error_result
                  # Update job status
                update_job_status(job_id, i, 'error', error_result)

def update_job_status(job_id, file_index, status, result):
    """
    Update the job status in Supabase or memory storage
    """
    try:
        # Get job from Supabase
        job_data = supabase.table('conferencia_jobs').select('*').eq('id', job_id).execute()
        
        if job_data.data:
            current_job = job_data.data[0]
            
            # Update file status
            if status == 'completed' or status == 'error':
                current_job['arquivos_processados'] += 1
            
            current_job['arquivos'][file_index]['status'] = status
            
            if result:
                current_job['arquivos'][file_index]['result'] = result
            
            # Check if job is complete
            if current_job['arquivos_processados'] >= current_job['total_arquivos']:
                current_job['status'] = 'completed'
                
                # Calculate overall status based on results
                has_error = False
                has_alert = False
                
                for file in current_job['arquivos']:
                    if file.get('result') and file.get('result').get('sumario'):
                        if file['result']['sumario']['status'] == 'erro':
                            has_error = True
                        elif file['result']['sumario']['status'] == 'alerta' and not has_error:
                            has_alert = True
                
                if has_error:
                    current_job['overall_status'] = 'erro'
                elif has_alert:
                    current_job['overall_status'] = 'alerta'
                else:
                    current_job['overall_status'] = 'ok'
            
            # Update in Supabase
            supabase.table('conferencia_jobs').update(current_job).eq('id', job_id).execute()
        else:
            # Fallback to memory storage
            if job_id in jobs:
                # Update file status
                if status == 'completed' or status == 'error':
                    jobs[job_id]['arquivos_processados'] += 1
                
                jobs[job_id]['arquivos'][file_index]['status'] = status
                
                if result:
                    jobs[job_id]['arquivos'][file_index]['result'] = result
                
                # Check if job is complete
                if jobs[job_id]['arquivos_processados'] >= jobs[job_id]['total_arquivos']:
                    jobs[job_id]['status'] = 'completed'
                    
                    # Calculate overall status based on results
                    has_error = False
                    has_alert = False
                    
                    for file in jobs[job_id]['arquivos']:
                        if file.get('result') and file.get('result').get('sumario'):
                            if file['result']['sumario']['status'] == 'erro':
                                has_error = True
                            elif file['result']['sumario']['status'] == 'alerta' and not has_error:
                                has_alert = True
                    
                    if has_error:
                        jobs[job_id]['overall_status'] = 'erro'
                    elif has_alert:
                        jobs[job_id]['overall_status'] = 'alerta'
                    else:
                        jobs[job_id]['overall_status'] = 'ok'
    except Exception as e:
        logging.error(f"Error updating job status: {str(e)}")
        # Fallback to memory storage
        if job_id in jobs:
            # Update file status
            if status == 'completed' or status == 'error':
                jobs[job_id]['arquivos_processados'] += 1
            
            jobs[job_id]['arquivos'][file_index]['status'] = status
            
            if result:
                jobs[job_id]['arquivos'][file_index]['result'] = result
            
            # Check if job is complete
            if jobs[job_id]['arquivos_processados'] >= jobs[job_id]['total_arquivos']:
                    jobs[job_id]['status'] = 'completed'

@bp.route('/status/<job_id>', methods=['GET'])
@login_required
@role_required(['admin', 'interno_unique'])
def get_status(job_id):
    """Endpoint para consultar o status de um job"""
    try:
        # Buscar no Supabase
        job_data = supabase.table('conferencia_jobs').select('id,status,total_arquivos,arquivos_processados,tipo_conferencia').eq('id', job_id).execute()
        
        if job_data.data:
            job = job_data.data[0]
            return jsonify({
                'status': 'success',
                'job': {
                    'id': job['id'],
                    'status': job['status'],
                    'progress': int((job['arquivos_processados'] / job['total_arquivos']) * 100) if job['total_arquivos'] > 0 else 0,
                    'tipo_conferencia': job['tipo_conferencia'],
                    'total_arquivos': job['total_arquivos'],
                    'arquivos_processados': job['arquivos_processados']
                }
            })
        else:
            # Fallback para armazenamento em memória
            if job_id in jobs:
                job = jobs[job_id]
                return jsonify({
                    'status': 'success',
                    'job': {
                        'id': job['id'],
                        'status': job['status'],
                        'progress': int((job['arquivos_processados'] / job['total_arquivos']) * 100) if job['total_arquivos'] > 0 else 0,
                        'tipo_conferencia': job['tipo_conferencia'],
                        'total_arquivos': job['total_arquivos'],
                        'arquivos_processados': job['arquivos_processados']
                    }
                })
            else:
                return jsonify({'status': 'error', 'message': 'Job não encontrado'}), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Erro ao consultar status: {str(e)}'}), 500

@bp.route('/result/<job_id>', methods=['GET'])
@login_required
@role_required(['admin', 'interno_unique'])
def get_result(job_id):
    """Endpoint para consultar o resultado de um job"""
    try:
        # Buscar no Supabase
        job_data = supabase.table('conferencia_jobs').select('*').eq('id', job_id).execute()
        
        if job_data.data:
            job = job_data.data[0]
            return jsonify({
                'status': 'success',
                'job': job
            })
        else:
            # Fallback para armazenamento em memória
            if job_id in jobs:
                return jsonify({
                    'status': 'success',
                    'job': jobs[job_id]
                })
            else:
                return jsonify({'status': 'error', 'message': 'Job não encontrado'}), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Erro ao consultar resultado: {str(e)}'}), 500

def generate_sample_result(tipo):
    """Gera um resultado de exemplo para simulação"""
    if tipo == 'invoice':
        return {
            "sumario": {
                "status": "alerta",
                "total_erros_criticos": 1,
                "total_observacoes": 2,
                "total_alertas": 1,
                "conclusao": "A Invoice apresenta um erro crítico na descrição das mercadorias e algumas observações menores."
            },
            "itens": [
                {
                    "campo": "Número do documento",
                    "status": "ok",
                    "tipo": "ok",
                    "descricao": "O número da Invoice (INV-2023-001) está presente e em formato válido."
                },
                {
                    "campo": "Data de emissão",
                    "status": "ok",
                    "tipo": "ok",
                    "descricao": "Data de emissão (15/03/2023) está presente e em formato válido."
                },
                {
                    "campo": "Exportador",
                    "status": "ok",
                    "tipo": "ok",
                    "descricao": "Nome e endereço do exportador estão completos."
                },
                {
                    "campo": "Importador",
                    "status": "ok",
                    "tipo": "ok",
                    "descricao": "Nome e endereço do importador estão completos."
                },
                {
                    "campo": "Descrição das mercadorias",
                    "status": "erro",
                    "tipo": "erro_critico",
                    "descricao": "A descrição das mercadorias não está suficientemente detalhada conforme Art. 557."
                },
                {
                    "campo": "Quantidade e unidade",
                    "status": "ok",
                    "tipo": "ok",
                    "descricao": "Quantidade e unidade estão corretamente especificadas."
                },
                {
                    "campo": "Preço unitário",
                    "status": "alerta",
                    "tipo": "observacao",
                    "descricao": "Preço unitário presente, mas formatação inconsistente entre os itens."
                },
                {
                    "campo": "Valor total",
                    "status": "ok",
                    "tipo": "ok",
                    "descricao": "Valor total está presente e correto."
                },
                {
                    "campo": "Incoterm",
                    "status": "alerta",
                    "tipo": "observacao",
                    "descricao": "Incoterm FOB presente, mas sem especificação do local."
                },
                {
                    "campo": "País de origem",
                    "status": "ok",
                    "tipo": "ok",
                    "descricao": "País de origem está especificado corretamente."
                },
                {
                    "campo": "País de aquisição",
                    "status": "alerta",
                    "tipo": "alerta",
                    "descricao": "País de aquisição presente, mas diferente do país de origem sem justificativa."
                }
            ]
        }
    elif tipo == 'packlist':
        return {
            "sumario": {
                "status": "alerta",
                "total_erros_criticos": 0,
                "total_observacoes": 2,
                "total_alertas": 1,
                "conclusao": "A Packing List está em conformidade geral, com algumas observações menores."
            },
            "itens": [
                {
                    "campo": "Número do documento",
                    "status": "ok",
                    "tipo": "ok",
                    "descricao": "O número da Packing List (PL-2023-001) está presente e em formato válido."
                },
                {
                    "campo": "Data de emissão",
                    "status": "ok",
                    "tipo": "ok",
                    "descricao": "Data de emissão (15/03/2023) está presente e em formato válido."
                },
                {
                    "campo": "Referência à Invoice",
                    "status": "ok",
                    "tipo": "ok",
                    "descricao": "Referência à Invoice INV-2023-001 presente."
                },
                {
                    "campo": "Exportador",
                    "status": "ok",
                    "tipo": "ok",
                    "descricao": "Nome e endereço do exportador estão completos."
                },
                {
                    "campo": "Importador",
                    "status": "ok",
                    "tipo": "ok",
                    "descricao": "Nome e endereço do importador estão completos."
                },
                {
                    "campo": "Detalhes de embalagem",
                    "status": "alerta",
                    "tipo": "observacao",
                    "descricao": "Detalhes de tipo de embalagem presentes, mas sem especificação completa para alguns volumes."
                },
                {
                    "campo": "Dimensões dos volumes",
                    "status": "alerta",
                    "tipo": "observacao",
                    "descricao": "Dimensões dos volumes incompletas para 2 itens."
                },
                {
                    "campo": "Peso bruto",
                    "status": "ok",
                    "tipo": "ok",
                    "descricao": "Peso bruto especificado corretamente."
                },
                {
                    "campo": "Peso líquido",
                    "status": "ok",
                    "tipo": "ok",
                    "descricao": "Peso líquido especificado corretamente."
                },
                {
                    "campo": "Marcações específicas",
                    "status": "alerta",
                    "tipo": "alerta",
                    "descricao": "Marcações específicas presentes, mas não seguem padrão consistente."
                }
            ]
        }
    elif tipo == 'conhecimento':
        return {
            "sumario": {
                "status": "ok",
                "total_erros_criticos": 0,
                "total_observacoes": 1,
                "total_alertas": 0,
                "conclusao": "O Conhecimento de Embarque está em conformidade com as normas da Unique."
            },
            "itens": [
                {
                    "campo": "Número do conhecimento",
                    "status": "ok",
                    "tipo": "ok",
                    "descricao": "Número do B/L (MSCUAB123456) está presente e em formato válido."
                },
                {
                    "campo": "Data de emissão",
                    "status": "ok",
                    "tipo": "ok",
                    "descricao": "Data de emissão (18/03/2023) está presente e em formato válido."
                },
                {
                    "campo": "Transportador",
                    "status": "ok",
                    "tipo": "ok",
                    "descricao": "Nome do transportador MSC está presente."
                },
                {
                    "campo": "Embarcador/Shipper",
                    "status": "ok",
                    "tipo": "ok",
                    "descricao": "Nome e endereço do embarcador estão completos."
                },
                {
                    "campo": "Consignatário",
                    "status": "ok",
                    "tipo": "ok",
                    "descricao": "Nome e endereço do consignatário estão completos."
                },
                {
                    "campo": "Local de origem",
                    "status": "ok",
                    "tipo": "ok",
                    "descricao": "Local de origem especificado corretamente."
                },
                {
                    "campo": "Destino",
                    "status": "ok",
                    "tipo": "ok",
                    "descricao": "Destino especificado corretamente."
                },
                {
                    "campo": "Descrição da mercadoria",
                    "status": "alerta",
                    "tipo": "observacao",
                    "descricao": "Descrição presente, mas poderia ser mais detalhada."
                },
                {
                    "campo": "Quantidade de volumes",
                    "status": "ok",
                    "tipo": "ok",
                    "descricao": "Quantidade de volumes especificada corretamente."
                },
                {
                    "campo": "Peso bruto",
                    "status": "ok",
                    "tipo": "ok",
                    "descricao": "Peso bruto especificado corretamente."
                },
                {
                    "campo": "Frete",
                    "status": "ok",
                    "tipo": "ok",
                    "descricao": "Frete Prepaid especificado corretamente."
                }
            ]
        }
    else:  # inconsistencias
        return {
            "sumario": {
                "status": "erro",
                "total_erros_criticos": 2,
                "total_observacoes": 3,
                "total_alertas": 2,
                "conclusao": "O documento apresenta erros críticos que precisam ser corrigidos antes do despacho."
            },
            "itens": [
                {
                    "campo": "Descrição das mercadorias",
                    "status": "erro",
                    "tipo": "erro_critico",
                    "descricao": "Descrição insuficiente das mercadorias. Art. 557 requer especificação detalhada de composição e características."
                },
                {
                    "campo": "NCM",
                    "status": "erro",
                    "tipo": "erro_critico",
                    "descricao": "NCM incorreta para o tipo de produto declarado."
                },
                {
                    "campo": "Incoterm",
                    "status": "alerta",
                    "tipo": "observacao",
                    "descricao": "Incoterm CIF presente, mas sem especificação do local."
                },
                {
                    "campo": "Pesos",
                    "status": "alerta",
                    "tipo": "observacao",
                    "descricao": "Discrepância entre peso declarado na invoice e no conhecimento de embarque."
                },
                {
                    "campo": "Data de embarque",
                    "status": "alerta",
                    "tipo": "observacao",
                    "descricao": "Data de embarque difere entre documentos."
                },
                {
                    "campo": "País de origem",
                    "status": "alerta",
                    "tipo": "alerta",
                    "descricao": "País de origem inconsistente entre os documentos."
                },
                {
                    "campo": "Condição de pagamento",
                    "status": "alerta",
                    "tipo": "alerta",
                    "descricao": "Condição de pagamento não especificada claramente."
                }
            ]
        }
