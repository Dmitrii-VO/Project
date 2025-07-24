#!/usr/bin/env python3
"""
WebApp Optimizer для Telegram Mini App
Утилиты для оптимизации производительности на мобильных устройствах
"""

import json
import gzip
import hashlib
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, g, current_app
import logging

logger = logging.getLogger(__name__)

class WebAppOptimizer:
    """Класс для оптимизации WebApp производительности"""
    
    def __init__(self):
        self.cache_storage = {}
        self.compression_enabled = True
        self.mobile_detection_enabled = True
    
    def is_mobile_request(self, user_agent=None):
        """Определение мобильного устройства"""
        if not user_agent:
            try:
                user_agent = request.headers.get('User-Agent', '').lower()
            except RuntimeError:
                # Если нет request context, используем переданный user_agent или возвращаем False
                user_agent = user_agent.lower() if user_agent else ''
        else:
            user_agent = user_agent.lower()
        
        mobile_indicators = [
            'mobile', 'android', 'iphone', 'ipad', 'tablet',
            'webview', 'telegram', 'tgwebapp'
        ]
        
        return any(indicator in user_agent for indicator in mobile_indicators)
    
    def get_device_info(self):
        """Получение информации об устройстве"""
        try:
            user_agent = request.headers.get('User-Agent', '')
        except RuntimeError:
            # Если нет request context, используем базовые значения
            user_agent = ''
        
        device_info = {
            'is_mobile': self.is_mobile_request(user_agent),
            'is_telegram': 'telegram' in user_agent.lower(),
            'is_webview': 'webview' in user_agent.lower(),
            'platform': 'unknown'
        }
        
        # Определяем платформу
        ua_lower = user_agent.lower()
        if 'android' in ua_lower:
            device_info['platform'] = 'android'
        elif 'iphone' in ua_lower or 'ipad' in ua_lower:
            device_info['platform'] = 'ios'
        elif 'windows' in ua_lower:
            device_info['platform'] = 'windows'
        elif 'mac' in ua_lower:
            device_info['platform'] = 'macos'
        elif 'linux' in ua_lower:
            device_info['platform'] = 'linux'
        
        return device_info
    
    def compress_json_response(self, data):
        """Сжатие JSON ответа"""
        if not self.compression_enabled:
            return data
        
        try:
            # Убираем пустые значения для экономии трафика
            if isinstance(data, dict):
                return self._clean_dict(data)
            elif isinstance(data, list):
                return [self._clean_dict(item) if isinstance(item, dict) else item for item in data]
            return data
        except Exception as e:
            logger.warning(f"JSON compression error: {e}")
            return data
    
    def _clean_dict(self, d):
        """Очистка словаря от пустых значений"""
        if not isinstance(d, dict):
            return d
        
        cleaned = {}
        for key, value in d.items():
            if value is not None and value != '' and value != []:
                if isinstance(value, dict):
                    cleaned_value = self._clean_dict(value)
                    if cleaned_value:  # Только если словарь не пустой
                        cleaned[key] = cleaned_value
                elif isinstance(value, list):
                    cleaned_list = [self._clean_dict(item) if isinstance(item, dict) else item for item in value]
                    if cleaned_list:  # Только если список не пустой
                        cleaned[key] = cleaned_list
                else:
                    cleaned[key] = value
        
        return cleaned
    
    def create_cache_key(self, prefix, *args):
        """Создание ключа кеша"""
        key_string = f"{prefix}_{('_'.join(str(arg) for arg in args))}"
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def get_cached_data(self, cache_key, max_age_seconds=300):
        """Получение данных из кеша"""
        if cache_key not in self.cache_storage:
            return None
        
        cached_item = self.cache_storage[cache_key]
        cache_time = cached_item.get('timestamp')
        
        if not cache_time:
            return None
        
        # Проверяем возраст кеша
        if datetime.now() - cache_time > timedelta(seconds=max_age_seconds):
            del self.cache_storage[cache_key]
            return None
        
        return cached_item.get('data')
    
    def set_cached_data(self, cache_key, data):
        """Сохранение данных в кеш"""
        self.cache_storage[cache_key] = {
            'data': data,
            'timestamp': datetime.now()
        }
    
    def clear_cache(self, prefix=None):
        """Очистка кеша"""
        if prefix:
            keys_to_delete = [k for k in self.cache_storage.keys() if k.startswith(prefix)]
            for key in keys_to_delete:
                del self.cache_storage[key]
        else:
            self.cache_storage.clear()
    
    def optimize_for_mobile(self, data, max_items=None):
        """Оптимизация данных для мобильных устройств"""
        if not self.is_mobile_request():
            return data
        
        optimized_data = self.compress_json_response(data)
        
        # Ограничиваем количество элементов для мобильных
        if max_items and isinstance(optimized_data, list):
            optimized_data = optimized_data[:max_items]
        elif max_items and isinstance(optimized_data, dict):
            # Если это словарь с массивом данных
            for key in ['channels', 'offers', 'proposals', 'items', 'data']:
                if key in optimized_data and isinstance(optimized_data[key], list):
                    optimized_data[key] = optimized_data[key][:max_items]
        
        return optimized_data
    
    def get_cache_headers(self, max_age=300):
        """Получение заголовков кеширования"""
        headers = {}
        
        if self.is_mobile_request():
            # Более агрессивное кеширование для мобильных
            headers['Cache-Control'] = f'public, max-age={max_age}'
            headers['X-Mobile-Optimized'] = 'true'
        else:
            # Обычное кеширование для десктопа
            headers['Cache-Control'] = f'public, max-age={max_age // 2}'
        
        headers['ETag'] = f'"{hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()}"'
        return headers

