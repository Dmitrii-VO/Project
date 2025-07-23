# app/performance/caching.py
"""
Система кэширования для Telegram Mini App
Поддерживает Redis и in-memory fallback для высокой доступности
"""

import json
import time
import hashlib
from typing import Any, Dict, Optional, Callable, Union
from functools import wraps
from flask import Flask, request, current_app
import logging

logger = logging.getLogger(__name__)

# Опциональный импорт Redis
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    REDIS_AVAILABLE = False

class CacheManager:
    """
    Менеджер кэширования с поддержкой Redis и in-memory fallback
    """
    
    def __init__(self, app: Flask = None, redis_client=None):
        self.app = app
        self.redis_client = redis_client
        self.in_memory_cache = {}
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0
        }
        
        # Конфигурация TTL для различных типов данных
        self.default_ttl = {
            'channels_list': 300,        # 5 минут
            'channel_stats': 600,        # 10 минут  
            'categories': 3600,          # 1 час
            'user_channels': 180,        # 3 минуты
            'offers_list': 240,          # 4 минуты
            'proposals_incoming': 60,    # 1 минута
            'analytics': 900,            # 15 минут
            'search_results': 300,       # 5 минут
            'recommendations': 600       # 10 минут
        }
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """Инициализация кэш менеджера"""
        self.app = app
        
        # Пытаемся подключиться к Redis
        if self.redis_client is None and REDIS_AVAILABLE:
            try:
                redis_url = app.config.get('REDIS_URL', 'redis://localhost:6379/1')
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                # Проверяем соединение
                self.redis_client.ping()
                logger.info("✅ Redis connected for caching")
            except Exception as e:
                logger.warning(f"⚠️ Redis not available for caching, using in-memory: {e}")
                self.redis_client = None
        elif not REDIS_AVAILABLE:
            logger.warning("⚠️ Redis module not installed, using in-memory caching")
            self.redis_client = None
        
        app.extensions['cache_manager'] = self
        logger.info("✅ Cache Manager initialized")
    
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Генерация ключа кэша"""
        # Создаем уникальный ключ на основе параметров
        key_data = {
            'args': args,
            'kwargs': kwargs,
            'user_id': getattr(request, 'headers', {}).get('X-Telegram-User-Id') if request else None
        }
        
        key_hash = hashlib.md5(json.dumps(key_data, sort_keys=True).encode()).hexdigest()
        return f"telegram_app:{prefix}:{key_hash}"
    
    def get(self, key: str) -> Optional[Any]:
        """Получение данных из кэша"""
        try:
            if self.redis_client:
                return self._get_from_redis(key)
            else:
                return self._get_from_memory(key)
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            self.cache_stats['misses'] += 1
            return None
    
    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Сохранение данных в кэш"""
        try:
            if self.redis_client:
                return self._set_to_redis(key, value, ttl)
            else:
                return self._set_to_memory(key, value, ttl)
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Удаление данных из кэша"""
        try:
            if self.redis_client:
                result = self.redis_client.delete(key) > 0
            else:
                result = key in self.in_memory_cache
                if result:
                    del self.in_memory_cache[key]
            
            if result:
                self.cache_stats['deletes'] += 1
            return result
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    def invalidate_pattern(self, pattern: str) -> int:
        """Инвалидация кэша по паттерну"""
        try:
            if self.redis_client:
                keys = self.redis_client.keys(pattern)
                if keys:
                    deleted = self.redis_client.delete(*keys)
                    self.cache_stats['deletes'] += deleted
                    return deleted
                return 0
            else:
                # In-memory - удаляем ключи по паттерну
                deleted = 0
                keys_to_delete = [k for k in self.in_memory_cache.keys() if pattern.replace('*', '') in k]
                for key in keys_to_delete:
                    del self.in_memory_cache[key]
                    deleted += 1
                self.cache_stats['deletes'] += deleted
                return deleted
        except Exception as e:
            logger.error(f"Cache invalidate error for pattern {pattern}: {e}")
            return 0
    
    def _get_from_redis(self, key: str) -> Optional[Any]:
        """Получение из Redis"""
        data = self.redis_client.get(key)
        if data:
            self.cache_stats['hits'] += 1
            return json.loads(data)
        else:
            self.cache_stats['misses'] += 1
            return None
    
    def _set_to_redis(self, key: str, value: Any, ttl: int) -> bool:
        """Сохранение в Redis"""
        try:
            serialized = json.dumps(value, ensure_ascii=False, default=str)
            result = self.redis_client.setex(key, ttl, serialized)
            if result:
                self.cache_stats['sets'] += 1
            return result
        except (TypeError, ValueError) as e:
            logger.error(f"Redis serialization error: {e}")
            return False
    
    def _get_from_memory(self, key: str) -> Optional[Any]:
        """Получение из памяти"""
        if key in self.in_memory_cache:
            item = self.in_memory_cache[key]
            if time.time() < item['expires_at']:
                self.cache_stats['hits'] += 1
                return item['value']
            else:
                # Удаляем устаревший элемент
                del self.in_memory_cache[key]
        
        self.cache_stats['misses'] += 1
        return None
    
    def _set_to_memory(self, key: str, value: Any, ttl: int) -> bool:
        """Сохранение в память"""
        try:
            self.in_memory_cache[key] = {
                'value': value,
                'expires_at': time.time() + ttl
            }
            self.cache_stats['sets'] += 1
            
            # Очищаем старые записи каждые 100 операций
            if self.cache_stats['sets'] % 100 == 0:
                self._cleanup_memory_cache()
            
            return True
        except Exception as e:
            logger.error(f"Memory cache error: {e}")
            return False
    
    def _cleanup_memory_cache(self):
        """Очистка устаревших записей из памяти"""
        current_time = time.time()
        expired_keys = [
            key for key, item in self.in_memory_cache.items()
            if current_time >= item['expires_at']
        ]
        
        for key in expired_keys:
            del self.in_memory_cache[key]
        
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики кэша"""
        total_requests = self.cache_stats['hits'] + self.cache_stats['misses']
        hit_rate = (self.cache_stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        stats = {
            'backend': 'redis' if self.redis_client else 'memory',
            'stats': self.cache_stats.copy(),
            'hit_rate': round(hit_rate, 2),
            'memory_entries': len(self.in_memory_cache)
        }
        
        if self.redis_client:
            try:
                info = self.redis_client.info('memory')
                stats['redis_memory'] = {
                    'used_memory': info.get('used_memory'),
                    'used_memory_human': info.get('used_memory_human')
                }
            except:
                pass
        
        return stats

# Глобальный экземпляр менеджера кэша
cache_manager = CacheManager()

def cached(ttl: int = None, key_prefix: str = None, cache_type: str = None):
    """
    Декоратор для кэширования результатов функций
    
    Args:
        ttl: Время жизни кэша в секундах
        key_prefix: Префикс для ключа кэша
        cache_type: Тип кэша для определения TTL по умолчанию
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Получаем cache manager из текущего приложения
            try:
                cache = current_app.extensions.get('cache_manager')
                if not cache:
                    # Если кэш не настроен, выполняем функцию без кэширования
                    return f(*args, **kwargs)
                
                # Определяем TTL
                actual_ttl = ttl
                if actual_ttl is None:
                    actual_ttl = cache.default_ttl.get(cache_type, 300)
                
                # Генерируем ключ
                prefix = key_prefix or f.__name__
                cache_key = cache._generate_key(prefix, *args, **kwargs)
                
                # Пытаемся получить из кэша
                cached_result = cache.get(cache_key)
                if cached_result is not None:
                    logger.debug(f"Cache hit for {f.__name__}")
                    return cached_result
                
                # Выполняем функцию
                result = f(*args, **kwargs)
                
                # Сохраняем результат в кэш
                if result is not None:
                    cache.set(cache_key, result, actual_ttl)
                    logger.debug(f"Cache set for {f.__name__} with TTL {actual_ttl}")
                
                return result
                
            except Exception as e:
                logger.error(f"Cache decorator error in {f.__name__}: {e}")
                # В случае ошибки кэша выполняем функцию без кэширования
                return f(*args, **kwargs)
        
        return wrapper
    return decorator

def cache_invalidate(patterns: Union[str, list]):
    """
    Декоратор для инвалидации кэша после выполнения функции
    
    Args:
        patterns: Паттерн или список паттернов для инвалидации
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args, **kwargs):
            result = f(*args, **kwargs)
            
            try:
                cache = current_app.extensions.get('cache_manager')
                if cache:
                    if isinstance(patterns, str):
                        pattern_list = [patterns]
                    else:
                        pattern_list = patterns
                    
                    for pattern in pattern_list:
                        deleted = cache.invalidate_pattern(f"telegram_app:{pattern}:*")
                        logger.debug(f"Invalidated {deleted} cache entries for pattern {pattern}")
                        
            except Exception as e:
                logger.error(f"Cache invalidation error in {f.__name__}: {e}")
            
            return result
        return wrapper
    return decorator

