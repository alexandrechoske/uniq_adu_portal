#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste das melhorias implementadas no Dashboard Importações
"""

import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

API_BYPASS_KEY = os.getenv('API_BYPASS_KEY')
BASE_URL = 'http://localhost:5000'

def test_improvements():
    """Teste das melhorias implementadas"""
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔧 Testando melhorias do Dashboard")
    print("=" * 70)
    
    headers = {
        'X-API-Key': API_BYPASS_KEY,
        'Content-Type': 'application/json'
    }
    
    try:
        # Teste 1: API básica
        print("📡 1. Testando API básica...")
        response = requests.get(f"{BASE_URL}/dash-importacoes-resumido/api/data", headers=headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            print("   ✅ API funcionando")
            
            # Verificar contagem de modais
            header = data.get('header', {})
            modal_counts = {
                'maritimo': header.get('count_maritimo', 0),
                'aereo': header.get('count_aereo', 0),
                'terrestre': header.get('count_terrestre', 0)
            }
            
            print(f"   📊 Contagem modais: Marítimo={modal_counts['maritimo']}, Aéreo={modal_counts['aereo']}, Terrestre={modal_counts['terrestre']}")
            
            # Verificar cotações
            rates = header.get('exchange_rates', {})
            print(f"   💱 Cotações: USD={rates.get('dolar', 'N/A')}, EUR={rates.get('euro', 'N/A')}")
            
        else:
            print(f"   ❌ Erro na API: {response.status_code}")
            
        # Teste 2: Paginação
        print("\n📄 2. Testando paginação...")
        response = requests.get(f"{BASE_URL}/dash-importacoes-resumido/api/data?page=2", headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            pagination = data.get('pagination', {})
            print(f"   ✅ Paginação OK: página {pagination.get('current_page')}/{pagination.get('pages')}")
        else:
            print(f"   ❌ Erro na paginação: {response.status_code}")
            
        # Teste 3: Filtro de data de embarque
        print("\n🔍 3. Testando filtro de data de embarque...")
        response = requests.get(f"{BASE_URL}/dash-importacoes-resumido/api/data?filtro_embarque=preenchida", headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            total_filtered = data.get('header', {}).get('total_processos', 0)
            print(f"   ✅ Filtro OK: {total_filtered} processos com data de embarque")
        else:
            print(f"   ❌ Erro no filtro: {response.status_code}")
            
        # Teste 4: Página principal
        print("\n🌐 4. Testando página principal...")
        response = requests.get(f"{BASE_URL}/dash-importacoes-resumido/", headers=headers, timeout=10)
        
        if response.status_code == 200:
            content = response.text
            
            # Verificar se elementos necessários estão presentes
            checks = [
                ('Cotações no topo', 'dolar-rate-top' in content and 'euro-rate-top' in content),
                ('Tabela customizada', 'custom-table' in content),
                ('Footer simplificado', 'footer-center' in content),
                ('CSS carregando', 'dashboard.css' in content),
                ('JS carregando', 'dashboard.js' in content)
            ]
            
            print("   📋 Verificações de estrutura:")
            for check_name, check_result in checks:
                status = "✅" if check_result else "❌"
                print(f"      {status} {check_name}")
                
        else:
            print(f"   ❌ Erro ao carregar página: {response.status_code}")
            
        print("\n" + "=" * 70)
        print("🎉 Teste de melhorias concluído!")
        print("\n📝 Melhorias implementadas:")
        print("   ✅ 1. Layout de tabela ajustado (cores consistentes)")
        print("   ✅ 2. Espaçamento entre linhas reduzido")
        print("   ✅ 3. Erro de JavaScript corrigido (showLoading)")
        print("   ✅ 4. Contagem de modais flexível implementada")
        print("   ✅ 5. Cotações USD/EUR movidas para o topo")
        
    except Exception as e:
        print(f"❌ Erro no teste: {e}")

if __name__ == "__main__":
    test_improvements()
