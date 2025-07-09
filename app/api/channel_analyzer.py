# app/api/channel_analyzer.py - API для автоматического анализа Telegram каналов

import re
import json
import logging
import asyncio
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
import random
import requests
from flask import Blueprint, request, jsonify, current_app
import os

logger = logging.getLogger(__name__)

# Blueprint для анализатора каналов
analyzer_bp = Blueprint('channel_analyzer', __name__)

class TelegramChannelAnalyzer:
    """
    Класс для анализа Telegram каналов и получения их статистики
    """
    
    def __init__(self, bot_token: Optional[str] = None):
        self.bot_token = bot_token
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'TelegramMiniApp/1.0'
        })
        
        # Кэш для избежания повторных запросов
        self.cache = {}
        self.cache_ttl = 300  # 5 минут
        
    def parse_channel_url(self, url: str) -> Optional[str]:
        """
        Парсинг различных форматов ссылок на Telegram каналы
        """
        if not url:
            return None
            
        url = url.strip().lower()
        
        # Поддерживаемые форматы:
        # https://t.me/channel_name
        # t.me/channel_name  
        # @channel_name
        # channel_name
        
        patterns = [
            r'^https?://t\.me/([^/?]+)',
            r'^t\.me/([^/?]+)',
            r'^@([^/?]+)',
            r'^([a-zA-Z0-9_]+)$'
        ]
        
        for pattern in patterns:
            match = re.match(pattern, url)
            if match:
                username = match.group(1)
                # Удаляем лишние символы
                username = re.sub(r'[^a-zA-Z0-9_]', '', username)
                return username
                
        return None
    
    async def get_channel_info_via_api(self, username: str) -> Optional[Dict]:
        if not self.bot_token:
            logger.debug("Bot token не настроен")
            return None
            
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/getChat"
            params = {'chat_id': f"@{username}"}
            
            logger.info(f"🤖 Bot API запрос: {url}")
            logger.debug(f"🔗 Параметры: {params}")
            
            response = self.session.get(url, params=params, timeout=10)
            
            logger.info(f"📡 Bot API ответ: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                logger.debug(f"📄 Полный ответ Bot API: {data}")
                
                if data.get('ok'):
                    chat_info = data['result']
                    
                    # ✅ ИСПРАВЛЕНО: Читаем member_count, а не subscriber_count
                    member_count = chat_info.get('member_count', 0)
                    
                    # Получаем дополнительную информацию о количестве участников
                    # Для каналов Bot API может не возвращать member_count, пробуем getChatMemberCount
                    if member_count == 0:
                        try:
                            count_url = f"https://api.telegram.org/bot{self.bot_token}/getChatMemberCount"
                            count_params = {'chat_id': f"@{username}"}
                            
                            logger.info(f"🔢 Запрашиваем количество участников: getChatMemberCount")
                            count_response = self.session.get(count_url, params=count_params, timeout=10)
                            
                            if count_response.status_code == 200:
                                count_data = count_response.json()
                                if count_data.get('ok'):
                                    member_count = count_data.get('result', 0)
                                    logger.info(f"✅ getChatMemberCount вернул: {member_count}")
                        except Exception as e:
                            logger.warning(f"⚠️ Ошибка getChatMemberCount: {e}")
                    
                    result = {
                        'title': chat_info.get('title', ''),
                        'username': chat_info.get('username', ''),
                        'description': chat_info.get('description', ''),
                        'member_count': member_count,  # ✅ Правильное поле
                        'type': chat_info.get('type', ''),
                        'invite_link': chat_info.get('invite_link', ''),
                        'api_response': chat_info  # Для отладки
                    }
                    
                    logger.info(f"✅ Bot API успешно:")
                    logger.info(f"   📺 Канал: {result['title']}")
                    logger.info(f"   👥 Участников: {member_count}")
                    logger.info(f"   📝 Описание: {result['description'][:50]}...")
                    
                    return result
                else:
                    error_description = data.get('description', 'Unknown error')
                    logger.warning(f"❌ Bot API ошибка: {error_description}")
                    return None
            else:
                logger.warning(f"❌ HTTP ошибка Bot API: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Исключение в Bot API: {e}")
            return None
    def get_channel_info_via_scraping(self, username: str) -> Optional[Dict]:
        try:
            # Пробуем разные URL форматы
            urls_to_try = [
                f"https://t.me/s/{username}",      # Стандартный
                f"https://t.me/{username}",        # Прямой  
            ]
            
            # Более реалистичные заголовки
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'max-age=0'
            }
            
            for url in urls_to_try:
                logger.info(f"🔍 Пробуем: {url}")
                
                try:
                    # Добавляем задержку и retry
                    import time
                    time.sleep(1)  # Небольшая задержка
                    
                    response = self.session.get(
                        url, 
                        headers=headers, 
                        timeout=15,
                        allow_redirects=True,
                        verify=True
                    )
                    
                    logger.info(f"📡 Статус {url}: {response.status_code}")
                    
                    if response.status_code == 200:
                        content = response.text
                        
                        # Проверяем что это страница канала
                        if any(indicator in content.lower() for indicator in [
                            'tgme_page_title', 'og:title', 'subscribers', 'подписчик'
                        ]):
                            logger.info(f"✅ Успешно загружена страница канала")
                            
                            result = {}
                            
                            # Ищем заголовок
                            title_patterns = [
                                r'<title>([^<]+?)</title>',
                                r'property="og:title"\s+content="([^"]+)"',
                                r'class="tgme_page_title"[^>]*>([^<]+)</div>'
                            ]
                            
                            for pattern in title_patterns:
                                match = re.search(pattern, content, re.IGNORECASE)
                                if match:
                                    title = match.group(1).strip()
                                    if title and 'telegram' not in title.lower():
                                        result['title'] = title
                                        logger.info(f"✅ Заголовок: {title}")
                                        break
                            
                            # Ищем подписчиков ОЧЕНЬ ОСТОРОЖНО
                            logger.info("🔍 Поиск подписчиков...")
                            
                            # Простые и точные паттерны
                            subscriber_patterns = [
                                r'(\d+(?:\.\d+)?[Kk])\s*subscribers?',
                                r'(\d+(?:\.\d+)?[Mm])\s*subscribers?',
                                r'(\d+)\s*subscribers?',
                                r'(\d+(?:\.\d+)?[КкМм])\s*подписчик',
                                r'(\d+)\s*подписчик'
                            ]
                            
                            found_count = 0
                            
                            for pattern in subscriber_patterns:
                                matches = re.finditer(pattern, content, re.IGNORECASE)
                                for match in matches:
                                    text = match.group(1)
                                    parsed = self.parse_subscriber_count(text)
                                    
                                    # Очень строгая проверка
                                    if 100 <= parsed <= 500000000:  # От 100 до 5М
                                        if parsed > found_count:
                                            found_count = parsed
                                            result['subscriber_text'] = text
                                            logger.info(f"✅ Найдено: '{text}' = {parsed}")
                            
                            if found_count > 0:
                                result['raw_subscriber_count'] = found_count
                                result['subscriber_count'] = found_count
                            else:
                                logger.warning(f"❌ Подписчики не найдены")
                            
                            result['username'] = username
                            result['scraped_at'] = datetime.now().isoformat()
                            result['source_url'] = url
                            
                            return result
                        else:
                            logger.warning(f"⚠️ Это не страница канала")
                            
                    elif response.status_code == 404:
                        logger.warning(f"❌ Канал не найден (404)")
                        return None
                    else:
                        logger.warning(f"⚠️ HTTP {response.status_code}")
                        
                except requests.exceptions.ConnectionError as e:
                    logger.warning(f"❌ Ошибка соединения с {url}: {e}")
                    continue
                except requests.exceptions.Timeout as e:
                    logger.warning(f"❌ Таймаут {url}: {e}")
                    continue
                except Exception as e:
                    logger.warning(f"❌ Ошибка {url}: {e}")
                    continue
            
            # Если все URL не сработали
            logger.error(f"❌ Все попытки скрапинга @{username} неуспешны")
            return None
                    
        except Exception as e:
            logger.error(f"❌ Критическая ошибка скрапинга @{username}: {e}")
            return None
    
    def parse_subscriber_count(self, text: str) -> int:
        if not text:
            return 0

        original = text
        text = text.strip().lower().replace(',', '').replace(' ', '')
        
        try:
            # K формат (тысячи)
            if text.endswith('k') or text.endswith('к'):
                num_part = text[:-1]
                try:
                    num = float(num_part)
                    result = int(num * 1000)
                    logger.debug(f"K-формат: '{original}' = {result}")
                    return result
                except:
                    pass
            
            # M формат (миллионы)
            if text.endswith('m') or text.endswith('м'):
                num_part = text[:-1]
                try:
                    num = float(num_part)
                    result = int(num * 1000000)
                    logger.debug(f"M-формат: '{original}' = {result}")
                    return result
                except:
                    pass
            
            # Обычное число - берем ПЕРВОЕ найденное
            numbers = re.findall(r'\d+', text)
            if numbers:
                first_num = int(numbers[0])
                # Проверяем разумность
                if 1 <= first_num <= 50000000:
                    logger.debug(f"Число: '{original}' = {first_num}")
                    return first_num
            
            return 0

        except Exception as e:
            logger.debug(f"Ошибка парсинга '{original}': {e}")
            return 0
    
    def generate_realistic_stats(self, username: str, base_subscriber: int = None) -> Dict:
        logger.info(f"📊 Обработка для @{username}, найденные подписчики: {base_subscriber}")
        
        # ТОЛЬКО реальные данные
        if base_subscriber is not None and base_subscriber > 0:
            subscribers_count = base_subscriber
            data_source = 'real'
            logger.info(f"✅ Используем РЕАЛЬНЫЕ данные: {subscribers_count} подписчиков")
        else:
            subscribers_count = 0  # НЕ ГЕНЕРИРУЕМ - просто 0
            data_source = 'not_found'
            logger.warning(f"❌ Реальные данные НЕ НАЙДЕНЫ - показываем 0")
        
        # Простая статистика
        stats = {
            'username': username,
            'title': f"@{username}",
            'description': f"Telegram канал @{username}",
            'category': 'other',
            
            # ВСЕ ПОЛЯ С РЕАЛЬНЫМ ЗНАЧЕНИЕМ ИЛИ 0
            'subscribers': subscribers_count,
            'subscriber_count': subscribers_count,
            'raw_subscriber_count': subscribers_count,
            'member_count': subscribers_count,
            'subscribers_count': subscribers_count,
            
            # Минимальные метрики
            'engagement_rate': 0 if subscribers_count == 0 else 5.0,
            'avg_views': 0,
            
            # Базовые поля
            'avatar_letter': username[0].upper() if username else 'C',
            'verified': False,
            'data_source': data_source,
            'generated_at': datetime.now().isoformat(),
            'invite_link': f'https://t.me/{username}'
        }
        
        logger.info(f"📊 Финальный результат: {subscribers_count} подписчиков (источник: {data_source})")
        
        return stats
    
    def calculate_estimated_cpm(self, subscriber: int, engagement_rate: float) -> float:
        """
        Расчет ориентировочной стоимости за 1000 просмотров
        """
        base_cpm = 50  # Базовая CPM в рублях
        
        # Корректировки на основе размера канала
        if subscriber > 100000:
            base_cpm *= 1.5
        elif subscriber > 50000:
            base_cpm *= 1.3
        elif subscriber < 5000:
            base_cpm *= 0.7
        
        # Корректировка на основе вовлеченности
        if engagement_rate > 10:
            base_cpm *= 1.4
        elif engagement_rate > 7:
            base_cpm *= 1.2
        elif engagement_rate < 3:
            base_cpm *= 0.8
        
        return round(base_cpm, 2)
    
    def estimate_audience_quality(self, subscriber: int, engagement_rate: float) -> str:
        """
        Оценка качества аудитории
        """
        if engagement_rate > 12:
            return "Высокое"
        elif engagement_rate > 7:
            return "Хорошее"
        elif engagement_rate > 4:
            return "Среднее"
        else:
            return "Низкое"
    
    async def analyze_channel(self, channel_url: str) -> Dict[str, Any]:
        try:
            # Парсим URL
            username = self.parse_channel_url(channel_url)
            if not username:
                return {'success': False, 'error': 'Неверный формат ссылки на канал'}
            
            logger.info(f"🔍 Анализируем: @{username}")
            
            # Проверяем кэш
            cache_key = f"channel_{username}"
            if cache_key in self.cache:
                cached_data, timestamp = self.cache[cache_key]
                if datetime.now().timestamp() - timestamp < self.cache_ttl:
                    return cached_data
            
            # Инициализируем переменные
            base_subscriber = None
            title = None
            description = None
            data_source = 'not_found'
            
            # ШАГ 1: Bot API
            try:
                api_data = await self.get_channel_info_via_api(username)
                if api_data:
                    title = api_data.get('title', '').strip()
                    description = api_data.get('description', '').strip()
                    member_count = api_data.get('member_count', 0)
                    
                    if member_count is not None:
                        base_subscriber = member_count
                        data_source = 'bot_api'
                        logger.info(f"✅ Bot API: {base_subscriber} подписчиков")
            except Exception as e:
                logger.warning(f"Bot API ошибка: {e}")
            
            # ШАГ 2: Веб-скрапинг (если Bot API не дал результат)
            if not base_subscriber:
                try:
                    scraped_data = self.get_channel_info_via_scraping(username)
                    if scraped_data:
                        if not title:
                            title = scraped_data.get('title', '').strip()
                        if not description:
                            description = scraped_data.get('description', '').strip()
                        
                        if scraped_data.get('raw_subscriber_count', 0) > 0:
                            base_subscriber = scraped_data['raw_subscriber_count']
                            data_source = 'scraping'
                            logger.info(f"✅ Скрапинг: {base_subscriber} подписчиков")
                except Exception as e:
                    logger.error(f"Скрапинг ошибка: {e}")
            
            # ШАГ 3: Формируем результат
            stats = self.generate_realistic_stats(username, base_subscriber)
            
            # Добавляем найденные данные
            if title:
                stats['title'] = title
            if description:
                stats['description'] = description
            
            stats['data_source'] = data_source
            
            result = {
                'success': True,
                'data': stats,
                'analyzed_at': datetime.now().isoformat()
            }
            
            # Кэшируем
            self.cache[cache_key] = (result, datetime.now().timestamp())
            
            logger.info(f"🎯 Результат: @{username} = {stats.get('subscriber_count', 0)} подписчиков ({data_source})")
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка анализа: {e}")
            return {
                'success': False,
                'error': f'Ошибка анализа канала: {str(e)}'
            }

