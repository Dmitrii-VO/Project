#!/usr/bin/env python3
"""
Event Handlers для Telegram Mini App
Обработчики различных типов событий
"""

import logging
from typing import Dict, Any
from datetime import datetime, timedelta

from .event_bus import event_handler, global_event_handler
from .event_types import (
    EventType, BaseEvent, UserEvent, ChannelEvent, OfferEvent, 
    ResponseEvent, PlacementEvent, PaymentEvent, NotificationEvent,
    SecurityEvent, AnalyticsEvent
)

logger = logging.getLogger(__name__)

# =================== ОБРАБОТЧИКИ ПОЛЬЗОВАТЕЛЕЙ ===================

@event_handler(EventType.USER_REGISTERED, priority=10)
def handle_user_registered(event: UserEvent):
    """Обработка регистрации нового пользователя"""
    try:
        from app.telegram.telegram_notifications import TelegramNotificationService
        from app.events.event_bus import event_bus
        from app.events.event_types import create_event
        
        notification_service = TelegramNotificationService()
        
        # Отправляем приветственное сообщение
        welcome_message = f"""
🎉 Добро пожаловать в Telegram Mini App!

Привет, {event.data.get('first_name', 'пользователь')}!

Теперь вы можете:
• 📢 Добавлять свои каналы для монетизации
• 🎯 Создавать рекламные кампании
• 💰 Зарабатывать на размещении рекламы
• 📊 Отслеживать статистику и доходы

Начните с добавления ваших каналов в разделе "Мои каналы".
        """
        
        notification_service.send_notification(
            user_id=event.telegram_id,
            message=welcome_message,
            notification_type='welcome'
        )
        
        # Начисляем приветственный бонус
        welcome_bonus = 50.0
        bonus_event = create_event(
            EventType.USER_BALANCE_CHANGED,
            user_id=event.user_id,
            telegram_id=event.telegram_id,
            data={
                'old_balance': 0.0,
                'new_balance': welcome_bonus,
                'change_amount': welcome_bonus,
                'change_type': 'welcome_bonus',
                'description': 'Приветственный бонус за регистрацию'
            }
        )
        event_bus.publish(bonus_event)
        
        logger.info(f"✅ Обработана регистрация пользователя {event.telegram_id}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка обработки регистрации пользователя: {e}")

@event_handler(EventType.USER_BALANCE_CHANGED, priority=8)
def handle_balance_changed(event: UserEvent):
    """Обработка изменения баланса пользователя"""
    try:
        from app.models.database import execute_db_query
        
        # Обновляем баланс в базе данных
        execute_db_query(
            "UPDATE users SET balance = ?, updated_at = ? WHERE telegram_id = ?",
            (event.data['new_balance'], datetime.now(), event.telegram_id)
        )
        
        # Уведомляем пользователя о значительных изменениях
        change_amount = abs(event.data.get('change_amount', 0))
        if change_amount >= 100:  # Уведомляем о изменениях от 100 руб
            from app.telegram.telegram_notifications import TelegramNotificationService
            
            notification_service = TelegramNotificationService()
            change_type = event.data.get('change_type', 'unknown')
            
            if change_amount > 0:
                emoji = "💰"
                action = "пополнен"
            else:
                emoji = "💸"
                action = "списан"
            
            message = f"""
{emoji} <b>Изменение баланса</b>

Ваш баланс {action} на {change_amount:.2f} руб.
Текущий баланс: {event.data['new_balance']:.2f} руб.

Причина: {event.data.get('description', change_type)}
            """
            
            notification_service.send_notification(
                user_id=event.telegram_id,
                message=message,
                notification_type='balance_change'
            )
        
        logger.info(f"✅ Обработано изменение баланса пользователя {event.telegram_id}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка обработки изменения баланса: {e}")

# =================== ОБРАБОТЧИКИ КАНАЛОВ ===================

