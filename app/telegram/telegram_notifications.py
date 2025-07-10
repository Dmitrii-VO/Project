#!/usr/bin/env python3
"""
Система уведомлений через Telegram Bot
Расширенная версия для новой системы офферов
"""

import sqlite3
import requests
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import os
import sys

# Добавляем путь для импорта
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.telegram_config import AppConfig

# Настройка логирования
logger = logging.getLogger(__name__)
# Путь к базе данных
DATABASE_PATH = AppConfig.DATABASE_PATH

class NotificationType(Enum):
    """Типы уведомлений"""
    NEW_PROPOSAL = "new_proposal"
    PROPOSAL_REMINDER = "proposal_reminder"
    PROPOSAL_EXPIRED = "proposal_expired"
    PROPOSAL_ACCEPTED = "proposal_accepted"
    PROPOSAL_REJECTED = "proposal_rejected"
    PLACEMENT_REQUIRED = "placement_required"
    PLACEMENT_SUBMITTED = "placement_submitted"
    PLACEMENT_VERIFIED = "placement_verified"
    PLACEMENT_FAILED = "placement_failed"
    CAMPAIGN_COMPLETED = "campaign_completed"

@dataclass
class NotificationData:
    """Данные для уведомления"""
    user_id: int
    telegram_id: int
    notification_type: NotificationType
    title: str
    message: str
    data: Dict[str, Any]
    buttons: Optional[List[Dict[str, str]]] = None
    priority: int = 1  # 1 - низкий, 2 - средний, 3 - высокий

