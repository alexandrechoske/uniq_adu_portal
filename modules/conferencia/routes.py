from flask import Blueprint, render_template, request, jsonify, session, url_for, current_app
from extensions import supabase
from routes.auth import login_required, role_required
import uuid
import json
from datetime import datetime
import os
import time
import tempfile
import random
import base64
import threading
import signal
import functools
import logging
from werkzeug.utils import secure_filename
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor
import re

# Imports for PDF processing
try:
    import PyPDF2
    from pdf2image import convert_from_path
    import google.generativeai as genai
    PDF_PROCESSING_AVAILABLE = True
except ImportError:
    PDF_PROCESSING_AVAILABLE = False

# Criar blueprint com configuração modular
conferencia_bp = Blueprint(
    'conferencia', 
    __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/conferencia/static',
    url_prefix='/conferencia'
)

# Configurações para armazenamento temporário de arquivos
UPLOAD_FOLDER = 'static/uploads/conferencia'
ALLOWED_EXTENSIONS = {'pdf'}

# Dicionário para armazenar o status dos jobs em memória
jobs = {}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def ensure_upload_folders():
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

# Templates de prompts para cada tipo de conferência
PROMPTS = {
    'inconsistencias': """
    Você é um sistema avançado de extração de dados, especializado em análise de documentos aduaneiros para identificar inconsistências gerais. Sua tarefa é analisar o documento fornecido e identificar possíveis problemas ou inconsistências.

    **Instruções para Análise Geral:**

    1. Analise a estrutura geral do documento
    2. Identifique campos obrigatórios ausentes
    3. Verifique a consistência de datas
    4. Analise valores e cálculos
    5. Identifique informações conflitantes

    **Formato da Saída (JSON):**
    {
        "sumario": {
            "status": "ok|alerta|erro",
            "total_erros_criticos": X,
            "total_observacoes": Y,
            "total_alertas": Z,
            "conclusao": "Breve resumo da análise geral do documento."
        },
        "itens": [
            {
                "campo": "Nome do Campo Analisado",
                "status": "ok|alerta|erro",
                "tipo": "ok|erro_critico|observacao|alerta",
                "valor_extraido": "Valor encontrado no documento",
                "descricao": "Descrição da análise ou problema identificado."
            }
        ]
    }
    """,
    'invoice': """
    Você é um sistema avançado de extração de dados, especializado em análise de documentos aduaneiros. Sua tarefa é analisar a Invoice Comercial fornecida e extrair informações cruciais com base no Art. 557 do regulamento aduaneiro brasileiro.

    **Instruções Detalhadas para Extração:**

    1.  **Número do documento (Invoice Number):**
        * Procure por rótulos como "Invoice No.", "Fattura nr.", "Rechnung", "Belegnummer", "INVOICE #", "Number", "Invoice No.:", "Fattura n.", "Número", "INVOICE", "INVOICE#", "SHIPMENT NUMBER".
        * Seja flexível com prefixos e sufixos (ex: 'PI', 'INV-', 'S', 'FE/', 'IT00125VEN', '1610743'). Extraia o identificador principal.

    2.  **Data de emissão (Issue Date):**
        * Procure por "Date", "Data", "Datum", "DATE".

    3.  **Exportador (Exporter/Shipper):**
        * Procure por "Exporter", "Shipper", "From", "The Seller/Exporter", "HEADQUARTER", "MANUFACTURER", ou o nome da empresa no cabeçalho do documento. Extraia o nome e o endereço completos.

    4.  **Importador (Importer/Consignee):**
        * Procure por "Importer", "Consignee", "Bill to", "Ship to", "To", "MESSRS:", "Destinatario", "Buyer", "SOLD TO". Extraia o nome e o endereço completos.

    5.  **Itens da Fatura (Line Items):**
        * **Lógica de Agrupamento de Itens:** Documentos com tabelas ou grades complexas podem ter informações de um único item espalhadas por várias linhas. Agrupe de forma inteligente as linhas que pertencem ao mesmo item antes de extrair os dados.
        * **Para cada item na fatura, extraia os seguintes campos:**
            * **descricao_completa:** Combine a descrição principal do produto, part number, códigos e outras especificações. Procure por colunas como "DESCRIPTION", "Descrizione", "Bezeichnung", "Description of goods", "Product".
            * **quantidade_unidade:** Extraia a quantidade total de peças. Procure por "Q'TY", "QTY", "Quantity", "PCS", "NR", "Menge", "SHIPPED", "QTY PACKED". A unidade (ex: "PCS", "NR", "KG", "LBS", "m", "pce", "pc", "pcs", "unit", "unt", "kgs", "ltr", "l", "mtr", "gr", "box") deve ser incluída se disponível.
            * **preco_unitario:** Encontre o preço por unidade ou por milheiro (M). Procure por "UNIT PRICE", "Prezzo", "Preis", "USD/M", "Gross price", "UNIT". Pode ser indicado por um '@'.
            * **valor_total_item:** O valor total para a linha do item. Procure por "AMOUNT", "Total", "Importo", "Summe", "Total tax excluded", "EXTENDED".

    6.  **Incoterm:**
        * Procure por termos como "INCOTERM", "PRICE TERM", "Delivery Terms", "FREIGHT TERMS". Extraia o termo e o local (ex: "FOB KAOHSIUNG TAIWAN", "EXWORKS").

    7.  **País de Origem (Country of Origin):**
        * Procure por "Country of Origin", "Made in", "Origin". Se não estiver explícito, infira a partir do endereço do exportador.

    8.  **País de Aquisição (Country of Acquisition):**
        * Procure por "Country of Acquisition", "COUNTRY OF ACQUISITION AND PROCEED". Se ausente, assuma que é o mesmo que o País de Origem.

    **Formato da Saída (JSON):**
    A saída DEVE ser um único objeto JSON válido, sem nenhum texto adicional antes ou depois. Para cada campo extraído, inclua um campo "valor_extraido" que mostra o texto exato do documento.

    {
        "sumario": {
            "status": "ok|alerta|erro",
            "total_erros_criticos": X,
            "total_observacoes": Y,
            "total_alertas": Z,
            "conclusao": "Breve resumo do status geral da análise da fatura."
        },
        "itens_analisados": [
            {
                "campo": "Nome do Campo Verificado",
                "status": "ok|alerta|erro",
                "tipo": "ok|erro_critico|observacao|alerta",
                "valor_extraido": "O texto exato encontrado no documento.",
                "descricao": "Detalhamento do problema encontrado ou confirmação de conformidade."
            }
        ],
        "itens_da_fatura": [
            {
                "descricao_completa": {
                    "valor_extraido": "Descrição completa do item, incluindo códigos e part numbers."
                },
                "quantidade_unidade": {
                    "valor_extraido": "Ex: 72,000 PCS"
                },
                "preco_unitario": {
                    "valor_extraido": "Ex: 1.91 USD/M"
                },
                "valor_total_item": {
                    "valor_extraido": "Ex: 137.48"
                }
            }
        ]
    }
    """
}

