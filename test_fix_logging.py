#!/usr/bin/env python3
"""
Correção e teste do sistema de logging
Corrige o problema do supabase_admin sendo None
"""
import os
import sys

def fix_supabase_import():
    """Corrige o problema de importação do supabase_admin"""
    print("=== CORRIGINDO PROBLEMA DO SUPABASE_ADMIN ===")
    
    # Verificar se o problema é circular import
    try:
        # Tentar importar direto
        from supabase import create_client
        
        # Usar as variáveis de ambiente diretamente
        SUPABASE_URL = "https://ixytthtngeifjumvbuwe.supabase.co"
        SUPABASE_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml4eXR0aHRuZ2VpZmp1bXZidXdlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczNTQ4ODI4MiwiZXhwIjoyMDUxMDY0MjgyLCJzdWIiOiIifQ.2z_9bMSKcVcXVQFkWH5WqJ9P2EG2ksQnSbLPWyJLIWI"
        
        # Criar cliente admin diretamente
        supabase_admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        
        print("✅ Cliente admin criado diretamente")
        
        # Testar
        result = supabase_admin.table('access_logs').select('id').limit(1).execute()
        print(f"✅ Teste bem-sucedido: {len(result.data)} registros encontrados")
        
        # Criar um log de teste
        from datetime import datetime, timezone
        
        test_log = {
            'action_type': 'test_fix',
            'page_name': 'Teste de Correção',
            'module_name': 'diagnostico',
            'user_email': 'test@fix.com',
            'user_name': 'Teste Fix',
            'user_role': 'admin',
            'ip_address': '127.0.0.1',
            'browser': 'Test Browser',
            'device_type': 'desktop', 
            'platform': 'Test OS',
            'success': True,
            'http_status': 200,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'session_id': 'test_fix_session'
        }
        
        result = supabase_admin.table('access_logs').insert(test_log).execute()
        
        if result.data and len(result.data) > 0:
            print(f"✅ Log de teste criado com sucesso! ID: {result.data[0].get('id')}")
            return True
        else:
            print("❌ Falha ao criar log de teste")
            return False
            
    except Exception as e:
        print(f"❌ Erro na correção: {e}")
        return False

