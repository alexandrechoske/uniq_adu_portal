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

# Prompts para análise IA
PROMPTS = {
    'inconsistencias': """
    Você é um sistema especializado em análise de documentos aduaneiros.
    Analise o documento fornecido e identifique possíveis inconsistências.
    Retorne uma análise estruturada em JSON com os problemas encontrados.
    """,
    'dados_estruturados': """
    Extraia dados estruturados do documento aduaneiro fornecido.
    Organize as informações em formato JSON com campos padronizados.
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
            'user_id': session['user']['id']
        }
        
        # Simular processamento (substituir por lógica real de IA)
        threading.Thread(target=background_process, args=(job_id, uploaded_files)).start()
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'files_count': len(uploaded_files),
            'errors': errors
        })
    
    return jsonify({
        'success': False,
        'message': 'Nenhum arquivo válido foi processado',
        'errors': errors
    }), 400

def background_process(job_id, files):
    """Processa arquivos em background"""
    try:
        total_files = len(files)
        
        for i, file_info in enumerate(files):
            if job_id not in jobs:
                break
                
            # Atualizar progresso
            progress = int((i / total_files) * 100)
            jobs[job_id]['progress'] = progress
            jobs[job_id]['current_file'] = file_info['original_name']
            
            # Simular processamento do arquivo
            time.sleep(2)  # Substituir por processamento real
            
            # Resultado simulado
            result = {
                'file': file_info['original_name'],
                'status': 'completed',
                'inconsistencias': [
                    'Dados de exemplo - implementar análise real'
                ],
                'dados_extraidos': {
                    'documento': file_info['original_name'],
                    'processado_em': datetime.now().isoformat()
                }
            }
            
            jobs[job_id]['results'].append(result)
        
        # Finalizar job
        if job_id in jobs:
            jobs[job_id]['status'] = 'completed'
            jobs[job_id]['progress'] = 100
            jobs[job_id]['completed_at'] = datetime.now()
            
    except Exception as e:
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

# Funções auxiliares para processamento de PDF (placeholder)
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
        return f"Erro ao extrair texto: {str(e)}"

def process_with_ai(text, prompt_template, api_key=None):
    """Processa texto com IA (placeholder para integração real)"""
    # Implementar integração real com Gemini ou outra IA
    return {
        "inconsistencias": ["Implementar análise real"],
        "dados_extraidos": {"status": "placeholder"}
    }
