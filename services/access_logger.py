"""
Serviço de logging de acessos para o portal UniSystem - Versão de produção
IMPORTANTE: Erros de logging NÃO devem impactar o funcionamento da aplicação
"""
import os
import time
import uuid
from datetime import datetime, timezone, timedelta
from flask import request, session, g
from functools import wraps
import traceback

try:
    from user_agents import parse
except ImportError:
    # Fallback se user_agents não estiver disponível
    def parse(user_agent_string):
        class FakeAgent:
            def __init__(self):
                self.browser = type('obj', (object,), {'family': 'Unknown', 'version_string': ''})()
                self.os = type('obj', (object,), {'family': 'Unknown'})()
                self.is_mobile = False
                self.is_tablet = False
        return FakeAgent()

try:
    from extensions import supabase_admin
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    print("[ACCESS_LOG_WARNING] Supabase não disponível - logs serão apenas no console")

# Fallback: criar cliente direto se extensions não funcionar
def _create_direct_supabase():
    """Cria cliente Supabase diretamente em caso de falha de import"""
    try:
        from supabase import create_client
        SUPABASE_URL = os.getenv("SUPABASE_URL")
        SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
        if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
            print("[ACCESS_LOG_WARNING] SUPABASE_URL ou SUPABASE_SERVICE_KEY não definidos no ambiente")
            return None
        return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    except Exception as e:
        print(f"[ACCESS_LOG_WARNING] Falha ao criar cliente direto: {e}")
        return None