# Глобальный экземпляр оптимизатора
webapp_optimizer = WebAppOptimizer()

# ================================================================
# ДЕКОРАТОРЫ ДЛЯ ОПТИМИЗАЦИИ
# ================================================================

def mobile_optimized(max_age=300, max_items=None):
    """Декоратор для оптимизации endpoint'ов под мобильные устройства"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Получаем данные об устройстве
            device_info = webapp_optimizer.get_device_info()
            g.device_info = device_info
            
            # Создаем ключ кеша
            cache_key = webapp_optimizer.create_cache_key(
                f.__name__, 
                request.path, 
                str(request.args),
                device_info['platform']
            )
            
            # Проверяем кеш для мобильных устройств
            if device_info['is_mobile']:
                cached_data = webapp_optimizer.get_cached_data(cache_key, max_age)
                if cached_data:
                    response = jsonify(cached_data)
                    for header, value in webapp_optimizer.get_cache_headers(max_age).items():
                        response.headers[header] = value
                    response.headers['X-Cache-Hit'] = 'true'
                    return response
            
            # Выполняем функцию
            result = f(*args, **kwargs)
            
            # Оптимизируем результат для мобильных
            if hasattr(result, 'get_json'):
                data = result.get_json()
                if data:
                    optimized_data = webapp_optimizer.optimize_for_mobile(data, max_items)
                    
                    # Кешируем результат для мобильных
                    if device_info['is_mobile']:
                        webapp_optimizer.set_cached_data(cache_key, optimized_data)
                    
                    response = jsonify(optimized_data)
                    for header, value in webapp_optimizer.get_cache_headers(max_age).items():
                        response.headers[header] = value
                    response.headers['X-Cache-Hit'] = 'false'
                    return response
            
            return result
        return decorated_function
    return decorator

def webapp_cache(seconds=300, mobile_boost=2):
    """Декоратор для кеширования с учетом типа устройства"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            device_info = webapp_optimizer.get_device_info()
            
            # Увеличиваем время кеша для мобильных устройств
            cache_time = seconds * mobile_boost if device_info['is_mobile'] else seconds
            
            cache_key = webapp_optimizer.create_cache_key(
                f.__name__, 
                request.path, 
                str(request.args)
            )
            
            # Проверяем кеш
            cached_data = webapp_optimizer.get_cached_data(cache_key, cache_time)
            if cached_data:
                response = jsonify(cached_data)
                response.headers['X-Cache-Hit'] = 'true'
                response.headers['Cache-Control'] = f'public, max-age={cache_time}'
                return response
            
            # Выполняем функцию и кешируем результат
            result = f(*args, **kwargs)
            
            if hasattr(result, 'get_json'):
                data = result.get_json()
                if data:
                    webapp_optimizer.set_cached_data(cache_key, data)
                    
                    response = jsonify(data)
                    response.headers['X-Cache-Hit'] = 'false' 
                    response.headers['Cache-Control'] = f'public, max-age={cache_time}'
                    return response
            
            return result
        return decorated_function
    return decorator

