# app/performance/monitoring.py
"""
Система мониторинга производительности для Telegram Mini App
Отслеживает метрики API, базы данных и пользовательской активности
"""

import time
import json
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict, deque
from flask import Flask, request, g, current_app
from functools import wraps
import logging

logger = logging.getLogger(__name__)

class PerformanceMonitor:
    """
    Класс для мониторинга производительности приложения
    """
    
    def __init__(self, app: Flask = None):
        self.app = app
        self.metrics = {
            'requests': defaultdict(list),
            'response_times': defaultdict(list),
            'error_rates': defaultdict(int),
            'database_queries': defaultdict(list),
            'cache_stats': defaultdict(int),
            'user_activity': defaultdict(int)
        }
        
        # Настройки мониторинга
        self.max_metrics_age = 3600  # 1 час
        self.slow_request_threshold = 1.0  # 1 секунда
        self.metrics_lock = threading.Lock()
        
        # Счетчики для текущего периода
        self.current_period = {
            'start_time': time.time(),
            'requests_count': 0,
            'errors_count': 0,
            'slow_requests': 0
        }
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """Инициализация системы мониторинга"""
        self.app = app
        
        # Добавляем middleware для отслеживания запросов
        app.before_request(self._before_request)
        app.after_request(self._after_request)
        
        # Периодическая очистка старых метрик
        self._schedule_cleanup()
        
        app.extensions['performance_monitor'] = self
        logger.info("✅ Performance Monitor initialized")
    
    def _before_request(self):
        """Обработка начала запроса"""
        g.start_time = time.time()
        g.request_id = f"{int(time.time())}-{hash(request.path + str(time.time()))}"
        
        # Увеличиваем счетчик запросов
        with self.metrics_lock:
            self.current_period['requests_count'] += 1
    
    def _after_request(self, response):
        """Обработка завершения запроса"""  
        try:
            if not hasattr(g, 'start_time'):
                return response
            
            # Вычисляем время выполнения
            execution_time = time.time() - g.start_time
            endpoint = request.endpoint or request.path
            method = request.method
            status_code = response.status_code
            
            # Записываем метрики
            self._record_request_metrics(
                endpoint=endpoint,
                method=method,
                status_code=status_code,
                execution_time=execution_time
            )
            
            # Проверяем на медленные запросы
            if execution_time > self.slow_request_threshold:
                self._record_slow_request(endpoint, method, execution_time)
            
            # Записываем ошибки
            if status_code >= 400:
                self._record_error(endpoint, status_code)
            
        except Exception as e:
            logger.error(f"Monitoring error: {e}")
        
        return response
    
    def _record_request_metrics(self, endpoint: str, method: str, status_code: int, execution_time: float):
        """Запись метрик запроса"""
        current_time = time.time()
        metric_key = f"{method}_{endpoint}"
        
        with self.metrics_lock:
            # Запись времени выполнения
            self.metrics['response_times'][metric_key].append({
                'timestamp': current_time,
                'execution_time': execution_time,
                'status_code': status_code
            })
            
            # Запись общей статистики запросов
            self.metrics['requests'][endpoint].append({
                'timestamp': current_time,
                'method': method,
                'status_code': status_code,
                'execution_time': execution_time
            })
    
    def _record_slow_request(self, endpoint: str, method: str, execution_time: float):
        """Запись медленного запроса"""
        with self.metrics_lock:
            self.current_period['slow_requests'] += 1
        
        logger.warning(
            f"Slow request: {method} {endpoint} took {execution_time:.3f}s"
        )
    
    def _record_error(self, endpoint: str, status_code: int):
        """Запись ошибки"""
        with self.metrics_lock:
            self.metrics['error_rates'][f"{endpoint}_{status_code}"] += 1
            self.current_period['errors_count'] += 1
    
    def record_database_query(self, query_type: str, execution_time: float, rows_affected: int = 0):
        """Запись метрик запроса к БД"""
        current_time = time.time()
        
        with self.metrics_lock:
            self.metrics['database_queries'][query_type].append({
                'timestamp': current_time,
                'execution_time': execution_time,
                'rows_affected': rows_affected
            })
    
    def record_cache_operation(self, operation: str, hit: bool = None):
        """Запись операции с кэшем"""
        with self.metrics_lock:
            self.metrics['cache_stats'][f'cache_{operation}'] += 1
            if hit is not None:
                self.metrics['cache_stats'][f'cache_{"hit" if hit else "miss"}'] += 1
    
    def record_user_activity(self, user_id: str, action: str):
        """Запись активности пользователя"""
        with self.metrics_lock:
            self.metrics['user_activity'][f'user_{action}'] += 1
            self.metrics['user_activity'][f'active_users'] = len(
                set(key.split('_')[1] for key in self.metrics['user_activity'].keys() 
                    if key.startswith('user_') and key != 'user_activity')
            )
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Получение текущих метрик"""
        current_time = time.time()
        period_duration = current_time - self.current_period['start_time']
        
        with self.metrics_lock:
            # Основные метрики
            basic_metrics = {
                'period_duration_minutes': round(period_duration / 60, 2),
                'total_requests': self.current_period['requests_count'],
                'total_errors': self.current_period['errors_count'],
                'slow_requests': self.current_period['slow_requests'],
                'error_rate': round(
                    (self.current_period['errors_count'] / max(self.current_period['requests_count'], 1)) * 100, 2
                ),
                'requests_per_minute': round(
                    self.current_period['requests_count'] / max(period_duration / 60, 1), 2
                )
            }
            
            # Средние времена отклика по endpoints
            response_times = {}
            for endpoint, times in self.metrics['response_times'].items():
                if times:
                    recent_times = [
                        t['execution_time'] for t in times 
                        if current_time - t['timestamp'] < 300  # Последние 5 минут
                    ]
                    if recent_times:
                        response_times[endpoint] = {
                            'avg_ms': round(sum(recent_times) / len(recent_times) * 1000, 2),
                            'min_ms': round(min(recent_times) * 1000, 2),
                            'max_ms': round(max(recent_times) * 1000, 2),
                            'count': len(recent_times)
                        }
            
            # Топ медленных endpoints
            slow_endpoints = sorted(
                [(endpoint, metrics['avg_ms']) for endpoint, metrics in response_times.items()],
                key=lambda x: x[1],
                reverse=True
            )[:10]
            
            # Метрики базы данных
            db_metrics = {}
            for query_type, queries in self.metrics['database_queries'].items():
                recent_queries = [
                    q for q in queries 
                    if current_time - q['timestamp'] < 300
                ]
                if recent_queries:
                    db_metrics[query_type] = {
                        'avg_time_ms': round(
                            sum(q['execution_time'] for q in recent_queries) / len(recent_queries) * 1000, 2
                        ),
                        'count': len(recent_queries),
                        'total_rows': sum(q['rows_affected'] for q in recent_queries)
                    }
            
            # Статистика кэша
            cache_metrics = dict(self.metrics['cache_stats'])
            if cache_metrics.get('cache_hit', 0) + cache_metrics.get('cache_miss', 0) > 0:
                cache_metrics['hit_rate'] = round(
                    cache_metrics.get('cache_hit', 0) / 
                    (cache_metrics.get('cache_hit', 0) + cache_metrics.get('cache_miss', 0)) * 100, 2
                )
            
            # Активность пользователей
            user_metrics = dict(self.metrics['user_activity'])
            
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'basic_metrics': basic_metrics,
                'response_times': response_times,
                'slow_endpoints': slow_endpoints,
                'database_metrics': db_metrics,
                'cache_metrics': cache_metrics,
                'user_metrics': user_metrics
            }
    
    def get_historical_data(self, hours: int = 1) -> Dict[str, List[Dict]]:
        """Получение исторических данных"""
        cutoff_time = time.time() - (hours * 3600)
        
        with self.metrics_lock:
            historical = {
                'requests': [],
                'errors': [],
                'response_times': []
            }
            
            # Группируем данные по минутам
            for endpoint, requests in self.metrics['requests'].items():
                for req in requests:
                    if req['timestamp'] > cutoff_time:
                        minute_bucket = int(req['timestamp'] // 60) * 60
                        historical['requests'].append({
                            'timestamp': minute_bucket,
                            'endpoint': endpoint,
                            'count': 1,
                            'status_code': req['status_code']
                        })
                        
                        if req['status_code'] >= 400:
                            historical['errors'].append({
                                'timestamp': minute_bucket,
                                'endpoint': endpoint,
                                'status_code': req['status_code']
                            })
                        
                        historical['response_times'].append({
                            'timestamp': minute_bucket,
                            'endpoint': endpoint,
                            'execution_time': req['execution_time']
                        })
            
            return historical
    
    def _cleanup_old_metrics(self):
        """Очистка старых метрик"""
        cutoff_time = time.time() - self.max_metrics_age
        
        with self.metrics_lock:
            # Очищаем времена отклика
            for endpoint in list(self.metrics['response_times'].keys()):
                self.metrics['response_times'][endpoint] = [
                    metric for metric in self.metrics['response_times'][endpoint]
                    if metric['timestamp'] > cutoff_time
                ]
                if not self.metrics['response_times'][endpoint]:
                    del self.metrics['response_times'][endpoint]
            
            # Очищаем запросы
            for endpoint in list(self.metrics['requests'].keys()):
                self.metrics['requests'][endpoint] = [
                    req for req in self.metrics['requests'][endpoint]
                    if req['timestamp'] > cutoff_time
                ]
                if not self.metrics['requests'][endpoint]:
                    del self.metrics['requests'][endpoint]
            
            # Очищаем запросы к БД
            for query_type in list(self.metrics['database_queries'].keys()):
                self.metrics['database_queries'][query_type] = [
                    query for query in self.metrics['database_queries'][query_type]
                    if query['timestamp'] > cutoff_time
                ]
                if not self.metrics['database_queries'][query_type]:
                    del self.metrics['database_queries'][query_type]
    
    def _schedule_cleanup(self):
        """Планирование периодической очистки"""
        def cleanup_worker():
            while True:
                time.sleep(300)  # Каждые 5 минут
                try:
                    self._cleanup_old_metrics()
                except Exception as e:
                    logger.error(f"Metrics cleanup error: {e}")
        
        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()
    
    def reset_current_period(self):
        """Сброс текущего периода метрик"""
        with self.metrics_lock:
            self.current_period = {
                'start_time': time.time(),
                'requests_count': 0,
                'errors_count': 0,
                'slow_requests': 0
            }

def monitor_performance(include_db: bool = True, include_cache: bool = True):
    """
    Декоратор для мониторинга производительности функций
    
    Args:
        include_db: Включать ли мониторинг БД операций
        include_cache: Включать ли мониторинг кэша
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            function_name = f.__name__
            
            try:
                result = f(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # Записываем метрики
                monitor = current_app.extensions.get('performance_monitor')
                if monitor:
                    if include_db and 'query' in function_name.lower():
                        monitor.record_database_query(function_name, execution_time)
                    
                    if execution_time > 0.1:  # Логируем функции >100ms
                        logger.debug(f"Function {function_name} took {execution_time*1000:.1f}ms")
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"Function {function_name} failed after {execution_time*1000:.1f}ms: {e}")
                raise
                
        return wrapper
    return decorator

