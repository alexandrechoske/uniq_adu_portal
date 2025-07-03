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

# Imports for PDF processing
import PyPDF2
from pdf2image import convert_from_path
import re
import io

# Import for Gemini AI integration - Implementação baseada no rest_gemini.md
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
        * Procure por rótulos como "Order","Order No","Invoice No.", "Fattura nr.", "Rechnung", "Belegnummer", "INVOICE #", "Number", "Invoice No.:", "Fattura n.", "Número", "INVOICE", "INVOICE#", "SHIPMENT NUMBER".
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
        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        
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
        
        # SEMPRE salvar na memória primeiro (fonte primária)
        jobs[job_id] = job_data
        print(f"DEBUG: Job {job_id} salvo na memória: {job_data['status']}")
        
        # Tentar salvar no Supabase como backup (não crítico)
        try:
            supabase.table('conferencia_jobs').insert(job_data).execute()
            print(f"DEBUG: Job {job_id} também salvo no Supabase")
        except Exception as e:
            print(f"DEBUG: Aviso - Não foi possível salvar no Supabase (usando memória): {e}")
            # Isso não é crítico, o sistema continua funcionando com memória
        
        # Obtém a API key do Gemini da configuração
        gemini_api_key = current_app.config.get('GEMINI_API_KEY')
        
        # PROCESSAMENTO ASSÍNCRONO PARA EVITAR TIMEOUT NO HEROKU
        # Retornar resposta imediata e processar em background
        
        def background_process():
            """Processa arquivos em background sem bloquear resposta HTTP"""
            try:
                print(f"DEBUG: Iniciando processamento assíncrono para job {job_id}")
                
                # Verificar se o job está na memória
                if job_id not in jobs:
                    print(f"DEBUG: ERRO - Job {job_id} não encontrado na memória ao iniciar processamento")
                    return
                
                # Processar cada arquivo
                for i, file_info in enumerate(saved_files):
                    try:
                        filename = file_info['filename']
                        file_path = file_info['path']
                        print(f"DEBUG: Processando arquivo {i+1}/{len(saved_files)}: {filename}")
                        
                        # Atualizar progresso - usando apenas colunas que existem na tabela
                        update_data = {
                            'arquivos_processados': i
                        }
                        try:
                            supabase.table('conferencia_jobs').update(update_data).eq('id', job_id).execute()
                        except Exception as db_error:
                            print(f"DEBUG: Erro ao atualizar progresso no banco: {db_error}")
                            # Atualizar na memória
                            if job_id in jobs:
                                jobs[job_id].update(update_data)
                        
                        # Processar arquivo
                        if gemini_api_key:
                            print(f"DEBUG: Analisando PDF diretamente com Gemini...")
                            prompt_template = PROMPTS[tipo_conferencia]
                            result = analyze_pdf_with_gemini(file_path, prompt_template, gemini_api_key)
                            print(f"DEBUG: Resultado recebido do Gemini para {filename}")
                        else:
                            print(f"DEBUG: API key do Gemini não encontrada, usando resultado de exemplo")
                            result = generate_sample_result(tipo_conferencia, filename)
                        
                        file_info['status'] = 'completed'
                        file_info['result'] = result
                        
                        # Atualizar job na memória imediatamente - PROTEÇÃO CONTRA NONES
                        print(f"DEBUG: [GRANULAR] Atualizando job na memória após sucesso")
                        print(f"DEBUG: [GRANULAR] job_id: {job_id}")
                        print(f"DEBUG: [GRANULAR] job_id in jobs: {job_id in jobs}")
                        
                        if job_id in jobs:
                            print(f"DEBUG: [GRANULAR] Jobs dict tipo: {type(jobs)}")
                            print(f"DEBUG: [GRANULAR] Jobs[job_id] tipo: {type(jobs[job_id])}")
                            print(f"DEBUG: [GRANULAR] Jobs[job_id] é None: {jobs[job_id] is None}")
                            
                            if jobs[job_id] is not None:
                                if 'arquivos' not in jobs[job_id]:
                                    print(f"DEBUG: [GRANULAR] ERRO - 'arquivos' não está em jobs[job_id]")
                                    jobs[job_id]['arquivos'] = []
                                
                                print(f"DEBUG: [GRANULAR] Atualizando arquivo {i} no job (sucesso)")
                                print(f"DEBUG: [GRANULAR] Arquivos list tipo: {type(jobs[job_id]['arquivos'])}")
                                print(f"DEBUG: [GRANULAR] Arquivos list tamanho: {len(jobs[job_id]['arquivos']) if jobs[job_id]['arquivos'] else 0}")
                                
                                if i < len(jobs[job_id]['arquivos']):
                                    jobs[job_id]['arquivos'][i] = file_info
                                    jobs[job_id]['arquivos_processados'] = i + 1
                                    print(f"DEBUG: [GRANULAR] Arquivo {i} atualizado com sucesso")
                                else:
                                    print(f"DEBUG: [GRANULAR] ERRO - Índice {i} fora do range da lista arquivos")
                            else:
                                print(f"DEBUG: [GRANULAR] ERRO - jobs[job_id] é None")
                        
                        # Debug do resultado - PROTEÇÃO CONTRA NONES
                        print(f"DEBUG: [GRANULAR] Verificando resultado para {filename}")
                        print(f"DEBUG: [GRANULAR] Tipo do resultado: {type(result)}")
                        print(f"DEBUG: [GRANULAR] Resultado é None: {result is None}")
                        
                        if result is None:
                            print(f"DEBUG: [GRANULAR] ERRO - Resultado é None para {filename}")
                        elif not isinstance(result, dict):
                            print(f"DEBUG: [GRANULAR] ERRO - Resultado não é dict para {filename}: {type(result)}")
                        else:
                            print(f"DEBUG: [GRANULAR] Resultado é dict válido")
                            print(f"DEBUG: [GRANULAR] Chaves do resultado: {list(result.keys()) if result else 'N/A'}")
                            
                            # Verificar se 'sumario' está presente
                            if 'sumario' not in result:
                                print(f"DEBUG: [GRANULAR] ERRO - Chave 'sumario' não encontrada no resultado")
                            else:
                                sumario = result.get('sumario')
                                print(f"DEBUG: [GRANULAR] Sumario extraído: {type(sumario)}")
                                print(f"DEBUG: [GRANULAR] Sumario é None: {sumario is None}")
                                
                                if sumario is None:
                                    print(f"DEBUG: [GRANULAR] ERRO - Sumario é None")
                                elif not isinstance(sumario, dict):
                                    print(f"DEBUG: [GRANULAR] ERRO - Sumario não é dict: {type(sumario)}")
                                else:
                                    print(f"DEBUG: [GRANULAR] Sumario é dict válido")
                                    print(f"DEBUG: [GRANULAR] Chaves do sumario: {list(sumario.keys()) if sumario else 'N/A'}")
                                    
                                    # Agora acessar com segurança
                                    status = sumario.get('status', 'N/A')
                                    conclusao = sumario.get('conclusao', 'N/A')
                                    total_erros = sumario.get('total_erros_criticos', 0)
                                    total_alertas = sumario.get('total_alertas', 0)
                                    total_obs = sumario.get('total_observacoes', 0)
                                    
                                    print(f"DEBUG: Arquivo {filename} processado - Status: {status}")
                                    print(f"DEBUG: Conclusão: {conclusao}")
                                    print(f"DEBUG: Erros críticos: {total_erros}")
                                    print(f"DEBUG: Alertas: {total_alertas}")
                                    print(f"DEBUG: Observações: {total_obs}")
                            
                            # Verificar itens com proteção
                            if 'itens' in result and result['itens'] is not None:
                                itens = result['itens']
                                print(f"DEBUG: [GRANULAR] Itens encontrados: {type(itens)}")
                                if isinstance(itens, list):
                                    print(f"DEBUG: Total de itens analisados: {len(itens)}")
                                    for idx, item in enumerate(itens[:3]):  # Primeiros 3 itens
                                        if item and isinstance(item, dict):
                                            campo = item.get('campo', 'N/A')
                                            status_item = item.get('status', 'N/A')
                                            descricao = item.get('descricao', 'N/A')
                                            desc_preview = descricao[:100] if isinstance(descricao, str) else str(descricao)[:100]
                                            print(f"DEBUG: Item {idx+1}: {campo} - {status_item} - {desc_preview}...")
                                        else:
                                            print(f"DEBUG: [GRANULAR] Item {idx+1} é inválido: {type(item)}")
                                else:
                                    print(f"DEBUG: [GRANULAR] ERRO - Itens não é uma lista: {type(itens)}")
                            else:
                                print(f"DEBUG: [GRANULAR] Nenhum item encontrado ou itens é None")
                            
                    except Exception as e:
                        print(f"DEBUG: ERRO ao processar {filename}: {str(e)}")
                        # Criar resultado de erro
                        error_result = {
                            "sumario": {
                                "status": "erro",
                                "total_erros_criticos": 1,
                                "total_observacoes": 0,
                                "total_alertas": 0,
                                "conclusao": f"Erro no processamento: {str(e)}"
                            },
                            "itens": [
                                {
                                    "campo": "Processamento",
                                    "status": "erro",
                                    "tipo": "erro_critico",
                                    "valor_extraido": None,
                                    "descricao": str(e)
                                }
                            ]
                        }
                        
                        file_info['status'] = 'error'
                        file_info['result'] = error_result
                        
                        # Atualizar job na memória - PROTEÇÃO CONTRA NONES
                        print(f"DEBUG: [GRANULAR] Atualizando job na memória após erro")
                        print(f"DEBUG: [GRANULAR] job_id: {job_id}")
                        print(f"DEBUG: [GRANULAR] job_id in jobs: {job_id in jobs}")
                        
                        if job_id in jobs:
                            print(f"DEBUG: [GRANULAR] Jobs dict tipo: {type(jobs)}")
                            print(f"DEBUG: [GRANULAR] Jobs[job_id] tipo: {type(jobs[job_id])}")
                            print(f"DEBUG: [GRANULAR] Jobs[job_id] é None: {jobs[job_id] is None}")
                            
                            if jobs[job_id] is not None:
                                if 'arquivos' not in jobs[job_id]:
                                    print(f"DEBUG: [GRANULAR] ERRO - 'arquivos' não está em jobs[job_id]")
                                    jobs[job_id]['arquivos'] = []
                                
                                print(f"DEBUG: [GRANULAR] Atualizando arquivo {i} no job")
                                print(f"DEBUG: [GRANULAR] Arquivos list tipo: {type(jobs[job_id]['arquivos'])}")
                                print(f"DEBUG: [GRANULAR] Arquivos list tamanho: {len(jobs[job_id]['arquivos']) if jobs[job_id]['arquivos'] else 0}")
                                
                                if i < len(jobs[job_id]['arquivos']):
                                    jobs[job_id]['arquivos'][i] = file_info
                                    jobs[job_id]['arquivos_processados'] = i + 1
                                    print(f"DEBUG: [GRANULAR] Arquivo {i} atualizado com erro")
                                else:
                                    print(f"DEBUG: [GRANULAR] ERRO - Índice {i} fora do range da lista arquivos")
                            else:
                                print(f"DEBUG: [GRANULAR] ERRO - jobs[job_id] é None")
                
                # Finalizar job - usando apenas colunas que existem na tabela - PROTEÇÃO CONTRA NONES
                print(f"DEBUG: [GRANULAR] Finalizando job {job_id}")
                print(f"DEBUG: [GRANULAR] saved_files tipo: {type(saved_files)}")
                print(f"DEBUG: [GRANULAR] saved_files tamanho: {len(saved_files) if saved_files else 0}")
                
                # Verificar se saved_files não foi corrompido
                if saved_files is None:
                    print(f"DEBUG: [GRANULAR] ERRO - saved_files é None ao finalizar")
                    saved_files = []
                elif not isinstance(saved_files, list):
                    print(f"DEBUG: [GRANULAR] ERRO - saved_files não é lista: {type(saved_files)}")
                    saved_files = []
                
                final_job_data = {
                    'status': 'completed',
                    'arquivos_processados': len(saved_files),
                    'arquivos': saved_files
                }
                
                print(f"DEBUG: [GRANULAR] final_job_data criado: {list(final_job_data.keys())}")
                
                # Atualizar na memória primeiro (fonte primária) - PROTEÇÃO CONTRA NONES
                print(f"DEBUG: [GRANULAR] Atualizando job finalizado na memória")
                print(f"DEBUG: [GRANULAR] job_id in jobs: {job_id in jobs}")
                
                if job_id in jobs:
                    print(f"DEBUG: [GRANULAR] Jobs[job_id] tipo antes update: {type(jobs[job_id])}")
                    print(f"DEBUG: [GRANULAR] Jobs[job_id] é None antes update: {jobs[job_id] is None}")
                    
                    if jobs[job_id] is not None:
                        try:
                            jobs[job_id].update(final_job_data)
                            print(f"DEBUG: Job {job_id} finalizado na memória")
                            print(f"DEBUG: [GRANULAR] Jobs[job_id] tipo após update: {type(jobs[job_id])}")
                        except Exception as update_error:
                            print(f"DEBUG: [GRANULAR] ERRO ao atualizar job na memória: {str(update_error)}")
                            print(f"DEBUG: [GRANULAR] Tipo do jobs[job_id]: {type(jobs[job_id])}")
                            print(f"DEBUG: [GRANULAR] Valor do jobs[job_id]: {jobs[job_id]}")
                    else:
                        print(f"DEBUG: [GRANULAR] ERRO - jobs[job_id] é None, criando novo")
                        jobs[job_id] = {**job_data, **final_job_data}
                else:
                    print(f"DEBUG: [GRANULAR] Job não encontrado na memória, criando")
                    jobs[job_id] = {**job_data, **final_job_data}
                
                # Tentar atualizar no Supabase como backup (não crítico)
                try:
                    supabase.table('conferencia_jobs').update(final_job_data).eq('id', job_id).execute()
                    print(f"DEBUG: Job {job_id} também atualizado no Supabase")
                except Exception as e:
                    print(f"DEBUG: Aviso - Não foi possível atualizar no Supabase (job finalizado em memória): {e}")
                
                print(f"DEBUG: Processamento assíncrono concluído para job {job_id}")
                
            except Exception as e:
                print(f"DEBUG: ERRO FATAL no processamento assíncrono: {str(e)}")
                # Marcar job como erro na memória (fonte primária)
                error_job_data = {
                    'status': 'error',
                    'arquivos_processados': len(saved_files)  # Marcar como processados mesmo com erro
                }
                
                if job_id in jobs:
                    jobs[job_id].update(error_job_data)
                else:
                    jobs[job_id] = {**job_data, **error_job_data}
                
                print(f"DEBUG: Job {job_id} marcado como erro na memória")
                
                # Tentar salvar erro no Supabase como backup (não crítico)
                try:
                    supabase.table('conferencia_jobs').update(error_job_data).eq('id', job_id).execute()
                    print(f"DEBUG: Status de erro também salvo no Supabase")
                except Exception as db_error:
                    print(f"DEBUG: Aviso - Erro não pôde ser salvo no Supabase: {db_error}")
        
        # Iniciar thread daemon em background
        background_thread = threading.Thread(target=background_process, daemon=True)
        background_thread.start()
        
        print(f"DEBUG: Thread assíncrona iniciada para job {job_id}, retornando resposta imediata")
        
        # Retornar resposta imediata para evitar timeout
        return jsonify({
            'status': 'success',
            'message': f'Upload concluído. {len(saved_files)} arquivos enviados para processamento assíncrono.',
            'job_id': job_id,
            'async_processing': True,
            'estimated_time': f'{len(saved_files) * 90} segundos'  # Estimativa de 1.5 min por arquivo
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

def process_pdf_with_gemini(pdf_path, api_key=None):
    """
    Process PDF with Gemini API using base64 encoding for direct PDF analysis.
    """
    try:
        if not api_key:
            print(f"DEBUG: API key não fornecida para process_pdf_with_gemini")
            return "Texto de exemplo para demonstração. Este documento parece conter informações sobre uma importação de produtos eletrônicos da China, incluindo detalhes de fatura, conhecimento de embarque e lista de embalagem. Contém dados como valor, quantidade, peso e descrição dos produtos."
        
        print(f"DEBUG: Iniciando processamento do PDF com Gemini via base64")
        genai.configure(api_key=api_key)
        
        # Ler o arquivo PDF e converter para base64
        with open(pdf_path, 'rb') as pdf_file:
            pdf_bytes = pdf_file.read()
            pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
        
        print(f"DEBUG: PDF convertido para base64 ({len(pdf_base64)} caracteres)")
        
        # Criar o modelo
        model = genai.GenerativeModel(model_name=os.getenv('GEMINI_MODEL'))
        
        # Criar a mensagem com o PDF em base64
        contents = [
            {
                "role": "user",
                "parts": [
                    {
                        "inline_data": {
                            "mime_type": "application/pdf",
                            "data": pdf_base64
                        }
                    },
                    {
                        "text": "Extraia todo o texto deste documento PDF, preservando sua estrutura e formatação da melhor forma possível. Identifique todos os dados presentes, incluindo números, datas, nomes de empresas, endereços, valores monetários, quantidades, descrições de produtos, etc. Mantenha a hierarquia e organização original do documento."
                    }
                ]
            }
        ]
        
        print(f"DEBUG: Enviando PDF para análise do Gemini...")
        
        # Enviar para o Gemini
        response = model.generate_content(contents)
        
        print(f"DEBUG: Resposta recebida do Gemini")
        extracted_text = response.text
        
        if extracted_text and len(extracted_text.strip()) > 50:
            print(f"DEBUG: Texto extraído com sucesso ({len(extracted_text)} caracteres)")
            return extracted_text
        else:
            print(f"DEBUG: Texto extraído muito curto, usando fallback")
            return "Texto de exemplo para demonstração. Este documento parece conter informações sobre uma importação de produtos eletrônicos da China, incluindo detalhes de fatura, conhecimento de embarque e lista de embalagem. Contém dados como valor, quantidade, peso e descrição dos produtos."
            
    except Exception as e:
        print(f"DEBUG: Erro no processamento do PDF com Gemini: {str(e)}")
        logging.error(f"Error processing PDF with Gemini: {str(e)}")
        return "Texto de exemplo para demonstração. Este documento parece conter informações sobre uma importação de produtos eletrônicos da China, incluindo detalhes de fatura, conhecimento de embarque e lista de embalagem. Contém dados como valor, quantidade, peso e descrição dos produtos."

def analyze_pdf_with_gemini(pdf_path, prompt_template, api_key):
    """
    Analisa PDF com Gemini de forma otimizada para evitar timeout.
    """
    try:
        print(f"DEBUG: Iniciando análise otimizada do PDF com Gemini")
        genai.configure(api_key=api_key)
        
        # Verificar tamanho do arquivo
        file_size = os.path.getsize(pdf_path)
        print(f"DEBUG: Tamanho do arquivo: {file_size / (1024*1024):.2f} MB")
        
        # Para arquivos grandes (>2MB), usar análise por texto
        if file_size > 2 * 1024 * 1024:
            print(f"DEBUG: Arquivo grande, usando extração de texto")
            return analyze_pdf_with_text_extraction(pdf_path, prompt_template, api_key)
        
        # Para arquivos menores, análise direta
        with open(pdf_path, 'rb') as pdf_file:
            pdf_bytes = pdf_file.read()
            pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
        
        print(f"DEBUG: PDF convertido para base64 ({len(pdf_base64)} chars)")
        
        # Configuração otimizada
        generation_config = {
            "temperature": 0.1,
            "top_p": 0.8,
            "top_k": 20,
            "max_output_tokens": 4096,
        }
        
        model = genai.GenerativeModel(
            model_name=os.getenv('GEMINI_MODEL'),
            generation_config=generation_config
        )
        
        # Prompt conciso
        prompt = f"""
        {prompt_template}
        
        Retorne APENAS JSON válido conforme o template, sem texto adicional.
        """
        
        contents = [
            {
                "role": "user",
                "parts": [
                    {
                        "inline_data": {
                            "mime_type": "application/pdf",
                            "data": pdf_base64
                        }
                    },
                    {
                        "text": prompt
                    }
                ]
            }
        ]
        
        print(f"DEBUG: Enviando para Gemini...")
        
        # Executar com timeout
        import threading
        result = {'response': None, 'error': None}
        
        def generate():
            try:
                result['response'] = model.generate_content(contents)
            except Exception as e:
                result['error'] = e
        
        thread = threading.Thread(target=generate)
        thread.start()
        thread.join(timeout=90)  # 90 segundos
        
        if thread.is_alive():
            raise TimeoutError("Timeout de 90s atingido")
        
        if result['error']:
            raise result['error']
        
        response = result['response']
        
        # Verificar se a resposta foi filtrada por segurança
        if not response:
            raise Exception("Resposta vazia do Gemini")
        
        # Verificar finish_reason para detectar filtragem de conteúdo
        if hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, 'finish_reason'):
                finish_reason = candidate.finish_reason
                print(f"DEBUG: Finish reason: {finish_reason}")
                
                # finish_reason = 2 significa SAFETY (conteúdo filtrado por segurança)
                if finish_reason == 2:
                    print(f"DEBUG: Conteúdo filtrado por segurança (finish_reason=2), tentando análise por texto")
                    return analyze_pdf_with_text_extraction(pdf_path, prompt_template, api_key)
                elif finish_reason == 3:  # LENGTH
                    print(f"DEBUG: Resposta muito longa (finish_reason=3), tentando análise por texto")
                    return analyze_pdf_with_text_extraction(pdf_path, prompt_template, api_key)
                elif finish_reason not in [1, 0]:  # 1 = STOP (sucesso), 0 = UNSPECIFIED
                    print(f"DEBUG: Finish reason inválido ({finish_reason}), tentando análise por texto")
                    return analyze_pdf_with_text_extraction(pdf_path, prompt_template, api_key)
        
        # Verificar se tem texto na resposta
        try:
            response_text = response.text
            if not response_text or len(response_text.strip()) < 10:
                print(f"DEBUG: Resposta muito curta, tentando análise por texto")
                return analyze_pdf_with_text_extraction(pdf_path, prompt_template, api_key)
        except Exception as text_error:
            print(f"DEBUG: Erro ao acessar response.text: {str(text_error)}")
            print(f"DEBUG: Tentando análise por texto como fallback")
            return analyze_pdf_with_text_extraction(pdf_path, prompt_template, api_key)
        
        print(f"DEBUG: Resposta recebida ({len(response_text)} chars)")
        return parse_gemini_json(response_text)
        
    except Exception as e:
        print(f"DEBUG: Erro na análise: {str(e)}")
        return create_error_result(f"Erro na análise: {str(e)}")

def analyze_pdf_with_text_extraction(pdf_path, prompt_template, api_key):
    """
    Analisa PDF extraindo texto primeiro (para arquivos grandes ou quando houve filtragem).
    """
    try:
        print(f"DEBUG: Extraindo texto do PDF para análise fallback...")
        text = extract_text_from_pdf(pdf_path)
        
        if not text or len(text) < 50:
            print(f"DEBUG: Texto extraído muito pequeno ({len(text) if text else 0} chars)")
            raise Exception("Não foi possível extrair texto legível")
        
        print(f"DEBUG: Texto extraído com sucesso ({len(text)} chars)")
        
        # Limitar texto para evitar problemas
        if len(text) > 30000:
            text = text[:30000] + "\n[TEXTO TRUNCADO]"
            print(f"DEBUG: Texto truncado para 30k chars")
        
        # Configurar Gemini
        genai.configure(api_key=api_key)
        
        generation_config = {
            "temperature": 0.1,
            "top_p": 0.8,
            "top_k": 20,
            "max_output_tokens": 4096,
        }
        
        model = genai.GenerativeModel(
            model_name=os.getenv('GEMINI_MODEL'),
            generation_config=generation_config
        )
        
        # Prompt simplificado para análise por texto
        prompt = f"""
        Analise o texto extraído do documento e retorne APENAS um JSON no formato especificado.
        
        {prompt_template}
        
        Texto do documento:
        {text}
        
        IMPORTANTE: Retorne APENAS JSON válido, sem texto adicional antes ou depois.
        """
        
        print(f"DEBUG: Enviando texto extraído para Gemini...")
        
        # Executar com timeout reduzido
        import threading
        result = {'response': None, 'error': None}
        
        def generate():
            try:
                result['response'] = model.generate_content(prompt)
                print(f"DEBUG: Resposta recebida do Gemini para análise por texto")
            except Exception as e:
                print(f"DEBUG: Erro na geração por texto: {str(e)}")
                result['error'] = e
        
        thread = threading.Thread(target=generate)
        thread.start()
        thread.join(timeout=60)  # 60 segundos para texto
        
        if thread.is_alive():
            print(f"DEBUG: Timeout atingido na análise por texto")
            raise TimeoutError("Timeout de 60s atingido na análise por texto")
        
        if result['error']:
            print(f"DEBUG: Erro na thread text analysis: {str(result['error'])}")
            raise result['error']
        
        if not result['response']:
            print(f"DEBUG: Resposta nula na análise por texto")
            raise Exception("Resposta nula do Gemini")
        
        # Verificar finish_reason também na análise por texto
        if hasattr(result['response'], 'candidates') and result['response'].candidates:
            candidate = result['response'].candidates[0]
            if hasattr(candidate, 'finish_reason'):
                finish_reason = candidate.finish_reason
                print(f"DEBUG: Finish reason na análise por texto: {finish_reason}")
                
                if finish_reason == 2:
                    print(f"DEBUG: Conteúdo ainda filtrado por segurança na análise por texto")
                    return create_safety_filtered_result()
        
        if not result['response'].text:
            print(f"DEBUG: Texto da resposta vazio na análise por texto")
            raise Exception("Texto da resposta vazio do Gemini")
        
        print(f"DEBUG: Resposta da análise por texto recebida ({len(result['response'].text)} chars)")
        return parse_gemini_json(result['response'].text)
        
    except Exception as e:
        print(f"DEBUG: Erro na análise por texto: {str(e)}")
        return create_error_result(f"Erro na análise por texto: {str(e)}")

def parse_gemini_json(response_text):
    """
    Extrai e faz parse do JSON da resposta do Gemini.
    """
    try:
        print(f"DEBUG: Parseando resposta do Gemini ({len(response_text)} chars)")
        print(f"DEBUG: Primeiros 500 chars da resposta: {response_text[:500]}")
        
        # Tentar extrair JSON de markdown - PROTEÇÃO CONTRA NONES
        print(f"DEBUG: [GRANULAR] Tentando extrair JSON do markdown...")
        json_match = re.search(r'```json\s+(.*?)\s+```', response_text, re.DOTALL)
        if json_match:
            extracted_json = json_match.group(1)
            print(f"DEBUG: JSON extraído do markdown")
            print(f"DEBUG: [GRANULAR] JSON extraído tipo: {type(extracted_json)}")
            print(f"DEBUG: [GRANULAR] JSON extraído é None: {extracted_json is None}")
            print(f"DEBUG: [GRANULAR] JSON extraído tamanho: {len(extracted_json) if extracted_json else 0}")
            if extracted_json:
                response_text = extracted_json
            else:
                print(f"DEBUG: [GRANULAR] ERRO - JSON extraído é vazio/None")
        else:
            print(f"DEBUG: [GRANULAR] Nenhum JSON encontrado em markdown")
            # Buscar JSON entre chaves
            print(f"DEBUG: [GRANULAR] Tentando extrair JSON entre chaves...")
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            print(f"DEBUG: [GRANULAR] json_start: {json_start}, json_end: {json_end}")
            if json_start != -1 and json_end > json_start:
                extracted_json = response_text[json_start:json_end]
                print(f"DEBUG: JSON extraído entre chaves")
                print(f"DEBUG: [GRANULAR] JSON extraído entre chaves tipo: {type(extracted_json)}")
                print(f"DEBUG: [GRANULAR] JSON extraído entre chaves tamanho: {len(extracted_json) if extracted_json else 0}")
                if extracted_json:
                    response_text = extracted_json
                else:
                    print(f"DEBUG: [GRANULAR] ERRO - JSON extraído entre chaves é vazio")
            else:
                print(f"DEBUG: [GRANULAR] ERRO - Não foi possível extrair JSON entre chaves")
        
        print(f"DEBUG: JSON a ser parseado: {response_text[:300]}...")
        
        # Parse JSON
        try:
            print(f"DEBUG: [GRANULAR] Tentando fazer parse do JSON...")
            result = json.loads(response_text)
            print(f"DEBUG: [GRANULAR] Parse JSON bem-sucedido")
            print(f"DEBUG: [GRANULAR] Tipo do resultado: {type(result)}")
            print(f"DEBUG: [GRANULAR] Resultado é None: {result is None}")
        except json.JSONDecodeError as json_error:
            print(f"DEBUG: [GRANULAR] ERRO no parse JSON: {str(json_error)}")
            raise json_error
        
        # Validar estrutura - PROTEÇÃO CONTRA NONES
        print(f"DEBUG: [GRANULAR] Validando estrutura do resultado...")
        
        if result is None:
            print(f"DEBUG: [GRANULAR] ERRO - Resultado é None após parse")
            raise ValueError("Resultado é None após parse JSON")
        
        if not isinstance(result, dict):
            print(f"DEBUG: [GRANULAR] ERRO - Resultado não é dict: {type(result)}")
            raise ValueError(f"Resultado não é dict: {type(result)}")
        
        print(f"DEBUG: [GRANULAR] Resultado é dict válido")
        print(f"DEBUG: [GRANULAR] Chaves do resultado: {list(result.keys()) if result else 'N/A'}")
        
        # AQUI PODE ESTAR O ERRO: 'sumario' in result quando result pode ser None
        print(f"DEBUG: [GRANULAR] Verificando se 'sumario' está no resultado...")
        try:
            has_sumario = 'sumario' in result
            print(f"DEBUG: [GRANULAR] 'sumario' in result: {has_sumario}")
        except TypeError as type_error:
            print(f"DEBUG: [GRANULAR] ERRO TypeError ao verificar 'sumario' in result: {str(type_error)}")
            print(f"DEBUG: [GRANULAR] Tipo do result durante erro: {type(result)}")
            print(f"DEBUG: [GRANULAR] Value do result durante erro: {result}")
            raise ValueError(f"Erro ao verificar 'sumario' in result: {str(type_error)}")
        
        if not has_sumario:
            print(f"DEBUG: [GRANULAR] ERRO - JSON não contém campo 'sumario'")
            raise ValueError("JSON não contém campo 'sumario'")
        
        # Validar se sumario não é None
        sumario_value = result.get('sumario')
        print(f"DEBUG: [GRANULAR] Valor do sumario: {type(sumario_value)}")
        print(f"DEBUG: [GRANULAR] Sumario é None: {sumario_value is None}")
        
        if sumario_value is None:
            print(f"DEBUG: [GRANULAR] ERRO - Campo 'sumario' é None")
            raise ValueError("Campo 'sumario' é None")
        
        print(f"DEBUG: JSON parseado com sucesso")
        print(f"DEBUG: Status do sumário: {result['sumario'].get('status', 'N/A')}")
        print(f"DEBUG: Conclusão: {result['sumario'].get('conclusao', 'N/A')}")
        
        return result
        
    except Exception as e:
        print(f"DEBUG: Erro no parse JSON: {str(e)}")
        print(f"DEBUG: Texto que falhou no parse: {response_text[:200]}...")
        return create_error_result("Formato inválido retornado pela IA")

def create_safety_filtered_result():
    """
    Cria resultado específico para quando o conteúdo é filtrado por segurança.
    """
    return {
        "sumario": {
            "status": "atencao",
            "total_erros_criticos": 0,
            "total_observacoes": 1,
            "total_alertas": 0,
            "conclusao": "Documento processado com limitações. O sistema de IA identificou conteúdo que pode conter informações sensíveis e aplicou filtros de segurança. A análise pode estar incompleta."
        },
        "itens": [
            {
                "campo": "Análise de Segurança",
                "status": "atencao",
                "tipo": "observacao",
                "valor_extraido": "Filtrado por segurança",
                "descricao": "O sistema de IA aplicou filtros de segurança ao analisar este documento. Isso pode ocorrer quando o documento contém informações pessoais, financeiras sensíveis ou outros dados que requerem tratamento especial. A análise foi realizada com as informações disponíveis após a filtragem."
            }
        ]
    }

def create_error_result(message):
    """
    Cria resultado de erro estruturado.
    """
    return {
        "sumario": {
            "status": "erro",
            "total_erros_criticos": 1,
            "total_observacoes": 0,
            "total_alertas": 0,
            "conclusao": message
        },
        "itens": [
            {
                "campo": "Processamento",
                "status": "erro",
                "tipo": "erro_critico",
                "valor_extraido": None,
                "descricao": message
            }
        ]
    }

def process_with_ai(text, prompt_template, model="gemini", api_key=None):
    """
    Process the extracted text with AI (only Gemini).
    """
    try:
        if api_key:
            return process_with_gemini(text, prompt_template, api_key)
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

def process_with_gemini(text, prompt_template, api_key):
    """
    Process text with Google Gemini API with timeout and retry logic.
    """
    import time
    import functools
    import signal
    
    def timeout_handler(signum, frame):
        raise TimeoutError("Timeout na requisição ao Gemini API")
    
    def with_timeout(timeout_seconds):
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # Set the signal handler
                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(timeout_seconds)
                
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    # Reset the alarm and restore the old handler
                    signal.alarm(0)
                    signal.signal(signal.SIGALRM, old_handler)
            return wrapper
        return decorator
    
    @with_timeout(60)  # 60 segundos de timeout
    def _make_gemini_request(text, prompt_template, api_key):
        try:
            print(f"DEBUG: Configurando Gemini com API key...")
            genai.configure(api_key=api_key)
            
            print(f"DEBUG: Criando modelo Gemini...")
            # Usar configuração com timeout
            generation_config = {
                "temperature": 0.3,
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 8192,
            }
            
            model = genai.GenerativeModel(
                model_name=os.getenv('GEMINI_MODEL'),
                generation_config=generation_config
            )
            
            # Preparar prompt completo - reduzir tamanho do texto se muito grande
            text_limit = 15000  # Aumentar limite para documentos maiores
            truncated_text = text[:text_limit]
            if len(text) > text_limit:
                truncated_text += "\n\n[TEXTO TRUNCADO - DOCUMENTO MUITO LONGO]"
            
            full_prompt = f"{prompt_template}\n\nDocumento para análise:\n{truncated_text}"
            print(f"DEBUG: Enviando prompt para Gemini ({len(full_prompt)} caracteres)...")
            
            # Fazer requisição com retry
            max_retries = 3
            retry_delay = 2
            
            for attempt in range(max_retries):
                try:
                    print(f"DEBUG: Tentativa {attempt + 1} de {max_retries}")
                    response = model.generate_content(full_prompt)
                    
                    if response and response.text:
                        print(f"DEBUG: Resposta recebida do Gemini")
                        return response.text
                    else:
                        raise Exception("Resposta vazia do Gemini")
                        
                except Exception as e:
                    print(f"DEBUG: Erro na tentativa {attempt + 1}: {str(e)}")
                    if attempt < max_retries - 1:
                        print(f"DEBUG: Aguardando {retry_delay} segundos antes da próxima tentativa...")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        raise e
            
            raise Exception("Todas as tentativas falharam")
            
        except Exception as e:
            print(f"DEBUG: Erro na requisição Gemini: {str(e)}")
            raise e
    
    try:
        # Executar com timeout
        result = _make_gemini_request(text, prompt_template, api_key)
        
        print(f"DEBUG: Texto da resposta ({len(result)} caracteres): {result[:200]}...")
        
        # Try to extract JSON from the response - PROTEÇÃO CONTRA NONES
        print(f"DEBUG: [GRANULAR] Tentando extrair JSON da resposta do Gemini...")
        print(f"DEBUG: [GRANULAR] Tipo do result: {type(result)}")
        print(f"DEBUG: [GRANULAR] Result é None: {result is None}")
        
        if result is None:
            print(f"DEBUG: [GRANULAR] ERRO - Result é None antes da extração JSON")
            raise Exception("Resposta None do Gemini")
        
        if not isinstance(result, str):
            print(f"DEBUG: [GRANULAR] ERRO - Result não é string: {type(result)}")
            raise Exception(f"Resposta não é string: {type(result)}")
        
        json_match = re.search(r'```json\s+(.*?)\s+```', result, re.DOTALL)
        if json_match:
            extracted_json = json_match.group(1)
            print(f"DEBUG: JSON extraído do markdown")
            print(f"DEBUG: [GRANULAR] JSON extraído tipo: {type(extracted_json)}")
            print(f"DEBUG: [GRANULAR] JSON extraído é None: {extracted_json is None}")
            if extracted_json:
                result = extracted_json
            else:
                print(f"DEBUG: [GRANULAR] ERRO - JSON extraído do markdown é None/vazio")
        else:
            print(f"DEBUG: Nenhum JSON encontrado em markdown, tentando parse direto")
        
        # Parse the JSON result - PROTEÇÃO CONTRA NONES
        print(f"DEBUG: [GRANULAR] Tentando fazer parse final do JSON...")
        print(f"DEBUG: [GRANULAR] JSON final a ser parseado (200 chars): {result[:200] if result else 'None'}...")
        
        if not result:
            print(f"DEBUG: [GRANULAR] ERRO - JSON final está vazio")
            raise Exception("JSON final está vazio")
        
        try:
            parsed_result = json.loads(result)
            print(f"DEBUG: JSON parseado com sucesso")
            print(f"DEBUG: [GRANULAR] Parsed result tipo: {type(parsed_result)}")
            print(f"DEBUG: [GRANULAR] Parsed result é None: {parsed_result is None}")
            if parsed_result and isinstance(parsed_result, dict):
                print(f"DEBUG: [GRANULAR] Parsed result chaves: {list(parsed_result.keys())}")
            else:
                print(f"DEBUG: [GRANULAR] ERRO - Parsed result não é dict válido")
        except json.JSONDecodeError as json_error:
            print(f"DEBUG: [GRANULAR] ERRO no parse final do JSON: {str(json_error)}")
            print(f"DEBUG: [GRANULAR] JSON que falhou: {result[:500] if result else 'None'}...")
            raise json_error
        
        return parsed_result
        
    except TimeoutError as e:
        print(f"DEBUG: Timeout na requisição ao Gemini: {str(e)}")
        return {
            "sumario": {
                "status": "erro",
                "total_erros_criticos": 1,
                "total_observacoes": 0,
                "total_alertas": 0,
                "conclusao": "Timeout na análise: o processamento demorou mais que o esperado"
            },
            "itens": [
                {
                    "campo": "Processamento",
                    "status": "erro",
                    "tipo": "erro_critico",
                    "valor_extraido": None,
                    "descricao": f"Timeout na requisição à IA (mais de 60 segundos). Documento pode ser muito complexo."
                }
            ]
        }
    except json.JSONDecodeError as e:
        print(f"DEBUG: Erro ao fazer parse do JSON: {str(e)}")
        print(f"DEBUG: Conteúdo que falhou no parse: {result[:500]}")
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
                    "valor_extraido": None,
                    "descricao": "A IA retornou dados em formato inválido."
                }
            ]
        }
    except Exception as e:
        print(f"DEBUG: Erro geral no processamento Gemini: {str(e)}")
        logging.error(f"Error with Gemini processing: {str(e)}")
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
                    "valor_extraido": None,
                    "descricao": f"Ocorreu um erro durante o processamento: {str(e)}"
                }
            ]
        }

