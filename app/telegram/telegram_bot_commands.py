#!/usr/bin/env python3
"""
Расширение команд Telegram бота для системы офферов
Новые команды для работы с предложениями и размещениями
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
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
    handler: Callable
    admin_only: bool = False
    channel_owner_only: bool = False

class TelegramBotExtension:
    """Расширение функциональности Telegram бота"""
    
    def __init__(self, bot_instance=None):
        self.bot = bot_instance
        self.db_path = getattr(AppConfig, 'DATABASE_PATH', 'telegram_mini_app.db')
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
    
    def get_user_proposals(self, user_id: int, status: str = None) -> List[Dict]:
        """Получение предложений пользователя"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return []
            
            cursor = conn.cursor()
            
            query = """
                SELECT 
                    op.id, op.status, op.created_at, op.expires_at,
                    op.rejection_reason, op.responded_at,
                    o.title as offer_title, o.budget as offer_budget,
                    c.title as channel_title, c.username as channel_username
                FROM offer_proposals op
                JOIN channels c ON op.channel_id = c.id
                JOIN offers o ON op.offer_id = o.id
                WHERE c.owner_id = ?
            """
            
            params = [user_id]
            
            if status:
                query += " AND op.status = ?"
                params.append(status)
            
            query += " ORDER BY op.created_at DESC LIMIT 20"
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Ошибка получения предложений: {e}")
            return []
    
    def get_user_offers(self, user_id: int) -> List[Dict]:
        """Получение офферов пользователя"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return []
            
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    o.id, o.title, o.status, o.budget, o.created_at,
                    o.selected_channels_count,
                    COUNT(op.id) as total_proposals,
                    SUM(CASE WHEN op.status = 'accepted' THEN 1 ELSE 0 END) as accepted_count
                FROM offers o
                LEFT JOIN offer_proposals op ON o.id = op.offer_id
                WHERE o.created_by = ?
                GROUP BY o.id, o.title, o.status, o.budget, o.created_at
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
                description="📋 Мои предложения - посмотреть входящие предложения",
                handler=self.handle_my_proposals
            ),
            BotCommand(
                command="my_offers",
                description="🎯 Мои офферы - посмотреть созданные офферы",
                handler=self.handle_my_offers
            ),
            BotCommand(
                command="my_channels",
                description="📢 Мои каналы - список моих каналов",
                handler=self.handle_my_channels
            ),
            BotCommand(
                command="proposal_stats",
                description="📊 Статистика предложений",
                handler=self.handle_proposal_stats
            ),
            BotCommand(
                command="accept_proposal",
                description="✅ Принять предложение",
                handler=self.handle_accept_proposal
            ),
            BotCommand(
                command="reject_proposal",
                description="❌ Отклонить предложение",
                handler=self.handle_reject_proposal
            ),
            BotCommand(
                command="placement_status",
                description="📤 Статус размещений",
                handler=self.handle_placement_status
            ),
            BotCommand(
                command="help_offers",
                description="❓ Помощь по системе офферов",
                handler=self.handle_help_offers
            )
        ]
    
    def handle_my_proposals(self, update, context) -> None:
        """Обработка команды /my_proposals"""
        try:
            telegram_id = update.effective_user.id
            user = self.get_user_by_telegram_id(telegram_id)
            
            if not user:
                update.message.reply_text(
                    "❌ Пользователь не найден. Убедитесь, что вы зарегистрированы в системе."
                )
                return
            
            # Получаем предложения
            proposals = self.get_user_proposals(user['id'])
            
            if not proposals:
                update.message.reply_text(
                    "📭 У вас пока нет предложений о размещении рекламы.\n\n"
                    "Добавьте и верифицируйте свои каналы, чтобы получать предложения!"
                )
                return
            
            # Формируем сообщение
            message = "📋 <b>Ваши предложения:</b>\n\n"
            
            # Группируем по статусам
            status_groups = {}
            for proposal in proposals:
                status = proposal['status']
                if status not in status_groups:
                    status_groups[status] = []
                status_groups[status].append(proposal)
            
            status_emojis = {
                'sent': '📨',
                'accepted': '✅',
                'rejected': '❌',
                'expired': '⏰'
            }
            
            status_names = {
                'sent': 'Ожидают ответа',
                'accepted': 'Принятые',
                'rejected': 'Отклоненные',
                'expired': 'Истекшие'
            }
            
            for status, proposals_list in status_groups.items():
                emoji = status_emojis.get(status, '📄')
                name = status_names.get(status, status.title())
                
                message += f"{emoji} <b>{name}</b> ({len(proposals_list)}):\n"
                
                for proposal in proposals_list[:5]:  # Показываем максимум 5 предложений на статус
                    message += f"• {proposal['offer_title']}\n"
                    message += f"  💰 {proposal['offer_budget']} руб.\n"
                    message += f"  📢 {proposal['channel_title']}\n"
                    
                    if status == 'sent':
                        expires_at = datetime.fromisoformat(proposal['expires_at'])
                        remaining = expires_at - datetime.now()
                        if remaining.total_seconds() > 0:
                            hours = int(remaining.total_seconds() // 3600)
                            message += f"  ⏱ Осталось: {hours} ч.\n"
                    
                    message += f"  🆔 ID: {proposal['id']}\n\n"
                
                if len(proposals_list) > 5:
                    message += f"  ... и еще {len(proposals_list) - 5}\n\n"
            
            message += "💡 <b>Команды:</b>\n"
            message += "• /accept_proposal <ID> - принять предложение\n"
            message += "• /reject_proposal <ID> - отклонить предложение\n"
            message += "• /placement_status - статус размещений"
            
            update.message.reply_text(message, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"Ошибка обработки /my_proposals: {e}")
            update.message.reply_text("❌ Произошла ошибка при получении предложений.")
    
    def handle_my_offers(self, update, context) -> None:
        """Обработка команды /my_offers"""
        try:
            telegram_id = update.effective_user.id
            user = self.get_user_by_telegram_id(telegram_id)
            
            if not user:
                update.message.reply_text("❌ Пользователь не найден.")
                return
            
            offers = self.get_user_offers(user['id'])
            
            if not offers:
                update.message.reply_text(
                    "📭 У вас пока нет офферов.\n\n"
                    "Создайте оффер через веб-приложение, чтобы начать рекламную кампанию!"
                )
                return
            
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
            
            update.message.reply_text(message, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"Ошибка обработки /my_offers: {e}")
            update.message.reply_text("❌ Произошла ошибка при получении офферов.")
    
    def handle_my_channels(self, update, context) -> None:
        """Обработка команды /my_channels"""
        try:
            telegram_id = update.effective_user.id
            user = self.get_user_by_telegram_id(telegram_id)
            
            if not user:
                update.message.reply_text("❌ Пользователь не найден.")
                return
            
            channels = self.get_user_channels(user['id'])
            
            if not channels:
                update.message.reply_text(
                    "📭 У вас пока нет каналов.\n\n"
                    "Добавьте свои каналы через веб-приложение, чтобы получать предложения о размещении рекламы!"
                )
                return
            
            message = "📢 <b>Ваши каналы:</b>\n\n"
            
            for channel in channels:
                verified_emoji = "✅" if channel['is_verified'] else "⏳"
                
                message += f"{verified_emoji} <b>{channel['title']}</b>\n"
                if channel['username']:
                    message += f"🔗 @{channel['username']}\n"
                message += f"👥 {channel['subscriber_count']} подписчиков\n"
                message += f"📊 Статус: {'Верифицирован' if channel['is_verified'] else 'Ожидает верификации'}\n"
                message += f"🆔 ID: {channel['id']}\n\n"
            
            message += "💡 Только верифицированные каналы получают предложения"
            
            update.message.reply_text(message, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"Ошибка обработки /my_channels: {e}")
            update.message.reply_text("❌ Произошла ошибка при получении каналов.")
    
    def handle_accept_proposal(self, update, context) -> None:
        """Обработка команды /accept_proposal"""
        try:
            if not context.args:
                update.message.reply_text(
                    "❌ Укажите ID предложения.\n"
                    "Пример: /accept_proposal 123"
                )
                return
            
            try:
                proposal_id = int(context.args[0])
            except ValueError:
                update.message.reply_text("❌ Неверный ID предложения.")
                return
            
            telegram_id = update.effective_user.id
            user = self.get_user_by_telegram_id(telegram_id)
            
            if not user:
                update.message.reply_text("❌ Пользователь не найден.")
                return
            
            # Получаем предложение
            proposal = self._get_proposal_by_id(proposal_id, user['id'])
            
            if not proposal:
                update.message.reply_text("❌ Предложение не найдено или вам не принадлежит.")
                return
            
            if proposal['status'] != 'sent':
                update.message.reply_text(
                    f"❌ Предложение имеет статус '{proposal['status']}' и не может быть принято."
                )
                return
            
            # Принимаем предложение
            if self._accept_proposal(proposal_id):
                message = f"✅ <b>Предложение принято!</b>\n\n"
                message += f"🎯 Оффер: {proposal['offer_title']}\n"
                message += f"💰 Бюджет: {proposal['offer_budget']} руб.\n"
                message += f"📢 Канал: {proposal['channel_title']}\n\n"
                message += f"📅 Разместите пост в течение 24 часов и подтвердите размещение через веб-приложение."
                
                update.message.reply_text(message, parse_mode='HTML')
                
                # Отправляем уведомление рекламодателю
                self._notify_advertiser_proposal_accepted(proposal_id)
                
            else:
                update.message.reply_text("❌ Не удалось принять предложение.")
            
        except Exception as e:
            logger.error(f"Ошибка обработки /accept_proposal: {e}")
            update.message.reply_text("❌ Произошла ошибка при принятии предложения.")
    
    def handle_reject_proposal(self, update, context) -> None:
        """Обработка команды /reject_proposal"""
        try:
            if len(context.args) < 2:
                update.message.reply_text(
                    "❌ Укажите ID предложения и причину отклонения.\n"
                    "Пример: /reject_proposal 123 Не подходит по тематике"
                )
                return
            
            try:
                proposal_id = int(context.args[0])
                reason = ' '.join(context.args[1:])
            except ValueError:
                update.message.reply_text("❌ Неверный ID предложения.")
                return
            
            telegram_id = update.effective_user.id
            user = self.get_user_by_telegram_id(telegram_id)
            
            if not user:
                update.message.reply_text("❌ Пользователь не найден.")
                return
            
            # Получаем предложение
            proposal = self._get_proposal_by_id(proposal_id, user['id'])
            
            if not proposal:
                update.message.reply_text("❌ Предложение не найдено или вам не принадлежит.")
                return
            
            if proposal['status'] != 'sent':
                update.message.reply_text(
                    f"❌ Предложение имеет статус '{proposal['status']}' и не может быть отклонено."
                )
                return
            
            # Отклоняем предложение
            if self._reject_proposal(proposal_id, reason):
                message = f"❌ <b>Предложение отклонено</b>\n\n"
                message += f"🎯 Оффер: {proposal['offer_title']}\n"
                message += f"📢 Канал: {proposal['channel_title']}\n"
                message += f"📝 Причина: {reason}\n\n"
                message += f"✅ Рекламодатель уведомлен об отклонении."
                
                update.message.reply_text(message, parse_mode='HTML')
                
                # Отправляем уведомление рекламодателю
                self._notify_advertiser_proposal_rejected(proposal_id, reason)
                
            else:
                update.message.reply_text("❌ Не удалось отклонить предложение.")
            
        except Exception as e:
            logger.error(f"Ошибка обработки /reject_proposal: {e}")
            update.message.reply_text("❌ Произошла ошибка при отклонении предложения.")
    
    def handle_placement_status(self, update, context) -> None:
        """Обработка команды /placement_status"""
        try:
            telegram_id = update.effective_user.id
            user = self.get_user_by_telegram_id(telegram_id)
            
            if not user:
                update.message.reply_text("❌ Пользователь не найден.")
                return
            
            # Получаем размещения пользователя
            placements = self._get_user_placements(user['id'])
            
            if not placements:
                update.message.reply_text(
                    "📭 У вас пока нет активных размещений.\n\n"
                    "Принимайте предложения о размещении рекламы, чтобы увидеть здесь статус!"
                )
                return
            
            message = "📤 <b>Статус размещений:</b>\n\n"
            
            for placement in placements:
                status_emoji = {
                    'pending': '⏳',
                    'placed': '📤',
                    'monitoring': '👀',
                    'completed': '✅',
                    'failed': '❌'
                }.get(placement['status'], '📄')
                
                message += f"{status_emoji} <b>{placement['offer_title']}</b>\n"
                message += f"📢 {placement['channel_title']}\n"
                message += f"📊 Статус: {placement['status']}\n"
                
                if placement['post_url']:
                    message += f"🔗 Пост: {placement['post_url']}\n"
                
                if placement['final_views_count']:
                    message += f"👁 Просмотры: {placement['final_views_count']}\n"
                
                message += f"🆔 ID: {placement['id']}\n\n"
            
            message += "💡 Подробную статистику смотрите в веб-приложении"
            
            update.message.reply_text(message, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"Ошибка обработки /placement_status: {e}")
            update.message.reply_text("❌ Произошла ошибка при получении статуса размещений.")
    
    def handle_proposal_stats(self, update, context) -> None:
        """Обработка команды /proposal_stats"""
        try:
            telegram_id = update.effective_user.id
            user = self.get_user_by_telegram_id(telegram_id)
            
            if not user:
                update.message.reply_text("❌ Пользователь не найден.")
                return
            
            # Получаем статистику
            stats = self._get_user_proposal_stats(user['id'])
            
            message = "📊 <b>Статистика предложений:</b>\n\n"
            
            message += f"📨 Всего получено: {stats['total']}\n"
            message += f"✅ Принято: {stats['accepted']} ({stats['acceptance_rate']:.1f}%)\n"
            message += f"❌ Отклонено: {stats['rejected']} ({stats['rejection_rate']:.1f}%)\n"
            message += f"⏰ Истекло: {stats['expired']}\n"
            message += f"⏳ Ожидает ответа: {stats['pending']}\n\n"
            
            message += f"💰 Общий доход: {stats['total_earnings']:.2f} руб.\n"
            message += f"📤 Размещений: {stats['total_placements']}\n"
            message += f"👁 Всего просмотров: {stats['total_views']}\n\n"
            
            if stats['top_categories']:
                message += "🏆 <b>Топ категории:</b>\n"
                for category, count in stats['top_categories'][:3]:
                    message += f"• {category}: {count}\n"
            
            update.message.reply_text(message, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"Ошибка обработки /proposal_stats: {e}")
            update.message.reply_text("❌ Произошла ошибка при получении статистики.")
    
    def handle_help_offers(self, update, context) -> None:
        """Обработка команды /help_offers"""
        message = "❓ <b>Помощь по системе офферов</b>\n\n"
        
        message += "🎯 <b>Для рекламодателей:</b>\n"
        message += "• Создавайте офферы через веб-приложение\n"
        message += "• Выбирайте подходящие каналы\n"
        message += "• Отслеживайте результаты\n\n"
        
        message += "📢 <b>Для владельцев каналов:</b>\n"
        message += "• Добавьте и верифицируйте каналы\n"
        message += "• Получайте предложения о размещении\n"
        message += "• Принимайте или отклоняйте предложения\n\n"
        
        message += "🤖 <b>Команды бота:</b>\n"
        message += "• /my_proposals - мои предложения\n"
        message += "• /my_offers - мои офферы\n"
        message += "• /my_channels - мои каналы\n"
        message += "• /accept_proposal <ID> - принять предложение\n"
        message += "• /reject_proposal <ID> <причина> - отклонить\n"
        message += "• /placement_status - статус размещений\n"
        message += "• /proposal_stats - статистика\n\n"
        
        message += "💡 <b>Процесс работы:</b>\n"
        message += "1. Рекламодатель создает оффер\n"
        message += "2. Система предлагает подходящие каналы\n"
        message += "3. Владельцам каналов приходят уведомления\n"
        message += "4. Принятие/отклонение предложений\n"
        message += "5. Размещение и отслеживание результатов\n\n"
        
        message += "🔗 Полный функционал доступен в веб-приложении"
        
        update.message.reply_text(message, parse_mode='HTML')
    
    def _get_proposal_by_id(self, proposal_id: int, user_id: int) -> Optional[Dict]:
        """Получение предложения по ID"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return None
            
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    op.id, op.status, op.offer_id, op.channel_id,
                    o.title as offer_title, o.budget as offer_budget,
                    c.title as channel_title
                FROM offer_proposals op
                JOIN offers o ON op.offer_id = o.id
                JOIN channels c ON op.channel_id = c.id
                WHERE op.id = ? AND c.owner_id = ?
            """, (proposal_id, user_id))
            
            result = cursor.fetchone()
            conn.close()
            
            return dict(result) if result else None
            
        except Exception as e:
            logger.error(f"Ошибка получения предложения: {e}")
            return None
    
    def _accept_proposal(self, proposal_id: int) -> bool:
        """Принятие предложения"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return False
            
            cursor = conn.cursor()
            
            # Обновляем статус предложения
            cursor.execute("""
                UPDATE offer_proposals 
                SET status = 'accepted', responded_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (proposal_id,))
            
            # Создаем запись о размещении
            cursor.execute("""
                INSERT INTO offer_placements (proposal_id, status, created_at)
                VALUES (?, 'pending', CURRENT_TIMESTAMP)
            """, (proposal_id,))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка принятия предложения: {e}")
            return False
    
    def _reject_proposal(self, proposal_id: int, reason: str) -> bool:
        """Отклонение предложения"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return False
            
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE offer_proposals 
                SET status = 'rejected', responded_at = CURRENT_TIMESTAMP, 
                    rejection_reason = ?
                WHERE id = ?
            """, (reason, proposal_id))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка отклонения предложения: {e}")
            return False
    
    def _get_user_placements(self, user_id: int) -> List[Dict]:
        """Получение размещений пользователя"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return []
            
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    opl.id, opl.status, opl.post_url, opl.final_views_count,
                    o.title as offer_title, c.title as channel_title
                FROM offer_placements opl
                JOIN offer_proposals op ON opl.proposal_id = op.id
                JOIN offers o ON op.offer_id = o.id
                JOIN channels c ON op.channel_id = c.id
                WHERE c.owner_id = ?
                ORDER BY opl.created_at DESC
                LIMIT 10
            """, (user_id,))
            
            results = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Ошибка получения размещений: {e}")
            return []
    
    def _get_user_proposal_stats(self, user_id: int) -> Dict:
        """Получение статистики предложений пользователя"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return {}
            
            cursor = conn.cursor()
            
            # Основная статистика
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'accepted' THEN 1 ELSE 0 END) as accepted,
                    SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected,
                    SUM(CASE WHEN status = 'expired' THEN 1 ELSE 0 END) as expired,
                    SUM(CASE WHEN status = 'sent' THEN 1 ELSE 0 END) as pending
                FROM offer_proposals op
                JOIN channels c ON op.channel_id = c.id
                WHERE c.owner_id = ?
            """, (user_id,))
            
            main_stats = cursor.fetchone()
            
            # Статистика размещений
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_placements,
                    SUM(final_views_count) as total_views
                FROM offer_placements opl
                JOIN offer_proposals op ON opl.proposal_id = op.id
                JOIN channels c ON op.channel_id = c.id
                WHERE c.owner_id = ?
            """, (user_id,))
            
            placement_stats = cursor.fetchone()
            
            # Топ категории
            cursor.execute("""
                SELECT o.category, COUNT(*) as count
                FROM offer_proposals op
                JOIN offers o ON op.offer_id = o.id
                JOIN channels c ON op.channel_id = c.id
                WHERE c.owner_id = ? AND op.status = 'accepted'
                GROUP BY o.category
                ORDER BY count DESC
                LIMIT 5
            """, (user_id,))
            
            top_categories = cursor.fetchall()
            
            conn.close()
            
            total = main_stats['total'] or 0
            accepted = main_stats['accepted'] or 0
            rejected = main_stats['rejected'] or 0
            
            return {
                'total': total,
                'accepted': accepted,
                'rejected': rejected,
                'expired': main_stats['expired'] or 0,
                'pending': main_stats['pending'] or 0,
                'acceptance_rate': (accepted / total * 100) if total > 0 else 0,
                'rejection_rate': (rejected / total * 100) if total > 0 else 0,
                'total_placements': placement_stats['total_placements'] or 0,
                'total_views': placement_stats['total_views'] or 0,
                'total_earnings': 0,  # Пока не реализовано
                'top_categories': [(row['category'], row['count']) for row in top_categories]
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return {}
    
    def _notify_advertiser_proposal_accepted(self, proposal_id: int):
        """Уведомление рекламодателю о принятии предложения"""
        try:
            # Импортируем систему уведомлений
            from .telegram_notifications import TelegramNotificationService
            
            service = TelegramNotificationService()
            service.send_proposal_accepted_notification(proposal_id)
            
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления о принятии: {e}")
    
    def _notify_advertiser_proposal_rejected(self, proposal_id: int, reason: str):
        """Уведомление рекламодателю об отклонении предложения"""
        try:
            # Импортируем систему уведомлений
            from .telegram_notifications import TelegramNotificationService
            
            service = TelegramNotificationService()
            service.send_proposal_rejected_notification(proposal_id, reason)
            
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления об отклонении: {e}")
    
    def register_handlers(self, dispatcher):
        """Регистрация обработчиков команд"""
        try:
            from telegram.ext import CommandHandler
            
            for command in self.commands:
                handler = CommandHandler(command.command, command.handler)
                dispatcher.add_handler(handler)
                
            logger.info(f"Зарегистрировано {len(self.commands)} команд для системы офферов")
            
        except Exception as e:
            logger.error(f"Ошибка регистрации обработчиков: {e}")
    
    def get_commands_list(self) -> List[Dict[str, str]]:
        """Получение списка команд для меню бота"""
        return [
            {"command": cmd.command, "description": cmd.description}
            for cmd in self.commands
        ]

# ================================================================
# CALLBACK HANDLERS
# ================================================================

class CallbackHandlers:
    """Обработчики inline кнопок"""
    
    def __init__(self, bot_extension: TelegramBotExtension):
        self.bot_extension = bot_extension
    
    def handle_accept_proposal_callback(self, update, context):
        """Обработка нажатия кнопки принятия предложения"""
        try:
            query = update.callback_query
            query.answer()
            
            # Извлекаем ID предложения из callback_data
            proposal_id = int(query.data.split('_')[-1])
            
            telegram_id = update.effective_user.id
            user = self.bot_extension.get_user_by_telegram_id(telegram_id)
            
            if not user:
                query.edit_message_text("❌ Пользователь не найден.")
                return
            
            # Получаем и принимаем предложение
            proposal = self.bot_extension._get_proposal_by_id(proposal_id, user['id'])
            
            if not proposal:
                query.edit_message_text("❌ Предложение не найдено.")
                return
            
            if proposal['status'] != 'sent':
                query.edit_message_text(f"❌ Предложение уже имеет статус: {proposal['status']}")
                return
            
            if self.bot_extension._accept_proposal(proposal_id):
                message = f"✅ <b>Предложение принято!</b>\n\n"
                message += f"🎯 {proposal['offer_title']}\n"
                message += f"📢 {proposal['channel_title']}\n\n"
                message += f"📅 Разместите пост в течение 24 часов"
                
                query.edit_message_text(message, parse_mode='HTML')
                
                # Уведомляем рекламодателя
                self.bot_extension._notify_advertiser_proposal_accepted(proposal_id)
            else:
                query.edit_message_text("❌ Не удалось принять предложение.")
                
        except Exception as e:
            logger.error(f"Ошибка обработки callback принятия: {e}")
            query.edit_message_text("❌ Произошла ошибка.")
    
    def handle_reject_proposal_callback(self, update, context):
        """Обработка нажатия кнопки отклонения предложения"""
        try:
            query = update.callback_query
            query.answer()
            
            # Для отклонения через кнопку просим указать причину через команду
            proposal_id = int(query.data.split('_')[-1])
            
            message = f"❌ Для отклонения предложения используйте команду:\n\n"
            message += f"<code>/reject_proposal {proposal_id} Причина отклонения</code>\n\n"
            message += f"Например:\n"
            message += f"<code>/reject_proposal {proposal_id} Не подходит по тематике</code>"
            
            query.edit_message_text(message, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"Ошибка обработки callback отклонения: {e}")
            query.edit_message_text("❌ Произошла ошибка.")
    
    def register_callback_handlers(self, dispatcher):
        """Регистрация обработчиков callback"""
        try:
            from telegram.ext import CallbackQueryHandler
            
            handlers = [
                CallbackQueryHandler(
                    self.handle_accept_proposal_callback,
                    pattern=r'^accept_proposal_\d+$'
                ),
                CallbackQueryHandler(
                    self.handle_reject_proposal_callback,
                    pattern=r'^reject_proposal_\d+$'
                )
            ]
            
            for handler in handlers:
                dispatcher.add_handler(handler)
                
            logger.info("Зарегистрированы обработчики callback для системы офферов")
            
        except Exception as e:
            logger.error(f"Ошибка регистрации callback обработчиков: {e}")

# ================================================================
# MAIN FUNCTION FOR TESTING
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