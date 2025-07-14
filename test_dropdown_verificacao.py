import requests
import json

# Teste do endpoint de filtros
url = "http://localhost:5000/materiais/bypass-filter-options"

try:
    response = requests.get(url)
    print(f"Status code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Endpoint funcionando!")
        print(f"Materiais: {len(data.get('materiais', []))} opções")
        print(f"Clientes: {len(data.get('clientes', []))} opções")
        print(f"Modais: {len(data.get('modais', []))} opções")
        print(f"Canais: {len(data.get('canais', []))} opções")
        
        # Mostrar algumas opções para verificar
        print("\nExemplos de materiais:", data.get('materiais', [])[:5])
        print("Exemplos de clientes:", data.get('clientes', [])[:3])
        print("Modais disponíveis:", data.get('modais', []))
        print("Canais disponíveis:", data.get('canais', []))
        
    else:
        print(f"❌ Erro {response.status_code}: {response.text}")
        
except Exception as e:
    print(f"❌ Erro de conexão: {e}")
