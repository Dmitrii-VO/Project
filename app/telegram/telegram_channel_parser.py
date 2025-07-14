#!/usr/bin/env python3
"""
Парсер каналов Telegram и проверка постов
Система автоматического мониторинга размещений
"""

import sqlite3
import requests
import json
import re
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
import os
import sys
from urllib.parse import urlparse, parse_qs


# Добавляем путь для импорта
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.telegram_config import AppConfig

# Настройка логирования
logger = logging.getLogger(__name__)

class CheckResult(Enum):
    """Результаты проверки поста"""
    SUCCESS = "success"
    NOT_FOUND = "not_found"
    ACCESS_DENIED = "access_denied"
    CHANNEL_NOT_FOUND = "channel_not_found"
    INVALID_URL = "invalid_url"
    NETWORK_ERROR = "network_error"
    RATE_LIMITED = "rate_limited"
    UNKNOWN_ERROR = "unknown_error"

@dataclass
class PostCheckResult:
    """Результат проверки поста"""
    result: CheckResult
    post_exists: bool
    views_count: int
    post_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    check_time: datetime = None
    
    def __post_init__(self):
        if self.check_time is None:
            self.check_time = datetime.now()

@dataclass
class ChannelInfo:
    """Информация о канале"""
    id: str
    title: str
    username: str
    description: str
    subscriber_count: int
    is_public: bool
    is_accessible: bool
    last_post_date: Optional[datetime] = None

