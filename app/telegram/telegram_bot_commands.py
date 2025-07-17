#!/usr/bin/env python3
"""
Telegram Bot Commands для webhook системы
Переписано для работы через HTTP webhook без python-telegram-bot library
"""

import sqlite3
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import os
import sys

# Добавляем путь для импорта
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.telegram_config import AppConfig

# Настройка логирования
logger = logging.getLogger(__name__)

@dataclass
class BotCommand:
    """Команда бота"""
    command: str
    description: str
    admin_only: bool = False
    channel_owner_only: bool = False

class TelegramBotExtension:
    """Расширение функциональности Telegram бота для webhook"""
    
    def __init__(self):
        self.db_path = getattr(AppConfig, 'DATABASE_PATH', 'telegram_mini_app.db')
        self.bot_token = getattr(AppConfig, 'BOT_TOKEN', None)
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}" if self.bot_token else None
        self.commands = self._register_commands()
        
    def get_db_connection(self):
        """Получение соединения с базой данных"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            logger.error(f"Ошибка подключения к БД: {e}")
            return None
    
    def send_telegram_message(self, chat_id: int, response_data: dict) -> bool:
        """Отправка сообщения через Telegram Bot API"""
        try:
            if not self.bot_token:
                logger.error("BOT_TOKEN не настроен")
                return False
            
            url = f"{self.base_url}/sendMessage"
            data = {
                'chat_id': chat_id,
                'text': response_data.get('text', 'Сообщение'),
                'parse_mode': response_data.get('parse_mode', 'HTML'),
                'disable_web_page_preview': response_data.get('disable_web_page_preview', True)
            }
            
            # Добавляем клавиатуру если есть
            if 'reply_markup' in response_data:
                data['reply_markup'] = json.dumps(response_data['reply_markup'])
            
            response = requests.post(url, json=data, timeout=10)
            
            if response.status_code == 200 and response.json().get('ok'):
                logger.info(f"✅ Сообщение отправлено пользователю {chat_id}")
                return True
            else:
                logger.error(f"❌ Ошибка отправки: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка отправки сообщения: {e}")
            return False
    
    def get_user_by_telegram_id(self, telegram_id: int) -> Optional[Dict]:
        """Получение пользователя по Telegram ID"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return None
            
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, telegram_id, username, first_name, last_name, is_admin
                FROM users WHERE telegram_id = ?
            """, (telegram_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            return dict(result) if result else None
            
        except Exception as e:
            logger.error(f"Ошибка получения пользователя: {e}")
            return None
    
    def get_user_channels(self, user_id: int) -> List[Dict]:
        """Получение каналов пользователя"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return []
            
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, title, username, subscriber_count, is_verified, is_active
                FROM channels 
                WHERE owner_id = ? AND is_active = 1
                ORDER BY subscriber_count DESC
            """, (user_id,))
            
            results = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Ошибка получения каналов: {e}")
            return []
    
    def get_user_proposals(self, user_id: int) -> List[Dict]:
        """Получение предложений пользователя"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return []
            
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    op.id, op.offer_id, op.status, op.response_message,
                    op.proposed_price, op.created_at, op.responded_at, op.expires_at,
                    o.title as offer_title, o.description as offer_description,
                    COALESCE(o.budget_total, o.price, 0) as offer_budget,
                    o.target_audience,
                    c.title as channel_title, c.username as channel_username,
                    c.subscriber_count
                FROM offer_proposals op
                JOIN offers o ON op.offer_id = o.id
                JOIN channels c ON op.channel_id = c.id
                WHERE c.owner_id = ?
                ORDER BY op.created_at DESC
                LIMIT 20
            """, (user_id,))
            
            results = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Ошибка получения предложений: {e}")
            return []
    
    def get_user_offers(self, user_id: int) -> List[Dict]:
        """Получение офферов пользователя (ИСПРАВЛЕННАЯ ВЕРСИЯ)"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return []
            
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    o.id, o.title, o.status, 
                    COALESCE(o.budget_total, o.price, 0) as budget,
                    o.created_at,
                    COUNT(r.id) as total_proposals,
                    COUNT(CASE WHEN r.status = 'accepted' THEN 1 END) as accepted_count
                FROM offers o
                LEFT JOIN offer_responses r ON o.id = r.offer_id
                WHERE o.created_by = ?
                GROUP BY o.id, o.title, o.status, o.budget_total, o.price, o.created_at
                ORDER BY o.created_at DESC
                LIMIT 10
            """, (user_id,))
            
            results = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Ошибка получения офферов: {e}")
            return []
    
    def _register_commands(self) -> List[BotCommand]:
        """Регистрация команд бота"""
        return [
            BotCommand(
                command="my_proposals",
                description="📋 Мои предложения - посмотреть входящие предложения"
            ),
            BotCommand(
                command="my_offers", 
                description="🎯 Мои офферы - посмотреть созданные офферы"
            ),
            BotCommand(
                command="my_channels",
                description="📢 Мои каналы - список моих каналов"
            ),
            BotCommand(
                command="proposal_stats",
                description="📊 Статистика предложений"
            ),
            BotCommand(
                command="help_offers",
                description="❓ Помощь по системе офферов"
            ),
            BotCommand(
                command="post_published",
                description="✅ Подтвердить размещение рекламного поста"
            )
        ]

   
    # ================================================================
    # COMMAND HANDLERS - переписаны для webhook
    # ================================================================
    
    def handle_my_proposals(self, telegram_id: int) -> dict:
        """Обработка команды /my_proposals"""
        try:
            user = self.get_user_by_telegram_id(telegram_id)
            
            if not user:
                return {
                    'text': "❌ Пользователь не найден. Убедитесь, что вы зарегистрированы в системе.",
                    'parse_mode': 'HTML'
                }
            
            # Получаем предложения
            proposals = self.get_user_proposals(user['id'])
            
            if not proposals:
                return {
                    'text': "📭 У вас пока нет предложений о размещении рекламы.\n\n"
                           "Добавьте и верифицируйте свои каналы, чтобы получать предложения!",
                    'parse_mode': 'HTML'
                }
            
            message = "📋 <b>Ваши предложения:</b>\n\n"
            
            for proposal in proposals[:5]:  # Показываем только первые 5
                status_emoji = {
                    'pending': '⏳',
                    'accepted': '✅',
                    'rejected': '❌',
                    'completed': '🎉'
                }.get(proposal['status'], '📄')
                
                message += f"{status_emoji} <b>{proposal['offer_title']}</b>\n"
                message += f"📢 Канал: {proposal['channel_title']}\n"  # ИСПРАВЛЕНО
                message += f"💰 Оффер: {proposal['offer_budget'] or 'Не указан'} руб.\n"  # ИСПРАВЛЕНО
                message += f"📊 Статус: {proposal['status']}\n"
                message += f"🆔 ID: {proposal['id']}\n\n"
            
            if len(proposals) > 5:
                message += f"... и еще {len(proposals) - 5} предложений\n\n"
            
            message += "💡 Управляйте предложениями через веб-приложение"
            
            return {
                'text': message,
                'parse_mode': 'HTML'
            }
            
        except Exception as e:
            logger.error(f"Ошибка обработки /my_proposals: {e}")
            return {
                'text': "❌ Произошла ошибка при получении предложений.",
                'parse_mode': 'HTML'
            }
    
    def handle_my_offers(self, telegram_id: int) -> dict:
        """Обработка команды /my_offers"""
        try:
            user = self.get_user_by_telegram_id(telegram_id)
            
            if not user:
                return {
                    'text': "❌ Пользователь не найден.",
                    'parse_mode': 'HTML'
                }
            
            offers = self.get_user_offers(user['id'])
            
            if not offers:
                return {
                    'text': "📭 У вас пока нет офферов.\n\n"
                           "Создайте оффер через веб-приложение, чтобы начать рекламную кампанию!",
                    'parse_mode': 'HTML'
                }
            
            message = "🎯 <b>Ваши офферы:</b>\n\n"
            
            for offer in offers:
                status_emoji = {
                    'draft': '📝',
                    'matching': '🔍', 
                    'started': '🚀',
                    'in_progress': '⏳',
                    'completed': '✅',
                    'cancelled': '❌'
                }.get(offer['status'], '📄')
                
                message += f"{status_emoji} <b>{offer['title']}</b>\n"
                message += f"💰 Бюджет: {offer['budget']} руб.\n"
                message += f"📊 Статус: {offer['status']}\n"
                message += f"📤 Предложений: {offer['total_proposals'] or 0}\n"
                message += f"✅ Принято: {offer['accepted_count'] or 0}\n"
                message += f"🆔 ID: {offer['id']}\n\n"
            
            message += "💡 Управляйте офферами через веб-приложение"
            
            return {
                'text': message,
                'parse_mode': 'HTML'
            }
            
        except Exception as e:
            logger.error(f"Ошибка обработки /my_offers: {e}")
            return {
                'text': "❌ Произошла ошибка при получении офферов.",
                'parse_mode': 'HTML'
            }
    
    def handle_my_channels(self, telegram_id: int) -> dict:
        """Обработка команды /my_channels"""
        try:
            user = self.get_user_by_telegram_id(telegram_id)
            
            if not user:
                return {
                    'text': "❌ Пользователь не найден.",
                    'parse_mode': 'HTML'
                }
            
            channels = self.get_user_channels(user['id'])
            
            if not channels:
                return {
                    'text': "📭 У вас пока нет каналов.\n\n"
                           "Добавьте свои каналы через веб-приложение, чтобы получать предложения о размещении рекламы!",
                    'parse_mode': 'HTML'
                }
            
            message = "📢 <b>Ваши каналы:</b>\n\n"
            
            for channel in channels:
                verified_emoji = "✅" if channel['is_verified'] else "⏳"
                active_emoji = "🟢" if channel['is_active'] else "🔴"
                
                message += f"{verified_emoji}{active_emoji} <b>{channel['title']}</b>\n"
                
                if channel['username']:
                    message += f"🔗 @{channel['username']}\n"
                
                message += f"👥 Подписчиков: {channel['subscriber_count'] or 0}\n"
                message += f"🆔 ID: {channel['id']}\n\n"
            
            message += "💡 Управляйте каналами через веб-приложение"
            
            return {
                'text': message,
                'parse_mode': 'HTML'
            }
            
        except Exception as e:
            logger.error(f"Ошибка обработки /my_channels: {e}")
            return {
                'text': "❌ Произошла ошибка при получении каналов.",
                'parse_mode': 'HTML'
            }
    
    def handle_proposal_stats(self, telegram_id: int) -> dict:
        """Обработка команды /proposal_stats"""
        try:
            user = self.get_user_by_telegram_id(telegram_id)
            
            if not user:
                return {
                    'text': "❌ Пользователь не найден.",
                    'parse_mode': 'HTML'
                }
            
            conn = self.get_db_connection()
            if not conn:
                return {
                    'text': "❌ Ошибка подключения к базе данных.",
                    'parse_mode': 'HTML'
                }
            
            cursor = conn.cursor()
            
            # Статистика для владельцев каналов
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_proposals,
                    COUNT(CASE WHEN r.status = 'pending' THEN 1 END) as pending_count,
                    COUNT(CASE WHEN r.status = 'accepted' THEN 1 END) as accepted_count,
                    COUNT(CASE WHEN r.status = 'rejected' THEN 1 END) as rejected_count
                FROM offer_responses r
                JOIN channels c ON r.channel_id = c.id
                WHERE c.owner_id = ?
            """, (user['id'],))
            
            stats = cursor.fetchone()
            
            # Статистика по офферам (для рекламодателей)
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_offers,
                    COUNT(CASE WHEN o.status = 'active' THEN 1 END) as active_offers,
                    COUNT(CASE WHEN o.status = 'completed' THEN 1 END) as completed_offers
                FROM offers o
                WHERE o.advertiser_id = ?
            """, (user['id'],))
            
            offer_stats = cursor.fetchone()
            conn.close()
            
            message = "📊 <b>Ваша статистика:</b>\n\n"
            
            if stats and stats['total_proposals'] > 0:
                message += "📋 <b>Предложения (как владелец канала):</b>\n"
                message += f"📤 Всего получено: {stats['total_proposals']}\n"
                message += f"⏳ Ожидают ответа: {stats['pending_count']}\n"
                message += f"✅ Принято: {stats['accepted_count']}\n"
                message += f"❌ Отклонено: {stats['rejected_count']}\n\n"
            
            if offer_stats and offer_stats['total_offers'] > 0:
                message += "🎯 <b>Офферы (как рекламодатель):</b>\n"
                message += f"📊 Всего создано: {offer_stats['total_offers']}\n"
                message += f"🚀 Активных: {offer_stats['active_offers']}\n"
                message += f"✅ Завершенных: {offer_stats['completed_offers']}\n\n"
            
            if not stats['total_proposals'] and not offer_stats['total_offers']:
                message += "📭 У вас пока нет активности в системе.\n\n"
                message += "💡 Добавьте каналы или создайте офферы!"
            
            return {
                'text': message,
                'parse_mode': 'HTML'
            }
            
        except Exception as e:
            logger.error(f"Ошибка обработки /proposal_stats: {e}")
            return {
                'text': "❌ Произошла ошибка при получении статистики.",
                'parse_mode': 'HTML'
            }
    
    def handle_help_offers(self, telegram_id: int) -> dict:
        """Обработка команды /help_offers"""
        return {
            'text': """