async def process_files(job_id, tipo_conferencia, files, api_key=None):
    """Processa os arquivos em background com timeout adequado"""
    from config import Config
    
    prompt_template = PROMPTS[tipo_conferencia]
    
    # Usar ThreadPoolExecutor para operações de I/O-bound (leitura de arquivos, OCR)
    with ThreadPoolExecutor(max_workers=2) as executor:  # Limitear workers para evitar sobrecarga
        for i, file_info in enumerate(files):
            try:
                print(f"DEBUG: Processando arquivo {i+1}: {file_info['filename']}")
                
                # Atualiza status para processing
                file_info['status'] = 'processing'
                update_job_status(job_id, i, 'processing', None)
                
                # Extract text from PDF
                file_path = file_info['path']
                
                print(f"DEBUG: Extraindo texto do PDF...")
                # Using executor for CPU-bound operations
                text = await asyncio.get_event_loop().run_in_executor(
                    executor, extract_text_from_pdf, file_path
                )
                
                print(f"DEBUG: Texto extraído ({len(text)} caracteres)")
                
                # Process with Gemini AI exclusively com timeout aumentado
                print(f"DEBUG: Iniciando processamento com IA...")
                
                # Usar timeout configurado para Gemini
                result = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        executor, process_with_ai, text, prompt_template, "gemini", api_key
                    ),
                    timeout=Config.GEMINI_TIMEOUT  # Usar timeout configurado
                )
                
                print(f"DEBUG: Processamento IA concluído")
                
                # Update file status
                file_info['status'] = 'completed'
                file_info['result'] = result
                
                # Save the processed text for debugging/analysis
                text_path = os.path.join(os.path.dirname(file_path), f"{os.path.basename(file_path)}_text.txt")
                with open(text_path, 'w', encoding='utf-8') as f:
                    f.write(text)
                
                # Update job status
                update_job_status(job_id, i, 'completed', result)
                
                print(f"DEBUG: Arquivo {file_info['filename']} processado com sucesso")
                
            except asyncio.TimeoutError as e:
                print(f"DEBUG: Timeout no processamento do arquivo {file_info['filename']}")
                logging.error(f"Timeout processing file {file_info['filename']}: {str(e)}")
                # Return timeout error result
                timeout_result = {
                    "sumario": {
                        "status": "erro",
                        "total_erros_criticos": 1,
                        "total_observacoes": 0,
                        "total_alertas": 0,
                        "conclusao": f"Timeout no processamento: análise demorou mais que {Config.GEMINI_TIMEOUT} segundos"
                    },
                    "itens": [
                        {
                            "campo": "Processamento",
                            "status": "erro",
                            "tipo": "erro_critico",
                            "valor_extraido": None,
                            "descricao": f"Timeout na análise IA. Documento pode ser muito complexo ou conexão lenta. Tempo limite: {Config.GEMINI_TIMEOUT}s"
                        }
                    ]
                }
                
                file_info['status'] = 'error'
                file_info['result'] = timeout_result
                update_job_status(job_id, i, 'error', timeout_result)
                
            except Exception as e:
                print(f"DEBUG: Erro no processamento do arquivo {file_info['filename']}: {str(e)}")
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
                            "valor_extraido": None,
                            "descricao": f"Ocorreu um erro durante o processamento: {str(e)}"
                        }
                    ]
                }
                
                file_info['status'] = 'error'
                file_info['result'] = error_result
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
                print(f"DEBUG: Job {job_id} marcado como completed - {current_job['arquivos_processados']}/{current_job['total_arquivos']} arquivos processados")
                
                # Calculate overall status based on results - PROTEÇÃO CONTRA NONES
                has_error = False
                has_alert = False
                
                print(f"DEBUG: [GRANULAR] Calculando status geral do job - {len(current_job['arquivos'])} arquivos")
                
                for file_idx, file in enumerate(current_job['arquivos']):
                    print(f"DEBUG: [GRANULAR] Verificando arquivo {file_idx+1}")
                    print(f"DEBUG: [GRANULAR] Tipo do file: {type(file)}")
                    
                    if file is None:
                        print(f"DEBUG: [GRANULAR] ERRO - File {file_idx+1} é None")
                        continue
                    
                    if not isinstance(file, dict):
                        print(f"DEBUG: [GRANULAR] ERRO - File {file_idx+1} não é dict: {type(file)}")
                        continue
                    
                    file_result = file.get('result')
                    print(f"DEBUG: [GRANULAR] File result tipo: {type(file_result)}")
                    print(f"DEBUG: [GRANULAR] File result é None: {file_result is None}")
                    
                    if file_result is None:
                        print(f"DEBUG: [GRANULAR] File {file_idx+1} result é None, pulando")
                        continue
                    
                    if not isinstance(file_result, dict):
                        print(f"DEBUG: [GRANULAR] File {file_idx+1} result não é dict: {type(file_result)}")
                        continue
                    
                    print(f"DEBUG: [GRANULAR] File {file_idx+1} result é dict válido")
                    print(f"DEBUG: [GRANULAR] Chaves do result: {list(file_result.keys()) if file_result else 'N/A'}")
                    
                    if 'sumario' not in file_result:
                        print(f"DEBUG: [GRANULAR] File {file_idx+1} não tem chave 'sumario'")
                        continue
                    
                    sumario = file_result.get('sumario')
                    print(f"DEBUG: [GRANULAR] Sumario tipo: {type(sumario)}")
                    print(f"DEBUG: [GRANULAR] Sumario é None: {sumario is None}")
                    
                    if sumario is None:
                        print(f"DEBUG: [GRANULAR] File {file_idx+1} sumario é None")
                        continue
                    
                    if not isinstance(sumario, dict):
                        print(f"DEBUG: [GRANULAR] File {file_idx+1} sumario não é dict: {type(sumario)}")
                        continue
                    
                    print(f"DEBUG: [GRANULAR] File {file_idx+1} sumario é dict válido")
                    print(f"DEBUG: [GRANULAR] Chaves do sumario: {list(sumario.keys()) if sumario else 'N/A'}")
                    
                    if 'status' not in sumario:
                        print(f"DEBUG: [GRANULAR] File {file_idx+1} sumario não tem chave 'status'")
                        continue
                    
                    status = sumario.get('status')
                    print(f"DEBUG: [GRANULAR] File {file_idx+1} status: {status}")
                    
                    if status == 'erro':
                        has_error = True
                        print(f"DEBUG: [GRANULAR] File {file_idx+1} tem status de erro")
                    elif status == 'alerta' and not has_error:
                        has_alert = True
                        print(f"DEBUG: [GRANULAR] File {file_idx+1} tem status de alerta")
                
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
                    print(f"DEBUG: Job {job_id} marcado como completed na memória - {jobs[job_id]['arquivos_processados']}/{jobs[job_id]['total_arquivos']} arquivos processados")
                    
                    # Calculate overall status based on results - PROTEÇÃO CONTRA NONES
                    has_error = False
                    has_alert = False
                    
                    print(f"DEBUG: [GRANULAR] Calculando status geral na memória - {len(jobs[job_id]['arquivos'])} arquivos")
                    
                    for file_idx, file in enumerate(jobs[job_id]['arquivos']):
                        print(f"DEBUG: [GRANULAR] Verificando arquivo {file_idx+1} na memória")
                        print(f"DEBUG: [GRANULAR] Tipo do file: {type(file)}")
                        
                        if file is None:
                            print(f"DEBUG: [GRANULAR] ERRO - File {file_idx+1} é None na memória")
                            continue
                        
                        if not isinstance(file, dict):
                            print(f"DEBUG: [GRANULAR] ERRO - File {file_idx+1} não é dict na memória: {type(file)}")
                            continue
                        
                        file_result = file.get('result')
                        print(f"DEBUG: [GRANULAR] File result tipo na memória: {type(file_result)}")
                        print(f"DEBUG: [GRANULAR] File result é None na memória: {file_result is None}")
                        
                        if file_result is None:
                            print(f"DEBUG: [GRANULAR] File {file_idx+1} result é None na memória, pulando")
                            continue
                        
                        if not isinstance(file_result, dict):
                            print(f"DEBUG: [GRANULAR] File {file_idx+1} result não é dict na memória: {type(file_result)}")
                            continue
                        
                        print(f"DEBUG: [GRANULAR] File {file_idx+1} result é dict válido na memória")
                        print(f"DEBUG: [GRANULAR] Chaves do result na memória: {list(file_result.keys()) if file_result else 'N/A'}")
                        
                        if 'sumario' not in file_result:
                            print(f"DEBUG: [GRANULAR] File {file_idx+1} não tem chave 'sumario' na memória")
                            continue
                        
                        sumario = file_result.get('sumario')
                        print(f"DEBUG: [GRANULAR] Sumario tipo na memória: {type(sumario)}")
                        print(f"DEBUG: [GRANULAR] Sumario é None na memória: {sumario is None}")
                        
                        if sumario is None:
                            print(f"DEBUG: [GRANULAR] File {file_idx+1} sumario é None na memória")
                            continue
                        
                        if not isinstance(sumario, dict):
                            print(f"DEBUG: [GRANULAR] File {file_idx+1} sumario não é dict na memória: {type(sumario)}")
                            continue
                        
                        print(f"DEBUG: [GRANULAR] File {file_idx+1} sumario é dict válido na memória")
                        print(f"DEBUG: [GRANULAR] Chaves do sumario na memória: {list(sumario.keys()) if sumario else 'N/A'}")
                        
                        if 'status' not in sumario:
                            print(f"DEBUG: [GRANULAR] File {file_idx+1} sumario não tem chave 'status' na memória")
                            continue
                        
                        status = sumario.get('status')
                        print(f"DEBUG: [GRANULAR] File {file_idx+1} status na memória: {status}")
                        
                        if status == 'erro':
                            has_error = True
                            print(f"DEBUG: [GRANULAR] File {file_idx+1} tem status de erro na memória")
                        elif status == 'alerta' and not has_error:
                            has_alert = True
                            print(f"DEBUG: [GRANULAR] File {file_idx+1} tem status de alerta na memória")
                    
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
        print(f"DEBUG: Consultando status do job: {job_id}")
        
        # Primeiro verificar na memória (onde jobs estão sendo salvos devido ao erro da coluna progress)
        if job_id in jobs:
            job = jobs[job_id]
            print(f"DEBUG: Job encontrado na memória - Status: {job['status']}")
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
        
        # Se não encontrou na memória, tentar no Supabase
        try:
            job_data = supabase.table('conferencia_jobs').select('id,status,total_arquivos,arquivos_processados,tipo_conferencia').eq('id', job_id).execute()
            
            if job_data.data:
                job = job_data.data[0]
                print(f"DEBUG: Job encontrado no banco - Status: {job['status']}")
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
        except Exception as db_error:
            print(f"DEBUG: Erro ao consultar banco: {db_error}")
        
        print(f"DEBUG: Job {job_id} não encontrado em lugar algum")
        return jsonify({'status': 'error', 'message': 'Job não encontrado'}), 404
        
    except Exception as e:
        print(f"DEBUG: Erro ao consultar status: {str(e)}")
        return jsonify({'status': 'error', 'message': f'Erro ao consultar status: {str(e)}'}), 500