def compress_response(f):
    """Декоратор для сжатия ответов"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        result = f(*args, **kwargs)
        
        if hasattr(result, 'get_json'):
            data = result.get_json()
            if data:
                compressed_data = webapp_optimizer.compress_json_response(data)
                response = jsonify(compressed_data)
                response.headers['X-Compressed'] = 'true'
                return response
        
        return result
    return decorated_function

# ================================================================
# УТИЛИТЫ ДЛЯ ПРОИЗВОДИТЕЛЬНОСТИ
# ================================================================

def get_optimized_page_size():
    """Получение оптимального размера страницы для устройства"""
    device_info = webapp_optimizer.get_device_info()
    
    if device_info['is_mobile']:
        return 20  # Меньше элементов для мобильных
    else:
        return 50  # Больше для десктопа

def should_load_images():
    """Определение, нужно ли загружать изображения"""
    device_info = webapp_optimizer.get_device_info()
    
    # На мобильных устройствах можем ограничить загрузку изображений
    # В зависимости от настроек пользователя или качества соединения
    return True

def get_api_timeout():
    """Получение таймаута API в зависимости от устройства"""
    device_info = webapp_optimizer.get_device_info()
    
    if device_info['is_mobile']:
        return 5  # Меньший таймаут для мобильных
    else:
        return 10  # Больший таймаут для десктопа

# ================================================================
# СТАТИСТИКА ПРОИЗВОДИТЕЛЬНОСТИ
# ================================================================

class PerformanceMonitor:
    """Монитор производительности WebApp"""
    
    def __init__(self):
        self.metrics = {}
    
    def record_request_time(self, endpoint, duration, device_type='unknown'):
        """Запись времени выполнения запроса"""
        key = f"{endpoint}_{device_type}"
        
        if key not in self.metrics:
            self.metrics[key] = {
                'total_time': 0,
                'request_count': 0,
                'avg_time': 0
            }
        
        self.metrics[key]['total_time'] += duration
        self.metrics[key]['request_count'] += 1
        self.metrics[key]['avg_time'] = self.metrics[key]['total_time'] / self.metrics[key]['request_count']
    
    def get_performance_stats(self):
        """Получение статистики производительности"""
        return self.metrics
    
    def get_slow_endpoints(self, threshold=1.0):
        """Получение медленных endpoint'ов"""
        slow_endpoints = {}
        
        for key, metrics in self.metrics.items():
            if metrics['avg_time'] > threshold:
                slow_endpoints[key] = metrics
        
        return slow_endpoints

# Глобальный монитор производительности
performance_monitor = PerformanceMonitor()

def monitor_performance(f):
    """Декоратор для мониторинга производительности"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = datetime.now()
        device_info = webapp_optimizer.get_device_info()
        
        try:
            result = f(*args, **kwargs)
            return result
        finally:
            duration = (datetime.now() - start_time).total_seconds()
            device_type = 'mobile' if device_info['is_mobile'] else 'desktop'
            performance_monitor.record_request_time(f.__name__, duration, device_type)
    
    return decorated_function