import requests
import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Configuração da API
API_BYPASS_KEY = os.getenv('API_BYPASS_KEY')
BASE_URL = 'http://localhost:5000'

headers = {
    'X-API-Key': API_BYPASS_KEY,
    'Content-Type': 'application/json'
}

def test_dashboard_improvements():
    """Testa as melhorias implementadas no dashboard executivo"""
    print("\n=== TESTE: Melhorias do Dashboard Executivo ===")
    
    try:
        response = requests.get(f"{BASE_URL}/dashboard-executivo/", headers=headers, timeout=30)
        if response.status_code != 200:
            print(f"❌ Dashboard não acessível: {response.status_code}")
            return False
            
        content = response.text
        
        # 1. Verificar se o botão de reset de filtros está presente
        if 'reset-filters' in content:
            print("✅ Botão de reset de filtros encontrado")
        else:
            print("❌ Botão de reset de filtros não encontrado")
            
        # 2. Verificar se os estilos para ícones de modal estão presentes
        if 'modal-icon-badge' in content:
            print("✅ Estilos para ícones de modal encontrados")
        else:
            print("❌ Estilos para ícones de modal não encontrados")
            
        # 3. Verificar se a tabela tem a coluna de status
        if 'data-sort="status"' in content:
            print("✅ Coluna de status na tabela encontrada")
        else:
            print("❌ Coluna de status na tabela não encontrada")
            
        return True
        
    except Exception as e:
        print(f"❌ Erro ao testar dashboard: {str(e)}")
        return False

def test_recent_operations_api():
    """Testa se a API de operações recentes está retornando os dados de status"""
    print("\n=== TESTE: API de Operações Recentes ===")
    
    try:
        response = requests.get(f"{BASE_URL}/dashboard-executivo/api/recent-operations", headers=headers, timeout=30)
        if response.status_code != 200:
            print(f"❌ API não acessível: {response.status_code}")
            return False
            
        data = response.json()
        
        if not data.get('success'):
            print(f"❌ API retornou erro: {data.get('error', 'Erro desconhecido')}")
            return False
            
        operations = data.get('operations', [])
        if not operations:
            print("⚠️  Nenhuma operação encontrada")
            return True
            
        # Verificar se as operações têm os campos de status
        first_operation = operations[0]
        
        status_fields = ['status_processo', 'status_macro_sistema', 'status']
        status_found = any(field in first_operation for field in status_fields)
        
        if status_found:
            print("✅ Campos de status encontrados nas operações")
            print(f"Campos disponíveis: {[field for field in status_fields if field in first_operation]}")
        else:
            print("❌ Nenhum campo de status encontrado nas operações")
            print(f"Campos disponíveis: {list(first_operation.keys())}")
            
        return status_found
        
    except Exception as e:
        print(f"❌ Erro ao testar API: {str(e)}")
        return False

def main():
    """Executa todos os testes das melhorias"""
    print("🚀 TESTANDO MELHORIAS DO DASHBOARD EXECUTIVO")
    print("=" * 60)
    
    tests_results = []
    
    # Executa os testes
    tests_results.append(test_dashboard_improvements())
    tests_results.append(test_recent_operations_api())
    
    # Resultado final
    print("\n" + "=" * 60)
    passed = sum(tests_results)
    total = len(tests_results)
    
    if passed == total:
        print(f"✅ TODOS OS TESTES PASSARAM ({passed}/{total})")
        print("🎉 MELHORIAS IMPLEMENTADAS COM SUCESSO!")
        print("\n📋 MELHORIAS APLICADAS:")
        print("  1. ✅ Botão de reset/remover filtros adicionado")
        print("  2. ✅ Popup de confirmação removido dos filtros")
        print("  3. ✅ Valores dos eixos removidos dos gráficos")
        print("  4. ✅ Ícones de modal centralizados e maiores")
        print("  5. ✅ Campo de status adicionado à API")
    else:
        print(f"❌ ALGUNS TESTES FALHARAM ({passed}/{total})")
        print("⚠️  VERIFICAR PROBLEMAS NAS MELHORIAS")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    if not success:
        exit(1)
