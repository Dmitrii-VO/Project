#!/usr/bin/env python3
"""
Модерация каналов
Административные функции для модерации и управления каналами
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.models.database import execute_db_query

logger = logging.getLogger(__name__)

class ChannelModerator:
    """Модератор каналов"""
    
    def __init__(self):
        pass
    
    def get_pending_channels(self, limit: int = 50) -> Dict[str, Any]:
        """Получение каналов на модерации"""
        try:
            channels = execute_db_query(
                """SELECT c.*, u.username as owner_username
                   FROM channels c
                   LEFT JOIN users u ON c.owner_id = u.id
                   WHERE c.verification_status = 'pending'
                   ORDER BY c.created_at ASC 
                   LIMIT ?""",
                (limit,),
                fetch_all=True
            )
            
            return {
                'success': True,
                'data': [dict(channel) for channel in channels] if channels else []
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения каналов на модерации: {e}")
            return {'success': False, 'error': str(e)}
    
    def approve_channel(self, channel_id: int, admin_id: int, notes: str = None) -> Dict[str, Any]:
        """Одобрение канала"""
        try:
            execute_db_query(
                """UPDATE channels 
                   SET verification_status = 'verified',
                       approved_by = ?,
                       approved_at = ?,
                       moderation_notes = ?,
                       updated_at = ?
                   WHERE id = ?""",
                (admin_id, datetime.now(), notes, datetime.now(), channel_id)
            )
            
            return {
                'success': True,
                'message': f'Канал {channel_id} одобрен'
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка одобрения канала: {e}")
            return {'success': False, 'error': str(e)}
    
    def reject_channel(self, channel_id: int, admin_id: int, reason: str) -> Dict[str, Any]:
        """Отклонение канала"""
        try:
            execute_db_query(
                """UPDATE channels 
                   SET verification_status = 'rejected',
                       rejected_by = ?,
                       rejected_at = ?,
                       rejection_reason = ?,
                       updated_at = ?
                   WHERE id = ?""",
                (admin_id, datetime.now(), reason, datetime.now(), channel_id)
            )
            
            return {
                'success': True,
                'message': f'Канал {channel_id} отклонен'
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка отклонения канала: {e}")
            return {'success': False, 'error': str(e)}
    
    def suspend_channel(self, channel_id: int, admin_id: int, reason: str) -> Dict[str, Any]:
        """Приостановка канала"""
        try:
            execute_db_query(
                """UPDATE channels 
                   SET status = 'suspended',
                       suspended_by = ?,
                       suspended_at = ?,
                       suspension_reason = ?,
                       updated_at = ?
                   WHERE id = ?""",
                (admin_id, datetime.now(), reason, datetime.now(), channel_id)
            )
            
            return {
                'success': True,
                'message': f'Канал {channel_id} приостановлен'
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка приостановки канала: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_moderation_history(self, channel_id: int) -> Dict[str, Any]:
        """Получение истории модерации канала"""
        try:
            history = execute_db_query(
                """SELECT verification_status, approved_by, approved_at,
                          rejected_by, rejected_at, rejection_reason,
                          suspended_by, suspended_at, suspension_reason,
                          moderation_notes
                   FROM channels 
                   WHERE id = ?""",
                (channel_id,),
                fetch_one=True
            )
            
            if history:
                return {
                    'success': True,
                    'data': dict(history)
                }
            else:
                return {'success': False, 'error': 'Канал не найден'}
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения истории модерации: {e}")
            return {'success': False, 'error': str(e)}