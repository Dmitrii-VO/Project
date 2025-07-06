# app/utils/notifications.py
"""
Полноценный сервис уведомлений для Telegram Mini App
Объединяет все функции уведомлений в одном файле
"""

import sqlite3
import logging
import requests
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
import os
import sys
from urllib.parse import quote

# Добавляем путь для импорта
sys.path.insert(0, os.getcwd())

logger = logging.getLogger(__name__)
DATABASE_PATH = 'telegram_mini_app.db'


class NotificationService:
    """Основной класс для работы с уведомлениями"""

    def __init__(self):
        self.bot_token = self._get_bot_token()
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}" if self.bot_token else None

    def _get_bot_token(self) -> Optional[str]:
        """Получение токена бота из конфигурации"""
        try:
            # Пробуем импортировать из конфигурации
            from app.config.telegram_config import AppConfig
            return AppConfig.BOT_TOKEN
        except:
            # Fallback на переменные окружения
            return os.environ.get('BOT_TOKEN')

    @staticmethod
    def send_telegram_notification(telegram_id: int, message: str, metadata: Dict[str, Any] = None) -> bool:
        """
        Отправка Telegram уведомления пользователю
        
        Args:
            telegram_id: ID пользователя в Telegram
            message: Текст сообщения
            metadata: Дополнительные данные
            
        Returns:
            bool: Успешность отправки
        """
        try:
            service = NotificationService()
            if not service.bot_token:
                logger.warning("BOT_TOKEN не настроен, уведомления не отправляются")
                return False

            # Отправляем сообщение
            url = f"{service.base_url}/sendMessage"
            data = {
                'chat_id': telegram_id,
                'text': message,
                'parse_mode': 'HTML',
                'disable_web_page_preview': True
            }

            response = requests.post(url, json=data, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('ok'):
                    logger.info(f"✅ Уведомление отправлено пользователю {telegram_id}")
                    
                    # Сохраняем в БД
                    service._save_notification_to_db(telegram_id, message, 'sent', metadata)
                    return True
                else:
                    logger.error(f"❌ Telegram API error: {result.get('description')}")
                    service._save_notification_to_db(telegram_id, message, 'failed', metadata)
                    return False
            else:
                logger.error(f"❌ HTTP error {response.status_code}")
                service._save_notification_to_db(telegram_id, message, 'failed', metadata)
                return False

        except Exception as e:
            logger.error(f"❌ Ошибка отправки уведомления: {e}")
            try:
                service._save_notification_to_db(telegram_id, message, 'error', metadata)
            except:
                pass
            return False

    def _save_notification_to_db(self, telegram_id: int, message: str, status: str, metadata: Dict[str, Any] = None):
        """Сохранение уведомления в базу данных"""
        try:
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()

            # Создаем таблицу уведомлений если не существует
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER NOT NULL,
                    message TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    metadata TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    sent_at DATETIME,
                    error_message TEXT
                )
            ''')

            # Вставляем уведомление
            cursor.execute('''
                INSERT INTO notifications (telegram_id, message, status, metadata, sent_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                telegram_id,
                message,
                status,
                json.dumps(metadata) if metadata else None,
                datetime.now().isoformat() if status == 'sent' else None
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"Ошибка сохранения уведомления в БД: {e}")

    @staticmethod
    def send_welcome_notification(user) -> bool:
        """Отправка приветственного уведомления новому пользователю"""
        try:
            welcome_message = f"""
🎉 <b>Добро пожаловать в платформу рекламы!</b>

Привет, {user.first_name or user.username or 'пользователь'}!

Вы успешно зарегистрировались. Теперь вы можете:
• Добавлять свои каналы для монетизации
• Создавать рекламные предложения  
• Зарабатывать на размещении рекламы

🎁 Ваш реферальный код: {getattr(user, 'referral_code', 'REF001')}
Приглашайте друзей и получайте бонусы!

Начните с добавления вашего первого канала 👇
            """

            return NotificationService.send_telegram_notification(
                user.telegram_id,
                welcome_message,
                {
                    'type': 'welcome',
                    'user_id': getattr(user, 'id', None),
                    'referral_code': getattr(user, 'referral_code', 'REF001')
                }
            )

        except Exception as e:
            logger.error(f"Ошибка отправки приветственного уведомления: {e}")
            return False

    @staticmethod
    def send_balance_notification(user, amount: float, transaction_type: str) -> bool:
        """Уведомление об изменении баланса"""
        try:
            if transaction_type == 'deposit':
                emoji = "💰"
                action = "пополнен"
            elif transaction_type == 'withdrawal':
                emoji = "💸"
                action = "списан"
            elif transaction_type == 'earning':
                emoji = "🎉"
                action = "начислен доход"
            else:
                emoji = "💳"
                action = "изменен"

            message = f"""
{emoji} <b>Баланс {action}</b>

Сумма: {abs(amount):,.2f} ₽
Текущий баланс: {getattr(user, 'balance', 0):,.2f} ₽

Все операции можно отслеживать в разделе "Платежи".
            """

            return NotificationService.send_telegram_notification(
                user.telegram_id,
                message,
                {
                    'type': 'balance_change',
                    'user_id': getattr(user, 'id', None),
                    'amount': amount,
                    'transaction_type': transaction_type
                }
            )

        except Exception as e:
            logger.error(f"Ошибка отправки уведомления о балансе: {e}")
            return False

    @staticmethod
    def send_offer_notification(user, offer, notification_type: str) -> bool:
        """Уведомления о офферах"""
        try:
            if notification_type == 'created':
                message = f"""
🚀 <b>Оффер создан!</b>

📢 <b>Название:</b> {offer.title}
💰 <b>Бюджет:</b> {getattr(offer, 'budget', 0)} ₽
🎯 <b>Целевая аудитория:</b> {getattr(offer, 'target_audience', 'Не указана')}

Ваш оффер опубликован и доступен владельцам каналов.
                """
            elif notification_type == 'new_response':
                message = f"""
📩 <b>Новый отклик на ваш оффер!</b>

📢 <b>Оффер:</b> {offer.title}
👤 <b>Канал:</b> {getattr(offer, 'channel_name', 'Неизвестный канал')}
💰 <b>Предложенная цена:</b> {getattr(offer, 'proposed_price', 0)} ₽

Проверьте детали в приложении.
                """
            else:
                message = f"📋 Обновление по офферу: {offer.title}"

            return NotificationService.send_telegram_notification(
                user.telegram_id,
                message,
                {
                    'type': f'offer_{notification_type}',
                    'offer_id': getattr(offer, 'id', None),
                    'user_id': getattr(user, 'id', None)
                }
            )

        except Exception as e:
            logger.error(f"Ошибка отправки уведомления об оффере: {e}")
            return False

    @staticmethod
    def send_channel_notification(user, channel, notification_type: str) -> bool:
        """Уведомления о каналах"""
        try:
            if notification_type == 'verified':
                message = f"""
✅ <b>Канал верифицирован!</b>

📺 <b>Канал:</b> {getattr(channel, 'title', 'Ваш канал')}
👥 <b>Подписчиков:</b> {getattr(channel, 'subscriber_count', 0):,}

Теперь вы можете получать предложения от рекламодателей!
                """
            elif notification_type == 'verification_failed':
                message = f"""
❌ <b>Верификация канала не пройдена</b>

📺 <b>Канал:</b> {getattr(channel, 'title', 'Ваш канал')}
📝 <b>Причина:</b> {getattr(channel, 'verification_error', 'Проверьте код верификации')}

Повторите процедуру верификации.
                """
            elif notification_type == 'new_offer':
                message = f"""
💎 <b>Новое предложение для вашего канала!</b>

📺 <b>Канал:</b> {getattr(channel, 'title', 'Ваш канал')}
💰 <b>Предложенная цена:</b> {getattr(channel, 'offer_price', 0)} ₽

Проверьте детали в приложении.
                """
            else:
                message = f"📋 Обновление канала: {getattr(channel, 'title', 'Ваш канал')}"

            return NotificationService.send_telegram_notification(
                user.telegram_id,
                message,
                {
                    'type': f'channel_{notification_type}',
                    'channel_id': getattr(channel, 'id', None),
                    'user_id': getattr(user, 'id', None)
                }
            )

        except Exception as e:
            logger.error(f"Ошибка отправки уведомления о канале: {e}")
            return False