# Создаем глобальный экземпляр анализатора
analyzer = TelegramChannelAnalyzer(bot_token=os.environ.get('BOT_TOKEN'))
@analyzer_bp.route('/analyze', methods=['POST'])
def analyze_channel():
    """
    API endpoint для анализа канала
    """
    try:
        data = request.get_json()
        
        if not data or 'channel_url' not in data:
            return jsonify({
                'success': False,
                'error': 'Необходимо указать channel_url'
            }), 400
        
        channel_url = data['channel_url'].strip()
        
        if not channel_url:
            return jsonify({
                'success': False,
                'error': 'Ссылка на канал не может быть пустой'
            }), 400
        
        # Выполняем анализ
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(analyzer.analyze_channel(channel_url))
        finally:
            loop.close()
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Ошибка API анализа канала: {e}")
        return jsonify({
            'success': False,
            'error': 'Внутренняя ошибка сервера'
        }), 500

@analyzer_bp.route('/validate', methods=['POST'])
def validate_channel_url():
    """
    Быстрая валидация URL канала
    """
    try:
        data = request.get_json()
        channel_url = data.get('channel_url', '').strip()
        
        username = analyzer.parse_channel_url(channel_url)
        
        if username:
            return jsonify({
                'success': True,
                'username': username,
                'formatted_url': f"https://t.me/{username}"
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Неверный формат ссылки на канал'
            }), 400
            
    except Exception as e:
        logger.error(f"Ошибка валидации URL: {e}")
        return jsonify({
            'success': False,
            'error': 'Ошибка валидации'
        }), 500

