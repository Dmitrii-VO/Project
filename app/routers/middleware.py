# app/routers/middleware.py
"""
Модуль middleware для Telegram Mini App

Содержит всю логику промежуточного ПО для обработки запросов,
безопасности, аутентификации и мониторинга производительности.
"""

import time
import json
from typing import Optional, Dict, Any, Tuple
from app.services.auth_service import AuthService
from functools import wraps
from flask import (
    request, jsonify, current_app, g, session,
    Response
)

# === КОНСТАНТЫ ===
MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10MB
RATE_LIMIT_REQUESTS = 100  # запросов
RATE_LIMIT_WINDOW = 3600  # в секунду (1 час)
ALLOWED_CONTENT_TYPES = ['application/json', 'multipart/form-data']
SUSPICIOUS_PATTERNS = [
    'union select', 'drop table', 'insert into',
    '../', '..\\', '<script', 'javascript:',
    'eval(', 'exec(', 'system('
]

# Глобальные кэши
rate_limit_cache = {}
security_events = []


class SecurityLogger:
    """Класс для логирования событий безопасности"""

    @staticmethod
    def log_security_event(event_type: str, details: Dict[str, Any]):
        """Логирование события безопасности"""
        event = {
            'timestamp': time.time(),
            'type': event_type,
            'ip': request.remote_addr,
            'user_agent': request.headers.get('User-Agent'),
            'path': request.path,
            'method': request.method,
            'details': details
        }

        security_events.append(event)

        # Ограничиваем размер лога (храним последние 1000 событий)
        if len(security_events) > 1000:
            security_events.pop(0)

        # Логируем в файл
        current_app.logger.warning(f"SECURITY EVENT [{event_type}]: {json.dumps(event)}")


class SecurityValidator:
    """Класс для валидации безопасности запросов"""

    @staticmethod
    def validate_request_size() -> Optional[Tuple[Dict, int]]:
        """Проверка размера запроса"""
        if request.content_length and request.content_length > MAX_REQUEST_SIZE:
            SecurityLogger.log_security_event('LARGE_REQUEST', {
                'size': request.content_length,
                'max_allowed': MAX_REQUEST_SIZE
            })
            return {'error': 'Request too large', 'max_size': MAX_REQUEST_SIZE}, 413
        return None

    @staticmethod
    def validate_content_type() -> Optional[Tuple[Dict, int]]:
        """Проверка Content-Type для POST запросов"""
        if request.method == 'POST' and request.path.startswith('/api/'):
            content_type = request.headers.get('Content-Type', '')
            if not any(ct in content_type for ct in ALLOWED_CONTENT_TYPES):
                SecurityLogger.log_security_event('INVALID_CONTENT_TYPE', {
                    'content_type': content_type,
                    'allowed': ALLOWED_CONTENT_TYPES
                })
                return {'error': 'Invalid Content-Type', 'allowed': ALLOWED_CONTENT_TYPES}, 400
        return None

    @staticmethod
    def validate_rate_limit() -> Optional[Tuple[Dict, int]]:
        """Простая проверка rate limiting"""
        client_ip = request.remote_addr
        current_time = time.time()

        # Очистка старых записей
        cutoff_time = current_time - RATE_LIMIT_WINDOW
        rate_limit_cache[client_ip] = [
            timestamp for timestamp in rate_limit_cache.get(client_ip, [])
            if timestamp > cutoff_time
        ]

        # Проверка лимита
        request_count = len(rate_limit_cache.get(client_ip, []))
        if request_count >= RATE_LIMIT_REQUESTS:
            SecurityLogger.log_security_event('RATE_LIMIT_EXCEEDED', {
                'requests_count': request_count,
                'limit': RATE_LIMIT_REQUESTS,
                'window': RATE_LIMIT_WINDOW
            })
            return {'error': 'Rate limit exceeded', 'retry_after': RATE_LIMIT_WINDOW}, 429

        # Добавление текущего запроса
        if client_ip not in rate_limit_cache:
            rate_limit_cache[client_ip] = []
        rate_limit_cache[client_ip].append(current_time)

        return None

    @staticmethod
    def check_suspicious_content() -> Optional[Tuple[Dict, int]]:
        """Проверка на подозрительный контент"""
        try:
            # Проверяем URL
            for pattern in SUSPICIOUS_PATTERNS:
                if pattern.lower() in request.path.lower():
                    SecurityLogger.log_security_event('SUSPICIOUS_URL', {
                        'pattern': pattern,
                        'url': request.path
                    })
                    return {'error': 'Suspicious request detected'}, 400

            # Проверяем параметры запроса
            for key, value in request.args.items():
                if isinstance(value, str):
                    for pattern in SUSPICIOUS_PATTERNS:
                        if pattern.lower() in value.lower():
                            SecurityLogger.log_security_event('SUSPICIOUS_PARAM', {
                                'pattern': pattern,
                                'param': key,
                                'value': value[:100]  # Ограничиваем длину для логов
                            })
                            return {'error': 'Suspicious request detected'}, 400

            # Проверяем JSON данные
            if request.is_json:
                data = request.get_json(silent=True)
                if data:
                    data_str = json.dumps(data).lower()
                    for pattern in SUSPICIOUS_PATTERNS:
                        if pattern in data_str:
                            SecurityLogger.log_security_event('SUSPICIOUS_JSON', {
                                'pattern': pattern
                            })
                            return {'error': 'Suspicious request detected'}, 400

        except Exception as e:
            current_app.logger.error(f"Error checking suspicious content: {e}")

        return None