class TelegramChannelParser:
    """Основной класс для парсинга каналов Telegram"""
    
    def __init__(self):
        self.bot_token = self._get_bot_token()
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}" if self.bot_token else None
        self.db_path = getattr(AppConfig, 'DATABASE_PATH', 'telegram_mini_app.db')
        self.session = None
        self.rate_limit_delay = 1.0  # Задержка между запросами
        self.max_retries = 3
        
    def _get_bot_token(self) -> Optional[str]:
        """Получение токена бота"""
        try:
            return AppConfig.BOT_TOKEN
        except:
            return os.environ.get('BOT_TOKEN')
    
    def get_db_connection(self):
        """Получение соединения с базой данных"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            logger.error(f"Ошибка подключения к БД: {e}")
            return None
    
    def parse_telegram_url(self, url: str) -> Optional[Dict[str, str]]:
        """Парсинг URL Telegram поста или канала"""
        try:
            # Паттерны для различных форматов URL
            patterns = [
                # https://t.me/channel_name/123
                r'https://t\.me/([^/]+)/(\d+)',
                # https://t.me/c/1234567890/123 (приватные каналы)
                r'https://t\.me/c/(-?\d+)/(\d+)',
                # https://telegram.me/channel_name/123
                r'https://telegram\.me/([^/]+)/(\d+)'
            ]
            
            for pattern in patterns:
                match = re.match(pattern, url)
                if match:
                    channel_identifier = match.group(1)
                    message_id = match.group(2)
                    
                    # Определяем тип канала
                    if channel_identifier.startswith('-'):
                        # Приватный канал (chat_id)
                        return {
                            'type': 'private',
                            'chat_id': channel_identifier,
                            'message_id': message_id,
                            'url': url,
                            'is_valid': True
                        }
                    else:
                        # Публичный канал (username)
                        return {
                            'type': 'public',
                            'username': channel_identifier,
                            'chat_id': f"@{channel_identifier}",
                            'message_id': message_id,
                            'url': url,
                            'is_valid': True
                        }
            
            return {'is_valid': False, 'error': 'Invalid URL format'}
            
        except Exception as e:
            logger.error(f"Ошибка парсинга URL: {e}")
            return {'is_valid': False, 'error': str(e)}
    
    def check_channel_access(self, chat_id: str) -> Tuple[bool, Optional[ChannelInfo]]:
        """Проверка доступа к каналу"""
        try:
            if not self.bot_token:
                return False, None
            
            # Получаем информацию о канале
            url = f"{self.base_url}/getChat"
            params = {'chat_id': chat_id}
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('ok'):
                    chat_info = data['result']
                    
                    # Формируем информацию о канале
                    channel_info = ChannelInfo(
                        id=str(chat_info['id']),
                        title=chat_info.get('title', ''),
                        username=chat_info.get('username', ''),
                        description=chat_info.get('description', ''),
                        subscriber_count=chat_info.get('member_count', 0),
                        is_public=chat_info.get('username') is not None,
                        is_accessible=True
                    )
                    
                    return True, channel_info
                else:
                    error_code = data.get('error_code', 0)
                    error_description = data.get('description', '')
                    
                    logger.warning(f"Канал недоступен: {error_code} - {error_description}")
                    return False, None
            else:
                logger.error(f"HTTP error {response.status_code}: {response.text}")
                return False, None
                
        except Exception as e:
            logger.error(f"Ошибка проверки доступа к каналу: {e}")
            return False, None
    
    def check_post_exists(self, url: str) -> PostCheckResult:
        """Проверка существования поста"""
        try:
            # Парсим URL
            parsed_url = self.parse_telegram_url(url)
            if not parsed_url.get('is_valid'):
                return PostCheckResult(
                    result=CheckResult.INVALID_URL,
                    post_exists=False,
                    views_count=0,
                    error_message=parsed_url.get('error', 'Invalid URL')
                )
            
            chat_id = parsed_url['chat_id']
            message_id = parsed_url['message_id']
            
            # Метод 1: Попытка получить сообщение через Bot API
            post_result = self._check_post_via_bot_api(chat_id, message_id)
            
            if post_result.result == CheckResult.SUCCESS:
                return post_result
            
            # Метод 2: Веб-скрейпинг (если Bot API не работает)
            if parsed_url['type'] == 'public':
                web_result = self._check_post_via_web_scraping(parsed_url['username'], message_id)
                if web_result.result == CheckResult.SUCCESS:
                    return web_result
            
            # Метод 3: Проверка через embed
            embed_result = self._check_post_via_embed(url)
            if embed_result.result == CheckResult.SUCCESS:
                return embed_result
            
            # Если все методы не сработали, возвращаем последний результат
            return post_result
            
        except Exception as e:
            logger.error(f"Ошибка проверки поста: {e}")
            return PostCheckResult(
                result=CheckResult.UNKNOWN_ERROR,
                post_exists=False,
                views_count=0,
                error_message=str(e)
            )
    
    def _check_post_via_bot_api(self, chat_id: str, message_id: str) -> PostCheckResult:
        """Проверка поста через Telegram Bot API"""
        try:
            if not self.bot_token:
                return PostCheckResult(
                    result=CheckResult.ACCESS_DENIED,
                    post_exists=False,
                    views_count=0,
                    error_message="Bot token not configured"
                )
            
            # Пробуем получить сообщение
            url = f"{self.base_url}/forwardMessage"
            params = {
                'chat_id': chat_id,  # Пробуем переслать в тот же чат
                'from_chat_id': chat_id,
                'message_id': message_id
            }
            
            response = requests.post(url, json=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('ok'):
                    # Сообщение существует
                    message_data = data['result']
                    
                    # Пытаемся извлечь количество просмотров
                    views_count = self._extract_views_count(message_data)
                    
                    return PostCheckResult(
                        result=CheckResult.SUCCESS,
                        post_exists=True,
                        views_count=views_count,
                        post_data=message_data
                    )
                else:
                    error_code = data.get('error_code', 0)
                    error_description = data.get('description', '')
                    
                    if error_code == 400 and 'message not found' in error_description.lower():
                        return PostCheckResult(
                            result=CheckResult.NOT_FOUND,
                            post_exists=False,
                            views_count=0,
                            error_message=error_description
                        )
                    elif error_code == 403:
                        return PostCheckResult(
                            result=CheckResult.ACCESS_DENIED,
                            post_exists=False,
                            views_count=0,
                            error_message=error_description
                        )
                    else:
                        return PostCheckResult(
                            result=CheckResult.UNKNOWN_ERROR,
                            post_exists=False,
                            views_count=0,
                            error_message=error_description
                        )
            else:
                return PostCheckResult(
                    result=CheckResult.NETWORK_ERROR,
                    post_exists=False,
                    views_count=0,
                    error_message=f"HTTP {response.status_code}"
                )
                
        except Exception as e:
            logger.error(f"Ошибка Bot API проверки: {e}")
            return PostCheckResult(
                result=CheckResult.UNKNOWN_ERROR,
                post_exists=False,
                views_count=0,
                error_message=str(e)
            )
    
    def _check_post_via_web_scraping(self, username: str, message_id: str) -> PostCheckResult:
        """Проверка поста через веб-скрейпинг"""
        try:
            # Формируем URL для предпросмотра
            preview_url = f"https://t.me/{username}/{message_id}?embed=1"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(preview_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                content = response.text
                
                # Проверяем наличие сообщения
                if 'tgme_widget_message' in content:
                    # Пытаемся извлечь количество просмотров
                    views_count = self._extract_views_from_html(content)
                    
                    return PostCheckResult(
                        result=CheckResult.SUCCESS,
                        post_exists=True,
                        views_count=views_count,
                        post_data={'method': 'web_scraping', 'url': preview_url}
                    )
                else:
                    return PostCheckResult(
                        result=CheckResult.NOT_FOUND,
                        post_exists=False,
                        views_count=0,
                        error_message="Message not found in HTML"
                    )
            else:
                return PostCheckResult(
                    result=CheckResult.NETWORK_ERROR,
                    post_exists=False,
                    views_count=0,
                    error_message=f"HTTP {response.status_code}"
                )
                
        except Exception as e:
            logger.error(f"Ошибка веб-скрейпинга: {e}")
            return PostCheckResult(
                result=CheckResult.UNKNOWN_ERROR,
                post_exists=False,
                views_count=0,
                error_message=str(e)
            )
    
    def _check_post_via_embed(self, url: str) -> PostCheckResult:
        """Проверка поста через embed API"""
        try:
            # Используем oEmbed для проверки
            embed_url = f"https://publish.twitter.com/oembed?url={url}"
            
            response = requests.get(embed_url, timeout=10)
            
            if response.status_code == 200:
                return PostCheckResult(
                    result=CheckResult.SUCCESS,
                    post_exists=True,
                    views_count=0,  # Embed не предоставляет просмотры
                    post_data={'method': 'embed', 'url': url}
                )
            else:
                return PostCheckResult(
                    result=CheckResult.NOT_FOUND,
                    post_exists=False,
                    views_count=0,
                    error_message="Embed not available"
                )
                
        except Exception as e:
            logger.error(f"Ошибка embed проверки: {e}")
            return PostCheckResult(
                result=CheckResult.UNKNOWN_ERROR,
                post_exists=False,
                views_count=0,
                error_message=str(e)
            )
    
    def _extract_views_count(self, message_data: Dict[str, Any]) -> int:
        """Извлечение количества просмотров из данных сообщения"""
        try:
            # Telegram Bot API не предоставляет просмотры напрямую
            # Возвращаем 0 как заглушку
            return 0
        except Exception as e:
            logger.error(f"Ошибка извлечения просмотров: {e}")
            return 0
    
    def _extract_views_from_html(self, html_content: str) -> int:
        """Извлечение количества просмотров из HTML"""
        try:
            # Ищем паттерн для просмотров
            patterns = [
                r'<span class="tgme_widget_message_views">(\d+(?:\.\d+)?[KM]?)</span>',
                r'data-views="(\d+)"',
                r'(\d+(?:\.\d+)?[KM]?)\s*views?'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, html_content, re.IGNORECASE)
                if match:
                    views_str = match.group(1)
                    return self._parse_views_string(views_str)
            
            return 0
            
        except Exception as e:
            logger.error(f"Ошибка извлечения просмотров из HTML: {e}")
            return 0
    
    def _parse_views_string(self, views_str: str) -> int:
        """Парсинг строки с количеством просмотров (например, '1.2K' -> 1200)"""
        try:
            views_str = views_str.strip().upper()
            
            if views_str.endswith('K'):
                return int(float(views_str[:-1]) * 1000)
            elif views_str.endswith('M'):
                return int(float(views_str[:-1]) * 1000000)
            else:
                return int(float(views_str))
                
        except Exception as e:
            logger.error(f"Ошибка парсинга просмотров: {e}")
            return 0
    
    def check_multiple_posts(self, urls: List[str]) -> List[PostCheckResult]:
        """Проверка нескольких постов с задержкой"""
        results = []
        
        for i, url in enumerate(urls):
            result = self.check_post_exists(url)
            results.append(result)
            
            # Задержка между запросами
            if i < len(urls) - 1:
                time.sleep(self.rate_limit_delay)
        
        return results
    
    def save_check_result(self, placement_id: int, result: PostCheckResult):
        """Сохранение результата проверки в базу данных"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return
            
            cursor = conn.cursor()
            
            # Сохраняем результат проверки
            cursor.execute("""
                INSERT INTO placement_checks (
                    placement_id, check_time, post_exists, views_count,
                    check_status, error_message, response_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                placement_id,
                result.check_time.isoformat(),
                1 if result.post_exists else 0,
                result.views_count,
                result.result.value,
                result.error_message,
                json.dumps(result.post_data) if result.post_data else None
            ))
            
            # Обновляем статус размещения
            if result.result == CheckResult.SUCCESS:
                if result.post_exists:
                    # Пост существует, обновляем количество просмотров
                    cursor.execute("""
                        UPDATE offer_placements 
                        SET final_views_count = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (result.views_count, placement_id))
                else:
                    # Пост не найден, помечаем как неудачное размещение
                    cursor.execute("""
                        UPDATE offer_placements 
                        SET status = 'failed', placement_end = CURRENT_TIMESTAMP,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (placement_id,))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Ошибка сохранения результата проверки: {e}")

# ================================================================
# ПЛАНИРОВЩИК ПРОВЕРОК
# ================================================================

class PlacementMonitor:
    """Планировщик для автоматических проверок размещений"""
    
    def __init__(self):
        self.parser = TelegramChannelParser()
        self.db_path = self.parser.db_path
    
    def get_active_placements(self) -> List[Dict[str, Any]]:
        """Получение активных размещений для проверки"""
        try:
            conn = self.parser.get_db_connection()
            if not conn:
                return []
            
            cursor = conn.cursor()
            
            # Получаем размещения, которые нужно проверить
            cursor.execute("""
                SELECT 
                    opl.id, opl.post_url, opl.placement_start, opl.expected_duration,
                    opl.status, opl.updated_at,
                    -- Информация о последней проверке
                    pc.check_time as last_check_time,
                    pc.check_status as last_check_status
                FROM offer_placements opl
                LEFT JOIN (
                    SELECT placement_id, check_time, check_status,
                           ROW_NUMBER() OVER (PARTITION BY placement_id ORDER BY check_time DESC) as rn
                    FROM placement_checks
                ) pc ON opl.id = pc.placement_id AND pc.rn = 1
                WHERE opl.status IN ('placed', 'monitoring')
                AND opl.post_url IS NOT NULL
                AND (
                    pc.check_time IS NULL OR 
                    pc.check_time < datetime('now', '-1 hour')
                )
                ORDER BY opl.placement_start ASC
            """)
            
            results = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Ошибка получения активных размещений: {e}")
            return []
    
    def check_placement(self, placement_id: int, post_url: str) -> bool:
        """Проверка одного размещения"""
        try:
            logger.info(f"Проверка размещения {placement_id}: {post_url}")
            
            result = self.parser.check_post_exists(post_url)
            self.parser.save_check_result(placement_id, result)
            
            # Логируем результат
            if result.result == CheckResult.SUCCESS:
                if result.post_exists:
                    logger.info(f"✅ Размещение {placement_id}: пост найден, {result.views_count} просмотров")
                else:
                    logger.warning(f"⚠️ Размещение {placement_id}: пост не найден")
            else:
                logger.error(f"❌ Размещение {placement_id}: ошибка - {result.error_message}")
            
            return result.result == CheckResult.SUCCESS
            
        except Exception as e:
            logger.error(f"Ошибка проверки размещения {placement_id}: {e}")
            return False
    
    def run_monitoring_cycle(self) -> Dict[str, int]:
        """Запуск цикла мониторинга"""
        try:
            active_placements = self.get_active_placements()
            
            if not active_placements:
                logger.info("Нет активных размещений для проверки")
                return {'checked': 0, 'success': 0, 'failed': 0}
            
            logger.info(f"Начинаем проверку {len(active_placements)} размещений")
            
            checked = 0
            success = 0
            failed = 0
            
            for placement in active_placements:
                try:
                    if self.check_placement(placement['id'], placement['post_url']):
                        success += 1
                    else:
                        failed += 1
                    
                    checked += 1
                    
                    # Задержка между проверками
                    time.sleep(self.parser.rate_limit_delay)
                    
                except Exception as e:
                    logger.error(f"Ошибка при проверке размещения {placement['id']}: {e}")
                    failed += 1
                    checked += 1
            
            logger.info(f"Цикл мониторинга завершен: {checked} проверено, {success} успешно, {failed} ошибок")
            
            return {'checked': checked, 'success': success, 'failed': failed}
            
        except Exception as e:
            logger.error(f"Ошибка цикла мониторинга: {e}")
            return {'checked': 0, 'success': 0, 'failed': 1}
    
    def cleanup_old_checks(self, days_old: int = 30):
        """Очистка старых записей проверок"""
        try:
            conn = self.parser.get_db_connection()
            if not conn:
                return
            
            cursor = conn.cursor()
            
            # Удаляем записи старше указанного количества дней
            cursor.execute("""
                DELETE FROM placement_checks 
                WHERE check_time < datetime('now', '-{} days')
            """.format(days_old))
            
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            logger.info(f"Удалено {deleted_count} старых записей проверок")
            
        except Exception as e:
            logger.error(f"Ошибка очистки старых проверок: {e}")

# ================================================================
# UTILITY FUNCTIONS
# ================================================================

def check_single_post(url: str) -> Dict[str, Any]:
    """Проверка одного поста (для API)"""
    parser = TelegramChannelParser()
    result = parser.check_post_exists(url)
    
    return {
        'success': result.result == CheckResult.SUCCESS,
        'post_exists': result.post_exists,
        'views_count': result.views_count,
        'check_status': result.result.value,
        'error_message': result.error_message,
        'check_time': result.check_time.isoformat()
    }

def run_placement_monitoring():
    """Запуск мониторинга размещений (для планировщика)"""
    monitor = PlacementMonitor()
    return monitor.run_monitoring_cycle()

def cleanup_old_placement_checks(days_old: int = 30):
    """Очистка старых проверок (для планировщика)"""
    monitor = PlacementMonitor()
    monitor.cleanup_old_checks(days_old)

# ================================================================
# MAIN FUNCTION FOR TESTING
# ================================================================

def main():
    """Тестовая функция"""
    parser = TelegramChannelParser()
    
    # Тест парсинга URL
    test_urls = [
        "https://t.me/test_channel/123",
        "https://t.me/c/1234567890/456",
        "invalid_url"
    ]
    
    for url in test_urls:
        parsed = parser.parse_telegram_url(url)
        print(f"URL: {url}")
        print(f"Parsed: {parsed}")
        print("-" * 50)
    
    # Тест проверки поста
    test_post_url = "https://t.me/test_channel/123"
    result = parser.check_post_exists(test_post_url)
    print(f"Check result: {result}")
    
    # Тест мониторинга
    monitor = PlacementMonitor()
    monitoring_result = monitor.run_monitoring_cycle()
    print(f"Monitoring result: {monitoring_result}")

if __name__ == "__main__":
    main()