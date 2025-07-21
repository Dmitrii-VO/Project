# app/services/offers/utils/offer_formatter.py
"""
Форматирование данных офферов для различных контекстов
Централизует логику форматирования ответов API
"""

import json
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class OfferFormatter:
    """Класс для форматирования данных офферов"""
    
    @staticmethod
    def format_offer_for_user(offer: Dict[str, Any], response_stats: Dict[str, Any] = None) -> Dict[str, Any]:
        """Форматирование оффера для владельца (детальная информация)"""
        try:
            response_stats = response_stats or {}
            
            # Парсим метаданные
            metadata = {}
            if offer.get('metadata'):
                try:
                    metadata = json.loads(offer['metadata']) if isinstance(offer['metadata'], str) else offer['metadata']
                except (json.JSONDecodeError, TypeError):
                    metadata = {}
            
            # Форматируем даты
            created_at = OfferFormatter._format_datetime(offer.get('created_at'))
            updated_at = OfferFormatter._format_datetime(offer.get('updated_at'))
            deadline = OfferFormatter._format_datetime(offer.get('deadline'))
            expires_at = OfferFormatter._format_datetime(offer.get('expires_at'))
            
            # Рассчитываем статус истечения
            is_expired = False
            if expires_at:
                try:
                    expire_date = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                    is_expired = expire_date < datetime.now()
                except:
                    pass
            
            return {
                'id': offer['id'],
                'title': offer['title'],
                'description': offer['description'],
                'content': offer.get('content', offer['description']),
                'price': float(offer['price']),
                'currency': offer.get('currency', 'RUB'),
                'category': offer.get('category', 'general'),
                'status': offer['status'],
                'target_audience': offer['target_audience'],
                'requirements': offer.get('requirements', ''),
                'deadline': deadline,
                'expires_at': expires_at,
                'is_expired': is_expired,
                'duration_days': offer.get('duration_days', 30),
                'budget_total': float(offer.get('budget_total', offer['price'])),
                'min_subscribers': offer.get('min_subscribers', 0),
                'max_subscribers': offer.get('max_subscribers', 0),
                'created_at': created_at,
                'updated_at': updated_at,
                'creator': {
                    'db_id': offer.get('creator_db_id', offer.get('created_by')),
                    'username': offer.get('creator_username'),
                    'name': offer.get('creator_name'),
                    'telegram_id': offer.get('creator_telegram_id')
                },
                'statistics': {
                    'total_responses': response_stats.get('total_count', 0),
                    'accepted_responses': response_stats.get('accepted_count', 0),
                    'pending_responses': response_stats.get('pending_count', 0),
                    'rejected_responses': response_stats.get('rejected_count', 0),
                    'acceptance_rate': OfferFormatter._calculate_acceptance_rate(response_stats)
                },
                'metadata': metadata,
                'posting_requirements': metadata.get('posting_requirements', {}),
                'additional_info': metadata.get('additional_info', '')
            }
            
        except Exception as e:
            logger.error(f"Ошибка форматирования оффера для пользователя: {e}")
            return OfferFormatter._get_minimal_offer_format(offer)
    
    @staticmethod
    def format_offer_for_public(offer: Dict[str, Any]) -> Dict[str, Any]:
        """Форматирование оффера для публичного просмотра (ограниченная информация)"""
        try:
            # Парсим метаданные
            metadata = {}
            if offer.get('metadata'):
                try:
                    metadata = json.loads(offer['metadata']) if isinstance(offer['metadata'], str) else offer['metadata']
                except (json.JSONDecodeError, TypeError):
                    metadata = {}
            
            # Проверяем истечение
            is_expired = False
            expires_at = offer.get('expires_at')
            if expires_at:
                try:
                    expire_date = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                    is_expired = expire_date < datetime.now()
                except:
                    pass
            
            return {
                'id': offer['id'],
                'title': offer['title'],
                'description': offer['description'][:500] + '...' if len(offer['description']) > 500 else offer['description'],
                'price': float(offer['price']),
                'currency': offer.get('currency', 'RUB'),
                'category': offer.get('category', 'general'),
                'status': offer['status'],
                'target_audience': offer['target_audience'],
                'requirements': offer.get('requirements', ''),
                'deadline': OfferFormatter._format_datetime(offer.get('deadline')),
                'duration_days': offer.get('duration_days', 30),
                'min_subscribers': offer.get('min_subscribers', 0),
                'max_subscribers': offer.get('max_subscribers', 0),
                'created_at': OfferFormatter._format_datetime(offer.get('created_at')),
                'is_expired': is_expired,
                'creator': {
                    'username': offer.get('creator_username'),
                    'name': offer.get('creator_name')
                },
                'posting_requirements': metadata.get('posting_requirements', {})
            }
            
        except Exception as e:
            logger.error(f"Ошибка форматирования оффера для публичного просмотра: {e}")
            return OfferFormatter._get_minimal_offer_format(offer)
    
    @staticmethod
    def format_offer_details(offer: Dict[str, Any]) -> Dict[str, Any]:
        """Форматирование детальной информации об оффере"""
        try:
            # Используем полное форматирование для пользователя
            formatted = OfferFormatter.format_offer_for_user(offer)
            
            # Добавляем дополнительную детальную информацию
            metadata = {}
            if offer.get('metadata'):
                try:
                    metadata = json.loads(offer['metadata']) if isinstance(offer['metadata'], str) else offer['metadata']
                except (json.JSONDecodeError, TypeError):
                    metadata = {}
            
            formatted.update({
                'full_content': offer.get('content', offer['description']),
                'detailed_requirements': offer.get('requirements', ''),
                'budget_breakdown': {
                    'price_per_post': float(offer['price']),
                    'total_budget': float(offer.get('budget_total', offer['price'])),
                    'currency': offer.get('currency', 'RUB')
                },
                'timeline': {
                    'duration_days': offer.get('duration_days', 30),
                    'deadline': OfferFormatter._format_datetime(offer.get('deadline')),
                    'expires_at': OfferFormatter._format_datetime(offer.get('expires_at'))
                },
                'audience_criteria': {
                    'min_subscribers': offer.get('min_subscribers', 0),
                    'max_subscribers': offer.get('max_subscribers', 0),
                    'target_audience': offer['target_audience']
                }
            })
            
            return formatted
            
        except Exception as e:
            logger.error(f"Ошибка форматирования деталей оффера: {e}")
            return OfferFormatter._get_minimal_offer_format(offer)
    
    @staticmethod
    def format_offer_response(response: Dict[str, Any]) -> Dict[str, Any]:
        """Форматирование отклика на оффер"""
        try:
            return {
                'id': response['id'],
                'offer_id': response['offer_id'],
                'channel_id': response.get('channel_id'),
                'status': response['status'],
                'message': response.get('message', ''),
                'created_at': OfferFormatter._format_datetime(response.get('created_at')),
                'updated_at': OfferFormatter._format_datetime(response.get('updated_at')),
                'channel_owner': {
                    'name': response.get('channel_owner_name', ''),
                    'username': response.get('channel_owner_username'),
                    'telegram_id': response.get('channel_owner_telegram_id')
                },
                'placement': {
                    'id': response.get('placement_id'),
                    'status': response.get('placement_status'),
                    'deadline': OfferFormatter._format_datetime(response.get('placement_deadline'))
                } if response.get('placement_id') else None
            }
            
        except Exception as e:
            logger.error(f"Ошибка форматирования отклика: {e}")
            return {
                'id': response.get('id'),
                'status': response.get('status', 'unknown'),
                'message': 'Ошибка форматирования данных'
            }
    
    @staticmethod
    def format_offer_list(offers: List[Dict[str, Any]], context: str = 'user') -> List[Dict[str, Any]]:
        """Форматирование списка офферов"""
        formatted_offers = []
        
        for offer in offers:
            try:
                if context == 'public':
                    formatted_offer = OfferFormatter.format_offer_for_public(offer)
                else:
                    formatted_offer = OfferFormatter.format_offer_for_user(offer)
                    
                formatted_offers.append(formatted_offer)
                
            except Exception as e:
                logger.error(f"Ошибка форматирования оффера {offer.get('id', 'unknown')}: {e}")
                # Добавляем минимальный формат вместо пропуска
                formatted_offers.append(OfferFormatter._get_minimal_offer_format(offer))
        
        return formatted_offers
    
    @staticmethod
    def format_offer_summary(offer: Dict[str, Any]) -> Dict[str, Any]:
        """Краткое форматирование оффера для списков"""
        try:
            return {
                'id': offer['id'],
                'title': offer['title'],
                'price': float(offer['price']),
                'currency': offer.get('currency', 'RUB'),
                'category': offer.get('category', 'general'),
                'status': offer['status'],
                'created_at': OfferFormatter._format_datetime(offer.get('created_at')),
                'min_subscribers': offer.get('min_subscribers', 0),
                'max_subscribers': offer.get('max_subscribers', 0)
            }
            
        except Exception as e:
            logger.error(f"Ошибка краткого форматирования оффера: {e}")
            return OfferFormatter._get_minimal_offer_format(offer)
    
    @staticmethod
    def _format_datetime(dt_string: Optional[str]) -> Optional[str]:
        """Форматирование даты и времени"""
        if not dt_string:
            return None
        
        try:
            # Пытаемся распарсить разные форматы
            if 'T' in dt_string:
                dt = datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
            else:
                dt = datetime.strptime(dt_string, '%Y-%m-%d %H:%M:%S')
            
            return dt.strftime('%Y-%m-%d %H:%M:%S')
            
        except (ValueError, TypeError):
            return dt_string
    
    @staticmethod
    def _calculate_acceptance_rate(response_stats: Dict[str, Any]) -> float:
        """Расчет процента принятых откликов"""
        total = response_stats.get('total_count', 0)
        accepted = response_stats.get('accepted_count', 0)
        
        if total == 0:
            return 0.0
            
        return round((accepted / total) * 100, 1)
    
    @staticmethod
    def _get_minimal_offer_format(offer: Dict[str, Any]) -> Dict[str, Any]:
        """Минимальный формат оффера при ошибках"""
        return {
            'id': offer.get('id'),
            'title': offer.get('title', 'Без названия'),
            'status': offer.get('status', 'unknown'),
            'price': float(offer.get('price', 0)),
            'currency': offer.get('currency', 'RUB'),
            'created_at': offer.get('created_at'),
            'error': 'Ошибка форматирования данных'
        }