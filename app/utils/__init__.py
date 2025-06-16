# app/utils/__init__.py
"""
Модуль утилит и вспомогательных функций для Telegram Mini App
Содержит декораторы, валидаторы, хелперы и обработчики исключений
"""

import logging
from typing import Dict, Any, List, Optional, Callable, Union
from functools import wraps
from datetime import datetime, timedelta
import re
import hashlib
import secrets
import json

logger = logging.getLogger(__name__)

# Список всех экспортируемых утилит
__all__ = []

# Импорт исключений
try:
    from .exceptions import (
        TelegramMiniAppError, ValidationError, AuthenticationError,
        UserError, ChannelError, OfferError, ResponseError,
        PaymentError, AnalyticsError, TelegramAPIError,
        InsufficientFundsError, RateLimitError, ConfigurationError
    )

    __all__.extend([
        'TelegramMiniAppError', 'ValidationError', 'AuthenticationError',
        'UserError', 'ChannelError', 'OfferError', 'ResponseError',
        'PaymentError', 'AnalyticsError', 'TelegramAPIError',
        'InsufficientFundsError', 'RateLimitError', 'ConfigurationError'
    ])
    logger.info("✅ Exceptions импортированы")
except ImportError as e:
    logger.error(f"❌ Ошибка импорта exceptions: {e}")

# Импорт декораторов
try:
    from .decorators import (
        require_telegram_auth, rate_limit_decorator, cache_response,
        validate_request_data, log_execution_time, retry_on_failure,
        require_user_type, sanitize_input
    )

    __all__.extend([
        'require_telegram_auth', 'rate_limit_decorator', 'cache_response',
        'validate_request_data', 'log_execution_time', 'retry_on_failure',
        'require_user_type', 'sanitize_input'
    ])
    logger.info("✅ Decorators импортированы")
except ImportError as e:
    logger.error(f"❌ Ошибка импорта decorators: {e}")

# Импорт валидаторов
try:
    from .validators import (
        TelegramDataValidator, ChannelDataValidator, OfferDataValidator,
        PaymentDataValidator, UserDataValidator, ResponseDataValidator,
        validate_telegram_id, validate_channel_id, validate_price,
        validate_email, validate_phone, validate_url
    )

    __all__.extend([
        'TelegramDataValidator', 'ChannelDataValidator', 'OfferDataValidator',
        'PaymentDataValidator', 'UserDataValidator', 'ResponseDataValidator',
        'validate_telegram_id', 'validate_channel_id', 'validate_price',
        'validate_email', 'validate_phone', 'validate_url'
    ])
    logger.info("✅ Validators импортированы")
except ImportError as e:
    logger.error(f"❌ Ошибка импорта validators: {e}")

# Импорт хелперов
try:
    from .helpers import (
        format_currency, format_datetime, format_number,
        generate_token, hash_password, verify_password,
        sanitize_html, truncate_text, slug_from_text,
        calculate_percentage, parse_telegram_data
    )

    __all__.extend([
        'format_currency', 'format_datetime', 'format_number',
        'generate_token', 'hash_password', 'verify_password',
        'sanitize_html', 'truncate_text', 'slug_from_text',
        'calculate_percentage', 'parse_telegram_data'
    ])
    logger.info("✅ Helpers импортированы")
except ImportError as e:
    logger.error(f"❌ Ошибка импорта helpers: {e}")


