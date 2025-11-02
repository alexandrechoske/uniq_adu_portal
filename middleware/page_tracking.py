"""
Middleware para rastreamento automático de navegação de páginas
Injeta JavaScript em todas as páginas HTML para tracking via WebSocket
"""
from flask import request, g, session
import logging

logger = logging.getLogger(__name__)

class PageTrackingMiddleware:
    """Middleware para injetar script de tracking em páginas HTML"""
    
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Inicializa middleware com a aplicação Flask"""
        app.after_request(self.inject_tracking_script)
        logger.info("✅ PageTrackingMiddleware inicializado")
    
    def inject_tracking_script(self, response):
        """
        Injeta script de tracking em páginas HTML
        """
        # Só injeta em páginas HTML
        if 'text/html' not in response.content_type:
            return response
        
        # Não injeta em páginas de login, logout ou públicas
        excluded_paths = ['/login', '/logout', '/auth/', '/static/', '/carreiras/']
        if any(request.path.startswith(path) for path in excluded_paths):
            return response
        
        # Verifica se usuário está autenticado
        if 'user_id' not in session:
            return response
        
        try:
            # Script de tracking
            tracking_script = """
<script>
// Page Tracking via WebSocket
(function() {
    if (typeof io !== 'undefined' && window.socket) {
        // Envia evento de mudança de página ao carregar
        window.socket.emit('page_change', {
            page: window.location.pathname,
            title: document.title
        });
        
        // Envia heartbeat a cada 30 segundos
        setInterval(function() {
            window.socket.emit('heartbeat');
        }, 30000);
        
        console.log('📊 Page tracking ativo:', window.location.pathname);
    }
})();
</script>
</body>
"""
            # Substitui </body> pelo script + </body>
            data = response.get_data(as_text=True)
            if '</body>' in data:
                data = data.replace('</body>', tracking_script)
                response.set_data(data)
        
        except Exception as e:
            logger.error(f"Erro ao injetar tracking script: {str(e)}")
        
        return response


# Instância global
page_tracking = PageTrackingMiddleware()
