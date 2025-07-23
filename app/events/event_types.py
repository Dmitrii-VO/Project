#!/usr/bin/env python3
"""
Event Types для Telegram Mini App
Определяет все типы событий в системе
"""

from enum import Enum
from dataclasses import dataclass
from typing import Any, Dict, Optional
from datetime import datetime

class EventType(Enum):
    """Типы событий в системе"""
    
    # Пользователи
    USER_REGISTERED = "user.registered"
    USER_UPDATED = "user.updated"
    USER_BALANCE_CHANGED = "user.balance_changed"
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    
    # Каналы
    CHANNEL_CREATED = "channel.created"
    CHANNEL_UPDATED = "channel.updated"
    CHANNEL_VERIFIED = "channel.verified"
    CHANNEL_DEACTIVATED = "channel.deactivated"
    CHANNEL_STATS_UPDATED = "channel.stats_updated"
    
    # Офферы
    OFFER_CREATED = "offer.created"
    OFFER_UPDATED = "offer.updated"
    OFFER_STATUS_CHANGED = "offer.status_changed"
    OFFER_EXPIRED = "offer.expired"
    OFFER_BUDGET_UPDATED = "offer.budget_updated"
    
    # Отклики на офферы
    RESPONSE_CREATED = "response.created"
    RESPONSE_STATUS_CHANGED = "response.status_changed"
    RESPONSE_ACCEPTED = "response.accepted"
    RESPONSE_REJECTED = "response.rejected"
    RESPONSE_COUNTER_OFFERED = "response.counter_offered"
    
    # Размещения
    PLACEMENT_CREATED = "placement.created"
    PLACEMENT_STARTED = "placement.started"
    PLACEMENT_COMPLETED = "placement.completed"
    PLACEMENT_STATS_UPDATED = "placement.stats_updated"
    PLACEMENT_POST_PUBLISHED = "placement.post_published"
    
    # Платежи
    PAYMENT_CREATED = "payment.created"
    PAYMENT_PROCESSED = "payment.processed"
    PAYMENT_FAILED = "payment.failed"
    PAYMENT_REFUNDED = "payment.refunded"
    ESCROW_RELEASED = "escrow.released"
    
    # Уведомления
    NOTIFICATION_SENT = "notification.sent"
    NOTIFICATION_READ = "notification.read"
    NOTIFICATION_FAILED = "notification.failed"
    
    # Система
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_ERROR = "system.error"
    SYSTEM_MAINTENANCE = "system.maintenance"
    
    # Безопасность
    SECURITY_LOGIN_ATTEMPT = "security.login_attempt"
    SECURITY_SUSPICIOUS_ACTIVITY = "security.suspicious_activity"
    SECURITY_RATE_LIMIT_EXCEEDED = "security.rate_limit_exceeded"
    SECURITY_UNAUTHORIZED_ACCESS = "security.unauthorized_access"
    
    # Аналитика
    ANALYTICS_PAGE_VIEW = "analytics.page_view"
    ANALYTICS_BUTTON_CLICK = "analytics.button_click"
    ANALYTICS_CONVERSION = "analytics.conversion"
    ANALYTICS_SESSION_START = "analytics.session_start"
    ANALYTICS_SESSION_END = "analytics.session_end"

