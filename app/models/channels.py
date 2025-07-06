# app/models/channels.py
"""
Модель каналов для Telegram Mini App
Поддерживает верификацию, управление настройками и статистику каналов
"""

import json
import secrets
import requests
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List, Tuple
from enum import Enum

from .database import db_manager
from ..utils.exceptions import ChannelError, ValidationError, TelegramAPIError
from ..config.telegram_config import TELEGRAM_BOT_TOKEN, TELEGRAM_API_TIMEOUT, MAX_CHANNELS_PER_USER



class ChannelStatus(Enum):
    """Статусы каналов"""
    PENDING = 'pending'
    VERIFIED = 'verified'
    SUSPENDED = 'suspended'
    DELETED = 'deleted'


class ChannelCategory(Enum):
    """Категории каналов"""
    TECHNOLOGY = 'technology'
    BUSINESS = 'business'
    ENTERTAINMENT = 'entertainment'
    NEWS = 'news'
    EDUCATION = 'education'
    LIFESTYLE = 'lifestyle'
    SPORTS = 'sports'
    GAMING = 'gaming'
    CRYPTO = 'crypto'
    TRAVEL = 'travel'
    FOOD = 'food'
    FITNESS = 'fitness'
    ART = 'art'
    MUSIC = 'music'
    OTHER = 'other'