@conferencia_bp.route('/')
@login_required
def index():
    """Página principal do módulo de conferência"""
    return render_template('index.html')

@conferencia_bp.route('/upload', methods=['POST'])
@login_required
def upload():
    """Endpoint para upload de arquivos PDF"""
    if not PDF_PROCESSING_AVAILABLE:
        return jsonify({
            'success': False,
            'message': 'Processamento de PDF não disponível. Instale as dependências necessárias.'
        }), 500
    
    ensure_upload_folders()
    
    if 'files[]' not in request.files:
        return jsonify({'success': False, 'message': 'Nenhum arquivo enviado'}), 400
    
    files = request.files.getlist('files[]')
    if not files or files[0].filename == '':
        return jsonify({'success': False, 'message': 'Nenhum arquivo selecionado'}), 400
    
    # Obter tipo de conferência do formulário
    tipo_conferencia = request.form.get('tipo_conferencia', 'inconsistencias')
    current_app.logger.info(f"Tipo de conferência selecionado: {tipo_conferencia}")
    
    uploaded_files = []
    errors = []
    
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_filename = f"{timestamp}_{filename}"
            filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
            
            try:
                file.save(filepath)
                uploaded_files.append({
                    'original_name': filename,
                    'saved_name': unique_filename,
                    'path': filepath,
                    'size': os.path.getsize(filepath)
                })
                current_app.logger.info(f"Arquivo salvo: {filepath}")
            except Exception as e:
                errors.append(f"Erro ao salvar {filename}: {str(e)}")
        else:
            errors.append(f"Arquivo inválido: {file.filename}")
    
    if uploaded_files:
        # Iniciar processamento em background
        job_id = str(uuid.uuid4())
        jobs[job_id] = {
            'status': 'processing',
            'progress': 0,
            'files': uploaded_files,
            'results': [],
            'started_at': datetime.now(),
            'user_id': session['user']['id'],
            'tipo_conferencia': tipo_conferencia
        }
        
        current_app.logger.info(f"Iniciando job {job_id} para {len(uploaded_files)} arquivos")
        
        # Processar em background
        threading.Thread(target=background_process, args=(job_id, uploaded_files)).start()
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'files_count': len(uploaded_files),
            'tipo_conferencia': tipo_conferencia,
            'errors': errors
        })
    
    return jsonify({
        'success': False,
        'message': 'Nenhum arquivo válido foi processado',
        'errors': errors
    }), 400

