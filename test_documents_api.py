#!/usr/bin/env python3
"""
Teste dos endpoints de documentos
Este script testa os endpoints da API de documentos
"""

import requests
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

BASE_URL = "http://127.0.0.1:5000"
API_BYPASS_KEY = os.getenv('API_BYPASS_KEY')

def test_document_endpoints():
    """Testa os endpoints de documentos"""
    
    print("🔍 Testando endpoints de documentos...")
    
    # Headers com bypass de autenticação
    headers = {
        'X-API-Key': API_BYPASS_KEY,
        'Content-Type': 'application/json'
    }
    
    # 1. Testar endpoint de teste
    print("\n1. Testando endpoint de teste...")
    try:
        response = requests.get(f"{BASE_URL}/api/documents/test-upload", headers=headers)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("✅ Endpoint de teste funcionando")
        else:
            print(f"❌ Erro no endpoint de teste: {response.text}")
    except Exception as e:
        print(f"❌ Erro ao testar endpoint: {e}")
    
    # 2. Testar listagem de documentos de um processo
    print("\n2. Testando listagem de documentos...")
    test_ref_unique = "TESTE-2024-001"  # Processo fictício para teste
    try:
        response = requests.get(f"{BASE_URL}/api/documents/process/{test_ref_unique}", headers=headers)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("✅ Endpoint de listagem funcionando")
            data = response.json()
            print(f"Documentos encontrados: {len(data.get('documents', []))}")
        else:
            print(f"❌ Erro na listagem: {response.text}")
    except Exception as e:
        print(f"❌ Erro ao testar listagem: {e}")
    
    print("\n✨ Teste de endpoints concluído!")

if __name__ == "__main__":
    test_document_endpoints()
