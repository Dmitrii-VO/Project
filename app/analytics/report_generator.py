#!/usr/bin/env python3
"""
Генератор отчетов
Создание различных типов аналитических отчетов
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
import json

from app.models.database import execute_db_query

logger = logging.getLogger(__name__)

class ReportGenerator:
    """Генератор аналитических отчетов"""
    
    def __init__(self):
        pass
    
    def generate_channel_performance_report(self, channel_id: int, period_days: int = 30) -> Dict[str, Any]:
        """Генерация отчета о производительности канала"""
        try:
            start_date = datetime.now() - timedelta(days=period_days)
            
            # Получаем данные канала
            channel_data = execute_db_query(
                """SELECT * FROM channels WHERE id = ?""",
                (channel_id,),
                fetch_one=True
            )
            
            if not channel_data:
                return {'success': False, 'error': 'Канал не найден'}
            
            # Статистика размещений
            placements_stats = execute_db_query(
                """SELECT COUNT(*) as total_placements,
                          SUM(views_count) as total_views,
                          SUM(clicks_count) as total_clicks,
                          AVG(CAST(clicks_count AS FLOAT) / NULLIF(views_count, 0)) as avg_ctr
                   FROM offer_placements 
                   WHERE channel_id = ? AND created_at >= ?""",
                (channel_id, start_date),
                fetch_one=True
            )
            
            return {
                'success': True,
                'data': {
                    'channel': dict(channel_data),
                    'period_days': period_days,
                    'placements': dict(placements_stats) if placements_stats else {},
                    'generated_at': datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка генерации отчета: {e}")
            return {'success': False, 'error': str(e)}
    
    def generate_advertiser_report(self, user_id: int, period_days: int = 30) -> Dict[str, Any]:
        """Генерация отчета для рекламодателя"""
        try:
            start_date = datetime.now() - timedelta(days=period_days)
            
            # Статистика офферов
            offers_stats = execute_db_query(
                """SELECT COUNT(*) as total_offers,
                          SUM(budget_total) as total_budget,
                          COUNT(CASE WHEN status = 'active' THEN 1 END) as active_offers
                   FROM offers 
                   WHERE created_by = ? AND created_at >= ?""",
                (user_id, start_date),
                fetch_one=True
            )
            
            return {
                'success': True,
                'data': {
                    'user_id': user_id,
                    'period_days': period_days,
                    'offers': dict(offers_stats) if offers_stats else {},
                    'generated_at': datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка генерации отчета рекламодателя: {e}")
            return {'success': False, 'error': str(e)}