#!/usr/bin/env python3
"""
Конфигурация для интеграции с eREIT API
"""

import os
from typing import Optional


class EREITConfig:
    """Конфигурация eREIT API"""
    
    # API настройки
    API_KEY: str = os.getenv('EREIT_API_KEY', 'test_api_key')
    API_BASE_URL: str = os.getenv('EREIT_API_URL', 'https://api.ereit.com')
    API_VERSION: str = os.getenv('EREIT_API_VERSION', 'v1')
    
    # Таймауты (в секундах)
    REQUEST_TIMEOUT: int = int(os.getenv('EREIT_REQUEST_TIMEOUT', '30'))
    CONNECTION_TIMEOUT: int = int(os.getenv('EREIT_CONNECTION_TIMEOUT', '10'))
    
    # Лимиты запросов
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv('EREIT_RATE_LIMIT', '60'))
    MAX_RETRIES: int = int(os.getenv('EREIT_MAX_RETRIES', '3'))
    
    # Настройки кэширования
    CACHE_TTL_SECONDS: int = int(os.getenv('EREIT_CACHE_TTL', '300'))  # 5 минут
    ENABLE_CACHING: bool = os.getenv('EREIT_ENABLE_CACHE', 'true').lower() == 'true'
    
    # Режим работы
    MOCK_MODE: bool = os.getenv('EREIT_MOCK_MODE', 'true').lower() == 'true'
    DEBUG_MODE: bool = os.getenv('EREIT_DEBUG', 'false').lower() == 'true'
    
    # Настройки токенов
    TOKEN_PREFIX: str = os.getenv('EREIT_TOKEN_PREFIX', 'EREIT_')
    TOKEN_LENGTH: int = int(os.getenv('EREIT_TOKEN_LENGTH', '10'))
    
    # Webhook настройки (если поддерживается)
    WEBHOOK_URL: Optional[str] = os.getenv('EREIT_WEBHOOK_URL')
    WEBHOOK_SECRET: Optional[str] = os.getenv('EREIT_WEBHOOK_SECRET')
    
    @classmethod
    def get_api_url(cls, endpoint: str) -> str:
        """Формирует полный URL для API запроса"""
        return f"{cls.API_BASE_URL}/{cls.API_VERSION}/{endpoint.lstrip('/')}"
    
    @classmethod
    def is_mock_mode(cls) -> bool:
        """Проверяет, включен ли мок-режим"""
        return cls.MOCK_MODE or cls.API_KEY in ['test_api_key', '', None]
    
    @classmethod
    def get_headers(cls) -> dict:
        """Возвращает стандартные заголовки для API запросов"""
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'TelegramMiniApp/1.0'
        }
        
        if not cls.is_mock_mode():
            headers['Authorization'] = f'Bearer {cls.API_KEY}'
        
        return headers
    
    @classmethod
    def validate_config(cls) -> list:
        """Проверяет корректность конфигурации"""
        errors = []
        
        if not cls.API_KEY or cls.API_KEY == 'test_api_key':
            errors.append("EREIT_API_KEY не установлен (работает в тестовом режиме)")
        
        if cls.REQUEST_TIMEOUT <= 0:
            errors.append("EREIT_REQUEST_TIMEOUT должен быть больше 0")
        
        if cls.RATE_LIMIT_PER_MINUTE <= 0:
            errors.append("EREIT_RATE_LIMIT должен быть больше 0")
        
        if cls.TOKEN_LENGTH < 5:
            errors.append("EREIT_TOKEN_LENGTH должен быть не менее 5")
        
        return errors


# Функции для работы с токенами
def generate_ereit_token(placement_id: int) -> str:
    """Генерирует eREIT токен для размещения"""
    import random
    import string
    
    # Генерируем случайную строку
    random_part = ''.join(random.choices(
        string.ascii_uppercase + string.digits, 
        k=EREITConfig.TOKEN_LENGTH
    ))
    
    return f"{EREITConfig.TOKEN_PREFIX}{random_part}"


def validate_ereit_token(token: str) -> bool:
    """Проверяет корректность eREIT токена"""
    if not token:
        return False
    
    if not token.startswith(EREITConfig.TOKEN_PREFIX):
        return False
    
    token_part = token[len(EREITConfig.TOKEN_PREFIX):]
    if len(token_part) != EREITConfig.TOKEN_LENGTH:
        return False
    
    # Проверяем, что токен содержит только допустимые символы
    allowed_chars = string.ascii_uppercase + string.digits
    return all(c in allowed_chars for c in token_part)


if __name__ == "__main__":
    # Тестирование конфигурации
    print("eREIT Configuration:")
    print(f"API URL: {EREITConfig.get_api_url('tokens')}")
    print(f"Mock Mode: {EREITConfig.is_mock_mode()}")
    print(f"Headers: {EREITConfig.get_headers()}")
    
    # Проверяем конфигурацию
    errors = EREITConfig.validate_config()
    if errors:
        print("Ошибки конфигурации:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("✅ Конфигурация корректна")
    
    # Тестируем генерацию токенов
    test_token = generate_ereit_token(12345)
    print(f"Test token: {test_token}")
    print(f"Token valid: {validate_ereit_token(test_token)}")