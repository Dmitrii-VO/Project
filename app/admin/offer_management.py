#!/usr/bin/env python3
"""
Управление офферами
Административные функции для управления рекламными предложениями
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.models.database import execute_db_query

logger = logging.getLogger(__name__)

class OfferManager:
    """Менеджер офферов"""
    
    def __init__(self):
        pass
    
    def get_all_offers(self, status: str = None, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """Получение списка всех офферов"""
        try:
            where_clause = ""
            params = [limit, offset]
            
            if status:
                where_clause = "WHERE status = ?"
                params = [status, limit, offset]
            
            offers = execute_db_query(
                f"""SELECT o.*, u.username as creator_username
                   FROM offers o
                   LEFT JOIN users u ON o.created_by = u.id
                   {where_clause}
                   ORDER BY o.created_at DESC 
                   LIMIT ? OFFSET ?""",
                params,
                fetch_all=True
            )
            
            return {
                'success': True,
                'data': [dict(offer) for offer in offers] if offers else []
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения офферов: {e}")
            return {'success': False, 'error': str(e)}
    
    def approve_offer(self, offer_id: int, admin_id: int) -> Dict[str, Any]:
        """Одобрение оффера"""
        try:
            execute_db_query(
                """UPDATE offers 
                   SET status = 'approved',
                       approved_by = ?,
                       approved_at = ?,
                       updated_at = ?
                   WHERE id = ?""",
                (admin_id, datetime.now(), datetime.now(), offer_id)
            )
            
            return {
                'success': True,
                'message': f'Оффер {offer_id} одобрен'
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка одобрения оффера: {e}")
            return {'success': False, 'error': str(e)}
    
    def reject_offer(self, offer_id: int, admin_id: int, reason: str) -> Dict[str, Any]:
        """Отклонение оффера"""
        try:
            execute_db_query(
                """UPDATE offers 
                   SET status = 'rejected',
                       rejected_by = ?,
                       rejected_at = ?,
                       rejection_reason = ?,
                       updated_at = ?
                   WHERE id = ?""",
                (admin_id, datetime.now(), reason, datetime.now(), offer_id)
            )
            
            return {
                'success': True,
                'message': f'Оффер {offer_id} отклонен'
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка отклонения оффера: {e}")
            return {'success': False, 'error': str(e)}
    
    def pause_offer(self, offer_id: int, admin_id: int, reason: str = None) -> Dict[str, Any]:
        """Приостановка оффера"""
        try:
            execute_db_query(
                """UPDATE offers 
                   SET status = 'paused',
                       paused_by = ?,
                       paused_at = ?,
                       pause_reason = ?,
                       updated_at = ?
                   WHERE id = ?""",
                (admin_id, datetime.now(), reason, datetime.now(), offer_id)
            )
            
            return {
                'success': True,
                'message': f'Оффер {offer_id} приостановлен'
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка приостановки оффера: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_offer_statistics(self, offer_id: int) -> Dict[str, Any]:
        """Получение статистики оффера"""
        try:
            stats = execute_db_query(
                """SELECT 
                    COUNT(op.id) as total_placements,
                    SUM(op.views_count) as total_views,
                    SUM(op.clicks_count) as total_clicks,
                    AVG(CAST(op.clicks_count AS FLOAT) / NULLIF(op.views_count, 0)) as avg_ctr
                   FROM offer_placements op
                   WHERE op.offer_id = ?""",
                (offer_id,),
                fetch_one=True
            )
            
            if stats:
                return {
                    'success': True,
                    'data': dict(stats)
                }
            else:
                return {'success': False, 'error': 'Статистика не найдена'}
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики оффера: {e}")
            return {'success': False, 'error': str(e)}