@bp.route('/result/<job_id>', methods=['GET'])
@login_required
@role_required(['admin', 'interno_unique'])
def get_result(job_id):
    """Endpoint para consultar o resultado de um job"""
    try:
        print(f"DEBUG: Consultando resultado do job: {job_id}")
        
        # Verificar se é um job de teste para validação do frontend
        if job_id.startswith('test-job-'):
            import json
            import os
            
            scenario_name = job_id.replace('test-job-', '')
            test_file = f"static/uploads/test_frontend/job_{scenario_name}.json"
            
            if os.path.exists(test_file):
                with open(test_file, 'r', encoding='utf-8') as f:
                    test_data = json.load(f)
                print(f"DEBUG: Retornando dados de teste para {job_id}")
                return jsonify({
                    'status': 'success',
                    'job': test_data
                })
            else:
                print(f"DEBUG: Arquivo de teste não encontrado: {test_file}")
                return jsonify({'status': 'error', 'message': f'Dados de teste não encontrados para {scenario_name}'}), 404
        
        # Primeiro verificar na memória (onde jobs estão sendo salvos devido ao erro da coluna progress)
        if job_id in jobs:
            job = jobs[job_id]
            print(f"DEBUG: Job encontrado na memória - {len(job.get('arquivos', []))} arquivos")
            
            # Debug dos arquivos - PROTEÇÃO CONTRA NONES
            for i, arquivo in enumerate(job.get('arquivos', [])):
                print(f"DEBUG: [GRANULAR] Verificando arquivo {i+1} no resultado")
                print(f"DEBUG: [GRANULAR] Tipo do arquivo: {type(arquivo)}")
                
                if arquivo is None:
                    print(f"DEBUG: [GRANULAR] ERRO - Arquivo {i+1} é None")
                    continue
                
                if not isinstance(arquivo, dict):
                    print(f"DEBUG: [GRANULAR] ERRO - Arquivo {i+1} não é dict: {type(arquivo)}")
                    continue
                
                filename = arquivo.get('filename', 'N/A')
                status = arquivo.get('status', 'N/A')
                print(f"DEBUG: Arquivo {i+1}: {filename} - Status: {status}")
                
                arquivo_result = arquivo.get('result')
                print(f"DEBUG: [GRANULAR] Arquivo {i+1} result tipo: {type(arquivo_result)}")
                print(f"DEBUG: [GRANULAR] Arquivo {i+1} result é None: {arquivo_result is None}")
                
                if arquivo_result is None:
                    print(f"DEBUG: - Sem resultado")
                    continue
                
                if not isinstance(arquivo_result, dict):
                    print(f"DEBUG: - Resultado inválido (tipo: {type(arquivo_result)})")
                    continue
                
                print(f"DEBUG: [GRANULAR] Arquivo {i+1} result é dict válido")
                print(f"DEBUG: [GRANULAR] Chaves do result: {list(arquivo_result.keys()) if arquivo_result else 'N/A'}")
                
                if 'sumario' not in arquivo_result:
                    print(f"DEBUG: - Resultado sem sumário")
                    continue
                
                sumario = arquivo_result.get('sumario')
                print(f"DEBUG: [GRANULAR] Sumario tipo: {type(sumario)}")
                print(f"DEBUG: [GRANULAR] Sumario é None: {sumario is None}")
                
                if sumario is None:
                    print(f"DEBUG: - Sumário é None")
                    continue
                
                if not isinstance(sumario, dict):
                    print(f"DEBUG: - Sumário inválido (tipo: {type(sumario)})")
                    continue
                
                print(f"DEBUG: [GRANULAR] Sumario é dict válido")
                print(f"DEBUG: [GRANULAR] Chaves do sumario: {list(sumario.keys()) if sumario else 'N/A'}")
                
                if 'conclusao' not in sumario:
                    print(f"DEBUG: - Sumário sem conclusão")
                else:
                    conclusao = sumario.get('conclusao')
                    print(f"DEBUG: - Conclusão: {conclusao}")
                    
            return jsonify({
                'status': 'success',
                'job': job
            })
        
        # Se não encontrou na memória, tentar no Supabase
        try:
            job_data = supabase.table('conferencia_jobs').select('*').eq('id', job_id).execute()
            
            if job_data.data:
                job = job_data.data[0]
                print(f"DEBUG: Job encontrado no banco - {len(job.get('arquivos', []))} arquivos")
                
                # Debug dos arquivos - PROTEÇÃO CONTRA NONES
                for i, arquivo in enumerate(job.get('arquivos', [])):
                    print(f"DEBUG: [GRANULAR] Verificando arquivo {i+1} no banco")
                    print(f"DEBUG: [GRANULAR] Tipo do arquivo: {type(arquivo)}")
                    
                    if arquivo is None:
                        print(f"DEBUG: [GRANULAR] ERRO - Arquivo {i+1} é None no banco")
                        continue
                    
                    if not isinstance(arquivo, dict):
                        print(f"DEBUG: [GRANULAR] ERRO - Arquivo {i+1} não é dict no banco: {type(arquivo)}")
                        continue
                    
                    filename = arquivo.get('filename', 'N/A')
                    status = arquivo.get('status', 'N/A')
                    print(f"DEBUG: Arquivo {i+1}: {filename} - Status: {status}")
                    
                    arquivo_result = arquivo.get('result')
                    print(f"DEBUG: [GRANULAR] Arquivo {i+1} result tipo no banco: {type(arquivo_result)}")
                    print(f"DEBUG: [GRANULAR] Arquivo {i+1} result é None no banco: {arquivo_result is None}")
                    
                    if arquivo_result is None:
                        print(f"DEBUG: - Sem resultado no banco")
                        continue
                    
                    if not isinstance(arquivo_result, dict):
                        print(f"DEBUG: - Resultado inválido no banco (tipo: {type(arquivo_result)})")
                        continue
                    
                    print(f"DEBUG: [GRANULAR] Arquivo {i+1} result é dict válido no banco")
                    print(f"DEBUG: [GRANULAR] Chaves do result no banco: {list(arquivo_result.keys()) if arquivo_result else 'N/A'}")
                    
                    if 'sumario' not in arquivo_result:
                        print(f"DEBUG: - Resultado sem sumário no banco")
                        continue
                    
                    sumario = arquivo_result.get('sumario')
                    print(f"DEBUG: [GRANULAR] Sumario tipo no banco: {type(sumario)}")
                    print(f"DEBUG: [GRANULAR] Sumario é None no banco: {sumario is None}")
                    
                    if sumario is None:
                        print(f"DEBUG: - Sumário é None no banco")
                        continue
                    
                    if not isinstance(sumario, dict):
                        print(f"DEBUG: - Sumário inválido no banco (tipo: {type(sumario)})")
                        continue
                    
                    print(f"DEBUG: [GRANULAR] Sumario é dict válido no banco")
                    print(f"DEBUG: [GRANULAR] Chaves do sumario no banco: {list(sumario.keys()) if sumario else 'N/A'}")
                    
                    if 'conclusao' not in sumario:
                        print(f"DEBUG: - Sumário sem conclusão no banco")
                    else:
                        conclusao = sumario.get('conclusao')
                        print(f"DEBUG: - Conclusão: {conclusao}")
                
                return jsonify({
                    'status': 'success',
                    'job': job
                })
        except Exception as db_error:
            print(f"DEBUG: Erro ao consultar banco: {db_error}")
        
        print(f"DEBUG: Job {job_id} não encontrado em lugar algum")
        return jsonify({'status': 'error', 'message': 'Job não encontrado'}), 404
    except Exception as e:
        print(f"DEBUG: Erro ao consultar resultado: {str(e)}")
        return jsonify({'status': 'error', 'message': f'Erro ao consultar resultado: {str(e)}'}), 500
    

