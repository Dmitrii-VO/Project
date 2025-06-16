# app/utils/decorators.py
"""
Декораторы для Telegram Mini App
Содержит все декораторы для аутентификации, rate limiting, кэширования и валидации
"""

import time
import json
import hashlib
import logging
from typing import Optional, Dict, Any, Callable
from functools import wraps
from datetime import datetime, timedelta

# Flask импорты
try:
    from flask import request, jsonify, current_app, g, session

    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    request = None
    jsonify = None
    current_app = None
    g = None
    session = None

logger = logging.getLogger(__name__)

# Глобальные кэши для декораторов
_rate_limit_cache = {}
_response_cache = {}
_security_events = []


# === АУТЕНТИФИКАЦИЯ ===

def require_telegram_auth(f):
    """
    Декоратор для обязательной Telegram аутентификации

    Использование:
    @require_telegram_auth
    def protected_route():
        return "Только для аутентифицированных пользователей"
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not FLASK_AVAILABLE:
            return {"error": "Flask not available"}, 500

        # Получаем Telegram User ID из заголовков или сессии
        telegram_user_id = None

        # Проверяем заголовки
        if hasattr(request, 'headers'):
            telegram_user_id = request.headers.get('X-Telegram-User-Id')

        # Проверяем сессию
        if not telegram_user_id and hasattr(session, 'get'):
            telegram_user_id = session.get('telegram_user_id')

        # Проверяем данные Telegram WebApp
        if not telegram_user_id and hasattr(request, 'json'):
            try:
                data = request.get_json(silent=True) or {}
                if 'initData' in data:
                    # Парсинг initData от Telegram WebApp
                    telegram_user_id = _parse_telegram_init_data(data['initData'])
            except:
                pass

        if not telegram_user_id:
            return jsonify({
                'error': 'Authentication required',
                'message': 'Telegram authentication is required for this endpoint'
            }), 401

        # Сохраняем в g для использования в маршруте
        if hasattr(g, '__setattr__'):
            g.telegram_user_id = telegram_user_id
            g.current_user_id = telegram_user_id

        return f(*args, **kwargs)

    return decorated_function


def _parse_telegram_init_data(init_data: str) -> Optional[str]:
    """Парсинг initData от Telegram WebApp"""
    try:
        # Простой парсинг для получения user_id
        # В реальном приложении нужна полная валидация подписи
        if 'user=' in init_data:
            user_part = init_data.split('user=')[1].split('&')[0]
            user_data = json.loads(user_part)
            return str(user_data.get('id'))
    except:
        pass
    return None


# === RATE LIMITING ===

def rate_limit_decorator(max_requests: int = 10, window: int = 60):
    """
    Декоратор для rate limiting маршрутов

    Args:
        max_requests: Максимальное количество запросов
        window: Временное окно в секундах

    Использование:
    @rate_limit_decorator(max_requests=5, window=60)
    def limited_route():
        return "Максимум 5 запросов в минуту"
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not FLASK_AVAILABLE:
                return {"error": "Flask not available"}, 500

            # Получаем идентификатор клиента
            client_ip = request.remote_addr if hasattr(request, 'remote_addr') else 'unknown'
            route_key = f"{request.endpoint}:{client_ip}" if hasattr(request, 'endpoint') else f"unknown:{client_ip}"
            current_time = time.time()

            # Очищаем старые записи
            cutoff_time = current_time - window
            if route_key in _rate_limit_cache:
                _rate_limit_cache[route_key] = [
                    timestamp for timestamp in _rate_limit_cache[route_key]
                    if timestamp > cutoff_time
                ]
            else:
                _rate_limit_cache[route_key] = []

            # Проверяем лимит
            if len(_rate_limit_cache[route_key]) >= max_requests:
                logger.warning(f"Rate limit exceeded for {route_key}")
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'message': f'Maximum {max_requests} requests per {window} seconds',
                    'retry_after': window
                }), 429

            # Добавляем текущий запрос
            _rate_limit_cache[route_key].append(current_time)

            return f(*args, **kwargs)

        return decorated_function

    return decorator


# === КЭШИРОВАНИЕ ===

def cache_response(timeout: int = 300):
    """
    Декоратор для кэширования ответов

    Args:
        timeout: Время жизни кэша в секундах

    Использование:
    @cache_response(timeout=600)  # 10 минут
    def cached_route():
        return expensive_calculation()
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not FLASK_AVAILABLE:
                return f(*args, **kwargs)

            # Создаем ключ кэша
            cache_key = _generate_cache_key(f.__name__, request)
            current_time = time.time()

            # Проверяем кэш
            if cache_key in _response_cache:
                cached_data = _response_cache[cache_key]
                if current_time - cached_data['timestamp'] < timeout:
                    logger.debug(f"Cache hit for {cache_key}")
                    return cached_data['response']

            # Выполняем функцию и кэшируем результат
            response = f(*args, **kwargs)
            _response_cache[cache_key] = {
                'response': response,
                'timestamp': current_time
            }

            # Очищаем старые записи кэша
            _cleanup_cache(timeout)

            logger.debug(f"Cached response for {cache_key}")
            return response

        return decorated_function

    return decorator


def _generate_cache_key(func_name: str, request_obj) -> str:
    """Генерация ключа кэша"""
    try:
        if not request_obj:
            return f"{func_name}:default"

        # Включаем в ключ метод, путь и параметры
        method = getattr(request_obj, 'method', 'GET')
        path = getattr(request_obj, 'path', 'unknown')
        args = str(sorted(getattr(request_obj, 'args', {}).items()))

        cache_string = f"{func_name}:{method}:{path}:{args}"
        return hashlib.md5(cache_string.encode()).hexdigest()
    except:
        return f"{func_name}:fallback"


def _cleanup_cache(timeout: int):
    """Очистка устаревших записей кэша"""
    try:
        current_time = time.time()
        expired_keys = [
            key for key, data in _response_cache.items()
            if current_time - data['timestamp'] > timeout * 2
        ]
        for key in expired_keys:
            del _response_cache[key]
    except:
        pass


# === ВАЛИДАЦИЯ ===

def validate_request_data(schema: Dict[str, Any]):
    """
    Декоратор для валидации данных запроса

    Args:
        schema: Схема валидации

    Использование:
    @validate_request_data({
        'title': {'required': True, 'type': str, 'max_length': 100},
        'price': {'required': True, 'type': float, 'min_value': 0}
    })
    def create_offer():
        return "Offer created"
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not FLASK_AVAILABLE:
                return f(*args, **kwargs)

            try:
                data = request.get_json() if hasattr(request, 'get_json') else {}
                if not data:
                    data = request.form.to_dict() if hasattr(request, 'form') else {}

                errors = _validate_data(data, schema)
                if errors:
                    return jsonify({
                        'error': 'Validation failed',
                        'errors': errors
                    }), 400

                return f(*args, **kwargs)
            except Exception as e:
                logger.error(f"Validation error: {e}")
                return jsonify({'error': 'Validation error'}), 400

        return decorated_function

    return decorator


