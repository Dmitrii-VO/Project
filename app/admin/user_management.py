#!/usr/bin/env python3
"""
Управление пользователями
Административные функции для работы с пользователями
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.models.database import execute_db_query

logger = logging.getLogger(__name__)

class UserManager:
    """Менеджер пользователей"""
    
    def __init__(self):
        pass
    
    def get_all_users(self, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """Получение списка всех пользователей"""
        try:
            users = execute_db_query(
                """SELECT id, telegram_id, username, first_name, last_name, 
                          is_admin, is_active, created_at, last_activity
                   FROM users 
                   ORDER BY created_at DESC 
                   LIMIT ? OFFSET ?""",
                (limit, offset),
                fetch_all=True
            )
            
            total_count = execute_db_query(
                "SELECT COUNT(*) as total FROM users",
                fetch_one=True
            )
            
            return {
                'success': True,
                'data': {
                    'users': [dict(user) for user in users] if users else [],
                    'total_count': total_count['total'] if total_count else 0,
                    'limit': limit,
                    'offset': offset
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения пользователей: {e}")
            return {'success': False, 'error': str(e)}
    
    def update_user_status(self, user_id: int, is_active: bool) -> Dict[str, Any]:
        """Обновление статуса пользователя"""
        try:
            execute_db_query(
                """UPDATE users 
                   SET is_active = ?, updated_at = ?
                   WHERE id = ?""",
                (is_active, datetime.now(), user_id)
            )
            
            return {
                'success': True,
                'message': f'Статус пользователя {user_id} обновлен'
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка обновления статуса: {e}")
            return {'success': False, 'error': str(e)}
    
    def grant_admin_privileges(self, user_id: int) -> Dict[str, Any]:
        """Предоставление административных прав"""
        try:
            execute_db_query(
                """UPDATE users 
                   SET is_admin = 1, updated_at = ?
                   WHERE id = ?""",
                (datetime.now(), user_id)
            )
            
            return {
                'success': True,
                'message': f'Пользователь {user_id} получил права администратора'
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка предоставления прав: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Получение статистики пользователя"""
        try:
            # Статистика каналов
            channels_count = execute_db_query(
                "SELECT COUNT(*) as count FROM channels WHERE owner_id = ?",
                (user_id,),
                fetch_one=True
            )
            
            # Статистика офферов
            offers_count = execute_db_query(
                "SELECT COUNT(*) as count FROM offers WHERE created_by = ?",
                (user_id,),
                fetch_one=True
            )
            
            return {
                'success': True,
                'data': {
                    'channels_count': channels_count['count'] if channels_count else 0,
                    'offers_count': offers_count['count'] if offers_count else 0
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики: {e}")
            return {'success': False, 'error': str(e)}