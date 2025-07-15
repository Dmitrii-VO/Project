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
    Заглушка декоратора аутентификации (отключена)
    
    Использование:
    @require_telegram_auth
    def protected_route():
        return "Доступ разрешен всем"
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Аутентификация отключена - разрешаем доступ всем
        if FLASK_AVAILABLE and hasattr(g, '__setattr__'):
            g.telegram_id = "test_user_123"
            g.current_user_id = "test_user_123"
        
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


# === ДОПОЛНИТЕЛЬНЫЕ ДЕКОРАТОРЫ (НЕИСПОЛЬЗУЕМЫЕ - УДАЛЕНЫ) ===
# Удалены неиспользуемые функции: validate_request_data, log_execution_time, 
# retry_on_failure, require_user_type, sanitize_input


# === ЭКСПОРТ ===

__all__ = [
    'require_telegram_auth',
    'rate_limit_decorator',
    'cache_response'
]