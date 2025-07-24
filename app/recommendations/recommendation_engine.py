#!/usr/bin/env python3
"""
Движок рекомендаций
Основная логика системы рекомендаций каналов и офферов
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from .ai_matcher import AIChannelMatcher
from app.models.database import execute_db_query

logger = logging.getLogger(__name__)

class RecommendationEngine:
    """Движок рекомендаций"""
    
    def __init__(self):
        self.ai_matcher = AIChannelMatcher()
    
    def get_recommended_channels_for_offer(self, offer_id: int, limit: int = 10) -> Dict[str, Any]:
        """Получение рекомендованных каналов для оффера"""
        try:
            # Получаем данные оффера
            offer = execute_db_query(
                "SELECT * FROM offers WHERE id = ?",
                (offer_id,),
                fetch_one=True
            )
            
            if not offer:
                return {'success': False, 'error': 'Оффер не найден'}
            
            # Получаем доступные каналы
            channels = execute_db_query(
                """SELECT * FROM channels 
                   WHERE verification_status = 'verified' 
                   AND status = 'active'
                   LIMIT 100""",
                fetch_all=True
            )
            
            if not channels:
                return {'success': True, 'data': []}
            
            # Используем AI для подбора
            recommendations = self.ai_matcher.find_matching_channels(
                dict(offer), 
                [dict(channel) for channel in channels]
            )
            
            # Ограничиваем количество
            limited_recommendations = recommendations['data'][:limit] if recommendations['success'] else []
            
            return {
                'success': True,
                'data': limited_recommendations
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения рекомендаций каналов: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_recommended_offers_for_channel(self, channel_id: int, limit: int = 10) -> Dict[str, Any]:
        """Получение рекомендованных офферов для канала"""
        try:
            # Получаем данные канала
            channel = execute_db_query(
                "SELECT * FROM channels WHERE id = ?",
                (channel_id,),
                fetch_one=True
            )
            
            if not channel:
                return {'success': False, 'error': 'Канал не найден'}
            
            # Получаем активные офферы
            offers = execute_db_query(
                """SELECT * FROM offers 
                   WHERE status = 'active'
                   AND budget_total > budget_spent
                   LIMIT 100""",
                fetch_all=True
            )
            
            if not offers:
                return {'success': True, 'data': []}
            
            # Используем AI для подбора
            recommendations = self.ai_matcher.find_matching_offers(
                dict(channel), 
                [dict(offer) for offer in offers]
            )
            
            # Ограничиваем количество
            limited_recommendations = recommendations['data'][:limit] if recommendations['success'] else []
            
            return {
                'success': True,
                'data': limited_recommendations
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения рекомендаций офферов: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_personalized_recommendations(self, user_id: int) -> Dict[str, Any]:
        """Получение персонализированных рекомендаций"""
        try:
            # Анализируем историю пользователя
            user_channels = execute_db_query(
                "SELECT * FROM channels WHERE owner_id = ?",
                (user_id,),
                fetch_all=True
            )
            
            user_offers = execute_db_query(
                "SELECT * FROM offers WHERE created_by = ?",
                (user_id,),
                fetch_all=True
            )
            
            recommendations = {
                'trending_offers': self._get_trending_offers(),
                'popular_channels': self._get_popular_channels(),
                'similar_users_activity': self._get_similar_users_activity(user_id)
            }
            
            return {
                'success': True,
                'data': recommendations
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения персонализированных рекомендаций: {e}")
            return {'success': False, 'error': str(e)}
    
    def _get_trending_offers(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Получение трендовых офферов"""
        try:
            offers = execute_db_query(
                """SELECT o.*, COUNT(op.id) as placement_count
                   FROM offers o
                   LEFT JOIN offer_placements op ON o.id = op.offer_id
                   WHERE o.status = 'active'
                   GROUP BY o.id
                   ORDER BY placement_count DESC, o.created_at DESC
                   LIMIT ?""",
                (limit,),
                fetch_all=True
            )
            
            return [dict(offer) for offer in offers] if offers else []
        except:
            return []
    
    def _get_popular_channels(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Получение популярных каналов"""
        try:
            channels = execute_db_query(
                """SELECT * FROM channels 
                   WHERE verification_status = 'verified' 
                   AND status = 'active'
                   ORDER BY subscriber_count DESC, engagement_rate DESC
                   LIMIT ?""",
                (limit,),
                fetch_all=True
            )
            
            return [dict(channel) for channel in channels] if channels else []
        except:
            return []
    
    def _get_similar_users_activity(self, user_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """Получение активности похожих пользователей"""
        try:
            # Упрощенная логика - возвращаем последние офферы других пользователей
            offers = execute_db_query(
                """SELECT * FROM offers 
                   WHERE created_by != ? 
                   AND status = 'active'
                   ORDER BY created_at DESC
                   LIMIT ?""",
                (user_id, limit),
                fetch_all=True
            )
            
            return [dict(offer) for offer in offers] if offers else []
        except:
            return []