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
        """
        Получение информации о канале через Telegram Bot API (если доступен)
        """
        if not self.bot_token:
            return None
            
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/getChat"
            params = {'chat_id': f"@{username}"}
            
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    chat_info = data['result']
                    return {
                        'title': chat_info.get('title', ''),
                        'username': chat_info.get('username', ''),
                        'description': chat_info.get('description', ''),
                        'member_count': chat_info.get('member_count', 0),
                        'type': chat_info.get('type', ''),
                        'invite_link': chat_info.get('invite_link', '')
                    }
            
        except Exception as e:
            logger.warning(f"Ошибка получения данных через Bot API: {e}")
            
        return None

    def get_channel_info_via_scraping(self, username: str) -> Optional[Dict]:
        """
        Получение базовой информации о канале через веб-скрапинг (улучшенная версия)
        """
        try:
            url = f"https://t.me/s/{username}"  # ✅ Используем /s/ для лучшего доступа к данным

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }

            response = self.session.get(url, headers=headers, timeout=15)

            if response.status_code == 200:
                content = response.text
                result = {}

                # Улучшенный парсинг заголовка
                title_patterns = [
                    r'<title>([^<]+)</title>',
                    r'property="og:title" content="([^"]+)"',
                    r'class="tgme_page_title"[^>]*>([^<]+)</div>'
                ]

                for pattern in title_patterns:
                    match = re.search(pattern, content)
                    if match:
                        result['title'] = match.group(1).strip()
                        break

                # Улучшенный парсинг описания
                desc_patterns = [
                    r'<meta property="og:description" content="([^"]+)"',
                    r'class="tgme_page_description"[^>]*>([^<]+)</div>'
                ]

                for pattern in desc_patterns:
                    match = re.search(pattern, content)
                    if match:
                        result['description'] = match.group(1).strip()
                        break

                # ИСПРАВЛЕННЫЙ парсинг подписчиков - ищем в разных местах
                subscriber_patterns = [
                    r'(\d+(?:\s*\d+)*)\s*(?:subscriber|подписчиков|members|участников)',  # Стандартный формат
                    r'(\d+(?:\.\d+)?[KММKk])\s*(?:subscriber|подписчиков|members|участников)',  # С K/M
                    r'"subscriber_count":(\d+)',  # JSON в коде страницы
                    r'data-num="(\d+)"',  # Атрибуты данных
                    r'class="counter_value"[^>]*>(\d+(?:\s*\d+)*)',  # Счетчик
                ]

                max_subscribers = 0  # Берем максимальное найденное значение

                for pattern in subscriber_patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        subs_text = match.group(1)
                        parsed_count = self.parse_subscriber_count(subs_text)
                        if parsed_count > max_subscribers:
                            max_subscribers = parsed_count
                            result['subscriber_text'] = subs_text

                # Логирование для отладки
                logger.info(f"Скрапинг канала {username}: найдено {max_subscribers} подписчиков")

                return result if result else None

        except Exception as e:
            logger.warning(f"Ошибка скрапинга канала {username}: {e}")

        return None

    def parse_subscriber_count(self, text: str) -> int:
        """
        Улучшенный парсинг количества подписчиков из текста
        """
        if not text:
            return 0

        # Убираем лишние символы но сохраняем структуру
        text = text.replace(',', '').replace(' ', '').lower()

        # Обработка сокращений K, M, К, М
        multipliers = {
            'k': 1000, 'к': 1000,
            'm': 1000000, 'м': 1000000,
            'млн': 1000000, 'mln': 1000000,
            'тыс': 1000, 'th': 1000
        }

        for suffix, multiplier in multipliers.items():
            if text.endswith(suffix):
                try:
                    number_part = text[:-len(suffix)]
                    number = float(number_part)
                    result = int(number * multiplier)
                    logger.debug(f"Parsed '{text}' as {result} subscriber")
                    return result
                except ValueError:
                    continue

        # Извлекаем все числа и берем самое большое (часто правильное)
        numbers = re.findall(r'\d+', text)
        if numbers:
            # Если несколько чисел - объединяем их или берем самое длинное
            if len(numbers) == 1:
                try:
                    return int(numbers[0])
                except ValueError:
                    return 0
            else:
                # Пробуем объединить (для случаев типа "397 812")
                combined = ''.join(numbers)
                try:
                    return int(combined)
                except ValueError:
                    # Если не получается - берем самое большое число
                    try:
                        return max(int(num) for num in numbers)
                    except ValueError:
                        return 0

        return 0
    
    def generate_realistic_stats(self, username: str, base_subscriber: int = None) -> Dict:
        """
        Генерация реалистичной статистики канала
        """
        # Если подписчиков не передано, генерируем на основе хэша username
        if base_subscriber is None:
            # Используем хэш для консистентности
            hash_val = abs(hash(username)) % 100000
            base_subscriber = 1000 + hash_val
        
        # Реалистичные метрики
        # ER обычно от 2% до 15% для Telegram каналов
        engagement_rate = 2 + (abs(hash(username + 'er')) % 13)
        avg_views = int(base_subscriber * (engagement_rate / 100))
        
        # Определяем категорию на основе названия канала/username
        categories = ['tech', 'business', 'education', 'lifestyle', 'finance', 
                     'health', 'entertainment', 'crypto', 'marketing', 'news']
        
        category = categories[abs(hash(username + 'cat')) % len(categories)]
        
        # Генерируем название канала
        channel_names = {
            'tech': ['Tech News', 'IT Hub', 'Dev Community', 'Code Life'],
            'business': ['Business Trends', 'Startup Hub', 'Бизнес канал'],
            'education': ['Learn More', 'Образование', 'Study Hub'],
            'lifestyle': ['Life Style', 'Жизнь', 'Daily Life'],
            'finance': ['Money Talk', 'Финансы', 'Invest Club'],
            'health': ['Health Tips', 'Здоровье', 'Wellness'],
            'entertainment': ['Fun Time', 'Развлечения', 'Comedy Club'],
            'crypto': ['Crypto News', 'Криптовалюты', 'Blockchain'],
            'marketing': ['Marketing Hub', 'Маркетинг', 'SMM Tips'],
            'news': ['News Channel', 'Новости', 'Daily News']
        }
        
        names = channel_names.get(category, ['Channel'])
        title = names[abs(hash(username + 'title')) % len(names)]
        
        # Добавляем username к названию для уникальности
        if len(username) > 3:
            title += f" {username.capitalize()}"
        
        descriptions = {
            'tech': 'Последние новости технологий, IT-тренды и разработка',
            'business': 'Бизнес-идеи, предпринимательство и развитие компаний',
            'education': 'Образовательный контент и развитие навыков',
            'lifestyle': 'Советы по стилю жизни и повседневные лайфхаки',
            'finance': 'Финансовая грамотность и инвестиционные стратегии',
            'health': 'Здоровый образ жизни и медицинские советы',
            'entertainment': 'Развлекательный контент и юмор',
            'crypto': 'Криптовалюты, блокчейн и DeFi проекты',
            'marketing': 'Маркетинговые стратегии и продвижение',
            'news': 'Актуальные новости и события дня'
        }
        
        return {
            'title': title,
            'username': f"@{username}",
            'description': descriptions.get(category, 'Интересный контент каждый день'),
            'subscriber': base_subscriber,
            'avg_views': avg_views,
            'engagement_rate': round(engagement_rate, 1),
            'category': category,
            'verified': abs(hash(username + 'verified')) % 100 < 15,  # 15% каналов верифицированы
            'avatar_letter': username[0].upper() if username else 'T',
            'last_post_date': (datetime.now() - timedelta(hours=abs(hash(username + 'time')) % 48)).isoformat(),
            'estimated_cpm': self.calculate_estimated_cpm(base_subscriber, engagement_rate),
            'audience_quality': self.estimate_audience_quality(base_subscriber, engagement_rate)
        }
    
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
        """
        Основной метод анализа канала
        """
        try:
            # Парсим URL
            username = self.parse_channel_url(channel_url)
            if not username:
                return {
                    'success': False,
                    'error': 'Неверный формат ссылки на канал'
                }
            
            # Проверяем кэш
            cache_key = f"channel_{username}"
            if cache_key in self.cache:
                cached_data, timestamp = self.cache[cache_key]
                if datetime.now().timestamp() - timestamp < self.cache_ttl:
                    logger.info(f"Возвращаем данные из кэша для {username}")
                    return cached_data
            
            logger.info(f"Анализируем канал: {username}")
            
            # Пытаемся получить данные через Bot API
            api_data = await self.get_channel_info_via_api(username)
            
            # Если Bot API недоступен, пытаемся скрапинг
            scraped_data = None
            if not api_data:
                scraped_data = self.get_channel_info_via_scraping(username)
            
            # Объединяем полученные данные
            base_subscriber = None
            title = None
            description = None
            
            if api_data:
                title = api_data.get('title')
                description = api_data.get('description')
                base_subscriber = api_data.get('member_count', 0)
                
            elif scraped_data:
                title = scraped_data.get('title')
                description = scraped_data.get('description')
                if 'subscriber_text' in scraped_data:
                    base_subscriber = self.parse_subscriber_count(scraped_data['subscriber_text'])
            
            # Генерируем полную статистику
            stats = self.generate_realistic_stats(username, base_subscriber)
            
            # Переопределяем данными из API/скрапинга если они есть
            if title:
                stats['title'] = title
            if description:
                stats['description'] = description
            
            result = {
                'success': True,
                'data': stats,
                'data_source': 'api' if api_data else ('scraping' if scraped_data else 'generated'),
                'analyzed_at': datetime.now().isoformat()
            }
            
            # Кэшируем результат
            self.cache[cache_key] = (result, datetime.now().timestamp())
            
            logger.info(f"Анализ канала {username} завершен успешно")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка анализа канала: {e}")
            return {
                'success': False,
                'error': f'Ошибка анализа канала: {str(e)}'
            }

# Создаем глобальный экземпляр анализатора
analyzer = TelegramChannelAnalyzer()

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

# Экспорт blueprint
__all__ = ['analyzer_bp', 'init_analyzer']