class PerformanceMonitor:
    """Класс для мониторинга производительности"""

    @staticmethod
    def start_timing():
        """Начало замера времени выполнения"""
        g.request_start_time = time.time()
        g.request_id = f"{int(time.time() * 1000)}-{id(request)}"

    @staticmethod
    def log_slow_requests(response: Response) -> Response:
        """Логирование медленных запросов"""
        if hasattr(g, 'request_start_time'):
            duration = time.time() - g.request_start_time

            # Логируем медленные запросы (>1 секунды)
            if duration > 1.0:
                current_app.logger.warning(
                    f"Slow request [{g.request_id}]: {request.method} {request.path} "
                    f"took {duration:.2f}s from {request.remote_addr}"
                )

            # Добавляем заголовки с метриками производительности
            response.headers['X-Response-Time'] = f"{duration:.3f}s"
            response.headers['X-Request-ID'] = g.request_id

            # Логируем все запросы в debug режиме
            if current_app.debug:
                current_app.logger.debug(
                    f"Request [{g.request_id}]: {request.method} {request.path} "
                    f"completed in {duration:.3f}s"
                )

        return response


# === MIDDLEWARE ФУНКЦИИ ===

def security_middleware():
    """
    Основной middleware для проверки безопасности

    Выполняет следующие проверки:
    - Размер запроса
    - Content-Type
    - Rate limiting
    - Подозрительный контент
    - Стартует мониторинг производительности
    """

    # Начинаем замер производительности
    PerformanceMonitor.start_timing()

    # Валидация размера запроса
    error_response = SecurityValidator.validate_request_size()
    if error_response:
        return jsonify(error_response[0]), error_response[1]

    # Валидация Content-Type
    error_response = SecurityValidator.validate_content_type()
    if error_response:
        return jsonify(error_response[0]), error_response[1]

    # Rate limiting
    error_response = SecurityValidator.validate_rate_limit()
    if error_response:
        return jsonify(error_response[0]), error_response[1]

    # Проверка на подозрительный контент
    error_response = SecurityValidator.check_suspicious_content()
    if error_response:
        return jsonify(error_response[0]), error_response[1]

    # Логирование доступа к API
    if request.path.startswith('/api/'):
        current_app.logger.info(
            f"API Access [{g.request_id}]: {request.method} {request.path} "
            f"from {request.remote_addr} "
            f"User-Agent: {request.headers.get('User-Agent', 'Unknown')[:100]}"
        )