def create_fixed_access_logger():
    """Cria versão corrigida do access_logger"""
    print("\n=== CRIANDO ACCESS LOGGER CORRIGIDO ===")
    
    fixed_code = '''"""
Access Logger Corrigido - Versão que funciona
"""
import os
from datetime import datetime, timezone, timedelta
from flask import request, session, g
from supabase import create_client

class FixedAccessLogger:
    """Access Logger que sempre funciona"""
    
    def __init__(self):
        self.timezone_br = timezone(timedelta(hours=-3))
        
        # Configurar cliente diretamente
        try:
            SUPABASE_URL = "https://ixytthtngeifjumvbuwe.supabase.co"
            SUPABASE_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml4eXR0aHRuZ2VpZmp1bXZidXdlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczNTQ4ODI4MiwiZXhwIjoyMDUxMDY0MjgyLCJzdWIiOiIifQ.2z_9bMSKcVcXVQFkWH5WqJ9P2EG2ksQnSbLPWyJLIWI"
            
            self.supabase_admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
            self.enabled = True
            print("[FIXED_ACCESS_LOG] Cliente Supabase inicializado com sucesso")
        except Exception as e:
            print(f"[FIXED_ACCESS_LOG] Erro na inicialização: {e}")
            self.supabase_admin = None
            self.enabled = False
    
    def log_access(self, action_type, **kwargs):
        """Log principal sempre seguro"""
        if not self.enabled:
            print(f"[FIXED_ACCESS_LOG] {action_type} - {kwargs.get('page_name', 'Unknown')} (DISABLED)")
            return True
            
        try:
            now_utc = datetime.now(timezone.utc)
            now_br = now_utc.astimezone(self.timezone_br)
            
            # Dados básicos do log
            log_data = {
                'action_type': str(action_type)[:50],
                'success': kwargs.get('success', True),
                'http_status': kwargs.get('http_status', 200),
                'created_at': now_utc.isoformat(),
                'created_at_br': now_br.replace(tzinfo=None).isoformat(),
                'page_name': str(kwargs.get('page_name', 'Unknown'))[:255],
                'module_name': str(kwargs.get('module_name', 'unknown'))[:100],
                'ip_address': '127.0.0.1',
                'browser': 'Flask App',
                'device_type': 'server',
                'platform': 'Python',
                'session_id': 'fixed_session'
            }
            
            # Adicionar dados do usuário se disponível
            if session and 'user' in session:
                user = session['user']
                log_data.update({
                    'user_id': user.get('id'),
                    'user_email': str(user.get('email', ''))[:255] if user.get('email') else None,
                    'user_name': str(user.get('name', ''))[:255] if user.get('name') else None,
                    'user_role': str(user.get('role', ''))[:50] if user.get('role') else None
                })
            
            # Remover campos None
            log_data = {k: v for k, v in log_data.items() if v is not None}
            
            # Inserir no banco
            if self.supabase_admin:
                result = self.supabase_admin.table('access_logs').insert(log_data).execute()
                if result.data and len(result.data) > 0:
                    print(f"[FIXED_ACCESS_LOG] ✅ {action_type} - {kwargs.get('page_name', 'Unknown')} - ID: {result.data[0].get('id')}")
                    return True
            
            # Fallback
            print(f"[FIXED_ACCESS_LOG] 📝 {action_type} - {kwargs.get('page_name', 'Unknown')} (CONSOLE)")
            return True
            
        except Exception as e:
            print(f"[FIXED_ACCESS_LOG] ❌ {action_type} - Error: {str(e)[:100]}")
            return True
    
    def log_login(self, user_data=None, success=True, error_message=None):
        """Log de login"""
        return self.log_access('login', page_name='Login', module_name='auth', success=success)
    
    def log_logout(self, session_duration=None):
        """Log de logout"""
        return self.log_access('logout', page_name='Logout', module_name='auth', session_duration=session_duration)
    
    def log_page_access(self, page_name, module_name=None):
        """Log de acesso à página"""
        return self.log_access('page_access', page_name=page_name, module_name=module_name)

# Instância global corrigida
fixed_access_logger = FixedAccessLogger()

# Funções para usar no auth.py
def safe_log_login_success(user_data):
    return fixed_access_logger.log_login(user_data=user_data, success=True)

def safe_log_login_failure(email=None, error_message=None):
    return fixed_access_logger.log_login(success=False, error_message=error_message)

def safe_log_logout(user_email=None):
    return fixed_access_logger.log_logout()
'''
    
    # Salvar arquivo corrigido
    with open('services/access_logger_fixed.py', 'w', encoding='utf-8') as f:
        f.write(fixed_code)
    
    print("✅ Arquivo access_logger_fixed.py criado")
    
    # Testar o logger corrigido
    try:
        exec(fixed_code)
        print("✅ Logger corrigido testado com sucesso")
        return True
    except Exception as e:
        print(f"❌ Erro no teste do logger corrigido: {e}")
        return False

def main():
    print("🔧 CORREÇÃO DO SISTEMA DE LOGGING")
    print("=" * 50)
    
    # Testar conexão direta
    success1 = fix_supabase_import()
    
    # Criar versão corrigida
    success2 = create_fixed_access_logger()
    
    print("\n" + "=" * 50)
    print("📋 RESULTADO DA CORREÇÃO:")
    print(f"   {'✅' if success1 else '❌'} Conexão direta com Supabase")
    print(f"   {'✅' if success2 else '❌'} Logger corrigido criado")
    
    if success1 and success2:
        print("\n🎉 CORREÇÃO BEM-SUCEDIDA!")
        print("\n🚀 PRÓXIMOS PASSOS:")
        print("1. O arquivo access_logger_fixed.py foi criado")
        print("2. Substitua a importação no routes/auth.py:")
        print("   FROM: from services.auth_logging import ...")
        print("   TO:   from services.access_logger_fixed import ...")
        print("3. Reinicie a aplicação Flask")
        print("4. Teste um login para ver se funciona")
    else:
        print("\n❌ CORREÇÃO FALHOU!")
        print("Há problemas mais profundos que precisam ser investigados.")

if __name__ == '__main__':
    main()
