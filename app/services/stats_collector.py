#!/usr/bin/env python3
"""
Сервис сбора статистики постов через различные источники
"""

import logging
import asyncio
import aiohttp
import re
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class StatsCollector:
    """Сборщик статистики постов"""
    
    def __init__(self):
        self.session = None
        
    async def collect_placement_stats(self) -> List[Dict]:
        """Собирает статистику для всех активных размещений"""
        from app.models import execute_db_query
        
        # Получаем активные размещения
        active_placements = execute_db_query("""
            SELECT p.*, 
                   r.channel_username,
                   r.channel_title,
                   o.title as offer_title
            FROM offer_placements p
            JOIN offer_responses r ON p.response_id = r.id
            JOIN offers o ON r.offer_id = o.id
            WHERE p.status = 'active'
            AND p.post_url IS NOT NULL
        """, fetch_all=True)
        
        results = []
        
        async with aiohttp.ClientSession() as session:
            self.session = session
            
            for placement in active_placements:
                try:
                    logger.info(f"📊 Собираем статистику для размещения {placement['id']}")
                    
                    stats = await self.collect_post_stats(placement)
                    
                    if stats:
                        # Сохраняем статистику в БД
                        await self.save_stats_to_db(placement['id'], stats)
                        results.append({
                            'placement_id': placement['id'],
                            'stats': stats,
                            'status': 'success'
                        })
                    else:
                        results.append({
                            'placement_id': placement['id'],
                            'status': 'failed'
                        })
                        
                except Exception as e:
                    logger.error(f"❌ Ошибка сбора статистики для размещения {placement['id']}: {e}")
                    results.append({
                        'placement_id': placement['id'],
                        'status': 'error',
                        'error': str(e)
                    })
        
        return results
    
    async def collect_post_stats(self, placement: Dict) -> Optional[Dict]:
        """Собирает статистику конкретного поста"""
        post_url = placement.get('post_url')
        if not post_url:
            return None
            
        # Извлекаем информацию из URL
        url_info = self.parse_post_url(post_url)
        if not url_info:
            return None
            
        channel_username = url_info['channel']
        message_id = url_info['message_id']
        
        # Собираем статистику из разных источников
        stats = {
            'views': 0,
            'reactions': 0,
            'shares': 0,
            'comments': 0,
            'collected_at': datetime.now().isoformat(),
            'source': 'telegram_web'
        }
        
        # Получаем статистику через веб-интерфейс Telegram
        web_stats = await self.get_telegram_web_stats(channel_username, message_id)
        if web_stats:
            stats.update(web_stats)
        
        # Получаем дополнительную статистику через альтернативные источники
        alt_stats = await self.get_alternative_stats(channel_username, message_id)
        if alt_stats:
            # Объединяем статистику, приоритет у более свежих данных
            for key, value in alt_stats.items():
                if key in stats and value > stats[key]:
                    stats[key] = value
                elif key not in stats:
                    stats[key] = value
        
        return stats
    
    def parse_post_url(self, post_url: str) -> Optional[Dict]:
        """Парсит URL поста и извлекает канал и ID сообщения"""
        pattern = r'https://t\.me/([^/]+)/(\d+)'
        match = re.match(pattern, post_url)
        
        if match:
            return {
                'channel': match.group(1),
                'message_id': int(match.group(2))
            }
        return None
    
    async def get_telegram_web_stats(self, channel_username: str, message_id: int) -> Optional[Dict]:
        """Получает статистику через веб-интерфейс Telegram"""
        try:
            url = f"https://t.me/{channel_username}/{message_id}?embed=1"
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    return None
                
                html = await response.text()
                
                # Парсим HTML для извлечения статистики
                stats = self.parse_telegram_html_stats(html)
                return stats
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения веб-статистики для @{channel_username}/{message_id}: {e}")
            return None
    
    def parse_telegram_html_stats(self, html: str) -> Dict:
        """Парсит HTML страницы для извлечения статистики"""
        stats = {
            'views': 0,
            'reactions': 0,
            'shares': 0,
            'comments': 0
        }
        
        try:
            # Улучшенный поиск количества просмотров с различными форматами
            views_patterns = [
                r'(\d+(?:[\.,]\d+)?[KMB]?)\s*(?:views?|просмотр)',
                r'tgme_widget_message_views[^>]*>([^<]+)',
                r'message_views[^>]*>.*?(\d+(?:[\.,]\d+)?[KMB]?)',
                r'data-views="(\d+)"'
            ]
            
            for pattern in views_patterns:
                views_match = re.search(pattern, html, re.IGNORECASE)
                if views_match:
                    views_text = views_match.group(1).strip()
                    stats['views'] = self.parse_number_with_suffix(views_text)
                    break
            
            # Улучшенный поиск реакций
            reactions_patterns = [
                r'(\d+)\s*(?:reactions?|реакц)',
                r'tgme_widget_message_reactions[^>]*>.*?(\d+)',
                r'reactions_count[^>]*>(\d+)',
                r'emoji_button[^>]*>.*?(\d+)'
            ]
            
            for pattern in reactions_patterns:
                reactions_match = re.search(pattern, html, re.IGNORECASE)
                if reactions_match:
                    stats['reactions'] = int(reactions_match.group(1))
                    break
            
            # Улучшенный поиск репостов/пересылок
            shares_patterns = [
                r'(\d+)\s*(?:shares?|forwards?|репост|пересыл)',
                r'tgme_widget_message_forwarded[^>]*>.*?(\d+)',
                r'forwards_count[^>]*>(\d+)',
                r'share_button[^>]*>.*?(\d+)'
            ]
            
            for pattern in shares_patterns:
                shares_match = re.search(pattern, html, re.IGNORECASE)
                if shares_match:
                    stats['shares'] = int(shares_match.group(1))
                    break
            
            # Улучшенный поиск комментариев
            comments_patterns = [
                r'(\d+)\s*(?:comments?|коммент|ответ)',
                r'tgme_widget_message_reply[^>]*>.*?(\d+)',
                r'comments_count[^>]*>(\d+)',
                r'reply_button[^>]*>.*?(\d+)'
            ]
            
            for pattern in comments_patterns:
                comments_match = re.search(pattern, html, re.IGNORECASE)
                if comments_match:
                    stats['comments'] = int(comments_match.group(1))
                    break
            
            # Дополнительное извлечение из JSON-LD или meta-данных
            additional_stats = self.parse_metadata_stats(html)
            if additional_stats:
                for key, value in additional_stats.items():
                    if value > stats.get(key, 0):
                        stats[key] = value
                
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга HTML статистики: {e}")
        
        return stats
    
    def parse_metadata_stats(self, html: str) -> Dict:
        """Извлекает статистику из метаданных страницы"""
        stats = {}
        
        try:
            # Поиск JSON-LD данных
            json_ld_pattern = r'<script type="application/ld\+json">(.*?)</script>'
            json_matches = re.findall(json_ld_pattern, html, re.DOTALL)
            
            for json_text in json_matches:
                try:
                    data = json.loads(json_text)
                    if isinstance(data, dict):
                        # Ищем статистику в структурированных данных
                        if 'interactionStatistic' in data:
                            interaction_stats = data['interactionStatistic']
                            if isinstance(interaction_stats, list):
                                for stat in interaction_stats:
                                    if stat.get('@type') == 'InteractionCounter':
                                        interaction_type = stat.get('interactionType', {}).get('@type', '')
                                        count = stat.get('userInteractionCount', 0)
                                        
                                        if 'ViewAction' in interaction_type:
                                            stats['views'] = max(stats.get('views', 0), int(count))
                                        elif 'LikeAction' in interaction_type:
                                            stats['reactions'] = max(stats.get('reactions', 0), int(count))
                                        elif 'ShareAction' in interaction_type:
                                            stats['shares'] = max(stats.get('shares', 0), int(count))
                                        elif 'CommentAction' in interaction_type:
                                            stats['comments'] = max(stats.get('comments', 0), int(count))
                except json.JSONDecodeError:
                    continue
            
            # Поиск Open Graph метаданных
            og_patterns = {
                'views': r'<meta property="og:views" content="(\d+)"',
                'reactions': r'<meta property="og:reactions" content="(\d+)"',
                'shares': r'<meta property="og:shares" content="(\d+)"',
                'comments': r'<meta property="og:comments" content="(\d+)"'
            }
            
            for stat_type, pattern in og_patterns.items():
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    stats[stat_type] = max(stats.get(stat_type, 0), int(match.group(1)))
            
            # Поиск Twitter Card данных
            twitter_patterns = {
                'views': r'<meta name="twitter:views" content="(\d+)"',
                'reactions': r'<meta name="twitter:reactions" content="(\d+)"'
            }
            
            for stat_type, pattern in twitter_patterns.items():
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    stats[stat_type] = max(stats.get(stat_type, 0), int(match.group(1)))
                    
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга метаданных: {e}")
        
        return stats
    
    def parse_number_with_suffix(self, number_str: str) -> int:
        """Парсит числа с суффиксами K, M, B"""
        number_str = number_str.upper().strip()
        
        if number_str.endswith('K'):
            return int(float(number_str[:-1]) * 1000)
        elif number_str.endswith('M'):
            return int(float(number_str[:-1]) * 1000000)
        elif number_str.endswith('B'):
            return int(float(number_str[:-1]) * 1000000000)
        else:
            return int(float(number_str))
    
    async def get_alternative_stats(self, channel_username: str, message_id: int) -> Optional[Dict]:
        """Получает статистику из альтернативных источников"""
        # Здесь можно добавить интеграцию с другими сервисами аналитики
        # Например, TGStat, Telemetr, собственные парсеры и т.д.
        
        stats = {}
        
        # Пример получения статистики через TGStat API (если доступен)
        tgstat_stats = await self.get_tgstat_stats(channel_username, message_id)
        if tgstat_stats:
            stats.update(tgstat_stats)
        
        return stats if stats else None
    
    async def get_tgstat_stats(self, channel_username: str, message_id: int) -> Optional[Dict]:
        """Получает статистику через TGStat API (пример)"""
        try:
            # Это пример - в реальности нужен API ключ и правильные эндпоинты
            # url = f"https://api.tgstat.ru/channels/posts?channel={channel_username}&message_id={message_id}"
            # headers = {'Authorization': 'Bearer YOUR_API_KEY'}
            
            # async with self.session.get(url, headers=headers) as response:
            #     if response.status == 200:
            #         data = await response.json()
            #         return self.parse_tgstat_response(data)
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения TGStat статистики: {e}")
            return None
    
    async def save_stats_to_db(self, placement_id: int, stats: Dict):
        """Сохраняет статистику в базу данных"""
        from app.models import execute_db_query
        
        try:
            # Создаем запись статистики
            execute_db_query("""
                INSERT INTO placement_statistics (
                    placement_id,
                    views_count,
                    reactions_count,
                    shares_count,
                    comments_count,
                    collected_at,
                    source,
                    raw_data,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                placement_id,
                stats.get('views', 0),
                stats.get('reactions', 0),
                stats.get('shares', 0),
                stats.get('comments', 0),
                stats.get('collected_at'),
                stats.get('source', 'unknown'),
                json.dumps(stats)
            ))
            
            logger.info(f"✅ Статистика сохранена для размещения {placement_id}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения статистики для размещения {placement_id}: {e}")
    
    async def calculate_performance_metrics(self, placement_id: int) -> Dict:
        """Вычисляет метрики эффективности размещения"""
        from app.models import execute_db_query
        
        # Получаем всю статистику для размещения
        stats_history = execute_db_query("""
            SELECT * FROM placement_statistics 
            WHERE placement_id = ?
            ORDER BY collected_at ASC
        """, (placement_id,), fetch_all=True)
        
        if not stats_history:
            return {}
        
        latest_stats = stats_history[-1]
        first_stats = stats_history[0]
        
        # Получаем информацию о размещении
        placement_info = execute_db_query("""
            SELECT p.*, r.channel_subscribers, o.price
            FROM offer_placements p
            JOIN offer_responses r ON p.response_id = r.id
            JOIN offers o ON r.offer_id = o.id
            WHERE p.id = ?
        """, (placement_id,), fetch_one=True)
        
        if not placement_info:
            return {}
        
        # Вычисляем метрики
        total_views = latest_stats['views_count']
        total_reactions = latest_stats['reactions_count']
        total_shares = latest_stats['shares_count']
        channel_subscribers = placement_info['channel_subscribers'] or 1
        cost = placement_info['price'] or placement_info['funds_reserved'] or 0
        
        metrics = {
            'total_views': total_views,
            'total_reactions': total_reactions,
            'total_shares': total_shares,
            'reach_percentage': round((total_views / channel_subscribers) * 100, 2) if channel_subscribers > 0 else 0,
            'engagement_rate': round((total_reactions / total_views) * 100, 2) if total_views > 0 else 0,
            'cpm': round((cost / total_views) * 1000, 2) if total_views > 0 else 0,  # Cost per mille
            'cost_per_reaction': round(cost / total_reactions, 2) if total_reactions > 0 else 0,
            'viral_coefficient': round(total_shares / total_views, 4) if total_views > 0 else 0,
            'calculated_at': datetime.now().isoformat()
        }
        
        return metrics


# Создаем таблицу для статистики, если её нет
def create_stats_tables():
    """Создает таблицы для хранения статистики"""
    from app.models import execute_db_query
    
    # Таблица статистики размещений
    execute_db_query("""
        CREATE TABLE IF NOT EXISTS placement_statistics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            placement_id INTEGER NOT NULL,
            views_count INTEGER DEFAULT 0,
            reactions_count INTEGER DEFAULT 0,
            shares_count INTEGER DEFAULT 0,
            comments_count INTEGER DEFAULT 0,
            collected_at TIMESTAMP,
            source TEXT DEFAULT 'unknown',
            raw_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (placement_id) REFERENCES offer_placements(id)
        )
    """)
    
    # Индекс для быстрого поиска
    execute_db_query("""
        CREATE INDEX IF NOT EXISTS idx_placement_stats_placement_id 
        ON placement_statistics(placement_id)
    """)
    
    # Индекс по времени сбора
    execute_db_query("""
        CREATE INDEX IF NOT EXISTS idx_placement_stats_collected_at 
        ON placement_statistics(collected_at)
    """)


if __name__ == "__main__":
    # Создаем таблицы при первом запуске
    create_stats_tables()
    
    # Тестовый запуск
    async def test_stats_collection():
        collector = StatsCollector()
        results = await collector.collect_placement_stats()
        print(f"Результаты сбора статистики: {results}")
    
    asyncio.run(test_stats_collection())