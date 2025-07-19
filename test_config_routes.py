#!/usr/bin/env python3
"""
Teste específico para as rotas de config
"""
import requests

def test_config_routes():
    headers = {"X-API-Key": "uniq_api_2025_dev_bypass_key"}
    base_url = "http://localhost:5000"
    
    routes_to_test = [
        "/config/logos-clientes",
        "/config/icones-materiais"
    ]
    
    print("=== TESTE DAS ROTAS DE CONFIG ===")
    
    for route in routes_to_test:
        try:
            response = requests.get(f"{base_url}{route}", headers=headers, timeout=10)
            status = "✅ OK" if response.status_code == 200 else f"❌ {response.status_code}"
            size = f"{len(response.text)} chars"
            
            # Verifica erros específicos
            template_error = "TemplateNotFound" in response.text
            build_error = "BuildError" in response.text
            
            if template_error:
                error_status = "❌ Template não encontrado"
            elif build_error:
                error_status = "❌ Erro de build de URL"
            elif response.status_code == 200:
                error_status = "✅ OK"
            else:
                error_status = f"❌ HTTP {response.status_code}"
            
            print(f"{route:<30} | {status:<10} | {size:<12} | {error_status}")
            
            # Se houver erro, mostrar detalhes
            if response.status_code != 200:
                print(f"   Erro detalhado: {response.text[:200]}...")
            
        except Exception as e:
            print(f"{route:<30} | ❌ ERRO: {e}")

if __name__ == "__main__":
    import time
    print("Aguardando servidor...")
    time.sleep(3)
    test_config_routes()