class TelegramNotificationService:
    """Основной класс для отправки уведомлений через Telegram"""
    
    def __init__(self):
        self.bot_token = self._get_bot_token()
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}" if self.bot_token else None
        self.db_path = getattr(AppConfig, 'DATABASE_PATH', 'telegram_mini_app.db')
        
    def _get_bot_token(self) -> Optional[str]:
        """Получение токена бота"""
        try:
            return AppConfig.BOT_TOKEN
        except:
            return os.environ.get('BOT_TOKEN')
    
    def get_db_connection(self):
        """Получение соединения с базой данных"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            logger.error(f"Ошибка подключения к БД: {e}")
            return None
    
    def send_notification(self, notification: NotificationData) -> bool:
        """Отправка уведомления пользователю"""
        try:
            if not self.bot_token:
                logger.warning("BOT_TOKEN не настроен, уведомления не отправляются")
                return False
            
            # Формируем сообщение
            message_text = f"<b>{notification.title}</b>\n\n{notification.message}"
            
            # Подготавливаем данные для отправки
            send_data = {
                'chat_id': notification.telegram_id,
                'text': message_text,
                'parse_mode': 'HTML',
                'disable_web_page_preview': True
            }
            
            # Добавляем кнопки если есть
            if notification.buttons:
                keyboard = {
                    'inline_keyboard': [
                        [{'text': btn['text'], 'callback_data': btn['callback_data']}] 
                        for btn in notification.buttons
                    ]
                }
                send_data['reply_markup'] = json.dumps(keyboard)
            
            # Отправляем сообщение
            response = requests.post(
                f"{self.base_url}/sendMessage",
                json=send_data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('ok'):
                    logger.info(f"✅ Уведомление отправлено: {notification.notification_type.value} -> {notification.telegram_id}")
                    self._save_notification_log(notification, 'sent', result.get('result', {}).get('message_id'))
                    return True
                else:
                    error_msg = result.get('description', 'Unknown error')
                    logger.error(f"❌ Telegram API error: {error_msg}")
                    self._save_notification_log(notification, 'failed', error_message=error_msg)
                    return False
            else:
                logger.error(f"❌ HTTP error {response.status_code}: {response.text}")
                self._save_notification_log(notification, 'failed', error_message=f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка отправки уведомления: {e}")
            self._save_notification_log(notification, 'failed', error_message=str(e))
            return False
    
    def _save_notification_log(self, notification: NotificationData, status: str, 
                              message_id: Optional[int] = None, error_message: Optional[str] = None):
        """Сохранение лога уведомления"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return
            
            cursor = conn.cursor()
            
            # Создаем таблицу логов уведомлений если не существует
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notification_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    telegram_id INTEGER,
                    notification_type TEXT,
                    title TEXT,
                    message TEXT,
                    status TEXT,
                    message_id INTEGER,
                    error_message TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    data TEXT
                )
            """)
            
            # Сохраняем лог
            cursor.execute("""
                INSERT INTO notification_logs (
                    user_id, telegram_id, notification_type, title, message,
                    status, message_id, error_message, data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                notification.user_id,
                notification.telegram_id,
                notification.notification_type.value,
                notification.title,
                notification.message,
                status,
                message_id,
                error_message,
                json.dumps(notification.data)
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Ошибка сохранения лога уведомления: {e}")
    
    def send_new_proposal_notification(self, proposal_id: int) -> bool:
        """Уведомление о новом предложении"""
        try:
            proposal_data = self._get_proposal_data(proposal_id)
            if not proposal_data:
                return False
            
            # Формируем сообщение
            message = f"📢 <b>Новое предложение о рекламе!</b>\n\n"
            message += f"🎯 <b>Оффер:</b> {proposal_data['offer_title']}\n"
            message += f"💰 <b>Бюджет:</b> {proposal_data['offer_budget']} руб.\n"
            message += f"📊 <b>Ваш канал:</b> {proposal_data['channel_title']}\n"
            message += f"👥 <b>Подписчики:</b> {proposal_data['subscriber_count']}\n\n"
            
            if proposal_data['offer_description']:
                message += f"📝 <b>Описание:</b>\n{proposal_data['offer_description'][:200]}...\n\n"
            
            message += f"⏱ <b>Срок ответа:</b> {proposal_data['expires_at']}\n\n"
            message += f"💡 Используйте команды /my_proposals для просмотра или ответьте через веб-приложение"
            
            # Добавляем кнопки
            buttons = [
                {'text': '✅ Принять', 'callback_data': f'accept_proposal_{proposal_id}'},
                {'text': '❌ Отклонить', 'callback_data': f'reject_proposal_{proposal_id}'},
                {'text': '📋 Подробнее', 'callback_data': f'proposal_details_{proposal_id}'}
            ]
            
            notification = NotificationData(
                user_id=proposal_data['channel_owner_id'],
                telegram_id=proposal_data['channel_owner_telegram_id'],
                notification_type=NotificationType.NEW_PROPOSAL,
                title="Новое предложение о рекламе",
                message=message,
                data={
                    'proposal_id': proposal_id,
                    'offer_id': proposal_data['offer_id'],
                    'channel_id': proposal_data['channel_id']
                },
                buttons=buttons,
                priority=2
            )
            
            return self.send_notification(notification)
            
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления о новом предложении: {e}")
            return False
    
    def send_proposal_reminder(self, proposal_id: int) -> bool:
        """Напоминание о предложении"""
        try:
            proposal_data = self._get_proposal_data(proposal_id)
            if not proposal_data:
                return False
            
            # Рассчитываем оставшееся время
            expires_at = datetime.fromisoformat(proposal_data['expires_at'])
            remaining = expires_at - datetime.now()
            
            if remaining.total_seconds() <= 0:
                return False  # Уже истекло
            
            hours_remaining = int(remaining.total_seconds() // 3600)
            
            message = f"⏰ <b>Напоминание о предложении</b>\n\n"
            message += f"🎯 <b>Оффер:</b> {proposal_data['offer_title']}\n"
            message += f"💰 <b>Бюджет:</b> {proposal_data['offer_budget']} руб.\n"
            message += f"📊 <b>Ваш канал:</b> {proposal_data['channel_title']}\n\n"
            message += f"⏱ <b>Осталось времени:</b> {hours_remaining} часов\n\n"
            message += f"❗️ Не забудьте ответить на предложение до истечения срока!"
            
            buttons = [
                {'text': '✅ Принять', 'callback_data': f'accept_proposal_{proposal_id}'},
                {'text': '❌ Отклонить', 'callback_data': f'reject_proposal_{proposal_id}'}
            ]
            
            notification = NotificationData(
                user_id=proposal_data['channel_owner_id'],
                telegram_id=proposal_data['channel_owner_telegram_id'],
                notification_type=NotificationType.PROPOSAL_REMINDER,
                title="Напоминание о предложении",
                message=message,
                data={
                    'proposal_id': proposal_id,
                    'hours_remaining': hours_remaining
                },
                buttons=buttons,
                priority=3
            )
            
            return self.send_notification(notification)
            
        except Exception as e:
            logger.error(f"Ошибка отправки напоминания о предложении: {e}")
            return False
    
    def send_proposal_accepted_notification(self, proposal_id: int) -> bool:
        """Уведомление рекламодателю о принятии предложения"""
        try:
            proposal_data = self._get_proposal_data(proposal_id)
            if not proposal_data:
                return False
            
            message = f"✅ <b>Предложение принято!</b>\n\n"
            message += f"📢 <b>Канал:</b> {proposal_data['channel_title']}\n"
            message += f"👥 <b>Подписчики:</b> {proposal_data['subscriber_count']}\n"
            message += f"🎯 <b>Ваш оффер:</b> {proposal_data['offer_title']}\n\n"
            message += f"📅 <b>Ожидайте размещения в течение 24 часов</b>\n\n"
            message += f"🔔 Вы получите уведомление когда пост будет размещен"
            
            notification = NotificationData(
                user_id=proposal_data['offer_creator_id'],
                telegram_id=proposal_data['offer_creator_telegram_id'],
                notification_type=NotificationType.PROPOSAL_ACCEPTED,
                title="Предложение принято",
                message=message,
                data={
                    'proposal_id': proposal_id,
                    'offer_id': proposal_data['offer_id']
                },
                priority=2
            )
            
            return self.send_notification(notification)
            
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления о принятии: {e}")
            return False
    
    def send_proposal_rejected_notification(self, proposal_id: int, rejection_reason: str) -> bool:
        """Уведомление рекламодателю об отклонении предложения"""
        try:
            proposal_data = self._get_proposal_data(proposal_id)
            if not proposal_data:
                return False
            
            message = f"❌ <b>Предложение отклонено</b>\n\n"
            message += f"📢 <b>Канал:</b> {proposal_data['channel_title']}\n"
            message += f"🎯 <b>Ваш оффер:</b> {proposal_data['offer_title']}\n\n"
            message += f"📝 <b>Причина отклонения:</b>\n{rejection_reason}\n\n"
            message += f"💡 Вы можете попробовать связаться с другими каналами"
            
            notification = NotificationData(
                user_id=proposal_data['offer_creator_id'],
                telegram_id=proposal_data['offer_creator_telegram_id'],
                notification_type=NotificationType.PROPOSAL_REJECTED,
                title="Предложение отклонено",
                message=message,
                data={
                    'proposal_id': proposal_id,
                    'rejection_reason': rejection_reason
                },
                priority=1
            )
            
            return self.send_notification(notification)
            
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления об отклонении: {e}")
            return False
    
    def send_placement_submitted_notification(self, placement_id: int, post_url: str) -> bool:
        """Уведомление рекламодателю о размещении поста"""
        try:
            placement_data = self._get_placement_data(placement_id)
            if not placement_data:
                return False
            
            message = f"📤 <b>Пост размещен!</b>\n\n"
            message += f"📢 <b>Канал:</b> {placement_data['channel_title']}\n"
            message += f"🎯 <b>Ваш оффер:</b> {placement_data['offer_title']}\n"
            message += f"🔗 <b>Ссылка на пост:</b> {post_url}\n\n"
            message += f"✅ Пост будет автоматически отслеживаться до завершения кампании\n"
            message += f"📊 Вы получите финальную статистику по окончании"
            
            buttons = [
                {'text': '👀 Посмотреть пост', 'url': post_url},
                {'text': '📊 Статистика', 'callback_data': f'placement_stats_{placement_id}'}
            ]
            
            notification = NotificationData(
                user_id=placement_data['offer_creator_id'],
                telegram_id=placement_data['offer_creator_telegram_id'],
                notification_type=NotificationType.PLACEMENT_SUBMITTED,
                title="Пост размещен",
                message=message,
                data={
                    'placement_id': placement_id,
                    'post_url': post_url
                },
                buttons=buttons,
                priority=2
            )
            
            return self.send_notification(notification)
            
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления о размещении: {e}")
            return False
    
    def send_placement_failed_notification(self, placement_id: int, reason: str) -> bool:
        """Уведомление о проблеме с размещением"""
        try:
            placement_data = self._get_placement_data(placement_id)
            if not placement_data:
                return False
            
            message = f"⚠️ <b>Проблема с размещением</b>\n\n"
            message += f"📢 <b>Канал:</b> {placement_data['channel_title']}\n"
            message += f"🎯 <b>Ваш оффер:</b> {placement_data['offer_title']}\n\n"
            message += f"❌ <b>Проблема:</b> {reason}\n\n"
            message += f"🔔 Мы уведомили владельца канала о проблеме"
            
            notification = NotificationData(
                user_id=placement_data['offer_creator_id'],
                telegram_id=placement_data['offer_creator_telegram_id'],
                notification_type=NotificationType.PLACEMENT_FAILED,
                title="Проблема с размещением",
                message=message,
                data={
                    'placement_id': placement_id,
                    'reason': reason
                },
                priority=3
            )
            
            return self.send_notification(notification)
            
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления о проблеме: {e}")
            return False
    
    def _get_proposal_data(self, proposal_id: int) -> Optional[Dict]:
        """Получение данных предложения для уведомлений"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return None
            
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    op.id, op.offer_id, op.channel_id, op.expires_at,
                    -- Информация об оффере
                    o.title as offer_title, o.description as offer_description,
                    o.budget as offer_budget, o.created_by as offer_creator_id,
                    -- Информация о канале
                    c.title as channel_title, c.subscriber_count, c.owner_id as channel_owner_id,
                    -- Информация о владельце канала
                    u_channel.telegram_id as channel_owner_telegram_id,
                    -- Информация о создателе оффера
                    u_offer.telegram_id as offer_creator_telegram_id
                FROM offer_proposals op
                JOIN offers o ON op.offer_id = o.id
                JOIN channels c ON op.channel_id = c.id
                JOIN users u_channel ON c.owner_id = u_channel.id
                JOIN users u_offer ON o.created_by = u_offer.id
                WHERE op.id = ?
            """, (proposal_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            return dict(result) if result else None
            
        except Exception as e:
            logger.error(f"Ошибка получения данных предложения: {e}")
            return None
    
    def _get_placement_data(self, placement_id: int) -> Optional[Dict]:
        """Получение данных размещения для уведомлений"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return None
            
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    opl.id, opl.proposal_id, opl.post_url,
                    -- Информация об оффере
                    o.title as offer_title, o.created_by as offer_creator_id,
                    -- Информация о канале
                    c.title as channel_title, c.owner_id as channel_owner_id,
                    -- Информация о создателе оффера
                    u_offer.telegram_id as offer_creator_telegram_id,
                    -- Информация о владельце канала
                    u_channel.telegram_id as channel_owner_telegram_id
                FROM offer_placements opl
                JOIN offer_proposals op ON opl.proposal_id = op.id
                JOIN offers o ON op.offer_id = o.id
                JOIN channels c ON op.channel_id = c.id
                JOIN users u_offer ON o.created_by = u_offer.id
                JOIN users u_channel ON c.owner_id = u_channel.id
                WHERE opl.id = ?
            """, (placement_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            return dict(result) if result else None
            
        except Exception as e:
            logger.error(f"Ошибка получения данных размещения: {e}")
            return None
# перенесены из notifications.py
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

    📋 Доступные команды:
    /start - Начало работы
    /my_proposals - ваши предложения
    /my_offers - ваши офферы  
    /my_channels - ваши каналы
    /proposal_stats - статистика

    Начните с добавления вашего первого канала 👇
            """

            return TelegramNotificationService.send_telegram_notification(
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
                real_channel_data = TelegramNotificationService._get_real_channel_data(
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

            return TelegramNotificationService.send_telegram_notification(
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
            service = TelegramNotificationService()
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
                service = TelegramNotificationService()
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

# ================================================================
# МАССОВЫЕ УВЕДОМЛЕНИЯ
# ================================================================

class NotificationQueue:
    """Очередь уведомлений для массовой отправки"""
    
    def __init__(self):
        self.service = TelegramNotificationService()
        self.queue = []
        self.failed_notifications = []
    
    def add_notification(self, notification: NotificationData):
        """Добавление уведомления в очередь"""
        self.queue.append(notification)
    
    def process_queue(self, batch_size: int = 10, delay: float = 1.0) -> Dict[str, int]:
        """Обработка очереди уведомлений"""
        import time
        
        processed = 0
        sent = 0
        failed = 0
        
        while self.queue and processed < batch_size:
            notification = self.queue.pop(0)
            
            try:
                if self.service.send_notification(notification):
                    sent += 1
                else:
                    failed += 1
                    self.failed_notifications.append(notification)
                
                processed += 1
                
                # Задержка между отправками
                if processed < batch_size and self.queue:
                    time.sleep(delay)
                    
            except Exception as e:
                logger.error(f"Ошибка обработки уведомления: {e}")
                failed += 1
                self.failed_notifications.append(notification)
                processed += 1
        
        return {
            'processed': processed,
            'sent': sent,
            'failed': failed,
            'remaining': len(self.queue)
        }
    
    def retry_failed_notifications(self) -> Dict[str, int]:
        """Повторная отправка неудачных уведомлений"""
        if not self.failed_notifications:
            return {'processed': 0, 'sent': 0, 'failed': 0}
        
        retry_queue = self.failed_notifications.copy()
        self.failed_notifications.clear()
        
        sent = 0
        failed = 0
        
        for notification in retry_queue:
            try:
                if self.service.send_notification(notification):
                    sent += 1
                else:
                    failed += 1
                    self.failed_notifications.append(notification)
            except Exception as e:
                logger.error(f"Ошибка повторной отправки: {e}")
                failed += 1
                self.failed_notifications.append(notification)
        
        return {
            'processed': len(retry_queue),
            'sent': sent,
            'failed': failed
        }

# ================================================================
# UTILITY FUNCTIONS
# ================================================================

def send_new_proposal_notifications(offer_id: int, channel_ids: List[int]) -> Dict[str, int]:
    """Отправка уведомлений о новых предложениях"""
    try:
        service = TelegramNotificationService()
        queue = NotificationQueue()
        
        # Получаем все предложения
        conn = service.get_db_connection()
        if not conn:
            return {'sent': 0, 'failed': 0}
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id FROM offer_proposals 
            WHERE offer_id = ? AND channel_id IN ({})
        """.format(','.join('?' * len(channel_ids))), [offer_id] + channel_ids)
        
        proposal_ids = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        # Добавляем уведомления в очередь
        for proposal_id in proposal_ids:
            if service.send_new_proposal_notification(proposal_id):
                pass  # Уведомление отправлено
        
        return {'sent': len(proposal_ids), 'failed': 0}
        
    except Exception as e:
        logger.error(f"Ошибка массовой отправки уведомлений: {e}")
        return {'sent': 0, 'failed': 1}

def send_daily_reminders() -> Dict[str, int]:
    """Отправка ежедневных напоминаний"""
    try:
        service = TelegramNotificationService()
        
        # Получаем предложения, которые истекают завтра
        conn = service.get_db_connection()
        if not conn:
            return {'sent': 0, 'failed': 0}
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id FROM offer_proposals 
            WHERE status = 'sent' 
            AND expires_at BETWEEN datetime('now') AND datetime('now', '+24 hours')
            AND reminder_sent_at IS NULL
        """)
        
        proposal_ids = [row[0] for row in cursor.fetchall()]
        
        # Отправляем напоминания
        sent = 0
        failed = 0
        
        for proposal_id in proposal_ids:
            if service.send_proposal_reminder(proposal_id):
                sent += 1
                # Отмечаем что напоминание отправлено
                cursor.execute("""
                    UPDATE offer_proposals 
                    SET reminder_sent_at = CURRENT_TIMESTAMP 
                    WHERE id = ?
                """, (proposal_id,))
            else:
                failed += 1
        
        conn.commit()
        conn.close()
        
        return {'sent': sent, 'failed': failed}
        
    except Exception as e:
        logger.error(f"Ошибка отправки ежедневных напоминаний: {e}")
        return {'sent': 0, 'failed': 1}

# ================================================================
# MAIN FUNCTION FOR TESTING
# ================================================================

def main():
    """Тестовая функция"""
    service = TelegramNotificationService()
    
    # Тест отправки уведомления
    test_notification = NotificationData(
        user_id=1,
        telegram_id=373086959,  # Ваш Telegram ID
        notification_type=NotificationType.NEW_PROPOSAL,
        title="Тестовое уведомление",
        message="Это тестовое уведомление системы офферов",
        data={'test': True},
        buttons=[
            {'text': 'Тест', 'callback_data': 'test_callback'}
        ]
    )
    
    result = service.send_notification(test_notification)
    print(f"Результат отправки: {result}")

if __name__ == "__main__":
    main()