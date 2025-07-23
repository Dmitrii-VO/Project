# app/security/security_headers.py
"""
Модуль безопасных HTTP заголовков для Telegram Mini App
Защита от XSS, clickjacking, MIME-sniffing и других атак
"""

from flask import Flask, request, g
from functools import wraps
import logging

logger = logging.getLogger(__name__)

class SecurityHeaders:
    """
    Класс для управления заголовками безопасности
    """
    
    def __init__(self, app: Flask = None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """Инициализация модуля заголовков безопасности"""
        app.extensions['security_headers'] = self
        
        # Добавляем middleware для заголовков
        app.after_request(self._add_security_headers)
        
        logger.info("✅ Security Headers initialized")
    
    def _add_security_headers(self, response):
        """Добавление заголовков безопасности к ответу"""
        
        # Базовые заголовки безопасности
        response.headers.update({
            # Предотвращение MIME-sniffing
            'X-Content-Type-Options': 'nosniff',
            
            # Защита от clickjacking
            'X-Frame-Options': 'SAMEORIGIN',
            
            # XSS защита (устаревшая, но для совместимости)
            'X-XSS-Protection': '1; mode=block',
            
            # Строгая безопасность транспорта (HSTS)
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains; preload',
            
            # Контроль рефереров
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            
            # Permissions Policy (ограничение API браузера)
            'Permissions-Policy': 'camera=(), microphone=(), geolocation=(self), payment=(self)',
            
            # Удаление информации о сервере
            'Server': 'TelegramMiniApp/1.0'
        })
        
        # Content Security Policy для разных типов контента
        if response.content_type and 'text/html' in response.content_type:
            response.headers['Content-Security-Policy'] = self._get_html_csp()
        elif response.content_type and 'application/json' in response.content_type:
            response.headers['Content-Security-Policy'] = self._get_api_csp()
        
        # CORS заголовки для Telegram WebApp
        if request.path.startswith('/api/'):
            self._add_cors_headers(response)
        
        # Дополнительные заголовки для статических файлов
        if request.endpoint and request.endpoint.startswith('static'):
            self._add_static_headers(response)
        
        return response
    
    def _get_html_csp(self) -> str:
        """Content Security Policy для HTML страниц"""
        # Разрешаем Telegram WebApp домены и собственные ресурсы
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' https://telegram.org https://*.telegram.org",
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
            "font-src 'self' https://fonts.gstatic.com",
            "img-src 'self' data: https: blob:",
            "connect-src 'self' https://api.telegram.org wss: ws:",
            "frame-ancestors 'self' https://web.telegram.org https://*.telegram.org",
            "form-action 'self'",
            "base-uri 'self'",
            "object-src 'none'",
            "upgrade-insecure-requests"
        ]
        return '; '.join(csp_directives)
    
    def _get_api_csp(self) -> str:
        """Content Security Policy для API endpoints"""
        csp_directives = [
            "default-src 'none'",
            "script-src 'none'",
            "style-src 'none'",
            "img-src 'none'",
            "connect-src 'self'",
            "frame-ancestors 'none'",
            "form-action 'none'",
            "base-uri 'none'",
            "object-src 'none'"
        ]
        return '; '.join(csp_directives)
    
    def _add_cors_headers(self, response):
        """Добавление CORS заголовков для API"""
        # Разрешаем запросы только от Telegram WebApp
        allowed_origins = [
            'https://web.telegram.org',
            'https://k.web.telegram.org',
            'https://z.web.telegram.org',
            'https://a.web.telegram.org'
        ]
        
        origin = request.headers.get('Origin')
        if origin in allowed_origins:
            response.headers['Access-Control-Allow-Origin'] = origin
        
        response.headers.update({
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, X-Telegram-User-Id, X-CSRF-Token, Authorization',
            'Access-Control-Allow-Credentials': 'true',
            'Access-Control-Max-Age': '86400'  # 24 hours
        })
    
    def _add_static_headers(self, response):
        """Дополнительные заголовки для статических файлов"""
        # Кэширование статических ресурсов
        if request.path.endswith(('.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg')):
            response.headers.update({
                'Cache-Control': 'public, max-age=31536000, immutable',  # 1 год
                'ETag': f'"{hash(request.path)}"',
                'Vary': 'Accept-Encoding'
            })
        
        # Дополнительная защита для JavaScript файлов
        if request.path.endswith('.js'):
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['Content-Type'] = 'application/javascript; charset=utf-8'