def background_process(job_id, files):
    """Processa arquivos em background com análise real via Gemini"""
    try:
        total_files = len(files)
        
        # Obter tipo de conferência da sessão ou padrão
        tipo_conferencia = jobs[job_id].get('tipo_conferencia', 'inconsistencias')
        
        for i, file_info in enumerate(files):
            if job_id not in jobs:
                break
                
            # Atualizar progresso
            progress = int((i / total_files) * 100)
            jobs[job_id]['progress'] = progress
            jobs[job_id]['current_file'] = file_info['original_name']
            
            current_app.logger.info(f"Processando arquivo {file_info['original_name']} - Progresso: {progress}%")
            
            try:
                # 1. Extrair texto do PDF
                current_app.logger.info(f"Extraindo texto do PDF: {file_info['path']}")
                pdf_text = extract_text_from_pdf(file_info['path'])
                
                if not pdf_text or pdf_text.strip() == "":
                    # Se não conseguiu extrair texto, tentar conversão para imagem
                    current_app.logger.warning(f"Texto vazio do PDF {file_info['original_name']}, tentando OCR...")
                    analysis_result = process_pdf_as_image(file_info['path'], tipo_conferencia)
                else:
                    # 2. Processar com IA usando o texto extraído
                    current_app.logger.info(f"Analisando texto com Gemini - Tipo: {tipo_conferencia}")
                    analysis_result = process_with_ai(pdf_text, tipo_conferencia)
                
                # 3. Criar resultado estruturado
                result = {
                    'file': file_info['original_name'],
                    'status': 'completed',
                    'tipo_conferencia': tipo_conferencia,
                    'analysis': analysis_result,
                    'processado_em': datetime.now().isoformat(),
                    'arquivo_info': {
                        'tamanho': file_info['size'],
                        'nome_salvo': file_info['saved_name']
                    }
                }
                
                current_app.logger.info(f"Análise concluída para {file_info['original_name']}")
                
            except Exception as e:
                current_app.logger.error(f"Erro ao processar {file_info['original_name']}: {str(e)}")
                result = {
                    'file': file_info['original_name'],
                    'status': 'error',
                    'error': str(e),
                    'processado_em': datetime.now().isoformat()
                }
            
            jobs[job_id]['results'].append(result)
        
        # Finalizar job
        if job_id in jobs:
            jobs[job_id]['status'] = 'completed'
            jobs[job_id]['progress'] = 100
            jobs[job_id]['completed_at'] = datetime.now()
            current_app.logger.info(f"Job {job_id} finalizado com sucesso")
            
    except Exception as e:
        current_app.logger.error(f"Erro geral no processamento do job {job_id}: {str(e)}")
        if job_id in jobs:
            jobs[job_id]['status'] = 'error'
            jobs[job_id]['error'] = str(e)

