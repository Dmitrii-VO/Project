#!/usr/bin/env python3
"""
Event Dispatcher для Telegram Mini App
Удобные функции для отправки событий из разных частей приложения
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from flask import g, request

from .event_bus import event_bus
from .event_types import EventType, create_event

logger = logging.getLogger(__name__)

class EventDispatcher:
    """Диспетчер событий с удобными методами"""
    
    def __init__(self):
        self.event_bus = event_bus
    
    def _get_current_context(self) -> Dict[str, Any]:
        """Получение текущего контекста запроса"""
        context = {}
        
        try:
            context['user_id'] = getattr(g, 'user_id', None)
            context['session_id'] = getattr(g, 'session_id', None)
            
            if hasattr(request, 'remote_addr'):
                context['ip_address'] = request.remote_addr
                context['user_agent'] = request.headers.get('User-Agent', '')
                context['endpoint'] = request.endpoint
                context['method'] = request.method
                
        except RuntimeError:
            # Вне контекста Flask приложения
            pass
            
        return context
    
    # =================== ПОЛЬЗОВАТЕЛИ ===================
    
    def user_registered(self, user_id: int, telegram_id: int, username: str = None, 
                       first_name: str = None, **kwargs) -> bool:
        """Событие регистрации пользователя"""
        context = self._get_current_context()
        
        event = create_event(
            EventType.USER_REGISTERED,
            user_id=user_id,
            data={
                'telegram_id': telegram_id,
                'username': username,
                'first_name': first_name,
                **kwargs
            },
            metadata=context
        )
        
        return self.event_bus.publish(event)
    
    def user_balance_changed(self, user_id: int, telegram_id: int, old_balance: float, 
                           new_balance: float, change_type: str, description: str = None) -> bool:
        """Событие изменения баланса пользователя"""
        event = create_event(
            EventType.USER_BALANCE_CHANGED,
            user_id=user_id,
            data={
                'telegram_id': telegram_id,
                'old_balance': old_balance,
                'new_balance': new_balance,
                'change_amount': new_balance - old_balance,
                'change_type': change_type,
                'description': description
            }
        )
        
        return self.event_bus.publish(event)
    
    def user_login(self, user_id: int, telegram_id: int, login_method: str = 'telegram') -> bool:
        """Событие входа пользователя"""
        context = self._get_current_context()
        
        event = create_event(
            EventType.USER_LOGIN,
            user_id=user_id,
            data={
                'telegram_id': telegram_id,
                'login_method': login_method
            },
            metadata=context
        )
        
        return self.event_bus.publish(event)
    
    # =================== КАНАЛЫ ===================
    
    def channel_created(self, channel_id: int, owner_id: int, title: str, 
                       username: str = None, category: str = None) -> bool:
        """Событие создания канала"""
        event = create_event(
            EventType.CHANNEL_CREATED,
            user_id=owner_id,
            data={
                'channel_id': channel_id,
                'title': title,
                'username': username,
                'category': category
            }
        )
        
        return self.event_bus.publish(event)
    
    def channel_verified(self, channel_id: int, owner_id: int, title: str) -> bool:
        """Событие верификации канала"""
        event = create_event(
            EventType.CHANNEL_VERIFIED,
            user_id=owner_id,
            data={
                'channel_id': channel_id,
                'title': title
            }
        )
        
        return self.event_bus.publish(event)
    
    def channel_stats_updated(self, channel_id: int, owner_id: int, 
                            old_subscriber_count: int, new_subscriber_count: int) -> bool:
        """Событие обновления статистики канала"""
        event = create_event(
            EventType.CHANNEL_STATS_UPDATED,
            user_id=owner_id,
            data={
                'channel_id': channel_id,
                'old_subscriber_count': old_subscriber_count,
                'new_subscriber_count': new_subscriber_count,
                'subscriber_change': new_subscriber_count - old_subscriber_count
            }
        )
        
        return self.event_bus.publish(event)
    
    # =================== ОФФЕРЫ ===================
    
    def offer_created(self, offer_id: int, advertiser_id: int, title: str, 
                     budget: float = None, category: str = None, **kwargs) -> bool:
        """Событие создания оффера"""
        event = create_event(
            EventType.OFFER_CREATED,
            user_id=advertiser_id,
            data={
                'offer_id': offer_id,
                'title': title,
                'budget': budget,
                'category': category,
                **kwargs
            }
        )
        
        return self.event_bus.publish(event)
    
    def offer_status_changed(self, offer_id: int, advertiser_id: int, 
                           old_status: str, new_status: str, title: str = None) -> bool:
        """Событие изменения статуса оффера"""
        event = create_event(
            EventType.OFFER_STATUS_CHANGED,
            user_id=advertiser_id,
            data={
                'offer_id': offer_id,
                'title': title,
                'old_status': old_status,
                'new_status': new_status
            }
        )
        
        return self.event_bus.publish(event)
    
    # =================== ОТКЛИКИ ===================
    
    def response_created(self, response_id: int, offer_id: int, channel_id: int, 
                        user_id: int, proposed_price: float = None, 
                        response_message: str = None) -> bool:
        """Событие создания отклика на оффер"""
        event = create_event(
            EventType.RESPONSE_CREATED,
            user_id=user_id,
            data={
                'response_id': response_id,
                'offer_id': offer_id,
                'channel_id': channel_id,
                'proposed_price': proposed_price,
                'response_message': response_message
            }
        )
        
        return self.event_bus.publish(event)
    
    def response_accepted(self, response_id: int, offer_id: int, channel_id: int, 
                         user_id: int, proposed_price: float) -> bool:
        """Событие принятия отклика"""
        event = create_event(
            EventType.RESPONSE_ACCEPTED,
            user_id=user_id,
            data={
                'response_id': response_id,
                'offer_id': offer_id,
                'channel_id': channel_id,
                'proposed_price': proposed_price
            }
        )
        
        return self.event_bus.publish(event)
    
    def response_rejected(self, response_id: int, offer_id: int, channel_id: int, 
                         user_id: int, reason: str = None) -> bool:
        """Событие отклонения отклика"""
        event = create_event(
            EventType.RESPONSE_REJECTED,
            user_id=user_id,
            data={
                'response_id': response_id,
                'offer_id': offer_id,
                'channel_id': channel_id,
                'reason': reason
            }
        )
        
        return self.event_bus.publish(event)
    
    # =================== РАЗМЕЩЕНИЯ ===================
    
    def placement_created(self, placement_id: int, response_id: int, 
                         offer_id: int, channel_id: int, user_id: int) -> bool:
        """Событие создания размещения"""
        event = create_event(
            EventType.PLACEMENT_CREATED,
            user_id=user_id,
            data={
                'placement_id': placement_id,
                'response_id': response_id,
                'offer_id': offer_id,
                'channel_id': channel_id
            }
        )
        
        return self.event_bus.publish(event)
    
    def placement_post_published(self, placement_id: int, post_url: str, 
                               user_id: int, **kwargs) -> bool:
        """Событие публикации рекламного поста"""
        event = create_event(
            EventType.PLACEMENT_POST_PUBLISHED,
            user_id=user_id,
            data={
                'placement_id': placement_id,
                'post_url': post_url,
                **kwargs
            }
        )
        
        return self.event_bus.publish(event)
    
    def placement_stats_updated(self, placement_id: int, views_count: int, 
                              clicks_count: int, engagement_rate: float, 
                              user_id: int) -> bool:
        """Событие обновления статистики размещения"""
        event = create_event(
            EventType.PLACEMENT_STATS_UPDATED,
            user_id=user_id,
            data={
                'placement_id': placement_id,
                'views_count': views_count,
                'clicks_count': clicks_count,
                'engagement_rate': engagement_rate
            }
        )
        
        return self.event_bus.publish(event)
    
    # =================== ПЛАТЕЖИ ===================
    
    def payment_created(self, payment_id: int, user_id: int, amount: float, 
                       payment_type: str, status: str = 'pending', **kwargs) -> bool:
        """Событие создания платежа"""
        event = create_event(
            EventType.PAYMENT_CREATED,
            user_id=user_id,
            data={
                'payment_id': payment_id,
                'amount': amount,
                'payment_type': payment_type,
                'status': status,
                **kwargs
            }
        )
        
        return self.event_bus.publish(event)
    
    def escrow_released(self, payment_id: int, user_id: int, amount: float, 
                       recipient_id: int, **kwargs) -> bool:
        """Событие освобождения средств из эскроу"""
        event = create_event(
            EventType.ESCROW_RELEASED,
            user_id=user_id,
            data={
                'payment_id': payment_id,
                'amount': amount,
                'recipient_id': recipient_id,
                **kwargs
            }
        )
        
        return self.event_bus.publish(event)
    
    # =================== БЕЗОПАСНОСТЬ ===================
    
    def security_suspicious_activity(self, user_id: int, action: str, 
                                   risk_level: str = 'medium', 
                                   details: Dict[str, Any] = None) -> bool:
        """Событие подозрительной активности"""
        context = self._get_current_context()
        
        event = create_event(
            EventType.SECURITY_SUSPICIOUS_ACTIVITY,
            user_id=user_id,
            data={
                'action': action,
                'risk_level': risk_level,
                'details': details or {},
                **context
            }
        )
        
        return self.event_bus.publish(event)
    
    def security_rate_limit_exceeded(self, user_id: int, limit_type: str, 
                                   current_count: int, limit: int) -> bool:
        """Событие превышения лимита запросов"""
        context = self._get_current_context()
        
        event = create_event(
            EventType.SECURITY_RATE_LIMIT_EXCEEDED,
            user_id=user_id,
            data={
                'limit_type': limit_type,
                'current_count': current_count,
                'limit': limit,
                **context
            }
        )
        
        return self.event_bus.publish(event)
    
    # =================== АНАЛИТИКА ===================
    
    def analytics_page_view(self, user_id: int, page_url: str, 
                          referrer: str = None, **kwargs) -> bool:
        """Событие просмотра страницы"""
        context = self._get_current_context()
        
        event = create_event(
            EventType.ANALYTICS_PAGE_VIEW,
            user_id=user_id,
            data={
                'page_url': page_url,
                'referrer': referrer,
                **kwargs,
                **context
            }
        )
        
        return self.event_bus.publish(event)
    
    def analytics_button_click(self, user_id: int, button_id: str, 
                             page_url: str = None, **kwargs) -> bool:
        """Событие клика по кнопке"""
        context = self._get_current_context()
        
        event = create_event(
            EventType.ANALYTICS_BUTTON_CLICK,
            user_id=user_id,
            data={
                'button_id': button_id,
                'page_url': page_url,
                **kwargs,
                **context
            }
        )
        
        return self.event_bus.publish(event)
    
    def analytics_conversion(self, user_id: int, conversion_type: str, 
                           value: float = None, **kwargs) -> bool:
        """Событие конверсии"""
        event = create_event(
            EventType.ANALYTICS_CONVERSION,
            user_id=user_id,
            data={
                'conversion_type': conversion_type,
                'value': value,
                **kwargs
            }
        )
        
        return self.event_bus.publish(event)
    
    # =================== СИСТЕМНЫЕ СОБЫТИЯ ===================
    
    def system_startup(self, version: str = None, environment: str = None) -> bool:
        """Событие запуска системы"""
        event = create_event(
            EventType.SYSTEM_STARTUP,
            data={
                'version': version,
                'environment': environment,
                'startup_time': datetime.utcnow().isoformat()
            }
        )
        
        return self.event_bus.publish(event)
    
    def system_error(self, error_type: str, error_message: str, 
                    user_id: int = None, **kwargs) -> bool:
        """Событие системной ошибки"""
        context = self._get_current_context()
        
        event = create_event(
            EventType.SYSTEM_ERROR,
            user_id=user_id,
            data={
                'error_type': error_type,
                'error_message': error_message,
                **kwargs,
                **context
            }
        )
        
        return self.event_bus.publish(event)

# Глобальный экземпляр диспетчера событий
event_dispatcher = EventDispatcher()

# Удобные функции для быстрого доступа
def dispatch_user_registered(user_id: int, telegram_id: int, **kwargs) -> bool:
    return event_dispatcher.user_registered(user_id, telegram_id, **kwargs)

def dispatch_offer_created(offer_id: int, advertiser_id: int, title: str, **kwargs) -> bool:
    return event_dispatcher.offer_created(offer_id, advertiser_id, title, **kwargs)

def dispatch_response_accepted(response_id: int, offer_id: int, channel_id: int, 
                             user_id: int, proposed_price: float) -> bool:
    return event_dispatcher.response_accepted(response_id, offer_id, channel_id, 
                                            user_id, proposed_price)

def dispatch_placement_post_published(placement_id: int, post_url: str, user_id: int) -> bool:
    return event_dispatcher.placement_post_published(placement_id, post_url, user_id)

def dispatch_security_suspicious_activity(user_id: int, action: str, 
                                         risk_level: str = 'medium') -> bool:
    return event_dispatcher.security_suspicious_activity(user_id, action, risk_level)