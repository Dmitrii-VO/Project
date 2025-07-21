# app/services/offers/utils/offer_matcher.py
"""
Утилита для сопоставления офферов с каналами
Логика подбора подходящих каналов для офферов
"""

from typing import Dict, List, Any, Optional
from app.models.database import execute_db_query
import logging

logger = logging.getLogger(__name__)


class OfferMatcher:
    """Класс для сопоставления офферов с каналами"""
    
    @staticmethod
    def find_matching_channels(offer: Dict[str, Any], filters: Dict[str, Any] = None) -> List[Dict]:
        """Поиск подходящих каналов для оффера"""
        filters = filters or {}
        
        # Базовый запрос для поиска каналов
        query = """
            SELECT c.*, u.username as owner_username, u.first_name as owner_name,
                   u.telegram_id as owner_telegram_id,
                   COUNT(or_resp.id) as response_count,
                   AVG(CASE WHEN or_resp.status = 'accepted' THEN 1.0 ELSE 0.0 END) as acceptance_rate
            FROM channels c
            JOIN users u ON c.owner_id = u.id
            LEFT JOIN offer_responses or_resp ON c.id = or_resp.channel_id
            WHERE c.is_active = 1
        """
        params = []
        
        # Фильтр по количеству подписчиков
        min_subscribers = offer.get('min_subscribers', 0)
        max_subscribers = offer.get('max_subscribers', 0)
        
        if min_subscribers > 0:
            query += " AND c.subscribers >= ?"
            params.append(min_subscribers)
            
        if max_subscribers > 0:
            query += " AND c.subscribers <= ?"
            params.append(max_subscribers)
        
        # Фильтр по категории
        if offer.get('category') and offer['category'] != 'general':
            query += " AND (c.category = ? OR c.category = 'general')"
            params.append(offer['category'])
        
        # Исключаем каналы создателя оффера
        if offer.get('created_by'):
            query += " AND c.owner_id != ?"
            params.append(offer['created_by'])
        
        # Дополнительные фильтры
        if filters.get('min_acceptance_rate'):
            # Фильтр будет применен после группировки
            pass
            
        query += """
            GROUP BY c.id, u.username, u.first_name, u.telegram_id
            ORDER BY c.subscribers DESC, acceptance_rate DESC
        """
        
        # Ограничиваем количество результатов
        limit = filters.get('limit', 50)
        query += f" LIMIT {limit}"
        
        try:
            channels = execute_db_query(query, tuple(params), fetch_all=True)
            
            # Применяем фильтр по acceptance_rate если нужно
            min_acceptance_rate = filters.get('min_acceptance_rate', 0)
            if min_acceptance_rate > 0:
                channels = [
                    ch for ch in channels 
                    if (ch['acceptance_rate'] or 0) >= min_acceptance_rate
                ]
            
            return [dict(channel) for channel in channels]
            
        except Exception as e:
            logger.error(f"Ошибка поиска подходящих каналов: {e}")
            return []
    
    @staticmethod
    def calculate_match_score(offer: Dict[str, Any], channel: Dict[str, Any]) -> float:
        """Расчет оценки соответствия оффера каналу"""
        score = 0.0
        
        try:
            # Соответствие по подписчикам (40% от оценки)
            channel_subs = channel.get('subscribers', 0)
            min_subs = offer.get('min_subscribers', 0)
            max_subs = offer.get('max_subscribers', float('inf'))
            
            if min_subs <= channel_subs <= max_subs:
                # Идеальное попадание в диапазон
                score += 40.0
            elif channel_subs >= min_subs:
                # Больше минимума, но без максимума
                score += 30.0
            elif min_subs > 0:
                # Частичное соответствие
                ratio = channel_subs / min_subs
                score += 20.0 * min(ratio, 1.0)
            
            # Соответствие по категории (25% от оценки)
            offer_category = offer.get('category', 'general')
            channel_category = channel.get('category', 'general')
            
            if offer_category == channel_category:
                score += 25.0
            elif channel_category == 'general' or offer_category == 'general':
                score += 15.0
            
            # История работы канала (20% от оценки)
            acceptance_rate = channel.get('acceptance_rate', 0) or 0
            response_count = channel.get('response_count', 0) or 0
            
            if response_count > 0:
                score += 10.0 + (acceptance_rate * 10.0)
            else:
                score += 5.0  # Новый канал
            
            # Активность канала (15% от оценки)
            if channel.get('is_verified'):
                score += 8.0
            if channel.get('last_post_date'):
                # TODO: учитывать давность последнего поста
                score += 7.0
            
        except Exception as e:
            logger.error(f"Ошибка расчета оценки соответствия: {e}")
            
        return round(score, 2)
    
    @staticmethod
    def get_recommended_channels(offer_id: int, limit: int = 20) -> List[Dict]:
        """Получение рекомендованных каналов для оффера"""
        try:
            # Получаем оффер
            offer = execute_db_query("""
                SELECT * FROM offers WHERE id = ?
            """, (offer_id,), fetch_one=True)
            
            if not offer:
                return []
            
            offer_dict = dict(offer)
            
            # Находим подходящие каналы
            channels = OfferMatcher.find_matching_channels(offer_dict, {'limit': limit * 2})
            
            # Рассчитываем оценки и сортируем
            scored_channels = []
            for channel in channels:
                score = OfferMatcher.calculate_match_score(offer_dict, channel)
                channel['match_score'] = score
                scored_channels.append(channel)
            
            # Сортируем по оценке
            scored_channels.sort(key=lambda x: x['match_score'], reverse=True)
            
            return scored_channels[:limit]
            
        except Exception as e:
            logger.error(f"Ошибка получения рекомендаций для оффера {offer_id}: {e}")
            return []
    
    @staticmethod
    def check_channel_eligibility(offer_id: int, channel_id: int) -> Dict[str, Any]:
        """Проверка подходности канала для оффера"""
        try:
            # Получаем данные оффера и канала
            offer_channel_data = execute_db_query("""
                SELECT o.*, c.*, u.telegram_id as channel_owner_telegram_id
                FROM offers o, channels c
                JOIN users u ON c.owner_id = u.id
                WHERE o.id = ? AND c.id = ?
            """, (offer_id, channel_id), fetch_one=True)
            
            if not offer_channel_data:
                return {
                    'eligible': False,
                    'reason': 'Оффер или канал не найден'
                }
            
            data = dict(offer_channel_data)
            
            # Проверки соответствия
            checks = []
            
            # Проверка подписчиков
            channel_subs = data.get('subscribers', 0)
            min_subs = data.get('min_subscribers', 0)
            max_subs = data.get('max_subscribers', 0)
            
            if min_subs > 0 and channel_subs < min_subs:
                checks.append({
                    'passed': False,
                    'check': 'min_subscribers',
                    'message': f"Недостаточно подписчиков: {channel_subs} < {min_subs}"
                })
            else:
                checks.append({
                    'passed': True,
                    'check': 'min_subscribers',
                    'message': 'Минимальные требования по подписчикам выполнены'
                })
            
            if max_subs > 0 and channel_subs > max_subs:
                checks.append({
                    'passed': False,
                    'check': 'max_subscribers', 
                    'message': f"Слишком много подписчиков: {channel_subs} > {max_subs}"
                })
            else:
                checks.append({
                    'passed': True,
                    'check': 'max_subscribers',
                    'message': 'Максимальные требования по подписчикам выполнены'
                })
            
            # Проверка активности канала
            if not data.get('is_active'):
                checks.append({
                    'passed': False,
                    'check': 'channel_active',
                    'message': 'Канал неактивен'
                })
            else:
                checks.append({
                    'passed': True,
                    'check': 'channel_active',
                    'message': 'Канал активен'
                })
            
            # Проверка что это не собственный канал
            if data.get('created_by') == data.get('owner_id'):
                checks.append({
                    'passed': False,
                    'check': 'not_own_channel',
                    'message': 'Нельзя размещать в собственном канале'
                })
            else:
                checks.append({
                    'passed': True,
                    'check': 'not_own_channel',
                    'message': 'Канал принадлежит другому пользователю'
                })
            
            # Итоговый результат
            all_passed = all(check['passed'] for check in checks)
            failed_checks = [check for check in checks if not check['passed']]
            
            return {
                'eligible': all_passed,
                'reason': '; '.join([check['message'] for check in failed_checks]) if failed_checks else 'Все проверки пройдены',
                'checks': checks,
                'match_score': OfferMatcher.calculate_match_score(data, data) if all_passed else 0
            }
            
        except Exception as e:
            logger.error(f"Ошибка проверки подходности канала {channel_id} для оффера {offer_id}: {e}")
            return {
                'eligible': False,
                'reason': f'Ошибка проверки: {str(e)}'
            }