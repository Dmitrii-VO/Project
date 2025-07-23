# app/security/rate_limiting.py
"""
Rate Limiting для Telegram Mini App
Защита от DDoS атак и чрезмерного использования API
"""

import time
from typing import Optional, Dict, Any

# Опциональный импорт Redis
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    REDIS_AVAILABLE = False
from flask import Flask, request, jsonify, g, current_app
from functools import wraps
import logging

logger = logging.getLogger(__name__)

class RateLimiter:
    """
    Rate Limiter с поддержкой Redis и in-memory storage
    """
    
    def __init__(self, app: Flask = None, redis_client=None):
        self.app = app
        self.redis_client = redis_client
        self.in_memory_cache = {}  # Fallback для случаев без Redis
        self.cleanup_interval = 300  # Очистка кэша каждые 5 минут
        self.last_cleanup = time.time()
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """Инициализация rate limiter"""
        # Пытаемся подключиться к Redis
        if self.redis_client is None and REDIS_AVAILABLE:
            try:
                redis_url = app.config.get('REDIS_URL', 'redis://localhost:6379/0')
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                # Проверяем соединение
                self.redis_client.ping()
                logger.info("✅ Redis connected for rate limiting")
            except Exception as e:
                logger.warning(f"⚠️ Redis not available, using in-memory cache: {e}")
                self.redis_client = None
        elif not REDIS_AVAILABLE:
            logger.warning("⚠️ Redis module not installed, using in-memory cache")
            self.redis_client = None
        
        app.extensions['rate_limiter'] = self
        
        # Добавляем middleware
        app.before_request(self._check_rate_limits)
    
    def _check_rate_limits(self):
        """Проверка rate limits для входящих запросов"""
        # Пропускаем статические файлы
        if request.endpoint and request.endpoint.startswith('static'):
            return
        
        # Получаем идентификатор пользователя
        user_id = self._get_user_identifier()
        
        # Проверяем глобальные лимиты
        if not self._check_limit(f"global:{user_id}", 200, 3600):  # 200 req/hour globally
            return self._rate_limit_exceeded("Too many requests per hour")
        
        # Проверяем лимиты для API endpoints
        if request.path.startswith('/api/'):
            if not self._check_limit(f"api:{user_id}", 100, 300):  # 100 req/5min for API
                return self._rate_limit_exceeded("Too many API requests")
        
        # Специальные лимиты для чувствительных операций
        sensitive_paths = ['/api/offers/', '/api/proposals/', '/api/channels/']
        for path in sensitive_paths:
            if request.path.startswith(path) and request.method in ['POST', 'PUT', 'DELETE']:
                if not self._check_limit(f"sensitive:{user_id}", 20, 300):  # 20 req/5min
                    return self._rate_limit_exceeded("Too many sensitive operations")
        
        # Лимиты для аутентификации
        if request.path in ['/api/auth/login', '/api/auth/register']:
            if not self._check_limit(f"auth:{user_id}", 5, 300):  # 5 req/5min
                return self._rate_limit_exceeded("Too many authentication attempts")
    
    def _get_user_identifier(self) -> str:
        """Получение идентификатора пользователя для rate limiting"""
        # Приоритет: Telegram User ID > IP адрес
        user_id = request.headers.get('X-Telegram-User-Id')
        if user_id:
            return f"telegram:{user_id}"
        
        # Fallback на IP адрес
        ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        if ip:
            # Берем первый IP из списка (в случае proxy)
            ip = ip.split(',')[0].strip()
        return f"ip:{ip or 'unknown'}"
    
    def _check_limit(self, key: str, limit: int, window: int) -> bool:
        """
        Проверка лимита запросов
        
        Args:
            key: Ключ для идентификации пользователя/операции
            limit: Максимальное количество запросов
            window: Временное окно в секундах
        """
        current_time = int(time.time())
        
        if self.redis_client:
            return self._check_limit_redis(key, limit, window, current_time)
        else:
            return self._check_limit_memory(key, limit, window, current_time)
    
    def _check_limit_redis(self, key: str, limit: int, window: int, current_time: int) -> bool:
        """Проверка лимита через Redis"""
        try:
            pipe = self.redis_client.pipeline()
            
            # Sliding window log
            window_start = current_time - window
            
            # Удаляем устаревшие записи
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Добавляем текущий запрос
            pipe.zadd(key, {str(current_time): current_time})
            
            # Получаем количество запросов в окне
            pipe.zcard(key)
            
            # Устанавливаем TTL
            pipe.expire(key, window)
            
            results = pipe.execute()
            request_count = results[2]  # Результат zcard
            
            return request_count <= limit
            
        except Exception as e:
            logger.error(f"Redis rate limiting error: {e}")
            # Fallback на in-memory при ошибке Redis
            return self._check_limit_memory(key, limit, window, current_time)
    
    def _check_limit_memory(self, key: str, limit: int, window: int, current_time: int) -> bool:
        """Проверка лимита через in-memory cache (fallback)"""
        # Периодическая очистка кэша
        if current_time - self.last_cleanup > self.cleanup_interval:
            self._cleanup_memory_cache(current_time)
            self.last_cleanup = current_time
        
        if key not in self.in_memory_cache:
            self.in_memory_cache[key] = []
        
        requests = self.in_memory_cache[key]
        window_start = current_time - window
        
        # Удаляем устаревшие запросы
        requests[:] = [req_time for req_time in requests if req_time > window_start]
        
        # Добавляем текущий запрос
        requests.append(current_time)
        
        return len(requests) <= limit
    
    def _cleanup_memory_cache(self, current_time: int):
        """Очистка устаревших записей из in-memory cache"""
        keys_to_remove = []
        
        for key, requests in self.in_memory_cache.items():
            # Удаляем записи старше 1 часа
            cutoff_time = current_time - 3600
            requests[:] = [req_time for req_time in requests if req_time > cutoff_time]
            
            # Удаляем пустые ключи
            if not requests:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.in_memory_cache[key]
        
        logger.debug(f"Cleaned up {len(keys_to_remove)} expired rate limit keys")
    
    def _rate_limit_exceeded(self, message: str):
        """Ответ при превышении лимита"""
        user_id = self._get_user_identifier()
        logger.warning(f"Rate limit exceeded: {user_id} on {request.path} - {message}")
        
        return jsonify({
            'error': 'Rate Limit Exceeded',
            'message': message,
            'retry_after': 300  # Рекомендуемое время ожидания
        }), 429