@event_handler(EventType.CHANNEL_VERIFIED, priority=9)
def handle_channel_verified(event: ChannelEvent):
    """Обработка верификации канала"""
    try:
        from app.telegram.telegram_notifications import TelegramNotificationService
        
        notification_service = TelegramNotificationService()
        
        message = f"""
✅ <b>Канал верифицирован!</b>

📢 <b>Канал:</b> {event.channel_title}
🎉 <b>Поздравляем!</b> Ваш канал успешно прошел верификацию.

Теперь вы можете:
• Получать предложения о размещении рекламы
• Устанавливать цены за посты
• Зарабатывать на рекламных размещениях

Следите за входящими предложениями в разделе "Мои предложения".
        """
        
        notification_service.send_notification(
            user_id=event.user_id,
            message=message,
            notification_type='channel_verified'
        )
        
        logger.info(f"✅ Обработана верификация канала {event.channel_id}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка обработки верификации канала: {e}")

# =================== ОБРАБОТЧИКИ ОФФЕРОВ ===================

@event_handler(EventType.OFFER_CREATED, priority=9)
def handle_offer_created(event: OfferEvent):
    """Обработка создания нового оффера"""
    try:
        from app.models.database import execute_db_query
        from app.events.event_bus import event_bus
        from app.events.event_types import create_event
        
        # Ищем подходящие каналы для автоматического матчинга
        matching_channels = execute_db_query("""
            SELECT c.id, c.title, c.owner_id, u.telegram_id
            FROM channels c
            JOIN users u ON c.owner_id = u.id
            WHERE c.is_verified = 1 
            AND c.is_active = 1
            AND c.category = ?
            AND c.price_per_post <= ?
            ORDER BY c.subscriber_count DESC
            LIMIT 10
        """, (
            event.data.get('category', 'other'),
            event.budget or 10000
        ))
        
        # Отправляем уведомления владельцам подходящих каналов
        for channel in matching_channels:
            try:
                from app.telegram.telegram_notifications import TelegramNotificationService
                notification_service = TelegramNotificationService()
                
                message = f"""
🎯 <b>Новое предложение о рекламе!</b>

📋 <b>Оффер:</b> {event.offer_title}
💰 <b>Бюджет:</b> {event.budget:.2f} руб.
📢 <b>Ваш канал:</b> {channel['title']}

Рассмотрите это предложение в веб-приложении и отправьте свой отклик.
                """
                
                notification_service.send_notification(
                    user_id=channel['telegram_id'],
                    message=message,
                    notification_type='new_offer_match'
                )
                
            except Exception as e:
                logger.error(f"Ошибка уведомления владельца канала {channel['id']}: {e}")
        
        logger.info(f"✅ Обработано создание оффера {event.offer_id}, найдено {len(matching_channels)} подходящих каналов")
        
    except Exception as e:
        logger.error(f"❌ Ошибка обработки создания оффера: {e}")

# =================== ОБРАБОТЧИКИ ОТКЛИКОВ ===================

@event_handler(EventType.RESPONSE_CREATED, priority=9)
def handle_response_created(event: ResponseEvent):
    """Обработка создания отклика на оффер"""
    try:
        from app.models.database import execute_db_query
        from app.telegram.telegram_notifications import TelegramNotificationService
        
        # Получаем данные оффера и рекламодателя
        offer_data = execute_db_query("""
            SELECT o.title, o.created_by, u.telegram_id, u.first_name
            FROM offers o
            JOIN users u ON o.created_by = u.id
            WHERE o.id = ?
        """, (event.offer_id,), fetch_one=True)
        
        # Получаем данные канала
        channel_data = execute_db_query("""
            SELECT c.title, c.username
            FROM channels c
            WHERE c.id = ?
        """, (event.channel_id,), fetch_one=True)
        
        if offer_data and channel_data:
            notification_service = TelegramNotificationService()
            
            message = f"""
📨 <b>Новый отклик на ваш оффер!</b>

📋 <b>Оффер:</b> {offer_data['title']}
📢 <b>Канал:</b> {channel_data['title']}
💰 <b>Предложенная цена:</b> {event.proposed_price:.2f} руб.

📝 <b>Сообщение:</b>
{event.data.get('response_message', 'Без комментариев')}

Рассмотрите предложение в веб-приложении.
            """
            
            notification_service.send_notification(
                user_id=offer_data['telegram_id'],
                message=message,
                notification_type='new_response'
            )
        
        logger.info(f"✅ Обработан отклик {event.response_id} на оффер {event.offer_id}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка обработки создания отклика: {e}")