def telegram_auth_middleware():
    """
    Middleware для аутентификации Telegram пользователей

    Обрабатывает аутентификацию только для защищенных эндпоинтов
    и автоматически создает пользователей в БД при необходимости.
    """

    # Определяем защищенные пути
    protected_paths = [
        '/api/channels/',
        '/api/offers/',
        '/api/payments/',
        '/channels-enhanced',
        '/offers',
        '/payments'
    ]

    # Публичные пути, не требующие аутентификации
    public_paths = [
        '/',
        '/test',
        '/health',
        '/api/channels',  # GET список каналов
    ]

    # Проверяем, нужна ли аутентификация
    needs_auth = False
    for protected_path in protected_paths:
        if request.path.startswith(protected_path):
            needs_auth = True
            break

    # Пропускаем публичные пути
    for public_path in public_paths:
        if request.path == public_path or request.path.startswith(public_path):
            needs_auth = False
            break

    if not needs_auth:
        return

    try:
        telegram_id = AuthService.get_current_user_id()

        if not telegram_id:
            current_app.logger.warning(
                f"Unauthorized access attempt to {request.path} from {request.remote_addr}"
            )
            SecurityLogger.log_security_event('UNAUTHORIZED_ACCESS', {
                'path': request.path,
                'method': request.method
            })

            # Возвращаем ошибку аутентификации
            if request.path.startswith('/api/'):
                return jsonify({
                    'error': 'Authentication required',
                    'message': 'Telegram user ID not found'
                }), 401
            else:
                # Для веб-страниц перенаправляем на страницу авторизации
                from flask import redirect, url_for
                return redirect(url_for('main.index'))

        # Убеждаемся что пользователь существует в БД
        user_db_id = AuthService.ensure_user_exists(telegram_id)

        if user_db_id:
            # Сохраняем информацию о пользователе в g для использования в маршрутах
            g.current_user_id = user_db_id
            g.telegram_id = telegram_id

            current_app.logger.debug(
                f"Telegram user {telegram_id} authenticated for {request.path}"
            )
        else:
            current_app.logger.error(
                f"Failed to ensure user exists for Telegram ID: {telegram_id}"
            )
            SecurityLogger.log_security_event('USER_CREATION_FAILED', {
                'telegram_id': telegram_id
            })

            if request.path.startswith('/api/'):
                return jsonify({
                    'error': 'User registration failed'
                }), 500

    except Exception as e:
        current_app.logger.error(f"Telegram auth middleware error: {e}")
        SecurityLogger.log_security_event('AUTH_MIDDLEWARE_ERROR', {
            'error': str(e)
        })

        if request.path.startswith('/api/'):
            return jsonify({
                'error': 'Authentication error'
            }), 500


def performance_middleware():
    """
    Middleware для мониторинга производительности

    Настраивает after_request обработчики для логирования
    времени выполнения запросов.
    """

    # Регистрируем after_request обработчик для текущего запроса
    @current_app.after_request
    def log_request_performance(response):
        """Логирование производительности после выполнения запроса"""
        return PerformanceMonitor.log_slow_requests(response)


def cors_middleware():
    """
    Middleware для обработки CORS (Cross-Origin Resource Sharing)

    Настраивает заголовки для безопасной работы с фронтендом
    """

    @current_app.after_request
    def add_cors_headers(response):
        """Добавление CORS заголовков"""

        # Разрешенные домены (в продакшене ограничить)
        allowed_origins = current_app.config.get('ALLOWED_ORIGINS', [
            'https://web.telegram.org',
            'https://k.web.telegram.org'
        ])

        origin = request.headers.get('Origin')
        if origin in allowed_origins or current_app.debug:
            response.headers['Access-Control-Allow-Origin'] = origin or '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = (
                'Content-Type, Authorization, X-Requested-With, '
                'X-Telegram-User-Id, X-Telegram-Username, '
                'X-Telegram-First-Name, X-Telegram-Last-Name'
            )
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            response.headers['Access-Control-Max-Age'] = '86400'  # 24 часа

        # Безопасность заголовки
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'

        return response


# === ДЕКОРАТОРЫ ===

