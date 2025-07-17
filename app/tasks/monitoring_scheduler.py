#!/usr/bin/env python3
"""
Планировщик задач для мониторинга постов и сбора статистики
"""

import asyncio
import logging
import schedule
import time
from datetime import datetime, timedelta
from typing import Dict, List
import threading

logger = logging.getLogger(__name__)


class MonitoringScheduler:
    """Планировщик задач мониторинга"""
    
    def __init__(self):
        self.running = False
        self.tasks = []
        
    def start(self):
        """Запускает планировщик"""
        if self.running:
            logger.warning("Планировщик уже запущен")
            return
            
        self.running = True
        logger.info("🚀 Запуск планировщика мониторинга...")
        
        # Настраиваем расписание задач
        self._setup_schedule()
        
        # Запускаем планировщик в отдельном потоке
        scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        scheduler_thread.start()
        
        logger.info("✅ Планировщик мониторинга запущен")
    
    def stop(self):
        """Останавливает планировщик"""
        self.running = False
        logger.info("⏹️ Планировщик мониторинга остановлен")
    
    def _setup_schedule(self):
        """Настраивает расписание задач"""
        
        # Мониторинг размещений каждые 30 минут
        schedule.every(30).minutes.do(self._run_placement_monitoring)
        
        # Сбор статистики постов каждый час
        schedule.every().hour.do(self._run_stats_collection)
        
        # Сбор eREIT статистики каждые 30 минут
        schedule.every(30).minutes.do(self._run_ereit_stats_collection)
        
        # Проверка просроченных размещений каждые 10 минут
        schedule.every(10).minutes.do(self._run_expiry_check)
        
        # НОВОЕ: Контроль дедлайнов каждые 15 минут
        schedule.every(15).minutes.do(self._run_deadline_monitoring)
        
        # НОВОЕ: Мониторинг удаления постов каждые 2 часа
        schedule.every(2).hours.do(self._run_deletion_monitoring)
        
        # НОВОЕ: Завершение размещений каждый час
        schedule.every().hour.do(self._run_placement_completion)
        
        # Планирование выплат каждый день в 9:00
        schedule.every().day.at("09:00").do(self._run_payment_planning)
        
        # Очистка старых данных каждую неделю в воскресенье в 2:00
        schedule.every().sunday.at("02:00").do(self._run_cleanup)
        
        # Обновление кэша дашбордов каждые 5 минут
        schedule.every(5).minutes.do(self._run_dashboard_cache_update)
        
        logger.info("📅 Расписание задач настроено (включая контроль дедлайнов, удаления постов и обновление дашбордов)")
    
    def _run_scheduler(self):
        """Основной цикл планировщика"""
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Проверяем каждую минуту
            except Exception as e:
                logger.error(f"❌ Ошибка в планировщике: {e}")
                time.sleep(60)
    
    def _run_placement_monitoring(self):
        """Запускает мониторинг размещений"""
        try:
            logger.info("🔍 Запуск мониторинга размещений...")
            
            # Запускаем асинхронную задачу
            asyncio.run(self._async_placement_monitoring())
            
        except Exception as e:
            logger.error(f"❌ Ошибка мониторинга размещений: {e}")
    
    async def _async_placement_monitoring(self):
        """Асинхронный мониторинг размещений"""
        from app.services.channel_monitor import ChannelMonitor
        from app.config.telegram_config import AppConfig
        
        monitor = ChannelMonitor(bot_token=AppConfig.BOT_TOKEN)
        
        # Проверяем активные размещения
        results = await monitor.check_pending_placements()
        
        found_count = len([r for r in results if r['status'] == 'found'])
        total_count = len(results)
        
        if total_count > 0:
            logger.info(f"📊 Мониторинг размещений: {found_count}/{total_count} постов найдено")
        
        return results
    
    def _run_stats_collection(self):
        """Запускает сбор статистики"""
        try:
            logger.info("📊 Запуск сбора статистики...")
            
            asyncio.run(self._async_stats_collection())
            
        except Exception as e:
            logger.error(f"❌ Ошибка сбора статистики: {e}")
    
    async def _async_stats_collection(self):
        """Асинхронный сбор статистики"""
        from app.services.stats_collector import StatsCollector
        
        collector = StatsCollector()
        
        # Собираем статистику для активных размещений
        results = await collector.collect_placement_stats()
        
        logger.info(f"📈 Статистика собрана для {len(results)} размещений")
        
        return results
    
    def _run_expiry_check(self):
        """Проверяет просроченные размещения"""
        try:
            logger.info("⏰ Проверка просроченных размещений...")
            
            asyncio.run(self._async_expiry_check())
            
        except Exception as e:
            logger.error(f"❌ Ошибка проверки просроченных размещений: {e}")
    
    async def _async_expiry_check(self):
        """Асинхронная проверка просроченных размещений"""
        from app.services.channel_monitor import ChannelMonitor
        from app.config.telegram_config import AppConfig
        
        monitor = ChannelMonitor(bot_token=AppConfig.BOT_TOKEN)
        
        # Проверяем просроченные размещения
        results = await monitor.check_expired_placements()
        
        if results:
            logger.info(f"⏰ Обработано просроченных размещений: {len(results)}")
        
        return results
    
    def _run_deadline_monitoring(self):
        """Запускает мониторинг дедлайнов"""
        try:
            logger.info("⏰ Запуск мониторинга дедлайнов...")
            
            asyncio.run(self._async_deadline_monitoring())
            
        except Exception as e:
            logger.error(f"❌ Ошибка мониторинга дедлайнов: {e}")
    
    async def _async_deadline_monitoring(self):
        """Асинхронный мониторинг дедлайнов"""
        from app.services.deadline_monitor import monitor_deadlines
        
        results = await monitor_deadlines()
        
        expired_count = len(results.get('expired', []))
        warning_count = len(results.get('warnings', []))
        
        if expired_count > 0 or warning_count > 0:
            logger.info(f"⏰ Мониторинг дедлайнов: {expired_count} просрочено, {warning_count} предупреждений")
        
        return results
    
    def _run_deletion_monitoring(self):
        """Запускает мониторинг удаления постов"""
        try:
            logger.info("🔍 Запуск мониторинга удаления постов...")
            
            asyncio.run(self._async_deletion_monitoring())
            
        except Exception as e:
            logger.error(f"❌ Ошибка мониторинга удаления постов: {e}")
    
    async def _async_deletion_monitoring(self):
        """Асинхронный мониторинг удаления постов"""
        from app.services.post_deletion_monitor import monitor_post_deletions
        
        results = await monitor_post_deletions()
        
        deleted_count = len([r for r in results if r['status'] == 'deleted'])
        total_count = len(results)
        
        if total_count > 0:
            logger.info(f"🔍 Мониторинг удаления: проверено {total_count} постов, удалено {deleted_count}")
        
        return results
    
    def _run_ereit_stats_collection(self):
        """Запускает сбор eREIT статистики"""
        try:
            logger.info("📊 Запуск сбора eREIT статистики...")
            
            asyncio.run(self._async_ereit_stats_collection())
            
        except Exception as e:
            logger.error(f"❌ Ошибка сбора eREIT статистики: {e}")
    
    async def _async_ereit_stats_collection(self):
        """Асинхронный сбор eREIT статистики"""
        from app.services.ereit_integration import collect_ereit_statistics
        
        results = await collect_ereit_statistics()
        
        success_count = len([r for r in results if r['status'] == 'success'])
        total_count = len(results)
        
        if total_count > 0:
            logger.info(f"📈 eREIT статистика: {success_count}/{total_count} размещений обработано")
        
        return results
    
    def _run_placement_completion(self):
        """Запускает завершение размещений"""
        try:
            logger.info("🏁 Запуск завершения размещений...")
            
            asyncio.run(self._async_placement_completion())
            
        except Exception as e:
            logger.error(f"❌ Ошибка завершения размещений: {e}")
    
    async def _async_placement_completion(self):
        """Асинхронное завершение размещений"""
        from app.services.placement_completion import complete_placements
        
        results = await complete_placements()
        
        completed_count = len([r for r in results if r['status'] == 'completed_successfully'])
        total_count = len(results)
        
        if total_count > 0:
            logger.info(f"🏁 Завершение размещений: {completed_count}/{total_count} успешно")
        
        return results
    
    def _run_payment_planning(self):
        """Планирует выплаты"""
        try:
            logger.info("💰 Планирование выплат...")
            
            # Планируем выплаты для завершенных размещений
            planned_payments = self._plan_payments()
            
            if planned_payments:
                logger.info(f"💰 Запланировано выплат: {len(planned_payments)}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка планирования выплат: {e}")
    
    def _plan_payments(self) -> List[Dict]:
        """Планирует выплаты владельцам каналов"""
        from app.models import execute_db_query
        
        # Находим завершенные размещения без запланированных выплат
        completed_placements = execute_db_query("""
            SELECT p.*, 
                   r.user_id as channel_owner_id,
                   r.channel_title,
                   u.telegram_id as channel_owner_telegram_id
            FROM offer_placements p
            JOIN offer_responses r ON p.response_id = r.id
            JOIN users u ON r.user_id = u.id
            WHERE p.status = 'completed'
            AND p.id NOT IN (SELECT placement_id FROM payments WHERE placement_id IS NOT NULL)
        """, fetch_all=True)
        
        planned_payments = []
        
        for placement in completed_placements:
            try:
                # Создаем запись о планируемой выплате
                payment_id = execute_db_query("""
                    INSERT INTO payments (
                        placement_id, 
                        user_id, 
                        amount, 
                        currency, 
                        status, 
                        scheduled_at,
                        created_at,
                        updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, (
                    placement['id'],
                    placement['channel_owner_id'],
                    placement['funds_reserved'],
                    'RUB',
                    'scheduled',
                    (datetime.now() + timedelta(days=3)).isoformat()  # Выплата через 3 дня
                ))
                
                planned_payments.append({
                    'payment_id': payment_id,
                    'placement_id': placement['id'],
                    'amount': placement['funds_reserved'],
                    'channel_owner_id': placement['channel_owner_id']
                })
                
            except Exception as e:
                logger.error(f"❌ Ошибка планирования выплаты для размещения {placement['id']}: {e}")
        
        return planned_payments
    
    def _run_cleanup(self):
        """Очищает старые данные"""
        try:
            logger.info("🧹 Очистка старых данных...")
            
            cleanup_results = self._cleanup_old_data()
            
            logger.info(f"🧹 Очистка завершена: {cleanup_results}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка очистки данных: {e}")
    
    def _cleanup_old_data(self) -> Dict:
        """Очищает старые данные из БД"""
        from app.models import execute_db_query
        
        # Удаляем старые уведомления (старше 30 дней)
        old_notifications = execute_db_query("""
            DELETE FROM notifications 
            WHERE created_at < datetime('now', '-30 days')
        """)
        
        # Удаляем старые логи ошибок (старше 7 дней)
        old_logs = execute_db_query("""
            DELETE FROM error_logs 
            WHERE created_at < datetime('now', '-7 days')
        """)
        
        # Архивируем старые размещения (старше 90 дней)
        old_placements = execute_db_query("""
            UPDATE offer_placements 
            SET status = 'archived'
            WHERE status = 'completed' 
            AND updated_at < datetime('now', '-90 days')
        """)
        
        return {
            'notifications_deleted': old_notifications or 0,
            'logs_deleted': old_logs or 0,
            'placements_archived': old_placements or 0
        }
    
    def _run_dashboard_cache_update(self):
        """Обновляет кэш дашбордов"""
        try:
            logger.debug("📊 Обновление кэша дашбордов...")
            
            self._update_dashboard_cache()
            
        except Exception as e:
            logger.error(f"❌ Ошибка обновления кэша дашбордов: {e}")
    
    def _update_dashboard_cache(self):
        """Обновляет кэшированные данные для дашбордов"""
        from app.models.database import execute_db_query
        
        try:
            # Кэшируем общую статистику
            overview_stats = execute_db_query("""
                SELECT 
                    COUNT(*) as total_placements,
                    COUNT(CASE WHEN status = 'active' THEN 1 END) as active_placements,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_placements,
                    SUM(CASE WHEN status IN ('active', 'completed') THEN funds_reserved ELSE 0 END) as total_revenue
                FROM offer_placements
                WHERE created_at >= datetime('now', '-30 days')
            """, fetch_one=True)
            
            # Обновляем кэш производительности активных размещений
            execute_db_query("""
                CREATE TEMPORARY TABLE IF NOT EXISTS dashboard_cache_temp AS
                SELECT 
                    p.id,
                    p.status,
                    COALESCE(ps.views_count, 0) as views,
                    COALESCE(es.clicks, 0) as clicks,
                    datetime('now') as cached_at
                FROM offer_placements p
                LEFT JOIN placement_statistics ps ON p.id = ps.placement_id 
                    AND ps.id = (SELECT MAX(id) FROM placement_statistics WHERE placement_id = p.id)
                LEFT JOIN ereit_statistics es ON p.id = es.placement_id 
                    AND es.id = (SELECT MAX(id) FROM ereit_statistics WHERE placement_id = p.id)
                WHERE p.status = 'active'
            """)
            
            logger.debug("✅ Кэш дашбордов обновлен")
            
        except Exception as e:
            logger.error(f"❌ Ошибка обновления кэша дашбордов: {e}")


# Глобальный экземпляр планировщика
_scheduler_instance = None


def get_scheduler() -> MonitoringScheduler:
    """Получает экземпляр планировщика (синглтон)"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = MonitoringScheduler()
    return _scheduler_instance


def start_monitoring():
    """Запускает мониторинг"""
    scheduler = get_scheduler()
    scheduler.start()


def stop_monitoring():
    """Останавливает мониторинг"""
    scheduler = get_scheduler()
    scheduler.stop()


if __name__ == "__main__":
    # Тестовый запуск
    scheduler = MonitoringScheduler()
    scheduler.start()
    
    try:
        # Бесконечный цикл для тестирования
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("🛑 Получен сигнал остановки")
        scheduler.stop()