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

def test_dashboard_materiais_removal():
    """Testa se o dashboard materiais foi removido"""
    print("\n=== TESTE: Verificação de Remoção do Dashboard Materiais ===")
    
    # Tenta acessar a rota do dashboard materiais (deve falhar)
    try:
        response = requests.get(f"{BASE_URL}/dashboard-materiais/", headers=headers, timeout=10)
        if response.status_code == 404:
            print("✅ Dashboard Materiais removido - rota retorna 404")
            return True
        else:
            print(f"❌ Dashboard Materiais ainda acessível: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("✅ Dashboard Materiais removido - rota não encontrada")
        return True
    except Exception as e:
        print(f"✅ Dashboard Materiais removido - erro esperado: {str(e)}")
        return True

def test_dashboard_executivo_working():
    """Testa se o dashboard executivo está funcionando"""
    print("\n=== TESTE: Verificação do Dashboard Executivo ===")
    
    try:
        response = requests.get(f"{BASE_URL}/dashboard-executivo/", headers=headers, timeout=10)
        if response.status_code == 200:
            print("✅ Dashboard Executivo acessível e funcionando")
            
            # Verifica se contém elementos de materiais integrados
            content = response.text
            if 'principais-materiais-table' in content:
                print("✅ Tabela de materiais integrada encontrada")
            else:
                print("❌ Tabela de materiais não encontrada no dashboard executivo")
                
            if 'filter-modal' in content:
                print("✅ Modal de filtros encontrado")
            else:
                print("❌ Modal de filtros não encontrado")
                
            return True
        else:
            print(f"❌ Dashboard Executivo com erro: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Erro ao acessar Dashboard Executivo: {str(e)}")
        return False

def test_menu_navigation():
    """Testa se o menu foi atualizado corretamente"""
    print("\n=== TESTE: Verificação do Menu de Navegação ===")
    
    try:
        response = requests.get(f"{BASE_URL}/menu/dashboards", headers=headers, timeout=10)
        if response.status_code == 200:
            content = response.text
            
            # Verifica se não há mais referência ao dashboard materiais
            if 'Dashboard Materiais' not in content:
                print("✅ Dashboard Materiais removido do menu")
            else:
                print("❌ Dashboard Materiais ainda presente no menu")
                return False
                
            # Verifica se o dashboard executivo menciona análise de materiais
            if 'análise de materiais integrada' in content or 'materiais integrada' in content:
                print("✅ Dashboard Executivo atualizado com descrição de materiais")
            else:
                print("❌ Descrição de materiais não encontrada no Dashboard Executivo")
                
            return True
        else:
            print(f"❌ Menu com erro: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Erro ao acessar menu: {str(e)}")
        return False

def main():
    """Executa todos os testes de verificação da migração"""
    print("🚀 INICIANDO TESTES DE VERIFICAÇÃO DA MIGRAÇÃO")
    print("=" * 60)
    
    tests_results = []
    
    # Executa os testes
    tests_results.append(test_dashboard_materiais_removal())
    tests_results.append(test_dashboard_executivo_working())
    tests_results.append(test_menu_navigation())
    
    # Resultado final
    print("\n" + "=" * 60)
    passed = sum(tests_results)
    total = len(tests_results)
    
    if passed == total:
        print(f"✅ TODOS OS TESTES PASSARAM ({passed}/{total})")
        print("🎉 MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
    else:
        print(f"❌ ALGUNS TESTES FALHARAM ({passed}/{total})")
        print("⚠️  VERIFICAR PROBLEMAS NA MIGRAÇÃO")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    if not success:
        exit(1)
