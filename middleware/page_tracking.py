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
            # Script de tracking via Heartbeat (Substitui WebSocket)
            tracking_script = """
<script>
// Page Tracking via Heartbeat
(function() {
    const HEARTBEAT_INTERVAL = 30000; // 30 segundos

    function sendHeartbeat() {
        fetch('/usuarios-online/api/heartbeat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                page: window.location.pathname,
                title: document.title
            })
        }).catch(err => console.error('Heartbeat error:', err));
    }

    // Envia heartbeat inicial
    sendHeartbeat();

    // Configura intervalo
    setInterval(sendHeartbeat, HEARTBEAT_INTERVAL);
    
    console.log('📊 Page tracking ativo (Heartbeat):', window.location.pathname);
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
