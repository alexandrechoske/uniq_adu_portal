#!/usr/bin/env python3
"""
Diagnóstico completo do sistema de logging
Identifica problemas na conexão com Supabase e integrações
"""
import os
import sys
import requests
from datetime import datetime

# Configuração
API_BYPASS_KEY = os.getenv('API_BYPASS_KEY', 'bypass-key-12345')
BASE_URL = 'http://localhost:5000'
headers = {'X-API-Key': API_BYPASS_KEY, 'Content-Type': 'application/json'}

def check_supabase_connection():
    """Verifica conexão com Supabase"""
    print("=== 1. DIAGNÓSTICO SUPABASE ===")
    
    try:
        # Importar extensões
        sys.path.append('.')
        from extensions import supabase_admin, supabase
        
        print("✅ Módulo extensions importado com sucesso")
        
        # Verificar cliente admin
        if supabase_admin is None:
            print("❌ supabase_admin é None - PROBLEMA CRÍTICO!")
            return False
        else:
            print("✅ supabase_admin está inicializado")
        
        # Verificar cliente regular
        if supabase is None:
            print("❌ supabase é None")
        else:
            print("✅ supabase está inicializado")
        
        # Testar conexão com tabela access_logs
        print("\n--- Testando acesso à tabela access_logs ---")
        try:
            result = supabase_admin.table('access_logs').select('id').limit(1).execute()
            print(f"✅ Tabela access_logs acessível: {len(result.data)} registros encontrados")
            return True
        except Exception as e:
            print(f"❌ Erro ao acessar tabela access_logs: {e}")
            return False
            
    except ImportError as e:
        print(f"❌ Erro ao importar extensions: {e}")
        return False
    except Exception as e:
        print(f"❌ Erro geral no Supabase: {e}")
        return False

def check_access_logger():
    """Verifica o sistema de logging"""
    print("\n=== 2. DIAGNÓSTICO ACCESS LOGGER ===")
    
    try:
        from services.access_logger import access_logger, SUPABASE_AVAILABLE
        
        print(f"✅ AccessLogger importado")
        print(f"📊 SUPABASE_AVAILABLE: {SUPABASE_AVAILABLE}")
        print(f"📊 Logger enabled: {access_logger.enabled}")
        print(f"📊 Console only: {access_logger.console_only}")
        
        # Teste manual de log
        print("\n--- Teste manual de log ---")
        result = access_logger.log_access(
            'test_manual',
            page_name='Teste Diagnóstico',
            module_name='diagnostico',
            success=True
        )
        
        if result:
            print("✅ Log manual criado com sucesso")
        else:
            print("❌ Falha na criação do log manual")
            
        return True
        
    except Exception as e:
        print(f"❌ Erro no AccessLogger: {e}")
        return False

