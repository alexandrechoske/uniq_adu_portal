from flask import Blueprint, jsonify
from extensions import supabase_admin
import requests
import os

bp = Blueprint('background_tasks', __name__, url_prefix='/background')

def update_importacoes_processos():
    """
    Função para atualizar importações-processos que foi removida do login
    para melhorar performance. Agora pode ser chamada via endpoint ou cron job.
    """
    try:
        response = requests.post(
            'https://ixytthtngeifjumvbuwe.supabase.co/functions/v1/att_importacoes-processos',
            headers={
                'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml4eXR0aHRuZ2VpZmp1bXZidXdlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDc5MjIwMDQsImV4cCI6MjA2MzQ5ODAwNH0.matnofV1H9hi2bEQGak6fo-RtmJIOyU455fcgsKbPfk',
                'Content-Type': 'application/json'
            },
            json={'name': 'Functions'},
            timeout=30  # Timeout de 30 segundos
        )
        return response.status_code == 200
    except Exception as e:
        print(f"[BACKGROUND] Erro ao atualizar importações: {str(e)}")
        return False

@bp.route('/update-importacoes', methods=['POST'])
def update_importacoes_endpoint():
    """
    Endpoint para atualizar importações-processos em background
    Pode ser chamado por cron jobs ou outros sistemas
    """
    # Verificar se o request vem de uma fonte autorizada (opcional)
    api_key = os.getenv('BACKGROUND_API_KEY')
    if api_key:
        from flask import request
        if request.headers.get('X-API-Key') != api_key:
            return jsonify({'error': 'Unauthorized'}), 401
    
    success = update_importacoes_processos()
    
    if success:
        return jsonify({
            'status': 'success',
            'message': 'Importações atualizadas com sucesso'
        })
    else:
        return jsonify({
            'status': 'error',
            'message': 'Erro ao atualizar importações'
        }), 500

@bp.route('/health')
def health_check():
    """
    Endpoint de health check para verificar se o serviço está funcionando
    """
    return jsonify({
        'status': 'healthy',
        'service': 'background_tasks'
    })
