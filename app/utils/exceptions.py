# app/utils/exceptions.py
"""
Кастомные исключения для Telegram Mini App
Минимальный набор используемых исключений
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Ошибка аутентификации"""
    pass


class TelegramMiniAppError(Exception):
    """
    Базовое исключение для всех ошибок Telegram Mini App
    """
    
    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None
    ):
        self.message = message
        self.code = code or self.__class__.__name__
        self.details = details or {}
        self.user_message = user_message or message
        self.timestamp = datetime.now()
        
        super().__init__(self.message)
        
        # Логирование ошибки
        logger.error(f"[{self.code}] {self.message}", extra={
            'error_code': self.code,
            'details': self.details,
            'timestamp': self.timestamp.isoformat()
        })
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь для API ответов"""
        return {
            'error': True,
            'code': self.code,
            'message': self.user_message,
            'details': self.details,
            'timestamp': self.timestamp.isoformat()
        }
    
    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


# === СПЕЦИФИЧЕСКИЕ ИСКЛЮЧЕНИЯ ===

class ValidationError(TelegramMiniAppError):
    """Ошибки валидации данных"""
    
    def __init__(self, message: str = "Ошибка валидации", **kwargs):
        super().__init__(
            message=message,
            user_message="Переданы некорректные данные.",
            **kwargs
        )


class ChannelError(TelegramMiniAppError):
    """Ошибки работы с каналами"""
    
    def __init__(self, message: str = "Ошибка канала", **kwargs):
        super().__init__(
            message=message,
            user_message="Ошибка при работе с каналом.",
            **kwargs
        )


class OfferError(TelegramMiniAppError):
    """Ошибки работы с офферами"""
    
    def __init__(self, message: str = "Ошибка оффера", **kwargs):
        super().__init__(
            message=message,
            user_message="Ошибка при работе с оффером.",
            **kwargs
        )


class PaymentError(TelegramMiniAppError):
    """Ошибки платежной системы"""
    
    def __init__(self, message: str = "Ошибка платежа", **kwargs):
        super().__init__(
            message=message,
            user_message="Ошибка при обработке платежа.",
            **kwargs
        )


class UserError(TelegramMiniAppError):
    """Ошибки пользователя"""
    
    def __init__(self, message: str = "Ошибка пользователя", **kwargs):
        super().__init__(
            message=message,
            user_message="Ошибка при работе с пользователем.",
            **kwargs
        )


class ResponseError(TelegramMiniAppError):
    """Ошибки ответа API"""
    
    def __init__(self, message: str = "Ошибка ответа", **kwargs):
        super().__init__(
            message=message,
            user_message="Ошибка при обработке ответа.",
            **kwargs
        )


class AnalyticsError(TelegramMiniAppError):
    """Ошибки аналитики"""
    
    def __init__(self, message: str = "Ошибка аналитики", **kwargs):
        super().__init__(
            message=message,
            user_message="Ошибка при работе с аналитикой.",
            **kwargs
        )


class TelegramAPIError(TelegramMiniAppError):
    """Ошибки Telegram API"""
    
    def __init__(self, message: str = "Ошибка Telegram API", **kwargs):
        super().__init__(
            message=message,
            user_message="Ошибка при работе с Telegram API.",
            **kwargs
        )


class InsufficientFundsError(TelegramMiniAppError):
    """Ошибка недостаточно средств"""
    
    def __init__(self, message: str = "Недостаточно средств", **kwargs):
        super().__init__(
            message=message,
            user_message="Недостаточно средств для выполнения операции.",
            **kwargs
        )


class RateLimitError(TelegramMiniAppError):
    """Ошибка превышения лимита запросов"""
    
    def __init__(self, message: str = "Превышен лимит запросов", **kwargs):
        super().__init__(
            message=message,
            user_message="Превышен лимит запросов. Попробуйте позже.",
            **kwargs
        )


class ConfigurationError(TelegramMiniAppError):
    """Ошибки конфигурации"""
    
    def __init__(self, message: str = "Ошибка конфигурации", **kwargs):
        super().__init__(
            message=message,
            user_message="Ошибка в конфигурации системы.",
            **kwargs
        )


__all__ = [
    'TelegramMiniAppError',
    'ValidationError',
    'AuthenticationError',
    'ChannelError', 
    'OfferError',
    'PaymentError',
    'UserError',
    'ResponseError',
    'AnalyticsError',
    'TelegramAPIError',
    'InsufficientFundsError',
    'RateLimitError',
    'ConfigurationError'
]