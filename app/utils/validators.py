# app/utils/validators.py
"""
Базовые валидаторы для Telegram Mini App
Минимальный набор необходимых функций валидации
"""

import re
import logging
from typing import Union

logger = logging.getLogger(__name__)


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


__all__ = [
    'validate_telegram_id',
    'validate_channel_id', 
    'validate_price'
]