#!/usr/bin/env python3
"""
Движок аналитики
Обработка и агрегация аналитических данных
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta

from app.models.database import execute_db_query

logger = logging.getLogger(__name__)

class AnalyticsEngine:
    """Движок аналитики"""
    
    def __init__(self):
        pass
    
    def generate_user_report(self, user_id: int, period_days: int = 30) -> Dict[str, Any]:
        """Генерация отчета для пользователя"""
        try:
            start_date = datetime.now() - timedelta(days=period_days)
            
            # Статистика каналов пользователя
            channel_stats = execute_db_query(
                """SELECT COUNT(*) as total_channels, 
                          SUM(subscriber_count) as total_subscribers,
                          AVG(engagement_rate) as avg_engagement
                   FROM channels 
                   WHERE owner_id = ? AND created_at >= ?""",
                (user_id, start_date),
                fetch_one=True
            )
            
            # Статистика офферов
            offer_stats = execute_db_query(
                """SELECT COUNT(*) as total_offers,
                          SUM(COALESCE(budget_total, price)) as total_budget
                   FROM offers 
                   WHERE created_by = ? AND created_at >= ?""",
                (user_id, start_date),
                fetch_one=True
            )
            
            return {
                'success': True,
                'data': {
                    'period_days': period_days,
                    'channels': dict(channel_stats) if channel_stats else {},
                    'offers': dict(offer_stats) if offer_stats else {},
                    'generated_at': datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка генерации отчета: {e}")
            return {'success': False, 'error': str(e)}