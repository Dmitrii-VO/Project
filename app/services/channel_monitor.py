#!/usr/bin/env python3
"""
Сервис мониторинга каналов для автоматической проверки размещения постов
"""

import logging
import re
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import json

logger = logging.getLogger(__name__)


class ChannelMonitor:
    """Мониторинг каналов для проверки размещения рекламных постов"""
    
    def __init__(self, bot_token: str = None):
        self.bot_token = bot_token
        self.api_base = f"https://api.telegram.org/bot{bot_token}" if bot_token else None
        
    async def check_pending_placements(self) -> List[Dict]:
        """Проверяет все активные размещения на предмет публикации постов"""
        from app.models import execute_db_query
        
        # Получаем все размещения со статусом pending_placement
        pending_placements = execute_db_query("""
            SELECT p.*, 
                   o.title as offer_title,
                   o.content as offer_content,
                   r.channel_username,
                   r.channel_title,
                   u.telegram_id as channel_owner_telegram_id
            FROM offer_placements p
            JOIN offer_responses r ON p.response_id = r.id
            JOIN offers o ON r.offer_id = o.id
            JOIN users u ON r.user_id = u.id
            WHERE p.status = 'pending_placement'
            AND p.deadline > CURRENT_TIMESTAMP
        """, fetch_all=True)
        
        results = []
        
        for placement in pending_placements:
            try:
                logger.info(f"🔍 Проверяем размещение ID {placement['id']} в канале @{placement['channel_username']}")
                
                # Проверяем канал на наличие поста с eREIT токеном
                post_found = await self.search_post_in_channel(
                    channel_username=placement['channel_username'],
                    ereit_token=placement['ereit_token'],
                    since_time=placement['created_at']
                )
                
                if post_found:
                    # Пост найден - обновляем статус размещения
                    await self.activate_placement(placement, post_found)
                    results.append({
                        'placement_id': placement['id'],
                        'status': 'found',
                        'post_url': post_found['url'],
                        'published_at': post_found['date']
                    })
                    logger.info(f"✅ Пост найден для размещения {placement['id']}: {post_found['url']}")
                else:
                    results.append({
                        'placement_id': placement['id'],
                        'status': 'not_found'
                    })
                    logger.debug(f"❌ Пост не найден для размещения {placement['id']}")
                    
            except Exception as e:
                logger.error(f"❌ Ошибка проверки размещения {placement['id']}: {e}")
                results.append({
                    'placement_id': placement['id'],
                    'status': 'error',
                    'error': str(e)
                })
        
        return results
    
    async def search_post_in_channel(self, channel_username: str, ereit_token: str, since_time: str) -> Optional[Dict]:
        """Ищет пост с eREIT токеном в канале"""
        if not self.api_base:
            logger.warning("❌ Bot token не настроен, поиск постов недоступен")
            return None
            
        try:
            # Преобразуем время создания размещения
            since_datetime = datetime.fromisoformat(since_time.replace('Z', '+00:00'))
            
            # Получаем последние сообщения из канала
            channel_messages = await self.get_channel_messages(channel_username, limit=50)
            
            for message in channel_messages:
                # Проверяем время публикации
                message_date = datetime.fromtimestamp(message.get('date', 0))
                if message_date < since_datetime:
                    continue
                
                # Проверяем наличие eREIT токена в тексте
                message_text = message.get('text', '') or message.get('caption', '')
                if ereit_token in message_text:
                    message_id = message.get('message_id')
                    post_url = f"https://t.me/{channel_username}/{message_id}"
                    
                    return {
                        'url': post_url,
                        'message_id': message_id,
                        'date': message_date.isoformat(),
                        'text': message_text
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Ошибка поиска поста в канале @{channel_username}: {e}")
            return None
    
    async def get_channel_messages(self, channel_username: str, limit: int = 50) -> List[Dict]:
        """Получает последние сообщения из канала через Telegram API"""
        if not self.api_base:
            return []
            
        try:
            async with aiohttp.ClientSession() as session:
                # Используем метод getUpdates с chat_id канала
                url = f"{self.api_base}/getChat"
                params = {'chat_id': f"@{channel_username}"}
                
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        logger.warning(f"❌ Не удалось получить информацию о канале @{channel_username}")
                        return []
                
                # Получаем историю сообщений (метод недоступен для ботов в публичных каналах)
                # Используем альтернативный подход через веб-скрапинг или RSS
                return await self.get_channel_messages_alternative(channel_username, limit)
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения сообщений канала @{channel_username}: {e}")
            return []
    
    async def get_channel_messages_alternative(self, channel_username: str, limit: int = 50) -> List[Dict]:
        """Альтернативный метод получения сообщений канала"""
        try:
            # Используем публичное API Telegram для получения постов
            url = f"https://t.me/s/{channel_username}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return []
                    
                    html_content = await response.text()
                    
                    # Простой парсинг HTML для извлечения постов
                    messages = self.parse_channel_html(html_content, channel_username)
                    return messages[:limit]
                    
        except Exception as e:
            logger.error(f"❌ Ошибка альтернативного получения сообщений @{channel_username}: {e}")
            return []
    
    def parse_channel_html(self, html_content: str, channel_username: str) -> List[Dict]:
        """Парсит HTML страницы канала для извлечения постов"""
        messages = []
        
        try:
            # Используем регулярные выражения для извлечения постов
            # Это упрощенная версия, в продакшене лучше использовать BeautifulSoup
            
            post_pattern = r'data-post="([^"]+)"[^>]*>[^<]*<div class="tgme_widget_message_text"[^>]*>(.*?)</div>'
            date_pattern = r'<time[^>]*datetime="([^"]+)"'
            
            post_matches = re.findall(post_pattern, html_content, re.DOTALL)
            date_matches = re.findall(date_pattern, html_content)
            
            for i, (post_id, text_html) in enumerate(post_matches):
                # Очищаем HTML теги из текста
                text = re.sub(r'<[^>]+>', '', text_html)
                text = text.strip()
                
                # Извлекаем ID сообщения
                message_id_match = re.search(r'/(\d+)$', post_id)
                message_id = int(message_id_match.group(1)) if message_id_match else i + 1
                
                # Парсим дату
                message_date = datetime.now()
                if i < len(date_matches):
                    try:
                        message_date = datetime.fromisoformat(date_matches[i].replace('Z', '+00:00'))
                    except:
                        pass
                
                messages.append({
                    'message_id': message_id,
                    'text': text,
                    'date': int(message_date.timestamp()),
                    'post_url': f"https://t.me/{channel_username}/{message_id}"
                })
            
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга HTML канала: {e}")
        
        return messages
    
    async def activate_placement(self, placement: Dict, post_info: Dict):
        """Активирует размещение после обнаружения поста"""
        from app.models import execute_db_query
        
        try:
            # Обновляем статус размещения
            execute_db_query("""
                UPDATE offer_placements 
                SET status = 'active',
                    post_url = ?,
                    placement_start = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (post_info['url'], post_info['date'], placement['id']))
            
            # Отправляем уведомление рекламодателю
            await self.notify_advertiser_about_placement(placement, post_info)
            
            logger.info(f"✅ Размещение {placement['id']} активировано автоматически")
            
        except Exception as e:
            logger.error(f"❌ Ошибка активации размещения {placement['id']}: {e}")
    
    async def notify_advertiser_about_placement(self, placement: Dict, post_info: Dict):
        """Отправляет уведомление рекламодателю о размещении"""
        try:
            from app.telegram.telegram_notifications import TelegramNotificationService
            notification_service = TelegramNotificationService()
            
            # Получаем информацию о рекламодателе
            from app.models import execute_db_query
            advertiser = execute_db_query("""
                SELECT u.telegram_id
                FROM offer_placements p
                JOIN offer_responses r ON p.response_id = r.id
                JOIN offers o ON r.offer_id = o.id
                JOIN users u ON o.created_by = u.id
                WHERE p.id = ?
            """, (placement['id'],), fetch_one=True)
            
            if not advertiser:
                return
            
            channel_name = f"@{placement['channel_username']}"
            publish_time = datetime.fromisoformat(post_info['date']).strftime("%d %B, %H:%M")
            
            message = f"""📤 <b>Реклама размещена автоматически!</b>

📺 <b>Канал:</b> {channel_name}
🔗 <b>Ссылка:</b> {post_info['url']}
⏰ <b>Размещено:</b> {publish_time}

📋 <b>Оффер:</b> {placement['offer_title']}
💰 <b>Сумма:</b> {placement.get('funds_reserved', 0)} руб.
🔗 <b>eREIT токен:</b> {placement['ereit_token']}

📊 <b>Отслеживание начато</b>
Статистика будет доступна через час

🤖 Обнаружено автоматически системой мониторинга"""
            
            notification_service.send_notification(
                user_id=advertiser['telegram_id'],
                message=message,
                notification_type='auto_placement_detected'
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки уведомления о размещении: {e}")
    
    async def check_expired_placements(self) -> List[Dict]:
        """Проверяет просроченные размещения"""
        from app.models import execute_db_query
        
        # Находим размещения с истекшим дедлайном
        expired_placements = execute_db_query("""
            SELECT p.*, 
                   r.channel_username,
                   u.telegram_id as channel_owner_telegram_id
            FROM offer_placements p
            JOIN offer_responses r ON p.response_id = r.id
            JOIN users u ON r.user_id = u.id
            WHERE p.status = 'pending_placement'
            AND p.deadline < CURRENT_TIMESTAMP
        """, fetch_all=True)
        
        results = []
        
        for placement in expired_placements:
            try:
                # Обновляем статус на просроченный
                execute_db_query("""
                    UPDATE offer_placements 
                    SET status = 'expired',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (placement['id'],))
                
                # Уведомляем участников
                await self.notify_about_expired_placement(placement)
                
                results.append({
                    'placement_id': placement['id'],
                    'status': 'expired'
                })
                
                logger.info(f"⏰ Размещение {placement['id']} помечено как просроченное")
                
            except Exception as e:
                logger.error(f"❌ Ошибка обработки просроченного размещения {placement['id']}: {e}")
        
        return results
    
    async def notify_about_expired_placement(self, placement: Dict):
        """Уведомляет о просроченном размещении"""
        try:
            from app.telegram.telegram_notifications import TelegramNotificationService
            notification_service = TelegramNotificationService()
            
            message = f"""⏰ <b>Срок размещения истек</b>

📋 <b>Размещение:</b> {placement.get('offer_title', 'Без названия')}
⏰ <b>Дедлайн был:</b> {placement['deadline']}

❌ Пост не был размещен в указанные сроки.
Размещение автоматически отменено.

💡 Вы можете подать новый отклик на этот оффер."""
            
            notification_service.send_notification(
                user_id=placement['channel_owner_telegram_id'],
                message=message,
                notification_type='placement_expired'
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка уведомления о просроченном размещении: {e}")


# Функция для запуска мониторинга
async def run_channel_monitoring():
    """Запускает цикл мониторинга каналов"""
    from app.config.telegram_config import AppConfig
    
    monitor = ChannelMonitor(bot_token=AppConfig.BOT_TOKEN)
    
    logger.info("🚀 Запуск мониторинга каналов...")
    
    while True:
        try:
            # Проверяем активные размещения
            active_results = await monitor.check_pending_placements()
            if active_results:
                logger.info(f"📊 Проверено размещений: {len(active_results)}")
            
            # Проверяем просроченные размещения
            expired_results = await monitor.check_expired_placements()
            if expired_results:
                logger.info(f"⏰ Обработано просроченных размещений: {len(expired_results)}")
            
            # Ждем 30 минут до следующей проверки
            await asyncio.sleep(30 * 60)  # 30 минут
            
        except Exception as e:
            logger.error(f"❌ Ошибка в цикле мониторинга: {e}")
            await asyncio.sleep(60)  # При ошибке ждем 1 минуту


if __name__ == "__main__":
    # Тестовый запуск
    asyncio.run(run_channel_monitoring())