# real_telegram_integration.py - Продуктивная интеграция с Telegram Bot API
import os
import asyncio
import aiohttp
import logging
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union
from urllib.parse import quote, unquote
from dataclasses import dataclass
from enum import Enum

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TelegramError(Exception):
    """Базовый класс для ошибок Telegram API"""
    pass


class ChannelNotFoundError(TelegramError):
    """Канал не найден"""
    pass


class AccessDeniedError(TelegramError):
    """Нет доступа к каналу"""
    pass


class BotNotInChannelError(TelegramError):
    """Бот не добавлен в канал"""
    pass


class RateLimitError(TelegramError):
    """Превышен лимит запросов"""
    pass


class ChatType(Enum):
    """Типы чатов Telegram"""
    PRIVATE = "private"
    GROUP = "group"
    SUPERGROUP = "supergroup"
    CHANNEL = "channel"


class MemberStatus(Enum):
    """Статусы участников"""
    CREATOR = "creator"
    ADMINISTRATOR = "administrator"
    MEMBER = "member"
    RESTRICTED = "restricted"
    LEFT = "left"
    KICKED = "kicked"


@dataclass
class ChannelInfo:
    """Информация о канале"""
    id: int
    title: str
    username: Optional[str]
    type: str
    description: Optional[str]
    subscribers_count: int
    is_public: bool
    invite_link: Optional[str]
    photo_url: Optional[str]
    verified: bool = False
    scam: bool = False
    fake: bool = False


@dataclass
class AdminRights:
    """Права администратора"""
    can_manage_chat: bool = False
    can_post_messages: bool = False
    can_edit_messages: bool = False
    can_delete_messages: bool = False
    can_invite_users: bool = False
    can_restrict_members: bool = False
    can_promote_members: bool = False
    can_change_info: bool = False
    can_pin_messages: bool = False


class TelegramBotAPI:
    """Клиент для работы с Telegram Bot API"""

    def __init__(self, bot_token: str):
        if not bot_token:
            raise TelegramError("Bot token is required for production mode")

        self.bot_token = bot_token
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.session: Optional[aiohttp.ClientSession] = None
        self._rate_limiter = RateLimiter()

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            connector=aiohttp.TCPConnector(limit=10)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def _make_request(self, method: str, **params) -> Dict:
        """Выполнение HTTP запроса к Telegram API"""
        if not self.session:
            raise TelegramError("Session not initialized. Use async context manager.")

        # Rate limiting
        await self._rate_limiter.wait()

        url = f"{self.base_url}/{method}"

        try:
            # Фильтруем None значения
            filtered_params = {k: v for k, v in params.items() if v is not None}

            async with self.session.post(url, json=filtered_params) as response:
                data = await response.json()

                if not data.get('ok'):
                    error_code = data.get('error_code', 0)
                    description = data.get('description', 'Unknown error')

                    # Обработка специфичных ошибок
                    if error_code == 429:  # Too Many Requests
                        retry_after = data.get('parameters', {}).get('retry_after', 1)
                        await asyncio.sleep(retry_after)
                        raise RateLimitError(f"Rate limit exceeded. Retry after {retry_after}s")
                    elif 'chat not found' in description.lower():
                        raise ChannelNotFoundError(f"Channel not found: {description}")
                    elif 'forbidden' in description.lower() or 'access' in description.lower():
                        raise AccessDeniedError(f"Access denied: {description}")
                    elif 'bot is not a member' in description.lower():
                        raise BotNotInChannelError(f"Bot not in channel: {description}")
                    else:
                        raise TelegramError(f"API Error {error_code}: {description}")

                return data['result']

        except aiohttp.ClientError as e:
            raise TelegramError(f"HTTP Error: {str(e)}")
        except asyncio.TimeoutError:
            raise TelegramError("Request timeout")

    async def get_me(self) -> Dict:
        """Получение информации о боте"""
        return await self._make_request('getMe')

    async def get_chat(self, chat_id: Union[str, int]) -> Dict:
        """Получение информации о чате/канале"""
        return await self._make_request('getChat', chat_id=chat_id)

    async def get_chat_member_count(self, chat_id: Union[str, int]) -> int:
        """Получение количества участников"""
        return await self._make_request('getChatMemberCount', chat_id=chat_id)

    async def get_chat_member(self, chat_id: Union[str, int], user_id: int) -> Dict:
        """Получение информации об участнике"""
        return await self._make_request('getChatMember', chat_id=chat_id, user_id=user_id)

    async def get_chat_administrators(self, chat_id: Union[str, int]) -> List[Dict]:
        """Получение списка администраторов"""
        return await self._make_request('getChatAdministrators', chat_id=chat_id)