def setup_security_headers(app: Flask) -> SecurityHeaders:
    """Настройка заголовков безопасности для приложения"""
    security_headers = SecurityHeaders(app)
    
    # Добавляем обработчик для OPTIONS запросов (CORS preflight)
    @app.before_request
    def handle_preflight():
        if request.method == 'OPTIONS':
            response = app.make_default_options_response()
            
            # Добавляем CORS заголовки для preflight запросов
            allowed_origins = [
                'https://web.telegram.org',
                'https://k.web.telegram.org', 
                'https://z.web.telegram.org',
                'https://a.web.telegram.org'
            ]
            
            origin = request.headers.get('Origin')
            if origin in allowed_origins:
                response.headers['Access-Control-Allow-Origin'] = origin
                response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
                response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-Telegram-User-Id, X-CSRF-Token, Authorization'
                response.headers['Access-Control-Allow-Credentials'] = 'true'
                response.headers['Access-Control-Max-Age'] = '86400'
            
            return response
    
    # Middleware для удаления чувствительных заголовков сервера
    @app.after_request
    def remove_server_headers(response):
        # Удаляем заголовки, которые могут раскрыть информацию о сервере
        headers_to_remove = ['Server', 'X-Powered-By', 'X-AspNet-Version', 'X-AspNetMvc-Version']
        for header in headers_to_remove:
            response.headers.pop(header, None)
        
        return response
    
    logger.info("✅ Security Headers configured")
    return security_headers


def secure_headers(additional_headers: dict = None):
    """
    Декоратор для добавления дополнительных заголовков безопасности к endpoint
    
    Args:
        additional_headers: Словарь дополнительных заголовков
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            response = f(*args, **kwargs)
            
            # Если response не является Response объектом, создаем его
            if not hasattr(response, 'headers'):
                from flask import make_response
                response = make_response(response)
            
            # Добавляем дополнительные заголовки
            if additional_headers:
                response.headers.update(additional_headers)
            
            return response
        return decorated_function
    return decorator


def api_security_headers():
    """Декоратор для API endpoints с усиленной безопасностью"""
    additional_headers = {
        'X-API-Version': '1.0',
        'X-Rate-Limit-Policy': 'strict',
        'Cache-Control': 'no-store, no-cache, must-revalidate, private',
        'Pragma': 'no-cache',
        'Expires': '0'
    }
    return secure_headers(additional_headers)


def admin_security_headers():
    """Декоратор для административных endpoints"""
    additional_headers = {
        'X-Admin-Protection': 'enabled',
        'X-Frame-Options': 'DENY',  # Более строгая защита от фреймов
        'Cache-Control': 'no-store, no-cache, must-revalidate, private',
        'Content-Security-Policy': "default-src 'none'; script-src 'none'"
    }
    return secure_headers(additional_headers)


class SecurityHeadersChecker:
    """Класс для проверки наличия и корректности заголовков безопасности"""
    
    REQUIRED_HEADERS = [
        'X-Content-Type-Options',
        'X-Frame-Options', 
        'Strict-Transport-Security',
        'Content-Security-Policy',
        'Referrer-Policy'
    ]
    
    @staticmethod
    def check_response_headers(response) -> dict:
        """Проверка наличия заголовков безопасности в ответе"""
        missing_headers = []
        present_headers = []
        
        for header in SecurityHeadersChecker.REQUIRED_HEADERS:
            if header in response.headers:
                present_headers.append(header)
            else:
                missing_headers.append(header)
        
        return {
            'security_score': len(present_headers) / len(SecurityHeadersChecker.REQUIRED_HEADERS),
            'missing_headers': missing_headers,
            'present_headers': present_headers,
            'recommendations': SecurityHeadersChecker._get_recommendations(missing_headers)
        }
    
    @staticmethod
    def _get_recommendations(missing_headers: list) -> list:
        """Получение рекомендаций по отсутствующим заголовкам"""
        recommendations = []
        
        for header in missing_headers:
            if header == 'X-Content-Type-Options':
                recommendations.append('Add X-Content-Type-Options: nosniff to prevent MIME sniffing')
            elif header == 'X-Frame-Options':
                recommendations.append('Add X-Frame-Options to prevent clickjacking attacks')
            elif header == 'Strict-Transport-Security':
                recommendations.append('Add HSTS header for secure HTTPS connections')
            elif header == 'Content-Security-Policy':
                recommendations.append('Add CSP header to prevent XSS attacks')
            elif header == 'Referrer-Policy':
                recommendations.append('Add Referrer-Policy to control referrer information')
        
        return recommendations


logger.info("✅ Security Headers module initialized")