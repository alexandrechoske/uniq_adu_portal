#!/usr/bin/env python3
"""
Teste para verificar rotas corrigidas
"""
import requests

def test_routes():
    headers = {"X-API-Key": "uniq_api_2025_dev_bypass_key"}
    base_url = "http://localhost:5000"
    
    routes_to_test = [
        "/usuarios/",
        "/config/logos-clientes",
        "/config/icones-materiais",
        "/dashboard-executivo/",
        "/dashboard-materiais/"
    ]
    
    print("=== TESTE DAS ROTAS CORRIGIDAS ===")
    
    for route in routes_to_test:
        try:
            response = requests.get(f"{base_url}{route}", headers=headers, timeout=10)
            status = "✅ OK" if response.status_code == 200 else f"❌ {response.status_code}"
            size = f"{len(response.text)} chars"
            
            # Verifica se contém erros de template
            has_error = "BuildError" in response.text or "dashboard_v2.static" in response.text
            error_status = "❌ ERRO TEMPLATE" if has_error else "✅ Template OK"
            
            print(f"{route:<25} | {status:<10} | {size:<12} | {error_status}")
            
        except Exception as e:
            print(f"{route:<25} | ❌ ERRO: {e}")

if __name__ == "__main__":
    import time
    print("Aguardando servidor inicializar...")
    time.sleep(5)
    test_routes()