# === ФУНКЦИИ ДЛЯ ОБРАТНОЙ СОВМЕСТИМОСТИ ===

def send_telegram_message(telegram_id: int, message: str, parse_mode: str = 'HTML') -> bool:
    """Отправка простого Telegram сообщения (для обратной совместимости)"""
    return NotificationService.send_telegram_notification(telegram_id, message)


# === ФУНКЦИИ ДЛЯ КОНТРАКТОВ (из существующего кода) ===

def send_contract_notification(contract_id, notification_type, extra_data=None):
    """Отправка уведомлений по контрактам"""
    try:
        bot_token = NotificationService()._get_bot_token()
        if not bot_token:
            logger.warning("BOT_TOKEN не настроен, уведомления не отправляются")
            return

        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Получаем информацию о контракте
        cursor.execute('''
            SELECT c.*,
                   o.title as offer_title,
                   u_adv.telegram_id as advertiser_telegram_id,
                   u_adv.first_name as advertiser_name,
                   u_pub.telegram_id as publisher_telegram_id,
                   u_pub.first_name as publisher_name,
                   or_resp.channel_title
            FROM contracts c
            JOIN offers o ON c.offer_id = o.id
            JOIN users u_adv ON c.advertiser_id = u_adv.id  
            JOIN users u_pub ON c.publisher_id = u_pub.id
            JOIN offer_responses or_resp ON c.response_id = or_resp.id
            WHERE c.id = ?
        ''', (contract_id,))

        data = cursor.fetchone()
        conn.close()

        if not data:
            return

        def format_date(date_str):
            """Форматирование даты"""
            try:
                if date_str:
                    dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    return dt.strftime('%d.%m.%Y %H:%M')
                return 'Не указано'
            except:
                return str(date_str)

        if notification_type == 'created':
            # Уведомления о создании контракта
            advertiser_msg = f"""📋 <b>Контракт создан!</b>

🎯 <b>Оффер:</b> {data['offer_title']}
💰 <b>Сумма:</b> {data['price']} RUB
📺 <b>Канал:</b> {data['channel_title']}
👤 <b>Издатель:</b> {data['publisher_name']}

⏰ <b>Срок размещения:</b> {format_date(data['placement_deadline'])}
🔍 <b>Срок мониторинга:</b> {data['monitoring_duration']} дней

📱 Издатель должен разместить рекламу и подать заявку в приложении."""

            publisher_msg = f"""✅ <b>Ваш отклик принят! Контракт создан.</b>

🎯 <b>Оффер:</b> {data['offer_title']}
💰 <b>Оплата:</b> {data['price']} RUB
👤 <b>Рекламодатель:</b> {data['advertiser_name']}

⏰ <b>Разместите рекламу до:</b> {format_date(data['placement_deadline'])}

📝 <b>Что делать дальше:</b>
1. Разместите рекламу в своем канале
2. Подайте заявку с ссылкой на пост в приложении
3. После проверки начнется мониторинг
4. Оплата будет произведена автоматически после завершения мониторинга."""

            NotificationService.send_telegram_notification(data['advertiser_telegram_id'], advertiser_msg)
            NotificationService.send_telegram_notification(data['publisher_telegram_id'], publisher_msg)

        elif notification_type == 'placement_verified':
            # Уведомления о проверке размещения
            verification_passed = extra_data.get('verified', False) if extra_data else False

            if verification_passed:
                adv_msg = f"""✅ <b>Размещение проверено и подтверждено!</b>

🎯 <b>Оффер:</b> {data['offer_title']}
📺 <b>Канал:</b> {data['channel_title']}

🔍 Начат мониторинг на {data['monitoring_duration']} дней.
Оплата будет произведена автоматически после завершения мониторинга."""

                pub_msg = f"""✅ <b>Размещение проверено и подтверждено!</b>

🎯 <b>Оффер:</b> {data['offer_title']}
💰 <b>К оплате:</b> {data['price']} RUB

🔍 Начат мониторинг на {data['monitoring_duration']} дней.
Не удаляйте пост до завершения мониторинга!"""
            else:
                error_msg = extra_data.get('message') if extra_data else 'Размещение не соответствует требованиям'

                pub_msg = f"""❌ <b>Проверка не пройдена</b>

🎯 <b>Оффер:</b> {data['offer_title']}
❌ <b>Причина:</b> {error_msg}

🔄 Исправьте размещение и подайте заявку повторно."""

                adv_msg = f"""❌ <b>Проверка размещения не пройдена</b>

🎯 <b>Оффер:</b> {data['offer_title']}
📺 <b>Канал:</b> {data['channel_title']}
❌ <b>Причина:</b> {error_msg}

Издатель должен исправить размещение."""

            NotificationService.send_telegram_notification(data['advertiser_telegram_id'], adv_msg)
            NotificationService.send_telegram_notification(data['publisher_telegram_id'], pub_msg)

        elif notification_type == 'completed':
            # Уведомления о завершении контракта
            payment_id = extra_data.get('payment_id') if extra_data else 'N/A'
            amount = extra_data.get('amount') if extra_data else data['price']

            adv_msg = f"""✅ <b>Контракт завершен!</b>

🎯 <b>Оффер:</b> {data['offer_title']}
📺 <b>Канал:</b> {data['channel_title']}
💰 <b>Сумма:</b> {amount} RUB

✅ Мониторинг завершен успешно.
💳 Платеж #{payment_id} обрабатывается."""

            pub_msg = f"""🎉 <b>Поздравляем! Контракт выполнен.</b>

🎯 <b>Оффер:</b> {data['offer_title']}
💰 <b>Заработано:</b> {amount} RUB

💳 Платеж #{payment_id} поступит на ваш счет в течение 24 часов.
Спасибо за качественную работу!"""

            NotificationService.send_telegram_notification(data['advertiser_telegram_id'], adv_msg)
            NotificationService.send_telegram_notification(data['publisher_telegram_id'], pub_msg)

        elif notification_type == 'violation':
            # Уведомления о нарушении
            reason = extra_data.get('reason') if extra_data else 'Нарушение условий контракта'

            pub_msg = f"""⚠️ <b>Обнаружено нарушение!</b>

🎯 <b>Оффер:</b> {data['offer_title']}
❌ <b>Проблема:</b> {reason}

🔄 Пожалуйста, восстановите размещение или свяжитесь с поддержкой."""

            adv_msg = f"""⚠️ <b>Нарушение контракта</b>

🎯 <b>Оффер:</b> {data['offer_title']}
📺 <b>Канал:</b> {data['channel_title']}
❌ <b>Проблема:</b> {reason}

Мы уведомили издателя о необходимости исправления."""

            NotificationService.send_telegram_notification(data['advertiser_telegram_id'], adv_msg)
            NotificationService.send_telegram_notification(data['publisher_telegram_id'], pub_msg)

    except Exception as e:
        logger.error(f"Ошибка отправки уведомления по контракту: {e}")


# === ЭКСПОРТ ===
__all__ = [
    'NotificationService',
    'send_telegram_message', 
    'send_contract_notification'
]