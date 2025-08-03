#!/usr/bin/env python3
"""
Teste para otimização do cabeçalho do Dashboard Importações Resumido
"""

import os
import requests

def test_header_optimization():
    """Testa as otimizações do cabeçalho via API."""
    
    API_BYPASS_KEY = os.getenv('API_BYPASS_KEY')
    BASE_URL = 'http://localhost:5000'
    
    if not API_BYPASS_KEY:
        print("❌ Erro: API_BYPASS_KEY não encontrada no .env")
        return False
    
    headers = {
        'X-API-Key': API_BYPASS_KEY,
        'Content-Type': 'application/json'
    }
    
    try:
        print("🚀 Testando cabeçalho otimizado do Dashboard...")
        
        # Testar página principal
        response = requests.get(f"{BASE_URL}/dash-importacoes-resumido/", headers=headers)
        
        if response.status_code == 200:
            print("✅ Página principal carregou com sucesso")
            
            # Verificar se os elementos otimizados estão presentes
            content = response.text.lower()
            
            checks = [
                ("❌ Título DASHBOARD removido", "dashboard-title" not in content),
                ("❌ Info de página removida", "pagination-text" not in content), 
                ("✅ Total de processos mantido", "total-processos" in content),
                ("✅ Contadores modais mantidos", "count-maritimo" in content),
                ("✅ Cotações mantidas", "exchange-rates-top" in content),
                ("✅ Logo do cliente mantida", "client-logo" in content)
            ]
            
            for desc, passed in checks:
                status = "✅" if passed else "❌"
                print(f"{status} {desc}")
            
        else:
            print(f"❌ Erro na página: {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            return False
        
        # Testar API de dados
        response = requests.get(f"{BASE_URL}/dash-importacoes-resumido/api/data", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ API de dados funcionando")
            
            if data.get('success'):
                header_data = data.get('header', {})
                print(f"📊 Total processos: {header_data.get('total_processos', 0)}")
                print(f"🚢 Marítimo: {header_data.get('count_maritimo', 0)}")
                print(f"✈️ Aéreo: {header_data.get('count_aereo', 0)}")
                print(f"🚛 Terrestre: {header_data.get('count_terrestre', 0)}")
            else:
                print("⚠️ API retornou success=false")
                
        else:
            print(f"❌ Erro na API: {response.status_code}")
            return False
        
        print("\n🎯 Teste de otimização do cabeçalho concluído!")
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ Erro: Não foi possível conectar ao servidor Flask")
        print("💡 Certifique-se de que o servidor está rodando em http://localhost:5000")
        return False
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return False

if __name__ == '__main__':
    success = test_header_optimization()
    exit(0 if success else 1)
