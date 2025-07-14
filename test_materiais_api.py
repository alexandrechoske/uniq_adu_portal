import requests
import json

# Configuração do teste
BASE_URL = "http://127.0.0.1:5000"
SESSION = requests.Session()

def test_materiais_api():
    """Testa a API de materiais sem login"""
    print("=== Testando API de Materiais ===")
    
    # Testar endpoint de debug sem login
    try:
        response = SESSION.get(f"{BASE_URL}/debug/check-materiais-cache")
        print(f"Debug Cache Status: {response.status_code}")
        if response.status_code == 200:
            print("Cache Debug Response:", response.text[:500])
    except Exception as e:
        print(f"Erro ao testar debug: {e}")
    
    # Teste com bypass de API key
    headers = {
        'X-API-Key': 'your-api-key-here',  # Teste com chave
        'Content-Type': 'application/json'
    }
    
    print("\n=== Testando endpoints com API Key ===")
    
    # Testar endpoint materiais_data
    try:
        response = SESSION.get(f"{BASE_URL}/materiais/materiais_data", headers=headers)
        print(f"Materiais Data Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print("Materiais Data Response:", json.dumps(data, indent=2))
    except Exception as e:
        print(f"Erro ao testar materiais_data: {e}")
    
    # Testar endpoint top-materiais
    try:
        response = SESSION.get(f"{BASE_URL}/materiais/api/top-materiais", headers=headers)
        print(f"Top Materiais Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print("Top Materiais Response:", json.dumps(data, indent=2))
    except Exception as e:
        print(f"Erro ao testar top-materiais: {e}")

if __name__ == "__main__":
    test_materiais_api()