class UtilsRegistry:
    """Реестр всех утилитарных функций"""

    _functions = {}
    _decorators = {}
    _validators = {}
    _initialized = False

    @classmethod
    def register_utils(cls):
        """Регистрация всех утилит"""
        if cls._initialized:
            return

        # Регистрация функций-хелперов
        helper_functions = [
            'format_currency', 'format_datetime', 'format_number',
            'generate_token', 'hash_password', 'verify_password',
            'sanitize_html', 'truncate_text', 'slug_from_text',
            'calculate_percentage', 'parse_telegram_data'
        ]

        cls._functions = {
            name: globals().get(name) for name in helper_functions
            if name in globals()
        }

        # Регистрация декораторов
        decorator_list = [
            'require_telegram_auth', 'rate_limit_decorator', 'cache_response',
            'validate_request_data', 'log_execution_time', 'retry_on_failure',
            'require_user_type', 'sanitize_input'
        ]

        cls._decorators = {
            name: globals().get(name) for name in decorator_list
            if name in globals()
        }

        # Регистрация валидаторов
        validator_list = [
            'validate_telegram_id', 'validate_channel_id', 'validate_price',
            'validate_email', 'validate_phone', 'validate_url'
        ]

        cls._validators = {
            name: globals().get(name) for name in validator_list
            if name in globals()
        }

        cls._initialized = True
        logger.info(
            f"✅ Utils registry: {len(cls._functions)} functions, {len(cls._decorators)} decorators, {len(cls._validators)} validators")

    @classmethod
    def get_available_functions(cls) -> List[str]:
        """Получение списка доступных функций"""
        cls.register_utils()
        return list(cls._functions.keys())

    @classmethod
    def get_available_decorators(cls) -> List[str]:
        """Получение списка доступных декораторов"""
        cls.register_utils()
        return list(cls._decorators.keys())

    @classmethod
    def get_available_validators(cls) -> List[str]:
        """Получение списка доступных валидаторов"""
        cls.register_utils()
        return list(cls._validators.keys())