def setup_performance_monitoring(app: Flask) -> PerformanceMonitor:
    """Настройка мониторинга производительности"""
    monitor = PerformanceMonitor(app)
    
    # Добавляем endpoints для мониторинга
    @app.route('/api/monitoring/metrics', methods=['GET'])
    def performance_metrics():
        """Текущие метрики производительности"""
        user_id = request.headers.get('X-Telegram-User-Id')
        
        # Проверяем права (администратор или самостоятельный мониторинг)
        if user_id != '373086959':
            return {'error': 'Access denied'}, 403
        
        try:
            metrics = monitor.get_current_metrics()
            return {
                'success': True,
                'metrics': metrics
            }
        except Exception as e:
            logger.error(f"Metrics error: {e}")
            return {'success': False, 'error': str(e)}, 500
    
    @app.route('/api/monitoring/historical', methods=['GET'])
    def historical_metrics():
        """Исторические метрики"""
        user_id = request.headers.get('X-Telegram-User-Id')
        
        if user_id != '373086959':
            return {'error': 'Access denied'}, 403
        
        try:
            hours = int(request.args.get('hours', 1))
            data = monitor.get_historical_data(hours)
            return {
                'success': True,
                'historical_data': data,
                'period_hours': hours
            }
        except Exception as e:
            logger.error(f"Historical metrics error: {e}")
            return {'success': False, 'error': str(e)}, 500
    
    @app.route('/api/monitoring/reset', methods=['POST'])
    def reset_metrics():
        """Сброс метрик (администратор)"""
        user_id = request.headers.get('X-Telegram-User-Id')
        
        if user_id != '373086959':
            return {'error': 'Access denied'}, 403
        
        try:
            monitor.reset_current_period()
            return {
                'success': True,
                'message': 'Metrics reset successfully'
            }
        except Exception as e:
            logger.error(f"Metrics reset error: {e}")
            return {'success': False, 'error': str(e)}, 500
    
    logger.info("✅ Performance monitoring configured")
    return monitor

logger.info("✅ Performance monitoring module initialized")