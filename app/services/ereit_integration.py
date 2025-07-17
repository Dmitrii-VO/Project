#!/usr/bin/env python3
"""
Интеграция с eREIT API для получения статистики кликов и взаимодействий
"""

import logging
import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


class EREITIntegration:
    """Интеграция с eREIT API для получения статистики"""
    
    def __init__(self, api_key: str = None, base_url: str = None):
        self.api_key = api_key or self._get_api_key_from_config()
        self.base_url = base_url or "https://api.ereit.com"  # Примерный URL API
        self.session = None
        
    def _get_api_key_from_config(self) -> str:
        """Получает API ключ из конфигурации"""
        try:
            from app.config.ereit_config import EREITConfig
            return EREITConfig.API_KEY
        except ImportError:
            logger.warning("❌ Конфигурация eREIT не найдена, используется тестовый режим")
            return "test_api_key"
    
    async def get_placement_stats(self, ereit_token: str, placement_id: int) -> Optional[Dict]:
        """Получает статистику по eREIT токену для конкретного размещения"""
        try:
            if not self.api_key or self.api_key == "test_api_key":
                # Возвращаем тестовые данные
                return await self._get_mock_stats(ereit_token, placement_id)
            
            async with aiohttp.ClientSession() as session:
                self.session = session
                
                # Получаем общую статистику по токену
                stats = await self._fetch_token_stats(ereit_token)
                
                if stats:
                    # Обогащаем данными о взаимодействиях
                    interactions = await self._fetch_token_interactions(ereit_token)
                    if interactions:
                        stats.update(interactions)
                    
                    # Сохраняем статистику в БД
                    await self._save_ereit_stats(placement_id, ereit_token, stats)
                
                return stats
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики eREIT для токена {ereit_token}: {e}")
            return None
    
    async def _fetch_token_stats(self, ereit_token: str) -> Optional[Dict]:
        """Получает основную статистику по токену"""
        try:
            url = f"{self.base_url}/v1/tokens/{ereit_token}/stats"
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    return {
                        'clicks': data.get('clicks', 0),
                        'unique_clicks': data.get('unique_clicks', 0),
                        'impressions': data.get('impressions', 0),
                        'ctr': data.get('ctr', 0.0),
                        'last_click_at': data.get('last_click_at'),
                        'first_click_at': data.get('first_click_at'),
                        'collected_at': datetime.now().isoformat(),
                        'source': 'ereit_api'
                    }
                elif response.status == 404:
                    logger.warning(f"⚠️ Токен {ereit_token} не найден в eREIT API")
                    return None
                else:
                    logger.error(f"❌ Ошибка API eREIT: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Ошибка запроса статистики токена {ereit_token}: {e}")
            return None
    
    async def _fetch_token_interactions(self, ereit_token: str) -> Optional[Dict]:
        """Получает данные о взаимодействиях пользователей"""
        try:
            url = f"{self.base_url}/v1/tokens/{ereit_token}/interactions"
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            # Получаем данные за последние 24 часа
            params = {
                'from': (datetime.now() - timedelta(hours=24)).isoformat(),
                'to': datetime.now().isoformat()
            }
            
            async with self.session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    interactions = data.get('interactions', [])
                    
                    # Анализируем типы взаимодействий
                    interaction_stats = {
                        'button_clicks': 0,
                        'link_clicks': 0,
                        'phone_clicks': 0,
                        'email_clicks': 0,
                        'social_clicks': 0,
                        'conversion_events': 0
                    }
                    
                    for interaction in interactions:
                        interaction_type = interaction.get('type', 'unknown')
                        if interaction_type in interaction_stats:
                            interaction_stats[interaction_type] += 1
                        elif interaction_type in ['purchase', 'signup', 'download']:
                            interaction_stats['conversion_events'] += 1
                    
                    return interaction_stats
                    
                return None
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения взаимодействий для токена {ereit_token}: {e}")
            return None
    
    async def _get_mock_stats(self, ereit_token: str, placement_id: int) -> Dict:
        """Возвращает тестовые данные для разработки"""
        import random
        
        # Генерируем реалистичные тестовые данные
        base_clicks = random.randint(50, 500)
        unique_ratio = random.uniform(0.6, 0.9)
        ctr = random.uniform(0.5, 5.0)
        
        return {
            'clicks': base_clicks,
            'unique_clicks': int(base_clicks * unique_ratio),
            'impressions': int(base_clicks / (ctr / 100)),
            'ctr': round(ctr, 2),
            'button_clicks': random.randint(5, 50),
            'link_clicks': random.randint(10, 80),
            'phone_clicks': random.randint(0, 15),
            'email_clicks': random.randint(0, 10),
            'social_clicks': random.randint(5, 30),
            'conversion_events': random.randint(1, 20),
            'last_click_at': (datetime.now() - timedelta(minutes=random.randint(1, 60))).isoformat(),
            'first_click_at': (datetime.now() - timedelta(hours=random.randint(1, 24))).isoformat(),
            'collected_at': datetime.now().isoformat(),
            'source': 'ereit_mock'
        }
    
    async def _save_ereit_stats(self, placement_id: int, ereit_token: str, stats: Dict):
        """Сохраняет статистику eREIT в базу данных"""
        from app.models.database import execute_db_query
        
        try:
            # Создаем таблицу для eREIT статистики, если её нет
            execute_db_query("""
                CREATE TABLE IF NOT EXISTS ereit_statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    placement_id INTEGER NOT NULL,
                    ereit_token TEXT NOT NULL,
                    clicks INTEGER DEFAULT 0,
                    unique_clicks INTEGER DEFAULT 0,
                    impressions INTEGER DEFAULT 0,
                    ctr REAL DEFAULT 0.0,
                    button_clicks INTEGER DEFAULT 0,
                    link_clicks INTEGER DEFAULT 0,
                    phone_clicks INTEGER DEFAULT 0,
                    email_clicks INTEGER DEFAULT 0,
                    social_clicks INTEGER DEFAULT 0,
                    conversion_events INTEGER DEFAULT 0,
                    first_click_at TIMESTAMP,
                    last_click_at TIMESTAMP,
                    collected_at TIMESTAMP,
                    source TEXT DEFAULT 'ereit_api',
                    raw_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (placement_id) REFERENCES offer_placements(id)
                )
            """)
            
            # Сохраняем статистику
            execute_db_query("""
                INSERT INTO ereit_statistics (
                    placement_id, ereit_token, clicks, unique_clicks, impressions, ctr,
                    button_clicks, link_clicks, phone_clicks, email_clicks, 
                    social_clicks, conversion_events, first_click_at, last_click_at,
                    collected_at, source, raw_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                placement_id,
                ereit_token,
                stats.get('clicks', 0),
                stats.get('unique_clicks', 0),
                stats.get('impressions', 0),
                stats.get('ctr', 0.0),
                stats.get('button_clicks', 0),
                stats.get('link_clicks', 0),
                stats.get('phone_clicks', 0),
                stats.get('email_clicks', 0),
                stats.get('social_clicks', 0),
                stats.get('conversion_events', 0),
                stats.get('first_click_at'),
                stats.get('last_click_at'),
                stats.get('collected_at'),
                stats.get('source', 'ereit_api'),
                json.dumps(stats)
            ))
            
            logger.info(f"✅ Статистика eREIT сохранена для размещения {placement_id}: {stats.get('clicks', 0)} кликов")
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения статистики eREIT: {e}")
    
    async def collect_stats_for_active_placements(self) -> List[Dict]:
        """Собирает статистику eREIT для всех активных размещений"""
        from app.models.database import execute_db_query
        
        # Получаем активные размещения с eREIT токенами
        active_placements = execute_db_query("""
            SELECT p.id, p.ereit_token, p.post_url,
                   o.title as offer_title,
                   r.channel_username
            FROM offer_placements p
            JOIN offer_responses r ON p.response_id = r.id
            JOIN offers o ON r.offer_id = o.id
            WHERE p.status = 'active'
            AND p.ereit_token IS NOT NULL
            AND p.ereit_token != ''
        """, fetch_all=True)
        
        results = []
        
        for placement in active_placements:
            try:
                logger.info(f"📊 Собираем eREIT статистику для размещения {placement['id']}")
                
                stats = await self.get_placement_stats(
                    placement['ereit_token'], 
                    placement['id']
                )
                
                if stats:
                    results.append({
                        'placement_id': placement['id'],
                        'ereit_token': placement['ereit_token'],
                        'stats': stats,
                        'status': 'success'
                    })
                else:
                    results.append({
                        'placement_id': placement['id'],
                        'ereit_token': placement['ereit_token'],
                        'status': 'no_data'
                    })
                    
            except Exception as e:
                logger.error(f"❌ Ошибка сбора eREIT статистики для размещения {placement['id']}: {e}")
                results.append({
                    'placement_id': placement['id'],
                    'ereit_token': placement['ereit_token'],
                    'status': 'error',
                    'error': str(e)
                })
        
        logger.info(f"📈 Собрана eREIT статистика для {len(results)} размещений")
        return results
    
    async def get_aggregated_stats(self, placement_id: int) -> Optional[Dict]:
        """Получает агрегированную статистику для размещения"""
        from app.models.database import execute_db_query
        
        try:
            # Получаем последнюю статистику из разных источников
            ereit_stats = execute_db_query("""
                SELECT * FROM ereit_statistics 
                WHERE placement_id = ? 
                ORDER BY collected_at DESC 
                LIMIT 1
            """, (placement_id,), fetch_one=True)
            
            telegram_stats = execute_db_query("""
                SELECT * FROM placement_statistics 
                WHERE placement_id = ? 
                ORDER BY collected_at DESC 
                LIMIT 1
            """, (placement_id,), fetch_one=True)
            
            # Объединяем статистику
            aggregated = {
                'placement_id': placement_id,
                'telegram': {
                    'views': telegram_stats['views_count'] if telegram_stats else 0,
                    'reactions': telegram_stats['reactions_count'] if telegram_stats else 0,
                    'shares': telegram_stats['shares_count'] if telegram_stats else 0,
                    'comments': telegram_stats['comments_count'] if telegram_stats else 0,
                } if telegram_stats else {},
                'ereit': {
                    'clicks': ereit_stats['clicks'] if ereit_stats else 0,
                    'unique_clicks': ereit_stats['unique_clicks'] if ereit_stats else 0,
                    'impressions': ereit_stats['impressions'] if ereit_stats else 0,
                    'ctr': ereit_stats['ctr'] if ereit_stats else 0.0,
                    'conversions': ereit_stats['conversion_events'] if ereit_stats else 0,
                } if ereit_stats else {},
                'updated_at': datetime.now().isoformat()
            }
            
            # Вычисляем комплексные метрики
            if telegram_stats and ereit_stats:
                views = telegram_stats['views_count'] or 1
                clicks = ereit_stats['clicks'] or 0
                
                aggregated['computed'] = {
                    'click_through_rate': round((clicks / views) * 100, 2),
                    'engagement_rate': round(((telegram_stats['reactions_count'] or 0) + clicks) / views * 100, 2),
                    'conversion_rate': round((ereit_stats['conversion_events'] or 0) / clicks * 100, 2) if clicks > 0 else 0
                }
            
            return aggregated
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения агрегированной статистики для размещения {placement_id}: {e}")
            return None


# Функция для планировщика
async def collect_ereit_statistics():
    """Основная функция сбора eREIT статистики"""
    integration = EREITIntegration()
    results = await integration.collect_stats_for_active_placements()
    return results


if __name__ == "__main__":
    # Тестовый запуск
    async def test_ereit_integration():
        results = await collect_ereit_statistics()
        print(f"Результаты сбора eREIT статистики: {results}")
    
    asyncio.run(test_ereit_integration())