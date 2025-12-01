"""
WebSocket Event Handlers para rastreamento de usuários online em tempo real
"""
from flask_socketio import emit, disconnect
from flask import request, session
from datetime import datetime, timezone, timedelta
import logging

logger = logging.getLogger(__name__)

# Dicionário em memória para mapear socket_id -> user_id
# Em produção com múltiplos servidores, usar Redis
connected_users = {}

def register_events(socketio, supabase_admin):
    """
    Registra todos os event handlers do WebSocket
    
    Args:
        socketio: Instância do Flask-SocketIO
        supabase_admin: Cliente Supabase com privilégios de service_role
    """
    
    @socketio.on('connect')
    def handle_connect():
        """Quando usuário conecta via WebSocket"""
        try:
            # DEBUG: Log inicial
            print(f"\n[WEBSOCKET] 🔌 Nova tentativa de conexão - SID: {request.sid}")
            print(f"[WEBSOCKET] Headers: {dict(request.headers)}")
            print(f"[WEBSOCKET] Session keys: {list(session.keys()) if session else 'Session vazia'}")
            
            # Pega user_id da sessão Flask
            user_id = session.get('user_id')
            user_name = session.get('user_name', 'Usuário')
            user_role = session.get('user_role', '')
            session_id = session.get('session_id', request.sid)
            is_admin_user = (user_role == 'admin')
            
            print(f"[WEBSOCKET] user_id: {user_id}")
            print(f"[WEBSOCKET] user_name: {user_name}")
            print(f"[WEBSOCKET] user_role: {user_role}")
            print(f"[WEBSOCKET] is_admin: {is_admin_user}")
            
            if not user_id:
                logger.warning(f"Tentativa de conexão sem autenticação. SID: {request.sid}")
                print(f"[WEBSOCKET] ❌ CONEXÃO RECUSADA - sem user_id na sessão")
                disconnect()
                return False
            
            # IP do cliente
            if request.headers.get('X-Forwarded-For'):
                ip_address = request.headers.get('X-Forwarded-For').split(',')[0].strip()
            else:
                ip_address = request.remote_addr
            user_agent = request.headers.get('User-Agent', '')
            current_timestamp = datetime.now(timezone.utc).isoformat()
            
            # Armazena mapeamento em memória
            connected_users[request.sid] = {
                'user_id': user_id,
                'user_name': user_name,
                'session_id': session_id,
                'connected_at': current_timestamp,
                'is_admin': is_admin_user
            }
            
            if is_admin_user:
                # Admins atuam apenas como observadores
                try:
                    from flask_socketio import join_room
                    join_room('admin')
                    logger.info(f"👑 Admin {user_name} (ID: {user_id}) conectado para monitoramento. Socket: {request.sid}")
                except Exception as room_error:
                    logger.error(f"Erro ao adicionar admin à sala: {str(room_error)}")
            else:
                # Registra sessão no banco de dados
                try:
                    supabase_admin.table('user_sessions').insert({
                        'user_id': user_id,
                        'session_id': session_id,
                        'socket_id': request.sid,
                        'ip_address': ip_address,
                        'user_agent': user_agent,
                        'is_active': True,
                        'connected_at': current_timestamp,
                        'last_activity': current_timestamp
                    }).execute()
                    
                    logger.info(f"✅ Usuário {user_name} (ID: {user_id}) conectado. Socket: {request.sid}")
                except Exception as db_error:
                    logger.error(f"Erro ao inserir sessão no banco: {str(db_error)}")
            
            # Admins não entram na listagem, mas precisam da lista atual para visualização
            online_users = get_online_users(supabase_admin)
            emit('initial_online_users', {'users': online_users, 'count': len(online_users)})
            
            if not is_admin_user:
                # Notifica TODOS os outros clientes sobre o novo usuário
                emit('user_connected', {
                    'user_id': user_id,
                    'user_name': user_name,
                    'socket_id': request.sid,
                    'timestamp': current_timestamp
                }, broadcast=True, include_self=False)
            
            return True
            
        except Exception as e:
            logger.error(f"Erro no handle_connect: {str(e)}")
            disconnect()
            return False
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """Quando usuário desconecta"""
        try:
            user_info = connected_users.pop(request.sid, None)
            
            if user_info:
                user_id = user_info['user_id']
                user_name = user_info['user_name']
                is_admin_user = user_info.get('is_admin', False)
                
                if is_admin_user:
                    logger.info(f"👑 Admin {user_name} (ID: {user_id}) desconectado do monitoramento. Socket: {request.sid}")
                else:
                    # Atualiza sessão no banco
                    try:
                        supabase_admin.table('user_sessions')\
                            .update({
                                'is_active': False,
                                'disconnected_at': datetime.now(timezone.utc).isoformat()
                            })\
                            .eq('socket_id', request.sid)\
                            .execute()
                        
                        logger.info(f"❌ Usuário {user_name} (ID: {user_id}) desconectado. Socket: {request.sid}")
                    except Exception as db_error:
                        logger.error(f"Erro ao atualizar sessão no banco: {str(db_error)}")
                    
                    # Notifica todos os outros clientes
                    emit('user_disconnected', {
                        'user_id': user_id,
                        'user_name': user_name,
                        'socket_id': request.sid,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }, broadcast=True)
                
        except Exception as e:
            logger.error(f"Erro no handle_disconnect: {str(e)}")
    
    @socketio.on('page_change')
    def handle_page_change(data):
        """Quando usuário navega para outra página"""
        try:
            user_id = session.get('user_id')
            user_role = session.get('user_role', '')
            
            if not user_id or user_role == 'admin':
                return
            
            current_page = data.get('page', '/')
            page_title = data.get('title', 'Sem título')
            current_timestamp = datetime.now(timezone.utc).isoformat()
            
            # Atualiza no banco
            try:
                supabase_admin.table('user_sessions')\
                    .update({
                        'current_page': current_page,
                        'page_title': page_title,
                        'last_activity': current_timestamp
                    })\
                    .eq('socket_id', request.sid)\
                    .eq('is_active', True)\
                    .execute()
                
                logger.debug(f"📄 Usuário {user_id} navegou para: {current_page} ({page_title})")
            except Exception as db_error:
                logger.error(f"Erro ao atualizar página no banco: {str(db_error)}")
            
            # Notifica admins (broadcast apenas para room 'admin')
            emit('user_page_changed', {
                'user_id': user_id,
                'socket_id': request.sid,
                'page': current_page,
                'title': page_title,
                'timestamp': current_timestamp
            }, room='admin')
            
        except Exception as e:
            logger.error(f"Erro no handle_page_change: {str(e)}")
    
    @socketio.on('heartbeat')
    def handle_heartbeat():
        """Heartbeat para manter conexão ativa e atualizar last_activity"""
        try:
            user_id = session.get('user_id')
            user_role = session.get('user_role', '')
            
            if not user_id or user_role == 'admin':
                return
            
            # Atualiza last_activity no banco
            try:
                current_timestamp = datetime.now(timezone.utc).isoformat()
                supabase_admin.table('user_sessions')\
                    .update({
                        'last_activity': current_timestamp
                    })\
                    .eq('socket_id', request.sid)\
                    .eq('is_active', True)\
                    .execute()
            except Exception as db_error:
                logger.error(f"Erro ao atualizar heartbeat: {str(db_error)}")
            
            # Responde ao cliente
            emit('heartbeat_ack', {'timestamp': datetime.now(timezone.utc).isoformat()})
            
        except Exception as e:
            logger.error(f"Erro no handle_heartbeat: {str(e)}")
    
    @socketio.on('get_online_users')
    def handle_get_online_users():
        """Endpoint para buscar lista completa de usuários online (apenas admins)"""
        try:
            user_id = session.get('user_id')
            user_role = session.get('user_role', '')
            
            # Verifica se é admin
            if user_role != 'admin':
                emit('error', {'message': 'Acesso negado. Apenas administradores.'})
                return
            
            cleanup_inactive_sessions(supabase_admin, timeout_minutes=5)

            # Busca usuários online
            online_users = get_online_users(supabase_admin)
            
            emit('online_users_list', {
                'users': online_users,
                'count': len(online_users),
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            logger.debug(f"📊 Admin {user_id} solicitou lista de usuários online: {len(online_users)} usuários")
            
        except Exception as e:
            logger.error(f"Erro no handle_get_online_users: {str(e)}")
            emit('error', {'message': 'Erro ao buscar usuários online'})
    
    @socketio.on('join_admin_room')
    def handle_join_admin_room():
        """Adiciona admin à room especial para receber eventos de navegação"""
        try:
            user_role = session.get('user_role', '')
            
            if user_role == 'admin':
                from flask_socketio import join_room
                join_room('admin')
                logger.info(f"👑 Admin {session.get('user_id')} entrou na room admin")
        except Exception as e:
            logger.error(f"Erro no handle_join_admin_room: {str(e)}")


def get_online_users(supabase_admin):
    """
    Busca lista de usuários online do banco de dados
    
    Args:
        supabase_admin: Cliente Supabase com privilégios
        
    Returns:
        list: Lista de usuários online com suas informações
    """
    try:
        # Busca sessões ativas com join na tabela users
        response = supabase_admin.table('user_sessions')\
            .select('*, users(id, name, email, role)')\
            .eq('is_active', True)\
            .order('last_activity', desc=True)\
            .execute()
        
        # Formata resultado
        online_users = []
        now_utc = datetime.now(timezone.utc)
        stale_threshold = timedelta(minutes=5)

        for session in response.data:
            user = session.get('users', {})
            user_role = user.get('role', '')

            # Ignora administradores (usados apenas para monitoramento)
            if user_role == 'admin':
                continue

            last_activity_str = session.get('last_activity')
            is_stale = False
            if last_activity_str:
                try:
                    # Compatível com formatação com ou sem timezone
                    normalized = last_activity_str.replace('Z', '+00:00')
                    last_activity_dt = datetime.fromisoformat(normalized)
                    if last_activity_dt.tzinfo is None:
                        last_activity_dt = last_activity_dt.replace(tzinfo=timezone.utc)
                    if now_utc - last_activity_dt > stale_threshold:
                        is_stale = True
                except Exception:
                    # Se não conseguir converter, considera stale para evitar dados presos
                    is_stale = True
            else:
                is_stale = True

            if is_stale:
                # Marca sessão como inativa para não aparecer mais
                try:
                    supabase_admin.table('user_sessions')\
                        .update({
                            'is_active': False,
                            'disconnected_at': now_utc.isoformat()
                        })\
                        .eq('socket_id', session.get('socket_id'))\
                        .execute()
                except Exception as cleanup_error:
                    logger.error(f"Erro ao desativar sessão obsoleta: {cleanup_error}")
                continue

            online_users.append({
                'user_id': session['user_id'],
                'user_name': user.get('name', 'Usuário'),
                'user_email': user.get('email', ''),
                'user_role': user_role,
                'current_page': session.get('current_page', '/'),
                'page_title': session.get('page_title', 'Sem título'),
                'ip_address': session.get('ip_address', ''),
                'connected_at': session.get('connected_at', ''),
                'last_activity': session.get('last_activity', ''),
                'socket_id': session.get('socket_id', '')
            })
        
        return online_users
        
    except Exception as e:
        logger.error(f"Erro ao buscar usuários online: {str(e)}")
        return []


def cleanup_inactive_sessions(supabase_admin, timeout_minutes=30):
    """
    Remove sessões inativas há mais de X minutos
    Útil para executar periodicamente
    
    Args:
        supabase_admin: Cliente Supabase
        timeout_minutes: Minutos de inatividade para considerar sessão morta
    """
    try:
        now_utc = datetime.now(timezone.utc)
        timeout_time = (now_utc - timedelta(minutes=timeout_minutes)).isoformat()
        
        supabase_admin.table('user_sessions')\
            .update({'is_active': False, 'disconnected_at': now_utc.isoformat()})\
            .eq('is_active', True)\
            .lt('last_activity', timeout_time)\
            .execute()
        
        logger.info(f"🧹 Limpeza de sessões inativas executada (timeout: {timeout_minutes}min)")
        
    except Exception as e:
        logger.error(f"Erro ao limpar sessões inativas: {str(e)}")
