from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class OnlineUserService:
    _instance = None
    _users = {}  # Dict to store user data: {user_id: {data}}
    _timeout_seconds = 60  # Consider offline after 60 seconds without heartbeat

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(OnlineUserService, cls).__new__(cls)
        return cls._instance

    def update_heartbeat(self, user_id, user_data):
        """
        Updates the heartbeat for a user.
        user_data should include: user_name, user_email, user_role, current_page, page_title, ip_address
        """
        now = datetime.now()
        
        if user_id not in self._users:
            logger.info(f"New user online: {user_data.get('user_name')} ({user_id})")
        
        self._users[user_id] = {
            **user_data,
            'last_seen': now,
            'user_id': user_id
        }

    def get_online_users(self):
        """
        Returns a list of online users, filtering out inactive ones.
        """
        self._cleanup_inactive_users()
        
        # Convert datetime objects to ISO format strings for JSON serialization
        users_list = []
        for user in self._users.values():
            user_copy = user.copy()
            if isinstance(user_copy['last_seen'], datetime):
                user_copy['last_seen'] = user_copy['last_seen'].isoformat()
            users_list.append(user_copy)
            
        return users_list

    def _cleanup_inactive_users(self):
        """
        Removes users who haven't sent a heartbeat recently.
        """
        now = datetime.now()
        threshold = now - timedelta(seconds=self._timeout_seconds)
        
        inactive_users = [
            uid for uid, data in self._users.items() 
            if data['last_seen'] < threshold
        ]
        
        for uid in inactive_users:
            logger.info(f"User timed out: {self._users[uid].get('user_name')} ({uid})")
            del self._users[uid]

    def get_stats(self):
        """
        Returns statistics about online users.
        """
        self._cleanup_inactive_users()
        users = self._users.values()
        
        return {
            'total_online': len(users),
            'internal_users': sum(1 for u in users if u.get('user_role') in ['admin', 'interno_unique']),
            'active_pages': len(set(u.get('current_page') for u in users if u.get('current_page')))
        }

online_user_service = OnlineUserService()
