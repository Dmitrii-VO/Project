# app/security/input_validation.py
"""
Валидация входных данных для Telegram Mini App
Защита от XSS, SQL injection и других атак
"""

import re
import html
import json
from typing import Any, Dict, List, Optional, Union
from flask import request, jsonify
from functools import wraps
import logging

logger = logging.getLogger(__name__)

class InputValidator:
    """
    Класс для валидации и санитизации входных данных
    """
    
    # Паттерны для валидации
    PATTERNS = {
        'telegram_id': r'^\d{1,15}$',
        'username': r'^[a-zA-Z0-9_]{1,32}$',
        'channel_username': r'^@?[a-zA-Z0-9_]{5,32}$',
        'email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
        'phone': r'^\+?[1-9]\d{1,14}$',
        'url': r'^https?://[^\s<>"]+$',
        'price': r'^\d+(\.\d{1,2})?$',
        'text': r'^[\w\s\-.,!?(){}[\]"\'№@#$%^&*+=:;|\\/<>~`]{1,1000}$',
        'title': r'^[\w\s\-.,!?(){}[\]"\'№]{1,200}$',
        'description': r'^[\w\s\-.,!?(){}[\]"\'№@#$%^&*+=:;|\\/<>~`\n]{1,2000}$'
    }
    
    # XSS опасные теги и атрибуты
    DANGEROUS_TAGS = [
        'script', 'iframe', 'object', 'embed', 'form', 'input', 'textarea',
        'select', 'button', 'meta', 'link', 'style', 'base', 'frame', 'frameset'
    ]
    
    DANGEROUS_ATTRIBUTES = [
        'onclick', 'onload', 'onerror', 'onmouseover', 'onfocus', 'onblur',
        'onchange', 'onsubmit', 'onreset', 'onselect', 'onunload', 'onabort',
        'onkeydown', 'onkeypress', 'onkeyup', 'onmousedown', 'onmouseup',
        'onmousemove', 'onmouseout', 'javascript:', 'vbscript:', 'data:'
    ]
    
    def __init__(self):
        self.max_length = {
            'title': 200,
            'description': 2000,
            'comment': 500,
            'message': 1000,
            'username': 32,
            'channel_name': 100
        }
    
    def validate_pattern(self, value: str, pattern_name: str) -> bool:
        """Валидация по регулярному выражению"""
        if pattern_name not in self.PATTERNS:
            logger.warning(f"Unknown validation pattern: {pattern_name}")
            return False
        
        pattern = self.PATTERNS[pattern_name]
        return bool(re.match(pattern, str(value)))
    
    def sanitize_html(self, text: str) -> str:
        """Санитизация HTML для защиты от XSS"""
        if not isinstance(text, str):
            return str(text)
        
        # Экранирование HTML символов
        sanitized = html.escape(text)
        
        # Удаление опасных тегов и атрибутов
        for tag in self.DANGEROUS_TAGS:
            sanitized = re.sub(f'<{tag}[^>]*>', '', sanitized, flags=re.IGNORECASE)
            sanitized = re.sub(f'</{tag}>', '', sanitized, flags=re.IGNORECASE)
        
        for attr in self.DANGEROUS_ATTRIBUTES:
            sanitized = re.sub(f'{attr}\\s*=\\s*["\'][^"\']*["\']', '', sanitized, flags=re.IGNORECASE)
        
        return sanitized.strip()
    
    def validate_length(self, value: str, field_name: str) -> bool:
        """Проверка длины поля"""
        if field_name not in self.max_length:
            return len(value) <= 1000  # Дефолтный лимит
        
        return len(value) <= self.max_length[field_name]
    
    def validate_telegram_id(self, telegram_id: Union[str, int]) -> bool:
        """Валидация Telegram ID"""
        try:
            telegram_id = str(telegram_id)
            return self.validate_pattern(telegram_id, 'telegram_id')
        except:
            return False
    
    def validate_price(self, price: Union[str, int, float]) -> bool:
        """Валидация цены"""
        try:
            price_float = float(price)
            return 0 <= price_float <= 1000000  # Максимум 1 млн
        except:
            return False
    
    def validate_channel_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Валидация данных канала"""
        errors = {}
        
        # Проверяем обязательные поля
        required_fields = ['title', 'username', 'owner_id']
        for field in required_fields:
            if field not in data or not data[field]:
                errors[field] = f'Field {field} is required'
        
        # Валидация username канала
        if 'username' in data:
            if not self.validate_pattern(data['username'], 'channel_username'):
                errors['username'] = 'Invalid channel username format'
        
        # Валидация owner_id
        if 'owner_id' in data:
            if not self.validate_telegram_id(data['owner_id']):
                errors['owner_id'] = 'Invalid Telegram ID format'
        
        # Валидация названия
        if 'title' in data:
            if not self.validate_length(data['title'], 'channel_name'):
                errors['title'] = 'Channel title is too long'
            data['title'] = self.sanitize_html(data['title'])
        
        # Валидация описания
        if 'description' in data:
            if not self.validate_length(data['description'], 'description'):
                errors['description'] = 'Description is too long'
            data['description'] = self.sanitize_html(data['description'])
        
        # Валидация цены
        if 'price_per_post' in data:
            if not self.validate_price(data['price_per_post']):
                errors['price_per_post'] = 'Invalid price format'
        
        return {'valid': len(errors) == 0, 'errors': errors, 'data': data}
    
    def validate_offer_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Валидация данных оффера"""
        errors = {}
        
        # Проверяем обязательные поля
        required_fields = ['title', 'description', 'budget_total', 'creator_id']
        for field in required_fields:
            if field not in data or not data[field]:
                errors[field] = f'Field {field} is required'
        
        # Валидация creator_id
        if 'creator_id' in data:
            if not self.validate_telegram_id(data['creator_id']):
                errors['creator_id'] = 'Invalid creator Telegram ID'
        
        # Валидация заголовка
        if 'title' in data:
            if not self.validate_length(data['title'], 'title'):
                errors['title'] = 'Title is too long'
            data['title'] = self.sanitize_html(data['title'])
        
        # Валидация описания
        if 'description' in data:
            if not self.validate_length(data['description'], 'description'):
                errors['description'] = 'Description is too long'
            data['description'] = self.sanitize_html(data['description'])
        
        # Валидация бюджета
        if 'budget_total' in data:
            if not self.validate_price(data['budget_total']):
                errors['budget_total'] = 'Invalid budget amount'
        
        # Валидация категории
        valid_categories = ['tech', 'business', 'entertainment', 'lifestyle', 'education', 'news', 'gaming', 'crypto', 'other']
        if 'category' in data and data['category'] not in valid_categories:
            errors['category'] = 'Invalid category'
        
        return {'valid': len(errors) == 0, 'errors': errors, 'data': data}
    
    def validate_proposal_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Валидация данных предложения"""
        errors = {}
        
        # Валидация комментария при принятии
        if 'comment' in data:
            if not self.validate_length(data['comment'], 'comment'):
                errors['comment'] = 'Comment is too long'
            data['comment'] = self.sanitize_html(data['comment'])
        
        # Валидация причины отклонения
        if 'rejection_reason' in data:
            valid_reasons = ['price', 'topic', 'timing', 'technical', 'content', 'audience', 'other']
            if data['rejection_reason'] not in valid_reasons:
                errors['rejection_reason'] = 'Invalid rejection reason'
        
        # Валидация даты размещения
        if 'placement_date' in data:
            try:
                from datetime import datetime
                datetime.fromisoformat(data['placement_date'].replace('Z', '+00:00'))
            except:
                errors['placement_date'] = 'Invalid date format'
        
        return {'valid': len(errors) == 0, 'errors': errors, 'data': data}
    
    def clean_sql_input(self, value: str) -> str:
        """Очистка входных данных от SQL injection"""
        if not isinstance(value, str):
            return str(value)
        
        # Список опасных SQL ключевых слов
        dangerous_keywords = [
            'DROP', 'DELETE', 'INSERT', 'UPDATE', 'ALTER', 'CREATE',
            'TRUNCATE', 'EXEC', 'EXECUTE', 'UNION', 'SELECT',
            '--', '/*', '*/', ';', 'SCRIPT', 'JAVASCRIPT'
        ]
        
        cleaned = value
        for keyword in dangerous_keywords:
            cleaned = re.sub(keyword, '', cleaned, flags=re.IGNORECASE)
        
        return cleaned.strip()


def validate_json(schema_class=None, **validation_kwargs):
    """
    Декоратор для валидации JSON входных данных
    
    Args:
        schema_class: Класс схемы для валидации (опционально)
        **validation_kwargs: Дополнительные параметры валидации
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            validator = InputValidator()
            
            # Проверяем наличие JSON данных
            if not request.is_json:
                return jsonify({
                    'error': 'Invalid Content-Type',
                    'message': 'Request must be JSON'
                }), 400
            
            try:
                data = request.get_json()
                if not data:
                    return jsonify({
                        'error': 'Empty JSON',
                        'message': 'Request body cannot be empty'
                    }), 400
                
            except Exception as e:
                logger.warning(f"JSON parsing error: {e}")
                return jsonify({
                    'error': 'Invalid JSON',
                    'message': 'Malformed JSON data'
                }), 400
            
            # Базовая валидация по типу endpoint
            validation_result = None
            endpoint = request.endpoint or ''
            
            if 'channels' in endpoint:
                validation_result = validator.validate_channel_data(data)
            elif 'offers' in endpoint:
                validation_result = validator.validate_offer_data(data)
            elif 'proposals' in endpoint:
                validation_result = validator.validate_proposal_data(data)
            
            # Проверяем результат валидации
            if validation_result and not validation_result['valid']:
                logger.warning(f"Validation failed for {endpoint}: {validation_result['errors']}")
                return jsonify({
                    'error': 'Validation Failed',
                    'message': 'Input data validation failed',
                    'details': validation_result['errors']
                }), 422
            
            # Если валидация прошла успешно, обновляем данные
            if validation_result:
                request._cached_json = validation_result['data']
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def validate_telegram_auth():
    """Декоратор для проверки Telegram аутентификации"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            telegram_id = request.headers.get('X-Telegram-User-Id')
            
            if not telegram_id:
                logger.warning(f"Missing Telegram auth: {request.path}")
                return jsonify({
                    'error': 'Unauthorized',
                    'message': 'Telegram authentication required'
                }), 401
            
            # Валидируем формат Telegram ID
            validator = InputValidator()
            if not validator.validate_telegram_id(telegram_id):
                logger.warning(f"Invalid Telegram ID format: {telegram_id}")
                return jsonify({
                    'error': 'Invalid Authentication',
                    'message': 'Invalid Telegram ID format'
                }), 401
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def sanitize_output(data: Any) -> Any:
    """Санитизация выходных данных"""
    validator = InputValidator()
    
    if isinstance(data, str):
        return validator.sanitize_html(data)
    elif isinstance(data, dict):
        return {k: sanitize_output(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_output(item) for item in data]
    else:
        return data


logger.info("✅ Input Validation module initialized")