@analyzer_bp.route('/cache/clear', methods=['POST'])
def clear_cache():
    """
    Очистка кэша анализатора (для админа)
    """
    try:
        analyzer.cache.clear()
        return jsonify({
            'success': True,
            'message': 'Кэш очищен'
        })
    except Exception as e:
        logger.error(f"Ошибка очистки кэша: {e}")
        return jsonify({
            'success': False,
            'error': 'Ошибка очистки кэша'
        }), 500

@analyzer_bp.route('/stats', methods=['GET'])
def analyzer_stats():
    """
    Статистика работы анализатора
    """
    try:
        return jsonify({
            'success': True,
            'stats': {
                'cache_size': len(analyzer.cache),
                'cache_ttl_seconds': analyzer.cache_ttl,
                'bot_token_configured': analyzer.bot_token is not None
            }
        })
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        return jsonify({
            'success': False,
            'error': 'Ошибка получения статистики'
        }), 500

# Функция для инициализации анализатора с токеном бота
def init_analyzer(bot_token: Optional[str] = None):
    """
    Инициализация анализатора с токеном бота
    """
    global analyzer
    if bot_token:
        analyzer.bot_token = bot_token
        logger.info("Анализатор каналов инициализирован с Bot Token")
    else:
        logger.info("Анализатор каналов работает без Bot Token (только демо-данные)")

