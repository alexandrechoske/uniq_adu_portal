#!/usr/bin/env python3
"""
Teste simples dos filtros de materiais
"""
import requests
from datetime import datetime, timedelta

def test_filter_modal_aerea():
    """Teste filtro por modal aéreo"""
    print("🧪 Testando filtro por modal AEREA...")
    
    url = "http://localhost:5000/materiais/bypass-materiais-data"
    params = {'modal': 'AEREA'}
    
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Filtro aplicado com sucesso!")
        print(f"   Total de processos: {data['total_processos']}")
        print(f"   Valor total: R$ {data['valor_total']:,.2f}")
        return True
    else:
        print(f"❌ Erro: {response.status_code}")
        return False

def test_filter_date_range():
    """Teste filtro por período específico"""
    print("\n🧪 Testando filtro por período...")
    
    # Últimos 7 dias
    hoje = datetime.now()
    semana_atras = hoje - timedelta(days=7)
    
    url = "http://localhost:5000/materiais/bypass-materiais-data"
    params = {
        'data_inicio': semana_atras.strftime('%Y-%m-%d'),
        'data_fim': hoje.strftime('%Y-%m-%d')
    }
    
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Filtro de data aplicado com sucesso!")
        print(f"   Período: {params['data_inicio']} até {params['data_fim']}")
        print(f"   Total de processos: {data['total_processos']}")
        return True
    else:
        print(f"❌ Erro: {response.status_code}")
        return False

def test_filter_material():
    """Teste filtro por material"""
    print("\n🧪 Testando filtro por material...")
    
    url = "http://localhost:5000/materiais/bypass-materiais-data"
    params = {'material': 'FERRAMENTA'}
    
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Filtro por material aplicado com sucesso!")
        print(f"   Material: {params['material']}")
        print(f"   Total de processos: {data['total_processos']}")
        return True
    else:
        print(f"❌ Erro: {response.status_code}")
        return False

def test_combined_filters():
    """Teste filtros combinados"""
    print("\n🧪 Testando filtros combinados...")
    
    url = "http://localhost:5000/materiais/bypass-materiais-data"
    params = {
        'modal': 'AEREA',
        'material': 'FERRAMENTA'
    }
    
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Filtros combinados aplicados com sucesso!")
        print(f"   Modal: {params['modal']}")
        print(f"   Material: {params['material']}")
        print(f"   Total de processos: {data['total_processos']}")
        return True
    else:
        print(f"❌ Erro: {response.status_code}")
        return False

def main():
    print("🚀 TESTE DOS FILTROS DE MATERIAIS")
    print("=" * 50)
    
    tests = [
        test_filter_modal_aerea,
        test_filter_date_range,
        test_filter_material,
        test_combined_filters
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print("\n📊 RESULTADOS:")
    print("=" * 50)
    passed = sum(results)
    total = len(results)
    print(f"✅ Testes passaram: {passed}/{total}")
    
    if passed == total:
        print("🎉 Todos os filtros estão funcionando corretamente!")
    else:
        print("⚠️  Alguns filtros precisam de ajustes")

if __name__ == "__main__":
    main()
