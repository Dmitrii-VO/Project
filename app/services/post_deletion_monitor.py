#!/usr/bin/env python3
"""
Сервис мониторинга удаления постов и контроля их доступности
"""

import logging
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json

logger = logging.getLogger(__name__)


class PostDeletionMonitor:
    """Мониторинг доступности размещенных постов"""
    
    def __init__(self):
        self.session = None
        
    async def check_active_posts_availability(self) -> List[Dict]:
        """Проверяет доступность всех активных постов"""
        from app.models.database import execute_db_query
        
        logger.info("🔍 Проверка доступности активных постов...")
        
        # Получаем все активные размещения с ссылками на посты
        active_placements = execute_db_query("""
            SELECT p.*, 
                   o.title as offer_title,
                   o.created_by as advertiser_id,
                   r.user_id as channel_owner_id,
                   r.channel_title,
                   r.channel_username,
                   u_adv.telegram_id as advertiser_telegram_id,
                   u_owner.telegram_id as channel_owner_telegram_id
            FROM offer_placements p
            JOIN offer_responses r ON p.response_id = r.id
            JOIN offers o ON r.offer_id = o.id
            JOIN users u_adv ON o.created_by = u_adv.id
            JOIN users u_owner ON r.user_id = u_owner.id
            WHERE p.status = 'active'
            AND p.post_url IS NOT NULL
            AND p.placement_start IS NOT NULL
        """, fetch_all=True)
        
        results = []
        
        async with aiohttp.ClientSession() as session:
            self.session = session
            
            for placement in active_placements:
                try:
                    logger.debug(f"🔍 Проверяем пост для размещения {placement['id']}: {placement['post_url']}")
                    
                    # Проверяем доступность поста
                    is_available = await self.check_post_availability(placement['post_url'])
                    
                    if not is_available:
                        # Пост удален - обрабатываем ситуацию
                        await self.handle_deleted_post(placement)
                        results.append({
                            'placement_id': placement['id'],
                            'post_url': placement['post_url'],
                            'status': 'deleted',
                            'action': 'penalties_applied'
                        })
                        logger.warning(f"❌ Пост удален для размещения {placement['id']}: {placement['post_url']}")
                    else:
                        results.append({
                            'placement_id': placement['id'],
                            'post_url': placement['post_url'],
                            'status': 'available'
                        })
                        logger.debug(f"✅ Пост доступен для размещения {placement['id']}")
                        
                except Exception as e:
                    logger.error(f"❌ Ошибка проверки поста для размещения {placement['id']}: {e}")
                    results.append({
                        'placement_id': placement['id'],
                        'status': 'check_error',
                        'error': str(e)
                    })
        
        available_count = len([r for r in results if r['status'] == 'available'])
        deleted_count = len([r for r in results if r['status'] == 'deleted'])
        
        if results:
            logger.info(f"📊 Проверено постов: {len(results)}, доступно: {available_count}, удалено: {deleted_count}")
        
        return results
    
    async def check_post_availability(self, post_url: str) -> bool:
        """Проверяет доступность конкретного поста"""
        try:
            # Пытаемся получить пост через веб-интерфейс Telegram
            if not post_url.startswith('https://t.me/'):
                return False
            
            # Конвертируем в веб-версию для проверки
            web_url = post_url.replace('https://t.me/', 'https://t.me/s/')
            
            async with self.session.get(web_url, timeout=10) as response:
                if response.status == 200:
                    html_content = await response.text()
                    
                    # Проверяем индикаторы удаленного поста
                    deletion_indicators = [
                        'Post not found',
                        'This post was deleted',
                        'Message not found',
                        'tgme_widget_message_error',
                        'Channel not found'
                    ]
                    
                    content_lower = html_content.lower()
                    for indicator in deletion_indicators:
                        if indicator.lower() in content_lower:
                            return False
                    
                    # Если найдено содержимое поста, он доступен
                    return 'tgme_widget_message' in html_content
                else:
                    # Статус 404 или другие ошибки обычно означают удаление
                    return response.status not in [404, 403, 410]
                    
        except asyncio.TimeoutError:
            logger.warning(f"⏱️ Таймаут при проверке поста: {post_url}")
            return True  # Считаем доступным при таймауте
        except Exception as e:
            logger.error(f"❌ Ошибка проверки доступности поста {post_url}: {e}")
            return True  # Считаем доступным при ошибке проверки
    
    async def handle_deleted_post(self, placement: Dict):
        """Обрабатывает случай удаления поста"""
        try:
            # 1. Проверяем, не истек ли договорный срок размещения
            placement_end = await self.calculate_placement_end_time(placement)
            current_time = datetime.now()
            
            if current_time < placement_end:
                # Пост удален раньше срока - применяем штрафы
                await self.apply_early_deletion_penalty(placement, placement_end)
                logger.warning(f"⚠️ Преждевременное удаление поста для размещения {placement['id']}")
            else:
                # Пост удален после истечения срока - это нормально
                await self.mark_placement_completed(placement)
                logger.info(f"✅ Размещение {placement['id']} завершено по сроку")
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки удаленного поста для размещения {placement['id']}: {e}")
    
    async def calculate_placement_end_time(self, placement: Dict) -> datetime:
        """Вычисляет время окончания размещения"""
        placement_start = datetime.fromisoformat(placement['placement_start'])
        
        # По умолчанию размещение длится 24 часа
        # В будущем можно сделать настраиваемым
        placement_duration = timedelta(hours=24)
        
        return placement_start + placement_duration
    
    async def apply_early_deletion_penalty(self, placement: Dict, planned_end_time: datetime):
        """Применяет штрафы за преждевременное удаление"""
        from app.models.database import execute_db_query
        
        try:
            current_time = datetime.now()
            time_remaining = planned_end_time - current_time
            hours_remaining = time_remaining.total_seconds() / 3600
            
            # Рассчитываем штраф (например, 20% от суммы + пропорционально оставшемуся времени)
            base_penalty_rate = 0.20  # 20%
            time_penalty_rate = hours_remaining / 24  # Пропорционально оставшемуся времени
            total_penalty_rate = min(base_penalty_rate + time_penalty_rate, 0.50)  # Максимум 50%
            
            penalty_amount = float(placement['funds_reserved']) * total_penalty_rate
            
            # 1. Помечаем размещение как завершенное с нарушением
            execute_db_query("""
                UPDATE offer_placements 
                SET status = 'early_deleted',
                    early_deletion_penalty = ?,
                    actual_end_time = CURRENT_TIMESTAMP,
                    penalty_reason = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                penalty_amount,
                f"Post deleted {hours_remaining:.1f} hours before planned end",
                placement['id']
            ))
            
            # 2. Создаем запись о штрафе
            await self.create_penalty_record(placement, penalty_amount, hours_remaining)
            
            # 3. Снижаем рейтинг канала
            await self.decrease_channel_rating_for_deletion(placement)
            
            # 4. Отправляем уведомления
            await self.notify_early_deletion(placement, penalty_amount, hours_remaining)
            
            logger.info(f"💸 Штраф {penalty_amount:.2f} руб. за преждевременное удаление размещения {placement['id']}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка применения штрафа для размещения {placement['id']}: {e}")
            raise
    
    async def create_penalty_record(self, placement: Dict, penalty_amount: float, hours_remaining: float):
        """Создает запись о штрафе"""
        from app.models.database import execute_db_query
        
        execute_db_query("""
            INSERT INTO payments (
                id,
                contract_id,
                placement_id,
                publisher_id,
                advertiser_id,
                amount,
                status,
                payment_method,
                created_at,
                processed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            f"PENALTY_{placement['id']}_{int(datetime.now().timestamp())}",
            f"PENALTY_CONTRACT_{placement['id']}",
            placement['id'],
            placement['channel_owner_id'],
            placement['advertiser_id'],
            penalty_amount,
            'completed',
            'penalty',
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))
        
        logger.info(f"📝 Создана запись о штрафе {penalty_amount:.2f} руб. для размещения {placement['id']}")
    
    async def decrease_channel_rating_for_deletion(self, placement: Dict):
        """Снижает рейтинг канала за преждевременное удаление"""
        from app.models.database import execute_db_query
        
        try:
            execute_db_query("""
                UPDATE channels 
                SET early_deletions = COALESCE(early_deletions, 0) + 1,
                    reliability_rating = MAX(0, COALESCE(reliability_rating, 100) - 15),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = (
                    SELECT r.channel_id 
                    FROM offer_responses r 
                    WHERE r.id = ?
                )
            """, (placement['response_id'],))
            
            logger.info(f"📉 Рейтинг канала снижен за преждевременное удаление размещения {placement['id']}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка снижения рейтинга канала за удаление: {e}")
    
    async def notify_early_deletion(self, placement: Dict, penalty_amount: float, hours_remaining: float):
        """Отправляет уведомления о преждевременном удалении"""
        try:
            # Уведомление рекламодателю
            await self.notify_advertiser_about_deletion(placement, penalty_amount, hours_remaining)
            
            # Уведомление владельцу канала
            await self.notify_channel_owner_about_penalty(placement, penalty_amount, hours_remaining)
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки уведомлений о преждевременном удалении: {e}")
    
    async def notify_advertiser_about_deletion(self, placement: Dict, penalty_amount: float, hours_remaining: float):
        """Уведомляет рекламодателя о преждевременном удалении"""
        try:
            from app.services.telegram_service import TelegramService
            telegram_service = TelegramService()
            
            message = f"""🚨 <b>Пост удален досрочно</b>

📺 <b>Канал:</b> @{placement['channel_username']}
📋 <b>Оффер:</b> {placement['offer_title']}
🔗 <b>Ссылка была:</b> {placement['post_url']}

⏰ <b>Удален на {hours_remaining:.1f} ч. раньше срока</b>

💰 <b>Компенсация:</b>
• Штраф с канала: {penalty_amount:.2f} руб.
• Частичный возврат средств

📊 <b>Ваша реклама показывалась, статистика сохранена</b>

⚖️ Канал нарушил условия договора"""
            
            await telegram_service.send_message(
                chat_id=placement['advertiser_telegram_id'],
                text=message,
                parse_mode='HTML'
            )
            
            logger.info(f"📤 Уведомление о досрочном удалении отправлено рекламодателю {placement['advertiser_telegram_id']}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка уведомления рекламодателя о досрочном удалении: {e}")
    
    async def notify_channel_owner_about_penalty(self, placement: Dict, penalty_amount: float, hours_remaining: float):
        """Уведомляет владельца канала о штрафе"""
        try:
            from app.services.telegram_service import TelegramService
            telegram_service = TelegramService()
            
            message = f"""⚠️ <b>Штраф за досрочное удаление</b>

📋 <b>Оффер:</b> {placement['offer_title']}
🔗 <b>Удаленный пост:</b> {placement['post_url']}
⏰ <b>Удален на {hours_remaining:.1f} ч. раньше срока</b>

💸 <b>Штраф:</b> {penalty_amount:.2f} руб.
📉 <b>Рейтинг канала снижен</b>

⚖️ <b>Причина штрафа:</b>
Пост должен был оставаться {hours_remaining:.1f} ч.
Досрочное удаление нарушает договор

💡 <b>В будущем:</b>
Не удаляйте посты до истечения срока размещения"""
            
            await telegram_service.send_message(
                chat_id=placement['channel_owner_telegram_id'],
                text=message,
                parse_mode='HTML'
            )
            
            logger.info(f"📤 Уведомление о штрафе отправлено владельцу канала {placement['channel_owner_telegram_id']}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка уведомления владельца канала о штрафе: {e}")
    
    async def mark_placement_completed(self, placement: Dict):
        """Помечает размещение как завершенное"""
        from app.models.database import execute_db_query
        
        execute_db_query("""
            UPDATE offer_placements 
            SET status = 'completed',
                actual_end_time = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (placement['id'],))
        
        logger.info(f"✅ Размещение {placement['id']} помечено как завершенное")


# Функция для планировщика
async def monitor_post_deletions():
    """Основная функция мониторинга удаления постов"""
    monitor = PostDeletionMonitor()
    results = await monitor.check_active_posts_availability()
    return results


if __name__ == "__main__":
    # Тестовый запуск
    async def test_deletion_monitoring():
        results = await monitor_post_deletions()
        print(f"Результаты мониторинга удаления постов: {results}")
    
    asyncio.run(test_deletion_monitoring())