class Channel:
    """Модель канала"""

    def __init__(self, channel_data: Dict[str, Any] = None):
        if channel_data:
            self.id = channel_data.get('id')
            self.channel_id = channel_data.get('channel_id')
            self.channel_name = channel_data.get('channel_name')
            self.channel_username = channel_data.get('channel_username')
            self.channel_description = channel_data.get('channel_description', '')
            self.subscriber_count = channel_data.get('subscriber_count', 0)
            self.category = channel_data.get('category')
            self.subcategory = channel_data.get('subcategory')
            self.price_per_post = Decimal(str(channel_data.get('price_per_post', 0)))
            self.price_per_view = Decimal(str(channel_data.get('price_per_view', 0)))
            self.min_budget = Decimal(str(channel_data.get('min_budget', 0)))
            self.verification_code = channel_data.get('verification_code')
            self.is_verified = channel_data.get('is_verified', False)
            self.is_active = channel_data.get('is_active', True)
            self.owner_id = channel_data.get('owner_id')
            self.settings = self._parse_settings(channel_data.get('settings'))
            self.stats = self._parse_stats(channel_data.get('stats'))
            self.created_at = channel_data.get('created_at')
            self.updated_at = channel_data.get('updated_at')
            self.verified_at = channel_data.get('verified_at')
            self.last_stats_update = channel_data.get('last_stats_update')
        else:
            self.id = None
            self.channel_id = None
            self.channel_name = None
            self.channel_username = None
            self.channel_description = ''
            self.subscribers_count = 0
            self.category = None
            self.subcategory = None
            self.price_per_post = Decimal('0')
            self.price_per_view = Decimal('0')
            self.min_budget = Decimal('0')
            self.verification_code = None
            self.is_verified = False
            self.is_active = True
            self.owner_id = None
            self.settings = {}
            self.stats = {}
            self.created_at = None
            self.updated_at = None
            self.verified_at = None
            self.last_stats_update = None

    def _parse_settings(self, settings: Any) -> Dict[str, Any]:
        """Парсинг настроек канала из JSON"""
        if isinstance(settings, str):
            try:
                return json.loads(settings)
            except (json.JSONDecodeError, TypeError):
                return {}
        elif isinstance(settings, dict):
            return settings
        return {}

    def _parse_stats(self, stats: Any) -> Dict[str, Any]:
        """Парсинг статистики канала из JSON"""
        if isinstance(stats, str):
            try:
                return json.loads(stats)
            except (json.JSONDecodeError, TypeError):
                return {}
        elif isinstance(stats, dict):
            return stats
        return {}

    def save(self) -> bool:
        """Сохранение канала в базу данных"""
        try:
            settings_json = json.dumps(self.settings) if self.settings else None
            stats_json = json.dumps(self.stats) if self.stats else None

            if self.id:
                # Обновление существующего канала
                query = """
                        UPDATE channels
                        SET channel_name        = ?, \
                            channel_username    = ?, \
                            channel_description = ?,
                            subscribers_count   = ?, \
                            category            = ?, \
                            subcategory         = ?,
                            price_per_post      = ?, \
                            price_per_view      = ?, \
                            min_budget          = ?,
                            is_verified         = ?, \
                            is_active           = ?, \
                            settings            = ?, \
                            stats               = ?,
                            updated_at          = CURRENT_TIMESTAMP, \
                            verified_at         = ?, \
                            last_stats_update   = ?
                        WHERE id = ? \
                        """
                params = (
                    self.channel_name, self.channel_username, self.channel_description,
                    self.subscribers_count, self.category, self.subcategory,
                    float(self.price_per_post), float(self.price_per_view), float(self.min_budget),
                    self.is_verified, self.is_active, settings_json, stats_json,
                    self.verified_at, self.last_stats_update, self.id
                )
            else:
                # Создание нового канала
                query = """
                        INSERT INTO channels (channel_id, channel_name, channel_username, channel_description, \
                                              subscribers_count, category, subcategory, price_per_post, \
                                              price_per_view, min_budget, verification_code, is_verified, \
                                              is_active, owner_id, settings, stats, created_at) \
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP) \
                        """
                params = (
                    self.channel_id, self.channel_name, self.channel_username,
                    self.channel_description, self.subscribers_count, self.category,
                    self.subcategory, float(self.price_per_post), float(self.price_per_view),
                    float(self.min_budget), self.verification_code, self.is_verified,
                    self.is_active, self.owner_id, settings_json, stats_json
                )

            result = db_manager.execute_query(query, params)

            if not self.id and result:
                # Получаем ID нового канала
                self.id = db_manager.execute_query("SELECT last_insert_rowid()", fetch_one=True)[0]

            return True

        except Exception as e:
            raise ChannelError(f"Ошибка сохранения канала: {str(e)}")

    @classmethod
    def get_by_id(cls, channel_id: int) -> Optional['Channel']:
        """Получение канала по ID"""
        query = "SELECT * FROM channels WHERE id = ?"
        result = db_manager.execute_query(query, (channel_id,), fetch_one=True)

        if result:
            return cls(dict(result))
        return None

    @classmethod
    def get_by_channel_id(cls, channel_id: str) -> Optional['Channel']:
        """Получение канала по Telegram channel_id"""
        query = "SELECT * FROM channels WHERE channel_id = ?"
        result = db_manager.execute_query(query, (channel_id,), fetch_one=True)

        if result:
            return cls(dict(result))
        return None

    @classmethod
    def get_user_channels(cls, user_id: int, include_deleted: bool = False) -> List['Channel']:
        """Получение каналов пользователя"""
        query = "SELECT * FROM channels WHERE owner_id = ?"
        params = [user_id]

        if not include_deleted:
            query += " AND is_active = 1"

        query += " ORDER BY created_at DESC"

        results = db_manager.execute_query(query, tuple(params), fetch_all=True)
        return [cls(dict(row)) for row in results] if results else []

    @classmethod
    def search_channels(cls, filters: Dict[str, Any], limit: int = 50, offset: int = 0) -> Tuple[List['Channel'], int]:
        """Поиск каналов с фильтрами"""
        base_query = """
                     SELECT * \
                     FROM channels
                     WHERE is_active = 1 \
                       AND is_verified = 1 \
                     """
        count_query = """
                      SELECT COUNT(*) \
                      FROM channels
                      WHERE is_active = 1 \
                        AND is_verified = 1 \
                      """

        params = []
        conditions = []

        # Фильтр по категории
        if filters.get('category'):
            conditions.append("category = ?")
            params.append(filters['category'])

        # Фильтр по минимальному количеству подписчиков
        if filters.get('min_subscribers'):
            conditions.append("subscribers_count >= ?")
            params.append(filters['min_subscribers'])

        # Фильтр по максимальной цене
        if filters.get('max_price'):
            conditions.append("price_per_post <= ?")
            params.append(filters['max_price'])

        # Поиск по названию
        if filters.get('search'):
            conditions.append("(channel_name LIKE ? OR channel_username LIKE ?)")
            search_term = f"%{filters['search']}%"
            params.extend([search_term, search_term])

        # Фильтр по минимальному бюджету
        if filters.get('min_budget'):
            conditions.append("min_budget <= ?")
            params.append(filters['min_budget'])

        # Добавляем условия к запросам
        if conditions:
            condition_str = " AND " + " AND ".join(conditions)
            base_query += condition_str
            count_query += condition_str

        # Получаем общее количество
        total_count = db_manager.execute_query(count_query, tuple(params), fetch_one=True)[0]

        # Добавляем сортировку и пагинацию
        base_query += " ORDER BY subscribers_count DESC, created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        # Получаем каналы
        results = db_manager.execute_query(base_query, tuple(params), fetch_all=True)
        channels = [cls(dict(row)) for row in results] if results else []

        return channels, total_count

    @classmethod
    def create_channel(cls, user_id: int, channel_data: Dict[str, Any]) -> 'Channel':
        """Создание нового канала"""
        # Проверяем лимит каналов на пользователя
        user_channels_count = len(cls.get_user_channels(user_id))
        if user_channels_count >= MAX_CHANNELS_PER_USER:
            raise ChannelError(f"Превышен лимит каналов на пользователя ({MAX_CHANNELS_PER_USER})")

        # Валидируем данные канала
        cls._validate_channel_data(channel_data)

        # Проверяем уникальность channel_id
        existing_channel = cls.get_by_channel_id(channel_data['channel_id'])
        if existing_channel:
            raise ChannelError("Канал с таким ID уже существует")

        # Получаем информацию о канале из Telegram
        telegram_info = TelegramChannelService.get_channel_info(channel_data['channel_id'])

        # Создаем канал
        channel = cls()
        channel.owner_id = user_id
        channel.channel_id = channel_data['channel_id']
        channel.channel_name = telegram_info.get('title', channel_data.get('channel_name', ''))
        channel.channel_username = telegram_info.get('username', channel_data.get('channel_username'))
        channel.channel_description = telegram_info.get('description', '')
        channel.subscribers_count = telegram_info.get('members_count', 0)
        channel.category = channel_data.get('category')
        channel.subcategory = channel_data.get('subcategory')
        channel.price_per_post = Decimal(str(channel_data.get('price_per_post', 0)))
        channel.price_per_view = Decimal(str(channel_data.get('price_per_view', 0)))
        channel.min_budget = Decimal(str(channel_data.get('min_budget', 0)))
        channel.verification_code = cls._generate_verification_code()
        channel.is_verified = False
        channel.is_active = True
        channel.settings = {
            'auto_accept_offers': channel_data.get('auto_accept_offers', False),
            'notification_enabled': channel_data.get('notification_enabled', True),
            'content_restrictions': channel_data.get('content_restrictions', []),
            'working_hours': channel_data.get('working_hours'),
            'preferred_posting_time': channel_data.get('preferred_posting_time')
        }

        channel.save()
        return channel

    @staticmethod
    def _validate_channel_data(data: Dict[str, Any]):
        """Валидация данных канала"""
        errors = []

        # Проверка обязательных полей
        required_fields = ['channel_id', 'category']
        for field in required_fields:
            if not data.get(field):
                errors.append(f'{field} is required')

        # Валидация channel_id
        channel_id = data.get('channel_id', '')
        if channel_id:
            if not (channel_id.startswith('@') or channel_id.startswith('-100')):
                errors.append('Invalid channel_id format (must start with @ or -100)')

        # Валидация цены
        price = data.get('price_per_post')
        if price is not None:
            try:
                price = float(price)
                if price < 0:
                    errors.append('Price cannot be negative')
                elif price > 1000000:
                    errors.append('Price too high (max: 1,000,000)')
            except (ValueError, TypeError):
                errors.append('Invalid price format')

        # Валидация категории
        valid_categories = [cat.value for cat in ChannelCategory]
        category = data.get('category')
        if category and category not in valid_categories:
            errors.append(f'Invalid category. Must be one of: {", ".join(valid_categories)}')

        if errors:
            raise ValidationError('; '.join(errors))

    @staticmethod
    def _generate_verification_code() -> str:
        """Генерация уникального кода верификации в формате #add123abc"""
        import string
        import random

        # Генерируем случайную строку из букв и цифр
        chars = string.ascii_lowercase + string.digits
        random_part = ''.join(random.choices(chars, k=6))

        return f"#add{random_part}"

    def verify_ownership(self) -> bool:
        """Верификация владения каналом"""
        if self.is_verified:
            return True

        if not self.verification_code:
            self.verification_code = self._generate_verification_code()
            self.save()

        # Проверяем наличие кода верификации в канале
        is_verified = TelegramChannelService.verify_channel_ownership(
            self.channel_id, self.verification_code
        )

        if is_verified:
            self.is_verified = True
            self.verified_at = datetime.now().isoformat()
            self.save()
            return True

        return False

    def update_stats(self) -> bool:
        """Обновление статистики канала"""
        try:
            telegram_info = TelegramChannelService.get_channel_info(self.channel_id)

            if telegram_info:
                old_subscribers = self.subscribers_count
                self.subscribers_count = telegram_info.get('members_count', self.subscribers_count)
                self.channel_description = telegram_info.get('description', self.channel_description)

                # Обновляем статистику
                if 'growth_stats' not in self.stats:
                    self.stats['growth_stats'] = []

                # Добавляем запись о росте
                if old_subscribers != self.subscribers_count:
                    self.stats['growth_stats'].append({
                        'date': datetime.now().isoformat(),
                        'subscribers': self.subscribers_count,
                        'growth': self.subscribers_count - old_subscribers
                    })

                # Оставляем только последние 30 записей
                self.stats['growth_stats'] = self.stats['growth_stats'][-30:]

                self.last_stats_update = datetime.now().isoformat()
                self.save()
                return True

        except Exception as e:
            print(f"Ошибка обновления статистики канала {self.id}: {e}")

        return False

    def get_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Получение аналитики канала"""
        growth_stats = self.stats.get('growth_stats', [])

        # Фильтруем данные за указанный период
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_stats = [
            stat for stat in growth_stats
            if datetime.fromisoformat(stat['date'].replace('Z', '+00:00')) >= cutoff_date
        ]

        if not recent_stats:
            return {
                'subscriber_growth': 0,
                'growth_rate': 0,
                'average_daily_growth': 0,
                'total_growth_events': 0
            }

        total_growth = sum(stat['growth'] for stat in recent_stats)
        positive_growth_events = len([stat for stat in recent_stats if stat['growth'] > 0])

        return {
            'subscribers_growth': total_growth,
            'growth_rate': (total_growth / self.subscribers_count * 100) if self.subscribers_count > 0 else 0,
            'average_daily_growth': total_growth / days if days > 0 else 0,
            'total_growth_events': positive_growth_events,
            'current_subscribers': self.subscribers_count,
            'data_points': len(recent_stats)
        }

    def update_pricing(self, price_per_post: float = None, price_per_view: float = None,
                       min_budget: float = None) -> bool:
        """Обновление ценовых настроек"""
        try:
            if price_per_post is not None:
                if price_per_post < 0 or price_per_post > 1000000:
                    raise ValidationError("Invalid price_per_post value")
                self.price_per_post = Decimal(str(price_per_post))

            if price_per_view is not None:
                if price_per_view < 0 or price_per_view > 1000:
                    raise ValidationError("Invalid price_per_view value")
                self.price_per_view = Decimal(str(price_per_view))

            if min_budget is not None:
                if min_budget < 0 or min_budget > 100000:
                    raise ValidationError("Invalid min_budget value")
                self.min_budget = Decimal(str(min_budget))

            return self.save()

        except Exception as e:
            raise ChannelError(f"Ошибка обновления ценовых настроек: {str(e)}")

    def update_settings(self, new_settings: Dict[str, Any]) -> bool:
        """Обновление настроек канала"""
        try:
            # Обновляем только разрешенные настройки
            allowed_settings = [
                'auto_accept_offers', 'notification_enabled', 'content_restrictions',
                'working_hours', 'preferred_posting_time', 'min_advance_booking_hours',
                'max_posts_per_day', 'blacklisted_categories'
            ]

            for key, value in new_settings.items():
                if key in allowed_settings:
                    self.settings[key] = value

            return self.save()

        except Exception as e:
            raise ChannelError(f"Ошибка обновления настроек: {str(e)}")

    def deactivate(self, reason: str = "") -> bool:
        """Деактивация канала"""
        self.is_active = False
        if reason:
            self.settings['deactivation_reason'] = reason
            self.settings['deactivated_at'] = datetime.now().isoformat()

        return self.save()

    def reactivate(self) -> bool:
        """Реактивация канала"""
        self.is_active = True
        if 'deactivation_reason' in self.settings:
            del self.settings['deactivation_reason']
        if 'deactivated_at' in self.settings:
            del self.settings['deactivated_at']

        return self.save()

    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь"""
        return {
            'id': self.id,
            'channel_id': self.channel_id,
            'channel_name': self.channel_name,
            'channel_username': self.channel_username,
            'channel_description': self.channel_description,
            'subscriber_count': self.subscriber_count,  # ИСПРАВЛЕНО
            'category': self.category,
            'subcategory': self.subcategory,
            'price_per_post': float(self.price_per_post),
            'price_per_view': float(self.price_per_view),
            'min_budget': float(self.min_budget),
            'verification_code': self.verification_code,
            'is_verified': self.is_verified,
            'is_active': self.is_active,
            'owner_id': self.owner_id,
            'settings': self.settings,
            'stats': self.stats,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'verified_at': self.verified_at,
            'last_stats_update': self.last_stats_update,
            # ДОБАВЛЯЕМ СТАТИСТИКУ
            'offers_count': self.get_offers_count(),
            'posts_count': self.get_posts_count()
        }

    def get_offers_count(self) -> int:
        """Получение количества офферов для канала"""
        try:
            from ..models.database import db_manager
            result = db_manager.execute_query(
                "SELECT COUNT(*) FROM offers WHERE channel_id = ?",
                (self.id,),
                fetch_one=True
            )
            return result[0] if result else 0
        except:
            return 0

    def get_posts_count(self) -> int:
        """Получение количества постов канала"""
        try:
            from ..models.database import db_manager
            # Если есть таблица posts
            result = db_manager.execute_query(
                "SELECT COUNT(*) FROM posts WHERE channel_id = ?",
                (self.id,),
                fetch_one=True
            )
            return result[0] if result else 0
        except:
            # Пока таблицы posts нет, возвращаем примерное значение
            # на основе времени создания канала
            if self.created_at:
                from datetime import datetime
                try:
                    created = datetime.fromisoformat(self.created_at.replace('Z', '+00:00'))
                    days_active = (datetime.now() - created).days
                    return max(0, days_active // 7)  # Примерно 1 пост в неделю
                except:
                    return 0
            return 0

    def get_statistics(self) -> dict:
        """Получение полной статистики канала"""
        return {
            'subscriber_count': self.subscriber_count,
            'offers_count': self.get_offers_count(),
            'posts_count': self.get_posts_count(),
            'is_verified': self.is_verified,
            'created_at': self.created_at
        }


class TelegramChannelService:
    """Сервис для работы с Telegram API"""

    @staticmethod
    def get_channel_info(channel_id: str) -> Dict[str, Any]:
        """Получение информации о канале через Telegram API"""
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getChat"
            response = requests.get(
                url,
                params={'chat_id': channel_id},
                timeout=TELEGRAM_API_TIMEOUT
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    chat_info = data['result']
                    return {
                        'title': chat_info.get('title', ''),
                        'username': chat_info.get('username'),
                        'description': chat_info.get('description', ''),
                        'members_count': chat_info.get('members_count', 0),
                        'type': chat_info.get('type')
                    }

            return {}

        except Exception as e:
            raise TelegramAPIError(f"Ошибка получения информации о канале: {str(e)}")

    @staticmethod
    def verify_channel_ownership(channel_id: str, verification_code: str) -> bool:
        """Верификация владения каналом через проверку кода"""
        try:
            # Получаем последние сообщения из канала
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
            response = requests.get(url, timeout=TELEGRAM_API_TIMEOUT)

            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    updates = data.get('result', [])

                    # Ищем код верификации в сообщениях канала
                    for update in updates[-50:]:  # Проверяем последние 50 обновлений
                        message = update.get('message', {})
                        chat = message.get('chat', {})

                        if str(chat.get('id')) == str(channel_id):
                            text = message.get('text', '')
                            if verification_code in text:
                                return True

            return False

        except Exception as e:
            print(f"Ошибка верификации канала: {e}")
            return False

    @staticmethod
    def get_channel_members_count(channel_id: str) -> int:
        """Получение количества участников канала"""
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getChatMembersCount"
            response = requests.get(
                url,
                params={'chat_id': channel_id},
                timeout=TELEGRAM_API_TIMEOUT
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    return data['result']

            return 0

        except Exception as e:
            print(f"Ошибка получения количества участников: {e}")
            return 0



class ChannelStatistics:
    """Класс для работы со статистикой каналов"""

    @staticmethod
    def get_platform_stats() -> Dict[str, Any]:
        """Получение общей статистики платформы"""
        try:
            # Общее количество каналов
            total_channels = db_manager.execute_query(
                "SELECT COUNT(*) FROM channels WHERE is_active = 1",
                fetch_one=True
            )[0]

            # Верифицированные каналы
            verified_channels = db_manager.execute_query(
                "SELECT COUNT(*) FROM channels WHERE is_active = 1 AND is_verified = 1",
                fetch_one=True
            )[0]

            # Статистика подписчиков
            subscribers_stats = db_manager.execute_query(
                """
                SELECT SUM(subscribers_count) as total_subscribers,
                       AVG(subscribers_count) as avg_subscribers,
                       MAX(subscribers_count) as max_subscribers
                FROM channels
                WHERE is_active = 1
                  AND is_verified = 1
                """,
                fetch_one=True
            )

            # Ценовая статистика
            price_stats = db_manager.execute_query(
                """
                SELECT AVG(price_per_post) as avg_price,
                       MIN(price_per_post) as min_price,
                       MAX(price_per_post) as max_price
                FROM channels
                WHERE is_active = 1
                  AND is_verified = 1
                  AND price_per_post > 0
                """,
                fetch_one=True
            )

            # Топ категории
            top_categories = db_manager.execute_query(
                """
                SELECT category, COUNT(*) as count
                FROM channels
                WHERE is_active = 1 AND is_verified = 1
                GROUP BY category
                ORDER BY count DESC
                    LIMIT 5
                """,
                fetch_all=True
            )

            return {
                'channels': {
                    'total': total_channels,
                    'verified': verified_channels,
                    'verification_rate': (verified_channels / total_channels * 100) if total_channels > 0 else 0
                },
                'subscribers': {
                    'total': int(subscribers_stats[0] or 0),
                    'average': int(subscribers_stats[1] or 0),
                    'maximum': int(subscribers_stats[2] or 0)
                },
                'pricing': {
                    'average': round(float(price_stats[0] or 0), 2),
                    'minimum': round(float(price_stats[1] or 0), 2),
                    'maximum': round(float(price_stats[2] or 0), 2)
                },
                'top_categories': [
                    {'category': row[0], 'count': row[1]}
                    for row in top_categories
                ] if top_categories else []
            }

        except Exception as e:
            raise ChannelError(f"Ошибка получения статистики: {str(e)}")

    @staticmethod
    def get_category_distribution() -> List[Dict[str, Any]]:
        """Получение распределения каналов по категориям"""
        try:
            results = db_manager.execute_query(
                """
                SELECT category,
                       COUNT(*) as count,
                       AVG(subscribers_count) as avg_subscribers,
                       AVG(price_per_post) as avg_price
                FROM channels
                WHERE is_active = 1 AND is_verified = 1
                GROUP BY category
                ORDER BY count DESC
                """,
                fetch_all=True
            )

            return [
                {
                    'category': row[0],
                    'count': row[1],
                    'avg_subscribers': int(row[2] or 0),
                    'avg_price': round(float(row[3] or 0), 2)
                }
                for row in results
            ] if results else []

        except Exception as e:
            raise ChannelError(f"Ошибка получения распределения по категориям: {str(e)}")


class ChannelMatcher:
    """Класс для подбора каналов под офферы"""

    @staticmethod
    def find_matching_channels(offer_criteria: Dict[str, Any], limit: int = 20) -> List[Dict[str, Any]]:
        """Поиск подходящих каналов для оффера"""
        try:
            query = """
                    SELECT c.*,
                           (CASE
                                WHEN c.category = ? THEN 100
                                WHEN c.subcategory = ? THEN 80
                                ELSE 50
                               END) as category_match_score,
                           (CASE
                                WHEN c.subscribers_count >= ? AND c.subscribers_count <= ? THEN 100
                                WHEN c.subscribers_count >= ? * 0.8 THEN 80
                                WHEN c.subscribers_count >= ? * 0.6 THEN 60
                                ELSE 30
                               END) as audience_match_score,
                           (CASE
                                WHEN c.price_per_post <= ? THEN 100
                                WHEN c.price_per_post <= ? * 1.2 THEN 80
                                WHEN c.price_per_post <= ? * 1.5 THEN 60
                                ELSE 30
                               END) as price_match_score
                    FROM channels c
                    WHERE c.is_active = 1 \
                      AND c.is_verified = 1
                      AND c.min_budget <= ?
                      AND c.price_per_post > 0
                    ORDER BY (category_match_score + audience_match_score + price_match_score) DESC LIMIT ? \
                    """

            category = offer_criteria.get('category', '')
            subcategory = offer_criteria.get('subcategory', '')
            min_subscribers = offer_criteria.get('min_subscribers', 0)
            max_subscribers = offer_criteria.get('max_subscribers', 999999999)
            max_price = offer_criteria.get('max_price', 999999)
            budget = offer_criteria.get('budget', 0)

            params = (
                category, subcategory,
                min_subscribers, max_subscribers, min_subscribers, min_subscribers,
                max_price, max_price, max_price,
                budget, limit
            )

            results = db_manager.execute_query(query, params, fetch_all=True)

            matching_channels = []
            for row in results:
                channel_data = dict(row)
                channel = Channel(channel_data)

                # Рассчитываем общий скор совпадения
                total_score = (
                                      channel_data['category_match_score'] +
                                      channel_data['audience_match_score'] +
                                      channel_data['price_match_score']
                              ) / 3

                matching_channels.append({
                    'channel': channel.to_dict(),
                    'match_score': round(total_score, 1),
                    'match_reasons': ChannelMatcher._get_match_reasons(channel, offer_criteria),
                    'estimated_reach': ChannelMatcher._estimate_reach(channel, offer_criteria)
                })

            return matching_channels

        except Exception as e:
            raise ChannelError(f"Ошибка поиска подходящих каналов: {str(e)}")

    @staticmethod
    def _get_match_reasons(channel: Channel, criteria: Dict[str, Any]) -> List[str]:
        """Получение причин совпадения канала с критериями"""
        reasons = []

        if channel.category == criteria.get('category'):
            reasons.append(f"Точное совпадение категории: {channel.category}")
        elif channel.subcategory == criteria.get('subcategory'):
            reasons.append(f"Совпадение подкатегории: {channel.subcategory}")

        if criteria.get('min_subscribers', 0) <= channel.subscribers_count <= criteria.get('max_subscribers',
                                                                                           999999999):
            reasons.append(f"Подходящая аудитория: {channel.subscribers_count:,} подписчиков")

        if channel.price_per_post <= criteria.get('max_price', 999999):
            reasons.append(f"Подходящая цена: {channel.price_per_post} ₽ за пост")

        if channel.min_budget <= criteria.get('budget', 0):
            reasons.append(f"Минимальный бюджет выполнен: {channel.min_budget} ₽")

        return reasons

    @staticmethod
    def _estimate_reach(channel: Channel, criteria: Dict[str, Any]) -> Dict[str, Any]:
        """Оценка охвата для канала"""
        # Примерные коэффициенты охвата для разных типов контента
        reach_coefficients = {
            'technology': 0.15,
            'business': 0.12,
            'entertainment': 0.25,
            'news': 0.20,
            'education': 0.18,
            'lifestyle': 0.22,
            'sports': 0.20,
            'gaming': 0.30,
            'crypto': 0.25,
            'other': 0.15
        }

        coefficient = reach_coefficients.get(channel.category, 0.15)
        estimated_views = int(channel.subscribers_count * coefficient)

        # Оценка вовлеченности (примерно 3-8% от просмотров)
        estimated_engagement = int(estimated_views * 0.05)

        return {
            'estimated_views': estimated_views,
            'estimated_engagement': estimated_engagement,
            'reach_percentage': round(coefficient * 100, 1),
            'cpm': round(float(channel.price_per_post) / estimated_views * 1000, 2) if estimated_views > 0 else 0
        }


class ChannelNotificationService:
    """Сервис уведомлений для каналов"""

    @staticmethod
    def notify_matching_channels(offer_id: int, matching_channels: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Отправка уведомлений владельцам подходящих каналов о новом оффере"""
        try:
            from .user import User

            notification_results = {
                'sent': 0,
                'failed': 0,
                'channels_notified': []
            }

            for match in matching_channels:
                channel_data = match['channel']
                channel_id = channel_data['id']
                owner_id = channel_data['owner_id']

                try:
                    # Получаем владельца канала
                    owner = User.get_by_id(owner_id)
                    if not owner:
                        continue

                    # Проверяем настройки уведомлений
                    channel = Channel.get_by_id(channel_id)
                    if not channel or not channel.settings.get('notification_enabled', True):
                        continue

                    # Отправляем уведомление через Telegram
                    notification_sent = ChannelNotificationService._send_telegram_notification(
                        owner.telegram_id,
                        offer_id,
                        match
                    )

                    if notification_sent:
                        notification_results['sent'] += 1
                        notification_results['channels_notified'].append({
                            'channel_id': channel_id,
                            'channel_name': channel_data['channel_name'],
                            'match_score': match['match_score']
                        })
                    else:
                        notification_results['failed'] += 1

                except Exception as e:
                    print(f"Ошибка отправки уведомления для канала {channel_id}: {e}")
                    notification_results['failed'] += 1

            return notification_results

        except Exception as e:
            raise ChannelError(f"Ошибка отправки уведомлений: {str(e)}")

    @staticmethod
    def _send_telegram_notification(telegram_id: str, offer_id: int, match: Dict[str, Any]) -> bool:
        """Отправка Telegram уведомления"""
        try:
            channel_data = match['channel']
            match_score = match['match_score']
            estimated_reach = match['estimated_reach']

            message = f"""
🎯 *Новый оффер для вашего канала!*

📊 *Совпадение:* {match_score}%
📺 *Канал:* {channel_data['channel_name']}
👥 *Ожидаемый охват:* {estimated_reach['estimated_views']:,} просмотров
💰 *Ваша цена:* {channel_data['price_per_post']} ₽

🔍 *Причины совпадения:*
{chr(10).join('• ' + reason for reason in match['match_reasons'])}

Перейдите в приложение, чтобы посмотреть детали и откликнуться на оффер.
            """

            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            response = requests.post(
                url,
                json={
                    'chat_id': telegram_id,
                    'text': message,
                    'parse_mode': 'Markdown',
                    'reply_markup': {
                        'inline_keyboard': [[
                            {
                                'text': '📱 Открыть приложение',
                                'web_app': {'url': f'https://your-app-url.com/offers/{offer_id}'}
                            }
                        ]]
                    }
                },
                timeout=TELEGRAM_API_TIMEOUT
            )

            return response.status_code == 200 and response.json().get('ok', False)

        except Exception as e:
            print(f"Ошибка отправки Telegram уведомления: {e}")
            return False


class ChannelContentAnalyzer:
    """Анализатор контента каналов"""

    @staticmethod
    def analyze_channel_content(channel_id: str, posts_limit: int = 10) -> Dict[str, Any]:
        """Анализ контента канала для автоматической категоризации"""
        try:
            # Получаем последние посты канала
            posts = ChannelContentAnalyzer._get_recent_posts(channel_id, posts_limit)

            if not posts:
                return {'category': 'other', 'confidence': 0, 'keywords': []}

            # Анализируем текст постов
            all_text = ' '.join(post.get('text', '') for post in posts)

            # Определяем категорию на основе ключевых слов
            category_analysis = ChannelContentAnalyzer._categorize_content(all_text)

            # Анализируем активность
            activity_analysis = ChannelContentAnalyzer._analyze_posting_activity(posts)

            return {
                'category': category_analysis['category'],
                'confidence': category_analysis['confidence'],
                'keywords': category_analysis['keywords'],
                'posting_frequency': activity_analysis['frequency'],
                'avg_post_length': activity_analysis['avg_length'],
                'content_types': activity_analysis['content_types']
            }

        except Exception as e:
            print(f"Ошибка анализа контента канала: {e}")
            return {'category': 'other', 'confidence': 0, 'keywords': []}

    @staticmethod
    def _get_recent_posts(channel_id: str, limit: int) -> List[Dict[str, Any]]:
        """Получение последних постов канала"""
        # Заглушка - в реальном приложении здесь будет интеграция с Telegram API
        # или парсинг публичных каналов
        return []

    @staticmethod
    def _categorize_content(text: str) -> Dict[str, Any]:
        """Категоризация контента на основе ключевых слов"""
        category_keywords = {
            'technology': ['технологии', 'IT', 'программирование', 'софт', 'гаджеты', 'интернет'],
            'business': ['бизнес', 'инвестиции', 'стартап', 'предпринимательство', 'финансы'],
            'entertainment': ['развлечения', 'фильмы', 'музыка', 'шоу', 'юмор', 'мемы'],
            'news': ['новости', 'политика', 'события', 'происшествия', 'мир'],
            'education': ['образование', 'курсы', 'обучение', 'знания', 'навыки'],
            'lifestyle': ['образ жизни', 'здоровье', 'красота', 'мода', 'путешествия'],
            'sports': ['спорт', 'футбол', 'хоккей', 'фитнес', 'тренировки'],
            'gaming': ['игры', 'геймер', 'стрим', 'консоль', 'PC'],
            'crypto': ['криптовалюта', 'bitcoin', 'блокчейн', 'майнинг', 'DeFi']
        }

        text_lower = text.lower()
        category_scores = {}

        for category, keywords in category_keywords.items():
            score = sum(text_lower.count(keyword) for keyword in keywords)
            if score > 0:
                category_scores[category] = score

        if not category_scores:
            return {'category': 'other', 'confidence': 0, 'keywords': []}

        best_category = max(category_scores, key=category_scores.get)
        max_score = category_scores[best_category]
        total_score = sum(category_scores.values())

        confidence = min(max_score / total_score * 100, 100) if total_score > 0 else 0

        # Находим найденные ключевые слова
        found_keywords = []
        for keyword in category_keywords[best_category]:
            if keyword in text_lower:
                found_keywords.append(keyword)

        return {
            'category': best_category,
            'confidence': round(confidence, 1),
            'keywords': found_keywords[:5]  # Топ 5 ключевых слов
        }

    @staticmethod
    def _analyze_posting_activity(posts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Анализ активности постинга"""
        if not posts:
            return {
                'frequency': 'unknown',
                'avg_length': 0,
                'content_types': []
            }

        # Анализ длины постов
        post_lengths = [len(post.get('text', '')) for post in posts]
        avg_length = sum(post_lengths) / len(post_lengths) if post_lengths else 0

        # Анализ типов контента
        content_types = []
        for post in posts:
            if post.get('photo'):
                content_types.append('photo')
            elif post.get('video'):
                content_types.append('video')
            elif post.get('text'):
                content_types.append('text')

        # Определение частоты постинга (упрощенная логика)
        if len(posts) >= 8:  # Больше 8 постов из последних
            frequency = 'high'
        elif len(posts) >= 4:
            frequency = 'medium'
        else:
            frequency = 'low'

        return {
            'frequency': frequency,
            'avg_length': round(avg_length),
            'content_types': list(set(content_types))
        }