# Базовые утилитарные функции, если отдельные модули недоступны
def safe_get(dictionary: Dict[str, Any], key: str, default: Any = None) -> Any:
    """Безопасное получение значения из словаря"""
    try:
        return dictionary.get(key, default)
    except (AttributeError, TypeError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    """Безопасное преобразование в integer"""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    """Безопасное преобразование в float"""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_json_loads(json_string: str, default: Any = None) -> Any:
    """Безопасный парсинг JSON"""
    try:
        return json.loads(json_string)
    except (json.JSONDecodeError, TypeError):
        return default if default is not None else {}


def safe_json_dumps(data: Any, default: str = "{}") -> str:
    """Безопасная сериализация в JSON"""
    try:
        return json.dumps(data, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return default


def generate_random_string(length: int = 16, use_hex: bool = True) -> str:
    """Генерация случайной строки"""
    try:
        if use_hex:
            return secrets.token_hex(length // 2)
        else:
            return secrets.token_urlsafe(length)
    except Exception:
        return hashlib.md5(str(datetime.now()).encode()).hexdigest()[:length]


def is_valid_telegram_id(telegram_id: Union[str, int]) -> bool:
    """Базовая проверка Telegram ID"""
    try:
        user_id = int(telegram_id)
        # Telegram user ID должен быть положительным числом
        return user_id > 0 and user_id < 10 ** 12
    except (ValueError, TypeError):
        return False


def is_valid_channel_id(channel_id: str) -> bool:
    """Базовая проверка Telegram Channel ID"""
    if not channel_id or not isinstance(channel_id, str):
        return False

    # Проверяем формат @username или -100xxxxxxxxx
    if channel_id.startswith('@'):
        username = channel_id[1:]
        return bool(re.match(r'^[a-zA-Z][a-zA-Z0-9_]{4,31}$', username))
    elif channel_id.startswith('-100'):
        return channel_id[1:].isdigit() and len(channel_id) >= 10
    else:
        return False


def sanitize_string(text: str, max_length: int = 1000, allow_html: bool = False) -> str:
    """Базовая санитизация строки"""
    if not isinstance(text, str):
        return ""

    # Обрезаем до максимальной длины
    text = text[:max_length]

    # Удаляем HTML теги если не разрешены
    if not allow_html:
        text = re.sub(r'<[^>]+>', '', text)

    # Удаляем лишние пробелы
    text = ' '.join(text.split())

    return text.strip()


def format_price(price: Union[int, float], currency: str = "RUB") -> str:
    """Базовое форматирование цены"""
    try:
        price_num = float(price)
        if currency == "RUB":
            return f"{price_num:,.0f} ₽"
        elif currency == "USD":
            return f"${price_num:,.2f}"
        elif currency == "EUR":
            return f"€{price_num:,.2f}"
        else:
            return f"{price_num:,.2f} {currency}"
    except (ValueError, TypeError):
        return f"0 {currency}"


def format_time_ago(timestamp: Union[str, datetime]) -> str:
    """Базовое форматирование времени 'назад'"""
    try:
        if isinstance(timestamp, str):
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        else:
            dt = timestamp

        now = datetime.now()
        if dt.tzinfo:
            from datetime import timezone
            now = now.replace(tzinfo=timezone.utc)

        diff = now - dt

        if diff.days > 0:
            return f"{diff.days} дн. назад"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} ч. назад"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} мин. назад"
        else:
            return "только что"

    except Exception:
        return "неизвестно"


def calculate_growth_rate(current: Union[int, float], previous: Union[int, float]) -> float:
    """Расчет темпа роста в процентах"""
    try:
        current_num = float(current)
        previous_num = float(previous)

        if previous_num == 0:
            return 100.0 if current_num > 0 else 0.0

        growth = ((current_num - previous_num) / previous_num) * 100
        return round(growth, 2)

    except (ValueError, TypeError, ZeroDivisionError):
        return 0.0


def chunk_list(items: List[Any], chunk_size: int) -> List[List[Any]]:
    """Разбиение списка на чанки"""
    try:
        chunk_size = max(1, int(chunk_size))
        return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]
    except Exception:
        return [items] if items else []


def deep_merge_dicts(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """Глубокое слияние словарей"""
    try:
        result = dict1.copy()

        for key, value in dict2.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = deep_merge_dicts(result[key], value)
            else:
                result[key] = value

        return result

    except Exception:
        return dict1.copy()


def get_client_ip(request_obj=None) -> str:
    """Получение IP адреса клиента"""
    try:
        if request_obj is None:
            from flask import request
            request_obj = request

        # Проверяем заголовки прокси
        if request_obj.environ.get('HTTP_X_FORWARDED_FOR'):
            return request_obj.environ['HTTP_X_FORWARDED_FOR'].split(',')[0].strip()
        elif request_obj.environ.get('HTTP_X_REAL_IP'):
            return request_obj.environ['HTTP_X_REAL_IP']
        else:
            return request_obj.environ.get('REMOTE_ADDR', 'unknown')

    except Exception:
        return 'unknown'


def mask_sensitive_data(data: str, mask_char: str = "*", show_chars: int = 4) -> str:
    """Маскирование чувствительных данных"""
    try:
        if not data or len(data) <= show_chars:
            return mask_char * len(data) if data else ""

        visible_part = data[:show_chars]
        masked_part = mask_char * (len(data) - show_chars)
        return visible_part + masked_part

    except Exception:
        return mask_char * 8


class Timer:
    """Простой таймер для измерения времени выполнения"""

    def __init__(self):
        self.start_time = None
        self.end_time = None

    def start(self):
        """Запуск таймера"""
        self.start_time = datetime.now()
        return self

    def stop(self):
        """Остановка таймера"""
        self.end_time = datetime.now()
        return self

    def elapsed(self) -> float:
        """Получение времени выполнения в секундах"""
        if not self.start_time:
            return 0.0

        end = self.end_time or datetime.now()
        delta = end - self.start_time
        return delta.total_seconds()

    def elapsed_ms(self) -> int:
        """Получение времени выполнения в миллисекундах"""
        return int(self.elapsed() * 1000)


class MemoryCache:
    """Простой кэш в памяти"""

    def __init__(self, default_ttl: int = 300):  # 5 минут по умолчанию
        self._cache = {}
        self._timestamps = {}
        self._default_ttl = default_ttl

    def get(self, key: str) -> Optional[Any]:
        """Получение значения из кэша"""
        if key not in self._cache:
            return None

        # Проверяем TTL
        if self._is_expired(key):
            self.delete(key)
            return None

        return self._cache[key]

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Установка значения в кэш"""
        self._cache[key] = value
        self._timestamps[key] = {
            'created': datetime.now(),
            'ttl': ttl or self._default_ttl
        }

    def delete(self, key: str) -> bool:
        """Удаление значения из кэша"""
        deleted = key in self._cache
        self._cache.pop(key, None)
        self._timestamps.pop(key, None)
        return deleted

    def clear(self) -> None:
        """Очистка всего кэша"""
        self._cache.clear()
        self._timestamps.clear()

    def _is_expired(self, key: str) -> bool:
        """Проверка истечения TTL"""
        if key not in self._timestamps:
            return True

        timestamp_info = self._timestamps[key]
        created = timestamp_info['created']
        ttl = timestamp_info['ttl']

        return (datetime.now() - created).total_seconds() > ttl

    def cleanup_expired(self) -> int:
        """Очистка истекших записей"""
        expired_keys = [
            key for key in self._cache.keys()
            if self._is_expired(key)
        ]

        for key in expired_keys:
            self.delete(key)

        return len(expired_keys)


# Глобальный экземпляр кэша
_global_cache = MemoryCache()


def get_cache() -> MemoryCache:
    """Получение глобального кэша"""
    return _global_cache


def initialize_utils() -> Dict[str, Any]:
    """Инициализация утилит"""
    results = {
        'utils_available': True,
        'cache_initialized': True,
        'registry_loaded': False
    }

    try:
        # Регистрируем утилиты
        UtilsRegistry.register_utils()
        results['registry_loaded'] = True

        # Получаем статистику
        results['functions_count'] = len(UtilsRegistry.get_available_functions())
        results['decorators_count'] = len(UtilsRegistry.get_available_decorators())
        results['validators_count'] = len(UtilsRegistry.get_available_validators())

        logger.info(
            f"✅ Utils инициализированы: {results['functions_count']} функций, {results['decorators_count']} декораторов")

    except Exception as e:
        results['error'] = str(e)
        logger.error(f"❌ Ошибка инициализации utils: {e}")

    return results


def get_utils_status() -> Dict[str, Any]:
    """Получение статуса утилит"""
    try:
        UtilsRegistry.register_utils()

        return {
            'available_functions': UtilsRegistry.get_available_functions(),
            'available_decorators': UtilsRegistry.get_available_decorators(),
            'available_validators': UtilsRegistry.get_available_validators(),
            'cache_items': len(_global_cache._cache),
            'utils_initialized': True
        }

    except Exception as e:
        return {
            'error': str(e),
            'utils_initialized': False
        }


# Добавляем базовые утилиты в экспорт
__all__.extend([
    'UtilsRegistry', 'Timer', 'MemoryCache', 'get_cache',
    'safe_get', 'safe_int', 'safe_float', 'safe_json_loads', 'safe_json_dumps',
    'generate_random_string', 'is_valid_telegram_id', 'is_valid_channel_id',
    'sanitize_string', 'format_price', 'format_time_ago', 'calculate_growth_rate',
    'chunk_list', 'deep_merge_dicts', 'get_client_ip', 'mask_sensitive_data',
    'initialize_utils', 'get_utils_status'
])

# Автоматическая инициализация при импорте
try:
    _init_results = initialize_utils()
    if _init_results.get('utils_available'):
        logger.info("🎉 Utils модуль успешно инициализирован")
    else:
        logger.warning("⚠️ Utils модуль инициализирован частично")
except Exception as e:
    logger.error(f"❌ Критическая ошибка инициализации utils: {e}")

# Метаинформация
__version__ = '1.0.0'
__author__ = 'Telegram Mini App Team'
__description__ = 'Утилиты и вспомогательные функции для Telegram Mini App'