#!/usr/bin/env python3
"""
Трекер размещений
Отслеживание эффективности рекламных размещений
"""

import logging
from typing import Dict, Any, List
from datetime import datetime

from app.models.database import execute_db_query

logger = logging.getLogger(__name__)

class PlacementTracker:
    """Трекер рекламных размещений"""
    
    def __init__(self):
        pass
    
    def track_placement_click(self, placement_id: int, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Отслеживание клика по размещению"""
        try:
            # Записываем клик в аналитику
            execute_db_query(
                """INSERT INTO placement_clicks 
                   (placement_id, ip_address, user_agent, clicked_at)
                   VALUES (?, ?, ?, ?)""",
                (
                    placement_id,
                    user_data.get('ip_address'),
                    user_data.get('user_agent'),
                    datetime.now()
                )
            )
            
            # Обновляем счетчик кликов
            execute_db_query(
                """UPDATE offer_placements 
                   SET clicks_count = clicks_count + 1, updated_at = ?
                   WHERE id = ?""",
                (datetime.now(), placement_id)
            )
            
            return {'success': True, 'placement_id': placement_id}
            
        except Exception as e:
            logger.error(f"❌ Ошибка отслеживания клика: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_placement_analytics(self, placement_id: int) -> Dict[str, Any]:
        """Получение аналитики размещения"""
        try:
            placement = execute_db_query(
                """SELECT p.*, COUNT(c.id) as total_clicks
                   FROM offer_placements p
                   LEFT JOIN placement_clicks c ON p.id = c.placement_id
                   WHERE p.id = ?
                   GROUP BY p.id""",
                (placement_id,),
                fetch_one=True
            )
            
            if placement:
                return {
                    'success': True,
                    'data': dict(placement)
                }
            else:
                return {'success': False, 'error': 'Размещение не найдено'}
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения аналитики: {e}")
            return {'success': False, 'error': str(e)}