def setup_rate_limiting(app: Flask) -> RateLimiter:
    """Настройка rate limiting для приложения"""
    rate_limiter = RateLimiter(app)
    
    # Добавляем endpoint для проверки статуса лимитов
    @app.route('/api/rate-limit-status', methods=['GET'])
    def rate_limit_status():
        """Получение текущего статуса rate limits"""
        user_id = rate_limiter._get_user_identifier()
        
        # Проверяем различные лимиты
        limits = {
            'global': rate_limiter._check_limit(f"global:{user_id}", 200, 3600),
            'api': rate_limiter._check_limit(f"api:{user_id}", 100, 300),
            'sensitive': rate_limiter._check_limit(f"sensitive:{user_id}", 20, 300)
        }
        
        return jsonify({
            'user_id': user_id,
            'limits': limits,
            'limits_info': {
                'global': '200 requests per hour',
                'api': '100 requests per 5 minutes',
                'sensitive': '20 operations per 5 minutes'
            }
        })
    
    logger.info("✅ Rate Limiting initialized")
    return rate_limiter


def rate_limit(limit: int, window: int, key_func=None):
    """
    Декоратор для установки custom rate limits на endpoints
    
    Args:
        limit: Максимальное количество запросов
        window: Временное окно в секундах
        key_func: Функция для генерации ключа (по умолчанию - user identifier)
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            rate_limiter = current_app.extensions.get('rate_limiter')
            if not rate_limiter:
                # Если rate limiter не настроен, пропускаем проверку
                return f(*args, **kwargs)
            
            # Генерируем ключ
            if key_func:
                key = key_func()
            else:
                key = f"custom:{rate_limiter._get_user_identifier()}:{f.__name__}"
            
            if not rate_limiter._check_limit(key, limit, window):
                return jsonify({
                    'error': 'Rate Limit Exceeded',
                    'message': f'Too many requests to {f.__name__}',
                    'retry_after': window
                }), 429
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator