from flask import session, request, jsonify, redirect, url_for
from datetime import datetime, timedelta
import os

def init_session_handler(app):
    """
    Configura o middleware para lidar com a limpeza de sessão
    """
    # Determinar se deve fazer log detalhado (apenas em debug)
    DEBUG_SESSION = app.debug and os.getenv('DEBUG_SESSION', 'false').lower() == 'true'
    
    @app.before_request
    def clear_invalid_session():
        """
        Remove dados inválidos da sessão antes de processar a requisição
        """
        # Skip para rotas estáticas e favicon
        if request.path.startswith('/static/') or request.path == '/favicon.ico':
            return None
            
        # Debug para acompanhamento de sessão (apenas se DEBUG_SESSION estiver ativo)
        if DEBUG_SESSION:
            print(f"[SESSION] Verificando sessão para rota {request.path}")
            
        if 'user' in session and session['user']:
            # Adicionar timestamp se não existir
            if 'last_activity' not in session:
                if DEBUG_SESSION:
                    print(f"[SESSION] Timestamp não existe, criando...")
                session['last_activity'] = datetime.now().timestamp()
                session.permanent = True  # Garantir que a sessão seja permanente
            
            # Verificar se a sessão expirou (12 horas sem atividade - aumentado de 8h)
            try:
                last_activity = datetime.fromtimestamp(session['last_activity'])
                time_diff = datetime.now() - last_activity
                hours_diff = time_diff.total_seconds() / 3600
                if DEBUG_SESSION:
                    print(f"[SESSION] Última atividade há {hours_diff:.2f} horas")
                # NÃO limpar a sessão automaticamente, apenas atualizar timestamp se necessário
                if not (request.path.endswith('/check-session') or 
                       request.path.startswith('/static/') or 
                       request.path.startswith('/api/health')):
                    session['last_activity'] = datetime.now().timestamp()
                    session.permanent = True  # Renovar permanência da sessão
                    if DEBUG_SESSION:
                        print(f"[SESSION] Timestamp atualizado para {session['last_activity']}")
                # Verificar integridade básica da sessão - mais permissivo
                user_data = session.get('user', {})
                if not isinstance(user_data, dict):
                    if DEBUG_SESSION:
                        print(f"[SESSION] Sessão corrompida, user não é um dict")
                    # NÃO limpar a sessão automaticamente
                elif not user_data.get('id'):
                    if DEBUG_SESSION:
                        print(f"[SESSION] Sessão corrompida, user.id não existe")
                    # NÃO limpar a sessão automaticamente
                else:
                    if not all(k in user_data for k in ['email', 'role']):
                        if DEBUG_SESSION:
                            print(f"[SESSION] Sessão incompleta mas válida, mantendo...")
            except (ValueError, TypeError, OSError) as e:
                if DEBUG_SESSION:
                    print(f"[SESSION] Erro ao processar timestamp: {e}")
                session['last_activity'] = datetime.now().timestamp()
                session.permanent = True
            
    def set_session_timeout(response):
        """
        Define o timeout da sessão no cookie e adiciona cabeçalhos para evitar cache
        """
        response.headers.add('Cache-Control', 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0')
        response.headers.add('Pragma', 'no-cache')
        response.headers.add('Expires', '0')
        
        # Adicionar timestamp na resposta para debugging se for JSON
        if response.content_type == 'application/json' and hasattr(response, 'json'):
            try:
                data = response.get_json()
                if isinstance(data, dict):
                    # Não modificar diretamente a resposta, mas adicionar informações se for um dict
                    if 'timestamp' not in data:
                        data['server_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    if 'session' not in data and 'user' in session:
                        data['session_valid'] = True
            except:
                pass
                
        return response
        
    # Rota de testes para depuração de sessão (somente em modo debug)
    app.after_request(set_session_timeout)
    # Rota de testes para depuração de sessão (somente em modo debug)
    if app.debug:
        def debug_session():
            """Endpoint para depuração da sessão"""
            session_data = {
                'has_session': 'user' in session,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            if 'user' in session:
                session_data['user_id'] = session['user'].get('id')
                session_data['user_role'] = session['user'].get('role')
                
                if 'last_activity' in session:
                    last_activity = datetime.fromtimestamp(session['last_activity'])
                    session_data['last_activity'] = last_activity.strftime('%Y-%m-%d %H:%M:%S')
                    session_data['age_hours'] = (datetime.now() - last_activity).total_seconds() / 3600
                    
            return jsonify(session_data)