@event_handler(EventType.RESPONSE_ACCEPTED, priority=9)
def handle_response_accepted(event: ResponseEvent):
    """Обработка принятия отклика"""
    try:
        from app.models.database import execute_db_query
        from app.telegram.telegram_notifications import TelegramNotificationService
        from app.events.event_bus import event_bus
        from app.events.event_types import create_event
        
        # Получаем данные для уведомления
        response_data = execute_db_query("""
            SELECT r.*, o.title as offer_title, c.title as channel_title,
                   ch_owner.telegram_id as channel_owner_telegram_id,
                   advertiser.telegram_id as advertiser_telegram_id
            FROM offer_responses r
            JOIN offers o ON r.offer_id = o.id
            JOIN channels c ON r.channel_id = c.id
            JOIN users ch_owner ON c.owner_id = ch_owner.id
            JOIN users advertiser ON o.created_by = advertiser.id
            WHERE r.id = ?
        """, (event.response_id,), fetch_one=True)
        
        if response_data:
            notification_service = TelegramNotificationService()
            
            # Уведомляем владельца канала
            channel_message = f"""
🎉 <b>Ваш отклик принят!</b>

📋 <b>Оффер:</b> {response_data['offer_title']}
📢 <b>Канал:</b> {response_data['channel_title']}
💰 <b>Сумма:</b> {event.proposed_price:.2f} руб.

Теперь вам нужно:
1. Разместить рекламный пост в канале
2. Подтвердить размещение командой /post_published <ссылка_на_пост>

После подтверждения средства будут зарезервированы для выплаты.
            """
            
            notification_service.send_notification(
                user_id=response_data['channel_owner_telegram_id'],
                message=channel_message,
                notification_type='response_accepted'
            )
            
            # Создаем событие размещения
            placement_event = create_event(
                EventType.PLACEMENT_CREATED,
                user_id=event.user_id,
                data={
                    'response_id': event.response_id,
                    'offer_id': event.offer_id,
                    'channel_id': event.channel_id,
                    'amount': event.proposed_price
                }
            )
            event_bus.publish(placement_event)
        
        logger.info(f"✅ Обработано принятие отклика {event.response_id}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка обработки принятия отклика: {e}")

# =================== ОБРАБОТЧИКИ РАЗМЕЩЕНИЙ ===================

@event_handler(EventType.PLACEMENT_POST_PUBLISHED, priority=9)
def handle_post_published(event: PlacementEvent):
    """Обработка публикации рекламного поста"""
    try:
        from app.models.database import execute_db_query
        from app.events.event_bus import event_bus
        from app.events.event_types import create_event
        
        # Создаем платеж в эскроу
        placement_data = execute_db_query("""
            SELECT p.*, r.proposed_price, r.offer_id, 
                   c.owner_id, o.created_by as advertiser_id
            FROM offer_placements p
            JOIN offer_responses r ON p.response_id = r.id
            JOIN channels c ON r.channel_id = c.id
            JOIN offers o ON r.offer_id = o.id
            WHERE p.id = ?
        """, (event.placement_id,), fetch_one=True)
        
        if placement_data:
            # Резервируем средства в эскроу
            escrow_event = create_event(
                EventType.PAYMENT_CREATED,
                user_id=placement_data['advertiser_id'],
                data={
                    'placement_id': event.placement_id,
                    'amount': placement_data['proposed_price'],
                    'payment_type': 'escrow',
                    'recipient_id': placement_data['owner_id'],
                    'description': f'Эскроу для размещения в канале'
                }
            )
            event_bus.publish(escrow_event)
            
            # Запускаем отслеживание статистики
            # (здесь можно добавить интеграцию с Telegram Analytics API)
        
        logger.info(f"✅ Обработана публикация поста для размещения {event.placement_id}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка обработки публикации поста: {e}")