❓ <b>Помощь по системе офферов</b>

🎯 <b>Для рекламодателей:</b>
• Создавайте офферы через веб-приложение
• Указывайте целевую аудиторию и бюджет
• Получайте отклики от владельцев каналов
• Выбирайте лучшие предложения

📢 <b>Для владельцев каналов:</b>
• Добавляйте и верифицируйте каналы
• Получайте предложения о размещении
• Принимайте или отклоняйте офферы
• Зарабатывайте на рекламе

📋 <b>Доступные команды:</b>
/start - Начало работы
/my_proposals - ваши предложения
/my_offers - ваши офферы  
/my_channels - ваши каналы
/proposal_stats - статистика

🌐 Полный функционал доступен в веб-приложении
            """,
            'parse_mode': 'HTML'
        }
    
    def get_commands_list(self) -> List[Dict[str, str]]:
        """Получение списка команд для меню бота"""
        return [
            {"command": cmd.command, "description": cmd.description}
            for cmd in self.commands
        ]
    
    def process_command(self, command: str, telegram_id: int) -> dict:
        """Главный роутер команд"""
        command_map = {
            'my_proposals': self.handle_my_proposals,
            'my_offers': self.handle_my_offers,
            'my_channels': self.handle_my_channels,
            'proposal_stats': self.handle_proposal_stats,
            'help_offers': self.handle_help_offers,
            'post_published': self.handle_post_published
        }
        
        handler = command_map.get(command)
        if handler:
            return handler(telegram_id)
        else:
            return {
                'text': f"❌ Неизвестная команда: /{command}\n\nИспользуйте /help_offers для списка команд.",
                'parse_mode': 'HTML'
            }
    
    def process_command_with_args(self, command: str, telegram_id: int, args: list) -> dict:
        """Обработка команд с аргументами"""
        if command == 'post_published':
            return self.handle_post_published_with_link(telegram_id, args)
        else:
            return self.process_command(command, telegram_id)
    
    def handle_post_published(self, telegram_id: int) -> dict:
        """Обработка команды /post_published - подтверждение размещения"""
        try:
            from app.models import execute_db_query
            
            # Получаем пользователя из БД
            user = self.get_user_by_telegram_id(telegram_id)
            if not user:
                return {
                    'text': "❌ Пользователь не найден в системе.",
                    'parse_mode': 'HTML'
                }
            
            # Ищем активные размещения пользователя со статусом pending_placement
            placements = execute_db_query("""
                SELECT p.*, 
                       r.offer_id,
                       o.title as offer_title,
                       o.description as offer_description,
                       COALESCE(o.budget_total, o.price) as offer_price,
                       u.telegram_id as advertiser_telegram_id,
                       u.first_name as advertiser_first_name,
                       u.last_name as advertiser_last_name,
                       c.username as channel_username,
                       c.title as channel_title,
                       r.id as response_id
                FROM offer_placements p
                JOIN offer_responses r ON p.response_id = r.id
                JOIN channels c ON r.channel_id = c.id
                JOIN users ch_owner ON r.user_id = ch_owner.id
                JOIN offers o ON r.offer_id = o.id
                JOIN users u ON o.created_by = u.id
                WHERE ch_owner.telegram_id = ? 
                AND p.status = 'pending_placement'
                AND r.status = 'accepted'
                ORDER BY p.created_at DESC
                LIMIT 1
            """, (telegram_id,), fetch_one=True)
            
            if not placements:
                return {
                    'text': """❌ У вас нет активных размещений для подтверждения.
                    