def check_auth_integration():
    """Verifica integração com auth"""
    print("\n=== 3. DIAGNÓSTICO AUTH INTEGRATION ===")
    
    # Verificar arquivo auth.py
    auth_file = 'routes/auth.py'
    if not os.path.exists(auth_file):
        print(f"❌ Arquivo {auth_file} não encontrado")
        return False
    
    with open(auth_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verificar imports
    imports_found = []
    if 'from services.auth_logging import' in content:
        imports_found.append("✅ Import auth_logging encontrado")
    else:
        imports_found.append("❌ Import auth_logging NÃO encontrado")
    
    if 'safe_log_login_success' in content:
        imports_found.append("✅ Função safe_log_login_success encontrada")
    else:
        imports_found.append("❌ Função safe_log_login_success NÃO encontrada")
    
    if 'safe_log_logout' in content:
        imports_found.append("✅ Função safe_log_logout encontrada")
    else:
        imports_found.append("❌ Função safe_log_logout NÃO encontrada")
    
    for item in imports_found:
        print(item)
    
    # Verificar se as chamadas estão nos locais corretos
    login_calls = content.count('safe_log_login_success')
    logout_calls = content.count('safe_log_logout')
    
    print(f"📊 Chamadas para login logging: {login_calls}")
    print(f"📊 Chamadas para logout logging: {logout_calls}")
    
    if login_calls == 0:
        print("⚠️ NENHUMA chamada de log de login encontrada!")
        return False
    
    return True

def check_middleware_integration():
    """Verifica integração do middleware"""
    print("\n=== 4. DIAGNÓSTICO MIDDLEWARE ===")
    
    # Verificar app.py
    app_file = 'app.py'
    if not os.path.exists(app_file):
        print(f"❌ Arquivo {app_file} não encontrado")
        return False
    
    with open(app_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    middleware_checks = []
    
    if 'from services.logging_middleware import' in content:
        middleware_checks.append("✅ Import logging_middleware encontrado")
    else:
        middleware_checks.append("❌ Import logging_middleware NÃO encontrado")
    
    if 'logging_middleware.init_app' in content:
        middleware_checks.append("✅ Inicialização do middleware encontrada")
    else:
        middleware_checks.append("❌ Inicialização do middleware NÃO encontrada")
    
    for check in middleware_checks:
        print(check)
    
    return 'logging_middleware' in content

def test_database_write():
    """Testa escrita direta no banco"""
    print("\n=== 5. TESTE DE ESCRITA DIRETA ===")
    
    try:
        from extensions import supabase_admin
        from datetime import datetime, timezone
        
        if supabase_admin is None:
            print("❌ supabase_admin é None - não é possível testar")
            return False
        
        # Criar log de teste
        test_log = {
            'action_type': 'test_direct',
            'page_name': 'Teste Direto',
            'module_name': 'diagnostico',
            'user_email': 'test@diagnostico.com',
            'user_name': 'Usuário Teste',
            'user_role': 'admin',
            'ip_address': '127.0.0.1',
            'browser': 'Test Browser',
            'device_type': 'desktop',
            'platform': 'Test OS',
            'success': True,
            'http_status': 200,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'session_id': 'test_session_123'
        }
        
        result = supabase_admin.table('access_logs').insert(test_log).execute()
        
        if result.data and len(result.data) > 0:
            print("✅ Teste de escrita direta bem-sucedido")
            print(f"📊 Log criado com ID: {result.data[0].get('id')}")
            return True
        else:
            print("❌ Teste de escrita retornou dados vazios")
            return False
            
    except Exception as e:
        print(f"❌ Erro no teste de escrita: {e}")
        return False

def check_environment_variables():
    """Verifica variáveis de ambiente"""
    print("\n=== 6. DIAGNÓSTICO VARIÁVEIS DE AMBIENTE ===")
    
    env_vars = {
        'SUPABASE_URL': os.getenv('SUPABASE_URL'),
        'SUPABASE_KEY': os.getenv('SUPABASE_KEY'),
        'SUPABASE_SERVICE_KEY': os.getenv('SUPABASE_SERVICE_KEY'),
        'ACCESS_LOGGING_ENABLED': os.getenv('ACCESS_LOGGING_ENABLED', 'true')
    }
    
    for var, value in env_vars.items():
        if value:
            if 'KEY' in var:
                print(f"✅ {var}: {value[:10]}... (mascarado)")
            else:
                print(f"✅ {var}: {value}")
        else:
            print(f"❌ {var}: NÃO DEFINIDA")
    
    # Verificar arquivo .env
    if os.path.exists('.env'):
        print("✅ Arquivo .env existe")
    else:
        print("❌ Arquivo .env não encontrado")
    
    return all(env_vars[key] for key in ['SUPABASE_URL', 'SUPABASE_KEY', 'SUPABASE_SERVICE_KEY'])

def check_current_logs():
    """Verifica logs atuais na API"""
    print("\n=== 7. CONSULTA DE LOGS ATUAIS ===")
    
    try:
        response = requests.get(f'{BASE_URL}/usuarios/analytics/api/stats', headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API de analytics acessível")
            print(f"📊 Total de acessos: {data.get('total_access', 0)}")
            print(f"📊 Usuários únicos: {data.get('unique_users', 0)}")
            print(f"📊 Logins hoje: {data.get('logins_today', 0)}")
            print(f"📊 Total de logins: {data.get('total_logins', 0)}")
            
            if data.get('total_access', 0) == 0:
                print("⚠️ ZERO logs encontrados na tabela!")
                return False
            else:
                print("✅ Logs encontrados na tabela")
                return True
        else:
            print(f"❌ Erro na API: {response.status_code}")
            if response.text:
                print(f"Resposta: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ Erro na consulta: {e}")
        return False

def show_solution_steps():
    """Mostra passos para resolver os problemas"""
    print("\n=== 8. PASSOS PARA RESOLVER ===")
    
    print("🔧 SOLUÇÕES POSSÍVEIS:")
    print()
    print("1. PROBLEMA SUPABASE_ADMIN:")
    print("   - Verificar se extensions.py está correto")
    print("   - Verificar SUPABASE_SERVICE_KEY no .env")
    print("   - Reiniciar aplicação Flask")
    print()
    print("2. PROBLEMA DE INTEGRAÇÃO AUTH:")
    print("   - Adicionar imports no routes/auth.py")
    print("   - Adicionar chamadas de log nas funções login/logout")
    print()
    print("3. PROBLEMA DE MIDDLEWARE:")
    print("   - Adicionar import no app.py")
    print("   - Inicializar middleware com app")
    print()
    print("4. PROBLEMA DE TABELA:")
    print("   - Verificar se tabela access_logs existe no Supabase")
    print("   - Verificar políticas RLS")
    print("   - Testar com cliente admin")

def main():
    """Executa diagnóstico completo"""
    print("🔍 DIAGNÓSTICO COMPLETO DO SISTEMA DE LOGGING")
    print("=" * 60)
    print(f"📅 Executado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print()
    
    results = []
    
    # Executar todos os diagnósticos
    results.append(("Supabase Connection", check_supabase_connection()))
    results.append(("Access Logger", check_access_logger()))
    results.append(("Auth Integration", check_auth_integration()))
    results.append(("Middleware Integration", check_middleware_integration()))
    results.append(("Database Write", test_database_write()))
    results.append(("Environment Variables", check_environment_variables()))
    results.append(("Current Logs", check_current_logs()))
    
    # Mostrar resumo
    print("\n" + "=" * 60)
    print("📋 RESUMO DO DIAGNÓSTICO:")
    print()
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status} - {test_name}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\n📊 RESULTADO: {passed}/{total} testes passaram")
    
    if passed < total:
        print("\n⚠️ PROBLEMAS ENCONTRADOS - veja soluções abaixo:")
        show_solution_steps()
    else:
        print("\n🎉 TODOS OS TESTES PASSARAM!")
        print("O sistema de logging deveria estar funcionando.")

if __name__ == '__main__':
    main()