def setup_caching(app: Flask) -> CacheManager:
    """Настройка системы кэширования для приложения"""
    cache = CacheManager(app)
    
    # Добавляем endpoint для статистики кэша
    @app.route('/api/cache/stats', methods=['GET'])
    def cache_stats():
        """Статистика кэширования (только для администратора)"""
        user_id = request.headers.get('X-Telegram-User-Id')
        
        # Проверяем права администратора
        if user_id != '373086959':
            return {'error': 'Access denied'}, 403
        
        try:
            stats = cache.get_stats()
            return {
                'success': True,
                'cache_stats': stats
            }
        except Exception as e:
            logger.error(f"Cache stats error: {e}")
            return {'success': False, 'error': str(e)}, 500
    
    # Endpoint для очистки кэша
    @app.route('/api/cache/clear', methods=['POST'])
    def clear_cache():
        """Очистка кэша (только для администратора)"""
        user_id = request.headers.get('X-Telegram-User-Id')
        
        if user_id != '373086959':
            return {'error': 'Access denied'}, 403
        
        try:
            pattern = request.json.get('pattern', '*') if request.is_json else '*'
            deleted = cache.invalidate_pattern(f"telegram_app:{pattern}:*")
            
            return {
                'success': True,
                'message': f'Cleared {deleted} cache entries',
                'pattern': pattern
            }
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return {'success': False, 'error': str(e)}, 500
    
    logger.info("✅ Caching system configured")
    return cache

logger.info("✅ Caching module initialized")