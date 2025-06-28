#!/usr/bin/env python3
"""
Script para testar endpoint de KPIs corrigido
"""
import requests
import json

def test_kpis_endpoint():
    """Testa o endpoint de KPIs"""
    try:
        # URL base - usando o endpoint de debug temporário
        base_url = "http://127.0.0.1:5000/materiais/api/kpis-debug"
        
        print("🧪 Testando endpoint de KPIs...")
        
        response = requests.get(base_url)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Status: {response.status_code}")
            print(f"📊 Resposta:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            
            if data.get('success'):
                kpis = data.get('data', {})
                print("\n🔢 KPIs encontrados:")
                for key, value in kpis.items():
                    print(f"  • {key}: {value.get('formatted', 'N/A')} ({value.get('label', 'N/A')})")
            else:
                print(f"❌ Erro: {data.get('error', 'Desconhecido')}")
        else:
            print(f"❌ Erro HTTP: {response.status_code}")
            print(f"Resposta: {response.text}")
            
    except Exception as e:
        print(f"❌ Erro na requisição: {str(e)}")

if __name__ == "__main__":
    print("🚀 Testando endpoints de materiais corrigidos\n")
    test_kpis_endpoint()
