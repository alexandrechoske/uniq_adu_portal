#!/usr/bin/env python3
"""
Script de teste para verificar se o filtro de CNPJs está funcionando na página de Materiais
"""

import requests
import json

def test_materiais_endpoints():
    """Testa os endpoints de materiais para verificar o filtro de CNPJ"""
    
    base_url = "http://localhost:5000"  # Ajustar conforme necessário
    
    # Endpoints para testar
    endpoints = [
        "/materiais/api/kpis",
        "/materiais/api/top-materiais", 
        "/materiais/api/evolucao-mensal",
        "/materiais/api/despesas-composicao",
        "/materiais/api/canal-parametrizacao",
        "/materiais/api/clientes-por-material",
        "/materiais/api/detalhamento",
        "/materiais/api/radar-cliente-material",
        "/materiais/api/materiais-opcoes",
        "/materiais/api/linha-tempo-chegadas"
    ]
    
    print("🚀 Testando endpoints de Materiais com filtro de CNPJ...")
    
    for endpoint in endpoints:
        print(f"\n📍 Testando: {endpoint}")
        
        try:
            # Fazer requisição (assumindo que há autenticação via session)
            response = requests.get(f"{base_url}{endpoint}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Status: {response.status_code}")
                print(f"   📊 Response: {type(data)} com {len(str(data))} chars")
                
                # Verificar estrutura básica da resposta
                if isinstance(data, dict):
                    if 'status' in data:
                        print(f"   📈 Status API: {data.get('status')}")
                    if 'data' in data:
                        print(f"   📋 Dados: {type(data['data'])}")
            else:
                print(f"   ❌ Erro: {response.status_code}")
                print(f"   📝 Response: {response.text[:200]}...")
                
        except Exception as e:
            print(f"   ⚠️  Exceção: {str(e)}")
    
    print("\n🎯 Teste concluído!")

if __name__ == "__main__":
    test_materiais_endpoints()