@conferencia_bp.route('/status/<job_id>')
@login_required
def get_status(job_id):
    """Retorna o status de um job de processamento"""
    if job_id not in jobs:
        return jsonify({'error': 'Job não encontrado'}), 404
    
    job = jobs[job_id]
    
    # Verificar se o usuário tem permissão para ver este job
    if job['user_id'] != session['user']['id']:
        return jsonify({'error': 'Não autorizado'}), 403
    
    return jsonify(job)

@conferencia_bp.route('/results/<job_id>')
@login_required
def get_results(job_id):
    """Retorna os resultados detalhados de um job"""
    if job_id not in jobs:
        return jsonify({'error': 'Job não encontrado'}), 404
    
    job = jobs[job_id]
    
    if job['user_id'] != session['user']['id']:
        return jsonify({'error': 'Não autorizado'}), 403
    
    if job['status'] != 'completed':
        return jsonify({'error': 'Job ainda não foi completado'}), 400
    
    return jsonify({
        'job_id': job_id,
        'results': job['results'],
        'summary': {
            'total_files': len(job['files']),
            'processed_files': len(job['results']),
            'started_at': job['started_at'].isoformat(),
            'completed_at': job.get('completed_at', '').isoformat() if job.get('completed_at') else None
        }
    })

@conferencia_bp.route('/cleanup/<job_id>', methods=['DELETE'])
@login_required
def cleanup_job(job_id):
    """Remove um job e seus arquivos temporários"""
    if job_id not in jobs:
        return jsonify({'error': 'Job não encontrado'}), 404
    
    job = jobs[job_id]
    
    if job['user_id'] != session['user']['id']:
        return jsonify({'error': 'Não autorizado'}), 403
    
    # Remover arquivos temporários
    try:
        for file_info in job['files']:
            if os.path.exists(file_info['path']):
                os.remove(file_info['path'])
    except Exception as e:
        current_app.logger.error(f"Erro ao remover arquivos do job {job_id}: {str(e)}")
    
    # Remover job da memória
    del jobs[job_id]
    
    return jsonify({'success': True, 'message': 'Job removido com sucesso'})

# Funções auxiliares para processamento de PDF
def extract_text_from_pdf(pdf_path):
    """Extrai texto de um arquivo PDF"""
    if not PDF_PROCESSING_AVAILABLE:
        return "Processamento de PDF não disponível"
    
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
            return text
    except Exception as e:
        current_app.logger.error(f"Erro ao extrair texto do PDF {pdf_path}: {str(e)}")
        return f"Erro ao extrair texto: {str(e)}"

def process_pdf_as_image(pdf_path, tipo_conferencia):
    """Processa PDF convertendo para imagem quando texto não é extraível"""
    try:
        from pdf2image import convert_from_path
        import base64
        import io
        
        current_app.logger.info(f"Convertendo PDF para imagem: {pdf_path}")
        
        # Converter primeira página do PDF para imagem
        images = convert_from_path(pdf_path, first_page=1, last_page=1, dpi=200)
        
        if not images:
            return {"error": "Não foi possível converter PDF para imagem"}
        
        # Converter imagem para base64
        img_buffer = io.BytesIO()
        images[0].save(img_buffer, format='PNG')
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
        
        # Processar com Gemini Vision
        return process_with_ai_vision(img_base64, tipo_conferencia)
        
    except Exception as e:
        current_app.logger.error(f"Erro ao processar PDF como imagem {pdf_path}: {str(e)}")
        return {"error": f"Erro no processamento de imagem: {str(e)}"}

