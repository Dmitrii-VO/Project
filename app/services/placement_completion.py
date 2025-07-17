#!/usr/bin/env python3
"""
Сервис завершения размещений через 24 часа с финальной статистикой и выплатами
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json

logger = logging.getLogger(__name__)


class PlacementCompletionService:
    """Сервис автоматического завершения размещений"""
    
    def __init__(self):
        self.platform_commission_rate = 0.05  # 5% комиссия платформы
        
    async def check_placements_for_completion(self) -> List[Dict]:
        """Проверяет размещения готовые к завершению (через 24+ часов)"""
        from app.models.database import execute_db_query
        
        logger.info("🏁 Проверка размещений готовых к завершению...")
        
        # Находим активные размещения, которые работают уже 24+ часов
        completion_time = datetime.now() - timedelta(hours=24)
        
        ready_placements = execute_db_query("""
            SELECT p.*, 
                   o.title as offer_title,
                   o.price as offer_price,
                   o.created_by as advertiser_id,
                   r.user_id as channel_owner_id,
                   r.channel_title,
                   r.channel_username,
                   u_adv.telegram_id as advertiser_telegram_id,
                   u_owner.telegram_id as channel_owner_telegram_id
            FROM offer_placements p
            JOIN offer_responses r ON p.proposal_id = r.id
            JOIN offers o ON r.offer_id = o.id
            JOIN users u_adv ON o.created_by = u_adv.id
            JOIN users u_owner ON r.user_id = u_owner.id
            WHERE p.status = 'active'
            AND p.placement_start IS NOT NULL
            AND p.placement_start <= ?
            AND p.post_url IS NOT NULL
        """, (completion_time.isoformat(),), fetch_all=True)
        
        results = []
        
        for placement in ready_placements:
            try:
                logger.info(f"🏁 Завершение размещения {placement['id']} - {placement['offer_title']}")
                
                # 1. Финальный сбор статистики
                final_stats = await self.collect_final_statistics(placement)
                
                # 2. Расчет выплаты с комиссией
                payout_details = await self.calculate_payout(placement, final_stats)
                
                # 3. Выполнение выплаты
                payment_result = await self.process_payout(placement, payout_details)
                
                # 4. Обновление статуса размещения
                await self.mark_placement_completed(placement, final_stats, payout_details)
                
                # 5. Генерация итогового отчета
                final_report = await self.generate_final_report(placement, final_stats, payout_details)
                
                # 6. Отправка уведомлений
                await self.send_completion_notifications(placement, final_stats, payout_details, final_report)
                
                results.append({
                    'placement_id': placement['id'],
                    'status': 'completed_successfully',
                    'final_stats': final_stats,
                    'payout_details': payout_details,
                    'payment_result': payment_result
                })
                
                logger.info(f"✅ Размещение {placement['id']} успешно завершено")
                
            except Exception as e:
                logger.error(f"❌ Ошибка завершения размещения {placement['id']}: {e}")
                results.append({
                    'placement_id': placement['id'],
                    'status': 'completion_error',
                    'error': str(e)
                })
        
        if results:
            logger.info(f"🏁 Завершено размещений: {len([r for r in results if r['status'] == 'completed_successfully'])}/{len(results)}")
        
        return results
    
    async def collect_final_statistics(self, placement: Dict) -> Dict:
        """Собирает финальную статистику из всех источников"""
        from app.models.database import execute_db_query
        
        try:
            placement_id = placement['id']
            
            # Получаем последнюю статистику Telegram
            telegram_stats = execute_db_query("""
                SELECT * FROM placement_statistics 
                WHERE placement_id = ? 
                ORDER BY collected_at DESC 
                LIMIT 1
            """, (placement_id,), fetch_one=True)
            
            # Получаем последнюю статистику eREIT
            ereit_stats = execute_db_query("""
                SELECT * FROM ereit_statistics 
                WHERE placement_id = ? 
                ORDER BY collected_at DESC 
                LIMIT 1
            """, (placement_id,), fetch_one=True)
            
            # Пытаемся собрать дополнительную статистику в режиме реального времени
            try:
                from app.services.stats_collector import StatsCollector
                from app.services.ereit_integration import EREITIntegration
                
                stats_collector = StatsCollector()
                ereit_integration = EREITIntegration()
                
                # Финальный сбор Telegram статистики
                if placement.get('post_url'):
                    final_telegram_stats = await stats_collector.collect_post_stats({
                        'post_url': placement['post_url'],
                        'ereit_token': placement['ereit_token'],
                        'created_at': placement['placement_start']
                    })
                    
                    if final_telegram_stats:
                        await stats_collector.save_stats_to_db(placement_id, final_telegram_stats)
                        # Обновляем данные только если получили новые
                        if final_telegram_stats.get('views', 0) > telegram_stats.get('views_count', 0):
                            telegram_stats = {
                                'views_count': final_telegram_stats.get('views', 0),
                                'reactions_count': final_telegram_stats.get('reactions', 0),
                                'shares_count': final_telegram_stats.get('shares', 0),
                                'comments_count': final_telegram_stats.get('comments', 0),
                                'collected_at': final_telegram_stats.get('collected_at')
                            }
                
                # Финальный сбор eREIT статистики
                if placement.get('ereit_token'):
                    final_ereit_stats = await ereit_integration.get_placement_stats(
                        placement['ereit_token'], 
                        placement_id
                    )
                    
                    if final_ereit_stats and final_ereit_stats.get('clicks', 0) > ereit_stats.get('clicks', 0):
                        ereit_stats = final_ereit_stats
                        
            except Exception as e:
                logger.warning(f"⚠️ Не удалось получить дополнительную статистику: {e}")
                # Используем существующие данные
            
            # Формируем общую статистику
            final_stats = {
                'telegram': {
                    'views': telegram_stats['views_count'] if telegram_stats else 0,
                    'reactions': telegram_stats['reactions_count'] if telegram_stats else 0,
                    'shares': telegram_stats['shares_count'] if telegram_stats else 0,
                    'comments': telegram_stats['comments_count'] if telegram_stats else 0,
                    'collected_at': telegram_stats['collected_at'] if telegram_stats else None
                },
                'ereit': {
                    'clicks': ereit_stats['clicks'] if ereit_stats else 0,
                    'unique_clicks': ereit_stats['unique_clicks'] if ereit_stats else 0,
                    'ctr': ereit_stats['ctr'] if ereit_stats else 0.0,
                    'conversions': ereit_stats['conversion_events'] if ereit_stats else 0,
                    'collected_at': ereit_stats['collected_at'] if ereit_stats else None
                },
                'performance': self.calculate_performance_metrics(placement, telegram_stats, ereit_stats),
                'placement_duration': self.calculate_placement_duration(placement),
                'collected_at': datetime.now().isoformat()
            }
            
            logger.info(f"📊 Финальная статистика собрана для размещения {placement_id}")
            return final_stats
            
        except Exception as e:
            logger.error(f"❌ Ошибка сбора финальной статистики для размещения {placement['id']}: {e}")
            return {
                'telegram': {'views': 0, 'reactions': 0, 'shares': 0, 'comments': 0},
                'ereit': {'clicks': 0, 'unique_clicks': 0, 'ctr': 0.0, 'conversions': 0},
                'performance': {},
                'error': str(e)
            }
    
    def calculate_performance_metrics(self, placement: Dict, telegram_stats: Optional[Dict], ereit_stats: Optional[Dict]) -> Dict:
        """Вычисляет метрики эффективности размещения"""
        metrics = {}
        
        try:
            views = telegram_stats['views_count'] if telegram_stats else 0
            reactions = telegram_stats['reactions_count'] if telegram_stats else 0
            clicks = ereit_stats['clicks'] if ereit_stats else 0
            conversions = ereit_stats['conversion_events'] if ereit_stats else 0
            cost = float(placement.get('funds_reserved', 0))
            
            # Основные метрики
            if views > 0:
                metrics['engagement_rate'] = round((reactions / views) * 100, 2)
                metrics['click_through_rate'] = round((clicks / views) * 100, 2)
                metrics['cost_per_view'] = round(cost / views, 2)
                metrics['cpm'] = round((cost / views) * 1000, 2)
            
            if clicks > 0:
                metrics['cost_per_click'] = round(cost / clicks, 2)
                metrics['conversion_rate'] = round((conversions / clicks) * 100, 2)
            
            if conversions > 0:
                metrics['cost_per_conversion'] = round(cost / conversions, 2)
            
            # Оценка эффективности
            if metrics.get('click_through_rate', 0) > 2.0:
                metrics['performance_rating'] = 'excellent'
            elif metrics.get('click_through_rate', 0) > 1.0:
                metrics['performance_rating'] = 'good'
            elif metrics.get('click_through_rate', 0) > 0.5:
                metrics['performance_rating'] = 'average'
            else:
                metrics['performance_rating'] = 'poor'
            
            # ROI приблизительный (если есть конверсии)
            if conversions > 0 and clicks > 0:
                estimated_revenue = conversions * 100  # Примерная оценка
                metrics['estimated_roi'] = round(((estimated_revenue - cost) / cost) * 100, 2)
            
        except Exception as e:
            logger.error(f"❌ Ошибка вычисления метрик: {e}")
            metrics['error'] = str(e)
        
        return metrics
    
    def calculate_placement_duration(self, placement: Dict) -> Dict:
        """Вычисляет длительность размещения"""
        try:
            start_time = datetime.fromisoformat(placement['placement_start'])
            end_time = datetime.now()
            duration = end_time - start_time
            
            return {
                'start_time': placement['placement_start'],
                'end_time': end_time.isoformat(),
                'duration_hours': round(duration.total_seconds() / 3600, 1),
                'duration_text': f"{duration.days} дней {duration.seconds // 3600} часов"
            }
        except Exception as e:
            return {'error': str(e)}
    
    async def calculate_payout(self, placement: Dict, final_stats: Dict) -> Dict:
        """Рассчитывает детали выплаты с учетом комиссии"""
        try:
            base_amount = float(placement.get('funds_reserved', 0))
            commission_amount = base_amount * self.platform_commission_rate
            payout_amount = base_amount - commission_amount
            
            # Бонусы за высокую эффективность
            performance_bonus = 0
            performance_rating = final_stats.get('performance', {}).get('performance_rating', 'average')
            
            if performance_rating == 'excellent':
                performance_bonus = base_amount * 0.02  # 2% бонус за отличную работу
            elif performance_rating == 'good':
                performance_bonus = base_amount * 0.01  # 1% бонус за хорошую работу
            
            final_payout = payout_amount + performance_bonus
            
            payout_details = {
                'base_amount': base_amount,
                'commission_rate': self.platform_commission_rate,
                'commission_amount': round(commission_amount, 2),
                'performance_bonus': round(performance_bonus, 2),
                'performance_rating': performance_rating,
                'net_payout': round(final_payout, 2),
                'calculated_at': datetime.now().isoformat()
            }
            
            logger.info(f"💰 Выплата рассчитана: {final_payout:.2f} руб. (база: {base_amount}, комиссия: {commission_amount:.2f}, бонус: {performance_bonus:.2f})")
            
            return payout_details
            
        except Exception as e:
            logger.error(f"❌ Ошибка расчета выплаты: {e}")
            return {
                'base_amount': 0,
                'commission_amount': 0,
                'net_payout': 0,
                'error': str(e)
            }
    
    async def process_payout(self, placement: Dict, payout_details: Dict) -> Dict:
        """Обрабатывает выплату владельцу канала"""
        from app.models.database import execute_db_query
        
        try:
            payout_amount = payout_details['net_payout']
            
            if payout_amount <= 0:
                return {'status': 'skipped', 'reason': 'zero_amount'}
            
            # Генерируем уникальные ID для платежей
            import random
            timestamp = int(datetime.now().timestamp())
            random_suffix = random.randint(1000, 9999)
            
            payout_payment_id = f"COMPLETION_{placement['id']}_{timestamp}_{random_suffix}"
            commission_payment_id = f"COMMISSION_{placement['id']}_{timestamp}_{random_suffix}"
            
            # Создаем запись о выплате
            payment_id = execute_db_query("""
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
                    processed_at,
                    completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                payout_payment_id,
                f"COMPLETION_CONTRACT_{placement['id']}_{random_suffix}",
                placement['id'],
                placement['channel_owner_id'],
                placement['advertiser_id'],
                payout_amount,
                'completed',
                'completion_payout',
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            
            # Также создаем запись о комиссии платформы
            commission_payment_result = execute_db_query("""
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
                    processed_at,
                    completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                commission_payment_id,
                f"COMMISSION_CONTRACT_{placement['id']}_{random_suffix}",
                placement['id'],
                1,  # Платформа как получатель
                placement['advertiser_id'],
                payout_details['commission_amount'],
                'completed',
                'platform_commission',
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            
            logger.info(f"💰 Выплата обработана: {payout_amount:.2f} руб. владельцу канала {placement['channel_owner_id']}")
            
            return {
                'status': 'completed',
                'payment_id': payout_payment_id,
                'commission_payment_id': commission_payment_id,
                'amount': payout_amount,
                'processed_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки выплаты: {e}")
            return {
                'status': 'failed',
                'error': str(e)
            }
    
    async def mark_placement_completed(self, placement: Dict, final_stats: Dict, payout_details: Dict):
        """Обновляет статус размещения на завершенный"""
        from app.models.database import execute_db_query
        
        try:
            execute_db_query("""
                UPDATE offer_placements 
                SET status = 'completed',
                    actual_end_time = CURRENT_TIMESTAMP,
                    final_stats = ?,
                    final_payout = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                json.dumps(final_stats),
                payout_details['net_payout'],
                placement['id']
            ))
            
            # Обновляем статистику канала
            execute_db_query("""
                UPDATE channels 
                SET completed_placements = COALESCE(completed_placements, 0) + 1,
                    total_earned = COALESCE(total_earned, 0) + ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = (
                    SELECT r.channel_id 
                    FROM offer_responses r 
                    WHERE r.id = ?
                )
            """, (payout_details['net_payout'], placement['proposal_id']))
            
            logger.info(f"✅ Размещение {placement['id']} помечено как завершенное")
            
        except Exception as e:
            logger.error(f"❌ Ошибка обновления статуса размещения: {e}")
    
    async def generate_final_report(self, placement: Dict, final_stats: Dict, payout_details: Dict) -> Dict:
        """Генерирует итоговый отчет по размещению"""
        try:
            telegram_stats = final_stats.get('telegram', {})
            ereit_stats = final_stats.get('ereit', {})
            performance = final_stats.get('performance', {})
            duration = final_stats.get('placement_duration', {})
            
            report = {
                'placement_info': {
                    'id': placement['id'],
                    'title': placement['offer_title'],
                    'channel': f"@{placement['channel_username']}",
                    'channel_title': placement['channel_title'],
                    'post_url': placement['post_url'],
                    'duration': duration.get('duration_text', 'Неизвестно')
                },
                'statistics': {
                    'views': telegram_stats.get('views', 0),
                    'reactions': telegram_stats.get('reactions', 0),
                    'shares': telegram_stats.get('shares', 0),
                    'comments': telegram_stats.get('comments', 0),
                    'clicks': ereit_stats.get('clicks', 0),
                    'unique_clicks': ereit_stats.get('unique_clicks', 0),
                    'conversions': ereit_stats.get('conversions', 0)
                },
                'performance_metrics': {
                    'ctr': performance.get('click_through_rate', 0),
                    'engagement_rate': performance.get('engagement_rate', 0),
                    'conversion_rate': performance.get('conversion_rate', 0),
                    'cost_per_click': performance.get('cost_per_click', 0),
                    'cost_per_view': performance.get('cost_per_view', 0),
                    'performance_rating': performance.get('performance_rating', 'average')
                },
                'financial': {
                    'total_cost': payout_details['base_amount'],
                    'commission': payout_details['commission_amount'],
                    'performance_bonus': payout_details.get('performance_bonus', 0),
                    'net_payout': payout_details['net_payout']
                },
                'generated_at': datetime.now().isoformat()
            }
            
            # Сохраняем отчет в базу данных
            from app.models.database import execute_db_query
            
            execute_db_query("""
                CREATE TABLE IF NOT EXISTS placement_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    placement_id INTEGER NOT NULL,
                    report_data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (placement_id) REFERENCES offer_placements(id)
                )
            """)
            
            execute_db_query("""
                INSERT INTO placement_reports (placement_id, report_data)
                VALUES (?, ?)
            """, (placement['id'], json.dumps(report)))
            
            logger.info(f"📋 Итоговый отчет сгенерирован для размещения {placement['id']}")
            
            return report
            
        except Exception as e:
            logger.error(f"❌ Ошибка генерации отчета: {e}")
            return {'error': str(e)}
    
    async def send_completion_notifications(self, placement: Dict, final_stats: Dict, payout_details: Dict, final_report: Dict):
        """Отправляет уведомления о завершении размещения"""
        try:
            # Уведомление рекламодателю
            await self.notify_advertiser_completion(placement, final_stats, final_report)
            
            # Уведомление владельцу канала
            await self.notify_channel_owner_payout(placement, final_stats, payout_details, final_report)
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки уведомлений: {e}")
    
    async def notify_advertiser_completion(self, placement: Dict, final_stats: Dict, final_report: Dict):
        """Уведомляет рекламодателя о завершении размещения"""
        try:
            from app.services.telegram_service import TelegramService
            telegram_service = TelegramService()
            
            stats = final_report.get('statistics', {})
            metrics = final_report.get('performance_metrics', {})
            
            ctr_text = f"{metrics.get('ctr', 0)}%" if metrics.get('ctr') else "н/д"
            cost_per_click = metrics.get('cost_per_click', 0)
            performance_rating = metrics.get('performance_rating', 'average')
            
            # Эмодзи в зависимости от результата
            rating_emoji = {
                'excellent': '🌟',
                'good': '👍',
                'average': '👌',
                'poor': '😐'
            }.get(performance_rating, '📊')
            
            message = f"""✅ <b>Размещение завершено!</b>

📺 <b>Канал:</b> @{placement['channel_username']}
📋 <b>Оффер:</b> {placement['offer_title']}
🔗 <b>Пост:</b> {placement['post_url']}

📊 <b>Итоговая статистика:</b>
👁 <b>Просмотры:</b> {stats.get('views', 0):,}
❤️ <b>Реакции:</b> {stats.get('reactions', 0)}
🔄 <b>Репосты:</b> {stats.get('shares', 0)}
💬 <b>Комментарии:</b> {stats.get('comments', 0)}
🖱 <b>Клики:</b> {stats.get('clicks', 0)} ({ctr_text} CTR)
🎯 <b>Конверсии:</b> {stats.get('conversions', 0)}

💰 <b>Экономика:</b>
💵 <b>Стоимость клика:</b> {cost_per_click:.2f} руб.
📈 <b>Эффективность:</b> {rating_emoji} {performance_rating.title()}

📈 <b>Подробный отчет доступен в приложении</b>

🎯 <b>Хотите разместить еще?</b> /create_offer"""
            
            await telegram_service.send_message(
                chat_id=placement['advertiser_telegram_id'],
                text=message,
                parse_mode='HTML'
            )
            
            logger.info(f"📤 Уведомление о завершении отправлено рекламодателю {placement['advertiser_telegram_id']}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка уведомления рекламодателя: {e}")
    
    async def notify_channel_owner_payout(self, placement: Dict, final_stats: Dict, payout_details: Dict, final_report: Dict):
        """Уведомляет владельца канала о выплате"""
        try:
            from app.services.telegram_service import TelegramService
            telegram_service = TelegramService()
            
            stats = final_report.get('statistics', {})
            metrics = final_report.get('performance_metrics', {})
            
            ctr = metrics.get('ctr', 0)
            payout_amount = payout_details['net_payout']
            commission_amount = payout_details['commission_amount']
            base_amount = payout_details['base_amount']
            performance_bonus = payout_details.get('performance_bonus', 0)
            
            # Определяем качество работы
            ctr_rating = "отличный" if ctr > 2.0 else "хороший" if ctr > 1.0 else "средний"
            
            bonus_text = f"\n🎁 <b>Бонус за качество:</b> +{performance_bonus:.2f} руб." if performance_bonus > 0 else ""
            
            message = f"""💰 <b>Выплата произведена!</b>

📺 <b>За размещение в</b> @{placement['channel_username']}
📋 <b>Оффер:</b> {placement['offer_title']}

💵 <b>Детали выплаты:</b>
💰 <b>Базовая сумма:</b> {base_amount:.2f} руб.
🏛 <b>Комиссия платформы:</b> -{commission_amount:.2f} руб. ({payout_details['commission_rate']*100}%){bonus_text}
✅ <b>К выплате:</b> {payout_amount:.2f} руб.

📊 <b>Результаты:</b>
👁 <b>Просмотры:</b> {stats.get('views', 0):,}
🖱 <b>Клики:</b> {stats.get('clicks', 0)} ({ctr}% CTR - {ctr_rating} результат!)
❤️ <b>Реакции:</b> {stats.get('reactions', 0)}

🎯 <b>Новые офферы:</b> /find_offers
📈 <b>Статистика канала:</b> /my_stats"""
            
            await telegram_service.send_message(
                chat_id=placement['channel_owner_telegram_id'],
                text=message,
                parse_mode='HTML'
            )
            
            logger.info(f"📤 Уведомление о выплате отправлено владельцу канала {placement['channel_owner_telegram_id']}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка уведомления владельца канала: {e}")


# Функция для планировщика
async def complete_placements():
    """Основная функция завершения размещений"""
    service = PlacementCompletionService()
    results = await service.check_placements_for_completion()
    return results


if __name__ == "__main__":
    # Тестовый запуск
    async def test_completion():
        results = await complete_placements()
        print(f"Результаты завершения размещений: {results}")
    
    asyncio.run(test_completion())