def _validate_data(data: Dict[str, Any], schema: Dict[str, Any]) -> list:
    """Валидация данных по схеме"""
    errors = []

    for field, rules in schema.items():
        value = data.get(field)

        # Проверка обязательности
        if rules.get('required', False) and value is None:
            errors.append(f"Field '{field}' is required")
            continue

        if value is None:
            continue

        # Проверка типа
        expected_type = rules.get('type')
        if expected_type and not isinstance(value, expected_type):
            errors.append(f"Field '{field}' must be of type {expected_type.__name__}")
            continue

        # Проверка длины строки
        if isinstance(value, str):
            max_length = rules.get('max_length')
            if max_length and len(value) > max_length:
                errors.append(f"Field '{field}' must not exceed {max_length} characters")

            min_length = rules.get('min_length')
            if min_length and len(value) < min_length:
                errors.append(f"Field '{field}' must be at least {min_length} characters")

        # Проверка числовых значений
        if isinstance(value, (int, float)):
            min_value = rules.get('min_value')
            if min_value is not None and value < min_value:
                errors.append(f"Field '{field}' must be at least {min_value}")

            max_value = rules.get('max_value')
            if max_value is not None and value > max_value:
                errors.append(f"Field '{field}' must not exceed {max_value}")

    return errors


# === ЛОГИРОВАНИЕ И МОНИТОРИНГ ===

def log_execution_time(f):
    """
    Декоратор для логирования времени выполнения

    Использование:
    @log_execution_time
    def slow_function():
        time.sleep(1)
        return "Done"
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = time.time()
        try:
            result = f(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(f"Function {f.__name__} executed in {execution_time:.3f}s")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Function {f.__name__} failed after {execution_time:.3f}s: {e}")
            raise

    return decorated_function


# === ПОВТОРНЫЕ ПОПЫТКИ ===

def retry_on_failure(max_attempts: int = 3, delay: float = 1.0):
    """
    Декоратор для повторных попыток при ошибках

    Args:
        max_attempts: Максимальное количество попыток
        delay: Задержка между попытками в секундах

    Использование:
    @retry_on_failure(max_attempts=3, delay=2.0)
    def unreliable_function():
        # Может упасть, но будет повторена
        return external_api_call()
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return f(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(f"Attempt {attempt + 1} failed for {f.__name__}: {e}. Retrying in {delay}s...")
                        time.sleep(delay)
                    else:
                        logger.error(f"All {max_attempts} attempts failed for {f.__name__}")

            raise last_exception

        return decorated_function

    return decorator


# === ДОПОЛНИТЕЛЬНЫЕ ДЕКОРАТОРЫ ===

def require_user_type(user_type: str):
    """
    Декоратор для проверки типа пользователя

    Args:
        user_type: Требуемый тип пользователя ('advertiser', 'channel_owner', 'admin')
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Заглушка - в реальном приложении нужна проверка типа пользователя из БД
            logger.debug(f"Checking user type requirement: {user_type}")
            return f(*args, **kwargs)

        return decorated_function

    return decorator


def sanitize_input(f):
    """
    Декоратор для санитизации входных данных

    Использование:
    @sanitize_input
    def process_user_input():
        data = request.get_json()
        # data будет очищена от потенциально опасного содержимого
        return data
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if FLASK_AVAILABLE and hasattr(request, 'get_json'):
            try:
                # Простая санитизация - в реальном приложении нужна более сложная логика
                data = request.get_json(silent=True)
                if data:
                    _sanitize_dict(data)
            except:
                pass

        return f(*args, **kwargs)

    return decorated_function


def _sanitize_dict(data: Dict[str, Any]):
    """Рекурсивная санитизация словаря"""
    dangerous_patterns = ['<script', 'javascript:', 'onload=', 'onerror=']

    for key, value in data.items():
        if isinstance(value, str):
            for pattern in dangerous_patterns:
                if pattern.lower() in value.lower():
                    data[key] = value.replace(pattern, '')
        elif isinstance(value, dict):
            _sanitize_dict(value)


# === ЭКСПОРТ ===

__all__ = [
    'require_telegram_auth',
    'rate_limit_decorator',
    'cache_response',
    'validate_request_data',
    'log_execution_time',
    'retry_on_failure',
    'require_user_type',
    'sanitize_input'
]