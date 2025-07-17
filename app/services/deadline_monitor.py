#!/usr/bin/env python3
"""
Сервис мониторинга дедлайнов и контроля размещений
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

logger = logging.getLogger(__name__)


class DeadlineMonitor:
    """Мониторинг дедлайнов размещений и автоматические действия"""
    
    def __init__(self):
        pass
        
    async def check_expired_placements(self) -> List[Dict]:
        """Проверяет размещения с истекшими дедлайнами"""
        from app.models.database import execute_db_query
        
        logger.info("🕐 Проверка просроченных размещений...")
        
        # Находим размещения с истекшими дедлайнами
        expired_placements = execute_db_query("""
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
            WHERE p.status = 'pending_placement'
            AND p.deadline < CURRENT_TIMESTAMP
        """, fetch_all=True)
        
        results = []
        
        for placement in expired_placements:
            try:
                logger.info(f"⏰ Обрабатываем просроченное размещение {placement['id']}")
                
                # 1. Меняем статус на просроченный
                await self.mark_placement_expired(placement)
                
                # 2. Возвращаем средства рекламодателю
                await self.refund_advertiser(placement)
                
                # 3. Отправляем уведомления
                await self.notify_expired_placement(placement)
                
                results.append({
                    'placement_id': placement['id'],
                    'status': 'expired_and_refunded',
                    'refund_amount': placement['funds_reserved']
                })
                
            except Exception as e:
                logger.error(f"❌ Ошибка обработки просроченного размещения {placement['id']}: {e}")
                results.append({
                    'placement_id': placement['id'],
                    'status': 'error',
                    'error': str(e)
                })
        
        if results:
            logger.info(f"✅ Обработано просроченных размещений: {len(results)}")
        
        return results
    
    async def mark_placement_expired(self, placement: Dict):
        """Помечает размещение как просроченное"""
        from app.models.database import execute_db_query
        
        execute_db_query("""
            UPDATE offer_placements 
            SET status = 'expired',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (placement['id'],))
        
        logger.info(f"📝 Размещение {placement['id']} помечено как просроченное")
    
    async def refund_advertiser(self, placement: Dict):
        """Возвращает средства рекламодателю"""
        from app.models.database import execute_db_query
        
        try:
            # Создаем запись о возврате средств
            refund_id = execute_db_query("""
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
                f"REFUND_{placement['id']}_{int(datetime.now().timestamp())}",
                f"REFUND_CONTRACT_{placement['id']}",
                placement['id'],
                placement['channel_owner_id'],
                placement['advertiser_id'],
                -float(placement['funds_reserved']),  # Отрицательная сумма = возврат
                'completed',
                'refund',
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            
            # Обновляем статус средств в размещении
            execute_db_query("""
                UPDATE offer_placements
                SET funds_reserved = 0,
                    refund_processed = 1,
                    refund_amount = ?,
                    refund_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (placement['funds_reserved'], placement['id']))
            
            logger.info(f"💰 Возврат {placement['funds_reserved']} руб. рекламодателю за размещение {placement['id']}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка возврата средств для размещения {placement['id']}: {e}")
            raise
    
    async def notify_expired_placement(self, placement: Dict):
        """Отправляет уведомления о просроченном размещении"""
        try:
            # Уведомление рекламодателю
            await self.notify_advertiser_about_expiry(placement)
            
            # Уведомление владельцу канала
            await self.notify_channel_owner_about_expiry(placement)
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки уведомлений о просрочке: {e}")
    
    async def notify_advertiser_about_expiry(self, placement: Dict):
        """Уведомляет рекламодателя о просрочке"""
        try:
            from app.services.telegram_service import TelegramService
            telegram_service = TelegramService()
            
            deadline_str = datetime.fromisoformat(placement['deadline']).strftime("%d %B, %H:%M")
            
            message = f"""⚠️ <b>Дедлайн размещения истек</b>

📺 <b>Канал:</b> @{placement['channel_username']} не разместил рекламу
📋 <b>Оффер:</b> {placement['offer_title']}
⏰ <b>Дедлайн был:</b> {deadline_str}
💰 <b>Средства возвращены на ваш баланс:</b> {placement['funds_reserved']} руб.

🔄 <b>Можете выбрать другой канал для размещения</b>

💡 Рекомендуем выбирать каналы с высоким рейтингом надежности."""
            
            await telegram_service.send_message(
                chat_id=placement['advertiser_telegram_id'],
                text=message,
                parse_mode='HTML'
            )
            
            logger.info(f"📤 Уведомление о просрочке отправлено рекламодателю {placement['advertiser_telegram_id']}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка уведомления рекламодателя о просрочке: {e}")
    
    async def notify_channel_owner_about_expiry(self, placement: Dict):
        """Уведомляет владельца канала о просрочке"""
        try:
            from app.services.telegram_service import TelegramService
            telegram_service = TelegramService()
            
            deadline_str = datetime.fromisoformat(placement['deadline']).strftime("%d %B, %H:%M")
            
            message = f"""❌ <b>Вы пропустили дедлайн размещения</b>

📋 <b>Оффер:</b> {placement['offer_title']}
⏰ <b>Дедлайн был:</b> {deadline_str}
💰 <b>Сумма:</b> {placement['funds_reserved']} руб.

⚠️ <b>Последствия:</b>
• Средства возвращены рекламодателю
• Ваш рейтинг надежности снижен
• Размещение отменено

💡 <b>В следующий раз:</b>
• Размещайте посты в срок
• Используйте команду /post_published для подтверждения"""
            
            await telegram_service.send_message(
                chat_id=placement['channel_owner_telegram_id'],
                text=message,
                parse_mode='HTML'
            )
            
            # Снижаем рейтинг канала
            await self.decrease_channel_rating(placement)
            
            logger.info(f"📤 Уведомление о просрочке отправлено владельцу канала {placement['channel_owner_telegram_id']}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка уведомления владельца канала о просрочке: {e}")
    
    async def decrease_channel_rating(self, placement: Dict):
        """Снижает рейтинг канала за просрочку"""
        from app.models.database import execute_db_query
        
        try:
            # Обновляем статистику канала
            execute_db_query("""
                UPDATE channels 
                SET failed_placements = COALESCE(failed_placements, 0) + 1,
                    reliability_rating = MAX(0, COALESCE(reliability_rating, 100) - 10),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = (
                    SELECT r.channel_id 
                    FROM offer_responses r 
                    WHERE r.id = ?
                )
            """, (placement['response_id'],))
            
            logger.info(f"📉 Рейтинг канала снижен за просрочку размещения {placement['id']}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка снижения рейтинга канала: {e}")
    
    async def check_pre_deadline_warnings(self) -> List[Dict]:
        """Проверяет размещения близкие к дедлайну и отправляет предупреждения"""
        from app.models.database import execute_db_query
        
        # Предупреждаем за 2 часа до дедлайна
        warning_time = datetime.now() + timedelta(hours=2)
        
        pending_placements = execute_db_query("""
            SELECT p.*, 
                   o.title as offer_title,
                   r.channel_username,
                   u.telegram_id as channel_owner_telegram_id
            FROM offer_placements p
            JOIN offer_responses r ON p.response_id = r.id
            JOIN offers o ON r.offer_id = o.id
            JOIN users u ON r.user_id = u.id
            WHERE p.status = 'pending_placement'
            AND p.deadline <= ?
            AND p.deadline > CURRENT_TIMESTAMP
            AND (p.warning_sent IS NULL OR p.warning_sent = 0)
        """, (warning_time.isoformat(),), fetch_all=True)
        
        results = []
        
        for placement in pending_placements:
            try:
                await self.send_deadline_warning(placement)
                
                # Помечаем что предупреждение отправлено
                execute_db_query("""
                    UPDATE offer_placements 
                    SET warning_sent = 1,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (placement['id'],))
                
                results.append({
                    'placement_id': placement['id'],
                    'status': 'warning_sent'
                })
                
            except Exception as e:
                logger.error(f"❌ Ошибка отправки предупреждения для размещения {placement['id']}: {e}")
                results.append({
                    'placement_id': placement['id'],
                    'status': 'warning_error',
                    'error': str(e)
                })
        
        return results
    
    async def send_deadline_warning(self, placement: Dict):
        """Отправляет предупреждение о приближающемся дедлайне"""
        try:
            from app.services.telegram_service import TelegramService
            telegram_service = TelegramService()
            
            deadline_dt = datetime.fromisoformat(placement['deadline'])
            time_left = deadline_dt - datetime.now()
            hours_left = int(time_left.total_seconds() / 3600)
            
            message = f"""⚠️ <b>Скоро дедлайн размещения!</b>

📋 <b>Оффер:</b> {placement['offer_title']}
⏰ <b>Осталось времени:</b> {hours_left} ч.
💰 <b>Сумма:</b> {placement['funds_reserved']} руб.

🚨 <b>Необходимо:</b>
1. Разместить пост в канале
2. Добавить eREIT токен: {placement['ereit_token']}
3. Отправить команду /post_published с ссылкой

❌ <b>Если не успеете:</b>
• Средства вернутся рекламодателю
• Ваш рейтинг снизится"""
            
            await telegram_service.send_message(
                chat_id=placement['channel_owner_telegram_id'],
                text=message,
                parse_mode='HTML'
            )
            
            logger.info(f"⚠️ Предупреждение о дедлайне отправлено для размещения {placement['id']}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки предупреждения о дедлайне: {e}")


# Функции для планировщика
async def monitor_deadlines():
    """Основная функция мониторинга дедлайнов"""
    monitor = DeadlineMonitor()
    
    # Проверяем просроченные размещения
    expired_results = await monitor.check_expired_placements()
    
    # Отправляем предупреждения о приближающихся дедлайнах
    warning_results = await monitor.check_pre_deadline_warnings()
    
    return {
        'expired': expired_results,
        'warnings': warning_results
    }


if __name__ == "__main__":
    # Тестовый запуск
    async def test_deadline_monitoring():
        results = await monitor_deadlines()
        print(f"Результаты мониторинга дедлайнов: {results}")
    
    asyncio.run(test_deadline_monitoring())