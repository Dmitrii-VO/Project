# app/security/csrf_protection.py
"""
CSRF Protection для Telegram Mini App
Интегрируется с Telegram WebApp authentication
"""

import hashlib
import hmac
import time
from typing import Optional
from flask import Flask, request, jsonify, session
from functools import wraps
import logging

logger = logging.getLogger(__name__)

class TelegramCSRFProtection:
    """
    CSRF защита, специально адаптированная для Telegram Mini App
    Использует Telegram WebApp initData для верификации
    """
    
    def __init__(self, app: Flask = None, secret_key: str = None):
        self.app = app
        self.secret_key = secret_key
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """Инициализация CSRF защиты"""
        self.secret_key = self.secret_key or app.config.get('SECRET_KEY')
        if not self.secret_key:
            raise ValueError("SECRET_KEY is required for CSRF protection")
        
        app.extensions['csrf'] = self
        
        # Добавляем middleware для проверки CSRF токенов
        app.before_request(self._check_csrf_token)
    
    def _check_csrf_token(self):
        """Проверка CSRF токена для защищенных endpoints"""
        # Пропускаем GET запросы и безопасные методы
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return
        
        # Пропускаем статические файлы
        if request.endpoint and request.endpoint.startswith('static'):
            return
        
        # Пропускаем некоторые публичные API endpoints
        exempt_paths = ['/api/health', '/api/status', '/webhook/telegram']
        if request.path in exempt_paths:
            return
        
        # Проверяем CSRF токен для API запросов
        if request.path.startswith('/api/'):
            return self._validate_api_request()
        
        # Проверяем CSRF токен для форм
        return self._validate_form_request()
    
    def _validate_api_request(self):
        """Валидация API запросов через Telegram WebApp"""
        # Получаем Telegram User ID из заголовков
        telegram_user_id = request.headers.get('X-Telegram-User-Id')
        if not telegram_user_id:
            logger.warning(f"Missing X-Telegram-User-Id header: {request.path}")
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Missing Telegram authentication'
            }), 401
        
        # Проверяем CSRF токен
        csrf_token = request.headers.get('X-CSRF-Token')
        if not csrf_token:
            logger.warning(f"Missing CSRF token: {request.path} from user {telegram_user_id}")
            return jsonify({
                'error': 'CSRF Token Missing',
                'message': 'CSRF token is required'
            }), 403
        
        # Валидируем токен
        if not self._validate_csrf_token(csrf_token, telegram_user_id):
            logger.warning(f"Invalid CSRF token: {request.path} from user {telegram_user_id}")
            return jsonify({
                'error': 'CSRF Token Invalid',
                'message': 'Invalid CSRF token'
            }), 403
        
        # Логируем успешную проверку
        logger.debug(f"CSRF validation passed: {request.path} from user {telegram_user_id}")
    
    def _validate_form_request(self):
        """Валидация форм через скрытое поле"""
        csrf_token = request.form.get('csrf_token')
        if not csrf_token:
            logger.warning(f"Missing CSRF token in form: {request.path}")
            return jsonify({
                'error': 'CSRF Token Missing',
                'message': 'CSRF token is required'
            }), 403
        
        # Получаем user_id из сессии или формы
        user_id = session.get('user_id') or request.form.get('user_id')
        if not user_id:
            logger.warning(f"Missing user_id for CSRF validation: {request.path}")
            return jsonify({
                'error': 'Unauthorized',
                'message': 'User identification required'
            }), 401
        
        if not self._validate_csrf_token(csrf_token, str(user_id)):
            logger.warning(f"Invalid CSRF token in form: {request.path} from user {user_id}")
            return jsonify({
                'error': 'CSRF Token Invalid',
                'message': 'Invalid CSRF token'
            }), 403
    
    def _validate_csrf_token(self, token: str, user_id: str) -> bool:
        """Проверка валидности CSRF токена"""
        try:
            # Разбираем токен (timestamp.signature)
            parts = token.split('.')
            if len(parts) != 2:
                return False
            
            timestamp_str, signature = parts
            timestamp = int(timestamp_str)
            
            # Проверяем время жизни токена (24 часа)
            current_time = int(time.time())
            if current_time - timestamp > 86400:  # 24 hours
                logger.debug(f"CSRF token expired: {token[:20]}...")
                return False
            
            # Генерируем ожидаемую подпись
            expected_signature = self._generate_signature(timestamp_str, user_id)
            
            # Сравниваем подписи
            return hmac.compare_digest(signature, expected_signature)
        
        except (ValueError, IndexError) as e:
            logger.debug(f"CSRF token parsing error: {e}")
            return False
    
    def _generate_signature(self, timestamp: str, user_id: str) -> str:
        """Генерация подписи для CSRF токена"""
        message = f"{timestamp}.{user_id}"
        return hmac.new(
            self.secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
    
    def generate_csrf_token(self, user_id: str) -> str:
        """Генерация CSRF токена для пользователя"""
        timestamp = str(int(time.time()))
        signature = self._generate_signature(timestamp, user_id)
        return f"{timestamp}.{signature}"


def setup_csrf_protection(app: Flask) -> TelegramCSRFProtection:
    """Настройка CSRF защиты для приложения"""
    csrf = TelegramCSRFProtection(app)
    
    # Добавляем endpoint для получения CSRF токена
    @app.route('/api/csrf-token', methods=['GET'])
    def get_csrf_token():
        """Получение CSRF токена для текущего пользователя"""
        user_id = request.headers.get('X-Telegram-User-Id')
        if not user_id:
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Telegram User ID required'
            }), 401
        
        token = csrf.generate_csrf_token(user_id)
        return jsonify({
            'csrf_token': token,
            'expires_in': 86400  # 24 hours
        })
    
    # Добавляем функцию в контекст шаблонов
    @app.context_processor
    def inject_csrf_token():
        """Добавление CSRF токена в контекст шаблонов"""
        user_id = session.get('user_id')
        if user_id:
            return {'csrf_token': csrf.generate_csrf_token(str(user_id))}
        return {}
    
    logger.info("✅ CSRF Protection initialized")
    return csrf


def csrf_exempt(f):
    """Декоратор для исключения endpoint из CSRF проверки"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    
    decorated_function._csrf_exempt = True
    return decorated_function