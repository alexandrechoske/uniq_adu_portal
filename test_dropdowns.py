#!/usr/bin/env python3
"""
Teste para verificar se os dropdowns de filtros estão funcionando
"""

import requests
import json

def test_filter_options():
    """Teste do endpoint de opções de filtro"""
    print("🧪 Testando endpoint de opções de filtro...")
    
    response = requests.get("http://localhost:5000/materiais/bypass-filter-options")
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Endpoint funcionando!")
        print(f"   Materiais: {len(data['materiais'])} opções")
        print(f"   Clientes: {len(data['clientes'])} opções")
        print(f"   Modais: {len(data['modais'])} opções")
        print(f"   Canais: {len(data['canais'])} opções")
        
        print("\n📋 Exemplos de opções:")
        print(f"   Materiais: {data['materiais'][:3]}...")
        print(f"   Clientes: {data['clientes'][:2]}...")
        print(f"   Modais: {data['modais']}")
        print(f"   Canais: {data['canais']}")
        
        return True
    else:
        print(f"❌ Erro: {response.status_code}")
        return False

def main():
    print("🚀 TESTE DOS DROPDOWNS DE FILTROS")
    print("=" * 50)
    
    if test_filter_options():
        print("\n✅ Dropdowns devem estar funcionando!")
        print("💡 Abra o modal de filtros na página para verificar visualmente")
    else:
        print("\n❌ Problema com os dropdowns")

if __name__ == "__main__":
    main()
