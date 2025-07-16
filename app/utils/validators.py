# app/utils/validators.py
"""
Базовые валидаторы для Telegram Mini App
Минимальный набор необходимых функций валидации
"""

import re
import logging
from typing import Union

logger = logging.getLogger(__name__)


class TelegramDataValidator:
    """Класс для валидации данных Telegram"""
    
    @staticmethod
    def validate_telegram_id(telegram_id: Union[str, int]) -> bool:
        """Валидация Telegram User ID"""
        try:
            tid = int(telegram_id)
            return 1 <= tid <= 4294967295
        except (ValueError, TypeError):
            return False


def validate_telegram_id(telegram_id: Union[str, int]) -> bool:
    """
    Валидация Telegram User ID
    
    Args:
        telegram_id: Telegram ID пользователя
        
    Returns:
        bool: True если ID валиден
    """
    try:
        tid = int(telegram_id)
        return 1 <= tid <= 4294967295
    except (ValueError, TypeError):
        return False


def validate_channel_id(channel_id: str) -> bool:
    """
    Валидация Telegram Channel ID
    
    Args:
        channel_id: ID или username канала
        
    Returns:
        bool: True если ID валиден  
    """
    if not isinstance(channel_id, str) or not channel_id.strip():
        return False
    
    channel_id = channel_id.strip()
    
    # Числовой ID (отрицательный для каналов)
    if channel_id.startswith('-'):
        try:
            int(channel_id)
            return True
        except ValueError:
            return False
    
    # Username канала
    if channel_id.startswith('@'):
        username = channel_id[1:]
        return re.match(r'^[a-zA-Z0-9_]{5,32}$', username) is not None
    
    # Username без @
    return re.match(r'^[a-zA-Z0-9_]{5,32}$', channel_id) is not None


def validate_price(price: Union[str, int, float]) -> bool:
    """
    Валидация цены
    
    Args:
        price: Цена для валидации
        
    Returns:
        bool: True если цена валидна
    """
    try:
        price_float = float(price)
        return price_float >= 0
    except (ValueError, TypeError):
        return False


def validate_email(email: str) -> bool:
    """
    Валидация email адреса
    
    Args:
        email: Email адрес для валидации
        
    Returns:
        bool: True если email валиден
    """
    if not isinstance(email, str) or not email.strip():
        return False
    
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_pattern, email.strip()) is not None


def validate_phone(phone: str) -> bool:
    """
    Валидация номера телефона
    
    Args:
        phone: Номер телефона для валидации
        
    Returns:
        bool: True если номер валиден
    """
    if not isinstance(phone, str) or not phone.strip():
        return False
    
    # Убираем все нецифровые символы
    phone_digits = re.sub(r'\D', '', phone)
    
    # Проверяем длину (от 10 до 15 цифр)
    return 10 <= len(phone_digits) <= 15


def validate_url(url: str) -> bool:
    """
    Валидация URL
    
    Args:
        url: URL для валидации
        
    Returns:
        bool: True если URL валиден
    """
    if not isinstance(url, str) or not url.strip():
        return False
    
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+'  # domain...
        r'[A-Z]{2,6}\.?|'  # host...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    return url_pattern.match(url.strip()) is not None


class ChannelDataValidator:
    """Класс для валидации данных канала"""
    
    @staticmethod
    def validate_channel_data(data: dict) -> bool:
        """Валидация данных канала"""
        if not isinstance(data, dict):
            return False
        
        # Проверяем обязательные поля
        required_fields = ['channel_id', 'channel_name']
        for field in required_fields:
            if field not in data or not data[field]:
                return False
        
        # Валидация ID канала
        if not validate_channel_id(data['channel_id']):
            return False
        
        # Валидация имени канала
        channel_name = data['channel_name']
        if not isinstance(channel_name, str) or len(channel_name.strip()) < 1:
            return False
        
        # Валидация описания (если есть)
        if 'description' in data and data['description']:
            if not isinstance(data['description'], str) or len(data['description']) > 1000:
                return False
        
        # Валидация ссылки (если есть)
        if 'url' in data and data['url']:
            if not validate_url(data['url']):
                return False
        
        return True
    
    @staticmethod
    def validate_channel_id(channel_id: str) -> bool:
        """Валидация ID канала"""
        return validate_channel_id(channel_id)


class OfferDataValidator:
    """Класс для валидации данных оффера"""
    
    @staticmethod
    def validate_offer_data(data: dict) -> bool:
        """Валидация данных оффера"""
        if not isinstance(data, dict):
            return False
        
        # Проверяем обязательные поля
        required_fields = ['title', 'description', 'price']
        for field in required_fields:
            if field not in data or not data[field]:
                return False
        
        # Валидация цены
        if not validate_price(data['price']):
            return False
        
        # Валидация заголовка и описания
        if len(data['title'].strip()) < 1 or len(data['title']) > 200:
            return False
        
        if len(data['description'].strip()) < 1 or len(data['description']) > 2000:
            return False
        
        return True


class PaymentDataValidator:
    """Класс для валидации платежных данных"""
    
    @staticmethod
    def validate_payment_data(data: dict) -> bool:
        """Валидация платежных данных"""
        if not isinstance(data, dict):
            return False
        
        # Проверяем обязательные поля
        required_fields = ['amount', 'currency']
        for field in required_fields:
            if field not in data or not data[field]:
                return False
        
        # Валидация суммы
        if not validate_price(data['amount']):
            return False
        
        # Валидация валюты
        allowed_currencies = ['RUB', 'USD', 'EUR']
        if data['currency'] not in allowed_currencies:
            return False
        
        return True


class UserDataValidator:
    """Класс для валидации данных пользователя"""
    
    @staticmethod
    def validate_user_data(data: dict) -> bool:
        """Валидация данных пользователя"""
        if not isinstance(data, dict):
            return False
        
        # Проверяем обязательные поля
        required_fields = ['telegram_id']
        for field in required_fields:
            if field not in data or not data[field]:
                return False
        
        # Валидация Telegram ID
        if not validate_telegram_id(data['telegram_id']):
            return False
        
        # Валидация email (если есть)
        if 'email' in data and data['email']:
            if not validate_email(data['email']):
                return False
        
        # Валидация телефона (если есть)
        if 'phone' in data and data['phone']:
            if not validate_phone(data['phone']):
                return False
        
        return True


class ResponseDataValidator:
    """Класс для валидации данных ответа"""
    
    @staticmethod
    def validate_response_data(data: dict) -> bool:
        """Валидация данных ответа"""
        if not isinstance(data, dict):
            return False
        
        # Проверяем обязательные поля
        required_fields = ['success']
        for field in required_fields:
            if field not in data:
                return False
        
        # Проверяем тип success
        if not isinstance(data['success'], bool):
            return False
        
        return True


__all__ = [
    'TelegramDataValidator',
    'ChannelDataValidator',
    'OfferDataValidator',
    'PaymentDataValidator',
    'UserDataValidator',
    'ResponseDataValidator',
    'validate_telegram_id',
    'validate_channel_id', 
    'validate_price',
    'validate_email',
    'validate_phone',
    'validate_url'
]