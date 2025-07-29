#!/usr/bin/env python3
"""
Teste do sistema de logging via API da aplicação
Testa se o logging está funcionando dentro do contexto Flask
"""
import os
import requests
import json
import time
from datetime import datetime

# Configuração
API_BYPASS_KEY = os.getenv('API_BYPASS_KEY', 'bypass-key-12345')
BASE_URL = 'http://localhost:5000'
headers = {'X-API-Key': API_BYPASS_KEY, 'Content-Type': 'application/json'}

def test_manual_log_creation():
    """Testa criação manual de log via endpoint"""
    print("=== TESTE DE CRIAÇÃO MANUAL DE LOG ===")
    
    # Criar endpoint de teste no analytics para testar logging
    test_data = {
        'action': 'create_test_log',
        'page_name': 'Teste Via API',
        'module_name': 'test_diagnostico'
    }
    
    try:
        # Primeiro vamos verificar se conseguimos acessar a API
        response = requests.get(f'{BASE_URL}/usuarios/analytics/api/stats', headers=headers)
        print(f"Status da API: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"✅ API funcionando - Total de logs: {data.get('total_access', 0)}")
            except json.JSONDecodeError:
                print("⚠️ API retornou HTML (provavelmente redirecionamento de login)")
                
        # Tentar fazer um log através de uma requisição normal
        print("\n--- Fazendo requisições para gerar logs ---")
        
        # Acessar algumas páginas que deveriam gerar logs
        test_urls = [
            '/menu/',
            '/dashboard-executivo/',
            '/usuarios/',
        ]
        
        for url in test_urls:
            try:
                response = requests.get(f'{BASE_URL}{url}', headers=headers)
                print(f"✅ {url} - Status: {response.status_code}")
                time.sleep(0.5)  # Pequena pausa entre requisições
            except Exception as e:
                print(f"❌ {url} - Erro: {e}")
        
        # Verificar novamente os logs
        print("\n--- Verificando logs após requisições ---")
        response = requests.get(f'{BASE_URL}/usuarios/analytics/api/stats', headers=headers)
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"📊 Logs após teste: {data.get('total_access', 0)}")
                print(f"📊 Usuários únicos: {data.get('unique_users', 0)}")
                print(f"📊 Logins hoje: {data.get('logins_today', 0)}")
                return True
            except json.JSONDecodeError:
                print("❌ API ainda retornando HTML")
                return False
        else:
            print(f"❌ Erro na API: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        return False

def test_login_logout_logging():
    """Testa se login/logout geram logs"""
    print("\n=== TESTE DE LOGIN/LOGOUT LOGGING ===")
    
    # Fazer logout para garantir estado limpo
    try:
        response = requests.get(f'{BASE_URL}/auth/logout', headers=headers)
        print(f"Logout: {response.status_code}")
        time.sleep(1)
    except:
        pass
    
    # Tentar fazer login
    login_data = {
        'email': 'system@uniqueaduaneira.com.br',
        'password': 'admin123'  # Senha padrão de admin
    }
    
    try:
        print("Tentando fazer login...")
        response = requests.post(f'{BASE_URL}/auth/login', 
                               data=login_data, 
                               headers={'X-API-Key': API_BYPASS_KEY},
                               allow_redirects=False)
        
        print(f"Login status: {response.status_code}")
        
        if response.status_code in [200, 302]:
            print("✅ Login aparentemente bem-sucedido")
            
            # Aguardar um pouco para o log ser processado
            time.sleep(2)
            
            # Verificar se log foi criado
            response = requests.get(f'{BASE_URL}/usuarios/analytics/api/stats', headers=headers)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    logins_today = data.get('logins_today', 0)
                    total_logins = data.get('total_logins', 0)
                    
                    print(f"📊 Logins hoje após teste: {logins_today}")
                    print(f"📊 Total de logins: {total_logins}")
                    
                    if total_logins > 0:
                        print("✅ Logs de login estão sendo criados!")
                        return True
                    else:
                        print("❌ Nenhum log de login encontrado")
                        return False
                        
                except json.JSONDecodeError:
                    print("❌ API retornando HTML após login")
                    return False
            else:
                print(f"❌ Erro ao verificar logs: {response.status_code}")
                return False
        else:
            print(f"❌ Falha no login: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Erro no teste de login: {e}")
        return False

def check_console_logs():
    """Verifica se logs estão aparecendo no console da aplicação"""
    print("\n=== VERIFICAÇÃO DE LOGS NO CONSOLE ===")
    print("👁️ Olhe o console da aplicação Flask e procure por:")
    print("   - [ACCESS_LOG] para logs bem-sucedidos")
    print("   - [ACCESS_LOG_FALLBACK] para logs com fallback")
    print("   - [ACCESS_LOG_ERROR] para erros")
    print("   - [AUTH_LOG] para logs de autenticação")
    print()
    print("🔍 Se você vê mensagens [ACCESS_LOG_FALLBACK], significa que:")
    print("   1. O sistema de logging está funcionando")
    print("   2. Mas há problema com a conexão Supabase")
    print("   3. Os logs estão sendo salvos apenas no console")

def main():
    """Executa teste completo via API"""
    print("🔍 TESTE DO SISTEMA DE LOGGING VIA API")
    print("=" * 50)
    print(f"📅 Executado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print()
    
    # Executar testes
    test1 = test_manual_log_creation()
    test2 = test_login_logout_logging()
    
    print("\n" + "=" * 50)
    print("📋 RESUMO DOS TESTES:")
    print(f"   {'✅' if test1 else '❌'} Criação manual de logs via API")
    print(f"   {'✅' if test2 else '❌'} Logging de login/logout")
    
    if test1 or test2:
        print("\n✅ PELO MENOS UM TESTE PASSOU!")
        print("O sistema de logging parece estar funcionando parcialmente.")
    else:
        print("\n❌ TODOS OS TESTES FALHARAM!")
        print("Há um problema sério no sistema de logging.")
    
    check_console_logs()
    
    print("\n🚀 PRÓXIMOS PASSOS:")
    print("1. Verifique os logs no console da aplicação Flask")
    print("2. Se vê [ACCESS_LOG_FALLBACK] -> problema é apenas no Supabase")
    print("3. Se não vê nenhum log -> problema nas integrações")
    print("4. Execute um login manual e observe o console")

if __name__ == '__main__':
    main()