def process_with_ai(text, tipo_conferencia):
    """Processa texto com IA usando Gemini"""
    try:
        import google.generativeai as genai
        import os
        
        # Configurar Gemini
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            current_app.logger.error("GEMINI_API_KEY não configurada")
            return {"error": "API Key do Gemini não configurada"}
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Obter prompt baseado no tipo de conferência
        prompt_template = PROMPTS.get(tipo_conferencia, PROMPTS['inconsistencias'])
        
        # Construir prompt completo
        full_prompt = f"{prompt_template}\n\n**DOCUMENTO A SER ANALISADO:**\n{text}"
        
        current_app.logger.info(f"Enviando texto para Gemini - Tamanho: {len(text)} caracteres")
        
        # Fazer request para o Gemini
        response = model.generate_content(full_prompt)
        
        if not response.text:
            return {"error": "Resposta vazia do Gemini"}
        
        current_app.logger.info("Resposta recebida do Gemini com sucesso")
        
        # Tentar parsear JSON da resposta
        try:
            import json
            # Limpar resposta (remover markdown se houver)
            clean_response = response.text.strip()
            if clean_response.startswith('```json'):
                clean_response = clean_response[7:]
            if clean_response.endswith('```'):
                clean_response = clean_response[:-3]
            
            parsed_result = json.loads(clean_response.strip())
            return parsed_result
            
        except json.JSONDecodeError as e:
            current_app.logger.error(f"Erro ao parsear JSON do Gemini: {str(e)}")
            current_app.logger.error(f"Resposta original: {response.text}")
            return {
                "error": "Erro ao parsear resposta da IA",
                "raw_response": response.text
            }
        
    except Exception as e:
        current_app.logger.error(f"Erro ao processar com Gemini: {str(e)}")
        return {"error": f"Erro no processamento: {str(e)}"}

def process_with_ai_vision(image_base64, tipo_conferencia):
    """Processa imagem com Gemini Vision"""
    try:
        import google.generativeai as genai
        import os
        
        # Configurar Gemini
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            return {"error": "API Key do Gemini não configurada"}
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Obter prompt baseado no tipo de conferência
        prompt_template = PROMPTS.get(tipo_conferencia, PROMPTS['inconsistencias'])
        
        # Construir prompt para visão
        vision_prompt = f"{prompt_template}\n\n**Analise a imagem do documento fornecida e extraia as informações conforme solicitado.**"
        
        current_app.logger.info("Enviando imagem para Gemini Vision")
        
        # Criar objeto de imagem
        import PIL.Image
        import io
        import base64
        
        image_data = base64.b64decode(image_base64)
        image = PIL.Image.open(io.BytesIO(image_data))
        
        # Fazer request para o Gemini Vision
        response = model.generate_content([vision_prompt, image])
        
        if not response.text:
            return {"error": "Resposta vazia do Gemini Vision"}
        
        current_app.logger.info("Resposta recebida do Gemini Vision com sucesso")
        
        # Tentar parsear JSON da resposta
        try:
            import json
            # Limpar resposta
            clean_response = response.text.strip()
            if clean_response.startswith('```json'):
                clean_response = clean_response[7:]
            if clean_response.endswith('```'):
                clean_response = clean_response[:-3]
            
            parsed_result = json.loads(clean_response.strip())
            return parsed_result
            
        except json.JSONDecodeError as e:
            current_app.logger.error(f"Erro ao parsear JSON do Gemini Vision: {str(e)}")
            return {
                "error": "Erro ao parsear resposta da IA Vision",
                "raw_response": response.text
            }
        
    except Exception as e:
        current_app.logger.error(f"Erro ao processar com Gemini Vision: {str(e)}")
        return {"error": f"Erro no processamento Vision: {str(e)}"}
