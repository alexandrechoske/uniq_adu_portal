import requests
import json

# Configuração do teste
BASE_URL = "http://127.0.0.1:5000"

def test_debug_endpoints():
    """Testa todos os endpoints de debug"""
    print("=== Testando Endpoints de Debug ===")
    
    endpoints = [
        '/materiais/debug-materiais-data',
        '/materiais/debug-top-materiais',
        '/materiais/debug-evolucao-mensal',
        '/materiais/debug-modal-distribution',
        '/materiais/debug-canal-distribution'
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"{BASE_URL}{endpoint}")
            print(f"\n{endpoint}: Status {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Response: {json.dumps(data, indent=2)}")
            else:
                print(f"Error: {response.text}")
        except Exception as e:
            print(f"Error testing {endpoint}: {e}")

if __name__ == "__main__":
    test_debug_endpoints()