def require_telegram_auth(f):
    """
    Декоратор для принудительной проверки Telegram аутентификации

    Использование:
    @require_telegram_auth
    def my_protected_route():
        return "Только для аутентифицированных пользователей"
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        telegram_id = AuthService.get_current_user_id()

        if not telegram_id:
            if request.path.startswith('/api/'):
                return jsonify({
                    'error': 'Authentication required',
                    'message': 'Telegram user ID not found'
                }), 401
            else:
                from flask import redirect, url_for
                return redirect(url_for('main.index'))

        # Проверяем существование пользователя в БД
        user_db_id = AuthService.ensure_user_exists(telegram_id)
        if not user_db_id:
            return jsonify({
                'error': 'User registration failed'
            }), 500

        g.current_user_id = user_db_id
        g.telegram_id = telegram_id

        return f(*args, **kwargs)

    return decorated_function


def cache_response(timeout=300):
    """
    Декоратор для кэширования ответов

    Args:
        timeout: Время жизни кэша в секундах (по умолчанию 5 минут)

    Использование:
    @cache_response(timeout=600)
    def my_cached_route():
        return "Этот ответ будет закэширован на 10 минут"
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Создаем ключ кэша на основе пути и параметров
            cache_key = f"{request.path}:{request.query_string.decode()}"

            # Проверяем кэш
            if hasattr(current_app, '_route_cache'):
                cached_data = current_app._route_cache.get(cache_key)
                if cached_data and time.time() - cached_data['timestamp'] < timeout:
                    current_app.logger.debug(f"Cache hit for {cache_key}")
                    return cached_data['response']

            # Выполняем функцию и кэшируем результат
            response = f(*args, **kwargs)

            # Инициализируем кэш если нужно
            if not hasattr(current_app, '_route_cache'):
                current_app._route_cache = {}

            # Сохраняем в кэш
            current_app._route_cache[cache_key] = {
                'response': response,
                'timestamp': time.time()
            }

            # Очищаем старые записи кэша (простая реализация)
            current_time = time.time()
            expired_keys = [
                key for key, data in current_app._route_cache.items()
                if current_time - data['timestamp'] > timeout * 2
            ]
            for key in expired_keys:
                del current_app._route_cache[key]

            current_app.logger.debug(f"Cached response for {cache_key}")
            return response

        return decorated_function

    return decorator


def rate_limit_decorator(max_requests=10, window=60):
    """
    Декоратор для индивидуального rate limiting маршрутов

    Args:
        max_requests: Максимальное количество запросов
        window: Временное окно в секундах

    Использование:
    @rate_limit_decorator(max_requests=5, window=60)
    def my_limited_route():
        return "Максимум 5 запросов в минуту"
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            client_ip = request.remote_addr
            route_key = f"{request.endpoint}:{client_ip}"
            current_time = time.time()

            # Инициализируем кэш для маршрута
            if not hasattr(current_app, '_route_rate_limits'):
                current_app._route_rate_limits = {}

            # Очищаем старые записи
            cutoff_time = current_time - window
            if route_key in current_app._route_rate_limits:
                current_app._route_rate_limits[route_key] = [
                    timestamp for timestamp in current_app._route_rate_limits[route_key]
                    if timestamp > cutoff_time
                ]
            else:
                current_app._route_rate_limits[route_key] = []

            # Проверяем лимит
            if len(current_app._route_rate_limits[route_key]) >= max_requests:
                SecurityLogger.log_security_event('ROUTE_RATE_LIMIT_EXCEEDED', {
                    'route': request.endpoint,
                    'requests_count': len(current_app._route_rate_limits[route_key]),
                    'limit': max_requests,
                    'window': window
                })

                return jsonify({
                    'error': 'Rate limit exceeded for this endpoint',
                    'retry_after': window
                }), 429

            # Добавляем текущий запрос
            current_app._route_rate_limits[route_key].append(current_time)

            return f(*args, **kwargs)

        return decorated_function

    return decorator


# === ФУНКЦИИ ИНИЦИАЛИЗАЦИИ ===

def init_middleware(app):
    """
    Инициализация всех middleware

    Args:
        app: Экземпляр Flask приложения
    """

    # Регистрируем before_request middleware
    app.before_request(security_middleware)
    app.before_request(telegram_auth_middleware)
    app.before_request(performance_middleware)
    app.before_request(cors_middleware)

    app.logger.info("✅ Middleware инициализированы")


def get_security_stats():
    """
    Получение статистики безопасности

    Returns:
        Dict с информацией о событиях безопасности
    """

    current_time = time.time()
    hour_ago = current_time - 3600

    recent_events = [
        event for event in security_events
        if event['timestamp'] > hour_ago
    ]

    stats = {
        'total_events': len(security_events),
        'recent_events': len(recent_events),
        'rate_limit_cache_size': len(rate_limit_cache),
        'event_types': {}
    }

    # Группируем события по типам
    for event in recent_events:
        event_type = event['type']
        if event_type not in stats['event_types']:
            stats['event_types'][event_type] = 0
        stats['event_types'][event_type] += 1

    return stats


# Экспортируем основные компоненты
__all__ = [
    'security_middleware',
    'telegram_auth_middleware',
    'performance_middleware',
    'cors_middleware',
    'require_telegram_auth',
    'cache_response',
    'rate_limit_decorator',
    'init_middleware',
    'get_security_stats',
    'SecurityLogger',
    'PerformanceMonitor'
]