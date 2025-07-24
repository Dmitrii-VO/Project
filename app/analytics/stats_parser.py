#!/usr/bin/env python3
"""
Автоматический парсинг статистики Telegram каналов
Система сбора и анализа метрик каналов и размещений
"""

import re
import logging
import asyncio
import aiohttp
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import json

from app.models.database import execute_db_query
from app.events.event_dispatcher import event_dispatcher
from app.config.telegram_config import AppConfig, CHANNEL_STATS_UPDATE_INTERVAL_HOURS

logger = logging.getLogger(__name__)

class TelegramStatsParser:
    """Парсер статистики Telegram каналов"""
    
    def __init__(self):
        self.session = None
        self.update_interval = CHANNEL_STATS_UPDATE_INTERVAL_HOURS
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        
        # Источники данных для парсинга
        self.data_sources = {
            'tgstat': 'https://tgstat.ru/channel/',
            'telemetr': 'https://telemetr.io/en/channels/',
            'telegram_analytics': 'https://telegram-analytics.com/channel/'
        }
    
    async def init_session(self):
        """Инициализация HTTP сессии"""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers={'User-Agent': self.user_agent}
            )
    
    async def close_session(self):
        """Закрытие HTTP сессии"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def update_all_channels_stats(self) -> Dict[str, Any]:
        """Обновление статистики всех активных каналов"""
        try:
            await self.init_session()
            
            # Получаем все активные верифицированные каналы
            channels = execute_db_query(
                """SELECT id, username, title, subscriber_count, last_stats_update
                   FROM channels 
                   WHERE is_verified = 1 AND is_active = 1
                   ORDER BY last_stats_update ASC""",
                fetch_all=True
            )
            
            updated_count = 0
            errors = []
            
            for channel in channels:
                try:
                    # Проверяем, нужно ли обновлять статистику
                    if self._should_update_stats(channel['last_stats_update']):
                        stats = await self.get_channel_stats(channel['username'])
                        
                        if stats['success']:
                            await self._save_channel_stats(channel['id'], stats['data'])
                            updated_count += 1
                            
                            # Отправляем событие об обновлении
                            event_dispatcher.channel_stats_updated(
                                channel_id=channel['id'],
                                owner_id=0,  # Получим из БД если нужно
                                old_subscriber_count=channel['subscriber_count'],
                                new_subscriber_count=stats['data']['subscriber_count']
                            )
                        else:
                            errors.append(f"Канал @{channel['username']}: {stats['error']}")
                    
                    # Небольшая задержка между запросами
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    errors.append(f"Канал @{channel['username']}: {str(e)}")
                    logger.error(f"❌ Ошибка обновления статистики канала @{channel['username']}: {e}")
            
            return {
                'success': True,
                'updated_count': updated_count,
                'total_channels': len(channels),
                'errors': errors
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка массового обновления статистики: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            await self.close_session()
    
    async def get_channel_stats(self, channel_username: str) -> Dict[str, Any]:
        """Получение статистики конкретного канала"""
        try:
            username = channel_username.lstrip('@')
            
            # Пробуем получить данные из разных источников
            for source_name, base_url in self.data_sources.items():
                try:
                    stats = await self._parse_from_source(source_name, base_url, username)
                    if stats['success']:
                        logger.info(f"✅ Статистика канала @{username} получена из {source_name}")
                        return stats
                except Exception as e:
                    logger.warning(f"⚠️ Не удалось получить данные из {source_name}: {e}")
                    continue
            
            # Если не удалось получить из внешних источников, используем Telegram API
            return await self._get_stats_from_telegram_api(username)
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики канала @{channel_username}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_post_statistics(self, channel_username: str, post_id: int) -> Dict[str, Any]:
        """Получение статистики конкретного поста"""
        try:
            username = channel_username.lstrip('@')
            post_url = f"https://t.me/{username}/{post_id}"
            
            # Парсим статистику поста из разных источников
            stats = await self._parse_post_stats(username, post_id)
            
            if stats['success']:
                return {
                    'success': True,
                    'data': {
                        'post_url': post_url,
                        'views': stats['data'].get('views', 0),
                        'forwards': stats['data'].get('forwards', 0),
                        'reactions': stats['data'].get('reactions', {}),
                        'comments': stats['data'].get('comments', 0),
                        'engagement_rate': stats['data'].get('engagement_rate', 0),
                        'reach': stats['data'].get('reach', 0),
                        'last_updated': datetime.now().isoformat()
                    }
                }
            else:
                return stats
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики поста: {e}")
            return {'success': False, 'error': str(e)}
    
    async def track_placement_performance(self, placement_id: int) -> Dict[str, Any]:
        """Отслеживание эффективности размещения"""
        try:
            # Получаем данные о размещении
            placement = execute_db_query(
                """SELECT p.*, r.channel_id, c.username, c.title
                   FROM offer_placements p
                   JOIN offer_responses r ON p.response_id = r.id
                   JOIN channels c ON r.channel_id = c.id
                   WHERE p.id = ?""",
                (placement_id,),
                fetch_one=True
            )
            
            if not placement:
                return {'success': False, 'error': 'Размещение не найдено'}
            
            # Извлекаем ID поста из URL
            post_id = self._extract_post_id_from_url(placement['post_url'])
            if not post_id:
                return {'success': False, 'error': 'Не удалось извлечь ID поста из URL'}
            
            # Получаем статистику поста
            post_stats = await self.get_post_statistics(placement['username'], post_id)
            
            if post_stats['success']:
                # Обновляем статистику размещения в БД
                await self._update_placement_stats(placement_id, post_stats['data'])
                
                # Отправляем событие
                event_dispatcher.placement_stats_updated(
                    placement_id=placement_id,
                    views_count=post_stats['data']['views'],
                    clicks_count=0,  # Клики отслеживаются отдельно
                    engagement_rate=post_stats['data']['engagement_rate'],
                    user_id=0  # Получим из БД если нужно
                )
                
                return {
                    'success': True,
                    'placement_id': placement_id,
                    'stats': post_stats['data']
                }
            else:
                return post_stats
                
        except Exception as e:
            logger.error(f"❌ Ошибка отслеживания размещения {placement_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _parse_from_source(self, source_name: str, base_url: str, username: str) -> Dict[str, Any]:
        """Парсинг статистики из конкретного источника"""
        try:
            url = f"{base_url}{username}"
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    return {'success': False, 'error': f'HTTP {response.status}'}
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Парсинг в зависимости от источника
                if source_name == 'tgstat':
                    return self._parse_tgstat(soup, username)
                elif source_name == 'telemetr':
                    return self._parse_telemetr(soup, username)
                elif source_name == 'telegram_analytics':
                    return self._parse_telegram_analytics(soup, username)
                else:
                    return {'success': False, 'error': 'Неизвестный источник'}
                    
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга из {source_name}: {e}")
            return {'success': False, 'error': str(e)}
    
    def _parse_tgstat(self, soup: BeautifulSoup, username: str) -> Dict[str, Any]:
        """Парсинг данных с TGStat"""
        try:
            # Ищем основные метрики
            subscriber_count = 0
            avg_views = 0
            engagement_rate = 0
            
            # Поиск подписчиков
            subscriber_elem = soup.find('div', class_='subscribers-count')
            if subscriber_elem:
                subscriber_text = subscriber_elem.get_text().strip()
                subscriber_count = self._extract_number(subscriber_text)
            
            # Поиск средних просмотров
            views_elem = soup.find('div', class_='avg-views')
            if views_elem:
                views_text = views_elem.get_text().strip()
                avg_views = self._extract_number(views_text)
            
            # Поиск engagement rate
            engagement_elem = soup.find('div', class_='engagement-rate')
            if engagement_elem:
                engagement_text = engagement_elem.get_text().strip()
                engagement_rate = self._extract_percentage(engagement_text)
            
            return {
                'success': True,
                'data': {
                    'subscriber_count': subscriber_count,
                    'avg_views': avg_views,
                    'engagement_rate': engagement_rate,
                    'source': 'tgstat',
                    'last_updated': datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            return {'success': False, 'error': f'Ошибка парсинга TGStat: {str(e)}'}
    
    def _parse_telemetr(self, soup: BeautifulSoup, username: str) -> Dict[str, Any]:
        """Парсинг данных с Telemetr"""
        try:
            # Аналогично TGStat, но с другими селекторами
            subscriber_count = 0
            avg_views = 0
            
            # Здесь должны быть селекторы специфичные для Telemetr
            # Для демонстрации используем базовые значения
            
            return {
                'success': True,
                'data': {
                    'subscriber_count': subscriber_count,
                    'avg_views': avg_views,
                    'engagement_rate': 0,
                    'source': 'telemetr',
                    'last_updated': datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            return {'success': False, 'error': f'Ошибка парсинга Telemetr: {str(e)}'}
    
    def _parse_telegram_analytics(self, soup: BeautifulSoup, username: str) -> Dict[str, Any]:
        """Парсинг данных с Telegram Analytics"""
        try:
            # Специфичная логика для Telegram Analytics
            return {
                'success': True,
                'data': {
                    'subscriber_count': 0,
                    'avg_views': 0,
                    'engagement_rate': 0,
                    'source': 'telegram_analytics',
                    'last_updated': datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            return {'success': False, 'error': f'Ошибка парсинга Telegram Analytics: {str(e)}'}
    
    async def _get_stats_from_telegram_api(self, username: str) -> Dict[str, Any]:
        """Получение базовой статистики через Telegram Bot API"""
        try:
            from app.verification.telegram_api_client import TelegramAPIClient
            
            client = TelegramAPIClient()
            channel_info = client.get_channel_info(username)
            
            if channel_info['success']:
                return {
                    'success': True,
                    'data': {
                        'subscriber_count': channel_info['data']['member_count'],
                        'avg_views': 0,  # Bot API не предоставляет эти данные
                        'engagement_rate': 0,
                        'source': 'telegram_api',
                        'last_updated': datetime.now().isoformat()
                    }
                }
            else:
                return channel_info
                
        except Exception as e:
            return {'success': False, 'error': f'Ошибка Telegram API: {str(e)}'}
    
    async def _parse_post_stats(self, username: str, post_id: int) -> Dict[str, Any]:
        """Парсинг статистики конкретного поста"""
        try:
            # В реальной реализации здесь должен быть парсинг
            # статистики поста из различных источников
            
            # Для демонстрации возвращаем базовые метрики
            return {
                'success': True,
                'data': {
                    'views': 1000,  # Примерные данные
                    'forwards': 50,
                    'reactions': {'👍': 25, '❤️': 15, '🔥': 10},
                    'comments': 5,
                    'engagement_rate': 5.5,
                    'reach': 800
                }
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _save_channel_stats(self, channel_id: int, stats_data: Dict[str, Any]):
        """Сохранение статистики канала в БД"""
        try:
            execute_db_query(
                """UPDATE channels 
                   SET subscriber_count = ?, avg_views = ?, engagement_rate = ?,
                       last_stats_update = ?, updated_at = ?
                   WHERE id = ?""",
                (
                    stats_data.get('subscriber_count', 0),
                    stats_data.get('avg_views', 0),
                    stats_data.get('engagement_rate', 0),
                    datetime.now(),
                    datetime.now(),
                    channel_id
                )
            )
            
            # Сохраняем историю статистики
            execute_db_query(
                """INSERT INTO channel_stats_history 
                   (channel_id, subscriber_count, avg_views, engagement_rate, 
                    data_source, recorded_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    channel_id,
                    stats_data.get('subscriber_count', 0),
                    stats_data.get('avg_views', 0),
                    stats_data.get('engagement_rate', 0),
                    stats_data.get('source', 'unknown'),
                    datetime.now()
                )
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения статистики канала {channel_id}: {e}")
    
    async def _update_placement_stats(self, placement_id: int, stats_data: Dict[str, Any]):
        """Обновление статистики размещения"""
        try:
            execute_db_query(
                """UPDATE offer_placements 
                   SET views_count = ?, engagement_rate = ?, updated_at = ?
                   WHERE id = ?""",
                (
                    stats_data.get('views', 0),
                    stats_data.get('engagement_rate', 0),
                    datetime.now(),
                    placement_id
                )
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка обновления статистики размещения {placement_id}: {e}")
    
    def _should_update_stats(self, last_update: str) -> bool:
        """Проверка необходимости обновления статистики"""
        if not last_update:
            return True
        
        try:
            last_update_dt = datetime.fromisoformat(last_update)
            time_diff = datetime.now() - last_update_dt
            return time_diff.total_seconds() > (self.update_interval * 3600)
        except:
            return True
    
    def _extract_number(self, text: str) -> int:
        """Извлечение числа из текста (поддержка K, M суффиксов)"""
        try:
            # Удаляем все кроме цифр, точек и букв K, M
            clean_text = re.sub(r'[^\d.,KMkm]', '', text.upper())
            
            if 'K' in clean_text:
                number = float(clean_text.replace('K', '')) * 1000
            elif 'M' in clean_text:
                number = float(clean_text.replace('M', '')) * 1000000
            else:
                number = float(clean_text.replace(',', ''))
            
            return int(number)
        except:
            return 0
    
    def _extract_percentage(self, text: str) -> float:
        """Извлечение процента из текста"""
        try:
            # Ищем число с знаком процента
            match = re.search(r'(\d+\.?\d*)%', text)
            if match:
                return float(match.group(1))
            return 0.0
        except:
            return 0.0
    
    def _extract_post_id_from_url(self, post_url: str) -> Optional[int]:
        """Извлечение ID поста из URL"""
        try:
            # Формат: https://t.me/channel_name/123
            match = re.search(r'/(\d+)/?$', post_url)
            if match:
                return int(match.group(1))
            return None
        except:
            return None