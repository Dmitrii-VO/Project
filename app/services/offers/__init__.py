# app/services/offers/__init__.py
"""
Сервисный слой для работы с офферами
Оптимизированная архитектура для замены монолитного offers.py
"""

from .core.offer_service import OfferService
from .core.offer_repository import OfferRepository
from .core.offer_validator import OfferValidator
from .utils.offer_matcher import OfferMatcher
from .utils.offer_formatter import OfferFormatter

__all__ = [
    'OfferService',
    'OfferRepository', 
    'OfferValidator',
    'OfferMatcher',
    'OfferFormatter'
]