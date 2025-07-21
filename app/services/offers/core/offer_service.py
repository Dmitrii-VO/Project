# app/services/offers/core/offer_service.py
"""
Основной сервис для бизнес-логики офферов
Централизует всю логику работы с офферами
"""

import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from app.services.auth_service import auth_service
from app.models.offer import Offer, OfferStatus
from .offer_repository import OfferRepository
from .offer_validator import OfferValidator
from ..utils.offer_formatter import OfferFormatter
from ..utils.offer_matcher import OfferMatcher
import logging

logger = logging.getLogger(__name__)


class OfferService:
    """Основной сервис для работы с офферами"""
    
    def __init__(self):
        self.repository = OfferRepository()
        self.validator = OfferValidator()
        self.formatter = OfferFormatter()
        self.matcher = OfferMatcher()
    
    def get_my_offers(self, filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Получение моих офферов с полной статистикой"""
        # Получаем пользователя
        telegram_id = auth_service.get_current_user_id()
        if not telegram_id:
            raise ValueError("Требуется авторизация")
        
        user_db_id = auth_service.get_user_db_id()
        if not user_db_id:
            raise ValueError("Пользователь не найден")
        
        # Получаем офферы и общее количество
        offers, total_count = self.repository.get_user_offers(user_db_id, filters or {})
        
        if not offers:
            return {
                'success': True,
                'offers': [],
                'count': 0,
                'total_count': total_count,
                'page': filters.get('page', 1) if filters else 1,
                'total_pages': 0,
                'user_db_id': user_db_id
            }
        
        # Получаем статистику откликов одним запросом
        offer_ids = [offer['id'] for offer in offers]
        response_stats = self.repository.get_offer_response_statistics(offer_ids)
        
        # Форматируем офферы
        formatted_offers = []
        for offer in offers:
            offer_id = offer['id']
            stats = response_stats.get(offer_id, {
                'total_count': 0,
                'accepted_count': 0, 
                'pending_count': 0,
                'rejected_count': 0
            })
            
            formatted_offer = self.formatter.format_offer_for_user(offer, stats)
            formatted_offers.append(formatted_offer)
        
        # Рассчитываем общую статистику
        total_responses = sum(stats.get('total_count', 0) for stats in response_stats.values())
        total_accepted = sum(stats.get('accepted_count', 0) for stats in response_stats.values())
        total_pending = sum(stats.get('pending_count', 0) for stats in response_stats.values())
        
        page = filters.get('page', 1) if filters else 1
        limit = filters.get('limit', 50) if filters else 50
        
        return {
            'success': True,
            'offers': formatted_offers,
            'count': len(formatted_offers),
            'total_count': total_count,
            'page': page,
            'total_pages': (total_count + limit - 1) // limit,
            'user_db_id': user_db_id,
            'telegram_id': telegram_id,
            'summary': {
                'total_offers': total_count,
                'total_responses': total_responses,
                'total_accepted': total_accepted,
                'total_pending': total_pending,
                'overall_acceptance_rate': round((total_accepted / total_responses * 100) if total_responses > 0 else 0, 1)
            },
            'filters': filters or {}
        }
    
    def get_available_offers(self, filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Получение доступных офферов для владельцев каналов"""
        # Получаем текущего пользователя (опционально)
        telegram_id = auth_service.get_current_user_id()
        user_db_id = None
        
        if telegram_id:
            user_db_id = auth_service.get_user_db_id()
        
        # Получаем офферы
        offers, total_count = self.repository.get_available_offers(user_db_id, filters or {})
        
        # Форматируем офферы
        formatted_offers = []
        for offer in offers:
            formatted_offer = self.formatter.format_offer_for_public(offer)
            formatted_offers.append(formatted_offer)
        
        page = filters.get('page', 1) if filters else 1
        limit = filters.get('limit', 10) if filters else 10
        
        return {
            'success': True,
            'offers': formatted_offers,
            'count': len(formatted_offers),
            'total_count': total_count,
            'page': page,
            'total_pages': (total_count + limit - 1) // limit
        }
    
    def create_offer(self, offer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Создание нового оффера"""
        # Авторизация
        telegram_id = auth_service.get_current_user_id()
        if not telegram_id:
            raise ValueError("Требуется авторизация")
        
        # Валидация данных
        validation_errors = self.validator.validate_offer_data(offer_data)
        if validation_errors:
            raise ValueError(f"Ошибки валидации: {'; '.join(validation_errors)}")
        
        # Получаем/создаем пользователя
        user_db_id = auth_service.ensure_user_exists(
            username=offer_data.get('username'),
            first_name=offer_data.get('first_name')
        )
        
        if not user_db_id:
            raise ValueError("Ошибка создания пользователя")
        
        # Подготавливаем данные
        offer_data['creator_telegram_id'] = telegram_id
        
        # Создаем оффер
        offer_id = self.repository.create_offer(user_db_id, offer_data)
        
        # Создаем предложения для выбранных каналов
        if offer_data.get('selected_channels'):
            channel_ids = offer_data['selected_channels']
            created_proposals = self.repository.create_offer_proposals(offer_id, channel_ids)
            
            # Отправляем уведомления (асинхронно)
            self._send_notifications_async(offer_id, created_proposals)
        
        # Получаем созданный оффер
        created_offer = self.repository.get_offer_by_id(offer_id, user_db_id)
        
        return {
            'success': True,
            'offer_id': offer_id,
            'offer': created_offer,
            'message': 'Оффер успешно создан'
        }
    
    def get_offer_details(self, offer_id: int) -> Dict[str, Any]:
        """Получение деталей оффера"""
        # Авторизация
        telegram_id = auth_service.get_current_user_id()
        if not telegram_id:
            raise ValueError("Требуется авторизация")
        
        user_db_id = auth_service.get_user_db_id()
        if not user_db_id:
            raise ValueError("Пользователь не найден")
        
        # Получаем оффер
        offer = self.repository.get_offer_by_id(offer_id, user_db_id)
        if not offer:
            raise ValueError("Оффер не найден")
        
        # Форматируем для ответа
        formatted_offer = self.formatter.format_offer_details(offer)
        
        return {
            'success': True,
            'offer': formatted_offer
        }
    
    def update_offer_status(self, offer_id: int, new_status: str, reason: str = '') -> Dict[str, Any]:
        """Обновление статуса оффера"""
        # Авторизация и проверка прав
        telegram_id = auth_service.get_current_user_id()
        if not telegram_id:
            raise ValueError("Требуется авторизация")
        
        user_db_id = auth_service.get_user_db_id()
        if not user_db_id:
            raise ValueError("Пользователь не найден")
        
        # Валидация статуса
        if not self.validator.validate_status_transition(offer_id, new_status):
            raise ValueError(f"Недопустимый переход статуса на '{new_status}'")
        
        # Обновляем статус
        success = self.repository.update_offer_status(offer_id, new_status, reason)
        if not success:
            raise ValueError("Ошибка обновления статуса")
        
        return {
            'success': True,
            'message': f'Статус оффера изменен на "{new_status}"',
            'offer_id': offer_id,
            'status': new_status
        }
    
    def delete_offer(self, offer_id: int) -> Dict[str, Any]:
        """Удаление оффера"""
        # Авторизация
        telegram_id = auth_service.get_current_user_id()
        if not telegram_id:
            raise ValueError("Требуется авторизация")
        
        user_db_id = auth_service.get_user_db_id()
        if not user_db_id:
            raise ValueError("Пользователь не найден")
        
        # Получаем оффер для проверки
        offer = self.repository.get_offer_by_id(offer_id, user_db_id)
        if not offer:
            raise ValueError("Оффер не найден или у вас нет прав на его удаление")
        
        # Удаляем оффер
        success = self.repository.delete_offer(offer_id, user_db_id)
        if not success:
            raise ValueError("Ошибка при удалении оффера")
        
        return {
            'success': True,
            'message': f'Оффер "{offer["title"]}" успешно удален',
            'offer_id': offer_id
        }
    
    def get_offer_responses(self, offer_id: int) -> Dict[str, Any]:
        """Получение откликов на оффер"""
        # Авторизация
        telegram_id = auth_service.get_current_user_id()
        if not telegram_id:
            raise ValueError("Требуется авторизация")
        
        user_db_id = auth_service.get_user_db_id()
        if not user_db_id:
            raise ValueError("Пользователь не найден")
        
        # Получаем отклики
        responses = self.repository.get_offer_responses(offer_id, user_db_id)
        
        # Форматируем отклики
        formatted_responses = []
        for response in responses:
            formatted_response = self.formatter.format_offer_response(response)
            formatted_responses.append(formatted_response)
        
        # Получаем информацию об оффере
        offer = self.repository.get_offer_by_id(offer_id, user_db_id)
        
        return {
            'success': True,
            'responses': formatted_responses,
            'count': len(formatted_responses),
            'offer': {
                'id': offer['id'],
                'title': offer['title'],
                'status': offer['status']
            } if offer else None
        }
    
    def get_offer_statistics(self) -> Dict[str, Any]:
        """Получение статистики офферов пользователя"""
        # Авторизация
        telegram_id = auth_service.get_current_user_id()
        if not telegram_id:
            raise ValueError("Требуется авторизация")
        
        user_db_id = auth_service.get_user_db_id()
        if not user_db_id:
            raise ValueError("Пользователь не найден")
        
        # Получаем статистику
        stats = self.repository.get_offer_statistics(user_db_id)
        
        return {
            'success': True,
            'stats': stats
        }
    
    def _send_notifications_async(self, offer_id: int, proposals: List[Dict]):
        """Асинхронная отправка уведомлений о новых предложениях"""
        try:
            from flask import current_app
            
            notification_results = []
            for proposal in proposals:
                try:
                    notification_service = current_app.telegram_notifications
                    success = notification_service.send_new_proposal_notification(proposal['proposal_id'])
                    notification_results.append({
                        'proposal_id': proposal['proposal_id'],
                        'notification_sent': success
                    })
                except Exception as e:
                    logger.error(f"Ошибка отправки уведомления: {e}")
                    notification_results.append({
                        'proposal_id': proposal['proposal_id'],
                        'notification_sent': False
                    })
            
            successful_notifications = sum(1 for r in notification_results if r['notification_sent'])
            logger.info(f"Отправлено уведомлений: {successful_notifications}/{len(proposals)}")
            
        except Exception as e:
            logger.error(f"Ошибка отправки уведомлений для оффера {offer_id}: {e}")
    
    def get_offer_categories(self) -> Dict[str, Any]:
        """Получение списка категорий офферов"""
        categories = [
            {'id': 'general', 'name': 'Общие', 'description': 'Общие предложения'},
            {'id': 'tech', 'name': 'Технологии', 'description': 'IT, гаджеты, программы'},
            {'id': 'finance', 'name': 'Финансы', 'description': 'Банки, инвестиции, криптовалюты'},
            {'id': 'lifestyle', 'name': 'Образ жизни', 'description': 'Мода, красота, здоровье'},
            {'id': 'education', 'name': 'Образование', 'description': 'Курсы, книги, обучение'},
            {'id': 'entertainment', 'name': 'Развлечения', 'description': 'Игры, фильмы, музыка'},
            {'id': 'business', 'name': 'Бизнес', 'description': 'Услуги, консалтинг, стартапы'},
            {'id': 'health', 'name': 'Здоровье', 'description': 'Медицина, фитнес, питание'},
            {'id': 'sports', 'name': 'Спорт', 'description': 'Спортивные товары и события'},
            {'id': 'travel', 'name': 'Путешествия', 'description': 'Туризм, отели, авиабилеты'},
            {'id': 'other', 'name': 'Другое', 'description': 'Прочие категории'}
        ]
        
        return {
            'success': True,
            'categories': categories
        }
    
    def get_user_summary(self) -> Dict[str, Any]:
        """Получение сводной информации пользователя"""
        # Авторизация
        telegram_id = auth_service.get_current_user_id()
        if not telegram_id:
            raise ValueError("Требуется авторизация")
        
        user_db_id = auth_service.get_user_db_id()
        if not user_db_id:
            raise ValueError("Пользователь не найден")
        
        # Получаем статистику
        stats = self.repository.get_offer_statistics(user_db_id)
        
        return {
            'success': True,
            'summary': {
                'total_offers': stats['total_offers'],
                'active_offers': stats['active_offers'], 
                'total_responses': stats['total_responses'],
                'pending_responses': 0,  # TODO: добавить в репозиторий
                'total_budget': stats['total_spent']
            }
        }