# =================== ОБРАБОТЧИКИ ПЛАТЕЖЕЙ ===================

@event_handler(EventType.ESCROW_RELEASED, priority=9)
def handle_escrow_released(event: PaymentEvent):
    """Обработка освобождения средств из эскроу"""
    try:
        from app.telegram.telegram_notifications import TelegramNotificationService
        from app.models.database import execute_db_query
        
        # Получаем данные о платеже
        payment_data = execute_db_query("""
            SELECT p.*, u.telegram_id, u.first_name
            FROM payments p
            JOIN users u ON p.user_id = u.id
            WHERE p.id = ?
        """, (event.payment_id,), fetch_one=True)
        
        if payment_data:
            notification_service = TelegramNotificationService()
            
            message = f"""
💰 <b>Выплата получена!</b>

Сумма: {event.amount:.2f} руб.
Статус: Завершено ✅

Средства зачислены на ваш баланс.
Спасибо за работу с нашей платформой!
            """
            
            notification_service.send_notification(
                user_id=payment_data['telegram_id'],
                message=message,
                notification_type='payment_received'
            )
        
        logger.info(f"✅ Обработано освобождение эскроу {event.payment_id}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка обработки освобождения эскроу: {e}")

# =================== ОБРАБОТЧИКИ БЕЗОПАСНОСТИ ===================

@event_handler(EventType.SECURITY_SUSPICIOUS_ACTIVITY, priority=10)
def handle_suspicious_activity(event: SecurityEvent):
    """Обработка подозрительной активности"""
    try:
        from app.telegram.telegram_notifications import TelegramNotificationService
        from app.config.telegram_config import AppConfig
        
        # Уведомляем администраторов
        if event.risk_level in ['high', 'critical']:
            notification_service = TelegramNotificationService()
            
            admin_message = f"""
🚨 <b>Подозрительная активность!</b>

Пользователь: {event.user_id}
Уровень риска: {event.risk_level}
Действие: {event.action}
IP: {event.ip_address}
Время: {event.timestamp.strftime('%Y-%m-%d %H:%M:%S')}

Детали: {event.data}
            """
            
            # Отправляем админу
            notification_service.send_notification(
                user_id=AppConfig.YOUR_TELEGRAM_ID,
                message=admin_message,
                notification_type='security_alert'
            )
        
        logger.warning(f"⚠️ Подозрительная активность: {event.action} от пользователя {event.user_id}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка обработки подозрительной активности: {e}")

# =================== ГЛОБАЛЬНЫЕ ОБРАБОТЧИКИ ===================

@global_event_handler(priority=1)
def global_analytics_handler(event: BaseEvent):
    """Глобальный обработчик для аналитики"""
    try:
        # Собираем метрики для всех событий
        from app.performance.monitoring import PerformanceMonitor
        
        monitor = PerformanceMonitor()
        monitor.record_event_metric(
            event_type=event.event_type.value,
            user_id=event.user_id,
            timestamp=event.timestamp
        )
        
    except Exception as e:
        logger.error(f"❌ Ошибка в глобальном аналитическом обработчике: {e}")

@global_event_handler(priority=0)
def global_debug_handler(event: BaseEvent):
    """Глобальный обработчик для отладки (только в DEBUG режиме)"""
    try:
        from app.config.telegram_config import AppConfig
        
        if AppConfig.DEBUG:
            logger.debug(f"🔍 EVENT DEBUG: {event.event_type.value} | User: {event.user_id} | Data: {event.data}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка в глобальном отладочном обработчике: {e}")