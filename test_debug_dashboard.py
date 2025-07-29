import requests
import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Configuração da API
API_BYPASS_KEY = os.getenv('API_BYPASS_KEY')
BASE_URL = 'http://localhost:5000'

headers = {
    'X-API-Key': API_BYPASS_KEY,
    'Content-Type': 'application/json'
}

def test_dashboard_executivo_detailed():
    """Testa o dashboard executivo com detalhes do erro"""
    print("=== TESTE DETALHADO: Dashboard Executivo ===")
    
    try:
        response = requests.get(f"{BASE_URL}/dashboard-executivo/", headers=headers, timeout=30)
        print(f"Status Code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        
        if response.status_code == 500:
            print("ERRO 500 - Conteúdo da resposta:")
            print(response.text[:2000])  # Primeiros 2000 caracteres
        elif response.status_code == 200:
            print("✅ Dashboard funcionando!")
            content = response.text
            if 'principais-materiais-table' in content:
                print("✅ Tabela de materiais encontrada")
            else:
                print("❌ Tabela de materiais não encontrada")
        else:
            print(f"Status inesperado: {response.status_code}")
            print(response.text[:1000])
            
    except Exception as e:
        print(f"❌ Erro de conexão: {str(e)}")

if __name__ == "__main__":
    test_dashboard_executivo_detailed()
