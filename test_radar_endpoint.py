#!/usr/bin/env python3
"""
Teste rápido do endpoint de radar de materiais
"""

import requests
import json

def test_radar_endpoint():
    """Testa o endpoint do radar para verificar se está retornando JSON válido"""
    
    base_url = "http://localhost:5000"  # Ajustar conforme necessário
    endpoint = "/materiais/api/radar-cliente-material"
    
    print(f"🧪 Testando endpoint: {endpoint}")
    
    try:
        # Fazer requisição (assumindo que há autenticação via session)
        response = requests.get(f"{base_url}{endpoint}")
        
        print(f"📊 Status Code: {response.status_code}")
        print(f"📋 Content-Type: {response.headers.get('content-type', 'N/A')}")
        
        if response.status_code == 200:
            # Tentar fazer parse do JSON
            try:
                data = response.json()
                print(f"✅ JSON válido recebido")
                print(f"📈 Status API: {data.get('status', 'N/A')}")
                
                if data.get('data'):
                    labels = data['data'].get('labels', [])
                    datasets = data['data'].get('datasets', [])
                    print(f"🏷️  Labels: {len(labels)} itens")
                    print(f"📊 Datasets: {len(datasets)} itens")
                    
                    if labels:
                        print(f"🔤 Labels: {labels}")
                    if datasets:
                        print(f"📈 Primeiro dataset: {datasets[0].get('label', 'N/A')}")
                
                return True
                
            except json.JSONDecodeError as e:
                print(f"❌ Erro ao fazer parse do JSON: {e}")
                print(f"📝 Primeiros 500 chars da resposta:")
                print(f"   {response.text[:500]}...")
                return False
                
        else:
            print(f"❌ Erro HTTP: {response.status_code}")
            print(f"📝 Response: {response.text[:200]}...")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"⚠️  Erro de conexão: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Testando endpoint de radar de materiais...")
    success = test_radar_endpoint()
    print(f"\n{'✅ Teste concluído com sucesso!' if success else '❌ Teste falhou!'}")
