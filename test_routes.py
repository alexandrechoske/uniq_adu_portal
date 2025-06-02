#!/usr/bin/env python
# Utilitário para testar as rotas e o sistema de permissões
import requests
import sys
import json
from urllib.parse import urljoin

def test_endpoints(base_url):
    """Testa os principais endpoints da aplicação"""
    print(f"\n==== Testando endpoints em {base_url} ====")
    
    # Teste 1: Login
    print("\n--- Teste 1: Login ---")
    session = requests.Session()
    try:
        login_url = urljoin(base_url, '/login')
        # Apenas faça uma requisição GET para verificar se o endpoint existe
        response = session.get(login_url)
        print(f"Requisição para {login_url}: Status {response.status_code}")
        print(f"Título da página: {response.text[:100]}...")
    except Exception as e:
        print(f"Erro ao acessar {login_url}: {str(e)}")

    # Teste 2: Verificação de Sessão
    print("\n--- Teste 2: Verificação de Sessão ---")
    try:
        check_session_url = urljoin(base_url, '/paginas/check-session')
        response = session.get(check_session_url)
        print(f"Requisição para {check_session_url}: Status {response.status_code}")
        print(f"Resposta: {response.text[:200]}...")
    except Exception as e:
        print(f"Erro ao acessar {check_session_url}: {str(e)}")
    
    # Teste 3: API de Páginas
    print("\n--- Teste 3: API de Páginas ---")
    try:
        pages_api_url = urljoin(base_url, '/paginas/api')
        response = session.get(pages_api_url)
        print(f"Requisição para {pages_api_url}: Status {response.status_code}")
        print(f"Resposta: {response.text[:200]}...")
    except Exception as e:
        print(f"Erro ao acessar {pages_api_url}: {str(e)}")
        
    # Teste 4: Dashboard
    print("\n--- Teste 4: Dashboard ---")
    try:
        dashboard_url = urljoin(base_url, '/dashboard')
        response = session.get(dashboard_url)
        print(f"Requisição para {dashboard_url}: Status {response.status_code}")
        print(f"Título da página: {response.text[:100]}...")
    except Exception as e:
        print(f"Erro ao acessar {dashboard_url}: {str(e)}")

    print("\n==== Testes concluídos ====")

if __name__ == "__main__":
    base_url = "http://localhost:5000"  # URL padrão
    
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    
    test_endpoints(base_url)
