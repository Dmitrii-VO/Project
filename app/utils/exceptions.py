# app/utils/exceptions.py
"""
Кастомные исключения для Telegram Mini App
Минимальный набор используемых исключений
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


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


__all__ = [
    'TelegramMiniAppError',
    'ValidationError',
    'ChannelError', 
    'OfferError',
    'PaymentError'
]