class RateLimiter:
    """Rate limiter для Telegram API"""

    def __init__(self, max_requests: int = 30, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []

    async def wait(self):
        """Ожидание перед выполнением запроса"""
        now = time.time()

        # Удаляем старые запросы
        self.requests = [req_time for req_time in self.requests
                         if now - req_time < self.time_window]

        # Проверяем лимит
        if len(self.requests) >= self.max_requests:
            sleep_time = self.time_window - (now - self.requests[0]) + 1
            logger.warning(f"Rate limit reached. Sleeping for {sleep_time:.1f}s")
            await asyncio.sleep(sleep_time)

        # Записываем текущий запрос
        self.requests.append(now)


class TelegramChannelManager:
    """Менеджер для работы с Telegram каналами"""

    def __init__(self, bot_token: str):
        if not bot_token:
            raise TelegramError("Bot token is required")

        self.bot_token = bot_token
        self._cache = {}
        self._cache_ttl = 300  # 5 минут

    def _get_cache_key(self, method: str, **params) -> str:
        """Генерация ключа кеша"""
        sorted_params = sorted(params.items())
        return f"{method}:{hash(str(sorted_params))}"

    def _is_cache_valid(self, timestamp: float) -> bool:
        """Проверка валидности кеша"""
        return time.time() - timestamp < self._cache_ttl

    async def search_channel_by_username(self, username: str) -> Tuple[bool, Optional[ChannelInfo], Optional[str]]:
        """
        Поиск канала по username

        Returns:
            Tuple[success, channel_info, error_message]
        """
        try:
            # Валидация username
            cleaned_username = self._clean_username(username)
            if not cleaned_username:
                return False, None, "Неверный формат username"

            # Проверка кеша
            cache_key = self._get_cache_key("search_channel", username=cleaned_username)
            if cache_key in self._cache:
                cached_data, timestamp = self._cache[cache_key]
                if self._is_cache_valid(timestamp):
                    logger.info(f"Using cached data for channel @{cleaned_username}")
                    return cached_data

            # Выполнение запроса
            async with TelegramBotAPI(self.bot_token) as api:
                try:
                    # Получаем информацию о канале
                    chat_data = await api.get_chat(f"@{cleaned_username}")

                    # Получаем количество участников
                    try:
                        member_count = await api.get_chat_member_count(f"@{cleaned_username}")
                    except (AccessDeniedError, BotNotInChannelError):
                        # Если нет доступа к точному количеству, используем приблизительное
                        member_count = chat_data.get('approximate_member_count', 0)

                    # Создаем объект ChannelInfo
                    channel_info = self._parse_channel_data(chat_data, member_count)

                    # Кешируем результат
                    result = (True, channel_info, None)
                    self._cache[cache_key] = (result, time.time())

                    logger.info(f"Successfully found channel @{cleaned_username}: {channel_info.title}")
                    return result

                except ChannelNotFoundError:
                    error_msg = f"Канал @{cleaned_username} не найден"
                    result = (False, None, error_msg)

                except AccessDeniedError:
                    error_msg = f"Нет доступа к каналу @{cleaned_username}"
                    result = (False, None, error_msg)

                except BotNotInChannelError:
                    error_msg = f"Бот не добавлен в канал @{cleaned_username}"
                    result = (False, None, error_msg)

                except RateLimitError as e:
                    error_msg = f"Превышен лимит запросов: {str(e)}"
                    result = (False, None, error_msg)

                # Кешируем ошибки на короткое время
                self._cache[cache_key] = (result, time.time() - self._cache_ttl + 60)
                return result

        except Exception as e:
            logger.error(f"Unexpected error searching channel @{username}: {e}")
            return False, None, f"Ошибка поиска: {str(e)}"

    async def check_user_admin_rights(self, channel_username: str, user_id: int) -> Tuple[
        bool, Optional[AdminRights], Optional[str]]:
        """
        Проверка прав администратора пользователя в канале

        Returns:
            Tuple[is_admin, admin_rights, error_message]
        """
        try:
            cleaned_username = self._clean_username(channel_username)

            # Проверка кеша
            cache_key = self._get_cache_key("check_admin", username=cleaned_username, user_id=user_id)
            if cache_key in self._cache:
                cached_data, timestamp = self._cache[cache_key]
                if self._is_cache_valid(timestamp):
                    return cached_data

            async with TelegramBotAPI(self.bot_token) as api:
                try:
                    # Получаем информацию об участнике
                    member_data = await api.get_chat_member(f"@{cleaned_username}", user_id)

                    status = member_data.get('status')
                    is_admin = status in ['creator', 'administrator']

                    admin_rights = None
                    if is_admin and status == 'administrator':
                        # Парсим права администратора
                        admin_rights = self._parse_admin_rights(member_data)
                    elif status == 'creator':
                        # Создатель имеет все права
                        admin_rights = AdminRights(
                            can_manage_chat=True,
                            can_post_messages=True,
                            can_edit_messages=True,
                            can_delete_messages=True,
                            can_invite_users=True,
                            can_restrict_members=True,
                            can_promote_members=True,
                            can_change_info=True,
                            can_pin_messages=True
                        )

                    result = (is_admin, admin_rights, None)
                    self._cache[cache_key] = (result, time.time())

                    logger.info(f"User {user_id} admin check for @{cleaned_username}: {is_admin}")
                    return result

                except (ChannelNotFoundError, AccessDeniedError, BotNotInChannelError) as e:
                    error_msg = str(e)
                    result = (False, None, error_msg)
                    self._cache[cache_key] = (result, time.time() - self._cache_ttl + 60)
                    return result

        except Exception as e:
            logger.error(f"Error checking admin rights for user {user_id} in @{channel_username}: {e}")
            return False, None, f"Ошибка проверки прав: {str(e)}"

    async def get_channel_administrators(self, channel_username: str) -> Tuple[bool, List[Dict], Optional[str]]:
        """Получение списка администраторов канала"""
        try:
            cleaned_username = self._clean_username(channel_username)

            cache_key = self._get_cache_key("get_admins", username=cleaned_username)
            if cache_key in self._cache:
                cached_data, timestamp = self._cache[cache_key]
                if self._is_cache_valid(timestamp):
                    return cached_data

            async with TelegramBotAPI(self.bot_token) as api:
                try:
                    admins_data = await api.get_chat_administrators(f"@{cleaned_username}")

                    # Обрабатываем данные администраторов
                    administrators = []
                    for admin in admins_data:
                        admin_info = {
                            'user_id': admin['user']['id'],
                            'username': admin['user'].get('username'),
                            'first_name': admin['user'].get('first_name'),
                            'last_name': admin['user'].get('last_name'),
                            'status': admin['status'],
                            'rights': self._parse_admin_rights(admin) if admin['status'] == 'administrator' else None
                        }
                        administrators.append(admin_info)

                    result = (True, administrators, None)
                    self._cache[cache_key] = (result, time.time())

                    logger.info(f"Found {len(administrators)} administrators for @{cleaned_username}")
                    return result

                except (ChannelNotFoundError, AccessDeniedError, BotNotInChannelError) as e:
                    error_msg = str(e)
                    result = (False, [], error_msg)
                    self._cache[cache_key] = (result, time.time() - self._cache_ttl + 60)
                    return result

        except Exception as e:
            logger.error(f"Error getting administrators for @{channel_username}: {e}")
            return False, [], f"Ошибка получения администраторов: {str(e)}"

    async def test_bot_connection(self) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """Тестирование подключения к Telegram Bot API"""
        try:
            async with TelegramBotAPI(self.bot_token) as api:
                bot_info = await api.get_me()

                logger.info(f"Bot connection test successful: @{bot_info.get('username')}")
                return True, bot_info, None

        except Exception as e:
            logger.error(f"Bot connection test failed: {e}")
            return False, None, str(e)

    def _clean_username(self, username: str) -> Optional[str]:
        """Очистка и валидация username"""
        if not username:
            return None

        # Удаляем @ и пробелы
        cleaned = username.strip().lstrip('@')

        # Валидация формата
        if not cleaned or len(cleaned) < 5 or len(cleaned) > 32:
            return None

        # Проверяем допустимые символы
        import re
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', cleaned):
            return None

        return cleaned

    def _parse_channel_data(self, chat_data: Dict, member_count: int) -> ChannelInfo:
        """Парсинг данных канала из Telegram API"""

        # Определяем тип канала
        chat_type = chat_data.get('type', 'unknown')
        is_channel = chat_type == 'channel'
        is_public = bool(chat_data.get('username'))

        # Получаем фото профиля
        photo_url = None
        if 'photo' in chat_data:
            # В реальном приложении нужно получить файл через getFile API
            photo_url = f"https://api.telegram.org/file/bot{self.bot_token}/photos/photo.jpg"

        return ChannelInfo(
            id=chat_data['id'],
            title=chat_data.get('title', 'Без названия'),
            username=chat_data.get('username'),
            type=chat_type,
            description=chat_data.get('description', ''),
            subscribers_count=member_count,
            is_public=is_public,
            invite_link=chat_data.get('invite_link'),
            photo_url=photo_url,
            verified=chat_data.get('is_verified', False),
            scam=chat_data.get('is_scam', False),
            fake=chat_data.get('is_fake', False)
        )

    def _parse_admin_rights(self, admin_data: Dict) -> AdminRights:
        """Парсинг прав администратора"""
        return AdminRights(
            can_manage_chat=admin_data.get('can_manage_chat', False),
            can_post_messages=admin_data.get('can_post_messages', False),
            can_edit_messages=admin_data.get('can_edit_messages', False),
            can_delete_messages=admin_data.get('can_delete_messages', False),
            can_invite_users=admin_data.get('can_invite_users', False),
            can_restrict_members=admin_data.get('can_restrict_members', False),
            can_promote_members=admin_data.get('can_promote_members', False),
            can_change_info=admin_data.get('can_change_info', False),
            can_pin_messages=admin_data.get('can_pin_messages', False)
        )


class TelegramChannelService:
    """Продуктивный сервис для работы с каналами"""

    def __init__(self, bot_token: str):
        if not bot_token:
            raise TelegramError("Bot token is required for production mode")

        self.bot_token = bot_token
        self.channel_manager = TelegramChannelManager(bot_token)

        logger.info("TelegramChannelService initialized in production mode")

    async def search_channel(self, username: str, user_id: int) -> Dict:
        """
        Поиск канала с проверкой прав пользователя

        Returns:
            Dict с результатами поиска
        """
        try:
            # Реальный поиск через Telegram API
            success, channel_info, error = await self.channel_manager.search_channel_by_username(username)

            if not success:
                return {
                    'success': False,
                    'error': error or 'Канал не найден'
                }

            # Проверяем права администратора пользователя
            is_admin, admin_rights, admin_error = await self.channel_manager.check_user_admin_rights(
                username, user_id
            )

            # Формируем ответ
            result = {
                'success': True,
                'channel': {
                    'id': channel_info.id,
                    'title': channel_info.title,
                    'username': channel_info.username,
                    'type': channel_info.type,
                    'description': channel_info.description,
                    'subscribers_count': channel_info.subscribers_count,
                    'is_public': channel_info.is_public,
                    'invite_link': channel_info.invite_link,
                    'photo_url': channel_info.photo_url,
                    'verified': channel_info.verified,
                    'scam': channel_info.scam,
                    'fake': channel_info.fake
                },
                'user_permissions': {
                    'is_admin': is_admin,
                    'admin_rights': admin_rights.__dict__ if admin_rights else None,
                    'can_add_to_system': is_admin,
                    'error': admin_error
                }
            }

            # Предупреждения
            warnings = []
            if channel_info.scam:
                warnings.append("⚠️ Канал помечен как мошеннический")
            if channel_info.fake:
                warnings.append("⚠️ Канал помечен как фейковый")
            if not is_admin:
                warnings.append("⚠️ Вы не являетесь администратором этого канала")

            if warnings:
                result['warnings'] = warnings

            return result

        except Exception as e:
            logger.error(f"Error in search_channel: {e}")
            return {
                'success': False,
                'error': f'Критическая ошибка поиска канала: {str(e)}'
            }

    async def test_connection(self) -> Dict:
        """Тестирование подключения к Bot API"""
        try:
            success, bot_info, error = await self.channel_manager.test_bot_connection()

            if success:
                return {
                    'success': True,
                    'bot_info': bot_info,
                    'message': 'Подключение к Bot API успешно'
                }
            else:
                return {
                    'success': False,
                    'error': error,
                    'message': 'Ошибка подключения к Bot API'
                }

        except Exception as e:
            logger.error(f"Connection test error: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Критическая ошибка подключения'
            }


# Функции для интеграции с Flask приложением
def create_telegram_service(bot_token: str) -> TelegramChannelService:
    """Создание продуктивного сервиса работы с каналами"""
    if not bot_token:
        bot_token = os.environ.get('BOT_TOKEN')

    if not bot_token:
        raise TelegramError("BOT_TOKEN is required for production mode")

    return TelegramChannelService(bot_token)


def run_async_in_sync(coro):
    """Запуск асинхронной функции в синхронном контексте"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Если уже есть запущенный loop, создаем новый в отдельном потоке
            import concurrent.futures
            import threading

            def run_in_thread():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(coro)
                finally:
                    new_loop.close()

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_in_thread)
                return future.result(timeout=30)
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        # Если нет event loop, создаем новый
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()