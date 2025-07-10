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
from app.config.telegram_config import AppConfig

# Добавляем путь для импорта
sys.path.insert(0, os.getcwd())

logger = logging.getLogger(__name__)

DATABASE_PATH = AppConfig.DATABASE_PATH


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
                service = NotificationService()
                service._save_notification_to_db(telegram_id, message, 'error', metadata)
            except:
                pass
            return False

    def _save_notification_to_db(self, telegram_id: int, message: str, status: str, metadata: Dict[str, Any] = None):
        """Сохранение уведомления в базу данных"""
        try:
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()

            # Получаем user_id по telegram_id (используем существующую структуру БД)
            cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (telegram_id,))
            user_row = cursor.fetchone()
            
            if not user_row:
                logger.warning(f"⚠️ Пользователь с telegram_id {telegram_id} не найден в БД")
                conn.close()
                return

            user_id = user_row[0]

            # Определяем тип уведомления на основе metadata
            notification_type = 'system'  # ✅ Разрешенный тип
            if metadata:
                notification_type_from_meta = metadata.get('type', 'system')
                # Маппинг на разрешенные типы
                type_mapping = {
                    'welcome': 'system',
                    'telegram_notification': 'system',
                    'balance_change': 'payment_received',
                    'offer_created': 'offer_received',
                    'offer_new_response': 'offer_received',
                    'channel_verified': 'channel_verified',
                    'channel_verification_failed': 'system',
                    'channel_new_offer': 'offer_received'
                }
                notification_type = type_mapping.get(notification_type_from_meta, 'system')

            # Вставляем в существующую таблицу notifications
            # Структура: id, user_id, type, title, message, data, priority, is_read, created_at
            cursor.execute('''
                INSERT INTO notifications (user_id, type, title, message, data, priority, is_read)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                notification_type,
                'Уведомление от бота',
                message,
                json.dumps(metadata) if metadata else None,
                1,  # Обычный приоритет
                0   # Непрочитанное
            ))

            conn.commit()
            conn.close()
            logger.info(f"✅ Уведомление сохранено в БД для user_id: {user_id}")

        except Exception as e:
            logger.error(f"❌ Ошибка сохранения уведомления в БД: {e}")
            if 'conn' in locals():
                conn.close()

    @staticmethod
    def send_welcome_notification(user) -> bool:
        """Отправка приветственного уведомления новому пользователю"""
        try:
            if isinstance(user, dict):
                telegram_id = user.get('telegram_id')
                first_name = user.get('first_name', '')
                last_name = user.get('last_name', '')
                username = user.get('username', '')
                referral_code = user.get('referral_code', 'REF001')
            else:
                telegram_id = getattr(user, 'telegram_id', None)
                first_name = getattr(user, 'first_name', '')
                last_name = getattr(user, 'last_name', '')
                username = getattr(user, 'username', '')
                referral_code = getattr(user, 'referral_code', 'REF001')

            # Формируем полное имя
            full_name = []
            if first_name:
                full_name.append(first_name)
            if last_name:
                full_name.append(last_name)
            
            display_name = ' '.join(full_name) if full_name else username or 'пользователь'

            welcome_message = f"""
    🎉 <b>Добро пожаловать в платформу рекламы!</b>

    Привет, {display_name}!

    Вы успешно зарегистрировались. Теперь вы можете:
    - Добавлять свои каналы для монетизации
    - Создавать рекламные предложения  
    - Зарабатывать на размещении рекламы

    🎁 Ваш реферальный код: {referral_code}
    Приглашайте друзей и получайте бонусы!

    Начните с добавления вашего первого канала 👇
            """

            return NotificationService.send_telegram_notification(
                telegram_id,
                welcome_message,
                {
                    'type': 'welcome',
                    'user_id': user.get('id') if isinstance(user, dict) else getattr(user, 'id', None),
                    'referral_code': referral_code
                }
            )

        except Exception as e:
            logger.error(f"Ошибка отправки приветственного уведомления: {e}")
            return False

    @staticmethod
    def send_balance_notification(user, amount: float, transaction_type: str) -> bool:
        """Уведомление об изменении баланса"""
        try:
            # Получаем telegram_id - поддерживаем как объект, так и dict
            if hasattr(user, 'telegram_id'):
                telegram_id = user.telegram_id
                balance = getattr(user, 'balance', 0)
                user_id = getattr(user, 'id', None)
            elif isinstance(user, dict):
                telegram_id = user.get('telegram_id')
                balance = user.get('balance', 0)
                user_id = user.get('id')
            else:
                return False

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
Текущий баланс: {balance:,.2f} ₽

Все операции можно отслеживать в разделе "Платежи".
            """

            return NotificationService.send_telegram_notification(
                telegram_id,
                message,
                {
                    'type': 'balance_change',
                    'user_id': user_id,
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
            # Получаем telegram_id - поддерживаем как объект, так и dict
            if hasattr(user, 'telegram_id'):
                telegram_id = user.telegram_id
                user_id = getattr(user, 'id', None)
            elif isinstance(user, dict):
                telegram_id = user.get('telegram_id')
                user_id = user.get('id')
            else:
                return False

            if notification_type == 'created':
                message = f"""
🚀 <b>Оффер создан!</b>

📢 <b>Название:</b> {getattr(offer, 'title', 'Без названия')}
💰 <b>Бюджет:</b> {getattr(offer, 'budget', getattr(offer, 'price', 0))} ₽
🎯 <b>Целевая аудитория:</b> {getattr(offer, 'target_audience', 'Не указана')}

Ваш оффер опубликован и доступен владельцам каналов.
                """
            elif notification_type == 'new_response':
                message = f"""
📩 <b>Новый отклик на ваш оффер!</b>

📢 <b>Оффер:</b> {getattr(offer, 'title', 'Без названия')}
👤 <b>Канал:</b> {getattr(offer, 'channel_name', 'Неизвестный канал')}
💰 <b>Предложенная цена:</b> {getattr(offer, 'proposed_price', 0)} ₽

Проверьте детали в приложении.
                """
            else:
                message = f"📋 Обновление по офферу: {getattr(offer, 'title', 'Без названия')}"

            return NotificationService.send_telegram_notification(
                telegram_id,
                message,
                {
                    'type': f'offer_{notification_type}',
                    'offer_id': getattr(offer, 'id', None),
                    'user_id': user_id
                }
            )

        except Exception as e:
            logger.error(f"Ошибка отправки уведомления об оффере: {e}")
            return False

    @staticmethod
    def send_channel_notification(user, channel, notification_type: str) -> bool:
        """Уведомления о каналах"""
        try:
            # Получаем telegram_id пользователя - поддерживаем как объект, так и dict
            if hasattr(user, 'telegram_id'):
                telegram_id = user.telegram_id
                user_id = getattr(user, 'id', None)
            elif isinstance(user, dict):
                telegram_id = user.get('telegram_id')
                user_id = user.get('id')
            else:
                return False

            # Получаем данные канала - поддерживаем как объект, так и dict
            if isinstance(channel, dict):
                channel_title = channel.get('title', 'Ваш канал')
                channel_subscriber_count = channel.get('subscriber_count', 0)
                channel_telegram_id = channel.get('telegram_id')
                channel_username = channel.get('username')
                channel_id = channel.get('id')
            else:
                channel_title = getattr(channel, 'title', 'Ваш канал')
                channel_subscriber_count = getattr(channel, 'subscriber_count', 0)
                channel_telegram_id = getattr(channel, 'telegram_id', None)
                channel_username = getattr(channel, 'username', None)
                channel_id = getattr(channel, 'id', None)

            # ✅ ПЫТАЕМСЯ ПОЛУЧИТЬ АКТУАЛЬНЫЕ ДАННЫЕ ИЗ TELEGRAM
            try:
                real_channel_data = NotificationService._get_real_channel_data(
                    channel_telegram_id, channel_username
                )
                
                if real_channel_data:
                    logger.info(f"✅ Получены актуальные данные канала из Telegram API")
                    channel_title = real_channel_data.get('title', channel_title)
                    channel_subscriber_count = real_channel_data.get('member_count', channel_subscriber_count)
                else:
                    logger.info(f"⚠️ Используем данные канала из БД")
                    
            except Exception as api_error:
                logger.warning(f"⚠️ Не удалось получить данные из Telegram API: {api_error}")

            # Формируем сообщения с актуальными данными
            if notification_type == 'verified':
                message = f"""
    ✅ <b>Канал верифицирован!</b>

    📺 <b>Канал:</b> {channel_title}
    👥 <b>Подписчиков:</b> {channel_subscriber_count:,}

    Теперь вы можете получать предложения от рекламодателей!
                """
            elif notification_type == 'verification_failed':
                verification_error = channel.get('verification_error') if isinstance(channel, dict) else getattr(channel, 'verification_error', 'Проверьте код верификации')
                message = f"""
    ❌ <b>Верификация канала не пройдена</b>

    📺 <b>Канал:</b> {channel_title}
    📝 <b>Причина:</b> {verification_error}

    Повторите процедуру верификации.
                """
            elif notification_type == 'new_offer':
                offer_price = channel.get('offer_price') if isinstance(channel, dict) else getattr(channel, 'offer_price', 0)
                message = f"""
    💎 <b>Новое предложение для вашего канала!</b>

    📺 <b>Канал:</b> {channel_title}
    👥 <b>Подписчиков:</b> {channel_subscriber_count:,}
    💰 <b>Предложенная цена:</b> {offer_price} ₽

    Проверьте детали в приложении.
                """
            else:
                message = f"📋 Обновление канала: {channel_title}"

            return NotificationService.send_telegram_notification(
                telegram_id,
                message,
                {
                    'type': f'channel_{notification_type}',
                    'channel_id': channel_id,
                    'user_id': user_id,
                    'real_data_used': real_channel_data is not None if 'real_channel_data' in locals() else False
                }
            )

        except Exception as e:
            logger.error(f"Ошибка отправки уведомления о канале: {e}")
            return False

    @staticmethod
    def _get_real_channel_data(channel_telegram_id, channel_username=None):
        """Получение актуальных данных канала из Telegram Bot API"""
        try:
            from app.config.telegram_config import AppConfig
            import requests
            
            if not AppConfig.BOT_TOKEN:
                return None
                
            # Определяем chat_id для запроса
            chat_id = None
            if channel_telegram_id:
                chat_id = channel_telegram_id
            elif channel_username:
                chat_id = f"@{channel_username}" if not channel_username.startswith('@') else channel_username
            
            if not chat_id:
                return None
                
            # Запрос к Telegram Bot API
            url = f"https://api.telegram.org/bot{AppConfig.BOT_TOKEN}/getChat"
            params = {'chat_id': chat_id}
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('ok'):
                    chat_data = result.get('result', {})
                    
                    # Пытаемся получить количество участников (не всегда работает для каналов)
                    member_count = 0
                    try:
                        count_url = f"https://api.telegram.org/bot{AppConfig.BOT_TOKEN}/getChatMemberCount"
                        count_response = requests.get(count_url, params=params, timeout=10)
                        if count_response.status_code == 200:
                            count_result = count_response.json()
                            if count_result.get('ok'):
                                member_count = count_result.get('result', 0)
                    except:
                        pass
                    
                    return {
                        'title': chat_data.get('title'),
                        'username': chat_data.get('username'),
                        'description': chat_data.get('description'),
                        'member_count': member_count,
                        'type': chat_data.get('type'),
                        'invite_link': chat_data.get('invite_link')
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка получения данных канала из Telegram API: {e}")
            return None

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
            logger.warning(f"Контракт с ID {contract_id} не найден")
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
💰 <b>Сумма:</b> {data.get('price', 0)} RUB
📺 <b>Канал:</b> {data.get('channel_title', 'Неизвестный канал')}
👤 <b>Издатель:</b> {data['publisher_name']}

⏰ <b>Срок размещения:</b> {format_date(data.get('placement_deadline'))}
🔍 <b>Срок мониторинга:</b> {data.get('monitoring_duration', 7)} дней

📱 Издатель должен разместить рекламу и подать заявку в приложении."""

            publisher_msg = f"""✅ <b>Ваш отклик принят! Контракт создан.</b>

🎯 <b>Оффер:</b> {data['offer_title']}
💰 <b>Оплата:</b> {data.get('price', 0)} RUB
👤 <b>Рекламодатель:</b> {data['advertiser_name']}

⏰ <b>Разместите рекламу до:</b> {format_date(data.get('placement_deadline'))}

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
📺 <b>Канал:</b> {data.get('channel_title', 'Неизвестный канал')}

🔍 Начат мониторинг на {data.get('monitoring_duration', 7)} дней.
Оплата будет произведена автоматически после завершения мониторинга."""

                pub_msg = f"""✅ <b>Размещение проверено и подтверждено!</b>

🎯 <b>Оффер:</b> {data['offer_title']}
💰 <b>К оплате:</b> {data.get('price', 0)} RUB

🔍 Начат мониторинг на {data.get('monitoring_duration', 7)} дней.
Не удаляйте пост до завершения мониторинга!"""
            else:
                error_msg = extra_data.get('message') if extra_data else 'Размещение не соответствует требованиям'

                pub_msg = f"""❌ <b>Проверка не пройдена</b>

🎯 <b>Оффер:</b> {data['offer_title']}
❌ <b>Причина:</b> {error_msg}

🔄 Исправьте размещение и подайте заявку повторно."""

                adv_msg = f"""❌ <b>Проверка размещения не пройдена</b>

🎯 <b>Оффер:</b> {data['offer_title']}
📺 <b>Канал:</b> {data.get('channel_title', 'Неизвестный канал')}
❌ <b>Причина:</b> {error_msg}

Издатель должен исправить размещение."""

            NotificationService.send_telegram_notification(data['advertiser_telegram_id'], adv_msg)
            NotificationService.send_telegram_notification(data['publisher_telegram_id'], pub_msg)

        elif notification_type == 'completed':
            # Уведомления о завершении контракта
            payment_id = extra_data.get('payment_id') if extra_data else 'N/A'
            amount = extra_data.get('amount') if extra_data else data.get('price', 0)

            adv_msg = f"""✅ <b>Контракт завершен!</b>

🎯 <b>Оффер:</b> {data['offer_title']}
📺 <b>Канал:</b> {data.get('channel_title', 'Неизвестный канал')}
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
📺 <b>Канал:</b> {data.get('channel_title', 'Неизвестный канал')}
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