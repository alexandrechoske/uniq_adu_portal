"""
Integração robusta do sistema de logging com autenticação
IMPORTANTE: Logging NUNCA deve falhar ou impedir login/logout
"""
from flask import session, request
from datetime import datetime
import time
from services.access_logger import access_logger

class AuthLoggingIntegration:
    """
    Classe para integrar logging com sistema de autenticação
    
    PRINCÍPIOS:
    1. Nunca impedir login/logout por falha de logging
    2. Sempre permitir acesso mesmo se logging falhar
    3. Logging é "nice to have", não "must have"
    """
    
    def __init__(self):
        self.enabled = True
    
    def log_login_attempt(self, email=None, success=True, error_message=None, user_data=None):
        """
        Registra tentativa de login de forma completamente segura
        
        Args:
            email: Email do usuário
            success: Se o login foi bem-sucedido
            error_message: Mensagem de erro (se houver)
            user_data: Dados completos do usuário (se login bem-sucedido)
        
        Returns:
            bool: Sempre True (nunca falha)
        """
        try:
            if not self.enabled:
                return True
            
            # Se login bem-sucedido, salvar timestamp na sessão
            if success and session:
                try:
                    session['login_time'] = time.time()
                    session['session_id'] = session.get('session_id', f"sess_{int(time.time())}")
                except:
                    pass  # Ignora erro de sessão
            
            # Determinar dados do usuário
            final_user_data = user_data or {}
            if not final_user_data.get('email') and email:
                final_user_data['email'] = email
            
            # Registrar log
            access_logger.log_login(
                user_data=final_user_data,
                success=success,
                error_message=error_message
            )
            
            # Log no console para debug
            status = "SUCCESS" if success else "FAILED"
            user_identifier = email or final_user_data.get('email', 'Unknown')
            print(f"[AUTH_LOG] Login {status}: {user_identifier}")
            
            return True
            
        except Exception as e:
            # Log apenas no console, nunca re-raise
            print(f"[AUTH_LOG_ERROR] Erro no log de login: {str(e)}")
            return True
    
    def log_logout_attempt(self, user_email=None):
        """
        Registra tentativa de logout de forma completamente segura
        
        Args:
            user_email: Email do usuário (opcional)
        
        Returns:
            bool: Sempre True (nunca falha)
        """
        try:
            if not self.enabled:
                return True
            
            # Calcular duração da sessão se disponível
            session_duration = None
            if session and 'login_time' in session:
                try:
                    session_duration = int(time.time() - session['login_time'])
                except:
                    pass
            
            # Registrar log
            access_logger.log_logout(session_duration=session_duration)
            
            # Log no console para debug
            user_identifier = user_email or session.get('user', {}).get('email', 'Unknown') if session else 'Unknown'
            duration_text = f" (Duration: {session_duration}s)" if session_duration else ""
            print(f"[AUTH_LOG] Logout: {user_identifier}{duration_text}")
            
            return True
            
        except Exception as e:
            # Log apenas no console, nunca re-raise
            print(f"[AUTH_LOG_ERROR] Erro no log de logout: {str(e)}")
            return True
    
    def log_access_denied(self, reason=None, user_email=None):
        """
        Registra acesso negado de forma completamente segura
        
        Args:
            reason: Razão da negação
            user_email: Email do usuário (opcional)
        
        Returns:
            bool: Sempre True (nunca falha)
        """
        try:
            if not self.enabled:
                return True
            
            access_logger.log_access(
                'access_denied',
                success=False,
                error_message=reason or 'Acesso negado',
                http_status=403
            )
            
            # Log no console para debug
            user_identifier = user_email or 'Unknown'
            print(f"[AUTH_LOG] Access Denied: {user_identifier} - {reason}")
            
            return True
            
        except Exception as e:
            print(f"[AUTH_LOG_ERROR] Erro no log de acesso negado: {str(e)}")
            return True
    
    def log_password_reset(self, email, success=True):
        """Registra tentativa de reset de senha"""
        try:
            if not self.enabled:
                return True
            
            access_logger.log_access(
                'password_reset',
                page_name='Reset de Senha',
                module_name='auth',
                success=success
            )
            
            status = "SUCCESS" if success else "FAILED"
            print(f"[AUTH_LOG] Password Reset {status}: {email}")
            return True
            
        except Exception as e:
            print(f"[AUTH_LOG_ERROR] Erro no log de reset: {str(e)}")
            return True
    
    def log_session_expired(self, user_email=None):
        """Registra expiração de sessão"""
        try:
            if not self.enabled:
                return True
            
            access_logger.log_access(
                'session_expired',
                page_name='Sessão Expirada',
                module_name='auth',
                success=True
            )
            
            user_identifier = user_email or 'Unknown'
            print(f"[AUTH_LOG] Session Expired: {user_identifier}")
            return True
            
        except Exception as e:
            print(f"[AUTH_LOG_ERROR] Erro no log de sessão expirada: {str(e)}")
            return True

# Instância global
auth_logging = AuthLoggingIntegration()

# Funções de conveniência para uso direto
def safe_log_login_success(user_data):
    """Log de login bem-sucedido - nunca falha"""
    return auth_logging.log_login_attempt(
        user_data=user_data,
        success=True
    )

def safe_log_login_failure(email=None, error_message=None):
    """Log de falha no login - nunca falha"""
    return auth_logging.log_login_attempt(
        email=email,
        success=False,
        error_message=error_message
    )

def safe_log_logout(user_email=None):
    """Log de logout - nunca falha"""
    return auth_logging.log_logout_attempt(user_email)

def safe_log_access_denied(reason=None):
    """Log de acesso negado - nunca falha"""
    return auth_logging.log_access_denied(reason)

def safe_log_password_reset(email, success=True):
    """Log de reset de senha - nunca falha"""
    return auth_logging.log_password_reset(email, success)

def safe_log_session_expired(user_email=None):
    """Log de sessão expirada - nunca falha"""
    return auth_logging.log_session_expired(user_email)
