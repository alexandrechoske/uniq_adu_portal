#!/usr/bin/env python3
"""
Teste da correção do access_logger
"""
import sys
import os

# Adicionar path para importar módulos
sys.path.append('.')

def test_fixed_logger():
    """Testa o logger corrigido"""
    print("=== TESTANDO ACCESS LOGGER CORRIGIDO ===")
    
    try:
        # Importar o logger corrigido
        from services.access_logger import access_logger
        
        print("✅ AccessLogger importado com sucesso")
        
        # Testar log de acesso
        result = access_logger.log_page_access(
            page_name="Teste Correção",
            module_name="test_fix"
        )
        
        if result:
            print("✅ Log de página criado com sucesso")
        else:
            print("❌ Falha ao criar log de página")
        
        # Testar log de login
        result = access_logger.log_login(
            user_data={'email': 'test@fix.com', 'name': 'Teste Fix'},
            success=True
        )
        
        if result:
            print("✅ Log de login criado com sucesso")
        else:
            print("❌ Falha ao criar log de login")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        return False

def main():
    print("🔧 TESTE DA CORREÇÃO DO ACCESS LOGGER")
    print("=" * 50)
    
    success = test_fixed_logger()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ CORREÇÃO BEM-SUCEDIDA!")
        print("\n🚀 Agora faça um login na aplicação e observe os logs.")
        print("Você deve ver mensagens [ACCESS_LOG] ✅ em vez de [ACCESS_LOG_FALLBACK]")
    else:
        print("❌ CORREÇÃO FALHOU!")
    
    print(f"\n📅 Teste executado em: {os.path.basename(__file__)}")

if __name__ == '__main__':
    main()