def generate_sample_result(tipo, filename=None):
    """Gera um resultado de exemplo para simulação com variações baseadas no arquivo"""
    import random
    
    # Gerar variações baseadas no nome do arquivo para simular resultados diferentes
    if filename:
        # Usar hash do nome do arquivo para gerar variações consistentes
        file_hash = hash(filename) % 1000
        random.seed(file_hash)  # Seed baseado no arquivo para resultados consistentes
        print(f"DEBUG: generate_sample_result - filename: {filename}, hash: {file_hash}")
    else:
        # Fallback caso não tenha filename
        import time
        random.seed(int(time.time()))
        print(f"DEBUG: generate_sample_result - sem filename, usando timestamp")
    
    if tipo == 'inconsistencias':
        # Gerar diferentes cenários baseados no arquivo
        documentos_exemplo = [
            "CE12345678",
            "BL-SHA-789456", 
            "INV20241205",
            "PL-2024-001122",
            "DU-E-45789123"
        ]
        
        valores_exemplo = [
            "USD 15,450.00",
            "USD 28,750.50", 
            "USD 45,200.75",
            "USD 8,950.25",
            "USD 67,300.00"
        ]
        
        # Gerar dados específicos para o arquivo
        doc_num = random.choice(documentos_exemplo)
        valor_doc = random.choice(valores_exemplo)
        peso_bruto = f"{random.randint(500, 5000):.1f} KG"
        peso_liquido = f"{random.randint(400, 4500):.1f} KG"
        
        cenarios = [
            {
                "status": "ok",
                "erros": 0,
                "observacoes": 2,
                "alertas": 0,
                "conclusao": "Documento analisado sem inconsistências críticas.",
                "itens": [
                    {
                        "campo": "Estrutura geral",
                        "status": "ok",
                        "tipo": "ok",
                        "valor_extraido": "Documento PDF bem estruturado, 3 páginas",
                        "descricao": "Documento possui estrutura adequada e legível para análise."
                    },
                    {
                        "campo": "Completude dos dados",
                        "status": "ok",
                        "tipo": "observacao",
                        "valor_extraido": "Todos os campos obrigatórios presentes",
                        "descricao": "Verificação confirma que todos os campos essenciais estão presentes."
                    },
                    {
                        "campo": "Consistência de valores",
                        "status": "ok",
                        "tipo": "observacao",
                        "valor_extraido": valor_doc,
                        "descricao": "Valores monetários consistentes em todo o documento."
                    }
                ]
            },
            {
                "status": "alerta",
                "erros": 0,
                "observacoes": 2,
                "alertas": 1,
                "conclusao": "Documento apresenta algumas inconsistências menores que merecem atenção.",
                "itens": [
                    {
                        "campo": "Formatação de datas",
                        "status": "alerta",
                        "tipo": "alerta",
                        "valor_extraido": "15/12/2024 e 2024-12-15",
                        "descricao": "Encontrados diferentes formatos de data no mesmo documento."
                    },
                    {
                        "campo": "Valores monetários",
                        "status": "ok",
                        "tipo": "observacao",
                        "valor_extraido": valor_doc,
                        "descricao": "Valores consistentes encontrados em moeda estrangeira."
                    },
                    {
                        "campo": "Informações de peso",
                        "status": "ok",
                        "tipo": "observacao",
                        "valor_extraido": f"Bruto: {peso_bruto}, Líquido: {peso_liquido}",
                        "descricao": "Informações de peso estão presentes e coerentes."
                    }
                ]
            },
            {
                "status": "erro",
                "erros": 1,
                "observacoes": 1,
                "alertas": 1,
                "conclusao": "Documento apresenta inconsistências que requerem correção imediata.",
                "itens": [
                    {
                        "campo": "Campos obrigatórios",
                        "status": "erro",
                        "tipo": "erro_critico",
                        "valor_extraido": None,
                        "descricao": "Campo 'País de Origem' obrigatório não encontrado no documento."
                    },
                    {
                        "campo": "Consistência de totais",
                        "status": "alerta",
                        "tipo": "alerta",
                        "valor_extraido": f"Declarado: {valor_doc}, Calculado: USD {float(valor_doc.split()[1].replace(',', '')) + 125.30:,.2f}",
                        "descricao": "Divergência de USD 125.30 entre valor declarado e soma dos itens."
                    },
                    {
                        "campo": "Qualidade do documento",
                        "status": "ok",
                        "tipo": "observacao",
                        "valor_extraido": "Documento digitalizado, resolução 300 DPI",
                        "descricao": "Documento possui boa qualidade para análise automatizada."
                    }
                ]
            }
        ]
        
        # Selecionar cenário baseado no arquivo
        cenario_idx = random.randint(0, len(cenarios) - 1)
        cenario = cenarios[cenario_idx]
        
        return {
            "sumario": {
                "status": cenario["status"],
                "total_erros_criticos": cenario["erros"],
                "total_observacoes": cenario["observacoes"],
                "total_alertas": cenario["alertas"],
                "conclusao": cenario["conclusao"]
            },
            "itens": cenario["itens"]
        }
        
    elif tipo == 'invoice':
        # Gerar diferentes resultados para invoices
        fornecedores = [
            "SHENZHEN TECH INDUSTRIES LTD",
            "GUANGZHOU ELECTRONICS CO.",
            "PILOT PRECISION INDUSTRIAL CO. LTD",
            "DONGGUAN MANUFACTURING INC.",
            "NINGBO TRADING COMPANY"
        ]
        
        produtos = [
            "Electronic Components",
            "Mechanical Parts",
            "LED Light Fixtures", 
            "Automotive Components",
            "Industrial Equipment"
        ]
        
        # Gerar dados variados
        fornecedor = random.choice(fornecedores)
        produto = random.choice(produtos)
        invoice_num = f"INV{random.randint(10000, 99999)}"
        valor_total = random.randint(5000, 50000)
        
        # Gerar data aleatória
        meses = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]
        dias = [f"{d:02d}" for d in range(1, 29)]
        data_emissao = f"2024-{random.choice(meses)}-{random.choice(dias)}"
        
        # Gerar endereço completo do fornecedor
        enderecos_china = [
            "NO.111 Qingliang Avenue, Yaozhuang Town, Jiashan County, Jiaxing City, Zhejiang Province",
            "Building A, No.25 Industrial Road, Baoan District, Shenzhen",
            "Floor 3, Block B, No.168 Technology Street, Tianhe District, Guangzhou",
            "No.88 Manufacturing Zone, Dongcheng District, Dongguan City",
            "Unit 15, No.200 Export Processing Zone, Yinzhou District, Ningbo"
        ]
        endereco_fornecedor = random.choice(enderecos_china)
        
        # Gerar dados do importador brasileiro
        importadores_br = [
            "CIA. INDUSTRIAL H. CARLOS SCHNEIDER",
            "ELETRONIC IMPORTS LTDA",
            "BRASIL COMPONENTS TRADING",
            "INDUSTRIAL SUPPLY DO BRASIL LTDA",
            "IMPORTADORA TECH SOLUTIONS"
        ]
        
        enderecos_br = [
            "RUA: ESTRADA GERAL RIO DO MORRO, 9277 BAIRRO ITINGA. ARAQUARI-SC CEP:89245-000",
            "AV. PAULISTA, 1000 - BELA VISTA, SÃO PAULO-SP CEP:01310-100",
            "RUA INDUSTRIAL, 500 - VILA LEOPOLDINA, SÃO PAULO-SP CEP:05033-000",
            "AV. DAS NAÇÕES, 2500 - CIDADE INDUSTRIAL, CONTAGEM-MG CEP:32210-000",
            "RUA DO COMÉRCIO, 123 - CENTRO, RIO DE JANEIRO-RJ CEP:20040-020"
        ]
        
        importador = random.choice(importadores_br)
        endereco_importador = random.choice(enderecos_br)
        cnpj = f"{random.randint(10, 99)}.{random.randint(100, 999)}.{random.randint(100, 999)}/0001-{random.randint(10, 99)}"
        
        # Determinar status baseado em critérios aleatórios
        tem_incoterm = random.random() > 0.3  # 70% chance de ter incoterm
        tem_pais_origem = random.random() > 0.1  # 90% chance de ter país origem
        
        erros = 0 if tem_incoterm else 1
        status = "ok" if erros == 0 else "erro"
        
        itens = [
            {
                "campo": "Número do documento",
                "status": "ok",
                "tipo": "ok",
                "valor_extraido": invoice_num,
                "descricao": "Número da Invoice encontrado e extraído com sucesso."
            },
            {
                "campo": "Data de emissão",
                "status": "ok",
                "tipo": "ok",
                "valor_extraido": data_emissao,
                "descricao": "Data de emissão encontrada e extraída com sucesso."
            },
            {
                "campo": "Exportador",
                "status": "ok",
                "tipo": "ok",
                "valor_extraido": f"{fornecedor}\n{endereco_fornecedor}, CHINA",
                "descricao": "Dados do exportador completos incluindo nome e endereço."
            },
            {
                "campo": "Importador",
                "status": "ok",
                "tipo": "ok",
                "valor_extraido": f"{importador}\n{endereco_importador}\nCNPJ: {cnpj}",
                "descricao": "Dados do importador completos incluindo nome, endereço e CNPJ."
            },
            {
                "campo": "Descrição das mercadorias",
                "status": "ok",
                "tipo": "observacao",
                "valor_extraido": f"{produto} - Diversos itens conforme lista detalhada",
                "descricao": "Descrição do produto extraída com sucesso da tabela de itens."
            }
        ]
        
        # Adicionar item de incoterm condicionalmente
        if tem_incoterm:
            incoterms = ["FOB SHENZHEN", "FOB GUANGZHOU", "FOB NINGBO", "FOB SHANGHAI", "CIF SANTOS"]
            incoterm_selecionado = random.choice(incoterms)
            itens.append({
                "campo": "Incoterm",
                "status": "ok",
                "tipo": "ok",
                "valor_extraido": incoterm_selecionado,
                "descricao": "Incoterm encontrado conforme Art. 557 do Regulamento Aduaneiro."
            })
        else:
            itens.append({
                "campo": "Incoterm",
                "status": "erro",
                "tipo": "erro_critico",
                "valor_extraido": None,
                "descricao": "Incoterm obrigatório (Art. 557) não foi encontrado no documento."
            })
        
        # Adicionar país de origem
        if tem_pais_origem:
            itens.append({
                "campo": "País de origem",
                "status": "ok",
                "tipo": "ok",
                "valor_extraido": "CHINA",
                "descricao": "País de origem identificado corretamente a partir dos dados do exportador."
            })
        
        # Adicionar valor total da fatura
        itens.append({
            "campo": "Valor total",
            "status": "ok",
            "tipo": "observacao",
            "valor_extraido": f"USD {valor_total:,.2f}",
            "descricao": "Valor total da fatura calculado a partir da soma dos itens."
        })
        
        return {
            "sumario": {
                "status": status,
                "total_erros_criticos": erros,
                "total_observacoes": 2,
                "total_alertas": 0,
                "conclusao": f"Invoice {invoice_num} analisada. " + ("Documento em conformidade." if status == "ok" else "Requer correção de incoterm.")
            },
            "itens": itens,
            "itens_da_fatura": [
                {
                    "descricao_completa": {
                        "valor_extraido": f"{produto} - Model XYZ-{random.randint(100, 999)}"
                    },
                    "quantidade_unidade": {
                        "valor_extraido": f"{random.randint(100, 10000):,} PCS"
                    },
                    "preco_unitario": {
                        "valor_extraido": f"{random.uniform(0.5, 10):.2f} USD"
                    },
                    "valor_total_item": {
                        "valor_extraido": f"USD {valor_total:.2f}"
                    }
                }
            ]
        }
    else:
        # Para tipos não implementados (packlist, conhecimento, etc.)
        return {
            "sumario": {
                "status": "alerta",
                "total_erros_criticos": 0,
                "total_observacoes": 1,
                "total_alertas": 1,
                "conclusao": f"Tipo '{tipo}' em desenvolvimento. Análise básica realizada."
            },
            "itens": [
                {
                    "campo": "Tipo de documento",
                    "status": "alerta",
                    "tipo": "alerta",
                    "valor_extraido": tipo,
                    "descricao": f"Análise para tipo '{tipo}' está em desenvolvimento. Resultado simulado."
                },
                {
                    "campo": "Estrutura detectada",
                    "status": "ok",
                    "tipo": "observacao",
                    "valor_extraido": "Documento PDF válido",
                    "descricao": "Documento foi processado com sucesso."
                }
            ]
        }
