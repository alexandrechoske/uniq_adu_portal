#!/usr/bin/env python3
"""
Teste para verificar dashboard materiais
"""
import requests

def test_materiais():
    headers = {"X-API-Key": "uniq_api_2025_dev_bypass_key"}
    
    try:
        response = requests.get("http://localhost:5000/dashboard-materiais/", headers=headers, timeout=10)
        content = response.text
        
        print("=== DASHBOARD MATERIAIS ===")
        print(f"Status: {response.status_code}")
        print(f"Tamanho: {len(content)}")
        
        # Indicadores específicos do dashboard de materiais
        if "Dashboard de Materiais" in content:
            print("✅ Título 'Dashboard de Materiais' encontrado")
        else:
            print("❌ Título 'Dashboard de Materiais' NÃO encontrado")
            
        if "mat-total-processos" in content:
            print("✅ KPIs de materiais encontrados")
        else:
            print("❌ KPIs de materiais NÃO encontrados")
            
        if "top-materiais-chart" in content:
            print("✅ Charts de materiais encontrados")
        else:
            print("❌ Charts de materiais NÃO encontrados")
            
    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    test_materiais()
