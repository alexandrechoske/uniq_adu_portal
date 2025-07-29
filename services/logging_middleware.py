"""
Middleware para logging automático de acessos - Versão de produção
IMPORTANTE: Este middleware NUNCA deve falhar ou impactar a aplicação
"""
from flask import request, session, g
import time
from services.access_logger import access_logger

class RobustLoggingMiddleware:
    """
    Middleware robusto para logging automático de acessos às páginas
    
    GARANTIAS:
    1. Nunca impede carregamento de páginas
    2. Nunca gera exceptions não tratadas
    3. Performance mínima (< 5ms overhead)
    4. Graceful degradation em caso de problemas
    """
    
    def __init__(self, app=None):
        self.app = app
        self.enabled = True
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Inicializa o middleware com a aplicação Flask"""
        try:
            app.before_request(self.before_request)
            app.after_request(self.after_request)
            print("[LOGGING_MIDDLEWARE] Middleware de logging inicializado")
        except Exception as e:
            print(f"[LOGGING_MIDDLEWARE_ERROR] Falha na inicialização: {e}")
            self.enabled = False
    
    def before_request(self):
        """Executado antes de cada request - deve ser ultra rápido"""
        try:
            if self.enabled:
                g.access_log_start_time = time.time()
                g.access_log_should_log = self._should_log_request()
        except Exception:
            # Silenciosamente ignora erros no before_request
            pass
    
    def after_request(self, response):
        """Executado após cada request - nunca pode falhar"""
        try:
            if (self.enabled and 
                hasattr(g, 'access_log_should_log') and 
                g.access_log_should_log):
                self._log_request_safe(response)
        except Exception:
            # Silenciosamente ignora erros - jamais afetar a resposta
            pass
        return response  # SEMPRE retorna a resposta original
    
    def _should_log_request(self):
        """Determina se deve fazer log da requisição"""
        try:
            # Não fazer log de arquivos estáticos
            if request.endpoint and (
                request.endpoint.startswith('static') or
                'static' in request.endpoint
            ):
                return False
            
            # Não fazer log de recursos (CSS, JS, imagens)
            static_extensions = (
                '.css', '.js', '.png', '.jpg', '.jpeg', '.gif', 
                '.ico', '.svg', '.woff', '.woff2', '.map', '.ttf'
            )
            if request.path.endswith(static_extensions):
                return False
            
            # Não fazer log de health checks
            if request.path in ['/health', '/ping', '/favicon.ico']:
                return False
            
            # Não fazer log de debug se não for admin
            if (request.path.startswith('/debug') and 
                session.get('user', {}).get('role') != 'admin'):
                return False
            
            return True
            
        except Exception:
            return False  # Em caso de erro, não fazer log
    
    def _get_page_info_safe(self):
        """Extrai informações da página atual de forma segura"""
        try:
            # Mapear rotas para nomes legíveis
            page_mapping = {
                'dashboard.dashboard': {'name': 'Dashboard Principal', 'module': 'dashboard'},
                'dashboard.dashboard_v2': {'name': 'Dashboard V2', 'module': 'dashboard'},
                'dashboard_v2.index': {'name': 'Dashboard V2', 'module': 'dashboard'},
                'materiais.materiais': {'name': 'Análise de Materiais', 'module': 'materiais'},
                'materiais.index': {'name': 'Análise de Materiais', 'module': 'materiais'},
                'usuarios.index': {'name': 'Gestão de Usuários', 'module': 'usuarios'},
                'usuarios.form': {'name': 'Formulário de Usuário', 'module': 'usuarios'},
                'usuarios.novo': {'name': 'Novo Usuário', 'module': 'usuarios'},
                'usuarios.editar': {'name': 'Editar Usuário', 'module': 'usuarios'},
                'relatorios.relatorios': {'name': 'Relatórios', 'module': 'relatorios'},
                'relatorios.index': {'name': 'Relatórios', 'module': 'relatorios'},
                'conferencia.conferencia': {'name': 'Conferência', 'module': 'conferencia'},
                'conferencia.index': {'name': 'Conferência', 'module': 'conferencia'},
                'agente.agente': {'name': 'Consulta Agente', 'module': 'agente'},
                'agente.index': {'name': 'Consulta Agente', 'module': 'agente'},
                'auth.login': {'name': 'Login', 'module': 'auth'},
                'auth.logout': {'name': 'Logout', 'module': 'auth'},
                'welcome': {'name': 'Página Inicial', 'module': 'main'},
                'index': {'name': 'Página Inicial', 'module': 'main'},
            }
            
            endpoint = request.endpoint or 'unknown'
            
            if endpoint in page_mapping:
                page_info = page_mapping[endpoint]
                return page_info['name'], page_info['module']
            
            # Fallback: inferir do endpoint
            if '.' in endpoint:
                module_part, page_part = endpoint.split('.', 1)
                page_name = page_part.replace('_', ' ').title()
                return page_name, module_part
            
            # Último fallback
            return endpoint.replace('_', ' ').title(), 'unknown'
            
        except Exception:
            return 'Unknown Page', 'unknown'
    
    def _log_request_safe(self, response):
        """Registra o log da requisição de forma completamente segura"""
        try:
            page_name, module_name = self._get_page_info_safe()
            
            # Determinar se foi sucesso
            success = 200 <= response.status_code < 400
            error_message = None
            
            if not success:
                error_message = f"HTTP {response.status_code}"
            
            # Registrar log (nunca falha)
            access_logger.log_page_access(
                page_name=page_name,
                module_name=module_name
            )
            
        except Exception:
            # Completamente silencioso - nunca afeta a aplicação
            pass

# Instância global
logging_middleware = RobustLoggingMiddleware()

def safe_log_route_access(page_name=None, module_name=None):
    """
    Decorator ultra-seguro para logging de rotas
    
    GARANTIA: Este decorator NUNCA causará falha na rota
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # SEMPRE executa a função original primeiro
            result = func(*args, **kwargs)
            
            # Tenta fazer log apenas APÓS sucesso, sem afetar resultado
            try:
                final_page_name = page_name or func.__name__.replace('_', ' ').title()
                final_module_name = module_name or 'unknown'
                access_logger.log_page_access(final_page_name, final_module_name)
            except Exception:
                # Completamente silencioso
                pass
            
            return result  # SEMPRE retorna o resultado original
                
        # Preserva metadados da função original
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    return decorator