# Добавить в конец файла app/api/channel_analyzer.py

@analyzer_bp.route('/debug/bot-api', methods=['GET'])
def debug_bot_api():
    """
    ДИАГНОСТИКА BOT API: Проверяем всю цепочку работы с токеном
    """
    import os
    import requests
    
    result = {
        'timestamp': datetime.now().isoformat(),
        'tests': {}
    }
    
    try:
        # ТЕСТ 1: Проверяем загрузку .env
        from dotenv import load_dotenv
        load_dotenv()
        result['tests']['env_loaded'] = True
        
        # ТЕСТ 2: Проверяем наличие токена в переменных окружения
        bot_token_env = os.environ.get('BOT_TOKEN')
        result['tests']['token_in_env'] = {
            'exists': bot_token_env is not None,
            'length': len(bot_token_env) if bot_token_env else 0,
            'starts_with': bot_token_env[:10] + '...' if bot_token_env and len(bot_token_env) > 10 else 'N/A'
        }
        
        # ТЕСТ 3: Проверяем токен в анализаторе
        analyzer_token = analyzer.bot_token
        result['tests']['token_in_analyzer'] = {
            'exists': analyzer_token is not None,
            'length': len(analyzer_token) if analyzer_token else 0,
            'starts_with': analyzer_token[:10] + '...' if analyzer_token and len(analyzer_token) > 10 else 'N/A',
            'matches_env': analyzer_token == bot_token_env if analyzer_token and bot_token_env else False
        }
        
        # ТЕСТ 4: Проверяем формат токена
        if bot_token_env:
            # Формат токена: числобота:длинная_строка
            token_parts = bot_token_env.split(':')
            result['tests']['token_format'] = {
                'valid_format': len(token_parts) == 2,
                'bot_id_part': token_parts[0] if len(token_parts) > 0 else 'missing',
                'secret_part_length': len(token_parts[1]) if len(token_parts) > 1 else 0,
                'expected_format': 'bot_id:secret (like 1234567890:AABBCC...)'
            }
        else:
            result['tests']['token_format'] = {'error': 'No token to check'}
        
        # ТЕСТ 5: Проверяем API Telegram напрямую
        if bot_token_env:
            try:
                api_url = f"https://api.telegram.org/bot{bot_token_env}/getMe"
                response = requests.get(api_url, timeout=10)
                
                result['tests']['telegram_api_test'] = {
                    'status_code': response.status_code,
                    'success': response.status_code == 200
                }
                
                if response.status_code == 200:
                    data = response.json()
                    result['tests']['telegram_api_test']['bot_info'] = {
                        'bot_username': data.get('result', {}).get('username', 'N/A'),
                        'bot_name': data.get('result', {}).get('first_name', 'N/A'),
                        'can_read_messages': data.get('result', {}).get('can_read_all_group_messages', False)
                    }
                else:
                    result['tests']['telegram_api_test']['error'] = response.text
                    
            except Exception as e:
                result['tests']['telegram_api_test'] = {
                    'error': str(e),
                    'success': False
                }
        else:
            result['tests']['telegram_api_test'] = {'error': 'No token available'}
        
        # ТЕСТ 6: Тестируем метод анализатора
        if bot_token_env:
            try:
                # Создаем тестовый анализатор с токеном
                test_analyzer = TelegramChannelAnalyzer(bot_token=bot_token_env)
                
                # Тестируем на реальном канале
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                api_data = loop.run_until_complete(test_analyzer.get_channel_info_via_api('durov'))
                loop.close()
                
                result['tests']['analyzer_method_test'] = {
                    'success': api_data is not None,
                    'data_received': api_data if api_data else 'No data'
                }
                
            except Exception as e:
                result['tests']['analyzer_method_test'] = {
                    'error': str(e),
                    'success': False
                }
        else:
            result['tests']['analyzer_method_test'] = {'error': 'No token available'}
        
        # ТЕСТ 7: Проверяем конфигурацию приложения
        try:
            from app.config.telegram_config import AppConfig
            config_token = getattr(AppConfig, 'BOT_TOKEN', None)
            result['tests']['app_config'] = {
                'token_in_config': config_token is not None,
                'matches_env': config_token == bot_token_env if config_token and bot_token_env else False
            }
        except Exception as e:
            result['tests']['app_config'] = {'error': str(e)}
        
        # ИТОГИ
        result['summary'] = {
            'token_loaded': result['tests']['token_in_env']['exists'],
            'token_valid_format': result['tests'].get('token_format', {}).get('valid_format', False),
            'api_accessible': result['tests'].get('telegram_api_test', {}).get('success', False),
            'analyzer_working': result['tests'].get('analyzer_method_test', {}).get('success', False),
            'overall_status': 'OK' if all([
                result['tests']['token_in_env']['exists'],
                result['tests'].get('telegram_api_test', {}).get('success', False)
            ]) else 'ISSUES_FOUND'
        }
        
        # Рекомендации
        recommendations = []
        if not result['tests']['token_in_env']['exists']:
            recommendations.append('Добавьте BOT_TOKEN в .env файл')
        elif not result['tests'].get('token_format', {}).get('valid_format', False):
            recommendations.append('Проверьте формат токена (должен быть: 1234567890:AABBCC...)')
        elif not result['tests'].get('telegram_api_test', {}).get('success', False):
            recommendations.append('Токен неверный или API Telegram недоступен')
        elif not result['tests'].get('analyzer_method_test', {}).get('success', False):
            recommendations.append('Проблема в методе анализатора - проверьте логи')
        else:
            recommendations.append('Bot API настроен корректно!')
        
        result['recommendations'] = recommendations
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# Экспорт blueprint
__all__ = ['analyzer_bp', 'init_analyzer']