class AccessLogger:
    """
    Serviço para registrar logs de acesso dos usuários
    
    PRINCÍPIOS DE SEGURANÇA:
    1. Nunca falhar - sempre retornar True
    2. Não bloquear a aplicação principal
    3. Fallback para console em caso de falha
    4. Timeout rápido para operações de rede
    """
    
    def __init__(self):
        self.timezone_br = timezone(timedelta(hours=-3))  # UTC-3 (Brasília)
        self.enabled = os.getenv('ACCESS_LOGGING_ENABLED', 'true').lower() == 'true'
        self.console_only = not SUPABASE_AVAILABLE
        self.max_retries = 1  # Apenas 1 tentativa para não impactar performance
        self.timeout = 2  # Timeout de 2 segundos
        
        # Skip logging in development mode
        self.flask_env = os.getenv('FLASK_ENV', 'production')
        if self.flask_env == 'development':
            self.enabled = False
            print("[ACCESS_LOG] Logging desabilitado no ambiente de desenvolvimento")
        
        # Production URL configuration
        self.production_url = os.getenv('PRODUCTION_URL', 'https://portalunique.com.br')
        
        if not self.enabled:
            print("[ACCESS_LOG] Logging desabilitado via configuração")
        elif self.console_only:
            print("[ACCESS_LOG] Modo console-only ativado")
    
    def _safe_execute(self, func, *args, **kwargs):
        """
        Executa uma função de forma segura, sem permitir que falhe
        """
        if not self.enabled:
            return True
            
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Log do erro apenas no console, nunca re-raise
            print(f"[ACCESS_LOG_ERROR] {func.__name__}: {str(e)}")
            return True  # Sempre retorna sucesso para não afetar a aplicação
    
    def _get_client_info_safe(self, request_obj=None):
        """Extrai informações do cliente de forma segura"""
        try:
            if not request_obj:
                if not request:
                    return self._get_default_client_info()
                request_obj = request
                
            # IP Address
            ip_address = '127.0.0.1'  # Default
            try:
                ip_address = request_obj.environ.get('HTTP_X_FORWARDED_FOR')
                if ip_address:
                    ip_address = ip_address.split(',')[0].strip()
                else:
                    ip_address = request_obj.environ.get('REMOTE_ADDR', '127.0.0.1')
            except:
                pass
            
            # User Agent
            user_agent_string = ''
            browser = 'Unknown'
            device_type = 'desktop'
            platform = 'Unknown'
            
            try:
                user_agent_string = request_obj.headers.get('User-Agent', '')
                if user_agent_string:
                    user_agent = parse(user_agent_string)
                    browser = f"{user_agent.browser.family}"
                    if user_agent.browser.version_string:
                        browser += f" {user_agent.browser.version_string}"
                    device_type = 'mobile' if user_agent.is_mobile else 'tablet' if user_agent.is_tablet else 'desktop'
                    platform = user_agent.os.family
            except:
                pass
            
            return {
                'ip_address': str(ip_address)[:45],  # Limitar tamanho para INET
                'user_agent': str(user_agent_string)[:500],
                'browser': str(browser)[:100],
                'device_type': str(device_type)[:50],
                'platform': str(platform)[:50]
            }
            
        except Exception:
            return self._get_default_client_info()
    
    def _get_default_client_info(self):
        """Informações padrão em caso de erro"""
        return {
            'ip_address': '127.0.0.1',
            'user_agent': 'Unknown',
            'browser': 'Unknown',
            'device_type': 'desktop',
            'platform': 'Unknown'
        }
    
    def _get_user_info_safe(self):
        """Extrai informações do usuário da sessão de forma segura"""
        try:
            # Check if we have a valid user session
            if not session:
                return {
                    'user_id': None,
                    'user_email': None,
                    'user_name': None,
                    'user_role': None,
                    'session_id': str(uuid.uuid4())[:255]
                }
            
            user = session.get('user', {})
            
            # If we have a user in session, extract info
            if user and isinstance(user, dict):
                return {
                    'user_id': user.get('id') if user.get('id') else None,
                    'user_email': str(user.get('email', ''))[:255] if user.get('email') else None,
                    'user_name': str(user.get('name', ''))[:255] if user.get('name') else None,
                    'user_role': str(user.get('role', ''))[:50] if user.get('role') else None,
                    'session_id': str(session.get('session_id', str(uuid.uuid4())))[:255] if session else str(uuid.uuid4())[:255]
                }
            else:
                # No valid user in session
                return {
                    'user_id': None,
                    'user_email': None,
                    'user_name': None,
                    'user_role': None,
                    'session_id': str(session.get('session_id', str(uuid.uuid4())))[:255] if session else str(uuid.uuid4())[:255]
                }
        except Exception as e:
            print(f"[ACCESS_LOG] Error getting user info: {str(e)}")
            return {
                'user_id': None,
                'user_email': None,
                'user_name': None,
                'user_role': None,
                'session_id': str(uuid.uuid4())[:255]
            }
    
    def _insert_log_safe(self, log_data):
        """Insere log de forma segura com fallback"""
        try:
            # Verificar se supabase_admin está disponível
            client = None
            
            if self.console_only or not SUPABASE_AVAILABLE:
                client = None
            else:
                # Tentar usar supabase_admin das extensions
                try:
                    from extensions import supabase_admin
                    client = supabase_admin
                except ImportError:
                    client = None
                
                # Se ainda for None, tentar criar cliente direto
                if client is None:
                    client = _create_direct_supabase()
            
            if client is None:
                # Fallback para console
                action = log_data.get('action_type', 'unknown')
                user = log_data.get('user_email', 'Anonymous')
                page = log_data.get('page_name', 'Unknown')
                print(f"[ACCESS_LOG] {action} - {user} - {page}")
                return True
            
            # Tentar inserir no Supabase com timeout
            result = client.table('access_logs').insert(log_data).execute()
            
            if result.data and len(result.data) > 0:
                log_id = result.data[0].get('id')
                print(f"[ACCESS_LOG] ✅ {log_data.get('action_type', 'unknown')} - {log_data.get('user_email', 'Anonymous')} - {log_data.get('page_name', 'Unknown')} - ID: {log_id}")
                return log_id
            return True
            
        except Exception as e:
            # Fallback para console em caso de erro
            action = log_data.get('action_type', 'unknown')
            user = log_data.get('user_email', 'Anonymous')
            page = log_data.get('page_name', 'Unknown')
            print(f"[ACCESS_LOG_FALLBACK] {action} - {user} - {page} (Error: {str(e)[:100]})")
            return True
    
    def log_access(self, action_type, **kwargs):
        """
        Registra um log de acesso de forma completamente segura
        
        Args:
            action_type: Tipo da ação ('login', 'page_access', 'logout', 'api_call')
            **kwargs: Parâmetros adicionais específicos da ação
            
        Returns:
            bool: Sempre True (nunca falha)
        """
        return self._safe_execute(self._log_access_internal, action_type, **kwargs)
    
    def _log_access_internal(self, action_type, **kwargs):
        """Implementação interna do logging"""
        start_time = time.time()
        
        # Informações básicas (sempre seguras)
        client_info = self._get_client_info_safe()
        user_info = self._get_user_info_safe()
        
        # Skip logging if we're in development mode
        if self.flask_env == 'development':
            return True
        
        # Skip logging if user info is completely empty and it's not a login/logout action
        # This prevents logging anonymous access to public pages
        if (not user_info['user_id'] and not user_info['user_email'] and 
            action_type not in ['login', 'logout'] and
            not session):  # If no session at all, it's likely a public access
            return True
        
        # Timestamp brasileiro
        try:
            now_utc = datetime.now(timezone.utc)
            now_br = now_utc.astimezone(self.timezone_br)
        except:
            now_utc = datetime.utcnow()
            now_br = now_utc
        
        # Dados do log (com validação de tamanho)
        log_data = {
            'action_type': str(action_type)[:50],
            'success': kwargs.get('success', True),
            'http_status': kwargs.get('http_status', 200),
            'created_at': now_utc.isoformat(),
            'created_at_br': now_br.replace(tzinfo=None).isoformat()
        }
        
        # Campos opcionais com validação
        if kwargs.get('page_url'):
            log_data['page_url'] = str(kwargs['page_url'])[:500]
        elif request and hasattr(request, 'url'):
            try:
                # Use the correct production URL
                if self.flask_env == 'production':
                    # Extract path from request.url and prepend production URL
                    request_path = request.path
                    if request.query_string:
                        request_path += '?' + request.query_string.decode('utf-8')
                    log_data['page_url'] = f"{self.production_url}{request_path}"[:500]
                else:
                    log_data['page_url'] = str(request.url)[:500]
            except:
                pass
        
        if kwargs.get('page_name'):
            log_data['page_name'] = str(kwargs['page_name'])[:255]
        
        if kwargs.get('module_name'):
            log_data['module_name'] = str(kwargs['module_name'])[:100]
        
        if kwargs.get('session_duration'):
            log_data['session_duration'] = int(kwargs['session_duration'])
        
        if kwargs.get('error_message'):
            log_data['error_message'] = str(kwargs['error_message'])[:1000]
        
        # Adicionar informações do usuário e cliente
        log_data.update(user_info)
        log_data.update(client_info)
        
        # Remove campos None
        log_data = {k: v for k, v in log_data.items() if v is not None}
        
        # Inserir no banco
        log_id = self._insert_log_safe(log_data)
        
        # Atualizar tempo de resposta se temos ID
        if log_id and log_id != True and not self.console_only:
            try:
                response_time = int((time.time() - start_time) * 1000)
                
                # Tentar usar o mesmo cliente que foi usado para inserir
                client = None
                try:
                    from extensions import supabase_admin
                    client = supabase_admin
                except ImportError:
                    pass
                
                if client is None:
                    client = _create_direct_supabase()
                
                if client:
                    client.table('access_logs').update({
                        'response_time': response_time
                    }).eq('id', log_id).execute()
            except:
                pass  # Ignora erro de update de response_time
        
        return True
    
    def log_login(self, user_data=None, success=True, error_message=None):
        """Registra um login"""
        return self.log_access(
            'login',
            page_name='Login',
            module_name='auth',
            success=success,
            error_message=error_message
        )
    
    def log_logout(self, session_duration=None):
        """Registra um logout"""
        return self.log_access(
            'logout',
            page_name='Logout',
            module_name='auth',
            session_duration=session_duration
        )
    
    def log_page_access(self, page_name, module_name=None):
        """Registra acesso a uma página"""
        return self.log_access(
            'page_access',
            page_name=page_name,
            module_name=module_name
        )
    
    def log_api_call(self, endpoint, success=True, http_status=200, error_message=None):
        """Registra uma chamada de API"""
        return self.log_access(
            'api_call',
            page_name=endpoint,
            module_name='api',
            success=success,
            http_status=http_status,
            error_message=error_message
        )

# Instância global
access_logger = AccessLogger()

# Decorator para logging automático de rotas
def log_route_access(page_name=None, module_name=None):
    """
    Decorator para adicionar logging automático a rotas Flask
    
    Usage:
        @app.route('/dashboard/')
        @log_route_access('Dashboard', 'dashboard')
        def dashboard():
            return render_template('dashboard.html')
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Executar função original primeiro
            try:
                result = func(*args, **kwargs)
                
                # Log apenas após sucesso
                final_page_name = page_name or func.__name__.replace('_', ' ').title()
                final_module_name = module_name or 'unknown'
                
                # Log em background para não afetar response
                access_logger.log_page_access(final_page_name, final_module_name)
                
                return result
                
            except Exception as e:
                # Log do erro, mas re-raise para não afetar funcionamento
                if page_name:
                    access_logger.log_page_access(
                        page_name, 
                        module_name or 'unknown'
                    )
                raise
                
        return wrapper
    return decorator