📌 Для подтверждения размещения используйте:
/post_published <ссылка_на_пост>

Пример: /post_published https://t.me/your_channel/123

🔄 Если у вас есть принятые предложения, проверьте ваши активные размещения в веб-приложении.""",
                    'parse_mode': 'HTML'
                }
            
            # Обновляем статус размещения на активное
            execute_db_query("""
                UPDATE offer_placements 
                SET status = 'active',
                    placement_start = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (placements['id'],))
            
            # Уведомляем рекламодателя о размещении
            try:
                from app.telegram.telegram_notifications import TelegramNotificationService
                notification_service = TelegramNotificationService()
                
                advertiser_message = f"""🎉 <b>Ваша реклама размещена!</b>

📢 <b>Канал:</b> @{placements.get('channel_username', 'неизвестно')}
📋 <b>Оффер:</b> {placements['offer_title']}
💰 <b>Сумма:</b> {placements['offer_price']} руб.
🆔 <b>ID размещения:</b> {placements['id']}

✅ Владелец канала подтвердил размещение рекламного поста.
📊 Отслеживание эффективности начато."""
                
                notification_service.send_notification(
                    user_id=placements['advertiser_telegram_id'],
                    message=advertiser_message,
                    notification_type='placement_confirmed'
                )
                
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления рекламодателю: {e}")
            
            return {
                'text': f"""✅ <b>Размещение подтверждено!</b>

📢 <b>Оффер:</b> {placements['offer_title']}
💰 <b>Сумма:</b> {placements['offer_price']} руб.
🆔 <b>ID размещения:</b> {placements['id']}

🎉 Рекламодатель уведомлен о размещении.
📊 Отслеживание результатов активировано.

💼 Следите за статистикой в веб-приложении.""",
                'parse_mode': 'HTML'
            }
            
        except Exception as e:
            logger.error(f"Ошибка обработки команды /post_published: {e}")
            return {
                'text': "❌ Произошла ошибка при обработке команды. Попробуйте позже.",
                'parse_mode': 'HTML'
            }
    
    def handle_post_published_with_link(self, telegram_id: int, args: list) -> dict:
        """Обработка команды /post_published с ссылкой на пост"""
        try:
            from app.models import execute_db_query
            import re
            
            # Проверяем наличие ссылки
            if not args:
                return {
                    'text': """❌ Укажите ссылку на опубликованный пост.

Использование: /post_published <ссылка>
Пример: /post_published https://t.me/your_channel/123""",
                    'parse_mode': 'HTML'
                }
            
            post_url = args[0]
            
            # Валидация ссылки на Telegram пост
            telegram_url_pattern = r'https://t\.me/([^/]+)/(\d+)'
            match = re.match(telegram_url_pattern, post_url)
            
            if not match:
                return {
                    'text': """❌ Неверный формат ссылки на пост.

Ссылка должна быть в формате:
https://t.me/channel_name/message_id

Пример: https://t.me/your_channel/123""",
                    'parse_mode': 'HTML'
                }
            
            channel_username = match.group(1)
            message_id = int(match.group(2))
            
            # Получаем пользователя из БД
            user = self.get_user_by_telegram_id(telegram_id)
            if not user:
                return {
                    'text': "❌ Пользователь не найден в системе.",
                    'parse_mode': 'HTML'
                }
            
            # Ищем активные размещения пользователя со статусом pending_placement
            placements = execute_db_query("""
                SELECT p.*, 
                       r.offer_id,
                       o.title as offer_title,
                       o.description as offer_description,
                       COALESCE(o.budget_total, o.price) as offer_price,
                       u.telegram_id as advertiser_telegram_id,
                       u.first_name as advertiser_first_name,
                       u.last_name as advertiser_last_name,
                       c.username as channel_username,
                       c.title as channel_title,
                       r.id as response_id
                FROM offer_placements p
                JOIN offer_responses r ON p.response_id = r.id
                JOIN channels c ON r.channel_id = c.id
                JOIN users ch_owner ON r.user_id = ch_owner.id
                JOIN offers o ON r.offer_id = o.id
                JOIN users u ON o.created_by = u.id
                WHERE ch_owner.telegram_id = ? 
                AND p.status = 'pending_placement'
                AND r.status = 'accepted'
                ORDER BY p.created_at DESC
                LIMIT 1
            """, (telegram_id,), fetch_one=True)
            
            if not placements:
                return {
                    'text': """❌ У вас нет активных размещений для подтверждения.
                    
🔄 Если у вас есть принятые предложения, проверьте ваши активные размещения в веб-приложении.""",
                    'parse_mode': 'HTML'
                }
            
            # Проверяем соответствие канала
            placement_channel = placements['channel_username']
            if placement_channel and placement_channel != channel_username:
                return {
                    'text': f"""❌ Ссылка указывает на канал @{channel_username}, но размещение должно быть в канале @{placement_channel}.

Убедитесь, что вы публикуете пост в правильном канале.""",
                    'parse_mode': 'HTML'
                }
            
            # Обновляем статус размещения на активное с указанием ссылки на пост
            execute_db_query("""
                UPDATE offer_placements 
                SET status = 'active',
                    post_url = ?,
                    placement_start = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (post_url, placements['id']))
            
            # Уведомляем рекламодателя о размещении
            try:
                from app.telegram.telegram_notifications import TelegramNotificationService
                notification_service = TelegramNotificationService()
                
                channel_name = f"@{channel_username}"
                publish_time = datetime.now().strftime("%d %B, %H:%M")
                
                advertiser_message = f"""📤 <b>Реклама размещена!</b>

📺 <b>Канал:</b> {channel_name}
🔗 <b>Ссылка:</b> {post_url}
⏰ <b>Размещено:</b> {publish_time}

📋 <b>Оффер:</b> {placements['offer_title']}
💰 <b>Сумма:</b> {placements['offer_price']} руб.
🆔 <b>ID размещения:</b> {placements['id']}

📊 <b>Отслеживание начато</b>
Статистика будет доступна через час"""
                
                notification_service.send_notification(
                    user_id=placements['advertiser_telegram_id'],
                    message=advertiser_message,
                    notification_type='post_published'
                )
                
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления рекламодателю: {e}")
            
            return {
                'text': f"""✅ <b>Размещение подтверждено!</b>

📺 <b>Канал:</b> @{channel_username}
🔗 <b>Ссылка:</b> {post_url}
📋 <b>Оффер:</b> {placements['offer_title']}
💰 <b>Сумма:</b> {placements['offer_price']} руб.
🆔 <b>ID размещения:</b> {placements['id']}

🎉 Рекламодатель уведомлен о размещении.
📊 Отслеживание результатов активировано.

💼 Следите за статистикой в веб-приложении.""",
                'parse_mode': 'HTML'
            }
            
        except Exception as e:
            logger.error(f"Ошибка обработки команды /post_published с ссылкой: {e}")
            return {
                'text': "❌ Произошла ошибка при обработке команды. Попробуйте позже.",
                'parse_mode': 'HTML'
            }

# ================================================================
# TESTING FUNCTION
# ================================================================

def main():
    """Тестовая функция"""
    extension = TelegramBotExtension()
    commands = extension.get_commands_list()
    
    print("Зарегистрированные команды:")
    for cmd in commands:
        print(f"/{cmd['command']} - {cmd['description']}")

if __name__ == "__main__":
    main()