@dataclass
class BaseEvent:
    """Базовый класс события"""
    event_type: EventType
    event_id: str
    timestamp: datetime
    user_id: Optional[int] = None
    session_id: Optional[str] = None
    source: str = "telegram_mini_app"
    data: Dict[str, Any] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.data is None:
            self.data = {}
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертация события в словарь"""
        return {
            'event_type': self.event_type.value,
            'event_id': self.event_id,
            'timestamp': self.timestamp.isoformat(),
            'user_id': self.user_id,
            'session_id': self.session_id,
            'source': self.source,
            'data': self.data,
            'metadata': self.metadata
        }

# Специализированные события

@dataclass
class UserEvent(BaseEvent):
    """События пользователей"""
    telegram_id: int = None
    username: str = None
    
@dataclass  
class ChannelEvent(BaseEvent):
    """События каналов"""
    channel_id: int = None
    channel_title: str = None
    owner_id: int = None

@dataclass
class OfferEvent(BaseEvent):
    """События офферов"""
    offer_id: int = None
    offer_title: str = None
    advertiser_id: int = None
    status: str = None
    budget: float = None

@dataclass
class ResponseEvent(BaseEvent):
    """События откликов"""
    response_id: int = None
    offer_id: int = None
    channel_id: int = None
    status: str = None
    proposed_price: float = None

@dataclass
class PlacementEvent(BaseEvent):
    """События размещений"""
    placement_id: int = None
    response_id: int = None
    offer_id: int = None
    channel_id: int = None
    status: str = None
    post_url: str = None

@dataclass
class PaymentEvent(BaseEvent):
    """События платежей"""
    payment_id: int = None
    amount: float = None
    payment_type: str = None
    status: str = None
    offer_id: int = None

@dataclass
class NotificationEvent(BaseEvent):
    """События уведомлений"""
    notification_id: int = None
    recipient_id: int = None
    notification_type: str = None
    title: str = None
    message: str = None

@dataclass
class SecurityEvent(BaseEvent):
    """События безопасности"""
    risk_level: str = "low"
    ip_address: str = None
    user_agent: str = None
    action: str = None
    resource: str = None

@dataclass
class AnalyticsEvent(BaseEvent):
    """События аналитики"""
    page_url: str = None
    referrer: str = None
    user_agent: str = None
    ip_address: str = None
    additional_data: Dict[str, Any] = None

# Маппинг типов событий на классы
EVENT_CLASS_MAPPING = {
    # Пользователи
    EventType.USER_REGISTERED: UserEvent,
    EventType.USER_UPDATED: UserEvent,
    EventType.USER_BALANCE_CHANGED: UserEvent,
    EventType.USER_LOGIN: UserEvent,
    EventType.USER_LOGOUT: UserEvent,
    
    # Каналы
    EventType.CHANNEL_CREATED: ChannelEvent,
    EventType.CHANNEL_UPDATED: ChannelEvent,
    EventType.CHANNEL_VERIFIED: ChannelEvent,
    EventType.CHANNEL_DEACTIVATED: ChannelEvent,
    EventType.CHANNEL_STATS_UPDATED: ChannelEvent,
    
    # Офферы
    EventType.OFFER_CREATED: OfferEvent,
    EventType.OFFER_UPDATED: OfferEvent,
    EventType.OFFER_STATUS_CHANGED: OfferEvent,
    EventType.OFFER_EXPIRED: OfferEvent,
    EventType.OFFER_BUDGET_UPDATED: OfferEvent,
    
    # Отклики
    EventType.RESPONSE_CREATED: ResponseEvent,
    EventType.RESPONSE_STATUS_CHANGED: ResponseEvent,
    EventType.RESPONSE_ACCEPTED: ResponseEvent,
    EventType.RESPONSE_REJECTED: ResponseEvent,
    EventType.RESPONSE_COUNTER_OFFERED: ResponseEvent,
    
    # Размещения
    EventType.PLACEMENT_CREATED: PlacementEvent,
    EventType.PLACEMENT_STARTED: PlacementEvent,
    EventType.PLACEMENT_COMPLETED: PlacementEvent,
    EventType.PLACEMENT_STATS_UPDATED: PlacementEvent,
    EventType.PLACEMENT_POST_PUBLISHED: PlacementEvent,
    
    # Платежи
    EventType.PAYMENT_CREATED: PaymentEvent,
    EventType.PAYMENT_PROCESSED: PaymentEvent,
    EventType.PAYMENT_FAILED: PaymentEvent,
    EventType.PAYMENT_REFUNDED: PaymentEvent,
    EventType.ESCROW_RELEASED: PaymentEvent,
    
    # Уведомления
    EventType.NOTIFICATION_SENT: NotificationEvent,
    EventType.NOTIFICATION_READ: NotificationEvent,
    EventType.NOTIFICATION_FAILED: NotificationEvent,
    
    # Безопасность
    EventType.SECURITY_LOGIN_ATTEMPT: SecurityEvent,
    EventType.SECURITY_SUSPICIOUS_ACTIVITY: SecurityEvent,
    EventType.SECURITY_RATE_LIMIT_EXCEEDED: SecurityEvent,
    EventType.SECURITY_UNAUTHORIZED_ACCESS: SecurityEvent,
    
    # Аналитика
    EventType.ANALYTICS_PAGE_VIEW: AnalyticsEvent,
    EventType.ANALYTICS_BUTTON_CLICK: AnalyticsEvent,
    EventType.ANALYTICS_CONVERSION: AnalyticsEvent,
    EventType.ANALYTICS_SESSION_START: AnalyticsEvent,
    EventType.ANALYTICS_SESSION_END: AnalyticsEvent,
}

def create_event(event_type: EventType, **kwargs) -> BaseEvent:
    """Фабрика для создания событий"""
    event_class = EVENT_CLASS_MAPPING.get(event_type, BaseEvent)
    
    # Добавляем обязательные поля
    if 'event_id' not in kwargs:
        import uuid
        kwargs['event_id'] = str(uuid.uuid4())
    
    if 'timestamp' not in kwargs:
        kwargs['timestamp'] = datetime.utcnow()
        
    kwargs['event_type'] = event_type
    
    return event_class(**kwargs)